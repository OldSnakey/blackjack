"""
Procedural Generator for Dealer Horizon Stage Backdrops and Wardrobe Hanger Icon.
Generates:
- backdrop_casino.png (Classic casino mahogany, brass trim, warm sconces, emerald drapery)
- backdrop_creep.png (Twilight reality warp, dimmed sconces, eerie stone shadows)
- backdrop_hell.png (Infernal volcanic volcanic brimstone, molten magma fissures, glowing embers)
- backdrop_celestial.png (Divine cathedral, golden light rays, celestial stained glass)
- backdrop_crypt.png (Gothic crypt, moonlit arches, stone bricks, misty cobwebs)
- hanger_icon.png (Polished brass wardrobe coat-hanger icon with alpha transparency)

Outputs to assets/haunted/backdrops/ and assets/haunted/
All backdrops are guaranteed to be 100% opaque RGB images to eliminate alpha keying artifacts in Tkinter.
"""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
HAUNTED_DIR = BASE_DIR / "assets" / "haunted"
BACKDROPS_DIR = HAUNTED_DIR / "backdrops"
BACKDROPS_DIR.mkdir(parents=True, exist_ok=True)


def create_casino_backdrop(w: int = 1000, h: int = 140) -> Image.Image:
    """Renders authentic luxury casino mahogany wall with sconces and velvet drape."""
    base = Image.new("RGBA", (w, h), (35, 18, 10, 255))
    draw = ImageDraw.Draw(base)

    # 1. Mahogany vertical panels
    panel_w = 40
    for x in range(0, w, panel_w):
        shade = 25 + (x * 7) % 15
        draw.rectangle([x, 0, x + panel_w - 2, h], fill=(shade + 10, shade // 2, 8, 255))
        # Deep groove between wood slats
        draw.line([x + panel_w - 1, 0, x + panel_w - 1, h], fill=(12, 6, 3, 255), width=2)
        # Subtle wood grain highlight
        draw.line([x + 2, 0, x + 2, h], fill=(shade + 22, shade // 2 + 5, 12, 255), width=1)

    # 2. Warm ambient sconce glows composited on overlay layer
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for sconce_x in (180, w - 180):
        for r in range(110, 0, -5):
            alpha = int(45 * (1.0 - r / 110.0))
            ov_draw.ellipse([sconce_x - r, 30 - r // 2, sconce_x + r, 30 + r // 2], fill=(255, 220, 130, alpha))
        # Sconce brass fixture
        ov_draw.polygon([(sconce_x - 6, 22), (sconce_x + 6, 22), (sconce_x + 3, 38), (sconce_x - 3, 38)], fill=(212, 175, 55, 255))
        ov_draw.ellipse([sconce_x - 4, 16, sconce_x + 4, 24], fill=(255, 245, 180, 255))

    img = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(img)

    # 3. Top emerald velvet drape valance
    drape_h = 24
    draw.rectangle([0, 0, w, drape_h], fill=(7, 76, 26, 255))
    # Scalloped bottom edge of drape
    scallop_w = 50
    for x in range(0, w, scallop_w):
        draw.pieslice([x, drape_h - 10, x + scallop_w, drape_h + 10], 0, 180, fill=(7, 76, 26, 255))
        draw.arc([x, drape_h - 10, x + scallop_w, drape_h + 10], 0, 180, fill=(212, 175, 55, 220), width=2)

    # Gold fringe trim
    draw.line([0, drape_h - 2, w, drape_h - 2], fill=(212, 175, 55, 255), width=2)

    # 4. Lower brass rail shadow along the horizon bottom
    draw.rectangle([0, h - 4, w, h], fill=(15, 8, 4, 255))
    draw.line([0, h - 4, w, h - 4], fill=(212, 175, 55, 180), width=1)

    return img.convert("RGB")


def create_creep_backdrop(w: int = 1000, h: int = 140) -> Image.Image:
    """Renders twilight reality warp backdrop with dimmed flickering sconces and stone creep."""
    base = Image.new("RGBA", (w, h), (20, 14, 18, 255))
    draw = ImageDraw.Draw(base)

    # 1. Darkened, weathered masonry and rotting wood
    for x in range(0, w, 50):
        shade = 18 + (x * 11) % 10
        draw.rectangle([x, 0, x + 48, h], fill=(shade, shade - 2, shade + 4, 255))
        draw.line([x + 49, 0, x + 49, h], fill=(8, 6, 10, 255), width=2)

    # 2. Dim flickering sickly amber sconce & dark vignette on overlay
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    for sconce_x in (180, w - 180):
        for r in range(60, 0, -4):
            alpha = int(35 * (1.0 - r / 60.0))
            ov_draw.ellipse([sconce_x - r, 30 - r // 2, sconce_x + r, 30 + r // 2], fill=(255, 160, 60, alpha))
        ov_draw.polygon([(sconce_x - 5, 24), (sconce_x + 5, 24), (sconce_x + 2, 38), (sconce_x - 2, 38)], fill=(120, 95, 40, 255))
        ov_draw.ellipse([sconce_x - 3, 20, sconce_x + 3, 26], fill=(255, 180, 80, 255))

    # Heavy dark vignette on outer 140px smoothly fading into pitch-black
    for x in range(140):
        alpha = int(240 * (1.0 - x / 140.0))
        ov_draw.line([x, 0, x, h], fill=(2, 2, 3, alpha))
        ov_draw.line([w - 1 - x, 0, w - 1 - x, h], fill=(2, 2, 3, alpha))

    img = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(img)

    # 3. Tattered drape valance
    draw.rectangle([0, 0, w, 18], fill=(12, 28, 16, 255))
    draw.line([0, 18, w, 18], fill=(80, 70, 30, 255), width=1)

    # Bottom edge shadow
    draw.rectangle([0, h - 3, w, h], fill=(5, 5, 5, 255))
    return img.convert("RGB")


def create_hell_backdrop(w: int = 1000, h: int = 140) -> Image.Image:
    """Renders fiery volcanic hellscape with molten fissures and rising brimstone glow."""
    base = Image.new("RGBA", (w, h), (18, 4, 6, 255))
    draw = ImageDraw.Draw(base)

    # 1. Jagged obsidian rock formations
    for x in range(0, w, 40):
        shade = 12 + (x * 13) % 12
        draw.polygon([(x, 0), (x + 35, 0), (x + 38, h), (x - 4, h)], fill=(shade + 6, shade // 3, shade // 2, 255))

    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    # 2. Molten lava glow from below
    for y in range(h - 45, h):
        factor = (y - (h - 45)) / 45.0
        r_val = int(180 * factor + 40)
        g_val = int(50 * factor)
        alpha = int(220 * factor)
        ov_draw.line([0, y, w, y], fill=(r_val, g_val, 0, alpha))

    # 3. Magma fissure cracks
    fissures = [
        [(80, h), (110, h - 25), (140, h - 18), (170, h - 35), (200, h)],
        [(w - 220, h), (w - 180, h - 30), (w - 150, h - 20), (w - 110, h - 38), (w - 70, h)],
        [(w // 2 - 120, h), (w // 2 - 80, h - 22), (w // 2, h - 15), (w // 2 + 70, h - 28), (w // 2 + 110, h)]
    ]
    for pts in fissures:
        ov_draw.line(pts, fill=(255, 100, 0, 180), width=5)
        ov_draw.line(pts, fill=(255, 240, 180, 240), width=2)

    # 4. Floating burning embers
    ember_pts = [
        (120, 45, 3), (160, 25, 2), (230, 60, 4), (w - 140, 35, 3),
        (w - 200, 50, 2), (w - 260, 20, 3), (w // 2 - 50, 40, 3), (w // 2 + 90, 30, 2)
    ]
    for ex, ey, sz in ember_pts:
        ov_draw.ellipse([ex - sz, ey - sz, ex + sz, ey + sz], fill=(255, 180, 50, 230))
        ov_draw.ellipse([ex - 1, ey - 1, ex + 1, ey + 1], fill=(255, 255, 200, 255))

    img = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(img)

    # Infernal bottom rail glow
    draw.line([0, h - 2, w, h - 2], fill=(255, 60, 0, 255), width=2)
    return img.convert("RGB")


def create_celestial_backdrop(w: int = 1000, h: int = 140) -> Image.Image:
    """Renders radiant golden cathedral with celestial rays and luminous stained glass."""
    base = Image.new("RGBA", (w, h), (10, 24, 42, 255))
    draw = ImageDraw.Draw(base)

    # 1. Stained glass lancet windows in the background
    window_xs = [140, 260, w - 260, w - 140]
    for wx in window_xs:
        win_w, win_h = 56, 95
        draw.pieslice([wx - win_w // 2, 10, wx + win_w // 2, 10 + win_h], 180, 360, fill=(30, 70, 110, 255))
        draw.rectangle([wx - win_w // 2, 10 + win_h // 2, wx + win_w // 2, 10 + win_h], fill=(25, 60, 95, 255))
        draw.line([wx, 10, wx, 10 + win_h], fill=(15, 30, 50, 255), width=2)
        draw.line([wx - win_w // 2, 10 + win_h // 2, wx + win_w // 2, 10 + win_h // 2], fill=(15, 30, 50, 255), width=2)

    # 2. Golden divine light rays streaming down on overlay
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    for wx in window_xs:
        win_w, win_h = 56, 95
        ov_draw.pieslice([wx - win_w // 2 + 4, 14, wx + win_w // 2 - 4, 10 + win_h - 4], 180, 360, fill=(255, 215, 0, 140))
        ov_draw.rectangle([wx - win_w // 2 + 4, 14 + win_h // 2, wx + win_w // 2 - 4, 10 + win_h - 4], fill=(255, 230, 100, 120))

    center_x = w // 2
    for angle_deg in range(-55, 60, 18):
        rad = math.radians(angle_deg)
        x_bottom = center_x + int(math.tan(rad) * h * 1.8)
        ray_pts = [(center_x - 10, 0), (center_x + 10, 0), (x_bottom + 45, h), (x_bottom - 45, h)]
        ov_draw.polygon(ray_pts, fill=(255, 235, 140, 28))

    # 3. Soft golden clouds at bottom
    for cx in range(0, w + 40, 70):
        ov_draw.ellipse([cx - 45, h - 25, cx + 45, h + 15], fill=(255, 240, 190, 45))

    img = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(img)

    # Golden holy bottom rail
    draw.line([0, h - 2, w, h - 2], fill=(255, 215, 0, 255), width=2)
    return img.convert("RGB")


def create_crypt_backdrop(w: int = 1000, h: int = 140) -> Image.Image:
    """Renders gothic stone crypt with moonlit arched window, cobwebs, and bricks."""
    base = Image.new("RGBA", (w, h), (18, 20, 24, 255))
    draw = ImageDraw.Draw(base)

    # 1. Ashlar masonry stone blocks
    brick_h = 24
    brick_w = 60
    for row, y in enumerate(range(0, h, brick_h)):
        offset = (row % 2) * (brick_w // 2)
        for x in range(-offset, w, brick_w):
            shade = 22 + (x * 7 + y * 13) % 12
            draw.rectangle([x, y, x + brick_w - 2, y + brick_h - 2], fill=(shade, shade + 2, shade + 5, 255))
            draw.line([x, y + brick_h - 1, x + brick_w, y + brick_h - 1], fill=(8, 10, 12, 255), width=2)
            draw.line([x + brick_w - 1, y, x + brick_w - 1, y + brick_h], fill=(8, 10, 12, 255), width=2)

    # 2. Arched moonlit crypt window (left and right)
    for wx in (160, w - 160):
        draw.pieslice([wx - 32, 12, wx + 32, 85], 180, 360, fill=(45, 65, 80, 255))
        draw.rectangle([wx - 32, 48, wx + 32, 95], fill=(45, 65, 80, 255))
        draw.ellipse([wx - 10, 26, wx + 14, 50], fill=(230, 240, 250, 220))
        draw.line([wx - 12, 20, wx - 12, 95], fill=(15, 18, 20, 255), width=2)
        draw.line([wx + 12, 20, wx + 12, 95], fill=(15, 18, 20, 255), width=2)
        draw.line([wx - 32, 55, wx + 32, 55], fill=(15, 18, 20, 255), width=2)

    # 3. Cobwebs on overlay layer
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)
    for start_x, start_y, step_dir in [(0, 0, 1), (w, 0, -1)]:
        for i in range(1, 5):
            r = i * 16
            ov_draw.arc([start_x - r, start_y - r, start_x + r, start_y + r], 0, 90 if step_dir == 1 else 90, fill=(180, 190, 200, 60), width=1)
            ov_draw.line([start_x, start_y, start_x + step_dir * 50, start_y + 35], fill=(180, 190, 200, 50), width=1)

    img = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(img)

    # Weathered stone rail
    draw.line([0, h - 3, w, h - 3], fill=(70, 75, 85, 255), width=2)
    return img.convert("RGB")


def create_hanger_icon(size: int = 28) -> Image.Image:
    """Renders a polished golden brass coat-hanger icon with alpha transparency."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    scale = size / 28.0
    gold_main = (255, 215, 0, 255)
    gold_dark = (180, 140, 20, 255)
    gold_hilite = (255, 245, 180, 255)

    # 1. Swivel hook top arc
    hook_bbox = [int(11 * scale), int(3 * scale), int(17 * scale), int(11 * scale)]
    draw.arc(hook_bbox, 180, 360, fill=gold_main, width=int(max(2, 2 * scale)))
    # Hook stem down to triangle
    draw.line([int(14 * scale), int(10 * scale), int(14 * scale), int(13 * scale)], fill=gold_main, width=int(max(2, 2 * scale)))

    # 2. Triangular hanger body
    pts = [
        (int(14 * scale), int(13 * scale)),
        (int(24 * scale), int(21 * scale)),
        (int(4 * scale), int(21 * scale)),
    ]
    # Drop shadow
    shadow_pts = [(x + 1, y + 1) for x, y in pts]
    draw.line(shadow_pts + [shadow_pts[0]], fill=(0, 0, 0, 120), width=int(max(2, 2 * scale)))
    # Main brass triangle
    draw.line(pts + [pts[0]], fill=gold_main, width=int(max(2, 2 * scale)))
    # Top highlight
    draw.line([(int(14 * scale), int(13 * scale)), (int(7 * scale), int(19 * scale))], fill=gold_hilite, width=1)

    # 3. Horizontal trouser bar
    draw.line([int(4 * scale), int(21 * scale), int(24 * scale), int(21 * scale)], fill=gold_dark, width=int(max(2, 2 * scale)))
    draw.line([int(5 * scale), int(20 * scale), int(23 * scale), int(20 * scale)], fill=gold_hilite, width=1)

    return img


def build_all_backdrops():
    print("Generating 1x and 2x Panoramic Stage Backdrops...")
    # 1x Backdrops (1000x140)
    create_casino_backdrop(1000, 140).save(BACKDROPS_DIR / "backdrop_casino.png")
    create_creep_backdrop(1000, 140).save(BACKDROPS_DIR / "backdrop_creep.png")
    create_hell_backdrop(1000, 140).save(BACKDROPS_DIR / "backdrop_hell.png")
    create_celestial_backdrop(1000, 140).save(BACKDROPS_DIR / "backdrop_celestial.png")
    create_crypt_backdrop(1000, 140).save(BACKDROPS_DIR / "backdrop_crypt.png")

    # 2x High-DPI Backdrops (2000x280)
    create_casino_backdrop(2000, 280).save(BACKDROPS_DIR / "backdrop_casino_2x.png")
    create_creep_backdrop(2000, 280).save(BACKDROPS_DIR / "backdrop_creep_2x.png")
    create_hell_backdrop(2000, 280).save(BACKDROPS_DIR / "backdrop_hell_2x.png")
    create_celestial_backdrop(2000, 280).save(BACKDROPS_DIR / "backdrop_celestial_2x.png")
    create_crypt_backdrop(2000, 280).save(BACKDROPS_DIR / "backdrop_crypt_2x.png")

    # Wardrobe Hanger Icon (28x28 and 56x56)
    create_hanger_icon(28).save(HAUNTED_DIR / "hanger_icon.png")
    create_hanger_icon(56).save(HAUNTED_DIR / "hanger_icon_2x.png")
    print(f"Successfully generated all backdrops in {BACKDROPS_DIR} and icons in {HAUNTED_DIR}!")


if __name__ == "__main__":
    build_all_backdrops()
