import pygame
import random
from settings import *
from utils import resource_path


# ---------------------------------------------------------------------------
# GROUND SEGMENT  — replaces one continuous ground with broken segments
# ---------------------------------------------------------------------------
class GroundSegment:
    def __init__(self, x, width, y=None):
        self.y = y if y is not None else SCREEN_HEIGHT - 100
        self.height = 146
        self.width = width
        self.image = pygame.Surface((width, self.height))

        top_color = (100, 50, 180)
        bottom_color = (30, 15, 60)
        self.image.fill(bottom_color)
        pygame.draw.rect(self.image, top_color, (0, 0, width, 12))
        # pixel edge highlight
        pygame.draw.rect(self.image, (140, 80, 255), (0, 0, width, 3))

        self.rect = pygame.Rect(x, self.y, width, self.height)

    def draw(self, screen, camera):
        screen.blit(self.image, camera.apply(self.rect))


# ---------------------------------------------------------------------------
# PLATFORM  — normal or glitch (disappears when stepped on)
# ---------------------------------------------------------------------------
GLITCH_COLORS = [(255, 0, 100), (0, 255, 200), (255, 200, 0), (180, 0, 255)]

# Module-level cached fonts — created once, reused every frame
_FONT_GLITCH_WARN = None
_FONT_GLITCH_IDLE = None

# Module-level cached label surfaces — rendered once, reused every frame
_SURF_GLITCH_WARN = None  # "!" label
_SURF_GLITCH_IDLE = None  # "?" label


def _get_glitch_fonts():
    global _FONT_GLITCH_WARN, _FONT_GLITCH_IDLE
    if _FONT_GLITCH_WARN is None:
        _FONT_GLITCH_WARN = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 8)
        _FONT_GLITCH_IDLE = pygame.font.Font(resource_path("assets/fonts/PressStart2P-Regular.ttf"), 6)
    return _FONT_GLITCH_WARN, _FONT_GLITCH_IDLE


def _ensure_glitch_label_surfs():
    """Render and cache the glitch label surfaces. Called at most once."""
    global _SURF_GLITCH_WARN, _SURF_GLITCH_IDLE
    warn_font, idle_font = _get_glitch_fonts()
    if _SURF_GLITCH_WARN is None:
        _SURF_GLITCH_WARN = warn_font.render("!", True, (255, 255, 0))
    if _SURF_GLITCH_IDLE is None:
        _SURF_GLITCH_IDLE = idle_font.render("?", True, (255, 150, 150))


class Platform:
    def __init__(self, x, y, width=120, height=30, glitch=False):
        self.width = width
        self.height = height
        self.glitch = glitch

        # Glitch timer state
        self.standing = False  # player is currently on it
        self.shake_timer = 0  # frames of shaking before disappear
        self.gone_timer = 0  # frames to stay invisible before reset
        self.visible = True
        self.shake_frame = 0

        self._base_x = x
        self._base_y = y

        self._build_surface()
        self.rect = pygame.Rect(x, y, width, height)
        # Pre-allocated draw rect — updated in-place in draw() to avoid per-frame allocation
        self._draw_rect = pygame.Rect(x, y, width, height)

    def _build_surface(self):
        # Normal platforms: single solid purple
        # Glitch platforms: single solid red/warning color (no random stripes)
        if self.glitch:
            # Fixed warning red — clearly different from normal platforms
            top_color = (220, 30, 80)
            bottom_color = (80, 10, 30)
        else:
            top_color = (140, 82, 255)
            bottom_color = (57, 43, 86)

        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(bottom_color)
        pygame.draw.rect(self.image, top_color, (0, 0, self.width, self.height))
        # Top highlight strip
        pygame.draw.rect(
            self.image,
            (
                min(top_color[0] + 60, 255),
                min(top_color[1] + 60, 255),
                min(top_color[2] + 60, 255),
            ),
            (0, 0, self.width, 6),
        )
        # Pre-bake both flicker variants for glitch platforms so draw() never
        # rebuilds the surface — just blits the right pre-baked image.
        if self.glitch:
            self._flicker_a = pygame.Surface((self.width, self.height))
            self._flicker_a.blit(self.image, (0, 0))
            pygame.draw.rect(self._flicker_a, (255, 255, 0), (0, 0, self.width, 6))
            self._flicker_b = pygame.Surface((self.width, self.height))
            self._flicker_b.blit(self.image, (0, 0))
            pygame.draw.rect(self._flicker_b, (255, 0, 100), (0, 0, self.width, 6))

    def notify_standing(self, is_standing):
        """Call each frame with whether the player is on this platform."""
        if not self.glitch or not self.visible:
            return
        if is_standing and self.gone_timer == 0 and self.shake_timer == 0:
            self.shake_timer = 50  # shake for ~0.8s then vanish

    def update(self):
        if not self.glitch:
            return

        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_frame += 1
            # No surface rebuild needed — flicker variants are pre-baked in _build_surface
            if self.shake_timer == 0:
                self.visible = False
                self.gone_timer = 180  # invisible for 3 seconds

        elif self.gone_timer > 0:
            self.gone_timer -= 1
            if self.gone_timer == 0:
                self.visible = True
                self.shake_timer = 0
                self.shake_frame = 0

        self.rect.topleft = (self._base_x, self._base_y)

    def draw(self, screen, camera):
        if not self.visible:
            return

        # Reuse pre-allocated draw rect — update in-place instead of rect.copy()
        dr = self._draw_rect
        dr.x = self._base_x
        dr.y = self._base_y

        if self.glitch and self.shake_timer > 0:
            # Apply shake offset directly on the reused rect
            dr.x += random.randint(-4, 4)
            # Evaluate flicker phase once — used for both surface and border colour
            flicker_a = (self.shake_frame // 3) % 2 == 0
            flicker_surf = self._flicker_a if flicker_a else self._flicker_b
            border_col = (255, 255, 0) if flicker_a else (255, 0, 100)
            cam_rect = camera.apply(dr)
            screen.blit(flicker_surf, cam_rect)
            pygame.draw.rect(screen, border_col, cam_rect, 3)
            # Use module-level cached surface for the "!" label
            if _SURF_GLITCH_WARN is None:
                _ensure_glitch_label_surfs()
            screen.blit(
                _SURF_GLITCH_WARN,
                (
                    cam_rect.centerx - _SURF_GLITCH_WARN.get_width() // 2,
                    cam_rect.top - 14,
                ),
            )
        else:
            cam_rect = camera.apply(dr)
            screen.blit(self.image, cam_rect)
            if self.glitch:
                # Use module-level cached surface for the "?" label
                if _SURF_GLITCH_IDLE is None:
                    _ensure_glitch_label_surfs()
                screen.blit(
                    _SURF_GLITCH_IDLE, (cam_rect.centerx - 3, cam_rect.top - 10)
                )
