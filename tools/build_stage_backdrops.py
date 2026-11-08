"""
16-Bit Crunchy Pixel-Art Horizon Stage Backdrop & Wardrobe Hanger Builder.

Processes the 7 bespoke 16-bit SNES/GBA architectural master renders in
`assets/haunted/backdrops/masters/master_<theme>.jpg` onto a canonical `500x110`
crunchy logical pixel grid (48-color 16-bit palette quantization with ordered
dithering, central dealer-arch contrast framing, and horizon-rail baseboard
grounding), then upscales via `Image.Resampling.NEAREST` to:
  - `1000x220` (`backdrop_<theme>.png`, 1x native `DealerStageCanvas` resolution)
  - `2000x440` (`backdrop_<theme>_2x.png`, 2x High-DPI resolution)

Also builds the 16-bit chunky pixel-art golden coat-hanger icon (`hanger_icon.png`
at `28x28` and `hanger_icon_2x.png` at `56x56`) with a `#121016` dark pixel outline.

All backdrops are guaranteed to be 100% opaque RGB images to eliminate alpha
keying artifacts in Tkinter.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
HAUNTED_DIR = BASE_DIR / "assets" / "haunted"
BACKDROPS_DIR = HAUNTED_DIR / "backdrops"
MASTERS_DIR = BACKDROPS_DIR / "masters"
BACKDROPS_DIR.mkdir(parents=True, exist_ok=True)

LOGICAL_W = 500
LOGICAL_H = 110

# Per-theme crop boxes (x0, y0, x1, y1) on the 1376x768 master renders,
# bottom rail accent color, and central alcove dimming factor behind the dealer.
THEME_SPECS: dict[str, dict] = {
    "casino": {
        "crop": (0, 0, 1376, 640),
        "rail_hi": (212, 175, 55),
        "rail_shd": (18, 12, 10),
        "center_dim": (210, 290, 38, 96, 0.58),
    },
    "creep": {
        "crop": (0, 0, 1376, 660),
        "rail_hi": (92, 82, 48),
        "rail_shd": (10, 8, 14),
        "center_dim": None,
    },
    "crypt": {
        "crop": (0, 10, 1376, 655),
        "rail_hi": (88, 94, 108),
        "rail_shd": (12, 12, 18),
        "center_dim": None,
    },
    "hell": {
        # Center the dark obsidian archway (x_center=674) at x=500
        "crop": (0, 15, 1348, 615),
        "rail_hi": (255, 84, 18),
        "rail_shd": (22, 8, 10),
        "center_dim": None,
    },
    "celestial": {
        "crop": (0, 0, 1376, 650),
        "rail_hi": (255, 215, 64),
        "rail_shd": (24, 28, 48),
        "center_dim": None,
    },
    "cyber": {
        "crop": (0, 10, 1376, 585),
        "rail_hi": (0, 229, 255),
        "rail_shd": (16, 12, 28),
        "center_dim": None,
    },
    "academy": {
        "crop": (0, 80, 1376, 625),
        "rail_hi": (212, 175, 55),
        "rail_shd": (18, 12, 10),
        "center_dim": (215, 285, 36, 104, 0.72),
    },
}


def _build_crunchy_backdrop_pair(theme: str) -> tuple[Image.Image, Image.Image]:
    """
    Loads `masters/master_<theme>.jpg`, crops the architectural stage band,
    downsamples to the `500x110` crunchy pixel grid, applies 16-bit palette
    quantization and horizon-rail grounding, and returns `(img_1x, img_2x)`
    at `(1000x220, 2000x440)` via `NEAREST` neighbor upscaling.
    """
    spec = THEME_SPECS[theme]
    master_path = MASTERS_DIR / f"master_{theme}.jpg"
    src = Image.open(master_path).convert("RGB")
    cropped = src.crop(spec["crop"])

    # Step 1: Downsample via 1000x220 BOX -> 500x110 NEAREST to preserve crisp pixel edges
    mid = cropped.resize((LOGICAL_W * 2, LOGICAL_H * 2), Image.Resampling.BOX)
    low = mid.resize((LOGICAL_W, LOGICAL_H), Image.Resampling.NEAREST)
    arr = np.array(low, dtype=np.float32)

    # Step 2: Optional subtle center-alcove dimming so the dealer puppet pops cleanly
    if spec["center_dim"] is not None:
        cx0, cx1, cy0, cy1, factor = spec["center_dim"]
        for y in range(cy0, cy1):
            # Smooth feather at edges of alcove
            wy = min(1.0, (y - cy0 + 1) / 6.0, (cy1 - y) / 6.0)
            for x in range(cx0, cx1):
                wx = min(1.0, (x - cx0 + 1) / 8.0, (cx1 - x) / 8.0)
                mult = 1.0 - (1.0 - factor) * wx * wy
                arr[y, x] *= mult

    # Step 3: Subtle dark vignette in top-right corner (x=470..499, y=0..22) so golden Wardrobe Hanger pops
    for y in range(0, 24):
        for x in range(466, LOGICAL_W):
            dx = (x - 488) / 16.0
            dy = (y - 9) / 14.0
            d2 = dx * dx + dy * dy
            if d2 < 1.0:
                arr[y, x] *= 0.45 + 0.55 * d2

    # Step 4: Crisp 16-bit Horizon Rail baseboard molding along bottom 2 logical rows (y=108..109)
    r_hi = np.array(spec["rail_hi"], dtype=np.float32)
    r_shd = np.array(spec["rail_shd"], dtype=np.float32)
    arr[LOGICAL_H - 2, :] = arr[LOGICAL_H - 2, :] * 0.35 + r_hi * 0.65
    arr[LOGICAL_H - 1, :] = r_shd

    # Step 5: Quantize to 64-color 16-bit adaptive palette on the 500x110 logical grid
    low_clean = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    quantized = low_clean.quantize(colors=64, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")

    # Step 6: Upscale via NEAREST so every pixel is an exact 2x2 (1x) or 4x4 (2x) crunchy block!
    img_1x = quantized.resize((LOGICAL_W * 2, LOGICAL_H * 2), Image.Resampling.NEAREST)
    img_2x = quantized.resize((LOGICAL_W * 4, LOGICAL_H * 4), Image.Resampling.NEAREST)
    return img_1x, img_2x


def create_casino_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("casino")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_creep_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("creep")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_hell_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("hell")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_celestial_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("celestial")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_crypt_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("crypt")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_cyber_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("cyber")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_academy_backdrop(w: int = 1000, h: int = 220) -> Image.Image:
    img_1x, img_2x = _build_crunchy_backdrop_pair("academy")
    target = img_2x if w >= 1500 else img_1x
    return target if target.size == (w, h) else target.resize((w, h), Image.Resampling.NEAREST)


def create_hanger_icon(size: int = 28) -> Image.Image:
    """Renders a chunky 16-bit pixel-art golden brass coat-hanger icon with a #121016 dark pixel outline."""
    # Authored on a crisp 28x28 pixel grid, then upscaled via NEAREST if size > 28
    grid = np.zeros((28, 28, 4), dtype=np.uint8)
    OUT = (18, 16, 22, 255)
    G_HI = (255, 246, 176, 255)
    G_MID = (242, 198, 64, 255)
    G_SHD = (172, 124, 24, 255)

    def put(y: int, x: int, c: tuple[int, int, int, int]) -> None:
        if 0 <= y < 28 and 0 <= x < 28:
            grid[y, x] = c

    # 1. Swivel hook at top (y=3..11, x=11..16)
    hook_pixels = [
        (4, 12, G_HI), (4, 13, G_HI), (4, 14, G_MID), (4, 15, G_MID),
        (5, 11, G_HI), (5, 16, G_MID),
        (6, 11, G_MID), (6, 16, G_SHD),
        (7, 15, G_MID), (8, 14, G_MID), (9, 14, G_MID), (10, 14, G_SHD), (11, 14, G_SHD),
    ]
    for hy, hx, hc in hook_pixels:
        put(hy, hx, hc)

    # 2. Sloping shoulders from (14, 11) down to (4, 20) and (23, 20)
    for step in range(11):
        lx = 14 - step
        rx = 14 + step
        sy = 11 + (step * 9) // 10
        put(sy, lx, G_HI if step < 8 else G_MID)
        put(sy + 1, lx, G_MID if step < 6 else G_SHD)
        put(sy, rx, G_MID)
        put(sy + 1, rx, G_SHD)

    # 3. Horizontal trouser bar at y=21..22, x=4..24
    for x in range(4, 25):
        put(21, x, G_HI if x < 18 else G_MID)
        put(22, x, G_SHD)

    # 4. Crisp 1px #121016 dark pixel-art outline around all gold pixels
    alpha = grid[:, :, 3] > 0
    for y in range(28):
        for x in range(28):
            if alpha[y, x]:
                continue
            has_gold = False
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < 28 and 0 <= nx < 28 and alpha[ny, nx]:
                    has_gold = True
                    break
            if has_gold:
                grid[y, x] = OUT

    img_28 = Image.fromarray(grid, "RGBA")
    if size != 28:
        return img_28.resize((size, size), Image.Resampling.NEAREST)
    return img_28


def build_all_backdrops() -> None:
    print("Generating 1x (1000x220) and 2x (2000x440) Crunchy 16-Bit Stage Backdrops...")
    for theme in THEME_SPECS:
        img_1x, img_2x = _build_crunchy_backdrop_pair(theme)
        img_1x.save(BACKDROPS_DIR / f"backdrop_{theme}.png")
        img_2x.save(BACKDROPS_DIR / f"backdrop_{theme}_2x.png")
        print(f"  Saved backdrop_{theme}.png ({img_1x.size}) & backdrop_{theme}_2x.png ({img_2x.size})")

    create_hanger_icon(28).save(HAUNTED_DIR / "hanger_icon.png")
    create_hanger_icon(56).save(HAUNTED_DIR / "hanger_icon_2x.png")
    print(f"Successfully generated all 7 pixel-art backdrops in {BACKDROPS_DIR} and hanger icons in {HAUNTED_DIR}!")


if __name__ == "__main__":
    build_all_backdrops()
