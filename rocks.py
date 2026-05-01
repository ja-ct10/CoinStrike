import pygame
import random
from settings import SCREEN_WIDTH, SCREEN_HEIGHT


class FallingRock:
    GRAVITY = 0.6
    BASE_DAMAGE = 15
    RADIUS = 14

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)
        self.vel_y = 0.0
        self._alive = True
        # Random slight horizontal drift
        self.vel_x = random.uniform(-1.0, 1.0)
        # Reusable rect — updated in-place to avoid per-frame allocation
        r = self.RADIUS
        self._rect = pygame.Rect(int(self.x) - r, int(self.y) - r, r * 2, r * 2)

    @property
    def alive(self):
        return self._alive

    @property
    def rect(self):
        r = self.RADIUS
        self._rect.x = int(self.x) - r
        self._rect.y = int(self.y) - r
        return self._rect

    def update(self, ground_segments, platforms):
        self.vel_y += self.GRAVITY
        self.x += self.vel_x
        self.y += self.vel_y

        # Off-screen below
        if self.y > SCREEN_HEIGHT + 100:
            self._alive = False
            return

        # Ground collision
        for seg in ground_segments:
            if self.rect.colliderect(seg.rect):
                self._alive = False
                return

        # Platform collision
        for p in platforms:
            if getattr(p, "visible", True) and self.rect.colliderect(p.rect):
                self._alive = False
                return

    def draw(self, screen, camera):
        if not self._alive:
            return
        pos = camera.apply(self.rect)
        cx, cy = pos.centerx, pos.centery
        r = self.RADIUS

        # Rock body
        pygame.draw.circle(screen, (90, 70, 50), (cx, cy), r)
        pygame.draw.circle(screen, (120, 95, 70), (cx, cy), r, 2)
        pygame.draw.circle(screen, (150, 120, 90), (cx - r // 3, cy - r // 3), r // 3)
        pygame.draw.line(screen, (60, 45, 30), (cx - 4, cy - 6), (cx + 2, cy + 4), 1)
        pygame.draw.line(screen, (60, 45, 30), (cx + 3, cy - 4), (cx - 1, cy + 5), 1)


class RockManager:
    BASE_INTERVAL = 300  # frames between spawns at start
    MIN_INTERVAL = 60  # minimum interval at max difficulty

    def __init__(self):
        self.rocks = []
        self.spawn_timer = 0

    def update(
        self, camera, ground_segments, platforms, player, health, difficulty_scaler=None
    ):
        # Determine spawn interval
        interval = self.BASE_INTERVAL
        if difficulty_scaler is not None:
            interval = difficulty_scaler.rock_interval

        self.spawn_timer += 1
        if self.spawn_timer >= interval:
            self.spawn_timer = 0
            self._spawn_rock(camera)

        # Update rocks
        for rock in self.rocks:
            rock.update(ground_segments, platforms)

        # Check player collision — only rocks near the player can hit them
        if health.invincible_timer == 0:
            px = player.rect.centerx
            for rock in self.rocks:
                if (
                    rock.alive
                    and abs(rock.rect.centerx - px) < 200
                    and rock.rect.colliderect(player.rect)
                ):
                    health.take_damage(rock.BASE_DAMAGE)
                    rock._alive = False
                    if not health.game_over:
                        health.invincible_timer = health.INVINCIBLE_FRAMES
                    break

        # Prune dead rocks
        self.rocks = [r for r in self.rocks if r.alive]

    def _spawn_rock(self, camera):
        # Spawn within the visible camera window + margin
        visible_left = -camera.offset_x - 200
        visible_right = -camera.offset_x + SCREEN_WIDTH + 200
        x = random.uniform(visible_left, visible_right)
        self.rocks.append(FallingRock(x, -60))

    def draw(self, screen, camera):
        screen_left = -camera.offset_x - FallingRock.RADIUS * 2
        screen_right = -camera.offset_x + SCREEN_WIDTH + FallingRock.RADIUS * 2
        for rock in self.rocks:
            if screen_left <= rock.x <= screen_right:
                rock.draw(screen, camera)
