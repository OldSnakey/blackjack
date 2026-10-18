"""
Unit tests for Panoramic Casino Table Felt Canvas (TableFeltCanvas).
Validates:
- Seamless felt texture rendering and background lower invariant.
- Theme switching across Normal, Creep, Hell's Table, and Celestial phases.
- Container compatibility for rowconfigure, columnconfigure, and child widget gridding.
"""

from __future__ import annotations

import unittest
import tkinter
from blackjack import (
    BlackjackApp,
    TableFeltCanvas,
    Phase,
    PANEL_BACKGROUND_COLOR,
)


class TestTableFeltCanvas(unittest.TestCase):
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

    def test_card_table_frame_is_table_felt_canvas(self):
        """card_table_frame is an instance of TableFeltCanvas and tkinter.Canvas."""
        self.assertTrue(hasattr(self.app, "card_table_frame"))
        self.assertIsInstance(self.app.card_table_frame, TableFeltCanvas)
        self.assertIsInstance(self.app.card_table_frame, tkinter.Canvas)

    def test_felt_container_geometry_apis(self):
        """TableFeltCanvas preserves container APIs: rowconfigure, columnconfigure, and ['background']."""
        table = self.app.card_table_frame
        r0 = table.rowconfigure(0)
        r1 = table.rowconfigure(1)
        self.assertGreaterEqual(r0["minsize"], 118)
        self.assertGreaterEqual(r0["weight"], 1)
        self.assertGreaterEqual(r1["minsize"], 118)
        self.assertGreaterEqual(r1["weight"], 1)

        c1 = table.columnconfigure(1)
        self.assertGreaterEqual(c1["weight"], 1)

        self.assertIsNotNone(table["background"])

    def test_felt_canvas_renders_felt_bg(self):
        """TableFeltCanvas renders the felt_bg canvas image item at bottom of display list."""
        table = self.app.card_table_frame
        self.root.update_idletasks()
        items = table.find_withtag("felt_bg")
        self.assertGreater(len(items), 0, "felt_bg item not found on TableFeltCanvas")

    def test_phase_theme_switching(self):
        """Switching haunted phases updates the TableFeltCanvas theme and palette."""
        table = self.app.card_table_frame

        # Normal phase -> casino emerald
        self.app._apply_phase_theme(Phase.NORMAL)
        self.root.update_idletasks()
        self.assertEqual(table.current_theme, "casino")

        # Creep phase -> creep
        self.app._apply_phase_theme(Phase.CREEP)
        self.root.update_idletasks()
        self.assertEqual(table.current_theme, "creep")

        # Hell table -> hell
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.root.update_idletasks()
        self.assertEqual(table.current_theme, "hell")

        # Victory -> celestial
        self.app._apply_phase_theme(Phase.VICTORY)
        self.root.update_idletasks()
        self.assertEqual(table.current_theme, "celestial")

    def test_chip_visualizer_felt_slice_background(self):
        """ChipVisualizer synchronizes seamless felt texture slice from TableFeltCanvas and eliminates flat box."""
        self.app.chips_mode_var.set(True)
        self.app.chip_visualizer.grid()
        self.root.update_idletasks()

        chip = self.app.chip_visualizer
        self.app.card_table_frame.sync_children_felt()
        self.root.update_idletasks()

        # Canvas must contain the felt_bg background image slice item
        items = chip.find_withtag("felt_bg")
        self.assertGreater(len(items), 0, "felt_bg slice item not found on ChipVisualizer")

        # spot_base must have no opaque flat green fill (fill == '')
        spot_fill = chip.itemcget("spot_base", "fill")
        self.assertEqual(spot_fill, "", "spot_base should have empty fill to show felt texture")

    def test_cards_frames_do_not_obscure_table_during_betting(self):
        """Dealer and player cards frames do not expand across the full table with sticky nsew when empty."""
        # Clear hands for betting phase
        self.app.dealer_hand = []
        self.app.player_hands = [[]]
        self.app._render_dealer_cards()
        self.app._render_player_cards()
        self.root.update_idletasks()

        d_frame = self.app.dealer_cards_frame
        p_frame = self.app.player_cards_frame

        # Must not have sticky='nsew' stretching them across the entire grid cell
        d_sticky = d_frame.grid_info().get("sticky", "")
        p_sticky = p_frame.grid_info().get("sticky", "")
        self.assertNotIn("n", d_sticky)
        self.assertNotIn("s", d_sticky)
        self.assertNotIn("e", d_sticky)
        self.assertNotIn("w", d_sticky)

        # Width of empty frames must be minimal (< 50px), not 600+ px
        self.assertLess(d_frame.winfo_width(), 50)
        self.assertLess(p_frame.winfo_width(), 50)

    def test_dealer_is_always_enabled(self):
        """Dealer view is always enabled and cannot be disabled."""
        self.assertTrue(self.app.dealer_view_var.get())
        # Toggling dealer view keeps it enabled (always on)
        self.app._on_toggle_dealer_view()
        self.assertTrue(self.app.dealer_view_var.get())
        # Dealer toggle button is removed from visible header grid
        self.assertFalse(bool(self.app.dealer_view_button.grid_info()))

    def test_empty_cards_frames_do_not_render_solid_boxes(self):
        """When hands are cleared for betting, cards frames are unmapped to prevent solid green patches."""
        self.app.dealer_hand = []
        self.app.player_hands = [[]]
        self.app._render_dealer_cards()
        self.app._render_player_cards()
        self.root.update_idletasks()

        # Frames should either be unmapped or have 0 geometry
        self.assertFalse(bool(self.app.dealer_cards_frame.winfo_ismapped()))
        self.assertFalse(bool(self.app.player_cards_frame.winfo_ismapped()))

    def test_chip_visualizer_slice_has_no_black_pixels(self):
        """ChipVisualizer felt slice contains no pure black (0,0,0) pixels from out-of-bounds crop."""
        self.app.chips_mode_var.set(True)
        self.app.chip_visualizer.grid()
        self.root.update_idletasks()
        self.app.card_table_frame.sync_children_felt()
        self.root.update_idletasks()

        chip = self.app.chip_visualizer
        slice_img = getattr(chip, "_felt_slice_img", None)
        if slice_img is not None:
            # Check minimum extrema across RGB channels - must be > 0 (felt base green, not black)
            extrema = slice_img.getextrema()
            min_r, min_g, min_b = extrema[0][0], extrema[1][0], extrema[2][0]
            self.assertGreater(min_g, 10, "Felt slice should contain authentic green tones, not (0,0,0) black")

    def test_dealer_sprite_has_stage_headroom(self):
        """Dealer sprite is bounded by stage canvas height and retains headroom above the head."""
        canvas = self.app.dealer_stage_canvas
        self.root.update_idletasks()
        items = canvas.find_withtag("dealer_sprite")
        self.assertGreater(len(items), 0)
        bbox = canvas.bbox(items[0])
        # bbox is (x1, y1, x2, y2)
        # y1 must be >= 5 (never clipped off the top of the canvas)
        self.assertGreaterEqual(bbox[1], 5, f"Dealer sprite clipped above canvas: y1={bbox[1]}")


if __name__ == "__main__":
    unittest.main()

