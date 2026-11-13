"""
Unit and persistence test suite for TripometerTracker, TripometerData,
and SaveManager HouseRules / Tripometer serialization.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import rules
from card_counter import HiLoCardCounter
from game_engine import BlackjackEngine
from rules import Card, HouseRules, RoundPhase
from save_manager import SaveManager
import tripometer
from tripometer import (
    DecisionStepRecord,
    HandHistoryRecord,
    TripometerData,
    TripometerTracker,
    format_card_token,
)


class TestTripometerDomainAndPersistence(unittest.TestCase):
    """Phase 2 tests for TripometerTracker grading, buffering, and SaveManager isolation."""

    def setUp(self):
        self._tmp_dir = Path(tempfile.mkdtemp(prefix="bj_trip_test_"))
        self.save_path = self._tmp_dir / "test_save.json"

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_card_token_formatting_and_json_safety(self):
        non_json_img = object()
        self.assertEqual(format_card_token(Card(1, non_json_img, "ace", "spade")), "A♠")
        self.assertEqual(format_card_token(Card(10, non_json_img, "king", "heart")), "K♥")
        self.assertEqual(format_card_token(Card(10, non_json_img, "10", "diamond")), "10♦")
        self.assertEqual(format_card_token(Card(13, non_json_img, "thirteen", "club")), "13♣")
        self.assertEqual(format_card_token(Card(1, non_json_img)), "A")

        tracker = TripometerTracker()
        hr = HouseRules()
        tracker.begin_round(hr, pre_deal_tc=0.0, seat_bets={0: 5}, round_bankroll=1000)
        tracker.record_decision(
            seat_idx=0,
            hand_idx=0,
            cards=[Card(10, non_json_img, "10", "spade"), Card(6, non_json_img, "6", "heart")],
            dealer_upcard=Card(10, non_json_img, "queen", "club"),
            action="SURRENDER",
            live_tc=-0.5,
            can_split=False,
            can_double=True,
            can_surrender=True,
        )
        tracker.finalize_round(
            settled_hands=[
                {
                    "seat_idx": 0,
                    "hand_idx": 0,
                    "wager": 5,
                    "cards": [Card(10, non_json_img, "10", "spade"), Card(6, non_json_img, "6", "heart")],
                    "outcome": "SURRENDER",
                    "net_profit": -3,
                }
            ],
            dealer_cards=[Card(10, non_json_img, "queen", "club"), Card(7, non_json_img, "7", "diamond")],
            net_round_profit=-3,
        )
        encoded = json.dumps(tracker.data.to_dict())
        self.assertIn("10\\u2660", encoded)
        summary = tracker.get_summary()
        self.assertEqual(summary["bs_pct"], 100.0)
        self.assertEqual(summary["i18_pct"], 100.0)
        self.assertEqual(summary["kelly_pct"], 100.0)
        self.assertEqual(summary["trip_net_profit"], -3)

    def test_empty_state_denominators_and_naturals_excluded(self):
        tracker = TripometerTracker()
        summary = tracker.get_summary()
        self.assertIsNone(summary["bs_pct"])
        self.assertIsNone(summary["i18_pct"])
        self.assertIsNone(summary["kelly_pct"])
        self.assertEqual(summary["bs_display"], "N/A (0 spots)")

        # Natural Blackjack + auto stand on split Aces must not increment BS denominator
        hr = HouseRules()
        tracker.begin_round(hr, pre_deal_tc=0.0, seat_bets={0: 5}, round_bankroll=500)
        tracker.record_decision(
            seat_idx=0,
            hand_idx=0,
            cards=[Card(1), Card(10)],
            dealer_upcard=Card(6),
            action="STAND",
            live_tc=0.0,
            can_split=False,
            can_double=False,
            can_surrender=False,
            auto=True,
        )
        tracker.finalize_round(
            settled_hands=[
                {
                    "seat_idx": 0,
                    "hand_idx": 0,
                    "wager": 5,
                    "cards": [Card(1), Card(10)],
                    "outcome": "NATURAL_BLACKJACK",
                    "net_profit": 7,
                }
            ],
            dealer_cards=[Card(6), Card(10)],
            net_round_profit=7,
        )
        self.assertEqual(tracker.data.bs_total_decisions, 0)
        self.assertEqual(tracker.data.kelly_total_rounds, 1)
        self.assertEqual(tracker.data.kelly_optimal_rounds, 1)
        self.assertEqual(tracker.data.hands_recorded, 1)
        self.assertEqual(tracker.data.trip_net_profit, 7)

    def test_multi_rule_snapshots_and_non_contradictory_i18_grading(self):
        tracker = TripometerTracker()
        classic = rules.VENUE_PRESETS["classic_4_deck"]
        pitch = rules.VENUE_PRESETS["downtown_pitch"]

        # Round 1 on Classic 4D: Stand on 16 vs 10 at TC +2.0 (Active I18 deviation)
        # Must satisfy BOTH I18 AND Basic Strategy grades!
        tracker.begin_round(classic, pre_deal_tc=2.0, seat_bets={0: 10}, round_bankroll=1000)
        tracker.record_decision(
            seat_idx=0,
            hand_idx=0,
            cards=[Card(10), Card(6)],
            dealer_upcard=Card(10),
            action="STAND",
            live_tc=2.0,
            can_split=False,
            can_double=True,
            can_surrender=True,
        )
        tracker.finalize_round(
            settled_hands=[
                {
                    "seat_idx": 0,
                    "hand_idx": 0,
                    "wager": 10,
                    "cards": [Card(10), Card(6)],
                    "outcome": "DEALER_BUST",
                    "net_profit": 10,
                }
            ],
            dealer_cards=[Card(10), Card(6), Card(10)],
            net_round_profit=10,
        )

        # Round 2 on Downtown 2D H17 ($10 min, No Surrender): Double Soft 19 vs 6 (H17 BS)
        tracker.begin_round(pitch, pre_deal_tc=0.0, seat_bets={0: 10}, round_bankroll=1010)
        tracker.record_decision(
            seat_idx=0,
            hand_idx=0,
            cards=[Card(1), Card(8)],
            dealer_upcard=Card(6),
            action="DOUBLE",
            live_tc=0.0,
            can_split=False,
            can_double=True,
            can_surrender=False,
        )
        tracker.finalize_round(
            settled_hands=[
                {
                    "seat_idx": 0,
                    "hand_idx": 0,
                    "wager": 20,
                    "cards": [Card(1), Card(8), Card(2)],
                    "outcome": "PLAYER_WINS",
                    "net_profit": 20,
                }
            ],
            dealer_cards=[Card(6), Card(10), Card(2)],
            net_round_profit=20,
        )

        self.assertEqual(tracker.data.bs_optimal_decisions, 2)
        self.assertEqual(tracker.data.bs_total_decisions, 2)
        self.assertEqual(tracker.data.i18_optimal_decisions, 1)
        self.assertEqual(tracker.data.i18_opportunities, 1)
        # Newest hand at index 0 is 2D H17; older hand at index 1 retains 4D S17 snapshot
        self.assertIn("2D H17", tracker.data.recent_hands[0].rules_badge)
        self.assertIn("4D S17", tracker.data.recent_hands[1].rules_badge)

    def test_insurance_grading_and_affordability_gate(self):
        tracker = TripometerTracker()
        hr = HouseRules()

        # Routine decline at TC +1.0 -> does NOT increment i18_opportunities or BS
        tracker.begin_round(hr, pre_deal_tc=1.0, seat_bets={0: 10}, round_bankroll=500)
        tracker.record_insurance_decision(seat_idx=0, took_insurance=False, live_tc=1.0, can_afford=True)
        tracker.finalize_round(
            settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 10, "cards": [Card(10), Card(10)], "outcome": "PLAYER_WINS", "net_profit": 10}],
            dealer_cards=[Card(1), Card(7)],
            net_round_profit=10,
        )
        self.assertEqual(tracker.data.i18_opportunities, 0)
        self.assertEqual(tracker.data.bs_total_decisions, 0)

        # Erroneous insurance taken at TC +1.0 -> increments i18_opportunities (0/1), never BS
        tracker.begin_round(hr, pre_deal_tc=1.0, seat_bets={0: 10}, round_bankroll=500)
        tracker.record_insurance_decision(seat_idx=0, took_insurance=True, live_tc=1.0, can_afford=True)
        tracker.finalize_round(
            settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 10, "cards": [Card(10), Card(10)], "outcome": "PLAYER_WINS", "net_profit": 5}],
            dealer_cards=[Card(1), Card(7)],
            net_round_profit=5,
        )
        self.assertEqual(tracker.data.i18_opportunities, 1)
        self.assertEqual(tracker.data.i18_optimal_decisions, 0)
        self.assertEqual(tracker.data.bs_total_decisions, 0)

        # Unaffordable seat at TC +4.0 -> no-op (does not penalize All-In player)
        tracker.begin_round(hr, pre_deal_tc=4.0, seat_bets={0: 500}, round_bankroll=500)
        tracker.record_insurance_decision(seat_idx=0, took_insurance=False, live_tc=4.0, can_afford=False)
        tracker.finalize_round(
            settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 500, "cards": [Card(10), Card(10)], "outcome": "DEALER_WINS", "net_profit": -500}],
            dealer_cards=[Card(1), Card(10)],
            net_round_profit=-500,
        )
        self.assertEqual(tracker.data.i18_opportunities, 1)

        # Affordable seat taking insurance at TC +3.5 -> optimal (1/2)
        tracker.begin_round(hr, pre_deal_tc=3.5, seat_bets={0: 20}, round_bankroll=500)
        tracker.record_insurance_decision(seat_idx=0, took_insurance=True, live_tc=3.5, can_afford=True)
        tracker.finalize_round(
            settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 20, "cards": [Card(10), Card(10)], "outcome": "DEALER_WINS", "net_profit": 0}],
            dealer_cards=[Card(1), Card(10)],
            net_round_profit=0,
        )
        self.assertEqual(tracker.data.i18_opportunities, 2)
        self.assertEqual(tracker.data.i18_optimal_decisions, 1)

    def test_kelly_tolerance_multiseat_and_casual_mode(self):
        tracker = TripometerTracker()
        hr = HouseRules()  # $5 min, 0.50% edge

        # Casual mode -> kelly_status = "N/A", kelly_total_rounds = 0
        tracker.begin_round(hr, pre_deal_tc=3.0, seat_bets={0: 0}, round_bankroll=1000, chips_mode=False)
        tracker.finalize_round(
            settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 0, "cards": [Card(10), Card(10)], "outcome": "PLAYER_WINS", "net_profit": 0}],
            dealer_cards=[Card(10), Card(7)],
            net_round_profit=0,
        )
        self.assertEqual(tracker.data.kelly_total_rounds, 0)
        self.assertEqual(tracker.data.recent_hands[0].kelly_status, "N/A")

        # 3-seat mode at TC +3.0 (target_tier = 2 -> $20; +-1 tier tolerance accepts $10..$40 per seat)
        tracker.begin_round(hr, pre_deal_tc=3.0, seat_bets={1: 10, 2: 20, 3: 40}, round_bankroll=1000, chips_mode=True)
        tracker.finalize_round(
            settled_hands=[
                {"seat_idx": 1, "hand_idx": 0, "wager": 10, "cards": [Card(10), Card(9)], "outcome": "PLAYER_WINS", "net_profit": 10},
                {"seat_idx": 2, "hand_idx": 0, "wager": 20, "cards": [Card(10), Card(9)], "outcome": "PLAYER_WINS", "net_profit": 20},
                {"seat_idx": 3, "hand_idx": 0, "wager": 40, "cards": [Card(10), Card(9)], "outcome": "PLAYER_WINS", "net_profit": 40},
            ],
            dealer_cards=[Card(10), Card(7)],
            net_round_profit=70,
        )
        self.assertEqual(tracker.data.kelly_total_rounds, 1)
        self.assertEqual(tracker.data.kelly_optimal_rounds, 1)

        # Tier 0 (TC 0.0 -> $5 min): overbetting $25 fails Kelly
        tracker.begin_round(hr, pre_deal_tc=0.0, seat_bets={0: 25}, round_bankroll=1000, chips_mode=True)
        tracker.finalize_round(
            settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 25, "cards": [Card(10), Card(9)], "outcome": "PLAYER_WINS", "net_profit": 25}],
            dealer_cards=[Card(10), Card(7)],
            net_round_profit=25,
        )
        self.assertEqual(tracker.data.kelly_total_rounds, 2)
        self.assertEqual(tracker.data.kelly_optimal_rounds, 1)
        self.assertEqual(tracker.data.recent_hands[0].kelly_status, "OVERBET")

    def test_ephemeral_buffering_mid_hand_abort_and_haunted_exclusions(self):
        tracker = TripometerTracker()
        hr = HouseRules()

        # Aborted mid-hand round never mutates persistent counters
        tracker.begin_round(hr, pre_deal_tc=0.0, seat_bets={0: 5}, round_bankroll=1000)
        tracker.record_decision(
            seat_idx=0,
            hand_idx=0,
            cards=[Card(10), Card(6)],
            dealer_upcard=Card(6),
            action="HIT",  # Deliberate blunder
            live_tc=0.0,
            can_split=False,
            can_double=True,
            can_surrender=True,
        )
        tracker.abort_round()
        self.assertEqual(tracker.data.bs_total_decisions, 0)
        self.assertEqual(tracker.data.kelly_total_rounds, 0)

        # Mid-hand supernatural trigger (e.g., Card 13 or HELL_TABLE +$6,666 bounty)
        # records audit log entry with ungraded_reason="haunted" without touching grades or trip_net_profit
        tracker.begin_round(hr, pre_deal_tc=0.0, seat_bets={0: 5}, round_bankroll=1000)
        tracker.record_decision(
            seat_idx=0,
            hand_idx=0,
            cards=[Card(5), Card(6)],
            dealer_upcard=Card(10),
            action="HIT",
            live_tc=0.0,
            can_split=False,
            can_double=True,
            can_surrender=True,
        )
        tracker.mark_supernatural("haunted")
        tracker.finalize_round(
            settled_hands=[
                {
                    "seat_idx": 0,
                    "hand_idx": 0,
                    "wager": 5,
                    "cards": [Card(5), Card(6), Card(13, None, "thirteen", "spade")],
                    "outcome": "PLAYER_BUST",
                    "net_profit": 6666,
                }
            ],
            dealer_cards=[Card(10), Card(7)],
            net_round_profit=6666,
        )
        self.assertEqual(tracker.data.bs_total_decisions, 0)
        self.assertEqual(tracker.data.kelly_total_rounds, 0)
        self.assertEqual(tracker.data.trip_net_profit, 0)
        self.assertEqual(len(tracker.data.recent_hands), 1)
        self.assertEqual(tracker.data.recent_hands[0].ungraded_reason, "haunted")

    def test_ring_buffer_50_hand_eviction_and_save_manager_isolation(self):
        sm = SaveManager(save_path=self.save_path)
        sm.record_bankroll(5500)
        sm.unlock_achievement("split_maestro")

        # Save custom rules and verify reload
        vip = rules.VENUE_PRESETS["high_roller_vip"]
        sm.save_house_rules(vip)
        tracker = TripometerTracker(data=sm.get_tripometer_data(), save_manager=sm)

        for idx in range(55):
            tracker.begin_round(vip, pre_deal_tc=0.0, seat_bets={0: 100}, round_bankroll=5500)
            tracker.record_decision(
                seat_idx=0,
                hand_idx=0,
                cards=[Card(10), Card(7)],
                dealer_upcard=Card(10),
                action="STAND",
                live_tc=0.0,
                can_split=False,
                can_double=True,
                can_surrender=True,
            )
            tracker.finalize_round(
                settled_hands=[{"seat_idx": 0, "hand_idx": 0, "wager": 100, "cards": [Card(10), Card(7)], "outcome": "PUSH", "net_profit": 0}],
                dealer_cards=[Card(10), Card(7)],
                net_round_profit=0,
            )

        self.assertEqual(len(tracker.data.recent_hands), 50)
        self.assertEqual(tracker.data.hands_recorded, 55)
        self.assertEqual(tracker.data.bs_total_decisions, 55)

        # Reload from disk and verify persistence
        sm_reloaded = SaveManager(save_path=self.save_path)
        self.assertEqual(sm_reloaded.get_house_rules(), vip)
        loaded_trip = sm_reloaded.get_tripometer_data()
        self.assertEqual(loaded_trip.hands_recorded, 55)
        self.assertEqual(len(loaded_trip.recent_hands), 50)

        # Reset Tripometer without affecting career bankroll, achievements, or costumes
        sm_reloaded.reset_tripometer()
        after_reset = SaveManager(save_path=self.save_path)
        self.assertEqual(after_reset.get_tripometer_data().hands_recorded, 0)
        self.assertEqual(after_reset.data.current_bankroll, 5500)
        self.assertTrue(after_reset.data.achievements.split_maestro)
        self.assertIn("grim", after_reset.data.unlocked_costumes)

        # Legacy save missing house_rules and tripometer + corrupted counter clamping
        corrupted_payload = {
            "version": "1.0",
            "current_bankroll": 1200,
            "tripometer": {
                "bs_optimal_decisions": 999,
                "bs_total_decisions": 10,
                "i18_optimal_decisions": -5,
                "i18_opportunities": -2,
                "recent_hands": [{}] * 80,
            },
        }
        self.save_path.write_text(json.dumps(corrupted_payload), encoding="utf-8")
        sm_legacy = SaveManager(save_path=self.save_path)
        self.assertEqual(sm_legacy.get_house_rules(), HouseRules())
        sanitized_trip = sm_legacy.get_tripometer_data()
        self.assertEqual(sanitized_trip.bs_total_decisions, 10)
        self.assertEqual(sanitized_trip.bs_optimal_decisions, 10)
        self.assertEqual(sanitized_trip.i18_opportunities, 0)
        self.assertEqual(sanitized_trip.i18_optimal_decisions, 0)
        self.assertEqual(len(sanitized_trip.recent_hands), 50)

    def test_headless_engine_telemetry_integration_1_seat_and_3_seat(self):
        counter = HiLoCardCounter(deck_count=4)
        tracker = TripometerTracker()
        engine = BlackjackEngine(
            bankroll=1000,
            rules=HouseRules(),
            tripometer=tracker,
            card_counter=counter,
            table_seats=3,
        )

        # 3-seat headless round: Seat 1 gets 16 vs 10 (Surrenders), Seat 2 gets 11 vs 10 (Doubles)
        engine.stage_bet(1, 5)
        engine.stage_bet(2, 5)
        engine.shoe = [
            Card(7, None, "7", "diamond"),    # Dealer hit/stand not needed or dealer 17
            Card(9, None, "9", "club"),       # Seat 2 double card -> 20
            Card(10, None, "10", "spade"),    # Dealer upcard (10)
            Card(5, None, "5", "heart"),      # Seat 2 card 2 (6+5=11)
            Card(6, None, "6", "club"),       # Seat 1 card 2 (10+6=16)
            Card(7, None, "7", "heart"),      # Dealer hole (17)
            Card(6, None, "6", "spade"),      # Seat 2 card 1
            Card(10, None, "king", "heart"),  # Seat 1 card 1
        ]
        engine.deal_round(bet=None)
        self.assertEqual(engine.phase, RoundPhase.PLAYER_TURN)
        engine.surrender(1)  # Optimal BS & I18 (16 vs 10 at TC 0)
        engine.double_down(2)  # Optimal BS (11 vs 10 -> DOUBLE)
        engine.resolve_outcomes()

        self.assertEqual(tracker.data.rounds_recorded, 1)
        self.assertEqual(tracker.data.hands_recorded, 2)
        self.assertEqual(tracker.data.bs_total_decisions, 2)
        self.assertEqual(tracker.data.bs_optimal_decisions, 2)
        self.assertEqual(tracker.data.kelly_total_rounds, 1)
        self.assertEqual(tracker.data.kelly_optimal_rounds, 1)
        # Seat 1 lost -$3 ($5 bet -> $2 refund), Seat 2 won +$10 ($10 doubled bet -> $20 payout) => net +$7
        self.assertEqual(tracker.data.trip_net_profit, 7)


if __name__ == "__main__":
    unittest.main()
