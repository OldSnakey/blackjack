# Uriel Dealer Puppet Rig (`assets/haunted/characters/uriel`)

## Overview
The `uriel` directory contains the puppet strata for Uriel, an angelic celestial croupier representing divine redemption in the aftermath of the Hell's Table Exorcism.

## Character Profile
- **Identifier**: `uriel`
- **Name**: Archangel Uriel
- **Title**: *The Seraph Croupier*
- **Unlock Status**: Default unlocked character (also presides during Celestial Victory).
- **Backdrop**: [`backdrop_celestial.png`](../../backdrops/backdrop_celestial.png) (Radiant ivory-and-gold marble cathedral).
- **Acoustic Profile**: Resonant, serene, bell-like tenor voice with celestial harmonic overtones (180 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Soft golden-ambient ground contact shadow. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Immaculate white and gold ceremonial vestments with seraphic wing roots. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Luminous golden collar and neck bridge. |
| **Head** | `head.png`, `head_2x.png` | 4 | Halo-adorned celestial headplate with golden curls and faceplate. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Serene golden celestial gaze with peaceful blink cycle. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 resonant viseme apertures for soothing divine dialogue. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Pure white silk-sleeved arms for dignified card delivery. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Flat composite portraits and source asset. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor for Uriel.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Harmonics-rich celestial voice synthesis.
- [`haunted_manager.py`](../../../../haunted_manager.py): Deploys Uriel upon banishing The Pit Fiend.

