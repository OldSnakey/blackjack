"""
Headless Blackjack Domain Engine (`BlackjackEngine`).

Executes complete Blackjack rounds (betting, initial deal, hitting, standing,
doubling down, pair splitting, late surrender, dealer S17 drawing, and payout
settlement) with zero GUI or Tkinter dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, List, Optional, Tuple

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
    HouseRules,
    Player,
    RoundPhase,
    Seat,
    SideBetResult,
    build_shoe,
    calculate_insurance_payout,
    calculate_payout,
    can_double_down_hand,
    can_surrender_hand,
    clamp_main_bet,
    cut_card_threshold,
    dealer_should_hit,
    determine_outcome,
    effective_minimum_bet,
    evaluate_21_plus_3,
    evaluate_perfect_pairs,
)
from state_machine import GameStateMachine

if TYPE_CHECKING:
    from card_counter import HiLoCardCounter
    from tripometer import TripometerTracker


@dataclass(frozen=True)
class RoundResult:
    """Outcome summary for an individual resolved player hand."""
    seat_index: int = 2
    hand_index: int = 0
    outcome: str = ""
    message: str = ""
    bet: int = 0
    payout: int = 0


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
        rules: Optional[HouseRules] = None,
        tripometer: Optional[TripometerTracker] = None,
        card_counter: Optional[HiLoCardCounter] = None,
        table_seats: int = 1,
    ):
        self.player: Player = Player(bankroll=bankroll)
        if rules is not None:
            self.house_rules: HouseRules = rules.normalized()
            self.deck_count: int = self.house_rules.deck_count
        else:
            self.house_rules = (
                HouseRules(deck_count=deck_count).normalized()
                if deck_count != DEFAULT_DECK_COUNT
                else HouseRules()
            )
            self.deck_count = deck_count
        self.table_seats: int = max(1, int(table_seats))
        self.tripometer: Optional[TripometerTracker] = tripometer
        self.card_counter: Optional[HiLoCardCounter] = card_counter
        self._engine_round_active: bool = False
        self._bets_deducted_on_stage: bool = False
        self._round_start_bankroll: int = bankroll

        self.event_bus: EventHub = event_bus or EventHub()
        self.fsm: GameStateMachine = GameStateMachine(
            initial_phase=RoundPhase.BETTING,
            event_bus=self.event_bus,
        )

        self.template_cards: List[Card] = _build_default_template_deck()
        self._shoe: List[Card] = build_shoe(self.template_cards, self.deck_count)
        self._shoe_from_engine: bool = True
        self.seats: List[Seat] = [Seat(1), Seat(2), Seat(3)]
        self.seats[1].hands = [Hand()]
        self.active_seat_index: int = 2
        self.dealer_hand: Hand = Hand()
        self.active_hand_index: int = 0
        self.staged_bet: int = 0
        self.insurance_bet: int = 0
        self.last_insurance_lost: int = 0
        self.hole_card_revealed: bool = False
        self.staged_side_bets: dict[str, int] = {"perfect_pairs": 0, "21_plus_3": 0}
        self.active_side_bets: dict[str, int] = {"perfect_pairs": 0, "21_plus_3": 0}

    @property
    def shoe(self) -> List[Card]:
        return self._shoe

    @shoe.setter
    def shoe(self, cards: List[Card]) -> None:
        self._shoe = list(cards)
        self._shoe_from_engine = len(self._shoe) >= (len(self.template_cards) * self.deck_count)

    def get_round_bankroll(self) -> int:
        """Returns invariant pre-deal round bankroll across un-staged and staged chips."""
        if self._bets_deducted_on_stage:
            staged_total = sum(s.main_bet + sum(s.side_bets.values()) for s in self.seats)
            return self.bankroll + staged_total
        return self.bankroll

    def apply_house_rules(self, rules: HouseRules) -> bool:
        """
        Commits new HouseRules when between rounds (BETTING or ROUND_OVER),
        refunding uncommitted bets, rebuilding the shoe, and resetting attached HiLoCardCounter.
        """
        if self.phase not in (RoundPhase.BETTING, RoundPhase.ROUND_OVER):
            return False

        if self._bets_deducted_on_stage and self.phase == RoundPhase.BETTING:
            self.clear_all_bets()
        else:
            self.staged_bet = 0
            self.staged_side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
            if self.phase == RoundPhase.BETTING:
                for s in self.seats:
                    s.main_bet = 0
                    s.side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
                    s.is_active = False

        self.house_rules = rules.normalized()
        self.deck_count = self.house_rules.deck_count
        self._engine_round_active = False
        self._bets_deducted_on_stage = False
        self.reshuffle_shoe()
        return True

    @property
    def bankroll(self) -> int:
        return self.player.bankroll

    @bankroll.setter
    def bankroll(self, val: int) -> None:
        self.player.bankroll = val

    def get_seat(self, seat_idx: Optional[int]) -> Optional[Seat]:
        """Returns Seat by 1-based index (1..3), or None if seat_idx is None or invalid."""
        if seat_idx is not None and 1 <= seat_idx <= len(self.seats):
            return self.seats[seat_idx - 1]
        return None

    def get_active_seats(self) -> List[Seat]:
        """Returns ordered list of active seats with staged main bets."""
        return [s for s in self.seats if s.is_active and s.main_bet > 0]

    def start_play(self) -> Optional[int]:
        """Initializes turn progression at the first active seat, returning its seat_index (or None if none)."""
        active = self.get_active_seats()
        if not active:
            self.active_seat_index = None
            self.active_hand_index = 0
            return None
        self.active_seat_index = active[0].seat_index
        self.active_hand_index = 0
        return self.active_seat_index

    @property
    def player_hands(self) -> List[Hand]:
        if hasattr(self, "seats") and self.seats:
            if self.active_seat_index is not None:
                active = self.get_seat(self.active_seat_index)
                if active and active.hands:
                    return active.hands
            if len(self.seats) >= 2 and self.seats[1].hands:
                return self.seats[1].hands
        return []

    @player_hands.setter
    def player_hands(self, hands: List[Hand]) -> None:
        if hasattr(self, "seats") and self.seats:
            if self.active_seat_index is not None:
                active = self.get_seat(self.active_seat_index)
                if active:
                    active.hands = list(hands)
            if len(self.seats) >= 2:
                self.seats[1].hands = list(hands)

    @property
    def current_bet(self) -> int:
        if hasattr(self, "seats") and self.seats:
            if self.active_seat_index is not None:
                active = self.get_seat(self.active_seat_index)
                if active and active.main_bet > 0:
                    return active.main_bet
            return self.seats[1].main_bet if len(self.seats) >= 2 else 0
        return 0

    @current_bet.setter
    def current_bet(self, val: int) -> None:
        if hasattr(self, "seats") and self.seats:
            if self.active_seat_index is not None:
                active = self.get_seat(self.active_seat_index)
                if active:
                    active.main_bet = val
            if len(self.seats) >= 2:
                self.seats[1].main_bet = val

    @property
    def phase(self) -> RoundPhase:
        return self.fsm.phase

    def stage_bet(
        self,
        amount_or_seat: int,
        amount: Optional[int] = None,
        sound_hint: str = "set",
        seat_idx: Optional[int] = None,
    ) -> int:
        """
        Stages a bet for a given seat or legacy single-seat.
        If called with (seat_idx, amount) or keyword seat_idx:
          Deducts amount from bankroll, adds to Seat[seat_idx].main_bet, sets is_active = True.
        If called with (amount) only (legacy):
          Sets staged_bet on Seat 2 (Center) without deducting from bankroll until committed.
        """
        if amount is not None or seat_idx is not None:
            target_seat = seat_idx if seat_idx is not None else amount_or_seat
            actual_amount = amount if amount is not None else amount_or_seat
            if target_seat is None:
                target_seat = 2
            seat = self.get_seat(target_seat)
            if not seat:
                return 0
            self._bets_deducted_on_stage = True
            r_bankroll = self.get_round_bankroll()
            if 0 < r_bankroll < self.house_rules.minimum_bet:
                if any(other.seat_index != seat.seat_index and other.main_bet > 0 for other in self.seats):
                    return seat.main_bet

            room_to_max = (
                max(0, self.house_rules.maximum_bet - seat.main_bet)
                if self.house_rules.maximum_bet > 0
                else self.bankroll
            )
            clamped = max(0, min(actual_amount, self.bankroll, room_to_max))
            self.bankroll -= clamped
            seat.main_bet += clamped
            seat.is_active = (seat.main_bet > 0)
            self.staged_bet = sum(s.main_bet for s in self.seats)
            self.event_bus.emit(
                GameEventType.BET_STAGED,
                {
                    "seat_index": target_seat,
                    "amount": seat.main_bet,
                    "staged_bet": self.staged_bet,
                    "delta": clamped,
                    "bankroll": self.bankroll,
                    "action": sound_hint,
                },
            )
            return seat.main_bet
        else:
            self._bets_deducted_on_stage = False
            old_bet = self.staged_bet
            clamped = clamp_main_bet(amount_or_seat, self.house_rules, self.bankroll)
            self.staged_bet = clamped
            if hasattr(self, "seats") and len(self.seats) >= 2:
                self.seats[1].main_bet = clamped
                self.seats[1].is_active = (clamped > 0)
            delta = self.staged_bet - old_bet
            self.event_bus.emit(
                GameEventType.BET_STAGED,
                {
                    "seat_index": 2,
                    "staged_bet": self.staged_bet,
                    "amount": clamped,
                    "delta": delta,
                    "bankroll": self.bankroll,
                    "action": sound_hint,
                },
            )
            return self.staged_bet

    def clear_bet(self, seat_idx: int) -> int:
        """Refunds main and side bets on Seat[seat_idx] to bankroll, resets to 0, sets is_active = False."""
        seat = self.get_seat(seat_idx)
        refund = seat.main_bet + sum(seat.side_bets.values())
        self.bankroll += refund
        seat.main_bet = 0
        seat.side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
        seat.is_active = False
        self.staged_bet = sum(s.main_bet for s in self.seats)
        self.event_bus.emit(
            GameEventType.BET_STAGED,
            {
                "seat_index": seat_idx,
                "amount": 0,
                "delta": -refund,
                "bankroll": self.bankroll,
                "action": "clear",
            },
        )
        return refund

    def clear_all_bets(self) -> int:
        """Clears and refunds all active seats."""
        total_refund = 0
        for s in self.seats:
            if s.is_active or s.main_bet > 0 or any(s.side_bets.values()):
                total_refund += self.clear_bet(s.seat_index)
        self._bets_deducted_on_stage = False
        return total_refund

    def commit_staged_bet(self, bet: Optional[int] = None) -> int:
        """Deducts staged bet from bankroll (if not already deducted) and sets up player hand bet."""
        actual_bet = self.staged_bet if bet is None else bet
        if bet is not None:
            r_bankroll = self.bankroll
            eff_min = effective_minimum_bet(self.house_rules, r_bankroll)
            if (
                actual_bet < eff_min
                or actual_bet > self.bankroll
                or (self.house_rules.maximum_bet > 0 and actual_bet > self.house_rules.maximum_bet)
            ):
                raise ValueError(f"Cannot commit invalid bet {actual_bet} with bankroll {self.bankroll}")
            self.bankroll -= actual_bet
            self._bets_deducted_on_stage = False
            self.current_bet = actual_bet
            self.seats[1].main_bet = actual_bet
            self.seats[1].is_active = True
            self.seats[1].hands = [Hand(bet=actual_bet)]
        elif self._bets_deducted_on_stage:
            r_bankroll = self.get_round_bankroll()
            eff_min = effective_minimum_bet(self.house_rules, r_bankroll)
            active = [s for s in self.seats if s.is_active and s.main_bet > 0]
            if not active:
                raise ValueError("No active bets staged to commit")
            if 0 < r_bankroll < self.house_rules.minimum_bet:
                if len(active) > 1 or active[0].main_bet != r_bankroll:
                    raise ValueError("Sub-minimum bankroll recovery requires single-seat All-In")
            else:
                for s in active:
                    if s.main_bet < eff_min or (
                        self.house_rules.maximum_bet > 0 and s.main_bet > self.house_rules.maximum_bet
                    ):
                        raise ValueError(f"Seat {s.seat_index} bet {s.main_bet} violates table limits")
            for s in active:
                if not s.hands:
                    s.hands = [Hand(bet=s.main_bet)]
        else:
            for s in self.seats:
                if s.is_active and s.main_bet > 0 and not s.hands:
                    s.hands = [Hand(bet=s.main_bet)]
        self.event_bus.emit(
            GameEventType.BET_COMMITTED,
            {"bet": actual_bet, "bankroll": self.bankroll},
        )
        return actual_bet

    def stage_side_bet(
        self,
        bet_type: str,
        amount: int,
        sound_hint: str = "set",
        seat_idx: Optional[int] = None,
    ) -> int:
        """Sets or clamps a staged side bet ('perfect_pairs' or '21_plus_3') for a seat or legacy mode."""
        if seat_idx is not None:
            seat = self.get_seat(seat_idx)
            if bet_type not in seat.side_bets:
                return 0
            curr = seat.side_bets.get(bet_type, 0)
            delta = amount - curr
            clamped_delta = max(-curr, min(delta, self.bankroll))
            self.bankroll -= clamped_delta
            seat.side_bets[bet_type] = curr + clamped_delta
            self.event_bus.emit(
                GameEventType.SIDE_BET_STAGED,
                {
                    "seat_index": seat_idx,
                    "bet_type": bet_type,
                    "amount": seat.side_bets[bet_type],
                    "bankroll": self.bankroll,
                    "action": sound_hint,
                },
            )
            return seat.side_bets[bet_type]

        if bet_type not in self.staged_side_bets:
            return 0
        other_side = sum(v for k, v in self.staged_side_bets.items() if k != bet_type)
        max_allowed = max(0, self.bankroll - self.staged_bet - other_side)
        clamped = max(0, min(amount, max_allowed))
        self.staged_side_bets[bet_type] = clamped
        self.event_bus.emit(
            GameEventType.SIDE_BET_STAGED,
            {
                "seat_index": 2,
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
        seat_idx: Optional[int] = None,
    ) -> dict[str, Any]:
        """Evaluates active side bets immediately after the initial deal, crediting payouts."""
        if seat_idx is not None:
            seat = self.get_seat(seat_idx)
            p_hand = seat.hands[0] if (seat and seat.hands) else (self.player_hands[0] if self.player_hands else None)
            pp_bet = seat.side_bets.get("perfect_pairs", 0) if seat else 0
            t13_bet = seat.side_bets.get("21_plus_3", 0) if seat else 0
        else:
            seat = None
            p_hand = self.player_hands[0] if (player_hand is None and self.player_hands) else player_hand
            pp_bet = self.active_side_bets.get("perfect_pairs", 0)
            t13_bet = self.active_side_bets.get("21_plus_3", 0)

        d_up = self.dealer_hand[0] if (dealer_upcard is None and len(self.dealer_hand) > 0) else dealer_upcard

        results: dict[str, Any] = {}
        pp_res = evaluate_perfect_pairs(p_hand, pp_bet) if p_hand else None
        t13_res = evaluate_21_plus_3(p_hand, d_up, t13_bet) if (p_hand and d_up) else None
        results["perfect_pairs"] = pp_res
        results["21_plus_3"] = t13_res
        results["pairs_payout"] = pp_res.payout if (pp_res and pp_res.won) else 0
        results["twenty_one_plus_three_payout"] = t13_res.payout if (t13_res and t13_res.won) else 0

        total_payout = results["pairs_payout"] + results["twenty_one_plus_three_payout"]
        self.bankroll += total_payout
        if seat:
            seat.side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
        else:
            self.active_side_bets = {"perfect_pairs": 0, "21_plus_3": 0}

        self.event_bus.emit(
            GameEventType.SIDE_BET_RESOLVED,
            {"results": results, "total_payout": total_payout, "bankroll": self.bankroll, "seat_index": seat_idx},
        )
        return results

    def rebuy(self, amount: int = STARTING_BANKROLL) -> int:
        """Replenishes bankroll strictly when total round_bankroll <= 0."""
        if self.get_round_bankroll() <= 0:
            self.clear_all_bets()
            self.bankroll = amount
            self.staged_bet = 0
            self._bets_deducted_on_stage = False
        return self.bankroll

    def reshuffle_shoe(self) -> None:
        """Rebuilds and shuffles the shoe from template cards and resets attached card_counter."""
        self._shoe = build_shoe(self.template_cards, self.deck_count)
        self._shoe_from_engine = True
        if self.card_counter is not None:
            self.card_counter.reset_shoe(self.deck_count)
        self.event_bus.emit(
            GameEventType.SHOE_RESHUFFLED,
            {"deck_count": self.deck_count, "cards_remaining": len(self._shoe)},
        )

    def _live_true_count(self) -> float:
        if self.card_counter is not None:
            return self.card_counter.true_count(len(self._shoe))
        return 0.0

    def _record_engine_action(self, seat: Seat, s_idx: int, h_idx: int, hand: Hand, action: str) -> None:
        if not self._engine_round_active or self.tripometer is None or not self.dealer_hand:
            return
        is_split_h = len(seat.hands) > 1 or hand.is_split
        self.tripometer.record_decision(
            seat_idx=s_idx,
            hand_idx=h_idx,
            cards=list(hand.cards),
            dealer_upcard=self.dealer_hand[0],
            action=action,
            live_tc=self._live_true_count(),
            can_split=(len(seat.hands) == 1 and hand.can_split and self.bankroll >= hand.bet),
            can_double=can_double_down_hand(hand, self.house_rules, self.bankroll, is_split_hand=is_split_h),
            can_surrender=can_surrender_hand(hand, self.house_rules, is_split_hand=is_split_h),
            is_split_hand=is_split_h,
            auto=False,
        )

    def _draw(self, target: str = "player", is_hole: bool = False) -> Card:
        if not self._shoe:
            self.reshuffle_shoe()
        card = self._shoe.pop()
        if not is_hole and self._engine_round_active and self.card_counter is not None:
            self.card_counter.observe_card(card)
        self.event_bus.emit(
            GameEventType.CARD_DEALT,
            {"target": target, "card": card, "is_hole": is_hole},
        )
        # Check cut card penetration (remaining-card threshold, never inverted)
        cut_threshold = cut_card_threshold(self.deck_count, self.table_seats, CUT_CARD_PENETRATION)
        if (
            self._shoe_from_engine
            and len(self._shoe) <= cut_threshold
            and self.phase in (RoundPhase.BETTING, RoundPhase.ROUND_OVER)
        ):
            self.reshuffle_shoe()
        return card

    def deal_round(self, bet: Optional[int] = None) -> Tuple[Any, Hand]:
        """
        Validates wager, deals initial cards in clockwise casino order, and transitions state.
        If bet is not None: Legacy single-seat dealing to Seat 2.
        If bet is None: Multi-seat dealing across active seats in clockwise order (1 -> 2 -> 3).
        """
        self.insurance_bet = 0
        self.hole_card_revealed = False

        if bet is not None:
            if bet < 0 or bet > self.bankroll:
                raise ValueError(f"Invalid bet {bet} for bankroll {self.bankroll}")
            if bet > 0:
                eff_min = effective_minimum_bet(self.house_rules, self.bankroll)
                if bet < eff_min or (
                    self.house_rules.maximum_bet > 0 and bet > self.house_rules.maximum_bet
                ):
                    raise ValueError(f"Bet {bet} violates table limits for bankroll {self.bankroll}")

            pre_round_bankroll = self.bankroll
            cut_threshold = cut_card_threshold(self.deck_count, max(1, self.table_seats), CUT_CARD_PENETRATION)
            if not self._shoe or (self._shoe_from_engine and len(self._shoe) <= cut_threshold):
                self.reshuffle_shoe()

            pre_deal_tc = self._live_true_count()
            self._round_start_bankroll = pre_round_bankroll
            self._engine_round_active = True
            self._bets_deducted_on_stage = False

            if self.tripometer is not None:
                self.tripometer.begin_round(
                    self.house_rules,
                    pre_deal_tc=pre_deal_tc,
                    seat_bets={2: bet},
                    round_bankroll=pre_round_bankroll,
                    chips_mode=(bet > 0),
                )

            self.bankroll -= bet
            self.current_bet = bet
            self.seats[0].is_active = False
            self.seats[0].hands = []
            self.seats[1].main_bet = bet
            self.seats[1].is_active = True
            p_hand = Hand(bet=bet)
            self.seats[1].hands = [p_hand]
            self.seats[2].is_active = False
            self.seats[2].hands = []
            self.active_seat_index = 2
            self.active_hand_index = 0
            self.event_bus.emit(GameEventType.BET_COMMITTED, {"bet": bet, "bankroll": self.bankroll})

            self.fsm.transition_to(RoundPhase.INITIAL_DEAL, force=True)
            d_hand = Hand()
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
        else:
            active_seats = [s for s in self.seats if s.is_active and s.main_bet > 0]
            if not active_seats:
                raise ValueError("No active bets staged on table")
            active_seats.sort(key=lambda s: s.seat_index)

            r_bankroll = self.get_round_bankroll()
            eff_min = effective_minimum_bet(self.house_rules, r_bankroll)
            if 0 < r_bankroll < self.house_rules.minimum_bet:
                if len(active_seats) > 1 or active_seats[0].main_bet != r_bankroll:
                    raise ValueError("Sub-minimum bankroll recovery requires single-seat All-In")
            else:
                for s in active_seats:
                    if s.main_bet < eff_min or (
                        self.house_rules.maximum_bet > 0 and s.main_bet > self.house_rules.maximum_bet
                    ):
                        raise ValueError(f"Seat {s.seat_index} bet {s.main_bet} violates table limits")

            needed_seats = max(self.table_seats, len(active_seats))
            cut_threshold = cut_card_threshold(self.deck_count, needed_seats, CUT_CARD_PENETRATION)
            if not self._shoe or (self._shoe_from_engine and len(self._shoe) <= cut_threshold):
                self.reshuffle_shoe()

            pre_deal_tc = self._live_true_count()
            self._round_start_bankroll = r_bankroll
            self._engine_round_active = True
            self._bets_deducted_on_stage = False

            if self.tripometer is not None:
                self.tripometer.begin_round(
                    self.house_rules,
                    pre_deal_tc=pre_deal_tc,
                    seat_bets={s.seat_index: s.main_bet for s in active_seats},
                    round_bankroll=r_bankroll,
                    chips_mode=True,
                )

            for s in self.seats:
                if s.is_active and s.main_bet > 0:
                    s.hands = [Hand(bet=s.main_bet)]
                    s.is_resolved = False
                else:
                    s.hands = []
                    s.is_resolved = True

            self.fsm.transition_to(RoundPhase.INITIAL_DEAL, force=True)
            # Round 1: Card 1 to active seats (1 -> 2 -> 3)
            for s in active_seats:
                c = self._draw("player")
                s.hands[0].add_card(c)
                self.event_bus.emit(
                    GameEventType.CARD_DEALT,
                    {"card": c, "seat_index": s.seat_index, "hand_index": 0, "is_dealer": False},
                )

            # Dealer Hole Card (face down)
            hole_card = self._draw("dealer", is_hole=True)

            # Round 2: Card 2 to active seats (1 -> 2 -> 3)
            for s in active_seats:
                c = self._draw("player")
                s.hands[0].add_card(c)
                self.event_bus.emit(
                    GameEventType.CARD_DEALT,
                    {"card": c, "seat_index": s.seat_index, "hand_index": 0, "is_dealer": False},
                )

            # Dealer Upcard (face up)
            upcard = self._draw("dealer", is_hole=False)
            self.dealer_hand = Hand([upcard, hole_card])

            self.active_seat_index = active_seats[0].seat_index
            self.active_hand_index = 0

            if upcard.value == 1:
                self.fsm.transition_to(RoundPhase.INSURANCE)
            elif self.dealer_hand.score >= BLACKJACK_TARGET or all(
                s.hands[0].score >= BLACKJACK_TARGET for s in active_seats
            ):
                self.reveal_hole_card()
                self.fsm.transition_to(RoundPhase.RESOLUTION)
            else:
                self.fsm.transition_to(RoundPhase.PLAYER_TURN)

            return [s.hands[0] for s in active_seats], self.dealer_hand

    def take_insurance(self, amount: Optional[int] = None) -> int:
        """Stages an insurance bet (up to half current bet) and advances phase."""
        if self.phase != RoundPhase.INSURANCE:
            raise ValueError(f"Insurance can only be taken during INSURANCE phase, current: {self.phase.value}")
        max_ins = self.current_bet // 2
        bet_amount = max_ins if amount is None else amount
        if bet_amount <= 0 or bet_amount > max_ins or bet_amount > self.bankroll:
            raise ValueError(f"Invalid insurance wager {bet_amount}")
        if self._engine_round_active and self.tripometer is not None:
            s_idx = self.active_seat_index or 2
            self.tripometer.record_insurance_decision(
                seat_idx=s_idx,
                took_insurance=True,
                live_tc=self._live_true_count(),
                can_afford=True,
            )
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
        if self._engine_round_active and self.tripometer is not None:
            active_seats = [s for s in self.seats if s.is_active and s.hands]
            live_tc = self._live_true_count()
            for s in active_seats:
                req = s.main_bet // 2
                can_aff = (req > 0 and self.bankroll >= req)
                self.tripometer.record_insurance_decision(
                    seat_idx=s.seat_index,
                    took_insurance=False,
                    live_tc=live_tc,
                    can_afford=can_aff,
                )
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.event_bus.emit(GameEventType.INSURANCE_DECLINED, {})
        self._conclude_insurance_phase()

    def _conclude_insurance_phase(self) -> None:
        active_seats = [s for s in self.seats if s.is_active and s.hands]
        d_hand = self.dealer_hand
        dealer_has_bj = (len(d_hand) == 2 and d_hand.score == BLACKJACK_TARGET)
        if not dealer_has_bj and self.insurance_bet > 0:
            self.last_insurance_lost = self.insurance_bet
            self.insurance_bet = 0
        all_players_done = bool(active_seats) and all(
            s.hands[0].score >= BLACKJACK_TARGET for s in active_seats
        )
        if dealer_has_bj or all_players_done:
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.fsm.transition_to(RoundPhase.PLAYER_TURN)

    def reveal_hole_card(self) -> Optional[Card]:
        """Marks the dealer's hole card as revealed and emits HOLE_CARD_REVEALED."""
        if not self.hole_card_revealed and len(self.dealer_hand) >= 2:
            self.hole_card_revealed = True
            hole = self.dealer_hand[1]
            if self._engine_round_active and self.card_counter is not None:
                self.card_counter.observe_card(hole)
            self.event_bus.emit(GameEventType.HOLE_CARD_REVEALED, {"card": hole})
            return hole
        return None

    def all_seats_busted(self) -> bool:
        """Returns True if every active hand across all active seats has busted or surrendered."""
        active_seats = [s for s in self.seats if s.is_active and s.hands]
        if not active_seats:
            return True
        for s in active_seats:
            for h in s.hands:
                if not (h.is_bust or h.is_surrendered):
                    return False
        return True

    def advance_turn(self) -> Tuple[Optional[int], Optional[int]]:
        """
        Advances through split hands for the active seat; once all sub-hands stand, bust,
        or surrender, advances to the next active seat in clockwise order (1 -> 2 -> 3).
        Transitions to Dealer Turn when all active seats finish.
        """
        if self.active_seat_index is None:
            return None, None
        seat = self.get_seat(self.active_seat_index)
        if not seat:
            return None, None
        if self.active_hand_index < len(seat.hands) - 1:
            self.active_hand_index += 1
            return self.active_seat_index, self.active_hand_index

        # Current seat finished; find next active seat clockwise (1 -> 2 -> 3)
        remaining_seats = [
            s for s in self.seats
            if s.seat_index > self.active_seat_index and s.is_active and s.hands
        ]
        if remaining_seats:
            self.active_seat_index = remaining_seats[0].seat_index
            self.active_hand_index = 0
            return self.active_seat_index, self.active_hand_index

        # All active seats finished player actions
        if self.all_seats_busted():
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.DEALER_TURN)
        return None, None

    def _advance_turn_after_hand_done(self) -> None:
        self.advance_turn()

    def hit(
        self,
        hand_index_or_seat: Optional[int] = None,
        seat_index: Optional[int] = None,
        hand_index: Optional[int] = None,
    ) -> Card:
        """Deals one card to the specified (or active) seat and hand."""
        if seat_index is not None:
            s_idx = seat_index
            h_idx = hand_index if hand_index is not None else self.active_hand_index
        elif hand_index_or_seat is not None:
            if hand_index_or_seat in (1, 2, 3) and hand_index_or_seat == self.active_seat_index:
                s_idx = hand_index_or_seat
                h_idx = self.active_hand_index
            elif hand_index_or_seat in (1, 2, 3) and len(self.get_seat(self.active_seat_index).hands) == 1:
                s_idx = hand_index_or_seat
                h_idx = 0
            else:
                s_idx = self.active_seat_index
                h_idx = hand_index_or_seat
        else:
            s_idx = self.active_seat_index
            h_idx = self.active_hand_index

        seat = self.get_seat(s_idx)
        hand = seat.hands[h_idx]
        self._record_engine_action(seat, s_idx, h_idx, hand, "HIT")
        card = self._draw("player")
        hand.add_card(card)
        self.event_bus.emit(
            GameEventType.CARD_DEALT,
            {"card": card, "seat_index": s_idx, "hand_index": h_idx, "is_dealer": False},
        )
        if hand.is_bust:
            self.event_bus.emit(
                GameEventType.PLAYER_BUSTED,
                {"seat_index": s_idx, "hand_index": h_idx, "score": hand.score},
            )
            self.advance_turn()
        elif hand.score >= BLACKJACK_TARGET:
            self.advance_turn()
        return card

    def stand(
        self,
        hand_index_or_seat: Optional[int] = None,
        seat_index: Optional[int] = None,
        hand_index: Optional[int] = None,
    ) -> None:
        """Stands on the specified (or active) seat/hand and advances turn."""
        if seat_index is not None:
            s_idx = seat_index
            h_idx = hand_index if hand_index is not None else self.active_hand_index
        elif hand_index_or_seat is not None:
            if hand_index_or_seat in (1, 2, 3) and hand_index_or_seat == self.active_seat_index:
                s_idx = hand_index_or_seat
                h_idx = self.active_hand_index
            elif hand_index_or_seat in (1, 2, 3) and len(self.get_seat(self.active_seat_index).hands) == 1:
                s_idx = hand_index_or_seat
                h_idx = 0
            else:
                s_idx = self.active_seat_index
                h_idx = hand_index_or_seat
        else:
            s_idx = self.active_seat_index
            h_idx = self.active_hand_index

        seat = self.get_seat(s_idx)
        hand = seat.hands[h_idx]
        self._record_engine_action(seat, s_idx, h_idx, hand, "STAND")
        hand.is_stood = True
        self.advance_turn()

    def double_down(
        self,
        hand_index_or_seat: Optional[int] = None,
        seat_index: Optional[int] = None,
        hand_index: Optional[int] = None,
    ) -> Card:
        """Doubles the hand wager, draws 1 card, and stands."""
        if seat_index is not None:
            s_idx = seat_index
            h_idx = hand_index if hand_index is not None else self.active_hand_index
        elif hand_index_or_seat is not None and hand_index_or_seat in (1, 2, 3) and len(self.get_seat(self.active_seat_index).hands) == 1:
            s_idx = hand_index_or_seat
            h_idx = 0
        else:
            s_idx = self.active_seat_index
            h_idx = hand_index_or_seat if hand_index_or_seat is not None else self.active_hand_index

        seat = self.get_seat(s_idx)
        hand = seat.hands[h_idx]
        is_split_h = len(seat.hands) > 1 or hand.is_split
        if not can_double_down_hand(hand, self.house_rules, self.bankroll, is_split_hand=is_split_h):
            raise ValueError("Hand is not eligible for double down under current HouseRules")
        self._record_engine_action(seat, s_idx, h_idx, hand, "DOUBLE")
        self.bankroll -= hand.bet
        hand.bet *= 2
        hand.is_doubled = True
        card = self._draw("player")
        hand.add_card(card)
        hand.is_stood = True
        self.event_bus.emit(
            GameEventType.CARD_DEALT,
            {"card": card, "seat_index": s_idx, "hand_index": h_idx, "is_dealer": False},
        )
        if hand.is_bust:
            self.event_bus.emit(
                GameEventType.PLAYER_BUSTED,
                {"seat_index": s_idx, "hand_index": h_idx, "score": hand.score},
            )
        self.advance_turn()
        return card

    def split(
        self,
        hand_index_or_seat: Optional[int] = None,
        seat_index: Optional[int] = None,
        hand_index: int = 0,
    ) -> Tuple[Hand, Hand]:
        """Splits a matching 2-card hand into two independent hands."""
        if seat_index is not None:
            s_idx = seat_index
            h_idx = hand_index
        elif hand_index_or_seat in (1, 2, 3) and len(self.get_seat(self.active_seat_index).hands) == 1:
            s_idx = hand_index_or_seat
            h_idx = 0
        else:
            s_idx = self.active_seat_index
            h_idx = hand_index_or_seat if hand_index_or_seat is not None else 0

        seat = self.get_seat(s_idx)
        hand = seat.hands[h_idx]
        if not hand.can_split or self.bankroll < hand.bet:
            raise ValueError("Hand is not eligible to split")
        self._record_engine_action(seat, s_idx, h_idx, hand, "SPLIT")
        self.bankroll -= hand.bet
        c1, c2 = hand[0], hand[1]
        h1 = Hand([c1, self._draw("player")], bet=hand.bet, is_split=True)
        h2 = Hand([c2, self._draw("player")], bet=hand.bet, is_split=True)
        seat.hands = [h1, h2]
        self.active_hand_index = 0
        self.event_bus.emit(GameEventType.HAND_SPLIT, {"seat_index": s_idx, "hands": 2})
        return h1, h2

    def surrender(
        self,
        hand_index_or_seat: Optional[int] = None,
        seat_index: Optional[int] = None,
        hand_index: Optional[int] = None,
    ) -> None:
        """Surrenders the active hand, recovering half the bet and advancing clockwise."""
        if seat_index is not None:
            s_idx = seat_index
            h_idx = hand_index if hand_index is not None else 0
        elif hand_index_or_seat in (1, 2, 3):
            s_idx = hand_index_or_seat
            h_idx = 0
        else:
            s_idx = self.active_seat_index
            h_idx = hand_index_or_seat if hand_index_or_seat is not None else self.active_hand_index

        seat = self.get_seat(s_idx)
        hand = seat.hands[h_idx]
        is_split_h = len(seat.hands) > 1 or hand.is_split
        if not can_surrender_hand(hand, self.house_rules, is_split_hand=is_split_h):
            raise ValueError("Late Surrender is not allowed for this hand under current HouseRules")
        self._record_engine_action(seat, s_idx, h_idx, hand, "SURRENDER")
        hand.is_surrendered = True
        hand.is_stood = True
        refund = hand.bet // 2
        self.bankroll += refund
        hand.is_settled = True

        active_seats = [s for s in self.seats if s.is_active and s.hands and not (s.hands[0].is_surrendered or s.hands[0].is_bust)]
        if self.all_seats_busted() or len(active_seats) == 0:
            self.reveal_hole_card()
            self.fsm.transition_to(RoundPhase.RESOLUTION)
        else:
            self.advance_turn()

    def dealer_step(self) -> Optional[Card]:
        """Draws one dealer card if dealer must hit under S17/H17 rules; returns None when standing."""
        self.reveal_hole_card()
        if self.all_seats_busted():
            return None
        if dealer_should_hit(self.dealer_hand, hits_soft_17=self.house_rules.dealer_hits_soft_17):
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
        if not self.all_seats_busted() and self.phase == RoundPhase.DEALER_TURN:
            while dealer_should_hit(self.dealer_hand, hits_soft_17=self.house_rules.dealer_hits_soft_17):
                self.dealer_step()
            if self.phase != RoundPhase.RESOLUTION:
                self.fsm.transition_to(RoundPhase.RESOLUTION)
        elif self.all_seats_busted():
            self.reveal_hole_card()
            if self.phase != RoundPhase.RESOLUTION:
                self.fsm.transition_to(RoundPhase.RESOLUTION)

        results: List[RoundResult] = []

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
        settled_telemetry: list[dict[str, Any]] = []

        active_seats = [s for s in self.seats if s.is_active and s.hands]
        if not active_seats and len(self.seats) >= 2 and self.seats[1].hands:
            active_seats = [self.seats[1]]

        for seat in active_seats:
            is_split_round = len(seat.hands) > 1
            for idx, hand in enumerate(seat.hands):
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
                payout = calculate_payout(
                    outcome,
                    hand.bet,
                    blackjack_payout=self.house_rules.blackjack_payout,
                )
                profit = payout - hand.bet
                hand.outcome = outcome
                hand.net_payout = payout
                if chips_mode and not hand.is_settled:
                    self.bankroll += payout
                hand.is_settled = True
                res = RoundResult(
                    seat_index=seat.seat_index,
                    hand_index=idx,
                    outcome=outcome,
                    message=msg,
                    bet=hand.bet,
                    payout=payout,
                )
                results.append(res)
                outcomes.append(outcome)
                messages.append(msg)
                payouts.append(payout)
                profits.append(profit)
                settled_telemetry.append(
                    {
                        "seat_idx": seat.seat_index,
                        "hand_idx": idx,
                        "wager": hand.bet,
                        "cards": list(hand.cards),
                        "outcome": outcome,
                        "net_profit": profit if chips_mode else 0,
                    }
                )
                self.event_bus.emit(
                    GameEventType.HAND_RESOLVED,
                    {
                        "seat_index": seat.seat_index,
                        "hand_index": idx,
                        "outcome": outcome,
                        "payout": payout,
                    },
                )
            seat.is_resolved = True

        total_profit = sum(profits)
        net_round = total_profit + ins_profit

        if self._engine_round_active and self.tripometer is not None:
            actual_net = (self.bankroll - self._round_start_bankroll) if chips_mode else 0
            self.tripometer.finalize_round(
                settled_hands=settled_telemetry,
                dealer_cards=list(self.dealer_hand.cards),
                net_round_profit=actual_net,
            )
        self._engine_round_active = False

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
