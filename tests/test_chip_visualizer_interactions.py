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
        """Clicking the center betting spot calls on_spot_click."""
        self.assertFalse(self.spot_cleared)
        self.viz.trigger_spot_click()
        self.assertTrue(self.spot_cleared)

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

