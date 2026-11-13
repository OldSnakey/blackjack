"""
Headless Tkinter GUI & Geometry test suite for Configurable House Rules & Persistent Strategy Tripometer.
Covers:
- TableFeltCanvas rule text, 6-tuple _felt_cache keys, and TableAnnouncementHUD payout banner formatting.
- ui_layout.DEFAULT_UI_CONFIG parity with assets/ui_config.json for top_bar.elements.trip_button.
- CardCountingHud rule/Kelly target synchronization and click-to-stage parity (1-seat & 3-seat).
- Two-tab SettingsDialog ([1] Table & Audio | [2] House Rules): default Tab 0 parity, keyboard tab navigation,
  >= 100px button widths via recursive traversal, staged draft edits until Apply Rules, mid-hand rule lock,
  and Reset Data clearing both house_rules and tripometer.
- Top-bar trip_button bounds within 900px window width, mid-hand count privacy, and T hotkey guards.
- 1-seat sub-minimum All-In & rebuy gating, 1-seat on_surrender() Tripometer finalization, and Haunted ungraded rounds.
- TripometerDialog lifecycle, dynamic height clamping, auto-hiding scrollbar, and confirmation-guarded Reset Trip.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import tkinter
import unittest
from pathlib import Path
from unittest.mock import patch

import blackjack
import config
import ui_layout
from blackjack import BlackjackApp
from haunted_manager import Blessing, Phase
from rules import Card, HouseRules, RoundPhase, VENUE_PRESETS
from ui_dialogs import SettingsDialog


def extract_widgets(parent: tkinter.Misc, widget_type: type = tkinter.Widget) -> list[tkinter.Widget]:
    """Recursively collect descendant widgets matching widget_type."""
    found: list[tkinter.Widget] = []
    if isinstance(parent, widget_type):
        found.append(parent)
    for child in parent.winfo_children():
        found.extend(extract_widgets(child, widget_type))
    return found


class TestHouseRulesAndTripometerGUI(unittest.TestCase):
    """Headless GUI verification for House Rules & Strategy Tripometer."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp(prefix="bj_hr_trip_gui_")
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

    # ------------------------------------------------------------------
    # 1. Declarative Layout & Felt Canvas / Banner Parity
    # ------------------------------------------------------------------
    def test_ui_layout_trip_button_parity_with_json(self) -> None:
        """DEFAULT_UI_CONFIG and assets/ui_config.json both define top_bar.elements.trip_button."""
        json_cfg = json.loads(ui_layout.UI_CONFIG_FILE.read_text(encoding="utf-8"))
        json_trip = json_cfg["top_bar"]["elements"].get("trip_button")
        default_trip = ui_layout.DEFAULT_UI_CONFIG["top_bar"]["elements"].get("trip_button")
        self.assertIsNotNone(json_trip)
        self.assertEqual(json_trip, default_trip)
        self.assertEqual(json_trip["row"], 0)
        self.assertEqual(json_trip["column"], 10)

    def test_table_felt_cache_keys_and_announcement_payout_banner(self) -> None:
        """TableFeltCanvas caches by 6-tuple including payout_ratio and dealer_hits_soft_17."""
        felt = self.app.card_table_frame
        felt.canvas_width = 900
        felt.canvas_height = 400
        felt._redraw_felt()
        s17_32_keys = [k for k in felt._felt_cache.keys() if len(k) == 6]
        self.assertTrue(s17_32_keys, "Expected 6-tuple _felt_cache keys on TableFeltCanvas")
        key_32 = (felt.current_theme, 900, 400, felt.scale_factor, (3, 2), False)
        self.assertIn(key_32, felt._felt_cache)
        img_32 = felt._felt_cache[key_32][0]

        felt.set_house_rules_display((6, 5), True)
        felt._redraw_felt()
        key_65 = (felt.current_theme, 900, 400, felt.scale_factor, (6, 5), True)
        self.assertIn(key_65, felt._felt_cache)
        img_65 = felt._felt_cache[key_65][0]
        self.assertNotEqual(img_32.tobytes(), img_65.tobytes())

        hud = self.app.table_hud
        hud.set_payout_ratio((3, 2))
        hud.set_message("BLACKJACK!")
        self.assertEqual(hud.outcome_label.cget("text"), "BLACKJACK! 3:2")

        hud.set_payout_ratio((6, 5))
        hud.set_message("BLACKJACK!")
        self.assertEqual(hud.outcome_label.cget("text"), "BLACKJACK! 6:5")

    # ------------------------------------------------------------------
    # 2. CardCountingHud Kelly Synchronization & Click-to-Stage
    # ------------------------------------------------------------------
    def test_card_counting_hud_kelly_sync_and_click_to_stage(self) -> None:
        """CardCountingHud bet_guide_label matches get_kelly_bet_target and stages exact bet."""
        high_limit = HouseRules(
            preset_id="custom",
            deck_count=2,
            dealer_hits_soft_17=False,
            blackjack_payout=(3, 2),
            allow_das=True,
            double_restriction="any",
            allow_surrender=True,
            minimum_bet=25,
            maximum_bet=500,
        )
        self.assertTrue(self.app.apply_house_rules(high_limit))
        self.app.apply_play_mode("training")
        # Force RC=+8 with 104 cards (2.0 decks) -> TC = +4.0
        self.app.card_counter.running_count = 8
        self.app.card_counting_hud.update_counts(
            cards_remaining=104,
            bankroll=self.app._get_gui_round_bankroll(),
            active_seats=1,
        )
        expected_bet, _, _ = self.app.card_counter.get_kelly_bet_target(
            high_limit, 4.0, self.app._get_gui_round_bankroll(), active_seats=1
        )
        self.assertIn(f"${expected_bet:,}", self.app.card_counting_hud.bet_guide_label.cget("text"))

        # Clicking bet_guide_label in 1-seat mode stages expected_bet
        self.app.card_counting_hud._on_stage_bet_click()
        self.assertEqual(self.app.current_bet_var.get(), expected_bet)

        # Verify 3-seat click-to-stage stages on focused_betting_seat
        self.app.set_table_seats(3)
        self.app.focused_betting_seat = 2
        self.app.card_counter.running_count = 8
        self.app.card_counting_hud.update_counts(
            cards_remaining=104,
            bankroll=self.app._get_gui_round_bankroll(),
            active_seats=3,
        )
        expected_3s, _, _ = self.app.card_counter.get_kelly_bet_target(
            high_limit, 4.0, self.app._get_gui_round_bankroll(), active_seats=3
        )
        self.app.card_counting_hud._on_stage_bet_click()
        seat2 = self.app.engine.get_seat(2)
        self.assertIsNotNone(seat2)
        self.assertEqual(seat2.main_bet, expected_3s)

    # ------------------------------------------------------------------
    # 3. Top-Bar trip_button Geometry, Count Privacy & T Hotkey Guards
    # ------------------------------------------------------------------
    def test_top_bar_trip_button_bounds_privacy_and_hotkey_guards(self) -> None:
        """trip_button fits within 900px, updates only between rounds, and guards T hotkey."""
        self.assertTrue(hasattr(self.app, "trip_button"))
        self.root.geometry("900x700")
        self.root.deiconify()
        self.root.update_idletasks()
        self.root.update()
        right_edge = self.app.scoreboard_frame.winfo_reqwidth()
        self.assertLessEqual(right_edge, 900)
        self.root.withdraw()

        initial_text = self.app.trip_button.cget("text")
        self.assertEqual(initial_text, "📊 Trip")

        # Start a deterministic round and make a mid-hand decision: button text MUST NOT change mid-hand
        self.app.current_bet_var.set(10)
        self.app.deck = list(self.app.deck) + [
            Card(5, self.app.back_image, rank="5", suit="club"),       # Hit card -> 17
            Card(7, self.app.back_image, rank="7", suit="diamond"),    # Dealer hole -> 17
            Card(10, self.app.back_image, rank="10", suit="heart"),    # Dealer up -> 10
            Card(7, self.app.back_image, rank="7", suit="spade"),      # Player c2 -> 12
            Card(5, self.app.back_image, rank="5", suit="heart"),      # Player c1 -> 5
        ]
        self.app._deal_hand_with_bet(10)
        self.assertEqual(self.app.round_phase, RoundPhase.PLAYER_TURN)

        # Hotkey T blocked while _dealing=True
        self.app._dealing = True
        self.app._on_tripometer_shortcut()
        self.assertIsNone(getattr(self.app, "_tripometer_dialog", None))
        self.app._dealing = False

        # Hotkey T blocked while bootcamp_active=True
        self.app.bootcamp_active = True
        self.app._on_tripometer_shortcut()
        self.assertIsNone(getattr(self.app, "_tripometer_dialog", None))
        self.app.bootcamp_active = False

        # Mid-hand hit records decision in ephemeral buffer, keeping trip_button unchanged
        self.app.on_hit()
        self.assertEqual(self.app.trip_button.cget("text"), "📊 Trip")

        # Concluding the round updates trip_button at ROUND_OVER
        self.app.on_stand()
        if self.app._dealer_timer_id is not None:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
            self.app._dealer_step()
        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        self.assertIn("%", self.app.trip_button.cget("text"))

        # Hotkey T blocked when SettingsDialog is open
        self.app._open_settings_dialog()
        self.assertIsNotNone(self.app._settings_dialog)
        self.app._on_tripometer_shortcut()
        self.assertIsNone(getattr(self.app, "_tripometer_dialog", None))
        self.app._settings_dialog._on_close()

        # Hotkey T opens TripometerDialog when unblocked
        self.app._on_tripometer_shortcut()
        self.assertIsNotNone(self.app._tripometer_dialog)
        self.assertTrue(self.app._tripometer_dialog.winfo_exists())
        self.app._on_escape_key()
        self.assertIsNone(self.app._tripometer_dialog)

    # ------------------------------------------------------------------
    # 4. Two-Tab SettingsDialog: Staged Rules, Button Widths & Mid-Hand Lock
    # ------------------------------------------------------------------
    def test_settings_dialog_two_tabs_button_widths_and_staged_apply(self) -> None:
        """SettingsDialog supports 2 tabs, >=100px buttons, staged Apply Rules, and mid-hand lock."""
        dlg = SettingsDialog(self.root, self.app)
        dlg.update_idletasks()
        dlg.update()
        try:
            self.assertEqual(dlg.active_tab, 0)
            max_allowed_h = min(
                self.root.winfo_screenheight() - 80,
                int(config.DEFAULT_WINDOW_HEIGHT * getattr(self.app, "scale_factor", 1.0)),
            )
            self.assertLessEqual(dlg.winfo_height(), max_allowed_h)

            # Keyboard tab switching
            dlg._on_next_tab()
            dlg.update_idletasks()
            dlg.update()
            self.assertEqual(dlg.active_tab, 1)

            dlg._switch_tab(0)
            self.assertEqual(dlg.active_tab, 0)

            # Verify every visible tkinter.Button across both tabs has rendered width >= 100px
            for tab_idx in (0, 1):
                dlg._switch_tab(tab_idx)
                dlg.update_idletasks()
                dlg.update()
                buttons = extract_widgets(dlg, tkinter.Button)
                mapped_buttons = [b for b in buttons if b.winfo_ismapped()]
                self.assertGreater(len(mapped_buttons), 0)
                for btn in mapped_buttons:
                    self.assertGreaterEqual(
                        btn.winfo_width(),
                        100,
                        f"Tab {tab_idx} button '{btn.cget('text')}' width {btn.winfo_width()} < 100px",
                    )

            # Verify all 6 Casino Venue Preset buttons map to VENUE_PRESETS and stage rules when clicked
            dlg._switch_tab(1)
            self.assertEqual(set(dlg._preset_buttons.keys()), set(VENUE_PRESETS.keys()))
            for pid, expected_preset in VENUE_PRESETS.items():
                dlg._preset_buttons[pid].invoke()
                self.assertEqual(
                    dlg._draft_rules,
                    expected_preset,
                    f"Clicking preset button '{pid}' did not stage VENUE_PRESETS['{pid}']",
                )

            # Stage Tourist Trap 6:5 on Tab 1 without clicking Apply Rules -> app.house_rules unchanged
            dlg._preset_buttons["tourist_trap_6_5"].invoke()
            self.assertEqual(self.app.house_rules, HouseRules())
            self.assertEqual(dlg._draft_rules.blackjack_payout, (6, 5))
            self.assertEqual(dlg._draft_rules.minimum_bet, 15)

            # Clicking Apply Rules commits rules to app and SaveManager
            dlg._on_apply_house_rules()
            self.assertEqual(self.app.house_rules, VENUE_PRESETS["tourist_trap_6_5"])
            self.assertEqual(self.app.save_manager.get_house_rules(), VENUE_PRESETS["tourist_trap_6_5"])
            self.assertEqual(self.app.deck_count, 8)
            self.assertEqual(self.app.card_table_frame.payout_ratio, (6, 5))
            self.assertTrue(self.app.card_table_frame.dealer_hits_soft_17)

            # Reset Data clears both house_rules and tripometer
            self.app.tripometer.data.hands_recorded = 5
            self.app.tripometer.data.bs_total_decisions = 5
            with patch.object(dlg, "_ask_confirm_clear_save", return_value=True):
                dlg._on_click_clear_save()
            self.assertEqual(self.app.house_rules, HouseRules())
            self.assertEqual(self.app.tripometer.data.hands_recorded, 0)
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

        # Verify mid-hand lock disables apply_rules_btn during PLAYER_TURN
        self.app.current_bet_var.set(10)
        self.app.deck = list(self.app.deck) + [
            Card(7, self.app.back_image, rank="7", suit="diamond"),
            Card(10, self.app.back_image, rank="10", suit="heart"),
            Card(5, self.app.back_image, rank="5", suit="spade"),
            Card(6, self.app.back_image, rank="6", suit="heart"),
        ]
        self.app._deal_hand_with_bet(10)
        self.assertEqual(self.app.round_phase, RoundPhase.PLAYER_TURN)

        locked_dlg = SettingsDialog(self.root, self.app)
        try:
            locked_dlg._switch_tab(1)
            locked_dlg.update_idletasks()
            self.assertEqual(str(locked_dlg.apply_rules_btn.cget("state")), "disabled")
            self.assertFalse(self.app.apply_house_rules(VENUE_PRESETS["reno_single_deck"]))
        finally:
            if locked_dlg.winfo_exists():
                locked_dlg._on_close()

    # ------------------------------------------------------------------
    # 5. Sub-Minimum All-In, Surrender Telemetry & Haunted Ungraded Rounds
    # ------------------------------------------------------------------
    def test_sub_minimum_all_in_and_rebuy_gate_in_gui(self) -> None:
        """GUI allows $3 All-In under $5 min and $40 All-In under $100 min while locking rebuy > $0."""
        high_min = HouseRules(minimum_bet=100, maximum_bet=1000)
        self.app.apply_house_rules(high_min)
        self.app.bankroll_var.set(40)
        self.app.engine.bankroll = 40
        self.app._enter_betting_phase()

        # Rebuy MUST remain disabled when round_bankroll == $40 > 0
        self.assertEqual(str(self.app.rebuy_button.cget("state")), "disabled")
        self.app._rebuy()
        self.assertEqual(self.app.bankroll_var.get(), 40)

        # All-In stages $40 and enables Deal Bet
        self.app._all_in()
        self.assertEqual(self.app.current_bet_var.get(), 40)
        self.assertEqual(str(self.app.deal_bet_button.cget("state")), "normal")

        # Odd $3 remainder under $5 minimum also stages cleanly via All-In
        self.app.apply_house_rules(HouseRules(minimum_bet=5))
        self.app.bankroll_var.set(3)
        self.app.engine.bankroll = 3
        self.app._enter_betting_phase()
        self.assertEqual(str(self.app.rebuy_button.cget("state")), "disabled")
        self.app._all_in()
        self.assertEqual(self.app.current_bet_var.get(), 3)
        self.assertEqual(str(self.app.deal_bet_button.cget("state")), "normal")

    def test_1seat_surrender_finalizes_tripometer_and_haunted_stays_ungraded(self) -> None:
        """1-seat on_surrender commits Tripometer decision & P&L; Haunted rounds stay ungraded."""
        self.app.tripometer.reset()
        # Force TC = -1 so 16 vs 10 optimal action is SURRENDER
        self.app.card_counter.running_count = -4
        self.app.deck = list(self.app.deck) + [
            Card(7, self.app.back_image, rank="7", suit="diamond"),    # Dealer hole
            Card(10, self.app.back_image, rank="10", suit="heart"),    # Dealer up -> 10
            Card(6, self.app.back_image, rank="6", suit="spade"),      # Player c2 -> 16
            Card(10, self.app.back_image, rank="10", suit="club"),     # Player c1 -> 10
        ]
        self.app.current_bet_var.set(10)
        self.app._deal_hand_with_bet(10)
        self.assertEqual(self.app.round_phase, RoundPhase.PLAYER_TURN)

        self.app.on_surrender()
        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        self.assertEqual(self.app.tripometer.data.hands_recorded, 1)
        self.assertEqual(self.app.tripometer.data.bs_total_decisions, 1)
        self.assertEqual(self.app.tripometer.data.bs_optimal_decisions, 1)
        self.assertEqual(self.app.tripometer.data.trip_net_profit, -5)

        # Now deal a round with Blessing.SHIELD active -> recorded as ungraded_reason == "haunted"
        self.app.haunted.equipped_blessings.add(Blessing.SHIELD)
        self.app.new_game()
        self.app.deck = list(self.app.deck) + [
            Card(7, self.app.back_image, rank="7", suit="diamond"),
            Card(10, self.app.back_image, rank="10", suit="spade"),
            Card(8, self.app.back_image, rank="8", suit="heart"),
            Card(10, self.app.back_image, rank="10", suit="club"),
        ]
        self.app.current_bet_var.set(10)
        self.app._deal_hand_with_bet(10)
        self.app.on_stand()
        if self.app._dealer_timer_id is not None:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
            self.app._dealer_step()

        self.assertEqual(self.app.tripometer.data.hands_recorded, 1)
        self.assertEqual(self.app.tripometer.data.bs_total_decisions, 1)
        self.assertEqual(self.app.tripometer.data.trip_net_profit, -5)
        self.assertEqual(self.app.tripometer.data.recent_hands[0].ungraded_reason, "haunted")

    # ------------------------------------------------------------------
    # 6. TripometerDialog Lifecycle, Auto-Hiding Scrollbar & Reset Trip
    # ------------------------------------------------------------------
    def test_tripometer_dialog_scroll_clamping_and_isolated_reset(self) -> None:
        """TripometerDialog clamps height, auto-hides/shows scrollbar, and resets only Tripometer."""
        from ui_dialogs import TripometerDialog

        self.app.tripometer.reset()
        empty_dlg = TripometerDialog(self.root, self.app)
        empty_dlg.update_idletasks()
        empty_dlg.update()
        try:
            max_allowed_h = min(
                self.root.winfo_screenheight() - 80,
                int(config.DEFAULT_WINDOW_HEIGHT * getattr(self.app, "scale_factor", 1.0)),
            )
            self.assertLessEqual(empty_dlg.winfo_height(), max_allowed_h)
            self.assertFalse(empty_dlg.v_scrollbar.winfo_ismapped())

            labels = [w.cget("text") for w in extract_widgets(empty_dlg, tkinter.Label)]
            joined = "\n".join(labels)
            self.assertIn("N/A", joined)

            # Verify 3 2.5D chip grading medallions render in the empty state
            empty_chip_canvases = [
                c
                for c in extract_widgets(empty_dlg.scroll_content, tkinter.Canvas)
                if len(c.find_withtag("grade_medallion")) > 0
            ]
            self.assertEqual(len(empty_chip_canvases), 3)
            for c in empty_chip_canvases:
                self.assertGreaterEqual(len(c.find_withtag("grade_medallion")), 18)
                self.assertGreater(len(c.find_withtag("grade_medallion_N/A")), 0)
        finally:
            if empty_dlg.winfo_exists():
                empty_dlg._on_close()

        # Populate 24 optimal hands + 1 mistake hand so content overflows and filter is testable
        for idx in range(24):
            self.app.tripometer.begin_round(HouseRules(), -0.5, {0: 5}, 1000, chips_mode=True)
            self.app.tripometer.record_decision(
                0, 0, [(10, "♠"), (6, "♥")], (10, "♦"), "SURRENDER", -0.5, False, True, True
            )
            self.app.tripometer.finalize_round(
                [
                    {
                        "seat_idx": 0,
                        "hand_idx": 0,
                        "wager": 5,
                        "cards": [(10, "♠"), (6, "♥")],
                        "outcome": "PLAYER_WINS",
                        "net_profit": 5,
                    }
                ],
                [(10, "♦"), (7, "♣")],
                net_round_profit=5,
            )

        # Record 1 mistake hand (HIT instead of SURRENDER on 16 vs 10 + OVERBET)
        self.app.tripometer.begin_round(HouseRules(), -1.0, {0: 100}, 1000, chips_mode=True)
        self.app.tripometer.record_decision(
            0, 0, [(10, "♠"), (6, "♥")], (10, "♦"), "HIT", -1.0, False, True, True
        )
        self.app.tripometer.finalize_round(
            [
                {
                    "seat_idx": 0,
                    "hand_idx": 0,
                    "wager": 100,
                    "cards": [(10, "♠"), (6, "♥"), (9, "♣")],
                    "outcome": "DEALER_WINS",
                    "net_profit": -100,
                }
            ],
            [(10, "♦"), (8, "♣")],
            net_round_profit=-100,
        )

        self.app.save_manager.data.highscores.total_hands_played = 42
        bankroll_before = self.app.bankroll_var.get()

        pop_dlg = TripometerDialog(self.root, self.app)
        pop_dlg.geometry("820x460")
        pop_dlg.update_idletasks()
        pop_dlg.update()
        try:
            self.assertTrue(pop_dlg.v_scrollbar.winfo_ismapped())
            pop_dlg.canvas.yview_scroll(2, "units")

            # Verify 3 2.5D chip grading medallions render in the populated state without clipping
            pop_chip_canvases = [
                c
                for c in extract_widgets(pop_dlg.scroll_content, tkinter.Canvas)
                if len(c.find_withtag("grade_medallion")) > 0
            ]
            self.assertEqual(len(pop_chip_canvases), 3)
            for c in pop_chip_canvases:
                self.assertGreaterEqual(len(c.find_withtag("grade_medallion")), 18)
                bx1, by1, bx2, by2 = c.bbox("grade_medallion")
                self.assertGreaterEqual(bx2 - bx1, 60)
                self.assertGreaterEqual(by2 - by1, 42)
                self.assertGreaterEqual(bx1, 0)
                self.assertGreaterEqual(by1, 0)
                self.assertLessEqual(bx2, int(c.cget("width")))
                self.assertLessEqual(by2, int(c.cget("height")))

            # Verify crisp pixel typography (>= 16px, zero synthetic bold smearing) & human-readable labels
            all_labels = extract_widgets(pop_dlg, tkinter.Label)
            self.assertGreater(len(all_labels), 0)
            combined_text = "\n".join(str(lbl.cget("text")) for lbl in all_labels)
            self.assertNotIn("PLAYER_WINS", combined_text)
            self.assertNotIn("DEALER_WINS", combined_text)
            self.assertNotIn("✗", combined_text)

            for lbl in all_labels:
                parts = pop_dlg.tk.splitlist(lbl.cget("font"))
                f_family = str(parts[0]) if len(parts) > 0 else ""
                f_size = abs(int(parts[1])) if len(parts) > 1 else 0
                f_weight = str(parts[2]).lower() if len(parts) > 2 else "normal"
                self.assertGreaterEqual(
                    f_size,
                    16,
                    f"Tripometer label '{lbl.cget('text')}' font size {f_size}px < 16px minimum",
                )
                if "boldpixels" not in f_family.lower():
                    self.assertEqual(
                        f_weight,
                        "normal",
                        f"Tripometer label '{lbl.cget('text')}' ({f_family}) uses synthetic '{f_weight}' on pixel font",
                    )

            # Verify all mapped buttons have rendered width >= 100px
            mapped_btns = [b for b in extract_widgets(pop_dlg, tkinter.Button) if b.winfo_ismapped()]
            self.assertGreaterEqual(len(mapped_btns), 4)
            for btn in mapped_btns:
                self.assertGreaterEqual(
                    btn.winfo_width(),
                    100,
                    f"Tripometer button '{btn.cget('text')}' width {btn.winfo_width()} < 100px",
                )

            # Verify Mistakes Only filter isolates the 1 mistake hand and All Hands restores all 25
            pop_dlg.filter_mistakes_btn.invoke()
            pop_dlg.update_idletasks()
            self.assertEqual(pop_dlg.filter_mode, "mistakes")
            self.assertEqual(len(pop_dlg._rendered_hand_frames), 1)

            pop_dlg.filter_all_btn.invoke()
            pop_dlg.update_idletasks()
            self.assertEqual(pop_dlg.filter_mode, "all")
            self.assertEqual(len(pop_dlg._rendered_hand_frames), 25)

            # Paired Done + Reset Trip on same footer row
            self.assertIs(pop_dlg.done_btn.master, pop_dlg.reset_trip_btn.master)
            done_grid = pop_dlg.done_btn.grid_info()
            reset_grid = pop_dlg.reset_trip_btn.grid_info()
            self.assertEqual(done_grid["row"], reset_grid["row"])
            self.assertNotEqual(done_grid["column"], reset_grid["column"])

            # Cancelled confirmation leaves Tripometer intact
            with patch.object(pop_dlg, "_ask_confirm_reset_trip", return_value=False):
                pop_dlg._on_click_reset_trip()
            self.assertEqual(self.app.tripometer.data.hands_recorded, 25)

            # Confirmed Reset Trip zeroes Tripometer while preserving career HighScores & bankroll
            with patch.object(pop_dlg, "_ask_confirm_reset_trip", return_value=True):
                pop_dlg._on_click_reset_trip()
            self.assertEqual(self.app.tripometer.data.hands_recorded, 0)
            self.assertEqual(len(self.app.tripometer.data.recent_hands), 0)
            self.assertEqual(self.app.save_manager.data.highscores.total_hands_played, 42)
            self.assertEqual(self.app.bankroll_var.get(), bankroll_before)
            self.assertEqual(self.app.trip_button.cget("text"), "📊 Trip")
        finally:
            if pop_dlg.winfo_exists():
                pop_dlg._on_close()


if __name__ == "__main__":
    unittest.main()
