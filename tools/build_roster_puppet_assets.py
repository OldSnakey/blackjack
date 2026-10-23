"""
Procedural Asset Pipeline: Roster Puppet Conversion and New Characters (Selene & Vladimir).

1. Converts remaining characters (Julian, Malphas, Uriel, Mortimer) to full 19-layer discrete puppet sets:
   - Synthesizes grounding contact shadow (shadow, shadow_2x).
   - Generates matching neck articulation pillar (neck, neck_2x).
   - Synthesizes distinct phonetic visemes (mouth_a, mouth_o, mouth_e, mouth_f, plus _2x) matching character mouth aesthetics.
2. Generates complete 19-layer discrete puppet strata in 2x (224x224) and 1x (112x112) for new dealer personalities:
   - Selene: Cyberpunk 2088 croupier with holographic cyan visor, neon trim, and chrome dealer arms.
   - Vladimir: Crimson Nocturne Victorian vampire count with aristocratic fangs, high velvet collar, and pale hands.
"""

from __future__ import annotations

import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = BASE_DIR / "assets" / "haunted" / "characters"


ROSTER_PUPPET_CONFIGS = {
    "julian": {
        "collar_y": 88,
        "eyes_box": (84, 34, 140, 54),
        "mouth_box": (96, 58, 128, 70),
        "arms_y": 165,
        "skin_color": (225, 185, 160),
        "ink_color": (28, 22, 22),
        "lip_color": (165, 55, 60),
        "eye_left_pupil": (96, 42, 104, 45),
        "eye_left_line": (95, 43, 105, 43),
        "eye_right_pupil": (121, 41, 128, 43),
        "eye_right_line": (120, 42, 129, 42),
        "mouth_center": (112, 64),
        "mouth_y": 64,
        "mouth_x_span": (104, 122),
        "card_back": (160, 25, 35),
        "clean_table": False,
    },
    "malphas": {
        "collar_y": 82,
        "eyes_box": (84, 44, 140, 62),
        "mouth_box": (96, 67, 128, 79),
        "arms_y": 150,
        "skin_color": (55, 34, 36),
        "ink_color": (15, 10, 12),
        "lip_color": (220, 45, 25),
        "eye_left_pupil": (96, 47, 105, 52),
        "eye_left_line": (95, 50, 106, 50),
        "eye_right_pupil": (119, 47, 128, 52),
        "eye_right_line": (118, 50, 129, 50),
        "mouth_center": (112, 72),
        "mouth_y": 72,
        "mouth_x_span": (104, 121),
        "card_back": (70, 15, 20),
        "clean_table": True,
    },
    "uriel": {
        "collar_y": 84,
        "eyes_box": (84, 44, 140, 62),
        "mouth_box": (96, 68, 128, 80),
        "arms_y": 152,
        "skin_color": (212, 174, 152),
        "ink_color": (25, 20, 22),
        "lip_color": (195, 95, 105),
        "eye_left_pupil": (95, 48, 106, 54),
        "eye_left_line": (94, 51, 107, 51),
        "eye_right_pupil": (118, 48, 129, 54),
        "eye_right_line": (117, 51, 130, 51),
        "mouth_center": (112, 74),
        "mouth_y": 74,
        "mouth_x_span": (105, 120),
        "card_back": (20, 90, 140),
        "clean_table": False,
    },
    "mortimer": {
        "collar_y": 88,
        "eyes_box": (84, 56, 140, 74),
        "mouth_box": (96, 74, 128, 86),
        "arms_y": 155,
        "skin_color": (225, 215, 190),
        "ink_color": (20, 15, 20),
        "lip_color": (45, 35, 50),
        "eye_left_pupil": (94, 59, 104, 69),
        "eye_left_line": (94, 64, 104, 64),
        "eye_right_pupil": (120, 59, 130, 69),
        "eye_right_line": (120, 64, 130, 64),
        "mouth_center": (112, 80),
        "mouth_y": 80,
        "mouth_x_span": (104, 122),
        "card_back": (65, 25, 95),
        "clean_table": False,
    },
}


def apply_unpremultiplied_mask(src_rgba: Image.Image, mask_l: Image.Image) -> Image.Image:
    """
    Applies an 8-bit grayscale mask to an RGBA image WITHOUT premultiplying RGB by black.
    Preserves exact source RGB values across feathered edges so Porter-Duff alpha_composite
    never produces dark rectangular halos or seams.
    """
    arr = np.array(src_rgba.convert("RGBA")).copy()
    m = np.array(mask_l.convert("L"), dtype=np.float32) / 255.0
    new_a = np.round(arr[:, :, 3].astype(np.float32) * m).astype(np.uint8)
    arr[:, :, 3] = new_a
    arr[new_a == 0] = [0, 0, 0, 0]
    return Image.fromarray(arr, "RGBA")


def put_unpremultiplied_alpha(img_rgba: Image.Image, radius: float = 0.3) -> Image.Image:
    """ Gently softens alpha edge while propagating nearby non-zero RGB into border pixels to avoid black fringes."""
    arr = np.array(img_rgba.convert("RGBA")).copy()
    orig_a = arr[:, :, 3]
    if not np.any(orig_a > 0):
        return img_rgba
    blurred_a = np.array(Image.fromarray(orig_a, "L").filter(ImageFilter.GaussianBlur(radius=radius)))
    # For pixels that gained alpha from blur but had (0,0,0) RGB, copy nearest non-zero neighbor RGB
    zero_rgb = (orig_a == 0) & (blurred_a > 0)
    if np.any(zero_rgb):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                shifted = np.roll(np.roll(arr, dy, axis=0), dx, axis=1)
                fill_mask = zero_rgb & (shifted[:, :, 3] > 0)
                arr[fill_mask, :3] = shifted[fill_mask, :3]
                zero_rgb = zero_rgb & (~fill_mask)
    arr[:, :, 3] = blurred_a
    arr[blurred_a == 0] = [0, 0, 0, 0]
    return Image.fromarray(arr, "RGBA")


def create_grounding_shadow(width: int = 224, height: int = 224, radius_x: int = 65, radius_y: int = 14) -> Image.Image:
    """Creates a soft feathered contact shadow at the base of the actor."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = width // 2, height - 16
    bbox = [cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y]
    draw.ellipse(bbox, fill=(10, 10, 15, 140))
    return img.filter(ImageFilter.GaussianBlur(radius=4))


def rebuild_puppet_layers_from_bust(char_id: str, cfg: dict):
    """
    Rebuilds all 19 discrete puppet layers (2x and 1x) for Julian, Malphas, Uriel, and Mortimer
    from bust_2x.png with:
    - Zero black-premultiplied paste masks (eliminates rectangular face/eye/mouth/arm banding)
    - Zero collar_y alpha seam (100% opaque interior junction)
    - Cleanly de-featured mouth region on head_2x so all 8 phonetic visemes articulate cleanly.
    """
    cdir = CHARACTERS_DIR / char_id
    bust_path = cdir / "bust_2x.png"
    if not bust_path.exists():
        return

    bust_2x = Image.open(bust_path).convert("RGBA")
    arr_bust = np.array(bust_2x).copy()

    # Clean residual green/brown table strip and wooden rail at bottom of Malphas
    if cfg.get("clean_table"):
        r = arr_bust[:, :, 0].astype(int)
        g = arr_bust[:, :, 1].astype(int)
        b = arr_bust[:, :, 2].astype(int)
        is_green = (g > r + 6) & (g > b - 4) & (r < 95) & (b < 95)
        is_bottom_strip = np.zeros((224, 224), dtype=bool)
        is_bottom_strip[188:, :] = is_green[188:, :]
        # Remove wooden table rail wings outside the central hands/arms at y >= 190
        is_bottom_strip[190:, :68] = True
        is_bottom_strip[190:, 164:] = True
        is_bottom_strip[200:, :90] = True
        is_bottom_strip[200:, 150:] = True
        arr_bust[is_bottom_strip] = [0, 0, 0, 0]
        bust_2x = Image.fromarray(arr_bust, "RGBA")
        bust_2x.save(cdir / "bust_2x.png")
        bust_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "bust.png")

    collar_y = cfg["collar_y"]
    eyes_box = cfg["eyes_box"]
    mouth_box = cfg["mouth_box"]
    arms_y = cfg["arms_y"]
    skin = cfg["skin_color"]
    ink = cfg["ink_color"]
    lip_col = cfg["lip_color"]
    el_box = cfg["eye_left_pupil"]
    er_box = cfg["eye_right_pupil"]
    el_line = cfg["eye_left_line"]
    er_line = cfg["eye_right_line"]
    mc_x, mc_y = cfg["mouth_center"]
    my = cfg["mouth_y"]
    mx_start, mx_end = cfg["mouth_x_span"]

    # 1. Shadow
    s2x = create_grounding_shadow(224, 224)
    s2x.save(cdir / "shadow_2x.png")
    s2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "shadow.png")

    # 2. Neck (bridges collar_y - 12 to collar_y + 24 behind torso and head)
    neck_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dneck = ImageDraw.Draw(neck_2x)
    dneck.rectangle([98, collar_y - 12, 126, collar_y + 24], fill=(*skin, 255))
    neck_arr = np.array(neck_2x)
    # Clip neck strictly to silhouette of bust_2x
    outside_silhouette = arr_bust[:, :, 3] < 128
    neck_arr[outside_silhouette] = [0, 0, 0, 0]
    neck_2x = Image.fromarray(neck_arr, "RGBA")
    neck_2x.save(cdir / "neck_2x.png")
    neck_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "neck.png")

    # 3. Torso (100% opaque for all y >= collar_y - 4 so head overlap has zero transparency drop)
    torso_arr = arr_bust.copy()
    torso_arr[:collar_y - 4, :] = [0, 0, 0, 0]
    torso_2x = Image.fromarray(torso_arr, "RGBA")
    torso_2x.save(cdir / "torso_2x.png")
    torso_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "torso.png")

    # 4. Head (100% opaque down to collar_y, unpremultiplied fade over collar_y+1..collar_y+3 over opaque torso)
    head_arr = arr_bust.copy()
    for y in range(224):
        if y > collar_y + 3:
            head_arr[y, :] = [0, 0, 0, 0]
        elif y > collar_y:
            factor = 1.0 - ((y - collar_y) / 4.0)
            head_arr[y, :, 3] = np.round(head_arr[y, :, 3].astype(np.float32) * factor).astype(np.uint8)
            head_arr[y, head_arr[y, :, 3] == 0] = [0, 0, 0, 0]

    # De-feature micro mouth aperture on head_2x using smooth horizontal cheek interpolation
    if char_id != "mortimer":
        x_left = max(0, mx_start - 2)
        x_right = min(223, mx_end + 2)
        span_w = max(1, x_right - x_left)
        for y in range(my - 2, my + 3):
            if 0 <= y < 224:
                c_left = arr_bust[y, x_left, :3].astype(np.float32)
                c_right = arr_bust[y, x_right, :3].astype(np.float32)
                for x in range(mx_start - 1, mx_end + 2):
                    if 0 <= x < 224 and head_arr[y, x, 3] > 0:
                        t = (x - x_left) / span_w
                        head_arr[y, x, :3] = np.round((1.0 - t) * c_left + t * c_right).astype(np.uint8)

    head_2x = Image.fromarray(head_arr, "RGBA")
    head_2x.save(cdir / "head_2x.png")
    head_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "head.png")

    # 5. Eyes (Open, Half, Closed)
    # A) eyes_open: unpremultiplied crop of eye region (zero black halo!)
    eyes_mask = Image.new("L", (224, 224), 0)
    ImageDraw.Draw(eyes_mask).rectangle(eyes_box, fill=255)
    eyes_mask = eyes_mask.filter(ImageFilter.GaussianBlur(radius=1.5))
    eyes_open_2x = apply_unpremultiplied_mask(bust_2x, eyes_mask)
    eyes_open_2x.save(cdir / "eyes_open_2x.png")
    eyes_open_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_open.png")

    # Sample orbital skin for blinks (for Uriel, sample forehead above cyan glow)
    if char_id == "uriel":
        skin_l = cfg["skin_color"]
        skin_r = cfg["skin_color"]
    else:
        yl = max(0, el_box[1] - 1)
        xl = (el_box[0] + el_box[2]) // 2
        yr = max(0, er_box[1] - 1)
        xr = (er_box[0] + er_box[2]) // 2
        skin_l = tuple(int(c) for c in arr_bust[yl, xl, :3])
        skin_r = tuple(int(c) for c in arr_bust[yr, xr, :3])

    # B) eyes_half: surgical half-lidded eyelids over eye_open base
    eyes_half_2x = eyes_open_2x.copy()
    draw_half = ImageDraw.Draw(eyes_half_2x)
    if char_id == "mortimer":
        for (bx1, by1, bx2, by2) in [el_box, er_box]:
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            draw_half.ellipse([bx1, by1, bx2, by2], fill=(15, 12, 18, 255))
            draw_half.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(160, 80, 230, 220))
    elif char_id == "malphas":
        for (bx1, by1, bx2, by2) in [el_box, er_box]:
            cx, cy = (bx1 + bx2) // 2, (by1 + by2) // 2
            draw_half.rectangle([bx1 - 1, by1, bx2 + 1, by2], fill=(30, 22, 24, 255))
            draw_half.line([bx1 - 1, cy, bx2 + 1, cy], fill=(255, 180, 40, 255), width=1)
    else:
        for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2), sk in [
            (el_box, el_line, skin_l),
            (er_box, er_line, skin_r),
        ]:
            mid_y = (by1 + by2) // 2
            draw_half.rectangle([bx1 - 1, by1 - 1, bx2 + 1, mid_y], fill=(*sk, 255))
            draw_half.line([lx1 - 1, ly1, lx2 + 1, ly2], fill=(*ink, 255), width=1)
    eyes_half_2x.save(cdir / "eyes_half_2x.png")
    eyes_half_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_half.png")

    # C) eyes_closed: surgical full blink over eyes_open base
    eyes_closed_2x = eyes_open_2x.copy()
    draw_closed = ImageDraw.Draw(eyes_closed_2x)
    if char_id == "mortimer":
        for (bx1, by1, bx2, by2) in [el_box, er_box]:
            draw_closed.ellipse([bx1 - 2, by1 - 2, bx2 + 2, by2 + 2], fill=(15, 12, 18, 255))
    elif char_id == "malphas":
        for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in [(el_box, el_line), (er_box, er_line)]:
            draw_closed.rectangle([bx1 - 1, by1 - 1, bx2 + 1, by2 + 1], fill=(30, 22, 24, 255))
            draw_closed.line([lx1 - 1, ly1, lx2 + 1, ly2], fill=(*ink, 255), width=1)
    else:
        for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2), sk in [
            (el_box, el_line, skin_l),
            (er_box, er_line, skin_r),
        ]:
            draw_closed.rectangle([bx1 - 1, by1 - 1, bx2 + 1, by2 + 1], fill=(*sk, 255))
            draw_closed.line([lx1 - 1, ly1, lx2 + 1, ly2], fill=(*ink, 255), width=1)
    eyes_closed_2x.save(cdir / "eyes_closed_2x.png")
    eyes_closed_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_closed.png")

    # 6. Mouth Visemes (neutral, talk, a, o, e, f, smirk, gasp)
    # A) mouth_neutral: unpremultiplied crop of original mouth from bust_2x (zero black halo!)
    mouth_mask = Image.new("L", (224, 224), 0)
    ImageDraw.Draw(mouth_mask).rectangle(mouth_box, fill=255)
    mouth_mask = mouth_mask.filter(ImageFilter.GaussianBlur(radius=1.2))
    mouth_neutral_2x = apply_unpremultiplied_mask(bust_2x, mouth_mask)
    mouth_neutral_2x.save(cdir / "mouth_neutral_2x.png")
    mouth_neutral_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_neutral.png")

    cavity_color = (30, 12, 16, 255) if char_id != "malphas" else (55, 10, 15, 255)

    # B) mouth_talk
    mouth_talk_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_talk = ImageDraw.Draw(mouth_talk_2x)
    draw_talk.ellipse([mc_x - 6, my - 3, mc_x + 6, my + 3], fill=cavity_color, outline=(*ink, 255), width=1)
    draw_talk.line([mc_x - 4, my - 1, mc_x + 4, my - 1], fill=(245, 240, 235, 230), width=1)
    mouth_talk_2x = put_unpremultiplied_alpha(mouth_talk_2x, radius=0.3)
    mouth_talk_2x.save(cdir / "mouth_talk_2x.png")
    mouth_talk_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_talk.png")

    # C) mouth_smirk
    mouth_smirk_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_smirk = ImageDraw.Draw(mouth_smirk_2x)
    draw_smirk.line([(mx_start, my + 1), (mc_x + 2, my), (mx_end, my - 3)], fill=(*ink, 255), width=2)
    draw_smirk.line([(mx_end, my - 4), (mx_end + 1, my - 2)], fill=(*ink, 200), width=1)
    mouth_smirk_2x = put_unpremultiplied_alpha(mouth_smirk_2x, radius=0.3)
    mouth_smirk_2x.save(cdir / "mouth_smirk_2x.png")
    mouth_smirk_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_smirk.png")

    # D) mouth_gasp
    mouth_gasp_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_gasp = ImageDraw.Draw(mouth_gasp_2x)
    draw_gasp.ellipse([mc_x - 4, my - 3, mc_x + 4, my + 4], fill=cavity_color, outline=(*ink, 255), width=1)
    mouth_gasp_2x = put_unpremultiplied_alpha(mouth_gasp_2x, radius=0.3)
    mouth_gasp_2x.save(cdir / "mouth_gasp_2x.png")
    mouth_gasp_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_gasp.png")

    # E) Phonetic visemes: mouth_a, mouth_o, mouth_e, mouth_f positioned accurately at (mc_x, my)
    viseme_specs = {
        "mouth_a": (6, 4, "open_teeth"),
        "mouth_o": (4, 4, "ellipse"),
        "mouth_e": (7, 2, "wide_teeth"),
        "mouth_f": (6, 2, "tuck"),
    }
    for vname, (rx, ry, style) in viseme_specs.items():
        vimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        dv = ImageDraw.Draw(vimg)
        bx = [mc_x - rx, my - ry, mc_x + rx, my + ry]
        if style == "open_teeth":
            dv.ellipse(bx, fill=cavity_color, outline=(*ink, 255), width=1)
            dv.line([(mc_x - rx + 2, my - ry + 1), (mc_x + rx - 2, my - ry + 1)], fill=(245, 240, 235, 230), width=1)
            dv.arc(bx, start=10, end=170, fill=(*lip_col, 255), width=1)
        elif style == "ellipse":
            dv.ellipse(bx, fill=cavity_color, outline=(*ink, 255), width=1)
            dv.ellipse([mc_x - rx + 1, my - ry + 1, mc_x + rx - 1, my + ry - 1], outline=(*lip_col, 220), width=1)
        elif style == "wide_teeth":
            dv.rounded_rectangle(bx, radius=2, fill=(235, 230, 225, 255), outline=(*ink, 255), width=1)
            dv.line([(mc_x - rx + 1, my), (mc_x + rx - 1, my)], fill=cavity_color, width=1)
        else:  # tuck ('f')
            dv.line([(mc_x - rx, my), (mc_x + rx, my)], fill=(*ink, 255), width=2)
            dv.line([(mc_x - rx + 2, my + 1), (mc_x + rx - 2, my + 1)], fill=(*lip_col, 240), width=1)
        vimg = put_unpremultiplied_alpha(vimg, radius=0.3)
        vimg.save(cdir / f"{vname}_2x.png")
        vimg.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / f"{vname}.png")

    # 7. Arms (arm_rest, arm_deal, arm_peek) with unpremultiplied mask (zero horizontal sleeve band!)
    arm_mask = Image.new("L", (224, 224), 0)
    for y in range(224):
        if y >= arms_y + 4:
            arm_mask.paste(255, (0, y, 224, y + 1))
        elif y >= arms_y:
            f = int(255 * (y - arms_y) / 4.0)
            arm_mask.paste(f, (0, y, 224, y + 1))
    arm_rest_2x = apply_unpremultiplied_mask(bust_2x, arm_mask)
    arm_rest_2x.save(cdir / "arm_rest_2x.png")
    arm_rest_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_rest.png")

    # B) arm_deal
    arm_deal_2x = arm_rest_2x.copy()
    draw_deal = ImageDraw.Draw(arm_deal_2x)
    cx1, cy1, cx2, cy2 = 120, 180, 146, 216
    draw_deal.rectangle([cx1 + 2, cy1 + 2, cx2 + 2, cy2 + 2], fill=(0, 0, 0, 80))
    draw_deal.rectangle([cx1, cy1, cx2, cy2], fill=(250, 250, 248, 255), outline=(25, 20, 22, 255), width=1)
    draw_deal.rectangle([cx1 + 2, cy1 + 2, cx2 - 2, cy2 - 2], outline=(220, 215, 210, 255), width=1)
    pip_color = (200, 25, 35, 255) if char_id in ("julian", "malphas") else (25, 20, 25, 255)
    draw_deal.polygon([(133, 192), (137, 198), (133, 204), (129, 198)], fill=pip_color)
    draw_deal.line([(123, 188), (125, 184), (127, 188)], fill=pip_color, width=1)
    draw_deal.line([(124, 186), (126, 186)], fill=pip_color, width=1)
    for fx in [125, 133, 141]:
        draw_deal.ellipse([fx - 3, cy1 - 3, fx + 3, cy1 + 2], fill=(*skin, 255), outline=(*ink, 255), width=1)
    arm_deal_2x.save(cdir / "arm_deal_2x.png")
    arm_deal_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_deal.png")

    # C) arm_peek
    arm_peek_2x = arm_rest_2x.copy()
    draw_peek = ImageDraw.Draw(arm_peek_2x)
    px1, py1, px2, py2 = 75, 185, 101, 221
    card_back_rgb = cfg["card_back"]
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 + 2, py2 + 2], fill=(0, 0, 0, 80))
    draw_peek.rectangle([px1, py1, px2, py2], fill=(250, 250, 248, 255), outline=(25, 20, 22, 255), width=1)
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 - 2, py2 - 2], fill=(*card_back_rgb, 255), outline=(240, 235, 230, 255), width=1)
    draw_peek.polygon(
        [(88, 195), (94, 203), (88, 211), (82, 203)],
        fill=(int(card_back_rgb[0] * 0.8), int(card_back_rgb[1] * 0.8), int(card_back_rgb[2] * 0.8), 255),
        outline=(220, 220, 220, 180),
        width=1,
    )
    draw_peek.polygon([(px2 - 6, py2), (px2, py2 - 6), (px2, py2)], fill=(245, 245, 240, 255), outline=(*ink, 255), width=1)
    for fx in [83, 91, 99]:
        draw_peek.ellipse([fx - 3, py1 - 3, fx + 3, py1 + 2], fill=(*skin, 255), outline=(*ink, 255), width=1)
    arm_peek_2x.save(cdir / "arm_peek_2x.png")
    arm_peek_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_peek.png")


def build_selene_cyberpunk_puppet():
    """Generates all 19 discrete graphic-novel puppet layers for Selene (Cyberpunk Croupier)."""
    from deocclude_dealer_faceplates import DEOCCLUDE_CONFIGS, deocclude_and_build_character

    deocclude_and_build_character("selene", DEOCCLUDE_CONFIGS["selene"])


def build_vladimir_vampire_puppet():
    """Generates all 19 discrete graphic-novel puppet layers for Vladimir (Victorian Vampire Count)."""
    from deocclude_dealer_faceplates import DEOCCLUDE_CONFIGS, deocclude_and_build_character

    deocclude_and_build_character("vladimir", DEOCCLUDE_CONFIGS["vladimir"])


def run_pipeline():
    """Runs the full puppet conversion and new character asset generation."""
    from deocclude_dealer_faceplates import DEOCCLUDE_CONFIGS, deocclude_and_build_character

    for cid, cfg in DEOCCLUDE_CONFIGS.items():
        print(f"Rebuilding de-occluded zero-banding puppet layers for {cid}...")
        deocclude_and_build_character(cid, cfg)

    print("Puppet roster asset generation complete!")


if __name__ == "__main__":
    run_pipeline()
