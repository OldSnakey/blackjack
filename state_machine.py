"""
Formal Finite State Machine (`GameStateMachine`) for Blackjack Round Lifecycle.

Enforces valid round phase transitions (`RoundPhase`), guards against re-entrancy,
emits `PHASE_CHANGED` events on an optional `EventHub`, and exposes backward-compatible
boolean property aliases (`is_betting_phase`, `is_insurance_phase`, `is_dealing`, `is_round_over`).
"""

from __future__ import annotations

from typing import Dict, Optional, Set
from event_bus import EventHub, GameEventType
from rules import RoundPhase


class InvalidStateTransitionError(ValueError):
    """Raised when attempting an illegal transition between RoundPhases."""


VALID_TRANSITIONS: Dict[RoundPhase, Set[RoundPhase]] = {
    RoundPhase.BETTING: {
        RoundPhase.BETTING,
        RoundPhase.INITIAL_DEAL,
        RoundPhase.PLAYER_TURN,
        RoundPhase.TRANSITION_CUTSCENE,
    },
    RoundPhase.INITIAL_DEAL: {
        RoundPhase.INSURANCE,
        RoundPhase.PLAYER_TURN,
        RoundPhase.RESOLUTION,
        RoundPhase.ROUND_OVER,
    },
    RoundPhase.INSURANCE: {
        RoundPhase.PLAYER_TURN,
        RoundPhase.RESOLUTION,
        RoundPhase.ROUND_OVER,
    },
    RoundPhase.PLAYER_TURN: {
        RoundPhase.PLAYER_TURN,
        RoundPhase.DEALER_TURN,
        RoundPhase.RESOLUTION,
        RoundPhase.ROUND_OVER,
    },
    RoundPhase.DEALER_TURN: {
        RoundPhase.DEALER_TURN,
        RoundPhase.RESOLUTION,
        RoundPhase.ROUND_OVER,
    },
    RoundPhase.RESOLUTION: {
        RoundPhase.ROUND_OVER,
        RoundPhase.BETTING,
        RoundPhase.TRANSITION_CUTSCENE,
    },
    RoundPhase.ROUND_OVER: {
        RoundPhase.BETTING,
        RoundPhase.INITIAL_DEAL,
        RoundPhase.PLAYER_TURN,
        RoundPhase.TRANSITION_CUTSCENE,
    },
    RoundPhase.TRANSITION_CUTSCENE: {
        RoundPhase.BETTING,
        RoundPhase.INITIAL_DEAL,
        RoundPhase.PLAYER_TURN,
        RoundPhase.ROUND_OVER,
    },
}

ACTION_ALLOWED_PHASES: Dict[str, Set[RoundPhase]] = {
    "stage_bet": {RoundPhase.BETTING},
    "deal": {RoundPhase.BETTING},
    "take_insurance": {RoundPhase.INSURANCE},
    "decline_insurance": {RoundPhase.INSURANCE},
    "hit": {RoundPhase.PLAYER_TURN},
    "stand": {RoundPhase.PLAYER_TURN},
    "double": {RoundPhase.PLAYER_TURN},
    "split": {RoundPhase.PLAYER_TURN},
    "surrender": {RoundPhase.PLAYER_TURN},
    "dealer_step": {RoundPhase.DEALER_TURN},
    "resolve": {
        RoundPhase.INITIAL_DEAL,
        RoundPhase.INSURANCE,
        RoundPhase.PLAYER_TURN,
        RoundPhase.DEALER_TURN,
        RoundPhase.RESOLUTION,
    },
    "new_game": set(RoundPhase),
}


class GameStateMachine:
    """Formal state machine governing Blackjack round phases."""

    def __init__(
        self,
        initial_phase: RoundPhase = RoundPhase.BETTING,
        event_bus: Optional[EventHub] = None,
    ):
        self._phase: RoundPhase = initial_phase
        self._event_bus: Optional[EventHub] = event_bus
        self._in_flight: bool = False

    @property
    def phase(self) -> RoundPhase:
        return self._phase

    @property
    def current_phase(self) -> RoundPhase:
        return self._phase

    @property
    def in_flight(self) -> bool:
        return self._in_flight

    @in_flight.setter
    def in_flight(self, value: bool) -> None:
        self._in_flight = bool(value)

    def can_trigger(self, action: str) -> bool:
        """Returns True if action is legally allowed in current phase and not locked in-flight."""
        if action == "new_game":
            return True
        if self._in_flight:
            return False
        allowed = ACTION_ALLOWED_PHASES.get(action)
        if allowed is None:
            return False
        return self._phase in allowed

    def trigger(self, action: str, target_phase: Optional[RoundPhase] = None) -> bool:
        """
        Validates action against current phase and in_flight lock.
        If valid and target_phase is provided, transitions to target_phase.
        Returns True if successful, False if blocked.
        """
        if not self.can_trigger(action):
            return False
        if action == "new_game":
            self._in_flight = False
        if target_phase is not None:
            self.transition_to(target_phase, force=True)
        return True

    def expected_action_button_states(
        self,
        can_double: bool = False,
        can_split: bool = False,
        can_surrender: bool = False,
    ) -> Dict[str, str]:
        """Computes authoritative button states ('normal' vs 'disabled') strictly from current phase & in_flight."""
        is_player_turn = (self._phase == RoundPhase.PLAYER_TURN) and not self._in_flight
        is_round_over = (self._phase in (RoundPhase.ROUND_OVER, RoundPhase.RESOLUTION)) and not self._in_flight
        return {
            "hit": "normal" if is_player_turn else "disabled",
            "stand": "normal" if is_player_turn else "disabled",
            "double": "normal" if (is_player_turn and can_double) else "disabled",
            "split": "normal" if (is_player_turn and can_split) else "disabled",
            "surrender": "normal" if (is_player_turn and can_surrender) else "disabled",
            "new_game": "normal" if is_round_over else "disabled",
        }

    def can_transition(self, target_phase: RoundPhase) -> bool:
        """Returns True if transitioning from current phase to `target_phase` is permitted."""
        allowed = VALID_TRANSITIONS.get(self._phase, set())
        return target_phase in allowed

    def transition_to(self, target_phase: RoundPhase, force: bool = False) -> RoundPhase:
        """
        Transitions to `target_phase`. Raises `InvalidStateTransitionError` if illegal
        unless `force=True`.
        """
        if not force and not self.can_transition(target_phase):
            raise InvalidStateTransitionError(
                f"Illegal state transition from {self._phase.value} to {target_phase.value}"
            )
        prev = self._phase
        self._phase = target_phase
        if self._event_bus is not None and prev != target_phase:
            self._event_bus.emit(
                GameEventType.PHASE_CHANGED,
                {"from_phase": prev.value, "to_phase": target_phase.value},
            )
        return self._phase

    # --- Backward-compatible boolean property aliases ---
    @property
    def is_betting_phase(self) -> bool:
        return self._phase == RoundPhase.BETTING

    @property
    def is_insurance_phase(self) -> bool:
        return self._phase == RoundPhase.INSURANCE

    @property
    def is_dealing(self) -> bool:
        return self._phase == RoundPhase.INITIAL_DEAL

    @property
    def is_round_over(self) -> bool:
        return self._phase in (RoundPhase.RESOLUTION, RoundPhase.ROUND_OVER)
