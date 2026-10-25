"""
Pixel UI Module for Blackjack.
Provides:
- Authentic retro pixel font registration via Windows GDI with negative pixel sizing.
- Vintage casino color palette tokens (Hit green, Stand red, Deal gold, Split blue, etc.).
- Procedural 9-slice CanvasPixelPanel (recessed plaques, prompt banners, and wooden rails).
- Interactive CanvasPixelButton with tactile press physics, drop shadow, and Tkinter compatibility shims.
"""

from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path
from typing import Any, Callable, Optional
import tkinter
import tkinter.font as tkfont
import json
from PIL import Image, ImageDraw, ImageTk


# ============================================================================
# Vintage Casino Pixel Art Palette
# ============================================================================
PALETTE = {
    "green":    {"bg": "#247a43", "hi": "#41a866", "sh": "#134726", "hov": "#2e9654"},  # Hit
    "red":      {"bg": "#a83232", "hi": "#d65454", "sh": "#661818", "hov": "#bf3b3b"},  # Stand / All In
    "gold":     {"bg": "#c9982c", "hi": "#ecc260", "sh": "#7d5b10", "hov": "#dbab3b"},  # Deal / Double / New Game
    "blue":     {"bg": "#326da8", "hi": "#5a9bd9", "sh": "#1a4066", "hov": "#3d80c2"},  # Split
    "neutral":  {"bg": "#5a636b", "hi": "#849099", "sh": "#33393d", "hov": "#6b757d"},  # Surrender / Clear Bet
    "amber":    {"bg": "#b86221", "hi": "#e08743", "sh": "#6e350b", "hov": "#cc702b"},  # Rebuy
    "disabled": {"bg": "#1e110b", "hi": "#120906", "sh": "#382117", "text": "#5e4337"},  # Recessed into mahogany wood
    "wood":     {"bg": "#2b170e", "border": "#140a05", "inner_hi": "#593322", "inner_sh": "#1a0d07", "rivet": "#d4af37"},
    "slate":    {"bg": "#141a1d", "border": "#090c0e", "inner_hi": "#2c3940", "inner_sh": "#0a0d0f", "accent": "#5ce6b5"},
}

# ============================================================================
# Centralized Font Registry & JSON Configuration
# ============================================================================

DEFAULT_FONT_CONFIG = {
    "version": "1.0",
    "fonts": {
        "BoldPixels": {"file": "BoldPixels.ttf", "family": "BoldPixels"},
        "m5x7": {"file": "m5x7.ttf", "family": "m5x7"},
        "m6x11": {"file": "m6x11.ttf", "family": "m6x11"},
        "m6x11plus": {"file": "m6x11plus.ttf", "family": "m6x11plus"},
        "Round9x13": {"file": "Round9x13.ttf", "family": "Round9x13"},
        "Volt5x5": {"file": "Volt5x5.ttf", "family": "Volt5x5"},
        "Covenant5x5": {"file": "Covenant5x5.ttf", "family": "Covenant5x5"},
        "Mini3x5": {"file": "Mini3x5.ttf", "family": "Mini3x5"},
        "3x5_Block_Adjusted": {"file": "3x5_Block_Adjusted-Regular.ttf", "family": "3x5_Block_Adjusted"},
    },
    "roles": {
        "title": {"family": "BoldPixels", "base_size": 32, "weight": "normal", "fallback": "m5x7"},
        "header": {"family": "m6x11plus", "base_size": 16, "weight": "normal", "fallback": "m5x7"},
        "display": {"family": "m6x11plus", "base_size": 32, "weight": "normal", "fallback": "m5x7"},
        "body": {"family": "m5x7", "base_size": 16, "weight": "normal", "fallback": "Courier"},
        "button": {"family": "m6x11plus", "base_size": 16, "weight": "normal", "fallback": "m5x7"},
        "digital": {"family": "Volt5x5", "base_size": 15, "weight": "normal", "fallback": "m5x7"},
        "badge": {"family": "Mini3x5", "base_size": 15, "weight": "normal", "fallback": "m5x7"},
        "micro": {"family": "3x5_Block_Adjusted", "base_size": 10, "weight": "normal", "fallback": "m5x7"},
    },
    "elements": {
        "top_bar_button": {"role": "button", "family": "m5x7", "base_size": 16, "description": "System buttons on top bar (Rules, Settings, Shortcuts, Wardrobe, Mute, Scale)"},
        "top_bar_status": {"role": "button", "family": "m5x7", "base_size": 16, "description": "Scale and status readouts on top bar (e.g. 🔍 1x / 2x)"},
        "scoreboard_title": {"role": "header", "family": "m6x11plus", "base_size": 22, "description": "Headers for Dealer, Player, Ties in top bar scoreboard"},
        "scoreboard_value": {"role": "display", "family": "m6x11plus", "base_size": 22, "description": "Win, Loss, and Tie numeric counters in top bar"},
        "bankroll_label": {"role": "display", "family": "m6x11plus", "base_size": 32, "description": "Player bankroll display on top bar"},
        "shoe_counter": {"role": "header", "family": "m5x7", "base_size": 16, "description": "Deck shoe card counter display on table felt"},
        "hand_title": {"role": "header", "family": "m6x11plus", "base_size": 16, "description": "Banners for dealer, player, and split hand areas"},
        "hand_score": {"role": "display", "family": "m6x11plus", "base_size": 32, "description": "Hand score plaques (19, 21, BUST, etc.)"},
        "action_button": {"role": "button", "family": "m5x7", "base_size": 32, "description": "Primary action rail buttons (Hit, Stand, Double, Split, Surrender, New Game)"},
        "cursed_stakes_button": {"role": "button", "family": "m5x7", "base_size": 32, "description": "Cursed stakes / High roller toggle button"},
        "strategy_hint": {"role": "body", "description": "Real-time basic strategy advice banner text"},
        "betting_button": {"role": "button", "family": "m5x7", "base_size": 32, "description": "Bet staging action buttons (Deal, Clear, Rebet, All-In, Rebuy)"},
        "betting_chip_button": {"role": "button", "description": "Quick chip increment buttons in casual mode"},
        "betting_spot_watermark": {"role": "badge", "description": "Felt watermark text inside betting circle"},
        "chip_bet_badge": {"role": "micro", "base_size": 10, "description": "Current staged bet readout above betting spot"},
        "chip_bankroll_badge": {"role": "micro", "base_size": 10, "description": "Reserve tray bankroll header (CHIPS: $... L-Click + | R-Click -)"},
        "chip_denomination_label": {"role": "digital", "base_size": 11, "description": "Denomination label under each reserve pile ($5, $25, $100, $500, $1K)"},
        "chip_face_value": {"role": "micro", "description": "Denomination and multiplier text stamped on individual chip sprites"},
        "chip_floating_payout": {"role": "digital", "description": "Animated floating payout text (+$150)"},
        "chip_push_banner": {"role": "header", "description": "Push announcement banner on betting spot"},
        "insurance_prompt_label": {"role": "header", "description": "Insurance inquiry text prompt"},
        "insurance_prompt_button": {"role": "button", "description": "Take / Decline Insurance action buttons"},
        "dealer_nameplate": {"role": "header", "description": "Dealer character nameplate on narrative dialogue stage"},
        "dealer_speech": {"role": "body", "description": "Dialogue box typewriter speech and narrative subtitles"},
        "table_announcement": {"role": "title", "description": "Centered floating banner announcements (BLACKJACK!, DEALER BUSTS, PUSH)"},
        "hilo_trainer_title": {"role": "header", "description": "Hi-Lo Card Counting Trainer header tab"},
        "hilo_trainer_label": {"role": "badge", "description": "Trainer HUD metric title badges (RC, TC, DECKS, EDGE, BET)"},
        "hilo_trainer_value": {"role": "digital", "description": "Trainer HUD numeric readouts"},
        "hilo_trainer_button": {"role": "button", "description": "Trainer HUD control buttons (Quiz, Assisted, Close)"},
        "hilo_trainer_advice": {"role": "body", "description": "Trainer drill hint and betting recommendation text"},
        "hilo_floating_badge": {"role": "display", "description": "Transient floating count particle badges (+1, -1, 0) above cards"},
        "soul_meter_title": {"role": "title", "description": "Soul Wager Altar HUD banner title"},
        "soul_meter_markers": {"role": "digital", "description": "Soul Meter threshold percentage markers (50%, 75%)"},
        "soul_meter_bounds": {"role": "badge", "description": "Soul Meter extremity labels (ABYSS 0%, LIGHT 100%)"},
        "soul_meter_status": {"role": "header", "description": "Soul Meter dynamic status text"},
        "soul_meter_hint": {"role": "body", "description": "Soul Meter bottom instruction text"},
        "dialog_title": {"role": "title", "description": "Modal dialog top window titles"},
        "dialog_tab": {"role": "header", "description": "Modal dialog tab navigation bar buttons"},
        "dialog_header": {"role": "header", "description": "Modal dialog section headers and mode card titles"},
        "dialog_body": {"role": "body", "description": "Modal dialog explanatory body text, rules, and bios"},
        "dialog_badge": {"role": "badge", "description": "Modal dialog shortcut key badges ([Space], [Esc], etc.)"},
        "dialog_button": {"role": "button", "description": "Modal dialog action and dismissal buttons"},
        "story_dialog_speaker": {"role": "header", "base_size": 20, "description": "Speaker name in narrative story dialogue modal"},
        "story_dialog_body": {"role": "body", "base_size": 18, "description": "Story narrative text in story dialogue modal"},
        "story_dialog_button": {"role": "button", "base_size": 16, "description": "Dismiss / proceed button in story dialogue modal"},
        "angelic_draft_subtitle": {"role": "header", "base_size": 15, "description": "Angelic draft dialog subtitle instruction"},
        "angelic_draft_title": {"role": "header", "base_size": 16, "description": "Relic card title in angelic blessing draft dialog"},
        "angelic_draft_tagline": {"role": "badge", "base_size": 13, "description": "Relic card tagline in angelic blessing draft dialog"},
        "angelic_draft_description": {"role": "body", "base_size": 16, "description": "Relic card power description in angelic blessing draft dialog"},
        "angelic_draft_button": {"role": "button", "base_size": 14, "description": "Equip relic button in angelic blessing draft dialog"}
    }
}

_LOADED_FONT_CONFIG: Optional[dict] = None
_FONT_CONFIG_MTIME: float = 0.0
_REGISTERED_FONTS: dict[str, bool] = {}
_ALL_FONTS_LOADED: bool = False
_PIXEL_FONT_REGISTERED = False
_PIXEL_FONT_FAMILY = "Courier"


def load_font_config(path: Optional[Path | str] = None) -> dict:
    """
    Loads font configuration from JSON file with fallback to internal defaults.
    Automatically detects on-disk modifications via file mtime and reloads.
    """
    global _LOADED_FONT_CONFIG, _FONT_CONFIG_MTIME

    if path is None:
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        candidate = (base_dir / "assets" / "fonts" / "font_config.json").resolve()
    else:
        candidate = Path(path).resolve()

    if candidate.exists():
        try:
            mtime = candidate.stat().st_mtime
            if _LOADED_FONT_CONFIG is not None and path is None and mtime == _FONT_CONFIG_MTIME:
                return _LOADED_FONT_CONFIG
            with open(candidate, "r", encoding="utf-8") as f:
                _LOADED_FONT_CONFIG = json.load(f)
                _FONT_CONFIG_MTIME = mtime
                return _LOADED_FONT_CONFIG
        except Exception:
            pass

    if _LOADED_FONT_CONFIG is not None and path is None:
        return _LOADED_FONT_CONFIG

    _LOADED_FONT_CONFIG = dict(DEFAULT_FONT_CONFIG)
    return _LOADED_FONT_CONFIG


def reload_font_config(path: Optional[Path | str] = None) -> dict:
    """Forces reloading font configuration from disk, clearing in-memory cache."""
    global _LOADED_FONT_CONFIG, _FONT_CONFIG_MTIME
    _LOADED_FONT_CONFIG = None
    _FONT_CONFIG_MTIME = 0.0
    return load_font_config(path)


def load_all_pixel_fonts(root: Optional[tkinter.Tk] = None, fonts_dir: Optional[Path | str] = None) -> dict[str, bool]:
    """
    Registers all pixel font files in assets/fonts/ with Windows GDI and Tkinter.
    Returns a dictionary of registered font families and their availability status.
    """
    global _ALL_FONTS_LOADED, _REGISTERED_FONTS, _PIXEL_FONT_REGISTERED, _PIXEL_FONT_FAMILY
    cfg = load_font_config()

    if fonts_dir is None:
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        target_dir = (base_dir / "assets" / "fonts").resolve()
    else:
        target_dir = Path(fonts_dir).resolve()

    if target_dir.exists() and sys.platform.startswith("win"):
        FR_PRIVATE = 0x10
        # First register known fonts from config
        font_records = cfg.get("fonts", {})
        for record in font_records.values():
            fn = record.get("file")
            if fn:
                p = (target_dir / fn).resolve()
                if p.exists():
                    try:
                        ctypes.windll.gdi32.AddFontResourceExW(str(p), FR_PRIVATE, 0)
                    except Exception:
                        pass
        # Also register any remaining .ttf files in target directory
        for p in target_dir.glob("*.ttf"):
            try:
                ctypes.windll.gdi32.AddFontResourceExW(str(p.resolve()), FR_PRIVATE, 0)
            except Exception:
                pass

    # Verify recognized families in Tkinter
    try:
        dummy_root = root or tkinter._default_root
        if dummy_root is not None:
            available = set(tkfont.families(dummy_root))
            font_records = cfg.get("fonts", {})
            for fam_key, record in font_records.items():
                fam_name = record.get("family", fam_key)
                _REGISTERED_FONTS[fam_name] = (fam_name in available)

            # Ensure m5x7 compatibility flags
            if "m5x7" in available:
                _PIXEL_FONT_FAMILY = "m5x7"
                _PIXEL_FONT_REGISTERED = True
            elif any("m5x7" in f.lower() for f in available):
                for f in available:
                    if "m5x7" in f.lower():
                        _PIXEL_FONT_FAMILY = f
                        _PIXEL_FONT_REGISTERED = True
                        break
    except Exception:
        pass

    _ALL_FONTS_LOADED = True
    return dict(_REGISTERED_FONTS)


def load_pixel_font(root: Optional[tkinter.Tk] = None, font_path: Optional[Path | str] = None) -> str:
    """
    Backward-compatible loader for m5x7.ttf. Calls load_all_pixel_fonts().
    """
    load_all_pixel_fonts(root)
    return _PIXEL_FONT_FAMILY


def get_role_font(
    role: str,
    scale: float = 1.0,
    size_override: Optional[int] = None,
    weight_override: Optional[str] = None
) -> tuple[str, int, str]:
    """
    Resolves a semantic font role into a Tkinter font tuple using exact negative pixel sizing.
    In Tkinter, negative sizes enforce exact pixel dimensions rather than DPI-scaled point sizes.
    Gracefully falls back to secondary pixel fonts or system fonts if unmapped.
    """
    if not _ALL_FONTS_LOADED:
        load_all_pixel_fonts()

    cfg = load_font_config()
    roles = cfg.get("roles", DEFAULT_FONT_CONFIG["roles"])
    role_def = roles.get(role, roles.get("body", {}))

    target_family = role_def.get("family", "m5x7")
    fallback_family = role_def.get("fallback", "Courier")
    base_size = role_def.get("base_size", 14)
    weight = weight_override if weight_override is not None else role_def.get("weight", "normal")

    final_size = size_override if size_override is not None else int(base_size * scale)
    final_size = -abs(int(final_size))

    # Determine best registered font family
    if _REGISTERED_FONTS.get(target_family, False):
        resolved_family = target_family
    elif _REGISTERED_FONTS.get(fallback_family, False):
        resolved_family = fallback_family
    elif _PIXEL_FONT_REGISTERED:
        resolved_family = _PIXEL_FONT_FAMILY
    else:
        resolved_family = fallback_family if fallback_family in ("Courier", "Arial") else "Courier"

    return (resolved_family, final_size, weight)


def get_element_font(
    element_name: str,
    scale: float = 1.0,
    size_override: Optional[int] = None,
    weight_override: Optional[str] = None
) -> tuple[str, int, str]:
    """
    Resolves a configured UI textual element into a Tkinter font tuple using exact negative pixel sizing.
    Checks loaded font configuration 'elements' mapping for either a semantic role reference
    or direct font attributes ('family', 'base_size', 'weight', 'fallback').
    Falls back gracefully to DEFAULT_FONT_CONFIG['elements'] or 'body' role.
    """
    if not _ALL_FONTS_LOADED:
        load_all_pixel_fonts()

    cfg = load_font_config()
    elements = cfg.get("elements", DEFAULT_FONT_CONFIG.get("elements", {}))
    elem_def = elements.get(element_name, DEFAULT_FONT_CONFIG.get("elements", {}).get(element_name, {}))

    # If element specifies or inherits a role, start with that role definition
    roles = cfg.get("roles", DEFAULT_FONT_CONFIG.get("roles", {}))
    role_name = elem_def.get("role", "body")
    role_def = roles.get(role_name, roles.get("body", {}))

    # Base parameters initialized from role, overridden by element specs if present
    target_family = elem_def.get("family", role_def.get("family", "m5x7"))
    fallback_family = elem_def.get("fallback", role_def.get("fallback", "Courier"))
    base_size = elem_def.get("base_size", role_def.get("base_size", 14))
    weight = weight_override if weight_override is not None else elem_def.get("weight", role_def.get("weight", "normal"))

    final_size = size_override if size_override is not None else int(base_size * scale)
    final_size = -abs(int(final_size))

    # Determine best registered font family
    if _REGISTERED_FONTS.get(target_family, False):
        resolved_family = target_family
    elif _REGISTERED_FONTS.get(fallback_family, False):
        resolved_family = fallback_family
    elif _PIXEL_FONT_REGISTERED:
        resolved_family = _PIXEL_FONT_FAMILY
    else:
        resolved_family = fallback_family if fallback_family in ("Courier", "Arial") else "Courier"

    return (resolved_family, final_size, weight)


# ============================================================================
# Semantic Font Getters
# ============================================================================

def get_title_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Large banner titles, table announcements, window titles (BoldPixels)."""
    return get_role_font("title", scale=scale, size_override=size_px, weight_override=weight)


def get_header_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Dialog section headers, mode card titles, character nameplates (BoldPixels)."""
    return get_role_font("header", scale=scale, size_override=size_px, weight_override=weight)


def get_display_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """High-impact bold rounded numerals, scores, bankroll, win/tie counts (Round9x13)."""
    return get_role_font("display", scale=scale, size_override=size_px, weight_override=weight)


def get_body_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Dialog descriptions, speech bubble typewriter text, help explanations (m5x7)."""
    return get_role_font("body", scale=scale, size_override=size_px, weight_override=weight)


def get_button_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Interactive action buttons, system buttons, dock controls (m5x7 bold)."""
    return get_role_font("button", scale=scale, size_override=size_px, weight_override=weight)


def get_digital_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Digital LCD terminal calculator readouts for Hi-Lo Trainer metrics (Volt5x5)."""
    return get_role_font("digital", scale=scale, size_override=size_px, weight_override=weight)


def get_badge_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Keyboard shortcut badges [Space], [Esc], [H] and HUD pill tags (Mini3x5)."""
    return get_role_font("badge", scale=scale, size_override=size_px, weight_override=weight)


def get_micro_font(size_px: Optional[int] = None, weight: Optional[str] = None, scale: float = 1.0) -> tuple[str, int, str]:
    """Chip stack denomination numbers and micro tags (3x5_Block_Adjusted)."""
    return get_role_font("micro", scale=scale, size_override=size_px, weight_override=weight)


def get_pixel_font(size_px: int = 16, weight: str = "normal", family: Optional[str] = None) -> tuple[str, int, str]:
    """
    Backward-compatible font getter using negative pixel sizing and normal weight by default.
    """
    if family is not None and _REGISTERED_FONTS.get(family, False):
        fam = family
    else:
        fam = _PIXEL_FONT_FAMILY
    return (fam, -abs(int(size_px)), weight)


# ============================================================================
# Procedural 9-Slice Canvas Panel (Plaques, Banners, Rails)
# ============================================================================
class CanvasPixelPanel:
    """
    Draws a procedural 9-slice pixel art plaque or panel onto a tkinter.Canvas.
    Supports notched corners, top/left and bottom/right bevels, corner brass rivets,
    and dynamic rebuild/resize for scaling transitions.
    """

    def __init__(
        self,
        canvas: tkinter.Canvas,
        x: int,
        y: int,
        width: int,
        height: int,
        bg: str = "#0c2917",
        border: str = "#06140b",
        inner_hi: str = "#1f4d30",
        inner_sh: str = "#071a0e",
        rivet_color: Optional[str] = "#d4af37",
        scale: int = 3,
        recessed: bool = True,
        anchor: str = "nw",
        tag: Optional[str] = None,
    ):
        self.canvas = canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.bg = bg
        self.border = border
        self.inner_hi = inner_hi
        self.inner_sh = inner_sh
        self.rivet_color = rivet_color
        self.scale = max(1, int(scale))
        self.recessed = recessed
        self.anchor = anchor
        self.tag = tag or f"panel_{id(self)}"

        self.photo: Optional[ImageTk.PhotoImage] = None
        self.item_id: int = 0
        self._render()

    def _render(self):
        w = max(6, self.width // self.scale)
        h = max(6, self.height // self.scale)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 1. Notched outer border (skip 4 extreme corners)
        draw.rectangle([1, 0, w - 2, h - 1], fill=self.border)
        draw.rectangle([0, 1, w - 1, h - 2], fill=self.border)

        # 2. Panel face
        draw.rectangle([1, 1, w - 2, h - 2], fill=self.bg)

        # 3. Inner bevel lines
        tl_color = self.inner_sh if self.recessed else self.inner_hi
        br_color = self.inner_hi if self.recessed else self.inner_sh

        draw.line([1, 1, w - 2, 1], fill=tl_color)
        draw.line([1, 1, 1, h - 2], fill=tl_color)
        draw.line([1, h - 2, w - 2, h - 2], fill=br_color)
        draw.line([w - 2, 1, w - 2, h - 2], fill=br_color)

        # 4. Optional 1x1 brass corner rivets
        if self.rivet_color and w >= 10 and h >= 8:
            for rx, ry in [(2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)]:
                draw.point((rx, ry), fill=self.rivet_color)

        upscaled = img.resize((w * self.scale, h * self.scale), Image.Resampling.NEAREST)
        self.photo = ImageTk.PhotoImage(upscaled, master=self.canvas)

        if self.item_id == 0:
            self.item_id = self.canvas.create_image(
                self.x, self.y, image=self.photo, anchor=self.anchor, tags=(self.tag,)
            )
        else:
            self.canvas.itemconfigure(self.item_id, image=self.photo)
            self.canvas.coords(self.item_id, self.x, self.y)

    def update_palette(
        self,
        bg: Optional[str] = None,
        border: Optional[str] = None,
        inner_hi: Optional[str] = None,
        inner_sh: Optional[str] = None,
        rivet_color: Optional[str] = None,
    ):
        """Updates palette colors and regenerates the panel PhotoImage sprite."""
        if bg is not None:
            self.bg = bg
        if border is not None:
            self.border = border
        if inner_hi is not None:
            self.inner_hi = inner_hi
        if inner_sh is not None:
            self.inner_sh = inner_sh
        if rivet_color is not None:
            self.rivet_color = rivet_color
        self._render()

    def rebuild(self, scale: Optional[float] = None):
        """Regenerates the panel PhotoImage sprite at the current or updated scale factor."""
        if scale is not None:
            self.scale = max(1, int(scale))
        self._render()

    def resize(self, x: int, y: int, width: int, height: int, scale: Optional[float] = None):
        """Updates panel position, dimensions, and scale, re-rendering the sprite."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        if scale is not None:
            self.scale = max(1, int(scale))
        self._render()


# ============================================================================
# Procedural Pixel Art Icons
# ============================================================================
_PIXEL_ICON_PIL_CACHE: dict[tuple[str, int], Image.Image] = {}


def get_pixel_icon(name: str, scale: int = 2, master: Optional[Any] = None) -> Optional[ImageTk.PhotoImage]:
    """
    Procedurally draws crisp 1x pixel art icons scaled with NEAREST filtering.
    Supported icons: 'top_hat', 'heart', 'flask', 'check', 'lock', 'mystery_bust'.
    """
    scale = max(1, int(scale))
    key = name.lower().strip()
    cache_key = (key, scale)

    if cache_key in _PIXEL_ICON_PIL_CACHE:
        img = _PIXEL_ICON_PIL_CACHE[cache_key]
        return ImageTk.PhotoImage(img, master=master)

    img: Optional[Image.Image] = None

    if key == "top_hat":
        img = Image.new("RGBA", (14, 14), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # Crown: x=4..9, y=2..8
        d.rectangle([4, 2, 9, 8], fill="#161616")
        d.line([4, 2, 4, 8], fill="#383838")
        d.line([5, 2, 9, 2], fill="#282828")
        # Gold ribbon band: y=8
        d.line([4, 8, 9, 8], fill="#ffd700")
        d.point((4, 8), fill="#ffe57f")
        d.point((9, 8), fill="#c69214")
        # Brim: y=9..10, x=1..12
        d.line([2, 9, 11, 9], fill="#2a2a2a")
        d.line([1, 10, 12, 10], fill="#161616")
        d.point((1, 9), fill="#383838")
        d.point((12, 9), fill="#383838")

    elif key == "heart":
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.line([(1, 1), (2, 1)], fill="#ff3366")
        d.line([(4, 1), (5, 1)], fill="#ff3366")
        d.rectangle([0, 2, 6, 3], fill="#ff3366")
        d.line([(1, 4), (5, 4)], fill="#ff3366")
        d.line([(2, 5), (4, 5)], fill="#e91e63")
        d.point((3, 6), fill="#c2185b")
        d.point((1, 2), fill="#ffffff")

    elif key == "flask":
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.line([(3, 0), (4, 0)], fill="#a1887f")
        d.rectangle([3, 1, 4, 2], fill="#cfd8dc")
        d.line([(2, 3), (5, 3)], fill="#90a4ae")
        d.rectangle([1, 4, 6, 6], fill="#00e676")
        d.line([(1, 4), (6, 4)], fill="#69f0ae")
        d.line([(2, 7), (5, 7)], fill="#37474f")
        d.point((2, 5), fill="#ffffff")

    elif key == "check":
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pts = [(1, 4), (2, 5), (3, 6), (4, 5), (5, 4), (6, 3), (7, 2)]
        for px, py in pts:
            d.point((px, py), fill="#5ce6b5")
            d.point((px, py + 1), fill="#004d40")

    elif key == "lock":
        img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.line([(2, 1), (5, 1)], fill="#cfd8dc")
        d.line([(2, 2), (2, 3)], fill="#90a4ae")
        d.line([(5, 2), (5, 3)], fill="#90a4ae")
        d.rectangle([1, 3, 6, 6], fill="#ffb300")
        d.line([(1, 3), (6, 3)], fill="#ffe082")
        d.line([(2, 7), (5, 7)], fill="#ff8f00")
        d.point((3, 5), fill="#3e2723")
        d.point((4, 5), fill="#3e2723")

    elif key == "mystery_bust":
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # Recessed dark silhouette bust
        d.rectangle([0, 0, 63, 63], fill="#060c08")
        # Shoulders / torso
        d.polygon([(6, 60), (18, 38), (45, 38), (57, 60)], fill="#0b1710", outline="#13271c")
        # Head oval
        d.ellipse([21, 12, 42, 34], fill="#0b1710", outline="#13271c")
        # Golden question mark
        d.rectangle([28, 18, 35, 21], fill="#8a6d1b")
        d.rectangle([32, 21, 35, 25], fill="#8a6d1b")
        d.rectangle([29, 25, 33, 27], fill="#8a6d1b")
        d.point((31, 30), fill="#8a6d1b")
        d.point((31, 31), fill="#8a6d1b")

    if img is None:
        return None

    if scale > 1:
        img = img.resize((img.width * scale, img.height * scale), Image.Resampling.NEAREST)

    _PIXEL_ICON_PIL_CACHE[cache_key] = img
    return ImageTk.PhotoImage(img, master=master)


# ============================================================================
# Transparent Canvas Text Label Proxy & Score Plaque Frame
# ============================================================================
class CanvasTextLabelProxy:
    """
    Lightweight compatibility proxy for Canvas text items rendered inside PixelPlaqueFrame and PixelDialogueFrame.
    Provides 100% transparent text rendering over 9-slice plaque sprites with 1px drop shadow,
    while satisfying Tkinter widget interface expectations (cget, config, configure, __getitem__, __setitem__, winfo_manager).
    """

    def __init__(
        self,
        canvas: tkinter.Canvas,
        text_id: int,
        shadow_id: Optional[int] = None,
        initial_text: str = "",
        initial_font: Optional[tuple] = None,
        initial_fg: str = "#ffffff",
        textvariable: Optional[tkinter.StringVar] = None,
        bg: str = "#0c2917",
        on_text_change: Optional[Callable[[str], None]] = None,
        on_manage_change: Optional[Callable[[bool], None]] = None,
        wraplength: int = 0,
    ):
        self.canvas = canvas
        self.text_id = text_id
        self.shadow_id = shadow_id
        self._text = str(initial_text)
        self._font = initial_font
        self._fg = initial_fg
        self._bg = bg
        self._textvariable = textvariable
        self._wraplength = int(wraplength)
        self.on_text_change = on_text_change
        self.on_manage_change = on_manage_change
        self._is_managed: bool = True

        if self._wraplength > 0:
            try:
                self.canvas.itemconfigure(self.text_id, width=self._wraplength)
                if self.shadow_id:
                    self.canvas.itemconfigure(self.shadow_id, width=self._wraplength)
            except Exception:
                pass

        if self._textvariable is not None:
            self.set_text(self._textvariable.get())
            try:
                self._textvariable.trace_add("write", lambda *args: self.set_text(self._textvariable.get()))
            except Exception:
                try:
                    self._textvariable.trace("w", lambda *args: self.set_text(self._textvariable.get()))
                except Exception:
                    pass

    def set_text(self, text: str):
        self._text = str(text)
        try:
            self.canvas.itemconfigure(self.text_id, text=self._text)
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, text=self._text)
        except Exception:
            pass
        if self.on_text_change:
            try:
                self.on_text_change(self._text)
            except Exception:
                pass

    def set_font(self, font: Any):
        self._font = font
        try:
            self.canvas.itemconfigure(self.text_id, font=self._font)
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, font=self._font)
        except Exception:
            pass

    def set_fg(self, fg: str):
        self._fg = str(fg)
        try:
            self.canvas.itemconfigure(self.text_id, fill=self._fg)
        except Exception:
            pass

    def configure(self, **kwargs):
        if "text" in kwargs:
            self.set_text(kwargs["text"])
        if "textvariable" in kwargs:
            self._textvariable = kwargs["textvariable"]
            if self._textvariable is not None:
                self.set_text(self._textvariable.get())
                try:
                    self._textvariable.trace_add("write", lambda *args: self.set_text(self._textvariable.get()))
                except Exception:
                    pass
        if "font" in kwargs:
            self.set_font(kwargs["font"])
        if "fg" in kwargs or "foreground" in kwargs:
            self.set_fg(kwargs.get("fg") or kwargs.get("foreground"))
        if "bg" in kwargs or "background" in kwargs:
            self._bg = kwargs.get("bg") or kwargs.get("background")
        if "wraplength" in kwargs:
            self._wraplength = int(kwargs["wraplength"])
            try:
                self.canvas.itemconfigure(self.text_id, width=self._wraplength)
                if self.shadow_id:
                    self.canvas.itemconfigure(self.shadow_id, width=self._wraplength)
            except Exception:
                pass
        if "justify" in kwargs:
            try:
                self.canvas.itemconfigure(self.text_id, justify=kwargs["justify"])
                if self.shadow_id:
                    self.canvas.itemconfigure(self.shadow_id, justify=kwargs["justify"])
            except Exception:
                pass

    config = configure

    def cget(self, key: str) -> Any:
        if key == "text":
            return self._text
        if key == "font":
            return self._font
        if key in ("fg", "foreground"):
            return self._fg
        if key in ("bg", "background"):
            return self._bg
        if key == "wraplength":
            return self._wraplength
        return ""

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    def __setitem__(self, key: str, value: Any):
        self.configure(**{key: value})

    def bind(self, sequence: str, func: Callable, add: Optional[str] = None):
        try:
            self.canvas.tag_bind(self.text_id, sequence, func, add=add)
            if self.shadow_id:
                self.canvas.tag_bind(self.shadow_id, sequence, func, add=add)
        except Exception:
            pass

    def pack(self, **kwargs):
        self._is_managed = True
        try:
            self.canvas.itemconfigure(self.text_id, state="normal")
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, state="normal")
        except Exception:
            pass
        if self.on_manage_change:
            try:
                self.on_manage_change(True)
            except Exception:
                pass

    def pack_forget(self):
        self._is_managed = False
        try:
            self.canvas.itemconfigure(self.text_id, state="hidden")
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, state="hidden")
        except Exception:
            pass
        if self.on_manage_change:
            try:
                self.on_manage_change(False)
            except Exception:
                pass

    def grid(self, **kwargs):
        self._is_managed = True
        try:
            self.canvas.itemconfigure(self.text_id, state="normal")
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, state="normal")
        except Exception:
            pass

    def grid_forget(self):
        self._is_managed = False
        try:
            self.canvas.itemconfigure(self.text_id, state="hidden")
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, state="hidden")
        except Exception:
            pass

    def grid_remove(self):
        self._is_managed = False
        try:
            self.canvas.itemconfigure(self.text_id, state="hidden")
            if self.shadow_id:
                self.canvas.itemconfigure(self.shadow_id, state="hidden")
        except Exception:
            pass

    def winfo_manager(self) -> str:
        return "pack" if self._is_managed else ""

    def winfo_ismapped(self) -> bool:
        return self._is_managed


class PixelPlaqueFrame(tkinter.Frame):
    """
    Procedural pixel-art score plaque framed with authentic brass rivets,
    double-beveled emerald face, dynamic score auto-fitting, and 100% transparent canvas text with 1px drop shadows.
    Replaces raw flat tk.Label boxes with true retro casino elegance.
    """

    def __init__(
        self,
        master: Any,
        width: int = 114,
        height: int = 60,
        title: str = "Dealer",
        score_var: Optional[tkinter.StringVar] = None,
        scale: int = 2,
        bg: str = "#0f4d26",
        relief: str = "ridge",
        borderwidth: int = 1,
        **kwargs
    ):
        super().__init__(master, bg=bg, bd=0, highlightthickness=0, **kwargs)
        self.base_width = width
        self.base_height = height
        self.scale = max(1, int(scale))
        self._bg = bg
        self._relief = relief
        self._borderwidth = borderwidth
        self._title = title
        self._score_var = score_var

        w = int(self.base_width * (self.scale / 2.0))
        h = int(self.base_height * (self.scale / 2.0))

        self.canvas = tkinter.Canvas(
            self,
            width=w,
            height=h,
            bg=bg,
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        # Procedural 9-slice panel
        self.panel = CanvasPixelPanel(
            self.canvas,
            x=w // 2,
            y=h // 2,
            width=w,
            height=h,
            bg="#0c2917",
            border="#06140b",
            inner_hi="#1f4d30",
            inner_sh="#071a0e",
            rivet_color="#d4af37",
            scale=self.scale,
            recessed=True,
            anchor="center",
            tag="plaque_panel",
        )

        # Title text item with 1px drop shadow centered
        title_font = get_element_font("hand_title", scale=self.scale / 2.0)
        ty = int(16 * (self.scale / 2.0))
        cx = w // 2
        self._title_sh_id = self.canvas.create_text(
            cx + 1, ty + 1, text=title, font=title_font, fill="#040c06", anchor="center"
        )
        self._title_id = self.canvas.create_text(
            cx, ty, text=title, font=title_font, fill="#ecc260", anchor="center"
        )
        self.title_label = CanvasTextLabelProxy(
            self.canvas,
            self._title_id,
            self._title_sh_id,
            initial_text=title,
            initial_font=title_font,
            initial_fg="#ecc260",
            bg=self._bg,
        )

        # Score text item with 1px drop shadow centered
        score_font = get_element_font("hand_score", scale=self.scale / 2.0)
        sy = int(39 * (self.scale / 2.0))
        init_score = score_var.get() if score_var is not None else ""
        self._score_sh_id = self.canvas.create_text(
            cx + 1, sy + 1, text=init_score, font=score_font, fill="#040c06", anchor="center"
        )
        self._score_id = self.canvas.create_text(
            cx, sy, text=init_score, font=score_font, fill="#ffffff", anchor="center"
        )
        self.score_label = CanvasTextLabelProxy(
            self.canvas,
            self._score_id,
            self._score_sh_id,
            initial_text=init_score,
            initial_font=score_font,
            initial_fg="#ffffff",
            textvariable=score_var,
            bg=self._bg,
            on_text_change=self._auto_fit_score,
        )
        if init_score:
            self._auto_fit_score(init_score)

        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _auto_fit_score(self, text_val: str):
        """
        Dynamically calculates and applies the optimal font size for hand scores,
        preventing long formatted strings ('10 + ?', 'Soft 17', '7 / 17', '21 (BJ)', 'H1: 18 | H2: 20')
        from grazing corner rivets (x=9 and x=105) by enforcing width <= max_inner_w (90px at scale=2).
        """
        if not text_val:
            return
        scale_ratio = self.scale / 2.0
        max_inner_w = int((self.base_width - 24) * scale_ratio)

        candidate_sizes = (32, 28, 24, 20, 16, 14, 12)
        family = "BoldPixels"
        role_font = get_element_font("hand_score", scale=scale_ratio)
        if isinstance(role_font, tuple) and len(role_font) > 0:
            family = role_font[0]

        chosen_font = None
        for base_sz in candidate_sizes:
            actual_sz = -max(8, int(base_sz * scale_ratio))
            test_font = (family, actual_sz)
            try:
                tk_f = tkfont.Font(font=test_font)
                w = tk_f.measure(str(text_val))
                if w <= max_inner_w:
                    chosen_font = test_font
                    break
            except Exception:
                continue

        if chosen_font is None:
            chosen_font = (family, -max(8, int(12 * scale_ratio)))

        try:
            self.canvas.itemconfigure(self._score_id, font=chosen_font)
            if self._score_sh_id:
                self.canvas.itemconfigure(self._score_sh_id, font=chosen_font)
            if hasattr(self, "score_label"):
                self.score_label._font = chosen_font
        except Exception:
            pass

    def _on_canvas_configure(self, event):
        cw = event.width
        ch = event.height
        if cw < 10 or ch < 10:
            return
        cx = cw // 2
        cy = ch // 2
        ty = int(16 * (self.scale / 2.0))
        sy = int(39 * (self.scale / 2.0))
        self.panel.resize(cx, cy, cw, ch, scale=self.scale)
        self.canvas.coords(self._title_sh_id, cx + 1, ty + 1)
        self.canvas.coords(self._title_id, cx, ty)
        self.canvas.coords(self._score_sh_id, cx + 1, sy + 1)
        self.canvas.coords(self._score_id, cx, sy)

    def set_scale(self, scale_factor: float):
        """Updates plaque dimensions, panel sprites, font sizes, and text positions on scale change."""
        self.scale = max(1, int(2 * scale_factor))
        w = int(self.base_width * scale_factor)
        h = int(self.base_height * scale_factor)

        self.canvas.config(width=w, height=h)
        cx = w // 2
        cy = h // 2
        ty = int(16 * scale_factor)
        sy = int(39 * scale_factor)
        self.panel.resize(cx, cy, w, h, scale=self.scale)

        self.canvas.coords(self._title_sh_id, cx + 1, ty + 1)
        self.canvas.coords(self._title_id, cx, ty)
        self.canvas.coords(self._score_sh_id, cx + 1, sy + 1)
        self.canvas.coords(self._score_id, cx, sy)

        title_font = get_element_font("hand_title", scale=scale_factor)
        self.title_label.set_font(title_font)
        self._auto_fit_score(self.score_label.cget("text"))

    def configure(self, **kwargs):
        if "relief" in kwargs:
            self._relief = kwargs.pop("relief")
        if "borderwidth" in kwargs:
            self._borderwidth = kwargs.pop("borderwidth")
        if "bd" in kwargs:
            self._borderwidth = kwargs.pop("bd")
        if "background" in kwargs or "bg" in kwargs:
            val = kwargs.get("background") or kwargs.get("bg")
            self._bg = val
            super().configure(bg=val)
            try:
                self.canvas.configure(bg=val)
                self.title_label.configure(bg=val)
                self.score_label.configure(bg=val)
            except Exception:
                pass
            return
        if kwargs:
            super().configure(**kwargs)

    config = configure

    def cget(self, key: str) -> Any:
        if key == "relief":
            return self._relief
        if key in ("borderwidth", "bd"):
            return self._borderwidth
        if key in ("background", "bg"):
            return self._bg
        return super().cget(key)

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)


class PixelDialogueFrame(tkinter.Frame):
    """
    Procedural pixel-art wooden nameplate and dialogue balloon framed with authentic brass corner rivets,
    double-beveled mahogany wood face, and transparent canvas text with 1px drop shadows.
    Replaces the 1px yellow wireframe rectangle around the dealer's name with authentic retro casino elegance.
    """

    def __init__(
        self,
        master: Any,
        scale: int = 2,
        bg: str = "#2b170e",
        title: str = "The Classic Croupier",
        speech_var: Optional[tkinter.StringVar] = None,
        nameplate_fg: str = "#ffd700",
        **kwargs
    ):
        super().__init__(master, bg="#000000", bd=0, highlightthickness=0, **kwargs)
        self.scale = max(1, int(scale))
        self._bg = bg
        self._nameplate_fg = nameplate_fg
        s = self.scale / 2.0
        self.width_px = int(180 * s)
        self.nameplate_h = int(38 * s)
        self.speech_h = int(78 * s)
        self.height_px = self.nameplate_h

        self.canvas = tkinter.Canvas(
            self,
            width=self.width_px,
            height=self.height_px,
            bg="#000000",
            bd=0,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.panel = CanvasPixelPanel(
            self.canvas,
            x=self.width_px // 2,
            y=self.height_px // 2,
            width=self.width_px,
            height=self.height_px,
            bg=self._bg,
            border="#140a05",
            inner_hi="#593322",
            inner_sh="#1a0d07",
            rivet_color="#d4af37",
            scale=self.scale,
            recessed=False,
            anchor="center",
            tag="dialogue_panel",
        )

        cx = self.width_px // 2
        ny = int(19 * s)
        title_font = get_header_font(int(12 * s))
        self._name_sh = self.canvas.create_text(
            cx + 1, ny + 1, text=title, font=title_font, fill="#0c0603", anchor="center"
        )
        self._name_id = self.canvas.create_text(
            cx, ny, text=title, font=title_font, fill=self._nameplate_fg, anchor="center"
        )
        self.nameplate_label = CanvasTextLabelProxy(
            self.canvas,
            self._name_id,
            self._name_sh,
            initial_text=title,
            initial_font=title_font,
            initial_fg=self._nameplate_fg,
            bg=self._bg,
        )

        speech_font = get_body_font(int(14 * s))
        sy = int(34 * s)
        pad_x = int(12 * s)
        wrap_w = int(156 * s)
        init_speech = speech_var.get() if speech_var is not None else ""
        self._speech_sh = self.canvas.create_text(
            pad_x + 1, sy + 1, text=init_speech, font=speech_font, fill="#0c0603",
            anchor="nw", width=wrap_w, state="hidden"
        )
        self._speech_id = self.canvas.create_text(
            pad_x, sy, text=init_speech, font=speech_font, fill="#f0f0f0",
            anchor="nw", width=wrap_w, state="hidden"
        )
        self.speech_label = CanvasTextLabelProxy(
            self.canvas,
            self._speech_id,
            self._speech_sh,
            initial_text=init_speech,
            initial_font=speech_font,
            initial_fg="#f0f0f0",
            textvariable=speech_var,
            bg=self._bg,
            on_manage_change=self._on_speech_manage_change,
        )
        self.speech_label._is_managed = False

    def _on_speech_manage_change(self, is_packed: bool):
        s = self.scale / 2.0
        self.height_px = self.speech_h if is_packed else self.nameplate_h
        self.canvas.config(height=self.height_px)
        cx = self.width_px // 2
        cy = self.height_px // 2
        ny = int(14 * s) if is_packed else int(19 * s)
        self.panel.resize(cx, cy, self.width_px, self.height_px, scale=self.scale)
        self.canvas.coords(self._name_sh, cx + 1, ny + 1)
        self.canvas.coords(self._name_id, cx, ny)

    def bind(self, sequence: str, func: Callable, add: Optional[str] = None):
        super().bind(sequence, func, add=add)
        self.canvas.bind(sequence, func, add=add)
        self.nameplate_label.bind(sequence, func, add=add)
        self.speech_label.bind(sequence, func, add=add)

    def set_scale(self, scale_factor: float):
        self.scale = max(1, int(2 * scale_factor))
        s = scale_factor
        self.width_px = int(180 * s)
        self.nameplate_h = int(38 * s)
        self.speech_h = int(78 * s)
        is_packed = self.speech_label._is_managed
        self.height_px = self.speech_h if is_packed else self.nameplate_h
        self.canvas.config(width=self.width_px, height=self.height_px)
        cx = self.width_px // 2
        cy = self.height_px // 2
        ny = int(14 * s) if is_packed else int(19 * s)
        self.panel.resize(cx, cy, self.width_px, self.height_px, scale=self.scale)
        self.canvas.coords(self._name_sh, cx + 1, ny + 1)
        self.canvas.coords(self._name_id, cx, ny)
        sy = int(34 * s)
        pad_x = int(12 * s)
        wrap_w = int(156 * s)
        self.canvas.coords(self._speech_sh, pad_x + 1, sy + 1)
        self.canvas.coords(self._speech_id, pad_x, sy)
        self.canvas.itemconfigure(self._speech_sh, width=wrap_w)
        self.canvas.itemconfigure(self._speech_id, width=wrap_w)
        self.nameplate_label.set_font(get_header_font(int(12 * s)))
        self.speech_label.set_font(get_body_font(int(14 * s)))

    def configure(self, **kwargs):
        if "background" in kwargs or "bg" in kwargs:
            val = kwargs.get("background") or kwargs.get("bg")
            self._bg = val
            self.panel.update_palette(bg=val)
            self.nameplate_label.configure(bg=val)
            self.speech_label.configure(bg=val)
        if "highlightbackground" in kwargs:
            fg_val = kwargs.get("highlightbackground")
            self._nameplate_fg = fg_val
            self.nameplate_label.configure(fg=fg_val)
        if kwargs:
            clean_kw = {k: v for k, v in kwargs.items() if k not in ("background", "bg", "highlightbackground")}
            if clean_kw:
                super().configure(**clean_kw)

    config = configure


class PixelButtonWidget(tkinter.Button):
    """
    Retro arcade pixel button widget inheriting directly from tkinter.Button.
    Supports authentic palette theming ('neutral', 'wood', 'green', 'gold', etc.),
    crisp 2px beveled borders, interactive hover states, and seamless High-DPI scaling.
    Satisfies isinstance(widget, tkinter.Button) across all testing harnesses.
    """

    def __init__(
        self,
        master: Any = None,
        theme: str = "neutral",
        scale: int = 2,
        **kwargs
    ):
        self.theme = theme
        self.scale = max(1, int(scale))
        p = PALETTE.get(theme, PALETTE["neutral"])
        bg = kwargs.pop("bg", kwargs.pop("background", p.get("bg", "#283339")))
        fg = kwargs.pop("fg", kwargs.pop("foreground", "#e6edf2"))
        abg = kwargs.pop("activebackground", p.get("hov", "#3c4a54"))
        afg = kwargs.pop("activeforeground", "#ffd700")
        bd = kwargs.pop("bd", kwargs.pop("borderwidth", 2))
        hl = kwargs.pop("highlightthickness", 1)
        hlbg = kwargs.pop("highlightbackground", p.get("sh", "#13191c"))
        relief = kwargs.pop("relief", "raised")
        cursor = kwargs.pop("cursor", "hand2")

        super().__init__(
            master,
            bg=bg,
            fg=fg,
            activebackground=abg,
            activeforeground=afg,
            bd=bd,
            highlightthickness=hl,
            highlightbackground=hlbg,
            relief=relief,
            cursor=cursor,
            **kwargs
        )
        self._norm_bg = bg
        self._norm_hl = hlbg
        self._hov_bg = p.get("hov", "#36434c")
        self._hov_hl = p.get("hi", "#d4af37")

        self.bind("<Enter>", self._on_enter, add="+")
        self.bind("<Leave>", self._on_leave, add="+")
        self.bind("<ButtonPress-1>", self._on_press, add="+")
        self.bind("<ButtonRelease-1>", self._on_release, add="+")

    def _on_enter(self, _event):
        try:
            self.config(bg=self._hov_bg, highlightbackground=self._hov_hl)
        except Exception:
            pass

    def _on_leave(self, _event):
        try:
            self.config(bg=self._norm_bg, highlightbackground=self._norm_hl)
        except Exception:
            pass

    def _on_press(self, _event):
        try:
            self.config(relief="sunken")
        except Exception:
            pass

    def _on_release(self, _event):
        try:
            self.config(relief="raised")
        except Exception:
            pass

    def set_scale(self, scale_factor: float):
        self.scale = max(1, int(2 * scale_factor))
        try:
            f = get_element_font("top_bar_button", scale=scale_factor)
            self.config(font=f)
        except Exception:
            pass


# ============================================================================
# Interactive Procedural Pixel Art Button
# ============================================================================
class CanvasPixelButton:
    """
    A pure-Canvas pixel art button with notched corners, hover highlights,
    physical press physics (-scale vertical shift on press), drop shadow text,
    recessed disabled states, and full Tkinter widget compatibility shims.
    """

    def __init__(
        self,
        canvas: tkinter.Canvas,
        x: int,
        y: int,
        width: int,
        height: int,
        text: str,
        command: Optional[Callable[[], None]] = None,
        theme: str = "green",
        font: Optional[tuple[str, int, str]] = None,
        text_color: str = "#f4efe6",
        scale: int = 3,
        enabled: bool = True,
        disabled_text_color: Optional[str] = None,
        group_tag: Optional[str] = None,
        master: Optional[tkinter.Widget] = None,
    ):
        self.canvas = canvas
        self.master = master if master is not None else canvas
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.text = text
        self.command = command
        self.theme = theme
        self.scale = max(1, int(scale))
        self.enabled = enabled
        self.disabled_text_color = disabled_text_color
        self.font = font or get_pixel_font(size_px=14 * self.scale // 2, weight="normal")
        self.text_color = text_color
        self.group_tag = group_tag

        self.tag = f"pxbtn_{id(self)}"
        self.tags = (self.tag, group_tag) if group_tag else (self.tag,)

        self.sprites: dict[str, ImageTk.PhotoImage] = {}
        self._is_hovered = False
        self._is_pressed = False

        self.bg_id: int = 0
        self.shadow_text_id: int = 0
        self.text_id: int = 0
        self._grid_info: dict = {}
        self._last_grid_info: dict = {}
        self._is_mapped: bool = True

        self._build_sprites()
        self._create_canvas_items()
        self._bind_events()
        self.set_enabled(self.enabled)

    def _make_sprite(self, bg: str, hi: str, sh: str, pressed: bool = False, disabled: bool = False) -> ImageTk.PhotoImage:
        w = max(6, self.width // self.scale)
        h = max(6, self.height // self.scale)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        border = "#140a05" if disabled else "#0e1711"
        y_off = 1 if pressed else 0

        # Outer notched border
        draw.rectangle([1, y_off, w - 2, h - 1], fill=border)
        draw.rectangle([0, 1 + y_off, w - 1, h - 2], fill=border)

        # Button face
        draw.rectangle([1, 1 + y_off, w - 2, h - 2], fill=bg)

        if disabled:
            # Recessed button slot carved into mahogany rail:
            # Dark inner shadow at Top and Left (hi = #120906)
            draw.line([1, 1, w - 2, 1], fill=hi)
            draw.line([1, 1, 1, h - 2], fill=hi)
            # Subtle wood rim highlight at Bottom and Right (sh = #382117)
            draw.line([1, h - 2, w - 2, h - 2], fill=sh)
            draw.line([w - 2, 1, w - 2, h - 2], fill=sh)
        elif not pressed:
            # Top & Left bright highlight bevel
            draw.line([1, 1, w - 2, 1], fill=hi)
            draw.line([1, 1, 1, h - 3], fill=hi)
            # Bottom & Right shadow bevel (2px thick at bottom)
            draw.line([1, h - 2, w - 2, h - 2], fill=sh)
            draw.line([1, h - 3, w - 2, h - 3], fill=sh)
            draw.line([w - 2, 2, w - 2, h - 2], fill=sh)
        else:
            # Recessed inner top shadow
            draw.line([1, 1 + y_off, w - 2, 1 + y_off], fill=sh)

        upscaled = img.resize((w * self.scale, h * self.scale), Image.Resampling.NEAREST)
        return ImageTk.PhotoImage(upscaled, master=self.canvas)

    def _build_sprites(self):
        colors = PALETTE.get(self.theme, PALETTE["neutral"])
        dis = PALETTE["disabled"]
        self.sprites = {
            "normal":   self._make_sprite(colors["bg"],  colors["hi"], colors["sh"], pressed=False),
            "hover":    self._make_sprite(colors["hov"], colors["hi"], colors["sh"], pressed=False),
            "pressed":  self._make_sprite(colors["bg"],  colors["hi"], colors["sh"], pressed=True),
            "disabled": self._make_sprite(dis["bg"],     dis["hi"],    dis["sh"],    pressed=False, disabled=True),
        }

    @property
    def _shadow_offset(self) -> int:
        return 2 if self.scale >= 2 else 1

    def _create_canvas_items(self):
        so = self._shadow_offset
        self.bg_id = self.canvas.create_image(
            self.x, self.y, image=self.sprites["normal"], anchor="center", tags=self.tags
        )
        self.shadow_text_id = self.canvas.create_text(
            self.x + so, self.y + so, text=self.text, font=self.font, fill="#0e1410", anchor="center", tags=self.tags
        )
        self.text_id = self.canvas.create_text(
            self.x, self.y - 1, text=self.text, font=self.font, fill=self.text_color, anchor="center", tags=self.tags
        )

    def _bind_events(self):
        self.canvas.tag_bind(self.tag, "<Enter>", self._on_enter)
        self.canvas.tag_bind(self.tag, "<Leave>", self._on_leave)
        self.canvas.tag_bind(self.tag, "<ButtonPress-1>", self._on_press)
        self.canvas.tag_bind(self.tag, "<ButtonRelease-1>", self._on_release)

    def _update_visuals(self):
        so = self._shadow_offset
        if not self.enabled:
            self.canvas.itemconfigure(self.bg_id, image=self.sprites["disabled"])
            dis_color = self.disabled_text_color or PALETTE["disabled"]["text"]
            self.canvas.itemconfigure(self.text_id, fill=dis_color)
            shadow_color = "#0a0503" if self.disabled_text_color else "#0e1410"
            self.canvas.itemconfigure(self.shadow_text_id, fill=shadow_color)
            self.canvas.coords(self.text_id, self.x, self.y + 1)
            self.canvas.coords(self.shadow_text_id, self.x + so, self.y + 1 + so)
            return

        self.canvas.itemconfigure(self.text_id, fill=self.text_color)
        self.canvas.itemconfigure(self.shadow_text_id, fill="#0e1410")
        if self._is_pressed:
            self.canvas.itemconfigure(self.bg_id, image=self.sprites["pressed"])
            # Shift text down by 1 pixel unit (scale) when pressed
            self.canvas.coords(self.text_id, self.x, self.y - 1 + self.scale)
            self.canvas.coords(self.shadow_text_id, self.x + so, self.y - 1 + self.scale + so)
        elif self._is_hovered:
            self.canvas.itemconfigure(self.bg_id, image=self.sprites["hover"])
            self.canvas.coords(self.text_id, self.x, self.y - 1)
            self.canvas.coords(self.shadow_text_id, self.x + so, self.y - 1 + so)
        else:
            self.canvas.itemconfigure(self.bg_id, image=self.sprites["normal"])
            self.canvas.coords(self.text_id, self.x, self.y - 1)
            self.canvas.coords(self.shadow_text_id, self.x + so, self.y - 1 + so)

    def _on_enter(self, _event):
        if self.enabled:
            self._is_hovered = True
            try:
                self.canvas.config(cursor="hand2")
            except Exception:
                pass
            self._update_visuals()

    def _on_leave(self, _event):
        if self.enabled:
            self._is_hovered = False
            self._is_pressed = False
            try:
                self.canvas.config(cursor="")
            except Exception:
                pass
            self._update_visuals()

    def _on_press(self, _event):
        if self.enabled:
            self._is_pressed = True
            self._update_visuals()

    def _on_release(self, _event):
        if self.enabled and self._is_pressed:
            self._is_pressed = False
            self._update_visuals()
            if self._is_hovered and callable(self.command):
                self.command()

    def set_enabled(self, enabled: bool):
        """Sets active or recessed disabled state."""
        self.enabled = bool(enabled)
        if not self.enabled:
            self._is_hovered = False
            self._is_pressed = False
        self._update_visuals()

    def set_disabled_text_color(self, color: Optional[str]):
        """Sets or clears the custom text color override for the disabled state."""
        self.disabled_text_color = color
        if not self.enabled:
            self._update_visuals()

    def set_text(self, new_text: str):
        """Updates button display text."""
        self.text = str(new_text)
        self.canvas.itemconfigure(self.text_id, text=self.text)
        self.canvas.itemconfigure(self.shadow_text_id, text=self.text)

    def rebuild(self, scale: Optional[float] = None):
        """Regenerates button sprites at updated scale factor."""
        if scale is not None:
            self.scale = max(1, int(scale))
        self._build_sprites()
        self._update_visuals()

    def resize(self, x: int, y: int, width: int, height: int, scale: Optional[float] = None):
        """Relocates and resizes the button."""
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        if scale is not None:
            self.scale = max(1, int(scale))
        self._build_sprites()
        self.canvas.coords(self.bg_id, self.x, self.y)
        self.canvas.coords(self.text_id, self.x, self.y - 1)
        self.canvas.coords(self.shadow_text_id, self.x + 1, self.y + 1)
        self._update_visuals()

    # ------------------------------------------------------------------------
    # Tkinter Widget Compatibility Shims for Test & Game Compatibility
    # ------------------------------------------------------------------------
    def __getitem__(self, key: str) -> Any:
        if key == "state":
            return "normal" if self.enabled else "disabled"
        if key == "text":
            return self.text
        if key == "font":
            return self.font
        return ""

    def cget(self, key: str) -> Any:
        return self[key]

    def configure(self, **kwargs):
        if "state" in kwargs:
            self.set_enabled(kwargs["state"] == "normal")
        if "text" in kwargs:
            self.set_text(kwargs["text"])
        if "command" in kwargs:
            self.command = kwargs["command"]
        if "font" in kwargs:
            self.font = kwargs["font"]
            self.canvas.itemconfigure(self.text_id, font=self.font)
            self.canvas.itemconfigure(self.shadow_text_id, font=self.font)
        if "theme" in kwargs:
            self.theme = kwargs["theme"]
            self._build_sprites()
            self._update_visuals()
        if "disabled_text_color" in kwargs:
            self.disabled_text_color = kwargs["disabled_text_color"]
            if not self.enabled:
                self._update_visuals()

    config = configure

    def invoke(self):
        """Simulates button activation (used by automated tests)."""
        if self.enabled and callable(self.command):
            return self.command()

    def grid(self, **kwargs):
        if kwargs:
            self._last_grid_info.update(kwargs)
        self._grid_info = dict(self._last_grid_info)
        self._is_mapped = True
        try:
            self.canvas.itemconfigure(self.tag, state="normal")
        except Exception:
            pass

    def grid_configure(self, **kwargs):
        self._last_grid_info.update(kwargs)
        if self._is_mapped:
            self._grid_info.update(kwargs)

    def grid_remove(self):
        self._grid_info = {}
        self._is_mapped = False
        try:
            self.canvas.itemconfigure(self.tag, state="hidden")
        except Exception:
            pass

    def grid_forget(self):
        self._grid_info = {}
        self._last_grid_info = {}
        self._is_mapped = False
        try:
            self.canvas.itemconfigure(self.tag, state="hidden")
        except Exception:
            pass

    def grid_info(self) -> dict:
        return dict(self._grid_info)

    def pack(self, **kwargs):
        self._grid_info = dict(kwargs)
        self._is_mapped = True
        try:
            self.canvas.itemconfigure(self.tag, state="normal")
        except Exception:
            pass

    def pack_configure(self, **kwargs):
        self._grid_info.update(kwargs)

    def pack_forget(self):
        self.grid_remove()

    def pack_info(self) -> dict:
        return dict(self._grid_info)

    def winfo_ismapped(self) -> bool:
        return self._is_mapped



class ChipButtonProxy:
    """Lightweight compatibility proxy for legacy tests that inspect app.chip_buttons."""

    def __init__(self, app: Any, amount: int):
        self.app = app
        self.amount = amount
        self.text = f"${amount}"
        self.state = "normal"

    def configure(self, **kwargs):
        if "state" in kwargs:
            self.state = kwargs["state"]
        if "text" in kwargs:
            self.text = kwargs["text"]

    config = configure

    def cget(self, key: str) -> Any:
        if key == "state":
            return self.state
        if key == "text":
            return self.text
        return None

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    def invoke(self):
        if self.state == "normal" and hasattr(self.app, "_add_chip_bet"):
            self.app._add_chip_bet(self.amount)

    def pack(self, **kwargs):
        pass

    def pack_configure(self, **kwargs):
        pass

    def pack_forget(self):
        pass

    def pack_info(self) -> dict:
        return {}

    def grid(self, **kwargs):
        pass

    def grid_configure(self, **kwargs):
        pass

    def grid_remove(self):
        pass

    def grid_forget(self):
        pass

    def grid_info(self) -> dict:
        return {}

