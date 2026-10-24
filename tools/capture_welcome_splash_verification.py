"""
Verification capture tool for:
1. WelcomeSplashDialog (Pixel art logo, Tiffany welcome greeting, 3 play mode cards, remember checkbox).
2. Table felt in Casual Mode (Chips mode disabled, no bankroll pressure).
3. Table felt in Casino Betting Mode (Bankroll $1,000, 2.5D chip visualizer active).
4. Table felt in Strategy & Counting Trainer Mode (Hi-Lo trainer HUD active with RC, TC, Bet Guide, and Strategy hint).
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import struct
import sys
import tempfile
import time
import tkinter
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import config
from blackjack import BlackjackApp
from save_manager import SaveManager
from ui_dialogs import WelcomeSplashDialog


def capture_hwnd_to_image(hwnd: int) -> Image.Image:
    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32

    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = wintypes.HDC
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user32.PrintWindow.restype = wintypes.BOOL

    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
        ctypes.c_void_p, ctypes.c_char_p, wintypes.UINT
    ]

    ga_root = user32.GetAncestor(hwnd, 2)
    if ga_root:
        hwnd = ga_root

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    if w <= 0 or h <= 0:
        raise ValueError(f"Invalid window dimensions: {w}x{h}")

    hdc_screen = user32.GetWindowDC(hwnd)
    hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
    hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
    gdi32.SelectObject(hdc_mem, hbm)

    user32.PrintWindow(hwnd, hdc_mem, 2)

    header = struct.pack("<LiiHHIIIIII", 40, w, -h, 1, 32, 0, w * h * 4, 0, 0, 0, 0)
    buf = (ctypes.c_byte * (w * h * 4))()
    gdi32.GetDIBits(hdc_mem, hbm, 0, h, ctypes.byref(buf), ctypes.c_char_p(header), 0)

    gdi32.DeleteObject(hbm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(hwnd, hdc_screen)

    img = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)
    return img.convert("RGB")


def main():
    out_dir = BASE_DIR / "verification"
    out_dir.mkdir(exist_ok=True)

    temp_save = Path(tempfile.mkdtemp()) / "capture_splash_save.json"

    root = tkinter.Tk()
    root.geometry(f"{config.DEFAULT_WINDOW_WIDTH}x{config.DEFAULT_WINDOW_HEIGHT}")
    root.title("Blackjack Verification Runner")
    app = BlackjackApp(root, sound_enabled=False, save_path=temp_save, chips_mode=True, skip_splash=True)
    root.update()

    # 1. Capture WelcomeSplashDialog
    print("Capturing WelcomeSplashDialog...")
    dlg = WelcomeSplashDialog(root, app)
    dlg.update()
    time.sleep(0.3)
    dlg_img = capture_hwnd_to_image(dlg.winfo_id())
    dlg_img.save(out_dir / "welcome_splash_dialog.png")
    print(f"Saved: {out_dir / 'welcome_splash_dialog.png'}")
    dlg.destroy()
    root.update()

    # 2. Capture Casual Mode Table Felt
    print("Capturing Casual Mode table felt...")
    app.apply_play_mode("casual")
    root.update()
    time.sleep(0.2)
    casual_img = capture_hwnd_to_image(root.winfo_id())
    casual_img.save(out_dir / "table_casual_mode.png")
    print(f"Saved: {out_dir / 'table_casual_mode.png'}")

    # 3. Capture Casino Betting Mode Table Felt
    print("Capturing Casino Betting Mode table felt...")
    app.apply_play_mode("betting")
    app.current_bet_var.set(50)
    if hasattr(app, "chip_visualizer"):
        app.chip_visualizer.set_bet(50, animate=False)
    root.update()
    time.sleep(0.2)
    betting_img = capture_hwnd_to_image(root.winfo_id())
    betting_img.save(out_dir / "table_betting_mode.png")
    print(f"Saved: {out_dir / 'table_betting_mode.png'}")

    # 4. Capture Strategy Trainer Mode Table Felt
    print("Capturing Strategy Trainer Mode table felt...")
    app.apply_play_mode("training")
    app.card_counter.running_count = 4
    app.card_counter.observed_cards_count = 52
    cards_rem = len(app.deck) if hasattr(app, "deck") else 156
    app.card_counting_hud.update_counts(cards_remaining=cards_rem, base_bet=25)
    app._refresh_strategy_hint()
    root.update()
    time.sleep(0.2)
    trainer_img = capture_hwnd_to_image(root.winfo_id())
    trainer_img.save(out_dir / "table_training_mode.png")
    print(f"Saved: {out_dir / 'table_training_mode.png'}")

    app._on_close()
    try:
        root.destroy()
    except Exception:
        pass
    print("Verification capture successfully completed!")


if __name__ == "__main__":
    main()
