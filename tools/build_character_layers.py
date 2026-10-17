"""
Layer decomposition and asset generator for high-fidelity graphic novel dealer characters.

Extracts transparent bust images and creates the 13 required layers for each of the 4 characters:
- Julian (The Classic Croupier)
- Malphas (The Pit Fiend)
- Uriel (The Celestial Seraph)
- Mortimer (Grim Bones)

Outputs 1x (112x112) and 2x (224x224) RGBA PNGs to assets/haunted/characters/<char_id>/
"""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

BRAIN_DIR = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\02743059-1d2a-482f-8223-b6e671bad578")
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "haunted" / "characters"

CHARACTERS_CONFIG = {
    "julian": {
        "source": BRAIN_DIR / "julian_nobg.png",
        "crop": (247, 10, 787, 550),
        "clean_table": False,
        "collar_y": 88,
        "eyes_box": (84, 34, 140, 54),
        "mouth_box": (94, 56, 130, 72),
        "arms_y": 165,
        "skin_color": (225, 185, 160),
        "ink_color": (28, 22, 22),
        # Precise eye pupil / sclera micro-boxes
        "eye_left_pupil": (96, 42, 104, 45),
        "eye_left_line": (95, 43, 105, 43),
        "eye_right_pupil": (121, 41, 128, 43),
        "eye_right_line": (120, 42, 129, 42),
        # Precise mouth coordinates
        "mouth_center": (112, 64),
        "mouth_y": 64,
        "mouth_x_span": (104, 122),
        "card_suit": "♦",
        "card_back": (160, 25, 35),
    },
    "malphas": {
        "source": BRAIN_DIR / "malphas_nobg.png",
        "crop": (12, 20, 1012, 1020),
        "clean_table": True,
        "collar_y": 82,
        "eyes_box": (84, 46, 140, 64),
        "mouth_box": (94, 65, 130, 81),
        "arms_y": 150,
        "skin_color": (45, 34, 36),
        "ink_color": (15, 10, 12),
        "eye_left_pupil": (96, 52, 104, 56),
        "eye_left_line": (95, 54, 105, 54),
        "eye_right_pupil": (120, 52, 128, 56),
        "eye_right_line": (119, 54, 129, 54),
        "mouth_center": (112, 73),
        "mouth_y": 73,
        "mouth_x_span": (104, 122),
        "card_suit": "☠",
        "card_back": (70, 15, 20),
    },
    "uriel": {
        "source": BRAIN_DIR / "uriel_nobg.png",
        "crop": (13, 20, 1013, 1020),
        "clean_table": False,
        "collar_y": 84,
        "eyes_box": (84, 46, 140, 64),
        "mouth_box": (94, 66, 130, 82),
        "arms_y": 152,
        "skin_color": (240, 218, 205),
        "ink_color": (25, 20, 22),
        "eye_left_pupil": (96, 51, 104, 55),
        "eye_left_line": (95, 53, 105, 53),
        "eye_right_pupil": (120, 51, 128, 55),
        "eye_right_line": (119, 53, 129, 53),
        "mouth_center": (112, 74),
        "mouth_y": 74,
        "mouth_x_span": (104, 122),
        "card_suit": "✨",
        "card_back": (20, 90, 140),
    },
    "mortimer": {
        "source": BRAIN_DIR / "mortimer_nobg.png",
        "crop": (18, 20, 1018, 1020),
        "clean_table": False,
        "collar_y": 88,
        "eyes_box": (84, 56, 140, 74),
        "mouth_box": (94, 72, 130, 88),
        "arms_y": 155,
        "skin_color": (225, 215, 190),
        "ink_color": (20, 15, 20),
        "eye_left_pupil": (94, 59, 104, 69),
        "eye_left_line": (94, 64, 104, 64),
        "eye_right_pupil": (120, 59, 130, 69),
        "eye_right_line": (120, 64, 130, 64),
        "mouth_center": (112, 80),
        "mouth_y": 80,
        "mouth_x_span": (104, 122),
        "card_suit": "♠",
        "card_back": (65, 25, 95),
    },
}

def create_feathered_mask(size: tuple[int, int], box: tuple[int, int, int, int], radius: float = 2.0) -> Image.Image:
    """Creates a smooth feathered alpha mask inside box."""
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle(box, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(radius=radius))

def generate_character_layers(char_id: str, cfg: dict):
    out_dir = ASSETS_DIR / char_id
    out_dir.mkdir(parents=True, exist_ok=True)

    src = Image.open(cfg["source"])
    bust_raw = src.crop(cfg["crop"])
    bust_2x = bust_raw.resize((224, 224), Image.Resampling.LANCZOS)

    # Clean up green table shelf on Malphas if configured
    if cfg.get("clean_table"):
        arr = np.array(bust_2x)
        # In rows 198..224: where pixels are green table (R < 65, G in 40..120, B < 70)
        is_green_felt = (arr[:, :, 0] < 65) & (arr[:, :, 1] > 40) & (arr[:, :, 1] > arr[:, :, 0] + 10) & (arr[:, :, 2] < 70)
        is_rail = (arr[:, :, 0] > 60) & (arr[:, :, 0] < 120) & (arr[:, :, 1] < 70) & (arr[:, :, 2] < 50)
        table_mask = np.zeros((224, 224), dtype=bool)
        table_mask[198:, :] = is_green_felt[198:, :] | is_rail[198:, :]
        # Keep card highlights
        is_card_or_hand = (arr[:, :, :3].mean(axis=2) > 130) | (arr[:, :, 0] > 110)
        table_mask = table_mask & (~is_card_or_hand)
        arr[table_mask, 3] = 0
        bust_2x = Image.fromarray(arr, mode="RGBA")

    bust_1x = bust_2x.resize((112, 112), Image.Resampling.LANCZOS)

    # Save bust
    bust_2x.save(out_dir / "bust_2x.png")
    bust_1x.save(out_dir / "bust.png")

    collar_y = cfg["collar_y"]
    eyes_box = cfg["eyes_box"]
    mouth_box = cfg["mouth_box"]
    arms_y = cfg["arms_y"]
    skin = cfg["skin_color"]
    ink = cfg["ink_color"]

    # 1. Torso: clear above collar_y with slight feathering
    torso_2x = bust_2x.copy()
    torso_arr = np.array(torso_2x)
    for y in range(224):
        if y < collar_y - 2:
            torso_arr[y, :, 3] = 0
        elif y <= collar_y + 2:
            factor = (y - (collar_y - 2)) / 4.0
            torso_arr[y, :, 3] = (torso_arr[y, :, 3] * factor).astype(np.uint8)
    torso_2x = Image.fromarray(torso_arr, mode="RGBA")
    torso_1x = torso_2x.resize((112, 112), Image.Resampling.LANCZOS)
    torso_2x.save(out_dir / "torso_2x.png")
    torso_1x.save(out_dir / "torso.png")

    # 2. Head: clear below collar_y
    head_2x = bust_2x.copy()
    head_arr = np.array(head_2x)
    for y in range(224):
        if y > collar_y + 4:
            head_arr[y, :, 3] = 0
        elif y >= collar_y:
            factor = 1.0 - ((y - collar_y) / 4.0)
            head_arr[y, :, 3] = (head_arr[y, :, 3] * factor).astype(np.uint8)
    head_2x = Image.fromarray(head_arr, mode="RGBA")
    head_1x = head_2x.resize((112, 112), Image.Resampling.LANCZOS)
    head_2x.save(out_dir / "head_2x.png")
    head_1x.save(out_dir / "head.png")

    # 3. Eyes
    # A) eyes_open: isolate eye area with feathering
    eyes_mask = create_feathered_mask((224, 224), eyes_box, radius=1.8)
    eyes_open_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    eyes_open_2x.paste(bust_2x, (0, 0), eyes_mask)
    eyes_open_1x = eyes_open_2x.resize((112, 112), Image.Resampling.LANCZOS)
    eyes_open_2x.save(out_dir / "eyes_open_2x.png")
    eyes_open_1x.save(out_dir / "eyes_open.png")

    # B) eyes_half: eyelids lowered by 50%
    eyes_half_2x = eyes_open_2x.copy()
    draw_half = ImageDraw.Draw(eyes_half_2x)
    el_box = cfg["eye_left_pupil"]
    er_box = cfg["eye_right_pupil"]
    el_line = cfg["eye_left_line"]
    er_line = cfg["eye_right_line"]

    if char_id == "mortimer":
        # Dim purple flame down to small central ember
        for (bx1, by1, bx2, by2) in [el_box, er_box]:
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            # Dark hollow socket
            draw_half.ellipse([bx1, by1, bx2, by2], fill=(15, 12, 18, 255))
            # Tiny dim ember spark
            draw_half.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(160, 80, 230, 200))
    elif char_id == "malphas":
        # Fiery slit
        for (bx1, by1, bx2, by2) in [el_box, er_box]:
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            draw_half.rectangle([bx1, by1, bx2, by2], fill=(30, 22, 24, 255))
            draw_half.line([bx1 + 1, cy, bx2 - 1, cy], fill=(255, 180, 40, 255), width=1)
    else:
        # Upper eyelid droop
        for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in [(el_box, el_line), (er_box, er_line)]:
            my = (by1 + by2) // 2
            draw_half.rectangle([bx1, by1, bx2, my], fill=(*skin, 255))
            draw_half.line([lx1, ly1, lx2, ly2], fill=(*ink, 255), width=1)

    alpha_half = eyes_half_2x.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.3))
    eyes_half_2x.putalpha(alpha_half)
    eyes_half_1x = eyes_half_2x.resize((112, 112), Image.Resampling.LANCZOS)
    eyes_half_2x.save(out_dir / "eyes_half_2x.png")
    eyes_half_1x.save(out_dir / "eyes_half.png")

    # C) eyes_closed: complete realistic blink
    eyes_closed_2x = eyes_open_2x.copy()
    draw_closed = ImageDraw.Draw(eyes_closed_2x)
    if char_id == "mortimer":
        # Extinguish spectral eye flames completely into deep hollow black bone socket
        for (bx1, by1, bx2, by2) in [el_box, er_box]:
            draw_closed.ellipse([bx1 - 2, by1 - 2, bx2 + 2, by2 + 2], fill=(15, 12, 18, 255))
    elif char_id == "malphas":
        # Dark charcoal eyelid seam
        for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in [(el_box, el_line), (er_box, er_line)]:
            draw_closed.rectangle([bx1, by1, bx2, by2], fill=(30, 22, 24, 255))
            draw_closed.line([lx1, ly1, lx2, ly2], fill=(*ink, 255), width=1)
    else:
        # Realistic closed eyelid
        for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in [(el_box, el_line), (er_box, er_line)]:
            draw_closed.rectangle([bx1, by1, bx2, by2], fill=(*skin, 255))
            draw_closed.line([lx1, ly1, lx2, ly2], fill=(*ink, 255), width=1)

    alpha_closed = eyes_closed_2x.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.4))
    eyes_closed_2x.putalpha(alpha_closed)
    eyes_closed_1x = eyes_closed_2x.resize((112, 112), Image.Resampling.LANCZOS)
    eyes_closed_2x.save(out_dir / "eyes_closed_2x.png")
    eyes_closed_1x.save(out_dir / "eyes_closed.png")

    # 4. Mouth
    # A) mouth_neutral
    mouth_mask = create_feathered_mask((224, 224), mouth_box, radius=1.8)
    mouth_neutral_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    mouth_neutral_2x.paste(bust_2x, (0, 0), mouth_mask)
    mouth_neutral_1x = mouth_neutral_2x.resize((112, 112), Image.Resampling.LANCZOS)
    mouth_neutral_2x.save(out_dir / "mouth_neutral_2x.png")
    mouth_neutral_1x.save(out_dir / "mouth_neutral.png")

    mc_x, mc_y = cfg["mouth_center"]
    my = cfg["mouth_y"]
    mx_start, mx_end = cfg["mouth_x_span"]

    # B) mouth_talk: slightly opened mouth with dark cavity and teeth hint
    mouth_talk_2x = mouth_neutral_2x.copy()
    draw_talk = ImageDraw.Draw(mouth_talk_2x)
    cavity_color = (25, 10, 15, 255) if char_id != "malphas" else (50, 10, 15, 255)
    # Open cavity right at mouth slit
    draw_talk.ellipse([mc_x - 5, my - 2, mc_x + 5, my + 2], fill=cavity_color, outline=(*ink, 255), width=1)
    # Upper teeth highlight
    draw_talk.line([mc_x - 4, my - 1, mc_x + 4, my - 1], fill=(245, 240, 235, 220), width=1)
    alpha_talk = mouth_talk_2x.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.3))
    mouth_talk_2x.putalpha(alpha_talk)
    mouth_talk_1x = mouth_talk_2x.resize((112, 112), Image.Resampling.LANCZOS)
    mouth_talk_2x.save(out_dir / "mouth_talk_2x.png")
    mouth_talk_1x.save(out_dir / "mouth_talk.png")

    # C) mouth_smirk: asymmetrical upward smirk
    mouth_smirk_2x = mouth_neutral_2x.copy()
    draw_smirk = ImageDraw.Draw(mouth_smirk_2x)
    # Cover right half of old flat mouth line with surrounding skin tone
    draw_smirk.rectangle([mc_x, my - 1, mx_end + 1, my + 1], fill=(*skin, 255))
    # Draw upward curving smirk
    draw_smirk.line([(mc_x - 1, my), (mc_x + 4, my - 1), (mx_end, my - 3)], fill=(*ink, 255), width=2)
    # Tiny corner smirk crease
    draw_smirk.line([(mx_end, my - 4), (mx_end + 1, my - 2)], fill=(*ink, 180), width=1)
    alpha_smirk = mouth_smirk_2x.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.3))
    mouth_smirk_2x.putalpha(alpha_smirk)
    mouth_smirk_1x = mouth_smirk_2x.resize((112, 112), Image.Resampling.LANCZOS)
    mouth_smirk_2x.save(out_dir / "mouth_smirk_2x.png")
    mouth_smirk_1x.save(out_dir / "mouth_smirk.png")

    # D) mouth_gasp: surprised round O-mouth
    mouth_gasp_2x = mouth_neutral_2x.copy()
    draw_gasp = ImageDraw.Draw(mouth_gasp_2x)
    draw_gasp.ellipse([mc_x - 3, my - 2, mc_x + 3, my + 3], fill=cavity_color, outline=(*ink, 255), width=1)
    alpha_gasp = mouth_gasp_2x.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.3))
    mouth_gasp_2x.putalpha(alpha_gasp)
    mouth_gasp_1x = mouth_gasp_2x.resize((112, 112), Image.Resampling.LANCZOS)
    mouth_gasp_2x.save(out_dir / "mouth_gasp_2x.png")
    mouth_gasp_1x.save(out_dir / "mouth_gasp.png")

    # 5. Arms
    # A) arm_rest: lower arms and hands on table
    arm_rest_mask = Image.new("L", (224, 224), 0)
    for y in range(224):
        if y >= arms_y + 4:
            arm_rest_mask.paste(255, (0, y, 224, y + 1))
        elif y >= arms_y:
            f = int(255 * (y - arms_y) / 4.0)
            arm_rest_mask.paste(f, (0, y, 224, y + 1))
    arm_rest_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    arm_rest_2x.paste(bust_2x, (0, 0), arm_rest_mask)
    arm_rest_1x = arm_rest_2x.resize((112, 112), Image.Resampling.LANCZOS)
    arm_rest_2x.save(out_dir / "arm_rest_2x.png")
    arm_rest_1x.save(out_dir / "arm_rest.png")

    # B) arm_deal: hand dealing an authentic playing card forward onto the table
    arm_deal_2x = arm_rest_2x.copy()
    draw_deal = ImageDraw.Draw(arm_deal_2x)
    cx1, cy1, cx2, cy2 = 120, 180, 146, 216
    # Card soft drop shadow
    draw_deal.rectangle([cx1 + 2, cy1 + 2, cx2 + 2, cy2 + 2], fill=(0, 0, 0, 80))
    # Card body
    draw_deal.rectangle([cx1, cy1, cx2, cy2], fill=(250, 250, 248, 255), outline=(25, 20, 22, 255), width=1)
    # Card inner border
    draw_deal.rectangle([cx1 + 2, cy1 + 2, cx2 - 2, cy2 - 2], outline=(220, 215, 210, 255), width=1)
    # Authentic pip (Diamond / Skull / Star / Spade)
    pip_color = (200, 25, 35, 255) if char_id in ("julian", "malphas") else (25, 20, 25, 255)
    draw_deal.polygon([(133, 192), (137, 198), (133, 204), (129, 198)], fill=pip_color)
    # Mini corner rank 'A'
    draw_deal.line([(123, 188), (125, 184), (127, 188)], fill=pip_color, width=1)
    draw_deal.line([(124, 186), (126, 186)], fill=pip_color, width=1)
    # Natural dealer fingertips resting over top card edge
    for fx in [125, 133, 141]:
        draw_deal.ellipse([fx - 3, cy1 - 3, fx + 3, cy1 + 2], fill=(*skin, 255), outline=(*ink, 255), width=1)

    arm_deal_1x = arm_deal_2x.resize((112, 112), Image.Resampling.LANCZOS)
    arm_deal_2x.save(out_dir / "arm_deal_2x.png")
    arm_deal_1x.save(out_dir / "arm_deal.png")

    # C) arm_peek: peeking hand lifting edge of hole card
    arm_peek_2x = arm_rest_2x.copy()
    draw_peek = ImageDraw.Draw(arm_peek_2x)
    px1, py1, px2, py2 = 75, 185, 101, 221
    card_back_rgb = cfg["card_back"]
    # Drop shadow
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 + 2, py2 + 2], fill=(0, 0, 0, 80))
    # Face down card body
    draw_peek.rectangle([px1, py1, px2, py2], fill=(250, 250, 248, 255), outline=(25, 20, 22, 255), width=1)
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 - 2, py2 - 2], fill=(*card_back_rgb, 255), outline=(240, 235, 230, 255), width=1)
    # Diamond back motif
    draw_peek.polygon([(88, 195), (94, 203), (88, 211), (82, 203)], fill=(int(card_back_rgb[0]*0.8), int(card_back_rgb[1]*0.8), int(card_back_rgb[2]*0.8), 255), outline=(220, 220, 220, 180), width=1)
    # Lifted bottom corner (peeking hole card)
    draw_peek.polygon([(px2 - 6, py2), (px2, py2 - 6), (px2, py2)], fill=(245, 245, 240, 255), outline=(*ink, 255), width=1)
    # Dealer hand resting naturally over card
    for fx in [83, 91, 99]:
        draw_peek.ellipse([fx - 3, py1 - 3, fx + 3, py1 + 2], fill=(*skin, 255), outline=(*ink, 255), width=1)

    arm_peek_1x = arm_peek_2x.resize((112, 112), Image.Resampling.LANCZOS)
    arm_peek_2x.save(out_dir / "arm_peek_2x.png")
    arm_peek_1x.save(out_dir / "arm_peek.png")

    print(f"Generated all 26 refined layers for {char_id} successfully.")

def main():
    print("Starting graphic novel dealer layers generation (refined)...")
    for char_id, cfg in CHARACTERS_CONFIG.items():
        generate_character_layers(char_id, cfg)
    print("All character layers generated successfully!")

if __name__ == "__main__":
    main()
