"""
Capture verification tool for the redesigned retro-pixel Wardrobe & Hall of Fame dialog.
Captures:
- Tab 1: Wardrobe Closet (Julian, Tiffany, Puppet Dummy, and Mystery Silhouette card)
- Tab 2: Hall of Fame & Trophy Shelf (Records plaque + 8 achievement plaques)
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

from blackjack import BlackjackApp
from save_manager import SaveManager


def capture_hwnd_to_image(hwnd: int) -> Image.Image:
    """Captures a window to a PIL Image using GDI PrintWindow (offscreen-safe)."""
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
    gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_char_p, wintypes.UINT]

    ga_root = user32.GetAncestor(hwnd, 2)
    if ga_root:
        hwnd = ga_root

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    if w <= 0 or h <= 0:
        w, h = 940, 650

    hwnd_dc = user32.GetWindowDC(hwnd)
    mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
    bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, w, h)
    gdi32.SelectObject(mem_dc, bitmap)

    res = user32.PrintWindow(hwnd, mem_dc, 2)
    if not res:
        user32.PrintWindow(hwnd, mem_dc, 0)

    header = struct.pack("<LiiHHIIIIII", 40, w, -h, 1, 32, 0, w * h * 4, 0, 0, 0, 0)
    buf = (ctypes.c_byte * (w * h * 4))()
    gdi32.GetDIBits(mem_dc, bitmap, 0, h, ctypes.byref(buf), ctypes.c_char_p(header), 0)

    img = Image.frombuffer("RGBA", (w, h), bytes(buf), "raw", "BGRA", 0, 1)

    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(mem_dc)
    user32.ReleaseDC(hwnd, hwnd_dc)

    return img


def main():
    temp_dir = tempfile.TemporaryDirectory()
    save_file = Path(temp_dir.name) / "test_save.json"

    root = tkinter.Tk()
    root.title("Blackjack - Wardrobe Redesign Verification")
    root.geometry("1100x820+50+50")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    app = BlackjackApp(root, chips_mode=False, sound_enabled=False)
    app.save_manager = SaveManager(save_path=save_file)
    # Unlock a couple achievements to showcase both unlocked gold and locked states in Tab 2
    app.save_manager.data.achievements.exorcist = True
    app.save_manager.data.achievements.high_roller = True
    app.save_manager.data.highscores.peak_bankroll = 12500
    app.save_manager.data.highscores.longest_win_streak = 7
    app.save_manager.data.highscores.total_hands_won = 42
    app.save_manager.data.highscores.total_hands_played = 68
    app.save_manager.data.highscores.total_blackjacks = 9

    artifact_dir = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\4cc8d8d2-c72e-4a67-8d44-37320d173939")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Equip Dummy to showcase active yellow highlight on Page 1
    app.dealer_actor.equip_costume("dummy", "dummy")
    app.save_manager.data.equipped_costume = "dummy"

    # 1. Open Wardrobe Dialog on Tab 0 (Closet)
    app._open_wardrobe_dialog(initial_tab=0)
    for _ in range(25):
        root.update()
        time.sleep(0.02)

    dialog = app._wardrobe_dialog
    if dialog and dialog.winfo_exists():
        hwnd = dialog.winfo_id()
        screenshot_tab0 = capture_hwnd_to_image(hwnd)
        out_path0 = artifact_dir / "wardrobe_tab1_closet.png"
        screenshot_tab0.convert("RGB").save(str(out_path0), "PNG")
        print(f"SAVED: {out_path0}")

        # 1. Trigger Julian's voice on Page 1 to capture speech bubble with tail
        dialog.cards["julian"]["panel"]._play_voice()
        for _ in range(40):
            root.update()
            time.sleep(0.02)

        screenshot_speech = capture_hwnd_to_image(hwnd)
        out_path_speech = artifact_dir / "wardrobe_tab1_voice_speech_bubble.png"
        screenshot_speech.convert("RGB").save(str(out_path_speech), "PNG")
        print(f"SAVED: {out_path_speech}")

        # 2. Switch to Page 3 (The Masters & High Rollers: Selene & Vladimir locked)
        dialog._switch_page(2)
        for _ in range(15):
            root.update()
            time.sleep(0.02)

        # Trigger Vladimir's voice on Page 3
        dialog.cards["vladimir"]["panel"]._play_voice()
        for _ in range(40):
            root.update()
            time.sleep(0.02)

        screenshot_p3 = capture_hwnd_to_image(hwnd)
        out_path_p3 = artifact_dir / "wardrobe_tab1_page3_locked.png"
        screenshot_p3.convert("RGB").save(str(out_path_p3), "PNG")
        print(f"SAVED: {out_path_p3}")

        # 3. Switch to Tab 1 (Hall of Fame)
        dialog._switch_tab(1)
        for _ in range(25):
            root.update()
            time.sleep(0.02)

        screenshot_tab1 = capture_hwnd_to_image(hwnd)
        out_path1 = artifact_dir / "wardrobe_tab2_hall_of_fame.png"
        screenshot_tab1.convert("RGB").save(str(out_path1), "PNG")
        print(f"SAVED: {out_path1}")

    try:
        if app._wardrobe_dialog:
            app._wardrobe_dialog.destroy()
    except Exception:
        pass
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
