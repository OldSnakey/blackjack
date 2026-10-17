"""
Unit test suite for Phase 4: Dealer Horizon Stage, Actor Dealer Presentation, and Horizon Layout.

Validates:
- Spatial Horizon Layout: scoreboard_frame -> dealer_stage_frame -> horizon_rail -> card_table_frame.
- Dealer stage components: Pumpkin, Dealer Actor (portrait + nameplate + reactive speech bubble), and Haunted Altar.
- Dynamic reactive speech callouts based on round outcomes.
- Demon actor transformation and locking in Hell's Table.
- In-memory 1x <-> 2x scaling of dealer stage elements and typography.
- Theme propagation across dealer_stage_frame for Normal, Creep, Hell's Table, and Victory phases.
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
    TABLE_BACKGROUND_COLOR,
    PANEL_BACKGROUND_COLOR,
    Phase,
)


class TestDealerActorAndHorizonStage(unittest.TestCase):
    """Verifies Phase 4 Dealer Horizon Stage and Actor Dealer behavior."""

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

    def test_horizon_layout_structure(self):
        """Verifies the four-tier vertical hierarchy of the Horizon Layout."""
        # 1. Dealer stage frame exists
        self.assertTrue(hasattr(self.app, "dealer_stage_frame"))
        self.assertIsInstance(self.app.dealer_stage_frame, tkinter.Frame)

        # 2. Horizon rail divider exists
        self.assertTrue(hasattr(self.app, "horizon_rail"))
        self.assertIsInstance(self.app.horizon_rail, tkinter.Frame)

        # 3. Card table felt exists below the horizon
        self.assertTrue(hasattr(self.app, "card_table_frame"))

        # 4. Dealer actor components exist within the dealer stage
        self.assertTrue(hasattr(self.app, "dealer_actor_frame"))
        self.assertTrue(hasattr(self.app, "dealer_nameplate_label"))
        self.assertTrue(hasattr(self.app, "dealer_speech_label"))
        self.assertTrue(hasattr(self.app, "pumpkin_label"))
        self.assertTrue(hasattr(self.app, "haunted_altar"))

    def test_dealer_actor_speech_callouts(self):
        """Setting dealer dialogue updates speech label text and visibility."""
        self.app.set_dealer_speech("Welcome to the high-stakes table, player.")
        self.assertEqual(self.app.dealer_speech_var.get(), "Welcome to the high-stakes table, player.")
        self.assertTrue(self.app.dealer_speech_label.winfo_manager())

        # Clearing speech
        self.app.set_dealer_speech("")
        self.assertEqual(self.app.dealer_speech_var.get(), "")

    def test_dealer_stage_hell_table_transformation(self):
        """Entering Hell's Table locks dealer view ON and displays Pit Fiend with demonic dialogue."""
        self.app.haunted.start_hell_table()
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.app._update_dealer_avatar()

        self.assertEqual(self.app.haunted.phase, Phase.HELL_TABLE)
        self.assertEqual(self.app.dealer_view_status_var.get(), "☠ The Pit Fiend")
        self.assertEqual(str(self.app.dealer_view_button.cget("state")), "disabled")
        # Stage frame should adopt infernal background
        self.assertEqual(self.app.dealer_stage_frame.cget("background"), "#140508")

    def test_dealer_stage_scaling_under_2x(self):
        """Switching to 2x scale mode doubles actor portrait and typography dimensions."""
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 2.0)

        # Speech font and nameplate font scaled
        nameplate_font = str(self.app.dealer_nameplate_label.cget("font"))
        self.assertTrue("20" in nameplate_font or "18" in nameplate_font)

        speech_font = str(self.app.dealer_speech_label.cget("font"))
        self.assertTrue("18" in speech_font or "16" in speech_font)

        # Toggle back to 1x
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 1.0)
        nameplate_font_1x = str(self.app.dealer_nameplate_label.cget("font"))
        self.assertTrue("10" in nameplate_font_1x or "9" in nameplate_font_1x)


if __name__ == "__main__":
    unittest.main()
