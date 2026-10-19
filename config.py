"""
Configuration, Constants, Asset Paths, and Theme Palettes for Blackjack.

Provides centralized configuration for:
- Standard casino Blackjack rules & shoe specifications.
- Wagering denominations, bankroll starting values, and chip color styling.
- Cross-platform asset directory path resolution (supporting PyInstaller frozen bundles).
- Dynamic theme palettes (Casino, Creep, Omen, Hell's Table, Celestial Victory).
- Hex color math utilities.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


# ============================================================================
# Application Metadata & Rule Constants
# ============================================================================
APP_VERSION = "1.3.0"

# Standard Blackjack target and casino dealer rules
BLACKJACK_TARGET = 21
DEALER_STAND_THRESHOLD = 17  # Standard casino rule: Dealer must stand on 17 or higher

# Shoe and Multi-Deck Configuration
DEFAULT_DECK_COUNT = 4  # Standard casino multi-deck shoe (4 decks = 208 cards)
CUT_CARD_PENETRATION = 0.25  # Cut card reshuffle trigger (when <= 25% cards remain)

# Bankroll and Betting Configuration
STARTING_BANKROLL = 1000
MINIMUM_BET = 5
CHIP_DENOMINATIONS = [
    (5, "#f5f5f5", "#000000"),    # White $5
    (25, "#c62828", "#ffffff"),   # Red $25
    (100, "#2e7d32", "#ffffff"),  # Green $100
    (500, "#212121", "#ffd700"),  # Black & Gold $500
]
INSURANCE_PAYOUT_RATIO = 2  # Standard casino rule: Insurance pays 2 to 1

# UI Animation Timing (in milliseconds)
DEALER_DRAW_DELAY_MS = 700

# Window dimensions and styling
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 720
MIN_WINDOW_WIDTH = 760
MIN_WINDOW_HEIGHT = 650
CARD_WIDTH = 74
CARD_HEIGHT = 107
PLAYER_CARD_OVERLAP_OFFSET = 26
TABLE_BACKGROUND_COLOR = "#0b6623"  # Classic casino felt green
PANEL_BACKGROUND_COLOR = "#074c1a"  # Darker contrasting green


# ============================================================================
# Asset Paths & Directory Resolution
# ============================================================================

def get_base_dir() -> Path:
    """
    Resolves the base directory for resource loading across standard Python execution
    and PyInstaller frozen bundles (both --onedir and --onefile).
    """
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            mei_path = Path(sys._MEIPASS)
            if (mei_path / "cards").exists():
                return mei_path
        exe_parent = Path(sys.executable).resolve().parent
        if (exe_parent / "cards").exists():
            return exe_parent
        if (exe_parent / "_internal" / "cards").exists():
            return exe_parent / "_internal"
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
ASSETS_DIR = BASE_DIR / "cards"
AUDIO_DIR = BASE_DIR / "audio"
ASSETS_EXTRA_DIR = BASE_DIR / "assets"
OVERLAY_ICONS_DIR = ASSETS_EXTRA_DIR / "overlay_icons"
HAUNTED_ASSETS_DIR = ASSETS_EXTRA_DIR / "haunted"
HAUNTED_AUDIO_DIR = AUDIO_DIR / "haunted"
DEFAULT_SOUND_VOLUME = 0.7


# ============================================================================
# Chip Visualizer Color Styles
# ============================================================================

CHIP_STYLES = {
    500: {"bg": "#212121", "fg": "#ffd700", "rim": "#111111", "stripe": "#ffd700"},
    100: {"bg": "#2e7d32", "fg": "#ffffff", "rim": "#1b5e20", "stripe": "#ffffff"},
    25:  {"bg": "#c62828", "fg": "#ffffff", "rim": "#8e0000", "stripe": "#ffffff"},
    5:   {"bg": "#f5f5f5", "fg": "#212121", "rim": "#bdbdbd", "stripe": "#c62828"},
    1:   {"bg": "#9e9e9e", "fg": "#ffffff", "rim": "#616161", "stripe": "#ffffff"},
}


# ============================================================================
# Color Math Utilities
# ============================================================================

def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """
    Converts a hex color string like '#074c1a' or '074c1a' to an (R, G, B) integer tuple.
    Handles 3-digit shorthand (e.g. '#fff') and graceful fallbacks.
    """
    clean = hex_str.lstrip("#").strip()
    if len(clean) == 3:
        clean = "".join(c * 2 for c in clean)
    if len(clean) != 6:
        return (20, 32, 24)
    try:
        return tuple(int(clean[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (20, 32, 24)


# ============================================================================
# Theme Palettes
# ============================================================================

@dataclass(frozen=True)
class ThemePalette:
    """
    Structured color palette representing the atmospheric visual state
    for table felt, stage horizon, plaques, and dialogues.
    """
    theme_name: str
    table_bg: str
    panel_bg: str
    plaque_border: str
    stage_bg: str
    dialogue_bg: str
    speech_bg: str
    rail_bg: str
    result_fg: str
    felt_theme: str


# Static themes
THEME_NORMAL = ThemePalette(
    theme_name="casino",
    table_bg=TABLE_BACKGROUND_COLOR,
    panel_bg=PANEL_BACKGROUND_COLOR,
    plaque_border="#d4af37",
    stage_bg="#0a0a0a",
    dialogue_bg="#141014",
    speech_bg="#1c161c",
    rail_bg="#073512",
    result_fg="#ffeb3b",
    felt_theme="casino",
)

THEME_OMEN_SNUFFING = ThemePalette(
    theme_name="creep",
    table_bg="#142018",
    panel_bg="#142018",
    plaque_border="#d4af37",
    stage_bg="#0a0a0a",
    dialogue_bg="#141014",
    speech_bg="#1c161c",
    rail_bg="#120914",
    result_fg="#ffeb3b",
    felt_theme="creep",
)

THEME_HELL_TABLE = ThemePalette(
    theme_name="hell",
    table_bg="#140508",
    panel_bg="#0d0204",
    plaque_border="#ff1744",
    stage_bg="#140508",
    dialogue_bg="#1c060a",
    speech_bg="#240a10",
    rail_bg="#2d0a0d",
    result_fg="#ff1744",
    felt_theme="hell",
)

THEME_VICTORY = ThemePalette(
    theme_name="celestial",
    table_bg="#062b1a",
    panel_bg="#031b10",
    plaque_border="#00e5ff",
    stage_bg="#0c2338",
    dialogue_bg="#0a1829",
    speech_bg="#0e2036",
    rail_bg="#06201b",
    result_fg="#00e5ff",
    felt_theme="celestial",
)

CREEP_SHADES = ["#09521c", "#084718", "#073b14", "#062f10", "#05240c", "#142018"]
CREEP_PANEL_SHADES = ["#063e15", "#053612", "#042c0e", "#03230b", "#031908", "#142018"]


def get_creep_theme(hand_counter: int) -> ThemePalette:
    """Returns progressively darker creep shade for hands 7-12."""
    step = min(max(1, hand_counter - 6), 6)
    return ThemePalette(
        theme_name="creep",
        table_bg=CREEP_SHADES[step - 1],
        panel_bg=CREEP_PANEL_SHADES[step - 1],
        plaque_border="#d4af37",
        stage_bg="#0a0a0a",
        dialogue_bg="#141014",
        speech_bg="#1c161c",
        rail_bg="#120914",
        result_fg="#ffeb3b",
        felt_theme="creep",
    )


def get_phase_palette(phase_val: str, hand_counter: int = 1) -> ThemePalette:
    """
    Returns the ThemePalette corresponding to a Haunted phase value.
    Accepts phase as enum or string.
    """
    key = getattr(phase_val, "value", str(phase_val)).lower()
    if key == "hell_table":
        return THEME_HELL_TABLE
    elif key == "victory":
        return THEME_VICTORY
    elif key in ("omen", "snuffing"):
        return THEME_OMEN_SNUFFING
    elif key == "creep":
        return get_creep_theme(hand_counter)
    return THEME_NORMAL
