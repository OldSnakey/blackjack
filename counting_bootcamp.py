"""
MIT Hi-Lo Card Counting Bootcamp View & Controller (`counting_bootcamp.py`).

Architecture (MVC):
- **Model (`bootcamp_domain.py`, re-exported here)**:
  `BootcampCurriculumDAG`, `BootcampDrillSession`, `BootcampNodeSpec`,
  `BootcampLectureSlide`, `BootcampPrompt`, and `BOOTCAMP_GRADE_CHIP_STYLES`.
- **View (`BootcampCanvasRenderer` + `BootcampControlDock`)**:
  Stateless 2.5D tabletop baize renderer (`row=3`) and mahogany control dock (`row=4`).
  Owns `tkinter.Canvas` drawing primitives, GC-safe `PhotoImage` references, and
  geometric hit-box registries without mutating `SaveManager` or Controller state.
- **Controller (`CountingBootcampFrame`)**:
  Orchestrates sub-view transitions (`teacher_intro`, `map`, `lecture`, `challenge`,
  `report_card`), drill session lifecycle, `.after()` timers, root keyboard/mouse
  routing, and `BlackjackApp` / `SaveManager` / `DealerActor` coaching integration.
"""

from __future__ import annotations

import math
import time
import tkinter
from typing import Any, Callable, Dict, List, Optional, Tuple

from bootcamp_domain import (
    BOOTCAMP_GRADE_CHIP_STYLES,
    STAGE_FIXED_CHOICES,
    BootcampCurriculumDAG,
    BootcampDrillSession,
    BootcampLectureSlide,
    BootcampNodeSpec,
    BootcampPrompt,
)
from config import TABLE_BACKGROUND_COLOR
from pixel_ui import (
    CanvasPixelButton,
    CanvasPixelPanel,
    get_badge_font,
    get_body_font,
    get_button_font,
    get_display_font,
    get_header_font,
    get_pixel_font as _raw_get_pixel_font,
    get_title_font,
)
from save_manager import BootcampProgress
from ui_canvases import MahoganyRailCanvas
from ui_chip_renderer import draw_single_25d_chip


def get_pixel_font(size_px: int = 14, bold: bool = False) -> Tuple[str, int, str]:
    return _raw_get_pixel_font(size_px=size_px, weight="bold" if bold else "normal")


# ============================================================================
# View Component 1: Bottom Mahogany Armrest Control Dock (row=4)
# ============================================================================

class BootcampControlDock(MahoganyRailCanvas):
    """
    Dedicated `row=4` mahogany armrest control dock for the Counting Bootcamp.
    Subclasses `MahoganyRailCanvas` (`tkinter.Canvas`) so `CanvasPixelButton` widgets
    render directly onto the wood rail with full hover/press state-healing.
    """

    def __init__(self, master: tkinter.Widget, height: int = 70, **kwargs: Any) -> None:
        super().__init__(master, width=880, height=height, background="#140a05", **kwargs)
        self.buttons: List[CanvasPixelButton] = []

    def clear_controls(self) -> None:
        for btn in self.buttons:
            try:
                self.delete(btn.tag)
            except Exception:
                pass
        self.buttons.clear()
        self.delete("dock_fg")

    def set_buttons(
        self,
        specs: List[Dict[str, Any]],
        status_left: str = "",
        status_right: str = "",
    ) -> None:
        """
        Renders a horizontal row of `CanvasPixelButton` items centered on the 880x70 mahogany rail.
        Automatically suppresses side status labels when button span leaves < 115px margin per side,
        guaranteeing zero button-over-text collisions and zero right-edge clipping.
        """
        self.clear_controls()
        self._draw_rail()
        w = 880
        h = self.rail_height

        if not specs:
            return

        spacing = 10 if len(specs) >= 5 else 12
        btn_h = 44
        widths = [int(sp.get("width", 160)) for sp in specs]
        total_w = sum(widths) + spacing * max(0, len(specs) - 1)
        cur_x = (w - total_w) // 2
        cy = h // 2
        side_margin = (w - total_w) // 2

        if status_left and side_margin >= 115:
            self.create_text(
                17, cy + 1,
                text=status_left,
                anchor="w",
                fill="#090503",
                font=get_header_font(16),
                tags="dock_fg",
            )
            self.create_text(
                16, cy,
                text=status_left,
                anchor="w",
                fill="#ffd700",
                font=get_header_font(16),
                tags="dock_fg",
            )
        if status_right and side_margin >= 165:
            self.create_text(
                w - 15, cy + 1,
                text=status_right,
                anchor="e",
                fill="#090503",
                font=get_body_font(16),
                tags="dock_fg",
            )
            self.create_text(
                w - 16, cy,
                text=status_right,
                anchor="e",
                fill="#cfd8dc",
                font=get_body_font(16),
                tags="dock_fg",
            )

        for sp, bw in zip(specs, widths):
            cx = cur_x + bw // 2
            theme = str(sp.get("theme", "green"))
            txt_col = str(sp.get("text_color", "#ffffff" if theme != "gold" else "#fffdf5"))
            btn = CanvasPixelButton(
                self,
                x=cx,
                y=cy,
                width=bw,
                height=btn_h,
                text=str(sp.get("text", "Action")),
                command=sp.get("command"),
                theme=theme,
                font=get_button_font(16),
                text_color=txt_col,
                scale=2,
                enabled=bool(sp.get("enabled", True)),
                group_tag="dock_fg",
            )
            self.buttons.append(btn)
            cur_x += bw + spacing


# ============================================================================
# View Component 2: Stateless 2.5D Tabletop Canvas Renderer (row=3)
# ============================================================================

class BootcampCanvasRenderer:
    """
    Stateless 2.5D Tabletop Canvas View Renderer for the Counting Bootcamp.
    Owns the `tkinter.Canvas`, GC-safe `PhotoImage` references (`_card_photo_refs`),
    and hit-box coordinate maps (`node_hit_boxes`, `action_hit_boxes`).
    Never mutates `SaveManager` or Controller state.
    """

    CANVAS_W = 880
    CANVAS_H = 390

    def __init__(
        self,
        canvas: tkinter.Canvas,
        card_lookup_fn: Callable[[str, str], Optional[Any]],
        banner_sync_fn: Optional[Callable[[], None]] = None,
    ) -> None:
        self.canvas = canvas
        self._get_card_image = card_lookup_fn
        self._banner_sync_fn = banner_sync_fn
        self.node_hit_boxes: Dict[str, Tuple[int, int, int, int]] = {}
        self.action_hit_boxes: Dict[str, Tuple[int, int, int, int]] = {}
        self._card_photo_refs: List[Any] = []
        self.last_drawn_card_xs: List[int] = []

    def _make_panel(
        self,
        x: int,
        y: int,
        width: int,
        height: int,
        bg: str = "#1b120c",
        border: str = "#d4af37",
        inner_hi: str = "#3d271d",
        inner_sh: str = "#0e0805",
        rivet_color: Optional[str] = "#ffd700",
        scale: int = 2,
        recessed: bool = False,
        anchor: str = "nw",
    ) -> CanvasPixelPanel:
        """Creates a 2.5D `CanvasPixelPanel` and retains a strong reference in `_card_photo_refs`."""
        panel = CanvasPixelPanel(
            self.canvas,
            x=x,
            y=y,
            width=width,
            height=height,
            bg=bg,
            border=border,
            inner_hi=inner_hi,
            inner_sh=inner_sh,
            rivet_color=rivet_color,
            scale=scale,
            recessed=recessed,
            anchor=anchor,
        )
        self._card_photo_refs.append(panel)
        return panel

    def _draw_shadow_text(
        self,
        x: int,
        y: int,
        text: str,
        font: Tuple[str, int, str],
        fill: str = "#ffffff",
        shadow: str = "#07120b",
        anchor: str = "center",
        justify: str = "left",
        width: int = 0,
    ) -> int:
        """Draws crisp pixel text with a 1px drop shadow for contrast over baize and mahogany."""
        kw: Dict[str, Any] = {"text": text, "font": font, "anchor": anchor, "justify": justify}
        if width > 0:
            kw["width"] = width
        self.canvas.create_text(x + 1, y + 1, fill=shadow, **kw)
        return self.canvas.create_text(x, y, fill=fill, **kw)

    def _draw_grade_medallion(
        self,
        x: int,
        y: int,
        grade: str,
        scale: float = 1.0,
        compact: bool = False,
    ) -> List[int]:
        """
        Renders a high-fidelity 2.5D Casino Chip Medallion with drop shadow, 3D ribbed cylinder wall,
        8 radial casino edge-spot inserts, recessed inner bezel, stitched inlay, and embossed letter grade.
        """
        style = BOOTCAMP_GRADE_CHIP_STYLES.get(grade, BOOTCAMP_GRADE_CHIP_STYLES["C"])
        tags = ("grade_medallion", f"grade_medallion_{grade}")
        items: List[int] = []

        if compact:
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

        # 1. 2.5D Drop Shadow on table/plaque surface
        items.append(
            self.canvas.create_oval(
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
            self.canvas.create_oval(
                x - rx,
                y - ry + depth,
                x + rx,
                y + ry + depth,
                fill=style["rim"],
                outline="#080808",
                width=2 if not compact else 1,
                tags=tags,
            )
        )
        items.append(
            self.canvas.create_rectangle(
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
            self.canvas.create_line(
                x - rx, y, x - rx, y + depth, fill="#080808", width=1, tags=tags
            )
        )
        items.append(
            self.canvas.create_line(
                x + rx, y, x + rx, y + depth, fill="#080808", width=1, tags=tags
            )
        )

        # 3. Visible 3D Cylinder Wall Vertical Edge Stripes along the front lower arc
        for fx in (-0.80, -0.42, 0.0, 0.42, 0.80):
            sx = x + int(fx * rx)
            arc_y = y + int(ry * math.sqrt(max(0.0, 1.0 - fx * fx)))
            items.append(
                self.canvas.create_line(
                    sx,
                    arc_y - 1,
                    sx,
                    arc_y + depth,
                    fill=style["stripe"],
                    width=stripe_w,
                    tags=tags,
                )
            )

        if not compact:
            # Mid-cylinder stacked medallion groove on large trophy chip
            items.append(
                self.canvas.create_arc(
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
        outer_border = "#ffd700" if grade in ("S", "A", "B") else "#cfd8dc"
        items.append(
            self.canvas.create_oval(
                x - rx,
                y - ry,
                x + rx,
                y + ry,
                fill=style["bg"],
                outline=outer_border,
                width=2 if not compact else 1,
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
                self.canvas.create_polygon(
                    *pts,
                    fill=style["stripe"],
                    outline=style["rim"],
                    width=1,
                    tags=tags,
                )
            )

        # 6. Recessed Inner Medallion Center Disc & Stitched Casino Inlay Ring
        irx, iry = max(12, int(rx * 0.66)), max(7, int(ry * 0.66))
        items.append(
            self.canvas.create_oval(
                x - irx,
                y - iry,
                x + irx,
                y + iry,
                fill=style["bg"],
                outline=style["stripe"],
                width=2 if not compact else 1,
                tags=tags,
            )
        )
        drx, dry = max(9, int(rx * 0.54)), max(5, int(ry * 0.54))
        if not compact:
            items.append(
                self.canvas.create_oval(
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
        sh_off = 1 if compact else 2
        shadow_col = "#ffffff" if style["fg"] == "#111111" else "#090503"
        items.append(
            self.canvas.create_text(
                x + sh_off,
                y + sh_off,
                text=grade,
                fill=shadow_col,
                font=face_font,
                tags=tags,
            )
        )
        items.append(
            self.canvas.create_text(
                x,
                y,
                text=grade,
                fill=style["fg"],
                font=face_font,
                tags=tags,
            )
        )
        return items

    def _draw_card_sprite(self, cx: int, cy: int, rank: str, suit: str) -> None:
        """Draws a card face sprite (or high-contrast fallback plaque) centered at `(cx, cy)`."""
        self.last_drawn_card_xs.append(cx)
        img = self._get_card_image(rank, suit)
        if img is not None:
            self._card_photo_refs.append(img)
            self.canvas.create_image(cx, cy, image=img)
        else:
            self.canvas.create_rectangle(cx - 37, cy - 53, cx + 37, cy + 53, fill="#ffffff", outline="#d4af37", width=2)
            self.canvas.create_text(cx, cy, text=rank.upper(), fill="#111111", font=get_header_font(18))

    def _draw_felt_backdrop(self, title: str, subtitle: str = "", right_reserved_px: int = 0) -> None:
        """Draws the 880x390 emerald baize tabletop border, stitched gold inner trim, and 2.5D top header plaque."""
        self.canvas.delete("all")
        self.node_hit_boxes.clear()
        self.action_hit_boxes.clear()
        self._card_photo_refs.clear()
        self.last_drawn_card_xs.clear()
        if self._banner_sync_fn is not None:
            self._banner_sync_fn()

        w = self.CANVAS_W
        h = self.CANVAS_H
        self.canvas.create_rectangle(3, 3, w - 3, h - 3, fill="#0b3820", outline="#d4af37", width=2)
        self.canvas.create_rectangle(9, 9, w - 9, h - 9, fill="#0f4728", outline="#1e6b40", width=1, dash=(4, 4))

        self._make_panel(
            x=14, y=14, width=w - 28, height=40,
            bg="#102419", border="#d4af37", inner_hi="#214732", inner_sh="#07120c",
            rivet_color="#ffd700", scale=2,
        )
        self._draw_shadow_text(
            28, 34,
            text=title,
            anchor="w",
            fill="#ffd700",
            font=get_header_font(18),
        )
        if subtitle:
            sub_x = w - 28 - right_reserved_px
            self._draw_shadow_text(
                sub_x, 34,
                text=subtitle,
                anchor="e",
                fill="#e0f2f1",
                font=get_body_font(18),
            )

    def draw_teacher_intro(self) -> None:
        """Renders the first-time MIT Coach welcome dossier and 3 demonstration cards."""
        self._draw_felt_backdrop(
            "🎓 MIT HI-LO CARD COUNTING ACADEMY",
            "Interactive Show & Tell Coaching + Graded Tabletop Drills",
        )
        self._make_panel(
            x=60, y=64, width=760, height=312,
            bg="#1b120c", border="#d4af37", inner_hi="#422a1d", inner_sh="#0c0704",
            rivet_color="#ffd700", scale=2,
        )
        self._draw_shadow_text(
            440, 94,
            text="MASTER THE MIT HI-LO SYSTEM IN 5 TIERS",
            fill="#ffd700",
            shadow="#090503",
            font=get_header_font(20),
        )
        self._draw_shadow_text(
            440, 130,
            text="Your Dealer is your live MIT Coach. Every tier pairs an interactive Show & Tell Lecture\n"
                 "with a rapid-fire Challenge Drill graded with 2.5D Casino Chip Medallions (S / A / B / C / F).",
            fill="#f0f4f8",
            shadow="#090503",
            justify="center",
            font=get_body_font(18),
        )

        sample_cards = [
            ("5", "hearts", "+1 LOW (2–6)", "#00e676", "#0d2b1a"),
            ("8", "spades", "0 NEUTRAL (7–9)", "#e0f2f1", "#1a2830"),
            ("ace", "spades", "-1 HIGH (10–A)", "#ff6b6b", "#331414"),
        ]
        for idx, (rk, st, lbl, col, pill_bg) in enumerate(sample_cards):
            cx = 250 + idx * 190
            cy = 216
            self._draw_card_sprite(cx, cy, rk, st)
            self.canvas.create_rectangle(cx - 68, cy + 58, cx + 68, cy + 84, fill=pill_bg, outline=col, width=2)
            self._draw_shadow_text(cx, cy + 71, text=lbl, fill=col, font=get_header_font(16))

        self._draw_shadow_text(
            440, 350,
            text="Press [1] or [Enter] to start the Counting Bootcamp   |   Press [2] or [Esc] for 3-Seat Free Play",
            fill="#80cbc4",
            shadow="#090503",
            font=get_body_font(18),
        )

    def draw_dag_map(self, dag: BootcampCurriculumDAG, bp: BootcampProgress, focused_node_id: str) -> None:
        """Renders the 14-node 2.5D Tabletop Curriculum Map across 5 tier columns (`w = 880`)."""
        passed_count = sum(1 for s in bp.stages.values() if s.passed)
        lect_count = sum(1 for l in bp.lectures.values() if l.completed)
        grad_badge = (
            "🏆 MIT GRADUATE"
            if bp.graduated
            else f"Passed: {passed_count}/7  |  Lectures: {lect_count}/7  |  Best Acc: {bp.overall_best_accuracy_pct:.0f}%"
        )

        self._draw_felt_backdrop("🗺 MIT HI-LO CURRICULUM MAP", grad_badge, right_reserved_px=150)

        fp_box = (722, 18, 858, 50)
        self.action_hit_boxes["free_play"] = fp_box
        self.canvas.create_rectangle(*fp_box, fill="#1b432c", outline="#ffd700", width=2)
        self._draw_shadow_text(790, 34, text="🃏 Free Play [Esc]", fill="#ffd700", font=get_header_font(16))

        col_xs = [96, 268, 440, 612, 784]
        tier_headers = [
            "TIER 1: BASICS",
            "TIER 2: FORK A/B",
            "TIER 3: TABLE/FLIP",
            "TIER 4: TRUE COUNT",
            "TIER 5: MIT SPREAD",
        ]
        for cx, h_txt in zip(col_xs, tier_headers):
            self.canvas.create_rectangle(cx - 78, 60, cx + 78, 82, fill="#0c2617", outline="#2e6b47", width=1)
            self._draw_shadow_text(cx, 71, text=h_txt, fill="#80cbc4", font=get_header_font(15))

        node_centers: Dict[str, Tuple[int, int]] = {}
        row_ys = {
            "center_top": 152,
            "center_bottom": 298,
            "fork_a_top": 124,
            "fork_a_bottom": 194,
            "fork_b_top": 272,
            "fork_b_bottom": 342,
        }
        for spec in dag.get_all_nodes():
            node_centers[spec.node_id] = (col_xs[spec.col_idx], row_ys[spec.row_slot])

        or_cx, or_cy = 564, 225
        or_lit = bp.lectures["L4"].unlocked

        edges = [
            (node_centers["L1"], node_centers["C1"], bp.stages["C1"].unlocked),
            (node_centers["C1"], node_centers["L2A"], bp.lectures["L2A"].unlocked),
            (node_centers["L2A"], node_centers["C2A"], bp.stages["C2A"].unlocked),
            (node_centers["C1"], node_centers["L2B"], bp.lectures["L2B"].unlocked),
            (node_centers["L2B"], node_centers["C2B"], bp.stages["C2B"].unlocked),
            (node_centers["C2A"], node_centers["L3A"], bp.lectures["L3A"].unlocked),
            (node_centers["L3A"], node_centers["C3A"], bp.stages["C3A"].unlocked),
            (node_centers["C2B"], node_centers["L3B"], bp.lectures["L3B"].unlocked),
            (node_centers["L3B"], node_centers["C3B"], bp.stages["C3B"].unlocked),
            (node_centers["C3A"], (or_cx, or_cy), bp.stages["C3A"].passed),
            (node_centers["C3B"], (or_cx, or_cy), bp.stages["C3B"].passed),
            ((or_cx, or_cy), node_centers["L4"], or_lit),
            (node_centers["L4"], node_centers["C4"], bp.stages["C4"].unlocked),
            (node_centers["C4"], node_centers["L5"], bp.lectures["L5"].unlocked),
            (node_centers["L5"], node_centers["C5"], bp.stages["C5"].unlocked),
        ]
        for (x1, y1), (x2, y2), is_lit in edges:
            line_col = "#ffd700" if is_lit else "#2e5e41"
            dash_pat = () if is_lit else (4, 4)
            self.canvas.create_line(x1, y1, x2, y2, fill=line_col, width=3 if is_lit else 2, dash=dash_pat)

        self.canvas.create_oval(
            or_cx - 19, or_cy - 13, or_cx + 19, or_cy + 13,
            fill="#2b170e" if or_lit else "#12241a",
            outline="#ffd700" if or_lit else "#607d8b",
            width=2,
        )
        self._draw_shadow_text(
            or_cx, or_cy,
            text="OR",
            fill="#ffd700" if or_lit else "#b0bec5",
            font=get_header_font(15),
        )

        nw, nh = 158, 60
        for spec in dag.get_all_nodes():
            cx, cy = node_centers[spec.node_id]
            x1, y1, x2, y2 = cx - nw // 2, cy - nh // 2, cx + nw // 2, cy + nh // 2
            self.node_hit_boxes[spec.node_id] = (x1, y1, x2, y2)

            is_focused = (spec.node_id == focused_node_id)
            if spec.node_type == "lecture":
                rec_l = bp.lectures[spec.node_id]
                unlocked = rec_l.unlocked
                completed = rec_l.completed
                bg_col = "#142c47" if unlocked else "#162026"
                border_col = "#00e5ff" if is_focused else ("#ffd700" if completed else ("#64b5f6" if unlocked else "#455a64"))
                badge_txt = "✔" if completed else ("OPEN" if unlocked else "LOCK")
                badge_col = "#00e676" if completed else ("#ffd700" if unlocked else "#78909c")

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_col, outline=border_col, width=3 if is_focused else 2)
                self._draw_shadow_text(
                    x1 + 7, y1 + 17,
                    text=spec.title,
                    anchor="w",
                    fill="#ffffff" if unlocked else "#90a4ae",
                    font=get_header_font(15),
                )
                self._draw_shadow_text(
                    x2 - 6, y1 + 17,
                    text=badge_txt,
                    anchor="e",
                    fill=badge_col,
                    font=get_badge_font(15),
                )
                self._draw_shadow_text(
                    x1 + 7, y1 + 42,
                    text=spec.subtitle,
                    anchor="w",
                    fill="#cfd8dc" if unlocked else "#607d8b",
                    font=get_body_font(16),
                )
            else:
                rec_s = bp.stages[spec.node_id]
                unlocked = rec_s.unlocked
                bg_col = "#2b170e" if unlocked else "#182024"
                border_col = "#00e5ff" if is_focused else ("#ffd700" if rec_s.passed else ("#d4af37" if unlocked else "#455a64"))
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=bg_col, outline=border_col, width=3 if is_focused else 2)

                self._draw_shadow_text(
                    x1 + 7, y1 + 15,
                    text=spec.title,
                    anchor="w",
                    fill="#ffd700" if unlocked else "#90a4ae",
                    font=get_header_font(15),
                )
                sub_str = f"Best: {rec_s.best_accuracy_pct:.0f}% ({rec_s.best_grade})" if rec_s.best_grade else spec.subtitle
                self._draw_shadow_text(
                    x1 + 7, y1 + 43,
                    text=sub_str,
                    anchor="w",
                    fill="#f0f4f8" if unlocked else "#607d8b",
                    font=get_body_font(16),
                )

                if rec_s.best_grade and rec_s.best_grade in BOOTCAMP_GRADE_CHIP_STYLES:
                    self._draw_grade_medallion(
                        x=x2 - 24,
                        y=y1 + 34,
                        grade=rec_s.best_grade,
                        scale=1.0,
                        compact=True,
                    )
                else:
                    lock_txt = "DRILL" if unlocked else "LOCK"
                    self._draw_shadow_text(
                        x2 - 6, y1 + 17,
                        text=lock_txt,
                        anchor="e",
                        fill="#ffb300" if unlocked else "#78909c",
                        font=get_badge_font(15),
                    )

    def draw_lecture_slide(
        self,
        slide: BootcampLectureSlide,
        spec: BootcampNodeSpec,
        slide_idx: int,
        total_slides: int,
        practice_answered: Optional[bool],
        practice_feedback_text: str,
    ) -> None:
        """Renders an interactive Show & Tell lecture slide on the green baize felt without mutating state."""
        self._draw_felt_backdrop(
            f"📖 {slide.title}",
            f"Slide {slide_idx + 1} of {total_slides}  |  Paired: {spec.paired_id}",
            right_reserved_px=152,
        )
        ab_box = (722, 18, 858, 50)
        self.action_hit_boxes["abandon_stage"] = ab_box
        self.canvas.create_rectangle(*ab_box, fill="#1b432c", outline="#ffd700", width=2)
        self._draw_shadow_text(790, 34, text="🗺 Map [Esc]", fill="#ffd700", font=get_header_font(16))

        if slide.formula_banner:
            self._make_panel(
                x=44, y=62, width=792, height=42,
                bg="#1b120c", border="#d4af37", inner_hi="#3d271d", inner_sh="#0c0704",
                rivet_color="#ffd700", scale=2,
            )
            self._draw_shadow_text(
                440, 83,
                text=slide.formula_banner,
                fill="#ffd700",
                shadow="#090503",
                font=get_header_font(18),
            )

        cards = slide.cards
        if cards:
            card_groups = getattr(slide, "card_groups", ())
            if card_groups:
                self._draw_lecture_card_groups(cards, card_groups)
            else:
                spacing = min(160, 680 // max(1, len(cards)))
                start_x = 440 - ((len(cards) - 1) * spacing) // 2
                cy = 180
                for idx, (rk, st, badge_txt) in enumerate(cards):
                    cx = start_x + idx * spacing
                    self._draw_card_sprite(cx, cy, rk, st)
                    badge_col = "#00e676" if "+" in badge_txt else ("#ff6b6b" if "-" in badge_txt else "#ffd700")
                    pill_bg = "#0d2b1a" if "+" in badge_txt else ("#331414" if "-" in badge_txt else "#1c2826")
                    self.canvas.create_rectangle(cx - 56, cy + 58, cx + 56, cy + 84, fill=pill_bg, outline=badge_col, width=2)
                    self._draw_shadow_text(cx, cy + 71, text=badge_txt, fill=badge_col, font=get_header_font(16))

        self._make_panel(
            x=36, y=276, width=808, height=98,
            bg="#0c2617", border="#d4af37", inner_hi="#1f4d30", inner_sh="#06140b",
            rivet_color="#d4af37", scale=2,
        )
        caption_y = 308 if slide.practice_question else 325
        self._draw_shadow_text(
            440, caption_y,
            text=slide.caption,
            fill="#f0f4f8",
            justify="center",
            width=760,
            font=get_body_font(20),
        )

        if slide.practice_question:
            q_txt = practice_feedback_text or f"PRACTICE CHECK: {slide.practice_question}  (Keys [1]–[{len(slide.practice_choices)}])"
            q_col = "#00e676" if practice_answered is True else ("#ff8a80" if practice_answered is False else "#ffd700")
            self._draw_shadow_text(
                440, 350,
                text=q_txt,
                fill=q_col,
                width=760,
                font=get_header_font(16),
            )

    def _draw_lecture_card_groups(
        self,
        cards: Tuple[Tuple[str, str, str], ...],
        card_groups: Tuple[Tuple[str, Tuple[int, ...]], ...],
    ) -> None:
        """
        Renders lecture cards grouped by seat/hand inside recessed baize seat wells (`seat_group_box`),
        keeping cards from the same hand tightly paired (`c_spacing = 78px`) and distinct seats
        widely separated across the felt (`group_gap = 68px..76px`).
        """
        c_spacing = 78
        box_ws = [max(124, len(g_indices) * c_spacing + 24) for _, g_indices in card_groups]
        group_gap = 68 if len(card_groups) >= 3 else 76
        total_w = sum(box_ws) + group_gap * max(0, len(card_groups) - 1)
        cur_x = 440 - total_w // 2
        cy = 185

        for (g_label, g_indices), box_w in zip(card_groups, box_ws):
            gx = cur_x + box_w // 2
            self.canvas.create_rectangle(
                gx - box_w // 2, 108, gx + box_w // 2, 270,
                fill="#0c3b20", outline="#2e7d32", width=1, dash=(3, 3),
                tags="seat_group_box",
            )
            self._draw_shadow_text(gx, 121, text=g_label, fill="#80cbc4", font=get_header_font(15))
            c_start = gx - ((len(g_indices) - 1) * c_spacing) // 2
            for pos_idx, card_idx in enumerate(g_indices):
                rk, st, badge_txt = cards[card_idx]
                cx = c_start + pos_idx * c_spacing
                self._draw_card_sprite(cx, cy, rk, st)
                badge_col = "#00e676" if "+" in badge_txt else ("#ff6b6b" if "-" in badge_txt else "#ffd700")
                pill_bg = "#0d2b1a" if "+" in badge_txt else ("#331414" if "-" in badge_txt else "#1c2826")
                self.canvas.create_rectangle(
                    cx - 36, 242, cx + 36, 265,
                    fill=pill_bg, outline=badge_col, width=2,
                )
                self._draw_shadow_text(cx, 253, text=badge_txt, fill=badge_col, font=get_header_font(15))
            cur_x += box_w + group_gap

    def draw_challenge_prompt(
        self,
        prompt: BootcampPrompt,
        spec: BootcampNodeSpec,
        streak: int,
        accuracy_pct: float,
        total_prompts: int,
    ) -> None:
        """Renders the active Challenge prompt, stage-specific felt visualization, and bottom quick-key plaque."""
        self._draw_felt_backdrop(
            f"⚡ {spec.title} ({prompt.prompt_index + 1}/{total_prompts})",
            f"Streak: {streak} 🔥 | Acc: {accuracy_pct:.0f}% | Par: {spec.par_ms / 1000.0:.1f}s",
            right_reserved_px=164,
        )
        ab_box = (712, 18, 858, 50)
        self.action_hit_boxes["abandon_stage"] = ab_box
        self.canvas.create_rectangle(*ab_box, fill="#3e1616", outline="#ff5252", width=2)
        self._draw_shadow_text(785, 34, text="✖ Abandon [Esc]", fill="#ffd700", font=get_header_font(16))

        self._make_panel(
            x=36, y=60, width=808, height=58,
            bg="#1b120c", border="#d4af37", inner_hi="#3d271d", inner_sh="#0c0704",
            rivet_color="#ffd700", scale=2,
        )
        self._draw_shadow_text(440, 78, text=prompt.headline, fill="#ffd700", shadow="#090503", font=get_header_font(18))
        self._draw_shadow_text(440, 102, text=prompt.subheadline, fill="#e0f2f1", shadow="#090503", font=get_body_font(18))

        cards = prompt.cards
        if spec.node_id == "C3A" and len(cards) == 5:
            self._draw_c3a_table_sweep_groups(cards)
        elif spec.node_id == "C2A" and len(cards) == 2:
            self._draw_c2a_hand_group(cards)
        elif spec.node_id == "C3B" and len(cards) == 3:
            self._draw_c3b_dealer_runout_group(cards)
        elif spec.node_id == "C4":
            self._draw_c4_shoe_calibration_dashboard(prompt)
        elif spec.node_id == "C5":
            self._draw_c5_pit_boss_telemetry(cards, prompt)
        else:
            self._draw_standard_card_fan(cards)

        self._make_panel(
            x=36, y=286, width=808, height=86,
            bg="#0c2617", border="#2e7d32", inner_hi="#1f4d30", inner_sh="#06140b",
            rivet_color="#d4af37", scale=2,
        )
        choices_preview = "   •   ".join(f"[{i + 1}] {ch}" for i, ch in enumerate(prompt.choices))
        self._draw_shadow_text(
            440, 314,
            text=f"QUICK KEYS:   {choices_preview}",
            fill="#ffd700",
            font=get_header_font(16),
        )
        self._draw_shadow_text(
            440, 346,
            text=f"Press key [1]–[{len(prompt.choices)}] for instant response or click a button on the mahogany rail below  ([Esc] Map)",
            fill="#b2dfdb",
            font=get_body_font(18),
        )

    def _draw_c2a_hand_group(self, cards: Tuple[Tuple[str, str], ...]) -> None:
        gx = 440
        box_w = 180
        self.canvas.create_rectangle(
            gx - box_w // 2, 124, gx + box_w // 2, 274,
            fill="#0c3b20", outline="#2e7d32", width=1, dash=(3, 3),
            tags="seat_group_box",
        )
        self._draw_shadow_text(gx, 138, text="PLAYER HAND", fill="#80cbc4", font=get_header_font(15))
        c_spacing = 78
        c_start = gx - ((len(cards) - 1) * c_spacing) // 2
        for c_idx, (rk, st) in enumerate(cards):
            self._draw_card_sprite(c_start + c_idx * c_spacing, 210, rk, st)

    def _draw_c3a_table_sweep_groups(self, cards: Tuple[Tuple[str, str], ...]) -> None:
        group_specs = [
            ("SEAT 1 HAND", [cards[0], cards[1]], 190),
            ("SEAT 2 HAND", [cards[2], cards[3]], 455),
            ("DEALER UPCARD", [cards[4]], 700),
        ]
        for g_label, g_cards, gx in group_specs:
            box_w = 180 if len(g_cards) == 2 else 118
            self.canvas.create_rectangle(
                gx - box_w // 2, 124, gx + box_w // 2, 274,
                fill="#0c3b20", outline="#2e7d32", width=1, dash=(3, 3),
                tags="seat_group_box",
            )
            self._draw_shadow_text(gx, 138, text=g_label, fill="#80cbc4", font=get_header_font(15))
            c_spacing = 78
            c_start = gx - ((len(g_cards) - 1) * c_spacing) // 2
            for c_idx, (rk, st) in enumerate(g_cards):
                self._draw_card_sprite(c_start + c_idx * c_spacing, 210, rk, st)

    def _draw_c3b_dealer_runout_group(self, cards: Tuple[Tuple[str, str], ...]) -> None:
        gx = 440
        box_w = 264
        self.canvas.create_rectangle(
            gx - box_w // 2, 124, gx + box_w // 2, 274,
            fill="#0c3b20", outline="#2e7d32", width=1, dash=(3, 3),
            tags="seat_group_box",
        )
        self._draw_shadow_text(gx, 138, text="DEALER RUNOUT (UPCARD + HOLE + HIT)", fill="#80cbc4", font=get_header_font(15))
        c_spacing = 78
        c_start = gx - ((len(cards) - 1) * c_spacing) // 2
        for c_idx, (rk, st) in enumerate(cards):
            self._draw_card_sprite(c_start + c_idx * c_spacing, 210, rk, st)

    def _draw_c4_shoe_calibration_dashboard(self, prompt: BootcampPrompt) -> None:
        self._make_panel(
            x=110, y=126, width=660, height=150,
            bg="#102419", border="#d4af37", inner_hi="#214732", inner_sh="#07120c",
            rivet_color="#ffd700", scale=2,
        )
        dealt_decks = max(0.0, 6.0 - prompt.decks_remaining)
        rem_ratio = max(0.0, min(1.0, prompt.decks_remaining / 6.0))
        bar_x1, bar_y1, bar_x2, bar_y2 = 165, 162, 255, 252
        self.canvas.create_rectangle(bar_x1, bar_y1, bar_x2, bar_y2, fill="#08140d", outline="#d4af37", width=2)
        fill_h = int((bar_y2 - bar_y1 - 4) * rem_ratio)
        if fill_h > 0:
            self.canvas.create_rectangle(
                bar_x1 + 2, bar_y2 - 2 - fill_h, bar_x2 - 2, bar_y2 - 2,
                fill="#1e824c", outline="#00e676", width=1,
            )
        for d_tick in range(1, 6):
            ty = bar_y2 - int((bar_y2 - bar_y1) * (d_tick / 6.0))
            self.canvas.create_line(bar_x1, ty, bar_x2, ty, fill="#d4af37", width=1, dash=(2, 2))
        self._draw_shadow_text(210, 146, text="6-DECK SHOE", fill="#ffd700", font=get_header_font(15))
        self._draw_shadow_text(210, 264, text=f"{prompt.decks_remaining:.1f} Decks Left", fill="#80cbc4", font=get_body_font(16))

        rc_col = "#00e676" if prompt.running_count_before >= 0 else "#ff6b6b"
        self._draw_shadow_text(
            320, 160,
            text=f"RUNNING COUNT:  {prompt.running_count_before:+d}",
            anchor="w",
            fill=rc_col,
            font=get_title_font(24),
        )
        self._draw_shadow_text(
            320, 196,
            text=f"SHOE REMAINING:  {prompt.decks_remaining:.1f} / 6.0 Decks   (Discard: {dealt_decks:.1f} Decks)",
            anchor="w",
            fill="#ffffff",
            font=get_header_font(16),
        )
        self._draw_shadow_text(
            320, 230,
            text=f"FORMULA:  True Count = {prompt.running_count_before:+d} ÷ {prompt.decks_remaining:.1f} Decks",
            anchor="w",
            fill="#ffd700",
            font=get_header_font(16),
        )
        self._draw_shadow_text(
            320, 256,
            text="Divide Running Count by Decks Remaining to calibrate your True Count.",
            anchor="w",
            fill="#b2dfdb",
            font=get_body_font(16),
        )

    def _draw_c5_pit_boss_telemetry(self, cards: Tuple[Tuple[str, str], ...], prompt: BootcampPrompt) -> None:
        c_spacing = 115
        c_start = 150
        for idx, (rk, st) in enumerate(cards):
            self._draw_card_sprite(c_start + idx * c_spacing, 200, rk, st)

        self._make_panel(
            x=490, y=130, width=354, height=142,
            bg="#102419", border="#d4af37", inner_hi="#214732", inner_sh="#07120c",
            rivet_color="#ffd700", scale=2,
        )
        self._draw_shadow_text(667, 152, text="SHOE TELEMETRY & UNIT RAMP", fill="#ffd700", font=get_header_font(16))
        rc_col = "#00e676" if prompt.running_count_before >= 0 else "#ff6b6b"
        self._draw_shadow_text(
            667, 182,
            text=f"Running Count: {prompt.running_count_before:+d}   |   Decks Left: {prompt.decks_remaining:.1f}",
            fill=rc_col,
            font=get_header_font(18),
        )
        self._draw_shadow_text(
            667, 214,
            text="MIT Spread:  TC<=+1: 1u ($25)  |  +2: 2u ($50)",
            fill="#e0f2f1",
            font=get_body_font(16),
        )
        self._draw_shadow_text(
            667, 240,
            text="TC +3: 4u ($100)  |  +4: 8u ($200)  |  >=+5: 12u ($300)",
            fill="#ffd700",
            font=get_body_font(16),
        )

    def _draw_standard_card_fan(self, cards: Tuple[Tuple[str, str], ...]) -> None:
        spacing = min(145, 620 // max(1, len(cards)))
        start_x = 440 - ((len(cards) - 1) * spacing) // 2
        for idx, (rk, st) in enumerate(cards):
            self._draw_card_sprite(start_x + idx * spacing, 200, rk, st)

    def draw_challenge_feedback(self, outcome: Dict[str, Any], selected_answer: str) -> None:
        """Draws the 2.5D instant feedback plaque over the bottom strip of the Challenge view."""
        is_ok = outcome["is_correct"]
        self._make_panel(
            x=36, y=286, width=808, height=86,
            bg="#123822" if is_ok else "#3e1616",
            border="#00e676" if is_ok else "#ff5252",
            inner_hi="#256640" if is_ok else "#6e2828",
            inner_sh="#081c10" if is_ok else "#210a0a",
            rivet_color="#ffd700",
            scale=2,
        )
        verdict = (
            "✔ CORRECT!"
            if is_ok
            else f"✖ INCORRECT  (You chose: {selected_answer}   |   Correct: {outcome['correct_answer']})"
        )
        self._draw_shadow_text(
            440, 314,
            text=f"{verdict}   [{outcome['response_ms'] / 1000.0:.2f}s]",
            fill="#00e676" if is_ok else "#ff8a80",
            font=get_header_font(18),
        )
        self._draw_shadow_text(
            440, 346,
            text=outcome["explanation"],
            fill="#ffffff",
            font=get_body_font(18),
        )

    def draw_report_card(self, summary: Dict[str, Any], newly_unlocked: List[str]) -> None:
        """Renders the Pit Boss Evaluation Report Card with a 2.5D mahogany dossier and Grade Medallion."""
        grade = summary["grade"]
        passed = summary["passed"]

        self._draw_felt_backdrop(
            f"📋 PIT BOSS EVALUATION — {summary['title']}",
            "Pass: Grade B (80%+)  |  S-Rank: 100% within Par",
        )
        self._make_panel(
            x=70, y=66, width=740, height=304,
            bg="#1b120c", border="#d4af37", inner_hi="#422a1d", inner_sh="#0c0704",
            rivet_color="#ffd700", scale=2,
        )

        self._draw_shadow_text(
            210, 118,
            text=f"GRADE {grade}",
            fill="#ffd700" if passed else "#ff8a80",
            shadow="#090503",
            font=get_title_font(24),
        )
        self._draw_grade_medallion(
            x=210,
            y=194,
            grade=grade,
            scale=2.2,
        )
        self._draw_shadow_text(
            210, 272,
            text="✔ STAGE PASSED" if passed else "✖ NEEDS 80%+",
            fill="#00e676" if passed else "#ff5252",
            shadow="#090503",
            font=get_header_font(18),
        )
        self._draw_shadow_text(
            210, 304,
            text="Mastery Unlocked!" if passed else "Retry or Read Lecture",
            fill="#b2dfdb",
            shadow="#090503",
            font=get_body_font(18),
        )

        self.canvas.create_line(335, 92, 335, 344, fill="#d4af37", width=2)

        formatted_unlocks = [
            "🎓 Professor Edward (Dealer)" if u == "professor" else u
            for u in newly_unlocked
        ]
        metric_rows = [
            ("Final Accuracy:", f"{summary['correct_count']} / {summary['total_prompts']}  ({summary['accuracy_pct']:.1f}%)", "#00e676" if passed else "#ff8a80"),
            ("Average Speed:", f"{summary['avg_response_ms'] / 1000.0:.2f}s   (Par: {summary['par_ms'] / 1000.0:.1f}s)", "#ffffff"),
            ("Best Streak:", f"{summary['best_streak']} 🔥", "#ffd700"),
            ("Stage Score:", f"{summary['score']:,} pts", "#ffd700"),
            ("Newly Unlocked:", ", ".join(formatted_unlocks) if formatted_unlocks else "All Prerequisites Met", "#80cbc4"),
        ]
        for idx, (lbl_txt, val_txt, val_col) in enumerate(metric_rows):
            ry = 116 + idx * 46
            if idx > 0:
                self.canvas.create_line(365, ry - 23, 765, ry - 23, fill="#2e1d14", width=1)
            self._draw_shadow_text(
                365, ry,
                text=lbl_txt,
                anchor="w",
                fill="#cfd8dc",
                shadow="#090503",
                font=get_header_font(16),
            )
            self._draw_shadow_text(
                765, ry,
                text=val_txt,
                anchor="e",
                fill=val_col,
                shadow="#090503",
                font=get_header_font(18),
            )


# ============================================================================
# Controller Layer: CountingBootcampFrame (row=3 Host Frame & State Controller)
# ============================================================================

class CountingBootcampFrame(tkinter.Frame):
    """
    MVC Controller for the MIT Hi-Lo Counting Bootcamp mounted at `row=3` of `BlackjackApp`
    while `DealerStageCanvas` (`row=1`) remains visible above the horizon rail (`row=2`).
    Delegates all 2.5D baize drawing to `self.renderer` (`BootcampCanvasRenderer`) and
    button rendering to `self.dock` (`BootcampControlDock`).
    """

    CANVAS_W = BootcampCanvasRenderer.CANVAS_W
    CANVAS_H = BootcampCanvasRenderer.CANVAS_H

    def __init__(
        self,
        master: tkinter.Widget,
        app: Any,
        dock: BootcampControlDock,
        **kwargs: Any,
    ) -> None:
        super().__init__(master, background=TABLE_BACKGROUND_COLOR, **kwargs)
        self.app = app
        self.dock = dock
        self.dag = BootcampCurriculumDAG()

        self.current_view: str = "map"  # "teacher_intro" | "map" | "lecture" | "challenge" | "report_card"
        self.focused_node_id: str = "L1"
        self.active_lecture_id: str = "L1"
        self.active_slide_index: int = 0
        self.practice_answered: Optional[bool] = None
        self.practice_feedback_text: str = ""

        self.active_session: Optional[BootcampDrillSession] = None
        self.prompt_started_at: float = 0.0
        self.awaiting_feedback_advance: bool = False
        self.last_outcome: Optional[Dict[str, Any]] = None
        self.last_report_summary: Optional[Dict[str, Any]] = None
        self.last_unlock_result: Optional[Dict[str, Any]] = None

        # Tracked Tkinter .after() timers
        self._stream_timer_id: Optional[str] = None
        self._feedback_timer_id: Optional[str] = None
        self._lecture_anim_timer_id: Optional[str] = None
        self._deal_audio_timer_ids: List[str] = []
        self._hovered_target: Optional[str] = None

        self.canvas = tkinter.Canvas(
            self,
            width=self.CANVAS_W,
            height=self.CANVAS_H,
            background=TABLE_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.renderer = BootcampCanvasRenderer(
            canvas=self.canvas,
            card_lookup_fn=self._get_card_image,
            banner_sync_fn=self._sync_top_academy_banner,
        )

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

    @property
    def _node_hit_boxes(self) -> Dict[str, Tuple[int, int, int, int]]:
        return self.renderer.node_hit_boxes

    @property
    def _action_hit_boxes(self) -> Dict[str, Tuple[int, int, int, int]]:
        return self.renderer.action_hit_boxes

    @property
    def _card_photo_refs(self) -> List[Any]:
        return self.renderer._card_photo_refs

    # ------------------------------------------------------------------
    # Timer & Host Application Bridge Helpers
    # ------------------------------------------------------------------

    def cancel_all_timers(self) -> None:
        """Cancels all pending `.after()` timers owned by the Bootcamp controller."""
        for attr in ("_stream_timer_id", "_feedback_timer_id", "_lecture_anim_timer_id"):
            tid = getattr(self, attr, None)
            if tid is not None:
                try:
                    self.after_cancel(tid)
                except Exception:
                    pass
                setattr(self, attr, None)
        self._cancel_deal_audio_timers()

    def _cancel_deal_audio_timers(self) -> None:
        """Cancels any staggered card-dealing sound effect timers."""
        for tid in list(getattr(self, "_deal_audio_timer_ids", [])):
            try:
                self.after_cancel(tid)
            except Exception:
                pass
        if hasattr(self, "_deal_audio_timer_ids"):
            self._deal_audio_timer_ids.clear()

    def _play_cards_dealt_sfx(self, card_count: int = 1) -> None:
        """
        Plays authentic card dealing sound effects (`sound_manager.play_card_deal`)
        when a card or multi-card spread is dealt onto the Bootcamp tabletop.
        Multi-card spreads stagger additional slide cues via tracked `.after()` timers.
        """
        self._cancel_deal_audio_timers()
        sm = getattr(self.app, "sound_manager", None)
        if sm is None or not hasattr(sm, "play_card_deal"):
            return
        count = max(1, min(int(card_count), 5))
        try:
            sm.play_card_deal()
        except Exception:
            return
        for idx in range(1, count):
            tid = self.after(idx * 65, self._trigger_single_card_deal_sfx)
            self._deal_audio_timer_ids.append(tid)

    def _trigger_single_card_deal_sfx(self) -> None:
        sm = getattr(self.app, "sound_manager", None)
        if sm is not None and hasattr(sm, "play_card_deal"):
            try:
                sm.play_card_deal()
            except Exception:
                pass

    def _dealer_coach_say(self, text: str, gesture: str = "nod", queue_if_busy: bool = False) -> None:
        """Commands the live `DealerActor` on `row=1` to speak in the stage dialogue bubble with typewriter voice and emote."""
        try:
            if hasattr(self.app, "set_dealer_speech"):
                self.app.set_dealer_speech(text, stream=True, queue_if_busy=queue_if_busy)
            elif hasattr(self.app, "dealer_speech_var"):
                self.app.dealer_speech_var.set(text)
            if gesture == "deal" and hasattr(self.app, "_trigger_dealer_deal_gesture"):
                self.app._trigger_dealer_deal_gesture(duration_ms=420)
            elif gesture == "shrug" and hasattr(self.app, "_trigger_dealer_gasp"):
                self.app._trigger_dealer_gasp(duration_ms=700)
            elif hasattr(self.app, "_trigger_dealer_smirk"):
                self.app._trigger_dealer_smirk(duration_ms=700)
        except Exception:
            pass

    def _try_complete_active_speech(self) -> bool:
        """
        If the dealer speech bubble is still mid-typewriter animation, immediately
        completes the full text so the player can read it before advancing to the next slide/prompt.
        Returns True if in-flight speech was completed.
        """
        try:
            if hasattr(self.app, "is_dealer_speaking") and self.app.is_dealer_speaking():
                self.app._complete_typewriter_speech()
                return True
        except Exception:
            pass
        return False

    def _sync_top_academy_banner(self) -> None:
        """Updates the top scoreboard banner (`bankroll_label`) with live Academy telemetry while Bootcamp is active."""
        try:
            if hasattr(self.app, "bankroll_label") and hasattr(self.app, "save_manager"):
                bp = self.app.save_manager.data.bootcamp
                passed_c = sum(1 for s in bp.stages.values() if s.passed)
                lect_c = sum(1 for l in bp.lectures.values() if l.completed)
                badge = "🏆 MIT GRADUATE" if bp.graduated else f"STAGES MASTERED: {passed_c}/7  |  LECTURES: {lect_c}/7"
                self.app.bankroll_label.configure(
                    text=f"🎓 MIT HI-LO ACADEMY   |   {badge}",
                    fg="#ffd700",
                )
        except Exception:
            pass

    def _get_card_image(self, rank: str, suit: str) -> Optional[Any]:
        """Looks up a loaded card face `PhotoImage` from `self.app.all_cards`."""
        rank_norm = str(rank).lower()
        suit_norm = str(suit).lower()
        for c in getattr(self.app, "all_cards", []):
            if str(getattr(c, "rank", "")).lower() == rank_norm and str(getattr(c, "suit", "")).lower() == suit_norm:
                return getattr(c, "image", None)
        for c in getattr(self.app, "all_cards", []):
            if str(getattr(c, "rank", "")).lower() == rank_norm:
                return getattr(c, "image", None)
        return None

    @staticmethod
    def _choice_button_theme(choice_text: str, idx: int = 0) -> str:
        """Assigns semantic high-contrast button themes (`green`, `blue`, `red`, `amber`) to drill choices."""
        low = choice_text.lower()
        if "+1" in low and ("low" in low or low.strip() == "+1"):
            return "green"
        if "0" in low and ("neutral" in low or low.strip() in ("0", "0.0")):
            return "blue"
        if "-1" in low and ("high" in low or low.strip() == "-1"):
            return "red"
        if choice_text.startswith("-"):
            return "red"
        if choice_text.startswith("+"):
            return "green"
        palette_cycle = ("blue", "green", "amber", "red", "neutral")
        return palette_cycle[idx % len(palette_cycle)]

    # ------------------------------------------------------------------
    # Sub-View 1: First-Time Teacher Intro
    # ------------------------------------------------------------------

    def render_teacher_intro_view(self) -> None:
        """Transitions to the first-time MIT Coach welcome dossier."""
        self.cancel_all_timers()
        self.current_view = "teacher_intro"
        self.renderer.draw_teacher_intro()
        self._play_cards_dealt_sfx(3)
        self._dealer_coach_say(
            "Welcome to the MIT Blackjack Team training table! Would you like the guided Hi-Lo Counting Bootcamp first?",
            gesture="nod",
        )
        self.dock.set_buttons(
            [
                {
                    "text": "[1] 🎓 Enter Counting Bootcamp [Enter]",
                    "command": lambda: self.handle_teacher_choice("enter_bootcamp"),
                    "theme": "green",
                    "width": 320,
                },
                {
                    "text": "[2] 🃏 Skip to 3-Seat Free Play [Esc]",
                    "command": lambda: self.handle_teacher_choice("skip_to_free_play"),
                    "theme": "blue",
                    "width": 310,
                },
            ],
        )

    def handle_teacher_choice(self, choice: str) -> None:
        """Handles the player's onboarding choice in `teacher_intro` view."""
        self.app.save_manager.mark_bootcamp_intro_seen(save_now=True)
        if choice == "enter_bootcamp":
            self.render_dag_map_view()
        else:
            self.app.exit_counting_bootcamp_to_free_play()

    # ------------------------------------------------------------------
    # Sub-View 2: 5-Column 2.5D Curriculum DAG Map
    # ------------------------------------------------------------------

    def render_dag_map_view(self) -> None:
        """Transitions to the 14-node 2.5D Tabletop Curriculum Map."""
        self.cancel_all_timers()
        self.current_view = "map"
        bp = self.app.save_manager.data.bootcamp
        self.renderer.draw_dag_map(self.dag, bp, self.focused_node_id)

        focused_spec = self.dag.get_node(self.focused_node_id)
        is_unlocked = (
            bp.lectures[focused_spec.node_id].unlocked
            if focused_spec.node_type == "lecture"
            else bp.stages[focused_spec.node_id].unlocked
        )
        self._dealer_coach_say(
            f"{focused_spec.title}: {focused_spec.subtitle}. "
            + ("Press [Enter] or click Launch below to begin!" if is_unlocked else "Pass the prerequisite Challenge with Grade B (80%+) to unlock!"),
            gesture="nod",
        )

        self.dock.set_buttons(
            [
                {
                    "text": f"▶ Launch {focused_spec.node_id} [Enter]" if is_unlocked else f"🔒 {focused_spec.node_id} Locked",
                    "command": lambda: self.activate_node(focused_spec.node_id),
                    "theme": "green" if is_unlocked else "neutral",
                    "width": 235,
                    "enabled": is_unlocked,
                },
                {
                    "text": f"📖 Lecture ({focused_spec.node_id if focused_spec.node_type == 'lecture' else focused_spec.paired_id})",
                    "command": lambda: self.activate_node(
                        focused_spec.node_id if focused_spec.node_type == "lecture" else focused_spec.paired_id
                    ),
                    "theme": "blue",
                    "width": 215,
                    "enabled": bp.lectures[
                        focused_spec.node_id if focused_spec.node_type == "lecture" else focused_spec.paired_id
                    ].unlocked,
                },
                {
                    "text": "🃏 3-Seat Free Play [Esc]",
                    "command": self.app.exit_counting_bootcamp_to_free_play,
                    "theme": "amber",
                    "width": 245,
                },
            ],
        )

    def activate_node(self, node_id: str) -> bool:
        """Opens a Lecture or Challenge node if unlocked; returns True if launched."""
        bp = self.app.save_manager.data.bootcamp
        spec = self.dag.get_node(node_id)
        self.focused_node_id = node_id
        if spec.node_type == "lecture":
            if not bp.lectures[node_id].unlocked:
                self._dealer_coach_say("That Lecture is still locked! Pass the earlier stage with Grade B (80%+) first.", gesture="shrug")
                return False
            self.render_lecture_view(node_id, slide_index=0)
            return True
        else:
            if not bp.stages[node_id].unlocked:
                self._dealer_coach_say("That Challenge is locked! Complete the earlier tier with Grade B (80%+) first.", gesture="shrug")
                return False
            self.render_challenge_view(node_id)
            return True

    # ------------------------------------------------------------------
    # Sub-View 3: Interactive Show & Tell Lecture (`L1`..`L5`)
    # ------------------------------------------------------------------

    def render_lecture_view(self, lecture_id: str, slide_index: int = 0) -> None:
        """
        Controller state transition to a Lecture slide (`lecture_id`, `slide_index`).
        Resets per-slide practice state, records lecture completion once when entering the
        final slide, and delegates canvas/dock rendering to `_redraw_current_lecture_slide()`.
        """
        self.cancel_all_timers()
        self.current_view = "lecture"
        self.active_lecture_id = lecture_id
        slides = self.dag.get_lecture_slides(lecture_id)
        self.active_slide_index = max(0, min(slide_index, len(slides) - 1))
        self.practice_answered = None
        self.practice_feedback_text = ""

        if self.active_slide_index == len(slides) - 1:
            self.app.save_manager.record_bootcamp_lecture(lecture_id)

        slide = slides[self.active_slide_index]
        self._dealer_coach_say(slide.dealer_line, gesture="nod")
        self._redraw_current_lecture_slide()
        if slide.cards:
            self._play_cards_dealt_sfx(len(slide.cards))

    def _redraw_current_lecture_slide(self) -> None:
        """Pure View/Dock synchronization for the active lecture slide without mutating `SaveManager` or resetting state."""
        slides = self.dag.get_lecture_slides(self.active_lecture_id)
        slide = slides[self.active_slide_index]
        spec = self.dag.get_node(self.active_lecture_id)
        self.renderer.draw_lecture_slide(
            slide=slide,
            spec=spec,
            slide_idx=self.active_slide_index,
            total_slides=len(slides),
            practice_answered=self.practice_answered,
            practice_feedback_text=self.practice_feedback_text,
        )
        self._update_lecture_dock(slide, spec, len(slides))

    def _update_lecture_dock(self, slide: BootcampLectureSlide, spec: BootcampNodeSpec, total_slides: int) -> None:
        if slide.practice_choices and self.practice_answered is not True:
            num_choices = len(slide.practice_choices)
            if num_choices >= 5:
                btn_w, map_w = 130, 148
            elif num_choices == 4:
                btn_w, map_w = 152, 158
            else:
                btn_w, map_w = 180, 165

            btn_specs: List[Dict[str, Any]] = []
            for idx, ch in enumerate(slide.practice_choices):
                lbl = ch.replace(" Units ", "u ").replace(" Unit ", "u ") if num_choices >= 5 else ch
                btn_specs.append(
                    {
                        "text": f"[{idx + 1}] {lbl}",
                        "command": lambda ans=ch: self.submit_lecture_practice(ans),
                        "theme": self._choice_button_theme(ch, idx),
                        "width": btn_w,
                    }
                )
            btn_specs.append(
                {
                    "text": "🗺 Map [Esc]",
                    "command": self.render_dag_map_view,
                    "theme": "neutral",
                    "width": map_w,
                }
            )
            self.dock.set_buttons(btn_specs)
            return

        btn_specs = [
            {
                "text": "◀ Prev Slide",
                "command": lambda: self._on_lecture_nav(-1),
                "theme": "neutral",
                "width": 165,
                "enabled": self.active_slide_index > 0,
            },
        ]
        if self.active_slide_index < total_slides - 1:
            btn_specs.append(
                {
                    "text": "Next Slide ▶ [Space]",
                    "command": lambda: self._on_lecture_nav(1),
                    "theme": "green",
                    "width": 235,
                }
            )
        else:
            btn_specs.append(
                {
                    "text": f"⚡ Start {spec.paired_id} Drill ▶ [Enter]",
                    "command": lambda: self._on_lecture_start_drill(spec.paired_id),
                    "theme": "green",
                    "width": 265,
                }
            )
        btn_specs.append(
            {
                "text": "🗺 Return to Map [Esc]",
                "command": self.render_dag_map_view,
                "theme": "blue",
                "width": 210,
            }
        )
        self.dock.set_buttons(btn_specs)

    def _on_lecture_nav(self, delta: int) -> None:
        """Advances or rewinds a Lecture slide, completing any in-flight dealer speech first."""
        if self._try_complete_active_speech():
            return
        self.render_lecture_view(self.active_lecture_id, self.active_slide_index + delta)

    def _on_lecture_start_drill(self, stage_id: str) -> None:
        """Starts the paired Challenge drill from a Lecture, completing any in-flight dealer speech first."""
        if self._try_complete_active_speech():
            return
        self.render_challenge_view(stage_id)

    def submit_lecture_practice(self, selected: str) -> None:
        """Evaluates the player's practice answer on a Lecture slide and redraws without double-counting telemetry."""
        slides = self.dag.get_lecture_slides(self.active_lecture_id)
        slide = slides[self.active_slide_index]
        if selected == slide.practice_correct:
            self.practice_answered = True
            self.practice_feedback_text = f"✔ {slide.practice_explanation}"
            self._dealer_coach_say(slide.practice_explanation, gesture="nod")
        else:
            self.practice_answered = False
            self.practice_feedback_text = f"✖ Not quite ({selected}). Try again! Hint: {slide.caption}"
            self._dealer_coach_say("Close! Re-check the bucket rule on the felt and try again.", gesture="shrug")
        self._redraw_current_lecture_slide()

    # ------------------------------------------------------------------
    # Sub-View 4: Interactive Challenge Drill (`C1`..`C5`) & Report Card
    # ------------------------------------------------------------------

    def abandon_stage(self) -> None:
        """Abandons the active Challenge or Lecture stage and returns to the Curriculum Map without recording an attempt."""
        self.cancel_all_timers()
        self.active_session = None
        self.awaiting_feedback_advance = False
        self.last_outcome = None
        self.render_dag_map_view()

    def render_challenge_view(self, stage_id: str, seed: Optional[int] = None) -> None:
        """Starts a fresh `BootcampDrillSession` for `stage_id` and renders the first prompt."""
        self.cancel_all_timers()
        self.current_view = "challenge"
        self.focused_node_id = stage_id
        self.active_session = BootcampDrillSession(stage_id=stage_id, dag=self.dag, seed=seed)
        self.awaiting_feedback_advance = False
        self.last_outcome = None
        self._render_current_challenge_prompt()

    def _render_current_challenge_prompt(self) -> None:
        self.cancel_all_timers()
        if self.active_session is None or self.active_session.is_complete():
            self._finish_challenge_session()
            return

        prompt = self.active_session.get_current_prompt()
        assert prompt is not None
        spec = self.active_session.node_spec
        self.prompt_started_at = time.perf_counter()
        self.awaiting_feedback_advance = False

        acc_now = (
            100.0 * self.active_session.correct_count / max(1, prompt.prompt_index)
            if prompt.prompt_index > 0
            else 100.0
        )
        if prompt.dealer_callout:
            self._dealer_coach_say(
                prompt.dealer_callout,
                gesture="deal",
                queue_if_busy=(prompt.prompt_index > 0),
            )

        self.renderer.draw_challenge_prompt(
            prompt=prompt,
            spec=spec,
            streak=self.active_session.streak,
            accuracy_pct=acc_now,
            total_prompts=len(self.active_session.prompts),
        )
        self._play_cards_dealt_sfx(len(prompt.cards) if prompt.cards else 1)

        num_choices = len(prompt.choices)
        if num_choices >= 5:
            btn_w, abandon_w = 130, 148
        elif num_choices == 4:
            btn_w, abandon_w = 152, 158
        else:
            btn_w, abandon_w = 180, 165

        btn_specs: List[Dict[str, Any]] = []
        for idx, ch in enumerate(prompt.choices):
            lbl = ch.replace(" Units ", "u ").replace(" Unit ", "u ") if num_choices >= 5 else ch
            btn_specs.append(
                {
                    "text": f"[{idx + 1}] {lbl}",
                    "command": lambda ans=ch: self.submit_challenge_answer(ans),
                    "theme": self._choice_button_theme(ch, idx),
                    "width": btn_w,
                }
            )
        btn_specs.append(
            {
                "text": "✖ Abandon [Esc]",
                "command": self.abandon_stage,
                "theme": "neutral",
                "width": abandon_w,
            }
        )
        self.dock.set_buttons(btn_specs)

    def submit_challenge_answer(self, selected_answer: str) -> Optional[Dict[str, Any]]:
        """Submits an answer for the active Challenge prompt and renders instant feedback."""
        if self.active_session is None or self.awaiting_feedback_advance:
            return None
        elapsed_ms = (time.perf_counter() - self.prompt_started_at) * 1000.0
        outcome = self.active_session.submit_answer(selected_answer, response_ms=elapsed_ms)
        self.last_outcome = outcome
        self.awaiting_feedback_advance = True

        self.renderer.draw_challenge_feedback(outcome, selected_answer)

        if outcome["is_correct"]:
            self._dealer_coach_say(f"Sharp! {outcome['explanation']}", gesture="nod", queue_if_busy=False)
            rem_ms = (
                self.app.get_remaining_speech_ms(min_read_hold_ms=950)
                if hasattr(self.app, "get_remaining_speech_ms")
                else 1450
            )
            delay_ms = max(1350, int(rem_ms))
            self._last_feedback_delay_ms = delay_ms
            self._feedback_timer_id = self.after(delay_ms, self._advance_after_feedback)
        else:
            self._dealer_coach_say(f"Hold up! {outcome['explanation']}", gesture="shrug", queue_if_busy=False)
            self._last_feedback_delay_ms = 0
            self.dock.set_buttons(
                [
                    {
                        "text": "Next Prompt ▶ [Space / Enter]",
                        "command": self._on_feedback_next_click,
                        "theme": "green",
                        "width": 280,
                    },
                    {
                        "text": "🗺 Return to Map [Esc]",
                        "command": self.abandon_stage,
                        "theme": "blue",
                        "width": 220,
                    },
                ],
            )
        return outcome

    def _on_feedback_next_click(self) -> None:
        """Advances from Challenge feedback, completing any in-flight speech bubble first."""
        if self._try_complete_active_speech():
            return
        self._advance_after_feedback()

    def _advance_after_feedback(self) -> None:
        self.cancel_all_timers()
        self.awaiting_feedback_advance = False
        if self.active_session is not None and not self.active_session.is_complete():
            self._render_current_challenge_prompt()
        else:
            self._finish_challenge_session()

    def _finish_challenge_session(self) -> None:
        if self.active_session is None:
            return
        summary = self.active_session.build_summary()
        unlock_res = self.app.save_manager.record_bootcamp_stage(
            stage_id=summary["stage_id"],
            grade=summary["grade"],
            accuracy_pct=summary["accuracy_pct"],
            score=summary["score"],
        )
        self.last_report_summary = summary
        self.last_unlock_result = unlock_res
        self.render_report_card_view(summary, unlock_res)

    def render_report_card_view(self, summary: Dict[str, Any], unlock_res: Optional[Dict[str, Any]] = None) -> None:
        """Transitions to the Pit Boss Evaluation Report Card."""
        self.cancel_all_timers()
        self.current_view = "report_card"
        grade = summary["grade"]
        passed = summary["passed"]
        newly_unlocked = (unlock_res or {}).get("newly_unlocked", [])

        if passed:
            unlock_msg = f" Unlocked: {', '.join(newly_unlocked)}!" if newly_unlocked else ""
            self._dealer_coach_say(
                f"Congratulations! Grade {grade} ({summary['accuracy_pct']:.1f}%).{unlock_msg}",
                gesture="nod",
            )
        else:
            self._dealer_coach_say(
                f"Grade {grade} ({summary['accuracy_pct']:.1f}%). You need 80% (Grade B) to pass — review the Lecture or retry!",
                gesture="shrug",
            )

        self.renderer.draw_report_card(summary, newly_unlocked)
        sm = getattr(self.app, "sound_manager", None)
        if sm is not None:
            try:
                if passed and hasattr(sm, "play_chip_stack"):
                    sm.play_chip_stack()
                elif hasattr(sm, "play_chip_add"):
                    sm.play_chip_add()
            except Exception:
                pass

        stage_id = summary["stage_id"]
        self.dock.set_buttons(
            [
                {
                    "text": f"🔄 Retry {stage_id} [1]",
                    "command": lambda: self.render_challenge_view(stage_id),
                    "theme": "blue",
                    "width": 205,
                },
                {
                    "text": "🗺 Return to Map [Enter]",
                    "command": self.render_dag_map_view,
                    "theme": "green",
                    "width": 250,
                },
                {
                    "text": "🃏 3-Seat Free Play",
                    "command": self.app.exit_counting_bootcamp_to_free_play,
                    "theme": "amber",
                    "width": 215,
                },
            ],
        )

    # ------------------------------------------------------------------
    # Geometric Canvas Click, Motion & Root Keyboard Routing
    # ------------------------------------------------------------------

    def _on_canvas_click(self, event: Any) -> None:
        x, y = int(event.x), int(event.y)
        if self.current_view in ("challenge", "lecture"):
            ab_box = self.renderer.action_hit_boxes.get("abandon_stage")
            if ab_box and ab_box[0] <= x <= ab_box[2] and ab_box[1] <= y <= ab_box[3]:
                self.abandon_stage()
                return
        if self.current_view == "map":
            fp_box = self.renderer.action_hit_boxes.get("free_play")
            if fp_box and fp_box[0] <= x <= fp_box[2] and fp_box[1] <= y <= fp_box[3]:
                self.app.exit_counting_bootcamp_to_free_play()
                return
            for node_id, (x1, y1, x2, y2) in self.renderer.node_hit_boxes.items():
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.focused_node_id = node_id
                    if not self.activate_node(node_id):
                        self.render_dag_map_view()
                    return

    def _on_canvas_motion(self, event: Any) -> None:
        x, y = int(event.x), int(event.y)
        hovered: Optional[str] = None
        if self.current_view in ("challenge", "lecture"):
            ab_box = self.renderer.action_hit_boxes.get("abandon_stage")
            if ab_box and ab_box[0] <= x <= ab_box[2] and ab_box[1] <= y <= ab_box[3]:
                hovered = "abandon_stage"
        elif self.current_view == "map":
            fp_box = self.renderer.action_hit_boxes.get("free_play")
            if fp_box and fp_box[0] <= x <= fp_box[2] and fp_box[1] <= y <= fp_box[3]:
                hovered = "free_play"
            else:
                for node_id, (x1, y1, x2, y2) in self.renderer.node_hit_boxes.items():
                    if x1 <= x <= x2 and y1 <= y <= y2:
                        hovered = node_id
                        break
        if hovered != self._hovered_target:
            self._hovered_target = hovered
            try:
                self.canvas.configure(cursor="hand2" if hovered else "")
            except Exception:
                pass

    def handle_key_event(self, keysym: str) -> bool:
        """
        Routes keyboard shortcuts (`1`–`5`, arrows, `Return`/`KP_Enter`/`space`, `Escape`)
        to the active Bootcamp sub-view. Returns True if handled.
        """
        key = str(keysym)

        if self.current_view == "teacher_intro":
            if key in ("1", "Return", "KP_Enter", "space"):
                self.handle_teacher_choice("enter_bootcamp")
                return True
            if key in ("2", "Escape"):
                self.handle_teacher_choice("skip_to_free_play")
                return True
            return False

        if self.current_view == "map":
            if key == "Escape":
                self.app.exit_counting_bootcamp_to_free_play()
                return True
            if key in ("Return", "KP_Enter", "space"):
                self.activate_node(self.focused_node_id)
                return True
            if key in ("Left", "Right", "Up", "Down"):
                self._move_map_focus(key)
                return True
            return False

        if self.current_view == "lecture":
            if key == "Escape":
                self.render_dag_map_view()
                return True
            slides = self.dag.get_lecture_slides(self.active_lecture_id)
            slide = slides[self.active_slide_index]
            if slide.practice_choices and self.practice_answered is not True and key in ("1", "2", "3", "4", "5"):
                idx = int(key) - 1
                if 0 <= idx < len(slide.practice_choices):
                    self.submit_lecture_practice(slide.practice_choices[idx])
                    return True
            if key in ("Right", "Return", "KP_Enter", "space"):
                if self._try_complete_active_speech():
                    return True
                if self.active_slide_index < len(slides) - 1:
                    self.render_lecture_view(self.active_lecture_id, self.active_slide_index + 1)
                else:
                    spec = self.dag.get_node(self.active_lecture_id)
                    self.render_challenge_view(spec.paired_id)
                return True
            if key == "Left" and self.active_slide_index > 0:
                if self._try_complete_active_speech():
                    return True
                self.render_lecture_view(self.active_lecture_id, self.active_slide_index - 1)
                return True
            return False

        if self.current_view == "challenge":
            if key in ("Escape", "BackSpace", "q", "Q"):
                self.abandon_stage()
                return True
            if self.awaiting_feedback_advance and key in ("Return", "KP_Enter", "space"):
                if self._try_complete_active_speech():
                    return True
                self._advance_after_feedback()
                return True
            if not self.awaiting_feedback_advance and self.active_session is not None and key in ("1", "2", "3", "4", "5"):
                prompt = self.active_session.get_current_prompt()
                idx = int(key) - 1
                if prompt is not None and 0 <= idx < len(prompt.choices):
                    self.submit_challenge_answer(prompt.choices[idx])
                    return True
            return False

        if self.current_view == "report_card":
            if key in ("Escape", "Return", "KP_Enter", "space"):
                self.render_dag_map_view()
                return True
            if key == "1" and self.last_report_summary is not None:
                self.render_challenge_view(self.last_report_summary["stage_id"])
                return True
            return False

        return False

    def _move_map_focus(self, direction: str) -> None:
        all_ids = [n.node_id for n in self.dag.get_all_nodes()]
        if self.focused_node_id not in all_ids:
            self.focused_node_id = "L1"
        idx = all_ids.index(self.focused_node_id)
        if direction in ("Right", "Down"):
            self.focused_node_id = all_ids[(idx + 1) % len(all_ids)]
        else:
            self.focused_node_id = all_ids[(idx - 1) % len(all_ids)]
        self.render_dag_map_view()
