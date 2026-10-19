"""
Verification tool: Captures the live WardrobeDialog with the Puppet Dummy card visible and equippable.
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
    root.title("Blackjack - Wardrobe Puppet Dummy Verification")
    root.geometry("1100x820+50+50")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    app = BlackjackApp(root, chips_mode=False, sound_enabled=False)
    app.save_manager = SaveManager(save_path=save_file)

    # Open Wardrobe Dialog
    app._on_click_stage_hanger()
    for _ in range(20):
        root.update()
        time.sleep(0.02)

    dialog = app._wardrobe_dialog
    if dialog and dialog.winfo_exists():
        hwnd = dialog.winfo_id()
        screenshot = capture_hwnd_to_image(hwnd)
        artifact_dir = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\961dac34-d1bc-4f26-a9b9-15da0b316e33")
        artifact_dir.mkdir(parents=True, exist_ok=True)
        out_path = artifact_dir / "wardrobe_dummy_card_verification.png"
        screenshot.convert("RGB").save(str(out_path), "PNG")
        print(f"SAVED: {out_path}")

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
