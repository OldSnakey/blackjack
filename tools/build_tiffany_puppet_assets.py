"""
Procedural Asset Pipeline: Builds discrete multi-layer puppet rig assets for Tiffany
from Nano Banana (Gemini Image API) generated elements and authentic character sources.

Solves:
1. Zero Transparency Holes / Fringes:
   - Green chroma-keying with spill suppression replaces lossy white background thresholding.
   - De-occluded torso vest & shirt preserves opaque fabric linework without semi-transparent artifacts.
2. True Casino Dealer Articulation:
   - arm_rest: Non-dominant left hand holding shoe deck, dominant right arm resting on table felt.
   - arm_deal: Non-dominant left hand holding shoe deck, dominant right arm sweeping playing card forward.
   - arm_peek: Non-dominant left hand holding shoe deck, dominant right hand lifting Ace of Hearts hole card.

Produces:
- 19 discrete 2x ($224x224 px$) and 19 discrete 1x ($112x112 px$) RGBA PNG layers:
  1. shadow, shadow_2x (Grounding contact base with soft ambient blur)
  2. torso, torso_2x (De-occluded waistcoat and dress shirt)
  3. neck, neck_2x (Discrete neck articulation pillar)
  4. head, head_2x (Blank face-plate with hair bun, ears, earrings, and nose)
  5. eyes_open, eyes_half, eyes_closed (plus _2x) (Discrete eye state overlays)
  6. mouth_neutral, mouth_a, mouth_o, mouth_e, mouth_f, mouth_talk, mouth_smirk, mouth_gasp (plus _2x)
     (Phonetic typewriter speech visemes with rose lips)
  7. arm_rest, arm_deal, arm_peek (plus _2x) (Discrete articulated arms)
  8. bust, bust_2x (Pre-composited portrait for wardrobe card previews)
"""

from __future__ import annotations

import io
import os
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
BRAIN_DIR = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\961dac34-d1bc-4f26-a9b9-15da0b316e33")
OUTPUT_DIR = BASE_DIR / "assets" / "haunted" / "characters" / "tiffany"

ORIG_BUST_SRC = BASE_DIR / "scratch_orig_tiffany_bust.png"
DEAL_POSE_SRC = BRAIN_DIR / "tiffany_deal_pose_1792591514708.jpg"
PEEK_POSE_SRC = BRAIN_DIR / "tiffany_peek_pose_1792591541741.jpg"
HEAD_SRC = BRAIN_DIR / "tiffany_head_blank_1792586489452.jpg"
FACE_SRC = BRAIN_DIR / "tiffany_face_features_sheet_1792586535228.jpg"


def get_original_bust() -> Image.Image:
    """Loads authentic Tiffany bust image, falling back to git history if needed."""
    if ORIG_BUST_SRC.exists():
        return Image.open(ORIG_BUST_SRC).convert("RGBA")
    try:
        data = subprocess.check_output(
            ["git", "show", "53310d6:assets/haunted/characters/tiffany/bust_2x.png"],
            cwd=str(BASE_DIR)
        )
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        img.save(ORIG_BUST_SRC)
        return img
    except Exception:
        target = OUTPUT_DIR / "bust_2x.png"
        return Image.open(target).convert("RGBA")


def chroma_key_green(img: Image.Image, low: float = 15.0, high: float = 45.0) -> Image.Image:
    """
    High-fidelity green chroma keyer with despill suppression.
    Guarantees white dress shirts, collars, and cuffs are 100% opaque without fringing.
    """
    rgba = img.convert("RGBA")
    arr = np.array(rgba, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    max_rb = np.maximum(r, b)
    green_diff = g - max_rb
    alpha = np.clip(255.0 * (1.0 - (green_diff - low) / (high - low)), 0.0, 255.0)
    despilled_g = np.where(g > max_rb, max_rb, g)
    out = np.zeros_like(arr, dtype=np.uint8)
    out[:, :, 0] = r.astype(np.uint8)
    out[:, :, 1] = despilled_g.astype(np.uint8)
    out[:, :, 2] = b.astype(np.uint8)
    out[:, :, 3] = alpha.astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def remove_white_bg(img: Image.Image, threshold: int = 240) -> Image.Image:
    """Replaces background white with transparent alpha (used for facial features)."""
    rgba = img.convert("RGBA")
    arr = np.array(rgba)
    is_white = (arr[:, :, 0] > threshold) & (arr[:, :, 1] > threshold) & (arr[:, :, 2] > threshold)
    arr[is_white, 3] = 0
    return Image.fromarray(arr, "RGBA")


def extract_feature(box_img: Image.Image, skin_threshold: float = 24.0) -> Image.Image:
    """Extracts facial features (eyes or mouth) by removing surrounding skin background."""
    rgba = box_img.convert("RGBA")
    arr = np.array(rgba)
    h, w = arr.shape[:2]
    corners = np.concatenate([
        arr[5:25, 5:25, :3].reshape(-1, 3),
        arr[5:25, w-25:w-5, :3].reshape(-1, 3),
        arr[h-25:h-5, 5:25, :3].reshape(-1, 3),
        arr[h-25:h-5, w-25:w-5, :3].reshape(-1, 3)
    ], axis=0)
    skin_rgb = np.median(corners, axis=0)
    dist = np.sqrt(np.sum((arr[:, :, :3].astype(float) - skin_rgb)**2, axis=2))
    alpha = np.clip((dist - skin_threshold) / 12.0 * 255.0, 0, 255).astype(np.uint8)
    alpha[:4, :] = 0
    alpha[-4:, :] = 0
    alpha[:, :4] = 0
    alpha[:, -4:] = 0
    arr[:, :, 3] = np.minimum(arr[:, :, 3], alpha)
    return Image.fromarray(arr, "RGBA")


def build_tiffany_layers() -> dict[str, Image.Image]:
    """Generates all discrete 2x ($224x224 px$) RGBA sprite layers."""
    print("Loading source artwork and models...")
    bust_raw = get_original_bust()
    head_raw = Image.open(HEAD_SRC)
    face_raw = Image.open(FACE_SRC)
    deal_raw = Image.open(DEAL_POSE_SRC)
    peek_raw = Image.open(PEEK_POSE_SRC)

    layers: dict[str, Image.Image] = {}

    # =========================================================================
    # 1. Shadow (Layer 1 - Soft Grounding Base)
    # =========================================================================
    shadow_raw = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    d_sh = ImageDraw.Draw(shadow_raw)
    d_sh.ellipse([34, 204, 190, 222], fill=(20, 25, 30, 140))
    # Gaussian blur creates natural feathered contact shadow
    layers["shadow"] = shadow_raw.filter(ImageFilter.GaussianBlur(3))

    # =========================================================================
    # 2. Torso (Layer 2 - De-occluded Waistcoat & Shirt)
    # =========================================================================
    torso_poly = [
        (96, 92), (112, 98), (128, 92),
        (140, 105), (162, 117), (155, 165), (153, 195), (152, 224),
        (112, 224),
        (60, 224), (66, 195), (68, 165), (60, 117), (84, 105)
    ]
    torso_mask = Image.new("L", (224, 224), 0)
    d_t = ImageDraw.Draw(torso_mask)
    d_t.polygon(torso_poly, fill=255)
    mask_arr = np.array(torso_mask)

    arr_bust = np.array(bust_raw)
    arr_torso = arr_bust.copy()
    arr_torso[mask_arr == 0] = [0, 0, 0, 0]

    # De-occlude behind deck hand (x: 65..125, y: 185..224)
    for y in range(185, 224):
        for x in range(65, 125):
            if mask_arr[y, x] > 0:
                r, g, b, a = arr_torso[y, x]
                if a > 0 and (r > 40 or g > 40 or b > 40):
                    arr_torso[y, x] = [0, 0, 0, 255]

    layers["torso"] = Image.fromarray(arr_torso, "RGBA")

    # =========================================================================
    # 3. Head (Layer 4 - Blank Face Plate)
    # =========================================================================
    scale_head = 64.0 / 455.0
    h_clean = remove_white_bg(head_raw)
    h_w = int(1024 * scale_head)
    h_h = int(1024 * scale_head)
    h_resized = h_clean.resize((h_w, h_h), Image.Resampling.LANCZOS)
    h_x = int(112 - 506.5 * scale_head)
    h_y = int(4 - 42 * scale_head)

    head_comp = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    head_comp.alpha_composite(h_resized, (h_x, h_y))
    # Clip neck skin at y <= 106 so neck does not overlap bowtie
    arr_h = np.array(head_comp)
    arr_h[106:, :, 3] = 0
    layers["head"] = Image.fromarray(arr_h, "RGBA")

    # =========================================================================
    # 4. Neck (Layer 3 - Discrete Articulation Pillar)
    # =========================================================================
    neck_layer = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    d_nk = ImageDraw.Draw(neck_layer)
    d_nk.polygon([(98, 92), (126, 92), (130, 122), (94, 122)], fill=(250, 198, 160, 255))
    d_nk.line([(98, 92), (94, 122)], fill=(215, 155, 120, 200), width=2)
    d_nk.line([(126, 92), (130, 122)], fill=(215, 155, 120, 200), width=2)
    layers["neck"] = neck_layer

    # =========================================================================
    # 5. Eyes (Layer 5 - Open, Half, Closed)
    # =========================================================================
    eye_configs = [
        ("open", (36, 60, 329, 340)),
        ("half", (365, 60, 658, 340)),
        ("closed", (694, 60, 987, 340)),
    ]
    for eye_name, eye_box in eye_configs:
        sub = face_raw.crop(eye_box)
        clean = extract_feature(sub, skin_threshold=26.0)
        bbox_e = clean.getbbox()
        crop_e = clean.crop(bbox_e) if bbox_e else clean
        scaled_e = crop_e.resize((48, 16), Image.Resampling.LANCZOS)

        e_layer = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        e_layer.alpha_composite(scaled_e, (88, 55))
        layers[f"eyes_{eye_name}"] = e_layer

    # =========================================================================
    # 6. Mouth Visemes (Layer 6 - 8 Phonetic States)
    # =========================================================================
    mouth_configs = [
        ("neutral", (38, 420, 254, 620)),
        ("a", (282, 420, 498, 620)),
        ("o", (526, 420, 741, 620)),
        ("e", (769, 420, 985, 620)),
        ("f", (38, 720, 254, 940)),
        ("talk", (282, 720, 498, 940)),
        ("smirk", (526, 720, 741, 940)),
        ("gasp", (769, 720, 985, 940)),
    ]
    for m_name, m_box in mouth_configs:
        sub = face_raw.crop(m_box)
        clean = extract_feature(sub, skin_threshold=24.0)
        arr_m = np.array(clean)
        arr_m[:60, :, 3] = 0
        clean_lips = Image.fromarray(arr_m, "RGBA")
        bbox_m = clean_lips.getbbox()
        crop_m = clean_lips.crop(bbox_m) if bbox_m else clean_lips

        if m_name in ("a", "talk"):
            m_w, m_h = 24, 15
            pos_y = 87
        elif m_name == "gasp":
            m_w, m_h = 24, 16
            pos_y = 86
        elif m_name in ("e", "smirk"):
            m_w, m_h = 26, 12
            pos_y = 88
        elif m_name == "o":
            m_w, m_h = 18, 15
            pos_y = 87
        elif m_name == "f":
            m_w, m_h = 24, 11
            pos_y = 88
        else:  # neutral
            m_w, m_h = 26, 11
            pos_y = 88

        scaled_m = crop_m.resize((m_w, m_h), Image.Resampling.LANCZOS)
        m_layer = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        m_x = 112 - m_w // 2
        m_layer.alpha_composite(scaled_m, (m_x, pos_y))
        layers[f"mouth_{m_name}"] = m_layer

    # =========================================================================
    # 7. Articulated Arms (Layer 7 - Rest, Deal, Peek)
    # =========================================================================
    # Common Authentic Left Arm holding shoe deck (x: 0..135, y: 95..224)
    arr_left = arr_bust.copy()
    arr_left[:95, :] = [0, 0, 0, 0]
    arr_left[:, 135:] = [0, 0, 0, 0]
    for y in range(95, 224):
        for x in range(0, 135):
            if mask_arr[y, x] > 0:
                if y < 185 or x < 65 or x > 125:
                    arr_left[y, x] = [0, 0, 0, 0]
                else:
                    r, g, b, a = arr_left[y, x]
                    if r <= 40 and g <= 40 and b <= 40:
                        arr_left[y, x] = [0, 0, 0, 0]

    # Clean white void at left table base
    white_void_left = (arr_left[:, :, 0] > 230) & (arr_left[:, :, 1] > 230) & (arr_left[:, :, 2] > 230) & (np.arange(224)[:, None] > 215)
    arr_left[white_void_left, 3] = 0
    clean_left = Image.fromarray(arr_left, "RGBA")

    # --- 7A. ARM REST: Canonical table rest pose ---
    arr_right_rest = arr_bust.copy()
    arr_right_rest[:95, :] = [0, 0, 0, 0]
    arr_right_rest[:, :135] = [0, 0, 0, 0]
    for y in range(95, 224):
        for x in range(135, 224):
            if mask_arr[y, x] > 0:
                arr_right_rest[y, x] = [0, 0, 0, 0]

    sleeve_line = {
        196: 159, 197: 159, 198: 160, 199: 160, 200: 160,
        201: 160, 202: 160, 203: 161, 204: 161, 205: 161,
        206: 161, 207: 162, 208: 163, 209: 164, 210: 165,
        211: 165, 212: 166, 213: 166, 214: 167, 215: 168,
        216: 169, 217: 170, 218: 172, 219: 174, 220: 176,
        221: 178, 222: 180, 223: 182, 224: 184
    }
    for y, min_x in sleeve_line.items():
        if y < 224:
            for x in range(135, min_x):
                arr_right_rest[y, x] = [0, 0, 0, 0]

    for y in range(180, 196):
        for x in range(152, 160):
            r, g, b, a = arr_right_rest[y, x]
            if a > 0 and (r > 200 or (r > 80 and g > 90 and b > 90)):
                arr_right_rest[y, x] = [0, 0, 0, 0]

    clean_right_rest = Image.fromarray(arr_right_rest, "RGBA")
    arm_rest_layer = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    arm_rest_layer.alpha_composite(clean_left)
    arm_rest_layer.alpha_composite(clean_right_rest)
    layers["arm_rest"] = arm_rest_layer

    # --- 7B. ARM DEAL: Card sweep slide pose ---
    deal_keyed = chroma_key_green(deal_raw)
    deal_224 = deal_keyed.resize((224, 224), Image.Resampling.LANCZOS)
    arr_d = np.array(deal_224)
    arr_d[:95, :] = [0, 0, 0, 0]
    arr_d[:, :135] = [0, 0, 0, 0]

    for y in range(95, 224):
        for x in range(135, 224):
            if mask_arr[y, x] > 0:
                if y < 175:
                    arr_d[y, x] = [0, 0, 0, 0]
                else:
                    r, g, b, a = arr_d[y, x]
                    if r <= 40 and g <= 40 and b <= 40:
                        arr_d[y, x] = [0, 0, 0, 0]

    # Remove right-side table armrest rail
    arr_d[:, 193:] = [0, 0, 0, 0]
    arr_d[180:210, 192:] = [0, 0, 0, 0]
    # Remove horizon background line outside card on left
    for y in range(178, 184):
        for x in range(135, 157):
            arr_d[y, x] = [0, 0, 0, 0]
    arr_d[218:, :, 3] = 0

    clean_right_deal = Image.fromarray(arr_d, "RGBA")
    arm_deal_layer = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    arm_deal_layer.alpha_composite(clean_left)
    arm_deal_layer.alpha_composite(clean_right_deal)
    layers["arm_deal"] = arm_deal_layer

    # --- 7C. ARM PEEK: Lifting Ace of Hearts hole card pose ---
    peek_keyed = chroma_key_green(peek_raw)
    peek_224 = peek_keyed.resize((224, 224), Image.Resampling.LANCZOS)
    arr_p = np.array(peek_224)
    arr_p[:95, :] = [0, 0, 0, 0]
    arr_p[:, :115] = [0, 0, 0, 0]
    # For x between 115 and 135: preserve ONLY where the lifted card is (y >= 170)
    arr_p[:170, 115:135] = [0, 0, 0, 0]
    # Remove table armrest rail cleanly to the right of sleeve
    arr_p[:, 194:] = [0, 0, 0, 0]
    arr_p[218:, :, 3] = 0

    clean_right_peek = Image.fromarray(arr_p, "RGBA")
    clean_left_peek = clean_left.copy()
    arr_lp = np.array(clean_left_peek)
    arr_lp[:, 115:] = [0, 0, 0, 0]

    arm_peek_layer = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    arm_peek_layer.alpha_composite(Image.fromarray(arr_lp, "RGBA"))
    arm_peek_layer.alpha_composite(clean_right_peek)
    layers["arm_peek"] = arm_peek_layer

    # =========================================================================
    # 8. Pre-composited Bust Portrait (Wardrobe Card & Dialogs)
    # =========================================================================
    bust_comp = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    bust_comp.alpha_composite(layers["shadow"])
    bust_comp.alpha_composite(layers["neck"])
    bust_comp.alpha_composite(layers["torso"])
    bust_comp.alpha_composite(layers["head"])
    bust_comp.alpha_composite(layers["eyes_open"])
    bust_comp.alpha_composite(layers["mouth_neutral"])
    bust_comp.alpha_composite(layers["arm_rest"])
    layers["bust"] = bust_comp

    return layers


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Building Tiffany 2.0 Puppet discrete layers into: {OUTPUT_DIR}")

    layers_2x = build_tiffany_layers()

    print(f"Exporting {len(layers_2x)} discrete 2x and 1x layer files...")
    for name, img_2x in layers_2x.items():
        # Save 2x ($224x224 px$)
        out_2x = OUTPUT_DIR / f"{name}_2x.png"
        img_2x.save(out_2x, "PNG")

        # Downsample and save 1x ($112x112 px$)
        img_1x = img_2x.resize((112, 112), Image.Resampling.LANCZOS)
        out_1x = OUTPUT_DIR / f"{name}.png"
        img_1x.save(out_1x, "PNG")
        print(f"  Saved: {name}.png & {name}_2x.png")

    print(f"SUCCESS: Tiffany 2.0 Puppet Rig generated successfully with {len(layers_2x)*2} files.")


if __name__ == "__main__":
    main()
