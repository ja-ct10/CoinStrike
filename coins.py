import pygame
import random
from settings import *


class Coin:
    def __init__(
        self,
        x=None,
        y=None,
        player=None,
        fixed_position=False,
        platforms=None,
        ground=None,
    ):
        self.image = pygame.image.load("assets/coin.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (COIN_WIDTH, COIN_HEIGHT))

        self.fixed_position = fixed_position
        self.platforms = platforms
        self.ground = ground

        if fixed_position and x is not None and y is not None:
            # HUD coin — stays at a fixed screen position
            self.rect = pygame.Rect(x, y, COIN_WIDTH, COIN_HEIGHT)
        else:
            self.rect = pygame.Rect(0, 0, COIN_WIDTH, COIN_HEIGHT)
            self._place_on_surface()

    def _place_on_surface(self):
        """Place the coin on top of a random platform or on the ground."""
        surfaces = []

        if self.platforms:
            surfaces.extend(self.platforms)
        if self.ground:
            surfaces.append(self.ground)

        if surfaces:
            surface = random.choice(surfaces)
            margin = 10
            min_x = surface.rect.left + margin
            max_x = surface.rect.right - COIN_WIDTH - margin

            if max_x <= min_x:
                coin_x = surface.rect.centerx - COIN_WIDTH // 2
            else:
                coin_x = random.randint(min_x, max_x)

            # Sit just above the surface top
            coin_y = surface.rect.top - COIN_HEIGHT - 4
            self.rect.topleft = (coin_x, coin_y)
        else:
            self.rect.topleft = (
                random.randint(50, SCREEN_WIDTH - 50),
                random.randint(50, SCREEN_HEIGHT - 150),
            )

    def draw(self, screen, player, camera=None, custom_text_position=None, y_offset=0):
        if self.fixed_position:
            # HUD coin — no camera offset, always on screen
            screen.blit(self.image, self.rect)
            font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 18)
            text = font.render(f"{player.coins_collected}", True, (255, 255, 255))
            if custom_text_position:
                x, y = custom_text_position
            else:
                x = self.rect.right + 5
                y = self.rect.top
            screen.blit(text, (x, y + y_offset))
        else:
            # World coin — apply camera transform
            if camera:
                screen.blit(self.image, camera.apply(self.rect))
            else:
                screen.blit(self.image, self.rect)

    def reset_position(self):
        """Move coin to a new surface position after collection."""
        self._place_on_surface()
