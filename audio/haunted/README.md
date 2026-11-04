# Haunted & Supernatural Audio (`audio/haunted`)

## Overview
The `haunted` audio directory houses 23 tactile sound effect files (.ogg / .wav) that provide atmospheric audio cues, supernatural transition stingers, demon confrontation effects, and character speech accents during Haunted Mode.

---

## Audio Asset Catalogue

| Category | Files (.ogg / .wav) | Trigger Event & In-Game Context |
| :--- | :--- | :--- |
| **Altar Mechanics** | `candle_snuff.ogg`, `candle_snuff.wav` | Extinguishing of an altar candle following a player bust or loss. |
| **Gravestone Rising** | `stone_scrape.ogg`, `stone_scrape.wav` | 2.5D gravestone rises from the table felt as candles extinguish. |
| **Omen & Atmosphere** | `clock_chime_13.ogg`, `clock_chime_13.wav` | Striking of the cursed clock when Card 13 appears or OMEN phase triggers. |
| **Tension & Pulse** | `heartbeat.ogg`, `heartbeat.wav` | Low-frequency rhythmic heartbeat during SNUFFING phase and Soul Meter struggle. |
| **Hell's Descent** | `hell_bell.ogg`, `hell_bell.wav` | Resonant abyssal bell toll marking transition to `Phase.HELL_TABLE`. |
| **Demon Showdown** | `demon_reveal.ogg`, `demon_reveal.wav` | Dramatic sting when The Pit Fiend manifests on stage. |
| **Demon Taunts** | `demon_laugh.ogg`, `demon_laugh.wav` | Dark sinister laugh when player loses a hand in Hell's Table. |
| **Exorcism Victory** | `banish.ogg`, `banish.wav` | Explosive sonic shockwave when The Pit Fiend's soul meter drops to 0%. |
| **Celestial Grace** | `angel_chime.ogg`, `angel_chime.wav` | Radiant angelic chime played when Archangel Uriel appears or blessings activate. |
| **Character Accents** | `dealer_julian.ogg`, `dealer_malphas.ogg`, `dealer_mortimer.ogg`, `dealer_tiffany.ogg`, `dealer_uriel.ogg` | Voice entry accents and greeting stingers for dealer personas. |

---

## Format & Synthesis Invariants
- **Encoding**: 1-channel mono 16-bit PCM WAV / OGG Vorbis encoded at 44,100 Hz.
- **Synthesizers**: Generated procedurally via [`tools/build_haunted_assets.py`](../../tools/build_haunted_assets.py) and [`tools/build_character_roster_assets.py`](../../tools/build_character_roster_assets.py).
- **Runtime Playback**: Loaded and triggered asynchronously via [`haunted_manager.py`](../../haunted_manager.py) and [`audio_assets.py:SoundManager`](../../audio_assets.py).

