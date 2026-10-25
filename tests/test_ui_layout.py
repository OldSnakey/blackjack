"""
Targeted Automated Test Suite for ui_layout.py and assets/ui_config.json.
Validates:
- Centralized configuration loading and schema integrity.
- Fallback resilience against missing or malformed configuration files.
- Hot-reloading on file modification timestamp changes.
- Mathematical precision of resolve_origin and resolve_offset across display scales.
"""

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from config import UI_CONFIG_FILE
import ui_layout


class TestUiLayout(unittest.TestCase):

    def setUp(self):
        ui_layout.reload_ui_config()

    def test_ui_config_file_exists_and_parses(self):
        """assets/ui_config.json must exist and parse as valid JSON."""
        self.assertTrue(Path(UI_CONFIG_FILE).exists(), f"{UI_CONFIG_FILE} does not exist!")
        with open(UI_CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("chip_visualizer", data)
        self.assertIn("soul_meter", data)
        self.assertIn("haunted_altar", data)
        self.assertIn("dealer_stage", data)
        self.assertIn("mahogany_rail", data)

    def test_chip_visualizer_schema_invariants(self):
        """chip_visualizer layout configuration must provide all required groups and offsets."""
        cv_cfg = ui_layout.get_ui_layout("chip_visualizer")
        self.assertIn("betting_spot", cv_cfg)
        self.assertIn("tray_divider", cv_cfg)
        self.assertIn("bankroll_piles", cv_cfg)
        self.assertIn("bankroll_badge", cv_cfg)
        self.assertIn("chips", cv_cfg)

        spot = cv_cfg["betting_spot"]
        self.assertIn("origin", spot)
        self.assertIn("outer_oval", spot)
        self.assertIn("inner_oval", spot)
        self.assertIn("watermark", spot)
        self.assertIn("bet_badge", spot)

        piles = cv_cfg["bankroll_piles"]
        self.assertIn("origin", piles)
        self.assertIn("denomination_label", piles)
        self.assertIn("hitbox", piles)

    def test_resolve_origin_ratio_and_pixel(self):
        """resolve_origin correctly evaluates ratio-based and pixel-based origins."""
        group_ratio = {"origin": {"x_ratio": 0.5, "y_ratio": 0.25}}
        ox, oy = ui_layout.resolve_origin(group_ratio, width=200, height=140)
        self.assertEqual(ox, 100)
        self.assertEqual(oy, 35)

        group_offset = {"origin": {"x_offset": 30, "y_offset": 50}}
        ox, oy = ui_layout.resolve_origin(group_offset, width=200, height=140, scale_x=1.5, scale_y=1.5)
        self.assertEqual(ox, 45)
        self.assertEqual(oy, 75)

    def test_resolve_offset_scaling(self):
        """resolve_offset adds scaled deltas accurately to an origin."""
        origin = (100, 50)
        elem = {"offset_x": 10, "offset_y": -15}
        # 1.0x scale
        rx, ry = ui_layout.resolve_offset(elem, origin, scale_x=1.0, scale_y=1.0)
        self.assertEqual(rx, 110)
        self.assertEqual(ry, 35)

        # 2.0x scale
        rx2, ry2 = ui_layout.resolve_offset(elem, origin, scale_x=2.0, scale_y=2.0)
        self.assertEqual(rx2, 120)
        self.assertEqual(ry2, 20)

    def test_fallback_on_missing_file(self):
        """If UI_CONFIG_FILE is pointed to a non-existent path, default config is safely returned."""
        with patch.object(ui_layout, "UI_CONFIG_FILE", Path("non_existent_config.json")):
            ui_layout.reload_ui_config()
            cfg = ui_layout.load_ui_config()
            self.assertEqual(cfg["version"], "1.0")
            self.assertIn("chip_visualizer", cfg)

    def test_hot_reloading_on_mtime_change(self):
        """load_ui_config reloads immediately when file mtime changes on disk."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_cfg = Path(tmp_dir) / "test_ui_config.json"
            tmp_cfg.write_text(json.dumps({"chip_visualizer": {"base_width": 250}}), encoding="utf-8")

            with patch.object(ui_layout, "UI_CONFIG_FILE", tmp_cfg):
                cfg1 = ui_layout.load_ui_config(force_reload=True)
                self.assertEqual(cfg1["chip_visualizer"]["base_width"], 250)

                # Mutate file and shift mtime forward
                time.sleep(0.05)
                tmp_cfg.write_text(json.dumps({"chip_visualizer": {"base_width": 320}}), encoding="utf-8")
                os.utime(tmp_cfg, (time.time() + 1, time.time() + 1))

                cfg2 = ui_layout.load_ui_config()
                self.assertEqual(cfg2["chip_visualizer"]["base_width"], 320)

    def test_get_grid_options(self):
        """get_grid_options extracts grid keyword arguments and converts list padding to tuples."""
        opts = ui_layout.get_grid_options("chip_visualizer")
        self.assertEqual(opts.get("row"), 1)
        self.assertEqual(opts.get("column"), 2)
        self.assertIn(opts.get("sticky"), ("e", "se"))
        self.assertIsInstance(opts.get("padx"), tuple)
        self.assertIsInstance(opts.get("pady"), tuple)

    def test_resolve_origin_with_content_offset(self):
        """resolve_origin shifts origin by content_offset accurately."""
        group = {"origin": {"x_ratio": 0.5, "y_ratio": 0.5}}
        ox, oy = ui_layout.resolve_origin(group, width=200, height=140, content_offset=(10, 20))
        self.assertEqual(ox, 110)
        self.assertEqual(oy, 90)


    def test_get_theme_color(self):
        """get_theme_color returns theme colors from ui_config or fallback default."""
        gold = ui_layout.get_theme_color("bankroll_text", "#ffd700")
        self.assertEqual(gold, "#ffd700")
        custom = ui_layout.get_theme_color("nonexistent_color", "#123456")
        self.assertEqual(custom, "#123456")

    def test_get_widget_style_and_scaling(self):
        """get_widget_style resolves fonts, colors, and scaled paddings."""
        style_1x = ui_layout.get_widget_style("insurance_prompt", "take_button", scale=1.0)
        self.assertEqual(style_1x.get("background"), "#ff9800")
        self.assertEqual(style_1x.get("padx"), 14)
        self.assertEqual(style_1x.get("pady"), 5)

        style_2x = ui_layout.get_widget_style("insurance_prompt", "take_button", scale=2.0)
        self.assertEqual(style_2x.get("padx"), 28)
        self.assertEqual(style_2x.get("pady"), 10)

    def test_apply_style_on_widget(self):
        """apply_style applies configuration-derived styles directly to a Tkinter widget."""
        import tkinter
        root = tkinter.Tk()
        root.withdraw()
        btn = tkinter.Button(root)
        ui_layout.apply_style(btn, "insurance_prompt", "decline_button", scale=1.0)
        self.assertEqual(btn.cget("background"), "#37474f")
        self.assertEqual(btn.cget("foreground"), "#ffffff")
        root.destroy()

    def test_table_felt_shoe_tray_configuration(self):
        """table_felt shoe_tray layout and plaque styling must be properly loaded and configurable."""
        cfg = ui_layout.get_ui_layout("table_felt", "shoe_tray")
        self.assertIn("width", cfg)
        self.assertIn("height", cfg)
        self.assertIn("offset_right", cfg)
        self.assertIn("offset_top", cfg)
        self.assertIn("plaque", cfg)

        plaque = cfg["plaque"]
        self.assertEqual(plaque.get("text_color"), "#ffd700")
        self.assertEqual(plaque.get("font_element"), "shoe_counter")
        self.assertIn("height", plaque)
        self.assertIn("offset_y", plaque)
        self.assertIn("background", plaque)
        self.assertIn("border", plaque)
        self.assertIn("cut_border", plaque)
        self.assertIn("cut_text_color", plaque)

    def test_soul_meter_configuration_and_widened_dimensions(self):
        """soul_meter layout configuration must specify a widened base_width (>= 240) to accommodate text."""
        cfg = ui_layout.get_ui_layout("soul_meter")
        self.assertGreaterEqual(cfg.get("base_width", 0), 240)
        self.assertIn("progress_bar", cfg)
        pbar = cfg["progress_bar"]
        self.assertIn("margin_x", pbar)
        self.assertIn("milestone_label_offset_y", pbar)

    def test_root_layout_configuration(self):
        """root_layout configuration provides window padding, weights, and row mappings."""
        cfg = ui_layout.get_ui_layout("root_layout")
        self.assertIn("padding", cfg)
        self.assertIn("column_weights", cfg)
        self.assertIn("row_weights", cfg)
        self.assertIn("rows", cfg)
        rows = cfg["rows"]
        self.assertIn("top_bar", rows)
        self.assertIn("dealer_stage", rows)
        self.assertIn("horizon_rail", rows)
        self.assertIn("card_table", rows)
        self.assertIn("mahogany_rail", rows)
        self.assertIn("insurance_prompt", rows)
        self.assertIn("blessings_tray", rows)

    def test_get_grid_options_with_sub_element(self):
        """get_grid_options retrieves grid options for top-level component or specific sub-element."""
        # Top-level component
        top_opts = ui_layout.get_grid_options("top_bar")
        self.assertEqual(top_opts.get("row"), 0)
        self.assertEqual(top_opts.get("columnspan"), 3)

        # Specific sub-element
        sound_opts = ui_layout.get_grid_options("top_bar", "sound_button")
        self.assertEqual(sound_opts.get("row"), 0)
        self.assertEqual(sound_opts.get("column"), 8)
        self.assertIsInstance(sound_opts.get("padx"), tuple)

        dealer_title_opts = ui_layout.get_grid_options("top_bar", "dealer_wins_title")
        self.assertEqual(dealer_title_opts.get("row"), 0)
        self.assertEqual(dealer_title_opts.get("column"), 0)

    def test_get_pack_options_and_scaling(self):
        """get_pack_options resolves pack keywords and scales paddings accurately."""
        pumpkin_1x = ui_layout.get_pack_options("dealer_stage", "pumpkin", scale=1.0)
        self.assertEqual(pumpkin_1x.get("side"), "left")
        self.assertEqual(pumpkin_1x.get("padx"), (0, 6))
        self.assertEqual(pumpkin_1x.get("pady"), 2)

        pumpkin_2x = ui_layout.get_pack_options("dealer_stage", "pumpkin", scale=2.0)
        self.assertEqual(pumpkin_2x.get("padx"), (0, 12))
        self.assertEqual(pumpkin_2x.get("pady"), 4)

    def test_card_table_layout_helper(self):
        """get_table_layout retrieves row/col configurations, plaque placements, and frame styles."""
        tbl = ui_layout.get_table_layout()
        self.assertIn("column_weights", tbl)
        self.assertIn("row_configs", tbl)
        self.assertIn("dealer_header", tbl)
        self.assertIn("player_header", tbl)
        self.assertIn("dealer_cards", tbl)
        self.assertIn("player_cards", tbl)
        self.assertIn("accessories", tbl)

        # Verify row min-heights are configured
        row_cfgs = {r["row"]: r for r in tbl["row_configs"]}
        self.assertGreaterEqual(row_cfgs[0].get("minsize", 0), 100)
        self.assertGreaterEqual(row_cfgs[1].get("minsize", 0), 100)

    def test_mahogany_rail_button_layout_helper(self):
        """get_rail_button_layout resolves button widths, dock gaps, and control dock options."""
        rail_layout = ui_layout.get_rail_button_layout()
        self.assertIn("btn_height", rail_layout)
        self.assertIn("dock_gap", rail_layout)
        self.assertIn("side_margin", rail_layout)
        self.assertIn("bet_buttons", rail_layout)
        self.assertIn("play_buttons", rail_layout)
        self.assertIn("anchor_buttons", rail_layout)
        self.assertIn("cursed_stakes", rail_layout)

        bet_btns = rail_layout["bet_buttons"]
        self.assertIn("clear_bet", bet_btns)
        self.assertIn("all_in", bet_btns)
        self.assertIn("deal_hand", bet_btns)

        play_btns = rail_layout["play_buttons"]
        self.assertIn("hit", play_btns)
        self.assertIn("stand", play_btns)
        self.assertIn("double", play_btns)
        self.assertIn("split", play_btns)
        self.assertIn("surrender", play_btns)

    def test_cards_layout_helper(self):
        """get_card_layout returns card spacing and multi-card compression options."""
        cards_layout = ui_layout.get_card_layout()
        self.assertIn("dealer_card_padx", cards_layout)
        self.assertIn("split_hand_gap", cards_layout)
        self.assertIn("container_pad", cards_layout)
        self.assertIn("multi_card_compress_threshold", cards_layout)
        self.assertIn("compression_factor_single", cards_layout)
        self.assertIn("compression_factor_split", cards_layout)
        self.assertIn("min_overlap", cards_layout)

    def test_blessings_tray_layout(self):
        """blessings_tray layout options are loaded and configurable."""
        tray_opts = ui_layout.get_grid_options("blessings_tray")
        self.assertEqual(tray_opts.get("row"), 7)
        self.assertEqual(tray_opts.get("columnspan"), 3)
        tray_cfg = ui_layout.get_ui_layout("blessings_tray")
        self.assertIn("relic_item_padx", tray_cfg)

    def test_root_layout_grid_options_sub_element(self):
        """get_grid_options correctly resolves sub-elements under root_layout rows with full sticky options."""
        ct_opts = ui_layout.get_grid_options("root_layout", "card_table")
        self.assertEqual(ct_opts.get("row"), 3)
        self.assertEqual(ct_opts.get("column"), 0)
        self.assertEqual(ct_opts.get("columnspan"), 3)
        self.assertEqual(ct_opts.get("sticky"), "nsew")

        ds_opts = ui_layout.get_grid_options("root_layout", "dealer_stage")
        self.assertEqual(ds_opts.get("row"), 1)
        self.assertEqual(ds_opts.get("column"), 0)
        self.assertEqual(ds_opts.get("columnspan"), 3)
        self.assertEqual(ds_opts.get("sticky"), "ew")

    def test_image_scaling_config_schema(self):
        """image_scaling configuration provides per-element-type scaling modes and resampling options."""
        for elem_type in ("cards", "dealer", "haunted_accessories", "relics", "ui_icons"):
            cfg = ui_layout.get_image_scaling_config(elem_type)
            self.assertIn("mode", cfg)
            self.assertIn("exact_1x_passthrough", cfg)
            self.assertIn("integer_resample", cfg)
            self.assertIn("fractional_resample", cfg)

    def test_resolve_pil_resample(self):
        """resolve_pil_resample evaluates 1x passthrough, integer pixel-perfect NEAREST, and fractional LANCZOS."""
        from PIL import Image
        nearest = getattr(Image, "Resampling", Image).NEAREST
        lanczos = getattr(Image, "Resampling", Image).LANCZOS

        # 1. Exact 1x match (e.g. 74x107 -> 74x107) -> True passthrough
        is_pass, resample = ui_layout.resolve_pil_resample("cards", (74, 107), (74, 107))
        self.assertTrue(is_pass)

        # 2. Integer 2x scale (74x107 -> 148x214) -> False passthrough, NEAREST filter
        is_pass_2x, resample_2x = ui_layout.resolve_pil_resample("cards", (74, 107), (148, 214))
        self.assertFalse(is_pass_2x)
        self.assertEqual(resample_2x, nearest)

        # 3. Fractional scale (74x107 -> 100x150) -> False passthrough, LANCZOS filter
        is_pass_frac, resample_frac = ui_layout.resolve_pil_resample("cards", (74, 107), (100, 150))
        self.assertFalse(is_pass_frac)
        self.assertEqual(resample_frac, lanczos)


if __name__ == "__main__":
    unittest.main()



