import pygame
from utils import resource_path


class ComboSystem:
    BONUS_THRESHOLD = 3  # combo >= 3 → bonus coins per kill
    BUFF_THRESHOLD = 5  # combo >= 5 → speed + damage buff
    BUFF_DURATION = 300  # frames (~5 s at 60 fps)
    INACTIVITY_TIMEOUT = 300  # frames without a kill → reset

    def __init__(self):
        self._count = 0
        self.inactivity_timer = 0
        self.buff_timer = 0
        self._last_kills = 0  # tracks cumulative kill delta for main.py combo wiring
        self._font = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 14)
        self._small_font = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 9)

        # --- render cache ---
        # Cached label surfaces keyed by (label_text, color) so font.render()
        # is only called when the combo count or buff state actually changes.
        self._cached_label: str | None = None
        self._cached_color: tuple | None = None
        self._cached_surf: pygame.Surface | None = None
        self._cached_shadow: pygame.Surface | None = None

        # The hint text never changes — render it once at init.
        self._hint_surf = self._small_font.render("SPEED+DMG BUFF", True, (0, 200, 160))

        # Pre-allocated Rects for the buff bar and shadow to avoid per-frame allocation.
        self._bar_bg_rect = pygame.Rect(0, 0, 160, 6)
        self._bar_fill_rect = pygame.Rect(0, 0, 160, 6)
        self._shadow_rect = pygame.Rect(0, 0, 0, 0)  # reused in draw()

        # Cached label surface height — updated whenever the surface is re-rendered.
        self._cached_surf_h: int = 0

        # Shadow blit offsets (constant)
        self._shadow_offsets = ((-2, -2), (2, -2), (-2, 2), (2, 2))

    # ------------------------------------------------------------------
    @property
    def count(self):
        return self._count

    def is_buff_active(self):
        return self.buff_timer > 0

    # ------------------------------------------------------------------
    def on_kill(self, player) -> int:
        """Call once per enemy death. Returns bonus coins awarded."""
        self._count += 1
        self.inactivity_timer = self.INACTIVITY_TIMEOUT  # reset inactivity

        # Activate buff when threshold reached
        if self._count >= self.BUFF_THRESHOLD and not self.is_buff_active():
            self.buff_timer = self.BUFF_DURATION
            player.speed_multiplier = 1.4
            player.damage_multiplier = 1.5

        # Return bonus coins
        if self._count >= self.BONUS_THRESHOLD:
            return self._count
        return 0

    def on_damage_taken(self, player):
        """Call when the player takes any damage."""
        self._count = 0
        self.buff_timer = 0
        self.inactivity_timer = 0
        player.speed_multiplier = 1.0
        player.damage_multiplier = 1.0

    def update(self):
        """Tick timers. Call once per frame."""
        if self.buff_timer > 0:
            self.buff_timer -= 1
            # Buff expired naturally — multipliers stay until next kill or damage

        if self.inactivity_timer > 0:
            self.inactivity_timer -= 1
            if self.inactivity_timer == 0 and self._count > 0:
                self._count = 0

    # ------------------------------------------------------------------
    def draw(self, screen, x=10, y=50):
        """Draw combo text below the HP bar.
        x/y set the top-left origin; defaults align with the HP bar (BAR_X=10).
        """
        if self._count < 2:
            return

        buff_active = self.buff_timer > 0  # evaluate once

        # --- label surface (cached) ---
        label = f"COMBO x{self._count}"
        color = (0, 255, 200) if buff_active else (255, 221, 68)

        if label != self._cached_label or color != self._cached_color:
            self._cached_label = label
            self._cached_color = color
            self._cached_surf = self._font.render(label, True, color)
            self._cached_shadow = self._font.render(label, True, (0, 0, 0))
            self._cached_surf_h = self._cached_surf.get_height()

        surf = self._cached_surf
        shadow = self._cached_shadow

        # Glow shadow — 4 blits using pre-computed offsets, reusing a single Rect
        sr = self._shadow_rect
        for ox, oy in self._shadow_offsets:
            sr.topleft = (x + ox, y + oy)
            screen.blit(shadow, sr)

        screen.blit(surf, (x, y))

        # Buff timer bar — same width as HP bar (200px), aligned left
        if buff_active:
            bar_w = 200
            bar_y = y + self._cached_surf_h + 4

            # Reuse pre-allocated Rects — just update position/size
            self._bar_bg_rect.update(x, bar_y, bar_w, 6)
            pygame.draw.rect(screen, (30, 30, 60), self._bar_bg_rect, border_radius=3)

            fill_w = int(bar_w * self.buff_timer / self.BUFF_DURATION)
            self._bar_fill_rect.update(x, bar_y, fill_w, 6)
            pygame.draw.rect(
                screen, (0, 255, 200), self._bar_fill_rect, border_radius=3
            )

            # Hint surface rendered once at init — left-aligned
            screen.blit(self._hint_surf, (x, bar_y + 6 + 4))
