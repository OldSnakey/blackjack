"""
Unit test suite for Haunted Halloween Slow-Burn & Hell's Table Mode.

Validates:
- Phase progression: NORMAL (1-6) -> CREEP (7-12) -> OMEN (13).
- 5-Candle snuffing lifecycle on round loss.
- Transition into Hell's Table mode at 0 candles with 25% starting soul meter.
- Tug-of-War calculations: win pushes (+15%), loss pulls (-15%), blackjacks (+30%).
- All 7 Balatro-style Angelic Blessings:
  - Seraph's Grace (Ace flexibility)
  - Eye of Providence (Hole card reveal)
  - Archangel's Smite (+25% soul push on 21)
  - Cherub's Shield (22 bust protection -> 21)
  - Heavenly Tithe (Safe split/double)
  - Miracle Draw (Card banish/redraw)
  - Hallowed Run (Streak compounding multiplier)
- Milestone drafting at 50% and 75% soul meter.
- Victory resolution (+6,666, Exorcist badge, Cursed Stakes unlock).
- Immutability of standard Casual and Casino gameplay when Haunted Mode is inactive.
"""

from __future__ import annotations

import unittest
from haunted_manager import HauntedManager, Phase, Blessing


class TestHauntedManager(unittest.TestCase):
    """Verifies core state machine transitions, math, and blessing powers headlessly."""

    def setUp(self):
        self.mgr = HauntedManager()

    def test_initial_state(self):
        """Newly initialized game must begin in NORMAL phase with 0 hands and 5 candles."""
        self.assertEqual(self.mgr.phase, Phase.NORMAL)
        self.assertEqual(self.mgr.hand_counter, 0)
        self.assertEqual(self.mgr.candles_remaining, 5)
        self.assertEqual(len(self.mgr.equipped_blessings), 0)

    def test_phase_progression_hands_1_to_13(self):
        """Hands 1-6 are NORMAL; 7-12 are CREEP; 13 is OMEN."""
        # Hands 1 to 6
        for i in range(1, 7):
            phase = self.mgr.on_new_hand()
            self.assertEqual(phase, Phase.NORMAL, f"Hand {i} should be NORMAL")
            self.assertEqual(self.mgr.hand_counter, i)

        # Hands 7 to 12
        for i in range(7, 13):
            phase = self.mgr.on_new_hand()
            self.assertEqual(phase, Phase.CREEP, f"Hand {i} should be CREEP")
            self.assertEqual(self.mgr.hand_counter, i)

        # Hand 13
        phase = self.mgr.on_new_hand()
        self.assertEqual(phase, Phase.OMEN, "Hand 13 must be OMEN")
        self.assertEqual(self.mgr.hand_counter, 13)

    def test_candle_snuffing_on_loss(self):
        """Lost hands in OMEN / SNUFFING extinguish candles from 5 down to 0."""
        # Advance to Hand 13
        for _ in range(13):
            self.mgr.on_new_hand()

        self.assertEqual(self.mgr.phase, Phase.OMEN)
        self.assertEqual(self.mgr.candles_remaining, 5)

        # Win a hand -> candles remain untouched
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertEqual(self.mgr.candles_remaining, 5)

        # Lose 4 hands -> candles extinguish 4, 3, 2, 1
        for expected in (4, 3, 2, 1):
            self.mgr.on_round_outcome("DEALER_WINS")
            self.assertEqual(self.mgr.candles_remaining, expected)
            self.assertEqual(self.mgr.phase, Phase.SNUFFING)

        # 5th loss -> all candles out, triggers HELL_TABLE!
        self.mgr.on_round_outcome("PLAYER_BUST")
        self.assertEqual(self.mgr.candles_remaining, 0)
        self.assertEqual(self.mgr.phase, Phase.HELL_TABLE)
        self.assertAlmostEqual(self.mgr.soul_meter, 0.25)

    def test_tug_of_war_combat_math(self):
        """In Hell's Table, winning pushes soul meter, losing pulls it back."""
        self.mgr.start_hell_table()
        self.assertEqual(self.mgr.phase, Phase.HELL_TABLE)
        self.assertAlmostEqual(self.mgr.soul_meter, 0.25)

        # Win -> pushes +15%
        delta, msg = self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.40)
        self.assertEqual(self.mgr.consecutive_wins, 1)

        # Loss -> pulls -15%
        delta, msg = self.mgr.on_round_outcome("DEALER_WINS")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.25)
        self.assertEqual(self.mgr.consecutive_wins, 0)

        # Natural Blackjack -> +30%
        delta, msg = self.mgr.on_round_outcome("NATURAL_BLACKJACK")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.55)

    def test_milestone_draft_triggers(self):
        """Crossing 50% and 75% thresholds flags a pending Angelic Draft."""
        self.mgr.start_hell_table()
        self.assertAlmostEqual(self.mgr.soul_meter, 0.25)
        # Initial draft granted upon entering Hell Table
        self.assertTrue(self.mgr.is_draft_pending)
        initial_choices = self.mgr.get_draft_choices(count=3)
        self.mgr.equip_blessing(initial_choices[0])
        self.assertFalse(self.mgr.is_draft_pending)

        # First win: 0.25 -> 0.40 (no milestone)
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertFalse(self.mgr.is_draft_pending)

        # Second win: 0.40 -> 0.55 (crosses 0.50 milestone!)
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertTrue(self.mgr.is_draft_pending)
        self.assertIn(0.50, self.mgr.claimed_milestones)

        # Claim draft
        choices = self.mgr.get_draft_choices(count=3)
        self.assertEqual(len(choices), 3)
        self.mgr.equip_blessing(choices[0])
        self.assertFalse(self.mgr.is_draft_pending)

        # Win two more: crosses 0.75 milestone!
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertTrue(self.mgr.is_draft_pending)
        self.assertIn(0.75, self.mgr.claimed_milestones)

    def test_blessing_cherub_shield(self):
        """Cherub's Shield converts a bust score of 22 into a 21."""
        self.mgr.start_hell_table()
        # Without shield
        self.assertEqual(self.mgr.modify_player_score(22), 22)

        # With shield
        self.mgr.equip_blessing(Blessing.SHIELD)
        self.assertEqual(self.mgr.modify_player_score(22), 21)
        self.assertEqual(self.mgr.modify_player_score(23), 23)

    def test_blessing_archangel_smite(self):
        """Archangel's Smite adds +25% bonus soul push on Natural Blackjack."""
        self.mgr.start_hell_table()
        # Without smite: Natural Blackjack pushes +30%
        self.mgr.on_round_outcome("NATURAL_BLACKJACK")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.55)

        # Reset and equip smite: 0.25 + 0.30 + 0.25 = 0.80!
        self.mgr.soul_meter = 0.25
        self.mgr.equip_blessing(Blessing.SMITE)
        self.mgr.on_round_outcome("NATURAL_BLACKJACK")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.80)

    def test_blessing_hallowed_run_streak(self):
        """Hallowed Run grants +5% compounding bonus per consecutive win."""
        self.mgr.start_hell_table()
        self.mgr.equip_blessing(Blessing.STREAK)

        # Win 1: base +15% + 0% (streak 0 before win) -> 0.40
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.40)
        self.assertEqual(self.mgr.consecutive_wins, 1)

        # Win 2: base +15% + (1 * 5%) = +20% -> 0.60
        self.mgr.on_round_outcome("PLAYER_WINS")
        self.assertAlmostEqual(self.mgr.soul_meter, 0.60)
        self.assertEqual(self.mgr.consecutive_wins, 2)

    def test_victory_and_rewards(self):
        """Pushing Soul Meter to 1.0 triggers VICTORY and unlocks permanent rewards."""
        self.mgr.start_hell_table()
        self.mgr.soul_meter = 0.90
        self.mgr.on_round_outcome("PLAYER_WINS")

        self.assertGreaterEqual(self.mgr.soul_meter, 1.0)
        self.assertEqual(self.mgr.phase, Phase.VICTORY)
        self.assertTrue(self.mgr.unlocked_exorcist)
        self.assertTrue(self.mgr.unlocked_cursed_stakes)
        self.assertTrue(self.mgr.unlocked_haunted_deck)

    def test_defeat_and_second_chance(self):
        """Dropping Soul Meter to 0.0 triggers DEFEAT; second chance restores to 25%."""
        self.mgr.start_hell_table()
        self.mgr.soul_meter = 0.10
        self.mgr.on_round_outcome("DEALER_WINS")

        self.assertLessEqual(self.mgr.soul_meter, 0.0)
        self.assertEqual(self.mgr.phase, Phase.DEFEAT)

        # Player takes Second Chance
        self.mgr.second_chance()
        self.assertEqual(self.mgr.phase, Phase.HELL_TABLE)
        self.assertAlmostEqual(self.mgr.soul_meter, 0.25)


import tkinter
from blackjack import BlackjackApp, Card, StoryDialogueDialog, TABLE_BACKGROUND_COLOR, PANEL_BACKGROUND_COLOR


class TestHauntedGui(unittest.TestCase):
    """Validates GUI integration of Haunted Halloween features, dealer toggle, accessories, and relics."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root, sound_enabled=False, chips_mode=False)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.app._on_close()
        except tkinter.TclError:
            pass

    def test_scoreboard_buttons_and_layout(self):
        """Dealer view is always enabled; cursed stakes button is docked in button_frame left of chips mode."""
        self.assertTrue(hasattr(self.app, "dealer_view_button"))
        self.assertTrue(hasattr(self.app, "cursed_stakes_button"))
        self.assertTrue(self.app.dealer_view_var.get())
        # Dealer toggle button is omitted from visible grid
        self.assertFalse(bool(self.app.dealer_view_button.grid_info()))

        # Cursed stakes button belongs to button_frame and is hidden until unlocked
        self.assertEqual(self.app.cursed_stakes_button.master, self.app.button_frame)
        self.assertFalse(bool(self.app.cursed_stakes_button.grid_info()))


        # When revealed, it grids at row 0, column 8
        self.app.cursed_stakes_button.grid()
        info_stakes = self.app.cursed_stakes_button.grid_info()
        self.assertEqual(info_stakes["row"], 0)
        self.assertEqual(info_stakes["column"], 8)

    def test_dealer_view_toggle(self):
        """Dealer view is always enabled and cannot be disabled."""
        self.assertTrue(self.app.dealer_view_var.get())
        self.app._on_toggle_dealer_view()
        self.assertTrue(self.app.dealer_view_var.get())


    def test_soul_meter_and_accessories_initialized(self):
        """SoulMeterCanvas, candle bar, and gravestones frame must be initialized."""
        self.assertTrue(hasattr(self.app, "soul_meter_canvas"))
        self.assertTrue(hasattr(self.app, "candle_bar_frame"))
        self.assertTrue(hasattr(self.app, "gravestones_frame"))
        self.assertTrue(hasattr(self.app, "miracle_button"))

        # Soul meter defaults to 25%
        self.assertAlmostEqual(self.app.soul_meter_canvas.current_value, 0.25)

    def test_hell_table_forces_dealer_view_and_fiend(self):
        """Entering Hell's Table forces dealer view ON and displays Pit Fiend."""
        self.app._trigger_hell_table()
        self.assertEqual(self.app.haunted.phase, Phase.HELL_TABLE)
        self.assertTrue(self.app.dealer_view_var.get())
        self.assertEqual(self.app.dealer_view_status_var.get(), "☠ The Pit Fiend")
        self.assertEqual(str(self.app.dealer_view_button.cget("state")), "disabled")

    def test_hand_13_deals_card_13_with_clock_chime(self):
        """On hand 13, player's 2nd card is Card 13 (Skulls)."""
        # App begins on Hand 1 in __init__
        self.assertEqual(self.app.haunted.hand_counter, 1)

        # Advance to Hand 12 (call new_game 11 more times)
        for _ in range(11):
            self.app.new_game()

        self.assertEqual(self.app.haunted.hand_counter, 12)

        # Ensure player receives non-bust cards (e.g. 5) so hand stays active in Phase.OMEN
        c5 = next(c for c in self.app.all_cards if c.value == 5)
        self.app.deck = [c5] * 20 + [c5, c5, c5]

        # Deal Hand 13
        self.app.new_game()
        self.assertEqual(self.app.haunted.hand_counter, 13)
        self.assertEqual(self.app.haunted.phase, Phase.OMEN)
        # Player has 2 cards, second card must be card 13
        p_hand = self.app.player_hands[0]
        self.assertEqual(len(p_hand), 2)
        self.assertEqual(p_hand[1].value, 13)
        self.assertEqual(p_hand[1].rank, "thirteen")
        self.assertEqual(str(self.app.hit_button.cget("state")), "normal")
        self.assertEqual(str(self.app.stand_button.cget("state")), "normal")

    def test_cherub_shield_gui_scoring(self):
        """When equipped, Cherub's Shield evaluates player hand score of 22 as 21."""
        self.app._trigger_hell_table()
        self.app.haunted.equip_blessing(Blessing.SHIELD)

        # Create dummy hand totaling 22 (e.g. 10 + 6 + 6)
        hand = [(10, None), (6, None), (6, None)]
        score = self.app._score_player_hand(hand)
        self.assertEqual(score, 21)

    def test_eye_of_providence_reveals_dealer_hole_card(self):
        """When equipped, Eye of Providence reveals dealer hole card immediately."""
        self.app._trigger_hell_table()
        self.app.haunted.equip_blessing(Blessing.EYE)
        self.app.new_game()

        self.assertIsNotNone(self.app.dealer_hole_widget)
        # Eye of Providence shows the actual card face, not back.png
        self.assertEqual(str(self.app.dealer_hole_widget.cget("image")), str(self.app.dealer_hole_card[1]))

    def test_hand_13_bust_on_deal_concludes_round_and_enables_new_game(self):
        """If dealt Card 13 and score > 21, round must conclude, snuff a candle, and enable New Game."""
        # Advance to Hand 12
        for _ in range(11):
            self.app.new_game()
        self.assertEqual(self.app.haunted.hand_counter, 12)

        # Ensure next dealt card to player is a 10 so 10 + 13 = 23, and dealer gets 2 + 5 = 7
        card_10 = next(c for c in self.app.all_cards if c.value == 10)
        card_2 = next(c for c in self.app.all_cards if c.value == 2)
        card_5 = next(c for c in self.app.all_cards if c.value == 5)
        self.app.deck = [card_5] * 20 + [card_5, card_2, card_10]

        # Deal Hand 13
        self.app.new_game()
        self.assertEqual(self.app.haunted.hand_counter, 13)

        # Check player hand and score
        p_score = self.app._score_player_hand(self.app.player_hands[0])
        self.assertEqual(p_score, 23)

        # All action buttons must be disabled, and new_game_button must be normal!
        self.assertEqual(str(self.app.hit_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.stand_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.double_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.split_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.surrender_button.cget("state")), "disabled")
        self.assertEqual(str(self.app.new_game_button.cget("state")), "normal")

        # Candle count must have dropped from 5 to 4 and gravestone risen
        self.assertEqual(self.app.haunted.candles_remaining, 4)
        self.assertEqual(self.app.haunted.gravestones_risen, 1)

        # Result string mentions clock chime, bust, and extinguished candle
        result_text = self.app.result_var.get()
        self.assertIn("13 of Skulls", result_text)
        self.assertIn("bust", result_text.lower())
        self.assertIn("candle dies", result_text.lower())

        # Dealer hole card must have been revealed face up
        self.assertEqual(str(self.app.dealer_hole_widget.cget("image")), str(self.app.dealer_hole_card[1]))

        # Starting hand 14 must succeed without error
        self.app.new_game()
        self.assertEqual(self.app.haunted.hand_counter, 14)

    def test_hand_13_bust_in_chips_mode_resolves_and_enables_next_round(self):
        """In Chips Mode, busting with Card 13 deducts bet, snuffs candle, and enables New Game/betting."""
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode(confirm=True)

        # Advance to Hand 12
        while self.app.haunted.hand_counter < 12:
            self.app.current_bet_var.set(10)
            self.app._deal_hand_with_bet()
            self.app.new_game()

        self.assertEqual(self.app.haunted.hand_counter, 12)

        # Start Hand 13 betting phase
        self.app.new_game()
        self.assertEqual(self.app.haunted.hand_counter, 13)

        # Stage bet of $50 for Hand 13
        card_10 = next(c for c in self.app.all_cards if c.value == 10)
        card_2 = next(c for c in self.app.all_cards if c.value == 2)
        card_5 = next(c for c in self.app.all_cards if c.value == 5)
        self.app.deck = [card_5] * 20 + [card_5, card_2, card_10]
        self.app.current_bet_var.set(50)
        bankroll_before = self.app.bankroll_var.get()
        self.app._deal_hand_with_bet()

        self.assertEqual(self.app.haunted.hand_counter, 13)
        self.assertEqual(self.app._score_player_hand(self.app.player_hands[0]), 23)

        # Bankroll should have lost the $50 bet
        self.assertEqual(self.app.bankroll_var.get(), bankroll_before - 50)
        self.assertEqual(self.app.haunted.candles_remaining, 4)

        # New game button enabled so player can proceed to hand 14
        self.assertEqual(str(self.app.new_game_button.cget("state")), "normal")
        self.app.new_game()
        self.assertEqual(self.app.haunted.hand_counter, 14)

    def test_table_announcement_hud_integration(self):
        """Verifies TableAnnouncementHUD reflects outcomes and lore during haunted play."""
        self.app.result_var.set("Dealer wins! (Total: 20) | ☠ Candle snuffed! 4 candles remain.")
        self.root.update_idletasks()
        self.assertEqual(self.app.announcement_hud.outcome_label.cget("text"), "Dealer wins! (Total: 20)")
        self.assertEqual(self.app.announcement_hud.lore_label.cget("text"), "☠ Candle snuffed! 4 candles remain.")
        self.assertEqual(self.app.announcement_hud.outcome_label.cget("fg").lower(), "#ff5252")
        self.assertEqual(self.app.announcement_hud.lore_label.cget("fg").lower(), "#ffb74d")

    def test_haunted_altar_canvas_integration(self):
        """Verifies HauntedAltarCanvas synchronizes candles and gravestones on hand 13."""
        self.app.haunted.phase = Phase.SNUFFING
        self.app.haunted.candles_remaining = 3
        self.app.haunted.gravestones_risen = 2
        self.app._update_candles_display()
        self.app._update_gravestones_display()
        self.root.update_idletasks()

        self.assertEqual(self.app.haunted_altar.candles_remaining, 3)
        self.assertEqual(self.app.haunted_altar.gravestones_count, 2)
        self.assertTrue(self.app.haunted_altar.candles_visible)
        self.assertTrue(self.app.haunted_altar.gravestones_visible)

    def test_card_table_layout_proportions(self):
        """Card table grid must give full height to Dealer and Player rows without card clipping."""
        r0 = self.app.card_table_frame.rowconfigure(0)
        r1 = self.app.card_table_frame.rowconfigure(1)

        self.assertGreaterEqual(r0["minsize"], 118)
        self.assertGreaterEqual(r0["weight"], 1)
        self.assertGreaterEqual(r1["minsize"], 118)
        self.assertGreaterEqual(r1["weight"], 1)

        self.assertEqual(self.app.dealer_cards_frame.grid_info()["row"], 0)
        self.assertEqual(self.app.player_cards_frame.grid_info()["row"], 1)

    def test_dialog_overlay_hidden_when_empty_and_placed_when_message_set(self):
        """Announcement HUD overlay must be completely unmapped when empty, and placed when active."""
        self.app.result_var.set("")
        self.root.update_idletasks()
        # When empty, zero outline/border: must be unmapped!
        self.assertEqual(self.app.announcement_hud.winfo_manager(), "")

        # When active, floats over the table as an in-table dialog overlay
        self.app.result_var.set("Player WINS!")
        self.root.update_idletasks()
        self.assertEqual(self.app.announcement_hud.winfo_manager(), "place")

        # Clearing message hides it again
        self.app.result_var.set("")
        self.root.update_idletasks()
        self.assertEqual(self.app.announcement_hud.winfo_manager(), "")

    def test_pumpkin_placement_beside_avatar_never_below_altar(self):
        """Pumpkin must be docked beside dealer avatar in header row and never below HauntedAltarCanvas."""
        self.app.haunted.phase = Phase.HELL_TABLE
        self.app._update_dealer_avatar()
        self.app._tick_ambient_animations()
        self.app._update_gravestones_display()
        self.root.update_idletasks()

        # Pumpkin must be inside dealer_header_row, above accessories_frame
        self.assertEqual(self.app.pumpkin_label.master, self.app.dealer_header_row)
        self.assertEqual(self.app.dealer_avatar_label.master, self.app.dealer_header_row)

    def test_victory_restores_normal_phase_and_green_felt(self):
        """Dismissing Exorcist victory dialog must restore normal phase, casino green felt, and clear altar."""
        self.app._trigger_hell_table()
        self.app.haunted.soul_meter = 1.0
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.root.update_idletasks()

        # Simulate round conclusion reaching 100% soul meter
        self.app.haunted.phase = Phase.VICTORY
        self.app._show_victory_dialog()
        self.root.update_idletasks()

        # If dialog was opened, dismiss it
        if hasattr(self.app, "_active_story_dialog") and self.app._active_story_dialog:
            self.app._active_story_dialog._dismiss()
            self.root.update_idletasks()

        # Phase must be restored to NORMAL
        self.assertEqual(self.app.haunted.phase, Phase.NORMAL)
        # Playing surface must be restored to vibrant casino green
        self.assertEqual(self.app.root["background"], TABLE_BACKGROUND_COLOR)
        self.assertEqual(self.app.card_table_frame["background"], PANEL_BACKGROUND_COLOR)
        # Altar must be hidden
        self.assertNotEqual(self.app.haunted_altar.winfo_manager(), "pack")
        # Cursed stakes button must be active in button_frame
        self.assertTrue(bool(self.app.cursed_stakes_button.grid_info()))
        # Dealer view button must return to normal state and reflect Dealer: ON
        self.assertEqual(str(self.app.dealer_view_button.cget("state")), "normal")
        self.assertEqual(self.app.dealer_view_status_var.get(), "👤 Dealer: ON")

    def test_no_duplicate_gravestones_legacy_unpacked(self):
        """Gravestones must only render on HauntedAltarCanvas without packing legacy frame."""
        self.app.haunted.phase = Phase.SNUFFING
        self.app.haunted.gravestones_risen = 3
        self.app._update_gravestones_display()
        self.root.update_idletasks()

        # Legacy frame must NOT be packed
        self.assertNotEqual(self.app.gravestones_frame.winfo_manager(), "pack")
        # Altar canvas must render all 3
        self.assertEqual(self.app.haunted_altar.gravestones_count, 3)
        self.assertTrue(self.app.haunted_altar.gravestones_visible)

    def test_phase_theme_full_surface_propagation(self):
        """All frames, labels, HUD, altar, and button bars must cascade theme colors."""
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.root.update_idletasks()

        bg_tbl = "#140508"
        bg_pnl = "#0d0204"

        self.assertEqual(self.app.root["background"], bg_tbl)
        self.assertEqual(self.app.card_table_frame["background"], bg_pnl)
        self.assertEqual(self.app.haunted_altar["background"], bg_pnl)
        self.assertEqual(self.app.announcement_hud["background"], bg_pnl)
        self.assertEqual(self.app.button_frame["background"], bg_tbl)
        self.assertEqual(self.app.dealer_title_label["background"], bg_pnl)
        self.assertEqual(self.app.player_title_label["background"], bg_pnl)

    def test_story_dialogue_button_styling_no_focus_distortion(self):
        """StoryDialogueDialog action button must use flat borderless styling to avoid glyph distortion."""
        dlg = StoryDialogueDialog(
            self.root,
            title="Test Modal",
            speaker="Test Speaker",
            portrait_img=None,
            text_content="Test message body.",
            button_text="Proceed",
            is_celestial=True,
        )
        self.root.update_idletasks()

        # Find the button inside the dialog
        btn = None
        for child in dlg.winfo_children():
            for sub in child.winfo_children():
                if isinstance(sub, tkinter.Frame):
                    for w in sub.winfo_children():
                        if isinstance(w, tkinter.Button):
                            btn = w
                            break

        self.assertIsNotNone(btn, "Dialogue button must be present in StoryDialogueDialog")
        self.assertEqual(btn.cget("relief"), "flat")
        self.assertEqual(int(btn.cget("highlightthickness")), 0)
        self.assertFalse(btn.cget("takefocus"))
    def test_altar_docked_on_card_table_felt_never_clipped_by_stage_canvas(self):
        """Haunted Altar accessories must dock on table felt below horizon, leaving stage canvas unobstructed."""
        self.assertEqual(self.app.accessories_frame.master, self.app.card_table_frame)
        self.assertEqual(len(self.app.dealer_stage_canvas.find_withtag("accessories_win")), 0)

        # Test phase theme matching felt background
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.root.update_idletasks()
        self.assertEqual(self.app.accessories_frame.cget("background"), self.app.card_table_frame.cget("background"))
        self.assertEqual(self.app.haunted_altar.cget("background"), self.app.card_table_frame.cget("background"))

        # Verify all 5 candle and 5 grave coordinates fit strictly inside altar canvas bounds
        altar_w = self.app.haunted_altar.winfo_reqwidth()
        for cx in self.app.haunted_altar.candle_x_positions:
            self.assertTrue(0 <= cx <= altar_w)
        for gx in self.app.haunted_altar.gravestone_x_positions:
            self.assertTrue(0 <= gx <= altar_w)


if __name__ == "__main__":
    unittest.main()


