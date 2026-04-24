import pygame
from settings import *

WEAPON_DATA = [
    {"name": "SPEAR", "asset": "spear-box", "price": 30},
    {"name": "GUN", "asset": "gun-box", "price": 100},
    {"name": "GRENADE", "asset": "grenade-box", "price": 150},
]


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
        """Draw the shop modal. Returns list of (buy_rect, weapon_index) if hovered."""
        modal_w, modal_h = 480, 340
        modal_x = SCREEN_WIDTH // 2 - modal_w // 2
        modal_y = SCREEN_HEIGHT // 2 - modal_h // 2

        title_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 13)
        label_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 9)
        price_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 10)

        close_btn_size = 34
        close_btn_rect = pygame.Rect(
            modal_x + modal_w - close_btn_size - 14,
            modal_y + 12,
            close_btn_size,
            close_btn_size,
        )

        # Overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))

        # Modal background
        modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
        modal_surf.fill((10, 8, 32, 245))
        screen.blit(modal_surf, (modal_x, modal_y))

        # Pixel border (double-line retro style)
        pygame.draw.rect(
            screen,
            (160, 32, 240),
            pygame.Rect(modal_x, modal_y, modal_w, modal_h),
            3,
            border_radius=10,
        )
        pygame.draw.rect(
            screen,
            (0, 255, 255),
            pygame.Rect(modal_x + 4, modal_y + 4, modal_w - 8, modal_h - 8),
            1,
            border_radius=8,
        )

        # Title
        title_surf = title_font.render("SHOP", True, (255, 221, 68))
        screen.blit(title_surf, (modal_x + 18, modal_y + 16))

        # Divider
        pygame.draw.line(
            screen,
            (160, 32, 240),
            (modal_x + 14, modal_y + 50),
            (modal_x + modal_w - 14, modal_y + 50),
        )

        # Weapon cards
        card_w, card_h = 120, 180
        card_gap = 24
        total_cards_w = len(WEAPON_DATA) * card_w + (len(WEAPON_DATA) - 1) * card_gap
        cards_start_x = modal_x + modal_w // 2 - total_cards_w // 2
        cards_y = modal_y + 68

        buy_rects = []
        for i, (weapon, img) in enumerate(zip(WEAPON_DATA, self.weapon_images)):
            cx = cards_start_x + i * (card_w + card_gap)

            # Card background
            card_rect = pygame.Rect(cx, cards_y, card_w, card_h)
            is_hover = card_rect.collidepoint(mouse_pos)
            card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            card_surf.fill((40, 16, 80, 200) if is_hover else (20, 8, 48, 180))
            screen.blit(card_surf, card_rect.topleft)

            border_col = (0, 255, 255) if is_hover else (160, 32, 240)
            pygame.draw.rect(screen, border_col, card_rect, 2)

            # Weapon image centered in card
            img_rect = img.get_rect(centerx=cx + card_w // 2, top=cards_y + 8)
            screen.blit(img, img_rect)

            # Weapon name
            name_surf = label_font.render(
                weapon["name"], True, (255, 221, 68) if is_hover else (200, 200, 200)
            )
            name_rect = name_surf.get_rect(
                centerx=cx + card_w // 2, top=cards_y + WEAPON_HEIGHT + 12
            )
            screen.blit(name_surf, name_rect)

            # Price row with coin icon
            price_str = f"{weapon['price']}"
            price_surf = price_font.render(price_str, True, (255, 200, 0))
            coin_size = 16
            price_total_w = coin_size + 4 + price_surf.get_width()
            price_x = cx + card_w // 2 - price_total_w // 2
            price_y = name_rect.bottom + 8

            # coin.png icon
            coin_img = pygame.image.load("assets/coin.png").convert_alpha()
            coin_img = pygame.transform.scale(coin_img, (coin_size, coin_size))
            # Vertically center both coin and text around the same midpoint
            row_mid = price_y + coin_size // 2
            coin_draw_y = row_mid - coin_size // 2
            text_draw_y = row_mid - price_surf.get_height() // 2

            screen.blit(coin_img, (price_x, coin_draw_y))
            screen.blit(price_surf, (price_x + coin_size + 4, text_draw_y))
            # BUY button
            can_afford = player_coins >= weapon["price"]
            btn_rect = pygame.Rect(cx + 10, cards_y + card_h - 34, card_w - 20, 26)
            btn_col = (0, 180, 80) if can_afford else (80, 80, 80)
            btn_surf = pygame.Surface(
                (btn_rect.width, btn_rect.height), pygame.SRCALPHA
            )
            btn_surf.fill((*btn_col, 200))
            screen.blit(btn_surf, btn_rect.topleft)
            pygame.draw.rect(
                screen, (0, 255, 120) if can_afford else (120, 120, 120), btn_rect, 2
            )
            buy_label = label_font.render(
                "BUY", True, (255, 255, 255) if can_afford else (160, 160, 160)
            )
            buy_label_rect = buy_label.get_rect(center=btn_rect.center)
            screen.blit(buy_label, buy_label_rect)

            buy_rects.append((btn_rect, i))

        # Close button
        is_close_hover = close_btn_rect.collidepoint(mouse_pos)
        close_surf = pygame.Surface((close_btn_size, close_btn_size), pygame.SRCALPHA)
        close_surf.fill((160, 32, 240, 80) if is_close_hover else (26, 8, 48, 200))
        screen.blit(close_surf, close_btn_rect.topleft)
        pygame.draw.rect(screen, (160, 32, 240), close_btn_rect, 2, border_radius=6)
        x_surf = label_font.render("X", True, (255, 68, 153))
        x_rect = x_surf.get_rect(center=close_btn_rect.center)
        screen.blit(x_surf, x_rect)

        return close_btn_rect, buy_rects
