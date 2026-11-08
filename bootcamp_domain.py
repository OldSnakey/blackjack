"""
Pure Domain Model for the MIT Hi-Lo Card Counting Bootcamp (`bootcamp_domain.py`).

Provides:
- Immutable DTOs (`BootcampLectureSlide`, `BootcampNodeSpec`, `BootcampPrompt`).
- 14-Node Curriculum DAG specification, 5-tier grading rubric (`S`/`A`/`B`/`C`/`F`),
  21 Show & Tell lecture slides, and deterministic drill generators (`BootcampCurriculumDAG`).
- Live session state and latency tracker (`BootcampDrillSession`).

Maintains zero Tkinter or PIL dependencies for fast, deterministic unit testing.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from save_manager import GRADE_RANK_ORDER


BOOTCAMP_GRADE_CHIP_STYLES: Dict[str, Dict[str, Any]] = {
    "S": {"denom": 1000, "bg": "#e5e4e2", "rim": "#9e9e9e", "stripe": "#ffd700", "fg": "#1a1a1a"},
    "A": {"denom": 100, "bg": "#262626", "rim": "#111111", "stripe": "#ffd700", "fg": "#ffd700"},
    "B": {"denom": 25, "bg": "#1e824c", "rim": "#11512f", "stripe": "#ffffff", "fg": "#ffffff"},
    "C": {"denom": 5, "bg": "#c0392b", "rim": "#782017", "stripe": "#ffffff", "fg": "#ffffff"},
    "F": {"denom": 1, "bg": "#33393d", "rim": "#1c2023", "stripe": "#7f8c8d", "fg": "#cfd8dc"},
}

# Canonical fixed hotkey answer ranges per Challenge stage (and paired Lecture practice check).
# Guarantees consistent muscle memory across every prompt within a stage and ensures the correct
# answer is always within the stage's valid hotkey range.
STAGE_FIXED_CHOICES: Dict[str, Tuple[str, ...]] = {
    "C1": ("+1 (Low)", "0 (Neutral)", "-1 (High)"),
    "C2A": ("-2", "-1", "0", "+1", "+2"),
    "C2B": ("-2", "-1", "0", "+1", "+2"),
    "C3A": ("-2", "-1", "0", "+1", "+2"),
    "C3B": ("-2", "-1", "0", "+1", "+2"),
    "C4": ("-1.0", "+1.0", "+2.0", "+3.0", "+4.0"),
    "C5": ("1 Unit ($25)", "2 Units ($50)", "4 Units ($100)", "8 Units ($200)", "12 Units ($300)"),
}


@dataclass(frozen=True)
class BootcampLectureSlide:
    """Represents a single interactive Show & Tell slide inside a Lecture node."""
    title: str
    dealer_line: str
    caption: str
    cards: Tuple[Tuple[str, str, str], ...]  # (rank, suit, badge_text)
    formula_banner: str = ""
    practice_question: str = ""
    practice_choices: Tuple[str, ...] = ()
    practice_correct: str = ""
    practice_explanation: str = ""
    card_groups: Tuple[Tuple[str, Tuple[int, ...]], ...] = ()  # ((group_label, (card_idx, ...)), ...)


@dataclass(frozen=True)
class BootcampNodeSpec:
    """Metadata and layout coordinates for one of the 14 DAG nodes (7 Lectures + 7 Challenges)."""
    node_id: str           # e.g. "L1", "C1", "L2A", "C2A", ...
    node_type: str         # "lecture" | "challenge"
    tier: int              # 1..5
    fork: str              # "main" | "A" | "B"
    title: str
    subtitle: str
    paired_id: str         # L1 <-> C1, L2A <-> C2A, etc.
    par_ms: float = 2500.0
    total_prompts: int = 15
    col_idx: int = 0       # 0..4 column index on DAG map
    row_slot: str = "center"  # "center_top", "center_bottom", "fork_a_top", "fork_a_bottom", "fork_b_top", "fork_b_bottom"


@dataclass(frozen=True)
class BootcampPrompt:
    """Single interactive drill question in a Challenge stage (`C1`–`C5`)."""
    prompt_index: int
    stage_id: str
    headline: str
    subheadline: str
    cards: Tuple[Tuple[str, str], ...]  # (rank, suit)
    choices: Tuple[str, ...]
    correct_answer: str
    explanation: str
    dealer_callout: str = ""
    running_count_before: int = 0
    decks_remaining: float = 6.0


class BootcampCurriculumDAG:
    """
    Pure domain specification of the 14-node MIT Hi-Lo Counting Bootcamp DAG,
    grading rubric, Show & Tell lecture slides, and deterministic drill generators.
    """

    STAGE_PAR_MS: Dict[str, float] = {
        "C1": 2000.0,
        "C2A": 3500.0,
        "C2B": 2200.0,
        "C3A": 3000.0,
        "C3B": 4500.0,
        "C4": 4500.0,
        "C5": 5000.0,
    }

    STAGE_PROMPT_COUNTS: Dict[str, int] = {
        "C1": 20,
        "C2A": 12,
        "C2B": 15,
        "C3A": 10,
        "C3B": 10,
        "C4": 12,
        "C5": 10,
    }

    def __init__(self) -> None:
        self._nodes: List[BootcampNodeSpec] = [
            # Tier 1: Foundation
            BootcampNodeSpec(
                node_id="L1", node_type="lecture", tier=1, fork="main",
                title="L1: Hi-Lo Buckets", subtitle="Low +1 | Neutral 0 | High -1",
                paired_id="C1", par_ms=0.0, total_prompts=0, col_idx=0, row_slot="center_top",
            ),
            BootcampNodeSpec(
                node_id="C1", node_type="challenge", tier=1, fork="main",
                title="C1: Tag Reflex", subtitle="20 Rapid Single-Card Tags",
                paired_id="L1", par_ms=2000.0, total_prompts=20, col_idx=0, row_slot="center_bottom",
            ),
            # Tier 2: Fork A (Visual Cancellation) & Fork B (Speed Stream)
            BootcampNodeSpec(
                node_id="L2A", node_type="lecture", tier=2, fork="A",
                title="L2A: Pair Cancels", subtitle="(+1) + (-1) = 0 Shortcut",
                paired_id="C2A", par_ms=0.0, total_prompts=0, col_idx=1, row_slot="fork_a_top",
            ),
            BootcampNodeSpec(
                node_id="C2A", node_type="challenge", tier=2, fork="A",
                title="C2A: Pair Cancel", subtitle="12 Two-Card Net Drills",
                paired_id="L2A", par_ms=3500.0, total_prompts=12, col_idx=1, row_slot="fork_a_bottom",
            ),
            BootcampNodeSpec(
                node_id="L2B", node_type="lecture", tier=2, fork="B",
                title="L2B: RC Cadence", subtitle="Running Count Cadence",
                paired_id="C2B", par_ms=0.0, total_prompts=0, col_idx=1, row_slot="fork_b_top",
            ),
            BootcampNodeSpec(
                node_id="C2B", node_type="challenge", tier=2, fork="B",
                title="C2B: Stream Sprint", subtitle="15-Card Stream RC Check",
                paired_id="L2B", par_ms=2200.0, total_prompts=15, col_idx=1, row_slot="fork_b_bottom",
            ),
            # Tier 3: Fork A (3-Seat Table Sweep) & Fork B (Dealer Turn & Hole Flip)
            BootcampNodeSpec(
                node_id="L3A", node_type="lecture", tier=3, fork="A",
                title="L3A: 3-Seat Sweep", subtitle="Cross-Seat Cancellation",
                paired_id="C3A", par_ms=0.0, total_prompts=0, col_idx=2, row_slot="fork_a_top",
            ),
            BootcampNodeSpec(
                node_id="C3A", node_type="challenge", tier=3, fork="A",
                title="C3A: Table Sweep", subtitle="10 Full-Table Net Deltas",
                paired_id="L3A", par_ms=3000.0, total_prompts=10, col_idx=2, row_slot="fork_a_bottom",
            ),
            BootcampNodeSpec(
                node_id="L3B", node_type="lecture", tier=3, fork="B",
                title="L3B: Hole Card Flip", subtitle="When Hidden Cards Count",
                paired_id="C3B", par_ms=0.0, total_prompts=0, col_idx=2, row_slot="fork_b_top",
            ),
            BootcampNodeSpec(
                node_id="C3B", node_type="challenge", tier=3, fork="B",
                title="C3B: Dealer Runout", subtitle="10 Hole-Flip + Hit Sequences",
                paired_id="L3B", par_ms=4500.0, total_prompts=10, col_idx=2, row_slot="fork_b_bottom",
            ),
            # Tier 4: Convergence (True Count & Shoe Depth)
            BootcampNodeSpec(
                node_id="L4", node_type="lecture", tier=4, fork="main",
                title="L4: True Count", subtitle="RC / Decks Remaining",
                paired_id="C4", par_ms=0.0, total_prompts=0, col_idx=3, row_slot="center_top",
            ),
            BootcampNodeSpec(
                node_id="C4", node_type="challenge", tier=4, fork="main",
                title="C4: TC Calibration", subtitle="12 Shoe-Depth TC Drills",
                paired_id="L4", par_ms=4500.0, total_prompts=12, col_idx=3, row_slot="center_bottom",
            ),
            # Tier 5: Graduation (MIT 1-to-12 Bet Spread)
            BootcampNodeSpec(
                node_id="L5", node_type="lecture", tier=5, fork="main",
                title="L5: MIT Bet Spread", subtitle="1-to-12 Ramp & Deviations",
                paired_id="C5", par_ms=0.0, total_prompts=0, col_idx=4, row_slot="center_top",
            ),
            BootcampNodeSpec(
                node_id="C5", node_type="challenge", tier=5, fork="main",
                title="C5: Final Exam", subtitle="10 Pit Boss Final Trials",
                paired_id="L5", par_ms=5000.0, total_prompts=10, col_idx=4, row_slot="center_bottom",
            ),
        ]
        self._node_map: Dict[str, BootcampNodeSpec] = {n.node_id: n for n in self._nodes}
        self._lectures: Dict[str, List[BootcampLectureSlide]] = self._build_lectures()

    def get_all_nodes(self) -> List[BootcampNodeSpec]:
        return list(self._nodes)

    def get_node(self, node_id: str) -> BootcampNodeSpec:
        return self._node_map[node_id]

    def get_lecture_slides(self, lecture_id: str) -> List[BootcampLectureSlide]:
        return list(self._lectures.get(lecture_id, []))

    @staticmethod
    def compute_stage_grade(accuracy_pct: float, avg_response_ms: float, par_ms: float) -> str:
        """
        Standardized 5-Tier Grading Rubric:
        - S (Pit Boss / MIT Pro): 100.0% accuracy AND avg_response_ms <= par_ms
        - A (Card Shark): >= 90.0% accuracy (or 100% slower than par_ms)
        - B (Advantage Player - PASS): >= 80.0% accuracy
        - C (Probation - FAIL): 65.0% - 79.9% accuracy
        - F (Busted Out - FAIL): < 65.0% accuracy
        """
        if accuracy_pct >= 100.0 and avg_response_ms <= par_ms:
            return "S"
        if accuracy_pct >= 90.0:
            return "A"
        if accuracy_pct >= 80.0:
            return "B"
        if accuracy_pct >= 65.0:
            return "C"
        return "F"

    @staticmethod
    def compute_stage_score(accuracy_pct: float, avg_response_ms: float, par_ms: float) -> int:
        """
        Computes stage high-score points:
        stage_score = int(round(accuracy_pct * 100)) + (max(0, int((par_ms - avg_response_ms) // 10)) if accuracy_pct >= 80.0 else 0)
        """
        base = int(round(accuracy_pct * 100))
        speed_bonus = max(0, int((par_ms - avg_response_ms) // 10)) if accuracy_pct >= 80.0 else 0
        return base + speed_bonus

    def _build_lectures(self) -> Dict[str, List[BootcampLectureSlide]]:
        return {
            "L1": [
                BootcampLectureSlide(
                    title="L1 (1/3) — Why High Cards Favor the Player",
                    dealer_line="Welcome to MIT Hi-Lo 101! Tens and Aces pay 3:2 on Blackjack and force the dealer to bust more often.",
                    caption="When low cards (2–6) leave the shoe, the remaining deck gets richer in 10s and Aces (+1 to Player Edge).",
                    cards=(("2", "spades", "+1"), ("5", "hearts", "+1"), ("6", "clubs", "+1")),
                    formula_banner="LOW CARDS (2, 3, 4, 5, 6) = +1   [Good when dealt out!]",
                ),
                BootcampLectureSlide(
                    title="L1 (2/3) — Neutral & High Card Buckets",
                    dealer_line="7, 8, and 9 are neutral — ignore them completely! 10, J, Q, K, and Ace are High Cards (-1).",
                    caption="Every 10-value card or Ace dealt onto the felt removes a weapon from the shoe (-1).",
                    cards=(("8", "diamonds", "0"), ("king", "spades", "-1"), ("ace", "hearts", "-1")),
                    formula_banner="NEUTRAL (7, 8, 9) = 0   |   HIGH (10, J, Q, K, A) = -1",
                ),
                BootcampLectureSlide(
                    title="L1 (3/3) — Interactive Practice Check",
                    dealer_line="Quick check before Challenge C1: What is the Hi-Lo tag of a Queen of Spades?",
                    caption="Remember: all face cards (J, Q, K), 10s, and Aces belong to the High (-1) bucket.",
                    cards=(("queen", "spades", "?"),),
                    formula_banner="Tag this card using [1] +1, [2] 0, or [3] -1:",
                    practice_question="What is the Hi-Lo tag for the Queen of Spades?",
                    practice_choices=STAGE_FIXED_CHOICES["C1"],
                    practice_correct="-1 (High)",
                    practice_explanation="Correct! Queen is a 10-value High card, so its Hi-Lo tag is -1.",
                ),
            ],
            "L2A": [
                BootcampLectureSlide(
                    title="L2A (1/3) — The MIT Pair Cancellation Trick",
                    dealer_line="Amateurs count every single card one by one. Pros pair a Low card (+1) with a High card (-1) and erase both!",
                    caption="Look at King (-1) + 5 (+1): they cancel to ZERO instantly. No mental addition required!",
                    cards=(("king", "hearts", "-1"), ("5", "clubs", "+1")),
                    formula_banner="CANCELLED PAIR: (-1) + (+1) = 0 NET CHANGE",
                    card_groups=(("PLAYER HAND (NET 0)", (0, 1)),),
                ),
                BootcampLectureSlide(
                    title="L2A (2/3) — Same-Sign Double Stacks",
                    dealer_line="When two cards belong to the same bucket, they double up to +2 or -2.",
                    caption="Two low cards [3, 6] stack to +2. Two high cards [10, Ace] stack to -2!",
                    cards=(("3", "spades", "+1"), ("6", "diamonds", "+1"), ("10", "clubs", "-1"), ("ace", "hearts", "-1")),
                    formula_banner="DOUBLE LOW: (+1) + (+1) = +2   |   DOUBLE HIGH: (-1) + (-1) = -2",
                    card_groups=(("DOUBLE LOW (+2)", (0, 1)), ("DOUBLE HIGH (-2)", (2, 3))),
                ),
                BootcampLectureSlide(
                    title="L2A (3/3) — Interactive Practice Check",
                    dealer_line="What is the combined net count of this two-card hand: Ace of Spades + 4 of Hearts?",
                    caption="Spot the High card (-1) and Low card (+1) pair!",
                    cards=(("ace", "spades", "-1"), ("4", "hearts", "+1")),
                    formula_banner="Compute net hand delta: Ace (-1) + 4 (+1)",
                    practice_question="Net Hi-Lo count for [Ace, 4]:",
                    practice_choices=STAGE_FIXED_CHOICES["C2A"],
                    practice_correct="0",
                    practice_explanation="Spot on! Ace (-1) and 4 (+1) cancel directly to 0.",
                    card_groups=(("PLAYER HAND [A, 4]", (0, 1)),),
                ),
            ],
            "L2B": [
                BootcampLectureSlide(
                    title="L2B (1/3) — Keeping a Silent Running Count Rhythm",
                    dealer_line="In Fork B, we train your internal metronome. Never say '+1, -1' in your head — only say the new Running Count!",
                    caption="If Running Count is +2 and a 4 (+1) lands, think 'Plus Three' — keep a single number in working memory.",
                    cards=(("4", "spades", "RC: +1"), ("5", "diamonds", "RC: +2"), ("2", "clubs", "RC: +3")),
                    formula_banner="CHANT ONLY THE TOTAL: +1 -> +2 -> +3",
                ),
                BootcampLectureSlide(
                    title="L2B (2/3) — Ignoring Neutral Noise in a Stream",
                    dealer_line="When 7s, 8s, or 9s appear mid-stream, hold your current Running Count steady without flinching.",
                    caption="Stream: 6 (+1) -> 8 (0) -> King (-1) -> 3 (+1) finishes at RC +1.",
                    cards=(("6", "hearts", "+1"), ("8", "spades", "0"), ("king", "clubs", "-1"), ("3", "diamonds", "+1")),
                    formula_banner="STREAM CHECK: (+1) + 0 + (-1) + (+1) = +1",
                ),
                BootcampLectureSlide(
                    title="L2B (3/3) — Interactive Practice Check",
                    dealer_line="Start at RC 0. Watch these 3 cards: [2, 10, 5]. What is the final Running Count?",
                    caption="2 (+1) and 10 (-1) cancel to 0, leaving the 5 (+1)!",
                    cards=(("2", "clubs", "+1"), ("10", "hearts", "-1"), ("5", "spades", "+1")),
                    formula_banner="Starting RC = 0  +  [2, 10, 5]",
                    practice_question="Final Running Count after [2, 10, 5]:",
                    practice_choices=STAGE_FIXED_CHOICES["C2B"],
                    practice_correct="+1",
                    practice_explanation="Exact! 2 (+1) + 10 (-1) + 5 (+1) = +1.",
                ),
            ],
            "L3A": [
                BootcampLectureSlide(
                    title="L3A (1/3) — Scanning a 3-Seat Table Right-to-Left",
                    dealer_line="Wait until every seat has two cards! Scanning across seats lets you cancel whole hands in one glance.",
                    caption="Seat 1 has [10, K] (-2) and Seat 2 has [3, 5] (+2). Those two seats completely cancel each other to 0!",
                    cards=(("10", "spades", "-1"), ("king", "hearts", "-1"), ("3", "clubs", "+1"), ("5", "diamonds", "+1")),
                    formula_banner="SEAT 1 (-2) + SEAT 2 (+2) = 0",
                    card_groups=(("SEAT 1 HAND (-2)", (0, 1)), ("SEAT 2 HAND (+2)", (2, 3))),
                ),
                BootcampLectureSlide(
                    title="L3A (2/3) — Including the Dealer's Upcard Last",
                    dealer_line="After sweeping the player seats, add the Dealer's face-up card. Ignore the face-down hole card until it flips!",
                    caption="Never guess the hole card. Only count visible faces on the green baize.",
                    cards=(("queen", "diamonds", "-1"), ("4", "spades", "+1"), ("6", "hearts", "+1")),
                    formula_banner="QUEEN (-1) + 4 (+1) = 0, PLUS DEALER 6 (+1) = +1",
                    card_groups=(("SEAT 1 HAND (0)", (0, 1)), ("DEALER UPCARD (+1)", (2,))),
                ),
                BootcampLectureSlide(
                    title="L3A (3/3) — Interactive Practice Check",
                    dealer_line="Sweep this mini table: Seat 1 [J, 6], Seat 2 [8, 9], Dealer Upcard [5]. What is the table delta?",
                    caption="J (-1) cancels 6 (+1); 8 and 9 are 0; Dealer 5 is +1!",
                    cards=(
                        ("jack", "clubs", "-1"),
                        ("6", "spades", "+1"),
                        ("8", "hearts", "0"),
                        ("9", "clubs", "0"),
                        ("5", "diamonds", "+1"),
                    ),
                    formula_banner="Cancel Seat 1 [J, 6] -> 0, skip Seat 2 [8, 9] -> 0, add Dealer [5] (+1)",
                    practice_question="Net Table Delta:",
                    practice_choices=STAGE_FIXED_CHOICES["C3A"],
                    practice_correct="+1",
                    practice_explanation="Bravo! [J, 6] cancels to 0, [8, 9] are neutral (0), leaving Dealer [5] = +1.",
                    card_groups=(
                        ("SEAT 1 HAND", (0, 1)),
                        ("SEAT 2 HAND", (2, 3)),
                        ("DEALER UPCARD", (4,)),
                    ),
                ),
            ],
            "L3B": [
                BootcampLectureSlide(
                    title="L3B (1/3) — The Dealer Hole Card Flip Rule",
                    dealer_line="In Blackjack, the dealer's hole card is dealt face-down. You count it the exact moment it flips face-up!",
                    caption="When the dealer turns over their hidden card and draws to 17, rapid-fire hits test your composure.",
                    cards=(("10", "clubs", "UP: -1"), ("4", "hearts", "HOLE: +1"), ("3", "spades", "HIT: +1")),
                    formula_banner="UPCARD (-1) + HOLE FLIP (+1) + HIT (+1) = +1",
                    card_groups=(("DEALER HAND RUNOUT", (0, 1, 2)),),
                ),
                BootcampLectureSlide(
                    title="L3B (2/3) — Tracking Multi-Card Dealer Runouts",
                    dealer_line="When a dealer pulls 3 or 4 small cards to make 21, the Running Count surges upward!",
                    caption="Example: Dealer has [5 up, 2 hole] and pulls [4, 3, 6] = five low cards in a row (+5 to RC)!",
                    cards=(
                        ("5", "spades", "+1"),
                        ("2", "hearts", "+1"),
                        ("4", "clubs", "+1"),
                        ("3", "spades", "+1"),
                        ("6", "diamonds", "+1"),
                    ),
                    formula_banner="DEALER LOW RUNOUT = MASSIVE +RC SURGE",
                    card_groups=(
                        ("DEALER [5 UP, 2 HOLE]", (0, 1)),
                        ("DEALER HITS [4, 3, 6]", (2, 3, 4)),
                    ),
                ),
                BootcampLectureSlide(
                    title="L3B (3/3) — Interactive Practice Check",
                    dealer_line="Prior RC is +2. Dealer flips a hidden King (-1) and hits a 6 (+1) to bust. What is the new RC?",
                    caption="The flipped King (-1) and hit 6 (+1) cancel each other out!",
                    cards=(("king", "spades", "FLIP: -1"), ("6", "clubs", "HIT: +1")),
                    formula_banner="Prior RC (+2) + King (-1) + 6 (+1)",
                    practice_question="Updated Running Count:",
                    practice_choices=STAGE_FIXED_CHOICES["C3B"],
                    practice_correct="+2",
                    practice_explanation="King (-1) and 6 (+1) cancel to 0, so Prior RC +2 stays +2!",
                    card_groups=(("DEALER FLIP + HIT", (0, 1)),),
                ),
            ],
            "L4": [
                BootcampLectureSlide(
                    title="L4 (1/3) — Why Running Count Alone Lies in a 6-Deck Shoe",
                    dealer_line="A Running Count of +6 in the first round means only +1 extra high card per deck. With 1 deck left, +6 is monster heat!",
                    caption="To measure true concentration of high cards, divide Running Count by Decks Remaining.",
                    cards=(("ace", "spades", "RC +6"), ("king", "hearts", "/ 3 Decks"), ("queen", "diamonds", "= TC +2.0")),
                    formula_banner="TRUE COUNT (TC) = RUNNING COUNT / DECKS REMAINING",
                ),
                BootcampLectureSlide(
                    title="L4 (2/3) — Estimating the Shoe & Discard Tray",
                    dealer_line="Watch the acrylic shoe on the top-right of the felt! 52 cards = 1 Deck. Divide RC by remaining decks.",
                    caption="Examples: RC +8 with 4.0 decks left = TC +2.0. RC -6 with 2.0 decks left = TC -3.0.",
                    cards=(("10", "clubs", "RC +8"), ("4", "diamonds", "4 Decks"), ("2", "spades", "TC +2.0")),
                    formula_banner="RC +8 / 4.0 Decks = +2.0   |   RC +6 / 1.5 Decks = +4.0",
                ),
                BootcampLectureSlide(
                    title="L4 (3/3) — Interactive Practice Check",
                    dealer_line="Your Running Count is +9 and 3.0 decks remain in the shoe. What is the True Count?",
                    caption="Divide +9 by 3.0 decks remaining:",
                    cards=(("ace", "hearts", "RC +9"), ("3", "clubs", "3.0 Decks")),
                    formula_banner="TC = +9 / 3.0",
                    practice_question="What is the True Count?",
                    practice_choices=STAGE_FIXED_CHOICES["C4"],
                    practice_correct="+3.0",
                    practice_explanation="Exact! +9 divided by 3.0 remaining decks equals True Count +3.0.",
                ),
            ],
            "L5": [
                BootcampLectureSlide(
                    title="L5 (1/3) — The Official MIT 1-to-12 Bet Spread",
                    dealer_line="Counting without raising your bet when the shoe is hot is like knowing the lottery numbers and not buying a ticket!",
                    caption="Each True Count above +1 adds ~0.5% player edge. Scale your wager with the True Count:",
                    cards=(("2", "clubs", "TC<=+1: 1u"), ("8", "diamonds", "TC+2: 2u"), ("king", "spades", "TC+3: 4u")),
                    formula_banner="TC <= +1: 1 Unit ($25)  |  TC +2: 2 Units ($50)  |  TC +3: 4 Units ($100)",
                ),
                BootcampLectureSlide(
                    title="L5 (2/3) — Maximum Attack at TC +4 and TC +5+",
                    dealer_line="When True Count hits +4, fire 8 Units ($200). At TC +5 or higher, unleash the 12-Unit ($300) MIT Max Bet!",
                    caption="Plus two golden Illustrious 18 rules: Take Insurance at TC >= +3.0, and Stand on 16 vs 10 at TC > 0!",
                    cards=(("ace", "spades", "TC+4: 8u"), ("ace", "hearts", "TC>=+5: 12u"), ("10", "diamonds", "INS >= +3")),
                    formula_banner="TC +4: 8 Units ($200)  |  TC >= +5: 12 Units ($300)  |  Insurance at TC >= +3",
                ),
                BootcampLectureSlide(
                    title="L5 (3/3) — Interactive Practice Check",
                    dealer_line="Final check before Graduation Exam C5: RC is +8 with 2.0 decks left (TC +4.0). What is your MIT wager?",
                    caption="Recall the 1-to-12 ramp: <=1 (1u), +2 (2u), +3 (4u), +4 (8u), >=+5 (12u).",
                    cards=(("ace", "clubs", "TC +4.0"), ("king", "diamonds", "8 Units")),
                    formula_banner="TC = +8 / 2.0 = +4.0  ->  How many units?",
                    practice_question="Optimal MIT Bet at TC +4.0 ($25 unit):",
                    practice_choices=STAGE_FIXED_CHOICES["C5"],
                    practice_correct="8 Units ($200)",
                    practice_explanation="You're ready! TC +4.0 calls for 8 Units ($200). Launch C5 to earn your MIT Diploma!",
                ),
            ],
        }

    @staticmethod
    def _rank_tag(rank: str) -> int:
        r = str(rank).lower().strip()
        if r in ("2", "3", "4", "5", "6"):
            return 1
        if r in ("7", "8", "9"):
            return 0
        if r in ("10", "jack", "queen", "king", "ace"):
            return -1
        return 0

    @staticmethod
    def _validate_stage_prompts(stage_id: str, prompts: List[BootcampPrompt]) -> List[BootcampPrompt]:
        """Enforces that every prompt in `stage_id` uses the fixed hotkey tuple and its correct answer is in-range."""
        expected_choices = STAGE_FIXED_CHOICES[stage_id]
        for p in prompts:
            if p.choices != expected_choices:
                raise ValueError(f"Stage {stage_id} prompt {p.prompt_index} changed hotkey choices: {p.choices} != {expected_choices}")
            if p.correct_answer not in expected_choices:
                raise ValueError(f"Stage {stage_id} prompt {p.prompt_index} answer {p.correct_answer!r} not in {expected_choices}")
        return prompts

    def generate_stage_prompts(self, stage_id: str, seed: Optional[int] = None) -> List[BootcampPrompt]:
        """Generates a deterministic or randomized list of drill prompts for `stage_id`."""
        rng = random.Random(seed)
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king", "ace"]
        suits = ["spades", "hearts", "clubs", "diamonds"]
        fixed_choices = STAGE_FIXED_CHOICES.get(stage_id, STAGE_FIXED_CHOICES["C5"])

        if stage_id == "C1":
            prompts: List[BootcampPrompt] = []
            bucket_counts: Dict[int, int] = {1: 0, 0: 0, -1: 0}
            for idx in range(20):
                valid_ranks = [rk for rk in ranks if bucket_counts[self._rank_tag(rk)] < 8]
                r = rng.choice(valid_ranks or ranks)
                s = rng.choice(suits)
                val = self._rank_tag(r)
                bucket_counts[val] = bucket_counts.get(val, 0) + 1
                if val > 0:
                    ans = "+1 (Low)"
                    bucket_desc = "Low Card (2–6) = +1"
                elif val < 0:
                    ans = "-1 (High)"
                    bucket_desc = "High Card (10–A) = -1"
                else:
                    ans = "0 (Neutral)"
                    bucket_desc = "Neutral Card (7–9) = 0"
                prompts.append(
                    BootcampPrompt(
                        prompt_index=idx,
                        stage_id="C1",
                        headline=f"Card {idx + 1}/20: Tag the {r.upper()} of {s.title()}",
                        subheadline="Press [1] +1 (Low), [2] 0 (Neutral), or [3] -1 (High)",
                        cards=((r, s),),
                        choices=fixed_choices,
                        correct_answer=ans,
                        explanation=f"{r.upper()} is a {bucket_desc}.",
                        dealer_callout=f"Spot the bucket for {r.upper()}!",
                    )
                )
            return self._validate_stage_prompts("C1", prompts)

        if stage_id == "C2A":
            prompts = []
            target_nets = [-2, -1, 0, 1, 2, -2, -1, 0, 1, 2, -1, 1]
            rng.shuffle(target_nets)
            for idx, target_net in enumerate(target_nets):
                while True:
                    r1, r2 = rng.choice(ranks), rng.choice(ranks)
                    v1, v2 = self._rank_tag(r1), self._rank_tag(r2)
                    if v1 + v2 == target_net:
                        break
                s1, s2 = rng.choice(suits), rng.choice(suits)
                net = v1 + v2
                ans = f"{net:+d}" if net != 0 else "0"
                prompts.append(
                    BootcampPrompt(
                        prompt_index=idx,
                        stage_id="C2A",
                        headline=f"Pair {idx + 1}/12: Net Count of [{r1.upper()}, {r2.upper()}]",
                        subheadline="Cancel opposing (+1/-1) pairs to 0 or sum matching buckets",
                        cards=((r1, s1), (r2, s2)),
                        choices=fixed_choices,
                        correct_answer=ans,
                        explanation=f"{r1.upper()} ({v1:+d}) + {r2.upper()} ({v2:+d}) = {ans}.",
                        dealer_callout="Cancel pairs before adding!",
                    )
                )
            return self._validate_stage_prompts("C2A", prompts)

        if stage_id == "C2B":
            prompts = []
            rc = 0
            rc_counts: Dict[int, int] = {-2: 0, -1: 0, 0: 0, 1: 0, 2: 0}
            for idx in range(15):
                valid_ranks = [
                    rk for rk in ranks
                    if -2 <= rc + self._rank_tag(rk) <= 2
                    and rc_counts[rc + self._rank_tag(rk)] < 4
                ]
                if not valid_ranks:
                    valid_ranks = [rk for rk in ranks if -2 <= rc + self._rank_tag(rk) <= 2]
                r = rng.choice(valid_ranks)
                s = rng.choice(suits)
                v = self._rank_tag(r)
                prior_rc = rc
                rc += v
                rc_counts[rc] = rc_counts.get(rc, 0) + 1
                ans = f"{rc:+d}" if rc != 0 else "0"
                prompts.append(
                    BootcampPrompt(
                        prompt_index=idx,
                        stage_id="C2B",
                        headline=f"Stream Card {idx + 1}/15: Prior RC {prior_rc:+d} + [{r.upper()}]",
                        subheadline="Update the cumulative Running Count as each card lands",
                        cards=((r, s),),
                        choices=fixed_choices,
                        correct_answer=ans,
                        explanation=f"Prior RC ({prior_rc:+d}) + {r.upper()} ({v:+d}) = {ans}.",
                        dealer_callout=f"Card {idx + 1}: keep the rhythm!",
                        running_count_before=prior_rc,
                    )
                )
            return self._validate_stage_prompts("C2B", prompts)

        if stage_id == "C3A":
            prompts = []
            target_nets = [-2, -1, 0, 1, 2, -2, -1, 0, 1, 2]
            rng.shuffle(target_nets)
            for idx, target_net in enumerate(target_nets):
                while True:
                    table_cards = [(rng.choice(ranks), rng.choice(suits)) for _ in range(5)]
                    vals = [self._rank_tag(r) for r, _ in table_cards]
                    if sum(vals) == target_net:
                        break
                net = sum(vals)
                ans = f"{net:+d}" if net != 0 else "0"
                breakdown = " + ".join(f"{r.upper()}({v:+d})" for (r, _), v in zip(table_cards, vals))
                prompts.append(
                    BootcampPrompt(
                        prompt_index=idx,
                        stage_id="C3A",
                        headline=f"Table Sweep {idx + 1}/10: 2 Player Hands + Dealer Upcard",
                        subheadline="Cancel opposing pairs across seats and report the Net Table Delta",
                        cards=tuple(table_cards),
                        choices=fixed_choices,
                        correct_answer=ans,
                        explanation=f"{breakdown} = {ans}.",
                        dealer_callout="Scan right-to-left and cancel across seats!",
                    )
                )
            return self._validate_stage_prompts("C3A", prompts)

        if stage_id == "C3B":
            prompts = []
            rc = 0
            rc_counts: Dict[int, int] = {-2: 0, -1: 0, 0: 0, 1: 0, 2: 0}
            for idx in range(10):
                prior_rc = rc
                attempts = 0
                while True:
                    attempts += 1
                    runout_cards = [(rng.choice(ranks), rng.choice(suits)) for _ in range(3)]
                    vals = [self._rank_tag(r) for r, _ in runout_cards]
                    candidate_rc = prior_rc + sum(vals)
                    if -2 <= candidate_rc <= 2 and (rc_counts[candidate_rc] < 3 or attempts > 64):
                        break
                rc = candidate_rc
                rc_counts[rc] += 1
                ans = f"{rc:+d}" if rc != 0 else "0"
                breakdown = " + ".join(f"{r.upper()}({v:+d})" for (r, _), v in zip(runout_cards, vals))
                prompts.append(
                    BootcampPrompt(
                        prompt_index=idx,
                        stage_id="C3B",
                        headline=f"Dealer Runout {idx + 1}/10: Prior RC {prior_rc:+d} + Hole Flip & Hits",
                        subheadline="Card 1 = Upcard (count all 3 shown cards onto Prior RC!)",
                        cards=tuple(runout_cards),
                        choices=fixed_choices,
                        correct_answer=ans,
                        explanation=f"Prior RC ({prior_rc:+d}) + {breakdown} = {ans}.",
                        dealer_callout="Dealer flips hole card and draws!",
                        running_count_before=prior_rc,
                    )
                )
            return self._validate_stage_prompts("C3B", prompts)

        if stage_id == "C4":
            scenarios = [
                (6, 3.0, "+2.0"),
                (-4, 4.0, "-1.0"),
                (9, 3.0, "+3.0"),
                (6, 1.5, "+4.0"),
                (3, 3.0, "+1.0"),
                (-2, 2.0, "-1.0"),
                (12, 3.0, "+4.0"),
                (4, 2.0, "+2.0"),
                (6, 2.0, "+3.0"),
                (4, 4.0, "+1.0"),
                (8, 2.0, "+4.0"),
                (12, 4.0, "+3.0"),
            ]
            prompts = []
            for idx, (rc_val, decks_rem, ans_tc) in enumerate(scenarios):
                prompts.append(
                    BootcampPrompt(
                        prompt_index=idx,
                        stage_id="C4",
                        headline=f"Shoe Calibration {idx + 1}/12: RC {rc_val:+d} with {decks_rem:.1f} Decks Left",
                        subheadline="Compute True Count = Running Count / Decks Remaining",
                        cards=(("ace", "spades"), ("king", "hearts")),
                        choices=fixed_choices,
                        correct_answer=ans_tc,
                        explanation=f"RC ({rc_val:+d}) / {decks_rem:.1f} Decks = TC {ans_tc}.",
                        dealer_callout=f"Shoe shows {decks_rem:.1f} decks remaining!",
                        running_count_before=rc_val,
                        decks_remaining=decks_rem,
                    )
                )
            return self._validate_stage_prompts("C4", prompts)

        # Stage C5: Graduation Exam (MIT 1-to-12 Bet Spread & Illustrious 18)
        c5_scenarios = [
            (0, 4.0, "1 Unit ($25)", "TC = 0.0 (<= +1): Bet table minimum 1 Unit ($25)."),
            (-4, 2.0, "1 Unit ($25)", "TC = -2.0 (<= +1): Negative shoe! Bet minimum 1 Unit ($25)."),
            (6, 3.0, "2 Units ($50)", "TC = +6 / 3.0 = +2.0: Ramp to 2 Units ($50)."),
            (9, 3.0, "4 Units ($100)", "TC = +9 / 3.0 = +3.0: Ramp to 4 Units ($100)."),
            (8, 2.0, "8 Units ($200)", "TC = +8 / 2.0 = +4.0: Attack with 8 Units ($200)."),
            (10, 2.0, "12 Units ($300)", "TC = +10 / 2.0 = +5.0: Maximum MIT Bet of 12 Units ($300)!"),
            (4, 4.0, "1 Unit ($25)", "TC = +4 / 4.0 = +1.0: House still has edge; bet 1 Unit ($25)."),
            (6, 2.0, "4 Units ($100)", "TC = +6 / 2.0 = +3.0: Ramp to 4 Units ($100) (& take Insurance!)."),
            (12, 3.0, "8 Units ($200)", "TC = +12 / 3.0 = +4.0: Fire 8 Units ($200)."),
            (15, 2.5, "12 Units ($300)", "TC = +15 / 2.5 = +6.0: Unleash 12 Units ($300) Max Bet!"),
        ]
        prompts = []
        for idx, (rc_val, decks_rem, ans_bet, expl) in enumerate(c5_scenarios):
            prompts.append(
                BootcampPrompt(
                    prompt_index=idx,
                    stage_id="C5",
                    headline=f"Pit Boss Exam {idx + 1}/10: RC {rc_val:+d} | {decks_rem:.1f} Decks Left",
                    subheadline="Convert to True Count and select the official MIT 1-to-12 Wager ($25 base unit)",
                    cards=(("ace", "spades"), ("king", "diamonds"), ("queen", "hearts")),
                    choices=fixed_choices,
                    correct_answer=ans_bet,
                    explanation=expl,
                    dealer_callout=f"New hand! RC is {rc_val:+d} with {decks_rem:.1f} decks in the shoe.",
                    running_count_before=rc_val,
                    decks_remaining=decks_rem,
                )
            )
        return self._validate_stage_prompts("C5", prompts)


class BootcampDrillSession:
    """Tracks live state, response latencies, streaks, and grading for a single Challenge run."""

    def __init__(
        self,
        stage_id: str,
        dag: Optional[BootcampCurriculumDAG] = None,
        seed: Optional[int] = None,
    ) -> None:
        self.stage_id = stage_id
        self.dag = dag or BootcampCurriculumDAG()
        self.node_spec = self.dag.get_node(stage_id)
        self.prompts: List[BootcampPrompt] = self.dag.generate_stage_prompts(stage_id, seed=seed)
        self.current_index: int = 0
        self.correct_count: int = 0
        self.streak: int = 0
        self.best_streak: int = 0
        self.response_times_ms: List[float] = []
        self.history: List[Dict[str, Any]] = []

    def get_current_prompt(self) -> Optional[BootcampPrompt]:
        if 0 <= self.current_index < len(self.prompts):
            return self.prompts[self.current_index]
        return None

    def is_complete(self) -> bool:
        return self.current_index >= len(self.prompts)

    def submit_answer(self, selected_answer: str, response_ms: float) -> Dict[str, Any]:
        prompt = self.get_current_prompt()
        if prompt is None:
            return {"is_correct": False, "complete": True}

        is_correct = (selected_answer == prompt.correct_answer)
        clamped_ms = max(50.0, float(response_ms))
        self.response_times_ms.append(clamped_ms)

        if is_correct:
            self.correct_count += 1
            self.streak += 1
            if self.streak > self.best_streak:
                self.best_streak = self.streak
        else:
            self.streak = 0

        outcome = {
            "prompt_index": self.current_index,
            "selected_answer": selected_answer,
            "correct_answer": prompt.correct_answer,
            "is_correct": is_correct,
            "explanation": prompt.explanation,
            "response_ms": clamped_ms,
            "streak": self.streak,
        }
        self.history.append(outcome)
        self.current_index += 1
        outcome["complete"] = self.is_complete()
        return outcome

    def build_summary(self) -> Dict[str, Any]:
        total = max(1, len(self.prompts))
        accuracy_pct = round(100.0 * self.correct_count / total, 1)
        avg_ms = (
            round(sum(self.response_times_ms) / len(self.response_times_ms), 1)
            if self.response_times_ms
            else self.node_spec.par_ms
        )
        par_ms = self.node_spec.par_ms
        grade = self.dag.compute_stage_grade(accuracy_pct, avg_ms, par_ms)
        score = self.dag.compute_stage_score(accuracy_pct, avg_ms, par_ms)
        passed = GRADE_RANK_ORDER.get(grade, 0) >= GRADE_RANK_ORDER["B"]
        return {
            "stage_id": self.stage_id,
            "title": self.node_spec.title,
            "total_prompts": len(self.prompts),
            "correct_count": self.correct_count,
            "accuracy_pct": accuracy_pct,
            "avg_response_ms": avg_ms,
            "par_ms": par_ms,
            "best_streak": self.best_streak,
            "grade": grade,
            "score": score,
            "passed": passed,
        }

