"""
Hi-Lo Card Counting Trainer and Simulation Engine for Blackjack.

Implements the standard casino Hi-Lo card counting strategy:
- Low cards (2-6): +1
- Neutral cards (7-9): 0
- High cards (10, J, Q, K, A): -1

Tracks:
- Running Count (RC): Net sum of all face-up cards seen since last shuffle.
- Decks Remaining: Estimation of remaining decks in shoe (minimum clamp 0.5).
- True Count (TC): RC / Decks Remaining.
- Bet Sizing Guide: Recommended bet multiplier based on positive True Count advantage.
- Quiz Evaluation: Checks player accuracy during training drills.
"""

from __future__ import annotations

from typing import Any, Optional


class HiLoCardCounter:
    """
    Core domain model for the Hi-Lo card counting subsystem.
    Maintains running and true counts strictly from observed face-up cards.
    """

    def __init__(self, deck_count: int = 6):
        self.deck_count = max(1, deck_count)
        self.running_count = 0
        self.observed_cards_count = 0

    def get_card_tag(self, card: Any) -> int:
        """
        Determines the Hi-Lo tag value for a given card:
        - 2, 3, 4, 5, 6 -> +1
        - 7, 8, 9 -> 0
        - 10, Jack, Queen, King, Ace -> -1
        """
        if card is None:
            return 0

        # Handle Card object, tuple, or primitive representation
        rank = getattr(card, "rank", None)
        value = getattr(card, "value", None)

        if rank is not None:
            r = str(rank).lower().strip()
            if r in ("2", "3", "4", "5", "6"):
                return 1
            if r in ("7", "8", "9"):
                return 0
            if r in ("10", "jack", "queen", "king", "ace"):
                return -1

        if value is not None:
            val = int(value)
            if 2 <= val <= 6:
                return 1
            if 7 <= val <= 9:
                return 0
            if val == 10 or val == 1:  # 1 is Ace in rules.py
                return -1

        return 0

    def observe_card(self, card: Any) -> int:
        """
        Observes a face-up card on the felt, updates Running Count, and returns the card tag.
        Dealer hole cards must NOT be passed to observe_card until flipped face up.
        """
        tag = self.get_card_tag(card)
        self.running_count += tag
        self.observed_cards_count += 1
        return tag

    def reset_shoe(self, deck_count: Optional[int] = None):
        """Resets the counter state on shoe shuffle."""
        if deck_count is not None:
            self.deck_count = max(1, deck_count)
        self.running_count = 0
        self.observed_cards_count = 0

    def decks_remaining(self, cards_remaining: int) -> float:
        """
        Calculates estimated decks remaining in the shoe with 0.5-deck minimum clamp.
        Formula: max(0.5, cards_remaining / 52.0)
        """
        decks = cards_remaining / 52.0
        return max(0.5, round(decks, 1))

    def true_count(self, cards_remaining: int) -> float:
        """
        Calculates the True Count:
        TC = Running Count / Decks Remaining
        """
        decks = self.decks_remaining(cards_remaining)
        return round(self.running_count / decks, 1)

    def get_recommended_bet(self, base_bet: int, true_count: float) -> int:
        """
        Recommends bet sizing in units based on positive player advantage:
        - TC <= 1: 1 unit
        - TC == 2: 2 units
        - TC == 3: 3 units
        - TC == 4: 4 units
        - TC >= 5: 5 units (capped at 5x base bet)
        """
        if true_count <= 1.0:
            units = 1
        elif true_count <= 2.0:
            units = 2
        elif true_count <= 3.0:
            units = 3
        elif true_count <= 4.0:
            units = 4
        else:
            units = 5

        return int(base_bet * units)

    def verify_quiz_answer(
        self,
        submitted_rc: int,
        submitted_tc: Optional[float] = None,
        cards_remaining: int = 0,
        tolerance_tc: float = 0.5,
    ) -> bool:
        """
        Validates player answers in counting drill challenges.
        """
        if submitted_rc != self.running_count:
            return False

        if submitted_tc is not None and cards_remaining > 0:
            actual_tc = self.true_count(cards_remaining)
            if abs(submitted_tc - actual_tc) > tolerance_tc:
                return False

        return True
