"""
Unit test suite for Display Modes: Frozen Window Resizing, Fullscreen, and Scale Removal.

Validates:
- Window size is frozen non-resizable (resizable(False, False)).
- Window minsize is set to (DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT).
- Scale button is removed / unmapped from the header top bar.
- Scale factor remains fixed at 1.0 (toggle_scale_mode is a safe no-op).
- Native Tkinter Fullscreen toggle (F11) operates cleanly at 1.0x scale.
- Shortcuts HUD overlay displays Fullscreen (F11) and omits Scale 1x / 2x.
"""

from __future__ import annotations

import unittest
import tkinter
from pathlib import Path

import blackjack
from blackjack import (
    BlackjackApp,
    Card,
    CARD_WIDTH,
    CARD_HEIGHT,
    PLAYER_CARD_OVERLAP_OFFSET,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
)


class TestScaleAndDisplayModes(unittest.TestCase):
    """Verifies frozen window size, fixed 1.0x scale mode, and F11 Fullscreen mode."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root, sound_enabled=False)

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_window_size_frozen_non_resizable(self):
        """Root window must be frozen non-resizable with minsize matching active DisplayProfile."""
        resizable = self.root.resizable()
        self.assertIn(resizable, ((0, 0), (False, False)))
        minsize = self.root.minsize()
        prof = self.app.display_profile
        self.assertEqual(minsize, (prof.window_w, prof.window_h))
        self.assertEqual(prof.window_w, DEFAULT_WINDOW_WIDTH)
        self.assertIn(prof.window_h, (DEFAULT_WINDOW_HEIGHT, 720))

    def test_scale_button_unmapped_from_header(self):
        """Scale button must be unmapped from visible header grid."""
        self.assertFalse(
            bool(self.app.scale_button.grid_info()),
            "Scale button should not be gridded in top bar"
        )

    def test_initial_scale_and_display_state(self):
        """Newly created BlackjackApp must start in 1x scale mode and windowed display."""
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertFalse(self.app.is_fullscreen)
        self.assertEqual(self.app.fullscreen_status_var.get(), "⛶ Full")
        self.assertEqual(self.app.card_width, CARD_WIDTH)
        self.assertEqual(self.app.card_height, CARD_HEIGHT)
        self.assertEqual(self.app.card_overlap_offset, PLAYER_CARD_OVERLAP_OFFSET)

    def test_toggle_scale_mode_is_safe_noop(self):
        """toggle_scale_mode must be a safe no-op that preserves 1.0x scale factor and dimensions."""
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertEqual(self.app.card_width, CARD_WIDTH)
        self.assertEqual(self.app.card_height, CARD_HEIGHT)
        self.assertEqual(self.app.card_overlap_offset, PLAYER_CARD_OVERLAP_OFFSET)

    def test_fullscreen_toggle_and_exit(self):
        """Fullscreen mode switches DisplayProfile cleanly, unlocks resizable for X11, and restores windowed mode."""
        from display_profile import make_profile_preset

        self.assertEqual(self.app.scale_factor, 1.0)
        windowed_prof = self.app.display_profile

        # Enter Fullscreen
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.assertTrue(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.fullscreen_status_var.get(), "🗗 Window")
        self.assertIn(self.app.display_profile.art_scale, (1, 2))
        self.assertEqual(self.app.card_width, self.app.display_profile.card_width)

        # Exit Fullscreen via toggle
        self.app.toggle_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        self.assertFalse(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.fullscreen_status_var.get(), "⛶ Full")
        self.assertEqual(self.app.display_profile.name, windowed_prof.name)
        self.assertEqual(self.app.card_width, windowed_prof.card_width)
        self.assertIn(self.root.resizable(), ((0, 0), (False, False)))

        # Exit Fullscreen via exit_fullscreen helper (Escape key handler)
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.app.exit_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        self.assertFalse(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.display_profile.name, windowed_prof.name)

        # Mid-hand atomic profile switch preserves active split hands, bets, and button state
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app._add_chip_bet(25)
        c8_h = Card(8, self.app.all_cards[0].image, rank="8", suit="heart")
        c8_s = Card(8, self.app.all_cards[0].image, rank="8", suit="spade")
        c6_d = Card(6, self.app.all_cards[0].image, rank="6", suit="diamond")
        c5_c = Card(5, self.app.all_cards[0].image, rank="5", suit="club")
        self.app.deck.extend([c5_c, c6_d, c5_c, c6_d, c8_s, c8_h])
        self.app._deal_hand_with_bet()
        self.app.on_split()
        self.assertEqual(len(self.app.player_hands), 2)
        bets_before = list(self.app.hand_bets)
        phase_before = self.app.fsm.phase

        prof_1440 = make_profile_preset("qhd_1440p", is_fullscreen=False)
        self.app.apply_display_profile(prof_1440, update_window_geometry=False)
        self.assertEqual(len(self.app.player_hands), 2)
        self.assertEqual(list(self.app.hand_bets), bets_before)
        self.assertEqual(self.app.fsm.phase, phase_before)
        self.assertEqual(self.app.player_hands[0][0].image.width(), 148)
        self.assertEqual(self.app.player_hands[0][0].image.height(), 214)

        self.app.apply_display_profile(windowed_prof, update_window_geometry=False)
        self.assertEqual(self.app.player_hands[0][0].image.width(), CARD_WIDTH)

    def test_shortcuts_dialog_registers_f11_and_omits_scale(self):
        """Shortcuts HUD overlay dialog must display F11 Fullscreen entry and omit Scale 1x/2x."""
        self.app._toggle_shortcuts_overlay()
        self.root.update_idletasks()

        dlg = getattr(self.app, "_shortcuts_dialog", None)
        self.assertIsNotNone(dlg)

        # Inspect shortcut text inside dialog frames recursively
        def extract_labels(w):
            texts = []
            if isinstance(w, tkinter.Label):
                texts.append(str(w.cget("text")))
            for ch in w.winfo_children():
                texts.extend(extract_labels(ch))
            return texts

        labels_text = []
        if hasattr(dlg, "_switch_tab"):
            for tab_idx in (0, 1):
                dlg._switch_tab(tab_idx)
                for w in dlg.winfo_children():
                    labels_text.extend(extract_labels(w))
        else:
            for w in dlg.winfo_children():
                labels_text.extend(extract_labels(w))

        has_scale_shortcut = any("Scale 1x / 2x" in t for t in labels_text)
        has_full_shortcut = any("Fullscreen" in t for t in labels_text)

        self.assertFalse(has_scale_shortcut, "Shortcuts HUD must not include Scale 1x / 2x shortcut")
        self.assertTrue(has_full_shortcut, "Shortcuts HUD must include Fullscreen shortcut")

        self.app._close_shortcuts_overlay()


if __name__ == "__main__":
    unittest.main()
