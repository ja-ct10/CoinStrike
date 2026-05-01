"""
utils.py — Utility functions for CoinStrike

Provides helper functions used across multiple modules.
"""

import sys
import os


def resource_path(relative_path):
    """
    Get absolute path to resource, works for dev and for PyInstaller.

    When running from source, returns the path relative to the current directory.
    When running as a PyInstaller bundle, returns the path relative to the
    temporary extraction directory (_MEIPASS).

    Args:
        relative_path: Path relative to the project root (e.g., "assets/coin.png")

    Returns:
        Absolute path to the resource
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
