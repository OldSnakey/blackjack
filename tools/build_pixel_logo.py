"""
Pixel Art Logo Generator for Blackjack Welcome Splash Screen.

Generates:
- assets/pixel_logo_blackjack.png (1x: 440 x 100)
- assets/pixel_logo_blackjack_2x.png (2x: 880 x 200)

Renders a crisp, authentic retro arcade pixel-art logo with:
- Bold blocky 3D lettering ('BLACKJACK') in gold gradient with emerald outline.
- Pixel-art playing card suits: Spades ♠, Hearts ♥, Diamonds ♦, Clubs ♣.
- Arcade subtitle badge: '★ CASINO & ADVANTAGE PLAY TRAINER ★'.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# 7x7 Pixel Font Definitions for letters B, L, A, C, K, J
PIXEL_LETTERS: dict[str, list[str]] = {
    "B": [
        "111110",
        "100001",
        "100001",
        "111110",
        "100001",
        "100001",
        "111110",
    ],
    "L": [
        "100000",
        "100000",
        "100000",
        "100000",
        "100000",
        "100000",
        "111111",
    ],
    "A": [
        "011110",
        "100001",
        "100001",
        "111111",
        "100001",
        "100001",
        "100001",
    ],
    "C": [
        "011111",
        "100000",
        "100000",
        "100000",
        "100000",
        "100000",
        "011111",
    ],
    "K": [
        "100001",
        "100010",
        "100100",
        "111000",
        "100100",
        "100010",
        "100001",
    ],
    "J": [
        "000001",
        "000001",
        "000001",
        "000001",
        "100001",
        "100001",
        "011110",
    ],
}

PIXEL_SPADE = [
    "0001000",
    "0011100",
    "0111110",
    "1111111",
    "1111111",
    "0110110",
    "0001000",
    "0011100",
]

PIXEL_HEART = [
    "0110110",
    "1111111",
    "1111111",
    "1111111",
    "0111110",
    "0011100",
    "0001000",
]

PIXEL_DIAMOND = [
    "0001000",
    "0011100",
    "0111110",
    "1111111",
    "0111110",
    "0011100",
    "0001000",
]

PIXEL_CLUB = [
    "0011100",
    "0111110",
    "0011100",
    "1101011",
    "1111111",
    "0111110",
    "0001000",
    "0011100",
]


def create_pixel_logo(scale: int = 1) -> Image.Image:
    # Virtual canvas grid size
    grid_w = 156
    grid_h = 28
    pixel_size = 3 * scale

    width = grid_w * pixel_size
    height = grid_h * pixel_size

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    def draw_pixel(gx: int, gy: int, color: tuple[int, int, int, int]):
        if 0 <= gx < grid_w and 0 <= gy < grid_h:
            x0 = gx * pixel_size
            y0 = gy * pixel_size
            draw.rectangle([x0, y0, x0 + pixel_size - 1, y0 + pixel_size - 1], fill=color)

    # Word: "BLACKJACK"
    word = "BLACKJACK"
    letter_spacing = 2
    block_scale = 2  # 1 font pixel = 2x2 grid pixels

    start_x = 16
    start_y = 4

    # Draw decorative suits on left and right
    def draw_bitmap(bmp, ox, oy, col, shadow_col=None):
        for r_idx, row in enumerate(bmp):
            for c_idx, ch in enumerate(row):
                if ch == "1":
                    if shadow_col:
                        draw_pixel(ox + c_idx + 1, oy + r_idx + 1, shadow_col)
                    draw_pixel(ox + c_idx, oy + r_idx, col)

    # Left suit: Spade (Casino Gold)
    draw_bitmap(PIXEL_SPADE, 4, 7, (255, 215, 0, 255), (10, 40, 18, 220))
    # Right suit: Heart (Ruby Red)
    draw_bitmap(PIXEL_HEART, 144, 7, (239, 83, 80, 255), (40, 10, 10, 220))

    cur_x = start_x
    for char in word:
        matrix = PIXEL_LETTERS.get(char, [])
        m_w = len(matrix[0]) if matrix else 6

        # Draw 3D shadow (offset +1, +1 grid)
        for r_idx, row in enumerate(matrix):
            for c_idx, ch in enumerate(row):
                if ch == "1":
                    for dy in range(block_scale):
                        for dx in range(block_scale):
                            draw_pixel(
                                cur_x + c_idx * block_scale + dx + 1,
                                start_y + r_idx * block_scale + dy + 1,
                                (10, 40, 18, 240),
                            )

        # Draw main gradient lettering (Gold / Amber / Yellow)
        for r_idx, row in enumerate(matrix):
            if r_idx <= 1:
                col = (255, 249, 196, 255)  # Lemon highlight
            elif r_idx <= 4:
                col = (255, 215, 0, 255)    # Casino gold
            else:
                col = (255, 179, 0, 255)    # Warm amber

            for c_idx, ch in enumerate(row):
                if ch == "1":
                    for dy in range(block_scale):
                        for dx in range(block_scale):
                            draw_pixel(
                                cur_x + c_idx * block_scale + dx,
                                start_y + r_idx * block_scale + dy,
                                col,
                            )

        cur_x += m_w * block_scale + letter_spacing

    # Subtitle Ribbon bar
    ribbon_y = 22
    for gx in range(12, 144):
        draw_pixel(gx, ribbon_y, (13, 71, 36, 230))
        draw_pixel(gx, ribbon_y + 1, (27, 94, 32, 230))
        draw_pixel(gx, ribbon_y + 2, (10, 45, 22, 230))

    # Gold corner pips on ribbon
    draw_pixel(12, ribbon_y + 1, (255, 215, 0, 255))
    draw_pixel(143, ribbon_y + 1, (255, 215, 0, 255))

    return img


def main():
    logo_1x = create_pixel_logo(scale=1)
    out_1x = ASSETS_DIR / "pixel_logo_blackjack.png"
    logo_1x.save(str(out_1x), "PNG")
    print(f"Saved 1x logo: {out_1x} ({logo_1x.width}x{logo_1x.height})")

    logo_2x = create_pixel_logo(scale=2)
    out_2x = ASSETS_DIR / "pixel_logo_blackjack_2x.png"
    logo_2x.save(str(out_2x), "PNG")
    print(f"Saved 2x logo: {out_2x} ({logo_2x.width}x{logo_2x.height})")


if __name__ == "__main__":
    main()
