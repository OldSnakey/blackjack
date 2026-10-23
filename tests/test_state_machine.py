"""
Unit test suite for the first-class `Hand` domain model (`rules.py`),
`GameStateMachine` (`state_machine.py`), and headless `BlackjackEngine` (`game_engine.py`).
"""

from __future__ import annotations

import unittest
from rules import Card, Hand, RoundPhase
from state_machine import GameStateMachine, InvalidStateTransitionError
from game_engine import BlackjackEngine
from event_bus import EventHub, GameEventType


class TestHandAndStateMachine(unittest.TestCase):
    """Tests for Hand domain model, GameStateMachine transitions, and headless BlackjackEngine."""

    def test_hand_domain_model_and_sequence_compatibility(self):
        """Hand encapsulates bet/flags/score while remaining 100% compatible with list[Card]."""
        c1 = Card(1, None, "ace", "spade")
        c2 = Card(10, None, "king", "spade")
        hand = Hand([c1, c2], bet=100)

        # List-like sequence behavior
        self.assertEqual(len(hand), 2)
        self.assertEqual(hand[0], c1)
        self.assertEqual(list(hand), [c1, c2])

        # Domain properties
        self.assertEqual(hand.bet, 100)
        self.assertEqual(hand.score, 21)
        self.assertTrue(hand.is_soft)
        self.assertTrue(hand.is_blackjack)
        self.assertFalse(hand.is_bust)
        self.assertFalse(hand.can_split)

        # Pair hand can_split and add_card bust check
        pair = Hand([Card(8, None, "8", "heart"), Card(8, None, "8", "club")], bet=50)
        self.assertTrue(pair.can_split)
        self.assertTrue(pair.can_double)
        pair.add_card(Card(10, None, "10", "diamond"))
        self.assertEqual(pair.score, 26)
        self.assertTrue(pair.is_bust)
        self.assertTrue(pair.is_stood)

    def test_fsm_valid_and_invalid_transitions(self):
        """GameStateMachine enforces legal transitions and exposes legacy boolean flags."""
        fsm = GameStateMachine(initial_phase=RoundPhase.BETTING)
        self.assertTrue(fsm.is_betting_phase)
        self.assertFalse(fsm.is_insurance_phase)
        self.assertFalse(fsm.is_round_over)

        # Valid transition: BETTING -> INITIAL_DEAL -> INSURANCE -> PLAYER_TURN -> DEALER_TURN -> ROUND_OVER
        self.assertTrue(fsm.can_transition(RoundPhase.INITIAL_DEAL))
        fsm.transition_to(RoundPhase.INITIAL_DEAL)
        self.assertTrue(fsm.is_dealing)

        fsm.transition_to(RoundPhase.INSURANCE)
        self.assertTrue(fsm.is_insurance_phase)

        fsm.transition_to(RoundPhase.PLAYER_TURN)
        self.assertFalse(fsm.is_insurance_phase)

        fsm.transition_to(RoundPhase.DEALER_TURN)
        fsm.transition_to(RoundPhase.ROUND_OVER)
        self.assertTrue(fsm.is_round_over)

        # Illegal transition: BETTING directly to DEALER_TURN should raise InvalidStateTransitionError
        fsm.transition_to(RoundPhase.BETTING)
        self.assertFalse(fsm.can_transition(RoundPhase.DEALER_TURN))
        with self.assertRaises(InvalidStateTransitionError):
            fsm.transition_to(RoundPhase.DEALER_TURN)

    def test_headless_blackjack_engine_lifecycle(self):
        """BlackjackEngine executes a complete round headlessly without Tkinter."""
        bus = EventHub()
        events = []
        bus.subscribe(GameEventType.CARD_DEALT, lambda ev: events.append(ev))
        bus.subscribe(GameEventType.ROUND_RESOLVED, lambda ev: events.append(ev))

        engine = BlackjackEngine(bankroll=1000, event_bus=bus)
        # Rig top of shoe (pop order: player c1, player c2, dealer up, dealer hole, player hit)
        engine.shoe = [
            Card(7, None, "7", "club"),     # 5th: dealer draw -> 18
            Card(5, None, "5", "heart"),    # 4th: player hit -> 20
            Card(8, None, "8", "diamond"),  # 3rd: dealer hole -> 18
            Card(10, None, "10", "spade"),  # 2nd: dealer upcard
            Card(9, None, "9", "club"),     # 1st: player card 2 -> 15
            Card(6, None, "6", "heart"),    # 0th: player card 1
        ]

        p_hand, d_hand = engine.deal_round(bet=100)
        self.assertEqual(engine.bankroll, 900)
        self.assertEqual(p_hand.score, 15)
        self.assertEqual(len(d_hand), 2)
        self.assertEqual(engine.phase, RoundPhase.PLAYER_TURN)

        # Hit player to 20, then stand
        drawn = engine.hit(0)
        self.assertEqual(drawn.value, 5)
        self.assertEqual(engine.player_hands[0].score, 20)
        engine.stand(0)
        self.assertEqual(engine.phase, RoundPhase.DEALER_TURN)

        # Resolve outcomes (20 vs 18 -> PLAYER_WINS -> +200 return -> bankroll 1100)
        results = engine.resolve_outcomes()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].outcome, "PLAYER_WINS")
        self.assertEqual(results[0].payout, 200)
        self.assertEqual(engine.bankroll, 1100)
        self.assertEqual(engine.phase, RoundPhase.ROUND_OVER)
        self.assertGreaterEqual(len(events), 5)


if __name__ == "__main__":
    unittest.main()
