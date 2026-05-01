# CoinStrike

A fast-paced 2D side-scrolling action platformer built with Python and Pygame. Run through a procedurally generated world, collect coins, fight enemies, complete missions, and take down a final boss.

---

## Overview

CoinStrike blends combat, platforming, and progression into a tight gameplay loop. Survive increasingly difficult conditions while managing movement, weapons, and resources — all before the boss arrives.

---

### Main Menu
<img width="1275" height="718" alt="image" src="https://github.com/user-attachments/assets/cd28918f-56b4-4ce7-8042-a3d85057d02a" />

### In-Game
<img width="1273" height="718" alt="image" src="https://github.com/user-attachments/assets/7834688c-b674-4b87-badf-fabcca34c959" />

---

## Gameplay Loop

1. Run through an infinite, procedurally generated world
2. Collect coins from platforms and ground segments
3. Buy weapons from the in-game shop
4. Eliminate enemies to build combo multipliers
5. Complete three randomized missions
6. Trigger and defeat the final boss

---

## World & Platforming

The world is procedurally generated with dynamic ground segments, breakable platforms, and glitch platforms that shake, disappear, and respawn after 3 seconds. A fixed left boundary keeps the player moving forward. Platform gaps are calculated based on real jump physics (`jump_power=15`, `gravity=0.8`).

---

## Combat & Weapons

| Weapon | Ammo | Key | Notes |
|--------|------|-----|-------|
| Gun | 35 | `F` | Rapid fire |
| Spear | 10 | `T` | Piercing throw, sticks to surfaces |
| Grenade | — | `T` | AOE explosion (90px radius), ballistic arc |

All weapons auto-aim toward the nearest enemy in the player's facing direction. Enemies fire homing projectiles within 600px range.

**Shop prices** (open with `B`):

| Weapon | Cost |
|--------|------|
| Spear | 30 coins |
| Gun | 100 coins |
| Grenade | 150 coins |

Re-purchasing a weapon refills its ammo. Players start each run with **100 coins**.

---

## Health & Respawn

- Max HP: 100 with a color-coded health bar
- Regeneration kicks in ~3 seconds after taking damage
- 90 invincibility frames after being hit
- Falling into pits deals 25 HP damage and triggers a respawn
- A brief shield bubble protects the player for 1 second after respawning
- Game over screen with restart option

---

## Enemies

Enemies patrol assigned platforms and chase the player within 260px. They attack within 600px range and display HP bars and hit-flash effects. Difficulty scales over time — enemies get faster, projectiles speed up, and hazards increase in frequency.

---

## Combo System

- **3+ kills** in a row: bonus coins per kill
- **5+ kills** in a row: speed ×1.4 and damage ×1.5 for 5 seconds
- Combo resets on taking damage or extended inactivity

---

## Missions

Each run generates 3 randomized missions drawn from a pool of 12 objectives, with no duplicate types per run. Possible objectives include coins collected, enemies killed, weapons purchased, and distance traveled. Completing all 3 missions triggers the final boss fight.

---

## Powerups

Powerups spawn roughly once every 5 surfaces and display countdown timers in the HUD.

| Powerup | Duration | Effect |
|---------|----------|--------|
| Magnet | 8s | Attracts coins within 220px |
| Turbo | 6s | Speed ×1.5 |
| Shield | 5s | Temporary invincibility |
| Ammo | Instant | Refills all weapons |

---

## Hazards

Falling rocks spawn from above at increasing frequency — starting every 5 seconds and ramping up to once per second over time. Each rock deals 15 HP and triggers invincibility frames on hit.

---

## HUD

- HP bar with regen indicator
- Combo counter and buff timer
- Coin counter
- Weapon slots with ammo counts and key bindings
- Active powerup timers
- Time elapsed and distance traveled
- Mission tracker panel
- Controls guide bar

---

## Screens & Menus

- **Main Menu** — Start, Options, Exit
- **Options** — Controls guide
- **Boss Intro** — Cutscene before the final encounter
- **Mission Complete** — Shows time survived, coins collected, enemies defeated, distance traveled, weapons purchased, and max combo
- **Game Over** — Restart prompt

---

## Installation

**Run from source:**
```bash
pip install pygame
python main.py
```

**Build a standalone executable:**
```bash
pip install pyinstaller
pyinstaller --onefile main.py
```

**Or download a prebuilt release:**
1. Go to the [Releases](../../releases) section
2. Download the latest `.zip`
3. Extract and run `CoinStrike.exe`

> **Note:** Windows may show a security warning because the app is not digitally signed.

---

## Tech Stack

- **Language:** Python
- **Framework:** Pygame
- **Distribution:** Windows executable via PyInstaller

---

## Roadmap

- Sound effects and background music
- Additional enemy types and boss encounters
- Weapon upgrade system
- Save/load progress
- Web-based version

---

## Version History

- **v1.0.0** — Initial release
