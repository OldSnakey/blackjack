# Selene Dealer Puppet Rig (`assets/haunted/characters/selene`)

## Overview
The `selene` directory provides the discrete puppet strata for Selene, a high-roller cyberpunk croupier with cybernetic neural implants and holographic HUD accents.

## Character Profile
- **Identifier**: `selene`
- **Name**: Selene
- **Title**: *The Neon Croupier*
- **Unlock Status**: Achievement unlock (`apprentice_counter` - complete a 5-drill Card Counting quiz streak).
- **Backdrop**: [`backdrop_casino.png`](../../backdrops/backdrop_casino.png) / Custom Neon Casino backdrop.
- **Acoustic Profile**: Crisp, synthetic, digitized alto voice with light ring modulation (210 Hz fundamental frequency $F_0$).

## Layer Hierarchy (1x: 112x112 px | 2x: 224x224 px)

| Layer | Files (1x / 2x) | Z-Order | Function & Description |
| :--- | :--- | :---: | :--- |
| **Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Crisp contact shadow with faint cyan neon edge bleed. |
| **Torso** | `torso.png`, `torso_2x.png` | 2 | Asymmetrical cyberpunk cyber-suit with luminescent circuitry lines. |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | High-collar neural connector neck strata. |
| **Head** | `head.png`, `head_2x.png` | 4 | Cybernetic temple implants, asymmetric neon bob haircut, and facial plate. |
| **Eyes** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | Cyan holographic ocular optics with blinking and HUD telemetry flicker. |
| **Mouth** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 precision cyber-viseme apertures for synthesized dialogue. |
| **Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Augmented cyber-arms with illuminated fingertips for card manipulation. |
| **Bust** | `bust.png`, `bust_2x.png`, `orig_bust_2x.png` | -- | Flat composite portraits and source asset. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor for Selene.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Digital synthesizer voice engine.
- [`card_counter.py`](../../../../card_counter.py) & [`save_manager.py`](../../../../save_manager.py): Evaluates counting quiz streaks to unlock Selene.

