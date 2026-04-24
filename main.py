import pygame
from settings import *
from camera import Camera
from platforms import (
    Platform,
    generate_random_platforms,
    generate_ground_segments,
    GroundSegment,
)
from player import Player
from health import Health, draw_game_over
from mission import Mission, PANEL_W, PANEL_H, PANEL_X, PANEL_Y
from coins import Coin
from shop import Shop, WEAPON_DATA
from weapon import WeaponManager
from enemy import EnemyManager

pygame.init()
pygame.mixer.init()

pygame.mixer.music.load("assets/sounds/background-music.mp3")
pygame.mixer.music.set_volume(0.5)
pygame.mixer.music.play(-1)

MENU = "menu"
PLAYING = "playing"
GAME_OVER = "game_over"

game_state = MENU

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

menu_bg = pygame.image.load("assets/game-cover.png").convert()
menu_rect = menu_bg.get_rect()
menu_scale = min(SCREEN_WIDTH / menu_rect.width, SCREEN_HEIGHT / menu_rect.height)
menu_size = (int(menu_rect.width * menu_scale), int(menu_rect.height * menu_scale))
menu_bg = pygame.transform.scale(menu_bg, menu_size)

pygame.display.set_caption("CoinStrike")
clock = pygame.time.Clock()

background = pygame.image.load("assets/background.png").convert()
background = pygame.transform.scale(background, (SCREEN_WIDTH, SCREEN_HEIGHT))

camera = Camera()

# --- HUD layout (right to left) ---
ICON_TOP = 10
ICON_MID_Y = ICON_TOP + SETTINGS_HEIGHT // 2

settings_icon = Settings(SCREEN_WIDTH - 10, ICON_TOP)

SHOP_RIGHT = PANEL_X - 8
SHOP_TOP = ICON_MID_Y - SHOP_HEIGHT // 2

COIN_HUD_SIZE = 24
COIN_RIGHT = SHOP_RIGHT - SHOP_WIDTH - 10

_coin_hud_img_raw = pygame.image.load("assets/coin.png").convert_alpha()
coin_hud_img = pygame.transform.scale(_coin_hud_img_raw, (COIN_HUD_SIZE, COIN_HUD_SIZE))
coin_hud_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 14)

game_over_flash = 0
MISSION_COMPLETE = "mission_complete"


def draw_hud_coin(screen, player):
    count_surf = coin_hud_font.render(
        str(player.coins_collected), True, (255, 255, 255)
    )
    total_w = COIN_HUD_SIZE + 6 + count_surf.get_width()
    start_x = COIN_RIGHT - total_w
    coin_y = ICON_MID_Y - COIN_HUD_SIZE // 2
    screen.blit(coin_hud_img, (start_x, coin_y))
    text_y = ICON_MID_Y - count_surf.get_height() // 2
    screen.blit(count_surf, (start_x + COIN_HUD_SIZE + 6, text_y))


def reset_game():
    p = Player(20, 200)
    plats = generate_random_platforms(p, num_platforms=14)
    segs = generate_ground_segments()
    hlth = Health(10, 10)
    msn = Mission()
    world_coins = [
        Coin(player=p, platforms=plats, ground=segs[0] if segs else None)
        for _ in range(8)
    ]
    wm = WeaponManager()
    em = EnemyManager(plats, segs)
    p.coins_collected = 100  # starting coins
    return p, plats, segs, hlth, msn, world_coins, wm, em


(
    player,
    platforms,
    ground_segments,
    health,
    mission,
    world_coins,
    weapon_manager,
    enemy_manager,
) = reset_game()

shop = Shop(SHOP_RIGHT, SHOP_TOP)


def draw_text_with_outline(screen, text, font, x, y):
    outer_color = (255, 255, 255)
    middle_color = (54, 36, 92)
    inner_color = (255, 222, 89)
    outer = font.render(text, True, outer_color)
    middle = font.render(text, True, middle_color)
    inner = font.render(text, True, inner_color)
    rect = inner.get_rect(center=(x, y))
    for dx in [-5, 0, 10]:
        for dy in [-5, 0, 10]:
            screen.blit(outer, rect.move(dx, dy))
    for dx in [-2, 0, 5]:
        for dy in [-2, 0, 5]:
            screen.blit(middle, rect.move(dx, dy))
    screen.blit(inner, rect)


def draw_menu(screen, menu_selection):
    bx = (SCREEN_WIDTH - menu_size[0]) // 2
    by = (SCREEN_HEIGHT - menu_size[1]) // 2
    screen.blit(menu_bg, (bx, by))
    font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 50)
    draw_text_with_outline(screen, "CoinStrike", font, SCREEN_WIDTH // 2, 150)
    menu_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 32)

    button_rects = []

    for i in range(3):
        btn_y = 280 + i * 60
        rect = pygame.Rect(SCREEN_WIDTH // 2 - 160, btn_y, 320, 55)
        button_rects.append(rect)

        text = "▶ " + menu_options[i] if i == menu_selection else menu_options[i]
        text_surf = menu_font.render(text, True, (255, 255, 255))
        text_rect = text_surf.get_rect(center=rect.center)

        btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        btn_surf.fill((57, 50, 116, 180))

        screen.blit(btn_surf, rect.topleft)
        screen.blit(text_surf, text_rect)

    return button_rects


def draw_options_modal(screen, mouse_pos):
    modal_w, modal_h = 500, 420
    modal_x = SCREEN_WIDTH // 2 - modal_w // 2
    modal_y = SCREEN_HEIGHT // 2 - modal_h // 2

    close_btn_size = 34
    close_btn_rect = pygame.Rect(
        modal_x + modal_w - close_btn_size - 14,
        modal_y + 12,
        close_btn_size,
        close_btn_size,
    )

    instr_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 9)
    title_font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 14)

    instructions = [
        ("W A D / ARROWS", "Move"),
        ("SPACE / W", "Jump"),
        ("ENTER", "Select / confirm"),
        ("", ""),
        ("F KEY", "Fire gun  (35 bullets)"),
        ("T KEY", "Throw spear (10) / grenade (15)"),
        ("", ""),
        ("COINS", "Collect coins to buy weapons"),
        ("SHOP", "Click shop icon to open store"),
        ("AVOID", "Don't fall into the pits!"),
        ("", ""),
        ("ENEMIES", "Kill them: bullet=1hp, spear/grenade=2hp"),
        ("GLITCH", "Purple platforms disappear!"),
    ]

    BADGE_W = 170
    BADGE_H = 24
    BADGE_X = modal_x + 16
    DESC_X = modal_x + BADGE_W + 30

    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen.blit(overlay, (0, 0))

    modal_surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    modal_surf.fill((10, 8, 32, 245))
    screen.blit(modal_surf, (modal_x, modal_y))

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

    title_surf = title_font.render("OPTIONS & GUIDE", True, (255, 221, 68))
    screen.blit(title_surf, (modal_x + 18, modal_y + 16))

    pygame.draw.line(
        screen,
        (160, 32, 240),
        (modal_x + 14, modal_y + 50),
        (modal_x + modal_w - 14, modal_y + 50),
    )

    row_y = modal_y + 60
    for key_text, desc_text in instructions:
        if key_text == "" and desc_text == "":
            pygame.draw.line(
                screen,
                (80, 40, 120),
                (modal_x + 14, row_y + 4),
                (modal_x + modal_w - 14, row_y + 4),
            )
            row_y += 14
            continue

        badge_surf = pygame.Surface((BADGE_W, BADGE_H), pygame.SRCALPHA)
        badge_surf.fill((26, 8, 48, 200))
        screen.blit(badge_surf, (BADGE_X, row_y))
        pygame.draw.rect(
            screen,
            (0, 200, 200),
            pygame.Rect(BADGE_X, row_y, BADGE_W, BADGE_H),
            1,
            border_radius=4,
        )

        key_surf = instr_font.render(key_text, True, (0, 255, 255))
        key_rect = key_surf.get_rect(
            center=(BADGE_X + BADGE_W // 2, row_y + BADGE_H // 2)
        )
        screen.blit(key_surf, key_rect)

        desc_surf = instr_font.render(desc_text, True, (200, 200, 200))
        desc_rect = desc_surf.get_rect(midleft=(DESC_X, row_y + BADGE_H // 2))
        screen.blit(desc_surf, desc_rect)
        row_y += 32

    is_close_hover = close_btn_rect.collidepoint(mouse_pos)
    close_surf = pygame.Surface((close_btn_size, close_btn_size), pygame.SRCALPHA)
    close_surf.fill((160, 32, 240, 80) if is_close_hover else (26, 8, 48, 200))
    screen.blit(close_surf, close_btn_rect.topleft)
    pygame.draw.rect(screen, (160, 32, 240), close_btn_rect, 2, border_radius=6)
    x_surf = instr_font.render("X", True, (255, 68, 153))
    x_rect = x_surf.get_rect(center=close_btn_rect.center)
    screen.blit(x_surf, x_rect)

    return close_btn_rect


def draw_mission_complete(screen, mouse_pos):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    screen.blit(overlay, (0, 0))

    font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 28)

    text = font.render("MISSION COMPLETE!", True, (255, 221, 68))
    rect = text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
    screen.blit(text, rect)

    btn_rect = pygame.Rect(SCREEN_WIDTH // 2 - 120, SCREEN_HEIGHT // 2 + 20, 240, 60)

    pygame.draw.rect(screen, (57, 50, 116), btn_rect)
    pygame.draw.rect(screen, (160, 32, 240), btn_rect, 2)

    btn_text = font.render("RESTART", True, (255, 255, 255))
    screen.blit(btn_text, btn_text.get_rect(center=btn_rect.center))

    return btn_rect


running = True
mouse_pos = (0, 0)
menu_selection = 0
menu_options = ["START", "OPTIONS", "EXIT"]
menu_button_rects = []
show_options_modal = False
show_settings_modal = False
show_shop_modal = False
options_source = None
game_over_flash = 0

while running:
    clock.tick(FPS)
    mouse_pos = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if game_state == GAME_OVER:
                pass

            elif show_shop_modal:
                if event.key == pygame.K_ESCAPE:
                    show_shop_modal = False

            elif show_options_modal:
                if event.key == pygame.K_ESCAPE:
                    show_options_modal = False

            elif show_settings_modal:
                if event.key == pygame.K_ESCAPE:
                    show_settings_modal = False

            elif game_state == MENU:

                if event.key in (pygame.K_UP, pygame.K_w):
                    menu_selection = max(0, menu_selection - 1)
                elif event.key in (pygame.K_DOWN, pygame.K_s):
                    menu_selection = min(2, menu_selection + 1)
                elif event.key == pygame.K_RETURN:
                    if menu_selection == 0:
                        (
                            player,
                            platforms,
                            ground_segments,
                            health,
                            mission,
                            world_coins,
                            weapon_manager,
                            enemy_manager,
                        ) = reset_game()
                        pygame.mixer.music.unpause()
                        game_state = PLAYING
                        camera.offset_x = 0
                        camera.offset_y = 0
                    elif menu_selection == 1:
                        show_options_modal = True
                        options_source = "menu"
                    elif menu_selection == 2:
                        running = False
                elif event.key == pygame.K_ESCAPE:
                    running = False

            elif game_state == PLAYING:
                if event.key == pygame.K_ESCAPE:
                    show_settings_modal = True
                else:
                    weapon_manager.handle_keydown(event.key, player)

            elif game_state == MISSION_COMPLETE:
                restart_rect = draw_mission_complete(screen, mouse_pos)

                if pygame.mouse.get_pressed()[0]:
                    if restart_rect.collidepoint(mouse_pos):
                        (
                            player,
                            platforms,
                            ground_segments,
                            health,
                            mission,
                            world_coins,
                            weapon_manager,
                            enemy_manager,
                        ) = reset_game()

                        pygame.mixer.music.stop()
                        pygame.mixer.music.play(-1)

                        camera.offset_x = 0
                        camera.offset_y = 0

                        game_state = PLAYING

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if game_state == MENU and not show_options_modal:
                for i, rect in enumerate(menu_button_rects):
                    if rect.collidepoint(event.pos):

                        if i == 0:  # START
                            (
                                player,
                                platforms,
                                ground_segments,
                                health,
                                mission,
                                world_coins,
                                weapon_manager,
                                enemy_manager,
                            ) = reset_game()
                            pygame.mixer.music.unpause()
                            game_state = PLAYING
                            camera.offset_x = 0
                            camera.offset_y = 0

                        elif i == 1:  # OPTIONS
                            show_options_modal = True
                            options_source = "menu"

                        elif i == 2:  # EXIT
                            running = False
            if (
                game_state == PLAYING
                and not show_settings_modal
                and not show_options_modal
                and not show_shop_modal
            ):
                if settings_icon.rect.collidepoint(event.pos):
                    show_settings_modal = True
                elif shop.rect.collidepoint(event.pos):
                    show_shop_modal = True

    # ================================================================ DRAW
    if game_state == MENU:
        menu_button_rects = draw_menu(screen, menu_selection)

        if show_options_modal:
            close_btn_rect = draw_options_modal(screen, mouse_pos)
            if pygame.mouse.get_pressed()[0]:
                if close_btn_rect.collidepoint(mouse_pos):
                    show_options_modal = False

    elif game_state in (PLAYING, GAME_OVER):
        any_modal = show_settings_modal or show_options_modal or show_shop_modal

        if game_state == PLAYING and not any_modal and not health.game_over:

            mission.update(player, enemy_manager, weapon_manager)

            if mission.all_completed:
                game_state = MISSION_COMPLETE
            player.update(platforms, ground_segments)
            weapon_manager.update(ground_segments, platforms)

            for p in platforms:
                p.update()
                is_on = (
                    player.rect.colliderect(p.rect)
                    and player.vel_y >= 0
                    and abs(player.rect.bottom - p.rect.top) <= 15
                )
                p.notify_standing(is_on)

            # Update enemies — also checks weapon hits internally
            enemy_manager.update(player, health, weapon_manager)

            died = health.update(player, ground_segments)
            if health.game_over:
                game_state = GAME_OVER
                game_over_flash = 0

            target_offset_x = -(player.rect.x - SCREEN_WIDTH // 2)
            if target_offset_x > 0:
                target_offset_x = 0
            camera.offset_x += (target_offset_x - camera.offset_x) * 0.15

        # Parallax background
        bg_offset = int(-camera.offset_x * 0.4) % SCREEN_WIDTH
        screen.blit(background, (bg_offset - SCREEN_WIDTH, 0))
        screen.blit(background, (bg_offset, 0))
        screen.blit(background, (bg_offset + SCREEN_WIDTH, 0))

        for seg in ground_segments:
            seg.draw(screen, camera)
        for platform in platforms:
            platform.draw(screen, camera)

        for coin in world_coins:
            player.collect_coin(coin)
        for coin in world_coins:
            coin.draw(screen, player, camera=camera)

        weapon_manager.draw(screen, camera)

        # Enemies drawn behind player
        enemy_manager.draw(screen, camera)

        # Player (invincibility flicker)
        if health.invincible_timer == 0 or (health.invincible_timer // 6) % 2 == 0:
            player.draw(screen, camera, weapon_manager=weapon_manager)

        # --- HUD ---
        draw_hud_coin(screen, player)
        shop.draw(screen)
        mission.draw(screen)
        settings_icon.draw(screen)
        health.draw(screen)
        weapon_manager.draw_ammo_hud(screen)

        # --- Shop modal ---
        if show_shop_modal:
            close_btn_rect, buy_rects = shop.draw_modal(
                screen, mouse_pos, player.coins_collected
            )
            if pygame.mouse.get_pressed()[0]:
                if close_btn_rect.collidepoint(mouse_pos):
                    show_shop_modal = False
                for btn_rect, idx in buy_rects:
                    if btn_rect.collidepoint(mouse_pos):
                        weapon = WEAPON_DATA[idx]
                        if player.coins_collected >= weapon["price"]:
                            player.coins_collected -= weapon["price"]
                            weapon_manager.grant(weapon["name"].lower())

                            if not hasattr(weapon_manager, "weapons_bought"):
                                weapon_manager.weapons_bought = 0
                            weapon_manager.weapons_bought += 1

        # --- Settings modal ---
        if show_settings_modal and not show_options_modal:
            close_btn_rect, btn_rects, btn_labels = draw_settings_modal(
                screen, mouse_pos
            )
            if pygame.mouse.get_pressed()[0]:
                if close_btn_rect.collidepoint(mouse_pos):
                    show_settings_modal = False
                for rect, label in zip(btn_rects, btn_labels):
                    if rect.collidepoint(mouse_pos):
                        if label == "RESUME":
                            show_settings_modal = False
                        elif label == "RESTART":
                            (
                                player,
                                platforms,
                                ground_segments,
                                health,
                                mission,
                                world_coins,
                                weapon_manager,
                                enemy_manager,
                            ) = reset_game()
                            pygame.mixer.music.stop()
                            pygame.mixer.music.play(-1)
                            camera.offset_x = 0
                            camera.offset_y = 0
                            show_settings_modal = False
                            game_state = PLAYING
                        elif label == "OPTIONS":
                            show_options_modal = True
                            options_source = "game"
                        elif label == "QUIT":
                            show_settings_modal = False
                            pygame.mixer.music.pause()
                            game_state = MENU

        # --- Options modal (in-game) ---
        if show_options_modal and options_source == "game":
            close_btn_rect = draw_options_modal(screen, mouse_pos)
            if pygame.mouse.get_pressed()[0]:
                if close_btn_rect.collidepoint(mouse_pos):
                    show_options_modal = False

        # --- Game Over overlay ---
        if game_state == GAME_OVER:
            game_over_flash += 1
            yes_rect, no_rect = draw_game_over(screen, mouse_pos, game_over_flash)
            if pygame.mouse.get_pressed()[0]:
                if yes_rect.collidepoint(mouse_pos):
                    (
                        player,
                        platforms,
                        ground_segments,
                        health,
                        mission,
                        world_coins,
                        weapon_manager,
                        enemy_manager,
                    ) = reset_game()
                    pygame.mixer.music.stop()
                    pygame.mixer.music.play(-1)
                    camera.offset_x = 0
                    camera.offset_y = 0
                    game_state = PLAYING
                elif no_rect.collidepoint(mouse_pos):
                    pygame.mixer.music.pause()
                    game_state = MENU

    pygame.display.flip()
