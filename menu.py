import pygame
import math
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


def draw_menu(screen, menu_selection):
    # Futuristic neon bg with grid
    screen.fill((5, 5, 15))
    # Grid lines
    for i in range(0, SCREEN_HEIGHT, 20):
        pygame.draw.line(screen, (0, 50, 100, 50), (0, i), (SCREEN_WIDTH, i))
    for i in range(0, SCREEN_WIDTH, 20):
        pygame.draw.line(screen, (0, 50, 100, 50), (i, 0), (i, SCREEN_HEIGHT))

    font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 44)

    # Title
    title = font.render("COINSTRIKE", True, (255, 255, 255))
    title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 150))
    screen.blit(title, title_rect)

    # Buttons
    options = ["START", "OPTIONS", "EXIT"]
    for i, text in enumerate(options):
        y = 280 + i * 60
        is_selected = i == menu_selection

        # Button rect
        rect = pygame.Rect(SCREEN_WIDTH // 2 - 160, y, 320, 55)

        # Futuristic chrome gradient + neon glow
        # Gradient base
        for j in range(rect.height):
            ratio = j / rect.height
            color = (int(40 + 60 * ratio), int(40 + 60 * ratio), int(60 + 80 * ratio))
            pygame.draw.line(screen, color, rect.left, rect.top + j, rect.width)

        # Neon cyan glow
        glow_rect = rect.inflate(10, 10)
        pygame.draw.rect(screen, (0, 255, 255, 100), glow_rect, border_radius=8)
        pygame.draw.rect(
            screen, (0, 255, 255, 200), rect.inflate(4, 4), border_radius=8, width=2
        )

        # Magenta inner border
        pygame.draw.rect(screen, (255, 0, 255, 255), rect, border_radius=8, width=3)

        # Text with ▶
        display_text = "▸ " + text if is_selected else text  # Neon arrow
        pulse = (
            1 + 0.2 * math.sin(pygame.time.get_ticks() * 0.01 + i) if is_selected else 1
        )
        glow_color = (int(255 * pulse), int(255 * pulse), int(255 * pulse))
        text_surf = font.render(display_text, True, glow_color)
        text_rect = text_surf.get_rect(center=rect.center)
        screen.blit(text_surf, text_rect)
