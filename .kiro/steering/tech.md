# Tech Stack

## Language & Runtime

- **Python 3** (no build step — run directly with the interpreter)
- **Pygame** — rendering, input, audio, collision detection

## Libraries

- `pygame` — display, surfaces, rects, fonts, mixer, event loop
- `math`, `random` — standard library only; no third-party dependencies

## Assets

- **Font**: `assets/fonts/PressStart2P-Regular.ttf` — used for all in-game text
- **Images**: PNG sprites in `assets/` (player, enemies, weapons, HUD icons, background)
- **Audio**: `assets/sounds/background-music.mp3` — looped via `pygame.mixer.music`

## Common Commands

```bash
# Run the game
python main.py

# Install pygame if missing
pip install pygame
```

No build system, test runner, linter, or virtual environment configuration is present in the repo.

## Performance Conventions

- **Pre-render surfaces once** — fonts, overlays, and static UI elements are rendered at startup or on first use, then cached and reused every frame. Never call `font.render()` or create `pygame.Surface` objects inside the main draw loop.
- **Reuse `pygame.Rect` objects in-place** — update `.x`/`.y` rather than allocating new rects per frame.
- **Shared class-level surfaces** — particle and effect surfaces that are identical across instances use `@classmethod` caches (e.g., `_GLOW_SURF`, `_SHADOW_SURF`).
- **Squared distance checks** — use `dx*dx + dy*dy` instead of `math.sqrt()` for range comparisons where possible.
- Target **60 FPS** (`FPS = 60` in `settings.py`).
