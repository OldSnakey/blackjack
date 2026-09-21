import unittest
import tkinter
from blackjack import (
    BlackjackApp,
    Card,
    STARTING_BANKROLL,
    MINIMUM_BET,
    calculate_payout,
    calculate_insurance_payout,
)


class TestPayoutCalculation(unittest.TestCase):
    """Unit tests for the pure calculate_payout and calculate_insurance_payout functions."""

    def test_natural_blackjack_payout(self):
        """Natural Blackjack pays 3:2 (returns original bet + 1.5x profit)."""
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 10), 25)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 20), 50)
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 100), 250)
        # Integer truncation for odd bets
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 5), 12)

    def test_insurance_payout(self):
        """Insurance pays 2:1 when dealer has Blackjack, returning 3x the insurance bet."""
        # $25 insurance returns $75 (original $25 + $50 profit)
        self.assertEqual(calculate_insurance_payout(True, 25), 75)
        self.assertEqual(calculate_insurance_payout(True, 10), 30)
        # Odd bets with main_bet parameter: payout covers main_bet for exact breakeven
        # $5 bet: insurance $2 -> payout $7 (original $2 + $5 profit)
        self.assertEqual(calculate_insurance_payout(True, 2, main_bet=5), 7)
        # $25 bet: insurance $12 -> payout $37 (original $12 + $25 profit)
        self.assertEqual(calculate_insurance_payout(True, 12, main_bet=25), 37)
        # $187 bet: insurance $93 -> payout $280 (original $93 + $187 profit)
        self.assertEqual(calculate_insurance_payout(True, 93, main_bet=187), 280)
        # Even bet with main_bet parameter: pays standard 2:1 (returning $75: $25 wager + $50 profit)
        self.assertEqual(calculate_insurance_payout(True, 25, main_bet=50), 75)
        # Partial insurance bet with main_bet parameter: pays standard 2:1 without exploiting main_bet
        # $100 main bet with $10 insurance: pays $30 ($10 wager + $20 profit), NOT $110
        self.assertEqual(calculate_insurance_payout(True, 10, main_bet=100), 30)
        # Dealer no blackjack -> 0
        self.assertEqual(calculate_insurance_payout(False, 25), 0)
        self.assertEqual(calculate_insurance_payout(False, 2, main_bet=5), 0)
        # Non-positive wager -> 0
        self.assertEqual(calculate_insurance_payout(True, 0), 0)
        self.assertEqual(calculate_insurance_payout(True, -10), 0)

    def test_standard_win_payout(self):
        """Standard player wins and dealer busts pay 1:1 (returns 2x bet)."""
        self.assertEqual(calculate_payout("PLAYER_WINS", 10), 20)
        self.assertEqual(calculate_payout("PLAYER_WINS", 50), 100)
        self.assertEqual(calculate_payout("DEALER_BUST", 25), 50)

    def test_push_refunds_wager(self):
        """A push refunds the original wager (1x bet)."""
        self.assertEqual(calculate_payout("PUSH", 10), 10)
        self.assertEqual(calculate_payout("PUSH", 100), 100)

    def test_loss_returns_zero(self):
        """Dealer wins and player busts return 0."""
        self.assertEqual(calculate_payout("DEALER_WINS", 25), 0)
        self.assertEqual(calculate_payout("PLAYER_BUST", 50), 0)
        self.assertEqual(calculate_payout("UNKNOWN_OUTCOME", 10), 0)

    def test_zero_or_negative_wager(self):
        """Zero or negative wagers return 0 regardless of outcome."""
        self.assertEqual(calculate_payout("NATURAL_BLACKJACK", 0), 0)
        self.assertEqual(calculate_payout("PLAYER_WINS", -10), 0)


class TestBettingGuiAndState(unittest.TestCase):
    """Integration and state tests for Chips Mode, bankroll management, and GUI controls."""

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

    def test_default_casual_mode(self):
        """By default, Chips Mode is OFF (Casual Mode) and betting controls are hidden."""
        self.assertFalse(self.app.chips_mode_var.get())
        # Check that betting frame and bankroll label are hidden via grid_info()
        self.assertFalse(bool(self.app.betting_frame.grid_info()))
        self.assertFalse(bool(self.app.bankroll_label.grid_info()))

    def test_toggle_chips_mode_on_and_off(self):
        """Toggling Chips Mode ON displays betting controls; toggling OFF hides them."""
        # Toggle ON
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode()

        self.assertTrue(bool(self.app.betting_frame.grid_info()))
        self.assertTrue(bool(self.app.bankroll_label.grid_info()))
        self.assertTrue(self.app.is_betting_phase)

        # Toggle OFF
        self.app.chips_mode_var.set(False)
        self.app._on_toggle_chips_mode()

        self.assertFalse(bool(self.app.betting_frame.grid_info()))
        self.assertFalse(bool(self.app.bankroll_label.grid_info()))
        self.assertFalse(self.app.is_betting_phase)

    def test_staging_bet_and_clear(self):
        """Adding chips updates the staged bet; Clear Bet resets it back to 0."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.assertTrue(self.app.is_betting_phase)

        # Reset staged bet to 0
        self.app.current_bet_var.set(0)
        self.app._update_betting_controls()

        # Add $25 chip
        self.app._add_chip_bet(25)
        self.assertEqual(self.app.current_bet_var.get(), 25)

        # Add $100 chip
        self.app._add_chip_bet(100)
        self.assertEqual(self.app.current_bet_var.get(), 125)

        # Clear bet
        self.app._clear_bet()
        self.assertEqual(self.app.current_bet_var.get(), 0)

    def test_staging_bet_cannot_exceed_bankroll(self):
        """Staged bet cannot be increased beyond current bankroll."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(50)
        self.app.current_bet_var.set(25)

        # Attempt to add $100 chip (25 + 100 > 50) -> should be blocked
        self.app._add_chip_bet(100)
        self.assertEqual(self.app.current_bet_var.get(), 25)

        # Adding $25 chip (25 + 25 <= 50) -> allowed
        self.app._add_chip_bet(25)
        self.assertEqual(self.app.current_bet_var.get(), 50)

    def test_all_in_bets_full_bankroll(self):
        """Clicking All In stages the full bankroll even if odd/non-standard denomination."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        # Set bankroll to 187 (e.g. an amount not evenly divisible by chips)
        self.app.bankroll_var.set(187)
        self.app.current_bet_var.set(0)
        self.app._update_betting_controls()

        self.assertEqual(self.app.all_in_button["state"], "normal")

        # Trigger All In
        self.app._all_in()
        self.assertEqual(self.app.current_bet_var.get(), 187)
        self.assertEqual(self.app.all_in_button["state"], "disabled")  # Already all-in
        self.assertEqual(self.app.deal_bet_button["state"], "normal")

        # Rig deck so hands do not accidentally deal a Natural 21
        self.app.deck = [
            Card(7, self.app.back_image, rank="7", suit="club"),
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="spade"),
            Card(10, self.app.back_image, rank="10", suit="heart"),
        ]

        # Committing the all-in deal
        self.app._deal_hand_with_bet()
        self.assertEqual(self.app.bankroll_var.get(), 0)
        self.assertEqual(self.app.hand_bets, [187])
        self.assertEqual(self.app.all_in_button["state"], "disabled")

    def test_all_in_disabled_if_bankroll_below_minimum(self):
        """All In is disabled if remaining bankroll is below the minimum bet."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(3)
        self.app.current_bet_var.set(0)
        self.app._update_betting_controls()

        self.assertEqual(self.app.all_in_button["state"], "disabled")
        self.app._all_in()
        self.assertEqual(self.app.current_bet_var.get(), 0)

    def test_deal_hand_with_bet_commits_wager(self):
        """Clicking Deal Hand commits wager, deducts from bankroll, and begins play."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        initial_bankroll = self.app.bankroll_var.get()

        # Rig deck so hands do not accidentally deal a Natural 21
        self.app.deck = [
            Card(7, self.app.back_image, rank="7", suit="club"),
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="spade"),
            Card(10, self.app.back_image, rank="10", suit="heart"),
        ]

        # Set bet to $50 and deal
        self.app.current_bet_var.set(50)
        self.app._deal_hand_with_bet()

        self.assertFalse(self.app.is_betting_phase)
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll - 50)
        self.assertEqual(self.app.hand_bets, [50])
        self.assertEqual(len(self.app.player_hands[0]), 2)
        self.assertEqual(len(self.app.dealer_hand), 2)

    def test_deal_hand_below_minimum_bet_blocked(self):
        """Betting less than MINIMUM_BET prevents dealing."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.current_bet_var.set(MINIMUM_BET - 1)

        self.app._deal_hand_with_bet()
        self.assertTrue(self.app.is_betting_phase)
        self.assertEqual(len(self.app.player_hands[0]), 0)

    def test_payout_resolution_player_win(self):
        """Winning a hand in Chips Mode awards 2x the bet to bankroll."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(900)
        self.app.hand_bets = [100]  # $100 bet already deducted from bankroll

        # Set up player winning hands (Player 20 vs Dealer 18)
        self.app.player_hands = [[
            Card(10, self.app.back_image, "10", "heart"),
            Card(10, self.app.back_image, "10", "spade"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "diamond"),
            Card(8, self.app.back_image, "8", "club"),
        ]

        self.app._conclude_round()

        # Bankroll should increase by payout (2 * 100 = 200) -> 900 + 200 = 1100
        self.assertEqual(self.app.bankroll_var.get(), 1100)
        self.assertIn("+$100", self.app.result_var.get())

    def test_payout_resolution_natural_blackjack(self):
        """Natural blackjack in Chips Mode awards 3:2 payout."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(900)
        self.app.hand_bets = [100]

        # Natural 21 vs 18
        self.app.player_hands = [[
            Card(1, self.app.back_image, "ace", "heart"),
            Card(10, self.app.back_image, "king", "spade"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "diamond"),
            Card(8, self.app.back_image, "8", "club"),
        ]

        self.app._conclude_round()

        # Payout is 100 + int(100 * 1.5) = 250 -> 900 + 250 = 1150
        self.assertEqual(self.app.bankroll_var.get(), 1150)
        self.assertIn("+$150", self.app.result_var.get())

    def test_payout_resolution_player_loss(self):
        """Losing a hand in Chips Mode awards $0 return (wager lost)."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        # Player 17 vs Dealer 19
        self.app.player_hands = [[
            Card(10, self.app.back_image, "10", "heart"),
            Card(7, self.app.back_image, "7", "spade"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "diamond"),
            Card(9, self.app.back_image, "9", "club"),
        ]

        self.app._conclude_round()

        # Bankroll remains 950 (loss returned 0)
        self.assertEqual(self.app.bankroll_var.get(), 950)
        self.assertIn("-$50", self.app.result_var.get())

    def test_payout_resolution_push(self):
        """Push in Chips Mode refunds the original bet."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        # Player 18 vs Dealer 18
        self.app.player_hands = [[
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "diamond"),
            Card(8, self.app.back_image, "8", "club"),
        ]

        self.app._conclude_round()

        # Bankroll refunded by 50 -> 1000
        self.assertEqual(self.app.bankroll_var.get(), 1000)
        self.assertIn("Push", self.app.result_var.get())

    def test_split_with_chips_matching_bet(self):
        """Splitting in Chips Mode deducts a matching bet for Hand 2 and tracks both."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(900)
        self.app.hand_bets = [50]

        card1 = Card(8, self.app.back_image, "8", "heart")
        card2 = Card(8, self.app.back_image, "8", "spade")
        self.app.player_hands = [[card1, card2]]
        self.app.active_hand_index = 0

        self.app.on_split()

        # Bankroll should decrease by $50 for matching bet: 900 - 50 = 850
        self.assertEqual(self.app.bankroll_var.get(), 850)
        self.assertEqual(self.app.hand_bets, [50, 50])
        self.assertEqual(len(self.app.player_hands), 2)

    def test_split_disabled_if_insufficient_bankroll(self):
        """Splitting is disabled and blocked if bankroll cannot match the initial bet."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(20)  # Less than $50 bet
        self.app.hand_bets = [50]

        card1 = Card(8, self.app.back_image, "8", "heart")
        card2 = Card(8, self.app.back_image, "8", "spade")
        self.app.player_hands = [[card1, card2]]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "diamond"),
            Card(6, self.app.back_image, "6", "club"),
        ]

        self.app._check_initial_blackjack()
        self.assertEqual(self.app.split_button["state"], "disabled")

        # Calling on_split directly should return early without splitting
        self.app.on_split()
        self.assertEqual(len(self.app.player_hands), 1)
        self.assertEqual(self.app.bankroll_var.get(), 20)

    def test_split_round_resolution_with_chips(self):
        """Split hands pay out independently in Chips Mode."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(800)
        self.app.hand_bets = [100, 100]

        # Hand 1 = 20 (wins vs dealer 18), Hand 2 = 16 (loses vs dealer 18)
        hand1 = [Card(10, self.app.back_image, "10", "heart"), Card(10, self.app.back_image, "10", "spade")]
        hand2 = [Card(10, self.app.back_image, "10", "club"), Card(6, self.app.back_image, "6", "diamond")]
        self.app.player_hands = [hand1, hand2]
        self.app.dealer_hand = [
            Card(10, self.app.back_image, "10", "heart"),
            Card(8, self.app.back_image, "8", "spade"),
        ]

        self.app._conclude_round()

        # Hand 1 wins: +200 payout; Hand 2 loses: +0 payout. Total bankroll: 800 + 200 = 1000
        self.assertEqual(self.app.bankroll_var.get(), 1000)
        self.assertIn("+$100", self.app.result_var.get())
        self.assertIn("-$100", self.app.result_var.get())

    def test_rebuy_replenishes_bankroll(self):
        """When bankroll falls below MINIMUM_BET, Rebuy button restores $1,000."""
        self.app.chips_mode_var.set(True)
        self.app.bankroll_var.set(0)
        self.app.current_bet_var.set(0)
        self.app.new_game()

        self.assertEqual(self.app.rebuy_button["state"], "normal")
        self.assertIn("Bankroll empty", self.app.result_var.get())

        self.app._rebuy()

        self.assertEqual(self.app.bankroll_var.get(), STARTING_BANKROLL)
        self.assertEqual(self.app.current_bet_var.get(), 0)
        self.assertEqual(self.app.rebuy_button["state"], "disabled")

    def test_insurance_prompt_when_dealer_upcard_is_ace_in_chips_mode(self):
        """Dealer upcard Ace triggers insurance prompt in Chips Mode and pauses player actions."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        # Rig deck so dealer upcard is Ace
        card_ace = Card(1, self.app.back_image, rank="ace", suit="spade")
        card_7 = Card(7, self.app.back_image, rank="7", suit="heart")
        self.app.dealer_hand = [card_ace, card_7]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="heart"),
            Card(8, self.app.back_image, rank="8", suit="diamond"),
        ]]

        self.app._prompt_insurance()

        self.assertTrue(self.app.is_insurance_phase)
        self.assertTrue(bool(self.app.insurance_frame.grid_info()))
        self.assertEqual(self.app.hit_button["state"], "disabled")
        self.assertEqual(self.app.stand_button["state"], "disabled")
        self.assertEqual(self.app.split_button["state"], "disabled")
        self.assertEqual(self.app.new_game_button["state"], "disabled")
        self.assertEqual(self.app.take_insurance_button["state"], "normal")
        self.assertIn("$25", self.app.take_insurance_button["text"])

    def test_insurance_not_prompted_in_casual_mode(self):
        """Casual Mode (Chips OFF) never prompts for insurance even if dealer upcard is Ace."""
        self.app.chips_mode_var.set(False)
        self.app.new_game()

        # In Casual Mode, insurance frame must remain unmapped and phase False
        self.assertFalse(self.app.is_insurance_phase)
        self.assertFalse(bool(self.app.insurance_frame.grid_info()))

    def test_insurance_taken_dealer_has_blackjack_breakeven(self):
        """Taking insurance when dealer has Blackjack pays 2:1, resulting in net $0 loss."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        card_ace = Card(1, self.app.back_image, rank="ace", suit="spade")
        card_king = Card(10, self.app.back_image, rank="king", suit="heart")
        self.app.dealer_hand = [card_ace, card_king]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(9, self.app.back_image, rank="9", suit="club"),
        ]]

        self.app._prompt_insurance()

        # Take Insurance ($25 cost)
        self.app._on_take_insurance()

        # Bankroll was 950 - 25 (insurance cost) + 75 (insurance return: 25*3) + 0 (main bet lost) = 1000!
        self.assertEqual(self.app.bankroll_var.get(), 1000)
        self.assertFalse(self.app.is_insurance_phase)
        self.assertFalse(bool(self.app.insurance_frame.grid_info()))
        self.assertEqual(self.app.new_game_button["state"], "normal")
        self.assertIn("Insurance won", self.app.result_var.get())
        self.assertIn("+$50", self.app.result_var.get())

    def test_insurance_odd_bet_5_dollars_exact_breakeven(self):
        """Odd bet of $5 with $2 insurance payout rounds up to $5 profit, guaranteeing $0 net breakeven."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        # Initial bankroll 1000, player wagered $5 (bankroll = 995)
        self.app.bankroll_var.set(995)
        self.app.hand_bets = [5]

        card_ace = Card(1, self.app.back_image, rank="ace", suit="spade")
        card_king = Card(10, self.app.back_image, rank="king", suit="heart")
        self.app.dealer_hand = [card_ace, card_king]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="club"),
        ]]

        self.app._prompt_insurance()
        # Insurance cost is 5 // 2 = $2
        self.assertIn("$2", self.app.take_insurance_button["text"])

        # Take Insurance ($2 cost, bankroll becomes 995 - 2 = 993)
        self.app._on_take_insurance()

        # Dealer has Blackjack:
        # Main bet loses $5 (-$5)
        # Insurance returns $2 wager + $5 profit = $7 (+7)
        # Bankroll becomes 993 + 7 = 1000 (EXACTLY BREAK EVEN!)
        self.assertEqual(self.app.bankroll_var.get(), 1000)
        self.assertIn("Insurance won (+$5)", self.app.result_var.get())
        self.assertIn("(-$5)", self.app.result_var.get())

    def test_insurance_taken_dealer_does_not_have_blackjack_resumes_play(self):
        """Taking insurance when dealer lacks Blackjack consumes the insurance wager and resumes player turn."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        card_ace = Card(1, self.app.back_image, rank="ace", suit="spade")
        card_7 = Card(7, self.app.back_image, rank="7", suit="heart")
        self.app.dealer_hand = [card_ace, card_7]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="club"),
        ]]

        self.app._prompt_insurance()
        self.app._on_take_insurance()

        # Insurance lost: 950 - 25 = 925
        self.assertEqual(self.app.bankroll_var.get(), 925)
        self.assertFalse(self.app.is_insurance_phase)
        self.assertFalse(bool(self.app.insurance_frame.grid_info()))
        # Actions re-enabled for player's turn
        self.assertEqual(self.app.hit_button["state"], "normal")
        self.assertEqual(self.app.stand_button["state"], "normal")
        self.assertIn("Insurance lost", self.app.result_var.get())

    def test_insurance_declined_dealer_has_blackjack(self):
        """Declining insurance when dealer has Blackjack loses main bet without insurance payout."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        card_ace = Card(1, self.app.back_image, rank="ace", suit="spade")
        card_king = Card(10, self.app.back_image, rank="king", suit="heart")
        self.app.dealer_hand = [card_ace, card_king]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="club"),
        ]]

        self.app._prompt_insurance()
        self.app._on_decline_insurance()

        # Bankroll remains 950 (no insurance cost, main bet lost)
        self.assertEqual(self.app.bankroll_var.get(), 950)
        self.assertFalse(self.app.is_insurance_phase)
        self.assertNotIn("Insurance won", self.app.result_var.get())
        self.assertEqual(self.app.new_game_button["state"], "normal")

    def test_insurance_disabled_if_insufficient_bankroll(self):
        """Take insurance button is disabled if bankroll cannot cover the insurance wager."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(10)  # Main bet 50 requires 25 insurance, bankroll only 10
        self.app.hand_bets = [50]

        card_ace = Card(1, self.app.back_image, rank="ace", suit="spade")
        self.app.dealer_hand = [card_ace, Card(7, self.app.back_image, rank="7", suit="heart")]
        self.app.player_hands = [[
            Card(10, self.app.back_image, rank="10", suit="diamond"),
            Card(8, self.app.back_image, rank="8", suit="club"),
        ]]

        self.app._prompt_insurance()

        self.assertEqual(self.app.take_insurance_button["state"], "disabled")
        # Attempting to call _on_take_insurance directly does nothing
        self.app._on_take_insurance()
        self.assertEqual(self.app.bankroll_var.get(), 10)
        self.assertEqual(self.app.insurance_bet, 0)

    def test_insurance_taken_player_natural_blackjack_dealer_no_blackjack(self):
        """When player has Natural 21 and dealer lacks BJ, round concludes showing BJ win and insurance lost."""
        self.app.chips_mode_var.set(True)
        self.app.new_game()
        self.app.bankroll_var.set(950)
        self.app.hand_bets = [50]

        card_ace_dealer = Card(1, self.app.back_image, rank="ace", suit="spade")
        card_7_dealer = Card(7, self.app.back_image, rank="7", suit="heart")
        self.app.dealer_hand = [card_ace_dealer, card_7_dealer]

        card_ace_player = Card(1, self.app.back_image, rank="ace", suit="heart")
        card_king_player = Card(10, self.app.back_image, rank="king", suit="club")
        self.app.player_hands = [[card_ace_player, card_king_player]]

        self.app._prompt_insurance()
        # Take insurance ($25 cost: bankroll 950 - 25 = 925)
        self.app._on_take_insurance()

        # Dealer lacks Blackjack -> insurance lost (-$25)
        # Player has Natural Blackjack -> pays 3:2: $50 bet + $75 profit = $125 return
        # Net bankroll: 925 + 125 = 1050 (net +$50 profit, exactly Even Money!)
        self.assertEqual(self.app.bankroll_var.get(), 1050)
        self.assertFalse(self.app.is_insurance_phase)
        self.assertIn("Player has Blackjack! You win!", self.app.result_var.get())
        self.assertIn("+$75", self.app.result_var.get())
        self.assertIn("Insurance lost (-$25)", self.app.result_var.get())


if __name__ == "__main__":
    unittest.main()
