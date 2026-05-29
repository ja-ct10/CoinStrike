"""
build_web.py — Automated Pygbag web build for CoinStrike
=========================================================
Creates a clean temporary directory with only the necessary files,
runs pygbag to build, then copies outputs to docs/ and vercel-deploy/.

Usage:
    python build_web.py
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


# ── Configuration ──────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
TEMP_DIR = ROOT / "coinstrike"
DOCS_DIR = ROOT / "docs"
VERCEL_DIR = ROOT / "vercel-deploy"

# Only copy these Python files (the game code)
PYTHON_FILES = [
    "main.py",
    "settings.py",
    "camera.py",
    "player.py",
    "health.py",
    "mission.py",
    "coins.py",
    "shop.py",
    "weapon.py",
    "enemy.py",
    "world.py",
    "difficulty.py",
    "rocks.py",
    "combo.py",
    "powerups.py",
    "score.py",
    "security.py",
    "platforms.py",
    "utils.py",
    "item_box.py",
    "menu.py",
]

# These are the output files pygbag generates (index.html is handled separately to protect custom design)
BUILD_OUTPUTS = [
    "favicon.png",
]
# Large archive files (these go to docs but NOT to vercel-deploy initially —
# they'll be copied separately so we can track their size)
ARCHIVE_OUTPUTS = [
    "coinstrike.apk",
    "coinstrike.tar.gz",
]


def clean(directory: Path):
    """Remove a directory tree if it exists."""
    if directory.exists():
        shutil.rmtree(directory)
        print(f"  Cleaned: {directory}")


def prepare_temp():
    """Create a clean temporary build directory with only required files."""
    clean(TEMP_DIR)
    TEMP_DIR.mkdir()
    print(f"  Created: {TEMP_DIR}")

    # Copy Python files
    for py_file in PYTHON_FILES:
        src = ROOT / py_file
        if src.exists():
            shutil.copy2(src, TEMP_DIR / py_file)
        else:
            print(f"  WARNING: {py_file} not found, skipping")

    # Copy assets directory (recursively)
    assets_src = ROOT / "assets"
    assets_dst = TEMP_DIR / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, assets_dst)
        print(f"  Copied assets/  ({sum(1 for _ in assets_dst.rglob('*'))} files)")
    else:
        print("  ERROR: assets/ directory not found!")
        sys.exit(1)

    # Create a highscores.json stub for web
    (TEMP_DIR / "highscores.json").write_text('{"high_score": 0}')

    total_size = sum(f.stat().st_size for f in TEMP_DIR.rglob("*") if f.is_file())
    print(f"  Build directory size: {total_size / (1024 * 1024):.1f} MB")


def run_pygbag():
    """Run pygbag to build the web version from the clean temp directory."""
    print("\n--- Running pygbag build ---")

    cmd = [
        sys.executable, "-m", "pygbag",
        "--build",
        str(TEMP_DIR),
    ]

    print(f"  Command: {' '.join(cmd)}")

    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=False)

    if result.returncode != 0:
        print(f"\n  ERROR: pygbag build failed with exit code {result.returncode}")
        print("  Try running: pip install pygbag")
        sys.exit(1)

    print("  pygbag build completed successfully!")


def copy_outputs():
    """Copy build outputs to docs/ and vercel-deploy/."""
    print("\n--- Copying build outputs ---")

    # The pygbag build output goes to TEMP_DIR/build/web/
    build_web = TEMP_DIR / "build" / "web"

    if not build_web.exists():
        print(f"  ERROR: Build output directory not found at {build_web}")
        print("  Listing temp directory contents:")
        for p in TEMP_DIR.rglob("*"):
            print(f"    {p.relative_to(TEMP_DIR)}")
        sys.exit(1)

    # Ensure output directories exist
    DOCS_DIR.mkdir(exist_ok=True)
    VERCEL_DIR.mkdir(exist_ok=True)

    # Copy all build outputs (except index.html) to both docs/ and vercel-deploy/
    for filename in BUILD_OUTPUTS + ARCHIVE_OUTPUTS:
        src = build_web / filename
        if src.exists():
            # Copy to docs/
            shutil.copy2(src, DOCS_DIR / filename)
            # Copy to vercel-deploy/
            shutil.copy2(src, VERCEL_DIR / filename)
            size_mb = src.stat().st_size / (1024 * 1024)
            print(f"  {filename}: {size_mb:.1f} MB -> docs/ + vercel-deploy/")
        else:
            print(f"  WARNING: {filename} not found in build output")

    # Handle index.html preserving custom-designed loader page
    custom_index = VERCEL_DIR / "index.html"
    generated_index = build_web / "index.html"
    if custom_index.exists():
        # Copy our beautiful custom index to docs/ so both GitHub and Vercel look stunning
        shutil.copy2(custom_index, DOCS_DIR / "index.html")
        print("  index.html: Custom loading screen copied to docs/index.html successfully!")
    elif generated_index.exists():
        shutil.copy2(generated_index, VERCEL_DIR / "index.html")
        shutil.copy2(generated_index, DOCS_DIR / "index.html")
        print("  index.html: Generated default index.html copied to docs/ + vercel-deploy/")
    else:
        print("  WARNING: index.html not found anywhere!")

    # Copy loading-page.jpg to vercel-deploy (for the loading screen)
    loading_page = ROOT / "assets" / "loading-page.jpg"
    if loading_page.exists():
        shutil.copy2(loading_page, VERCEL_DIR / "loading-page.jpg")
        print(f"  loading-page.jpg -> vercel-deploy/")

    # Also copy loading-page.jpg to docs/ for GitHub Pages
    if loading_page.exists():
        shutil.copy2(loading_page, DOCS_DIR / "loading-page.jpg")
        print(f"  loading-page.jpg -> docs/")


def verify():
    """Verify the build outputs exist and check sizes."""
    print("\n--- Verification ---")

    all_ok = True
    for filename in BUILD_OUTPUTS + ARCHIVE_OUTPUTS:
        vercel_file = VERCEL_DIR / filename
        docs_file = DOCS_DIR / filename

        if vercel_file.exists():
            size_mb = vercel_file.stat().st_size / (1024 * 1024)
            status = "[OK]" if size_mb < 50 else "[WARN - LARGE]"
            print(f"  {status} vercel-deploy/{filename}: {size_mb:.1f} MB")
        else:
            print(f"  [MISSING] vercel-deploy/{filename}: MISSING")
            all_ok = False

        if docs_file.exists():
            size_mb = docs_file.stat().st_size / (1024 * 1024)
            print(f"  [OK] docs/{filename}: {size_mb:.1f} MB")

    # Check for loading-page.jpg
    lp = VERCEL_DIR / "loading-page.jpg"
    if lp.exists():
        print(f"  [OK] vercel-deploy/loading-page.jpg: {lp.stat().st_size / 1024:.0f} KB")
    else:
        print(f"  [MISSING] vercel-deploy/loading-page.jpg: MISSING")
        all_ok = False

    # Check vercel.json
    vj = VERCEL_DIR / "vercel.json"
    if vj.exists():
        print(f"  [OK] vercel-deploy/vercel.json: present")
    else:
        print(f"  [WARN] vercel-deploy/vercel.json: MISSING (create manually)")

    return all_ok


def cleanup():
    """Remove the temporary build directory."""
    print("\n--- Cleanup ---")
    clean(TEMP_DIR)


def main():
    print("=" * 60)
    print("  CoinStrike Web Build Script")
    print("=" * 60)

    print("\n--- Step 1: Prepare clean build directory ---")
    prepare_temp()

    print("\n--- Step 2: Build with pygbag ---")
    run_pygbag()

    print("\n--- Step 3: Copy outputs ---")
    copy_outputs()

    print("\n--- Step 4: Verify ---")
    ok = verify()

    print("\n--- Step 5: Cleanup ---")
    cleanup()

    print("\n" + "=" * 60)
    if ok:
        print("  BUILD SUCCESSFUL!")
        print("  Files are ready in vercel-deploy/ and docs/")
        print("  Commit and push to trigger Vercel auto-deploy")
    else:
        print("  BUILD COMPLETED WITH WARNINGS")
        print("  Check the output above for details")
    print("=" * 60)


if __name__ == "__main__":
    main()
