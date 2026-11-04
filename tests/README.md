# Automated Test Suite (`tests`)

## Overview
The `tests` directory houses the complete automated test suite for the Blackjack desktop application, consisting of 47 modular test files and over 300 unit and integration tests. The suite validates core domain rules, finite state transitions, multi-seat progression, puppet presentation, procedural voice synthesis, save persistence, and Tkinter GUI geometry.

---

## Tiered Test Runner Architecture

Tests are executed via the centralized CLI runner [`run_tests.py`](../run_tests.py) or standard Python `unittest`:

```powershell
# Fast Smoke Suite (~10-15s) - Routine developer iterations & domain logic
python run_tests.py smoke

# Subsystem Verification Suites (~25-90s) - Targeted domain testing
python run_tests.py core        # Pure card rules, payouts, splits, double, surrender, shoe, FSM
python run_tests.py betting     # Wagering, bankroll persistence, all-in, insurance, chip stacks
python run_tests.py dealer      # Stage canvas, 7-layer puppet actor, wardrobe, voice engine
python run_tests.py haunted     # Supernatural phases, Card 13, altar candles, relics
python run_tests.py gui         # Table felt, layout geometry, modals, shortcuts, multi-seat UI

# Full System & Regression Suite (~5-6m) - Release verification
python run_tests.py full
# Or via standard discovery:
python -m unittest discover tests
```

---

## Test Catalogue by Subsystem

### 1. Core Domain, Rules & Engine
- [`test_game_rules.py`](test_game_rules.py): Dealer AI hit/stand rules (S17), 3:2 natural blackjack, push, and surrender payouts.
- [`test_scoring.py`](test_scoring.py): `score_hand()` algorithm across dynamic Ace valuations (soft vs. hard hands, multiple Aces).
- [`test_hand.py`](test_hand.py): `Hand` sequence protocol, card accumulation, soft status, and equality.
- [`test_deck.py`](test_deck.py): Card properties, suit/rank generation, and 52-card image existence.
- [`test_shoe.py`](test_shoe.py): 4-deck shoe composition (208 cards), depletion, and cut-card penetration triggers (~25%).
- [`test_state_machine.py`](test_state_machine.py): `GameStateMachine` phase transition validation across `RoundPhase`.
- [`test_game_engine.py`](test_game_engine.py): Headless `BlackjackEngine` round orchestration, dealing order, and payouts.
- [`test_event_bus.py`](test_event_bus.py): Synchronous pub-sub `EventHub` subscriber dispatch and payload delivery.
- [`test_architectural_integration.py`](test_architectural_integration.py): Cross-cutting integration across Engine, FSM, and EventBus.

### 2. Wagering, Bankroll & Side Bets
- [`test_betting.py`](test_betting.py): Payout math, 2:1 insurance with odd-bet rounding, chip visualizer sync, and rebuy logic.
- [`test_chip_visualizer_interactions.py`](test_chip_visualizer_interactions.py): Bankroll chip tray click staging, right-click deduction, and hover hitboxes.
- [`test_side_bets.py`](test_side_bets.py): Perfect Pairs and 21+3 poker paytables, min $5 main bet requirement, deduction refunds, and achievements.
- [`test_double_down.py`](test_double_down.py): Double Down eligibility, bankroll checks, single-card draw, and auto-stand.
- [`test_split.py`](test_split.py): Hand split qualification, Double After Split (DAS), and multi-hand resolution.
- [`test_surrender.py`](test_surrender.py): Late Surrender eligibility (initial 2 cards only), 50% wager refund, and hole card reveal.

### 3. Multi-Seat Wagering Subsystem
- [`test_multi_seat_engine.py`](test_multi_seat_engine.py): Headless clockwise deal order, inactive seat skipping, and canonical bankroll delegation.
- [`test_multi_seat_gui.py`](test_multi_seat_gui.py): 3-seat felt bounding boxes, active turn halos, and `MultiSeatInsuranceDialog`.
- [`test_multi_seat_normal_play.py`](test_multi_seat_normal_play.py): 22 end-to-end integration tests (player actions across seats, side bets, arrow key focus navigation, and round lifecycles).

### 4. Card Counting & Strategy Engine
- [`test_card_counter.py`](test_card_counter.py): Hi-Lo tag values (+1, 0, -1), Running Count, decks remaining, True Count, and Edge %.
- [`test_card_counting_hud.py`](test_card_counter.py): HUD pill rendering, floating count badges, and mid-shoe quiz test drills.
- [`test_basic_strategy.py`](test_basic_strategy.py): Pure Basic Strategy decision matrices (pair splits, soft hands, hard thresholds).

### 5. Dealer Puppet Actor, Wardrobe & Voice Synthesis
- [`test_dealer_actor.py`](test_dealer_actor.py): Sprite compositing, dynamic scale factor handling, and mouth/eye state transitions.
- [`test_dealer_actor_layers.py`](test_dealer_actor_layers.py): Layer coordinate math, anchor positioning, and costume resolution.
- [`test_dealer_stage_canvas.py`](test_dealer_stage_canvas.py): Panoramic backdrop scaling and sconce light flicker timers.
- [`test_living_animations.py`](test_living_animations.py): Idle breathing sine cycles, eye blink cadences, and typewriter text streaming.
- [`test_puppet_multi_layer_actor.py`](test_puppet_multi_layer_actor.py): 7-layer rigging, phonetic viseme mapping, and dummy asset integrity.
- [`test_roster_puppet_conversion.py`](test_roster_puppet_conversion.py): 19-layer puppet conversion across all 8 dealer personas.
- [`test_universal_puppet_faceplates.py`](test_universal_puppet_faceplates.py): Mannequin head de-occlusion, isolated eye sockets, and arm poses.
- [`test_dialogue_voice_engine.py`](test_dialogue_voice_engine.py): Procedural 16-bit mono 44.1 kHz PCM WAV synthesis and pitch inflections.
- [`test_dealer_wardrobe_dialog.py`](test_dealer_wardrobe_dialog.py): Wardrobe modal lifecycle, costume selection, and achievement unlocks.
- [`test_hall_of_fame_and_achievements.py`](test_hall_of_fame_and_achievements.py): Hall of Fame modal GUI, badge rendering, and telemetry banner.

### 6. Haunted Mode & Supernatural Narrative
- [`test_haunted_mode.py`](test_haunted_mode.py): Phases (`NORMAL` to `HELL_TABLE`), Card 13, altar candles, gravestones, and relics.
- [`test_typewriter_and_audio_accents.py`](test_typewriter_and_audio_accents.py): Typewriter text streaming and character audio accents.

### 7. GUI Layout, Canvas Felt & Modal Dialogs
- [`test_gui_state.py`](test_gui_state.py): Button states (Hit, Stand, Double, Split, Surrender, New Game) across game phases.
- [`test_table_felt.py`](test_table_felt.py): Procedural canvas baize texture generation and theme switching.
- [`test_table_hud.py`](test_table_hud.py): 2.5D animated table felt announcement popups and auto-dismiss timers.
- [`test_ui_layout.py`](test_ui_layout.py): JSON-driven UI layout configuration, origin resolution, and grid/pack options.
- [`test_ui_geometry_and_rendering.py`](test_ui_geometry_and_rendering.py): Plaque geometry and card bounding box clipping checks.
- [`test_pixel_ui.py`](test_pixel_ui.py): Pixel art UI primitives (`CanvasPixelPanel`, `PixelPlaqueFrame`, `CanvasPixelButton`).
- [`test_shortcuts_overlay.py`](test_shortcuts_overlay.py): Kenney prompt keycaps, two-tab navigation, and 24+ shortcut bindings.
- [`test_settings_dialog.py`](test_settings_dialog.py): Settings dialog lifecycle, play mode switching, volume sliders, and save reset modal.
- [`test_welcome_splash_dialog.py`](test_welcome_splash_dialog.py): Welcome modal lifecycle and table mode preferences.
- [`test_scale_and_display_modes.py`](test_scale_and_display_modes.py): Fixed 1.0x layout invariants and borderless fullscreen toggle.

### 8. Persistence, Sound & Build Infrastructure
- [`test_save_manager.py`](test_save_manager.py): Save file serialization, bankroll persistence, telemetry, and corruption recovery.
- [`test_sound.py`](test_sound.py): Polyphonic audio catalog loading, volume clamping, and headless degradation.
- [`test_test_runner.py`](test_test_runner.py): Tiered test runner module resolution and CLI parsing.
- [`test_version.py`](test_version.py): Enforces single source of truth for versioning across modules and documentation.

---

## Headless Testing Standards
Per [`AGENTS.md`](../AGENTS.md#L8):
1. **Window Isolation**: Headless GUI tests must invoke `root.withdraw()` during `setUp()` and cleanly invoke `_on_close()` and `root.destroy()` in `tearDown()`.
2. **Save Data Isolation**: Tests must never mutate or overwrite the player's production save file (`blackjack_save.json`). Fixtures must configure `SaveManager` with an ephemeral temporary directory (`tempfile.TemporaryDirectory`).
3. **Audio Disabled**: Automated test fixtures pass `sound_enabled=False` to guarantee deterministic execution without audio hardware dependencies.
4. **Configuration-Driven Assertions**: Never assert against arbitrary hardcoded pixel constants; compare geometry against live container boundaries (`winfo_screenheight()`, `scale_factor`).

