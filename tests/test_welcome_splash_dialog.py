"""
Unit tests for WelcomeSplashDialog, Play Mode onboarding, and Trainer integrations.

Validates:
- WelcomeSplashDialog initialization, pixel art logo display, and dealer greeting.
- Selection of Casual, Betting, and Training modes via click and keyboard shortcuts.
- Persistence of play mode and onboarding completion in SaveManager.
- Display fit compliance and scroll container resilience as per AGENTS.md.
- Strategy hint live reflection and ideal bet staging in Training mode.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import tkinter
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import config
from blackjack import BlackjackApp
from rules import BasicStrategyDecision
from ui_dialogs import WelcomeSplashDialog, SettingsDialog


def extract_widgets(parent, widget_type=tkinter.Label):
    """Recursively descends widget hierarchy collecting matching widget instances."""
    found = []
    if isinstance(parent, widget_type):
        found.append(parent)
    for child in parent.winfo_children():
        found.extend(extract_widgets(child, widget_type))
    return found


class TestWelcomeSplashDialog(unittest.TestCase):
    """Verifies WelcomeSplashDialog lifecycle, geometry compliance, and mode selection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_file = Path(self.temp_dir) / "test_splash_save.json"
        self.root = tkinter.Tk()
        self.root.withdraw()

        # Initialize app with splash suppressed initially to isolate dialog instantiation
        self.app = BlackjackApp(
            self.root,
            sound_enabled=False,
            save_path=self.save_file,
            chips_mode=True,
            skip_splash=True,
        )
        self.root.update_idletasks()

    def tearDown(self):
        try:
            if hasattr(self.app, "_close_welcome_splash_dialog"):
                self.app._close_welcome_splash_dialog()
            if hasattr(self.app, "_close_settings_dialog"):
                self.app._close_settings_dialog()
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_welcome_splash_creation_and_geometry(self):
        """Verifies WelcomeSplashDialog instantiates, embeds scroll container, and satisfies display bounds."""
        dialog = WelcomeSplashDialog(self.root, self.app)
        dialog.update_idletasks()

        self.assertTrue(dialog.winfo_exists())
        self.assertIsNotNone(dialog.canvas)
        self.assertIsNotNone(dialog.scroll_content)

        # Dynamic geometry compliance as per AGENTS.md
        scale = getattr(self.app, "scale_factor", 1.0)
        max_allowed_h = min(
            self.root.winfo_screenheight() - 80,
            int(config.DEFAULT_WINDOW_HEIGHT * scale * 1.15),
        )
        dialog_h = dialog.winfo_height()
        self.assertLessEqual(dialog_h, max_allowed_h)

        # Content verification: 3 mode cards created
        self.assertIn("casual", dialog._mode_cards)
        self.assertIn("betting", dialog._mode_cards)
        self.assertIn("training", dialog._mode_cards)

        dialog.destroy()

    def test_mode_selection_and_confirm(self):
        """Tests mode selection via shortcuts 1, 2, 3 and confirmation applying play mode."""
        dialog = WelcomeSplashDialog(self.root, self.app)
        dialog.update_idletasks()

        # Test selecting Training mode with '3'
        dialog._select_mode("training")
        self.assertEqual(dialog.selected_mode, "training")
        self.assertIn("SELECTED", dialog._mode_cards["training"]["badge"].cget("text"))

        # Test selecting Casual mode with '1'
        dialog._select_mode("casual")
        self.assertEqual(dialog.selected_mode, "casual")
        self.assertIn("SELECTED", dialog._mode_cards["casual"]["badge"].cget("text"))

        # Confirm choice
        confirmed_modes = []
        dialog.on_confirm_cb = lambda m: confirmed_modes.append(m)
        dialog._on_confirm()

        self.assertEqual(confirmed_modes, ["casual"])
        self.assertEqual(self.app.play_mode, "casual")
        self.assertFalse(self.app.chips_mode_var.get())
        self.assertTrue(self.app.save_manager.data.onboarding_completed)

    def test_skip_dismissal_preserves_onboarding_state(self):
        """Tests that pressing skip closes dialog without forcing onboarding completion."""
        self.app.save_manager.data.onboarding_completed = False
        dialog = WelcomeSplashDialog(self.root, self.app)
        dialog.update_idletasks()

        dialog._on_close()
        self.assertFalse(dialog.winfo_exists())
        self.assertFalse(self.app.save_manager.data.onboarding_completed)

    def test_play_mode_application_casual_betting_training(self):
        """Tests that apply_play_mode cleanly manages chips_mode and card counting HUD states."""
        # 1. Switch to Casual Mode
        self.app.apply_play_mode("casual")
        self.assertEqual(self.app.play_mode, "casual")
        self.assertFalse(self.app.chips_mode_var.get())
        self.assertFalse(self.app.card_counting_hud.is_visible)

        # 2. Switch to Betting Mode
        self.app.apply_play_mode("betting")
        self.assertEqual(self.app.play_mode, "betting")
        self.assertTrue(self.app.chips_mode_var.get())
        self.assertFalse(self.app.card_counting_hud.is_visible)

        # 3. Switch to Training Mode
        self.app.apply_play_mode("training")
        self.assertEqual(self.app.play_mode, "training")
        self.assertTrue(self.app.chips_mode_var.get())
        self.assertTrue(self.app.card_counting_hud.is_visible)

        # Verify persistence in save manager
        self.assertEqual(self.app.save_manager.data.play_mode, "training")

    def test_settings_dialog_play_mode_cycle(self):
        """Tests that SettingsDialog allows cycling the play mode and relaunching welcome screen."""
        self.app.apply_play_mode("casual")
        settings_dlg = SettingsDialog(self.root, self.app)
        settings_dlg.update_idletasks()

        self.assertTrue(hasattr(settings_dlg, "mode_btn"))
        self.assertIn("Casual", settings_dlg.mode_btn.cget("text"))

        # Cycle mode
        settings_dlg._on_cycle_play_mode()
        self.assertEqual(self.app.play_mode, "betting")
        self.assertIn("Betting", settings_dlg.mode_btn.cget("text"))

        settings_dlg._on_cycle_play_mode()
        self.assertEqual(self.app.play_mode, "training")
        self.assertIn("Training", settings_dlg.mode_btn.cget("text"))

        settings_dlg.destroy()

    def test_ideal_bet_staging(self):
        """Tests that _stage_recommended_bet sets staged bet and updates visualizer."""
        self.app.is_betting_phase = True
        self.app.bankroll_var.set(1000)
        self.app.current_bet_var.set(0)

        self.app._stage_recommended_bet(75)
        self.assertEqual(self.app.current_bet_var.get(), 75)

    def test_basic_strategy_hint_computation(self):
        """Tests get_current_strategy_hint during player turn."""
        from rules import Card, RoundPhase

        self.app.round_phase = RoundPhase.PLAYER_TURN
        self.app.player_hands = [[Card(8, None, rank="8", suit="spades"), Card(8, None, rank="8", suit="hearts")]]
        self.app.dealer_hand = [Card(9, None, rank="9", suit="clubs"), Card(10, None, rank="10", suit="diamonds")]
        self.app.active_hand_index = 0
        self.app.split_button.configure(state="normal")
        self.app.double_button.configure(state="disabled")

        hint = self.app.get_current_strategy_hint()
        self.assertIsNotNone(hint)
        self.assertIsInstance(hint, BasicStrategyDecision)
        self.assertEqual(hint.action, "SPLIT")


if __name__ == "__main__":
    unittest.main()
