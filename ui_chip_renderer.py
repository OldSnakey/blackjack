"""
Stateless 2.5D Casino Chip Stack Renderer (`ui_chip_renderer.py`).
Shared by ChipVisualizer (1-Seat Mode) and TableFeltCanvas (3-Seat Mode).
"""

from __future__ import annotations
import tkinter
from typing import Optional
from config import CHIP_STYLES
from rules import breakdown_chips
from pixel_ui import get_element_font


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
            font=get_element_font("chip_bet_badge", scale=scale * (0.85 if compact else 0.95)),
            tags=("betting_spot", tag_prefix),
        )
    )
    return items

