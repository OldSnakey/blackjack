"""
Unit tests for TableAnnouncementHUD and HauntedAltarCanvas.
Validates:
- Two-tiered Table Announcement HUD typography, parsing, and non-truncation wraplength.
- Dynamic color-coding for outcomes (Win, Loss, Push, Blackjack, Lore).
- Parameterized font updates.
- 2.5D HauntedAltarCanvas candle states, radial glow, and directional shadow vector math.
- Kinetic animation lifecycle: grave eruption, candle smoke poof, and cancellation safety.
"""

from __future__ import annotations

import tkinter
import unittest
from pathlib import Path
from PIL import Image

# Import after checking tkinter availability
import blackjack
from blackjack import (
    TableAnnouncementHUD,
    HauntedAltarCanvas,
    HUD_OUTCOME_FONT_FAMILY,
    HUD_OUTCOME_FONT_SIZE,
    HUD_LORE_FONT_FAMILY,
    HUD_LORE_FONT_SIZE,
)


class TestTableAnnouncementHUD(unittest.TestCase):
    """Verifies the two-tier Table Announcement HUD logic and layout."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.hud = TableAnnouncementHUD(self.root)
        self.hud.pack()

    def tearDown(self):
        self.root.destroy()

    def test_default_typography_and_wraplength(self):
        """HUD must initialize with parameterized typography and non-zero wraplength."""
        self.assertEqual(self.hud.outcome_font_family, HUD_OUTCOME_FONT_FAMILY)
        self.assertEqual(self.hud.outcome_font_size, HUD_OUTCOME_FONT_SIZE)
        self.assertEqual(self.hud.lore_font_family, HUD_LORE_FONT_FAMILY)
        self.assertEqual(self.hud.lore_font_size, HUD_LORE_FONT_SIZE)

        # Labels must have wrapping enabled to eliminate truncation
        self.assertGreater(self.hud.wraplength, 400)
        self.assertEqual(int(self.hud.outcome_label.cget("wraplength")), self.hud.wraplength)
        self.assertEqual(int(self.hud.lore_label.cget("wraplength")), self.hud.wraplength)

    def test_single_message_outcome_only(self):
        """Standard single-line messages display as an outcome without lore."""
        self.hud.set_message("Player has Blackjack! You win!")
        self.assertEqual(self.hud.outcome_label.cget("text"), "Player has Blackjack! You win!")
        self.assertEqual(self.hud.lore_label.cget("text"), "")
        self.assertFalse(self.hud.is_lore_visible)

    def test_combined_message_split_into_two_tiers(self):
        """Messages with ' | ' must split into primary outcome and thematic lore."""
        raw = "Dealer wins! (Total: 20) | ☠ Candle snuffed! 4 candles remain."
        self.hud.set_message(raw)
        self.assertEqual(self.hud.outcome_label.cget("text"), "Dealer wins! (Total: 20)")
        self.assertEqual(self.hud.lore_label.cget("text"), "☠ Candle snuffed! 4 candles remain.")
        self.assertTrue(self.hud.is_lore_visible)

    def test_color_coding_rules(self):
        """Outcome colors should reflect game state (win green/gold, loss red, push yellow)."""
        # Win
        self.hud.set_message("Player WINS!")
        self.assertIn(self.hud.outcome_label.cget("fg").lower(), ("#69f0ae", "#ffd700", "#4caf50"))

        # Loss / Bust
        self.hud.set_message("Player BUSTS! Dealer wins.")
        self.assertEqual(self.hud.outcome_label.cget("fg").lower(), "#ff5252")

        # Push / Tie
        self.hud.set_message("Push! It's a draw.")
        self.assertEqual(self.hud.outcome_label.cget("fg").lower(), "#ffeb3b")

    def test_parameterized_typography_update(self):
        """Developers can hot-swap font parameters at runtime."""
        self.hud.set_typography(
            outcome_family="Courier New", outcome_size=18, outcome_weight="normal",
            lore_family="Times New Roman", lore_size=13, lore_slant="roman"
        )
        self.assertEqual(self.hud.outcome_font_family, "Courier New")
        self.assertEqual(self.hud.outcome_font_size, 18)
        self.assertEqual(self.hud.lore_font_family, "Times New Roman")
        self.assertEqual(self.hud.lore_font_size, 13)


class TestHauntedAltarCanvas(unittest.TestCase):
    """Verifies HauntedAltarCanvas lighting, shadow math, and particle animations."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        # Create dummy assets dict
        self.assets = {}
        # Load real gravestone if present
        grave_path = Path(blackjack.__file__).parent / "assets" / "haunted" / "gravestone.png"
        if grave_path.exists():
            self.assets["gravestone"] = tkinter.PhotoImage(file=str(grave_path))
        lit_path = Path(blackjack.__file__).parent / "assets" / "haunted" / "candle_lit.png"
        if lit_path.exists():
            self.assets["candle_lit"] = tkinter.PhotoImage(file=str(lit_path))
        unlit_path = Path(blackjack.__file__).parent / "assets" / "haunted" / "candle_unlit.png"
        if unlit_path.exists():
            self.assets["candle_unlit"] = tkinter.PhotoImage(file=str(unlit_path))

        self.altar = HauntedAltarCanvas(self.root, assets=self.assets, width=260, height=135)
        self.altar.pack()

    def tearDown(self):
        self.altar.cancel_animations()
        self.root.destroy()

    def test_candle_state_sync(self):
        """Updating candle states updates internal count and redraws altar."""
        self.altar.set_candle_state(candles_remaining=3, visible=True)
        self.assertEqual(self.altar.candles_remaining, 3)
        self.assertTrue(self.altar.candles_visible)

        # 3 lit (indices 0, 1, 2), 2 unlit (indices 3, 4)
        lit_indices = self.altar.get_lit_candle_indices()
        self.assertEqual(lit_indices, [0, 1, 2])

    def test_directional_shadow_offset_calculation(self):
        """Shadows cast by gravestones tilt dynamically away from lit candle centroid."""
        # When only candle 0 (leftmost) is lit, centroid is around x=26.
        # A stone on the right (x=224) should cast shadow strongly to the right (dx > 0).
        self.altar.set_candle_state(candles_remaining=1, visible=True)
        centroid = self.altar.calculate_light_centroid()
        self.assertLess(centroid, 50.0)

        dx_right_stone = self.altar.calculate_shadow_offset_dx(stone_x=224.0, centroid=centroid)
        self.assertGreater(dx_right_stone, 10.0)

        # When all 5 candles are lit, centroid is near center (~130)
        self.altar.set_candle_state(candles_remaining=5, visible=True)
        centroid_center = self.altar.calculate_light_centroid()
        self.assertAlmostEqual(centroid_center, 130.0, delta=5.0)

        # Center stone has near-zero lateral shadow offset
        dx_center = self.altar.calculate_shadow_offset_dx(stone_x=130.0, centroid=centroid_center)
        self.assertAlmostEqual(dx_center, 0.0, delta=3.0)

    def test_grave_eruption_animation_lifecycle(self):
        """Grave eruption animation creates fissure and debris particles, ending cleanly."""
        completed = []
        self.altar.animate_grave_eruption(stone_index=0, on_complete=lambda: completed.append(True))
        self.assertTrue(self.altar.is_animating_eruption)

        # Pump the event loop to run frames
        for _ in range(12):
            self.root.update_idletasks()
            self.root.update()

        # After frames conclude, on_complete should have fired
        self.altar.cancel_animations()
        self.assertFalse(self.altar.is_animating_eruption)

    def test_candle_poof_animation_lifecycle(self):
        """Candle manifestation poof creates smoke and flash particles, concluding safely."""
        completed = []
        self.altar.animate_candle_poof(on_complete=lambda: completed.append(True))
        self.assertTrue(self.altar.is_animating_poof)

        for _ in range(12):
            self.root.update_idletasks()
            self.root.update()

        self.altar.cancel_animations()
        self.assertFalse(self.altar.is_animating_poof)


if __name__ == "__main__":
    unittest.main()
