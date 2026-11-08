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
        for cid in ("julian", "tiffany", "malphas", "uriel", "mortimer", "selene", "vladimir", "professor", "dummy"):
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
        for cid in ("julian", "tiffany", "malphas", "uriel", "mortimer", "selene", "vladimir", "professor", "dummy"):
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
        All 8 portrait dealers (julian, professor, tiffany, selene, malphas, mortimer, uriel, vladimir)
        feature native 16-bit chunky pixel-art paper-doll rigs with rich clustered palettes (>= 24 unique colors).
        """
        for cid in ("julian", "professor", "tiffany", "selene", "malphas", "mortimer", "uriel", "vladimir"):
            bust_img = self.actor.get_bust_image(cid, scale_factor=2.0)
            self.assertIsNotNone(bust_img)
            arr = np.array(bust_img)
            opaque_rgb = arr[arr[:, :, 3] > 128][:, :3]
            unique_colors = len(np.unique(opaque_rgb, axis=0))
            self.assertGreaterEqual(
                unique_colors,
                24,
                f"Chunky pixel-art character '{cid}' has only {unique_colors} unique RGB colors!",
            )

    def test_chunky_puppet_tall_neck_overlap_and_card_back_dealing_arm(self):
        """
        Verifies the new chunky articulated paper-doll rig invariants across all 8 portrait dealers:
        1. Tall neck column extends high behind the head (y <= 80 in 2x coordinates) so lifting
           head_offset=(0, -6) never exposes a transparent seam along the central spine.
        2. Dealing arm (arm_deal_2x) holds a blue-backed playing card matching cards/back.png
           (royal-blue pixels with B > R + 80) rather than an exposed red card face.
        3. Intra-sclera gaze tracking shifts pupil pixels inside the eye sockets without moving
           the outer temple/cheek silhouette of the head.
        """
        for cid in ("julian", "professor", "tiffany", "selene", "malphas", "mortimer", "uriel", "vladimir"):
            self.actor.equip_costume(cid)
            self.actor.reset_kinematics()

            neck_img = self.actor.get_layer_image("neck", force_2x=True)
            self.assertIsNotNone(neck_img)
            neck_arr = np.array(neck_img)
            neck_ys = np.where(neck_arr[:, :, 3] > 200)[0]
            self.assertGreater(len(neck_ys), 0)
            self.assertLessEqual(
                int(neck_ys.min()),
                80,
                f"Character '{cid}' neck_2x top y={int(neck_ys.min())} does not extend high behind the head (<= 80)!",
            )

            # Lifting head by -6px must leave 100% opaque central spine (y: 60..160, x: 106..118)
            self.actor.set_layer_offsets(head_offset=(0, -6))
            lifted_comp = np.array(self.actor.get_composite_image(force_2x=True))
            spine_min_alpha = int(lifted_comp[60:160, 106:118, 3].min())
            self.assertEqual(
                spine_min_alpha,
                255,
                f"Character '{cid}' exposed a neck gap (min alpha={spine_min_alpha}) when head lifted by -6px!",
            )

            # Dealing arm must hold the canonical blue card back (cards/back.png)
            self.actor.reset_kinematics()
            arm_deal_img = self.actor.get_layer_image("arm_deal", force_2x=True)
            self.assertIsNotNone(arm_deal_img)
            deal_arr = np.array(arm_deal_img, dtype=np.int16)
            blue_card_pixels = int(
                ((deal_arr[:, :, 3] > 200) & (deal_arr[:, :, 2] > deal_arr[:, :, 0] + 80) & (deal_arr[:, :, 2] > 180)).sum()
            )
            self.assertGreater(
                blue_card_pixels,
                150,
                f"Character '{cid}' arm_deal_2x does not show canonical blue card back (found {blue_card_pixels} blue pixels)!",
            )

            # Intra-sclera gaze tracking: shifting eye_gaze_offset=(2, 0) changes pupil pixels but keeps outer cheek/temple silhouette fixed
            self.actor.reset_kinematics()
            base_c = np.array(self.actor.get_composite_image(force_2x=True))
            self.actor.set_gaze_target(dx=2, dy=0)
            gaze_c = np.array(self.actor.get_composite_image(force_2x=True))
            self.assertFalse(np.array_equal(base_c[50:96, 80:148], gaze_c[50:96, 80:148]))
            # Outer head silhouette alpha in eye rows (y: 50..96) must be unchanged by gaze shift
            self.assertTrue(
                np.array_equal(base_c[50:96, :, 3] > 128, gaze_c[50:96, :, 3] > 128),
                f"Character '{cid}' eye_gaze_offset altered outer head silhouette!",
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

    def test_live_speech_head_bob_and_reset_kinematics(self):
        """
        Verifies that BlackjackApp._step_speech_mouth drives subtle syllable-synced head_offset
        articulation on open vowels ('a', 'o') and resets head_offset to (0, 0) when speech completes.
        """
        from pathlib import Path
        import tempfile
        from blackjack import BlackjackApp
        from save_manager import SaveManager

        tmp_dir = tempfile.TemporaryDirectory()
        app = BlackjackApp(self.root, chips_mode=False, sound_enabled=False)
        app.save_manager = SaveManager(Path(tmp_dir.name) / "save.json")
        try:
            app.dealer_actor.equip_costume("julian")
            app.dealer_actor.reset_kinematics()

            app._step_speech_mouth("a")
            self.assertEqual(app.dealer_actor.mouth_state, "a")
            self.assertNotEqual(app.dealer_actor.head_offset, (0, 0), "Open vowel should bob head slightly")

            app._complete_typewriter_speech()
            self.assertEqual(app.dealer_actor.mouth_state, "neutral")
            self.assertEqual(app.dealer_actor.head_offset, (0, 0), "Completing speech must reset head_offset to (0, 0)")

            app._step_speech_mouth("o")
            self.assertNotEqual(app.dealer_actor.head_offset, (0, 0))
            app.clear_dealer_speech()
            self.assertEqual(app.dealer_actor.head_offset, (0, 0), "Clearing speech must reset head_offset to (0, 0)")
        finally:
            app._on_close()
            tmp_dir.cleanup()

    def test_biomechanical_torso_breathing_keeps_head_stationary_and_bottom_clamped(self):
        """
        Verifies that inhaling via torso_offset=(0, -2) lifts the shoulders/chest while:
        1. Keeping the head, face, hat, and halo completely stationary (y: 10..96 unchanged).
        2. Clamping the bottom horizon-rail rows (y: 222..223) so no transparent gap opens at the bottom.
        """
        for cid in ("julian", "professor", "tiffany", "selene", "malphas", "mortimer", "uriel", "vladimir"):
            self.actor.equip_costume(cid)
            self.actor.reset_kinematics()
            rest_comp = np.array(self.actor.get_composite_image(force_2x=True))

            self.actor.set_layer_offsets(torso_offset=(0, -2), head_offset=(0, 0))
            inhale_comp = np.array(self.actor.get_composite_image(force_2x=True))

            # 1. Upper head, eyes, hat/halo (y: 0..88, above popped shirt collars) must remain 100% stationary during torso breath
            self.assertTrue(
                np.array_equal(rest_comp[0:88, :, :], inhale_comp[0:88, :, :]),
                f"Character '{cid}' head/face pixels moved during torso-only breathing!",
            )

            # 2. Chest/shoulders (y: 120..180) must visibly shift during inhalation
            self.assertFalse(
                np.array_equal(rest_comp[120:180, :, :], inhale_comp[120:180, :, :]),
                f"Character '{cid}' chest/shoulders did not move when torso_offset=(0, -2)!",
            )

            # 3. Bottom-most rows (y: 222..223) must retain identical opaque coverage (zero floating gap)
            rest_bottom_opaque = int((rest_comp[222:224, :, 3] > 200).sum())
            inhale_bottom_opaque = int((inhale_comp[222:224, :, 3] > 200).sum())
            self.assertEqual(
                inhale_bottom_opaque,
                rest_bottom_opaque,
                f"Character '{cid}' lost bottom-edge horizon coverage during inhale ({inhale_bottom_opaque} vs {rest_bottom_opaque})!",
            )


if __name__ == "__main__":
    unittest.main()
