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
        self.assertTrue(self.manager.data.chips_mode)

    def test_set_chips_mode(self):
        """set_chips_mode persists the user's preference to disk."""
        self.manager.set_chips_mode(False)
        self.assertFalse(self.manager.data.chips_mode)

        # Check disk
        with open(self.save_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertFalse(disk_data["chips_mode"])

        # Reload in fresh instance
        reloaded = SaveManager(save_path=self.save_file)
        self.assertFalse(reloaded.data.chips_mode)

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
        self.manager.set_chips_mode(False)
        self.assertTrue(self.manager.data.achievements.exorcist)
        self.assertIn("seraph", self.manager.data.unlocked_costumes)
        self.assertFalse(self.manager.data.chips_mode)

        # Execute clear save
        success = self.manager.clear_save()
        self.assertTrue(success)

        # State must now be back to default
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 1000)
        self.assertEqual(self.manager.data.highscores.longest_win_streak, 0)
        self.assertEqual(self.manager.data.unlocked_costumes, ["classic", "tiffany"])
        self.assertFalse(self.manager.data.achievements.exorcist)
        self.assertFalse(self.manager.data.achievements.high_roller)
        self.assertTrue(self.manager.data.chips_mode)

        # Reload from disk into fresh manager instance to ensure persistence was overwritten
        fresh_mgr = SaveManager(save_path=self.save_file)
        self.assertEqual(fresh_mgr.data.highscores.peak_bankroll, 1000)
        self.assertFalse(fresh_mgr.data.achievements.exorcist)
        self.assertTrue(fresh_mgr.data.chips_mode)

    def test_corrupt_file_recovery(self):
        """Corrupted JSON file resets gracefully to blank slate on load."""
        with open(self.save_file, "w", encoding="utf-8") as f:
            f.write("{broken json!@#$")

        recovered_mgr = SaveManager(save_path=self.save_file)
        self.assertEqual(recovered_mgr.data.highscores.peak_bankroll, 1000)
        self.assertEqual(recovered_mgr.data.unlocked_costumes, ["classic", "tiffany"])
    def test_play_mode_and_onboarding_persistence(self):
        """Play mode (casual, betting, training) and onboarding completion status persist across sessions."""
        self.assertEqual(self.manager.data.play_mode, "betting")
        self.assertFalse(self.manager.data.onboarding_completed)

        # Update play mode to training
        self.manager.set_play_mode("training")
        self.manager.complete_onboarding()
        self.assertEqual(self.manager.data.play_mode, "training")
        self.assertTrue(self.manager.data.onboarding_completed)
        self.assertTrue(self.manager.data.chips_mode)

        # Reload from disk
        fresh_mgr = SaveManager(save_path=self.save_file)
        self.assertEqual(fresh_mgr.data.play_mode, "training")
        self.assertTrue(fresh_mgr.data.onboarding_completed)

        # Switch to casual -> chips_mode should sync to False
        fresh_mgr.set_play_mode("casual")
        self.assertEqual(fresh_mgr.data.play_mode, "casual")
        self.assertFalse(fresh_mgr.data.chips_mode)

        # Clear save resets onboarding_completed to False
        fresh_mgr.clear_save()
        self.assertFalse(fresh_mgr.data.onboarding_completed)
        self.assertEqual(fresh_mgr.data.play_mode, "betting")

    def test_default_bankroll_and_financial_telemetry(self):
        """Default SaveData provides persistent current_bankroll and zeroed financial telemetry."""
        from save_manager import DEFAULT_STARTING_BANKROLL
        self.assertEqual(DEFAULT_STARTING_BANKROLL, 1000)
        self.assertEqual(self.manager.data.current_bankroll, 1000)
        self.assertEqual(self.manager.data.highscores.bankruptcies, 0)
        self.assertEqual(self.manager.data.highscores.total_bailout_funds, 0)
        self.assertEqual(self.manager.data.highscores.lifetime_wagered, 0)
        self.assertEqual(self.manager.get_net_profit_loss(), 0)

    def test_record_round_financials(self):
        """record_round_financials updates current bankroll, peak bankroll, and lifetime wagered."""
        # Initial bankroll 1000. Player bets $100 and ends round with $1200.
        self.manager.record_round_financials(current_bankroll=1200, total_wagered=100, save_now=True)
        self.assertEqual(self.manager.data.current_bankroll, 1200)
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 1200)
        self.assertEqual(self.manager.data.highscores.lifetime_wagered, 100)
        self.assertEqual(self.manager.get_net_profit_loss(), 200)

        # Player places another $200 bet and drops to $800. Peak bankroll remains 1200. save_now=False
        self.manager.record_round_financials(current_bankroll=800, total_wagered=200, save_now=False)
        self.assertEqual(self.manager.data.current_bankroll, 800)
        self.assertEqual(self.manager.data.highscores.peak_bankroll, 1200)
        self.assertEqual(self.manager.data.highscores.lifetime_wagered, 300)
        self.assertEqual(self.manager.get_net_profit_loss(), -200)

        # Confirm reload from disk reflects the save
        self.manager.save()
        reloaded = SaveManager(save_path=self.save_file)
        self.assertEqual(reloaded.data.current_bankroll, 800)
        self.assertEqual(reloaded.data.highscores.lifetime_wagered, 300)

    def test_record_rebuy(self):
        """record_rebuy reloads bankroll, increments bankruptcies, and tracks cumulative bailout dollars."""
        self.manager.record_round_financials(current_bankroll=0, total_wagered=1000, save_now=True)
        self.assertEqual(self.manager.get_net_profit_loss(), -1000)

        # Execute rebuy
        self.manager.record_rebuy(amount=1000)
        self.assertEqual(self.manager.data.current_bankroll, 1000)
        self.assertEqual(self.manager.data.highscores.bankruptcies, 1)
        self.assertEqual(self.manager.data.highscores.total_bailout_funds, 1000)
        # Net P/L should now be: 1000 - (1000 + 1000) = -1000
        self.assertEqual(self.manager.get_net_profit_loss(), -1000)

        # Reload from disk
        reloaded = SaveManager(save_path=self.save_file)
        self.assertEqual(reloaded.data.current_bankroll, 1000)
        self.assertEqual(reloaded.data.highscores.bankruptcies, 1)
        self.assertEqual(reloaded.data.highscores.total_bailout_funds, 1000)

        # Second rebuy
        reloaded.record_rebuy(amount=1000)
        self.assertEqual(reloaded.data.highscores.bankruptcies, 2)
        self.assertEqual(reloaded.data.highscores.total_bailout_funds, 2000)
        # Net P/L: 1000 - (1000 + 2000) = -2000
        self.assertEqual(reloaded.get_net_profit_loss(), -2000)

    def test_get_net_profit_loss_scenarios(self):
        """get_net_profit_loss computes exact closed-form lifetime profit or loss."""
        # 1. Winning without bailouts: bankroll $3500 -> profit +$2500
        self.manager.data.current_bankroll = 3500
        self.manager.data.highscores.total_bailout_funds = 0
        self.assertEqual(self.manager.get_net_profit_loss(), 2500)

        # 2. Rebuilt to profit after 1 rebuy: bankroll $2500, bailout $1000 -> profit +$500
        self.manager.data.current_bankroll = 2500
        self.manager.data.highscores.total_bailout_funds = 1000
        self.assertEqual(self.manager.get_net_profit_loss(), 500)

        # 3. In the hole after multiple bailouts: bankroll $500, bailout $3000 -> -$3500
        self.manager.data.current_bankroll = 500
        self.manager.data.highscores.total_bailout_funds = 3000
        self.assertEqual(self.manager.get_net_profit_loss(), -3500)

    def test_legacy_version_1_0_migration(self):
        """Loading a legacy JSON save file without bankroll or telemetry initializes defaults safely."""
        legacy_data = {
            "version": "1.0",
            "equipped_costume": "classic",
            "unlocked_costumes": ["classic", "tiffany"],
            "highscores": {
                "peak_bankroll": 4500,
                "longest_win_streak": 3,
                "total_hands_played": 15,
                "total_hands_won": 9,
            },
            "achievements": {
                "high_roller": False,
            },
            "chips_mode": True,
            "play_mode": "betting",
            "onboarding_completed": True,
        }
        with open(self.save_file, "w", encoding="utf-8") as f:
            json.dump(legacy_data, f)

        loaded_mgr = SaveManager(save_path=self.save_file)
        self.assertEqual(loaded_mgr.data.version, "1.1")
        self.assertEqual(loaded_mgr.data.current_bankroll, 1000)
        self.assertEqual(loaded_mgr.data.highscores.peak_bankroll, 4500)
        self.assertEqual(loaded_mgr.data.highscores.bankruptcies, 0)
        self.assertEqual(loaded_mgr.data.highscores.total_bailout_funds, 0)
        self.assertEqual(loaded_mgr.data.highscores.lifetime_wagered, 0)
        self.assertEqual(loaded_mgr.get_net_profit_loss(), 0)


if __name__ == "__main__":
    unittest.main()

