"""
Universal Dealer Puppet Faceplate & Torso De-Occlusion Pipeline.

Converts all graphic-novel portrait dealers (`julian`, `malphas`, `uriel`, `mortimer`,
`selene`, `vladimir`) into genuine 7-layer discrete puppets with:
1. Blank Mannequin Faceplates (`head_2x.png` / `head.png`):
   - Left and right eye sockets (`eye_left_pupil`, `eye_right_pupil`) and mouth apertures
     (`mouth_x_span`, `mouth_y`) are cleanly de-occluded on `head_2x.png` using local boundary
     eyelid/cheek interpolation.
   - Zero baked-in open eyes or neutral mouths remain on `head_2x.png`.
2. Isolated Per-Socket Eye Overlays (`eyes_open`, `eyes_half`, `eyes_closed`):
   - `eyes_open` isolates only the two elliptical eye apertures (never the nose bridge or temples),
     so `eye_gaze_offset` shifts the eyes cleanly within the sockets.
   - `eyes_half` keeps the lower half of the open eyes + lowered upper lash line over the
     already-smooth blank faceplate `head_2x`.
   - `eyes_closed` renders clean closed lash lines directly over the smooth de-occluded eyelids on `head_2x`
     with zero rectangular skin patches.
3. De-Occluded Torso (`torso_2x.png` / `torso.png`):
   - Foreground resting hands/cards in the lower torso zone (`y >= arms_y + 8`) are replaced with
     the character's waistcoat/vest fabric shading so moving `arm_*` layers or `arm_offset` kinematics
     never reveal duplicate ghost hands on the torso underneath.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = BASE_DIR / "assets" / "haunted" / "characters"


DEOCCLUDE_CONFIGS = {
    "julian": {
        "collar_y": 88,
        "arms_y": 165,
        "skin_color": (225, 185, 160),
        "ink_color": (28, 22, 22),
        "lip_color": (165, 55, 60),
        "vest_color": (32, 34, 38),
        "eye_left_pupil": (94, 40, 106, 46),
        "eye_left_line": (95, 43, 105, 43),
        "eye_right_pupil": (119, 39, 130, 45),
        "eye_right_line": (120, 42, 129, 42),
        "mouth_center": (112, 64),
        "mouth_y": 64,
        "mouth_x_span": (103, 122),
        "card_back": (160, 25, 35),
        "clean_table": False,
    },
    "malphas": {
        "collar_y": 82,
        "arms_y": 150,
        "skin_color": (55, 34, 36),
        "ink_color": (15, 10, 12),
        "lip_color": (220, 45, 25),
        "vest_color": (28, 28, 32),
        "eye_left_pupil": (94, 46, 106, 53),
        "eye_left_line": (95, 50, 106, 50),
        "eye_right_pupil": (118, 46, 130, 53),
        "eye_right_line": (118, 50, 129, 50),
        "mouth_center": (112, 72),
        "mouth_y": 72,
        "mouth_x_span": (103, 121),
        "card_back": (70, 15, 20),
        "clean_table": True,
    },
    "uriel": {
        "collar_y": 84,
        "arms_y": 152,
        "skin_color": (212, 174, 152),
        "ink_color": (25, 20, 22),
        "lip_color": (195, 95, 105),
        "vest_color": (215, 202, 175),
        "eye_left_pupil": (94, 48, 106, 54),
        "eye_left_line": (94, 51, 106, 51),
        "eye_right_pupil": (118, 48, 130, 54),
        "eye_right_line": (118, 51, 130, 51),
        "mouth_center": (112, 74),
        "mouth_y": 74,
        "mouth_x_span": (104, 120),
        "card_back": (20, 90, 140),
        "clean_table": False,
    },
    "mortimer": {
        "collar_y": 88,
        "arms_y": 155,
        "skin_color": (225, 215, 190),
        "ink_color": (20, 15, 20),
        "lip_color": (45, 35, 50),
        "vest_color": (42, 26, 48),
        "eye_left_pupil": (93, 58, 105, 69),
        "eye_left_line": (94, 64, 104, 64),
        "eye_right_pupil": (119, 58, 131, 69),
        "eye_right_line": (120, 64, 130, 64),
        "mouth_center": (112, 80),
        "mouth_y": 80,
        "mouth_x_span": (102, 122),
        "card_back": (65, 25, 95),
        "clean_table": False,
    },
    "selene": {
        "collar_y": 90,
        "arms_y": 156,
        "skin_color": (208, 148, 118),
        "ink_color": (18, 22, 32),
        "lip_color": (235, 65, 150),
        "vest_color": (32, 38, 48),
        "eye_left_pupil": (95, 52, 106, 57),
        "eye_left_line": (96, 55, 105, 55),
        "eye_right_pupil": (119, 52, 130, 57),
        "eye_right_line": (120, 55, 129, 55),
        "mouth_center": (112, 77),
        "mouth_y": 77,
        "mouth_x_span": (106, 119),
        "card_back": (0, 200, 235),
        "clean_table": False,
    },
    "vladimir": {
        "collar_y": 82,
        "arms_y": 152,
        "skin_color": (228, 224, 228),
        "ink_color": (18, 14, 20),
        "lip_color": (135, 55, 68),
        "vest_color": (115, 22, 28),
        "eye_left_pupil": (98, 43, 108, 48),
        "eye_left_line": (99, 46, 107, 46),
        "eye_right_pupil": (118, 43, 128, 48),
        "eye_right_line": (119, 46, 127, 46),
        "mouth_center": (113, 65),
        "mouth_y": 65,
        "mouth_x_span": (106, 120),
        "card_back": (155, 20, 35),
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
    """Gently softens alpha edge while propagating nearby non-zero RGB into border pixels to avoid black fringes."""
    arr = np.array(img_rgba.convert("RGBA")).copy()
    orig_a = arr[:, :, 3]
    if not np.any(orig_a > 0):
        return img_rgba
    blurred_a = np.array(Image.fromarray(orig_a, "L").filter(ImageFilter.GaussianBlur(radius=radius)))
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


def deocclude_and_build_character(char_id: str, cfg: dict | None = None) -> None:
    """
    De-occludes the head faceplate and lower torso of `char_id` and writes all 19
    discrete 2x (224x224) and 1x (112x112) puppet layer PNGs.
    """
    if cfg is None:
        cfg = DEOCCLUDE_CONFIGS[char_id]

    cdir = CHARACTERS_DIR / char_id
    cdir.mkdir(parents=True, exist_ok=True)

    orig_path = cdir / "orig_bust_2x.png"
    bust_path = cdir / "bust_2x.png"
    if orig_path.exists():
        master_2x = Image.open(orig_path).convert("RGBA")
    elif bust_path.exists():
        master_2x = Image.open(bust_path).convert("RGBA")
        master_2x.save(orig_path)
    else:
        return

    arr_bust = np.array(master_2x).copy()

    # Clean residual green/brown table strip and wooden rail at bottom of Malphas
    if cfg.get("clean_table"):
        r = arr_bust[:, :, 0].astype(int)
        g = arr_bust[:, :, 1].astype(int)
        b = arr_bust[:, :, 2].astype(int)
        is_green = (g > r + 6) & (g > b - 4) & (r < 95) & (b < 95)
        is_bottom_strip = np.zeros((224, 224), dtype=bool)
        is_bottom_strip[188:, :] = is_green[188:, :]
        is_bottom_strip[190:, :68] = True
        is_bottom_strip[190:, 164:] = True
        is_bottom_strip[200:, :90] = True
        is_bottom_strip[200:, 150:] = True
        arr_bust[is_bottom_strip] = [0, 0, 0, 0]
        master_2x = Image.fromarray(arr_bust, "RGBA")

    collar_y = cfg["collar_y"]
    arms_y = cfg["arms_y"]
    skin = cfg["skin_color"]
    ink = cfg["ink_color"]
    lip_col = cfg["lip_color"]
    vest_col = cfg.get("vest_color", (30, 32, 38))
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
    dneck.rectangle([94, collar_y - 14, 130, collar_y + 24], fill=(*skin, 255))
    neck_arr = np.array(neck_2x)
    outside_silhouette = arr_bust[:, :, 3] < 128
    neck_arr[outside_silhouette] = [0, 0, 0, 0]
    neck_2x = Image.fromarray(neck_arr, "RGBA")
    neck_2x.save(cdir / "neck_2x.png")
    neck_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "neck.png")

    # 3. Torso (de-occlude foreground skin/card pixels in lower hand region y >= arms_y + 8)
    torso_arr = arr_bust.copy()
    torso_arr[:collar_y - 4, :] = [0, 0, 0, 0]
    for y in range(max(145, arms_y + 8), 224):
        for x in range(72, 152):
            if torso_arr[y, x, 3] > 160:
                # Replace foreground hand/card pixels on torso with smooth vest shading
                torso_arr[y, x, 0] = int(0.75 * vest_col[0] + 0.25 * torso_arr[y, x, 0])
                torso_arr[y, x, 1] = int(0.75 * vest_col[1] + 0.25 * torso_arr[y, x, 1])
                torso_arr[y, x, 2] = int(0.75 * vest_col[2] + 0.25 * torso_arr[y, x, 2])
    torso_2x = Image.fromarray(torso_arr, "RGBA")
    torso_2x.save(cdir / "torso_2x.png")
    torso_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "torso.png")

    # 4. Head (Genuine Blank Mannequin Faceplate: both eye sockets AND mouth aperture de-occluded!)
    head_arr = arr_bust.copy()
    for y in range(224):
        if y > collar_y + 3:
            head_arr[y, :] = [0, 0, 0, 0]
        elif y > collar_y:
            factor = 1.0 - ((y - collar_y) / 4.0)
            head_arr[y, :, 3] = np.round(head_arr[y, :, 3].astype(np.float32) * factor).astype(np.uint8)
            head_arr[y, head_arr[y, :, 3] == 0] = [0, 0, 0, 0]

    # 4A. De-occlude left and right eye sockets on head_2x using local boundary skin interpolation
    for bx1, by1, bx2, by2 in (el_box, er_box):
        if char_id == "mortimer":
            # Hollow dark bone socket without purple soul flame
            for y in range(max(0, by1), min(224, by2 + 1)):
                for x in range(max(0, bx1), min(224, bx2 + 1)):
                    if head_arr[y, x, 3] > 0:
                        head_arr[y, x, :3] = [18, 14, 22]
        else:
            # Sample skin row immediately below lower lash (cheek/lower lid) and above upper lash
            y_top = max(0, by1 - 2)
            y_bot = min(223, by2 + 2)
            span_h = max(1, y_bot - y_top)
            for x in range(max(0, bx1 - 1), min(224, bx2 + 2)):
                c_top = arr_bust[y_top, x, :3].astype(np.float32)
                c_bot = arr_bust[y_bot, x, :3].astype(np.float32)
                # Prefer the brighter/cleaner eyelid skin sample so dark eyebrow ink doesn't bleed down
                for y in range(max(0, by1 - 1), min(224, by2 + 2)):
                    if head_arr[y, x, 3] > 0:
                        t = (y - y_top) / span_h
                        # Weight 65% toward lower eyelid/cheek (c_bot) + 35% upper lid (c_top) for natural lid tone
                        w_bot = 0.35 + 0.65 * t
                        interp = (1.0 - w_bot) * c_top + w_bot * c_bot
                        head_arr[y, x, :3] = np.round(interp).astype(np.uint8)

    # 4B. De-occlude mouth aperture on head_2x using smooth horizontal cheek interpolation
    x_left = max(0, mx_start - 3)
    x_right = min(223, mx_end + 3)
    span_w = max(1, x_right - x_left)
    my_half = 4 if char_id != "mortimer" else 5
    for y in range(my - my_half, my + my_half + 1):
        if 0 <= y < 224:
            c_left = arr_bust[y, x_left, :3].astype(np.float32) if arr_bust[y, x_left, 3] > 128 else np.array(skin, dtype=np.float32)
            c_right = arr_bust[y, x_right, :3].astype(np.float32) if arr_bust[y, x_right, 3] > 128 else np.array(skin, dtype=np.float32)
            for x in range(mx_start - 2, mx_end + 3):
                if 0 <= x < 224 and head_arr[y, x, 3] > 0:
                    t = (x - x_left) / span_w
                    head_arr[y, x, :3] = np.round((1.0 - t) * c_left + t * c_right).astype(np.uint8)

    head_2x = Image.fromarray(head_arr, "RGBA")
    head_2x.save(cdir / "head_2x.png")
    head_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "head.png")

    # 5. Eyes (Open, Half, Closed) — isolated per-socket masks (never masking nose bridge or temples!)
    eyes_mask = Image.new("L", (224, 224), 0)
    d_em = ImageDraw.Draw(eyes_mask)
    for bx1, by1, bx2, by2 in (el_box, er_box):
        d_em.rectangle([bx1 - 2, by1 - 2, bx2 + 2, by2 + 2], fill=255)
    eyes_mask = eyes_mask.filter(ImageFilter.GaussianBlur(radius=0.8))
    d_em = ImageDraw.Draw(eyes_mask)
    for bx1, by1, bx2, by2 in (el_box, er_box):
        d_em.rectangle([bx1 - 1, by1 - 1, bx2 + 1, by2 + 1], fill=255)

    # A) eyes_open
    eyes_open_2x = apply_unpremultiplied_mask(master_2x, eyes_mask)
    eyes_open_2x.save(cdir / "eyes_open_2x.png")
    eyes_open_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_open.png")

    # B) eyes_half: keep only lower half of open eyes + draw lowered upper lash line at mid_y!
    # Because head_2x underneath is already a smooth de-occluded eyelid faceplate, no flat skin rectangle is needed!
    eyes_half_arr = np.array(eyes_open_2x).copy()
    for bx1, by1, bx2, by2 in (el_box, er_box):
        mid_y = (by1 + by2) // 2
        eyes_half_arr[max(0, by1 - 3):mid_y, max(0, bx1 - 3):min(224, bx2 + 4)] = [0, 0, 0, 0]
    eyes_half_2x = Image.fromarray(eyes_half_arr, "RGBA")
    draw_half = ImageDraw.Draw(eyes_half_2x)
    for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in ((el_box, el_line), (er_box, er_line)):
        mid_y = (by1 + by2) // 2
        lash_col = (0, 210, 240, 255) if char_id == "selene" else (160, 80, 230, 220) if char_id == "mortimer" else (*ink, 255)
        draw_half.line([(lx1, mid_y), (lx2, mid_y)], fill=lash_col, width=1)
    eyes_half_2x.save(cdir / "eyes_half_2x.png")
    eyes_half_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_half.png")

    # C) eyes_closed: clean curved closed lash lines directly over the smooth de-occluded eyelids on head_2x!
    eyes_closed_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_closed = ImageDraw.Draw(eyes_closed_2x)
    for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in ((el_box, el_line), (er_box, er_line)):
        if char_id == "mortimer":
            # Subtle dark bone suture line in socket
            draw_closed.line([(lx1, ly1), (lx2, ly2)], fill=(35, 25, 42, 220), width=1)
        elif char_id == "selene":
            draw_closed.line([(lx1, ly1), ((lx1 + lx2) // 2, ly1 + 1), (lx2, ly2)], fill=(10, 85, 110, 255), width=2)
        else:
            draw_closed.line([(lx1, ly1), ((lx1 + lx2) // 2, ly1 + 1), (lx2, ly2)], fill=(*ink, 255), width=2)
    eyes_closed_2x = put_unpremultiplied_alpha(eyes_closed_2x, radius=0.3)
    eyes_closed_2x.save(cdir / "eyes_closed_2x.png")
    eyes_closed_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_closed.png")

    # 6. Mouth Visemes (neutral, talk, a, o, e, f, smirk, gasp)
    # A) mouth_neutral: isolated per-mouth mask (100% opaque over de-occluded mouth span)
    mouth_mask = Image.new("L", (224, 224), 0)
    ImageDraw.Draw(mouth_mask).rectangle([mx_start - 3, my - my_half - 1, mx_end + 3, my + my_half + 1], fill=255)
    mouth_mask = mouth_mask.filter(ImageFilter.GaussianBlur(radius=0.8))
    ImageDraw.Draw(mouth_mask).rectangle([mx_start - 2, my - my_half, mx_end + 2, my + my_half], fill=255)
    mouth_neutral_2x = apply_unpremultiplied_mask(master_2x, mouth_mask)
    mouth_neutral_2x.save(cdir / "mouth_neutral_2x.png")
    mouth_neutral_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_neutral.png")

    cavity_color = (30, 12, 16, 255) if char_id != "malphas" else (55, 10, 15, 255)

    # B) mouth_talk
    mouth_talk_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_talk = ImageDraw.Draw(mouth_talk_2x)
    draw_talk.ellipse([mc_x - 6, my - 3, mc_x + 6, my + 3], fill=cavity_color, outline=(*ink, 255), width=1)
    draw_talk.line([mc_x - 4, my - 1, mc_x + 4, my - 1], fill=(245, 240, 235, 230), width=1)
    if char_id == "vladimir":
        draw_talk.polygon([(mc_x - 3, my - 2), (mc_x - 2, my + 1), (mc_x - 4, my - 2)], fill=(255, 255, 255, 255))
        draw_talk.polygon([(mc_x + 3, my - 2), (mc_x + 2, my + 1), (mc_x + 4, my - 2)], fill=(255, 255, 255, 255))
    mouth_talk_2x = put_unpremultiplied_alpha(mouth_talk_2x, radius=0.3)
    mouth_talk_2x.save(cdir / "mouth_talk_2x.png")
    mouth_talk_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_talk.png")

    # C) mouth_smirk
    mouth_smirk_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_smirk = ImageDraw.Draw(mouth_smirk_2x)
    draw_smirk.line([(mx_start, my + 1), (mc_x + 2, my), (mx_end, my - 2)], fill=(*lip_col, 255), width=2)
    draw_smirk.line([(mx_start, my), (mc_x + 2, my), (mx_end, my - 2)], fill=(*ink, 255), width=1)
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

    # E) Phonetic visemes: mouth_a, mouth_o, mouth_e, mouth_f positioned at (mc_x, my)
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

    # 7. Arms (arm_rest, arm_deal, arm_peek)
    arm_mask = Image.new("L", (224, 224), 0)
    for y in range(224):
        if y >= arms_y + 4:
            arm_mask.paste(255, (0, y, 224, y + 1))
        elif y >= arms_y:
            f = int(255 * (y - arms_y) / 4.0)
            arm_mask.paste(f, (0, y, 224, y + 1))
    arm_rest_2x = apply_unpremultiplied_mask(master_2x, arm_mask)
    arm_rest_2x.save(cdir / "arm_rest_2x.png")
    arm_rest_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_rest.png")

    # B) arm_deal: articulated forward-swept dealing hand + angled card in motion
    arm_deal_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    left_crop = arm_rest_2x.crop((0, 0, 112, 224))
    right_crop = arm_rest_2x.crop((112, 0, 224, 224))
    arm_deal_2x.paste(left_crop, (0, 0))
    arm_deal_2x.paste(right_crop, (110, 2))
    draw_deal = ImageDraw.Draw(arm_deal_2x)
    card_poly = [(118, 182), (144, 176), (150, 212), (124, 218)]
    shadow_poly = [(x + 2, y + 2) for x, y in card_poly]
    draw_deal.polygon(shadow_poly, fill=(0, 0, 0, 85))
    draw_deal.polygon(card_poly, fill=(250, 250, 248, 255), outline=(25, 20, 22, 255))
    pip_color = (200, 25, 35, 255) if char_id in ("julian", "malphas", "vladimir") else (0, 180, 220, 255) if char_id == "selene" else (25, 20, 25, 255)
    draw_deal.polygon([(134, 190), (138, 196), (134, 202), (130, 196)], fill=pip_color)
    for fx in (124, 132, 140):
        draw_deal.ellipse([fx - 3, 177, fx + 3, 182], fill=(*skin, 255), outline=(*ink, 255), width=1)
    arm_deal_2x.save(cdir / "arm_deal_2x.png")
    arm_deal_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_deal.png")

    # C) arm_peek: inward hole-card peek gesture
    arm_peek_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    arm_peek_2x.paste(left_crop, (2, -1))
    arm_peek_2x.paste(right_crop, (112, 0))
    draw_peek = ImageDraw.Draw(arm_peek_2x)
    px1, py1, px2, py2 = 75, 185, 101, 221
    card_back_rgb = cfg["card_back"]
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 + 2, py2 + 2], fill=(0, 0, 0, 80))
    draw_peek.rectangle([px1, py1, px2, py2], fill=(250, 250, 248, 255), outline=(25, 20, 22, 255), width=1)
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 - 2, py2 - 2], fill=(*card_back_rgb, 255), outline=(240, 235, 230, 255), width=1)
    draw_peek.polygon([(px2 - 6, py2), (px2, py2 - 6), (px2, py2)], fill=(245, 245, 240, 255), outline=(*ink, 255), width=1)
    for fx in (83, 91, 99):
        draw_peek.ellipse([fx - 3, py1 - 3, fx + 3, py1 + 2], fill=(*skin, 255), outline=(*ink, 255), width=1)
    arm_peek_2x.save(cdir / "arm_peek_2x.png")
    arm_peek_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_peek.png")

    # 8. Update bust_2x.png and bust.png to the exact neutral 7-layer composite
    bust_comp = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    for lname in ("shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
        limg = Image.open(cdir / f"{lname}_2x.png").convert("RGBA")
        bust_comp.alpha_composite(limg)
    bust_comp.save(cdir / "bust_2x.png")
    bust_comp.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "bust.png")


def run_all() -> None:
    for cid, cfg in DEOCCLUDE_CONFIGS.items():
        print(f"De-occluding faceplate & torso and building 19 puppet layers for {cid}...")
        deocclude_and_build_character(cid, cfg)
    print("All dealer faceplates and torsos de-occluded successfully.")


if __name__ == "__main__":
    run_all()
