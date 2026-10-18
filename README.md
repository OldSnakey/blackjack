# Blackjack v1.3.0 (Python & Tkinter)

> 🎮 **Play the Game**: Download the standalone, zero-install Windows release on itch.io:  
> 👉 **[https://wrehman.itch.io/blackjack-classic](https://wrehman.itch.io/blackjack-classic)** *(No Python setup required!)*

An interactive, graphical desktop implementation of the classic casino card game **Blackjack**, built with standard Python and Tkinter, featuring an **animated living dealer**, a supernatural **Haunted Halloween & Hell's Table expansion**, **2x HiDPI scaling**, and persistent **Hall of Fame & Achievements**.

Designed as an educational project for Python learners and junior developers, this codebase demonstrates how to transition from basic procedural scripting to clean, production-quality Python: eliminating global variables with Object-Oriented Programming (OOP), managing non-blocking animations without freezing the GUI event loop, decoupling stage canvas rendering from table felt geometry, and authoring exhaustive automated regression tests (234 tests).

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
  - [6. Horizon Stage vs. Card Table Felt Decoupling](#6-horizon-stage-vs-card-table-felt-decoupling)
  - [7. Persistent State & Achievement Tracking](#7-persistent-state--achievement-tracking)
- [Automated Testing](#automated-testing)
- [File Structure](#file-structure)

---

## Features

- **Casino Felt GUI & Panoramic Horizon Stage**: Re-architected two-tier layout dividing an atmospheric upper room stage from the card table felt via a 3D wooden horizon rail.
- **Living Dealer Animation Engine (`dealer_actor.py`)**:
  - Autonomous idle breathing cycle and procedural eye-blinking timers.
  - Expressive talking mouth frames and dynamic arm gestures for wins, busts, and blackjacks.
  - Interactive speech bubbles with responsive typewriter dialogue.
  - Curated panoramic backdrops (*Casino*, *Crypt*, *Creep*, *Hell*, *Celestial*) with synchronized flickering sconce lighting.
- **Haunted Halloween & Hell's Table Expansion (`haunted_manager.py`)**:
  - Progressive supernatural narrative phases: `CLASSIC` → `CREEP` → `OMEN` → `SNUFFING` → `HELL_TABLE`.
  - Authentic custom **13 of Skulls** cursed card with authentic host deck geometry and typography.
  - Haunted Altar with 5 candles that snuff out on player busts/losses, summoning 2.5D rising gravestones.
  - Showdown against **The Pit Fiend** with a 2.5D Animated Tug-of-War Soul Meter and Celestial Blessings (*St. Jude's Grace*, *Archangel's Smite*, *Eye of Providence*, *Aegis of Dawn*, *Holy Water*).
- **Dealer Wardrobe & Costumes (`dealer_wardrobe_dialog.py`)**:
  - Change dealer attire anytime (`Shift + W`): *Classic*, *Tiffany* noir, *The Pit Fiend*, and the celestial *Seraph* (awarded for exorcising the demon).
- **Hall of Fame & Save Persistence (`save_manager.py`)**:
  - Persistent career metrics (`blackjack_save.json`): Peak Bankroll, Longest Win Streak, Total Blackjacks, and Hell's Table Clears.
  - 6 unlockable gameplay achievements (*Exorcist*, *High Roller*, *Natural Streak*, *Cursed Survivor*, *Split Maestro*, *Big Spender*).
- **Dual Play Modes (Chips Mode Default)**:
  - **Casino Mode (Default)**: Authentic wagering system with a \$1,000 starting bankroll, authentic casino chips (\$5, \$25, \$100, \$500, \$1,000), staged betting, an **"All In"** button, 3:2 Natural Blackjack payouts, and a \$1,000 rebuy feature.
  - **Casual Mode**: Instant deals, zero-stress casual play with win/loss tracking and no bankroll overhead. Switching modes prompts confirmation and automatically persists preferences to disk.
- **2x HiDPI Display Scaling & Fullscreen**:
  - Crisp integer 2x resolution scaling (`Shift + S` / `🔍 2x`) for 1440p and 4K monitors with nearest-neighbor scaled card assets.
  - Borderless Fullscreen mode (`F11` / `⛶ Full`).
- **Multi-Deck Shoe & Cut Card Penetration**: 4-deck shoe (208 cards) with persistent card depletion across rounds, live shoe count, and an authentic ~25% cut card penetration reshuffle trigger.
- **Double Down Option**: Double down on initial 2-card hands (and split hands), doubling the wager, drawing exactly one card, and standing automatically.
- **Late Surrender**: Forfeit initial 2-card hands after dealer peeks for Natural Blackjack to recover 50% of the initial wager.
- **Procedural 2.5D Chip Visualizer**: Stacked clay chips with drop shadows and animations for bets, dealer rakes, payouts, and pushes.
- **Authentic Dealer Hole Card**: Dealer receives one card face-up and one card face-down (`back.png`). The hidden card is revealed only after the player stands (or when round resolves early).
- **Dynamic Score Tracking & Beveled Plaques**: Dealer upcard score shows `"X + ?"` until reveal, framed in antique gold-bordered casino score plaques.
- **Insurance Option**: When the dealer's visible upcard is an Ace in Casino Mode, players are offered an Insurance side bet costing half their main bet and paying 2:1 against a Dealer Natural Blackjack.
- **Hand Splitting**: Split matching rank pairs into two independent hands with active hand indicators, Double After Split (DAS) support, and multi-hand resolution.
- **Auto-Stand & Mid-Hand Guarding**: Automatically stands on 21; action buttons strictly guard against re-entrant input while animations or dealer draws are in flight.
- **Authentic Casino Audio (`.ogg`)**: 42 organic audio variations powered by `pygame.mixer` (via `pygame-ce`): card slides, hole card reveals, shoe shuffles, chip clicks, all-in thuds, rakes, and payout slides.
- **Full Keyboard Accessibility**: High-speed play with context-sensitive bindings and an in-game shortcuts HUD (`?` / `/`).

## Play Online / Download (itch.io)

For casual players and non-engineers who want to play without installing Python or touching a command line:

👉 **Download the Standalone Game on itch.io**:  
**[https://wrehman.itch.io/blackjack-classic](https://wrehman.itch.io/blackjack-classic)**

- **Platform**: Windows 64-bit (Standalone portable release)
- **Zero Installation**: Extract `Blackjack-Windows-v1.3.0.zip` and double-click `Blackjack.exe` to play.
- **Features Included**: Complete game with Living Dealer, Hell's Table, 2x scaling, sound effects, and persistent achievements.

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
   - `dist/Blackjack-Windows-v1.3.0.zip`: Optimized ZIP archive ready to upload to [itch.io](https://wrehman.itch.io/blackjack-classic).

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
| `1`, `2`, `3`, `4`, `5` | Betting Phase | Quick Stage \$5, \$25, \$100, \$500, or \$1,000 chip |
| `A` | Betting Phase | **All In** (Wager entire bankroll) |
| `C` | Betting Phase | **Clear Bet** (Reset staged bet to \$0) |
| `Y` / `N` (or `Esc`)| Dealer Shows Ace | **Take** or **Decline** Insurance (2:1 side bet) |
| `M` | Any Time | Toggle Sound Mute (`ON` / `OFF`) |
| `Shift + S` | Any Time | Toggle **2x HiDPI Display Scaling** |
| `F11` | Any Time | Toggle **Borderless Fullscreen** |
| `Shift + W` | Any Time | Open **Dealer Wardrobe & Costumes** |
| `Shift + H` | Any Time | Open **Hall of Fame & Achievements** |
| `?` / `/` / `F1` | Any Time | Toggle Keyboard Shortcuts Help Overlay |
| `Escape` | Dialog Active | Dismiss Dialog / Overlay |

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

### 6. Horizon Stage vs. Card Table Felt Decoupling
In version 1.3.0, the user interface was decoupled into a strict two-tier architectural model:
- **Horizon Stage (`DealerStageCanvas`)**: Dedicated strictly to the dealer composite actor, panoramic atmospheric room lighting, and narrative dialogue. It maintains a distinct perspective and palette above the 3D wooden horizon rail.
- **Card Table Felt (`TableFeltCanvas`)**: All playing cards, wagering chips, table props (such as the Haunted Altar candles and gravestones), and HUD popups live on the lower felt area. Sub-canvases dynamically crop and synchronize their background slices from the active felt texture, guaranteeing seamless visual continuity across horror phase shifts.

### 7. Persistent State & Achievement Tracking
Career statistics, costume unlocks, and game mode preferences are encapsulated within `SaveManager` (`save_manager.py`). Saved state is serialized to a robust JSON schema (`blackjack_save.json`) with automated corruption recovery, ephemeral directory isolation during headless testing, and atomic disk writes.

---

## Automated Testing

The project includes an exhaustive automated test suite with **234 unit tests** written with Python's built-in `unittest` framework, validating domain logic, Tkinter GUI widgets, audio fallbacks, and rendering geometry.

### Running the Tests
To run all tests with verbose output:

```bash
python -m unittest discover tests -v
```

### Test Coverage Summary
| Test File | Description |
| :--- | :--- |
| [`tests/test_betting.py`](tests/test_betting.py) | Tests pure payout calculations (3:2, 1:1, push, loss, surrender), 2:1 insurance payouts with odd-bet breakeven guarantees, chip denomination breakdowns, ChipVisualizer state sync/animations, default Chips Mode, and bankroll tracking. |
| [`tests/test_dealer_actor.py`](tests/test_dealer_actor.py) | Unit tests for DealerActor sprite compositing, layer positioning, dynamic scale adjustments, and mouth/eye state changes. |
| [`tests/test_dealer_actor_layers.py`](tests/test_dealer_actor_layers.py) | Validates layer coordinate math, anchor positioning, and costume asset resolution across all supported outfits. |
| [`tests/test_dealer_stage_canvas.py`](tests/test_dealer_stage_canvas.py) | Verifies panoramic 1000px/2000px stage backdrop scaling, sconce compositing, and stage lighting across themes. |
| [`tests/test_dealer_wardrobe_dialog.py`](tests/test_dealer_wardrobe_dialog.py) | Tests Dealer Wardrobe dialog lifecycle, costume selection, preview rendering, and unlock requirement enforcement. |
| [`tests/test_deck.py`](tests/test_deck.py) | Verifies all 52 card PNGs and `back.png` exist, validates deck distribution, and tests `Card` tuple subclass properties. |
| [`tests/test_double_down.py`](tests/test_double_down.py) | Tests Double Down eligibility (2 cards only, bankroll checks), wager doubling, single card draw, auto-stand, and bust resolution. |
| [`tests/test_game_rules.py`](tests/test_game_rules.py) | Tests win/loss/push evaluations, dealer AI hit/stand rules, Natural Blackjack vs split 21s (1:1 payout), and surrender payouts. |
| [`tests/test_gui_state.py`](tests/test_gui_state.py) | Validates actual `BlackjackApp` widget states (Hit, Stand, Double, Split, Surrender, New Game buttons, ties, timer cleanup) across real game lifecycle transitions. |
| [`tests/test_hall_of_fame_and_achievements.py`](tests/test_hall_of_fame_and_achievements.py) | Tests Hall of Fame modal GUI, badge rendering, stats aggregation, and achievement unlock triggers. |
| [`tests/test_haunted_mode.py`](tests/test_haunted_mode.py) | Validates Haunted Halloween phase transitions, Card 13 manifestation & immediate deal bust handling, candle snuffing, gravestone rising, Pit Fiend composite, Soul Meter animations, and relic mechanics. |
| [`tests/test_living_animations.py`](tests/test_living_animations.py) | Validates DealerActor autonomous idle breathing, blinking cadence, typewriter speech timers, and gesture transitions. |
| [`tests/test_save_manager.py`](tests/test_save_manager.py) | Validates blank-slate defaults, persistent file I/O, career stats, costume unlocks, corruption recovery, and user preference retention (including default Chips Mode). |
| [`tests/test_scale_and_display_modes.py`](tests/test_scale_and_display_modes.py) | Verifies 1.0x vs 2.0x HiDPI integer scaling, geometry recomputation, and borderless fullscreen toggle. |
| [`tests/test_scoring.py`](tests/test_scoring.py) | Verifies `score_hand()` across empty hands, multiple Aces, soft-to-hard shifts, and busts. |
| [`tests/test_settings_dialog.py`](tests/test_settings_dialog.py) | Tests settings dialog lifecycle, display scaling toggles, sound volume sliders, and preference saving. |
| [`tests/test_shoe.py`](tests/test_shoe.py) | Verifies 4-deck shoe composition (208 cards), persistence across consecutive rounds, cut-card penetration triggers (~25%), and UI count display. |
| [`tests/test_shortcuts_overlay.py`](tests/test_shortcuts_overlay.py) | Verifies curated Kenney prompt icon asset integrity, `KeyboardIconLoader` scaling & caching, `[?] Help` button placement, dialog open/close lifecycle, keyboard event dismissal (`Escape`, `?`), and game state immutability. |
| [`tests/test_sound.py`](tests/test_sound.py) | Validates SoundManager audio engine, 42-file .ogg catalog loading across 10 categories, polyphony, volume clamping, mute toggling, UI sound button synchronization, keyboard shortcut integration, and headless fail-safe degradation. |
| [`tests/test_split.py`](tests/test_split.py) | Tests hand split qualification (`can_split`), multi-hand turn progression, button states, and independent outcome resolution. |
| [`tests/test_surrender.py`](tests/test_surrender.py) | Tests Late Surrender eligibility (initial 2 cards only, un-split), 50% wager refund, hole card reveal, and dealer win recording. |
| [`tests/test_table_felt.py`](tests/test_table_felt.py) | Validates procedural canvas texture generation, theme switching (casino/creep/hell), and child coordinate slice extraction. |
| [`tests/test_table_hud.py`](tests/test_table_hud.py) | Tests 2.5D animated announcement HUD popups, banner styling, and auto-dismiss timers on the table felt. |
| [`tests/test_ui_geometry_and_rendering.py`](tests/test_ui_geometry_and_rendering.py) | Validates zero card clipping, beveled plaque geometry, TableAnnouncementHUD auto-dismiss, and OMEN altar color synchronization. |
| [`tests/test_version.py`](tests/test_version.py) | Enforces single source of truth for versioning across `blackjack.py`, specifications, and documentation. |

---

## File Structure

```
Blackjack/
├── blackjack.py                    # Main application: game engine, SoundManager, KeyboardIconLoader & GUI
├── blackjack.spec                  # PyInstaller build spec for itch.io packaging
├── build_itch_release.bat          # Windows 1-click build batch wrapper
├── build_itch_release.ps1          # Automated PowerShell build, test, and zip packaging pipeline
├── dealer_actor.py                 # Living Dealer animation engine: composite sprites, breathing, blinking
├── dealer_wardrobe_dialog.py       # Modal dialog for previewing and equipping dealer costumes
├── haunted_manager.py              # Haunted Halloween narrative state: phases, altar candles, relics
├── save_manager.py                 # Persistent save data, stats tracking, and achievement unlocks
├── import_test.py                  # External import verification test
├── README.md                       # Project documentation and architectural guide
├── README_PLAYERS.txt              # End-user player guide bundled with releases
├── .gitignore                      # Git exclusions (caches, IDEs, builds, raw asset packs)
├── cards/                          # 52 playing card PNG images + back.png and Card 13 of Skulls
├── audio/                          # 42 tactile casino .ogg audio files (slides, chips, shuffles, organ chimes)
├── assets/                         # Release packaging assets
│   ├── haunted/                    # Panoramic room backdrops (casino, crypt, creep, hell, celestial)
│   ├── overlay_icons/              # 20 curated 64x64 PNG keyboard & mouse prompt icons
│   ├── icon.ico / icon.png         # Window and executable icons
│   ├── cover_itch.png              # Storefront marketing cover art
│   └── screenshots/                # High-resolution gameplay captures
├── tools/
│   ├── build_character_layers.py   # Sprite layer slicer and coordinate extractor for dealer actors
│   ├── build_character_roster_assets.py # Texture generator for dealer costumes and facial assets
│   ├── build_haunted_assets.py     # Procedural asset generator for altar, candles, and gravestones
│   └── build_stage_backdrops.py    # Generator script for 1x and 2x panoramic stage backdrops
├── docs/
│   └── ITCH_IO_GUIDE.md            # itch.io deployment, store copy, and release guide
└── tests/                          # Automated test suite (234 tests)
    ├── __init__.py
    ├── test_betting.py
    ├── test_dealer_actor.py
    ├── test_dealer_actor_layers.py
    ├── test_dealer_stage_canvas.py
    ├── test_dealer_wardrobe_dialog.py
    ├── test_deck.py
    ├── test_double_down.py
    ├── test_game_rules.py
    ├── test_gui_state.py
    ├── test_hall_of_fame_and_achievements.py
    ├── test_haunted_mode.py
    ├── test_living_animations.py
    ├── test_save_manager.py
    ├── test_scale_and_display_modes.py
    ├── test_scoring.py
    ├── test_settings_dialog.py
    ├── test_shoe.py
    ├── test_shortcuts_overlay.py
    ├── test_sound.py
    ├── test_split.py
    ├── test_surrender.py
    ├── test_table_felt.py
    ├── test_table_hud.py
    ├── test_ui_geometry_and_rendering.py
    └── test_version.py
```
