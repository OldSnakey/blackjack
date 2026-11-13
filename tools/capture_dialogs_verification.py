"""
Capture verification tool for refactored dialogs:
- SettingsDialog Tab 0 (Table & Audio) & Tab 1 (House Rules)
- TripometerDialog (Empty state & Populated audit log state)
- ShortcutsDialog Tab 0 (Gameplay & Betting) & Tab 1 (System & Controls)
- WardrobeDialog Tab 2 (Hall of Fame plaques in scrollable container)
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
from rules import Card, VENUE_PRESETS


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

    app = BlackjackApp(root, chips_mode=True, sound_enabled=False, save_path=save_file)
    app.save_manager.data.highscores.peak_bankroll = 15500
    app.save_manager.data.highscores.total_hands_played = 120
    app.save_manager.data.highscores.total_hands_won = 68
    app.save_manager.data.highscores.total_blackjacks = 19
    app.save_manager.data.highscores.best_counting_streak = 14
    app.save_manager.data.highscores.counting_streak = 8
    app.save_manager.data.achievements.exorcist = True
    app.save_manager.data.achievements.apprentice_counter = True

    for _ in range(15):
        root.update()
        time.sleep(0.02)

    artifact_dirs = [
        BASE_DIR / "verification",
        Path(r"C:\Users\wrehm\.gemini\antigravity\brain\6946b530-e64f-4dcb-931a-cb4cacaca12f"),
    ]
    for d in artifact_dirs:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Capture Settings Dialog (Tab 0: Table & Audio, Tab 1: House Rules)
    app._open_settings_dialog()
    for _ in range(15):
        root.update()
        time.sleep(0.02)

    settings = app._settings_dialog
    if settings and settings.winfo_exists():
        settings._switch_tab(0)
        root.update()
        time.sleep(0.05)
        screenshot = capture_hwnd_to_image(settings.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_settings_dialog.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")

        settings._switch_tab(1)
        root.update()
        time.sleep(0.05)
        screenshot = capture_hwnd_to_image(settings.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_settings_house_rules_tab.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")
    app._close_settings_dialog()
    root.update()

    # 2. Capture Tripometer Dialog (Empty State)
    app._open_tripometer_dialog()
    for _ in range(15):
        root.update()
        time.sleep(0.02)

    trip_dlg = app._tripometer_dialog
    if trip_dlg and trip_dlg.winfo_exists():
        screenshot = capture_hwnd_to_image(trip_dlg.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_tripometer_empty.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")
    app._close_tripometer_dialog()
    root.update()

    # 3. Populate sample Tripometer rounds and capture Populated State
    rules_classic = VENUE_PRESETS["classic_4_deck"]
    rules_vegas = VENUE_PRESETS["vegas_strip"]

    # Round 1: Optimal Basic Strategy Double (11 vs 6 @ TC +2.0, Kelly 2u=$10)
    app.tripometer.begin_round(rules_classic, pre_deal_tc=2.0, seat_bets={0: 10}, round_bankroll=1000, chips_mode=True)
    app.tripometer.record_decision(
        seat_idx=0,
        hand_idx=0,
        cards=[Card(6, "", "6", "spade"), Card(5, "", "5", "heart")],
        dealer_upcard=Card(6, "", "6", "diamond"),
        action="DOUBLE",
        live_tc=2.0,
        can_split=False,
        can_double=True,
        can_surrender=True,
    )
    app.tripometer.finalize_round(
        settled_hands=[
            {
                "seat_idx": 0,
                "hand_idx": 0,
                "cards": [Card(6, "", "6", "spade"), Card(5, "", "5", "heart"), Card(10, "", "king", "club")],
                "wager": 20,
                "outcome": "PLAYER_WINS",
                "net_profit": 20,
            }
        ],
        dealer_cards=[Card(6, "", "6", "diamond"), Card(10, "", "queen", "heart"), Card(8, "", "8", "club")],
        net_round_profit=20,
    )

    # Round 2: Optimal Illustrious 18 Deviation (16 vs 10 Stand @ TC +3.0, Kelly 4u=$20)
    app.tripometer.begin_round(rules_classic, pre_deal_tc=3.0, seat_bets={0: 20}, round_bankroll=1020, chips_mode=True)
    app.tripometer.record_decision(
        seat_idx=0,
        hand_idx=0,
        cards=[Card(10, "", "10", "club"), Card(6, "", "6", "diamond")],
        dealer_upcard=Card(10, "", "jack", "spade"),
        action="STAND",
        live_tc=3.0,
        can_split=False,
        can_double=True,
        can_surrender=False,
    )
    app.tripometer.finalize_round(
        settled_hands=[
            {
                "seat_idx": 0,
                "hand_idx": 0,
                "cards": [Card(10, "", "10", "club"), Card(6, "", "6", "diamond")],
                "wager": 20,
                "outcome": "PLAYER_WINS",
                "net_profit": 20,
            }
        ],
        dealer_cards=[Card(10, "", "jack", "spade"), Card(6, "", "6", "club"), Card(9, "", "9", "heart")],
        net_round_profit=20,
    )

    # Round 3: Two optimal BS decisions in one round (12 vs 2 Hit -> 18 vs 2 Stand @ TC +0.5, Kelly 1u=$5)
    app.tripometer.begin_round(rules_classic, pre_deal_tc=0.5, seat_bets={0: 5}, round_bankroll=1040, chips_mode=True)
    app.tripometer.record_decision(
        seat_idx=0,
        hand_idx=0,
        cards=[Card(8, "", "8", "spade"), Card(4, "", "4", "heart")],
        dealer_upcard=Card(2, "", "2", "club"),
        action="HIT",
        live_tc=0.5,
        can_split=False,
        can_double=True,
        can_surrender=True,
    )
    app.tripometer.record_decision(
        seat_idx=0,
        hand_idx=0,
        cards=[Card(8, "", "8", "spade"), Card(4, "", "4", "heart"), Card(6, "", "6", "diamond")],
        dealer_upcard=Card(2, "", "2", "club"),
        action="STAND",
        live_tc=0.5,
        can_split=False,
        can_double=False,
        can_surrender=False,
    )
    app.tripometer.finalize_round(
        settled_hands=[
            {
                "seat_idx": 0,
                "hand_idx": 0,
                "cards": [Card(8, "", "8", "spade"), Card(4, "", "4", "heart"), Card(6, "", "6", "diamond")],
                "wager": 5,
                "outcome": "PLAYER_WINS",
                "net_profit": 5,
            }
        ],
        dealer_cards=[Card(2, "", "2", "club"), Card(10, "", "king", "diamond"), Card(10, "", "10", "spade")],
        net_round_profit=5,
    )

    # Round 4: Suboptimal Overbet + Basic Strategy Mistake (Stand on 14 vs 10 @ TC -1.0 instead of Surrender)
    app.tripometer.begin_round(rules_vegas, pre_deal_tc=-1.0, seat_bets={0: 100}, round_bankroll=1045, chips_mode=True)
    app.tripometer.record_decision(
        seat_idx=0,
        hand_idx=0,
        cards=[Card(8, "", "8", "heart"), Card(6, "", "6", "spade")],
        dealer_upcard=Card(10, "", "10", "diamond"),
        action="STAND",
        live_tc=-1.0,
        can_split=False,
        can_double=True,
        can_surrender=True,
    )
    app.tripometer.finalize_round(
        settled_hands=[
            {
                "seat_idx": 0,
                "hand_idx": 0,
                "cards": [Card(8, "", "8", "heart"), Card(6, "", "6", "spade")],
                "wager": 100,
                "outcome": "DEALER_WINS",
                "net_profit": -100,
            }
        ],
        dealer_cards=[Card(10, "", "10", "diamond"), Card(8, "", "8", "spade")],
        net_round_profit=-100,
    )

    app._open_tripometer_dialog()
    for _ in range(15):
        root.update()
        time.sleep(0.02)

    trip_dlg = app._tripometer_dialog
    if trip_dlg and trip_dlg.winfo_exists():
        screenshot = capture_hwnd_to_image(trip_dlg.winfo_id())
        for d in artifact_dirs:
            out_path = d / "verified_tripometer_populated.png"
            screenshot.convert("RGB").save(str(out_path), "PNG")
            print(f"SAVED: {out_path}")
    app._close_tripometer_dialog()
    root.update()

    # 4. Capture Shortcuts Dialog Tab 0 (Gameplay & Betting)
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
