"""
Haunted Halloween & Hell's Table Mode Manager for Blackjack.

Encapsulates:
- Phase progression: NORMAL (Hands 1-6) -> CREEP (Hands 7-12) -> OMEN (Hand 13) -> HELL_TABLE.
- 5-Candle snuffing lifecycle on round loss.
- Tug-of-War Soul Meter combat economy (0% Abyss <---> 100% Light, starting at 25%).
- 7 Balatro-style Roguelike Angelic Blessings:
  - Seraph's Grace (Ace dynamic flexibility)
  - Eye of Providence (Dealer hole card reveal)
  - Archangel's Smite (+25% bonus soul push on 21)
  - Cherub's Shield (22 bust forgiveness -> 21)
  - Heavenly Tithe (Safe Double/Split)
  - Miracle Draw (Card banish & redraw)
  - Hallowed Run (Compounding streak multiplier)
- Milestone drafting at 50% and 75% soul meter.
- Persistent unlock tracking (Exorcist badge, Cursed Stakes, Haunted Deck).
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass
from typing import Optional


class Phase(enum.Enum):
    """Lifecycle phases of the Haunted Halloween experience."""
    NORMAL = "normal"          # Hands 1-6: Standard casino gameplay
    CREEP = "creep"            # Hands 7-12: Subtle reality warping, jitters, dimming felt
    OMEN = "omen"              # Hand 13: "13" card dealt, 5 candles appear
    SNUFFING = "snuffing"      # Post-13 hands: Lost rounds extinguish candles (5 -> 0)
    HELL_TABLE = "hell_table"  # 0 candles left: Tug-of-War Soul battle at 25%
    VICTORY = "victory"        # Soul Meter hits 100%: Demon banished
    DEFEAT = "defeat"          # Soul Meter hits 0%: Damnation


class Blessing(enum.Enum):
    """The 7 Balatro-style Celestial Blessings."""
    SERAPH = "seraph"    # Seraph's Grace: Ace flexibility
    EYE = "eye"          # Eye of Providence: Hole card reveal
    SMITE = "smite"      # Archangel's Smite: Double soul push on 21
    SHIELD = "shield"    # Cherub's Shield: 22 bust forgiveness
    TITHE = "tithe"      # Heavenly Tithe: Safe Double/Split
    MIRACLE = "miracle"  # Miracle Draw: Card banish & redraw
    STREAK = "streak"    # Hallowed Run: Streak compounding multiplier


@dataclass(frozen=True)
class BlessingDetails:
    """Metadata describing a blessing for UI displays and drafts."""
    id: Blessing
    title: str
    tagline: str
    description: str
    icon_filename: str


BLESSING_REGISTRY: dict[Blessing, BlessingDetails] = {
    Blessing.SERAPH: BlessingDetails(
        id=Blessing.SERAPH,
        title="Seraph's Grace",
        tagline="Divine Flexibility",
        description="Aces can flexibly evaluate as 1, 10, or 11 to form a winning 21 or avoid a bust.",
        icon_filename="relic_seraph.png",
    ),
    Blessing.EYE: BlessingDetails(
        id=Blessing.EYE,
        title="Eye of Providence",
        tagline="Omniscient Sight",
        description="The dealer's hidden hole card is permanently revealed in a celestial halo.",
        icon_filename="relic_eye.png",
    ),
    Blessing.SMITE: BlessingDetails(
        id=Blessing.SMITE,
        title="Archangel's Smite",
        tagline="Righteous Fury",
        description="Natural Blackjacks and 21s strike with holy force, granting a +25% bonus soul push.",
        icon_filename="relic_smite.png",
    ),
    Blessing.SHIELD: BlessingDetails(
        id=Blessing.SHIELD,
        title="Cherub's Shield",
        tagline="Merciful Forgiveness",
        description="Busting with a total of exactly 22 is forgiven and evaluated as a standing 21.",
        icon_filename="relic_shield.png",
    ),
    Blessing.TITHE: BlessingDetails(
        id=Blessing.TITHE,
        title="Heavenly Tithe",
        tagline="Hallowed Wagers",
        description="Doubling Down or Splitting incurs no extra soul penalty on defeat, but doubles reward on victory.",
        icon_filename="relic_tithe.png",
    ),
    Blessing.MIRACLE: BlessingDetails(
        id=Blessing.MIRACLE,
        title="Miracle Draw",
        tagline="Celestial Second Chance",
        description="Once per round, click any dealt card to banish it and draw a fresh card from the deck.",
        icon_filename="relic_miracle.png",
    ),
    Blessing.STREAK: BlessingDetails(
        id=Blessing.STREAK,
        title="Hallowed Run",
        tagline="Compounding Momentum",
        description="Consecutive winning hands grant an escalating momentum bonus (+5% compounding soul push per win).",
        icon_filename="relic_streak.png",
    ),
}


class HauntedManager:
    """
    Decoupled state machine governing the Haunted Halloween and Hell's Table progression.
    Independent of Tkinter rendering for clean unit testability.
    """

    STARTING_SOUL_METER = 0.25
    BASE_WIN_PUSH = 0.15
    BLACKJACK_WIN_PUSH = 0.30
    BASE_LOSS_PULL = 0.15
    SMITE_BONUS = 0.25
    STREAK_BONUS_PER_WIN = 0.05

    def __init__(self):
        # Progress counters
        self.hand_counter: int = 0
        self.candles_remaining: int = 5
        self.phase: Phase = Phase.NORMAL

        # Combat & Tug-of-War economy
        self.soul_meter: float = self.STARTING_SOUL_METER
        self.consecutive_wins: int = 0
        self.gravestones_risen: int = 0

        # Blessings & Roguelike drafting
        self.equipped_blessings: set[Blessing] = set()
        self.claimed_milestones: set[float] = set()
        self.is_draft_pending: bool = False
        self.miracle_used_this_round: bool = False

        # Persistent Unlocks
        self.unlocked_exorcist: bool = False
        self.unlocked_cursed_stakes: bool = False
        self.unlocked_haunted_deck: bool = False
        self.dealer_view_enabled: bool = False

    def reset_after_victory(self):
        """Resets the slow-burn state machine back to NORMAL mortal play after triumph."""
        self.phase = Phase.NORMAL
        self.candles_remaining = 5
        self.gravestones_risen = 0
        self.soul_meter = self.STARTING_SOUL_METER
        self.equipped_blessings.clear()
        self.claimed_milestones.clear()
        self.consecutive_wins = 0
        self.hand_counter = 0
        # Preserves persistent unlocks:
        self.unlocked_exorcist = True
        self.unlocked_cursed_stakes = True
        self.unlocked_haunted_deck = True

    # ------------------------------------------------------------------------
    # State Progression
    # ------------------------------------------------------------------------

    def on_new_hand(self) -> Phase:
        """
        Advances the hand counter for mortal play and determines current phase.
        Called at the beginning of each deal.
        """
        self.miracle_used_this_round = False

        if self.phase in (Phase.HELL_TABLE, Phase.VICTORY, Phase.DEFEAT):
            return self.phase

        self.hand_counter += 1

        if self.hand_counter < 7:
            self.phase = Phase.NORMAL
        elif self.hand_counter < 13:
            self.phase = Phase.CREEP
        elif self.hand_counter == 13:
            self.phase = Phase.OMEN
        elif self.candles_remaining > 0:
            self.phase = Phase.SNUFFING
        else:
            self.start_hell_table()

        return self.phase

    def on_round_outcome(
        self,
        outcome: str,
        is_double: bool = False,
        is_split: bool = False,
    ) -> tuple[float, str]:
        """
        Processes round completion and updates candles or Tug-of-War Soul Meter.

        Args:
            outcome: Outcome string ('PLAYER_WINS', 'NATURAL_BLACKJACK', 'DEALER_BUST',
                     'PUSH', 'DEALER_WINS', 'PLAYER_BUST', 'SURRENDER').
            is_double: True if player doubled down on this hand.
            is_split: True if hand was from a split.

        Returns:
            tuple[float, str]: (soul_delta, message)
        """
        is_win = outcome in ("PLAYER_WINS", "NATURAL_BLACKJACK", "DEALER_BUST")
        is_loss = outcome in ("DEALER_WINS", "PLAYER_BUST", "SURRENDER")
        is_push = outcome == "PUSH"

        # 1. Mortal / Snuffing Phase
        if self.phase in (Phase.OMEN, Phase.SNUFFING):
            if is_loss:
                self.candles_remaining = max(0, self.candles_remaining - 1)
                self.gravestones_risen += 1
                if self.candles_remaining == 0:
                    self.start_hell_table()
                    return 0.0, "The 5th candle dies! Hell's Table emerges!"
                self.phase = Phase.SNUFFING
                return 0.0, f"A candle dies! {self.candles_remaining} candles remain."
            return 0.0, "The flame holds."

        # 2. Hell's Table Combat
        if self.phase == Phase.HELL_TABLE:
            delta = 0.0

            if is_push:
                # Pushes hold the ground
                return 0.0, "Soul standoff! The line holds."

            if is_win:
                self.consecutive_wins += 1
                delta = self.BLACKJACK_WIN_PUSH if outcome == "NATURAL_BLACKJACK" else self.BASE_WIN_PUSH

                # Double down multiplier
                if is_double:
                    delta *= 2.0

                # Archangel's Smite Blessing
                if Blessing.SMITE in self.equipped_blessings and outcome == "NATURAL_BLACKJACK":
                    delta += self.SMITE_BONUS

                # Hallowed Run Blessing
                if Blessing.STREAK in self.equipped_blessings and self.consecutive_wins > 1:
                    delta += (self.consecutive_wins - 1) * self.STREAK_BONUS_PER_WIN

            elif is_loss:
                self.consecutive_wins = 0
                self.gravestones_risen += 1
                delta = -self.BASE_LOSS_PULL

                # Double down without Tithe increases loss
                if is_double and Blessing.TITHE not in self.equipped_blessings:
                    delta *= 2.0

            # Apply delta to Soul Meter
            self.soul_meter = max(0.0, min(1.0, round(self.soul_meter + delta, 4)))

            # Check for milestone draft triggers (at 50% and 75%)
            if self.soul_meter >= 0.50 and 0.50 not in self.claimed_milestones:
                self.claimed_milestones.add(0.50)
                self.is_draft_pending = True

            if self.soul_meter >= 0.75 and 0.75 not in self.claimed_milestones:
                self.claimed_milestones.add(0.75)
                self.is_draft_pending = True

            # Check victory/defeat
            if self.soul_meter >= 1.0:
                self.phase = Phase.VICTORY
                self.unlocked_exorcist = True
                self.unlocked_cursed_stakes = True
                self.unlocked_haunted_deck = True
                return delta, "VICTORY! The Pit Fiend is banished!"

            if self.soul_meter <= 0.0:
                self.phase = Phase.DEFEAT
                return delta, "DEFEAT! Your soul is forfeit to the House."

            return delta, f"Soul Meter: {int(self.soul_meter * 100)}%"

        return 0.0, ""

    # ------------------------------------------------------------------------
    # Blessing Mechanics
    # ------------------------------------------------------------------------

    def modify_player_score(self, calculated_score: int) -> int:
        """Applies blessings that alter hand scoring (e.g. Cherub's Shield)."""
        if Blessing.SHIELD in self.equipped_blessings and calculated_score == 22:
            return 21
        return calculated_score

    def can_use_miracle_draw(self) -> bool:
        """Determines if the player can use Miracle Draw this round."""
        return (
            self.phase == Phase.HELL_TABLE
            and Blessing.MIRACLE in self.equipped_blessings
            and not self.miracle_used_this_round
        )

    def use_miracle_draw(self):
        """Marks Miracle Draw as used for the active round."""
        self.miracle_used_this_round = True

    def get_draft_choices(self, count: int = 3) -> list[Blessing]:
        """Returns a list of unequipped blessings available for drafting."""
        available = [b for b in Blessing if b not in self.equipped_blessings]
        if not available:
            return []
        sample_count = min(count, len(available))
        return random.sample(available, sample_count)

    def equip_blessing(self, blessing: Blessing):
        """Equips an acquired blessing and clears pending draft status."""
        self.equipped_blessings.add(blessing)
        self.is_draft_pending = False

    # ------------------------------------------------------------------------
    # Mode Transitions & Replayability
    # ------------------------------------------------------------------------

    def start_hell_table(self):
        """Forces the table into Hell's Table mode (used on 5th snuff or Cursed Stakes toggle)."""
        self.phase = Phase.HELL_TABLE
        self.candles_remaining = 0
        self.soul_meter = self.STARTING_SOUL_METER
        self.consecutive_wins = 0
        self.is_draft_pending = True  # Initial blessing draft upon entering Hell

    def second_chance(self):
        """Restores the player to Hell's Table with a fresh 25% soul meter."""
        self.phase = Phase.HELL_TABLE
        self.soul_meter = self.STARTING_SOUL_METER
        self.consecutive_wins = 0
        self.is_draft_pending = False

    def reset_to_mortal(self):
        """Resets the game state back to mortal Normal play."""
        self.phase = Phase.NORMAL
        self.hand_counter = 0
        self.candles_remaining = 5
        self.soul_meter = self.STARTING_SOUL_METER
        self.consecutive_wins = 0
        self.equipped_blessings.clear()
        self.claimed_milestones.clear()
        self.is_draft_pending = False
        self.gravestones_risen = 0
