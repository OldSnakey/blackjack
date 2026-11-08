# Stage Backdrops (`assets/haunted/backdrops`)

## Overview
The `backdrops` directory contains 7 curated 16-bit pixel-art panoramic stage backdrops that establish the atmospheric room environment on the upper horizon stage (`DealerStageCanvas`). Each backdrop is authored on a canonical **`500x110` crunchy logical pixel grid** (matching the `2x2` texel density of the `224x224` dealer puppets) and upscaled via `Image.Resampling.NEAREST` to:
- **1x Standard Resolution (`1000x220` px)**: `backdrop_<theme>.png` (matches `DealerStageCanvas.DEFAULT_HEIGHT = 220` with zero vertical stretching)
- **2x HiDPI Resolution (`2000x440` px)**: `backdrop_<theme>_2x.png`

All backdrops are 100% opaque RGB PNGs. High-resolution source masters reside in `assets/haunted/backdrops/masters/master_<theme>.jpg`.

---

## Backdrop Catalogue

| Environment | Files (1x / 2x) | Narrative Phase / Associated Dealer | 16-Bit Pixel-Art Scene |
| :--- | :--- | :--- | :--- |
| **Casino** | `backdrop_casino.png`, `backdrop_casino_2x.png` | `Phase.NORMAL` (Julian, Tiffany) | Monte Carlo Grand Salon with carved mahogany wainscoting, emerald/gold damask panels, crystal wall sconces, and scalloped velvet drapery. |
| **Creep** | `backdrop_creep.png`, `backdrop_creep_2x.png` | `Phase.CREEP`, `Phase.OMEN`, `Phase.SNUFFING` | Twilight reality-warp salon with peeling green wallpaper, exposed damp bricks, crooked gilt picture frames, cobwebs, and flickering amber/violet sconces. |
| **Crypt** | `backdrop_crypt.png`, `backdrop_crypt_2x.png` | Mortimer & Count Vladimir | Gothic Vampire Castle & Moonlit Ossuary with pointed lancet windows, glowing full moons, gargoyle/skull corbels, candelabras, and crimson bat banners. |
| **Hell** | `backdrop_hell.png`, `backdrop_hell_2x.png` | `Phase.HELL_TABLE` (Malphas / The Pit Fiend) | Infernal Brimstone Citadel with carved obsidian pillars, molten lava waterfalls, hanging chains, and a demon throne room arch. |
| **Celestial** | `backdrop_celestial.png`, `backdrop_celestial_2x.png` | Exorcism Victory & Default (Archangel Uriel) | Seraphic Marble Sanctuary with fluted ivory/gold columns, sapphire/cyan/gold stained-glass lancet windows, crepuscular light rays, and golden clouds. |
| **Cyber** | `backdrop_cyber.png`, `backdrop_cyber_2x.png` | Selene (Cyber Dealer) | Neo-Tokyo Synthwave VIP Lounge with brushed-titanium central cyber-arch, glowing circuit columns, and rain-streaked windows overlooking a neon city skyline. |
| **Academy** | `backdrop_academy.png`, `backdrop_academy_2x.png` | Professor Edward (MIT Bootcamp & Table) | Ivy-League Card-Counting Seminar Library with floor-to-ceiling mahogany bookshelves, Hi-Lo probability & bell-curve slate chalkboards, and green banker's lamps. |

---

## Architectural Role & Rendering Rules
- **Decoupled Horizon Stage**: The backdrops span the full width of `dealer_stage_canvas` behind the dealer puppet. They remain strictly above the 3D mahogany horizon rail and are never obscured by table felt props.
- **Locked `2x2` Crunchy Texel Density**: Built from `500x110` quantized pixel grids upscaled `2x` (`1000x220`) and `4x` (`2000x440`) with `NEAREST` neighbor resampling so background pixels match the dealer puppet's `2x2` pixel size.
- **Generation Script**: Built via [`tools/build_stage_backdrops.py`](../../../tools/build_stage_backdrops.py).

## Runtime Collaborators
- [`ui_canvases.py:DealerStageCanvas`](../../../ui_canvases.py): Renders the active backdrop and manages ambient particles and the top-right wardrobe coat-hanger button (`assets/haunted/hanger_icon.png`).
- [`haunted_manager.py`](../../../haunted_manager.py) & [`blackjack.py`](../../../blackjack.py): Drive narrative phase and dealer profile transitions that swap the active backdrop.
