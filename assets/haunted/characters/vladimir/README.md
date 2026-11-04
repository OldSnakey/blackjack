# Count Vladimir Dealer Puppet Rig (`assets/haunted/characters/vladimir`)

## Overview
The `vladimir` directory stores the puppet layers for Count Vladimir, an aristocratic vampire dealer and high-roller persona from the Crimson Nocturne.

## Character Profile
- **Identifier**: `vladimir`
- **Name**: Count Vladimir
- **Title**: *The Crimson Noble*
- **Unlock Status**: Achievement unlock (`master_counter` - complete a 10-drill Card Counting quiz streak).
- **Backdrop**: [`backdrop_crypt.png`](../../backdrops/backdrop_crypt.png) / Crimson Castle backdrop.
- **Acoustic Profile**: Aristocratic, velvety, dramatic theatrical baritone with slight reverb (120 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Deep obsidian contact shadow with sharp edges. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Victorian aristocratic doublet with high-standing crimson-lined cape collar. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Pale alabaster neck strata with crimson ruby medallion. |
| **Head** | `head.png`, `head_2x.png` | 4 | Sleek ebony widow's-peak hairstyle with aristocratic facial plate. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Piercing crimson vampire eyes with haughty, deliberate blink cadence. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 fanged aristocratic viseme apertures for elegant dialogue. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Black velvet-sleeved arms with sharp alabaster hands for card handling. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Flat composite portraits and source asset. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor for Count Vladimir.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Velvety aristocratic voice synthesis.
- [`card_counter.py`](../../../../card_counter.py) & [`save_manager.py`](../../../../save_manager.py): Evaluates 10-quiz counting master streak for character unlock.

