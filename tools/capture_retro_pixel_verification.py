"""
Visual verification capture script for retro pixel typography and plaque styling.
Captures:
1. Betting phase table (Shoe counter, Bankroll, Bet buttons).
2. In-play phase table (Riveted plaques with transparent canvas text, Hit/Stand enabled, Double/Split/Surrender disabled recessed into mahogany).
3. Cursed stakes unlocked on mahogany rail (checking horizontal collision and 24px gap).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import tempfile
import time
import tkinter
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from blackjack import BlackjackApp
from save_manager import SaveManager
from tools.capture_dialogs_verification import capture_hwnd_to_image


def main():
    artifact_dir = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\4cc8d8d2-c72e-4a67-8d44-37320d173939")
    temp_dir = tempfile.TemporaryDirectory()

    root = tkinter.Tk()
    root.geometry("1020x720")
    SaveManager.DEFAULT_SAVE_FILE = str(Path(temp_dir.name) / "test_save.json")

    app = BlackjackApp(root, chips_mode=True, sound_enabled=False)
    root.update_idletasks()
    root.update()
    time.sleep(0.1)

    # 1. Capture Betting Phase
    shot1 = capture_hwnd_to_image(root.winfo_id())
    out1 = artifact_dir / "verified_betting_phase.png"
    shot1.convert("RGB").save(str(out1), "PNG")
    print(f"SAVED: {out1}")

    # 2. Stage $5 bet and deal hand -> In-Play Phase
    app._add_chip_bet(5)
    root.update()
    app._deal_hand_with_bet()
    for _ in range(10):
        root.update()
        time.sleep(0.05)

    shot2 = capture_hwnd_to_image(root.winfo_id())
    out2 = artifact_dir / "verified_play_phase.png"
    shot2.convert("RGB").save(str(out2), "PNG")
    print(f"SAVED: {out2}")

    # 3. Unlock and reveal Cursed Stakes on Mahogany Rail
    app.haunted.unlocked_cursed_stakes = True
    app.cursed_stakes_button.grid()
    app._reposition_rail_buttons()
    for _ in range(5):
        root.update()
        time.sleep(0.02)

    shot3 = capture_hwnd_to_image(root.winfo_id())
    out3 = artifact_dir / "verified_cursed_stakes_rail.png"
    shot3.convert("RGB").save(str(out3), "PNG")
    print(f"SAVED: {out3}")

    try:
        app._on_close()
    except Exception:
        pass
    try:
        root.destroy()
    except Exception:
        pass
    try:
        temp_dir.cleanup()
    except Exception:
        pass


if __name__ == "__main__":
    main()
