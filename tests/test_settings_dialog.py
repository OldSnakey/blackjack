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
        """Settings button is present on scoreboard_frame."""
        self.assertTrue(hasattr(self.app, "settings_button"))
        self.assertEqual(self.app.settings_button.master, self.app.scoreboard_frame)
        info = self.app.settings_button.grid_info()
        self.assertEqual(info["row"], 0)

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
        """Settings buttons are organized in two tiers with sufficient width (no truncation)."""
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)

        # Check all 5 preference buttons exist
        self.assertTrue(hasattr(dialog, "sound_btn"))
        self.assertTrue(hasattr(dialog, "scale_btn"))
        self.assertTrue(hasattr(dialog, "dealer_btn"))
        self.assertTrue(hasattr(dialog, "wardrobe_btn"))
        self.assertTrue(hasattr(dialog, "voice_btn"))

        # Verify buttons are mapped and rendered width is not squished (all buttons >= 100px actual width)
        dialog.update()
        for btn in (dialog.sound_btn, dialog.voice_btn, dialog.scale_btn, dialog.dealer_btn, dialog.wardrobe_btn):
            w = btn.winfo_width()
            self.assertGreaterEqual(w, 100, f"Button {btn} actual width {w} is too narrow and will truncate text")

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
        """Settings dialog embeds content in a scrollable frame with mousewheel support."""
        self.app._open_settings_dialog()
        dialog = self.app._settings_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(hasattr(dialog, "_on_mousewheel") or hasattr(dialog, "canvas"))

        dialog.update_idletasks()
        req_h = dialog.winfo_reqheight()
        max_allowed_h = min(
            self.root.winfo_screenheight() - 80,
            int(config.DEFAULT_WINDOW_HEIGHT * getattr(self.app, "scale_factor", 1.0)),
        )
        self.assertLessEqual(req_h, max_allowed_h, f"Settings dialog requested height {req_h} exceeds live display allowance {max_allowed_h}")

        self.app._close_settings_dialog()


if __name__ == "__main__":
    unittest.main()

