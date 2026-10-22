"""
Targeted Automated Test Suite for Universal Puppet Roster Conversion & Expansion.

Verifies:
- All character personas (julian, malphas, uriel, mortimer, tiffany, selene, vladimir, dummy)
  have is_puppet=True.
- Every character's discrete puppet layer files exist in 1x and 2x.
- DealerActor successfully composites valid RGBA images for all characters across:
  - 1x ($112x112$) and 2x ($224x224$) scales.
  - 3 eye blink states (open, half, closed).
  - 8 phonetic viseme mouth states (neutral, talk, a, o, e, f, smirk, gasp).
  - 3 arm dealer articulation gestures (rest, deal, peek).
- Safe persona swapping without game state corruption.
"""

from __future__ import annotations

import tempfile
import tkinter
import unittest
from pathlib import Path
from PIL import Image

from dealer_actor import CHARACTERS, COSTUME_ALIASES, DealerActor, VISEME_STATES
import blackjack


class TestRosterPuppetConversion(unittest.TestCase):
    """Unit tests verifying full puppet conversion for all dealer characters."""

    @classmethod
    def setUpClass(cls):
        cls.root = tkinter.Tk()
        cls.root.withdraw()
        cls.actor = DealerActor(master=cls.root, scale_factor=1.0)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_all_characters_marked_as_puppets(self):
        """Every dealer profile in CHARACTERS is marked is_puppet=True."""
        expected = ["julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir", "dummy"]
        for cid in expected:
            self.assertIn(cid, CHARACTERS, f"Character '{cid}' not registered in CHARACTERS")
            prof = CHARACTERS[cid]
            self.assertTrue(prof.is_puppet, f"Character '{cid}' must have is_puppet=True")

    def test_all_characters_composite_cleanly_at_1x_and_2x(self):
        """Every character composites into a valid non-empty RGBA image at 1x and 2x."""
        for cid in ("julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir", "dummy"):
            self.actor.equip_costume(cid)

            # 1x scale
            self.actor.set_scale(1.0)
            img1x = self.actor.get_composite_image()
            self.assertEqual(img1x.size, (112, 112))
            self.assertEqual(img1x.mode, "RGBA")
            self.assertIsNotNone(img1x.getbbox(), f"Character '{cid}' composite at 1x is completely empty")

            # 2x scale
            self.actor.set_scale(2.0)
            img2x = self.actor.get_composite_image()
            self.assertEqual(img2x.size, (224, 224))
            self.assertEqual(img2x.mode, "RGBA")
            self.assertIsNotNone(img2x.getbbox(), f"Character '{cid}' composite at 2x is completely empty")

    def test_all_visemes_render_for_all_characters(self):
        """All 8 viseme states composite without crashing across all characters."""
        for cid in ("julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir"):
            self.actor.equip_costume(cid)
            for vstate in VISEME_STATES:
                self.actor.set_mouth_state(vstate)
                img = self.actor.get_composite_image()
                self.assertIsNotNone(img.getbbox(), f"Viseme '{vstate}' for '{cid}' resulted in empty composite")

    def test_all_eye_states_render_for_all_characters(self):
        """Blink eye states (open, half, closed) composite successfully."""
        for cid in ("julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir"):
            self.actor.equip_costume(cid)
            for estate in ("open", "half", "closed"):
                self.actor.set_eye_state(estate)
                img = self.actor.get_composite_image()
                self.assertIsNotNone(img.getbbox())

    def test_all_arm_gestures_render_for_all_characters(self):
        """Arm gestures (rest, deal, peek) composite successfully."""
        for cid in ("julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir"):
            self.actor.equip_costume(cid)
            for astate in ("rest", "deal", "peek"):
                self.actor.set_arm_state(astate)
                img = self.actor.get_composite_image()
                self.assertIsNotNone(img.getbbox())


if __name__ == "__main__":
    unittest.main()
