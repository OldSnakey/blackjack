"""
Release Media Capture Tool for itch.io Release 2.0.0.
Captures:
- Screenshots in docs/release/screenshots/:
  - 01_bootcamp_curriculum_map.png
  - 02_bootcamp_lecture_table_sweep.png
  - 03_bootcamp_challenge_drill.png
  - 04_bootcamp_report_card.png
  - 05_dealer_wardrobe_costumes.png
  - 06_3seat_training_mode.png (also saved as 01_3seat_training_mode.png)
  - 07_3seat_in_play.png (also saved as 02_3seat_in_play.png)
  - 08_single_seat_casino.png (also saved as 03_single_seat_casino.png)
  - 09_wardrobe_hall_of_fame.png (also saved as 04_wardrobe_hall_of_fame.png)
  - 10_hells_table_pit_fiend.png (also saved as 05_hells_table_pit_fiend.png)
  - 06_keyboard_shortcuts_help.png
- Animated GIFs in docs/release/:
  - gameplay_card_counting_bootcamp.gif
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

from blackjack import BlackjackApp, __version__
from rules import Card
from haunted_manager import Phase
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
    gdi32.GetDIBits.argtypes = [
        wintypes.HDC,
        wintypes.HBITMAP,
        wintypes.UINT,
        wintypes.UINT,
        ctypes.c_void_p,
        ctypes.c_char_p,
        wintypes.UINT,
    ]

    ga_root = user32.GetAncestor(hwnd, 2)
    if ga_root:
        hwnd = ga_root

    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    w = rect.right - rect.left
    h = rect.bottom - rect.top

    if w <= 0 or h <= 0:
        w, h = 1000, 740

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


def pump(root: tkinter.Tk, iterations: int = 6, delay: float = 0.02) -> None:
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


def equip_dealer_and_variant(app: BlackjackApp, character_id: str, variant_id: str, theme: str) -> None:
    app.save_manager.data.equipped_costume = variant_id
    app.dealer_actor.equip_costume(character_id, costume_id=variant_id)
    app.dealer_stage_canvas.set_theme(theme)
    img = app._get_scaled_dealer_photo() or app.dealer_actor.get_photo_image()
    if img:
        app.dealer_stage_canvas.set_dealer_image(img)
    profile = app.dealer_actor.get_profile()
    if hasattr(app, "dealer_nameplate_label"):
        app.dealer_nameplate_label.configure(text=profile.title, fg=profile.nameplate_fg)
    app._sync_dealer_stage_colors(profile.speech_bg)


def save_animated_gif(frames: list[Image.Image], out_path: Path, target_w: int = 760, duration_ms: int = 260) -> None:
    resized_frames: list[Image.Image] = []
    for f in frames:
        scale = target_w / f.width
        target_h = int(f.height * scale)
        rf = f.resize((target_w, target_h), Image.Resampling.LANCZOS).convert(
            "P", palette=Image.Palette.ADAPTIVE
        )
        resized_frames.append(rf)

    resized_frames[0].save(
        out_path,
        save_all=True,
        append_images=resized_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True,
    )
    print(f"Saved {out_path} ({out_path.stat().st_size / 1024 / 1024:.2f} MB)")


def capture_all() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    out_dir = BASE_DIR / "docs" / "release" / "screenshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    bootcamp_gif_path = BASE_DIR / "docs" / "release" / "gameplay_card_counting_bootcamp.gif"
    table_gif_path = BASE_DIR / "docs" / "release" / "gameplay_3seat_card_counting.gif"

    temp_dir = tempfile.TemporaryDirectory()
    save_file = Path(temp_dir.name) / "release_save_v2.json"

    root = tkinter.Tk()
    root.title(f"Blackjack v{__version__}")
    root.geometry("1000x740+50+40")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    app = BlackjackApp(root, chips_mode=True, sound_enabled=False, save_path=save_file, skip_splash=True)
    sm = app.save_manager
    sm.data.unlocked_costumes = [
        "classic", "julian", "tiffany", "mortimer", "malphas",
        "uriel", "selene", "vladimir", "professor", "pit_fiend",
    ]
    sm.data.highscores.peak_bankroll = 24500
    sm.data.highscores.total_hands_played = 186
    sm.data.highscores.total_hands_won = 104
    sm.data.highscores.total_blackjacks = 29
    sm.data.highscores.best_counting_streak = 24
    sm.data.highscores.counting_streak = 14
    sm.data.achievements.exorcist = True
    sm.data.achievements.celestial = True
    sm.data.achievements.high_roller = True
    sm.data.achievements.apprentice_counter = True
    sm.data.achievements.master_counter = True
    sm.data.achievements.pair_perfectionist = True
    sm.data.achievements.poker_face = True

    # Populate realistic Bootcamp progress for the Curriculum Map
    sm.mark_bootcamp_intro_seen()
    sm.record_bootcamp_lecture("L1")
    sm.record_bootcamp_stage("C1", "S", 100.0, 10120)
    sm.record_bootcamp_lecture("L2A")
    sm.record_bootcamp_stage("C2A", "A", 92.0, 9240)
    sm.record_bootcamp_lecture("L2B")
    sm.record_bootcamp_stage("C2B", "S", 100.0, 10080)
    sm.record_bootcamp_lecture("L3A")
    sm.record_bootcamp_stage("C3A", "A", 90.0, 9050)
    sm.record_bootcamp_lecture("L4")
    sm.record_bootcamp_stage("C4", "B", 83.3, 8330)
    sm.record_bootcamp_lecture("L5")

    bootcamp_frames: list[Image.Image] = []

    # =========================================================================
    # 1. MIT Hi-Lo Curriculum Map (01_bootcamp_curriculum_map.png)
    # =========================================================================
    print("[1/10] Capturing 01_bootcamp_curriculum_map.png...")
    app.enter_counting_bootcamp(start_view="map")
    bf = app.bootcamp_frame
    assert bf is not None
    bf.focused_node_id = "L3A"
    bf.render_dag_map_view()
    equip_dealer_and_variant(app, "professor", "professor", "academy")
    app.set_dealer_speech(
        "Welcome to the MIT Hi-Lo Curriculum Map! Complete Show & Tell Lectures and earn S-Rank Casino Chip Medallions.",
        stream=False,
    )
    pump(root, 10)
    img_map = capture_hwnd_to_image(root.winfo_id())
    img_map.save(out_dir / "01_bootcamp_curriculum_map.png")
    for _ in range(5):
        bootcamp_frames.append(img_map)

    # =========================================================================
    # 2. Interactive Show & Tell Lecture — 5-Card Seat Grouping (02_bootcamp_lecture_table_sweep.png)
    # =========================================================================
    print("[2/10] Capturing 02_bootcamp_lecture_table_sweep.png...")
    bf.render_lecture_view("L3A", slide_index=2)
    equip_dealer_and_variant(app, "mortimer", "mortimer_pirate", "crypt")
    app.set_dealer_speech(
        "Sweep this mini table: Seat 1 [J, 6], Seat 2 [8, 9], Dealer Upcard [5]. What is the table delta?",
        stream=False,
    )
    pump(root, 10)
    img_lec = capture_hwnd_to_image(root.winfo_id())
    img_lec.save(out_dir / "02_bootcamp_lecture_table_sweep.png")
    for _ in range(5):
        bootcamp_frames.append(img_lec)

    # Submit practice answer on L3A Slide 3 for the animated GIF
    bf.submit_lecture_practice("+1")
    app.set_dealer_speech(
        "Bravo! Seat 1 [J, 6] cancels to 0, Seat 2 [8, 9] are neutral (0), leaving Dealer [5] = +1!",
        stream=False,
    )
    pump(root, 8)
    img_lec_ok = capture_hwnd_to_image(root.winfo_id())
    for _ in range(4):
        bootcamp_frames.append(img_lec_ok)

    # =========================================================================
    # 3. Timed Challenge Drill — C3A Table Sweep & C4 Shoe Calibration (03_bootcamp_challenge_drill.png)
    # =========================================================================
    print("[3/10] Capturing 03_bootcamp_challenge_drill.png...")
    bf.render_challenge_view("C3A", seed=7)
    equip_dealer_and_variant(app, "professor", "professor_vegas_disguise", "academy")
    app.set_dealer_speech(
        "Scan right-to-left across Seat 1, Seat 2, and the Dealer Upcard — cancel opposing pairs!",
        stream=False,
    )
    pump(root, 10)
    img_c3a = capture_hwnd_to_image(root.winfo_id())
    img_c3a.save(out_dir / "03_bootcamp_challenge_drill.png")
    for _ in range(5):
        bootcamp_frames.append(img_c3a)

    # Answer C3A prompt for animated GIF feedback plaque
    p_c3a = bf.active_session.get_current_prompt()
    bf.submit_challenge_answer(p_c3a.correct_answer)
    bf.cancel_all_timers()
    app.set_dealer_speech(f"Sharp! {p_c3a.explanation}", stream=False)
    pump(root, 8)
    img_c3a_ok = capture_hwnd_to_image(root.winfo_id())
    for _ in range(4):
        bootcamp_frames.append(img_c3a_ok)

    # Also capture C4 Shoe Calibration & C5 Final Exam frames for the Bootcamp GIF
    bf.render_challenge_view("C4", seed=42)
    equip_dealer_and_variant(app, "professor", "professor_sherlock", "academy")
    app.set_dealer_speech(
        "6-Deck Shoe Calibration: divide your Running Count (+6) by 3.0 Decks Remaining for True Count +2.0!",
        stream=False,
    )
    pump(root, 8)
    img_c4 = capture_hwnd_to_image(root.winfo_id())
    for _ in range(5):
        bootcamp_frames.append(img_c4)

    bf.render_challenge_view("C5", seed=42)
    bf.active_session.current_index = 4  # RC +8, 2.0 Decks -> TC +4.0 -> 8 Units ($200)
    bf.active_session.streak = 9
    bf.active_session.correct_count = 4
    bf._render_current_challenge_prompt()
    equip_dealer_and_variant(app, "professor", "professor_dean", "academy")
    app.set_dealer_speech(
        "Final Exam! Running Count is +8 with 2.0 decks left (TC +4.0). Fire the 8-Unit ($200) MIT attack bet!",
        stream=False,
    )
    pump(root, 8)
    img_c5 = capture_hwnd_to_image(root.winfo_id())
    for _ in range(5):
        bootcamp_frames.append(img_c5)

    # =========================================================================
    # 4. Pit Boss Evaluation Report Card — S-Rank Medallion (04_bootcamp_report_card.png)
    # =========================================================================
    print("[4/10] Capturing 04_bootcamp_report_card.png...")
    bf.render_report_card_view(
        summary={
            "stage_id": "C5",
            "title": "C5: Final Exam",
            "grade": "S",
            "passed": True,
            "correct_count": 10,
            "total_prompts": 10,
            "accuracy_pct": 100.0,
            "avg_response_ms": 1840.0,
            "par_ms": 5000.0,
            "best_streak": 10,
            "score": 10316,
        },
        unlock_res={"newly_unlocked": ["professor"]},
    )
    equip_dealer_and_variant(app, "professor", "professor", "academy")
    app.set_dealer_speech(
        "Grade S — 100% accuracy! You've graduated from the MIT Hi-Lo Card Counting Academy!",
        stream=False,
    )
    pump(root, 10)
    img_rc = capture_hwnd_to_image(root.winfo_id())
    img_rc.save(out_dir / "04_bootcamp_report_card.png")
    for _ in range(6):
        bootcamp_frames.append(img_rc)

    # Exit Bootcamp to 3-Seat Training Free Play
    app.exit_counting_bootcamp_to_free_play()
    pump(root, 6)

    # =========================================================================
    # 5. Dealer Wardrobe & 35 Bespoke Costumes (05_dealer_wardrobe_costumes.png)
    # =========================================================================
    print("[5/10] Capturing 05_dealer_wardrobe_costumes.png...")
    app._open_wardrobe_dialog(initial_tab=0)
    pump(root, 10)
    wardrobe_dlg = app._wardrobe_dialog
    # Select bespoke variants on dealers in the wardrobe so the screenshot highlights the new costumes
    for cid, target_idx in (("julian", 1), ("tiffany", 8), ("mortimer", 4), ("malphas", 4), ("uriel", 4), ("selene", 5)):
        if cid in wardrobe_dlg.cards:
            pnl = wardrobe_dlg.cards[cid].get("panel")
            if pnl is not None and hasattr(pnl, "_update_costume_display"):
                pnl.costume_idx = min(target_idx, max(0, len(pnl.costumes) - 1))
                pnl._update_costume_display()
    pump(root, 10)
    img_wardrobe_t1 = capture_hwnd_to_image(wardrobe_dlg.winfo_id())
    img_wardrobe_t1.save(out_dir / "05_dealer_wardrobe_costumes.png")
    wardrobe_dlg.destroy()
    app._wardrobe_dialog = None
    pump(root, 5)

    # =========================================================================
    # 6. 3-Seat Training Mode with Selene (Cyber Kunoichi) & Cyber Backdrop
    # =========================================================================
    print("[6/10] Capturing 06_3seat_training_mode.png...")
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
    app.card_counter.running_count = 6
    app.card_counting_hud.update_counts(cards_remaining=156, base_bet=25)
    equip_dealer_and_variant(app, "selene", "selene_kunoichi", "cyber")
    app.set_dealer_speech(
        "True Count is +2.0 on the 3-seat training table. Scale your wagers or click [Bootcamp] to drill!",
        stream=False,
    )
    pump(root, 10)
    img_3seat_train = capture_hwnd_to_image(root.winfo_id())
    img_3seat_train.save(out_dir / "06_3seat_training_mode.png")
    img_3seat_train.save(out_dir / "01_3seat_training_mode.png")
    for _ in range(5):
        bootcamp_frames.append(img_3seat_train)

    # Save the Bootcamp animated GIF!
    print(f"Saving {bootcamp_gif_path.name} ({len(bootcamp_frames)} frames)...")
    save_animated_gif(bootcamp_frames, bootcamp_gif_path, target_w=760, duration_ms=280)

    # =========================================================================
    # 7. 3-Seat In-Play with Tiffany (Femme Fatale Noir) & Casino Backdrop
    # =========================================================================
    print("[7/10] Capturing 07_3seat_in_play.png...")
    equip_dealer_and_variant(app, "tiffany", "tiffany_noir", "casino")
    c_s1_1 = build_card_helper(app, "10", "spades")
    c_s2_1 = build_card_helper(app, "6", "hearts")
    c_s3_1 = build_card_helper(app, "9", "diamonds")
    c_dl_1 = build_card_helper(app, "6", "clubs")
    c_s1_2 = build_card_helper(app, "8", "clubs")
    c_s2_2 = build_card_helper(app, "5", "diamonds")
    c_s3_2 = build_card_helper(app, "10", "hearts")
    c_dl_2 = build_card_helper(app, "10", "spades")
    c_s2_hit = build_card_helper(app, "10", "clubs")
    c_dl_bust = build_card_helper(app, "10", "diamonds")

    app.deck = [c_dl_bust, c_s2_hit, c_dl_2, c_s3_2, c_s2_2, c_s1_2, c_dl_1, c_s3_1, c_s2_1, c_s1_1]
    app._deal_hand_with_bet()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    pump(root, 5)
    app.on_stand()
    pump(root, 10)
    app.card_counting_hud.update_counts(cards_remaining=148, base_bet=25)
    app.set_dealer_speech("Seat 2 shows 11 against my 6, darling. Textbook Double Down!", stream=False)
    pump(root, 10)
    img_3seat_play = capture_hwnd_to_image(root.winfo_id())
    img_3seat_play.save(out_dir / "07_3seat_in_play.png")
    img_3seat_play.save(out_dir / "02_3seat_in_play.png")

    # =========================================================================
    # 8. Single-Seat Casino with Count Vladimir (Alucard) & Creep Backdrop
    # =========================================================================
    print("[8/10] Capturing 08_single_seat_casino.png...")
    app.set_table_seats(1)
    if app.card_counting_hud.is_visible:
        app._toggle_card_counting_hud()
    app._clear_bet()
    app._add_chip_bet(100)
    equip_dealer_and_variant(app, "vladimir", "vladimir_alucard", "creep")

    c1 = build_card_helper(app, "ace", "spades")
    c2 = build_card_helper(app, "king", "hearts")
    d1 = build_card_helper(app, "9", "diamonds")
    d2 = build_card_helper(app, "7", "clubs")
    app.deck = [d2, c2, d1, c1]
    app._deal_hand_with_bet()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    equip_dealer_and_variant(app, "vladimir", "vladimir_alucard", "creep")
    app.set_dealer_speech("A Soft 20 under the blood moon! Standing against my King is the wise play.", stream=False)
    pump(root, 10)
    img_1seat = capture_hwnd_to_image(root.winfo_id())
    img_1seat.save(out_dir / "08_single_seat_casino.png")
    img_1seat.save(out_dir / "03_single_seat_casino.png")

    # =========================================================================
    # 9. Wardrobe Hall of Fame & Career Telemetry (09_wardrobe_hall_of_fame.png)
    # =========================================================================
    print("[9/10] Capturing 09_wardrobe_hall_of_fame.png...")
    app._open_wardrobe_dialog(initial_tab=1)
    pump(root, 10)
    wardrobe_dlg = app._wardrobe_dialog
    img_hof = capture_hwnd_to_image(wardrobe_dlg.winfo_id())
    img_hof.save(out_dir / "09_wardrobe_hall_of_fame.png")
    img_hof.save(out_dir / "04_wardrobe_hall_of_fame.png")
    wardrobe_dlg.destroy()
    app._wardrobe_dialog = None
    pump(root, 5)

    # =========================================================================
    # 10. Hell's Table Showdown with Malphas (Cinder-Lord) & Hell Backdrop
    # =========================================================================
    print("[10/10] Capturing 10_hells_table_pit_fiend.png & 06_keyboard_shortcuts_help.png...")
    app.set_table_seats(1)
    app.suppress_mode_dialog = True
    app._trigger_hell_table()
    c_inf1 = build_card_helper(app, "ace", "spades")
    c_inf2 = build_card_helper(app, "king", "hearts")
    d_inf1 = build_card_helper(app, "ace", "clubs")
    d_inf2 = build_card_helper(app, "10", "diamonds")
    app.deck = [d_inf2, c_inf2, d_inf1, c_inf1]
    app._deal_hand_with_bet()
    while getattr(app, "_dealing", False):
        pump(root, 2, delay=0.01)
    equip_dealer_and_variant(app, "malphas", "malphas_warlord", "hell")
    app.set_dealer_speech(
        "Welcome to the Abyssal Wager! Your petty chips mean nothing—only your Soul remains.",
        stream=False,
    )
    pump(root, 10)
    img_hell = capture_hwnd_to_image(root.winfo_id())
    img_hell.save(out_dir / "10_hells_table_pit_fiend.png")
    img_hell.save(out_dir / "05_hells_table_pit_fiend.png")

    # Keyboard Shortcuts overlay
    app.haunted.phase = Phase.NORMAL
    app._apply_phase_theme(Phase.NORMAL)
    app._show_shortcuts_overlay()
    pump(root, 10)
    shortcuts_dlg = app._shortcuts_dialog
    img_shortcuts = capture_hwnd_to_image(shortcuts_dlg.winfo_id())
    img_shortcuts.save(out_dir / "06_keyboard_shortcuts_help.png")
    shortcuts_dlg.destroy()
    app._shortcuts_dialog = None
    pump(root, 5)

    # Also update gameplay_3seat_card_counting.gif with the new v2.0.0 Bootcamp + 3-Seat sequence
    save_animated_gif(bootcamp_frames, table_gif_path, target_w=760, duration_ms=280)

    app._on_close()
    temp_dir.cleanup()
    print("Done! All v2.0.0 release screenshots and animated GIFs captured successfully.")


if __name__ == "__main__":
    capture_all()
