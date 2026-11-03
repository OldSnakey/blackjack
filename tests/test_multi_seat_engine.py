"""
Unit Test Suite for Headless Multi-Seat Wagering Engine (`game_engine.py`).

Tests clockwise dealing order across active seats, skipping inactive seats,
dealer hole-card reveal and skip on bust/surrender, surrender non-premature exit,
Seat 2 backward compatibility, and canonical bankroll delegation.
"""

from __future__ import annotations

import unittest
from event_bus import EventHub, GameEventType
from game_engine import BlackjackEngine, RoundResult
from rules import Card, Hand, Player, RoundPhase, Seat


class TestMultiSeatEngine(unittest.TestCase):
    """Verifies multi-seat traversal, turn progression, and rules invariants."""

    def setUp(self):
        self.bus = EventHub()
        self.events = []
        for et in GameEventType:
            self.bus.subscribe(et, lambda ev: self.events.append(ev))
        self.engine = BlackjackEngine(bankroll=1000, event_bus=self.bus)

    def test_canonical_bankroll_delegation(self):
        """Asserts mutating engine.bankroll directly synchronizes with engine.player.bankroll."""
        self.assertEqual(self.engine.bankroll, 1000)
        self.assertEqual(self.engine.player.bankroll, 1000)

        self.engine.bankroll = 750
        self.assertEqual(self.engine.bankroll, 750)
        self.assertEqual(self.engine.player.bankroll, 750)

        self.engine.player.bankroll = 1200
        self.assertEqual(self.engine.bankroll, 1200)

    def test_single_seat_backward_compatibility(self):
        """Asserts legacy calls to engine.player_hands and engine.current_bet map to Seat 2."""
        # Rig shoe for single seat legacy deal
        self.engine.shoe = [
            Card(8, None, "8", "diamond"),  # dealer hole
            Card(10, None, "10", "spade"),  # dealer upcard
            Card(9, None, "9", "club"),     # player card 2
            Card(6, None, "6", "heart"),    # player card 1
        ]
        p_hand, d_hand = self.engine.deal_round(bet=100)
        self.assertEqual(self.engine.current_bet, 100)
        self.assertEqual(self.engine.player_hands[0].score, 15)
        self.assertEqual(self.engine.seats[1].main_bet, 100)
        self.assertTrue(self.engine.seats[1].is_active)
        self.assertFalse(self.engine.seats[0].is_active)
        self.assertFalse(self.engine.seats[2].is_active)

    def test_clockwise_dealing_order_active_seats(self):
        """
        Stages bets on Seats 1 and 3 (Seat 2 inactive).
        Asserts dealing sequence deals 2 cards each to Seats 1 and 3 and 2 cards to dealer.
        Asserts inactive Seat 2 receives 0 cards.
        """
        # Seat 1: First Base (Right), Seat 3: Third Base (Left)
        self.engine.stage_bet(1, 50)
        self.engine.stage_bet(3, 25)

        self.assertEqual(self.engine.seats[0].main_bet, 50)
        self.assertTrue(self.engine.seats[0].is_active)
        self.assertFalse(self.engine.seats[1].is_active)
        self.assertEqual(self.engine.seats[2].main_bet, 25)
        self.assertTrue(self.engine.seats[2].is_active)

        # Total staged = 75 deducted from 1000 bankroll -> 925
        self.assertEqual(self.engine.bankroll, 925)

        # Rig shoe for clockwise deal:
        # Round 1: Seat 1 c1, Seat 3 c1, Dealer hole
        # Round 2: Seat 1 c2, Seat 3 c2, Dealer upcard
        # Popped from end of list:
        self.engine.shoe = [
            Card(10, None, "10", "spade"),   # Dealer upcard
            Card(5, None, "5", "club"),      # Seat 3 card 2
            Card(9, None, "9", "diamond"),   # Seat 1 card 2
            Card(7, None, "7", "heart"),     # Dealer hole card
            Card(6, None, "6", "spade"),     # Seat 3 card 1
            Card(10, None, "king", "heart"), # Seat 1 card 1
        ]

        self.engine.deal_round(bet=None)

        # Verify Seat 1 (index 0) received King + 9 = 19
        self.assertEqual(len(self.engine.seats[0].hands[0]), 2)
        self.assertEqual(self.engine.seats[0].hands[0].score, 19)

        # Verify Seat 2 received 0 cards
        self.assertEqual(len(self.engine.seats[1].hands), 0)

        # Verify Seat 3 (index 2) received 6 + 5 = 11
        self.assertEqual(len(self.engine.seats[2].hands[0]), 2)
        self.assertEqual(self.engine.seats[2].hands[0].score, 11)

        # Verify Dealer has upcard (10) and hole card (7)
        self.assertEqual(len(self.engine.dealer_hand), 2)
        self.assertEqual(self.engine.dealer_hand[0].rank, "10")
        self.assertEqual(self.engine.dealer_hand[1].rank, "7")

        # Active seat begins at Seat 1 (First Base)
        self.assertEqual(self.engine.active_seat_index, 1)

    def test_turn_advancement_skips_inactive_seats(self):
        """Completing Seat 1 actions advances directly to Seat 3, skipping inactive Seat 2."""
        self.engine.stage_bet(1, 50)
        self.engine.stage_bet(3, 25)

        self.engine.shoe = [
            Card(8, None, "8", "diamond"),
            Card(5, None, "5", "club"),
            Card(9, None, "9", "diamond"),
            Card(7, None, "7", "heart"),
            Card(6, None, "6", "spade"),
            Card(10, None, "king", "heart"),
        ]
        self.engine.deal_round(bet=None)
        self.assertEqual(self.engine.active_seat_index, 1)

        # Seat 1 stands on 19
        self.engine.stand(1)

        # Should advance directly to Seat 3, skipping Seat 2
        self.assertEqual(self.engine.active_seat_index, 3)

        # Seat 3 stands on 11
        self.engine.stand(3)

        # Turns finished -> dealer turn or resolution
        self.assertIn(self.engine.phase, (RoundPhase.DEALER_TURN, RoundPhase.RESOLUTION))

    def test_all_seats_busted_or_surrendered_dealer_skip(self):
        """When all active seats bust or surrender, dealer reveals hole card and skips draws."""
        self.engine.stage_bet(1, 50)
        self.engine.stage_bet(2, 50)

        # Rig shoe: Seat 1 deals 16, Seat 2 deals 15, Dealer deals 12
        # Then hit cards bust both seats: 10 to Seat 1 (26), 10 to Seat 2 (25)
        self.engine.shoe = [
            Card(10, None, "queen", "diamond"), # Seat 2 hit card (busts)
            Card(10, None, "jack", "club"),     # Seat 1 hit card (busts)
            Card(6, None, "6", "diamond"),      # Dealer upcard
            Card(7, None, "7", "club"),         # Seat 2 c2
            Card(10, None, "10", "spade"),      # Seat 1 c2
            Card(6, None, "6", "heart"),        # Dealer hole card (dealer has 12, would hit if active)
            Card(8, None, "8", "spade"),        # Seat 2 c1
            Card(6, None, "6", "club"),         # Seat 1 c1
        ]
        self.engine.deal_round(bet=None)

        # Hit Seat 1 -> busts
        self.engine.hit(1)
        self.assertTrue(self.engine.seats[0].hands[0].is_bust)
        self.assertEqual(self.engine.active_seat_index, 2)

        # Hit Seat 2 -> busts
        self.engine.hit(2)
        self.assertTrue(self.engine.seats[1].hands[0].is_bust)

        # All active seats have busted: dealer skips hit drawing, reveals hole card, transitions to RESOLUTION
        self.assertTrue(self.engine.all_seats_busted())
        self.assertTrue(self.engine.hole_card_revealed)
        self.assertEqual(len(self.engine.dealer_hand), 2)  # Dealer never drew 3rd card!
        self.assertEqual(self.engine.phase, RoundPhase.RESOLUTION)

    def test_surrender_does_not_prematurely_terminate_other_seats(self):
        """Surrendering Seat 1 refunds 50% and advances to Seat 2 with dealer hole card face down."""
        self.engine.stage_bet(1, 50)
        self.engine.stage_bet(2, 50)
        # 1000 - 100 = 900
        self.assertEqual(self.engine.bankroll, 900)

        self.engine.shoe = [
            Card(10, None, "10", "diamond"),
            Card(10, None, "king", "club"),
            Card(6, None, "6", "heart"),
            Card(7, None, "7", "spade"),
            Card(9, None, "9", "diamond"),
            Card(10, None, "jack", "heart"),
        ]
        self.engine.deal_round(bet=None)

        self.assertEqual(self.engine.active_seat_index, 1)
        self.assertFalse(self.engine.hole_card_revealed)

        # Seat 1 surrenders: refunds 50% ($25)
        self.engine.surrender(1)
        self.assertEqual(self.engine.bankroll, 925)
        self.assertTrue(self.engine.seats[0].hands[0].is_surrendered)

        # Hole card should still be face down because Seat 2 is still active!
        self.assertFalse(self.engine.hole_card_revealed)
        self.assertEqual(self.engine.active_seat_index, 2)
        self.assertEqual(self.engine.phase, RoundPhase.PLAYER_TURN)

    def test_get_seat_null_safety_and_inactive_properties(self):
        """
        Asserts get_seat(None) and out-of-range indexes return None safely without TypeError.
        Asserts player_hands and current_bet properties do not raise when active_seat_index is None.
        """
        self.assertIsNone(self.engine.get_seat(None))
        self.assertIsNone(self.engine.get_seat(0))
        self.assertIsNone(self.engine.get_seat(4))

        # Explicitly set active_seat_index to None as happens in new_game()
        self.engine.active_seat_index = None
        self.assertIsNone(self.engine.get_seat(self.engine.active_seat_index))

        # Querying player_hands and current_bet should fall back gracefully and not raise
        hands = self.engine.player_hands
        self.assertIsInstance(hands, list)

        bet = self.engine.current_bet
        self.assertIsInstance(bet, int)

        # advance_turn() should return (None, None) gracefully without TypeError
        next_seat, next_hand = self.engine.advance_turn()
        self.assertIsNone(next_seat)
        self.assertIsNone(next_hand)

    def test_stage_bet_safe_with_none_or_out_of_bounds_seat(self):
        """
        Asserts stage_bet with None or invalid seat index falls back gracefully
        or returns 0 without raising AttributeError: 'NoneType' object has no attribute 'main_bet'.
        """
        initial_bankroll = self.engine.bankroll
        # Passing None as seat should fall back to seat 2 (Center) safely
        bet = self.engine.stage_bet(None, 50)
        self.assertEqual(bet, 50)
        self.assertEqual(self.engine.get_seat(2).main_bet, 50)
        self.assertEqual(self.engine.bankroll, initial_bankroll - 50)

        # Passing an invalid out-of-bounds seat index should safely return 0 without raising
        bet_invalid = self.engine.stage_bet(99, 50)
        self.assertEqual(bet_invalid, 0)


if __name__ == "__main__":
    unittest.main()

