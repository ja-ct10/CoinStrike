import math
import random
from settings import SCREEN_WIDTH, SCREEN_HEIGHT
from platforms import Platform, GroundSegment


class WorldManager:
    """
    Continuously streams platforms and ground segments as the player moves
    forward. Prunes content that is far behind the player to keep memory
    bounded.
    """

    LOOKAHEAD = SCREEN_WIDTH * 2  # generate this far ahead of player
    PRUNE_BEHIND = SCREEN_WIDTH * 3  # remove content this far behind player

    def __init__(self, player, difficulty_scaler=None):
        self.player = player
        self.difficulty_scaler = difficulty_scaler

        # ---- seed initial ground ----
        self.ground_segments = []
        self._rightmost_ground_x = 0
        self._extend_ground(until_x=SCREEN_WIDTH * 4)

        # ---- seed initial platforms ----
        self.platforms = []
        self._rightmost_platform_x = 300
        self._prev_platform_y = SCREEN_HEIGHT - 100 - random.randint(60, 120)
        self._prev_platform_w = random.randint(100, 180)
        self._extend_platforms(until_x=SCREEN_WIDTH * 4)

    # ------------------------------------------------------------------
    # PUBLIC
    # ------------------------------------------------------------------

    def update(
        self, player, enemy_manager=None, coin_manager=None, powerup_manager=None
    ):
        """Call every frame. Extends world ahead of player and prunes behind.
        Returns True if the world was extended (new platforms/ground added)."""
        target_x = player.world_x + self.LOOKAHEAD

        extended = False
        if target_x > self._rightmost_platform_x:
            self._extend_platforms(until_x=target_x + SCREEN_WIDTH)
            extended = True
        if target_x > self._rightmost_ground_x:
            self._extend_ground(until_x=target_x + SCREEN_WIDTH)
            extended = True

        self._prune(player.world_x)

        if extended:
            if enemy_manager is not None:
                enemy_manager.update_surfaces(self.platforms, self.ground_segments)
            if coin_manager is not None:
                coin_manager.update_surfaces(self.platforms, self.ground_segments)
            if powerup_manager is not None:
                powerup_manager.update_surfaces(self.platforms, self.ground_segments)

        return extended

    # ------------------------------------------------------------------
    # PRIVATE — GENERATION
    # ------------------------------------------------------------------

    def _glitch_ratio(self):
        if self.difficulty_scaler is not None:
            return self.difficulty_scaler.glitch_ratio
        return 0.30

    def _max_horizontal_gap(self, delta_y, speed, jump_velocity, gravity):
        """Return safe horizontal reach for a jump landing at delta_y downward."""
        disc = jump_velocity * jump_velocity + 2 * gravity * delta_y
        if disc < 0:
            return -1
        return speed * ((-jump_velocity + math.sqrt(disc)) / gravity)

    def _extend_platforms(self, until_x):
        """Generate platforms from rightmost_platform_x up to until_x.
        Heights and gaps are derived from the player's jump physics so newly
        spawned platforms remain reachable while keeping vertical variety.
        """
        player = self.player
        jump_velocity = player.jump_power
        gravity = player.gravity
        horizontal_speed = max(1, player.speed * player.speed_multiplier)

        max_jump_height = int((jump_velocity * jump_velocity) / (2 * gravity))
        max_air_time = int(-2 * jump_velocity / gravity)
        max_jump_distance = int(horizontal_speed * max_air_time)

        # Reserve a safety margin so the player doesn't need a perfect jump.
        max_v_rise = max(28, int(max_jump_height * 0.40))
        max_v_drop = max(48, int(max_jump_height * 0.60))
        min_h_gap = 40
        max_h_gap = max(min_h_gap + 1, int(max_jump_distance * 0.55))

        ground_top = SCREEN_HEIGHT - 100
        MIN_Y = 180
        MAX_Y = ground_top - 60

        prev_x = self._rightmost_platform_x
        prev_y = self._prev_platform_y
        prev_w = self._prev_platform_w

        while prev_x < until_x:
            if prev_y - MIN_Y < max_v_rise:
                max_up = prev_y - MIN_Y
            else:
                max_up = max_v_rise
            max_down = min(MAX_Y - prev_y, max_v_drop)

            # Try a few candidate heights until we get one with enough reachable gap.
            for attempt in range(8):
                v_shift = random.randint(-max_up, max_down)
                y = max(MIN_Y, min(MAX_Y, prev_y + v_shift))
                delta_y = y - prev_y
                reachable_gap = self._max_horizontal_gap(
                    delta_y, horizontal_speed, jump_velocity, gravity
                )
                if reachable_gap >= min_h_gap:
                    break
            else:
                # Fallback to a safer height if random candidates were too steep.
                y = max(MIN_Y, min(MAX_Y, prev_y + min(max_down, 20)))
                delta_y = y - prev_y
                reachable_gap = max(
                    min_h_gap,
                    self._max_horizontal_gap(
                        delta_y, horizontal_speed, jump_velocity, gravity
                    ),
                )

            safe_h_gap = min(max_h_gap, int(reachable_gap * 0.70))
            h_gap = random.randint(min_h_gap, max(min_h_gap, safe_h_gap))
            x = prev_x + prev_w + h_gap

            if y <= MIN_Y + 40:
                width = random.randint(90, 140)
            elif y >= MAX_Y - 40:
                width = random.randint(120, 220)
            else:
                width = random.randint(100, 180)

            is_glitch = random.random() < self._glitch_ratio()
            self.platforms.append(Platform(x, y, width, glitch=is_glitch))

            prev_x = x
            prev_y = y
            prev_w = width

        self._rightmost_platform_x = prev_x
        self._prev_platform_y = prev_y
        self._prev_platform_w = prev_w

    def _extend_ground(self, until_x):
        """Generate ground segments from rightmost_ground_x up to until_x."""
        x = self._rightmost_ground_x

        # First segment — wide safe spawn zone
        if not self.ground_segments:
            first_w = random.randint(300, 500)
            self.ground_segments.append(GroundSegment(x, first_w))
            x += first_w

        while x < until_x:
            gap = random.randint(80, 220)
            x += gap
            seg_w = random.randint(160, 400)
            self.ground_segments.append(GroundSegment(x, seg_w))
            x += seg_w

        self._rightmost_ground_x = x

    # ------------------------------------------------------------------
    # PRIVATE — PRUNING
    # ------------------------------------------------------------------

    def _prune(self, player_world_x):
        cutoff = player_world_x - self.PRUNE_BEHIND

        # Early-exit: the oldest platform/segment is always at the front of the
        # list (generation is strictly left-to-right), so if the first element
        # is still within range nothing needs pruning.
        if self.platforms and self.platforms[0].rect.right > cutoff:
            plat_prune = False
        else:
            plat_prune = True

        if self.ground_segments and self.ground_segments[0].rect.right > cutoff:
            seg_prune = False
        else:
            seg_prune = True

        if plat_prune:
            self.platforms = [p for p in self.platforms if p.rect.right > cutoff]
        if seg_prune:
            self.ground_segments = [
                s for s in self.ground_segments if s.rect.right > cutoff
            ]
