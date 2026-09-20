import unittest
from blackjack import score_hand, determine_outcome, dealer_should_hit


class TestGameRules(unittest.TestCase):
    """Test specifications for Blackjack game outcomes and dealer AI rules."""

    def test_player_busts(self):
        outcome, _ = determine_outcome([10, 6, 7], [10, 7])
        self.assertEqual(outcome, 'PLAYER_BUST')

    def test_dealer_busts(self):
        outcome, _ = determine_outcome([10, 8], [10, 6, 7])
        self.assertEqual(outcome, 'DEALER_BUST')

    def test_player_higher_score(self):
        outcome, _ = determine_outcome([10, 10], [10, 9])
        self.assertEqual(outcome, 'PLAYER_WINS')

        outcome, _ = determine_outcome([1, 7], [10, 7])  # 18 vs 17
        self.assertEqual(outcome, 'PLAYER_WINS')

    def test_dealer_higher_score(self):
        outcome, _ = determine_outcome([10, 7], [10, 9])
        self.assertEqual(outcome, 'DEALER_WINS')

    def test_push_equal_scores(self):
        outcome, _ = determine_outcome([10, 8], [10, 8])
        self.assertEqual(outcome, 'PUSH')

        outcome, _ = determine_outcome([1, 6], [10, 7])  # 17 vs 17
        self.assertEqual(outcome, 'PUSH')

    def test_natural_blackjack(self):
        # Player has Ace + 10 = 21 on initial deal
        outcome, _ = determine_outcome([1, 10], [10, 8])
        self.assertEqual(outcome, 'NATURAL_BLACKJACK')

        # Both have Ace + 10 = 21 -> Push
        outcome, _ = determine_outcome([1, 10], [10, 1])
        self.assertEqual(outcome, 'PUSH')

        # Dealer has Ace + 10, player has 21 but with 3 cards -> Dealer wins with natural
        outcome, _ = determine_outcome([7, 7, 7], [1, 10])
        self.assertEqual(outcome, 'DEALER_WINS')

    def test_dealer_should_hit_logic(self):
        # Dealer must hit below 17
        self.assertTrue(dealer_should_hit([10, 6]))  # 16
        self.assertTrue(dealer_should_hit([5, 8]))   # 13
        self.assertTrue(dealer_should_hit([1, 5]))   # soft 16

        # Dealer must stand on 17 or higher
        self.assertFalse(dealer_should_hit([10, 7]))  # 17
        self.assertFalse(dealer_should_hit([1, 6]))   # soft 17 (S17 rule)
        self.assertFalse(dealer_should_hit([10, 8]))  # 18
        self.assertFalse(dealer_should_hit([10, 10])) # 20
        self.assertFalse(dealer_should_hit([10, 6, 6])) # 22 (bust)


if __name__ == "__main__":
    unittest.main()
