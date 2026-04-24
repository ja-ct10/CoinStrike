import pygame
import random
from settings import *


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


def generate_ground_segments(world_width=SCREEN_WIDTH * 6):
    """
    Breaks the ground into segments separated by random gaps.
    Returns a list of GroundSegment objects.
    """
    segments = []
    x = 0
    # First solid stretch so the player spawns safely
    first_w = random.randint(300, 500)
    segments.append(GroundSegment(x, first_w))
    x += first_w

    while x < world_width:
        gap = random.randint(80, 220)  # pit width
        x += gap
        seg_w = random.randint(160, 400)  # next ground chunk
        if x + seg_w > world_width:
            seg_w = max(200, world_width - x)
        segments.append(GroundSegment(x, seg_w))
        x += seg_w

    return segments


# ---------------------------------------------------------------------------
# PLATFORM  — normal or glitch (disappears when stepped on)
# ---------------------------------------------------------------------------
GLITCH_COLORS = [(255, 0, 100), (0, 255, 200), (255, 200, 0), (180, 0, 255)]


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

    def _build_surface(self):
        if self.glitch:
            top_color = random.choice(GLITCH_COLORS)
            bottom_color = (20, 8, 40)
        else:
            top_color = (140, 82, 255)
            bottom_color = (57, 43, 86)

        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(bottom_color)
        pygame.draw.rect(self.image, top_color, (0, 0, self.width, 10))

        if self.glitch:
            # Scanline glitch stripes
            for gy in range(0, self.height, 6):
                if random.random() < 0.4:
                    stripe_col = (*random.choice(GLITCH_COLORS)[:3], 80)
                    s = pygame.Surface((self.width, 2), pygame.SRCALPHA)
                    s.fill(stripe_col)
                    self.image.blit(s, (0, gy))

    def notify_standing(self, is_standing):
        """Call each frame with whether the player is on this platform."""
        if not self.glitch or not self.visible:
            return
        if is_standing and self.shake_timer == 0 and self.gone_timer == 0:
            self.shake_timer = 50  # shake for 50 frames then vanish

    def update(self):
        if not self.glitch:
            return

        if self.shake_timer > 0:
            self.shake_timer -= 1
            self.shake_frame += 1
            # Rebuild glitch colours while shaking for flicker effect
            if self.shake_frame % 4 == 0:
                self._build_surface()
            if self.shake_timer == 0:
                self.visible = False
                self.gone_timer = 180  # invisible for 3 seconds then respawn

        elif self.gone_timer > 0:
            self.gone_timer -= 1
            if self.gone_timer == 0:
                self.visible = True
                self.shake_timer = 0
                self.shake_frame = 0
                self._build_surface()

        # Reset rect to base (shake offset applied in draw only)
        self.rect.topleft = (self._base_x, self._base_y)

    def draw(self, screen, camera):
        if not self.visible:
            return

        draw_rect = self.rect.copy()

        # Horizontal shake while counting down
        if self.glitch and self.shake_timer > 0:
            shake_x = random.randint(-3, 3)
            draw_rect.x += shake_x

        screen.blit(self.image, camera.apply(draw_rect))

        # Glitch warning label
        if self.glitch and self.visible and self.shake_timer > 0:
            font = pygame.font.Font("assets/fonts/PressStart2P-Regular.ttf", 6)
            warn = font.render("!", True, (255, 50, 50))
            cam_rect = camera.apply(draw_rect)
            screen.blit(warn, (cam_rect.centerx - 3, cam_rect.top - 10))


def generate_random_platforms(player, num_platforms=14):
    """
    Generate reachable platforms. ~30% are glitch platforms.
    """
    platforms = []

    jump_power = abs(player.jump_power)
    gravity = player.gravity
    speed = player.speed

    max_jump_height = int((jump_power**2) / (2 * gravity))
    air_time = int(2 * jump_power / gravity)
    max_jump_distance = int(speed * air_time)

    max_h_gap = int(max_jump_distance * 0.72)
    max_v_gap = int(max_jump_height * 0.75)

    ground_top = SCREEN_HEIGHT - 100

    prev_x = 300
    prev_y = ground_top - random.randint(80, 160)
    prev_w = random.randint(100, 180)

    for _ in range(num_platforms):
        h_gap = random.randint(60, max_h_gap)
        x = prev_x + prev_w + h_gap

        v_shift = random.randint(-max_v_gap, max_v_gap)
        y = max(80, min(ground_top - 60, prev_y + v_shift))

        width = random.randint(90, 200)
        is_glitch = random.random() < 0.30  # 30% chance

        platform = Platform(x, y, width, glitch=is_glitch)
        platforms.append(platform)

        prev_x = x
        prev_y = y
        prev_w = width

    return platforms
