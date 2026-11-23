"""Small virtual controller; gameplay continues to consume the usual keys."""

import json
import math

import pygame

from settings import IS_WEB, SCREEN_WIDTH, SCREEN_HEIGHT
from utils import resource_path


class CombinedKeys:
    def __init__(self, keyboard, virtual):
        self.keyboard = keyboard
        self.virtual = virtual

    def __getitem__(self, key):
        return bool(self.keyboard[key] or key in self.virtual)


def pointer_click(event):
    """Return one logical UI click, ignoring SDL's duplicate touch mouse event."""
    if event.type == pygame.FINGERDOWN:
        return (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
    if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
            and not getattr(event, "touch", False)):
        return event.pos
    return None


class TouchControls:
    ICONS = {
        pygame.K_LEFT: "left", pygame.K_RIGHT: "right",
        pygame.K_SPACE: "jump", pygame.K_f: "gun",
    }

    def __init__(self):
        self.enabled = False
        self.manual = False
        self.active = False
        self.pointers = {}
        self._jump_pressed = False
        self._browser_snapshot = None
        self._browser_reset = 0
        self._layout = None
        self._weapons = (False, None)
        self.rects = {}
        self._surfaces = {}
        self._toggle_surfaces = {}
        self.resize(SCREEN_WIDTH, SCREEN_HEIGHT)

    def clear(self):
        self.pointers.clear()
        self._jump_pressed = False

    def set_active(self, active):
        if self.active != active:
            self.clear()
            self.active = active

    def toggle(self):
        self.manual = True
        self.enabled = not self.enabled
        self.clear()

    def sync_browser(self):
        if not IS_WEB:
            return
        # One cached string crosses the browser bridge; JSON/layout work only on change.
        import platform
        snapshot = str(platform.window.coinstrikeTouch.snapshot)
        if snapshot == self._browser_snapshot:
            return
        self._browser_snapshot = snapshot
        data = json.loads(snapshot)
        if not self.manual:
            self.enabled = data["touch"]
        if self._browser_reset != data["reset"]:
            self.clear()
            self._browser_reset = data["reset"]
        self.resize(data["width"], data["height"], data["left"],
                    data["right"], data["bottom"])

    def resize(self, width, height, safe_left=0, safe_right=0, safe_bottom=0):
        scale = max(0.1, min(width / SCREEN_WIDTH, height / SCREEN_HEIGHT))
        diameter = max(36, min(48, width * 0.06))
        size = math.ceil(max(44, diameter) / scale)
        visual_size = round(diameter / scale)
        gap = math.ceil(8 / scale)
        left = math.ceil((safe_left + 8) / scale)
        right = math.ceil((safe_right + 8) / scale)
        bottom = math.ceil((safe_bottom + 8) / scale)
        layout = (size, visual_size, gap, left, right, bottom, scale)
        if layout == self._layout:
            return
        self._layout = layout
        self.bottom_margin = bottom
        self.clear()
        self._surfaces.clear()
        self._place_buttons()

    def sync_weapons(self, manager):
        weapons = (manager.can_use("gun"), manager.get_throw_weapon())
        if weapons != self._weapons:
            self._weapons = weapons
            self._place_buttons()

    def _place_buttons(self):
        size, _, gap, left, right, bottom, _ = self._layout
        y = SCREEN_HEIGHT - bottom - size
        rects = {
            pygame.K_LEFT: pygame.Rect(left, y, size, size),
            pygame.K_RIGHT: pygame.Rect(left + size + gap, y, size, size),
        }
        attacks = ([pygame.K_f] if self._weapons[0] else [])
        attacks += ([pygame.K_t] if self._weapons[1] else [])
        actions = attacks + [pygame.K_SPACE]
        start_x = SCREEN_WIDTH - right - len(actions) * size - (len(actions) - 1) * gap
        for i, key in enumerate(actions):
            rects[key] = pygame.Rect(start_x + i * (size + gap), y, size, size)
        # Reflow never transfers a finger to a different action. Unmoved holds survive.
        for pointer, key in tuple(self.pointers.items()):
            if key not in rects or self.rects.get(key) != rects[key]:
                del self.pointers[pointer]
        self.rects = rects
        self.hud_obstacles = tuple(rect.inflate(gap * 2, gap * 2) for rect in rects.values())

    def _inside(self, key, pos):
        rect = self.rects[key]
        return ((pos[0] - rect.centerx) ** 2 + (pos[1] - rect.centery) ** 2
                <= (rect.width / 2) ** 2)

    def _button_surface(self, key, pressed):
        icon = self._weapons[1] if key == pygame.K_t else self.ICONS[key]
        cache_key = (icon, pressed)
        if cache_key not in self._surfaces:
            size, visual_size, *_, scale = self._layout
            # Render at 2x once, then downsample for smooth, transparent circular edges.
            surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            center = (size, size)
            pygame.draw.circle(surf, (12, 6, 28, 80 if pressed else 48), center, visual_size)
            border = (160, 100, 240, 210) if pressed else (145, 210, 235, 140)
            pygame.draw.circle(surf, border, center, visual_size, max(1, round(2 / scale)))
            self._draw_icon(surf, icon, center, visual_size * 1.12, scale)
            self._surfaces[cache_key] = pygame.transform.smoothscale(surf, (size, size))
        return self._surfaces[cache_key]

    @staticmethod
    def _draw_icon(surf, icon, center, extent, scale):
        color = (235, 242, 255, 220)
        stroke = max(2, round(4 / scale))

        def point(x, y):
            return (round(center[0] + (x / 100 - 0.5) * extent),
                    round(center[1] + (y / 100 - 0.5) * extent))

        def polygon(points, width=0):
            pygame.draw.polygon(surf, color, [point(x, y) for x, y in points], width)

        if icon == "left":
            polygon([(80, 8), (12, 50), (80, 92)])
        elif icon == "right":
            polygon([(20, 8), (88, 50), (20, 92)])
        elif icon == "jump":
            polygon([(50, 8), (8, 50), (34, 50), (34, 92), (66, 92), (66, 50), (92, 50)])
        elif icon == "gun":
            polygon([(8, 24), (92, 24), (92, 44), (60, 44), (48, 86),
                     (27, 86), (37, 47), (8, 47)], stroke)
            pygame.draw.lines(surf, color, False,
                              [point(60, 47), point(72, 47), point(65, 63), point(55, 63)], stroke)
        elif icon == "spear":
            pygame.draw.line(surf, color, point(15, 90), point(76, 25), stroke)
            polygon([(90, 8), (80, 42), (58, 22)])
            pygame.draw.line(surf, color, point(18, 75), point(32, 89), stroke)
        elif icon == "grenade":
            a, b = point(23, 32), point(77, 92)
            pygame.draw.ellipse(surf, color, pygame.Rect(a, (b[0] - a[0], b[1] - a[1])), stroke)
            polygon([(37, 21), (62, 21), (62, 34), (37, 34)], stroke)
            pygame.draw.circle(surf, color, point(75, 18), max(3, round(extent * 0.1)), stroke)
            for y in (50, 70):
                pygame.draw.line(surf, color, point(28, y), point(72, y), max(1, stroke // 2))

    def handle_event(self, event):
        """Return (consumed, initial key), keeping every pointer independent."""
        if event.type in (pygame.WINDOWFOCUSLOST, pygame.WINDOWMINIMIZED,
                          pygame.WINDOWRESIZED, pygame.VIDEORESIZE):
            self.clear()
        if event.type == pygame.FINGERDOWN and not self.manual:
            self.enabled = True
        if event.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            pointer = (event.touch_id, event.finger_id)
            pos = (int(event.x * SCREEN_WIDTH), int(event.y * SCREEN_HEIGHT))
            down = event.type == pygame.FINGERDOWN
            up = event.type == pygame.FINGERUP
        elif event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if getattr(event, "touch", False):
                return False, None
            if event.type != pygame.MOUSEMOTION and event.button != 1:
                return False, None
            pointer, pos = "mouse", event.pos
            down = event.type == pygame.MOUSEBUTTONDOWN
            up = event.type == pygame.MOUSEBUTTONUP
        else:
            return False, None

        if pointer in self.pointers:
            key = self.pointers[pointer]
            if up or not self._inside(key, pos):
                del self.pointers[pointer]
            return True, None
        if down and self.active and self.enabled:
            for key, rect in self.rects.items():
                if self._inside(key, pos):
                    self.pointers[pointer] = key
                    if key == pygame.K_SPACE:
                        self._jump_pressed = True
                    return True, key
        return False, None

    def keys(self, keyboard):
        virtual = set(self.pointers.values())
        if self._jump_pressed:
            virtual.add(pygame.K_SPACE)
        self._jump_pressed = False
        return CombinedKeys(keyboard, virtual)

    def draw(self, screen):
        if self.active and self.enabled:
            held = self.pointers.values()
            for key, rect in self.rects.items():
                screen.blit(self._button_surface(key, key in held), rect)

    def draw_toggle(self, screen, rect):
        # Options has room for one small switch below its existing guide.
        surf = self._toggle_surfaces.get(self.enabled)
        if surf is None:
            font = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 9)
            surf = font.render("ON-SCREEN CONTROLS: " + ("ON" if self.enabled else "OFF"),
                               True, (255, 221, 68))
            self._toggle_surfaces[self.enabled] = surf
        pygame.draw.rect(screen, (26, 8, 48), rect, border_radius=4)
        pygame.draw.rect(screen, (0, 200, 220), rect, 1, border_radius=4)
        screen.blit(surf, surf.get_rect(center=rect.center))
