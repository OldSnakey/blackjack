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
        r2 = table.rowconfigure(2)
        self.assertGreaterEqual(r0["minsize"], 118)
        self.assertGreaterEqual(r0["weight"], 1)
        self.assertGreaterEqual(r1["minsize"], 140)
        self.assertGreaterEqual(r1["weight"], 1)
        self.assertGreaterEqual(r2["minsize"], 55)
        self.assertEqual(r2["weight"], 0)

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
        """Dealer and player cards frames are retired; card sprites are cleared from canvas when hands are empty."""
        # Clear hands for betting phase
        self.app.dealer_hand = []
        self.app.player_hands = [[]]
        self.app._render_dealer_cards()
        self.app._render_player_cards()
        self.root.update_idletasks()

        # Retired frame containers must no longer exist on app
        self.assertFalse(hasattr(self.app, "dealer_cards_frame"))
        self.assertFalse(hasattr(self.app, "player_cards_frame"))

        # Canvas must have zero card sprite items
        card_sprites = self.app.card_table_frame.find_withtag("card_sprite")
        self.assertEqual(len(card_sprites), 0)

    def test_dealer_is_always_enabled(self):
        """Dealer view is always enabled and cannot be disabled."""
        self.assertTrue(self.app.dealer_view_var.get())
        # Toggling dealer view keeps it enabled (always on)
        self.app._on_toggle_dealer_view()
        self.assertTrue(self.app.dealer_view_var.get())
        # Dealer toggle button is removed from visible header grid
        self.assertFalse(bool(self.app.dealer_view_button.grid_info()))

    def test_empty_cards_frames_do_not_render_solid_boxes(self):
        """When hands are cleared for betting, no card sprites or decorations exist on TableFeltCanvas."""
        self.app.dealer_hand = []
        self.app.player_hands = [[]]
        self.app._render_dealer_cards()
        self.app._render_player_cards()
        self.root.update_idletasks()

        table = self.app.card_table_frame
        self.assertEqual(len(table.find_withtag("card_sprite")), 0)
        self.assertEqual(len(table.find_withtag("dealer_card_decor")), 0)
        self.assertEqual(len(table.find_withtag("player_card_decor")), 0)

    def test_compute_slide_trajectory(self):
        """Quadratic Bezier slide trajectory calculates smooth curve from shoe mouth to target."""
        table = self.app.card_table_frame
        shoe_x, shoe_y = table.get_shoe_mouth_coords()
        dest_x, dest_y = 300, 200
        trajectory = table.compute_slide_trajectory(shoe_x, shoe_y, dest_x, dest_y, steps=9, arc_lift=18)
        self.assertEqual(len(trajectory), 9)
        # Final point should arrive at destination coords
        self.assertEqual(trajectory[-1], (dest_x, dest_y))
        # Midpoint should have upward lift (lower y in screen coords) relative to linear progression
        mid_x, mid_y = trajectory[4]
        t = 5.0 / 9.0
        u = 1.0 - (1.0 - t) * (1.0 - t)
        linear_y_at_u = (1.0 - u) * shoe_y + u * dest_y
        self.assertLess(mid_y, linear_y_at_u)

    def test_animate_card_slide_and_cancel(self):
        """animate_card_slide schedules timer and cancel_card_animations snaps to target and executes completion."""
        table = self.app.card_table_frame
        item_id = table.draw_card_sprite(self.app.back_image, 100, 100)
        completed = [False]
        def _done():
            completed[0] = True
        table.animate_card_slide(item_id, 800, 50, 200, 150, on_complete=_done, force_animate=True)
        self.assertTrue(table.has_active_card_animations())
        table.cancel_card_animations()
        self.assertFalse(table.has_active_card_animations())
        self.root.update_idletasks()
        self.assertTrue(completed[0])
        # Verify sprite snapped to target coords
        coords = table.coords(item_id)
        self.assertEqual((int(coords[0]), int(coords[1])), (200, 150))

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

    def test_shoe_tray_perched_at_horizon_and_moves_on_resize(self):
        """Shoe tray is perched at the horizon rail (y <= 5) and dynamically repositions on window resize."""
        table = self.app.card_table_frame
        table.update_shoe_penetration(remaining=180, total=208)
        self.root.update_idletasks()

        items = table.find_withtag("shoe_tray")
        self.assertGreater(len(items), 0, "shoe_tray items not found on felt canvas")
        bbox_initial = table.bbox("shoe_tray")
        # y1 must be at the top horizon rail (<= 5)
        self.assertLessEqual(bbox_initial[1], 5, f"Shoe tray not at horizon rail: y1={bbox_initial[1]}")

        # Simulate window stretch resize event from 900 to 1300
        old_x2 = bbox_initial[2]
        new_width = 1300
        event = type("ResizeEvent", (), {"width": new_width, "height": table.canvas_height})()
        table._on_resize(event)
        self.root.update_idletasks()

        bbox_resized = table.bbox("shoe_tray")
        # x2 must have shifted rightward to track the new window width
        self.assertGreater(bbox_resized[2], old_x2 + 200, "Shoe tray did not move rightward with window resize")
        self.assertLessEqual(bbox_resized[1], 5, "Shoe tray shifted away from horizon rail on resize")

    def test_discard_rack_has_no_opaque_black_box(self):
        """Discard rack does not draw an opaque black box on the felt."""
        table = self.app.card_table_frame
        table.draw_discard_rack(discarded=0, total=208)
        # Empty discard rack should render zero items
        self.assertEqual(len(table.find_withtag("discard_rack")), 0)

        # Non-empty discard rack should have empty fill on container (no opaque black)
        table.draw_discard_rack(discarded=50, total=208)
        items = table.find_withtag("discard_rack")
        self.assertGreater(len(items), 0)
        container_fill = table.itemcget(items[0], "fill")
        self.assertNotEqual(container_fill, "#0a1812", "Discard rack should not have opaque black fill")

    def test_trainer_hud_window_expansion_and_row_clearance(self):
        """Toggling Trainer HUD expands window height if less than DEFAULT_WINDOW_HEIGHT."""
        import config
        from unittest.mock import patch

        with patch.object(self.root, "winfo_height", return_value=700), \
             patch.object(self.root, "geometry") as mock_geom:
            self.app.apply_play_mode("training")
            expected_h = min(config.DEFAULT_WINDOW_HEIGHT, self.root.winfo_screenheight() - 80)
            mock_geom.assert_called_with(f"900x{expected_h}")


if __name__ == "__main__":
    unittest.main()

