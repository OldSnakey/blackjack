# Playing Card Deck Assets (`cards`)

## Overview
The `cards` directory houses the complete 55-card visual deck asset catalogue powering table deals, dealer hands, and card shoe management in the Blackjack application.

---

## Asset Catalogue

| Asset Group | Filename Pattern | Count | Description |
| :--- | :--- | :---: | :--- |
| **Clubs (♣)** | `1_club.png` .. `10_club.png`, `jack_club.png`, `queen_club.png`, `king_club.png` | 13 | Complete Clubs suit with traditional black serif ranks and pips (`1` = Ace). |
| **Diamonds (♦)** | `1_diamond.png` .. `10_diamond.png`, `jack_diamond.png`, `queen_diamond.png`, `king_diamond.png` | 13 | Complete Diamonds suit with classic crimson ranks and pips. |
| **Hearts (♥)** | `1_heart.png` .. `10_heart.png`, `jack_heart.png`, `queen_heart.png`, `king_heart.png` | 13 | Complete Hearts suit with classic crimson ranks and pips. |
| **Spades (♠)** | `1_spade.png` .. `10_spade.png`, `jack_spade.png`, `queen_spade.png`, `king_spade.png` | 13 | Complete Spades suit with traditional black serif ranks and pips. |
| **Hole Card Back** | `back.png` | 1 | Authentic blue geometric crosshatch damask design for face-down dealer hole cards and deck stacks. |
| **Jokers** | `black_joker.png`, `red_joker.png` | 2 | Traditional illustrated court jokers (reserved for variants/extensions). |

---

## Visual Dimensions & Scaling Rules
- **Base Asset Dimensions**: Native resolution is standardized at $74 \times 107\,\text{px}$.
- **Felt Table Resampling**: On the table felt canvas, [`audio_assets.py:AssetScaler`](../audio_assets.py) dynamically scales cards by $1.5\times$ to $111 \times 160\,\text{px}$ using high-quality PIL Lanczos interpolation.
- **Visual Deck Harmony**: Any custom cards (such as the supernatural 13 of Skulls in [`assets/haunted/card_13.png`](../assets/haunted/card_13.png)) match this exact dimension, corner rank typography, and serif border weight.

## Domain Model & Runtime Integration
- **`Card` Named Tuple** ([`rules.py`](../rules.py)): Encapsulates rank string, suit string, numeric Blackjack value ($1\text{--}10$), image key, and Hi-Lo count tag value ($+1, 0, -1$).
- **4-Deck Shoe** ([`rules.py:build_shoe`](../rules.py)): Compiles 208 cards with persistent depletion and an authentic ~25% cut-card penetration reshuffle trigger.
- **Hole Card Privacy**: The dealer's downcard (`back.png`) remains unrevealed and excluded from score totals and card counting running counts until the dealer's turn.

## Asset Protection
> [!IMPORTANT]
> Files in this directory are **Protected Binary Assets** per [`AGENTS.md`](../AGENTS.md). Automated refactors or script migrations must never alter or overwrite these original card textures.

