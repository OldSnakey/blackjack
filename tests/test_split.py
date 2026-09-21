import unittest
import tkinter
from blackjack import BlackjackApp, Card, can_split


class TestSplitLogicAndState(unittest.TestCase):
    """Test suite covering hand splitting eligibility, state transitions, and outcomes."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.app._on_close()
        except tkinter.TclError:
            pass

    def test_can_split_identical_ranks(self):
        """Pairs of cards with identical ranks must be eligible to split."""
        card_8h = Card(8, self.app.back_image, rank="8", suit="heart")
        card_8s = Card(8, self.app.back_image, rank="8", suit="spade")
        self.assertTrue(can_split([card_8h, card_8s]))

        card_kh = Card(10, self.app.back_image, rank="king", suit="heart")
        card_kd = Card(10, self.app.back_image, rank="king", suit="diamond")
        self.assertTrue(can_split([card_kh, card_kd]))

        card_ah = Card(1, self.app.back_image, rank="ace", suit="heart")
        card_as = Card(1, self.app.back_image, rank="ace", suit="spade")
        self.assertTrue(can_split([card_ah, card_as]))

        # Plain integers fallback
        self.assertTrue(can_split([7, 7]))

    def test_can_split_mismatched_ranks(self):
        """Cards with different ranks are not eligible to split."""
        card_8h = Card(8, self.app.back_image, rank="8", suit="heart")
        card_9h = Card(9, self.app.back_image, rank="9", suit="heart")
        self.assertFalse(can_split([card_8h, card_9h]))

        # King and Queen both have value 10, but different ranks
        card_kh = Card(10, self.app.back_image, rank="king", suit="heart")
        card_qh = Card(10, self.app.back_image, rank="queen", suit="heart")
        self.assertFalse(can_split([card_kh, card_qh]))

        self.assertFalse(can_split([7, 8]))

    def test_can_split_invalid_card_count(self):
        """Hands with fewer than 2 or more than 2 cards cannot be split."""
        card_8h = Card(8, self.app.back_image, rank="8", suit="heart")
        self.assertFalse(can_split([]))
        self.assertFalse(can_split([card_8h]))
        self.assertFalse(can_split([card_8h, card_8h, card_8h]))

    def test_split_creates_two_hands_and_disables_button(self):
        """Executing a split separates cards into two hands, deals a card to each, and disables Split."""
        card_8h = Card(8, self.app.back_image, rank="8", suit="heart")
        card_8s = Card(8, self.app.back_image, rank="8", suit="spade")
        self.app.player_hands = [[card_8h, card_8s]]
        self.app.active_hand_index = 0
        self.app.split_button.configure(state="normal")

        self.app.on_split()

        self.assertEqual(len(self.app.player_hands), 2)
        self.assertEqual(len(self.app.player_hands[0]), 2)
        self.assertEqual(len(self.app.player_hands[1]), 2)
        self.assertEqual(self.app.active_hand_index, 0)
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.hit_button["state"], "normal")
        self.assertEqual(self.app.stand_button["state"], "normal")

    def test_split_turn_progression_across_hands(self):
        """Standing on Hand 1 advances focus to Hand 2; standing on Hand 2 triggers dealer turn."""
        card_8h = Card(8, self.app.back_image, rank="8", suit="heart")
        card_8s = Card(8, self.app.back_image, rank="8", suit="spade")
        self.app.player_hands = [[card_8h, card_8s]]
        self.app.active_hand_index = 0
        self.app.on_split()

        self.assertEqual(self.app.active_hand_index, 0)
        # Stand on Hand 1 -> should advance to Hand 2
        self.app.on_stand()
        self.assertEqual(self.app.active_hand_index, 1)
        self.assertEqual(self.app.hit_button["state"], "normal")
        self.assertEqual(self.app.stand_button["state"], "normal")
        self.assertIsNone(self.app._dealer_timer_id)

        # Stand on Hand 2 -> should start dealer turn
        self.app.on_stand()
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "disabled")
        self.assertIsNotNone(self.app._dealer_timer_id)

    def test_split_double_win_resolution(self):
        """When both split hands beat the dealer, player_wins_var increments by 2."""
        initial_wins = self.app.player_wins_var.get()
        # Hand 1 = 20, Hand 2 = 19
        hand1 = [Card(10, self.app.back_image, "10", "heart"), Card(10, self.app.back_image, "10", "spade")]
        hand2 = [Card(10, self.app.back_image, "10", "club"), Card(9, self.app.back_image, "9", "diamond")]
        self.app.player_hands = [hand1, hand2]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]  # Dealer = 18

        self.app._conclude_round()

        self.assertEqual(self.app.player_wins_var.get(), initial_wins + 2)
        self.assertIn("Hand 1: Player WINS!", self.app.result_var.get())
        self.assertIn("Hand 2: Player WINS!", self.app.result_var.get())

    def test_split_win_and_loss_resolution(self):
        """When Hand 1 wins and Hand 2 loses, player_wins_var and dealer_wins_var each increment by 1."""
        initial_player_wins = self.app.player_wins_var.get()
        initial_dealer_wins = self.app.dealer_wins_var.get()

        hand1 = [Card(10, self.app.back_image, "10", "heart"), Card(10, self.app.back_image, "10", "spade")]  # 20
        hand2 = [Card(10, self.app.back_image, "10", "club"), Card(6, self.app.back_image, "6", "diamond")]   # 16
        self.app.player_hands = [hand1, hand2]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]  # Dealer = 18

        self.app._conclude_round()

        self.assertEqual(self.app.player_wins_var.get(), initial_player_wins + 1)
        self.assertEqual(self.app.dealer_wins_var.get(), initial_dealer_wins + 1)
        self.assertIn("Hand 1: Player WINS!", self.app.result_var.get())
        self.assertIn("Hand 2: The dealer wins!", self.app.result_var.get())

    def test_split_button_disabled_after_hit(self):
        """Taking a hit disables the split button so player cannot split after drawing a 3rd card."""
        card_8h = Card(8, self.app.back_image, rank="8", suit="heart")
        card_8s = Card(8, self.app.back_image, rank="8", suit="spade")
        self.app.player_hands = [[card_8h, card_8s]]
        self.app.split_button.configure(state="normal")

        self.app.on_hit()

        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(len(self.app.player_hands[0]), 3)


if __name__ == "__main__":
    unittest.main()
