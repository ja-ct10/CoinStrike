import pygame
import math
from settings import *
from utils import resource_path


class Player:
    def __init__(self, x, y):
        self.idle_right = pygame.transform.scale(
            pygame.image.load(resource_path("assets/player-idle-right.png")).convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )
        self.idle_left = pygame.transform.scale(
            pygame.image.load(resource_path("assets/player-idle-left.png")).convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )
        self.run_right = pygame.transform.scale(
            pygame.image.load(resource_path("assets/player-run-right.png")).convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )
        self.run_left = pygame.transform.scale(
            pygame.image.load(resource_path("assets/player-run-left.png")).convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )

        # Weapon-holding sprites — idle and running, left and right
        # Each dict maps weapon name → scaled surface (with try/except fallback)
        self.hold_idle_right = {}
        self.hold_idle_left = {}
        self.hold_run_right = {}
        self.hold_run_left = {}

        _holding_map = {
            "gun": (
                "holding-gun-right",
                "holding-gun-left",
                "run-holding-gun-right",
                "run-holding-gun-left",
            ),
            "spear": (
                "holding-spear-right",
                "holding-spear-left",
                "run-holding-spear-right",
                "run-holding-spear-left",
            ),
            "grenade": (
                "holding-grenade-right",
                "holding-grenade-left",
                "run-holding-grenade-right",
                "run-holding-grenade-left",
            ),
        }
        for weapon, (ir, il, rr, rl) in _holding_map.items():
            for attr, fname in [
                (self.hold_idle_right, ir),
                (self.hold_idle_left, il),
                (self.hold_run_right, rr),
                (self.hold_run_left, rl),
            ]:
                try:
                    img = pygame.image.load(resource_path(f"assets/{fname}.png")).convert_alpha()
                    attr[weapon] = pygame.transform.scale(
                        img, (PLAYER_WIDTH, PLAYER_HEIGHT)
                    )
                except Exception:
                    attr[weapon] = None  # fallback: use base sprite

        self.image = self.idle_right
        self.rect = self.image.get_rect(topleft=(x, y))

        self.facing_right = True
        self.running = False
        self.speed = 5
        self.speed_multiplier = 1.0  # modified by ComboSystem buff
        self.damage_multiplier = 1.0  # modified by ComboSystem buff

        self.vel_y = 0
        self.gravity = 0.8
        self.jump_power = -15
        self.on_ground = False

        self.coins_collected = 0
        self.coins_earned = 0
        self.world_x = float(x)

    def collect_coin(self, coin):
        if self.rect.colliderect(coin.rect):
            coin.reset_position()
            self.coins_collected += 1
            self.coins_earned += 1

    def update(self, platforms, ground_segments, camera_offset_x=0):
        keys = pygame.key.get_pressed()
        self.running = False

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.world_x += self.speed * self.speed_multiplier
            self.facing_right = True
            self.running = True
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.world_x -= self.speed * self.speed_multiplier
            self.facing_right = False
            self.running = True

        # Hard left boundary: never go behind world origin (x=0)
        if self.world_x < 0:
            self.world_x = 0

        self.rect.x = int(self.world_x)

        if (
            keys[pygame.K_UP] or keys[pygame.K_w] or keys[pygame.K_SPACE]
        ) and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False

        self.vel_y += self.gravity
        self.rect.y += self.vel_y
        self.on_ground = False

        # Platforms first (skip invisible glitch platforms)
        for platform in platforms:
            if not getattr(platform, "visible", True):
                continue
            if self.rect.colliderect(platform.rect):
                if self.vel_y >= 0 and self.rect.bottom <= platform.rect.top + 15:
                    self.rect.bottom = platform.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    break

        # Ground segments
        if not self.on_ground:
            for seg in ground_segments:
                if self.rect.colliderect(seg.rect):
                    if self.vel_y >= 0 and self.rect.bottom <= seg.rect.top + 15:
                        self.rect.bottom = seg.rect.top
                        self.vel_y = 0
                        self.on_ground = True
                        break

        if self.running:
            self.image = self.run_right if self.facing_right else self.run_left
        else:
            self.image = self.idle_right if self.facing_right else self.idle_left

    def _get_held_weapon(self, weapon_manager):
        """Return the name of the currently held weapon, or None."""
        if weapon_manager is None:
            return None
        for w in ["gun", "spear", "grenade"]:
            if w in weapon_manager.owned:
                return w
        return None

    # Pre-baked shield surfaces keyed by (radius, alpha_q).
    # Cleared on class definition so stale entries never carry over.
    _SHIELD_SURF_CACHE: dict = {}

    def draw(self, screen, camera, weapon_manager=None, health=None):
        # Pick holding sprite if a weapon is owned and sprite exists
        held = self._get_held_weapon(weapon_manager)
        sprite = None
        if held:
            if self.running:
                table = self.hold_run_right if self.facing_right else self.hold_run_left
            else:
                table = (
                    self.hold_idle_right if self.facing_right else self.hold_idle_left
                )
            sprite = table.get(held)

        screen.blit(sprite if sprite else self.image, camera.apply(self.rect))

        # Only draw the floating weapon overlay if no baked-in holding sprite
        if held and sprite is None and weapon_manager is not None:
            weapon_manager.draw_held_weapon(screen, self, camera)

        # Post-respawn shield bubble
        if health is not None and health.shield_timer > 0:
            progress = health.shield_timer / health.SHIELD_FRAMES  # 1.0 → 0.0
            # Skip near-zero alpha to avoid invisible surface allocation
            if progress >= 0.05:
                pulse = 0.85 + 0.15 * math.sin(health.shield_timer * 0.35)
                radius = max(
                    4, int((max(PLAYER_WIDTH, PLAYER_HEIGHT) // 2 + 14) * pulse)
                )
                # Alpha: 180 → 16, never 0. Quantise to 16-step buckets.
                alpha_q = max(16, int(180 * progress) & 0xF0)

                key = (radius, alpha_q)
                surf = Player._SHIELD_SURF_CACHE.get(key)
                if surf is None:
                    size = radius * 2
                    surf = pygame.Surface((size, size), pygame.SRCALPHA)
                    pygame.draw.circle(
                        surf, (0, 220, 255, alpha_q), (radius, radius), radius
                    )
                    inner_alpha = max(16, alpha_q // 4)
                    pygame.draw.circle(
                        surf,
                        (0, 180, 255, inner_alpha),
                        (radius, radius),
                        max(1, radius - 4),
                    )
                    # Partial eviction — keep hot entries alive, avoid cold-cache spike
                    if len(Player._SHIELD_SURF_CACHE) > 128:
                        evict = list(Player._SHIELD_SURF_CACHE.keys())[:32]
                        for k in evict:
                            del Player._SHIELD_SURF_CACHE[k]
                    Player._SHIELD_SURF_CACHE[key] = surf

                dr = camera.apply(self.rect)
                screen.blit(surf, (dr.centerx - radius, dr.centery - radius))
