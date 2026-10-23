"""
Targeted Automated Test Suite for Hi-Lo Card Counting Engine.

Verifies:
- Standard Hi-Lo tag valuations:
  - Low cards (2-6) = +1
  - Neutral cards (7-9) = 0
  - High cards (10, J, Q, K, A) = -1
- Running Count (RC) updates and shoe reset handling.
- Decks Remaining calculation with half-deck precision clamp (minimum 0.5 decks).
- True Count (TC) calculation: TC = RC / Decks Remaining.
- Bet sizing recommendations based on positive True Count index.
- Dealer hole card observation invariant (only counts when explicitly revealed).
- Quiz verification for counter training drills.
"""

from __future__ import annotations

import unittest
from card_counter import HiLoCardCounter
from rules import Card


class TestCardCounter(unittest.TestCase):
    """Unit tests for HiLoCardCounter domain calculations."""

    def setUp(self):
        self.counter = HiLoCardCounter(deck_count=6)

    def test_card_tag_values(self):
        """Card tag values strictly follow standard casino Hi-Lo card counting rules."""
        # Low cards (+1)
        for val in (2, 3, 4, 5, 6):
            c = Card(value=val, image=None, rank=str(val), suit="heart")
            self.assertEqual(self.counter.get_card_tag(c), 1, f"Card {val} should be +1")

        # Neutral cards (0)
        for val in (7, 8, 9):
            c = Card(value=val, image=None, rank=str(val), suit="diamond")
            self.assertEqual(self.counter.get_card_tag(c), 0, f"Card {val} should be 0")

        # High cards (-1): 10, Face cards (Jack, Queen, King), and Ace
        for rank in ("10", "jack", "queen", "king"):
            c = Card(value=10, image=None, rank=rank, suit="spade")
            self.assertEqual(self.counter.get_card_tag(c), -1, f"Card {rank} should be -1")

        ace = Card(value=1, image=None, rank="ace", suit="club")
        self.assertEqual(self.counter.get_card_tag(ace), -1, "Ace should be -1")

    def test_running_count_accumulation(self):
        """Running count correctly accumulates observed cards and tracks counts."""
        self.assertEqual(self.counter.running_count, 0)

        # Observe low cards: +1, +1
        self.counter.observe_card(Card(2, None, "2", "heart"))
        self.counter.observe_card(Card(5, None, "5", "spade"))
        self.assertEqual(self.counter.running_count, 2)

        # Observe neutral card: +0
        self.counter.observe_card(Card(8, None, "8", "diamond"))
        self.assertEqual(self.counter.running_count, 2)

        # Observe high card: -1
        self.counter.observe_card(Card(10, None, "king", "club"))
        self.assertEqual(self.counter.running_count, 1)

        # Observe Ace: -1
        self.counter.observe_card(Card(1, None, "ace", "heart"))
        self.assertEqual(self.counter.running_count, 0)

    def test_shoe_reset(self):
        """Shoe reset clears running count back to zero."""
        self.counter.observe_card(Card(2, None, "2", "heart"))
        self.counter.observe_card(Card(3, None, "3", "heart"))
        self.assertEqual(self.counter.running_count, 2)

        self.counter.reset_shoe(deck_count=6)
        self.assertEqual(self.counter.running_count, 0)
        self.assertEqual(self.counter.observed_cards_count, 0)

    def test_decks_remaining_calculation(self):
        """Decks remaining is computed as cards_remaining / 52 with minimum clamp of 0.5."""
        # 6 full decks = 312 cards -> 6.0 decks
        self.assertAlmostEqual(self.counter.decks_remaining(312), 6.0, places=1)

        # 3 full decks = 156 cards -> 3.0 decks
        self.assertAlmostEqual(self.counter.decks_remaining(156), 3.0, places=1)

        # 1 deck = 52 cards -> 1.0 decks
        self.assertAlmostEqual(self.counter.decks_remaining(52), 1.0, places=1)

        # Very low shoe: 10 cards remaining -> clamped to 0.5 decks
        self.assertAlmostEqual(self.counter.decks_remaining(10), 0.5, places=1)

    def test_true_count_calculation(self):
        """True count is running count divided by decks remaining."""
        # RC = +6, 3 decks remaining -> TC = +2.0
        self.counter.running_count = 6
        self.assertAlmostEqual(self.counter.true_count(cards_remaining=156), 2.0, places=1)

        # RC = -4, 2 decks remaining -> TC = -2.0
        self.counter.running_count = -4
        self.assertAlmostEqual(self.counter.true_count(cards_remaining=104), -2.0, places=1)

        # RC = +5, 1 deck remaining -> TC = +5.0
        self.counter.running_count = 5
        self.assertAlmostEqual(self.counter.true_count(cards_remaining=52), 5.0, places=1)

    def test_bet_recommendation(self):
        """Recommends bet multiplier based on True Count."""
        base_unit = 25
        # TC <= 1: 1 unit ($25)
        self.assertEqual(self.counter.get_recommended_bet(base_unit, true_count=0.0), 25)
        self.assertEqual(self.counter.get_recommended_bet(base_unit, true_count=1.0), 25)

        # TC = +2: 2 units ($50)
        self.assertEqual(self.counter.get_recommended_bet(base_unit, true_count=2.0), 50)

        # TC = +3: 3 units ($75)
        self.assertEqual(self.counter.get_recommended_bet(base_unit, true_count=3.0), 75)

        # TC = +4: 4 units ($100)
        self.assertEqual(self.counter.get_recommended_bet(base_unit, true_count=4.0), 100)

        # TC >= +5: capped at max 5 units ($125)
        self.assertEqual(self.counter.get_recommended_bet(base_unit, true_count=6.0), 125)

    def test_quiz_verification(self):
        """Verifies player quiz answers for Running Count and True Count drills."""
        self.counter.running_count = 4
        # 2 decks = 104 cards -> TC = 2.0
        self.assertTrue(self.counter.verify_quiz_answer(submitted_rc=4, submitted_tc=2.0, cards_remaining=104))
        self.assertFalse(self.counter.verify_quiz_answer(submitted_rc=3, submitted_tc=2.0, cards_remaining=104))
        self.assertFalse(self.counter.verify_quiz_answer(submitted_rc=4, submitted_tc=1.0, cards_remaining=104))

    def test_player_advantage_percentage(self):
        """Player advantage is estimated as -0.5% + 0.5% * TC."""
        # TC = 0.0 -> -0.5%
        self.counter.running_count = 0
        self.assertAlmostEqual(self.counter.get_player_advantage(cards_remaining=104), -0.5, places=2)

        # TC = +1.0 -> 0.0%
        self.counter.running_count = 2
        self.assertAlmostEqual(self.counter.get_player_advantage(cards_remaining=104), 0.0, places=2)

        # TC = +3.0 -> +1.0%
        self.counter.running_count = 6
        self.assertAlmostEqual(self.counter.get_player_advantage(cards_remaining=104), 1.0, places=2)

        # TC = -2.0 -> -1.5%
        self.counter.running_count = -4
        self.assertAlmostEqual(self.counter.get_player_advantage(cards_remaining=104), -1.5, places=2)

    def test_hud_edge_display_and_drill_mode_masking(self):
        """CardCountingHud displays Edge % and masks RC/TC/Edge as '?' in Drill Challenge Mode."""
        import tkinter
        from card_counting_hud import CardCountingHud

        root = tkinter.Tk()
        root.withdraw()
        try:
            hud = CardCountingHud(master=root, counter=self.counter)
            self.counter.running_count = 6  # 104 cards (2 decks) -> TC = +3.0, Edge = +1.0%
            hud.update_counts(cards_remaining=104, base_bet=25)

            self.assertFalse(hud.drill_mode)
            self.assertEqual(hud.rc_label.cget("text"), "+6")
            self.assertEqual(hud.tc_label.cget("text"), "+3.0")
            self.assertEqual(hud.edge_label.cget("text"), "+1.0%")
            self.assertEqual(hud.edge_label.cget("fg"), "#4ade80")

            # Toggle into Drill Challenge Mode: live RC, TC, Edge are masked as '?'
            hud.toggle_drill_mode(cards_remaining=104, base_bet=25)
            self.assertTrue(hud.drill_mode)
            self.assertEqual(hud.rc_label.cget("text"), "?")
            self.assertEqual(hud.tc_label.cget("text"), "?")
            self.assertEqual(hud.edge_label.cget("text"), "?")

            # Toggle back to Assisted Mode: live values restored
            hud.toggle_drill_mode(cards_remaining=104, base_bet=25)
            self.assertFalse(hud.drill_mode)
            self.assertEqual(hud.rc_label.cget("text"), "+6")
            self.assertEqual(hud.tc_label.cget("text"), "+3.0")
            self.assertEqual(hud.edge_label.cget("text"), "+1.0%")
        finally:
            root.destroy()

    def test_extended_counting_telemetry_and_achievements(self):
        """SaveManager persists quiz accuracy telemetry and unlocks Shoe Whisperer & Count Capitalist."""
        import tempfile
        from pathlib import Path
        from save_manager import SaveManager

        with tempfile.TemporaryDirectory() as tmp:
            sm = SaveManager(save_path=Path(tmp) / "test_save.json")
            for _ in range(3):
                sm.record_counting_quiz(True)
            self.assertEqual(sm.data.highscores.counting_quizzes_taken, 3)
            self.assertEqual(sm.data.highscores.counting_quizzes_correct, 3)
            self.assertAlmostEqual(sm.data.highscores.counting_accuracy_pct, 100.0, places=1)

            # Completing a shoe with >=3 quizzes and 100% accuracy unlocks shoe_whisperer
            self.assertTrue(sm.evaluate_shoe_whisperer())
            self.assertTrue(sm.data.achievements.shoe_whisperer)

            # Winning a $1,000+ wager when TC >= +3.0 unlocks count_capitalist
            sm.evaluate_round_achievements(
                outcomes=["PLAYER_WINS"],
                player_hands=[[Card(10, None, "10", "spade"), Card(10, None, "king", "heart")]],
                dealer_hand=[Card(10, None, "10", "club"), Card(8, None, "8", "diamond")],
                current_streak=1,
                chips_mode=True,
                current_bankroll=2500,
                hand_bets=[1000],
                is_all_in=False,
                haunted_phase="normal",
                session_blackjacks=0,
                true_count=3.5,
            )
            self.assertTrue(sm.data.achievements.count_capitalist)


if __name__ == "__main__":
    unittest.main()
