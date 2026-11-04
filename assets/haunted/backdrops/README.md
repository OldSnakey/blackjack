# Stage Backdrops (`assets/haunted/backdrops`)

## Overview
The `backdrops` directory contains 5 curated panoramic stage backdrops that establish the atmospheric room environment on the upper horizon stage (`DealerStageCanvas`). Each backdrop is provided in both 1x standard resolution (`1000x140` px) and 2x HiDPI resolution (`2000x280` px) as 100% opaque RGB PNGs.

---

## Backdrop Catalogue

| Environment | Files (1x / 2x) | Narrative Phase / Associated Dealer | Visual Aesthetic |
| :--- | :--- | :--- | :--- |
| **Casino** | `backdrop_casino.png`, `backdrop_casino_2x.png` | `Phase.NORMAL` (Julian, Tiffany, Selene) | Opulent classic casino with green velvet wallpaper, antique gold mouldings, and warm wall sconces. |
| **Crypt** | `backdrop_crypt.png`, `backdrop_crypt_2x.png` | `Phase.CREEP` (Malphas, Vladimir) | Gothic stone masonry with arched wall niches and dim cold torchlight. |
| **Creep** | `backdrop_creep.png`, `backdrop_creep_2x.png` | `Phase.OMEN` & `Phase.SNUFFING` (Mortimer) | Decaying subterranean cellar with green mold, peeling plaster, and flickering candles. |
| **Hell** | `backdrop_hell.png`, `backdrop_hell_2x.png` | `Phase.HELL_TABLE` (The Pit Fiend) | Blazing obsidian cavern, volcanic fissures, and brimstone glow framing the demon showdown. |
| **Celestial** | `backdrop_celestial.png`, `backdrop_celestial_2x.png` | Exorcism Victory (Archangel Uriel) | Luminous ivory and gold marble cathedral with divine seraphic light beams. |

---

## Architectural Role & Rendering Rules
- **Decoupled Horizon Stage**: The backdrops span the full width of `dealer_stage_canvas` behind the dealer puppet. They remain strictly above the 3D mahogany horizon rail and are never obscured by table felt props.
- **Dynamic Sconce Lighting**: `DealerStageCanvas` overlays synchronized procedural sconce halos ($r = 18\,\text{px}$) with randomized flicker timers on top of the backdrop.
- **Generation Script**: Produced procedurally via [`tools/build_stage_backdrops.py`](../../../tools/build_stage_backdrops.py).

## Runtime Collaborators
- [`ui_canvases.py:DealerStageCanvas`](../../../ui_canvases.py): Renders the active backdrop and manages sconce lighting.
- [`haunted_manager.py`](../../../haunted_manager.py): Drives narrative phase transitions that swap the active backdrop.

