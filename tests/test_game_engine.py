"""
Modular Unit Test Suite for Headless BlackjackEngine (`game_engine.py`).

Tests the complete casino game lifecycle, betting math, hand actions, dealer drawing,
insurance resolution, and event dispatching with ZERO Tkinter or GUI dependencies.
"""

from __future__ import annotations

import unittest
from event_bus import EventHub, GameEventType
from game_engine import BlackjackEngine, RoundResult
from rules import Card, Hand, RoundPhase


class TestBlackjackEngineModular(unittest.TestCase):
    """Verifies BlackjackEngine lifecycle, rule transitions, and payout math in isolation."""

    def setUp(self):
        self.bus = EventHub()
        self.events = []
        for et in GameEventType:
            self.bus.subscribe(et, lambda ev: self.events.append(ev))
        self.engine = BlackjackEngine(bankroll=1000, event_bus=self.bus)

    def test_deal_round_standard_and_events(self):
        # Rig shoe: player (6, 9 -> 15), dealer (10 upcard, 8 hole -> 18)
        self.engine.shoe = [
            Card(8, None, "8", "diamond"),  # dealer hole
            Card(10, None, "10", "spade"),  # dealer upcard
            Card(9, None, "9", "club"),     # player card 2
            Card(6, None, "6", "heart"),    # player card 1
        ]
        p_hand, d_hand = self.engine.deal_round(bet=100)
        self.assertEqual(self.engine.bankroll, 900)
        self.assertEqual(self.engine.current_bet, 100)
        self.assertEqual(p_hand.score, 15)
        self.assertEqual(len(d_hand), 2)
        self.assertEqual(d_hand[0].value, 10)
        self.assertEqual(self.engine.phase, RoundPhase.PLAYER_TURN)

        # Check emitted events
        event_types = [e.event_type for e in self.events]
        self.assertIn(GameEventType.BET_COMMITTED, event_types)
        self.assertIn(GameEventType.CARD_DEALT, event_types)

    def test_invalid_bet_rejection(self):
        with self.assertRaises(ValueError):
            self.engine.deal_round(bet=-50)
        with self.assertRaises(ValueError):
            self.engine.deal_round(bet=2000)

    def test_insurance_flow_taken_and_won(self):
        # Dealer upcard is Ace, hole card is King (Natural Blackjack)
        self.engine.shoe = [
            Card(10, None, "king", "diamond"),  # dealer hole (King)
            Card(1, None, "ace", "spade"),      # dealer upcard (Ace)
            Card(9, None, "9", "club"),         # player card 2
            Card(10, None, "jack", "heart"),    # player card 1 (19)
        ]
        p_hand, d_hand = self.engine.deal_round(bet=100)
        self.assertEqual(self.engine.phase, RoundPhase.INSURANCE)

        # Take insurance for $50
        ins = self.engine.take_insurance(50)
        self.assertEqual(ins, 50)
        self.assertEqual(self.engine.bankroll, 850)
        # Dealer has 21, so transitions to RESOLUTION
        self.assertEqual(self.engine.phase, RoundPhase.RESOLUTION)

        # Resolve outcomes: player loses main bet ($100), wins insurance 2:1 ($50 -> +$150 return)
        results = self.engine.resolve_outcomes()
        self.assertEqual(results[0].outcome, "DEALER_WINS")
        self.assertIn("Dealer has Blackjack", results[0].message)
        # Bankroll was 850, insurance pays +150 -> 1000
        self.assertEqual(self.engine.bankroll, 1000)
        self.assertEqual(self.engine.phase, RoundPhase.ROUND_OVER)

    def test_insurance_flow_declined(self):
        # Dealer upcard is Ace, hole card is 7 (no Blackjack)
        self.engine.shoe = [
            Card(7, None, "7", "diamond"),   # dealer hole (7)
            Card(1, None, "ace", "spade"),   # dealer upcard (Ace)
            Card(9, None, "9", "club"),      # player card 2
            Card(8, None, "8", "heart"),     # player card 1 (17)
        ]
        self.engine.deal_round(bet=100)
        self.assertEqual(self.engine.phase, RoundPhase.INSURANCE)

        self.engine.decline_insurance()
        self.assertEqual(self.engine.phase, RoundPhase.PLAYER_TURN)
        self.assertEqual(self.engine.insurance_bet, 0)

    def test_hit_and_bust(self):
        # Player dealt 16, draws 10 -> 26 bust
        self.engine.shoe = [
            Card(10, None, "king", "club"),     # hit card
            Card(8, None, "8", "diamond"),      # dealer hole
            Card(10, None, "10", "spade"),      # dealer upcard
            Card(6, None, "6", "club"),         # player c2
            Card(10, None, "10", "heart"),      # player c1
        ]
        self.engine.deal_round(bet=100)
        drawn = self.engine.hit(0)
        self.assertEqual(drawn.value, 10)
        self.assertTrue(self.engine.player_hands[0].is_bust)
        self.assertEqual(self.engine.phase, RoundPhase.RESOLUTION)

        results = self.engine.resolve_outcomes()
        self.assertEqual(results[0].outcome, "PLAYER_BUST")
        self.assertEqual(results[0].payout, 0)
        self.assertEqual(self.engine.bankroll, 900)

    def test_double_down(self):
        # Player dealt 11 (5 + 6), doubles down, draws 10 -> 21
        self.engine.shoe = [
            Card(10, None, "king", "spade"),    # double card
            Card(8, None, "8", "diamond"),      # dealer hole
            Card(9, None, "9", "heart"),        # dealer upcard
            Card(6, None, "6", "club"),         # player c2
            Card(5, None, "5", "heart"),        # player c1
        ]
        self.engine.deal_round(bet=50)
        self.assertEqual(self.engine.bankroll, 950)

        card = self.engine.double_down(0)
        self.assertEqual(card.value, 10)
        self.assertEqual(self.engine.player_hands[0].score, 21)
        self.assertEqual(self.engine.player_hands[0].bet, 100)
        self.assertEqual(self.engine.bankroll, 900)
        self.assertTrue(self.engine.player_hands[0].is_doubled)
        self.assertTrue(self.engine.player_hands[0].is_stood)
        self.assertEqual(self.engine.phase, RoundPhase.DEALER_TURN)

    def test_split_pair(self):
        # Player dealt pair of 8s, splits into two hands
        self.engine.shoe = [
            Card(10, None, "10", "club"),       # hand 2 card 2 -> 18
            Card(9, None, "9", "diamond"),      # hand 1 card 2 -> 17
            Card(8, None, "8", "spade"),        # dealer hole
            Card(7, None, "7", "heart"),        # dealer upcard
            Card(8, None, "8", "club"),         # player c2
            Card(8, None, "8", "heart"),        # player c1
        ]
        self.engine.deal_round(bet=100)
        self.assertEqual(self.engine.bankroll, 900)

        h1, h2 = self.engine.split(0)
        self.assertEqual(len(self.engine.player_hands), 2)
        self.assertEqual(self.engine.bankroll, 800)
        self.assertEqual(h1.bet, 100)
        self.assertEqual(h2.bet, 100)
        self.assertEqual(h1.score, 17)
        self.assertEqual(h2.score, 18)

        # Stand hand 1, then stand hand 2
        self.engine.stand(0)
        self.assertEqual(self.engine.active_hand_index, 1)
        self.engine.stand(1)
        self.assertEqual(self.engine.phase, RoundPhase.DEALER_TURN)

    def test_late_surrender(self):
        # Player dealt 16 vs dealer 10, chooses late surrender
        self.engine.shoe = [
            Card(8, None, "8", "diamond"),
            Card(10, None, "10", "spade"),
            Card(10, None, "10", "heart"),
            Card(6, None, "6", "club"),
        ]
        self.engine.deal_round(bet=100)
        self.engine.surrender(0)
        self.assertEqual(self.engine.phase, RoundPhase.RESOLUTION)

        results = self.engine.resolve_outcomes()
        self.assertEqual(results[0].outcome, "SURRENDER")
        # Surrender recovers half of $100 ($50) -> bankroll 950
        self.assertEqual(results[0].payout, 50)
        self.assertEqual(self.engine.bankroll, 950)

    def test_shoe_reshuffle_event(self):
        self.engine.reshuffle_shoe()
        event_types = [e.event_type for e in self.events]
        self.assertIn(GameEventType.SHOE_RESHUFFLED, event_types)


if __name__ == "__main__":
    unittest.main()
