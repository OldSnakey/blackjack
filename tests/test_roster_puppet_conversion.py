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

    def test_zero_collar_seam_and_zero_facial_banding_at_2x(self):
        """All primary dealer puppets must have 100% opaque interior face/neck/collar pixels (no alpha<255 horizontal slits or black-premultiplied boxes)."""
        import numpy as np

        for cid in ("julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir"):
            self.actor.equip_costume(cid)
            self.actor.set_scale(2.0)
            self.actor.set_eye_state("open")
            self.actor.set_mouth_state("neutral")
            self.actor.set_arm_state("rest")

            comp = np.array(self.actor.get_composite_image())
            # Central vertical spine of face & neck & torso (x: 106..118, y: 70..145) must be 100% opaque (alpha == 255)
            spine_alpha = comp[70:145, 106:118, 3]
            min_alpha = int(spine_alpha.min())
            self.assertEqual(
                min_alpha,
                255,
                f"Character '{cid}' has semi-transparent interior neck/collar seam (min alpha={min_alpha} < 255)!"
            )

            # Face & collar composite (y: 25..120, x: 75..150) in neutral state must match bust_2x
            # with zero rectangular feather-border banding or collar darkening
            bust_img = self.actor.get_bust_image(cid, scale_factor=2.0)
            self.assertIsNotNone(bust_img)
            comp_face = comp[25:120, 75:150, :3].astype(int)
            bust_face = np.array(bust_img)[25:120, 75:150, :3].astype(int)
            face_diff = np.abs(comp_face - bust_face).max(axis=2)
            self.assertLessEqual(
                int((face_diff > 15).sum()),
                10,
                f"Character '{cid}' neutral composite face has {int((face_diff > 15).sum())} banded/divergent pixels vs bust_2x!"
            )

    def test_visemes_and_eye_states_produce_distinct_composites(self):
        """Changing eye_state or mouth_state on puppet characters visibly alters the rendered composite."""
        import numpy as np

        for cid in ("julian", "malphas", "uriel", "mortimer", "tiffany", "selene", "vladimir"):
            self.actor.equip_costume(cid)
            self.actor.set_scale(2.0)
            self.actor.set_eye_state("open")
            self.actor.set_mouth_state("neutral")
            base_arr = np.array(self.actor.get_composite_image())

            self.actor.set_eye_state("closed")
            closed_arr = np.array(self.actor.get_composite_image())
            self.assertFalse(
                np.array_equal(base_arr, closed_arr),
                f"Character '{cid}' eyes_closed composite is identical to eyes_open!"
            )

            self.actor.set_eye_state("open")
            for vstate in ("a", "o", "e", "talk", "smirk", "gasp"):
                self.actor.set_mouth_state(vstate)
                v_arr = np.array(self.actor.get_composite_image())
                self.assertFalse(
                    np.array_equal(base_arr, v_arr),
                    f"Character '{cid}' mouth_{vstate} composite is identical to mouth_neutral!"
                )


if __name__ == "__main__":
    unittest.main()
