"""
Build crunchy 16-bit pixel-art Hall of Fame achievement trophy sprites and
per-achievement locked '?' silhouettes.

Pipeline:
1. Crops each trophy cell from the 3 concept sprite sheets (Sheet 1: 3x2, Sheet 2: 3x2, Sheet 3: 2x1).
2. Strips exterior white background via border BFS flood-fill (plus optional interior pocket
   clearing for open handles/wreaths while preserving white skulls/cards) and defringes outer halos.
3. Centers each trophy inside a 32x32 logical pixel grid (>= 2px transparent margin on all sides),
   quantizes to a crisp 32-color 16-bit palette (no dithering), and exports NEAREST-upscaled
   64x64 (1x) and 128x128 (2x) RGBA PNGs to `assets/achievements/`.
4. Synthesizes per-achievement locked '?' silhouettes (`locked_<id>.png` & `locked_<id>_2x.png`)
   preserving each trophy's exact silhouette footprint with a crisp pixel-art '?' centered inside.
5. Renders a visual contact sheet for QA inspection.
"""

from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "assets" / "achievements"

SHEET_SPECS = [
    (
        "sheet1",
        (3, 2),
        [
            "exorcist",
            "high_roller",
            "natural_streak",
            "cursed_survivor",
            "split_maestro",
            "big_spender",
        ],
    ),
    (
        "sheet2",
        (3, 2),
        [
            "apprentice_counter",
            "master_counter",
            "shoe_whisperer",
            "count_capitalist",
            "pair_perfectionist",
            "poker_face",
        ],
    ),
    (
        "sheet3",
        (2, 1),
        [
            "tour_champion",
            "ironman_legend",
        ],
    ),
]

# Trophies that have open interior white holes (handles, laurel interior) where enclosed
# pure-white regions should also be made transparent.
CLEAR_INTERIOR_WHITE_IDS = {
    "tour_champion",
    "pair_perfectionist",
    "exorcist",
    "master_counter",
    "apprentice_counter",
    "ironman_legend",
}

# Crisp 7x11 logical-pixel '?' glyph stamped onto locked 32x32 silhouettes
QUESTION_GLYPH = [
    "..###..",
    ".#####.",
    "##...##",
    "##...##",
    "....##.",
    "...##..",
    "..##...",
    "..##...",
    ".......",
    "..##...",
    "..##...",
]


def _is_near_white(rgb: Tuple[int, int, int], thresh: int = 232) -> bool:
    r, g, b = rgb
    return r >= thresh and g >= thresh and b >= thresh and (max(r, g, b) - min(r, g, b)) <= 22


def _strip_background(img: Image.Image, clear_interior_white: bool = False) -> Image.Image:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()

    visited = [[False] * w for _ in range(h)]
    q: deque[Tuple[int, int]] = deque()

    def _enqueue_if_bg(x: int, y: int) -> None:
        if not visited[y][x]:
            r, g, b, a = px[x, y]
            if a == 0 or _is_near_white((r, g, b), thresh=226):
                visited[y][x] = True
                q.append((x, y))

    for x in range(w):
        _enqueue_if_bg(x, 0)
        _enqueue_if_bg(x, h - 1)
    for y in range(h):
        _enqueue_if_bg(0, y)
        _enqueue_if_bg(w - 1, y)

    while q:
        cx, cy = q.popleft()
        px[cx, cy] = (0, 0, 0, 0)
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                r, g, b, a = px[nx, ny]
                if a == 0 or _is_near_white((r, g, b), thresh=226):
                    visited[ny][nx] = True
                    q.append((nx, ny))

    # Optional: clear enclosed pure-white holes (cup handles, laurel loops)
    if clear_interior_white:
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a > 0 and _is_near_white((r, g, b), thresh=246):
                    px[x, y] = (0, 0, 0, 0)

    # 2-pass outer white-halo defringe
    for _ in range(2):
        to_clear = []
        for y in range(h):
            for x in range(w):
                r, g, b, a = px[x, y]
                if a == 0:
                    continue
                if _is_near_white((r, g, b), thresh=208):
                    for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                        if 0 <= nx < w and 0 <= ny < h and px[nx, ny][3] == 0:
                            to_clear.append((x, y))
                            break
        for x, y in to_clear:
            px[x, y] = (0, 0, 0, 0)

    return rgba


def _normalize_to_32x32(rgba: Image.Image) -> Image.Image:
    bbox = rgba.getchannel("A").getbbox()
    if bbox is None:
        return Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    cropped = rgba.crop(bbox)
    cw, ch = cropped.size
    max_dim = 28  # leaves >= 2px transparent headroom on all 4 sides in 32x32
    scale = min(max_dim / cw, max_dim / ch)
    nw = max(1, int(round(cw * scale)))
    nh = max(1, int(round(ch * scale)))

    # Box/Lanczos downsample RGB + crisp alpha threshold to avoid blurry edges
    resized = cropped.resize((nw, nh), Image.Resampling.LANCZOS)
    rpx = resized.load()
    for y in range(nh):
        for x in range(nw):
            r, g, b, a = rpx[x, y]
            if a < 115:
                rpx[x, y] = (0, 0, 0, 0)
            else:
                rpx[x, y] = (r, g, b, 255)

    # Quantize opaque RGB to 32-color 16-bit palette (zero dithering)
    alpha_mask = resized.getchannel("A")
    rgb_q = resized.convert("RGB").quantize(colors=32, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    quant_rgba = rgb_q.convert("RGBA")
    quant_rgba.putalpha(alpha_mask)

    canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    ox = (32 - nw) // 2
    oy = (32 - nh) // 2
    canvas.paste(quant_rgba, (ox, oy), quant_rgba)
    return canvas


def _build_locked_silhouette_32x32(unlocked_32: Image.Image) -> Image.Image:
    w, h = unlocked_32.size
    upx = unlocked_32.load()
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    opx = out.load()

    # Fill silhouette with atmospheric dark emerald shadow + subtle bevel edge
    for y in range(h):
        for x in range(w):
            if upx[x, y][3] == 0:
                continue
            is_edge = False
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if not (0 <= nx < w and 0 <= ny < h) or upx[nx, ny][3] == 0:
                    is_edge = True
                    break
            if is_edge:
                opx[x, y] = (28, 66, 46, 255)  # crisp dark-emerald silhouette rim (#1c422e)
            else:
                opx[x, y] = (10, 26, 18, 255)  # deep shadow core (#0a1a12)

    # Stamp crisp '?' glyph centered on silhouette bbox (only within non-transparent canvas, keeping bbox intact)
    bbox = unlocked_32.getchannel("A").getbbox()
    if bbox is None:
        return out
    cx = (bbox[0] + bbox[2]) // 2
    cy = (bbox[1] + bbox[3]) // 2
    gh = len(QUESTION_GLYPH)
    gw = len(QUESTION_GLYPH[0])
    gx0 = max(bbox[0], min(bbox[2] - gw, cx - gw // 2))
    gy0 = max(bbox[1], min(bbox[3] - gh, cy - gh // 2))

    # 1px dark outline behind '?' (clamped to silhouette bbox so silhouette footprint stays exact)
    for dy, row in enumerate(QUESTION_GLYPH):
        for dx, ch in enumerate(row):
            if ch != "#":
                continue
            px_x = gx0 + dx
            px_y = gy0 + dy
            for oy in (-1, 0, 1):
                for ox in (-1, 0, 1):
                    nx, ny = px_x + ox, px_y + oy
                    if bbox[0] <= nx < bbox[2] and bbox[1] <= ny < bbox[3]:
                        if upx[nx, ny][3] > 0:
                            opx[nx, ny] = (5, 13, 9, 255)

    # Gold/teal '?' foreground pixels
    for dy, row in enumerate(QUESTION_GLYPH):
        for dx, ch in enumerate(row):
            if ch != "#":
                continue
            px_x = gx0 + dx
            px_y = gy0 + dy
            if bbox[0] <= px_x < bbox[2] and bbox[1] <= px_y < bbox[3]:
                # Top highlight in warm gold, lower pixels in muted gold
                opx[px_x, px_y] = (255, 215, 96, 255) if dy < 5 else (212, 175, 55, 255)

    return out


def build_all(sheet1: Path, sheet2: Path, sheet3: Path, out_dir: Path = OUT_DIR, contact_sheet_path: Path | None = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet_paths = {"sheet1": sheet1, "sheet2": sheet2, "sheet3": sheet3}
    rendered_pairs: list[Tuple[str, Image.Image, Image.Image]] = []

    for sheet_key, (cols, rows), ids in SHEET_SPECS:
        sheet_img = Image.open(sheet_paths[sheet_key]).convert("RGB")
        sw, sh = sheet_img.size
        cell_w = sw / cols
        cell_h = sh / rows

        for idx, ach_id in enumerate(ids):
            c = idx % cols
            r = idx // cols
            # Inset 2% from cell border to avoid neighboring bleed
            pad_x = int(cell_w * 0.02)
            pad_y = int(cell_h * 0.02)
            box = (
                int(round(c * cell_w)) + pad_x,
                int(round(r * cell_h)) + pad_y,
                int(round((c + 1) * cell_w)) - pad_x,
                int(round((r + 1) * cell_h)) - pad_y,
            )
            cell = sheet_img.crop(box)
            stripped = _strip_background(cell, clear_interior_white=(ach_id in CLEAR_INTERIOR_WHITE_IDS))
            u32 = _normalize_to_32x32(stripped)
            l32 = _build_locked_silhouette_32x32(u32)

            u64 = u32.resize((64, 64), Image.Resampling.NEAREST)
            u128 = u32.resize((128, 128), Image.Resampling.NEAREST)
            l64 = l32.resize((64, 64), Image.Resampling.NEAREST)
            l128 = l32.resize((128, 128), Image.Resampling.NEAREST)

            u64.save(out_dir / f"{ach_id}.png")
            u128.save(out_dir / f"{ach_id}_2x.png")
            l64.save(out_dir / f"locked_{ach_id}.png")
            l128.save(out_dir / f"locked_{ach_id}_2x.png")
            rendered_pairs.append((ach_id, u64, l64))
            print(f"Built {ach_id}: 64x64 & 128x128 (+ locked '?' silhouette)")

    if contact_sheet_path is not None:
        cols_cs = 2
        rows_cs = (len(rendered_pairs) + 1) // 2
        tile_w, tile_h = 180, 88
        cs = Image.new("RGB", (cols_cs * tile_w + 16, rows_cs * tile_h + 16), (12, 41, 23))
        for i, (_ach_id, u64, l64) in enumerate(rendered_pairs):
            tx = (i % cols_cs) * tile_w + 16
            ty = (i // cols_cs) * tile_h + 16
            cs.paste(u64, (tx, ty), u64)
            cs.paste(l64, (tx + 76, ty), l64)
        contact_sheet_path.parent.mkdir(parents=True, exist_ok=True)
        cs.save(contact_sheet_path)
        print(f"Saved contact sheet: {contact_sheet_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Hall of Fame pixel-art achievement trophies.")
    parser.add_argument("--sheet1", type=Path, required=True)
    parser.add_argument("--sheet2", type=Path, required=True)
    parser.add_argument("--sheet3", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--contact-sheet", type=Path, default=None)
    args = parser.parse_args()
    build_all(args.sheet1, args.sheet2, args.sheet3, args.out_dir, args.contact_sheet)


if __name__ == "__main__":
    main()
