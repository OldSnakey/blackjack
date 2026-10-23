"""
Unit test suite for the Keyboard Shortcut Informational Overlay in Blackjack.

Validates:
- Presence and loadability of curated Kenney icon assets in assets/overlay_icons.
- KeyboardIconLoader caching, scaling, and graceful missing-asset handling.
- Help button widget initialization and layout presence on the scoreboard bar.
- Overlay dialog lifecycle (creation, positioning, modal properties, clean destruction).
- Dismissal via keyboard events (Escape, question mark, F1).
- Strict game state immutability when opening/closing the overlay.
"""

from __future__ import annotations

import unittest
import tkinter
from pathlib import Path

from blackjack import (
    BASE_DIR,
    OVERLAY_ICONS_DIR,
    KeyboardIconLoader,
    BlackjackApp,
    Card,
)
import config


class TestKeyboardOverlayAssets(unittest.TestCase):
    """Verifies that all required shortcut prompt PNG sprites exist and load correctly."""

    REQUIRED_ICONS = [
        "keyboard_question.png",
        "keyboard_f1.png",
        "keyboard_space.png",
        "keyboard_enter.png",
        "keyboard_h.png",
        "keyboard_s.png",
        "keyboard_d.png",
        "keyboard_p.png",
        "keyboard_r.png",
        "keyboard_1.png",
        "keyboard_2.png",
        "keyboard_3.png",
        "keyboard_4.png",
        "keyboard_5.png",
        "keyboard_a.png",
        "keyboard_c.png",
        "keyboard_y.png",
        "keyboard_n.png",
        "keyboard_escape.png",
        "keyboard_m.png",
        "keyboard_k.png",
        "keyboard_shift.png",
        "keyboard_v.png",
        "keyboard_x.png",
        "keyboard_f10.png",
        "keyboard_f11.png",
        "mouse_left.png",
    ]

    def test_curated_icons_exist_on_disk(self):
        """Every curated icon required by the overlay must exist in assets/overlay_icons."""
        self.assertTrue(
            OVERLAY_ICONS_DIR.exists(),
            f"Directory {OVERLAY_ICONS_DIR} does not exist",
        )
        for icon_file in self.REQUIRED_ICONS:
            path = OVERLAY_ICONS_DIR / icon_file
            self.assertTrue(path.exists(), f"Missing required icon: {icon_file}")

    def test_icon_loader_caching_and_scaling(self):
        """KeyboardIconLoader should correctly scale and cache PhotoImage instances."""
        root = tkinter.Tk()
        root.withdraw()
        try:
            loader = KeyboardIconLoader(OVERLAY_ICONS_DIR)

            # Test 32x32 scaled icon (scale_div=2)
            img_32 = loader.get_icon("keyboard_space", scale_div=2)
            self.assertIsNotNone(img_32)
            self.assertEqual(img_32.width(), 32)
            self.assertEqual(img_32.height(), 32)

            # Test cache identity
            img_32_cached = loader.get_icon("keyboard_space", scale_div=2)
            self.assertIs(img_32, img_32_cached)

            # Test 22x22 scaled icon (scale_div=3)
            img_22 = loader.get_icon("keyboard_question", scale_div=3)
            self.assertIsNotNone(img_22)
            self.assertEqual(img_22.width(), 22)
            self.assertEqual(img_22.height(), 22)

            # Test missing icon returns None gracefully without throwing
            missing_img = loader.get_icon("keyboard_nonexistent_key_xyz", scale_div=2)
            self.assertIsNone(missing_img)
        finally:
            root.destroy()


class TestShortcutsOverlayGui(unittest.TestCase):
    """Validates the UI behavior, bindings, and state preservation of the help overlay."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root, sound_enabled=False)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.app._on_close()
        except tkinter.TclError:
            pass

    def test_help_button_initialized(self):
        """Help button must exist on the scoreboard bar and be configured."""
        self.assertTrue(hasattr(self.app, "help_button"))
        self.assertIsInstance(self.app.help_button, tkinter.Button)
        # Verify it is gridded and has expected text or image
        info = self.app.help_button.grid_info()
        self.assertEqual(info["row"], 0)
        self.assertEqual(info["column"], 9)

    def test_toggle_shortcuts_overlay_lifecycle(self):
        """Toggling the overlay repeatedly creates and cleanly destroys the dialog."""
        self.assertIsNone(self.app._shortcuts_dialog)

        # Open overlay
        self.app._toggle_shortcuts_overlay()
        self.assertIsNotNone(self.app._shortcuts_dialog)
        self.assertTrue(self.app._shortcuts_dialog.winfo_exists())
        self.assertEqual(
            self.app._shortcuts_dialog.title(),
            "Blackjack - Keyboard Shortcuts & Controls",
        )

        # Toggle again -> should close
        self.app._toggle_shortcuts_overlay()
        self.assertIsNone(self.app._shortcuts_dialog)

    def test_close_via_escape_binding(self):
        """Pressing Escape inside the overlay dialog destroys it cleanly."""
        self.app._show_shortcuts_overlay()
        dialog = self.app._shortcuts_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(dialog.winfo_exists())

        # Simulate Escape event on dialog with focus
        dialog.focus_force()
        dialog.update_idletasks()
        dialog.event_generate("<Escape>")
        dialog.update()

        self.assertIsNone(self.app._shortcuts_dialog)

    def test_game_state_unaltered_by_overlay(self):
        """Opening and closing the overlay must not alter bankroll, bets, or hands."""
        initial_bankroll = self.app.bankroll_var.get()
        initial_bet = self.app.current_bet_var.get()
        initial_hand_len = len(self.app.player_hand)
        initial_dealer_len = len(self.app.dealer_hand)

        # Open and close overlay
        self.app._show_shortcuts_overlay()
        self.root.update()
        self.app._close_shortcuts_overlay()
        self.root.update()

        # Invariants
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll)
        self.assertEqual(self.app.current_bet_var.get(), initial_bet)
        self.assertEqual(len(self.app.player_hand), initial_hand_len)
        self.assertEqual(len(self.app.dealer_hand), initial_dealer_len)

    def test_keyboard_shortcuts_bound_on_root(self):
        """All expected shortcut keys must have bindings on the root window."""
        expected_keys = [
            "<question>", "?", "/", "<F1>", "<h>", "<H>", "<s>", "<S>",
            "<Key-5>", "<Shift-W>", "<Shift-H>", "<Shift-S>",
        ]
        for key in expected_keys:
            # Check that root has a binding for this sequence
            binding = self.root.bind(key)
            self.assertTrue(
                bool(binding),
                f"Expected binding for key '{key}' on root window, but none found",
            )

    def test_shortcuts_dialog_tabs_and_navigation(self):
        """Shortcuts dialog supports two-tab category switching and arrow-key navigation."""
        self.app._show_shortcuts_overlay()
        dialog = self.app._shortcuts_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(hasattr(dialog, "current_tab"))
        self.assertEqual(dialog.current_tab, 0)
        self.assertTrue(hasattr(dialog, "btn_tab_gameplay"))
        self.assertTrue(hasattr(dialog, "btn_tab_system"))

        # Switch to Tab 1 (System & Controls)
        dialog._switch_tab(1)
        self.assertEqual(dialog.current_tab, 1)

        # Switch back to Tab 0 via method
        dialog._switch_tab(0)
        self.assertEqual(dialog.current_tab, 0)

        # Test arrow key events
        dialog.focus_force()
        dialog.update()
        dialog.event_generate("<Right>")
        dialog.update()
        self.assertEqual(dialog.current_tab, 1)

        dialog.event_generate("<Left>")
        dialog.update()
        self.assertEqual(dialog.current_tab, 0)

        self.app._close_shortcuts_overlay()

    def test_shortcuts_dialog_contains_all_essential_controls(self):
        """Shortcuts dialog includes all controls: $1000 chip, Shift+W, Shift+H, Shift+C, Shift+S, V, X."""
        self.app._show_shortcuts_overlay()
        dialog = self.app._shortcuts_dialog
        self.assertIsNotNone(dialog)

        # Switch across both tabs and collect all action texts
        all_action_texts = []
        for tab_idx in (0, 1):
            dialog._switch_tab(tab_idx)
            dialog.update_idletasks()
            for widget in dialog.winfo_children():
                # Recursively search for labels in the dialog
                def extract_labels(w):
                    texts = []
                    if isinstance(w, tkinter.Label):
                        texts.append(w.cget("text"))
                    for ch in w.winfo_children():
                        texts.extend(extract_labels(ch))
                    return texts
                all_action_texts.extend(extract_labels(widget))

        combined_text = " ".join(all_action_texts)
        # Check presence of key 5 / $1,000
        self.assertIn("1,000", combined_text, "Missing $1,000 chip shortcut")
        # Check Wardrobe
        self.assertIn("Wardrobe", combined_text, "Missing Wardrobe shortcut")
        # Check Hall of Fame
        self.assertIn("Hall of Fame", combined_text, "Missing Hall of Fame shortcut")
        # Check Card Counter
        self.assertIn("Card Counter", combined_text, "Missing Card Counter shortcut")
        # Check Scale
        self.assertIn("Scale", combined_text, "Missing Scale shortcut")
        # Check Fullscreen
        self.assertIn("Fullscreen", combined_text, "Missing Fullscreen shortcut")

        self.app._close_shortcuts_overlay()

    def test_shortcuts_dialog_scrollable_container_and_no_clipping(self):
        """Shortcuts dialog wraps content in a scrollable container with mousewheel support and zero clipped rows."""
        self.app._show_shortcuts_overlay()
        dialog = self.app._shortcuts_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(hasattr(dialog, "_on_mousewheel") or hasattr(dialog, "canvas"))

        # Verify dialog geometry fits within live configuration bounds
        dialog.update_idletasks()
        req_h = dialog.winfo_reqheight()
        max_allowed_h = min(
            self.root.winfo_screenheight() - 80,
            int(config.DEFAULT_WINDOW_HEIGHT * getattr(self.app, "scale_factor", 1.0)),
        )
        self.assertLessEqual(req_h, max_allowed_h, f"Dialog height {req_h} exceeds live display allowance {max_allowed_h}")

        self.app._close_shortcuts_overlay()


if __name__ == "__main__":
    unittest.main()

