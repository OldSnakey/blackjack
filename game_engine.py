"""
Headless Blackjack Domain Engine (`BlackjackEngine`).

Executes complete Blackjack rounds (betting, initial deal, hitting, standing,
doubling down, pair splitting, late surrender, dealer S17 drawing, and payout
settlement) with zero GUI or Tkinter dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

from config import BLACKJACK_TARGET, DEFAULT_DECK_COUNT, MINIMUM_BET, STARTING_BANKROLL
from event_bus import EventHub, GameEventType
from rules import (
    Card,
    Hand,
    RoundPhase,
    build_shoe,
    calculate_payout,
    dealer_should_hit,
    determine_outcome,
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
        self.insurance_bet: int = 0
        self.hole_card_revealed: bool = False

    @property
    def phase(self) -> RoundPhase:
        return self.fsm.phase

    def _draw(self, target: str = "player", is_hole: bool = False) -> Card:
        if not self.shoe:
            self.shoe = build_shoe(self.template_cards, self.deck_count)
        card = self.shoe.pop()
        self.event_bus.emit(
            GameEventType.CARD_DEALT,
            {"target": target, "card": card, "is_hole": is_hole},
        )
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

        if p_hand.score >= BLACKJACK_TARGET or d_hand.score >= BLACKJACK_TARGET:
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.fsm.transition_to(RoundPhase.PLAYER_TURN)

        return p_hand, d_hand

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

    def resolve_outcomes(self) -> List[RoundResult]:
        """Completes any remaining dealer draws, settles all player hands, and updates bankroll."""
        if self.phase == RoundPhase.DEALER_TURN:
            while dealer_should_hit(self.dealer_hand):
                self.dealer_step()
            self.fsm.transition_to(RoundPhase.RESOLUTION)

        results: List[RoundResult] = []
        is_split_round = len(self.player_hands) > 1
        for idx, hand in enumerate(self.player_hands):
            if hand.is_surrendered:
                outcome, msg = "SURRENDER", "Surrendered."
            else:
                outcome, msg = determine_outcome(hand, self.dealer_hand, is_split=is_split_round or hand.is_split)
            payout = calculate_payout(outcome, hand.bet)
            hand.outcome = outcome
            hand.net_payout = payout
            hand.is_settled = True
            self.bankroll += payout
            res = RoundResult(hand_index=idx, outcome=outcome, message=msg, bet=hand.bet, payout=payout)
            results.append(res)
            self.event_bus.emit(
                GameEventType.ROUND_RESOLVED,
                {"hand_index": idx, "outcome": outcome, "payout": payout, "bankroll": self.bankroll},
            )

        self.fsm.transition_to(RoundPhase.ROUND_OVER)
        return results
