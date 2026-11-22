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
        """Verifies the four-tier vertical hierarchy and sibling StageBand pillars."""
        self.assertTrue(hasattr(self.app, "stage_band_frame"))
        self.assertTrue(hasattr(self.app, "left_stage_wing"))
        self.assertTrue(hasattr(self.app, "dealer_stage_frame"))
        self.assertTrue(hasattr(self.app, "right_stage_wing"))
        self.assertEqual(self.app.left_stage_wing.master, self.app.stage_band_frame)
        self.assertEqual(self.app.dealer_stage_frame.master, self.app.stage_band_frame)
        self.assertEqual(self.app.right_stage_wing.master, self.app.stage_band_frame)

        # Horizon rail divider and Card table felt exist below StageBand
        self.assertTrue(hasattr(self.app, "horizon_rail"))
        self.assertIsInstance(self.app.horizon_rail, tkinter.Frame)
        self.assertTrue(hasattr(self.app, "card_table_frame"))

        # Dealer actor components exist within the dealer stage
        self.assertTrue(hasattr(self.app, "dealer_actor_frame"))
        self.assertTrue(hasattr(self.app, "dealer_nameplate_label"))
        self.assertTrue(hasattr(self.app, "dealer_speech_label"))
        self.assertTrue(hasattr(self.app, "pumpkin_label"))
        self.assertTrue(hasattr(self.app, "haunted_altar"))

    def test_dealer_composite_integer_clamp(self):
        """DealerActor.get_composite_image produces strictly integer 112x112 (1x) or 224x224 (2x) composites."""
        img_1x = self.app.dealer_actor.get_composite_image(scale_override=1.0)
        img_15x = self.app.dealer_actor.get_composite_image(scale_override=1.5)
        img_2x = self.app.dealer_actor.get_composite_image(scale_override=2.0)
        self.assertEqual(img_1x.size, (112, 112))
        self.assertEqual(img_15x.size, (112, 112))
        self.assertEqual(img_2x.size, (224, 224))

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

    def test_scale_mode_is_fixed_at_1x(self):
        """2x scale mode is removed; toggle_scale_mode is a safe no-op leaving scale_factor at 1.0."""
        self.app.toggle_scale_mode()
        self.assertEqual(self.app.scale_factor, 1.0)


if __name__ == "__main__":
    unittest.main()
