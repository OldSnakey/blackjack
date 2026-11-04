# Dummy Dealer Puppet Rig (`assets/haunted/characters/dummy`)

## Overview
The `dummy` asset directory provides a high-contrast test mannequin puppet used for automated kinematic verification, headless GUI tests, and visual calibration of the multi-layer dealer compositing engine.

## Character Profile
- **Identifier**: `dummy`
- **Name**: The Test Dummy
- **Title**: *Diagnostic Automaton*
- **Unlock Status**: Test & Debug mode default (unlocked).
- **Acoustic Profile**: Low-resonance diagnostic tone (110 Hz base pitch).

## Asset Specification
All assets are RGBA 32-bit PNGs provided at both 1x (`112x112` px) and 2x (`224x224` px) native resolutions:

| Layer Category | Files (1x / 2x) | Z-Order | Function & Animation Dynamics |
| :--- | :--- | :---: | :--- |
| **Grounding Shadow** | `shadow.png`, `shadow_2x.png` | 1 | Ambient soft ground contact shadow anchoring the dealer to the horizon rail. |
| **Torso & Outfit** | `torso.png`, `torso_2x.png` | 2 | High-contrast calibration garment; anchors idle breathing vertical displacement ($Y \pm 1.5\,\text{px}$). |
| **Neck** | `neck.png`, `neck_2x.png` | 3 | Anatomical bridge between torso and head. |
| **Mannequin Head** | `head.png`, `head_2x.png` | 4 | De-occluded base faceplate with blank eye sockets and mouth aperture. |
| **Eyes (Blink Cadence)** | `eyes_open.png`, `eyes_half.png`, `eyes_closed.png` (+ `*_2x.png`) | 5 | 3-frame procedural blinking sequence triggered at randomized 3.5–5.5s intervals. |
| **Mouth (Visemes)** | `mouth_neutral.png`, `mouth_talk.png`, `mouth_smirk.png`, `mouth_gasp.png`, `mouth_a.png`, `mouth_o.png`, `mouth_e.png`, `mouth_f.png` (+ `*_2x.png`) | 6 | 8 phonetic lip-sync apertures synchronized 1:1 with `AnimaleseVoiceEngine` speech audio. |
| **Articulated Arms** | `arm_rest.png`, `arm_deal.png`, `arm_peek.png` (+ `*_2x.png`) | 7 | Dynamic dealer arm poses: resting idle, card deal gesture, and hole-card peek. |
| **Composite Fallback** | `bust.png`, `bust_2x.png` | -- | Flattened static composite image for legacy fallback rendering. |

## Runtime Collaborators
- [`dealer_actor.py`](../../../../dealer_actor.py): Kinematic compositor managing layer positions, breathing offsets, and gesture transitions.
- [`dialogue_voice_engine.py`](../../../../dialogue_voice_engine.py): Drives mouth viseme switches during typewriter dialogue streaming.
- [`tools/build_dummy_puppet_assets.py`](../../../../tools/build_dummy_puppet_assets.py): Offline procedural generator script for dummy layers.

