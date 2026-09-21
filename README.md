# Blackjack (Python & Tkinter)

An interactive, graphical desktop implementation of the classic casino card game **Blackjack**, built with standard Python and Tkinter.

Designed as an educational project for Python learners and junior developers, this codebase demonstrates how to transition from basic procedural scripting to clean, production-quality Python: eliminating global variables with Object-Oriented Programming (OOP), handling event loops without freezing the GUI, and writing unit tests to protect against regressions.

---

## Table of Contents
- [Features](#features)
- [How to Run](#how-to-run)
- [Game Rules & Flow](#game-rules--flow)
- [Project Architecture & Key Lessons](#project-architecture--key-lessons)
  - [1. Eliminating Global State with OOP](#1-eliminating-global-state-with-oop)
  - [2. The Tkinter Event Loop: `root.after()` vs. `time.sleep()`](#2-the-tkinter-event-loop-rootafter-vs-timesleep)
  - [3. Preventing Race Conditions & Re-Entrancy](#3-preventing-race-conditions--re-entrancy)
  - [4. Dynamic Ace Valuation Algorithm](#4-dynamic-ace-valuation-algorithm)
  - [5. Portable Path Handling with `pathlib`](#5-portable-path-handling-with-pathlib)
- [Automated Testing](#automated-testing)
- [File Structure](#file-structure)

---

## Features

- **Casino Felt GUI**: Visual card display on a classic green felt table with borderless cards and authentic layout.
- **Dual Play Modes (Chips Mode Toggle)**:
  - **Casual Mode (Chips OFF)**: Instant deals, zero-stress casual play with win/loss tracking and no bankroll overhead.
  - **Casino Mode (Chips ON)**: Authentic wagering system with a $1,000 starting bankroll, authentic casino chips ($5, $25, $100, $500), an **"All In"** button to easily bet entire bankrolls (even odd sums like $187), staged betting, 3:2 Natural Blackjack payouts, and a $1,000 rebuy feature.
- **Authentic Dealer Hole Card**: Dealer receives one card face-up and one card face-down (`back.png`). The hidden card is revealed only after the player stands.
- **Dynamic Score Tracking**: Dealer's visible score shows only the upcard (`"X + ?"`) until the hole card is revealed.
- **Scoreboard Tracking**: Real-time tracking of Dealer Wins, Player Wins, Ties, and Bankroll.
- **Insurance Option**: When the dealer's visible upcard is an Ace in Casino Mode, players are offered an Insurance side bet costing half their main bet and paying 2:1 against a Dealer Natural Blackjack (with odd-bet rounding ensuring an exact $0 net breakeven round on all wagers).
- **Hand Splitting**: When dealt a pair of cards of the same rank, split into two independent hands with active hand indicators and multi-hand resolution. In Chips Mode, Hand 2 requires an additional matching bet.
- **Natural Blackjack Detection**: Automatically detects 2-card 21s for both player and dealer on the deal, paying 3:2 in Chips Mode.
- **Auto-Stand Protection**: Automatically stands when a player hits to 21, preventing accidental bust clicks.
- **Non-Blocking Dealing Cadence**: Smooth, observable 700ms dealing pace without GUI freezes.
- **Zero External Dependencies**: Runs entirely on Python's built-in standard library (`tkinter`, `random`, `pathlib`, `unittest`).

---

## How to Run

### Requirements
- Python 3.8+ (including Python 3.12, 3.13, 3.14+)
- Tkinter (included by default with standard Windows and macOS Python installers)

### Launching the Game
From the project directory:
```bash
python blackjack.py
```

Or from a parent directory:
```bash
python Blackjack/blackjack.py
```

You can also run the game via the external module test script:
```bash
python import_test.py
```

---

## Game Rules & Flow

```
                     +---------------------------+
                     |        Initial Deal       |
                     |  Player: 2 cards face-up  |
                     |  Dealer: 1 up, 1 hole (?) |
                     +-------------+-------------+
                                   |
                +------------------┴------------------+
                | Does Player or Dealer have 21?      |
                +-------+---------------------+-------+
                   YES  |                     | NO
                        ▼                     ▼
           +-----------------------+     +-----------------------+
           | Reveal Dealer Hole    |     |      Player Turn      |
           | Check for Tie / Win   |     | [Hit] -> Draw card    |
           +-----------------------+     | [Stand] -> End turn   |
                                         +-----------+-----------+
                                                     | (Stand or 21)
                                                     ▼
                                         +-----------------------+
                                         |      Dealer Turn      |
                                         | Flip Hole Card        |
                                         | Hit while score < 17  |
                                         | Stand on 17+          |
                                         +-----------+-----------+
                                                     |
                                                     ▼
                                         +-----------------------+
                                         |     Resolve Winner    |
                                         | Update Win Counters   |
                                         | Enable [New Game]     |
                                         +-----------------------+
```

1. **Card Values**:
   - Number cards `2` through `10` are worth their face value.
   - Face cards (`Jack`, `Queen`, `King`) are each worth `10`.
   - `Ace` is worth `11` or `1` depending on which gives the highest non-busting total.
2. **Player Actions**:
   - **Hit**: Draw an additional card. If your score exceeds 21, you bust and the dealer wins immediately.
   - **Stand**: Conclude your turn and pass control to the dealer (or the next split hand).
   - **Split**: If dealt two cards of matching rank on the deal, separate them into two hands, each receiving a new card and played independently.
3. **Dealer Rules**:
   - The dealer must hit on any score below 17.
   - The dealer must stand on 17 or higher (standard casino S17 rule).

---

## Project Architecture & Key Lessons

For Python learners, this project illustrates several fundamental software engineering principles:

### 1. Eliminating Global State with OOP
Many beginner tutorials use global variables (`global deck`, `global player_hand`, `global score`) to share state between functions. While simple for short scripts, globals quickly lead to unpredictable bugs when functions overwrite each other's data.

In this refactored version, all game state, card decks, and UI controls are encapsulated within the `BlackjackApp` class:

```python
class BlackjackApp:
    def __init__(self, root):
        self.root = root
        self.deck = []
        self.player_hand = []
        self.dealer_hand = []
        # State variables are safely bound to the instance (self)
```

### 2. The Tkinter Event Loop: `root.after()` vs. `time.sleep()`
A common mistake in GUI programming is using `time.sleep()` to pause execution (e.g., between dealer card draws).

- **Why `time.sleep()` breaks GUIs**: Tkinter is single-threaded. Its `mainloop()` continuously listens for mouse clicks, keyboard input, and window redrawing. Calling `time.sleep(1)` halts the entire thread—the window stops responding and buttons freeze.
- **The Solution**: `self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)` asks the Tkinter scheduler to call a function after a delay, immediately releasing control back to the event loop so the window remains smooth and responsive:

```python
def _dealer_step(self):
    if dealer_should_hit(self.dealer_hand):
        self._deal_card_to_dealer()
        # Schedule the next draw in 700ms without freezing the GUI
        self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
    else:
        self._conclude_round()
```

### 3. Preventing Race Conditions & Re-Entrancy
When an asynchronous or timed action begins, user input must be restricted. If the player could click "Hit", "Stand", or "New Game" while the dealer was drawing, multiple functions would execute concurrently and corrupt the game state.

Before scheduling the dealer's timer, we explicitly disable the action buttons:

```python
def on_stand(self):
    # Immediately disable buttons before starting the asynchronous sequence
    self._set_action_buttons_state("disabled")
    self.new_game_button.configure(state="disabled")
    self._reveal_dealer_hole_card()
    self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
```

### 4. Dynamic Ace Valuation Algorithm
Blackjack hands with Aces can be "soft" (Ace counted as 11) or "hard" (Ace counted as 1).

Because $11 + 11 = 22 > 21$, a hand can **never** have more than one Ace counted as 11. Rather than complex state flags inside a loop, the pure logic function `score_hand(hand)` sums all cards with Aces initially counted as 1, then promotes at most one Ace to 11 if doing so does not cause a bust:

```python
def score_hand(hand):
    values = [card[0] if isinstance(card, (tuple, list)) else card for card in hand]
    score = sum(values)
    # If an Ace is present and counting it as 11 doesn't bust, add 10
    if 1 in values and score + 10 <= BLACKJACK_TARGET:
        score += 10
    return score
```

### 5. Portable Path Handling with `pathlib`
Hardcoding relative paths like `"cards/1_heart.png"` causes scripts to fail if executed from a different working directory. Using Python's modern `pathlib` module ensures the assets are always located relative to the script's actual file path:

```python
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent / "cards"
card_image_path = ASSETS_DIR / f"{card}_{suit}.png"
```

---

## Automated Testing

The project includes a comprehensive automated test suite with **63 unit tests** written with Python's built-in `unittest` framework.

### Running the Tests
To run all tests with verbose output:

```bash
python -m unittest discover tests -v
```

### Test Coverage Summary
| Test File | Description |
| :--- | :--- |
| [`tests/test_scoring.py`](tests/test_scoring.py) | Verifies `score_hand()` across empty hands, multiple Aces, soft-to-hard shifts, and busts. |
| [`tests/test_deck.py`](tests/test_deck.py) | Verifies all 52 card PNGs and `back.png` exist, validates deck distribution, and tests `Card` tuple subclass properties. |
| [`tests/test_game_rules.py`](tests/test_game_rules.py) | Tests win/loss/push evaluations, dealer AI hit/stand rules, and Natural Blackjack detection on both player and dealer. |
| [`tests/test_gui_state.py`](tests/test_gui_state.py) | Validates actual `BlackjackApp` widget states (Hit, Stand, New Game buttons, ties, timer cleanup) across real game lifecycle transitions. |
| [`tests/test_split.py`](tests/test_split.py) | Tests hand split qualification (`can_split`), multi-hand turn progression, button states, and independent outcome resolution. |
| [`tests/test_betting.py`](tests/test_betting.py) | Tests pure payout calculations (3:2, 1:1, push, loss), 2:1 insurance payouts with odd-bet breakeven guarantees, Casual vs. Casino mode toggling, staged chip betting, "All In" max wagering, split wagers, insurance prompts and decisions, and the rebuy mechanic. |

---

## File Structure

```
Blackjack/
├── blackjack.py           # Main application: pure game engine & Tkinter GUI
├── import_test.py         # Demonstrates importing and running the game externally
├── README.md              # Documentation and learning guide
├── .gitignore             # Git exclusions for Python cache, IDEs, and OS artifacts
├── cards/                 # 52 playing card images + back.png and jokers
└── tests/                 # Automated test suite (63 tests)
    ├── __init__.py
    ├── test_betting.py
    ├── test_deck.py
    ├── test_game_rules.py
    ├── test_gui_state.py
    ├── test_scoring.py
    └── test_split.py
```
