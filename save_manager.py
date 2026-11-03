"""
Save Data Manager for Blackjack.

Manages persistent storage in blackjack_save.json:
- High scores (peak bankroll, win streaks, hands played/won, blackjacks, counting streaks).
- Achievements (The Exorcist, High Roller, Natural Born Winner, Cursed Survivor,
  Split Maestro, Big Spender, Card Shark, Rain Man).
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
DEFAULT_STARTING_BANKROLL = 1000


@dataclass
class HighScores:
    peak_bankroll: int = 1000
    longest_win_streak: int = 0
    total_hands_played: int = 0
    total_hands_won: int = 0
    total_blackjacks: int = 0
    hell_table_clears: int = 0
    counting_streak: int = 0
    best_counting_streak: int = 0
    counting_quizzes_taken: int = 0
    counting_quizzes_correct: int = 0
    counting_accuracy_pct: float = 0.0
    side_bets_played: int = 0
    side_bets_won: int = 0
    biggest_side_bet_win: int = 0
    bankruptcies: int = 0
    total_bailout_funds: int = 0
    lifetime_wagered: int = 0


@dataclass
class Achievements:
    exorcist: bool = False           # Survived Hell's Table & banished The Pit Fiend
    high_roller: bool = False        # Accumulated $10,000+ bankroll
    natural_streak: bool = False     # 3 Natural Blackjacks in a single session
    cursed_survivor: bool = False    # Survived the cursed 13 card
    split_maestro: bool = False      # Won both split hands
    big_spender: bool = False        # Won a $1,000+ all-in bet
    apprentice_counter: bool = False # 5 consecutive correct card counting quiz answers
    master_counter: bool = False     # 20 consecutive correct card counting quiz answers
    shoe_whisperer: bool = False     # Completed a shoe to cut card with 100% quiz accuracy (min 3 quizzes)
    count_capitalist: bool = False   # Won a $1,000+ wager when True Count >= +3.0
    pair_perfectionist: bool = False # Hit a 25:1 Perfect Pair
    poker_face: bool = False         # Hit Three of a Kind, Straight Flush, or Suited Trips on 21+3


@dataclass
class SaveData:
    version: str = "1.1"
    current_bankroll: int = DEFAULT_STARTING_BANKROLL
    equipped_costume: str = "classic"
    unlocked_costumes: List[str] = field(default_factory=lambda: ["classic", "tiffany"])
    highscores: HighScores = field(default_factory=HighScores)
    achievements: Achievements = field(default_factory=Achievements)
    chips_mode: bool = True
    play_mode: str = "betting"  # "casual" | "betting" | "training"
    onboarding_completed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "current_bankroll": self.current_bankroll,
            "equipped_costume": self.equipped_costume,
            "unlocked_costumes": list(self.unlocked_costumes),
            "highscores": asdict(self.highscores),
            "achievements": asdict(self.achievements),
            "chips_mode": self.chips_mode,
            "play_mode": self.play_mode,
            "onboarding_completed": self.onboarding_completed,
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
            version="1.1",
            current_bankroll=int(data.get("current_bankroll", DEFAULT_STARTING_BANKROLL)),
            equipped_costume=data.get("equipped_costume", "classic"),
            unlocked_costumes=unlocked,
            highscores=HighScores(
                peak_bankroll=hs_data.get("peak_bankroll", 1000),
                longest_win_streak=hs_data.get("longest_win_streak", 0),
                total_hands_played=hs_data.get("total_hands_played", 0),
                total_hands_won=hs_data.get("total_hands_won", 0),
                total_blackjacks=hs_data.get("total_blackjacks", 0),
                hell_table_clears=hs_data.get("hell_table_clears", 0),
                counting_streak=hs_data.get("counting_streak", 0),
                best_counting_streak=hs_data.get("best_counting_streak", 0),
                counting_quizzes_taken=hs_data.get("counting_quizzes_taken", 0),
                counting_quizzes_correct=hs_data.get("counting_quizzes_correct", 0),
                counting_accuracy_pct=float(hs_data.get("counting_accuracy_pct", 0.0)),
                side_bets_played=hs_data.get("side_bets_played", 0),
                side_bets_won=hs_data.get("side_bets_won", 0),
                biggest_side_bet_win=hs_data.get("biggest_side_bet_win", 0),
                bankruptcies=int(hs_data.get("bankruptcies", 0)),
                total_bailout_funds=int(hs_data.get("total_bailout_funds", 0)),
                lifetime_wagered=int(hs_data.get("lifetime_wagered", 0)),
            ),
            achievements=Achievements(
                exorcist=ach_data.get("exorcist", False),
                high_roller=ach_data.get("high_roller", False),
                natural_streak=ach_data.get("natural_streak", False),
                cursed_survivor=ach_data.get("cursed_survivor", False),
                split_maestro=ach_data.get("split_maestro", False),
                big_spender=ach_data.get("big_spender", False),
                apprentice_counter=ach_data.get("apprentice_counter", False),
                master_counter=ach_data.get("master_counter", False),
                shoe_whisperer=ach_data.get("shoe_whisperer", False),
                count_capitalist=ach_data.get("count_capitalist", False),
                pair_perfectionist=ach_data.get("pair_perfectionist", False),
                poker_face=ach_data.get("poker_face", False),
            ),
            chips_mode=bool(data.get("chips_mode", True)),
            play_mode=str(data.get("play_mode", "betting")),
            onboarding_completed=bool(data.get("onboarding_completed", False)),
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

    def set_play_mode(self, mode: str, save_now: bool = True) -> bool:
        """
        Sets the active play mode ('casual', 'betting', 'training') and synchronizes chips_mode.
        """
        if mode in ("casual", "betting", "training"):
            self.data.play_mode = mode
            self.data.chips_mode = (mode != "casual")
            if save_now:
                return self.save()
            return True
        return False

    def complete_onboarding(self, save_now: bool = True) -> bool:
        """Marks initial onboarding splash screen as completed."""
        self.data.onboarding_completed = True
        if save_now:
            return self.save()
        return True

    # --- High Score & Statistics Tracking ---

    def record_bankroll(self, current_bankroll: int):
        """Updates peak bankroll if current exceeds it and checks bankroll unlock milestones."""
        self.data.current_bankroll = current_bankroll
        if current_bankroll >= 5000:
            self.unlock_costume("grim")
        if current_bankroll > self.data.highscores.peak_bankroll:
            self.data.highscores.peak_bankroll = current_bankroll
            if current_bankroll >= 10000:
                self.unlock_achievement("high_roller")
            self.save()
        elif current_bankroll >= 5000:
            self.save()

    def record_round_financials(self, current_bankroll: int, total_wagered: int, save_now: bool = False):
        """
        Records round completion financial state:
        - Updates persistent current_bankroll.
        - Updates peak bankroll and evaluates bankroll milestones.
        - Adds total_wagered to lifetime_wagered.
        - Writes atomically to disk if save_now is True.
        """
        self.data.current_bankroll = current_bankroll
        if current_bankroll > self.data.highscores.peak_bankroll:
            self.data.highscores.peak_bankroll = current_bankroll
        if current_bankroll >= 5000:
            self.unlock_costume("grim")
        if current_bankroll >= 10000:
            self.unlock_achievement("high_roller")
        self.data.highscores.lifetime_wagered += max(0, total_wagered)
        if save_now:
            self.save()

    def record_rebuy(self, amount: int = DEFAULT_STARTING_BANKROLL):
        """
        Records a player bankruptcy rebuy event:
        - Sets persistent current_bankroll to amount.
        - Increments bankruptcies counter.
        - Adds amount to cumulative total_bailout_funds.
        - Saves immediately to disk.
        """
        self.data.current_bankroll = amount
        self.data.highscores.bankruptcies += 1
        self.data.highscores.total_bailout_funds += amount
        self.save()

    def get_net_profit_loss(self) -> int:
        """
        Computes lifetime net profit or loss using the closed-form balance sheet formula:
        Net P/L = current_bankroll - (DEFAULT_STARTING_BANKROLL + total_bailout_funds)
        """
        total_injected = DEFAULT_STARTING_BANKROLL + self.data.highscores.total_bailout_funds
        return self.data.current_bankroll - total_injected

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

    def record_side_bet(self, bet_type: str, outcome: str, bet: int, profit: int, won: bool):
        """Updates side bet statistics, checks high water marks, and evaluates side bet achievements."""
        self.data.highscores.side_bets_played += 1
        if won:
            self.data.highscores.side_bets_won += 1
            if profit > self.data.highscores.biggest_side_bet_win:
                self.data.highscores.biggest_side_bet_win = profit
            if bet_type == "perfect_pairs" and outcome == "PERFECT_PAIR":
                self.unlock_achievement("pair_perfectionist")
            elif bet_type == "21_plus_3" and outcome in ("THREE_OF_A_KIND", "STRAIGHT_FLUSH", "SUITED_TRIPS"):
                self.unlock_achievement("poker_face")
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
        true_count: float = 0.0,
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

        # 6. Big Spender (Win an all-in bet of $1,000+) & Count Capitalist ($1,000+ win at TC >= +3.0)
        if chips_mode and hand_bets:
            total_bet = sum(hand_bets)
            if total_bet >= 1000 and any_won and is_all_in:
                self.unlock_achievement("big_spender")
            if total_bet >= 1000 and any_won and true_count >= 3.0:
                self.unlock_achievement("count_capitalist")

        # 7. Exorcist / Malphas costume
        phase_str = getattr(haunted_phase, "value", str(haunted_phase)).lower()
        if phase_str == "victory":
            self.unlock_achievement("exorcist")
        elif phase_str == "hell_table":
            self.unlock_costume("malphas")

        return current_streak, session_blackjacks

    def record_counting_quiz(self, is_correct: bool) -> tuple[int, bool, bool]:
        """
        Records a card counting quiz result, updates streaks and accuracy telemetry,
        and unlocks achievements.
        Returns: (current_streak, unlocked_apprentice, unlocked_master)
        """
        unlocked_apprentice = False
        unlocked_master = False

        self.data.highscores.counting_quizzes_taken += 1
        if not hasattr(self, "_shoe_quizzes_taken"):
            self._shoe_quizzes_taken = 0
            self._shoe_quizzes_correct = 0
        self._shoe_quizzes_taken += 1

        if is_correct:
            self.data.highscores.counting_quizzes_correct += 1
            self._shoe_quizzes_correct += 1
            self.data.highscores.counting_streak += 1
            cur = self.data.highscores.counting_streak
            if cur > self.data.highscores.best_counting_streak:
                self.data.highscores.best_counting_streak = cur

            if cur >= 5 and not self.data.achievements.apprentice_counter:
                self.unlock_achievement("apprentice_counter")
                unlocked_apprentice = True
            if cur >= 20 and not self.data.achievements.master_counter:
                self.unlock_achievement("master_counter")
                unlocked_master = True
        else:
            self.data.highscores.counting_streak = 0

        taken = max(1, self.data.highscores.counting_quizzes_taken)
        self.data.highscores.counting_accuracy_pct = round(
            100.0 * self.data.highscores.counting_quizzes_correct / taken, 1
        )

        self.save()
        return self.data.highscores.counting_streak, unlocked_apprentice, unlocked_master

    def evaluate_shoe_whisperer(self, reset_shoe_tracker: bool = True) -> bool:
        """
        Evaluates whether the player tracked the shoe to the cut card with 100% quiz accuracy
        across at least 3 quizzes, unlocking the 'shoe_whisperer' achievement.
        """
        taken = getattr(self, "_shoe_quizzes_taken", self.data.highscores.counting_quizzes_taken)
        correct = getattr(self, "_shoe_quizzes_correct", self.data.highscores.counting_quizzes_correct)
        unlocked = False
        if taken >= 3 and correct == taken:
            unlocked = self.unlock_achievement("shoe_whisperer") or self.data.achievements.shoe_whisperer
        if reset_shoe_tracker:
            self._shoe_quizzes_taken = 0
            self._shoe_quizzes_correct = 0
        return unlocked
