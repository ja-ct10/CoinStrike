# Compact touch controller

The controller uses small, translucent circles with cached white arrow, pistol,
spear, and grenade icons. Visible circles scale with 6% of the displayed canvas
width, clamped to 36–48 CSS pixels; circular touch targets remain at least 44 CSS
pixels, separated by 8 CSS pixels. Left/Right stay at bottom-left. Jump stays at
bottom-right; available Fire/Throw buttons close gaps immediately to its left.
The full right-hand order is Fire, Throw, Jump, matching the reference design.

`WeaponManager.can_use()` checks existing ownership and positive ammunition;
`get_throw_weapon()` shares the existing Grenade-before-Spear priority with combat.
No weapons means only three controls. A usable Gun reveals Fire; a usable Spear or
Grenade reveals Throw. Cooldown does not hide a button. Purchases, depletion, and
refills synchronize before input and drawing. Throw changes from the Grenade icon
to Spear while held if usable Spears remain after the last Grenade.

The controller combines independent finger holds with physical keyboard state.
Movement and jumping still run in `Player.update`; attacks still run through
`WeaponManager.handle_keydown`, including the original cooldowns and ammunition.
Jump repeats on landing while held, matching the keyboard. Leaving a button,
releasing, cancelling, opening a modal, changing screens, resizing, or losing
focus clears the relevant virtual inputs. Two fingers on one action release
independently. Touch-generated mouse events are ignored to prevent double clicks.

Touch capability enables the controller automatically. Options contains a manual
switch that overrides automatic detection until the page/app is restarted.
The controller is hidden in menus, modals, cutscenes, and end screens. In touch
mode, ammo moves to the bottom center and the keyboard guide is hidden. If narrow
screens leave insufficient room between controllers, ammo moves above the row.
Reflow clears captures only for moved or removed actions, retaining unaffected
holds and physical keys. A moved button requires a fresh press; an existing
pointer is never transferred to another action.

## Build and deployment

```powershell
python -m unittest discover -s tests -v
node --test tests/browser_touch.test.cjs
python build_web.py

# Run from the repository root. The existing Vercel project's root is vercel-deploy.
$coinStrikeProject = Get-Content vercel-deploy/.vercel/project.json | ConvertFrom-Json
$env:VERCEL_PROJECT_ID = $coinStrikeProject.projectId
$env:VERCEL_ORG_ID = $coinStrikeProject.orgId
vercel deploy --yes             # preview
vercel deploy --prod --yes      # existing production website
```

The root `.vercelignore` uploads only `vercel-deploy`, excluding local environment
and linking files. `build_web.py` includes the controller module and copies the
game archives to both deployment directories, preserving the custom loader.
The existing cross-origin headers, project, domain, runtime version, and 1024×576
logical resolution are retained. Pygbag scales the canvas uniformly to fit.

## Verification

- Automated SDL tests cover multitouch, independent releases, same-action fingers,
  quick taps, drag-off, held attacks, ammo depletion, weapon priority, focus and
  resize resets, safe areas, manual override, and keyboard/touch combinations.
- A full-loop test exercises menu and in-game Options, duplicate-click prevention,
  shop purchases, simultaneous move/jump/fire, pause/resume, game-over restart,
  mission-complete restart, and keyboard menu/shop/settings shortcuts.
- Controller layout tests cover rendered canvas sizes from 320×180 to 1024×576,
  with targets at least 44 CSS pixels and ammo clear of the button groups. Native
  screenshots of no weapons, Gun, Spear, Grenade, Gun+Spear, and all weapons are
  generated under `build/touch-qa/compact/`.
- The expanded Python suite passes 23 tests, including visibility combinations,
  last-round depletion and repurchase, priority fallback, circular boundaries,
  transparency/caching, and reflow without input retargeting. The browser bridge
  suite passes three tests. No runtime dependencies were added.
- Run browser checks against the public production domain if Vercel preview
  authentication blocks the Pygbag archive download; preserve preview protection.
- Real Android Chrome and iOS Safari device verification remains pending unless
  explicitly recorded below. Desktop resizing and synthetic SDL events do not
  constitute real-device testing.

Manual device checklist: load and enter the game; move in both directions; hold
move+jump+fire/throw together; release each finger; drag off a button; purchase
and exhaust weapons; pause/resume/restart; rotate and background/resume the page;
confirm no scrolling, zooming, selection, stuck inputs, HUD overlap, or slowdown.

### Initial controller browser check — 2026-11-23

Verified startup, the Options switch, held on-screen movement, shop purchase,
held Fire (35 → 32 rounds), no further ammo consumption after release, and
keyboard movement/pause at `https://coinstrike.vercel.app/`. Browser viewport
checks used 844×390, 390×844, and 1280×720. The portrait canvas measured 390×219
and the landscape canvas 693×390, retaining the 1024×576 logical resolution.
The canvas reports `touch-action: none`. Screenshots are saved locally under
`build/touch-qa/`. These checks used mouse/keyboard input in a desktop browser;
Android and iOS hardware checks remain pending.

The initial Python suite passed 15 tests; the dependency-free Node suite passed three
browser bridge tests, including releasing a finger outside the canvas without
cancelling other held fingers. The deployed archive's ETag matched the local
archive's MD5, and the original COEP/COOP response headers were present.
