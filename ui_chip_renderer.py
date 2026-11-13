"""
Stateless 2.5D Casino Chip & Grade Medallion Renderer (`ui_chip_renderer.py`).
Shared by ChipVisualizer (1-Seat Mode), TableFeltCanvas (3-Seat Mode),
CountingBootcampFrame, and TripometerDialog.
"""

from __future__ import annotations

import math
import tkinter
from typing import Any, Optional

from bootcamp_domain import BOOTCAMP_GRADE_CHIP_STYLES
from config import CHIP_STYLES
from pixel_ui import get_badge_font, get_display_font, get_element_font, get_header_font, get_title_font
from rules import breakdown_chips


GRADE_CHIP_STYLES: dict[str, dict[str, Any]] = {
    **BOOTCAMP_GRADE_CHIP_STYLES,
    "D": {"denom": 2, "bg": "#9a4b1a", "rim": "#5c2b0c", "stripe": "#ffe082", "fg": "#fff8e1"},
    "N/A": {"denom": 0, "bg": "#1b3024", "rim": "#0e1b14", "stripe": "#4f6b5b", "fg": "#90a4ae"},
    "-": {"denom": 0, "bg": "#1b3024", "rim": "#0e1b14", "stripe": "#4f6b5b", "fg": "#90a4ae"},
    "TOUR_GOLD": {"denom": 500, "bg": "#115e38", "rim": "#093820", "stripe": "#ffd700", "fg": "#fff8e1"},
    "TOUR_IRONMAN": {"denom": 1000, "bg": "#1a0a10", "rim": "#4a0714", "stripe": "#ff1744", "fg": "#ffd700"},
}


def draw_single_25d_chip(
    canvas: tkinter.Canvas,
    x: int,
    y: int,
    denom: int,
    style: dict,
    scale: float = 1.0,
    count: Optional[int] = None,
    tags: tuple[str, ...] | str = "chip",
    compact: bool = False,
) -> list[int]:
    """Draws a single 2.5D casino chip cylinder and returns created canvas item IDs."""
    items: list[int] = []
    rx = int((12 if compact else 14) * scale)
    ry = int((6 if compact else 7) * scale)
    depth = max(2, int((3 if compact else 4) * scale))
    stripe_x = int((6 if compact else 8) * scale)

    # 1. Bottom rim / 3D cylinder body
    items.append(
        canvas.create_oval(
            x - rx, y - ry + depth, x + rx, y + ry + depth,
            fill=style["rim"], outline=style["rim"], tags=tags
        )
    )
    items.append(
        canvas.create_rectangle(
            x - rx, y, x + rx, y + depth,
            fill=style["rim"], outline=style["rim"], tags=tags
        )
    )

    # 2. Edge stripes
    lw = max(1, int(2 * scale))
    items.append(
        canvas.create_line(x - stripe_x, y + 1, x - stripe_x, y + depth, fill=style["stripe"], width=lw, tags=tags)
    )
    items.append(
        canvas.create_line(x + stripe_x, y + 1, x + stripe_x, y + depth, fill=style["stripe"], width=lw, tags=tags)
    )

    # 3. Top face & inner dashed inlay
    items.append(
        canvas.create_oval(
            x - rx, y - ry, x + rx, y + ry,
            fill=style["bg"], outline="#ffffff", width=1, tags=tags
        )
    )
    items.append(
        canvas.create_oval(
            x - rx + int(3 * scale), y - ry + int(2 * scale),
            x + rx - int(3 * scale), y + ry - int(2 * scale),
            outline=style["fg"], dash=(2, 2), tags=tags
        )
    )

    # 4. Denomination label
    short_denom = "$1K" if denom == 1000 else f"${denom}"
    cap_limit = 5 if compact else 6
    display_text = f"x{count}" if (count and count > cap_limit) else short_denom
    items.append(
        canvas.create_text(
            x, y, text=display_text, fill=style["fg"],
            font=get_element_font("chip_face_value", scale=scale), tags=tags
        )
    )
    return items


def draw_felt_chip_stack(
    canvas: tkinter.Canvas,
    cx: int,
    cy: int,
    amount: int,
    tag_prefix: str = "felt_chip",
    scale: float = 1.0,
    compact: bool = False,
) -> list[int]:
    """Renders 2.5D stacked casino chip cylinders and a gold numerical value badge at (cx, cy)."""
    canvas.delete(tag_prefix)
    if amount <= 0:
        return []

    breakdown = breakdown_chips(amount)
    if not breakdown:
        return []

    items: list[int] = []
    num_stacks = len(breakdown)
    spacing = int((18 if compact else 24) * scale)
    total_span = (num_stacks - 1) * spacing
    start_x = cx - (total_span // 2)
    base_y = cy + int(4 * scale)

    for s_idx, (denom, count) in enumerate(breakdown):
        stack_x = start_x + (s_idx * spacing)
        style = CHIP_STYLES.get(denom, CHIP_STYLES[5])
        visible_count = min(count, 5 if compact else 6)
        for c_idx in range(visible_count):
            chip_y = base_y - int(c_idx * 3 * scale)
            is_top = (c_idx == visible_count - 1)
            items.extend(
                draw_single_25d_chip(
                    canvas, stack_x, chip_y, denom, style,
                    scale=scale,
                    count=count if is_top else None,
                    tags=("betting_spot", tag_prefix),
                    compact=compact,
                )
            )

    # Value badge above stack
    badge_y = cy - int((22 if compact else 28) * scale)
    items.append(
        canvas.create_text(
            cx, badge_y,
            text=f"${amount:,}",
            fill="#ffd700",
            font=get_element_font("chip_bet_badge", scale=scale),
            tags=("betting_spot", tag_prefix),
        )
    )
    return items


def draw_25d_grade_medallion(
    canvas: tkinter.Canvas,
    x: int,
    y: int,
    grade: str,
    scale: float = 1.0,
    compact: bool = False,
    mini: bool = False,
    stamp_override: Optional[str] = None,
    extra_tags: tuple[str, ...] = (),
) -> list[int]:
    """
    Renders a high-fidelity 2.5D Casino Chip Medallion with drop shadow, 3D ribbed cylinder wall,
    8 radial casino edge-spot inserts, recessed inner bezel, stitched inlay, and embossed letter grade.
    """
    clean_grade = str(grade or "N/A").strip()
    style = GRADE_CHIP_STYLES.get(clean_grade, GRADE_CHIP_STYLES["C"])
    if stamp_override is not None:
        stamp_text = str(stamp_override)
    elif clean_grade == "TOUR_GOLD":
        stamp_text = "★"
    elif clean_grade == "TOUR_IRONMAN":
        stamp_text = "♦"
    else:
        stamp_text = "-" if clean_grade in ("N/A", "-", "") else clean_grade
    tags = ("grade_medallion", f"grade_medallion_{clean_grade}", *extra_tags)
    items: list[int] = []

    if mini:
        rx, ry, depth = 13, 8, 4
        sh_dx, sh_dy = 2, 2
        stripe_w = 2
        edge_deg_half = 12.0
        face_font = get_badge_font(12)
    elif compact:
        rx, ry, depth = 21, 11, 5
        sh_dx, sh_dy = 2, 3
        stripe_w = 3
        edge_deg_half = 11.0
        face_font = get_header_font(16)
    else:
        rx = max(28, int(27 * scale))
        ry = max(17, int(16 * scale))
        depth = max(7, int(7 * scale))
        sh_dx, sh_dy = 4, 5
        stripe_w = max(4, int(3.5 * scale))
        edge_deg_half = 10.0
        face_font = get_display_font(36) if scale >= 1.8 else get_title_font(24)

    is_small = bool(compact or mini)

    # 1. 2.5D Drop Shadow on table/plaque surface
    items.append(
        canvas.create_oval(
            x - rx + sh_dx - 1,
            y - ry + depth + sh_dy - 1,
            x + rx + sh_dx + 1,
            y + ry + depth + sh_dy + 1,
            fill="#060a08",
            outline="#040705",
            width=1,
            tags=tags,
        )
    )

    # 2. 3D Cylinder Side Wall & Base Rim
    items.append(
        canvas.create_oval(
            x - rx,
            y - ry + depth,
            x + rx,
            y + ry + depth,
            fill=style["rim"],
            outline="#080808",
            width=2 if not is_small else 1,
            tags=tags,
        )
    )
    items.append(
        canvas.create_rectangle(
            x - rx,
            y,
            x + rx,
            y + depth,
            fill=style["rim"],
            outline=style["rim"],
            tags=tags,
        )
    )
    items.append(
        canvas.create_line(
            x - rx, y, x - rx, y + depth, fill="#080808", width=1, tags=tags
        )
    )
    items.append(
        canvas.create_line(
            x + rx, y, x + rx, y + depth, fill="#080808", width=1, tags=tags
        )
    )

    # 3. Visible 3D Cylinder Wall Vertical Edge Stripes along the front lower arc
    for fx in (-0.80, -0.42, 0.0, 0.42, 0.80):
        sx = x + int(fx * rx)
        arc_y = y + int(ry * math.sqrt(max(0.0, 1.0 - fx * fx)))
        items.append(
            canvas.create_line(
                sx,
                arc_y - 1,
                sx,
                arc_y + depth,
                fill=style["stripe"],
                width=stripe_w,
                tags=tags,
            )
        )

    if not is_small:
        # Mid-cylinder stacked medallion groove on large trophy chip
        items.append(
            canvas.create_arc(
                x - rx,
                y - ry + depth // 2,
                x + rx,
                y + ry + depth // 2,
                start=180,
                extent=180,
                style="arc",
                outline="#111111",
                width=1,
                tags=tags,
            )
        )

    # 4. Top Chip Face & Outer Metallic Bevel
    outer_border = (
        "#ffd700"
        if clean_grade in ("S", "A", "B", "TOUR_GOLD", "TOUR_IRONMAN")
        else ("#546e7a" if clean_grade in ("N/A", "-") else "#cfd8dc")
    )
    items.append(
        canvas.create_oval(
            x - rx,
            y - ry,
            x + rx,
            y + ry,
            fill=style["bg"],
            outline=outer_border,
            width=2 if not is_small else 1,
            tags=tags,
        )
    )

    # 5. 8 Radial Casino Edge-Spot Wedges around the perimeter
    r_outer = 0.94
    r_inner = 0.70
    for deg in (0, 45, 90, 135, 180, 225, 270, 315):
        a1 = math.radians(deg - edge_deg_half)
        a2 = math.radians(deg + edge_deg_half)
        pts = [
            x + int(rx * r_inner * math.cos(a1)),
            y + int(ry * r_inner * math.sin(a1)),
            x + int(rx * r_outer * math.cos(a1)),
            y + int(ry * r_outer * math.sin(a1)),
            x + int(rx * r_outer * math.cos(a2)),
            y + int(ry * r_outer * math.sin(a2)),
            x + int(rx * r_inner * math.cos(a2)),
            y + int(ry * r_inner * math.sin(a2)),
        ]
        items.append(
            canvas.create_polygon(
                *pts,
                fill=style["stripe"],
                outline=style["rim"],
                width=1,
                tags=tags,
            )
        )

    # 6. Recessed Inner Medallion Center Disc & Stitched Casino Inlay Ring
    irx, iry = max(8 if mini else 12, int(rx * 0.66)), max(5 if mini else 7, int(ry * 0.66))
    items.append(
        canvas.create_oval(
            x - irx,
            y - iry,
            x + irx,
            y + iry,
            fill=style["bg"],
            outline=style["stripe"],
            width=2 if not is_small else 1,
            tags=tags,
        )
    )
    drx, dry = max(9, int(rx * 0.54)), max(5, int(ry * 0.54))
    if not is_small:
        items.append(
            canvas.create_oval(
                x - drx,
                y - dry,
                x + drx,
                y + dry,
                outline=style["fg"],
                dash=(3, 2),
                width=1,
                tags=tags,
            )
        )

    # 7. Embossed Grade Stamp with 3D Drop Shadow
    sh_off = 1 if is_small else 2
    shadow_col = "#ffffff" if style["fg"] in ("#111111", "#1a1a1a") else "#090503"
    items.append(
        canvas.create_text(
            x + sh_off,
            y + sh_off,
            text=stamp_text,
            fill=shadow_col,
            font=face_font,
            tags=tags,
        )
    )
    items.append(
        canvas.create_text(
            x,
            y,
            text=stamp_text,
            fill=style["fg"],
            font=face_font,
            tags=tags,
        )
    )
    return items


