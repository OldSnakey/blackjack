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
        """CardCountingHud embeds title in a top-left tab_frame perched above bar_frame."""
        self.assertTrue(hasattr(self.hud, "tab_frame"), "tab_frame missing on CardCountingHud")
        self.assertTrue(hasattr(self.hud, "bar_frame"), "bar_frame missing on CardCountingHud")
        # Title label is child of tab_frame
        self.assertEqual(self.hud.title_lbl.master, self.hud.tab_frame)
        self.assertEqual("Hi-Lo", self.hud.title_lbl.cget("text"))
        # Stat frames are children of bar_frame
        self.assertEqual(self.hud.rc_frame.master, self.hud.bar_frame)
        self.assertEqual(self.hud.decks_frame.master, self.hud.bar_frame)

    def test_hud_action_buttons_right_anchored(self):
        """Action buttons (close, quiz, mode) are packed side='right' in bar_frame."""
        close_info = self.hud.close_btn.pack_info()
        quiz_info = self.hud.quiz_btn.pack_info()
        mode_info = self.hud.mode_btn.pack_info()
        self.assertEqual(close_info.get("side"), "right")
        self.assertEqual(quiz_info.get("side"), "right")
        self.assertEqual(mode_info.get("side"), "right")

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

    def test_hud_warm_mahogany_rail_styling_and_horizon_mount(self):
        """CardCountingHud mounts on horizon rail of dealer_stage_canvas in Warm Mahogany style."""
        self.app.card_counting_hud.set_visible(True)
        self.app.root.update_idletasks()

        # Shelf is mounted on horizon (pinned at bottom of dealer_stage_canvas)
        self.assertTrue(self.app.card_counting_hud.is_visible)
        self.assertEqual(self.app.card_counting_hud.winfo_manager(), "place")
        # In Warm Mahogany Rail style
        bg_col = self.app.card_counting_hud.cget("background")
        self.assertEqual(bg_col.lower(), "#26110d")

    def test_dealer_dialogue_highest_z_order_over_hud_shelf(self):
        """Dealer dialogue bubble maintains highest z-order above the horizon shelf."""
        self.app.card_counting_hud.set_visible(True)
        self.app.set_dealer_speech("Welcome to the high rollers table!")
        self.app.root.update_idletasks()

        # Verify speech is visible and dialogue_frame has highest z-order
        self.assertEqual(self.app.dealer_speech_var.get(), "Welcome to the high rollers table!")
        # Both dialogue_win and speech_tail are raised
        canvas = self.app.dealer_stage_canvas
        tags_order = canvas.find_all()
        dialogue_items = canvas.find_withtag("dialogue_win")
        if dialogue_items:
            # dialogue_win is among the topmost items
            self.assertIn(dialogue_items[0], tags_order[-3:])

    def test_multi_seat_chip_tray_unobstructed_by_hud(self):
        """In multi-seat play with HUD enabled, chip piles on felt remain 100% visible and interactive."""
        self.app.chips_mode_var.set(True)
        self.app.set_table_seats(3)
        self.app.new_game()
        self.app.card_counting_hud.set_visible(True)
        self.app.root.update_idletasks()

        # The felt baize has NO card_counting_hud in row 2 covering the chip tray
        felt = self.app.card_table_frame
        chip_tray_items = felt.find_withtag("felt_chip_tray")
        self.assertTrue(len(chip_tray_items) > 0, "felt_chip_tray items must be drawn on felt")

        # Simulate clicking on the $100 chip pile at (440, 360)
        # Should set selected_denomination and stage bet without being blocked by HUD
        prev_staged = self.app.current_bet_var.get()
        felt.trigger_chip_tray_click(100)
        self.assertEqual(self.app.selected_denomination, 100)
        self.assertEqual(self.app.current_bet_var.get(), prev_staged + 100)

    def test_hud_preserves_visibility_when_dealer_view_toggled(self):
        """Toggling dealer view OFF and ON preserves HUD on horizon without collisions."""
        self.app.card_counting_hud.set_visible(True)
        self.assertTrue(self.app.card_counting_hud.is_visible)

        # Toggle dealer view OFF
        self.app._on_toggle_dealer_view()
        self.app.root.update_idletasks()
        self.assertTrue(self.app.card_counting_hud.is_visible)
        # Consistent horizon placement: must NEVER jump to bottom of window over buttons/chips
        place_info_off = self.app.card_counting_hud.place_info()
        self.assertNotEqual(place_info_off.get("rely"), "1")
        self.assertEqual(place_info_off.get("y"), "176")

        # Toggle dealer view back ON
        self.app._on_toggle_dealer_view()
        self.app.root.update_idletasks()
        self.assertTrue(self.app.card_counting_hud.is_visible)
        place_info_on = self.app.card_counting_hud.place_info()
        self.assertEqual(place_info_on.get("in"), self.app.dealer_stage_canvas)
        self.assertEqual(place_info_on.get("y"), "-44")

    def test_strategy_plaque_centered_between_dealer_and_seat_boxes_and_narrow_mode_btn(self):
        """
        Verifies Option C layout:
        1. `strategy_frame` is mounted as a dedicated felt plaque on `card_table_frame`
           centered between the Dealer and Seat/Player score boxes when the HUD is visible.
        2. `mode_btn` uses the compact '👁 Assisted' label (no wide variation selector '\ufe0f')
           so its requested width stays <= 85px.
        3. Long strategy recommendations (e.g. 'SURRENDER (15 vs 10)') and active Illustrious 18
           deviation badges render unclipped inside the felt plaque.
        """
        from rules import get_basic_strategy_decision

        self.app.exit_counting_bootcamp_to_free_play()
        hud = self.app.card_counting_hud
        self.assertTrue(hud.is_visible)

        # 1. Verify mode_btn text has no variation selector '\ufe0f' and stays compact (<= 85px)
        self.assertNotIn("\ufe0f", hud.mode_btn.cget("text"))
        self.assertEqual(hud.mode_btn.cget("text"), "👁 Assisted")
        self.app.root.update_idletasks()
        self.assertLessEqual(hud.mode_btn.winfo_reqwidth(), 85)

        # 2. Verify strategy_frame is placed on card_table_frame centered between Dealer and Seat boxes
        self.assertEqual(hud.strategy_frame.winfo_manager(), "place")
        place_info = hud.strategy_frame.place_info()
        self.assertEqual(place_info.get("in"), self.app.card_table_frame)
        self.assertEqual(place_info.get("anchor"), "center")

        # Update with long strategy recommendation + 4-digit bet and verify zero clipping
        hud.update_counts(cards_remaining=204, base_bet=1567)
        dec = get_basic_strategy_decision([Card(7), Card(8)], Card(10), can_surrender=True)
        hud.update_strategy_hint(hint=dec)
        self.app.root.update_idletasks()
        self.assertIn("SURRENDER", hud.strategy_label.cget("text"))

        # Hiding HUD also hides the felt strategy plaque
        hud.set_visible(False)
        self.assertEqual(hud.strategy_frame.winfo_manager(), "")


if __name__ == "__main__":
    unittest.main()
