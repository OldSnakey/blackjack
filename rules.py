"""
Pure, Stateless Blackjack Rules & Mathematical Evaluation.

Zero GUI or Tkinter dependencies:
This module contains pure Python domain logic and can be executed or tested in a
standard REPL, pytest, or CLI pipeline without initializing a display.

Provides:
- Card NamedTuple model (supporting indexing, unpacking, and rank/suit metadata).
- RoundPhase Enum for explicit, self-documenting game loop state.
- score_hand(): Optimal Ace valuation and bust detection.
- dealer_should_hit(): Standard casino Dealer S17 rule.
- can_split(): Pair detection for split hands.
- determine_outcome(): Comprehensive round resolution (Natural 21, busts, pushes, wins).
- calculate_payout(): Standard 1:1, 3:2 Natural Blackjack, and surrender payouts.
- calculate_insurance_payout(): 2:1 insurance side bet resolution with odd-bet rounding.
- breakdown_chips(): Greedy chip denomination decomposition.
- build_shoe(): Multi-deck shoe creation and shuffling.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, NamedTuple, Optional

from config import (
    BLACKJACK_TARGET,
    DEALER_STAND_THRESHOLD,
    DEFAULT_DECK_COUNT,
    INSURANCE_PAYOUT_RATIO,
)


class RoundPhase(Enum):
    """Explicit state machine phases for a Blackjack round."""
    BETTING = "betting"
    INSURANCE = "insurance"
    PLAYER_TURN = "player_turn"
    DEALER_TURN = "dealer_turn"
    ROUND_OVER = "round_over"


class Card(tuple):
    """
    Lightweight, educational representation of a playing card.
    Inherits from tuple (value, image) for 100% backward compatibility:
      - Tuple indexing: card[0] -> value, card[1] -> PhotoImage
      - 2-tuple unpacking: val, img = card
      - Length: len(card) == 2
    Also exposes clean dot-attribute access:
      - card.value, card.image, card.rank, card.suit
    """
    rank: str
    suit: str

    def __new__(cls, value: int, image: Any = None, rank: str = "", suit: str = ""):
        card = super().__new__(cls, (value, image))
        card.rank = rank
        card.suit = suit
        return card

    @property
    def value(self) -> int:
        return self[0]

    @property
    def image(self) -> Any:
        return self[1]

    def __repr__(self) -> str:
        r = self.rank or str(self.value)
        s = f" of {self.suit}" if self.suit else ""
        return f"Card({r}{s}, val={self.value})"


def score_hand(hand) -> int:
    """
    Calculates the best Blackjack score for a hand.

    Args:
        hand: A list of card values (integers 1-10) or card tuples/Card instances.

    Returns:
        int: The optimal score (up to 21, or lowest bust score).

    How Ace handling works:
    - Number cards (2-10) count as their face value.
    - Face cards (Jack, Queen, King) have value 10.
    - Aces initially count as 1. If promoting one Ace to 11 does not cause
      the total score to exceed 21, 10 is added. At most ONE Ace can count as 11,
      because 11 + 11 = 22 > 21.
    """
    values = [card[0] if isinstance(card, (tuple, list)) else card for card in hand]
    score = sum(values)
    if 1 in values and score + 10 <= BLACKJACK_TARGET:
        score += 10
    return score


def dealer_should_hit(dealer_hand) -> bool:
    """
    Determines if the dealer must draw another card.
    Under standard casino S17 rules, the dealer must hit on any score below 17.
    """
    return score_hand(dealer_hand) < DEALER_STAND_THRESHOLD


def can_split(player_hand) -> bool:
    """
    Determines if a hand is eligible to split.
    A hand is eligible if it contains exactly two cards of the same rank (or value).
    """
    if len(player_hand) != 2:
        return False
    card1, card2 = player_hand
    rank1 = getattr(card1, "rank", None)
    rank2 = getattr(card2, "rank", None)
    if rank1 is not None and rank2 is not None:
        return rank1 == rank2
    val1 = card1[0] if isinstance(card1, (tuple, list)) else card1
    val2 = card2[0] if isinstance(card2, (tuple, list)) else card2
    return val1 == val2


def determine_outcome(
    player_hand,
    dealer_hand,
    is_split: bool = False,
    player_score_override: Optional[int] = None,
) -> tuple[str, str]:
    """
    Evaluates the final result of a round once both player and dealer have completed their turns.

    Args:
        player_hand: List of card values or Card instances for the player.
        dealer_hand: List of card values or Card instances for the dealer.
        is_split: Whether this hand originated from a split. Split 21s cannot be Natural Blackjacks.
        player_score_override: Optional explicit score to use for player (e.g. from blessings).

    Returns:
        tuple[str, str]: (outcome_code, display_message)
    """
    player_score = player_score_override if player_score_override is not None else score_hand(player_hand)
    dealer_score = score_hand(dealer_hand)

    # 1. Player Bust
    if player_score > BLACKJACK_TARGET:
        return "PLAYER_BUST", "You bust, dealer wins!"

    # Check for natural blackjacks (2 cards totaling 21 on initial deal, un-split)
    player_natural = (not is_split and len(player_hand) == 2 and player_score == BLACKJACK_TARGET)
    dealer_natural = (len(dealer_hand) == 2 and dealer_score == BLACKJACK_TARGET)

    if player_natural and dealer_natural:
        return "PUSH", "Both have Blackjack! It's a draw."
    if player_natural:
        return "NATURAL_BLACKJACK", "Player has Blackjack! You win!"
    if dealer_natural:
        return "DEALER_WINS", "Dealer has Blackjack! Dealer wins!"

    # 2. Dealer Bust
    if dealer_score > BLACKJACK_TARGET:
        return "DEALER_BUST", "Dealer busts, Player WINS!"

    # 3. Compare Scores
    if player_score > dealer_score:
        return "PLAYER_WINS", "Player WINS!"
    elif dealer_score > player_score:
        return "DEALER_WINS", "The dealer wins!"
    else:
        return "PUSH", "It's a draw"


def calculate_payout(outcome: str, bet: int) -> int:
    """
    Calculates the total payout (return of wager plus winnings) for a given outcome and bet.

    Args:
        outcome: Outcome code from determine_outcome ('NATURAL_BLACKJACK', 'PLAYER_WINS',
                 'DEALER_BUST', 'PUSH', 'SURRENDER', 'DEALER_WINS', 'PLAYER_BUST').
        bet: The amount wagered on this hand (integer >= 0).

    Returns:
        int: Total return to the player (0 for loss, bet for push, 2*bet for standard win,
             bet + int(bet * 1.5) for 3:2 natural blackjack, bet // 2 for surrender).
    """
    if bet <= 0:
        return 0
    if outcome == "NATURAL_BLACKJACK":
        return bet + int(bet * 1.5)
    elif outcome in ("PLAYER_WINS", "DEALER_BUST"):
        return bet * 2
    elif outcome == "PUSH":
        return bet
    elif outcome == "SURRENDER":
        return bet // 2
    else:
        # 'DEALER_WINS', 'PLAYER_BUST', or any other loss outcome
        return 0


def calculate_insurance_payout(dealer_has_blackjack: bool, insurance_bet: int, main_bet: int = 0) -> int:
    """
    Calculates the total payout returned for an Insurance side bet.
    Insurance pays 2:1. When main_bet is specified and insurance_bet is full insurance
    for an odd wager (e.g. $2 insurance on a $5 bet), the payout is rounded up to fully
    cover the main bet, guaranteeing a $0 net breakeven round. Partial insurance wagers
    pay standard 2:1.

    Args:
        dealer_has_blackjack: True if the dealer has a 2-card 21 (Natural Blackjack).
        insurance_bet: The amount wagered on insurance (integer >= 0).
        main_bet: The original main bet being insured (optional integer >= 0).

    Returns:
        int: Total return to the player (original insurance_bet + profit).
    """
    if insurance_bet <= 0 or not dealer_has_blackjack:
        return 0
    if main_bet > 0 and insurance_bet == main_bet // 2:
        profit = max(main_bet, insurance_bet * INSURANCE_PAYOUT_RATIO)
        return insurance_bet + profit
    return insurance_bet + (insurance_bet * INSURANCE_PAYOUT_RATIO)


def breakdown_chips(amount: int) -> list[tuple[int, int]]:
    """
    Decomposes an integer wager into denomination counts greedily from highest to lowest.
    Supported denominations: $500, $100, $25, $5, and $1 (silver remainder).

    Args:
        amount: Integer wager amount (>= 0).

    Returns:
        list[tuple[int, int]]: List of (denomination, count) pairs for denominations with count > 0.
    """
    if amount <= 0:
        return []
    result = []
    remaining = amount
    for denom in (500, 100, 25, 5, 1):
        count = remaining // denom
        if count > 0:
            result.append((denom, count))
            remaining %= denom
    return result


def build_shoe(all_cards, num_decks: int = DEFAULT_DECK_COUNT) -> list:
    """
    Creates and shuffles a multi-deck shoe from template Card instances.

    Args:
        all_cards: List of 52 unique Card instances.
        num_decks: Number of standard 52-card decks in the shoe.

    Returns:
        list[Card]: Shuffled list containing (52 * num_decks) cards.
    """
    shoe = []
    for _ in range(num_decks):
        shoe.extend(all_cards)
    random.shuffle(shoe)
    return shoe


@dataclass
class BasicStrategyDecision:
    """
    Statistically optimal basic strategy decision recommendation.
    """
    action: str  # "HIT", "STAND", "DOUBLE", "SPLIT", "SURRENDER"
    label: str   # "Hit", "Stand", "Double Down", "Split Pair", "Surrender"
    reason: str  # Contextual reasoning for the recommendation


def get_basic_strategy_decision(
    player_hand: list,
    dealer_upcard: Any,
    can_double: bool = True,
    can_split: bool = False,
    can_surrender: bool = True,
) -> BasicStrategyDecision:
    """
    Evaluates statistically optimal Blackjack basic strategy (4-8 decks, Dealer stands on 17).

    Returns:
        BasicStrategyDecision with optimal action ('HIT', 'STAND', 'DOUBLE', 'SPLIT', 'SURRENDER').
    """
    if not player_hand or dealer_upcard is None:
        return BasicStrategyDecision("STAND", "Stand", "No active hand")

    # Normalize dealer upcard value (Ace -> 11, Face cards -> 10, else 2..9)
    up_val = dealer_upcard[0] if isinstance(dealer_upcard, (tuple, list)) else getattr(dealer_upcard, "value", dealer_upcard)
    if up_val == 1:
        up_val = 11

    # Extract card values
    values = [c[0] if isinstance(c, (tuple, list)) else getattr(c, "value", c) for c in player_hand]
    score = score_hand(player_hand)
    num_cards = len(player_hand)

    # 1. Check Pair Splitting (if exactly 2 cards and can_split)
    if num_cards == 2 and can_split:
        p_val = values[0]
        # Aces
        if p_val == 1:
            return BasicStrategyDecision("SPLIT", "Split Pair", "Aces always split for maximum winning potential")
        # 8s
        if p_val == 8:
            return BasicStrategyDecision("SPLIT", "Split Pair", "Pair of 8s (16) splits to escape worst starting hand")
        # 10s
        if p_val == 10:
            return BasicStrategyDecision("STAND", "Stand", "Never split 20 against any dealer upcard")
        # 9s
        if p_val == 9:
            if up_val in (7, 10, 11):
                return BasicStrategyDecision("STAND", "Stand", "Pair of 9s (18) stands against 7, 10, or Ace")
            return BasicStrategyDecision("SPLIT", "Split Pair", f"Pair of 9s splits against dealer {up_val}")
        # 7s
        if p_val == 7:
            if 2 <= up_val <= 7:
                return BasicStrategyDecision("SPLIT", "Split Pair", f"Pair of 7s splits against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Pair of 7s hits against dealer {up_val}")
        # 6s
        if p_val == 6:
            if 2 <= up_val <= 6:
                return BasicStrategyDecision("SPLIT", "Split Pair", f"Pair of 6s splits against dealer bust card {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Pair of 6s hits against dealer {up_val}")
        # 5s - Never split 5s!
        if p_val == 5:
            if can_double and 2 <= up_val <= 9:
                return BasicStrategyDecision("DOUBLE", "Double Down", f"Pair of 5s (10) doubles against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Pair of 5s (10) hits against dealer {up_val}")
        # 4s
        if p_val == 4:
            if 5 <= up_val <= 6 and can_double:
                return BasicStrategyDecision("SPLIT", "Split Pair", f"Pair of 4s splits against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Pair of 4s hits against dealer {up_val}")
        # 2s and 3s
        if p_val in (2, 3):
            if 2 <= up_val <= 7:
                return BasicStrategyDecision("SPLIT", "Split Pair", f"Pair of {p_val}s splits against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Pair of {p_val}s hits against dealer {up_val}")

    # 2. Check Surrender (if 2 cards, can_surrender)
    if num_cards == 2 and can_surrender:
        if score == 16 and up_val in (9, 10, 11):
            return BasicStrategyDecision("SURRENDER", "Surrender", f"Hard 16 surrenders against high dealer card {up_val}")
        if score == 15 and up_val == 10:
            return BasicStrategyDecision("SURRENDER", "Surrender", "Hard 15 surrenders against dealer 10")

    # 3. Check Soft Hands (contains an Ace counted as 11)
    is_soft = (1 in values and sum(values) + 10 <= 21)
    if is_soft:
        if score >= 20:
            return BasicStrategyDecision("STAND", "Stand", f"Soft {score} always stands")
        if score == 19:
            if up_val == 6 and can_double and num_cards == 2:
                return BasicStrategyDecision("DOUBLE", "Double Down", "Soft 19 doubles against dealer 6")
            return BasicStrategyDecision("STAND", "Stand", "Soft 19 stands")
        if score == 18:
            if 3 <= up_val <= 6 and can_double and num_cards == 2:
                return BasicStrategyDecision("DOUBLE", "Double Down", f"Soft 18 doubles against dealer {up_val}")
            if up_val in (2, 7, 8):
                return BasicStrategyDecision("STAND", "Stand", f"Soft 18 stands against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Soft 18 hits against dealer {up_val}")
        if score == 17:
            if 3 <= up_val <= 6 and can_double and num_cards == 2:
                return BasicStrategyDecision("DOUBLE", "Double Down", f"Soft 17 doubles against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Soft 17 hits against dealer {up_val}")
        if score in (15, 16):
            if 4 <= up_val <= 6 and can_double and num_cards == 2:
                return BasicStrategyDecision("DOUBLE", "Double Down", f"Soft {score} doubles against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Soft {score} hits against dealer {up_val}")
        if score in (13, 14):
            if 5 <= up_val <= 6 and can_double and num_cards == 2:
                return BasicStrategyDecision("DOUBLE", "Double Down", f"Soft {score} doubles against dealer {up_val}")
            return BasicStrategyDecision("HIT", "Hit", f"Soft {score} hits against dealer {up_val}")

    # 4. Hard Hands
    if score >= 17:
        return BasicStrategyDecision("STAND", "Stand", f"Hard {score} always stands")
    if 13 <= score <= 16:
        if 2 <= up_val <= 6:
            return BasicStrategyDecision("STAND", "Stand", f"Hard {score} stands, dealer shows bust card {up_val}")
        return BasicStrategyDecision("HIT", "Hit", f"Hard {score} hits against dealer {up_val}")
    if score == 12:
        if 4 <= up_val <= 6:
            return BasicStrategyDecision("STAND", "Stand", f"Hard 12 stands against dealer bust card {up_val}")
        return BasicStrategyDecision("HIT", "Hit", f"Hard 12 hits against dealer {up_val}")
    if score == 11:
        if can_double and num_cards == 2:
            return BasicStrategyDecision("DOUBLE", "Double Down", f"11 doubles down against dealer {up_val}")
        return BasicStrategyDecision("HIT", "Hit", f"11 hits against dealer {up_val}")
    if score == 10:
        if can_double and num_cards == 2 and 2 <= up_val <= 9:
            return BasicStrategyDecision("DOUBLE", "Double Down", f"10 doubles down against dealer {up_val}")
        return BasicStrategyDecision("HIT", "Hit", f"10 hits against dealer {up_val}")
    if score == 9:
        if can_double and num_cards == 2 and 3 <= up_val <= 6:
            return BasicStrategyDecision("DOUBLE", "Double Down", f"9 doubles down against dealer {up_val}")
        return BasicStrategyDecision("HIT", "Hit", f"9 hits against dealer {up_val}")

    return BasicStrategyDecision("HIT", "Hit", f"Hard {score} always hits")

