# Blackjack v2.0.0 (Python & Tkinter)

> 🎮 **Play the Game**: Download the standalone, zero-install Windows release on itch.io:  
> 👉 **[https://wrehman.itch.io/blackjack-classic](https://wrehman.itch.io/blackjack-classic)** *(No Python setup required!)*

## System Overview

An interactive, graphical desktop implementation of the classic casino card game **Blackjack**, built with standard Python and Tkinter, featuring an **animated 19-layer living dealer puppet roster** (9 dealers, 35 bespoke pixel-art costumes, 7 crunchy 16-bit stage backdrops), a **Bankroll-Gated 2.5D Casino Venue Tour & Super Mario World Overworld Map**, the **MIT Hi-Lo Card Counting Academy & Bootcamp**, a supernatural **Haunted Halloween & Hell's Table expansion**, and persistent **Hall of Fame & Achievements**.

Designed as an educational project for Python learners and junior developers, this codebase demonstrates how to transition from basic procedural scripting to clean, production-quality Python: eliminating global variables with Object-Oriented Programming (OOP), managing non-blocking animations without freezing the GUI event loop, decoupling stage canvas rendering from table felt geometry, separating pure mathematical game rules into zero-GUI modules, and authoring exhaustive automated regression tests (300+ unit tests).

---

## Table of Contents
- [System Overview](#system-overview)
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
  - [8. Educational Modular Architecture & Separation of Concerns](#8-educational-modular-architecture--separation-of-concerns)
  - [9. Procedural Animalese Dialogue Voice Engine](#9-procedural-animalese-dialogue-voice-engine)
  - [10. Real-Time Hi-Lo Card Counting Engine & Invariant State](#10-real-time-hi-lo-card-counting-engine--invariant-state)
- [Automated Testing](#automated-testing)
- [File Structure](#file-structure)
- [Local Interface & Invariants](#local-interface--invariants)
- [Subdirectories & System Boundaries](#subdirectories--system-boundaries)
- [Global Invariants](#global-invariants)
- [Global Side Effects](#global-side-effects)
- [System Verification](#system-verification)

---

## Features

- **Casino Felt GUI & Panoramic Horizon Stage**: Re-architected two-tier layout dividing an atmospheric upper room stage from the card table felt via a 3D wooden horizon rail.
- **Living Dealer Animation Engine & Puppet Framework (`dealer_actor.py`)**:
  - Autonomous idle breathing cycle, procedural eye-blinking timers, and dynamic gesture rigging.
  - Discrete 7-layer puppet strata (*shadow*, *torso*, *neck*, *head*, *eyes*, *mouth*, *arms*) with phonetic lip-sync visemes (`a`, `o`, `e`, `f`, `talk`).
  - Interactive speech bubbles with responsive typewriter dialogue streaming.
  - Curated panoramic backdrops (*Casino*, *Crypt*, *Creep*, *Hell*, *Celestial*) with synchronized flickering sconce lighting.
- **Animalese Dialogue Voice Engine (`dialogue_voice_engine.py`)**:
  - Procedural in-memory 16-bit mono 44.1 kHz PCM WAV audio buffer generation with zero external audio asset footprint.
  - Deterministic 1:1 viseme-to-sound phonetic mapping ensuring consistent vocal personality per character rather than random beeps.
  - Punctuation inflection dynamics: rising pitch (+18%) on questions (`?`) and falling pitch (-12%) on statements (`.`).
  - 8 distinct character acoustics (*Julian*, *Tiffany*, *Malphas*, *Uriel*, *Mortimer*, *Dummy*, *Selene*, *Vladimir*) with in-game mute/volume toggle in Settings.
- **Card Counting Trainer, Testing Engine & MIT Hi-Lo Counting Bootcamp (`card_counter.py`, `card_counting_hud.py`, `counting_bootcamp.py`)**:
  - Full implementation of the classic casino **Hi-Lo Card Counting System** (Low cards $2\text{--}6 = +1$, Neutral $7\text{--}9 = 0$, High cards $10\text{--}\text{A} = -1$).
  - **MIT Hi-Lo Counting Bootcamp (`counting_bootcamp.py`)**: Interactive 14-node curriculum DAG (`L0`–`L6` blackboard lectures and `S1`–`S7` timed challenge drills) covering Single-Card Tagging, Pair Cancellation, Running Count Stream, Deck Estimation & True Count, Kelly Bet Sizing, Illustrious 18 Index Deviations (`16 vs 10`, `15 vs 10`, `12 vs 3`, `12 vs 2`, `Insurance at TC >= +3`), and the 3-Seat Full Table Final Exam with persistent `S`/`A`/`B`/`C`/`F` casino chip mastery badges.
  - Sleek felt-embedded pill HUD (`K` or `Shift + C`) displaying Running Count (RC), Estimated Remaining Decks ($\max(0.5, \text{cards} / 52.0)$), True Count ($\text{TC} = \text{RC} / \text{Decks}$) with dynamic Kelly-spread bet recommendations, and a `🎓 Bootcamp` launcher button.
  - Transient floating count badges (`+1`, `-1`, `0`) dynamically rising above dealt cards.
  - Strict dealer hole card invariant: The dealer's downcard remains uncounted until revealed face-up.
  - Interactive mid-shoe quiz test drills verifying player Running Count, unlocking persistent streak achievements (*Apprentice Counter*, *Master Counter*).
- **Universal Puppet Roster & Expansion (`dealer_wardrobe_dialog.py`)**:
  - Universal 7-layer puppet conversion across all dealers: *Julian*, *Tiffany*, *Malphas*, *Uriel*, *Mortimer*, and *The Pit Fiend*.
  - Two new high-roller personas: *Selene* (Cyberpunk Croupier) and *Count Vladimir* (Crimson Nocturne Vampire), unlockable through Card Counting streak achievements.
  - Paginated wardrobe customizer (`Shift + W`) with real-time character previews and unlock status tracking.
- **Haunted Halloween & Hell's Table Expansion (`haunted_manager.py`)**:
  - Progressive supernatural narrative phases: `NORMAL` → `CREEP` → `OMEN` → `SNUFFING` → `HELL_TABLE`.
  - Authentic custom **13 of Skulls** cursed card with authentic host deck geometry and typography.
  - Haunted Altar with 5 candles that snuff out on player busts/losses, summoning 2.5D rising gravestones.
  - Showdown against **The Pit Fiend** with a 2.5D Animated Tug-of-War Soul Meter and 7 Celestial Blessings (*Seraph's Grace* bust-redraw protection, *Eye of Providence*, *Archangel's Smite*, *Cherub's Shield*, *Heavenly Tithe*, *Miracle Draw*, and *Hallowed Run*). Clearing `HELL_TABLE` once awards a `+\$666` Exorcist bounty, permanently retires automatic Haunted slow-burn ambushes (`🔥 Cursed` remains opt-in), and unlocks the **2.5D Casino Venue Tour**.
- **Bankroll-Gated 2.5D Casino Venue Tour & Overworld Map (`tour_domain.py`, `venue_tour.py`)**:
  - Unlocked upon clearing `HELL_TABLE` (*The Exorcist*), accessible via the top-bar `🗺 Tour` button or `Shift + T` shortcut.
  - **8 Pure-Math Mortal Dealer Salons (\$500 $\to$ \$150,000)**: Climbs from *Puppet Dummy*'s *Training Pit* (\$500) through *Julian*'s *Golden Floor*, *Tiffany*'s *Downtown Lounge*, *Professor Edward*'s *MIT Faculty Club*, *Mortimer*'s *Bone Vault*, *Selene*'s *Neon Cyber-Deck*, and *Count Vladimir*'s *Crimson Salon* up to *Uriel*'s single-deck *Sanctum of Light* (\$75,000 entry / \$150,000 target), allowing players to face locked dealers and custom room backdrops over authentic green felt without supernatural rule twists.
  - **2.5D Super Mario World Overworld Map & Dual Medallions**: Hosted by Tour Coordinator *Julian* (`julian_monte_carlo`) with 2.5D pixel-art landmarks, darkened `'???'` mystery silhouettes, anti-Wonging shoe caching, **Standard Mode** (`★` Gold Star Medallions with `<= 80%` Checkpoint Top-Ups), and **Ironman Gauntlet Mode** (`♦` permanent Obsidian Medallions with zero re-buys and velvet-roped prior salons), strictly isolated from Free-Play career financials.
- **Hall of Fame & Save Persistence (`save_manager.py`)**:
  - Persistent career metrics (`blackjack_save.json`): Session-persistent bankroll (`current_bankroll`), Lifetime Wagered, Bankruptcies & Bailouts, Net Profit, Peak Bankroll, Longest Win Streak, Total Blackjacks, Hell's Table Clears, Counting Streaks, and `VenueTourProgress` (`★ X/8 • ♦ Y/8`).
  - 14 unlockable gameplay achievements (*Exorcist*, *High Roller*, *Natural Streak*, *Cursed Survivor*, *Split Maestro*, *Big Spender*, *Apprentice Counter*, *Master Counter*, *Shoe Whisperer*, *Count Capitalist*, *Pair Perfectionist*, *Poker Face*, *Grand Tour Champion*, *Ironman Legend*).
- **Three Table Play Modes (Betting Mode Default)**:
  - **Betting Mode (Default)**: Authentic wagering system with a persistent bankroll, 5 authentic casino chip denominations (\$5, \$25, \$100, \$500, and \$1,000 Platinum), interactive bottom-right bankroll chip piles, staged betting, an **"All In"** button, 3:2 Natural Blackjack payouts, and a \$1,000 rebuy feature.
  - **Casual Mode**: Instant deals, zero-stress casual play with win/loss tracking and no bankroll overhead.
  - **Training Mode**: Combines full betting mechanics with the real-time Hi-Lo Card Counting Trainer HUD and dynamic Basic Strategy hints.
  - Seamless in-game cycling via `Shift + M` or the Casino Settings dialog.
- **Multi-Seat Table Wagering Engine (1-Seat vs. 3-Seat Wagering)**:
  - Symmetrical 3-seat betting layout with Option B crescent baize geometry (Seats 1, 2, and 3).
  - Independent hands per seat with clockwise deal progression (First Base $\to$ Center $\to$ Third Base).
  - Dynamic glowing turn halos tracking the active playing seat and split hand.
  - Independent Double Down, Split, and Surrender decisions across all seats.
  - Bankroll-guarded `MultiSeatInsuranceDialog` offering sequential insurance decisions across all active seats when the dealer shows an Ace.
  - Multi-seat felt chip tray and hands-free seat focus navigation via `Left` and `Right` arrow keys.
- **Configurable Casino House Rules & Venue Presets (`rules.py`, `ui_dialogs.py`)**:
  - Dedicated `[2] House Rules` tab in Casino Settings (`O` / `F2`) with 6 authentic venue presets (*Classic 4-Deck*, *Vegas Strip 6-Deck*, *Downtown 2-Deck Pitch*, *Reno Single-Deck Pitch*, *High-Roller VIP Salon*, and *Tourist Trap 6:5 Warning*) plus full custom overrides.
  - Configurable shoe size (`1`, `2`, `4`, `6`, `8` decks), dealer soft-17 rule (`S17` vs `H17`), Natural Blackjack payout (`3:2` vs `6:5`), Double After Split (`DAS`), double-down total restrictions (`Any 2`, `9/10/11`, `10/11`), Late Surrender (`LS`), and flexible table limits (default \$5 min and No Limit max, scaling up to \$1,000 min / \$5,000 max for bankroll progression) with sub-minimum All-In recovery protection.
  - Dynamic felt arc engraving (`BLACKJACK PAYS 3 TO 2` / `6 TO 5`, `DEALER MUST STAND ON ALL 17s` / `HITS SOFT 17`), live House Edge % estimation, and rule-aware Basic Strategy, Illustrious 18 + Fab 4 surrender deviations, and Hi-Lo advantage math.
- **Persistent Strategy Tripometer & 50-Hand Audit Log (`tripometer.py`, `ui_dialogs.py`)**:
  - Continuous background skill grading accessible any time via the top-bar `📊 Trip` button or `T` shortcut—independent from lifetime career records so players can reset trip stats (`🗑 Reset Trip`) when switching rules or practicing new spreads.
  - Real-time evaluation of Basic Strategy accuracy, Illustrious 18 + Fab 4 True Count index play accuracy, and bankroll-aware Kelly bet sizing (`±1` unit tier tolerance) against each hand's snapshotted `HouseRules`.
  - Bounded 50-hand scrollable audit log with rule badges (`6D · H17 · 3:2 · DAS · LS`), `All Hands` vs `Mistakes Only` filtering, and automatic quarantine of supernatural Haunted/Card 13 rounds so arcade effects never skew mastery percentages.
- **Fixed 1.0x Scale & Borderless Fullscreen**:
  - Crisp, fixed 1.0x interface geometry (`1000x700` default) ensuring authentic pixel art rendering without blurring or distortion.
  - Borderless Fullscreen mode (`F11` / `⛶ Full`).
- **Multi-Deck Shoe & Cut Card Penetration**: 4-deck shoe (208 cards) with persistent card depletion across rounds, live shoe count, and an authentic ~25% cut card penetration reshuffle trigger.
- **Double Down Option**: Double down on initial 2-card hands (and split hands), doubling the wager, drawing exactly one card, and standing automatically.
- **Late Surrender**: Forfeit initial 2-card hands after dealer peeks for Natural Blackjack to recover 50% of the initial wager.
- **Procedural 2.5D Chip Visualizer & Interactive Bankroll Chip Piles**: Stacked clay chips in the active betting spot plus a bottom-right bankroll reserve tray showing all 5 chip denominations piled up as a live visual indicator of running wealth or losses—click any pile directly to add a chip to your bet.
- **Authentic Dealer Hole Card**: Dealer receives one card face-up and one card face-down (`back.png`). The hidden card is revealed only after the player stands (or when round resolves early).
- **Dynamic Score Tracking & Beveled Plaques**: Dealer upcard score shows `"X + ?"` until reveal, framed in antique gold-bordered casino score plaques.
- **Insurance Option**: When the dealer's visible upcard is an Ace in Casino Mode, players are offered an Insurance side bet costing half their main bet and paying 2:1 against a Dealer Natural Blackjack.
- **Casino Side Bets Subsystem (`rules.py`, `ui_canvases.py`)**:
  - **Perfect Pairs**: Pays on the player's initial two cards: Mixed Pair (6:1), Colored Pair (12:1), and Perfect Pair (25:1).
  - **21+3**: Combines the player's initial two cards with the dealer's visible upcard for a 3-card poker hand: Flush (5:1), Straight (10:1), Three of a Kind (30:1), Straight Flush (40:1), and Suited Trips (100:1).
  - Dedicated diegetic side bet felt spots flanking the main betting circle with full-surface click detection, symmetrical controls (Left-click adds \$5 / Shift+\$25, Right-click clears to \$0), and immediate post-deal resolution animations.
  - 2 unlockable side bet achievements (*Pair Perfectionist*, *Poker Face*) and persistent tracking in the Hall of Fame.
- **Hand Splitting**: Split matching rank pairs into two independent hands with active hand indicators, Double After Split (DAS) support, and multi-hand resolution.
- **Auto-Stand & Mid-Hand Guarding**: Automatically stands on 21; action buttons strictly guard against re-entrant input while animations or dealer draws are in flight.
- **Authentic Casino Audio (`.ogg`)**: 42 organic audio variations powered by `pygame.mixer` (via `pygame-ce`): card slides, hole card reveals, shoe shuffles, chip clicks, all-in thuds, rakes, and payout slides.
- **Full Keyboard Accessibility**: High-speed play with context-sensitive bindings and an in-game shortcuts HUD (`?` / `/`).

## Play Online / Download (itch.io)

For casual players and non-engineers who want to play without installing Python or touching a command line:

👉 **Download the Standalone Game on itch.io**:  
**[https://wrehman.itch.io/blackjack-classic](https://wrehman.itch.io/blackjack-classic)**

- **Platform**: Windows 64-bit (Standalone portable release)
- **Zero Installation**: Extract `Blackjack-Windows-v2.0.0.zip` and double-click `Blackjack.exe` to play.
- **Features Included**: Complete game with Living Dealer, MIT Hi-Lo Card Counting Academy, Hell's Table, sound effects, and persistent achievements.

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
   - `dist/Blackjack-Windows-v2.0.0.zip`: Optimized ZIP archive ready to upload to [itch.io](https://wrehman.itch.io/blackjack-classic).

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
| `Left` / `Right` | 3-Seat Betting | Cycle Betting Focus between Seat 1, Seat 2, and Seat 3 |
| `Q` (or `6`) | Betting Phase | Stage \$5 on **Perfect Pairs** Side Bet |
| `E` (or `7`) | Betting Phase | Stage \$5 on **21+3 Poker** Side Bet |
| `A` | Betting Phase | **All In** (Wager entire bankroll) |
| `C` | Betting Phase | **Clear Bet** (Reset staged bet to \$0) |
| `Y` / `N` (or `Esc`)| Dealer Shows Ace | **Take** or **Decline** Insurance (2:1 side bet) |
| `M` | Any Time | Toggle Sound Mute (`ON` / `OFF`) |
| `Shift + M` | Any Time (Betting/Over) | Cycle Table Play Mode (`Casual` $\to$ `Betting` $\to$ `Training`) |
| `V` | Any Time | Toggle **Dealer Horizon Stage View** (Show / Hide) |
| `T` | Any Time | Open **Strategy Tripometer & 50-Hand Audit Log** (`📊 Trip`) |
| `Shift + T` | Exorcist Unlocked | Enter / Toggle **2.5D Casino Venue Tour Overworld Map** (`🗺 Tour`) |
| `O` / `F2` | Any Time | Open **Casino Settings & House Rules** |
| `F11` | Any Time | Toggle **Borderless Fullscreen** |
| `K` / `Shift + C` | Any Time | Toggle **Card Counter Trainer HUD** (Hi-Lo Running & True Count) |
| `Shift + W` | Any Time | Open **Dealer Wardrobe & Costumes** |
| `Shift + H` | Any Time | Open **Hall of Fame & Achievements** |
| `X` | Hell's Table | **Miracle Draw** (Celestial Blessing: redraw active hand card) |
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

### 8. Educational Modular Architecture & Separation of Concerns
To foster code discoverability and provide junior developers with clean patterns, the core codebase is decoupled into modular layers:
- **`config.py`**: Centralized configuration, game constants, screen dimension limits, theme color math (`hex_to_rgb`), and frozen `@dataclass` `ThemePalette` definitions with `get_phase_palette()`.
- **`rules.py`**: Pure, stateless domain logic with zero GUI or Tkinter dependencies. Implements `Card(tuple)` (supporting indexing `card[0]`, `val, img = card`, dot access, and `len(card) == 2`), `Hand` (first-class hand domain model with `list[Card]` sequence compatibility), `HouseRules` & `VENUE_PRESETS` (configurable table rules and house-edge math), `RoundPhase`, `score_hand()`, `dealer_should_hit()`, `determine_outcome()`, `calculate_payout()`, and `breakdown_chips()`. Juniors can import and experiment with rules in a CLI REPL or headless test without spinning up a GUI.
- **`state_machine.py`**: Pure Finite State Machine (`GameStateMachine`) governing legal `RoundPhase` transitions and raising `InvalidStateTransitionError` on illegal jumps.
- **`event_bus.py`**: Synchronous publish-subscribe event bus (`EventHub`, `GameEvent`, `GameEventType`) decoupling domain state transitions from audio, HUDs, puppet kinematics, and persistence.
- **`game_engine.py`**: Pure headless Blackjack state engine (`BlackjackEngine`, `RoundResult`) encapsulating shoe management, betting, multi-hand splits, double downs, surrenders, and dealer turns without GUI dependencies.
- **`card_counter.py`**: Pure stateless Hi-Lo card counting math, Running Count, True Count estimation, rule-aware player edge percentage (`estimate_player_advantage` / `get_player_advantage`), bankroll-aware Kelly bet ramp (`get_kelly_bet_target`), Illustrious 18 + Fab 4 surrender deviations, and quiz verification independent of the GUI.
- **`tripometer.py`**: Pure headless Strategy Tripometer engine (`TripometerTracker`, `TripometerData`, `HandHistoryRecord`, `DecisionStepRecord`) grading Basic Strategy, Illustrious 18 index plays, and Kelly bet sizing in real time with a 50-hand JSON-safe ring buffer.
- **`card_counting_hud.py`**: Custom 2.5D felt HUD pill (with Running Count, True Count, Decks Remaining, Edge %, and Assisted vs. Drill Challenge Mode toggle), transient floating count badges (`+1`, `-1`, `0`), and interactive mid-shoe counting quiz drill modal.
- **`haunted_manager.py`**: Haunted Halloween narrative state engine managing supernatural creep phases, altar candle tracking, cursed Card 13 manifestation, and The Pit Fiend boss logic with Celestial Blessings.
- **`dealer_actor.py`**: Living Dealer 7-layer puppet engine handling autonomous breathing/blinking kinematics, phonetic visemes, costume profiles, and high-resolution composite rendering.
- **`dealer_wardrobe_dialog.py`**: Modal dialog providing interactive dealer costume selection, voice previews, and the 12-plaque Hall of Fame trophy shelf.
- **`dialogue_voice_engine.py`**: Procedural Animalese dialogue voice synthesis generating in-memory 16-bit PCM WAV buffers with 1:1 deterministic viseme-to-sound mappings and punctuation inflection (`?`, `.`, `!`).
- **`audio_assets.py`**: Low-latency 16-channel polyphonic sound playback (`SoundManager`) with randomized acoustic sample pools and silent fallback, in-memory HiDPI image scaling (`AssetScaler`), and Kenney prompt icon caching (`KeyboardIconLoader`).
- **`pixel_ui.py`**: Retro pixel art UI controls (`CanvasPixelButton`, `CanvasPixelPanel`, `PixelPlaqueFrame`, `PixelDialogueFrame`), GDI pixel font loader, and negative pixel font scale clamping.
- **`ui_layout.py`**: Declarative JSON UI geometry (`ui_layout.json`), responsive coordinate resolution, widget styling, and PIL filter configuration.
- **`ui_canvases.py`**: Custom 2.5D `tkinter.Canvas` presentation components: `ChipVisualizer`, `SoulMeterCanvas`, `TableAnnouncementHUD`, `HauntedAltarCanvas` (with color synchronization), `DealerStageCanvas`, `TableFeltCanvas`, and `MahoganyRailCanvas`.
- **`ui_dialogs.py`**: Modal `tkinter.Toplevel` dialogs: `ShortcutsDialog`, `SettingsDialog` (two-tab Table & Audio + House Rules), `TripometerDialog` (50-hand strategy audit log), `StoryDialogueDialog`, `AngelicDraftDialog`, and `WelcomeSplashDialog`.
- **`save_manager.py`**: Career statistics, persistent JSON storage, and round achievement evaluation (`evaluate_round_achievements`).
- **`blackjack.py`**: Main application coordinator (`BlackjackApp`) wiring event loops, user keyboard/mouse bindings, and game phase transitions, while re-exporting key domain symbols for 100% backward compatibility.
- **[CRC Architecture & System Design (`docs/ARCHITECTURE_CRC.md`)](docs/ARCHITECTURE_CRC.md)**: Exhaustive Class-Responsibility-Collaboration (CRC) reference covering all project classes, sequence flows, and architectural improvement analyses.
- **[Active Development Roadmap (`development_roadmap/ROADMAP.md`)](development_roadmap/ROADMAP.md)**: Authoritative forward roadmap tracking remaining architectural decoupling and prospective casino features.

### 9. Procedural Animalese Dialogue Voice Engine
Instead of bundling hundreds of static `.ogg` voice clips that bloat repository size, `dialogue_voice_engine.py` synthesizes lightweight, high-fidelity 16-bit mono 44.1 kHz PCM WAV audio buffers procedurally in memory using Python's standard `wave`, `struct`, and `math` libraries.

To avoid the "random beeping" pitfall of chaotic speech synthesizers, every character is bound to a deterministic, 1:1 viseme-to-frequency mapping:
- Open vowels (`a`, `o`, `e`) oscillate on steady, harmonic formant frequencies.
- Consonants and percussive labials (`f`, `talk`) synthesize short, crisp frequency-decay bursts.
- Inflections alter pitch dynamically based on punctuation: question marks (`?`) trigger a rising frequency ramp (+18%), while periods (`.`) introduce a subtle cadence drop (-12%).

### 10. Real-Time Hi-Lo Card Counting Engine & Invariant State
The card counting trainer (`card_counter.py`, `card_counting_hud.py`) models the professional casino Hi-Lo system:
- **Card Tagging**: Low cards ($2\text{--}6$) contribute $+1$, neutral cards ($7\text{--}9$) contribute $0$, and high cards ($10, \text{J}, \text{Q}, \text{K}, \text{A}$) contribute $-1$.
- **True Count Conversion**: Because card advantage depends on deck penetration, True Count is calculated as $\text{TC} = \text{RC} / \text{Decks Remaining}$, where decks remaining is computed as $\max(0.5, \text{cards in shoe} / 52.0)$ to prevent division-by-zero singularities near the cut card.
- **Dealer Hole Card Invisibility Invariant**: In authentic casino play, the dealer's downcard is private information. `BlackjackApp` enforces this boundary condition by tracking an `_hole_card_observed` flag; the hole card is strictly omitted from the Running Count until it is flipped face-up in `_reveal_dealer_hole_card()`.

---

## Automated Testing

The project includes an exhaustive automated test suite with **350+ unit tests** written with Python's built-in `unittest` framework, validating domain logic, Tkinter GUI widgets, audio fallbacks, and rendering geometry.

### Running the Tests
Use the tiered test runner (`run_tests.py`) to run fast smoke checks, subsystem suites, or the full system regression suite:

```bash
# Fast Smoke Suite (~10-15s) - Default for iterative development
python run_tests.py smoke

# Subsystem Suites (~30-90s) - Targeted domain verification
python run_tests.py core
python run_tests.py betting
python run_tests.py dealer
python run_tests.py haunted
python run_tests.py gui

# List all available test tiers and module counts
python run_tests.py --list

# Full System & Regression Suite (~5-6m) - Pre-release verification
python run_tests.py full
# Or via standard unittest discovery:
python -m unittest discover tests -v
```

### Test Coverage Summary
| Test File | Description |
| :--- | :--- |
| [`tests/test_architectural_integration.py`](tests/test_architectural_integration.py) | Full integration tests validating end-to-end domain wiring between `BlackjackApp`, `BlackjackEngine`, `GameStateMachine`, `EventHub`, and `Hand` abstractions across real game lifecycles. |
| [`tests/test_basic_strategy.py`](tests/test_basic_strategy.py) | Unit tests for pure Basic Strategy domain decision math: pair splits (A-A, 8-8, 5-5 double, 4-4, 9-9), late surrender (16 vs 9/10/A, 15 vs 10), soft hands (A-2 through A-9 vs dealer upcards), and hard hand hit/stand/double thresholds. |
| [`tests/test_betting.py`](tests/test_betting.py) | Tests pure payout calculations (3:2, 1:1, push, loss, surrender), 2:1 insurance payouts with odd-bet breakeven guarantees, chip denomination breakdowns, ChipVisualizer state sync/animations, default Chips Mode, and bankroll tracking. |
| [`tests/test_card_counter.py`](tests/test_card_counter.py) | Unit tests for pure Hi-Lo card counting logic: tag values (+1, 0, -1), Running Count accumulation, cut-card penetration shoe resets, decks remaining calculation with 0.5 minimum clamp, True Count estimation, bet spread sizing, and quiz verification. |
| [`tests/test_card_counting_hud.py`](tests/test_card_counting_hud.py) | Verifies CardCountingHud container rendering, dynamic felt theme synchronization, pack/grid integration, floating count badge particle animations (+1, -1, 0), mid-shoe interactive quiz dialogs, and shortcut key bindings (`K`, `Shift+C`). |
| [`tests/test_chip_visualizer_interactions.py`](tests/test_chip_visualizer_interactions.py) | Validates interactive bankroll chip pile left-click staging, right-click deduction, betting spot click actions, and hover hitbox stability on `ChipVisualizer`. |
| [`tests/test_counting_bootcamp.py`](tests/test_counting_bootcamp.py) | Unit and headless GUI tests for the MIT Hi-Lo Counting Bootcamp: 14-node DAG prerequisite evaluation, grading rubrics, `SaveManager` persistence & monotonic rank preservation, grid swap lifecycle (`row=3` & `row=4`), first-time Training Mode splash onboarding, keyboard shortcut isolation, and timer cleanup. |
| [`tests/test_dealer_actor.py`](tests/test_dealer_actor.py) | Unit tests for DealerActor sprite compositing, layer positioning, dynamic scale adjustments, and mouth/eye state changes. |
| [`tests/test_dealer_actor_layers.py`](tests/test_dealer_actor_layers.py) | Validates layer coordinate math, anchor positioning, and costume asset resolution across all supported outfits. |
| [`tests/test_dealer_stage_canvas.py`](tests/test_dealer_stage_canvas.py) | Verifies panoramic 1000px/2000px stage backdrop scaling, sconce compositing, and stage lighting across themes. |
| [`tests/test_dealer_wardrobe_dialog.py`](tests/test_dealer_wardrobe_dialog.py) | Tests Dealer Wardrobe dialog lifecycle, costume selection, preview rendering, unlock requirement enforcement, and scrollable Hall of Fame achievement trophy shelf. |
| [`tests/test_deck.py`](tests/test_deck.py) | Verifies all 52 card PNGs and `back.png` exist, validates deck distribution, and tests `Card` tuple subclass properties. |
| [`tests/test_dialogue_voice_engine.py`](tests/test_dialogue_voice_engine.py) | Validates procedural 16-bit mono 44.1 kHz PCM WAV byte buffer generation, 1:1 deterministic viseme-to-sound phonetic consistency, voice profile registration, volume/mute handling, and question/period/exclamation pitch inflection. |
| [`tests/test_double_down.py`](tests/test_double_down.py) | Tests Double Down eligibility (2 cards only, bankroll checks), wager doubling, single card draw, auto-stand, and bust resolution. |
| [`tests/test_event_bus.py`](tests/test_event_bus.py) | Validates synchronous pub-sub event dispatch, subscriber registration, unsubscription, and payload propagation across `EventHub`. |
| [`tests/test_game_engine.py`](tests/test_game_engine.py) | Modular headless unit tests for `BlackjackEngine`: round initialization, dealing, player actions, dealer drawing, outcome evaluation, insurance side bets, and cut-card penetration triggers. |
| [`tests/test_game_rules.py`](tests/test_game_rules.py) | Tests win/loss/push evaluations, dealer AI hit/stand rules, Natural Blackjack vs split 21s (1:1 payout), and surrender payouts. |
| [`tests/test_gui_state.py`](tests/test_gui_state.py) | Validates actual `BlackjackApp` widget states (Hit, Stand, Double, Split, Surrender, New Game buttons, ties, timer cleanup) across real game lifecycle transitions. |
| [`tests/test_hall_of_fame_and_achievements.py`](tests/test_hall_of_fame_and_achievements.py) | Tests Hall of Fame modal GUI, badge rendering, stats aggregation, and achievement unlock triggers. |
| [`tests/test_hand.py`](tests/test_hand.py) | Modular domain unit tests for the pure `Hand` class: card accumulation, soft/hard scoring, sequence protocol (`len`, `getitem`, `iter`), equality, and string formatting. |
| [`tests/test_haunted_mode.py`](tests/test_haunted_mode.py) | Validates Haunted Halloween phase transitions, Card 13 manifestation & immediate deal bust handling, candle snuffing, gravestone rising, Pit Fiend composite, Soul Meter animations, and relic mechanics. |
| [`tests/test_house_rules.py`](tests/test_house_rules.py) | Unit tests for `HouseRules` normalization, 6 casino venue presets, house-edge estimation, H17/6:5/DAS/double-restriction/LS basic strategy & payouts, sub-minimum All-In recovery, and `BlackjackEngine` rule enforcement. |
| [`tests/test_house_rules_and_tripometer_gui.py`](tests/test_house_rules_and_tripometer_gui.py) | Headless GUI integration tests verifying `SettingsDialog` Tab 1 (`House Rules`), mid-hand mutation guards, dynamic felt `6 TO 5` / `H17` markings, `TripometerDialog` (`📊 Trip` & `T`), end-to-end GUI round telemetry, and Trip reset isolation. |
| [`tests/test_living_animations.py`](tests/test_living_animations.py) | Validates DealerActor autonomous idle breathing, blinking cadence, typewriter speech timers, and gesture transitions. |
| [`tests/test_multi_seat_engine.py`](tests/test_multi_seat_engine.py) | Headless unit tests for multi-seat engine: clockwise dealing, inactive seat skipping, dealer turn skip on bust/surrender, independent surrender, and canonical bankroll synchronization. |
| [`tests/test_multi_seat_gui.py`](tests/test_multi_seat_gui.py) | Headless GUI tests for 3-seat felt layout, bounding boxes, split hand fanning, canvas-level geometric click dispatching, and `MultiSeatInsuranceDialog` bankroll clamping. |
| [`tests/test_multi_seat_normal_play.py`](tests/test_multi_seat_normal_play.py) | End-to-end integration tests for 3-seat multi-seat normal play: Hit/Stand turn progression, Double Down across seats, split multi-hand resolution, surrender, dealer draws, natural Blackjacks, side bets, and round reset lifecycles. |
| [`tests/test_pixel_ui.py`](tests/test_pixel_ui.py) | Verifies pixel art UI primitives (`CanvasPixelPanel`, `PixelPlaqueFrame`, `PixelDialogueFrame`, `CanvasPixelButton`), pixel font loading, and integer scaling invariants. |
| [`tests/test_puppet_multi_layer_actor.py`](tests/test_puppet_multi_layer_actor.py) | Tests discrete multi-layer puppet rigging (shadow, torso, neck, head, eyes, mouth, arms), high-contrast dummy asset integrity, Tiffany 2.0 puppet integration, phonetic viseme mapping ('a', 'o', 'e', 'f', 'talk'), Z-order compositing, and backward-compatible costume fallback. |
| [`tests/test_roster_puppet_conversion.py`](tests/test_roster_puppet_conversion.py) | Validates universal puppet conversion across the dealer cast, 19-layer discrete puppet strata for new personas Selene and Vladimir, phonetic mouth visemes, and achievement-locked wardrobe progression. |
| [`tests/test_save_manager.py`](tests/test_save_manager.py) | Validates blank-slate defaults, persistent file I/O, career stats, costume unlocks, corruption recovery, and user preference retention (including default Chips Mode). |
| [`tests/test_scale_and_display_modes.py`](tests/test_scale_and_display_modes.py) | Verifies 1.0x vs 2.0x HiDPI integer scaling, geometry recomputation, and borderless fullscreen toggle. |
| [`tests/test_scoring.py`](tests/test_scoring.py) | Verifies `score_hand()` across empty hands, multiple Aces, soft-to-hard shifts, and busts. |
| [`tests/test_settings_dialog.py`](tests/test_settings_dialog.py) | Tests settings dialog lifecycle, two-tier preference layout, display scaling toggles, sound volume and voice toggles, career records & counting streak, scrollable container, and clear save confirmation. |
| [`tests/test_shoe.py`](tests/test_shoe.py) | Verifies 4-deck shoe composition (208 cards), persistence across consecutive rounds, cut-card penetration triggers (~25%), and UI count display. |
| [`tests/test_shortcuts_overlay.py`](tests/test_shortcuts_overlay.py) | Verifies curated Kenney prompt icon asset integrity (including keys 5, Shift, V, X), `KeyboardIconLoader` scaling & caching, `[?] Help` button placement, dialog open/close lifecycle, two-tab navigation, scrollable canvas container, and all 20+ gameplay & system shortcuts. |
| [`tests/test_side_bets.py`](tests/test_side_bets.py) | Unit tests for Track 4 Casino Side Bets: Perfect Pairs paytables (Mixed 6:1, Colored 12:1, Perfect 25:1), 21+3 poker hands (Flush 5:1, Straight 10:1, Trips 30:1, Straight Flush 40:1, Suited Trips 100:1), staging and right-click clearing, bankroll persistence, and achievement unlocks. |
| [`tests/test_sound.py`](tests/test_sound.py) | Validates SoundManager audio engine, 42-file .ogg catalog loading across 10 categories, polyphony, volume clamping, mute toggling, UI sound button synchronization, keyboard shortcut integration, and headless fail-safe degradation. |
| [`tests/test_split.py`](tests/test_split.py) | Tests hand split qualification (`can_split`), multi-hand turn progression, button states, and independent outcome resolution. |
| [`tests/test_state_machine.py`](tests/test_state_machine.py) | Validates `GameStateMachine` transitions across `RoundPhase`, legal transition queries, and `InvalidStateTransitionError` enforcement. |
| [`tests/test_surrender.py`](tests/test_surrender.py) | Tests Late Surrender eligibility (initial 2 cards only, un-split), 50% wager refund, hole card reveal, and dealer win recording. |
| [`tests/test_table_felt.py`](tests/test_table_felt.py) | Validates procedural canvas texture generation, theme switching (casino/creep/hell), and child coordinate slice extraction. |
| [`tests/test_table_hud.py`](tests/test_table_hud.py) | Tests 2.5D animated announcement HUD popups, banner styling, and auto-dismiss timers on the table felt. |
| [`tests/test_test_runner.py`](tests/test_test_runner.py) | Validates the tiered test runner (`run_tests.py`), tier module mappings, disk existence of configured test modules, suite construction, and CLI argument parsing. |
| [`tests/test_tripometer.py`](tests/test_tripometer.py) | Unit tests for `TripometerTracker`, `TripometerData`, `HandHistoryRecord`, Kelly $\pm 1$-tier bet grading, Illustrious 18 + Fab 4 surrender index evaluation, supernatural round quarantine, 50-hand ring buffer eviction, and `SaveManager` persistence. |
| [`tests/test_typewriter_and_audio_accents.py`](tests/test_typewriter_and_audio_accents.py) | Validates typewriter dialogue streaming (25-35 ms cadence), directional speech tail rendering, fast-forward skip on click, character audio accents, and extension safety. |
| [`tests/test_ui_geometry_and_rendering.py`](tests/test_ui_geometry_and_rendering.py) | Validates zero card clipping, beveled plaque geometry, TableAnnouncementHUD auto-dismiss, and OMEN altar color synchronization. |
| [`tests/test_ui_layout.py`](tests/test_ui_layout.py) | Validates JSON-driven UI layout configuration (`ui_layout.py`), origin/offset resolution, grid/pack option scaling, and PIL resampling filters. |
| [`tests/test_universal_puppet_faceplates.py`](tests/test_universal_puppet_faceplates.py) | Verifies universal 7-layer mannequin faceplate de-occlusion (blank eye sockets and mouth apertures), isolated eye socket layers, distinct articulated arm poses (`arm_idle`, `arm_deal`, `arm_peek`), and multi-layer puppet kinematics across all 8 dealers. |
| [`tests/test_version.py`](tests/test_version.py) | Enforces single source of truth for versioning across `blackjack.py`, specifications, and documentation. |
| [`tests/test_welcome_splash_dialog.py`](tests/test_welcome_splash_dialog.py) | Verifies WelcomeSplashDialog lifecycle, retro pixel art logo, dealer greeting banner, interactive selection across 3 modes (Casual, Betting, Training), dynamic display bounds, persistent save settings, and live basic strategy hint reflection. |

---

## File Structure

```
Blackjack/
├── blackjack.py                    # Main application coordinator: BlackjackApp event loop & re-exports
├── card_counter.py                 # Pure stateless Hi-Lo card counting math, True Count, Edge %, and quiz validation
├── card_counting_hud.py            # 2.5D felt HUD pill, Drill Mode toggle, floating count badges, and quiz drill modal
├── bootcamp_domain.py              # Pure domain Model for MIT Hi-Lo Counting Bootcamp (14-node DAG, drills, grading)
├── counting_bootcamp.py            # Bootcamp View (BootcampCanvasRenderer, BootcampControlDock) & Controller (CountingBootcampFrame)
├── tour_domain.py                  # Pure domain Model for 8-Salon Casino Venue Tour (SalonSpecs, Standard/Ironman gates)
├── venue_tour.py                   # 2.5D Super Mario World Overworld Map View & Controller (VenueTourFrame, TourControlDock)
├── config.py                       # Game constants, ThemePalette dataclasses, and path resolution
├── dealer_actor.py                 # Living Dealer 7-layer puppet engine: kinematics, breathing, blinking, visemes
├── dealer_wardrobe_dialog.py       # Modal dialog for previewing and equipping dealer costumes
├── dialogue_voice_engine.py        # Procedural Animalese voice synthesis engine (16-bit PCM WAV in memory)
├── event_bus.py                    # Synchronous pub-sub EventHub and GameEvent domain events
├── game_engine.py                  # Pure headless BlackjackEngine and RoundResult domain state manager
├── haunted_manager.py              # Haunted Halloween narrative state: phases, altar candles, relics
├── pixel_ui.py                     # Retro pixel art UI primitives, beveled plaques, and GDI pixel font loader
├── rules.py                        # Pure stateless Blackjack math, HouseRules, VENUE_PRESETS, Card, Hand, and RoundPhase
├── save_manager.py                 # Persistent save data, HouseRules, TripometerData, stats tracking, and achievements
├── state_machine.py                # Formal Finite State Machine (GameStateMachine) for RoundPhase transitions
├── tripometer.py                   # Persistent Strategy Tripometer engine: BS, Illustrious 18, Kelly bet grading & 50-hand log
├── audio_assets.py                 # Polyphonic SoundManager, AssetScaler & KeyboardIconLoader
├── ui_canvases.py                  # Custom 2.5D Canvas components (Chips, Altar, Stage, Felt, Rail)
├── ui_chip_renderer.py              # Stateless 2.5D casino chip cylinder and stack renderer
├── ui_dialogs.py                   # Modal Toplevel dialogs (Shortcuts, Settings, Tripometer, Story, Draft, Welcome)
├── ui_layout.py                    # Declarative UI geometry, scaling options, and resampling configuration
├── blackjack.spec                  # PyInstaller build spec for itch.io packaging
├── build_itch_release.bat          # Windows 1-click build batch wrapper
├── build_itch_release.ps1          # Automated PowerShell build, test, and zip packaging pipeline
├── run_tests.py                    # Tiered CLI test runner (smoke, core, betting, dealer, haunted, gui, full)
├── import_test.py                  # External import verification test
├── README.md                       # Project documentation and architectural guide
├── README_PLAYERS.txt              # End-user player guide bundled with releases
├── .gitignore                      # Git exclusions (caches, IDEs, builds, raw asset packs)
├── cards/                          # 52 playing card PNG images + back.png and Card 13 of Skulls
├── audio/                          # 42 tactile casino .ogg audio files (slides, chips, shuffles, organ chimes)
├── assets/                         # Release packaging assets
│   ├── fonts/                      # Bundled TrueType pixel fonts and font_config.json
│   ├── haunted/                    # Panoramic room backdrops (casino, crypt, creep, hell, celestial) and character puppet strata
│   ├── overlay_icons/              # Curated 64x64 PNG keyboard & mouse prompt icons
│   ├── pixel_logo_blackjack.png    # Retro pixel art game logo (468x84)
│   ├── pixel_logo_blackjack_2x.png # HiDPI retro pixel art game logo (936x168)
│   ├── icon.ico / icon.png         # Window and executable icons
│   ├── cover_itch.png              # Storefront marketing cover art
│   └── screenshots/                # High-resolution gameplay captures
├── tools/
│   ├── README.md                   # Component contract for offline asset generation and GDI capture tools
│   ├── build_character_layers.py   # Sprite layer slicer and coordinate extractor for dealer actors
│   ├── build_character_roster_assets.py # Texture generator for dealer costumes and facial assets
│   ├── build_dummy_puppet_assets.py # Generator for multi-layer puppet rig test assets
│   ├── build_font_comparison_specimen.py # Candidate pixel font comparison sheet generator
│   ├── build_haunted_assets.py     # Procedural asset generator for altar, candles, and gravestones
│   ├── build_pixel_logo.py         # Procedural generator for 1x and 2x retro pixel art game logo assets
│   ├── build_roster_puppet_assets.py # Texture synthesis pipeline for full roster puppet conversion & expansion
│   ├── build_stage_backdrops.py    # Generator script for 1x and 2x panoramic stage backdrops
│   ├── build_tiffany_puppet_assets.py # Pipeline tool for extracting, de-occluding, and generating Tiffany 2.0 discrete puppet layers
│   ├── capture_dialogs_verification.py # Automation tool for capturing Settings, Shortcuts, and Wardrobe Hall of Fame dialog verifications
│   ├── capture_puppet_demo.py      # Automation tool for capturing puppet exploded layers, visemes, and stage verification
│   ├── capture_retro_pixel_verification.py # Automation tool for capturing retro pixel betting, play, and cursed stakes phases
│   ├── capture_tiffany_puppet_demo.py # Automation tool for capturing Tiffany puppet exploded layers, phonetic visemes, arms, and live stage verification
│   ├── capture_typewriter_demo.py  # Automation tool for capturing dialogue and stage screenshots
│   ├── capture_universal_puppet_audit.py # Visual contact sheet generator for universal 7-layer dealer puppets & poses
│   ├── capture_wardrobe_dummy_demo.py # Automation tool for capturing wardrobe dialog with dummy puppet
│   ├── capture_wardrobe_redesign_verification.py # Automation tool for capturing Wardrobe Closet and Hall of Fame tabs
│   ├── capture_welcome_splash_verification.py # Automation tool for capturing WelcomeSplashDialog and table mode verifications
│   ├── deocclude_dealer_faceplates.py # Pipeline tool for de-occluding mannequin faceplates, isolating eye sockets, and building articulated arm poses
│   └── test_counting_simulation.py # Monte Carlo simulation runner validating Hi-Lo card counting invariants across 10,000 deals
├── development_roadmap/
│   ├── ROADMAP.md                  # Sole active, forward-looking roadmap for pending initiatives
│   └── archive/                    # Archived historical design specifications & plans (obsolete, for reference)
├── docs/
│   ├── ARCHITECTURE_CRC.md         # Class-Responsibility-Collaboration (CRC) architecture & review
│   ├── ITCH_IO_GUIDE.md            # itch.io deployment, store copy, and release guide
│   └── designs/
│       ├── counting_bootcamp.md    # Architectural design specification for the MIT Hi-Lo Counting Bootcamp
│       └── house_rules_and_tripometer.md # Design spec for Configurable House Rules & Persistent Strategy Tripometer
└── tests/                          # Automated test suite (400+ unit tests)
    ├── __init__.py
    ├── test_architectural_integration.py
    ├── test_basic_strategy.py
    ├── test_betting.py
    ├── test_card_counter.py
    ├── test_card_counting_hud.py
    ├── test_chip_visualizer_interactions.py
    ├── test_counting_bootcamp.py
    ├── test_dealer_actor.py
    ├── test_dealer_actor_layers.py
    ├── test_dealer_stage_canvas.py
    ├── test_dealer_wardrobe_dialog.py
    ├── test_deck.py
    ├── test_dialogue_voice_engine.py
    ├── test_double_down.py
    ├── test_event_bus.py
    ├── test_game_engine.py
    ├── test_game_rules.py
    ├── test_gui_state.py
    ├── test_hall_of_fame_and_achievements.py
    ├── test_hand.py
    ├── test_haunted_mode.py
    ├── test_house_rules.py
    ├── test_house_rules_and_tripometer_gui.py
    ├── test_living_animations.py
    ├── test_multi_seat_engine.py
    ├── test_multi_seat_gui.py
    ├── test_multi_seat_normal_play.py
    ├── test_pixel_ui.py
    ├── test_puppet_multi_layer_actor.py
    ├── test_roster_puppet_conversion.py
    ├── test_save_manager.py
    ├── test_scale_and_display_modes.py
    ├── test_scoring.py
    ├── test_settings_dialog.py
    ├── test_shoe.py
    ├── test_shortcuts_overlay.py
    ├── test_side_bets.py
    ├── test_sound.py
    ├── test_split.py
    ├── test_state_machine.py
    ├── test_surrender.py
    ├── test_table_felt.py
    ├── test_table_hud.py
    ├── test_test_runner.py
    ├── test_tripometer.py
    ├── test_typewriter_and_audio_accents.py
    ├── test_ui_geometry_and_rendering.py
    ├── test_ui_layout.py
    ├── test_universal_puppet_faceplates.py
    ├── test_venue_tour_domain.py
    ├── test_venue_tour_gui.py
    ├── test_venue_tour_integration.py
    ├── test_version.py
    └── test_welcome_splash_dialog.py
```

---

## Local Interface & Invariants

### Public Symbols (Root Modules)
- **Application Coordinator (`blackjack.py`)**: `[blackjack.py:__version__]`, `[blackjack.py:APP_VERSION]`, `[blackjack.py:BlackjackApp]`, `[blackjack.py:BlackjackApp.new_game]`, `[blackjack.py:BlackjackApp.apply_play_mode]`, `[blackjack.py:BlackjackApp.get_current_strategy_hint]`, `[blackjack.py:BlackjackApp.clear_player_save_data]`, `[blackjack.py:BlackjackApp.play_dealer_accent]`, `[blackjack.py:BlackjackApp.set_dealer_speech]`, `[blackjack.py:BlackjackApp.clear_dealer_speech]`, `[blackjack.py:BlackjackApp.on_hit]`, `[blackjack.py:BlackjackApp.on_stand]`, `[blackjack.py:BlackjackApp.on_double_down]`, `[blackjack.py:BlackjackApp.on_split]`, `[blackjack.py:BlackjackApp.on_surrender]`, `[blackjack.py:BlackjackApp.toggle_scale_mode]`, `[blackjack.py:BlackjackApp.toggle_fullscreen]`, `[blackjack.py:BlackjackApp.exit_fullscreen]`, `[blackjack.py:play_game]`
- **Configuration & Theme Palettes (`config.py`)**: `[config.py:BLACKJACK_TARGET]`, `[config.py:DEALER_STAND_THRESHOLD]`, `[config.py:DEFAULT_DECK_COUNT]`, `[config.py:CUT_CARD_PENETRATION]`, `[config.py:STARTING_BANKROLL]`, `[config.py:MINIMUM_BET]`, `[config.py:CHIP_DENOMINATIONS]`, `[config.py:INSURANCE_PAYOUT_RATIO]`, `[config.py:DEALER_DRAW_DELAY_MS]`, `[config.py:DEFAULT_WINDOW_WIDTH]`, `[config.py:DEFAULT_WINDOW_HEIGHT]`, `[config.py:MIN_WINDOW_WIDTH]`, `[config.py:MIN_WINDOW_HEIGHT]`, `[config.py:CARD_WIDTH]`, `[config.py:CARD_HEIGHT]`, `[config.py:get_base_dir]`, `[config.py:BASE_DIR]`, `[config.py:ASSETS_DIR]`, `[config.py:AUDIO_DIR]`, `[config.py:OVERLAY_ICONS_DIR]`, `[config.py:HAUNTED_ASSETS_DIR]`, `[config.py:HAUNTED_AUDIO_DIR]`, `[config.py:FONTS_DIR]`, `[config.py:hex_to_rgb]`, `[config.py:ThemePalette]`, `[config.py:get_creep_theme]`, `[config.py:get_phase_palette]`
- **Domain Rules & Math (`rules.py`)**: `[rules.py:RoundPhase]`, `[rules.py:Card]`, `[rules.py:Hand]`, `[rules.py:HouseRules]`, `[rules.py:VENUE_PRESETS]`, `[rules.py:Player]`, `[rules.py:Seat]`, `[rules.py:score_hand]`, `[rules.py:is_soft_hand]`, `[rules.py:dealer_should_hit]`, `[rules.py:can_split]`, `[rules.py:can_double_down_hand]`, `[rules.py:can_surrender_hand]`, `[rules.py:estimate_house_edge_pct]`, `[rules.py:effective_minimum_bet]`, `[rules.py:clamp_main_bet]`, `[rules.py:determine_outcome]`, `[rules.py:calculate_payout]`, `[rules.py:calculate_insurance_payout]`, `[rules.py:breakdown_chips]`, `[rules.py:breakdown_bankroll_piles]`, `[rules.py:build_shoe]`, `[rules.py:BasicStrategyDecision]`, `[rules.py:get_basic_strategy_decision]`
- **State Machine, Event Bus, Headless Engine & Tripometer (`state_machine.py`, `event_bus.py`, `game_engine.py`, `tripometer.py`)**: `[state_machine.py:InvalidStateTransitionError]`, `[state_machine.py:VALID_TRANSITIONS]`, `[state_machine.py:GameStateMachine]`, `[event_bus.py:GameEventType]`, `[event_bus.py:GameEvent]`, `[event_bus.py:EventHub]`, `[game_engine.py:RoundResult]`, `[game_engine.py:BlackjackEngine]`, `[tripometer.py:DecisionStepRecord]`, `[tripometer.py:HandHistoryRecord]`, `[tripometer.py:TripometerData]`, `[tripometer.py:TripometerTracker]`
- **Card Counting & Bootcamp Subsystem (`card_counter.py`, `card_counting_hud.py`, `bootcamp_domain.py`, `counting_bootcamp.py`)**: `[card_counter.py:HiLoCardCounter]`, `[card_counting_hud.py:FloatingCountBadge]`, `[card_counting_hud.py:CardCountingHud]`, `[card_counting_hud.py:CardCountingQuizDialog]`, `[bootcamp_domain.py:BootcampLectureSlide]`, `[bootcamp_domain.py:BootcampNodeSpec]`, `[bootcamp_domain.py:BootcampPrompt]`, `[bootcamp_domain.py:BootcampCurriculumDAG]`, `[bootcamp_domain.py:BootcampDrillSession]`, `[bootcamp_domain.py:BOOTCAMP_GRADE_CHIP_STYLES]`, `[counting_bootcamp.py:BootcampControlDock]`, `[counting_bootcamp.py:BootcampCanvasRenderer]`, `[counting_bootcamp.py:CountingBootcampFrame]`
- **Haunted Narrative & Persistence (`haunted_manager.py`, `save_manager.py`)**: `[haunted_manager.py:Phase]`, `[haunted_manager.py:Blessing]`, `[haunted_manager.py:BlessingDetails]`, `[haunted_manager.py:BLESSING_REGISTRY]`, `[haunted_manager.py:HauntedManager]`, `[save_manager.py:GRADE_RANK_ORDER]`, `[save_manager.py:LECTURE_IDS]`, `[save_manager.py:STAGE_IDS]`, `[save_manager.py:BootcampLectureRecord]`, `[save_manager.py:BootcampStageRecord]`, `[save_manager.py:BootcampProgress]`, `[save_manager.py:create_default_bootcamp_progress]`, `[save_manager.py:HighScores]`, `[save_manager.py:Achievements]`, `[save_manager.py:SaveData]`, `[save_manager.py:SaveManager]`
- **Living Dealer, Wardrobe & Voice Synthesis (`dealer_actor.py`, `dealer_wardrobe_dialog.py`, `dialogue_voice_engine.py`)**: `[dealer_actor.py:CostumeVariant]`, `[dealer_actor.py:CharacterProfile]`, `[dealer_actor.py:CHARACTERS]`, `[dealer_actor.py:COSTUME_ALIASES]`, `[dealer_actor.py:VISEME_STATES]`, `[dealer_actor.py:map_char_to_viseme]`, `[dealer_actor.py:DealerActor]`, `[dealer_wardrobe_dialog.py:DealerCardPanel]`, `[dealer_wardrobe_dialog.py:MysteryDealerCardPanel]`, `[dealer_wardrobe_dialog.py:WardrobeDialog]`, `[dialogue_voice_engine.py:VOICE_PROFILES]`, `[dialogue_voice_engine.py:SUPPORTED_VISEMES]`, `[dialogue_voice_engine.py:synthesize_viseme_pcm]`, `[dialogue_voice_engine.py:AnimaleseVoiceEngine]`
- **Audio Presentation & Asset Scaling (`audio_assets.py`)**: `[audio_assets.py:AssetScaler]`, `[audio_assets.py:load_images]`, `[audio_assets.py:SoundManager]`, `[audio_assets.py:KeyboardIconLoader]`
- **Table Felt, Stage & HUD Canvases (`ui_canvases.py`)**: `[ui_canvases.py:ChipVisualizer]`, `[ui_canvases.py:SoulMeterCanvas]`, `[ui_canvases.py:TableAnnouncementHUD]`, `[ui_canvases.py:HauntedAltarCanvas]`, `[ui_canvases.py:DealerStageCanvas]`, `[ui_canvases.py:TableFeltCanvas]`, `[ui_canvases.py:MahoganyRailCanvas]`
- **Modal & Informational Overlays (`ui_dialogs.py`)**: `[ui_dialogs.py:StoryDialogueDialog]`, `[ui_dialogs.py:AngelicDraftDialog]`, `[ui_dialogs.py:SettingsDialog]`, `[ui_dialogs.py:TripometerDialog]`, `[ui_dialogs.py:ShortcutsDialog]`, `[ui_dialogs.py:WelcomeSplashDialog]`, `[ui_dialogs.py:MultiSeatInsuranceDialog]`
- **Pixel Art UI & Font Rendering (`pixel_ui.py`)**: `[pixel_ui.py:PALETTE]`, `[pixel_ui.py:DEFAULT_FONT_CONFIG]`, `[pixel_ui.py:load_font_config]`, `[pixel_ui.py:reload_font_config]`, `[pixel_ui.py:load_pixel_font]`, `[pixel_ui.py:load_all_pixel_fonts]`, `[pixel_ui.py:get_title_font]`, `[pixel_ui.py:get_header_font]`, `[pixel_ui.py:get_display_font]`, `[pixel_ui.py:get_body_font]`, `[pixel_ui.py:get_button_font]`, `[pixel_ui.py:get_digital_font]`, `[pixel_ui.py:get_badge_font]`, `[pixel_ui.py:get_micro_font]`, `[pixel_ui.py:get_pixel_font]`, `[pixel_ui.py:get_pixel_icon]`, `[pixel_ui.py:get_role_font]`, `[pixel_ui.py:get_element_font]`, `[pixel_ui.py:CanvasPixelPanel]`, `[pixel_ui.py:PixelPlaqueFrame]`, `[pixel_ui.py:PixelDialogueFrame]`, `[pixel_ui.py:CanvasPixelButton]`, `[pixel_ui.py:ChipButtonProxy]`, `[pixel_ui.py:CanvasTextLabelProxy]`, `[pixel_ui.py:PixelButtonWidget]`
- **Declarative Layout & Geometry (`ui_layout.py`)**: `[ui_layout.py:DEFAULT_UI_CONFIG]`, `[ui_layout.py:UI_CONFIG_FILE]`, `[ui_layout.py:load_ui_config]`, `[ui_layout.py:reload_ui_config]`, `[ui_layout.py:get_ui_layout]`, `[ui_layout.py:get_table_layout]`, `[ui_layout.py:get_rail_button_layout]`, `[ui_layout.py:get_card_layout]`, `[ui_layout.py:get_seat_origin]`, `[ui_layout.py:get_grid_options]`, `[ui_layout.py:get_pack_options]`, `[ui_layout.py:resolve_origin]`, `[ui_layout.py:resolve_offset]`, `[ui_layout.py:get_theme_color]`, `[ui_layout.py:get_widget_style]`, `[ui_layout.py:apply_style]`, `[ui_layout.py:get_image_scaling_config]`, `[ui_layout.py:resolve_pil_resample]`

### Local Invariants
- `[blackjack.py:__version__]`: Single source of truth for application semantic version (`"2.0.0"`), aliased as `APP_VERSION`.
- `[rules.py:score_hand]`: Sums card values with Aces counted as `1` and promotes at most one Ace by `+10` iff `1 in values and score + 10 <= BLACKJACK_TARGET`.
- `[rules.py:determine_outcome]` and `[rules.py:calculate_payout]`: Split hands (`is_split=True`) with 2-card 21 evaluate as `PLAYER_WINS` (`1:1`), never `NATURAL_BLACKJACK` (`3:2`); `[rules.py:calculate_insurance_payout]` rounds odd-bet insurance profit via `max(main_bet, insurance_bet * INSURANCE_PAYOUT_RATIO)` when `insurance_bet == main_bet // 2`.
- `[state_machine.py:GameStateMachine.transition_to]`: Enforces `VALID_TRANSITIONS` across `RoundPhase` and raises `InvalidStateTransitionError` on illegal jumps unless `force=True`.
- `[card_counter.py:HiLoCardCounter.decks_remaining]` and `[blackjack.py:BlackjackApp._deal_card_to_dealer]`: Clamps remaining decks to `max(0.5, round(cards_remaining / 52.0, 1))` and withholds the dealer hole card from the Running Count (`_hole_card_observed`) until revealed face-up in `_reveal_dealer_hole_card()`.
- `[haunted_manager.py:HauntedManager.on_new_hand]` and `[blackjack.py:BlackjackApp._start_round_deal]`: Mortal hands progress through `NORMAL` (1–6), `CREEP` (7–12), `OMEN` (13), and `SNUFFING` (>13 until `candles_remaining == 0` triggers `HELL_TABLE`); an initial 2-card deal exceeding `BLACKJACK_TARGET` (such as Cursed Card 13) immediately disables action buttons, flips the dealer hole card, and concludes the round.
- `[dealer_actor.py:DealerActor.get_composite_image]`: Composites 7 puppet strata in fixed bottom-to-top Z-order (`shadow`, `neck`, `torso`, `head`, `eyes_<state>`, `mouth_<state>`, `arm_<state>`) with kinematic offsets clamped in `set_layer_offsets`.
- `[pixel_ui.py:get_role_font]`, `[pixel_ui.py:CanvasPixelButton.grid_configure]`, and `[blackjack.py:BlackjackApp._update_ui_scaling]`: Enforce negative pixel font sizing (`-abs(int(final_size))`) and verify `bool(widget.grid_info())` (`_is_mapped`) before calling `grid_configure` so widgets hidden via `grid_remove()` are never accidentally remapped.

---

## Subdirectories & System Boundaries

- `assets`: [`./assets/README.md`](./assets/README.md) — Visual branding, bundled pixel fonts, Kenney overlay keycaps, storefront screenshots, and declarative UI layout configuration.
- `audio`: [`./audio/README.md`](./audio/README.md) — 42 tactile casino sound effects (.ogg) across 10 categories and procedural supernatural audio stingers.
- `cards`: [`./cards/README.md`](./cards/README.md) — 55 standard playing card PNG assets (74x107 px) and authentic hole card damask back.
- `development_roadmap`: [`./development_roadmap/README.md`](./development_roadmap/README.md) — Active development roadmap (`ROADMAP.md`) and historical completed specification archive.
- `docs`: [`./docs/README.md`](./docs/README.md) — Architectural Class-Responsibility-Collaboration index (`ARCHITECTURE_CRC.md`), itch.io release guide, and technical feature design specifications.
- `tests`: [`./tests/README.md`](./tests/README.md) — 47 automated test modules covering core rules, multi-seat wagering, card counting, puppet kinematics, and GUI geometry.
- `tools`: [`./tools/README.md`](./tools/README.md) — Offline procedural asset generators, 19-layer dealer puppet slicers and faceplate de-occluders, and Win32 GDI (`PrintWindow`) visual verification capture scripts.
- `.agents/skills/package-itch-release`: [`./.agents/skills/package-itch-release/SKILL.md`](./.agents/skills/package-itch-release/SKILL.md) — Standalone PyInstaller packaging and itch.io distribution workflow skill.

---

## Global Invariants

- **OOP State Encapsulation & Zero Global Mutable Game State**: All active deck, hand, bankroll, timer, and round states are encapsulated on `[blackjack.py:BlackjackApp]` and `[game_engine.py:BlackjackEngine]`.
- **Non-Blocking Tkinter Event Loop**: UI animations and dealer turns (`[blackjack.py:BlackjackApp._dealer_step]`, `[blackjack.py:BlackjackApp._stream_typewriter_step]`) schedule asynchronous callbacks via `root.after(...)` and cancel all active timer IDs in `[blackjack.py:BlackjackApp._cancel_all_active_timers]` and `[blackjack.py:BlackjackApp._on_close]`.
- **Horizon Stage vs. Card Table Felt Decoupling**: Upper stage rendering (`[ui_canvases.py:DealerStageCanvas]`) is strictly isolated from lower felt card/chip/altar accessories (`[ui_canvases.py:TableFeltCanvas]`, `[ui_canvases.py:HauntedAltarCanvas]`, `[ui_canvases.py:ChipVisualizer]`), which synchronize background slices via `get_felt_slice()`.
- **Headless Test Save Isolation**: `[blackjack.py:BlackjackApp.__init__]` automatically isolates `[save_manager.py:SaveManager]` to an ephemeral temporary file (`tempfile.mkdtemp()`) whenever `unittest` is loaded in `sys.modules` and no explicit `save_path` is passed, protecting production `blackjack_save.json`.
- **Dynamic Dialog Clamping & Adaptive Scrollbars**: Modal dialogs (`[ui_dialogs.py:SettingsDialog]`, `[ui_dialogs.py:ShortcutsDialog]`, `[ui_dialogs.py:WelcomeSplashDialog]`, `[dealer_wardrobe_dialog.py:WardrobeDialog]`) derive dimensions from live screen bounds (`screen_h - 80`) and auto-hide scrollbars via `pack_forget()` when `float(first) <= 0.0 and float(last) >= 1.0`.

---

## Global Side Effects

- **Persistent Save File I/O**: `[save_manager.py:SaveManager.save]` serializes career statistics, achievements, and mode preferences to `blackjack_save.json` via atomic `.tmp` file replacement (`Path.replace()`).
- **Audio & Procedural Voice Playback**: `[audio_assets.py:SoundManager]` and `[dialogue_voice_engine.py:AnimaleseVoiceEngine]` initialize `pygame.mixer` (`44100` Hz, 16-bit, 16 channels) to play `.ogg` samples from `audio/` and `audio/haunted/` as well as in-memory synthesized 16-bit PCM WAV voice blips, degrading silently when audio hardware or `pygame` is unavailable.
- **Private Font Registration & Asset Caching**: `[pixel_ui.py:load_all_pixel_fonts]` registers bundled `.ttf` pixel fonts from `assets/fonts/` into Windows GDI (`AddFontResourceExW` with `FR_PRIVATE=0x10`), and `[audio_assets.py:AssetScaler]` / `[dealer_actor.py:DealerActor]` load and cache PNG sprites from `cards/` and `assets/`.

---

## System Verification

- Run: `python -m unittest discover tests`
