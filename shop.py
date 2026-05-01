import pygame
from settings import *

WEAPON_DATA = [
    {"name": "SPEAR", "asset": "spear-box", "price": 30},
    {"name": "GUN", "asset": "gun-box", "price": 100},
    {"name": "GRENADE", "asset": "grenade-box", "price": 150},
]

# Coin icon loaded once at module level — reused every frame the shop is open
_SHOP_COIN_IMG: pygame.Surface | None = None
_SHOP_COIN_SIZE = 16

# Per-card surface caches keyed by is_hover — avoids per-frame allocation
_CARD_SURF_CACHE: dict = {}  # is_hover → Surface
_BTN_SURF_CACHE: dict = {}  # (can_afford, is_hover) → Surface
_CLOSE_SURF_CACHE: dict = {}  # is_hover → Surface

# Modal-level surfaces cached at module level — never reallocated after first use
_SHOP_OVERLAY: pygame.Surface | None = None
_SHOP_MODAL_BG: pygame.Surface | None = None

# Modal fonts — created once at module level
_SHOP_TITLE_FONT: pygame.font.Font | None = None
_SHOP_LABEL_FONT: pygame.font.Font | None = None
_SHOP_PRICE_FONT: pygame.font.Font | None = None

# Static text surfaces rendered once — never change
_TITLE_SURF: pygame.Surface | None = None  # "SHOP"
_X_SURF: pygame.Surface | None = None  # "X" on close button

# Per-weapon static text caches — keyed by (weapon_name, is_hover) and price string
_NAME_SURF_CACHE: dict = {}  # (weapon_name, is_hover) → Surface
_PRICE_SURF_CACHE: dict = {}  # price_str → Surface
_BUY_SURF_CACHE: dict = {}  # (can_afford,) → Surface  ("BUY" label)

# Pre-computed layout constants (computed once after fonts are ready)
_MODAL_W = 480
_MODAL_H = 340
_MODAL_X = SCREEN_WIDTH // 2 - _MODAL_W // 2
_MODAL_Y = SCREEN_HEIGHT // 2 - _MODAL_H // 2
_CARD_W = 120
_CARD_H = 180
_CARD_GAP = 24
_CARDS_Y = _MODAL_Y + 68
_CLOSE_BTN_SIZE = 34
_CLOSE_BTN_RECT = pygame.Rect(
    _MODAL_X + _MODAL_W - _CLOSE_BTN_SIZE - 14,
    _MODAL_Y + 12,
    _CLOSE_BTN_SIZE,
    _CLOSE_BTN_SIZE,
)

# Pre-computed per-card rects (fixed positions — computed once at import time)
_total_cards_w = len(WEAPON_DATA) * _CARD_W + (len(WEAPON_DATA) - 1) * _CARD_GAP
_cards_start_x = _MODAL_X + _MODAL_W // 2 - _total_cards_w // 2

_CARD_RECTS: list[pygame.Rect] = []
_BTN_RECTS: list[pygame.Rect] = []
_IMG_RECTS: list[pygame.Rect] = []  # weapon image positions (top-left)

for _i in range(len(WEAPON_DATA)):
    _cx = _cards_start_x + _i * (_CARD_W + _CARD_GAP)
    _CARD_RECTS.append(pygame.Rect(_cx, _CARDS_Y, _CARD_W, _CARD_H))
    _BTN_RECTS.append(pygame.Rect(_cx + 10, _CARDS_Y + _CARD_H - 34, _CARD_W - 20, 26))
    # Weapon image: centered horizontally, 8px from top of card
    _IMG_RECTS.append(
        pygame.Rect(
            _cx + (_CARD_W - WEAPON_WIDTH) // 2,
            _CARDS_Y + 8,
            WEAPON_WIDTH,
            WEAPON_HEIGHT,
        )
    )

# Pre-built buy_rects list — returned every frame without rebuilding
_BUY_RECTS_LIST: list[tuple[pygame.Rect, int]] = [
    (_BTN_RECTS[i], i) for i in range(len(WEAPON_DATA))
]


def _get_shop_fonts():
    global _SHOP_TITLE_FONT, _SHOP_LABEL_FONT, _SHOP_PRICE_FONT
    if _SHOP_TITLE_FONT is None:
        _SHOP_TITLE_FONT = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 13)
        _SHOP_LABEL_FONT = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 9)
        _SHOP_PRICE_FONT = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 10)
    return _SHOP_TITLE_FONT, _SHOP_LABEL_FONT, _SHOP_PRICE_FONT


def _get_shop_coin_img():
    global _SHOP_COIN_IMG
    if _SHOP_COIN_IMG is None:
        raw = pygame.image.load("assets/coin.png").convert_alpha()
        _SHOP_COIN_IMG = pygame.transform.scale(raw, (_SHOP_COIN_SIZE, _SHOP_COIN_SIZE))
    return _SHOP_COIN_IMG


def _ensure_modal_resources():
    """Lazily initialise all cached surfaces and static text renders."""
    global _SHOP_OVERLAY, _SHOP_MODAL_BG, _TITLE_SURF, _X_SURF

    title_font, label_font, price_font = _get_shop_fonts()

    if _SHOP_OVERLAY is None:
        _SHOP_OVERLAY = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        _SHOP_OVERLAY.fill((0, 0, 0, 190))

    if _SHOP_MODAL_BG is None:
        _SHOP_MODAL_BG = pygame.Surface((_MODAL_W, _MODAL_H), pygame.SRCALPHA)
        _SHOP_MODAL_BG.fill((10, 8, 32, 245))

    if _TITLE_SURF is None:
        _TITLE_SURF = title_font.render("SHOP", True, (255, 221, 68))

    if _X_SURF is None:
        _X_SURF = label_font.render("X", True, (255, 68, 153))

    # Pre-render weapon name surfaces for both hover states
    for weapon in WEAPON_DATA:
        for is_hover in (True, False):
            key = (weapon["name"], is_hover)
            if key not in _NAME_SURF_CACHE:
                color = (255, 221, 68) if is_hover else (200, 200, 200)
                _NAME_SURF_CACHE[key] = label_font.render(weapon["name"], True, color)

    # Pre-render price surfaces (static — price never changes)
    for weapon in WEAPON_DATA:
        price_str = str(weapon["price"])
        if price_str not in _PRICE_SURF_CACHE:
            _PRICE_SURF_CACHE[price_str] = price_font.render(
                price_str, True, (255, 200, 0)
            )

    # Pre-render BUY label for both afford states
    for can_afford in (True, False):
        key = (can_afford,)
        if key not in _BUY_SURF_CACHE:
            color = (255, 255, 255) if can_afford else (160, 160, 160)
            _BUY_SURF_CACHE[key] = label_font.render("BUY", True, color)


class Shop:
    def __init__(self, x, y):
        self.image = pygame.image.load("assets/shop.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (SHOP_WIDTH, SHOP_HEIGHT))
        # Position is passed in — align between mission and settings in main.py
        self.rect = self.image.get_rect(topright=(x, y))
        self.is_open = False
        self._load_weapon_images()

    def _load_weapon_images(self):
        self.weapon_images = []
        for w in WEAPON_DATA:
            img = pygame.image.load(f"assets/{w['asset']}.png").convert_alpha()
            img = pygame.transform.scale(img, (WEAPON_WIDTH, WEAPON_HEIGHT))
            self.weapon_images.append(img)

    def toggle(self):
        self.is_open = not self.is_open

    def draw(self, screen):
        screen.blit(self.image, self.rect)

    def draw_modal(self, screen, mouse_pos, player_coins):
        """Draw the shop modal. Returns (close_btn_rect, buy_rects)."""
        _ensure_modal_resources()

        title_font, label_font, price_font = _get_shop_fonts()
        coin_img = _get_shop_coin_img()
        coin_size = _SHOP_COIN_SIZE

        # --- Overlay + modal background (cached surfaces — no allocation) ---
        screen.blit(_SHOP_OVERLAY, (0, 0))
        screen.blit(_SHOP_MODAL_BG, (_MODAL_X, _MODAL_Y))

        # Pixel border (double-line retro style)
        pygame.draw.rect(
            screen,
            (160, 32, 240),
            (_MODAL_X, _MODAL_Y, _MODAL_W, _MODAL_H),
            3,
            border_radius=10,
        )
        pygame.draw.rect(
            screen,
            (0, 255, 255),
            (_MODAL_X + 4, _MODAL_Y + 4, _MODAL_W - 8, _MODAL_H - 8),
            1,
            border_radius=8,
        )

        # Title — cached surface, never re-rendered
        screen.blit(_TITLE_SURF, (_MODAL_X + 18, _MODAL_Y + 16))

        # Divider
        pygame.draw.line(
            screen,
            (160, 32, 240),
            (_MODAL_X + 14, _MODAL_Y + 50),
            (_MODAL_X + _MODAL_W - 14, _MODAL_Y + 50),
        )

        # --- Weapon cards ---
        for i, weapon in enumerate(WEAPON_DATA):
            img = self.weapon_images[i]
            card_rect = _CARD_RECTS[i]
            btn_rect = _BTN_RECTS[i]
            img_rect = _IMG_RECTS[i]
            cx = card_rect.x

            is_hover = card_rect.collidepoint(mouse_pos)

            # Card background — cached per hover state
            card_surf = _CARD_SURF_CACHE.get(is_hover)
            if card_surf is None:
                card_surf = pygame.Surface((_CARD_W, _CARD_H), pygame.SRCALPHA)
                card_surf.fill((40, 16, 80, 200) if is_hover else (20, 8, 48, 180))
                _CARD_SURF_CACHE[is_hover] = card_surf
            screen.blit(card_surf, card_rect.topleft)

            border_col = (0, 255, 255) if is_hover else (160, 32, 240)
            pygame.draw.rect(screen, border_col, card_rect, 2)

            # Weapon image — pre-computed rect
            screen.blit(img, img_rect)

            # Weapon name — cached per (name, hover) state
            name_surf = _NAME_SURF_CACHE[(weapon["name"], is_hover)]
            name_x = cx + _CARD_W // 2 - name_surf.get_width() // 2
            name_y = _CARDS_Y + WEAPON_HEIGHT + 12
            screen.blit(name_surf, (name_x, name_y))

            # Price row with coin icon — price surface cached per price string
            price_str = str(weapon["price"])
            price_surf = _PRICE_SURF_CACHE[price_str]
            price_total_w = coin_size + 4 + price_surf.get_width()
            price_x = cx + _CARD_W // 2 - price_total_w // 2
            price_y = name_y + name_surf.get_height() + 8

            row_mid = price_y + coin_size // 2
            coin_draw_y = row_mid - coin_size // 2
            text_draw_y = row_mid - price_surf.get_height() // 2

            screen.blit(coin_img, (price_x, coin_draw_y))
            screen.blit(price_surf, (price_x + coin_size + 4, text_draw_y))

            # BUY button — background cached per (can_afford, is_hover)
            can_afford = player_coins >= weapon["price"]
            btn_key = (can_afford, is_hover)
            btn_surf = _BTN_SURF_CACHE.get(btn_key)
            if btn_surf is None:
                btn_col = (0, 180, 80) if can_afford else (80, 80, 80)
                btn_surf = pygame.Surface(
                    (btn_rect.width, btn_rect.height), pygame.SRCALPHA
                )
                btn_surf.fill((*btn_col, 200))
                _BTN_SURF_CACHE[btn_key] = btn_surf
            screen.blit(btn_surf, btn_rect.topleft)
            pygame.draw.rect(
                screen, (0, 255, 120) if can_afford else (120, 120, 120), btn_rect, 2
            )

            # BUY label — cached per afford state
            buy_label = _BUY_SURF_CACHE[(can_afford,)]
            buy_label_x = btn_rect.centerx - buy_label.get_width() // 2
            buy_label_y = btn_rect.centery - buy_label.get_height() // 2
            screen.blit(buy_label, (buy_label_x, buy_label_y))

        # --- Close button ---
        is_close_hover = _CLOSE_BTN_RECT.collidepoint(mouse_pos)
        close_surf = _CLOSE_SURF_CACHE.get(is_close_hover)
        if close_surf is None:
            close_surf = pygame.Surface(
                (_CLOSE_BTN_SIZE, _CLOSE_BTN_SIZE), pygame.SRCALPHA
            )
            close_surf.fill((160, 32, 240, 80) if is_close_hover else (26, 8, 48, 200))
            _CLOSE_SURF_CACHE[is_close_hover] = close_surf
        screen.blit(close_surf, _CLOSE_BTN_RECT.topleft)
        pygame.draw.rect(screen, (160, 32, 240), _CLOSE_BTN_RECT, 2, border_radius=6)

        # "X" label — cached static surface
        x_surf = _X_SURF
        x_x = _CLOSE_BTN_RECT.centerx - x_surf.get_width() // 2
        x_y = _CLOSE_BTN_RECT.centery - x_surf.get_height() // 2
        screen.blit(x_surf, (x_x, x_y))

        # Return pre-built list — no per-frame allocation
        return _CLOSE_BTN_RECT, _BUY_RECTS_LIST
