# Mortimer Dealer Puppet Rig (`assets/haunted/characters/mortimer`)

## Overview
The `mortimer` directory stores the 19-layer discrete puppet strata for Mortimer, a solemn plague doctor dealer embodying the decaying atmosphere of the Haunted Mode `CREEP` and `OMEN` phases.

## Character Profile
- **Identifier**: `mortimer`
- **Name**: Mortimer
- **Title**: *The Plague Physician*
- **Unlock Status**: Default unlocked character.
- **Backdrop**: [`backdrop_creep.png`](../../backdrops/backdrop_creep.png) (Decaying green cellar walls with dripping slime).
- **Acoustic Profile**: Hollow, raspy, echoing nasal voice (105 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Ambient soft ground shadow. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Black leather trench coat with physician cowl and belt buckles. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Heavy dark cowl cowl-neck layer. |
| **Head** | `head.png`, `head_2x.png` | 4 | Wide-brimmed physician hat and curved avian plague doctor mask. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Dark glass-goggle lenses with procedural glint and blink shading. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | Beak-tip acoustic vent visemes for raspy dialogue. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Heavy leather-gloved arms: table rest, card pitch, and hole-card peek. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Flat composite portraits and source asset. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor rendering Mortimer's respiratory cycle.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Synthesizes muffled beak vocalizations.
- [`dealer_wardrobe_dialog.py`](../../../../dealer_wardrobe_dialog.py): Wardrobe preview and selection.

