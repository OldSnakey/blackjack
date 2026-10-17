"""
Unit test suite for Phase C: Living Dealer Animation Engine & Reactive Table Juice.

Validates:
- Idle breathing oscillation ticker and vertical offset calculation ([-2, +2] bounds).
- Autonomous blinking timer scheduling and eye state transitions (open -> closed -> open).
- Dialogue typewriter mouth flapping (neutral <-> talk).
- Game event gesture triggers: deal arm sweep, hole card peek, bust gasp, and win smirk.
- Clean timer tracking and cancellation during _on_close().
- Headless safety with root.withdraw().
"""

from __future__ import annotations

import tempfile
import unittest
import tkinter
from pathlib import Path

from blackjack import BlackjackApp, Phase, Card
from save_manager import SaveManager


class TestLivingDealerAnimations(unittest.TestCase):
    """Verifies dealer living presence, breathing, blinking, and gesture systems."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_file = Path(self.temp_dir.name) / "test_save.json"

        self.root = tkinter.Tk()
        self.root.withdraw()

        self.app = BlackjackApp(self.root, sound_enabled=False)
        self.app.save_manager = SaveManager(save_path=self.save_file)

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_idle_breathing_offset_bounds(self):
        """Breathing offset stays strictly within [-2 px, +2 px] across oscillation cycles."""
        self.assertTrue(hasattr(self.app, "_dealer_breathing_tick"))
        offsets = []
        for step in range(50):
            offset = self.app._calculate_breathing_offset(step * 0.15)
            offsets.append(offset)
            self.assertGreaterEqual(offset, -2)
            self.assertLessEqual(offset, 2)
        # Verifies variation exists (not constant 0)
        self.assertGreater(max(offsets), 0)
        self.assertLess(min(offsets), 0)

    def test_autonomous_blinking_transitions(self):
        """Blinking triggers closed eyes and restores open eyes."""
        self.assertEqual(self.app.dealer_actor.eye_state, "open")
        self.app._trigger_dealer_blink(duration_ms=50)
        self.assertEqual(self.app.dealer_actor.eye_state, "closed")

        # Let scheduled after callback restore open
        self.root.update()
        # Explicit callback verification
        self.app._restore_dealer_eyes()
        self.assertEqual(self.app.dealer_actor.eye_state, "open")

    def test_dialogue_mouth_animation(self):
        """Dialogue typing animates mouth state and restores neutral when speech is dismissed."""
        self.app.set_dealer_speech("Welcome to the High Roller Suite!")
        # During speech, mouth alternates
        self.app._step_speech_mouth()
        self.assertIn(self.app.dealer_actor.mouth_state, ("talk", "neutral"))

        # Clearing speech returns to neutral
        self.app.clear_dealer_speech()
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

    def test_game_event_gestures(self):
        """Game events trigger context-appropriate dealer gestures."""
        # 1. Dealing gesture
        self.app._trigger_dealer_deal_gesture(duration_ms=100)
        self.assertEqual(self.app.dealer_actor.arm_state, "deal")
        self.app._restore_dealer_arms()
        self.assertEqual(self.app.dealer_actor.arm_state, "rest")

        # 2. Peeking gesture
        self.app._trigger_dealer_peek_gesture(duration_ms=100)
        self.assertEqual(self.app.dealer_actor.arm_state, "peek")
        self.app._restore_dealer_arms()
        self.assertEqual(self.app.dealer_actor.arm_state, "rest")

        # 3. Bust gasp
        self.app._trigger_dealer_gasp()
        self.assertEqual(self.app.dealer_actor.mouth_state, "gasp")
        self.app._restore_dealer_mouth()
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

        # 4. Win smirk
        self.app._trigger_dealer_smirk()
        self.assertEqual(self.app.dealer_actor.mouth_state, "smirk")
        self.app._restore_dealer_mouth()
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

    def test_timer_cleanup_on_close(self):
        """Closing the application cleanly cancels all dealer living animation timers."""
        self.app._schedule_dealer_blink()
        self.assertIsNotNone(self.app._dealer_blink_timer_id)

        self.app._on_close()
        self.assertIsNone(self.app._dealer_blink_timer_id)
        self.assertIsNone(self.app._dealer_idle_timer_id)


if __name__ == "__main__":
    unittest.main()
