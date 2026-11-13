"""
Integration tests for Track 6 (`BlackjackApp` Tour Mode isolation, +$666 Exorcist bounty,
locked-dealer salon access, per-salon shoe persistence, betting ergonomics, and counting HUD fixes).
"""

from __future__ import annotations

import shutil
import tempfile
import tkinter
import unittest
from pathlib import Path

from blackjack import BlackjackApp
from dealer_wardrobe_dialog import WardrobeDialog
from rules import Card, HouseRules, RoundPhase
from ui_dialogs import SettingsDialog


class TestVenueTourIntegration(unittest.TestCase):
    """Headless integration tests for Casino Venue Tour state isolation and table mechanics."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="bj_tour_int_")
        self.save_path = Path(self.temp_dir) / "test_save.json"
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(
            self.root,
            chips_mode=True,
            sound_enabled=False,
            save_path=self.save_path,
        )
        self.root.update_idletasks()

    def tearDown(self) -> None:
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_exorcist_bounty_666_and_tour_button_unlock_gate(self) -> None:
        """Clearing HELL_TABLE awards +$666 (not +$6,666) and maps tour_button while scale_button stays hidden."""
        self.assertTrue(hasattr(self.app, "tour_button"))
        self.assertFalse(bool(self.app.tour_button.grid_info()))
        self.assertFalse(bool(self.app.scale_button.grid_info()))

        # Shift+T blocked before Exorcist is earned
        self.app._on_tour_shortcut()
        self.assertFalse(getattr(self.app, "tour_active", False))

        start_br = self.app.bankroll_var.get()
        self.app._show_victory_dialog()

        self.assertEqual(self.app.bankroll_var.get(), start_br + 666)
        self.assertIn("+$666", self.app.result_var.get())
        self.assertTrue(self.app.save_manager.data.achievements.exorcist)
        self.assertTrue(bool(self.app.tour_button.grid_info()))
        self.assertFalse(bool(self.app.scale_button.grid_info()))

        # Clearing save data hides tour_button again
        self.app.clear_player_save_data()
        self.assertFalse(bool(self.app.tour_button.grid_info()))

    def test_free_play_bankroll_rules_and_close_isolation(self) -> None:
        """Tour Mode isolates bankroll, HouseRules, bailouts, and _on_close persistence from Free Play."""
        self.app.save_manager.unlock_achievement("exorcist")
        self.app._sync_tour_button()

        custom_fp_rules = HouseRules(
            preset_id="custom",
            deck_count=8,
            dealer_hits_soft_17=True,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=True,
            minimum_bet=15,
            maximum_bet=1000,
        )
        self.assertTrue(self.app.apply_house_rules(custom_fp_rules))
        self.app._set_bankroll(3210)
        self.app.save_manager.data.current_bankroll = 3210
        self.app.save_manager.data.equipped_costume = "tiffany"
        self.app.save_manager.data.highscores.total_bailout_funds = 1000
        self.app.save_manager.save()

        # Advance Standard Tour to Salon 3 (Faculty Club: $8,000, 6D, $50 min)
        vt = self.app.save_manager.data.venue_tour
        vt.forgiving_salons_cleared = 3
        vt.forgiving_selected_idx = 3
        vt.forgiving_bankroll = 8000
        self.app.save_manager.save_venue_tour()

        self.app.enter_venue_tour()
        self.assertTrue(self.app.tour_active)
        self.app.enter_tour_salon(3)
        self.assertTrue(self.app.tour_in_salon)
        self.assertEqual(self.app.bankroll_var.get(), 8000)
        self.assertEqual(self.app.house_rules.deck_count, 6)
        self.assertEqual(self.app.house_rules.minimum_bet, 50)
        self.assertIn("TOUR BANKROLL: $8,000", self.app.bankroll_label.cget("text"))

        # Free-Play saved rules and bankroll remain untouched
        self.assertEqual(self.app.save_manager.data.house_rules["deck_count"], 8)
        self.assertEqual(self.app.save_manager.data.current_bankroll, 3210)

        # Exit Tour back to Free Play -> restores $3,210, 8-deck custom rules, and Tiffany
        self.app.exit_venue_tour()
        self.assertFalse(self.app.tour_active)
        self.assertEqual(self.app.bankroll_var.get(), 3210)
        self.assertEqual(self.app.house_rules.deck_count, 8)
        self.assertEqual(self.app.house_rules.minimum_bet, 15)

        # Verify closing window mid-Tour never overwrites Free-Play current_bankroll
        root2 = tkinter.Tk()
        root2.withdraw()
        try:
            app2 = BlackjackApp(root2, chips_mode=True, sound_enabled=False, save_path=self.save_path)
            app2.enter_venue_tour()
            app2.enter_tour_salon(3)
            app2._set_bankroll(9450)
            app2._on_close()
        finally:
            try:
                if root2.winfo_exists():
                    root2.destroy()
            except Exception:
                pass

        from save_manager import SaveManager

        reloaded = SaveManager(save_path=self.save_path)
        self.assertEqual(reloaded.data.current_bankroll, 3210)
        self.assertEqual(reloaded.data.venue_tour.forgiving_bankroll, 9450)
        self.assertEqual(reloaded.data.highscores.total_bailout_funds, 1000)

    def test_locked_dealers_and_stage_backdrops_work_in_tour_without_permanent_unlock(self) -> None:
        """Tour salons equip locked dealers and custom backdrops over green felt without unlocking them in Free Play."""
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.save_manager.data.unlocked_costumes = ["classic", "tiffany"]
        vt = self.app.save_manager.data.venue_tour
        vt.forgiving_salons_cleared = 4
        vt.forgiving_selected_idx = 4
        vt.forgiving_bankroll = 15000

        self.app.enter_venue_tour()

        # Salon 2 (Downtown Lounge): Tiffany + "creep" stage backdrop + "casino" green table felt
        self.app.enter_tour_salon(2)
        self.assertEqual(self.app.dealer_actor.current_character, "tiffany")
        self.assertEqual(self.app.dealer_stage_canvas.current_theme, "creep")
        self.assertEqual(self.app.card_table_frame.current_theme, "casino")

        # Salon 4 (Bone Vault): Mortimer (locked in Free Play!) + "crypt" stage backdrop + "casino" felt
        self.app.enter_tour_salon(4)
        self.assertEqual(self.app.dealer_actor.current_character, "mortimer")
        self.assertEqual(self.app.dealer_stage_canvas.current_theme, "crypt")
        self.assertEqual(self.app.card_table_frame.current_theme, "casino")
        self.assertNotIn("grim_bones", self.app.save_manager.data.unlocked_costumes)

    def test_mode_guards_settings_and_wardrobe_locks_during_tour(self) -> None:
        """Cursed Stakes, 3-seat mode, Shift+M, Settings rule edits, and Wardrobe equip are guarded in Tour."""
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.haunted.unlocked_cursed_stakes = True
        self.app._sync_cursed_stakes_button()

        self.app.enter_venue_tour()
        self.app.enter_tour_salon(0)

        self.assertFalse(bool(self.app.cursed_stakes_button.grid_info()))
        self.assertEqual(self.app.table_seats, 1)
        self.app.set_table_seats(3)
        self.assertEqual(self.app.table_seats, 1)
        self.app._on_cycle_play_mode_shortcut()
        self.assertTrue(self.app.tour_active)

        # SettingsDialog House Rules & Welcome Screen backdoor locked during Tour
        dlg = SettingsDialog(self.root, self.app)
        try:
            self.assertEqual(str(dlg.apply_rules_btn.cget("state")), "disabled")
            self.assertIn("Tour", dlg.rules_status_var.get())
            dlg._on_open_welcome_screen()
            self.assertIsNone(getattr(self.app, "_welcome_splash_dialog", None))
        finally:
            dlg.destroy()

        # WardrobeDialog equip saves Free-Play preference & marks card equipped without hijacking Tour salon host
        wdlg = WardrobeDialog(self.root, self.app, initial_tab=0)
        try:
            wdlg._equip_costume("tiffany", costume_id="tiffany")
            self.assertEqual(self.app.dealer_actor.current_character, "dummy")
            self.assertEqual(self.app.save_manager.data.equipped_costume, "tiffany")
            self.assertTrue(wdlg.cards["tiffany"]["is_equipped"])
        finally:
            wdlg.destroy()

    def test_per_salon_shoe_persistence_prevents_map_hop_wonging_and_topup_reshuffles(self) -> None:
        """Map-hopping preserves active salon shoe & count; Top-Up at <=80% restores floor and reshuffles."""
        self.app.save_manager.unlock_achievement("exorcist")
        self.app.enter_venue_tour()
        self.app.enter_tour_salon(0)

        initial_len = len(self.app.deck)
        # Play a deterministic hand in Salon 0
        self.app.deck = list(self.app.deck[:-5]) + [
            Card(10, self.app.back_image, rank="10", suit="club"),     # Dealer hole (-1)
            Card(6, self.app.back_image, rank="6", suit="spade"),      # Dealer up (+1) -> 16, draws from deck
            Card(10, self.app.back_image, rank="king", suit="heart"),  # Player c2 (-1)
            Card(10, self.app.back_image, rank="10", suit="spade"),    # Player c1 (-1) -> 20
        ]
        # Ensure dealer bust card below
        self.app.deck.insert(-4, Card(10, self.app.back_image, rank="queen", suit="diamond"))
        self.app._deal_hand_with_bet(10)
        self.app.on_stand()
        while self.app._dealer_timer_id is not None:
            self.app._dealer_step()

        post_hand_len = len(self.app.deck)
        post_hand_rc = self.app.card_counter.running_count
        post_hand_obs = self.app.card_counter.observed_cards_count
        self.assertLess(post_hand_len, initial_len)
        self.assertGreater(post_hand_obs, 0)

        # Hop out to Overworld Map and back into Salon 0 -> exact shoe & count preserved!
        self.app.return_to_tour_map()
        self.app.enter_tour_salon(0)
        self.assertEqual(len(self.app.deck), post_hand_len)
        self.assertEqual(self.app.card_counter.running_count, post_hand_rc)
        self.assertEqual(self.app.card_counter.observed_cards_count, post_hand_obs)

        # Simulate drawdown to $350 (<= 80% of $500 floor) and execute Top-Up -> restores $500 & fresh shoe!
        self.app._set_bankroll(350)
        self.app.save_manager.data.venue_tour.forgiving_bankroll = 350
        self.assertTrue(self.app.top_up_tour_stake())
        self.assertEqual(self.app.bankroll_var.get(), 500)
        self.assertEqual(self.app.card_counter.observed_cards_count, 0)
        self.assertEqual(self.app.card_counter.running_count, 0)
        self.assertEqual(self.app.save_manager.data.highscores.total_bailout_funds, 0)

    def test_ergonomics_spot_min_bet_sidebet_cap_hud_drill_guard_and_tripometer_tag(self) -> None:
        """Center spot stages min_bet from 0, side bets clamp to max_bet, Drill HUD blocks bet leak, and Tripometer tags Tour."""
        self.app.save_manager.unlock_achievement("exorcist")
        vt = self.app.save_manager.data.venue_tour
        vt.forgiving_salons_cleared = 7
        vt.forgiving_selected_idx = 7
        vt.forgiving_bankroll = 75000
        self.app.enter_venue_tour()
        self.app.enter_tour_salon(7)  # Sanctum of Light: 1D, $500 min, $5,000 max

        # 1. Entering Salon 8 auto-stages $500 minimum_bet, and after Clear Bet ($0),
        # clicking center main spot ramps cleanly in 1u ($500) increments!
        self.assertEqual(self.app.current_bet_var.get(), 500)
        self.app._clear_bet()
        self.assertEqual(self.app.current_bet_var.get(), 0)
        self.app._on_main_spot_click(5)
        self.assertEqual(self.app.current_bet_var.get(), 500)
        # Second click adds another 1u ($500 -> $1,000) rather than $5!
        self.app._on_main_spot_click(5)
        self.assertEqual(self.app.current_bet_var.get(), 1000)

        # 2. Side bets clamp at salon maximum_bet ($5,000)
        self.app._add_side_bet("perfect_pairs", 6000)
        self.assertLessEqual(self.app.engine.staged_side_bets.get("perfect_pairs", 0), 5000)
        self.app._clear_bet()

        # 3. Single-deck quarter-deck clamp + CardCountingHud clamped unit display (10u MAX) & Drill Mode felt guard
        self.assertAlmostEqual(self.app.card_counter.decks_remaining(16), 0.31, places=2)
        hud = self.app.card_counting_hud
        hud.set_visible(True)
        self.app.card_counter.running_count = 6  # 52 cards (1.0 deck) -> TC = +6.0 (Tier 4 = 12u -> clamped to $5,000 = 10u)
        hud.update_counts(cards_remaining=52, base_bet=500, bankroll=75000, active_seats=1)
        self.app._refresh_strategy_hint()
        self.assertIn("10u MAX", hud.bet_guide_label.cget("text"))
        self.assertIn("10u MAX", hud.strategy_label.cget("text"))

        hud.set_drill_mode(True, cards_remaining=52, base_bet=500)
        self.app._refresh_strategy_hint()
        self.assertNotIn("$5,000", hud.strategy_label.cget("text"), "Drill mode felt plaque leaked Kelly bet!")
        self.assertIn("DRILL", hud.strategy_label.cget("text"))
        self.assertEqual(self.app.current_bet_var.get(), 0)
        hud._on_stage_bet_click()
        self.assertEqual(self.app.current_bet_var.get(), 0, "Drill mode must never stage hidden Kelly bet!")
        hud.set_drill_mode(False, cards_remaining=52, base_bet=500)

        # 4. Tripometer tags Tour rounds with salon code ("T8 Sanctum")
        self.app.deck = list(self.app.deck[:-4]) + [
            Card(7, self.app.back_image, rank="7", suit="club"),
            Card(10, self.app.back_image, rank="10", suit="spade"),
            Card(10, self.app.back_image, rank="king", suit="heart"),
            Card(10, self.app.back_image, rank="10", suit="diamond"),
        ]
        self.app._deal_hand_with_bet(500)
        self.app.on_stand()
        while self.app._dealer_timer_id is not None:
            self.app._dealer_step()
        recent = self.app.tripometer.data.recent_hands
        self.assertTrue(recent)
        self.assertIn("T8", recent[0].rules_badge)

    def test_ironman_bust_transition_race_never_clobbers_500_reset(self) -> None:
        """Pressing Esc / returning to Map during the 1,500ms post-bust window preserves the $500 reset."""
        self.app.save_manager.unlock_achievement("exorcist")
        vt = self.app.save_manager.data.venue_tour
        vt.active_mode = "ironman"
        vt.ironman_stage_idx = 2
        vt.ironman_salons_cleared = 2
        vt.ironman_bankroll = 400  # All-in in Salon 3 ($25-$400)

        self.app.enter_venue_tour()
        self.app.enter_tour_salon(2)
        self.assertEqual(self.app.house_rules.maximum_bet, 400)
        self.assertIn("IRONMAN", self.app.bankroll_label.cget("text"))

        # Force player loss (19 vs dealer 20) to bust Ironman stack to $0
        self.app.deck = list(self.app.deck[:-4]) + [
            Card(10, self.app.back_image, rank="queen", suit="club"),
            Card(10, self.app.back_image, rank="10", suit="spade"),
            Card(9, self.app.back_image, rank="9", suit="heart"),
            Card(10, self.app.back_image, rank="10", suit="diamond"),
        ]
        self.app._deal_hand_with_bet(400)
        self.app.on_stand()
        while self.app._dealer_timer_id is not None:
            self.app._dealer_step()

        # Immediately after settlement (BEFORE 1,500ms timer fires):
        # 1) new_game_button must stay disabled while _tour_transition_timer_id is pending
        self.assertIsNotNone(self.app._tour_transition_timer_id)
        self.assertEqual(str(self.app.new_game_button.cget("state")), "disabled")
        self.assertEqual(vt.ironman_bankroll, 500)
        self.assertEqual(vt.ironman_salons_cleared, 2)

        # 2) Immediately invoking return_to_tour_map() (simulating Esc / Map click) must NOT overwrite $500 with $0!
        self.assertTrue(self.app.return_to_tour_map())
        self.assertEqual(vt.ironman_bankroll, 500)
        self.assertEqual(vt.ironman_stage_idx, 0)
        self.assertEqual(self.app.tour_frame.focused_salon_idx, 0)


if __name__ == "__main__":
    unittest.main()
