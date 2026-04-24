import pygame
from settings import *


class Player:
    def __init__(self, x, y):
        self.idle_right = pygame.transform.scale(
            pygame.image.load("assets/player-idle-right.png").convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )
        self.idle_left = pygame.transform.scale(
            pygame.image.load("assets/player-idle-left.png").convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )
        self.run_right = pygame.transform.scale(
            pygame.image.load("assets/player-run-right.png").convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )
        self.run_left = pygame.transform.scale(
            pygame.image.load("assets/player-run-left.png").convert_alpha(),
            (PLAYER_WIDTH, PLAYER_HEIGHT),
        )

        self.image = self.idle_right
        self.rect = self.image.get_rect(topleft=(x, y))

        self.facing_right = True
        self.running = False
        self.speed = 5

        self.vel_y = 0
        self.gravity = 0.8
        self.jump_power = -12
        self.on_ground = False

        self.coins_collected = 0
        self.coins_earned = 0
        self.world_x = float(x)

    def collect_coin(self, coin):
        if self.rect.colliderect(coin.rect):
            coin.reset_position()
            self.coins_collected += 1
            self.coins_earned += 1

    def update(self, platforms, ground_segments):
        keys = pygame.key.get_pressed()
        self.running = False

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.world_x += self.speed
            self.facing_right = True
            self.running = True
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.world_x -= self.speed
            self.facing_right = False
            self.running = True

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

    def draw(self, screen, camera, weapon_manager=None):
        # Draw player sprite
        screen.blit(self.image, camera.apply(self.rect))
        # Draw held weapon on top of player
        if weapon_manager is not None:
            weapon_manager.draw_held_weapon(screen, self, camera)
