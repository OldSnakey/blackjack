# Haunted Mode & Supernatural Assets (`assets/haunted`)

## Overview
The `haunted` directory contains all visual assets supporting the slow-burn supernatural narrative expansion of Blackjack, culminating in the showdown against The Pit Fiend at Hell's Table and divine exorcism with Archangel Uriel.

---

## Subdirectories

Detailed specifications for layered character rigs and panoramic stage backdrops reside in their respective child documentation:

- **[`characters/`](characters/README.md)**: 19-layer discrete puppet strata for all 8 dealer personalities (breathing, blinking, visemes, arms).
- **[`backdrops/`](backdrops/README.md)**: 5 panoramic 1x/2x room backdrops (*Casino*, *Crypt*, *Creep*, *Hell*, *Celestial*).

---

## Direct Directory Assets

### 1. Table Altar Accessories
Rendered on the table felt within `HauntedAltarCanvas` (`ui_canvases.py`):
- `candle_lit.png` / `candle_unlit.png`: Tabletop altar candles extinguished one-by-one as the player loses hands or busts.
- `gravestone.png`: 2.5D stone gravestones rising from the green felt as candles snuff out.

### 2. Cursed Playing Cards
- `card_13.png`: The authentic **13 of Skulls** cursed card, featuring authentic host deck geometry (`74x107` px), corner rank typography, and 13 skull pips. Triggers immediate deal busts and starts the slow-burn supernatural transition.
- `back_haunted.png`: Crimson-tinted damask back design for cursed deck shoes.

### 3. Celestial Blessing Relics
Badges drafted during Hell's Table Soul Meter milestones (`50%` and `75%`) via `AngelicDraftDialog`:
- `relic_seraph.png`: *Seraph's Grace* (protects against player bust by redrawing once).
- `relic_eye.png`: *Eye of Providence* (peeks dealer downcard).
- `relic_smite.png`: *Archangel's Smite* (instantly advances Soul Meter).
- `relic_shield.png`: *Cherub's Shield* (absorbs dealer blackjack damage).
- `relic_tithe.png`: *Heavenly Tithe* (doubles natural blackjack payout).
- `relic_miracle.png`: *Miracle Draw* (enables hotkey `X` card banishment).
- `relic_streak.png`: *Hallowed Run* (bonus score momentum per consecutive win).

### 4. Stage & Interface Props
- `hanger_icon.png`, `hanger_icon_2x.png`: Wardrobe dressing room icon on the horizon stage canvas.
- `angel_avatar.png`: Dialogue portrait for celestial narrative events.
- `dealer_classic.png`, `dealer_creep.png`, `dealer_demon_0.png`, `dealer_demon_1.png`: Legacy demon sprites preserved for reference.

## Runtime Collaborators
- [`haunted_manager.py`](../../haunted_manager.py): State engine driving narrative progression and relic powers.
- [`ui_canvases.py`](../../ui_canvases.py): Hosts `HauntedAltarCanvas` and `SoulMeterCanvas`.
- [`tools/build_haunted_assets.py`](../../tools/build_haunted_assets.py): Generator script for procedural candles, gravestones, and cursed cards.

