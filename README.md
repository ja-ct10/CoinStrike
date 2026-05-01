🎮 CoinStrike

CoinStrike is a 2D side-scrolling action platformer built with Python and Pygame. The game features a fast-paced, procedurally generated world where players collect coins, fight enemies, complete missions, and ultimately face a final boss.

🏠 Main Menu Screen
<img width="1275" height="718" alt="image" src="https://github.com/user-attachments/assets/cd28918f-56b4-4ce7-8042-a3d85057d02a" />

🎮 In-Game Screen
<img width="1273" height="718" alt="image" src="https://github.com/user-attachments/assets/7834688c-b674-4b87-badf-fabcca34c959" />

📌 Overview
CoinStrike combines combat, platforming, and progression systems into a single gameplay loop. Players must survive increasingly difficult conditions while optimizing movement, combat efficiency, and resource management.

🔁 Core Gameplay Loop
Run continuously through an infinite, procedurally generated world
Collect coins from platforms and ground segments
Purchase weapons from the in-game shop
Eliminate enemies to build combo multipliers
Complete three randomized missions
Trigger and defeat the final boss
Avoid hazards such as falling rocks, enemy projectiles, and pits

🌍 World & Platforming
Procedural world generation with dynamic ground segments
Broken platforms that create pits and traversal challenges
Glitch platforms that shake, disappear, and respawn after 3 seconds
Fixed left boundary to maintain forward progression
Platform gaps calculated based on actual jump physics (jump_power=15, gravity=0.8)

⚔️ Combat & Weapons
Weapons
Gun — rapid fire (35 bullets), activated with F key
Spear — piercing throw (10 ammo), activated with T key
Grenade — area-of-effect (90px radius), activated with T key

Mechanics
Auto-aim toward nearest enemy in facing direction
Spear sticks to surfaces
Grenades follow ballistic arcs
Enemies fire homing projectiles within 600px

Boss
Final boss unlocks after mission completion
Clears all enemies for a focused 1v1 battle

❤️ Health & Respawn System
Max HP: 100 with color-based health bar
Regeneration activates ~3 seconds after damage
Invincibility frames (90 frames) after being hit
Pit falls deal 25 HP damage and trigger respawn
Temporary shield bubble after respawn (1 second)
Game over screen with restart option

👾 Enemies
Patrol assigned platforms and chase within 260px
Attack player within 600px range
Visual effects: hit flashes, particles, HP bars
Difficulty scales over time:
Faster enemies
Faster projectiles
Increased hazards

🔥 Combo System
3+ kills → bonus coins per kill
5+ kills → temporary buffs:
Speed ×1.4
Damage ×1.5
Buff duration: 5 seconds
Combo resets on damage or inactivity

🎯 Missions
3 randomized missions per game
Drawn from a pool of 12 objectives:
Coins collected
Enemies killed
Weapons purchased
Distance traveled
No duplicate mission types per run
Completing all missions triggers boss fight

⚡ Powerups

Spawn rate: ~1 per 5 surfaces

Magnet (8s) — attracts coins within 220px
Turbo (6s) — increases speed (×1.5)
Shield (5s) — temporary invincibility
Ammo (Instant) — refills all weapons

Includes:

Animated floating visuals
HUD timer indicators
🛒 Shop System
Open with B key
Available weapons:
Spear — 30 coins
Gun — 100 coins
Grenade — 150 coins
Re-purchasing refills ammo
Player starts each game with 100 coins

🖥️ HUD (Heads-Up Display)
HP bar with regeneration indicator
Combo counter with buff timer
Coin counter
Weapon slots with ammo and key bindings
Active powerups display
Time elapsed and distance traveled
Mission tracker panel
Controls guide bar
Settings/options menu

📋 Menus & Screens
Main Menu (Start / Options / Exit)
Options menu with controls guide
Boss intro cutscene ("FINAL BOSS")
Mission complete screen with stats:
Time survived
Coins collected
Enemies defeated
Distance traveled
Weapons purchased
Max combo
Game Over screen with restart prompt

☄️ Falling Rocks System
Rocks fall from above at increasing frequency:
Every 5 seconds → up to every 1 second over time
Deal 15 HP damage
Slight random horizontal drift
Trigger invincibility frames on hit

🛠️ Tech Stack
Language: Python
Framework: Pygame
Platform: Desktop (Windows executable supported via PyInstaller)

🚀 Installation & Running
Run from source
pip install pygame
python main.py

Build executable
pip install pyinstaller
pyinstaller --onefile main.py

📦 Download & Play
Go to the Releases section of this repository
Download the latest .zip file
Extract the file
Run CoinStrike.exe

⚠️ Windows may show a security warning because the application is not digitally signed.

🔄 Versioning
v1.0.0 — Initial release
Future updates will include new features, optimizations, and bug fixes

🚧 Future Improvements
Sound effects and background music
Additional enemies and bosses
Upgrade system for weapons
Save/load progress system
Web-based version (optional)

👨‍💻 Developer
Developed as part of a project using Python and Pygame, showcasing:

Procedural generation
Combat systems
Game state management
UI/UX design
