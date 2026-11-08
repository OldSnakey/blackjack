# Dealer Puppet Characters Roster (`assets/haunted/characters`)

## Overview
The `characters` directory houses the modular 19-layer discrete puppet strata for all 9 dealers in the Blackjack application. Each character features standardized layer decomposition, enabling real-time procedural idle breathing, eye blinking, 8-viseme phonetic lip-sync, and dynamic arm poses across both standard (1x) and HiDPI (2x) resolutions.

---

## Dealer Roster & Character Directories

Detailed layer specifications, acoustic parameters, and animation notes are documented within each character's dedicated directory:

| Character | Title & Persona | Unlock Requirement | Acoustic Profile | Documentation Link |
| :--- | :--- | :--- | :--- | :--- |
| **Julian** | *The Classic Croupier* | Default Unlocked | Classic Baritone (180 Hz) | [`julian/README.md`](julian/README.md) |
| **Tiffany** | *♥ The Velvet Croupier* | Default Unlocked | Warm Flute (380 Hz) | [`tiffany/README.md`](tiffany/README.md) |
| **Malphas** | *☠ The Pit Fiend* | Encounter Hell's Table | Guttural Brimstone (85 Hz) | [`malphas/README.md`](malphas/README.md) |
| **Uriel** | *✨ Celestial Seraph* | Defeat Hell's Table (`exorcist`) | Angelic Crystal (520 Hz) | [`uriel/README.md`](uriel/README.md) |
| **Mortimer** | *🎩 Grim Bones* | Survive Card 13 / \$5,000 Bankroll | Crypt Hollow (240 Hz) | [`mortimer/README.md`](mortimer/README.md) |
| **Dummy** | *🧪 Test Puppet Dummy* | Default Unlocked | Synthetic Square (300 Hz) | [`dummy/README.md`](dummy/README.md) |
| **Selene** | *⚡ Cyber Croupier* | 5-Quiz Streak (`apprentice_counter`) | Cyber Synth (440 Hz) | [`selene/README.md`](selene/README.md) |
| **Vladimir** | *🩸 Crimson Nocturne* | 20-Quiz Streak (`master_counter`) | Crimson Velvet (140 Hz) | [`vladimir/README.md`](vladimir/README.md) |
| **Professor Edward** | *🎓 The MIT Card Professor* | Default in Training Mode; Graduate Bootcamp (`C5`) for All Modes | Academic Baritone (160 Hz) | [`professor/README.md`](professor/README.md) |

---

## Puppet Strata Architecture
Every character folder implements an identical 7-tier Z-order layer schema:

```
Z-7: Arms        -> arm_rest.png, arm_deal.png, arm_peek.png (pose dispatch)
Z-6: Mouth       -> 8 phonetic visemes (neutral, talk, smirk, gasp, a, o, e, f)
Z-5: Eyes        -> eyes_open.png, eyes_half.png, eyes_closed.png (blinking)
Z-4: Head        -> head.png (de-occluded faceplate with blank eye/mouth apertures)
Z-3: Neck        -> neck.png (collarbone connection layer)
Z-2: Torso       -> torso.png (garment body subjected to vertical sine breathing)
Z-1: Shadow      -> shadow.png (soft ambient grounding contact shadow)
```

## Runtime Collaborators
- [`dealer_actor.py`](../../../dealer_actor.py): The primary puppet compositor that renders the layers on the horizon stage.
- [`dialogue_voice_engine.py`](../../../dialogue_voice_engine.py): Synthesizes Animalese audio and synchronizes visemes.
- [`dealer_wardrobe_dialog.py`](../../../dealer_wardrobe_dialog.py): Wardrobe customizer for previewing and equipping dealer personas.
- [`tools/deocclude_dealer_faceplates.py`](../../../tools/deocclude_dealer_faceplates.py): Pipeline tool that de-occluded mannequin plates and extracted puppet layers.

