# CoinStrike — Product Overview

CoinStrike is a 2D side-scrolling action platformer built with Python and Pygame. The player runs through a procedurally generated world, collects coins, buys weapons from a shop, and fights enemies to complete missions before facing a final boss.

## Core Gameplay Loop

- Run right through an infinite, procedurally generated world
- Collect coins from platforms and ground segments
- Buy weapons (gun, spear, grenade) from the in-game shop
- Kill enemies to build combo multipliers and earn bonus coins
- Complete three randomised missions to trigger the final boss
- Survive falling rocks, enemy projectiles, and pit falls

## Key Features

### World & Platforming

- Procedural world generation with broken ground segments (gaps between platforms create pits)
- Glitch platforms (red/warning colour) that shake and disappear when stood on, then respawn after 3 seconds
- Hard left boundary — player cannot move behind world origin
- Platform reachability guaranteed: gap sizes are derived from actual jump physics (jump_power=15, gravity=0.8)

### Combat & Weapons

- Three weapons with distinct mechanics:
  - **Gun** — rapid fire (35 bullets), fires on F key
  - **Spear** — piercing throw (10 ammo), fires on T key; sticks into surfaces
  - **Grenade** — AoE explosion radius 90px (15 ammo), fires on T key; ballistic arc targeting
- Weapons auto-aim at the nearest enemy in the player's facing direction when thrown
- Enemy projectiles: enemies fire homing shots at the player within 600px range
- Final boss encounter after all missions are complete — clears all regular enemies for a 1-on-1 fight

### Health & Respawn

- HP-based health (100 HP max) with colour-coded bar (green → yellow → red)
- HP regeneration kicks in ~3 seconds after last hit
- Invincibility frames (90 frames) after taking damage — bar flickers to indicate
- Falling into a pit costs 25 HP and respawns the player at the last safe ground position
- Post-respawn shield bubble (1 second of visible invincibility)
- Game over screen with YES/NO restart prompt

### Enemies

- Enemies patrol their home platform/ground segment and chase the player within 260px
- Enemies fire projectiles at the player when within 600px horizontal range
- Death particles and hit flash effects on enemy kill
- HP bar shown above enemy when chasing or recently hit
- Difficulty scaling over 10 minutes: faster enemy spawns, faster projectiles, more glitch platforms, more falling rocks

### Combo System

- 3+ kills in a row → bonus coins per kill equal to the current combo count
- 5+ kills in a row → speed multiplier (×1.4) and damage multiplier (×1.5) buff for 5 seconds
- Combo resets on taking damage or 5 seconds of inactivity
- Buff timer bar displayed below the combo counter

### Missions

- 3 randomised missions per game drawn from a pool of 12 (coins, kills, weapon purchases, distance)
- Mission types are always distinct (no two missions of the same type in one game)
- Completing all 3 missions triggers the boss intro cutscene

### Powerups

- Collectible powerups spawn on platforms and ground segments (1 per every 5 surfaces)
- **Magnet** (8s) — auto-collects all coins within 220px
- **Turbo** (6s) — doubles movement speed (×1.5 multiplier)
- **Shield** (5s) — grants invincibility frames
- **Ammo** (instant) — refills all owned weapon ammo to full
- Powerups bob up and down with a glowing icon and type label
- Active powerup timers shown as HUD pill badges

### Shop

- In-game shop modal (B key or click shop icon) with three weapon cards
- Weapons: Spear (30 coins), Gun (100 coins), Grenade (150 coins)
- Buying a weapon you already own refills its ammo to full
- Player starts each game with 100 coins

### HUD

- HP bar with regen indicator ("HP +") and numeric value
- Combo counter with buff bar
- Coin counter (icon + number)
- Weapon ammo slots (bottom-left) showing icon, name, ammo count, and key hint
- Active powerup timer badges
- Elapsed time and distance travelled (below HP bar)
- Mission panel (top-right)
- Key guide bar at the bottom of the screen
- Settings icon (top-right) opens options/controls modal

### Menus & Screens

- Main menu with START / OPTIONS / EXIT (keyboard navigable)
- Options modal with full key bindings guide
- Boss intro cutscene overlay ("FINAL BOSS" with pulsing animation)
- Mission complete screen with per-game stats (time, coins, kills, distance, weapons bought, max combo)
- Game over screen with restart prompt

### Falling Rocks

- Rocks fall from above at increasing frequency (every 5s → every 1s over 10 minutes)
- Rocks deal 15 HP damage on contact and grant invincibility frames
- Slight random horizontal drift per rock
