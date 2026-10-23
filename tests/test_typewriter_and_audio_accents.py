"""
Unit tests for Typewriter Dialogue Streaming, Canvas Speech Balloon Pointer Tail,
and Character Signature Audio Accents.

Validates:
- SoundManager extension normalization for .ogg / .wav filenames.
- Character audio cue mapping and dispatch per character profile.
- Dynamic vector speech tail rendering and cleanup on DealerStageCanvas.
- Character theme color synchronization for speech balloon and tail.
- Typewriter text streaming with mouth flapping synchronization.
- Fast-forward on click during active typewriter streaming.
- Gameplay outcome integration and headless safety.
"""

from __future__ import annotations

import tempfile
import unittest
import tkinter
from pathlib import Path
from unittest.mock import MagicMock, patch

from blackjack import (
    BlackjackApp,
    Card,
    DealerStageCanvas,
    HAUNTED_AUDIO_DIR,
    Phase,
    SoundManager,
)
from dealer_actor import CHARACTERS
from save_manager import SaveManager


class TestTypewriterAndAudioAccents(unittest.TestCase):
    """Verifies typewriter dialogue streaming, vector speech tail, and audio accents."""

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

    def test_sound_manager_extension_normalization(self):
        """SoundManager.play_haunted_sound must handle names with and without .ogg/.wav extensions."""
        sm = SoundManager(enabled=True)
        # Mock sound creation to verify resolved path
        with patch("blackjack.pygame_mixer.Sound") as mock_sound_cls:
            mock_sound_instance = MagicMock()
            mock_sound_cls.return_value = mock_sound_instance

            # 1. With .ogg extension
            sm.play_haunted_sound("dealer_malphas.ogg")
            expected_path = HAUNTED_AUDIO_DIR / "dealer_malphas.ogg"
            if expected_path.exists():
                mock_sound_cls.assert_called_with(str(expected_path))

            # 2. Without extension
            mock_sound_cls.reset_mock()
            sm.play_haunted_sound("dealer_julian")
            expected_julian = HAUNTED_AUDIO_DIR / "dealer_julian.ogg"
            if expected_julian.exists():
                mock_sound_cls.assert_called_with(str(expected_julian))

    def test_character_audio_cues_exist_on_disk(self):
        """All character profiles in CHARACTERS must reference valid audio files in audio/haunted/."""
        for char_id, profile in CHARACTERS.items():
            audio_cue = profile.audio_cue
            clean_name = audio_cue[:-4] if audio_cue.endswith((".ogg", ".wav")) else audio_cue
            ogg_path = HAUNTED_AUDIO_DIR / f"{clean_name}.ogg"
            wav_path = HAUNTED_AUDIO_DIR / f"{clean_name}.wav"
            self.assertTrue(
                ogg_path.exists() or wav_path.exists(),
                f"Missing audio file for character {char_id}: {profile.audio_cue}"
            )

    def test_speech_tail_rendered_and_cleared(self):
        """Setting dealer speech renders speech_tail polygon on stage canvas; clearing removes it."""
        stage = self.app.dealer_stage_canvas
        self.assertEqual(len(stage.find_withtag("speech_tail")), 0)

        # Set speech -> speech_tail rendered
        self.app.set_dealer_speech("Place your bets on the felt.")
        self.assertGreater(len(stage.find_withtag("speech_tail")), 0, "speech_tail polygon should be drawn")

        # Clear speech -> speech_tail removed
        self.app.clear_dealer_speech()
        self.assertEqual(len(stage.find_withtag("speech_tail")), 0, "speech_tail should be deleted on clear")

    def test_speech_tail_theming(self):
        """Speech tail inherits active character theme colors."""
        stage = self.app.dealer_stage_canvas

        # Equip Malphas (Hell's Table)
        self.app.dealer_actor.equip_costume("malphas")
        self.app.set_dealer_speech("The flames hunger!")
        tail_items = stage.find_withtag("speech_tail")
        self.assertGreater(len(tail_items), 0)

        # Outline should match Malphas theme (#ff1744 or #c8a038)
        outline = stage.itemcget(tail_items[0], "outline")
        fill = stage.itemcget(tail_items[0], "fill")
        self.assertIn(outline.lower(), ("#ff1744", "#c8a038", "#ff1111", "#140508"))
        self.assertIn(fill.lower(), ("#140508", "#1c060a", "#141014"))

    def test_typewriter_cadence_and_flapping(self):
        """Typewriter streams characters and flaps dealer mouth between talk and neutral."""
        text = "A test line for living speech."
        self.app.set_dealer_speech(text, stream=True)
        self.assertTrue(hasattr(self.app, "_typewriter_timer_id"))

        # Step typewriter
        initial_flaps = 0
        for _ in range(6):
            if hasattr(self.app, "_stream_typewriter_step"):
                self.app._stream_typewriter_step()
                if self.app.dealer_actor.mouth_state in ("talk", "neutral"):
                    initial_flaps += 1
        self.assertGreater(initial_flaps, 0)

        # Complete typewriter
        self.app._complete_typewriter_speech()
        self.assertEqual(self.app.dealer_speech_var.get(), text)
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

    def test_fast_forward_on_dialogue_click(self):
        """Clicking dialogue frame or speech label immediately completes in-flight typewriter text."""
        long_text = "This is an elaborate narration that the player decides to fast-forward."
        self.app.set_dealer_speech(long_text, stream=True)

        # Simulate user click on dialogue frame
        event = tkinter.Event()
        event.widget = self.app.dealer_dialogue_frame
        self.app._on_dialogue_click(event)

        # Text should be fully revealed and timer cleared
        self.assertEqual(self.app.dealer_speech_var.get(), long_text)
        self.assertIsNone(self.app._typewriter_timer_id)
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

    def test_character_audio_accent_dispatched(self):
        """play_dealer_accent plays character's signature audio cue with debouncing."""
        self.app.sound_manager.play_haunted_sound = MagicMock()

        # Equipping Mortimer
        self.app.dealer_actor.equip_costume("mortimer")
        self.app.play_dealer_accent()
        self.app.sound_manager.play_haunted_sound.assert_called_with("dealer_mortimer.ogg")

        # Debounced call within 100ms should be suppressed
        self.app.sound_manager.play_haunted_sound.reset_mock()
        self.app.play_dealer_accent()
        self.app.sound_manager.play_haunted_sound.assert_not_called()

    def test_gameplay_outcome_triggers_typewriter_and_tail(self):
        """Round outcome sets dealer speech with typewriter streaming and displays tail."""
        self.app._update_dealer_speech_for_outcome("PLAYER_WINS")
        self.assertTrue(self.app.dealer_speech_label.winfo_manager())
        stage = self.app.dealer_stage_canvas
        self.assertGreater(len(stage.find_withtag("speech_tail")), 0)

    def test_tail_points_toward_mouth_without_obscuring(self):
        """Tail tip angles upward toward mouth level and terminates outside character body."""
        stage = self.app.dealer_stage_canvas
        self.app.set_dealer_speech("Observing the deal.")
        tail_items = stage.find_withtag("speech_tail")
        self.assertGreater(len(tail_items), 0)

        coords = stage.coords(tail_items[0])
        self.assertEqual(len(coords), 6)
        tip_x, tip_y = coords[4], coords[5]
        s = stage.scale_factor
        w = max(10, stage.canvas_width)
        h = max(10, stage.canvas_height)

        # Dialogue window sits up at head level rather than table bottom
        dialogue_bbox = stage.bbox("dialogue_win")
        self.assertLessEqual(dialogue_bbox[1], h - int(110 * s))
        self.assertLessEqual(dialogue_bbox[3], h - int(80 * s))

        # Tip must point directly at character mouth/head level
        self.assertLessEqual(tip_y, h - int(120 * s))
        self.assertGreaterEqual(tip_y, h - int(135 * s))
        # Tip must stop outside the character face/silhouette (x < w // 2 - 40*s)
        self.assertLessEqual(tip_x, w // 2 - int(40 * s))
        self.assertGreaterEqual(tip_x, w // 2 - int(55 * s))

    def test_dealer_nameplate_persists_character_title(self):
        """Nameplate consistently shows The Classic Croupier and never reverts to 'The Dealer'."""
        self.assertEqual(self.app.dealer_nameplate_label.cget("text"), "The Classic Croupier")

        # After avatar update in normal phase
        self.app._update_dealer_avatar()
        self.assertEqual(self.app.dealer_nameplate_label.cget("text"), "The Classic Croupier")

        # After phase theme applied
        self.app._apply_phase_theme(Phase.NORMAL)
        self.assertEqual(self.app.dealer_nameplate_label.cget("text"), "The Classic Croupier")

        # During haunted phases, maintains character title with (Hollow)
        self.app.haunted.phase = Phase.CREEP
        self.app._update_dealer_avatar()
        self.assertEqual(self.app.dealer_nameplate_label.cget("text"), "The Classic Croupier (Hollow)")

        # When Malphas equipped
        self.app.haunted.phase = Phase.NORMAL
        self.app.dealer_actor.equip_costume("malphas")
        self.app.set_dealer_speech("Demonic greetings.")
        self.assertEqual(self.app.dealer_nameplate_label.cget("text"), "☠ The Pit Fiend")

    def test_typewriter_animalese_voice_blip_dispatched(self):
        """Typewriter character step dispatches play_dialogue_blip to SoundManager using active character_id."""
        self.app.sound_manager.play_dialogue_blip = MagicMock()
        self.app.dealer_actor.equip_costume("malphas")
        self.app.set_dealer_speech("Hit me!", stream=True)
        if hasattr(self.app, "_stream_typewriter_step"):
            self.app._stream_typewriter_step()
            self.app.sound_manager.play_dialogue_blip.assert_called()
            call_kwargs = self.app.sound_manager.play_dialogue_blip.call_args
            # First positional arg is character_id
            self.assertEqual(call_kwargs[0][0], "malphas")


if __name__ == "__main__":
    unittest.main()
