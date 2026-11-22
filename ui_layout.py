"""
UI Layout & Coordinate Configuration Engine for Blackjack (v2.0 Pit-Wings Schema).

Provides:
- Centralized coordinate hierarchy mapping for the unified 4-row Pit-Wings layout
  and 2.5D canvas presentation components (ChipVisualizer, SoulMeterCanvas,
  HauntedAltarCanvas, DealerStageCanvas, TableFeltCanvas, MahoganyRailCanvas).
- Hot-reloading from assets/ui_config.json on disk modification (read-only at runtime).
- Robust, zero-crash default fallbacks matching assets/ui_config.json byte-for-byte.
- Center-relative (pit_cx) lane, pit-bounds, and multi-seat resolvers across DisplayProfiles.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Tuple

from config import UI_CONFIG_FILE

DEFAULT_UI_CONFIG: dict[str, Any] = {
    "version": "2.0",
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
    "display_profiles": {
        "hd_720p": {
            "window_w": 1280,
            "window_h": 720,
            "art_scale": 1,
            "card_scale": 1.0,
            "font_scale": 1,
            "stage_w": 1000,
            "stage_h": 220,
            "rail_h": 72,
            "divider_h": 4,
            "pit_max_width": 1280,
            "multi_seat_dx": 240,
        },
        "deck_800p": {
            "window_w": 1280,
            "window_h": 800,
            "art_scale": 1,
            "card_scale": 1.0,
            "font_scale": 1,
            "stage_w": 1000,
            "stage_h": 220,
            "rail_h": 72,
            "divider_h": 4,
            "pit_max_width": 1280,
            "multi_seat_dx": 240,
        },
        "fhd_1080p": {
            "window_w": 1920,
            "window_h": 1080,
            "art_scale": 1,
            "card_scale": 1.5,
            "font_scale": 1,
            "stage_w": 1000,
            "stage_h": 220,
            "rail_h": 72,
            "divider_h": 4,
            "pit_max_width": 1920,
            "multi_seat_dx": 345,
        },
        "qhd_1440p": {
            "window_w": 2560,
            "window_h": 1440,
            "art_scale": 2,
            "card_scale": 2.0,
            "font_scale": 2,
            "stage_w": 2000,
            "stage_h": 440,
            "rail_h": 144,
            "divider_h": 8,
            "pit_max_width": 2560,
            "multi_seat_dx": 480,
        },
        "uhd_4k": {
            "window_w": 3840,
            "window_h": 2160,
            "art_scale": 2,
            "card_scale": 2.0,
            "font_scale": 2,
            "stage_w": 2000,
            "stage_h": 440,
            "rail_h": 144,
            "divider_h": 8,
            "pit_max_width": 2560,
            "multi_seat_dx": 480,
        },
    },
    "root_layout": {
        "padding": {"padx": 0, "pady": 0},
        "column_weights": [{"column": 0, "weight": 1}],
        "row_weights": [{"row": 2, "weight": 1}],
        "rows": {
            "stage_band": {"row": 0, "column": 0, "sticky": "ew"},
            "horizon_rail": {"row": 1, "column": 0, "sticky": "ew"},
            "card_table": {"row": 2, "column": 0, "sticky": "nsew"},
            "mahogany_rail": {"row": 3, "column": 0, "sticky": "ew"},
        },
    },
    "stage_wings": {
        "min_wing_width_1x": 140,
        "min_wing_width_2x": 280,
        "proscenium_bg": "#120906",
        "wing_bg": "#1b0f0a",
        "wing_border": "#7d5b10",
        "left_stage_wing": {
            "padx": 8,
            "pady": 6,
            "elements": {
                "header_label": {"row": 0, "column": 0, "sticky": "ew"},
                "bankroll_label": {"row": 1, "column": 0, "pady": [2, 2], "sticky": "ew"},
                "staged_bet_label": {"row": 2, "column": 0, "pady": [1, 2], "sticky": "ew"},
                "stats_frame": {"row": 3, "column": 0, "pady": [2, 2], "sticky": "ew"},
                "house_rules_pill": {"row": 4, "column": 0, "pady": [2, 1], "sticky": "ew"},
                "tour_goal_label": {"row": 5, "column": 0, "pady": [1, 0], "sticky": "ew"},
            },
        },
        "right_stage_wing": {
            "padx": 6,
            "pady": 6,
            "btn_width_1x": 60,
            "btn_height_1x": 30,
            "buttons": {
                "tour_button": {"row": 0, "column": 0, "padx": 2, "pady": 3},
                "trip_button": {"row": 0, "column": 1, "padx": 2, "pady": 3},
                "settings_button": {"row": 1, "column": 0, "padx": 2, "pady": 3},
                "sound_button": {"row": 1, "column": 1, "padx": 2, "pady": 3},
                "help_button": {"row": 2, "column": 0, "padx": 2, "pady": 3},
                "fullscreen_button": {"row": 2, "column": 1, "padx": 2, "pady": 3},
            },
        },
    },
    "insurance_prompt": {
        "placement": "center_felt_floating_plaque",
        "anchor": "center",
        "frame": {
            "background": "#0c2917",
            "highlightbackground": "#d4af37",
            "highlightthickness": 2,
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
    "counting_hud": {
        "zone": "left_felt_wing",
        "orientation": "vertical_slate",
        "max_width_1x": 206,
        "collapsed_tab_width_1x": 96,
        "collapsed_tab_height_1x": 28,
        "slate_bg": "#1f120b",
        "slate_border": "#d4af37",
    },
    "chip_visualizer": {
        "base_width": 288,
        "base_height": 204,
        "grid_placement": {
            "row": 1,
            "column": 2,
            "rowspan": 2,
            "padx": [10, 6],
            "pady": [0, 6],
            "sticky": "se",
        },
        "content_offset": {"x": 0, "y": 6},
        "perfect_pairs_spot": {
            "origin": {"x_ratio": 0.16, "y_ratio": 0.23},
            "outer_oval": {"rx": 34, "ry": 16},
            "inner_oval": {"rx": 30, "ry": 13},
            "watermark": {"offset_x": 0, "offset_y": 1},
            "bet_badge": {"offset_x": 0, "offset_y": -26},
        },
        "betting_spot": {
            "origin": {"x_ratio": 0.5, "y_ratio": 0.23},
            "outer_oval": {"rx": 48, "ry": 20},
            "inner_oval": {"rx": 43, "ry": 16},
            "watermark": {"offset_x": 0, "offset_y": 1},
            "bet_badge": {"offset_x": 0, "offset_y": -32},
        },
        "twenty_one_plus_three_spot": {
            "origin": {"x_ratio": 0.84, "y_ratio": 0.23},
            "outer_oval": {"rx": 34, "ry": 16},
            "inner_oval": {"rx": 30, "ry": 13},
            "watermark": {"offset_x": 0, "offset_y": 1},
            "bet_badge": {"offset_x": 0, "offset_y": -26},
        },
        "tray_divider": {
            "y_ratio": 0.46,
            "margin_x": 10,
        },
        "bankroll_piles": {
            "origin": {"x_ratio": 0.5, "y_ratio": 0.65},
            "margin_x": 24,
            "chip_vertical_step": 3,
            "denomination_label": {"offset_x": 0, "offset_y": 18},
            "hitbox": {"pad_x": 4, "top_offset": -18, "bottom_offset": 7},
        },
        "bankroll_badge": {
            "origin": {"x_ratio": 0.5, "y_ratio": 0.91},
        },
        "chips": {
            "compact": {"rx": 14, "ry": 7, "depth": 3, "stripe_x": 7},
            "standard": {"rx": 16, "ry": 8, "depth": 4, "stripe_x": 9},
        },
        "animations": {
            "payout_offset": {"x": 20, "y": -20},
            "floating_text_offset_y": -16,
        },
    },
    "soul_meter": {
        "base_width": 260,
        "base_height": 150,
        "grid_placement": {
            "row": 1,
            "column": 2,
            "padx": [10, 6],
            "pady": [2, 6],
            "sticky": "se",
        },
        "content_offset": {"x": 0, "y": 0},
        "header": {"origin": {"x_ratio": 0.5, "y_offset": 16}},
        "progress_bar": {
            "margin_x": 18,
            "top_y": 44,
            "bottom_y": 64,
            "pointer": {"width": 5, "height": 6},
            "milestone_label_offset_y": -12,
            "bound_label_offset_y": 11,
        },
        "status_text": {"origin": {"x_ratio": 0.5, "y_offset": 96}},
        "hint_text": {"origin": {"x_ratio": 0.5, "y_offset": 122}},
    },
    "haunted_altar": {
        "base_width": 260,
        "base_height": 96,
        "candles": {
            "origin_y": 22,
            "start_x": 26,
            "step_x": 52,
            "glow": {
                "outer": {"rx": 22, "ry_top": -5, "ry_bottom": 22},
                "mid": {"rx": 15, "ry_top": 0, "ry_bottom": 18},
                "inner": {"rx": 8, "ry_top": 4, "ry_bottom": 14},
            },
        },
        "gravestones": {
            "origin_y": 62,
            "x_positions": [36, 83, 130, 177, 224],
        },
    },
    "dealer_stage": {
        "default_width": 1000,
        "default_height": 220,
        "stage_canvas": {"fill": "none", "expand": False},
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
        "frame": {"relief": "flat", "borderwidth": 0, "padx": 0, "pady": 0},
        "column_weights": [
            {"column": 0, "weight": 0},
            {"column": 1, "weight": 1},
            {"column": 2, "weight": 0},
        ],
        "row_configs": [
            {"row": 0, "weight": 1, "minsize": 118},
            {"row": 1, "weight": 1, "minsize": 140},
            {"row": 2, "weight": 0, "minsize": 58},
        ],
        "left_felt_wing": {"row": 0, "column": 0, "rowspan": 3, "sticky": "nw", "padx": [8, 4], "pady": [8, 6]},
        "dealer_header": {"row": 0, "column": 1, "sticky": "nw", "padx": [8, 6], "pady": [6, 0]},
        "dealer_cards": {"row": 0, "column": 1, "padx": 10, "pady": 1},
        "player_header": {"row": 1, "column": 1, "sticky": "nw", "padx": [8, 6], "pady": [6, 0]},
        "player_cards": {"row": 1, "column": 1, "padx": 10, "pady": [6, 1]},
        "accessories": {"row": 0, "column": 2, "sticky": "ne", "padx": [4, 8], "pady": [56, 2]},
        "haunted_altar": {"side": "top", "pady": 0},
    },
    "mahogany_rail": {
        "default_height": 72,
        "trim_line_y": 0,
        "accent_line_y": 2,
        "grid_placement": {"row": 3, "column": 0, "sticky": "ew", "pady": [0, 0]},
        "dock": {
            "btn_height": 38,
            "scale_2x_height_multiplier": 2.0,
            "dock_gap": 12,
            "side_margin": 24,
            "bet_buttons": {
                "clear_bet": {"width": 140},
                "all_in": {"width": 104},
                "deal_hand": {"width": 156},
                "rebuy": {"width": 132},
            },
            "play_buttons": {
                "hit": {"width": 104},
                "stand": {"width": 104},
                "double": {"width": 104},
                "split": {"width": 104},
                "surrender": {"width": 124},
            },
            "anchor_buttons": {
                "new_game": {"width": 124},
                "miracle": {"width": 144},
            },
            "cursed_stakes": {
                "grid_placement": {"row": 0, "column": 8, "padx": [6, 8], "pady": 3, "sticky": "e"},
            },
        },
    },
    "cards_layout": {
        "dealer_card_padx": 2,
        "split_hand_gap": 12,
        "container_pad": {"padx": 6, "pady": 4},
        "multi_card_compress_threshold": 4,
        "compression_factor_single": 0.85,
        "compression_factor_split": 0.72,
        "min_overlap": 12,
        "dealer_top_margin": 16,
        "player_bottom_margin": 22,
        "split_badge_height": 18,
        "slide_duration_ms": 144,
        "slide_interval_ms": 16,
        "slide_arc_lift": 18,
    },
    "blessings_tray": {
        "zone": "left_felt_wing",
        "orientation": "vertical",
        "max_width_1x": 206,
        "header_pady": [2, 4],
        "relic_item_padx": 4,
        "relic_item_pady": 2,
        "icon_padx": 4,
    },
    "table_felt": {
        "shoe_tray": {
            "width": 94,
            "height": 28,
            "offset_right": 14,
            "offset_top": 3,
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
        "multi_seat": {
            "default_dx_1x": 240,
            "fhd_1080p_dx": 345,
            "qhd_2x_dx": 480,
            "side_bet_offset_1x": 76,
            "side_bet_offset_1080p": 96,
            "side_bet_offset_2x": 152,
            "flank_arc_lift_y": 10,
        },
        "split_fan_offset_x": 35,
        "split_vertical_cascade_y": 16,
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
    Supports nested v2.0 stage_wings ('left_stage_wing.elements' / 'right_stage_wing.buttons').
    """
    comp_dict = get_ui_layout(component_key)
    if element_key is not None:
        raw_opts = comp_dict.get("elements", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("rows", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("dock", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("right_stage_wing", {}).get("buttons", {}).get(element_key)
        if raw_opts is None:
            raw_opts = comp_dict.get("left_stage_wing", {}).get("elements", {}).get(element_key)
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
    valid_grid_keys = {"row", "column", "rowspan", "columnspan", "sticky", "padx", "pady", "ipadx", "ipady"}
    opts = {k: v for k, v in raw_opts.items() if k in valid_grid_keys}
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


def resolve_pit_bounds(canvas_w: int, pit_max_width: int) -> Tuple[int, int, int]:
    """
    Computes centered horizontal pit boundaries (pit_left, pit_cx, pit_right).
    On ultrawide (3440x1440) and 4K (3840x2160) displays, clamps outer felt wings
    inside pit_max_width (e.g. 2560px) so bankroll/shoe/count panels stay within comfortable eye travel.
    """
    cw = max(1, int(canvas_w))
    max_w = max(1, int(pit_max_width)) if pit_max_width else cw
    eff_w = min(cw, max_w)
    pit_cx = cw // 2
    pit_left = max(0, pit_cx - eff_w // 2)
    pit_right = min(cw, pit_left + eff_w)
    return pit_left, pit_cx, pit_right


def get_seat_origin(
    seat_idx: int,
    canvas_w: int = 1280,
    canvas_h: int = 504,
    profile: Any = None,
) -> dict[str, int]:
    """
    Computes symmetric center-relative coordinates (x, y, card_y, side_bet_offset_x, side_bet_y)
    for table seats 1 (Right / First Base), 2 (Center), and 3 (Left / Third Base).
    All returned coordinates are in final canvas pixels for (canvas_w, canvas_h).
    """
    ms_cfg = get_ui_layout("table_felt", "multi_seat")
    if profile is not None:
        art_scale = int(getattr(profile, "art_scale", 1))
        card_scale = float(getattr(profile, "card_scale", 1.0))
        seat_dx = int(getattr(profile, "multi_seat_dx", 240))
        prof_name = str(getattr(profile, "name", "deck_800p"))
    else:
        art_scale = 2 if canvas_w >= 2500 else 1
        card_scale = 2.0 if art_scale == 2 else (1.5 if canvas_w >= 1600 else 1.0)
        prof_name = "qhd_1440p" if art_scale == 2 else ("fhd_1080p" if canvas_w >= 1600 else "deck_800p")
        if art_scale == 2:
            seat_dx = int(ms_cfg.get("qhd_2x_dx", 480))
        elif canvas_w >= 1600:
            seat_dx = int(ms_cfg.get("fhd_1080p_dx", 345))
        else:
            seat_dx = int(ms_cfg.get("default_dx_1x", 240))

    # Clamp seat_dx for narrow isolated unit-test canvases (e.g. 610px or 980px)
    max_safe_dx = max(140, (int(canvas_w) - int(180 * art_scale)) // 2)
    seat_dx = min(seat_dx, max_safe_dx)

    if art_scale == 2:
        sb_off = int(ms_cfg.get("side_bet_offset_2x", 152))
    elif prof_name == "fhd_1080p":
        sb_off = int(ms_cfg.get("side_bet_offset_1080p", 96))
    else:
        sb_off = int(ms_cfg.get("side_bet_offset_1x", 76))
    sb_off = min(sb_off, max(44, (seat_dx - int(64 * art_scale)) // 2))

    pit_cx = int(canvas_w) // 2
    s_idx = int(seat_idx)
    if s_idx == 1:
        cx = pit_cx + seat_dx
    elif s_idx == 3:
        cx = pit_cx - seat_dx
    else:
        cx = pit_cx

    card_h = 160 if abs(card_scale - 1.5) < 0.05 else int(round(107 * card_scale))
    flank_lift = int(ms_cfg.get("flank_arc_lift_y", 10) * art_scale)

    ch = max(220, int(canvas_h))
    if ch < int(360 * art_scale):
        # Compact unit-test canvas fallback
        spot_center_y = ch - int(58 * art_scale)
        card_center_y = max(int(24 * art_scale), spot_center_y - card_h - int(14 * art_scale))
    else:
        spot_center_y = ch - int(86 * art_scale)
        card_center_y = max(int(126 * art_scale), spot_center_y - card_h - int(36 * art_scale))

    if s_idx in (1, 3):
        spot_y = spot_center_y - flank_lift
        card_y = card_center_y - flank_lift
    else:
        spot_y = spot_center_y
        card_y = card_center_y

    return {
        "x": cx,
        "y": spot_y,
        "card_y": card_y,
        "side_bet_offset_x": sb_off,
        "side_bet_y": spot_y,
    }


def resolve_center_pit_lanes(
    canvas_w: int,
    canvas_h: int,
    profile: Any = None,
    table_seats: int = 1,
) -> dict[str, Any]:
    """
    Computes vertical card lanes and midpoint markings for CenterPit:
    returns dict with pit_left, pit_cx, pit_right, dealer_y, player_y, mid_gap_y, and seat_origins.
    """
    if profile is not None:
        art_scale = int(getattr(profile, "art_scale", 1))
        card_h = int(getattr(profile, "card_height", 107 * art_scale))
        pit_max_w = int(getattr(profile, "pit_max_width", canvas_w))
    else:
        art_scale = 2 if canvas_w >= 2500 else 1
        card_h = 214 if art_scale == 2 else (160 if canvas_w >= 1600 else 107)
        pit_max_w = 2560 if art_scale == 2 else min(max(1280, canvas_w), 1920)

    pit_left, pit_cx, pit_right = resolve_pit_bounds(canvas_w, pit_max_w)
    cards_cfg = get_card_layout()
    ch = max(200, int(canvas_h))
    extra_v = (
        min(int(64 * art_scale), max(0, ch - int(540 * art_scale)) // 3)
        if int(table_seats) == 1
        else 0
    )
    dealer_top = int(cards_cfg.get("dealer_top_margin", 16) * art_scale) + extra_v
    player_bot = int(cards_cfg.get("player_bottom_margin", 22) * art_scale) + extra_v

    dealer_y = dealer_top
    dealer_bottom = dealer_y + card_h

    seat_origins = {
        s_idx: get_seat_origin(s_idx, canvas_w=canvas_w, canvas_h=ch, profile=profile)
        for s_idx in (1, 2, 3)
    }

    if int(table_seats) > 1:
        player_y = min(o["card_y"] for o in seat_origins.values())
    else:
        player_y = max(dealer_bottom + int(44 * art_scale), ch - card_h - player_bot)

    mid_gap_y = (dealer_bottom + player_y) // 2
    return {
        "pit_left": pit_left,
        "pit_cx": pit_cx,
        "pit_right": pit_right,
        "dealer_y": dealer_y,
        "dealer_card_y": dealer_y,
        "player_y": player_y,
        "player_card_y": player_y,
        "mid_gap_y": mid_gap_y,
        "seat_origins": seat_origins,
    }


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


def get_widget_style(
    component_key: str,
    element_key: str,
    scale: Any = 1.0,
    profile: Any = None,
) -> dict[str, Any]:
    """
    Resolves a complete style dictionary for a Tkinter widget (font, colors, borders, and scaled paddings).
    Accepts either a float scale factor or a DisplayProfile instance (via `scale` or `profile`).
    """
    cfg = get_ui_layout(component_key, element_key)
    if not cfg:
        return {}

    prof_obj = profile if (profile is not None and hasattr(profile, "font_scale") and hasattr(profile, "art_scale")) else (
        scale if (hasattr(scale, "font_scale") and hasattr(scale, "art_scale")) else None
    )
    if prof_obj is not None:
        font_scale = float(prof_obj.font_scale)
        art_scale = float(prof_obj.art_scale)
    else:
        s_val = float(scale)
        font_scale = 2.0 if s_val > 1.5 else 1.0
        art_scale = s_val

    style = dict(cfg)
    if "font_element" in style:
        font_elem = style.pop("font_element")
        try:
            from pixel_ui import get_element_font
            style["font"] = get_element_font(font_elem, scale=font_scale)
        except Exception:
            pass

    if "padx" in style:
        px = style["padx"]
        if isinstance(px, (int, float)):
            style["padx"] = int(px * art_scale)
        elif isinstance(px, (list, tuple)):
            style["padx"] = tuple(int(p * art_scale) for p in px)

    if "pady" in style:
        py = style["pady"]
        if isinstance(py, (int, float)):
            style["pady"] = int(py * art_scale)
        elif isinstance(py, (list, tuple)):
            style["pady"] = tuple(int(p * art_scale) for p in py)

    return style


def apply_style(
    widget: Any,
    component_key: str,
    element_key: str,
    scale: Any = 1.0,
    profile: Any = None,
) -> dict[str, Any]:
    """
    Applies the configuration-derived styling directly to a Tkinter widget.
    Filters options supported by widget.configure() to prevent runtime errors.
    Returns the applied style dictionary.
    """
    style = get_widget_style(component_key, element_key, scale=scale, profile=profile)
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
