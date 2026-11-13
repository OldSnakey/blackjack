"""
Unit tests for Track 6 Pure Domain (`tour_domain.py`), Persistence (`save_manager.py`),
and 2.5D Tour Chip Medallions (`ui_chip_renderer.py`).
"""

from __future__ import annotations

import shutil
import tempfile
import tkinter
import unittest
from pathlib import Path

from dealer_actor import CHARACTERS
from save_manager import SaveData, SaveManager, VenueTourProgress
from tour_domain import (
    SALON_SPECS,
    TOP_UP_DRAWDOWN_RATIO,
    TOUR_COORDINATOR_COSTUME,
    TOUR_STARTING_BANKROLL,
    TOUR_VICTORY_TARGET,
    TourSalonSpec,
    apply_forgiving_top_up,
    can_select_salon,
    can_top_up_forgiving,
    evaluate_tour_settlement,
    get_forgiving_checkpoint_floor,
    get_salon_visual_state,
    reset_ironman_run,
    switch_tour_mode,
)
from ui_chip_renderer import GRADE_CHIP_STYLES, draw_25d_grade_medallion


class TestVenueTourDomain(unittest.TestCase):
    """Pure mathematical, progression, and persistence tests for the 8-Salon Casino Venue Tour."""

    def test_salon_specs_integrity_and_spread_bounds(self) -> None:
        """All 8 salons use valid characters, backdrops, 3:2 rules, contiguous brackets, and <= 1:25 spreads."""
        self.assertEqual(len(SALON_SPECS), 8)
        self.assertEqual(TOUR_COORDINATOR_COSTUME, "julian_monte_carlo")
        self.assertEqual(SALON_SPECS[0].entry_bankroll, TOUR_STARTING_BANKROLL)
        self.assertEqual(SALON_SPECS[-1].exit_bankroll, TOUR_VICTORY_TARGET)
        self.assertEqual(TOUR_VICTORY_TARGET, 150000)

        valid_backdrops = {"casino", "creep", "hell", "celestial", "crypt", "cyber", "academy"}
        seen_ids: set[str] = set()

        for idx, spec in enumerate(SALON_SPECS):
            self.assertIsInstance(spec, TourSalonSpec)
            self.assertEqual(spec.index, idx)
            self.assertNotIn(spec.salon_id, seen_ids)
            seen_ids.add(spec.salon_id)

            self.assertIn(spec.dealer_id, CHARACTERS)
            profile = CHARACTERS[spec.dealer_id]
            valid_costumes = {c.costume_id for c in profile.get_costumes()}
            self.assertIn(spec.costume_id, valid_costumes)
            self.assertIn(spec.stage_backdrop_theme, valid_backdrops)

            self.assertGreater(spec.exit_bankroll, spec.entry_bankroll)
            if idx > 0:
                self.assertEqual(spec.entry_bankroll, SALON_SPECS[idx - 1].exit_bankroll)

            self.assertEqual(spec.rules.blackjack_payout, (3, 2))
            self.assertGreaterEqual(spec.rules.minimum_bet, 5)
            self.assertGreater(spec.rules.maximum_bet, spec.rules.minimum_bet)
            # Every salon's HouseRules must survive normalization with zero silent limit coercion
            norm_rules = spec.rules.normalized()
            self.assertEqual(
                (norm_rules.minimum_bet, norm_rules.maximum_bet, norm_rules.deck_count),
                (spec.rules.minimum_bet, spec.rules.maximum_bet, spec.rules.deck_count),
                f"Salon {spec.index + 1} ({spec.name}) limits mutated by HouseRules.normalized()",
            )
            self.assertEqual(norm_rules, spec.rules)

            # Anti-brute-force invariant: every salon profit gap requires at least 10 max bets
            profit_gap = spec.exit_bankroll - spec.entry_bankroll
            self.assertLessEqual(
                spec.rules.maximum_bet * 10,
                profit_gap,
                f"Salon {spec.name} max bet ${spec.rules.maximum_bet} allows <10 max-bet clear of ${profit_gap} gap",
            )

        # Salon 3 Tiffany uses atmospheric "creep" stage backdrop over green felt
        self.assertEqual(SALON_SPECS[2].dealer_id, "tiffany")
        self.assertEqual(SALON_SPECS[2].stage_backdrop_theme, "creep")
        # Salon 8 Uriel uses 1D $500-$5,000 -> $150,000
        self.assertEqual(SALON_SPECS[7].dealer_id, "uriel")
        self.assertEqual(SALON_SPECS[7].rules.deck_count, 1)
        self.assertEqual(SALON_SPECS[7].rules.minimum_bet, 500)
        self.assertEqual(SALON_SPECS[7].rules.maximum_bet, 5000)

    def test_save_manager_venue_tour_roundtrip_and_isolation(self) -> None:
        """VenueTourProgress persists cleanly in SaveData without touching Free-Play bankroll or bailouts."""
        tmp = tempfile.mkdtemp(prefix="bj_tour_dom_")
        try:
            save_path = Path(tmp) / "test_save.json"
            sm = SaveManager(save_path=save_path)
            vt = sm.data.venue_tour
            self.assertIsInstance(vt, VenueTourProgress)
            self.assertEqual(vt.active_mode, "forgiving")
            self.assertEqual(vt.forgiving_bankroll, 500)
            self.assertEqual(vt.ironman_bankroll, 500)

            sm.data.current_bankroll = 2450
            sm.data.highscores.total_bailout_funds = 1000
            vt.active_mode = "ironman"
            vt.forgiving_bankroll = 18250
            vt.forgiving_salons_cleared = 4
            vt.forgiving_selected_idx = 4
            vt.forgiving_rebuys = 2
            vt.ironman_bankroll = 6100
            vt.ironman_stage_idx = 2
            vt.ironman_salons_cleared = 3
            vt.ironman_runs_attempted = 5
            vt.intro_seen = True
            sm.save()

            sm2 = SaveManager(save_path=save_path)
            self.assertEqual(sm2.data.current_bankroll, 2450)
            self.assertEqual(sm2.data.highscores.total_bailout_funds, 1000)
            vt2 = sm2.data.venue_tour
            self.assertEqual(vt2.active_mode, "ironman")
            self.assertEqual(vt2.forgiving_bankroll, 18250)
            self.assertEqual(vt2.forgiving_salons_cleared, 4)
            self.assertEqual(vt2.forgiving_selected_idx, 4)
            self.assertEqual(vt2.forgiving_rebuys, 2)
            self.assertEqual(vt2.ironman_bankroll, 6100)
            self.assertEqual(vt2.ironman_stage_idx, 2)
            self.assertEqual(vt2.ironman_salons_cleared, 3)
            self.assertEqual(vt2.ironman_runs_attempted, 5)
            self.assertTrue(vt2.intro_seen)

            # Malformed values clamp safely
            corrupted = SaveData.from_dict(
                {
                    "venue_tour": {
                        "active_mode": "invalid_mode",
                        "forgiving_bankroll": -999,
                        "forgiving_salons_cleared": 99,
                        "forgiving_selected_idx": -5,
                        "ironman_stage_idx": 42,
                        "ironman_salons_cleared": -3,
                    }
                }
            )
            self.assertEqual(corrupted.venue_tour.active_mode, "forgiving")
            self.assertEqual(corrupted.venue_tour.forgiving_bankroll, 0)
            self.assertEqual(corrupted.venue_tour.forgiving_salons_cleared, 8)
            self.assertEqual(corrupted.venue_tour.forgiving_selected_idx, 0)
            self.assertEqual(corrupted.venue_tour.ironman_stage_idx, 8)
            self.assertEqual(corrupted.venue_tour.ironman_salons_cleared, 0)

            sm2.clear_save()
            self.assertEqual(sm2.data.venue_tour.forgiving_salons_cleared, 0)
            self.assertEqual(sm2.data.venue_tour.ironman_salons_cleared, 0)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_forgiving_frontier_residency_and_anti_camping(self) -> None:
        """Standard Tour unlocks Salon k+1 only when crossing exit_bankroll while seated in Frontier Salon k."""
        vt = VenueTourProgress()

        # Seated in Salon 0 (Training Pit, frontier=0), winning to $1,500 unlocks Salon 1
        res = evaluate_tour_settlement(vt, active_salon_idx=0, new_bankroll=1500)
        self.assertTrue(res.promoted)
        self.assertEqual(res.newly_unlocked_salon_idx, 1)
        self.assertEqual(vt.forgiving_salons_cleared, 1)
        self.assertEqual(vt.forgiving_selected_idx, 1)
        self.assertEqual(vt.forgiving_bankroll, 1500)

        # Replay Salon 0 (Training Pit, 0.28% HE) while frontier is Salon 1 (exit=$4,000):
        # Even if bankroll reaches $4,200 inside Salon 0, Salon 1 was NOT beaten, so frontier stays 1!
        vt.forgiving_selected_idx = 0
        res_camp = evaluate_tour_settlement(vt, active_salon_idx=0, new_bankroll=4200)
        self.assertFalse(res_camp.promoted)
        self.assertEqual(vt.forgiving_salons_cleared, 1)

        # Now step into Frontier Salon 1 (Golden Floor) and settle >= $4,000 -> promotes to Salon 2!
        vt.forgiving_selected_idx = 1
        res_s1 = evaluate_tour_settlement(vt, active_salon_idx=1, new_bankroll=4200)
        self.assertTrue(res_s1.promoted)
        self.assertEqual(res_s1.newly_unlocked_salon_idx, 2)
        self.assertEqual(vt.forgiving_salons_cleared, 2)
        self.assertEqual(vt.forgiving_selected_idx, 2)

        # Replaying Salon 0 when frontier is 3 ($8,000 checkpoint floor) never demotes checkpoint floor
        vt.forgiving_salons_cleared = 3
        vt.forgiving_selected_idx = 0
        self.assertEqual(get_forgiving_checkpoint_floor(vt), 8000)

        # Clearing Salon 7 ($150,000) completes the Standard Tour
        vt.forgiving_salons_cleared = 7
        vt.forgiving_selected_idx = 7
        res_win = evaluate_tour_settlement(
            vt, active_salon_idx=7, new_bankroll=150000, round_start_bankroll=145000
        )
        self.assertTrue(res_win.promoted)
        self.assertTrue(res_win.tour_completed)
        self.assertEqual(vt.forgiving_salons_cleared, 8)
        # Once Standard Tour is completed, all 8 salons remain open for VIP Free-Roam regardless of bankroll
        vt.forgiving_bankroll = 200000
        for idx in range(8):
            self.assertTrue(can_select_salon(vt, idx))

    def test_anti_domino_skip_requires_winning_hand_and_caps_earlier_salon_farming(self) -> None:
        """Blocks farming $150k+ in Salon 1 and losing min-bets in Salons 2-8 to domino-unlock medallions."""
        vt = VenueTourProgress(
            active_mode="forgiving",
            forgiving_salons_cleared=1,  # Frontier is Salon 1 (Golden Floor, exit=$4,000)
            forgiving_selected_idx=1,
            forgiving_bankroll=3500,
        )
        # Below frontier exit_bankroll ($3,500 < $4,000), both Salon 0 and Salon 1 are freely playable
        self.assertTrue(can_select_salon(vt, 0))
        self.assertTrue(can_select_salon(vt, 1))

        # Once bankroll >= frontier exit_bankroll ($4,200 >= $4,000), earlier Salon 0 ropes off
        # so the player cannot farm $150,000 in 0.28%-HE Salon 0; they must play Frontier Salon 1!
        vt.forgiving_bankroll = 4200
        self.assertFalse(can_select_salon(vt, 0))
        self.assertTrue(can_select_salon(vt, 1))
        st0 = get_salon_visual_state(vt, 0)
        self.assertTrue(st0.velvet_rope_promoted)

        # Even inside Frontier Salon 1 with $4,200, LOSING or PUSHING a hand ($4,200 -> $4,190 or $4,200)
        # must NOT promote to Salon 2—player must win net profit on the promoting hand!
        res_loss = evaluate_tour_settlement(
            vt, active_salon_idx=1, new_bankroll=4190, round_start_bankroll=4200
        )
        self.assertFalse(res_loss.promoted)
        self.assertEqual(vt.forgiving_salons_cleared, 1)

        res_push = evaluate_tour_settlement(
            vt, active_salon_idx=1, new_bankroll=4190, round_start_bankroll=4190
        )
        self.assertFalse(res_push.promoted)
        self.assertEqual(vt.forgiving_salons_cleared, 1)

        # Winning a hand ($4,190 -> $4,200) at Frontier Salon 1 legitimately promotes to Salon 2!
        res_win = evaluate_tour_settlement(
            vt, active_salon_idx=1, new_bankroll=4200, round_start_bankroll=4190
        )
        self.assertTrue(res_win.promoted)
        self.assertEqual(vt.forgiving_salons_cleared, 2)
        # Now frontier is Salon 2 (exit=$8,000), and $4,200 < $8,000, so Salons 0..2 are all open again!
        self.assertTrue(can_select_salon(vt, 0))
        self.assertTrue(can_select_salon(vt, 1))
        self.assertTrue(can_select_salon(vt, 2))

    def test_forgiving_top_up_80_pct_drawdown_gate_blocks_hand1_freeroll(self) -> None:
        """Top-Up in Standard Mode requires <= 80% of checkpoint floor (blocking Hand-1 freeroll) and adds chips."""
        self.assertAlmostEqual(TOP_UP_DRAWDOWN_RATIO, 0.80)
        vt = VenueTourProgress(
            active_mode="forgiving",
            forgiving_salons_cleared=7,  # Salon 8 unlocked -> $75,000 checkpoint floor
            forgiving_selected_idx=7,
            forgiving_bankroll=75000,
        )
        self.assertEqual(get_forgiving_checkpoint_floor(vt), 75000)
        self.assertFalse(can_top_up_forgiving(vt))

        # Losing 1 min bet ($74,500) must NOT allow freeroll top-up
        vt.forgiving_bankroll = 74500
        self.assertFalse(can_top_up_forgiving(vt))
        self.assertFalse(apply_forgiving_top_up(vt))
        self.assertEqual(vt.forgiving_bankroll, 74500)
        self.assertEqual(vt.forgiving_rebuys, 0)

        # At exactly 80% ($60,000), Top-Up unlocks and restores $75,000
        vt.forgiving_bankroll = 60000
        self.assertTrue(can_top_up_forgiving(vt))
        self.assertTrue(apply_forgiving_top_up(vt))
        self.assertEqual(vt.forgiving_bankroll, 75000)
        self.assertEqual(vt.forgiving_rebuys, 1)

        # Busting to $0 in Forgiving Mode also allows Top-Up (or auto-top-up on rebuy)
        vt.forgiving_bankroll = 0
        self.assertTrue(can_top_up_forgiving(vt))
        self.assertTrue(apply_forgiving_top_up(vt))
        self.assertEqual(vt.forgiving_bankroll, 75000)
        self.assertEqual(vt.forgiving_rebuys, 2)

    def test_ironman_gauntlet_stamps_velvet_rope_and_bust_preservation(self) -> None:
        """Ironman enforces linear velvet-rope progression, permanent high-water stamps, and $500 reset on bust."""
        vt = VenueTourProgress(active_mode="ironman")
        # Entry != Exit: starting at $500 gives 0 Ironman stamps
        self.assertEqual(vt.ironman_salons_cleared, 0)
        self.assertTrue(can_select_salon(vt, 0))
        self.assertFalse(can_select_salon(vt, 1))

        # Clear Salon 0 ($1,500) and Salon 1 ($4,000)
        r0 = evaluate_tour_settlement(vt, active_salon_idx=0, new_bankroll=1500)
        self.assertTrue(r0.promoted)
        self.assertEqual(vt.ironman_salons_cleared, 1)
        self.assertEqual(vt.ironman_stage_idx, 1)
        # Velvet rope locks Salon 0 once promoted to Salon 1
        self.assertFalse(can_select_salon(vt, 0))
        self.assertTrue(can_select_salon(vt, 1))

        r1 = evaluate_tour_settlement(vt, active_salon_idx=1, new_bankroll=4100)
        self.assertTrue(r1.promoted)
        self.assertEqual(vt.ironman_salons_cleared, 2)
        self.assertEqual(vt.ironman_stage_idx, 2)

        # Busting to $0 in Salon 2 resets active climb to Salon 0 ($500) WITHOUT erasing 2 Ironman stamps!
        rbust = evaluate_tour_settlement(vt, active_salon_idx=2, new_bankroll=0)
        self.assertTrue(rbust.ironman_busted)
        self.assertEqual(vt.ironman_bankroll, 500)
        self.assertEqual(vt.ironman_stage_idx, 0)
        self.assertEqual(vt.ironman_salons_cleared, 2)
        self.assertEqual(vt.ironman_runs_attempted, 1)
        self.assertTrue(can_select_salon(vt, 0))
        self.assertFalse(can_select_salon(vt, 2))

        # Completing Salon 7 ($150,000) in Ironman unlocks Grand Slam VIP Free-Roam across all 8 salons
        vt.ironman_stage_idx = 7
        vt.ironman_salons_cleared = 7
        r7 = evaluate_tour_settlement(vt, active_salon_idx=7, new_bankroll=150000)
        self.assertTrue(r7.promoted)
        self.assertTrue(r7.tour_completed)
        self.assertEqual(vt.ironman_salons_cleared, 8)
        self.assertEqual(vt.ironman_stage_idx, 8)
        self.assertTrue(vt.ironman_completed)
        for idx in range(8):
            self.assertTrue(can_select_salon(vt, idx))

        # Optional fresh Ironman gauntlet run resets stage/bankroll, increments runs_attempted,
        # and preserves 8/8 stamps
        prev_attempts = vt.ironman_runs_attempted
        reset_ironman_run(vt)
        self.assertEqual(vt.ironman_bankroll, 500)
        self.assertEqual(vt.ironman_stage_idx, 0)
        self.assertEqual(vt.ironman_salons_cleared, 8)
        self.assertTrue(vt.ironman_completed)
        self.assertEqual(vt.ironman_runs_attempted, prev_attempts + 1)

    def test_tour_achievements_and_side_bet_financial_quarantine(self) -> None:
        """SaveManager persists tour_champion/ironman_legend and quarantines Tour side-bet highscores."""
        tmp = tempfile.mkdtemp(prefix="bj_tour_ach_")
        try:
            save_path = Path(tmp) / "ach_save.json"
            sm = SaveManager(save_path=save_path)
            self.assertFalse(sm.data.achievements.tour_champion)
            self.assertFalse(sm.data.achievements.ironman_legend)

            # Tour side-bet win unlocks Pair Perfectionist WITHOUT inflating Free-Play biggest_side_bet_win
            sm.record_side_bet(
                "perfect_pairs", "PERFECT_PAIR", bet=5000, profit=125000, won=True, track_financials=False
            )
            self.assertTrue(sm.data.achievements.pair_perfectionist)
            self.assertEqual(sm.data.highscores.biggest_side_bet_win, 0)
            self.assertEqual(sm.data.highscores.side_bets_played, 0)

            self.assertTrue(sm.unlock_achievement("tour_champion"))
            self.assertTrue(sm.unlock_achievement("ironman_legend"))

            sm2 = SaveManager(save_path=save_path)
            self.assertTrue(sm2.data.achievements.tour_champion)
            self.assertTrue(sm2.data.achievements.ironman_legend)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_mode_switch_non_destructive_and_visual_discovery_persistence(self) -> None:
        """Switching Standard <-> Ironman preserves both slots and never reverts discovered salons to '???'."""
        vt = VenueTourProgress(
            active_mode="forgiving",
            forgiving_bankroll=19500,
            forgiving_salons_cleared=4,  # Salons 0..4 discovered in Forgiving
            forgiving_selected_idx=4,
            ironman_bankroll=1800,
            ironman_stage_idx=1,
            ironman_salons_cleared=1,
        )
        switch_tour_mode(vt, "ironman")
        self.assertEqual(vt.active_mode, "ironman")
        self.assertEqual(vt.forgiving_bankroll, 19500)
        self.assertEqual(vt.ironman_bankroll, 1800)

        # Salon 3 was cleared in Forgiving -> stays visually discovered in Ironman (not '???'), though gated
        st3 = get_salon_visual_state(vt, 3)
        self.assertTrue(st3.discovered)
        self.assertTrue(st3.forgiving_cleared)
        self.assertFalse(st3.ironman_cleared)
        self.assertFalse(st3.selectable)

        # Salon 6 has not been reached in either mode -> undiscovered ('???') silhouette
        st6 = get_salon_visual_state(vt, 6)
        self.assertFalse(st6.discovered)
        self.assertFalse(st6.selectable)

        switch_tour_mode(vt, "forgiving")
        self.assertEqual(vt.active_mode, "forgiving")
        self.assertEqual(vt.forgiving_selected_idx, 4)

    def test_25d_tour_chip_medallion_styles_render_cleanly(self) -> None:
        """ui_chip_renderer supports TOUR_GOLD and TOUR_IRONMAN 2.5D medallions with custom stamps."""
        self.assertIn("TOUR_GOLD", GRADE_CHIP_STYLES)
        self.assertIn("TOUR_IRONMAN", GRADE_CHIP_STYLES)

        root = tkinter.Tk()
        root.withdraw()
        try:
            canvas = tkinter.Canvas(root, width=240, height=120)
            gold_items = draw_25d_grade_medallion(
                canvas, 60, 60, "TOUR_GOLD", compact=True, stamp_override="★"
            )
            iron_items = draw_25d_grade_medallion(
                canvas, 160, 60, "TOUR_IRONMAN", compact=True, stamp_override="💀"
            )
            self.assertGreater(len(gold_items), 6)
            self.assertGreater(len(iron_items), 6)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()

