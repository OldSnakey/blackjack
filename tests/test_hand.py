"""
Modular Unit Test Suite for Hand Domain Model (`rules.py`).

Tests Hand encapsulation, properties, sequence protocol backward compatibility,
and card operations completely in isolation from Tkinter or GUI widgets.
"""

from __future__ import annotations

import unittest
from rules import Card, Hand


class TestHandDomainModel(unittest.TestCase):
    """Verifies Hand domain methods and sequence protocol compatibility."""

    def test_empty_hand_initialization(self):
        hand = Hand()
        self.assertEqual(len(hand), 0)
        self.assertEqual(hand.bet, 0)
        self.assertEqual(hand.score, 0)
        self.assertFalse(hand.is_soft)
        self.assertFalse(hand.is_blackjack)
        self.assertFalse(hand.is_bust)
        self.assertFalse(hand.can_split)
        self.assertFalse(hand.can_double)
        self.assertFalse(hand.is_doubled)
        self.assertFalse(hand.is_surrendered)
        self.assertFalse(hand.is_stood)
        self.assertFalse(hand.is_settled)
        self.assertIsNone(hand.outcome)

    def test_sequence_protocol_compatibility(self):
        c1 = Card(10, None, "king", "spade")
        c2 = Card(1, None, "ace", "heart")
        hand = Hand([c1, c2], bet=50)

        # len()
        self.assertEqual(len(hand), 2)
        # indexing
        self.assertEqual(hand[0], c1)
        self.assertEqual(hand[1], c2)
        # 2-tuple unpacking via card
        val, img = hand[0]
        self.assertEqual(val, 10)
        # list() iteration
        self.assertEqual(list(hand), [c1, c2])
        # append and pop
        c3 = Card(5, None, "5", "club")
        hand.append(c3)
        self.assertEqual(len(hand), 3)
        self.assertEqual(hand[-1], c3)
        popped = hand.pop()
        self.assertEqual(popped, c3)
        self.assertEqual(len(hand), 2)

    def test_dynamic_hand_properties(self):
        # Blackjack: Ace + 10-value
        bj_hand = Hand([Card(1, None, "ace", "spade"), Card(10, None, "queen", "diamond")], bet=100)
        self.assertEqual(bj_hand.score, 21)
        self.assertTrue(bj_hand.is_blackjack)
        self.assertTrue(bj_hand.is_soft)
        self.assertFalse(bj_hand.is_bust)

        # Splittable pair
        pair = Hand([Card(8, None, "8", "heart"), Card(8, None, "8", "spade")], bet=25)
        self.assertTrue(pair.can_split)
        self.assertTrue(pair.can_double)

        # Non-splittable different ranks
        mixed = Hand([Card(8, None, "8", "heart"), Card(9, None, "9", "spade")], bet=25)
        self.assertFalse(mixed.can_split)
        self.assertTrue(mixed.can_double)

    def test_bust_and_auto_stand_behavior(self):
        hand = Hand([Card(10, None, "10", "heart"), Card(6, None, "6", "diamond")], bet=20)
        self.assertEqual(hand.score, 16)
        self.assertFalse(hand.is_bust)
        self.assertFalse(hand.is_stood)

        # Add card causing bust
        hand.add_card(Card(10, None, "king", "club"))
        self.assertEqual(hand.score, 26)
        self.assertTrue(hand.is_bust)
        self.assertTrue(hand.is_stood)

    def test_flags_and_mutation(self):
        hand = Hand([Card(5, None, "5", "heart"), Card(6, None, "6", "club")], bet=30)
        self.assertFalse(hand.is_doubled)
        hand.is_doubled = True
        hand.bet *= 2
        self.assertEqual(hand.bet, 60)
        self.assertTrue(hand.is_doubled)
        # Double down cannot double again or split
        self.assertFalse(hand.can_double)
        self.assertFalse(hand.can_split)


if __name__ == "__main__":
    unittest.main()
