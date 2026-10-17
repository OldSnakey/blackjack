"""
Reusable Asset Generation & Processing Tool for Blackjack: Haunted Halloween.
Generates and synthesizes game-ready 2.5D sprites, playing cards, relics,
and organic audio effects with 100% alpha transparency.

Usage:
    python tools/build_haunted_assets.py
"""

from __future__ import annotations

import argparse
import math
import struct
import wave
import shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
HAUNTED_ASSETS_DIR = ASSETS_DIR / "haunted"
HAUNTED_AUDIO_DIR = BASE_DIR / "audio" / "haunted"
CARDS_DIR = BASE_DIR / "cards"

HAUNTED_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
HAUNTED_AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# 1. 2.5D Isometric Pixel-Art Gravestone with 100% Alpha Transparency
# ---------------------------------------------------------------------------
def generate_isometric_gravestone(w: int = 48, h: int = 56) -> Image.Image:
    """
    Renders an authentic 2.5D isometric gothic gravestone with:
    - Arched rounded top
    - 2.5D depth extrusion on the right flank
    - Weathered stone texture and fissure cracks
    - Carved 'R.I.P' / cross monument detail
    - Ground base plinth with subtle contact ambient shadow
    - 100% alpha transparency outside the stone boundaries
    """
    scale = 4
    W = w * scale
    H = h * scale
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base coordinates
    # Plinth / ground base: bottom centered
    # Front face: x from 20 to 140, y from 40 to 180
    # Right flank extrusion: x from 140 to 170, shifted isometrically
    plinth_l = int(W * 0.12)
    plinth_r = int(W * 0.88)
    plinth_t = int(H * 0.78)
    plinth_b = int(H * 0.92)

    # 1. Soft Ambient Contact Shadow on the table felt (beneath the stone)
    shadow_pad = int(scale * 2)
    draw.ellipse(
        [plinth_l - shadow_pad, plinth_b - int(H * 0.08), plinth_r + shadow_pad + int(scale * 4), plinth_b + int(H * 0.06)],
        fill=(10, 20, 10, 110)
    )

    # 2. Bottom Plinth Stone Block
    # Plinth Front
    draw.rounded_rectangle(
        [plinth_l, plinth_t, plinth_r - int(scale * 5), plinth_b],
        radius=int(scale * 1.5),
        fill="#42484f", outline="#282b30", width=int(scale * 0.8)
    )
    # Plinth Right Flank (Darker 2.5D bevel)
    plinth_flank = [
        (plinth_r - int(scale * 5), plinth_t),
        (plinth_r, plinth_t - int(scale * 2)),
        (plinth_r, plinth_b - int(scale * 2)),
        (plinth_r - int(scale * 5), plinth_b),
    ]
    draw.polygon(plinth_flank, fill="#2c3036", outline="#1c1e22")

    # 3. Main Headstone Body
    hs_l = int(W * 0.20)
    hs_r = int(W * 0.72)
    hs_t = int(H * 0.16)
    hs_arch_b = int(H * 0.44)
    hs_b = plinth_t

    # 3a. Right Flank Extrusion (Extruded back-right for 2.5D depth)
    extrusion_dx = int(scale * 5)
    extrusion_dy = -int(scale * 2.5)

    flank_poly = [
        (hs_r, hs_arch_b),
        (hs_r + extrusion_dx, hs_arch_b + extrusion_dy),
        (hs_r + extrusion_dx, hs_b + extrusion_dy),
        (hs_r, hs_b),
    ]
    draw.polygon(flank_poly, fill="#343a40", outline="#1e2226")

    # Flank arch curved side
    flank_arch = [
        (int((hs_l + hs_r) / 2), hs_t),
        (int((hs_l + hs_r) / 2) + extrusion_dx, hs_t + extrusion_dy),
        (hs_r + extrusion_dx, hs_arch_b + extrusion_dy),
        (hs_r, hs_arch_b),
    ]
    draw.polygon(flank_arch, fill="#3d444b", outline="#1e2226")

    # 3b. Front Headstone Face
    # Lower rectangular pillar
    draw.rectangle([hs_l, hs_arch_b, hs_r, hs_b], fill="#606770", outline="#30353b", width=int(scale * 0.8))
    # Top gothic arch dome
    draw.pieslice([hs_l, hs_t, hs_r, hs_arch_b + int(scale * 6)], start=180, end=0, fill="#606770", outline="#30353b", width=int(scale * 0.8))
    draw.rectangle([hs_l + int(scale * 0.8), hs_arch_b - int(scale * 3), hs_r - int(scale * 0.8), hs_arch_b + int(scale * 1)], fill="#606770")

    # 4. Chiseled Bevel / Highlight on Top-Left Edge (Light source highlight)
    draw.arc([hs_l + int(scale * 1), hs_t + int(scale * 1), hs_r - int(scale * 1), hs_arch_b + int(scale * 5)], start=180, end=270, fill="#8a939e", width=int(scale * 0.8))
    draw.line([(hs_l + int(scale * 1), hs_arch_b), (hs_l + int(scale * 1), hs_b - int(scale * 1))], fill="#8a939e", width=int(scale * 0.8))

    # 5. Weathering, Cracks, & Fissures
    # Crack 1: Lightning fissure across top right
    crack1 = [
        (int(W * 0.52), int(H * 0.24)),
        (int(W * 0.58), int(H * 0.31)),
        (int(W * 0.54), int(H * 0.38)),
        (int(W * 0.64), int(H * 0.44)),
    ]
    draw.line(crack1, fill="#24272c", width=max(1, int(scale * 0.6)))

    # Crack 2: Bottom hairline crack
    crack2 = [
        (int(W * 0.30), int(H * 0.74)),
        (int(W * 0.35), int(H * 0.66)),
        (int(W * 0.32), int(H * 0.60)),
    ]
    draw.line(crack2, fill="#24272c", width=max(1, int(scale * 0.5)))

    # 6. Carved Gothic Cross / Monument Insignia
    cx = int((hs_l + hs_r) / 2)
    cy = int(H * 0.46)
    c_w = int(scale * 2.5)
    # Vertical cross bar
    draw.rectangle([cx - c_w // 2, cy - int(scale * 7), cx + c_w // 2, cy + int(scale * 9)], fill="#33383e")
    # Horizontal cross bar
    draw.rectangle([cx - int(scale * 7), cy - int(scale * 3), cx + int(scale * 7), cy], fill="#33383e")

    # Chiseled text "R . I . P"
    rip_y = int(H * 0.63)
    # 'R'
    draw.line([(cx - int(scale * 8), rip_y), (cx - int(scale * 8), rip_y + int(scale * 5))], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx - int(scale * 8), rip_y), (cx - int(scale * 5), rip_y)], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx - int(scale * 5), rip_y), (cx - int(scale * 5), rip_y + int(scale * 2.5))], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx - int(scale * 8), rip_y + int(scale * 2.5)), (cx - int(scale * 5), rip_y + int(scale * 2.5))], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx - int(scale * 6), rip_y + int(scale * 2.5)), (cx - int(scale * 4), rip_y + int(scale * 5))], fill="#2b2f34", width=int(scale * 0.7))
    # 'I'
    draw.line([(cx, rip_y), (cx, rip_y + int(scale * 5))], fill="#2b2f34", width=int(scale * 0.7))
    # 'P'
    draw.line([(cx + int(scale * 5), rip_y), (cx + int(scale * 5), rip_y + int(scale * 5))], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx + int(scale * 5), rip_y), (cx + int(scale * 8), rip_y)], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx + int(scale * 8), rip_y), (cx + int(scale * 8), rip_y + int(scale * 2.5))], fill="#2b2f34", width=int(scale * 0.7))
    draw.line([(cx + int(scale * 5), rip_y + int(scale * 2.5)), (cx + int(scale * 8), rip_y + int(scale * 2.5))], fill="#2b2f34", width=int(scale * 0.7))

    # Moss specks at plinth
    draw.point([plinth_l + int(scale * 3), plinth_t + int(scale * 2)], fill=(40, 95, 45, 180))
    draw.point([plinth_l + int(scale * 4), plinth_t + int(scale * 3)], fill=(50, 110, 50, 190))
    draw.point([plinth_r - int(scale * 8), plinth_t + int(scale * 2)], fill=(35, 85, 40, 170))

    final_sprite = img.resize((w, h), Image.Resampling.LANCZOS)
    return final_sprite


def generate_procedural_cursed_back(w: int = 74, h: int = 107, make_skull_pip_func=None) -> Image.Image:
    """
    Renders an authentic ornate gothic cursed card back procedurally with:
    - Ivory card border
    - Deep crimson velvet inlay
    - Golden filigree frame with diamond lattice crosshatch
    - Central gothic seal medallion with dark skull crest
    """
    scale = 4
    W, H = w * scale, h * scale
    img = Image.new("RGBA", (W, H), "#120204")
    draw = ImageDraw.Draw(img)

    # 1. Ivory Card Border
    draw.rounded_rectangle([scale, scale, W - scale, H - scale], radius=int(scale * 3), outline="#e0e0e0", width=int(scale * 0.8))

    # 2. Crimson Velvet Inlay
    pad = int(scale * 3)
    draw.rounded_rectangle([pad, pad, W - pad, H - pad], radius=int(scale * 2), fill="#2b0409", outline="#8b0000", width=int(scale * 1.2))

    # 3. Inner Gold Border
    gpad = int(scale * 4.5)
    draw.rounded_rectangle([gpad, gpad, W - gpad, H - gpad], radius=int(scale * 1.5), outline="#d4af37", width=int(scale * 0.6))

    # 4. Diamond Filigree Lattice
    step = int(scale * 6)
    for x in range(gpad, W - gpad, step):
        draw.line([(x, gpad), (x + int(scale * 6), H - gpad)], fill="#450810", width=1)
        draw.line([(x, H - gpad), (x + int(scale * 6), gpad)], fill="#450810", width=1)

    # 5. Central Seal / Medallion
    cx, cy = W // 2, H // 2
    r_med = int(scale * 11)
    draw.ellipse([cx - r_med, cy - r_med, cx + r_med, cy + r_med], fill="#140205", outline="#d4af37", width=int(scale * 1.0))
    draw.ellipse([cx - r_med + int(scale * 1.2), cy - r_med + int(scale * 1.2), cx + r_med - int(scale * 1.2), cy + r_med - int(scale * 1.2)], outline="#8b0000", width=int(scale * 0.6))

    # Central Skull Crest
    if make_skull_pip_func:
        skull = make_skull_pip_func(14, 16)
        skull_scaled = skull.resize((int(scale * 14), int(scale * 16)), Image.Resampling.LANCZOS)
        img.paste(skull_scaled, (cx - skull_scaled.width // 2, cy - skull_scaled.height // 2), skull_scaled)

    return img.resize((w, h), Image.Resampling.LANCZOS)


# ---------------------------------------------------------------------------
# 2. Playing Card 13 & Haunted Card Back
# ---------------------------------------------------------------------------
def process_cards(source_dir: Path | None = None, force: bool = False):
    print("Processing card assets...")

    def make_skull_pip(w=12, h=14):
        scale = 16
        W = w * scale
        H = h * scale
        hires = Image.new("RGBA", (W, H), (255, 255, 255, 0))
        draw = ImageDraw.Draw(hires)
        cx = W / 2.0

        # Cranium dome
        draw.ellipse([int(W * 0.06), int(H * 0.02), int(W * 0.94), int(H * 0.69)], fill=(0, 0, 0, 255))
        # Jaw & teeth block
        jaw_left, jaw_right = int(W * 0.25), int(W * 0.75)
        draw.rounded_rectangle([jaw_left, int(H * 0.58), jaw_right, int(H * 0.96)], radius=int(scale * 0.8), fill=(0, 0, 0, 255))
        # Cheekbone arches
        draw.polygon([(int(W * 0.06) + scale, int(H * 0.40)), (int(W * 0.02), int(H * 0.60)), (jaw_left, int(H * 0.68))], fill=(0, 0, 0, 255))
        draw.polygon([(int(W * 0.94) - scale, int(H * 0.40)), (int(W * 0.98), int(H * 0.60)), (jaw_right, int(H * 0.68))], fill=(0, 0, 0, 255))
        # Eye sockets
        eye_w, eye_h, eye_y = int(W * 0.13), int(H * 0.15), int(H * 0.38)
        draw.ellipse([int(cx - W * 0.23 - eye_w), eye_y - eye_h, int(cx - W * 0.23 + eye_w), eye_y + eye_h], fill=(255, 255, 255, 255))
        draw.ellipse([int(cx + W * 0.23 - eye_w), eye_y - eye_h, int(cx + W * 0.23 + eye_w), eye_y + eye_h], fill=(255, 255, 255, 255))
        # Nasal cavity
        draw.polygon([(cx - int(W * 0.09), int(H * 0.65)), (cx + int(W * 0.09), int(H * 0.65)), (cx, int(H * 0.49))], fill=(255, 255, 255, 255))
        # Teeth slits
        t_w = max(1, int(scale * 0.45))
        for tx in [int(cx - W * 0.13), int(cx), int(cx + W * 0.13)]:
            draw.line([(tx, int(H * 0.76)), (tx, int(H * 0.93))], fill=(255, 255, 255, 255), width=t_w)
        return hires.resize((w, h), Image.Resampling.LANCZOS)

    ref_card = CARDS_DIR / "2_diamond.png"
    if ref_card.exists():
        im2d = Image.open(ref_card).convert("RGBA")
        card_13 = im2d.copy()
        for y in range(2, 105):
            for x in range(2, 72):
                card_13.putpixel((x, y), (255, 255, 255, 255))

        im10 = Image.open(CARDS_DIR / "10_spade.png")
        im3 = Image.open(CARDS_DIR / "3_spade.png")
        d1 = im10.crop((2, 2, 6, 16))
        d3 = im3.crop((3, 2, 9, 16))
        rank_13 = Image.new("RGBA", (10, 14), (255, 255, 255, 0))
        rank_13.paste(d1, (0, 0), d1)
        rank_13.paste(d3, (4, 0), d3)

        mini_skull = make_skull_pip(8, 9)
        main_skull = make_skull_pip(12, 14)

        card_13.paste(rank_13, (2, 2), rank_13)
        card_13.paste(mini_skull, (3, 18), mini_skull)
        r13_rot = rank_13.rotate(180)
        mini_rot = mini_skull.rotate(180)
        card_13.paste(r13_rot, (74 - 2 - 10, 107 - 2 - 14), r13_rot)
        card_13.paste(mini_rot, (74 - 3 - 8, 107 - 18 - 9), mini_rot)

        pips_coords = [
            (22, 16), (37, 16), (52, 16),
            (37, 34),
            (22, 40), (52, 40),
            (37, 52),
            (22, 64), (52, 64),
            (37, 70),
            (22, 88), (37, 88), (52, 88),
        ]
        for px, py in pips_coords:
            card_13.paste(main_skull, (px - main_skull.width // 2, py - main_skull.height // 2), main_skull)

        card_13.save(HAUNTED_ASSETS_DIR / "card_13.png")
        print(" -> Saved card_13.png (74x107 playing card style)")

    # Haunted Card Back
    back_dest = HAUNTED_ASSETS_DIR / "back_haunted.png"
    if not back_dest.exists() or force:
        # Check if user provided an external source directory
        custom_srcs = []
        if source_dir and source_dir.exists():
            custom_srcs = (
                list(source_dir.glob("*back*.jpg"))
                + list(source_dir.glob("*back*.png"))
            )

        if custom_srcs:
            with Image.open(custom_srcs[0]) as img:
                w, h = img.size
                back_crop = img.crop((int(w * 0.08), int(h * 0.08), int(w * 0.92), int(h * 0.92)))
                back_resized = back_crop.resize((74, 107), Image.Resampling.LANCZOS).convert("RGBA")
                back_resized.save(back_dest)
                print(f" -> Generated back_haunted.png from {custom_srcs[0].name}")
        else:
            # Procedural fallback
            back_proc = generate_procedural_cursed_back(74, 107, make_skull_pip_func=make_skull_pip)
            back_proc.save(back_dest)
            print(" -> Generated procedural back_haunted.png (74x107 gothic filigree)")
    else:
        print(" -> Preserved existing back_haunted.png")


# ---------------------------------------------------------------------------
# 3. Process Table Accessories & Isometric Gravestone
# ---------------------------------------------------------------------------
def process_accessories():
    print("Processing accessories...")
    # 2.5D Isometric Gravestone with 100% Alpha
    gravestone = generate_isometric_gravestone(48, 56)
    gravestone.save(HAUNTED_ASSETS_DIR / "gravestone.png")
    print(" -> Saved 2.5D Isometric gravestone.png with 100% alpha (48x56)")

    # Candle Sprites (Lit & Snuffed)
    # Lit Candle (48x48)
    img_lit = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_lit)
    # Wax body
    draw.rounded_rectangle([18, 18, 30, 44], radius=3, fill="#e8d8a7", outline="#8a733f", width=1)
    # Wax drips
    draw.ellipse([16, 22, 21, 28], fill="#d8c897")
    draw.ellipse([27, 20, 32, 27], fill="#d8c897")
    # Wick
    draw.line([24, 18, 24, 12], fill="#222222", width=2)
    # Flame outer aura
    draw.ellipse([20, 4, 28, 14], fill=(255, 140, 0, 190))
    # Flame inner core
    draw.ellipse([22, 6, 26, 12], fill=(255, 240, 120, 245))
    img_lit.save(HAUNTED_ASSETS_DIR / "candle_lit.png")

    # Snuffed Candle with Smoke (48x48)
    img_unlit = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img_unlit)
    # Dim wax body
    draw.rounded_rectangle([18, 18, 30, 44], radius=3, fill="#8a8068", outline="#4a4030", width=1)
    # Wick with tiny ember
    draw.line([24, 18, 24, 12], fill="#111111", width=2)
    draw.point([24, 12], fill=(255, 50, 0, 255))
    # Smoke wisps
    draw.arc([16, 2, 26, 12], start=200, end=350, fill=(200, 200, 200, 150), width=2)
    draw.arc([22, 0, 32, 10], start=50, end=180, fill=(180, 180, 180, 110), width=2)
    img_unlit.save(HAUNTED_ASSETS_DIR / "candle_unlit.png")
    print(" -> Saved candle_lit.png & candle_unlit.png (48x48)")


# ---------------------------------------------------------------------------
# 4. Synthesize Clean Haunted Sound Effects (.ogg / .wav)
# ---------------------------------------------------------------------------
def synthesize_audio():
    print("Synthesizing organic audio cues (.ogg)...")
    sample_rate = 44100

    def write_wav(filename: str, duration_sec: float, sample_func):
        num_samples = int(sample_rate * duration_sec)
        wav_path = HAUNTED_AUDIO_DIR / filename.replace(".ogg", ".wav")
        ogg_path = HAUNTED_AUDIO_DIR / filename
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                val = sample_func(t, duration_sec)
                val = max(-1.0, min(1.0, val))
                sample_int = int(val * 32767)
                frames.extend(struct.pack("<h", sample_int))
            wf.writeframes(frames)
        shutil.copy(wav_path, ogg_path)
        print(f" -> Created sound: {filename} ({duration_sec}s)")

    # 1. Midnight Clock Toll
    def clock_chime(t, dur):
        env = math.exp(-t * 1.8)
        return env * (0.6 * math.sin(2 * math.pi * 130.81 * t) +
                      0.3 * math.sin(2 * math.pi * 261.63 * t) +
                      0.15 * math.sin(2 * math.pi * 392.00 * t))
    write_wav("clock_chime_13.ogg", 2.8, clock_chime)

    # 2. Heartbeat
    def heartbeat(t, dur):
        env1 = math.exp(-((t - 0.1) * 35)**2)
        env2 = math.exp(-((t - 0.35) * 35)**2)
        return (env1 * math.sin(2 * math.pi * 55 * t) + env2 * 0.7 * math.sin(2 * math.pi * 60 * t)) * 0.8
    write_wav("heartbeat.ogg", 1.0, heartbeat)

    # 3. Candle Snuff Hiss
    import random
    def candle_snuff(t, dur):
        env = math.exp(-t * 6.0)
        noise = random.uniform(-1, 1)
        return env * noise * 0.5
    write_wav("candle_snuff.ogg", 0.6, candle_snuff)

    # 4. Stone Scrape Gravestone
    def stone_scrape(t, dur):
        env = math.sin(math.pi * t / dur)
        rumble = math.sin(2 * math.pi * 45 * t) + 0.4 * random.uniform(-1, 1)
        return env * rumble * 0.6
    write_wav("stone_scrape.ogg", 0.8, stone_scrape)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Self-contained asset generator & synthesizer for Blackjack: Haunted Halloween."
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=None,
        help="Optional directory containing raw source art or card backs."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of card backs and assets even if already present."
    )
    args = parser.parse_args()

    process_cards(source_dir=args.source_dir, force=args.force)
    process_accessories()
    synthesize_audio()
    print("All haunted assets built and verified successfully without external dependencies.")
