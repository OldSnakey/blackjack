"""
Release Media Capture Tool for itch.io Release 1.6.0.
Captures:
- 01_3seat_training_mode.png
- 02_3seat_in_play.png
- 03_single_seat_casino.png
- 04_wardrobe_hall_of_fame.png
- 05_hells_table_pit_fiend.png
- 06_keyboard_shortcuts_help.png
- gameplay_3seat_card_counting.gif
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

from blackjack import BlackjackApp, StoryDialogueDialog
from rules import Card
from haunted_manager import Phase
from save_manager import SaveManager
from ui_dialogs import (
    StoryDialogueDialog,
    AngelicDraftDialog,
    SettingsDialog,
    ShortcutsDialog,
    WelcomeSplashDialog,
)
from dealer_wardrobe_dialog import WardrobeDialog
from card_counting_hud import CardCountingHud


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
        w, h = 900, 800

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


def pump(root: tkinter.Tk, iterations: int = 5, delay: float = 0.02):
    for _ in range(iterations):
        root.update_idletasks()
        root.update()
        if delay > 0:
            time.sleep(delay)


def build_card_helper(app: BlackjackApp, rank: str, suit: str) -> Card:
    suit_clean = suit.rstrip("s").lower()
    rank_clean = str(rank).lower()
    for c in app.all_cards:
        if str(c.rank).lower() == rank_clean and c.suit.lower() == suit_clean:
            return c
    raise ValueError(f"Card not found: {rank} of {suit}")


def capture_all():
    sys.stdout.reconfigure(encoding="utf-8")
    out_dir = BASE_DIR / "docs" / "release" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    gif_path = BASE_DIR / "docs" / "release" / "gameplay_3seat_card_counting.gif"

    temp_dir = tempfile.TemporaryDirectory()
    save_file = Path(temp_dir.name) / "release_save.json"

    root = tkinter.Tk()
    root.title("Blackjack v1.6.0")
    root.geometry("1100x820+50+50")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    app = BlackjackApp(root, chips_mode=True, sound_enabled=False)
    app.save_manager = SaveManager(save_path=save_file)
    app.save_manager.data.highscores.peak_bankroll = 15500
    app.save_manager.data.highscores.total_hands_played = 142
    app.save_manager.data.highscores.total_hands_won = 78
    app.save_manager.data.highscores.total_blackjacks = 22
    app.save_manager.data.highscores.best_counting_streak = 16
    app.save_manager.data.highscores.counting_streak = 9
    app.save_manager.data.achievements.exorcist = True
    app.save_manager.data.achievements.celestial = True
    app.save_manager.data.achievements.high_roller = True
    app.save_manager.data.achievements.apprentice_counter = True
    app.save_manager.data.achievements.master_counter = True

    print("[1/7] Capturing 01_3seat_training_mode.png...")
    app.set_table_seats(3)
    if not app.card_counting_hud.is_visible:
        app._toggle_card_counting_hud()
    app._clear_bet()
    app.focused_betting_seat = 2
    app._on_key_chip(50)
    app._on_key_cycle_seat_focus(-1)
    app._on_key_chip(25)
    app._on_key_cycle_seat_focus(1)
    app._on_key_cycle_seat_focus(1)
    app._on_key_chip(25)
    app._on_key_cycle_seat_focus(-1)
    app.card_counting_hud.update_counts(cards_remaining=284, base_bet=50)
    app.set_dealer_speech("Welcome to the 3-seat training table. Keep your count sharp!", stream=False)
    pump(root, 10)
    img_01 = capture_hwnd_to_image(root.winfo_id())
    img_01.save(out_dir / "01_3seat_training_mode.png")

    print("[2/7] Capturing 02_3seat_in_play.png...")
    # Setup rigged deck for clean 3-seat play:
    # Clockwise order deal:
    # Round 1: Seat 1, Seat 2, Seat 3, Dealer Upcard
    # Round 2: Seat 1, Seat 2, Seat 3, Dealer Hole
    c_s1_1 = build_card_helper(app, "10", "spades")
    c_s2_1 = build_card_helper(app, "6", "hearts")
    c_s3_1 = build_card_helper(app, "9", "diamonds")
    c_dl_1 = build_card_helper(app, "6", "clubs")  # dealer upcard: 6

    c_s1_2 = build_card_helper(app, "8", "clubs")     # seat 1 total: 18
    c_s2_2 = build_card_helper(app, "5", "diamonds")  # seat 2 total: 11
    c_s3_2 = build_card_helper(app, "10", "hearts")   # seat 3 total: 19
    c_dl_2 = build_card_helper(app, "10", "spades")   # dealer hole: 10 (total 16)

    # Subsequent hit card for seat 2
    c_s2_hit = build_card_helper(app, "10", "clubs")  # seat 2 hit -> 21!
    c_dl_bust = build_card_helper(app, "10", "diamonds") # dealer hit -> 26 bust!

    # Rig shoe (pop from end)
    app.deck = [c_dl_bust, c_s2_hit, c_dl_2, c_s3_2, c_s2_2, c_s1_2, c_dl_1, c_s3_1, c_s2_1, c_s1_1]
    
    app._deal_hand_with_bet()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    pump(root, 5)

    # Advance Seat 1 by standing (Seat 1 stands on 18)
    app.on_stand()
    pump(root, 10)

    # Now Seat 2 is active with 11!
    app.card_counting_hud.update_counts(cards_remaining=276, base_bet=50)
    app.set_dealer_speech("Seat 2, you have 11 against my 6. Double down or Hit?", stream=False)
    pump(root, 10)
    img_02 = capture_hwnd_to_image(root.winfo_id())
    img_02.save(out_dir / "02_3seat_in_play.png")

    print("[3/7] Capturing 03_single_seat_casino.png...")
    # Switch back to 1-seat casino mode
    app.set_table_seats(1)
    if app.card_counting_hud.is_visible:
        app._toggle_card_counting_hud()
    app._clear_bet()
    app._add_chip_bet(100)

    c1 = build_card_helper(app, "king", "spades")
    c2 = build_card_helper(app, "queen", "hearts")
    d1 = build_card_helper(app, "6", "diamonds")
    d2 = build_card_helper(app, "jack", "clubs")
    app.deck = [d2, c2, d1, c1]

    app._deal_hand_with_bet()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    app.set_dealer_speech("A pristine 20! Dealer shows a 6. Standing is the textbook play.", stream=False)
    pump(root, 10)
    img_03 = capture_hwnd_to_image(root.winfo_id())
    img_03.save(out_dir / "03_single_seat_casino.png")

    print("[4/7] Capturing 04_wardrobe_hall_of_fame.png...")
    app._open_wardrobe_dialog(initial_tab=2)
    pump(root, 10)
    wardrobe_dlg = app._wardrobe_dialog
    img_04 = capture_hwnd_to_image(wardrobe_dlg.winfo_id())
    img_04.save(out_dir / "04_wardrobe_hall_of_fame.png")
    wardrobe_dlg.destroy()
    app._wardrobe_dialog = None
    pump(root, 5)

    print("[5/7] Capturing 05_hells_table_pit_fiend.png...")
    # Set up Hell's Table showdown
    app.set_table_seats(1)
    app.suppress_mode_dialog = True
    app._trigger_hell_table()
    app.set_dealer_speech("Welcome to the Abyssal Wager! Your petty chips mean nothing—only your Soul remains.", stream=False)
    
    # Place infernal cards on table
    c_inf1 = build_card_helper(app, "ace", "spades")
    c_inf2 = build_card_helper(app, "king", "hearts")
    d_inf1 = build_card_helper(app, "ace", "clubs")
    d_inf2 = build_card_helper(app, "10", "diamonds")
    app.deck = [d_inf2, c_inf2, d_inf1, c_inf1]
    app._deal_hand_with_bet()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    pump(root, 10)
    img_05 = capture_hwnd_to_image(root.winfo_id())
    img_05.save(out_dir / "05_hells_table_pit_fiend.png")

    print("[6/7] Capturing 06_keyboard_shortcuts_help.png...")
    # Revert back to normal theme for shortcuts screenshot
    app.haunted.phase = Phase.NORMAL
    app._apply_phase_theme(Phase.NORMAL)
    app._show_shortcuts_overlay()
    pump(root, 10)
    shortcuts_dlg = app._shortcuts_dialog
    img_06 = capture_hwnd_to_image(shortcuts_dlg.winfo_id())
    img_06.save(out_dir / "06_keyboard_shortcuts_help.png")
    shortcuts_dlg.destroy()
    app._shortcuts_dialog = None
    pump(root, 5)

    print("[7/7] Generating animated GIF gameplay_3seat_card_counting.gif...")
    # Prepare animated GIF sequence of 3-seat card counting round
    frames: list[Image.Image] = []
    
    # Re-init fresh 3-seat mode
    app.haunted.phase = Phase.NORMAL
    app._apply_phase_theme(Phase.NORMAL)
    app.set_table_seats(3)
    if not app.card_counting_hud.is_visible:
        app._toggle_card_counting_hud()
    app._clear_bet()
    app.card_counter.running_count = 2
    app.card_counter.deck_count = 6
    app.card_counting_hud.update_counts(cards_remaining=288, base_bet=50)

    # Frame sequence 1: Betting focus on Seat 2, place $50 bet
    app.focused_betting_seat = 2
    app._on_key_chip(50)
    app.set_dealer_speech("Place your bets across all three seats.", stream=False)
    pump(root, 5)
    for _ in range(3):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Frame sequence 2: Shift to Seat 1, place $25 bet
    app._on_key_cycle_seat_focus(-1)
    app._on_key_chip(25)
    pump(root, 5)
    for _ in range(3):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Frame sequence 3: Shift to Seat 3, place $25 bet
    app._on_key_cycle_seat_focus(1)
    app._on_key_cycle_seat_focus(1)
    app._on_key_chip(25)
    pump(root, 5)
    for _ in range(3):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Return focus to Seat 1
    app._on_key_cycle_seat_focus(-1)
    pump(root, 5)

    # Setup rigged deck for full 3-seat round drama:
    # Clockwise initial deal:
    # Pass 1: S1 (10), S2 (6), S3 (9), Dealer Upcard (6)
    # Pass 2: S1 (8 -> 18), S2 (5 -> 11), S3 (10 -> 19), Dealer Hole (10 -> 16)
    # Player hits: S2 hits (10 -> 21!)
    # Dealer hits: Dealer hits (Queen -> 26 BUST!)
    c_s1_1 = build_card_helper(app, "10", "spades")
    c_s2_1 = build_card_helper(app, "6", "hearts")
    c_s3_1 = build_card_helper(app, "9", "diamonds")
    c_dl_1 = build_card_helper(app, "6", "clubs")

    c_s1_2 = build_card_helper(app, "8", "clubs")
    c_s2_2 = build_card_helper(app, "5", "diamonds")
    c_s3_2 = build_card_helper(app, "10", "hearts")
    c_dl_2 = build_card_helper(app, "10", "spades")

    c_s2_hit = build_card_helper(app, "10", "clubs")
    c_dl_bust = build_card_helper(app, "queen", "diamonds")

    app.deck = [c_dl_bust, c_s2_hit, c_dl_2, c_s3_2, c_s2_2, c_s1_2, c_dl_1, c_s3_1, c_s2_1, c_s1_1]

    # Deal hand
    app.set_dealer_speech("Dealing clockwise across all 3 active seats...", stream=False)
    app._deal_hand_with_bet()
    
    # Capture deal progression frames
    deal_step = 0
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
        deal_step += 1
        if deal_step % 2 == 0:
            frames.append(capture_hwnd_to_image(root.winfo_id()))

    pump(root, 5)
    # Cards dealt! Seat 1 active (18 points)
    app.set_dealer_speech("Seat 1: 18 points. Standing.", stream=False)
    pump(root, 5)
    for _ in range(4):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Seat 1 stands -> moves to Seat 2 (11 points)
    app.on_stand()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    pump(root, 5)
    app.set_dealer_speech("Seat 2: 11 points against Dealer 6. Hit!", stream=False)
    pump(root, 5)
    for _ in range(4):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Seat 2 hits -> receives 10 -> 21!
    app.on_hit()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    pump(root, 5)
    app.set_dealer_speech("21 on Seat 2! Outstanding!", stream=False)
    pump(root, 5)
    for _ in range(4):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Seat 2 stands -> moves to Seat 3 (19 points)
    app.on_stand()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    pump(root, 5)
    app.set_dealer_speech("Seat 3: 19 points. Standing.", stream=False)
    pump(root, 5)
    for _ in range(4):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    # Seat 3 stands -> Dealer turn
    app.on_stand()
    while getattr(app, "_dealing", False) or getattr(app, "_dealer_timer_id", None):
        pump(root, 2, delay=0.02)
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    pump(root, 10)
    # Dealer busts with 26, win banners on all 3 seats
    app.set_dealer_speech("Dealer busts with 26! All 3 seats win!", stream=False)
    pump(root, 10)
    for _ in range(8):
        frames.append(capture_hwnd_to_image(root.winfo_id()))

    print(f"Captured {len(frames)} frames for animated GIF.")
    
    # Optimize and resize slightly for smooth loading (width: 720, height: proportional)
    resized_frames = []
    target_w = 720
    for f in frames:
        scale = target_w / f.width
        target_h = int(f.height * scale)
        rf = f.resize((target_w, target_h), Image.Resampling.LANCZOS).convert("P", palette=Image.Palette.ADAPTIVE)
        resized_frames.append(rf)

    resized_frames[0].save(
        gif_path,
        save_all=True,
        append_images=resized_frames[1:],
        duration=220,
        loop=0,
        optimize=True,
    )
    print(f"Saved {gif_path} ({gif_path.stat().st_size / 1024 / 1024:.2f} MB)")

    app._on_close()
    temp_dir.cleanup()
    print("Done! All media captured successfully.")


if __name__ == "__main__":
    capture_all()
