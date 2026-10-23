"""
Unit test suite for Universal Dealer Puppet Faceplate De-occlusion, Graphic-Novel Roster Upgrade,
Multi-Layer Puppet Kinematics, and Legacy Non-Puppet Retirement.

Verifies:
1. All 8 characters (julian, tiffany, malphas, uriel, mortimer, selene, vladimir, dummy) have
   blank mannequin faceplates on `head_2x.png` (no baked-in open eyes or neutral mouth).
2. All 8 characters have de-occluded lower torso regions behind their articulated hands/arms.
3. Selene and Vladimir feature rich graphic-novel cel-shaded artwork (> 500 unique colors)
   rather than flat geometric polygon placeholders.
4. DealerActor supports independent sub-layer kinematics (`torso_offset`, `head_offset`,
   `arm_offset`, `eye_gaze_offset`) and `set_gaze_target()`.
5. Legacy `is_puppet=False` branches in `DealerActor` are retired; all characters articulate
   full phonetic visemes natively.
"""

from __future__ import annotations

import tkinter
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

from dealer_actor import CHARACTERS, DealerActor, VISEME_STATES


class TestUniversalPuppetFaceplates(unittest.TestCase):
    """Verifies true 7-layer de-occluded puppet rigs and multi-layer kinematics."""

    @classmethod
    def setUpClass(cls):
        cls.root = tkinter.Tk()
        cls.root.withdraw()
        cls.actor = DealerActor(master=cls.root, scale_factor=2.0)
        cls.chars_dir = Path(__file__).resolve().parent.parent / "assets" / "haunted" / "characters"

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.actor.set_scale(2.0)
        self.actor.reset_kinematics()

    def test_all_characters_have_deoccluded_blank_faceplates(self):
        """
        Every dealer's `head_2x.png` must be a blank mannequin faceplate where compositing
        `eyes_open_2x.png` and `mouth_neutral_2x.png` visibly changes the eye and mouth pixels
        compared to `head_2x.png` alone.
        """
        for cid in ("julian", "tiffany", "malphas", "uriel", "mortimer", "selene", "vladimir", "dummy"):
            self.actor.equip_costume(cid)
            head_img = self.actor.get_layer_image("head", force_2x=True)
            eyes_img = self.actor.get_layer_image("eyes_open", force_2x=True)
            mouth_img = self.actor.get_layer_image("mouth_neutral", force_2x=True)

            self.assertIsNotNone(head_img, f"Missing head_2x for {cid}")
            self.assertIsNotNone(eyes_img, f"Missing eyes_open_2x for {cid}")
            self.assertIsNotNone(mouth_img, f"Missing mouth_neutral_2x for {cid}")

            head_arr = np.array(head_img, dtype=np.int16)

            with_eyes = head_img.copy()
            with_eyes.alpha_composite(eyes_img)
            with_eyes_arr = np.array(with_eyes, dtype=np.int16)

            eye_diff_pixels = int((np.abs(with_eyes_arr[:, :, :3] - head_arr[:, :, :3]).max(axis=2) > 18).sum())
            self.assertGreater(
                eye_diff_pixels,
                25,
                f"Character '{cid}' head_2x still has open eyes baked in (only {eye_diff_pixels} pixels changed when overlaying eyes_open_2x)!",
            )

            with_mouth = head_img.copy()
            with_mouth.alpha_composite(mouth_img)
            with_mouth_arr = np.array(with_mouth, dtype=np.int16)

            mouth_diff_pixels = int((np.abs(with_mouth_arr[:, :, :3] - head_arr[:, :, :3]).max(axis=2) > 15).sum())
            self.assertGreater(
                mouth_diff_pixels,
                15,
                f"Character '{cid}' head_2x still has neutral mouth baked in (only {mouth_diff_pixels} pixels changed when overlaying mouth_neutral_2x)!",
            )

    def test_torso_deocclusion_under_articulated_arms(self):
        """
        Compositing `torso_2x` + `arm_rest_2x` must differ substantially from `torso_2x` alone
        in the lower arm zone (y: 145..224), proving hands/forearms are not baked identically into `torso_2x`.
        """
        for cid in ("julian", "tiffany", "malphas", "uriel", "mortimer", "selene", "vladimir", "dummy"):
            self.actor.equip_costume(cid)
            torso_img = self.actor.get_layer_image("torso", force_2x=True)
            arm_img = self.actor.get_layer_image("arm_rest", force_2x=True)

            torso_arr = np.array(torso_img, dtype=np.int16)
            combined = torso_img.copy()
            combined.alpha_composite(arm_img)
            comb_arr = np.array(combined, dtype=np.int16)

            arm_zone_diff = int((np.abs(comb_arr[140:224, :, :4] - torso_arr[140:224, :, :4]).max(axis=2) > 20).sum())
            self.assertGreater(
                arm_zone_diff,
                150,
                f"Character '{cid}' torso_2x still has resting arms/hands baked in (only {arm_zone_diff} pixels changed when overlaying arm_rest_2x)!",
            )

    def test_selene_and_vladimir_graphic_novel_art_richness(self):
        """
        Selene and Vladimir must feature richly shaded graphic-novel artwork (> 500 unique RGB colors
        in bust_2x.png) rather than flat geometric polygon placeholders.
        """
        for cid in ("selene", "vladimir"):
            bust_img = self.actor.get_bust_image(cid, scale_factor=2.0)
            self.assertIsNotNone(bust_img)
            arr = np.array(bust_img)
            opaque_rgb = arr[arr[:, :, 3] > 128][:, :3]
            unique_colors = len(np.unique(opaque_rgb, axis=0))
            self.assertGreater(
                unique_colors,
                500,
                f"Character '{cid}' has only {unique_colors} unique RGB colors (expected > 500 for cel-shaded graphic novel illustration)!",
            )

    def test_multi_layer_kinematics_and_gaze_tracking(self):
        """
        DealerActor supports independent sub-layer offsets (`torso_offset`, `head_offset`,
        `arm_offset`, `eye_gaze_offset`) that dynamically shift individual puppet strata.
        """
        self.actor.equip_costume("julian")
        base_comp = np.array(self.actor.get_composite_image(force_2x=True))

        # 1. Eye gaze shift changes eye region without moving torso
        self.actor.set_gaze_target(dx=2, dy=1)
        self.assertEqual(self.actor.eye_gaze_offset, (2, 1))
        gaze_comp = np.array(self.actor.get_composite_image(force_2x=True))
        self.assertFalse(np.array_equal(base_comp, gaze_comp), "Eye gaze offset should alter composite")
        # Lower torso (y: 130..160) should be unchanged when only eye_gaze_offset moves
        self.assertTrue(
            np.array_equal(base_comp[130:160, 80:140], gaze_comp[130:160, 80:140]),
            "Eye gaze offset must only move eyes, not torso",
        )

        # 2. Head offset moves head/eyes/mouth relative to torso
        self.actor.reset_kinematics()
        self.actor.set_layer_offsets(head_offset=(0, 3))
        head_comp = np.array(self.actor.get_composite_image(force_2x=True))
        self.assertFalse(np.array_equal(base_comp[20:85, :], head_comp[20:85, :]))

        # 3. Arm offset shifts arms during dealing reach
        self.actor.reset_kinematics()
        self.actor.set_layer_offsets(arm_offset=(2, 3))
        arm_comp = np.array(self.actor.get_composite_image(force_2x=True))
        self.assertFalse(np.array_equal(base_comp[165:224, :], arm_comp[165:224, :]))

    def test_universal_phonetic_viseme_mapping_without_legacy_branch(self):
        """All characters map speech characters directly to phonetic visemes without legacy coercion."""
        for cid in CHARACTERS:
            self.actor.equip_costume(cid)
            self.assertEqual(self.actor.set_mouth_for_char("o"), "o")
            self.assertEqual(self.actor.set_mouth_for_char("a"), "a")
            self.assertEqual(self.actor.set_mouth_for_char("e"), "e")
            self.assertEqual(self.actor.set_mouth_for_char("f"), "f")
            self.assertEqual(self.actor.set_mouth_for_char(" "), "neutral")


if __name__ == "__main__":
    unittest.main()
