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

import random
import sys
import tkinter
from pathlib import Path

# Optional pygame.mixer support for authentic tactile casino audio
try:
    # pyrefly: ignore [missing-import]
    from pygame import mixer as pygame_mixer
    PYGAME_AVAILABLE = True
except (ImportError, Exception):
    pygame_mixer = None
    PYGAME_AVAILABLE = False

# ============================================================================
# Named Constants & Configuration
# ============================================================================
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
DEFAULT_WINDOW_WIDTH = 840
DEFAULT_WINDOW_HEIGHT = 580
MIN_WINDOW_WIDTH = 760
MIN_WINDOW_HEIGHT = 520
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
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()
ASSETS_DIR = BASE_DIR / "cards"
AUDIO_DIR = BASE_DIR / "audio"
ASSETS_EXTRA_DIR = BASE_DIR / "assets"
DEFAULT_SOUND_VOLUME = 0.7


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


def determine_outcome(player_hand, dealer_hand, is_split: bool = False):
    """
    Evaluates the final result of a round once both player and dealer have completed their turns.

    Args:
        player_hand: List of card values or Card instances for the player.
        dealer_hand: List of card values or Card instances for the dealer.
        is_split: Whether this hand originated from a split. Split 21s cannot be Natural Blackjacks.

    Returns:
        tuple[str, str]: (outcome_code, display_message)
    """
    player_score = score_hand(player_hand)
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
        self.canvas_width = width
        self.canvas_height = height
        self.cx = width // 2
        self.cy = height // 2
        self.current_bet = 0
        self._active_timers = set()

        self._draw_base_spot()

    def _draw_base_spot(self):
        """Draws the felt betting spot: outer dashed gold ellipse, inner accent ring, watermark, and badge."""
        self.delete("all")
        cx, cy = self.cx, self.cy

        # 1. Outer betting circle felt background and golden dashed ring
        self.create_oval(
            cx - 74, cy - 38, cx + 74, cy + 38,
            outline="#d4af37", width=2, dash=(4, 3), fill="#053c14", tags="spot_base"
        )
        # 2. Inner subtle gold accent ring
        self.create_oval(
            cx - 66, cy - 32, cx + 66, cy + 32,
            outline="#8a6d1b", width=1, dash=(2, 3), tags="spot_ring"
        )
        # 3. Felt watermark
        self.create_text(
            cx, cy + 1, text="BETTING SPOT", fill="#144d21",
            font=("Arial", 7, "bold"), tags="watermark"
        )
        # 4. Top badge for bet amount
        self.create_text(
            cx, 13, text="", fill="#ffd700",
            font=("Arial", 9, "bold"), tags="badge"
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
        rx, ry, depth = 15, 8, 4

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
        self.create_line(x - 8, y + 1, x - 8, y + depth, fill=style["stripe"], width=2, tags=tags)
        self.create_line(x + 8, y + 1, x + 8, y + depth, fill=style["stripe"], width=2, tags=tags)

        # 3. Top face
        self.create_oval(
            x - rx, y - ry, x + rx, y + ry,
            fill=style["bg"], outline="#ffffff", width=1, tags=tags
        )
        # Inner dashed circle
        self.create_oval(
            x - rx + 3, y - ry + 2, x + rx - 3, y + ry - 2,
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


def load_images(card_images):
    """
    Loads all 52 card PNG images into a list of Card instances.
    Preserved for backward compatibility with test suites and external callers.
    """
    suits = ["heart", "club", "diamond", "spade"]
    face_cards = ["jack", "queen", "king"]

    for suit in suits:
        # Number cards 1 to 10 (1 = Ace)
        for card in range(1, 11):
            name = ASSETS_DIR / f"{card}_{suit}.png"
            image = tkinter.PhotoImage(file=str(name))
            rank = "ace" if card == 1 else str(card)
            card_images.append(Card(value=card, image=image, rank=rank, suit=suit))

        # Face cards (Jack, Queen, King all value 10)
        for card in face_cards:
            name = ASSETS_DIR / f"{card}_{suit}.png"
            image = tkinter.PhotoImage(file=str(name))
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


# ============================================================================
# GUI Application: Object-Oriented Presentation Layer
# ============================================================================

class BlackjackApp:
    """
    Encapsulates the Blackjack GUI, card state, and game lifecycle.
    Eliminates all global variables by storing state in instance attributes.
    Supports hand splitting with independent turn progression and outcome resolution.
    """

    def __init__(self, root: tkinter.Tk, sound_enabled: bool = True):
        self.root = root
        self.root.title("Blackjack")
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
        self.root.rowconfigure(1, weight=1)

        # Async timer management & graceful window destruction
        self._dealer_timer_id = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

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

        # Chips and Wagering State
        self.chips_mode_var = tkinter.BooleanVar(value=False)
        self.bankroll_var = tkinter.IntVar(value=STARTING_BANKROLL)
        self.current_bet_var = tkinter.IntVar(value=0)
        self.hand_bets = [0]
        self.is_betting_phase = False
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.is_insurance_phase = False
        self.chip_buttons = []

        # Load card visual assets
        self._load_assets()

        # Build interface layout
        self._build_ui()

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
        """Loads 52 card face images and the card back image."""
        load_images(self.all_cards)
        back_path = ASSETS_DIR / "back.png"
        self.back_image = tkinter.PhotoImage(file=str(back_path))

    def _build_ui(self):
        """Builds all Tkinter frames, scoreboards, card tables, and action buttons."""
        # Top Scoreboard: Win/Tie counters and status message
        scoreboard_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        scoreboard_frame.grid(row=0, column=0, columnspan=3, pady=(0, 6))

        tkinter.Label(
            scoreboard_frame, text="Dealer Wins: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=0)
        tkinter.Label(
            scoreboard_frame, textvariable=self.dealer_wins_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=1, padx=(0, 15))

        tkinter.Label(
            scoreboard_frame, text="Player Wins: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=2)
        tkinter.Label(
            scoreboard_frame, textvariable=self.player_wins_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=3, padx=(0, 15))

        tkinter.Label(
            scoreboard_frame, text="Ties: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=4)
        tkinter.Label(
            scoreboard_frame, textvariable=self.ties_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=5)

        # Chips Mode Toggle Checkbutton
        self.chips_mode_check = tkinter.Checkbutton(
            scoreboard_frame, text="Chips Mode", variable=self.chips_mode_var,
            command=self._on_toggle_chips_mode, font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white",
            selectcolor=PANEL_BACKGROUND_COLOR, activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white"
        )
        self.chips_mode_check.grid(row=0, column=6, padx=(15, 0))

        # Shoe Cards Remaining Display
        self.shoe_label = tkinter.Label(
            scoreboard_frame, textvariable=self.shoe_info_var, font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#80cbc4"
        )
        self.shoe_label.grid(row=0, column=7, padx=(15, 0))

        # Sound Mute Toggle Button
        self.sound_button = tkinter.Button(
            scoreboard_frame, textvariable=self.sound_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_toggle_sound
        )
        self.sound_button.grid(row=0, column=8, padx=(15, 0))

        # Bankroll and Bet summary (visible in Chips Mode)
        self.bankroll_label = tkinter.Label(
            scoreboard_frame, text="Bankroll: $1,000  |  Bet: $0",
            font=("Arial", 11, "bold"), background=TABLE_BACKGROUND_COLOR, fg="#81c784"
        )
        self.bankroll_label.grid(row=1, column=0, columnspan=9, pady=(2, 2))
        self.bankroll_label.grid_remove()  # Hidden by default in Casual Mode

        # Status / Result banner
        self.result_label = tkinter.Label(
            scoreboard_frame, textvariable=self.result_var, font=("Arial", 13, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#ffeb3b"
        )
        self.result_label.grid(row=2, column=0, columnspan=9, pady=(2, 4))

        # Main Card Table Area
        card_table_frame = tkinter.Frame(
            self.root, relief="sunken", borderwidth=2, background=PANEL_BACKGROUND_COLOR, padx=10, pady=10
        )
        card_table_frame.grid(row=1, column=0, sticky="nsew", columnspan=3)
        card_table_frame.columnconfigure(1, weight=1)

        # Dealer Section
        tkinter.Label(
            card_table_frame, text="Dealer", font=("Arial", 11, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white"
        ).grid(row=0, column=0, sticky="w")
        tkinter.Label(
            card_table_frame, textvariable=self.dealer_score_var, font=("Arial", 12),
            background=PANEL_BACKGROUND_COLOR, fg="white"
        ).grid(row=1, column=0, sticky="w")

        self.dealer_cards_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR)
        self.dealer_cards_frame.grid(row=0, column=1, sticky="ew", rowspan=2, padx=10, pady=5)

        # Player Section
        tkinter.Label(
            card_table_frame, text="Player", font=("Arial", 11, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white"
        ).grid(row=2, column=0, sticky="w", pady=(15, 0))
        tkinter.Label(
            card_table_frame, textvariable=self.player_score_var, font=("Arial", 12),
            background=PANEL_BACKGROUND_COLOR, fg="white"
        ).grid(row=3, column=0, sticky="w")

        self.player_cards_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR)
        self.player_cards_frame.grid(row=2, column=1, sticky="ew", rowspan=2, padx=10, pady=5)

        # 2.5D Casino Felt Betting Spot Visualizer (visible in Chips Mode)
        self.chip_visualizer = ChipVisualizer(
            card_table_frame, width=180, height=135, background=PANEL_BACKGROUND_COLOR
        )
        self.chip_visualizer.grid(row=2, column=2, rowspan=2, padx=(10, 5), pady=5, sticky="e")
        self.chip_visualizer.grid_remove()  # Hidden by default in Casual Mode

        # Betting Controls Bar (visible in Chips Mode)
        self.betting_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        self.betting_frame.grid(row=2, column=0, columnspan=3, pady=(4, 6))
        self.betting_frame.grid_remove()  # Hidden by default in Casual Mode

        tkinter.Label(
            self.betting_frame, text="Bet Chips:", font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        ).pack(side="left", padx=(0, 6))

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
        self.insurance_frame.grid(row=3, column=0, columnspan=3, pady=(2, 6))
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
        button_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(4, 10))

        self.hit_button = tkinter.Button(
            button_frame, text="Hit", width=8, font=("Arial", 10, "bold"),
            takefocus=False, command=self.on_hit
        )
        self.hit_button.grid(row=0, column=0, padx=6)

        self.stand_button = tkinter.Button(
            button_frame, text="Stand", width=8, font=("Arial", 10, "bold"),
            takefocus=False, command=self.on_stand
        )
        self.stand_button.grid(row=0, column=1, padx=6)

        self.double_button = tkinter.Button(
            button_frame, text="Double", width=8, font=("Arial", 10, "bold"),
            takefocus=False, command=self.on_double_down, state="disabled"
        )
        self.double_button.grid(row=0, column=2, padx=6)

        self.split_button = tkinter.Button(
            button_frame, text="Split", width=8, font=("Arial", 10, "bold"),
            takefocus=False, command=self.on_split, state="disabled"
        )
        self.split_button.grid(row=0, column=3, padx=6)

        self.surrender_button = tkinter.Button(
            button_frame, text="Surrender", width=9, font=("Arial", 10, "bold"),
            takefocus=False, command=self.on_surrender, state="disabled"
        )
        self.surrender_button.grid(row=0, column=4, padx=6)

        self.new_game_button = tkinter.Button(
            button_frame, text="New Game", width=9, font=("Arial", 10, "bold"),
            takefocus=False, command=self.new_game
        )
        self.new_game_button.grid(row=0, column=5, padx=6)

        # Keyboard shortcuts initialization
        self._setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self):
        """Binds full keyboard shortcut support across the window for gameplay accessibility."""
        # Deal / Hit / New Game shortcuts (Enter and Space)
        for key in ("<Return>", "<KP_Enter>", "<space>"):
            self.root.bind(key, self._on_key_deal_or_hit)
            self.root.bind_class("Button", key, self._on_key_deal_or_hit)

        # Action shortcuts (case-insensitive)
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

        # Insurance shortcuts (Y = Take, N / Escape = Decline)
        for key in ("<y>", "<Y>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_take_insurance, getattr(self, "take_insurance_button", None)))
        for key in ("<n>", "<N>", "<Escape>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_decline_insurance, getattr(self, "decline_insurance_button", None)))

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
        score = score_hand(hand)

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

        # 2. Clear card visuals from frames
        for child in self.dealer_cards_frame.winfo_children():
            child.destroy()
        for child in self.player_cards_frame.winfo_children():
            child.destroy()

        # 3. Reset scores and status
        self.dealer_score_var.set("0")
        self.player_score_var.set("0")
        self.result_var.set("")
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.is_insurance_phase = False
        if hasattr(self, "insurance_frame"):
            self.insurance_frame.grid_remove()

        if self.chips_mode_var.get():
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
            # Chips Mode activated: reset bankroll to starting $1,000 as per policy
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.hand_bets = [0]
            self.bankroll_label.grid()
            self.betting_frame.grid()
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid()
                self.chip_visualizer.set_bet(0, animate=False)
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

            # Check if player has Natural Blackjack
            player_score = score_hand(self.player_hands[0])
            if player_score == BLACKJACK_TARGET:
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
        return card

    def _deal_card_to_player(self, hand_index=None):
        """Deals one card to the active player hand and updates visuals."""
        if hand_index is None:
            hand_index = self.active_hand_index
        card = self._draw_card()
        self.player_hands[hand_index].append(card)
        self._render_player_cards()
        self._update_player_score_display()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_card_deal()

    def _deal_card_to_dealer(self, is_hole_card=False):
        """
        Deals one card to the dealer.
        If `is_hole_card` is True, renders `back.png` and hides its score until Stand.
        """
        card = self._draw_card()
        self.dealer_hand.append(card)
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_card_deal()

        if is_hole_card:
            # Face-down hole card
            self.dealer_hole_card = card
            self.dealer_hole_widget = tkinter.Label(
                self.dealer_cards_frame, image=self.back_image,
                relief="flat", borderwidth=0, highlightthickness=0,
                background=PANEL_BACKGROUND_COLOR
            )
            self.dealer_hole_widget.pack(side="left", padx=2)
            # Display only the upcard score while hole card remains hidden
            upcard_score = score_hand([self.dealer_hand[0]])
            self.dealer_score_var.set(f"{upcard_score} + ?")
        else:
            # Face-up card
            tkinter.Label(
                self.dealer_cards_frame, image=card[1],
                relief="flat", borderwidth=0, highlightthickness=0,
                background=PANEL_BACKGROUND_COLOR
            ).pack(side="left", padx=2)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))

    def _render_player_cards(self):
        """Renders visual card labels and hand frames for player hand(s)."""
        for child in self.player_cards_frame.winfo_children():
            child.destroy()

        is_split = len(self.player_hands) > 1

        for idx, hand in enumerate(self.player_hands):
            is_active = (idx == self.active_hand_index)
            container = tkinter.Frame(
                self.player_cards_frame,
                background=PANEL_BACKGROUND_COLOR,
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
                    background=PANEL_BACKGROUND_COLOR, fg=fg_color
                ).pack(anchor="w", pady=(0, 2))

            num_cards = len(hand)
            if num_cards == 0:
                frame_width = CARD_WIDTH
            else:
                frame_width = CARD_WIDTH + (num_cards - 1) * PLAYER_CARD_OVERLAP_OFFSET

            cards_frame = tkinter.Frame(
                container, background=PANEL_BACKGROUND_COLOR,
                width=frame_width, height=CARD_HEIGHT
            )
            cards_frame.pack(side="top")
            cards_frame.pack_propagate(False)

            for i, card in enumerate(hand):
                lbl = tkinter.Label(
                    cards_frame, image=card[1],
                    relief="flat", borderwidth=0, highlightthickness=0,
                    background=PANEL_BACKGROUND_COLOR
                )
                lbl.place(x=i * PLAYER_CARD_OVERLAP_OFFSET, y=0, width=CARD_WIDTH, height=CARD_HEIGHT)

    def _update_player_score_display(self):
        """Updates the reactive player score variable."""
        if len(self.player_hands) == 1:
            self.player_score_var.set(str(score_hand(self.player_hands[0])))
        else:
            scores = [str(score_hand(h)) for h in self.player_hands]
            self.player_score_var.set(f"H1: {scores[0]} | H2: {scores[1]}")

    def _check_initial_blackjack(self):
        """
        Inspects hands immediately after initial deal for Natural Blackjacks (21 on 2 cards).
        Resolves immediately if either player or dealer has 21.
        Otherwise, configures action buttons (Hit, Stand, Double, Split, Surrender).
        """
        player_score = score_hand(self.player_hands[0])
        dealer_score = score_hand(self.dealer_hand)
        if player_score == BLACKJACK_TARGET or dealer_score == BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            self._reveal_dealer_hole_card()
            self._conclude_round()
        else:
            self._update_action_buttons()

    def _reveal_dealer_hole_card(self):
        """Flips the dealer's hole card face-up and displays the full dealer score."""
        if self.dealer_hole_widget and self.dealer_hole_card:
            self.dealer_hole_widget.configure(image=self.dealer_hole_card[1])
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

        # Disable double, split, and surrender buttons immediately
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")

        # Deal exactly 1 card
        self._deal_card_to_player()
        score = score_hand(self.player_hands[self.active_hand_index])

        if score > BLACKJACK_TARGET:
            # Busted on double down
            if self.active_hand_index < len(self.player_hands) - 1:
                # Advance to next split hand
                self.active_hand_index += 1
                self.result_var.set("Hand 1 busted on Double! Playing Hand 2...")
                self._render_player_cards()
                self._update_player_score_display()
                self._update_action_buttons()
                if score_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                    self.on_stand()
            else:
                all_busted = all(score_hand(h) > BLACKJACK_TARGET for h in self.player_hands)
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
        current_score = score_hand(current_hand)

        if current_score > BLACKJACK_TARGET:
            # Current hand busted!
            if self.active_hand_index < len(self.player_hands) - 1:
                # Move to next split hand
                self.active_hand_index += 1
                self.result_var.set("Hand 1 busted! Playing Hand 2...")
                self._render_player_cards()
                self._update_player_score_display()
                self._update_action_buttons()
                if score_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                    self.on_stand()
            else:
                # Final hand has completed (busted)
                all_busted = all(score_hand(h) > BLACKJACK_TARGET for h in self.player_hands)
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
            tkinter.Label(
                self.dealer_cards_frame, image=card[1],
                relief="flat", borderwidth=0, highlightthickness=0,
                background=PANEL_BACKGROUND_COLOR
            ).pack(side="left", padx=2)
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
            outcome, message = determine_outcome(self.player_hands[0], self.dealer_hand, is_split=False)
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
                self.result_var.set(f"{message}{net_str}{ins_str}")

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
                self.result_var.set(message)
                if hasattr(self, "sound_manager"):
                    if outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
                        self.sound_manager.play_payout()
                    elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()
        else:
            # Evaluate each split hand independently with is_split=True
            outcome1, msg1 = determine_outcome(self.player_hands[0], self.dealer_hand, is_split=True)
            outcome2, msg2 = determine_outcome(self.player_hands[1], self.dealer_hand, is_split=True)
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

        if self.chips_mode_var.get():
            self._update_bankroll_display()
            self._update_betting_controls()

        # Disable Hit/Stand/Double/Split/Surrender, enable New Game
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="normal")

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

    def _on_close(self):
        """Safely cleans up any pending timer callback before window destruction."""
        if self._dealer_timer_id:
            try:
                self.root.after_cancel(self._dealer_timer_id)
            except Exception:
                pass
            self._dealer_timer_id = None
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.clear_timers()
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
