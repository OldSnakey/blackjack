import unittest
import tkinter
from blackjack import BlackjackApp, Card


class TestDoubleDown(unittest.TestCase):
    """Test suite covering Double Down eligibility, bankroll deduction, single card draw, and auto-stand."""

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

    def test_double_down_eligibility_initial_cards(self):
        """Double Down is enabled on initial 2 cards, and disabled after hitting."""
        self.app.player_hands = [[
            Card(5, self.app.back_image, rank="5", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        self.app.active_hand_index = 0
        self.app._update_action_buttons()

        self.assertEqual(self.app.double_button["state"], "normal")

        # Dealing a 3rd card disables Double Down
        self.app._deal_card_to_player()
        self.assertEqual(len(self.app.player_hands[0]), 3)
        self.app._update_action_buttons()
        self.assertEqual(self.app.double_button["state"], "disabled")

    def test_double_down_insufficient_bankroll_disables_button(self):
        """In Chips Mode, Double Down is disabled if bankroll is less than the active hand bet."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(20)  # Bankroll only $20
        self.app.hand_bets = [50]      # Bet is $50
        self.app.player_hands = [[
            Card(5, self.app.back_image, rank="5", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        self.app.active_hand_index = 0
        self.app._update_action_buttons()

        self.assertEqual(self.app.double_button["state"], "disabled")

        # Invoking on_double_down directly does nothing
        self.app.on_double_down()
        self.assertEqual(self.app.bankroll_var.get(), 20)
        self.assertEqual(self.app.hand_bets[0], 50)
        self.assertEqual(len(self.app.player_hands[0]), 2)

    def test_double_down_execution_doubles_bet_deals_one_card_and_stands(self):
        """Executing Double Down doubles wager, draws exactly 1 card, and transitions to dealer turn."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]
        self.app.player_hands = [[
            Card(5, self.app.back_image, rank="5", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="club"),
        ]
        self.app.active_hand_index = 0
        self.app._update_action_buttons()

        # Stack deck so drawn card is a 9 (total 20, non-busting)
        card_9 = Card(9, self.app.back_image, rank="9", suit="club")
        self.app.deck.append(card_9)

        self.app.on_double_down()

        # Wager doubled to $100, bankroll decremented by $50 (950 - 50 = 900)
        self.assertEqual(self.app.hand_bets[0], 100)
        self.assertEqual(self.app.bankroll_var.get(), 900)
        self.assertEqual(len(self.app.player_hands[0]), 3)

        # Action buttons disabled and dealer turn initiated
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.double_button["state"], "disabled")
        self.assertIsNotNone(self.app._dealer_timer_id)

    def test_double_down_bust_resolves_immediately(self):
        """Busting on Double Down immediately reveals dealer hole card and concludes round."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="heart"),
            Card(6, self.app.back_image, rank="6", suit="spade"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="club"),
        ]
        self.app.active_hand_index = 0

        # Stack deck so drawn card causes bust (10 + 6 + 10 = 26)
        card_10 = Card(10, self.app.back_image, rank="10", suit="club")
        self.app.deck.append(card_10)

        self.app.on_double_down()

        self.assertEqual(len(self.app.player_hands[0]), 3)
        self.assertEqual(self.app.hand_bets[0], 100)
        self.assertIn("bust", self.app.result_var.get().lower())
        self.assertEqual(self.app.new_game_button["state"], "normal")


if __name__ == "__main__":
    unittest.main()
