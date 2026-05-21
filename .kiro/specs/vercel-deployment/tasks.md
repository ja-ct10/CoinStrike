# Implementation Plan: Vercel Deployment for CoinStrike

## Overview

This implementation plan converts the Vercel deployment design into actionable tasks for deploying the CoinStrike web version to Vercel. The tasks cover Vercel configuration setup, web platform performance optimizations, custom loading page implementation, and deployment automation. Since this is an infrastructure/deployment spec focused on configuration and deployment automation, no property-based tests are included.

## Tasks

- [x] 1. Create Vercel configuration file
  - Create `vercel-deploy/vercel.json` with static builder configuration
  - Configure `@vercel/static` builder for all files (`"src": "**"`)
  - Add CORS headers: `Cross-Origin-Embedder-Policy: require-corp` and `Cross-Origin-Opener-Policy: same-origin`
  - Configure routing rules to map `/(.*)` to `/$1` destination
  - Set API version to 2
  - _Requirements: 2.1, 2.2, 2.3, 2.5, 3.1, 3.5_

- [x] 2. Implement web platform performance optimizations in main.py
  - [x] 2.1 Add web platform detection logic
    - Import `sys` module at the top of main.py
    - Add platform detection: `IS_WEB = sys.platform == "emscripten"`
    - Define web-specific performance limits: `WEB_FPS = 60`, `WEB_MAX_ENEMIES = 5`, `WEB_MAX_PARTICLES = 30`
    - _Requirements: 4.1, 4.3, 4.4_
  - [x] 2.2 Apply FPS limit in game loop
    - Modify `clock.tick()` call to use `WEB_FPS` when `IS_WEB` is True
    - Ensure frame timing uses 60 FPS target for web platform
    - _Requirements: 4.1, 4.2_
  - [x] 2.3 Add asyncio yield in game loop
    - Import `asyncio` module
    - Add `await asyncio.sleep(0)` at the end of the main game loop to yield control to browser event loop
    - Ensure the main game function is defined as `async def main()`
    - _Requirements: 7.5_
  - [x] 2.4 Implement enemy count limiting for web
    - Modify enemy spawning logic in EnemyManager to check `IS_WEB` flag
    - Limit concurrent enemies to `WEB_MAX_ENEMIES` (5) when on web platform
    - Skip spawning new enemies when limit is reached
    - _Requirements: 4.3, 7.2_
  - [x] 2.5 Implement particle effect limiting for web
    - Modify particle creation logic to check `IS_WEB` flag
    - Limit total particles to `WEB_MAX_PARTICLES` (30) when on web platform
    - Prune oldest particles when limit is exceeded
    - _Requirements: 4.4, 7.3_

- [x] 3. Checkpoint - Verify web optimizations
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Customize loading page in index.html
  - [x] 4.1 Add custom loading page background image
    - Locate the `#infobox` style block in index.html
    - Replace background color with `background: url("loading-page.jpg") center/cover`
    - Set infobox to full viewport: `width: 100%; height: 100%;`
    - Add flexbox centering: `display: flex; align-items: center; justify-content: center;`
    - _Requirements: 5.1, 5.5_
  - [x] 4.2 Create custom progress bar styling
    - Add `.progress-container` style with semi-transparent background: `background: rgba(0, 0, 0, 0.7); padding: 20px; border-radius: 10px;`
    - Add `.progress-bar` style with fixed width (400px), height (30px), border, and dark background
    - Add `.progress-fill` style with gradient fill: `background: linear-gradient(90deg, #00ffff, #ff00ff);`
    - Add transition for smooth progress updates: `transition: width 0.3s;`
    - _Requirements: 5.2, 5.3_
  - [x] 4.3 Update loading page HTML structure
    - Replace the default `#infobox` content with custom progress bar HTML
    - Add progress container div with progress bar and progress text elements
    - Add `<span id="progress-percent">0</span>%` for dynamic percentage display
    - Use PressStart2P font for progress text to match game style
    - _Requirements: 5.2, 5.3, 5.5, 12.2, 12.3, 12.5_
  - [x] 4.4 Implement progress bar update logic
    - Locate the progress update code in the JavaScript section
    - Modify to update both the progress bar width and percentage text
    - Set `progress-fill` width to match download percentage
    - Update `progress-percent` text content with current percentage
    - Add "Loading complete..." message when progress reaches 100%
    - _Requirements: 12.1, 12.2, 12.4_

- [x] 5. Remove click-to-start requirement
  - [x] 5.1 Bypass user media engagement check
    - Locate the `if (!platform.window.MM.UME)` block in the `custom_site()` function
    - Comment out or remove the entire UME check block that waits for user gesture
    - Remove the "Ready to start! Please click/touch page" message display
    - _Requirements: 6.1, 6.2, 6.3_
  - [x] 5.2 Enable direct menu transition
    - Ensure `await shell.source(main, callback=ui_callback)` executes immediately after asset loading
    - Ensure `platform.window.infobox.style.display = "none"` hides loading screen when complete
    - Verify no blocking prompts appear between loading and menu
    - _Requirements: 6.2, 6.4_

- [x] 6. Checkpoint - Test loading experience
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create deployment file validation script
  - [x] 7.1 Create validate_deployment.py script
    - Create new Python script in project root: `validate_deployment.py`
    - Define `validate_deployment_files(deploy_dir: str)` function
    - Define required files dictionary with minimum size requirements
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  - [x] 7.2 Implement file existence and size checks
    - Check each required file exists in deployment directory
    - Verify index.html exists and is >1KB
    - Verify coinstrike.apk exists and is >100MB
    - Verify coinstrike.tar.gz exists and is >100MB
    - Verify vercel.json exists and is >100 bytes
    - Verify favicon.png exists
    - _Requirements: 8.1, 8.2, 8.3_
  - [x] 7.3 Implement JSON validation for vercel.json
    - Attempt to parse vercel.json as JSON
    - Catch JSON parsing errors and report line number
    - Return validation error if JSON is invalid
    - _Requirements: 8.4, 11.3_
  - [x] 7.4 Add error reporting and exit codes
    - Return tuple of (is_valid: bool, missing_files: list[str])
    - Print detailed error messages listing all missing/invalid files
    - Exit with code 1 if validation fails, 0 if successful
    - Add main block to run validation when script is executed
    - _Requirements: 8.5, 11.1_

- [x] 8. Create deployment preparation script
  - [x] 8.1 Create prepare_deployment.py script
    - Create new Python script in project root: `prepare_deployment.py`
    - Import `shutil` for file operations
    - Define function to copy files from docs/ to vercel-deploy/
    - _Requirements: 10.2, 10.3_
  - [x] 8.2 Implement file copying logic
    - Copy all files from docs/ directory to vercel-deploy/ directory
    - Preserve existing vercel.json in vercel-deploy/ (do not overwrite)
    - Preserve existing loading-page.jpg in vercel-deploy/ (do not overwrite)
    - Preserve .vercel/ directory in vercel-deploy/
    - _Requirements: 10.2, 10.3, 10.4, 10.5_
  - [x] 8.3 Add validation call after copying
    - Call `validate_deployment_files()` after copying completes
    - Display validation results
    - Exit with error if validation fails
    - _Requirements: 10.5_

- [x] 9. Create deployment documentation
  - [x] 9.1 Create VERCEL_DEPLOYMENT.md guide
    - Create new markdown file in project root: `VERCEL_DEPLOYMENT.md`
    - Add overview section explaining Vercel deployment process
    - Document prerequisites: Vercel CLI installation, authentication
    - _Requirements: 9.1, 9.2, 11.4_
  - [x] 9.2 Document deployment workflow steps
    - Add step-by-step deployment instructions
    - Document build command: `pygbag --build --disable-sound-format-error .`
    - Document preparation command: `python prepare_deployment.py`
    - Document validation command: `python validate_deployment.py vercel-deploy`
    - Document deployment command: `cd vercel-deploy && vercel --prod`
    - _Requirements: 1.1, 9.1, 10.1_
  - [x] 9.3 Add troubleshooting section
    - Document common deployment errors and solutions
    - Add section for missing files errors with checklist
    - Add section for authentication errors with `vercel login` instructions
    - Add section for CORS errors with browser compatibility notes
    - Add section for network errors with retry suggestions
    - Add section for game loading failures with diagnostic checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_
  - [x] 9.4 Document post-deployment verification
    - Add checklist for verifying deployment success
    - Document how to check production URL
    - Document how to verify CORS headers using browser DevTools
    - Document how to test game loading and performance
    - Add expected deployment time (<5 minutes)
    - _Requirements: 1.5, 9.3, 9.5_

- [x] 10. Checkpoint - Review documentation and scripts
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Add loading-page.jpg asset to vercel-deploy
  - Copy the game background image or create custom loading screen image
  - Save as `vercel-deploy/loading-page.jpg`
  - Ensure image dimensions are appropriate for web (1920x1080 or similar)
  - Optimize image file size for fast loading (<500KB recommended)
  - _Requirements: 5.1, 10.3_

- [x] 12. Initialize Vercel project configuration
  - [x] 12.1 Create .vercel directory structure
    - Create `vercel-deploy/.vercel/` directory if it doesn't exist
    - Create `vercel-deploy/.vercel/project.json` file
    - _Requirements: 9.4_
  - [x] 12.2 Configure project linking metadata
    - Add project_id and org_id to project.json (use existing values if available)
    - Set production_url to `https://vercel-deploy-psi-lyart.vercel.app`
    - Set framework, build_command, output_directory, install_command to null
    - _Requirements: 9.2, 9.4_

- [x] 13. Final integration and deployment test
  - [x] 13.1 Run full deployment workflow
    - Execute `python prepare_deployment.py` to copy files
    - Execute `python validate_deployment.py vercel-deploy` to validate
    - Navigate to vercel-deploy directory
    - Execute `vercel --prod` to deploy to production
    - _Requirements: 1.1, 1.2, 1.3_
  - [x] 13.2 Verify deployment success
    - Confirm Vercel CLI returns production URL
    - Visit production URL in browser
    - Verify custom loading screen appears with progress bar
    - Verify game loads without click-to-start prompt
    - Verify game runs at stable 60 FPS
    - Check browser console for CORS errors (should be none)
    - Test gameplay for 5 minutes to ensure no freezing
    - _Requirements: 1.2, 2.4, 4.5, 5.4, 6.4, 7.1, 9.5_

- [x] 14. Final checkpoint - Deployment complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- This is an infrastructure/deployment spec, so no property-based tests are included
- All tasks involve configuration files, scripts, or deployment automation
- The game code (Python/Pygame) requires minimal modifications for web platform detection
- Most changes are to index.html (loading page customization) and vercel.json (CORS configuration)
- Deployment validation happens before upload to catch errors early
- The workflow is designed for single-command deployment: `vercel --prod`
- Custom loading page provides branded experience during asset download
- Web performance optimizations ensure stable 60 FPS gameplay
- CORS headers are critical for WebAssembly/SharedArrayBuffer support

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1", "11"] },
    { "id": 1, "tasks": ["2.1", "7.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "7.2", "7.3", "8.1"] },
    { "id": 3, "tasks": ["2.4", "2.5", "7.4", "8.2"] },
    { "id": 4, "tasks": ["4.1", "4.2", "8.3", "9.1"] },
    { "id": 5, "tasks": ["4.3", "4.4", "5.1", "9.2", "9.3", "12.1"] },
    { "id": 6, "tasks": ["5.2", "9.4", "12.2"] },
    { "id": 7, "tasks": ["13.1"] },
    { "id": 8, "tasks": ["13.2"] }
  ]
}
```
