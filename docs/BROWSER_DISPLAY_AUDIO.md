# Browser display and audio

## Display and mobile orientation

The custom loader owns CSS canvas placement (`user_canvas_managed: 1`). The
1024×576 framebuffer and gameplay coordinates remain unchanged. Window, visual
viewport, orientation, and fullscreen changes fit the largest 16:9 rectangle
inside the available safe area. Remaining margins on differently shaped screens
are required to preserve the entire scene without stretching or cropping.

The Enter CoinStrike button requests document fullscreen once through a trusted
click or keyboard activation. Rejection leaves viewport gameplay available.
Phones/tablets request landscape lock after fullscreen when supported; manual
rotation remains the fallback. Leaving fullscreen releases an acquired lock.
Fullscreen is not automatically re-entered after the player exits it.

Mobile portrait displays a simple rotation overlay with an explicit fullscreen
button. `coinstrikeTouch.snapshot.portraitBlocked` pauses simulation and boss-intro
timers, rejects gameplay input, and clears virtual holds. Returning to landscape
preserves the run and any Shop/Settings/Options state. Music is independent of
this pause. Desktop portrait-shaped windows remain usable.

Directional buttons retain their circular hit regions and compact sizing, with
an inset ring and arrow glyphs in the existing cyan/purple palette. Weapon button
visibility, reflow, multitouch, and the desktop Options toggle are unchanged.

## Brief crackling after Start in Chrome

The original OGG decodes as 44,100 Hz stereo, lasts about 30.77 seconds, and has
only two near-full-scale samples out of 2,714,112 decoded samples. Its loop
boundary is near zero. No soundtrack replacement or conversion was indicated.

The previous `pre_init` ran after `pygame.init`, so its intended buffer was not
applied at initial mixer creation. Start also synchronously decoded/scaled 16
player images again. Local diagnostics measured a 665 ms reset, including 619 ms
constructing the player. Such a stall can starve Pygbag's main-thread audio queue.

Player surfaces are now cached during initial loading. Local warm resets measured
20.4–22.4 ms (median 22.4 ms), with cached player construction at 0.03 ms. Player
positions and gameplay state remain separate for every run. Mixer defaults are
applied before `pygame.init`: 44,100 Hz, signed 16-bit stereo, 2,048-sample buffer.
One reserved channel starts the original track once at its original volume.
Ordinary input performs no repeated mixer operation; explicit pause/resume is
idempotent, and restarting a run does not restart the track.

## Verification

Run the existing Python and Node test commands documented in TOUCH_CONTROLS.md.
The suites cover initialization order, shared sprites with independent player
state, a single music play call across run resets, portrait input/update blocking,
boss timer freezing, modal preservation, safe-area fitting, fullscreen/lock
acceptance and rejection, mobile rotation, and existing gameplay/controller flows.

Auditory acceptance requires listening in Chrome across Start, repeated restarts,
active play, and a complete music loop. Automated channel assertions and timing
measurements alone do not establish sound quality. Real Chrome/Edge listening and
Android/iOS hardware results must be recorded separately from simulated API tests.
