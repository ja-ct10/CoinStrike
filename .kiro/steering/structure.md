# Project Structure

## Root Layout

All source files live flat in the project root. There are no subdirectories for source code.

```
main.py          # Entry point — game loop, state machine, HUD, event handling
settings.py      # Global constants (screen size, FPS, sprite dimensions) + Settings icon class
camera.py        # Camera — applies world-to-screen offset via camera.apply(rect)
player.py        # Player class — movement, jumping, sprite selection, coin collection
world.py         # WorldManager — procedural terrain streaming and pruning
platforms.py     # Platform + GroundSegment classes, glitch platform logic, generation helpers
enemy.py         # Enemy, EnemyManager, FinalBoss, projectiles, particles, hit effects
weapon.py        # Bullet, Grenade, Spear, WeaponManager — firing, ammo, HUD
coins.py         # Coin, CoinManager — placement on surfaces, collection
health.py        # Health — HP bar, regen, fall detection, game over screen
mission.py       # Mission — tracks 3 objectives, draws mission panel
shop.py          # Shop — modal UI, WEAPON_DATA, purchase logic
combo.py         # ComboSystem — kill streak tracking, speed/damage buff
difficulty.py    # DifficultyScaler — linear scaling of spawn rate, speed, glitch ratio
rocks.py         # FallingRock, RockManager — falling hazard
menu.py          # Standalone draw_menu() helper (not used by main.py directly)

assets/          # All game assets
  *.png          # Sprites and UI images
  fonts/         # PressStart2P-Regular.ttf
  sounds/        # background-music.mp3
```

## Architecture Patterns

**Manager pattern** — complex subsystems expose a manager class that owns a list of instances and provides `update()` and `draw()` methods called each frame:

- `EnemyManager`, `WeaponManager`, `CoinManager`, `RockManager`, `WorldManager`

**World coordinates vs screen coordinates** — objects store world-space positions (`world_x`, `rect` in world space). `camera.apply(rect)` converts to screen space for drawing. Never draw using raw world rects.

**Game state machine** — `main.py` drives a string-based state machine:
`MENU` → `PLAYING` → `BOSS_INTRO` → `PLAYING` → `GAME_OVER` or `MISSION_COMPLETE`

**Constants in settings.py** — all magic numbers for dimensions, speeds, and layout belong in `settings.py`. Import with `from settings import *`.

**Modal UI** — pause, shop, options, and game-over screens are drawn as overlays inside the main loop. Each returns clickable `pygame.Rect` objects that `main.py` stores and checks on `MOUSEBUTTONDOWN`.

**reset_game()** — full game state is reconstructed by calling `reset_game()` in `main.py`, which returns fresh instances of all managers and the player. Use this pattern for restart/new game.

## Coordinate System

- Origin `(0, 0)` is top-left
- `player.world_x` is the authoritative horizontal position; `player.rect.x` is kept in sync
- Camera offset is negative (world scrolls left as player moves right): `camera.offset_x` decreases over time
