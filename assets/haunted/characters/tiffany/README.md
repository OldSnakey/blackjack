# Tiffany Dealer Puppet Rig (`assets/haunted/characters/tiffany`)

## Overview
The `tiffany` directory houses the puppet layers for Tiffany (Tiffany 2.0), the vibrant, energetic VIP high-roller dealer.

## Character Profile
- **Identifier**: `tiffany`
- **Name**: Tiffany
- **Title**: *The VIP Hostess*
- **Unlock Status**: Default unlocked character.
- **Backdrop**: [`backdrop_casino.png`](../../backdrops/backdrop_casino.png) (Opulent casino velvet).
- **Acoustic Profile**: Bright, upbeat, energetic soprano Animalese voice (245 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Soft radial grounding shadow. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Elegant red velvet evening gown with gold embroidery. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Slender neck strata with gold pendant necklace. |
| **Head** | `head.png`, `head_2x.png` | 4 | Styled blonde updo with de-occluded facial apertures. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Animated expressive blue eyes with flutter-blink cadence. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 high-energy viseme apertures for upbeat speech delivery. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Graceful gloved arms for dealing and revealing cards. |
| **Bust** | `bust.png`, `bust_2x.png` | -- | Flattened reference composites. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematics and dynamic breathing cycles.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): High-pitch soprano voice synthesizer.
- [`tools/build_tiffany_puppet_assets.py`](../../../../tools/build_tiffany_puppet_assets.py): Asset generation pipeline script for Tiffany 2.0.

