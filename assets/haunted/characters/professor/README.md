# Professor Edward Dealer Puppet Rig (`assets/haunted/characters/professor`)

## Overview
The `professor` directory provides the discrete 19-layer puppet strata for Professor Edward, a distinguished academic card-counting mentor and probability theorist inspired by Edward O. Thorp and the MIT Blackjack Team.

## Character Profile
- **Identifier**: `professor`
- **Name**: Professor Edward
- **Title**: *🎓 The MIT Card Professor*
- **Unlock Status**: Default stage dealer in Training Mode (Counting Bootcamp & 3-Seat Strategy/Counting Trainer Free Play); permanently unlocked for all casino modes upon graduating Counting Bootcamp (passing Stage `C5`).
- **Backdrop**: [`backdrop_academy.png`](../../backdrops/backdrop_academy.png) / MIT Seminar room with slate chalkboard probability formulas, mahogany shelving, and brass banker's lamps.
- **Acoustic Profile**: Warm, articulate academic baritone voice (`classic_baritone` timbre, 160 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Soft ambient contact shadow beneath the torso. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Charcoal-brown herringbone tweed jacket, emerald-green waistcoat, brass pocket-watch chain, and crimson silk bow tie. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Starched white dress shirt collar and neck strata. |
| **Head** | `head.png`, `head_2x.png` | 4 | Silver-streaked professorial hair, neatly trimmed beard, brass wire-rimmed spectacles frame, and de-occluded facial plate. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Keen analytical eyes behind wire-rimmed lenses with curved upper lash arches for blinking. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 contoured pixel-art lip viseme overlays for real-time pedagogical lip-sync. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Tweed jacket sleeves with leather elbow patches and compact 2.5D pixel-art cards for dealing and hole-card peeks. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Crunchy 2.5D pixel-art composite portraits and source asset. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor and pedagogical dialogue tables for Professor Edward.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Academic baritone voice synthesis profile.
- [`counting_bootcamp.py`](../../../../counting_bootcamp.py) & [`save_manager.py`](../../../../save_manager.py): Manages Training Mode default equip and Stage `C5` graduation unlock.

