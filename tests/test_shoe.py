import unittest
import tkinter
from blackjack import (
    BlackjackApp,
    Card,
    build_shoe,
    DEFAULT_DECK_COUNT,
    CUT_CARD_PENETRATION,
)


class TestMultiDeckShoe(unittest.TestCase):
    """Test suite for validating the multi-deck shoe, cut card penetration, and persistence."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.app._on_close()
        except tkinter.TclError:
            pass

    def test_build_shoe_composition(self):
        """build_shoe creates 208 cards for a 4-deck shoe with exact rank frequencies."""
        shoe = build_shoe(self.app.all_cards, num_decks=4)
        self.assertEqual(len(shoe), 208)

        # 16 Aces (4 decks * 4 suits)
        ace_count = sum(1 for c in shoe if getattr(c, "rank", "") == "ace" or c[0] == 1)
        self.assertEqual(ace_count, 16)

        # 64 Ten-value cards (16 tens, 16 jacks, 16 queens, 16 kings)
        ten_count = sum(1 for c in shoe if c[0] == 10)
        self.assertEqual(ten_count, 64)

    def test_shoe_persists_across_rounds(self):
        """Cards dealt from the shoe persist across consecutive rounds without premature reshuffling."""
        initial_cards = len(self.app.deck)
        self.assertEqual(initial_cards, 208 - 4)  # 208 initial minus 4 cards dealt on game 1

        # Play a round where player takes a hit
        self.app.on_hit()
        cards_after_round1 = len(self.app.deck)
        self.assertLess(cards_after_round1, initial_cards)

        self.app.on_stand()
        self.app._conclude_round()

        # Start game 2 - shoe should NOT reshuffle because cut card was not reached
        self.app.new_game()
        # Game 2 deals 4 cards (2 to player, 2 to dealer)
        self.assertEqual(len(self.app.deck), cards_after_round1 - 4)
        self.assertFalse(self.app.shoe_needs_reshuffle)

    def test_cut_card_penetration_triggers_reshuffle_on_subsequent_game(self):
        """When remaining cards drop to <= 25%, shoe_needs_reshuffle is set, and new_game() reshuffles."""
        threshold = int(len(self.app.all_cards) * self.app.deck_count * CUT_CARD_PENETRATION)
        self.assertEqual(threshold, 52)  # 25% of 208 = 52 cards

        # Simulate shoe depletion to just above threshold
        self.app.deck = self.app.deck[:threshold + 1]
        self.assertFalse(self.app.shoe_needs_reshuffle)

        # Drawing 1 card reaches the threshold
        card = self.app._draw_card()
        self.assertTrue(self.app.shoe_needs_reshuffle)
        self.assertIn("[Cut]", self.app.shoe_info_var.get())

        # Calling new_game() now should rebuild the full 4-deck shoe (208 cards minus 4 dealt = 204)
        self.app.new_game()
        self.assertEqual(len(self.app.deck), 208 - 4)
        self.assertFalse(self.app.shoe_needs_reshuffle)
        self.assertNotIn("[Cut]", self.app.shoe_info_var.get())


if __name__ == "__main__":
    unittest.main()
