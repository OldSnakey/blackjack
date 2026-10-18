"""
Blackjack GUI Game in Python using Tkinter.

This implementation demonstrates:
- Clean separation between pure game logic and presentation (GUI).
- Robust, non-blocking asynchronous timers with `root.after()` instead of `time.sleep()`.
- Strict button state management to prevent race conditions and re-entrant callbacks.
- Authentic casino Blackjack rules: Dealer Hole Card (face-down), Natural 21 detection,
  and automatic standing on 21.
- Safe cross-platform asset path resolution using Python's `pathlib`.
"""

from __future__ import annotations

import math
import os
import random
import sys
import tempfile
import tkinter
from pathlib import Path
from typing import Optional, Callable, Any

from save_manager import SaveManager, DEFAULT_SAVE_FILE
from dealer_actor import DealerActor, CharacterProfile, CHARACTERS, COSTUME_ALIASES
from dealer_wardrobe_dialog import WardrobeDialog

# Silence pygame greeting message on import to ensure clean stdout in CLI pipelines
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Optional pygame.mixer support for authentic tactile casino audio
try:
    # pyrefly: ignore [missing-import]
    from pygame import mixer as pygame_mixer
    PYGAME_AVAILABLE = True
except (ImportError, Exception):
    pygame_mixer = None
    PYGAME_AVAILABLE = False

# Optional Pillow support for dynamic in-memory High-DPI scaling
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except (ImportError, Exception):
    Image = None
    ImageTk = None
    ImageDraw = None
    ImageFont = None
    PIL_AVAILABLE = False

# ============================================================================
# Application Metadata & Named Constants
# ============================================================================
__version__ = "1.3.0"

# Standard Blackjack target and casino dealer rules
BLACKJACK_TARGET = 21
DEALER_STAND_THRESHOLD = 17  # Standard casino rule: Dealer must stand on 17 or higher

# Shoe and Multi-Deck Configuration
DEFAULT_DECK_COUNT = 4  # Standard casino multi-deck shoe (4 decks = 208 cards)
CUT_CARD_PENETRATION = 0.25  # Cut card reshuffle trigger (when <= 25% cards remain)

# Bankroll and Betting Configuration
STARTING_BANKROLL = 1000
MINIMUM_BET = 5
CHIP_DENOMINATIONS = [
    (5, "#f5f5f5", "#000000"),    # White $5
    (25, "#c62828", "#ffffff"),   # Red $25
    (100, "#2e7d32", "#ffffff"),  # Green $100
    (500, "#212121", "#ffd700"),  # Black & Gold $500
]
INSURANCE_PAYOUT_RATIO = 2  # Standard casino rule: Insurance pays 2 to 1

# UI Animation Timing (in milliseconds)
# 700ms provides an authentic, observable card-dealing cadence without feeling sluggish
# or stalling the game flow.
DEALER_DRAW_DELAY_MS = 700

# Window dimensions and styling
DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 720
MIN_WINDOW_WIDTH = 760
MIN_WINDOW_HEIGHT = 650
CARD_WIDTH = 74
CARD_HEIGHT = 107
PLAYER_CARD_OVERLAP_OFFSET = 26
TABLE_BACKGROUND_COLOR = "#0b6623"  # Classic casino felt green
PANEL_BACKGROUND_COLOR = "#074c1a"  # Slightly darker green for contrasting frames

# Asset paths resolved relative to bundle/script directory for portability
def get_base_dir() -> Path:
    """
    Resolves the base directory for resource loading across standard Python execution
    and PyInstaller frozen bundles (both --onedir and --onefile).
    """
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            mei_path = Path(sys._MEIPASS)
            if (mei_path / "cards").exists():
                return mei_path
        exe_parent = Path(sys.executable).resolve().parent
        if (exe_parent / "cards").exists():
            return exe_parent
        if (exe_parent / "_internal" / "cards").exists():
            return exe_parent / "_internal"
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
ASSETS_DIR = BASE_DIR / "cards"
AUDIO_DIR = BASE_DIR / "audio"
ASSETS_EXTRA_DIR = BASE_DIR / "assets"
OVERLAY_ICONS_DIR = ASSETS_EXTRA_DIR / "overlay_icons"
HAUNTED_ASSETS_DIR = ASSETS_EXTRA_DIR / "haunted"
HAUNTED_AUDIO_DIR = AUDIO_DIR / "haunted"
DEFAULT_SOUND_VOLUME = 0.7

from haunted_manager import HauntedManager, Phase, Blessing, BLESSING_REGISTRY


# ============================================================================
# Pure Game Logic (Independent of GUI)
# ============================================================================

class Card(tuple):
    """
    Represents a playing card.
    Subclasses tuple for backwards compatibility:
      card[0] == value
      card[1] == PhotoImage
    Provides rank and suit attributes for inspection and extensibility.
    """
    def __new__(cls, value: int, image: tkinter.PhotoImage, rank: str = "", suit: str = ""):
        instance = super().__new__(cls, (value, image))
        instance.value = value
        instance.image = image
        instance.rank = rank
        instance.suit = suit
        return instance

    def __repr__(self):
        return f"Card({self.rank.capitalize()} of {self.suit.capitalize()}, value={self.value})"


def score_hand(hand):
    """
    Calculates the best Blackjack score for a hand.

    Args:
        hand: A list of card values (integers 1-10) or card tuples (value, image).

    Returns:
        int: The optimal score (up to 21, or lowest bust score).

    How Ace handling works:
    - Number cards (2-10) count as their face value.
    - Face cards (Jack, Queen, King) have value 10.
    - Aces initially count as 1. If promoting one Ace to 11 does not cause
      the total score to exceed 21, 10 is added. At most ONE Ace can count as 11,
      because 11 + 11 = 22 > 21.
    """
    values = [card[0] if isinstance(card, (tuple, list)) else card for card in hand]
    score = sum(values)
    if 1 in values and score + 10 <= BLACKJACK_TARGET:
        score += 10
    return score


def dealer_should_hit(dealer_hand):
    """
    Determines if the dealer must draw another card.
    Under standard S17 rules, the dealer must hit on any score below 17.
    """
    return score_hand(dealer_hand) < DEALER_STAND_THRESHOLD


def can_split(player_hand):
    """
    Determines if a hand is eligible to split.
    A hand is eligible if it contains exactly two cards of the same rank (or value).
    """
    if len(player_hand) != 2:
        return False
    card1, card2 = player_hand
    rank1 = getattr(card1, 'rank', None)
    rank2 = getattr(card2, 'rank', None)
    if rank1 is not None and rank2 is not None:
        return rank1 == rank2
    val1 = card1[0] if isinstance(card1, (tuple, list)) else card1
    val2 = card2[0] if isinstance(card2, (tuple, list)) else card2
    return val1 == val2


def determine_outcome(player_hand, dealer_hand, is_split: bool = False, player_score_override: int | None = None):
    """
    Evaluates the final result of a round once both player and dealer have completed their turns.

    Args:
        player_hand: List of card values or Card instances for the player.
        dealer_hand: List of card values or Card instances for the dealer.
        is_split: Whether this hand originated from a split. Split 21s cannot be Natural Blackjacks.
        player_score_override: Optional explicit score to use for player (e.g. from blessings).

    Returns:
        tuple[str, str]: (outcome_code, display_message)
    """
    player_score = player_score_override if player_score_override is not None else score_hand(player_hand)
    dealer_score = score_hand(dealer_hand)

    # 1. Player Bust
    if player_score > BLACKJACK_TARGET:
        return 'PLAYER_BUST', 'You bust, dealer wins!'

    # Check for natural blackjacks (2 cards totaling 21 on initial deal, un-split)
    player_natural = (not is_split and len(player_hand) == 2 and player_score == BLACKJACK_TARGET)
    dealer_natural = (len(dealer_hand) == 2 and dealer_score == BLACKJACK_TARGET)

    if player_natural and dealer_natural:
        return 'PUSH', "Both have Blackjack! It's a draw."
    if player_natural:
        return 'NATURAL_BLACKJACK', 'Player has Blackjack! You win!'
    if dealer_natural:
        return 'DEALER_WINS', 'Dealer has Blackjack! Dealer wins!'

    # 2. Dealer Bust
    if dealer_score > BLACKJACK_TARGET:
        return 'DEALER_BUST', 'Dealer busts, Player WINS!'

    # 3. Compare Scores
    if player_score > dealer_score:
        return 'PLAYER_WINS', 'Player WINS!'
    elif dealer_score > player_score:
        return 'DEALER_WINS', 'The dealer wins!'
    else:
        return 'PUSH', "It's a draw"


def calculate_payout(outcome: str, bet: int) -> int:
    """
    Calculates the total payout (return of wager plus winnings) for a given outcome and bet.

    Args:
        outcome: Outcome code from determine_outcome ('NATURAL_BLACKJACK', 'PLAYER_WINS',
                 'DEALER_BUST', 'PUSH', 'SURRENDER', 'DEALER_WINS', 'PLAYER_BUST').
        bet: The amount wagered on this hand (integer >= 0).

    Returns:
        int: Total return to the player (0 for loss, bet for push, 2*bet for standard win,
             bet + int(bet * 1.5) for 3:2 natural blackjack, bet // 2 for surrender).
    """
    if bet <= 0:
        return 0
    if outcome == 'NATURAL_BLACKJACK':
        return bet + int(bet * 1.5)
    elif outcome in ('PLAYER_WINS', 'DEALER_BUST'):
        return bet * 2
    elif outcome == 'PUSH':
        return bet
    elif outcome == 'SURRENDER':
        return bet // 2
    else:
        # 'DEALER_WINS', 'PLAYER_BUST', or any other loss outcome
        return 0


def calculate_insurance_payout(dealer_has_blackjack: bool, insurance_bet: int, main_bet: int = 0) -> int:
    """
    Calculates the total payout returned for an Insurance side bet.
    Insurance pays 2:1. When main_bet is specified and insurance_bet is full insurance
    for an odd wager (e.g. $2 insurance on a $5 bet), the payout is rounded up to fully
    cover the main bet, guaranteeing a $0 net breakeven round. Partial insurance wagers
    pay standard 2:1.

    Args:
        dealer_has_blackjack: True if the dealer has a 2-card 21 (Natural Blackjack).
        insurance_bet: The amount wagered on insurance (integer >= 0).
        main_bet: The original main bet being insured (optional integer >= 0).

    Returns:
        int: Total return to the player (original insurance_bet + profit).
    """
    if insurance_bet <= 0 or not dealer_has_blackjack:
        return 0
    if main_bet > 0 and insurance_bet == main_bet // 2:
        profit = max(main_bet, insurance_bet * INSURANCE_PAYOUT_RATIO)
        return insurance_bet + profit
    return insurance_bet + (insurance_bet * INSURANCE_PAYOUT_RATIO)


def breakdown_chips(amount: int) -> list[tuple[int, int]]:
    """
    Decomposes an integer wager into denomination counts greedily from highest to lowest.
    Supported denominations: $500, $100, $25, $5, and $1 (silver remainder).

    Args:
        amount: Integer wager amount (>= 0).

    Returns:
        list[tuple[int, int]]: List of (denomination, count) pairs for denominations with count > 0.
    """
    if amount <= 0:
        return []
    result = []
    remaining = amount
    for denom in (500, 100, 25, 5, 1):
        count = remaining // denom
        if count > 0:
            result.append((denom, count))
            remaining %= denom
    return result


# Visual styling map for 2.5D procedural chip rendering
CHIP_STYLES = {
    500: {"bg": "#212121", "fg": "#ffd700", "rim": "#111111", "stripe": "#ffd700"},
    100: {"bg": "#2e7d32", "fg": "#ffffff", "rim": "#1b5e20", "stripe": "#ffffff"},
    25:  {"bg": "#c62828", "fg": "#ffffff", "rim": "#8e0000", "stripe": "#ffffff"},
    5:   {"bg": "#f5f5f5", "fg": "#212121", "rim": "#bdbdbd", "stripe": "#c62828"},
    1:   {"bg": "#9e9e9e", "fg": "#ffffff", "rim": "#616161", "stripe": "#ffffff"},
}


class ChipVisualizer(tkinter.Canvas):
    """
    Renders a procedural 2.5D casino felt betting spot with 3D stacked chips
    and non-blocking micro-animations for drops, clears, payouts, sweeps, and pushes.
    """

    def __init__(self, master, width=180, height=135, background=PANEL_BACKGROUND_COLOR, **kwargs):
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.scale = 1.0
        self.canvas_width = width
        self.canvas_height = height
        self.cx = width // 2
        self.cy = height // 2
        self.current_bet = 0
        self._active_timers = set()
        self._felt_slice_photo: Optional[Any] = None
        self._felt_source_img: Optional[Any] = None
        self._felt_coords: Optional[tuple[int, int]] = None

        self._draw_base_spot()

    def sync_felt_background(self, felt_img: Optional[Any], rel_x: int, rel_y: int):
        """Draws the underlying felt texture slice as the canvas background item safely with no black borders."""
        if not PIL_AVAILABLE or not felt_img:
            return
        self._felt_source_img = felt_img
        self._felt_coords = (rel_x, rel_y)
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        try:
            bg_rgb = (7, 76, 26)
            if hasattr(self.master, "THEME_COLORS") and hasattr(self.master, "current_theme"):
                bg_rgb = self.master.THEME_COLORS.get(self.master.current_theme, {}).get("base", bg_rgb)
            slice_img = Image.new("RGB", (w, h), bg_rgb)
            src_x1 = max(0, rel_x)
            src_y1 = max(0, rel_y)
            src_x2 = min(felt_img.width, rel_x + w)
            src_y2 = min(felt_img.height, rel_y + h)
            if src_x2 > src_x1 and src_y2 > src_y1:
                cropped = felt_img.crop((src_x1, src_y1, src_x2, src_y2))
                slice_img.paste(cropped, (src_x1 - rel_x, src_y1 - rel_y))
            self._felt_slice_img = slice_img
            self._felt_slice_photo = ImageTk.PhotoImage(slice_img, master=self)
            if not self.find_withtag("felt_bg"):
                self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
            else:
                self.itemconfigure("felt_bg", image=self._felt_slice_photo)
            self.tag_lower("felt_bg")
        except Exception:
            pass

    def set_scale(self, scale: float):
        """Scales visualizer canvas and re-renders base spot proportionally without table overflow."""
        self.scale = scale
        self.canvas_width = int(180 * scale)
        self.canvas_height = int(135 * (1.0 if scale <= 1.0 else 1.25))
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.cx = self.canvas_width // 2
        self.cy = self.canvas_height // 2
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        self._draw_base_spot()
        if self.current_bet > 0:
            self.render_stacks(self.current_bet)


    def _draw_base_spot(self):
        """Draws the felt betting spot: outer dashed gold ellipse, inner accent ring, watermark, and badge."""
        self.delete("all")
        cx, cy = self.cx, self.cy
        s = getattr(self, "scale", 1.0)

        # 0. Underlying felt slice background
        if getattr(self, "_felt_slice_photo", None):
            self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")

        # 1. Outer betting circle felt background and golden dashed ring (fill empty for authentic felt texture)
        self.create_oval(
            cx - int(74 * s), cy - int(38 * s), cx + int(74 * s), cy + int(38 * s),
            outline="#d4af37", width=max(1, int(2 * s)), dash=(4, 3), fill="", tags="spot_base"
        )
        # 2. Inner subtle gold accent ring
        self.create_oval(
            cx - int(66 * s), cy - int(32 * s), cx + int(66 * s), cy + int(32 * s),
            outline="#8a6d1b", width=1, dash=(2, 3), tags="spot_ring"
        )
        # 3. Felt watermark
        self.create_text(
            cx, cy + int(1 * s), text="BETTING SPOT", fill="#8a6d1b",
            font=("Arial", max(6, int(7 * s)), "bold"), tags="watermark"
        )
        # 4. Top badge for bet amount
        self.create_text(
            cx, int(13 * s), text="", fill="#ffd700",
            font=("Arial", max(8, int(9 * s)), "bold"), tags="badge"
        )

    def _is_animation_enabled(self) -> bool:
        """Determines if animations should run (only when window is actively mapped)."""
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except Exception:
            return False

    def _schedule(self, ms: int, callback):
        """Wraps root.after to automatically register and clean up active timer callbacks."""
        timer_id = None
        def wrapper():
            if timer_id in self._active_timers:
                self._active_timers.discard(timer_id)
            if self.winfo_exists():
                callback()

        timer_id = self.after(ms, wrapper)
        self._active_timers.add(timer_id)
        return timer_id

    def clear_timers(self):
        """Cancels all active animation callbacks."""
        for tid in list(self._active_timers):
            try:
                self.after_cancel(tid)
            except Exception:
                pass
        self._active_timers.clear()

    def set_bet(self, amount: int, animate: bool = True):
        """Updates the visualized bet amount."""
        self.current_bet = amount
        if amount <= 0:
            self.animate_clear(animated=animate)
        else:
            self.render_stacks(amount)

    def render_stacks(self, amount: int):
        """Procedurally draws 2.5D chip stacks representing the specified amount."""
        self.delete("chip")
        self.delete("anim_chip")
        self.delete("floating_text")

        if amount <= 0:
            self.itemconfigure("badge", text="")
            return

        self.itemconfigure("badge", text=f"BET: ${amount:,}")

        breakdown = breakdown_chips(amount)
        if not breakdown:
            return

        num_stacks = len(breakdown)
        spacing = 26 if num_stacks >= 4 else 30
        total_span = (num_stacks - 1) * spacing
        start_x = self.cx - (total_span // 2)
        base_y = self.cy + 10

        for s_idx, (denom, count) in enumerate(breakdown):
            stack_x = start_x + (s_idx * spacing)
            style = CHIP_STYLES.get(denom, CHIP_STYLES[5])

            offset_y = 0
            if num_stacks >= 3 and s_idx % 2 == 1:
                offset_y = -3

            visible_count = min(count, 6)
            for c_idx in range(visible_count):
                chip_y = (base_y + offset_y) - (c_idx * 3)
                is_top = (c_idx == visible_count - 1)
                self._draw_single_chip(
                    stack_x, chip_y, denom, style, is_top=is_top,
                    count=count if count > 6 and is_top else None, tags="chip"
                )

    def _draw_single_chip(self, x: int, y: int, denom: int, style: dict, is_top: bool = False, count: int = None, tags="chip"):
        """Draws one 2.5D chip with rim thickness, edge stripes, top face, and denomination."""
        s = getattr(self, "scale", 1.0)
        rx, ry, depth = int(15 * s), int(8 * s), int(4 * s)

        # 1. Shadow / bottom rim
        self.create_oval(
            x - rx, y - ry + depth, x + rx, y + ry + depth,
            fill=style["rim"], outline=style["rim"], tags=tags
        )
        self.create_rectangle(
            x - rx, y, x + rx, y + depth,
            fill=style["rim"], outline=style["rim"], tags=tags
        )

        # 2. Edge stripes
        self.create_line(x - int(8 * s), y + 1, x - int(8 * s), y + depth, fill=style["stripe"], width=max(1, int(2 * s)), tags=tags)
        self.create_line(x + int(8 * s), y + 1, x + int(8 * s), y + depth, fill=style["stripe"], width=max(1, int(2 * s)), tags=tags)

        # 3. Top face
        self.create_oval(
            x - rx, y - ry, x + rx, y + ry,
            fill=style["bg"], outline="#ffffff", width=1, tags=tags
        )
        # Inner dashed circle
        self.create_oval(
            x - rx + int(3 * s), y - ry + int(2 * s), x + rx - int(3 * s), y + ry - int(2 * s),
            outline=style["fg"], dash=(2, 2), tags=tags
        )

        # 4. Text (denomination or count badge if stack is capped)
        display_text = f"x{count}" if (count and count > 6) else f"${denom}"
        self.create_text(
            x, y, text=display_text, fill=style["fg"],
            font=("Arial", 6 if len(display_text) > 3 else 7, "bold"), tags=tags
        )

    def animate_chip_drop(self, added_amount: int, new_total: int, animated: bool = True):
        """Plays a tactile drop-and-bounce animation when a chip is added."""
        self.current_bet = new_total
        if not animated or not self._is_animation_enabled():
            self.render_stacks(new_total)
            return

        style = CHIP_STYLES.get(added_amount, CHIP_STYLES[5])
        drop_x = self.cx
        target_y = self.cy + 10
        start_y = target_y - 24

        drop_tag = "anim_chip"
        self.delete(drop_tag)
        self._draw_single_chip(drop_x, start_y, added_amount, style, is_top=True, tags=drop_tag)

        def frame1():
            self.move(drop_tag, 0, 12)
            self._schedule(16, frame2)

        def frame2():
            self.move(drop_tag, 0, 14)
            self._schedule(16, frame3)

        def frame3():
            self.delete(drop_tag)
            self.render_stacks(new_total)

        self._schedule(16, frame1)

    def animate_clear(self, animated: bool = True):
        """Animates chips sliding downwards off the table when bet is cleared."""
        self.current_bet = 0
        if not animated or not self._is_animation_enabled():
            self.delete("chip")
            self.delete("anim_chip")
            self.delete("floating_text")
            self.itemconfigure("badge", text="")
            return

        def step(count=0):
            if count >= 4:
                self.delete("chip")
                self.delete("anim_chip")
                self.delete("floating_text")
                self.itemconfigure("badge", text="")
            else:
                self.move("chip", 0, 14)
                self.move("anim_chip", 0, 14)
                self._schedule(16, lambda: step(count + 1))

        step()

    def animate_win(self, profit: int, animated: bool = True):
        """Animates dealer payout sliding in from top, glowing +$XX text, and chip collection."""
        if not animated or not self._is_animation_enabled():
            return

        payout_tag = "payout_stack"
        text_tag = "floating_text"
        self.delete(payout_tag)
        self.delete(text_tag)

        breakdown = breakdown_chips(max(profit, 5))
        top_denom = breakdown[0][0] if breakdown else 25
        style = CHIP_STYLES.get(top_denom, CHIP_STYLES[25])

        for c in range(min(3, len(breakdown))):
            self._draw_single_chip(self.cx + 20, -20 - (c * 3), top_denom, style, is_top=(c == 2), tags=payout_tag)

        def slide_payout(frame=0):
            if frame >= 5:
                self.create_text(
                    self.cx, self.cy - 16, text=f"+${profit:,}", fill="#ffd700",
                    font=("Arial", 11, "bold"), tags=text_tag
                )
                self._schedule(20, float_text)
            else:
                self.move(payout_tag, 0, 18)
                self._schedule(18, lambda: slide_payout(frame + 1))

        def float_text(frame=0):
            if frame >= 4:
                self._schedule(400, collect_chips)
            else:
                self.move(text_tag, 0, -3)
                self._schedule(20, lambda: float_text(frame + 1))

        def collect_chips(frame=0):
            if frame >= 5:
                self.delete(payout_tag)
                self.delete("chip")
                self.delete(text_tag)
                self.itemconfigure("badge", text="")
            else:
                self.move(payout_tag, -12, 16)
                self.move("chip", -12, 16)
                self.move(text_tag, -4, 4)
                self._schedule(18, lambda: collect_chips(frame + 1))

        slide_payout()

    def animate_loss(self, animated: bool = True):
        """Animates dealer sweeping the chips upward toward the dealer tray."""
        if not animated or not self._is_animation_enabled():
            self.delete("chip")
            self.delete("anim_chip")
            self.delete("floating_text")
            self.itemconfigure("badge", text="")
            return

        text_tag = "floating_text"
        self.delete(text_tag)

        def sweep_chips(frame=0):
            if frame >= 5:
                self.delete("chip")
                self.delete("anim_chip")
                self.delete(text_tag)
                self.itemconfigure("badge", text="")
            else:
                self.move("chip", 0, -18)
                self.move("anim_chip", 0, -18)
                self._schedule(18, lambda: sweep_chips(frame + 1))

        sweep_chips()

    def animate_push(self, animated: bool = True):
        """Highlights the betting spot on push and returns chips to player."""
        if not animated or not self._is_animation_enabled():
            return

        text_tag = "floating_text"
        self.delete(text_tag)
        self.create_text(
            self.cx, self.cy - 16, text="PUSH", fill="#ffffff",
            font=("Arial", 10, "bold"), tags=text_tag
        )

        self.itemconfigure("spot_base", outline="#ffffff")

        def reset_ring():
            self.itemconfigure("spot_base", outline="#d4af37")
            self.animate_clear(animated=True)

        self._schedule(450, reset_ring)


class SoulMeterCanvas(tkinter.Canvas):
    """
    Renders an animated 2.5D Tug-of-War Soul Meter during Hell's Table Mode.
    Visualizes the struggle between the mortal soul (0% Abyss) and celestial freedom (100% Light).
    """

    def __init__(self, master, width=180, height=135, background="#140508", **kwargs):
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.scale = 1.0
        self.canvas_width = width
        self.canvas_height = height
        self.cx = width // 2
        self.cy = height // 2
        self.current_value = 0.25
        self.target_value = 0.25
        self._anim_timer_id = None
        self._draw_meter()

    def set_scale(self, scale: float):
        """Scales soul meter canvas dimensions proportionally."""
        self.scale = scale
        self.canvas_width = int(180 * scale)
        self.canvas_height = int(135 * scale)
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.cx = self.canvas_width // 2
        self.cy = self.canvas_height // 2
        self._draw_meter()

    def set_meter(self, value: float, animated: bool = True):
        """Sets target soul value (0.0 to 1.0) and animates smoothly."""
        self.target_value = max(0.0, min(1.0, value))
        if not animated or not self._is_animation_enabled():
            self.current_value = self.target_value
            self._draw_meter()
            return

        self._cancel_timer()
        self._step_animation()

    def _step_animation(self):
        """Steps towards target_value in non-blocking increments."""
        diff = self.target_value - self.current_value
        if abs(diff) < 0.01:
            self.current_value = self.target_value
            self._draw_meter()
            return

        self.current_value += diff * 0.25
        self._draw_meter()
        self._anim_timer_id = self.after(25, self._step_animation)

    def _draw_meter(self):
        self.delete("all")
        cx, cy = self.cx, self.cy
        s = getattr(self, "scale", 1.0)

        # 1. Dark ornate frame with ember trim
        self._draw_rounded_rect(5, 5, self.canvas_width - 5, self.canvas_height - 5, radius=int(8 * s), fill="#0d0204", outline="#8b0000", width=max(1, int(2 * s)))

        # 2. Header
        self.create_text(cx, int(16 * s), text="☠ SOUL WAGER ☠", fill="#ffd700", font=("Arial", max(7, int(8 * s)), "bold"))

        # 3. Bar dimensions
        bx1, by1 = int(16 * s), int(42 * s)
        bx2, by2 = self.canvas_width - int(16 * s), int(62 * s)
        bar_w = bx2 - bx1

        # Background track
        self.create_rectangle(bx1, by1, bx2, by2, fill="#240004", outline="#4a000a", width=1)

        # Milestones (50% and 75%)
        m50_x = bx1 + int(bar_w * 0.50)
        m75_x = bx1 + int(bar_w * 0.75)
        self.create_line(m50_x, by1 - 3, m50_x, by2 + 3, fill="#80cbc4", width=1, dash=(2, 2))
        self.create_line(m75_x, by1 - 3, m75_x, by2 + 3, fill="#ffd700", width=1, dash=(2, 2))
        self.create_text(m50_x, by1 - int(7 * s), text="50%", fill="#80cbc4", font=("Arial", max(6, int(6 * s)), "bold"))
        self.create_text(m75_x, by1 - int(7 * s), text="75%", fill="#ffd700", font=("Arial", max(6, int(6 * s)), "bold"))

        # Fill segment
        fill_x = bx1 + int(bar_w * self.current_value)
        if fill_x > bx1:
            fill_color = "#ff1744" if self.current_value < 0.35 else ("#ffd700" if self.current_value < 0.70 else "#00e5ff")
            self.create_rectangle(bx1, by1, fill_x, by2, fill=fill_color, outline="")

        # Tug pointer
        p_w = int(5 * s)
        p_h = int(6 * s)
        self.create_polygon([fill_x, by1 - 3, fill_x - p_w, by1 - 3 - p_h, fill_x + p_w, by1 - 3 - p_h], fill="#ffffff", outline="#ffd700")

        # 4. Labels
        self.create_text(bx1 + int(16 * s), by2 + int(10 * s), text="ABYSS 0%", fill="#ff5252", font=("Arial", max(6, int(7 * s)), "bold"))
        self.create_text(bx2 - int(16 * s), by2 + int(10 * s), text="LIGHT 100%", fill="#69f0ae", font=("Arial", max(6, int(7 * s)), "bold"))

        # 5. Status Text
        pct = int(self.current_value * 100)
        status_txt = f"{pct}% SOUL ESSENCE"
        status_color = "#ff5252" if pct <= 25 else ("#ffeb3b" if pct < 75 else "#00e5ff")
        self.create_text(cx, int(90 * s), text=status_txt, fill=status_color, font=("Arial", max(8, int(9 * s)), "bold"))

        # Tip
        hint = "Win to advance • 21 surges"
        self.create_text(cx, int(112 * s), text=hint, fill="#cfd8dc", font=("Arial", max(6, int(7 * s)), "italic"))

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=8, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2, y1,
                  x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2,
                  x2-radius, y2, x2-radius, y2, x1+radius, y2, x1, y2,
                  x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def _is_animation_enabled(self) -> bool:
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except Exception:
            return False

    def _cancel_timer(self):
        if self._anim_timer_id:
            try:
                self.after_cancel(self._anim_timer_id)
            except Exception:
                pass
            self._anim_timer_id = None


# ============================================================================
# Parameterized Typography & HUD Constants
# ============================================================================
HUD_OUTCOME_FONT_FAMILY = "Georgia"
HUD_OUTCOME_FONT_SIZE = 14
HUD_OUTCOME_FONT_WEIGHT = "bold"

HUD_LORE_FONT_FAMILY = "Georgia"
HUD_LORE_FONT_SIZE = 11
HUD_LORE_FONT_SLANT = "italic"
HUD_DEFAULT_WRAPLENGTH = 600


class TableAnnouncementHUD(tkinter.Frame):
    """
    Two-tiered Table Announcement HUD displayed prominently on the table felt.
    Eliminates text truncation via parameterized typography, dynamic wraplength,
    and visual hierarchy separating the core round outcome from secondary/lore messages.
    """

    def __init__(
        self,
        master,
        outcome_family: str = HUD_OUTCOME_FONT_FAMILY,
        outcome_size: int = HUD_OUTCOME_FONT_SIZE,
        outcome_weight: str = HUD_OUTCOME_FONT_WEIGHT,
        lore_family: str = HUD_LORE_FONT_FAMILY,
        lore_size: int = HUD_LORE_FONT_SIZE,
        lore_slant: str = HUD_LORE_FONT_SLANT,
        wraplength: int = HUD_DEFAULT_WRAPLENGTH,
        background: str = PANEL_BACKGROUND_COLOR,
        **kwargs
    ):
        super().__init__(master, background=background, **kwargs)
        self.outcome_font_family = outcome_family
        self.outcome_font_size = outcome_size
        self.outcome_font_weight = outcome_weight
        self.lore_font_family = lore_family
        self.lore_font_size = lore_size
        self.lore_font_slant = lore_slant
        self.wraplength = wraplength
        self.current_raw_message = ""
        self._dismiss_timer_id: Optional[str] = None

        # Outer felt badge with subtle gold border
        self.badge = tkinter.Frame(
            self, background="#07200e", highlightthickness=2,
            highlightbackground="#d4af37", relief="ridge", borderwidth=1, padx=22, pady=8, cursor="hand2"
        )
        self.badge.pack(anchor="center")

        # Tier 1: Outcome Label
        self.outcome_label = tkinter.Label(
            self.badge,
            text="",
            font=(self.outcome_font_family, self.outcome_font_size, self.outcome_font_weight),
            background="#07200e",
            fg="#f5f5f5",
            justify="center",
            cursor="hand2",
            wraplength=self.wraplength
        )
        self.outcome_label.pack(side="top", fill="x", expand=True)

        # Tier 2: Thematic Lore / Status Label
        self.lore_label = tkinter.Label(
            self.badge,
            text="",
            font=(self.lore_font_family, self.lore_font_size, self.lore_font_slant),
            background="#07200e",
            fg="#ffb74d",
            justify="center",
            cursor="hand2",
            wraplength=self.wraplength
        )
        # Hidden by default until lore text is present
        self.lore_label.pack_forget()

        # Click-to-dismiss bindings across dialog elements
        for w in (self, self.badge, self.outcome_label, self.lore_label):
            w.bind("<Button-1>", lambda e: self.dismiss())

    def dismiss(self):
        """Dismisses the floating dialog overlay immediately."""
        if self._dismiss_timer_id:
            try:
                self.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
            self._dismiss_timer_id = None
        if self.winfo_manager() == "place":
            self.place_forget()

    def set_message(self, full_text: str):
        """
        Parses incoming result string. If delimited by ' | ', cleanly separates
        primary outcome (Tier 1) from lore / status narrative (Tier 2).
        Automatically unmaps when empty, and manifests as a floating in-table overlay dialog when active.
        """
        if self._dismiss_timer_id:
            try:
                self.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
            self._dismiss_timer_id = None

        self.current_raw_message = full_text or ""
        text = self.current_raw_message.strip()
        if not text:
            self.outcome_label.configure(text="")
            self.lore_label.configure(text="")
            self.lore_label.pack_forget()
            if self.winfo_manager() == "place":
                self.place_forget()
            return

        # Check for lore delimiter
        if " | " in text:
            parts = text.split(" | ", 1)
            outcome_text = parts[0].strip()
            lore_text = parts[1].strip()
        else:
            outcome_text = text
            lore_text = ""

        self.outcome_label.configure(text=outcome_text)
        self._update_outcome_color(outcome_text)
        if lore_text:
            self.lore_label.configure(text=lore_text)
            if not self.lore_label.winfo_manager():
                self.lore_label.pack(side="top", pady=(3, 0), fill="x", expand=True)
        else:
            self.lore_label.configure(text="")
            self.lore_label.pack_forget()

        # Float in center of parent table felt as an overlay dialog card
        if not self.winfo_manager() or self.winfo_manager() == "place":
            self.place(relx=0.5, rely=0.5, anchor="center")
            self.lift()

        # Automatically dismiss transient announcements after 2.5s
        tl = text.lower()
        if "relic" in tl or "equipped" in tl or "blessing" in tl or "achievement" in tl:
            self._dismiss_timer_id = self.after(2500, self.dismiss)

    @property
    def is_lore_visible(self) -> bool:
        return bool(self.lore_label.winfo_manager() == "pack" and self.lore_label.cget("text"))

    def _update_outcome_color(self, outcome_text: str):
        t = outcome_text.lower()
        if "dealer wins" in t or "bust" in t or "lose" in t or "lost" in t or "damnation" in t:
            fg = "#ff5252"  # Crisp Red
            border = "#ff1744"
        elif "blackjack" in t:
            fg = "#ffd700"  # Gold
            border = "#ffd700"
        elif "win" in t or "won" in t:
            fg = "#69f0ae"  # Vibrant Green
            border = "#00e676"
        elif "push" in t or "tie" in t or "draw" in t:
            fg = "#ffeb3b"  # Amber / Gold
            border = "#ffeb3b"
        else:
            fg = "#f5f5f5"  # Clean White
            border = "#80cbc4"
        self.outcome_label.configure(fg=fg)
        if hasattr(self, "badge"):
            self.badge.configure(highlightbackground=border)

    def set_typography(
        self,
        outcome_family: str | None = None,
        outcome_size: int | None = None,
        outcome_weight: str | None = None,
        lore_family: str | None = None,
        lore_size: int | None = None,
        lore_slant: str | None = None,
        wraplength: int | None = None,
    ):
        """Allows hot-swapping font parameters and wraplength dynamically."""
        if outcome_family is not None:
            self.outcome_font_family = outcome_family
        if outcome_size is not None:
            self.outcome_font_size = outcome_size
        if outcome_weight is not None:
            self.outcome_font_weight = outcome_weight
        if lore_family is not None:
            self.lore_font_family = lore_family
        if lore_size is not None:
            self.lore_font_size = lore_size
        if lore_slant is not None:
            self.lore_font_slant = lore_slant
        if wraplength is not None:
            self.wraplength = wraplength

        self.outcome_label.configure(
            font=(self.outcome_font_family, self.outcome_font_size, self.outcome_font_weight),
            wraplength=self.wraplength
        )
        self.lore_label.configure(
            font=(self.lore_font_family, self.lore_font_size, self.lore_font_slant),
            wraplength=self.wraplength
        )

    def set_scale(self, scale: float):
        """Scales outcome/lore typography and wraplength proportionally."""
        self.scale = scale
        self.set_typography(
            outcome_size=int(14 * scale),
            lore_size=int(11 * scale),
            wraplength=int(600 * scale),
        )
        if hasattr(self, "badge"):
            self.badge.configure(padx=int(22 * scale), pady=int(8 * scale))

    def set_theme_color(self, bg_color: str, border_color: str | None = None):
        """Cascades table felt background color to announcement HUD and badge."""
        self.configure(background=bg_color)
        if hasattr(self, "badge"):
            if border_color:
                border = border_color
            else:
                border = "#3a151b" if bg_color.lower() in ("#0d0204", "#140508", "#0e0306") else "#1b2a1b"
            self.badge.configure(background=bg_color, highlightbackground=border)
        if hasattr(self, "outcome_label"):
            self.outcome_label.configure(background=bg_color)
        if hasattr(self, "lore_label"):
            self.lore_label.configure(background=bg_color)


class HauntedAltarCanvas(tkinter.Canvas):
    """
    Unified 2.5D Haunted Altar rendering:
    - 5 materializing candles with radial warm light pools and snuffed smoke wisps.
    - Up to 5 rising 2.5D isometric gravestones with dynamic directional shadows cast away from lit candles.
    - Kinetic particle animations:
      - Graves erupting out of table felt with fissure cracks and flying dirt particles.
      - Candles poofing into existence with expanding smoke puff particles and ignition flare sparks.
    - Strict non-blocking Tkinter animation timers with lifecycle cancellation safety.
    """

    def __init__(
        self,
        master,
        assets: dict[str, tkinter.PhotoImage] | None = None,
        width: int = 260,
        height: int = 135,
        background: str = PANEL_BACKGROUND_COLOR,
        **kwargs
    ):
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.scale = 1.0
        self.canvas_width = width
        self.canvas_height = height
        self.assets = assets or {}

        # 5 Candle positions along top row (y = 28)
        self.candle_y = 28
        self.candle_x_positions = [26 + i * 52 for i in range(5)]

        # Gravestone positions along bottom row (y = 80)
        self.gravestone_y = 80
        self.gravestone_x_positions = [36, 83, 130, 177, 224]

        # Altar state
        self.candles_remaining = 5
        self.candles_visible = False
        self.gravestones_count = 0
        self.gravestones_visible = False

        # Animation states & timer tracking
        self.is_animating_eruption = False
        self.is_animating_poof = False
        self._anim_timer_ids: list[str] = []

        # Eruption animation parameters
        self._eruption_stone_index = 0
        self._eruption_frame = 0
        self._eruption_total_frames = 8
        self._eruption_y_offset = 0.0
        self._eruption_on_complete = None
        self._debris_particles: list[dict] = []

        # Poof animation parameters
        self._poof_frame = 0
        self._poof_total_frames = 10
        self._poof_on_complete = None
        self._smoke_particles: list[dict] = []
        self._spark_particles: list[dict] = []
        # Felt texture synchronization tracking
        self._felt_source_img = None
        self._felt_coords = None
        self._felt_slice_img = None
        self._felt_slice_photo = None
        self._felt_theme = None

        self.bind("<Map>", lambda e: self._ensure_felt_sync())
        self._draw_altar()

    def _ensure_felt_sync(self):
        """Automatically resolves the active TableFeltCanvas and crops matching felt slice."""
        parent = getattr(self, "master", None)
        while parent is not None and not isinstance(parent, TableFeltCanvas) and hasattr(parent, "master"):
            parent = parent.master
        if parent is not None and isinstance(parent, TableFeltCanvas):
            if (
                getattr(self, "_felt_slice_photo", None) is not None
                and getattr(self, "_felt_theme", None) == parent.current_theme
                and getattr(self, "_felt_slice_img", None) is not None
                and self._felt_slice_img.size == (self.canvas_width, self.canvas_height)
            ):
                return
            self._felt_theme = parent.current_theme
            try:
                cx = self.winfo_x()
                cy = self.winfo_y()
                p_curr = getattr(self, "master", None)
                while p_curr is not None and p_curr is not parent and hasattr(p_curr, "master"):
                    cx += p_curr.winfo_x()
                    cy += p_curr.winfo_y()
                    p_curr = p_curr.master
                w = max(10, self.canvas_width)
                h = max(10, self.canvas_height)
                slice_img = parent.get_felt_slice(cx, cy, w, h)
                if slice_img:
                    self._felt_slice_img = slice_img
                    self._felt_slice_photo = ImageTk.PhotoImage(slice_img, master=self)
                    if not self.find_withtag("felt_bg"):
                        self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
                    else:
                        self.itemconfigure("felt_bg", image=self._felt_slice_photo)
                    self.tag_lower("felt_bg")
            except Exception:
                pass

    def set_scale(self, scale: float, assets: dict[str, tkinter.PhotoImage] | None = None):
        """Scales canvas dimensions and re-projects candle/stone coordinates proportionally."""
        self.scale = scale
        if assets is not None:
            self.assets = assets
        self.canvas_width = int(260 * scale)
        self.canvas_height = int(135 * scale)
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.candle_y = int(28 * scale)
        self.candle_x_positions = [int((26 + i * 52) * scale) for i in range(5)]
        self.gravestone_y = int(80 * scale)
        self.gravestone_x_positions = [int(x * scale) for x in [36, 83, 130, 177, 224]]
        self._felt_slice_photo = None
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        else:
            self._ensure_felt_sync()
        self._draw_altar()

    def sync_felt_background(self, felt_img: Any, rel_x: int, rel_y: int):
        """Crops and synchronizes the underlying table felt texture into this canvas for seamless alpha integration."""
        if not PIL_AVAILABLE or Image is None or ImageTk is None:
            return
        if not felt_img or not hasattr(felt_img, "width"):
            return
        self._felt_source_img = felt_img
        self._felt_coords = (rel_x, rel_y)
        parent = getattr(self, "master", None)
        while parent is not None and not isinstance(parent, TableFeltCanvas) and hasattr(parent, "master"):
            parent = parent.master
        if parent is not None and isinstance(parent, TableFeltCanvas):
            self._felt_theme = parent.current_theme
        try:
            w = self.canvas_width
            h = self.canvas_height
            bg_col = str(self["background"])
            bg_rgb = hex_to_rgb(bg_col) if bg_col.startswith("#") else (20, 32, 24)

            # Clamp crop window so it is fully contained within the parent felt image
            if felt_img.width >= w:
                crop_x1 = max(0, min(rel_x, felt_img.width - w))
            else:
                crop_x1 = 0
            if felt_img.height >= h:
                crop_y1 = max(0, min(rel_y, felt_img.height - h))
            else:
                crop_y1 = 0

            crop_x2 = min(felt_img.width, crop_x1 + w)
            crop_y2 = min(felt_img.height, crop_y1 + h)

            slice_img = Image.new("RGB", (w, h), bg_rgb)
            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                cropped = felt_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                slice_img.paste(cropped, (0, 0))

            self._felt_slice_img = slice_img
            self._felt_slice_photo = ImageTk.PhotoImage(slice_img, master=self)
            if not self.find_withtag("felt_bg"):
                self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
            else:
                self.itemconfigure("felt_bg", image=self._felt_slice_photo)
            self.tag_lower("felt_bg")
        except Exception:
            pass

    def set_candle_state(self, candles_remaining: int, visible: bool = True):
        """Sets remaining lit candles (0 to 5) and redraws altar."""
        self.candles_remaining = max(0, min(5, candles_remaining))
        self.candles_visible = visible
        self._ensure_felt_sync()
        self._draw_altar()

    def set_gravestone_state(self, count: int, visible: bool = True):
        """Sets visible gravestones count (0 to 5) and redraws altar."""
        self.gravestones_count = max(0, min(5, count))
        self.gravestones_visible = visible
        self._ensure_felt_sync()
        self._draw_altar()

    def get_lit_candle_indices(self) -> list[int]:
        """Returns indices of candles that are currently lit."""
        if not self.candles_visible:
            return []
        return list(range(self.candles_remaining))

    def calculate_light_centroid(self) -> float:
        """Calculates average X position of all currently lit candles."""
        lit = self.get_lit_candle_indices()
        if not lit:
            return 130.0  # Center default
        total_x = sum(self.candle_x_positions[i] for i in lit)
        return total_x / len(lit)

    def calculate_shadow_offset_dx(self, stone_x: float, centroid: float) -> float:
        """Calculates directional X offset for drop shadow based on light centroid."""
        if not self.candles_visible or self.candles_remaining == 0:
            return 0.0
        # Shadow tilts away from light source
        return 0.45 * (stone_x - centroid)

    def animate_candle_poof(self, candle_indices: list[int] | None = None, on_complete=None):
        """Triggers smoke puff and ignition spark burst when candles manifest."""
        self.cancel_animations()
        self.is_animating_poof = True
        self._poof_frame = 0
        self._poof_total_frames = 10
        self._poof_on_complete = on_complete
        self.candles_visible = True

        targets = candle_indices if candle_indices is not None else list(range(5))
        self._smoke_particles = []
        self._spark_particles = []

        for ci in targets:
            cx = self.candle_x_positions[ci]
            cy = self.candle_y
            # 12 expanding smoke particles per candle
            for _ in range(12):
                angle = random.uniform(0, 2 * math.pi)
                spd = random.uniform(0.6, 2.2)
                self._smoke_particles.append({
                    "x": cx + math.cos(angle) * 3,
                    "y": cy + math.sin(angle) * 3,
                    "vx": math.cos(angle) * spd,
                    "vy": math.sin(angle) * spd - 0.4,
                    "radius": random.uniform(3.0, 5.0),
                    "max_radius": random.uniform(11.0, 16.0),
                    "color": random.choice(["#f5f5f5", "#e0e0e0", "#bdbdbd", "#9e9e9e", "#757575"])
                })
            # Core ignition spark
            self._spark_particles.append({
                "x": cx,
                "y": cy - 12,
                "radius": 2.0,
                "max_radius": 8.0,
                "color": "#fff59d"
            })

        self._step_poof()

    def _step_poof(self):
        if not self.is_animating_poof:
            return
        t = (self._poof_frame + 1) / self._poof_total_frames

        # Update smoke particles
        for p in self._smoke_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["radius"] += (p["max_radius"] - p["radius"]) * 0.22

        # Update sparks (grow then shrink)
        for s in self._spark_particles:
            if t < 0.35:
                s["radius"] = 2.0 + (s["max_radius"] - 2.0) * (t / 0.35)
            else:
                s["radius"] = max(0.0, s["max_radius"] * (1.0 - (t - 0.35) / 0.65))

        self._draw_altar()
        self._poof_frame += 1

        if self._poof_frame < self._poof_total_frames:
            tid = self.after(30, self._step_poof)
            self._anim_timer_ids.append(tid)
        else:
            self._smoke_particles.clear()
            self._spark_particles.clear()
            self.is_animating_poof = False
            self._draw_altar()
            if self._poof_on_complete:
                cb = self._poof_on_complete
                self._poof_on_complete = None
                cb()

    def animate_grave_eruption(self, stone_index: int, on_complete=None):
        """Animates a gravestone bursting up through the table felt."""
        self.cancel_animations()
        self.is_animating_eruption = True
        self._eruption_stone_index = max(0, min(4, stone_index))
        self._eruption_frame = 0
        self._eruption_total_frames = 8
        self._eruption_on_complete = on_complete
        self.gravestones_visible = True
        self.gravestones_count = max(self.gravestones_count, self._eruption_stone_index + 1)

        gx = self.gravestone_x_positions[self._eruption_stone_index]
        gy = self.gravestone_y

        self._debris_particles = []
        for _ in range(14):
            vx = random.uniform(-2.5, 2.5)
            vy = random.uniform(-6.5, -3.5)
            self._debris_particles.append({
                "x": gx + random.uniform(-10, 10),
                "y": gy + 20,
                "vx": vx,
                "vy": vy,
                "size": random.randint(2, 4),
                "color": random.choice(["#3e2723", "#271b12", "#4e342e", "#1b120c"])
            })

        self._step_eruption()

    def _step_eruption(self):
        if not self.is_animating_eruption:
            return
        t = (self._eruption_frame + 1) / self._eruption_total_frames
        # Smooth ease-out rise from under ground (offset from 36 down to 0)
        self._eruption_y_offset = 36.0 * (1.0 - math.sqrt(t))

        # Gravity on debris
        for p in self._debris_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.85

        self._draw_altar()
        self._eruption_frame += 1

        if self._eruption_frame < self._eruption_total_frames:
            tid = self.after(35, self._step_eruption)
            self._anim_timer_ids.append(tid)
        else:
            self._eruption_y_offset = 0.0
            self._debris_particles.clear()
            self.is_animating_eruption = False
            self._draw_altar()
            if self._eruption_on_complete:
                cb = self._eruption_on_complete
                self._eruption_on_complete = None
                cb()

    def cancel_animations(self):
        """Immediately stops all animation timers and resets transient visual effects."""
        for tid in self._anim_timer_ids:
            try:
                self.after_cancel(tid)
            except Exception:
                pass
        self._anim_timer_ids.clear()
        self.is_animating_eruption = False
        self.is_animating_poof = False
        self._eruption_y_offset = 0.0
        self._debris_particles.clear()
        self._smoke_particles.clear()
        self._spark_particles.clear()

    def set_theme_color(self, bg_color: str, is_hell_table: bool = False):
        """Updates the altar canvas background color and refreshes lighting."""
        self._is_hell_table = is_hell_table
        self.configure(background=bg_color)
        self._felt_theme = None
        self._felt_slice_photo = None
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        else:
            self._ensure_felt_sync()
        self._draw_altar()

    def destroy(self):
        self.cancel_animations()
        super().destroy()

    def _draw_altar(self):
        self.delete("all")
        # 0. Underlying felt slice background
        if getattr(self, "_felt_slice_photo", None) is None:
            self._ensure_felt_sync()
        if getattr(self, "_felt_slice_photo", None):
            self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
        bg_col = str(self["background"])
        bg_lower = bg_col.lower()
        is_hell = getattr(self, "_is_hell_table", False) or (bg_lower in ("#0d0204", "#140508", "#2a0d12", "#0e0306", "#16050a"))
        is_creep = getattr(self, "_felt_theme", None) == "creep" or (bg_lower in ("#142018", "#021206", "#031908", "#03230b", "#042c0e"))
        is_dark_bg = is_hell or is_creep

        # Calculate lighting centroid
        centroid = self.calculate_light_centroid()

        # 1. Candles & Glow Pools
        if self.candles_visible:
            lit_img = self.assets.get("candle_lit")
            unlit_img = self.assets.get("candle_unlit")

            for i, cx in enumerate(self.candle_x_positions):
                cy = self.candle_y
                is_lit = i < self.candles_remaining

                if is_lit:
                    # Luminous warm candlelight glow pool on the table felt
                    if is_hell:
                        glow_outer = "#3d1008"
                        glow_mid = "#7a200d"
                        glow_inner = "#ff8f00"
                    elif is_creep:
                        glow_outer = "#102a16"
                        glow_mid = "#28441c"
                        glow_inner = "#c4a32a"
                    else:
                        # Radiant golden-olive wash that illuminates green felt
                        glow_outer = "#1a5e1a"
                        glow_mid = "#3b7a22"
                        glow_inner = "#d4b830"

                    s = getattr(self, "scale", 1.0)
                    self.create_oval(
                        cx - int(24 * s), cy - int(6 * s), cx + int(24 * s), cy + int(30 * s),
                        fill=glow_outer, outline="", tags="glow"
                    )
                    self.create_oval(
                        cx - int(16 * s), cy, cx + int(16 * s), cy + int(24 * s),
                        fill=glow_mid, outline="", tags="glow"
                    )
                    self.create_oval(
                        cx - int(8 * s), cy + int(6 * s), cx + int(8 * s), cy + int(18 * s),
                        fill=glow_inner, outline="", tags="glow"
                    )
                    if lit_img:
                        self.create_image(cx, cy, image=lit_img, anchor="center", tags="candle")
                    else:
                        # Fallback vector lit candle
                        self.create_rectangle(cx - 5, cy - 8, cx + 5, cy + 14, fill="#e8d8a7", outline="#8a733f", tags="candle")
                        self.create_oval(cx - 4, cy - 16, cx + 4, cy - 7, fill="#ff9100", outline="", tags="candle")
                        self.create_oval(cx - 2, cy - 14, cx + 2, cy - 8, fill="#fff59d", outline="", tags="candle")
                else:
                    if unlit_img:
                        self.create_image(cx, cy, image=unlit_img, anchor="center", tags="candle")
                    else:
                        # Fallback vector unlit candle
                        self.create_rectangle(cx - 5, cy - 8, cx + 5, cy + 14, fill="#8a8068", outline="#4a4030", tags="candle")
                        self.create_line(cx, cy - 8, cx, cy - 12, fill="#111111", width=2, tags="candle")

        # 2. Gravestones with Directional Drop Shadows
        if self.gravestones_visible and self.gravestones_count > 0:
            grave_img = self.assets.get("gravestone")
            num_stones = min(self.gravestones_count, 5)

            for k in range(num_stones):
                gx = self.gravestone_x_positions[k]
                gy = self.gravestone_y
                y_disp = self._eruption_y_offset if (self.is_animating_eruption and k == self._eruption_stone_index) else 0.0

                # Directional shadow calculation
                s = getattr(self, "scale", 1.0)
                dx = self.calculate_shadow_offset_dx(gx, centroid)
                dy = (6 + (5 - self.candles_remaining)) * s

                ground_y = gy + int(20 * s)
                w_half = int(18 * s)
                # Draw directional drop shadow
                shadow_pts = [
                    gx - w_half + dx * 0.15, ground_y,
                    gx + w_half + dx * 0.15, ground_y,
                    gx + w_half + dx, ground_y + dy,
                    gx - w_half + dx, ground_y + dy
                ]
                shadow_col = "#150204" if is_dark_bg else "#071207"
                self.create_polygon(shadow_pts, fill=shadow_col, outline="", smooth=True, tags="shadow")

                # Fissure cracks if erupting
                if self.is_animating_eruption and k == self._eruption_stone_index:
                    fissure_col = "#1a0408" if is_dark_bg else "#040b04"
                    self.create_line(gx, ground_y, gx - 16, ground_y + 4, fill=fissure_col, width=2, tags="fissure")
                    self.create_line(gx, ground_y, gx + 18, ground_y + 3, fill=fissure_col, width=2, tags="fissure")
                    self.create_line(gx - 6, ground_y + 2, gx - 20, ground_y + 8, fill=fissure_col, width=1, tags="fissure")
                    self.create_line(gx + 8, ground_y + 2, gx + 22, ground_y + 7, fill=fissure_col, width=1, tags="fissure")

                # Gravestone sprite
                if grave_img:
                    self.create_image(gx, gy + y_disp, image=grave_img, anchor="center", tags="grave")
                else:
                    # Fallback vector gravestone
                    self.create_polygon(
                        [gx - 16, gy + y_disp + 18, gx - 16, gy + y_disp - 8,
                         gx, gy + y_disp - 20, gx + 16, gy + y_disp - 8, gx + 16, gy + y_disp + 18],
                        fill="#606770", outline="#30353b", tags="grave"
                    )

        # 3. Particle Layers: Debris & Smoke
        # Dirt Debris particles
        for p in self._debris_particles:
            s = p["size"]
            self.create_oval(p["x"] - s, p["y"] - s, p["x"] + s, p["y"] + s, fill=p["color"], outline="", tags="debris")

        # Smoke Puff particles
        for sm in self._smoke_particles:
            r = sm["radius"]
            self.create_oval(sm["x"] - r, sm["y"] - r, sm["x"] + r, sm["y"] + r, fill=sm["color"], outline="", tags="smoke")

        # Ignition Sparks
        for sp in self._spark_particles:
            r = sp["radius"]
            if r > 0.5:
                self.create_oval(sp["x"] - r, sp["y"] - r, sp["x"] + r, sp["y"] + r, fill=sp["color"], outline="", tags="spark")


class DealerStageCanvas(tkinter.Canvas):
    """
    Panoramic Horizon Stage Canvas.
    Spans 100% of the table width above the horizon rail, rendering:
    - High-definition panoramic atmospheric backdrops (Casino, Creep, Hell, Celestial, Crypt).
    - Centered living dealer actor composite and stage accessories.
    - Top-right wardrobe coat-hanger button for launching Wardrobe & Casino Records.
    - Dynamic resize handling and High-DPI in-memory scaling.
    """

    DEFAULT_HEIGHT = 220

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Optional[Any] = None,
        width: int = 1000,
        height: int = 220,
        on_hanger_click: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            background="#0a0a0a",
            highlightthickness=0,
            borderwidth=0,
            **kwargs
        )
        self.app = app
        self.current_theme = "casino"
        self.scale_factor = 1.0
        self.on_hanger_click = on_hanger_click
        self.canvas_width = width
        self.canvas_height = height

        self.backdrop_images: dict[str, Any] = {}
        self.hanger_photo: Optional[Any] = None
        self.hanger_photo_2x: Optional[Any] = None
        self._active_backdrop_photo: Optional[Any] = None
        self._dealer_photo: Optional[Any] = None
        self.particles: list[dict] = []

        self._load_backdrop_assets()
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_canvas_click)
        self.bind("<Motion>", self._on_mouse_move)

        self._redraw_stage()

    def set_dealer_image(self, photo: Optional[Any]):
        """Sets and updates the dealer sprite rendered directly on the stage canvas."""
        self._dealer_photo = photo
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        if self.find_withtag("dealer_sprite"):
            if photo:
                self.itemconfigure("dealer_sprite", image=photo)
                self.coords("dealer_sprite", w // 2, h)
                self.lift("dealer_sprite")
                if self.find_withtag("dialogue_win"):
                    self.lift("dialogue_win")
                if self.find_withtag("hanger_btn"):
                    self.lift("hanger_btn")
            else:
                self.delete("dealer_sprite")
        elif photo:
            self.create_image(w // 2, h, image=photo, anchor="s", tags="dealer_sprite")
            if self.find_withtag("dialogue_win"):
                self.lift("dialogue_win")
            if self.find_withtag("hanger_btn"):
                self.lift("hanger_btn")

    def _load_backdrop_assets(self):
        backdrops_dir = HAUNTED_ASSETS_DIR / "backdrops"
        theme_files = {
            "casino": ("backdrop_casino.png", "backdrop_casino_2x.png"),
            "creep": ("backdrop_creep.png", "backdrop_creep_2x.png"),
            "hell": ("backdrop_hell.png", "backdrop_hell_2x.png"),
            "celestial": ("backdrop_celestial.png", "backdrop_celestial_2x.png"),
            "crypt": ("backdrop_crypt.png", "backdrop_crypt_2x.png"),
        }

        for theme, (f1x, f2x) in theme_files.items():
            p1x = backdrops_dir / f1x
            p2x = backdrops_dir / f2x
            if p1x.exists() and PIL_AVAILABLE:
                try:
                    img1x = Image.open(p1x)
                    photo1x = ImageTk.PhotoImage(img1x)
                    img2x = Image.open(p2x) if p2x.exists() else img1x
                    photo2x = ImageTk.PhotoImage(img2x) if p2x.exists() else photo1x
                    self.backdrop_images[theme] = {
                        1.0: (img1x, photo1x),
                        2.0: (img2x, photo2x),
                    }
                except Exception:
                    pass

        # Hanger icon
        h1x = HAUNTED_ASSETS_DIR / "hanger_icon.png"
        h2x = HAUNTED_ASSETS_DIR / "hanger_icon_2x.png"
        if h1x.exists() and PIL_AVAILABLE:
            try:
                self.hanger_photo = ImageTk.PhotoImage(Image.open(h1x), master=self)
                self.hanger_photo_2x = ImageTk.PhotoImage(Image.open(h2x), master=self) if h2x.exists() else self.hanger_photo
            except Exception:
                pass

    def _on_resize(self, event):
        if event.width > 10 and (event.width != self.canvas_width or event.height != self.canvas_height):
            self.canvas_width = event.width
            self.canvas_height = event.height
            self._redraw_stage()

    def _redraw_stage(self):
        self.delete("backdrop")
        self.delete("hanger_btn")

        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)

        # 1. Draw scaled backdrop
        theme_data = self.backdrop_images.get(self.current_theme)
        if theme_data and PIL_AVAILABLE:
            active_scale = 2.0 if self.scale_factor > 1.5 else 1.0
            raw_img, _ = theme_data.get(active_scale, (None, None))
            if raw_img:
                try:
                    resample_mode = getattr(Image, "Resampling", Image).BILINEAR
                    resized = raw_img.resize((w, h), resample_mode)
                    self._active_backdrop_photo = ImageTk.PhotoImage(resized, master=self)
                    self.create_image(0, 0, image=self._active_backdrop_photo, anchor="nw", tags="backdrop")
                except Exception:
                    pass

        # 2. Draw Hanger button at top right
        hanger_img = self.hanger_photo_2x if self.scale_factor > 1.5 else self.hanger_photo
        if hanger_img:
            hx = w - int(24 * self.scale_factor)
            hy = int(18 * self.scale_factor)
            self.create_image(hx, hy, image=hanger_img, anchor="center", tags="hanger_btn")

        # 3. Position and update Centered Dealer Sprite directly on canvas
        if getattr(self, "_dealer_photo", None):
            if not self.find_withtag("dealer_sprite"):
                self.create_image(w // 2, h, image=self._dealer_photo, anchor="s", tags="dealer_sprite")
            else:
                self.coords("dealer_sprite", w // 2, h)
                self.itemconfigure("dealer_sprite", anchor="s")

        # 4. Position Dialogue Window to the left of the dealer
        if self.find_withtag("dialogue_win"):
            bubble_x = w // 2 - int(105 * self.scale_factor)
            bubble_y = h - int(16 * self.scale_factor)
            self.coords("dialogue_win", bubble_x, bubble_y)
            self.itemconfigure("dialogue_win", anchor="se")
            self.lift("dialogue_win")

        if self.find_withtag("hanger_btn"):
            self.lift("hanger_btn")

        # Legacy header_row support
        if self.find_withtag("header_row"):
            self.coords("header_row", w // 2, h - 2)
            self.itemconfigure("header_row", anchor="s")

    def _is_over_hanger(self, x: int, y: int) -> bool:
        s = self.scale_factor
        w = max(10, self.canvas_width)
        hx = w - int(24 * s)
        hy = int(18 * s)
        pad = int(16 * s)
        return (hx - pad <= x <= hx + pad) and (hy - pad <= y <= hy + pad)

    def _on_canvas_click(self, event):
        if self._is_over_hanger(event.x, event.y):
            if self.on_hanger_click:
                self.on_hanger_click()

    def _on_mouse_move(self, event):
        if self._is_over_hanger(event.x, event.y):
            self.configure(cursor="hand2")
        else:
            self.configure(cursor="")

    def spawn_ambient_particles(self, count: int = 1):
        """Spawns ambient floating motes/embers/dust on the stage canvas matching active theme."""
        s = self.scale_factor
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        theme = self.current_theme

        for _ in range(count):
            if theme == "hell":
                # Rising glowing embers and charcoal ash
                px = random.randint(w // 2 - int(130 * s), w // 2 + int(130 * s))
                py = h - random.randint(10, 70)
                vx = random.uniform(-0.8, 0.8)
                vy = random.uniform(-2.5, -0.9)
                r = random.uniform(1.5, 3.5)
                color = random.choice(["#ff3d00", "#ff9100", "#ffab00", "#424242"])
                life = random.randint(25, 45)
                ptype = "ember"
            elif theme == "celestial":
                # Descending golden starlight and ethereal azure motes
                px = random.randint(w // 2 - int(140 * s), w // 2 + int(140 * s))
                py = random.randint(10, 60)
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(0.6, 1.8)
                r = random.uniform(1.5, 3.0)
                color = random.choice(["#ffd700", "#ffffff", "#80d8ff"])
                life = random.randint(30, 50)
                ptype = "starlight"
            elif theme == "crypt":
                # Pale bone dust and violet sparks
                px = random.randint(w // 2 - int(120 * s), w // 2 + int(120 * s))
                py = h - random.randint(10, 60)
                vx = random.uniform(-0.6, 0.6)
                vy = random.uniform(-1.5, -0.5)
                r = random.uniform(1.2, 2.8)
                color = random.choice(["#b388ff", "#b0bec5", "#e0e0e0", "#80cbc4"])
                life = random.randint(25, 40)
                ptype = "bonedust"
            else:
                # Classic casino / creep: warm chandelier dust motes
                px = random.randint(int(40 * s), w - int(40 * s))
                py = random.randint(20, h - 20)
                vx = random.uniform(-0.3, 0.3)
                vy = random.uniform(-0.5, -0.1)
                r = random.uniform(1.0, 2.2)
                color = random.choice(["#ffe082", "#ffd54f", "#cfd8dc"])
                life = random.randint(30, 55)
                ptype = "dust"

            self.particles.append({
                "x": px,
                "y": py,
                "vx": vx,
                "vy": vy,
                "radius": r,
                "color": color,
                "life": life,
                "max_life": life,
                "type": ptype,
            })

    def spawn_sweat_particle(self):
        """Spawns an anxious sweat drop particle when dealer busts or suffers shock."""
        s = self.scale_factor
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        self.particles.append({
            "x": w // 2 + int(36 * s),
            "y": h - int(120 * s),
            "vx": random.uniform(0.1, 0.3),
            "vy": 2.8,
            "radius": 2.5,
            "color": "#80d8ff",
            "life": 18,
            "max_life": 18,
            "type": "sweat",
        })

    def update_particles(self):
        """Advances and renders all active stage canvas particles."""
        if not self.particles:
            return
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)

        surviving = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] > 0 and 0 <= p["x"] <= w and 0 <= p["y"] <= h + 10:
                surviving.append(p)

        self.particles = surviving

        # Redraw particle canvas items
        self.delete("stage_particle")
        for p in self.particles:
            x, y, r = p["x"], p["y"], p["radius"]
            self.create_oval(
                x - r, y - r, x + r, y + r,
                fill=p["color"], outline="", tags="stage_particle"
            )

        if self.find_withtag("dealer_sprite"):
            self.lift("dealer_sprite")
        if self.find_withtag("dialogue_win"):
            self.lift("dialogue_win")
        if self.find_withtag("hanger_btn"):
            self.lift("hanger_btn")

    def clear_particles(self):
        """Removes all active stage particles from memory and canvas."""
        self.particles.clear()
        self.delete("stage_particle")

    def set_theme(self, theme: str):
        if self.current_theme != theme:
            self.current_theme = theme
            self.clear_particles()
            self._redraw_stage()

    def set_scale(self, scale_factor: float):
        self.scale_factor = scale_factor
        self.canvas_height = int(self.DEFAULT_HEIGHT * (1.0 if scale_factor <= 1.0 else 1.30))
        self.configure(height=self.canvas_height)
        self._redraw_stage()



class TableFeltCanvas(tkinter.Canvas):
    """
    Panoramic Casino Table Felt Canvas.
    Renders an authentic tactile woven baize felt texture with:
    - High-frequency micro-fiber woolen noise and subtle cross-twill weave lines.
    - Soft overhead table lamp ambient radial lighting vignette.
    - Authentic casino table markings in muted antique gold:
      * Dealer/insurance boundary arc
      * 'BLACKJACK PAYS 3 TO 2'
      * 'Dealer must stand on 17 and must draw to 16'
      * 'INSURANCE PAYS 2 TO 1'
    - Phase-specific felt color palettes (Classic, Creep, Hell, Celestial).
    - Preserves container compatibility: grid(), rowconfigure(), columnconfigure(), ['background'].
    """

    THEME_COLORS = {
        "casino": {
            "base": (7, 76, 26),
            "bg_hex": PANEL_BACKGROUND_COLOR,
            "gold": (212, 175, 55),
            "rules_fg": (240, 240, 240),
        },
        "creep": {
            "base": (20, 32, 24),
            "bg_hex": "#142018",
            "gold": (180, 150, 190),
            "rules_fg": (200, 190, 210),
        },
        "hell": {
            "base": (42, 13, 18),
            "bg_hex": "#2a0d12",
            "gold": (255, 90, 50),
            "rules_fg": (255, 180, 120),
        },
        "celestial": {
            "base": (12, 35, 56),
            "bg_hex": "#0c2338",
            "gold": (0, 229, 255),
            "rules_fg": (220, 245, 255),
        },
    }

    def __init__(self, parent: tkinter.Misc, background: str = PANEL_BACKGROUND_COLOR, **kwargs):
        hl = kwargs.pop("highlightthickness", 0)
        bw = kwargs.pop("borderwidth", 0)
        rel = kwargs.pop("relief", "flat")
        self.padx = kwargs.pop("padx", 0)
        self.pady = kwargs.pop("pady", 0)
        super().__init__(
            parent,
            background=background,
            highlightthickness=hl,
            borderwidth=bw,
            relief=rel,
            **kwargs
        )
        self.current_theme = "casino"
        self.scale_factor = 1.0
        self.canvas_width = 900
        self.canvas_height = 274
        self._bg_hex = background
        self._felt_photo: Optional[Any] = None
        self._felt_cache: dict[tuple[str, int, int, float], Any] = {}

        self.bind("<Configure>", self._on_resize)
        self._redraw_felt()

    def _on_resize(self, event):
        if event.width > 20 and (event.width != self.canvas_width or event.height != self.canvas_height):
            self.canvas_width = event.width
            self.canvas_height = event.height
            self._redraw_felt()

    def set_theme(self, theme: str):
        t = (theme or "casino").lower()
        if t not in self.THEME_COLORS:
            t = "casino"
        if self.current_theme != t:
            self.current_theme = t
            theme_cfg = self.THEME_COLORS.get(t, self.THEME_COLORS["casino"])
            self._bg_hex = theme_cfg["bg_hex"]
            self.configure(background=self._bg_hex)
            self._redraw_felt()

    def set_scale(self, scale_factor: float):
        if self.scale_factor != scale_factor:
            self.scale_factor = scale_factor
            self._redraw_felt()

    def _generate_felt_image(self, w: int, h: int) -> Optional[Any]:
        if not PIL_AVAILABLE:
            return None
        import numpy as np

        cfg = self.THEME_COLORS.get(self.current_theme, self.THEME_COLORS["casino"])
        base_rgb = np.array(cfg["base"], dtype=np.float32)

        rng = np.random.RandomState(42)
        noise = rng.normal(0, 5.0, (h, w, 1))

        y_idx, x_idx = np.indices((h, w))
        weave = ((x_idx + y_idx) % 4 == 0).astype(np.float32)[:, :, np.newaxis] * 2.5

        cx, cy = w / 2.0, h * 0.45
        dist = np.sqrt(((x_idx - cx) / (w * 0.6)) ** 2 + ((y_idx - cy) / (h * 0.7)) ** 2)
        vignette = np.clip(1.06 - 0.18 * dist, 0.85, 1.10)[:, :, np.newaxis]

        felt_arr = (base_rgb + noise + weave) * vignette
        felt_arr = np.clip(felt_arr, 0, 255).astype(np.uint8)

        felt_img = Image.fromarray(felt_arr, mode="RGB")
        draw = ImageDraw.Draw(felt_img)

        # Muted antique gold rules arc and middle ribbon markings
        s = self.scale_factor
        gold = cfg["gold"]

        # Position middle ribbon safely between dealer hand (top) and player hand (bottom)
        ribbon_y = int(h * 0.36)
        rx = int(w * 0.38)
        ry = int(h * 0.28)
        draw.arc([cx - rx, ribbon_y - int(10 * s), cx + rx, ribbon_y + ry], start=22, end=158, fill=gold, width=max(1, int(2 * s)))

        try:
            from PIL import ImageFont
            font_large = ImageFont.truetype("arial.ttf", int(12 * (1.0 if s <= 1.0 else 1.4)))
            font_small = ImageFont.truetype("arial.ttf", int(9 * (1.0 if s <= 1.0 else 1.3)))
        except Exception:
            font_large = font_small = None

        if font_large and font_small:
            draw.text((cx, ribbon_y + int(10 * s)), "BLACKJACK PAYS 3 TO 2", fill=gold, font=font_large, anchor="mm")
            draw.text((cx, ribbon_y + int(24 * s)), "Dealer must stand on 17 and must draw to 16", fill=cfg["rules_fg"], font=font_small, anchor="mm")
            draw.text((cx, ribbon_y + int(36 * s)), "INSURANCE PAYS 2 TO 1", fill=gold, font=font_small, anchor="mm")

        return felt_img

    def _redraw_felt(self):
        w = max(20, self.canvas_width)
        h = max(20, self.canvas_height)
        key = (self.current_theme, w, h, self.scale_factor)

        if key in self._felt_cache:
            self._felt_img, self._felt_photo = self._felt_cache[key]
        elif PIL_AVAILABLE:
            try:
                img = self._generate_felt_image(w, h)
                if img:
                    self._felt_img = img
                    self._felt_photo = ImageTk.PhotoImage(img, master=self)
                    self._felt_cache[key] = (self._felt_img, self._felt_photo)
            except Exception:
                self._felt_img = None
                self._felt_photo = None
        else:
            self._felt_img = None
            self._felt_photo = None

        if self._felt_photo:
            if not self.find_withtag("felt_bg"):
                self.create_image(0, 0, image=self._felt_photo, anchor="nw", tags="felt_bg")
            else:
                self.itemconfigure("felt_bg", image=self._felt_photo)
            self.tag_lower("felt_bg")
            try:
                self.sync_children_felt()
            except Exception:
                pass

    def get_felt_slice(self, x: int, y: int, width: int, height: int) -> Optional[Any]:
        """Returns safe PIL Image slice of active felt texture with no black borders."""
        if not getattr(self, "_felt_img", None) or not PIL_AVAILABLE:
            return None
        try:
            cfg = self.THEME_COLORS.get(self.current_theme, self.THEME_COLORS["casino"])
            slice_img = Image.new("RGB", (width, height), cfg["base"])
            if self._felt_img.width >= width:
                src_x1 = max(0, min(x, self._felt_img.width - width))
            else:
                src_x1 = 0
            if self._felt_img.height >= height:
                src_y1 = max(0, min(y, self._felt_img.height - height))
            else:
                src_y1 = 0
            src_x2 = min(self._felt_img.width, src_x1 + width)
            src_y2 = min(self._felt_img.height, src_y1 + height)
            if src_x2 > src_x1 and src_y2 > src_y1:
                cropped = self._felt_img.crop((src_x1, src_y1, src_x2, src_y2))
                slice_img.paste(cropped, (0, 0))
            return slice_img
        except Exception:
            return None

    def sync_children_felt(self):
        """Synchronizes felt texture slices across child canvases and visualizers (both direct and nested)."""
        if not getattr(self, "_felt_img", None):
            return
        try:
            self.update_idletasks()
        except Exception:
            pass

        def _sync(parent, base_x: int, base_y: int):
            for child in parent.winfo_children():
                cx = base_x + child.winfo_x()
                cy = base_y + child.winfo_y()
                if hasattr(child, "sync_felt_background") and bool(child.winfo_manager()):
                    try:
                        child.sync_felt_background(self._felt_img, cx, cy)
                    except Exception:
                        pass
                if child.winfo_children():
                    _sync(child, cx, cy)

        _sync(self, 0, 0)


class AssetScaler:
    """
    Manages in-memory dynamic image scaling using Pillow (PIL) for cards,
    table accessories, character avatars, and relics across 1x and 2x display modes.
    Zero disk duplication.
    """
    def __init__(self, master=None):
        self.master = master
        self._source_pil_cache: dict[Path, Image.Image] = {}
        self._tk_cache: dict[tuple[Path, int, int], ImageTk.PhotoImage] = {}

    def get_scaled_image(self, file_path: Path, width: int, height: int):
        """Returns a scaled PhotoImage (or ImageTk.PhotoImage) resized in memory."""
        file_path = Path(file_path)
        if not PIL_AVAILABLE or Image is None or ImageTk is None:
            kw = {"master": self.master} if self.master is not None else {}
            try:
                return tkinter.PhotoImage(file=str(file_path), **kw)
            except Exception:
                return None

        key = (file_path, width, height)
        if key in self._tk_cache:
            return self._tk_cache[key]

        if file_path not in self._source_pil_cache:
            if not file_path.exists():
                return None
            try:
                self._source_pil_cache[file_path] = Image.open(file_path).convert("RGBA")
            except Exception:
                return None

        src = self._source_pil_cache[file_path]
        resized = src.resize((width, height), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized, master=self.master)
        self._tk_cache[key] = tk_img
        return tk_img


def load_images(card_images, master=None, scale: float = 1.0, asset_scaler: AssetScaler | None = None):
    """
    Loads all 52 card PNG images into a list of Card instances.
    Supports in-memory scaling when scale != 1.0 or asset_scaler is provided.
    Preserved for backward compatibility with test suites and external callers.
    """
    suits = ["heart", "club", "diamond", "spade"]
    face_cards = ["jack", "queen", "king"]
    use_scaler = (asset_scaler is not None) or (scale != 1.0)
    scaler = (asset_scaler or AssetScaler(master=master)) if use_scaler else None
    w = int(CARD_WIDTH * scale)
    h = int(CARD_HEIGHT * scale)

    for suit in suits:
        # Number cards 1 to 10 (1 = Ace)
        for card in range(1, 11):
            name = ASSETS_DIR / f"{card}_{suit}.png"
            if scaler:
                image = scaler.get_scaled_image(name, w, h)
            else:
                image = tkinter.PhotoImage(file=str(name), master=master)
            rank = "ace" if card == 1 else str(card)
            card_images.append(Card(value=card, image=image, rank=rank, suit=suit))

        # Face cards (Jack, Queen, King all value 10)
        for card in face_cards:
            name = ASSETS_DIR / f"{card}_{suit}.png"
            if scaler:
                image = scaler.get_scaled_image(name, w, h)
            else:
                image = tkinter.PhotoImage(file=str(name), master=master)
            card_images.append(Card(value=10, image=image, rank=card, suit=suit))


def build_shoe(all_cards, num_decks: int = DEFAULT_DECK_COUNT) -> list:
    """
    Creates and shuffles a multi-deck shoe from template Card instances.

    Args:
        all_cards: List of 52 unique Card instances.
        num_decks: Number of standard 52-card decks in the shoe.

    Returns:
        list[Card]: Shuffled list containing (52 * num_decks) cards.
    """
    shoe = []
    for _ in range(num_decks):
        shoe.extend(all_cards)
    random.shuffle(shoe)
    return shoe


# ============================================================================
# Audio System: Pygame Mixer Sound Manager
# ============================================================================

class SoundManager:
    """
    Manages sound effects playback using pygame.mixer for .ogg audio assets.

    Features:
    - Low-latency asynchronous audio playback via pygame.mixer buffer configuration.
    - Polyphonic 16-channel mixing so cards and chips sound concurrently without clipping.
    - Natural acoustic variety through randomized sample pools (e.g. 8 card slides, 6 chip sounds).
    - Graceful headless degradation: silently no-ops if pygame is missing or audio hardware is absent.
    - Master volume control and mute toggling with Tkinter reactive updates.
    """

    def __init__(self, audio_dir: Path = AUDIO_DIR, enabled: bool = True, volume: float = DEFAULT_SOUND_VOLUME):
        self.audio_dir = Path(audio_dir)
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.is_available = False
        self.sounds = {
            "card_slide": [],
            "card_place": [],
            "card_shove": [],
            "card_shuffle": [],
            "card_fan": [],
            "cards_pack": [],
            "chip_lay": [],
            "chips_collide": [],
            "chips_stack": [],
            "chips_handle": [],
        }

        self._init_mixer()
        if self.is_available:
            self._load_sounds()

    def _init_mixer(self):
        """Initializes pygame.mixer safely with low latency and 16 channels."""
        if not PYGAME_AVAILABLE or pygame_mixer is None:
            self.is_available = False
            return
        try:
            if not pygame_mixer.get_init():
                pygame_mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame_mixer.set_num_channels(16)
            self.is_available = True
        except Exception:
            # Handles headless CI environments or missing sound card
            self.is_available = False

    def _load_sounds(self):
        """Pre-loads all .ogg sound files from audio_dir into categorized pools."""
        if not self.audio_dir.exists() or pygame_mixer is None:
            return

        patterns = {
            "card_slide": "card-slide-*.ogg",
            "card_place": "card-place-*.ogg",
            "card_shove": "card-shove-*.ogg",
            "card_shuffle": "card-shuffle.ogg",
            "card_fan": "card-fan-*.ogg",
            "cards_pack": "cards-pack-*.ogg",
            "chip_lay": "chip-lay-*.ogg",
            "chips_collide": "chips-collide-*.ogg",
            "chips_stack": "chips-stack-*.ogg",
            "chips_handle": "chips-handle-*.ogg",
        }

        for category, pattern in patterns.items():
            for file_path in sorted(self.audio_dir.glob(pattern)):
                try:
                    sound = pygame_mixer.Sound(str(file_path))
                    sound.set_volume(self.volume)
                    self.sounds[category].append(sound)
                except Exception:
                    pass

    def set_volume(self, volume: float):
        """Sets master volume (0.0 to 1.0) and updates all loaded sounds."""
        self.volume = max(0.0, min(1.0, volume))
        for sound_list in self.sounds.values():
            for sound in sound_list:
                try:
                    sound.set_volume(self.volume)
                except Exception:
                    pass

    def toggle_mute(self) -> bool:
        """Toggles mute state. Returns True if sound is now enabled, False if muted."""
        self.enabled = not self.enabled
        return self.enabled

    @property
    def is_muted(self) -> bool:
        """Returns whether sound output is currently muted or unavailable."""
        return (not self.enabled) or (not self.is_available)

    def stop_all(self):
        """Stops all currently playing audio channels."""
        if self.is_available and pygame_mixer is not None:
            try:
                pygame_mixer.stop()
            except Exception:
                pass

    def play(self, category: str):
        """Plays a random sound from the specified category if sound is enabled."""
        if not self.enabled or not self.is_available:
            return
        sound_pool = self.sounds.get(category)
        if not sound_pool:
            return
        try:
            sound = random.choice(sound_pool)
            sound.play()
        except Exception:
            pass

    # Convenience domain event playback methods
    def play_card_deal(self):
        """Plays random card slide sound when dealing cards."""
        self.play("card_slide")

    def play_card_place(self):
        """Plays crisp card placement sound (e.g. flipping hole card or split)."""
        self.play("card_place")

    def play_card_shuffle(self):
        """Plays riffle shuffle sound when resetting or cutting shoe."""
        self.play("card_shuffle")

    def play_card_fan(self):
        """Plays card fanning sound."""
        self.play("card_fan")

    def play_chip_add(self):
        """Plays chip click or lay sound when placing/increasing bets."""
        cat = random.choice(["chip_lay", "chips_collide"])
        self.play(cat)

    def play_chip_stack(self):
        """Plays heavy chip stack sound for all-in or large bets."""
        self.play("chips_stack")

    def play_chip_clear(self):
        """Plays dealer chip handling sound when clearing bets."""
        self.play("chips_handle")

    def play_surrender(self):
        """Plays card shove sound when player surrenders their hand."""
        self.play("card_shove")

    def play_payout(self):
        """Plays dealer chip slide / handle sound on player win."""
        self.play("chips_handle")

    def play_loss(self):
        """Plays dealer scooping chips sound on player loss/bust."""
        self.play("chips_handle")

    def play_push(self):
        """Plays soft chip tap on push."""
        self.play("chip_lay")

    def play_haunted_sound(self, sound_name: str):
        """Plays a one-shot haunted audio effect from audio/haunted/."""
        if not self.enabled or not self.is_available:
            return
        sound_path = HAUNTED_AUDIO_DIR / f"{sound_name}.ogg"
        if not sound_path.exists():
            sound_path = HAUNTED_AUDIO_DIR / f"{sound_name}.wav"
        if sound_path.exists() and pygame_mixer is not None:
            try:
                sound = pygame_mixer.Sound(str(sound_path))
                sound.set_volume(self.volume)
                sound.play()
            except Exception:
                pass


# ============================================================================
# Keyboard & Input Prompts Asset Loader
# ============================================================================

class KeyboardIconLoader:
    """
    Loads, scales, and caches Kenney keyboard & mouse prompt PNG sprites.
    Provides graceful fallback to text-based badges if assets are missing.
    """

    def __init__(self, icons_dir: Path | None = None, master: tkinter.Misc | None = None):
        self.icons_dir = icons_dir or OVERLAY_ICONS_DIR
        self.master = master
        self._cache: dict[tuple[str, int], tkinter.PhotoImage] = {}

    def get_icon(self, icon_name: str, scale_div: int = 2) -> tkinter.PhotoImage | None:
        """
        Retrieves a cached PhotoImage for the given icon name and scale divisor.
        Example: get_icon('keyboard_space', 2) loads keyboard_space.png subsampled by (2, 2) -> 32x32.
        """
        key = (icon_name, scale_div)
        if key in self._cache:
            return self._cache[key]

        candidates = []
        if self.icons_dir:
            candidates.append(self.icons_dir / f"{icon_name}.png")
            if not icon_name.startswith("keyboard_") and not icon_name.startswith("mouse_"):
                candidates.append(self.icons_dir / f"keyboard_{icon_name}.png")

        # Local development fallback to raw Kenney pack if curated dir not yet populated
        raw_fallback = BASE_DIR / "Keyboard & Mouse" / "Default"
        candidates.append(raw_fallback / f"{icon_name}.png")
        if not icon_name.startswith("keyboard_") and not icon_name.startswith("mouse_"):
            candidates.append(raw_fallback / f"keyboard_{icon_name}.png")

        kw = {"master": self.master} if self.master is not None else {}
        for path in candidates:
            if path.exists():
                try:
                    img = tkinter.PhotoImage(file=str(path), **kw)
                    if scale_div > 1:
                        img = img.subsample(scale_div, scale_div)
                    self._cache[key] = img
                    return img
                except Exception:
                    continue

        return None



class StoryDialogueDialog(tkinter.Toplevel):
    """
    Atmospheric narrative dialogue modal featuring custom speaker portraits,
    dark gothic or celestial styling, and responsive proceed controls.
    """

    def __init__(
        self,
        parent,
        title: str,
        speaker: str,
        portrait_img: tkinter.PhotoImage | None,
        text_content: str,
        button_text: str = "Proceed...",
        on_close=None,
        is_celestial: bool = False,
    ):
        super().__init__(parent)
        self.on_close_cb = on_close
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)

        bg_col = "#041421" if is_celestial else "#0d0204"
        border_col = "#00e5ff" if is_celestial else "#8b0000"
        header_col = "#80cbc4" if is_celestial else "#ff5252"
        btn_bg = "#00695c" if is_celestial else "#b71c1c"
        btn_active = "#00897b" if is_celestial else "#d32f2f"

        self.configure(background=bg_col, padx=14, pady=14)

        # Center relative to parent
        w, h = 540, 240
        try:
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
        except Exception:
            self.geometry(f"{w}x{h}")

        frame = tkinter.Frame(
            self, background=bg_col, relief="ridge", borderwidth=2,
            highlightbackground=border_col, highlightthickness=1
        )
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Portrait container
        self.portrait_img = portrait_img
        if portrait_img:
            port_lbl = tkinter.Label(frame, image=portrait_img, background=bg_col)
            port_lbl.image = portrait_img
            port_lbl.pack(side="left", padx=12, pady=10)
            self.portrait_label = port_lbl

        # Content container
        content_box = tkinter.Frame(frame, background=bg_col)
        content_box.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=10)

        tkinter.Label(
            content_box, text=speaker, font=("Arial", 11, "bold"),
            fg=header_col, background=bg_col
        ).pack(anchor="w")

        tkinter.Label(
            content_box, text=text_content, font=("Arial", 9),
            fg="#eceff1", background=bg_col, justify="left", wraplength=380
        ).pack(anchor="w", pady=(6, 12))

        btn = tkinter.Button(
            content_box, text=button_text, font=("Arial", 10, "bold"),
            background=btn_bg, foreground="#ffffff", activebackground=btn_active,
            activeforeground="#ffffff", relief="flat", borderwidth=0,
            highlightthickness=0, cursor="hand2", padx=16, pady=6,
            takefocus=False, command=self._dismiss
        )
        btn.pack(anchor="e")

        self.bind("<Return>", lambda e: self._dismiss())
        self.bind("<space>", lambda e: self._dismiss())
        self.bind("<Escape>", lambda e: self._dismiss())
        self.protocol("WM_DELETE_WINDOW", self._dismiss)
        self.focus_set()

    def _dismiss(self):
        cb = self.on_close_cb
        try:
            self.destroy()
        except Exception:
            pass
        if cb:
            cb()


class AngelicDraftDialog(tkinter.Toplevel):
    """
    Balatro-style Roguelike celestial blessing draft dialog.
    Presents 3 relic cards side-by-side with icon, title, tagline, description, and draft buttons.
    """

    def __init__(self, parent, choices: list[Blessing], relic_icons: dict, on_select):
        super().__init__(parent)
        self.on_select = on_select
        self.title("✦ CELESTIAL BLESSINGS - DRAFT A SACRED RELIC ✦")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#03101c", padx=16, pady=14)

        w, h = 680, 360
        try:
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
        except Exception:
            self.geometry(f"{w}x{h}")

        tkinter.Label(
            self, text="✦ CHOOSE YOUR CELESTIAL BLESSING ✦",
            font=("Arial", 13, "bold"), fg="#ffd700", background="#03101c"
        ).pack(pady=(0, 2))

        tkinter.Label(
            self, text="The Angel intervenes! Draft one divine relic to aid in the struggle for your soul.",
            font=("Arial", 9, "italic"), fg="#80cbc4", background="#03101c"
        ).pack(pady=(0, 12))

        cards_frame = tkinter.Frame(self, background="#03101c")
        cards_frame.pack(fill="both", expand=True)

        for blessing in choices:
            details = BLESSING_REGISTRY[blessing]
            card_f = tkinter.Frame(
                cards_frame, background="#051f38", relief="ridge", borderwidth=2,
                highlightbackground="#00e5ff", highlightthickness=1, padx=10, pady=8
            )
            card_f.pack(side="left", fill="both", expand=True, padx=5)

            icon = relic_icons.get(blessing.value)
            if icon:
                ilbl = tkinter.Label(card_f, image=icon, background="#051f38")
                ilbl.image = icon
                ilbl.pack(pady=(2, 4))

            tkinter.Label(
                card_f, text=details.title, font=("Arial", 10, "bold"),
                fg="#ffd700", background="#051f38"
            ).pack()

            tkinter.Label(
                card_f, text=details.tagline, font=("Arial", 8, "italic"),
                fg="#80cbc4", background="#051f38"
            ).pack(pady=(0, 4))

            tkinter.Label(
                card_f, text=details.description, font=("Arial", 8),
                fg="#eceff1", background="#051f38", justify="center", wraplength=170
            ).pack(fill="both", expand=True, pady=(0, 8))

            btn = tkinter.Button(
                card_f, text="Equip Relic", font=("Arial", 9, "bold"),
                background="#00838f", foreground="#ffffff", activebackground="#00acc1",
                activeforeground="#ffffff", relief="raised", borderwidth=2, cursor="hand2",
                command=lambda b=blessing: self._pick(b)
            )
            btn.pack(side="bottom", pady=4)

        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Must draft a blessing to proceed

    def _pick(self, blessing: Blessing):
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_select:
            self.on_select(blessing)



class SettingsDialog(tkinter.Toplevel):
    """
    Casino Settings & Save Data Management Dialog.
    Provides options for sound, scaling, dealer stage, and persistent save data
    management, including an irreversible 'Clear Save File' reset with safety confirmation.
    """

    def __init__(self, parent: tkinter.Tk, app: BlackjackApp):
        super().__init__(parent)
        self.app = app
        self.title("⚙ Settings & Casino Records")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background=PANEL_BACKGROUND_COLOR, padx=16, pady=14)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        dialog_w, dialog_h = 460, 440
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            x = max(0, root_x + (root_w - dialog_w) // 2)
            y = max(0, root_y + (root_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self.status_msg_var = tkinter.StringVar(value="All casino records active.")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.focus_set()

    def _build_ui(self):
        # Header title
        header = tkinter.Label(
            self, text="⚙ CASINO SETTINGS & RECORDS",
            font=("Arial", 12, "bold"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        )
        header.pack(pady=(0, 10))

        # Audio & Display Controls Frame
        ctrl_frame = tkinter.LabelFrame(
            self, text=" Table Preferences ", font=("Arial", 10, "bold"),
            fg="#80cbc4", background=PANEL_BACKGROUND_COLOR, padx=10, pady=8
        )
        ctrl_frame.pack(fill="x", pady=(0, 12))

        # Sound button
        self.sound_btn = tkinter.Button(
            ctrl_frame, textvariable=self.app.sound_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_sound
        )
        self.sound_btn.pack(side="left", padx=(0, 6), expand=True, fill="x")

        # Scale button
        self.scale_btn = tkinter.Button(
            ctrl_frame, textvariable=self.app.scale_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app.toggle_scale_mode
        )
        self.scale_btn.pack(side="left", padx=6, expand=True, fill="x")

        # Dealer view button
        self.dealer_btn = tkinter.Button(
            ctrl_frame, textvariable=self.app.dealer_view_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_dealer_view
        )
        self.dealer_btn.pack(side="left", padx=6, expand=True, fill="x")

        # Dealer wardrobe button
        self.wardrobe_btn = tkinter.Button(
            ctrl_frame, text="🎩 Wardrobe", font=("Arial", 9, "bold"),
            background="#1b5e20", fg="white", activebackground="#2e7d32", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._open_wardrobe_dialog
        )
        self.wardrobe_btn.pack(side="left", padx=(6, 0), expand=True, fill="x")

        # Save Data Management Frame
        save_frame = tkinter.LabelFrame(
            self, text=" Save Data & Hall of Fame Records ", font=("Arial", 10, "bold"),
            fg="#ffd700", background=PANEL_BACKGROUND_COLOR, padx=12, pady=10
        )
        save_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Stats labels
        self.stats_frame = tkinter.Frame(save_frame, background=PANEL_BACKGROUND_COLOR)
        self.stats_frame.pack(fill="x", pady=(0, 8))

        self.lbl_peak = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_peak.pack(fill="x", pady=1)

        self.lbl_hands = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_hands.pack(fill="x", pady=1)

        self.lbl_exorcist = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_exorcist.pack(fill="x", pady=1)

        self._refresh_stats_display()

        # Status feedback label
        lbl_status = tkinter.Label(
            save_frame, textvariable=self.status_msg_var, font=("Arial", 9, "italic"),
            fg="#ffeb3b", background=PANEL_BACKGROUND_COLOR
        )
        lbl_status.pack(pady=(4, 8))

        # Clear Save File Button
        self.clear_save_btn = tkinter.Button(
            save_frame, text="🗑 Clear Save File (Reset to Blank Slate)",
            font=("Arial", 10, "bold"), background="#b71c1c", fg="#ffffff",
            activebackground="#d32f2f", activeforeground="#ffffff",
            relief="raised", borderwidth=2, cursor="hand2",
            command=self._on_click_clear_save
        )
        self.clear_save_btn.pack(fill="x", pady=4)

        # Close Button
        close_btn = tkinter.Button(
            self, text="Close", font=("Arial", 10, "bold"),
            background="#37474f", fg="white", activebackground="#455a64",
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_close
        )
        close_btn.pack(pady=(4, 0))

    def _refresh_stats_display(self):
        """Refreshes the high scores and achievement badges displayed in the dialog."""
        data = self.app.save_manager.data
        self.lbl_peak.configure(
            text=f"• All-Time Peak Bankroll: ${data.highscores.peak_bankroll:,}"
        )
        self.lbl_hands.configure(
            text=f"• Hands Won / Played: {data.highscores.total_hands_won:,} / {data.highscores.total_hands_played:,}  (Blackjacks: {data.highscores.total_blackjacks:,})"
        )
        exorcist_str = "✦ UNLOCKED (Cursed Stakes Active)" if data.achievements.exorcist else "Locked (Survive Hell's Table)"
        self.lbl_exorcist.configure(
            text=f"• Exorcist Title: {exorcist_str}"
        )

    def _ask_confirm_clear_save(self) -> bool:
        """
        Displays an explicit confirmation modal warning that clearing the save file is irreversible.
        Isolated for headless unit testing.
        """
        import tkinter.messagebox as msgbox
        return msgbox.askyesno(
            title="⚠️ Confirm Save Reset",
            message=(
                "WARNING: This action is irreversible!\n\n"
                "Clearing your save file will permanently reset all high scores, "
                "achievements (including Exorcist status), statistics, and "
                "unlocked dealer costumes back to an initial blank slate.\n\n"
                "Are you sure you want to clear your save file?"
            ),
            icon="warning",
            default="no",
            parent=self,
        )

    def _on_click_clear_save(self):
        """Handles clear save file button click with confirmation."""
        confirmed = self._ask_confirm_clear_save()
        if not confirmed:
            return

        self.app.clear_player_save_data()
        self._refresh_stats_display()
        self.status_msg_var.set("✓ Save file reset to initial blank slate.")

    def _on_close(self):
        self.app._close_settings_dialog()


# ============================================================================
# GUI Application: Object-Oriented Presentation Layer
# ============================================================================


class BlackjackApp:
    """
    Encapsulates the Blackjack GUI, card state, and game lifecycle.
    Eliminates all global variables by storing state in instance attributes.
    Supports hand splitting with independent turn progression and outcome resolution.
    """

    def __init__(self, root: tkinter.Tk, sound_enabled: bool = True, save_path: Optional[Path] = None, chips_mode: Optional[bool] = None):
        self.root = root
        self.root.title(f"Blackjack v{__version__}")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.configure(background=TABLE_BACKGROUND_COLOR, padx=10, pady=10)

        # Window icon configuration (supports .png via PhotoImage and .ico fallback)
        self._icon_photo = None
        icon_png = ASSETS_EXTRA_DIR / "icon.png"
        icon_ico = ASSETS_EXTRA_DIR / "icon.ico"
        try:
            if icon_png.exists():
                self._icon_photo = tkinter.PhotoImage(file=str(icon_png))
                self.root.iconphoto(False, self._icon_photo)
            elif icon_ico.exists():
                self.root.iconbitmap(default=str(icon_ico))
        except Exception:
            pass  # Graceful fallback if window icon fails on headless or unsupported display

        # Allow responsive centering/scaling on window resize
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        # Async timer management & graceful window destruction
        self._dealer_timer_id = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Destroy>", lambda e: self._on_close() if e.widget == self.root else None, add="+")

        # Audio Manager & Reactive Sound State
        self.sound_manager = SoundManager(audio_dir=AUDIO_DIR, enabled=sound_enabled)
        self.sound_status_var = tkinter.StringVar(
            value="🔊 Sound: ON" if self.sound_manager.enabled else "🔇 Sound: OFF"
        )

        # Shoe and Multi-Deck Configuration
        self.deck_count = DEFAULT_DECK_COUNT
        self.shoe_needs_reshuffle = False
        self.shoe_info_var = tkinter.StringVar(value="")

        # Game State Collections
        self.deck = []
        self.all_cards = []
        self.player_hands = [[]]
        self.active_hand_index = 0
        self.dealer_hand = []

        # Dealer Hole Card Tracking (Face-down card mechanics)
        self.dealer_hole_card = None        # Card of the hidden card
        self.dealer_hole_widget = None      # Tkinter Label displaying the card back
        self.back_image = None              # PhotoImage for cards/back.png

        # Reactive GUI Variables
        self.dealer_wins_var = tkinter.IntVar(value=0)
        self.player_wins_var = tkinter.IntVar(value=0)
        self.ties_var = tkinter.IntVar(value=0)
        self.dealer_score_var = tkinter.StringVar(value="0")
        self.player_score_var = tkinter.StringVar(value="0")
        self.result_var = tkinter.StringVar(value="")

        # Haunted Halloween & Hell's Table Controller
        self.haunted = HauntedManager()
        # Player Save Data & Hall of Fame Controller
        if save_path is None and "unittest" in sys.modules:
            save_path = Path(tempfile.mkdtemp()) / "isolated_test_save.json"
        self.save_manager = SaveManager(save_path=save_path)
        self._settings_dialog = None
        if self.save_manager.data.achievements.exorcist:
            self.haunted.unlocked_cursed_stakes = True
            self.haunted.unlocked_exorcist = True

        # Chips and Wagering State (Defaults to enabled / saved preference)
        initial_chips_mode = self.save_manager.data.chips_mode if chips_mode is None else chips_mode
        self.chips_mode_var = tkinter.BooleanVar(value=initial_chips_mode)
        self.bankroll_var = tkinter.IntVar(value=STARTING_BANKROLL)
        self.current_bet_var = tkinter.IntVar(value=0)
        self.hand_bets = [0]
        self.is_betting_phase = False
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.is_insurance_phase = False
        self.chip_buttons = []
        self._last_was_double = False
        self._ambient_timer_id = None
        self._anim_frame_toggle = False
        self._active_story_dialog = None
        self.dealer_view_var = tkinter.BooleanVar(value=True)
        self.dealer_view_status_var = tkinter.StringVar(value="👤 Dealer: ON")
        self.dealer_speech_var = tkinter.StringVar(value="")
        self.cursed_stakes_var = tkinter.BooleanVar(value=False)
        self.haunted_assets: dict[str, tkinter.PhotoImage] = {}
        self.card_13: Card | None = None
        self._last_gravestones_risen = 0
        self._candles_manifested = False

        # Scale and Fullscreen Display Mode State
        self.scale_factor: float = 1.0
        self.card_width: int = CARD_WIDTH
        self.card_height: int = CARD_HEIGHT
        self.card_overlap_offset: int = PLAYER_CARD_OVERLAP_OFFSET
        self.is_fullscreen: bool = False
        self.scale_status_var = tkinter.StringVar(value="🔍 2x")
        self.fullscreen_status_var = tkinter.StringVar(value="⛶ Full")
        self.is_hole_card_hidden: bool = False
        self._prev_geometry = None
        self._asset_scaler = None

        # Living Dealer Animation Engine
        self._wardrobe_dialog = None
        self._dealer_idle_timer_id = None
        self._dealer_blink_timer_id = None
        self._dealer_blink_restore_timer_id = None
        self._dealer_blink_timers: list[Any] = []
        self._dealer_gesture_timer_id = None
        self._dealer_mouth_timer_id = None
        self._dealer_speech_anim_timer_id = None
        self._typewriter_timer_id = None
        self._haunted_round_timer_id = None
        self._dealer_anim_step = 0.0
        self._session_blackjacks = 0

        # Load card visual assets
        self._load_assets()

        # Build interface layout
        self._build_ui()

        # Render dealer on stage canvas
        self._update_dealer_avatar()

        # Bind emergency timer cleanup when root is destroyed directly
        try:
            self.root.bind("<Destroy>", self._on_root_destroyed, add="+")
        except Exception:
            pass

        # Start ambient animations loop for haunted elements
        self._start_ambient_animations()

        # Start living dealer idle breathing & autonomous blinking
        self._start_dealer_idle_animation()
        self._schedule_dealer_blink()

        # Start first game
        self.new_game()


    @property
    def player_hand(self):
        """Backwards-compatible access to the currently active player hand."""
        if not self.player_hands:
            return []
        return self.player_hands[self.active_hand_index]

    @player_hand.setter
    def player_hand(self, cards):
        """Backwards-compatible setter for the currently active player hand."""
        if not self.player_hands:
            self.player_hands = [list(cards)]
            self.active_hand_index = 0
        else:
            self.player_hands[self.active_hand_index] = list(cards)

    def _load_assets(self):
        """Loads 52 card face images, card back image, keyboard overlay icons, and haunted assets."""
        self._asset_scaler = AssetScaler(master=self.root)
        w = int(CARD_WIDTH * self.scale_factor)
        h = int(CARD_HEIGHT * self.scale_factor)
        load_images(self.all_cards, master=self.root, scale=self.scale_factor, asset_scaler=self._asset_scaler)
        back_path = ASSETS_DIR / "back.png"
        self.back_image = self._asset_scaler.get_scaled_image(back_path, w, h)
        self.icon_loader = KeyboardIconLoader(OVERLAY_ICONS_DIR, master=self.root)
        self.icon_question_small = self.icon_loader.get_icon("keyboard_question", scale_div=3)
        self._shortcuts_dialog = None

        # Load Haunted PNG Assets safely
        if HAUNTED_ASSETS_DIR.exists():
            for p in HAUNTED_ASSETS_DIR.glob("*.png"):
                stem = p.stem
                if stem.startswith("card_") or stem == "back_haunted" or ("haunted" in stem and any(f in stem for f in ("jack", "queen", "king"))):
                    img_w, img_h = w, h
                elif "avatar" in stem or "dealer" in stem:
                    img_w, img_h = int(96 * self.scale_factor), int(96 * self.scale_factor)
                elif "pumpkin" in stem:
                    img_w, img_h = int(48 * self.scale_factor), int(48 * self.scale_factor)
                elif "gravestone" in stem:
                    img_w, img_h = int(48 * self.scale_factor), int(56 * self.scale_factor)
                elif "candle" in stem:
                    img_w, img_h = int(40 * self.scale_factor), int(40 * self.scale_factor)
                elif "relic" in stem:
                    img_w, img_h = int(48 * self.scale_factor), int(48 * self.scale_factor)
                else:
                    img_w, img_h = int(48 * self.scale_factor), int(48 * self.scale_factor)

                scaled = self._asset_scaler.get_scaled_image(p, img_w, img_h)
                if scaled:
                    self.haunted_assets[stem] = scaled

        if "card_13" in self.haunted_assets:
            self.card_13 = Card(13, self.haunted_assets["card_13"], rank="thirteen", suit="skulls")

    def _build_ui(self):
        """Builds all Tkinter frames, scoreboards, card tables, and action buttons."""
        # Top Scoreboard: Win/Tie counters and status message
        scoreboard_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        scoreboard_frame.grid(row=0, column=0, columnspan=3, pady=(0, 6))

        lbl_dw_t = tkinter.Label(
            scoreboard_frame, text="Dealer Wins: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_dw_t.grid(row=0, column=0)
        lbl_dw_v = tkinter.Label(
            scoreboard_frame, textvariable=self.dealer_wins_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_dw_v.grid(row=0, column=1, padx=(0, 15))

        lbl_pw_t = tkinter.Label(
            scoreboard_frame, text="Player Wins: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_pw_t.grid(row=0, column=2)
        lbl_pw_v = tkinter.Label(
            scoreboard_frame, textvariable=self.player_wins_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_pw_v.grid(row=0, column=3, padx=(0, 15))

        lbl_t_t = tkinter.Label(
            scoreboard_frame, text="Ties: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_t_t.grid(row=0, column=4)
        lbl_t_v = tkinter.Label(
            scoreboard_frame, textvariable=self.ties_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_t_v.grid(row=0, column=5)

        self.stat_labels = [
            (lbl_dw_t, True),
            (lbl_dw_v, False),
            (lbl_pw_t, True),
            (lbl_pw_v, False),
            (lbl_t_t, True),
            (lbl_t_v, False),
        ]

        # Shoe Cards Remaining Display
        self.shoe_label = tkinter.Label(
            scoreboard_frame, textvariable=self.shoe_info_var, font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#80cbc4"
        )
        self.shoe_label.grid(row=0, column=6, padx=(12, 0))

        # Spacer column to push utility buttons to the right
        scoreboard_frame.columnconfigure(7, weight=1)

        # Sound Mute Toggle Button
        self.sound_button = tkinter.Button(
            scoreboard_frame, textvariable=self.sound_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_toggle_sound
        )
        self.sound_button.grid(row=0, column=8, padx=(15, 0))

        # Shortcuts / Help Button
        help_btn_kwargs = {
            "font": ("Arial", 9, "bold"),
            "background": PANEL_BACKGROUND_COLOR,
            "fg": "#ffeb3b",
            "activebackground": TABLE_BACKGROUND_COLOR,
            "activeforeground": "#ffeb3b",
            "relief": "ridge",
            "borderwidth": 1,
            "cursor": "hand2",
            "command": self._toggle_shortcuts_overlay,
        }
        if self.icon_question_small:
            self.help_button = tkinter.Button(
                scoreboard_frame, text=" Help", image=self.icon_question_small, compound="left",
                **help_btn_kwargs
            )
        else:
            self.help_button = tkinter.Button(
                scoreboard_frame, text="[?] Help",
                **help_btn_kwargs
            )
        self.help_button.grid(row=0, column=9, padx=(10, 0))

        # Dealer View Toggle Button (retained as instance for compatibility, unmapped since dealer is permanent)
        self.dealer_view_button = tkinter.Button(
            scoreboard_frame, textvariable=self.dealer_view_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_toggle_dealer_view
        )
        # Omitted from header grid since dealer is always enabled


        # Scale Mode Toggle Button (1x <-> 2x High-DPI in-memory scaling)
        self.scale_button = tkinter.Button(
            scoreboard_frame, textvariable=self.scale_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self.toggle_scale_mode
        )
        self.scale_button.grid(row=0, column=11, padx=(6, 0))

        # Fullscreen Toggle Button (F11)
        self.fullscreen_button = tkinter.Button(
            scoreboard_frame, textvariable=self.fullscreen_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self.toggle_fullscreen
        )
        self.fullscreen_button.grid(row=0, column=12, padx=(6, 0))

        # Settings & Save Management Button
        self.settings_button = tkinter.Button(
            scoreboard_frame, text="⚙ Settings", font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._open_settings_dialog
        )
        self.settings_button.grid(row=0, column=13, padx=(6, 0))

        # Bankroll and Bet summary (visible in Chips Mode)
        self.bankroll_label = tkinter.Label(
            scoreboard_frame, text="Bankroll: $1,000  |  Bet: $0",
            font=("Arial", 11, "bold"), background=TABLE_BACKGROUND_COLOR, fg="#81c784"
        )
        self.bankroll_label.grid(row=1, column=0, columnspan=14, pady=(2, 2))
        if not self.chips_mode_var.get():
            self.bankroll_label.grid_remove()  # Hidden in Casual Mode

        # Status / Result banner (Preserved for backwards compatibility, hidden from crowded top bar)
        self.result_label = tkinter.Label(
            scoreboard_frame, textvariable=self.result_var, font=("Arial", 13, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#ffeb3b"
        )
        self.result_label.grid(row=2, column=0, columnspan=14, pady=(2, 4))
        self.result_label.grid_remove()  # Moved to TableAnnouncementHUD between Dealer & Player hands

        # Tier 1: Dealer Stage Area (Phase 4 Horizon Layout - Above the Horizon Rail)
        self.dealer_stage_frame = tkinter.Frame(
            self.root, background=PANEL_BACKGROUND_COLOR, padx=0, pady=0
        )
        self.dealer_stage_frame.grid(row=1, column=0, sticky="ew", columnspan=3)
        self.dealer_panel = self.dealer_stage_frame

        # Panoramic Dealer Stage Canvas (Full width atmospheric backdrops & stage hanger)
        self.dealer_stage_canvas = DealerStageCanvas(
            self.dealer_stage_frame,
            app=self,
            on_hanger_click=self._on_click_stage_hanger,
        )
        self.dealer_stage_canvas.pack(fill="both", expand=True)

        # Living Dealer Actor Layer Compositor
        init_costume = "julian"
        if hasattr(self, "save_manager") and hasattr(self.save_manager, "data"):
            init_costume = getattr(self.save_manager.data, "equipped_costume", "julian")
        self.dealer_actor = DealerActor(
            master=self.root,
            scale_factor=self.scale_factor,
            initial_character=init_costume,
        )

        # Dealer Actor Frame (Portrait + Theatrical Nameplate + Reactive Speech Dialogue)
        self.dealer_header_row = tkinter.Frame(self.dealer_stage_canvas, background=PANEL_BACKGROUND_COLOR)
        stage_init_h = int(DealerStageCanvas.DEFAULT_HEIGHT * self.scale_factor)
        self.dealer_actor_frame = self.dealer_header_row

        # Flickering Jack-o'-Lantern
        pumpkin_img = self.haunted_assets.get("pumpkin_glow_0")
        self.pumpkin_label = tkinter.Label(
            self.dealer_header_row, image=pumpkin_img, background=PANEL_BACKGROUND_COLOR
        )
        if pumpkin_img:
            self.pumpkin_label.image = pumpkin_img
        self.pumpkin_label.pack(side="left", padx=(0, 6), pady=2)
        self.pumpkin_label.pack_forget()

        # Dealer Avatar Portrait (Retained inside dealer_header_row for legacy tests)
        dealer_img = self.dealer_actor.get_photo_image() or self.haunted_assets.get("dealer_classic")
        self.dealer_avatar_label = tkinter.Label(
            self.dealer_header_row, image=dealer_img, background=PANEL_BACKGROUND_COLOR
        )
        if dealer_img:
            self.dealer_avatar_label.image = dealer_img
            self.dealer_stage_canvas.set_dealer_image(dealer_img)
        self.dealer_avatar_label.pack(side="left", padx=2, pady=2)
        self.dealer_avatar_label.pack_forget()

        # Dealer Dialogue & Actor Info Column (placed directly on stage canvas)
        self.dealer_dialogue_frame = tkinter.Frame(
            self.dealer_stage_canvas, background="#141014", relief="ridge", borderwidth=1,
            highlightthickness=1, highlightbackground="#c8a038", padx=6, pady=4
        )
        bubble_x = 500 - int(105 * self.scale_factor)
        bubble_y = stage_init_h - int(16 * self.scale_factor)
        self.dealer_stage_canvas.create_window(bubble_x, bubble_y, window=self.dealer_dialogue_frame, anchor="se", tags="dialogue_win")

        self.dealer_nameplate_label = tkinter.Label(
            self.dealer_dialogue_frame, text="The Dealer", font=("Arial", 10, "bold"),
            foreground="#ffd700", background="#141014"
        )
        self.dealer_nameplate_label.pack(anchor="w")

        self.dealer_speech_label = tkinter.Label(
            self.dealer_dialogue_frame, textvariable=self.dealer_speech_var,
            font=("Arial", 9, "italic"), fg="#f0f0f0", background="#1c161c",
            relief="flat", borderwidth=0, padx=6, pady=2, wraplength=380, justify="left"
        )
        self.dealer_speech_label.pack(anchor="w", pady=(2, 0))
        self.dealer_speech_label.pack_forget()  # Hidden until speech is set

        # Tier 2: 3D Beveled Horizon Rail (Separates Dealer Stage from Playing Felt)
        self.horizon_rail = tkinter.Frame(
            self.root, height=4, background="#073512", relief="raised", borderwidth=1
        )
        self.horizon_rail.grid(row=2, column=0, columnspan=3, sticky="ew")

        # Tier 3: Main Card Table Area (Below the Horizon Rail)
        card_table_frame = TableFeltCanvas(
            self.root, relief="sunken", borderwidth=2, background=PANEL_BACKGROUND_COLOR, padx=8, pady=3
        )
        card_table_frame.grid(row=3, column=0, sticky="nsew", columnspan=3)
        card_table_frame.columnconfigure(1, weight=1)
        card_table_frame.columnconfigure(2, weight=0)
        card_table_frame.rowconfigure(0, weight=1, minsize=118)
        card_table_frame.rowconfigure(1, weight=1, minsize=118)
        self.scoreboard_frame = scoreboard_frame
        self.card_table_frame = card_table_frame

        # Table Accessories Frame (Haunted Altar: 5 Candles & 5 Rising Gravestones on Table Felt)
        self.accessories_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR, borderwidth=0, highlightthickness=0)
        self.accessories_frame.grid(row=0, column=2, sticky="ne", padx=0, pady=0)

        # Unified 2.5D Haunted Altar Canvas (5 Candles, Directional Shadows, Rising Gravestones)
        self.haunted_altar = HauntedAltarCanvas(
            self.accessories_frame, assets=self.haunted_assets, width=260, height=135,
            background=PANEL_BACKGROUND_COLOR
        )
        self.haunted_altar.pack(side="top", pady=2)
        self.haunted_altar.pack_forget()

        # Legacy frames preserved for backwards compatibility with tests / extensions
        self.candle_bar_frame = tkinter.Frame(self.accessories_frame, background=PANEL_BACKGROUND_COLOR)
        self.candle_labels = []
        self.gravestones_frame = tkinter.Frame(self.accessories_frame, background=PANEL_BACKGROUND_COLOR)
        self.gravestone_labels = []

        # Dealer Section - Casino Plaque Styling
        self.dealer_header_frame = tkinter.Frame(
            card_table_frame, background="#082210", relief="ridge", borderwidth=1,
            highlightthickness=1, highlightbackground="#8a733f", padx=6, pady=3
        )
        self.dealer_header_frame.grid(row=0, column=0, sticky="nw", padx=(4, 6), pady=(4, 0))

        self.dealer_title_label = tkinter.Label(
            self.dealer_header_frame, text="Dealer", font=("Arial", 11, "bold"),
            background="#082210", fg="#d4af37"
        )
        self.dealer_title_label.pack(anchor="w")

        self.dealer_score_label = tkinter.Label(
            self.dealer_header_frame, textvariable=self.dealer_score_var, font=("Arial", 12, "bold"),
            background="#082210", fg="#ffffff"
        )
        self.dealer_score_label.pack(anchor="w", pady=(1, 0))

        self.dealer_cards_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR)
        self.dealer_cards_frame.grid(row=0, column=1, padx=10, pady=1)

        # In-Table Floating Dialog Overlay (unmapped when empty, floats over center when active)
        self.announcement_hud = TableAnnouncementHUD(
            card_table_frame, background=PANEL_BACKGROUND_COLOR
        )
        self.result_var.trace_add("write", lambda *_: self.announcement_hud.set_message(self.result_var.get()))
        self.announcement_hud.set_message(self.result_var.get())

        # Player Section - Casino Plaque Styling
        self.player_header_frame = tkinter.Frame(
            card_table_frame, background="#082210", relief="ridge", borderwidth=1,
            highlightthickness=1, highlightbackground="#8a733f", padx=6, pady=3
        )
        self.player_header_frame.grid(row=1, column=0, sticky="nw", padx=(4, 6), pady=(4, 0))

        self.player_title_label = tkinter.Label(
            self.player_header_frame, text="Player", font=("Arial", 11, "bold"),
            background="#082210", fg="#d4af37"
        )
        self.player_title_label.pack(anchor="w")

        self.player_score_label = tkinter.Label(
            self.player_header_frame, textvariable=self.player_score_var, font=("Arial", 12, "bold"),
            background="#082210", fg="#ffffff"
        )
        self.player_score_label.pack(anchor="w", pady=(1, 0))

        self.player_cards_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR)
        self.player_cards_frame.grid(row=1, column=1, padx=10, pady=1)

        # 2.5D Casino Felt Betting Spot Visualizer (visible in Chips Mode)
        self.chip_visualizer = ChipVisualizer(
            card_table_frame, width=180, height=135, background=PANEL_BACKGROUND_COLOR
        )
        self.chip_visualizer.grid(row=1, column=2, padx=(10, 5), pady=2, sticky="e")
        if not self.chips_mode_var.get():
            self.chip_visualizer.grid_remove()  # Hidden in Casual Mode

        # 2.5D Animated Tug-of-War Soul Meter (visible in Hell's Table Mode)
        self.soul_meter_canvas = SoulMeterCanvas(
            card_table_frame, width=180, height=135, background="#140508"
        )
        self.soul_meter_canvas.grid(row=1, column=2, padx=(10, 5), pady=2, sticky="e")
        self.soul_meter_canvas.grid_remove()  # Hidden until Hell's Table Mode

        # Betting Controls Bar (visible in Chips Mode)
        self.betting_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        self.betting_frame.grid(row=4, column=0, columnspan=3, pady=(2, 4))
        if not self.chips_mode_var.get():
            self.betting_frame.grid_remove()  # Hidden in Casual Mode

        self.bet_chips_label = tkinter.Label(
            self.betting_frame, text="Bet Chips:", font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        self.bet_chips_label.pack(side="left", padx=(0, 6))

        self.chip_buttons.clear()
        for amount, bg_color, fg_color in CHIP_DENOMINATIONS:
            btn = tkinter.Button(
                self.betting_frame, text=f"${amount}", font=("Arial", 9, "bold"),
                width=5, background=bg_color, foreground=fg_color,
                activebackground=bg_color, activeforeground=fg_color,
                relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
                command=lambda a=amount: self._add_chip_bet(a)
            )
            btn.pack(side="left", padx=3)
            self.chip_buttons.append(btn)

        self.all_in_button = tkinter.Button(
            self.betting_frame, text="All In", font=("Arial", 9, "bold"),
            width=7, background="#e65100", foreground="#ffffff",
            activebackground="#f57c00", activeforeground="#ffffff",
            relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
            command=self._all_in
        )
        self.all_in_button.pack(side="left", padx=4)

        self.clear_bet_button = tkinter.Button(
            self.betting_frame, text="Clear Bet", font=("Arial", 9, "bold"),
            width=8, takefocus=False, command=self._clear_bet
        )
        self.clear_bet_button.pack(side="left", padx=5)

        self.deal_bet_button = tkinter.Button(
            self.betting_frame, text="Deal Hand", font=("Arial", 9, "bold"),
            width=10, background="#ffd700", foreground="#000000",
            activebackground="#ffea00", activeforeground="#000000",
            relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
            command=self._deal_hand_with_bet
        )
        self.deal_bet_button.pack(side="left", padx=5)

        self.rebuy_button = tkinter.Button(
            self.betting_frame, text="Rebuy ($1,000)", font=("Arial", 9, "bold"),
            width=13, background="#ff9800", foreground="#000000",
            activebackground="#ffa726", relief="raised", borderwidth=2,
            cursor="hand2", takefocus=False, command=self._rebuy
        )
        self.rebuy_button.pack(side="left", padx=5)

        # Insurance Prompt Bar (visible when dealer shows an Ace in Chips Mode)
        self.insurance_frame = tkinter.Frame(
            self.root, background=PANEL_BACKGROUND_COLOR, padx=10, pady=5,
            relief="ridge", borderwidth=2
        )
        self.insurance_frame.grid(row=5, column=0, columnspan=3, pady=(2, 6))
        self.insurance_frame.grid_remove()  # Hidden by default

        self.insurance_label = tkinter.Label(
            self.insurance_frame, text="Dealer shows an Ace! Insurance pays 2:1 against Dealer Blackjack.",
            font=("Arial", 10, "bold"), background=PANEL_BACKGROUND_COLOR, fg="#ffeb3b"
        )
        self.insurance_label.pack(side="left", padx=(0, 10))

        self.take_insurance_button = tkinter.Button(
            self.insurance_frame, text="Take Insurance ($25)", font=("Arial", 9, "bold"),
            background="#ff9800", foreground="#000000", activebackground="#ffa726",
            relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
            command=self._on_take_insurance
        )
        self.take_insurance_button.pack(side="left", padx=5)

        self.decline_insurance_button = tkinter.Button(
            self.insurance_frame, text="Decline", font=("Arial", 9, "bold"),
            width=8, takefocus=False, command=self._on_decline_insurance
        )
        self.decline_insurance_button.pack(side="left", padx=5)

        # Bottom Button Bar
        button_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        button_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 10))
        self.button_frame = button_frame

        # Ornate Video Poker Gem Action Buttons (Polished glass / gem styling with crisp black text)
        self.hit_button = tkinter.Button(
            button_frame, text="Hit", width=8, font=("Arial", 10, "bold"),
            background="#00e676", foreground="#000000",
            activebackground="#69f0ae", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_hit
        )
        self.hit_button.grid(row=0, column=0, padx=6)

        self.stand_button = tkinter.Button(
            button_frame, text="Stand", width=8, font=("Arial", 10, "bold"),
            background="#ff5252", foreground="#000000",
            activebackground="#ff8a80", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_stand
        )
        self.stand_button.grid(row=0, column=1, padx=6)

        self.double_button = tkinter.Button(
            button_frame, text="Double", width=8, font=("Arial", 10, "bold"),
            background="#ffd740", foreground="#000000",
            activebackground="#ffe57f", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_double_down, state="disabled"
        )
        self.double_button.grid(row=0, column=2, padx=6)

        self.split_button = tkinter.Button(
            button_frame, text="Split", width=8, font=("Arial", 10, "bold"),
            background="#40c4ff", foreground="#000000",
            activebackground="#80d8ff", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_split, state="disabled"
        )
        self.split_button.grid(row=0, column=3, padx=6)

        self.surrender_button = tkinter.Button(
            button_frame, text="Surrender", width=9, font=("Arial", 10, "bold"),
            background="#cfd8dc", foreground="#000000",
            activebackground="#eceff1", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_surrender, state="disabled"
        )
        self.surrender_button.grid(row=0, column=4, padx=6)

        self.new_game_button = tkinter.Button(
            button_frame, text="New Game", width=9, font=("Arial", 10, "bold"),
            background="#ffd700", foreground="#000000",
            activebackground="#ffea00", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=4, cursor="hand2", takefocus=False,
            command=self.new_game
        )
        self.new_game_button.grid(row=0, column=5, padx=6)

        self.miracle_button = tkinter.Button(
            button_frame, text="✨ Miracle", width=10, font=("Arial", 10, "bold"),
            background="#18ffff", foreground="#000000",
            activebackground="#84ffff", activeforeground="#000000",
            relief="raised", borderwidth=3, cursor="hand2",
            takefocus=False, command=self._on_miracle_draw, state="disabled"
        )
        self.miracle_button.grid(row=0, column=6, padx=6)
        self.miracle_button.grid_remove()

        # Spacer column to push right-hand action controls to the far right
        button_frame.columnconfigure(7, weight=1)

        # Cursed Stakes Mode Button (Unlocks upon surviving Hell's Table, placed left of Chips Mode)
        self.cursed_stakes_button = tkinter.Button(
            button_frame, text="🔥 Cursed Stakes", font=("Arial", 10, "bold"),
            background="#b71c1c", fg="#ffd700", activebackground="#d32f2f",
            activeforeground="#ffffff", relief="ridge", borderwidth=1, cursor="hand2",
            takefocus=False, command=self._on_toggle_cursed_stakes
        )
        self.cursed_stakes_button.grid(row=0, column=8, padx=(6, 8), sticky="e")
        if not self.haunted.unlocked_cursed_stakes:
            self.cursed_stakes_button.grid_remove()  # Hidden until unlocked

        # Chips Mode Toggle Checkbutton placed in bottom-right action area
        self.chips_mode_check = tkinter.Checkbutton(
            button_frame, text="Chips Mode", variable=self.chips_mode_var,
            command=self._on_toggle_chips_mode, font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white",
            selectcolor=PANEL_BACKGROUND_COLOR, activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", cursor="hand2"
        )
        self.chips_mode_check.grid(row=0, column=9, padx=(8, 12), sticky="e")

        # Celestial Blessings Display Tray (shows acquired relics in Hell's Table)
        self.blessings_tray = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        self.blessings_tray.grid(row=7, column=0, columnspan=3, pady=(0, 4))
        self.blessings_tray.grid_remove()

        # Keyboard shortcuts initialization
        self._setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self):
        """Binds full keyboard shortcut support across the window for gameplay accessibility."""
        # Deal / Hit / New Game shortcuts (Enter and Space)
        for key in ("<Return>", "<KP_Enter>", "<space>"):
            self.root.bind(key, self._on_key_deal_or_hit)
            self.root.bind_class("Button", key, self._on_key_deal_or_hit)

        # Action shortcuts (case-insensitive)
        for key in ("<h>", "<H>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_hit, self.hit_button))
        for key in ("<s>", "<S>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_stand, self.stand_button))
        for key in ("<d>", "<D>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_double_down, self.double_button))
        for key in ("<p>", "<P>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_split, self.split_button))
        for key in ("<r>", "<R>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_surrender, self.surrender_button))
        for key in ("<c>", "<C>"):
            self.root.bind(key, lambda e: self._on_key_action(self._clear_bet, getattr(self, "clear_bet_button", None)))
        for key in ("<a>", "<A>"):
            self.root.bind(key, lambda e: self._on_key_action(self._all_in, getattr(self, "all_in_button", None)))
        for key in ("<m>", "<M>"):
            self.root.bind(key, lambda e: self._on_toggle_sound())
        for key in ("<v>", "<V>"):
            self.root.bind(key, lambda e: self._on_toggle_dealer_view())
        for key in ("<x>", "<X>"):
            self.root.bind(key, lambda e: self._on_miracle_draw())

        # Shortcuts / Help Overlay toggle shortcuts
        for key in ("<question>", "?", "/", "<F1>"):
            self.root.bind(key, lambda e: self._toggle_shortcuts_overlay())

        # Scale and Fullscreen display mode shortcuts
        self.root.bind("<F10>", lambda e: self.toggle_scale_mode())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())

        # Settings dialog shortcuts
        for key in ("<o>", "<O>", "<F2>"):
            self.root.bind(key, lambda e: self._open_settings_dialog())

        # Insurance shortcuts (Y = Take, N = Decline)
        for key in ("<y>", "<Y>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_take_insurance, getattr(self, "take_insurance_button", None)))
        for key in ("<n>", "<N>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_decline_insurance, getattr(self, "decline_insurance_button", None)))

        # Context-sensitive Escape: closes shortcuts HUD, declines insurance, or exits fullscreen
        self.root.bind("<Escape>", self._on_escape_key)

        # Chip denomination shortcuts: 1=$5, 2=$25, 3=$100, 4=$500
        chip_keys = {
            "<Key-1>": 5, "<KP_1>": 5,
            "<Key-2>": 25, "<KP_2>": 25,
            "<Key-3>": 100, "<KP_3>": 100,
            "<Key-4>": 500, "<KP_4>": 500,
        }
        for k, amt in chip_keys.items():
            self.root.bind(k, lambda e, a=amt: self._on_key_chip(a))

    def _on_key_action(self, action_fn, button=None):
        """Invokes an action function if the corresponding button is currently enabled."""
        if button is not None:
            try:
                if str(button.cget("state")) != "normal":
                    return "break"
            except Exception:
                pass
        action_fn()
        return "break"

    def _on_key_chip(self, amount: int):
        """Adds chip bet if currently in the betting phase."""
        if getattr(self, "is_betting_phase", False) and self.chips_mode_var.get():
            self._add_chip_bet(amount)
        return "break"

    def _on_key_deal_or_hit(self, event=None):
        """
        Handles Enter and Space key presses dynamically based on game state:
        1. If insurance is offered -> takes insurance if enabled.
        2. If betting phase in Chips Mode -> deals hand if bet is valid.
        3. If player's turn -> hits if Hit is enabled.
        4. If round is over -> deals a new game.
        """
        # 1. Insurance phase
        if getattr(self, "is_insurance_phase", False):
            if hasattr(self, "take_insurance_button") and str(self.take_insurance_button.cget("state")) == "normal":
                self._on_take_insurance()
                return "break"

        # 2. Betting phase (Chips Mode)
        if getattr(self, "is_betting_phase", False) and self.chips_mode_var.get():
            if hasattr(self, "deal_bet_button") and str(self.deal_bet_button.cget("state")) == "normal":
                self._deal_hand_with_bet()
                return "break"

        # 3. Active card turn: Hit
        if hasattr(self, "hit_button") and str(self.hit_button.cget("state")) == "normal":
            self.on_hit()
            return "break"

        # 4. Round completed: New Game
        if hasattr(self, "new_game_button") and str(self.new_game_button.cget("state")) == "normal":
            self.new_game()
            return "break"

        return "break"

    def _on_toggle_sound(self):
        """Toggles sound playback on or off and updates the UI button text."""
        is_enabled = self.sound_manager.toggle_mute()
        self.sound_status_var.set("🔊 Sound: ON" if is_enabled else "🔇 Sound: OFF")
        return "break"

    def _toggle_shortcuts_overlay(self):
        """Toggles the display of the keyboard shortcut help overlay dialog."""
        if self._shortcuts_dialog is not None and self._shortcuts_dialog.winfo_exists():
            self._close_shortcuts_overlay()
        else:
            self._show_shortcuts_overlay()
        return "break"

    def _close_shortcuts_overlay(self):
        """Closes and destroys the shortcuts help overlay dialog."""
        if self._shortcuts_dialog is not None:
            try:
                if self._shortcuts_dialog.winfo_exists():
                    self._shortcuts_dialog.destroy()
            except Exception:
                pass
            self._shortcuts_dialog = None

    def _show_shortcuts_overlay(self):
        """Displays a clean modal HUD dialog illustrating all keyboard and mouse controls."""
        if self._shortcuts_dialog is not None and self._shortcuts_dialog.winfo_exists():
            self._shortcuts_dialog.lift()
            self._shortcuts_dialog.focus_set()
            return

        dialog = tkinter.Toplevel(self.root)
        dialog.title("Blackjack - Keyboard Shortcuts & Controls")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.configure(background=PANEL_BACKGROUND_COLOR, padx=14, pady=12)

        if getattr(self, "_icon_photo", None):
            try:
                dialog.iconphoto(False, self._icon_photo)
            except Exception:
                pass

        # Center dialog relative to main window
        dialog_w, dialog_h = 740, 530
        try:
            root_x = self.root.winfo_rootx()
            root_y = self.root.winfo_rooty()
            root_w = self.root.winfo_width()
            root_h = self.root.winfo_height()
            pos_x = max(root_x + (root_w - dialog_w) // 2, 0)
            pos_y = max(root_y + (root_h - dialog_h) // 2, 0)
            dialog.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
        except Exception:
            dialog.geometry(f"{dialog_w}x{dialog_h}")

        # Top Header Bar
        header_frame = tkinter.Frame(dialog, background=PANEL_BACKGROUND_COLOR)
        header_frame.pack(fill="x", pady=(0, 10))

        q_icon = self.icon_loader.get_icon("keyboard_question", scale_div=2)
        if q_icon:
            q_lbl = tkinter.Label(header_frame, image=q_icon, background=PANEL_BACKGROUND_COLOR)
            q_lbl.image = q_icon
            q_lbl.pack(side="left", padx=(0, 8))

        title_box = tkinter.Frame(header_frame, background=PANEL_BACKGROUND_COLOR)
        title_box.pack(side="left")

        tkinter.Label(
            title_box, text="KEYBOARD SHORTCUTS & CONTROLS",
            font=("Arial", 13, "bold"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="w")

        tkinter.Label(
            title_box, text="Full hands-free keyboard accessibility for authentic casino gameplay",
            font=("Arial", 8, "italic"), fg="#80cbc4", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="w")

        close_btn = tkinter.Button(
            header_frame, text="✕ Close (Esc)", font=("Arial", 9, "bold"),
            background="#c62828", foreground="#ffffff", activebackground="#e53935",
            activeforeground="#ffffff", relief="raised", borderwidth=1, cursor="hand2",
            takefocus=False, command=self._close_shortcuts_overlay
        )
        close_btn.pack(side="right")

        # 2x2 Grid of Categorized Panels
        grid_frame = tkinter.Frame(dialog, background=PANEL_BACKGROUND_COLOR)
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)
        grid_frame.rowconfigure(1, weight=1)

        def make_panel(parent, title_text, row_idx, col_idx):
            panel = tkinter.Frame(
                parent, background="#053612", relief="ridge", borderwidth=2,
                padx=10, pady=8
            )
            panel.grid(row=row_idx, column=col_idx, sticky="nsew", padx=5, pady=5)
            tkinter.Label(
                panel, text=title_text, font=("Arial", 10, "bold"),
                fg="#ffeb3b", background="#053612"
            ).pack(anchor="w", pady=(0, 4))
            return panel

        def add_row(parent_panel, icon_names: list[str], action_text: str, hint_text: str = ""):
            r = tkinter.Frame(parent_panel, background="#053612")
            r.pack(fill="x", pady=2)

            badges = tkinter.Frame(r, background="#053612")
            badges.pack(side="left")

            for i, name in enumerate(icon_names):
                if i > 0:
                    tkinter.Label(
                        badges, text="or", font=("Arial", 8, "bold"),
                        fg="#80cbc4", background="#053612"
                    ).pack(side="left", padx=2)

                icon = self.icon_loader.get_icon(name, scale_div=2)
                if icon:
                    l = tkinter.Label(badges, image=icon, background="#053612")
                    l.image = icon
                    l.pack(side="left", padx=1)
                else:
                    disp = name.replace("keyboard_", "").replace("mouse_", "").upper()
                    tkinter.Label(
                        badges, text=f"[{disp}]", font=("Consolas", 8, "bold"),
                        background="#ffffff", foreground="#000000",
                        padx=3, pady=1, relief="raised", bd=1
                    ).pack(side="left", padx=1)

            tkinter.Label(
                r, text=action_text, font=("Arial", 9, "bold"),
                fg="#ffffff", background="#053612"
            ).pack(side="left", padx=(6, 2))

            if hint_text:
                tkinter.Label(
                    r, text=hint_text, font=("Arial", 8),
                    fg="#a5d6a7", background="#053612"
                ).pack(side="left")

        # 1. Table Actions
        panel_actions = make_panel(grid_frame, "🃏 TABLE ACTIONS", 0, 0)
        add_row(panel_actions, ["keyboard_space", "keyboard_enter"], "Deal / Hit / Next", "(Context-sensitive)")
        add_row(panel_actions, ["keyboard_h"], "Hit", "(Draw another card)")
        add_row(panel_actions, ["keyboard_s"], "Stand", "(End turn, dealer plays)")
        add_row(panel_actions, ["keyboard_d"], "Double Down", "(Double bet, draw 1 card)")
        add_row(panel_actions, ["keyboard_p"], "Split Pair", "(Split equal rank cards)")
        add_row(panel_actions, ["keyboard_r"], "Surrender", "(Forfeit half bet before hitting)")

        # 2. Chips & Wagering
        panel_betting = make_panel(grid_frame, "💰 CHIPS & WAGERING", 0, 1)
        add_row(panel_betting, ["keyboard_1"], "Bet $5", "(White chip)")
        add_row(panel_betting, ["keyboard_2"], "Bet $25", "(Red chip)")
        add_row(panel_betting, ["keyboard_3"], "Bet $100", "(Green chip)")
        add_row(panel_betting, ["keyboard_4"], "Bet $500", "(Black & Gold chip)")
        add_row(panel_betting, ["keyboard_a"], "All In", "(Wager entire bankroll)")
        add_row(panel_betting, ["keyboard_c"], "Clear Bet", "(Reset bet to $0)")

        # 3. Insurance Phase
        panel_insurance = make_panel(grid_frame, "🛡️ INSURANCE DECISIONS", 1, 0)
        add_row(panel_insurance, ["keyboard_y"], "Take Insurance", "(Pays 2:1 on Dealer Ace)")
        add_row(panel_insurance, ["keyboard_n", "keyboard_escape"], "Decline", "(Decline side bet)")

        # 4. System & Controls
        panel_system = make_panel(grid_frame, "⚙️ SYSTEM & CONTROLS", 1, 1)
        add_row(panel_system, ["keyboard_m"], "Toggle Sound", "(Mute / Unmute)")
        add_row(panel_system, ["keyboard_f10"], "Scale 1x / 2x", "(Toggle High-DPI UI)")
        add_row(panel_system, ["keyboard_f11"], "Toggle Fullscreen", "(F11 or Escape to exit)")
        add_row(panel_system, ["keyboard_question", "keyboard_f1"], "Toggle Help", "(Show / Hide this overlay)")
        add_row(panel_system, ["mouse_left"], "Click Button / Chip", "(Direct mouse interaction)")

        # Footer Tip Banner
        footer_frame = tkinter.Frame(dialog, background=PANEL_BACKGROUND_COLOR)
        footer_frame.pack(fill="x", pady=(8, 0))

        tkinter.Label(
            footer_frame,
            text="💡 Tip: Keyboard shortcuts are context-sensitive and only activate when the corresponding button is enabled.",
            font=("Arial", 8, "italic"), fg="#ffe082", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="center")

        # Window event bindings
        def _close_dialog_event(e=None):
            self._close_shortcuts_overlay()
            return "break"

        dialog.protocol("WM_DELETE_WINDOW", self._close_shortcuts_overlay)
        for k in ("<Escape>", "<question>", "?", "/", "<F1>"):
            dialog.bind(k, _close_dialog_event)
            close_btn.bind(k, _close_dialog_event)

        dialog.focus_set()
        self._shortcuts_dialog = dialog

    def _open_settings_dialog(self):
        """Displays the casino settings and save management modal dialog."""
        if self._settings_dialog is not None and self._settings_dialog.winfo_exists():
            self._settings_dialog.lift()
            self._settings_dialog.focus_set()
            return "break"
        self._settings_dialog = SettingsDialog(self.root, self)
        return "break"

    def _close_settings_dialog(self):
        """Safely dismisses and destroys the settings dialog."""
        if self._settings_dialog is not None:
            try:
                if self._settings_dialog.winfo_exists():
                    self._settings_dialog.destroy()
            except Exception:
                pass
            self._settings_dialog = None

    def _on_click_stage_hanger(self):
        """Callback when the wardrobe hanger button on the stage canvas is clicked."""
        self._open_wardrobe_dialog()

    def _open_wardrobe_dialog(self):
        """Displays the Dealer Wardrobe & Dressing Room modal dialog."""
        if getattr(self, "_wardrobe_dialog", None) is not None and self._wardrobe_dialog.winfo_exists():
            self._wardrobe_dialog.lift()
            self._wardrobe_dialog.focus_set()
            return "break"
        self._wardrobe_dialog = WardrobeDialog(self.root, self)
        return "break"

    def _close_wardrobe_dialog(self):
        """Safely dismisses and destroys the wardrobe dialog."""
        if getattr(self, "_wardrobe_dialog", None) is not None:
            try:
                if self._wardrobe_dialog.winfo_exists():
                    self._wardrobe_dialog.destroy()
            except Exception:
                pass
            self._wardrobe_dialog = None

    def clear_player_save_data(self):
        """Resets persistent save data to blank slate and synchronizes table unlocks."""
        self.save_manager.clear_save()
        self.haunted.unlocked_cursed_stakes = False
        self.haunted.unlocked_exorcist = False
        self.haunted.unlocked_haunted_deck = False
        self.cursed_stakes_var.set(False)
        if hasattr(self, "cursed_stakes_button"):
            self.cursed_stakes_button.grid_remove()

    # ------------------------------------------------------------------------
    # Haunted Halloween & Hell's Table Orchestration
    # ------------------------------------------------------------------------

    def _score_player_hand(self, hand):
        """Scores player hand, taking into account celestial blessings like Cherub's Shield."""
        raw = score_hand(hand)
        if hasattr(self, "haunted"):
            return self.haunted.modify_player_score(raw)
        return raw

    def _on_toggle_dealer_view(self):
        """Dealer view is permanently enabled."""
        self.dealer_view_var.set(True)
        self.dealer_view_status_var.set("👤 Dealer: ON")
        self._update_dealer_avatar()
        return "break"


    def set_dealer_speech(self, text: str, stream: bool = False):
        """Sets dealer dialogue callout bubble text, updates visibility, and animates mouth."""
        if not hasattr(self, "dealer_speech_var"):
            self.dealer_speech_var = tkinter.StringVar(value="")
        self._current_speech_full = text
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            try:
                self.root.after_cancel(self._typewriter_timer_id)
            except Exception:
                pass
            self._typewriter_timer_id = None

        if not text:
            self.clear_dealer_speech()
            return

        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.pack(anchor="w", pady=(2, 0))

        is_headless = getattr(self, "suppress_mode_dialog", False) or (self.root.state() == "withdrawn")
        if stream and not is_headless:
            self._typewriter_index = 0
            self.dealer_speech_var.set("")
            self._stream_typewriter_step()
        elif stream and is_headless:
            self._typewriter_index = 0
            self.dealer_speech_var.set("")
            try:
                if self.root.winfo_exists():
                    self._typewriter_timer_id = self.root.after(25, self._stream_typewriter_step)
            except Exception:
                pass
        else:
            self.dealer_speech_var.set(text)
            if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
                self._animate_speech_mouth(remaining_flaps=min(max(2, len(text) // 8), 8))

    def _stream_typewriter_step(self):
        """Streams one character to the speech balloon at 25 ms intervals."""
        if not hasattr(self, "_current_speech_full") or not self._current_speech_full:
            return
        if self._typewriter_index < len(self._current_speech_full):
            self._typewriter_index += 1
            self.dealer_speech_var.set(self._current_speech_full[:self._typewriter_index])
            if self._typewriter_index % 2 == 0:
                self._step_speech_mouth()
            try:
                if self.root.winfo_exists():
                    self._typewriter_timer_id = self.root.after(25, self._stream_typewriter_step)
            except Exception:
                pass
        else:
            self._complete_typewriter_speech()

    def _complete_typewriter_speech(self):
        """Completes in-flight typewriter speech immediately."""
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            try:
                self.root.after_cancel(self._typewriter_timer_id)
            except Exception:
                pass
            self._typewriter_timer_id = None
        if hasattr(self, "_current_speech_full") and self._current_speech_full:
            self.dealer_speech_var.set(self._current_speech_full)
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_mouth_state("neutral")
            self._refresh_dealer_avatar_image()

    def clear_dealer_speech(self):
        """Hides dealer dialogue bubble and resets mouth to neutral."""
        if hasattr(self, "_dealer_speech_anim_timer_id") and self._dealer_speech_anim_timer_id:
            try:
                self.root.after_cancel(self._dealer_speech_anim_timer_id)
            except Exception:
                pass
            self._dealer_speech_anim_timer_id = None
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            try:
                self.root.after_cancel(self._typewriter_timer_id)
            except Exception:
                pass
            self._typewriter_timer_id = None
        self._current_speech_full = ""
        if hasattr(self, "dealer_speech_var"):
            self.dealer_speech_var.set("")
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.pack_forget()
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_mouth_state("neutral")
            self._refresh_dealer_avatar_image()

    def _calculate_breathing_offset(self, step: float) -> int:
        """Calculates sinusoidal vertical offset in [-2, +2] px for dealer respiration."""
        return int(round(1.8 * math.sin(step)))

    def _dealer_breathing_tick(self):
        """25-30 FPS idle ticker oscillating dealer avatar vertically to simulate breathing and stage particles."""
        if not hasattr(self, "root") or not self.root.winfo_exists():
            return
        self._dealer_anim_step += 0.15
        y_off = self._calculate_breathing_offset(self._dealer_anim_step)
        if hasattr(self, "dealer_stage_canvas") and self.dealer_stage_canvas.find_withtag("dealer_sprite"):
            w = max(10, self.dealer_stage_canvas.canvas_width)
            h = max(10, self.dealer_stage_canvas.canvas_height)
            self.dealer_stage_canvas.coords("dealer_sprite", w // 2, h + y_off)

        if hasattr(self, "dealer_stage_canvas"):
            if random.random() < 0.35:
                self.dealer_stage_canvas.spawn_ambient_particles(count=1)
            self.dealer_stage_canvas.update_particles()

        if hasattr(self, "dealer_avatar_label") and self.dealer_avatar_label.winfo_manager() == "pack":
            try:
                self.dealer_avatar_label.pack_configure(pady=(max(0, 2 + y_off), max(0, 2 - y_off)))
            except Exception:
                pass

        try:
            if self.root.winfo_exists():
                self._dealer_idle_timer_id = self.root.after(40, self._dealer_breathing_tick)
        except Exception:
            pass

    def _start_dealer_idle_animation(self):
        """Starts the continuous idle breathing animation ticker."""
        if self._dealer_idle_timer_id is None:
            self._dealer_breathing_tick()

    def _schedule_dealer_blink(self, delay_ms: Optional[int] = None):
        """Schedules the next natural autonomous dealer eye blink."""
        if self._dealer_blink_timer_id:
            try:
                self.root.after_cancel(self._dealer_blink_timer_id)
            except Exception:
                pass
            self._dealer_blink_timer_id = None

        if delay_ms is None:
            delay_ms = random.randint(3000, 5500)

        try:
            if self.root.winfo_exists():
                self._dealer_blink_timer_id = self.root.after(delay_ms, self._trigger_dealer_blink)
        except Exception:
            pass

    def _cancel_blink_timers(self):
        """Safely cancels all active sub-timers for the 3-frame blink sequence."""
        if not hasattr(self, "_dealer_blink_timers"):
            self._dealer_blink_timers = []
        for tid in self._dealer_blink_timers:
            try:
                self.root.after_cancel(tid)
            except Exception:
                pass
        self._dealer_blink_timers.clear()
        if hasattr(self, "_dealer_blink_restore_timer_id") and self._dealer_blink_restore_timer_id:
            try:
                self.root.after_cancel(self._dealer_blink_restore_timer_id)
            except Exception:
                pass
            self._dealer_blink_restore_timer_id = None

    def _trigger_dealer_blink(self, duration_ms: int = 120):
        """Initiates a smooth 3-frame dealer eye blink (open -> half -> closed -> half -> open)."""
        self._cancel_blink_timers()
        self._advance_blink_step(1, duration_ms)

    def _advance_blink_step(self, step: int, duration_ms: int = 120):
        """Advances through the 3-frame eye blink sequence."""
        if not hasattr(self, "dealer_actor"):
            return
        if step == 1:
            self.dealer_actor.set_eye_state("half")
            self._refresh_dealer_avatar_image()
            try:
                if self.root.winfo_exists():
                    tid = self.root.after(int(duration_ms * 0.25), lambda: self._advance_blink_step(2, duration_ms))
                    self._dealer_blink_timers.append(tid)
            except Exception:
                pass
        elif step == 2:
            self.dealer_actor.set_eye_state("closed")
            self._refresh_dealer_avatar_image()
            try:
                if self.root.winfo_exists():
                    tid = self.root.after(int(duration_ms * 0.45), lambda: self._advance_blink_step(3, duration_ms))
                    self._dealer_blink_timers.append(tid)
            except Exception:
                pass
        elif step == 3:
            self.dealer_actor.set_eye_state("half")
            self._refresh_dealer_avatar_image()
            try:
                if self.root.winfo_exists():
                    tid = self.root.after(int(duration_ms * 0.25), lambda: self._advance_blink_step(4, duration_ms))
                    self._dealer_blink_timers.append(tid)
            except Exception:
                pass
        elif step == 4:
            self.dealer_actor.set_eye_state("open")
            self._refresh_dealer_avatar_image()
            self._schedule_dealer_blink()

    def _restore_dealer_eyes(self):
        """Restores dealer eyes to open state and schedules the next blink."""
        self._cancel_blink_timers()
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_eye_state("open")
            self._refresh_dealer_avatar_image()
        self._schedule_dealer_blink()

    def _get_scaled_dealer_photo(self) -> Optional[ImageTk.PhotoImage]:
        """Returns a high-resolution, scale-proportional PhotoImage for the horizon stage with curtain headroom."""
        if not hasattr(self, "dealer_actor"):
            return None
        pil_img = self.dealer_actor.get_composite_image()
        stage_h = self.dealer_stage_canvas.winfo_height() if hasattr(self, "dealer_stage_canvas") else 250
        if stage_h <= 20:
            stage_h = getattr(self.dealer_stage_canvas, "canvas_height", 250) if hasattr(self, "dealer_stage_canvas") else 250
        max_h = max(100, int(stage_h * 0.88))
        target_size = min(int(190 * self.scale_factor), max_h)
        if pil_img.size != (target_size, target_size):
            resample_mode = getattr(Image, "Resampling", Image).BILINEAR
            pil_img = pil_img.resize((target_size, target_size), resample_mode)
        self._scaled_dealer_photo = ImageTk.PhotoImage(pil_img, master=self.root)
        return self._scaled_dealer_photo


    def _refresh_dealer_avatar_image(self):
        """Lightweight composite re-render on dealer_avatar_label without full UI refresh."""
        if hasattr(self, "dealer_avatar_label") and hasattr(self, "dealer_actor"):
            img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            if img:
                try:
                    self.dealer_avatar_label.configure(image=img)
                    self.dealer_avatar_label.image = img
                except Exception:
                    pass
                if hasattr(self, "dealer_stage_canvas") and getattr(self, "dealer_view_var", None) and self.dealer_view_var.get():
                    self.dealer_stage_canvas.set_dealer_image(img)

    def _step_speech_mouth(self):
        """Toggles mouth state between talk and neutral during active speech."""
        if not hasattr(self, "dealer_actor"):
            return
        curr = self.dealer_actor.mouth_state
        next_state = "talk" if curr == "neutral" else "neutral"
        self.dealer_actor.set_mouth_state(next_state)
        self._refresh_dealer_avatar_image()

    def _animate_speech_mouth(self, remaining_flaps: int = 4):
        """Animates mouth flapping while dealer is speaking."""
        if remaining_flaps <= 0:
            if hasattr(self, "dealer_actor"):
                self.dealer_actor.set_mouth_state("neutral")
                self._refresh_dealer_avatar_image()
            self._dealer_speech_anim_timer_id = None
            return

        self._step_speech_mouth()
        try:
            if self.root.winfo_exists():
                self._dealer_speech_anim_timer_id = self.root.after(
                    120, lambda: self._animate_speech_mouth(remaining_flaps - 1)
                )
        except Exception:
            pass

    def _trigger_dealer_deal_gesture(self, duration_ms: int = 350):
        """Animates dealer dealing arm gesture when sweeping cards onto table."""
        if not hasattr(self, "dealer_actor"):
            return
        if self._dealer_gesture_timer_id:
            try:
                self.root.after_cancel(self._dealer_gesture_timer_id)
            except Exception:
                pass
        self.dealer_actor.set_arm_state("deal")
        self._refresh_dealer_avatar_image()
        try:
            if self.root.winfo_exists():
                self._dealer_gesture_timer_id = self.root.after(duration_ms, self._restore_dealer_arms)
        except Exception:
            self._restore_dealer_arms()

    def _trigger_dealer_peek_gesture(self, duration_ms: int = 500):
        """Animates dealer peeking at hole card."""
        if not hasattr(self, "dealer_actor"):
            return
        if self._dealer_gesture_timer_id:
            try:
                self.root.after_cancel(self._dealer_gesture_timer_id)
            except Exception:
                pass
        self.dealer_actor.set_arm_state("peek")
        self._refresh_dealer_avatar_image()
        try:
            if self.root.winfo_exists():
                self._dealer_gesture_timer_id = self.root.after(duration_ms, self._restore_dealer_arms)
        except Exception:
            self._restore_dealer_arms()

    def _restore_dealer_arms(self):
        """Restores dealer arms to resting table position."""
        if hasattr(self, "_dealer_gesture_timer_id") and self._dealer_gesture_timer_id:
            try:
                self.root.after_cancel(self._dealer_gesture_timer_id)
            except Exception:
                pass
            self._dealer_gesture_timer_id = None
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_arm_state("rest")
            self._refresh_dealer_avatar_image()

    def _trigger_dealer_gasp(self, duration_ms: int = 1200):
        """Animates surprised gasp mouth expression and spawns sweat drop on busts."""
        if not hasattr(self, "dealer_actor"):
            return
        if hasattr(self, "_dealer_mouth_timer_id") and self._dealer_mouth_timer_id:
            try:
                self.root.after_cancel(self._dealer_mouth_timer_id)
            except Exception:
                pass
            self._dealer_mouth_timer_id = None
        self.dealer_actor.set_mouth_state("gasp")
        self._refresh_dealer_avatar_image()
        if hasattr(self, "dealer_stage_canvas"):
            self.dealer_stage_canvas.spawn_sweat_particle()
            self.dealer_stage_canvas.update_particles()
        try:
            if self.root.winfo_exists():
                self._dealer_mouth_timer_id = self.root.after(duration_ms, self._restore_dealer_mouth)
        except Exception:
            self._restore_dealer_mouth()

    def _trigger_dealer_smirk(self, duration_ms: int = 1500):
        """Animates confident smirk mouth expression on dealer natural or victory."""
        if not hasattr(self, "dealer_actor"):
            return
        if hasattr(self, "_dealer_mouth_timer_id") and self._dealer_mouth_timer_id:
            try:
                self.root.after_cancel(self._dealer_mouth_timer_id)
            except Exception:
                pass
            self._dealer_mouth_timer_id = None
        self.dealer_actor.set_mouth_state("smirk")
        self._refresh_dealer_avatar_image()
        try:
            if self.root.winfo_exists():
                self._dealer_mouth_timer_id = self.root.after(duration_ms, self._restore_dealer_mouth)
        except Exception:
            self._restore_dealer_mouth()

    def _restore_dealer_mouth(self):
        """Restores dealer mouth to neutral resting expression."""
        if hasattr(self, "_dealer_mouth_timer_id") and self._dealer_mouth_timer_id:
            try:
                self.root.after_cancel(self._dealer_mouth_timer_id)
            except Exception:
                pass
            self._dealer_mouth_timer_id = None
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_mouth_state("neutral")
            self._refresh_dealer_avatar_image()

    def _update_dealer_speech_for_outcome(self, outcome: str):
        """Selects theatrical dealer dialogue based on outcome and active haunted phase."""
        phase = self.haunted.phase
        if phase == Phase.HELL_TABLE:
            if outcome == 'NATURAL_BLACKJACK':
                text = "A natural 21?! Insolent mortal, you test my wrath!"
            elif outcome in ('PLAYER_WINS', 'DEALER_BUST'):
                text = "Arrrgh! The fire consumes me... but only for a moment!"
            elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                text = "Claimed! Another fragment of your soul burns in the pit!"
            elif outcome == 'PUSH':
                text = "A standoff... the abyss is patient."
            else:
                text = "Stake your next breath, mortal!"
        elif phase == Phase.VICTORY:
            text = "✦ The holy dawn breaks! The void is sealed! ✦"
        elif phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
            if outcome in ('PLAYER_WINS', 'NATURAL_BLACKJACK'):
                text = "Enjoy your luck while the candles still flicker..."
            elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                text = "The cold deepens. Another flame wavers..."
            else:
                text = "Do you hear the whispers in the dark?"
        else:
            if outcome == 'NATURAL_BLACKJACK':
                text = "Blackjack! Natural 21 pays 3 to 2. Splendid hand."
            elif outcome == 'DEALER_BUST':
                text = "Dealer busts! The table pays all active hands."
            elif outcome == 'PLAYER_WINS':
                text = "Winner! Excellent play."
            elif outcome == 'PLAYER_BUST':
                text = "Bust! House takes the cards."
            elif outcome == 'DEALER_WINS':
                text = "House wins this hand."
            elif outcome == 'PUSH':
                text = "Push! Bets are returned."
            elif outcome == 'SURRENDER':
                text = "Surrendered. Live to wager another day."
            else:
                text = "Place your bets, cards on the felt."

        # Living dealer outcome reaction gestures
        if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
            if outcome == 'DEALER_BUST':
                self._trigger_dealer_gasp()
            elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                self._trigger_dealer_smirk()
            elif outcome in ('PLAYER_WINS', 'NATURAL_BLACKJACK') and phase == Phase.HELL_TABLE:
                self._trigger_dealer_gasp()

        self.set_dealer_speech(text)

    def _update_dealer_avatar(self):
        """Updates the dealer avatar image based on toggle state and haunted phase."""
        if not hasattr(self, "dealer_avatar_label"):
            return

        if self.haunted.phase == Phase.HELL_TABLE:
            if hasattr(self, "dealer_actor"):
                self.dealer_actor.equip_costume("malphas")
                demon_img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            else:
                demon_img = self.haunted_assets.get("dealer_demon_0")
            if demon_img:
                self.dealer_avatar_label.configure(image=demon_img)
                self.dealer_avatar_label.image = demon_img
                if hasattr(self, "dealer_stage_canvas"):
                    self.dealer_stage_canvas.set_dealer_image(demon_img)
            self.dealer_avatar_label.pack(side="left", padx=2, pady=2)
            self.dealer_view_status_var.set("☠ The Pit Fiend")
            self.dealer_view_button.configure(state="disabled")
            if hasattr(self, "dealer_nameplate_label"):
                self.dealer_nameplate_label.configure(text="☠ The Pit Fiend", fg="#ff1744")
            self._sync_dealer_stage_colors("#140508")
            return

        self.dealer_view_button.configure(state="normal")
        self.dealer_view_status_var.set("👤 Dealer: ON")

        if hasattr(self, "dealer_actor"):
            if self.haunted.phase == Phase.VICTORY:
                self.dealer_actor.equip_costume("uriel")
            elif self.haunted.phase == Phase.NORMAL:
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)

        bg_col = PANEL_BACKGROUND_COLOR

        if self.haunted.phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
            if hasattr(self, "dealer_actor"):
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)
                img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            else:
                img = self.haunted_assets.get("dealer_creep")
            name_text = "The Dealer (Hollow)"
            name_col = "#ce93d8"
            bg_col = "#0f0d1a"
        elif self.haunted.phase == Phase.VICTORY:
            if hasattr(self, "dealer_actor"):
                self.dealer_actor.equip_costume("uriel")
                img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            else:
                img = self.haunted_assets.get("angel_avatar")
            name_text = "✨ Celestial Messenger"
            name_col = "#00e5ff"
            bg_col = "#0d2b26"
        else:
            if hasattr(self, "dealer_actor"):
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)
                img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
                profile = self.dealer_actor.get_profile()
                name_text = profile.name if profile.id == "julian" else profile.title
                name_col = profile.nameplate_fg
                bg_col = profile.speech_bg
            else:
                img = self.haunted_assets.get("dealer_classic")
                name_text = "The Dealer"
                name_col = "#ffd700"

        if img:
            self.dealer_avatar_label.configure(image=img)
            self.dealer_avatar_label.image = img
            if hasattr(self, "dealer_stage_canvas"):
                self.dealer_stage_canvas.set_dealer_image(img)
        self.dealer_avatar_label.pack(side="left", padx=2, pady=2)
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(text=name_text, fg=name_col)
        self._sync_dealer_stage_colors(bg_col)

    def _sync_dealer_stage_colors(self, bg_col: str):
        """Synchronizes dealer stage frames with active character/phase atmosphere."""
        if hasattr(self, "dealer_header_row"):
            self.dealer_header_row.configure(background=bg_col)
        if hasattr(self, "dealer_avatar_label"):
            self.dealer_avatar_label.configure(background=bg_col)
        if hasattr(self, "dealer_dialogue_frame"):
            self.dealer_dialogue_frame.configure(background=bg_col)
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(background=bg_col)

    def _update_candles_display(self):
        """Synchronizes 5-candle indicator bar and 2.5D Altar with remaining candles."""
        if hasattr(self, "haunted_altar"):
            if self.haunted.phase in (Phase.OMEN, Phase.SNUFFING) or (self.haunted.phase == Phase.HELL_TABLE and self.haunted.candles_remaining > 0):
                if not getattr(self, "_candles_manifested", False):
                    self.haunted_altar.pack(side="top", pady=0)
                    self.haunted_altar.animate_candle_poof()
                    self._candles_manifested = True
                else:
                    self.haunted_altar.pack(side="top", pady=0)
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass
                if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
                    self.card_table_frame.sync_children_felt()
                self.haunted_altar.set_candle_state(self.haunted.candles_remaining, visible=True)
            else:
                self.haunted_altar.set_candle_state(0, visible=False)
                if getattr(self.haunted, "gravestones_risen", 0) <= 0:
                    self.haunted_altar.pack_forget()

        # Legacy fallback synchronization
        if hasattr(self, "candle_bar_frame") and self.candle_labels:
            if self.haunted.phase in (Phase.OMEN, Phase.SNUFFING) or (self.haunted.phase == Phase.HELL_TABLE and self.haunted.candles_remaining > 0):
                self.candle_bar_frame.pack(side="top", pady=2)
                lit_img = self.haunted_assets.get("candle_lit")
                unlit_img = self.haunted_assets.get("candle_unlit")
                for i, lbl in enumerate(self.candle_labels):
                    img = lit_img if i < self.haunted.candles_remaining else unlit_img
                    if img:
                        lbl.configure(image=img)
                        lbl.image = img
            else:
                self.candle_bar_frame.pack_forget()

    def _update_gravestones_display(self):
        """Displays gravestones rising through the felt on deaths / busts with kinetic eruption."""
        if hasattr(self, "haunted_altar"):
            if self.haunted.gravestones_risen <= 0 or self.haunted.phase == Phase.NORMAL:
                self.haunted_altar.set_gravestone_state(0, visible=False)
                if not (self.haunted.phase in (Phase.OMEN, Phase.SNUFFING) or (self.haunted.phase == Phase.HELL_TABLE and self.haunted.candles_remaining > 0)):
                    self.haunted_altar.pack_forget()
            else:
                self.haunted_altar.pack(side="top", pady=0)
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass
                if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
                    self.card_table_frame.sync_children_felt()
                new_risen = self.haunted.gravestones_risen
                last_risen = getattr(self, "_last_gravestones_risen", 0)
                if new_risen > last_risen:
                    stone_idx = min(new_risen, 5) - 1
                    self.haunted_altar.set_gravestone_state(new_risen, visible=True)
                    self.haunted_altar.animate_grave_eruption(stone_idx)
                    self._last_gravestones_risen = new_risen
                else:
                    self.haunted_altar.set_gravestone_state(new_risen, visible=True)

        # Legacy fallback synchronization (kept populated for compatibility, but never packed to avoid duplicate rendering)
        if hasattr(self, "gravestones_frame") and self.gravestone_labels is not None and self.gravestones_frame.winfo_exists():
            self.gravestones_frame.pack_forget()
            grave_img = self.haunted_assets.get("gravestone")
            for child in self.gravestones_frame.winfo_children():
                child.destroy()
            self.gravestone_labels.clear()
            if self.haunted.gravestones_risen > 0 and self.haunted.phase != Phase.NORMAL:
                count = min(self.haunted.gravestones_risen, 5)
                for _ in range(count):
                    lbl = tkinter.Label(self.gravestones_frame, image=grave_img, background=PANEL_BACKGROUND_COLOR)
                    lbl.image = grave_img
                    self.gravestone_labels.append(lbl)

    def _update_blessings_tray(self):
        """Renders equipped relic badges in the blessings tray."""
        if not hasattr(self, "blessings_tray"):
            return
        for child in self.blessings_tray.winfo_children():
            child.destroy()

        if self.haunted.phase != Phase.HELL_TABLE or not self.haunted.equipped_blessings:
            self.blessings_tray.grid_remove()
            if hasattr(self, "miracle_button"):
                self.miracle_button.grid_remove()
            return

        bg_col = self.root["background"]
        self.blessings_tray.configure(background=bg_col)
        self.blessings_tray.grid()
        tkinter.Label(
            self.blessings_tray, text="✦ RELICS: ", font=("Arial", 9, "bold"),
            fg="#ffd700", background=bg_col
        ).pack(side="left", padx=(0, 4))

        for b in sorted(self.haunted.equipped_blessings, key=lambda x: x.value):
            details = BLESSING_REGISTRY[b]
            img = self.haunted_assets.get(f"relic_{b.value}") or self.haunted_assets.get(b.value)
            f = tkinter.Frame(self.blessings_tray, background="#051f38", relief="ridge", borderwidth=1, padx=4, pady=2)
            f.pack(side="left", padx=3)
            if img:
                ilbl = tkinter.Label(f, image=img, background="#051f38")
                ilbl.image = img
                ilbl.pack(side="left", padx=2)
            tkinter.Label(
                f, text=details.title, font=("Arial", 8, "bold"),
                fg="#80cbc4", background="#051f38"
            ).pack(side="left")

        if Blessing.MIRACLE in self.haunted.equipped_blessings and hasattr(self, "miracle_button"):
            action_btn_pad = int(6 * self.scale_factor)
            btn_pady = int(3 * self.scale_factor)
            self.miracle_button.grid(row=0, column=6, padx=action_btn_pad, pady=btn_pady)
            can_miracle = self.haunted.can_use_miracle_draw()
            self.miracle_button.configure(state="normal" if can_miracle else "disabled")

    def _apply_phase_theme(self, phase: Phase):
        """Applies atmospheric table felt darkening and infernal/celestial colors."""
        if phase == Phase.HELL_TABLE:
            bg_tbl = "#140508"
            bg_pnl = "#0d0204"
            fg_res = "#ff1744"
        elif phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
            if phase in (Phase.OMEN, Phase.SNUFFING):
                bg_tbl = "#142018"
                bg_pnl = "#142018"
            else:
                step = min(max(1, self.haunted.hand_counter - 6), 6)
                shades = ["#09521c", "#084718", "#073b14", "#062f10", "#05240c", "#142018"]
                p_shades = ["#063e15", "#053612", "#042c0e", "#03230b", "#031908", "#142018"]
                bg_tbl = shades[step - 1]
                bg_pnl = p_shades[step - 1]
            fg_res = "#ffeb3b"
        elif phase == Phase.VICTORY:
            bg_tbl = "#062b1a"
            bg_pnl = "#031b10"
            fg_res = "#00e5ff"
        else:
            bg_tbl = TABLE_BACKGROUND_COLOR
            bg_pnl = PANEL_BACKGROUND_COLOR
            fg_res = "#ffeb3b"

        self.root.configure(background=bg_tbl)
        if hasattr(self, "scoreboard_frame"):
            self.scoreboard_frame.configure(background=bg_tbl)
        if hasattr(self, "bankroll_label"):
            self.bankroll_label.configure(background=bg_tbl)
        if hasattr(self, "dealer_view_button"):
            self.dealer_view_button.configure(background=bg_pnl, activebackground=bg_tbl)
        if hasattr(self, "card_table_frame"):
            if isinstance(self.card_table_frame, TableFeltCanvas):
                if phase == Phase.NORMAL:
                    self.card_table_frame.set_theme("casino")
                elif phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
                    self.card_table_frame.set_theme("creep")
                elif phase == Phase.HELL_TABLE:
                    self.card_table_frame.set_theme("hell")
                elif phase == Phase.VICTORY:
                    self.card_table_frame.set_theme("celestial")
            self.card_table_frame.configure(background=bg_pnl)

        # Casino Score Plaque Theme Styling (Harmonized with phase panel felt and beveled metallic trim)
        plaque_bg = bg_pnl
        plaque_border = "#ff1744" if phase == Phase.HELL_TABLE else ("#00e5ff" if phase == Phase.VICTORY else "#d4af37")
        if hasattr(self, "dealer_header_frame"):
            self.dealer_header_frame.configure(background=plaque_bg, highlightbackground=plaque_border)
        if hasattr(self, "dealer_title_label"):
            self.dealer_title_label.configure(background=plaque_bg)
        if hasattr(self, "dealer_score_label"):
            self.dealer_score_label.configure(background=plaque_bg)
        if hasattr(self, "dealer_cards_frame"):
            self.dealer_cards_frame.configure(background=bg_pnl)
            for child in self.dealer_cards_frame.winfo_children():
                try:
                    child.configure(background=bg_pnl)
                except Exception:
                    pass

        # Theatrical Stage Horizon Background (Always Dark/Theatrical, never green)
        stage_bg = "#140508" if phase == Phase.HELL_TABLE else ("#0c2338" if phase == Phase.VICTORY else "#0a0a0a")
        if hasattr(self, "dealer_stage_frame"):
            self.dealer_stage_frame.configure(background=stage_bg)
        if hasattr(self, "dealer_stage_canvas"):
            self.dealer_stage_canvas.configure(background=stage_bg)
            if phase == Phase.NORMAL:
                self.dealer_stage_canvas.set_theme("casino")
            elif phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
                self.dealer_stage_canvas.set_theme("creep")
            elif phase == Phase.HELL_TABLE:
                self.dealer_stage_canvas.set_theme("hell")
            elif phase == Phase.VICTORY:
                self.dealer_stage_canvas.set_theme("celestial")
        if hasattr(self, "dealer_actor"):
            if phase == Phase.HELL_TABLE:
                self.dealer_actor.equip_costume("malphas")
            elif phase == Phase.VICTORY:
                self.dealer_actor.equip_costume("uriel")
            elif phase == Phase.NORMAL:
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)
        if hasattr(self, "dealer_panel"):
            self.dealer_panel.configure(background=stage_bg)
        if hasattr(self, "dealer_header_row"):
            self.dealer_header_row.configure(background=stage_bg)
        if hasattr(self, "dealer_actor_frame"):
            self.dealer_actor_frame.configure(background=stage_bg)

        # Theatrical Dealer Dialogue Frame (Dark Obsidian/Theme Palette)
        dialogue_bg = "#1c060a" if phase == Phase.HELL_TABLE else ("#0a1829" if phase == Phase.VICTORY else "#141014")
        speech_bg = "#240a10" if phase == Phase.HELL_TABLE else ("#0e2036" if phase == Phase.VICTORY else "#1c161c")
        if hasattr(self, "dealer_dialogue_frame"):
            self.dealer_dialogue_frame.configure(background=dialogue_bg)
        if hasattr(self, "dealer_nameplate_label"):
            nameplate_fg = "#ffd700"
            nameplate_text = "The Dealer"
            if phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
                nameplate_fg = "#ce93d8"
                nameplate_text = "The Dealer (Hollow)"
            elif phase == Phase.HELL_TABLE:
                nameplate_fg = "#ff1744"
                nameplate_text = "☠ The Pit Fiend"
            elif phase == Phase.VICTORY:
                nameplate_fg = "#00e5ff"
                nameplate_text = "✨ Celestial Messenger"
            self.dealer_nameplate_label.configure(background=dialogue_bg, fg=nameplate_fg, text=nameplate_text)
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.configure(background=speech_bg)
        if hasattr(self, "horizon_rail"):
            rail_bg = "#2d0a0d" if phase == Phase.HELL_TABLE else ("#06201b" if phase == Phase.VICTORY else ("#120914" if phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING) else "#073512"))
            self.horizon_rail.configure(background=rail_bg)
        if hasattr(self, "accessories_frame"):
            self.accessories_frame.configure(background=bg_pnl)
        if hasattr(self, "haunted_altar"):
            self.haunted_altar.set_theme_color(bg_pnl, is_hell_table=(phase == Phase.HELL_TABLE))
        if hasattr(self, "candle_bar_frame"):
            self.candle_bar_frame.configure(background=bg_pnl)
        if hasattr(self, "gravestones_frame"):
            self.gravestones_frame.configure(background=bg_pnl)
        if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
            try:
                self.card_table_frame.sync_children_felt()
            except Exception:
                pass
        if hasattr(self, "announcement_hud"):
            border_col = "#ff1744" if phase == Phase.HELL_TABLE else ("#00e5ff" if phase == Phase.VICTORY else None)
            self.announcement_hud.set_theme_color(bg_pnl, border_color=border_col)
        if hasattr(self, "player_header_frame"):
            self.player_header_frame.configure(background=plaque_bg, highlightbackground=plaque_border)
        if hasattr(self, "player_title_label"):
            self.player_title_label.configure(background=plaque_bg)
        if hasattr(self, "player_score_label"):
            self.player_score_label.configure(background=plaque_bg)
        if hasattr(self, "player_cards_frame"):
            self.player_cards_frame.configure(background=bg_pnl)
            for child in self.player_cards_frame.winfo_children():
                try:
                    child.configure(background=bg_pnl)
                    for sub in child.winfo_children():
                        try:
                            sub.configure(background=bg_pnl)
                        except Exception:
                            pass
                except Exception:
                    pass
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.configure(background=bg_pnl)
        if hasattr(self, "betting_frame"):
            self.betting_frame.configure(background=bg_tbl)
        if hasattr(self, "bet_chips_label"):
            self.bet_chips_label.configure(background=bg_tbl)
        if hasattr(self, "button_frame"):
            self.button_frame.configure(background=bg_tbl)
        if hasattr(self, "blessings_tray"):
            self.blessings_tray.configure(background=bg_tbl)
        if hasattr(self, "insurance_frame"):
            self.insurance_frame.configure(background=bg_pnl)
        if hasattr(self, "insurance_label"):
            self.insurance_label.configure(background=bg_pnl)
        if hasattr(self, "result_label"):
            self.result_label.configure(background=bg_tbl, fg=fg_res)
        if hasattr(self, "pumpkin_label"):
            self.pumpkin_label.configure(background=stage_bg)
        if hasattr(self, "dealer_avatar_label"):
            self.dealer_avatar_label.configure(background=stage_bg)
        if hasattr(self, "scale_button"):
            self.scale_button.configure(background=bg_pnl, activebackground=bg_tbl)
        if hasattr(self, "fullscreen_button"):
            self.fullscreen_button.configure(background=bg_pnl, activebackground=bg_tbl)
        if hasattr(self, "chips_mode_check"):
            self.chips_mode_check.configure(
                background=bg_tbl, activebackground=bg_tbl, selectcolor=bg_pnl
            )
        if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
            try:
                self.card_table_frame.sync_children_felt()
            except Exception:
                pass

    def _start_ambient_animations(self):
        """Starts non-blocking timer loop for flickering pumpkin and animated demonic eyes."""
        try:
            if self.root.state() == "withdrawn":
                return
        except Exception:
            return
        if self._ambient_timer_id is None:
            self._ambient_timer_id = self.root.after(600, self._tick_ambient_animations)

    def _tick_ambient_animations(self):
        """Ticks ambient animations non-blockingly."""
        self._ambient_timer_id = None
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return

        self._anim_frame_toggle = not self._anim_frame_toggle
        frame_idx = 1 if self._anim_frame_toggle else 0

        # 1. Flickering Pumpkin
        if hasattr(self, "pumpkin_label"):
            if self.haunted.phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING, Phase.HELL_TABLE):
                pack_kw = {"before": self.dealer_avatar_label} if hasattr(self, "dealer_avatar_label") and self.dealer_avatar_label.winfo_manager() == "pack" else {}
                self.pumpkin_label.pack(side="left", padx=(0, 6), pady=2, **pack_kw)
                p_img = self.haunted_assets.get(f"pumpkin_glow_{frame_idx}")
                if p_img:
                    self.pumpkin_label.configure(image=p_img)
                    self.pumpkin_label.image = p_img
            else:
                self.pumpkin_label.pack_forget()

        # Schedule next tick safely
        try:
            if self.root.winfo_exists() and self.root.state() != "withdrawn":
                self._ambient_timer_id = self.root.after(600, self._tick_ambient_animations)
        except Exception:
            pass

    def _trigger_hell_table(self):
        """Transitions into Hell's Table mode with bell audio, dialogs, and draft."""
        self.haunted.start_hell_table()
        self.sound_manager.play_haunted_sound("hell_bell")
        self._apply_phase_theme(Phase.HELL_TABLE)
        self._update_candles_display()
        self._update_gravestones_display()

        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.grid_remove()
        self.soul_meter_canvas.grid()
        self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=False)

        self.dealer_view_var.set(True)
        self._update_dealer_avatar()
        self.set_dealer_speech("Your soul is on the line now, mortal! The pit claims all.")
        self.sound_manager.play_haunted_sound("demon_reveal")

        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            self._open_angelic_draft()
            return

        def on_fiend_closed():
            self.sound_manager.play_haunted_sound("angel_chime")
            self._show_angel_dialog(on_close=self._open_angelic_draft)

        self._show_pit_fiend_dialog(on_close=on_fiend_closed)

    def _show_pit_fiend_dialog(self, on_close=None):
        """Displays atmospheric Pit Fiend narrative challenge."""
        text = (
            "Welcome to the Abyssal Wager, mortal.\n\n"
            "Your petty chips mean nothing here. The stakes are now your immortal Soul.\n\n"
            "Win hands to claw your way back to the light... Fail, and you belong to the Pit forever."
        )
        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("malphas", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("dealer_demon_0")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="☠ THE ABYSSAL WAGER ☠",
            speaker="☠ THE PIT FIEND ☠",
            portrait_img=port_img,
            text_content=text,
            button_text="Face Your Fate",
            on_close=on_close,
            is_celestial=False,
        )

    def _show_angel_dialog(self, on_close=None):
        """Displays Angelic messenger offering celestial intervention."""
        text = (
            "Be not afraid, mortal soul. The Heavens have witnessed this unholy trap.\n\n"
            "I grant you sacred blessings forged in celestial fire. Choose your relic wisely, "
            "and banish the Fiend with righteous hands."
        )
        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("uriel", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("angel_avatar")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="✦ CELESTIAL INTERVENTION ✦",
            speaker="✦ CELESTIAL MESSENGER ✦",
            portrait_img=port_img,
            text_content=text,
            button_text="Accept Divine Aid",
            on_close=on_close,
            is_celestial=True,
        )

    def _open_angelic_draft(self):
        """Opens Balatro-style Roguelike draft modal for celestial blessings."""
        choices = self.haunted.get_draft_choices(count=3)
        if not choices:
            return

        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            self.haunted.equip_blessing(choices[0])
            self._update_blessings_tray()
            return

        relic_map = {b.value: self.haunted_assets.get(f"relic_{b.value}") for b in choices}

        def on_drafted(b: Blessing):
            self.haunted.equip_blessing(b)
            self.sound_manager.play_haunted_sound("angel_chime")
            self._update_blessings_tray()
            self.result_var.set(f"✦ Relic Equipped: {BLESSING_REGISTRY[b].title}!")

        self._active_draft_dialog = AngelicDraftDialog(
            self.root, choices=choices, relic_icons=relic_map, on_select=on_drafted
        )

    def _show_victory_dialog(self):
        """Displays triumphant banishment dialogue and awards spoils."""
        self._apply_phase_theme(Phase.VICTORY)
        self.bankroll_var.set(self.bankroll_var.get() + 6666)
        if hasattr(self, "save_manager"):
            self.save_manager.unlock_achievement("exorcist")
            self.save_manager.record_bankroll(self.bankroll_var.get())
        if hasattr(self, "cursed_stakes_button"):
            s = self.scale_factor
            self.cursed_stakes_button.grid(row=0, column=8, padx=(int(6 * s), int(8 * s)), pady=int(3 * s), sticky="e")

        def on_victory_close():
            self.haunted.reset_after_victory()
            self._apply_phase_theme(Phase.NORMAL)
            self._candles_manifested = False
            if hasattr(self, "haunted_altar"):
                self.haunted_altar.set_gravestone_state(0, visible=False)
                self.haunted_altar.set_candle_state(0, visible=False)
                self.haunted_altar.pack_forget()
            if hasattr(self, "pumpkin_label"):
                self.pumpkin_label.pack_forget()
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.pack_forget()
            self._update_dealer_avatar()
            self.set_dealer_speech("✦ Darkness is banished! Peace returns to the table. ✦")
            self.result_var.set("VICTORY! +$6,666 Exorcist Bounty Claimed!")

        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            on_victory_close()
            return

        text = (
            "The Pit Fiend is banished back to the void! Your soul shines untarnished.\n\n"
            "The Heavens have bestowed upon you the EXORCIST title and +$6,666 casino bankroll.\n\n"
            "You have unlocked permanent Cursed Stakes mode at the bottom action bar!"
        )
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="✦ THE EXORCIST'S TRIUMPH ✦",
            speaker="✦ CELESTIAL MESSENGER ✦",
            portrait_img=self.haunted_assets.get("angel_avatar"),
            text_content=text,
            button_text="Return to Table",
            on_close=on_victory_close,
            is_celestial=True,
        )

    def _show_defeat_dialog(self):
        """Displays defeat dialogue with choice to retry Hell's Table or flee."""
        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            self.haunted.second_chance()
            self.new_game()
            return

        text = (
            "Your soul is claimed! Dragged down into the suffocating abyss...\n\n"
            "Yet the House of Damnation is ever insatiable. Will you stake your next life "
            "for another chance at redemption?"
        )

        def on_retry():
            self.haunted.second_chance()
            self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=False)
            self.new_game()

        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("malphas", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("dealer_demon_0")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="☠ SOUL FORFEIT ☠",
            speaker="☠ THE PIT FIEND ☠",
            portrait_img=port_img,
            text_content=text,
            button_text="Second Chance (25% Soul)",
            on_close=on_retry,
            is_celestial=False,
        )

    def _on_miracle_draw(self):
        """Miracle Draw: banishes the last dealt player card and draws a fresh one."""
        if not self.haunted.can_use_miracle_draw():
            return
        if not self.player_hand:
            return

        self.haunted.use_miracle_draw()
        self.sound_manager.play_haunted_sound("angel_chime")

        self.player_hand.pop()
        self._deal_card_to_player(self.active_hand_index)
        self.result_var.set("🌟 Miracle Draw invoked! Card banished and redrawn.")
        if hasattr(self, "miracle_button"):
            self.miracle_button.configure(state="disabled")

    def _on_toggle_cursed_stakes(self):
        """Manually launches Hell's Table mode for replayability."""
        self._trigger_hell_table()
        self.new_game()

    # ------------------------------------------------------------------------
    # Game Flow & Actions
    # ------------------------------------------------------------------------

    def _update_shoe_display(self):
        """Updates the shoe cards remaining label text."""
        if hasattr(self, "shoe_info_var"):
            total = len(self.all_cards) * self.deck_count
            remaining = len(self.deck)
            cut_notice = " [Cut]" if self.shoe_needs_reshuffle else ""
            self.shoe_info_var.set(f"Shoe: {remaining}/{total}{cut_notice}")

    def _update_action_buttons(self):
        """Evaluates and applies eligibility for Hit, Stand, Double, Split, and Surrender."""
        if not self.player_hands or self.active_hand_index >= len(self.player_hands):
            self._set_action_buttons_state("disabled")
            return

        hand = self.player_hands[self.active_hand_index]
        score = self._score_player_hand(hand)

        if score >= BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            return

        # Hit & Stand are available for active hand
        self.hit_button.configure(state="normal")
        self.stand_button.configure(state="normal")

        # Double Down: exactly 2 cards in current hand, and sufficient bankroll if in Chips Mode
        can_double = (len(hand) == 2)
        if can_double and self.chips_mode_var.get() and self.hand_bets:
            current_bet = self.hand_bets[self.active_hand_index] if self.active_hand_index < len(self.hand_bets) else 0
            can_double = (self.bankroll_var.get() >= current_bet and current_bet > 0)
        self.double_button.configure(state="normal" if can_double else "disabled")

        # Split: only on initial 2 cards of non-split hand, matching rank, and sufficient bankroll
        can_sp = (len(self.player_hands) == 1 and can_split(self.player_hands[0]))
        if can_sp and self.chips_mode_var.get() and self.hand_bets:
            can_sp = (self.bankroll_var.get() >= self.hand_bets[0])
        self.split_button.configure(state="normal" if can_sp else "disabled")

        # Surrender: only on initial 2 cards of non-split hand (before any hit, double, or split)
        can_surr = (len(self.player_hands) == 1 and len(self.player_hands[0]) == 2)
        self.surrender_button.configure(state="normal" if can_surr else "disabled")

    def new_game(self):
        """Starts a fresh round of Blackjack or enters betting phase depending on Chips Mode."""
        # 0. Cancel any active dealer timer from a prior round
        if self._dealer_timer_id:
            try:
                self.root.after_cancel(self._dealer_timer_id)
            except Exception:
                pass
            self._dealer_timer_id = None
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.clear_timers()
        if hasattr(self, "announcement_hud"):
            self.announcement_hud.dismiss()

        # 1. Reset deck/shoe and hands
        if not self.deck or self.shoe_needs_reshuffle or len(self.deck) < 15:
            self.deck = build_shoe(self.all_cards, self.deck_count)
            self.shoe_needs_reshuffle = False
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_card_shuffle()

        self._update_shoe_display()
        self.player_hands = [[]]
        self.active_hand_index = 0
        self.dealer_hand.clear()
        self.dealer_hole_card = None
        self.dealer_hole_widget = None
        self.is_hole_card_hidden = False

        # 2. Clear card visuals from frames and unmap them to keep table felt clean during betting
        for child in self.dealer_cards_frame.winfo_children():
            child.destroy()
        for child in self.player_cards_frame.winfo_children():
            child.destroy()
        self.dealer_cards_frame.grid_remove()
        self.player_cards_frame.grid_remove()


        # 3. Reset scores and status
        self.dealer_score_var.set("0")
        self.player_score_var.set("0")
        self.result_var.set("")
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.is_insurance_phase = False
        if hasattr(self, "insurance_frame"):
            self.insurance_frame.grid_remove()

        # Haunted progression & table synchronization
        phase = self.haunted.on_new_hand()
        self._apply_phase_theme(phase)
        self._update_dealer_avatar()
        if hasattr(self, "dealer_actor"):
            self._restore_dealer_arms()
            self._restore_dealer_mouth()
        self.clear_dealer_speech()
        self._update_candles_display()
        self._update_gravestones_display()
        self._update_blessings_tray()

        if self.haunted.phase == Phase.HELL_TABLE:
            self.is_betting_phase = False
            self._start_round_deal()
        elif self.chips_mode_var.get():
            self._enter_betting_phase()
        else:
            self.is_betting_phase = False
            self._start_round_deal()

    def _enter_betting_phase(self):
        """Transitions game state into the betting phase where player places chips."""
        self.is_betting_phase = True
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")

        bankroll = self.bankroll_var.get()
        if bankroll < MINIMUM_BET and self.current_bet_var.get() < MINIMUM_BET:
            self.current_bet_var.set(0)
            self.result_var.set("Bankroll empty! Click Rebuy ($1,000) to keep playing.")
        else:
            # Default staged bet: preserve previous bet if affordable, or MINIMUM_BET
            if self.current_bet_var.get() == 0 or self.current_bet_var.get() > bankroll:
                if self.hand_bets and 0 < self.hand_bets[0] <= bankroll:
                    self.current_bet_var.set(self.hand_bets[0])
                elif bankroll >= MINIMUM_BET:
                    self.current_bet_var.set(MINIMUM_BET)
                else:
                    self.current_bet_var.set(0)
            self.result_var.set("Place your bet and click 'Deal Hand'")

        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.set_bet(self.current_bet_var.get(), animate=False)

        self._update_bankroll_display()
        self._update_betting_controls()

    def _start_round_deal(self):
        """Authentic initial deal: 2 cards to player, 2 to dealer (1 face-down hole card)."""
        self.result_var.set("")
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        if hasattr(self, "insurance_frame"):
            self.insurance_frame.grid_remove()

        if self.chips_mode_var.get():
            self._update_betting_controls()

        # Player gets 2 cards face-up
        self._deal_card_to_player(hand_index=0)
        self._deal_card_to_player(hand_index=0)

        # Dealer gets 1 card face-up and 1 card face-down (the hole card)
        self._deal_card_to_dealer(is_hole_card=False)
        self._deal_card_to_dealer(is_hole_card=True)

        # Check if player immediately busted on deal (e.g. Cursed Card 13)
        player_score = self._score_player_hand(self.player_hands[0])
        if player_score > BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            self._reveal_dealer_hole_card()
            self._conclude_round()
            return

        # Check for Insurance (Dealer upcard is Ace in Chips Mode)
        dealer_upcard = self.dealer_hand[0]
        is_ace = getattr(dealer_upcard, "rank", "") == "ace" or (isinstance(dealer_upcard, (tuple, list)) and dealer_upcard[0] == 1)
        if self.chips_mode_var.get() and is_ace:
            self._prompt_insurance()
        else:
            # Check for Natural Blackjack and Action eligibility
            self._check_initial_blackjack()

    def _on_toggle_chips_mode(self, confirm: bool = None):
        """Handles switching between Casual Mode (Chips OFF) and Casino Mode (Chips ON)."""
        if self.chips_mode_var.get():
            self.save_manager.set_chips_mode(True)
            # Chips Mode activated: reset bankroll to starting $1,000 as per policy
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.hand_bets = [0]
            self.bankroll_label.grid()
            self.betting_frame.grid()
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid()
                self.chip_visualizer.set_bet(0, animate=False)
                if hasattr(self, "card_table_frame"):
                    self.card_table_frame.sync_children_felt()
            self._update_bankroll_display()
            self.new_game()
        else:
            # Chips Mode deactivated: confirm forfeit of bankroll
            if confirm is None:
                # In headless test environments or withdrawn root, auto-confirm without modal popup
                is_headless = getattr(self, "suppress_mode_dialog", False)
                try:
                    is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
                except Exception:
                    is_withdrawn = True

                if is_headless or is_withdrawn:
                    confirm = True
                else:
                    try:
                        import tkinter.messagebox as messagebox
                        confirm = messagebox.askyesno(
                            "Exit Chips Mode?",
                            "Leaving Chips Mode will forfeit your current bankroll progress and any active wagers.\n\n"
                            f"Returning to Chips Mode later will reset your bankroll to the starting ${STARTING_BANKROLL:,}.\n\n"
                            "Do you want to switch to Casual Mode?"
                        )
                    except Exception:
                        confirm = True

            if not confirm:
                # User cancelled: keep Chips Mode ON
                self.chips_mode_var.set(True)
                return

            self.save_manager.set_chips_mode(False)
            # User confirmed: reset bankroll to starting $1,000 and clear chips state
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.hand_bets = [0]
            self.bankroll_label.grid_remove()
            self.betting_frame.grid_remove()
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid_remove()
                self.chip_visualizer.clear_timers()
            if hasattr(self, "insurance_frame"):
                self.insurance_frame.grid_remove()
            self.last_insurance_lost = 0
            self.is_insurance_phase = False
            self.insurance_bet = 0
            self.is_betting_phase = False
            self.new_game()

    def _add_chip_bet(self, amount: int):
        """Adds chip amount to the staged bet, bounded by available bankroll."""
        if not self.is_betting_phase:
            return
        current_bet = self.current_bet_var.get()
        bankroll = self.bankroll_var.get()
        if current_bet + amount <= bankroll:
            new_bet = current_bet + amount
            self.current_bet_var.set(new_bet)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.animate_chip_drop(amount, new_bet)
            self._update_bankroll_display()
            self._update_betting_controls()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

    def _clear_bet(self):
        """Resets the staged bet back to 0."""
        if not self.is_betting_phase:
            return
        self.current_bet_var.set(0)
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.animate_clear()
        self._update_bankroll_display()
        self._update_betting_controls()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_chip_clear()

    def _all_in(self):
        """Sets the staged bet to the player's full remaining bankroll."""
        if not self.is_betting_phase:
            return
        bankroll = self.bankroll_var.get()
        if bankroll >= MINIMUM_BET:
            self.current_bet_var.set(bankroll)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.set_bet(bankroll, animate=False)
            self._update_bankroll_display()
            self._update_betting_controls()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_stack()

    def _deal_hand_with_bet(self):
        """Commits the staged bet, deducts it from bankroll, and begins the deal."""
        if not self.is_betting_phase:
            return
        bet = self.current_bet_var.get()
        bankroll = self.bankroll_var.get()
        if bet < MINIMUM_BET or bet > bankroll:
            return
        self.bankroll_var.set(bankroll - bet)
        self.hand_bets = [bet]
        self.is_betting_phase = False
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.set_bet(bet, animate=False)
        self._update_bankroll_display()
        self._update_betting_controls()
        self._start_round_deal()

    def _rebuy(self):
        """Replenishes player bankroll if it drops below the minimum bet."""
        if self.bankroll_var.get() < MINIMUM_BET and self.current_bet_var.get() < MINIMUM_BET:
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.result_var.set("Bankroll replenished to $1,000! Place your bet.")
            self._update_bankroll_display()
            self._update_betting_controls()

    def _update_bankroll_display(self):
        """Updates the bankroll & bet label text."""
        if not hasattr(self, "bankroll_label"):
            return
        bankroll = self.bankroll_var.get()
        bet = self.current_bet_var.get() if self.is_betting_phase else sum(self.hand_bets)
        self.bankroll_label.configure(
            text=f"Bankroll: ${bankroll:,}  |  Bet: ${bet:,}"
        )

    def _update_betting_controls(self):
        """Updates states of chip buttons, clear bet, deal, and rebuy buttons."""
        if not self.chips_mode_var.get() or not hasattr(self, "chip_buttons") or not self.chip_buttons:
            return

        bankroll = self.bankroll_var.get()
        staged_bet = self.current_bet_var.get()
        remaining = bankroll - staged_bet

        if self.is_betting_phase:
            for btn, (denom, _, _) in zip(self.chip_buttons, CHIP_DENOMINATIONS):
                btn.configure(state="normal" if remaining >= denom else "disabled")
            if hasattr(self, "all_in_button"):
                self.all_in_button.configure(state="normal" if bankroll >= MINIMUM_BET and staged_bet < bankroll else "disabled")
            self.clear_bet_button.configure(state="normal" if staged_bet > 0 else "disabled")
            self.deal_bet_button.configure(state="normal" if staged_bet >= MINIMUM_BET else "disabled")
            if bankroll < MINIMUM_BET and staged_bet < MINIMUM_BET:
                self.rebuy_button.configure(state="normal")
            else:
                self.rebuy_button.configure(state="disabled")
        else:
            # During active card play or dealer turn, betting controls are disabled
            for btn in self.chip_buttons:
                btn.configure(state="disabled")
            if hasattr(self, "all_in_button"):
                self.all_in_button.configure(state="disabled")
            self.clear_bet_button.configure(state="disabled")
            self.deal_bet_button.configure(state="disabled")
            self.rebuy_button.configure(state="disabled")

    def _prompt_insurance(self):
        """Offers the insurance side bet when the dealer shows an Ace in Chips Mode."""
        self.is_insurance_phase = True
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")

        main_bet = self.hand_bets[0] if self.hand_bets else 0
        insurance_cost = main_bet // 2
        bankroll = self.bankroll_var.get()
        can_afford = (bankroll >= insurance_cost and insurance_cost >= 1)

        self.take_insurance_button.configure(
            text=f"Take Insurance (${insurance_cost})",
            state="normal" if can_afford else "disabled"
        )
        self.result_var.set("Dealer shows an Ace. Take insurance?")
        self.insurance_frame.grid()

    def _on_take_insurance(self):
        """Handles player taking insurance."""
        if not self.is_insurance_phase:
            return
        main_bet = self.hand_bets[0] if self.hand_bets else 0
        insurance_cost = main_bet // 2
        if self.bankroll_var.get() < insurance_cost or insurance_cost < 1:
            return

        self.bankroll_var.set(self.bankroll_var.get() - insurance_cost)
        self.insurance_bet = insurance_cost
        self._update_bankroll_display()
        self._resolve_insurance_decision()

    def _on_decline_insurance(self):
        """Handles player declining insurance."""
        if not self.is_insurance_phase:
            return
        self.insurance_bet = 0
        self._resolve_insurance_decision()

    def _resolve_insurance_decision(self):
        """Concludes insurance phase, peeks at dealer hole card, and resolves or resumes play."""
        self.is_insurance_phase = False
        self.insurance_frame.grid_remove()

        dealer_score = score_hand(self.dealer_hand)
        dealer_has_bj = (len(self.dealer_hand) == 2 and dealer_score == BLACKJACK_TARGET)

        if dealer_has_bj:
            # Dealer has Natural Blackjack
            if self.insurance_bet > 0:
                main_bet = self.hand_bets[0] if self.hand_bets else 0
                payout = calculate_insurance_payout(True, self.insurance_bet, main_bet=main_bet)
                self.bankroll_var.set(self.bankroll_var.get() + payout)
                self._update_bankroll_display()
            self._reveal_dealer_hole_card()
            self._conclude_round()
        else:
            # Dealer does not have Blackjack
            if self.insurance_bet > 0:
                lost_amount = self.insurance_bet
                self.last_insurance_lost = lost_amount
                self.insurance_bet = 0  # Insurance lost
                self.result_var.set(f"Dealer has no Blackjack. Insurance lost (-${lost_amount}). Your turn!")
            else:
                self.result_var.set("")

            # Check if player has Natural Blackjack or bust
            player_score = self._score_player_hand(self.player_hands[0])
            if player_score >= BLACKJACK_TARGET:
                self._reveal_dealer_hole_card()
                self._conclude_round()
            else:
                # Normal player turn: action buttons evaluated dynamically
                self._update_action_buttons()

    def _draw_card(self):
        """Pops the next card from the shoe, marking cut card if penetration threshold reached."""
        if not self.deck:
            self.deck = build_shoe(self.all_cards, self.deck_count)
            self.shoe_needs_reshuffle = False

        card = self.deck.pop()
        total_shoe_cards = len(self.all_cards) * self.deck_count
        if len(self.deck) <= int(total_shoe_cards * CUT_CARD_PENETRATION):
            self.shoe_needs_reshuffle = True

        self._update_shoe_display()

        # In Hell's Table, transform face cards to animated demonic editions
        if getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE:
            rank = getattr(card, "rank", "")
            if rank in ("jack", "queen", "king"):
                haunted_img = self.haunted_assets.get(f"{rank}_haunted_0")
                if haunted_img:
                    card = Card(card.value, haunted_img, rank=rank, suit=card.suit)

        return card

    def _deal_card_to_player(self, hand_index=None):
        """Deals one card to the active player hand and updates visuals."""
        if hand_index is None:
            hand_index = self.active_hand_index

        # Hand 13 Omen injection check
        if getattr(self, "haunted", None) and self.haunted.phase == Phase.OMEN and len(self.player_hands[hand_index]) == 1 and self.card_13:
            card = self.card_13
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("clock_chime_13")
            self.result_var.set("The clock strikes 13... The 13 of Skulls is dealt!")
        else:
            card = self._draw_card()

        self.player_hands[hand_index].append(card)
        self._render_player_cards()
        self._update_player_score_display()
        if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
            self._trigger_dealer_deal_gesture()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_card_deal()

    def _get_or_create_dealer_cards_container(self, bg_pnl: str) -> tkinter.Frame:
        """Returns or creates the centered container for dealer cards."""
        self.dealer_cards_frame.grid()
        if not hasattr(self, "_dealer_cards_container") or not self._dealer_cards_container.winfo_exists():
            self._dealer_cards_container = tkinter.Frame(self.dealer_cards_frame, background=bg_pnl)
            self._dealer_cards_container.pack(anchor="center")
        return self._dealer_cards_container

    def _deal_card_to_dealer(self, is_hole_card=False):
        """
        Deals one card to the dealer.
        If `is_hole_card` is True, renders `back.png` and hides its score until Stand.
        """
        card = self._draw_card()
        self.dealer_hand.append(card)
        if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
            self._trigger_dealer_deal_gesture()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_card_deal()

        bg_pnl = self.card_table_frame["background"] if hasattr(self, "card_table_frame") else PANEL_BACKGROUND_COLOR
        container = self._get_or_create_dealer_cards_container(bg_pnl)
        padx = int(2 * self.scale_factor)

        if is_hole_card:
            # Face-down hole card
            self.dealer_hole_card = card
            self.is_hole_card_hidden = True
            if getattr(self, "haunted", None) and Blessing.EYE in self.haunted.equipped_blessings:
                # Eye of Providence Blessing reveals hole card immediately in halo!
                self.dealer_hole_widget = tkinter.Label(
                    container, image=card[1],
                    relief="solid", borderwidth=1, highlightthickness=1,
                    highlightbackground="#00e5ff", background=bg_pnl
                )
                self.dealer_hole_widget.pack(side="left", padx=padx)
                self.dealer_score_var.set(f"{score_hand(self.dealer_hand)} (Revealed)")
            else:
                back_img = self.haunted_assets.get("back_haunted") if (getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE) else self.back_image
                self.dealer_hole_widget = tkinter.Label(
                    container, image=back_img or self.back_image,
                    relief="flat", borderwidth=0, highlightthickness=0,
                    background=bg_pnl
                )
                self.dealer_hole_widget.pack(side="left", padx=padx)
                upcard_score = score_hand([self.dealer_hand[0]])
                self.dealer_score_var.set(f"{upcard_score} + ?")
        else:
            # Face-up card
            tkinter.Label(
                container, image=card[1],
                relief="flat", borderwidth=0, highlightthickness=0,
                background=bg_pnl
            ).pack(side="left", padx=padx)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))

    def _render_dealer_cards(self):
        """Renders visual card labels for dealer hand centered according to current scale factor."""
        for child in self.dealer_cards_frame.winfo_children():
            child.destroy()
        if hasattr(self, "_dealer_cards_container"):
            delattr(self, "_dealer_cards_container")

        bg_pnl = self.card_table_frame["background"] if hasattr(self, "card_table_frame") else PANEL_BACKGROUND_COLOR
        padx = int(2 * self.scale_factor)

        num_cards = len(self.dealer_hand)
        if num_cards == 0:
            self.dealer_cards_frame.configure(width=1, height=1)
            self.dealer_cards_frame.grid_remove()
            try:
                self.dealer_cards_frame.place(x=0, y=0, width=1, height=1)
                self.root.update_idletasks()
                self.dealer_cards_frame.place_forget()
            except Exception:
                pass
            return
        self.dealer_cards_frame.grid()
        container = self._get_or_create_dealer_cards_container(bg_pnl)

        if num_cards > 4:
            # Overlapping layout for 5+ cards to prevent table felt overflow
            card_w = getattr(self, "card_width", CARD_WIDTH)
            card_h = getattr(self, "card_height", CARD_HEIGHT)
            overlap = self._calculate_hand_overlap(num_cards, is_split=False)
            frame_width = card_w + (num_cards - 1) * overlap
            container.configure(width=frame_width, height=card_h)
            container.pack_propagate(False)
            for i, card in enumerate(self.dealer_hand):
                if i == 1 and getattr(self, "is_hole_card_hidden", False):
                    back_img = self.haunted_assets.get("back_haunted") if (getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE) else self.back_image
                    self.dealer_hole_widget = tkinter.Label(
                        container, image=back_img or self.back_image,
                        relief="flat", borderwidth=0, highlightthickness=0,
                        background=bg_pnl
                    )
                    self.dealer_hole_widget.place(x=i * overlap, y=0, width=card_w, height=card_h)
                else:
                    lbl = tkinter.Label(
                        container, image=card[1],
                        relief="flat", borderwidth=0, highlightthickness=0,
                        background=bg_pnl
                    )
                    lbl.place(x=i * overlap, y=0, width=card_w, height=card_h)
                    if i == 1 and not getattr(self, "is_hole_card_hidden", False):
                        self.dealer_hole_widget = lbl
        else:
            container.pack_propagate(True)
            for i, card in enumerate(self.dealer_hand):
                if i == 1 and getattr(self, "is_hole_card_hidden", False):
                    # Hole card face down (or revealed with halo by Eye of Providence)
                    if getattr(self, "haunted", None) and Blessing.EYE in self.haunted.equipped_blessings:
                        self.dealer_hole_widget = tkinter.Label(
                            container, image=card[1],
                            relief="solid", borderwidth=1, highlightthickness=1,
                            highlightbackground="#00e5ff", background=bg_pnl
                        )
                        self.dealer_hole_widget.pack(side="left", padx=padx)
                    else:
                        back_img = self.haunted_assets.get("back_haunted") if (getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE) else self.back_image
                        self.dealer_hole_widget = tkinter.Label(
                            container, image=back_img or self.back_image,
                            relief="flat", borderwidth=0, highlightthickness=0,
                            background=bg_pnl
                        )
                        self.dealer_hole_widget.pack(side="left", padx=padx)
                else:
                    lbl = tkinter.Label(
                        container, image=card[1],
                        relief="flat", borderwidth=0, highlightthickness=0,
                        background=bg_pnl
                    )
                    lbl.pack(side="left", padx=padx)
                    if i == 1 and not getattr(self, "is_hole_card_hidden", False):
                        self.dealer_hole_widget = lbl

    def _calculate_hand_overlap(self, num_cards: int, is_split: bool) -> int:
        """Dynamically compresses card overlap offset when hand has many cards to prevent right-edge overflow."""
        base_overlap = getattr(self, "card_overlap_offset", PLAYER_CARD_OVERLAP_OFFSET)
        if num_cards <= 4:
            return base_overlap
        # For hands with 5+ cards, compress overlap dynamically to prevent table overflow
        factor = 0.7 if is_split else 0.85
        compressed = int(base_overlap * (factor ** (num_cards - 4)))
        min_overlap = int(12 * self.scale_factor)
        return max(min_overlap, compressed)

    def _render_player_cards(self):
        """Renders visual card labels and hand frames for player hand(s) centered on table felt."""
        for child in self.player_cards_frame.winfo_children():
            child.destroy()

        if not any(len(h) > 0 for h in self.player_hands):
            self.player_cards_frame.configure(width=1, height=1)
            self.player_cards_frame.grid_remove()
            try:
                self.player_cards_frame.place(x=0, y=0, width=1, height=1)
                self.root.update_idletasks()
                self.player_cards_frame.place_forget()
            except Exception:
                pass
            return

        self.player_cards_frame.grid()
        is_split = len(self.player_hands) > 1
        bg_pnl = self.card_table_frame["background"] if hasattr(self, "card_table_frame") else PANEL_BACKGROUND_COLOR

        player_container = tkinter.Frame(self.player_cards_frame, background=bg_pnl)

        player_container.pack(anchor="center")

        for idx, hand in enumerate(self.player_hands):
            is_active = (idx == self.active_hand_index)
            container = tkinter.Frame(
                player_container,
                background=bg_pnl,
                padx=6,
                pady=4,
                relief="groove" if is_split else "flat",
                borderwidth=2 if is_split else 0
            )
            container.pack(side="left", padx=10 if is_split else 0)

            if is_split:
                status_suffix = " (Active)" if is_active else ""
                title = f"Hand {idx + 1}{status_suffix}"
                fg_color = "#ffeb3b" if is_active else "#cfd8dc"
                tkinter.Label(
                    container, text=title, font=("Arial", 9, "bold"),
                    background=bg_pnl, fg=fg_color
                ).pack(anchor="w", pady=(0, 2))

            num_cards = len(hand)
            card_w = getattr(self, "card_width", CARD_WIDTH)
            card_h = getattr(self, "card_height", CARD_HEIGHT)
            available_h = self.card_table_frame.winfo_height() if hasattr(self, "card_table_frame") else 0
            if available_h > 40 and available_h < (card_h * 2 + 10):
                card_h = max(36, (available_h - 14) // 2)
                card_w = max(24, int(card_h * (CARD_WIDTH / CARD_HEIGHT)))
            overlap = self._calculate_hand_overlap(num_cards, is_split)

            if num_cards == 0:
                frame_width = card_w
            else:
                frame_width = card_w + (num_cards - 1) * overlap

            cards_frame = tkinter.Frame(
                container, background=bg_pnl,
                width=frame_width, height=card_h
            )
            cards_frame.pack(side="top")
            cards_frame.pack_propagate(False)

            for i, card in enumerate(hand):
                lbl = tkinter.Label(
                    cards_frame, image=card[1],
                    relief="flat", borderwidth=0, highlightthickness=0,
                    background=bg_pnl
                )
                lbl.place(x=i * overlap, y=0, width=card_w, height=card_h)

    def _update_player_score_display(self):
        """Updates the reactive player score variable."""
        if len(self.player_hands) == 1:
            self.player_score_var.set(str(self._score_player_hand(self.player_hands[0])))
        else:
            scores = [str(self._score_player_hand(h)) for h in self.player_hands]
            self.player_score_var.set(f"H1: {scores[0]} | H2: {scores[1]}")

    def _check_initial_blackjack(self):
        """
        Inspects hands immediately after initial deal for Natural Blackjacks (21 on 2 cards)
        or immediate busts (e.g., cursed 13 card).
        Resolves immediately if either player or dealer has 21, or if player has busted.
        Otherwise, configures action buttons (Hit, Stand, Double, Split, Surrender).
        """
        player_score = self._score_player_hand(self.player_hands[0])
        dealer_score = score_hand(self.dealer_hand)
        if self.dealer_hand and self.dealer_hand[0][0] in (1, 10):
            if hasattr(self, "dealer_actor") and self.root.winfo_exists():
                self._trigger_dealer_peek_gesture()
        if player_score >= BLACKJACK_TARGET or dealer_score >= BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            self._reveal_dealer_hole_card()
            self._conclude_round()
        else:
            self._update_action_buttons()

    def _reveal_dealer_hole_card(self):
        """Flips the dealer's hole card face-up and displays the full dealer score."""
        self.is_hole_card_hidden = False
        if self.dealer_hole_widget and self.dealer_hole_card:
            self.dealer_hole_widget.configure(image=self.dealer_hole_card[1], relief="flat", borderwidth=0, highlightthickness=0)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_card_place()

    def on_split(self):
        """
        Handles the 'Split' action. Separates the initial two matching cards
        into two independent hands and deals one card to each.
        In Chips Mode, requires and deducts a matching wager for the second hand.
        """
        if not can_split(self.player_hands[0]):
            return

        if self.chips_mode_var.get():
            hand1_bet = self.hand_bets[0] if self.hand_bets else 0
            if self.bankroll_var.get() < hand1_bet:
                return  # Insufficient funds to match bet
            self.bankroll_var.set(self.bankroll_var.get() - hand1_bet)
            self.hand_bets.append(hand1_bet)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.set_bet(sum(self.hand_bets), animate=False)
            self._update_bankroll_display()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

        # 1. Separate into two hands
        card1 = self.player_hands[0][0]
        card2 = self.player_hands[0][1]
        self.player_hands = [[card1], [card2]]
        self.active_hand_index = 0

        # 2. Deal second card to both Hand 1 and Hand 2
        self._deal_card_to_player(hand_index=0)
        self._deal_card_to_player(hand_index=1)

        # 3. Update action buttons for Hand 1 (Double Down available on 2 cards if eligible)
        self._update_action_buttons()

        # 4. Check if Hand 1 reached 21 on the deal
        if score_hand(self.player_hands[0]) == BLACKJACK_TARGET:
            self.on_stand()

    def on_double_down(self):
        """
        Handles the 'Double' player action.
        Doubles the wager on the active hand, deals exactly 1 card, and automatically stands (or busts).
        """
        hand = self.player_hands[self.active_hand_index]
        if len(hand) != 2:
            return

        if self.chips_mode_var.get() and self.hand_bets:
            current_bet = self.hand_bets[self.active_hand_index]
            if self.bankroll_var.get() < current_bet:
                return  # Cannot afford double
            self.bankroll_var.set(self.bankroll_var.get() - current_bet)
            self.hand_bets[self.active_hand_index] += current_bet
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.animate_chip_drop(current_bet, sum(self.hand_bets))
            self._update_bankroll_display()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

        # Mark double flag for Hell's Table scoring calculations
        self._last_was_double = True

        # Disable double, split, and surrender buttons immediately
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")

        # Deal exactly 1 card
        self._deal_card_to_player()
        score = self._score_player_hand(self.player_hands[self.active_hand_index])

        if score > BLACKJACK_TARGET:
            # Busted on double down
            if self.active_hand_index < len(self.player_hands) - 1:
                # Advance to next split hand
                self.active_hand_index += 1
                self.result_var.set("Hand 1 busted on Double! Playing Hand 2...")
                self._render_player_cards()
                self._update_player_score_display()
                self._update_action_buttons()
                if self._score_player_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                    self.on_stand()
            else:
                all_busted = all(self._score_player_hand(h) > BLACKJACK_TARGET for h in self.player_hands)
                if all_busted:
                    self._reveal_dealer_hole_card()
                    self._conclude_round()
                else:
                    self._set_action_buttons_state("disabled")
                    self.new_game_button.configure(state="disabled")
                    self._reveal_dealer_hole_card()
                    self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        else:
            # Automatically stand after receiving exactly one card
            self.on_stand()

    def on_surrender(self):
        """
        Handles the 'Surrender' player action (Late Surrender).
        Forfeits the hand after dealer checks for Blackjack, recovering 50% of the initial bet.
        """
        if len(self.player_hands) != 1 or len(self.player_hands[0]) != 2:
            return

        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")
        self._reveal_dealer_hole_card()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_surrender()

        if self.chips_mode_var.get() and self.hand_bets:
            bet = self.hand_bets[0]
            refund = bet // 2
            loss = bet - refund
            self.bankroll_var.set(self.bankroll_var.get() + refund)
            self._update_bankroll_display()
            self._record_outcome('DEALER_WINS')
            self.result_var.set(f"Surrendered. Half bet returned (${refund:,}). (-${loss:,})")
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.animate_loss()
            self._update_betting_controls()
        else:
            self._record_outcome('DEALER_WINS')
            self.result_var.set("Surrendered. Hand forfeited.")

        self.new_game_button.configure(state="normal")

    def on_hit(self):
        """
        Handles the 'Hit' player action.
        Deals a card to the currently active hand, checks for bust or 21.
        """
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")
        self._deal_card_to_player()
        current_hand = self.player_hands[self.active_hand_index]
        current_score = self._score_player_hand(current_hand)

        if current_score > BLACKJACK_TARGET:
            # Current hand busted!
            if self.active_hand_index < len(self.player_hands) - 1:
                # Move to next split hand
                self.active_hand_index += 1
                self.result_var.set("Hand 1 busted! Playing Hand 2...")
                self._render_player_cards()
                self._update_player_score_display()
                self._update_action_buttons()
                if self._score_player_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                    self.on_stand()
            else:
                # Final hand has completed (busted)
                all_busted = all(self._score_player_hand(h) > BLACKJACK_TARGET for h in self.player_hands)
                if all_busted:
                    self._reveal_dealer_hole_card()
                    self._conclude_round()
                else:
                    # At least one earlier hand is still in play; dealer plays
                    self._set_action_buttons_state("disabled")
                    self.new_game_button.configure(state="disabled")
                    self._reveal_dealer_hole_card()
                    self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        elif current_score == BLACKJACK_TARGET:
            self.on_stand()
        else:
            self._update_action_buttons()

    def on_stand(self):
        """
        Handles the 'Stand' player action.
        If playing split hands and Hand 1 stands, advances to Hand 2.
        Once all player hands have stood, begins dealer turn.
        """
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")

        if self.active_hand_index < len(self.player_hands) - 1:
            # Advance to Hand 2
            self.active_hand_index += 1
            self._render_player_cards()
            self._update_player_score_display()
            self._update_action_buttons()
            if score_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                self.on_stand()
            return

        # All player hands completed -> transition to dealer turn
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")
        self._reveal_dealer_hole_card()
        self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)

    def _dealer_step(self):
        """
        Non-blocking recursive timer step for dealer draws.

        How it works:
        - Check if the dealer needs another card (< 17).
        - If YES: deals one card and reschedules itself via `root.after()`.
          Control immediately returns to the Tkinter event loop, keeping the UI responsive.
        - If NO: concludes the round and awards wins.
        """
        self._dealer_timer_id = None

        # Guard against window close during active callback
        if not self.root.winfo_exists():
            return

        if dealer_should_hit(self.dealer_hand):
            # Dealer must draw
            card = self._draw_card()
            self.dealer_hand.append(card)
            self._render_dealer_cards()
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_card_deal()

            # Schedule the next dealer step after the delay
            self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        else:
            # Dealer stands or busts; conclude round
            self._conclude_round()

    def _conclude_round(self):
        """Determines the winner for all player hands, updates win counters, resolves payouts, and enables 'New Game'."""
        if len(self.player_hands) == 1:
            p_score = self._score_player_hand(self.player_hands[0])
            outcome, message = determine_outcome(
                self.player_hands[0], self.dealer_hand, is_split=False, player_score_override=p_score
            )
            self._record_outcome(outcome)
            if self.chips_mode_var.get() and self.hand_bets:
                bet = self.hand_bets[0]
                payout = calculate_payout(outcome, bet)
                self.bankroll_var.set(self.bankroll_var.get() + payout)
                profit = payout - bet
                if profit > 0:
                    net_str = f" (+${profit})"
                elif profit < 0:
                    net_str = f" (-${abs(profit)})"
                else:
                    net_str = " (Push)"

                ins_str = ""
                dealer_has_bj = (len(self.dealer_hand) == 2 and score_hand(self.dealer_hand) == BLACKJACK_TARGET)
                if self.insurance_bet > 0 and dealer_has_bj:
                    main_bet = self.hand_bets[0] if self.hand_bets else 0
                    ins_payout = calculate_insurance_payout(True, self.insurance_bet, main_bet=main_bet)
                    ins_profit = ins_payout - self.insurance_bet
                    ins_str = f" | Insurance won (+${ins_profit})"
                    self.insurance_bet = 0
                elif self.last_insurance_lost > 0:
                    ins_str = f" | Insurance lost (-${self.last_insurance_lost})"
                    self.last_insurance_lost = 0
                cur_msg = self.result_var.get()
                prefix = "The clock strikes 13... The 13 of Skulls is dealt! | " if "The clock strikes 13" in cur_msg else ""
                self.result_var.set(f"{prefix}{message}{net_str}{ins_str}")

                ins_gain = ins_profit if 'ins_profit' in locals() else 0
                net_round = profit + ins_gain
                if hasattr(self, "chip_visualizer"):
                    if net_round > 0:
                        self.chip_visualizer.animate_win(net_round)
                    elif net_round < 0:
                        self.chip_visualizer.animate_loss()
                    else:
                        self.chip_visualizer.animate_push()
                if hasattr(self, "sound_manager"):
                    if net_round > 0:
                        self.sound_manager.play_payout()
                    elif net_round < 0:
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()
            else:
                self.last_insurance_lost = 0
                cur_msg = self.result_var.get()
                prefix = "The clock strikes 13... The 13 of Skulls is dealt! | " if "The clock strikes 13" in cur_msg else ""
                self.result_var.set(f"{prefix}{message}")
                if hasattr(self, "sound_manager"):
                    if outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
                        self.sound_manager.play_payout()
                    elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()
        else:
            # Evaluate each split hand independently with is_split=True
            p1_score = self._score_player_hand(self.player_hands[0])
            p2_score = self._score_player_hand(self.player_hands[1])
            outcome1, msg1 = determine_outcome(
                self.player_hands[0], self.dealer_hand, is_split=True, player_score_override=p1_score
            )
            outcome2, msg2 = determine_outcome(
                self.player_hands[1], self.dealer_hand, is_split=True, player_score_override=p2_score
            )
            self._record_outcome(outcome1)
            self._record_outcome(outcome2)
            if self.chips_mode_var.get() and self.hand_bets:
                bet1 = self.hand_bets[0] if len(self.hand_bets) > 0 else 0
                bet2 = self.hand_bets[1] if len(self.hand_bets) > 1 else 0
                payout1 = calculate_payout(outcome1, bet1)
                payout2 = calculate_payout(outcome2, bet2)
                self.bankroll_var.set(self.bankroll_var.get() + payout1 + payout2)
                profit1 = payout1 - bet1
                profit2 = payout2 - bet2
                p1_str = f"+${profit1}" if profit1 > 0 else (f"-${abs(profit1)}" if profit1 < 0 else "Push")
                p2_str = f"+${profit2}" if profit2 > 0 else (f"-${abs(profit2)}" if profit2 < 0 else "Push")
                ins_str = f" | Insurance lost (-${self.last_insurance_lost})" if self.last_insurance_lost > 0 else ""
                self.last_insurance_lost = 0
                self.result_var.set(f"Hand 1: {msg1} ({p1_str}) | Hand 2: {msg2} ({p2_str}){ins_str}")

                total_profit = profit1 + profit2
                if hasattr(self, "chip_visualizer"):
                    if total_profit > 0:
                        self.chip_visualizer.animate_win(total_profit)
                    elif total_profit < 0:
                        self.chip_visualizer.animate_loss()
                    else:
                        self.chip_visualizer.animate_push()
                if hasattr(self, "sound_manager"):
                    if total_profit > 0:
                        self.sound_manager.play_payout()
                    elif total_profit < 0:
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()
            else:
                self.last_insurance_lost = 0
                self.result_var.set(f"Hand 1: {msg1} | Hand 2: {msg2}")
                if hasattr(self, "sound_manager"):
                    p_wins = sum(1 for o in (outcome1, outcome2) if o in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'))
                    d_wins = sum(1 for o in (outcome1, outcome2) if o in ('DEALER_WINS', 'PLAYER_BUST'))
                    if p_wins > d_wins:
                        self.sound_manager.play_payout()
                    elif d_wins > p_wins:
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()

        # Haunted Halloween progression & Hell's Table combat resolution
        primary_outcome = outcome if len(self.player_hands) == 1 else outcome1
        is_double = getattr(self, "_last_was_double", False)
        self._last_was_double = False
        is_split_round = len(self.player_hands) > 1

        soul_delta, haunted_msg = self.haunted.on_round_outcome(
            primary_outcome, is_double=is_double, is_split=is_split_round
        )
        self._update_dealer_speech_for_outcome(primary_outcome)

        if self.haunted.phase in (Phase.OMEN, Phase.SNUFFING):
            self._update_candles_display()
            if primary_outcome in ('DEALER_WINS', 'PLAYER_BUST', 'SURRENDER'):
                self._update_gravestones_display()
                if hasattr(self, "sound_manager"):
                    self.sound_manager.play_haunted_sound("candle_snuff")
                    self.sound_manager.play_haunted_sound("stone_scrape")
            if self.haunted.candles_remaining == 0:
                self._haunted_round_timer_id = self.root.after(800, self._trigger_hell_table)

        elif self.haunted.phase == Phase.HELL_TABLE:
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=True)
            if primary_outcome in ('DEALER_WINS', 'PLAYER_BUST', 'SURRENDER'):
                self._update_gravestones_display()
                if hasattr(self, "sound_manager"):
                    self.sound_manager.play_haunted_sound("stone_scrape")

            if self.haunted.is_draft_pending:
                self._haunted_round_timer_id = self.root.after(700, self._open_angelic_draft)

        elif self.haunted.phase == Phase.VICTORY:
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.set_meter(1.0, animated=True)
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("banish")
            self._haunted_round_timer_id = self.root.after(600, self._show_victory_dialog)

        elif self.haunted.phase == Phase.DEFEAT:
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.set_meter(0.0, animated=True)
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("demon_laugh")
            self.root.after(600, self._show_defeat_dialog)

        if haunted_msg:
            cur = self.result_var.get()
            if not cur.endswith(haunted_msg):
                sep = " | " if cur else ""
                self.result_var.set(f"{cur}{sep}{haunted_msg}")

        if self.chips_mode_var.get():
            self._update_bankroll_display()
            self._update_betting_controls()

        # --------------------------------------------------------------------
        # SaveManager Statistics & Gameplay Achievements Hookup
        # --------------------------------------------------------------------
        if hasattr(self, "save_manager"):
            # 1. Update hands played / won / blackjacks & win streak
            if len(self.player_hands) == 1:
                p_won = outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK')
                p_bj = outcome == 'NATURAL_BLACKJACK'
                if p_won:
                    self._current_win_streak = getattr(self, "_current_win_streak", 0) + 1
                    self.save_manager.record_win_streak(self._current_win_streak)
                elif outcome in ('DEALER_WINS', 'PLAYER_BUST', 'SURRENDER'):
                    self._current_win_streak = 0
                self.save_manager.record_hand_played(won=p_won, is_blackjack=p_bj)
            else:
                p1_won = outcome1 in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK')
                p2_won = outcome2 in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK')
                self.save_manager.record_hand_played(won=p1_won, is_blackjack=(outcome1 == 'NATURAL_BLACKJACK'))
                self.save_manager.record_hand_played(won=p2_won, is_blackjack=(outcome2 == 'NATURAL_BLACKJACK'))
                if p1_won or p2_won:
                    self._current_win_streak = getattr(self, "_current_win_streak", 0) + 1
                    self.save_manager.record_win_streak(self._current_win_streak)
                else:
                    self._current_win_streak = 0

            # 2. Record bankroll in Chips Mode
            if self.chips_mode_var.get():
                self.save_manager.record_bankroll(self.bankroll_var.get())

            # 3. Achievement: Natural Born Winner (3 Natural Blackjacks in a session)
            bjs_in_round = 0
            if len(self.player_hands) == 1:
                if outcome == 'NATURAL_BLACKJACK':
                    bjs_in_round += 1
            else:
                if outcome1 == 'NATURAL_BLACKJACK':
                    bjs_in_round += 1
                if outcome2 == 'NATURAL_BLACKJACK':
                    bjs_in_round += 1
            if bjs_in_round > 0:
                self._session_blackjacks = getattr(self, "_session_blackjacks", 0) + bjs_in_round
                if self._session_blackjacks >= 3:
                    self.save_manager.unlock_achievement("natural_streak")

            # 4. Achievement: Cursed Survivor (Survive Card 13 round with win or push)
            card_13_present = any(
                getattr(c, "rank", "") == "thirteen" or (isinstance(c, (tuple, list)) and c[0] == 13)
                for h in self.player_hands for c in h
            ) or any(
                getattr(c, "rank", "") == "thirteen" or (isinstance(c, (tuple, list)) and c[0] == 13)
                for c in self.dealer_hand
            )
            if card_13_present:
                survived = False
                if len(self.player_hands) == 1:
                    survived = outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK', 'PUSH')
                else:
                    survived = any(o in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK', 'PUSH') for o in (outcome1, outcome2))
                if survived:
                    self.save_manager.unlock_achievement("cursed_survivor")

            # 5. Achievement: Split Maestro (Win both split hands)
            if len(self.player_hands) > 1:
                if outcome1 in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK') and outcome2 in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
                    self.save_manager.unlock_achievement("split_maestro")

            # 6. Achievement: Big Spender (Win an all-in bet of $1,000+)
            if self.chips_mode_var.get():
                total_bet = sum(self.hand_bets) if self.hand_bets else 0
                round_won = (outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK')) if len(self.player_hands) == 1 else any(o in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK') for o in (outcome1, outcome2))
                if total_bet >= 1000 and round_won:
                    payout_amt = payout if len(self.player_hands) == 1 else (payout1 + payout2)
                    if self.bankroll_var.get() == payout_amt or getattr(self, "_is_all_in_round", False):
                        self.save_manager.unlock_achievement("big_spender")
                self._is_all_in_round = False

            # 7. Achievement: The Exorcist (Defeat Hell's Table and banish Pit Fiend)
            if self.haunted.phase == Phase.VICTORY:
                self.save_manager.unlock_achievement("exorcist")
            elif self.haunted.phase == Phase.HELL_TABLE:
                self.save_manager.unlock_costume("malphas")

        # Disable Hit/Stand/Double/Split/Surrender, enable New Game
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="normal")

    def _update_ui_scaling(self):
        """Updates typography, button dimensions, and padding across the entire UI for the active scale factor."""
        s = self.scale_factor
        scale_ratio = 2.0 if s > 1.5 else 1.0

        # 1. Scoreboard Typography
        f_stat_title = ("Arial", int(11 * scale_ratio), "bold")
        f_stat_val = ("Arial", int(11 * scale_ratio))
        f_shoe = ("Arial", int(10 * scale_ratio), "bold")
        f_top_btn = ("Arial", int(9 * scale_ratio), "bold")
        f_bankroll = ("Arial", int(11 * scale_ratio), "bold")

        if hasattr(self, "stat_labels"):
            for lbl, is_bold in self.stat_labels:
                lbl.configure(font=f_stat_title if is_bold else f_stat_val)

        if hasattr(self, "shoe_label"):
            self.shoe_label.configure(font=f_shoe)

        for btn in (
            getattr(self, "sound_button", None),
            getattr(self, "help_button", None),
            getattr(self, "dealer_view_button", None),
            getattr(self, "scale_button", None),
            getattr(self, "fullscreen_button", None),
            getattr(self, "settings_button", None),
        ):
            if btn:
                btn.configure(font=f_top_btn)

        if hasattr(self, "bankroll_label"):
            self.bankroll_label.configure(font=f_bankroll)

        # Scale help button icon if present
        if getattr(self, "icon_loader", None) and hasattr(self, "help_button"):
            div = 1.5 if s > 1.5 else 3.0
            self.icon_question_small = self.icon_loader.get_icon("keyboard_question", scale_div=div)
            if self.icon_question_small:
                self.help_button.configure(image=self.icon_question_small)

        # 2. Hand Titles and Scores
        f_hand_title = ("Arial", int(11 * scale_ratio), "bold")
        f_hand_score = ("Arial", int(12 * scale_ratio), "bold" if s > 1.5 else "normal")
        if hasattr(self, "dealer_title_label"):
            self.dealer_title_label.configure(font=f_hand_title)
        if hasattr(self, "dealer_score_label"):
            self.dealer_score_label.configure(font=f_hand_score)
        if hasattr(self, "player_title_label"):
            self.player_title_label.configure(font=f_hand_title)
        if hasattr(self, "player_score_label"):
            self.player_score_label.configure(font=f_hand_score)

        # 3. Action Buttons & Chips Mode Toggle
        f_action_btn = ("Arial", int(10 * scale_ratio), "bold")
        action_btn_pad = int(6 * s)
        btn_pady = int(3 * s)
        action_buttons = [
            getattr(self, "hit_button", None),
            getattr(self, "stand_button", None),
            getattr(self, "double_button", None),
            getattr(self, "split_button", None),
            getattr(self, "surrender_button", None),
            getattr(self, "new_game_button", None),
            getattr(self, "miracle_button", None),
        ]
        for btn in action_buttons:
            if btn:
                btn.configure(font=f_action_btn)
                if bool(btn.grid_info()):
                    btn.grid_configure(padx=action_btn_pad, pady=btn_pady)

        if hasattr(self, "cursed_stakes_button"):
            self.cursed_stakes_button.configure(font=f_action_btn)
            if bool(self.cursed_stakes_button.grid_info()):
                self.cursed_stakes_button.grid_configure(padx=(int(6 * s), int(8 * s)), pady=btn_pady)

        if hasattr(self, "chips_mode_check"):
            self.chips_mode_check.configure(font=f_action_btn)
            self.chips_mode_check.grid_configure(padx=(int(8 * s), int(12 * s)), pady=btn_pady)

        # 4. Betting Buttons (when Chips Mode is on)
        f_bet_btn = ("Arial", int(9 * scale_ratio), "bold")
        f_bet_label = ("Arial", int(10 * scale_ratio), "bold")
        if hasattr(self, "bet_chips_label"):
            self.bet_chips_label.configure(font=f_bet_label)
        if hasattr(self, "chip_buttons"):
            for b in self.chip_buttons:
                b.configure(font=f_bet_btn)
                b.pack_configure(padx=int(3 * s), pady=int(2 * s))
        for b in (
            getattr(self, "all_in_button", None),
            getattr(self, "clear_bet_button", None),
            getattr(self, "deal_bet_button", None),
            getattr(self, "rebuy_button", None),
        ):
            if b:
                b.configure(font=f_bet_btn)
                b.pack_configure(padx=int(4 * s), pady=int(2 * s))

        # 5. Insurance prompt bar
        f_ins_label = ("Arial", int(10 * scale_ratio), "bold")
        f_ins_btn = ("Arial", int(9 * scale_ratio), "bold")
        if hasattr(self, "insurance_label"):
            self.insurance_label.configure(font=f_ins_label)
        if hasattr(self, "take_insurance_button"):
            self.take_insurance_button.configure(font=f_ins_btn)
        if hasattr(self, "decline_insurance_button"):
            self.decline_insurance_button.configure(font=f_ins_btn)

        # 6. Dealer Actor Elements (Phase 4)
        f_nameplate = ("Arial", int(10 * scale_ratio), "bold")
        f_speech = ("Arial", int(9 * scale_ratio), "italic")
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(font=f_nameplate)
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.configure(
                font=f_speech,
                wraplength=int(380 * scale_ratio),
                padx=int(6 * s),
                pady=int(2 * s)
            )
        if hasattr(self, "dealer_stage_canvas"):
            self.dealer_stage_canvas.set_scale(self.scale_factor)
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_scale(self.scale_factor)
        if hasattr(self, "horizon_rail"):
            self.horizon_rail.configure(height=int(4 * s))
        if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
            self.card_table_frame.set_scale(self.scale_factor)

    def toggle_scale_mode(self, event=None):
        """Toggles between 1.0x and 2.0x in-memory interface scaling."""
        new_scale = 2.0 if self.scale_factor == 1.0 else 1.0
        self.scale_factor = new_scale
        self.card_width = int(CARD_WIDTH * self.scale_factor)
        self.card_height = int(CARD_HEIGHT * self.scale_factor)
        self.card_overlap_offset = int(PLAYER_CARD_OVERLAP_OFFSET * self.scale_factor)
        target_scale = 1 if self.scale_factor == 2.0 else 2
        self.scale_status_var.set(f"🔍 {target_scale}x")

        # Re-scale card images in memory
        self._rebuild_scaled_assets(self.scale_factor)

        # Update table frames and widgets
        if hasattr(self, "card_table_frame"):
            if isinstance(self.card_table_frame, TableFeltCanvas):
                self.card_table_frame.set_scale(self.scale_factor)
            self.card_table_frame.rowconfigure(0, weight=1, minsize=int(118 * self.scale_factor))
            self.card_table_frame.rowconfigure(1, weight=1, minsize=int(118 * self.scale_factor))

        if hasattr(self, "announcement_hud"):
            self.announcement_hud.set_scale(self.scale_factor)
        if hasattr(self, "haunted_altar"):
            self.haunted_altar.set_scale(self.scale_factor, self.haunted_assets)
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.set_scale(self.scale_factor)
        if hasattr(self, "soul_meter_canvas"):
            self.soul_meter_canvas.set_scale(self.scale_factor)
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_scale(self.scale_factor)

        # Update UI typography, button dimensions, and padding
        self._update_ui_scaling()

        # Redraw hands
        self._render_dealer_cards()
        self._render_player_cards()

        # Update ambient accessory images
        self._update_dealer_avatar()
        if hasattr(self, "pumpkin_label") and hasattr(self, "_anim_frame_toggle"):
            p_img = self.haunted_assets.get(f"pumpkin_glow_{1 if self._anim_frame_toggle else 0}")
            if p_img:
                self.pumpkin_label.configure(image=p_img)
                self.pumpkin_label.image = p_img

        # Resize window or exit fullscreen mode
        if self.is_fullscreen and self.scale_factor == 1.0:
            self.toggle_fullscreen()
        elif not self.is_fullscreen:
            try:
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()
                target_w = min(int(DEFAULT_WINDOW_WIDTH * self.scale_factor), max(DEFAULT_WINDOW_WIDTH, screen_w - 40))
                target_h = min(int(DEFAULT_WINDOW_HEIGHT * self.scale_factor), max(DEFAULT_WINDOW_HEIGHT, screen_h - 80))
                self.root.minsize(
                    int(MIN_WINDOW_WIDTH * (1.0 if self.scale_factor == 1.0 else 1.5)),
                    int(MIN_WINDOW_HEIGHT * (1.0 if self.scale_factor == 1.0 else 1.5))
                )
                self.root.geometry(f"{target_w}x{target_h}")
            except Exception:
                pass
        return "break"

    def _rebuild_scaled_assets(self, scale: float):
        """Re-scales all cards, card backs, and haunted assets in memory using AssetScaler."""
        w = int(CARD_WIDTH * scale)
        h = int(CARD_HEIGHT * scale)
        scaler = getattr(self, "_asset_scaler", None)
        if not scaler:
            self._asset_scaler = AssetScaler(master=self.root)
            scaler = self._asset_scaler

        # 1. Update all_cards
        new_all_cards = []
        for c in self.all_cards:
            fname = f"1_{c.suit}.png" if c.rank == "ace" else f"{c.rank}_{c.suit}.png"
            path = ASSETS_DIR / fname
            scaled_img = scaler.get_scaled_image(path, w, h)
            new_card = Card(value=c.value, image=scaled_img, rank=c.rank, suit=c.suit)
            new_all_cards.append(new_card)
        self.all_cards = new_all_cards

        # 2. Update card back
        back_path = ASSETS_DIR / "back.png"
        self.back_image = scaler.get_scaled_image(back_path, w, h)

        # 3. Update haunted assets
        if HAUNTED_ASSETS_DIR.exists():
            for p in HAUNTED_ASSETS_DIR.glob("*.png"):
                stem = p.stem
                if stem.startswith("card_") or stem == "back_haunted" or ("haunted" in stem and any(f in stem for f in ("jack", "queen", "king"))):
                    img_w, img_h = w, h
                elif "avatar" in stem or "dealer" in stem:
                    img_w, img_h = int(96 * scale), int(96 * scale)
                elif "pumpkin" in stem:
                    img_w, img_h = int(48 * scale), int(48 * scale)
                elif "gravestone" in stem:
                    img_w, img_h = int(48 * scale), int(56 * scale)
                elif "candle" in stem:
                    img_w, img_h = int(40 * scale), int(40 * scale)
                elif "relic" in stem:
                    img_w, img_h = int(48 * scale), int(48 * scale)
                else:
                    img_w, img_h = int(48 * scale), int(48 * scale)

                scaled = scaler.get_scaled_image(p, img_w, img_h)
                if scaled:
                    self.haunted_assets[stem] = scaled

        if "card_13" in self.haunted_assets:
            self.card_13 = Card(13, self.haunted_assets["card_13"], rank="thirteen", suit="skulls")

        # 4. Helper to find updated card matching rank and suit
        def find_updated_card(old_card: Card) -> Card:
            if old_card.rank == "thirteen" and self.card_13:
                return self.card_13
            for c in self.all_cards:
                if c.rank == old_card.rank and c.suit == old_card.suit:
                    return c
            return old_card

        # Update active deck and hands
        self.deck = [find_updated_card(c) for c in self.deck]
        self.dealer_hand = [find_updated_card(c) for c in self.dealer_hand]
        if self.dealer_hole_card:
            self.dealer_hole_card = find_updated_card(self.dealer_hole_card)
        self.player_hands = [[find_updated_card(c) for c in h] for h in self.player_hands]

    def toggle_fullscreen(self, event=None):
        """Toggles native Tkinter fullscreen mode and automatically upscales interface to 2x for full screens."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            try:
                self._prev_geometry = self.root.geometry()
                self._prev_scale_factor = self.scale_factor
            except Exception:
                self._prev_geometry = None
                self._prev_scale_factor = 1.0
            try:
                self.root.attributes("-fullscreen", True)
            except Exception:
                pass
            self.fullscreen_status_var.set("🗗 Window")
            # Automatically upscale to 2x if currently at 1x so cards and components fill the screen
            if self.scale_factor == 1.0:
                self.toggle_scale_mode()
        else:
            try:
                self.root.attributes("-fullscreen", False)
            except Exception:
                pass
            self.fullscreen_status_var.set("⛶ Full")
            # Restore previous scale factor if auto-upscaled upon entering fullscreen
            if getattr(self, "_prev_scale_factor", 1.0) == 1.0 and self.scale_factor == 2.0:
                self.toggle_scale_mode()
            if hasattr(self, "_prev_geometry") and self._prev_geometry:
                try:
                    self.root.geometry(self._prev_geometry)
                except Exception:
                    pass
        return "break"

    def exit_fullscreen(self, event=None):
        """Exits fullscreen mode if currently in fullscreen (Escape handler)."""
        if getattr(self, "is_fullscreen", False):
            self.toggle_fullscreen()
            return "break"

    def _on_escape_key(self, event=None):
        """Context-sensitive Escape key: closes shortcuts HUD, declines insurance, or exits fullscreen."""
        if getattr(self, "_shortcuts_dialog", None) is not None:
            self._close_shortcuts_overlay()
            return "break"
        if getattr(self, "is_insurance_phase", False) and getattr(self, "decline_insurance_button", None):
            try:
                if str(self.decline_insurance_button.cget("state")) == "normal":
                    self._on_decline_insurance()
                    return "break"
            except Exception:
                pass
        if getattr(self, "is_fullscreen", False):
            self.exit_fullscreen()
            return "break"
        return "break"

    def _record_outcome(self, outcome: str):
        """Updates win/loss/tie counters according to hand outcome."""
        if outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
            self.player_wins_var.set(self.player_wins_var.get() + 1)
        elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
            self.dealer_wins_var.set(self.dealer_wins_var.get() + 1)
        elif outcome == 'PUSH':
            self.ties_var.set(self.ties_var.get() + 1)

    def _set_action_buttons_state(self, state: str):
        """Helper to set the state of action buttons."""
        self.hit_button.configure(state=state)
        self.stand_button.configure(state=state)
        if state == "disabled":
            if hasattr(self, "double_button"):
                self.double_button.configure(state="disabled")
            if hasattr(self, "split_button"):
                self.split_button.configure(state="disabled")
            if hasattr(self, "surrender_button"):
                self.surrender_button.configure(state="disabled")

    def _cancel_all_active_timers(self):
        """Safely cancels all registered background and animation timers across subsystems."""
        self._cancel_blink_timers()
        for attr in (
            "_dealer_idle_timer_id",
            "_dealer_blink_timer_id",
            "_dealer_blink_restore_timer_id",
            "_dealer_gesture_timer_id",
            "_dealer_mouth_timer_id",
            "_dealer_speech_anim_timer_id",
            "_typewriter_timer_id",
            "_haunted_round_timer_id",
            "_ambient_timer_id",
            "_dealer_timer_id",
        ):
            timer_id = getattr(self, attr, None)
            if timer_id:
                try:
                    self.root.after_cancel(timer_id)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _on_root_destroyed(self, event):
        """Emergency callback invoked when root is destroyed directly without _on_close."""
        if getattr(event, "widget", None) == self.root:
            self._cancel_all_active_timers()

    def _on_close(self):
        """Safely cleans up any pending timer callback before window destruction."""
        self._close_shortcuts_overlay()
        self._close_settings_dialog()
        self._close_wardrobe_dialog()
        self._cancel_all_active_timers()
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.clear_timers()
        if hasattr(self, "soul_meter_canvas"):
            self.soul_meter_canvas._cancel_timer()
        if hasattr(self, "haunted_altar"):
            self.haunted_altar.cancel_animations()
        if hasattr(self, "sound_manager"):
            self.sound_manager.stop_all()
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tkinter.TclError:
            pass


# ============================================================================
# Entry Point
# ============================================================================

def play_game():
    """
    Main entry point to initialize and launch the Blackjack GUI.
    Preserved as a top-level function for backward compatibility with import_test.py.
    """
    root = tkinter.Tk()
    BlackjackApp(root)
    root.mainloop()


if __name__ == "__main__":
    play_game()
