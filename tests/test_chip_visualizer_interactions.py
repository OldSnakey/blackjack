"""
Targeted Automated Test Suite for ChipVisualizer diegetic controls.
Validates:
- Persistent _hovered_denom state without delta accumulation.
- Left-click addition to staged bet.
- Right-click deduction from staged bet with lower bound $0.
- Center betting spot click to clear staged bet.
- Suppression of chip interactions and hover lift when not interactive.
"""

from __future__ import annotations

import unittest
import tkinter
from ui_canvases import ChipVisualizer


class TestChipVisualizerInteractions(unittest.TestCase):
    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.added = []
        self.deducted = []
        self.spot_cleared = False

        self.viz = ChipVisualizer(
            self.root,
            width=200,
            height=135,
            on_chip_click=lambda d: self.added.append(d),
            on_chip_deduct=lambda d: self.deducted.append(d),
            on_spot_click=self._on_spot_cleared,
        )
        self.viz.pack()
        self.viz.set_bankroll(1000, interactive=True)
        self.root.update_idletasks()

    def tearDown(self):
        try:
            self.viz.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _on_spot_cleared(self):
        self.spot_cleared = True

    def test_hover_lift_persistent_state(self):
        """Hovering a chip pile sets _hovered_denom and lifts pile by 3px at draw time."""
        self.assertIsNone(self.viz._hovered_denom)
        denom = 25
        pile_tag = f"bank_pile_{denom}"

        # Get initial Y bbox before hover
        bbox_initial = self.viz.bbox(pile_tag)
        self.assertIsNotNone(bbox_initial)

        # Trigger hover enter
        self.viz._on_pile_enter(None, denom)
        self.assertEqual(self.viz._hovered_denom, denom)
        bbox_hovered = self.viz.bbox(pile_tag)
        # Top of bounding box should be lifted up (smaller Y)
        self.assertLess(bbox_hovered[1], bbox_initial[1])

        # Repeated redraws while hovered must not accumulate extra lift (persistent state)
        self.viz.render_bankroll_piles()
        bbox_repeated = self.viz.bbox(pile_tag)
        self.assertEqual(bbox_hovered[1], bbox_repeated[1], "Lift must not accumulate across redraws")

        # Trigger hover leave
        self.viz._on_pile_leave(None, denom)
        self.assertIsNone(self.viz._hovered_denom)
        bbox_restored = self.viz.bbox(pile_tag)
        self.assertEqual(bbox_restored[1], bbox_initial[1], "Position must be restored on leave")

    def test_left_and_right_click_interactions(self):
        """Left-click calls on_chip_click, right-click calls on_chip_deduct."""
        self.viz.trigger_pile_click(25)
        self.assertEqual(self.added, [25])

        self.viz.trigger_pile_deduct(25)
        self.assertEqual(self.deducted, [25])

    def test_spot_click_clears_bet(self):
        """Clicking the center betting spot calls on_spot_click in legacy 0-arg configuration."""
        self.assertFalse(self.spot_cleared)
        self.viz.trigger_spot_click()
        self.assertTrue(self.spot_cleared)

    def test_spot_symmetric_add_and_clear(self):
        """Center spot supports left-click add and right-click clear."""
        main_added = []
        main_cleared = []
        sb_added = []
        sb_cleared = []

        viz = ChipVisualizer(
            self.root,
            width=260,
            height=140,
            on_spot_click=lambda amt: main_added.append(amt),
            on_spot_clear=lambda: main_cleared.append(True),
            on_side_bet_click=lambda b, amt: sb_added.append((b, amt)),
            on_side_bet_clear=lambda b: sb_cleared.append(b),
        )
        viz.pack()
        viz.set_bankroll(1000, interactive=True)
        self.root.update_idletasks()

        # Left-click on center spot adds $5
        viz.trigger_spot_click(5)
        self.assertEqual(main_added, [5])

        # Right-click on center spot clears main bet
        viz.trigger_spot_clear()
        self.assertEqual(main_cleared, [True])

        # Side bets also support left-click add and right-click clear symmetrically
        viz.trigger_side_bet_click("perfect_pairs", 5)
        self.assertEqual(sb_added, [("perfect_pairs", 5)])

        viz.trigger_side_bet_clear("perfect_pairs")
        self.assertEqual(sb_cleared, ["perfect_pairs"])

        viz.destroy()

    def test_canvas_event_full_surface_and_chip_hit_detection(self):
        """Synthetic canvas events on spots and stacked chips correctly route to actions without dead pixels."""
        main_added = []
        main_cleared = []
        sb_added = []
        sb_cleared = []

        viz = ChipVisualizer(
            self.root,
            width=260,
            height=140,
            on_spot_click=lambda amt: main_added.append(amt),
            on_spot_clear=lambda: main_cleared.append(True),
            on_side_bet_click=lambda b, amt: sb_added.append((b, amt)),
            on_side_bet_clear=lambda b: sb_cleared.append(b),
        )
        viz.pack()
        viz.set_bankroll(1000, interactive=True)
        # Render chips on all spots
        viz.render_stacks(25)
        viz.render_side_bet_stacks("perfect_pairs", 15)
        viz.render_side_bet_stacks("21_plus_3", 10)
        self.root.update_idletasks()

        # Simulate left-click directly on Perfect Pairs spot center
        ev_pp_left = type("Event", (), {"x": viz.pp_cx, "y": viz.pp_cy, "state": 0})()
        viz._on_canvas_click(ev_pp_left, is_right_click=False)
        self.assertEqual(sb_added, [("perfect_pairs", 5)])

        # Simulate left-click on Perfect Pairs chip stack (slightly elevated above center)
        ev_pp_chip = type("Event", (), {"x": viz.pp_cx, "y": viz.pp_cy - 8, "state": 0})()
        viz._on_canvas_click(ev_pp_chip, is_right_click=False)
        self.assertEqual(sb_added, [("perfect_pairs", 5), ("perfect_pairs", 5)])

        # Simulate right-click on Perfect Pairs chips
        viz._on_canvas_click(ev_pp_chip, is_right_click=True)
        self.assertEqual(sb_cleared, ["perfect_pairs"])

        # Simulate left-click on center Main Bet chips (elevated above center)
        ev_main_chip = type("Event", (), {"x": viz.cx, "y": viz.cy - 10, "state": 0x0001})()  # Shift held -> 25
        viz._on_canvas_click(ev_main_chip, is_right_click=False)
        self.assertEqual(main_added, [25])

        # Simulate right-click on center Main Bet
        viz._on_canvas_click(ev_main_chip, is_right_click=True)
        self.assertEqual(main_cleared, [True])

        # Simulate click on 21+3 spot
        ev_t13 = type("Event", (), {"x": viz.t13_cx, "y": viz.t13_cy, "state": 0})()
        viz._on_canvas_click(ev_t13, is_right_click=False)
        self.assertEqual(sb_added[-1], ("21_plus_3", 5))

        viz.destroy()

    def test_no_double_firing_on_tagged_elements(self):
        """Clicks directly on watermark text, badges, or chips must invoke callback exactly once for $5, never $10."""
        self.root.deiconify()
        try:
            main_added = []
            viz = ChipVisualizer(
                self.root,
                width=260,
                height=140,
                on_spot_click=lambda amt: main_added.append(amt),
            )
            viz.pack()
            viz.set_bankroll(1000, interactive=True)
            self.root.update()

            # Watermark coords
            wm_items = viz.find_withtag("watermark")
            self.assertTrue(len(wm_items) > 0)
            wm_coords = viz.coords(wm_items[0])

            # Event generation on the canvas
            viz.event_generate("<Button-1>", x=int(wm_coords[0]), y=int(wm_coords[1]))
            self.root.update()

            # Must be called exactly once with 5, never [5, 5] ($10)
            self.assertEqual(main_added, [5], f"Expected exactly [5] but got {main_added} (double-firing detected)")

            viz.destroy()
        finally:
            self.root.withdraw()

    def test_clear_followed_immediately_by_add_resets_accurately(self):
        """Immediately adding chips after clear resets badge text and renders fresh bet without resurrecting old bet."""
        viz = ChipVisualizer(
            self.root,
            width=260,
            height=140,
        )
        viz.pack()
        viz.set_bankroll(1000, interactive=True)
        self.root.update_idletasks()

        # Rapidly add chips up to 50
        for amt in (10, 20, 30, 40, 50):
            viz.animate_chip_drop(10, amt)

        self.assertEqual(viz.current_bet, 50)
        self.assertEqual(viz.itemcget("badge", "text"), "BET: $50")

        # Clear bet
        viz.animate_clear()
        self.assertEqual(viz.current_bet, 0)
        # Badge must be cleared immediately, not delayed
        self.assertEqual(viz.itemcget("badge", "text"), "")

        # Immediately left click to add 5
        viz.animate_chip_drop(5, 5)
        self.assertEqual(viz.current_bet, 5)
        self.assertEqual(viz.itemcget("badge", "text"), "BET: $5")

        # Wait out any animation ticks
        for _ in range(5):
            self.root.after(20)
            self.root.update_idletasks()

        # After all ticks complete, total must still be 5, never old bet (50) + 5
        self.assertEqual(viz.current_bet, 5)
        self.assertEqual(viz.itemcget("badge", "text"), "BET: $5")

        viz.destroy()

    def test_interactions_suppressed_when_non_interactive(self):
        """Clicks and hover are ignored when interactive_bankroll is False."""
        self.viz.set_bankroll(1000, interactive=False)
        self.added.clear()
        self.deducted.clear()
        self.spot_cleared = False

        self.viz._on_pile_enter(None, 25)
        self.assertIsNone(self.viz._hovered_denom)

        self.viz.trigger_pile_click(25)
        self.assertEqual(self.added, [])

        self.viz.trigger_pile_deduct(25)
        self.assertEqual(self.deducted, [])

        self.viz.trigger_spot_click()
        self.assertFalse(self.spot_cleared)

    def test_bankroll_badge_and_stack_labels_non_overlapping(self):
        """bankroll_badge and denomination labels must never overlap across scales and bankrolls."""
        for scale in (1.0, 1.5, 2.0):
            self.viz.set_scale(scale)
            for bankroll in (1000, 2500, 995, 50, 0):
                self.viz.set_bankroll(bankroll, interactive=True)
                self.root.update_idletasks()

                badge_box = self.viz.bbox("bankroll_badge")
                self.assertIsNotNone(badge_box, "bankroll_badge must have a valid bounding box")

                # Find all denomination labels under the stacks
                for denom in (5, 25, 100, 500, 1000):
                    pile_items = self.viz.find_withtag(f"bank_pile_{denom}")
                    # short_lbl text is tagged with bankroll_chip and pile_tag
                    lbl_items = [it for it in pile_items if self.viz.type(it) == "text"]
                    self.assertTrue(len(lbl_items) >= 1)
                    lbl_box = self.viz.bbox(lbl_items[-1])
                    self.assertIsNotNone(lbl_box)

                    # Denomination labels must be strictly ABOVE bankroll badge with positive clearance
                    self.assertLess(
                        lbl_box[3], badge_box[1],
                        f"denom {denom} label bottom ({lbl_box[3]}) collided with bankroll_badge top ({badge_box[1]}) at scale {scale}!"
                    )
                    # Bankroll badge must fit within the canvas height
                    self.assertLessEqual(
                        badge_box[3], self.viz.canvas_height + 2,
                        f"bankroll_badge bottom ({badge_box[3]}) overflowed canvas height ({self.viz.canvas_height})!"
                    )


if __name__ == "__main__":
    unittest.main()

