"""Convert and align the 12 bespoke 16-bit pixel-art costume masters for Selene, Professor, and Vladimir,
and strip all outer-edge anti-aliased white/grey halos and enclosed armpit background pockets across all costumes.
"""

import os
from collections import deque
import numpy as np
from PIL import Image

BRAIN_DIR = r"C:\Users\wrehm\.gemini\antigravity\brain\4d4b5af8-c42c-4aa6-a12b-db9778a254c0"
CHARS_DIR = r"f:\Programming\UdemyPython\Blackjack\assets\haunted\characters"
OUTLINE = np.array([18, 16, 22, 255], dtype=np.uint8)

SOURCES = {
    "selene": {
        "kunoichi": "selene_kunoichi_1794133630347.jpg",
        "valkyrie": "selene_valkyrie_1794133648946.jpg",
        "synthwave": "selene_synthwave_1794133670693.jpg",
        "bounty": "selene_bounty_1794133715528.jpg",
    },
    "professor": {
        "vegas_disguise": "professor_vegas_disguise_1794133630948.jpg",
        "sherlock": "professor_sherlock_1794133651328.jpg",
        "mad_scientist": "professor_mad_scientist_1794133672200.jpg",
        "dean": "professor_dean_1794133689893.jpg",
    },
    "vladimir": {
        "dracul": "vladimir_dracul_1794133668838.jpg",
        "phantom": "vladimir_phantom_1794133691018.jpg",
        "alucard": "vladimir_alucard_1794133760230.jpg",
        "masquerade": "vladimir_masquerade_1794133800516.jpg",
    },
}

# Explicit enclosed background pockets (armpits, under-pauldron gaps, katana-to-hair creases)
# Format: (dealer, variant): list of (y0, y1, x0, x1, min_lum, max_sat)
ENCLOSED_POCKETS: dict[tuple[str, str], list[tuple[int, int, int, int, int, int]]] = {
    ("vladimir", "alucard"): [
        (114, 128, 24, 33, 140, 35),
        (114, 128, 94, 103, 140, 35),
    ],
    ("vladimir", "masquerade"): [
        (116, 128, 24, 32, 140, 35),
        (116, 128, 94, 102, 140, 35),
    ],
    ("professor", "vegas_disguise"): [
        (116, 128, 23, 30, 140, 35),
        (116, 128, 95, 102, 140, 35),
    ],
    ("selene", "valkyrie"): [
        (103, 120, 5, 15, 130, 35),
        (103, 120, 113, 123, 130, 35),
    ],
    ("selene", "kunoichi"): [
        (68, 99, 19, 38, 135, 32),
        (68, 99, 88, 106, 135, 32),
    ],
    ("uriel", "archangel"): [
        (76, 100, 15, 33, 130, 35),
        (76, 100, 94, 112, 130, 35),
    ],
    ("tiffany", "bunny"): [
        (90, 106, 21, 33, 140, 35),
        (90, 106, 94, 106, 140, 35),
    ],
    ("malphas", "biker"): [
        (112, 128, 20, 35, 140, 35),
        (112, 128, 92, 108, 140, 35),
    ],
}


def strip_pockets_and_outer_halo(arr: np.ndarray, dealer: str, variant: str) -> np.ndarray:
    """Clear enclosed armpit/pauldron/katana background pockets and strip all outer-edge white/grey halo pixels."""
    out = arr.copy()
    h, w, _ = out.shape

    # 1. Clear enclosed armpit / under-pauldron / katana pockets
    for y0, y1, x0, x1, min_lum, max_sat in ENCLOSED_POCKETS.get((dealer, variant), []):
        for y in range(max(0, y0), min(h, y1)):
            for x in range(max(0, x0), min(w, x1)):
                if out[y, x, 3] == 0:
                    continue
                r, g, b = int(out[y, x, 0]), int(out[y, x, 1]), int(out[y, x, 2])
                lum = (r + g + b) // 3
                sat = max(r, g, b) - min(r, g, b)
                if lum >= min_lum and sat <= max_sat:
                    out[y, x] = [0, 0, 0, 0]
        # Also strip any residual medium-grey boundary pixels inside the pocket touching the newly cleared pocket
        for _ in range(2):
            for y in range(max(0, y0), min(h, y1)):
                for x in range(max(0, x0), min(w, x1)):
                    if out[y, x, 3] == 0:
                        continue
                    r, g, b = int(out[y, x, 0]), int(out[y, x, 1]), int(out[y, x, 2])
                    lum = (r + g + b) // 3
                    sat = max(r, g, b) - min(r, g, b)
                    if lum >= 85 and sat <= 35:
                        has_trans = False
                        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                            ny, nx = y + dy, x + dx
                            if 0 <= ny < h and 0 <= nx < w and out[ny, nx, 3] == 0:
                                has_trans = True
                                break
                        if has_trans:
                            out[y, x] = OUTLINE

    # 2. Multi-pass outer-edge anti-aliased white/grey halo removal
    # Any neutral grey/white pixel touching exterior transparency (y < 127) that sits outside a darker pixel
    # is a downsampling halo from the #FFFFFF background.
    for _ in range(5):
        alpha = out[:, :, 3] > 0
        trans = ~alpha
        adj_trans = np.zeros_like(trans)
        adj_trans[1:, :] |= trans[:-1, :]
        adj_trans[:-1, :] |= trans[1:, :]
        adj_trans[:, 1:] |= trans[:, :-1]
        adj_trans[:, :-1] |= trans[:, 1:]
        adj_trans[h - 1, :] = False  # Never eat bottom row y=127

        r = out[:, :, 0].astype(int)
        g = out[:, :, 1].astype(int)
        b = out[:, :, 2].astype(int)
        lum = (r + g + b) // 3
        sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)

        # Check if pixel has an 8-connected darker opaque neighbor (e.g., the sprite's dark outline)
        dark_opa = alpha & (lum < 90)
        adj_dark = np.zeros_like(dark_opa)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                sy0, sy1 = max(0, -dy), min(h, h - dy)
                dy0, dy1 = max(0, dy), min(h, h + dy)
                sx0, sx1 = max(0, -dx), min(w, w - dx)
                dx0, dx1 = max(0, dx), min(w, w + dx)
                adj_dark[dy0:dy1, dx0:dx1] |= dark_opa[sy0:sy1, sx0:sx1]

        # Protect Uriel's glowing cyan halo on non-statue variants
        is_cyan_halo = (dealer == "uriel") & (b > r + 25) & (np.arange(h)[:, None] < 55)
        halo_erode = alpha & adj_trans & (~is_cyan_halo) & (lum >= 85) & (sat <= 38) & adj_dark
        if not np.any(halo_erode):
            break
        out[halo_erode] = [0, 0, 0, 0]

    # 3. Clamp any remaining light/medium neutral boundary pixel (touching transparency at y < 127)
    # to the crisp dark 1px silhouette outline so zero white/grey pixels can appear on any edge!
    alpha = out[:, :, 3] > 0
    trans = ~alpha
    adj_trans = np.zeros_like(trans)
    adj_trans[1:, :] |= trans[:-1, :]
    adj_trans[:-1, :] |= trans[1:, :]
    adj_trans[:, 1:] |= trans[:, :-1]
    adj_trans[:, :-1] |= trans[:, 1:]
    adj_trans[h - 1, :] = False

    r = out[:, :, 0].astype(int)
    g = out[:, :, 1].astype(int)
    b = out[:, :, 2].astype(int)
    lum = (r + g + b) // 3
    sat = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    is_cyan_halo = (dealer == "uriel") & (b > r + 25) & (np.arange(h)[:, None] < 55)

    clamp_mask = alpha & adj_trans & (~is_cyan_halo) & (lum >= 80) & (sat <= 38)
    out[clamp_mask] = OUTLINE
    return out


def downsample_and_strip_white(src_path: str, dealer: str, variant: str, thresh: int = 225) -> np.ndarray:
    """Downsample 1024x1024 image to 128x128 and strip exterior white background and armpit pockets."""
    img = Image.open(src_path).convert("RGBA")
    s256 = img.resize((256, 256), Image.Resampling.BOX)
    s128 = s256.resize((128, 128), Image.Resampling.NEAREST)
    out = np.array(s128)
    h, w, _ = out.shape

    r, g, b = out[:, :, 0].astype(int), out[:, :, 1].astype(int), out[:, :, 2].astype(int)
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    sat = cmax - cmin
    lum = (r + g + b) // 3
    is_white = (lum >= thresh) & (sat <= 26)

    visited = np.zeros((h, w), dtype=bool)
    q = deque()
    # Seed from top (y=0), left (x=0), and right (x=w-1) borders
    for x in range(w):
        if is_white[0, x]:
            visited[0, x] = True
            q.append((0, x))
    for y in range(h):
        if is_white[y, 0]:
            visited[y, 0] = True
            q.append((y, 0))
        if is_white[y, w - 1]:
            visited[y, w - 1] = True
            q.append((y, w - 1))

    while q:
        cy, cx = q.popleft()
        out[cy, cx] = [0, 0, 0, 0]
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            ny, nx = cy + dy, cx + dx
            if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and is_white[ny, nx]:
                visited[ny, nx] = True
                q.append((ny, nx))

    return strip_pockets_and_outer_halo(out, dealer, variant)


def remap_top_headroom(arr: np.ndarray, target_y_min: int, anchor_y: int) -> np.ndarray:
    """Compress rows [y_min..anchor_y] into [target_y_min..anchor_y] while keeping [anchor_y..127] untouched."""
    ys = np.where(arr[:, :, 3] > 128)[0]
    if len(ys) == 0:
        return arr
    y_min = int(ys.min())
    if y_min >= target_y_min:
        return arr

    out = np.zeros_like(arr)
    out[anchor_y:, :] = arr[anchor_y:, :]
    src_span = max(1, anchor_y - y_min)
    dst_span = max(1, anchor_y - target_y_min)
    for y_dst in range(target_y_min, anchor_y):
        t = (y_dst - target_y_min) / float(dst_span)
        y_src = int(round(y_min + t * src_span))
        y_src = max(y_min, min(anchor_y - 1, y_src))
        out[y_dst, :] = arr[y_src, :]
    return out


def align_vladimir_dracul(arr: np.ndarray) -> np.ndarray:
    """Align vladimir_dracul (whose face is at dy=+9 due to tall kuka hat) to canonical Vladimir 128 space."""
    out = np.zeros_like(arr)
    # 1. Compress tall kuka crown + plume y_src=1..37 into y_dst=1..28 (y_128=1 maps to y_112=3)
    for y_dst in range(1, 28):
        t = (y_dst - 1) / 27.0
        y_src = int(round(1 + t * 36.0))
        y_src = max(1, min(36, y_src))
        out[y_dst, :] = arr[y_src, :]
    # 2. Shift face and upper chest y_src=37..108 up by -9px into y_dst=28..99
    out[28:99, :] = arr[37:108, :]
    # 3. Stretch lower dragon plate armor y_src=108..127 into y_dst=99..127 so bottom is flush with y=127
    for y_dst in range(99, 128):
        t = (y_dst - 99) / 28.0
        y_src = int(round(108 + t * 19.0))
        y_src = max(108, min(127, y_src))
        out[y_dst, :] = arr[y_src, :]
    return out


def main() -> None:
    # 1. Rebuild & clean the 12 Selene, Professor, and Vladimir masters from high-res renders
    for dealer, variants in SOURCES.items():
        dealer_dir = os.path.join(CHARS_DIR, dealer)
        for v, fname in variants.items():
            src_path = os.path.join(BRAIN_DIR, fname)
            arr = downsample_and_strip_white(src_path, dealer, v)

            if dealer == "selene":
                arr = remap_top_headroom(arr, target_y_min=1, anchor_y=26)
            elif dealer == "professor":
                arr = remap_top_headroom(arr, target_y_min=5, anchor_y=25)
            elif dealer == "vladimir":
                if v == "dracul":
                    arr = align_vladimir_dracul(arr)
                else:
                    arr = remap_top_headroom(arr, target_y_min=1, anchor_y=27)

            # Re-run outer halo guard after vertical remapping
            arr = strip_pockets_and_outer_halo(arr, dealer, v)
            dst_path = os.path.join(dealer_dir, f"costume_{v}_128.png")
            Image.fromarray(arr).save(dst_path)
            ys, xs = np.where(arr[:, :, 3] > 128)
            print(f"Saved {dealer}/costume_{v}_128.png: y={ys.min()}..{ys.max()}, x={xs.min()}..{xs.max()}")

    # 2. Also clean enclosed armpit pockets & outer-edge halos on the other 16 costume masters
    other_dealers = ("tiffany", "julian", "malphas", "mortimer", "uriel")
    for dealer in other_dealers:
        dealer_dir = os.path.join(CHARS_DIR, dealer)
        for fname in sorted(os.listdir(dealer_dir)):
            if not (fname.startswith("costume_") and fname.endswith("_128.png")):
                continue
            v = fname[len("costume_") : -len("_128.png")]
            fpath = os.path.join(dealer_dir, fname)
            arr = np.array(Image.open(fpath).convert("RGBA"))
            cleaned = strip_pockets_and_outer_halo(arr, dealer, v)
            Image.fromarray(cleaned).save(fpath)
            print(f"Cleaned pockets & outer halo on {dealer}/{fname}")


if __name__ == "__main__":
    main()
