"""
Unit test suite for HouseRules, Casino Presets, Rule-Aware Basic Strategy,
Surrender-Aware Illustrious 18 Deviations, and MIT 1-12 Kelly Bet Targets.
"""

from __future__ import annotations

import unittest

import rules
from card_counter import HiLoCardCounter
from event_bus import EventHub, GameEventType
from game_engine import BlackjackEngine
from rules import (
    Card,
    Hand,
    RoundPhase,
    calculate_payout,
    determine_outcome,
    get_basic_strategy_decision,
)


class TestHouseRulesDomain(unittest.TestCase):
    """Phase 1 pure-domain tests for HouseRules and rule-aware strategy/counting math."""

    def test_default_house_rules_match_classic_baseline(self):
        hr = rules.HouseRules()
        self.assertEqual(hr.preset_id, "classic_4_deck")
        self.assertEqual(hr.deck_count, 4)
        self.assertFalse(hr.dealer_hits_soft_17)
        self.assertEqual(hr.blackjack_payout, (3, 2))
        self.assertTrue(hr.allow_das)
        self.assertEqual(hr.double_restriction, "any")
        self.assertTrue(hr.allow_surrender)
        self.assertEqual(hr.minimum_bet, 5)
        self.assertEqual(hr.maximum_bet, 0)
        with self.assertRaises(Exception):
            hr.deck_count = 6  # type: ignore[misc]

    def test_normalization_and_json_sanitization(self):
        # Tourist trap $15 min must be preserved without clamping mutation
        trap = rules.VENUE_PRESETS["tourist_trap_6_5"]
        self.assertEqual(trap.minimum_bet, 15)
        self.assertEqual(trap.normalized(), trap)
        self.assertEqual(trap.normalized().preset_id, "tourist_trap_6_5")

        # JSON list payout [6, 5] must coerce to hashable tuple (6, 5)
        loaded = rules.HouseRules.from_dict(
            {
                "preset_id": "tourist_trap_6_5",
                "deck_count": 8,
                "dealer_hits_soft_17": True,
                "blackjack_payout": [6, 5],
                "allow_das": False,
                "double_restriction": "any",
                "allow_surrender": False,
                "minimum_bet": 15,
                "maximum_bet": 500,
            }
        )
        self.assertIsInstance(loaded.blackjack_payout, tuple)
        self.assertEqual(loaded.blackjack_payout, (6, 5))
        cache_probe = {loaded.blackjack_payout: "ok"}
        self.assertEqual(cache_probe[(6, 5)], "ok")

        # Corrupted / out-of-range values clamp safely and enforce maximum_bet >= minimum_bet
        corrupted = rules.HouseRules.from_dict(
            {
                "deck_count": 99,
                "blackjack_payout": [3, 0],
                "double_restriction": "bogus",
                "minimum_bet": 500,
                "maximum_bet": 100,
            }
        )
        self.assertEqual(corrupted.deck_count, 8)
        self.assertEqual(corrupted.blackjack_payout, (3, 2))
        self.assertEqual(corrupted.double_restriction, "any")
        self.assertEqual(corrupted.minimum_bet, 500)
        self.assertGreaterEqual(corrupted.maximum_bet, 500)
        self.assertEqual(corrupted.preset_id, "custom")

    def test_venue_presets_and_house_edge_monotonicity(self):
        expected_keys = {
            "classic_4_deck",
            "vegas_strip",
            "downtown_pitch",
            "reno_single_deck",
            "high_roller_vip",
            "tourist_trap_6_5",
        }
        self.assertEqual(set(rules.VENUE_PRESETS.keys()), expected_keys)

        classic_edge = rules.estimate_house_edge_pct(rules.VENUE_PRESETS["classic_4_deck"])
        strip_edge = rules.estimate_house_edge_pct(rules.VENUE_PRESETS["vegas_strip"])
        trap_edge = rules.estimate_house_edge_pct(rules.VENUE_PRESETS["tourist_trap_6_5"])

        self.assertAlmostEqual(classic_edge, 0.50, places=2)
        self.assertGreater(strip_edge, classic_edge)
        self.assertGreater(trap_edge, 2.0)

    def test_dealer_soft_17_behavior(self):
        soft_17_two = [Card(1), Card(6)]
        soft_17_three = [Card(1), Card(2), Card(4)]
        hard_17_two = [Card(10), Card(7)]
        hard_17_ace_as_one = [Card(10), Card(6), Card(1)]
        hard_16 = [Card(10), Card(6)]

        # S17 default
        self.assertFalse(rules.dealer_should_hit(soft_17_two))
        self.assertFalse(rules.dealer_should_hit(soft_17_two, hits_soft_17=False))
        self.assertFalse(rules.dealer_should_hit(soft_17_three, hits_soft_17=False))
        self.assertTrue(rules.dealer_should_hit(hard_16, hits_soft_17=False))

        # H17
        self.assertTrue(rules.dealer_should_hit(soft_17_two, hits_soft_17=True))
        self.assertTrue(rules.dealer_should_hit(soft_17_three, hits_soft_17=True))
        self.assertFalse(rules.dealer_should_hit(hard_17_two, hits_soft_17=True))
        self.assertFalse(rules.dealer_should_hit(hard_17_ace_as_one, hits_soft_17=True))

    def test_blackjack_payout_ratios_and_post_split_21(self):
        # 3:2 payouts (total return = bet + floor(bet * 3 / 2))
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 5, (3, 2)), 12)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 15, (3, 2)), 37)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 25, (3, 2)), 62)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 100, (3, 2)), 250)

        # 6:5 payouts (total return = bet + floor(bet * 6 / 5))
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 5, (6, 5)), 11)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 15, (6, 5)), 33)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 25, (6, 5)), 55)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 100, (6, 5)), 220)

        # Post-split 2-card 21 (A+10) must never evaluate as NATURAL_BLACKJACK
        split_21 = Hand([Card(1), Card(10)], bet=100, is_split=True)
        outcome_vs_20, _ = determine_outcome(split_21, [Card(10), Card(10)])
        self.assertEqual(outcome_vs_20, "PLAYER_WINS")
        self.assertEqual(calculate_payout(outcome_vs_20, 100, (3, 2)), 200)

        outcome_vs_dealer_21, _ = determine_outcome(split_21, [Card(7), Card(7), Card(7)])
        self.assertEqual(outcome_vs_dealer_21, "PUSH")

        outcome_vs_dealer_bj, _ = determine_outcome(split_21, [Card(1), Card(10)])
        self.assertEqual(outcome_vs_dealer_bj, "DEALER_WINS")

    def test_can_double_and_surrender_helpers(self):
        reno = rules.VENUE_PRESETS["reno_single_deck"]  # No DAS, double 10_11 only, no surrender
        r_9_11 = rules.HouseRules(double_restriction="9_10_11", allow_das=False, allow_surrender=False)

        hard_10 = Hand([Card(6), Card(4)], bet=25)
        hard_9 = Hand([Card(5), Card(4)], bet=25)
        soft_19_raw_9 = Hand([Card(1), Card(8)], bet=25)   # Raw sum 9, Soft 19 -> MUST NOT double!
        soft_20_raw_10 = Hand([Card(1), Card(9)], bet=25)  # Raw sum 10, Soft 20 -> MUST NOT double!
        split_10 = Hand([Card(6), Card(4)], bet=25, is_split=True)
        already_doubled = Hand([Card(6), Card(4)], bet=25, is_doubled=True)

        self.assertTrue(rules.can_double_down_hand(hard_10, reno, available_bankroll=50))
        self.assertFalse(rules.can_double_down_hand(hard_10, reno, available_bankroll=10))
        self.assertFalse(rules.can_double_down_hand(hard_9, reno, available_bankroll=50))
        self.assertTrue(rules.can_double_down_hand(hard_9, r_9_11, available_bankroll=50))
        self.assertFalse(rules.can_double_down_hand(soft_19_raw_9, r_9_11, available_bankroll=50))
        self.assertFalse(rules.can_double_down_hand(soft_20_raw_10, reno, available_bankroll=50))
        self.assertFalse(rules.can_double_down_hand(split_10, reno, available_bankroll=50))
        self.assertFalse(rules.can_double_down_hand(already_doubled, rules.HouseRules(), available_bankroll=50))

        # Surrender helper
        self.assertTrue(rules.can_surrender_hand(hard_10, rules.HouseRules()))
        self.assertFalse(rules.can_surrender_hand(hard_10, reno))
        self.assertFalse(rules.can_surrender_hand(split_10, rules.HouseRules()))

    def test_betting_limits_and_cut_card_thresholds(self):
        vip = rules.HouseRules(minimum_bet=250, maximum_bet=5000)
        self.assertEqual(rules.effective_minimum_bet(vip, round_bankroll=12000), 250)
        self.assertEqual(rules.effective_minimum_bet(vip, round_bankroll=150), 150)
        self.assertEqual(rules.effective_minimum_bet(vip, round_bankroll=3), 3)
        self.assertEqual(rules.effective_minimum_bet(vip, round_bankroll=0), 250)

        self.assertEqual(rules.clamp_main_bet(10000, vip, max_affordable=12000), 5000)
        self.assertEqual(rules.clamp_main_bet(10000, rules.HouseRules(), max_affordable=12000), 10000)
        self.assertEqual(rules.clamp_main_bet(15000, rules.HouseRules(), max_affordable=12000), 12000)

        # Cut card scaling
        self.assertEqual(rules.min_cards_before_deal(1, table_seats=1), 15)
        self.assertEqual(rules.min_cards_before_deal(1, table_seats=3), 27)
        self.assertEqual(rules.cut_card_threshold(1, table_seats=1), 15)
        self.assertEqual(rules.cut_card_threshold(1, table_seats=3), 27)
        self.assertEqual(rules.cut_card_threshold(4, table_seats=1), 52)
        self.assertEqual(rules.cut_card_threshold(8, table_seats=1), 104)

    def test_rule_aware_basic_strategy(self):
        # Legacy rules=None keeps 11 vs A -> DOUBLE
        self.assertEqual(
            get_basic_strategy_decision([Card(5), Card(6)], Card(1), can_double=True).action,
            "DOUBLE",
        )

        # 4D S17 (HouseRules default): 11 vs A -> HIT; Soft 19 vs 6 -> STAND
        s17_4d = rules.HouseRules()
        self.assertEqual(
            get_basic_strategy_decision([Card(5), Card(6)], Card(1), rules=s17_4d).action,
            "HIT",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(1), Card(8)], Card(6), rules=s17_4d).action,
            "STAND",
        )

        # 2D S17: 11 vs A -> DOUBLE
        s17_2d = rules.HouseRules(deck_count=2, dealer_hits_soft_17=False)
        self.assertEqual(
            get_basic_strategy_decision([Card(5), Card(6)], Card(1), rules=s17_2d).action,
            "DOUBLE",
        )

        # H17 with Surrender: 11 vs A -> DOUBLE; Soft 18 vs 2 -> DOUBLE; Soft 19 vs 6 -> DOUBLE;
        # 15 vs A -> SURRENDER; Hard 17 vs A -> SURRENDER (Soft 17 vs A -> HIT); 8,8 vs A -> SURRENDER
        h17_ls = rules.HouseRules(deck_count=6, dealer_hits_soft_17=True, allow_surrender=True)
        self.assertEqual(
            get_basic_strategy_decision([Card(5), Card(6)], Card(1), rules=h17_ls).action,
            "DOUBLE",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(1), Card(7)], Card(2), rules=h17_ls).action,
            "DOUBLE",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(1), Card(8)], Card(6), rules=h17_ls).action,
            "DOUBLE",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(9), Card(6)], Card(1), rules=h17_ls).action,
            "SURRENDER",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(10), Card(7)], Card(1), rules=h17_ls).action,
            "SURRENDER",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(1), Card(6)], Card(1), rules=h17_ls).action,
            "HIT",
        )
        self.assertEqual(
            get_basic_strategy_decision(
                [Card(8), Card(8)], Card(1), can_split=True, rules=h17_ls
            ).action,
            "SURRENDER",
        )

        # No DAS suppresses DAS-dependent splits
        ndas = rules.HouseRules(allow_das=False)
        self.assertEqual(
            get_basic_strategy_decision([Card(4), Card(4)], Card(6), can_split=True, rules=ndas).action,
            "HIT",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(6), Card(6)], Card(2), can_split=True, rules=ndas).action,
            "HIT",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(6), Card(6)], Card(3), can_split=True, rules=ndas).action,
            "SPLIT",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(2), Card(2)], Card(3), can_split=True, rules=ndas).action,
            "HIT",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(2), Card(2)], Card(4), can_split=True, rules=ndas).action,
            "SPLIT",
        )

        # Double 10_11 restriction falls back Soft 18 vs 5 -> STAND and Hard 9 vs 4 -> HIT
        d10_11 = rules.HouseRules(double_restriction="10_11")
        self.assertEqual(
            get_basic_strategy_decision([Card(1), Card(7)], Card(5), rules=d10_11).action,
            "STAND",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(5), Card(4)], Card(4), rules=d10_11).action,
            "HIT",
        )
        self.assertEqual(
            get_basic_strategy_decision([Card(6), Card(4)], Card(8), rules=d10_11).action,
            "DOUBLE",
        )

    def test_surrender_and_rule_aware_illustrious_18(self):
        counter = HiLoCardCounter(deck_count=4)
        classic = rules.HouseRules()  # 4D S17, allow_surrender=True

        # Late Surrender on 16 vs 10 below index (TC -1.0) must recommend SURRENDER, not HIT
        dev_16_neg = counter.evaluate_hand_deviation(
            [Card(10), Card(6)], Card(10), true_count=-1.0, can_surrender=True, rules=classic
        )
        self.assertIsNotNone(dev_16_neg)
        self.assertEqual(dev_16_neg.recommended_action, "SURRENDER")
        self.assertFalse(dev_16_neg.is_deviation_active)

        # At TC +1.0 (>= 0.0), 16 vs 10 recommends STAND (active I18 deviation)
        dev_16_pos = counter.evaluate_hand_deviation(
            [Card(10), Card(6)], Card(10), true_count=1.0, can_surrender=True, rules=classic
        )
        self.assertEqual(dev_16_pos.recommended_action, "STAND")
        self.assertTrue(dev_16_pos.is_deviation_active)

        # 15 vs 10 at TC +2.0 (< +4.0) with surrender legal -> SURRENDER
        dev_15_below = counter.evaluate_hand_deviation(
            [Card(9), Card(6)], Card(10), true_count=2.0, can_surrender=True, rules=classic
        )
        self.assertEqual(dev_15_below.recommended_action, "SURRENDER")

        # 9 vs 2 suppressed under 10_11 double restriction
        reno = rules.VENUE_PRESETS["reno_single_deck"]
        self.assertIsNone(
            counter.evaluate_hand_deviation(
                [Card(5), Card(4)], Card(2), true_count=3.0, can_double=True, rules=reno
            )
        )

        # 11 vs A active on 4D S17 at TC +1.0, suppressed on H17 / 2D where BS already doubles
        dev_11_4d = counter.evaluate_hand_deviation(
            [Card(5), Card(6)], Card(1), true_count=1.5, can_double=True, rules=classic
        )
        self.assertIsNotNone(dev_11_4d)
        self.assertTrue(dev_11_4d.is_deviation_active)
        self.assertEqual(dev_11_4d.recommended_action, "DOUBLE")

        pitch_2d = rules.VENUE_PRESETS["downtown_pitch"]
        self.assertIsNone(
            counter.evaluate_hand_deviation(
                [Card(5), Card(6)], Card(1), true_count=1.5, can_double=True, rules=pitch_2d
            )
        )

    def test_unified_mit_kelly_bet_target(self):
        counter = HiLoCardCounter(deck_count=4)
        classic = rules.HouseRules()  # $5 min, No Max, 0.50% house edge

        # Bootcamp integer-TC parity on classic_4_deck
        self.assertEqual(counter.get_kelly_bet_target(classic, -1.0, 1000)[:2], (5, 0))
        self.assertEqual(counter.get_kelly_bet_target(classic, 1.0, 1000)[:2], (5, 0))
        self.assertEqual(counter.get_kelly_bet_target(classic, 1.9, 1000)[:2], (5, 0))
        self.assertEqual(counter.get_kelly_bet_target(classic, 2.0, 1000)[:2], (10, 1))
        self.assertEqual(counter.get_kelly_bet_target(classic, 3.0, 1000)[:2], (20, 2))
        self.assertEqual(counter.get_kelly_bet_target(classic, 4.0, 1000)[:2], (40, 3))
        self.assertEqual(counter.get_kelly_bet_target(classic, 5.0, 1000)[:2], (60, 4))

        # 8D H17 6:5 trap (~2.28% house edge) stays flat at 1u ($15) even at TC +3.0
        trap = rules.VENUE_PRESETS["tourist_trap_6_5"]
        bet_tc3, tier_tc3, edge_tc3 = counter.get_kelly_bet_target(trap, 3.0, 1000)
        self.assertLess(edge_tc3, 0.0)
        self.assertEqual((bet_tc3, tier_tc3), (15, 0))

        # Clamping by maximum_bet, multi-seat bankroll split, and $3 odd sub-minimum All-In
        capped = rules.HouseRules(minimum_bet=100, maximum_bet=500)
        self.assertEqual(counter.get_kelly_bet_target(capped, 5.0, 5000)[:2], (500, 4))
        self.assertEqual(counter.get_kelly_bet_target(classic, 5.0, 95, active_seats=3)[:2], (30, 4))
        self.assertEqual(counter.get_kelly_bet_target(capped, 0.0, 3, active_seats=1)[:2], (3, 0))


class TestHeadlessEngineHouseRules(unittest.TestCase):
    """Phase 3 headless BlackjackEngine tests for HouseRules enforcement and shoe lifecycle."""

    def test_apply_house_rules_gating_refund_and_counter_reset(self):
        counter = HiLoCardCounter(deck_count=4)
        counter.observe_card(Card(2))
        self.assertEqual(counter.running_count, 1)

        engine = BlackjackEngine(bankroll=1000, card_counter=counter)
        engine.stage_bet(1, 50)
        self.assertEqual(engine.bankroll, 950)

        # Switching to Downtown 2D Pitch in BETTING refunds staged bet, rebuilds 104-card shoe, resets RC
        pitch = rules.VENUE_PRESETS["downtown_pitch"]
        self.assertTrue(engine.apply_house_rules(pitch))
        self.assertEqual(engine.bankroll, 1000)
        self.assertEqual(engine.staged_bet, 0)
        self.assertEqual(len(engine.shoe), 104)
        self.assertEqual(counter.running_count, 0)
        self.assertEqual(counter.deck_count, 2)

        # Mid-hand rule changes must be rejected
        engine.shoe = [
            Card(8, None, "8", "diamond"),
            Card(10, None, "10", "spade"),
            Card(9, None, "9", "club"),
            Card(6, None, "6", "heart"),
        ]
        engine.deal_round(bet=10)
        self.assertEqual(engine.phase, RoundPhase.PLAYER_TURN)
        self.assertFalse(engine.apply_house_rules(rules.HouseRules()))
        self.assertEqual(engine.house_rules, pitch)

    def test_h17_6_5_payout_and_split_21_settlement_in_engine(self):
        trap = rules.VENUE_PRESETS["tourist_trap_6_5"]  # 8D, H17, 6:5, No DAS, No Surrender, $15 min
        engine = BlackjackEngine(bankroll=1000, rules=trap)

        # Natural Blackjack on $25 pays 6:5 (+$30 profit -> $55 return -> bankroll 1030)
        engine.shoe = [
            Card(7, None, "7", "diamond"),
            Card(10, None, "10", "spade"),
            Card(10, None, "king", "heart"),
            Card(1, None, "ace", "spade"),
        ]
        engine.deal_round(bet=25)
        res_bj = engine.resolve_outcomes()
        self.assertEqual(res_bj[0].outcome, "NATURAL_BLACKJACK")
        self.assertEqual(res_bj[0].payout, 55)
        self.assertEqual(engine.bankroll, 1030)

        # Dealer Soft 17 (A + 6) must HIT under H17 rules (draws 4 -> 21, beating player 20)
        engine.shoe = [
            Card(4, None, "4", "club"),      # dealer H17 hit card -> 21
            Card(6, None, "6", "diamond"),   # dealer hole -> Soft 17
            Card(10, None, "10", "spade") if False else Card(1, None, "ace", "heart"),
        ]
        engine.shoe = [
            Card(4, None, "4", "club"),      # dealer hit -> 21
            Card(1, None, "ace", "diamond"), # dealer hole (6 + A = Soft 17)
            Card(6, None, "6", "spade"),     # dealer upcard
            Card(10, None, "queen", "club"), # player c2
            Card(10, None, "king", "heart"), # player c1 (20)
        ]
        engine.deal_round(bet=25)
        engine.stand(0)
        res_h17 = engine.resolve_outcomes()
        self.assertEqual(len(engine.dealer_hand), 3)
        self.assertEqual(engine.dealer_hand.score, 21)
        self.assertEqual(res_h17[0].outcome, "DEALER_WINS")

        # Post-split A + 10 = 21 settles at 1:1 ($200 return on $100 bet), never 3:2 ($250)
        classic_eng = BlackjackEngine(bankroll=1000, rules=rules.HouseRules())
        classic_eng.shoe = [
            Card(10, None, "10", "club"),    # split hand 2 card 2 -> 21
            Card(10, None, "king", "spade"), # split hand 1 card 2 -> 21
            Card(8, None, "8", "diamond"),   # dealer hole -> 18
            Card(10, None, "10", "heart"),   # dealer upcard
            Card(1, None, "ace", "club"),    # player c2
            Card(1, None, "ace", "spade"),   # player c1
        ]
        classic_eng.deal_round(bet=100)
        h1, h2 = classic_eng.split(0)
        # Split Aces auto-stand at 21 or stand manually
        if classic_eng.phase == RoundPhase.PLAYER_TURN:
            classic_eng.stand(0)
        if classic_eng.phase == RoundPhase.PLAYER_TURN:
            classic_eng.stand(1)
        split_res = classic_eng.resolve_outcomes()
        self.assertEqual(split_res[0].outcome, "PLAYER_WINS")
        self.assertEqual(split_res[0].payout, 200)
        self.assertEqual(split_res[1].outcome, "PLAYER_WINS")
        self.assertEqual(split_res[1].payout, 200)

    def test_reno_restrictions_table_limits_submin_all_in_and_rebuy_gate(self):
        reno = rules.VENUE_PRESETS["reno_single_deck"]  # No DAS, double 10_11 only, no surrender
        eng = BlackjackEngine(bankroll=1000, rules=reno)

        # Soft 19 (A,8) and Hard 9 (5,4) must reject double_down; surrender must raise ValueError
        eng.shoe = [
            Card(8, None, "8", "diamond"),
            Card(6, None, "6", "spade"),
            Card(8, None, "8", "club"),
            Card(1, None, "ace", "heart"),
        ]
        eng.deal_round(bet=20)
        with self.assertRaises(ValueError):
            eng.double_down(0)
        with self.assertRaises(ValueError):
            eng.surrender(0)
        eng.stand(0)
        eng.resolve_outcomes()

        # High-limit table ($250 min, $500 max): stage_bet clamps initial bet at $500,
        # while post-deal double/split can still exceed $500 using remaining bankroll
        high = rules.HouseRules(minimum_bet=250, maximum_bet=500)
        eng_hi = BlackjackEngine(bankroll=2000, rules=high)
        staged = eng_hi.stage_bet(1, 900)
        self.assertEqual(staged, 500)
        self.assertEqual(eng_hi.bankroll, 1500)

        eng_hi.shoe = [
            Card(10, None, "king", "club"),
            Card(7, None, "7", "diamond"),
            Card(10, None, "10", "spade"),
            Card(6, None, "6", "heart"),
            Card(5, None, "5", "club"),
        ]
        eng_hi.deal_round(bet=None)
        eng_hi.double_down(1)
        self.assertEqual(eng_hi.seats[0].hands[0].bet, 1000)
        eng_hi.resolve_outcomes()

        # Sub-minimum bankroll ($150 on $250 min table): rebuy stays locked (> $0),
        # single-seat All-In ($150) is allowed, 2-seat split ($100 + $50) is blocked!
        eng_sub = BlackjackEngine(bankroll=150, rules=high, table_seats=3)
        self.assertEqual(eng_sub.rebuy(1000), 150)  # Locked while round_bankroll > 0!
        eng_sub.stage_bet(1, 100)
        self.assertEqual(eng_sub.stage_bet(2, 50), 0)  # 2nd seat blocked when sub-minimum!
        eng_sub.clear_all_bets()
        self.assertEqual(eng_sub.stage_bet(1, 150), 150)
        self.assertEqual(eng_sub.rebuy(1000), 0)  # Still locked because round_bankroll == 150 > 0!
        eng_sub.commit_staged_bet()

        # Only when round_bankroll == 0 does rebuy unlock
        eng_broke = BlackjackEngine(bankroll=0, rules=high)
        self.assertEqual(eng_broke.rebuy(1000), 1000)

    def test_cut_card_fix_and_1_deck_3_seat_reshuffle(self):
        bus = EventHub()
        reshuffles = []
        bus.subscribe(GameEventType.SHOE_RESHUFFLED, lambda ev: reshuffles.append(ev))

        # 4-deck shoe (208 cards): drawing 4 cards in 1 round leaves 204 cards (> 52 cut card)
        # Must NOT reshuffle prematurely (verifying inverted 1.0 - 0.25 bug is fixed!)
        eng_4d = BlackjackEngine(bankroll=1000, rules=rules.HouseRules(), event_bus=bus)
        eng_4d.deal_round(bet=10)
        if eng_4d.phase == RoundPhase.INSURANCE:
            eng_4d.decline_insurance()
        if eng_4d.phase == RoundPhase.PLAYER_TURN:
            eng_4d.stand(0)
        eng_4d.resolve_outcomes()
        self.assertEqual(len(reshuffles), 0)

        # 1-deck 3-seat shoe depleted to <= 27 cards reshuffles automatically pre-deal
        eng_1d = BlackjackEngine(
            bankroll=1000,
            rules=rules.VENUE_PRESETS["reno_single_deck"],
            event_bus=bus,
            table_seats=3,
        )
        # Pop down to 25 cards (marked as engine shoe)
        while len(eng_1d.shoe) > 25:
            eng_1d.shoe.pop()
        eng_1d.stage_bet(1, 10)
        eng_1d.stage_bet(2, 10)
        eng_1d.stage_bet(3, 10)
        eng_1d.deal_round(bet=None)
        self.assertGreaterEqual(len(reshuffles), 1)
        self.assertGreater(len(eng_1d.shoe), 35)


if __name__ == "__main__":
    unittest.main()
