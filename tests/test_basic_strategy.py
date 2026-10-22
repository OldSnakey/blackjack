"""
Unit test suite for Blackjack Basic Strategy / Perfect Play Advisor.

Validates statistically optimal decision recommendations for:
- Pair splitting (A-A, 8-8, 10-10, 5-5, etc.)
- Surrender qualifications (16 vs 9,10,A; 15 vs 10)
- Soft hands (A,2 through A,9)
- Hard hands (5 through 20)
- Fallback actions when doubling or splitting is disallowed
"""

from __future__ import annotations

import unittest
from rules import Card, get_basic_strategy_decision, BasicStrategyDecision


class TestBasicStrategy(unittest.TestCase):
    """Verifies standard mathematical basic strategy decision recommendations."""

    def test_pair_splitting(self):
        """Aces and 8s always split; 10s and 5s never split."""
        # Aces split against any dealer upcard
        for upcard_val in (2, 6, 10, 1):
            dec = get_basic_strategy_decision([Card(1), Card(1)], Card(upcard_val), can_split=True)
            self.assertEqual(dec.action, "SPLIT")
            self.assertIn("Split", dec.label)

        # 8s split against any dealer upcard
        for upcard_val in (2, 7, 10, 1):
            dec = get_basic_strategy_decision([Card(8), Card(8)], Card(upcard_val), can_split=True)
            self.assertEqual(dec.action, "SPLIT")

        # 10s never split -> always Stand
        for upcard_val in (5, 6, 10):
            dec = get_basic_strategy_decision([Card(10), Card(10)], Card(upcard_val), can_split=True)
            self.assertEqual(dec.action, "STAND")

        # 5s never split -> double against 2-9, hit against 10, A
        dec_55_vs_6 = get_basic_strategy_decision([Card(5), Card(5)], Card(6), can_split=True, can_double=True)
        self.assertEqual(dec_55_vs_6.action, "DOUBLE")

        dec_55_vs_10 = get_basic_strategy_decision([Card(5), Card(5)], Card(10), can_split=True, can_double=False)
        self.assertEqual(dec_55_vs_10.action, "HIT")

    def test_surrender_decisions(self):
        """Hard 16 surrenders vs 9, 10, A; Hard 15 surrenders vs 10."""
        # 16 vs 10 -> Surrender
        dec_16_vs_10 = get_basic_strategy_decision([Card(10), Card(6)], Card(10), can_surrender=True)
        self.assertEqual(dec_16_vs_10.action, "SURRENDER")

        # 16 vs 10 with surrender disabled -> Hit
        dec_16_vs_10_nosur = get_basic_strategy_decision([Card(10), Card(6)], Card(10), can_surrender=False)
        self.assertEqual(dec_16_vs_10_nosur.action, "HIT")

        # 15 vs 10 -> Surrender
        dec_15_vs_10 = get_basic_strategy_decision([Card(9), Card(6)], Card(10), can_surrender=True)
        self.assertEqual(dec_15_vs_10.action, "SURRENDER")

        # 15 vs 6 -> Stand (dealer bust card)
        dec_15_vs_6 = get_basic_strategy_decision([Card(9), Card(6)], Card(6), can_surrender=True)
        self.assertEqual(dec_15_vs_6.action, "STAND")

    def test_soft_hands(self):
        """Soft hands leverage Aces dynamically."""
        # Soft 18 (A, 7): Double vs 3-6, Stand vs 2, 7, 8; Hit vs 9, 10, A
        dec_soft18_vs_5 = get_basic_strategy_decision([Card(1), Card(7)], Card(5), can_double=True)
        self.assertEqual(dec_soft18_vs_5.action, "DOUBLE")

        dec_soft18_vs_7 = get_basic_strategy_decision([Card(1), Card(7)], Card(7), can_double=True)
        self.assertEqual(dec_soft18_vs_7.action, "STAND")

        dec_soft18_vs_9 = get_basic_strategy_decision([Card(1), Card(7)], Card(9), can_double=True)
        self.assertEqual(dec_soft18_vs_9.action, "HIT")

        # Soft 17 (A, 6): Double vs 3-6, else Hit
        dec_soft17_vs_4 = get_basic_strategy_decision([Card(1), Card(6)], Card(4), can_double=True)
        self.assertEqual(dec_soft17_vs_4.action, "DOUBLE")

        dec_soft17_vs_10 = get_basic_strategy_decision([Card(1), Card(6)], Card(10), can_double=True)
        self.assertEqual(dec_soft17_vs_10.action, "HIT")

        # Soft 20 (A, 9): Always Stand
        for upcard in (5, 6, 10, 1):
            dec_soft20 = get_basic_strategy_decision([Card(1), Card(9)], Card(upcard))
            self.assertEqual(dec_soft20.action, "STAND")

    def test_hard_hands(self):
        """Hard hand rules across dealer upcards."""
        # 11: Always Double if allowed, else Hit
        dec_11_vs_6 = get_basic_strategy_decision([Card(5), Card(6)], Card(6), can_double=True)
        self.assertEqual(dec_11_vs_6.action, "DOUBLE")

        dec_11_nodbl = get_basic_strategy_decision([Card(5), Card(6)], Card(6), can_double=False)
        self.assertEqual(dec_11_nodbl.action, "HIT")

        # 10: Double vs 2-9, Hit vs 10, A
        dec_10_vs_8 = get_basic_strategy_decision([Card(4), Card(6)], Card(8), can_double=True)
        self.assertEqual(dec_10_vs_8.action, "DOUBLE")

        dec_10_vs_10 = get_basic_strategy_decision([Card(4), Card(6)], Card(10), can_double=True)
        self.assertEqual(dec_10_vs_10.action, "HIT")

        # 12: Stand vs 4, 5, 6; Hit vs 2, 3, 7-A
        dec_12_vs_4 = get_basic_strategy_decision([Card(10), Card(2)], Card(4))
        self.assertEqual(dec_12_vs_4.action, "STAND")

        dec_12_vs_2 = get_basic_strategy_decision([Card(10), Card(2)], Card(2))
        self.assertEqual(dec_12_vs_2.action, "HIT")

        # 13-16: Stand vs 2-6, Hit vs 7-A (when no surrender)
        dec_14_vs_6 = get_basic_strategy_decision([Card(10), Card(4)], Card(6))
        self.assertEqual(dec_14_vs_6.action, "STAND")

        dec_14_vs_7 = get_basic_strategy_decision([Card(10), Card(4)], Card(7))
        self.assertEqual(dec_14_vs_7.action, "HIT")

        # 17+: Always Stand
        for total in (17, 18, 19, 20):
            dec_hard = get_basic_strategy_decision([Card(10), Card(total - 10)], Card(10))
            self.assertEqual(dec_hard.action, "STAND")


if __name__ == "__main__":
    unittest.main()
