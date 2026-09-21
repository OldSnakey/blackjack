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

import random
import tkinter
from pathlib import Path

# ============================================================================
# Named Constants & Configuration
# ============================================================================
# Standard Blackjack target and casino dealer rules
BLACKJACK_TARGET = 21
DEALER_STAND_THRESHOLD = 17  # Standard casino rule: Dealer must stand on 17 or higher

# UI Animation Timing (in milliseconds)
# 700ms provides an authentic, observable card-dealing cadence without feeling sluggish
# or stalling the game flow.
DEALER_DRAW_DELAY_MS = 700

# Window dimensions and styling
DEFAULT_WINDOW_WIDTH = 640
DEFAULT_WINDOW_HEIGHT = 480
TABLE_BACKGROUND_COLOR = "#0b6623"  # Classic casino felt green
PANEL_BACKGROUND_COLOR = "#074c1a"  # Slightly darker green for contrasting frames

# Asset paths resolved relative to this script's directory for portability
ASSETS_DIR = Path(__file__).resolve().parent / "cards"


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


def determine_outcome(player_hand, dealer_hand):
    """
    Evaluates the final result of a round once both player and dealer have completed their turns.

    Returns:
        tuple[str, str]: (outcome_code, display_message)
    """
    player_score = score_hand(player_hand)
    dealer_score = score_hand(dealer_hand)

    # 1. Player Bust
    if player_score > BLACKJACK_TARGET:
        return 'PLAYER_BUST', 'You bust, dealer wins!'

    # Check for natural blackjacks (2 cards totaling 21 on initial deal)
    player_natural = (len(player_hand) == 2 and player_score == BLACKJACK_TARGET)
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


# ============================================================================
# GUI Application: Object-Oriented Presentation Layer
# ============================================================================

class BlackjackApp:
    """
    Encapsulates the Blackjack GUI, card state, and game lifecycle.
    Eliminates all global variables by storing state in instance attributes.
    """

    def __init__(self, root: tkinter.Tk):
        self.root = root
        self.root.title("Blackjack")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.configure(background=TABLE_BACKGROUND_COLOR, padx=10, pady=10)

        # Allow responsive centering/scaling on window resize
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Async timer management & graceful window destruction
        self._dealer_timer_id = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # Game State Collections
        self.deck = []
        self.all_cards = []
        self.player_hand = []
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
        self.player_score_var = tkinter.IntVar(value=0)
        self.result_var = tkinter.StringVar(value="")

        # Load card visual assets
        self._load_assets()

        # Build interface layout
        self._build_ui()

        # Start first game
        self.new_game()

    def _load_assets(self):
        """Loads 52 card face images and the card back image."""
        load_images(self.all_cards)
        back_path = ASSETS_DIR / "back.png"
        self.back_image = tkinter.PhotoImage(file=str(back_path))

    def _build_ui(self):
        """Builds all Tkinter frames, scoreboards, card tables, and action buttons."""
        # Top Scoreboard: Win/Tie counters and status message
        scoreboard_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        scoreboard_frame.grid(row=0, column=0, columnspan=3, pady=(0, 10))

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

        # Status / Result banner
        self.result_label = tkinter.Label(
            scoreboard_frame, textvariable=self.result_var, font=("Arial", 13, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#ffeb3b"
        )
        self.result_label.grid(row=1, column=0, columnspan=6, pady=5)

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

        # Bottom Button Bar
        button_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="ew", pady=15)

        self.hit_button = tkinter.Button(
            button_frame, text="Hit", width=10, font=("Arial", 10, "bold"),
            command=self.on_hit
        )
        self.hit_button.grid(row=0, column=0, padx=10)

        self.stand_button = tkinter.Button(
            button_frame, text="Stand", width=10, font=("Arial", 10, "bold"),
            command=self.on_stand
        )
        self.stand_button.grid(row=0, column=1, padx=10)

        self.new_game_button = tkinter.Button(
            button_frame, text="New Game", width=10, font=("Arial", 10, "bold"),
            command=self.new_game
        )
        self.new_game_button.grid(row=0, column=2, padx=10)

    # ------------------------------------------------------------------------
    # Game Flow & Actions
    # ------------------------------------------------------------------------

    def new_game(self):
        """Starts a fresh round of Blackjack with a newly shuffled deck."""
        # 0. Cancel any active dealer timer from a prior round
        if self._dealer_timer_id:
            try:
                self.root.after_cancel(self._dealer_timer_id)
            except Exception:
                pass
            self._dealer_timer_id = None

        # 1. Reset deck and hands
        self.deck = list(self.all_cards)
        random.shuffle(self.deck)
        self.player_hand.clear()
        self.dealer_hand.clear()
        self.dealer_hole_card = None
        self.dealer_hole_widget = None

        # 2. Clear card visuals from frames
        for child in self.dealer_cards_frame.winfo_children():
            child.destroy()
        for child in self.player_cards_frame.winfo_children():
            child.destroy()

        # 3. Reset result text and control buttons
        self.result_var.set("")
        self._set_action_buttons_state("normal")
        self.new_game_button.configure(state="normal")

        # 4. Authentic initial deal:
        # Player gets 2 cards face-up
        self._deal_card_to_player()
        self._deal_card_to_player()

        # Dealer gets 1 card face-up and 1 card face-down (the hole card)
        self._deal_card_to_dealer(is_hole_card=False)
        self._deal_card_to_dealer(is_hole_card=True)

        # 5. Check for Natural Blackjack on deal (both player and dealer)
        self._check_initial_blackjack()

    def _draw_card(self):
        """Pops the next card from the deck, reshuffling if necessary."""
        if not self.deck:
            self.deck = list(self.all_cards)
            random.shuffle(self.deck)
        return self.deck.pop()

    def _deal_card_to_player(self):
        """Deals one card to the player and updates the player's score."""
        card = self._draw_card()
        self.player_hand.append(card)
        tkinter.Label(self.player_cards_frame, image=card[1], relief="raised").pack(side="left", padx=2)
        self.player_score_var.set(score_hand(self.player_hand))

    def _deal_card_to_dealer(self, is_hole_card=False):
        """
        Deals one card to the dealer.
        If `is_hole_card` is True, renders `back.png` and hides its score until Stand.
        """
        card = self._draw_card()
        self.dealer_hand.append(card)

        if is_hole_card:
            # Face-down hole card
            self.dealer_hole_card = card
            self.dealer_hole_widget = tkinter.Label(
                self.dealer_cards_frame, image=self.back_image, relief="raised"
            )
            self.dealer_hole_widget.pack(side="left", padx=2)
            # Display only the upcard score while hole card remains hidden
            upcard_score = score_hand([self.dealer_hand[0]])
            self.dealer_score_var.set(f"{upcard_score} + ?")
        else:
            # Face-up card
            tkinter.Label(
                self.dealer_cards_frame, image=card[1], relief="raised"
            ).pack(side="left", padx=2)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))

    def _check_initial_blackjack(self):
        """
        Inspects hands immediately after initial deal for Natural Blackjacks (21 on 2 cards).
        Resolves immediately if either player or dealer has 21.
        """
        player_score = score_hand(self.player_hand)
        dealer_score = score_hand(self.dealer_hand)
        if player_score == BLACKJACK_TARGET or dealer_score == BLACKJACK_TARGET:
            # Natural Blackjack on initial deal! Reveal hole card and resolve immediately
            self._reveal_dealer_hole_card()
            self._conclude_round()

    def _reveal_dealer_hole_card(self):
        """Flips the dealer's hole card face-up and displays the full dealer score."""
        if self.dealer_hole_widget and self.dealer_hole_card:
            self.dealer_hole_widget.configure(image=self.dealer_hole_card[1])
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))

    def on_hit(self):
        """
        Handles the 'Hit' player action.
        Deals a card to the player, checks for bust or auto-stand at 21.
        """
        self._deal_card_to_player()
        current_score = score_hand(self.player_hand)

        if current_score > BLACKJACK_TARGET:
            # Player Busted! Reveal hole card and conclude round via unified handler
            self._reveal_dealer_hole_card()
            self._conclude_round()
        elif current_score == BLACKJACK_TARGET:
            # Player reached 21! Auto-stand to prevent accidental bust
            self.on_stand()

    def on_stand(self):
        """
        Handles the 'Stand' player action.

        Educational Note:
        To prevent race conditions, action buttons must be DISABLED IMMEDIATELY
        before scheduling asynchronous dealer steps with `root.after()`.
        """
        # 1. Immediately disable action buttons (prevents duplicate clicks / re-entrancy)
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")

        # 2. Reveal dealer's face-down hole card
        self._reveal_dealer_hole_card()

        # 3. Begin non-blocking dealer card drawing
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
                self.dealer_cards_frame, image=card[1], relief="raised"
            ).pack(side="left", padx=2)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))

            # Schedule the next dealer step after the delay
            self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        else:
            # Dealer stands or busts; conclude round
            self._conclude_round()

    def _conclude_round(self):
        """Determines the winner, updates win counters, and enables 'New Game'."""
        outcome, message = determine_outcome(self.player_hand, self.dealer_hand)
        self.result_var.set(message)

        if outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
            self.player_wins_var.set(self.player_wins_var.get() + 1)
        elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
            self.dealer_wins_var.set(self.dealer_wins_var.get() + 1)
        elif outcome == 'PUSH':
            self.ties_var.set(self.ties_var.get() + 1)

        # Disable Hit/Stand, enable New Game
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="normal")

    def _set_action_buttons_state(self, state: str):
        """Helper to set the state of both Hit and Stand buttons simultaneously."""
        self.hit_button.configure(state=state)
        self.stand_button.configure(state=state)

    def _on_close(self):
        """Safely cleans up any pending timer callback before window destruction."""
        if self._dealer_timer_id:
            try:
                self.root.after_cancel(self._dealer_timer_id)
            except Exception:
                pass
            self._dealer_timer_id = None
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
