# CoinStrike - GitHub Pages Deployment Guide

This guide explains how to deploy CoinStrike as a web game on GitHub Pages.

## Prerequisites

- Git repository on GitHub
- Python 3.7+ with Pygbag installed (`pip install pygbag`)

## Deployment Steps

### 1. Build the Web Version

The web version has already been built and is in the `docs/` folder. To rebuild:

```bash
pygbag --build --disable-sound-format-error .
```

Then copy the build output to docs:

```bash
cp -r build/web/* docs/
```

### 2. Push to GitHub

```bash
git add docs/
git commit -m "Deploy web version to GitHub Pages"
git push origin main
```

### 3. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages**
3. Under "Source", select:
   - **Branch**: `main`
   - **Folder**: `/docs`
4. Click **Save**

### 4. Access Your Game

After a few minutes, your game will be available at:

```
https://YOUR-USERNAME.github.io/YOUR-REPO-NAME/
```

## Updating the Game

To update the web version after making changes:

1. Make your code changes
2. Rebuild with Pygbag:
   ```bash
   pygbag --build --disable-sound-format-error .
   cp -r build/web/* docs/
   ```
3. Commit and push:
   ```bash
   git add docs/
   git commit -m "Update web version"
   git push origin main
   ```

GitHub Pages will automatically update within a few minutes.

## Troubleshooting

### Game doesn't load

- Check browser console for errors (F12)
- Ensure all files in `docs/` are committed
- Wait 5-10 minutes for GitHub Pages to deploy

### Audio doesn't work

- MP3 format is not supported in browsers
- Convert audio to OGG format for web compatibility
- Or use `--disable-sound-format-error` flag (audio will be silent)

### Performance issues

- Web version may run slower than desktop
- Try closing other browser tabs
- Use a modern browser (Chrome, Firefox, Edge)

## Technical Notes

- The game runs using WebAssembly (Python compiled to WASM)
- All assets are bundled in the `.apk` file
- Security features (file integrity checks) are disabled for web version
- The game uses async/await for browser compatibility

## Local Testing

To test the web version locally before deploying:

```bash
pygbag .
```

This starts a local server at `http://localhost:8000`

Press Ctrl+C to stop the server.
