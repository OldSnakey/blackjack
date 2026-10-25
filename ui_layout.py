"""
UI Layout & Coordinate Configuration Engine for Blackjack.

Provides:
- Centralized coordinate hierarchy mapping for 2.5D canvas presentation components:
  ChipVisualizer, SoulMeterCanvas, HauntedAltarCanvas, DealerStageCanvas, and MahoganyRailCanvas.
- Hot-reloading from assets/ui_config.json on disk modification.
- Robust, zero-crash default fallbacks if configuration files are missing or incomplete.
- Origin-offset mathematical resolvers and grid placement options for Tkinter widgets.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple

from config import UI_CONFIG_FILE

DEFAULT_UI_CONFIG: dict[str, Any] = {
    "version": "1.0",
    "theme_colors": {
        "bankroll_text": "#ffd700",
        "table_background": "#073512",
        "panel_background": "#0c2917",
        "gold_trim": "#d4af37",
        "white_text": "#ffffff",
        "status_yellow": "#ffeb3b",
        "shoe_teal": "#80cbc4",
        "insurance_bg": "#0c2917",
        "insurance_text": "#ffd700",
        "insurance_btn_take_bg": "#ff9800",
        "insurance_btn_take_fg": "#111111",
        "insurance_btn_take_active_bg": "#ffa726",
        "insurance_btn_take_active_fg": "#000000",
        "insurance_btn_decline_bg": "#37474f",
        "insurance_btn_decline_fg": "#ffffff",
        "insurance_btn_decline_active_bg": "#455a64",
        "insurance_btn_decline_active_fg": "#ffffff",
    },
    "root_layout": {
        "padding": {"padx": 10, "pady": 10},
        "column_weights": [{"column": 0, "weight": 1}],
        "row_weights": [{"row": 3, "weight": 1}],
        "rows": {
            "top_bar": {"row": 0, "column": 0, "columnspan": 3, "pady": [0, 6]},
            "dealer_stage": {"row": 1, "column": 0, "columnspan": 3, "sticky": "ew"},
            "horizon_rail": {"row": 2, "column": 0, "columnspan": 3, "sticky": "ew"},
            "card_table": {"row": 3, "column": 0, "columnspan": 3, "sticky": "nsew"},
            "mahogany_rail": {"row": 4, "column": 0, "columnspan": 3, "sticky": "ew", "pady": [2, 6]},
            "insurance_prompt": {"row": 5, "column": 0, "columnspan": 3, "pady": [6, 10]},
            "blessings_tray": {"row": 7, "column": 0, "columnspan": 3, "pady": [0, 4]},
        },
    },
    "top_bar": {
        "grid_placement": {
            "row": 0,
            "column": 0,
            "columnspan": 3,
            "pady": [0, 6],
        },
        "button_ipady": 2,
        "help_button_ipady_2x": 2,
        "stats_spacing_x": 15,
        "bankroll_banner": {
            "pady": [2, 2],
            "font_element": "bankroll_label",
        },
        "elements": {
            "dealer_wins_title": {"row": 0, "column": 0},
            "dealer_wins_value": {"row": 0, "column": 1, "padx": [0, 15]},
            "player_wins_title": {"row": 0, "column": 2},
            "player_wins_value": {"row": 0, "column": 3, "padx": [0, 15]},
            "ties_title": {"row": 0, "column": 4},
            "ties_value": {"row": 0, "column": 5},
            "shoe_label": {"row": 0, "column": 6, "padx": [12, 0]},
            "spacer": {"column": 7, "weight": 1},
            "sound_button": {"row": 0, "column": 8, "padx": [15, 0]},
            "help_button": {"row": 0, "column": 9, "padx": [10, 0]},
            "scale_button": {"row": 0, "column": 11, "padx": [6, 0]},
            "fullscreen_button": {"row": 0, "column": 12, "padx": [6, 0]},
            "settings_button": {"row": 0, "column": 13, "padx": [6, 0]},
            "bankroll_label": {"row": 1, "column": 0, "columnspan": 14, "pady": [2, 2]},
            "result_label": {"row": 2, "column": 0, "columnspan": 14, "pady": [2, 4]},
        },
    },
    "insurance_prompt": {
        "grid_placement": {
            "row": 5,
            "column": 0,
            "columnspan": 3,
            "pady": [6, 10],
        },
        "frame": {
            "background": "#0c2917",
            "highlightbackground": "#d4af37",
            "highlightthickness": 1,
            "relief": "ridge",
            "borderwidth": 2,
            "padx": 16,
            "pady": 8,
        },
        "label": {
            "font_element": "insurance_prompt_label",
            "background": "#0c2917",
            "foreground": "#ffd700",
            "padx": [0, 16],
        },
        "take_button": {
            "font_element": "insurance_prompt_button",
            "background": "#ff9800",
            "foreground": "#111111",
            "activebackground": "#ffa726",
            "activeforeground": "#000000",
            "relief": "raised",
            "borderwidth": 2,
            "cursor": "hand2",
            "padx": 14,
            "pady": 5,
        },
        "decline_button": {
            "font_element": "insurance_prompt_button",
            "background": "#37474f",
            "foreground": "#ffffff",
            "activebackground": "#455a64",
            "activeforeground": "#ffffff",
            "relief": "raised",
            "borderwidth": 2,
            "cursor": "hand2",
            "padx": 14,
            "pady": 5,
            "width": 10,
        },
    },
    "chip_visualizer": {
        "base_width": 200,
        "base_height": 148,
        "grid_placement": {
            "row": 1,
            "column": 2,
            "rowspan": 2,
            "padx": [10, 5],
            "pady": [0, 6],
            "sticky": "se",
        },
        "content_offset": {"x": 0, "y": 8},
        "betting_spot": {
            "origin": {"x_ratio": 0.5, "y_ratio": 0.24},
            "outer_oval": {"rx": 72, "ry": 22},
            "inner_oval": {"rx": 65, "ry": 18},
            "watermark": {"offset_x": 0, "offset_y": 1},
            "bet_badge": {"offset_x": 0, "offset_y": -34},
        },
        "tray_divider": {
            "y_ratio": 0.46,
            "margin_x": 10,
        },
        "bankroll_piles": {
            "origin": {"x_ratio": 0.5, "y_ratio": 0.66},
            "margin_x": 24,
            "chip_vertical_step": 3,
            "denomination_label": {"offset_x": 0, "offset_y": 15},
            "hitbox": {"pad_x": 4, "top_offset": -18, "bottom_offset": 7},
        },
        "bankroll_badge": {
            "origin": {"x_ratio": 0.5, "y_ratio": 0.90},
        },
        "chips": {
            "compact": {"rx": 12, "ry": 6, "depth": 3, "stripe_x": 6},
            "standard": {"rx": 14, "ry": 7, "depth": 4, "stripe_x": 8},
        },
        "animations": {
            "payout_offset": {"x": 20, "y": -20},
            "floating_text_offset_y": -16,
        },
    },
    "soul_meter": {
        "base_width": 250,
        "base_height": 135,
        "grid_placement": {
            "row": 1,
            "column": 2,
            "padx": [10, 5],
            "pady": [2, 2],
            "sticky": "e",
        },
        "content_offset": {"x": 0, "y": 0},
        "header": {"origin": {"x_ratio": 0.5, "y_offset": 16}},
        "progress_bar": {
            "margin_x": 18,
            "top_y": 42,
            "bottom_y": 62,
            "pointer": {"width": 5, "height": 6},
            "milestone_label_offset_y": -12,
            "bound_label_offset_y": 10,
        },
        "status_text": {"origin": {"x_ratio": 0.5, "y_offset": 90}},
        "hint_text": {"origin": {"x_ratio": 0.5, "y_offset": 112}},
    },
    "haunted_altar": {
        "base_width": 260,
        "base_height": 135,
        "candles": {
            "origin_y": 28,
            "start_x": 26,
            "step_x": 52,
            "glow": {
                "outer": {"rx": 24, "ry_top": -6, "ry_bottom": 30},
                "mid": {"rx": 16, "ry_top": 0, "ry_bottom": 24},
                "inner": {"rx": 8, "ry_top": 6, "ry_bottom": 18},
            },
        },
        "gravestones": {
            "origin_y": 80,
            "x_positions": [36, 83, 130, 177, 224],
        },
    },
    "dealer_stage": {
        "default_height": 220,
        "stage_canvas": {"fill": "both", "expand": True},
        "pumpkin": {"side": "left", "padx": [0, 6], "pady": 2},
        "avatar": {"side": "left", "padx": 2, "pady": 2},
        "dialogue_frame": {
            "anchor": "se",
            "offset_x": -76,
            "offset_y": -90,
            "padx": 6,
            "pady": 4,
        },
        "nameplate": {"anchor": "w"},
        "speech_label": {"anchor": "w", "pady": [2, 0], "padx": 6, "wraplength": 270},
        "speech_bubble": {
            "anchor_offset": {"x": -76, "y": -90},
            "tail_top_offset": {"x": -4, "y": -44},
            "tail_mid_offset": {"x": -4, "y": -30},
            "tail_target_offset": {"x": -44, "y": -127},
        },
    },
    "card_table": {
        "frame": {"relief": "sunken", "borderwidth": 2, "padx": 8, "pady": 3},
        "column_weights": [
            {"column": 1, "weight": 1},
            {"column": 2, "weight": 0},
        ],
        "row_configs": [
            {"row": 0, "weight": 1, "minsize": 118},
            {"row": 1, "weight": 1, "minsize": 140},
            {"row": 2, "weight": 0, "minsize": 58},
        ],
        "dealer_header": {"row": 0, "column": 0, "sticky": "nw", "padx": [14, 6], "pady": [4, 0]},
        "dealer_cards": {"row": 0, "column": 1, "padx": 10, "pady": 1},
        "player_header": {"row": 1, "column": 0, "sticky": "nw", "padx": [14, 6], "pady": [4, 0]},
        "player_cards": {"row": 1, "column": 1, "padx": 10, "pady": [6, 1]},
        "accessories": {"row": 0, "column": 2, "sticky": "ne", "padx": 0, "pady": 0},
        "haunted_altar": {"side": "top", "pady": 2},
    },
    "mahogany_rail": {
        "default_height": 72,
        "trim_line_y": 0,
        "accent_line_y": 2,
        "grid_placement": {"row": 4, "column": 0, "columnspan": 3, "sticky": "ew", "pady": [2, 6]},
        "dock": {
            "btn_height": 36,
            "scale_2x_height_multiplier": 1.25,
            "dock_gap": 12,
            "side_margin": 24,
            "bet_buttons": {
                "clear_bet": {"width": 136},
                "all_in": {"width": 96},
                "deal_hand": {"width": 144},
                "rebuy": {"width": 124},
            },
            "play_buttons": {
                "hit": {"width": 96},
                "stand": {"width": 96},
                "double": {"width": 96},
                "split": {"width": 96},
                "surrender": {"width": 118},
            },
            "anchor_buttons": {
                "new_game": {"width": 118},
                "miracle": {"width": 100},
            },
            "cursed_stakes": {
                "grid_placement": {"row": 0, "column": 8, "padx": [6, 8], "pady": 3, "sticky": "e"},
            },
        },
    },
    "cards_layout": {
        "dealer_card_padx": 2,
        "split_hand_gap": 10,
        "container_pad": {"padx": 6, "pady": 4},
        "multi_card_compress_threshold": 4,
        "compression_factor_single": 0.85,
        "compression_factor_split": 0.70,
        "min_overlap": 12,
    },
    "blessings_tray": {
        "grid_placement": {"row": 7, "column": 0, "columnspan": 3, "pady": [0, 4]},
        "header_padx": [0, 4],
        "relic_item_padx": 3,
        "icon_padx": 2,
    },
    "table_felt": {
        "shoe_tray": {
            "width": 82,
            "height": 28,
            "offset_right": 12,
            "offset_top": 2,
            "plaque": {
                "height": 20,
                "offset_y": 3,
                "background": "transparent",
                "border": "transparent",
                "inner_border": "transparent",
                "text_color": "#ffd700",
                "cut_border": "#ff1744",
                "cut_text_color": "#ff5252",
                "font_element": "shoe_counter",
            },
        },
    },
    "image_scaling": {
        "cards": {
            "mode": "pixel_perfect",
            "exact_1x_passthrough": True,
            "integer_resample": "NEAREST",
            "fractional_resample": "LANCZOS",
        },
        "dealer": {
            "mode": "pixel_perfect",
            "exact_1x_passthrough": True,
            "integer_resample": "NEAREST",
            "fractional_resample": "LANCZOS",
        },
        "haunted_accessories": {
            "mode": "pixel_perfect",
            "exact_1x_passthrough": True,
            "integer_resample": "NEAREST",
            "fractional_resample": "LANCZOS",
        },
        "relics": {
            "mode": "pixel_perfect",
            "exact_1x_passthrough": True,
            "integer_resample": "NEAREST",
            "fractional_resample": "LANCZOS",
        },
        "ui_icons": {
            "mode": "pixel_perfect",
            "exact_1x_passthrough": True,
            "integer_resample": "NEAREST",
            "fractional_resample": "LANCZOS",
        },
    },
}

_CACHED_UI_CONFIG: dict[str, Any] = {}
_LAST_CONFIG_MTIME: float = 0.0


def load_ui_config(force_reload: bool = False) -> dict[str, Any]:
    """
    Loads and caches ui_config.json from disk, automatically reloading whenever
    the file modification timestamp changes. Falls back safely to DEFAULT_UI_CONFIG.
    """
    global _CACHED_UI_CONFIG, _LAST_CONFIG_MTIME
    cfg_file = Path(UI_CONFIG_FILE)
    if not cfg_file.exists():
        return DEFAULT_UI_CONFIG

    try:
        current_mtime = cfg_file.stat().st_mtime
        if force_reload or current_mtime != _LAST_CONFIG_MTIME or not _CACHED_UI_CONFIG:
            with open(cfg_file, "r", encoding="utf-8") as f:
                _CACHED_UI_CONFIG = json.load(f)
            _LAST_CONFIG_MTIME = current_mtime
    except Exception:
        if not _CACHED_UI_CONFIG:
            return DEFAULT_UI_CONFIG

    return _CACHED_UI_CONFIG


def reload_ui_config() -> dict[str, Any]:
    """Explicitly forces a fresh reload of ui_config.json from disk."""
    return load_ui_config(force_reload=True)


def get_ui_layout(canvas_key: str, group_key: str | None = None) -> dict[str, Any]:
    """
    Retrieves the layout configuration dictionary for a canvas and optional group.
    Falls back gracefully to DEFAULT_UI_CONFIG if keys are absent.
    """
    cfg = load_ui_config()
    canvas_dict = cfg.get(canvas_key, DEFAULT_UI_CONFIG.get(canvas_key, {}))
    if group_key is None:
        return canvas_dict
    default_group = DEFAULT_UI_CONFIG.get(canvas_key, {}).get(group_key, {})
    return canvas_dict.get(group_key, default_group)


def get_grid_options(component_key: str, element_key: str | None = None) -> dict[str, Any]:
    """
    Returns keyword arguments formatted for tkinter widget .grid(**options).
    Converts list paddings to tuples.
    If element_key is provided, looks under component's 'elements' or as a sub-dictionary.
    """
    comp_dict = get_ui_layout(component_key)
    if element_key is not None:
        raw_opts = comp_dict.get("elements", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("rows", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("dock", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get(element_key, {})
        if isinstance(raw_opts, dict) and "grid_placement" in raw_opts:
            raw_opts = raw_opts["grid_placement"]
    else:
        raw_opts = comp_dict.get("grid_placement")
        if raw_opts is None and any(k in comp_dict for k in ("row", "column", "columnspan")):
            raw_opts = comp_dict

    if not raw_opts or not isinstance(raw_opts, dict):
        return {}
    opts = dict(raw_opts)
    if "padx" in opts and isinstance(opts["padx"], list):
        opts["padx"] = tuple(opts["padx"])
    if "pady" in opts and isinstance(opts["pady"], list):
        opts["pady"] = tuple(opts["pady"])
    return opts


def get_pack_options(component_key: str, element_key: str | None = None, scale: float = 1.0) -> dict[str, Any]:
    """
    Returns keyword arguments formatted for tkinter widget .pack(**options).
    Scales padding by scale factor.
    """
    comp_dict = get_ui_layout(component_key)
    if element_key is not None:
        raw_opts = comp_dict.get("elements", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("rows", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("dock", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get(element_key, {})
        if isinstance(raw_opts, dict) and "pack_placement" in raw_opts:
            raw_opts = raw_opts["pack_placement"]
    else:
        raw_opts = comp_dict.get("pack_placement")
        if raw_opts is None and any(k in comp_dict for k in ("side", "anchor", "expand", "fill")):
            raw_opts = comp_dict

    if not raw_opts or not isinstance(raw_opts, dict):
        return {}

    valid_keys = {"side", "anchor", "expand", "fill", "padx", "pady", "ipadx", "ipady"}
    opts = {}
    for k, v in raw_opts.items():
        if k in valid_keys:
            if k in ("padx", "pady", "ipadx", "ipady"):
                if isinstance(v, (int, float)):
                    opts[k] = int(v * scale)
                elif isinstance(v, (list, tuple)):
                    opts[k] = tuple(int(x * scale) for x in v)
                else:
                    opts[k] = v
            else:
                opts[k] = v
    return opts


def get_table_layout() -> dict[str, Any]:
    """Retrieves row and column configurations, plaque placements, and frame styles for the card table."""
    return get_ui_layout("card_table")


def get_rail_button_layout() -> dict[str, Any]:
    """Retrieves dimensions, gaps, side margins, and button configurations for the mahogany rail dock."""
    return get_ui_layout("mahogany_rail", "dock")


def get_card_layout() -> dict[str, Any]:
    """Retrieves card layout rules, dynamic overlap compression factors, and split margins."""
    return get_ui_layout("cards_layout")



def resolve_origin(
    group_cfg: dict[str, Any],
    width: int,
    height: int,
    scale_x: float = 1.0,
    scale_y: float = 1.0,
    content_offset: Tuple[int, int] = (0, 0),
) -> Tuple[int, int]:
    """
    Calculates origin (x, y) coordinates for a group of elements.
    Supports normalized ratios (x_ratio, y_ratio) or absolute/offset coordinates,
    with an optional parent content_offset applied.
    """
    origin = group_cfg.get("origin", {})
    if "x_ratio" in origin:
        ox = int(width * origin["x_ratio"])
    elif "x_offset" in origin:
        ox = int(origin["x_offset"] * scale_x)
    else:
        ox = origin.get("x", width // 2)

    if "y_ratio" in origin:
        oy = int(height * origin["y_ratio"])
    elif "y_offset" in origin:
        oy = int(origin["y_offset"] * scale_y)
    else:
        oy = origin.get("y", height // 2)

    cox, coy = content_offset
    return ox + int(cox * scale_x), oy + int(coy * scale_y)


def resolve_offset(
    elem_cfg: dict[str, Any], origin: Tuple[int, int], scale_x: float = 1.0, scale_y: float = 1.0
) -> Tuple[int, int]:
    """
    Applies scaled delta offsets (offset_x, offset_y) to a parent origin (ox, oy).
    """
    ox, oy = origin
    dx = int(elem_cfg.get("offset_x", 0) * scale_x)
    dy = int(elem_cfg.get("offset_y", 0) * scale_y)
    return ox + dx, oy + dy


def get_theme_color(color_key: str, default: str = "") -> str:
    """
    Returns a configured hex color from ui_config.json ['theme_colors'], falling back to default.
    """
    cfg = load_ui_config()
    colors = cfg.get("theme_colors", DEFAULT_UI_CONFIG.get("theme_colors", {}))
    return colors.get(color_key, default)


def get_widget_style(component_key: str, element_key: str, scale: float = 1.0) -> dict[str, Any]:
    """
    Resolves a complete style dictionary for a Tkinter widget (font, colors, borders, and scaled paddings).
    """
    cfg = get_ui_layout(component_key, element_key)
    if not cfg:
        return {}

    style = dict(cfg)
    if "font_element" in style:
        font_elem = style.pop("font_element")
        try:
            from pixel_ui import get_element_font
            scale_ratio = 2.0 if scale > 1.5 else 1.0
            style["font"] = get_element_font(font_elem, scale=scale_ratio)
        except Exception:
            pass

    if "padx" in style:
        px = style["padx"]
        if isinstance(px, (int, float)):
            style["padx"] = int(px * scale)
        elif isinstance(px, (list, tuple)):
            style["padx"] = tuple(int(p * scale) for p in px)

    if "pady" in style:
        py = style["pady"]
        if isinstance(py, (int, float)):
            style["pady"] = int(py * scale)
        elif isinstance(py, (list, tuple)):
            style["pady"] = tuple(int(p * scale) for p in py)

    return style


def apply_style(widget: Any, component_key: str, element_key: str, scale: float = 1.0) -> dict[str, Any]:
    """
    Applies the configuration-derived styling directly to a Tkinter widget.
    Filters options supported by widget.configure() to prevent runtime errors.
    Returns the applied style dictionary.
    """
    style = get_widget_style(component_key, element_key, scale=scale)
    if not style or not hasattr(widget, "configure"):
        return style

    configure_opts = {}
    for k, v in style.items():
        try:
            if hasattr(widget, "keys") and k in widget.keys():
                configure_opts[k] = v
            elif not hasattr(widget, "keys"):
                configure_opts[k] = v
        except Exception:
            configure_opts[k] = v

    try:
        widget.configure(**configure_opts)
    except Exception:
        for k, v in configure_opts.items():
            try:
                widget.configure(**{k: v})
            except Exception:
                pass

    return style


def get_image_scaling_config(element_type: str = "cards") -> dict[str, Any]:
    """
    Returns image scaling and resampling configurations for the specified element type.
    Falls back to element defaults or DEFAULT_UI_CONFIG defaults.
    """
    cfg = load_ui_config()
    img_cfg = cfg.get("image_scaling", DEFAULT_UI_CONFIG.get("image_scaling", {}))
    defaults = DEFAULT_UI_CONFIG.get("image_scaling", {}).get(element_type, {
        "mode": "pixel_perfect",
        "exact_1x_passthrough": True,
        "integer_resample": "NEAREST",
        "fractional_resample": "LANCZOS",
    })
    return img_cfg.get(element_type, defaults)


def resolve_pil_resample(
    element_type: str,
    src_size: tuple[int, int],
    target_size: tuple[int, int],
) -> tuple[bool, Any]:
    """
    Determines whether an image can be passed through without resampling (exact 1:1 match)
    or which PIL resample filter (e.g. NEAREST vs LANCZOS) should be used based on configuration.

    Returns:
        (is_passthrough: bool, resample_filter: PIL.Image.Resampling | None)
    """
    from PIL import Image

    cfg = get_image_scaling_config(element_type)
    exact_pass = cfg.get("exact_1x_passthrough", True)

    # 1. Exact 1:1 dimension match -> passthrough without resample
    if exact_pass and src_size == target_size:
        return True, None

    resampling_ns = getattr(Image, "Resampling", Image)

    # Parse configured filter names
    int_filter_name = str(cfg.get("integer_resample", "NEAREST")).upper()
    frac_filter_name = str(cfg.get("fractional_resample", "LANCZOS")).upper()

    filter_map = {
        "NEAREST": resampling_ns.NEAREST,
        "BOX": resampling_ns.BOX,
        "BILINEAR": resampling_ns.BILINEAR,
        "HAMMING": resampling_ns.HAMMING,
        "BICUBIC": resampling_ns.BICUBIC,
        "LANCZOS": resampling_ns.LANCZOS,
    }

    int_filter = filter_map.get(int_filter_name, resampling_ns.NEAREST)
    frac_filter = filter_map.get(frac_filter_name, resampling_ns.LANCZOS)

    # 2. Check for integer multiple scaling (pixel doubling / tripling)
    src_w, src_h = src_size
    tgt_w, tgt_h = target_size

    if (
        src_w > 0 and src_h > 0
        and tgt_w % src_w == 0 and tgt_h % src_h == 0
        and (tgt_w // src_w) == (tgt_h // src_h)
        and (tgt_w // src_w) > 0
    ):
        return False, int_filter

    # 3. Fractional scaling
    return False, frac_filter


