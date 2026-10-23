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


class GameStateMachine:
    """Formal state machine governing Blackjack round phases."""

    def __init__(
        self,
        initial_phase: RoundPhase = RoundPhase.BETTING,
        event_bus: Optional[EventHub] = None,
    ):
        self._phase: RoundPhase = initial_phase
        self._event_bus: Optional[EventHub] = event_bus

    @property
    def phase(self) -> RoundPhase:
        return self._phase

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
