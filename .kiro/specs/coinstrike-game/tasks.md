# Implementation Plan: CoinStrike Game Improvements

## Overview

Implement all missing features and bug fixes for CoinStrike in Python/Pygame. Tasks are ordered so each step builds on the previous: bugs first (unblock mission flow), then new systems (WorldManager is highest priority), then wiring everything together in main.py.

## Tasks

- [x] 1. Fix existing bugs
  - [x] 1.1 Fix "Kill 15 enemies" mission target in `mission.py`
    - Change `"target": 5` to `"target": 15` for the second mission entry
    - _Requirements: 4.1, 4.2_

  - [x] 1.2 Move `weapons_bought` initialisation into `WeaponManager.__init__` in `weapon.py`
    - Add `self.weapons_bought = 0` inside `WeaponManager.__init__`
    - Remove the ad-hoc `if not hasattr(weapon_manager, "weapons_bought")` guard in `main.py`
    - Increment `self.weapons_bought` inside `WeaponManager.grant` instead of in `main.py`
    - _Requirements: 6.5_

  - [x] 1.3 Fix `draw_mission_complete` in `main.py` to return two button rects
    - Add a QUIT button below the RESTART button
    - Return `(restart_rect, quit_rect)` from the function
    - Handle both button clicks in the `MISSION_COMPLETE` draw block (not the keydown handler)
    - QUIT returns to `MENU` state; RESTART resets and goes to `PLAYING`
    - _Requirements: 13.4, 13.5, 13.6_

  - [ ]\* 1.4 Write unit tests for bug fixes
    - `test_mission_target_15`: assert `missions[1]["target"] == 15`
    - `test_weapons_bought_initialized`: assert `WeaponManager().weapons_bought == 0`
    - `test_mission_complete_has_quit_button`: assert `draw_mission_complete` returns a tuple of two `pygame.Rect` objects
    - _Requirements: 4.1, 6.5, 13.4_

- [x] 2. Implement `WorldManager` in `world.py` (continuous world streaming)
  - [x] 2.1 Create `world.py` with the `WorldManager` class
    - Import `Platform`, `generate_random_platforms`, `GroundSegment`, `generate_ground_segments` from `platforms.py`
    - `__init__(self, player, difficulty_scaler)`: seed initial platforms and ground from the existing generators; store `rightmost_platform_x` and `rightmost_ground_x`
    - `LOOKAHEAD = SCREEN_WIDTH * 2` — generate this far ahead of the player's `world_x`
    - `update(self, player, enemy_manager, coin_manager)`: when `player.world_x + LOOKAHEAD > rightmost_platform_x`, generate a new batch of platforms using `generate_random_platforms` logic starting from `rightmost_platform_x`; similarly extend ground segments when `player.world_x + LOOKAHEAD > rightmost_ground_x`
    - Prune platforms and ground segments whose `rect.right < player.world_x - SCREEN_WIDTH * 3` to keep memory bounded
    - Expose `self.platforms` and `self.ground_segments` as plain lists (mutated in-place so existing references stay valid)
    - After extending, call `enemy_manager.update_surfaces(self.platforms, self.ground_segments)` and `coin_manager.update_surfaces(self.platforms, self.ground_segments)` so they always see the live lists
    - _Requirements: 9.6, 10.1_

  - [ ]\* 2.2 Write unit tests for `WorldManager`
    - Test that `platforms` list grows when player moves forward past the lookahead threshold
    - Test that old platforms behind `SCREEN_WIDTH * 3` are pruned
    - Test that `ground_segments` list always contains at least one segment ahead of the player
    - _Requirements: 9.6, 10.1_

- [x] 3. Update `Coin` and `EnemyManager` to accept live surface lists
  - [x] 3.1 Add `update_surfaces` method to `Coin` in `coins.py`
    - Add `update_surfaces(self, platforms, ground_segments)` that replaces `self.platforms` and `self.ground` with the new lists
    - Create a `CoinManager` wrapper (or update `world_coins` list in `main.py`) so `WorldManager` can call a single `coin_manager.update_surfaces(...)` — simplest approach: add a thin `CoinManager` class that holds the list of `Coin` objects and exposes `update_surfaces`
    - _Requirements: 3.1, 3.3_

  - [x] 3.2 Add `update_surfaces` method to `EnemyManager` in `enemy.py`
    - Add `update_surfaces(self, platforms, ground_segments)` that replaces `self.platforms` and `self.ground_segments` with the new lists
    - Ensure newly spawned enemies use the updated lists
    - _Requirements: 8.1, 8.7_

- [x] 4. Implement `ComboSystem` in `combo.py`
  - [x] 4.1 Create `combo.py` with the `ComboSystem` class
    - Constants: `BONUS_THRESHOLD = 3`, `BUFF_THRESHOLD = 5`, `BUFF_DURATION = 300`, `INACTIVITY_TIMEOUT = 300`
    - `on_kill(self, player) -> int`: increment `self.count`; reset `inactivity_timer`; if `count >= BUFF_THRESHOLD` activate buff (`buff_timer = BUFF_DURATION`, set `player.speed_multiplier = 1.4`, `player.damage_multiplier = 1.5`); return bonus coins (`self.count` if `count >= BONUS_THRESHOLD` else `0`)
    - `on_damage_taken(self, player)`: reset `count = 0`, cancel buff (`buff_timer = 0`, restore `player.speed_multiplier = 1.0`, `player.damage_multiplier = 1.0`)
    - `update(self)`: decrement `buff_timer` if > 0; decrement `inactivity_timer` if > 0; if `inactivity_timer` reaches 0 and `count > 0`, reset `count = 0`
    - `is_buff_active(self) -> bool`: return `buff_timer > 0`
    - `draw(self, screen)`: render combo counter at top-center of screen when `count >= 2`; show "COMBO x{count}" with a glow effect; show buff timer bar when buff is active
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [x] 4.2 Add `speed_multiplier` and `damage_multiplier` to `Player` in `player.py`
    - Add `self.speed_multiplier = 1.0` and `self.damage_multiplier = 1.0` in `Player.__init__`
    - In `Player.update`, replace `self.speed` with `self.speed * self.speed_multiplier` for horizontal movement
    - _Requirements: 5.3_

  - [ ]\* 4.3 Write property tests for `ComboSystem`
    - **Property 6: Combo counter increments on each kill without damage**
    - **Validates: Requirements 5.1**
    - **Property 7: Combo bonus coins scale with combo count**
    - **Validates: Requirements 5.2**
    - **Property 8: Combo buff activates at threshold and deactivates on damage**
    - **Validates: Requirements 5.3, 5.4**
    - **Property 9: Combo resets after inactivity timeout**
    - **Validates: Requirements 5.5**

- [ ] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement `EnemyProjectile` in `enemy.py`
  - [x] 6.1 Add `EnemyProjectile` class to `enemy.py`
    - `BASE_SPEED = 5`, `DAMAGE = 10`, `RADIUS = 6`
    - `__init__(self, x, y, target_x, target_y, speed_multiplier=1.0)`: compute normalised direction vector toward target; store `dx`, `dy` scaled by `BASE_SPEED * speed_multiplier`
    - `update(self, ground_segments, platforms)`: move by `dx`, `dy`; set `alive = False` on ground/platform collision or when off-screen
    - `draw(self, screen, camera)`: draw a small glowing red circle
    - `alive` property
    - _Requirements: 8.4 (enemy attacks player)_

  - [x] 6.2 Add projectile firing to `Enemy` class
    - Add `self.shoot_timer = 0`, `SHOOT_RANGE = 400`, `SHOOT_COOLDOWN = 180`, `self.projectiles: list = []` in `Enemy.__init__`
    - In `Enemy.update`, when in chase state and distance to player < `SHOOT_RANGE` and `shoot_timer == 0`: append a new `EnemyProjectile` aimed at player center; reset `shoot_timer = SHOOT_COOLDOWN`
    - Decrement `shoot_timer` each frame
    - Update and prune `self.projectiles` in `Enemy.update`
    - Draw projectiles in `Enemy.draw`
    - _Requirements: 8.4_

  - [x] 6.3 Add `_check_projectile_hits` to `EnemyManager`
    - Iterate all enemies' `projectiles` lists; for each alive projectile that collides with `player.rect`, call `health.take_damage(projectile.DAMAGE)` and set `projectile.alive = False`
    - Call this method from `EnemyManager.update`
    - Pass `difficulty_scaler.projectile_speed_multiplier` when constructing new projectiles (add `difficulty_scaler` param to `EnemyManager.update`)
    - _Requirements: 8.4, 12.2_

  - [ ]\* 6.4 Write property tests for projectile damage
    - **Property 2: Damage decreases HP by the exact damage amount**
    - **Validates: Requirements 2.2**
    - **Property 3: Invincibility prevents all damage**
    - **Validates: Requirements 2.8**

- [x] 7. Implement `FallingRock` and `RockManager` in `rocks.py`
  - [x] 7.1 Create `rocks.py` with `FallingRock` and `RockManager`
    - `FallingRock`: `GRAVITY = 0.6`, `BASE_DAMAGE = 15`, `RADIUS = 14`; `__init__(self, x, y)`; `update(self, ground_segments, platforms)` applies gravity, sets `alive = False` on surface collision; `draw(self, screen, camera)` draws a grey/brown circle with a crack detail; `alive` property
    - `RockManager`: `BASE_INTERVAL = 300`, `MIN_INTERVAL = 60`; `__init__(self)`; `update(self, camera, ground_segments, platforms, player, health, difficulty_scaler)` — spawn a rock at random x within camera view + 200 px margin at y = -60 when `spawn_timer` reaches `difficulty_scaler.rock_interval`; check rock/player collision and call `health.take_damage(rock.BASE_DAMAGE)`; prune dead rocks; `draw(self, screen, camera)`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ]\* 7.2 Write property tests for `FallingRock`
    - **Property 1: Gravity is applied uniformly**
    - **Validates: Requirements 1.3, 11.3**
    - **Property 2: Damage decreases HP by the exact damage amount (rock variant)**
    - **Validates: Requirements 11.2**

- [x] 8. Implement `DifficultyScaler` in `difficulty.py`
  - [x] 8.1 Create `difficulty.py` with the `DifficultyScaler` class
    - `SCALE_DURATION = 36000` (10 minutes at 60 fps)
    - `_lerp(self, start, end, t)`: `return start + (end - start) * min(1.0, t)`
    - `update(self, game_frames: int)`: store `self.game_frames = game_frames`
    - `enemy_spawn_interval` property: lerp from 420 → 120
    - `projectile_speed_multiplier` property: lerp from 1.0 → 2.5
    - `rock_interval` property: lerp from 300 → 60
    - `glitch_ratio` property: lerp from 0.30 → 0.70
    - All outputs clamped to their defined min/max
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]\* 8.2 Write property tests for `DifficultyScaler`
    - **Property 15: Difficulty values scale monotonically with time**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4**

- [x] 9. Implement `FinalBoss` in `enemy.py`
  - [x] 9.1 Add `FinalBoss` class to `enemy.py` extending `Enemy`
    - `MAX_HP = 300`, `ATTACK_DAMAGE = 30`, `SHOOT_COOLDOWN = 60`, `MULTI_SHOT_COUNT = 3`, `SPEED_MULTIPLIER = 1.5`
    - Override `__init__(self, x, y)`: call `super().__init__(x, y)`; set `self.hp = self.MAX_HP`; set patrol/chase speeds scaled by `SPEED_MULTIPLIER`
    - Add `_fire_spread(self, player)`: fire `MULTI_SHOT_COUNT` projectiles in a spread pattern (e.g., ±15° around the direct aim angle)
    - Override `update` to use `_fire_spread` instead of single-shot firing and use the faster `SHOOT_COOLDOWN`
    - Override `draw` to render a larger, visually distinct boss sprite (bigger body, crown/spikes, different colour scheme)
    - Add `boss_spawned = False` flag to `EnemyManager`; expose `self.boss = None`
    - Add `spawn_boss(self, player)` method to `EnemyManager` that creates a `FinalBoss` ahead of the player and sets `boss_spawned = True`
    - Update `EnemyManager.update` to also update and draw `self.boss` if it exists; when `boss.hp <= 0` set `boss.alive = False` and signal completion via a `self.boss_defeated` flag
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ]\* 9.2 Write unit tests for `FinalBoss`
    - `test_boss_hp_greater_than_enemy`: assert `FinalBoss.MAX_HP > Enemy.MAX_HP`
    - `test_boss_spawns_on_mission_complete`: assert `EnemyManager.boss` is not None after `spawn_boss` is called
    - _Requirements: 13.1, 13.2_

- [ ] 10. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Add weapon-holding sprites to `Player` in `player.py`
  - [x] 11.1 Load holding sprites in `Player.__init__`
    - Load and scale all 8 holding sprites (idle + run × left + right × gun/spear/grenade) using `try/except` with a colored-rect fallback if a file is missing
    - Store as `self.hold_idle_right`, `self.hold_idle_left`, `self.hold_run_right`, `self.hold_run_left` — each a dict keyed by weapon name (`"gun"`, `"spear"`, `"grenade"`)
    - _Requirements: (player visual polish)_

  - [x] 11.2 Update `Player.update` sprite selection to use holding sprites
    - Determine `held_weapon` from `weapon_manager` if passed (or store it on player); select the appropriate holding sprite when a weapon is owned
    - Fall back to base idle/run sprites when no weapon is held
    - Remove the `draw_held_weapon` call from `weapon.py` / `player.draw` since the weapon is now baked into the sprite
    - _Requirements: (player visual polish)_

- [x] 12. Wire all new systems together in `main.py`
  - [x] 12.1 Instantiate `DifficultyScaler`, `WorldManager`, `RockManager`, and `ComboSystem` in `reset_game`
    - `difficulty_scaler = DifficultyScaler()`
    - `world_manager = WorldManager(player, difficulty_scaler)` — replace the direct `generate_random_platforms` / `generate_ground_segments` calls; use `world_manager.platforms` and `world_manager.ground_segments` as the live lists
    - `rock_manager = RockManager()`
    - `combo_system = ComboSystem()`
    - Add `game_frames = 0` counter
    - Return all new objects from `reset_game` and unpack them at call sites
    - _Requirements: 9.6, 11.1, 12.1–12.4, 5.1–5.5_

  - [x] 12.2 Update the main game loop to call all new systems each frame
    - Increment `game_frames` each frame when `game_state == PLAYING` and no modal is open
    - Call `difficulty_scaler.update(game_frames)`
    - Call `world_manager.update(player, enemy_manager, coin_manager)` — pass the `CoinManager` wrapper
    - Call `rock_manager.update(camera, ground_segments, platforms, player, health, difficulty_scaler)`
    - Call `combo_system.update()`
    - Pass `difficulty_scaler` to `enemy_manager.update(player, health, weapon_manager, difficulty_scaler)`
    - After `enemy_manager.update`, collect kills via `just_died` and call `combo_system.on_kill(player)` for each; add returned bonus coins to `player.coins_collected` and `player.coins_earned`
    - Call `combo_system.on_damage_taken(player)` when `health.take_damage` is triggered (hook via a flag or subclass — simplest: check `health.hp` decreased since last frame)
    - _Requirements: 5.1–5.5, 9.6, 11.1–11.4, 12.1–12.4_

  - [x] 12.3 Integrate `FinalBoss` spawn and `MISSION_COMPLETE` transition
    - When `mission.all_completed` becomes `True` and `not enemy_manager.boss_spawned`, call `enemy_manager.spawn_boss(player)`
    - Each frame, check `enemy_manager.boss_defeated`; when `True`, set `game_state = MISSION_COMPLETE`
    - Update `draw_mission_complete` call to unpack `(restart_rect, quit_rect)` and handle both clicks
    - _Requirements: 13.1, 13.4, 13.5, 13.6_

  - [x] 12.4 Draw all new HUD elements
    - Call `combo_system.draw(screen)` after the player draw
    - Call `rock_manager.draw(screen, camera)` in the world draw pass
    - Call `enemy_manager.draw` to include boss drawing (already handled inside `EnemyManager.draw`)
    - _Requirements: 5.1, 11.1_

  - [ ]\* 12.5 Write integration tests for the wired-up game loop
    - Test that `world_manager.platforms` grows after simulating player movement past the lookahead threshold
    - Test that `combo_system.count` increments when `enemy_manager.enemies_killed` increases
    - Test that `game_state` transitions to `MISSION_COMPLETE` when `enemy_manager.boss_defeated` is True
    - _Requirements: 9.6, 5.1, 13.4_

- [ ] 13. Write remaining property-based tests using Hypothesis
  - [ ]\* 13.1 Write property tests for `Health` (gravity, damage, invincibility, pit fall)
    - **Property 1: Gravity is applied uniformly** — `@given(vel_y=st.floats(...))` verify `vel_y + 0.8` after one player tick
    - **Validates: Requirements 1.3**
    - **Property 2: Damage decreases HP by exact amount** — `@given(hp, damage)` verify `new_hp == hp - damage`
    - **Validates: Requirements 2.2**
    - **Property 3: Invincibility prevents all damage** — `@given(invincible_timer, damage)` verify HP unchanged
    - **Validates: Requirements 2.8**
    - **Property 4: Pit fall costs 25 HP and triggers respawn** — `@given(hp=st.integers(min_value=26, max_value=100))` verify `hp - 25` and position reset
    - **Validates: Requirements 2.4, 10.3, 10.4**

  - [ ]\* 13.2 Write property tests for `Coin` and `Shop`
    - **Property 5: Coin collection increments counter by 1** — `@given(initial_coins)` verify `coins + 1`
    - **Validates: Requirements 3.2**
    - **Property 10: Shop purchase deducts exact cost** — `@given(coins, weapon)` verify `coins - price`
    - **Validates: Requirements 6.3**
    - **Property 11: Shop rejects insufficient coins** — `@given(weapon, coins < price)` verify coins unchanged
    - **Validates: Requirements 6.4**

  - [ ]\* 13.3 Write property tests for `Enemy` and weapons
    - **Property 12: Weapon damage values are exact** — bullet=3, spear=5, grenade=5
    - **Validates: Requirements 7.3, 7.4, 7.5**
    - **Property 13: Enemy AI state determined by distance** — `@given(distance)` verify chase/patrol state
    - **Validates: Requirements 8.2, 8.3**
    - **Property 14: Enemy contact damage is 20 HP** — `@given(hp)` verify `hp - 20`
    - **Validates: Requirements 8.4**

- [ ] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- `WorldManager` (task 2) is the highest-priority task — it fixes the core bug where platforms and coins stop generating after a few seconds
- Each task references specific requirements for traceability
- Property tests use [Hypothesis](https://hypothesis.readthedocs.io/) — install with `pip install hypothesis`
- The `CoinManager` wrapper in task 3.1 is the simplest way to give `WorldManager` a single `update_surfaces` call target
- `damage_multiplier` from `ComboSystem` should be applied in `EnemyManager._check_bullets/spears/grenades` by multiplying damage by `combo_system.damage_multiplier` when `combo_system.is_buff_active()` is True
