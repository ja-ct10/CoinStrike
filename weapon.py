import pygame
import math
import random
from settings import *
from utils import resource_path


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

    # Pre-baked glow surface — allocated once, reused every draw call
    _GLOW_SURF: "pygame.Surface | None" = None

    @classmethod
    def _get_glow_surf(cls) -> pygame.Surface:
        if cls._GLOW_SURF is None:
            cls._GLOW_SURF = pygame.Surface(
                (cls.WIDTH + 8, cls.HEIGHT + 8), pygame.SRCALPHA
            )
            pygame.draw.ellipse(
                cls._GLOW_SURF, (0, 255, 255, 60), cls._GLOW_SURF.get_rect()
            )
        return cls._GLOW_SURF

    def __init__(self, x, y, facing_right):
        self.dx = self.SPEED if facing_right else -self.SPEED
        self.rect = pygame.Rect(x, y, self.WIDTH, self.HEIGHT)
        self.alive = True
        # Track spawn position to kill bullet after it travels too far
        self._spawn_x = x
        # Reusable core rect — updated in-place in draw()
        self._core_rect = pygame.Rect(0, 0, self.WIDTH - 4, self.HEIGHT - 2)

    def update(self, ground_segments, platforms):
        self.rect.x += self.dx

        # Kill after travelling 1200px — far enough to cross the screen twice
        if abs(self.rect.x - self._spawn_x) > 1200:
            self.alive = False
            return

        # Only collide with ground (not platforms) — bullets fly over/through platforms
        for seg in ground_segments:
            if self.rect.colliderect(seg.rect):
                self.alive = False
                return

    def draw(self, screen, camera):
        if not self.alive:
            return
        draw_rect = camera.apply(self.rect)
        screen.blit(self._get_glow_surf(), (draw_rect.x - 4, draw_rect.y - 4))
        pygame.draw.rect(screen, (0, 255, 255), draw_rect, border_radius=2)
        # Reuse pre-allocated core rect — update in-place
        self._core_rect.x = draw_rect.x + 2
        self._core_rect.y = draw_rect.y + 1
        pygame.draw.rect(screen, (255, 255, 255), self._core_rect, border_radius=1)


# ---------------------------------------------------------------------------
# PARTICLE
# ---------------------------------------------------------------------------
class Particle:
    # Surface cache keyed by (size, r, g, b, alpha_quantised) — same pattern as
    # EnemyParticle in enemy.py. Quantising alpha to steps of 16 keeps the cache
    # small (16 buckets) at the cost of imperceptible banding.
    _surf_cache: dict = {}
    # Reusable world rect — updated in-place to avoid per-frame allocation
    _WORLD_RECT = pygame.Rect(0, 0, 0, 0)

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
        # Quantise alpha to 16-step buckets to maximise cache hits
        alpha_q = (alpha >> 4) << 4
        key = (size, r, g, b, alpha_q)
        surf = Particle._surf_cache.get(key)
        if surf is None:
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (r, g, b, alpha_q), (size, size), size)
            # Evict oldest quarter when cache exceeds 256 entries
            if len(Particle._surf_cache) > 256:
                evict = list(Particle._surf_cache.keys())[:64]
                for k in evict:
                    del Particle._surf_cache[k]
            Particle._surf_cache[key] = surf
        # Reuse class-level rect — update in-place
        Particle._WORLD_RECT.x = int(self.x) - size
        Particle._WORLD_RECT.y = int(self.y) - size
        Particle._WORLD_RECT.width = size * 2
        Particle._WORLD_RECT.height = size * 2
        screen.blit(surf, camera.apply(Particle._WORLD_RECT))


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

    # Explosion ring surface cache keyed by (radius, alpha_quantised)
    _RING_CACHE: dict = {}
    # Reusable world rect for explosion ring blit — updated in-place
    _RING_WORLD_RECT = pygame.Rect(0, 0, 0, 0)

    # Pre-baked grenade body surface — drawn once, reused every frame
    _BODY_SURF: "pygame.Surface | None" = None

    @classmethod
    def _get_body_surf(cls) -> pygame.Surface:
        """Pre-render the grenade body to avoid multiple draw calls per frame."""
        if cls._BODY_SURF is None:
            size = cls.RADIUS * 2
            cls._BODY_SURF = pygame.Surface((size, size), pygame.SRCALPHA)
            r = cls.RADIUS
            # Body circle
            pygame.draw.circle(cls._BODY_SURF, (60, 140, 60), (r, r), r)
            pygame.draw.circle(cls._BODY_SURF, (80, 200, 80), (r, r), r, 2)
            # Cross lines
            pygame.draw.line(cls._BODY_SURF, (40, 100, 40), (r - 4, r), (r + 4, r), 1)
            pygame.draw.line(cls._BODY_SURF, (40, 100, 40), (r, r - 4), (r, r + 4), 1)
        return cls._BODY_SURF

    def __init__(self, x, y, facing_right, target=None):
        self.x = float(x)
        self.y = float(y)
        self._spawn_x = x  # used for travel-distance culling
        self.alive = True
        self.exploding = False
        self.explosion_frame = 0
        self.explosion_max = 18
        self.fuse = self.FUSE_FRAMES
        self.particles = []
        self.rotation = 0
        # Reusable rect — updated in-place to avoid per-frame allocation
        self._rect = pygame.Rect(
            int(self.x) - self.RADIUS,
            int(self.y) - self.RADIUS,
            self.RADIUS * 2,
            self.RADIUS * 2,
        )

        if target is not None:
            # Direct hit trajectory: calculate velocity to reach target using ballistic arc
            # that accounts for gravity. Uses the standard projectile motion formula.
            tx, ty = target
            dx = tx - x
            dy = ty - y

            # Calculate the optimal throw angle and speed to hit the target
            # Using the formula: t = dx / vx, and solving for vy given gravity
            # We want: ty = y + vy*t + 0.5*g*t²

            # Use a fixed horizontal speed and calculate vertical speed needed
            horiz_dist = abs(dx)
            if horiz_dist > 0:
                # Time to reach target horizontally
                t = horiz_dist / self.THROW_SPEED_X
                # Vertical velocity needed: vy = (dy - 0.5*g*t²) / t
                vy_needed = (dy - 0.5 * self.GRAVITY * t * t) / t

                self.dx = self.THROW_SPEED_X if dx >= 0 else -self.THROW_SPEED_X
                self.dy = float(vy_needed)
            else:
                # Target is directly above/below - throw straight
                self.dx = self.THROW_SPEED_X if facing_right else -self.THROW_SPEED_X
                self.dy = float(self.THROW_SPEED_Y)
        else:
            self.dx = self.THROW_SPEED_X if facing_right else -self.THROW_SPEED_X
            self.dy = float(self.THROW_SPEED_Y)

    @property
    def rect(self):
        # Update in-place — no allocation
        self._rect.x = int(self.x) - self.RADIUS
        self._rect.y = int(self.y) - self.RADIUS
        return self._rect

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

        # Kill if it travels more than 1200px horizontally from spawn
        if abs(self.x - self._spawn_x) > 1200:
            self._explode()
            return

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
                # Quantise alpha to 8-step buckets for better cache hit rate
                alpha_q = (alpha >> 3) << 3
                ring_key = (radius, alpha_q)
                ring_surf = Grenade._RING_CACHE.get(ring_key)
                if ring_surf is None:
                    ring_surf = pygame.Surface(
                        (radius * 2, radius * 2), pygame.SRCALPHA
                    )
                    pygame.draw.circle(
                        ring_surf, (255, 160, 0, alpha_q), (radius, radius), radius, 4
                    )
                    # Keep cache bounded — explosion lasts 18 frames so this stays tiny
                    if len(Grenade._RING_CACHE) > 64:
                        evict = list(Grenade._RING_CACHE.keys())[:16]
                        for k in evict:
                            del Grenade._RING_CACHE[k]
                    Grenade._RING_CACHE[ring_key] = ring_surf
                # Reuse class-level world rect — update in-place
                Grenade._RING_WORLD_RECT.x = int(self.x) - radius
                Grenade._RING_WORLD_RECT.y = int(self.y) - radius
                Grenade._RING_WORLD_RECT.width = radius * 2
                Grenade._RING_WORLD_RECT.height = radius * 2
                screen.blit(ring_surf, camera.apply(Grenade._RING_WORLD_RECT))
            return

        draw_rect = camera.apply(self.rect)
        cx, cy = draw_rect.centerx, draw_rect.centery

        # Blit pre-rendered grenade body — single blit instead of 4 draw calls
        body_surf = self._get_body_surf()
        screen.blit(body_surf, (cx - self.RADIUS, cy - self.RADIUS))

        # Fuse pin (changes per frame so can't be cached)
        pygame.draw.rect(screen, (200, 200, 60), (cx - 3, cy - self.RADIUS - 5, 6, 5))
        if self.fuse > 0 and (self.fuse // 4) % 2 == 0:
            pygame.draw.circle(screen, (255, 200, 0), (cx, cy - self.RADIUS - 5), 3)


# ---------------------------------------------------------------------------
# SPEAR
# ---------------------------------------------------------------------------
class Spear:
    THROW_SPEED_X = 14
    THROW_SPEED_Y = 0  # horizontal throw — no upward arc
    GRAVITY = 0.15  # very slight drop over distance
    LENGTH = 32
    THICKNESS = 4

    def __init__(self, x, y, facing_right, target=None):
        self.x = float(x)
        self.y = float(y)
        self.facing_right = facing_right
        self.stuck = False
        self.alive = True
        self.stuck_timer = 180
        self.particles = []
        self._spawn_x = x  # used for travel-distance culling
        # Reusable rect — updated in-place to avoid per-frame allocation
        self._rect = pygame.Rect(int(self.x) - 4, int(self.y) - 4, 8, 8)
        # Reusable world rect for draw — updated in-place
        self._world_rect = pygame.Rect(0, 0, self.LENGTH, self.THICKNESS)

        if target is not None:
            # Aim directly at the target using a normalised direction vector,
            # scaled to THROW_SPEED_X so the spear travels at a consistent speed.
            tx, ty = target
            dx = tx - x
            dy = ty - y
            dist = math.sqrt(dx * dx + dy * dy) or 1.0
            speed = math.sqrt(self.THROW_SPEED_X**2 + self.THROW_SPEED_Y**2)
            # Use full throw speed magnitude along the aim vector
            speed = max(self.THROW_SPEED_X, speed)
            self.dx = (dx / dist) * speed
            self.dy = (dy / dist) * speed
        else:
            self.dx = self.THROW_SPEED_X if facing_right else -self.THROW_SPEED_X
            self.dy = float(self.THROW_SPEED_Y)

    @property
    def rect(self):
        # Update in-place — no allocation
        self._rect.x = int(self.x) - 4
        self._rect.y = int(self.y) - 4
        return self._rect

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

        if self.x < self._spawn_x - 1200 or self.x > self._spawn_x + 1200:
            self.alive = False

    def draw(self, screen, camera):
        if not self.alive:
            return
        for p in self.particles:
            p.draw(screen, camera)

        # Reuse pre-allocated world rect — update in-place
        self._world_rect.x = int(self.x) - self.LENGTH // 2
        self._world_rect.y = int(self.y) - self.THICKNESS // 2
        draw_rect = camera.apply(self._world_rect)
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
        self.weapons_bought = 0  # Track weapons purchased for mission progress

        # Weapon display images (loaded once)
        self._images = {}
        for name, path in [
            ("gun", "assets/gun.png"),
            ("spear", "assets/spear.png"),
            ("grenade", "assets/grenade.png"),
        ]:
            try:
                img = pygame.image.load(resource_path(path)).convert_alpha()
                self._images[name] = pygame.transform.scale(img, (36, 36))
            except Exception:
                self._images[name] = None

        # Pre-flipped images — avoids pygame.transform.flip() every draw call
        self._images_flipped = {
            name: pygame.transform.flip(img, True, False)
            for name, img in self._images.items()
            if img is not None
        }

        # HUD slot backgrounds — pre-rendered once per (active) state
        # keyed by (weapon_name, active: bool)
        slot_w, slot_h = 80, 52
        self._slot_bg_surfs: dict = {}
        for active in (True, False):
            surf = pygame.Surface((slot_w, slot_h), pygame.SRCALPHA)
            surf.fill((10, 6, 28, 200))
            self._slot_bg_surfs[active] = surf

        # HUD weapon icons — pre-scaled to 28×28, both active and inactive variants
        # keyed by (weapon_name, active: bool)
        self._hud_icons: dict = {}
        for name, img in self._images.items():
            if img is None:
                self._hud_icons[(name, True)] = None
                self._hud_icons[(name, False)] = None
                continue
            icon_active = pygame.transform.scale(img, (28, 28))
            icon_inactive = icon_active.copy()
            icon_inactive.fill((60, 60, 60, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self._hud_icons[(name, True)] = icon_active
            self._hud_icons[(name, False)] = icon_inactive

        # HUD text surfaces — pre-rendered; ammo count re-rendered only when it changes
        # keyed by weapon_name
        self._hud_label_surfs: dict = {}  # weapon_name → (active_surf, inactive_surf)
        self._hud_hint_surfs: dict = {}  # weapon_name → surf
        self._hud_ammo_surfs: dict = {}  # (weapon_name, ammo_value) → surf
        # Reusable slot rect — updated in-place in draw_ammo_hud
        self._slot_rect = pygame.Rect(0, 0, slot_w, slot_h)

        self._ammo_font = pygame.font.Font(
            resource_path("assets/fonts/PressStart2P-Regular.ttf"), 8
        )
        self._label_font = pygame.font.Font(
            resource_path("assets/fonts/PressStart2P-Regular.ttf"), 7
        )

        # Pre-render static label and hint surfaces now that fonts are ready
        for name in ("gun", "spear", "grenade"):
            key_hint = "F" if name == "gun" else "T"
            self._hud_label_surfs[name] = (
                self._label_font.render(name.upper(), True, (200, 220, 255)),  # active
                self._label_font.render(name.upper(), True, (80, 80, 80)),  # inactive
            )
            self._hud_hint_surfs[name] = self._label_font.render(
                f"[{key_hint}]", True, (120, 120, 160)
            )

    def grant(self, weapon_name):
        """Grant weapon and set ammo. Buying again tops up ammo."""
        self.owned.add(weapon_name)
        limits = {
            "gun": GUN_MAX_AMMO,
            "grenade": GRENADE_MAX_AMMO,
            "spear": SPEAR_MAX_AMMO,
        }
        self.ammo[weapon_name] = limits.get(weapon_name, 0)
        self.weapons_bought += 1

    def _has_ammo(self, weapon_name):
        return self.ammo.get(weapon_name, 0) > 0

    def _use_ammo(self, weapon_name):
        if weapon_name in self.ammo:
            self.ammo[weapon_name] = max(0, self.ammo[weapon_name] - 1)
            if self.ammo[weapon_name] == 0:
                self.owned.discard(weapon_name)

    def handle_keydown(self, event_key, player, enemies=None, boss=None):
        if event_key == pygame.K_f and "gun" in self.owned:
            if self._gun_cooldown <= 0 and self._has_ammo("gun"):
                bx = player.rect.right if player.facing_right else player.rect.left
                # Spawn at upper-chest height — well above any platform the player stands on
                by = player.rect.top + (player.rect.height // 3)
                self.bullets.append(Bullet(bx, by, player.facing_right))
                self._use_ammo("gun")
                self._gun_cooldown = self.GUN_COOLDOWN

        if event_key == pygame.K_t:
            if self._throw_cooldown <= 0:
                cx, cy = player.rect.centerx, player.rect.centery
                if "grenade" in self.owned and self._has_ammo("grenade"):
                    target = self._find_throw_target(player, enemies, boss)
                    self.grenades.append(
                        Grenade(cx, cy, player.facing_right, target=target)
                    )
                    self._use_ammo("grenade")
                    self._throw_cooldown = self.THROW_COOLDOWN
                elif "spear" in self.owned and self._has_ammo("spear"):
                    target = self._find_throw_target(player, enemies, boss)
                    self.spears.append(
                        Spear(cx, cy, player.facing_right, target=target)
                    )
                    self._use_ammo("spear")
                    self._throw_cooldown = self.THROW_COOLDOWN

    def _find_throw_target(self, player, enemies, boss):
        """Return (target_x, target_y) of the nearest alive enemy in the facing
        direction, or None if no enemy is in range (falls back to default arc)."""
        candidates = []
        all_enemies = list(enemies) if enemies else []
        if boss is not None and getattr(boss, "alive", False):
            all_enemies.append(boss)

        for e in all_enemies:
            if not getattr(e, "alive", False):
                continue
            dx = e.rect.centerx - player.rect.centerx
            # Must be in the direction the player is facing
            if player.facing_right and dx <= 0:
                continue
            if not player.facing_right and dx >= 0:
                continue
            dist_sq = dx * dx + (e.rect.centery - player.rect.centery) ** 2
            candidates.append((dist_sq, e.rect.centerx, e.rect.centery))

        if not candidates:
            return None
        candidates.sort()
        _, tx, ty = candidates[0]
        return (tx, ty)

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
        # Use pre-cached flipped image — pygame.transform.flip allocates a new
        # surface every call, so we cache both orientations at load time.
        if not player.facing_right:
            img = self._images_flipped.get(held, img)

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
            active = weapon in self.owned and ammo_left > 0

            # Slot background — pre-rendered, no allocation
            screen.blit(self._slot_bg_surfs[active], (sx, sy))

            # Border — cyan if active, grey if empty
            border_col = (0, 200, 220) if active else (80, 80, 80)
            self._slot_rect.x = sx
            self._slot_rect.y = sy
            pygame.draw.rect(screen, border_col, self._slot_rect, 2)

            # Weapon icon — pre-scaled and pre-desaturated
            icon = self._hud_icons.get((weapon, active))
            if icon:
                screen.blit(icon, (sx + 4, sy + 4))

            # Weapon label — pre-rendered for both active states
            label_surf = self._hud_label_surfs[weapon][0 if active else 1]
            screen.blit(label_surf, (sx + 36, sy + 6))

            # Ammo count — cached per (weapon, ammo_value); re-rendered only on change
            ammo_key = (weapon, ammo_left)
            ammo_surf = self._hud_ammo_surfs.get(ammo_key)
            if ammo_surf is None:
                ammo_color = (
                    (255, 221, 68)
                    if ammo_left > 5
                    else (255, 140, 0) if ammo_left > 0 else (180, 60, 60)
                )
                ammo_surf = font.render(str(ammo_left), True, ammo_color)
                self._hud_ammo_surfs[ammo_key] = ammo_surf
            screen.blit(ammo_surf, (sx + 36, sy + 22))

            # Key hint — pre-rendered static surface
            screen.blit(self._hud_hint_surfs[weapon], (sx + 36, sy + 38))
