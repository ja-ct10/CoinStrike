import pygame
import random
from settings import *
from utils import resource_path

# How many coins to place per platform
COINS_PER_PLATFORM = 3
# How many coins to place per ground segment (per 100px of width)
COINS_PER_100PX_GROUND = 2

# Shared coin image — loaded once
_COIN_IMAGE = None


def _get_coin_image():
    global _COIN_IMAGE
    if _COIN_IMAGE is None:
        raw = pygame.image.load(resource_path("assets/coin.png")).convert_alpha()
        _COIN_IMAGE = pygame.transform.scale(raw, (COIN_WIDTH, COIN_HEIGHT))
    return _COIN_IMAGE


class Coin:
    """A single world coin placed at a fixed position on a surface."""

    def __init__(self, x, y):
        self.image = _get_coin_image()
        self.rect = pygame.Rect(x, y, COIN_WIDTH, COIN_HEIGHT)
        self.collected = False

    def draw(self, screen, camera):
        if not self.collected:
            screen.blit(self.image, camera.apply(self.rect))


def _make_coin_row(surface_rect, count):
    """Return a list of Coin objects evenly spaced across the surface."""
    coins = []
    if count <= 0:
        return coins

    usable_w = surface_rect.width - COIN_WIDTH * 2
    if usable_w <= 0:
        # Surface too narrow — place one coin in the centre
        cx = surface_rect.centerx - COIN_WIDTH // 2
        cy = surface_rect.top - COIN_HEIGHT - 6
        return [Coin(cx, cy)]

    # Space coins evenly; cap count so they fit
    max_fit = max(1, usable_w // (COIN_WIDTH + 4))
    count = min(count, max_fit)

    if count == 1:
        positions = [surface_rect.centerx - COIN_WIDTH // 2]
    else:
        step = usable_w // (count - 1) if count > 1 else 0
        start_x = surface_rect.left + COIN_WIDTH
        positions = [start_x + i * step for i in range(count)]

    coin_y = surface_rect.top - COIN_HEIGHT - 6
    for x in positions:
        coins.append(Coin(x, coin_y))
    return coins


class CoinManager:
    """
    Manages all world coins. Coins are placed in neat rows on every platform
    and ground segment. When WorldManager extends the world, update_surfaces()
    is called and new coins are generated for the new terrain.
    """

    def __init__(self, platforms, ground_segments):
        self.coins = []
        # Track by world-x position instead of Python id() — id() can be reused
        # after pruning, causing new surfaces to be mistaken for already-seen ones.
        self._seen_platform_xs: set = set()
        self._seen_ground_xs: set = set()
        self._add_surfaces(platforms, ground_segments)

    # ------------------------------------------------------------------
    def update_surfaces(self, platforms, ground_segments):
        """Called by WorldManager when new terrain is added."""
        self._add_surfaces(platforms, ground_segments)

    def _add_surfaces(self, platforms, ground_segments):
        """Generate coin rows for any surface we haven't seen yet."""
        for surf in platforms:
            key = surf.rect.x
            if key in self._seen_platform_xs:
                continue
            self._seen_platform_xs.add(key)

            count = COINS_PER_PLATFORM
            self.coins.extend(_make_coin_row(surf.rect, count))

        for surf in ground_segments:
            key = surf.rect.x
            if key in self._seen_ground_xs:
                continue
            self._seen_ground_xs.add(key)

            count = max(1, int(surf.rect.width / 100) * COINS_PER_100PX_GROUND)
            count = min(count, 8)  # cap ground coins
            self.coins.extend(_make_coin_row(surf.rect, count))

    # ------------------------------------------------------------------
    def update(self, player):
        """Check collection for all coins near the player. Returns number collected this frame."""
        collected = 0
        # Only check coins within 2 screen-widths of the player — coins further
        # away can't possibly be touched, so skip them entirely.
        px = player.rect.centerx
        cull_dist = SCREEN_WIDTH * 2
        for coin in self.coins:
            if coin.collected:
                continue
            if abs(coin.rect.centerx - px) > cull_dist:
                continue
            if coin.rect.colliderect(player.rect):
                coin.collected = True
                player.coins_collected += 1
                player.coins_earned += 1
                collected += 1
        return collected

    def draw(self, screen, camera):
        # Cull coins outside the visible camera window — avoids blit calls for
        # coins the player can't see. screen_left/right are world-space bounds.
        screen_left = -camera.offset_x - COIN_WIDTH
        screen_right = -camera.offset_x + SCREEN_WIDTH + COIN_WIDTH
        for coin in self.coins:
            if screen_left <= coin.rect.x <= screen_right:
                coin.draw(screen, camera)

    def prune(self, player_world_x, prune_behind):
        """Remove collected coins and coins far behind the player."""
        cutoff = player_world_x - prune_behind
        self.coins = [
            c for c in self.coins if not c.collected and c.rect.right > cutoff
        ]
