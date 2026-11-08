# Project Architecture & Developer Documentation (`docs`)

## Overview
The `docs` directory contains authoritative system architecture blueprints, Class-Responsibility-Collaboration (CRC) indexes, distribution release guides, and feature design specifications for the Blackjack desktop application.

---

## Documentation Catalogue

### 1. Subsystem Architecture & Boundary Contracts
- **[`ARCHITECTURE_CRC.md`](ARCHITECTURE_CRC.md)**:
  - Comprehensive structural reference using Class-Responsibility-Collaboration (CRC) cards across 8 primary subsystems:
    - *Subsystem A*: Core Game Domain & Rules (`rules.py`, `game_engine.py`, `state_machine.py`, `card_counter.py`)
    - *Subsystem B*: Progression & Haunted Game Modes (`haunted_manager.py`)
    - *Subsystem C*: Dealer Puppet Engine & Dialogue Voice (`dealer_actor.py`, `dialogue_voice_engine.py`)
    - *Subsystem D*: Audio, Assets & Theme Configuration (`audio_assets.py`, `config.py`)
    - *Subsystem E*: Persistence, Records & Telemetry (`save_manager.py`)
    - *Subsystem F*: Table Felt Canvases & In-Table HUDs (`ui_canvases.py`, `ui_chip_renderer.py`, `card_counting_hud.py`)
    - *Subsystem G*: Modal Dialogs & Specialized Views (`ui_dialogs.py`, `dealer_wardrobe_dialog.py`)
    - *Subsystem H*: Central Orchestration Controller (`blackjack.py:BlackjackApp`)
  - Sequence diagrams detailing round deal lifecycles, hole card privacy invariants, and haunted narrative escalation.
  - Critical architectural review tracking God-object deconstruction and observer event bus decouplings.
- **[`DEALER_COSTUME_AUTHORING_GUIDE.md`](DEALER_COSTUME_AUTHORING_GUIDE.md)**:
  - Authoritative engineering and pixel-art pipeline reference for the **19-Layer Universal Chunky Pixel-Art Puppet Engine** (`dealer_actor.py`, `tools/deocclude_dealer_faceplates.py`, `tools/dealer_imaginative_costumes.py`, `tools/convert_selene_prof_vlad_costumes.py`).
  - Covers per-dealer `128x128` $\to$ `112x112` coordinate alignment tables, frame headroom & horizon rail grounding invariants, 3-stage white background / armpit pocket / outer-halo stripping, the 6 facial & jawline grafting modes, and dealing-arm pixel anatomy (`C` / `H` / `W` / `S`).
- **[`STAGE_BACKDROP_AUTHORING_GUIDE.md`](STAGE_BACKDROP_AUTHORING_GUIDE.md)**:
  - Authoritative engineering and pixel-art pipeline reference for **Horizon Stage Panoramic Backdrops** (`ui_canvases.py:DealerStageCanvas`, `tools/build_stage_backdrops.py`, `assets/haunted/backdrops/`).
  - Covers the locked `500x110` $\to$ `1000x220` (`1x`) & `2000x440` (`2x`) `NEAREST` crunchy pixel grid, architectural wall-band cropping, optical archway centering, the 4 UI clearance & contrast framing zones, 64-color 16-bit palette quantization, and the 4-file registration checklist.

### 2. Packaging, Distribution & Storefront Publishing
- **[`ITCH_IO_GUIDE.md`](ITCH_IO_GUIDE.md)**:
  - Step-by-step release packaging instructions using PyInstaller and `build_itch_release.ps1`.
  - Storefront metadata configuration, screenshot catalogue, upload tagging, and desktop client compatibility guidelines for [itch.io](https://itch.io).
- **[`release/`](release/README.md)**:
  - Authoritative publishing package for itch.io release v1.6.0, including store page description ([`main_game_page.md`](release/main_game_page.md)), devlog announcement ([`devlog_v1.6.0.md`](release/devlog_v1.6.0.md)), animated representative gameplay GIF ([`gameplay_3seat_card_counting.gif`](release/gameplay_3seat_card_counting.gif)), and full screenshots gallery ([`screenshots/`](release/screenshots/)).

### 3. Feature Design Specifications
- **[`designs/`](designs/README.md)**:
  - In-depth technical design documents covering Multi-Seat Wagering Engine ([`multi_seat_wagering.md`](designs/multi_seat_wagering.md)), Option B Crescent Baize UX Integration ([`multi_seat_wagering_ux_integration.md`](designs/multi_seat_wagering_ux_integration.md)), and Persistent Bankroll & Career Telemetry ([`persistent_bankroll_and_career_telemetry.md`](designs/persistent_bankroll_and_career_telemetry.md)).
  - Specification index in [`designs/SITEMAP.md`](designs/SITEMAP.md).

---

## Agent Discovery & Review Invariant
Per [`AGENTS.md`](../AGENTS.md#L9), all agents and developers must consult this documentation catalogue prior to authoring new subsystem modules, refactoring contracts, or modifying table invariants.

