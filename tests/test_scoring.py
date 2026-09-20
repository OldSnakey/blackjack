import unittest
from blackjack import score_hand


class TestScoreHand(unittest.TestCase):
    """Regression test suite for blackjack score_hand function."""

    def test_empty_hand(self):
        self.assertEqual(score_hand([]), 0)

    def test_number_cards_no_aces(self):
        self.assertEqual(score_hand([2]), 2)
        self.assertEqual(score_hand([2, 5]), 7)
        self.assertEqual(score_hand([7, 8]), 15)
        self.assertEqual(score_hand([10, 10]), 20)
        self.assertEqual(score_hand([2, 3, 4, 5, 6]), 20)

    def test_single_ace_as_eleven(self):
        # Ace counted as 11 when score <= 21
        self.assertEqual(score_hand([1]), 11)
        self.assertEqual(score_hand([1, 6]), 17)  # Soft 17
        self.assertEqual(score_hand([1, 9]), 20)  # Soft 20
        self.assertEqual(score_hand([1, 10]), 21)  # Natural Blackjack score

    def test_single_ace_reduced_to_one(self):
        # Ace downgraded to 1 when 11 would cause bust
        self.assertEqual(score_hand([1, 10, 5]), 16)  # 11 + 10 + 5 = 26 -> 16
        self.assertEqual(score_hand([10, 6, 1]), 17)  # 10 + 6 + 11 = 27 -> 17
        self.assertEqual(score_hand([1, 5, 8]), 14)  # 11 + 5 = 16 -> + 8 = 24 -> 14
        self.assertEqual(score_hand([10, 2, 1, 8]), 21)

    def test_multiple_aces(self):
        # Two aces: only one can be 11, the other must be 1 (11 + 1 = 12)
        self.assertEqual(score_hand([1, 1]), 12)
        # Three aces: 11 + 1 + 1 = 13
        self.assertEqual(score_hand([1, 1, 1]), 13)
        # Four aces: 11 + 1 + 1 + 1 = 14
        self.assertEqual(score_hand([1, 1, 1, 1]), 14)

    def test_multiple_aces_with_other_cards(self):
        self.assertEqual(score_hand([1, 1, 9]), 21)  # 11 + 1 + 9 = 21
        self.assertEqual(score_hand([1, 1, 10]), 12)  # 11 + 1 + 10 = 22 -> 1 + 1 + 10 = 12
        self.assertEqual(score_hand([10, 1, 1]), 12)
        self.assertEqual(score_hand([1, 8, 5, 1]), 15)  # 1 + 8 + 5 + 1 = 15
        self.assertEqual(score_hand([5, 8, 1, 1]), 15)
        self.assertEqual(score_hand([10, 6, 1, 1]), 18)

    def test_bust_hands(self):
        self.assertEqual(score_hand([10, 6, 6]), 22)
        self.assertEqual(score_hand([10, 10, 5]), 25)
        self.assertEqual(score_hand([10, 10, 10]), 30)
        self.assertEqual(score_hand([1, 5, 8, 8]), 22)  # 1 + 5 + 8 + 8 = 22


if __name__ == "__main__":
    unittest.main()
