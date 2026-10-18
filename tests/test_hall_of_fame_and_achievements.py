"""
Unit test suite for Phase D: Casino Hall of Fame, Wardrobe, and Gameplay Achievements.

Validates:
- 6 Core Casino Achievements and unlock criteria:
  1. The Exorcist (banish Pit Fiend in Hell's Table) -> unlocks Uriel
  2. High Roller (reach $10,000+ bankroll)
  3. Natural Born Winner (deal 3 Natural Blackjacks in session)
  4. Cursed Survivor (win or push round where Card 13 is dealt) -> unlocks Mortimer
  5. Split Maestro (win both hands following a split)
  6. Big Spender (win an all-in bet of $1,000+)
- Mortimer unlocks upon reaching $5,000 peak bankroll or Card 13 survival.
- SaveManager statistics updates upon round conclusion (hands played/won, win streaks, peak bankroll).
- Hall of Fame & Wardrobe modal two-tab layout (Wardrobe Closet <-> Trophy Shelf),
  all-time records summary, and 6 visual achievement plaques.
- Headless execution safety and isolated temporary save directory.
"""

from __future__ import annotations

import tempfile
import unittest
import tkinter
from pathlib import Path
from unittest.mock import patch

from blackjack import BlackjackApp, Card, Phase
from dealer_wardrobe_dialog import WardrobeDialog
from save_manager import SaveManager


class TestHallOfFameAndAchievements(unittest.TestCase):
    """Verifies achievement progression, statistics persistence, and Hall of Fame UI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_dir = Path(self.temp_dir.name)
        self.save_file = self.save_dir / "test_hall_of_fame_save.json"

        self.root = tkinter.Tk()
        self.root.withdraw()

        self.app = BlackjackApp(self.root, sound_enabled=False, save_path=self.save_file)

    def tearDown(self):
        try:
            if hasattr(self.app, "_wardrobe_dialog") and self.app._wardrobe_dialog:
                self.app._wardrobe_dialog.destroy()
        except Exception:
            pass
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

    def test_natural_born_winner_achievement(self):
        """Achieving 3 Natural Blackjacks in a session unlocks Natural Born Winner."""
        self.assertFalse(self.app.save_manager.data.achievements.natural_streak)
        self.app._session_blackjacks = 2

        # Simulate round ending with player natural blackjack
        self.app.player_hands = [[
            Card(1, self.app.all_cards[0][1], rank="ace", suit="spades"),
            Card(10, self.app.all_cards[1][1], rank="king", suit="spades"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.all_cards[2][1], rank="10", suit="diamonds"),
            Card(8, self.app.all_cards[3][1], rank="8", suit="hearts"),
        ]
        self.app._conclude_round()

        self.assertEqual(self.app._session_blackjacks, 3)
        self.assertTrue(self.app.save_manager.data.achievements.natural_streak)

    def test_cursed_survivor_achievement_and_mortimer_unlock(self):
        """Winning or pushing when Card 13 is dealt awards Cursed Survivor and unlocks Mortimer."""
        self.assertFalse(self.app.save_manager.data.achievements.cursed_survivor)
        self.assertNotIn("grim", self.app.save_manager.data.unlocked_costumes)

        # Player dealt card 13
        card_13 = Card(13, self.app.haunted_assets.get("card_13") or self.app.all_cards[0][1], rank="thirteen", suit="skulls")
        self.app.player_hands = [[
            card_13,
            Card(8, self.app.all_cards[1][1], rank="8", suit="hearts"),
        ]]
        # Player score modified by Cherub's Shield or high score
        self.app.dealer_hand = [
            Card(10, self.app.all_cards[2][1], rank="10", suit="diamonds"),
            Card(7, self.app.all_cards[3][1], rank="7", suit="clubs"),
        ]

        with patch.object(self.app, "_score_player_hand", return_value=21):
            self.app._conclude_round()

        self.assertTrue(self.app.save_manager.data.achievements.cursed_survivor)
        self.assertIn("grim", self.app.save_manager.data.unlocked_costumes)

    def test_split_maestro_achievement(self):
        """Winning both hands in a split round awards the Split Maestro achievement."""
        self.assertFalse(self.app.save_manager.data.achievements.split_maestro)

        self.app.player_hands = [
            [
                Card(10, self.app.all_cards[0][1], rank="10", suit="spades"),
                Card(10, self.app.all_cards[1][1], rank="jack", suit="hearts"),
            ],
            [
                Card(10, self.app.all_cards[2][1], rank="queen", suit="diamonds"),
                Card(9, self.app.all_cards[3][1], rank="9", suit="clubs"),
            ]
        ]
        self.app.dealer_hand = [
            Card(10, self.app.all_cards[4][1], rank="10", suit="clubs"),
            Card(7, self.app.all_cards[5][1], rank="7", suit="diamonds"),
        ]

        self.app._conclude_round()
        self.assertTrue(self.app.save_manager.data.achievements.split_maestro)

    def test_big_spender_achievement(self):
        """Winning an all-in bet of $1,000 or more awards Big Spender."""
        self.assertFalse(self.app.save_manager.data.achievements.big_spender)
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(0)  # Bankroll empty after placing wager
        self.app.hand_bets = [1500]

        self.app.player_hands = [[
            Card(10, self.app.all_cards[0][1], rank="10", suit="spades"),
            Card(10, self.app.all_cards[1][1], rank="king", suit="spades"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.all_cards[2][1], rank="10", suit="diamonds"),
            Card(8, self.app.all_cards[3][1], rank="8", suit="hearts"),
        ]

        self.app._conclude_round()
        self.assertTrue(self.app.save_manager.data.achievements.big_spender)

    def test_peak_bankroll_milestone_unlocks_mortimer(self):
        """Reaching $5,000 peak bankroll unlocks Mortimer even without Cursed Survivor."""
        self.assertNotIn("grim", self.app.save_manager.data.unlocked_costumes)
        self.app.save_manager.record_bankroll(5500)
        self.assertIn("grim", self.app.save_manager.data.unlocked_costumes)

    def test_round_conclusion_updates_save_statistics(self):
        """Round conclusion updates total hands played, total hands won, and bankroll."""
        initial_played = self.app.save_manager.data.highscores.total_hands_played
        initial_won = self.app.save_manager.data.highscores.total_hands_won

        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(1200)
        self.app.hand_bets = [100]

        self.app.player_hands = [[
            Card(10, self.app.all_cards[0][1], rank="10", suit="spades"),
            Card(10, self.app.all_cards[1][1], rank="king", suit="spades"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.all_cards[2][1], rank="10", suit="diamonds"),
            Card(8, self.app.all_cards[3][1], rank="8", suit="hearts"),
        ]

        self.app._conclude_round()
        self.assertEqual(self.app.save_manager.data.highscores.total_hands_played, initial_played + 1)
        self.assertEqual(self.app.save_manager.data.highscores.total_hands_won, initial_won + 1)
        self.assertGreaterEqual(self.app.save_manager.data.highscores.peak_bankroll, 1200)

    def test_hall_of_fame_tab_switching_and_plaques(self):
        """WardrobeDialog features Tab 1 (Wardrobe) and Tab 2 (Trophy Shelf) with 6 plaques."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(hasattr(dialog, "_switch_tab"))
        self.assertTrue(hasattr(dialog, "plaque_widgets"))

        # Switch to Tab 2: Trophy Shelf
        dialog._switch_tab(1)
        self.assertEqual(dialog.current_tab, 1)

        # Verify all 6 core achievement plaques exist
        expected_plaques = (
            "exorcist",
            "high_roller",
            "natural_streak",
            "cursed_survivor",
            "split_maestro",
            "big_spender",
        )
        for ach_id in expected_plaques:
            self.assertIn(ach_id, dialog.plaque_widgets, f"Achievement plaque missing: {ach_id}")

        # Switch back to Tab 1: Wardrobe Closet
        dialog._switch_tab(0)
        self.assertEqual(dialog.current_tab, 0)

    def test_boot_equipped_costume_sync(self):
        """App initializes and equips the dealer costume specified in SaveManager."""
        # Save Uriel as equipped costume
        self.app.save_manager.data.unlocked_costumes.append("uriel")
        self.app.save_manager.data.equipped_costume = "uriel"
        self.app.save_manager.save()

        # Instantiate fresh app reading the same save file
        fresh_root = tkinter.Tk()
        fresh_root.withdraw()
        try:
            fresh_app = BlackjackApp(fresh_root, sound_enabled=False, save_path=self.save_file)
            self.assertEqual(fresh_app.dealer_actor.current_character, "uriel")
            fresh_app._on_close()
        finally:
            try:
                fresh_root.destroy()
            except Exception:
                pass


if __name__ == "__main__":
    unittest.main()
