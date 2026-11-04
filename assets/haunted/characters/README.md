# Dealer Puppet Characters Roster (`assets/haunted/characters`)

## Overview
The `characters` directory houses the modular 19-layer discrete puppet strata for all 8 dealers in the Blackjack application. Each character features standardized layer decomposition, enabling real-time procedural idle breathing, eye blinking, 8-viseme phonetic lip-sync, and dynamic arm poses across both standard (1x) and HiDPI (2x) resolutions.

---

## Dealer Roster & Character Directories

Detailed layer specifications, acoustic parameters, and animation notes are documented within each character's dedicated directory:

| Character | Title & Persona | Unlock Requirement | Acoustic Profile | Documentation Link |
| :--- | :--- | :--- | :--- | :--- |
| **Julian** | *The House Croupier* | Default Unlocked | Warm Baritone (135 Hz) | [`julian/README.md`](julian/README.md) |
| **Tiffany** | *The VIP Hostess* | Default Unlocked | Upbeat Soprano (245 Hz) | [`tiffany/README.md`](tiffany/README.md) |
| **Malphas** | *The Gargoyle Watcher* | Default Unlocked | Guttural Bass (85 Hz) | [`malphas/README.md`](malphas/README.md) |
| **Uriel** | *The Seraph Croupier* | Default Unlocked (Exorcism) | Celestial Tenor (180 Hz) | [`uriel/README.md`](uriel/README.md) |
| **Mortimer** | *The Plague Physician* | Default Unlocked | Raspy Nasal (105 Hz) | [`mortimer/README.md`](mortimer/README.md) |
| **Dummy** | *Diagnostic Automaton* | Test / Debug Mode | Flat Diagnostic (110 Hz) | [`dummy/README.md`](dummy/README.md) |
| **Selene** | *The Neon Croupier* | 5-Quiz Streak (`apprentice_counter`) | Cybernetic Alto (210 Hz) | [`selene/README.md`](selene/README.md) |
| **Vladimir** | *The Crimson Noble* | 10-Quiz Streak (`master_counter`) | Aristocratic Baritone (120 Hz) | [`vladimir/README.md`](vladimir/README.md) |

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

