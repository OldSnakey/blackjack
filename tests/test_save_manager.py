"""
Unit test suite for SaveManager and blackjack_save.json persistence.

Validates:
- Blank slate default state.
- Save file generation and loading.
- High score and streak tracking.
- Achievement unlocks and dependent costume rewards.
- Clear save file resetting everything back to blank slate.
- Graceful recovery from corrupt save files.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from save_manager import SaveData, SaveManager


class TestSaveManager(unittest.TestCase):
    """Verifies persistence, achievement tracking, and clear save functionality."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.save_file = self.test_dir / "test_blackjack_save.json"
        self.manager = SaveManager(save_path=self.save_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_default_blank_slate(self):
        """Initial save data has default values and creates save file."""
        self.assertTrue(self.save_file.exists())
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 1000)
        self.assertEqual(self.manager.data.highscores.total_hands_played, 0)
        self.assertEqual(self.manager.data.equipped_costume, "classic")
        self.assertEqual(self.manager.data.unlocked_costumes, ["classic", "tiffany"])
        self.assertFalse(self.manager.data.achievements.exorcist)
        self.assertFalse(self.manager.data.achievements.high_roller)

    def test_record_bankroll_and_high_roller(self):
        """Bankroll record updates peak and awards high roller achievement at $10,000."""
        self.manager.record_bankroll(5000)
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 5000)
        self.assertFalse(self.manager.data.achievements.high_roller)

        self.manager.record_bankroll(10500)
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 10500)
        self.assertTrue(self.manager.data.achievements.high_roller)

        # Check file contents on disk
        with open(self.save_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertEqual(disk_data["highscores"]["peak_bankroll"], 10500)
        self.assertTrue(disk_data["achievements"]["high_roller"])

    def test_record_hands_and_streaks(self):
        """Hand wins and blackjacks update statistics correctly."""
        self.manager.record_hand_played(won=True, is_blackjack=True)
        self.manager.record_hand_played(won=False)
        self.manager.record_win_streak(5)

        self.assertEqual(self.manager.data.highscores.total_hands_played, 2)
        self.assertEqual(self.manager.data.highscores.total_hands_won, 1)
        self.assertEqual(self.manager.data.highscores.total_blackjacks, 1)
        self.assertEqual(self.manager.data.highscores.longest_win_streak, 5)

    def test_unlock_exorcist_unlocks_seraph_costume(self):
        """Unlocking Exorcist achievement also awards the celestial Seraph costume."""
        newly_unlocked = self.manager.unlock_achievement("exorcist")
        self.assertTrue(newly_unlocked)
        self.assertTrue(self.manager.data.achievements.exorcist)
        self.assertIn("seraph", self.manager.data.unlocked_costumes)
        self.assertEqual(self.manager.data.highscores.hell_table_clears, 1)

        # Unlocking again returns False
        self.assertFalse(self.manager.unlock_achievement("exorcist"))

    def test_clear_save_resets_to_blank_slate(self):
        """clear_save resets in-memory data and overwrites file with blank slate."""
        self.manager.record_bankroll(25000)
        self.manager.unlock_achievement("exorcist")
        self.manager.record_win_streak(10)
        self.assertTrue(self.manager.data.achievements.exorcist)
        self.assertIn("seraph", self.manager.data.unlocked_costumes)

        # Execute clear save
        success = self.manager.clear_save()
        self.assertTrue(success)

        # State must now be back to default
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 1000)
        self.assertEqual(self.manager.data.highscores.longest_win_streak, 0)
        self.assertEqual(self.manager.data.unlocked_costumes, ["classic", "tiffany"])
        self.assertFalse(self.manager.data.achievements.exorcist)
        self.assertFalse(self.manager.data.achievements.high_roller)

        # Reload from disk into fresh manager instance to ensure persistence was overwritten
        fresh_mgr = SaveManager(save_path=self.save_file)
        self.assertEqual(fresh_mgr.data.highscores.peak_bankroll, 1000)
        self.assertFalse(fresh_mgr.data.achievements.exorcist)

    def test_corrupt_file_recovery(self):
        """Corrupted JSON file resets gracefully to blank slate on load."""
        with open(self.save_file, "w", encoding="utf-8") as f:
            f.write("{broken json!@#$")

        recovered_mgr = SaveManager(save_path=self.save_file)
        self.assertEqual(recovered_mgr.data.highscores.peak_bankroll, 1000)
        self.assertEqual(recovered_mgr.data.unlocked_costumes, ["classic", "tiffany"])


if __name__ == "__main__":
    unittest.main()
