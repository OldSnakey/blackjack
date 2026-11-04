# Malphas Dealer Puppet Rig (`assets/haunted/characters/malphas`)

## Overview
The `malphas` directory houses the puppet layers for Malphas, an ominous gothic gargoyle dealer who manifests during the supernatural transition phases of Haunted Mode.

## Character Profile
- **Identifier**: `malphas`
- **Name**: Malphas
- **Title**: *The Gargoyle Watcher*
- **Unlock Status**: Default unlocked character.
- **Backdrop**: [`backdrop_crypt.png`](../../backdrops/backdrop_crypt.png) (Gothic crypt masonry and arched niches).
- **Acoustic Profile**: Deep, grating guttural bass voice (85 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Heavy ground contact shadow anchoring stone physique. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Weathered stone gargoyle torso with bat-wing contours. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Chiseled obsidian/granite neck strata. |
| **Head** | `head.png`, `head_2x.png` | 4 | Horned gargoyle headplate with de-occluded facial apertures. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Glowing amber stone eyes with heavy lid animations. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 stone-jaw viseme apertures for guttural speech synthesis. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Clawed granite arms for idle rest, dealing cards, and peeking hole cards. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Flat composite portraits and high-res source asset. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Rigging and procedural idle animation.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Guttural sound synthesizer.
- [`haunted_manager.py`](../../../../haunted_manager.py): Narrative phase manager triggering Malphas during supernatural escalation.

