"""
Save Data Manager for Blackjack.

Manages persistent storage in blackjack_save.json:
- High scores (peak bankroll, win streaks, hands played/won, blackjacks).
- Achievements (The Exorcist, High Roller, Natural Born Winner, Cursed Survivor, Split Maestro, Big Spender).
- Unlocked dealer costumes & equipped preference.
- Blank slate reset with confirmation safety.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SAVE_FILE = BASE_DIR / "blackjack_save.json"


@dataclass
class HighScores:
    peak_bankroll: int = 1000
    longest_win_streak: int = 0
    total_hands_played: int = 0
    total_hands_won: int = 0
    total_blackjacks: int = 0
    hell_table_clears: int = 0


@dataclass
class Achievements:
    exorcist: bool = False           # Survived Hell's Table & banished The Pit Fiend
    high_roller: bool = False        # Accumulated $10,000+ bankroll
    natural_streak: bool = False     # 3 Natural Blackjacks in a single session
    cursed_survivor: bool = False    # Survived the cursed 13 card
    split_maestro: bool = False      # Won both split hands
    big_spender: bool = False        # Won a $1,000+ all-in bet


@dataclass
class SaveData:
    version: str = "1.0"
    equipped_costume: str = "classic"
    unlocked_costumes: List[str] = field(default_factory=lambda: ["classic", "tiffany"])
    highscores: HighScores = field(default_factory=HighScores)
    achievements: Achievements = field(default_factory=Achievements)
    chips_mode: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "equipped_costume": self.equipped_costume,
            "unlocked_costumes": list(self.unlocked_costumes),
            "highscores": asdict(self.highscores),
            "achievements": asdict(self.achievements),
            "chips_mode": self.chips_mode,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SaveData:
        hs_data = data.get("highscores", {})
        ach_data = data.get("achievements", {})
        unlocked = list(data.get("unlocked_costumes", ["classic", "tiffany"]))
        if "classic" not in unlocked:
            unlocked.append("classic")
        if "tiffany" not in unlocked:
            unlocked.append("tiffany")
        return cls(
            version=data.get("version", "1.0"),
            equipped_costume=data.get("equipped_costume", "classic"),
            unlocked_costumes=unlocked,
            highscores=HighScores(
                peak_bankroll=hs_data.get("peak_bankroll", 1000),
                longest_win_streak=hs_data.get("longest_win_streak", 0),
                total_hands_played=hs_data.get("total_hands_played", 0),
                total_hands_won=hs_data.get("total_hands_won", 0),
                total_blackjacks=hs_data.get("total_blackjacks", 0),
                hell_table_clears=hs_data.get("hell_table_clears", 0),
            ),
            achievements=Achievements(
                exorcist=ach_data.get("exorcist", False),
                high_roller=ach_data.get("high_roller", False),
                natural_streak=ach_data.get("natural_streak", False),
                cursed_survivor=ach_data.get("cursed_survivor", False),
                split_maestro=ach_data.get("split_maestro", False),
                big_spender=ach_data.get("big_spender", False),
            ),
            chips_mode=bool(data.get("chips_mode", True)),
        )


class SaveManager:
    """Handles loading, updating, saving, and clearing persistent player data."""

    def __init__(self, save_path: Optional[Path] = None):
        self.save_path = save_path or DEFAULT_SAVE_FILE
        self.data: SaveData = SaveData()
        self.load()

    def load(self) -> SaveData:
        """Loads save data from disk, creating a default blank slate if none exists."""
        if not self.save_path.exists():
            self.data = SaveData()
            self.save()
            return self.data

        try:
            with open(self.save_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.data = SaveData.from_dict(raw)
        except Exception as e:
            logger.warning(f"Failed to parse save file {self.save_path}: {e}. Initializing blank slate.")
            self.data = SaveData()
            self.save()

        return self.data

    def save(self) -> bool:
        """Writes current save data to disk atomically."""
        try:
            tmp_path = self.save_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.data.to_dict(), f, indent=2)
            tmp_path.replace(self.save_path)
            return True
        except Exception as e:
            logger.error(f"Error saving to {self.save_path}: {e}")
            return False

    def clear_save(self) -> bool:
        """Resets in-memory save data to an absolute blank slate and writes to disk."""
        self.data = SaveData()
        return self.save()

    # --- High Score & Statistics Tracking ---

    def record_bankroll(self, current_bankroll: int):
        """Updates peak bankroll if current exceeds it and checks bankroll unlock milestones."""
        if current_bankroll >= 5000:
            self.unlock_costume("grim")
        if current_bankroll > self.data.highscores.peak_bankroll:
            self.data.highscores.peak_bankroll = current_bankroll
            if current_bankroll >= 10000:
                self.unlock_achievement("high_roller")
            self.save()
        elif current_bankroll >= 5000:
            self.save()

    def record_hand_played(self, won: bool, is_blackjack: bool = False):
        """Updates hand counters and win streak."""
        self.data.highscores.total_hands_played += 1
        if won:
            self.data.highscores.total_hands_won += 1
        if is_blackjack:
            self.data.highscores.total_blackjacks += 1
        self.save()

    def record_win_streak(self, streak: int):
        """Updates longest win streak."""
        if streak > self.data.highscores.longest_win_streak:
            self.data.highscores.longest_win_streak = streak
            self.save()

    # --- Achievement & Unlock Tracking ---

    def unlock_achievement(self, achievement_id: str) -> bool:
        """Unlocks an achievement and saves. Returns True if newly unlocked."""
        if not hasattr(self.data.achievements, achievement_id):
            return False
        already_unlocked = getattr(self.data.achievements, achievement_id)
        if not already_unlocked:
            setattr(self.data.achievements, achievement_id, True)
            if achievement_id == "exorcist":
                self.unlock_costume("seraph")
                self.data.highscores.hell_table_clears += 1
            elif achievement_id == "cursed_survivor":
                self.unlock_costume("grim")
            self.save()
            return True
        return False

    def unlock_costume(self, costume_id: str) -> bool:
        """Unlocks a dealer costume if not already available."""
        if costume_id not in self.data.unlocked_costumes:
            self.data.unlocked_costumes.append(costume_id)
            self.save()
            return True
        return False

    def equip_costume(self, costume_id: str) -> bool:
        """Sets the current equipped dealer costume if unlocked."""
        if costume_id in self.data.unlocked_costumes:
            self.data.equipped_costume = costume_id
            self.save()
            return True
        return False

    def set_chips_mode(self, enabled: bool):
        """Persists player preference for Chips Mode vs Casual Mode."""
        self.data.chips_mode = enabled
        self.save()

    def evaluate_round_achievements(
        self,
        outcomes: list[str],
        player_hands: list,
        dealer_hand: list,
        current_streak: int,
        chips_mode: bool,
        current_bankroll: int,
        hand_bets: list[int],
        is_all_in: bool,
        haunted_phase: Any,
        session_blackjacks: int,
    ) -> tuple[int, int]:
        """
        Evaluates round outcomes, records statistics, updates streaks, and unlocks achievements.
        Returns (new_win_streak, new_session_blackjacks).
        """
        win_outcomes = ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK')
        loss_outcomes = ('DEALER_WINS', 'PLAYER_BUST', 'SURRENDER')

        # 1. Update hands played / won / blackjacks & win streak
        any_won = False
        all_lost = True
        for outcome in outcomes:
            p_won = outcome in win_outcomes
            p_bj = outcome == 'NATURAL_BLACKJACK'
            if p_won:
                any_won = True
                all_lost = False
            elif outcome not in loss_outcomes:
                all_lost = False
            self.record_hand_played(won=p_won, is_blackjack=p_bj)

        if any_won:
            current_streak += 1
            self.record_win_streak(current_streak)
        elif all_lost:
            current_streak = 0

        # 2. Record bankroll in Chips Mode
        if chips_mode:
            self.record_bankroll(current_bankroll)

        # 3. Natural Born Winner (3 natural blackjacks in session)
        bjs_in_round = sum(1 for o in outcomes if o == 'NATURAL_BLACKJACK')
        if bjs_in_round > 0:
            session_blackjacks += bjs_in_round
            if session_blackjacks >= 3:
                self.unlock_achievement("natural_streak")

        # 4. Cursed Survivor (Survive Card 13 round with win or push)
        card_13_present = any(
            getattr(c, "rank", "") == "thirteen" or (isinstance(c, (tuple, list)) and c[0] == 13)
            for h in player_hands for c in h
        ) or any(
            getattr(c, "rank", "") == "thirteen" or (isinstance(c, (tuple, list)) and c[0] == 13)
            for c in dealer_hand
        )
        if card_13_present:
            survived = any(o in (*win_outcomes, 'PUSH') for o in outcomes)
            if survived:
                self.unlock_achievement("cursed_survivor")

        # 5. Split Maestro (Win both split hands)
        if len(player_hands) > 1 and len(outcomes) >= 2:
            if all(o in win_outcomes for o in outcomes):
                self.unlock_achievement("split_maestro")

        # 6. Big Spender (Win an all-in bet of $1,000+)
        if chips_mode and hand_bets:
            total_bet = sum(hand_bets)
            if total_bet >= 1000 and any_won and is_all_in:
                self.unlock_achievement("big_spender")

        # 7. Exorcist / Malphas costume
        phase_str = getattr(haunted_phase, "value", str(haunted_phase)).lower()
        if phase_str == "victory":
            self.unlock_achievement("exorcist")
        elif phase_str == "hell_table":
            self.unlock_costume("malphas")

        return current_streak, session_blackjacks
