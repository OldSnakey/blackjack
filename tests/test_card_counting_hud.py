"""
Targeted Automated Test Suite for Card Counting HUD & Trainer Interface.

Verifies:
- CardCountingHud initialization, layout, and placement in the card table felt area.
- Visibility toggling (Shift+C / K hotkey integration).
- Formatting and color coding of Running Count, Decks Remaining, True Count, and Bet Guide.
- FloatingCountBadge creation and lifecycle.
- CardCountingQuizDialog submission, feedback, and streak tracking.
"""

from __future__ import annotations

import tempfile
import tkinter
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from card_counter import HiLoCardCounter
from card_counting_hud import CardCountingHud, CardCountingQuizDialog, FloatingCountBadge
from rules import Card
import blackjack
from blackjack import BlackjackApp


class TestCardCountingHud(unittest.TestCase):
    """Unit tests for CardCountingHud widget and training overlay."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.parent_frame = tkinter.Frame(self.root, bg="#076324")
        self.parent_frame.pack()
        self.counter = HiLoCardCounter(deck_count=6)
        self.hud = CardCountingHud(master=self.parent_frame, counter=self.counter)

    def tearDown(self):
        try:
            self.hud.destroy()
        except Exception:
            pass
        try:
            self.parent_frame.destroy()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_hud_initialization_hidden_by_default(self):
        """CardCountingHud starts hidden until toggled by player."""
        self.assertFalse(self.hud.is_visible)
        self.assertEqual(self.hud.winfo_manager(), "")

    def test_toggle_visibility(self):
        """toggle_visibility maps and unmaps the HUD pill container smoothly."""
        # Toggle on
        state = self.hud.toggle_visibility()
        self.assertTrue(state)
        self.assertTrue(self.hud.is_visible)
        self.assertEqual(self.hud.winfo_manager(), "pack")

        # Toggle off
        state = self.hud.toggle_visibility()
        self.assertFalse(state)
        self.assertFalse(self.hud.is_visible)
        self.assertEqual(self.hud.winfo_manager(), "")

    def test_update_counts_formatting(self):
        """update_counts updates RC, Decks, TC, and Bet Guide labels accurately."""
        self.hud.toggle_visibility()
        self.counter.running_count = 5
        # 156 cards = 3.0 decks -> TC = 5 / 3 = +1.7
        self.hud.update_counts(cards_remaining=156, base_bet=25)

        self.assertIn("+5", self.hud.rc_label.cget("text"))
        self.assertIn("3.0", self.hud.decks_label.cget("text"))
        self.assertIn("+1.7", self.hud.tc_label.cget("text"))
        self.assertIn("50", self.hud.bet_guide_label.cget("text"))  # 2 units for TC ~ 1.7

    def test_floating_count_badge_spawns_and_cleans_up(self):
        """FloatingCountBadge renders tag and schedules destroy callback."""
        badge = FloatingCountBadge(master=self.parent_frame, tag_value=1)
        self.assertIn("+1", badge.cget("text"))
        self.assertEqual(badge.cget("fg"), "#00e676")  # Green for +1

        badge_neg = FloatingCountBadge(master=self.parent_frame, tag_value=-1)
        self.assertIn("-1", badge_neg.cget("text"))
        self.assertEqual(badge_neg.cget("fg"), "#ff5252")  # Red for -1

        badge_zero = FloatingCountBadge(master=self.parent_frame, tag_value=0)
        self.assertIn("0", badge_zero.cget("text"))

        badge.destroy()
        badge_neg.destroy()
        badge_zero.destroy()

    def test_hud_top_tab_and_bar_hierarchy(self):
        """CardCountingHud embeds title + close in tab_frame above vertical bar_frame slate."""
        self.assertTrue(hasattr(self.hud, "tab_frame"), "tab_frame missing on CardCountingHud")
        self.assertTrue(hasattr(self.hud, "bar_frame"), "bar_frame missing on CardCountingHud")
        self.assertEqual(self.hud.title_lbl.master, self.hud.tab_frame)
        self.assertIn("Hi-Lo", self.hud.title_lbl.cget("text"))
        self.assertEqual(self.hud.rc_frame.master, self.hud.stats_grid)
        self.assertEqual(self.hud.decks_frame.master, self.hud.stats_grid)

    def test_hud_vertical_slate_hierarchy_and_compact_width(self):
        """Vertical Counting Slate keeps width <= 210px at 1x and embeds strategy_frame + stage_bet_btn."""
        self.hud.toggle_visibility()
        self.root.update_idletasks()
        self.assertLessEqual(
            self.hud.winfo_reqwidth(),
            210,
            f"Counting Slate reqwidth {self.hud.winfo_reqwidth()} exceeds 210px 1x budget",
        )
        self.assertEqual(self.hud.strategy_frame.master, self.hud.bar_frame)
        self.assertTrue(hasattr(self.hud, "stage_bet_btn"))
        for btn in (self.hud.close_btn, self.hud.quiz_btn, self.hud.mode_btn, self.hud.bootcamp_btn):
            self.assertTrue(btn.winfo_exists())

    def test_strategy_hint_shorthand_length(self):
        """Strategy decisions produce concise shorthand notation under 22 characters."""
        from rules import Card, get_basic_strategy_decision
        # 8,8 split
        dec_88 = get_basic_strategy_decision([Card(8), Card(8)], Card(10), can_split=True)
        self.hud.update_strategy_hint(hint=dec_88)
        text_88 = self.hud.strategy_label.cget("text")
        self.assertIn("SPLIT", text_88)
        self.assertIn("8,8", text_88)
        self.assertLessEqual(len(text_88), 22, f"Strategy text too long: {text_88}")

        # Hard 16 surrender
        dec_16 = get_basic_strategy_decision([Card(10), Card(6)], Card(10), can_surrender=True)
        self.hud.update_strategy_hint(hint=dec_16)
        text_16 = self.hud.strategy_label.cget("text")
        self.assertIn("SURRENDER", text_16)
        self.assertIn("16 vs 10", text_16)
        self.assertLessEqual(len(text_16), 22, f"Strategy text too long: {text_16}")


class TestCardCountingIntegration(unittest.TestCase):
    """Verifies BlackjackApp integration with CardCountingHud and game loop hooks."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.test_dir = tempfile.mkdtemp()
        self.test_save = Path(self.test_dir) / "test_save.json"
        self.app = BlackjackApp(self.root, chips_mode=False, sound_enabled=False, save_path=self.test_save)

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_app_has_card_counter_and_hud(self):
        """BlackjackApp initializes card_counter and card_counting_hud."""
        self.assertTrue(hasattr(self.app, "card_counter"))
        self.assertTrue(hasattr(self.app, "card_counting_hud"))
        self.assertIsInstance(self.app.card_counter, HiLoCardCounter)

    def test_hotkey_toggles_card_counting_hud(self):
        """Pressing 'K' or Shift+C toggles the counting HUD."""
        initial_state = self.app.card_counting_hud.is_visible
        self.app._toggle_card_counting_hud()
        self.assertEqual(self.app.card_counting_hud.is_visible, not initial_state)
        self.app._toggle_card_counting_hud()
        self.assertEqual(self.app.card_counting_hud.is_visible, initial_state)

    def test_hole_card_invariant_on_initial_deal(self):
        """Dealer unrevealed hole card is NOT counted until turned face up."""
        # Ensure fresh shoe
        self.app.card_counter.reset_shoe(deck_count=self.app.deck_count)
        self.assertEqual(self.app.card_counter.running_count, 0)

        # Clear hands and deal specific cards
        player_card1 = Card(value=2, image=None, rank="2", suit="heart")   # +1
        dealer_upcard = Card(value=5, image=None, rank="5", suit="spade")  # +1
        player_card2 = Card(value=10, image=None, rank="10", suit="club")  # -1
        dealer_hole = Card(value=10, image=None, rank="king", suit="heart") # -1 (NOT counted yet!)

        self.app.player_hands[0] = [player_card1, player_card2]
        self.app.dealer_hand = [dealer_upcard, dealer_hole]
        self.app.dealer_hole_card = dealer_hole
        self.app._hole_card_observed = False

        # Process initial cards through counting hook (simulate face-up cards)
        self.app._observe_card_face_up(player_card1)
        self.app._observe_card_face_up(dealer_upcard)
        self.app._observe_card_face_up(player_card2)

        # RC should be (+1) + (+1) + (-1) = +1. Hole card NOT yet observed!
        self.assertEqual(self.app.card_counter.running_count, 1)

        # Reveal dealer hole card
        self.app._reveal_dealer_hole_card()
        # Now hole card is observed: 1 + (-1) = 0
        self.assertEqual(self.app.card_counter.running_count, 0)

    def test_default_deck_count_is_four(self):
        """Default deck count in HiLoCardCounter and CardCountingHud matches the 4-deck shoe."""
        default_counter = HiLoCardCounter()
        self.assertEqual(default_counter.deck_count, 4)
        hud = CardCountingHud(master=self.app.card_table_frame, counter=default_counter)
        self.assertEqual(hud.decks_label.cget("text"), "4.0")
        hud.destroy()

    def test_dealer_step_hit_cards_observed_by_counter(self):
        """Cards drawn by the dealer during _dealer_step() must be observed by the card counter."""
        self.app.card_counter.reset_shoe(deck_count=self.app.deck_count)
        c10 = Card(10, self.app.back_image, rank="10", suit="spade")
        c8 = Card(8, self.app.back_image, rank="8", suit="heart")
        c5 = Card(5, self.app.back_image, rank="5", suit="club")  # +1 tag
        c6 = Card(6, self.app.back_image, rank="6", suit="diamond")  # +1 tag

        # Player stands on 18; Dealer has 10 + 5 = 15 (< 17, must hit) and draws c6 (+1) -> 21
        self.app.player_hands = [[c10, c8]]
        self.app.dealer_hand = [c10, c5]
        self.app.deck = [c6] * 20
        self.app._hole_card_observed = True

        rc_before = self.app.card_counter.running_count
        obs_before = self.app.card_counter.observed_cards_count
        self.app._dealer_step()

        self.assertEqual(self.app.card_counter.observed_cards_count, obs_before + 1)
        self.assertEqual(self.app.card_counter.running_count, rc_before + 1)

    def test_blessing_eye_observes_hole_card_on_deal_without_double_counting(self):
        """When Blessing.EYE is equipped, the revealed hole card is observed on deal and not double-counted on reveal."""
        from haunted_manager import Blessing
        self.app._trigger_hell_table()
        self.app.haunted.equip_blessing(Blessing.EYE)
        self.app.card_counter.reset_shoe(deck_count=self.app.deck_count)

        c2 = Card(2, self.app.back_image, rank="2", suit="heart")  # +1
        self.app.deck = [c2] * 20
        self.app._deal_card_to_dealer(is_hole_card=True)

        self.assertTrue(self.app._hole_card_observed)
        self.assertEqual(self.app.card_counter.running_count, 1)

        # Revealing hole card at round end must NOT count it a second time
        self.app._reveal_dealer_hole_card()
        self.assertEqual(self.app.card_counter.running_count, 1)

    def test_hud_deviation_badge_rendering_and_drill_masking(self):
        """CardCountingHud displays deviation badge on active index plays and hides during drill mode."""
        from card_counter import StrategyDeviation

        self.assertTrue(hasattr(self.app.card_counting_hud, "deviation_badge"))
        hud = self.app.card_counting_hud

        # Initially badge is unmapped
        self.assertFalse(bool(hud.deviation_badge.winfo_manager()))

        # Active deviation badge update
        active_dev = StrategyDeviation(
            rule_id="16_vs_10",
            label="16 vs 10",
            index_tc=0.0,
            recommended_action="STAND",
            basic_action="HIT",
            is_deviation_active=True,
            condition_str="TC >= 0",
            badge_text="⚡ DEVIATION: Stand (TC >= 0)",
        )
        hud.update_strategy_hint(text="Hard 16 vs 10", deviation=active_dev)
        self.assertEqual(hud.deviation_badge.winfo_manager(), "pack")
        self.assertIn("DEVIATION: Stand", hud.deviation_badge.cget("text"))

        # Inactive deviation removes badge
        inactive_dev = StrategyDeviation(
            rule_id="16_vs_10",
            label="16 vs 10",
            index_tc=0.0,
            recommended_action="HIT",
            basic_action="HIT",
            is_deviation_active=False,
            condition_str="TC >= 0",
            badge_text="",
        )
        hud.update_strategy_hint(text="Hard 16 vs 10", deviation=inactive_dev)
        self.assertFalse(bool(hud.deviation_badge.winfo_manager()))

        # When drill mode is active, active deviations are masked
        hud.set_drill_mode(True)
        hud.update_strategy_hint(text="Hard 16 vs 10", deviation=active_dev)
        self.assertFalse(bool(hud.deviation_badge.winfo_manager()))
        hud.set_drill_mode(False)

    def test_card_counting_quiz_dialog_deviation_mode(self):
        """CardCountingQuizDialog supports Deviation Check mode with question options and validation."""
        from card_counter import DeviationQuizQuestion

        q = DeviationQuizQuestion(
            rule_id="16_vs_10",
            true_count=3.0,
            player_hand_desc="16",
            dealer_upcard_desc="10",
            prompt="True Count is +3.0. You hold 16 against Dealer 10. Do you Hit or Stand?",
            options=("HIT", "STAND"),
            correct_action="STAND",
            explanation="Illustrious 18 #2: Stand on 16 vs 10 at TC >= 0 (TC is +3.0).",
        )

        result_payload = []
        def on_quiz_result(is_correct, rc, tc):
            result_payload.append((is_correct, rc, tc))

        dlg = CardCountingQuizDialog(
            parent=self.app.root,
            counter=self.app.card_counter,
            cards_remaining=104,
            on_result=on_quiz_result,
            quiz_mode="deviation",
            deviation_question=q,
        )

        try:
            dlg.update_idletasks()
            dlg.update()
            self.assertIsInstance(dlg, tkinter.Frame)
            self.assertNotIsInstance(dlg, tkinter.Toplevel)
            self.assertLess(dlg.winfo_width(), 1280)
            self.assertLess(dlg.winfo_height(), 800)
            self.assertGreater(int(float(dlg.place_info()["x"])), 0)
            self.assertEqual(dlg.quiz_mode, "deviation")
            self.assertIn("True Count is +3.0", dlg.deviation_prompt_label.cget("text"))
            self.assertIn("STAND", dlg.deviation_choice_buttons)
            self.assertIn("HIT", dlg.deviation_choice_buttons)

            # Submit correct answer: STAND
            dlg.submit_deviation_answer("STAND")
            self.assertEqual(len(result_payload), 1)
            self.assertTrue(result_payload[0][0])
            self.assertIn("Correct", dlg.feedback_var.get())
        finally:
            dlg._on_close()

    def test_card_counting_quiz_dialog_plus_minus_steppers_and_dpad(self):
        """Count Check mode uses controller-friendly +/- stepper buttons (zero Entry text boxes) for RC and TC."""
        self.app.card_counter.reset_shoe(deck_count=4)
        self.app.card_counter.running_count = 3  # With 104 cards (2.0 decks) remaining -> TC = +1.5

        results = []
        dlg = CardCountingQuizDialog(
            parent=self.app.root,
            counter=self.app.card_counter,
            cards_remaining=104,
            on_result=lambda ok, rc, tc: results.append((ok, rc, tc)),
            quiz_mode="count",
        )
        try:
            dlg.update_idletasks()
            dlg.update()

            def _find_entries(w):
                found = [w] if isinstance(w, tkinter.Entry) else []
                for c in w.winfo_children():
                    found.extend(_find_entries(c))
                return found

            # Must have zero blank Entry text boxes
            self.assertEqual(_find_entries(dlg), [])

            # Initial stepper values start cleanly at 0 and +0.0
            self.assertEqual(dlg.rc_val, 0)
            self.assertAlmostEqual(dlg.tc_val, 0.0)
            self.assertEqual(dlg.rc_value_label.cget("text"), "0")
            self.assertEqual(dlg.tc_value_label.cget("text"), "0.0")

            # Test +/- buttons for RC (±1) and TC (±0.5)
            for _ in range(4):
                dlg.rc_plus_btn.invoke()
            self.assertEqual(dlg.rc_val, 4)
            self.assertEqual(dlg.rc_value_label.cget("text"), "+4")

            dlg.rc_minus_btn.invoke()
            self.assertEqual(dlg.rc_val, 3)
            self.assertEqual(dlg.rc_value_label.cget("text"), "+3")

            for _ in range(4):
                dlg.tc_plus_btn.invoke()
            self.assertAlmostEqual(dlg.tc_val, 2.0)
            self.assertEqual(dlg.tc_value_label.cget("text"), "+2.0")

            dlg.tc_minus_btn.invoke()
            self.assertAlmostEqual(dlg.tc_val, 1.5)
            self.assertEqual(dlg.tc_value_label.cget("text"), "+1.5")

            # Verify D-pad Up/Down row focus + Left/Right adjustment
            self.assertEqual(dlg.active_count_field, "tc")  # Focused TC after clicking TC stepper
            dlg.event_generate("<Up>")
            self.assertEqual(dlg.active_count_field, "rc")
            dlg.event_generate("<Left>")
            self.assertEqual(dlg.rc_val, 2)
            dlg.event_generate("<Right>")
            self.assertEqual(dlg.rc_val, 3)

            # Submit exact RC=+3, TC=+1.5 -> Correct!
            dlg.submit_btn.invoke()
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0], (True, 3, 1.5))
            self.assertIn("Correct", dlg.feedback_var.get())
        finally:
            dlg._on_close()

    def test_card_counting_quiz_deviation_mode_dpad_and_keyboard_navigation(self):
        """Deviation Check mode supports Left/Right focus + Enter submit without yanking back to Tab 1, and avoids Mini3x5 labels."""
        self.app.card_counter.reset_shoe(deck_count=4)
        self.app.card_counter.running_count = 6  # TC = +3.0

        results = []
        dlg = CardCountingQuizDialog(
            parent=self.app.root,
            counter=self.app.card_counter,
            cards_remaining=104,
            on_result=lambda ok, rc, tc: results.append(ok),
            quiz_mode="deviation",
        )
        try:
            dlg.update_idletasks()
            dlg.update()
            self.assertEqual(dlg.quiz_mode, "deviation")
            # Pressing Left/Right cycles deviation choices instead of switching back to 'count' mode!
            dlg.event_generate("<Right>")
            self.assertEqual(dlg.quiz_mode, "deviation")
            self.assertEqual(dlg.focused_deviation_idx, 1)
            dlg.event_generate("<Left>")
            self.assertEqual(dlg.quiz_mode, "deviation")
            self.assertEqual(dlg.focused_deviation_idx, 0)

            # Pressing Return submits the focused deviation choice
            dlg.event_generate("<Return>")
            self.assertEqual(len(results), 1)
        finally:
            if dlg.winfo_exists():
                dlg._on_close()

    def test_app_integration_deviation_hint_and_insurance(self):
        """BlackjackApp computes active deviation hints for hand play and insurance."""
        # 1. 16 vs 10 with TC >= 0
        c10 = Card(10, self.app.back_image, rank="10", suit="spade")
        c6 = Card(6, self.app.back_image, rank="6", suit="heart")
        self.app.player_hands = [[c10, c6]]
        self.app.dealer_hand = [c10, Card(5, self.app.back_image, rank="5", suit="club")]
        self.app.deck = [c10] * 104  # 2 decks
        self.app.card_counter.running_count = 2  # TC = +1.0 >= 0
        self.app.round_phase = blackjack.RoundPhase.PLAYER_TURN

        dev_hint = self.app.get_current_deviation_hint()
        self.assertIsNotNone(dev_hint)
        self.assertTrue(dev_hint.is_deviation_active)
        self.assertEqual(dev_hint.recommended_action, "STAND")

        # Refresh strategy hint updates HUD
        self.app.card_counting_hud.set_visible(True)
        self.app._refresh_strategy_hint()
        self.assertTrue(bool(self.app.card_counting_hud.deviation_badge.winfo_manager()))
        self.assertIn("DEVIATION: Stand", self.app.card_counting_hud.deviation_badge.cget("text"))

        # 2. Insurance phase with TC >= +3
        cA = Card(1, self.app.back_image, rank="ace", suit="diamond")
        self.app.dealer_hand = [cA, c10]
        self.app.is_insurance_phase = True
        self.app.card_counter.running_count = 8  # 104 cards = 2 decks -> TC = +4.0 >= +3.0

        ins_dev = self.app.get_current_deviation_hint()
        self.assertIsNotNone(ins_dev)
        self.assertTrue(ins_dev.is_deviation_active)
        self.assertEqual(ins_dev.recommended_action, "INSURANCE")
        self.app.is_insurance_phase = False

    def test_hud_warm_mahogany_slate_in_left_felt_wing_and_edge_tab(self):
        """CardCountingHud mounts in LeftFeltWing with collapsed [Count (K)] tab and zero felt reflow."""
        hud = self.app.card_counting_hud
        self.app.root.update_idletasks()
        felt_h_before = self.app.card_table_frame.winfo_reqheight()

        # When collapsed, [Count (K)] edge tab is mapped in left_felt_wing
        hud.set_visible(False)
        self.app.root.update_idletasks()
        self.assertFalse(hud.is_visible)
        self.assertTrue(hasattr(hud, "edge_tab_btn"))
        self.assertTrue(bool(hud.edge_tab_btn.winfo_manager()))
        self.assertIn("Count", hud.edge_tab_btn.cget("text"))

        # Expanding Slate hides edge tab, maps Slate in left_felt_wing, and preserves felt height
        hud.set_visible(True)
        self.app.root.update_idletasks()
        self.assertTrue(hud.is_visible)
        self.assertFalse(bool(hud.edge_tab_btn.winfo_manager()))
        self.assertEqual(hud.master, self.app.counting_wing_slot)
        self.assertEqual(hud.master.master, self.app.left_felt_wing)
        self.assertEqual(hud.cget("background").lower(), "#26110d")
        max_w = 210 * self.app.display_profile.art_scale
        self.assertLessEqual(hud.winfo_reqwidth(), max_w)
        self.assertEqual(self.app.card_table_frame.winfo_reqheight(), felt_h_before)

    def test_dealer_dialogue_highest_z_order_over_hud_shelf(self):
        """Dealer dialogue bubble renders cleanly on DealerStageCanvas with zero stage overlap from Counting Slate."""
        self.app.card_counting_hud.set_visible(True)
        self.app.set_dealer_speech("Welcome to the high rollers table!")
        self.app.root.update_idletasks()

        self.assertEqual(self.app.dealer_speech_var.get(), "Welcome to the high rollers table!")
        canvas = self.app.dealer_stage_canvas
        tags_order = canvas.find_all()
        dialogue_items = canvas.find_withtag("dialogue_win")
        if dialogue_items:
            self.assertIn(dialogue_items[0], tags_order[-3:])

    def test_multi_seat_chip_tray_unobstructed_by_hud(self):
        """In multi-seat play with HUD enabled, chip piles and Seat 3 spots remain 100% unobstructed."""
        self.app.chips_mode_var.set(True)
        self.app.set_table_seats(3)
        self.app.new_game()
        self.app.card_counting_hud.set_visible(True)
        self.app.root.update_idletasks()

        felt = self.app.card_table_frame
        chip_tray_items = felt.find_withtag("felt_chip_tray")
        self.assertTrue(len(chip_tray_items) > 0, "felt_chip_tray items must be drawn on felt")

        prev_staged = self.app.current_bet_var.get()
        felt.trigger_chip_tray_click(100)
        self.assertEqual(self.app.selected_denomination, 100)
        self.assertEqual(self.app.current_bet_var.get(), prev_staged + 100)

    def test_hud_preserves_visibility_when_dealer_view_toggled(self):
        """Retired _on_toggle_dealer_view() is a safe no-op keeping dealer_view_var True and Slate stable."""
        self.app.card_counting_hud.set_visible(True)
        self.assertTrue(self.app.card_counting_hud.is_visible)

        self.app._on_toggle_dealer_view()
        self.app.root.update_idletasks()
        self.assertTrue(self.app.dealer_view_var.get())
        self.assertTrue(self.app.card_counting_hud.is_visible)
        self.assertEqual(self.app.card_counting_hud.master, self.app.counting_wing_slot)
        self.assertEqual(self.app.card_counting_hud.master.master, self.app.left_felt_wing)

    def test_strategy_section_embedded_in_slate_and_cancel_floating_badges(self):
        """
        Verifies:
        1. `strategy_frame` is embedded inside `CardCountingHud.bar_frame` in LeftFeltWing.
        2. `mode_btn` has no wide variation selector '\\ufe0f'.
        3. Long strategy recommendations and Illustrious 18 badges keep Slate width <= 210 * art_scale.
        4. `cancel_floating_badges()` destroys tracked FloatingCountBadge widgets immediately.
        """
        from rules import get_basic_strategy_decision

        self.app.exit_counting_bootcamp_to_free_play()
        hud = self.app.card_counting_hud
        self.assertTrue(hud.is_visible)

        self.assertNotIn("\ufe0f", hud.mode_btn.cget("text"))
        self.assertEqual(hud.strategy_frame.master, hud.bar_frame)

        hud.update_counts(cards_remaining=204, base_bet=1567)
        dec = get_basic_strategy_decision([Card(7), Card(8)], Card(10), can_surrender=True)
        hud.update_strategy_hint(hint=dec)
        self.app.root.update_idletasks()
        self.assertIn("SURRENDER", hud.strategy_label.cget("text"))
        self.assertLessEqual(hud.winfo_reqwidth(), 210 * self.app.display_profile.art_scale)

        badge = hud.spawn_floating_badge(master=self.app.card_table_frame, tag_value=1, x=300, y=200)
        self.assertTrue(badge.winfo_exists())
        hud.cancel_floating_badges()
        self.assertFalse(badge.winfo_exists())

    def test_counting_slate_stage_btn_disabled_mid_hand_and_hell_table_hides_tab(self):
        """[Stage] disables mid-hand; entering HELL_TABLE maps SoulMeterCanvas and hides [Count (K)] tab."""
        from haunted_manager import Phase

        self.app.exit_counting_bootcamp_to_free_play()
        self.app.set_table_seats(1)
        self.app.new_game()
        hud = self.app.card_counting_hud
        hud.set_visible(True)
        self.assertEqual(str(hud.stage_bet_btn.cget("state")), "normal")

        self.app._add_chip_bet(25)
        c10 = self.app.all_cards[0]
        c8 = Card(8, c10.image, rank="8", suit="spade")
        c6 = Card(6, c10.image, rank="6", suit="heart")
        self.app.deck[-4:] = [c6, c6, c8, c8]
        self.app._deal_hand_with_bet()
        self.assertEqual(str(hud.stage_bet_btn.cget("state")), "disabled")

        self.app.haunted.start_hell_table()
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.assertTrue(bool(self.app.soul_meter_canvas.grid_info()))
        self.assertFalse(bool(self.app.chip_visualizer.grid_info()))
        self.assertFalse(hud.is_visible)
        self.assertFalse(bool(hud.edge_tab_btn.winfo_manager()))

        hud.set_visible(False)
        self.assertEqual(hud.winfo_manager(), "")


if __name__ == "__main__":
    unittest.main()
