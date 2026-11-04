# Bundled UI Pixel Fonts (`assets/fonts`)

## Overview
The `fonts` directory contains bundled TrueType (`.ttf`) pixel fonts that supply the authentic retro 1990s arcade casino typography across all UI buttons, plaques, dialogues, chips, and overlays. These fonts are loaded dynamically into the Windows GDI font table at runtime without requiring system installation.

---

## Font Catalogue & Semantic Roles

| Font File | Typography Characteristics | Semantic Role in `font_config.json` | Used By |
| :--- | :--- | :--- | :--- |
| **`m6x11plus.ttf`** | High-legibility 6x11 proportional pixel typeface with enhanced punctuation and spacing | `help_title` (16pt), `help_action` (12pt), `button_large` (13pt), `heading` | [`ShortcutsDialog`](../../ui_dialogs.py), [`CanvasPixelButton`](../../pixel_ui.py) |
| **`m6x11.ttf`** | Standard 6x11 proportional pixel font | `title_medium` (14pt), `button` (11pt) | General UI controls and button labels |
| **`m5x7.ttf`** | Compact 5x7 dense pixel font | `body` (10pt), `help_key` (11pt), `telemetry` | Settings dialog descriptions, Hall of Fame telemetry, dialogue bubbles |
| **`Mini3x5.ttf`** | 3x5 micro font | `chip_micro` (7pt) | Smallest chip denomination labels (\$5, \$25) |
| **`Volt5x5.ttf`** | 5x5 crisp square pixel font | `chip_label` (9pt), `plaque_score` | Chip face markings and score plaque headers |
| **`Covenant5x5.ttf`** | 5x5 condensed pixel font | `badge_label` (8pt) | Floating count badges (`+1`, `-1`, `0`) |
| **`Round9x13.ttf`** | 9x13 rounded display font | `headline` (18pt) | High-impact victory plaques and mode splash |
| **`BoldPixels.ttf`** | Heavy bold square pixel font | `title_bold` (16pt) | Retro pixel art title displays |
| **`3x5_*` Family** | 6 variants: Block, Notched, Rounded (Standard & Mono) | Specialized micro labels | Experimental micro-typography and candidate testing |

---

## Configuration & Runtime Lifecycle
- **`font_config.json`**: Centralized declarative JSON dictionary mapping abstract UI font tokens to concrete `.ttf` filenames and default point sizes.
- **Windows GDI Font Registration**: [`pixel_ui.py`](../../pixel_ui.py) registers bundled TTF files into the Windows process font table via `AddFontResourceExW(path, FR_PRIVATE, 0)`.
- **Clean Process Tear-Down**: On application exit or root window destroy, `pixel_ui.unload_bundled_fonts()` calls `RemoveFontResourceExW` to release process handles.
- **Font Comparison Specimen**: Visual candidate comparisons are generated via [`tools/build_font_comparison_specimen.py`](../../tools/build_font_comparison_specimen.py).

