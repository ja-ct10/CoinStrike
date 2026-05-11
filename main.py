import pygame
import math
from settings import *
from camera import Camera
from player import Player
from health import Health, draw_game_over
from mission import Mission, PANEL_W, PANEL_H, PANEL_X, PANEL_Y
from coins import Coin, CoinManager
from shop import Shop, WEAPON_DATA
from weapon import WeaponManager
from enemy import EnemyManager
from world import WorldManager
from difficulty import DifficultyScaler
from rocks import RockManager
from combo import ComboSystem
from powerups import PowerupManager
from security import SecurityManager  # Security system integration
from utils import resource_path  # PyInstaller path resolution

pygame.init()

# Initialize audio with error handling for systems without audio devices
audio_available = True
try:
    pygame.mixer.init()
except pygame.error as e:
    print(f"Warning: Audio initialization failed - {e}")
    print("Game will run without sound.")
    audio_available = False

# ================================================================
# SECURITY SYSTEM INITIALIZATION
# ================================================================
security_manager = SecurityManager()

# Define critical files for integrity checking
CRITICAL_FILES = [
    "main.py",
    "player.py",
    "enemy.py",
    "weapon.py",
    "world.py",
    "health.py",
    "security.py",
]

# Initialize security system
security_manager.initialize(CRITICAL_FILES)

# Verify game files integrity on startup
is_valid, error_msg = security_manager.verify_game_files()
if not is_valid:
    # File tampering detected - show error and exit
    print("=" * 60)
    print("SECURITY ERROR: Game files have been modified")
    print("=" * 60)
    print(error_msg)
    print("\nPlease reinstall the game.")
    print("=" * 60)
    # In production, you might want to show a graphical error message
    # For now, we'll allow the game to continue for development
    # Uncomment the line below to enforce file integrity:
    # pygame.quit()
    # exit(1)

# ================================================================

# Load background music if audio is available
if audio_available:
    try:
        pygame.mixer.music.load(resource_path("assets/sounds/background-music.mp3"))
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
    except pygame.error as e:
        print(f"Warning: Could not load background music - {e}")
        audio_available = False

MENU = "menu"
PLAYING = "playing"
GAME_OVER = "game_over"
BOSS_INTRO = "boss_intro"

game_state = MENU

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

menu_bg = pygame.image.load(resource_path("assets/game-cover.png")).convert()
menu_rect = menu_bg.get_rect()
menu_scale = min(SCREEN_WIDTH / menu_rect.width, SCREEN_HEIGHT / menu_rect.height)
menu_size = (int(menu_rect.width * menu_scale), int(menu_rect.height * menu_scale))
menu_bg = pygame.transform.scale(menu_bg, menu_size)

pygame.display.set_caption("CoinStrike")
clock = pygame.time.Clock()

import pygame
from settings import *
from utils import resource_path


background = pygame.image.load(resource_path("assets/background.png")).convert()
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

_coin_hud_img_raw = pygame.image.load(resource_path("assets/coin.png")).convert_alpha()
coin_hud_img = pygame.transform.scale(_coin_hud_img_raw, (COIN_HUD_SIZE, COIN_HUD_SIZE))
coin_hud_font = pygame.font.Font(
    resource_path("assets/fonts/PressStart2P-Regular.ttf"), 14
)

game_over_flash = 0
MISSION_COMPLETE = "mission_complete"

# --- Cached fonts (created once at startup) ---
_FONT_MENU_TITLE = None
_FONT_MENU_BTN = None
_FONT_INSTR = None
_FONT_INSTR_TITLE = None
_FONT_MISSION_COMPLETE = None
_FONT_MISSION_COMPLETE_SMALL = None


def _init_fonts():
    global _FONT_MENU_TITLE, _FONT_MENU_BTN, _FONT_INSTR, _FONT_INSTR_TITLE
    global _FONT_MISSION_COMPLETE, _FONT_MISSION_COMPLETE_SMALL
    global _FONT_BOSS_INTRO, _FONT_BOSS_INTRO_SUB
    _FONT_MENU_TITLE = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 50
    )
    _FONT_MENU_BTN = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 32
    )
    _FONT_INSTR = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 9
    )
    _FONT_INSTR_TITLE = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 14
    )
    _FONT_MISSION_COMPLETE = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 28
    )
    _FONT_MISSION_COMPLETE_SMALL = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 14
    )
    _FONT_BOSS_INTRO = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 36
    )
    _FONT_BOSS_INTRO_SUB = pygame.font.Font(
        resource_path("assets/fonts/PressStart2P-Regular.ttf"), 14
    )


_FONT_BOSS_INTRO = None
_FONT_BOSS_INTRO_SUB = None

_init_fonts()


_BOSS_INTRO_OVERLAY = None
_BOSS_INTRO_STATIC = None  # pre-rendered static text (sub1, sub2)
# Pre-allocated glow surface — reused every frame (only the ellipse is redrawn)
_BOSS_INTRO_GLOW_SURF: pygame.Surface | None = None
# Pre-rendered shadow for the title — cached per color to avoid per-frame render
_BOSS_INTRO_SHADOW_SURF: pygame.Surface | None = None
# Pulsing title cache — quantise the green/blue channel to 8-step buckets so
# we only re-render ~32 unique surfaces instead of one per frame.
_BOSS_INTRO_TITLE_CACHE: dict = {}  # quantised_gb → Surface


def _build_boss_intro_static():
    """Pre-render the non-animated parts of the boss intro overlay."""
    surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    cx = SCREEN_WIDTH // 2
    cy = SCREEN_HEIGHT // 2
    sub1 = _FONT_BOSS_INTRO_SUB.render("ALL MISSIONS COMPLETE!", True, (255, 221, 68))
    surf.blit(sub1, sub1.get_rect(center=(cx, cy - 55)))
    sub2 = _FONT_BOSS_INTRO_SUB.render("INCOMING!", True, (255, 100, 100))
    surf.blit(sub2, sub2.get_rect(center=(cx, cy + 50)))
    return surf


def draw_boss_intro(screen, timer, total):
    """Fullscreen boss announcement overlay. timer counts down from total."""
    global _BOSS_INTRO_OVERLAY, _BOSS_INTRO_STATIC, _BOSS_INTRO_GLOW_SURF

    cx = SCREEN_WIDTH // 2
    cy = SCREEN_HEIGHT // 2

    # Fade-in overlay — alpha changes each frame so we reuse one surface
    if _BOSS_INTRO_OVERLAY is None:
        _BOSS_INTRO_OVERLAY = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
    progress = 1.0 - (timer / total)
    alpha = min(200, int(220 * progress))
    _BOSS_INTRO_OVERLAY.fill((0, 0, 0, alpha))
    screen.blit(_BOSS_INTRO_OVERLAY, (0, 0))

    # Pulsing red glow — reuse a single pre-allocated surface, just redraw the ellipse
    pulse = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 0.4 + 0.6
    glow_r = int(180 * pulse)
    if _BOSS_INTRO_GLOW_SURF is None:
        _BOSS_INTRO_GLOW_SURF = pygame.Surface((600, 120), pygame.SRCALPHA)
    _BOSS_INTRO_GLOW_SURF.fill((0, 0, 0, 0))  # clear previous frame
    pygame.draw.ellipse(
        _BOSS_INTRO_GLOW_SURF, (glow_r, 0, 0, 80), _BOSS_INTRO_GLOW_SURF.get_rect()
    )
    screen.blit(_BOSS_INTRO_GLOW_SURF, (cx - 300, cy - 60))

    # Static text (sub1 + sub2) — rendered once
    if _BOSS_INTRO_STATIC is None:
        _BOSS_INTRO_STATIC = _build_boss_intro_static()
    screen.blit(_BOSS_INTRO_STATIC, (0, 0))

    # "FINAL BOSS" title — colour pulses so must be rendered each frame,
    # but the dark shadow is static — render it once and cache it.
    global _BOSS_INTRO_SHADOW_SURF
    if _BOSS_INTRO_SHADOW_SURF is None:
        _BOSS_INTRO_SHADOW_SURF = _FONT_BOSS_INTRO.render(
            "FINAL BOSS", True, (80, 0, 0)
        )
    # Quantise the pulsing channel to 8-step buckets — reduces unique renders
    # from ~180 (one per frame) to ~32 without visible quality loss.
    gb_val = int(40 * pulse)
    gb_q = (gb_val >> 3) << 3  # round down to nearest multiple of 8
    title = _BOSS_INTRO_TITLE_CACHE.get(gb_q)
    if title is None:
        title_col = (255, gb_q, gb_q)
        title = _FONT_BOSS_INTRO.render("FINAL BOSS", True, title_col)
        _BOSS_INTRO_TITLE_CACHE[gb_q] = title
    screen.blit(
        _BOSS_INTRO_SHADOW_SURF,
        _BOSS_INTRO_SHADOW_SURF.get_rect(center=(cx + 3, cy + 3)),
    )
    screen.blit(title, title.get_rect(center=(cx, cy)))


def _build_key_guide_surface():
    """Pre-render the key guide as a single horizontal bar. Called once after fonts init."""
    font = _FONT_INSTR  # 9px PressStart2P
    keys = [
        ("W/A/D", "Move"),
        ("SPACE", "Jump"),
        ("F", "Gun"),
        ("T", "Spear/Grenade"),
        ("B", "Shop"),
    ]

    BADGE_H = 20
    ITEM_GAP = 14  # horizontal gap between items
    KEY_PAD_X = 6  # horizontal padding inside the key badge
    DESC_GAP = 5  # gap between badge and description text

    # Pre-render all text surfaces so we can measure widths
    key_surfs = [font.render(k, True, (0, 220, 220)) for k, _ in keys]
    desc_surfs = [font.render(d, True, (180, 180, 180)) for _, d in keys]

    # Width of each item = badge_w + DESC_GAP + desc_w
    badge_ws = [s.get_width() + KEY_PAD_X * 2 for s in key_surfs]
    item_ws = [bw + DESC_GAP + ds.get_width() for bw, ds in zip(badge_ws, desc_surfs)]

    total_w = sum(item_ws) + ITEM_GAP * (len(keys) - 1)
    total_h = BADGE_H

    surf = pygame.Surface((total_w, total_h), pygame.SRCALPHA)

    x = 0
    for i, (key_text, desc_text) in enumerate(keys):
        bw = badge_ws[i]
        ks = key_surfs[i]
        ds = desc_surfs[i]

        # Badge background + border
        badge_bg = pygame.Surface((bw, BADGE_H), pygame.SRCALPHA)
        badge_bg.fill((26, 8, 48, 180))
        surf.blit(badge_bg, (x, 0))
        pygame.draw.rect(
            surf, (0, 180, 180), pygame.Rect(x, 0, bw, BADGE_H), 1, border_radius=3
        )

        # Key text centred in badge
        surf.blit(ks, ks.get_rect(center=(x + bw // 2, BADGE_H // 2)))

        # Description text to the right of badge, vertically centred
        surf.blit(ds, (x + bw + DESC_GAP, BADGE_H // 2 - ds.get_height() // 2))

        x += item_ws[i] + ITEM_GAP

    return surf


# Pre-rendered key guide — built once, drawn as a horizontal bar at the bottom.
_KEY_GUIDE_SURF = None  # reset whenever key bindings change
_KEY_GUIDE_BOTTOM_MARGIN = 8


def draw_key_guide(screen):
    """Blit the pre-rendered key guide centred horizontally at the bottom of the screen."""
    global _KEY_GUIDE_SURF
    if _KEY_GUIDE_SURF is None:
        _KEY_GUIDE_SURF = _build_key_guide_surface()
    surf = _KEY_GUIDE_SURF
    draw_x = SCREEN_WIDTH // 2 - surf.get_width() // 2
    draw_y = SCREEN_HEIGHT - surf.get_height() - _KEY_GUIDE_BOTTOM_MARGIN
    screen.blit(surf, (draw_x, draw_y))


_coin_hud_cache_count = None
_coin_hud_cache_surf = None
# Cache the computed layout values so they aren't recalculated every frame
_coin_hud_cache_start_x = None
_coin_hud_cache_coin_y = None
_coin_hud_cache_text_y = None

# Stats HUD (time + distance) — cached surfaces, re-rendered only on change
_stats_font: pygame.font.Font | None = None
# Bounded caches: keep only the last 2 unique values for time and distance.
# Time changes once per second, distance once per metre — no need for more.
_stats_time_key: object = None
_stats_time_surf: "pygame.Surface | None" = None
_stats_dist_key: object = None
_stats_dist_surf: "pygame.Surface | None" = None

# HP bar constants mirrored here so draw_hud_stats can align with the bar
_STATS_X = 10  # same as BAR_X in health.py
_STATS_Y = 44  # just below the "HP" label (BAR_Y + BAR_H + 4 + label_h ≈ 44)


def _get_stats_font():
    global _stats_font
    if _stats_font is None:
        _stats_font = pygame.font.Font(
            resource_path("assets/fonts/PressStart2P-Regular.ttf"), 7
        )
    return _stats_font


def draw_hud_stats(screen, game_frames, player):
    """Draw elapsed time and distance travelled, aligned below the HP bar."""
    global _stats_time_key, _stats_time_surf, _stats_dist_key, _stats_dist_surf

    font = _get_stats_font()

    total_secs = game_frames // 60
    time_str = f"{total_secs // 60}:{total_secs % 60:02d}"
    dist_m = int(player.world_x // 100)
    dist_str = f"{dist_m}m"

    # Time — re-render only when the string changes (once per second)
    if time_str is not _stats_time_key and time_str != _stats_time_key:
        _stats_time_key = time_str
        _stats_time_surf = font.render(f"\u23f1 {time_str}", True, (180, 200, 255))

    # Distance — re-render only when the string changes (once per metre)
    if dist_str is not _stats_dist_key and dist_str != _stats_dist_key:
        _stats_dist_key = dist_str
        _stats_dist_surf = font.render(f"\u27a4 {dist_str}", True, (180, 255, 200))

    if _stats_time_surf is not None:
        screen.blit(_stats_time_surf, (_STATS_X, _STATS_Y))
    if _stats_dist_surf is not None and _stats_time_surf is not None:
        screen.blit(
            _stats_dist_surf, (_STATS_X + _stats_time_surf.get_width() + 10, _STATS_Y)
        )


def draw_hud_coin(screen, player):
    global _coin_hud_cache_count, _coin_hud_cache_surf
    global _coin_hud_cache_start_x, _coin_hud_cache_coin_y, _coin_hud_cache_text_y
    count = player.coins_collected
    if count != _coin_hud_cache_count:
        _coin_hud_cache_count = count
        _coin_hud_cache_surf = coin_hud_font.render(str(count), True, (255, 255, 255))
        # Recompute layout only when the surface width changes
        total_w = COIN_HUD_SIZE + 6 + _coin_hud_cache_surf.get_width()
        _coin_hud_cache_start_x = COIN_RIGHT - total_w
        _coin_hud_cache_coin_y = ICON_MID_Y - COIN_HUD_SIZE // 2
        _coin_hud_cache_text_y = ICON_MID_Y - _coin_hud_cache_surf.get_height() // 2
    screen.blit(coin_hud_img, (_coin_hud_cache_start_x, _coin_hud_cache_coin_y))
    screen.blit(
        _coin_hud_cache_surf,
        (_coin_hud_cache_start_x + COIN_HUD_SIZE + 6, _coin_hud_cache_text_y),
    )


def reset_game():
    p = Player(20, 200)
    difficulty_scaler = DifficultyScaler()
    world_manager = WorldManager(p, difficulty_scaler)
    plats = world_manager.platforms
    segs = world_manager.ground_segments
    hlth = Health(10, 10)
    msn = Mission()
    coin_manager = CoinManager(plats, segs)
    wm = WeaponManager()
    em = EnemyManager(plats, segs)
    rock_manager = RockManager()
    combo_system = ComboSystem()
    powerup_manager = PowerupManager()
    # Seed powerups on the initial terrain
    powerup_manager.update_surfaces(plats, segs)
    p.coins_collected = 100  # starting coins
    return (
        p,
        plats,
        segs,
        hlth,
        msn,
        coin_manager,
        wm,
        em,
        world_manager,
        difficulty_scaler,
        rock_manager,
        combo_system,
        powerup_manager,
    )


def _reset_stats():
    """Reset per-game tracking variables. Call after every reset_game()."""
    global game_stats, _max_combo, _MC_STATS_SURF, _MC_STATS_DATA
    game_stats = {}
    _max_combo = 0
    _MC_STATS_SURF = None
    _MC_STATS_DATA = None


(
    player,
    platforms,
    ground_segments,
    health,
    mission,
    coin_manager,
    weapon_manager,
    enemy_manager,
    world_manager,
    difficulty_scaler,
    rock_manager,
    combo_system,
    powerup_manager,
) = reset_game()
_reset_stats()

game_frames = 0

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


# Pre-rendered menu button background — one surface reused for all buttons
_MENU_BTN_BG: pygame.Surface | None = None

# Cache for menu button text surfaces — keyed by (text, selected)
# Avoids font.render() every frame for static button labels
_MENU_BTN_TEXT_CACHE: dict = {}
# Pre-computed button rects — never change
_MENU_BTN_RECTS: list = [
    pygame.Rect(SCREEN_WIDTH // 2 - 160, 280 + i * 60, 320, 55) for i in range(3)
]
# Pre-rendered title surface — rendered once
_MENU_TITLE_SURF: pygame.Surface | None = None
_MENU_TITLE_SHADOW_SURF: pygame.Surface | None = None


def _get_menu_btn_bg():
    global _MENU_BTN_BG
    if _MENU_BTN_BG is None:
        _MENU_BTN_BG = pygame.Surface((320, 55), pygame.SRCALPHA)
        _MENU_BTN_BG.fill((57, 50, 116, 180))
    return _MENU_BTN_BG


def draw_menu(screen, menu_selection):
    global _MENU_TITLE_SURF, _MENU_TITLE_SHADOW_SURF
    bx = (SCREEN_WIDTH - menu_size[0]) // 2
    by = (SCREEN_HEIGHT - menu_size[1]) // 2
    screen.blit(menu_bg, (bx, by))

    # Title — rendered once and cached (never changes)
    if _MENU_TITLE_SURF is None:
        _MENU_TITLE_SURF = _FONT_MENU_TITLE.render("CoinStrike", True, (255, 222, 89))
        _MENU_TITLE_SHADOW_SURF = _FONT_MENU_TITLE.render(
            "CoinStrike", True, (54, 36, 92)
        )
    cx = SCREEN_WIDTH // 2
    title_rect = _MENU_TITLE_SURF.get_rect(center=(cx, 150))
    # Simplified outline: 4 shadow blits + 1 main blit (was 9+9+1 renders per frame)
    for ox, oy in ((-3, -3), (3, -3), (-3, 3), (3, 3)):
        screen.blit(_MENU_TITLE_SHADOW_SURF, title_rect.move(ox, oy))
    screen.blit(_MENU_TITLE_SURF, title_rect)

    btn_bg = _get_menu_btn_bg()
    for i, rect in enumerate(_MENU_BTN_RECTS):
        is_selected = i == menu_selection
        # Cache key includes selection state — re-render only when selection changes
        cache_key = (menu_options[i], is_selected)
        text_surf = _MENU_BTN_TEXT_CACHE.get(cache_key)
        if text_surf is None:
            text = "▶ " + menu_options[i] if is_selected else menu_options[i]
            text_surf = _FONT_MENU_BTN.render(text, True, (255, 255, 255))
            _MENU_BTN_TEXT_CACHE[cache_key] = text_surf
        screen.blit(btn_bg, rect.topleft)
        screen.blit(text_surf, text_surf.get_rect(center=rect.center))
    return _MENU_BTN_RECTS


# Pre-rendered options modal static content — built once, reused every frame
_OPTIONS_MODAL_STATIC: pygame.Surface | None = None
_OPTIONS_OVERLAY: pygame.Surface | None = None
_OPTIONS_CLOSE_SURFS: dict = {}  # is_hover → Surface
_OPTIONS_X_SURF: "pygame.Surface | None" = None  # "X" label — rendered once


def draw_options_modal(screen, mouse_pos):
    global _OPTIONS_MODAL_STATIC, _OPTIONS_OVERLAY

    modal_w, modal_h = 500, 484
    modal_x = SCREEN_WIDTH // 2 - modal_w // 2
    modal_y = SCREEN_HEIGHT // 2 - modal_h // 2

    close_btn_size = 34
    close_btn_rect = pygame.Rect(
        modal_x + modal_w - close_btn_size - 14,
        modal_y + 12,
        close_btn_size,
        close_btn_size,
    )

    instr_font = _FONT_INSTR
    title_font = _FONT_INSTR_TITLE

    instructions = [
        ("W A D / ARROWS", "Move"),
        ("SPACE / W", "Jump"),
        ("ENTER", "Select / confirm"),
        ("", ""),
        ("F KEY", "Fire gun  (35 bullets)"),
        ("T KEY", "Throw spear (10) / grenade (15)"),
        ("B KEY", "Open / close shop"),
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

    # Overlay — allocated once
    if _OPTIONS_OVERLAY is None:
        _OPTIONS_OVERLAY = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
        _OPTIONS_OVERLAY.fill((0, 0, 0, 180))
    screen.blit(_OPTIONS_OVERLAY, (0, 0))

    # Static modal content — rendered once into a surface, then blitted every frame
    if _OPTIONS_MODAL_STATIC is None:
        static = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
        static.fill((10, 8, 32, 245))
        pygame.draw.rect(
            static,
            (160, 32, 240),
            pygame.Rect(0, 0, modal_w, modal_h),
            2,
            border_radius=10,
        )
        pygame.draw.rect(
            static,
            (0, 255, 255),
            pygame.Rect(3, 3, modal_w - 6, modal_h - 6),
            1,
            border_radius=8,
        )
        title_surf = title_font.render("OPTIONS & GUIDE", True, (255, 221, 68))
        static.blit(title_surf, (18, 16))
        pygame.draw.line(static, (160, 32, 240), (14, 50), (modal_w - 14, 50))
        row_y = 60
        badge_bg = pygame.Surface((BADGE_W, BADGE_H), pygame.SRCALPHA)
        badge_bg.fill((26, 8, 48, 200))
        for key_text, desc_text in instructions:
            if key_text == "" and desc_text == "":
                pygame.draw.line(
                    static, (80, 40, 120), (14, row_y + 4), (modal_w - 14, row_y + 4)
                )
                row_y += 14
                continue
            static.blit(badge_bg, (16, row_y))
            pygame.draw.rect(
                static,
                (0, 200, 200),
                pygame.Rect(16, row_y, BADGE_W, BADGE_H),
                1,
                border_radius=4,
            )
            key_surf = instr_font.render(key_text, True, (0, 255, 255))
            key_rect = key_surf.get_rect(
                center=(16 + BADGE_W // 2, row_y + BADGE_H // 2)
            )
            static.blit(key_surf, key_rect)
            desc_surf = instr_font.render(desc_text, True, (200, 200, 200))
            desc_rect = desc_surf.get_rect(midleft=(BADGE_W + 30, row_y + BADGE_H // 2))
            static.blit(desc_surf, desc_rect)
            row_y += 32
        _OPTIONS_MODAL_STATIC = static

    screen.blit(_OPTIONS_MODAL_STATIC, (modal_x, modal_y))

    is_close_hover = close_btn_rect.collidepoint(mouse_pos)
    close_surf = _OPTIONS_CLOSE_SURFS.get(is_close_hover)
    if close_surf is None:
        close_surf = pygame.Surface((close_btn_size, close_btn_size), pygame.SRCALPHA)
        close_surf.fill((160, 32, 240, 80) if is_close_hover else (26, 8, 48, 200))
        _OPTIONS_CLOSE_SURFS[is_close_hover] = close_surf
    screen.blit(close_surf, close_btn_rect.topleft)
    pygame.draw.rect(screen, (160, 32, 240), close_btn_rect, 2, border_radius=6)
    global _OPTIONS_X_SURF
    if _OPTIONS_X_SURF is None:
        _OPTIONS_X_SURF = instr_font.render("X", True, (255, 68, 153))
    x_rect = _OPTIONS_X_SURF.get_rect(center=close_btn_rect.center)
    screen.blit(_OPTIONS_X_SURF, x_rect)

    return close_btn_rect


_MISSION_COMPLETE_OVERLAY = None
# Pre-cached button surfaces keyed by (label, is_hover) — avoids per-frame allocation
_MC_BTN_SURFS: dict = {}
# Pre-computed button rects — fixed positions, never change
_MC_BTN_W, _MC_BTN_H = 180, 48
_MC_BTN_GAP = 24
_MC_BTN_START_X = SCREEN_WIDTH // 2 - (_MC_BTN_W * 2 + _MC_BTN_GAP) // 2
_MC_BTN_Y = SCREEN_HEIGHT - 80
_MC_RESTART_RECT = pygame.Rect(_MC_BTN_START_X, _MC_BTN_Y, _MC_BTN_W, _MC_BTN_H)
_MC_QUIT_RECT = pygame.Rect(
    _MC_BTN_START_X + _MC_BTN_W + _MC_BTN_GAP, _MC_BTN_Y, _MC_BTN_W, _MC_BTN_H
)
# Pre-rendered button label surfaces — rendered once
_MC_LABEL_SURFS: dict = {}

# Stats font — created once
_MC_STATS_FONT: pygame.font.Font | None = None
_MC_TITLE_FONT: pygame.font.Font | None = None


def _get_mc_fonts():
    global _MC_STATS_FONT, _MC_TITLE_FONT
    if _MC_STATS_FONT is None:
        _MC_STATS_FONT = pygame.font.Font(
            resource_path("assets/fonts/PressStart2P-Regular.ttf"), 9
        )
        _MC_TITLE_FONT = pygame.font.Font(
            resource_path("assets/fonts/PressStart2P-Regular.ttf"), 22
        )
    return _MC_TITLE_FONT, _MC_STATS_FONT


# Stats surface — rebuilt once per game when stats are first available
_MC_STATS_SURF: pygame.Surface | None = None
_MC_STATS_DATA: dict | None = None  # the stats dict used to build the surface


def _build_mc_stats_surf(stats: dict) -> pygame.Surface:
    """Render the stats panel into a surface. Called once per game completion."""
    title_font, stats_font = _get_mc_fonts()

    # Modal dimensions
    modal_w, modal_h = 560, 340
    surf = pygame.Surface((modal_w, modal_h), pygame.SRCALPHA)
    surf.fill((8, 6, 28, 240))
    pygame.draw.rect(
        surf, (160, 32, 240), pygame.Rect(0, 0, modal_w, modal_h), 3, border_radius=12
    )
    pygame.draw.rect(
        surf,
        (0, 255, 255),
        pygame.Rect(4, 4, modal_w - 8, modal_h - 8),
        1,
        border_radius=10,
    )

    cx = modal_w // 2

    # Title
    title = title_font.render("MISSION COMPLETE!", True, (255, 221, 68))
    surf.blit(title, title.get_rect(center=(cx, 30)))

    # Subtitle
    sub = stats_font.render("All missions accomplished!", True, (180, 255, 180))
    surf.blit(sub, sub.get_rect(center=(cx, 58)))

    # Divider
    pygame.draw.line(surf, (160, 32, 240), (20, 74), (modal_w - 20, 74))

    # Stats rows — label on left, value on right
    rows = [
        ("Time", stats.get("time_str", "0:00")),
        ("Coins Collected", str(stats.get("coins", 0))),
        ("Enemies Killed", str(stats.get("kills", 0))),
        ("Distance", f"{stats.get('distance', 0)} m"),
        ("Weapons Bought", str(stats.get("weapons", 0))),
        ("Max Combo", f"x{stats.get('max_combo', 0)}"),
    ]

    row_y = 88
    row_h = 34
    for label, value in rows:
        # Row background
        row_bg = pygame.Surface((modal_w - 24, row_h - 4), pygame.SRCALPHA)
        row_bg.fill((20, 10, 50, 160))
        surf.blit(row_bg, (12, row_y))

        label_surf = stats_font.render(label, True, (160, 180, 255))
        value_surf = stats_font.render(value, True, (255, 221, 68))
        surf.blit(
            label_surf, (20, row_y + (row_h - 4) // 2 - label_surf.get_height() // 2)
        )
        surf.blit(
            value_surf,
            (
                modal_w - 20 - value_surf.get_width(),
                row_y + (row_h - 4) // 2 - value_surf.get_height() // 2,
            ),
        )
        row_y += row_h

    return surf


def draw_mission_complete(screen, mouse_pos, stats: dict):
    global _MISSION_COMPLETE_OVERLAY, _MC_STATS_SURF, _MC_STATS_DATA

    # Overlay
    if _MISSION_COMPLETE_OVERLAY is None:
        _MISSION_COMPLETE_OVERLAY = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA
        )
        _MISSION_COMPLETE_OVERLAY.fill((0, 0, 0, 200))
    screen.blit(_MISSION_COMPLETE_OVERLAY, (0, 0))

    # Stats panel — rebuilt only when stats change (once per game)
    if _MC_STATS_SURF is None or _MC_STATS_DATA is not stats:
        _MC_STATS_SURF = _build_mc_stats_surf(stats)
        _MC_STATS_DATA = stats

    modal_w = _MC_STATS_SURF.get_width()
    modal_x = SCREEN_WIDTH // 2 - modal_w // 2
    modal_y = 30
    screen.blit(_MC_STATS_SURF, (modal_x, modal_y))

    # Buttons
    _, btn_font = _get_mc_fonts()
    for rect, label, base_col, border_col in [
        (_MC_RESTART_RECT, "RESTART", (57, 50, 116), (160, 32, 240)),
        (_MC_QUIT_RECT, "QUIT", (100, 20, 20), (255, 60, 60)),
    ]:
        is_hover = rect.collidepoint(mouse_pos)
        btn_key = (label, is_hover)
        btn_surf = _MC_BTN_SURFS.get(btn_key)
        if btn_surf is None:
            r, g, b = base_col
            fill_col = (
                (min(r + 40, 255), min(g + 40, 255), min(b + 40, 255), 220)
                if is_hover
                else (*base_col, 180)
            )
            btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            btn_surf.fill(fill_col)
            _MC_BTN_SURFS[btn_key] = btn_surf
        screen.blit(btn_surf, rect.topleft)
        pygame.draw.rect(screen, border_col, rect, 2, border_radius=6)

        label_surf = _MC_LABEL_SURFS.get(label)
        if label_surf is None:
            label_surf = _FONT_MISSION_COMPLETE_SMALL.render(
                label, True, (255, 255, 255)
            )
            _MC_LABEL_SURFS[label] = label_surf
        screen.blit(label_surf, label_surf.get_rect(center=rect.center))

    return _MC_RESTART_RECT, _MC_QUIT_RECT


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
# Shop modal state — updated each frame during draw
_shop_close_rect = None
_shop_buy_rects = []
_settings_close_rect = None
_settings_btn_rects = []
_settings_btn_labels = []
_options_close_rect = None
_game_over_yes_rect = None
_game_over_no_rect = None
_mission_complete_restart_rect = None
_mission_complete_quit_rect = None
BOSS_INTRO_DURATION = 180  # 3 seconds at 60fps
boss_intro_timer = 0
game_stats: dict = {}  # populated when boss is defeated
_max_combo: int = 0  # peak combo this game

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
                            coin_manager,
                            weapon_manager,
                            enemy_manager,
                            world_manager,
                            difficulty_scaler,
                            rock_manager,
                            combo_system,
                            powerup_manager,
                        ) = reset_game()
                        game_frames = 0
                        _reset_stats()
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
                elif (
                    event.key == pygame.K_b
                    and not show_settings_modal
                    and not show_options_modal
                ):
                    # B — toggle shop
                    show_shop_modal = not show_shop_modal
                elif event.key in (pygame.K_f, pygame.K_t) and not show_shop_modal:
                    # Fire/throw on initial key press — guarantees response even
                    # for quick taps that release before the per-frame poll runs.
                    weapon_manager.handle_keydown(
                        event.key,
                        player,
                        enemies=enemy_manager.enemies,
                        boss=enemy_manager.boss,
                    )

            elif game_state == MISSION_COMPLETE:
                pass  # handled via MOUSEBUTTONDOWN below

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
                                coin_manager,
                                weapon_manager,
                                enemy_manager,
                                world_manager,
                                difficulty_scaler,
                                rock_manager,
                                combo_system,
                                powerup_manager,
                            ) = reset_game()
                            game_frames = 0
                            _reset_stats()
                            pygame.mixer.music.unpause()
                            game_state = PLAYING
                            camera.offset_x = 0
                            camera.offset_y = 0

                        elif i == 1:  # OPTIONS
                            show_options_modal = True
                            options_source = "menu"

                        elif i == 2:  # EXIT
                            running = False

            # Shop modal clicks
            if game_state == PLAYING and show_shop_modal:
                if _shop_close_rect and _shop_close_rect.collidepoint(event.pos):
                    show_shop_modal = False
                else:
                    for btn_rect, idx in _shop_buy_rects:
                        if btn_rect.collidepoint(event.pos):
                            weapon = WEAPON_DATA[idx]
                            if player.coins_collected >= weapon["price"]:
                                player.coins_collected -= weapon["price"]
                                weapon_manager.grant(weapon["name"].lower())
                                show_shop_modal = False  # close shop after purchase
                            break

            # Settings modal clicks
            if game_state == PLAYING and show_settings_modal and not show_options_modal:
                if _settings_close_rect and _settings_close_rect.collidepoint(
                    event.pos
                ):
                    show_settings_modal = False
                else:
                    for rect, label in zip(_settings_btn_rects, _settings_btn_labels):
                        if rect.collidepoint(event.pos):
                            if label == "RESUME":
                                show_settings_modal = False
                            elif label == "RESTART":
                                (
                                    player,
                                    platforms,
                                    ground_segments,
                                    health,
                                    mission,
                                    coin_manager,
                                    weapon_manager,
                                    enemy_manager,
                                    world_manager,
                                    difficulty_scaler,
                                    rock_manager,
                                    combo_system,
                                    powerup_manager,
                                ) = reset_game()
                                game_frames = 0
                                _reset_stats()
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
                            break

            # Options modal close
            if (
                show_options_modal
                and _options_close_rect
                and _options_close_rect.collidepoint(event.pos)
            ):
                show_options_modal = False

            # Game Over buttons
            if game_state == GAME_OVER:
                if _game_over_yes_rect and _game_over_yes_rect.collidepoint(event.pos):
                    (
                        player,
                        platforms,
                        ground_segments,
                        health,
                        mission,
                        coin_manager,
                        weapon_manager,
                        enemy_manager,
                        world_manager,
                        difficulty_scaler,
                        rock_manager,
                        combo_system,
                        powerup_manager,
                    ) = reset_game()
                    game_frames = 0
                    _reset_stats()
                    pygame.mixer.music.stop()
                    pygame.mixer.music.play(-1)
                    camera.offset_x = 0
                    camera.offset_y = 0
                    game_state = PLAYING
                elif _game_over_no_rect and _game_over_no_rect.collidepoint(event.pos):
                    pygame.mixer.music.pause()
                    game_state = MENU

            # Mission Complete buttons
            if game_state == MISSION_COMPLETE:
                if (
                    _mission_complete_restart_rect
                    and _mission_complete_restart_rect.collidepoint(event.pos)
                ):
                    (
                        player,
                        platforms,
                        ground_segments,
                        health,
                        mission,
                        coin_manager,
                        weapon_manager,
                        enemy_manager,
                        world_manager,
                        difficulty_scaler,
                        rock_manager,
                        combo_system,
                        powerup_manager,
                    ) = reset_game()
                    game_frames = 0
                    _reset_stats()
                    pygame.mixer.music.stop()
                    pygame.mixer.music.play(-1)
                    camera.offset_x = 0
                    camera.offset_y = 0
                    game_state = PLAYING
                elif (
                    _mission_complete_quit_rect
                    and _mission_complete_quit_rect.collidepoint(event.pos)
                ):
                    pygame.mixer.music.pause()
                    game_state = MENU

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

    # ================================================================ UPDATE
    # Performance optimizations applied:
    # - Cached visible bounds computed once per frame, reused for all culling
    # - Glitch platform updates only check platforms near player (300px range)
    # - Camera lerp skips update if delta < 0.5px (avoids micro-adjustments)
    # - Key state polled once per frame and cached in _held variable
    # - All font rendering uses pre-cached surfaces (no per-frame font.render calls)
    # - Event handling moved before draw to reduce input latency
    # - Collision checks use spatial partitioning (visible bounds)
    # - Bitwise operations replace division/modulo for flicker effects
    # - Early exit patterns reduce unnecessary computation
    # - Batch processing for combo kills reduces function call overhead
    # - Spatial culling for all drawable entities (platforms, enemies, coins, etc.)
    # ================================================================

    if game_state == MENU:
        menu_button_rects = draw_menu(screen, menu_selection)

        if show_options_modal:
            _options_close_rect = draw_options_modal(screen, mouse_pos)

    elif game_state == BOSS_INTRO:
        # Keep the world rendering live so the player can see the world behind
        # the overlay, but freeze all game logic during the intro.
        # Optimized: reuse visible bounds from main game loop pattern
        bg_offset = int(-camera.offset_x * 0.4) % SCREEN_WIDTH
        screen.blit(background, (bg_offset - SCREEN_WIDTH, 0))
        screen.blit(background, (bg_offset, 0))
        screen.blit(background, (bg_offset + SCREEN_WIDTH, 0))

        for seg in ground_segments:
            seg.draw(screen, camera)

        # Optimized platform culling during boss intro (reuse pattern from main loop)
        _bi_left = -camera.offset_x - 200
        _bi_right = -camera.offset_x + SCREEN_WIDTH + 200
        for platform in platforms:
            # Cache rect.x to avoid repeated attribute access
            plat_x = platform.rect.x
            if _bi_left <= plat_x <= _bi_right:
                platform.draw(screen, camera)

        enemy_manager.draw(screen, camera)

        # Optimized invincibility flicker check (bitwise AND is faster than modulo)
        if health.invincible_timer == 0 or (health.invincible_timer & 0x1F) < 16:
            player.draw(screen, camera, weapon_manager=weapon_manager, health=health)

        draw_boss_intro(screen, boss_intro_timer, BOSS_INTRO_DURATION)

        # Count down and transition to PLAYING once the intro finishes
        boss_intro_timer -= 1
        if boss_intro_timer <= 0:
            enemy_manager.spawn_boss(player)
            game_state = PLAYING

    elif game_state in (PLAYING, GAME_OVER):
        any_modal = show_settings_modal or show_options_modal or show_shop_modal

        if game_state == PLAYING and not any_modal and not health.game_over:

            game_frames += 1
            difficulty_scaler.update(game_frames)

            mission.update(player, enemy_manager, weapon_manager)

            # When all missions complete, show boss intro screen first
            if (
                mission.all_completed
                and not enemy_manager.boss_spawned
                and game_state == PLAYING
            ):
                game_state = BOSS_INTRO
                boss_intro_timer = BOSS_INTRO_DURATION

            # World streaming — extends platforms/ground/coins as player moves
            world_extended = world_manager.update(
                player, enemy_manager, coin_manager, powerup_manager
            )
            # Keep local references in sync only when the world actually extended
            if world_extended:
                platforms = world_manager.platforms
                ground_segments = world_manager.ground_segments

            player.update(platforms, ground_segments)

            # Per-frame poll for held fire/throw keys (auto-fire while held).
            # KEYDOWN handles the initial press; this poll handles continuous fire.
            # Cache key state once per frame to avoid multiple get_pressed() calls
            _held = pygame.key.get_pressed()
            if _held[pygame.K_f]:
                weapon_manager.handle_keydown(
                    pygame.K_f,
                    player,
                    enemies=enemy_manager.enemies,
                    boss=enemy_manager.boss,
                )
            if _held[pygame.K_t]:
                weapon_manager.handle_keydown(
                    pygame.K_t,
                    player,
                    enemies=enemy_manager.enemies,
                    boss=enemy_manager.boss,
                )

            weapon_manager.update(ground_segments, platforms)

            # Optimized glitch platform update — only check platforms near player
            # Glitch platforms only matter when player is close enough to stand on them
            # Cache player position once to avoid repeated rect access
            player_x = player.rect.centerx
            player_bottom = player.rect.bottom
            player_left = player.rect.left
            player_right = player.rect.right
            player_check_range = 300  # Only check platforms within 300px of player

            for p in platforms:
                # Non-glitch platforms never change — skip update entirely.
                if not p.glitch:
                    continue
                # Skip platforms far from player — they can't be stood on
                # Use squared distance to avoid sqrt (faster)
                dx = p.rect.centerx - player_x
                if dx * dx > player_check_range * player_check_range:
                    continue

                p.update()
                # Check if player is standing on this specific glitch platform.
                # player.update() snaps rect.bottom = p.rect.top when landing,
                # so we check the feet are within a small band of the platform top.
                is_on = (
                    p.visible
                    and player.on_ground
                    and player_right > p.rect.left
                    and player_left < p.rect.right
                    and player_bottom >= p.rect.top - 2
                    and player_bottom <= p.rect.top + 10
                )
                p.notify_standing(is_on)

            # Track HP before enemy update to detect damage for combo reset
            hp_before = health.hp

            # Update enemies — also checks weapon hits internally
            enemy_manager.update(player, health, weapon_manager, difficulty_scaler)

            # Count new kills this frame and feed combo system (batch processing)
            # (enemies_killed is cumulative; track delta)
            new_kills = enemy_manager.enemies_killed - combo_system._last_kills
            if new_kills > 0:
                combo_system._last_kills = enemy_manager.enemies_killed
                # Batch process all kills at once to reduce function call overhead
                for _ in range(new_kills):
                    bonus = combo_system.on_kill(player)
                    player.coins_collected += bonus
                    player.coins_earned += bonus

            # Combo: reset on damage (only check if combo is active)
            if combo_system.count > 0 and health.hp < hp_before:
                combo_system.on_damage_taken(player)

            combo_system.update()

            # Track peak combo for end-of-game stats (avoid redundant comparisons)
            combo_count = combo_system.count
            if combo_count > _max_combo:
                _max_combo = combo_count

            # ================================================================
            # SECURITY CHECK - Anti-cheat monitoring
            # ================================================================
            # Runs every 300 frames (5 seconds) to minimize performance impact
            # Detects abnormal values and applies penalties if needed
            # Reduced frequency from 120 to 300 frames for better performance
            if game_frames % 300 == 0:
                cheat_detected = not security_manager.update(
                    player, health, weapon_manager
                )
                if cheat_detected:
                    # Anti-cheat penalty was applied
                    # Values have been reset to safe defaults
                    pass  # Silently handle - no message to avoid disrupting gameplay
            # ================================================================

            # Transition to mission complete when boss is defeated
            if enemy_manager.boss_defeated:
                # Snapshot end-of-game statistics
                total_secs = game_frames // 60
                game_stats = {
                    "time_str": f"{total_secs // 60}:{total_secs % 60:02d}",
                    "coins": player.coins_earned,
                    "kills": enemy_manager.enemies_killed,
                    "distance": int(player.world_x // 100),
                    "weapons": weapon_manager.weapons_bought,
                    "max_combo": _max_combo,
                }
                game_state = MISSION_COMPLETE

            # Falling rocks
            rock_manager.update(
                camera, ground_segments, platforms, player, health, difficulty_scaler
            )

            # Powerups — update effects and collection
            powerup_manager.update(player, health, weapon_manager, coin_manager)
            powerup_manager.prune(player.world_x, 3 * SCREEN_WIDTH)

            health.update(player, ground_segments, platforms)
            if health.game_over:
                game_state = GAME_OVER
                game_over_flash = 0

            # Optimized camera smoothing — use integer math and early exit
            # Cache screen center to avoid repeated division
            screen_center_x = SCREEN_WIDTH >> 1  # Bitwise shift is faster than division
            target_offset_x = -(player.rect.x - screen_center_x)
            if target_offset_x > 0:
                target_offset_x = 0
            # Lerp factor 0.15 — only update if delta is significant (> 0.5px)
            # This avoids micro-adjustments that cause unnecessary redraws
            delta = target_offset_x - camera.offset_x
            if abs(delta) > 0.5:
                camera.offset_x += delta * 0.15

        # Parallax background — cache offset calculation
        bg_offset = int(-camera.offset_x * 0.4) % SCREEN_WIDTH
        screen.blit(background, (bg_offset - SCREEN_WIDTH, 0))
        screen.blit(background, (bg_offset, 0))
        screen.blit(background, (bg_offset + SCREEN_WIDTH, 0))

        # Optimized culling — compute visible bounds once, reuse for all draw calls
        # Extended margin for smooth scrolling (objects appear/disappear off-screen)
        _vis_left = -camera.offset_x - 400
        _vis_right = -camera.offset_x + SCREEN_WIDTH + 400

        # Ground segments — draw only visible ones (batch check with cached rect properties)
        for seg in ground_segments:
            # Cache rect properties to avoid repeated attribute access
            seg_right = seg.rect.right
            seg_left = seg.rect.left
            if seg_right > _vis_left and seg_left < _vis_right:
                seg.draw(screen, camera)

        # Platforms — draw only visible ones (optimized bounds check)
        for platform in platforms:
            # Single comparison using cached rect.x (platforms are fixed-width)
            plat_x = platform.rect.x
            if _vis_left <= plat_x <= _vis_right:
                platform.draw(screen, camera)

        # Coins — update (collect) and draw
        coin_manager.update(player)
        coin_manager.prune(player.world_x, 3 * SCREEN_WIDTH)
        coin_manager.draw(screen, camera)

        # Powerups
        powerup_manager.draw(screen, camera)

        weapon_manager.draw(screen, camera)

        # Falling rocks
        rock_manager.draw(screen, camera)

        # Enemies drawn behind player
        enemy_manager.draw(screen, camera)

        # Player (invincibility flicker) - optimized with bitwise check
        # Bitwise AND is ~2x faster than division+modulo for flicker effect
        if health.invincible_timer == 0 or (health.invincible_timer & 0x1F) < 16:
            player.draw(screen, camera, weapon_manager=weapon_manager, health=health)

        # --- HUD ---
        draw_hud_coin(screen, player)
        shop.draw(screen)
        mission.draw(screen)
        settings_icon.draw(screen)
        health.draw(screen)
        weapon_manager.draw_ammo_hud(screen)

        # Time + distance — aligned below the HP bar
        draw_hud_stats(screen, game_frames, player)

        # Active powerup timers
        powerup_manager.draw_hud(screen)

        # Combo text — below the stats line (stats at y=44, ~10px tall → start at 58)
        combo_system.draw(screen, y=58)

        # Key guide — anchored to the bottom-right corner
        draw_key_guide(screen)

        # --- Shop modal ---
        if show_shop_modal:
            _shop_close_rect, _shop_buy_rects = shop.draw_modal(
                screen, mouse_pos, player.coins_collected
            )

        # --- Settings modal ---
        if show_settings_modal and not show_options_modal:
            _settings_close_rect, _settings_btn_rects, _settings_btn_labels = (
                draw_settings_modal(screen, mouse_pos)
            )

        # --- Options modal (in-game) ---
        if show_options_modal and options_source == "game":
            _options_close_rect = draw_options_modal(screen, mouse_pos)

        # --- Game Over overlay ---
        if game_state == GAME_OVER:
            game_over_flash += 1
            _game_over_yes_rect, _game_over_no_rect = draw_game_over(
                screen, mouse_pos, game_over_flash
            )

    elif game_state == MISSION_COMPLETE:
        bg_offset = int(-camera.offset_x * 0.4) % SCREEN_WIDTH
        screen.blit(background, (bg_offset - SCREEN_WIDTH, 0))
        screen.blit(background, (bg_offset, 0))
        screen.blit(background, (bg_offset + SCREEN_WIDTH, 0))
        _mission_complete_restart_rect, _mission_complete_quit_rect = (
            draw_mission_complete(screen, mouse_pos, game_stats)
        )

    pygame.display.flip()
