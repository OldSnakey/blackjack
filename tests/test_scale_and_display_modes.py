"""
Unit test suite for Phase 2: In-Memory Pillow Scaling (1x <-> 2x) & Fullscreen Display Modes.

Validates:
- Scale factor state machine (1.0 <-> 2.0).
- Dynamic in-memory card and asset scaling with PIL (zero duplicate files on disk).
- Proportional coordinate scaling for HauntedAltarCanvas, ChipVisualizer, and SoulMeterCanvas.
- Typography & wraplength scaling in TableAnnouncementHUD.
- Active card hand and score preservation across scale transitions.
- Native Tkinter Fullscreen toggle (F11) and Escape exit.
- Keyboard shortcuts overlay HUD registration of F10 and F11 prompts.
"""

from __future__ import annotations

import unittest
import tkinter
from pathlib import Path
from PIL import ImageTk

import blackjack
from blackjack import (
    BlackjackApp,
    Card,
    CARD_WIDTH,
    CARD_HEIGHT,
    PLAYER_CARD_OVERLAP_OFFSET,
    ASSETS_DIR,
)


class TestScaleAndDisplayModes(unittest.TestCase):
    """Verifies 1x <-> 2x in-memory Pillow scaling and F11 Fullscreen mode."""

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

    def test_initial_scale_and_display_state(self):
        """Newly created BlackjackApp must start in 1x scale mode and windowed display, button showing '🔍 2x'."""
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertEqual(self.app.scale_status_var.get(), "🔍 2x")
        self.assertFalse(self.app.is_fullscreen)
        self.assertEqual(self.app.fullscreen_status_var.get(), "⛶ Full")
        self.assertEqual(self.app.card_width, CARD_WIDTH)
        self.assertEqual(self.app.card_height, CARD_HEIGHT)
        self.assertEqual(self.app.card_overlap_offset, PLAYER_CARD_OVERLAP_OFFSET)

    def test_toggle_scale_mode_to_2x_and_back(self):
        """Toggling scale mode switches to 2.0 and accurately doubles dimensions, then returns to 1.0."""
        # Toggle 1x -> 2x
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 2.0)
        self.assertEqual(self.app.scale_status_var.get(), "🔍 1x")
        self.assertEqual(self.app.card_width, CARD_WIDTH * 2)
        self.assertEqual(self.app.card_height, CARD_HEIGHT * 2)
        self.assertEqual(self.app.card_overlap_offset, PLAYER_CARD_OVERLAP_OFFSET * 2)

        # Haunted Altar Canvas doubled
        self.assertEqual(self.app.haunted_altar.canvas_width, 260 * 2)
        self.assertEqual(self.app.haunted_altar.canvas_height, 135 * 2)

        # Announcement HUD wraplength doubled
        self.assertEqual(self.app.announcement_hud.wraplength, 600 * 2)

        # Button and text typography doubled in 2x mode
        hit_font = str(self.app.hit_button.cget("font"))
        self.assertTrue("20" in hit_font or "18" in hit_font, f"Expected scaled font, got {hit_font}")
        dealer_title_font = str(self.app.dealer_title_label.cget("font"))
        self.assertTrue("22" in dealer_title_font or "20" in dealer_title_font, f"Expected scaled title font, got {dealer_title_font}")
        chips_check_font = str(self.app.chips_mode_check.cget("font"))
        self.assertTrue("20" in chips_check_font or "18" in chips_check_font, f"Expected scaled chips check font, got {chips_check_font}")

        # Toggle 2x -> 1x
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertEqual(self.app.scale_status_var.get(), "🔍 2x")
        self.assertEqual(self.app.card_width, CARD_WIDTH)
        self.assertEqual(self.app.card_height, CARD_HEIGHT)
        self.assertEqual(self.app.card_overlap_offset, PLAYER_CARD_OVERLAP_OFFSET)
        self.assertEqual(self.app.haunted_altar.canvas_width, 260)
        self.assertEqual(self.app.haunted_altar.canvas_height, 135)
        self.assertEqual(self.app.announcement_hud.wraplength, 600)

        # Button and text typography restored in 1x mode
        hit_font_1x = str(self.app.hit_button.cget("font"))
        self.assertTrue("10" in hit_font_1x, f"Expected 10 in 1x font, got {hit_font_1x}")
        dealer_title_font_1x = str(self.app.dealer_title_label.cget("font"))
        self.assertTrue("11" in dealer_title_font_1x, f"Expected 11 in 1x title font, got {dealer_title_font_1x}")

    def test_in_memory_pillow_scaling_zero_disk_duplication(self):
        """Card scaling must use PIL in memory without creating duplicate files on disk."""
        initial_png_count = len(list(ASSETS_DIR.glob("*.png")))

        # Switch to 2x mode
        self.app.toggle_scale_mode()

        # Check sample card image dimensions in memory
        sample_card = self.app.all_cards[0]
        self.assertIsInstance(sample_card.image, (ImageTk.PhotoImage, tkinter.PhotoImage))
        self.assertEqual(sample_card.image.width(), CARD_WIDTH * 2)
        self.assertEqual(sample_card.image.height(), CARD_HEIGHT * 2)

        # Card back in memory
        self.assertEqual(self.app.back_image.width(), CARD_WIDTH * 2)
        self.assertEqual(self.app.back_image.height(), CARD_HEIGHT * 2)

        # Disk verification: Zero new files written to cards/
        final_png_count = len(list(ASSETS_DIR.glob("*.png")))
        self.assertEqual(initial_png_count, final_png_count, "No duplicate card files should be created on disk")

    def test_scale_mode_preserves_active_hands_and_scoring(self):
        """Toggling scale during an active round must preserve card identities, scores, and state."""
        # Seed player and dealer with known cards
        c1 = [c for c in self.app.all_cards if c.rank == "10" and c.suit == "spade"][0]
        c2 = [c for c in self.app.all_cards if c.rank == "8" and c.suit == "heart"][0]
        d1 = [c for c in self.app.all_cards if c.rank == "9" and c.suit == "club"][0]
        d2 = [c for c in self.app.all_cards if c.rank == "7" and c.suit == "diamond"][0]

        self.app.player_hands = [[c1, c2]]
        self.app.dealer_hand = [d1, d2]
        self.app.dealer_hole_card = d2
        self.app.is_hole_card_hidden = True
        self.app._render_player_cards()
        self.app._render_dealer_cards()

        # Score before scale
        p_score_before = self.app._score_player_hand(self.app.player_hands[0])
        d_score_before = blackjack.score_hand(self.app.dealer_hand)
        self.assertEqual(p_score_before, 18)
        self.assertEqual(d_score_before, 16)

        # Scale to 2x
        self.app.toggle_scale_mode()

        # Score and card identity after scale
        p_score_after = self.app._score_player_hand(self.app.player_hands[0])
        d_score_after = blackjack.score_hand(self.app.dealer_hand)
        self.assertEqual(p_score_after, 18)
        self.assertEqual(d_score_after, 16)
        self.assertEqual(self.app.player_hands[0][0].rank, "10")
        self.assertEqual(self.app.player_hands[0][1].rank, "8")
        self.assertEqual(self.app.dealer_hand[0].rank, "9")
        self.assertEqual(self.app.dealer_hand[1].rank, "7")

        # Visual widgets in cards_frame reflect 2x dimensions
        self.assertEqual(self.app.player_hands[0][0].image.width(), CARD_WIDTH * 2)

    def test_fullscreen_toggle_and_exit(self):
        """Fullscreen mode toggles root fullscreen, auto-upscales interface to 2x, and updates status button."""
        self.assertEqual(self.app.scale_factor, 1.0)

        # Enter Fullscreen -> Automatically upscales to 2x so elements fill the screen
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.assertTrue(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.fullscreen_status_var.get(), "🗗 Window")
        self.assertEqual(self.app.scale_factor, 2.0)
        self.assertEqual(self.app.card_width, CARD_WIDTH * 2)

        # Exit Fullscreen via toggle -> Restores to 1x
        self.app.toggle_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        self.assertFalse(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.fullscreen_status_var.get(), "⛶ Full")
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertEqual(self.app.card_width, CARD_WIDTH)

        # Exit Fullscreen via exit_fullscreen helper (Escape key handler)
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.assertEqual(self.app.scale_factor, 2.0)
        self.app.exit_fullscreen()
        self.assertFalse(self.app.is_fullscreen)
        self.assertFalse(bool(self.root.attributes("-fullscreen")))
        self.assertEqual(self.app.scale_factor, 1.0)

    def test_shortcuts_dialog_registers_f10_and_f11(self):
        """Shortcuts HUD overlay dialog must display F10 (Scale) and F11 (Fullscreen) entries."""
        self.app._toggle_shortcuts_overlay()
        self.root.update_idletasks()

        dlg = getattr(self.app, "_shortcuts_dialog", None)
        self.assertIsNotNone(dlg)

        # Inspect shortcut text inside dialog frames (recursively supporting tabbed and canvas containers)
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

        has_scale_shortcut = any("Scale" in t or "1x" in t or "2x" in t for t in labels_text)
        has_full_shortcut = any("Fullscreen" in t for t in labels_text)

        self.assertTrue(has_scale_shortcut, "Shortcuts HUD must include Scale 1x/2x shortcut")
        self.assertTrue(has_full_shortcut, "Shortcuts HUD must include Fullscreen shortcut")

        self.app._close_shortcuts_overlay()

    def test_miracle_button_visibility_preserved_across_scale_toggles(self):
        """Miracle button must remain hidden during 1x <-> 2x toggles when unequipped, and stay visible when equipped."""
        from haunted_manager import Blessing

        # 1. Initially unequipped: miracle button must be hidden
        self.assertFalse(bool(self.app.miracle_button.grid_info()))

        # 2. Toggle to 2x: miracle button must still be hidden
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 2.0)
        self.assertFalse(
            bool(self.app.miracle_button.grid_info()),
            "Miracle button must NOT appear when toggling to 2x mode while unequipped"
        )

        # 3. Toggle back to 1x: miracle button must still be hidden
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertFalse(
            bool(self.app.miracle_button.grid_info()),
            "Miracle button must NOT appear when toggling back to 1x mode while unequipped"
        )

        # 4. Equip Miracle blessing in Hell's Table: button should become visible
        from blackjack import Phase
        self.app.haunted.phase = Phase.HELL_TABLE
        self.app.haunted.equip_blessing(Blessing.MIRACLE)
        self.app._update_blessings_tray()
        self.assertTrue(bool(self.app.miracle_button.grid_info()))

        # 5. Toggle to 2x while equipped: button should remain visible and scale
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 2.0)
        self.assertTrue(
            bool(self.app.miracle_button.grid_info()),
            "Miracle button must remain visible when toggling to 2x mode while equipped"
        )
        miracle_font = str(self.app.miracle_button.cget("font"))
        self.assertTrue("20" in miracle_font or "18" in miracle_font)

    def test_toggle_scale_to_1x_in_fullscreen_forces_windowed_mode(self):
        """When in fullscreen mode, clicking 1x scale forces the application back to windowed mode."""
        # Enter fullscreen mode (which upscales to 2x)
        self.app.toggle_fullscreen()
        self.assertTrue(self.app.is_fullscreen)
        self.assertEqual(self.app.scale_factor, 2.0)
        self.assertEqual(self.app.fullscreen_status_var.get(), "🗗 Window")

        # Now click 1x scale (toggle_scale_mode from 2x -> 1x)
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 1.0)
        self.assertFalse(
            self.app.is_fullscreen,
            "Toggling to 1x scale while in fullscreen mode must force return to windowed mode"
        )
        self.assertEqual(self.app.fullscreen_status_var.get(), "⛶ Full")


if __name__ == "__main__":
    unittest.main()

