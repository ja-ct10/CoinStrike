import pygame
import random
from settings import *

PANEL_W = 260
PANEL_H = 100
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
    ("distance", "Travel {target}m", 500),
    ("distance", "Travel {target}m", 1000),
    ("distance", "Travel {target}m", 2000),
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
        self.font_title = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 8)
        self.font_line = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 8)

        self.missions = _pick_missions()

        self.rect = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
        self.all_completed = False

        # Pre-rendered panel background and title — never change
        self._bg_surf = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        self._bg_surf.fill((8, 6, 28, 220))
        self._title_surf = self.font_title.render("MISSIONS", True, (255, 221, 68))

        # Cache for mission line surfaces — keyed by (text_string, done)
        self._line_cache: dict = {}

    def update(self, player, enemy_manager, weapon_manager):
        for m in self.missions:
            if m["done"]:
                continue

            mtype = m["type"]
            if mtype == "coins":
                m["progress"] = getattr(player, "coins_earned", 0)
            elif mtype == "kills":
                m["progress"] = getattr(enemy_manager, "enemies_killed", 0)
            elif mtype == "weapons":
                m["progress"] = getattr(weapon_manager, "weapons_bought", 0)
            elif mtype == "distance":
                # Convert world_x pixels to metres (100 px ≈ 1 m)
                m["progress"] = int(getattr(player, "world_x", 0) // 100)

            if m["progress"] >= m["target"]:
                m["done"] = True

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
            text = f"{m['text']} ({m['progress']}/{m['target']})"
            done = m["done"]
            cache_key = (text, done)
            surf = self._line_cache.get(cache_key)
            if surf is None:
                color = (0, 255, 120) if done else (200, 220, 255)
                surf = self.font_line.render(text, True, color)
                self._line_cache[cache_key] = surf
            screen.blit(surf, (px + 10, line_y + i * 20))
