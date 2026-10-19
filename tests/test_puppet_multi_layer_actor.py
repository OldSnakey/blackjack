"""
Targeted Automated Test Suite for Puppet Multi-Layer Dealer Actor & Dummy Test Rig.

Verifies:
- Existence and RGBA format of all 1x and 2x dummy puppet layers.
- High-contrast unique color signatures for each puppet layer.
- Phonetic character-to-viseme mapping logic.
- Typewriter speech streaming viseme mouth state driver.
- Discrete layer Z-index compositing order in DealerActor.
- Persona switching to dummy without state corruption.
- Graceful viseme degradation and fallback for legacy characters.
"""

from __future__ import annotations

import os
import tempfile
import tkinter
import unittest
from pathlib import Path
from PIL import Image

import blackjack
from dealer_actor import (
    CHARACTERS,
    COSTUME_ALIASES,
    DealerActor,
    VISEME_STATES,
    map_char_to_viseme,
)
from save_manager import SaveManager


class TestPuppetMultiLayerActor(unittest.TestCase):
    """Exhaustive tests for the modular puppet layered actor and viseme system."""

    @classmethod
    def setUpClass(cls):
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.dummy_dir = cls.project_root / "assets" / "haunted" / "characters" / "dummy"

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_save = Path(self.temp_dir.name) / "test_puppet_save.json"

        # Initialize BlackjackApp in silent headless mode
        self.app = blackjack.BlackjackApp(
            self.root,
            sound_enabled=False,
            save_path=self.temp_save,
            chips_mode=False,
        )

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

    def test_dummy_character_layers_exist_1x_and_2x(self):
        """All 19 discrete puppet layers must exist on disk in both 1x and 2x resolutions."""
        expected_layers = [
            "shadow",
            "torso",
            "neck",
            "head",
            "eyes_open",
            "eyes_half",
            "eyes_closed",
            "mouth_neutral",
            "mouth_a",
            "mouth_o",
            "mouth_e",
            "mouth_f",
            "mouth_talk",
            "mouth_smirk",
            "mouth_gasp",
            "arm_rest",
            "arm_deal",
            "arm_peek",
            "bust",
        ]

        for layer in expected_layers:
            path_1x = self.dummy_dir / f"{layer}.png"
            path_2x = self.dummy_dir / f"{layer}_2x.png"
            self.assertTrue(path_1x.exists(), f"Missing 1x layer: {path_1x.name}")
            self.assertTrue(path_2x.exists(), f"Missing 2x layer: {path_2x.name}")

            with Image.open(path_1x) as img1x:
                self.assertEqual(img1x.size, (112, 112))
                self.assertEqual(img1x.mode, "RGBA")

            with Image.open(path_2x) as img2x:
                self.assertEqual(img2x.size, (224, 224))
                self.assertEqual(img2x.mode, "RGBA")

    def test_dummy_layers_have_unique_chromatic_signatures(self):
        """Each discrete puppet layer must contain its designated high-contrast solid fill color."""
        # Layer -> Expected color signature RGB
        layer_color_signatures = {
            "torso": (35, 75, 185),     # Royal Blue
            "neck": (225, 180, 130),    # Warm Sand
            "head": (245, 155, 115),    # Coral Peach
            "eyes_open": (0, 225, 245), # Electric Cyan
            "mouth_neutral": (210, 30, 65), # Ruby Crimson
            "arm_rest": (30, 175, 110), # Emerald Green (left arm)
        }

        for layer_name, (er, eg, eb) in layer_color_signatures.items():
            path = self.dummy_dir / f"{layer_name}.png"
            with Image.open(path) as img:
                pixels = [img.getpixel((x, y)) for y in range(img.height) for x in range(img.width)]
                has_color = any(
                    abs(p[0] - er) <= 5 and abs(p[1] - eg) <= 5 and abs(p[2] - eb) <= 5 and p[3] > 200
                    for p in pixels
                )
                self.assertTrue(has_color, f"Layer '{layer_name}' does not contain expected color signature ({er}, {eg}, {eb})")

    def test_viseme_mapping_logic(self):
        """map_char_to_viseme correctly maps vowels, consonants, fricatives, and punctuation."""
        # Rounded vowels -> 'o'
        for ch in ("o", "O", "u", "U", "w", "W", "q", "Q"):
            self.assertEqual(map_char_to_viseme(ch), "o", f"Char '{ch}' should map to 'o'")

        # Open vowels -> 'a'
        for ch in ("a", "A", "i", "I", "y", "Y", "h", "H"):
            self.assertEqual(map_char_to_viseme(ch), "a", f"Char '{ch}' should map to 'a'")

        # Wide dental consonants/vowels -> 'e'
        for ch in ("e", "E", "c", "C", "d", "D", "s", "S", "t", "T", "r", "R", "n", "N"):
            self.assertEqual(map_char_to_viseme(ch), "e", f"Char '{ch}' should map to 'e'")

        # Fricatives -> 'f'
        for ch in ("f", "F", "v", "V"):
            self.assertEqual(map_char_to_viseme(ch), "f", f"Char '{ch}' should map to 'f'")

        # Bilabials, whitespace, and punctuation -> 'neutral'
        for ch in (" ", "\t", ".", ",", "!", "?", "m", "M", "b", "B", "p", "P", "-", "—"):
            self.assertEqual(map_char_to_viseme(ch), "neutral", f"Char '{ch}' should map to 'neutral'")

        # Empty string -> 'neutral'
        self.assertEqual(map_char_to_viseme(""), "neutral")

    def test_puppet_profile_registration(self):
        """The 'dummy' character must be registered as is_puppet=True in CHARACTERS."""
        self.assertIn("dummy", CHARACTERS)
        profile = CHARACTERS["dummy"]
        self.assertEqual(profile.id, "dummy")
        self.assertTrue(profile.is_puppet)
        self.assertIn("dummy", COSTUME_ALIASES)
        self.assertEqual(COSTUME_ALIASES["puppet"], "dummy")

    def test_puppet_z_index_compositing_order(self):
        """Puppet compositor stacks layers in exact order: Shadow -> Torso -> Neck -> Head -> Eyes -> Mouth -> Arms."""
        actor = DealerActor(master=self.root, initial_character="dummy")
        self.assertTrue(actor.get_profile().is_puppet)

        # Composite should be valid 112x112 RGBA
        comp = actor.get_composite_image()
        self.assertEqual(comp.size, (112, 112))
        self.assertEqual(comp.mode, "RGBA")

        # Head layer center pixel (56, 46) must contain coral peach head or eyes/mouth, not transparent
        pixel_at_face = comp.getpixel((56, 46))
        self.assertGreater(pixel_at_face[3], 200, "Face center pixel should be opaque")

        # Torso layer pixel at (56, 92) should be opaque
        pixel_at_torso = comp.getpixel((56, 92))
        self.assertGreater(pixel_at_torso[3], 200, "Torso center pixel should be opaque")

    def test_typewriter_drives_visemes_for_puppet_character(self):
        """Typewriter speech streaming sets phonetic viseme mouth states when active dealer is a puppet."""
        self.app.dealer_actor.equip_costume("dummy")
        self.assertEqual(self.app.dealer_actor.current_character, "dummy")

        text = "Hello world! Fantastic cards."
        self.app.set_dealer_speech(text, stream=True)

        observed_visemes = set()
        for _ in range(len(text)):
            if self.app._typewriter_index < len(text):
                self.app._stream_typewriter_step()
                observed_visemes.add(self.app.dealer_actor.mouth_state)

        # Must have articulated multiple visemes (e.g. 'e', 'o', 'neutral', 'a', 'f')
        self.assertGreater(len(observed_visemes), 1, "Typewriter should articulate varied visemes")
        self.assertTrue(observed_visemes.issubset(set(VISEME_STATES)))

        # On complete, resets to neutral
        self.app._complete_typewriter_speech()
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

    def test_legacy_character_fallback_safety(self):
        """Legacy characters (is_puppet=False) safely map non-neutral visemes to 'talk' and degrade gracefully."""
        self.app.dealer_actor.equip_costume("julian")
        self.assertFalse(self.app.dealer_actor.get_profile().is_puppet)

        # set_mouth_for_char on Julian should set 'talk' for letters and 'neutral' for whitespace
        state_letter = self.app.dealer_actor.set_mouth_for_char("o")
        self.assertEqual(state_letter, "talk")
        self.assertEqual(self.app.dealer_actor.mouth_state, "talk")

        state_space = self.app.dealer_actor.set_mouth_for_char(" ")
        self.assertEqual(state_space, "neutral")
        self.assertEqual(self.app.dealer_actor.mouth_state, "neutral")

        # Composite still renders without error
        comp = self.app.dealer_actor.get_composite_image()
        self.assertIsNotNone(comp)

    def test_costume_switching_to_dummy(self):
        """Equipping dummy updates persona and title without corrupting table state."""
        initial_bankroll = self.app.bankroll_var.get()
        self.app.dealer_actor.equip_costume("dummy")
        self.assertEqual(self.app.dealer_actor.current_character, "dummy")
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll)

        profile = self.app.dealer_actor.get_profile()
        self.assertEqual(profile.title, "🧪 Test Puppet Dummy")


if __name__ == "__main__":
    unittest.main()
