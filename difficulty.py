class DifficultyScaler:
    """
    Linearly scales game difficulty over SCALE_DURATION frames (~10 minutes).
    All properties are monotonic and clamped to their defined ranges.
    """

    SCALE_DURATION = 36000  # 10 minutes at 60 fps

    def __init__(self):
        self.game_frames = 0

    def update(self, game_frames: int):
        self.game_frames = game_frames

    def _t(self):
        return min(1.0, self.game_frames / self.SCALE_DURATION)

    @staticmethod
    def _lerp(start, end, t):
        return start + (end - start) * t

    # ------------------------------------------------------------------
    @property
    def enemy_spawn_interval(self) -> int:
        """420 → 120 frames (enemies spawn more frequently over time)."""
        return max(120, int(self._lerp(420, 120, self._t())))

    @property
    def projectile_speed_multiplier(self) -> float:
        """1.0 → 2.5 (projectiles get faster over time)."""
        return min(2.5, self._lerp(1.0, 2.5, self._t()))

    @property
    def rock_interval(self) -> int:
        """300 → 60 frames (rocks fall more frequently over time)."""
        return max(60, int(self._lerp(300, 60, self._t())))

    @property
    def glitch_ratio(self) -> float:
        """0.30 → 0.70 (more glitch platforms generated over time)."""
        return min(0.70, self._lerp(0.30, 0.70, self._t()))
