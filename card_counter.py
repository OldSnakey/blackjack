"""
Hi-Lo Card Counting Trainer, Simulation Engine, and Illustrious 18 Strategy Deviations.

Implements the standard casino Hi-Lo card counting strategy:
- Low cards (2-6): +1
- Neutral cards (7-9): 0
- High cards (10, J, Q, K, A): -1

Tracks:
- Running Count (RC): Net sum of all face-up cards seen since last shuffle.
- Decks Remaining: Estimation of remaining decks in shoe (minimum clamp 0.5).
- True Count (TC): RC / Decks Remaining.
- Bet Sizing Guide: Recommended bet multiplier based on positive True Count advantage.
- The Illustrious 18: Index play strategy deviations optimizing player advantage.
- Quiz Evaluation: Checks player accuracy during training drills.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Optional
from config import DEFAULT_DECK_COUNT


@dataclass(frozen=True)
class Illustrious18Rule:
    """
    Specification for one of Don Schlesinger's Illustrious 18 strategy index plays.
    """
    rule_id: str
    rank_order: int
    label: str
    player_total: Optional[int]
    dealer_upcard: int
    is_pair: bool
    is_insurance: bool
    index_tc: float
    action_at_or_above: str
    action_below: str
    basic_action: str
    explanation: str


@dataclass(frozen=True)
class StrategyDeviation:
    """
    Result of evaluating an Illustrious 18 rule against the current True Count.
    """
    rule_id: str
    label: str
    index_tc: float
    recommended_action: str
    basic_action: str
    is_deviation_active: bool
    condition_str: str = ""
    badge_text: str = ""
    explanation: str = ""


@dataclass(frozen=True)
class DeviationQuizQuestion:
    """
    Drill quiz question testing the player's knowledge of the Illustrious 18.
    """
    rule_id: str
    true_count: float
    player_hand_desc: str
    dealer_upcard_desc: str
    prompt: str
    options: tuple[str, ...]
    correct_action: str
    explanation: str


# Canonical 18-play Illustrious 18 table
ILLUSTRIOUS_18_RULES: tuple[Illustrious18Rule, ...] = (
    Illustrious18Rule(
        rule_id="insurance",
        rank_order=1,
        label="Insurance",
        player_total=None,
        dealer_upcard=11,
        is_pair=False,
        is_insurance=True,
        index_tc=3.0,
        action_at_or_above="INSURANCE",
        action_below="DECLINE",
        basic_action="DECLINE",
        explanation="Take Insurance at TC >= +3.0",
    ),
    Illustrious18Rule(
        rule_id="16_vs_10",
        rank_order=2,
        label="16 vs 10",
        player_total=16,
        dealer_upcard=10,
        is_pair=False,
        is_insurance=False,
        index_tc=0.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="HIT",
        explanation="Stand on 16 vs 10 at TC >= 0.0",
    ),
    Illustrious18Rule(
        rule_id="15_vs_10",
        rank_order=3,
        label="15 vs 10",
        player_total=15,
        dealer_upcard=10,
        is_pair=False,
        is_insurance=False,
        index_tc=4.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="HIT",
        explanation="Stand on 15 vs 10 at TC >= +4.0",
    ),
    Illustrious18Rule(
        rule_id="10_10_vs_5",
        rank_order=4,
        label="10-10 vs 5",
        player_total=20,
        dealer_upcard=5,
        is_pair=True,
        is_insurance=False,
        index_tc=5.0,
        action_at_or_above="SPLIT",
        action_below="STAND",
        basic_action="STAND",
        explanation="Split 10-10 vs 5 at TC >= +5.0",
    ),
    Illustrious18Rule(
        rule_id="10_10_vs_6",
        rank_order=5,
        label="10-10 vs 6",
        player_total=20,
        dealer_upcard=6,
        is_pair=True,
        is_insurance=False,
        index_tc=4.0,
        action_at_or_above="SPLIT",
        action_below="STAND",
        basic_action="STAND",
        explanation="Split 10-10 vs 6 at TC >= +4.0",
    ),
    Illustrious18Rule(
        rule_id="10_vs_10",
        rank_order=6,
        label="10 vs 10",
        player_total=10,
        dealer_upcard=10,
        is_pair=False,
        is_insurance=False,
        index_tc=4.0,
        action_at_or_above="DOUBLE",
        action_below="HIT",
        basic_action="HIT",
        explanation="Double on 10 vs 10 at TC >= +4.0",
    ),
    Illustrious18Rule(
        rule_id="12_vs_3",
        rank_order=7,
        label="12 vs 3",
        player_total=12,
        dealer_upcard=3,
        is_pair=False,
        is_insurance=False,
        index_tc=2.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="HIT",
        explanation="Stand on 12 vs 3 at TC >= +2.0",
    ),
    Illustrious18Rule(
        rule_id="12_vs_2",
        rank_order=8,
        label="12 vs 2",
        player_total=12,
        dealer_upcard=2,
        is_pair=False,
        is_insurance=False,
        index_tc=3.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="HIT",
        explanation="Stand on 12 vs 2 at TC >= +3.0",
    ),
    Illustrious18Rule(
        rule_id="11_vs_A",
        rank_order=9,
        label="11 vs A",
        player_total=11,
        dealer_upcard=11,
        is_pair=False,
        is_insurance=False,
        index_tc=1.0,
        action_at_or_above="DOUBLE",
        action_below="HIT",
        basic_action="HIT",
        explanation="Double on 11 vs A at TC >= +1.0",
    ),
    Illustrious18Rule(
        rule_id="9_vs_2",
        rank_order=10,
        label="9 vs 2",
        player_total=9,
        dealer_upcard=2,
        is_pair=False,
        is_insurance=False,
        index_tc=1.0,
        action_at_or_above="DOUBLE",
        action_below="HIT",
        basic_action="HIT",
        explanation="Double on 9 vs 2 at TC >= +1.0",
    ),
    Illustrious18Rule(
        rule_id="10_vs_A",
        rank_order=11,
        label="10 vs A",
        player_total=10,
        dealer_upcard=11,
        is_pair=False,
        is_insurance=False,
        index_tc=4.0,
        action_at_or_above="DOUBLE",
        action_below="HIT",
        basic_action="HIT",
        explanation="Double on 10 vs A at TC >= +4.0",
    ),
    Illustrious18Rule(
        rule_id="9_vs_7",
        rank_order=12,
        label="9 vs 7",
        player_total=9,
        dealer_upcard=7,
        is_pair=False,
        is_insurance=False,
        index_tc=3.0,
        action_at_or_above="DOUBLE",
        action_below="HIT",
        basic_action="HIT",
        explanation="Double on 9 vs 7 at TC >= +3.0",
    ),
    Illustrious18Rule(
        rule_id="16_vs_9",
        rank_order=13,
        label="16 vs 9",
        player_total=16,
        dealer_upcard=9,
        is_pair=False,
        is_insurance=False,
        index_tc=5.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="HIT",
        explanation="Stand on 16 vs 9 at TC >= +5.0",
    ),
    Illustrious18Rule(
        rule_id="13_vs_2",
        rank_order=14,
        label="13 vs 2",
        player_total=13,
        dealer_upcard=2,
        is_pair=False,
        is_insurance=False,
        index_tc=-1.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="STAND",
        explanation="Stand on 13 vs 2 at TC >= -1.0 (Hit if TC < -1.0)",
    ),
    Illustrious18Rule(
        rule_id="12_vs_4",
        rank_order=15,
        label="12 vs 4",
        player_total=12,
        dealer_upcard=4,
        is_pair=False,
        is_insurance=False,
        index_tc=0.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="STAND",
        explanation="Stand on 12 vs 4 at TC >= 0.0 (Hit if TC < 0.0)",
    ),
    Illustrious18Rule(
        rule_id="12_vs_5",
        rank_order=16,
        label="12 vs 5",
        player_total=12,
        dealer_upcard=5,
        is_pair=False,
        is_insurance=False,
        index_tc=-2.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="STAND",
        explanation="Stand on 12 vs 5 at TC >= -2.0 (Hit if TC < -2.0)",
    ),
    Illustrious18Rule(
        rule_id="12_vs_6",
        rank_order=17,
        label="12 vs 6",
        player_total=12,
        dealer_upcard=6,
        is_pair=False,
        is_insurance=False,
        index_tc=-1.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="STAND",
        explanation="Stand on 12 vs 6 at TC >= -1.0 (Hit if TC < -1.0)",
    ),
    Illustrious18Rule(
        rule_id="13_vs_3",
        rank_order=18,
        label="13 vs 3",
        player_total=13,
        dealer_upcard=3,
        is_pair=False,
        is_insurance=False,
        index_tc=-2.0,
        action_at_or_above="STAND",
        action_below="HIT",
        basic_action="STAND",
        explanation="Stand on 13 vs 3 at TC >= -2.0 (Hit if TC < -2.0)",
    ),
)

ILLUSTRIOUS_18_MAP: dict[str, Illustrious18Rule] = {r.rule_id: r for r in ILLUSTRIOUS_18_RULES}


class HiLoCardCounter:
    """
    Core domain model for the Hi-Lo card counting subsystem.
    Maintains running and true counts strictly from observed face-up cards.
    """

    def __init__(self, deck_count: int = DEFAULT_DECK_COUNT):
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

    def get_player_advantage(self, cards_remaining: int) -> float:
        """
        Estimates player advantage percentage based on True Count:
        Advantage (%) = -0.5% + (0.5% * TC)
        """
        tc = self.true_count(cards_remaining)
        return round(-0.5 + (0.5 * tc), 2)

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

    def evaluate_rule(self, rule_id: str, true_count: float) -> StrategyDeviation:
        """
        Evaluates an individual Illustrious 18 rule against a given True Count.
        """
        rule = ILLUSTRIOUS_18_MAP[rule_id]
        is_at_or_above = round(true_count, 1) >= round(rule.index_tc, 1)
        rec_action = rule.action_at_or_above if is_at_or_above else rule.action_below
        is_active = (rec_action != rule.basic_action)

        # Build condition string
        sign = "+" if rule.index_tc > 0 else ""
        if rule.action_below != rule.basic_action:
            # Negative index deviation triggers when TC < index
            cond_str = f"TC < {sign}{rule.index_tc:g}"
        else:
            cond_str = f"TC >= {sign}{rule.index_tc:g}"

        badge_text = f"⚡ DEVIATION: {rec_action.capitalize()} ({cond_str})" if is_active else ""

        return StrategyDeviation(
            rule_id=rule.rule_id,
            label=rule.label,
            index_tc=rule.index_tc,
            recommended_action=rec_action,
            basic_action=rule.basic_action,
            is_deviation_active=is_active,
            condition_str=cond_str,
            badge_text=badge_text,
            explanation=rule.explanation,
        )

    def evaluate_hand_deviation(
        self,
        player_hand: list,
        dealer_upcard: Any,
        true_count: Optional[float] = None,
        cards_remaining: int = 208,
        can_double: bool = True,
        can_split: bool = True,
        is_insurance_phase: bool = False,
    ) -> Optional[StrategyDeviation]:
        """
        Determines if the active hand matchup against dealer upcard triggers any Illustrious 18 index play.
        """
        if dealer_upcard is None:
            return None

        tc = true_count if true_count is not None else self.true_count(cards_remaining)

        # Normalize dealer upcard value (Ace -> 11, Face -> 10, else 2..9)
        up_val = dealer_upcard[0] if isinstance(dealer_upcard, (tuple, list)) else getattr(dealer_upcard, "value", dealer_upcard)
        if up_val == 1:
            up_val = 11

        # 1. Insurance phase
        if is_insurance_phase:
            if up_val == 11:
                return self.evaluate_rule("insurance", tc)
            return None

        if not player_hand:
            return None

        # Extract values
        values = [c[0] if isinstance(c, (tuple, list)) else getattr(c, "value", c) for c in player_hand]
        raw_score = sum(values)

        # Soft hand check: Illustrious 18 does NOT apply to soft hands (soft hands use ace as 11)
        is_soft = (1 in values and raw_score + 10 <= 21)
        if is_soft:
            return None

        num_cards = len(player_hand)
        score = raw_score
        if score > 21:
            return None

        # 2. Check 10-10 pair split (10-10 vs 5, 10-10 vs 6)
        if num_cards == 2 and can_split and (values[0] == 10 and values[1] == 10):
            if up_val == 5:
                return self.evaluate_rule("10_10_vs_5", tc)
            if up_val == 6:
                return self.evaluate_rule("10_10_vs_6", tc)

        # 3. Check Hard Totals
        # Hard 16
        if score == 16:
            if up_val == 10:
                return self.evaluate_rule("16_vs_10", tc)
            if up_val == 9:
                return self.evaluate_rule("16_vs_9", tc)

        # Hard 15
        if score == 15 and up_val == 10:
            return self.evaluate_rule("15_vs_10", tc)

        # Hard 13
        if score == 13:
            if up_val == 2:
                return self.evaluate_rule("13_vs_2", tc)
            if up_val == 3:
                return self.evaluate_rule("13_vs_3", tc)

        # Hard 12
        if score == 12:
            if up_val == 2:
                return self.evaluate_rule("12_vs_2", tc)
            if up_val == 3:
                return self.evaluate_rule("12_vs_3", tc)
            if up_val == 4:
                return self.evaluate_rule("12_vs_4", tc)
            if up_val == 5:
                return self.evaluate_rule("12_vs_5", tc)
            if up_val == 6:
                return self.evaluate_rule("12_vs_6", tc)

        # Doubling deviations (require exactly 2 cards and can_double)
        if num_cards == 2 and can_double:
            if score == 11 and up_val == 11:
                return self.evaluate_rule("11_vs_A", tc)
            if score == 10:
                if up_val == 10:
                    return self.evaluate_rule("10_vs_10", tc)
                if up_val == 11:
                    return self.evaluate_rule("10_vs_A", tc)
            if score == 9:
                if up_val == 2:
                    return self.evaluate_rule("9_vs_2", tc)
                if up_val == 7:
                    return self.evaluate_rule("9_vs_7", tc)

        return None

    def get_active_deviation(
        self,
        player_hand: list,
        dealer_upcard: Any,
        true_count: Optional[float] = None,
        cards_remaining: int = 208,
        can_double: bool = True,
        can_split: bool = True,
        is_insurance_phase: bool = False,
    ) -> Optional[StrategyDeviation]:
        """
        Convenience wrapper returning the StrategyDeviation ONLY when it is active (overriding basic strategy).
        """
        dev = self.evaluate_hand_deviation(
            player_hand=player_hand,
            dealer_upcard=dealer_upcard,
            true_count=true_count,
            cards_remaining=cards_remaining,
            can_double=can_double,
            can_split=can_split,
            is_insurance_phase=is_insurance_phase,
        )
        if dev and dev.is_deviation_active:
            return dev
        return None

    def generate_deviation_question(
        self,
        rule_id: Optional[str] = None,
        true_count: Optional[float] = None,
    ) -> DeviationQuizQuestion:
        """
        Generates a challenge question testing player mastery of an Illustrious 18 index play.
        """
        if rule_id is not None:
            rule = ILLUSTRIOUS_18_MAP[rule_id]
        else:
            rule = random.choice(ILLUSTRIOUS_18_RULES)

        if true_count is not None:
            tc = round(true_count, 1)
        else:
            # Generate a realistic TC around the threshold
            offset = random.choice([-2.0, -1.0, 0.0, 1.0, 2.0])
            tc = round(rule.index_tc + offset, 1)

        dev = self.evaluate_rule(rule.rule_id, tc)

        up_str = "Ace" if rule.dealer_upcard == 11 else str(rule.dealer_upcard)
        if rule.is_insurance:
            hand_desc = "any hand (Dealer shows Ace)"
            prompt = f"True Count is {tc:+.1f}. Dealer shows an Ace. Do you take Insurance or Decline?"
            options = ("INSURANCE", "DECLINE")
        elif rule.is_pair:
            hand_desc = "10,10"
            prompt = f"True Count is {tc:+.1f}. You hold a pair of 10s against Dealer {up_str}. Do you Split or Stand?"
            options = ("STAND", "SPLIT")
        elif rule.action_at_or_above == "DOUBLE":
            hand_desc = f"Hard {rule.player_total}"
            prompt = f"True Count is {tc:+.1f}. You hold {rule.player_total} against Dealer {up_str}. Do you Hit or Double?"
            options = ("HIT", "DOUBLE")
        else:
            hand_desc = f"Hard {rule.player_total}"
            prompt = f"True Count is {tc:+.1f}. You hold {rule.player_total} against Dealer {up_str}. Do you Hit or Stand?"
            options = ("HIT", "STAND")

        return DeviationQuizQuestion(
            rule_id=rule.rule_id,
            true_count=tc,
            player_hand_desc=hand_desc,
            dealer_upcard_desc=up_str,
            prompt=prompt,
            options=options,
            correct_action=dev.recommended_action,
            explanation=f"Illustrious 18 #{rule.rank_order} ({rule.label}): {rule.explanation}. At TC {tc:+.1f}, correct action is {dev.recommended_action}.",
        )

    def verify_deviation_quiz_answer(
        self,
        question: DeviationQuizQuestion,
        submitted_action: str,
    ) -> bool:
        """
        Validates the player's submitted deviation decision.
        """
        if not submitted_action:
            return False
        return submitted_action.strip().upper() == question.correct_action.strip().upper()

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

    # Method aliases for compatibility
    tag_card = get_card_tag
    on_card_revealed = observe_card
    on_shuffle = reset_shoe
    get_true_count = true_count
    get_decks_remaining = decks_remaining
