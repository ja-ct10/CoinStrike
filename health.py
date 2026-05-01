import pygame
from settings import *

FALL_THRESHOLD = SCREEN_HEIGHT + 60  # y below this = fell into pit

MAX_HP = 100
REGEN_DELAY = 180  # frames after last hit before regen starts (~3 s at 60 fps)
REGEN_RATE = 1  # HP restored per frame once regen kicks in (~15 HP/s)
BAR_W = 200
BAR_H = 18
BAR_X = 10
BAR_Y = 10

# ---------------------------------------------------------------------------
# Module-level surface caches for Health.draw — allocated once, reused every frame
# ---------------------------------------------------------------------------
_SHINE_SURF_CACHE: dict = {}  # fill_w → Surface
_PULSE_SURF_CACHE: dict = {}  # fill_w → Surface


class Health:
    # Pre-allocated rects reused every draw call — avoids per-frame allocation
    _BAR_BG_RECT = pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)
    _BAR_FILL_RECT = pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)
    _BAR_BORDER_RECT = pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H)
    _BAR_INNER_RECT = pygame.Rect(BAR_X + 2, BAR_Y + 2, BAR_W - 4, BAR_H - 4)

    def __init__(self, x, y):
        # lives param kept for API compatibility but we use hp now
        self.hp = MAX_HP
        self.max_hp = MAX_HP

        self.x = x
        self.y = y

        # Respawn / invincibility state
        self.respawn_x = 100
        self.respawn_y = 300
        self.invincible_timer = 0
        self.INVINCIBLE_FRAMES = 90
        # Post-respawn shield — separate from regular invincibility flicker.
        # Lasts 60 frames (1 second). Drawn as a visible bubble on the player.
        self.shield_timer = 0
        self.SHIELD_FRAMES = 60

        # Regen state
        self.regen_delay_timer = 0  # counts down to 0 before regen starts
        self._regen_accumulator = 0.0  # fractional HP carried between frames

        self.game_over = False

        self._hp_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 9)
        # Cached label surfaces — re-rendered only when state changes
        self._cached_label_text: str | None = None
        self._cached_label_surf: pygame.Surface | None = None
        self._cached_hp_val: int | None = None
        self._cached_hp_surf: pygame.Surface | None = None

    # ------------------------------------------------------------------
    def take_damage(self, amount):
        """Direct HP damage (use this instead of lives for new code)."""
        if self.invincible_timer > 0:
            return
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.hp = 0
            self.game_over = True
        self.regen_delay_timer = REGEN_DELAY  # reset delay on every hit
        self._regen_accumulator = 0.0

    # ------------------------------------------------------------------
    def update(self, player, ground_segments):
        if self.game_over:
            return False

        if self.invincible_timer > 0:
            self.invincible_timer -= 1
        if self.shield_timer > 0:
            self.shield_timer -= 1

        # Regen tick — only when not dead and delay has elapsed
        if not self.game_over and self.hp < self.max_hp:
            if self.regen_delay_timer > 0:
                self.regen_delay_timer -= 1
            else:
                self._regen_accumulator += REGEN_RATE
                whole = int(self._regen_accumulator)
                if whole >= 1:
                    self.hp = min(self.max_hp, self.hp + whole)
                    self._regen_accumulator -= whole

        # Update respawn checkpoint — last safe ground position
        for seg in ground_segments:
            if (
                player.rect.bottom >= seg.rect.top - 4
                and player.rect.bottom <= seg.rect.top + 20
                and player.rect.right >= seg.rect.left
                and player.rect.left <= seg.rect.right
            ):
                self.respawn_x = player.rect.x
                self.respawn_y = seg.rect.top - PLAYER_HEIGHT
                break

        # Detect fall into pit
        if player.rect.top > FALL_THRESHOLD and self.invincible_timer == 0:
            self.hp -= 25  # falling costs 25 HP
            self.regen_delay_timer = REGEN_DELAY
            self._regen_accumulator = 0.0
            if self.hp <= 0:
                self.hp = 0
                self.game_over = True
            else:
                # Respawn
                player.world_x = float(self.respawn_x)
                player.rect.x = self.respawn_x
                player.rect.y = self.respawn_y
                player.vel_y = 0
                self.invincible_timer = self.INVINCIBLE_FRAMES
                # Grant a 1-second visible shield on respawn
                self.shield_timer = self.SHIELD_FRAMES
            return True

        return False

    # ------------------------------------------------------------------
    def draw(self, screen):
        ratio = self.hp / self.max_hp
        fill_w = int(BAR_W * ratio)

        # Bar colour: green → yellow → red
        if ratio > 0.5:
            r = int(255 * (1 - ratio) * 2)
            g = 220
        else:
            r = 220
            g = int(255 * ratio * 2)
        bar_color = (r, g, 30)

        # Invincible flicker — dim the bar
        if self.invincible_timer > 0 and (self.invincible_timer // 6) % 2 == 0:
            bar_color = (bar_color[0] // 2, bar_color[1] // 2, bar_color[2] // 2)

        # --- Background track --- (reuse pre-allocated class-level rect)
        Health._BAR_BG_RECT.update(BAR_X, BAR_Y, BAR_W, BAR_H)
        pygame.draw.rect(screen, (30, 10, 50), Health._BAR_BG_RECT, border_radius=6)

        # --- Fill --- (reuse pre-allocated class-level rect)
        if fill_w > 0:
            Health._BAR_FILL_RECT.update(BAR_X, BAR_Y, fill_w, BAR_H)
            pygame.draw.rect(screen, bar_color, Health._BAR_FILL_RECT, border_radius=6)

        # --- Shine strip (top highlight) ---
        if fill_w > 4:
            sw = fill_w - 4
            shine_surf = _SHINE_SURF_CACHE.get(sw)
            if shine_surf is None:
                shine_surf = pygame.Surface((sw, BAR_H // 3), pygame.SRCALPHA)
                shine_surf.fill((255, 255, 255, 40))
                if len(_SHINE_SURF_CACHE) > 210:
                    _SHINE_SURF_CACHE.clear()
                _SHINE_SURF_CACHE[sw] = shine_surf
            screen.blit(shine_surf, (BAR_X + 2, BAR_Y + 2))

        # --- Regen pulse glow (cyan tint on bar when regen is active) ---
        if self.regen_delay_timer == 0 and self.hp < self.max_hp and fill_w > 0:
            pulse = _PULSE_SURF_CACHE.get(fill_w)
            if pulse is None:
                pulse = pygame.Surface((fill_w, BAR_H), pygame.SRCALPHA)
                pulse.fill((0, 220, 255, 35))
                if len(_PULSE_SURF_CACHE) > 210:
                    _PULSE_SURF_CACHE.clear()
                _PULSE_SURF_CACHE[fill_w] = pulse
            screen.blit(pulse, (BAR_X, BAR_Y))

        # --- Border --- (reuse pre-allocated class-level rects)
        Health._BAR_BORDER_RECT.update(BAR_X, BAR_Y, BAR_W, BAR_H)
        pygame.draw.rect(
            screen, (160, 32, 240), Health._BAR_BORDER_RECT, 2, border_radius=6
        )
        Health._BAR_INNER_RECT.update(BAR_X + 2, BAR_Y + 2, BAR_W - 4, BAR_H - 4)
        pygame.draw.rect(
            screen, (0, 255, 255), Health._BAR_INNER_RECT, 1, border_radius=5
        )

        # --- "HP" label + regen indicator ---
        regen_active = self.regen_delay_timer == 0 and self.hp < self.max_hp
        label_color = (0, 220, 255) if regen_active else (200, 200, 255)
        label_text = "HP +" if regen_active else "HP"
        # Re-render only when text or color changes
        if label_text != self._cached_label_text:
            self._cached_label_text = label_text
            self._cached_label_surf = self._hp_font.render(
                label_text, True, label_color
            )
        screen.blit(self._cached_label_surf, (BAR_X, BAR_Y + BAR_H + 4))

        # --- Numeric value to the right ---
        # Re-render only when HP value changes
        if self.hp != self._cached_hp_val:
            self._cached_hp_val = self.hp
            self._cached_hp_surf = self._hp_font.render(
                f"{self.hp}", True, (255, 255, 255)
            )
        screen.blit(
            self._cached_hp_surf,
            (
                BAR_X + BAR_W + 6,
                BAR_Y + (BAR_H - self._cached_hp_surf.get_height()) // 2,
            ),
        )


# ---------------------------------------------------------------------------
# GAME OVER SCREEN
# ---------------------------------------------------------------------------

# Cached resources for draw_game_over — built once on first call
_GO_FONTS: tuple | None = None  # (title_font, sub_font, btn_font)
_GO_OVERLAY: pygame.Surface | None = None
_GO_MODAL_SURF: pygame.Surface | None = None
_GO_SUB_SURF: pygame.Surface | None = None
_GO_BTN_SURFS: dict = {}  # (label, is_hover) → Surface
# Cache for the flashing title — keyed by flash_on bool (only 2 states)
_GO_TITLE_SURFS: dict = {}  # flash_on → Surface


def _ensure_go_resources():
    global _GO_FONTS, _GO_OVERLAY, _GO_MODAL_SURF, _GO_SUB_SURF
    if _GO_FONTS is None:
        _GO_FONTS = (
            pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 26),
            pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 12),
            pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 13),
        )
        _GO_OVERLAY = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        _GO_OVERLAY.fill((0, 0, 0, 210))

        modal_w, modal_h = 420, 280
        _GO_MODAL_SURF = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
        _GO_MODAL_SURF.fill((10, 4, 28, 250))

        title_font, sub_font, btn_font = _GO_FONTS
        _GO_SUB_SURF = sub_font.render("Try Again?", True, (220, 220, 255))
        # Pre-render both flash states for the title (only 2 possible colors)
        _GO_TITLE_SURFS[True] = title_font.render("GAME OVER", True, (255, 40, 80))
        _GO_TITLE_SURFS[False] = title_font.render("GAME OVER", True, (255, 180, 200))


def draw_game_over(screen, mouse_pos, flash_timer):
    _ensure_go_resources()
    title_font, sub_font, btn_font = _GO_FONTS

    modal_w, modal_h = 420, 280
    modal_x = SCREEN_WIDTH // 2 - modal_w // 2
    modal_y = SCREEN_HEIGHT // 2 - modal_h // 2

    screen.blit(_GO_OVERLAY, (0, 0))
    screen.blit(_GO_MODAL_SURF, (modal_x, modal_y))

    pygame.draw.rect(
        screen,
        (200, 0, 80),
        pygame.Rect(modal_x, modal_y, modal_w, modal_h),
        3,
        border_radius=10,
    )
    pygame.draw.rect(
        screen,
        (255, 60, 120),
        pygame.Rect(modal_x + 4, modal_y + 4, modal_w - 8, modal_h - 8),
        1,
        border_radius=8,
    )

    for cx, cy in [
        (modal_x, modal_y),
        (modal_x + modal_w - 6, modal_y),
        (modal_x, modal_y + modal_h - 6),
        (modal_x + modal_w - 6, modal_y + modal_h - 6),
    ]:
        pygame.draw.rect(screen, (255, 60, 120), pygame.Rect(cx, cy, 6, 6))

    flash_on = (flash_timer // 20) % 2 == 0
    title_surf = _GO_TITLE_SURFS[flash_on]
    title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, modal_y + 60))
    screen.blit(title_surf, title_rect)

    pygame.draw.line(
        screen,
        (200, 0, 80),
        (modal_x + 20, modal_y + 90),
        (modal_x + modal_w - 20, modal_y + 90),
        1,
    )

    sub_rect = _GO_SUB_SURF.get_rect(center=(SCREEN_WIDTH // 2, modal_y + 120))
    screen.blit(_GO_SUB_SURF, sub_rect)

    btn_w, btn_h = 130, 44
    gap = 30
    total_w = btn_w * 2 + gap
    btn_start_x = SCREEN_WIDTH // 2 - total_w // 2
    btn_y = modal_y + 165

    yes_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
    no_rect = pygame.Rect(btn_start_x + btn_w + gap, btn_y, btn_w, btn_h)

    for rect, label, base_col, border_col in [
        (yes_rect, "YES", (0, 160, 80), (0, 255, 120)),
        (no_rect, "NO", (160, 0, 60), (255, 60, 120)),
    ]:
        is_hover = rect.collidepoint(mouse_pos)
        key = (label, is_hover)
        btn_surf = _GO_BTN_SURFS.get(key)
        if btn_surf is None:
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            r, g, b = base_col
            btn_surf.fill((r, g, b, 220) if is_hover else (r // 2, g // 2, b // 2, 180))
            _GO_BTN_SURFS[key] = btn_surf
        screen.blit(btn_surf, rect.topleft)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=6)

        if is_hover:
            pygame.draw.rect(
                screen,
                border_col,
                pygame.Rect(rect.left, rect.top + 4, 3, rect.height - 8),
                border_radius=2,
            )

        # Button label — cached per (label, is_hover) to avoid per-frame render
        text_key = (label, is_hover)
        text_surf = _GO_BTN_SURFS.get(("text_" + label, is_hover))
        if text_surf is None:
            text_surf = btn_font.render(
                label, True, (255, 255, 255) if is_hover else (200, 200, 200)
            )
            _GO_BTN_SURFS[("text_" + label, is_hover)] = text_surf
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

    return yes_rect, no_rect
