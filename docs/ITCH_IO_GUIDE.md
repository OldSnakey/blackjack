# itch.io Distribution & Store Setup Guide

This guide details step-by-step instructions for publishing **Blackjack** to [itch.io](https://itch.io) so that non-engineers can effortlessly download and play the game.

---

## 1. Building the Release Package

Before creating your itch.io page, compile the release bundle:

1. Double-click `build_itch_release.bat` (or run `./build_itch_release.ps1` in PowerShell).
2. The script will:
   - Run all 92 unit tests to ensure zero bugs are shipped.
   - Compile a standalone executable with PyInstaller.
   - Bundle all cards, organic sound effects, and `README_PLAYERS.txt`.
   - Generate `dist/Blackjack-Windows-v1.0.0.zip`.

---

## 2. Setting Up Your itch.io Project

1. Log in to [itch.io](https://itch.io) and click **Create new project** (or go to `itch.io/game/new`).
2. Fill in the project details using the recommended settings below:

### Basic Information
- **Title**: `Blackjack` (or `Blackjack Classic`)
- **Project URL**: `https://<your-username>.itch.io/blackjack`
- **Short description or tagline**:
  > Authentic casino Blackjack desktop game with tactile 3D chips, dealer hole card peeks, splitting, doubling, and organic casino audio.
- **Classification**: `Games`
- **Kind of project**: `Downloadable`
- **Release status**: `Released`
- **Pricing**: `No payments` (or `$0 or donate`)

---

## 3. Visual Assets

- **Cover Image**: Upload `assets/cover_itch.png` (optimized 630x500 format featuring the gold chip, cards, and emerald felt).
- **Screenshots**: Take 2-4 in-game screenshots of:
  - The starting table with chips and cards.
  - A split hand or double-down scenario.
  - An authentic dealer hole card reveal or natural blackjack payout.

---

## 4. File Upload Configuration

Under the **Uploads** section:

1. Click **Upload files** and select `dist/Blackjack-Windows-v1.0.0.zip`.
2. Check the **Windows** platform checkbox (the Windows logo icon).
3. Under **Display name**, type: `Blackjack (Windows 64-bit)`.
4. Check the box: **"This file will be seen by everyone"**.

> [!TIP]
> **itch.io Desktop App Compatibility**:
> Because the zip contains a directory with `Blackjack.exe` at the root, users who have the itch.io Desktop App installed can simply click **Install** and **Launch** directly from their client with zero extraction steps!

---

## 5. Description (Copy & Paste)

Paste the following formatted description into the itch.io description editor:

```markdown
### Classic Casino Blackjack on Your Desktop

Experience authentic casino Blackjack with zero setup or installation required! Step up to the green felt table, place your wagers with realistic 3D stacked chips, and test your strategy against the dealer.

### Key Features
- 🎰 **Casino Mode & Casual Mode**: Play with an authentic $1,000 bankroll and staged betting, or switch to casual mode for instant zero-stress practice.
- 🃏 **Authentic Casino Rules**: Dealer Hole Card (face-down) peeks, 3:2 Natural Blackjack payouts, Double Down, Pair Splitting, Late Surrender, and 2:1 Insurance side bets.
- 🔊 **Tactile Casino Sound Effects**: 42 organic audio variations including card slides, hole card placement, chip clicks, all-in thuds, and shoe shuffles.
- 🪙 **Procedural 3D Chip Visualizer**: Stacked clay chips with drop shadows and dynamic chip animations for bets, dealer rakes, and payouts.
- 🧮 **Multi-Deck Shoe with Cut Card**: Persistent 4-deck shoe with dynamic card count tracking and authentic 25% cut card penetration reshuffling.
- ⌨️ **Keyboard Accessibility**: Full keyboard support for high-speed play (`Space`/`Enter` to Hit/Deal, `S` to Stand, `D` to Double, `P` to Split, `M` to Mute).

---

### Controls & Shortcuts
| Action | Mouse | Keyboard |
| :--- | :--- | :--- |
| **Deal / Hit** | Click Deal / Hit | `Enter` / `Space` |
| **Stand** | Click Stand | `S` |
| **Double Down** | Click Double | `D` |
| **Split Pair** | Click Split | `P` |
| **Surrender** | Click Surrender | `R` |
| **Toggle Audio** | Click Speaker Icon | `M` |
| **Clear Bet** | Click Clear Bet | `C` |
| **All In** | Click All In | `A` |
```

---

## 6. Download & Install Instructions

Paste the following in the **Download & Install Instructions** section on itch.io:

```text
1. Download the ZIP file: "Blackjack-Windows-v1.0.0.zip".
2. Right-click the downloaded file and select "Extract All...".
3. Open the extracted folder and double-click "Blackjack.exe" to play!

Note on Windows SmartScreen:
When launching for the first time, Windows Defender may display a blue warning ("Windows protected your PC"). This is normal for independent software without an expensive commercial signing certificate. Simply click "More info" and then "Run anyway" to launch the game.
```

---

## 7. Categorization & Tags

Add the following tags in the itch.io metadata section to maximize discoverability:
- `Card Game`
- `Casino`
- `Blackjack`
- `Singleplayer`
- `2D`
- `Casual`
- `Retro`
- `Pixel Graphics` (or `Stylized`)
- `Tabletop`

---

## 8. Publishing

1. Set **Visibility & Access** to **Public**.
2. Click **Save & View Page**.
3. Share your itch.io link with friends, family, or players!
