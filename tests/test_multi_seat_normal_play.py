"""
Headless Integration Tests: Multi-Seat Normal Play Scenarios

Systematically validates end-to-end multi-seat game flows, preventing regressions
across turn progression, player decisions, dealer interactions, bankroll payouts,
and round lifecycle resets.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile
import tkinter as tk
import unittest

from blackjack import BlackjackApp, RoundPhase
from rules import Card, BLACKJACK_TARGET
from save_manager import SaveManager


class TestMultiSeatNormalPlayIntegration(unittest.TestCase):
    """Rigorous end-to-end integration tests for 3-seat multi-seat table play."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.save_mgr = SaveManager(save_path=Path(self.temp_dir) / "test_save.json")

        self.root = tk.Tk()
        self.root.withdraw()

        self.app = BlackjackApp(self.root, chips_mode=True, sound_enabled=False)
        self.app.save_manager = self.save_mgr
        self.app.set_table_seats(3)
        self.root.update_idletasks()

    def tearDown(self):
        if hasattr(self, "app"):
            if getattr(self.app, "_dealer_timer_id", None):
                try:
                    self.root.after_cancel(self.app._dealer_timer_id)
                except Exception:
                    pass
                self.app._dealer_timer_id = None
            if getattr(self.app, "_haunted_round_timer_id", None):
                try:
                    self.root.after_cancel(self.app._haunted_round_timer_id)
                except Exception:
                    pass
                self.app._haunted_round_timer_id = None
            try:
                self.app._on_close()
            except Exception:
                pass
        try:
            self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # Scenario 1: Full 3-Seat Standard Round (Hit / Stand / Dealer / Settlement)
    # ------------------------------------------------------------------------
    def test_full_round_hit_stand_dealer_settlement(self):
        """
        Validates clockwise turn progression across 3 active seats:
        Seat 1 (15 -> Hit 19 -> Stand), Seat 2 (11 -> Hit 20 -> Stand), Seat 3 (16 -> Stand).
        Dealer starts at 16, draws to 19.
        Outcomes: Seat 1 Push (returns $25), Seat 2 Win 1:1 (+$50), Seat 3 Loss (-$100).
        Net table profit: -$25.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage bets: S1=$25, S2=$50, S3=$100
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 3
        self.app._on_felt_chip_click(100)
        self.root.update_idletasks()

        self.assertEqual(self.app.bankroll_var.get(), 825)

        # Rig deck so:
        # Pass 1: S1 gets 10, S2 gets 10, S3 gets 10, Dealer upcard gets 10
        # Pass 2: S1 gets 5 (15), S2 gets 1 (Ace: 11), S3 gets 6 (16), Dealer hole gets 6 (16)
        # Next draws:
        # S1 hits: draws 4 -> 19 (stands)
        # S2 hits: draws 9 -> 20 (stands)
        # S3 stands at 16
        # Dealer draws 3 -> 19 (stands)
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_5s = [c for c in self.app.all_cards if c.value == 5]
        c_4s = [c for c in self.app.all_cards if c.value == 4]
        c_3s = [c for c in self.app.all_cards if c.value == 3]
        c_2s = [c for c in self.app.all_cards if c.value == 2]

        self.app.deck = [
            c_3s[0],   # Dealer draw (16 + 3 = 19)
            c_9s[0],   # S2 hit (11 + 9 = 20)
            c_4s[0],   # S1 hit (15 + 4 = 19)
            c_6s[0],   # Dealer hole card (6) -> 10 + 6 = 16
            c_6s[1],   # S3 c2 (6) -> 10 + 6 = 16
            c_9s[1],   # S2 c2 (9) -> 2 + 9 = 11
            c_5s[0],   # S1 c2 (5) -> 10 + 5 = 15
            c_10s[0],  # Dealer upcard (10)
            c_10s[1],  # S3 c1 (10)
            c_2s[0],   # S2 c1 (2)
            c_10s[2],  # S1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Turn starts at Seat 1
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.seats[0].hands[0].score, 15)

        # Seat 1 hits -> draws 4 -> score 19
        self.app.on_hit()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.seats[0].hands[0].score, 19)
        self.assertEqual(self.app.engine.active_seat_index, 1)

        # Seat 1 stands -> advances to Seat 2
        self.app.on_stand()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 2)
        self.assertEqual(self.app.engine.seats[1].hands[0].score, 11)

        # Seat 2 hits -> draws 9 -> score 20
        self.app.on_hit()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.seats[1].hands[0].score, 20)
        self.assertEqual(self.app.engine.active_seat_index, 2)

        # Seat 2 stands -> advances to Seat 3
        self.app.on_stand()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 3)
        self.assertEqual(self.app.engine.seats[2].hands[0].score, 16)

        # Seat 3 stands -> advances to Dealer Turn
        self.app.on_stand()
        self.root.update_idletasks()
        self.assertEqual(self.app.round_phase, RoundPhase.DEALER_TURN)

        # Execute dealer step: draws 3 -> 19, then stands -> concludes
        while self.app.round_phase == RoundPhase.DEALER_TURN:
            if self.app._dealer_timer_id:
                self.root.after_cancel(self.app._dealer_timer_id)
                self.app._dealer_timer_id = None
            self.app._dealer_step()
            self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        self.assertEqual(self.app.dealer_score_var.get(), "19")

        # Bankroll settlement:
        # Initial: $1000 - $175 (bets) = $825
        # Seat 1 (19 vs 19): Push -> +$25
        # Seat 2 (20 vs 19): Win 1:1 -> +$100 (staked $50 returned + $50 profit)
        # Seat 3 (16 vs 19): Loss -> +$0 (lost $100)
        # Final bankroll: 825 + 25 + 100 = $950
        self.assertEqual(self.app.bankroll_var.get(), 950)

        # Verify two-tier summary
        summary = self.app.result_var.get()
        self.assertIn("\n", summary)
        tier1, tier2 = summary.split("\n", 1)
        self.assertIn("Total Loss: -$50", tier1)
        self.assertIn("Seat 1: Push", tier2)
        self.assertIn("Seat 2: Win", tier2)
        self.assertIn("Seat 3: Loss", tier2)
        self.assertEqual(self.app.new_game_button.cget("state"), "normal")

    # ------------------------------------------------------------------------
    # Scenario 2: Double Down Progression & Bankroll
    # ------------------------------------------------------------------------
    def test_double_down_progression_and_bankroll(self):
        """
        Validates Double Down in multi-seat:
        Seat 1 holds 11 (5+6) with $50 bet. Doubles down:
        - Additional $50 deducted from bankroll.
        - Seat 1 bet becomes $100.
        - Deals exactly 1 card, then automatically stands and advances to Seat 2.
        - On round conclusion, doubled bet awards correct 2x win payout ($200 returned).
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage $50 on Seat 1 and $50 on Seat 2
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(50)
        self.root.update_idletasks()

        self.assertEqual(self.app.bankroll_var.get(), 900)

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_5s = [c for c in self.app.all_cards if c.value == 5]

        # Deal order (2 active seats: S1, S2):
        # Round 1: S1 c1 (5), S2 c1 (10), Dealer upcard (8)
        # Round 2: S1 c2 (6) [score 11], S2 c2 (9) [score 19], Dealer hole (9) [score 17]
        # Double draw on S1: draws 9 -> score 20
        self.app.deck = [
            c_9s[0],   # S1 Double draw (11 + 9 = 20)
            c_9s[1],   # Dealer hole card (9) -> 8 + 9 = 17
            c_9s[2],   # S2 c2 (9) -> 10 + 9 = 19
            c_6s[0],   # S1 c2 (6) -> 5 + 6 = 11
            c_8s[0],   # Dealer upcard (8)
            c_10s[0],  # S2 c1 (10)
            c_5s[0],   # S1 c1 (5)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.double_button.cget("state"), "normal")

        # Double down on Seat 1
        self.app.on_double_down()
        self.root.update_idletasks()

        # Bankroll should have deducted another $50 (900 - 50 = 850)
        self.assertEqual(self.app.bankroll_var.get(), 850)
        s1 = self.app.engine.seats[0]
        self.assertEqual(s1.hands[0].bet, 100)
        self.assertEqual(len(s1.hands[0]), 3)
        self.assertEqual(s1.hands[0].score, 20)

        # Turn must have advanced automatically to Seat 2!
        self.assertEqual(self.app.engine.active_seat_index, 2)
        self.assertEqual(self.app.stand_button.cget("state"), "normal")

        # Seat 2 stands -> dealer stands at 17
        self.app.on_stand()
        self.root.update_idletasks()

        while self.app.round_phase == RoundPhase.DEALER_TURN:
            if self.app._dealer_timer_id:
                self.root.after_cancel(self.app._dealer_timer_id)
                self.app._dealer_timer_id = None
            self.app._dealer_step()
            self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)

        # Settlement:
        # S1 (20 vs 17): Win on doubled $100 bet -> returns $200 (profit +$100)
        # S2 (19 vs 17): Win on $50 bet -> returns $100 (profit +$50)
        # Bankroll: 850 + 200 + 100 = 1150 (initial 1000 + 150 net profit)
        self.assertEqual(self.app.bankroll_var.get(), 1150)
        summary = self.app.result_var.get()
        self.assertIn("Total Won: +$150", summary)

    # ------------------------------------------------------------------------
    # Scenario 3: Double Down Blocked on Insufficient Bankroll
    # ------------------------------------------------------------------------
    def test_double_down_insufficient_bankroll_blocked(self):
        """
        Verifies that when bankroll is lower than active hand's bet,
        Double Down is disabled and clicking it rejects without altering bet.
        """
        self.app.bankroll_var.set(70)
        self.app.engine.bankroll = 70

        # Stage $50 on Seat 1 -> remaining bankroll is $20
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.root.update_idletasks()
        self.assertEqual(self.app.bankroll_var.get(), 20)

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_5s = [c for c in self.app.all_cards if c.value == 5]
        c_7s = [c for c in self.app.all_cards if c.value == 7]

        self.app.deck = [
            c_7s[0],   # Dealer hole
            c_6s[0],   # S1 c2 (6) -> 11
            c_10s[0],  # Dealer upcard
            c_5s[0],   # S1 c1 (5)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Seat 1 has 11 with $50 bet, but bankroll is only $20
        self.assertEqual(self.app.double_button.cget("state"), "disabled")

        # Directly invoking on_double_down should reject cleanly
        self.app.on_double_down()
        self.root.update_idletasks()

        self.assertEqual(self.app.bankroll_var.get(), 20)
        self.assertEqual(self.app.engine.seats[0].hands[0].bet, 50)
        self.assertEqual(len(self.app.engine.seats[0].hands[0]), 2)
        self.assertEqual(self.app.engine.active_seat_index, 1)

    # ------------------------------------------------------------------------
    # Scenario 4: Split Multi-Hand Progression Across Seats
    # ------------------------------------------------------------------------
    def test_split_pair_full_play_both_hands_and_advance(self):
        """
        Verifies that splitting a pair creates 2 independent sub-hands:
        - Hand 1 hits and stands.
        - Hand 2 hits and stands.
        - Turn advances to Seat 2, which plays and stands.
        - All 3 player hands are independently evaluated against the dealer.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage $25 on Seat 1 and $25 on Seat 2
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(25)
        self.root.update_idletasks()

        self.assertEqual(self.app.bankroll_var.get(), 950)

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_7s = [c for c in self.app.all_cards if c.value == 7]

        # Deal order (2 active seats: S1, S2):
        # Round 1: S1 c1 (8), S2 c1 (10), Dealer upcard (8)
        # Round 2: S1 c2 (8) [Pair of 8s], S2 c2 (10) [20], Dealer hole (9) [17]
        # When Split triggered on S1:
        # S1 H1 deal card: 10 -> score 18
        # S1 H2 deal card: 9 -> score 17
        self.app.deck = [
            c_9s[0],   # S1 H2 card on split (8 + 9 = 17)
            c_10s[0],  # S1 H1 card on split (8 + 10 = 18)
            c_9s[1],   # Dealer hole card (9) -> 8 + 9 = 17
            c_10s[1],  # S2 c2 (10) -> 20
            c_8s[0],   # S1 c2 (8) -> pair of 8s
            c_8s[1],   # Dealer upcard (8)
            c_10s[2],  # S2 c1 (10)
            c_8s[2],   # S1 c1 (8)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.split_button.cget("state"), "normal")

        # Split on Seat 1
        self.app.on_split()
        self.root.update_idletasks()

        # Matching bet $25 deducted (950 - 25 = 925)
        self.assertEqual(self.app.bankroll_var.get(), 925)
        s1 = self.app.engine.seats[0]
        self.assertEqual(len(s1.hands), 2)
        self.assertEqual(s1.hands[0].bet, 25)
        self.assertEqual(s1.hands[1].bet, 25)

        # Turn focus should be on Hand 1 (score 18)
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.active_hand_index, 0)
        self.assertEqual(s1.hands[0].score, 18)

        # Stand on Hand 1 -> advances to Hand 2
        self.app.on_stand()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.active_hand_index, 1)
        self.assertEqual(s1.hands[1].score, 17)

        # Stand on Hand 2 -> advances to Seat 2
        self.app.on_stand()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 2)
        self.assertEqual(self.app.engine.active_hand_index, 0)
        self.assertEqual(self.app.engine.seats[1].hands[0].score, 20)

        # Stand on Seat 2 -> dealer finishes at 17
        self.app.on_stand()
        self.root.update_idletasks()

        while self.app.round_phase == RoundPhase.DEALER_TURN:
            if self.app._dealer_timer_id:
                self.root.after_cancel(self.app._dealer_timer_id)
                self.app._dealer_timer_id = None
            self.app._dealer_step()
            self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)

        # Settlement:
        # S1 H1 (18 vs 17): Win -> pays $50 (+$25 profit)
        # S1 H2 (17 vs 17): Push -> returns $25 ($0 profit)
        # S2 (20 vs 17): Win -> pays $50 (+$25 profit)
        # Total profit: +$50. Bankroll: 925 + 50 + 25 + 50 = 1050
        self.assertEqual(self.app.bankroll_var.get(), 1050)

        summary = self.app.result_var.get()
        self.assertIn("Seat 1 (H1): Win", summary)
        self.assertIn("Seat 1 (H2): Push", summary)
        self.assertIn("Seat 2: Win", summary)

    # ------------------------------------------------------------------------
    # Scenario 5: Surrender Individual Hand and Turn Advancement
    # ------------------------------------------------------------------------
    def test_surrender_individual_and_turn_advance(self):
        """
        Verifies Late Surrender in multi-seat:
        - Seat 1 surrenders: 50% refunded immediately, advances to Seat 2.
        - Seat 2 plays normally and stands.
        - Seat 3 surrenders: 50% refunded, advances to Dealer.
        - Dealer resolves against Seat 2 only; Seat 1 & 3 recorded as Surrendered.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage $50 on Seats 1, 2, 3
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 3
        self.app._on_felt_chip_click(50)
        self.root.update_idletasks()

        self.assertEqual(self.app.bankroll_var.get(), 850)

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_5s = [c for c in self.app.all_cards if c.value == 5]

        # Deal order (3 active seats: S1, S2, S3):
        # Round 1: S1 c1 (10), S2 c1 (10), S3 c1 (10), Dealer upcard (10)
        # Round 2: S1 c2 (6) [16], S2 c2 (10) [20], S3 c2 (5) [15], Dealer hole (8) [18]
        self.app.deck = [
            c_8s[0],   # Dealer hole card (8) -> 10 + 8 = 18
            c_5s[0],   # S3 c2 (5) -> 10 + 5 = 15
            c_10s[0],  # S2 c2 (10) -> 20
            c_6s[0],   # S1 c2 (6) -> 16
            c_10s[1],  # Dealer upcard (10)
            c_10s[2],  # S3 c1 (10)
            c_10s[3],  # S2 c1 (10)
            c_10s[4],  # S1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Seat 1 active (16 vs 10). Surrenders!
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.app.on_surrender()
        self.root.update_idletasks()

        # $25 refunded immediately (850 + 25 = 875)
        self.assertEqual(self.app.bankroll_var.get(), 875)
        self.assertTrue(self.app.engine.seats[0].hands[0].is_surrendered)

        # Turn advanced to Seat 2!
        self.assertEqual(self.app.engine.active_seat_index, 2)
        # Seat 2 stands at 20
        self.app.on_stand()
        self.root.update_idletasks()

        # Turn advanced to Seat 3 (15 vs 10). Surrenders!
        self.assertEqual(self.app.engine.active_seat_index, 3)
        self.app.on_surrender()
        self.root.update_idletasks()

        # $25 refunded immediately (875 + 25 = 900)
        self.assertEqual(self.app.bankroll_var.get(), 900)
        self.assertTrue(self.app.engine.seats[2].hands[0].is_surrendered)

        # Dealer finishes at 18
        while self.app.round_phase == RoundPhase.DEALER_TURN:
            if self.app._dealer_timer_id:
                self.root.after_cancel(self.app._dealer_timer_id)
                self.app._dealer_timer_id = None
            self.app._dealer_step()
            self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)

        # Settlement:
        # S1: Surrendered (-$25)
        # S2 (20 vs 18): Win -> pays $100 (+$50 profit)
        # S3: Surrendered (-$25)
        # Net profit: -25 + 50 - 25 = $0
        # Final bankroll: 900 + 100 = 1000
        self.assertEqual(self.app.bankroll_var.get(), 1000)

        summary = self.app.result_var.get()
        self.assertIn("Seat 1: Surrendered", summary)
        self.assertIn("Seat 2: Win", summary)
        self.assertIn("Seat 3: Surrendered", summary)

    # ------------------------------------------------------------------------
    # Scenario 6: All Active Seats Surrender Concludes Immediately
    # ------------------------------------------------------------------------
    def test_all_active_seats_surrender_immediate_conclusion(self):
        """
        Verifies that when every active seat surrenders:
        - Dealer does NOT draw any cards.
        - Hole card is revealed immediately.
        - Round concludes directly with new_game_button enabled.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage $50 on Seat 1 and $50 on Seat 2
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(50)
        self.root.update_idletasks()

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_5s = [c for c in self.app.all_cards if c.value == 5]
        c_4s = [c for c in self.app.all_cards if c.value == 4]

        self.app.deck = [
            c_4s[0],   # Dealer hole card (4)
            c_5s[0],   # S2 c2 (5) -> 15
            c_6s[0],   # S1 c2 (6) -> 16
            c_10s[0],  # Dealer upcard (10)
            c_10s[1],  # S2 c1 (10)
            c_10s[2],  # S1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # S1 surrenders -> advances to S2
        self.app.on_surrender()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 2)

        # S2 surrenders -> all seats surrendered!
        self.app.on_surrender()
        self.root.update_idletasks()

        # Immediate conclusion
        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        self.assertIsNone(self.app._dealer_timer_id)
        self.assertEqual(self.app.new_game_button.cget("state"), "normal")
        self.assertEqual(len(self.app.dealer_hand), 2)  # Dealer did not draw extra cards

    # ------------------------------------------------------------------------
    # Scenario 7: Discontinuous Active Seats (e.g. Seats 1 & 3 Active, Seat 2 Empty)
    # ------------------------------------------------------------------------
    def test_discontinuous_seats_skips_inactive(self):
        """
        Verifies that when Seat 1 and Seat 3 are active and Seat 2 has $0:
        - Only Seat 1 and Seat 3 are dealt cards; Seat 2 receives 0 cards.
        - Turn order progresses from Seat 1 directly to Seat 3, cleanly skipping Seat 2.
        - Settlement displays results for Seat 1 and Seat 3 only.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage $50 on Seat 1 and $50 on Seat 3 (Seat 2 left empty)
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 3
        self.app._on_felt_chip_click(50)
        self.root.update_idletasks()

        self.assertTrue(self.app.engine.seats[0].is_active)
        self.assertFalse(self.app.engine.seats[1].is_active)
        self.assertTrue(self.app.engine.seats[2].is_active)

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_8s = [c for c in self.app.all_cards if c.value == 8]

        # Deal order (active seats: S1, S3):
        # Pass 1: S1 c1 (10), S3 c1 (10), Dealer upcard (8)
        # Pass 2: S1 c2 (10) [20], S3 c2 (9) [19], Dealer hole (9) [17]
        self.app.deck = [
            c_9s[0],   # Dealer hole card (9) -> 8 + 9 = 17
            c_9s[1],   # S3 c2 (9) -> 19
            c_10s[0],  # S1 c2 (10) -> 20
            c_8s[0],   # Dealer upcard (8)
            c_10s[1],  # S3 c1 (10)
            c_10s[2],  # S1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Seat 2 received no cards
        self.assertEqual(len(self.app.engine.seats[1].hands[0]), 0)

        # Turn starts at Seat 1
        self.assertEqual(self.app.engine.active_seat_index, 1)

        # Seat 1 stands -> skips Seat 2 directly to Seat 3!
        self.app.on_stand()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 3)

        # Seat 3 stands -> dealer turn
        self.app.on_stand()
        self.root.update_idletasks()

        while self.app.round_phase == RoundPhase.DEALER_TURN:
            if self.app._dealer_timer_id:
                self.root.after_cancel(self.app._dealer_timer_id)
                self.app._dealer_timer_id = None
            self.app._dealer_step()
            self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        summary = self.app.result_var.get()
        self.assertIn("Seat 1: Win", summary)
        self.assertIn("Seat 3: Win", summary)
        self.assertNotIn("Seat 2", summary)

    # ------------------------------------------------------------------------
    # Scenario 8: Deal-Time Natural Blackjack Auto-Advancement
    # ------------------------------------------------------------------------
    def test_natural_blackjack_on_deal_auto_advances(self):
        """
        Verifies that when Seat 1 receives a Natural Blackjack (21 on 2 cards):
        - Seat 1 is marked stood automatically.
        - Turn immediately begins at Seat 2.
        - Seat 1 receives 3:2 payout on settlement.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage $50 on Seat 1 and $50 on Seat 2
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(50)
        self.root.update_idletasks()

        c_aces = [c for c in self.app.all_cards if c.rank == "ace"]
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_7s = [c for c in self.app.all_cards if c.value == 7]

        # S1 gets Ace + 10 (Natural BJ)
        # S2 gets 10 + 9 (19)
        # Dealer gets 7 + 10 (17)
        self.app.deck = [
            c_10s[0],  # Dealer hole card (10) -> 7 + 10 = 17
            c_9s[0],   # S2 c2 (9) -> 19
            c_aces[0], # S1 c2 (Ace: 11) -> 10 + 11 = 21 (Natural Blackjack!)
            c_7s[0],   # Dealer upcard (7)
            c_10s[1],  # S2 c1 (10)
            c_10s[2],  # S1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Turn must have started directly at Seat 2 because Seat 1 auto-stood!
        self.assertEqual(self.app.engine.active_seat_index, 2)
        self.assertTrue(self.app.engine.seats[0].hands[0].is_stood)

        # Seat 2 stands
        self.app.on_stand()
        self.root.update_idletasks()

        while self.app.round_phase == RoundPhase.DEALER_TURN:
            if self.app._dealer_timer_id:
                self.root.after_cancel(self.app._dealer_timer_id)
                self.app._dealer_timer_id = None
            self.app._dealer_step()
            self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)

        # Settlement:
        # S1 Natural Blackjack: $50 bet pays 3:2 -> $125 returned (+$75 profit)
        # S2 Win: $50 bet pays 1:1 -> $100 returned (+$50 profit)
        # Bankroll: 900 + 125 + 100 = 1125
        self.assertEqual(self.app.bankroll_var.get(), 1125)
        summary = self.app.result_var.get()
        self.assertIn("Seat 1: Blackjack!", summary)
        self.assertIn("Seat 2: Win", summary)

    # ------------------------------------------------------------------------
    # Scenario 9: Full Round Lifecycle and New Game Reset
    # ------------------------------------------------------------------------
    def test_new_game_reset_lifecycle_multi_seat(self):
        """
        Verifies that concluding a round and starting a new game:
        - Clears all hand cards across seats and table canvas sprites.
        - Resets engine.active_seat_index to None.
        - Restores player title to 'Player' and erases turn halos.
        - Re-enters Betting Phase with action buttons disabled.
        """
        # Run a quick round to conclusion
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(25)
        self.root.update_idletasks()

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        self.app.deck = [
            c_10s[0], c_10s[1], c_10s[2], c_10s[3]
        ]
        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        self.app.on_stand()
        self.root.update_idletasks()
        if self.app._dealer_timer_id:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
        self.app._conclude_round()
        self.root.update_idletasks()
        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)

        # Start fresh round via new_game()
        self.app.new_game()
        self.root.update_idletasks()

        # Engine state reset
        self.assertEqual(self.app.round_phase, RoundPhase.BETTING)
        self.assertTrue(self.app.is_betting_phase)
        self.assertIsNone(self.app.engine.active_seat_index)
        self.assertEqual(self.app.engine.active_hand_index, 0)
        for s in self.app.engine.seats:
            self.assertEqual(len(s.hands[0]), 0)

        # UI state reset
        self.assertEqual(self.app.player_title_label.cget("text"), "Player")
        self.assertEqual(self.app.hit_button.cget("state"), "disabled")
        self.assertEqual(self.app.stand_button.cget("state"), "disabled")
        self.assertEqual(self.app.new_game_button.cget("state"), "disabled")

        # Table canvas clean
        card_sprites = self.app.card_table_frame.find_withtag("card_sprite")
        self.assertEqual(len(card_sprites), 0)

    # ------------------------------------------------------------------------
    # Scenario 10: Keyboard Action Routing to Active Seat
    # ------------------------------------------------------------------------
    def test_keyboard_shortcuts_route_to_active_seat(self):
        """
        Verifies that keyboard action shortcuts ('H', 'S') dispatch
        correctly to the currently active seat in multi-seat play.
        """
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(25)
        self.root.update_idletasks()

        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_5s = [c for c in self.app.all_cards if c.value == 5]
        c_4s = [c for c in self.app.all_cards if c.value == 4]
        c_3s = [c for c in self.app.all_cards if c.value == 3]

        self.app.deck = [
            c_3s[0],   # S2 hit card
            c_4s[0],   # S1 hit card
            c_10s[0],  # Dealer hole
            c_6s[0],   # S2 c2 (6) -> 16
            c_5s[0],   # S1 c2 (5) -> 15
            c_10s[1],  # Dealer up
            c_10s[2],  # S2 c1 (10)
            c_10s[3],  # S1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Turn starts at Seat 1
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(len(self.app.engine.seats[0].hands[0]), 2)

        # Trigger 'H' shortcut via _on_key_action
        self.app._on_key_action(self.app.on_hit, self.app.hit_button)
        self.root.update_idletasks()

        # Seat 1 should have received the hit card
        self.assertEqual(len(self.app.engine.seats[0].hands[0]), 3)
        self.assertEqual(self.app.engine.seats[0].hands[0].score, 19)

        # Trigger 'S' shortcut to stand Seat 1
        self.app._on_key_action(self.app.on_stand, self.app.stand_button)
        self.root.update_idletasks()

        # Turn must have advanced to Seat 2!
        self.assertEqual(self.app.engine.active_seat_index, 2)
        self.assertEqual(len(self.app.engine.seats[1].hands[0]), 2)

        # Trigger 'H' shortcut on Seat 2
        self.app._on_key_action(self.app.on_hit, self.app.hit_button)
        self.root.update_idletasks()

        # Seat 2 should have received the hit card
        self.assertEqual(len(self.app.engine.seats[1].hands[0]), 3)
        self.assertEqual(self.app.engine.seats[1].hands[0].score, 19)

    # ------------------------------------------------------------------------
    # Scenario 11: Multi-Seat Side Bets Lifecycle (Perfect Pairs & 21+3)
    # ------------------------------------------------------------------------
    def test_side_bets_lifecycle_in_multi_seat(self):
        """
        Verifies that side bets placed across multiple seats:
        - Are evaluated and paid on initial deal.
        - Are completely cleared upon new_game() without carrying over into subsequent hands.
        """
        self.app.bankroll_var.set(1000)
        self.app.engine.bankroll = 1000

        # Stage main bet on Seat 1 ($50) and side bets ($10 Perfect Pairs, $10 21+3)
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app._on_table_spot_click(1, "perfect_pairs")
        self.app._on_table_spot_click(1, "21_plus_3")
        self.root.update_idletasks()

        s1 = self.app.engine.seats[0]
        self.assertEqual(s1.main_bet, 50)
        self.assertEqual(s1.side_bets["perfect_pairs"], self.app.selected_denomination)
        self.assertEqual(s1.side_bets["21_plus_3"], self.app.selected_denomination)

        # Deal hand: side bets resolve immediately on deal
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        self.app.deck = [
            c_10s[0], c_10s[1], c_10s[2], c_10s[3]
        ]
        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Conclude round
        self.app.on_stand()
        self.root.update_idletasks()
        if self.app._dealer_timer_id:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
        self.app._conclude_round()
        self.root.update_idletasks()

        # Start fresh round
        self.app.new_game()
        self.root.update_idletasks()

        # Side bets must be zeroed for fresh round
        for s in self.app.engine.seats:
            self.assertEqual(s.side_bets.get("perfect_pairs", 0), 0)
            self.assertEqual(s.side_bets.get("21_plus_3", 0), 0)

    # ------------------------------------------------------------------------
    # Scenario 12: Haunted Mode Strictly Disabled in Multi-Seat Play
    # ------------------------------------------------------------------------
    def test_haunted_mode_strictly_disabled_in_multi_seat(self):
        """
        Verifies that Haunted Halloween and Hell's Table cannot be activated in multi-seat mode:
        1. Advancing rounds in 3-seat mode does not advance haunted phase (remains Phase.NORMAL).
        2. Altar and accessories canvas remain unmapped.
        3. Cursed stakes button is hidden and clicking it does not enter Hell's Table.
        4. Invoking _trigger_hell_table directly is blocked when table_seats == 3.
        5. Round losses in multi-seat mode do not snuff candles or schedule Hell's Table.
        """
        from haunted_manager import Phase

        self.assertEqual(self.app.table_seats, 3)

        # 1. Advance 15 hands via new_game()
        for _ in range(15):
            self.app.new_game()
            self.root.update_idletasks()
            self.assertEqual(self.app.haunted.phase, Phase.NORMAL)

        # Altar must not be packed
        if hasattr(self.app, "haunted_altar"):
            self.assertEqual(self.app.haunted_altar.winfo_manager(), "")

        # 2. Cursed stakes button must be hidden
        if hasattr(self.app, "cursed_stakes_button"):
            self.assertFalse(bool(self.app.cursed_stakes_button.grid_info()))

        # 3. Invoking manual toggles must be blocked
        self.app._on_toggle_cursed_stakes()
        self.root.update_idletasks()
        self.assertEqual(self.app.haunted.phase, Phase.NORMAL)

        self.app._trigger_hell_table()
        self.root.update_idletasks()
        self.assertEqual(self.app.haunted.phase, Phase.NORMAL)

        # Soul meter must remain hidden
        if hasattr(self.app, "soul_meter_canvas"):
            self.assertFalse(bool(self.app.soul_meter_canvas.grid_info()))

    # ------------------------------------------------------------------------
    # Scenario 13: All-In Stages Full Remaining Bankroll on Active Betting Seat
    # ------------------------------------------------------------------------
    def test_all_in_stages_full_bankroll_on_default_active_seat(self):
        """
        Verifies that in 3-seat mode, clicking 'All In' without prior seat selection
        stages the full bankroll on the default active seat (Seat 2 / Center)
        without throwing an AttributeError: 'NoneType' object has no attribute 'main_bet'.
        """
        initial_bankroll = self.app.bankroll_var.get()
        self.assertGreaterEqual(initial_bankroll, 100)
        self.assertEqual(self.app.focused_betting_seat, 2)

        # Trigger All In
        self.app._all_in()
        self.root.update_idletasks()

        # Seat 2 must hold entire bankroll, remaining bankroll must be 0
        seat2 = self.app.engine.get_seat(2)
        self.assertEqual(seat2.main_bet, initial_bankroll)
        self.assertTrue(seat2.is_active)
        self.assertEqual(self.app.engine.get_seat(1).main_bet, 0)
        self.assertEqual(self.app.engine.get_seat(3).main_bet, 0)
        self.assertEqual(self.app.engine.bankroll, 0)
        self.assertEqual(self.app.bankroll_var.get(), 0)
        self.assertEqual(self.app.current_bet_var.get(), initial_bankroll)

        # All-in button must now be disabled
        if hasattr(self.app, "all_in_button"):
            self.assertEqual(str(self.app.all_in_button.cget("state")), "disabled")

    def test_all_in_stages_on_explicitly_focused_seat(self):
        """
        Verifies that clicking 'All In' when Seat 1 or Seat 3 is focused stages
        all remaining bankroll directly onto that active seat.
        """
        # Focus Seat 1
        self.app._on_table_spot_click(1, None)
        self.root.update_idletasks()
        self.assertEqual(self.app.focused_betting_seat, 1)

        initial_bankroll = self.app.bankroll_var.get()
        self.app._all_in()
        self.root.update_idletasks()

        seat1 = self.app.engine.get_seat(1)
        self.assertEqual(seat1.main_bet, initial_bankroll)
        self.assertTrue(seat1.is_active)
        self.assertEqual(self.app.engine.get_seat(2).main_bet, 0)
        self.assertEqual(self.app.engine.get_seat(3).main_bet, 0)
        self.assertEqual(self.app.engine.bankroll, 0)

    def test_all_in_with_partial_bets_across_seats(self):
        """
        Verifies that if bets are already placed on Seats 1 & 2, focusing Seat 3
        and clicking 'All In' stages the remaining bankroll onto Seat 3.
        """
        # Place $100 on Seat 1
        self.app.focused_betting_seat = 1
        self.app.selected_denomination = 100
        self.app.engine.stage_bet(1, 100)
        self.app.bankroll_var.set(self.app.engine.bankroll)
        self.app.current_bet_var.set(self.app.engine.staged_bet)

        # Place $200 on Seat 2
        self.app.focused_betting_seat = 2
        self.app.selected_denomination = 100
        self.app.engine.stage_bet(2, 200)
        self.app.bankroll_var.set(self.app.engine.bankroll)
        self.app.current_bet_var.set(self.app.engine.staged_bet)

        remaining_before_all_in = self.app.bankroll_var.get()
        self.assertGreater(remaining_before_all_in, 0)

        # Focus Seat 3 and go All-In
        self.app._on_table_spot_click(3, None)
        self.assertEqual(self.app.focused_betting_seat, 3)

        self.app._all_in()
        self.root.update_idletasks()

        self.assertEqual(self.app.engine.get_seat(1).main_bet, 100)
        self.assertEqual(self.app.engine.get_seat(2).main_bet, 200)
        self.assertEqual(self.app.engine.get_seat(3).main_bet, remaining_before_all_in)
        self.assertEqual(self.app.engine.bankroll, 0)
        self.assertEqual(self.app.bankroll_var.get(), 0)

    # ------------------------------------------------------------------------
    # Scenario 14: Default Chip Denomination is $5 (Lowest Chip Denomination)
    # ------------------------------------------------------------------------
    def test_default_chip_denomination_is_five_dollars(self):
        """
        Verifies that on startup and round reset, the default selected denomination
        in multi-seat mode is $5 (lowest chip, MINIMUM_BET), not $25.
        """
        self.assertEqual(self.app.selected_denomination, 5)

        # Trigger new game and verify it remains $5
        self.app.new_game()
        self.root.update_idletasks()
        self.assertEqual(self.app.selected_denomination, 5)

    def test_initial_click_on_active_spot_adds_five_dollar_bet(self):
        """
        Verifies that clicking on the currently active seat betting spot
        stages exactly $5 (the lowest denomination) by default.
        """
        self.assertEqual(self.app.focused_betting_seat, 2)
        self.app._on_table_spot_click(2, None)
        self.root.update_idletasks()

        seat2 = self.app.engine.get_seat(2)
        self.assertEqual(seat2.main_bet, 5)


if __name__ == "__main__":
    unittest.main()
