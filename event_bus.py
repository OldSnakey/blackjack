"""
Lightweight In-Memory Pub/Sub Event Hub (`EventHub`) for Blackjack.

Decouples core game domain transitions (`BlackjackEngine` / `GameStateMachine`) from
presentation, audio, card counting, and persistence observers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class GameEventType(Enum):
    """Typed game events emitted across the round lifecycle."""
    BET_STAGED = "bet_staged"
    BET_COMMITTED = "bet_committed"
    CARD_DEALT = "card_dealt"
    HOLE_CARD_REVEALED = "hole_card_revealed"
    HAND_SPLIT = "hand_split"
    PLAYER_BUSTED = "player_busted"
    DEALER_BUSTED = "dealer_busted"
    ROUND_RESOLVED = "round_resolved"
    CANDLE_SNUFFED = "candle_snuffed"
    PHASE_CHANGED = "phase_changed"


@dataclass(frozen=True)
class GameEvent:
    """Immutable event envelope dispatched to registered listeners."""
    event_type: GameEventType
    payload: Dict[str, Any] = field(default_factory=dict)


ListenerCallback = Callable[[GameEvent], None]


class EventHub:
    """Synchronous, zero-dependency in-memory event bus."""

    def __init__(self):
        self._subscribers: Dict[GameEventType, List[ListenerCallback]] = {}

    def subscribe(self, event_type: GameEventType, callback: ListenerCallback) -> None:
        """Registers a callback for a specific GameEventType."""
        listeners = self._subscribers.setdefault(event_type, [])
        if callback not in listeners:
            listeners.append(callback)

    def unsubscribe(self, event_type: GameEventType, callback: ListenerCallback) -> None:
        """Removes a previously registered callback."""
        listeners = self._subscribers.get(event_type)
        if listeners and callback in listeners:
            listeners.remove(callback)

    def emit(self, event_type: GameEventType, payload: Optional[Dict[str, Any]] = None) -> GameEvent:
        """Constructs and synchronously dispatches a GameEvent to all subscribers."""
        event = GameEvent(event_type=event_type, payload=dict(payload or {}))
        for callback in list(self._subscribers.get(event_type, [])):
            callback(event)
        return event

    def clear(self) -> None:
        """Removes all registered event subscribers."""
        self._subscribers.clear()
