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
    LABELS = {
        pygame.K_LEFT: "LEFT", pygame.K_RIGHT: "RIGHT",
        pygame.K_SPACE: "JUMP", pygame.K_f: "FIRE", pygame.K_t: "THROW",
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
        size = max(72, math.ceil(44 / scale))
        gap = max(12, math.ceil(8 / scale))
        left = max(12, math.ceil((safe_left + 8) / scale))
        right = max(12, math.ceil((safe_right + 8) / scale))
        bottom = max(12, math.ceil((safe_bottom + 8) / scale))
        layout = (size, gap, left, right, bottom)
        if layout == self._layout:
            return
        self._layout = layout
        self.bottom_margin = bottom
        self.clear()
        y = SCREEN_HEIGHT - bottom - size
        x = SCREEN_WIDTH - right - size
        self.rects = {
            pygame.K_LEFT: pygame.Rect(left, y, size, size),
            pygame.K_RIGHT: pygame.Rect(left + size + gap, y, size, size),
            pygame.K_f: pygame.Rect(x - size - gap, y, size, size),
            pygame.K_t: pygame.Rect(x, y, size, size),
            pygame.K_SPACE: pygame.Rect(x, y - size - gap, size, size),
        }
        # Font and surfaces are rebuilt only when the displayed control size changes.
        font = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"),
                                max(9, int(size * 0.16)))
        self._surfaces.clear()
        for key, label in self.LABELS.items():
            text = font.render(label, True, (220, 245, 255))
            for pressed in (False, True):
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                surf.fill((16, 8, 40, 190 if pressed else 105))
                pygame.draw.rect(surf, (255, 221, 68, 235) if pressed else (0, 220, 240, 155),
                                 surf.get_rect(), 2, border_radius=10)
                surf.blit(text, text.get_rect(center=(size // 2, size // 2)))
                self._surfaces[(key, pressed)] = surf

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
            if up or not self.rects[key].collidepoint(pos):
                del self.pointers[pointer]
            return True, None
        if down and self.active and self.enabled:
            for key, rect in self.rects.items():
                if rect.collidepoint(pos):
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
                screen.blit(self._surfaces[(key, key in held)], rect)

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
