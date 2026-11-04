# Julian Dealer Puppet Rig (`assets/haunted/characters/julian`)

## Overview
The `julian` asset directory contains the complete 19-layer discrete puppet strata for Julian, the classic casino croupier and primary default dealer of the application.

## Character Profile
- **Identifier**: `julian`
- **Name**: Julian
- **Title**: *The House Croupier*
- **Unlock Status**: Default unlocked character.
- **Backdrop**: [`backdrop_casino.png`](../../backdrops/backdrop_casino.png) (Opulent classic casino velvet wallpaper).
- **Acoustic Profile**: Warm, courteous mid-baritone Animalese voice (135 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Soft semi-transparent radial contact shadow. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Black formal casino tuxedo with emerald bowtie and crisp white shirt. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Collarbone and neck bridge layer. |
| **Head** | `head.png`, `head_2x.png` | 4 | De-occluded mannequin headplate with slicked hair, ears, and blank apertures. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Focused croupier gaze with natural procedural blinking cadence. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 phonetic viseme sprites mapped to English vowels/consonants. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Articulated tuxedo sleeves: table rest, card pitch/deal, and downcard peek. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Reference composites and source high-resolution portrait. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor rendering Julian on `DealerStageCanvas`.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Synthesizes Julian's voice chirps during dialogue playback.
- [`dealer_wardrobe_dialog.py`](../../../../dealer_wardrobe_dialog.py): Wardrobe selector for equipping Julian.

