# Requirements Document

## Introduction

CoinStrike is a 2D side-scrolling platformer game built with Python and Pygame, inspired by Super Mario Bros. The player navigates a continuously generated world, collecting coins, defeating enemies with purchasable weapons, and completing three missions. The game escalates in difficulty over time and culminates in a Final Boss encounter once all missions are complete. A combo kill system rewards skilled play with bonus coins and temporary buffs. The game includes a HUD, shop, settings/pause menu, and game-over/mission-complete screens.

---

## Glossary

- **Game**: The CoinStrike Pygame application.
- **Player**: The user-controlled character navigating the world.
- **World**: The continuously generated side-scrolling environment.
- **Platform**: An elevated surface the Player can stand on.
- **Glitch_Platform**: A Platform that flickers and temporarily disappears when the Player stands on it.
- **Ground**: The base-level terrain containing randomly placed gaps (pits).
- **Pit**: A gap in the Ground that causes the Player to fall.
- **Coin**: A collectible item scattered across Platforms and Ground segments.
- **Enemy**: An AI-controlled hostile character that attacks the Player.
- **Final_Boss**: A special high-HP Enemy that appears after all Missions are completed.
- **Projectile**: An attack fired by an Enemy toward the Player.
- **Weapon**: A purchasable item (Spear, Gun, or Grenade) used to defeat Enemies.
- **Shop**: The in-game store where the Player purchases Weapons using Coins.
- **Mission**: One of three objectives the Player must complete to trigger the Final Boss.
- **Mission_Banner**: The HUD panel displaying the three Missions and their progress.
- **Combo**: A streak of consecutive Enemy kills without the Player taking damage.
- **Combo_Buff**: A temporary stat boost granted for maintaining a Combo.
- **Health_Bar**: The HUD element displaying the Player's current HP.
- **HUD**: The heads-up display showing HP, Coin count, Mission_Banner, Shop icon, and Settings icon.
- **Settings_Menu**: The pause overlay accessible via the Settings icon or Escape key.
- **Game_Over_Screen**: The overlay shown when the Player's HP reaches 0.
- **Mission_Complete_Screen**: The overlay shown after the Final Boss is defeated.
- **Falling_Rock**: An environmental hazard that drops from above at random intervals.
- **Respawn_Point**: The last safe Ground position recorded before the Player fell.

---

## Requirements

### Requirement 1: Player Movement

**User Story:** As a player, I want to walk, run, and jump across the world, so that I can navigate platforms and avoid hazards.

#### Acceptance Criteria

1. WHEN the Player presses the left or right movement key, THE Player SHALL move horizontally at a base speed of 5 pixels per frame.
2. WHEN the Player presses the jump key while on the Ground or a Platform, THE Player SHALL launch upward with a vertical velocity of -12 pixels per frame.
3. WHILE the Player is airborne, THE Player SHALL accelerate downward at 0.8 pixels per frame squared (gravity).
4. WHEN the Player lands on a Platform or Ground segment, THE Player SHALL stop vertical movement and register as on-ground.
5. WHEN the Player moves horizontally, THE Player SHALL display the running sprite facing the direction of movement.
6. WHILE the Player is stationary, THE Player SHALL display the idle sprite facing the last movement direction.

---

### Requirement 2: Player Health and Respawn

**User Story:** As a player, I want a health bar and the ability to respawn after falling, so that I can recover from mistakes and continue playing.

#### Acceptance Criteria

1. THE Player SHALL have a maximum HP of 100.
2. WHEN the Player takes damage, THE Health_Bar SHALL decrease by the damage amount.
3. WHILE the Player has not taken damage for 180 frames (3 seconds), THE Player SHALL regenerate HP at a rate of 1 HP per frame until maximum HP is reached.
4. WHEN the Player falls into a Pit, THE Player SHALL lose 25 HP and respawn at the Respawn_Point if HP remains above 0.
5. WHEN the Player's HP reaches 0, THE Game SHALL display the Game_Over_Screen with the message "GAME OVER" and a "Try Again?" prompt with YES and NO options.
6. WHEN the Player selects YES on the Game_Over_Screen, THE Game SHALL reset all state and restart from the beginning.
7. WHEN the Player selects NO on the Game_Over_Screen, THE Game SHALL return to the main menu.
8. WHILE the Player is in an invincibility period of 90 frames after taking damage, THE Player SHALL not receive further damage.

---

### Requirement 3: Coin System

**User Story:** As a player, I want to collect coins scattered across the world, so that I can purchase weapons from the Shop.

#### Acceptance Criteria

1. THE Game SHALL scatter Coins across Platforms and Ground segments throughout the World.
2. WHEN the Player's rect overlaps a Coin's rect, THE Player SHALL collect the Coin and increment the coin counter by 1.
3. WHEN a Coin is collected, THE Coin SHALL reposition to a new random Platform or Ground segment.
4. THE HUD SHALL display the Player's current Coin count at all times during gameplay.
5. THE Player's Coin count SHALL persist as currency available for Shop purchases.

---

### Requirement 4: Mission System

**User Story:** As a player, I want to track three objectives on screen, so that I know what I need to accomplish to progress to the Final Boss.

#### Acceptance Criteria

1. THE Mission_Banner SHALL display three Missions: "Collect 100 coins", "Kill 15 enemies", and "Buy 2 weapons".
2. WHEN a Mission's progress value reaches its target, THE Mission_Banner SHALL highlight that Mission in green.
3. THE Mission_Banner SHALL display the current progress and target for each Mission (e.g., "12/15").
4. WHEN all three Missions are completed, THE Game SHALL transition to the Final Boss encounter.
5. THE Mission_Banner SHALL remain visible on the HUD at all times during gameplay.

---

### Requirement 5: Combo Kill System

**User Story:** As a player, I want to be rewarded for killing enemies consecutively without taking damage, so that skilled play is incentivised.

#### Acceptance Criteria

1. WHEN the Player defeats an Enemy without having taken damage since the last kill, THE Game SHALL increment the Combo counter by 1.
2. WHEN the Combo counter reaches 3 or more, THE Player SHALL receive bonus Coins equal to the Combo count for each subsequent kill.
3. WHEN the Combo counter reaches 5 or more, THE Player SHALL receive a Combo_Buff granting increased movement speed and increased Weapon damage for 300 frames (5 seconds).
4. WHEN the Player takes damage, THE Combo counter SHALL reset to 0 and any active Combo_Buff SHALL end immediately.
5. WHEN no Enemy is killed for 300 frames (5 seconds) of inactivity, THE Combo counter SHALL reset to 0.

---

### Requirement 6: Shop System

**User Story:** As a player, I want to purchase weapons using coins, so that I can defeat enemies more effectively.

#### Acceptance Criteria

1. THE HUD SHALL display a Shop icon that the Player can click to open the Shop modal.
2. THE Shop SHALL offer three Weapons for purchase: Spear (30 coins), Gun (100 coins), Grenade (150 coins).
3. WHEN the Player clicks BUY for a Weapon and has sufficient Coins, THE Shop SHALL deduct the Weapon's cost from the Player's Coin count and grant the Weapon with its full ammo.
4. IF the Player has insufficient Coins for a Weapon, THEN THE Shop SHALL display the BUY button in a disabled state and not process the purchase.
5. WHEN a Weapon is purchased, THE weapon_manager.weapons_bought counter SHALL increment by 1.
6. THE Shop modal SHALL display a close button that dismisses the modal without purchasing.

---

### Requirement 7: Weapon System

**User Story:** As a player, I want to use purchased weapons to defeat enemies, so that I can complete the kill mission and survive.

#### Acceptance Criteria

1. THE Player SHALL be able to fire the Gun by pressing the F key, consuming 1 ammo per shot with a maximum of 35 rounds.
2. THE Player SHALL be able to throw the Spear or Grenade by pressing the T key, consuming 1 ammo per throw (Spear: 10 max, Grenade: 15 max).
3. WHEN a Bullet hits an Enemy, THE Enemy SHALL lose 3 HP.
4. WHEN a Spear hits an Enemy, THE Enemy SHALL lose 5 HP.
5. WHEN a Grenade explodes within 90 pixels of an Enemy, THE Enemy SHALL lose 5 HP.
6. THE HUD SHALL display the ammo count for each owned Weapon at all times during gameplay.
7. WHEN a Weapon's ammo reaches 0, THE Weapon SHALL be removed from the Player's inventory.

---

### Requirement 8: Enemy System

**User Story:** As a player, I want enemies to spawn and attack me, so that the game presents a challenge.

#### Acceptance Criteria

1. THE Game SHALL spawn Enemies on Platforms and Ground segments at regular intervals of 420 frames (7 seconds).
2. WHEN an Enemy is within 260 pixels of the Player, THE Enemy SHALL enter chase state and move toward the Player at 3 pixels per frame.
3. WHILE an Enemy is outside 260 pixels of the Player, THE Enemy SHALL patrol back and forth within its home surface bounds at 2 pixels per frame.
4. WHEN an Enemy makes contact with the Player and the Player is not invincible, THE Enemy SHALL deal 20 HP damage to the Player with a cooldown of 90 frames between hits.
5. WHEN an Enemy's HP reaches 0, THE Enemy SHALL play a death particle animation and be removed from the World.
6. WHEN an Enemy is defeated, THE enemy_manager.enemies_killed counter SHALL increment by 1.
7. THE Game SHALL pre-spawn Enemies on every third Platform and on alternating Ground segments at game start.

---

### Requirement 9: Platform System

**User Story:** As a player, I want to jump between platforms at reachable heights, so that the game is fair and navigable.

#### Acceptance Criteria

1. THE Game SHALL generate Platforms at horizontal gaps and vertical offsets within the Player's maximum jump range.
2. THE Game SHALL generate approximately 30% of Platforms as Glitch_Platforms.
3. WHEN the Player stands on a Glitch_Platform for the first time, THE Glitch_Platform SHALL flicker for 50 frames as a warning before disappearing.
4. WHEN a Glitch_Platform disappears, THE Glitch_Platform SHALL remain invisible for 180 frames (3 seconds) before reappearing.
5. IF the Player is on a Glitch_Platform when it disappears, THEN THE Player SHALL fall.
6. THE Game SHALL continuously generate new Platforms as the Player progresses forward.

---

### Requirement 10: Ground and Pit System

**User Story:** As a player, I want the ground to have gaps, so that navigation requires skill and attention.

#### Acceptance Criteria

1. THE Game SHALL generate Ground segments separated by Pits of 80 to 220 pixels in width.
2. THE Game SHALL ensure the first Ground segment is at least 300 pixels wide so the Player spawns safely.
3. WHEN the Player falls below the screen boundary (y > screen height + 60 pixels), THE Health system SHALL register a Pit fall and apply 25 HP damage.
4. WHEN the Player survives a Pit fall, THE Player SHALL respawn at the last recorded Respawn_Point.
5. THE Health system SHALL update the Respawn_Point to the Player's current position whenever the Player is standing on a Ground segment.

---

### Requirement 11: Environmental Hazards — Falling Rocks

**User Story:** As a player, I want to dodge falling rocks, so that I must stay alert even when not near enemies.

#### Acceptance Criteria

1. THE Game SHALL spawn Falling_Rocks at random horizontal positions above the visible screen area at random intervals.
2. WHEN a Falling_Rock contacts the Player, THE Player SHALL lose HP equal to the rock's damage value.
3. WHILE a Falling_Rock is falling, THE Game SHALL apply downward gravity to the Falling_Rock.
4. WHEN a Falling_Rock contacts the Ground or a Platform, THE Falling_Rock SHALL be removed from the World.

---

### Requirement 12: Difficulty Progression

**User Story:** As a player, I want the game to get harder over time, so that the experience remains challenging as I improve.

#### Acceptance Criteria

1. THE Game SHALL increase Enemy spawn frequency as game time increases.
2. THE Game SHALL increase Enemy Projectile speed as game time increases.
3. THE Game SHALL increase the frequency of Falling_Rock spawns as game time increases.
4. THE Game SHALL increase the number of Glitch_Platforms in newly generated sections as game time increases.

---

### Requirement 13: Final Boss System

**User Story:** As a player, I want to fight a Final Boss after completing all missions, so that the game has a satisfying climax.

#### Acceptance Criteria

1. WHEN all three Missions are completed, THE Game SHALL spawn the Final_Boss in the World.
2. THE Final_Boss SHALL have significantly higher HP than a standard Enemy.
3. THE Final_Boss SHALL use unique attack patterns, including firing multiple Projectiles simultaneously or firing Projectiles with increased speed.
4. WHEN the Final_Boss's HP reaches 0, THE Game SHALL display the Mission_Complete_Screen with the message "MISSION COMPLETE!" and options to restart or quit.
5. WHEN the Player selects restart on the Mission_Complete_Screen, THE Game SHALL reset all state and restart from the beginning.
6. WHEN the Player selects quit on the Mission_Complete_Screen, THE Game SHALL return to the main menu.

---

### Requirement 14: Settings Menu

**User Story:** As a player, I want to pause, restart, view instructions, or quit from within the game, so that I have control over my session.

#### Acceptance Criteria

1. WHEN the Player clicks the Settings icon or presses the Escape key during gameplay, THE Settings_Menu SHALL open and pause all game updates.
2. THE Settings_Menu SHALL provide four options: RESUME, RESTART, OPTIONS, and QUIT.
3. WHEN the Player selects RESUME, THE Settings_Menu SHALL close and gameplay SHALL continue from the paused state.
4. WHEN the Player selects RESTART, THE Game SHALL reset all state and restart from the beginning.
5. WHEN the Player selects OPTIONS, THE Game SHALL display the instructions/controls overlay.
6. WHEN the Player selects QUIT, THE Game SHALL return to the main menu.

---

### Requirement 15: Main Menu

**User Story:** As a player, I want a main menu with start, options, and exit choices, so that I can begin or leave the game easily.

#### Acceptance Criteria

1. THE Game SHALL display a main menu with options: START, OPTIONS, and EXIT.
2. WHEN the Player selects START, THE Game SHALL initialise all game state and begin gameplay.
3. WHEN the Player selects OPTIONS, THE Game SHALL display the instructions/controls overlay.
4. WHEN the Player selects EXIT, THE Game SHALL close the application.
5. THE Main menu SHALL support both keyboard navigation (arrow keys + Enter) and mouse click selection.

---

### Requirement 16: HUD Layout

**User Story:** As a player, I want all important information visible on screen at all times, so that I can make informed decisions without pausing.

#### Acceptance Criteria

1. THE HUD SHALL display the Health_Bar in the top-left corner of the screen at all times during gameplay.
2. THE HUD SHALL display the Coin count with a coin icon in the top area of the screen at all times during gameplay.
3. THE HUD SHALL display the Mission_Banner in the top-right area of the screen at all times during gameplay.
4. THE HUD SHALL display the Shop icon adjacent to the Mission_Banner at all times during gameplay.
5. THE HUD SHALL display the Settings icon in the top-right corner of the screen at all times during gameplay.
6. THE HUD SHALL display the ammo slots for owned Weapons in the bottom-left corner of the screen at all times during gameplay.
