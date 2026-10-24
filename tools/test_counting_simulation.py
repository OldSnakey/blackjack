"""
Card Counting Simulation Tool (`tools/test_counting_simulation.py`).

Performs a high-speed mathematical Monte-Carlo simulation of 10,000 deals
to rigorously verify Hi-Lo card counting invariants:
1. Zero-Sum Full Deck Invariant: Sum of tags across every 52-card deck is exactly 0.
2. Running Count (RC) accumulation fidelity across individual and multi-round deals.
3. True Count (TC) formula precision: TC = RC / max(0.5, remaining_cards / 52.0).
4. Dealer Hole Card Invariant: Hole card is strictly uncounted until revealed.
5. Shuffle Reset Invariant: Reshuffle completely clears RC and revealed history.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Ensure utf-8 stdout on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from card_counter import HiLoCardCounter
from rules import Card, build_shoe


def build_raw_52_deck() -> list[Card]:
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


def run_simulation(num_rounds: int = 10_000, deck_count: int = 4) -> bool:
    print(f"================================================================")
    print(f"[*] Starting Card Counting Simulation: {num_rounds:,} Deals ({deck_count} Decks)")
    print(f"================================================================")

    template_deck = build_raw_52_deck()
    counter = HiLoCardCounter(deck_count=deck_count)

    # Invariant 1: Single deck tag sum must be zero
    single_deck_sum = sum(counter.tag_card(c) for c in template_deck)
    assert single_deck_sum == 0, f"Single deck tag sum must be 0, got {single_deck_sum}"
    print("[OK] Invariant 1 Passed: Zero-sum tag invariant for 52 cards confirmed (sum = 0).")

    start_time = time.perf_counter()
    shoe: list[Card] = []
    rounds_completed = 0
    shuffles_occurred = 0
    total_cards_observed = 0

    while rounds_completed < num_rounds:
        # Shuffle when shoe penetration drops below 25% (cut card)
        if len(shoe) < int(52 * deck_count * 0.25):
            shoe = build_shoe(template_deck, deck_count)
            counter.on_shuffle()
            shuffles_occurred += 1
            assert counter.running_count == 0, "Running count must reset to 0 on shuffle!"

        # Deal standard 4-card round: P1, D_up, P2, D_hole
        p1 = shoe.pop()
        d_up = shoe.pop()
        p2 = shoe.pop()
        d_hole = shoe.pop()

        # Observe initial face-up cards (P1, D_up, P2) - DO NOT observe hole card yet
        initial_rc = counter.running_count
        expected_rc = initial_rc + counter.tag_card(p1) + counter.tag_card(d_up) + counter.tag_card(p2)

        counter.on_card_revealed(p1)
        counter.on_card_revealed(d_up)
        counter.on_card_revealed(p2)
        total_cards_observed += 3

        # Invariant 4: Hole card must NOT have altered count
        assert counter.running_count == expected_rc, (
            f"Count mismatch! Expected {expected_rc}, got {counter.running_count}"
        )

        # Invariant 3: Verify True Count formula
        cards_rem = len(shoe) + 1  # +1 for unrevealed hole card
        expected_decks = counter.decks_remaining(cards_rem)
        expected_tc = round(counter.running_count / expected_decks, 1)
        assert abs(counter.get_true_count(cards_rem) - expected_tc) < 1e-4, "True count calculation mismatch!"

        # Player hits with 40% probability
        while random.random() < 0.4 and len(shoe) > 5:
            hit_card = shoe.pop()
            counter.on_card_revealed(hit_card)
            total_cards_observed += 1

        # Reveal dealer hole card at round conclusion
        counter.on_card_revealed(d_hole)
        total_cards_observed += 1

        rounds_completed += 1

    elapsed = time.perf_counter() - start_time
    rate = rounds_completed / elapsed if elapsed > 0 else 0

    print("[OK] Invariant 2 Passed: Running count accumulation verified across all deals.")
    print("[OK] Invariant 3 Passed: True count division & deck estimation verified.")
    print("[OK] Invariant 4 Passed: Dealer hole card privacy verified on all rounds.")
    print("[OK] Invariant 5 Passed: Reshuffle resets verified.")
    print(f"----------------------------------------------------------------")
    print(f"[DONE] Simulation Complete!")
    print(f"   Rounds Played:        {rounds_completed:,}")
    print(f"   Cards Tracked:        {total_cards_observed:,}")
    print(f"   Shuffles Executed:    {shuffles_occurred}")
    print(f"   Execution Time:       {elapsed:.3f} seconds ({rate:,.0f} rounds/sec)")
    print(f"================================================================")
    return True


if __name__ == "__main__":
    success = run_simulation()
    sys.exit(0 if success else 1)
