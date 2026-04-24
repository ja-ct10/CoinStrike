import pygame
from settings import *

PANEL_W = 260
PANEL_H = 100
PANEL_Y = 10
PANEL_X = SCREEN_WIDTH - PANEL_W - 10 - SETTINGS_WIDTH - 8


class Mission:
    def __init__(self):
        self.font_title = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 8)
        self.font_line = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 8)

        self.missions = [
            {"text": "Collect 100 coins", "target": 10, "progress": 0, "done": False},
            {"text": "Kill 5 enemies", "target": 5, "progress": 0, "done": False},
            {"text": "Buy 2 weapons", "target": 2, "progress": 0, "done": False},
        ]

        self.rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
        self.all_completed = False

    def update(self, player, enemy_manager, weapon_manager):
        # Coins
        self.missions[0]["progress"] = getattr(player, "coins_earned", 0)
        if self.missions[0]["progress"] >= self.missions[0]["target"]:
            self.missions[0]["done"] = True

        # Enemies
        self.missions[1]["progress"] = getattr(enemy_manager, "enemies_killed", 0)
        if self.missions[1]["progress"] >= self.missions[1]["target"]:
            self.missions[1]["done"] = True

        # Weapons bought
        self.missions[2]["progress"] = getattr(weapon_manager, "weapons_bought", 0)
        if self.missions[2]["progress"] >= self.missions[2]["target"]:
            self.missions[2]["done"] = True

        # All complete check
        self.all_completed = all(m["done"] for m in self.missions)

    def draw(self, screen):
        px = PANEL_X
        py = PANEL_Y

        bg_surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        bg_surf.fill((8, 6, 28, 220))
        screen.blit(bg_surf, (px, py))

        pygame.draw.rect(screen, (0, 200, 220), self.rect, 2)
        pygame.draw.rect(screen, (100, 40, 180), self.rect.inflate(-6, -6), 1)

        title_surf = self.font_title.render("MISSIONS", True, (255, 221, 68))
        screen.blit(title_surf, (px + 10, py + 8))

        pygame.draw.line(
            screen, (0, 200, 220), (px + 8, py + 24), (px + PANEL_W - 8, py + 24)
        )

        line_y = py + 32
        for i, m in enumerate(self.missions):
            color = (200, 220, 255)

            if m["done"]:
                color = (0, 255, 120)  # green highlight

            text = f"{m['text']} ({m['progress']}/{m['target']})"
            surf = self.font_line.render(text, True, color)
            screen.blit(surf, (px + 10, line_y + i * 20))
