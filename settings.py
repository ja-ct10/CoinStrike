import pygame

# Screen
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 576
FPS = 60

PLAYER_WIDTH = 70
PLAYER_HEIGHT = 80

WEAPON_WIDTH = 90
WEAPON_HEIGHT = 90

GROUND_DEPTH_OFFSET = 105
GROUND_OFFSET = 2

HEALTH_WIDTH = 35
HEALTH_HEIGHT = 35

MISSION_WIDTH = 270
MISSION_HEIGHT = 140

COIN_WIDTH = 40
COIN_HEIGHT = 40

SETTINGS_WIDTH = 40
SETTINGS_HEIGHT = 40

SHOP_WIDTH = 60
SHOP_HEIGHT = 60


class Settings:
    def __init__(self, x, y):
        self.image = pygame.image.load("assets/settings.png").convert_alpha()
        self.image = pygame.transform.scale(
            self.image, (SETTINGS_WIDTH, SETTINGS_HEIGHT)
        )
        self.rect = self.image.get_rect(topright=(x, y))

    def draw(self, screen):
        screen.blit(self.image, self.rect)


def draw_settings_modal(screen, mouse_pos):
    modal_w, modal_h = 340, 320
    modal_x = SCREEN_WIDTH // 2 - modal_w // 2
    modal_y = SCREEN_HEIGHT // 2 - modal_h // 2

    close_btn_size = 34
    close_btn_rect = pygame.Rect(
        modal_x + modal_w - close_btn_size - 14,
        modal_y + 12,
        close_btn_size,
        close_btn_size,
    )

    title_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 14)
    btn_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 12)

    btn_labels = ["RESUME", "RESTART", "OPTIONS", "QUIT"]
    btn_w, btn_h = 240, 44
    btn_x = modal_x + modal_w // 2 - btn_w // 2
    btn_start_y = modal_y + 80
    btn_gap = 54

    btn_rects = [
        pygame.Rect(btn_x, btn_start_y + i * btn_gap, btn_w, btn_h)
        for i in range(len(btn_labels))
    ]

    # Overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    # Modal background
    modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    modal_surf.fill((10, 8, 32, 245))
    screen.blit(modal_surf, (modal_x, modal_y))

    # Modal borders
    pygame.draw.rect(
        screen,
        (160, 32, 240),
        pygame.Rect(modal_x, modal_y, modal_w, modal_h),
        2,
        border_radius=10,
    )
    pygame.draw.rect(
        screen,
        (0, 255, 255),
        pygame.Rect(modal_x + 3, modal_y + 3, modal_w - 6, modal_h - 6),
        1,
        border_radius=8,
    )

    # Title
    title_surf = title_font.render("PAUSED", True, (255, 221, 68))
    screen.blit(title_surf, (modal_x + 18, modal_y + 16))

    # Divider
    pygame.draw.line(
        screen,
        (160, 32, 240),
        (modal_x + 14, modal_y + 50),
        (modal_x + modal_w - 14, modal_y + 50),
    )

    # Buttons
    for i, (label, rect) in enumerate(zip(btn_labels, btn_rects)):
        is_hover = rect.collidepoint(mouse_pos)

        # Button background
        btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        btn_surf.fill((40, 16, 80, 200) if is_hover else (26, 8, 48, 180))
        screen.blit(btn_surf, rect.topleft)

        # Button border — cyan for RESUME, pink for QUIT, purple for others
        if label == "RESUME":
            border_color = (0, 200, 200)
        elif label == "QUIT":
            border_color = (255, 68, 153)
        else:
            border_color = (160, 32, 240)

        pygame.draw.rect(screen, border_color, rect, 1, border_radius=6)

        # Hover glow line on left edge
        if is_hover:
            pygame.draw.rect(
                screen,
                border_color,
                pygame.Rect(rect.left, rect.top + 4, 3, rect.height - 8),
                border_radius=2,
            )

        text_color = (255, 221, 68) if is_hover else (220, 220, 220)
        text_surf = btn_font.render(label, True, text_color)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)

    # Close button
    is_close_hover = close_btn_rect.collidepoint(mouse_pos)
    close_bg = (160, 32, 240, 80) if is_close_hover else (26, 8, 48, 200)
    close_surf = pygame.Surface((close_btn_size, close_btn_size), pygame.SRCALPHA)
    close_surf.fill(close_bg)
    screen.blit(close_surf, close_btn_rect.topleft)
    pygame.draw.rect(screen, (160, 32, 240), close_btn_rect, 2, border_radius=6)

    x_surf = btn_font.render("X", True, (255, 68, 153))
    x_rect = x_surf.get_rect(center=close_btn_rect.center)
    screen.blit(x_surf, x_rect)

    return close_btn_rect, btn_rects, btn_labels
