# Blackjack (Python & Tkinter)

> 🎮 **Play the Game**: Download the standalone, zero-install Windows release on itch.io:  
> 👉 **[https://wrehman.itch.io/blackjack-classic](https://wrehman.itch.io/blackjack-classic)** *(No Python setup required!)*

An interactive, graphical desktop implementation of the classic casino card game **Blackjack**, built with standard Python and Tkinter.

Designed as an educational project for Python learners and junior developers, this codebase demonstrates how to transition from basic procedural scripting to clean, production-quality Python: eliminating global variables with Object-Oriented Programming (OOP), handling event loops without freezing the GUI, and writing unit tests to protect against regressions.

---

## Table of Contents
- [Play Online / Download (itch.io)](#play-online--download-itchio)
- [Features](#features)
- [How to Run (Developers)](#how-to-run-developers)
- [Game Rules & Flow](#game-rules--flow)
  - [Keyboard Shortcuts & Controls](#keyboard-shortcuts--controls)
- [Project Architecture & Key Lessons](#project-architecture--key-lessons)
  - [1. Eliminating Global State with OOP](#1-eliminating-global-state-with-oop)
  - [2. The Tkinter Event Loop: `root.after()` vs. `time.sleep()`](#2-the-tkinter-event-loop-rootafter-vs-timesleep)
  - [3. Preventing Race Conditions & Re-Entrancy](#3-preventing-race-conditions--re-entrancy)
  - [4. Dynamic Ace Valuation Algorithm](#4-dynamic-ace-valuation-algorithm)
  - [5. Portable Asset Resolution & PyInstaller Bundling](#5-portable-asset-resolution--pyinstaller-bundling)
- [Automated Testing](#automated-testing)
- [File Structure](#file-structure)

---

## Features

- **Casino Felt GUI**: Visual card display on a classic green felt table with borderless cards and authentic layout.
- **Dual Play Modes (Chips Mode Toggle)**:
  - **Casual Mode (Chips OFF)**: Instant deals, zero-stress casual play with win/loss tracking and no bankroll overhead.
  - **Casino Mode (Chips ON)**: Authentic wagering system with a $1,000 starting bankroll, authentic casino chips ($5, $25, $100, $500), an **"All In"** button to easily bet entire bankrolls (even odd sums like $187), staged betting, 3:2 Natural Blackjack payouts, and a $1,000 rebuy feature. Switching modes prompts a confirmation warning to prevent accidental forfeiture, resetting to the default $1,000 upon return.
- **Multi-Deck Shoe & Cut Card Penetration**: 4-deck shoe (208 cards) by default with persistent card depletion across rounds, live card count indicator, and an authentic ~25% cut card penetration reshuffle trigger.
- **Double Down Option**: Double down on initial 2-card hands (and 2-card split hands), doubling the wager, drawing exactly one card, and standing automatically.
- **Late Surrender**: Forfeit initial 2-card hands after the dealer peeks for Natural Blackjack to recover 50% of the initial wager.
- **Procedural 2.5D Chip Visualizer & Micro-Animations**: A casino felt betting circle displaying live 3D stacked chips with drop shadows, clay edge stripes, and dynamic micro-animations for chip drops, dealer payouts, house scoops, and pushes.
- **Authentic Dealer Hole Card**: Dealer receives one card face-up and one card face-down (`back.png`). The hidden card is revealed only after the player stands (or when round resolves early).
- **Dynamic Score Tracking**: Dealer's visible score shows only the upcard (`"X + ?"`) until the hole card is revealed.
- **Scoreboard Tracking**: Real-time tracking of Dealer Wins, Player Wins, Ties, Shoe cards remaining, and Bankroll.
- **Insurance Option**: When the dealer's visible upcard is an Ace in Casino Mode, players are offered an Insurance side bet costing half their main bet and paying 2:1 against a Dealer Natural Blackjack (with odd-bet rounding ensuring an exact $0 net breakeven round on all wagers).
- **Hand Splitting**: When dealt a pair of cards of the same rank, split into two independent hands with active hand indicators, Double After Split (DAS) support, and multi-hand resolution (with split 21s evaluated as standard 21s paying 1:1).
- **Natural Blackjack Detection**: Automatically detects 2-card 21s for both player and dealer on the deal, paying 3:2 in Chips Mode.
- **Auto-Stand Protection**: Automatically stands when a player hits or doubles to 21, preventing accidental bust clicks.
- **Mid-Hand Guarding**: Action buttons and New Game controls strictly guard against accidental mid-hand forfeit or re-entrancy.
- **Non-Blocking Dealing Cadence**: Smooth, observable 700ms dealing pace without GUI freezes.
- **Authentic Casino Audio Effects (`.ogg`)**: Tactile sound effects powered by `pygame.mixer` (via `pygame-ce`), featuring 42 organic audio variations: randomized card slides for dealing, crisp card placement on hole card reveals, riffle shoe shuffles, tactile chip drop and collision clicks, heavy all-in stacks, dealer chip rakes, and payout slides.
- **Audio Mute & Accessibility**: Top scoreboard mute toggle (`🔊 Sound: ON` / `🔇 Sound: OFF`) and keyboard shortcut (`M`) for instant muting. Graceful headless fallback if audio devices or packages are unavailable.
- **Interactive Keyboard Shortcut Overlay**: Visual in-game HUD dialog accessible via the `[?] Help` button or hotkeys (`?`, `/`, `F1`), illustrating all gameplay, betting, insurance, and system controls with curated Kenney keycap badges.
- **Hands-Free Keyboard Accessibility**: Full keyboard controls for fast, mouse-free play:
  - `Space` / `Enter` (Contextual Deal / Hit / Next Game), `H` (Hit), `S` (Stand), `D` (Double), `P` (Split), `R` (Surrender)
  - `1`, `2`, `3`, `4` ($5, $25, $100, $500 chips), `A` (All-In), `C` (Clear Bet)
  - `Y` / `N` (Insurance), `M` (Mute Audio), `?` / `F1` (Help HUD), `Esc` (Close / Decline)
- **Zero Required External Dependencies**: Core game logic, cards, and GUI run entirely on Python's standard library (`tkinter`, `random`, `pathlib`, `unittest`). Audio support is optional via `pygame-ce`.

## Play Online / Download (itch.io)

For casual players and non-engineers who want to play without installing Python or touching a command line:

👉 **Download the Standalone Game on itch.io**:  
**[https://wrehman.itch.io/blackjack-classic](https://wrehman.itch.io/blackjack-classic)**

- **Platform**: Windows 64-bit (Standalone portable release)
- **Zero Installation**: Simply extract the ZIP and double-click `Blackjack.exe` to play.
- **Features Included**: Complete game with 4-deck shoe, 2.5D stacked chip animations, and 42 authentic `.ogg` casino sound effects bundled.

---

## How to Run (Developers)

### Requirements
- Python 3.8+ (including Python 3.12, 3.13, 3.14+)
- Tkinter (included by default with standard Windows and macOS Python installers)
- **Audio Support (Optional)**: `pip install pygame-ce` (enables realistic casino `.ogg` audio effects; if omitted, the game runs smoothly in silent fallback mode)

### Launching the Game from Source
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

### Packaging for Distribution (Standalone Executable / itch.io)
To compile the standalone Windows release uploaded to [itch.io](https://wrehman.itch.io/blackjack-classic):
1. Double-click `build_itch_release.bat` (or run `./build_itch_release.ps1` in PowerShell).
2. The automated pipeline runs regression tests, invokes PyInstaller, bundles documentation, and outputs:
   - `dist/Blackjack-Windows/`: Unpacked folder containing `Blackjack.exe` and bundled assets.
   - `dist/Blackjack-Windows-v1.0.0.zip`: Optimized ZIP archive ready to upload to [itch.io](https://wrehman.itch.io/blackjack-classic).

For complete store page copy, metadata, and upload instructions, see [docs/ITCH_IO_GUIDE.md](docs/ITCH_IO_GUIDE.md).

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
   - **Double**: Available on initial 2 cards (including after a split). Doubles your wager, draws exactly one card, and automatically stands.
   - **Split**: If dealt two cards of matching rank on the deal, separate them into two hands, each receiving a new card and played independently.
   - **Surrender**: Forfeit initial 2-card hands (before hitting/splitting) after the dealer peeks for Blackjack, recovering 50% of your wager.
3. **Dealer Rules**:
   - The dealer must hit on any score below 17.
   - The dealer must stand on 17 or higher (standard casino S17 rule).

### Keyboard Shortcuts & Controls

The game supports complete hands-free keyboard navigation with context-sensitive key bindings:

| Shortcut | Context | Action |
| :--- | :--- | :--- |
| `Space` / `Enter` | Any Phase | **Context-Sensitive**: Deal Bet (Betting) / Hit (Turn) / New Game (Round Over) |
| `H` | Player Turn | **Hit** (Draw another card) |
| `S` | Player Turn | **Stand** (End turn; dealer plays) |
| `D` | Initial 2 Cards | **Double Down** (Double bet, draw 1 card, auto-stand) |
| `P` | Equal Rank Pair | **Split** (Split into two independent hands) |
| `R` | Initial 2 Cards | **Surrender** (Forfeit hand, recover 50% wager) |
| `1`, `2`, `3`, `4` | Betting Phase | Stage $5, $25, $100, or $500 chip |
| `A` | Betting Phase | **All In** (Wager entire bankroll) |
| `C` | Betting Phase | **Clear Bet** (Reset staged bet to $0) |
| `Y` / `N` (or `Esc`)| Dealer Shows Ace | **Take** or **Decline** Insurance (2:1 side bet) |
| `M` | Any Time | Toggle Sound Mute (`ON` / `OFF`) |
| `?` / `/` / `F1` | Any Time | Toggle Keyboard Shortcuts Help Overlay |
| `Escape` | Overlay Active | Close Help Overlay |

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

### 5. Portable Asset Resolution & PyInstaller Bundling
Hardcoding relative paths like `"cards/1_heart.png"` causes scripts to fail when executed from another working directory or packaged into standalone executables via PyInstaller.

The project implements a resilient multi-tier path resolver (`get_base_dir()`) that guarantees assets load seamlessly across standard source runs, PyInstaller `--onefile` temp directories (`sys._MEIPASS`), and PyInstaller `--onedir` release folders (`_internal/`):

```python
def get_base_dir() -> Path:
    """Resolves asset directory across standard execution and PyInstaller bundles."""
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            return Path(sys._MEIPASS)
        exe_parent = Path(sys.executable).resolve().parent
        if (exe_parent / "cards").exists():
            return exe_parent
        if (exe_parent / "_internal" / "cards").exists():
            return exe_parent / "_internal"
    return Path(__file__).resolve().parent

BASE_DIR = get_base_dir()
ASSETS_DIR = BASE_DIR / "cards"
OVERLAY_ICONS_DIR = BASE_DIR / "assets" / "overlay_icons"
```

Additionally, transparent PNG assets (like the 64×64 Kenney prompt icons) are scaled down using Tkinter's native `PhotoImage.subsample(2, 2)` method, producing crisp 32×32 pixel badges without requiring heavy third-party image manipulation libraries like Pillow.

---

## Automated Testing

The project includes a comprehensive automated test suite with **102 unit tests** written with Python's built-in `unittest` framework.

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
| [`tests/test_shoe.py`](tests/test_shoe.py) | Verifies 4-deck shoe composition (208 cards), persistence across consecutive rounds, cut-card penetration triggers (~25%), and UI count display. |
| [`tests/test_game_rules.py`](tests/test_game_rules.py) | Tests win/loss/push evaluations, dealer AI hit/stand rules, Natural Blackjack vs split 21s (1:1 payout), and surrender payouts. |
| [`tests/test_double_down.py`](tests/test_double_down.py) | Tests Double Down eligibility (2 cards only, bankroll checks), wager doubling, single card draw, auto-stand, and bust resolution. |
| [`tests/test_surrender.py`](tests/test_surrender.py) | Tests Late Surrender eligibility (initial 2 cards only, un-split), 50% wager refund, hole card reveal, and dealer win recording. |
| [`tests/test_gui_state.py`](tests/test_gui_state.py) | Validates actual `BlackjackApp` widget states (Hit, Stand, Double, Split, Surrender, New Game buttons, ties, timer cleanup) across real game lifecycle transitions. |
| [`tests/test_split.py`](tests/test_split.py) | Tests hand split qualification (`can_split`), multi-hand turn progression, button states, and independent outcome resolution. |
| [`tests/test_betting.py`](tests/test_betting.py) | Tests pure payout calculations (3:2, 1:1, push, loss, surrender), 2:1 insurance payouts with odd-bet breakeven guarantees, greedy chip denomination breakdowns, ChipVisualizer state sync/animations, Casual vs. Casino mode toggle confirmation warnings and bankroll resets, staged chip betting, "All In" max wagering, split wagers, insurance prompts and decisions, and the rebuy mechanic. |
| [`tests/test_sound.py`](tests/test_sound.py) | Validates SoundManager audio engine, 42-file .ogg catalog loading across 10 categories, polyphony, volume clamping, mute toggling, UI sound button synchronization, keyboard shortcut integration, and headless fail-safe degradation. |
| [`tests/test_shortcuts_overlay.py`](tests/test_shortcuts_overlay.py) | Verifies curated Kenney prompt icon asset integrity, `KeyboardIconLoader` scaling & caching, `[?] Help` button placement, dialog open/close lifecycle, keyboard event dismissal (`Escape`, `?`), and game state immutability. |

---

## File Structure

```
Blackjack/
├── blackjack.py              # Main application: pure game engine, SoundManager, KeyboardIconLoader & GUI
├── blackjack.spec            # PyInstaller build spec for itch.io packaging
├── build_itch_release.bat    # Windows 1-click build batch wrapper
├── build_itch_release.ps1    # Automated PowerShell build, test, and zip packaging pipeline
├── import_test.py            # External import verification test
├── README.md                 # Project documentation and architectural guide
├── README_PLAYERS.txt        # End-user player guide bundled with releases
├── .gitignore                # Git exclusions (caches, IDEs, builds, raw asset packs)
├── cards/                    # 52 playing card PNG images + back.png and jokers
├── audio/                    # 42 tactile casino .ogg audio files (slides, chips, shuffles)
├── assets/                   # Release packaging assets
│   ├── overlay_icons/        # 20 curated 64x64 PNG keyboard & mouse prompt icons
│   ├── icon.ico / icon.png   # Window and executable icons
│   ├── cover_itch.png        # Storefront marketing cover art
│   └── screenshots/          # High-resolution gameplay captures
├── docs/
│   └── ITCH_IO_GUIDE.md      # itch.io deployment, store copy, and release guide
└── tests/                    # Automated test suite (102 tests)
    ├── __init__.py
    ├── test_betting.py
    ├── test_deck.py
    ├── test_double_down.py
    ├── test_game_rules.py
    ├── test_gui_state.py
    ├── test_scoring.py
    ├── test_shoe.py
    ├── test_shortcuts_overlay.py
    ├── test_sound.py
    ├── test_split.py
    └── test_surrender.py
```
