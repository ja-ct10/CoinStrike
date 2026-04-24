import pygame
import random
import math
from settings import *


# ---------------------------------------------------------------------------
# ENEMY DEATH PARTICLES
# ---------------------------------------------------------------------------
class EnemyParticle:
    def __init__(self, x, y):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(3, 9)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed - 3
        self.x = float(x)
        self.y = float(y)
        self.color = random.choice(
            [
                (255, 60, 60),
                (255, 140, 0),
                (255, 220, 60),
                (200, 0, 80),
                (255, 80, 180),
            ]
        )
        self.lifetime = random.randint(20, 40)
        self.max_lifetime = self.lifetime
        self.size = random.randint(3, 8)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dy += 0.25
        self.dx *= 0.95
        self.lifetime -= 1

    @property
    def alive(self):
        return self.lifetime > 0

    def draw(self, screen, camera):
        alpha = int(255 * (self.lifetime / self.max_lifetime))
        size = max(1, int(self.size * (self.lifetime / self.max_lifetime)))
        r, g, b = self.color
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (r, g, b, alpha), (size, size), size)
        world_rect = pygame.Rect(
            int(self.x) - size, int(self.y) - size, size * 2, size * 2
        )
        screen.blit(surf, camera.apply(world_rect))


# ---------------------------------------------------------------------------
# HIT FLASH EFFECT
# ---------------------------------------------------------------------------
class HitFlash:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = 12
        self.max_timer = 12

    @property
    def alive(self):
        return self.timer > 0

    def update(self):
        self.timer -= 1

    def draw(self, screen, camera):
        if not self.alive:
            return
        progress = self.timer / self.max_timer
        radius = int(22 * (1 - progress) + 6)
        alpha = int(220 * progress)
        surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 160, alpha), (radius, radius), radius)
        world_rect = pygame.Rect(
            self.x - radius, self.y - radius, radius * 2, radius * 2
        )
        screen.blit(surf, camera.apply(world_rect))


# ---------------------------------------------------------------------------
# ENEMY
# ---------------------------------------------------------------------------
ENEMY_WIDTH = 48
ENEMY_HEIGHT = 52

# How many frames of invincibility the player gets after being hit
PLAYER_HIT_INVINCIBLE_FRAMES = 90


class Enemy:
    # Sprite-sheet-less colours for the drawn enemy
    BODY_COLOR = (180, 30, 30)
    BODY_DARK = (100, 10, 10)
    EYE_COLOR = (255, 220, 60)
    PUPIL_COLOR = (20, 0, 0)
    OUTLINE_COLOR = (60, 0, 0)
    HEALTH_BG = (60, 0, 0)
    HEALTH_FG = (255, 60, 60)

    PATROL_SPEED = 2
    CHASE_SPEED = 3
    DETECT_RANGE = 260  # px — starts chasing player inside this range
    ATTACK_RANGE = 36  # px — deals damage inside this range
    ATTACK_DAMAGE = 1  # hearts removed per hit
    ATTACK_COOLDOWN = 90  # frames between damage ticks
    MAX_HP = 3

    def __init__(self, x, y, home_surface=None):
        self.rect = pygame.Rect(x, y, ENEMY_WIDTH, ENEMY_HEIGHT)
        self.world_x = float(x)
        self.vel_y = 0
        self.gravity = 0.7
        self.on_ground = False

        self.facing_right = True
        self.home_surface = home_surface  # surface enemy is locked to
        self.patrol_dir = 1  # +1 = right, -1 = left

        self.hp = self.MAX_HP
        self.alive = True
        self.hit_timer = 0  # flash red when hit
        self.attack_timer = 0  # cooldown between player hits

        self.state = "patrol"  # "patrol" | "chase"

        self.particles = []
        self.hit_flashes = []
        self.death_done = False  # True once death animation finished

        # Walk animation
        self.anim_frame = 0
        self.anim_timer = 0

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _distance_to_player(self, player):
        dx = self.rect.centerx - player.rect.centerx
        dy = self.rect.centery - player.rect.centery
        return math.sqrt(dx * dx + dy * dy)

    def _get_home_bounds(self):
        """
        Returns (left, right) world-x limits the enemy must stay within.
        Uses the assigned platform or ground segment as the home surface.
        """
        if self.home_surface is not None:
            margin = 2
            return (
                self.home_surface.rect.left + margin,
                self.home_surface.rect.right - ENEMY_WIDTH - margin,
            )
        return (0, SCREEN_WIDTH * 6)

    def _clamp_to_home(self):
        """Hard-clamp world_x so the enemy never leaves its home surface."""
        left, right = self._get_home_bounds()
        self.world_x = max(float(left), min(float(right), self.world_x))
        self.rect.x = int(self.world_x)

    def _patrol(self, platforms, ground_segments):
        """Walk back and forth strictly within the home surface bounds."""
        left, right = self._get_home_bounds()

        self.world_x += self.PATROL_SPEED * self.patrol_dir
        self.rect.x = int(self.world_x)

        # Reverse at home surface edges
        if self.world_x >= right:
            self.world_x = float(right)
            self.patrol_dir = -1
        elif self.world_x <= left:
            self.world_x = float(left)
            self.patrol_dir = 1

        self._clamp_to_home()
        self.facing_right = self.patrol_dir > 0

    def _chase(self, player, platforms, ground_segments):
        """Chase the player but never leave the home surface."""
        left, right = self._get_home_bounds()

        if player.rect.centerx > self.rect.centerx:
            self.patrol_dir = 1
            self.facing_right = True
        else:
            self.patrol_dir = -1
            self.facing_right = False

        next_x = self.world_x + self.CHASE_SPEED * self.patrol_dir

        # Stop at home surface boundary instead of crossing it
        next_x = max(float(left), min(float(right), next_x))
        self.world_x = next_x
        self.rect.x = int(self.world_x)

    def _apply_gravity(self, platforms, ground_segments):
        """Simple gravity + landing on platforms/ground."""
        self.vel_y += self.gravity
        self.rect.y += int(self.vel_y)
        self.on_ground = False

        for seg in ground_segments:
            if self.rect.colliderect(seg.rect) and self.vel_y >= 0:
                if self.rect.bottom <= seg.rect.top + 16:
                    self.rect.bottom = seg.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    break

        if not self.on_ground:
            for p in platforms:
                if not p.visible:
                    continue
                if self.rect.colliderect(p.rect) and self.vel_y >= 0:
                    if self.rect.bottom <= p.rect.top + 16:
                        self.rect.bottom = p.rect.top
                        self.vel_y = 0
                        self.on_ground = True
                        break

    def _try_attack_player(self, player, health):
        """If close enough, deal 1 heart of damage to the player."""
        if self.attack_timer > 0:
            self.attack_timer -= 1
            return

        if not pygame.Rect.colliderect(self.rect, player.rect):
            return

        dist = self._distance_to_player(player)
        if dist <= self.ATTACK_RANGE + 30:  # generous contact box
            if health.invincible_timer == 0:
                health.take_damage(20)  # each enemy hit = 20 HP
                if not health.game_over:
                    health.invincible_timer = PLAYER_HIT_INVINCIBLE_FRAMES
                self.attack_timer = self.ATTACK_COOLDOWN

    # ------------------------------------------------------------------
    # TAKE HIT  (called by EnemyManager when a projectile lands)
    # ------------------------------------------------------------------
    def take_hit(self, damage=1):
        if not self.alive:
            return
        self.hp -= damage
        self.hit_timer = 10
        self.hit_flashes.append(HitFlash(self.rect.centerx, self.rect.centery))
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            self.just_died = True
            self._spawn_death_particles()

    def _spawn_death_particles(self):
        for _ in range(30):
            self.particles.append(EnemyParticle(self.rect.centerx, self.rect.centery))

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self, platforms, ground_segments, player, health):
        # Death animation — keep updating particles even after alive=False
        if not self.alive:
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.alive]
            for f in self.hit_flashes:
                f.update()
            self.hit_flashes = [f for f in self.hit_flashes if f.alive]
            if not self.particles and not self.hit_flashes:
                self.death_done = True
            return

        # Hit flash timer
        if self.hit_timer > 0:
            self.hit_timer -= 1

        # AI state machine
        dist = self._distance_to_player(player)
        if dist < self.DETECT_RANGE:
            self.state = "chase"
        else:
            self.state = "patrol"

        if self.state == "patrol":
            self._patrol(platforms, ground_segments)
        else:
            self._chase(player, platforms, ground_segments)

        self._apply_gravity(platforms, ground_segments)
        self._try_attack_player(player, health)

        # Walk animation tick
        self.anim_timer += 1
        if self.anim_timer >= 8:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4

        # Update particles / flashes
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]
        for f in self.hit_flashes:
            f.update()
        self.hit_flashes = [f for f in self.hit_flashes if f.alive]

    # ------------------------------------------------------------------
    # DRAW  (procedural pixel-art style — no sprite file needed)
    # ------------------------------------------------------------------
    def draw(self, screen, camera):
        # Always draw particles / flashes even after death
        for f in self.hit_flashes:
            f.draw(screen, camera)
        for p in self.particles:
            p.draw(screen, camera)

        if not self.alive:
            return

        dr = camera.apply(self.rect)  # screen-space rect
        cx, cy = dr.centerx, dr.centery
        w, h = ENEMY_WIDTH, ENEMY_HEIGHT

        # Leg bobbing offset
        leg_bob = [0, 3, 0, -3][self.anim_frame]

        # --- Shadow ---
        shadow_surf = pygame.Surface((w, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), shadow_surf.get_rect())
        screen.blit(shadow_surf, (dr.x, dr.bottom - 4))

        # --- Body ---
        body_col = (255, 80, 80) if self.hit_timer > 0 else self.BODY_COLOR
        pygame.draw.ellipse(
            screen, self.OUTLINE_COLOR, pygame.Rect(dr.x - 1, dr.y + 10, w + 2, h - 16)
        )
        pygame.draw.ellipse(screen, body_col, pygame.Rect(dr.x, dr.y + 12, w, h - 18))
        # Belly sheen
        pygame.draw.ellipse(
            screen,
            (220, 60, 60) if self.hit_timer == 0 else (255, 160, 160),
            pygame.Rect(dr.x + w // 4, dr.y + 18, w // 2, (h - 18) // 2),
        )

        # --- Head ---
        head_r = 20
        hx, hy = cx, dr.y + head_r + 4
        pygame.draw.circle(screen, self.OUTLINE_COLOR, (hx, hy), head_r + 1)
        pygame.draw.circle(screen, body_col, (hx, hy), head_r)

        # --- Horns ---
        horn_col = (220, 40, 40) if self.hit_timer == 0 else (255, 180, 180)
        if self.facing_right:
            pygame.draw.polygon(
                screen,
                horn_col,
                [(hx - 10, hy - 14), (hx - 6, hy - 26), (hx - 2, hy - 14)],
            )
            pygame.draw.polygon(
                screen,
                horn_col,
                [(hx + 4, hy - 16), (hx + 8, hy - 28), (hx + 12, hy - 14)],
            )
        else:
            pygame.draw.polygon(
                screen,
                horn_col,
                [(hx - 12, hy - 14), (hx - 8, hy - 28), (hx - 4, hy - 16)],
            )
            pygame.draw.polygon(
                screen,
                horn_col,
                [(hx + 2, hy - 14), (hx + 6, hy - 26), (hx + 10, hy - 14)],
            )

        # --- Eyes ---
        eye_offset = 7 if self.facing_right else -7
        for ex_sign in [1, -1]:
            ex = hx + ex_sign * 7
            ey = hy - 3
            pygame.draw.circle(screen, self.EYE_COLOR, (ex, ey), 6)
            # Pupil tracks toward player direction
            px_off = 2 if self.facing_right else -2
            pygame.draw.circle(screen, self.PUPIL_COLOR, (ex + px_off, ey + 1), 3)
            pygame.draw.circle(screen, (255, 255, 255), (ex + px_off - 1, ey - 1), 1)

        # Angry brow
        brow_col = (80, 0, 0)
        if self.state == "chase":
            brow_col = (200, 0, 0)
        for ex_sign in [1, -1]:
            ex = hx + ex_sign * 7
            ey = hy - 3
            brow_dx = 5 if ex_sign == 1 else -5
            pygame.draw.line(
                screen,
                brow_col,
                (ex - brow_dx // 2, ey - 8),
                (ex + brow_dx // 2, ey - 5),
                2,
            )

        # --- Legs ---
        leg_col = self.BODY_DARK if self.hit_timer == 0 else (180, 40, 40)
        leg_y_base = dr.bottom - 10
        bob_a = leg_bob
        bob_b = -leg_bob
        pygame.draw.ellipse(
            screen, leg_col, pygame.Rect(dr.x + 4, leg_y_base + bob_a, 14, 12)
        )
        pygame.draw.ellipse(
            screen, leg_col, pygame.Rect(dr.x + w - 18, leg_y_base + bob_b, 14, 12)
        )

        # --- Arms ---
        arm_col = self.BODY_DARK if self.hit_timer == 0 else (180, 40, 40)
        arm_bob = leg_bob // 2
        pygame.draw.ellipse(
            screen, arm_col, pygame.Rect(dr.x - 6, dr.y + 26 + arm_bob, 12, 20)
        )
        pygame.draw.ellipse(
            screen, arm_col, pygame.Rect(dr.right - 6, dr.y + 26 - arm_bob, 12, 20)
        )

        # --- HP bar (only when chasing or recently hit) ---
        if self.state == "chase" or self.hit_timer > 0:
            bar_w = w
            bar_h = 6
            bar_x = dr.x
            bar_y = dr.y - 12
            pygame.draw.rect(
                screen,
                self.HEALTH_BG,
                pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                border_radius=3,
            )
            fill_w = int(bar_w * (self.hp / self.MAX_HP))
            if fill_w > 0:
                pygame.draw.rect(
                    screen,
                    self.HEALTH_FG,
                    pygame.Rect(bar_x, bar_y, fill_w, bar_h),
                    border_radius=3,
                )
            pygame.draw.rect(
                screen,
                (200, 0, 0),
                pygame.Rect(bar_x, bar_y, bar_w, bar_h),
                1,
                border_radius=3,
            )


# ---------------------------------------------------------------------------
# ENEMY MANAGER  — owns all enemies, handles spawning & weapon collision
# ---------------------------------------------------------------------------
class EnemyManager:

    SPAWN_INTERVAL = 420  # frames between spawns (~7 s at 60 fps)

    def __init__(self, platforms, ground_segments):
        self.enemies = []
        self.platforms = platforms
        self.ground_segments = ground_segments
        self.spawn_timer = 0

        # ✅ ADDED: mission tracking
        self.enemies_killed = 0

        # Pre-spawn a few enemies spread across platforms
        self._initial_spawn()

    def _initial_spawn(self):
        for i, plat in enumerate(self.platforms):
            if i % 3 == 2:
                x = plat.rect.centerx - ENEMY_WIDTH // 2
                y = plat.rect.top - ENEMY_HEIGHT
                self.enemies.append(Enemy(x, y, home_surface=plat))

        for seg in self.ground_segments[1::2]:
            x = seg.rect.left + random.randint(60, max(61, seg.rect.width - 100))
            y = seg.rect.top - ENEMY_HEIGHT
            self.enemies.append(Enemy(x, y, home_surface=seg))

    def _spawn_new(self):
        candidates = [p for p in self.platforms if not p.glitch or p.visible]
        if not candidates:
            return
        plat = random.choice(candidates)
        x = plat.rect.centerx - ENEMY_WIDTH // 2
        y = plat.rect.top - ENEMY_HEIGHT
        self.enemies.append(Enemy(x, y, home_surface=plat))

    def update(self, player, health, weapon_manager):
        # Spawn logic
        self.spawn_timer += 1
        if self.spawn_timer >= self.SPAWN_INTERVAL:
            self.spawn_timer = 0
            self._spawn_new()

        # Update enemies
        for enemy in self.enemies:
            enemy.update(self.platforms, self.ground_segments, player, health)

        # Weapon collisions
        self._check_bullets(weapon_manager)
        self._check_grenades(weapon_manager)
        self._check_spears(weapon_manager)

        # ✅ FINAL KILL COUNTING (CORRECT + SAFE)
        new_enemies = []
        for e in self.enemies:
            if getattr(e, "just_died", False):
                self.enemies_killed += 1
                e.just_died = False

            if not e.death_done:
                new_enemies.append(e)

        self.enemies = new_enemies

    # --- Collision helpers ---
    def _check_bullets(self, wm):
        for bullet in wm.bullets:
            if not bullet.alive:
                continue
            for enemy in self.enemies:
                if enemy.alive and bullet.rect.colliderect(enemy.rect):
                    enemy.take_hit(3)
                    bullet.alive = False
                    break

    def _check_grenades(self, wm):
        for grenade in wm.grenades:
            if not grenade.exploding:
                continue
            for enemy in self.enemies:
                if not enemy.alive:
                    continue
                dx = enemy.rect.centerx - grenade.x
                dy = enemy.rect.centery - grenade.y
                if math.sqrt(dx * dx + dy * dy) <= grenade.EXPLOSION_RADIUS:
                    enemy.take_hit(5)

    def _check_spears(self, wm):
        for spear in wm.spears:
            if not spear.alive:
                continue
            spear_rect = pygame.Rect(int(spear.x) - 20, int(spear.y) - 4, 40, 8)
            for enemy in self.enemies:
                if enemy.alive and spear_rect.colliderect(enemy.rect):
                    enemy.take_hit(5)
                    spear.alive = False
                    break

    def draw(self, screen, camera):
        for enemy in self.enemies:
            enemy.draw(screen, camera)
