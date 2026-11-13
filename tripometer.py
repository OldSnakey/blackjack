"""
Persistent Strategy Tripometer & Per-Round Skill Grading Engine.

Zero GUI or Tkinter dependencies:
Buffers per-round Kelly bet sizing, Illustrious 18 index play opportunities,
and rule-aware Basic Strategy decisions in memory, committing running totals
and a bounded 50-hand JSON-safe audit log at round finalization.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

from card_counter import HiLoCardCounter
from rules import (
    HouseRules,
    effective_minimum_bet,
    get_basic_strategy_decision,
)

MAX_RECENT_HANDS: int = 50

_SUIT_SYMBOLS: dict[str, str] = {
    "spade": "♠",
    "spades": "♠",
    "heart": "♥",
    "hearts": "♥",
    "diamond": "♦",
    "diamonds": "♦",
    "club": "♣",
    "clubs": "♣",
}

_RANK_TOKENS: dict[str, str] = {
    "ace": "A",
    "king": "K",
    "queen": "Q",
    "jack": "J",
    "thirteen": "13",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_card_token(card: Any) -> str:
    """
    Converts a Card object, tuple, or primitive value into a compact JSON-safe string token
    (e.g., 'A♠', '10♥', '13♣'), stripping any Tkinter PhotoImage references.
    """
    if isinstance(card, str):
        return card
    if card is None:
        return "?"

    rank = getattr(card, "rank", "")
    suit = getattr(card, "suit", "")
    val = card[0] if isinstance(card, (tuple, list)) and len(card) > 0 else getattr(card, "value", card)

    if rank:
        r_clean = str(rank).strip().lower()
        r_tok = _RANK_TOKENS.get(r_clean, str(rank).strip().upper())
    else:
        try:
            ival = int(val)
            r_tok = "A" if ival == 1 else str(ival)
        except (TypeError, ValueError):
            r_tok = str(val)

    s_tok = _SUIT_SYMBOLS.get(str(suit).strip().lower(), "") if suit else ""
    return f"{r_tok}{s_tok}"


@dataclass(frozen=True)
class DecisionStepRecord:
    """JSON-safe audit record for a single player decision within a hand."""
    action_taken: str
    optimal_action: str
    is_bs_optimal: bool
    is_i18_spot: bool
    is_i18_optimal: bool
    live_tc: float
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_taken": self.action_taken,
            "optimal_action": self.optimal_action,
            "is_bs_optimal": self.is_bs_optimal,
            "is_i18_spot": self.is_i18_spot,
            "is_i18_optimal": self.is_i18_optimal,
            "live_tc": round(float(self.live_tc), 1),
            "explanation": self.explanation,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Optional[DecisionStepRecord]:
        if not isinstance(data, dict):
            return None
        try:
            return cls(
                action_taken=str(data.get("action_taken", "")),
                optimal_action=str(data.get("optimal_action", "")),
                is_bs_optimal=bool(data.get("is_bs_optimal", True)),
                is_i18_spot=bool(data.get("is_i18_spot", False)),
                is_i18_optimal=bool(data.get("is_i18_optimal", True)),
                live_tc=round(float(data.get("live_tc", 0.0)), 1),
                explanation=str(data.get("explanation", "")),
            )
        except (TypeError, ValueError):
            return None


@dataclass(frozen=True)
class HandHistoryRecord:
    """JSON-safe audit snapshot of a completed hand and its active HouseRules."""
    timestamp_iso: str
    seat_idx: int
    hand_idx: int
    rules_badge: str
    rules_dict: dict[str, Any]
    pre_deal_tc: float
    wager: int
    kelly_target_bet: int
    kelly_status: str  # "OPTIMAL" | "OVERBET" | "UNDERBET" | "N/A"
    player_cards: tuple[str, ...]
    dealer_cards: tuple[str, ...]
    outcome: str
    net_profit: int
    decisions: tuple[DecisionStepRecord, ...] = ()
    ungraded_reason: Optional[str] = None

    @property
    def has_mistake(self) -> bool:
        if self.ungraded_reason is not None:
            return False
        if self.kelly_status in ("OVERBET", "UNDERBET"):
            return True
        for step in self.decisions:
            if not step.is_bs_optimal:
                return True
            if step.is_i18_spot and not step.is_i18_optimal:
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_iso": self.timestamp_iso,
            "seat_idx": int(self.seat_idx),
            "hand_idx": int(self.hand_idx),
            "rules_badge": self.rules_badge,
            "rules_dict": dict(self.rules_dict),
            "pre_deal_tc": round(float(self.pre_deal_tc), 1),
            "wager": int(self.wager),
            "kelly_target_bet": int(self.kelly_target_bet),
            "kelly_status": self.kelly_status,
            "player_cards": list(self.player_cards),
            "dealer_cards": list(self.dealer_cards),
            "outcome": self.outcome,
            "net_profit": int(self.net_profit),
            "decisions": [d.to_dict() for d in self.decisions],
            "ungraded_reason": self.ungraded_reason,
        }

    @classmethod
    def from_dict(cls, data: Any) -> Optional[HandHistoryRecord]:
        if not isinstance(data, dict):
            return None
        try:
            raw_rules = data.get("rules_dict")
            sanitized_rules = HouseRules.from_dict(raw_rules if isinstance(raw_rules, dict) else None)
            raw_decisions = data.get("decisions", [])
            parsed_decisions: list[DecisionStepRecord] = []
            if isinstance(raw_decisions, list):
                for item in raw_decisions[:20]:
                    rec = DecisionStepRecord.from_dict(item)
                    if rec is not None:
                        parsed_decisions.append(rec)

            raw_status = str(data.get("kelly_status", "N/A"))
            if raw_status not in ("OPTIMAL", "OVERBET", "UNDERBET", "N/A"):
                raw_status = "N/A"

            raw_p_cards = data.get("player_cards", [])
            raw_d_cards = data.get("dealer_cards", [])
            p_cards = tuple(str(c) for c in raw_p_cards[:12]) if isinstance(raw_p_cards, list) else ()
            d_cards = tuple(str(c) for c in raw_d_cards[:12]) if isinstance(raw_d_cards, list) else ()

            raw_reason = data.get("ungraded_reason")
            ungraded = str(raw_reason) if raw_reason is not None else None

            return cls(
                timestamp_iso=str(data.get("timestamp_iso", "")),
                seat_idx=int(data.get("seat_idx", 0)),
                hand_idx=int(data.get("hand_idx", 0)),
                rules_badge=str(data.get("rules_badge") or sanitized_rules.short_badge()),
                rules_dict=sanitized_rules.to_dict(),
                pre_deal_tc=round(float(data.get("pre_deal_tc", 0.0)), 1),
                wager=max(0, int(data.get("wager", 0))),
                kelly_target_bet=max(0, int(data.get("kelly_target_bet", 0))),
                kelly_status=raw_status,
                player_cards=p_cards,
                dealer_cards=d_cards,
                outcome=str(data.get("outcome", "UNKNOWN")),
                net_profit=int(data.get("net_profit", 0)),
                decisions=tuple(parsed_decisions),
                ungraded_reason=ungraded,
            )
        except (TypeError, ValueError):
            return None


def _clamp_counter_pair(raw_opt: Any, raw_tot: Any) -> tuple[int, int]:
    try:
        tot = max(0, int(raw_tot))
    except (TypeError, ValueError):
        tot = 0
    try:
        opt = max(0, min(tot, int(raw_opt)))
    except (TypeError, ValueError):
        opt = 0
    return opt, tot


def _safe_nonneg_int(raw: Any) -> int:
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return 0


def _safe_signed_int(raw: Any) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


@dataclass
class TripometerData:
    """Persistent cumulative skill telemetry and 50-hand ring buffer."""
    bs_optimal_decisions: int = 0
    bs_total_decisions: int = 0
    i18_optimal_decisions: int = 0
    i18_opportunities: int = 0
    kelly_optimal_rounds: int = 0
    kelly_total_rounds: int = 0
    hands_recorded: int = 0
    rounds_recorded: int = 0
    trip_net_profit: int = 0
    started_at_iso: str = field(default_factory=_now_iso)
    recent_hands: deque[HandHistoryRecord] = field(
        default_factory=lambda: deque(maxlen=MAX_RECENT_HANDS)
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bs_optimal_decisions": int(self.bs_optimal_decisions),
            "bs_total_decisions": int(self.bs_total_decisions),
            "i18_optimal_decisions": int(self.i18_optimal_decisions),
            "i18_opportunities": int(self.i18_opportunities),
            "kelly_optimal_rounds": int(self.kelly_optimal_rounds),
            "kelly_total_rounds": int(self.kelly_total_rounds),
            "hands_recorded": int(self.hands_recorded),
            "rounds_recorded": int(self.rounds_recorded),
            "trip_net_profit": int(self.trip_net_profit),
            "started_at_iso": self.started_at_iso,
            "recent_hands": [h.to_dict() for h in list(self.recent_hands)[:MAX_RECENT_HANDS]],
        }

    @classmethod
    def from_dict(cls, data: Any) -> TripometerData:
        if not isinstance(data, dict):
            return cls()
        bs_opt, bs_tot = _clamp_counter_pair(
            data.get("bs_optimal_decisions", 0),
            data.get("bs_total_decisions", 0),
        )
        i18_opt, i18_tot = _clamp_counter_pair(
            data.get("i18_optimal_decisions", 0),
            data.get("i18_opportunities", 0),
        )
        kelly_opt, kelly_tot = _clamp_counter_pair(
            data.get("kelly_optimal_rounds", 0),
            data.get("kelly_total_rounds", 0),
        )
        hands_rec = _safe_nonneg_int(data.get("hands_recorded", 0))
        rounds_rec = _safe_nonneg_int(data.get("rounds_recorded", 0))
        net_pl = _safe_signed_int(data.get("trip_net_profit", 0))
        started = str(data.get("started_at_iso") or _now_iso())

        ring: deque[HandHistoryRecord] = deque(maxlen=MAX_RECENT_HANDS)
        raw_hands = data.get("recent_hands", [])
        if isinstance(raw_hands, list):
            for entry in raw_hands[:MAX_RECENT_HANDS]:
                parsed = HandHistoryRecord.from_dict(entry)
                if parsed is not None:
                    ring.append(parsed)

        return cls(
            bs_optimal_decisions=bs_opt,
            bs_total_decisions=bs_tot,
            i18_optimal_decisions=i18_opt,
            i18_opportunities=i18_tot,
            kelly_optimal_rounds=kelly_opt,
            kelly_total_rounds=kelly_tot,
            hands_recorded=hands_rec,
            rounds_recorded=rounds_rec,
            trip_net_profit=net_pl,
            started_at_iso=started,
            recent_hands=ring,
        )


class TripometerTracker:
    """
    Stateful per-round telemetry buffer and skill evaluator shared across
    headless BlackjackEngine runs and BlackjackApp GUI sessions.
    """

    def __init__(
        self,
        data: Optional[TripometerData] = None,
        save_manager: Optional[Any] = None,
    ):
        self.data: TripometerData = data if data is not None else TripometerData()
        self.save_manager: Optional[Any] = save_manager
        self._counter = HiLoCardCounter()
        self._round_buffer: Optional[dict[str, Any]] = None

    @property
    def has_active_round(self) -> bool:
        return self._round_buffer is not None

    def begin_round(
        self,
        rules: HouseRules,
        pre_deal_tc: float,
        seat_bets: dict[int, int],
        round_bankroll: int,
        chips_mode: bool = True,
        ungraded_reason: Optional[str] = None,
    ) -> None:
        """Snapshots active HouseRules and stages Kelly bet-sizing evaluation in memory."""
        norm_rules = rules.normalized()
        tc_val = round(float(pre_deal_tc), 1)
        clean_bets = {int(s): max(0, int(b)) for s, b in seat_bets.items()}
        wagered_seats = {s: b for s, b in clean_bets.items() if b > 0}
        active_seats = max(1, len(wagered_seats))

        target_bet, target_tier, _ = self._counter.get_kelly_bet_target(
            norm_rules, tc_val, round_bankroll, active_seats=active_seats
        )

        kelly_status_by_seat: dict[int, str] = {}
        kelly_tot = 0
        kelly_opt = 0

        if not chips_mode or not wagered_seats:
            for s in clean_bets:
                kelly_status_by_seat[s] = "N/A"
        else:
            eff_min = effective_minimum_bet(norm_rules, round_bankroll)
            if target_tier == 0:
                low_ok = eff_min
                high_ok = eff_min
            else:
                b_low = self._counter.get_kelly_tier_bet(
                    norm_rules, max(0, target_tier - 1), round_bankroll, active_seats=active_seats
                )
                b_high = self._counter.get_kelly_tier_bet(
                    norm_rules, min(4, target_tier + 1), round_bankroll, active_seats=active_seats
                )
                low_ok = min(b_low, b_high)
                high_ok = max(b_low, b_high)

            all_compliant = True
            for s, bet in wagered_seats.items():
                if low_ok <= bet <= high_ok:
                    kelly_status_by_seat[s] = "OPTIMAL"
                elif bet < low_ok:
                    kelly_status_by_seat[s] = "UNDERBET"
                    all_compliant = False
                else:
                    kelly_status_by_seat[s] = "OVERBET"
                    all_compliant = False

            kelly_tot = 1
            kelly_opt = 1 if all_compliant else 0

        self._round_buffer = {
            "timestamp_iso": _now_iso(),
            "rules": norm_rules,
            "pre_deal_tc": tc_val,
            "kelly_target_bet": target_bet,
            "kelly_status_by_seat": kelly_status_by_seat,
            "chips_mode": bool(chips_mode),
            "ungraded_reason": ungraded_reason,
            "bs_opt": 0,
            "bs_tot": 0,
            "i18_opt": 0,
            "i18_opp": 0,
            "kelly_opt": kelly_opt,
            "kelly_tot": kelly_tot,
            "decisions_by_hand": {},
        }

    def record_insurance_decision(
        self,
        seat_idx: int,
        took_insurance: bool,
        live_tc: float,
        can_afford: bool,
    ) -> None:
        """
        Grades an affordable Insurance opportunity against the Illustrious 18 +3.0 index.
        Never touches Basic Strategy denominators; routine declines below +3.0 are skipped.
        """
        if self._round_buffer is None or not can_afford:
            return

        tc_val = round(float(live_tc), 1)
        is_plus_three = tc_val >= 3.0
        if not is_plus_three and not took_insurance:
            return

        action_str = "INSURANCE" if took_insurance else "DECLINE"
        optimal_str = "INSURANCE" if is_plus_three else "DECLINE"
        is_opt = (took_insurance == is_plus_three)

        self._round_buffer["i18_opp"] += 1
        if is_opt:
            self._round_buffer["i18_opt"] += 1

        explanation = (
            f"I18 (Insurance): Take Insurance at TC >= +3.0 (live TC {tc_val:+.1f})"
            if is_plus_three
            else f"I18 (Insurance): Decline Insurance below TC +3.0 (live TC {tc_val:+.1f})"
        )
        step = DecisionStepRecord(
            action_taken=action_str,
            optimal_action=optimal_str,
            is_bs_optimal=True,
            is_i18_spot=True,
            is_i18_optimal=is_opt,
            live_tc=tc_val,
            explanation=explanation,
        )
        key = (int(seat_idx), 0)
        self._round_buffer["decisions_by_hand"].setdefault(key, []).append(step)

    def record_decision(
        self,
        seat_idx: int,
        hand_idx: int,
        cards: Sequence[Any],
        dealer_upcard: Any,
        action: str,
        live_tc: float,
        can_split: bool,
        can_double: bool,
        can_surrender: bool,
        is_split_hand: bool = False,
        auto: bool = False,
    ) -> None:
        """
        Evaluates a voluntary player action against rule-aware Basic Strategy and Illustrious 18.
        Executing an active I18 deviation satisfies both I18 and Basic Strategy grades.
        """
        if auto or self._round_buffer is None:
            return

        act = action.strip().upper()
        if act == "DOUBLE_DOWN":
            act = "DOUBLE"

        rules_snap: HouseRules = self._round_buffer["rules"]
        card_list = list(cards)
        bs = get_basic_strategy_decision(
            card_list,
            dealer_upcard,
            can_double=can_double,
            can_split=can_split,
            can_surrender=can_surrender,
            rules=rules_snap,
            is_split_hand=is_split_hand,
        )
        if bs is None:
            return

        tc_val = round(float(live_tc), 1)
        dev = self._counter.evaluate_hand_deviation(
            card_list,
            dealer_upcard,
            true_count=tc_val,
            can_double=can_double,
            can_split=can_split,
            is_insurance_phase=False,
            can_surrender=can_surrender,
            is_split_hand=is_split_hand,
            rules=rules_snap,
        )

        is_i18_spot = dev is not None
        is_i18_optimal = bool(dev is not None and act == dev.recommended_action)
        is_bs_optimal = bool(
            act == bs.action
            or (dev is not None and dev.is_deviation_active and act == dev.recommended_action)
        )
        optimal_action = (
            dev.recommended_action
            if (dev is not None and dev.is_deviation_active)
            else bs.action
        )

        if dev is not None and dev.is_deviation_active:
            explanation = (
                f"I18 ({dev.label}): {dev.recommended_action} at TC {tc_val:+.1f} "
                f"({dev.condition_str}; BS: {bs.action})"
            )
        elif dev is not None:
            explanation = (
                f"{bs.reason} — {dev.recommended_action} below {dev.condition_str} "
                f"(TC {tc_val:+.1f})"
            )
        else:
            explanation = f"Basic Strategy: {bs.label} ({bs.reason})"

        self._round_buffer["bs_tot"] += 1
        if is_bs_optimal:
            self._round_buffer["bs_opt"] += 1
        if is_i18_spot:
            self._round_buffer["i18_opp"] += 1
            if is_i18_optimal:
                self._round_buffer["i18_opt"] += 1

        step = DecisionStepRecord(
            action_taken=act,
            optimal_action=optimal_action,
            is_bs_optimal=is_bs_optimal,
            is_i18_spot=is_i18_spot,
            is_i18_optimal=is_i18_optimal,
            live_tc=tc_val,
            explanation=explanation,
        )
        key = (int(seat_idx), int(hand_idx))
        self._round_buffer["decisions_by_hand"].setdefault(key, []).append(step)

    def mark_supernatural(self, reason: str = "haunted") -> None:
        """Marks the in-flight round as ungraded (e.g., Card 13, Haunted Relic, or HELL_TABLE)."""
        if self._round_buffer is not None:
            self._round_buffer["ungraded_reason"] = reason

    def abort_round(self) -> None:
        """Discards any uncommitted in-flight round buffer cleanly."""
        self._round_buffer = None

    def finalize_round(
        self,
        settled_hands: Sequence[dict[str, Any]],
        dealer_cards: Sequence[Any],
        net_round_profit: int,
        ungraded_reason: Optional[str] = None,
    ) -> None:
        """
        Commits buffered skill counters and net P&L (iff ungraded_reason is None),
        appends HandHistoryRecord entries to recent_hands, and persists via SaveManager.
        """
        if self._round_buffer is None:
            return

        buf = self._round_buffer
        self._round_buffer = None

        effective_reason: Optional[str] = ungraded_reason or buf.get("ungraded_reason")
        rules_snap: HouseRules = buf["rules"]
        rules_badge = rules_snap.short_badge()
        rules_dict = rules_snap.to_dict()
        d_tokens = tuple(format_card_token(c) for c in dealer_cards)
        kelly_map: dict[int, str] = buf["kelly_status_by_seat"]
        decisions_map: dict[tuple[int, int], list[DecisionStepRecord]] = buf["decisions_by_hand"]

        new_records: list[HandHistoryRecord] = []
        for entry in settled_hands:
            s_idx = int(entry.get("seat_idx", 0))
            h_idx = int(entry.get("hand_idx", 0))
            p_tokens = tuple(format_card_token(c) for c in entry.get("cards", ()))
            if effective_reason is None and any(tok.startswith("13") for tok in (*p_tokens, *d_tokens)):
                effective_reason = "haunted"

            k_status = kelly_map.get(
                s_idx,
                "N/A" if not buf["chips_mode"] else "OPTIMAL",
            )
            steps = tuple(decisions_map.get((s_idx, h_idx), ()))
            new_records.append(
                HandHistoryRecord(
                    timestamp_iso=buf["timestamp_iso"],
                    seat_idx=s_idx,
                    hand_idx=h_idx,
                    rules_badge=rules_badge,
                    rules_dict=rules_dict,
                    pre_deal_tc=buf["pre_deal_tc"],
                    wager=max(0, int(entry.get("wager", 0))),
                    kelly_target_bet=int(buf["kelly_target_bet"]),
                    kelly_status=k_status,
                    player_cards=p_tokens,
                    dealer_cards=d_tokens,
                    outcome=str(entry.get("outcome", "UNKNOWN")),
                    net_profit=int(entry.get("net_profit", 0)),
                    decisions=steps,
                    ungraded_reason=effective_reason,
                )
            )

        if effective_reason is not None:
            new_records = [
                HandHistoryRecord(
                    timestamp_iso=r.timestamp_iso,
                    seat_idx=r.seat_idx,
                    hand_idx=r.hand_idx,
                    rules_badge=r.rules_badge,
                    rules_dict=r.rules_dict,
                    pre_deal_tc=r.pre_deal_tc,
                    wager=r.wager,
                    kelly_target_bet=r.kelly_target_bet,
                    kelly_status=r.kelly_status,
                    player_cards=r.player_cards,
                    dealer_cards=r.dealer_cards,
                    outcome=r.outcome,
                    net_profit=r.net_profit,
                    decisions=r.decisions,
                    ungraded_reason=effective_reason,
                )
                for r in new_records
            ]

        for rec in reversed(new_records):
            self.data.recent_hands.appendleft(rec)

        if effective_reason is None:
            self.data.bs_optimal_decisions += int(buf["bs_opt"])
            self.data.bs_total_decisions += int(buf["bs_tot"])
            self.data.i18_optimal_decisions += int(buf["i18_opt"])
            self.data.i18_opportunities += int(buf["i18_opp"])
            self.data.kelly_optimal_rounds += int(buf["kelly_opt"])
            self.data.kelly_total_rounds += int(buf["kelly_tot"])
            self.data.rounds_recorded += 1
            self.data.hands_recorded += len(new_records)
            self.data.trip_net_profit += int(net_round_profit)

        if self.save_manager is not None:
            self.save_manager.save_tripometer_data(self.data)

    def reset(self) -> None:
        """Resets Tripometer counters and hand log to a fresh slate."""
        self._round_buffer = None
        if self.save_manager is not None:
            self.data = self.save_manager.reset_tripometer()
        else:
            self.data = TripometerData()

    def get_summary(self) -> dict[str, Any]:
        """Returns formatted accuracy grades, denominators, and top-bar badge text."""
        d = self.data
        bs_pct = (
            round(100.0 * d.bs_optimal_decisions / d.bs_total_decisions, 1)
            if d.bs_total_decisions > 0
            else None
        )
        i18_pct = (
            round(100.0 * d.i18_optimal_decisions / d.i18_opportunities, 1)
            if d.i18_opportunities > 0
            else None
        )
        kelly_pct = (
            round(100.0 * d.kelly_optimal_rounds / d.kelly_total_rounds, 1)
            if d.kelly_total_rounds > 0
            else None
        )

        bs_disp = (
            f"{bs_pct:.1f}% ({d.bs_optimal_decisions}/{d.bs_total_decisions})"
            if bs_pct is not None
            else "N/A (0 spots)"
        )
        i18_disp = (
            f"{i18_pct:.1f}% ({d.i18_optimal_decisions}/{d.i18_opportunities})"
            if i18_pct is not None
            else "N/A (0 spots)"
        )
        kelly_disp = (
            f"{kelly_pct:.1f}% ({d.kelly_optimal_rounds}/{d.kelly_total_rounds})"
            if kelly_pct is not None
            else "N/A (0 spots)"
        )
        top_bar_text = f"📊 {int(round(bs_pct))}%" if bs_pct is not None else "📊 Trip"

        return {
            "bs_pct": bs_pct,
            "bs_optimal": d.bs_optimal_decisions,
            "bs_total": d.bs_total_decisions,
            "i18_pct": i18_pct,
            "i18_optimal": d.i18_optimal_decisions,
            "i18_opportunities": d.i18_opportunities,
            "kelly_pct": kelly_pct,
            "kelly_optimal": d.kelly_optimal_rounds,
            "kelly_total": d.kelly_total_rounds,
            "bs_display": bs_disp,
            "i18_display": i18_disp,
            "kelly_display": kelly_disp,
            "top_bar_text": top_bar_text,
            "hands_recorded": d.hands_recorded,
            "rounds_recorded": d.rounds_recorded,
            "trip_net_profit": d.trip_net_profit,
            "started_at_iso": d.started_at_iso,
        }
