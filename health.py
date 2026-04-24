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


class Health:
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

        # Regen state
        self.regen_delay_timer = 0  # counts down to 0 before regen starts
        self._regen_accumulator = 0.0  # fractional HP carried between frames

        self.game_over = False

        # For compatibility with enemy.py which reads health.lives
        # We expose lives as a property so enemy damage still works
        self._lives_compat = 3

        self._hp_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 9)

    # ------------------------------------------------------------------
    # Compatibility shim — enemy.py does health.lives -= 1
    # We map each "life lost" to -20 HP
    # ------------------------------------------------------------------
    @property
    def lives(self):
        return self._lives_compat

    @lives.setter
    def lives(self, value):
        diff = self._lives_compat - value  # how many lives were deducted
        self._lives_compat = value
        self.hp = max(0, self.hp - diff * 20)
        if self.hp <= 0:
            self.hp = 0
            self.game_over = True

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

        # --- Background track ---
        pygame.draw.rect(
            screen,
            (30, 10, 50),
            pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H),
            border_radius=6,
        )

        # --- Fill ---
        if fill_w > 0:
            pygame.draw.rect(
                screen,
                bar_color,
                pygame.Rect(BAR_X, BAR_Y, fill_w, BAR_H),
                border_radius=6,
            )

        # --- Shine strip (top highlight) ---
        if fill_w > 4:
            shine_surf = pygame.Surface((fill_w - 4, BAR_H // 3), pygame.SRCALPHA)
            shine_surf.fill((255, 255, 255, 40))
            screen.blit(shine_surf, (BAR_X + 2, BAR_Y + 2))

        # --- Regen pulse glow (cyan tint on bar when regen is active) ---
        if self.regen_delay_timer == 0 and self.hp < self.max_hp and fill_w > 0:
            pulse = pygame.Surface((fill_w, BAR_H), pygame.SRCALPHA)
            pulse.fill((0, 220, 255, 35))
            screen.blit(pulse, (BAR_X, BAR_Y))

        # --- Border ---
        pygame.draw.rect(
            screen,
            (160, 32, 240),
            pygame.Rect(BAR_X, BAR_Y, BAR_W, BAR_H),
            2,
            border_radius=6,
        )
        pygame.draw.rect(
            screen,
            (0, 255, 255),
            pygame.Rect(BAR_X + 2, BAR_Y + 2, BAR_W - 4, BAR_H - 4),
            1,
            border_radius=5,
        )

        # --- "HP" label + regen indicator ---
        regen_active = self.regen_delay_timer == 0 and self.hp < self.max_hp
        label_color = (0, 220, 255) if regen_active else (200, 200, 255)
        label_text = "HP +" if regen_active else "HP"
        label = self._hp_font.render(label_text, True, label_color)
        screen.blit(label, (BAR_X, BAR_Y + BAR_H + 4))

        # --- Numeric value to the right ---
        hp_text = self._hp_font.render(f"{self.hp}", True, (255, 255, 255))
        screen.blit(
            hp_text, (BAR_X + BAR_W + 6, BAR_Y + (BAR_H - hp_text.get_height()) // 2)
        )


# ---------------------------------------------------------------------------
# GAME OVER SCREEN
# ---------------------------------------------------------------------------
def draw_game_over(screen, mouse_pos, flash_timer):
    modal_w, modal_h = 420, 280
    modal_x = SCREEN_WIDTH // 2 - modal_w // 2
    modal_y = SCREEN_HEIGHT // 2 - modal_h // 2

    title_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 26)
    sub_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 12)
    btn_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 13)

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 210))
    screen.blit(overlay, (0, 0))

    modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    modal_surf.fill((10, 4, 28, 250))
    screen.blit(modal_surf, (modal_x, modal_y))

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
    title_color = (255, 40, 80) if flash_on else (255, 180, 200)
    title_surf = title_font.render("GAME OVER", True, title_color)
    title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, modal_y + 60))
    screen.blit(title_surf, title_rect)

    pygame.draw.line(
        screen,
        (200, 0, 80),
        (modal_x + 20, modal_y + 90),
        (modal_x + modal_w - 20, modal_y + 90),
        1,
    )

    sub_surf = sub_font.render("Try Again?", True, (220, 220, 255))
    sub_rect = sub_surf.get_rect(center=(SCREEN_WIDTH // 2, modal_y + 120))
    screen.blit(sub_surf, sub_rect)

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
        btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        r, g, b = base_col
        btn_surf.fill((r, g, b, 220) if is_hover else (r // 2, g // 2, b // 2, 180))
        screen.blit(btn_surf, rect.topleft)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=6)

        if is_hover:
            pygame.draw.rect(
                screen,
                border_col,
                pygame.Rect(rect.left, rect.top + 4, 3, rect.height - 8),
                border_radius=2,
            )

        text_surf = btn_font.render(
            label, True, (255, 255, 255) if is_hover else (200, 200, 200)
        )
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

    return yes_rect, no_rect
