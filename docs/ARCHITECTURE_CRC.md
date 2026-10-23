# Blackjack Architecture & CRC Cards Documentation

This document provides a comprehensive structural reference for the **Blackjack** desktop application using **Class-Responsibility-Collaboration (CRC) Cards**, accompanied by system interaction diagrams and an architectural review identifying high-leverage areas of potential improvement.

---

## Table of Contents
1. [Architectural Overview & Subsystem Map](#1-architectural-overview--subsystem-map)
2. [Class-Responsibility-Collaboration (CRC) Cards](#2-class-responsibility-collaboration-crc-cards)
   - [Subsystem A: Core Game Domain & Rules](#subsystem-a-core-game-domain--rules)
   - [Subsystem B: Progression & Haunted Game Modes](#subsystem-b-progression--haunted-game-modes)
   - [Subsystem C: Dealer Puppet Engine & Dialogue Voice](#subsystem-c-dealer-puppet-engine--dialogue-voice)
   - [Subsystem D: Audio, Assets & Theme Configuration](#subsystem-d-audio-assets--theme-configuration)
   - [Subsystem E: Persistence, Records & Achievements](#subsystem-e-persistence-records--achievements)
   - [Subsystem F: Table Felt Canvases & In-Table HUDs](#subsystem-f-table-felt-canvases--in-table-huds)
   - [Subsystem G: Modal Dialogs & Specialized Views](#subsystem-g-modal-dialogs--specialized-views)
   - [Subsystem H: Central Orchestration Controller](#subsystem-h-central-orchestration-controller)
3. [System Collaboration Flows](#3-system-collaboration-flows)
   - [Round Deal & Lifecycle Sequence](#round-deal--lifecycle-sequence)
   - [Card Counting & Hole Card Privacy Invariant](#card-counting--hole-card-privacy-invariant)
   - [Haunted Altar & Supernatural Dialogue Flow](#haunted-altar--supernatural-dialogue-flow)
4. [Critical Review & Areas of Potential Improvement](#4-critical-review--areas-of-potential-improvement)
   - [1. Deconstruction of the `BlackjackApp` God Object](#1-deconstruction-of-the-blackjackapp-god-object)
   - [2. Event-Driven Observer / Pub-Sub Architecture](#2-event-driven-observer--pub-sub-architecture)
   - [3. Formalization of Domain Models & Typing](#3-formalization-of-domain-models--typing)
   - [4. Pure FSM (Finite State Machine) State Transition Validator](#4-pure-fsm-finite-state-machine-state-transition-validator)
   - [5. Decoupling View Presentation from Table Felt State](#5-decoupling-view-presentation-from-table-felt-state)
5. [Summary Matrix of Improvement Recommendations](#5-summary-matrix-of-improvement-recommendations)

---

## 1. Architectural Overview & Subsystem Map

The application is structured into decoupled domain rules, puppet presentation components, procedural audio synthesizers, persistence managers, and a centralized Tkinter GUI controller:

```mermaid
graph TD
    subgraph Core Domain [Core Rules & Domain]
        rules[rules.py: Card, RoundPhase, BasicStrategyDecision]
        counter[card_counter.py: HiLoCardCounter]
    end

    subgraph Meta Game [Progression & State]
        haunted[haunted_manager.py: HauntedManager, Blessing]
        save[save_manager.py: SaveManager, SaveData, Achievements]
    end

    subgraph Audio & Assets [Audio & Theme Subsystem]
        audio[audio_assets.py: SoundManager, AssetScaler]
        voice[dialogue_voice_engine.py: AnimaleseVoiceEngine]
        config[config.py: ThemePalette]
    end

    subgraph Dealer Actor [Puppet & Actor Subsystem]
        actor[dealer_actor.py: DealerActor, CharacterProfile]
    end

    subgraph Presentation Canvases [Canvases & In-Table HUDs]
        stage_c[ui_canvases.py: DealerStageCanvas]
        felt_c[ui_canvases.py: TableFeltCanvas]
        chip_c[ui_canvases.py: ChipVisualizer]
        altar_c[ui_canvases.py: HauntedAltarCanvas]
        soul_c[ui_canvases.py: SoulMeterCanvas]
        hud[ui_canvases.py: TableAnnouncementHUD]
        count_hud[card_counting_hud.py: CardCountingHud, FloatingCountBadge]
    end

    subgraph Modal Views [Toplevel Dialogs]
        settings_dlg[ui_dialogs.py: SettingsDialog]
        shortcuts_dlg[ui_dialogs.py: ShortcutsDialog]
        splash_dlg[ui_dialogs.py: WelcomeSplashDialog]
        story_dlg[ui_dialogs.py: StoryDialogueDialog]
        draft_dlg[ui_dialogs.py: AngelicDraftDialog]
        wardrobe_dlg[dealer_wardrobe_dialog.py: WardrobeDialog]
        quiz_dlg[card_counting_hud.py: CardCountingQuizDialog]
    end

    subgraph Orchestration [Central Controller]
        app[blackjack.py: BlackjackApp]
    end

    app --> rules
    app --> counter
    app --> haunted
    app --> save
    app --> audio
    app --> voice
    app --> actor
    app --> stage_c
    app --> felt_c
    app --> chip_c
    app --> altar_c
    app --> soul_c
    app --> hud
    app --> count_hud

    app --> settings_dlg
    app --> shortcuts_dlg
    app --> splash_dlg
    app --> story_dlg
    app --> draft_dlg
    app --> wardrobe_dlg
    app --> quiz_dlg

    stage_c --> actor
    actor --> voice
    actor --> audio
```

---

## 2. Class-Responsibility-Collaboration (CRC) Cards

---

### Subsystem A: Core Game Domain & Rules

#### `Card` & Pure Domain Functions ([rules.py](../rules.py#L44))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Rank (`int` 1--13), suit (`str` `♠`, `♥`, `♦`, `♣`), face value, display label, and asset file name.<br>**Knows**: Special card identity (e.g. Card 13 cursed Card of Skulls, Ace soft value).<br>**Does**: Formats rank string (`"A"`, `"K"`, `"13"`), computes point values, checks blackjack / bust properties, decomposes wagers (`breakdown_chips`) and bankroll reserve stacks (`breakdown_bankroll_piles`) across all 5 chip denominations (\$5, \$25, \$100, \$500, \$1,000 Platinum), and builds/shuffles multi-deck shoes (`build_shoe`). | None (Pure immutable value object / stateless domain functions). |

#### `RoundPhase` ([rules.py](../rules.py#L99))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Enumerated round lifecycles (`BETTING`, `DEALING`, `PLAYER_TURN`, `DEALER_TURN`, `ROUND_OVER`).<br>**Does**: Provides explicit state identifiers synchronized via `BlackjackApp.round_phase` across the game lifecycle. | Collaborates with [BlackjackApp](../blackjack.py) and [TableAnnouncementHUD](../ui_canvases.py#L645). |

#### `BasicStrategyDecision` ([rules.py](../rules.py#L226))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Optimal mathematical Blackjack decisions (`HIT`, `STAND`, `DOUBLE`, `SPLIT`, `SURRENDER`).<br>**Does**: Evaluates player hand vs. dealer upcard according to standard casino multi-deck basic strategy charts (hard totals, soft totals, pair splitting). | Collaborates with [Card](../rules.py#L44) and [BlackjackApp](../blackjack.py). |

#### `HiLoCardCounter` ([card_counter.py](../card_counter.py#L23))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Running count (RC), total face-up cards observed, initial shoe deck count (`DEFAULT_DECK_COUNT = 4` decks / 208 cards), and remaining deck estimation.<br>**Does**: Consumes observed face-up cards and applies standard Hi-Lo card counting weights ($2\text{--}6 \to +1$, $7\text{--}9 \to 0$, $10\text{--}\text{A} \to -1$).<br>**Does**: Computes estimated remaining decks ($\max(0.5, \text{cards} / 52.0)$) and mathematically converts RC to True Count ($\text{TC} = \text{RC} / \text{Decks}$).<br>**Does**: Provides betting unit recommendations based on Kelly criterion / True Count thresholds. | Collaborates with [Card](../rules.py#L44), [CardCountingHud](../card_counting_hud.py#L58), and [BlackjackApp](../blackjack.py). |

---

### Subsystem B: Progression & Haunted Game Modes

#### `HauntedManager` ([haunted_manager.py](../haunted_manager.py#L137))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Active supernatural phase (`NORMAL`, `CREEP`, `OMEN`, `SNUFFING`, `HELL_TABLE`, `VICTORY`), hand count, candle states (5 candles), Tug-of-War Soul Meter percentage (`0%`--`100%`), active blessings, and per-hand ability flags (`miracle_used_this_hand`, `seraph_used_this_hand`).<br>**Does**: Evaluates game state triggers on round outcomes (win, loss, bust, push, natural).<br>**Does**: Advances progression narrative phases, snuffs candles on lost rounds, injects Card 13 (Cursed Card of Skulls), and triggers Hell's Table when all 5 candles extinguish.<br>**Does**: Manages Angelic Blessing drafts at `50%` and `75%` Soul Meter milestones and enforces per-hand blessing powers (such as `Blessing.SERAPH` auto-banishing and redrawing a busting hit card once per hand). | Collaborates with [Phase](../haunted_manager.py#L28), [Blessing](../haunted_manager.py#L38), [BlessingDetails](../haunted_manager.py#L50), [HauntedAltarCanvas](../ui_canvases.py#L815), [SoulMeterCanvas](../ui_canvases.py#L461), and [BlackjackApp](../blackjack.py). |

#### `Phase` ([haunted_manager.py](../haunted_manager.py#L28))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: The enumeration of haunted progression tiers (`NORMAL`, `CREEP`, `OMEN`, `SNUFFING`, `HELL_TABLE`, `VICTORY`).<br>**Does**: Dictates table visual style, dealer demeanor, HUD switching (swapping `ChipVisualizer` for `SoulMeterCanvas` in `HELL_TABLE`), and cursed card deck injection. | Collaborates with [HauntedManager](../haunted_manager.py#L137) and [BlackjackApp](../blackjack.py). |

#### `Blessing` & `BlessingDetails` ([haunted_manager.py](../haunted_manager.py#L38))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Blessing ID (`SERAPH`, `EYE`, `SMITE`, `CHERUB`, `TITHE`, `MIRACLE`, `HALLOWED`), human-readable title, icon badge, and gameplay modifier description.<br>**Does**: Supplies metadata for `AngelicDraftDialog` presentation and modifies game rule calculations during rounds (e.g. `SERAPH` bust-card auto-redraw once per hand, `EYE` immediate dealer hole card exposure and count observation, `CHERUB` 22-bust forgiveness, `MIRACLE` manual card banish & redraw). | Collaborates with [AngelicDraftDialog](../ui_dialogs.py#L130) and [HauntedManager](../haunted_manager.py#L137). |

---

### Subsystem C: Dealer Puppet Engine & Dialogue Voice

#### `DealerActor` ([dealer_actor.py](../dealer_actor.py#L133))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Active dealer identity (`character_id` / `current_character` across all 8 personas: `julian`, `tiffany`, `malphas`, `uriel`, `mortimer`, `selene`, `vladimir`, `dummy`), active costume alias, 7 puppet layer image composites (*shadow*, *torso*, *neck*, *head*, *eyes*, *mouth*, *arms*), idle breathing cycle phase, procedural blink countdown, and emotional expression state.<br>**Does**: Loads, caches, and scales multi-layer character PNG sprites.<br>**Does**: Computes breathing offsets and dynamic eye-blink durations; selects phonetic mouth visemes during speech (`a`, `o`, `e`, `f`, `talk`, `smirk`, `gasp`).<br>**Does**: Blits composite character layers onto the stage canvas; triggers character voice utterances on typewriter dialogue events. | Collaborates with [CharacterProfile](../dealer_actor.py#L33), [AnimaleseVoiceEngine](../dialogue_voice_engine.py#L25), [SoundManager](../audio_assets.py#L140), and [DealerStageCanvas](../ui_canvases.py#L1319). |

#### `CharacterProfile` ([dealer_actor.py](../dealer_actor.py#L33))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Character display name, lore title, backdrop setting, baseline voice pitch, vocal speed, sound timbre category, unlocked status, and costume aliases.<br>**Does**: Supplies profile metadata used to configure `DealerActor`, `AnimaleseVoiceEngine`, and `WardrobeDialog`. | Collaborates with [DealerActor](../dealer_actor.py#L133) and [WardrobeDialog](../dealer_wardrobe_dialog.py#L28). |

#### `AnimaleseVoiceEngine` ([dialogue_voice_engine.py](../dialogue_voice_engine.py#L25))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Acoustic parameters per dealer (fundamental frequency $F_0$, harmonics, formant filter frequencies, phonetic viseme map, volume scale).<br>**Does**: Procedurally synthesizes 16-bit mono 44.1 kHz PCM audio in memory with zero external sound files.<br>**Does**: Dynamically inflects pitch (rising on `?`, falling on `.`) and plays phonetic audio chirps matching typewriter text animation. | Collaborates with [DealerActor](../dealer_actor.py#L133) and [SoundManager](../audio_assets.py#L140). |

---

### Subsystem D: Audio, Assets & Theme Configuration

#### `SoundManager` ([audio_assets.py](../audio_assets.py#L140))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Master mute flag, SFX volume, dialogue voice volume, and cached sound effects (`.ogg`).<br>**Does**: Initializes 16-channel polyphonic `pygame.mixer` audio backend with graceful headless fallback; plays card slides, chip clinks, shuffles, bets, rakes, and win/loss fanfares asynchronously without blocking the UI thread. | Collaborates with [BlackjackApp](../blackjack.py) and [SettingsDialog](../ui_dialogs.py#L219). |

#### `AssetScaler` ([audio_assets.py](../audio_assets.py#L28))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Active UI scale multiplier (`1.0x` standard, `2.0x` HiDPI).<br>**Does**: Resolves absolute asset paths across development directories and PyInstaller bundles (`sys._MEIPASS`). Scales card images, icons, and textures using PIL with high-quality resampling filters. | Collaborates with [BlackjackApp](../blackjack.py) and all presentation canvases. |

#### `KeyboardIconLoader` ([audio_assets.py](../audio_assets.py#L210))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Curated Kenney keyboard and mouse UI sprite assets.<br>**Does**: Loads, resizes, and caches visual keyboard shortcut badges for in-game HUDs and shortcut overlay dialogs. | Collaborates with [ShortcutsDialog](../ui_dialogs.py#L555). |

#### `ThemePalette` ([config.py](../config.py#L65))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Centralized UI color tokens (felt colors, button states, stage backdrops, text typography, accent gold, border highlights) and chip denomination styling (\$5 White, \$25 Green, \$100 Black, \$500 Purple, \$1,000 Platinum).<br>**Does**: Standardizes color palette across Classic, Haunted, Hell's Table, and Celestial Victory environments. | Collaborates with all UI Canvases, Dialogs, and [BlackjackApp](../blackjack.py). |

---

### Subsystem E: Persistence, Records & Achievements

#### `SaveManager` ([save_manager.py](../save_manager.py#L182))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Active save file path (`blackjack_save.json`), fallback paths, and in-memory `SaveData` payload.<br>**Does**: Safely serializes and deserializes player records, unlocked dealers, unlocked costumes, card counting test streaks, and 8 achievement badges. Gracefully recovers from corrupted JSON files. | Collaborates with [SaveData](../save_manager.py#L140), [Achievements](../save_manager.py#L65), [HighScores](../save_manager.py#L26), and [BlackjackApp](../blackjack.py). |

#### `SaveData`, `Achievements`, `HighScores` ([save_manager.py](../save_manager.py#L26))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Persistent player stats: total hands played, hands won/lost/pushed, natural blackjacks, peak bankroll, Hell's Table clears, card counting quiz streaks, and all 8 unlocked achievements.<br>**Does**: Provides validated dataclass structures for JSON serialization. | Collaborates with [SaveManager](../save_manager.py#L182). |

---

### Subsystem F: Table Felt Canvases & In-Table HUDs

#### `DealerStageCanvas` ([ui_canvases.py](../ui_canvases.py#L1319))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Stage backdrop image, 3D horizon rail dimensions, dynamic sconce lighting timers, dealer speech bubble bounds, and typewriter text position.<br>**Does**: Renders atmospheric room environment and composite dealer puppet; animates flickering candles and handles interactive speech bubble typewriter text streaming. | Collaborates with [DealerActor](../dealer_actor.py#L133), [AnimaleseVoiceEngine](../dialogue_voice_engine.py#L25), and [BlackjackApp](../blackjack.py). |

#### `TableFeltCanvas` ([ui_canvases.py](../ui_canvases.py#L1675))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Casino table boundaries, gold rule arcs, vignette shading, and child widget background slice coordinates.<br>**Does**: Draws high-resolution baize felt texture, casino markings, and synchronizes seamless child frame background slices. | Collaborates with [BlackjackApp](../blackjack.py). |

#### `ChipVisualizer` ([ui_canvases.py](../ui_canvases.py#L59))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Current wager denomination breakdown and player bankroll reserve piles across all 5 denominations (\$5, \$25, \$100, \$500, \$1,000 Platinum), 3D stack offsets, and pile bounding boxes.<br>**Does**: Visually renders realistic layered casino chip stacks in the top Betting Spot and bottom interactive Bankroll Reserve Tray (`render_bankroll_piles`); handles direct click-to-bet on reserve piles (`trigger_pile_click`); executes non-blocking chip slide and rake animations. | Collaborates with [BlackjackApp](../blackjack.py) and [SoundManager](../audio_assets.py#L140). |

#### `TableAnnouncementHUD` ([ui_canvases.py](../ui_canvases.py#L645))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Active table banner messages, status pill labels, and banner typography.<br>**Does**: Presents non-intrusive in-felt status announcements (`"BLACKJACK! 3:2"`, `"DEALER BUSTS"`, `"SERAPH'S GRACE"`, `"MIRACLE DRAW"`) with fade/slide animations and click-to-dismiss. | Collaborates with [BlackjackApp](../blackjack.py). |

#### `HauntedAltarCanvas` ([ui_canvases.py](../ui_canvases.py#L815))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Altar geometry, 5 candle coordinates, flame particle timers, gravestone elevation offsets, and smoke animations.<br>**Does**: Animates atmospheric burning candle flames; triggers candle snuffing animations on player losses; renders 2.5D gravestones rising from the table felt. | Collaborates with [HauntedManager](../haunted_manager.py#L137) and [BlackjackApp](../blackjack.py). |

#### `SoulMeterCanvas` ([ui_canvases.py](../ui_canvases.py#L461))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Current Tug-of-War Soul Meter percentage (`0%`--`100%`), target display value, particle glow effects, and milestone markers (`50%`, `75%`).<br>**Does**: Replaces `ChipVisualizer` in the bottom-right table dock during `Phase.HELL_TABLE` to render the interactive Tug-of-War Soul Meter HUD on the felt. | Collaborates with [HauntedManager](../haunted_manager.py#L137) and [BlackjackApp](../blackjack.py). |

#### `CardCountingHud` & `FloatingCountBadge` ([card_counting_hud.py](../card_counting_hud.py#L20))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Hi-Lo Running Count, True Count, remaining shoe decks (`4.0` default), visibility toggle state, and floating count badge coordinates.<br>**Does**: Draws compact felt-embedded count HUD; animates transient floating text badges (`+1`, `-1`, `0`) above dealt cards; provides betting spread advice. | Collaborates with [HiLoCardCounter](../card_counter.py#L23) and [BlackjackApp](../blackjack.py). |

---

### Subsystem G: Modal Dialogs & Specialized Views

#### `SettingsDialog` ([ui_dialogs.py](../ui_dialogs.py#L219))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Audio toggles, dialogue voice toggle, Haunted Mode toggle, Card Counting HUD/tag toggles, and HiDPI scale factor (`1x` / `2x`).<br>**Does**: Provides adaptive scrollable configuration controls, validates live config changes, and applies them to [BlackjackApp](../blackjack.py) with confirmation safety for save resets. | Collaborates with [SoundManager](../audio_assets.py#L140) and [BlackjackApp](../blackjack.py). |

#### `ShortcutsDialog` ([ui_dialogs.py](../ui_dialogs.py#L555))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: All keyboard and mouse shortcut mappings across Gameplay, Wagering (`1`--`5` for \$5--\$1,000 chips), Card Counting, and System controls (`Shift+S`, `Shift+W`, `Shift+H`, `F1`/`?`).<br>**Does**: Renders scrollable two-column modal HUD with Kenney graphical keycap icons, auto-hiding scrollbar, and mousewheel bindings. | Collaborates with [KeyboardIconLoader](../audio_assets.py#L210) and [BlackjackApp](../blackjack.py). |

#### `WelcomeSplashDialog` ([ui_dialogs.py](../ui_dialogs.py#L876))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: First-launch overview of Classic Casino, Haunted Mode, Card Counting Trainer, and essential shortcuts.<br>**Does**: Displays introductory splash modal on first run (or via Help button) with adaptive scrolling. | Collaborates with [BlackjackApp](../blackjack.py). |

#### `StoryDialogueDialog` ([ui_dialogs.py](../ui_dialogs.py#L31))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Narrative story script branches, speaker character, portraits, and proceed callbacks.<br>**Does**: Displays modal narrative dialogues during major Haunted mode milestone transitions (Hell's Table descent and Celestial Exorcism victory). | Collaborates with [DealerActor](../dealer_actor.py#L133) and [BlackjackApp](../blackjack.py). |

#### `AngelicDraftDialog` ([ui_dialogs.py](../ui_dialogs.py#L130))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: 3 randomly selected Blessing cards drawn from the active pool at `50%` and `75%` Soul Meter milestones.<br>**Does**: Renders 3 selectable blessing cards and equips the chosen celestial power to `HauntedManager`. | Collaborates with [HauntedManager](../haunted_manager.py#L137) and [BlackjackApp](../blackjack.py). |

#### `WardrobeDialog` ([dealer_wardrobe_dialog.py](../dealer_wardrobe_dialog.py#L28))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: All 8 dealer character profiles, unlocked statuses, unlock achievement criteria, 8 Hall of Fame achievement plaques, and `initial_tab` selection.<br>**Does**: Displays two-tab modal (Tab 0: Wardrobe Closet; Tab 1: Hall of Fame & Trophy Shelf) with interactive character sprite/voice previews and instant costume equipping. | Collaborates with [CharacterProfile](../dealer_actor.py#L33), [DealerActor](../dealer_actor.py#L133), [SaveManager](../save_manager.py#L182), and [BlackjackApp](../blackjack.py). |

#### `CardCountingQuizDialog` ([card_counting_hud.py](../card_counting_hud.py#L194))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Current ground-truth Running Count (RC) held by [HiLoCardCounter](../card_counter.py#L23) and player's streak count.<br>**Does**: Challenges player to input the current Running Count; verifies answer, plays audio cue, records streak in `SaveManager`, and unlocks `Card Shark` / `Rain Man` achievements. | Collaborates with [HiLoCardCounter](../card_counter.py#L23), [SaveManager](../save_manager.py#L182), and [BlackjackApp](../blackjack.py). |

---

### Subsystem H: Central Orchestration Controller

#### `BlackjackApp` ([blackjack.py](../blackjack.py#L155))
| Responsibility | Collaboration |
| :--- | :--- |
| **Knows**: Application version (`__version__ = "1.3.1"`), Tkinter root and widget tree; active deck shoe, player hand(s), dealer hand, active split hand index; chip bankroll and active bets; `round_phase` (`RoundPhase`), dealing timers, and re-entrancy flags (`_dealing`, `_round_over`).<br>**Does**: Coordinates initial GUI layout and dynamic scaling.<br>**Does**: Handles user input (keyboard shortcuts, buttons, interactive bankroll chip piles); drives the dealing animation sequence; resolves round outcomes and payouts (\$5, \$25, \$100, \$500, \$1,000 chip math); updates score displays and synchronizes table HUDs (`ChipVisualizer` vs. `SoulMeterCanvas`), puppet expressions, and persistence saves. | Collaborates with **ALL** subsystems (Domain rules, Card counter, Haunted manager, Save manager, Sound manager, Puppet actor, Canvases, and Dialogs). |

---

## 3. System Collaboration Flows

### Round Deal & Lifecycle Sequence

```mermaid
sequenceDiagram
    autonumber
    actor Player
    participant App as BlackjackApp
    participant Chip as ChipVisualizer
    participant Shoe as DeckShoe (rules.py)
    participant Counter as HiLoCardCounter
    participant Stage as DealerStageCanvas / Actor
    participant Felt as TableFeltCanvas
    participant Audio as SoundManager

    Player->>App: Stage Bet (\$100) via Button, Key, or Bankroll Pile & Click Deal
    App->>Chip: Render Bet Stack & Update Bankroll Reserve Piles
    App->>Audio: Play chip_clink.ogg
    App->>Shoe: Draw Card (Player 1)
    Shoe-->>App: Card(10, '♠')
    App->>Counter: observe_card(Card(10, '♠'))
    App->>Felt: Render Card 1
    App->>Audio: Play card_slide.ogg
    
    App->>Shoe: Draw Card (Dealer Upcard)
    Shoe-->>App: Card(6, '♦')
    App->>Counter: observe_card(Card(6, '♦'))
    App->>Felt: Render Dealer Upcard
    
    App->>Shoe: Draw Card (Player 2)
    Shoe-->>App: Card(1, '♥') (Ace)
    App->>Counter: observe_card(Card(1, '♥'))
    
    App->>Shoe: Draw Card (Dealer Downcard)
    Shoe-->>App: Card(10, '♣') [Hole Card]
    Note over Counter,App: Invariant: Dealer downcard is NOT observed until revealed (unless Blessing.EYE is active)!
    App->>Felt: Render Face-Down Card Back

    App->>App: Evaluate Blackjack Invariants (Player has 21)
    App->>Stage: Trigger Actor Reaction ('shocked')
    App->>Counter: observe_card(Card(10, '♣')) [Flipping Downcard]
    App->>Felt: Flip Dealer Hole Card Face-Up
    App->>App: Settle Payout (3:2 Natural Blackjack = \$150)
    App->>Chip: Animate Rake & Payout to Player
    App->>Audio: Play win_fanfare.ogg
```

### Card Counting & Hole Card Privacy Invariant

A critical architectural invariant in the application is the **Dealer Hole Card Privacy Invariant**:
- In casino blackjack, the dealer's facedown downcard must never impact the running count before it is legitimately exposed.
- `HiLoCardCounter.observe_card()` is invoked for player cards and the dealer's *upcard* on initial deal.
- The dealer hole card is only supplied to `HiLoCardCounter` when `_reveal_dealer_hole_card()` executes at the start of the dealer's turn, upon early round conclusion (such as immediate player natural or bust), or immediately on initial deal if `Blessing.EYE` (*Eye of Providence*) deals the hole card face-up (`_hole_card_observed = True`).
- Subsequent dealer hit cards drawn during `_dealer_step()` are also immediately observed via `_observe_card_face_up()`.

### Haunted Altar & Supernatural Dialogue Flow

When playing in Haunted Mode:
1. `BlackjackApp.new_game()` invokes `HauntedManager.advance_hand()`.
2. As `HauntedManager` transitions phases (`NORMAL` $\to$ `CREEP` $\to$ `OMEN` $\to$ `SNUFFING` $\to$ `HELL_TABLE` $\to$ `VICTORY`):
   - Table felt color tokens update via `ThemePalette`.
   - `DealerStageCanvas` switches backdrop and prompts `DealerActor` to adopt corresponding personas (`julian` $\to$ `malphas` $\to$ `uriel`) and supernatural dialogue lines.
   - `AnimaleseVoiceEngine` shifts fundamental frequency and timbre parameters.
3. On round loss in `Phase.SNUFFING`:
   - `HauntedManager.on_round_outcome()` extinguishes a candle flame (`5` $\to$ `0`).
   - `HauntedAltarCanvas` plays flame extinguish particle effects and raises a 2.5D gravestone.
   - When the 5th candle is snuffed (`candles_remaining == 0`), `_conclude_round()` detects the transition into `Phase.HELL_TABLE`, invokes `_trigger_hell_table()`, hides `ChipVisualizer`, and grids `SoulMeterCanvas` (the 2.5D Tug-of-War Soul Meter) in the bottom-right dock.

---

## 4. Critical Review & Areas of Potential Improvement

While the codebase is modularized into 12 focused modules, an architectural analysis identifies several long-term structural opportunities for future refactoring:

---

### 1. Deconstruction of the `BlackjackApp` God Object

#### Current State
[blackjack.py](../blackjack.py) spans **~4,000 lines of code**. The `BlackjackApp` class functions as a central controller that manages:
- GUI layout and window management.
- Raw deck state (`self.deck`, `self.deck_count`).
- Betting rules, bankroll math, and payout resolution.
- Hand splitting (`self.player_hands`, `self.hand_bets`, `self.active_hand_index`).
- Timer animation callbacks (`self._deal_timer_id`, `self._dealer_timer_id`).
- Keyboard shortcuts and button bindings.

#### Proposed Architecture Improvement: Split into Headless Engine & GUI Adapter
Extract stateful round orchestration into an independent, zero-GUI `BlackjackEngine` that builds on top of `rules.py`:

```mermaid
classDiagram
    class BlackjackEngine {
        +Shoe deck
        +List~Hand~ player_hands
        +Hand dealer_hand
        +int bankroll
        +int current_bet
        +RoundPhase phase
        +deal_initial_cards()
        +hit()
        +stand()
        +double_down()
        +split()
        +surrender()
        +resolve_outcomes()
    }

    class BlackjackApp {
        +Tk root
        +TableFeltCanvas felt
        +DealerStageCanvas stage
        +BlackjackEngine engine
        +bind_events()
        +sync_ui_with_engine()
    }

    BlackjackApp --> BlackjackEngine : Delegates domain actions to
```

*Benefit*: Full multi-hand round sequences become 100% testable without instantiating a `tkinter.Tk` root, reducing test execution time even further.

---

### 2. Event-Driven Observer / Pub-Sub Architecture

#### Current State
Communication across subsystems is coordinated via direct method calls on `BlackjackApp`:
- `self.table_announcement_hud.show_announcement(...)`
- `self.haunted_altar_canvas.update_candles(...)`
- `self.dealer_actor.set_state(...)`
- `self.sound_manager.play(...)`

#### Proposed Architecture Improvement: Internal Event Bus
Introduce a lightweight event bus (e.g. `EventHub` with pub-sub):

```python
# Event definitions
class GameEvent:
    CARD_DEALT = "card_dealt"
    ROUND_RESOLVED = "round_resolved"
    BET_PLACED = "bet_placed"
    CANDLE_SNUFFED = "candle_snuffed"
    DEALER_EXPRESSION_CHANGED = "dealer_expression_changed"

# Example decoupled subscriber
event_hub.subscribe(GameEvent.CARD_DEALT, lambda evt: sound_manager.play("card_slide"))
event_hub.subscribe(GameEvent.CARD_DEALT, lambda evt: card_counter.observe_card(evt.card))
event_hub.subscribe(GameEvent.ROUND_RESOLVED, lambda evt: save_manager.record_hand(evt))
```

*Benefit*: Eliminates cascading cross-calls when adding new visual effects, sound accents, or achievements.

---

### 3. Formalization of Domain Models & Typing

#### Current State
While `Card` is a formal `NamedTuple` in `rules.py`, player splits are managed as parallel lists on `BlackjackApp`: `self.player_hands`, `self.hand_bets`, `self.hand_frames`, `self.hand_score_vars`.

#### Proposed Architecture Improvement: Dedicated `Hand` Class
Encapsulate cards, bets, and status into a first-class `Hand` domain object:

```python
@dataclass
class Hand:
    cards: list[Card] = field(default_factory=list)
    bet: int = 0
    is_doubled: bool = False
    is_surrendered: bool = False
    is_settled: bool = False
    outcome: Optional[str] = None

    @property
    def score(self) -> int:
        return score_hand(self.cards)

    @property
    def is_blackjack(self) -> bool:
        return len(self.cards) == 2 and self.score == 21

    @property
    def is_bust(self) -> bool:
        return self.score > 21
```

*Benefit*: Simplifies split hand management by replacing parallel lists with a single `list[Hand]`.

---

### 4. Pure FSM (Finite State Machine) State Transition Validator

#### Current State
`BlackjackApp` maintains `self.round_phase` (`RoundPhase`) synchronized across `BETTING`, `DEALING`, `PLAYER_TURN`, `DEALER_TURN`, and `ROUND_OVER`, alongside legacy boolean flags (`self._dealing`, `self._round_over`, `self._player_stood`, `self._in_betting_phase`).

#### Proposed Architecture Improvement: Formal State Transitions
Retire the remaining legacy boolean flags so all guards read exclusively from a centralized state transition table:

```mermaid
stateDiagram-v2
    [*] --> BETTING
    BETTING --> DEALING : Place Bet & Deal
    DEALING --> PLAYER_TURN : Initial Deal Complete
    PLAYER_TURN --> PLAYER_TURN : Hit / Double / Split / Miracle
    PLAYER_TURN --> DEALER_TURN : Stand / 21
    DEALER_TURN --> DEALER_TURN : Dealer Hits (< 17)
    DEALER_TURN --> ROUND_OVER : Dealer Stands / Busts
    PLAYER_TURN --> ROUND_OVER : Bust / Surrender
    ROUND_OVER --> BETTING : New Round
```

---

### 5. Decoupling View Presentation from Table Felt State

#### Current State
- Card image widgets (`tkinter.Label`) are created inside child `tkinter.Frame` containers (`self.player_card_frame`, `self.dealer_card_frame`) whose background slices are synchronized with `TableFeltCanvas`.

#### Proposed Architecture Improvement: Unified `TableFeltView`
Consolidate card sprite rendering, chip stack drawing, and table accessories into a single canvas coordinate system on `TableFeltCanvas`:
- Cards rendered directly on canvas via `create_image()` rather than child `tkinter.Label` frames.
- Standardizes z-ordering (Felt background $\to$ Markings $\to$ Chip stacks $\to$ Playing cards $\to$ Floating count badges).

---

## 5. Summary Matrix of Improvement Recommendations

| Recommendation | Scope / Effort | Impact | Risk | Target Phase |
| :--- | :--- | :--- | :--- | :--- |
| **1. Extract Headless `BlackjackEngine`** | High | Eliminates God Object; makes stateful multi-hand rounds testable without Tk. | Medium | Next Architectural Milestone |
| **2. Internal Event Bus (Pub-Sub)** | Medium | Decouples audio, HUDs, dealer animations, and persistence. | Low | Incremental |
| **3. First-Class `Hand` Domain Model** | Low | Replaces parallel lists for split hands with clean OOP encapsulation. | Very Low | Next Minor Release |
| **4. Consolidate Legacy Booleans into `RoundPhase` FSM** | Low | Retires `_dealing`/`_round_over` booleans in favor of `round_phase` alone. | Low | Next Minor Release |
| **5. Unified Canvas Card Rendering** | Medium | Eliminates child frame slicing and unifies z-index stacking. | Low | UI Polish Milestone |
