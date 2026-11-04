# Casino Sound Effects Catalog (`audio`)

## Overview
The `audio` directory contains 42 tactile casino sound effects (.ogg files) powering the acoustic environment of the Blackjack desktop application. Sound effects are polyphonically managed by [`audio_assets.py:SoundManager`](../audio_assets.py) using `pygame.mixer` (via `pygame-ce`) to ensure responsive, non-blocking audio cues for every table interaction.

---

## Subdirectories

- **[`haunted/`](haunted/README.md)**: 23 synthesized audio stingers, altar candle extinguishing sounds, bell tolls, and boss confrontation audio for Haunted Mode.

---

## Sound Effects Catalogue

| Sound Event Category | Audio Files (.ogg) | Game Trigger Context |
| :--- | :--- | :--- |
| **Card Slide** | `card-slide-1.ogg` through `card-slide-8.ogg` | Card dealing animations sliding from the shoe to player/dealer hands. |
| **Card Placement** | `card-place-1.ogg` through `card-place-4.ogg` | Card landing firmly on the baize felt table. |
| **Hole Card Reveal** | `card-shove-1.ogg` through `card-shove-4.ogg` | Dealer hole card peek or final face-up card reveal. |
| **Shoe Shuffle** | `card-shuffle.ogg`, `card-fan-1.ogg`, `card-fan-2.ogg` | Shoe reshuffle triggered upon reaching the ~25% cut-card penetration threshold. |
| **Deck Pack Handling** | `cards-pack-open-1.ogg`, `cards-pack-open-2.ogg`, `cards-pack-take-out-1.ogg`, `cards-pack-take-out-2.ogg` | Fresh shoe loading and new game initialization. |
| **Chip Handling & Clicks** | `chips-handle-1.ogg` through `chips-handle-6.ogg` | Hovering over or clicking bankroll chip piles in the bottom-right tray. |
| **Chip Placement** | `chip-lay-1.ogg`, `chip-lay-2.ogg`, `chip-lay-3.ogg` | Adding chip denominations to active betting spots on the table felt. |
| **Chip Collisions** | `chips-collide-1.ogg` through `chips-collide-4.ogg` | Multi-chip stacking and tactile clinking during rapid bet adjustments. |
| **Chip Stacks & Payouts** | `chips-stack-1.ogg` through `chips-stack-6.ogg` | Win payout slides, chip collection rakes, and all-in bet commitments. |

---

## Playback Engine & Invariants
- **16-Channel Polyphony**: `SoundManager` initializes 16 independent playback channels, allowing simultaneous chip clinks, card slides, and dialogue voice synthesis without cutting off active sounds.
- **Headless & CI Fail-Safe**: In test environments or systems without physical audio hardware, `SoundManager` detects `pygame.error` on initialization and degrades gracefully into a silent, non-throwing mock layer.
- **Controls & Volume**: Controlled in real time via keyboard shortcut `M` (master mute) and the Casino Settings dialog ([`ui_dialogs.py:SettingsDialog`](../ui_dialogs.py)).
- **Packaging**: Bundled into standalone distribution executables via `datas` tuples in [`blackjack.spec`](../blackjack.spec).

