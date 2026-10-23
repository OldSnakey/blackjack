"""
Unit test suite for the in-memory `EventHub` pub-sub architecture (`event_bus.py`).
"""

from __future__ import annotations

import unittest
from event_bus import EventHub, GameEvent, GameEventType


class TestEventBus(unittest.TestCase):
    """Verifies EventHub subscription, emission, unsubscription, and payload integrity."""

    def test_subscribe_emit_and_unsubscribe(self):
        bus = EventHub()
        received: list[GameEvent] = []

        def on_card(event: GameEvent):
            received.append(event)

        bus.subscribe(GameEventType.CARD_DEALT, on_card)
        bus.emit(GameEventType.CARD_DEALT, {"target": "player", "rank": "ace"})

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0].event_type, GameEventType.CARD_DEALT)
        self.assertEqual(received[0].payload["rank"], "ace")

        # Unsubscribe prevents further delivery
        bus.unsubscribe(GameEventType.CARD_DEALT, on_card)
        bus.emit(GameEventType.CARD_DEALT, {"target": "dealer", "rank": "10"})
        self.assertEqual(len(received), 1)

    def test_multiple_subscribers_and_clear(self):
        bus = EventHub()
        calls_a = []
        calls_b = []

        bus.subscribe(GameEventType.ROUND_RESOLVED, lambda e: calls_a.append(e.payload))
        bus.subscribe(GameEventType.ROUND_RESOLVED, lambda e: calls_b.append(e.payload))

        bus.emit(GameEventType.ROUND_RESOLVED, {"outcome": "NATURAL_BLACKJACK", "payout": 250})
        self.assertEqual(len(calls_a), 1)
        self.assertEqual(len(calls_b), 1)

        bus.clear()
        bus.emit(GameEventType.ROUND_RESOLVED, {"outcome": "PUSH", "payout": 100})
        self.assertEqual(len(calls_a), 1)
        self.assertEqual(len(calls_b), 1)


if __name__ == "__main__":
    unittest.main()
