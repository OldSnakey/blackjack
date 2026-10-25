"""
Capture verification tool for refactored dialogs:
- SettingsDialog (two-tier preferences, complete records, scroll container)
- ShortcutsDialog Tab 0 (Gameplay & Betting)
- ShortcutsDialog Tab 1 (System & Controls)
- WardrobeDialog Tab 2 (Hall of Fame 8 plaques in scrollable container)
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
        w, h = 800, 600

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
    root.title("Blackjack - Dialog Verification")
    root.geometry("1100x820+50+50")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    app = BlackjackApp(root, chips_mode=False, sound_enabled=False)
    app.save_manager = SaveManager(save_path=save_file)
    app.save_manager.data.highscores.peak_bankroll = 15500
    app.save_manager.data.highscores.total_hands_played = 120
    app.save_manager.data.highscores.total_hands_won = 68
    app.save_manager.data.highscores.total_blackjacks = 19
    app.save_manager.data.highscores.best_counting_streak = 14
    app.save_manager.data.highscores.counting_streak = 8
    app.save_manager.data.achievements.exorcist = True
    app.save_manager.data.achievements.apprentice_counter = True

    artifact_dirs = [
        BASE_DIR / "verification",
        Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\4cc8d8d2-c72e-4a67-8d44-37320d173939"),
    ]
    for d in artifact_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Capture Settings Dialog
    app._open_settings_dialog()
    for _ in range(15):
        root.update()
        time.sleep(0.02)

    settings = app._settings_dialog
    if settings and settings.winfo_exists():
        screenshot = capture_hwnd_to_image(settings.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_settings_dialog.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")
    app._close_settings_dialog()
    root.update()

    # 2. Capture Shortcuts Dialog Tab 0 (Gameplay & Betting)
    app._show_shortcuts_overlay()
    for _ in range(15):
        root.update()
        time.sleep(0.02)

    shortcuts = app._shortcuts_dialog
    if shortcuts and shortcuts.winfo_exists():
        shortcuts._switch_tab(0)
        root.update()
        time.sleep(0.05)
        screenshot = capture_hwnd_to_image(shortcuts.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_shortcuts_dialog_tab0.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")

        # 3. Capture Shortcuts Dialog Tab 1 (System & Controls)
        shortcuts._switch_tab(1)
        root.update()
        time.sleep(0.05)
        screenshot = capture_hwnd_to_image(shortcuts.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_shortcuts_dialog_tab1.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")

    app._close_shortcuts_overlay()
    root.update()

    # 4. Capture Wardrobe Dialog Tab 2 (Hall of Fame)
    app._on_click_stage_hanger()
    for _ in range(15):
        root.update()
        time.sleep(0.02)

    wardrobe = app._wardrobe_dialog
    if wardrobe and wardrobe.winfo_exists():
        wardrobe._switch_tab(1)
        root.update()
        time.sleep(0.05)
        screenshot = capture_hwnd_to_image(wardrobe.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_wardrobe_tab2_hof.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")
        wardrobe._on_close()

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
