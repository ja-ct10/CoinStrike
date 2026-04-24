import pygame
from settings import *


class ItemBox:
    def __init__(self, x, y, item_type):
        self.item_type = item_type

        # Load correct image based on type
        if item_type == "spear":
            image = pygame.image.load("assets/spear-box.png").convert_alpha()
        elif item_type == "gun":
            image = pygame.image.load("assets/gun-box.png").convert_alpha()
        elif item_type == "grenade":
            image = pygame.image.load("assets/grenade-box.png").convert_alpha()
        else:
            raise ValueError("Unknown item type")

        self.image = pygame.transform.scale(image, (WEAPON_WIDTH, WEAPON_HEIGHT))

        self.rect = self.image.get_rect(topleft=(x, y))

    def draw(self, screen):
        screen.blit(self.image, self.rect)
