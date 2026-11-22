"""
Unit tests verifying all 14 Hall of Fame achievement trophy sprites and their
per-achievement locked '?' silhouettes exist, load cleanly, match 1x (64x64)
and 2x (128x128) crunchy pixel-art invariants, and have distinct unlocked vs
locked visual signatures.
"""

from __future__ import annotations

import unittest
from PIL import Image

import config

ACHIEVEMENT_IDS = (
    "exorcist",
    "high_roller",
    "natural_streak",
    "cursed_survivor",
    "split_maestro",
    "big_spender",
    "apprentice_counter",
    "master_counter",
    "shoe_whisperer",
    "count_capitalist",
    "pair_perfectionist",
    "poker_face",
    "tour_champion",
    "ironman_legend",
)


class TestAchievementTrophyAssets(unittest.TestCase):
    """Validates existence, dimensions, transparency headroom, and silhouette integrity of all 14 trophies."""

    def test_achievements_assets_dir_configured_and_exists(self):
        self.assertTrue(hasattr(config, "ACHIEVEMENTS_ASSETS_DIR"))
        self.assertTrue(config.ACHIEVEMENTS_ASSETS_DIR.exists())
        self.assertTrue(config.ACHIEVEMENTS_ASSETS_DIR.is_dir())

    def test_all_14_unlocked_and_locked_sprites_exist_at_1x_and_2x(self):
        base = config.ACHIEVEMENTS_ASSETS_DIR
        for ach_id in ACHIEVEMENT_IDS:
            for fname, expected_wh in (
                (f"{ach_id}.png", (64, 64)),
                (f"{ach_id}_2x.png", (128, 128)),
                (f"locked_{ach_id}.png", (64, 64)),
                (f"locked_{ach_id}_2x.png", (128, 128)),
            ):
                p = base / fname
                self.assertTrue(p.exists(), f"Missing achievement sprite: {p}")
                with Image.open(p) as im:
                    self.assertEqual(im.mode, "RGBA", f"{fname} must be RGBA")
                    self.assertEqual(im.size, expected_wh, f"{fname} expected {expected_wh}, got {im.size}")
                    alpha = im.getchannel("A")
                    bbox = alpha.getbbox()
                    self.assertIsNotNone(bbox, f"{fname} is completely transparent")
                    # Ensure >= 2px transparent margin on all 4 sides at 1x (4px at 2x)
                    margin = 2 if expected_wh[0] == 64 else 4
                    self.assertGreaterEqual(bbox[0], margin, f"{fname} clips left edge: {bbox}")
                    self.assertGreaterEqual(bbox[1], margin, f"{fname} clips top edge: {bbox}")
                    self.assertLessEqual(bbox[2], expected_wh[0] - margin, f"{fname} clips right edge: {bbox}")
                    self.assertLessEqual(bbox[3], expected_wh[1] - margin, f"{fname} clips bottom edge: {bbox}")

    def test_unlocked_and_locked_sprites_have_distinct_pixels_and_matching_silhouette_envelope(self):
        base = config.ACHIEVEMENTS_ASSETS_DIR
        for ach_id in ACHIEVEMENT_IDS:
            with Image.open(base / f"{ach_id}.png") as unlocked, Image.open(base / f"locked_{ach_id}.png") as locked:
                self.assertNotEqual(
                    unlocked.tobytes(),
                    locked.tobytes(),
                    f"Locked silhouette for {ach_id} must differ visually from unlocked trophy",
                )
                # Locked silhouette should preserve the exact non-empty silhouette footprint
                u_bbox = unlocked.getchannel("A").getbbox()
                l_bbox = locked.getchannel("A").getbbox()
                self.assertEqual(u_bbox, l_bbox, f"Locked silhouette bbox mismatch for {ach_id}")


if __name__ == "__main__":
    unittest.main()
