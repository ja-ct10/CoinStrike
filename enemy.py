import pygame
import random
import math
from settings import *

# Module-level reusable Rects to avoid per-frame allocation in draw methods
_SCRATCH_RECT = pygame.Rect(0, 0, 0, 0)
# Extra scratch rects for FinalBoss.draw which needs several simultaneously
_SCRATCH_RECT_B = pygame.Rect(0, 0, 0, 0)
_SCRATCH_RECT_C = pygame.Rect(0, 0, 0, 0)
_SCRATCH_RECT_D = pygame.Rect(0, 0, 0, 0)

# Pre-computed leg-bob lookup (avoids list construction each draw call)
_LEG_BOB = (0, 3, 0, -3)
_BOSS_LEG_BOB = (0, 4, 0, -4)


# ---------------------------------------------------------------------------
# ENEMY PROJECTILE
# ---------------------------------------------------------------------------
class EnemyProjectile:
    BASE_SPEED = 5
    DAMAGE = 5
    RADIUS = 6

    # Pre-baked glow surface shared across all projectile instances
    _GLOW_SURF: pygame.Surface | None = None

    @classmethod
    def _get_glow_surf(cls) -> pygame.Surface:
        if cls._GLOW_SURF is None:
            r = cls.RADIUS
            size = r * 4
            cls._GLOW_SURF = pygame.Surface((size, size), pygame.SRCALPHA)
            pygame.draw.circle(cls._GLOW_SURF, (255, 60, 0, 80), (r * 2, r * 2), r * 2)
        return cls._GLOW_SURF

    def __init__(self, x, y, target_x, target_y, speed_multiplier=1.0):
        self.x = float(x)
        self.y = float(y)
        self._alive = True

        dx = target_x - x
        dy = target_y - y
        dist = math.sqrt(dx * dx + dy * dy) or 1
        speed = self.BASE_SPEED * speed_multiplier
        self.dx = (dx / dist) * speed
        self.dy = (dy / dist) * speed

        # Reusable rect — updated in-place to avoid per-frame allocation
        r = self.RADIUS
        self._rect = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    @property
    def alive(self):
        return self._alive

    @property
    def rect(self):
        r = self.RADIUS
        self._rect.x = int(self.x) - r
        self._rect.y = int(self.y) - r
        return self._rect

    def update(self, ground_segments, platforms):
        self.x += self.dx
        self.y += self.dy

        # Off-screen check
        if self.x < -400 or self.x > SCREEN_WIDTH * 8 or self.y > SCREEN_HEIGHT + 100:
            self._alive = False
            return

        # Ground collision only — projectiles pass through platforms so they
        # can travel between different platform heights
        for seg in ground_segments:
            if self.rect.colliderect(seg.rect):
                self._alive = False
                return

    def draw(self, screen, camera):
        if not self._alive:
            return
        world_rect = self.rect
        draw_pos = camera.apply(world_rect)
        cx = draw_pos.centerx
        cy = draw_pos.centery
        r = self.RADIUS

        # Glow — reuse shared pre-baked surface (no per-frame allocation)
        glow_surf = self._get_glow_surf()
        screen.blit(glow_surf, (cx - r * 2, cy - r * 2))

        # Core
        pygame.draw.circle(screen, (255, 120, 0), (cx, cy), r)
        pygame.draw.circle(screen, (255, 220, 100), (cx, cy), max(1, r - 2))


# ---------------------------------------------------------------------------
# ENEMY DEATH PARTICLES
# ---------------------------------------------------------------------------
class EnemyParticle:
    # Cache of (size, r, g, b, alpha) → Surface to avoid per-frame allocation
    _surf_cache: dict = {}

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
        # Quantize alpha to steps of 16 to dramatically improve cache hit rate
        # (255 unique values → 16 buckets), at the cost of imperceptible banding.
        alpha_q = (alpha >> 4) << 4
        key = (size, r, g, b, alpha_q)
        surf = EnemyParticle._surf_cache.get(key)
        if surf is None:
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (r, g, b, alpha_q), (size, size), size)
            # Keep cache bounded — evict a quarter of entries (LRU-lite) rather
            # than clearing everything, so hot entries survive the eviction.
            if len(EnemyParticle._surf_cache) > 256:
                evict_keys = list(EnemyParticle._surf_cache.keys())[:64]
                for k in evict_keys:
                    del EnemyParticle._surf_cache[k]
            EnemyParticle._surf_cache[key] = surf
        # Reuse module-level scratch rect — avoids per-frame allocation
        _SCRATCH_RECT.x = int(self.x) - size
        _SCRATCH_RECT.y = int(self.y) - size
        _SCRATCH_RECT.width = size * 2
        _SCRATCH_RECT.height = size * 2
        screen.blit(surf, camera.apply(_SCRATCH_RECT))


# ---------------------------------------------------------------------------
# HIT FLASH EFFECT
# ---------------------------------------------------------------------------
class HitFlash:
    # Pre-bake all 12 frames at construction time so draw() never allocates
    _FRAMES: list | None = None
    _MAX_TIMER = 12

    @classmethod
    def _build_frames(cls):
        cls._FRAMES = []
        for t in range(cls._MAX_TIMER, 0, -1):
            progress = t / cls._MAX_TIMER
            radius = int(22 * (1 - progress) + 6)
            alpha = int(220 * progress)
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (255, 255, 160, alpha), (radius, radius), radius)
            cls._FRAMES.append((surf, radius))

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.timer = self._MAX_TIMER
        self.max_timer = self._MAX_TIMER
        if HitFlash._FRAMES is None:
            HitFlash._build_frames()

    @property
    def alive(self):
        return self.timer > 0

    def update(self):
        self.timer -= 1

    def draw(self, screen, camera):
        if not self.alive:
            return
        # Index into pre-baked frames (timer counts down from max_timer to 1)
        frame_idx = self.max_timer - self.timer  # 0 = first frame (largest alpha)
        surf, radius = HitFlash._FRAMES[frame_idx]
        # Reuse module-level scratch rect — avoids per-frame allocation
        _SCRATCH_RECT.x = self.x - radius
        _SCRATCH_RECT.y = self.y - radius
        _SCRATCH_RECT.width = radius * 2
        _SCRATCH_RECT.height = radius * 2
        screen.blit(surf, camera.apply(_SCRATCH_RECT))


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
    DETECT_RANGE_SQ = 260 * 260  # squared — avoids sqrt in state check
    ATTACK_RANGE = 36  # px — deals damage inside this range
    ATTACK_DAMAGE = 5  # HP removed per contact hit
    ATTACK_COOLDOWN = 90  # frames between damage ticks
    MAX_HP = 3

    # Pre-baked shadow surface shared across all Enemy instances
    _SHADOW_SURF: pygame.Surface | None = None

    @classmethod
    def _get_shadow_surf(cls) -> pygame.Surface:
        if cls._SHADOW_SURF is None:
            cls._SHADOW_SURF = pygame.Surface((ENEMY_WIDTH, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(
                cls._SHADOW_SURF, (0, 0, 0, 60), cls._SHADOW_SURF.get_rect()
            )
        return cls._SHADOW_SURF

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
        self.just_died = False  # True for exactly one frame after death

        # Walk animation
        self.anim_frame = 0
        self.anim_timer = 0

        # Projectile firing
        self.shoot_timer = random.randint(60, 240)  # stagger initial shots
        self.projectiles = []
        self.projectile_speed_multiplier = 1.0  # set by DifficultyScaler

    SHOOT_RANGE = 600
    SHOOT_COOLDOWN = 240  # 4 seconds between shots per enemy

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _distance_sq_to_player(self, player):
        """Return squared distance to player (avoids sqrt — use for comparisons)."""
        dx = self.rect.centerx - player.rect.centerx
        dy = self.rect.centery - player.rect.centery
        return dx * dx + dy * dy

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

        # Inline clamp — avoids a second _get_home_bounds() call
        self.world_x = max(float(left), min(float(right), self.world_x))
        self.rect.x = int(self.world_x)
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

        # Stop at home surface boundary instead of crossing it — inline clamp
        self.world_x = max(float(left), min(float(right), next_x))
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
        """If close enough, deal damage to the player."""
        if self.attack_timer > 0:
            self.attack_timer -= 1
            return

        if not pygame.Rect.colliderect(self.rect, player.rect):
            return

        # Rect overlap already confirms contact — no sqrt needed
        if health.invincible_timer == 0:
            health.take_damage(self.ATTACK_DAMAGE)
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

        # AI state machine — use squared distance to avoid sqrt
        dist_sq = self._distance_sq_to_player(player)
        if dist_sq < self.DETECT_RANGE_SQ:
            self.state = "chase"
        else:
            self.state = "patrol"

        if self.state == "patrol":
            self._patrol(platforms, ground_segments)
        else:
            self._chase(player, platforms, ground_segments)

        self._apply_gravity(platforms, ground_segments)
        self._try_attack_player(player, health)

        # Projectile firing — only fires if player is within horizontal range
        # AND the player is ahead of the enemy (not behind/passed them)
        h_dist = abs(self.rect.centerx - player.rect.centerx)
        player_is_ahead = (
            player.rect.centerx > self.rect.centerx and self.facing_right
        ) or (player.rect.centerx < self.rect.centerx and not self.facing_right)
        if h_dist < self.SHOOT_RANGE and player_is_ahead:
            if self.shoot_timer <= 0:
                self.projectiles.append(
                    EnemyProjectile(
                        self.rect.centerx,
                        self.rect.centery,
                        player.rect.centerx,
                        player.rect.centery,
                        speed_multiplier=self.projectile_speed_multiplier,
                    )
                )
                self.shoot_timer = self.SHOOT_COOLDOWN
            else:
                self.shoot_timer -= 1
        elif self.shoot_timer > 0:
            self.shoot_timer -= 1

        # Update projectiles
        for proj in self.projectiles:
            proj.update(ground_segments, platforms)
        self.projectiles = [p for p in self.projectiles if p.alive]

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

    # Pre-allocated draw rects — updated in-place each frame to avoid allocation
    _DRAW_RECT_A = pygame.Rect(0, 0, 0, 0)
    _DRAW_RECT_B = pygame.Rect(0, 0, 0, 0)
    _DRAW_RECT_C = pygame.Rect(0, 0, 0, 0)

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

        # Leg bobbing offset — use pre-computed tuple (no list allocation per frame)
        leg_bob = _LEG_BOB[self.anim_frame]

        # --- Shadow ---
        screen.blit(self._get_shadow_surf(), (dr.x, dr.bottom - 4))

        # --- Body --- (reuse class-level rects)
        body_col = (255, 80, 80) if self.hit_timer > 0 else self.BODY_COLOR
        Enemy._DRAW_RECT_A.update(dr.x - 1, dr.y + 10, w + 2, h - 16)
        pygame.draw.ellipse(screen, self.OUTLINE_COLOR, Enemy._DRAW_RECT_A)
        Enemy._DRAW_RECT_A.update(dr.x, dr.y + 12, w, h - 18)
        pygame.draw.ellipse(screen, body_col, Enemy._DRAW_RECT_A)
        # Belly sheen
        Enemy._DRAW_RECT_A.update(dr.x + w // 4, dr.y + 18, w // 2, (h - 18) // 2)
        pygame.draw.ellipse(
            screen,
            (220, 60, 60) if self.hit_timer == 0 else (255, 160, 160),
            Enemy._DRAW_RECT_A,
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
        for ex_sign in [1, -1]:
            ex = hx + ex_sign * 7
            ey = hy - 3
            pygame.draw.circle(screen, self.EYE_COLOR, (ex, ey), 6)
            # Pupil tracks toward player direction
            px_off = 2 if self.facing_right else -2
            pygame.draw.circle(screen, self.PUPIL_COLOR, (ex + px_off, ey + 1), 3)
            pygame.draw.circle(screen, (255, 255, 255), (ex + px_off - 1, ey - 1), 1)

        # Angry brow
        brow_col = (200, 0, 0) if self.state == "chase" else (80, 0, 0)
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
        Enemy._DRAW_RECT_A.update(dr.x + 4, leg_y_base + bob_a, 14, 12)
        pygame.draw.ellipse(screen, leg_col, Enemy._DRAW_RECT_A)
        Enemy._DRAW_RECT_A.update(dr.x + w - 18, leg_y_base + bob_b, 14, 12)
        pygame.draw.ellipse(screen, leg_col, Enemy._DRAW_RECT_A)

        # --- Arms ---
        arm_col = self.BODY_DARK if self.hit_timer == 0 else (180, 40, 40)
        arm_bob = leg_bob // 2
        Enemy._DRAW_RECT_A.update(dr.x - 6, dr.y + 26 + arm_bob, 12, 20)
        pygame.draw.ellipse(screen, arm_col, Enemy._DRAW_RECT_A)
        Enemy._DRAW_RECT_A.update(dr.right - 6, dr.y + 26 - arm_bob, 12, 20)
        pygame.draw.ellipse(screen, arm_col, Enemy._DRAW_RECT_A)

        # --- HP bar (only when chasing or recently hit) ---
        if self.state == "chase" or self.hit_timer > 0:
            bar_w = w
            bar_h = 6
            bar_x = dr.x
            bar_y = dr.y - 12
            Enemy._DRAW_RECT_B.update(bar_x, bar_y, bar_w, bar_h)
            pygame.draw.rect(
                screen, self.HEALTH_BG, Enemy._DRAW_RECT_B, border_radius=3
            )
            fill_w = int(bar_w * (self.hp / self.MAX_HP))
            if fill_w > 0:
                Enemy._DRAW_RECT_C.update(bar_x, bar_y, fill_w, bar_h)
                pygame.draw.rect(
                    screen, self.HEALTH_FG, Enemy._DRAW_RECT_C, border_radius=3
                )
            pygame.draw.rect(
                screen, (200, 0, 0), Enemy._DRAW_RECT_B, 1, border_radius=3
            )

        # --- Projectiles ---
        for proj in self.projectiles:
            proj.draw(screen, camera)


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

        # Shared alive-enemies cache — rebuilt once per update(), reused by all
        # collision helpers to avoid three separate list comprehensions per frame.
        self._alive_enemies_cache = []

        # Boss state
        self.boss = None
        self.boss_spawned = False
        self.boss_defeated = False

        # Track by world-x position instead of Python id() — id() can be reused
        # after pruning, causing new surfaces to be mistaken for already-seen ones.
        self._seen_platform_xs: set = set()
        self._seen_ground_xs: set = set()

        # Pre-spawn a few enemies spread across platforms
        self._initial_spawn()

    def update_surfaces(self, platforms, ground_segments):
        """Called by WorldManager when new terrain is generated."""
        self.platforms = platforms
        self.ground_segments = ground_segments
        # Spawn enemies on newly generated platforms and ground segments
        self._spawn_on_new_surfaces()

    def _spawn_on_new_surfaces(self):
        """Spawn enemies on platforms and ground segments we haven't seen yet."""
        # Spawn on new platforms (every 3rd platform)
        for plat in self.platforms:
            key = plat.rect.x
            if key in self._seen_platform_xs:
                continue
            self._seen_platform_xs.add(key)

            # Spawn on every 3rd platform (same pattern as initial spawn)
            if len(self._seen_platform_xs) % 3 == 0:
                x = plat.rect.centerx - ENEMY_WIDTH // 2
                y = plat.rect.top - ENEMY_HEIGHT
                self.enemies.append(Enemy(x, y, home_surface=plat))

        # Spawn on new ground segments (every other segment)
        for seg in self.ground_segments:
            key = seg.rect.x
            if key in self._seen_ground_xs:
                continue
            self._seen_ground_xs.add(key)

            # Spawn on every other ground segment (same pattern as initial spawn)
            if len(self._seen_ground_xs) % 2 == 0:
                x = seg.rect.left + random.randint(60, max(61, seg.rect.width - 100))
                y = seg.rect.top - ENEMY_HEIGHT
                self.enemies.append(Enemy(x, y, home_surface=seg))

    def _initial_spawn(self):
        """Pre-spawn enemies on initial platforms and ground segments."""
        for i, plat in enumerate(self.platforms):
            # Track this platform as seen
            self._seen_platform_xs.add(plat.rect.x)

            if i % 3 == 2:
                x = plat.rect.centerx - ENEMY_WIDTH // 2
                y = plat.rect.top - ENEMY_HEIGHT
                self.enemies.append(Enemy(x, y, home_surface=plat))

        for i, seg in enumerate(self.ground_segments):
            # Track this segment as seen
            self._seen_ground_xs.add(seg.rect.x)

            if i % 2 == 1:  # every other segment (1, 3, 5, ...)
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

    def spawn_boss(self, player):
        """Spawn the FinalBoss ahead of the player and clear all regular enemies."""
        if self.boss_spawned:
            return
        bx = player.rect.x + 600
        by = SCREEN_HEIGHT - 100 - BOSS_HEIGHT
        self.boss = FinalBoss(bx, by)
        self.boss_spawned = True
        # Clear all regular enemies so the boss fight is a 1-on-1 encounter
        self.enemies = []
        # Stop regular enemy spawning during the boss fight
        self.spawn_timer = 0

    def update(self, player, health, weapon_manager, difficulty_scaler=None):
        # Timer-based spawn logic as fallback — only spawns if no new surfaces
        # were generated recently. No regular enemy spawning during boss fight.
        if not self.boss_spawned:
            spawn_interval = self.SPAWN_INTERVAL
            if difficulty_scaler is not None:
                spawn_interval = difficulty_scaler.enemy_spawn_interval

            self.spawn_timer += 1
            if self.spawn_timer >= spawn_interval:
                self.spawn_timer = 0
                # Fallback spawn: pick a random platform from the current list
                # This ensures enemies still spawn even if world generation stalls
                self._spawn_new()

        # Apply projectile speed multiplier and update enemies in a single pass
        proj_speed = 1.0
        if difficulty_scaler is not None:
            proj_speed = difficulty_scaler.projectile_speed_multiplier
        for enemy in self.enemies:
            if enemy.projectile_speed_multiplier != proj_speed:
                enemy.projectile_speed_multiplier = proj_speed
            enemy.update(self.platforms, self.ground_segments, player, health)

        # Weapon collisions — build alive_enemies once, share across all checks
        self._alive_enemies_cache = [e for e in self.enemies if e.alive]
        self._check_bullets(weapon_manager)
        self._check_grenades(weapon_manager)
        self._check_spears(weapon_manager)

        # Projectile hits on player
        self._check_projectile_hits(player, health)

        # Update boss if present
        if self.boss is not None:
            self.boss.projectile_speed_multiplier = proj_speed
            self.boss.update(self.platforms, self.ground_segments, player, health)
            # Check weapon hits on boss
            self._check_bullets_boss(weapon_manager)
            self._check_grenades_boss(weapon_manager)
            self._check_spears_boss(weapon_manager)
            # Check boss projectile hits on player
            if health.invincible_timer == 0:
                for proj in self.boss.projectiles:
                    if proj.alive and proj.rect.colliderect(player.rect):
                        health.take_damage(proj.DAMAGE)
                        proj._alive = False
                        if not health.game_over:
                            health.invincible_timer = health.INVINCIBLE_FRAMES
                        break
            # Check if boss defeated
            if not self.boss.alive and self.boss.death_done:
                self.boss_defeated = True

        # ✅ FINAL KILL COUNTING (CORRECT + SAFE)
        # Only rebuild the list when at least one enemy died this frame.
        has_dead = any(e.death_done or e.just_died for e in self.enemies)
        if has_dead:
            new_enemies = []
            for e in self.enemies:
                if e.just_died:
                    self.enemies_killed += 1
                    e.just_died = False

                if not e.death_done:
                    new_enemies.append(e)

            self.enemies = new_enemies
        else:
            # No deaths — still clear any stale just_died flags cheaply
            for e in self.enemies:
                if e.just_died:
                    self.enemies_killed += 1
                    e.just_died = False

    # --- Collision helpers ---
    def _check_bullets(self, wm):
        # Use the alive_enemies list built once in update() — no per-call allocation
        alive_enemies = self._alive_enemies_cache
        for bullet in wm.bullets:
            if not bullet.alive:
                continue
            for enemy in alive_enemies:
                if bullet.rect.colliderect(enemy.rect):
                    enemy.take_hit(3)
                    bullet.alive = False
                    break

    def _check_grenades(self, wm):
        # Use the alive_enemies list built once in update() — no per-call allocation
        alive_enemies = self._alive_enemies_cache
        for grenade in wm.grenades:
            if not grenade.exploding:
                continue
            radius_sq = grenade.EXPLOSION_RADIUS * grenade.EXPLOSION_RADIUS
            for enemy in alive_enemies:
                dx = enemy.rect.centerx - grenade.x
                dy = enemy.rect.centery - grenade.y
                if dx * dx + dy * dy <= radius_sq:
                    enemy.take_hit(5)

    def _check_spears(self, wm):
        # Use the alive_enemies list built once in update() — no per-call allocation
        alive_enemies = self._alive_enemies_cache
        spear_rect = pygame.Rect(0, 0, 40, 8)
        for spear in wm.spears:
            if not spear.alive:
                continue
            spear_rect.x = int(spear.x) - 20
            spear_rect.y = int(spear.y) - 4
            for enemy in alive_enemies:
                if spear_rect.colliderect(enemy.rect):
                    enemy.take_hit(5)
                    spear.alive = False
                    break

    def _check_projectile_hits(self, player, health):
        """Check if any enemy projectile hit the player."""
        if health.invincible_timer > 0:
            return
        # Cache player rect to avoid repeated attribute access
        player_rect = player.rect
        # Only check enemies that have projectiles — skip empty lists entirely
        for enemy in self.enemies:
            projectiles = enemy.projectiles
            if not projectiles:
                continue
            # Check only alive projectiles — early exit on first hit
            for proj in projectiles:
                if proj.alive and proj.rect.colliderect(player_rect):
                    health.take_damage(proj.DAMAGE)
                    proj._alive = False
                    if not health.game_over:
                        health.invincible_timer = health.INVINCIBLE_FRAMES
                    return  # one hit per frame is enough

    def _check_bullets_boss(self, wm):
        if self.boss is None or not self.boss.alive:
            return
        boss_rect = self.boss.rect  # cache rect to avoid repeated attribute access
        for bullet in wm.bullets:
            if bullet.alive and bullet.rect.colliderect(boss_rect):
                self.boss.take_hit(10)  # 3× normal bullet damage during boss fight
                bullet.alive = False

    def _check_grenades_boss(self, wm):
        if self.boss is None or not self.boss.alive:
            return
        # Cache boss position to avoid repeated attribute access
        boss_cx = self.boss.rect.centerx
        boss_cy = self.boss.rect.centery
        radius_sq = 90 * 90  # EXPLOSION_RADIUS squared — inline constant
        for grenade in wm.grenades:
            if not grenade.exploding:
                continue
            dx = boss_cx - grenade.x
            dy = boss_cy - grenade.y
            if dx * dx + dy * dy <= radius_sq:
                self.boss.take_hit(18)  # 3× normal grenade damage during boss fight

    def _check_spears_boss(self, wm):
        if self.boss is None or not self.boss.alive:
            return
        # Reuse module-level scratch rect — avoids per-call allocation
        _SCRATCH_RECT.update(0, 0, 40, 8)
        for spear in wm.spears:
            if not spear.alive:
                continue
            _SCRATCH_RECT.x = int(spear.x) - 20
            _SCRATCH_RECT.y = int(spear.y) - 4
            if _SCRATCH_RECT.colliderect(self.boss.rect):
                self.boss.take_hit(18)  # 3× normal spear damage during boss fight
                spear.alive = False

    def draw(self, screen, camera):
        # Cull enemies that are entirely off-screen — avoids all the procedural
        # draw calls (circles, ellipses, polygons) for enemies the player can't see.
        # Cache camera offset to avoid repeated attribute access
        cam_offset_x = camera.offset_x
        screen_left = -cam_offset_x - ENEMY_WIDTH
        screen_right = -cam_offset_x + SCREEN_WIDTH + ENEMY_WIDTH
        for enemy in self.enemies:
            enemy_x = enemy.rect.x
            if screen_left <= enemy_x <= screen_right:
                enemy.draw(screen, camera)
        # Draw boss if present
        if self.boss is not None:
            self.boss.draw(screen, camera)


# ---------------------------------------------------------------------------
# FINAL BOSS
# ---------------------------------------------------------------------------
BOSS_WIDTH = 80
BOSS_HEIGHT = 90


class FinalBoss(Enemy):
    MAX_HP = 200
    ATTACK_DAMAGE = 10  # contact damage dealt to player (double normal enemy)
    SHOOT_COOLDOWN = 60  # fires much more frequently than normal enemies
    MULTI_SHOT_COUNT = 3  # spread shots
    PATROL_SPEED = 1
    CHASE_SPEED = 2
    DETECT_RANGE = 600  # detects player from further away
    SHOOT_RANGE_SQ = 600 * 600  # squared — avoids sqrt in shoot check

    # Jump constants — tuned so the boss clears the widest pit (220px)
    # at its chase speed of 2px/frame.
    JUMP_POWER = -14  # normal jump
    JUMP_POWER_WIDE = -18  # used when gap looks wider than ~120px

    # Class-level cached resources (initialised once, shared across instances)
    _label_font: pygame.font.Font | None = None
    _label_surf: pygame.Surface | None = None  # cached "FINAL BOSS" text surface
    _SHADOW_SURF: pygame.Surface | None = None  # override parent's enemy-sized shadow

    @classmethod
    def _get_shadow_surf(cls) -> pygame.Surface:
        if cls._SHADOW_SURF is None:
            cls._SHADOW_SURF = pygame.Surface((BOSS_WIDTH + 10, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(
                cls._SHADOW_SURF, (0, 0, 0, 80), cls._SHADOW_SURF.get_rect()
            )
        return cls._SHADOW_SURF

    @classmethod
    def _get_label_font(cls) -> pygame.font.Font:
        if cls._label_font is None:
            cls._label_font = pygame.font.Font(
                "assets/fonts/PressStart2P-Regular.ttf", 7
            )
        return cls._label_font

    # Pre-computed label rect — updated once when the label surface is first created
    _label_rect: pygame.Rect | None = None

    @classmethod
    def _get_label_surf(cls) -> pygame.Surface:
        if cls._label_surf is None:
            cls._label_surf = cls._get_label_font().render(
                "FINAL BOSS", True, (255, 200, 0)
            )
            cls._label_rect = cls._label_surf.get_rect()
        return cls._label_surf

    def __init__(self, x, y):
        super().__init__(x, y)
        self.rect = pygame.Rect(x, y, BOSS_WIDTH, BOSS_HEIGHT)
        self.hp = self.MAX_HP
        self.shoot_timer = 0
        self.just_died = False

    # Pre-computed spread offsets for MULTI_SHOT_COUNT=3: [-20°, 0°, +20°]
    _SPREAD_OFFSETS = (
        -math.radians(20),
        0.0,
        math.radians(20),
    )

    def _fire_spread(self, player):
        """Fire MULTI_SHOT_COUNT projectiles in a spread pattern."""
        dx = player.rect.centerx - self.rect.centerx
        dy = player.rect.centery - self.rect.centery
        base_angle = math.atan2(dy, dx)
        cx = self.rect.centerx
        cy = self.rect.centery
        spd = self.projectile_speed_multiplier

        projectiles = []
        for offset in self._SPREAD_OFFSETS:
            angle = base_angle + offset
            tx = cx + math.cos(angle) * 400
            ty = cy + math.sin(angle) * 400
            projectiles.append(EnemyProjectile(cx, cy, tx, ty, speed_multiplier=spd))
        return projectiles

    def _respawn_near_player(self, player, ground_segments):
        """Teleport the boss back onto the nearest ground segment ahead of the
        player, preserving current HP. Called when the boss falls into a pit."""
        # Find the ground segment whose center is closest to 300px ahead of the
        # player so the boss lands somewhere the player can still reach it.
        target_x = player.rect.centerx + 300
        best_seg = None
        best_dist = float("inf")
        for seg in ground_segments:
            dist = abs(seg.rect.centerx - target_x)
            if dist < best_dist:
                best_dist = dist
                best_seg = seg

        if best_seg is not None:
            spawn_x = best_seg.rect.centerx - BOSS_WIDTH // 2
            spawn_y = best_seg.rect.top - BOSS_HEIGHT
        else:
            # Fallback: respawn directly above the player
            spawn_x = player.rect.centerx + 200
            spawn_y = SCREEN_HEIGHT - 100 - BOSS_HEIGHT

        self.rect.x = spawn_x
        self.rect.y = spawn_y
        self.world_x = float(spawn_x)
        self.vel_y = 0
        self.on_ground = False
        # Clear in-flight projectiles so they don't ghost at the old position
        self.projectiles = []

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------
    def update(self, platforms, ground_segments, player, health):
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

        # --- Pit fall respawn ---
        # If the boss falls below the screen it respawns on the nearest ground
        # segment ahead of the player, keeping its current HP.
        if self.rect.y > SCREEN_HEIGHT + 60:
            self._respawn_near_player(player, ground_segments)
            return

        if self.hit_timer > 0:
            self.hit_timer -= 1

        # --- AI movement (always chase — boss never patrols) ---
        self._chase_on_ground(player, ground_segments, platforms)

        # --- Gravity + landing ---
        self._apply_gravity(platforms, ground_segments)

        # --- Contact attack ---
        self._try_attack_player(player, health)

        # --- Spread shooting ---
        # Use squared distance to avoid sqrt — compare against SHOOT_RANGE_SQ
        dx = self.rect.centerx - player.rect.centerx
        dy = self.rect.centery - player.rect.centery
        dist_sq = dx * dx + dy * dy
        if dist_sq <= self.SHOOT_RANGE_SQ:
            if self.shoot_timer <= 0:
                self.projectiles.extend(self._fire_spread(player))
                self.shoot_timer = self.SHOOT_COOLDOWN
            else:
                self.shoot_timer -= 1
        elif self.shoot_timer > 0:
            self.shoot_timer -= 1

        # --- Update in-flight projectiles ---
        for proj in self.projectiles:
            proj.update(ground_segments, platforms)
        # Prune dead projectiles — only rebuild list when there are dead ones
        # Check first projectile as a heuristic — if it's alive, likely all are
        if self.projectiles and not self.projectiles[0].alive:
            self.projectiles = [p for p in self.projectiles if p.alive]
        elif len(self.projectiles) > 1:
            # Fallback: check if any are dead (rare case where first is alive but others aren't)
            if any(not p.alive for p in self.projectiles):
                self.projectiles = [p for p in self.projectiles if p.alive]

        # --- Walk animation ---
        self.anim_timer += 1
        if self.anim_timer >= 8:
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4

        # --- Particles / hit flashes ---
        for p in self.particles:
            p.update()
        # Only rebuild particles list if there are dead ones — check first as heuristic
        if self.particles and not self.particles[0].alive:
            self.particles = [p for p in self.particles if p.alive]
        elif len(self.particles) > 1:
            if any(not p.alive for p in self.particles):
                self.particles = [p for p in self.particles if p.alive]

        for f in self.hit_flashes:
            f.update()
        # Only rebuild flashes list if there are dead ones — check first as heuristic
        if self.hit_flashes and not self.hit_flashes[0].alive:
            self.hit_flashes = [f for f in self.hit_flashes if f.alive]
        elif len(self.hit_flashes) > 1:
            if any(not f.alive for f in self.hit_flashes):
                self.hit_flashes = [f for f in self.hit_flashes if f.alive]

    def _has_surface_at(self, probe_x, foot_y, ground_segments, platforms):
        """Return True if there is solid ground/platform under probe_x at foot_y.

        Performance: iterates only segments whose x-range overlaps probe_x,
        which is O(n) but with an early-exit on the first hit.
        """
        # Check ground segments first — they're more common and wider
        for seg in ground_segments:
            seg_rect = seg.rect
            if seg_rect.left <= probe_x <= seg_rect.right:
                if seg_rect.top <= foot_y <= seg_rect.bottom:
                    return True
        # Check platforms only if no ground found
        for p in platforms:
            if not p.visible:
                continue
            p_rect = p.rect
            if p_rect.left <= probe_x <= p_rect.right:
                if p_rect.top <= foot_y <= p_rect.bottom + 20:
                    return True
        return False

    def _chase_on_ground(self, player, ground_segments, platforms):
        """Move toward player; jump over pits instead of stopping at the edge.

        Performance: pit-detection and gap-scan only run when on_ground is True
        (skipped entirely while airborne). The gap scan uses a coarse 16px step
        and exits as soon as solid ground is found, keeping the worst-case
        iteration count at 15 instead of the previous 30.
        """
        speed = self.CHASE_SPEED

        # Cache player center to avoid repeated attribute access
        player_cx = player.rect.centerx
        if player_cx > self.rect.centerx:
            direction = 1
            self.facing_right = True
        else:
            direction = -1
            self.facing_right = False

        next_x = self.world_x + speed * direction

        # Only do pit detection when on the ground — skip entirely when airborne
        if self.on_ground:
            # Probe just past the leading foot edge at ground level.
            foot_y = self.rect.bottom + 4
            probe_x = next_x + (BOSS_WIDTH if direction > 0 else 0)

            has_ground_ahead = self._has_surface_at(
                probe_x, foot_y, ground_segments, platforms
            )

            if not has_ground_ahead:
                # Measure how wide the gap is so we can pick the right jump power.
                # Scan forward up to 240px in 16px steps (15 iterations max).
                gap_width = 0
                scan_step = 16
                for i in range(1, 16):  # up to 240px
                    sx = probe_x + direction * scan_step * i
                    if self._has_surface_at(sx, foot_y, ground_segments, platforms):
                        gap_width = scan_step * i
                        break

                # Choose jump power based on gap width
                self.vel_y = (
                    self.JUMP_POWER_WIDE if gap_width > 120 else self.JUMP_POWER
                )
                self.on_ground = False

        # Move forward whether jumping or walking
        self.world_x = next_x
        self.rect.x = int(self.world_x)

    def draw(self, screen, camera):
        for f in self.hit_flashes:
            f.draw(screen, camera)
        for p in self.particles:
            p.draw(screen, camera)

        if not self.alive:
            return

        dr = camera.apply(self.rect)
        cx, cy = dr.centerx, dr.centery
        w, h = BOSS_WIDTH, BOSS_HEIGHT

        # Use pre-computed tuple — no list allocation per frame
        leg_bob = _BOSS_LEG_BOB[self.anim_frame]

        # Shadow — reuse pre-baked surface
        screen.blit(self._get_shadow_surf(), (dr.x - 5, dr.bottom - 5))

        # Body — dark purple/gold boss colours
        body_col = (255, 200, 0) if self.hit_timer > 0 else (120, 0, 180)
        outline_col = (60, 0, 100)
        # Reuse module-level scratch rects — no per-frame allocation
        _SCRATCH_RECT.update(dr.x - 2, dr.y + 14, w + 4, h - 20)
        pygame.draw.ellipse(screen, outline_col, _SCRATCH_RECT)
        _SCRATCH_RECT.update(dr.x, dr.y + 16, w, h - 24)
        pygame.draw.ellipse(screen, body_col, _SCRATCH_RECT)
        # Belly
        _SCRATCH_RECT.update(dr.x + w // 4, dr.y + 24, w // 2, (h - 24) // 2)
        pygame.draw.ellipse(
            screen,
            (160, 0, 220) if self.hit_timer == 0 else (255, 220, 100),
            _SCRATCH_RECT,
        )

        # Head
        head_r = 28
        hx, hy = cx, dr.y + head_r + 4
        pygame.draw.circle(screen, outline_col, (hx, hy), head_r + 2)
        pygame.draw.circle(screen, body_col, (hx, hy), head_r)

        # Crown spikes
        crown_col = (255, 200, 0)
        spike_pts = [
            [
                (hx - 22, hy - head_r),
                (hx - 16, hy - head_r - 20),
                (hx - 10, hy - head_r),
            ],
            [
                (hx - 4, hy - head_r - 4),
                (hx, hy - head_r - 28),
                (hx + 4, hy - head_r - 4),
            ],
            [
                (hx + 10, hy - head_r),
                (hx + 16, hy - head_r - 20),
                (hx + 22, hy - head_r),
            ],
        ]
        for pts in spike_pts:
            pygame.draw.polygon(screen, crown_col, pts)

        # Eyes — glowing red
        for ex_sign in [1, -1]:
            ex = hx + ex_sign * 10
            ey = hy - 4
            pygame.draw.circle(screen, (255, 0, 0), (ex, ey), 8)
            pygame.draw.circle(screen, (255, 100, 0), (ex, ey), 5)
            pygame.draw.circle(screen, (255, 255, 255), (ex - 2, ey - 2), 2)

        # Legs — reuse scratch rects
        leg_col = (80, 0, 120)
        leg_y_base = dr.bottom - 12
        _SCRATCH_RECT.update(dr.x + 6, leg_y_base + leg_bob, 18, 14)
        pygame.draw.ellipse(screen, leg_col, _SCRATCH_RECT)
        _SCRATCH_RECT.update(dr.x + w - 24, leg_y_base - leg_bob, 18, 14)
        pygame.draw.ellipse(screen, leg_col, _SCRATCH_RECT)

        # Arms — reuse scratch rects
        arm_col = (80, 0, 120)
        _SCRATCH_RECT.update(dr.x - 8, dr.y + 32 + leg_bob // 2, 14, 24)
        pygame.draw.ellipse(screen, arm_col, _SCRATCH_RECT)
        _SCRATCH_RECT.update(dr.right - 6, dr.y + 32 - leg_bob // 2, 14, 24)
        pygame.draw.ellipse(screen, arm_col, _SCRATCH_RECT)

        # HP bar — always visible for boss (reuse class-level rects)
        bar_w = w + 20
        bar_h = 8
        bar_x = dr.x - 10
        bar_y = dr.y - 18
        Enemy._DRAW_RECT_B.update(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(screen, (40, 0, 60), Enemy._DRAW_RECT_B, border_radius=4)
        fill_w = int(bar_w * (self.hp / self.MAX_HP))
        if fill_w > 0:
            fill_col = (255, 200, 0) if self.hp > self.MAX_HP * 0.5 else (255, 60, 0)
            Enemy._DRAW_RECT_C.update(bar_x, bar_y, fill_w, bar_h)
            pygame.draw.rect(screen, fill_col, Enemy._DRAW_RECT_C, border_radius=4)
        pygame.draw.rect(screen, (200, 0, 200), Enemy._DRAW_RECT_B, 2, border_radius=4)

        # BOSS label — use cached surface and cached rect (no per-frame allocation)
        label = self._get_label_surf()
        lr = self._label_rect
        lr.centerx = cx
        lr.centery = bar_y - 10
        screen.blit(label, lr)

        # Projectiles
        for proj in self.projectiles:
            proj.draw(screen, camera)
