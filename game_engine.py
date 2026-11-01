"""
Headless Blackjack Domain Engine (`BlackjackEngine`).

Executes complete Blackjack rounds (betting, initial deal, hitting, standing,
doubling down, pair splitting, late surrender, dealer S17 drawing, and payout
settlement) with zero GUI or Tkinter dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from config import (
    BLACKJACK_TARGET,
    CUT_CARD_PENETRATION,
    DEFAULT_DECK_COUNT,
    MINIMUM_BET,
    STARTING_BANKROLL,
)
from event_bus import EventHub, GameEventType
from rules import (
    Card,
    Hand,
    RoundPhase,
    SideBetResult,
    build_shoe,
    calculate_insurance_payout,
    calculate_payout,
    dealer_should_hit,
    determine_outcome,
    evaluate_21_plus_3,
    evaluate_perfect_pairs,
)
from state_machine import GameStateMachine


@dataclass(frozen=True)
class RoundResult:
    """Outcome summary for an individual resolved player hand."""
    hand_index: int
    outcome: str
    message: str
    bet: int
    payout: int


def _build_default_template_deck() -> List[Card]:
    suits = ("spade", "heart", "diamond", "club")
    ranks = (
        ("ace", 1),
        ("2", 2),
        ("3", 3),
        ("4", 4),
        ("5", 5),
        ("6", 6),
        ("7", 7),
        ("8", 8),
        ("9", 9),
        ("10", 10),
        ("jack", 10),
        ("queen", 10),
        ("king", 10),
    )
    return [Card(val, None, rank=r, suit=s) for s in suits for r, val in ranks]


class BlackjackEngine:
    """Pure Python, headless Blackjack domain controller."""

    def __init__(
        self,
        bankroll: int = STARTING_BANKROLL,
        deck_count: int = DEFAULT_DECK_COUNT,
        event_bus: Optional[EventHub] = None,
    ):
        self.bankroll: int = bankroll
        self.deck_count: int = deck_count
        self.event_bus: EventHub = event_bus or EventHub()
        self.fsm: GameStateMachine = GameStateMachine(
            initial_phase=RoundPhase.BETTING,
            event_bus=self.event_bus,
        )

        self.template_cards: List[Card] = _build_default_template_deck()
        self.shoe: List[Card] = build_shoe(self.template_cards, self.deck_count)
        self.player_hands: List[Hand] = [Hand()]
        self.dealer_hand: Hand = Hand()
        self.active_hand_index: int = 0
        self.current_bet: int = 0
        self.staged_bet: int = 0
        self.insurance_bet: int = 0
        self.last_insurance_lost: int = 0
        self.hole_card_revealed: bool = False
        self.staged_side_bets: dict[str, int] = {"perfect_pairs": 0, "21_plus_3": 0}
        self.active_side_bets: dict[str, int] = {"perfect_pairs": 0, "21_plus_3": 0}

    @property
    def phase(self) -> RoundPhase:
        return self.fsm.phase

    def stage_bet(self, amount: int, sound_hint: str = "set") -> int:
        """Sets or clamps the staged bet and emits BET_STAGED."""
        old_bet = self.staged_bet
        clamped = max(0, min(amount, self.bankroll))
        self.staged_bet = clamped
        delta = self.staged_bet - old_bet
        self.event_bus.emit(
            GameEventType.BET_STAGED,
            {
                "staged_bet": self.staged_bet,
                "delta": delta,
                "bankroll": self.bankroll,
                "action": sound_hint,
            },
        )
        return self.staged_bet

    def commit_staged_bet(self, bet: Optional[int] = None) -> int:
        """Deducts staged bet from bankroll and sets up player hand bet."""
        actual_bet = self.staged_bet if bet is None else bet
        if actual_bet < MINIMUM_BET or actual_bet > self.bankroll:
            raise ValueError(f"Cannot commit invalid bet {actual_bet} with bankroll {self.bankroll}")
        self.bankroll -= actual_bet
        self.current_bet = actual_bet
        if self.player_hands:
            self.player_hands[0].bet = actual_bet
        self.event_bus.emit(
            GameEventType.BET_COMMITTED,
            {"bet": actual_bet, "bankroll": self.bankroll},
        )
        return actual_bet

    def stage_side_bet(self, bet_type: str, amount: int, sound_hint: str = "set") -> int:
        """Sets or clamps a staged side bet ('perfect_pairs' or '21_plus_3') bounded by available bankroll."""
        if bet_type not in self.staged_side_bets:
            return 0
        other_side = sum(v for k, v in self.staged_side_bets.items() if k != bet_type)
        max_allowed = max(0, self.bankroll - self.staged_bet - other_side)
        clamped = max(0, min(amount, max_allowed))
        self.staged_side_bets[bet_type] = clamped
        self.event_bus.emit(
            GameEventType.SIDE_BET_STAGED,
            {
                "bet_type": bet_type,
                "amount": clamped,
                "bankroll": self.bankroll,
                "action": sound_hint,
            },
        )
        return clamped

    def clear_side_bets(self, sound_hint: str = "clear") -> None:
        """Resets all staged side bets to 0."""
        self.staged_side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
        self.event_bus.emit(
            GameEventType.SIDE_BET_STAGED,
            {"bet_type": "all", "amount": 0, "bankroll": self.bankroll, "action": sound_hint},
        )

    def commit_side_bets(self, side_bets: Optional[dict[str, int]] = None) -> dict[str, int]:
        """Deducts staged side bets from bankroll and moves them to active_side_bets."""
        source = self.staged_side_bets if side_bets is None else side_bets
        total_side = sum(source.values())
        if total_side > self.bankroll:
            raise ValueError(f"Cannot commit side bets {source} exceeding bankroll {self.bankroll}")
        self.bankroll -= total_side
        self.active_side_bets = dict(source)
        self.staged_side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
        return self.active_side_bets

    def resolve_side_bets(
        self,
        player_hand: Optional[Hand] = None,
        dealer_upcard: Optional[Card] = None,
    ) -> dict[str, SideBetResult]:
        """Evaluates active side bets immediately after the initial deal, crediting payouts."""
        p_hand = self.player_hands[0] if player_hand is None else player_hand
        d_up = self.dealer_hand[0] if dealer_upcard is None and len(self.dealer_hand) > 0 else dealer_upcard

        results: dict[str, SideBetResult] = {}
        pp_bet = self.active_side_bets.get("perfect_pairs", 0)
        t13_bet = self.active_side_bets.get("21_plus_3", 0)

        pp_res = evaluate_perfect_pairs(p_hand, pp_bet)
        t13_res = evaluate_21_plus_3(p_hand, d_up, t13_bet)
        results["perfect_pairs"] = pp_res
        results["21_plus_3"] = t13_res

        total_payout = 0
        if pp_res.won:
            total_payout += pp_res.payout
        if t13_res.won:
            total_payout += t13_res.payout

        self.bankroll += total_payout
        self.active_side_bets = {"perfect_pairs": 0, "21_plus_3": 0}

        self.event_bus.emit(
            GameEventType.SIDE_BET_RESOLVED,
            {"results": results, "total_payout": total_payout, "bankroll": self.bankroll},
        )
        return results

    def rebuy(self, amount: int = STARTING_BANKROLL) -> int:
        """Replenishes bankroll if below MINIMUM_BET."""
        if self.bankroll < MINIMUM_BET and self.staged_bet < MINIMUM_BET:
            self.bankroll = amount
            self.staged_bet = 0
        return self.bankroll

    def reshuffle_shoe(self) -> None:
        """Rebuilds and shuffles the shoe from template cards."""
        self.shoe = build_shoe(self.template_cards, self.deck_count)
        self.event_bus.emit(
            GameEventType.SHOE_RESHUFFLED,
            {"deck_count": self.deck_count, "cards_remaining": len(self.shoe)},
        )

    def _draw(self, target: str = "player", is_hole: bool = False) -> Card:
        if not self.shoe:
            self.reshuffle_shoe()
        card = self.shoe.pop()
        self.event_bus.emit(
            GameEventType.CARD_DEALT,
            {"target": target, "card": card, "is_hole": is_hole},
        )
        # Check cut card penetration
        cut_threshold = int(len(self.template_cards) * self.deck_count * (1.0 - CUT_CARD_PENETRATION))
        if len(self.shoe) <= cut_threshold and self.phase in (RoundPhase.BETTING, RoundPhase.ROUND_OVER):
            self.reshuffle_shoe()
        return card

    def deal_round(self, bet: int = MINIMUM_BET) -> Tuple[Hand, Hand]:
        """Validates wager, deals initial 2 cards to player and dealer, and transitions state."""
        if bet < 0 or bet > self.bankroll:
            raise ValueError(f"Invalid bet {bet} for bankroll {self.bankroll}")

        self.bankroll -= bet
        self.current_bet = bet
        self.insurance_bet = 0
        self.hole_card_revealed = False
        self.active_hand_index = 0
        self.event_bus.emit(GameEventType.BET_COMMITTED, {"bet": bet, "bankroll": self.bankroll})

        self.fsm.transition_to(RoundPhase.INITIAL_DEAL, force=True)
        p_hand = Hand(bet=bet)
        d_hand = Hand()
        self.player_hands = [p_hand]
        self.dealer_hand = d_hand

        p_hand.add_card(self._draw("player"))
        p_hand.add_card(self._draw("player"))
        d_hand.add_card(self._draw("dealer", is_hole=False))
        d_hand.add_card(self._draw("dealer", is_hole=True))

        if d_hand[0].value == 1:
            self.fsm.transition_to(RoundPhase.INSURANCE)
        elif p_hand.score >= BLACKJACK_TARGET or d_hand.score >= BLACKJACK_TARGET:
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.fsm.transition_to(RoundPhase.PLAYER_TURN)

        return p_hand, d_hand

    def take_insurance(self, amount: Optional[int] = None) -> int:
        """Stages an insurance bet (up to half current bet) and advances phase."""
        if self.phase != RoundPhase.INSURANCE:
            raise ValueError(f"Insurance can only be taken during INSURANCE phase, current: {self.phase.value}")
        max_ins = self.current_bet // 2
        bet_amount = max_ins if amount is None else amount
        if bet_amount <= 0 or bet_amount > max_ins or bet_amount > self.bankroll:
            raise ValueError(f"Invalid insurance wager {bet_amount}")
        self.bankroll -= bet_amount
        self.insurance_bet = bet_amount
        self.last_insurance_lost = 0
        self.event_bus.emit(
            GameEventType.INSURANCE_TAKEN,
            {"bet": bet_amount, "bankroll": self.bankroll},
        )
        self._conclude_insurance_phase()
        return self.insurance_bet

    def decline_insurance(self) -> None:
        """Declines insurance wager and advances round."""
        if self.phase != RoundPhase.INSURANCE:
            raise ValueError(f"Insurance can only be declined during INSURANCE phase, current: {self.phase.value}")
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.event_bus.emit(GameEventType.INSURANCE_DECLINED, {})
        self._conclude_insurance_phase()

    def _conclude_insurance_phase(self) -> None:
        p_hand = self.player_hands[0]
        d_hand = self.dealer_hand
        dealer_has_bj = (len(d_hand) == 2 and d_hand.score == BLACKJACK_TARGET)
        if not dealer_has_bj and self.insurance_bet > 0:
            self.last_insurance_lost = self.insurance_bet
            self.insurance_bet = 0
        if dealer_has_bj or p_hand.score >= BLACKJACK_TARGET:
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.fsm.transition_to(RoundPhase.PLAYER_TURN)

    def reveal_hole_card(self) -> Optional[Card]:
        """Marks the dealer's hole card as revealed and emits HOLE_CARD_REVEALED."""
        if not self.hole_card_revealed and len(self.dealer_hand) >= 2:
            self.hole_card_revealed = True
            hole = self.dealer_hand[1]
            self.event_bus.emit(GameEventType.HOLE_CARD_REVEALED, {"card": hole})
            return hole
        return None

    def hit(self, hand_index: Optional[int] = None) -> Card:
        """Deals one card to the specified (or active) player hand."""
        idx = self.active_hand_index if hand_index is None else hand_index
        hand = self.player_hands[idx]
        card = self._draw("player")
        hand.add_card(card)
        if hand.is_bust:
            self.event_bus.emit(GameEventType.PLAYER_BUSTED, {"hand_index": idx, "score": hand.score})
            self._advance_turn_after_hand_done()
        elif hand.score == BLACKJACK_TARGET:
            self._advance_turn_after_hand_done()
        return card

    def stand(self, hand_index: Optional[int] = None) -> None:
        """Stands on the specified (or active) player hand and advances turn."""
        idx = self.active_hand_index if hand_index is None else hand_index
        self.player_hands[idx].is_stood = True
        self._advance_turn_after_hand_done()

    def double_down(self, hand_index: Optional[int] = None) -> Card:
        """Doubles the hand wager, draws 1 card, and stands."""
        idx = self.active_hand_index if hand_index is None else hand_index
        hand = self.player_hands[idx]
        if not hand.can_double or self.bankroll < hand.bet:
            raise ValueError("Hand is not eligible for double down")
        self.bankroll -= hand.bet
        hand.bet *= 2
        hand.is_doubled = True
        card = self._draw("player")
        hand.add_card(card)
        hand.is_stood = True
        if hand.is_bust:
            self.event_bus.emit(GameEventType.PLAYER_BUSTED, {"hand_index": idx, "score": hand.score})
        self._advance_turn_after_hand_done()
        return card

    def split(self, hand_index: int = 0) -> Tuple[Hand, Hand]:
        """Splits a matching 2-card hand into two independent hands."""
        hand = self.player_hands[hand_index]
        if not hand.can_split or self.bankroll < hand.bet:
            raise ValueError("Hand is not eligible to split")
        self.bankroll -= hand.bet
        c1, c2 = hand[0], hand[1]
        h1 = Hand([c1, self._draw("player")], bet=hand.bet, is_split=True)
        h2 = Hand([c2, self._draw("player")], bet=hand.bet, is_split=True)
        self.player_hands = [h1, h2]
        self.active_hand_index = 0
        self.event_bus.emit(GameEventType.HAND_SPLIT, {"hands": 2})
        return h1, h2

    def surrender(self, hand_index: int = 0) -> None:
        """Surrenders the initial 2-card hand, recovering half the bet."""
        hand = self.player_hands[hand_index]
        hand.is_surrendered = True
        hand.is_stood = True
        self.reveal_hole_card()
        self.fsm.transition_to(RoundPhase.RESOLUTION)

    def _advance_turn_after_hand_done(self) -> None:
        if self.active_hand_index < len(self.player_hands) - 1:
            self.active_hand_index += 1
            return
        all_done = all(h.is_bust or h.is_surrendered for h in self.player_hands)
        self.reveal_hole_card()
        if all_done:
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.fsm.transition_to(RoundPhase.DEALER_TURN)

    def dealer_step(self) -> Optional[Card]:
        """Draws one dealer card if dealer score < 17; returns None when dealer stands."""
        self.reveal_hole_card()
        if dealer_should_hit(self.dealer_hand):
            card = self._draw("dealer", is_hole=False)
            self.dealer_hand.add_card(card)
            if self.dealer_hand.is_bust:
                self.event_bus.emit(GameEventType.DEALER_BUSTED, {"score": self.dealer_hand.score})
            return card
        return None

    def resolve_outcomes(
        self,
        player_score_fn: Optional[Callable[[Hand], int]] = None,
        chips_mode: bool = True,
    ) -> List[RoundResult]:
        """Completes any remaining dealer draws, settles all player hands, and updates bankroll."""
        if self.phase == RoundPhase.DEALER_TURN:
            while dealer_should_hit(self.dealer_hand):
                self.dealer_step()
            self.fsm.transition_to(RoundPhase.RESOLUTION)

        results: List[RoundResult] = []
        is_split_round = len(self.player_hands) > 1

        # Settle insurance side bet if placed
        ins_profit = 0
        ins_str = ""
        if self.insurance_bet > 0:
            dealer_has_bj = len(self.dealer_hand) == 2 and self.dealer_hand.score == BLACKJACK_TARGET
            ins_payout = calculate_insurance_payout(dealer_has_bj, self.insurance_bet, self.current_bet)
            if chips_mode:
                self.bankroll += ins_payout
            if dealer_has_bj:
                ins_profit = ins_payout - self.insurance_bet
                ins_str = f" | Insurance won (+${ins_profit})"
            self.insurance_bet = 0
        elif self.last_insurance_lost > 0:
            ins_str = f" | Insurance lost (-${self.last_insurance_lost})"
            self.last_insurance_lost = 0

        outcomes: List[str] = []
        messages: List[str] = []
        payouts: List[int] = []
        profits: List[int] = []

        for idx, hand in enumerate(self.player_hands):
            if hand.is_surrendered:
                outcome, msg = "SURRENDER", "Surrendered."
            else:
                score_override = player_score_fn(hand) if player_score_fn else None
                outcome, msg = determine_outcome(
                    hand,
                    self.dealer_hand,
                    is_split=is_split_round or hand.is_split,
                    player_score_override=score_override,
                )
            payout = calculate_payout(outcome, hand.bet)
            profit = payout - hand.bet
            hand.outcome = outcome
            hand.net_payout = payout
            hand.is_settled = True
            if chips_mode:
                self.bankroll += payout
            res = RoundResult(hand_index=idx, outcome=outcome, message=msg, bet=hand.bet, payout=payout)
            results.append(res)
            outcomes.append(outcome)
            messages.append(msg)
            payouts.append(payout)
            profits.append(profit)

        total_profit = sum(profits)
        net_round = total_profit + ins_profit

        self.event_bus.emit(
            GameEventType.ROUND_RESOLVED,
            {
                "hand_index": 0,
                "outcome": outcomes[0] if outcomes else "",
                "payout": payouts[0] if payouts else 0,
                "results": results,
                "outcomes": outcomes,
                "messages": messages,
                "payouts": payouts,
                "profits": profits,
                "ins_profit": ins_profit,
                "ins_str": ins_str,
                "net_round": net_round,
                "bankroll": self.bankroll,
                "chips_mode": chips_mode,
            },
        )

        self.fsm.transition_to(RoundPhase.ROUND_OVER, force=True)
        return results
