import unittest
from blackjack import score_hand


def determine_outcome(player_hand, dealer_hand):
    """
    Evaluates the outcome of a completed round of Blackjack.
    Returns a tuple of (outcome_code, message):
      - 'PLAYER_BUST': Player exceeded 21 (Dealer wins)
      - 'DEALER_BUST': Dealer exceeded 21 (Player wins)
      - 'NATURAL_BLACKJACK': Player has 21 on initial deal (Player wins)
      - 'PLAYER_WINS': Player score higher than dealer
      - 'DEALER_WINS': Dealer score higher than player
      - 'PUSH': Tie / Draw
    """
    player_score = score_hand(player_hand)
    dealer_score = score_hand(dealer_hand)

    # 1. Player Bust
    if player_score > 21:
        return 'PLAYER_BUST', 'You bust, dealer wins!'

    # Check for natural blackjack (initial 2 cards totaling 21)
    player_natural = (len(player_hand) == 2 and player_score == 21)
    dealer_natural = (len(dealer_hand) == 2 and dealer_score == 21)

    if player_natural and dealer_natural:
        return 'PUSH', "Both have Blackjack! It's a draw."
    if player_natural:
        return 'NATURAL_BLACKJACK', 'Player has Blackjack! You win!'
    if dealer_natural:
        return 'DEALER_WINS', 'Dealer has Blackjack! Dealer wins!'

    # 2. Dealer Bust
    if dealer_score > 21:
        return 'DEALER_BUST', 'Dealer busts, Player WINS!'

    # 3. Compare scores
    if player_score > dealer_score:
        return 'PLAYER_WINS', 'Player WINS!'
    elif dealer_score > player_score:
        return 'DEALER_WINS', 'The dealer wins!'
    else:
        return 'PUSH', "It's a draw"


def dealer_should_hit(dealer_hand):
    """Under standard S17 rules, dealer hits on < 17 and stands on >= 17."""
    return score_hand(dealer_hand) < 17


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
