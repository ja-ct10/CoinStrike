import pygame
import math
import random
from settings import *


# ---------------------------------------------------------------------------
# AMMO LIMITS
# ---------------------------------------------------------------------------
GUN_MAX_AMMO = 35
GRENADE_MAX_AMMO = 15
SPEAR_MAX_AMMO = 10


# ---------------------------------------------------------------------------
# BULLET  (Gun — fires on F key)
# ---------------------------------------------------------------------------
class Bullet:
    SPEED = 14
    WIDTH = 12
    HEIGHT = 5

    def __init__(self, x, y, facing_right):
        self.dx = self.SPEED if facing_right else -self.SPEED
        self.rect = pygame.Rect(x, y, self.WIDTH, self.HEIGHT)
        self.alive = True

    def update(self, ground_segments, platforms):
        self.rect.x += self.dx

        if self.rect.right < -200 or self.rect.left > SCREEN_WIDTH * 6 + 200:
            self.alive = False
            return

        for seg in ground_segments:
            if self.rect.colliderect(seg.rect):
                self.alive = False
                return
        for p in platforms:
            if self.rect.colliderect(p.rect):
                self.alive = False
                return

    def draw(self, screen, camera):
        if not self.alive:
            return
        draw_rect = camera.apply(self.rect)
        glow_surf = pygame.Surface((self.WIDTH + 8, self.HEIGHT + 8), pygame.SRCALPHA)
        pygame.draw.ellipse(glow_surf, (0, 255, 255, 60), glow_surf.get_rect())
        screen.blit(glow_surf, (draw_rect.x - 4, draw_rect.y - 4))
        pygame.draw.rect(screen, (0, 255, 255), draw_rect, border_radius=2)
        core = pygame.Rect(
            draw_rect.x + 2, draw_rect.y + 1, self.WIDTH - 4, self.HEIGHT - 2
        )
        pygame.draw.rect(screen, (255, 255, 255), core, border_radius=1)


# ---------------------------------------------------------------------------
# PARTICLE
# ---------------------------------------------------------------------------
class Particle:
    def __init__(self, x, y, color, speed=None, angle=None, lifetime=None):
        angle = angle if angle is not None else random.uniform(0, 2 * math.pi)
        speed = speed if speed is not None else random.uniform(2, 7)
        self.dx = math.cos(angle) * speed
        self.dy = math.sin(angle) * speed
        self.x = float(x)
        self.y = float(y)
        self.color = color
        self.lifetime = lifetime if lifetime is not None else random.randint(18, 36)
        self.max_lifetime = self.lifetime
        self.size = random.randint(3, 7)

    def update(self):
        self.x += self.dx
        self.y += self.dy
        self.dy += 0.18
        self.dx *= 0.96
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
# GRENADE
# ---------------------------------------------------------------------------
EXPLOSION_COLORS = [
    (255, 80, 0),
    (255, 200, 0),
    (255, 255, 100),
    (255, 120, 40),
    (200, 40, 0),
]


class Grenade:
    THROW_SPEED_X = 9
    THROW_SPEED_Y = -13
    GRAVITY = 0.5
    RADIUS = 8
    FUSE_FRAMES = 120
    EXPLOSION_RADIUS = 90

    def __init__(self, x, y, facing_right):
        self.x = float(x)
        self.y = float(y)
        self.dx = self.THROW_SPEED_X if facing_right else -self.THROW_SPEED_X
        self.dy = float(self.THROW_SPEED_Y)
        self.alive = True
        self.exploding = False
        self.explosion_frame = 0
        self.explosion_max = 18
        self.fuse = self.FUSE_FRAMES
        self.particles = []
        self.rotation = 0

    @property
    def rect(self):
        return pygame.Rect(
            int(self.x) - self.RADIUS,
            int(self.y) - self.RADIUS,
            self.RADIUS * 2,
            self.RADIUS * 2,
        )

    def _explode(self):
        self.exploding = True
        self.dx = self.dy = 0
        for _ in range(40):
            self.particles.append(
                Particle(self.x, self.y, random.choice(EXPLOSION_COLORS))
            )
        for _ in range(15):
            self.particles.append(
                Particle(
                    self.x,
                    self.y,
                    (160, 160, 160),
                    speed=random.uniform(1, 4),
                    lifetime=random.randint(30, 50),
                )
            )

    def update(self, ground_segments, platforms):
        if self.exploding:
            self.explosion_frame += 1
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.alive]
            if self.explosion_frame > self.explosion_max and not self.particles:
                self.alive = False
            return

        self.fuse -= 1
        self.dy += self.GRAVITY
        self.x += self.dx
        self.y += self.dy
        self.rotation += self.dx * 3
        self.dx *= 0.99

        for seg in ground_segments:
            if self.rect.colliderect(seg.rect):
                self._explode()
                return
        for p in platforms:
            if self.rect.colliderect(p.rect) and self.dy > 0:
                self._explode()
                return
        if self.fuse <= 0:
            self._explode()

    def draw(self, screen, camera):
        if not self.alive:
            return
        for p in self.particles:
            p.draw(screen, camera)

        if self.exploding:
            progress = self.explosion_frame / self.explosion_max
            radius = int(self.EXPLOSION_RADIUS * progress)
            alpha = int(220 * (1 - progress))
            if alpha > 0:
                world_rect = pygame.Rect(
                    int(self.x) - radius, int(self.y) - radius, radius * 2, radius * 2
                )
                ring_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    ring_surf, (255, 160, 0, alpha), (radius, radius), radius, 4
                )
                screen.blit(ring_surf, camera.apply(world_rect))
            return

        draw_rect = camera.apply(self.rect)
        cx, cy = draw_rect.centerx, draw_rect.centery
        pygame.draw.circle(screen, (60, 140, 60), (cx, cy), self.RADIUS)
        pygame.draw.circle(screen, (80, 200, 80), (cx, cy), self.RADIUS, 2)
        pygame.draw.line(screen, (40, 100, 40), (cx - 4, cy), (cx + 4, cy), 1)
        pygame.draw.line(screen, (40, 100, 40), (cx, cy - 4), (cx, cy + 4), 1)
        pygame.draw.rect(
            screen, (200, 200, 60), pygame.Rect(cx - 3, cy - self.RADIUS - 5, 6, 5)
        )
        if self.fuse > 0 and (self.fuse // 4) % 2 == 0:
            pygame.draw.circle(screen, (255, 200, 0), (cx, cy - self.RADIUS - 5), 3)


# ---------------------------------------------------------------------------
# SPEAR
# ---------------------------------------------------------------------------
class Spear:
    THROW_SPEED_X = 12
    THROW_SPEED_Y = -8
    GRAVITY = 0.35
    LENGTH = 32
    THICKNESS = 4

    def __init__(self, x, y, facing_right):
        self.x = float(x)
        self.y = float(y)
        self.dx = self.THROW_SPEED_X if facing_right else -self.THROW_SPEED_X
        self.dy = float(self.THROW_SPEED_Y)
        self.facing_right = facing_right
        self.stuck = False
        self.alive = True
        self.stuck_timer = 180
        self.particles = []

    @property
    def rect(self):
        return pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)

    def _get_angle(self):
        return math.degrees(math.atan2(self.dy, self.dx))

    def _stick(self):
        self.stuck = True
        self.dx = self.dy = 0
        for _ in range(12):
            self.particles.append(
                Particle(
                    self.x,
                    self.y,
                    (200, 200, 60),
                    speed=random.uniform(2, 5),
                    lifetime=random.randint(10, 20),
                )
            )

    def update(self, ground_segments, platforms):
        if self.stuck:
            self.stuck_timer -= 1
            for p in self.particles:
                p.update()
            self.particles = [p for p in self.particles if p.alive]
            if self.stuck_timer <= 0:
                self.alive = False
            return

        self.dy += self.GRAVITY
        self.x += self.dx
        self.y += self.dy

        for seg in ground_segments:
            if self.rect.colliderect(seg.rect):
                self.y = seg.rect.top - 2
                self._stick()
                return
        for p in platforms:
            if self.rect.colliderect(p.rect):
                self.y = p.rect.top - 2
                self._stick()
                return

        if self.x < -400 or self.x > SCREEN_WIDTH * 6 + 400:
            self.alive = False

    def draw(self, screen, camera):
        if not self.alive:
            return
        for p in self.particles:
            p.draw(screen, camera)

        world_rect = pygame.Rect(
            int(self.x) - self.LENGTH // 2,
            int(self.y) - self.THICKNESS // 2,
            self.LENGTH,
            self.THICKNESS,
        )
        draw_rect = camera.apply(world_rect)
        cx, cy = draw_rect.centerx, draw_rect.centery

        angle = (-15 if self.facing_right else 165) if self.stuck else self._get_angle()
        half = self.LENGTH // 2
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)

        tip_x = cx + cos_a * half
        tip_y = cy + sin_a * half
        tail_x = cx - cos_a * half
        tail_y = cy - sin_a * half

        pygame.draw.line(
            screen,
            (20, 10, 40),
            (int(tail_x) + 2, int(tail_y) + 2),
            (int(tip_x) + 2, int(tip_y) + 2),
            self.THICKNESS,
        )
        pygame.draw.line(
            screen,
            (160, 100, 40),
            (int(tail_x), int(tail_y)),
            (int(tip_x), int(tip_y)),
            self.THICKNESS,
        )
        pygame.draw.line(
            screen,
            (200, 140, 70),
            (int(tail_x), int(tail_y)),
            (int(tip_x), int(tip_y)),
            max(1, self.THICKNESS - 2),
        )

        tip_len = 10
        tip2_x = cx + cos_a * (half + tip_len)
        tip2_y = cy + sin_a * (half + tip_len)
        pygame.draw.line(
            screen,
            (0, 220, 220),
            (int(tip_x), int(tip_y)),
            (int(tip2_x), int(tip2_y)),
            self.THICKNESS + 1,
        )
        pygame.draw.line(
            screen,
            (255, 255, 255),
            (int(tip_x), int(tip_y)),
            (int(tip2_x), int(tip2_y)),
            1,
        )

        perp_x = -sin_a * 5
        perp_y = cos_a * 5
        pygame.draw.line(
            screen,
            (220, 60, 60),
            (int(tail_x), int(tail_y)),
            (int(tail_x + perp_x), int(tail_y + perp_y)),
            2,
        )
        pygame.draw.line(
            screen,
            (220, 60, 60),
            (int(tail_x), int(tail_y)),
            (int(tail_x - perp_x), int(tail_y - perp_y)),
            2,
        )


# ---------------------------------------------------------------------------
# WEAPON MANAGER
# ---------------------------------------------------------------------------
class WeaponManager:
    GUN_COOLDOWN = 15
    THROW_COOLDOWN = 45

    def __init__(self):
        self.owned = set()
        self.ammo = {}  # {"gun": 30, "grenade": 10, "spear": 5}
        self.bullets = []
        self.grenades = []
        self.spears = []
        self._gun_cooldown = 0
        self._throw_cooldown = 0

        # Weapon display images (loaded once)
        self._images = {}
        for name, path in [
            ("gun", "assets/gun.png"),
            ("spear", "assets/spear.png"),
            ("grenade", "assets/grenade.png"),
        ]:
            try:
                img = pygame.image.load(path).convert_alpha()
                self._images[name] = pygame.transform.scale(img, (36, 36))
            except Exception:
                self._images[name] = None

        self._ammo_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 8)
        self._label_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 7)

    def grant(self, weapon_name):
        """Grant weapon and set ammo. Buying again tops up ammo."""
        self.owned.add(weapon_name)
        limits = {
            "gun": GUN_MAX_AMMO,
            "grenade": GRENADE_MAX_AMMO,
            "spear": SPEAR_MAX_AMMO,
        }
        self.ammo[weapon_name] = limits.get(weapon_name, 0)

    def _has_ammo(self, weapon_name):
        return self.ammo.get(weapon_name, 0) > 0

    def _use_ammo(self, weapon_name):
        if weapon_name in self.ammo:
            self.ammo[weapon_name] = max(0, self.ammo[weapon_name] - 1)
            if self.ammo[weapon_name] == 0:
                self.owned.discard(weapon_name)

    def handle_keydown(self, event_key, player):
        if event_key == pygame.K_f and "gun" in self.owned:
            if self._gun_cooldown <= 0 and self._has_ammo("gun"):
                bx = player.rect.right if player.facing_right else player.rect.left
                by = player.rect.centery - 4
                self.bullets.append(Bullet(bx, by, player.facing_right))
                self._use_ammo("gun")
                self._gun_cooldown = self.GUN_COOLDOWN

        if event_key == pygame.K_t:
            if self._throw_cooldown <= 0:
                cx, cy = player.rect.centerx, player.rect.centery
                if "grenade" in self.owned and self._has_ammo("grenade"):
                    self.grenades.append(Grenade(cx, cy, player.facing_right))
                    self._use_ammo("grenade")
                    self._throw_cooldown = self.THROW_COOLDOWN
                elif "spear" in self.owned and self._has_ammo("spear"):
                    self.spears.append(Spear(cx, cy, player.facing_right))
                    self._use_ammo("spear")
                    self._throw_cooldown = self.THROW_COOLDOWN

    def update(self, ground_segments, platforms):
        if self._gun_cooldown > 0:
            self._gun_cooldown -= 1
        if self._throw_cooldown > 0:
            self._throw_cooldown -= 1

        for b in self.bullets:
            b.update(ground_segments, platforms)
        for g in self.grenades:
            g.update(ground_segments, platforms)
        for s in self.spears:
            s.update(ground_segments, platforms)

        self.bullets = [b for b in self.bullets if b.alive]
        self.grenades = [g for g in self.grenades if g.alive]
        self.spears = [s for s in self.spears if s.alive]

    def draw(self, screen, camera):
        for b in self.bullets:
            b.draw(screen, camera)
        for g in self.grenades:
            g.draw(screen, camera)
        for s in self.spears:
            s.draw(screen, camera)

    def draw_held_weapon(self, screen, player, camera):
        """Draw the weapon the player is currently holding, attached to their hand."""
        held = None
        if "gun" in self.owned:
            held = "gun"
        elif "spear" in self.owned:
            held = "spear"
        elif "grenade" in self.owned:
            held = "grenade"

        if held is None or self._images.get(held) is None:
            return

        img = self._images[held]
        # Flip horizontally if facing left
        if not player.facing_right:
            img = pygame.transform.flip(img, True, False)

        player_draw = camera.apply(player.rect)
        if player.facing_right:
            wx = player_draw.right - 8
        else:
            wx = player_draw.left - img.get_width() + 8
        wy = player_draw.centery - img.get_height() // 2 + 10

        screen.blit(img, (wx, wy))

    def draw_ammo_hud(self, screen):
        """Draw ammo counter bar bottom-left of screen."""
        if not self.owned:
            return

        font = self._ammo_font
        lfont = self._label_font

        panel_x = 10
        panel_y = SCREEN_HEIGHT - 10
        slot_w, slot_h = 80, 52
        slot_gap = 8

        order = [
            w for w in ["gun", "spear", "grenade"] if w in self.owned or w in self.ammo
        ]

        for i, weapon in enumerate(order):
            if weapon not in self.owned and weapon not in self.ammo:
                continue
            ammo_left = self.ammo.get(weapon, 0)
            sx = panel_x + i * (slot_w + slot_gap)
            sy = panel_y - slot_h

            # Slot background
            slot_surf = pygame.Surface((slot_w, slot_h), pygame.SRCALPHA)
            slot_surf.fill((10, 6, 28, 200))
            screen.blit(slot_surf, (sx, sy))

            # Border — cyan if active (owned + ammo > 0), grey if empty
            active = weapon in self.owned and ammo_left > 0
            border_col = (0, 200, 220) if active else (80, 80, 80)
            pygame.draw.rect(screen, border_col, pygame.Rect(sx, sy, slot_w, slot_h), 2)

            # Weapon icon
            img = self._images.get(weapon)
            if img:
                icon = pygame.transform.scale(img, (28, 28))
                if not active:
                    # Desaturate by darkening
                    dark = icon.copy()
                    dark.fill((60, 60, 60, 0), special_flags=pygame.BLEND_RGBA_MULT)
                    icon = dark
                screen.blit(icon, (sx + 4, sy + 4))

            # Weapon label
            label_surf = lfont.render(
                weapon.upper(), True, (200, 220, 255) if active else (80, 80, 80)
            )
            screen.blit(label_surf, (sx + 36, sy + 6))

            # Ammo count
            ammo_color = (
                (255, 221, 68)
                if ammo_left > 5
                else (255, 140, 0) if ammo_left > 0 else (180, 60, 60)
            )
            ammo_surf = font.render(str(ammo_left), True, ammo_color)
            screen.blit(ammo_surf, (sx + 36, sy + 22))

            # Key hint
            key = "F" if weapon == "gun" else "T"
            hint = lfont.render(f"[{key}]", True, (120, 120, 160))
            screen.blit(hint, (sx + 36, sy + 38))
