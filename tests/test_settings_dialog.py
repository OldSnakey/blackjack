"""
Unit test suite for Settings Dialog and Clear Save File confirmation flow.

Validates:
- Settings button initialization and placement in scoreboard_frame.
- SettingsDialog lifecycle (creation, layout, clean dismissal).
- Clear save confirmation prompt behavior:
  - User cancellation preserves existing save data and unlocks.
  - User confirmation clears save data to blank slate and relocks cursed stakes.
- Hotkey binding for Settings (O key).
"""

from __future__ import annotations

import tempfile
import unittest
import tkinter
from pathlib import Path
from unittest.mock import patch

from save_manager import SaveManager
import config
import blackjack
from blackjack import BlackjackApp, TABLE_BACKGROUND_COLOR, PANEL_BACKGROUND_COLOR, Phase


class TestSettingsDialog(unittest.TestCase):
    """Verifies SettingsDialog and Clear Save File confirmation handling."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.test_dir = tempfile.mkdtemp()
        self.test_save_file = Path(self.test_dir) / "test_save.json"

        # Instantiate app with custom save path for testing isolation
        self.app = BlackjackApp(self.root, sound_enabled=False, save_path=self.test_save_file)

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_settings_button_presence_in_scoreboard(self):
        """Settings button is present on right_stage_wing Salon Menu."""
        self.assertTrue(hasattr(self.app, "settings_button"))
        self.assertEqual(self.app.settings_button.master, self.app.right_stage_wing)
        info = self.app.settings_button.grid_info()
        self.assertEqual(info["row"], 1)
        self.assertEqual(info["column"], 0)

    def test_settings_dialog_lifecycle(self):
        """Settings dialog opens as modal, renders controls, and closes cleanly."""
        self.assertIsNone(self.app._settings_dialog)
        self.app._open_settings_dialog()
        self.assertIsNotNone(self.app._settings_dialog)
        self.assertTrue(self.app._settings_dialog.winfo_exists())

        # Close dialog
        self.app._close_settings_dialog()
        self.assertIsNone(self.app._settings_dialog)

    def test_clear_save_cancelled_preserves_data(self):
        """When user declines the confirmation prompt, save data and unlocks are untouched."""
        # Setup: unlock exorcist and record a high bankroll
        self.app.save_manager.record_bankroll(15000)
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.haunted.unlocked_cursed_stakes = True
        self.app.cursed_stakes_button.grid()
        self.root.update_idletasks()

        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Mock confirmation prompt returning False (User clicks "Cancel" / "No")
        with patch.object(dialog, "_ask_confirm_clear_save", return_value=False):
            dialog._on_click_clear_save()

        # Data must remain intact
        self.assertEqual(self.app.save_manager.data.highscores.peak_bankroll, 15000)
        self.assertTrue(self.app.save_manager.data.achievements.exorcist)
        self.assertTrue(bool(self.app.cursed_stakes_button.grid_info()))

    def test_clear_save_confirmed_resets_to_blank_slate(self):
        """When user confirms the irreversible prompt, save data is wiped and cursed stakes locked."""
        # Setup: unlock exorcist, record high bankroll, show cursed stakes
        self.app.save_manager.record_bankroll(20000)
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.haunted.unlocked_cursed_stakes = True
        self.app.cursed_stakes_button.grid()
        self.root.update_idletasks()

        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Mock confirmation prompt returning True (User confirms "Yes, Clear")
        with patch.object(dialog, "_ask_confirm_clear_save", return_value=True):
            dialog._on_click_clear_save()

        # Verify blank slate
        self.assertEqual(self.app.save_manager.data.highscores.peak_bankroll, 1000)
        self.assertFalse(self.app.save_manager.data.achievements.exorcist)
        self.assertFalse(self.app.haunted.unlocked_cursed_stakes)
        # Cursed stakes button must be removed from grid
        self.assertFalse(bool(self.app.cursed_stakes_button.grid_info()))

    def test_settings_dialog_button_grid_layout(self):
        """Settings buttons are organized in two tiers with sufficient width (no truncation) and retired dealer_btn."""
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Check preference buttons exist (scale_btn and dealer_btn retired; display controls added)
        self.assertTrue(hasattr(dialog, "sound_btn"))
        self.assertFalse(hasattr(dialog, "scale_btn"))
        self.assertFalse(hasattr(dialog, "dealer_btn"))
        self.assertTrue(hasattr(dialog, "wardrobe_btn"))
        self.assertTrue(hasattr(dialog, "card_scale_btn"))
        self.assertTrue(hasattr(dialog, "window_size_btn"))
        self.assertTrue(hasattr(dialog, "fullscreen_btn"))
        self.assertTrue(hasattr(dialog, "diagnostics_lbl"))
        self.assertTrue(hasattr(dialog, "voice_btn"))

        # Verify buttons are mapped and rendered width is not squished (all buttons >= 100px actual width)
        dialog.update()
        for btn in (
            dialog.sound_btn,
            dialog.voice_btn,
            dialog.wardrobe_btn,
            dialog.card_scale_btn,
            dialog.window_size_btn,
            dialog.fullscreen_btn,
        ):
            w = btn.winfo_width()
            self.assertGreaterEqual(w, 100, f"Button {btn} actual width {w} is too narrow and will truncate text")

        self.app._close_settings_dialog()

    def test_dealer_view_retired_and_display_profile_controls_persist(self):
        """_on_toggle_dealer_view is a safe no-op; Card Scale and Window Size controls persist and re-apply profile."""
        # Dealer stage stays permanently ON
        self.assertTrue(self.app.dealer_view_var.get())
        self.app._on_toggle_dealer_view()
        self.assertTrue(self.app.dealer_view_var.get())
        self.assertTrue(bool(self.app.dealer_stage_frame.grid_info()))
        self.assertTrue(bool(self.app.horizon_rail.grid_info()))

        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Toggle strict_integer_cards via card_scale_btn
        self.assertFalse(self.app.save_manager.data.strict_integer_cards)
        dialog.card_scale_btn.invoke()
        self.assertTrue(self.app.save_manager.data.strict_integer_cards)
        self.assertIn("1x Crisp", dialog.card_scale_btn.cget("text"))

        # Window Mode button label clearly reads "Window Mode:" and opens in-window picker modal
        self.assertEqual(self.app.save_manager.data.window_profile_override, "auto")
        self.assertIn("Window Mode:", dialog.window_size_btn.cget("text"))
        dialog.window_size_btn.invoke()
        picker = getattr(dialog, "_window_mode_picker", None)
        self.assertIsNotNone(picker, "Clicking Window Mode button must open in-window picker modal")
        self.assertIsInstance(picker, tkinter.Frame)
        self.assertNotIsInstance(picker, tkinter.Toplevel)

        # Select 1280x720 (hd_720p) inside picker
        picker.select_option("hd_720p")
        self.assertEqual(self.app.save_manager.data.window_profile_override, "hd_720p")
        self.assertEqual(self.app.display_profile.name, "hd_720p")
        self.assertIn("720p", dialog.window_size_btn.cget("text"))

        # Diagnostics label includes profile name and resolution
        diag_txt = dialog.diagnostics_lbl.cget("text")
        self.assertIn("hd_720p", diag_txt)
        self.assertIn("1280x720", diag_txt)

        self.app._close_settings_dialog()

    def test_window_mode_picker_exits_fullscreen_and_disables_oversized_options(self):
        """Picking a windowed mode while in fullscreen exits fullscreen; oversized tiers are disabled in picker."""
        from unittest import mock
        from display_profile import DisplayEnvironmentProbe

        probe_1080 = DisplayEnvironmentProbe(
            monitor_wh=(1920, 1080),
            usable_workarea_wh=(1920, 1030),
            is_steam_deck=False,
            is_gamescope=False,
        )
        with mock.patch("blackjack.probe_display_environment", return_value=probe_1080), mock.patch(
            "ui_dialogs.probe_display_environment", return_value=probe_1080
        ):
            self.app._open_settings_dialog()
            dialog = self.app._settings_dialog
            self.assertIsNotNone(dialog)

            # Simulate currently in fullscreen
            self.app._is_fullscreen = True
            dialog._refresh_display_controls()
            self.assertIn("Fullscreen", dialog.window_size_btn.cget("text"))

            # Open picker and verify 1080p & 1440p windowed options are disabled on 1920x1030 work area
            dialog.window_size_btn.invoke()
            picker = dialog._window_mode_picker
            self.assertIsNotNone(picker)
            self.assertFalse(picker.is_option_enabled("fhd_1080p"))
            self.assertFalse(picker.is_option_enabled("qhd_1440p"))
            self.assertTrue(picker.is_option_enabled("hd_720p"))
            self.assertTrue(picker.is_option_enabled("auto"))

            # Picking hd_720p exits fullscreen and applies hd_720p
            picker.select_option("hd_720p")
            self.assertFalse(self.app._is_fullscreen)
            self.assertEqual(self.app.save_manager.data.window_profile_override, "hd_720p")
            self.assertEqual(self.app.display_profile.name, "hd_720p")

            # Picking auto restores auto override
            dialog.window_size_btn.invoke()
            dialog._window_mode_picker.select_option("auto")
            self.assertEqual(self.app.save_manager.data.window_profile_override, "auto")
            self.assertEqual(self.app.display_profile.name, "deck_800p")

            self.app._close_settings_dialog()

    def test_settings_dialog_displays_card_counting_streak(self):
        """Settings dialog displays card counting drill streak in career records."""
        self.app.save_manager.data.highscores.best_counting_streak = 14
        self.app.save_manager.data.highscores.counting_streak = 8
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Verify stats labels contain counting streak info
        labels_text = " ".join(
            w.cget("text") for w in dialog.stats_frame.winfo_children() if isinstance(w, tkinter.Label)
        )
        self.assertIn("Counting", labels_text)
        self.assertIn("14", labels_text)

        self.app._close_settings_dialog()

    def test_settings_dialog_scrollable_container_and_screen_clamping(self):
        """Settings screen mounts in-window at 100% viewport size with adaptive scroll safety and zero Toplevels."""
        self.root.geometry("1280x800")
        self.root.update_idletasks()
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)
        self.assertIsInstance(dialog, tkinter.Frame)
        self.assertNotIsInstance(dialog, tkinter.Toplevel)
        self.assertTrue(hasattr(dialog, "_on_mousewheel") or hasattr(dialog, "canvas"))

        dialog.update_idletasks()
        dialog.update()
        size_part = dialog.geometry().split("+")[0]
        w, h = map(int, size_part.split("x"))
        self.assertEqual((w, h), (1280, 800))

        # Both Tab 0 and Tab 1 (House Rules) fit without vertical scrollbar on 1280x800 and 1280x720
        for tab_idx in (0, 1):
            dialog._switch_tab(tab_idx)
            dialog.update_idletasks()
            dialog.update()
            self.assertFalse(
                bool(dialog.v_scrollbar.winfo_manager()),
                f"Tab {tab_idx} mapped vertical scrollbar on 1280x800 full-screen Settings",
            )

        # Pressing background betting/deal hotkeys while Settings is open must not mutate bets or deal
        bet_before = self.app.current_bet_var.get()
        self.app._on_key_chip(100, "3")
        self.app._on_key_deal_or_hit()
        self.assertEqual(self.app.current_bet_var.get(), bet_before)
        self.assertEqual(len(self.app.player_hand), 0)

        self.app._close_settings_dialog()


    def test_settings_dialog_dimensions_and_font_sizes(self):
        """Settings dialog window width and height are expanded and font sizes are increased by 2pts."""
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)
        dialog.update_idletasks()

        # Geometry checks (expanded width and height)
        geom = dialog.geometry()
        size_part = geom.split("+")[0]
        w, h = map(int, size_part.split("x"))
        self.assertGreaterEqual(w, 600)
        self.assertGreaterEqual(h, 600)

        # Font checks (native m6x11plus >= 18px at 1x, >= 32px at 2x)
        btn_font = dialog.sound_btn.cget("font")
        font_size = btn_font[1] if isinstance(btn_font, (tuple, list)) else int(str(btn_font).split()[1])
        self.assertGreaterEqual(abs(font_size), 18)

        self.app._close_settings_dialog()

    def test_settings_fhd_1080p_2x_crunchy_fonts_zero_scroll_and_confirm_modal_keys(self):
        """1920x1080 SettingsDialog uses 2x crunchy fonts with zero scrollbars, and InWindowConfirmModal supports Left/Right/Return."""
        from display_profile import make_profile_preset
        from ui_dialogs import InWindowConfirmModal

        self.app.apply_display_profile(make_profile_preset("fhd_1080p"))
        self.root.geometry("1920x1080")
        self.root.update_idletasks()

        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)
        try:
            dialog.update_idletasks()
            dialog.update()
            self.assertEqual(dialog.menu_scale, 2)
            btn_parts = dialog.tk.splitlist(dialog.sound_btn.cget("font"))
            self.assertGreaterEqual(abs(int(btn_parts[1])), 32)

            for tab_idx in (0, 1):
                dialog._switch_tab(tab_idx)
                dialog.update_idletasks()
                dialog.update()
                self.assertFalse(
                    bool(dialog.v_scrollbar.winfo_manager()),
                    f"1080p Settings Tab {tab_idx} mapped unexpected vertical scrollbar",
                )

            # Test non-blocking keyboard navigation on InWindowConfirmModal via internal key handler
            chosen = []
            def _spawn_and_confirm():
                pass
            dialog.after(20, lambda: (
                dialog._active_confirm_key("Right"),
                dialog._active_confirm_key("Return"),
            ))
            res = InWindowConfirmModal.ask_yes_no(dialog, "Confirm Test", "Proceed with reset?")
            chosen.append(res)
            self.assertEqual(chosen, [True])
        finally:
            if self.app._settings_dialog is not None:
                self.app._close_settings_dialog()

    def test_bottom_action_buttons_done_and_reset_data(self):
        """Bottom action area presents a green 'Done' button and a red 'Reset Data' button beside it."""
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Both buttons must exist
        self.assertTrue(hasattr(dialog, "done_btn"))
        self.assertTrue(hasattr(dialog, "clear_save_btn"))

        # Verify Done button is green and has "Done" in text
        self.assertIn("Done", dialog.done_btn.cget("text"))
        self.assertEqual(dialog.done_btn.cget("background"), "#2e7d32")

        # Verify Reset Data button is red and has "Reset Data" in text
        self.assertIn("Reset Data", dialog.clear_save_btn.cget("text"))
        self.assertEqual(dialog.clear_save_btn.cget("background"), "#b71c1c")

        # Both buttons must share the same parent row frame and be side-by-side
        self.assertEqual(dialog.done_btn.master, dialog.clear_save_btn.master)
        done_info = dialog.done_btn.grid_info()
        reset_info = dialog.clear_save_btn.grid_info()
        self.assertEqual(done_info["row"], reset_info["row"])
        self.assertNotEqual(done_info["column"], reset_info["column"])

        # Tab 0 fits without mapping vertical scrollbar on standard 800p display
        dialog._switch_tab(0)
        dialog.update_idletasks()
        if self.root.winfo_screenheight() >= 768:
            self.assertFalse(bool(dialog.v_scrollbar.winfo_manager()))

        self.app._close_settings_dialog()


if __name__ == "__main__":
    unittest.main()

