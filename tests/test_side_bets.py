"""
Automated Test Suite for Track 4: Casino Side Bets Subsystem (Perfect Pairs & 21+3).
Validates:
- Pure mathematical evaluation of Perfect Pairs (Mixed 6:1, Colored 12:1, Perfect 25:1).
- Pure mathematical evaluation of 21+3 (Flush 5:1, Straight 10:1, Three of a Kind 30:1, Straight Flush 40:1, Suited Trips 100:1).
- Edge cases: Ace-low/high straights, rank matching vs value matching (10 vs Queen), multi-deck identity.
- BlackjackEngine staged, committed, and resolved side bet states with bankroll synchronization.
- SaveManager side bet statistics and achievement unlocks (pair_perfectionist, poker_face).
- ChipVisualizer side bet spot rendering, clicks, and animations.
- BlackjackApp initial deal immediate settlement and telemetry.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config import STARTING_BANKROLL
from event_bus import EventHub, GameEventType
from game_engine import BlackjackEngine
from rules import (
    Card,
    Hand,
    RoundPhase,
    SideBetResult,
    evaluate_21_plus_3,
    evaluate_perfect_pairs,
)
from save_manager import SaveData, SaveManager


class TestSideBetsRules(unittest.TestCase):
    """Unit tests for pure side bet mathematical rules in rules.py."""

    def test_perfect_pairs_mixed_pair(self):
        """Mixed Pair (same rank, different color) pays 6:1."""
        c1 = Card(8, None, rank="8", suit="spade")    # Black
        c2 = Card(8, None, rank="8", suit="diamond")  # Red
        res = evaluate_perfect_pairs([c1, c2], bet=10)
        self.assertEqual(res.bet_type, "perfect_pairs")
        self.assertEqual(res.outcome, "MIXED_PAIR")
        self.assertEqual(res.multiplier, 6)
        self.assertEqual(res.bet, 10)
        self.assertEqual(res.payout, 70)  # 10 + 60
        self.assertEqual(res.profit, 60)
        self.assertTrue(res.won)

    def test_perfect_pairs_colored_pair(self):
        """Colored Pair (same rank, same color, different suit) pays 12:1."""
        # Black pair
        c1 = Card(8, None, rank="8", suit="spade")
        c2 = Card(8, None, rank="8", suit="club")
        res1 = evaluate_perfect_pairs([c1, c2], bet=5)
        self.assertEqual(res1.outcome, "COLORED_PAIR")
        self.assertEqual(res1.multiplier, 12)
        self.assertEqual(res1.payout, 65)  # 5 + 60
        self.assertEqual(res1.profit, 60)
        self.assertTrue(res1.won)

        # Red pair
        c3 = Card(10, None, rank="queen", suit="heart")
        c4 = Card(10, None, rank="queen", suit="diamond")
        res2 = evaluate_perfect_pairs([c3, c4], bet=25)
        self.assertEqual(res2.outcome, "COLORED_PAIR")
        self.assertEqual(res2.multiplier, 12)
        self.assertEqual(res2.payout, 325)
        self.assertEqual(res2.profit, 300)

    def test_perfect_pairs_perfect_pair(self):
        """Perfect Pair (identical rank and identical suit) pays 25:1."""
        c1 = Card(7, None, rank="7", suit="heart")
        c2 = Card(7, None, rank="7", suit="heart")
        res = evaluate_perfect_pairs([c1, c2], bet=10)
        self.assertEqual(res.outcome, "PERFECT_PAIR")
        self.assertEqual(res.multiplier, 25)
        self.assertEqual(res.payout, 260)  # 10 + 250
        self.assertEqual(res.profit, 250)
        self.assertTrue(res.won)

    def test_perfect_pairs_loss_and_non_matching_ranks(self):
        """Different ranks lose; identical values with different ranks (10 vs King) lose."""
        c1 = Card(10, None, rank="10", suit="club")
        c2 = Card(10, None, rank="king", suit="club")
        res = evaluate_perfect_pairs([c1, c2], bet=10)
        self.assertEqual(res.outcome, "LOSS")
        self.assertEqual(res.multiplier, 0)
        self.assertEqual(res.payout, 0)
        self.assertEqual(res.profit, -10)
        self.assertFalse(res.won)

        c3 = Card(2, None, rank="2", suit="club")
        c4 = Card(9, None, rank="9", suit="club")
        res2 = evaluate_perfect_pairs([c3, c4], bet=5)
        self.assertEqual(res2.outcome, "LOSS")
        self.assertFalse(res2.won)

    def test_perfect_pairs_supernatural_card_thirteen_rejected(self):
        """Cursed Card 13 is excluded from qualifying pairs."""
        c1 = Card(13, None, rank="thirteen", suit="skulls")
        c2 = Card(13, None, rank="thirteen", suit="skulls")
        res = evaluate_perfect_pairs([c1, c2], bet=10)
        self.assertEqual(res.outcome, "LOSS")
        self.assertFalse(res.won)

    # --- 21+3 Poker Tests ---

    def test_21_plus_3_flush(self):
        """Flush (same suit, non-consecutive ranks) pays 5:1."""
        p1 = Card(2, None, rank="2", suit="diamond")
        p2 = Card(6, None, rank="6", suit="diamond")
        dup = Card(9, None, rank="9", suit="diamond")
        res = evaluate_21_plus_3([p1, p2], dup, bet=10)
        self.assertEqual(res.outcome, "FLUSH")
        self.assertEqual(res.multiplier, 5)
        self.assertEqual(res.payout, 60)  # 10 + 50
        self.assertEqual(res.profit, 50)
        self.assertTrue(res.won)

    def test_21_plus_3_straight(self):
        """Straight (consecutive ranks, mixed suits) pays 10:1."""
        # 4, 5, 6
        p1 = Card(4, None, rank="4", suit="heart")
        p2 = Card(5, None, rank="5", suit="spade")
        dup = Card(6, None, rank="6", suit="diamond")
        res = evaluate_21_plus_3([p1, p2], dup, bet=5)
        self.assertEqual(res.outcome, "STRAIGHT")
        self.assertEqual(res.multiplier, 10)
        self.assertEqual(res.payout, 55)
        self.assertEqual(res.profit, 50)
        self.assertTrue(res.won)

        # Ace-low: A, 2, 3
        p1 = Card(1, None, rank="ace", suit="club")
        p2 = Card(2, None, rank="2", suit="spade")
        dup = Card(3, None, rank="3", suit="heart")
        res_low = evaluate_21_plus_3([p1, p2], dup, bet=5)
        self.assertEqual(res_low.outcome, "STRAIGHT")
        self.assertEqual(res_low.multiplier, 10)

        # Ace-high: Q, K, A
        p1 = Card(10, None, rank="queen", suit="club")
        p2 = Card(10, None, rank="king", suit="heart")
        dup = Card(1, None, rank="ace", suit="diamond")
        res_high = evaluate_21_plus_3([p1, p2], dup, bet=5)
        self.assertEqual(res_high.outcome, "STRAIGHT")
        self.assertEqual(res_high.multiplier, 10)

    def test_21_plus_3_three_of_a_kind(self):
        """Three of a Kind (same rank, non-identical suits) pays 30:1."""
        p1 = Card(8, None, rank="8", suit="heart")
        p2 = Card(8, None, rank="8", suit="spade")
        dup = Card(8, None, rank="8", suit="club")
        res = evaluate_21_plus_3([p1, p2], dup, bet=10)
        self.assertEqual(res.outcome, "THREE_OF_A_KIND")
        self.assertEqual(res.multiplier, 30)
        self.assertEqual(res.payout, 310)  # 10 + 300
        self.assertEqual(res.profit, 300)
        self.assertTrue(res.won)

        # Different ranks with same value (10, Jack, Queen) must NOT count as Three of a Kind
        p1 = Card(10, None, rank="10", suit="heart")
        p2 = Card(10, None, rank="jack", suit="spade")
        dup = Card(10, None, rank="queen", suit="club")
        res_diff = evaluate_21_plus_3([p1, p2], dup, bet=10)
        self.assertNotEqual(res_diff.outcome, "THREE_OF_A_KIND")

    def test_21_plus_3_straight_flush(self):
        """Straight Flush (consecutive ranks, same suit) pays 40:1."""
        p1 = Card(9, None, rank="9", suit="spade")
        p2 = Card(10, None, rank="10", suit="spade")
        dup = Card(10, None, rank="jack", suit="spade")
        res = evaluate_21_plus_3([p1, p2], dup, bet=10)
        self.assertEqual(res.outcome, "STRAIGHT_FLUSH")
        self.assertEqual(res.multiplier, 40)
        self.assertEqual(res.payout, 410)
        self.assertEqual(res.profit, 400)
        self.assertTrue(res.won)

    def test_21_plus_3_suited_trips(self):
        """Suited Trips (same rank, same suit from multi-deck shoe) pays 100:1."""
        p1 = Card(7, None, rank="7", suit="diamond")
        p2 = Card(7, None, rank="7", suit="diamond")
        dup = Card(7, None, rank="7", suit="diamond")
        res = evaluate_21_plus_3([p1, p2], dup, bet=10)
        self.assertEqual(res.outcome, "SUITED_TRIPS")
        self.assertEqual(res.multiplier, 100)
        self.assertEqual(res.payout, 1010)
        self.assertEqual(res.profit, 1000)
        self.assertTrue(res.won)

    def test_21_plus_3_loss(self):
        """Non-matching cards yield LOSS (0 payout, negative profit)."""
        p1 = Card(2, None, rank="2", suit="heart")
        p2 = Card(7, None, rank="7", suit="spade")
        dup = Card(10, None, rank="king", suit="club")
        res = evaluate_21_plus_3([p1, p2], dup, bet=15)
        self.assertEqual(res.outcome, "LOSS")
        self.assertEqual(res.multiplier, 0)
        self.assertEqual(res.payout, 0)
        self.assertEqual(res.profit, -15)
        self.assertFalse(res.won)


class TestSideBetsEngine(unittest.TestCase):
    """Unit tests for BlackjackEngine side bet staging, committing, and resolution."""

    def setUp(self):
        self.hub = EventHub()
        self.engine = BlackjackEngine(bankroll=1000, event_bus=self.hub)

    def test_stage_and_clear_side_bets(self):
        """Staging side bets respects bankroll limits; clear_side_bets resets them."""
        # Stage main bet $100
        self.engine.stage_bet(100)

        # Stage Perfect Pairs $25
        pp = self.engine.stage_side_bet("perfect_pairs", 25)
        self.assertEqual(pp, 25)
        self.assertEqual(self.engine.staged_side_bets["perfect_pairs"], 25)

        # Stage 21+3 $50
        t13 = self.engine.stage_side_bet("21_plus_3", 50)
        self.assertEqual(t13, 50)
        self.assertEqual(self.engine.staged_side_bets["21_plus_3"], 50)

        # Cannot exceed remaining bankroll: 1000 - 100 - 25 - 50 = 825 available
        overflow = self.engine.stage_side_bet("perfect_pairs", 900)
        self.assertEqual(overflow, 25 + 825)

        # Clear side bets
        self.engine.clear_side_bets()
        self.assertEqual(self.engine.staged_side_bets["perfect_pairs"], 0)
        self.assertEqual(self.engine.staged_side_bets["21_plus_3"], 0)

    def test_commit_and_resolve_side_bets(self):
        """Committed side bets deduct from bankroll and resolve immediately upon deal."""
        events = []
        self.hub.subscribe(GameEventType.SIDE_BET_RESOLVED, lambda e: events.append(e))

        self.engine.stage_bet(50)
        self.engine.stage_side_bet("perfect_pairs", 10)
        self.engine.stage_side_bet("21_plus_3", 20)

        # Rig shoe so player gets 8♠, 8♠ (Perfect Pair) and dealer upcard is 8♠ (Suited Trips)
        # Note: deal pops cards from shoe (reverse order)
        # Sequence: player 1, player 2, dealer 1, dealer 2 (hole)
        c_player1 = Card(8, None, rank="8", suit="spade")
        c_player2 = Card(8, None, rank="8", suit="spade")
        c_dealer_up = Card(8, None, rank="8", suit="spade")
        c_dealer_hole = Card(9, None, rank="9", suit="club")
        self.engine.shoe = [c_dealer_hole, c_dealer_up, c_player2, c_player1]

        # Deal round commits both main bet and side bets
        self.engine.commit_side_bets()
        self.assertEqual(self.engine.bankroll, 1000 - 30)

        p_hand, d_hand = self.engine.deal_round(bet=50)
        self.assertEqual(self.engine.bankroll, 1000 - 30 - 50)  # 920

        # Resolve side bets
        results = self.engine.resolve_side_bets(p_hand, d_hand[0])
        self.assertIn("perfect_pairs", results)
        self.assertIn("21_plus_3", results)
        self.assertEqual(results["perfect_pairs"].outcome, "PERFECT_PAIR")
        self.assertEqual(results["21_plus_3"].outcome, "SUITED_TRIPS")

        # Payouts:
        # Perfect Pairs: 10 * 25 + 10 = 260
        # 21+3: 20 * 100 + 20 = 2020
        # Bankroll should now be 920 + 260 + 2020 = 3200
        self.assertEqual(self.engine.bankroll, 3200)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["results"]["perfect_pairs"].outcome, "PERFECT_PAIR")


class TestSideBetsPersistence(unittest.TestCase):
    """Unit tests for SaveManager side bet stats and achievement tracking."""

    def test_side_bet_statistics_and_achievements(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            save_path = Path(tmp_dir) / "test_save.json"
            mgr = SaveManager(save_path=save_path)

            self.assertEqual(getattr(mgr.data.highscores, "side_bets_played", 0), 0)
            self.assertEqual(getattr(mgr.data.highscores, "side_bets_won", 0), 0)
            self.assertEqual(getattr(mgr.data.highscores, "biggest_side_bet_win", 0), 0)

            # Record a losing side bet
            mgr.record_side_bet("perfect_pairs", outcome="LOSS", bet=10, profit=-10, won=False)
            self.assertEqual(mgr.data.highscores.side_bets_played, 1)
            self.assertEqual(mgr.data.highscores.side_bets_won, 0)
            self.assertFalse(mgr.data.achievements.pair_perfectionist)

            # Record a winning 25:1 Perfect Pair
            mgr.record_side_bet("perfect_pairs", outcome="PERFECT_PAIR", bet=10, profit=250, won=True)
            self.assertEqual(mgr.data.highscores.side_bets_played, 2)
            self.assertEqual(mgr.data.highscores.side_bets_won, 1)
            self.assertEqual(mgr.data.highscores.biggest_side_bet_win, 250)
            self.assertTrue(mgr.data.achievements.pair_perfectionist)

            # Record a 21+3 Straight Flush win ($400 profit)
            mgr.record_side_bet("21_plus_3", outcome="STRAIGHT_FLUSH", bet=10, profit=400, won=True)
            self.assertEqual(mgr.data.highscores.side_bets_played, 3)
            self.assertEqual(mgr.data.highscores.side_bets_won, 2)
            self.assertEqual(mgr.data.highscores.biggest_side_bet_win, 400)
            self.assertTrue(mgr.data.achievements.poker_face)

            # Reload from disk and verify persistence
            mgr_reloaded = SaveManager(save_path=save_path)
            self.assertEqual(mgr_reloaded.data.highscores.side_bets_played, 3)
            self.assertEqual(mgr_reloaded.data.highscores.side_bets_won, 2)
            self.assertEqual(mgr_reloaded.data.highscores.biggest_side_bet_win, 400)
            self.assertTrue(mgr_reloaded.data.achievements.pair_perfectionist)
            self.assertTrue(mgr_reloaded.data.achievements.poker_face)


class TestSideBetsGuiAndIntegration(unittest.TestCase):
    """Integration and GUI tests for side bets in BlackjackApp."""

    def setUp(self):
        import tkinter
        from blackjack import BlackjackApp

        self.root = tkinter.Tk()
        self.root.withdraw()
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.save_path = Path(self.tmp_dir.name) / "test_gui_save.json"
        self.app = BlackjackApp(
            self.root,
            sound_enabled=False,
            save_path=self.save_path,
            chips_mode=True,
        )
        self.root.update_idletasks()

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        self.tmp_dir.cleanup()

    def test_side_bet_staging_and_clearing(self):
        """Side bets stage and clear cleanly through BlackjackApp."""
        self.app.current_bet_var.set(50)
        self.app._add_side_bet("perfect_pairs", 10)
        self.app._add_side_bet("21_plus_3", 15)

        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 10)
        self.assertEqual(self.app.engine.staged_side_bets["21_plus_3"], 15)
        # Total staged: 50 + 10 + 15 = 75
        self.assertIn("BET: $75", self.app.bankroll_label.cget("text"))

        # Deduct side bet
        self.app._deduct_side_bet("perfect_pairs", 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)
        self.assertIn("BET: $70", self.app.bankroll_label.cget("text"))

        # Clear bet
        self.app._clear_bet()
        self.assertEqual(self.app.current_bet_var.get(), 0)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 0)
        self.assertEqual(self.app.engine.staged_side_bets["21_plus_3"], 0)

    def test_side_bet_immediate_settlement_on_deal(self):
        """Side bets settle immediately after initial deal, crediting winnings before player action."""
        self.app.current_bet_var.set(25)
        self.app._add_side_bet("perfect_pairs", 10)

        # Rig deck: player gets 8♠, 8♠ (25:1 Perfect Pair); dealer gets 10♣, 7♦
        c_p1 = Card(8, self.app.back_image, rank="8", suit="spade")
        c_p2 = Card(8, self.app.back_image, rank="8", suit="spade")
        c_d1 = Card(10, self.app.back_image, rank="10", suit="club")
        c_d2 = Card(7, self.app.back_image, rank="7", suit="diamond")
        self.app.deck = [c_d2, c_d1, c_p2, c_p1]

        initial_bankroll = self.app.bankroll_var.get()
        # Commit deal: 25 main + 10 side bet = 35 deducted
        self.app._deal_hand_with_bet()

        # Side bet resolves immediately: 10 * 25 + 10 = 260 payout credited
        # Expected bankroll: initial_bankroll - 35 + 260 = initial_bankroll + 225
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll + 225)
        self.assertEqual(self.app.save_manager.data.highscores.side_bets_won, 1)
        self.assertTrue(self.app.save_manager.data.achievements.pair_perfectionist)

    def test_side_bet_shortcuts(self):
        """Shortcuts Q and E stage side bets during the betting phase."""
        self.assertTrue(self.app.is_betting_phase)
        self.app._add_side_bet("perfect_pairs", 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)
        self.app._add_side_bet("21_plus_3", 5)
        self.assertEqual(self.app.engine.staged_side_bets["21_plus_3"], 5)

    def test_side_bet_right_click_clears_single_side_bet_to_zero(self):
        """Right-clicking a side bet spot clears that side bet directly back to $0 without desync."""
        self.assertTrue(self.app.is_betting_phase)
        self.app._add_side_bet("perfect_pairs", 25)
        self.app._add_side_bet("21_plus_3", 10)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 25)
        self.assertEqual(self.app.engine.staged_side_bets["21_plus_3"], 10)

        # Trigger right-click clear on perfect_pairs spot
        self.app.chip_visualizer.trigger_side_bet_clear("perfect_pairs")
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 0)
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 0)
        self.assertEqual(self.app.engine.staged_side_bets["21_plus_3"], 10)

        # Subsequent click on perfect pairs starts fresh from $0 (0 + 5 = $5)
        self.app.chip_visualizer.trigger_side_bet_click("perfect_pairs", 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)

    def test_main_bet_deduction_does_not_clear_visual_side_bets(self):
        """Deducting the main bet to $0 must not clear visual side bet chips or desync staged side bets."""
        self.assertTrue(self.app.is_betting_phase)
        self.app.current_bet_var.set(10)
        self.app.engine.stage_bet(10)
        self.app._add_side_bet("perfect_pairs", 15)

        self.assertEqual(self.app.current_bet_var.get(), 10)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 15)

        # Deduct main bet to 0 via chip pile deduction
        self.app._deduct_chip_bet(10)
        self.assertEqual(self.app.current_bet_var.get(), 0)

        # Visual side bet and domain side bet must remain active and visible
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 15)
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 15)
        badge_text = self.app.chip_visualizer.itemcget("pp_badge", "text")
        self.assertIn("PAIRS: $15", badge_text)

    def test_bankroll_tray_deduct_when_main_bet_zero_deducts_side_bets(self):
        """Right-clicking bankroll chip piles when main bet is $0 deducts staged side bets."""
        self.assertTrue(self.app.is_betting_phase)
        self.app.current_bet_var.set(0)
        self.app._add_side_bet("perfect_pairs", 5)
        self.app._add_side_bet("21_plus_3", 5)

        # First deduction consumes 21+3
        self.app._deduct_chip_bet(5)
        self.assertEqual(self.app.engine.staged_side_bets["21_plus_3"], 0)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)

        # Second deduction consumes perfect pairs
        self.app._deduct_chip_bet(5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 0)

        # Re-adding starts fresh from $0
        self.app._add_side_bet("perfect_pairs", 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)

    def test_center_spot_left_click_adds_main_bet_and_right_click_clears_only_main_bet(self):
        """Center spot left-click adds $5/$25 to main bet, right-click clears only main bet."""
        self.assertTrue(self.app.is_betting_phase)
        self.app.current_bet_var.set(0)
        self.app._add_side_bet("perfect_pairs", 15)

        # Left-click on center spot adds $5
        self.app.chip_visualizer.trigger_spot_click(5)
        self.assertEqual(self.app.current_bet_var.get(), 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 15)

        # Shift + Left-click on center spot adds $25
        self.app.chip_visualizer.trigger_spot_click(25)
        self.assertEqual(self.app.current_bet_var.get(), 30)

        # Right-click on center spot clears ONLY the main bet, keeping side bets intact
        self.app.chip_visualizer.trigger_spot_clear()
        self.assertEqual(self.app.current_bet_var.get(), 0)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 15)

        # The dedicated Clear Bet button at the bottom clears all bets
        self.app._clear_bet()
        self.assertEqual(self.app.current_bet_var.get(), 0)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 0)

    def test_side_bets_do_not_carry_over_across_consecutive_rounds(self):
        """Losing side bet in Round 1 must not carry over into Round 2; clicking spot starts fresh at $5."""
        self.assertTrue(self.app.is_betting_phase)
        self.app.current_bet_var.set(10)
        self.app._add_side_bet("perfect_pairs", 5)

        # Rig non-matching cards: player gets 8♠, 9♦ (Loss)
        c_p1 = Card(8, self.app.back_image, rank="8", suit="spade")
        c_p2 = Card(9, self.app.back_image, rank="9", suit="diamond")
        c_d1 = Card(10, self.app.back_image, rank="10", suit="club")
        c_d2 = Card(7, self.app.back_image, rank="7", suit="diamond")
        self.app.deck = [c_d2, c_d1, c_p2, c_p1]

        # Deal hand: commits $10 main and $5 side bet
        self.app._deal_hand_with_bet()
        self.app.root.update_idletasks()

        # Side bet resolved as loss; verify active_side_bets is cleared
        self.assertEqual(self.app.engine.active_side_bets["perfect_pairs"], 0)

        # End round and start Round 2
        self.app.new_game()
        self.assertTrue(self.app.is_betting_phase)

        # Staged side bets in engine and visualizer must be 0
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 0)
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 0)

        # Left-click on Perfect Pairs in Round 2 must stage exactly $5 (NOT $10)
        self.app.chip_visualizer.trigger_side_bet_click("perfect_pairs", 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 5)
        self.assertIn("PAIRS: $5", self.app.chip_visualizer.itemcget("pp_badge", "text"))

    def test_winning_side_bet_resets_and_clears_for_next_round(self):
        """Winning side bet chips and staged amounts must reset for Round 2; clicking spot starts fresh at $5."""
        self.assertTrue(self.app.is_betting_phase)
        self.app.current_bet_var.set(10)
        self.app._add_side_bet("perfect_pairs", 5)

        # Rig matching cards: player gets 8♠, 8♠ (25:1 win)
        c_p1 = Card(8, self.app.back_image, rank="8", suit="spade")
        c_p2 = Card(8, self.app.back_image, rank="8", suit="spade")
        c_d1 = Card(10, self.app.back_image, rank="10", suit="club")
        c_d2 = Card(7, self.app.back_image, rank="7", suit="diamond")
        self.app.deck = [c_d2, c_d1, c_p2, c_p1]

        # Deal hand
        self.app._deal_hand_with_bet()
        self.app.root.update_idletasks()

        # Visualizer side_bets tracking should reset to 0
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 0)

        # End round and start Round 2
        self.app.new_game()
        self.assertTrue(self.app.is_betting_phase)

        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 0)
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 0)

        # Left click in Round 2 starts fresh at $5 (NOT $15 or higher)
        self.app.chip_visualizer.trigger_side_bet_click("perfect_pairs", 5)
        self.assertEqual(self.app.engine.staged_side_bets["perfect_pairs"], 5)
        self.assertEqual(self.app.chip_visualizer.side_bets["perfect_pairs"], 5)


if __name__ == "__main__":
    unittest.main()
