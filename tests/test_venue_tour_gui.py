"""
Headless GUI tests for Track 6 (`venue_tour.py` 2.5D Super Mario World Overworld Map,
`TourControlDock`, mystery silhouettes, Gold/Ironman 2.5D medallions, keyboard/mouse navigation,
Coordinator stage unveiling transitions, and top-bar width invariants).
"""

from __future__ import annotations

import json
import shutil
import tempfile
import tkinter
import unittest
from pathlib import Path

from blackjack import BlackjackApp
from rules import Card
from ui_dialogs import ShortcutsDialog
from ui_layout import DEFAULT_UI_CONFIG


def _extract_widgets(parent: tkinter.Misc, widget_type: type = tkinter.Label) -> list:
    found = []
    if isinstance(parent, widget_type):
        found.append(parent)
    for child in parent.winfo_children():
        found.extend(_extract_widgets(child, widget_type))
    return found


class TestVenueTourGui(unittest.TestCase):
    """GUI layout, Overworld Map rendering, navigation, and transition tests for Casino Venue Tour."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="bj_tour_gui_")
        self.save_path = Path(self.temp_dir) / "test_save.json"
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(
            self.root,
            chips_mode=True,
            sound_enabled=False,
            save_path=self.save_path,
        )
        self.root.update_idletasks()

    def tearDown(self) -> None:
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ui_layout_tour_button_parity_and_scoreboard_fit_under_900px(self) -> None:
        """ui_layout.py and assets/ui_config.json match on tour_button and scoreboard fits <= 900px."""
        cfg_path = Path(__file__).resolve().parent.parent / "assets" / "ui_config.json"
        disk_cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.assertIn("tour_button", DEFAULT_UI_CONFIG["top_bar"]["elements"])
        self.assertEqual(
            DEFAULT_UI_CONFIG["top_bar"]["elements"]["tour_button"],
            disk_cfg["top_bar"]["elements"]["tour_button"],
        )

        # Unlock both Exorcist (maps tour_button) and Cursed Stakes (maps cursed_stakes_button)
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.haunted.unlocked_cursed_stakes = True
        self.app._sync_tour_button()
        self.app._sync_cursed_stakes_button()
        self.root.update_idletasks()

        self.assertTrue(bool(self.app.tour_button.grid_info()))
        self.assertLessEqual(
            self.app.scoreboard_frame.winfo_reqwidth(),
            900,
            f"Top scoreboard bar overflowed 900px width: {self.app.scoreboard_frame.winfo_reqwidth()}px",
        )

    def test_overworld_map_mount_silhouette_mystery_and_medallion_stamps(self) -> None:
        """Overworld Map mounts on row=3 beneath live DealerStageCanvas, renders ??? silhouettes, and stamps medallions."""
        self.app.save_manager.unlock_achievement("exorcist")
        self.app._sync_tour_button()

        self.app.enter_venue_tour()
        self.root.update_idletasks()

        self.assertTrue(self.app.tour_active)
        self.assertFalse(self.app.tour_in_salon)
        self.assertIsNotNone(self.app.tour_frame)
        self.assertIsNotNone(self.app.tour_dock)
        self.assertTrue(bool(self.app.tour_frame.grid_info()))
        self.assertTrue(bool(self.app.tour_dock.grid_info()))
        self.assertTrue(bool(self.app.dealer_stage_frame.grid_info()))
        self.assertFalse(bool(self.app.card_table_frame.grid_info()))
        self.assertFalse(bool(self.app.mahogany_rail.grid_info()))
        self.assertEqual(self.app.dealer_actor.current_costume, "julian_monte_carlo")

        canvas = self.app.tour_frame.canvas
        renderer = self.app.tour_frame.renderer
        self.assertEqual(len(renderer.node_hit_boxes), 8)

        # Collect canvas text items in initial state (only Salon 1 discovered)
        texts_initial = [
            canvas.itemcget(item_id, "text")
            for item_id in canvas.find_all()
            if canvas.type(item_id) == "text"
        ]
        joined_initial = "\n".join(texts_initial)
        self.assertIn("Training Pit", joined_initial)
        self.assertIn("???", joined_initial)
        self.assertIn("$1,500", joined_initial)
        self.assertEqual(len(canvas.find_withtag("tour_medallion_gold")), 0)
        self.assertEqual(len(canvas.find_withtag("tour_medallion_ironman")), 0)

        # Advance 3 Standard clears and 2 Ironman clears, then re-render
        vt = self.app.save_manager.data.venue_tour
        vt.forgiving_salons_cleared = 3
        vt.forgiving_selected_idx = 3
        vt.forgiving_bankroll = 8000
        vt.ironman_salons_cleared = 2
        self.app.tour_frame.refresh_map()
        self.root.update_idletasks()

        texts_mid = "\n".join(
            canvas.itemcget(item_id, "text")
            for item_id in canvas.find_all()
            if canvas.type(item_id) == "text"
        )
        self.assertIn("Golden Floor", texts_mid)
        self.assertIn("Downtown", texts_mid)
        self.assertIn("Faculty Club", texts_mid)
        # Salons 4..7 remain undiscovered silhouettes
        self.assertIn("???", texts_mid)
        self.assertGreater(len(canvas.find_withtag("tour_medallion_gold")), 0)
        self.assertGreater(len(canvas.find_withtag("tour_medallion_ironman")), 0)

    def test_keyboard_navigation_canvas_hitboxes_and_mode_toggle(self) -> None:
        """Keyboard arrows/Enter, single-source node hitboxes, and Standard<->Ironman toggle work cleanly."""
        self.app.save_manager.unlock_achievement("exorcist")
        vt = self.app.save_manager.data.venue_tour
        vt.forgiving_salons_cleared = 3
        vt.forgiving_selected_idx = 0
        vt.forgiving_bankroll = 8000
        vt.ironman_stage_idx = 2
        vt.ironman_salons_cleared = 2
        vt.ironman_bankroll = 4200

        self.app.enter_venue_tour()
        tf = self.app.tour_frame
        self.assertEqual(tf.focused_salon_idx, 0)

        # Arrow key navigation updates focused salon
        tf.move_focus(1)
        self.assertEqual(tf.focused_salon_idx, 1)
        tf.move_focus(1)
        self.assertEqual(tf.focused_salon_idx, 2)

        # Toggle to Ironman -> discovered salons stay visible, earlier salons velvet-roped
        tf.toggle_tour_mode()
        self.assertEqual(vt.active_mode, "ironman")
        self.assertEqual(tf.focused_salon_idx, 2)

        # Clicking velvet-roped Salon 0 focuses it for inspection, but attempting to enter stays on map
        x1, y1, x2, y2 = tf.renderer.node_hit_boxes[0]
        tf.on_map_click((x1 + x2) // 2, (y1 + y2) // 2)
        self.assertEqual(tf.focused_salon_idx, 0)
        tf.activate_focused_salon()
        self.assertFalse(self.app.tour_in_salon, "Velvet-roped Ironman salon must not be playable")

        # Clicking active Ironman frontier Salon 2 twice enters Salon 2
        fx1, fy1, fx2, fy2 = tf.renderer.node_hit_boxes[2]
        cx, cy = (fx1 + fx2) // 2, (fy1 + fy2) // 2
        tf.on_map_click(cx, cy)
        self.assertEqual(tf.focused_salon_idx, 2)
        tf.on_map_click(cx, cy)
        self.assertTrue(self.app.tour_in_salon)
        self.assertEqual(self.app.active_tour_salon_idx, 2)

        # Returning to map via Shift+T or return_to_tour_map restores Overworld Map
        self.app._on_tour_shortcut()
        self.assertTrue(self.app.tour_active)
        self.assertFalse(self.app.tour_in_salon)

    def test_top_up_dock_button_and_promotion_transition_timer(self) -> None:
        """Top-Up dock button obeys <=80% threshold and salon promotion schedules tracked transition back to Map."""
        self.app.save_manager.unlock_achievement("exorcist")
        vt = self.app.save_manager.data.venue_tour
        vt.forgiving_salons_cleared = 1
        vt.forgiving_selected_idx = 1
        vt.forgiving_bankroll = 1400  # > 80% of $1,500 ($1,200) -> Top-Up disabled

        self.app.enter_venue_tour()
        self.assertFalse(self.app.tour_dock.buttons["top_up"].enabled)

        vt.forgiving_bankroll = 1200  # == 80% of $1,500 -> Top-Up enabled!
        self.app.tour_frame.refresh_map()
        self.assertTrue(self.app.tour_dock.buttons["top_up"].enabled)
        self.app.top_up_tour_stake()
        self.assertEqual(vt.forgiving_bankroll, 1500)
        self.assertFalse(self.app.tour_dock.buttons["top_up"].enabled)

        # Test Salon 0 -> Salon 1 promotion celebration transition
        vt.forgiving_salons_cleared = 0
        vt.forgiving_selected_idx = 0
        vt.forgiving_bankroll = 1450
        self.app.enter_tour_salon(0)

        self.app.deck = list(self.app.deck[:-4]) + [
            Card(7, self.app.back_image, rank="7", suit="club"),
            Card(10, self.app.back_image, rank="10", suit="spade"),
            Card(10, self.app.back_image, rank="king", suit="heart"),
            Card(10, self.app.back_image, rank="10", suit="diamond"),
        ]
        self.app._deal_hand_with_bet(100)
        self.app.on_stand()
        while self.app._dealer_timer_id is not None:
            self.app._dealer_step()

        self.assertEqual(vt.forgiving_salons_cleared, 1)
        self.assertIsNotNone(self.app._tour_transition_timer_id)

        # Trigger transition callback deterministically without waiting 1,500ms wall-clock
        self.app._complete_tour_promotion_transition(1)
        self.assertIsNone(self.app._tour_transition_timer_id)
        self.assertTrue(self.app.tour_active)
        self.assertFalse(self.app.tour_in_salon)
        self.assertEqual(self.app.tour_frame.focused_salon_idx, 1)
        self.assertEqual(self.app.dealer_actor.current_costume, "julian_monte_carlo")

    def test_dock_button_widths_and_shortcuts_dialog_tour_entry(self) -> None:
        """All TourControlDock buttons >= 100px wide and ShortcutsDialog documents Shift+T cleanly."""
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.enter_venue_tour()
        self.root.update_idletasks()

        for key, btn in self.app.tour_dock.buttons.items():
            self.assertGreaterEqual(
                btn.width,
                100,
                f"TourControlDock button '{key}' width {btn.width}px violates >= 100px invariant",
            )

        # Verify Ironman Reset Run confirmation cancel safety on Overworld Map
        vt = self.app.save_manager.data.venue_tour
        vt.active_mode = "ironman"
        vt.ironman_stage_idx = 3
        vt.ironman_bankroll = 9200
        self.app.tour_frame.refresh_map()
        orig_confirm = self.app.tour_frame._ask_confirm_ironman_reset
        self.app.tour_frame._ask_confirm_ironman_reset = lambda: False
        try:
            self.app.tour_frame.restart_ironman_climb()
            self.assertEqual(vt.ironman_stage_idx, 3)
            self.assertEqual(vt.ironman_bankroll, 9200)
        finally:
            self.app.tour_frame._ask_confirm_ironman_reset = orig_confirm

        # Verify in-salon left-anchor Map [Esc] button on mahogany_rail
        vt.active_mode = "forgiving"
        self.app.enter_tour_salon(0)
        self.root.update_idletasks()
        self.assertTrue(hasattr(self.app, "tour_map_rail_button"))
        self.assertTrue(bool(self.app.tour_map_rail_button.grid_info()))
        self.assertGreaterEqual(self.app.tour_map_rail_button.width, 100)
        self.app.tour_map_rail_button.invoke()
        self.assertTrue(self.app.tour_active)
        self.assertFalse(self.app.tour_in_salon)
        self.assertFalse(bool(self.app.tour_map_rail_button.grid_info()))

        dlg = ShortcutsDialog(self.root, self.app.icon_loader)
        try:
            dlg.update_idletasks()
            all_texts = []
            for tab in (0, 1):
                dlg._switch_tab(tab)
                dlg.update_idletasks()
                all_texts.extend(lbl.cget("text") for lbl in _extract_widgets(dlg, tkinter.Label))
            joined = "\n".join(all_texts)
            self.assertIn("Shift+T", joined)
            self.assertIn("Tour", joined)
        finally:
            dlg.destroy()


if __name__ == "__main__":
    unittest.main()
