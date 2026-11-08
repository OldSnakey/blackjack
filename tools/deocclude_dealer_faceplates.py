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

from collections import deque
import math
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
    "tiffany": {},
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
        "collar_y": 82,
        "arms_y": 152,
        "skin_color": (218, 182, 160),
        "ink_color": (25, 20, 22),
        "lip_color": (190, 110, 112),
        "vest_color": (215, 202, 175),
        "eye_left_pupil": (94, 46, 106, 53),
        "eye_left_line": (95, 50, 105, 50),
        "eye_right_pupil": (118, 46, 130, 53),
        "eye_right_line": (119, 50, 129, 50),
        "mouth_center": (112, 66),
        "mouth_y": 66,
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
    "professor": {
        "collar_y": 82,
        "arms_y": 156,
        "skin_color": (228, 184, 152),
        "ink_color": (24, 20, 18),
        "lip_color": (162, 98, 88),
        "vest_color": (18, 86, 56),
        "eye_left_pupil": (96, 42, 106, 46),
        "eye_left_line": (97, 44, 105, 44),
        "eye_right_pupil": (118, 42, 128, 46),
        "eye_right_line": (119, 44, 127, 44),
        "mouth_center": (112, 63),
        "mouth_y": 63,
        "mouth_x_span": (105, 119),
        "card_back": (20, 110, 75),
        "clean_table": False,
    },
}


BAYER_2X2 = np.array([[0.0, 0.5], [0.75, 0.25]], dtype=np.float32) - 0.375


def apply_crunchy_25d_pixel_pass(
    img_rgba: Image.Image,
    levels: int = 16,
    dither_strength: float = 8.0,
    add_silhouette_ink: bool = False,
) -> Image.Image:
    """
    Applies a crunchy 2.5D pixel-art shader pass (ordered 2x2 Bayer dithering + stepped
    palette quantization + optional 1px dark silhouette ink outline) while preserving
    100% opaque interior alpha and >500 unique colors on cel-shaded portraits.
    """
    arr = np.array(img_rgba.convert("RGBA"), dtype=np.float32)
    h, w, _ = arr.shape
    bayer = np.tile(BAYER_2X2, (h // 2 + 1, w // 2 + 1))[:h, :w, None]
    rgb = arr[:, :, :3] + bayer * dither_strength
    step = 255.0 / float(levels - 1)
    rgb_q = np.clip(np.round(rgb / step) * step, 0, 255).astype(np.uint8)
    alpha = arr[:, :, 3].astype(np.uint8)
    out = np.dstack([rgb_q, alpha])

    if add_silhouette_ink:
        mask = alpha > 200
        padded = np.pad(mask, 1, mode="constant", constant_values=False)
        dilated = (
            padded[:-2, 1:-1] | padded[2:, 1:-1] |
            padded[1:-1, :-2] | padded[1:-1, 2:]
        )
        outline = dilated & (alpha == 0)
        out[outline] = [14, 16, 22, 255]

    return Image.fromarray(out, "RGBA")


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


def build_chunky_paper_doll_character(char_id: str) -> None:
    """
    Builds a true 16-bit chunky pixel-art articulated paper-doll rig (112x112 1x and
    exact 2x2 integer-upscaled 224x224 2x) from `chunky_master_128.png` for `julian`
    and `professor`.

    Features:
    - True anatomical symmetry alignment (`cx = 63.5` on 128x128 -> `55.5` on 112x112).
    - Sleeveless waistcoat `torso` separated at the vertical black armhole seams from
      the full white dress-shirt sleeves on `arm_*`.
    - Tall cylindrical `neck` column extending high behind the head (`y_128 = 32..66`)
      so upward head lifts (`head_offset=(0, -6)`) never expose a transparent gap.
    - Closed-outline parabolic chin contour on `head` with 100% clean column-interpolated
      blank eye/brow/mouth faceplate.
    - Intact symmetrical `eyes_open`, `eyes_half`, `eyes_closed` and 8 centered pixel-art
      phonetic `mouth_*` visemes.
    - Full-volume 25px-diameter ascending forearm rising from an out-of-frame elbow into
      an angled dress-shirt cuff, sculpted hand, and canonical blue card back (`cards/back.png`).
    """
    cdir = CHARACTERS_DIR / char_id
    cdir.mkdir(parents=True, exist_ok=True)
    master_128_path = cdir / "chunky_master_128.png"
    if not master_128_path.exists():
        return

    raw_im = Image.open(master_128_path).convert("RGBA")
    raw_arr = np.array(raw_im)
    h, w, _ = raw_arr.shape

    # 1. Segment foreground character from background on 128x128 grid
    fg_mask_raw = np.zeros((h, w), dtype=bool)
    if char_id in ("tiffany", "selene", "malphas", "mortimer", "uriel", "vladimir"):
        fg_mask_raw = raw_arr[:, :, 3] > 128
    elif char_id == "julian":
        for y in range(6, h):
            xmin_s = 35 if y < 60 else 4
            xmax_s = 93 if y < 60 else 124
            dark_xs = [
                x
                for x in range(xmin_s, xmax_s)
                if int(raw_arr[y, x, 0]) + int(raw_arr[y, x, 1]) + int(raw_arr[y, x, 2]) < 120
            ]
            if len(dark_xs) >= 2:
                fg_mask_raw[y, dark_xs[0] : dark_xs[-1] + 1] = True
    else:
        bg_col = raw_arr[2, 2, :3].astype(int)
        diff_bg = np.abs(raw_arr[:, :, :3].astype(int) - bg_col).max(axis=2)
        visited = np.zeros((h, w), dtype=bool)
        q = deque()
        for x in range(w):
            if diff_bg[0, x] < 22:
                visited[0, x] = True
                q.append((0, x))
        for y in range(h):
            for x in (0, w - 1):
                if diff_bg[y, x] < 22 and not visited[y, x]:
                    visited[y, x] = True
                    q.append((y, x))
        while q:
            cy, cx = q.popleft()
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and diff_bg[ny, nx] < 24:
                    visited[ny, nx] = True
                    q.append((ny, nx))
        fg_mask_raw = ~visited

    # Align anatomical symmetry center to cx = 63.5 (55.5 in 112x112 crop x=8..120)
    char_rgba = np.zeros_like(raw_arr)
    fg_mask = np.zeros_like(fg_mask_raw)
    for y in range(h):
        if char_id == "malphas" and y >= 121:
            continue
        if char_id == "tiffany":
            shift_x = 1 if y <= 65 else 0
        elif char_id in ("mortimer", "uriel", "vladimir"):
            shift_x = 1
        elif char_id == "selene":
            shift_x = 2
        elif char_id == "malphas":
            shift_x = -3
        else:
            shift_x = 3
        for x in range(w):
            if fg_mask_raw[y, x] and 0 <= x + shift_x < w:
                char_rgba[y, x + shift_x] = raw_arr[y, x]
                fg_mask[y, x + shift_x] = True

    # Ensure outer sleeve borders at x=8 and x=119 have crisp dark 1px outlines inside the 112x112 crop window (x=8..120)
    for y in range(68, h):
        if fg_mask[y, 8]:
            char_rgba[y, 8] = [18, 16, 22, 255]
        if fg_mask[y, 119]:
            char_rgba[y, 119] = [18, 16, 22, 255]

    def jaw_y(x: int) -> int:
        dx = abs(x - 63.5)
        if char_id == "tiffany":
            return int(round(65.0 - 0.05 * (dx ** 2)))
        if char_id == "mortimer":
            return min(65, int(round(65.5 - 0.075 * (dx ** 2))))
        if char_id == "uriel":
            if 51 <= x <= 75:
                return min(69, int(round(72.0 - abs(x - 63.0))))
            return 56
        if char_id == "vladimir":
            return max(51, min(60, int(round(64.5 - dx))))
        if char_id == "selene":
            return int(round(79.0 - 0.06 * (dx ** 2)))
        if char_id == "malphas":
            return min(65, int(round(65.5 - max(0.0, dx - 3.5))))
        base_y = 61.5 if char_id == "julian" else 62.2
        return int(round(base_y - 0.045 * (dx ** 2)))

    def is_uriel_head_or_hair(y: int, x: int) -> bool:
        if not fg_mask[y, x]:
            return False
        if 51 <= x <= 75:
            if y <= jaw_y(x):
                r, g, b, _ = [int(v) for v in char_rgba[y, x]]
                # Exclude cream dress-shirt collar flanking the lower jaw at y >= 58
                if y >= 58 and (x <= 55 or x >= 71) and r > 225 and g > 210 and b > 200:
                    return False
                return True
            return False
        dist_out = max(0, (46 - x) if x < 63 else (x - 80))
        sh_y = 65 + (dist_out + 1) // 2
        if y < sh_y:
            r, g, b, _ = [int(v) for v in char_rgba[y, x]]
            # Exclude cream dress-shirt collar tips at x=47..50 and x=76..79 for y >= 58
            if y >= 58 and (47 <= x <= 50 or 76 <= x <= 79) and r > 225 and g > 210 and b > 200:
                return False
            return True
        return False

    def is_mortimer_head(y: int, x: int) -> bool:
        if not fg_mask[y, x]:
            return False
        if y <= 57:
            return True
        if y <= 65 and 51 <= x <= 76 and y <= jaw_y(x):
            r, g, b, _ = [int(v) for v in char_rgba[y, x]]
            # Exclude cool-white dress-shirt collar pixels (where B > R + 5) flanking the skull jaw
            if r > 180 and b > r + 5:
                return False
            return True
        return False

    def is_malphas_head(y: int, x: int) -> bool:
        if not fg_mask[y, x]:
            return False
        if y <= 52:
            return True
        if y <= 65 and 49 <= x <= 78 and y <= jaw_y(x):
            r, g, b, _ = [int(v) for v in char_rgba[y, x]]
            # Exclude white dress-shirt collar flanking the jaw
            if r > 180 and g > 180 and b > 180:
                return False
            return True
        return False

    def is_selene_head_or_hair(y: int, x: int) -> bool:
        if not fg_mask[y, x]:
            return False
        if 48 <= x <= 79:
            return y <= jaw_y(x)
        if y <= 58:
            return True
        if y <= 98:
            r, g, b, _ = [int(v) for v in char_rgba[y, x]]
            # Right-side hanging hair lock above the white shoulder pauldron (y <= 94, x >= 82)
            if y <= 94 and x >= 82:
                return True
            # Blue/green cyber hair and its dark outline (exclude white collar and silver shoulder panels)
            if r < 135 and not (r > 110 and g > 110 and b > 110):
                return True
        return False

    def left_vest_seam_x(y: int) -> int:
        if y < 65:
            return 25 if char_id == "tiffany" else 30
        if char_id == "tiffany":
            lx = 25
            for x in range(12, 36):
                r, g, b, a = [int(v) for v in char_rgba[y, x]]
                if a > 128 and (r + g + b) > 360:
                    lx = x + 1
            return lx
        best_x, best_lum = 30, 999
        for x in range(26, 36):
            r, g, b, a = char_rgba[y, x]
            if a > 0:
                lum = int(r) + int(g) + int(b)
                if lum < best_lum:
                    best_lum, best_x = lum, x
        return best_x

    def right_vest_seam_x(y: int) -> int:
        if y < 65:
            return 102 if char_id == "tiffany" else 97
        if char_id == "tiffany":
            rx = 102
            for x in range(115, 90, -1):
                r, g, b, a = [int(v) for v in char_rgba[y, x]]
                if a > 128 and (r + g + b) > 360:
                    rx = x - 1
            return rx
        best_x, best_lum = 97, 999
        for x in range(93, 103):
            r, g, b, a = char_rgba[y, x]
            if a > 0:
                lum = int(r) + int(g) + int(b)
                if lum < best_lum:
                    best_lum, best_x = lum, x
        return best_x

    # 2. TORSO & ARM_REST (on 128x128 grid)
    torso = np.zeros_like(char_rgba)
    arm_rest = np.zeros_like(char_rgba)
    if char_id == "selene":
        # Keep Selene's high white stand-up collar & long cyber-neck at exact 1:1 (y <= 88), and smoothly map her shoulder pauldrons & jacket (y_raw=88..122 -> y_dst=88..112)
        for y_dst in range(74, 113):
            y_raw = y_dst if y_dst <= 88 else min(h - 1, 88 + int(round((y_dst - 88) * (34.0 / 24.0))))
            for x in range(w):
                if fg_mask[y_raw, x] and not is_selene_head_or_hair(y_raw, x):
                    if y_raw >= 100 and (x < 33 or x > 94):
                        arm_rest[y_dst, x] = char_rgba[y_raw, x]
                        if 31 <= x <= 33 or 94 <= x <= 96:
                            torso[y_dst, x] = [18, 18, 22, 255]
                    else:
                        torso[y_dst, x] = char_rgba[y_raw, x]
                        if y_raw >= 100 and x in (33, 94):
                            arm_rest[y_dst, x] = char_rgba[y_raw, x]
    elif char_id == "malphas":
        # 1) Upper collar, chest V, and shoulders (y = 53..86)
        for y in range(53, 87):
            lx = 23 if y < 73 else (26 if y < 78 else (28 if y < 84 else 29))
            rx = 104 if y < 73 else (101 if y < 78 else (99 if y < 84 else 98))
            for x in range(w):
                if fg_mask[y, x]:
                    if is_malphas_head(y, x):
                        if y >= 54 and 51 <= x <= 76:
                            torso[y, x] = [219, 219, 219, 255] if (x < 54 or x > 73) else [159, 13, 0, 255]
                    elif y >= 68 and (x < lx or x > rx):
                        arm_rest[y, x] = char_rgba[y, x]
                        if lx - 1 <= x <= lx or rx <= x <= rx + 1:
                            torso[y, x] = [0, 0, 0, 255]
                    else:
                        torso[y, x] = char_rgba[y, x]
                        if y >= 68 and x in (lx, rx):
                            arm_rest[y, x] = char_rgba[y, x]
        # 2) Lower bust continuation down to the bottom of the 112x112 frame (y = 87..117)
        for y in range(87, 118):
            lx = 29 + (y - 87) // 12
            rx = 98 - (y - 87) // 12
            sl_x0 = max(9, 11 - (y - 86) // 5)
            sr_x1 = min(115, 112 + (y - 86) // 5)
            # Outer notched lapel lines converging from (36, 91) at y=92 to (50, 77) at y=117
            lapel_out_l = int(round(36.0 + max(0, y - 92) * (14.0 / 25.0)))
            lapel_out_r = int(round(91.0 - max(0, y - 92) * (14.0 / 25.0)))
            xs_row = np.where(fg_mask[y])[0]
            raw_x0 = int(xs_row[0]) if len(xs_row) > 0 else 55
            raw_x1 = int(xs_row[-1]) if len(xs_row) > 0 else 72
            # A. Waistcoat & center shirt placket (lx .. rx)
            for x in range(lx, rx + 1):
                if x in (lx, lx + 1, rx - 1, rx):
                    torso[y, x] = [0, 0, 0, 255]
                elif x in (lapel_out_l, lapel_out_r) and y >= 92:
                    torso[y, x] = [82, 82, 81, 255]
                elif x in (lapel_out_l - 1, lapel_out_r + 1) and y >= 92:
                    torso[y, x] = [30, 31, 34, 255]
                elif fg_mask[y, x] and (raw_x0 + 4 <= x <= raw_x1 - 4) and (lapel_out_l < x < lapel_out_r):
                    px_v = char_rgba[y, x]
                    if y >= 112 and (x < 59 or x > 69) and int(px_v[0]) < 45 and int(px_v[1]) < 45:
                        torso[y, x] = [57, 57, 57, 255]
                    else:
                        torso[y, x] = px_v
                else:
                    if x >= rx - 4:
                        torso[y, x] = [30, 31, 34, 255]
                    elif x in (lx + 2, rx - 5):
                        torso[y, x] = [60, 61, 60, 255]
                    else:
                        torso[y, x] = [57, 57, 57, 255]
            # B. Left & right full-height white dress-shirt sleeves (arm_rest)
            for x in range(sl_x0, lx + 1):
                if x in (sl_x0, lx - 1, lx):
                    arm_rest[y, x] = [0, 0, 0, 255]
                elif x <= sl_x0 + 3 or x == lx - 2 or ((y - 87) + (x - sl_x0)) in (16, 17, 30, 31):
                    arm_rest[y, x] = [219, 219, 219, 255]
                else:
                    arm_rest[y, x] = [255, 255, 255, 255]
            for x in range(rx, sr_x1 + 1):
                if x in (rx, rx + 1, sr_x1):
                    arm_rest[y, x] = [0, 0, 0, 255]
                elif x >= sr_x1 - 3 or x == rx + 2 or ((y - 87) + (sr_x1 - x)) in (16, 17, 30, 31):
                    arm_rest[y, x] = [219, 219, 219, 255]
                else:
                    arm_rest[y, x] = [255, 255, 255, 255]
    else:
        for y in range(52 if char_id in ("uriel", "vladimir") else 56, h):
            if char_id == "mortimer":
                lx = 28 if y <= 107 else 29
                rx = 97 if y <= 107 else 96
            elif char_id == "uriel":
                lx = max(26, 31 - max(0, y - 72) // 7)
                rx = min(100, 95 + max(0, y - 72) // 7)
            elif char_id == "vladimir":
                lx = 28 if y <= 95 else (29 if y <= 110 else 31)
                rx = 98 if y <= 95 else (97 if y <= 110 else 95)
            else:
                lx = left_vest_seam_x(y)
                rx = right_vest_seam_x(y)
            for x in range(w):
                if fg_mask[y, x]:
                    if y <= jaw_y(x) and 53 <= x <= 74:
                        neck_fill = (
                            [185, 118, 102, 255]
                            if char_id == "tiffany"
                            else (
                                [42, 38, 36, 255]
                                if char_id == "mortimer"
                                else (
                                    [203, 117, 108, 255]
                                    if char_id == "uriel"
                                    else ([148, 152, 164, 255] if char_id == "vladimir" else [145, 98, 78, 255])
                                )
                            )
                        )
                        if char_id in ("mortimer", "uriel", "vladimir"):
                            torso[y, x] = neck_fill
                        else:
                            torso[y, x] = [214, 214, 220, 255] if (x < 55 or x > 72) else neck_fill
                    elif y >= (70 if char_id == "uriel" else (66 if char_id == "mortimer" else 65)) and (x < lx or x > rx):
                        arm_rest[y, x] = char_rgba[y, x]
                        if lx - 2 <= x <= lx or rx <= x <= rx + 2:
                            torso[y, x] = [18, 18, 22, 255]
                    else:
                        if char_id == "uriel" and is_uriel_head_or_hair(y, x):
                            # Fill behind Uriel's shoulder-length golden hair following sloped shoulder seam
                            if 52 <= x <= 74:
                                torso[y, x] = [203, 117, 108, 255]
                            elif 32 <= x <= 94:
                                dist_out = max(0, (46 - x) if x < 63 else (x - 80))
                                sh_y = 66 + (dist_out + 1) // 2
                                if y == sh_y:
                                    torso[y, x] = [18, 16, 20, 255]
                                elif y > sh_y:
                                    torso[y, x] = [176, 130, 40, 255] if (43 <= x <= 83) else [114, 150, 196, 255]
                            continue
                        torso[y, x] = char_rgba[y, x]
                        if y >= (70 if char_id == "uriel" else (66 if char_id == "mortimer" else 65)) and (x == lx or x == rx):
                            arm_rest[y, x] = char_rgba[y, x]

    # 3. NECK: Tall cylindrical column extending up to y=32 behind the head
    neck = np.zeros_like(char_rgba)
    neck_y_bot = 82 if char_id == "selene" else (74 if char_id == "uriel" else (71 if char_id == "mortimer" else 68))
    nx0, nx1 = (51, 76) if char_id == "uriel" else ((51, 77) if char_id in ("mortimer", "vladimir") else (49, 79))
    for y in range(32, neck_y_bot):
        for x in range(nx0, nx1):
            if y <= jaw_y(x):
                if x in (nx0, nx1 - 1):
                    neck[y, x] = [18, 16, 20, 255]
                elif x in (nx0 + 1, nx1 - 2):
                    neck[y, x] = (
                        [165, 104, 90, 255]
                        if char_id == "tiffany"
                        else (
                            [130, 4, 0, 255]
                            if char_id == "malphas"
                            else (
                                [165, 148, 122, 255]
                                if char_id == "mortimer"
                                else (
                                    [165, 81, 85, 255]
                                    if char_id == "uriel"
                                    else ([122, 126, 138, 255] if char_id == "vladimir" else [125, 80, 64, 255])
                                )
                            )
                        )
                    )
                else:
                    dist_c = abs(x - 63.5) / 14.0
                    if char_id == "tiffany":
                        r_c = int(round(238 - 30 * dist_c))
                        g_c = int(round(166 - 26 * dist_c))
                        b_c = int(round(146 - 22 * dist_c))
                    elif char_id == "selene":
                        r_c = int(round(196 - 32 * dist_c))
                        g_c = int(round(154 - 26 * dist_c))
                        b_c = int(round(126 - 22 * dist_c))
                    elif char_id == "malphas":
                        r_c = int(round(210 - 50 * dist_c))
                        g_c = int(round(26 - 14 * dist_c))
                        b_c = int(round(8 - 7 * dist_c))
                    elif char_id == "mortimer":
                        ridge = -18 if (y % 3 == 0) else 0
                        r_c = int(round(224 + ridge - 32 * dist_c))
                        g_c = int(round(208 + ridge - 30 * dist_c))
                        b_c = int(round(180 + ridge - 28 * dist_c))
                    elif char_id == "uriel":
                        r_c = int(round(203 - 24 * dist_c))
                        g_c = int(round(117 - 20 * dist_c))
                        b_c = int(round(108 - 18 * dist_c))
                    elif char_id == "vladimir":
                        r_c = int(round(192 - 36 * dist_c))
                        g_c = int(round(196 - 36 * dist_c))
                        b_c = int(round(208 - 34 * dist_c))
                    else:
                        r_c = int(round(178 - 32 * dist_c))
                        g_c = int(round(122 - 26 * dist_c))
                        b_c = int(round(96 - 22 * dist_c))
                    neck[y, x] = [r_c, g_c, b_c, 255]
            elif fg_mask[y, x]:
                neck[y, x] = char_rgba[y, x]
            elif char_id == "mortimer" and 51 <= x <= 76:
                neck[y, x] = [42, 38, 36, 255]

    # 4. HEAD: Closed-outline jawline + 100% clean blank faceplate
    head = np.zeros_like(char_rgba)
    if char_id == "selene":
        for y in range(1, 100):
            for x in range(20, 106):
                if is_selene_head_or_hair(y, x):
                    head[y, x] = char_rgba[y, x]
    elif char_id == "malphas":
        for y in range(6, 66):
            for x in range(20, 108):
                if is_malphas_head(y, x):
                    head[y, x] = char_rgba[y, x]
    elif char_id == "mortimer":
        for y in range(2, 66):
            for x in range(36, 92):
                if is_mortimer_head(y, x):
                    head[y, x] = char_rgba[y, x]
        # Clean cheekbone dot artifacts at y=46, x=55..58 and x=70..73
        for y in range(45, 48):
            for x in list(range(54, 59)) + list(range(69, 74)):
                if head[y, x, 3] > 0 and int(head[y, x, 0]) < 180:
                    head[y, x] = [216, 199, 168, 255]
        # Close 1px dark jaw outline along bottom of skull jaw
        for x in range(51, 77):
            jy = jaw_y(x)
            if head[jy, x, 3] > 0:
                head[jy, x] = [19, 18, 19, 255]
                if jy - 1 >= 0 and head[jy - 1, x, 3] > 0:
                    head[jy - 1, x] = [175, 155, 128, 255]
    elif char_id == "uriel":
        for y in range(1, 74):
            for x in range(28, 98):
                if is_uriel_head_or_hair(y, x):
                    head[y, x] = char_rgba[y, x]
        for x in range(52, 75):
            jy = jaw_y(x)
            if head[jy, x, 3] > 0:
                head[jy, x] = [18, 16, 20, 255]
    else:
        head_y_top = 1 if char_id in ("tiffany", "vladimir") else 6
        head_y_bot = 66 if char_id == "tiffany" else 64
        for y in range(head_y_top, head_y_bot):
            for x in range(34, 96):
                if fg_mask[y, x] and y <= jaw_y(x):
                    if char_id == "vladimir" and y >= 52:
                        r_h, g_h, b_h, _ = [int(v) for v in char_rgba[y, x]]
                        # Exclude white dress-shirt collar triangles outside the jawline
                        if r_h > 200 and g_h > 200 and b_h > 200 and (x <= 55 or x >= 72):
                            continue
                    head[y, x] = char_rgba[y, x]
        for x in range(52 if char_id == "vladimir" else 50, 76 if char_id == "vladimir" else 78):
            jy = jaw_y(x)
            if head[jy, x, 3] > 0:
                head[jy, x] = [24, 16, 18, 255] if char_id in ("tiffany", "vladimir") else [48, 32, 28, 255]
                if jy - 1 >= 0 and char_id == "julian":
                    head[jy - 1, x] = [125, 80, 62, 255]

    # 5. EYES + BROWS (and glasses for professor / cyber-visor for selene)
    eyes_open = np.zeros_like(char_rgba)
    if char_id == "julian":
        eye_sockets = ((50, 61, 30, 39), (66, 77, 30, 39))
    elif char_id == "tiffany":
        eye_sockets = ((48, 59, 33, 41), (68, 79, 33, 41))
    elif char_id == "selene":
        # Selene: extract eyebrows + crimson cyber-visor + neon-green eyes (x=42..83, y=37..52)
        eye_sockets = ((42, 83, 37, 52),)
    elif char_id == "malphas":
        eye_sockets = ((48, 60, 34, 41), (67, 79, 34, 41))
    elif char_id == "mortimer":
        eye_sockets = ((52, 61, 37, 43), (66, 75, 37, 43))
    elif char_id == "uriel":
        eye_sockets = ((50, 60, 40, 47), (66, 76, 40, 47))
    elif char_id == "vladimir":
        eye_sockets = ((50, 61, 30, 37), (66, 77, 30, 37))
    else:
        # Professor Edward: extract eyebrows + wire-rimmed glasses + eyes (x=48..79, y=31..41)
        eye_sockets = ((48, 79, 31, 41),)

    for x0, x1, y0, y1 in eye_sockets:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                px = head[y, x]
                r_p, g_p, b_p, a_p = int(px[0]), int(px[1]), int(px[2]), int(px[3])
                if char_id == "tiffany":
                    is_plain_skin = (r_p >= 235 and 148 <= g_p <= 210 and 130 <= b_p <= 190)
                elif char_id == "selene":
                    # Exclude dark blue/green hair on left (x <= 46) or right (x >= 80, y <= 40) and plain tan cheek/bridge skin (218, 184, 153)
                    is_hair_side = (x <= 46 or (x >= 80 and y <= 40)) and (b_p >= r_p or (g_p > r_p and r_p < 95) or (r_p < 35 and g_p < 35 and b_p < 35))
                    is_tan_skin = (195 <= r_p <= 230 and 155 <= g_p <= 195 and 125 <= b_p <= 168)
                    is_plain_skin = is_hair_side or is_tan_skin
                elif char_id == "malphas":
                    # Plain crimson skin (R >= 175, G < 130, G - B < 35) stays transparent on eyes_*
                    is_plain_skin = (r_p >= 175 and g_p < 130 and (g_p - b_p) < 35)
                elif char_id == "mortimer":
                    # Only dark hollow sockets (R < 110, G < 110) and violet soul-fire stay opaque on eyes_*
                    is_plain_skin = not (r_p < 110 and g_p < 110)
                elif char_id == "uriel":
                    # Plain peach face skin (R >= 240, G >= 185, B >= 165) and temple shading stay transparent on eyes_*
                    is_plain_skin = (x in (50, 76)) or (r_p >= 240 and g_p >= 185 and b_p >= 165)
                elif char_id == "vladimir":
                    # Plain pale vampire skin (R >= 165, G >= 165, B >= 165) stays transparent on eyes_*
                    is_plain_skin = (x in (50, 77)) or (r_p >= 165 and g_p >= 165 and b_p >= 165)
                else:
                    is_plain_skin = (r_p > 175 and g_p > 110 and b_p > 80 and (r_p - g_p) > 32 and (r_p - b_p) > 55)
                if not is_plain_skin:
                    eyes_open[y, x] = px
        for x in range(x0, x1 + 1):
            if char_id == "tiffany":
                col_skin = head[42, x, :3].astype(np.uint8)
                for y in range(y0, y1 + 1):
                    head[y, x] = [col_skin[0], col_skin[1], col_skin[2], 255]
            elif char_id == "selene":
                for y in range(y0, y1 + 1):
                    if eyes_open[y, x, 3] > 0:
                        dist_c = abs(x - 63.5) / 18.5
                        r_s = int(round(218 - 32 * (dist_c ** 1.6)))
                        g_s = int(round(184 - 30 * (dist_c ** 1.6)))
                        b_s = int(round(153 - 26 * (dist_c ** 1.6)))
                        head[y, x] = [r_s, g_s, b_s, 255]
            elif char_id == "malphas":
                fill_s = [212, 44, 28, 255] if (x <= 50 or x >= 77) else [237, 70, 54, 255]
                for y in range(y0, y1 + 1):
                    if head[y, x, 3] > 0 and x not in (48, 79):
                        head[y, x] = fill_s
            elif char_id == "mortimer":
                fill_s = [216, 199, 168, 255] if (x <= 52 or x >= 75) else [243, 232, 210, 255]
                for y in range(y0, y1 + 1):
                    if head[y, x, 3] > 0:
                        head[y, x] = fill_s
            elif char_id == "uriel":
                fill_s = [216, 133, 125, 255] if (x <= 51 or x >= 75) else [255, 201, 181, 255]
                for y in range(y0, y1 + 1):
                    if head[y, x, 3] > 0:
                        head[y, x] = fill_s
            elif char_id == "vladimir":
                col_skin = head[41, max(52, min(75, x)), :3].astype(np.uint8)
                for y in range(y0, y1 + 1):
                    if head[y, x, 3] > 0:
                        head[y, x] = [col_skin[0], col_skin[1], col_skin[2], 255]
            else:
                ref_x = max(50, min(77, x))
                bot_rgb = head[y1 + 2, ref_x, :3].astype(np.float32)
                top_rgb = head[y0 - 2, ref_x, :3].astype(np.float32)
                span = float(max(1, (y1 + 2) - (y0 - 2)))
                for y in range(y0, y1 + 1):
                    t = (y - (y0 - 2)) / span
                    interp = np.round((1.0 - t) * top_rgb + t * bot_rgb).astype(np.uint8)
                    head[y, x] = [interp[0], interp[1], interp[2], 255]

    # Build eyes_half and eyes_closed on 128x128 grid
    eyes_half = eyes_open.copy()
    eyes_closed = eyes_open.copy()
    if char_id == "julian":
        for sx0, sx1 in ((51, 59), (67, 75)):
            eyes_half[35:37, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                eyes_half[36, x] = [28, 20, 18, 255]
            eyes_closed[34:39, sx0 - 1 : sx1 + 2] = 0
            for x in range(sx0, sx1 + 1):
                ly = 37 if (sx0 < x < sx1) else 36
                eyes_closed[ly, x] = [28, 20, 18, 255]
                eyes_closed[ly - 1, x] = [148, 96, 74, 255]
    elif char_id == "tiffany":
        for sx0, sx1 in ((49, 58), (68, 77)):
            eyes_half[38:40, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                eyes_half[39, x] = [18, 12, 14, 255]
            eyes_closed[37:42, sx0 - 1 : sx1 + 2] = 0
            for x in range(sx0, sx1 + 1):
                ly = 40 if (sx0 + 1 <= x <= sx1 - 1) else 39
                eyes_closed[ly, x] = [18, 12, 14, 255]
                eyes_closed[ly - 1, x] = [215, 130, 115, 255]
    elif char_id == "selene":
        # Blink eyelids behind the crimson cyber-visor
        for sx0, sx1 in ((48, 56), (71, 79)):
            for y in range(43, 46):
                for x in range(sx0, sx1 + 1):
                    eyes_half[y, x] = [215, 95, 87, 255]
            for x in range(sx0, sx1 + 1):
                eyes_half[45, x] = [18, 14, 16, 255]
            for y in range(42, 49):
                for x in range(sx0, sx1 + 1):
                    eyes_closed[y, x] = [215, 95, 87, 255]
            for x in range(sx0, sx1 + 1):
                ly = 46 if (sx0 + 1 <= x <= sx1 - 1) else 45
                eyes_closed[ly, x] = [18, 14, 16, 255]
                eyes_closed[ly - 1, x] = [172, 92, 86, 255]
    elif char_id == "malphas":
        for sx0, sx1 in ((52, 59), (68, 75)):
            eyes_half[38:40, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                eyes_half[39, x] = [0, 0, 0, 255]
            eyes_closed[38:42, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                ly = 40 if (sx0 + 1 <= x <= sx1 - 1) else 39
                eyes_closed[ly, x] = [0, 0, 0, 255]
                eyes_closed[ly - 1, x] = [189, 26, 7, 255]
    elif char_id == "mortimer":
        for sx0, sx1 in ((53, 59), (68, 74)):
            for y in range(38, 40):
                for x in range(sx0, sx1 + 1):
                    eyes_half[y, x] = [19, 18, 19, 255]
            for y in range(38, 42):
                for x in range(sx0, sx1 + 1):
                    eyes_closed[y, x] = [19, 18, 19, 255]
            eyes_closed[40, (sx0 + sx1) // 2] = [92, 42, 128, 255]
    elif char_id == "uriel":
        for sx0, sx1 in ((52, 57), (68, 73)):
            eyes_half[44:46, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                eyes_half[45, x] = [18, 16, 20, 255]
            eyes_closed[42:48, sx0 - 2 : sx1 + 3] = 0
            for x in range(sx0, sx1 + 1):
                ly = 46 if (sx0 < x < sx1) else 45
                eyes_closed[ly, x] = [18, 16, 20, 255]
                eyes_closed[ly - 1, x] = [203, 117, 108, 255]
    elif char_id == "vladimir":
        for sx0, sx1 in ((53, 59), (68, 74)):
            for x in range(sx0, sx1 + 1):
                eyes_half[33, x] = [18, 16, 22, 255]
            for y in range(32, 36):
                for x in range(sx0 - 1, sx1 + 2):
                    eyes_closed[y, x] = [145, 149, 158, 255]
            for x in range(sx0 - 1, sx1 + 2):
                ly = 35 if (sx0 <= x <= sx1) else 34
                eyes_closed[ly, x] = [18, 16, 22, 255]
                eyes_closed[ly - 1, x] = [114, 110, 112, 255]
    else:
        for sx0, sx1 in ((52, 59), (68, 75)):
            eyes_half[36:38, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                eyes_half[37, x] = [28, 22, 20, 255]
            eyes_closed[36:40, sx0 : sx1 + 1] = 0
            for x in range(sx0, sx1 + 1):
                eyes_closed[38, x] = [28, 22, 20, 255]
                eyes_closed[37, x] = [155, 105, 82, 255]
            eyes_open[36, sx0 + 1] = [220, 245, 255, 255]
            eyes_closed[36, sx0 + 1] = [220, 245, 255, 255]

    # 6. MOUTH_NEUTRAL + 7 PHONETIC VISEMES centered at CX = 63.5
    mouth_neutral = np.zeros_like(char_rgba)
    if char_id == "tiffany":
        m_y0, m_y1, m_x0, m_x1 = 54, 60, 58, 70
    elif char_id == "selene":
        m_y0, m_y1, m_x0, m_x1 = 65, 71, 58, 71
    elif char_id == "malphas":
        m_y0, m_y1, m_x0, m_x1 = 52, 58, 55, 73
    elif char_id == "mortimer":
        m_y0, m_y1, m_x0, m_x1 = 51, 60, 54, 74
    elif char_id == "uriel":
        m_y0, m_y1, m_x0, m_x1 = 58, 63, 56, 71
    elif char_id == "vladimir":
        m_y0, m_y1, m_x0, m_x1 = 48, 54, 57, 72
    else:
        m_y0, m_y1, m_x0, m_x1 = 50, 54, 56, 72
    clean_cheek_rgb = head[m_y0 - 1, 58, :3].astype(np.float32)
    for y in range(m_y0, m_y1):
        for x in range(m_x0, m_x1):
            px_m = head[y, x]
            if char_id == "tiffany":
                if not (int(px_m[0]) >= 245 and int(px_m[1]) >= 170):
                    mouth_neutral[y, x] = px_m
            elif char_id == "selene":
                if not (int(px_m[0]) >= 200 and int(px_m[1]) >= 170):
                    mouth_neutral[y, x] = px_m
            elif char_id == "malphas":
                if y <= 53 and 61 <= x <= 66:
                    continue
                if int(px_m[0]) <= 145 and int(px_m[1]) <= 12:
                    mouth_neutral[y, x] = px_m
                    head[y, x] = [212, 44, 28, 255] if 58 <= x <= 69 else [189, 26, 7, 255]
                continue
            elif char_id == "mortimer":
                in_teeth_poly = (
                    (51 <= y <= 54 and 55 <= x <= 72)
                    or (55 <= y <= 57 and 56 <= x <= 71)
                    or (y == 58 and 58 <= x <= 69)
                    or (y == 59 and 60 <= x <= 67)
                )
                if in_teeth_poly:
                    if y >= 53 and 56 <= x <= 71 and (int(px_m[0]) < 180 or (54 <= y <= 58 and 57 <= x <= 70)):
                        mouth_neutral[y, x] = px_m
                    head[y, x] = [243, 232, 210, 255] if 58 <= x <= 69 else [216, 199, 168, 255]
                continue
            elif char_id == "uriel":
                if int(px_m[0]) < 215 and int(px_m[1]) < 125:
                    mouth_neutral[y, x] = px_m
                head[y, x] = [255, 201, 181, 255]
                continue
            elif char_id == "vladimir":
                if int(px_m[0]) < 175 and int(px_m[1]) < 175:
                    mouth_neutral[y, x] = px_m
                col_m = head[47, 58, :3].astype(np.uint8)
                head[y, x] = [col_m[0], col_m[1], col_m[2], 255]
                continue
            else:
                mouth_neutral[y, x] = px_m
            top_m = head[m_y0 - 1, x, :3].astype(np.float32)
            t = (y - (m_y0 - 1)) / float(max(1, m_y1 - m_y0 + 1))
            interp = np.round((1.0 - t) * top_m + t * clean_cheek_rgb).astype(np.uint8)
            head[y, x] = [interp[0], interp[1], interp[2], 255]

    def build_viseme_128(vname: str) -> np.ndarray:
        if char_id == "mortimer" and vname != "mouth_smirk":
            m = mouth_neutral.copy()
            # Articulate skeletal jaw + glowing violet soul-fire between upper & lower teeth
            x_span = {
                "mouth_o": (61, 66),
                "mouth_a": (58, 69),
                "mouth_e": (57, 70),
                "mouth_f": (59, 68),
                "mouth_talk": (59, 68),
                "mouth_gasp": (58, 69),
            }.get(vname, (59, 68))
            gx0, gx1 = x_span
            y_rows = (54, 55, 56, 57) if vname in ("mouth_a", "mouth_gasp") else (55, 56)
            for gy in y_rows:
                for gx in range(gx0, gx1 + 1):
                    if gx in (gx0, gx1):
                        m[gy, gx] = [19, 18, 19, 255]
                    elif gy == y_rows[-1] and gx0 + 1 < gx < gx1 - 1:
                        m[gy, gx] = [188, 96, 252, 255] if vname != "mouth_f" else [118, 52, 168, 255]
                    else:
                        m[gy, gx] = [42, 18, 58, 255]
            return m
        m = np.zeros_like(char_rgba)
        if vname == "mouth_o":
            rows = [
                (50, {61: (135, 78, 64), 62: (72, 34, 30), 63: (62, 28, 26), 64: (62, 28, 26), 65: (72, 34, 30), 66: (135, 78, 64)}),
                (51, {60: (145, 86, 70), 61: (55, 24, 22), 62: (230, 225, 225), 63: (238, 234, 234), 64: (238, 234, 234), 65: (230, 225, 225), 66: (55, 24, 22), 67: (145, 86, 70)}),
                (52, {60: (145, 86, 70), 61: (48, 20, 20), 62: (165, 58, 58), 63: (185, 68, 68), 64: (185, 68, 68), 65: (165, 58, 58), 66: (48, 20, 20), 67: (145, 86, 70)}),
                (53, {61: (135, 78, 64), 62: (85, 42, 36), 63: (72, 34, 30), 64: (72, 34, 30), 65: (85, 42, 36), 66: (135, 78, 64)}),
            ]
        elif vname == "mouth_a":
            rows = [
                (50, {59: (135, 78, 64), 60: (72, 34, 30), 61: (58, 26, 24), 62: (58, 26, 24), 63: (58, 26, 24), 64: (58, 26, 24), 65: (58, 26, 24), 66: (58, 26, 24), 67: (72, 34, 30), 68: (135, 78, 64)}),
                (51, {58: (145, 86, 70), 59: (55, 24, 22), 60: (225, 220, 220), 61: (238, 235, 235), 62: (242, 240, 240), 63: (242, 240, 240), 64: (242, 240, 240), 65: (242, 240, 240), 66: (238, 235, 235), 67: (225, 220, 220), 68: (55, 24, 22), 69: (145, 86, 70)}),
                (52, {59: (145, 86, 70), 60: (48, 20, 20), 61: (155, 52, 52), 62: (182, 66, 66), 63: (192, 74, 74), 64: (192, 74, 74), 65: (182, 66, 66), 66: (155, 52, 52), 67: (48, 20, 20), 68: (145, 86, 70)}),
                (53, {60: (135, 78, 64), 61: (88, 44, 38), 62: (72, 34, 30), 63: (68, 32, 28), 64: (68, 32, 28), 65: (72, 34, 30), 66: (88, 44, 38), 67: (135, 78, 64)}),
            ]
        elif vname == "mouth_e":
            rows = [
                (50, {58: (135, 78, 64), 59: (72, 34, 30), 60: (58, 26, 24), 61: (58, 26, 24), 62: (58, 26, 24), 63: (58, 26, 24), 64: (58, 26, 24), 65: (58, 26, 24), 66: (58, 26, 24), 67: (58, 26, 24), 68: (72, 34, 30), 69: (135, 78, 64)}),
                (51, {58: (55, 24, 22), 59: (230, 226, 226), 60: (242, 240, 240), 61: (242, 240, 240), 62: (242, 240, 240), 63: (242, 240, 240), 64: (242, 240, 240), 65: (242, 240, 240), 66: (242, 240, 240), 67: (242, 240, 240), 68: (230, 226, 226), 69: (55, 24, 22)}),
                (52, {59: (88, 44, 38), 60: (68, 32, 28), 61: (165, 58, 58), 62: (175, 64, 64), 63: (175, 64, 64), 64: (175, 64, 64), 65: (175, 64, 64), 66: (165, 58, 58), 67: (68, 32, 28), 68: (88, 44, 38)}),
            ]
        elif vname == "mouth_f":
            rows = [
                (50, {59: (72, 34, 30), 60: (58, 26, 24), 61: (58, 26, 24), 62: (58, 26, 24), 63: (58, 26, 24), 64: (58, 26, 24), 65: (58, 26, 24), 66: (58, 26, 24), 67: (58, 26, 24), 68: (72, 34, 30)}),
                (51, {59: (135, 78, 64), 60: (238, 235, 235), 61: (242, 240, 240), 62: (242, 240, 240), 63: (242, 240, 240), 64: (242, 240, 240), 65: (242, 240, 240), 66: (242, 240, 240), 67: (238, 235, 235), 68: (135, 78, 64)}),
                (52, {60: (145, 86, 70), 61: (112, 56, 48), 62: (112, 56, 48), 63: (112, 56, 48), 64: (112, 56, 48), 65: (112, 56, 48), 66: (112, 56, 48), 67: (145, 86, 70)}),
            ]
        elif vname == "mouth_talk":
            rows = [
                (50, {60: (72, 34, 30), 61: (58, 26, 24), 62: (58, 26, 24), 63: (58, 26, 24), 64: (58, 26, 24), 65: (58, 26, 24), 66: (58, 26, 24), 67: (72, 34, 30)}),
                (51, {59: (55, 24, 22), 60: (235, 232, 232), 61: (240, 238, 238), 62: (240, 238, 238), 63: (240, 238, 238), 64: (240, 238, 238), 65: (240, 238, 238), 66: (240, 238, 238), 67: (235, 232, 232), 68: (55, 24, 22)}),
                (52, {60: (68, 32, 28), 61: (175, 62, 62), 62: (185, 68, 68), 63: (185, 68, 68), 64: (185, 68, 68), 65: (185, 68, 68), 66: (175, 62, 62), 67: (68, 32, 28)}),
            ]
        elif vname == "mouth_gasp":
            rows = [
                (49, {61: (72, 34, 30), 62: (58, 26, 24), 63: (58, 26, 24), 64: (58, 26, 24), 65: (58, 26, 24), 66: (72, 34, 30)}),
                (50, {60: (55, 24, 22), 61: (235, 232, 232), 62: (240, 238, 238), 63: (240, 238, 238), 64: (240, 238, 238), 65: (240, 238, 238), 66: (235, 232, 232), 67: (55, 24, 22)}),
                (51, {60: (48, 20, 20), 61: (38, 16, 18), 62: (32, 12, 14), 63: (32, 12, 14), 64: (32, 12, 14), 65: (32, 12, 14), 66: (38, 16, 18), 67: (48, 20, 20)}),
                (52, {60: (48, 20, 20), 61: (165, 58, 58), 62: (185, 68, 68), 63: (192, 74, 74), 64: (192, 74, 74), 65: (185, 68, 68), 66: (165, 58, 58), 67: (48, 20, 20)}),
                (53, {61: (85, 42, 36), 62: (68, 32, 28), 63: (68, 32, 28), 64: (68, 32, 28), 65: (68, 32, 28), 66: (85, 42, 36)}),
            ]
        else:  # mouth_smirk
            m = mouth_neutral.copy()
            v_dy = 16 if char_id == "selene" else (9 if char_id == "uriel" else (5 if char_id == "tiffany" else (4 if char_id in ("malphas", "mortimer") else 0)))
            m[50 + v_dy : 55 + v_dy, 65:72] = 0
            lip_out = (213, 57, 46) if char_id == "tiffany" else ((144, 74, 71) if char_id == "selene" else ((94, 4, 1) if char_id == "malphas" else ((19, 18, 19) if char_id == "mortimer" else (82, 42, 36))))
            lip_mid = (236, 99, 91) if char_id == "tiffany" else ((215, 95, 87) if char_id == "selene" else ((159, 13, 0) if char_id == "malphas" else ((148, 136, 114) if char_id == "mortimer" else (155, 95, 78))))
            for sx, sy, col in [
                (65, 51 + v_dy, lip_out),
                (66, 51 + v_dy, lip_out),
                (67, 50 + v_dy, lip_out),
                (68, 50 + v_dy, lip_out),
                (69, 49 + v_dy, lip_mid),
                (66, 52 + v_dy, lip_mid),
                (67, 51 + v_dy, lip_mid),
            ]:
                if 0 <= sy < h and 0 <= sx < w:
                    m[sy, sx] = [col[0], col[1], col[2], 255]
            return m

        v_dy = 16 if char_id == "selene" else (9 if char_id == "uriel" else (5 if char_id == "tiffany" else (4 if char_id in ("malphas", "mortimer") else 0)))
        for y, row_cols in rows:
            for x, (r, g, b) in row_cols.items():
                if char_id == "tiffany" and r < 150 and g < 95 and b < 80 and (r > 60):
                    r, g, b = 213, 57, 46
                elif char_id == "selene" and r < 150 and g < 95 and b < 80 and (r > 60):
                    r, g, b = 215, 95, 87
                elif char_id == "malphas" and r < 150 and g < 95 and b < 80 and (r > 60):
                    r, g, b = 159, 13, 0
                elif char_id == "vladimir" and r < 150 and g < 95 and b < 80 and (r > 60):
                    r, g, b = 114, 110, 112
                elif char_id == "mortimer":
                    if r > 150 and g < 80 and b < 80:
                        r, g, b = 168, 82, 240
                    elif r < 150 and g < 95 and b < 80 and r > 60:
                        r, g, b = 148, 136, 114
                m[y + v_dy, x] = [r, g, b, 255]
        if char_id == "vladimir" and vname in ("mouth_a", "mouth_e", "mouth_talk", "mouth_gasp"):
            m[52, 60] = [252, 252, 255, 255]
            m[52, 67] = [252, 252, 255, 255]
        return m

    # 7. FULL-VOLUME FOREARM, CUFF, SCULPTED HAND & CANONICAL BLUE CARD BACK (`arm_deal` & `arm_peek`)
    def build_dealing_arm_128(
        shift_dx: int = 0,
        shift_dy: int = 0,
        base_arm_rest: np.ndarray | None = None,
        is_bare_sequin: bool = False,
        is_opera_glove: bool = False,
    ) -> np.ndarray:
        arm_arr = (base_arm_rest if base_arm_rest is not None else arm_rest).copy()
        SK_OUT = (18, 16, 22, 255)
        if is_opera_glove:
            SK_DRK = (22, 20, 26, 255)
            SK_MID = (38, 34, 44, 255)
            SK_LIT = (58, 54, 66, 255)
            SK_HI = (88, 82, 98, 255)
        elif char_id == "tiffany":
            SK_DRK = (185, 122, 104, 255)
            SK_MID = (232, 162, 142, 255)
            SK_LIT = (250, 182, 162, 255)
            SK_HI = (255, 202, 182, 255)
        elif char_id == "selene":
            SK_DRK = (130, 96, 80, 255)
            SK_MID = (162, 123, 105, 255)
            SK_LIT = (218, 184, 153, 255)
            SK_HI = (236, 208, 182, 255)
        elif char_id == "malphas":
            SK_DRK = (159, 13, 0, 255)
            SK_MID = (189, 26, 7, 255)
            SK_LIT = (231, 41, 18, 255)
            SK_HI = (255, 112, 97, 255)
        elif char_id == "mortimer":
            SK_DRK = (175, 155, 128, 255)
            SK_MID = (216, 199, 168, 255)
            SK_LIT = (243, 232, 210, 255)
            SK_HI = (252, 246, 232, 255)
        elif char_id == "uriel":
            SK_DRK = (185, 114, 106, 255)
            SK_MID = (218, 146, 134, 255)
            SK_LIT = (248, 188, 170, 255)
            SK_HI = (255, 206, 188, 255)
        elif char_id == "vladimir":
            SK_DRK = (152, 156, 168, 255)
            SK_MID = (192, 196, 206, 255)
            SK_LIT = (224, 228, 236, 255)
            SK_HI = (242, 245, 250, 255)
        else:
            SK_DRK = (148, 96, 74, 255)
            SK_MID = (196, 140, 108, 255)
            SK_LIT = (226, 174, 140, 255)
            SK_HI = (238, 192, 160, 255)
        if char_id == "selene":
            # Dark gunmetal cyber-jacket sleeve with silver cyber-cuff
            CF_WHT = (72, 76, 84, 255)
            CF_LIT = (54, 58, 66, 255)
            CF_MID = (38, 40, 46, 255)
            CF_DRK = (24, 26, 30, 255)
        elif char_id == "uriel":
            CF_WHT = (255, 244, 232, 255)
            CF_LIT = (238, 218, 212, 255)
            CF_MID = (202, 169, 182, 255)
            CF_DRK = (166, 117, 136, 255)
        elif is_opera_glove:
            CF_WHT = (72, 66, 82, 255)
            CF_LIT = (52, 48, 60, 255)
            CF_MID = (36, 32, 42, 255)
            CF_DRK = (22, 20, 26, 255)
        elif is_bare_sequin:
            CF_WHT = (244, 176, 156, 255)
            CF_LIT = (234, 162, 142, 255)
            CF_MID = (218, 146, 126, 255)
            CF_DRK = (185, 122, 104, 255)
        else:
            CF_WHT = (238, 238, 242, 255)
            CF_LIT = (214, 214, 220, 255)
            CF_MID = (180, 182, 190, 255)
            CF_DRK = (140, 142, 152, 255)
        CD_SHD = (212, 214, 222, 255)
        CB_BLUE_DRK = (0, 88, 228, 255)
        CB_BLUE_MID = (12, 112, 252, 255)
        CB_BLUE_LIT = (135, 190, 255, 255)
        CB_WHT = (244, 246, 252, 255)

        dy_base = (-13 if char_id == "tiffany" else (-5 if char_id == "selene" else -8)) + shift_dy
        dx_base = shift_dx

        # A. Canonical Blue Card Back (`cards/back.png`)
        cy0, cy1 = 84 + dy_base, 116 + dy_base
        cx0, cx1 = 42 + dx_base, 66 + dx_base
        for y in range(cy0, cy1):
            for x in range(cx0, cx1):
                if not (0 <= y < h and 0 <= x < w):
                    continue
                if y in (cy0, cy1 - 1) or x in (cx0, cx1 - 1):
                    if x in (cx0, cx1 - 1) and y in (cy0, cy1 - 1):
                        continue
                    arm_arr[y, x] = SK_OUT
                elif y in (cy0 + 1, cy1 - 2) or x in (cx0 + 1, cx1 - 2):
                    arm_arr[y, x] = CD_SHD if (y == cy1 - 2 or x == cx0 + 1) else CB_WHT
                elif y in (cy0 + 2, cy1 - 3) or x in (cx0 + 2, cx1 - 3):
                    arm_arr[y, x] = CB_BLUE_DRK
                elif y in (cy0 + 3, cy1 - 4) or x in (cx0 + 3, cx1 - 4):
                    arm_arr[y, x] = CB_BLUE_LIT
                else:
                    dx_m = (x - (cx0 + 11.5)) / 3.4
                    dy_m = (y - (cy0 + 15.5)) / 5.0
                    dist_m = dx_m * dx_m + dy_m * dy_m
                    if 0.55 <= dist_m <= 1.15:
                        arm_arr[y, x] = CB_WHT
                    elif dist_m < 0.55:
                        arm_arr[y, x] = CB_BLUE_LIT if (abs(x - (cx0 + 11.5)) < 1.0 or abs(y - (cy0 + 15.5)) < 1.0) else CB_BLUE_DRK
                    elif (x in (cx0 + 4, cx0 + 5, cx1 - 6, cx1 - 5)) and (y in (cy0 + 4, cy0 + 5, cy1 - 6, cy1 - 5)):
                        arm_arr[y, x] = CB_WHT if ((x + y) % 2 == 0) else CB_BLUE_LIT
                    elif (x % 2 == 1) and (y % 2 == 1):
                        arm_arr[y, x] = CB_BLUE_LIT
                    else:
                        arm_arr[y, x] = CB_BLUE_MID

        # B. Sculpted Hand (for non-skeletal dealers)
        if char_id != "mortimer":
            hand_full_rows = {
                92: (62, 72, "top_outline"),
                93: (58, 74, "index_top"),
                94: (57, 76, "index_body"),
                95: (57, 77, "index_bot"),
                96: (56, 78, "mid_top"),
                97: (56, 79, "mid_body"),
                98: (57, 80, "mid_bot"),
                99: (57, 80, "ring_top"),
                100: (58, 80, "ring_body"),
                101: (59, 79, "ring_bot"),
                102: (59, 78, "pinky_top"),
                103: (60, 77, "pinky_body"),
                104: (62, 76, "palm_low"),
                105: (64, 75, "palm_base1"),
                106: (66, 74, "palm_base2"),
                107: (68, 73, "bottom_outline"),
            }
            for ry, (rx0, rx1, kind) in hand_full_rows.items():
                y = ry + dy_base
                x0, x1 = rx0 + dx_base, rx1 + dx_base
                if not (0 <= y < h):
                    continue
                for x in range(max(0, x0), min(w, x1 + 1)):
                    if kind in ("top_outline", "bottom_outline") or x == x0 or x == x1:
                        arm_arr[y, x] = SK_OUT
                    elif kind in ("index_bot", "mid_bot", "ring_bot") and x < x0 + 9:
                        arm_arr[y, x] = SK_DRK if x > x0 + 1 else SK_OUT
                    elif x > x1 - 4 or ry >= 103:
                        arm_arr[y, x] = SK_DRK
                    elif x > x1 - 8:
                        arm_arr[y, x] = SK_MID
                    elif ry in (93, 96, 99) and x < x0 + 8:
                        arm_arr[y, x] = SK_HI
                    else:
                        arm_arr[y, x] = SK_LIT
            for fy, fx in ((94, 58), (97, 57), (100, 59)):
                if 0 <= fy + dy_base < h and 0 <= fx + dx_base < w:
                    arm_arr[fy + dy_base, fx + dx_base] = SK_HI

        # C. Full-Volume 25px Forearm Sleeve & 17px Angled Cuff
        ax0, ay0 = 96.0 + dx_base, 130.0 + dy_base
        ax1, ay1 = 78.0 + dx_base, 108.0 + dy_base
        vx, vy = ax1 - ax0, ay1 - ay0
        seg_len = math.hypot(vx, vy)
        ux, uy = vx / seg_len, vy / seg_len
        nx, ny = -uy, ux

        for y in range(max(0, 96 + dy_base), min(h, 128)):
            for x in range(max(0, 62 + dx_base), min(w, 118)):
                px, py = x - ax0, y - ay0
                proj = px * ux + py * uy
                perp = px * nx + py * ny
                if -6.0 <= proj <= seg_len + 0.5:
                    t_along = max(0.0, min(1.0, proj / seg_len))
                    radius = (
                        (9.2 * (1.0 - t_along) + 6.8 * t_along)
                        if (is_bare_sequin or is_opera_glove)
                        else (12.5 * (1.0 - t_along) + 9.2 * t_along)
                    )
                    if abs(perp) <= radius:
                        if abs(abs(perp) - radius) <= 1.05:
                            arm_arr[y, x] = SK_OUT
                        else:
                            norm_p = perp / radius
                            crease1 = (not is_bare_sequin) and abs((proj - 6.0) + perp * 0.45) < 1.2 and norm_p > -0.4
                            crease2 = (not is_bare_sequin) and abs((proj - 13.0) - perp * 0.35) < 1.2 and norm_p < 0.5
                            if norm_p < -0.55 or crease1:
                                arm_arr[y, x] = CF_DRK
                            elif norm_p < -0.15 or crease2 or norm_p > 0.82:
                                arm_arr[y, x] = CF_MID
                            elif norm_p < 0.25:
                                arm_arr[y, x] = CF_LIT
                            else:
                                arm_arr[y, x] = CF_WHT

        for y in range(max(0, 92 + dy_base), min(h, 120 + dy_base)):
            for x in range(max(0, 60 + dx_base), min(w, 94 + dx_base)):
                px, py = x - ax0, y - ay0
                proj = px * ux + py * uy
                perp = px * nx + py * ny
                cuff_r = 6.8 if (is_bare_sequin or is_opera_glove) else 8.4
                cuff_end = (seg_len + 2.6) if (is_bare_sequin or is_opera_glove) else (seg_len + 5.5)
                if seg_len - 1.0 <= proj <= cuff_end and abs(perp) <= cuff_r:
                    if abs(abs(perp) - cuff_r) <= 1.05 or abs(proj - (seg_len - 1.0)) <= 0.95 or abs(proj - cuff_end) <= 0.95:
                        arm_arr[y, x] = SK_OUT
                    elif is_bare_sequin or is_opera_glove:
                        arm_arr[y, x] = (255, 232, 142, 255) if ((x + y) % 2 == 0) else (224, 172, 64, 255)
                    else:
                        norm_p = perp / cuff_r
                        if norm_p < -0.45:
                            arm_arr[y, x] = (140, 142, 152, 255)
                        elif norm_p < -0.05:
                            arm_arr[y, x] = (180, 182, 190, 255)
                        elif norm_p < 0.35:
                            arm_arr[y, x] = (214, 214, 220, 255)
                        else:
                            arm_arr[y, x] = (238, 238, 242, 255)
        if not (is_bare_sequin or is_opera_glove) and 0 <= 108 + dy_base < h and 0 <= 73 + dx_base < w:
            arm_arr[108 + dy_base, 72 + dx_base] = (
                (65, 219, 79, 255)
                if char_id == "selene"
                else (
                    (222, 162, 54, 255)
                    if char_id in ("mortimer", "uriel")
                    else ((210, 18, 36, 255) if char_id == "vladimir" else (70, 72, 82, 255))
                )
            )
            arm_arr[108 + dy_base, 73 + dx_base] = (
                (57, 127, 64, 255)
                if char_id == "selene"
                else (
                    (172, 118, 32, 255)
                    if char_id in ("mortimer", "uriel")
                    else ((148, 10, 22, 255) if char_id == "vladimir" else (45, 48, 55, 255))
                )
            )

        # D. True Articulated Skeletal Bony Hand for Mortimer (`char_id == "mortimer"`)
        if char_id == "mortimer":
            def set_bone_px(ry: int, rx: int, col: tuple[int, int, int, int]) -> None:
                yy, xx = ry + dy_base, rx + dx_base
                if 0 <= yy < h and 0 <= xx < w:
                    arm_arr[yy, xx] = col

            # 1) Back-of-hand dark skeletal web silhouette (converging diagonally from knuckles rx=64 into cuff rx=76)
            for rx in range(64, 77):
                t_w = (rx - 64) / 12.0
                ry_top_w = int(round(91.0 + 6.5 * t_w))
                ry_bot_w = int(round(103.5 + 3.0 * t_w))
                for ry in range(ry_top_w, ry_bot_w + 1):
                    set_bone_px(ry, rx, SK_OUT)

            # 2) 4 splayed horizontal phalangeal finger bones over the card back (rx = 52..65)
            skeletal_fingers = [
                # (ry_top, rx_tip, joints_tuple)
                (92, 54, (57, 61, 65)),  # Index phalanges + MCP knuckle
                (95, 52, (56, 60, 65)),  # Middle phalanges + MCP knuckle
                (98, 53, (57, 61, 65)),  # Ring phalanges + MCP knuckle
                (101, 56, (59, 63, 65)), # Pinky phalanges + MCP knuckle
            ]
            for rx in range(54, 66):
                set_bone_px(91, rx, SK_OUT)
            for idx_f, (ry_t, rx0, joints) in enumerate(skeletal_fingers):
                for dy_b in (0, 1):
                    ry = ry_t + dy_b
                    set_bone_px(ry, rx0 - 1, SK_OUT)
                    for rx in range(rx0, 66):
                        if rx in joints:
                            set_bone_px(ry, rx, SK_OUT if dy_b == 1 or rx == 65 else SK_DRK)
                        elif rx == 64 or rx == rx0:
                            set_bone_px(ry, rx, SK_HI if dy_b == 0 else SK_MID)
                        else:
                            set_bone_px(ry, rx, SK_HI if dy_b == 0 else SK_MID)
                # Inter-finger gap row (ry_t + 2): leave open gap between splayed fingertips (rx0..rx0+3) so card back shows through!
                ry_gap = ry_t + 2
                gap_start = rx0 if idx_f == 3 else rx0 + 4
                for rx in range(rx0, 66):
                    if rx < gap_start or idx_f == 3:
                        set_bone_px(ry_gap, rx, SK_OUT)

            # 3) 4 Diagonally Converging Metacarpal Bones (rx = 66..71) + Carpal Wrist Bones (rx = 72..75) entering the cuff
            metacarpal_paths = [
                (92.2, 97.5),  # 1st metacarpal (index -> scaphoid)
                (95.0, 99.5),  # 2nd metacarpal (middle -> lunate)
                (98.0, 101.5), # 3rd metacarpal (ring -> triquetrum)
                (101.0, 103.5),# 4th metacarpal (pinky -> pisiform)
            ]
            for m_idx, (y_start, y_end) in enumerate(metacarpal_paths):
                for rx in range(66, 75):
                    t_m = (rx - 66) / 8.0
                    ry_c = int(round(y_start * (1.0 - t_m) + y_end * t_m))
                    if rx == 71:
                        # Carpal-metacarpal wrist joint line
                        set_bone_px(ry_c, rx, SK_OUT)
                    else:
                        set_bone_px(ry_c, rx, SK_LIT if m_idx < 2 else SK_MID)
                        if rx <= 70 and m_idx in (0, 3):
                            set_bone_px(ry_c + 1, rx, SK_DRK)

        return arm_arr

    arm_deal = build_dealing_arm_128(shift_dx=0, shift_dy=0)
    arm_peek = build_dealing_arm_128(shift_dx=-4, shift_dy=2)

    # Helper to crop 112x112 at 1:1 native texel resolution and upscale 2x via NEAREST to 224x224!
    top_pad_1x = {
        "julian": 4,
        "professor": 4,
        "tiffany": 5,
        "selene": 4,
        "uriel": 2,
        "malphas": 4,
        "mortimer": 0,
        "vladimir": 4,
    }.get(char_id, 0)

    def save_1x_and_2x(layer_128: np.ndarray, name: str) -> None:
        cy0 = 2 if char_id in ("mortimer", "vladimir") else (1 if char_id in ("tiffany", "selene", "uriel") else 6)
        raw_112 = layer_128[cy0 : cy0 + 112, 8:120].copy()
        if top_pad_1x > 0:
            crop_112 = np.zeros_like(raw_112)
            crop_112[top_pad_1x:112, :] = raw_112[0 : 112 - top_pad_1x, :]
        else:
            crop_112 = raw_112
        img_1x = Image.fromarray(crop_112, "RGBA")
        img_2x = img_1x.resize((224, 224), Image.Resampling.NEAREST)
        img_1x.save(cdir / f"{name}.png")
        img_2x.save(cdir / f"{name}_2x.png")

    s2x = create_grounding_shadow(224, 224)
    s2x.save(cdir / "shadow_2x.png")
    s2x.resize((112, 112), Image.Resampling.NEAREST).save(cdir / "shadow.png")

    save_1x_and_2x(torso, "torso")
    save_1x_and_2x(neck, "neck")
    save_1x_and_2x(head, "head")
    save_1x_and_2x(eyes_open, "eyes_open")
    save_1x_and_2x(eyes_half, "eyes_half")
    save_1x_and_2x(eyes_closed, "eyes_closed")
    save_1x_and_2x(mouth_neutral, "mouth_neutral")
    for vname in ("mouth_talk", "mouth_a", "mouth_o", "mouth_e", "mouth_f", "mouth_smirk", "mouth_gasp"):
        save_1x_and_2x(build_viseme_128(vname), vname)
    save_1x_and_2x(arm_rest, "arm_rest")
    save_1x_and_2x(arm_deal, "arm_deal")
    save_1x_and_2x(arm_peek, "arm_peek")

    # Save neutral composite to bust.png, bust_2x.png, and orig_bust_2x.png
    bust_comp_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    for lname in ("shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
        limg = Image.open(cdir / f"{lname}_2x.png").convert("RGBA")
        bust_comp_2x.alpha_composite(limg)
    bust_comp_2x.save(cdir / "bust_2x.png")
    bust_comp_2x.save(cdir / "orig_bust_2x.png")
    bust_comp_2x.resize((112, 112), Image.Resampling.NEAREST).save(cdir / "bust.png")

    def save_variant_bust(v_key: str) -> None:
        v_bust_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        for base_lname in ("shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
            cand_v = cdir / f"{base_lname}_{v_key}_2x.png"
            l_path = cand_v if cand_v.exists() else (cdir / f"{base_lname}_2x.png")
            limg = Image.open(l_path).convert("RGBA")
            v_bust_2x.alpha_composite(limg)
        v_bust_2x.save(cdir / f"bust_{v_key}_2x.png")
        v_bust_2x.resize((112, 112), Image.Resampling.NEAREST).save(cdir / f"bust_{v_key}.png")

    # Build wardrobe costume variants across all 8 portrait dealers
    if char_id == "uriel":
        uriel_variants = {
            "alabaster": {
                "body_hi": (246, 242, 230),
                "body_mid": (234, 228, 212),
                "body_shd": (188, 180, 162),
                "keep_gold_lapel": True,
            },
            "sapphire": {
                "body_hi": (86, 138, 214),
                "body_mid": (66, 114, 192),
                "body_shd": (42, 78, 146),
                "keep_gold_lapel": True,
            },
            "obsidian": {
                "body_hi": (69, 64, 72),
                "body_mid": (57, 54, 59),
                "body_shd": (39, 36, 40),
                "keep_gold_lapel": False,
            },
        }
        for v_key, v_cfg in uriel_variants.items():
            v_torso = torso.copy()
            for y in range(60, h):
                for x in range(w):
                    r_t, g_t, b_t, a_t = [int(v) for v in v_torso[y, x]]
                    if a_t == 0:
                        continue
                    if b_t > r_t + 15:  # Seraphic sky-blue waistcoat body
                        if r_t >= 175:
                            c_rgb = v_cfg["body_hi"]
                        elif r_t >= 150:
                            c_rgb = v_cfg["body_mid"]
                        else:
                            c_rgb = v_cfg["body_shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    elif not v_cfg["keep_gold_lapel"] and b_t <= 102 and r_t > b_t + 30 and g_t > b_t + 12:
                        # Convert gold lapels & button back to obsidian charcoal
                        if r_t >= 235:
                            c_rgb = v_cfg["body_hi"]
                        elif r_t >= 210:
                            c_rgb = v_cfg["body_mid"]
                        else:
                            c_rgb = v_cfg["body_shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
            save_1x_and_2x(v_torso, f"torso_{v_key}")
            save_variant_bust(v_key)

    elif char_id == "julian":
        julian_variants = {
            "monte_carlo": {
                "lapel": (228, 194, 108),
                "mid": (236, 228, 210),
                "shd": (202, 192, 172),
                "bow_hi": (164, 28, 48),
                "bow_shd": (114, 16, 32),
                "btn": (232, 188, 72),
            },
            "high_roller": {
                "lapel": (176, 36, 58),
                "mid": (132, 20, 38),
                "shd": (88, 12, 24),
                "bow_hi": (58, 58, 66),
                "bow_shd": (34, 34, 40),
                "btn": (238, 196, 78),
            },
            "emerald": {
                "lapel": (54, 146, 94),
                "mid": (32, 104, 64),
                "shd": (18, 68, 42),
                "bow_hi": (42, 122, 78),
                "bow_shd": (22, 76, 48),
                "btn": (238, 196, 78),
            },
        }
        for v_key, v_cfg in julian_variants.items():
            v_torso = torso.copy()
            for y in range(60, h):
                for x in range(w):
                    r_t, g_t, b_t, a_t = [int(v) for v in v_torso[y, x]]
                    if a_t == 0:
                        continue
                    lum = r_t + g_t + b_t
                    if y <= 69 and 52 <= x <= 75 and r_t > g_t + 15:
                        continue  # neck skin
                    if 51 <= x <= 76 and r_t > 130 and g_t > 130 and b_t > 130:
                        continue  # white dress-shirt V
                    if 66 <= y <= 78 and 50 <= x <= 77 and lum >= 35 and r_t < 115:
                        c_rgb = v_cfg["bow_hi"] if lum >= 120 else v_cfg["bow_shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    elif y >= 94 and 61 <= x <= 66 and 40 <= lum <= 260:
                        c_rgb = v_cfg["btn"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    elif lum >= 45 and r_t <= 115 and g_t <= 115 and b_t <= 115:
                        if lum >= 180:
                            c_rgb = v_cfg["lapel"]
                        elif lum >= 115:
                            c_rgb = v_cfg["mid"]
                        else:
                            c_rgb = v_cfg["shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
            save_1x_and_2x(v_torso, f"torso_{v_key}")
            save_variant_bust(v_key)

    elif char_id == "tiffany":
        glamour_configs = {
            "sequin": {
                "file": "glamour_sequin_128.png",
                "is_opera_glove": False,
            },
            "rose": {
                "file": "glamour_corset_128.png",
                "is_opera_glove": True,
            },
            "champagne": {
                "file": "glamour_gold_128.png",
                "is_opera_glove": False,
            },
            "amethyst": {
                "file": "glamour_midnight_128.png",
                "is_opera_glove": False,
            },
        }
        for v_key, g_cfg in glamour_configs.items():
            g_path = cdir / g_cfg["file"]
            g_arr = np.array(Image.open(g_path).convert("RGBA"))

            # 1) Neck layer (`neck_<v>`): upper neck column behind chin (y=32..56) + lower neck/choker (y=52..67)
            v_neck = np.zeros_like(neck)
            for y in range(32, 56):
                for x in range(54, 74):
                    if x in (54, 73):
                        v_neck[y, x] = [18, 16, 20, 255]
                    elif x in (55, 72):
                        v_neck[y, x] = [204, 132, 114, 255]
                    else:
                        v_neck[y, x] = [238, 166, 146, 255]
            for y in range(52, 68):
                for x in range(51, 77):
                    if g_arr[y, x, 3] > 128:
                        v_neck[y, x] = g_arr[y, x]

            # 2) Torso (`torso_<v>`) and resting arms (`arm_rest_<v>`)
            v_torso = np.zeros_like(torso)
            v_arm_rest = np.zeros_like(arm_rest)
            for y in range(56, h):
                for x in range(w):
                    if g_arr[y, x, 3] <= 128:
                        continue
                    # Strip stray hair tips outside the neck column above the shoulders (y <= 66)
                    if y <= 66 and (x < 51 or x > 76):
                        continue
                    if y < 74:
                        v_torso[y, x] = g_arr[y, x]
                    else:
                        # Separate outer hanging arms (x <= 29 or x >= 98) into arm_rest
                        if x <= 29 or x >= 98:
                            v_arm_rest[y, x] = g_arr[y, x]
                            # Keep upper right deltoid cap (y=74..92, x=98..106) on torso so dealing arm connects cleanly
                            if 74 <= y <= 92 and 98 <= x <= 106:
                                v_torso[y, x] = g_arr[y, x]
                        else:
                            v_torso[y, x] = g_arr[y, x]
                            # Keep 1px overlap at x=30 and x=97 on arm_rest so IDLE composite is 100% seamless
                            if x in (30, 97):
                                v_arm_rest[y, x] = g_arr[y, x]

            # For `glamour_corset_128.png` (`rose`), copy the folded black-gloved forearms (y >= 104) onto arm_rest
            # and extend the crimson-and-black corset waist cleanly on `v_torso` underneath for card-dealing poses
            if g_cfg["is_opera_glove"]:
                for y in range(104, h):
                    for x in range(30, 98):
                        if v_torso[y, x, 3] > 0:
                            v_arm_rest[y, x] = v_torso[y, x]
                            src_y = 100 + ((y - 104) % 3)
                            v_torso[y, x] = g_arr[src_y, x]

            v_arm_deal = build_dealing_arm_128(
                shift_dx=0,
                shift_dy=0,
                base_arm_rest=v_arm_rest,
                is_bare_sequin=not g_cfg["is_opera_glove"],
                is_opera_glove=g_cfg["is_opera_glove"],
            )
            v_arm_peek = build_dealing_arm_128(
                shift_dx=-4,
                shift_dy=2,
                base_arm_rest=v_arm_rest,
                is_bare_sequin=not g_cfg["is_opera_glove"],
                is_opera_glove=g_cfg["is_opera_glove"],
            )

            save_1x_and_2x(v_neck, f"neck_{v_key}")
            save_1x_and_2x(v_torso, f"torso_{v_key}")
            save_1x_and_2x(v_arm_rest, f"arm_rest_{v_key}")
            save_1x_and_2x(v_arm_deal, f"arm_deal_{v_key}")
            save_1x_and_2x(v_arm_peek, f"arm_peek_{v_key}")
            save_variant_bust(v_key)

    elif char_id == "professor":
        prof_variants = {
            "ivy": {
                "hi": (168, 114, 74),
                "mid": (128, 82, 50),
                "shd": (88, 54, 32),
                "bow_hi": (186, 32, 48),
                "bow_shd": (134, 18, 32),
            },
            "oxford": {
                "hi": (72, 108, 168),
                "mid": (46, 74, 128),
                "shd": (28, 48, 88),
                "bow_hi": (228, 184, 68),
                "bow_shd": (36, 62, 114),
            },
            "vegas": {
                "hi": (112, 142, 104),
                "mid": (78, 104, 72),
                "shd": (50, 68, 46),
                "bow_hi": (164, 28, 52),
                "bow_shd": (112, 16, 34),
            },
        }
        for v_key, v_cfg in prof_variants.items():
            v_torso = torso.copy()
            for y in range(60, h):
                for x in range(w):
                    r_t, g_t, b_t, a_t = [int(v) for v in v_torso[y, x]]
                    if a_t == 0:
                        continue
                    lum = r_t + g_t + b_t
                    if y <= 69 and 52 <= x <= 75 and r_t > g_t + 15 and g_t > 70:
                        continue  # neck skin
                    if 50 <= x <= 77 and r_t > 130 and g_t > 130 and b_t > 130:
                        continue  # white dress-shirt V
                    if 65 <= y <= 76 and 50 <= x <= 77 and lum >= 35:
                        c_rgb = v_cfg["bow_hi"] if lum >= 120 else v_cfg["bow_shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    elif lum >= 45 and r_t <= 125 and g_t <= 125 and b_t <= 125:
                        if lum >= 195:
                            c_rgb = v_cfg["hi"]
                        elif lum >= 115:
                            c_rgb = v_cfg["mid"]
                        else:
                            c_rgb = v_cfg["shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
            save_1x_and_2x(v_torso, f"torso_{v_key}")
            save_variant_bust(v_key)

    elif char_id == "selene":
        # 1) Suit/pauldron variants (netrunner, arasaka, ghost)
        selene_suits = {
            "netrunner": {
                "pauldron_hi": (244, 72, 178),
                "pauldron_mid": (196, 38, 138),
                "suit_mid": (88, 42, 128),
                "suit_shd": (52, 22, 82),
            },
            "arasaka": {
                "pauldron_hi": (242, 202, 88),
                "pauldron_mid": (196, 152, 52),
                "suit_mid": (168, 24, 38),
                "suit_shd": (104, 12, 22),
            },
            "ghost": {
                "pauldron_hi": (148, 218, 252),
                "pauldron_mid": (102, 174, 222),
                "suit_mid": (226, 232, 242),
                "suit_shd": (178, 188, 204),
            },
        }
        for v_key, v_cfg in selene_suits.items():
            def _recolor_selene_suit(arr_in: np.ndarray, is_deal_arm: bool = False) -> np.ndarray:
                out = arr_in.copy()
                for y in range(72, h):
                    for x in range(w):
                        r_s, g_s, b_s, a_s = [int(v) for v in out[y, x]]
                        if a_s == 0:
                            continue
                        if is_deal_arm and 76 <= y <= 114 and 36 <= x <= 82:
                            continue  # keep hand & card intact
                        if 52 <= x <= 75 and r_s > b_s + 20 and g_s > 75:
                            continue  # keep tan neck/chest skin intact
                        lum = r_s + g_s + b_s
                        if lum >= 420:  # white/silver shoulder pauldrons & stand-up collar
                            c_rgb = v_cfg["pauldron_hi"] if lum >= 580 else v_cfg["pauldron_mid"]
                            out[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                        elif 45 <= lum < 420:  # dark synth-leather jacket
                            c_rgb = v_cfg["suit_mid"] if lum >= 135 else v_cfg["suit_shd"]
                            out[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                return out

            save_1x_and_2x(_recolor_selene_suit(torso), f"torso_{v_key}")
            save_1x_and_2x(_recolor_selene_suit(arm_rest), f"arm_rest_{v_key}")
            save_1x_and_2x(_recolor_selene_suit(arm_deal, is_deal_arm=True), f"arm_deal_{v_key}")
            save_1x_and_2x(_recolor_selene_suit(arm_peek, is_deal_arm=True), f"arm_peek_{v_key}")
            save_variant_bust(v_key)

        # 2) All-Chrome Liquid Chrome Version (`selene_chrome`)
        def _to_liquid_chrome(arr_in: np.ndarray, is_eyes: bool = False, is_deal_arm: bool = False) -> np.ndarray:
            out = arr_in.copy()
            for y in range(h):
                for x in range(w):
                    r_c, g_c, b_c, a_c = [int(v) for v in out[y, x]]
                    if a_c == 0:
                        continue
                    # Preserve canonical blue playing card back on dealing/peeking arms
                    if is_deal_arm and b_c > r_c + 65 and b_c > 140:
                        continue
                    lum = int(round(0.299 * r_c + 0.587 * g_c + 0.114 * b_c))
                    if is_eyes:
                        # Convert crimson visor & green iris into glowing ice-cyan & liquid-mercury cyber-optics
                        if r_c > g_c + 30 or g_c > r_c + 20:
                            if lum >= 150:
                                out[y, x] = [184, 246, 255, 255]
                            elif lum >= 100:
                                out[y, x] = [96, 212, 248, 255]
                            else:
                                out[y, x] = [44, 148, 204, 255]
                            continue
                    # Convert neon-green hair streaks into glowing ice-cyan fiber-optic highlights
                    if g_c > r_c + 18 and g_c >= b_c:
                        out[y, x] = [124, 236, 255, 255]
                        continue
                    if lum < 22:
                        out[y, x] = [18, 24, 34, 255]
                    elif lum < 65:
                        out[y, x] = [84, 98, 120, 255]
                    elif lum < 115:
                        out[y, x] = [138, 154, 178, 255]
                    elif lum < 160:
                        out[y, x] = [184, 200, 222, 255]
                    elif lum < 205:
                        out[y, x] = [220, 232, 246, 255]
                    else:
                        out[y, x] = [246, 252, 255, 255]
            return out

        save_1x_and_2x(_to_liquid_chrome(torso), "torso_chrome")
        save_1x_and_2x(_to_liquid_chrome(neck), "neck_chrome")
        save_1x_and_2x(_to_liquid_chrome(head), "head_chrome")
        save_1x_and_2x(_to_liquid_chrome(eyes_open, is_eyes=True), "eyes_open_chrome")
        save_1x_and_2x(_to_liquid_chrome(eyes_half, is_eyes=True), "eyes_half_chrome")
        save_1x_and_2x(_to_liquid_chrome(eyes_closed, is_eyes=True), "eyes_closed_chrome")
        save_1x_and_2x(_to_liquid_chrome(mouth_neutral), "mouth_neutral_chrome")
        for vname in ("mouth_talk", "mouth_a", "mouth_o", "mouth_e", "mouth_f", "mouth_smirk", "mouth_gasp"):
            save_1x_and_2x(_to_liquid_chrome(build_viseme_128(vname)), f"{vname}_chrome")
        save_1x_and_2x(_to_liquid_chrome(arm_rest), "arm_rest_chrome")
        save_1x_and_2x(_to_liquid_chrome(arm_deal, is_deal_arm=True), "arm_deal_chrome")
        save_1x_and_2x(_to_liquid_chrome(arm_peek, is_deal_arm=True), "arm_peek_chrome")
        save_variant_bust("chrome")

    elif char_id == "malphas":
        malphas_variants = {
            "hellfire": {
                "lapel": (236, 118, 32),
                "vest_mid": (168, 64, 16),
                "vest_shd": (104, 34, 10),
                "shirt_hi": (76, 70, 74),
                "shirt_shd": (52, 46, 50),
            },
            "brimstone": {
                "lapel": (242, 198, 64),
                "vest_mid": (52, 46, 56),
                "vest_shd": (30, 26, 34),
                "shirt_hi": (164, 28, 42),
                "shirt_shd": (118, 16, 28),
            },
            "abyssal": {
                "lapel": (148, 78, 214),
                "vest_mid": (78, 38, 128),
                "vest_shd": (44, 20, 78),
                "shirt_hi": (88, 94, 122),
                "shirt_shd": (60, 64, 88),
            },
        }
        for v_key, v_cfg in malphas_variants.items():
            def _recolor_malphas(arr_in: np.ndarray, is_deal_arm: bool = False) -> np.ndarray:
                out = arr_in.copy()
                for y in range(52, h):
                    for x in range(w):
                        r_m, g_m, b_m, a_m = [int(v) for v in out[y, x]]
                        if a_m == 0:
                            continue
                        if is_deal_arm and 74 <= y <= 112 and 36 <= x <= 70:
                            continue  # keep card back intact
                        if r_m > g_m + 60:
                            continue  # keep crimson demon skin intact
                        lum = r_m + g_m + b_m
                        if r_m >= 150 and g_m >= 150 and b_m >= 150:
                            c_rgb = v_cfg["shirt_hi"] if lum >= 680 else v_cfg["shirt_shd"]
                            out[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                        elif 45 <= lum < 450 and abs(r_m - g_m) <= 12 and abs(g_m - b_m) <= 12:
                            if lum >= 210:
                                c_rgb = v_cfg["lapel"]
                            elif lum >= 135:
                                c_rgb = v_cfg["vest_mid"]
                            else:
                                c_rgb = v_cfg["vest_shd"]
                            out[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                return out

            save_1x_and_2x(_recolor_malphas(torso), f"torso_{v_key}")
            save_1x_and_2x(_recolor_malphas(arm_rest), f"arm_rest_{v_key}")
            save_1x_and_2x(_recolor_malphas(arm_deal, is_deal_arm=True), f"arm_deal_{v_key}")
            save_1x_and_2x(_recolor_malphas(arm_peek, is_deal_arm=True), f"arm_peek_{v_key}")
            save_variant_bust(v_key)

    elif char_id == "mortimer":
        mortimer_variants = {
            "baron": {
                "coat_hi": (152, 32, 54),
                "coat_mid": (114, 22, 38),
                "coat_shd": (74, 14, 24),
                "cravat": (196, 28, 48),
                "hat_band": (184, 24, 44),
            },
            "lich": {
                "coat_hi": (38, 118, 108),
                "coat_mid": (24, 84, 78),
                "coat_shd": (14, 52, 48),
                "cravat": (64, 208, 132),
                "hat_band": (58, 194, 122),
            },
            "gilded": {
                "coat_hi": (232, 206, 134),
                "coat_mid": (196, 168, 96),
                "coat_shd": (148, 122, 64),
                "cravat": (148, 28, 48),
                "hat_band": (228, 182, 62),
            },
        }
        for v_key, v_cfg in mortimer_variants.items():
            # 1) Recolor silk top-hat crown & band (y = 8..31 on 128x128 grid)
            v_head = head.copy()
            for y in range(8, 32):
                for x in range(38, 90):
                    r_h, g_h, b_h, a_h = [int(v) for v in v_head[y, x]]
                    if a_h > 0 and b_h > g_h + 10 and r_h > g_h + 6 and r_h < 155:
                        c_rgb = v_cfg["coat_mid"] if r_h >= 55 else v_cfg["coat_shd"]
                        v_head[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]

            # 2) Recolor waistcoat & bowtie on torso while keeping white dress shirt & sleeves clean
            v_torso = torso.copy()
            for y in range(58, h):
                for x in range(w):
                    r_m, g_m, b_m, a_m = [int(v) for v in v_torso[y, x]]
                    if a_m == 0:
                        continue
                    lum = r_m + g_m + b_m
                    # Skip bone neck (y <= 67, 52 <= x <= 75, warm beige R > B + 12) and white dress shirt placket
                    if (y <= 68 and 50 <= x <= 77 and r_m > b_m + 12) or (51 <= x <= 76 and lum >= 240):
                        continue
                    # Preserve gold lapel badge & buttons (R > B + 50 and G > 100)
                    if r_m > b_m + 50 and g_m > 100:
                        continue
                    # Central bowtie (55 <= x <= 72, 67 <= y <= 76)
                    if 55 <= x <= 72 and 67 <= y <= 76 and 25 <= lum < 220:
                        c_rgb = v_cfg["cravat"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    elif 45 <= lum < 340:  # waistcoat fabric & lapels
                        if lum >= 210:
                            c_rgb = v_cfg["coat_hi"]
                        elif lum >= 135:
                            c_rgb = v_cfg["coat_mid"]
                        else:
                            c_rgb = v_cfg["coat_shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]

            save_1x_and_2x(v_head, f"head_{v_key}")
            save_1x_and_2x(v_torso, f"torso_{v_key}")
            save_variant_bust(v_key)

    elif char_id == "vladimir":
        vladimir_variants = {
            "nosferatu": {
                "hi": (82, 76, 92),
                "mid": (52, 48, 60),
                "shd": (30, 28, 36),
                "cravat": (136, 42, 114),
                "btn": (214, 220, 232),
            },
            "royal": {
                "hi": (156, 68, 196),
                "mid": (104, 38, 138),
                "shd": (62, 20, 86),
                "cravat": (196, 28, 54),
                "btn": (242, 202, 82),
            },
            "frost": {
                "hi": (78, 136, 214),
                "mid": (46, 90, 162),
                "shd": (26, 56, 104),
                "cravat": (138, 204, 238),
                "btn": (224, 236, 248),
            },
        }
        for v_key, v_cfg in vladimir_variants.items():
            v_torso = torso.copy()
            for y in range(54, h):
                for x in range(w):
                    r_v, g_v, b_v, a_v = [int(v) for v in v_torso[y, x]]
                    if a_v == 0:
                        continue
                    lum = r_v + g_v + b_v
                    # Preserve pale vampire neck and white shirt collar
                    if y <= 76 and ((b_v >= r_v and lum >= 360) or lum >= 540):
                        continue
                    # Double-breasted waistcoat buttons (gold/warm yellow pixels where R > 160, G > 110, B < 120)
                    if y >= 72 and r_v > 150 and g_v > 105 and b_v < 125:
                        c_rgb = v_cfg["btn"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    # Central cravat (57 <= x <= 70, 62 <= y <= 84)
                    elif 57 <= x <= 70 and 62 <= y <= 84 and r_v > g_v + 25:
                        c_rgb = v_cfg["cravat"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
                    # Crimson waistcoat body & lapels
                    elif r_v > g_v + 20 or (y >= 64 and 45 <= lum <= 320):
                        if r_v >= 120 or lum >= 200:
                            c_rgb = v_cfg["hi"]
                        elif r_v >= 65 or lum >= 110:
                            c_rgb = v_cfg["mid"]
                        else:
                            c_rgb = v_cfg["shd"]
                        v_torso[y, x] = [c_rgb[0], c_rgb[1], c_rgb[2], 255]
            save_1x_and_2x(v_torso, f"torso_{v_key}")
            save_variant_bust(v_key)

    from dealer_imaginative_costumes import build_imaginative_costumes_for_dealer
    build_imaginative_costumes_for_dealer(char_id, cdir)


def deocclude_and_build_character(char_id: str, cfg: dict | None = None) -> None:
    """
    De-occludes the head faceplate and lower torso of `char_id` and writes all 19
    discrete 2x (224x224) and 1x (112x112) puppet layer PNGs.
    """
    if char_id in ("julian", "professor", "tiffany", "selene", "malphas", "mortimer", "uriel", "vladimir") and (CHARACTERS_DIR / char_id / "chunky_master_128.png").exists():
        build_chunky_paper_doll_character(char_id)
        return
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

    # Apply Crunchy 2.5D Pixel-Art pass (ordered 2x2 Bayer dither + stepped palette + 1px dark silhouette ink)
    master_2x = apply_crunchy_25d_pixel_pass(
        master_2x,
        levels=16,
        dither_strength=7.5,
        add_silhouette_ink=True,
    )
    arr_bust = np.array(master_2x).copy()

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

    # 4A. De-occlude left and right eye sockets on head_2x using clean lower-lid skin interpolation
    for bx1, by1, bx2, by2 in (el_box, er_box):
        if char_id == "mortimer":
            # Hollow dark bone socket without purple soul flame
            for y in range(max(0, by1), min(224, by2 + 1)):
                for x in range(max(0, bx1), min(224, bx2 + 1)):
                    if head_arr[y, x, 3] > 0:
                        head_arr[y, x, :3] = [18, 14, 22]
        else:
            # Sample clean skin row immediately below lower lash (cheek/lower lid) to avoid eyebrow/glow bleed
            y_top = max(0, by1 - 1)
            y_bot = min(223, by2 + 2)
            span_h = max(1, y_bot - y_top)
            for x in range(max(0, bx1 - 1), min(224, bx2 + 2)):
                c_bot = arr_bust[y_bot, x, :3].astype(np.float32)
                if arr_bust[y_bot, x, 3] < 128:
                    c_bot = np.array(skin, dtype=np.float32)
                for y in range(max(0, by1 - 1), min(224, by2 + 2)):
                    if head_arr[y, x, 3] > 0:
                        t = (y - y_top) / span_h
                        # Subtle upper-lid contour shading (0.90 at upper crease -> 1.00 at lower lid)
                        shade = 0.90 + 0.10 * t
                        head_arr[y, x, :3] = np.clip(np.round(c_bot * shade), 0, 255).astype(np.uint8)

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
    if char_id == "professor":
        # Add crisp pixel-art spectacle lens specular glint on open eyes
        d_eo = ImageDraw.Draw(eyes_open_2x)
        d_eo.line([(el_box[0] + 1, el_box[1]), (el_box[0] + 3, el_box[1])], fill=(225, 250, 255, 210), width=1)
        d_eo.line([(er_box[0] + 1, er_box[1]), (er_box[0] + 3, er_box[1])], fill=(225, 250, 255, 210), width=1)
    eyes_open_2x.save(cdir / "eyes_open_2x.png")
    eyes_open_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_open.png")

    # B) eyes_half: keep only lower half of open eyes + draw curved upper lash arch at mid_y!
    eyes_half_arr = np.array(eyes_open_2x).copy()
    for bx1, by1, bx2, by2 in (el_box, er_box):
        mid_y = (by1 + by2) // 2
        eyes_half_arr[max(0, by1 - 3):mid_y, max(0, bx1 - 3):min(224, bx2 + 4)] = [0, 0, 0, 0]
    eyes_half_2x = Image.fromarray(eyes_half_arr, "RGBA")
    draw_half = ImageDraw.Draw(eyes_half_2x)
    for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in ((el_box, el_line), (er_box, er_line)):
        mid_y = (by1 + by2) // 2
        cx_eye = (lx1 + lx2) // 2
        lash_col = (0, 210, 240, 255) if char_id == "selene" else (160, 80, 230, 220) if char_id == "mortimer" else (*ink, 255)
        draw_half.line([(lx1, mid_y + 1), (cx_eye, mid_y), (lx2, mid_y + 1)], fill=lash_col, width=1)
    eyes_half_2x.save(cdir / "eyes_half_2x.png")
    eyes_half_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_half.png")

    # C) eyes_closed: clean curved closed lash lines directly over the smooth de-occluded eyelids on head_2x!
    eyes_closed_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_closed = ImageDraw.Draw(eyes_closed_2x)
    for (bx1, by1, bx2, by2), (lx1, ly1, lx2, ly2) in ((el_box, el_line), (er_box, er_line)):
        if char_id == "mortimer":
            draw_closed.line([(lx1, ly1), (lx2, ly2)], fill=(35, 25, 42, 220), width=1)
        elif char_id == "selene":
            draw_closed.line([(lx1, ly1), ((lx1 + lx2) // 2, ly1 + 1), (lx2, ly2)], fill=(10, 85, 110, 255), width=2)
        else:
            draw_closed.line([(lx1, ly1), ((lx1 + lx2) // 2, ly1 + 1), (lx2, ly2)], fill=(*ink, 255), width=2)
    eyes_closed_2x = put_unpremultiplied_alpha(eyes_closed_2x, radius=0.3)
    eyes_closed_2x.save(cdir / "eyes_closed_2x.png")
    eyes_closed_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "eyes_closed.png")

    # 6. Mouth Visemes (neutral, talk, a, o, e, f, smirk, gasp) — Crunchy 2.5D Pixel-Art Lip Contours
    mouth_mask = Image.new("L", (224, 224), 0)
    ImageDraw.Draw(mouth_mask).rectangle([mx_start - 3, my - my_half - 1, mx_end + 3, my + my_half + 1], fill=255)
    mouth_mask = mouth_mask.filter(ImageFilter.GaussianBlur(radius=0.8))
    ImageDraw.Draw(mouth_mask).rectangle([mx_start - 2, my - my_half, mx_end + 2, my + my_half], fill=255)
    mouth_neutral_2x = apply_unpremultiplied_mask(master_2x, mouth_mask)
    mouth_neutral_2x.save(cdir / "mouth_neutral_2x.png")
    mouth_neutral_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_neutral.png")

    cavity_color = (34, 12, 16, 255) if char_id != "malphas" else (55, 10, 15, 255)
    lip_rgba = (*lip_col, 255)
    lip_hi = (
        min(255, lip_col[0] + 28),
        min(255, lip_col[1] + 22),
        min(255, lip_col[2] + 22),
        255,
    )
    tongue_rgba = (175, 72, 82, 240) if char_id != "mortimer" else (145, 65, 210, 220)
    teeth_rgba = (242, 238, 232, 245)

    def _draw_pixel_mouth(draw_obj: ImageDraw.ImageDraw, rx: int, ry: int, style: str):
        bx_outer = [mc_x - rx - 1, my - ry - 1, mc_x + rx + 1, my + ry + 1]
        bx_inner = [mc_x - rx, my - ry, mc_x + rx, my + ry]
        if char_id == "mortimer":
            # Skeletal jaw articulation with glowing purple soul-fire between teeth
            draw_obj.rectangle([mc_x - rx, my - ry, mc_x + rx, my + ry], fill=(24, 14, 32, 255), outline=(*ink, 255))
            for tx in range(mc_x - rx + 2, mc_x + rx, 3):
                draw_obj.point((tx, my - ry + 1), fill=teeth_rgba)
                draw_obj.point((tx, my + ry - 1), fill=teeth_rgba)
            if ry >= 2:
                draw_obj.line([(mc_x - rx + 2, my), (mc_x + rx - 2, my)], fill=tongue_rgba, width=1)
            return

        if style in ("open_teeth", "talk"):
            # Upper/lower lip rim + inner cavity + teeth row + tongue pixel highlight
            draw_obj.ellipse(bx_outer, fill=lip_rgba, outline=(*ink, 255), width=1)
            draw_obj.ellipse(bx_inner, fill=cavity_color)
            if ry >= 2:
                draw_obj.line([(mc_x - rx + 2, my - ry + 1), (mc_x + rx - 2, my - ry + 1)], fill=teeth_rgba, width=1)
                draw_obj.line([(mc_x - rx // 2, my + ry - 1), (mc_x + rx // 2, my + ry - 1)], fill=tongue_rgba, width=1)
            draw_obj.line([(mc_x - rx // 2, my + ry + 1), (mc_x + rx // 2, my + ry + 1)], fill=lip_hi, width=1)
            if char_id == "vladimir" and ry >= 2:
                draw_obj.point((mc_x - rx + 2, my), fill=(255, 255, 255, 255))
                draw_obj.point((mc_x + rx - 2, my), fill=(255, 255, 255, 255))
        elif style in ("ellipse", "gasp"):
            draw_obj.ellipse(bx_outer, fill=lip_rgba, outline=(*ink, 255), width=1)
            draw_obj.ellipse(bx_inner, fill=cavity_color)
            draw_obj.point((mc_x, my - ry + 1), fill=teeth_rgba)
            draw_obj.line([(mc_x - 2, my + ry + 1), (mc_x + 2, my + ry + 1)], fill=lip_hi, width=1)
        elif style == "wide_teeth":
            draw_obj.rounded_rectangle(bx_outer, radius=2, fill=lip_rgba, outline=(*ink, 255), width=1)
            draw_obj.rectangle([mc_x - rx + 1, my - ry + 1, mc_x + rx - 1, my + ry - 1], fill=teeth_rgba)
            draw_obj.line([(mc_x - rx + 1, my), (mc_x + rx - 1, my)], fill=cavity_color, width=1)
        else:  # tuck ('f')
            draw_obj.line([(mc_x - rx, my - 1), (mc_x + rx, my - 1)], fill=lip_rgba, width=1)
            draw_obj.line([(mc_x - rx, my), (mc_x + rx, my)], fill=(*ink, 255), width=1)
            draw_obj.line([(mc_x - rx + 2, my), (mc_x + rx - 2, my)], fill=teeth_rgba, width=1)
            draw_obj.line([(mc_x - rx + 1, my + 1), (mc_x + rx - 1, my + 1)], fill=lip_hi, width=1)

    # B) mouth_talk
    mouth_talk_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    _draw_pixel_mouth(ImageDraw.Draw(mouth_talk_2x), rx=5, ry=2, style="talk")
    mouth_talk_2x.save(cdir / "mouth_talk_2x.png")
    mouth_talk_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_talk.png")

    # C) mouth_smirk
    mouth_smirk_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    draw_smirk = ImageDraw.Draw(mouth_smirk_2x)
    draw_smirk.line([(mx_start, my + 1), (mc_x + 2, my), (mx_end, my - 2)], fill=lip_rgba, width=2)
    draw_smirk.line([(mx_start, my), (mc_x + 2, my), (mx_end, my - 2)], fill=(*ink, 255), width=1)
    draw_smirk.point((mx_end, my - 3), fill=(*ink, 255))
    mouth_smirk_2x.save(cdir / "mouth_smirk_2x.png")
    mouth_smirk_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_smirk.png")

    # D) mouth_gasp
    mouth_gasp_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    _draw_pixel_mouth(ImageDraw.Draw(mouth_gasp_2x), rx=4, ry=3, style="gasp")
    mouth_gasp_2x.save(cdir / "mouth_gasp_2x.png")
    mouth_gasp_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "mouth_gasp.png")

    # E) Phonetic visemes: mouth_a, mouth_o, mouth_e, mouth_f positioned at (mc_x, my)
    viseme_specs = {
        "mouth_a": (5, 3, "open_teeth"),
        "mouth_o": (3, 3, "ellipse"),
        "mouth_e": (6, 2, "wide_teeth"),
        "mouth_f": (5, 1, "tuck"),
    }
    for vname, (rx, ry, style) in viseme_specs.items():
        vimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        _draw_pixel_mouth(ImageDraw.Draw(vimg), rx=rx, ry=ry, style=style)
        vimg.save(cdir / f"{vname}_2x.png")
        vimg.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / f"{vname}.png")

    # 7. Arms (arm_rest, arm_deal, arm_peek) — 2.5D Pixel-Art Card Articulation
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

    # B) arm_deal: articulated forward-swept dealing hand + compact 2.5D pixel-art card
    arm_deal_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    left_crop = arm_rest_2x.crop((0, 0, 112, 224))
    right_crop = arm_rest_2x.crop((112, 0, 224, 224))
    arm_deal_2x.paste(left_crop, (0, 0))
    arm_deal_2x.paste(right_crop, (110, 2))
    draw_deal = ImageDraw.Draw(arm_deal_2x)
    card_poly = [(116, 178), (136, 173), (141, 197), (121, 202)]
    shadow_poly = [(x + 2, y + 3) for x, y in card_poly]
    draw_deal.polygon(shadow_poly, fill=(8, 10, 14, 150))
    draw_deal.polygon(card_poly, fill=(248, 246, 240, 255), outline=(18, 16, 20, 255))
    pip_color = (205, 30, 40, 255) if char_id in ("julian", "malphas", "vladimir") else (0, 190, 230, 255) if char_id == "selene" else (20, 130, 80, 255) if char_id == "professor" else (25, 20, 25, 255)
    # Corner index pip + center diamond pip
    draw_deal.rectangle([119, 180, 121, 182], fill=pip_color)
    draw_deal.polygon([(129, 183), (132, 187), (129, 191), (126, 187)], fill=pip_color)
    # Crisp gripping thumb/index pixel knuckles
    for fx, fy in ((121, 176), (128, 175)):
        draw_deal.rectangle([fx - 2, fy - 2, fx + 2, fy + 1], fill=(*skin, 255), outline=(*ink, 255))
    arm_deal_2x.save(cdir / "arm_deal_2x.png")
    arm_deal_2x.resize((112, 112), Image.Resampling.LANCZOS).save(cdir / "arm_deal.png")

    # C) arm_peek: inward hole-card peek gesture with compact 2.5D pixel card & lifted corner
    arm_peek_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    arm_peek_2x.paste(left_crop, (2, -1))
    arm_peek_2x.paste(right_crop, (112, 0))
    draw_peek = ImageDraw.Draw(arm_peek_2x)
    px1, py1, px2, py2 = 90, 176, 110, 200
    card_back_rgb = cfg["card_back"]
    draw_peek.rectangle([px1 + 2, py1 + 3, px2 + 2, py2 + 3], fill=(8, 10, 14, 150))
    draw_peek.rectangle([px1, py1, px2, py2], fill=(248, 246, 240, 255), outline=(18, 16, 20, 255), width=1)
    draw_peek.rectangle([px1 + 2, py1 + 2, px2 - 2, py2 - 2], fill=(*card_back_rgb, 255), outline=(235, 230, 220, 255), width=1)
    # Lifted white corner peek triangle
    draw_peek.polygon([(px2 - 6, py2), (px2, py2 - 6), (px2, py2)], fill=(248, 246, 240, 255), outline=(*ink, 255))
    for fx in (95, 102):
        draw_peek.rectangle([fx - 2, py1 - 2, fx + 2, py1 + 1], fill=(*skin, 255), outline=(*ink, 255))
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
