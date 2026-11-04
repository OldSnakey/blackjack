# Keyboard & Mouse Overlay Icons (`assets/overlay_icons`)

## Overview
The `overlay_icons` directory contains 29 curated Kenney input prompt sprites (64x64 RGBA PNGs) providing authentic, high-contrast graphical keycaps for the in-game Keyboard Shortcuts & Controls modal HUD ([`ui_dialogs.py:ShortcutsDialog`](../../ui_dialogs.py)).

---

## Icon Catalogue

| Category | Sprite Files | Associated Game Action |
| :--- | :--- | :--- |
| **Table Actions** | `keyboard_space.png`, `keyboard_enter.png` | Deal Bet / Hit / Next Game (Context-Sensitive) |
| **Player Actions** | `keyboard_h.png`, `keyboard_s.png`, `keyboard_d.png`, `keyboard_p.png`, `keyboard_r.png` | Hit, Stand, Double Down, Split Pair, Surrender |
| **Chips & Betting** | `keyboard_1.png` through `keyboard_5.png` | Quick-stage \$5, \$25, \$100, \$500, \$1,000 chips |
| **Multi-Seat Navigation** | `keyboard_arrow_left.png`, `keyboard_arrow_right.png` | Cycle betting seat focus visually across Seats 1, 2, and 3 |
| **Side Bets** | `keyboard_q.png`, `keyboard_e.png` | Stage \$5 on Perfect Pairs (`Q` / `6`) or 21+3 Poker (`E` / `7`) |
| **Wager Controls** | `keyboard_a.png`, `keyboard_c.png` | All In (Wager entire bankroll) / Clear All Staged Bets |
| **Insurance** | `keyboard_y.png`, `keyboard_n.png`, `keyboard_escape.png` | Take Insurance / Decline Insurance / Dismiss Modals |
| **System & Overlays** | `keyboard_m.png`, `keyboard_v.png`, `keyboard_k.png`, `keyboard_shift.png`, `keyboard_f1.png`, `keyboard_f11.png`, `keyboard_question.png` | Sound Mute, Dealer View, Card Counter HUD, Fullscreen, Help Overlay |
| **Specialized Actions** | `keyboard_x.png`, `keyboard_f10.png` | Miracle Draw (Hell's Table) / Secondary display bindings |
| **Mouse Clicks** | `mouse_left.png` | Direct table felt spot and chip pile clicking |

---

## Caching & Scaling Architecture
- **`KeyboardIconLoader`** ([`audio_assets.py`](../../audio_assets.py)): Reads 64x64 master PNGs from this directory, applies PIL Lanczos anti-aliasing resampling to render clean 24x24, 28x28, or 32x32 `ImageTk.PhotoImage` widgets, and caches them in memory to eliminate disk I/O when opening dialogs.
- **Visual Deck Harmony**: Matches dark emerald baize themes with clean white keycaps and crisp black legends.

