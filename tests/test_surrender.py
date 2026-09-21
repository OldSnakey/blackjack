import unittest
import tkinter
from blackjack import BlackjackApp, Card


class TestLateSurrender(unittest.TestCase):
    """Test suite covering Late Surrender eligibility, 50% wager refund, hole card reveal, and resolution."""

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

    def test_surrender_eligibility(self):
        """Surrender is enabled only on initial 2 cards of an un-split hand."""
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        self.app.active_hand_index = 0
        self.app._update_action_buttons()

        self.assertEqual(self.app.surrender_button["state"], "normal")

        # After hitting, Surrender is disabled
        self.app._deal_card_to_player()
        self.app._update_action_buttons()
        self.assertEqual(self.app.surrender_button["state"], "disabled")

    def test_surrender_disabled_on_split_hands(self):
        """Surrender cannot be used after splitting."""
        self.app.player_hands = [
            [Card(8, self.app.back_image, rank="8", suit="heart"), Card(5, self.app.back_image, rank="5", suit="club")],
            [Card(8, self.app.back_image, rank="8", suit="spade"), Card(6, self.app.back_image, rank="6", suit="diamond")],
        ]
        self.app.active_hand_index = 0
        self.app._update_action_buttons()

        self.assertEqual(self.app.surrender_button["state"], "disabled")

    def test_surrender_chips_mode_refunds_half_wager_and_flips_hole_card(self):
        """In Chips Mode, Surrender refunds 50% of the bet to bankroll and reveals the hole card."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        card_hole = Card(7, self.app.back_image, rank="7", suit="diamond")
        self.app.dealer_hand = [
            Card(10, self.app.back_image, rank="10", suit="club"),
            card_hole,
        ]
        self.app.dealer_hole_card = card_hole
        self.app.dealer_hole_widget = tkinter.Label(self.app.dealer_cards_frame, image=self.app.back_image)

        initial_dealer_wins = self.app.dealer_wins_var.get()
        self.app.on_surrender()

        # 50% of $50 = $25 refunded -> bankroll 950 + 25 = 975
        self.assertEqual(self.app.bankroll_var.get(), 975)
        self.assertEqual(self.app.dealer_wins_var.get(), initial_dealer_wins + 1)
        self.assertIn("Surrendered", self.app.result_var.get())
        self.assertIn("($25)", self.app.result_var.get())
        self.assertEqual(self.app.new_game_button["state"], "normal")
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")

    def test_surrender_casual_mode_forfeits_hand(self):
        """In Casual Mode, Surrender records dealer win and completes the hand."""
        self.app.chips_mode_var.set(False)
        self.app.new_game()
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        card_hole = Card(8, self.app.back_image, rank="8", suit="diamond")
        self.app.dealer_hand = [
            Card(10, self.app.back_image, rank="10", suit="club"),
            card_hole,
        ]
        self.app.dealer_hole_card = card_hole
        self.app.dealer_hole_widget = tkinter.Label(self.app.dealer_cards_frame, image=self.app.back_image)

        initial_dealer_wins = self.app.dealer_wins_var.get()
        self.app.on_surrender()

        self.assertEqual(self.app.dealer_wins_var.get(), initial_dealer_wins + 1)
        self.assertIn("Surrendered", self.app.result_var.get())
        self.assertEqual(self.app.new_game_button["state"], "normal")


if __name__ == "__main__":
    unittest.main()
