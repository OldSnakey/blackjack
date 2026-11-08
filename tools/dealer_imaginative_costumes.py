"""
Procedural + 16-Bit Master Layer Builder for the 32 Imaginative Dealer Costumes.

Combines authentic 16-bit SNES/arcade pixel-art costume masters (`costume_<variant>_128.png`)
with canonical paper-doll face/viseme rig grafting and per-layer kinematics (`head_<v>`, `neck_<v>`,
`torso_<v>`, `eyes_*_<v>`, `mouth_*_<v>`, `arm_rest_<v>`, `arm_deal_<v>`, `arm_peek_<v>`, `bust_<v>`)
while enforcing the strict top/side frame headroom invariant (`y >= 3` at 1x, `y >= 6` at 2x).
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

OUTLINE = (18, 16, 20, 255)


def _set_px(arr: np.ndarray, y: int, x: int, rgba: tuple[int, int, int, int]) -> None:
    if 3 <= y < 112 and 2 <= x < 110:
        arr[y, x] = rgba


def _draw_outlined_box(
    arr: np.ndarray,
    y0: int,
    y1: int,
    x0: int,
    x1: int,
    hi: tuple[int, int, int, int],
    mid: tuple[int, int, int, int],
    shd: tuple[int, int, int, int],
    outline: tuple[int, int, int, int] = OUTLINE,
) -> None:
    y0_c, y1_c = max(3, y0), min(111, y1)
    x0_c, x1_c = max(2, x0), min(109, x1)
    for y in range(y0_c, y1_c + 1):
        for x in range(x0_c, x1_c + 1):
            if y in (y0_c, y1_c) or x in (x0_c, x1_c):
                _set_px(arr, y, x, outline)
            elif y == y0_c + 1 or x == x0_c + 1:
                _set_px(arr, y, x, hi)
            elif y == y1_c - 1 or x == x1_c - 1:
                _set_px(arr, y, x, shd)
            else:
                _set_px(arr, y, x, mid)


def _draw_hat_crown_and_brim(
    arr: np.ndarray,
    crown_y0: int,
    crown_y1: int,
    crown_x0: int,
    crown_x1: int,
    brim_y0: int,
    brim_y1: int,
    brim_x0: int,
    brim_x1: int,
    hi: tuple[int, int, int, int],
    mid: tuple[int, int, int, int],
    shd: tuple[int, int, int, int],
    band_col: tuple[int, int, int, int] | None = None,
    pinch_center: bool = False,
) -> None:
    cy0 = max(3, crown_y0)
    cy1 = min(111, crown_y1)
    cx_mid = 0.5 * (crown_x0 + crown_x1)
    half_w = max(1.0, 0.5 * (crown_x1 - crown_x0))
    for y in range(cy0, cy1 + 1):
        t = (y - cy0) / max(1, cy1 - cy0)
        cur_hw = int(round(half_w * (0.76 + 0.24 * (t ** 0.65))))
        lx = max(2, int(round(cx_mid - cur_hw)))
        rx = min(109, int(round(cx_mid + cur_hw)))
        for x in range(lx, rx + 1):
            is_top_dip = pinch_center and y == cy0 and abs(x - cx_mid) <= 2.5
            if is_top_dip:
                continue
            is_pinch_outline = pinch_center and y == cy0 + 1 and abs(x - cx_mid) <= 2.5
            if y in (cy0, cy1) or x in (lx, rx) or is_pinch_outline:
                _set_px(arr, y, x, OUTLINE)
            elif band_col is not None and cy1 - 3 <= y <= cy1 - 1:
                _set_px(arr, y, x, band_col)
            elif x < cx_mid - 2 and y <= cy0 + 3:
                _set_px(arr, y, x, hi)
            elif x > cx_mid + 3 or y >= cy1 - 1:
                _set_px(arr, y, x, shd)
            else:
                _set_px(arr, y, x, mid)

    by0 = max(3, brim_y0)
    by1 = min(111, brim_y1)
    bx_mid = 0.5 * (brim_x0 + brim_x1)
    b_hw = max(1.0, 0.5 * (brim_x1 - brim_x0))
    for y in range(by0, by1 + 1):
        for x in range(max(2, brim_x0), min(109, brim_x1) + 1):
            dx_norm = abs(x - bx_mid) / b_hw
            curve_dy = int(round((dx_norm ** 2) * 1.5))
            if y < by0 + curve_dy or y > by1:
                continue
            if y in (by0 + curve_dy, by1) or x in (max(2, brim_x0), min(109, brim_x1)):
                _set_px(arr, y, x, OUTLINE)
            elif y == by0 + curve_dy + 1:
                _set_px(arr, y, x, hi)
            else:
                _set_px(arr, y, x, shd if y == by1 - 1 else mid)


def _draw_sunglasses(
    arr: np.ndarray,
    lx0: int,
    lx1: int,
    rx0: int,
    rx1: int,
    y0: int,
    y1: int,
    frame_col: tuple[int, int, int, int],
    lens_hi: tuple[int, int, int, int],
    lens_mid: tuple[int, int, int, int],
    lens_shd: tuple[int, int, int, int],
) -> None:
    for sx0, sx1 in ((lx0, lx1), (rx0, rx1)):
        for y in range(y0, y1 + 1):
            for x in range(sx0, sx1 + 1):
                if y == y1 and x in (sx0, sx1):
                    continue
                if y in (y0, y1) or x in (sx0, sx1):
                    _set_px(arr, y, x, frame_col)
                elif (x - sx0) + (y - y0) in (2, 3):
                    _set_px(arr, y, x, lens_hi)
                elif y >= y1 - 2:
                    _set_px(arr, y, x, lens_shd)
                else:
                    _set_px(arr, y, x, lens_mid)
    for x in range(lx1 + 1, rx0):
        _set_px(arr, y0 + 1, x, frame_col)
        _set_px(arr, y0 + 2, x, OUTLINE)
    for x in range(lx0 - 3, lx0):
        _set_px(arr, y0 + 1, x, frame_col)
    for x in range(rx1 + 1, rx1 + 4):
        _set_px(arr, y0 + 1, x, frame_col)


def _recolor_vest_and_sleeves(
    torso_112: np.ndarray,
    arm_rest_112: np.ndarray,
    arm_deal_112: np.ndarray,
    arm_peek_112: np.ndarray,
    vest_hi: tuple[int, int, int],
    vest_mid: tuple[int, int, int],
    vest_shd: tuple[int, int, int],
    sleeve_hi: tuple[int, int, int],
    sleeve_mid: tuple[int, int, int],
    sleeve_shd: tuple[int, int, int],
    tie_hi: tuple[int, int, int] | None = None,
    tie_shd: tuple[int, int, int] | None = None,
    shirt_hi: tuple[int, int, int] | None = None,
    shirt_shd: tuple[int, int, int] | None = None,
    pinstripe_col: tuple[int, int, int] | None = None,
    protect_neck_y: int = 69,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Recolors a standard waistcoat/suit torso and dress-shirt sleeves cleanly in 112x112 space."""
    v_torso = torso_112.copy()
    for y in range(52, 112):
        for x in range(112):
            r, g, b, a = [int(v) for v in v_torso[y, x]]
            if a == 0:
                continue
            lum = r + g + b
            if lum < 42:
                continue
            if y <= protect_neck_y and 44 <= x <= 67 and r > b + 22 and g > 70 and r < 245:
                continue
            if tie_hi and tie_shd and 61 <= y <= 76 and 44 <= x <= 67 and lum < 230:
                c = tie_hi if lum >= 115 else tie_shd
                v_torso[y, x] = [c[0], c[1], c[2], 255]
                continue
            if 43 <= x <= 68 and r >= 150 and g >= 150 and b >= 150:
                if shirt_hi and shirt_shd:
                    c = shirt_hi if lum >= 640 else shirt_shd
                    v_torso[y, x] = [c[0], c[1], c[2], 255]
                continue
            if pinstripe_col and (x % 5 == 0) and 30 <= x <= 81 and y >= 72:
                v_torso[y, x] = [pinstripe_col[0], pinstripe_col[1], pinstripe_col[2], 255]
            elif lum >= 185:
                v_torso[y, x] = [vest_hi[0], vest_hi[1], vest_hi[2], 255]
            elif lum >= 110:
                v_torso[y, x] = [vest_mid[0], vest_mid[1], vest_mid[2], 255]
            else:
                v_torso[y, x] = [vest_shd[0], vest_shd[1], vest_shd[2], 255]

    def _recolor_arm(arm_in: np.ndarray, is_deal: bool) -> np.ndarray:
        out = arm_in.copy()
        for y in range(55, 112):
            for x in range(112):
                r, g, b, a = [int(v) for v in out[y, x]]
                if a == 0:
                    continue
                lum = r + g + b
                if lum < 42:
                    continue
                if is_deal:
                    if (b > r + 45 and b > 120) or (70 <= y <= 108 and 28 <= x <= 74 and r > b + 28 and r < 245):
                        continue
                    if 70 <= y <= 102 and 28 <= x <= 68 and lum >= 620:
                        continue
                if pinstripe_col and (x % 5 == 0):
                    out[y, x] = [pinstripe_col[0], pinstripe_col[1], pinstripe_col[2], 255]
                elif lum >= 660:
                    out[y, x] = [sleeve_hi[0], sleeve_hi[1], sleeve_hi[2], 255]
                elif lum >= 520:
                    out[y, x] = [sleeve_mid[0], sleeve_mid[1], sleeve_mid[2], 255]
                else:
                    out[y, x] = [sleeve_shd[0], sleeve_shd[1], sleeve_shd[2], 255]
        return out

    return (
        v_torso,
        _recolor_arm(arm_rest_112, False),
        _recolor_arm(arm_deal_112, True),
        _recolor_arm(arm_peek_112, True),
    )


def _map_128_master_to_112(arr_128: np.ndarray, char_id: str, brow_y_112: int, v_key: str = "") -> np.ndarray:
    """
    Maps a 128x128 costume master into the dealer's canonical 112x112 coordinate space
    using the exact same (cy0, top_pad_1x, shift_x) offset as `build_chunky_paper_doll_character`.
    If a tall headpiece extends above y_112 = 3 (or wide brim/pauldron extends outside x_112 = 2..109),
    smoothly compresses only the outer margin above `brow_y_112` so 100% of the headpiece and its
    dark outline stay inside y in [3, 111] and x in [2, 109] without shifting the face!
    """
    cy0 = 2 if char_id in ("mortimer", "vladimir") else (1 if char_id in ("tiffany", "selene", "uriel") else 6)
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

    def _get_shift_x(sy_128: int) -> int:
        if char_id == "tiffany":
            return 1 if sy_128 <= 65 else 0
        if char_id in ("mortimer", "uriel", "vladimir"):
            return 1
        if char_id == "selene":
            return 2
        if char_id == "malphas":
            return -3
        return 3

    # First check raw y_top in 128 space
    ys_128, xs_128 = np.where(arr_128[:, :, 3] > 0)
    y_top_128 = int(ys_128.min()) if len(ys_128) else cy0
    # Standard mapping: y_112 = y_128 - cy0 + top_pad_1x  <=>  y_128 = y_112 + cy0 - top_pad_1x
    raw_top_112 = y_top_128 - cy0 + top_pad_1x
    brow_y_128 = brow_y_112 + cy0 - top_pad_1x

    # Check horizontal span of head rows after shift_x
    head_span_h = 38 if char_id == "selene" else (8 if char_id in ("professor", "vladimir") else 22)
    head_mask_128 = arr_128[: min(128, brow_y_128 + head_span_h), :, 3] > 0
    _, h_xs = np.where(head_mask_128)
    s_head = _get_shift_x(brow_y_128)
    x_left_128 = (int(h_xs.min()) + s_head) if len(h_xs) else 10
    x_right_128 = (int(h_xs.max()) + s_head) if len(h_xs) else 117

    out_112 = np.zeros((112, 112, 4), dtype=np.uint8)
    target_top_y = max(3, raw_top_112)

    for y in range(target_top_y, 112):
        if raw_top_112 < 3 and y < brow_y_112:
            t_y = (y - 3) / max(1.0, float(brow_y_112 - 3))
            sy = int(round(y_top_128 + t_y * (brow_y_128 - y_top_128)))
        elif char_id == "selene" and y >= 88:
            sy = int(round(85 + (y - 88) * (42.0 / 23.0)))
        elif char_id == "professor" and y >= 63:
            sy = int(round(65 + (y - 63) * (62.0 / 48.0)))
        elif char_id == "vladimir" and y >= 63:
            sy = int(round(61 + (y - 63) * (66.0 / 48.0)))
        else:
            sy = y + cy0 - top_pad_1x
        sy = max(0, min(127, sy))
        shift_x = _get_shift_x(sy)

        is_head_row = y < brow_y_112 + (38 if char_id == "selene" else 18)
        is_noir_scarf = char_id == "tiffany" and v_key == "noir" and y >= 54
        for x in range(2, 110):
            if is_noir_scarf and x < 34:
                if x < 5:
                    continue
                t_x = (x - 5) / 29.0
                sx_shifted = int(round(2 + t_x * ((8 + 34) - 2)))
            elif is_noir_scarf and x > 77:
                if x > 106:
                    continue
                t_x = (x - 77) / 29.0
                sx_shifted = int(round((8 + 77) + t_x * (126 - (8 + 77))))
            elif is_head_row and x_left_128 < 10 and x < 34:
                t_x = (x - 2) / 32.0
                sx_shifted = int(round(x_left_128 + t_x * ((8 + 34) - x_left_128)))
            elif is_head_row and x_right_128 > 117 and x > 77:
                t_x = (x - 77) / 32.0
                sx_shifted = int(round((8 + 77) + t_x * (x_right_128 - (8 + 77))))
            else:
                sx_shifted = x + 8
            sx = sx_shifted - shift_x
            if 0 <= sx < 128:
                out_112[y, x] = arr_128[sy, sx]

    # Ensure any top/side boundary pixel at y=3 or x=2, 109 has a closed dark outline
    for x in range(2, 110):
        if out_112[3, x, 3] > 0:
            out_112[3, x] = OUTLINE
    for y in range(3, 112):
        if out_112[y, 2, 3] > 0:
            out_112[y, 2] = OUTLINE
        if out_112[y, 109, 3] > 0:
            out_112[y, 109] = OUTLINE
    return out_112


def _build_right_dealing_arm_from_base(
    arm_deal_base: np.ndarray,
    arm_rest_base: np.ndarray,
    arm_rest_v: np.ndarray,
    sleeve_hi: tuple[int, int, int],
    sleeve_mid: tuple[int, int, int],
    sleeve_shd: tuple[int, int, int],
    cuff_col: tuple[int, int, int] | None = None,
    hand_skin: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]] | None = None,
) -> np.ndarray:
    """
    Starts with `arm_rest_v.copy()` (preserving 100% of the costume's left and right resting arms,
    shoulders, pauldrons, and stoles) and overlays ONLY the raised dealing/peeking forearm, cuff,
    hand, and canonical blue playing card (`arm_deal_base != arm_rest_base`).
    """
    # First collect all forearm sleeve luminances so dark-sleeved base dealers (Selene) get full 3-tone shading
    sleeve_lums: list[int] = []
    for y in range(88, 112):
        for x in range(60, 102):
            if not np.any(arm_deal_base[y, x] != arm_rest_base[y, x]):
                continue
            r, g, b, a = [int(v) for v in arm_deal_base[y, x]]
            if a > 0 and (x + y >= 169) and (max(r, g, b) >= 48):
                sleeve_lums.append(r + g + b)
    max_s_lum = max(sleeve_lums) if sleeve_lums else 720
    hi_thresh = 620 if max_s_lum >= 400 else int(max_s_lum * 0.82)
    mid_thresh = 450 if max_s_lum >= 400 else int(max_s_lum * 0.58)

    out = arm_rest_v.copy()
    for y in range(55, 112):
        for x in range(24, 112):
            if not np.any(arm_deal_base[y, x] != arm_rest_base[y, x]):
                continue
            r, g, b, a = [int(v) for v in arm_deal_base[y, x]]
            if a == 0:
                continue
            lum = r + g + b
            # Preserve canonical blue playing card back & white card border (y=73..106, x=35..57)
            is_blue_card = (b > r + 35 and b > 105) or (73 <= y <= 106 and 35 <= x <= 57 and lum >= 580)
            if is_blue_card:
                out[y, x] = [r, g, b, 255]
                continue
            # Dark 1px outlines (except interior jacket-cuff line when bare-armed `cuff_col is None`)
            if max(r, g, b) < 48:
                if cuff_col is None and 167 <= x + y <= 170 and 92 <= y <= 102 and 66 <= x <= 75:
                    out[y, x] = [sleeve_shd[0], sleeve_shd[1], sleeve_shd[2], 255]
                else:
                    out[y, x] = [r, g, b, 255]
                continue
            # Sculpted hand region (`y <= 90` or `x + y <= 159` or warm skin pixels inside wrist outline)
            is_hand = (y <= 90) or (x + y <= 159) or (r > b + 20 and x <= 71 and y <= 96)
            if is_hand:
                if hand_skin is not None:
                    h_hi, h_mid, h_shd = hand_skin
                    c_h = h_hi if lum >= 520 else (h_mid if lum >= 360 else h_shd)
                    out[y, x] = [c_h[0], c_h[1], c_h[2], 255]
                else:
                    out[y, x] = [r, g, b, 255]
                continue
            # Shirt wrist cuff band between the wrist outline and jacket cuff outline (`160 <= x + y <= 168`)
            if cuff_col is not None and 160 <= x + y <= 168 and 91 <= y <= 102:
                c_scale = 1.05 if lum >= hi_thresh else (0.90 if lum >= mid_thresh else 0.72)
                out[y, x] = [
                    min(255, int(round(cuff_col[0] * c_scale))),
                    min(255, int(round(cuff_col[1] * c_scale))),
                    min(255, int(round(cuff_col[2] * c_scale))),
                    255,
                ]
                continue
            # Forearm sleeve with 3-tone cylindrical shading
            if lum >= hi_thresh:
                c_s = sleeve_hi
            elif lum >= mid_thresh:
                c_s = sleeve_mid
            else:
                c_s = sleeve_shd
            out[y, x] = [c_s[0], c_s[1], c_s[2], 255]
    return out


def _extract_layers_from_128_master(
    cdir: Path,
    char_id: str,
    v_key: str,
    head_base: np.ndarray,
    neck_base: np.ndarray,
    eyes_open_base: np.ndarray,
    eyes_half_base: np.ndarray,
    eyes_closed_base: np.ndarray,
    mouth_neutral_base: np.ndarray,
    arm_rest_base: np.ndarray,
    arm_deal_base: np.ndarray,
    arm_peek_base: np.ndarray,
    brow_y_112: int,
    head_cutoff_y: int,
    deocclude_box: tuple[int, int, int, int],
    sleeve_cols: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]],
    cuff_col: tuple[int, int, int] | None = None,
    hand_skin: tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]] | None = None,
    eyewear_box: tuple[int, int, int, int] | None = None,
    keep_face_paint: bool = False,
    is_marble_statue: bool = False,
    has_lower_face_mask: bool = False,
) -> dict[str, np.ndarray]:
    """
    Extracts `head`, `neck`, `torso`, `arm_rest`, `arm_deal`, `arm_peek` (and optional `eyes_*` / `mouth_*`)
    from `costume_<v_key>_128.png` in 112x112 space.
    """
    master_128 = np.array(Image.open(cdir / f"costume_{v_key}_128.png").convert("RGBA"))
    c_112 = _map_128_master_to_112(master_128, char_id, brow_y_112=brow_y_112, v_key=v_key)

    # 1) Build `head_<v>`
    v_head = np.zeros_like(head_base)
    for y in range(3, 112):
        for x in range(2, 110):
            if c_112[y, x, 3] == 0:
                continue
            in_base_head = head_base[y, x, 3] > 0
            if char_id == "vladimir":
                # Above y=head_cutoff_y (36), keep hats/crowns/hair; at y>=36 keep only canonical head/ears/jaw so cape collars go to torso
                if y < head_cutoff_y or in_base_head:
                    v_head[y, x] = c_112[y, x]
                continue
            if char_id == "professor":
                # Keep hats/hair/goggles/doctoral tassel above head_cutoff_y, and canonical head/beard below
                is_prof_tassel = v_key == "dean" and y <= 46 and x >= 72
                is_prof_hair = v_key == "mad_scientist" and y <= 51 and (x <= 39 or x >= 72)
                if y < head_cutoff_y or in_base_head or is_prof_tassel or is_prof_hair:
                    if y >= head_cutoff_y and not (is_prof_tassel or is_prof_hair) and not in_base_head:
                        continue
                    v_head[y, x] = c_112[y, x]
                continue
            if char_id == "selene":
                # Keep back katana hilts (y>=46, x<26 or x>85) on torso, and stop outer hair at y<=76 so dealing arm is never occluded
                if v_key == "kunoichi" and y >= 46 and (x < 26 or x > 85):
                    continue
                if y > 82 or (y > 76 and (x < 38 or x > 73)):
                    continue
                if y < head_cutoff_y or in_base_head:
                    v_head[y, x] = c_112[y, x]
                continue

            # Include all pixels above head_cutoff_y, or inside base head mask,
            # or hanging head ornaments (jester bells, bunny ears, veil, chopsticks) above y=52
            is_head_ornament = y <= 50 and (x < 38 or x > 73) and y < head_cutoff_y + 4
            if y < head_cutoff_y or in_base_head or is_head_ornament:
                # For costumes with high collars/epaulets overlapping the lower hair/horns at y >= head_cutoff_y,
                # only take pixels inside the face/jaw column (35 <= x <= 76) when y >= head_cutoff_y
                if y >= head_cutoff_y and (x < 35 or x > 76):
                    continue
                v_head[y, x] = c_112[y, x]

    # Graft canonical de-occluded face & jawline so eyes & mouth visemes animate with zero rectangular seams!
    dy0, dy1, dx0, dx1 = deocclude_box
    eye_mask = (eyes_open_base[:, :, 3] > 0) | (eyes_half_base[:, :, 3] > 0) | (eyes_closed_base[:, :, 3] > 0)
    m_ys, m_xs = np.where(mouth_neutral_base[:, :, 3] > 0)
    my0 = (int(m_ys.min()) - 1) if len(m_ys) else (dy1 - 9)
    my1 = (int(m_ys.max()) + 1) if len(m_ys) else (dy1 - 3)
    mx0 = (int(m_xs.min()) - 1) if len(m_xs) else 47
    mx1 = (int(m_xs.max()) + 1) if len(m_xs) else 64

    if is_marble_statue:
        # De-occlude ONLY the active eye socket pixels and dark lip-crease pixels using `v_head`'s own adjacent marble skin
        e_ys, e_xs = np.where(eye_mask)
        if len(e_ys):
            ey0, ey1 = int(e_ys.min()), int(e_ys.max())
            for x in range(int(e_xs.min()), int(e_xs.max()) + 1):
                ref_c = v_head[min(111, ey1 + 2), x]
                for y in range(ey0, ey1 + 1):
                    if eye_mask[y, x]:
                        v_head[y, x] = ref_c
        for y in range(59, 64):
            for x in range(48, 62):
                r, g, b, _ = [int(v) for v in v_head[y, x]]
                lum = int(round(0.299 * r + 0.587 * g + 0.114 * b))
                if lum < 175 or mouth_neutral_base[y, x, 3] > 0:
                    v_head[y, x] = v_head[58, x] if y <= 60 else v_head[64, x]
    elif keep_face_paint:
        # Keep calavera face paint on skull, only de-occlude active eye sockets and interior teeth viseme box
        for y in range(32, 60):
            for x in range(41, 70):
                near_eye = bool(np.any(eye_mask[max(0, y - 1) : min(112, y + 2), max(0, x - 1) : min(112, x + 2)]))
                in_teeth = (51 <= y <= 57) and (48 <= x <= 63)
                if (near_eye or in_teeth) and head_base[y, x, 3] > 0:
                    v_head[y, x] = head_base[y, x]
    elif has_lower_face_mask:
        # Keep shinobi lower-face menpo mask on `v_head`, only de-occluding the upper cyber-visor/eye sockets (`y <= 53`)
        for y in range(39, 54):
            for x in range(36, 76):
                near_eye = bool(np.any(eye_mask[max(0, y - 1) : min(112, y + 2), max(0, x - 1) : min(112, x + 2)]))
                if near_eye and head_base[y, x, 3] > 0:
                    v_head[y, x] = head_base[y, x]
    elif char_id == "selene":
        # Graft Selene's cyber-visor eye zone and lower face/chin while preserving Valkyrie/Bounty cheek guards at x<=40, x>=71
        for y in range(39, 83):
            lx_s = 41 if y <= 58 else 38
            rx_s = 70 if y <= 58 else 73
            for x in range(35, 77):
                near_eye = bool(np.any(eye_mask[max(0, y - 1) : min(112, y + 2), max(0, x - 1) : min(112, x + 2)]))
                in_lower = (y >= 42) and (lx_s <= x <= rx_s)
                if near_eye or in_lower:
                    if head_base[y, x, 3] > 0:
                        v_head[y, x] = head_base[y, x]
                    elif y >= 74 and 40 <= x <= 71:
                        v_head[y, x] = [0, 0, 0, 0]
    elif char_id == "professor":
        # Graft Professor Edward's complete canonical face and silver beard contour
        for y in range(28, 62):
            for x in range(35, 77):
                near_eye = bool(np.any(eye_mask[max(0, y - 1) : min(112, y + 2), max(0, x - 1) : min(112, x + 2)]))
                in_lower = (y >= 29) and (36 <= x <= 75)
                if near_eye or in_lower:
                    if head_base[y, x, 3] > 0:
                        v_head[y, x] = head_base[y, x]
                    elif y >= 54 and 38 <= x <= 73:
                        v_head[y, x] = [0, 0, 0, 0]
    elif char_id == "vladimir":
        # Graft Count Vladimir's canonical face while preserving Phantom half-mask, Venetian masquerade eye-mask, or Alucard brow/glasses
        for y in range(30, 64):
            for x in range(38, 74):
                near_eye = (
                    False
                    if v_key == "alucard"
                    else bool(np.any(eye_mask[max(0, y - 1) : min(112, y + 2), max(0, x - 1) : min(112, x + 2)]))
                )
                if v_key == "masquerade":
                    in_unmasked = (y >= 45) and (39 <= x <= 72)
                elif v_key == "alucard":
                    in_unmasked = (y >= 41) and (39 <= x <= 72)
                elif v_key == "phantom":
                    in_unmasked = (
                        (30 <= y <= 44 and 58 <= x <= 72)
                        or (45 <= y <= 47 and 48 <= x <= 72)
                        or (48 <= y <= 52 and 46 <= x <= 72)
                        or (y >= 53 and 39 <= x <= 72)
                    )
                else:
                    in_unmasked = (y >= 30) and (39 <= x <= 72)
                if near_eye or in_unmasked:
                    if head_base[y, x, 3] > 0:
                        v_head[y, x] = head_base[y, x]
                    elif y >= 55 and 40 <= x <= 71:
                        v_head[y, x] = [0, 0, 0, 0]
    elif char_id == "uriel":
        # Graft Uriel's exact row-by-row canonical face and closed jawline contour
        for y in range(39, 71):
            if y <= 57:
                lx_u, rx_u = 41, 69
            elif y <= 59:
                lx_u, rx_u = 42, 68
            elif y <= 61:
                lx_u, rx_u = 43, 67
            else:
                lx_u, rx_u = 44 + (y - 62), 66 - (y - 62)
            for x in range(lx_u, rx_u + 1):
                if v_key == "archangel" and y == 39 and 50 <= x <= 60:
                    continue
                if head_base[y, x, 3] > 0:
                    v_head[y, x] = head_base[y, x]
    else:
        # Graft complete canonical face & jawline contour from `head_base` so there is zero rectangular seam around the mouth
        full_face_y0 = (
            31
            if char_id == "malphas"
            else (30 if char_id == "julian" else (32 if char_id == "mortimer" else (41 if v_key == "noir" else 35)))
        )
        for y in range(dy0, 71):
            for x in range(34, 78):
                near_eye = bool(np.any(eye_mask[max(0, y - 1) : min(112, y + 2), max(0, x - 1) : min(112, x + 2)]))
                in_lower_face = (y >= full_face_y0) and (dx0 <= x <= dx1)
                if near_eye or in_lower_face:
                    if head_base[y, x, 3] > 0:
                        v_head[y, x] = head_base[y, x]
                    elif y >= 52 and 40 <= x <= 71:
                        # Clear any dangling chin pixels below head_base's canonical jawline
                        v_head[y, x] = [0, 0, 0, 0]

    # 2) Build `neck_<v>`, `torso_<v>`, and `arm_rest_<v>`
    v_neck = neck_base.copy()
    if is_marble_statue:
        for y in range(112):
            for x in range(112):
                if v_neck[y, x, 3] > 0:
                    r, g, b, _ = [int(v) for v in v_neck[y, x]]
                    lum = int(round(0.299 * r + 0.587 * g + 0.114 * b))
                    v_neck[y, x] = [18, 16, 20, 255] if lum < 40 else ([168, 172, 182, 255] if lum < 150 else [218, 222, 230, 255])

    v_torso = np.zeros_like(head_base)
    v_arm_rest = np.zeros_like(head_base)
    neck_start_y = 36 if char_id == "vladimir" else (40 if char_id == "professor" else max(46, head_cutoff_y - 6))
    arm_split_y = 88 if char_id == "selene" else 74
    for y in range(neck_start_y, 112):
        for x in range(112):
            if c_112[y, x, 3] == 0:
                continue
            # Skip upper head ornaments or face pixels that already belong exclusively to `v_head`
            if y < head_cutoff_y + (12 if char_id in ("vladimir", "professor") else 0) and v_head[y, x, 3] > 0:
                if not (42 <= x <= 69 and y >= head_cutoff_y + 4):
                    continue
            # Also copy collar/choker pixels into v_neck for y <= head_cutoff_y + 10
            if y <= head_cutoff_y + 12 and 38 <= x <= 73:
                v_neck[y, x] = c_112[y, x]
            # Split torso vs outer resting arms at y >= arm_split_y
            if y < arm_split_y:
                v_torso[y, x] = c_112[y, x]
            else:
                if x <= 26 or x >= 85:
                    v_arm_rest[y, x] = c_112[y, x]
                    # Keep upper shoulder/deltoid/pauldron/stole cap on torso too so dealing arm connects seamlessly
                    if y <= arm_split_y + 10 and (14 <= x <= 28 or 83 <= x <= 97):
                        v_torso[y, x] = c_112[y, x]
                else:
                    v_torso[y, x] = c_112[y, x]
                    if x in (27, 28, 83, 84):
                        v_arm_rest[y, x] = c_112[y, x]

    # Ensure bottom row y=111 of torso/arm_rest is 100% flush with the horizon rail
    for arr_b in (v_torso, v_arm_rest):
        if arr_b[111, :, 3].sum() == 0:
            for src_y in range(110, 95, -1):
                if arr_b[src_y, :, 3].sum() > 0:
                    for fill_y in range(src_y + 1, 112):
                        arr_b[fill_y, :] = arr_b[src_y, :]
                    break

    # 3) Build `arm_deal_<v>` and `arm_peek_<v>`
    s_hi, s_mid, s_shd = sleeve_cols
    v_arm_deal = _build_right_dealing_arm_from_base(
        arm_deal_base, arm_rest_base, v_arm_rest, s_hi, s_mid, s_shd, cuff_col=cuff_col, hand_skin=hand_skin
    )
    v_arm_peek = _build_right_dealing_arm_from_base(
        arm_peek_base, arm_rest_base, v_arm_rest, s_hi, s_mid, s_shd, cuff_col=cuff_col, hand_skin=hand_skin
    )

    layers: dict[str, np.ndarray] = {
        "head": v_head,
        "neck": v_neck,
        "torso": v_torso,
        "arm_rest": v_arm_rest,
        "arm_deal": v_arm_deal,
        "arm_peek": v_arm_peek,
    }

    # 4) Build optional `eyes_*_<v>` and `mouth_*_<v>`
    if eyewear_box is not None:
        ey0, ey1, ex0, ex1 = eyewear_box
        for ename, ebase in (("eyes_open", eyes_open_base), ("eyes_half", eyes_half_base), ("eyes_closed", eyes_closed_base)):
            e_arr = ebase.copy()
            for y in range(ey0, ey1 + 1):
                for x in range(ex0, ex1 + 1):
                    if c_112[y, x, 3] > 0:
                        e_arr[y, x] = c_112[y, x]
            layers[ename] = e_arr
        if char_id == "malphas" and v_key == "mephisto":
            for y in range(42, 56):
                for x in range(66, 72):
                    r, g, b, a = [int(v) for v in c_112[y, x]]
                    if a > 0 and r > 160 and g > 110 and r > b + 40:
                        v_head[y, x] = c_112[y, x]

    if has_lower_face_mask:
        # For shinobi lower-face mask (selene_kunoichi), keep neutral/smirk/gasp transparent so bare lips never draw over the mask,
        # and make active speech visemes pulse the crimson cyber-seams on her menpo mask!
        for mname in ("mouth_neutral", "mouth_talk", "mouth_a", "mouth_o", "mouth_e", "mouth_f", "mouth_smirk", "mouth_gasp"):
            m_arr = np.zeros_like(mouth_neutral_base)
            if mname in ("mouth_talk", "mouth_a", "mouth_o", "mouth_e", "mouth_f"):
                for y in range(56, 77):
                    for x in range(42, 70):
                        r, g, b, a = [int(v) for v in v_head[y, x]]
                        if a > 0 and r > g + 45 and r > 120:
                            m_arr[y, x] = [255, 84, 118, 255]
            layers[mname] = m_arr

    if is_marble_statue:
        # Chiseled blank white Carrara marble statue eyes and marble mouth visemes
        for ename, ebase in (("eyes_open", eyes_open_base), ("eyes_half", eyes_half_base), ("eyes_closed", eyes_closed_base)):
            e_arr = np.zeros_like(ebase)
            for y in range(36, 52):
                for x in range(38, 74):
                    if ebase[y, x, 3] > 0:
                        r, g, b, _ = [int(v) for v in ebase[y, x]]
                        lum = int(round(0.299 * r + 0.587 * g + 0.114 * b))
                        if ename == "eyes_open" and b > r + 15:
                            # Convert blue irises into blank chiseled white/grey marble eyeball relief
                            e_arr[y, x] = [232, 234, 240, 255] if lum >= 110 else [188, 192, 202, 255]
                        elif lum < 55:
                            e_arr[y, x] = [54, 58, 66, 255]
                        elif lum < 150:
                            e_arr[y, x] = [156, 160, 170, 255]
                        else:
                            e_arr[y, x] = [238, 240, 246, 255]
            layers[ename] = e_arr

        for mname in ("mouth_neutral", "mouth_talk", "mouth_a", "mouth_o", "mouth_e", "mouth_f", "mouth_smirk", "mouth_gasp"):
            m_path = cdir / f"{mname}.png"
            if m_path.exists():
                m_base = np.array(Image.open(m_path).convert("RGBA"))
                m_arr = np.zeros_like(m_base)
                for y in range(52, 70):
                    for x in range(44, 68):
                        if m_base[y, x, 3] > 0:
                            r, g, b, _ = [int(v) for v in m_base[y, x]]
                            lum = int(round(0.299 * r + 0.587 * g + 0.114 * b))
                            m_arr[y, x] = [44, 46, 54, 255] if lum < 75 else ([148, 152, 162, 255] if lum < 165 else [224, 226, 234, 255])
                layers[mname] = m_arr

    return layers


def build_imaginative_costumes_for_dealer(char_id: str, cdir: Path) -> None:
    """
    Loads the canonical 112x112 base layers from `cdir`, constructs the 4 imaginative
    silhouette-transforming costumes for `char_id`, saves `1x` (112x112) and `2x` (224x224)
    layer PNGs and bust portraits, and verifies top/side frame headroom.
    """
    head_base = np.array(Image.open(cdir / "head.png").convert("RGBA"))
    neck_base = np.array(Image.open(cdir / "neck.png").convert("RGBA"))
    torso_base = np.array(Image.open(cdir / "torso.png").convert("RGBA"))
    eyes_open_base = np.array(Image.open(cdir / "eyes_open.png").convert("RGBA"))
    eyes_half_base = np.array(Image.open(cdir / "eyes_half.png").convert("RGBA"))
    eyes_closed_base = np.array(Image.open(cdir / "eyes_closed.png").convert("RGBA"))
    mouth_neutral_base = np.array(Image.open(cdir / "mouth_neutral.png").convert("RGBA"))
    arm_rest_base = np.array(Image.open(cdir / "arm_rest.png").convert("RGBA"))
    arm_deal_base = np.array(Image.open(cdir / "arm_deal.png").convert("RGBA"))
    arm_peek_base = np.array(Image.open(cdir / "arm_peek.png").convert("RGBA"))

    def save_layer(arr_112: np.ndarray, layer_name: str, v_key: str) -> None:
        if layer_name == "head":
            arr_112[0:3, :, :] = 0
            arr_112[:, 0:2, :] = 0
            arr_112[:, 110:112, :] = 0
        img_1x = Image.fromarray(arr_112, "RGBA")
        img_2x = img_1x.resize((224, 224), Image.Resampling.NEAREST)
        img_1x.save(cdir / f"{layer_name}_{v_key}.png")
        img_2x.save(cdir / f"{layer_name}_{v_key}_2x.png")

    def save_bust(v_key: str) -> None:
        v_bust_2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        for base_lname in ("shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
            cand_v = cdir / f"{base_lname}_{v_key}_2x.png"
            l_path = cand_v if cand_v.exists() else (cdir / f"{base_lname}_2x.png")
            limg = Image.open(l_path).convert("RGBA")
            v_bust_2x.alpha_composite(limg)
        v_bust_2x.save(cdir / f"bust_{v_key}_2x.png")
        v_bust_2x.resize((112, 112), Image.Resampling.NEAREST).save(cdir / f"bust_{v_key}.png")

    def save_extracted_dict(layers_dict: dict[str, np.ndarray], v_key: str) -> None:
        # Remove any stale optional layer files for this variant before saving
        for opt_l in ("eyes_open", "eyes_half", "eyes_closed", "mouth_neutral", "mouth_talk", "mouth_a", "mouth_o", "mouth_e", "mouth_f", "mouth_smirk", "mouth_gasp"):
            if opt_l not in layers_dict:
                for p_stale in (cdir / f"{opt_l}_{v_key}.png", cdir / f"{opt_l}_{v_key}_2x.png"):
                    if p_stale.exists():
                        p_stale.unlink()
        for lname, larr in layers_dict.items():
            save_layer(larr, lname, v_key)
        save_bust(v_key)

    # =========================================================================
    # 1. TIFFANY — VIP Bunny Girl, Vegas Showgirl, Macau Silk Qipao, Femme Fatale Noir
    # =========================================================================
    if char_id == "tiffany":
        seq_arm_r = np.array(Image.open(cdir / "arm_rest_sequin.png").convert("RGBA"))
        seq_arm_d = np.array(Image.open(cdir / "arm_deal_sequin.png").convert("RGBA"))
        seq_arm_p = np.array(Image.open(cdir / "arm_peek_sequin.png").convert("RGBA"))
        rose_arm_r = np.array(Image.open(cdir / "arm_rest_rose.png").convert("RGBA"))
        rose_arm_d = np.array(Image.open(cdir / "arm_deal_rose.png").convert("RGBA"))
        rose_arm_p = np.array(Image.open(cdir / "arm_peek_rose.png").convert("RGBA"))
        tif_peach = ((252, 198, 176), (238, 166, 146), (204, 132, 114))

        # 1A. tiffany_bunny ("VIP Bunny Girl")
        bunny_layers = _extract_layers_from_128_master(
            cdir, "tiffany", "bunny",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            seq_arm_r, seq_arm_d, seq_arm_p,
            brow_y_112=34, head_cutoff_y=55, deocclude_box=(34, 65, 38, 73),
            sleeve_cols=tif_peach, cuff_col=(248, 248, 252), hand_skin=tif_peach,
        )
        save_extracted_dict(bunny_layers, "bunny")

        # 1B. tiffany_showgirl ("Vegas Showgirl")
        show_layers = _extract_layers_from_128_master(
            cdir, "tiffany", "showgirl",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            seq_arm_r, seq_arm_d, seq_arm_p,
            brow_y_112=34, head_cutoff_y=55, deocclude_box=(34, 65, 38, 73),
            sleeve_cols=tif_peach, cuff_col=None,
        )
        save_extracted_dict(show_layers, "showgirl")

        # 1C. tiffany_cheongsam ("Macau Silk Qipao")
        qipao_layers = _extract_layers_from_128_master(
            cdir, "tiffany", "cheongsam",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            seq_arm_r, seq_arm_d, seq_arm_p,
            brow_y_112=34, head_cutoff_y=55, deocclude_box=(34, 65, 38, 73),
            sleeve_cols=tif_peach, cuff_col=None,
        )
        save_extracted_dict(qipao_layers, "cheongsam")

        # 1D. tiffany_noir ("Femme Fatale Noir")
        noir_layers = _extract_layers_from_128_master(
            cdir, "tiffany", "noir",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            rose_arm_r, rose_arm_d, rose_arm_p,
            brow_y_112=34, head_cutoff_y=55, deocclude_box=(37, 65, 38, 73),
            sleeve_cols=((68, 64, 78), (40, 38, 48), (22, 20, 28)),
            hand_skin=((68, 64, 78), (40, 38, 48), (22, 20, 28)),
        )
        save_extracted_dict(noir_layers, "noir")

    # =========================================================================
    # 2. JULIAN — Secret Agent 007, 1920s Speakeasy, Wild West Maverick, 80s Miami Vice
    # =========================================================================
    elif char_id == "julian":
        # 2A. julian_bond ("Secret Agent 007") — 16-bit Ivory Dinner Jacket & Spy Sunglasses master
        bond_layers = _extract_layers_from_128_master(
            cdir, "julian", "bond",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=26, head_cutoff_y=52, deocclude_box=(27, 56, 38, 73),
            sleeve_cols=((250, 246, 234), (236, 230, 214), (204, 196, 178)),
            eyewear_box=(27, 39, 36, 75),
        )
        save_extracted_dict(bond_layers, "bond")

        # 2B. julian_godfather ("1920s Speakeasy")
        h_gf = head_base.copy()
        _draw_hat_crown_and_brim(
            h_gf, 3, 16, 37, 74, 16, 20, 28, 83,
            (92, 94, 106, 255), (56, 58, 68, 255), (34, 36, 44, 255),
            band_col=(188, 24, 44, 255), pinch_center=True,
        )
        t_gf, ar_gf, ad_gf, ap_gf = _recolor_vest_and_sleeves(
            torso_base, arm_rest_base, arm_deal_base, arm_peek_base,
            vest_hi=(84, 86, 96), vest_mid=(48, 50, 58), vest_shd=(28, 30, 36),
            sleeve_hi=(68, 70, 80), sleeve_mid=(46, 48, 56), sleeve_shd=(28, 30, 36),
            tie_hi=(212, 28, 48), tie_shd=(144, 16, 30),
            shirt_hi=(72, 74, 82), shirt_shd=(52, 54, 62),
            pinstripe_col=(148, 152, 166),
        )
        for x in range(56, 74):
            _set_px(t_gf, 96 + ((x - 56) // 6), x, (242, 198, 74, 255))
        save_layer(h_gf, "head", "godfather")
        save_layer(t_gf, "torso", "godfather")
        save_layer(ar_gf, "arm_rest", "godfather")
        save_layer(ad_gf, "arm_deal", "godfather")
        save_layer(ap_gf, "arm_peek", "godfather")
        save_bust("godfather")

        # 2C. julian_maverick ("Wild West Maverick")
        h_mav = head_base.copy()
        _draw_hat_crown_and_brim(
            h_mav, 3, 15, 36, 75, 14, 19, 22, 89,
            (78, 66, 58, 255), (44, 36, 32, 255), (26, 20, 18, 255),
            band_col=(218, 174, 72, 255), pinch_center=True,
        )
        t_mav, ar_mav, ad_mav, ap_mav = _recolor_vest_and_sleeves(
            torso_base, arm_rest_base, arm_deal_base, arm_peek_base,
            vest_hi=(198, 142, 86), vest_mid=(156, 104, 58), vest_shd=(108, 68, 36),
            sleeve_hi=(242, 228, 196), sleeve_mid=(218, 200, 166), sleeve_shd=(182, 162, 128),
            tie_hi=(64, 208, 214), tie_shd=(182, 188, 198),
            shirt_hi=(244, 232, 204), shirt_shd=(212, 196, 164),
        )
        _draw_outlined_box(t_mav, 82, 88, 36, 42, (255, 236, 124, 255), (232, 184, 58, 255), (168, 124, 28, 255))
        save_layer(h_mav, "head", "maverick")
        save_layer(t_mav, "torso", "maverick")
        save_layer(ar_mav, "arm_rest", "maverick")
        save_layer(ad_mav, "arm_deal", "maverick")
        save_layer(ap_mav, "arm_peek", "maverick")
        save_bust("maverick")

        # 2D. julian_miami ("80s Miami Vice")
        h_miami = head_base.copy()
        e_miami = eyes_open_base.copy()
        _draw_sunglasses(
            e_miami, 42, 52, 59, 69, 29, 36,
            (248, 248, 252, 255), (255, 164, 218, 255), (236, 68, 148, 255), (148, 28, 96, 255),
        )
        t_miami, ar_miami, ad_miami, ap_miami = _recolor_vest_and_sleeves(
            torso_base, arm_rest_base, arm_deal_base, arm_peek_base,
            vest_hi=(252, 252, 255), vest_mid=(232, 236, 244), vest_shd=(194, 200, 212),
            sleeve_hi=(252, 252, 255), sleeve_mid=(232, 236, 244), sleeve_shd=(194, 200, 212),
            tie_hi=(36, 214, 218), tie_shd=(20, 158, 168),
            shirt_hi=(48, 224, 228), shirt_shd=(28, 176, 184),
        )
        for x in range(49, 63):
            _set_px(t_miami, 74 + (1 if 52 <= x <= 59 else 0), x, (255, 222, 88, 255))
        save_layer(h_miami, "head", "miami")
        save_layer(e_miami, "eyes_open", "miami")
        save_layer(e_miami, "eyes_half", "miami")
        save_layer(e_miami, "eyes_closed", "miami")
        save_layer(t_miami, "torso", "miami")
        save_layer(ar_miami, "arm_rest", "miami")
        save_layer(ad_miami, "arm_deal", "miami")
        save_layer(ap_miami, "arm_peek", "miami")
        save_bust("miami")

    # =========================================================================
    # 3. PROFESSOR EDWARD — Vegas High-Roller, Baker Street Detective, Quantum Lab Coat, Grand Chancellor
    # =========================================================================
    elif char_id == "professor":
        # 3A. professor_vegas_disguise ("Vegas High-Roller")
        vd_layers = _extract_layers_from_128_master(
            cdir, "professor", "vegas_disguise",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=26, head_cutoff_y=45, deocclude_box=(28, 60, 36, 75),
            sleeve_cols=((248, 240, 214), (228, 214, 184), (192, 176, 144)),
            cuff_col=(204, 34, 54),
            eyewear_box=(27, 40, 38, 73),
        )
        save_extracted_dict(vd_layers, "vegas_disguise")

        # 3B. professor_sherlock ("Baker Street Detective")
        sh_layers = _extract_layers_from_128_master(
            cdir, "professor", "sherlock",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=26, head_cutoff_y=45, deocclude_box=(28, 60, 36, 75),
            sleeve_cols=((142, 114, 82), (104, 80, 56), (68, 52, 36)),
            cuff_col=(184, 38, 44),
        )
        save_extracted_dict(sh_layers, "sherlock")

        # 3C. professor_mad_scientist ("Quantum Lab Coat")
        ms_layers = _extract_layers_from_128_master(
            cdir, "professor", "mad_scientist",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=26, head_cutoff_y=45, deocclude_box=(28, 60, 36, 75),
            sleeve_cols=((248, 250, 255), (218, 224, 236), (176, 184, 200)),
            cuff_col=(48, 228, 108),
        )
        save_extracted_dict(ms_layers, "mad_scientist")

        # 3D. professor_dean ("Grand Chancellor")
        dean_layers = _extract_layers_from_128_master(
            cdir, "professor", "dean",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=26, head_cutoff_y=45, deocclude_box=(28, 60, 36, 75),
            sleeve_cols=((168, 24, 46), (124, 16, 34), (82, 10, 22)),
            cuff_col=(242, 198, 68),
        )
        save_extracted_dict(dean_layers, "dean")

    # =========================================================================
    # 4. SELENE — Cyber Kunoichi, Mecha Valkyrie, Retro Arcade Idol, Void Bounty Hunter
    # =========================================================================
    elif char_id == "selene":
        selene_skin = ((218, 184, 153), (186, 148, 122), (142, 108, 88))

        # 4A. selene_kunoichi ("Cyber Kunoichi")
        kun_layers = _extract_layers_from_128_master(
            cdir, "selene", "kunoichi",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=46, deocclude_box=(39, 82, 37, 74),
            sleeve_cols=((56, 58, 68), (34, 36, 44), (20, 22, 28)),
            cuff_col=(238, 38, 68), hand_skin=selene_skin,
            has_lower_face_mask=True,
        )
        save_extracted_dict(kun_layers, "kunoichi")

        # 4B. selene_valkyrie ("Mecha Valkyrie")
        val_layers = _extract_layers_from_128_master(
            cdir, "selene", "valkyrie",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=52, deocclude_box=(39, 82, 37, 74),
            sleeve_cols=((248, 248, 255), (218, 222, 234), (168, 174, 192)),
            cuff_col=(234, 188, 62), hand_skin=selene_skin,
        )
        save_extracted_dict(val_layers, "valkyrie")

        # 4C. selene_synthwave ("Retro Arcade Idol")
        syn_layers = _extract_layers_from_128_master(
            cdir, "selene", "synthwave",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=52, deocclude_box=(39, 82, 37, 74),
            sleeve_cols=((48, 236, 255), (228, 38, 212), (124, 24, 168)),
            cuff_col=(255, 64, 218), hand_skin=selene_skin,
        )
        save_extracted_dict(syn_layers, "synthwave")

        # 4D. selene_bounty ("Void Bounty Hunter")
        bnt_layers = _extract_layers_from_128_master(
            cdir, "selene", "bounty",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=52, deocclude_box=(39, 82, 37, 74),
            sleeve_cols=((116, 120, 128), (78, 82, 88), (46, 48, 54)),
            cuff_col=(48, 228, 255), hand_skin=selene_skin,
        )
        save_extracted_dict(bnt_layers, "bounty")

    # =========================================================================
    # 5. URIEL — Crusader Battleplate, Olympian Apollo, Marble Statue, 70s Disco King
    # =========================================================================
    elif char_id == "uriel":
        uriel_skin = ((248, 196, 172), (224, 162, 138), (188, 124, 102))

        # 5A. uriel_archangel ("Crusader Battleplate")
        arch_layers = _extract_layers_from_128_master(
            cdir, "uriel", "archangel",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=58, deocclude_box=(38, 66, 39, 72),
            sleeve_cols=((232, 238, 248), (168, 178, 198), (108, 116, 136)),
            cuff_col=(238, 190, 64),
        )
        save_extracted_dict(arch_layers, "archangel")

        # 5B. uriel_olympian ("Olympian Apollo")
        oly_layers = _extract_layers_from_128_master(
            cdir, "uriel", "olympian",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=58, deocclude_box=(38, 66, 39, 72),
            sleeve_cols=uriel_skin, cuff_col=None,
        )
        save_extracted_dict(oly_layers, "olympian")

        # 5C. uriel_pontiff ("Marble Statue")
        marble_cols = ((242, 244, 248), (206, 210, 218), (158, 162, 172))
        pont_layers = _extract_layers_from_128_master(
            cdir, "uriel", "pontiff",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=58, deocclude_box=(36, 68, 38, 73),
            sleeve_cols=marble_cols, hand_skin=marble_cols,
            is_marble_statue=True,
        )
        save_extracted_dict(pont_layers, "pontiff")

        # 5D. uriel_fallen ("70s Disco King")
        disco_layers = _extract_layers_from_128_master(
            cdir, "uriel", "fallen",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=38, head_cutoff_y=56, deocclude_box=(36, 66, 38, 73),
            sleeve_cols=((248, 248, 255), (222, 226, 238), (184, 190, 208)),
            cuff_col=(204, 24, 78),
            eyewear_box=(36, 51, 35, 76),
        )
        save_extracted_dict(disco_layers, "fallen")

    # =========================================================================
    # 6. MALPHAS — Infernal Warlord, Faustian Gentleman, Hell's Highway, Underworld Anubis
    # =========================================================================
    elif char_id == "malphas":
        malphas_skin = ((236, 48, 28), (192, 28, 14), (138, 14, 6))

        # 6A. malphas_warlord ("Infernal Warlord")
        war_layers = _extract_layers_from_128_master(
            cdir, "malphas", "warlord",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=28, head_cutoff_y=46, deocclude_box=(28, 58, 39, 72),
            sleeve_cols=((96, 86, 88), (58, 52, 56), (34, 30, 34)),
            cuff_col=(248, 128, 28), hand_skin=malphas_skin,
        )
        save_extracted_dict(war_layers, "warlord")

        # 6B. malphas_mephisto ("Faustian Gentleman")
        mep_layers = _extract_layers_from_128_master(
            cdir, "malphas", "mephisto",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=28, head_cutoff_y=48, deocclude_box=(28, 58, 39, 72),
            sleeve_cols=((142, 18, 36), (96, 12, 24), (58, 6, 14)),
            cuff_col=(236, 188, 62), hand_skin=malphas_skin,
            eyewear_box=(29, 44, 54, 71),
        )
        save_extracted_dict(mep_layers, "mephisto")

        # 6C. malphas_biker ("Hell's Highway")
        bik_layers = _extract_layers_from_128_master(
            cdir, "malphas", "biker",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=28, head_cutoff_y=48, deocclude_box=(28, 58, 39, 72),
            sleeve_cols=((76, 76, 84), (46, 46, 52), (26, 26, 30)),
            cuff_col=(196, 204, 218), hand_skin=malphas_skin,
            eyewear_box=(28, 42, 36, 75),
        )
        save_extracted_dict(bik_layers, "biker")

        # 6D. malphas_pharaoh ("Underworld Anubis")
        pha_layers = _extract_layers_from_128_master(
            cdir, "malphas", "pharaoh",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=28, head_cutoff_y=48, deocclude_box=(28, 58, 39, 72),
            sleeve_cols=malphas_skin, cuff_col=None,
        )
        save_extracted_dict(pha_layers, "pharaoh")

    # =========================================================================
    # 7. MORTIMER — Ghost Pirate Captain, Día de los Muertos, Court of Fools, Hooded Ferryman
    # =========================================================================
    elif char_id == "mortimer":
        bone_hand = ((243, 232, 210), (216, 199, 168), (172, 154, 126))

        # 7A. mortimer_pirate ("Ghost Pirate Captain")
        pir_layers = _extract_layers_from_128_master(
            cdir, "mortimer", "pirate",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=31, head_cutoff_y=52, deocclude_box=(32, 60, 41, 70),
            sleeve_cols=((46, 68, 108), (28, 44, 74), (16, 26, 48)),
            cuff_col=(236, 188, 62), hand_skin=bone_hand,
            eyewear_box=(29, 44, 48, 70),
        )
        save_extracted_dict(pir_layers, "pirate")

        # 7B. mortimer_mariachi ("Día de los Muertos")
        mar_layers = _extract_layers_from_128_master(
            cdir, "mortimer", "mariachi",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=31, head_cutoff_y=52, deocclude_box=(32, 60, 41, 70),
            sleeve_cols=((56, 56, 66), (34, 34, 42), (20, 20, 26)),
            cuff_col=(238, 196, 72), hand_skin=bone_hand,
            keep_face_paint=True,
        )
        save_extracted_dict(mar_layers, "mariachi")

        # 7C. mortimer_jester ("Court of Fools")
        jes_layers = _extract_layers_from_128_master(
            cdir, "mortimer", "jester",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=31, head_cutoff_y=52, deocclude_box=(32, 60, 41, 70),
            sleeve_cols=((196, 32, 64), (118, 38, 184), (72, 20, 118)),
            cuff_col=(244, 198, 64), hand_skin=bone_hand,
        )
        save_extracted_dict(jes_layers, "jester")

        # 7D. mortimer_reaper ("Hooded Ferryman")
        def _clear_mortimer_tophat(arr_in: np.ndarray) -> np.ndarray:
            out = arr_in.copy()
            out[0:32, :, :] = 0
            for y in range(25, 32):
                hw = min(13, 8 + (y - 25) * 2)
                lx, rx = int(55.5 - hw), int(55.5 + hw)
                for x in range(lx, rx + 1):
                    if y == 25 or x in (lx, rx):
                        _set_px(out, y, x, OUTLINE)
                    else:
                        _set_px(out, y, x, (243, 232, 210, 255) if x < 60 else (216, 199, 168, 255))
            return out

        h_rep = _clear_mortimer_tophat(head_base)
        for y in range(4, 61):
            t_y = (y - 4) / 56.0
            outer_hw = int(round(3 + 22 * (t_y ** 0.65)))
            lx, rx = int(55.5 - outer_hw), int(55.5 + outer_hw)
            for x in range(lx, rx + 1):
                if y >= 26 and abs(x - 55.5) <= min(13, 6 + (y - 26) * 0.45):
                    continue
                if y == 4 or x in (lx, rx) or (y == 25 and abs(x - 55.5) <= 7):
                    _set_px(h_rep, y, x, OUTLINE)
                elif x <= lx + 2 or y <= 8:
                    _set_px(h_rep, y, x, (64, 58, 82, 255))
                else:
                    _set_px(h_rep, y, x, (34, 30, 46, 255) if x < 56 else (22, 18, 30, 255))
        t_rep, ar_rep, ad_rep, ap_rep = _recolor_vest_and_sleeves(
            torso_base, arm_rest_base, arm_deal_base, arm_peek_base,
            vest_hi=(96, 224, 242), vest_mid=(38, 34, 52), vest_shd=(22, 18, 32),
            sleeve_hi=(54, 48, 72), sleeve_mid=(34, 30, 46), sleeve_shd=(20, 18, 28),
            tie_hi=(88, 232, 252), tie_shd=(36, 148, 178),
            shirt_hi=(48, 44, 62), shirt_shd=(28, 24, 38),
        )
        _draw_outlined_box(t_rep, 72, 83, 51, 60, (212, 252, 255, 255), (64, 218, 242, 255), (28, 128, 158, 255))
        save_layer(h_rep, "head", "reaper")
        save_layer(t_rep, "torso", "reaper")
        save_layer(ar_rep, "arm_rest", "reaper")
        save_layer(ad_rep, "arm_deal", "reaper")
        save_layer(ap_rep, "arm_peek", "reaper")
        save_bust("reaper")

    # =========================================================================
    # 8. VLADIMIR — Vlad the Impaler, Opera Phantom, Crimson Gunslinger, Venetian Casanova
    # =========================================================================
    elif char_id == "vladimir":
        vlad_skin = ((226, 228, 240), (192, 198, 214), (146, 152, 168))

        # 8A. vladimir_dracul ("Vlad the Impaler")
        dra_layers = _extract_layers_from_128_master(
            cdir, "vladimir", "dracul",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=30, head_cutoff_y=36, deocclude_box=(30, 62, 39, 72),
            sleeve_cols=((188, 28, 48), (138, 18, 32), (82, 10, 20)),
            cuff_col=(242, 198, 68), hand_skin=vlad_skin,
        )
        save_extracted_dict(dra_layers, "dracul")

        # 8B. vladimir_phantom ("Opera Phantom")
        pha_layers = _extract_layers_from_128_master(
            cdir, "vladimir", "phantom",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=30, head_cutoff_y=36, deocclude_box=(30, 62, 39, 72),
            sleeve_cols=((56, 54, 68), (34, 32, 44), (20, 18, 28)),
            cuff_col=(246, 244, 236), hand_skin=vlad_skin,
        )
        save_extracted_dict(pha_layers, "phantom")

        # 8C. vladimir_alucard ("Crimson Gunslinger")
        alu_layers = _extract_layers_from_128_master(
            cdir, "vladimir", "alucard",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=30, head_cutoff_y=36, deocclude_box=(30, 62, 39, 72),
            sleeve_cols=((208, 32, 52), (148, 18, 34), (88, 10, 22)),
            cuff_col=(42, 40, 48), hand_skin=vlad_skin,
            eyewear_box=(29, 41, 40, 71),
        )
        save_extracted_dict(alu_layers, "alucard")

        # 8D. vladimir_masquerade ("Venetian Casanova")
        msq_layers = _extract_layers_from_128_master(
            cdir, "vladimir", "masquerade",
            head_base, neck_base, eyes_open_base, eyes_half_base, eyes_closed_base, mouth_neutral_base,
            arm_rest_base, arm_deal_base, arm_peek_base,
            brow_y_112=30, head_cutoff_y=36, deocclude_box=(30, 62, 39, 72),
            sleeve_cols=((142, 34, 184), (96, 20, 132), (58, 12, 84)),
            cuff_col=(242, 196, 64), hand_skin=vlad_skin,
        )
        save_extracted_dict(msq_layers, "masquerade")
