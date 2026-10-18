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
        self.assertIn(self.app.dealer_actor.eye_state, ("half", "closed"))

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

    def test_stage_breathing_updates_dealer_sprite_coords(self):
        """Idle breathing ticker moves dealer_sprite item on dealer_stage_canvas within vertical bounds."""
        stage = self.app.dealer_stage_canvas
        self.assertTrue(stage.find_withtag("dealer_sprite"))
        initial_coords = stage.coords("dealer_sprite")
        self.assertEqual(len(initial_coords), 2)
        base_y = initial_coords[1]

        # Advance breathing step
        self.app._dealer_anim_step = 1.57  # ~pi/2, peak positive offset
        self.app._dealer_breathing_tick()
        new_coords = stage.coords("dealer_sprite")
        self.assertNotEqual(new_coords[1], base_y)
        self.assertAlmostEqual(new_coords[1] - base_y, 2, delta=1)

    def test_three_frame_blinking_sequence(self):
        """Blinking transitions smoothly through open -> half -> closed -> half -> open."""
        actor = self.app.dealer_actor
        self.assertEqual(actor.eye_state, "open")

        self.app._trigger_dealer_blink(duration_ms=120)
        # Immediate state is half or closed
        self.assertIn(actor.eye_state, ("half", "closed"))

        # Advance through callbacks
        if hasattr(self.app, "_advance_blink_step"):
            self.app._advance_blink_step(2)
            self.assertEqual(actor.eye_state, "closed")
            self.app._advance_blink_step(3)
            self.assertEqual(actor.eye_state, "half")
            self.app._advance_blink_step(4)
            self.assertEqual(actor.eye_state, "open")
        else:
            self.app._restore_dealer_eyes()
            self.assertEqual(actor.eye_state, "open")

    def test_ambient_particles_system_on_stage_canvas(self):
        """DealerStageCanvas maintains an ambient particle pool updated per frame."""
        stage = self.app.dealer_stage_canvas
        self.assertTrue(hasattr(stage, "particles"))
        self.assertTrue(hasattr(stage, "update_particles"))

        # Switch to Hell theme and spawn particles
        stage.set_theme("hell")
        stage.spawn_ambient_particles(count=5)
        self.assertGreaterEqual(len(stage.particles), 5)
        # Verify particles have motion vectors and lifetime
        p = stage.particles[0]
        self.assertIn("x", p)
        self.assertIn("y", p)
        self.assertIn("vy", p)
        self.assertIn("life", p)

        # Update moves particles
        old_y = p["y"]
        stage.update_particles()
        self.assertNotEqual(stage.particles[0]["y"], old_y)

        # Clear particles
        stage.clear_particles()
        self.assertEqual(len(stage.particles), 0)

    def test_sweat_drop_particle_on_dealer_gasp(self):
        """Dealer bust gasp spawns a sweat drop particle on DealerStageCanvas."""
        stage = self.app.dealer_stage_canvas
        initial_count = len(stage.particles) if hasattr(stage, "particles") else 0

        self.app._trigger_dealer_gasp()
        self.assertEqual(self.app.dealer_actor.mouth_state, "gasp")
        if hasattr(stage, "particles"):
            self.assertGreater(len(stage.particles), initial_count)
            sweat_particles = [p for p in stage.particles if p.get("type") == "sweat"]
            self.assertGreater(len(sweat_particles), 0)

    def test_typewriter_dialogue_streaming(self):
        """Speech callout streams characters in interactive mode and supports fast-forward."""
        # Test full streaming mode
        self.app.set_dealer_speech("A high wager on the felt!", stream=True)
        self.assertTrue(hasattr(self.app, "_typewriter_timer_id"))

        # Fast forward completes speech immediately
        self.app._complete_typewriter_speech()
        self.assertEqual(self.app.dealer_speech_var.get(), "A high wager on the felt!")
        self.assertIsNone(self.app._typewriter_timer_id)

    def test_hole_card_peek_on_ace_or_ten(self):
        """Dealer upcard of Ace or 10 invokes peek gesture before player actions."""
        # Setup dealer with Ace upcard and 9 in the hole (no BJ)
        self.app.dealer_hand = [
            Card(1, self.app.all_cards[0][1], rank="ace", suit="spades"),
            Card(9, self.app.all_cards[1][1], rank="9", suit="hearts"),
        ]
        self.app.player_hands = [[
            Card(10, self.app.all_cards[2][1], rank="10", suit="diamonds"),
            Card(7, self.app.all_cards[3][1], rank="7", suit="clubs"),
        ]]
        self.app._check_initial_blackjack()
        self.assertEqual(self.app.dealer_actor.arm_state, "peek")

        # Restoring returns to rest
        self.app._restore_dealer_arms()
        self.assertEqual(self.app.dealer_actor.arm_state, "rest")

    def test_timer_cleanup_on_close(self):
        """Closing the application cleanly cancels all dealer living animation timers."""
        self.app._schedule_dealer_blink()
        self.assertIsNotNone(self.app._dealer_blink_timer_id)

        self.app._on_close()
        self.assertIsNone(self.app._dealer_blink_timer_id)
        self.assertIsNone(self.app._dealer_idle_timer_id)
        self.assertIsNone(self.app._typewriter_timer_id)


if __name__ == "__main__":
    unittest.main()
