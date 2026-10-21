"""
Verification & Showcase Script for Tiffany Multi-Layer Puppet Actor System.
Demonstrates:
1. Exploded view of Tiffany's discrete sprite layers:
   (shadow, torso, neck, head, eyes, mouth, arms) and composite result.
2. Phonetic speech viseme states:
   (neutral, a, o, e, f, talk, smirk, gasp) with lip movements.
3. Arm articulation states:
   (rest, deal, peek).
4. Live Tkinter window capture of Tiffany puppet actor on stage with dynamic speech.
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
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dealer_actor import DealerActor
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
        w, h = 1000, 700

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


def generate_tiffany_layers_breakdown(artifact_dir: Path) -> Path:
    """Creates a side-by-side exploded visualization of all discrete Tiffany layers."""
    actor = DealerActor(master=None, initial_character="tiffany", scale_factor=2.0)
    actor.set_arm_state("rest")
    actor.set_eye_state("open")
    actor.set_mouth_state("a")

    layers = [
        ("1. Shadow", actor.get_layer_image("shadow")),
        ("2. Torso", actor.get_layer_image("torso")),
        ("3. Neck", actor.get_layer_image("neck")),
        ("4. Head", actor.get_layer_image("head")),
        ("5. Eyes (Open)", actor.get_layer_image("eyes_open")),
        ("6. Mouth (Viseme A)", actor.get_layer_image("mouth_a")),
        ("7. Arms (Rest)", actor.get_layer_image("arm_rest")),
        ("Composite Result", actor.get_composite_image())
    ]

    layer_w, layer_h = 224, 224
    pad = 20
    header_h = 70
    footer_h = 50
    total_w = len(layers) * (layer_w + pad) + pad
    total_h = layer_h + header_h + footer_h + 30

    canvas = Image.new("RGBA", (total_w, total_h), (20, 24, 36, 255))
    draw = ImageDraw.Draw(canvas)

    draw.text((pad, 15), "Tiffany Puppet Multi-Layer Discrete Rig: Exploded Layers Breakdown", fill=(240, 245, 255, 255))
    draw.text((pad, 40), "De-occluded torso, independent neck, blank face plate, animated eyes & mouth visemes, dynamic arms.", fill=(160, 175, 205, 255))

    for idx, (label, img) in enumerate(layers):
        x = pad + idx * (layer_w + pad)
        y = header_h + 10

        # Checkerboard background for alpha
        tile_size = 14
        for tx in range(0, layer_w, tile_size):
            for ty in range(0, layer_h, tile_size):
                color = (34, 40, 58) if ((tx // tile_size) + (ty // tile_size)) % 2 == 0 else (26, 30, 46)
                draw.rectangle([x + tx, y + ty, min(x + tx + tile_size, x + layer_w), min(y + ty + tile_size, y + layer_h)], fill=color)

        border_col = (255, 180, 100, 255) if idx == len(layers) - 1 else (65, 80, 115, 255)
        draw.rectangle([x - 2, y - 2, x + layer_w + 1, y + layer_h + 1], outline=border_col, width=2)

        if img:
            canvas.alpha_composite(img, (x, y))

        lbl_col = (255, 205, 140, 255) if idx == len(layers) - 1 else (220, 230, 245, 255)
        draw.text((x, y + layer_h + 8), label, fill=lbl_col)

    out_path = artifact_dir / "tiffany_puppet_exploded_layers_breakdown.png"
    canvas.convert("RGB").save(str(out_path), "PNG")
    print(f"SAVED: {out_path}")
    return out_path


def generate_tiffany_visemes_sheet(artifact_dir: Path) -> Path:
    """Generates a matrix showcasing all 8 phonetic visemes on Tiffany's face."""
    actor = DealerActor(master=None, initial_character="tiffany", scale_factor=2.0)
    actor.set_arm_state("rest")
    actor.set_eye_state("open")

    visemes = ["neutral", "a", "o", "e", "f", "talk", "smirk", "gasp"]
    sample_phonetics = {
        "neutral": "Silent / Rest (Subtle Closed)",
        "a": "'A', 'I', 'H' (Open Vowel)",
        "o": "'O', 'U', 'W' (Rounded O-Shape)",
        "e": "'E', 'Y', 'C' (Wide Smile E)",
        "f": "'F', 'V' (Tuck Lower Lip)",
        "talk": "Consonant Accent (Standard Talk)",
        "smirk": "Win / Tease (Subtle Smile)",
        "gasp": "Bust / High Risk (Shock O)"
    }

    tile_w, tile_h = 160, 160
    pad = 16
    cols = 4
    rows = 2

    total_w = cols * (tile_w + pad) + pad
    total_h = rows * (tile_h + 55 + pad) + 80

    canvas = Image.new("RGBA", (total_w, total_h), (20, 24, 36, 255))
    draw = ImageDraw.Draw(canvas)

    draw.text((pad, 15), "Tiffany Puppet Typewriter Phonetic Viseme Matrix", fill=(240, 245, 255, 255))
    draw.text((pad, 38), "Real-time typewriter dialogue articulation maps characters directly to specialized mouth shapes.", fill=(160, 175, 205, 255))

    for idx, v in enumerate(visemes):
        r = idx // cols
        c = idx % cols
        x = pad + c * (tile_w + pad)
        y = 70 + r * (tile_h + 55 + pad)

        tile_size = 10
        for tx in range(0, tile_w, tile_size):
            for ty in range(0, tile_h, tile_size):
                color = (34, 40, 58) if ((tx // tile_size) + (ty // tile_size)) % 2 == 0 else (26, 30, 46)
                draw.rectangle([x + tx, y + ty, min(x + tx + tile_size, x + tile_w), min(y + ty + tile_size, y + tile_h)], fill=color)

        draw.rectangle([x - 1, y - 1, x + tile_w, y + tile_h], outline=(70, 85, 120, 255), width=1)

        actor.set_mouth_state(v)
        comp = actor.get_composite_image()
        scaled = comp.resize((tile_w, tile_h), Image.Resampling.LANCZOS)
        canvas.alpha_composite(scaled, (x, y))

        draw.text((x, y + tile_h + 6), f"Viseme: '{v}'", fill=(255, 215, 130, 255))
        draw.text((x, y + tile_h + 24), sample_phonetics.get(v, ""), fill=(170, 185, 210, 255))

    out_path = artifact_dir / "tiffany_puppet_visemes_matrix.png"
    canvas.convert("RGB").save(str(out_path), "PNG")
    print(f"SAVED: {out_path}")
    return out_path


def generate_tiffany_arms_sheet(artifact_dir: Path) -> Path:
    """Generates a side-by-side sheet showing Tiffany's 3 arm articulation states."""
    actor = DealerActor(master=None, initial_character="tiffany", scale_factor=2.0)
    actor.set_eye_state("open")
    actor.set_mouth_state("smirk")

    arms = [
        ("Rest (Neutral Idle)", "rest"),
        ("Deal (Card Sweep)", "deal"),
        ("Peek (Hole Card Guard)", "peek"),
    ]

    tile_w, tile_h = 224, 224
    pad = 20
    header_h = 70
    footer_h = 45
    total_w = len(arms) * (tile_w + pad) + pad
    total_h = tile_h + header_h + footer_h

    canvas = Image.new("RGBA", (total_w, total_h), (20, 24, 36, 255))
    draw = ImageDraw.Draw(canvas)

    draw.text((pad, 15), "Tiffany Puppet Arm Articulation Rig", fill=(240, 245, 255, 255))
    draw.text((pad, 40), "Independent arm layer articulates based on game phase (table idle, dealing cards, hole card peek).", fill=(160, 175, 205, 255))

    for idx, (label, state) in enumerate(arms):
        x = pad + idx * (tile_w + pad)
        y = header_h + 10

        tile_size = 14
        for tx in range(0, tile_w, tile_size):
            for ty in range(0, tile_h, tile_size):
                color = (34, 40, 58) if ((tx // tile_size) + (ty // tile_size)) % 2 == 0 else (26, 30, 46)
                draw.rectangle([x + tx, y + ty, min(x + tx + tile_size, x + tile_w), min(y + ty + tile_size, y + tile_h)], fill=color)

        draw.rectangle([x - 1, y - 1, x + tile_w, y + tile_h], outline=(80, 100, 140, 255), width=2)

        actor.set_arm_state(state)
        comp = actor.get_composite_image()
        canvas.alpha_composite(comp, (x, y))

        draw.text((x, y + tile_h + 8), label, fill=(240, 220, 150, 255))

    out_path = artifact_dir / "tiffany_puppet_arms_matrix.png"
    canvas.convert("RGB").save(str(out_path), "PNG")
    print(f"SAVED: {out_path}")
    return out_path


def capture_tiffany_live_application(artifact_dir: Path) -> Path:
    """Launches BlackjackApp with Tiffany puppet equipped and takes an offscreen screenshot."""
    temp_dir = tempfile.TemporaryDirectory()
    save_file = Path(temp_dir.name) / "test_save.json"

    root = tkinter.Tk()
    root.title("Blackjack - Tiffany Puppet Multi-Layer Actor Live Verification")
    root.geometry("1100x820+50+50")
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    app = BlackjackApp(root, chips_mode=False, sound_enabled=False)
    app.save_manager = SaveManager(save_path=save_file)

    # Equip Tiffany puppet
    app.dealer_actor.equip_costume("tiffany")
    app._refresh_dealer_avatar_image()
    app.dealer_stage_canvas.set_theme("casino")

    # Stage dialogue showing viseme integration
    speech_text = "Welcome to my table, darling. Let's see if luck favors you tonight!"
    app.set_dealer_speech(speech_text, stream=False)

    for _ in range(30):
        root.update()
        time.sleep(0.02)

    hwnd = root.winfo_id()
    screenshot = capture_hwnd_to_image(hwnd)
    out_path = artifact_dir / "tiffany_puppet_live_stage_verification.png"
    screenshot.convert("RGB").save(str(out_path), "PNG")
    print(f"SAVED: {out_path}")

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

    return out_path


def main():
    artifact_dir = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\961dac34-d1bc-4f26-a9b9-15da0b316e33")
    artifact_dir.mkdir(parents=True, exist_ok=True)

    print("Generating Tiffany Exploded Layers Breakdown...")
    generate_tiffany_layers_breakdown(artifact_dir)

    print("Generating Tiffany Visemes Matrix...")
    generate_tiffany_visemes_sheet(artifact_dir)

    print("Generating Tiffany Arms Articulation Matrix...")
    generate_tiffany_arms_sheet(artifact_dir)

    print("Capturing Tiffany Live Window Application...")
    capture_tiffany_live_application(artifact_dir)
    print("ALL TIFFANY PUPPET VERIFICATION ARTIFACTS GENERATED SUCCESSFULLY.")


if __name__ == "__main__":
    main()
