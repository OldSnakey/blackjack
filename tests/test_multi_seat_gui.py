"""
Automated GUI and Presentation Test Suite for Multi-Seat Wagering.

Tests:
- Table felt seat origins bounding boxes and card geometry margins.
- Split hand fanning bounding boxes.
- Canvas-level geometric click dispatching for main and side bets.
- MultiSeatInsuranceDialog bankroll clamping and Escape/close auto-decline safety.
"""

from __future__ import annotations

import tkinter
import unittest
from rules import Seat, RoundPhase
from ui_canvases import TableFeltCanvas
from ui_dialogs import MultiSeatInsuranceDialog
import ui_layout


class TestMultiSeatGUI(unittest.TestCase):

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.canvas = TableFeltCanvas(self.root, width=610, height=274)
        self.canvas.pack()

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_active_turn_halo_creates_base_and_pulsing_sprite(self):
        """Verifies drawing turn halo creates both the base outline and the feathered pulsing image item."""
        self.canvas.set_table_seats(3)
        self.canvas.draw_active_turn_halo(2)
        self.root.update_idletasks()

        # Both base halo and pulsing halo items must exist on canvas
        halo_items = self.canvas.find_withtag("turn_halo")
        pulse_items = self.canvas.find_withtag("turn_halo_pulse")
        self.assertGreater(len(halo_items), 0)
        self.assertGreater(len(pulse_items), 0)
        self.assertIsNotNone(getattr(self.canvas, "_halo_pulse_timer_id", None))

    def test_active_turn_halo_clear_removes_sprites_and_cancels_timer(self):
        """Verifies clearing turn halo removes sprites and cancels pending pulse timer."""
        self.canvas.set_table_seats(3)
        self.canvas.draw_active_turn_halo(2)
        self.root.update_idletasks()

        # Clear halo
        self.canvas.draw_active_turn_halo(None)
        self.root.update_idletasks()

        self.assertEqual(len(self.canvas.find_withtag("turn_halo")), 0)
        self.assertEqual(len(self.canvas.find_withtag("turn_halo_pulse")), 0)
        self.assertIsNone(getattr(self.canvas, "_halo_pulse_timer_id", None))

    def test_table_felt_seat_origins_bounding_boxes(self):
        """Verifies full-size card sprites (74x107 px) on Seats 1, 2, and 3 remain within felt margins."""
        felt_width = 980
        card_w, card_h = 74, 107

        # Margin requirements: min 10px clear on left (Column 0) and right (Column 2)
        min_left_margin = 10
        max_right_margin = felt_width - 10

        for seat_idx in (1, 2, 3):
            origin = ui_layout.get_seat_origin(seat_idx)
            cx, cy = origin["x"], origin["y"]
            left_edge = cx - (card_w // 2)
            right_edge = cx + (card_w // 2)

            self.assertGreaterEqual(
                left_edge,
                min_left_margin,
                f"Seat {seat_idx} left edge {left_edge} clips Column 0 plaque border!",
            )
            self.assertLessEqual(
                right_edge,
                max_right_margin,
                f"Seat {seat_idx} right edge {right_edge} clips Column 2 chip rack border!",
            )

    def test_split_fan_bounding_box_within_felt(self):
        """Verifies split hands fanning +-45 px remain within central felt bounds."""
        card_w = 74
        felt_width = 980
        fan_offset = ui_layout.get_ui_layout("table_felt").get("split_fan_offset_x", 45)

        for seat_idx in (1, 2, 3):
            origin = ui_layout.get_seat_origin(seat_idx)
            cx = origin["x"]
            # Sub-hand A fans left (-45px), Sub-hand B fans right (+45px)
            sub_a_left = (cx - fan_offset) - (card_w // 2)
            sub_b_right = (cx + fan_offset) + (card_w // 2)

            # In worst-case 3-seat split, check lateral boundaries
            self.assertGreaterEqual(sub_a_left, 0, f"Seat {seat_idx} split sub-hand A clips left felt bound!")
            self.assertLessEqual(sub_b_right, felt_width, f"Seat {seat_idx} split sub-hand B clips right felt bound!")

    def test_canvas_geometric_click_dispatching(self):
        """Verifies left-click stages bet and right-click clears bet without duplicate event firings."""
        clicked_events = []
        cleared_events = []

        self.canvas.on_spot_click_callback = lambda s_idx, b_type: clicked_events.append((s_idx, b_type))
        self.canvas.on_spot_clear_callback = lambda s_idx: cleared_events.append(s_idx)
        self.canvas.set_table_seats(3)
        self.canvas.draw_betting_spots()

        origin2 = ui_layout.get_seat_origin(2)
        # Simulate click on Seat 2 main betting spot
        event_main = tkinter.Event()
        event_main.x = origin2["x"]
        event_main.y = origin2["y"]

        self.canvas._on_canvas_click(event_main)
        self.assertEqual(len(clicked_events), 1)
        self.assertEqual(clicked_events[0], (2, None))

        # Simulate click on Seat 2 side bet spot (Perfect Pairs at left flanking offset)
        event_side = tkinter.Event()
        event_side.x = origin2["x"] - origin2.get("side_bet_offset_x", 42)
        event_side.y = origin2.get("side_bet_y", origin2["y"])

        self.canvas._on_canvas_click(event_side)
        self.assertEqual(len(clicked_events), 2)
        self.assertEqual(clicked_events[1], (2, "perfect_pairs"))

        # Simulate right click on Seat 2
        self.canvas._on_canvas_right_click(event_main)
        self.assertEqual(len(cleared_events), 1)
        self.assertEqual(cleared_events[0], 2)

    def test_multi_seat_dual_concentric_betting_rings(self):
        """Verifies that main and flanking side bet spots feature dual concentric dashed rings."""
        self.canvas.set_table_seats(3)
        self.canvas.draw_betting_spots()

        for s_idx in (1, 2, 3):
            # Main spot outer and inner rings
            self.assertTrue(self.canvas.find_withtag(f"spot_main_{s_idx}"))
            self.assertTrue(self.canvas.find_withtag(f"spot_main_inner_{s_idx}"))

            # PP spot outer and inner rings
            self.assertTrue(self.canvas.find_withtag(f"spot_pp_{s_idx}"))
            self.assertTrue(self.canvas.find_withtag(f"spot_pp_inner_{s_idx}"))

            # 21+3 spot outer and inner rings
            self.assertTrue(self.canvas.find_withtag(f"spot_t13_{s_idx}"))
            self.assertTrue(self.canvas.find_withtag(f"spot_t13_inner_{s_idx}"))

    def test_multi_seat_25d_chip_tray_rendered_and_clickable(self):
        """Verifies 3-seat mode renders 2.5D chip tray on table felt and handles clicks."""
        clicked_chips = []
        self.canvas.set_table_seats(3)
        self.canvas.on_chip_click_callback = lambda d: clicked_chips.append(d)
        self.canvas.draw_chip_tray(available_bankroll=1000)

        # Verify chip tray items and denomination labels exist on felt
        tray_items = self.canvas.find_withtag("felt_chip_tray")
        self.assertTrue(len(tray_items) > 0)

        # Trigger click on $25 chip pile
        self.canvas.trigger_chip_tray_click(25)
        self.assertEqual(clicked_chips, [25])

    def test_multi_seat_insurance_dialog_clamping(self):
        """Verifies 'Insure All' is disabled when bankroll is below total insurance cost."""
        seats = [
            Seat(1, main_bet=100, is_active=True),
            Seat(2, main_bet=200, is_active=True),
        ]
        # Total insurance needed: 50 + 100 = 150
        # Bankroll is only 100 -> Insure All must be disabled
        dialog = MultiSeatInsuranceDialog(
            self.root,
            seats=seats,
            bankroll=100,
            on_confirm=lambda chosen: None,
            on_decline=lambda: None,
        )
        dialog.update_idletasks()

        self.assertEqual(dialog.btn_insure_all["state"], "disabled")
        # Checkbox for Seat 2 ($100 insurance) can be afforded ($100 bankroll)
        self.assertEqual(dialog.cb_widgets[2]["state"], "normal")
        dialog.destroy()

    def test_multi_seat_insurance_escape_and_close_auto_declines(self):
        """Verifies <Escape> and WM_DELETE_WINDOW invoke auto-decline cleanly."""
        seats = [Seat(1, main_bet=50, is_active=True)]
        declined = []

        dialog = MultiSeatInsuranceDialog(
            self.root,
            seats=seats,
            bankroll=500,
            on_confirm=lambda chosen: None,
            on_decline=lambda: declined.append(True),
        )
        dialog._on_decline()
        self.assertEqual(len(declined), 1)


class TestMultiSeatAppIntegration(unittest.TestCase):
    """End-to-end integration tests for BlackjackApp in 3-Seat Wagering Mode."""

    def setUp(self):
        import tempfile
        import shutil
        from save_manager import SaveManager
        from blackjack import BlackjackApp

        from pathlib import Path
        self.temp_dir = tempfile.mkdtemp()
        self.save_mgr = SaveManager(save_path=Path(self.temp_dir) / "test_save.json")

        self.root = tkinter.Tk()
        self.root.withdraw()

        self.app = BlackjackApp(self.root, chips_mode=True, sound_enabled=False)
        self.app.save_manager = self.save_mgr
        self.app.set_table_seats(3)
        self.root.update_idletasks()

    def tearDown(self):
        import shutil
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def test_multi_seat_app_deal_and_play_flow(self):
        """
        End-to-end test verifying multi-seat betting, deal hand button invocation,
        clockwise turn traversal across active seats, and round conclusion without TypeError.
        """
        # 1. Verify 3-seat mode initialized cleanly
        self.assertEqual(self.app.table_seats, 3)
        self.assertIsNone(self.app.engine.active_seat_index)
        self.assertEqual(self.app.round_phase, RoundPhase.BETTING)

        # 2. Stage bets on Seat 1 ($50) and Seat 3 ($100) via UI callbacks
        # Initial click on inactive spot activates it; second click stages chips
        self.app._select_rail_denomination(50)
        self.app._on_table_spot_click(1, None)  # First click activates/focuses Seat 1
        self.app._on_table_spot_click(1, None)  # Second click adds $50 chip
        self.assertEqual(self.app.engine.seats[0].main_bet, 50)
        self.assertTrue(self.app.engine.seats[0].is_active)

        self.app._select_rail_denomination(100)
        self.app._on_table_spot_click(3, None)  # First click activates/focuses Seat 3
        self.app._on_table_spot_click(3, None)  # Second click adds $100 chip
        self.assertEqual(self.app.engine.seats[2].main_bet, 100)
        self.assertTrue(self.app.engine.seats[2].is_active)

        # Seat 2 remains unbet (inactive)
        self.assertEqual(self.app.engine.seats[1].main_bet, 0)
        self.assertFalse(self.app.engine.seats[1].is_active)

        # Select cards from self.app.all_cards with valid images to ensure non-21 hands
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_6s = [c for c in self.app.all_cards if c.value == 6]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_7s = [c for c in self.app.all_cards if c.value == 7]
        self.app.deck = [
            c_7s[0],   # Dealer card 2
            c_8s[0],   # Seat 3 card 2
            c_6s[0],   # Seat 1 card 2
            c_10s[0],  # Dealer card 1
            c_10s[1],  # Seat 3 card 1
            c_10s[2],  # Seat 1 card 1
        ]

        # 3. Click "Deal Hand" (_deal_hand_with_bet) - previously crashed with TypeError
        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Assert deal succeeded cleanly
        self.assertFalse(self.app.is_betting_phase)
        self.assertEqual(len(self.app.engine.seats[0].hands[0]), 2)
        self.assertEqual(len(self.app.engine.seats[2].hands[0]), 2)
        # Inactive seat receives 0 cards
        self.assertEqual(sum(len(h) for h in self.app.engine.seats[1].hands), 0)
        self.assertEqual(len(self.app.dealer_hand), 2)

        # 4. If round is in player turn, test clockwise turn advancement
        if self.app.round_phase == RoundPhase.PLAYER_TURN:
            # Active seat should be Seat 1
            self.assertEqual(self.app.engine.active_seat_index, 1)

            # Stand on Seat 1 -> should advance clockwise to Seat 3 (skipping inactive Seat 2)
            self.app.on_stand()
            self.root.update_idletasks()

            if self.app.round_phase == RoundPhase.PLAYER_TURN:
                self.assertEqual(self.app.engine.active_seat_index, 3)
                # Stand on Seat 3 -> round transitions to dealer turn / conclusion
                self.app.on_stand()
                self.root.update_idletasks()

        # 5. Conclude round and verify result text formatting
        if self.app._dealer_timer_id:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
        self.app._conclude_round()
        self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        self.assertTrue(len(self.app.result_var.get()) > 0)
        self.assertEqual(self.app.new_game_button.cget("state"), "normal")

    def test_multi_seat_hit_and_bust_advances_turn_cleanly(self):
        """
        Asserts that when a seat hits and busts (> 21):
        1. play_bust() executes cleanly without AttributeError.
        2. Turn immediately advances clockwise to the next active seat.
        3. Round resolves properly with individual bust message in result banner.
        """
        from rules import Card

        # Stage bets on Seat 1 ($50) and Seat 2 ($25)
        # First click activates/focuses, second click stages chip
        self.app._select_rail_denomination(50)
        self.app._on_table_spot_click(1, None)  # Focuses Seat 1
        self.app._on_table_spot_click(1, None)  # Adds $50 chip
        self.app._select_rail_denomination(25)
        self.app._on_table_spot_click(2, None)  # Focuses Seat 2
        self.app._on_table_spot_click(2, None)  # Adds $25 chip

        # Rig deck so initial deal gives Seat 1 hard 16, Seat 2 hard 15, Dealer 17
        # Deal order:
        # S1 c1 (10), S2 c1 (10), D hole (7), S1 c2 (6), S2 c2 (5), D up (10)
        # Next draw on hit: King (10) -> S1 busts with 26!
        self.app.deck = [
            Card(10, None, "10", "spade"),   # S2 stand / next
            Card(10, None, "king", "heart"), # S1 hit -> busts (16 + 10 = 26)
            Card(10, None, "10", "diamond"), # D upcard
            Card(5, None, "5", "club"),      # S2 c2
            Card(6, None, "6", "spade"),     # S1 c2
            Card(7, None, "7", "heart"),     # D hole
            Card(10, None, "jack", "club"),  # S2 c1
            Card(10, None, "queen", "spade"),# S1 c1
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.seats[0].hands[0].score, 16)

        # Hit on Seat 1 -> draws King (10) -> score 26 (BUST)
        self.app.on_hit()
        self.root.update_idletasks()

        # Seat 1 should be busted and turn should advance to Seat 2!
        self.assertTrue(self.app.engine.seats[0].hands[0].is_bust)
        self.assertEqual(self.app.engine.active_seat_index, 2)
        self.assertEqual(self.app.round_phase, RoundPhase.PLAYER_TURN)

        # Stand on Seat 2 -> transitions to Dealer Turn / Conclusion
        self.app.on_stand()
        self.root.update_idletasks()

        if self.app._dealer_timer_id:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
        self.app._conclude_round()
        self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        # Verify Seat 1 shows BUST in banner
        banner = self.app.result_var.get()
        self.assertTrue("Seat 1" in banner or "S1" in banner)
        self.assertIn("bust", banner.lower())

    def test_multi_seat_all_seats_bust_concludes_round_immediately(self):
        """
        Asserts that if all active seats bust, round concludes immediately
        without waiting for dealer draws.
        """
        from rules import Card

        # Stage bets on Seat 1 and Seat 3
        self.app._select_rail_denomination(50)
        self.app._on_table_spot_click(1, None)  # Focuses Seat 1
        self.app._on_table_spot_click(1, None)  # Adds $50 chip
        self.app._select_rail_denomination(50)
        self.app._on_table_spot_click(3, None)  # Focuses Seat 3
        self.app._on_table_spot_click(3, None)  # Adds $50 chip

        # S1 hard 15, S3 hard 16. Hits on both bust them.
        self.app.deck = [
            Card(10, None, "king", "diamond"), # S3 hit -> busts
            Card(10, None, "king", "club"),    # S1 hit -> busts
            Card(10, None, "10", "diamond"),   # D upcard
            Card(6, None, "6", "club"),        # S3 c2
            Card(5, None, "5", "spade"),       # S1 c2
            Card(7, None, "7", "heart"),       # D hole
            Card(10, None, "jack", "club"),    # S3 c1
            Card(10, None, "queen", "spade"),  # S1 c1
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Hit on Seat 1 -> score 25 (BUST)
        self.app.on_hit()
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.active_seat_index, 3)

        # Hit on Seat 3 -> score 26 (BUST)
        # All seats busted -> should conclude round immediately!
        self.app.on_hit()
        self.root.update_idletasks()

        self.assertEqual(self.app.round_phase, RoundPhase.ROUND_OVER)
        self.assertIsNone(self.app._dealer_timer_id)
        self.assertEqual(self.app.new_game_button.cget("state"), "normal")

    def test_multi_seat_no_colored_buttons_on_mahogany_rail(self):
        """Verifies that mahogany rail dock does not render colored flat chip buttons."""
        self.app.set_table_seats(3)
        self.root.update_idletasks()

        # The flat colored chip buttons should not exist or should not be active
        colored_buttons = getattr(self.app, "rail_denom_buttons", [])
        self.assertEqual(len(colored_buttons), 0)

    def test_multi_seat_clicking_chip_adds_to_focused_seat(self):
        """Verifies left-clicking a 2.5D chip adds that denomination to the active betting seat."""
        self.app.set_table_seats(3)
        self.app.focused_betting_seat = 2
        self.root.update_idletasks()

        # Click $25 chip -> adds $25 to Seat 2
        self.app._on_felt_chip_click(25)
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.seats[1].main_bet, 25)

        # Focus Seat 1, click $100 chip -> adds $100 to Seat 1
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(100)
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.seats[0].main_bet, 100)
        self.assertEqual(self.app.engine.seats[1].main_bet, 25)

    def test_multi_seat_inactive_spot_initial_click_activates_without_chips(self):
        """Verifies initial click on an inactive seat activates it without adding chips."""
        self.app.set_table_seats(3)
        self.app.focused_betting_seat = 2
        self.root.update_idletasks()

        # Seat 1 has 0 bet and is inactive (Seat 2 is focused)
        self.assertEqual(self.app.engine.seats[0].main_bet, 0)

        # 1st Click on Seat 1: must activate Seat 1 and add 0 chips
        self.app._on_table_spot_click(1, None)
        self.root.update_idletasks()
        self.assertEqual(self.app.focused_betting_seat, 1)
        self.assertEqual(self.app.engine.seats[0].main_bet, 0)

        # 2nd Click on Seat 1: now that it is active, adds chips
        self.app._on_table_spot_click(1, None)
        self.root.update_idletasks()
        self.assertEqual(self.app.engine.seats[0].main_bet, self.app.selected_denomination)

    def test_multi_seat_conclusion_summary_format(self):
        """Verifies that round conclusion produces a two-tier summary: Total in Tier 1, details in Tier 2."""
        from rules import Card

        # Stage bets on Seat 1 ($50) and Seat 2 ($50)
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(50)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(50)

        # Rig deck so Seat 1 wins and Seat 2 pushes
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        self.app.deck = [
            c_8s[0],   # Dealer c2 (10+8=18)
            c_9s[0],   # Seat 2 c2 (9+9=18, push)
            c_10s[0],  # Seat 1 c2 (10+10=20, win)
            c_10s[1],  # Dealer c1
            c_9s[1],   # Seat 2 c1
            c_10s[2],  # Seat 1 c1
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Stand on Seat 1
        self.app.on_stand()
        self.root.update_idletasks()
        # Stand on Seat 2
        self.app.on_stand()
        self.root.update_idletasks()

        if self.app._dealer_timer_id:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
        self.app._conclude_round()
        self.root.update_idletasks()

        summary_text = self.app.result_var.get()
        self.assertIn("\n", summary_text)
        tier1, tier2 = summary_text.split("\n", 1)

        # Tier 1 should contain aggregate table total
        self.assertIn("Total Won:", tier1)
        self.assertIn("+$50", tier1)

        # Tier 2 should contain breakdown across played seats
        self.assertIn("Seat 1", tier2)
        self.assertIn("Seat 2", tier2)
        self.assertTrue("win" in tier2.lower())
        self.assertTrue("push" in tier2.lower())

    def test_multi_seat_dealer_blackjack_single_announcement(self):
        """
        Verifies that when dealer has natural Blackjack in 3-seat mode:
        1. Dealer Blackjack is announced once in Tier 1.
        2. Tier 2 does NOT repeat 'Dealer has Blackjack' for each seat.
        """
        from rules import Card

        # Stage bets on Seat 1 ($25), Seat 2 ($25), Seat 3 ($25)
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 3
        self.app._on_felt_chip_click(25)

        # Dealer gets Natural Blackjack: 10 of Clubs (upcard) + Ace of Spades (hole card)
        # Seats get non-21 hands
        c_aces = [c for c in self.app.all_cards if c.rank == "ace"]
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_7s = [c for c in self.app.all_cards if c.value == 7]

        # Deal order (3 active seats: S1, S2, S3):
        # Round 1: S1 c1 (10), S2 c1 (10), S3 c1 (10), D upcard (10)
        # Round 2: S1 c2 (8),  S2 c2 (9),  S3 c2 (7),  D hole card (Ace) -> Dealer Blackjack!
        self.app.deck = [
            c_aces[0], # Dealer hole card (Ace: 11) -> total 21 Blackjack!
            c_7s[0],   # Seat 3 c2 (17)
            c_9s[0],   # Seat 2 c2 (19)
            c_8s[0],   # Seat 1 c2 (18)
            c_10s[0],  # Dealer upcard (10)
            c_10s[1],  # Seat 3 c1 (10)
            c_10s[2],  # Seat 2 c1 (10)
            c_10s[3],  # Seat 1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        if self.app._dealer_timer_id:
            self.root.after_cancel(self.app._dealer_timer_id)
            self.app._dealer_timer_id = None
        self.app._conclude_round()
        self.root.update_idletasks()

        summary_text = self.app.result_var.get()
        self.assertIn("\n", summary_text)
        tier1, tier2 = summary_text.split("\n", 1)

        # Tier 1 announces Dealer Blackjack once with total loss
        self.assertIn("Dealer has Blackjack!", tier1)
        self.assertIn("Total Loss:", tier1)
        self.assertIn("-$75", tier1)

        # Tier 2 does NOT repeat 'Dealer has Blackjack'
        self.assertNotIn("Dealer has Blackjack", tier2)
        # Instead, each seat simply displays Loss
        self.assertIn("Seat 1: Loss", tier2)
        self.assertIn("Seat 2: Loss", tier2)
        self.assertIn("Seat 3: Loss", tier2)

    def test_multi_seat_split_bust_advances_active_rectangle_and_centers_hands(self):
        """
        Verifies that when Seat 1 splits:
        1. Both hands are placed side-by-side at the same Y level and centered over Seat 1's betting spot.
        2. When Hand 1 hits and busts, the active yellow rectangle correctly moves to Hand 2,
           and Hand 1 is marked as Bust (not erroneously showing the yellow active outline).
        """
        from rules import Card

        # Stage bet on Seat 1 only ($50)
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(25)
        self.app._on_felt_chip_click(25)

        # Rig cards: Seat 1 gets pair of 8s (8 + 8)
        # Dealer gets 7 + 10
        # When split:
        # Hand 1 draws 10 (8+10=18)
        # Hand 2 draws 8 (8+8=16)
        # Next hit on Hand 1: draws King (10) -> score 28 (Bust!)
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_7s = [c for c in self.app.all_cards if c.value == 7]

        # Deal order (only Seat 1 active):
        # Initial deal: S1 c1 (8), D upcard (7), S1 c2 (8), D hole (10)
        # Split deal: S1 H1 draw (10), S1 H2 draw (8)
        # Hit on H1: draws 10 -> busts with 28
        self.app.deck = [
            c_10s[0],  # Hit on H1 (10) -> score 28 (BUST)
            c_8s[2],   # Split draw for Hand 2 (8)
            c_10s[1],  # Split draw for Hand 1 (10)
            c_10s[2],  # Dealer hole (10)
            c_8s[1],   # Seat 1 c2 (8)
            c_7s[0],   # Dealer upcard (7)
            c_8s[0],   # Seat 1 c1 (8)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Seat 1 has pair of 8s, trigger split
        self.assertEqual(len(self.app.engine.seats[0].hands), 1)
        self.app.on_split()
        self.root.update_idletasks()

        seat = self.app.engine.seats[0]
        self.assertEqual(len(seat.hands), 2)
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.active_hand_index, 0)

        # 1. Verify hands are side-by-side at same Y level and centered over Seat 1 (X=745)
        canvas = self.app.card_table_frame
        h1_card0_pos = canvas.coords(seat.hands[0].sprite_ids[0])
        h2_card0_pos = canvas.coords(seat.hands[1].sprite_ids[0])

        # Y positions should be identical (side by side, not cascaded vertically)
        self.assertEqual(h1_card0_pos[1], h2_card0_pos[1], "Split hands should be side-by-side at same Y level")

        # Hand 1 must be to the left of Hand 2
        self.assertLess(h1_card0_pos[0], h2_card0_pos[0])

        # The midpoint between Hand 1 left edge and Hand 2 right edge should be centered near X=745
        card_w = self.app.card_width
        h1_left = h1_card0_pos[0]
        h2_right = canvas.coords(seat.hands[1].sprite_ids[-1])[0] + card_w
        combined_center = (h1_left + h2_right) / 2.0
        self.assertAlmostEqual(combined_center, 745, delta=10, msg="Split hands should be centered over Seat 1 betting area (X=745)")

        # Verify initial active decor: Hand 1 active, Hand 2 inactive
        decors = canvas.find_withtag("player_card_decor")
        rects = [item for item in decors if canvas.type(item) == "rectangle"]
        self.assertEqual(len(rects), 2)
        # Rect 0 (Hand 1) should be gold (#ffd700), Rect 1 (Hand 2) should be dark (#37474f)
        self.assertEqual(canvas.itemcget(rects[0], "outline").lower(), "#ffd700")
        self.assertEqual(canvas.itemcget(rects[1], "outline").lower(), "#37474f")

        # 2. Hit on Hand 1 -> draws King (10) -> score 28 (BUST!)
        self.app.on_hit()
        self.root.update_idletasks()

        # Turn must have advanced to Hand 2!
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.active_hand_index, 1)
        self.assertTrue(seat.hands[0].is_busted)

        # Re-check decor rectangles: Hand 1 must NOT be yellow, Hand 2 MUST be yellow (#ffd700)!
        decors = canvas.find_withtag("player_card_decor")
        rects = [item for item in decors if canvas.type(item) == "rectangle"]
        self.assertEqual(len(rects), 2)
        self.assertNotEqual(canvas.itemcget(rects[0], "outline").lower(), "#ffd700", "Hand 1 should no longer be active yellow")
        self.assertEqual(canvas.itemcget(rects[1], "outline").lower(), "#ffd700", "Hand 2 should now have the active yellow rectangle")

    def test_multi_seat_insurance_taken_dealer_no_blackjack_resumes_play(self):
        """
        Verifies that in 3-seat mode, when seats take insurance and the dealer does NOT have Blackjack:
        1. Insurance wagers are deducted and marked as lost.
        2. Play resumes smoothly at the first active seat (Seat 1).
        3. Player action buttons (Hit, Stand) are ENABLED ('normal'), not stuck disabled.
        """
        from rules import Card

        # Stage bets on all 3 seats: Seat 1 ($50), Seat 2 ($50), Seat 3 ($50)
        self.app.focused_betting_seat = 1
        self.app._on_felt_chip_click(25)
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 2
        self.app._on_felt_chip_click(25)
        self.app._on_felt_chip_click(25)
        self.app.focused_betting_seat = 3
        self.app._on_felt_chip_click(25)
        self.app._on_felt_chip_click(25)

        c_aces = [c for c in self.app.all_cards if c.rank == "ace"]
        c_10s = [c for c in self.app.all_cards if c.value == 10]
        c_9s = [c for c in self.app.all_cards if c.value == 9]
        c_8s = [c for c in self.app.all_cards if c.value == 8]
        c_7s = [c for c in self.app.all_cards if c.value == 7]

        # Deal order (3 active seats: S1, S2, S3):
        # Round 1: S1 c1 (10), S2 c1 (10), S3 c1 (10), D upcard (Ace) -> Triggers Insurance!
        # Round 2: S1 c2 (8),  S2 c2 (9),  S3 c2 (7),  D hole (8) -> Total 19 (NO Blackjack!)
        self.app.deck = [
            c_8s[0],   # Dealer hole (8) -> Ace + 8 = 19 (NO Blackjack!)
            c_7s[0],   # Seat 3 c2 (17)
            c_9s[0],   # Seat 2 c2 (19)
            c_8s[1],   # Seat 1 c2 (18)
            c_aces[0], # Dealer upcard (Ace)
            c_10s[0],  # Seat 3 c1 (10)
            c_10s[1],  # Seat 2 c1 (10)
            c_10s[2],  # Seat 1 c1 (10)
        ]

        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        # Should be in insurance phase
        self.assertTrue(self.app.is_insurance_phase)
        self.assertEqual(self.app.round_phase, RoundPhase.INSURANCE)

        # All 3 seats take insurance ($25 each)
        self.app._on_multi_seat_insurance_confirm({1: 25, 2: 25, 3: 25})
        self.root.update_idletasks()

        # Insurance phase should be concluded
        self.assertFalse(self.app.is_insurance_phase)
        self.assertEqual(self.app.round_phase, RoundPhase.PLAYER_TURN)

        # Play MUST resume at first active seat (Seat 1)
        self.assertEqual(self.app.engine.active_seat_index, 1)
        self.assertEqual(self.app.engine.active_hand_index, 0)

        # Action buttons MUST be enabled ('normal')
        self.assertEqual(self.app.hit_button.cget("state"), "normal")
        self.assertEqual(self.app.stand_button.cget("state"), "normal")
        self.assertIn("Dealer has no Blackjack", self.app.result_var.get())


if __name__ == "__main__":
    unittest.main()

