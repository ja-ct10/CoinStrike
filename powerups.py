"""
powerups.py — Collectible powerup items that spawn in the world.

Powerups:
  MAGNET  — auto-collects all coins within 220px for 8 seconds
  TURBO   — doubles movement speed for 6 seconds
  SHIELD  — grants 5 seconds of invincibility (no damage)
  AMMO    — refills all owned weapon ammo to full

Each powerup floats above the ground/platform it spawns on, bobs up and down,
and glows with a colour unique to its type.
"""

import pygame
import math
import random
from settings import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_WIDTH, PLAYER_HEIGHT

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PU_SIZE = 28  # bounding box (square)
PU_BOB_SPEED = 0.07  # radians per frame
PU_BOB_AMP = 5  # pixels of vertical bob

# Powerup type definitions: name → (duration_frames, colour, label)
_TYPES = {
    "magnet": (480, (0, 200, 255), "MAGNET"),  # 8 s
    "turbo": (360, (255, 180, 0), "TURBO"),  # 6 s
    "shield": (300, (100, 255, 180), "SHIELD"),  # 5 s
    "ammo": (0, (255, 80, 200), "AMMO"),  # instant
}

# Spawn probability weights (must sum to 1.0)
_SPAWN_WEIGHTS = [0.30, 0.30, 0.20, 0.20]
_SPAWN_TYPES = ["magnet", "turbo", "shield", "ammo"]

# Shared label font — created once
_LABEL_FONT: pygame.font.Font | None = None
# Surface cache keyed by (pu_type, bob_phase_bucket) — avoids per-frame alloc
_SURF_CACHE: dict = {}

# Pre-rendered label surfaces keyed by pu_type — rendered once, never again
_LABEL_SURF_CACHE: dict = {}

# Pre-rendered HUD pill backgrounds keyed by (text_width, text_height) — allocated once
_HUD_PILL_CACHE: dict = {}

# Pre-baked icon surfaces keyed by pu_type — drawn once at first use, reused every frame.
# Icons are drawn at a fixed size centred in a (PU_SIZE × PU_SIZE) SRCALPHA surface so
# draw() only needs a single blit instead of multiple draw calls per powerup per frame.
_ICON_SURF_CACHE: dict = {}

# Pre-allocated reusable Rect used inside Powerup.draw — updated in-place
_DRAW_SCRATCH_RECT = pygame.Rect(0, 0, 0, 0)


def _get_label_font() -> pygame.font.Font:
    global _LABEL_FONT
    if _LABEL_FONT is None:
        _LABEL_FONT = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 6)
    return _LABEL_FONT


def _get_label_surf(pu_type: str, color: tuple) -> pygame.Surface:
    """Return a cached label surface for the given powerup type."""
    surf = _LABEL_SURF_CACHE.get(pu_type)
    if surf is None:
        font = _get_label_font()
        _, col, label = _TYPES[pu_type]
        surf = font.render(label, True, col)
        _LABEL_SURF_CACHE[pu_type] = surf
    return surf


def _build_icon_surf(pu_type: str, color: tuple) -> pygame.Surface:
    """Pre-bake the icon for a powerup type into a cached SRCALPHA surface.
    Called at most once per type — result is reused every frame."""
    size = PU_SIZE
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2

    if pu_type == "magnet":
        # U-shape magnet — pygame.draw.arc is expensive; bake it once
        arc_rect = pygame.Rect(cx - 7, cy - 7, 14, 14)
        pygame.draw.arc(surf, color, arc_rect, 0, math.pi, 3)
        pygame.draw.line(surf, color, (cx - 7, cy - 7), (cx - 7, cy + 2), 3)
        pygame.draw.line(surf, color, (cx + 7, cy - 7), (cx + 7, cy + 2), 3)
        pygame.draw.line(surf, (255, 60, 60), (cx - 7, cy + 2), (cx - 4, cy + 2), 3)
        pygame.draw.line(surf, (60, 60, 255), (cx + 4, cy + 2), (cx + 7, cy + 2), 3)

    elif pu_type == "turbo":
        # Lightning bolt — pre-bake the polygon; points are relative to centre
        pts = [
            (cx - 2, cy - 8),
            (cx + 4, cy - 1),
            (cx, cy - 1),
            (cx + 2, cy + 8),
            (cx - 4, cy + 1),
            (cx, cy + 1),
        ]
        pygame.draw.polygon(surf, color, pts)

    elif pu_type == "shield":
        # Shield outline
        shield_pts = [
            (cx, cy - 8),
            (cx + 7, cy - 4),
            (cx + 7, cy + 2),
            (cx, cy + 8),
            (cx - 7, cy + 2),
            (cx - 7, cy - 4),
        ]
        pygame.draw.polygon(surf, color, shield_pts, 2)

    elif pu_type == "ammo":
        # Bullet shape — use a pre-allocated rect updated in-place
        pygame.draw.rect(
            surf, color, pygame.Rect(cx - 3, cy - 6, 6, 10), border_radius=2
        )
        pygame.draw.polygon(
            surf, color, [(cx - 3, cy - 6), (cx + 3, cy - 6), (cx, cy - 11)]
        )

    return surf


def _get_icon_surf(pu_type: str, color: tuple) -> pygame.Surface:
    """Return (and lazily build) the cached icon surface for a powerup type."""
    surf = _ICON_SURF_CACHE.get(pu_type)
    if surf is None:
        surf = _build_icon_surf(pu_type, color)
        _ICON_SURF_CACHE[pu_type] = surf
    return surf


# ---------------------------------------------------------------------------
# Powerup
# ---------------------------------------------------------------------------
class Powerup:
    def __init__(self, x, y, pu_type: str):
        self.pu_type = pu_type
        self.world_x = float(x)
        self.base_y = float(y)
        self.bob_timer = random.uniform(0, math.pi * 2)  # stagger phases
        self.collected = False
        self.rect = pygame.Rect(int(x), int(y), PU_SIZE, PU_SIZE)

        _, self.color, self.label = _TYPES[pu_type]
        self.duration = _TYPES[pu_type][0]

        # Pre-cache both the label and icon surfaces at construction time
        self._label_surf = _get_label_surf(pu_type, self.color)
        self._icon_surf = _get_icon_surf(pu_type, self.color)

    def update(self):
        self.bob_timer += PU_BOB_SPEED
        # Compute sin once and store — reused by draw() to avoid a second math.sin call
        self._sin_val = math.sin(self.bob_timer)
        bob_y = self.base_y + self._sin_val * PU_BOB_AMP
        self.rect.x = int(self.world_x)
        self.rect.y = int(bob_y)

    def draw(self, screen, camera):
        if self.collected:
            return
        # Reuse module-level scratch rect — update in-place to avoid allocation
        _DRAW_SCRATCH_RECT.x = self.rect.x + camera.offset_x
        _DRAW_SCRATCH_RECT.y = self.rect.y + camera.offset_y
        _DRAW_SCRATCH_RECT.width = PU_SIZE
        _DRAW_SCRATCH_RECT.height = PU_SIZE
        dr = _DRAW_SCRATCH_RECT
        cx, cy = dr.centerx, dr.centery
        r = PU_SIZE // 2

        # Outer glow — reuse the sin value computed in update() (no second math.sin call)
        # Quantise to 16-step buckets to maximise cache hits
        glow_alpha = int(120 + 80 * math.sin(self.bob_timer * 2))
        glow_r = r + 6
        glow_key = (self.pu_type, glow_alpha >> 4)
        glow_surf = _SURF_CACHE.get(glow_key)
        if glow_surf is None:
            size = glow_r * 2
            glow_surf = pygame.Surface((size, size), pygame.SRCALPHA)
            rc, gc, bc = self.color
            pygame.draw.circle(
                glow_surf, (rc, gc, bc, glow_alpha >> 4 << 4), (glow_r, glow_r), glow_r
            )
            if len(_SURF_CACHE) > 128:
                for k in list(_SURF_CACHE.keys())[:32]:
                    del _SURF_CACHE[k]
            _SURF_CACHE[glow_key] = glow_surf
        screen.blit(glow_surf, (cx - glow_r, cy - glow_r))

        # Body — rounded square (2 draw calls, no allocation)
        pygame.draw.rect(screen, (20, 10, 40), dr, border_radius=6)
        pygame.draw.rect(screen, self.color, dr, 2, border_radius=6)

        # Icon — single blit of the pre-baked surface (replaces 2–5 draw calls per frame)
        screen.blit(self._icon_surf, dr.topleft)

        # Label below icon — use pre-cached surface (no font.render per frame)
        label_surf = self._label_surf
        screen.blit(label_surf, (cx - label_surf.get_width() // 2, dr.bottom + 2))


# ---------------------------------------------------------------------------
# PowerupManager
# ---------------------------------------------------------------------------
class PowerupManager:
    """
    Spawns powerups on platforms and ground segments, handles collection,
    applies/ticks active effects on the player.
    """

    # Spawn one powerup roughly every N platforms/ground segments
    SPAWN_EVERY_N = 5

    # Squared magnet range — avoids sqrt in the hot coin-pull loop
    _MAGNET_RANGE_SQ = 220 * 220

    def __init__(self):
        self.powerups: list[Powerup] = []
        # Track by world-x position instead of Python id() — id() can be reused
        # after pruning, causing new surfaces to be mistaken for already-seen ones.
        self._seen_platform_xs: set = set()
        self._seen_ground_xs: set = set()
        self._surface_counter: int = 0

        # Active effects: list of {"type": str, "timer": int}
        self.active_effects: list[dict] = []

        # Fast O(1) lookup for active effect types — kept in sync with active_effects
        self._active_set: set = set()

        # HUD font
        self._hud_font: pygame.font.Font | None = None
        # HUD surface cache keyed by (label, timer_bucket) — text only, no pill bg
        self._hud_text_cache: dict = {}
        # Pre-allocated reusable Rect for pill border drawing
        self._pill_rect = pygame.Rect(0, 0, 0, 0)

    def _get_hud_font(self) -> pygame.font.Font:
        if self._hud_font is None:
            self._hud_font = pygame.font.Font(
                "assets/fonts/PressStart2P-Regular.ttf", 8
            )
        return self._hud_font

    # ------------------------------------------------------------------
    def update_surfaces(self, platforms, ground_segments):
        """Called by WorldManager when new terrain is added."""
        for surf in platforms:
            key = surf.rect.x
            if key in self._seen_platform_xs:
                continue
            self._seen_platform_xs.add(key)
            self._surface_counter += 1
            if self._surface_counter % self.SPAWN_EVERY_N == 0:
                self._spawn_on_surface(surf)
        for surf in ground_segments:
            key = surf.rect.x
            if key in self._seen_ground_xs:
                continue
            self._seen_ground_xs.add(key)
            self._surface_counter += 1
            if self._surface_counter % self.SPAWN_EVERY_N == 0:
                self._spawn_on_surface(surf)

    def _spawn_on_surface(self, surf):
        """Place one powerup on top of a surface."""
        margin = PU_SIZE
        if surf.rect.width < margin * 2:
            return
        x = random.randint(surf.rect.left + margin, surf.rect.right - margin - PU_SIZE)
        y = surf.rect.top - PU_SIZE - 8
        pu_type = random.choices(_SPAWN_TYPES, weights=_SPAWN_WEIGHTS, k=1)[0]
        self.powerups.append(Powerup(x, y, pu_type))

    # ------------------------------------------------------------------
    def update(self, player, health, weapon_manager, coin_manager):
        """Call every frame."""
        # Single pass: bob animation + collection check together
        player_rect = player.rect
        for pu in self.powerups:
            pu.update()
            if not pu.collected and pu.rect.colliderect(player_rect):
                pu.collected = True
                self._apply(pu.pu_type, player, health, weapon_manager)

        # Prune collected
        self.powerups = [p for p in self.powerups if not p.collected]

        # Tick active effects — rebuild _active_set only when something expires
        still_active = []
        set_dirty = False
        for effect in self.active_effects:
            effect["timer"] -= 1
            if effect["timer"] > 0:
                still_active.append(effect)
            else:
                self._expire(effect["type"], player)
                set_dirty = True
        self.active_effects = still_active
        if set_dirty:
            self._active_set = {e["type"] for e in self.active_effects}

        # Magnet effect — pull nearby coins using squared distance (no sqrt)
        if "magnet" in self._active_set:
            range_sq = self._MAGNET_RANGE_SQ
            px, py = player_rect.centerx, player_rect.centery
            for coin in coin_manager.coins:
                if coin.collected:
                    continue
                dx = px - coin.rect.centerx
                dy = py - coin.rect.centery
                if dx * dx + dy * dy < range_sq:
                    coin.collected = True
                    player.coins_collected += 1
                    player.coins_earned += 1

    def _is_active(self, pu_type: str) -> bool:
        """O(1) lookup via the active set."""
        return pu_type in self._active_set

    def _apply(self, pu_type: str, player, health, weapon_manager):
        """Apply the powerup effect immediately."""
        if pu_type == "turbo":
            # Cancel any existing turbo first
            self.active_effects = [
                e for e in self.active_effects if e["type"] != "turbo"
            ]
            player.speed_multiplier = max(player.speed_multiplier, 1.5)
            self.active_effects.append({"type": "turbo", "timer": _TYPES["turbo"][0]})
            self._active_set.add("turbo")

        elif pu_type == "magnet":
            self.active_effects = [
                e for e in self.active_effects if e["type"] != "magnet"
            ]
            self.active_effects.append({"type": "magnet", "timer": _TYPES["magnet"][0]})
            self._active_set.add("magnet")

        elif pu_type == "shield":
            # Grant invincibility frames
            health.invincible_timer = max(health.invincible_timer, _TYPES["shield"][0])
            health.shield_timer = max(health.shield_timer, _TYPES["shield"][0])
            self.active_effects.append({"type": "shield", "timer": _TYPES["shield"][0]})
            self._active_set.add("shield")

        elif pu_type == "ammo":
            # Refill all owned weapons — iterate set directly, no copy needed
            from weapon import GUN_MAX_AMMO, GRENADE_MAX_AMMO, SPEAR_MAX_AMMO

            limits = {
                "gun": GUN_MAX_AMMO,
                "grenade": GRENADE_MAX_AMMO,
                "spear": SPEAR_MAX_AMMO,
            }
            for w in weapon_manager.owned:
                weapon_manager.ammo[w] = limits.get(w, weapon_manager.ammo.get(w, 0))

    def _expire(self, pu_type: str, player):
        """Remove the effect when the timer runs out."""
        if pu_type == "turbo":
            # Only reset if no other speed source is active (combo buff)
            if player.speed_multiplier >= 1.5:
                player.speed_multiplier = 1.0

    # ------------------------------------------------------------------
    def prune(self, player_world_x, prune_behind):
        cutoff = player_world_x - prune_behind
        self.powerups = [p for p in self.powerups if p.rect.right > cutoff]

    def draw(self, screen, camera):
        screen_left = -camera.offset_x - PU_SIZE * 2
        screen_right = -camera.offset_x + SCREEN_WIDTH + PU_SIZE * 2
        for pu in self.powerups:
            if screen_left <= pu.rect.x <= screen_right:
                pu.draw(screen, camera)

    # ------------------------------------------------------------------
    def draw_hud(self, screen):
        """Draw active effect timers as small pill badges below the stats line."""
        if not self.active_effects:
            return
        font = self._get_hud_font()
        x = 10
        y = 80  # below time/distance line
        pad = 4

        for effect in self.active_effects:
            pu_type = effect["type"]
            _, color, label = _TYPES[pu_type]
            # Bucket timer to whole seconds — re-render text only once per second
            secs = max(0, effect["timer"] // 60)
            key = (pu_type, secs)
            surf = self._hud_text_cache.get(key)
            if surf is None:
                text = f"{label} {secs}s"
                surf = font.render(text, True, color)
                if len(self._hud_text_cache) > 64:
                    for k in list(self._hud_text_cache.keys())[:16]:
                        del self._hud_text_cache[k]
                self._hud_text_cache[key] = surf

            sw, sh = surf.get_width(), surf.get_height()
            pill_w = sw + pad * 2
            pill_h = sh + pad * 2

            # Pill background — cached per (pill_w, pill_h) to avoid per-frame alloc
            pill_key = (pill_w, pill_h)
            bg = _HUD_PILL_CACHE.get(pill_key)
            if bg is None:
                bg = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
                bg.fill((10, 6, 28, 200))
                if len(_HUD_PILL_CACHE) > 32:
                    for k in list(_HUD_PILL_CACHE.keys())[:8]:
                        del _HUD_PILL_CACHE[k]
                _HUD_PILL_CACHE[pill_key] = bg

            screen.blit(bg, (x - pad, y - pad))

            # Reuse pre-allocated rect for the border draw
            self._pill_rect.update(x - pad, y - pad, pill_w, pill_h)
            pygame.draw.rect(screen, color, self._pill_rect, 1, border_radius=4)

            screen.blit(surf, (x, y))
            x += pill_w + 6
