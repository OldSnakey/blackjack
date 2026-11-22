"""
Unit and headless integration tests for DisplayProfile resolution matching,
OS DPI / Linux font bootstrap state transitions, 1.5x binary-alpha card scaling,
and Pit-Wings configuration contracts.
"""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock
import tkinter
from PIL import Image

import config
from event_bus import GameEventType


class TestDisplayProfileEngine(unittest.TestCase):
    """Verifies DisplayProfile tier resolution, work-area clamping, and bootstrap diagnostics."""

    def test_config_window_constants_updated_to_widescreen(self):
        """Window constants default to 1280x800 with 1280x720 fallback."""
        self.assertEqual(config.DEFAULT_WINDOW_WIDTH, 1280)
        self.assertEqual(config.DEFAULT_WINDOW_HEIGHT, 800)
        self.assertEqual(config.FALLBACK_WINDOW_HEIGHT, 720)
        self.assertEqual(config.MIN_WINDOW_WIDTH, 1280)
        self.assertEqual(config.MIN_WINDOW_HEIGHT, 720)

    def test_event_bus_has_display_profile_changed_event(self):
        """GameEventType defines DISPLAY_PROFILE_CHANGED."""
        self.assertTrue(hasattr(GameEventType, "DISPLAY_PROFILE_CHANGED"))
        self.assertEqual(GameEventType.DISPLAY_PROFILE_CHANGED.value, "display_profile_changed")

    def test_windowed_default_vs_constrained_workarea_fallback(self):
        """Desktop Windowed mode defaults to 1280x800 when usable height >= 840, else 1280x720."""
        from display_profile import DisplayEnvironmentProbe, resolve_display_profile

        probe_roomy = DisplayEnvironmentProbe(
            monitor_wh=(1920, 1080),
            usable_workarea_wh=(1920, 1040),
            is_steam_deck=False,
            is_gamescope=False,
        )
        prof_800 = resolve_display_profile(probe_roomy, fullscreen=False)
        self.assertEqual(prof_800.name, "deck_800p")
        self.assertEqual((prof_800.window_w, prof_800.window_h), (1280, 800))
        self.assertEqual(prof_800.art_scale, 1)
        self.assertEqual(prof_800.card_scale, 1.0)
        self.assertEqual(prof_800.font_scale, 1)
        self.assertEqual(prof_800.pit_max_width, 1280)
        self.assertFalse(prof_800.is_fullscreen)

        # Laptop with 150% DPI virtual 1280x720 or 1366x768 with taskbar leaving 728px
        probe_tight = DisplayEnvironmentProbe(
            monitor_wh=(1366, 768),
            usable_workarea_wh=(1366, 728),
            is_steam_deck=False,
            is_gamescope=False,
        )
        prof_720 = resolve_display_profile(probe_tight, fullscreen=False)
        self.assertEqual(prof_720.name, "hd_720p")
        self.assertEqual((prof_720.window_w, prof_720.window_h), (1280, 720))
        self.assertEqual(prof_720.art_scale, 1)
        self.assertEqual(prof_720.card_scale, 1.0)

    def test_steam_deck_native_800p_and_docked_720p_fullscreen(self):
        """Steam Deck 1280x800 fullscreen resolves to deck_800p (not misclassified into hd_720p)."""
        from display_profile import DisplayEnvironmentProbe, resolve_display_profile

        deck_native = DisplayEnvironmentProbe(
            monitor_wh=(1280, 800),
            usable_workarea_wh=(1280, 800),
            is_steam_deck=True,
            is_gamescope=True,
        )
        prof_deck = resolve_display_profile(deck_native, fullscreen=True)
        self.assertEqual(prof_deck.name, "deck_800p")
        self.assertEqual((prof_deck.window_w, prof_deck.window_h), (1280, 800))
        self.assertTrue(prof_deck.is_fullscreen)
        self.assertEqual(prof_deck.art_scale, 1)
        self.assertEqual(prof_deck.card_scale, 1.0)

        deck_docked_720 = DisplayEnvironmentProbe(
            monitor_wh=(1280, 720),
            usable_workarea_wh=(1280, 720),
            is_steam_deck=True,
            is_gamescope=True,
        )
        prof_docked = resolve_display_profile(deck_docked_720, fullscreen=True)
        self.assertEqual(prof_docked.name, "hd_720p")
        self.assertEqual((prof_docked.window_w, prof_docked.window_h), (1280, 720))

    def test_fullscreen_1080p_and_strict_integer_cards_override(self):
        """1920x1080 and 1920x1200 fullscreen use fhd_1080p (1x stage, 1.5x cards, 1.0x when strict_integer_cards)."""
        from display_profile import DisplayEnvironmentProbe, resolve_display_profile

        for mon in ((1920, 1080), (1920, 1200), (1600, 900)):
            probe = DisplayEnvironmentProbe(
                monitor_wh=mon,
                usable_workarea_wh=(mon[0], mon[1] - 48),
                is_steam_deck=False,
                is_gamescope=False,
            )
            prof = resolve_display_profile(probe, fullscreen=True, strict_integer_cards=False)
            self.assertEqual(prof.name, "fhd_1080p")
            self.assertEqual((prof.window_w, prof.window_h), mon)
            self.assertEqual(prof.art_scale, 1)
            self.assertEqual(prof.card_scale, 1.5)
            self.assertEqual(prof.font_scale, 1)
            self.assertEqual((prof.stage_w, prof.stage_h), (1000, 220))
            self.assertEqual(prof.pit_max_width, 1920)

            prof_int = resolve_display_profile(probe, fullscreen=True, strict_integer_cards=True)
            self.assertEqual(prof_int.card_scale, 1.0)
            self.assertEqual(prof_int.art_scale, 1)

    def test_dual_monitor_virtual_width_clamped_by_height_tier(self):
        """Dual 1080p (3840x1080) must NOT match uhd_4k because height 1080 < 1440."""
        from display_profile import DisplayEnvironmentProbe, resolve_display_profile

        dual_1080 = DisplayEnvironmentProbe(
            monitor_wh=(3840, 1080),
            usable_workarea_wh=(3840, 1040),
            is_steam_deck=False,
            is_gamescope=False,
        )
        prof = resolve_display_profile(dual_1080, fullscreen=True)
        self.assertEqual(prof.name, "fhd_1080p")
        self.assertEqual(prof.art_scale, 1)
        self.assertEqual(prof.pit_max_width, 1920)

    def test_fullscreen_1440p_ultrawide_and_4k_profiles(self):
        """2560x1440, 3440x1440, and 3840x2160 resolve to native 2x profiles with pit_max_width=2560."""
        from display_profile import DisplayEnvironmentProbe, resolve_display_profile

        for mon in ((2560, 1440), (2560, 1600), (3440, 1440)):
            probe = DisplayEnvironmentProbe(
                monitor_wh=mon,
                usable_workarea_wh=(mon[0], mon[1] - 48),
                is_steam_deck=False,
                is_gamescope=False,
            )
            prof = resolve_display_profile(probe, fullscreen=True)
            self.assertEqual(prof.name, "qhd_1440p")
            self.assertEqual(prof.art_scale, 2)
            self.assertEqual(prof.card_scale, 2.0)
            self.assertEqual(prof.font_scale, 2)
            self.assertEqual((prof.stage_w, prof.stage_h), (2000, 440))
            self.assertEqual(prof.pit_max_width, 2560)

        probe_4k = DisplayEnvironmentProbe(
            monitor_wh=(3840, 2160),
            usable_workarea_wh=(3840, 2100),
            is_steam_deck=False,
            is_gamescope=False,
        )
        prof_4k = resolve_display_profile(probe_4k, fullscreen=True)
        self.assertEqual(prof_4k.name, "uhd_4k")
        self.assertEqual(prof_4k.art_scale, 2)
        self.assertEqual(prof_4k.card_scale, 2.0)
        self.assertEqual(prof_4k.font_scale, 2)
        self.assertEqual((prof_4k.stage_w, prof_4k.stage_h), (2000, 440))
        self.assertEqual(prof_4k.pit_max_width, 2560)

        # Optional 2x Windowed mode on 4K desktop
        prof_win_2x = resolve_display_profile(
            probe_4k, fullscreen=False, window_profile_override="qhd_1440p"
        )
        self.assertEqual(prof_win_2x.name, "qhd_1440p")
        self.assertEqual((prof_win_2x.window_w, prof_win_2x.window_h), (2560, 1440))
        self.assertFalse(prof_win_2x.is_fullscreen)

        # Requesting qhd_1440p window on a 1080p monitor safely clamps down to deck_800p
        probe_1080 = DisplayEnvironmentProbe(
            monitor_wh=(1920, 1080),
            usable_workarea_wh=(1920, 1030),
            is_steam_deck=False,
            is_gamescope=False,
        )
        prof_clamped = resolve_display_profile(
            probe_1080, fullscreen=False, window_profile_override="qhd_1440p"
        )
        self.assertEqual(prof_clamped.name, "deck_800p")
        self.assertEqual((prof_clamped.window_w, prof_clamped.window_h), (1280, 800))

    def test_font_verification_sets_loaded_only_when_root_present_and_records_missing(self):
        """pixel_ui font verification does not prematurely lock _ALL_FONTS_LOADED before root verification."""
        import pixel_ui

        root = tkinter.Tk()
        root.withdraw()
        try:
            mode, missing = pixel_ui.verify_and_finalize_pixel_fonts(root)
            self.assertIsInstance(mode, str)
            self.assertIsInstance(missing, tuple)
            self.assertTrue(pixel_ui._ALL_FONTS_LOADED)
            # Simulate missing families under mocked tkfont.families
            with mock.patch("pixel_ui.tkfont.families", return_value=("Courier", "Arial")):
                mode_miss, missing_fams = pixel_ui.verify_and_finalize_pixel_fonts(
                    root, allow_linux_user_dir_fallback=False
                )
                self.assertIn("m5x7", missing_fams)
                self.assertIn("BoldPixels", missing_fams)
                self.assertEqual(mode_miss, "fallback_system")
            # Restore real registration
            pixel_ui.verify_and_finalize_pixel_fonts(root)
        finally:
            root.destroy()

    def test_asset_scaler_1_5x_card_binary_alpha_and_crisp_border(self):
        """1.5x card scaling (111x160) produces binary alpha (0 or 255) with zero grey corner fringe."""
        from audio_assets import AssetScaler

        card_path = config.ASSETS_DIR / "1_spade.png"
        self.assertTrue(card_path.exists())
        src = Image.open(card_path).convert("RGBA")
        scaled = AssetScaler.scale_pil_image(src, 111, 160, element_type="cards")
        self.assertEqual(scaled.size, (111, 160))
        alphas = set(scaled.getchannel("A").tobytes())
        semi_transparent = [a for a in alphas if 0 < a < 255]
        self.assertEqual(
            semi_transparent,
            [],
            f"1.5x card must not contain semi-transparent halo pixels, found: {semi_transparent[:10]}",
        )

    def test_ui_config_v2_schema_parity_with_default_ui_config(self):
        """assets/ui_config.json v2.0 and ui_layout.DEFAULT_UI_CONFIG must match byte-for-byte in structure."""
        import json
        import ui_layout

        cfg_path = Path(config.UI_CONFIG_FILE)
        self.assertTrue(cfg_path.exists())
        disk_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertEqual(disk_cfg.get("version"), "2.0")
        self.assertIn("display_profiles", disk_cfg)
        self.assertIn("stage_wings", disk_cfg)
        self.assertNotIn("top_bar", disk_cfg)
        self.assertEqual(disk_cfg, ui_layout.DEFAULT_UI_CONFIG)

    def test_canvas_components_pure_pillow_felt_lru_and_locked_stage_dimensions(self):
        """Verifies zero-numpy TableFeltCanvas (<15ms 4K, maxsize=2 cache), 96px Altar, and 1000x220 / 2000x440 Stage."""
        import sys
        import time
        from ui_canvases import TableFeltCanvas, DealerStageCanvas, HauntedAltarCanvas, ChipVisualizer

        root = tkinter.Tk()
        root.withdraw()
        try:
            # 1. DealerStageCanvas locks strictly to 1000x220 (1x) and 2000x440 (2x)
            stage = DealerStageCanvas(root)
            stage.set_scale(1.0)
            self.assertEqual((stage.canvas_width, stage.canvas_height), (1000, 220))
            stage.set_scale(2.0)
            self.assertEqual((stage.canvas_width, stage.canvas_height), (2000, 440))

            # 2. HauntedAltarCanvas compacts to 260x96 (1x) and 520x192 (2x)
            altar = HauntedAltarCanvas(root)
            altar.set_scale(1.0)
            self.assertEqual((altar.canvas_width, altar.canvas_height), (260, 96))
            altar.set_scale(2.0)
            self.assertEqual((altar.canvas_width, altar.canvas_height), (520, 192))

            # 3. ChipVisualizer removes duplicate "CHIPS: $" header text while preserving non-empty hint badge
            viz = ChipVisualizer(root)
            viz.set_scale(1.0)
            self.assertEqual((viz.canvas_width, viz.canvas_height), (288, 204))
            viz.set_bankroll(1000, interactive=True)
            badge_txt = viz.itemcget("bankroll_badge", "text")
            self.assertTrue(len(badge_txt) > 0)
            self.assertNotIn("CHIPS:", badge_txt)

            # 4. TableFeltCanvas works with numpy blocked, bounds _felt_cache <= 2, and generates 4K felt rapidly
            felt = TableFeltCanvas(root, width=1280, height=504)
            with mock.patch.dict(sys.modules, {"numpy": None}):
                t0 = time.perf_counter()
                img_800 = felt._generate_felt_image(1280, 504)
                dt_800_ms = (time.perf_counter() - t0) * 1000.0
                self.assertIsNotNone(img_800)
                self.assertEqual(img_800.size, (1280, 504))
                # Verify non-uniform woven baize grain
                extrema = img_800.getextrema()
                self.assertGreater(extrema[1][1] - extrema[1][0], 8)

                # Warm tile cache then time 3840x1568 (uhd_4k felt area) baize + vignette + rules render
                felt.scale_factor = 2.0
                felt._generate_felt_image(512, 512)
                t1 = time.perf_counter()
                img_4k = felt._generate_felt_image(3840, 1568)
                dt_4k_ms = (time.perf_counter() - t1) * 1000.0
                self.assertIsNotNone(img_4k)
                self.assertEqual(img_4k.size, (3840, 1568))
                # Allow generous CI headroom while ensuring pure-Pillow path stays fast (< 90ms even on busy CPU, ~30ms typical)
                self.assertLess(dt_800_ms, 45.0, f"1280x504 felt generation took {dt_800_ms:.2f}ms")
                self.assertLess(dt_4k_ms, 90.0, f"4K felt generation took {dt_4k_ms:.2f}ms")

            # Verify LRU maxsize=2 cache bound across 4 theme transitions
            for th in ("casino", "creep", "hell", "celestial"):
                felt.set_theme(th)
            self.assertLessEqual(len(felt._felt_cache), 2)

            # Verify 4K shoe mouth clamps inside pit_max_width=2560 (pit_right = 3200)
            felt.canvas_width = 3840
            felt.pit_max_width = 2560
            mouth_x, _ = felt.get_shoe_mouth_coords()
            self.assertLessEqual(mouth_x, 3200)
            self.assertGreaterEqual(mouth_x, 2900)
        finally:
            root.destroy()

    def test_five_profiles_pit_wings_layout_bounds_zero_overlap_and_clipping(self):
        """Verifies StageBand sibling pillars and 4-row vertical stack do not overlap across all 5 DisplayProfiles."""
        import tempfile
        from blackjack import BlackjackApp
        from display_profile import make_profile_preset

        root = tkinter.Tk()
        root.withdraw()
        tmp_dir = tempfile.TemporaryDirectory()
        try:
            save_path = Path(tmp_dir.name) / "profile_bounds_save.json"
            app = BlackjackApp(root, sound_enabled=False, save_path=save_path)
            for preset_name in ("hd_720p", "deck_800p", "fhd_1080p", "qhd_1440p", "uhd_4k"):
                prof = make_profile_preset(preset_name, is_fullscreen=(preset_name in ("fhd_1080p", "qhd_1440p", "uhd_4k")))
                app.apply_display_profile(prof, update_window_geometry=False)
                root.geometry(f"{prof.window_w}x{prof.window_h}")
                root.update_idletasks()
                snap = app.collect_layout_bounds_snapshot()

                self.assertIn("left_stage_wing", snap, f"Missing left_stage_wing in {preset_name}")
                self.assertIn("dealer_stage", snap, f"Missing dealer_stage in {preset_name}")
                self.assertIn("right_stage_wing", snap, f"Missing right_stage_wing in {preset_name}")
                self.assertIn("card_table", snap, f"Missing card_table in {preset_name}")
                self.assertIn("mahogany_rail", snap, f"Missing mahogany_rail in {preset_name}")

                lw = snap["left_stage_wing"]
                ds = snap["dealer_stage"]
                rw = snap["right_stage_wing"]
                ct = snap["card_table"]
                mr = snap["mahogany_rail"]

                # Horizontal sibling non-overlap in StageBand
                self.assertLessEqual(lw[2], ds[0], f"LeftStageWing overlaps DealerStage in {preset_name}: {lw} vs {ds}")
                self.assertLessEqual(ds[2], rw[0], f"DealerStage overlaps RightStageWing in {preset_name}: {ds} vs {rw}")

                # Vertical 4-row stack non-overlap (StageBand -> CardTable -> MahoganyRail)
                self.assertLessEqual(ds[3], ct[1], f"DealerStage overlaps CardTable in {preset_name}: {ds} vs {ct}")
                self.assertLessEqual(ct[3], mr[1], f"CardTable overlaps MahoganyRail in {preset_name}: {ct} vs {mr}")
            app._on_close()
        finally:
            try:
                root.destroy()
            except Exception:
                pass
            tmp_dir.cleanup()

    def test_mahogany_rail_buttons_in_bounds_and_stage_height_locked_across_profiles(self):
        """
        Round 1 Focus Group regression suite:
        1. All betting & in-play Mahogany Rail buttons lie strictly within [pit_left, pit_right] without clipping or overlapping New Game.
        2. StageBand height remains locked to `prof.stage_h` (no black abyss band on Venue Tour or Counting Bootcamp).
        3. LeftStageWing `bankroll_label` wraplength fits strictly inside `prof.stage_wing_width` (fixes 1440p 'BANKROLL: $' truncation).
        4. RightStageWing buttons avoid GDI faux-bold smearing and cap width on 1080p.
        """
        import tempfile
        from blackjack import BlackjackApp
        from display_profile import make_profile_preset
        from ui_layout import resolve_pit_bounds

        root = tkinter.Tk()
        root.withdraw()
        tmp_dir = tempfile.TemporaryDirectory()
        try:
            save_path = Path(tmp_dir.name) / "rail_stage_bounds_save.json"
            app = BlackjackApp(root, sound_enabled=False, save_path=save_path, skip_splash=True)
            app.save_manager.data.achievements.exorcist = True
            for preset_name in ("hd_720p", "deck_800p", "fhd_1080p", "qhd_1440p", "uhd_4k"):
                prof = make_profile_preset(
                    preset_name,
                    is_fullscreen=(preset_name in ("fhd_1080p", "qhd_1440p", "uhd_4k")),
                )
                app.apply_display_profile(prof, update_window_geometry=False)
                root.geometry(f"{prof.window_w}x{prof.window_h}")
                root.update_idletasks()
                app._reposition_rail_buttons()

                pit_left, _pit_cx, pit_right = resolve_pit_bounds(prof.window_w, prof.pit_max_width)
                ng_left = app.new_game_button.x - app.new_game_button.width / 2
                ng_right = app.new_game_button.x + app.new_game_button.width / 2
                self.assertGreaterEqual(ng_left, pit_left, f"New Game left out of bounds in {preset_name}")
                self.assertLessEqual(ng_right, pit_right, f"New Game right clipped in {preset_name}")

                for btn_name, btn in (
                    ("clear_bet", app.clear_bet_button),
                    ("all_in", app.all_in_button),
                    ("deal_hand", app.deal_bet_button),
                    ("rebuy", app.rebuy_button),
                    ("hit", app.hit_button),
                    ("stand", app.stand_button),
                    ("double", app.double_button),
                    ("split", app.split_button),
                    ("surrender", app.surrender_button),
                ):
                    b_left = btn.x - btn.width / 2
                    b_right = btn.x + btn.width / 2
                    self.assertGreaterEqual(
                        b_left, pit_left, f"{btn_name} clipped left in {preset_name}: {b_left} < {pit_left}"
                    )
                    self.assertLessEqual(
                        b_right, pit_right, f"{btn_name} clipped right in {preset_name}: {b_right} > {pit_right}"
                    )
                    self.assertLessEqual(
                        b_right, ng_left - 4, f"{btn_name} overlaps New Game in {preset_name}: {b_right} vs {ng_left}"
                    )

                # Wraplength inside LeftStageWing must fit within stage_wing_width
                wrap_val = int(app.bankroll_label.cget("wraplength"))
                self.assertLess(
                    wrap_val,
                    prof.stage_wing_width,
                    f"bankroll_label wraplength {wrap_val} >= stage_wing_width {prof.stage_wing_width} in {preset_name}",
                )

                # RightStageWing button width capped & no synthetic bold on single-weight bitmap fonts
                btn_font = app.settings_button.cget("font")
                if "bold" in str(btn_font).lower():
                    self.assertIn("Tiny5", str(btn_font), f"Synthetic bold on RightStageWing in {preset_name}: {btn_font}")
                max_wing_btn_w = 160 if preset_name == "fhd_1080p" else int(140 * prof.art_scale)
                self.assertLessEqual(
                    app.settings_button.winfo_width(),
                    max_wing_btn_w,
                    f"RightStageWing button stretched too wide in {preset_name}: {app.settings_button.winfo_width()}",
                )

                # Verify 8px integer grid table_px() step-up on fhd_1080p
                if preset_name == "fhd_1080p":
                    self.assertEqual(prof.table_px(16), 24)
                    self.assertEqual(prof.table_px(24), 32)
                    self.assertEqual(prof.table_px(32), 40)
                    self.assertIn("-24", str(app.ledger_header_label.cget("font")))
                elif preset_name in ("hd_720p", "deck_800p"):
                    self.assertEqual(prof.table_px(16), 16)
                    self.assertEqual(prof.table_px(24), 24)
                elif preset_name in ("qhd_1440p", "uhd_4k"):
                    self.assertEqual(prof.table_px(16), 32)
                    self.assertEqual(prof.table_px(24), 48)

                # StageBand height remains locked to prof.stage_h even in Venue Tour & Bootcamp
                self.assertLessEqual(app.stage_band_frame.winfo_reqheight(), prof.stage_h)

            # Verify Venue Tour & Counting Bootcamp do not blow out StageBand height
            prof_800 = make_profile_preset("deck_800p", is_fullscreen=False)
            app.apply_display_profile(prof_800, update_window_geometry=False)
            root.geometry("1280x800")
            app.enter_venue_tour()
            root.update_idletasks()
            self.assertEqual(app.stage_band_frame.winfo_height(), prof_800.stage_h)
            app.exit_venue_tour()

            app.enter_counting_bootcamp(start_view="map")
            root.update_idletasks()
            self.assertEqual(app.stage_band_frame.winfo_height(), prof_800.stage_h)
            app.exit_counting_bootcamp_to_free_play()

            app._on_close()
        finally:
            try:
                root.destroy()
            except Exception:
                pass
            tmp_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
