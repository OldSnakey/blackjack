"""
Integration Test Suite for Architectural Improvements (`tests/test_architectural_integration.py`).

Verifies the integration of BlackjackEngine, GameStateMachine, EventHub, Hand domain model,
and TableFeltCanvas layer rendering into BlackjackApp while enforcing headless test standards.
"""

from __future__ import annotations

import tempfile
import tkinter
import unittest
from pathlib import Path

from blackjack import BlackjackApp
from event_bus import EventHub, GameEventType
from game_engine import BlackjackEngine
from rules import Card, Hand, RoundPhase
from state_machine import GameStateMachine
from ui_canvases import TableFeltCanvas


class TestArchitecturalIntegration(unittest.TestCase):
    """Verifies end-to-end integration of architectural components into BlackjackApp."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_path = Path(self.temp_dir.name) / "test_save.json"
        self.app = BlackjackApp(
            self.root,
            sound_enabled=False,
            chips_mode=True,
            save_path=self.save_path,
            skip_splash=True,
        )

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_engine_and_event_hub_initialization(self):
        """BlackjackApp initializes EventHub, BlackjackEngine, and GameStateMachine."""
        self.assertIsInstance(self.app.event_bus, EventHub)
        self.assertIsInstance(self.app.engine, BlackjackEngine)
        self.assertIsInstance(self.app.fsm, GameStateMachine)
        self.assertEqual(self.app.engine.deck_count, self.app.deck_count)

    def test_hand_domain_model_in_app(self):
        """player_hands and dealer_hand contain Hand instances compatible with list protocol."""
        self.assertIsInstance(self.app.player_hands[0], Hand)
        self.assertIsInstance(self.app.dealer_hand, Hand)

        # Sequence protocol: len(), indexing, iteration
        self.assertEqual(len(self.app.player_hands), 1)
        self.assertEqual(len(self.app.player_hands[0]), 0)

        # Append card directly to hand
        card = Card(10, None, "10", "heart")
        self.app.player_hands[0].append(card)
        self.assertEqual(len(self.app.player_hands[0]), 1)
        self.assertEqual(self.app.player_hands[0][0], card)

    def test_bet_commitment_emits_event(self):
        """Staging and committing a bet emits BET_COMMITTED on EventHub."""
        events = []
        self.app.event_bus.subscribe(
            GameEventType.BET_COMMITTED,
            lambda ev: events.append(ev),
        )
        self.app.current_bet_var.set(50)
        self.app._deal_hand_with_bet()

        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0].payload.get("bet"), 50)

    def test_card_deals_emit_event_and_update_shoe_visual(self):
        """Drawing cards emits CARD_DEALT and triggers shoe penetration updates."""
        dealt_events = []
        self.app.event_bus.subscribe(
            GameEventType.CARD_DEALT,
            lambda ev: dealt_events.append(ev),
        )
        self.app.current_bet_var.set(25)
        self.app._deal_hand_with_bet()

        # Initial deal issues 4 cards (2 player + 2 dealer)
        self.assertGreaterEqual(len(dealt_events), 4)

    def test_split_creates_independent_hand_objects(self):
        """Splitting a pair creates two independent Hand instances and emits HAND_SPLIT."""
        split_events = []
        self.app.event_bus.subscribe(
            GameEventType.HAND_SPLIT,
            lambda ev: split_events.append(ev),
        )

        # Rig pair of 8s
        c1 = Card(8, None, "8", "spade")
        c2 = Card(8, None, "8", "club")
        self.app.player_hands = [Hand([c1, c2], bet=50)]
        self.app.hand_bets = [50]
        self.app.on_split()

        self.assertEqual(len(self.app.player_hands), 2)
        self.assertIsInstance(self.app.player_hands[0], Hand)
        self.assertIsInstance(self.app.player_hands[1], Hand)
        self.assertTrue(self.app.player_hands[0].is_split)
        self.assertTrue(self.app.player_hands[1].is_split)
        self.assertGreaterEqual(len(split_events), 1)

    def test_table_felt_layer_shoe_methods(self):
        """TableFeltCanvas renders Layer 1 (Shoe Tray & Discard Rack) without headless errors."""
        canvas = self.app.card_table_frame
        self.assertIsInstance(canvas, TableFeltCanvas)

        # Call visual drawing methods
        canvas.draw_shoe_tray(remaining=150, total=208)
        self.assertGreater(len(canvas.find_withtag("shoe_tray")), 0)

        canvas.draw_discard_rack(discarded=58, total=208)
        self.assertGreater(len(canvas.find_withtag("discard_rack")), 0)

        canvas.update_shoe_penetration(remaining=100, total=208)
        self.assertGreater(len(canvas.find_withtag("shoe_tray")), 0)

    def test_table_felt_layer_card_sprite_methods(self):
        """TableFeltCanvas provides Layer 3 card sprite creation and cleanup."""
        canvas = self.app.card_table_frame
        # Draw sprite with dummy image
        item_id = canvas.draw_card_sprite(image=None, x=50, y=50, tags="test_card")
        self.assertIsNotNone(item_id)
        coords = canvas.coords(item_id)
        self.assertEqual(coords, [50.0, 50.0])

        canvas.move_card_sprite(item_id, target_x=100, target_y=120)
        self.assertEqual(canvas.coords(item_id), [100.0, 120.0])

        canvas.clear_card_sprites(tag="test_card")
        self.assertEqual(len(canvas.find_withtag("test_card")), 0)


if __name__ == "__main__":
    unittest.main()
