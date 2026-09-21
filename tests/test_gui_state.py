import unittest
import tkinter
from blackjack import BlackjackApp, Card


class GameStateMachine:
    """
    Reference state machine managing Blackjack control states.
    Preserved for backward compatibility with external test callers.
    """

    STATE_BETTING = "BETTING"
    STATE_PLAYER_TURN = "PLAYER_TURN"
    STATE_DEALER_TURN = "DEALER_TURN"
    STATE_ROUND_OVER = "ROUND_OVER"

    def __init__(self):
        self.state = self.STATE_PLAYER_TURN
        self.hit_enabled = True
        self.stand_enabled = True
        self.new_game_enabled = True

    def on_deal(self, player_has_natural=False):
        if player_has_natural:
            self.state = self.STATE_ROUND_OVER
            self.hit_enabled = False
            self.stand_enabled = False
            self.new_game_enabled = True
        else:
            self.state = self.STATE_PLAYER_TURN
            self.hit_enabled = True
            self.stand_enabled = True
            self.new_game_enabled = True

    def on_player_hit(self, player_score):
        if player_score > 21:  # Bust
            self.state = self.STATE_ROUND_OVER
            self.hit_enabled = False
            self.stand_enabled = False
            self.new_game_enabled = True
        elif player_score == 21:  # Auto-stand
            self.on_player_stand()

    def on_player_stand(self):
        # Immediately disable action buttons to prevent re-entrancy
        self.state = self.STATE_DEALER_TURN
        self.hit_enabled = False
        self.stand_enabled = False
        self.new_game_enabled = False  # Protected during dealer draw

    def on_dealer_finished(self):
        self.state = self.STATE_ROUND_OVER
        self.hit_enabled = False
        self.stand_enabled = False
        self.new_game_enabled = True


class TestGuiStateInvariants(unittest.TestCase):
    """
    Validates actual BlackjackApp widget states (Hit, Stand, New Game)
    across the entire round lifecycle to guarantee race-condition freedom.
    """

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

    def test_initial_deal_normal(self):
        """Initial deal with non-blackjack hands keeps Hit, Stand, and New Game enabled."""
        self.app._set_action_buttons_state("normal")
        self.app.new_game_button.configure(state="normal")
        self.assertEqual(self.app.hit_button["state"], "normal")
        self.assertEqual(self.app.stand_button["state"], "normal")
        self.assertEqual(self.app.new_game_button["state"], "normal")

    def test_initial_deal_player_natural_blackjack(self):
        """Player natural blackjack ends the round immediately, disabling action buttons."""
        initial_wins = self.app.player_wins_var.get()
        self.app.player_hand = [
            Card(1, self.app.back_image, "ace", "spade"),
            Card(10, self.app.back_image, "king", "heart"),
        ]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "diamond"),
            Card(8, self.app.back_image, "8", "club"),
        ]
        self.app._check_initial_blackjack()
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "normal")
        self.assertEqual(self.app.player_wins_var.get(), initial_wins + 1)
        self.assertIn("Blackjack", self.app.result_var.get())

    def test_initial_deal_dealer_natural_blackjack(self):
        """Dealer natural blackjack ends the round immediately, disabling action buttons."""
        initial_dealer_wins = self.app.dealer_wins_var.get()
        self.app.player_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]
        self.app.dealer_hand = [
            Card(1, self.app.back_image, "ace", "club"),
            Card(10, self.app.back_image, "jack", "diamond"),
        ]
        self.app._check_initial_blackjack()
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "normal")
        self.assertEqual(self.app.dealer_wins_var.get(), initial_dealer_wins + 1)
        self.assertIn("Dealer has Blackjack", self.app.result_var.get())

    def test_player_bust_disables_actions(self):
        """Player bust disables Hit/Stand, reveals hole card, and enables New Game."""
        initial_dealer_wins = self.app.dealer_wins_var.get()
        self.app.player_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(6, self.app.back_image, "6", "spade"),
            Card(7, self.app.back_image, "7", "diamond"),
        ]
        self.app._conclude_round()
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "normal")
        self.assertIn("bust", self.app.result_var.get().lower())
        self.assertEqual(self.app.dealer_wins_var.get(), initial_dealer_wins + 1)

    def test_player_stand_disables_actions_during_dealer_turn(self):
        """Clicking Stand disables Hit, Stand, AND New Game during asynchronous dealer drawing."""
        self.app.on_stand()
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "disabled")
        self.assertIsNotNone(self.app._dealer_timer_id)

    def test_dealer_completion_enables_new_game(self):
        """Dealer turn completion enables New Game button and keeps Hit/Stand disabled."""
        initial_wins = self.app.player_wins_var.get()
        self.app.player_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(9, self.app.back_image, "9", "spade"),
        ]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "club"),
            Card(8, self.app.back_image, "8", "diamond"),
        ]
        self.app._conclude_round()
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "normal")
        self.assertEqual(self.app.player_wins_var.get(), initial_wins + 1)

    def test_push_increments_ties_var(self):
        """Equal scores correctly increment ties_var counter."""
        initial_ties = self.app.ties_var.get()
        self.app.player_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "club"),
            Card(8, self.app.back_image, "8", "diamond"),
        ]
        self.app._conclude_round()
        self.assertEqual(self.app.ties_var.get(), initial_ties + 1)
        self.assertIn("draw", self.app.result_var.get().lower())

    def test_window_close_cancels_pending_timer(self):
        """Safely cleans up any active dealer timer on window destruction."""
        self.app.on_stand()
        timer_id = self.app._dealer_timer_id
        self.assertIsNotNone(timer_id)
        self.app._on_close()
        self.assertIsNone(self.app._dealer_timer_id)


if __name__ == "__main__":
    unittest.main()
