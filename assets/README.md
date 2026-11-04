# Application Assets (`assets`)

## Overview
The `assets` directory houses all visual media, bundled typography, branding artwork, and declarative UI configuration powering the Blackjack desktop application.

---

## Subdirectories

Detailed specifications for sub-components reside in their dedicated documentation:

- **[`fonts/`](fonts/README.md)**: Bundled TrueType pixel fonts (`m6x11plus.ttf`, `m5x7.ttf`, `Mini3x5.ttf`, etc.) dynamically registered into Windows GDI via `pixel_ui.py`.
- **[`haunted/`](haunted/README.md)**: Supernatural expansion assets, 19-layer discrete puppet strata for all 8 dealers, and 5 panoramic room backdrops.
- **[`overlay_icons/`](overlay_icons/README.md)**: 29 curated Kenney input prompt sprites (64x64 PNG) for the in-game shortcuts modal HUD.
- **[`screenshots/`](screenshots/README.md)**: 5 high-resolution gameplay captures for itch.io storefront publishing.

---

## Direct Directory Assets

### 1. Game Branding & Executable Icons
- `icon.ico` / `icon.png`: Multi-resolution Windows executable icon and Tkinter window titlebar brand icon.
- `cover_itch.png`: Optimized 630x500 2.5D pixel graphics storefront cover on diamond felt for itch.io.
- `pixel_logo_blackjack.png`: 1x resolution (468x84 px) retro pixel art game logo with playing card suit emblems.
- `pixel_logo_blackjack_2x.png`: 2x HiDPI resolution (936x168 px) pixel logo rendered from [`tools/build_pixel_logo.py`](../tools/build_pixel_logo.py).

### 2. Declarative Layout Configuration
- **`ui_config.json`**: Centralized JSON specification loaded by [`ui_layout.py`](../ui_layout.py). Defines exact pixel coordinates for:
  - Table felt boundaries and horizon stage geometry.
  - 3-Seat Wagering origins (Seat 3 at $X=235, Y=285$; Seat 2 at $X=490, Y=298$; Seat 1 at $X=745, Y=285$).
  - Card deal anchors and horizontal side bet flanking offsets ($X \pm 82\,\text{px}$).
  - Bottom mahogany rail dock button paddings and widget grid configurations.

## Distribution & Build Integration
- Bundled into standalone distribution executables via `datas` tuples in [`blackjack.spec`](../blackjack.spec).
- Protected binary assets: Original artwork in this tree must not be overwritten or corrupted by automated code refactors.

