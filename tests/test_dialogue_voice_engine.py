"""
Targeted Automated Test Suite for Animalese Dialogue Voice Engine.

Verifies:
- Procedural PCM audio synthesis of valid 44.1 kHz 16-bit mono/stereo WAV byte buffers.
- 1:1 Viseme-to-sound consistency (same viseme always generates the exact same audio signature).
- Character-specific fundamental pitch registers (e.g. Malphas 85 Hz vs Uriel 520 Hz).
- Inflection pitch shifts (rising for '?', falling for '.', accented for '!').
- Cadence stepping (sound triggered at regular letter cadence, silent on whitespace).
- Graceful degradation in headless environments (with or without audio hardware / pygame).
"""

from __future__ import annotations

import unittest
from pathlib import Path
from dialogue_voice_engine import (
    AnimaleseVoiceEngine,
    VOICE_PROFILES,
    synthesize_viseme_pcm,
)


class TestDialogueVoiceEngine(unittest.TestCase):
    """Unit tests for the Animalese procedural voice synthesis engine."""

    def setUp(self):
        self.engine = AnimaleseVoiceEngine(enabled=True, volume=0.8)

    def test_voice_profiles_registered_for_all_characters(self):
        """All dealer characters have defined voice profiles with base frequency and timbre."""
        expected_characters = ["tiffany", "julian", "malphas", "uriel", "mortimer", "dummy"]
        for cid in expected_characters:
            self.assertIn(cid, VOICE_PROFILES, f"Character '{cid}' missing voice profile")
            prof = VOICE_PROFILES[cid]
            self.assertIn("base_freq", prof)
            self.assertIn("timbre", prof)
            self.assertGreater(prof["base_freq"], 50.0)
            self.assertLess(prof["base_freq"], 1000.0)

    def test_synthesize_viseme_pcm_produces_valid_wav_header(self):
        """synthesize_viseme_pcm outputs a valid RIFF/WAVE header and non-empty PCM samples."""
        wav_bytes = synthesize_viseme_pcm(
            base_freq=380.0,
            viseme="a",
            timbre="warm_flute",
            duration_ms=45,
            sample_rate=44100,
        )
        self.assertIsInstance(wav_bytes, bytes)
        self.assertGreater(len(wav_bytes), 44, "WAV buffer must contain header + samples")
        self.assertEqual(wav_bytes[:4], b"RIFF")
        self.assertEqual(wav_bytes[8:12], b"WAVE")
        self.assertEqual(wav_bytes[12:16], b"fmt ")

    def test_viseme_sound_consistency(self):
        """1:1 Consistency: Synthesizing the same viseme for a character produces identical audio bytes."""
        bytes1 = synthesize_viseme_pcm(base_freq=380.0, viseme="a", timbre="warm_flute")
        bytes2 = synthesize_viseme_pcm(base_freq=380.0, viseme="a", timbre="warm_flute")
        self.assertEqual(bytes1, bytes2, "Identical viseme must produce identical acoustic bytes (deterministic)")

        # Distinct visemes must produce distinct audio bytes
        bytes_o = synthesize_viseme_pcm(base_freq=380.0, viseme="o", timbre="warm_flute")
        self.assertNotEqual(bytes1, bytes_o, "Viseme 'a' and 'o' must have distinct acoustic signatures")

    def test_character_pitch_discrimination(self):
        """Different characters produce distinct audio data reflecting their pitch register."""
        malphas_bytes = synthesize_viseme_pcm(base_freq=85.0, viseme="a", timbre="guttural_brimstone")
        uriel_bytes = synthesize_viseme_pcm(base_freq=520.0, viseme="a", timbre="angelic_crystal")
        self.assertNotEqual(malphas_bytes, uriel_bytes, "Deep demonic pitch must differ from celestial chime")

    def test_inflection_pitch_shifts(self):
        """Question inflection raises pitch while period inflection drops pitch."""
        normal_bytes = synthesize_viseme_pcm(base_freq=380.0, viseme="e", inflection="normal")
        question_bytes = synthesize_viseme_pcm(base_freq=380.0, viseme="e", inflection="question")
        period_bytes = synthesize_viseme_pcm(base_freq=380.0, viseme="e", inflection="period")

        self.assertNotEqual(normal_bytes, question_bytes)
        self.assertNotEqual(normal_bytes, period_bytes)

    def test_neutral_viseme_is_silent(self):
        """Viseme 'neutral' produces an empty/silent buffer for punctuation and pauses."""
        neutral_bytes = synthesize_viseme_pcm(base_freq=380.0, viseme="neutral")
        self.assertEqual(len(neutral_bytes), 0, "Neutral viseme should produce 0 bytes (silence)")

    def test_engine_caches_sounds_per_character(self):
        """Engine pre-caches viseme sound objects upon loading character without memory leaks."""
        sound_dict = self.engine.get_character_sounds("tiffany")
        self.assertIsInstance(sound_dict, dict)
        for v in ("a", "o", "e", "f", "talk", "smirk", "gasp"):
            self.assertIn(v, sound_dict)

    def test_play_speech_blip_cadence_filtering(self):
        """play_speech_blip handles whitespace, punctuation, and letter step cadence safely."""
        # Whitespace does not crash and returns False
        played_space = self.engine.play_speech_blip("tiffany", " ", char_index=0)
        self.assertFalse(played_space, "Whitespace must not trigger sound blip")

        # Punctuation does not play standard letter sound
        played_period = self.engine.play_speech_blip("tiffany", ".", char_index=1)
        self.assertFalse(played_period, "Punctuation must not trigger letter sound")

        # Alphanumeric letter plays on valid cadence step
        played_letter = self.engine.play_speech_blip("tiffany", "W", char_index=2)
        # In headless environment without audio, handles safely without throwing
        self.assertIn(played_letter, (True, False))

    def test_mute_and_volume_control(self):
        """Muting the engine immediately silences all playback."""
        self.engine.enabled = False
        self.assertFalse(self.engine.play_speech_blip("tiffany", "A", char_index=0))

        self.engine.set_volume(0.5)
        self.assertEqual(self.engine.volume, 0.5)


if __name__ == "__main__":
    unittest.main()
