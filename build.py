#!/usr/bin/env python3
"""
build.py — Automated build script for CoinStrike

Handles:
- File manifest generation
- PyInstaller build
- Optional PyArmor obfuscation
- Build verification

Usage:
    python build.py                    # Standard build
    python build.py --obfuscate        # Build with code obfuscation
    python build.py --generate-manifest # Only generate file manifest
"""

import os
import sys
import subprocess
import argparse
from security import FileIntegrityChecker


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

# Critical files to include in integrity manifest
CRITICAL_FILES = [
    "main.py",
    "player.py",
    "enemy.py",
    "weapon.py",
    "world.py",
    "platforms.py",
    "coins.py",
    "health.py",
    "camera.py",
    "combo.py",
    "mission.py",
    "shop.py",
    "powerups.py",
    "rocks.py",
    "difficulty.py",
    "item_box.py",
    "menu.py",
    "settings.py",
    "security.py",
]

# PyInstaller spec file
SPEC_FILE = "build_config.spec"

# Output directories
DIST_DIR = "dist"
BUILD_DIR = "build"
OBFUSCATED_DIR = "obfuscated"


# ---------------------------------------------------------------------------
# BUILD FUNCTIONS
# ---------------------------------------------------------------------------


def generate_manifest():
    """Generate file integrity manifest."""
    print("=" * 60)
    print("Generating file integrity manifest...")
    print("=" * 60)

    checker = FileIntegrityChecker()

    # Filter to only existing files
    existing_files = [f for f in CRITICAL_FILES if os.path.exists(f)]
    missing_files = [f for f in CRITICAL_FILES if not os.path.exists(f)]

    if missing_files:
        print(f"\nWarning: {len(missing_files)} files not found:")
        for f in missing_files:
            print(f"  - {f}")

    print(f"\nGenerating manifest for {len(existing_files)} files...")
    checker.generate_manifest(existing_files)

    print("✓ Manifest generated: file_manifest.json")
    return True


def clean_build():
    """Clean previous build artifacts."""
    print("\nCleaning previous build artifacts...")

    import shutil

    dirs_to_clean = [DIST_DIR, BUILD_DIR, OBFUSCATED_DIR]
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"  Removed: {dir_path}/")

    print("✓ Clean complete")


def run_pyinstaller():
    """Run PyInstaller to build executable."""
    print("\n" + "=" * 60)
    print("Building executable with PyInstaller...")
    print("=" * 60)

    if not os.path.exists(SPEC_FILE):
        print(f"Error: {SPEC_FILE} not found!")
        return False

    try:
        # Run PyInstaller
        cmd = ["pyinstaller", SPEC_FILE, "--clean"]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)

        print(result.stdout)
        print("✓ Build complete")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during build:")
        print(e.stderr)
        return False

    except FileNotFoundError:
        print("Error: PyInstaller not found!")
        print("Install with: pip install pyinstaller")
        return False


def run_pyarmor():
    """Run PyArmor to obfuscate code."""
    print("\n" + "=" * 60)
    print("Obfuscating code with PyArmor...")
    print("=" * 60)

    try:
        # Check if PyArmor is installed
        subprocess.run(["pyarmor", "--version"], check=True, capture_output=True)

        # Obfuscate all Python files
        cmd = ["pyarmor", "gen", "-O", OBFUSCATED_DIR, "-r", "*.py"]

        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        print(f"✓ Code obfuscated to: {OBFUSCATED_DIR}/")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error during obfuscation:")
        print(e.stderr)
        return False

    except FileNotFoundError:
        print("Error: PyArmor not found!")
        print("Install with: pip install pyarmor")
        return False


def verify_build():
    """Verify the built executable exists."""
    print("\n" + "=" * 60)
    print("Verifying build...")
    print("=" * 60)

    # Check for executable
    exe_name = "CoinStrike.exe" if sys.platform == "win32" else "CoinStrike"
    exe_path = os.path.join(DIST_DIR, exe_name)

    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"✓ Executable found: {exe_path}")
        print(f"  Size: {size_mb:.2f} MB")
        return True
    else:
        print(f"✗ Executable not found: {exe_path}")
        return False


def show_summary(obfuscated=False):
    """Show build summary."""
    print("\n" + "=" * 60)
    print("BUILD SUMMARY")
    print("=" * 60)

    print("\nGenerated files:")
    print("  - file_manifest.json (integrity manifest)")

    if obfuscated:
        print(f"  - {OBFUSCATED_DIR}/ (obfuscated source)")

    exe_name = "CoinStrike.exe" if sys.platform == "win32" else "CoinStrike"
    exe_path = os.path.join(DIST_DIR, exe_name)
    print(f"  - {exe_path} (executable)")

    print("\nNext steps:")
    print("  1. Test the executable thoroughly")
    print("  2. Verify anti-cheat detection works")
    print("  3. Test save/load functionality")
    print("  4. Distribute the executable")

    print("\n" + "=" * 60)


# ---------------------------------------------------------------------------
# MAIN BUILD PROCESS
# ---------------------------------------------------------------------------


def build_standard():
    """Standard build process."""
    print("Starting standard build...")

    # Step 1: Generate manifest
    if not generate_manifest():
        return False

    # Step 2: Clean previous builds
    clean_build()

    # Step 3: Build with PyInstaller
    if not run_pyinstaller():
        return False

    # Step 4: Verify
    if not verify_build():
        return False

    show_summary(obfuscated=False)
    return True


def build_obfuscated():
    """Build with code obfuscation."""
    print("Starting obfuscated build...")

    # Step 1: Generate manifest
    if not generate_manifest():
        return False

    # Step 2: Clean previous builds
    clean_build()

    # Step 3: Obfuscate code
    if not run_pyarmor():
        return False

    # Step 4: Build from obfuscated code
    print("\nBuilding from obfuscated code...")
    original_dir = os.getcwd()

    try:
        # Copy spec file to obfuscated directory
        import shutil

        shutil.copy(SPEC_FILE, OBFUSCATED_DIR)

        # Change to obfuscated directory
        os.chdir(OBFUSCATED_DIR)

        # Build
        if not run_pyinstaller():
            os.chdir(original_dir)
            return False

        # Move dist back to original directory
        os.chdir(original_dir)
        if os.path.exists(DIST_DIR):
            shutil.rmtree(DIST_DIR)
        shutil.move(os.path.join(OBFUSCATED_DIR, DIST_DIR), DIST_DIR)

    except Exception as e:
        print(f"Error during obfuscated build: {e}")
        os.chdir(original_dir)
        return False

    # Step 5: Verify
    if not verify_build():
        return False

    show_summary(obfuscated=True)
    return True


# ---------------------------------------------------------------------------
# COMMAND LINE INTERFACE
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Build CoinStrike with security features"
    )

    parser.add_argument(
        "--obfuscate", action="store_true", help="Build with PyArmor code obfuscation"
    )

    parser.add_argument(
        "--generate-manifest",
        action="store_true",
        help="Only generate file integrity manifest",
    )

    parser.add_argument(
        "--clean", action="store_true", help="Only clean build artifacts"
    )

    args = parser.parse_args()

    # Handle specific actions
    if args.clean:
        clean_build()
        return

    if args.generate_manifest:
        generate_manifest()
        return

    # Full build
    if args.obfuscate:
        success = build_obfuscated()
    else:
        success = build_standard()

    if success:
        print("\n✓ Build completed successfully!")
        sys.exit(0)
    else:
        print("\n✗ Build failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
