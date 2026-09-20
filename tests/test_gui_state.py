import unittest


class GameStateMachine:
    """
    Reference state machine managing Blackjack control states
    to prevent race conditions and illegal transitions.
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
    """Verifies UI control state transitions to guarantee race-condition freedom."""

    def setUp(self):
        self.fsm = GameStateMachine()

    def test_initial_deal_normal(self):
        self.fsm.on_deal(player_has_natural=False)
        self.assertEqual(self.fsm.state, GameStateMachine.STATE_PLAYER_TURN)
        self.assertTrue(self.fsm.hit_enabled)
        self.assertTrue(self.fsm.stand_enabled)

    def test_initial_deal_natural_blackjack(self):
        self.fsm.on_deal(player_has_natural=True)
        self.assertEqual(self.fsm.state, GameStateMachine.STATE_ROUND_OVER)
        self.assertFalse(self.fsm.hit_enabled)
        self.assertFalse(self.fsm.stand_enabled)
        self.assertTrue(self.fsm.new_game_enabled)

    def test_player_bust_disables_actions(self):
        self.fsm.on_deal(player_has_natural=False)
        self.fsm.on_player_hit(player_score=22)  # Bust
        self.assertEqual(self.fsm.state, GameStateMachine.STATE_ROUND_OVER)
        self.assertFalse(self.fsm.hit_enabled)
        self.assertFalse(self.fsm.stand_enabled)
        self.assertTrue(self.fsm.new_game_enabled)

    def test_player_21_triggers_auto_stand(self):
        self.fsm.on_deal(player_has_natural=False)
        self.fsm.on_player_hit(player_score=21)  # Hit to 21
        self.assertEqual(self.fsm.state, GameStateMachine.STATE_DEALER_TURN)
        self.assertFalse(self.fsm.hit_enabled)
        self.assertFalse(self.fsm.stand_enabled)

    def test_player_stand_disables_actions_during_dealer_turn(self):
        self.fsm.on_deal(player_has_natural=False)
        self.fsm.on_player_stand()
        # In dealer turn, user cannot click hit or stand (prevents re-entrancy)
        self.assertEqual(self.fsm.state, GameStateMachine.STATE_DEALER_TURN)
        self.assertFalse(self.fsm.hit_enabled)
        self.assertFalse(self.fsm.stand_enabled)
        self.assertFalse(self.fsm.new_game_enabled)

    def test_dealer_completion_enables_new_game(self):
        self.fsm.on_deal(player_has_natural=False)
        self.fsm.on_player_stand()
        self.fsm.on_dealer_finished()
        self.assertEqual(self.fsm.state, GameStateMachine.STATE_ROUND_OVER)
        self.assertFalse(self.fsm.hit_enabled)
        self.assertFalse(self.fsm.stand_enabled)
        self.assertTrue(self.fsm.new_game_enabled)


if __name__ == "__main__":
    unittest.main()
