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
        """Root window must be frozen non-resizable with minsize at default dimensions."""
        resizable = self.root.resizable()
        self.assertIn(resizable, ((0, 0), (False, False)))
        minsize = self.root.minsize()
        self.assertEqual(minsize, (DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT))

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
        """Fullscreen mode toggles root fullscreen cleanly without altering 1.0x scale factor."""
        self.assertEqual(self.app.scale_factor, 1.0)

        # Enter Fullscreen
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.assertTrue(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.fullscreen_status_var.get(), "🗗 Window")
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertEqual(self.app.card_width, CARD_WIDTH)

        # Exit Fullscreen via toggle
        self.app.toggle_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        self.assertFalse(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.fullscreen_status_var.get(), "⛶ Full")
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertEqual(self.app.card_width, CARD_WIDTH)

        # Exit Fullscreen via exit_fullscreen helper (Escape key handler)
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.assertEqual(self.app.scale_factor, 1.0)
        self.app.exit_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        self.assertFalse(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.scale_factor, 1.0)

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
