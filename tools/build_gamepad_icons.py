"""
Deterministic crunchy 16-bit pixel-art generator for Xbox / Steam Deck and
PlayStation controller prompt icons (16x16 logical grid -> 64x64 NEAREST RGBA)
saved into `assets/overlay_icons/`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence, Tuple

from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "assets" / "overlay_icons"

OUTLINE = (18, 16, 22, 255)
WHITE = (248, 250, 252, 255)
DARK_TXT = (18, 16, 22, 255)
GOLD = (255, 215, 64, 255)

# 5x7 crisp pixel glyphs for face/shoulder legends
GLYPHS_5X7: dict[str, list[str]] = {
    "A": [
        ".###.",
        "#...#",
        "#...#",
        "#####",
        "#...#",
        "#...#",
        "#...#",
    ],
    "B": [
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#...#",
        "#...#",
        "####.",
    ],
    "X": [
        "#...#",
        "#...#",
        ".#.#.",
        "..#..",
        ".#.#.",
        "#...#",
        "#...#",
    ],
    "Y": [
        "#...#",
        "#...#",
        ".#.#.",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
    ],
    "L": [
        "#....",
        "#....",
        "#....",
        "#....",
        "#....",
        "#....",
        "#####",
    ],
    "R": [
        "####.",
        "#...#",
        "#...#",
        "####.",
        "#..#.",
        "#...#",
        "#...#",
    ],
    "T": [
        "#####",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
    ],
    "1": [
        "..#..",
        ".##..",
        "..#..",
        "..#..",
        "..#..",
        "..#..",
        ".###.",
    ],
    "2": [
        ".###.",
        "#...#",
        "....#",
        "..##.",
        ".#...",
        "#....",
        "#####",
    ],
}

# 4x5 compact glyphs for 2-letter shoulder/trigger pills (LB, RB, LT, RT, L1, R1, L2, R2)
GLYPHS_4X5: dict[str, list[str]] = {
    "L": [
        "#...",
        "#...",
        "#...",
        "#...",
        "####",
    ],
    "R": [
        "###.",
        "#..#",
        "###.",
        "#.#.",
        "#..#",
    ],
    "B": [
        "###.",
        "#..#",
        "###.",
        "#..#",
        "###.",
    ],
    "T": [
        "####",
        ".##.",
        ".##.",
        ".##.",
        ".##.",
    ],
    "1": [
        ".##.",
        "..#.",
        "..#.",
        "..#.",
        ".###",
    ],
    "2": [
        "###.",
        "...#",
        ".##.",
        "#...",
        "####",
    ],
}

PS_SYMBOLS_7X7: dict[str, list[str]] = {
    "cross": [
        "#.....#",
        "##...##",
        ".##.##.",
        "..###..",
        ".##.##.",
        "##...##",
        "#.....#",
    ],
    "circle": [
        "..###..",
        ".##.##.",
        "##...##",
        "##...##",
        "##...##",
        ".##.##.",
        "..###..",
    ],
    "square": [
        "#######",
        "#######",
        "##...##",
        "##...##",
        "##...##",
        "#######",
        "#######",
    ],
    "triangle": [
        "...#...",
        "..###..",
        ".##.##.",
        ".#...#.",
        "##...##",
        "#######",
        "#######",
    ],
}


def _stamp_bitmap(
    img: Image.Image,
    bitmap: Sequence[str],
    x0: int,
    y0: int,
    color: Tuple[int, int, int, int],
) -> None:
    px = img.load()
    w, h = img.size
    for dy, row in enumerate(bitmap):
        for dx, ch in enumerate(row):
            if ch == "#" and 0 <= x0 + dx < w and 0 <= y0 + dy < h:
                px[x0 + dx, y0 + dy] = color


def _draw_circle_button(
    fill: Tuple[int, int, int, int],
    hi: Tuple[int, int, int, int],
    sh: Tuple[int, int, int, int],
    glyph: Sequence[str],
    glyph_color: Tuple[int, int, int, int],
) -> Image.Image:
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    cx, cy = 7.5, 7.5
    for y in range(16):
        for x in range(16):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= 6.7 ** 2:
                if d2 >= 5.6 ** 2:
                    px[x, y] = OUTLINE
                elif y <= 4 and d2 >= 3.6 ** 2:
                    px[x, y] = hi
                elif y >= 11 and d2 >= 3.6 ** 2:
                    px[x, y] = sh
                else:
                    px[x, y] = fill
    gh = len(glyph)
    gw = len(glyph[0])
    gx = (16 - gw) // 2
    gy = (16 - gh) // 2
    _stamp_bitmap(im, glyph, gx, gy, glyph_color)
    return im


def _draw_bumper_pill(text: str, is_trigger: bool = False) -> Image.Image:
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    top = 2 if is_trigger else 3
    bot = 13 if is_trigger else 12
    fill = (46, 58, 66, 255) if not is_trigger else (36, 46, 54, 255)
    hi = (88, 108, 120, 255)
    sh = (24, 30, 36, 255)
    for y in range(top, bot + 1):
        for x in range(1, 15):
            # Round outer corners
            if (x in (1, 14) and y in (top, bot)):
                continue
            if y in (top, bot) or x in (1, 14) or (x in (2, 13) and y in (top + 1, bot - 1) and False):
                px[x, y] = OUTLINE
            elif y == top + 1:
                px[x, y] = hi
            elif y == bot - 1:
                px[x, y] = sh
            else:
                px[x, y] = fill
    # Outline inner corners
    for cx, cy in ((2, top), (13, top), (2, bot), (13, bot)):
        px[cx, cy] = OUTLINE

    g1 = GLYPHS_4X5[text[0]]
    g2 = GLYPHS_4X5[text[1]]
    gy = (top + bot + 1 - 5) // 2
    _stamp_bitmap(im, g1, 3, gy, WHITE)
    _stamp_bitmap(im, g2, 9, gy, GOLD if is_trigger else WHITE)
    return im


def _draw_dpad(highlight: str = "all") -> Image.Image:
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    base = (48, 58, 64, 255)
    hi_col = (90, 108, 118, 255)
    # Cross shape: x in 5..10 or y in 5..10 within 1..14
    for y in range(1, 15):
        for x in range(1, 15):
            in_v = 5 <= x <= 10 and 1 <= y <= 14
            in_h = 5 <= y <= 10 and 1 <= x <= 14
            if not (in_v or in_h):
                continue
            # Check border
            is_edge = False
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                nv = 5 <= nx <= 10 and 1 <= ny <= 14
                nh = 5 <= ny <= 10 and 1 <= nx <= 14
                if not (nv or nh):
                    is_edge = True
                    break
            px[x, y] = OUTLINE if is_edge else base

    # Directional tips
    up_c = GOLD if highlight in ("ud", "all") else hi_col
    dn_c = GOLD if highlight in ("ud", "all") else hi_col
    lt_c = GOLD if highlight in ("lr", "all") else hi_col
    rt_c = GOLD if highlight in ("lr", "all") else hi_col

    for x in (7, 8):
        px[x, 3] = up_c
        px[x, 12] = dn_c
    for y in (7, 8):
        px[3, y] = lt_c
        px[12, y] = rt_c
    for x in (7, 8):
        for y in (7, 8):
            px[x, y] = (30, 38, 44, 255)
    return im


def _draw_system_button(kind: str) -> Image.Image:
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = im.load()
    cx, cy = 7.5, 7.5
    for y in range(16):
        for x in range(16):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= 6.5 ** 2:
                if d2 >= 5.4 ** 2:
                    px[x, y] = OUTLINE
                elif y <= 4 and d2 >= 3.5 ** 2:
                    px[x, y] = (92, 108, 118, 255)
                else:
                    px[x, y] = (44, 54, 62, 255)
    if kind == "menu":
        for y in (5, 7, 10):
            for x in range(5, 11):
                px[x, y] = WHITE
    else:
        # Overlapping two squares (View / Select)
        for x in range(4, 9):
            px[x, 5] = WHITE
            px[x, 9] = WHITE
        for y in range(5, 10):
            px[4, y] = WHITE
            px[8, y] = WHITE
        for x in range(7, 12):
            px[x, 7] = GOLD
            px[x, 11] = GOLD
        for y in range(7, 12):
            px[7, y] = GOLD
            px[11, y] = GOLD
    return im


def build_all(out_dir: Path = OUT_DIR) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sprites: dict[str, Image.Image] = {
        # Xbox / Steam Deck
        "gamepad_a": _draw_circle_button((46, 125, 50, 255), (102, 187, 106, 255), (27, 94, 32, 255), GLYPHS_5X7["A"], WHITE),
        "gamepad_b": _draw_circle_button((198, 40, 40, 255), (239, 83, 80, 255), (142, 0, 0, 255), GLYPHS_5X7["B"], WHITE),
        "gamepad_x": _draw_circle_button((21, 101, 192, 255), (66, 165, 245, 255), (13, 71, 161, 255), GLYPHS_5X7["X"], WHITE),
        "gamepad_y": _draw_circle_button((249, 168, 37, 255), (255, 213, 79, 255), (193, 121, 0, 255), GLYPHS_5X7["Y"], DARK_TXT),
        "gamepad_lb": _draw_bumper_pill("LB", is_trigger=False),
        "gamepad_rb": _draw_bumper_pill("RB", is_trigger=False),
        "gamepad_lt": _draw_bumper_pill("LT", is_trigger=True),
        "gamepad_rt": _draw_bumper_pill("RT", is_trigger=True),
        "gamepad_dpad": _draw_dpad("all"),
        "gamepad_dpad_lr": _draw_dpad("lr"),
        "gamepad_dpad_ud": _draw_dpad("ud"),
        "gamepad_menu": _draw_system_button("menu"),
        "gamepad_view": _draw_system_button("view"),
        # PlayStation
        "ps_cross": _draw_circle_button((38, 44, 54, 255), (72, 82, 96, 255), (22, 26, 32, 255), PS_SYMBOLS_7X7["cross"], (79, 195, 247, 255)),
        "ps_circle": _draw_circle_button((38, 44, 54, 255), (72, 82, 96, 255), (22, 26, 32, 255), PS_SYMBOLS_7X7["circle"], (255, 110, 110, 255)),
        "ps_square": _draw_circle_button((38, 44, 54, 255), (72, 82, 96, 255), (22, 26, 32, 255), PS_SYMBOLS_7X7["square"], (244, 143, 177, 255)),
        "ps_triangle": _draw_circle_button((38, 44, 54, 255), (72, 82, 96, 255), (22, 26, 32, 255), PS_SYMBOLS_7X7["triangle"], (105, 240, 174, 255)),
        "ps_l1": _draw_bumper_pill("L1", is_trigger=False),
        "ps_r1": _draw_bumper_pill("R1", is_trigger=False),
        "ps_l2": _draw_bumper_pill("L2", is_trigger=True),
        "ps_r2": _draw_bumper_pill("R2", is_trigger=True),
    }
    for name, im16 in sprites.items():
        im64 = im16.resize((64, 64), Image.Resampling.NEAREST)
        im64.save(out_dir / f"{name}.png")
    print(f"Generated {len(sprites)} crunchy 64x64 controller icons in {out_dir}")


if __name__ == "__main__":
    build_all()
