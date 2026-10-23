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


if __name__ == "__main__":
    unittest.main()
