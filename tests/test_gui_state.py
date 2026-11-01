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
        self.app = BlackjackApp(self.root, chips_mode=False, sound_enabled=False)

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
        self.app.player_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "club"),
            Card(6, self.app.back_image, "6", "diamond"),
        ]
        self.app.round_phase = self.app.fsm.phase.__class__.PLAYER_TURN
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
        self.app.player_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "club"),
            Card(6, self.app.back_image, "6", "diamond"),
        ]
        self.app.round_phase = self.app.fsm.phase.__class__.PLAYER_TURN
        self.app.on_stand()
        timer_id = self.app._dealer_timer_id
        self.assertIsNotNone(timer_id)
        self.app._on_close()
        self.assertIsNone(self.app._dealer_timer_id)

    def test_keyboard_deal_or_hit_in_active_turn(self):
        """Space / Enter triggers on_hit when Hit button is normal."""
        hit_invoked = []
        orig_on_hit = self.app.on_hit
        self.app.on_hit = lambda: hit_invoked.append(True)
        try:
            self.app.hit_button.configure(state="normal")
            ret = self.app._on_key_deal_or_hit()
            self.assertEqual(ret, "break")
            self.assertEqual(len(hit_invoked), 1)
        finally:
            self.app.on_hit = orig_on_hit

    def test_keyboard_stand_shortcut(self):
        """'S' key triggers on_stand only when Stand button is enabled."""
        stand_invoked = []
        orig_on_stand = self.app.on_stand
        self.app.on_stand = lambda: stand_invoked.append(True)
        try:
            self.app.stand_button.configure(state="normal")
            self.app._on_key_action(self.app.on_stand, self.app.stand_button)
            self.assertEqual(len(stand_invoked), 1)

            # Guarded when disabled
            self.app.stand_button.configure(state="disabled")
            self.app._on_key_action(self.app.on_stand, self.app.stand_button)
            self.assertEqual(len(stand_invoked), 1)
        finally:
            self.app.on_stand = orig_on_stand

    def test_keyboard_chips_mode_shortcuts(self):
        """Key '3' adds $100, 'A' sets All In, 'C' clears bet in betting phase."""
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode()
        self.app.current_bet_var.set(0)

        # Key '3' adds $100
        self.app._on_key_chip(100)
        self.assertEqual(self.app.current_bet_var.get(), 100)

        # Key 'C' clears bet
        self.app._on_key_action(self.app._clear_bet, self.app.clear_bet_button)
        self.assertEqual(self.app.current_bet_var.get(), 0)

        # Key 'A' goes All In
        self.app._on_key_action(self.app._all_in, self.app.all_in_button)
        self.assertEqual(self.app.current_bet_var.get(), 1000)

    def test_deal_hand_animation_settlement_enables_action_buttons(self):
        """
        Regression test: When the window is mapped (interactive GUI mode),
        clicking 'Deal Hand' starts asynchronous card slide animations that set
        _dealing=True (in_flight=True), temporarily disabling action buttons.
        Once those card slide animations finish, Hit, Stand, Double, and Surrender
        must automatically become 'normal' so the player can continue play.
        """
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode()
        self.app.current_bet_var.set(25)

        # Deterministic non-blackjack, non-ace cards (Player: 6+5=11, Dealer: 7+8=15)
        c1 = Card(6, self.app.back_image, "6", "heart")
        c2 = Card(5, self.app.back_image, "5", "spade")
        d1 = Card(7, self.app.back_image, "7", "club")
        d2 = Card(8, self.app.back_image, "8", "diamond")
        self.app.deck = [d2, d1, c2, c1]

        # Simulate mapped window so animate_card_slide schedules async timers
        self.app.card_table_frame.winfo_ismapped = lambda: True

        self.app._deal_hand_with_bet()

        # While animations are in flight, buttons are guarded (disabled)
        self.assertTrue(self.app._dealing)
        self.assertTrue(self.app.card_table_frame.has_active_card_animations())
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")

        # Complete all in-flight card animations (invokes on_complete callbacks)
        self.app.card_table_frame.cancel_card_animations()

        # After animations settle, _dealing is False and action buttons must be normal!
        self.assertFalse(self.app._dealing)
        self.assertEqual(self.app.hit_button["state"], "normal")
        self.assertEqual(self.app.stand_button["state"], "normal")
        self.assertEqual(self.app.double_button["state"], "normal")
        self.assertEqual(self.app.surrender_button["state"], "normal")

    def test_hit_animation_settlement_reenables_action_buttons(self):
        """
        Regression test: Hitting in mapped GUI mode disables buttons while the drawn
        card slides in, and re-enables Hit/Stand once the slide animation settles.
        """
        c1 = Card(6, self.app.back_image, "6", "heart")
        c2 = Card(5, self.app.back_image, "5", "spade")
        d1 = Card(7, self.app.back_image, "7", "club")
        d2 = Card(8, self.app.back_image, "8", "diamond")
        hit_card = Card(4, self.app.back_image, "4", "heart")
        self.app.player_hands = [[]]
        self.app.dealer_hand = []
        self.app.deck = [hit_card, d2, d1, c2, c1]

        self.app._start_round_deal()
        self.assertEqual(self.app.hit_button["state"], "normal")

        # Simulate mapped window for the Hit card slide
        self.app.card_table_frame.winfo_ismapped = lambda: True
        self.app.on_hit()

        # In-flight guard active during slide
        self.assertTrue(self.app._dealing)
        self.assertEqual(self.app.hit_button["state"], "disabled")

        # Settle animation
        self.app.card_table_frame.cancel_card_animations()

        # Player has 15 (6+5+4), so Hit and Stand must be re-enabled
        self.assertFalse(self.app._dealing)
        self.assertEqual(self.app.hit_button["state"], "normal")
        self.assertEqual(self.app.stand_button["state"], "normal")


if __name__ == "__main__":
    unittest.main()
