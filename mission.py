import pygame
import random
from settings import *
from utils import resource_path

PANEL_W = 260
PANEL_H = 120  # Increased from 100 to ensure all 3 missions fit comfortably
PANEL_Y = 10
PANEL_X = SCREEN_WIDTH - PANEL_W - 10 - SETTINGS_WIDTH - 8

# ---------------------------------------------------------------------------
# Mission pool — pick 3 at random each game.
# Each entry: (type, text_template, target)
#   type         — used by update() to know which stat to read
#   text_template — f-string with {target} placeholder
#   target        — the goal value
# ---------------------------------------------------------------------------
_MISSION_POOL = [
    # Coin missions
    ("coins", "Collect {target} coins", 50),
    ("coins", "Collect {target} coins", 100),
    ("coins", "Collect {target} coins", 200),
    # Kill missions
    ("kills", "Kill {target} enemies", 5),
    ("kills", "Kill {target} enemies", 15),
    ("kills", "Kill {target} enemies", 25),
    # Weapon purchase missions
    ("weapons", "Buy {target} weapon(s)", 1),
    ("weapons", "Buy {target} weapon(s)", 2),
    ("weapons", "Buy {target} weapon(s)", 3),
    # Survival missions (reach a distance)
    ("distance", "Travel {target}m", 150),
    ("distance", "Travel {target}m", 300),
    ("distance", "Travel {target}m", 450),
]


def _pick_missions():
    """
    Pick 3 missions at random, ensuring no two missions share the same type
    so the player always has a variety of objectives.
    """
    # Group pool by type
    by_type: dict = {}
    for entry in _MISSION_POOL:
        t = entry[0]
        by_type.setdefault(t, []).append(entry)

    types = list(by_type.keys())
    random.shuffle(types)
    chosen_types = types[:3]  # pick 3 distinct types

    missions = []
    for t in chosen_types:
        entry = random.choice(by_type[t])
        mtype, template, target = entry
        missions.append(
            {
                "type": mtype,
                "text": template.format(target=target),
                "target": target,
                "progress": 0,
                "done": False,
            }
        )
    return missions


class Mission:
    def __init__(self):
        self.font_title = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 8)
        self.font_line = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 8)

        self.missions = _pick_missions()

        self.rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
        self.all_completed = False

        # Pre-rendered panel background and title — never change
        self._bg_surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        self._bg_surf.fill((8, 6, 28, 220))
        self._title_surf = self.font_title.render("MISSIONS", True, (255, 221, 68))

        # Cache for mission line surfaces — keyed by (mission_index, progress, done)
        # Using mission index instead of full text reduces key size and comparison cost
        self._line_cache: dict = {}

        # Pre-render static mission text parts (without progress) — never change
        self._mission_text_base: list = [m["text"] for m in self.missions]

        # Track previous progress and done state to avoid redundant cache lookups
        # Initialize to None so first draw always triggers rendering
        self._prev_progress: list = [None, None, None]
        self._prev_done: list = [False, False, False]

        # Pre-render all mission lines on initialization so they appear immediately
        for i, m in enumerate(self.missions):
            text = f"{self._mission_text_base[i]} ({m['progress']}/{m['target']})"
            color = (200, 220, 255)  # Initial color (not done yet)
            surf = self.font_line.render(text, True, color)
            cache_key = (i, m["progress"], m["done"])
            self._line_cache[cache_key] = surf
            self._prev_progress[i] = m["progress"]
            self._prev_done[i] = m["done"]

    def update(self, player, enemy_manager, weapon_manager):
        # Early exit if all missions already complete — avoid redundant checks
        if self.all_completed:
            return

        any_changed = False
        for m in self.missions:
            if m["done"]:
                continue

            mtype = m["type"]
            # Direct attribute access — faster than getattr with defaults
            if mtype == "coins":
                new_progress = player.coins_earned
            elif mtype == "kills":
                new_progress = enemy_manager.enemies_killed
            elif mtype == "weapons":
                new_progress = weapon_manager.weapons_bought
            elif mtype == "distance":
                # Convert world_x pixels to metres (100 px ≈ 1 m)
                new_progress = int(player.world_x // 100)
            else:
                new_progress = 0

            m["progress"] = new_progress

            if new_progress >= m["target"]:
                m["done"] = True
                any_changed = True

        # Only check all_completed when a mission state changed
        if any_changed:
            self.all_completed = all(m["done"] for m in self.missions)

    def draw(self, screen):
        px = PANEL_X
        py = PANEL_Y

        screen.blit(self._bg_surf, (px, py))
        pygame.draw.rect(screen, (0, 200, 220), self.rect, 2)
        pygame.draw.rect(screen, (100, 40, 180), self.rect.inflate(-6, -6), 1)
        screen.blit(self._title_surf, (px + 10, py + 8))
        pygame.draw.line(
            screen, (0, 200, 220), (px + 8, py + 24), (px + PANEL_W - 8, py + 24)
        )

        line_y = py + 32
        for i, m in enumerate(self.missions):
            progress = m["progress"]
            done = m["done"]

            # Only re-render if progress or done state changed
            if progress != self._prev_progress[i] or done != self._prev_done[i]:
                text = f"{self._mission_text_base[i]} ({progress}/{m['target']})"
                color = (0, 255, 120) if done else (200, 220, 255)
                surf = self.font_line.render(text, True, color)

                # Use mission index as cache key — much faster than string comparison
                cache_key = (i, progress, done)
                self._line_cache[cache_key] = surf
                self._prev_progress[i] = progress
                self._prev_done[i] = done

                # Bounded cache: evict old entries only when cache grows too large
                # Move eviction outside the hot path by checking size less frequently
                if len(self._line_cache) > 15:  # 3 missions × 5 entries each (buffer)
                    # Evict oldest entries for this specific mission only
                    mission_keys = [k for k in self._line_cache.keys() if k[0] == i]
                    if len(mission_keys) > 5:
                        # Sort by progress value (k[1]) to find oldest
                        mission_keys.sort(key=lambda k: k[1])
                        # Keep only the 3 most recent entries for this mission
                        for k in mission_keys[:-3]:
                            del self._line_cache[k]

            # Retrieve from cache — cache_key is already computed above or from previous frame
            cache_key = (i, progress, done)
            surf = self._line_cache.get(cache_key)
            if surf:
                screen.blit(surf, (px + 10, line_y + i * 20))
