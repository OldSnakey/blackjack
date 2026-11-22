"""
Custom 2.5D Canvas Components and HUD Overlays for Blackjack.

Provides:
- ChipVisualizer: Procedural 2.5D active betting spot & interactive bankroll reserve
  chip piles ($5, $25, $100, $500, $1,000 Platinum) with 3D stacked chips & micro-animations.
- SoulMeterCanvas: 2.5D tug-of-war soul meter for Hell's Table combat.
- TableAnnouncementHUD: Two-tiered result and lore banner with click-to-dismiss.
- HauntedAltarCanvas: 5 candles, 5 rising gravestones, dynamic drop shadows,
  and debris/smoke particles.
- DealerStageCanvas: Panoramic horizon stage with dynamic backdrops, ambient motes,
  sweat drop particles, and speech bubble directional tail.
- TableFeltCanvas: Baize felt canvas with gold rule arcs, noise, vignette,
  and seamless child slice synchronization.
"""

from __future__ import annotations

from collections import OrderedDict
import math
import random
import tkinter
from pathlib import Path
from typing import Any, Callable, Optional

# Optional Pillow support
try:
    from PIL import Image, ImageChops, ImageTk, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except (ImportError, Exception):
    Image = None
    ImageChops = None
    ImageTk = None
    ImageDraw = None
    ImageFont = None
    ImageFilter = None
    PIL_AVAILABLE = False

from config import (
    CHIP_STYLES,
    FONTS_DIR,
    HAUNTED_ASSETS_DIR,
    PANEL_BACKGROUND_COLOR,
    TABLE_BACKGROUND_COLOR,
    hex_to_rgb,
)
from rules import breakdown_chips, breakdown_bankroll_piles
from pixel_ui import (
    get_element_font,
    get_title_font,
    get_header_font,
    get_body_font,
    get_button_font,
    get_badge_font,
    get_display_font,
    get_digital_font,
    get_micro_font,
    CanvasPixelPanel,
    CanvasTextLabelProxy,
)
from ui_layout import (
    get_ui_layout,
    resolve_origin,
    resolve_offset,
    get_seat_origin,
    resolve_pit_bounds,
    resolve_center_pit_lanes,
)

# Parameterized Typography & HUD Constants
HUD_OUTCOME_FONT_FAMILY = "Tiny5 Duo"
HUD_OUTCOME_FONT_SIZE = 32
HUD_OUTCOME_FONT_WEIGHT = "bold"

HUD_LORE_FONT_FAMILY = "Tiny5"
HUD_LORE_FONT_SIZE = 24
HUD_LORE_FONT_SLANT = "normal"
HUD_DEFAULT_WRAPLENGTH = 680


# ============================================================================
# 1. ChipVisualizer
# ============================================================================

class ChipVisualizer(tkinter.Canvas):
    """
    Renders a procedural 2.5D casino felt betting spot with 3D stacked chips,
    an interactive bottom-right bankroll chip reserve tray separated by denomination,
    and non-blocking micro-animations for drops, clears, payouts, sweeps, and pushes.
    """

    def __init__(
        self,
        master,
        width: Optional[int] = None,
        height: Optional[int] = None,
        background=PANEL_BACKGROUND_COLOR,
        on_chip_click: Optional[Callable[[int], None]] = None,
        on_chip_deduct: Optional[Callable[[int], None]] = None,
        on_spot_click: Optional[Any] = None,
        on_spot_clear: Optional[Callable[[], None]] = None,
        on_side_bet_click: Optional[Callable[[str, int], None]] = None,
        on_side_bet_deduct: Optional[Callable[[str, int], None]] = None,
        on_side_bet_clear: Optional[Callable[[str], None]] = None,
        display_profile: Optional[Any] = None,
        **kwargs,
    ):
        cv_cfg = get_ui_layout("chip_visualizer")
        init_scale = float(getattr(display_profile, "art_scale", 1)) if display_profile is not None else 1.0
        base_w = width if width is not None else cv_cfg.get("base_width", 288)
        base_h = height if height is not None else cv_cfg.get("base_height", 204)
        init_w = int(base_w * init_scale) if width is None else int(width)
        init_h = int(base_h * init_scale) if height is None else int(height)
        super().__init__(
            master, width=init_w, height=init_h, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.display_profile = display_profile
        self.scale = init_scale
        self.base_width = base_w
        self.base_height = base_h
        self.canvas_width = init_w
        self.canvas_height = init_h
        self.cx, self.cy = resolve_origin(
            get_ui_layout("chip_visualizer", "betting_spot"), base_w, base_h, content_offset=self._get_content_offset()
        )
        self.rx, self.ry = 54, 20
        self.pp_cx, self.pp_cy = self.cx, self.cy
        self.pp_rx, self.pp_ry = 34, 16
        self.t13_cx, self.t13_cy = self.cx, self.cy
        self.t13_rx, self.t13_ry = 34, 16
        self.current_bet = 0
        self.side_bets: dict[str, int] = {"perfect_pairs": 0, "21_plus_3": 0}
        self.available_bankroll = 1000
        self.interactive_bankroll = True
        self.on_chip_click = on_chip_click
        self.on_chip_deduct = on_chip_deduct
        self.on_spot_click = on_spot_click
        self.on_spot_clear = on_spot_clear
        self.on_side_bet_click = on_side_bet_click
        self.on_side_bet_deduct = on_side_bet_deduct
        self.on_side_bet_clear = on_side_bet_clear
        self._hovered_denom: Optional[int] = None
        self._active_timers: set[str] = set()
        self._felt_slice_photo: Optional[Any] = None
        self._felt_slice_img: Optional[Any] = None
        self._felt_source_img: Optional[Any] = None
        self._felt_coords: Optional[tuple[int, int]] = None

        self._draw_base_spot()
        self.render_bankroll_piles()

    def sync_felt_background(self, felt_img: Optional[Any], rel_x: int, rel_y: int):
        """Draws the underlying felt texture slice as the canvas background item safely with no black borders."""
        if not PIL_AVAILABLE or not felt_img or Image is None or ImageTk is None:
            return
        self._felt_source_img = felt_img
        self._felt_coords = (rel_x, rel_y)
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        try:
            bg_rgb = (7, 76, 26)
            if hasattr(self.master, "THEME_COLORS") and hasattr(self.master, "current_theme"):
                bg_rgb = self.master.THEME_COLORS.get(self.master.current_theme, {}).get("base", bg_rgb)
            slice_img = Image.new("RGB", (w, h), bg_rgb)
            src_x1 = max(0, rel_x)
            src_y1 = max(0, rel_y)
            src_x2 = min(felt_img.width, rel_x + w)
            src_y2 = min(felt_img.height, rel_y + h)
            if src_x2 > src_x1 and src_y2 > src_y1:
                cropped = felt_img.crop((src_x1, src_y1, src_x2, src_y2))
                slice_img.paste(cropped, (src_x1 - rel_x, src_y1 - rel_y))
            self._felt_slice_img = slice_img
            self._felt_slice_photo = ImageTk.PhotoImage(slice_img, master=self)
            if not self.find_withtag("felt_bg"):
                self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
            else:
                self.itemconfigure("felt_bg", image=self._felt_slice_photo)
            self.tag_lower("felt_bg")
        except Exception:
            pass

    def set_display_profile(self, profile: Any) -> None:
        """Applies integer `art_scale` from an active `DisplayProfile`."""
        self.display_profile = profile
        self.set_scale(float(getattr(profile, "art_scale", 1)))

    def set_scale(self, scale: float):
        """Scales visualizer canvas and re-renders base spot proportionally without table overflow."""
        self.scale = scale
        self.canvas_width = int(getattr(self, "base_width", 260) * scale)
        self.canvas_height = int(getattr(self, "base_height", 195) * scale)
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.cx, self.cy = resolve_origin(
            get_ui_layout("chip_visualizer", "betting_spot"), self.canvas_width, self.canvas_height,
            content_offset=self._get_content_offset()
        )
        self.pp_cx, self.pp_cy = resolve_origin(
            get_ui_layout("chip_visualizer", "perfect_pairs_spot"), self.canvas_width, self.canvas_height,
            content_offset=self._get_content_offset()
        )
        self.t13_cx, self.t13_cy = resolve_origin(
            get_ui_layout("chip_visualizer", "twenty_one_plus_three_spot"), self.canvas_width, self.canvas_height,
            content_offset=self._get_content_offset()
        )
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        self._draw_base_spot()
        if self.current_bet > 0:
            self.render_stacks(self.current_bet)
        for b_type in ("perfect_pairs", "21_plus_3"):
            if self.side_bets.get(b_type, 0) > 0:
                self.render_side_bet_stacks(b_type, self.side_bets[b_type])
        self.render_bankroll_piles()

    def _get_content_offset(self) -> tuple[int, int]:
        off = get_ui_layout("chip_visualizer").get("content_offset", {})
        return (off.get("x", 0), off.get("y", 0))

    def _draw_base_spot(self):
        """Draws the felt betting spots: center main bet and flanking side bet spots."""
        self.delete("all")
        w, h = self.canvas_width, self.canvas_height
        sx = w / float(getattr(self, "base_width", 260))
        sy = h / float(getattr(self, "base_height", 140))
        s_font = min(sx, sy)

        # 0. Underlying felt slice background
        if getattr(self, "_felt_slice_photo", None):
            self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")

        content_offset = self._get_content_offset()

        # 1. Left Flanking Spot: Perfect Pairs
        pp_cfg = get_ui_layout("chip_visualizer", "perfect_pairs_spot")
        pp_cx, pp_cy = resolve_origin(pp_cfg, w, h, sx, sy, content_offset=content_offset)
        self.pp_cx, self.pp_cy = pp_cx, pp_cy
        pp_outer = pp_cfg.get("outer_oval", {"rx": 34, "ry": 16})
        pp_rx = int(pp_outer["rx"] * sx)
        pp_ry = int(pp_outer["ry"] * sy)
        self.pp_rx, self.pp_ry = pp_rx, pp_ry
        self.create_oval(
            pp_cx - pp_rx, pp_cy - pp_ry, pp_cx + pp_rx, pp_cy + pp_ry,
            outline="#d4af37", width=max(1, int(1.5 * s_font)), dash=(3, 3), fill="",
            tags=("pp_spot_base", "pp_spot_interactive")
        )
        pp_inner = pp_cfg.get("inner_oval", {"rx": 30, "ry": 13})
        pp_in_rx = int(pp_inner["rx"] * sx)
        pp_in_ry = int(pp_inner["ry"] * sy)
        self.create_oval(
            pp_cx - pp_in_rx, pp_cy - pp_in_ry, pp_cx + pp_in_rx, pp_cy + pp_in_ry,
            outline="#8a6d1b", width=1, dash=(2, 2),
            tags=("pp_spot_ring", "pp_spot_interactive")
        )
        pp_wm = pp_cfg.get("watermark", {"offset_x": 0, "offset_y": 1})
        pp_wm_x, pp_wm_y = resolve_offset(pp_wm, (pp_cx, pp_cy), sx, sy)
        self.create_text(
            pp_wm_x, pp_wm_y, text="PAIRS", fill="#bfa040",
            font=get_element_font("betting_spot_watermark", scale=s_font),
            tags=("pp_watermark", "pp_spot_interactive")
        )
        pp_bdg = pp_cfg.get("bet_badge", {"offset_x": 0, "offset_y": -26})
        pp_bdg_x, pp_bdg_y = resolve_offset(pp_bdg, (pp_cx, pp_cy), sx, sy)
        self.create_text(
            pp_bdg_x, max(int(6 * sy), pp_bdg_y), text="", fill="#ffd700",
            font=get_element_font("chip_bet_badge", scale=s_font), tags=("pp_badge", "pp_spot_interactive")
        )

        # 2. Center Main Betting Spot
        spot_cfg = get_ui_layout("chip_visualizer", "betting_spot")
        cx, cy = resolve_origin(spot_cfg, w, h, sx, sy, content_offset=content_offset)
        self.cx, self.cy = cx, cy
        outer_cfg = spot_cfg.get("outer_oval", {"rx": 54, "ry": 20})
        rx = int(outer_cfg["rx"] * sx)
        ry = int(outer_cfg["ry"] * sy)
        self.rx, self.ry = rx, ry
        self.create_oval(
            cx - rx, cy - ry, cx + rx, cy + ry,
            outline="#d4af37", width=max(1, int(2 * s_font)), dash=(4, 3), fill="", tags=("spot_base", "spot_interactive")
        )
        inner_cfg = spot_cfg.get("inner_oval", {"rx": 49, "ry": 16})
        rx_inner = int(inner_cfg["rx"] * sx)
        ry_inner = int(inner_cfg["ry"] * sy)
        self.create_oval(
            cx - rx_inner, cy - ry_inner, cx + rx_inner, cy + ry_inner,
            outline="#8a6d1b", width=1, dash=(2, 3), tags=("spot_ring", "spot_interactive")
        )
        wm_cfg = spot_cfg.get("watermark", {"offset_x": 0, "offset_y": 1})
        wm_x, wm_y = resolve_offset(wm_cfg, (cx, cy), sx, sy)
        self.create_text(
            wm_x, wm_y, text="MAIN BET", fill="#bfa040",
            font=get_element_font("betting_spot_watermark", scale=s_font), tags=("watermark", "spot_interactive")
        )
        badge_cfg = spot_cfg.get("bet_badge", {"offset_x": 0, "offset_y": -34})
        bet_badge_x, bet_badge_y = resolve_offset(badge_cfg, (cx, cy), sx, sy)
        self.create_text(
            bet_badge_x, max(int(6 * sy), bet_badge_y), text="", fill="#ffd700",
            font=get_element_font("chip_bet_badge", scale=s_font), tags=("badge", "spot_interactive")
        )

        # 3. Right Flanking Spot: 21+3
        t13_cfg = get_ui_layout("chip_visualizer", "twenty_one_plus_three_spot")
        t13_cx, t13_cy = resolve_origin(t13_cfg, w, h, sx, sy, content_offset=content_offset)
        self.t13_cx, self.t13_cy = t13_cx, t13_cy
        t13_outer = t13_cfg.get("outer_oval", {"rx": 34, "ry": 16})
        t13_rx = int(t13_outer["rx"] * sx)
        t13_ry = int(t13_outer["ry"] * sy)
        self.t13_rx, self.t13_ry = t13_rx, t13_ry
        self.create_oval(
            t13_cx - t13_rx, t13_cy - t13_ry, t13_cx + t13_rx, t13_cy + t13_ry,
            outline="#d4af37", width=max(1, int(1.5 * s_font)), dash=(3, 3), fill="",
            tags=("t13_spot_base", "t13_spot_interactive")
        )
        t13_inner = t13_cfg.get("inner_oval", {"rx": 30, "ry": 13})
        t13_in_rx = int(t13_inner["rx"] * sx)
        t13_in_ry = int(t13_inner["ry"] * sy)
        self.create_oval(
            t13_cx - t13_in_rx, t13_cy - t13_in_ry, t13_cx + t13_in_rx, t13_cy + t13_in_ry,
            outline="#8a6d1b", width=1, dash=(2, 2),
            tags=("t13_spot_ring", "t13_spot_interactive")
        )
        t13_wm = t13_cfg.get("watermark", {"offset_x": 0, "offset_y": 1})
        t13_wm_x, t13_wm_y = resolve_offset(t13_wm, (t13_cx, t13_cy), sx, sy)
        self.create_text(
            t13_wm_x, t13_wm_y, text="21+3", fill="#bfa040",
            font=get_element_font("betting_spot_watermark", scale=s_font),
            tags=("t13_watermark", "t13_spot_interactive")
        )
        t13_bdg = t13_cfg.get("bet_badge", {"offset_x": 0, "offset_y": -26})
        t13_bdg_x, t13_bdg_y = resolve_offset(t13_bdg, (t13_cx, t13_cy), sx, sy)
        self.create_text(
            t13_bdg_x, max(int(6 * sy), t13_bdg_y), text="", fill="#ffd700",
            font=get_element_font("chip_bet_badge", scale=s_font), tags=("t13_badge", "t13_spot_interactive")
        )

        # 4. Divider (strictly above reserve chip piles)
        divider_cfg = get_ui_layout("chip_visualizer", "tray_divider")
        tray_top_y = int(h * divider_cfg.get("y_ratio", 0.46)) + int(content_offset[1] * sy)
        margin_div = int(divider_cfg.get("margin_x", 10) * sx)
        self.create_line(
            margin_div, tray_top_y, w - margin_div, tray_top_y,
            fill="#8a6d1b", width=1, dash=(2, 2), tags="tray_divider"
        )
        # 5. Bankroll badge (at bottom)
        bankroll_badge_cfg = get_ui_layout("chip_visualizer", "bankroll_badge")
        eff_bdg_scale = 1.0 if h < int(160 * s_font) else s_font
        badge_font = get_element_font("chip_bankroll_badge", scale=eff_bdg_scale)
        f_sz_bdg = abs(badge_font[1]) if isinstance(badge_font, tuple) and len(badge_font) > 1 else int(10 * s_font)
        bdg_x, bdg_y = resolve_origin(bankroll_badge_cfg, w, h, sx, sy, content_offset=content_offset)
        badge_y = min(h - int(f_sz_bdg / 2) - 1, max(bdg_y, h - int(f_sz_bdg / 2) - 2))
        self.create_text(
            bdg_x, badge_y, text="", fill="#ffd54f",
            font=badge_font, tags="bankroll_badge"
        )

        # Canvas-level full-surface spot hit-dispatch and cursor hover
        self.bind("<Button-1>", lambda e: self._on_canvas_click(e, is_right_click=False))
        self.bind("<Button-3>", lambda e: self._on_canvas_click(e, is_right_click=True))
        self.bind("<Motion>", self._on_canvas_motion)

        # Tag bindings for hover styling
        self.tag_bind("spot_interactive", "<Enter>", lambda e: self.configure(cursor="hand2") if self.interactive_bankroll else None)
        self.tag_bind("spot_interactive", "<Leave>", lambda e: self.configure(cursor=""))
        self.tag_bind("pp_spot_interactive", "<Enter>", lambda e: self.configure(cursor="hand2") if self.interactive_bankroll else None)
        self.tag_bind("pp_spot_interactive", "<Leave>", lambda e: self.configure(cursor=""))
        self.tag_bind("t13_spot_interactive", "<Enter>", lambda e: self.configure(cursor="hand2") if self.interactive_bankroll else None)
        self.tag_bind("t13_spot_interactive", "<Leave>", lambda e: self.configure(cursor=""))

    def set_bankroll(self, available_bankroll: int, interactive: bool = True):
        """Updates the player's available bankroll chip piles in the bottom reserve tray."""
        avail = max(0, int(available_bankroll))
        inter = bool(interactive)
        if getattr(self, "available_bankroll", None) == avail and getattr(self, "interactive_bankroll", None) == inter:
            return
        self.available_bankroll = avail
        self.interactive_bankroll = inter
        if not self.interactive_bankroll:
            self._hovered_denom = None
        self.render_bankroll_piles()

    def trigger_pile_click(self, denom: int):
        """Invokes the chip bet callback when a denomination pile in the bankroll tray is clicked."""
        if self.interactive_bankroll and self.available_bankroll >= denom and callable(self.on_chip_click):
            self.on_chip_click(denom)

    def trigger_pile_deduct(self, denom: int):
        """Invokes chip bet deduction when a denomination pile is right-clicked."""
        if self.interactive_bankroll and callable(self.on_chip_deduct):
            self.on_chip_deduct(denom)

    def trigger_spot_click(self, amount: int = 5):
        """Adds chip amount to staged main bet when left-clicked."""
        if self.interactive_bankroll and callable(self.on_spot_click):
            try:
                self.on_spot_click(amount)
            except TypeError:
                self.on_spot_click()

    def trigger_spot_clear(self):
        """Clears the center staged bet when right-clicked."""
        if not self.interactive_bankroll:
            return
        if callable(self.on_spot_clear):
            self.on_spot_clear()
        elif callable(self.on_spot_click):
            try:
                self.on_spot_click()
            except TypeError:
                pass

    def trigger_side_bet_click(self, bet_type: str, amount: int = 5):
        """Invokes callback when a side bet spot is left-clicked."""
        if self.interactive_bankroll and callable(self.on_side_bet_click):
            self.on_side_bet_click(bet_type, amount)

    def trigger_side_bet_deduct(self, bet_type: str, amount: int = 5):
        """Invokes callback when a side bet spot is right-clicked."""
        if self.interactive_bankroll and callable(self.on_side_bet_deduct):
            self.on_side_bet_deduct(bet_type, amount)

    def trigger_side_bet_clear(self, bet_type: str):
        """Invokes callback when a side bet spot is right-clicked to clear it to $0."""
        if self.interactive_bankroll and callable(self.on_side_bet_clear):
            self.on_side_bet_clear(bet_type)

    def _point_in_spot(
        self,
        px: int,
        py: int,
        cx: int,
        cy: int,
        rx: int,
        ry: int,
        pad_x: float = 1.15,
        pad_y_top: float = 1.6,
        pad_y_bottom: float = 1.15,
    ) -> bool:
        """Determines if (px, py) is within the elliptical boundary of a betting spot with chip stack headroom."""
        if rx <= 0 or ry <= 0:
            return False
        dx = px - cx
        dy = py - cy
        eff_ry = ry * (pad_y_top if dy < 0 else pad_y_bottom)
        eff_rx = rx * pad_x
        return (dx * dx) / (eff_rx * eff_rx) + (dy * dy) / (eff_ry * eff_ry) <= 1.0

    def _on_canvas_click(self, event, is_right_click: bool = False):
        """Unified full-surface click dispatcher across all three betting spots."""
        if not self.interactive_bankroll:
            return None
        x, y = event.x, event.y
        shift = bool(getattr(event, "state", 0) & 0x0001)
        amt = 25 if shift else 5

        # 1. Left Flanking Spot: Perfect Pairs
        if self._point_in_spot(x, y, self.pp_cx, self.pp_cy, self.pp_rx, self.pp_ry):
            if is_right_click:
                self.trigger_side_bet_clear("perfect_pairs")
            else:
                self.trigger_side_bet_click("perfect_pairs", amt)
            return "break"

        # 2. Right Flanking Spot: 21+3
        if self._point_in_spot(x, y, self.t13_cx, self.t13_cy, self.t13_rx, self.t13_ry):
            if is_right_click:
                self.trigger_side_bet_clear("21_plus_3")
            else:
                self.trigger_side_bet_click("21_plus_3", amt)
            return "break"

        # 3. Center Main Betting Spot
        if self._point_in_spot(x, y, self.cx, self.cy, self.rx, self.ry):
            if is_right_click:
                self.trigger_spot_clear()
            else:
                self.trigger_spot_click(amt)
            return "break"

        return None

    def _on_canvas_motion(self, event):
        """Dynamic cursor hover feedback when moving across betting spots."""
        if not self.interactive_bankroll:
            return
        x, y = event.x, event.y
        in_any_spot = (
            self._point_in_spot(x, y, self.pp_cx, self.pp_cy, self.pp_rx, self.pp_ry)
            or self._point_in_spot(x, y, self.t13_cx, self.t13_cy, self.t13_rx, self.t13_ry)
            or self._point_in_spot(x, y, self.cx, self.cy, self.rx, self.ry)
        )
        if in_any_spot:
            try:
                self.configure(cursor="hand2")
            except Exception:
                pass
        elif self._hovered_denom is None:
            try:
                self.configure(cursor="")
            except Exception:
                pass

    def _on_pile_enter(self, _event, denom: int):
        if not self.interactive_bankroll:
            return
        try:
            self.configure(cursor="hand2")
        except Exception:
            pass
        if self._hovered_denom == denom:
            return
        sy = self.canvas_height / float(getattr(self, "base_height", 140))
        lift = max(2, int(3 * sy))
        if self._hovered_denom is not None:
            self.move(f"bank_pile_{self._hovered_denom}", 0, lift)
        self._hovered_denom = denom
        self.move(f"bank_pile_{denom}", 0, -lift)

    def _on_pile_leave(self, _event, denom: int):
        try:
            self.configure(cursor="")
        except Exception:
            pass
        if self._hovered_denom == denom:
            sy = self.canvas_height / float(getattr(self, "base_height", 140))
            lift = max(2, int(3 * sy))
            self.move(f"bank_pile_{denom}", 0, lift)
            self._hovered_denom = None

    def render_bankroll_piles(self):
        """Draws the 5 interactive denomination piles ($5, $25, $100, $500, $1,000) in the bottom reserve tray."""
        self.delete("bankroll_chip")
        w, h = self.canvas_width, self.canvas_height
        sx = w / float(getattr(self, "base_width", 200))
        sy = h / float(getattr(self, "base_height", 140))
        s_font = min(sx, sy)

        avail = getattr(self, "available_bankroll", 0)
        if getattr(self, "interactive_bankroll", False):
            badge_label = "L-CLICK +BET  |  R-CLICK -BET" if avail >= 5 else "OUT OF CHIPS - REBUY TO BET"
        else:
            badge_label = "HAND IN PROGRESS"
        self.itemconfigure("bankroll_badge", text=badge_label)

        piles = breakdown_bankroll_piles(avail)
        denoms = (5, 25, 100, 500, 1000)
        num_cols = len(denoms)

        content_offset = self._get_content_offset()
        piles_cfg = get_ui_layout("chip_visualizer", "bankroll_piles")
        margin_x = int(piles_cfg.get("margin_x", 24) * sx)
        usable_w = max(40, w - 2 * margin_x)
        spacing = usable_w / max(1, num_cols - 1)
        _, base_y = resolve_origin(piles_cfg, w, h, sx, sy, content_offset=content_offset)
        is_compact_h = h < int(160 * s_font)
        if is_compact_h:
            base_y = max(int(h * 0.56), base_y - int(8 * sy))
        eff_lbl_scale = 1.0 if is_compact_h else s_font
        lbl_font = get_element_font("chip_denomination_label", scale=eff_lbl_scale)
        f_sz = abs(lbl_font[1]) if isinstance(lbl_font, tuple) and len(lbl_font) > 1 else int(11 * s_font)
        denom_lbl_cfg = piles_cfg.get("denomination_label", {"offset_x": 0, "offset_y": 20})
        _, lbl_y = resolve_offset(denom_lbl_cfg, (0, base_y), sx, sy)
        if is_compact_h:
            lbl_y = base_y + int(15 * sy)
        step_y = int(piles_cfg.get("chip_vertical_step", 3) * sy)

        for idx, denom in enumerate(denoms):
            col_x = int(margin_x + idx * spacing)
            count = piles.get(denom, 0)
            style = CHIP_STYLES.get(denom, CHIP_STYLES[5])
            pile_tag = f"bank_pile_{denom}"
            combined_tags = ("bankroll_chip", pile_tag)
            short_lbl = "$1K" if denom == 1000 else f"${denom}"

            if count > 0:
                visible_count = min(count, 5)
                for c_idx in range(visible_count):
                    chip_y = base_y - (c_idx * step_y)
                    is_top = (c_idx == visible_count - 1)
                    self._draw_single_chip(
                        col_x, chip_y, denom, style, is_top=is_top,
                        count=count if count > 5 and is_top else None,
                        tags=combined_tags, compact=True
                    )
                lbl_color = "#ffffff" if self.interactive_bankroll else "#b0bec5"
            else:
                rx, ry = int(12 * s_font), int(6 * s_font)
                self.create_oval(
                    col_x - rx, base_y - ry, col_x + rx, base_y + ry,
                    outline="#7d6728", width=1, dash=(2, 2), fill="", tags=combined_tags
                )
                lbl_color = "#8fa89b"

            self.create_text(
                col_x, lbl_y, text=short_lbl, fill=lbl_color,
                font=lbl_font, tags=combined_tags
            )

            hit_tag = f"bank_hit_{denom}"
            rx, ry = int(14 * s_font), int(7 * s_font)
            hitbox_cfg = piles_cfg.get("hitbox", {"pad_x": 4, "top_offset": -18, "bottom_offset": 7})
            pad_x = int(hitbox_cfg.get("pad_x", 4) * sx)
            top_y = base_y + int(hitbox_cfg.get("top_offset", -18) * sy)
            bot_y = lbl_y + int(hitbox_cfg.get("bottom_offset", 7) * sy)
            # Fixed, non-moving hitbox encompassing the whole pile column and label
            self.create_rectangle(
                col_x - rx - pad_x, top_y, col_x + rx + pad_x, bot_y,
                fill="", outline="", tags=("bankroll_chip", hit_tag)
            )

            # Bind clicks deferred by 0ms so Tkinter completes ButtonPress event cycle before bankroll re-renders
            self.tag_bind(hit_tag, "<Button-1>", lambda e, d=denom: self.after(0, lambda: self.trigger_pile_click(d)))
            self.tag_bind(hit_tag, "<Button-3>", lambda e, d=denom: self.after(0, lambda: self.trigger_pile_deduct(d)))
            self.tag_bind(pile_tag, "<Button-1>", lambda e, d=denom: self.after(0, lambda: self.trigger_pile_click(d)))
            self.tag_bind(pile_tag, "<Button-3>", lambda e, d=denom: self.after(0, lambda: self.trigger_pile_deduct(d)))

            # Bind hover events STRICTLY to the fixed hitbox so moving visual chips NEVER causes false Leave/Enter oscillation
            if self.interactive_bankroll and count > 0:
                self.tag_bind(hit_tag, "<Enter>", lambda e, d=denom: self._on_pile_enter(e, d))
                self.tag_bind(hit_tag, "<Leave>", lambda e, d=denom: self._on_pile_leave(e, d))
            else:
                self.tag_bind(hit_tag, "<Enter>", lambda e: None)

        if self._hovered_denom is not None and self.interactive_bankroll:
            lift = max(2, int(3 * sy))
            self.move(f"bank_pile_{self._hovered_denom}", 0, -lift)

    def _is_animation_enabled(self) -> bool:
        """Determines if animations should run (only when window is actively mapped)."""
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except Exception:
            return False

    def _schedule(self, ms: int, callback):
        """Wraps root.after to automatically register and clean up active timer callbacks."""
        timer_id = None
        def wrapper():
            if timer_id in self._active_timers:
                self._active_timers.discard(timer_id)
            if self.winfo_exists():
                callback()

        timer_id = self.after(ms, wrapper)
        self._active_timers.add(timer_id)
        return timer_id

    def _clear_transient_spot_items(self):
        """Removes any in-flight or leftover main-spot chip, payout, or floating text items and restores ring color."""
        self.delete("chip")
        self.delete("anim_chip")
        self.delete("payout_stack")
        self.delete("floating_text")
        self.itemconfigure("spot_base", outline="#d4af37")

    def cancel_animations(self):
        """Alias for clear_timers() used during atomic DisplayProfile transitions."""
        self.clear_timers()

    def clear_timers(self):
        """Cancels all active animation callbacks and cleans up any interrupted transient animation items."""
        for tid in list(self._active_timers):
            try:
                self.after_cancel(tid)
            except Exception:
                pass
        self._active_timers.clear()
        try:
            if not self.winfo_exists():
                return
            self.delete("anim_chip")
            self.delete("payout_stack")
            self.delete("floating_text")
            self.itemconfigure("spot_base", outline="#d4af37")
            if getattr(self, "current_bet", 0) <= 0:
                self.delete("chip")
                self.itemconfigure("badge", text="")
                self.itemconfigure("watermark", state="normal")
            for b_type, badge_tag, wm_tag in (
                ("perfect_pairs", "pp_badge", "pp_watermark"),
                ("21_plus_3", "t13_badge", "t13_watermark"),
            ):
                if self.side_bets.get(b_type, 0) <= 0:
                    self.delete(f"sb_chip_{b_type}")
                    self.delete(f"anim_sb_chip_{b_type}")
                    self.delete(f"floating_sb_{b_type}")
                    self.itemconfigure(badge_tag, text="")
                    self.itemconfigure(wm_tag, state="normal")
        except Exception:
            pass

    def set_bet(self, amount: int, animate: bool = True):
        """Updates the visualized bet amount."""
        self.current_bet = amount
        if amount <= 0:
            self.animate_clear(animated=animate)
        else:
            self.render_stacks(amount)

    def set_side_bet(self, bet_type: str, amount: int, animate: bool = True):
        """Updates the visualized side bet amount ('perfect_pairs' or '21_plus_3')."""
        self.side_bets[bet_type] = max(0, amount)
        self.render_side_bet_stacks(bet_type, self.side_bets[bet_type])

    def clear_side_bets_display(self):
        """Clears all side bet visual stacks and badges."""
        self.side_bets = {"perfect_pairs": 0, "21_plus_3": 0}
        self.delete("sb_chip_perfect_pairs")
        self.delete("sb_chip_21_plus_3")
        self.delete("floating_sb_perfect_pairs")
        self.delete("floating_sb_21_plus_3")
        self.itemconfigure("pp_badge", text="")
        self.itemconfigure("t13_badge", text="")
        self.itemconfigure("pp_watermark", state="normal")
        self.itemconfigure("t13_watermark", state="normal")

    def render_side_bet_stacks(self, bet_type: str, amount: int):
        """Procedurally draws compact 2.5D chip stacks representing the side bet amount."""
        tag = f"sb_chip_{bet_type}"
        badge_tag = "pp_badge" if bet_type == "perfect_pairs" else "t13_badge"
        self.delete(tag)
        self.delete(f"anim_{tag}")

        title = "PAIRS" if bet_type == "perfect_pairs" else "21+3"
        wm_tag = "pp_watermark" if bet_type == "perfect_pairs" else "t13_watermark"
        if amount <= 0:
            self.itemconfigure(badge_tag, text="")
            self.itemconfigure(wm_tag, state="normal")
            return

        self.itemconfigure(wm_tag, state="hidden")
        self.itemconfigure(badge_tag, text=f"{title}: ${amount:,}")

        breakdown = breakdown_chips(amount)
        if not breakdown:
            return

        w, h = self.canvas_width, self.canvas_height
        sx = w / float(getattr(self, "base_width", 260))
        sy = h / float(getattr(self, "base_height", 140))

        spot_cx = getattr(self, "pp_cx", self.cx) if bet_type == "perfect_pairs" else getattr(self, "t13_cx", self.cx)
        spot_cy = getattr(self, "pp_cy", self.cy) if bet_type == "perfect_pairs" else getattr(self, "t13_cy", self.cy)

        num_stacks = len(breakdown)
        spacing = int(18 * sx)
        total_span = (num_stacks - 1) * spacing
        start_x = spot_cx - (total_span // 2)
        base_y = spot_cy + int(6 * sy)

        spot_tag = "pp_spot_interactive" if bet_type == "perfect_pairs" else "t13_spot_interactive"
        for s_idx, (denom, count) in enumerate(breakdown):
            stack_x = start_x + (s_idx * spacing)
            style = CHIP_STYLES.get(denom, CHIP_STYLES[5])
            visible_count = min(count, 5)
            for c_idx in range(visible_count):
                chip_y = base_y - int(c_idx * 3 * sy)
                is_top = (c_idx == visible_count - 1)
                self._draw_single_chip(
                    stack_x, chip_y, denom, style, is_top=is_top,
                    count=count if count > 5 and is_top else None, tags=("side_bet_chip", tag, spot_tag), compact=True
                )

    def animate_side_bet_win(self, bet_type: str, profit: int, label: str = "", animated: bool = True):
        """Animates winning side bet payout text and collects side bet chips."""
        self.side_bets[bet_type] = 0
        tag = f"sb_chip_{bet_type}"
        badge_tag = "pp_badge" if bet_type == "perfect_pairs" else "t13_badge"
        if not animated or not self._is_animation_enabled():
            self.delete(tag)
            self.itemconfigure(badge_tag, text="")
            return
        spot_cx = getattr(self, "pp_cx", self.cx) if bet_type == "perfect_pairs" else getattr(self, "t13_cx", self.cx)
        spot_cy = getattr(self, "pp_cy", self.cy) if bet_type == "perfect_pairs" else getattr(self, "t13_cy", self.cy)
        sy = self.canvas_height / float(getattr(self, "base_height", 140))
        float_tag = f"floating_sb_{bet_type}"
        self.delete(float_tag)
        self.create_text(
            spot_cx, spot_cy - int(18 * sy), text=f"+${profit:,}", fill="#ffd700",
            font=get_element_font("chip_floating_payout"), tags=float_tag
        )
        def float_up(frame=0):
            if frame >= 4:
                self._schedule(600, lambda: self.delete(float_tag))
                self.delete(tag)
                self.itemconfigure(badge_tag, text="")
            else:
                self.move(float_tag, 0, -2)
                self._schedule(20, lambda: float_up(frame + 1))
        float_up()

    def animate_side_bet_loss(self, bet_type: str, animated: bool = True):
        """Animates side bet chips swept away on loss."""
        self.side_bets[bet_type] = 0
        tag = f"sb_chip_{bet_type}"
        badge_tag = "pp_badge" if bet_type == "perfect_pairs" else "t13_badge"
        if not animated or not self._is_animation_enabled():
            self.delete(tag)
            self.itemconfigure(badge_tag, text="")
            return
        def sweep(frame=0):
            if frame >= 4:
                self.delete(tag)
                self.itemconfigure(badge_tag, text="")
            else:
                self.move(tag, 0, -14)
                self._schedule(16, lambda: sweep(frame + 1))
        sweep()

    def render_stacks(self, amount: int):
        """Procedurally draws 2.5D chip stacks representing the specified amount."""
        self.clear_timers()
        self._clear_transient_spot_items()

        if amount <= 0:
            self.itemconfigure("badge", text="")
            self.itemconfigure("watermark", state="normal")
            return

        self.itemconfigure("watermark", state="hidden")
        self.itemconfigure("badge", text=f"BET: ${amount:,}")

        breakdown = breakdown_chips(amount)
        if not breakdown:
            return

        w, h = self.canvas_width, self.canvas_height
        sx = w / float(getattr(self, "base_width", 200))
        sy = h / float(getattr(self, "base_height", 140))

        num_stacks = len(breakdown)
        spacing = int((26 if num_stacks >= 4 else 30) * sx)
        total_span = (num_stacks - 1) * spacing
        start_x = self.cx - (total_span // 2)
        base_y = self.cy + int(8 * sy)

        for s_idx, (denom, count) in enumerate(breakdown):
            stack_x = start_x + (s_idx * spacing)
            style = CHIP_STYLES.get(denom, CHIP_STYLES[5])

            offset_y = 0
            if num_stacks >= 3 and s_idx % 2 == 1:
                offset_y = -int(3 * sy)

            visible_count = min(count, 6)
            for c_idx in range(visible_count):
                chip_y = (base_y + offset_y) - int(c_idx * 3 * sy)
                is_top = (c_idx == visible_count - 1)
                self._draw_single_chip(
                    stack_x, chip_y, denom, style, is_top=is_top,
                    count=count if count > 6 and is_top else None, tags=("chip", "spot_interactive")
                )

    def _draw_single_chip(self, x: int, y: int, denom: int, style: dict, is_top: bool = False, count: int = None, tags="chip", compact: bool = False):
        """Draws one 2.5D chip with rim thickness, edge stripes, top face, and denomination."""
        w, h = self.canvas_width, self.canvas_height
        sx = w / float(getattr(self, "base_width", 200))
        sy = h / float(getattr(self, "base_height", 140))
        s_chip = min(sx, sy)

        chips_cfg = get_ui_layout("chip_visualizer", "chips")
        geom = chips_cfg.get("compact" if compact else "standard", {})
        rx = int(geom.get("rx", 12 if compact else 14) * s_chip)
        ry = int(geom.get("ry", 6 if compact else 7) * s_chip)
        depth = int(geom.get("depth", 3 if compact else 4) * s_chip)
        stripe_x = int(geom.get("stripe_x", 6 if compact else 8) * s_chip)

        # 1. Shadow / bottom rim
        self.create_oval(
            x - rx, y - ry + depth, x + rx, y + ry + depth,
            fill=style["rim"], outline=style["rim"], tags=tags
        )
        self.create_rectangle(
            x - rx, y, x + rx, y + depth,
            fill=style["rim"], outline=style["rim"], tags=tags
        )

        # 2. Edge stripes
        self.create_line(x - stripe_x, y + 1, x - stripe_x, y + depth, fill=style["stripe"], width=max(1, int(2 * s_chip)), tags=tags)
        self.create_line(x + stripe_x, y + 1, x + stripe_x, y + depth, fill=style["stripe"], width=max(1, int(2 * s_chip)), tags=tags)

        # 3. Top face
        self.create_oval(
            x - rx, y - ry, x + rx, y + ry,
            fill=style["bg"], outline="#ffffff", width=1, tags=tags
        )
        # Inner dashed circle (only at >1x chip scale so 1x numerals stay crisp and unobstructed)
        if s_chip > 1.15:
            self.create_oval(
                x - rx + int(3 * s_chip), y - ry + int(2 * s_chip), x + rx - int(3 * s_chip), y + ry - int(2 * s_chip),
                outline=style["fg"], dash=(2, 2), tags=tags
            )

        # 4. Text (denomination or count badge if stack is capped)
        short_denom = "$1K" if denom == 1000 else f"${denom}"
        cap_limit = 5 if compact else 6
        display_text = f"x{count}" if (count and count > cap_limit) else short_denom
        self.create_text(
            x, y, text=display_text, fill=style["fg"],
            font=get_element_font("chip_face_value", scale=s_chip), tags=tags
        )

    def animate_chip_drop(self, added_amount: int, new_total: int, animated: bool = True):
        """Plays a tactile drop-and-bounce animation when a chip is added."""
        self.current_bet = new_total
        self.itemconfigure("badge", text=f"BET: ${new_total:,}")
        self.clear_timers()
        self.delete("anim_chip")
        if new_total <= added_amount:
            self.delete("chip")

        if not animated or not self._is_animation_enabled():
            self.render_stacks(new_total)
            return

        style = CHIP_STYLES.get(added_amount, CHIP_STYLES[5])
        drop_x = self.cx
        sy = self.canvas_height / float(getattr(self, "base_height", 140))
        target_y = self.cy + int(8 * sy)
        start_y = target_y - int(24 * sy)

        drop_tag = "anim_chip"
        self._draw_single_chip(drop_x, start_y, added_amount, style, is_top=True, tags=drop_tag)

        def frame1():
            self.move(drop_tag, 0, 12)
            self._schedule(16, frame2)

        def frame2():
            self.move(drop_tag, 0, 14)
            self._schedule(16, frame3)

        def frame3():
            self.delete(drop_tag)
            self.render_stacks(new_total)

        self._schedule(16, frame1)

    def animate_clear(self, animated: bool = True):
        """Animates chips sliding downwards off the table when main bet is cleared."""
        self.current_bet = 0
        self.clear_timers()
        self.delete("payout_stack")
        self.delete("floating_text")
        self.itemconfigure("spot_base", outline="#d4af37")
        self.itemconfigure("badge", text="")
        if not animated or not self._is_animation_enabled():
            self._clear_transient_spot_items()
            return

        def step(count=0):
            if count >= 4:
                self._clear_transient_spot_items()
            else:
                self.move("chip", 0, 14)
                self.move("anim_chip", 0, 14)
                self._schedule(16, lambda: step(count + 1))

        step()

    def animate_win(self, profit: int, animated: bool = True):
        """Animates dealer payout sliding in from top, glowing +$XX text, and chip collection."""
        self.current_bet = 0
        self.clear_timers()
        payout_tag = "payout_stack"
        text_tag = "floating_text"
        self.delete("anim_chip")
        self.delete(payout_tag)
        self.delete(text_tag)

        if not animated or not self._is_animation_enabled():
            self._clear_transient_spot_items()
            self.itemconfigure("badge", text="")
            return

        breakdown = breakdown_chips(max(profit, 5))
        top_denom = breakdown[0][0] if breakdown else 25
        style = CHIP_STYLES.get(top_denom, CHIP_STYLES[25])

        anim_cfg = get_ui_layout("chip_visualizer", "animations")
        p_off = anim_cfg.get("payout_offset", {"x": 20, "y": -20})
        float_y = anim_cfg.get("floating_text_offset_y", -16)

        for c in range(min(3, len(breakdown))):
            self._draw_single_chip(self.cx + p_off.get("x", 20), p_off.get("y", -20) - (c * 3), top_denom, style, is_top=(c == 2), tags=payout_tag)

        def slide_payout(frame=0):
            if frame >= 5:
                self.create_text(
                    self.cx, self.cy + float_y, text=f"+${profit:,}", fill="#ffd700",
                    font=get_element_font("chip_floating_payout"), tags=text_tag
                )
                self._schedule(20, float_text)
            else:
                self.move(payout_tag, 0, 18)
                self._schedule(18, lambda: slide_payout(frame + 1))

        def float_text(frame=0):
            if frame >= 4:
                self._schedule(400, collect_chips)
            else:
                self.move(text_tag, 0, -3)
                self._schedule(20, lambda: float_text(frame + 1))

        def collect_chips(frame=0):
            if frame >= 5:
                self._clear_transient_spot_items()
                self.itemconfigure("badge", text="")
            else:
                self.move(payout_tag, -12, 16)
                self.move("chip", -12, 16)
                self.move(text_tag, -4, 4)
                self._schedule(18, lambda: collect_chips(frame + 1))

        slide_payout()

    def animate_loss(self, animated: bool = True):
        """Animates dealer sweeping the chips upward toward the dealer tray."""
        self.current_bet = 0
        self.clear_timers()
        text_tag = "floating_text"
        self.delete("payout_stack")
        self.delete(text_tag)
        if not animated or not self._is_animation_enabled():
            self._clear_transient_spot_items()
            self.itemconfigure("badge", text="")
            return

        def sweep_chips(frame=0):
            if frame >= 5:
                self._clear_transient_spot_items()
                self.itemconfigure("badge", text="")
            else:
                self.move("chip", 0, -18)
                self.move("anim_chip", 0, -18)
                self._schedule(18, lambda: sweep_chips(frame + 1))

        sweep_chips()

    def animate_push(self, animated: bool = True):
        """Highlights the betting spot on push and returns chips to player."""
        self.current_bet = 0
        self.clear_timers()
        text_tag = "floating_text"
        self.delete("payout_stack")
        self.delete("anim_chip")
        self.delete(text_tag)
        if not animated or not self._is_animation_enabled():
            self._clear_transient_spot_items()
            self.itemconfigure("badge", text="")
            return

        self.create_text(
            self.cx, self.cy - 16, text="PUSH", fill="#ffffff",
            font=get_element_font("chip_push_banner"), tags=text_tag
        )

        self.itemconfigure("spot_base", outline="#ffffff")

        def reset_ring():
            self.itemconfigure("spot_base", outline="#d4af37")
            self.animate_clear(animated=True)

        self._schedule(450, reset_ring)


# ============================================================================
# 2. SoulMeterCanvas
# ============================================================================

class SoulMeterCanvas(tkinter.Canvas):
    """
    Renders an animated 2.5D Tug-of-War Soul Meter during Hell's Table Mode.
    Visualizes the struggle between the mortal soul (0% Abyss) and celestial freedom (100% Light).
    """

    def __init__(self, master, width=None, height=None, background="#140508", display_profile: Optional[Any] = None, **kwargs):
        cfg = get_ui_layout("soul_meter")
        init_scale = float(getattr(display_profile, "art_scale", 1)) if display_profile is not None else 1.0
        if width is None:
            width = int(cfg.get("base_width", 250) * init_scale)
        if height is None:
            height = int(cfg.get("base_height", 135) * init_scale)
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.display_profile = display_profile
        self.scale = init_scale
        self.canvas_width = width
        self.canvas_height = height
        self.cx = width // 2
        self.cy = height // 2
        self.current_value = 0.25
        self.target_value = 0.25
        self._anim_timer_id = None
        self._felt_bg_photo = None
        self._felt_coords = None
        self._draw_meter()

    def sync_felt_background(self, felt_img: Any, x_off: int = 0, y_off: int = 0) -> None:
        """Slices active table felt behind SoulMeterCanvas so rounded corners show zero rectangular box halo."""
        if not PIL_AVAILABLE or Image is None or ImageTk is None or felt_img is None:
            return
        try:
            self._felt_coords = (int(x_off), int(y_off))
            w, h = max(10, self.canvas_width), max(10, self.canvas_height)
            sx1 = max(0, min(int(x_off), max(0, felt_img.width - w)))
            sy1 = max(0, min(int(y_off), max(0, felt_img.height - h)))
            cropped = felt_img.crop((sx1, sy1, min(felt_img.width, sx1 + w), min(felt_img.height, sy1 + h)))
            if cropped.size != (w, h):
                cropped = cropped.resize((w, h))
            self._felt_bg_photo = ImageTk.PhotoImage(cropped, master=self)
            self.delete("soul_felt_bg")
            self.create_image(0, 0, image=self._felt_bg_photo, anchor="nw", tags="soul_felt_bg")
            self.tag_lower("soul_felt_bg")
        except Exception:
            pass

    def cancel_animations(self) -> None:
        """Cancels any in-flight soul meter step timer."""
        self._cancel_timer()

    def set_display_profile(self, profile: Any) -> None:
        """Applies integer `art_scale` from an active `DisplayProfile`."""
        self.display_profile = profile
        self.set_scale(float(getattr(profile, "art_scale", 1)))

    def set_scale(self, scale: float):
        """Scales soul meter canvas dimensions proportionally."""
        self.scale = scale
        cfg = get_ui_layout("soul_meter")
        bw = int(cfg.get("base_width", 250))
        bh = int(cfg.get("base_height", 135))
        self.canvas_width = int(bw * scale)
        self.canvas_height = int(bh * scale)
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.cx = self.canvas_width // 2
        self.cy = self.canvas_height // 2
        self._draw_meter()

    def set_meter(self, value: float, animated: bool = True):
        """Sets target soul value (0.0 to 1.0) and animates smoothly."""
        self.target_value = max(0.0, min(1.0, value))
        if not animated or not self._is_animation_enabled():
            self.current_value = self.target_value
            self._draw_meter()
            return

        self._cancel_timer()
        self._step_animation()

    def _step_animation(self):
        """Steps towards target_value in non-blocking increments."""
        diff = self.target_value - self.current_value
        if abs(diff) < 0.01:
            self.current_value = self.target_value
            self._draw_meter()
            return

        self.current_value += diff * 0.25
        self._draw_meter()
        self._anim_timer_id = self.after(25, self._step_animation)

    def _draw_meter(self):
        self.delete("all")
        if getattr(self, "_felt_bg_photo", None) is not None:
            self.create_image(0, 0, image=self._felt_bg_photo, anchor="nw", tags="soul_felt_bg")
        cx, cy = self.cx, self.cy
        s = getattr(self, "scale", 1.0)

        # 1. Dark ornate frame with ember trim
        self._draw_rounded_rect(5, 5, self.canvas_width - 5, self.canvas_height - 5, radius=int(8 * s), fill="#0d0204", outline="#8b0000", width=max(1, int(2 * s)))

        sm_cfg = get_ui_layout("soul_meter")
        hdr_cfg = sm_cfg.get("header", {})
        hdr_x, hdr_y = resolve_origin(hdr_cfg, self.canvas_width, self.canvas_height, s, s)

        # 2. Header
        self.create_text(hdr_x, hdr_y, text="☠ SOUL WAGER ☠", fill="#ffd700", font=get_element_font("soul_meter_title", scale=s))

        # 3. Bar dimensions
        bar_cfg = sm_cfg.get("progress_bar", {})
        margin_bar = int(bar_cfg.get("margin_x", 18) * s)
        bx1, by1 = margin_bar, int(bar_cfg.get("top_y", 42) * s)
        bx2, by2 = self.canvas_width - margin_bar, int(bar_cfg.get("bottom_y", 62) * s)
        bar_w = bx2 - bx1

        # Background track
        self.create_rectangle(bx1, by1, bx2, by2, fill="#240004", outline="#4a000a", width=1)

        # Milestones (50% and 75%)
        m50_x = bx1 + int(bar_w * 0.50)
        m75_x = bx1 + int(bar_w * 0.75)
        self.create_line(m50_x, by1 - 3, m50_x, by2 + 3, fill="#80cbc4", width=1, dash=(2, 2))
        self.create_line(m75_x, by1 - 3, m75_x, by2 + 3, fill="#ffd700", width=1, dash=(2, 2))
        m_offset_y = int(bar_cfg.get("milestone_label_offset_y", -12) * s)
        self.create_text(m50_x, by1 + m_offset_y, text="50%", fill="#80cbc4", font=get_element_font("soul_meter_markers", scale=s))
        self.create_text(m75_x, by1 + m_offset_y, text="75%", fill="#ffd700", font=get_element_font("soul_meter_markers", scale=s))

        # Fill segment
        fill_x = bx1 + int(bar_w * self.current_value)
        if fill_x > bx1:
            fill_color = "#ff1744" if self.current_value < 0.35 else ("#ffd700" if self.current_value < 0.70 else "#00e5ff")
            self.create_rectangle(bx1, by1, fill_x, by2, fill=fill_color, outline="")

        # Tug pointer
        ptr_cfg = bar_cfg.get("pointer", {"width": 5, "height": 6})
        p_w = int(ptr_cfg.get("width", 5) * s)
        p_h = int(ptr_cfg.get("height", 6) * s)
        self.create_polygon([fill_x, by1 - 3, fill_x - p_w, by1 - 3 - p_h, fill_x + p_w, by1 - 3 - p_h], fill="#ffffff", outline="#ffd700")

        # 4. Labels
        b_offset_y = int(bar_cfg.get("bound_label_offset_y", 10) * s)
        self.create_text(bx1, by2 + b_offset_y, text="ABYSS 0%", fill="#ff5252", font=get_element_font("soul_meter_bounds", scale=s), anchor="w")
        self.create_text(bx2, by2 + b_offset_y, text="LIGHT 100%", fill="#69f0ae", font=get_element_font("soul_meter_bounds", scale=s), anchor="e")

        # 5. Status Text
        pct = int(self.current_value * 100)
        status_txt = f"{pct}% SOUL ESSENCE"
        status_color = "#ff5252" if pct <= 25 else ("#ffeb3b" if pct < 75 else "#00e5ff")
        stat_cfg = sm_cfg.get("status_text", {})
        stat_x, stat_y = resolve_origin(stat_cfg, self.canvas_width, self.canvas_height, s, s)
        self.create_text(stat_x, stat_y, text=status_txt, fill=status_color, font=get_element_font("soul_meter_status", scale=s))

        # Tip
        hint = "Win to advance • 21 surges"
        hint_cfg = sm_cfg.get("hint_text", {})
        hint_x, hint_y = resolve_origin(hint_cfg, self.canvas_width, self.canvas_height, s, s)
        self.create_text(hint_x, hint_y, text=hint, fill="#cfd8dc", font=get_element_font("soul_meter_hint", scale=s))

    def _draw_rounded_rect(self, x1, y1, x2, y2, radius=8, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2, y1,
                  x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2,
                  x2-radius, y2, x2-radius, y2, x1+radius, y2, x1, y2,
                  x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def _is_animation_enabled(self) -> bool:
        try:
            return bool(self.winfo_exists() and self.winfo_ismapped())
        except Exception:
            return False

    def cancel_animations(self):
        """Cancels active SoulMeter animation timer and snaps to target_value."""
        self._cancel_timer()
        self.current_value = self.target_value
        if self.winfo_exists():
            self._draw_meter()

    def _cancel_timer(self):
        if self._anim_timer_id:
            try:
                self.after_cancel(self._anim_timer_id)
            except Exception:
                pass
            self._anim_timer_id = None


# ============================================================================
# 3. TableAnnouncementHUD
# ============================================================================

class TableAnnouncementHUD(tkinter.Frame):
    """
    Two-tiered Table Announcement HUD displayed prominently on the table felt.
    Eliminates text truncation via parameterized typography, dynamic wraplength,
    and visual hierarchy separating the core round outcome from secondary/lore messages.
    """

    def __init__(
        self,
        master,
        outcome_family: str = HUD_OUTCOME_FONT_FAMILY,
        outcome_size: int = HUD_OUTCOME_FONT_SIZE,
        outcome_weight: str = HUD_OUTCOME_FONT_WEIGHT,
        lore_family: str = HUD_LORE_FONT_FAMILY,
        lore_size: int = HUD_LORE_FONT_SIZE,
        lore_slant: str = HUD_LORE_FONT_SLANT,
        wraplength: int = HUD_DEFAULT_WRAPLENGTH,
        background: str = PANEL_BACKGROUND_COLOR,
        **kwargs
    ):
        super().__init__(master, background=background, **kwargs)
        self.scale = 1.0
        self.display_profile = None
        self._manual_typography_override = (
            outcome_family != HUD_OUTCOME_FONT_FAMILY
            or outcome_size != HUD_OUTCOME_FONT_SIZE
            or outcome_weight != HUD_OUTCOME_FONT_WEIGHT
            or lore_family != HUD_LORE_FONT_FAMILY
            or lore_size != HUD_LORE_FONT_SIZE
        )
        self._tier_short_px = abs(int(outcome_size))
        self._tier_long_px = 24
        self._tier_lore_px = abs(int(lore_size))
        self.outcome_font_family = outcome_family
        self.outcome_font_size = outcome_size
        self.outcome_font_weight = outcome_weight
        self.lore_family = lore_family
        self.lore_font_family = lore_family
        self.lore_font_size = lore_size
        self.lore_font_slant = lore_slant
        self.wraplength = wraplength
        self.payout_ratio: tuple[int, int] = (3, 2)
        self.current_raw_message = ""
        self.insurance_overlay_active: bool = False
        self._dismiss_timer_id: Optional[str] = None

        # Outer felt badge containing procedural brass-riveted plaque canvas
        self.badge = tkinter.Frame(
            self, background=background, bd=0, highlightthickness=0, cursor="hand2"
        )
        self.badge.pack(anchor="center")

        init_w, init_h = 280, 44
        self.badge_canvas = tkinter.Canvas(
            self.badge, width=init_w, height=init_h, bd=0, highlightthickness=0,
            background=background, cursor="hand2"
        )
        self.badge_canvas.pack(fill="both", expand=True)

        self.panel = CanvasPixelPanel(
            self.badge_canvas,
            x=init_w // 2,
            y=init_h // 2,
            width=init_w,
            height=init_h,
            bg="#0c2917",
            border="#06140b",
            inner_hi="#1f4d30",
            inner_sh="#071a0e",
            rivet_color="#d4af37",
            scale=2,
            recessed=True,
            anchor="center",
            tag="announcement_panel",
        )

        # Tier 1: Outcome text item with 1px drop shadow
        out_f = (self.outcome_font_family, -abs(self.outcome_font_size), self.outcome_font_weight)
        self._outcome_sh_id = self.badge_canvas.create_text(
            init_w // 2 + 1, init_h // 2 + 1, text="", font=out_f, fill="#040c06", anchor="center"
        )
        self._outcome_id = self.badge_canvas.create_text(
            init_w // 2, init_h // 2, text="", font=out_f, fill="#f5f5f5", anchor="center"
        )
        self.outcome_label = CanvasTextLabelProxy(
            self.badge_canvas, self._outcome_id, self._outcome_sh_id,
            initial_text="", initial_font=out_f, initial_fg="#f5f5f5", bg="#0c2917",
            wraplength=self.wraplength
        )

        # Tier 2: Thematic Lore / Status text item with 1px drop shadow
        lore_f = (self.lore_font_family, -abs(self.lore_font_size), self.lore_font_slant)
        self._lore_sh_id = self.badge_canvas.create_text(
            init_w // 2 + 1, int(init_h * 0.72) + 1, text="", font=lore_f, fill="#040c06",
            anchor="center", state="hidden"
        )
        self._lore_id = self.badge_canvas.create_text(
            init_w // 2, int(init_h * 0.72), text="", font=lore_f, fill="#ffb74d",
            anchor="center", state="hidden"
        )
        self.lore_label = CanvasTextLabelProxy(
            self.badge_canvas, self._lore_id, self._lore_sh_id,
            initial_text="", initial_font=lore_f, initial_fg="#ffb74d", bg="#0c2917",
            wraplength=self.wraplength
        )
        self.lore_label.pack_forget()

        # Click-to-dismiss bindings across dialog elements
        for w in (self, self.badge, self.badge_canvas):
            w.bind("<Button-1>", lambda e: self.dismiss())
        self.outcome_label.bind("<Button-1>", lambda e: self.dismiss())
        self.lore_label.bind("<Button-1>", lambda e: self.dismiss())

    def set_payout_ratio(self, payout_ratio: tuple[int, int]) -> None:
        """Updates the active Natural Blackjack payout ratio used for banner formatting."""
        if (
            isinstance(payout_ratio, (tuple, list))
            and len(payout_ratio) == 2
            and (int(payout_ratio[0]), int(payout_ratio[1])) in {(3, 2), (6, 5)}
        ):
            self.payout_ratio = (int(payout_ratio[0]), int(payout_ratio[1]))
        else:
            self.payout_ratio = (3, 2)
        if self.current_raw_message:
            self.set_message(self.current_raw_message)

    def format_blackjack_banner(self) -> str:
        """Returns formatted Natural Blackjack banner string for active payout_ratio."""
        num, den = self.payout_ratio
        return f"BLACKJACK! {num}:{den}"

    def dismiss(self):
        """Dismisses the floating dialog overlay immediately."""
        if self._dismiss_timer_id:
            try:
                self.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
            self._dismiss_timer_id = None
        if self.winfo_manager() == "place":
            self.place_forget()

    def destroy(self):
        """Cancels any pending auto-dismiss timer before widget destruction."""
        if self._dismiss_timer_id:
            try:
                self.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
            self._dismiss_timer_id = None
        super().destroy()

    def set_message(self, full_text: str):
        """
        Parses incoming result string. If delimited by ' | ', cleanly separates
        primary outcome (Tier 1) from lore / status narrative (Tier 2).
        Automatically unmaps when empty, and manifests as a floating in-table overlay dialog when active.
        """
        if self._dismiss_timer_id:
            try:
                self.after_cancel(self._dismiss_timer_id)
            except Exception:
                pass
            self._dismiss_timer_id = None

        self.current_raw_message = full_text or ""
        text = self.current_raw_message.strip()
        if not text:
            self.outcome_label.configure(text="")
            self.lore_label.configure(text="")
            self.lore_label.pack_forget()
            if self.winfo_manager() == "place":
                self.place_forget()
            return

        # Check for newline or lore delimiter
        if "\n" in text:
            parts = text.split("\n", 1)
            outcome_text = parts[0].strip()
            lore_text = parts[1].strip()
        elif " | " in text:
            parts = text.split(" | ", 1)
            outcome_text = parts[0].strip()
            lore_text = parts[1].strip()
        else:
            outcome_text = text
            lore_text = ""

        norm_upper = outcome_text.strip().upper()
        if norm_upper in ("BLACKJACK!", "BLACKJACK! 3:2", "BLACKJACK! 6:5"):
            outcome_text = self.format_blackjack_banner()

        if not getattr(self, "_manual_typography_override", False):
            char_len = len(outcome_text)
            if char_len <= 28:
                dyn_out_font = ("Tiny5 Duo", -abs(int(self._tier_short_px)), "bold")
            elif char_len <= 46:
                dyn_out_font = ("Tiny5", -abs(int(self._tier_short_px)), "bold")
            else:
                dyn_out_font = ("Tiny5", -abs(int(self._tier_long_px)), "bold")
            dyn_lore_font = ("Tiny5", -abs(int(self._tier_lore_px)), "normal")
            self.outcome_font_family, self.outcome_font_size, self.outcome_font_weight = (
                dyn_out_font[0],
                abs(dyn_out_font[1]),
                dyn_out_font[2],
            )
            self.lore_font_family, self.lore_font_size = dyn_lore_font[0], abs(dyn_lore_font[1])
            self.outcome_label.configure(font=dyn_out_font, wraplength=self.wraplength)
            self.lore_label.configure(font=dyn_lore_font, wraplength=self.wraplength)
        else:
            dyn_out_font = (self.outcome_font_family, -abs(self.outcome_font_size), self.outcome_font_weight)
            dyn_lore_font = (self.lore_font_family, -abs(self.lore_font_size), self.lore_font_slant)

        self.outcome_label.configure(text=outcome_text)
        self._update_outcome_color(outcome_text)
        if lore_text:
            self.lore_label.configure(text=lore_text)
            self.lore_label.pack()
        else:
            self.lore_label.configure(text="")
            self.lore_label.pack_forget()

        # Dynamic measurement and plaque sizing
        s = getattr(self, "scale", 1.0)
        try:
            import tkinter.font
            f_out = tkinter.font.Font(font=dyn_out_font)
            raw_out_w = f_out.measure(outcome_text)
            line_h = f_out.metrics("linespace")
            if raw_out_w > self.wraplength and self.wraplength > 100:
                n_lines = max(2, int(math.ceil(raw_out_w / float(self.wraplength - 24))))
                tw = min(self.wraplength, raw_out_w)
                th = line_h * n_lines
            else:
                tw = raw_out_w
                th = line_h
            if lore_text:
                f_lore = tkinter.font.Font(font=dyn_lore_font)
                tw = max(tw, min(self.wraplength, f_lore.measure(lore_text)))
                th += f_lore.metrics("linespace") + int(8 * s)
        except Exception:
            tw = max(len(outcome_text), len(lore_text)) * 12
            th = 32

        w = max(int(300 * s), tw + int(56 * s))
        h = max(int(54 * s), th + (int(26 * s) if lore_text else int(22 * s)))
        self.badge_canvas.configure(width=w, height=h)
        self.panel.resize(w // 2, h // 2, w, h, scale=max(2, int(2 * s)))

        cx = w // 2
        if lore_text:
            cy_out = int(h * 0.36)
            cy_lore = int(h * 0.70)
            self.badge_canvas.coords(self._outcome_id, cx, cy_out)
            self.badge_canvas.coords(self._outcome_sh_id, cx + 1, cy_out + 1)
            self.badge_canvas.coords(self._lore_id, cx, cy_lore)
            self.badge_canvas.coords(self._lore_sh_id, cx + 1, cy_lore + 1)
        else:
            cy = h // 2
            self.badge_canvas.coords(self._outcome_id, cx, cy)
            self.badge_canvas.coords(self._outcome_sh_id, cx + 1, cy + 1)

        # Float in upper-center pit gap above the felt rules block (and suppress duplicate generic Ace prompt during Insurance)
        tl = text.lower()
        if getattr(self, "insurance_overlay_active", False) and "take insurance" in tl and "side bet" not in tl:
            if self.winfo_manager() == "place":
                self.place_forget()
            return

        if not self.winfo_manager() or self.winfo_manager() == "place":
            if getattr(self.master, "table_seats", 1) == 3:
                target_rely = 0.24
            elif getattr(self, "insurance_overlay_active", False):
                target_rely = 0.27
            elif lore_text:
                target_rely = 0.29
            else:
                target_rely = 0.33
            self.place(relx=0.5, rely=target_rely, anchor="center")
            self.lift()

        # Automatically dismiss transient announcements after 2.5s
        if "relic" in tl or "equipped" in tl or "blessing" in tl or "achievement" in tl:
            self._dismiss_timer_id = self.after(2500, self.dismiss)

    def set_insurance_overlay_active(self, active: bool) -> None:
        """Coordinates vertical placement and suppresses duplicate prompt text while floating Insurance plaque is active."""
        self.insurance_overlay_active = bool(active)
        if self.insurance_overlay_active and "take insurance" in self.current_raw_message.lower() and "side bet" not in self.current_raw_message.lower():
            if self.winfo_manager() == "place":
                self.place_forget()
            return
        if self.winfo_manager() == "place":
            if getattr(self.master, "table_seats", 1) == 3:
                target_rely = 0.25
            elif self.insurance_overlay_active:
                target_rely = 0.28
            else:
                target_rely = 0.35
            self.place(relx=0.5, rely=target_rely, anchor="center")
            self.lift()

    @property
    def is_lore_visible(self) -> bool:
        return bool(self.lore_label.winfo_manager() == "pack" and self.lore_label.cget("text"))

    def _update_outcome_color(self, outcome_text: str):
        t = outcome_text.lower()
        if "total won" in t or "total win" in t:
            fg = "#69f0ae"  # Vibrant Green
            border = "#00e676"
        elif "total loss" in t or "dealer wins" in t or "bust" in t or "lose" in t or "lost" in t or "damnation" in t:
            fg = "#ff5252"  # Crisp Red
            border = "#ff1744"
        elif "blackjack" in t:
            fg = "#ffd700"  # Gold
            border = "#ffd700"
        elif "win" in t or "won" in t:
            fg = "#69f0ae"  # Vibrant Green
            border = "#00e676"
        elif "total push" in t or "push" in t or "tie" in t or "draw" in t:
            fg = "#ffeb3b"  # Amber / Gold
            border = "#ffeb3b"
        else:
            fg = "#f5f5f5"  # Clean White
            border = "#80cbc4"
        self.outcome_label.configure(fg=fg)
        if hasattr(self, "panel") and self.panel:
            self.panel.update_palette(
                border=border if fg != "#f5f5f5" else "#06140b",
                inner_hi=border if fg != "#f5f5f5" else "#1f4d30",
            )
        if hasattr(self, "badge"):
            try:
                self.badge.configure(highlightbackground=border)
            except Exception:
                pass

    def set_typography(
        self,
        outcome_family: str | None = None,
        outcome_size: int | None = None,
        outcome_weight: str | None = None,
        lore_family: str | None = None,
        lore_size: int | None = None,
        lore_slant: str | None = None,
        wraplength: int | None = None,
        _internal_scale: bool = False,
    ):
        """Allows hot-swapping font parameters and wraplength dynamically."""
        if not _internal_scale:
            self._manual_typography_override = True
        if outcome_family is not None:
            self.outcome_font_family = outcome_family
        if outcome_size is not None:
            self.outcome_font_size = outcome_size
        if outcome_weight is not None:
            self.outcome_font_weight = outcome_weight
        if lore_family is not None:
            self.lore_font_family = lore_family
        if lore_size is not None:
            self.lore_font_size = lore_size
        if lore_slant is not None:
            self.lore_font_slant = lore_slant
        if wraplength is not None:
            self.wraplength = wraplength

        self.outcome_label.configure(
            font=(self.outcome_font_family, -abs(self.outcome_font_size), self.outcome_font_weight),
            wraplength=self.wraplength
        )
        self.lore_label.configure(
            font=(self.lore_font_family, -abs(self.lore_font_size), self.lore_font_slant),
            wraplength=self.wraplength
        )

    def set_display_profile(self, profile: Any) -> None:
        """Applies exact 8px-grid outcome/prompt/lore tiers from an active `DisplayProfile`."""
        self.display_profile = profile
        self._manual_typography_override = False
        art_s = int(getattr(profile, "art_scale", 1))
        tbl_fs = float(getattr(profile, "table_font_scale", float(art_s)))
        if art_s >= 2:
            self.scale = 2.0
            self._tier_short_px = 64
            self._tier_long_px = 48
            self._tier_lore_px = 48
            wrap = 1360
        elif tbl_fs >= 1.35:
            self.scale = 1.25
            self._tier_short_px = 40
            self._tier_long_px = 32
            self._tier_lore_px = 32
            wrap = 980
        else:
            self.scale = 1.0
            self._tier_short_px = 32
            self._tier_long_px = 24
            self._tier_lore_px = 24
            wrap = 680
        self.set_typography(
            outcome_family="Tiny5 Duo",
            outcome_size=self._tier_short_px,
            outcome_weight="bold",
            lore_family="Tiny5",
            lore_size=self._tier_lore_px,
            lore_slant="normal",
            wraplength=wrap,
            _internal_scale=True,
        )
        if self.current_raw_message:
            self.set_message(self.current_raw_message)

    def set_scale(self, scale: float):
        """Scales outcome/lore typography and wraplength proportionally."""
        self.scale = scale
        self._manual_typography_override = False
        if scale >= 1.75:
            self._tier_short_px, self._tier_long_px, self._tier_lore_px, wrap = 64, 48, 48, 1360
        elif scale >= 1.2:
            self._tier_short_px, self._tier_long_px, self._tier_lore_px, wrap = 40, 32, 32, 980
        else:
            self._tier_short_px, self._tier_long_px, self._tier_lore_px, wrap = 32, 24, 24, 680
        self.set_typography(
            outcome_size=self._tier_short_px,
            lore_size=self._tier_lore_px,
            wraplength=wrap,
            _internal_scale=True,
        )
        if hasattr(self, "badge"):
            try:
                self.badge.configure(padx=int(22 * scale), pady=int(8 * scale))
            except Exception:
                pass
        if self.current_raw_message:
            self.set_message(self.current_raw_message)

    def set_theme_color(self, bg_color: str, border_color: str | None = None):
        """Cascades table felt background color to announcement HUD and badge."""
        self.configure(background=bg_color)
        if hasattr(self, "badge"):
            try:
                if border_color:
                    border = border_color
                else:
                    border = "#3a151b" if bg_color.lower() in ("#0d0204", "#140508", "#0e0306") else "#1b2a1b"
                self.badge.configure(background=bg_color, highlightbackground=border)
            except Exception:
                pass
        if hasattr(self, "badge_canvas"):
            try:
                self.badge_canvas.configure(background=bg_color)
            except Exception:
                pass
        if hasattr(self, "outcome_label"):
            self.outcome_label.configure(background=bg_color)
        if hasattr(self, "lore_label"):
            self.lore_label.configure(background=bg_color)


# ============================================================================
# 4. HauntedAltarCanvas
# ============================================================================

class HauntedAltarCanvas(tkinter.Canvas):
    """
    Unified 2.5D Haunted Altar rendering:
    - 5 materializing candles with radial warm light pools and snuffed smoke wisps.
    - Up to 5 rising 2.5D isometric gravestones with dynamic directional shadows cast away from lit candles.
    - Kinetic particle animations:
      - Graves erupting out of table felt with fissure cracks and flying dirt particles.
      - Candles poofing into existence with expanding smoke puff particles and ignition flare sparks.
    - Strict non-blocking Tkinter animation timers with lifecycle cancellation safety.
    """

    def __init__(
        self,
        master,
        assets: dict[str, tkinter.PhotoImage] | None = None,
        width: int | None = None,
        height: int | None = None,
        background: str = PANEL_BACKGROUND_COLOR,
        display_profile: Optional[Any] = None,
        **kwargs
    ):
        altar_cfg = get_ui_layout("haunted_altar")
        init_scale = float(getattr(display_profile, "art_scale", 1)) if display_profile is not None else 1.0
        if width is None:
            width = int(altar_cfg.get("base_width", 260) * init_scale)
        if height is None:
            height = int(altar_cfg.get("base_height", 96) * init_scale)
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.display_profile = display_profile
        self.scale = init_scale
        self.base_width = int(altar_cfg.get("base_width", 260))
        self.base_height = int(altar_cfg.get("base_height", 96))
        self.canvas_width = width
        self.canvas_height = height
        self.assets = assets or {}

        candles_cfg = altar_cfg.get("candles", {})
        self.candle_y = int(candles_cfg.get("origin_y", 22) * init_scale)
        start_c = candles_cfg.get("start_x", 26)
        step_c = candles_cfg.get("step_x", 52)
        self.candle_x_positions = [int((start_c + i * step_c) * init_scale) for i in range(5)]

        graves_cfg = altar_cfg.get("gravestones", {})
        self.gravestone_y = int(graves_cfg.get("origin_y", 62) * init_scale)
        self.gravestone_x_positions = [int(x * init_scale) for x in graves_cfg.get("x_positions", [36, 83, 130, 177, 224])]

        # Altar state
        self.candles_remaining = 5
        self.candles_visible = False
        self.gravestones_count = 0
        self.gravestones_visible = False

        # Animation states & timer tracking
        self.is_animating_eruption = False
        self.is_animating_poof = False
        self._anim_timer_ids: list[str] = []

        # Eruption animation parameters
        self._eruption_stone_index = 0
        self._eruption_frame = 0
        self._eruption_total_frames = 8
        self._eruption_y_offset = 0.0
        self._eruption_on_complete = None
        self._debris_particles: list[dict] = []

        # Poof animation parameters
        self._poof_frame = 0
        self._poof_total_frames = 10
        self._poof_on_complete = None
        self._smoke_particles: list[dict] = []
        self._spark_particles: list[dict] = []

        # Felt texture synchronization tracking
        self._felt_source_img = None
        self._felt_coords = None
        self._felt_slice_img = None
        self._felt_slice_photo = None
        self._felt_theme = None
        self._is_hell_table = False

        self.bind("<Map>", lambda e: self._ensure_felt_sync())
        self._draw_altar()

    def _ensure_felt_sync(self):
        """Automatically resolves the active TableFeltCanvas and crops matching felt slice."""
        parent = getattr(self, "master", None)
        while parent is not None and not isinstance(parent, TableFeltCanvas) and hasattr(parent, "master"):
            parent = parent.master
        if parent is not None and isinstance(parent, TableFeltCanvas):
            if (
                getattr(self, "_felt_slice_photo", None) is not None
                and getattr(self, "_felt_theme", None) == parent.current_theme
                and getattr(self, "_felt_slice_img", None) is not None
                and self._felt_slice_img.size == (self.canvas_width, self.canvas_height)
            ):
                return
            self._felt_theme = parent.current_theme
            try:
                cx = self.winfo_x()
                cy = self.winfo_y()
                p_curr = getattr(self, "master", None)
                while p_curr is not None and p_curr is not parent and hasattr(p_curr, "master"):
                    cx += p_curr.winfo_x()
                    cy += p_curr.winfo_y()
                    p_curr = p_curr.master
                w = max(10, self.canvas_width)
                h = max(10, self.canvas_height)
                slice_img = parent.get_felt_slice(cx, cy, w, h)
                if slice_img and PIL_AVAILABLE and ImageTk is not None:
                    self._felt_slice_img = slice_img
                    self._felt_slice_photo = ImageTk.PhotoImage(slice_img, master=self)
                    if not self.find_withtag("felt_bg"):
                        self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
                    else:
                        self.itemconfigure("felt_bg", image=self._felt_slice_photo)
                    self.tag_lower("felt_bg")
            except Exception:
                pass

    def set_display_profile(self, profile: Any, assets: dict[str, tkinter.PhotoImage] | None = None) -> None:
        """Applies integer `art_scale` from an active `DisplayProfile`."""
        self.display_profile = profile
        self.set_scale(float(getattr(profile, "art_scale", 1)), assets=assets)

    def set_scale(self, scale: float, assets: dict[str, tkinter.PhotoImage] | None = None):
        """Scales canvas dimensions and re-projects candle/stone coordinates proportionally."""
        self.scale = scale
        if assets is not None:
            self.assets = assets
        altar_cfg = get_ui_layout("haunted_altar")
        bw = int(altar_cfg.get("base_width", 260))
        bh = int(altar_cfg.get("base_height", 96))
        self.canvas_width = int(bw * scale)
        self.canvas_height = int(bh * scale)
        self.configure(width=self.canvas_width, height=self.canvas_height)
        candles_cfg = altar_cfg.get("candles", {})
        graves_cfg = altar_cfg.get("gravestones", {})
        self.candle_y = int(candles_cfg.get("origin_y", 22) * scale)
        start_c = candles_cfg.get("start_x", 26)
        step_c = candles_cfg.get("step_x", 52)
        self.candle_x_positions = [int((start_c + i * step_c) * scale) for i in range(5)]
        self.gravestone_y = int(graves_cfg.get("origin_y", 62) * scale)
        self.gravestone_x_positions = [int(x * scale) for x in graves_cfg.get("x_positions", [36, 83, 130, 177, 224])]
        self._felt_slice_photo = None
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        else:
            self._ensure_felt_sync()
        self._draw_altar()

    def sync_felt_background(self, felt_img: Any, rel_x: int, rel_y: int):
        """Crops and synchronizes the underlying table felt texture into this canvas for seamless alpha integration."""
        if not PIL_AVAILABLE or Image is None or ImageTk is None:
            return
        if not felt_img or not hasattr(felt_img, "width"):
            return
        self._felt_source_img = felt_img
        self._felt_coords = (rel_x, rel_y)
        parent = getattr(self, "master", None)
        while parent is not None and not isinstance(parent, TableFeltCanvas) and hasattr(parent, "master"):
            parent = parent.master
        if parent is not None and isinstance(parent, TableFeltCanvas):
            self._felt_theme = parent.current_theme
        try:
            w = self.canvas_width
            h = self.canvas_height
            bg_col = str(self["background"])
            bg_rgb = hex_to_rgb(bg_col) if bg_col.startswith("#") else (20, 32, 24)

            # Clamp crop window so it is fully contained within the parent felt image
            if felt_img.width >= w:
                crop_x1 = max(0, min(rel_x, felt_img.width - w))
            else:
                crop_x1 = 0
            if felt_img.height >= h:
                crop_y1 = max(0, min(rel_y, felt_img.height - h))
            else:
                crop_y1 = 0

            crop_x2 = min(felt_img.width, crop_x1 + w)
            crop_y2 = min(felt_img.height, crop_y1 + h)

            slice_img = Image.new("RGB", (w, h), bg_rgb)
            if crop_x2 > crop_x1 and crop_y2 > crop_y1:
                cropped = felt_img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
                slice_img.paste(cropped, (0, 0))

            self._felt_slice_img = slice_img
            self._felt_slice_photo = ImageTk.PhotoImage(slice_img, master=self)
            if not self.find_withtag("felt_bg"):
                self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
            else:
                self.itemconfigure("felt_bg", image=self._felt_slice_photo)
            self.tag_lower("felt_bg")
        except Exception:
            pass

    def set_candle_state(self, candles_remaining: int, visible: bool = True):
        """Sets remaining lit candles (0 to 5) and redraws altar."""
        self.candles_remaining = max(0, min(5, candles_remaining))
        self.candles_visible = visible
        self._ensure_felt_sync()
        self._draw_altar()

    def set_gravestone_state(self, count: int, visible: bool = True):
        """Sets visible gravestones count (0 to 5) and redraws altar."""
        self.gravestones_count = max(0, min(5, count))
        self.gravestones_visible = visible
        self._ensure_felt_sync()
        self._draw_altar()

    def get_lit_candle_indices(self) -> list[int]:
        """Returns indices of candles that are currently lit."""
        if not self.candles_visible:
            return []
        return list(range(self.candles_remaining))

    def calculate_light_centroid(self) -> float:
        """Calculates average X position of all currently lit candles."""
        lit = self.get_lit_candle_indices()
        if not lit:
            return 130.0  # Center default
        total_x = sum(self.candle_x_positions[i] for i in lit)
        return total_x / len(lit)

    def calculate_shadow_offset_dx(self, stone_x: float, centroid: float) -> float:
        """Calculates directional X offset for drop shadow based on light centroid."""
        if not self.candles_visible or self.candles_remaining == 0:
            return 0.0
        # Shadow tilts away from light source
        return 0.45 * (stone_x - centroid)

    def animate_candle_poof(self, candle_indices: list[int] | None = None, on_complete=None):
        """Triggers smoke puff and ignition spark burst when candles manifest."""
        self.cancel_animations()
        self.is_animating_poof = True
        self._poof_frame = 0
        self._poof_total_frames = 10
        self._poof_on_complete = on_complete
        self.candles_visible = True

        targets = candle_indices if candle_indices is not None else list(range(5))
        self._smoke_particles = []
        self._spark_particles = []

        for ci in targets:
            cx = self.candle_x_positions[ci]
            cy = self.candle_y
            # 12 expanding smoke particles per candle
            for _ in range(12):
                angle = random.uniform(0, 2 * math.pi)
                spd = random.uniform(0.6, 2.2)
                self._smoke_particles.append({
                    "x": cx + math.cos(angle) * 3,
                    "y": cy + math.sin(angle) * 3,
                    "vx": math.cos(angle) * spd,
                    "vy": math.sin(angle) * spd - 0.4,
                    "radius": random.uniform(3.0, 5.0),
                    "max_radius": random.uniform(11.0, 16.0),
                    "color": random.choice(["#f5f5f5", "#e0e0e0", "#bdbdbd", "#9e9e9e", "#757575"])
                })
            # Core ignition spark
            self._spark_particles.append({
                "x": cx,
                "y": cy - 12,
                "radius": 2.0,
                "max_radius": 8.0,
                "color": "#fff59d"
            })

        self._step_poof()

    def _step_poof(self):
        if not self.is_animating_poof:
            return
        t = (self._poof_frame + 1) / self._poof_total_frames

        # Update smoke particles
        for p in self._smoke_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["radius"] += (p["max_radius"] - p["radius"]) * 0.22

        # Update sparks (grow then shrink)
        for s in self._spark_particles:
            if t < 0.35:
                s["radius"] = 2.0 + (s["max_radius"] - 2.0) * (t / 0.35)
            else:
                s["radius"] = max(0.0, s["max_radius"] * (1.0 - (t - 0.35) / 0.65))

        self._draw_altar()
        self._poof_frame += 1

        if self._poof_frame < self._poof_total_frames:
            tid = self.after(30, self._step_poof)
            self._anim_timer_ids.append(tid)
        else:
            self._smoke_particles.clear()
            self._spark_particles.clear()
            self.is_animating_poof = False
            self._draw_altar()
            if self._poof_on_complete:
                cb = self._poof_on_complete
                self._poof_on_complete = None
                cb()

    def animate_grave_eruption(self, stone_index: int, on_complete=None):
        """Animates a gravestone bursting up through the table felt."""
        self.cancel_animations()
        self.is_animating_eruption = True
        self._eruption_stone_index = max(0, min(4, stone_index))
        self._eruption_frame = 0
        self._eruption_total_frames = 8
        self._eruption_on_complete = on_complete
        self.gravestones_visible = True
        self.gravestones_count = max(self.gravestones_count, self._eruption_stone_index + 1)

        gx = self.gravestone_x_positions[self._eruption_stone_index]
        gy = self.gravestone_y

        self._debris_particles = []
        for _ in range(14):
            vx = random.uniform(-2.5, 2.5)
            vy = random.uniform(-6.5, -3.5)
            self._debris_particles.append({
                "x": gx + random.uniform(-10, 10),
                "y": gy + 20,
                "vx": vx,
                "vy": vy,
                "size": random.randint(2, 4),
                "color": random.choice(["#3e2723", "#271b12", "#4e342e", "#1b120c"])
            })

        self._step_eruption()

    def _step_eruption(self):
        if not self.is_animating_eruption:
            return
        t = (self._eruption_frame + 1) / self._eruption_total_frames
        # Smooth ease-out rise from under ground (offset from 36 down to 0)
        self._eruption_y_offset = 36.0 * (1.0 - math.sqrt(t))

        # Gravity on debris
        for p in self._debris_particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.85

        self._draw_altar()
        self._eruption_frame += 1

        if self._eruption_frame < self._eruption_total_frames:
            tid = self.after(35, self._step_eruption)
            self._anim_timer_ids.append(tid)
        else:
            self._eruption_y_offset = 0.0
            self._debris_particles.clear()
            self.is_animating_eruption = False
            self._draw_altar()
            if self._eruption_on_complete:
                cb = self._eruption_on_complete
                self._eruption_on_complete = None
                cb()

    def cancel_animations(self):
        """Immediately stops all animation timers and resets transient visual effects."""
        for tid in self._anim_timer_ids:
            try:
                self.after_cancel(tid)
            except Exception:
                pass
        self._anim_timer_ids.clear()
        self.is_animating_eruption = False
        self.is_animating_poof = False
        self._eruption_y_offset = 0.0
        self._debris_particles.clear()
        self._smoke_particles.clear()
        self._spark_particles.clear()

    def set_theme_color(self, bg_color: str, is_hell_table: bool = False):
        """Updates the altar canvas background color and refreshes lighting."""
        self._is_hell_table = is_hell_table
        self.configure(background=bg_color)
        self._felt_theme = None
        self._felt_slice_photo = None
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        else:
            self._ensure_felt_sync()
        self._draw_altar()

    def destroy(self):
        self.cancel_animations()
        super().destroy()

    def _draw_altar(self):
        self.delete("all")
        # 0. Underlying felt slice background
        if getattr(self, "_felt_slice_photo", None) is None:
            self._ensure_felt_sync()
        if getattr(self, "_felt_slice_photo", None):
            self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")
        bg_col = str(self["background"])
        bg_lower = bg_col.lower()
        is_hell = getattr(self, "_is_hell_table", False) or (bg_lower in ("#0d0204", "#140508", "#2a0d12", "#0e0306", "#16050a"))
        is_creep = getattr(self, "_felt_theme", None) == "creep" or (bg_lower in ("#142018", "#021206", "#031908", "#03230b", "#042c0e"))
        is_dark_bg = is_hell or is_creep

        # Calculate lighting centroid
        centroid = self.calculate_light_centroid()

        # 1. Candles & Glow Pools
        if self.candles_visible:
            candles_cfg = get_ui_layout("haunted_altar", "candles")
            lit_img = self.assets.get("candle_lit")
            unlit_img = self.assets.get("candle_unlit")

            for i, cx in enumerate(self.candle_x_positions):
                cy = self.candle_y
                is_lit = i < self.candles_remaining

                if is_lit:
                    # Luminous warm candlelight glow pool on the table felt
                    if is_hell:
                        glow_outer = "#3d1008"
                        glow_mid = "#7a200d"
                        glow_inner = "#ff8f00"
                    elif is_creep:
                        glow_outer = "#102a16"
                        glow_mid = "#28441c"
                        glow_inner = "#c4a32a"
                    else:
                        glow_outer = "#1a5e1a"
                        glow_mid = "#3b7a22"
                        glow_inner = "#d4b830"

                    s = getattr(self, "scale", 1.0)
                    glow_cfg = candles_cfg.get("glow", {})
                    out_g = glow_cfg.get("outer", {"rx": 24, "ry_top": -6, "ry_bottom": 30})
                    mid_g = glow_cfg.get("mid", {"rx": 16, "ry_top": 0, "ry_bottom": 24})
                    inn_g = glow_cfg.get("inner", {"rx": 8, "ry_top": 6, "ry_bottom": 18})

                    self.create_oval(
                        cx - int(out_g["rx"] * s), cy + int(out_g["ry_top"] * s), cx + int(out_g["rx"] * s), cy + int(out_g["ry_bottom"] * s),
                        fill=glow_outer, outline="", tags="glow"
                    )
                    self.create_oval(
                        cx - int(mid_g["rx"] * s), cy + int(mid_g["ry_top"] * s), cx + int(mid_g["rx"] * s), cy + int(mid_g["ry_bottom"] * s),
                        fill=glow_mid, outline="", tags="glow"
                    )
                    self.create_oval(
                        cx - int(inn_g["rx"] * s), cy + int(inn_g["ry_top"] * s), cx + int(inn_g["rx"] * s), cy + int(inn_g["ry_bottom"] * s),
                        fill=glow_inner, outline="", tags="glow"
                    )
                    if lit_img:
                        self.create_image(cx, cy, image=lit_img, anchor="center", tags="candle")
                    else:
                        # Fallback vector lit candle
                        self.create_rectangle(cx - 5, cy - 8, cx + 5, cy + 14, fill="#e8d8a7", outline="#8a733f", tags="candle")
                        self.create_oval(cx - 4, cy - 16, cx + 4, cy - 7, fill="#ff9100", outline="", tags="candle")
                        self.create_oval(cx - 2, cy - 14, cx + 2, cy - 8, fill="#fff59d", outline="", tags="candle")
                else:
                    if unlit_img:
                        self.create_image(cx, cy, image=unlit_img, anchor="center", tags="candle")
                    else:
                        # Fallback vector unlit candle
                        self.create_rectangle(cx - 5, cy - 8, cx + 5, cy + 14, fill="#8a8068", outline="#4a4030", tags="candle")
                        self.create_line(cx, cy - 8, cx, cy - 12, fill="#111111", width=2, tags="candle")

        # 2. Gravestones with Directional Drop Shadows
        if self.gravestones_visible and self.gravestones_count > 0:
            grave_img = self.assets.get("gravestone")
            num_stones = min(self.gravestones_count, 5)

            for k in range(num_stones):
                gx = self.gravestone_x_positions[k]
                gy = self.gravestone_y
                y_disp = self._eruption_y_offset if (self.is_animating_eruption and k == self._eruption_stone_index) else 0.0

                s = getattr(self, "scale", 1.0)
                dx = self.calculate_shadow_offset_dx(gx, centroid)
                dy = (6 + (5 - self.candles_remaining)) * s

                ground_y = gy + int(15 * s)
                w_half = int(18 * s)
                shadow_pts = [
                    gx - w_half + dx * 0.15, ground_y,
                    gx + w_half + dx * 0.15, ground_y,
                    gx + w_half + dx, ground_y + dy,
                    gx - w_half + dx, ground_y + dy
                ]
                shadow_col = "#150204" if is_dark_bg else "#071207"
                self.create_polygon(shadow_pts, fill=shadow_col, outline="", smooth=True, tags="shadow")

                # Fissure cracks if erupting
                if self.is_animating_eruption and k == self._eruption_stone_index:
                    fissure_col = "#1a0408" if is_dark_bg else "#040b04"
                    self.create_line(gx, ground_y, gx - 16, ground_y + 4, fill=fissure_col, width=2, tags="fissure")
                    self.create_line(gx, ground_y, gx + 18, ground_y + 3, fill=fissure_col, width=2, tags="fissure")
                    self.create_line(gx - 6, ground_y + 2, gx - 20, ground_y + 8, fill=fissure_col, width=1, tags="fissure")
                    self.create_line(gx + 8, ground_y + 2, gx + 22, ground_y + 7, fill=fissure_col, width=1, tags="fissure")

                # Gravestone sprite
                if grave_img:
                    self.create_image(gx, gy + y_disp, image=grave_img, anchor="center", tags="grave")
                else:
                    self.create_polygon(
                        [gx - 16, gy + y_disp + 18, gx - 16, gy + y_disp - 8,
                         gx, gy + y_disp - 20, gx + 16, gy + y_disp - 8, gx + 16, gy + y_disp + 18],
                        fill="#606770", outline="#30353b", tags="grave"
                    )

        # 3. Particle Layers: Debris & Smoke
        for p in self._debris_particles:
            s_sz = p["size"]
            self.create_oval(p["x"] - s_sz, p["y"] - s_sz, p["x"] + s_sz, p["y"] + s_sz, fill=p["color"], outline="", tags="debris")

        for sm in self._smoke_particles:
            r = sm["radius"]
            self.create_oval(sm["x"] - r, sm["y"] - r, sm["x"] + r, sm["y"] + r, fill=sm["color"], outline="", tags="smoke")

        for sp in self._spark_particles:
            r = sp["radius"]
            if r > 0.5:
                self.create_oval(sp["x"] - r, sp["y"] - r, sp["x"] + r, sp["y"] + r, fill=sp["color"], outline="", tags="spark")


# ============================================================================
# 5. DealerStageCanvas
# ============================================================================

class DealerStageCanvas(tkinter.Canvas):
    """
    Panoramic Horizon Stage Canvas.
    Spans 100% of the table width above the horizon rail, rendering:
    - High-definition panoramic atmospheric backdrops (Casino, Creep, Hell, Celestial, Crypt).
    - Centered living dealer actor composite and stage accessories.
    - Top-right wardrobe coat-hanger button for launching Wardrobe & Casino Records.
    - Dynamic resize handling and High-DPI in-memory scaling.
    """

    DEFAULT_WIDTH = 1000
    DEFAULT_HEIGHT = 220

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Optional[Any] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        on_hanger_click: Optional[Callable[[], None]] = None,
        display_profile: Optional[Any] = None,
        **kwargs
    ):
        art_scale = int(getattr(display_profile, "art_scale", 1)) if display_profile is not None else 1
        eff_w = int(width) if width is not None else (int(getattr(display_profile, "stage_w", self.DEFAULT_WIDTH * art_scale)) if display_profile is not None else self.DEFAULT_WIDTH)
        eff_h = int(height) if height is not None else (int(getattr(display_profile, "stage_h", self.DEFAULT_HEIGHT * art_scale)) if display_profile is not None else self.DEFAULT_HEIGHT)
        super().__init__(
            parent,
            width=eff_w,
            height=eff_h,
            background="#0a0a0a",
            highlightthickness=0,
            borderwidth=0,
            **kwargs
        )
        self.app = app
        self.display_profile = display_profile
        self.current_theme = "casino"
        self.scale_factor = float(art_scale)
        self.on_hanger_click = on_hanger_click
        self.canvas_width = eff_w
        self.canvas_height = eff_h

        self.backdrop_images: dict[str, Any] = {}
        self.hanger_photo: Optional[Any] = None
        self.hanger_photo_2x: Optional[Any] = None
        self._active_backdrop_photo: Optional[Any] = None
        self._dealer_photo: Optional[Any] = None
        self.particles: list[dict] = []
        self._active_speech_tail: Optional[tuple[str, str]] = None

        self._load_backdrop_assets()
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_canvas_click)
        self.bind("<Motion>", self._on_mouse_move)

        self._redraw_stage()

    def draw_speech_tail(self, fill_col: str = "#1c110b", border_col: str = "#d4af37"):
        """Draws directional callout tail from speech bubble pointing toward dealer avatar."""
        self._active_speech_tail = (fill_col, border_col)
        if not self.find_withtag("dialogue_win"):
            return
        s = self.scale_factor
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)

        stage_cfg = get_ui_layout("dealer_stage")
        bubble_cfg = stage_cfg.get("speech_bubble", {})
        anchor = bubble_cfg.get("anchor_offset", {"x": -76, "y": -90})
        bubble_x = w // 2 + int(anchor.get("x", -76) * s)
        bubble_y = h + int(anchor.get("y", -90) * s)

        p1_off = bubble_cfg.get("tail_top_offset", {"x": -4, "y": -44})
        p2_off = bubble_cfg.get("tail_mid_offset", {"x": -4, "y": -30})
        p3_off = bubble_cfg.get("tail_target_offset", {"x": -44, "y": -127})

        # Directional pointer tail projecting toward dealer avatar mouth at head level
        p1 = (bubble_x + int(p1_off.get("x", -4) * s), bubble_y + int(p1_off.get("y", -44) * s))
        p2 = (bubble_x + int(p2_off.get("x", -4) * s), bubble_y + int(p2_off.get("y", -30) * s))
        p3 = (w // 2 + int(p3_off.get("x", -44) * s), h + int(p3_off.get("y", -127) * s))

        self.delete("speech_tail")
        self.create_polygon(
            p1[0], p1[1], p2[0], p2[1], p3[0], p3[1],
            fill=fill_col, outline=border_col, width=max(1, int(s)),
            tags="speech_tail"
        )
        self.create_line(
            p1[0], p1[1], p3[0], p3[1],
            fill=border_col, width=max(1, int(s)), tags="speech_tail"
        )
        if self.find_withtag("dialogue_win"):
            if self.itemcget("dialogue_win", "state") == "hidden":
                self.itemconfigure("speech_tail", state="hidden")
            else:
                self.lift("dialogue_win")

    def clear_speech_tail(self):
        """Removes the active speech callout tail from the canvas."""
        self._active_speech_tail = None
        self.delete("speech_tail")

    def set_dealer_image(self, photo: Optional[Any]):
        """Sets and updates the dealer sprite rendered directly on the stage canvas."""
        self._dealer_photo = photo
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        if self.find_withtag("dealer_sprite"):
            if photo:
                self.itemconfigure("dealer_sprite", image=photo)
                self.coords("dealer_sprite", w // 2, h)
                self.lift("dealer_sprite")
                if self.find_withtag("speech_tail"):
                    self.lift("speech_tail")
                if self.find_withtag("dialogue_win"):
                    self.lift("dialogue_win")
                if self.find_withtag("hanger_btn"):
                    self.lift("hanger_btn")
            else:
                self.delete("dealer_sprite")
        elif photo:
            self.create_image(w // 2, h, image=photo, anchor="s", tags="dealer_sprite")
            if self.find_withtag("speech_tail"):
                self.lift("speech_tail")
            if self.find_withtag("dialogue_win"):
                self.lift("dialogue_win")
            if self.find_withtag("hanger_btn"):
                self.lift("hanger_btn")

    def _load_backdrop_assets(self):
        backdrops_dir = HAUNTED_ASSETS_DIR / "backdrops"
        theme_files = {
            "casino": ("backdrop_casino.png", "backdrop_casino_2x.png"),
            "creep": ("backdrop_creep.png", "backdrop_creep_2x.png"),
            "hell": ("backdrop_hell.png", "backdrop_hell_2x.png"),
            "celestial": ("backdrop_celestial.png", "backdrop_celestial_2x.png"),
            "crypt": ("backdrop_crypt.png", "backdrop_crypt_2x.png"),
            "cyber": ("backdrop_cyber.png", "backdrop_cyber_2x.png"),
            "academy": ("backdrop_academy.png", "backdrop_academy_2x.png"),
        }

        for theme, (f1x, f2x) in theme_files.items():
            p1x = backdrops_dir / f1x
            p2x = backdrops_dir / f2x
            if p1x.exists() and PIL_AVAILABLE and Image is not None and ImageTk is not None:
                try:
                    with Image.open(p1x) as im1:
                        img1x = im1.copy()
                    photo1x = ImageTk.PhotoImage(img1x, master=self)
                    if p2x.exists():
                        with Image.open(p2x) as im2:
                            img2x = im2.copy()
                        photo2x = ImageTk.PhotoImage(img2x, master=self)
                    else:
                        img2x = img1x
                        photo2x = photo1x
                    self.backdrop_images[theme] = {
                        1.0: (img1x, photo1x),
                        2.0: (img2x, photo2x),
                    }
                except Exception:
                    pass

        # Hanger icon
        h1x = HAUNTED_ASSETS_DIR / "hanger_icon.png"
        h2x = HAUNTED_ASSETS_DIR / "hanger_icon_2x.png"
        if h1x.exists() and PIL_AVAILABLE and Image is not None and ImageTk is not None:
            try:
                self.hanger_photo = ImageTk.PhotoImage(Image.open(h1x), master=self)
                self.hanger_photo_2x = ImageTk.PhotoImage(Image.open(h2x), master=self) if h2x.exists() else self.hanger_photo
            except Exception:
                pass

    def _on_resize(self, event):
        if event.width > 10 and (event.width != self.canvas_width or event.height != self.canvas_height):
            self.canvas_width = event.width
            self.canvas_height = event.height
            self._redraw_stage()

    def _redraw_stage(self):
        self.delete("backdrop")
        self.delete("hanger_btn")

        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)

        # 1. Draw exact integer backdrop (zero non-integer stretch at 1000x220 1x and 2000x440 2x)
        theme_data = self.backdrop_images.get(self.current_theme)
        if theme_data and PIL_AVAILABLE and Image is not None and ImageTk is not None:
            active_scale = 2.0 if self.scale_factor >= 1.8 else 1.0
            raw_img, cached_photo = theme_data.get(active_scale, (None, None))
            if raw_img is not None:
                try:
                    if raw_img.size == (w, h) and cached_photo is not None:
                        self._active_backdrop_photo = cached_photo
                    else:
                        resample_mode = getattr(Image, "Resampling", Image).NEAREST
                        resized = raw_img.resize((w, h), resample_mode)
                        self._active_backdrop_photo = ImageTk.PhotoImage(resized, master=self)
                    self.create_image(0, 0, image=self._active_backdrop_photo, anchor="nw", tags="backdrop")
                except Exception:
                    pass

        # 2. Draw Hanger button at top right
        hanger_img = self.hanger_photo_2x if self.scale_factor > 1.5 else self.hanger_photo
        if hanger_img:
            hx = w - int(24 * self.scale_factor)
            hy = int(18 * self.scale_factor)
            self.create_image(hx, hy, image=hanger_img, anchor="center", tags="hanger_btn")

        # 3. Position and update Centered Dealer Sprite directly on canvas
        if getattr(self, "_dealer_photo", None):
            if not self.find_withtag("dealer_sprite"):
                self.create_image(w // 2, h, image=self._dealer_photo, anchor="s", tags="dealer_sprite")
            else:
                self.coords("dealer_sprite", w // 2, h)
                self.itemconfigure("dealer_sprite", anchor="s")

        # 4. Position Dialogue Window at head level to the left of the dealer
        if self.find_withtag("dialogue_win"):
            bubble_x = w // 2 - int(76 * self.scale_factor)
            bubble_y = h - int(90 * self.scale_factor)
            self.coords("dialogue_win", bubble_x, bubble_y)
            self.itemconfigure("dialogue_win", anchor="se")
            self.lift("dialogue_win")

        if self._active_speech_tail:
            self.draw_speech_tail(self._active_speech_tail[0], self._active_speech_tail[1])

        if self.find_withtag("hanger_btn"):
            self.lift("hanger_btn")

        # Legacy header_row support
        if self.find_withtag("header_row"):
            self.coords("header_row", w // 2, h - 2)
            self.itemconfigure("header_row", anchor="s")

    def _is_over_hanger(self, x: int, y: int) -> bool:
        s = self.scale_factor
        w = max(10, self.canvas_width)
        hx = w - int(24 * s)
        hy = int(18 * s)
        pad = int(16 * s)
        return (hx - pad <= x <= hx + pad) and (hy - pad <= y <= hy + pad)

    def _on_canvas_click(self, event):
        if self._is_over_hanger(event.x, event.y):
            if self.on_hanger_click:
                self.on_hanger_click()

    def _on_mouse_move(self, event):
        if self._is_over_hanger(event.x, event.y):
            self.configure(cursor="hand2")
        else:
            self.configure(cursor="")

    def spawn_ambient_particles(self, count: int = 1):
        """Spawns ambient floating motes/embers/dust on the stage canvas matching active theme."""
        s = self.scale_factor
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        theme = self.current_theme

        for _ in range(count):
            if theme == "hell":
                px = random.randint(w // 2 - int(130 * s), w // 2 + int(130 * s))
                py = h - random.randint(10, 70)
                vx = random.uniform(-0.8, 0.8)
                vy = random.uniform(-2.5, -0.9)
                r = random.uniform(1.5, 3.5)
                color = random.choice(["#ff3d00", "#ff9100", "#ffab00", "#424242"])
                life = random.randint(25, 45)
                ptype = "ember"
            elif theme == "celestial":
                px = random.randint(w // 2 - int(140 * s), w // 2 + int(140 * s))
                py = random.randint(10, 60)
                vx = random.uniform(-0.5, 0.5)
                vy = random.uniform(0.6, 1.8)
                r = random.uniform(1.5, 3.0)
                color = random.choice(["#ffd700", "#ffffff", "#80d8ff"])
                life = random.randint(30, 50)
                ptype = "starlight"
            elif theme == "crypt":
                px = random.randint(w // 2 - int(120 * s), w // 2 + int(120 * s))
                py = h - random.randint(10, 60)
                vx = random.uniform(-0.6, 0.6)
                vy = random.uniform(-1.5, -0.5)
                r = random.uniform(1.2, 2.8)
                color = random.choice(["#b388ff", "#b0bec5", "#e0e0e0", "#80cbc4"])
                life = random.randint(25, 40)
                ptype = "bonedust"
            else:
                px = random.randint(int(40 * s), w - int(40 * s))
                py = random.randint(20, h - 20)
                vx = random.uniform(-0.3, 0.3)
                vy = random.uniform(-0.5, -0.1)
                r = random.uniform(1.0, 2.2)
                color = random.choice(["#ffe082", "#ffd54f", "#cfd8dc"])
                life = random.randint(30, 55)
                ptype = "dust"

            self.particles.append({
                "x": px,
                "y": py,
                "vx": vx,
                "vy": vy,
                "radius": r,
                "color": color,
                "life": life,
                "max_life": life,
                "type": ptype,
            })

    def spawn_sweat_particle(self):
        """Spawns an anxious sweat drop particle when dealer busts or suffers shock."""
        s = self.scale_factor
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        self.particles.append({
            "x": w // 2 + int(36 * s),
            "y": h - int(120 * s),
            "vx": random.uniform(0.1, 0.3),
            "vy": 2.8,
            "radius": 2.5,
            "color": "#80d8ff",
            "life": 18,
            "max_life": 18,
            "type": "sweat",
        })

    def update_particles(self):
        """Advances and renders all active stage canvas particles."""
        if not self.particles:
            return
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)

        surviving = []
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] > 0 and 0 <= p["x"] <= w and 0 <= p["y"] <= h + 10:
                surviving.append(p)

        self.particles = surviving

        # Redraw particle canvas items
        self.delete("stage_particle")
        for p in self.particles:
            x, y, r = p["x"], p["y"], p["radius"]
            self.create_oval(
                x - r, y - r, x + r, y + r,
                fill=p["color"], outline="", tags="stage_particle"
            )

        if self.find_withtag("dealer_sprite"):
            self.lift("dealer_sprite")
        if self.find_withtag("speech_tail"):
            self.lift("speech_tail")
        if self.find_withtag("dialogue_win"):
            if self.itemcget("dialogue_win", "state") == "hidden":
                self.itemconfigure("speech_tail", state="hidden")
            else:
                self.lift("dialogue_win")
        if self.find_withtag("hanger_btn"):
            self.lift("hanger_btn")

    def clear_particles(self):
        """Removes all active stage particles from memory and canvas."""
        self.particles.clear()
        self.delete("stage_particle")

    def set_theme(self, theme: str):
        if self.current_theme != theme:
            self.current_theme = theme
            self.clear_particles()
            self._redraw_stage()

    def cancel_animations(self):
        """Clears transient stage particles during DisplayProfile transitions."""
        self.clear_particles()

    def set_display_profile(self, profile: Any) -> None:
        """Locks `DealerStageCanvas` to integer `1000x220` (`1x`) or `2000x440` (`2x`) with zero stretch."""
        self.display_profile = profile
        art_scale = int(getattr(profile, "art_scale", 1))
        self.scale_factor = float(art_scale)
        self.canvas_width = int(getattr(profile, "stage_w", self.DEFAULT_WIDTH * art_scale))
        self.canvas_height = int(getattr(profile, "stage_h", self.DEFAULT_HEIGHT * art_scale))
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self._redraw_stage()

    def set_scale(self, scale_factor: float):
        art_scale = 2 if scale_factor >= 1.8 else 1
        self.scale_factor = float(art_scale)
        self.canvas_width = self.DEFAULT_WIDTH * art_scale
        self.canvas_height = self.DEFAULT_HEIGHT * art_scale
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self._redraw_stage()


# ============================================================================
# 6. TableFeltCanvas
# ============================================================================

class CanvasCardSpriteProxy:
    """
    Lightweight compatibility proxy for canvas card sprites (e.g., dealer_hole_widget).
    Exposes cget('image'), __getitem__('image'), and configure(image=...) to maintain
    100% backward compatibility with tests/callers that inspected tkinter.Label widgets.
    """

    def __init__(self, canvas: tkinter.Canvas, item_id: int):
        self._canvas = canvas
        self._item_id = item_id

    @property
    def item_id(self) -> int:
        return self._item_id

    def cget(self, key: str) -> Any:
        if key == "image":
            return self._canvas.itemcget(self._item_id, "image")
        try:
            return self._canvas.itemcget(self._item_id, key)
        except Exception:
            return ""

    def __getitem__(self, key: str) -> Any:
        return self.cget(key)

    def configure(self, **kwargs) -> None:
        opts = {}
        for k, v in kwargs.items():
            if k in ("image", "tags"):
                opts[k] = v
        if opts:
            try:
                self._canvas.itemconfigure(self._item_id, **opts)
            except Exception:
                pass

    def config(self, **kwargs) -> None:
        self.configure(**kwargs)

    def destroy(self) -> None:
        try:
            self._canvas.delete(self._item_id)
        except Exception:
            pass


class TableFeltCanvas(tkinter.Canvas):
    """
    Panoramic Casino Table Felt Canvas.
    Renders an authentic tactile woven baize felt texture with:
    - High-frequency micro-fiber woolen noise and subtle cross-twill weave lines.
    - Soft overhead table lamp ambient radial lighting vignette.
    - Authentic casino table markings in muted antique gold:
      * Dealer/insurance boundary arc
      * 'BLACKJACK PAYS 3 TO 2'
      * 'Dealer must stand on 17 and must draw to 16'
      * 'INSURANCE PAYS 2 TO 1'
    - Phase-specific felt color palettes (Classic, Creep, Hell, Celestial).
    - Preserves container compatibility: grid(), rowconfigure(), columnconfigure(), ['background'].
    """

    THEME_COLORS = {
        "casino": {
            "base": (7, 76, 26),
            "bg_hex": PANEL_BACKGROUND_COLOR,
            "gold": (212, 175, 55),
            "rules_fg": (240, 240, 240),
        },
        "creep": {
            "base": (20, 32, 24),
            "bg_hex": "#142018",
            "gold": (180, 150, 190),
            "rules_fg": (200, 190, 210),
        },
        "hell": {
            "base": (42, 13, 18),
            "bg_hex": "#2a0d12",
            "gold": (255, 90, 50),
            "rules_fg": (255, 180, 120),
        },
        "celestial": {
            "base": (12, 35, 56),
            "bg_hex": "#0c2338",
            "gold": (0, 229, 255),
            "rules_fg": (220, 245, 255),
        },
    }

    MAX_FELT_CACHE = 2
    _SHARED_TILE_CACHE: dict[tuple[str, int], Any] = {}
    _SHARED_VIGNETTE_GRID: dict[tuple[int, int], Any] = {}
    _SHARED_FONT_CACHE: dict[tuple[str, int], Any] = {}
    _SHARED_ARC_CACHE: dict[tuple[int, int, int, tuple[int, int, int]], Any] = {}

    def __init__(self, parent: tkinter.Misc, background: str = PANEL_BACKGROUND_COLOR, display_profile: Optional[Any] = None, **kwargs):
        hl = kwargs.pop("highlightthickness", 0)
        bw = kwargs.pop("borderwidth", 0)
        rel = kwargs.pop("relief", "flat")
        self.padx = kwargs.pop("padx", 0)
        self.pady = kwargs.pop("pady", 0)
        default_w = int(getattr(display_profile, "window_w", 1280)) if display_profile is not None else 1280
        default_h = int(getattr(display_profile, "felt_height", 504)) if display_profile is not None else 504
        init_w = int(kwargs.get("width", default_w))
        init_h = int(kwargs.get("height", default_h))
        super().__init__(
            parent,
            background=background,
            highlightthickness=hl,
            borderwidth=bw,
            relief=rel,
            **kwargs
        )
        self.current_theme = "casino"
        self.scale_factor = float(getattr(display_profile, "art_scale", 1)) if display_profile is not None else 1.0
        self.pit_max_width: int = int(getattr(display_profile, "pit_max_width", 1920)) if display_profile is not None else 1920
        self._display_profile: Optional[Any] = display_profile
        self.canvas_width = init_w
        self.canvas_height = init_h
        self._bg_hex = background
        self._felt_photo: Optional[Any] = None
        self._felt_img: Optional[Any] = None
        self.payout_ratio: tuple[int, int] = (3, 2)
        self.dealer_hits_soft_17: bool = False
        self._felt_cache: OrderedDict[tuple[Any, ...], Any] = OrderedDict()
        self._shoe_visible: bool = False
        self._shoe_remaining: int = 208
        self._shoe_total: int = 208
        self._card_anim_timers: dict[int, str] = {}
        self._card_anim_targets: dict[int, tuple[int, int]] = {}
        self._card_anim_callbacks: dict[int, Any] = {}
        self.table_seats: int = 1
        self.seat_bets: dict[int, int] = {1: 0, 2: 0, 3: 0}
        self.seat_side_bets: dict[int, dict[str, int]] = {
            1: {"perfect_pairs": 0, "21_plus_3": 0},
            2: {"perfect_pairs": 0, "21_plus_3": 0},
            3: {"perfect_pairs": 0, "21_plus_3": 0},
        }
        self.active_turn_seat: Optional[int] = None
        self._halo_pulse_timer_id: Optional[str] = None
        self._halo_pulse_frame_idx: int = 0
        self._halo_frames_cache: dict[float, list[Any]] = {}
        self.on_spot_click_callback: Optional[Callable[[int, Optional[str]], None]] = None
        self.on_spot_clear_callback: Optional[Callable[[int], None]] = None
        self.on_chip_click_callback: Optional[Callable[[int], None]] = None
        self.on_chip_deduct_callback: Optional[Callable[[int], None]] = None
        self.available_bankroll: int = 1000
        self._hovered_denom: Optional[int] = None

        self.bind("<Button-1>", self._on_canvas_click)
        self.bind("<Button-3>", self._on_canvas_right_click)
        self.bind("<Motion>", self._on_felt_motion)
        self.bind("<Configure>", self._on_resize)
        self._redraw_felt()

    @property
    def art_scale(self) -> int:
        return 2 if getattr(self, "scale_factor", 1.0) >= 1.8 else 1

    def _on_resize(self, event):
        if event.width > 20 and (event.width != self.canvas_width or event.height != self.canvas_height):
            self.canvas_width = event.width
            self.canvas_height = event.height
            self._redraw_felt()
            if getattr(self, "_shoe_visible", False):
                self.draw_shoe_tray(self._shoe_remaining, self._shoe_total, getattr(self, "_shoe_cut_notice", False))

    def destroy(self):
        """Cancels all active pulse and card animation timers before destroying canvas."""
        if getattr(self, "_halo_pulse_timer_id", None):
            try:
                self.after_cancel(self._halo_pulse_timer_id)
            except Exception:
                pass
            self._halo_pulse_timer_id = None
        if hasattr(self, "_card_anim_timers"):
            for t_id in list(self._card_anim_timers.values()):
                try:
                    self.after_cancel(t_id)
                except Exception:
                    pass
            self._card_anim_timers.clear()
        super().destroy()

    def set_theme(self, theme: str):
        t = (theme or "casino").lower()
        if t not in self.THEME_COLORS:
            t = "casino"
        if self.current_theme != t:
            self.current_theme = t
            theme_cfg = self.THEME_COLORS.get(t, self.THEME_COLORS["casino"])
            self._bg_hex = theme_cfg["bg_hex"]
            self.configure(background=self._bg_hex)
            self._redraw_felt()
            if getattr(self, "_shoe_visible", False):
                self.draw_shoe_tray(self._shoe_remaining, self._shoe_total, getattr(self, "_shoe_cut_notice", False))

    def set_display_profile(self, profile: Any):
        """Updates TableFeltCanvas scale, pit_max_width, and profile reference atomically."""
        self._display_profile = profile
        new_scale = float(getattr(profile, "art_scale", 1))
        new_font_scale = float(getattr(profile, "table_font_scale", new_scale))
        new_pit_max = int(getattr(profile, "pit_max_width", 1920))
        old_font_scale = float(getattr(self, "_table_font_scale", self.scale_factor))
        changed = (
            (self.scale_factor != new_scale)
            or (self.pit_max_width != new_pit_max)
            or (abs(old_font_scale - new_font_scale) > 0.05)
        )
        self.scale_factor = new_scale
        self._table_font_scale = new_font_scale
        self.pit_max_width = new_pit_max
        if changed:
            self._felt_cache.clear()
            self._redraw_felt()
            if getattr(self, "_shoe_visible", False):
                self.draw_shoe_tray(self._shoe_remaining, self._shoe_total, getattr(self, "_shoe_cut_notice", False))
            if self.table_seats > 1:
                self.draw_betting_spots()
                self.draw_chip_tray()

    def set_scale(self, scale_factor: float):
        if self.scale_factor != scale_factor:
            self.scale_factor = scale_factor
            self.pit_max_width = 2560 if scale_factor >= 1.8 else 1920
            self._redraw_felt()
            if getattr(self, "_shoe_visible", False):
                self.draw_shoe_tray(self._shoe_remaining, self._shoe_total, getattr(self, "_shoe_cut_notice", False))

    def _get_baize_tile(self, theme: str, art_scale: int) -> Any:
        """Synthesizes a deterministic, edge-wrapping 128x128 RGB woven baize tile without numpy."""
        cache_key = (theme, art_scale)
        cached = self._SHARED_TILE_CACHE.get(cache_key)
        if cached is not None:
            return cached

        cfg = self.THEME_COLORS.get(theme, self.THEME_COLORS["casino"])
        br, bg, bb = cfg["base"]
        # Pre-boost base slightly (~1.06x) so multiplicative overhead-lamp vignette peaks cleanly at center
        r_base = min(255.0, br * 1.07 + 1.0)
        g_base = min(255.0, bg * 1.07 + 1.0)
        b_base = min(255.0, bb * 1.07 + 1.0)

        tile_sz = 128
        period = 4 * max(1, art_scale)
        rng = random.Random(42)
        buf = bytearray(tile_sz * tile_sz * 3)
        idx = 0
        for y in range(tile_sz):
            for x in range(tile_sz):
                grain = rng.gauss(0.0, 4.5)
                twill = 3.0 if ((x + y) % period == 0) else (-1.0 if ((x - y) % (period * 2) == 0) else 0.0)
                delta = grain + twill
                rv = int(r_base + delta * 0.75)
                gv = int(g_base + delta)
                bv = int(b_base + delta * 0.80)
                buf[idx] = 0 if rv < 0 else (255 if rv > 255 else rv)
                buf[idx + 1] = 0 if gv < 0 else (255 if gv > 255 else gv)
                buf[idx + 2] = 0 if bv < 0 else (255 if bv > 255 else bv)
                idx += 3

        tile = Image.frombytes("RGB", (tile_sz, tile_sz), bytes(buf))
        self._SHARED_TILE_CACHE[cache_key] = tile
        return tile

    def _get_vignette_base(self) -> Any:
        """Builds a cached 64x48 single-channel overhead-lamp dark-edge vignette alpha mask."""
        key = (64, 48)
        cached = self._SHARED_VIGNETTE_GRID.get(key)
        if cached is not None:
            return cached
        gw, gh = key
        cx, cy = gw * 0.5, gh * 0.46
        buf = bytearray(gw * gh)
        idx = 0
        for y in range(gh):
            dy = (y - cy) / (gh * 0.68)
            dy2 = dy * dy
            for x in range(gw):
                dx = (x - cx) / (gw * 0.58)
                dist = math.sqrt(dx * dx + dy2)
                darkness = max(0.0, min(0.22, 0.19 * dist - 0.03))
                buf[idx] = int(round(darkness * 255.0))
                idx += 1
        vig = Image.frombytes("L", (gw, gh), bytes(buf))
        self._SHARED_VIGNETTE_GRID[key] = vig
        return vig

    @classmethod
    def _get_cached_pil_font(cls, filename: str, px_size: int) -> Any:
        key = (filename, px_size)
        if key in cls._SHARED_FONT_CACHE:
            return cls._SHARED_FONT_CACHE[key]
        if ImageFont is None:
            return None
        path = FONTS_DIR / filename
        font_obj = ImageFont.truetype(str(path), px_size) if path.exists() else ImageFont.load_default()
        cls._SHARED_FONT_CACHE[key] = font_obj
        return font_obj

    def _generate_felt_image(self, w: int, h: int) -> Optional[Any]:
        if not PIL_AVAILABLE or Image is None or ImageDraw is None:
            return None

        cfg = self.THEME_COLORS.get(self.current_theme, self.THEME_COLORS["casino"])
        art_scale = 2 if self.scale_factor >= 1.8 else 1
        lw = max(1, (w + art_scale - 1) // art_scale)
        lh = max(1, (h + art_scale - 1) // art_scale)
        tile = self._get_baize_tile(self.current_theme, 1)

        # 1. Fast exponential doubling paste on 1x logical grid (lw, lh)
        base_img = Image.new("RGB", (lw, lh))
        tw, th = tile.size
        base_img.paste(tile, (0, 0))
        filled_w = min(tw, lw)
        while filled_w < lw:
            copy_w = min(filled_w, lw - filled_w)
            strip = base_img.crop((0, 0, copy_w, min(th, lh)))
            base_img.paste(strip, (filled_w, 0))
            filled_w += copy_w
        filled_h = min(th, lh)
        while filled_h < lh:
            copy_h = min(filled_h, lh - filled_h)
            band = base_img.crop((0, 0, lw, copy_h))
            base_img.paste(band, (0, filled_h))
            filled_h += copy_h

        # 2. Low-res 64x48 overhead-lamp dark-edge alpha vignette applied on logical grid
        resampling_ns = getattr(Image, "Resampling", Image)
        vig_small = self._get_vignette_base()
        vig_mask = vig_small.resize((lw, lh), resampling_ns.BILINEAR)
        base_img.paste((0, 0, 0), (0, 0, lw, lh), vig_mask)

        # Upscale logical pixel-art felt grain via NEAREST when art_scale == 2 (2x2 crunchy baize)
        if (lw, lh) != (w, h):
            felt_img = base_img.resize((w, h), resampling_ns.NEAREST)
        else:
            felt_img = base_img

        # 3. Center-Pit dealer arc (2x supersampled ribbon) + crisp pixel-font house rules
        lanes = resolve_center_pit_lanes(w, h, self._display_profile, self.table_seats)
        pit_left, cx, pit_right = lanes["pit_left"], lanes["pit_cx"], lanes["pit_right"]
        mid_y = lanes["mid_gap_y"] if h >= 320 else int(h * 0.42)
        pit_w = max(240, pit_right - pit_left)

        gold = cfg["gold"]
        tbl_fs = float(
            getattr(
                getattr(self, "_display_profile", None),
                "table_font_scale",
                getattr(self, "_table_font_scale", float(art_scale)),
            )
        )
        is_fhd = (art_scale == 1 and tbl_fs >= 1.35)
        rx = min(int(pit_w * 0.30), int((430 if is_fhd else 370) * art_scale))
        ry = min(max(int(36 * art_scale), int(h * 0.16)), int((112 if is_fhd else 96) * art_scale))

        compact_v = h < int(450 * art_scale)
        large_px = 32 if is_fhd else (24 * art_scale)
        small_px = 24 if is_fhd else (16 * art_scale)
        ins_px = 24 if is_fhd else (16 * art_scale)
        step_1 = 28 if is_fhd else int((18 if compact_v else 21) * art_scale)
        step_2 = 54 if is_fhd else int((35 if compact_v else 40) * art_scale)
        text_top_y = mid_y - (26 if is_fhd else int((19 if compact_v else 23) * art_scale))

        if rx > 30 and ry > 16:
            box_w = rx * 2 + int(16 * art_scale)
            box_h = ry + int(24 * art_scale)
            arc_key = (art_scale, rx, ry, tuple(gold))
            arc_down = self._SHARED_ARC_CACHE.get(arc_key)
            if arc_down is None:
                ss = 2
                arc_layer = Image.new("RGBA", (box_w * ss, box_h * ss), (0, 0, 0, 0))
                arc_draw = ImageDraw.Draw(arc_layer)
                pad_ss = int(8 * art_scale * ss)
                arc_draw.arc(
                    [pad_ss, -ry * ss + pad_ss, box_w * ss - pad_ss, ry * ss + pad_ss],
                    start=20,
                    end=160,
                    fill=(gold[0], gold[1], gold[2], 215),
                    width=max(2, int(2 * art_scale * ss)),
                )
                arc_down = arc_layer.resize((box_w, box_h), resampling_ns.BILINEAR)
                self._SHARED_ARC_CACHE[arc_key] = arc_down
            paste_x = cx - box_w // 2
            target_apex_y = text_top_y + step_2 + int((22 if is_fhd else 18) * art_scale)
            paste_y = max(0, target_apex_y - (ry + int(8 * art_scale)))
            felt_img.paste(arc_down, (paste_x, paste_y), arc_down)

        draw = ImageDraw.Draw(felt_img)
        try:
            draw.fontmode = "1"
        except Exception:
            pass

        try:
            font_large = self._get_cached_pil_font("Tiny5SC-Bold.ttf", large_px)
            font_small = self._get_cached_pil_font("Tiny5-Regular.ttf", small_px)
            font_ins = self._get_cached_pil_font("Tiny5SC-Bold.ttf", ins_px)
        except Exception:
            font_large = font_small = font_ins = None

        if font_large and font_small:
            num, den = self.payout_ratio
            bj_text = f"BLACKJACK PAYS {num} TO {den}"
            soft17_text = (
                "Dealer hits soft 17 and stands on hard 17"
                if self.dealer_hits_soft_17
                else "Dealer must stand on 17 and must draw to 16"
            )
            draw.text((cx, text_top_y), bj_text, fill=gold, font=font_large, anchor="mm")
            draw.text((cx, text_top_y + step_1), soft17_text, fill=cfg["rules_fg"], font=font_small, anchor="mm")
            draw.text((cx, text_top_y + step_2), "INSURANCE PAYS 2 TO 1", fill=gold, font=font_ins or font_small, anchor="mm")

        return felt_img

    def set_house_rules_display(self, payout_ratio: tuple[int, int], dealer_hits_soft_17: bool) -> None:
        """Updates table felt typography for Blackjack payout and Soft-17 rules."""
        norm_ratio = (
            (int(payout_ratio[0]), int(payout_ratio[1]))
            if isinstance(payout_ratio, (tuple, list))
            and len(payout_ratio) == 2
            and (int(payout_ratio[0]), int(payout_ratio[1])) in {(3, 2), (6, 5)}
            else (3, 2)
        )
        h17 = bool(dealer_hits_soft_17)
        if self.payout_ratio != norm_ratio or self.dealer_hits_soft_17 != h17:
            self.payout_ratio = norm_ratio
            self.dealer_hits_soft_17 = h17
            self._redraw_felt()
            try:
                self.sync_children_felt()
            except Exception:
                pass

    def _redraw_felt(self):
        w = max(20, self.canvas_width)
        h = max(20, self.canvas_height)
        key = (
            self.current_theme,
            w,
            h,
            int(self.art_scale),
            self.payout_ratio,
            self.dealer_hits_soft_17,
        )

        if key in self._felt_cache:
            self._felt_cache.move_to_end(key)
            self._felt_img, self._felt_photo = self._felt_cache[key]
        elif PIL_AVAILABLE and Image is not None and ImageTk is not None:
            try:
                img = self._generate_felt_image(w, h)
                if img:
                    self._felt_img = img
                    self._felt_photo = ImageTk.PhotoImage(img, master=self)
                    self._felt_cache[key] = (self._felt_img, self._felt_photo)
                    while len(self._felt_cache) > self.MAX_FELT_CACHE:
                        self._felt_cache.popitem(last=False)
            except Exception:
                self._felt_img = None
                self._felt_photo = None
        else:
            self._felt_img = None
            self._felt_photo = None

        if self._felt_photo:
            if not self.find_withtag("felt_bg"):
                self.create_image(0, 0, image=self._felt_photo, anchor="nw", tags="felt_bg")
            else:
                self.itemconfigure("felt_bg", image=self._felt_photo)
            self.tag_lower("felt_bg")
            try:
                self.sync_children_felt()
            except Exception:
                pass

    def get_felt_slice(self, x: int, y: int, width: int, height: int) -> Optional[Any]:
        """Returns safe PIL Image slice of active felt texture with no black borders."""
        if not getattr(self, "_felt_img", None) or not PIL_AVAILABLE or Image is None:
            return None
        try:
            cfg = self.THEME_COLORS.get(self.current_theme, self.THEME_COLORS["casino"])
            slice_img = Image.new("RGB", (width, height), cfg["base"])
            if self._felt_img.width >= width:
                src_x1 = max(0, min(x, self._felt_img.width - width))
            else:
                src_x1 = 0
            if self._felt_img.height >= height:
                src_y1 = max(0, min(y, self._felt_img.height - height))
            else:
                src_y1 = 0
            src_x2 = min(self._felt_img.width, src_x1 + width)
            src_y2 = min(self._felt_img.height, src_y1 + height)
            if src_x2 > src_x1 and src_y2 > src_y1:
                cropped = self._felt_img.crop((src_x1, src_y1, src_x2, src_y2))
                slice_img.paste(cropped, (0, 0))
            return slice_img
        except Exception:
            return None

    def sync_children_felt(self):
        """Synchronizes felt texture slices across child canvases and visualizers (both direct and nested)."""
        if not getattr(self, "_felt_img", None):
            return
        try:
            self.update_idletasks()
        except Exception:
            pass

        def _sync(parent, base_x: int, base_y: int):
            for child in parent.winfo_children():
                cx = base_x + child.winfo_x()
                cy = base_y + child.winfo_y()
                if hasattr(child, "sync_felt_background"):
                    if bool(child.winfo_manager()):
                        try:
                            child.sync_felt_background(self._felt_img, cx, cy)
                        except Exception:
                            pass
                    elif getattr(child, "_felt_coords", None) is not None:
                        try:
                            prev_x, prev_y = child._felt_coords
                            child.sync_felt_background(self._felt_img, prev_x, prev_y)
                        except Exception:
                            pass
                    else:
                        try:
                            child.sync_felt_background(self._felt_img, cx, cy)
                        except Exception:
                            pass
                if child.winfo_children():
                    _sync(child, cx, cy)

        _sync(self, 0, 0)

    # ------------------------------------------------------------------------
    # Layer 1: Visual Shoe Tray & Discard Rack
    # ------------------------------------------------------------------------
    def draw_shoe_tray(self, remaining: int = 208, total: int = 208, cut_notice: bool = False):
        """Renders 2.5D acrylic card shoe perched at the far right of the table horizon rail with counter plaque."""
        self._shoe_visible = True
        self._shoe_remaining = remaining
        self._shoe_total = total
        self._shoe_cut_notice = cut_notice
        self.delete("shoe_tray")
        if self.canvas_width < 350:
            return
        s = self.scale_factor
        tbl_fs = float(getattr(self, "_table_font_scale", s))
        shoe_w_mult = 1.35 if (s < 1.5 and tbl_fs >= 1.35) else 1.0
        w = self.canvas_width
        _, _, pit_right = resolve_pit_bounds(w, getattr(self, "pit_max_width", w))

        shoe_cfg = get_ui_layout("table_felt", "shoe_tray")
        sw = int(shoe_cfg.get("width", 126) * s * shoe_w_mult)
        sh = int(shoe_cfg.get("height", 28) * s)  # Compact, sleek profile sitting right at the horizon rail
        sx = pit_right - sw - int(shoe_cfg.get("offset_right", 14) * s)
        sy = int(shoe_cfg.get("offset_top", 3) * s)   # Flush with the top horizon rail

        # Clear acrylic shoe housing with subtle metallic bevel
        self.create_rectangle(sx, sy, sx + sw, sy + sh, fill="#0d2419", outline="#2e543e", width=max(1, int(1.5 * s)), tags="shoe_tray")
        self.create_rectangle(sx + 1, sy + 1, sx + sw - 1, sy + sh - 1, fill="", outline="#3a684c", width=1, tags="shoe_tray")

        # Stack depth based on remaining cards (clamp total >= remaining against custom/rigged shoes)
        total = max(int(total), int(remaining))
        ratio = max(0.0, min(1.0, remaining / max(1, total)))
        stack_w = max(4, int((sw - 14) * ratio))

        # Cards remaining block
        self.create_rectangle(sx + 4, sy + 4, sx + 4 + stack_w, sy + sh - 4, fill="#f5f5f0", outline="#b0bec5", tags="shoe_tray")
        if stack_w > 10:
            for step in range(sx + 8, sx + 4 + stack_w, max(4, int(5 * s))):
                self.create_line(step, sy + 4, step, sy + sh - 4, fill="#cfd8dc", tags="shoe_tray")

        # Red plastic cut-card penetration indicator
        cut_x = sx + 4 + int((sw - 14) * 0.25)
        self.create_line(cut_x, sy + 2, cut_x, sy + sh - 2, fill="#ff1744", width=max(1, int(2 * s)), tags="shoe_tray")

        # Front roller / brass exit mouth on the left
        self.create_rectangle(sx + 1, sy + 2, sx + int(5 * s), sy + sh - 2, fill="#b58830", outline="#ffd700", tags="shoe_tray")

        # --------------------------------------------------------------------
        # Plaque: Cardstock shoe count readout directly beneath the shoe tray
        # --------------------------------------------------------------------
        plaque_cfg = shoe_cfg.get("plaque", {})
        ph = int(plaque_cfg.get("height", 20) * s)
        py1 = sy + sh + int(plaque_cfg.get("offset_y", 3) * s)
        py2 = py1 + ph
        bx1 = sx
        bx2 = sx + sw

        bg_col = plaque_cfg.get("background", "")
        if bg_col in ("transparent", "none", None):
            bg_col = ""
        border_col = plaque_cfg.get("cut_border" if cut_notice else "border", "")
        if border_col in ("transparent", "none", None):
            border_col = ""
        inner_border_col = plaque_cfg.get("inner_border", "")
        if inner_border_col in ("transparent", "none", None):
            inner_border_col = ""
        text_col = plaque_cfg.get("cut_text_color" if cut_notice else "text_color", "#ffd700")
        font_elem = plaque_cfg.get("font_element", "shoe_counter")
        f_shoe = get_element_font(font_elem, scale=tbl_fs)

        # Outer beveled plaque border (only drawn if a fill or outline is configured)
        if bg_col or border_col:
            self.create_rectangle(bx1, py1, bx2, py2, fill=bg_col, outline=border_col, width=max(1, int(1.5 * s)), tags="shoe_tray")
        # Subtle inset cardstock border (only drawn if inner outline is configured)
        if inner_border_col:
            self.create_rectangle(bx1 + 1, py1 + 1, bx2 - 1, py2 - 1, fill="", outline=inner_border_col, width=1, tags="shoe_tray")

        # Text label (e.g. "Shoe: 196/208" or "Shoe: 32/208 [Cut]") with 1px drop shadow for baize legibility
        cut_text = " [Cut]" if cut_notice else ""
        label_text = f"Shoe: {remaining}/{total}{cut_text}"
        tx, ty = (bx1 + bx2) // 2, (py1 + py2) // 2
        self.create_text(tx + 1, ty + 1, text=label_text, fill="#040e07", font=f_shoe, tags="shoe_tray")
        self.create_text(tx, ty, text=label_text, fill=text_col, font=f_shoe, tags="shoe_tray")

    def draw_discard_rack(self, discarded: int = 0, total: int = 208):
        """Optional discard rack - renders without opaque black box so table felt is not obscured."""
        self.delete("discard_rack")
        if discarded <= 0 or self.canvas_width < 500:
            return
        s = self.scale_factor
        w = self.canvas_width
        _, _, pit_right = resolve_pit_bounds(w, getattr(self, "pit_max_width", w))
        dw = int(60 * s)
        dh = int(24 * s)
        dx = pit_right - int(175 * s)
        dy = int(3 * s)
        ratio = max(0.0, min(1.0, discarded / max(1, total)))
        d_stack_w = max(3, int((dw - 8) * ratio))
        self.create_rectangle(dx, dy, dx + dw, dy + dh, fill="", outline="#2e543e", width=max(1, int(1.5 * s)), tags="discard_rack")
        self.create_rectangle(dx + 4, dy + 3, dx + 4 + d_stack_w, dy + dh - 3, fill="#e0e0dc", outline="#9e9e9e", tags="discard_rack")

    def update_shoe_penetration(self, remaining: int, total: int, cut_notice: bool = False):
        """Updates shoe tray to reflect live card penetration and count plaque at the horizon rail."""
        self._shoe_visible = True
        self._shoe_remaining = remaining
        self._shoe_total = total
        self._shoe_cut_notice = cut_notice
        self.draw_shoe_tray(remaining, total, cut_notice)

    def clear_shoe_overlay(self):
        """Cleans up shoe tray and discard rack canvas items."""
        self._shoe_visible = False
        self.delete("shoe_tray")
        self.delete("discard_rack")

    # ------------------------------------------------------------------------
    # Layer 3: Canvas Card Sprites
    # ------------------------------------------------------------------------
    # ------------------------------------------------------------------------
    # Layer 3: Canvas Card Sprites & Slide Trajectories
    # ------------------------------------------------------------------------
    def get_shoe_mouth_coords(self) -> tuple[int, int]:
        """Calculates the (x, y) exit mouth coordinates of the acrylic card shoe inside pit_right."""
        s = self.scale_factor
        tbl_fs = float(getattr(self, "_table_font_scale", s))
        shoe_w_mult = 1.35 if (s < 1.5 and tbl_fs >= 1.35) else 1.0
        w = max(20, self.canvas_width)
        _, _, pit_right = resolve_pit_bounds(w, getattr(self, "pit_max_width", w))
        shoe_cfg = get_ui_layout("table_felt", "shoe_tray")
        sw = int(shoe_cfg.get("width", 126) * s * shoe_w_mult)
        sx = pit_right - sw - int(shoe_cfg.get("offset_right", 14) * s)
        sy = int(shoe_cfg.get("offset_top", 3) * s)
        # Exit mouth is on the left side of the shoe tray
        exit_x = sx + int(3 * s)
        exit_y = sy + int(14 * s)
        return (exit_x, exit_y)

    @staticmethod
    def compute_slide_trajectory(
        start_x: int, start_y: int, target_x: int, target_y: int,
        steps: int = 9, arc_lift: int = 18
    ) -> list[tuple[int, int]]:
        """
        Calculates a smooth quadratic Bezier trajectory with ease-out interpolation
        from (start_x, start_y) to (target_x, target_y).
        Control point elevates the card slightly above the direct line.
        """
        if steps <= 1:
            return [(target_x, target_y)]

        ctrl_x = int((start_x + target_x) / 2.0)
        ctrl_y = int(min(start_y, target_y) - arc_lift)

        points: list[tuple[int, int]] = []
        for step in range(1, steps + 1):
            t = step / float(steps)
            # Quadratic ease-out: u = 1 - (1 - t)^2
            u = 1.0 - (1.0 - t) * (1.0 - t)
            bx = (1.0 - u) * (1.0 - u) * start_x + 2.0 * (1.0 - u) * u * ctrl_x + u * u * target_x
            by = (1.0 - u) * (1.0 - u) * start_y + 2.0 * (1.0 - u) * u * ctrl_y + u * u * target_y
            points.append((int(round(bx)), int(round(by))))

        # Guarantee exact endpoint arrival on the final frame
        points[-1] = (target_x, target_y)
        return points

    def draw_card_sprite(self, image: Any, x: int, y: int, tags: str = "card_sprite") -> int:
        """Renders a card image item directly onto the felt canvas."""
        return self.create_image(x, y, image=image, anchor="nw", tags=tags)

    def move_card_sprite(self, item_id: int, target_x: int, target_y: int):
        """Reposition a card sprite on the felt canvas."""
        self.coords(item_id, target_x, target_y)

    def animate_card_slide(
        self,
        item_id: int,
        start_x: int,
        start_y: int,
        target_x: int,
        target_y: int,
        duration_ms: int = 144,
        interval_ms: int = 16,
        on_complete: Optional[Callable[[], None]] = None,
        force_animate: bool = False,
    ) -> None:
        """
        Animates a card sprite along a quadratic trajectory to (target_x, target_y).
        When the window is mapped or force_animate is True, runs 16ms non-blocking ticks.
        Otherwise (headless/withdrawn test mode), snaps immediately to target_x, target_y.
        """
        # Cancel any previous animation for this item
        self.cancel_card_animation(item_id)

        # Immediate snap condition
        is_mapped = bool(self.winfo_exists() and self.winfo_ismapped())
        if not is_mapped and not force_animate:
            self.move_card_sprite(item_id, target_x, target_y)
            if on_complete:
                try:
                    on_complete()
                except Exception:
                    pass
            return

        steps = max(2, int(duration_ms / max(1, interval_ms)))
        s = getattr(self, "scale_factor", 1.0)
        arc_lift = int(18 * s)
        trajectory = self.compute_slide_trajectory(start_x, start_y, target_x, target_y, steps=steps, arc_lift=arc_lift)

        self._card_anim_targets[item_id] = (target_x, target_y)
        if on_complete:
            self._card_anim_callbacks[item_id] = on_complete

        # Position at starting point
        self.move_card_sprite(item_id, start_x, start_y)

        def _step_anim(traj_index: int = 0):
            if item_id not in self._card_anim_targets:
                return
            if traj_index < len(trajectory):
                cur_x, cur_y = trajectory[traj_index]
                self.move_card_sprite(item_id, cur_x, cur_y)
                timer_id = self.after(interval_ms, lambda: _step_anim(traj_index + 1))
                self._card_anim_timers[item_id] = timer_id
            else:
                self.move_card_sprite(item_id, target_x, target_y)
                cb = self._card_anim_callbacks.pop(item_id, None)
                self._card_anim_timers.pop(item_id, None)
                self._card_anim_targets.pop(item_id, None)
                if cb:
                    try:
                        cb()
                    except Exception:
                        pass

        timer_id = self.after(interval_ms, lambda: _step_anim(0))
        self._card_anim_timers[item_id] = timer_id

    def cancel_card_animation(self, item_id: int, snap_to_target: bool = True):
        """Cancels an active slide animation for a specific card sprite."""
        timer_id = self._card_anim_timers.pop(item_id, None)
        if timer_id:
            try:
                self.after_cancel(timer_id)
            except Exception:
                pass
        target = self._card_anim_targets.pop(item_id, None)
        if snap_to_target and target:
            try:
                self.move_card_sprite(item_id, target[0], target[1])
            except Exception:
                pass
        cb = self._card_anim_callbacks.pop(item_id, None)
        if snap_to_target and cb:
            try:
                cb()
            except Exception:
                pass

    def cancel_card_animations(self, snap_to_target: bool = True):
        """Cancels all active card slide animation timers."""
        for item_id in list(self._card_anim_timers.keys()):
            self.cancel_card_animation(item_id, snap_to_target=snap_to_target)
        self._card_anim_timers.clear()
        self._card_anim_targets.clear()
        self._card_anim_callbacks.clear()

    def cancel_animations(self):
        """Quiesces all active card slide and turn-halo timers before profile transitions."""
        self.cancel_card_animations(snap_to_target=False)
        if getattr(self, "_halo_pulse_timer_id", None):
            try:
                self.after_cancel(self._halo_pulse_timer_id)
            except Exception:
                pass
            self._halo_pulse_timer_id = None

    def has_active_card_animations(self) -> bool:
        """Returns True if any card slide animations are currently in-flight."""
        return bool(self._card_anim_timers)

    def clear_card_sprites(self, tag: str = "card_sprite"):
        """Removes canvas card sprites matching the specified tag, cancelling active animations."""
        # Find item IDs matching tag
        items = self.find_withtag(tag)
        for item_id in items:
            self.cancel_card_animation(item_id, snap_to_target=False)
        self.delete(tag)

    # ------------------------------------------------------------------------
    # Layer 4: Multi-Seat Betting Spots & Geometric Hit Dispatching
    # ------------------------------------------------------------------------
    def _get_live_seat_origin(self, seat_idx: int) -> dict[str, int]:
        """Resolves final pixel seat coordinates for the live canvas dimensions and active DisplayProfile."""
        w = max(100, self.winfo_width() if self.winfo_width() > 1 else self.canvas_width)
        h = max(100, self.winfo_height() if self.winfo_height() > 1 else self.canvas_height)
        return get_seat_origin(
            seat_idx,
            canvas_w=w,
            canvas_h=h,
            profile=getattr(self, "_display_profile", None),
        )

    def set_table_seats(self, seats: int):
        """Sets the active table seats configuration (1 or 3) and refreshes felt geometry and spots."""
        new_seats = max(1, min(3, seats))
        changed = (getattr(self, "table_seats", 1) != new_seats)
        self.table_seats = new_seats
        if changed:
            self._felt_cache.clear()
            self._redraw_felt()
        self.draw_betting_spots()

    def get_edge_baize_hex(self) -> str:
        """Returns the edge-vignetted baize hex matching the current felt theme for seamless wing frame blending."""
        cfg = self.THEME_COLORS.get(self.current_theme, self.THEME_COLORS["casino"])
        r, g, b = cfg["base"]
        # Outer edge vignette factor (~0.88x base RGB)
        er, eg, eb = max(0, int(r * 0.88)), max(0, int(g * 0.88)), max(0, int(b * 0.88))
        return f"#{er:02x}{eg:02x}{eb:02x}"

    def update_seat_bet(self, seat_idx: int, amount: int):
        """Updates staged bet display for a seat and refreshes spots."""
        self.seat_bets[seat_idx] = amount
        self.draw_betting_spots()

    def update_seat_side_bet(self, seat_idx: int, bet_type: str, amount: int):
        """Updates staged side bet display for a seat and refreshes spots."""
        if seat_idx in self.seat_side_bets and bet_type in self.seat_side_bets[seat_idx]:
            self.seat_side_bets[seat_idx][bet_type] = amount
            self.draw_betting_spots()

    def draw_betting_spots(self):
        """Draws the felt betting circles, flanking side-bet spots, and 2.5D chip stacks in 3-seat mode."""
        self.delete("betting_spot")
        self.delete("turn_halo")
        self.delete("turn_halo_pulse")
        if getattr(self, "_halo_pulse_timer_id", None):
            try:
                self.after_cancel(self._halo_pulse_timer_id)
            except Exception:
                pass
            self._halo_pulse_timer_id = None

        # In 1-Seat Mode, ChipVisualizer handles betting visuals; draw zero felt rings.
        if self.table_seats == 1:
            return

        from ui_chip_renderer import draw_felt_chip_stack
        s = getattr(self, "scale_factor", 1.0)
        tbl_fs = float(getattr(self, "_table_font_scale", s))
        spot_mult = 1.25 if (s < 1.5 and tbl_fs >= 1.35) else 1.0
        visible_seats = [1, 2, 3]

        for s_idx in visible_seats:
            origin = self._get_live_seat_origin(s_idx)
            cx = int(origin["x"])
            cy = int(origin["y"])
            sb_offset_x = int(origin.get("side_bet_offset_x", int(76 * s)))
            side_y = int(origin.get("side_bet_y", cy))

            # 1. Left Flanking Spot: Perfect Pairs (cx - sb_offset_x)
            pp_x = cx - sb_offset_x
            pp_rx, pp_ry = int(32 * s * spot_mult), int(15 * s * spot_mult)
            pp_in_rx, pp_in_ry = int(28 * s * spot_mult), int(12 * s * spot_mult)
            self.create_oval(
                pp_x - pp_rx, side_y - pp_ry, pp_x + pp_rx, side_y + pp_ry,
                outline="#d4af37", width=max(1, int(1.5 * s)), dash=(3, 3), fill="",
                tags=("betting_spot", f"spot_pp_{s_idx}")
            )
            self.create_oval(
                pp_x - pp_in_rx, side_y - pp_in_ry, pp_x + pp_in_rx, side_y + pp_in_ry,
                outline="#8a6d1b", width=1, dash=(2, 2), fill="",
                tags=("betting_spot", f"spot_pp_inner_{s_idx}")
            )
            pp_bet = self.seat_side_bets.get(s_idx, {}).get("perfect_pairs", 0)
            if pp_bet > 0:
                draw_felt_chip_stack(self, pp_x, side_y, pp_bet, tag_prefix=f"chip_pp_{s_idx}", scale=s * 0.8, compact=True)
            else:
                self.create_text(
                    pp_x, side_y, text="PAIRS", fill="#d4b44a",
                    font=get_element_font("betting_spot_watermark", scale=tbl_fs),
                    tags=("betting_spot", f"spot_pp_txt_{s_idx}")
                )

            # 2. Center Main Betting Spot (cx, cy)
            rx, ry = int(50 * s * spot_mult), int(19 * s * spot_mult)
            rx_in, ry_in = int(44 * s * spot_mult), int(15 * s * spot_mult)
            self.create_oval(
                cx - rx, cy - ry, cx + rx, cy + ry,
                outline="#d4af37", width=max(1, int(2 * s)), dash=(4, 3), fill="",
                tags=("betting_spot", f"spot_main_{s_idx}")
            )
            self.create_oval(
                cx - rx_in, cy - ry_in, cx + rx_in, cy + ry_in,
                outline="#8a6d1b", width=1, dash=(2, 2), fill="",
                tags=("betting_spot", f"spot_main_inner_{s_idx}")
            )
            main_bet = self.seat_bets.get(s_idx, 0)
            if main_bet > 0:
                draw_felt_chip_stack(self, cx, cy, main_bet, tag_prefix=f"chip_main_{s_idx}", scale=s * 0.95, compact=False)
            else:
                self.create_text(
                    cx, cy, text=f"SEAT {s_idx}", fill="#d4b44a",
                    font=get_element_font("betting_spot_watermark", scale=tbl_fs),
                    tags=("betting_spot", f"spot_txt_{s_idx}")
                )

            # 3. Right Flanking Spot: 21+3 (cx + sb_offset_x)
            t13_x = cx + sb_offset_x
            t13_rx, t13_ry = int(32 * s * spot_mult), int(15 * s * spot_mult)
            t13_in_rx, t13_in_ry = int(28 * s * spot_mult), int(12 * s * spot_mult)
            self.create_oval(
                t13_x - t13_rx, side_y - t13_ry, t13_x + t13_rx, side_y + t13_ry,
                outline="#d4af37", width=max(1, int(1.5 * s)), dash=(3, 3), fill="",
                tags=("betting_spot", f"spot_t13_{s_idx}")
            )
            self.create_oval(
                t13_x - t13_in_rx, side_y - t13_in_ry, t13_x + t13_in_rx, side_y + t13_in_ry,
                outline="#8a6d1b", width=1, dash=(2, 2), fill="",
                tags=("betting_spot", f"spot_t13_inner_{s_idx}")
            )
            t13_bet = self.seat_side_bets.get(s_idx, {}).get("21_plus_3", 0)
            if t13_bet > 0:
                draw_felt_chip_stack(self, t13_x, side_y, t13_bet, tag_prefix=f"chip_t13_{s_idx}", scale=s * 0.8, compact=True)
            else:
                self.create_text(
                    t13_x, side_y, text="21+3", fill="#d4b44a",
                    font=get_element_font("betting_spot_watermark", scale=tbl_fs),
                    tags=("betting_spot", f"spot_t13_txt_{s_idx}")
                )

        if self.active_turn_seat is not None and self.table_seats == 3:
            self._render_turn_halo(self.active_turn_seat)

    def _get_halo_pulse_frames(self, s: float) -> list[Any]:
        """Pre-renders 16 cached RGBA PhotoImage frames of a 5px feathered pulsing glow halo."""
        if not PIL_AVAILABLE or Image is None or ImageTk is None or ImageDraw is None or ImageFilter is None:
            return []
        scale_key = round(float(s), 2)
        if scale_key in self._halo_frames_cache:
            return self._halo_frames_cache[scale_key]

        rx = int(54 * s)
        ry = int(22 * s)
        pad = int(14 * s)
        img_w = (rx + pad) * 2
        img_h = (ry + pad) * 2
        cx = img_w // 2
        cy = img_h // 2
        thickness = max(3, int(5 * s))

        num_frames = 16
        frames = []
        for i in range(num_frames):
            theta = 2.0 * math.pi * (i / num_frames)
            # Smooth sinusoidal alpha pulse between 0.18 and 0.82
            alpha_ratio = 0.18 + 0.64 * (0.5 + 0.5 * math.sin(theta))
            alpha_byte = int(alpha_ratio * 255)

            im = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(im)
            draw.ellipse(
                [cx - rx, cy - ry, cx + rx, cy + ry],
                outline=(20, 250, 138, alpha_byte),
                width=thickness,
            )
            feathered = im.filter(ImageFilter.GaussianBlur(radius=1.8 * s))
            try:
                photo = ImageTk.PhotoImage(feathered, master=self)
                frames.append(photo)
            except Exception:
                pass

        if len(frames) == num_frames:
            self._halo_frames_cache[scale_key] = frames
            return frames
        return frames

    def draw_active_turn_halo(self, seat_index: Optional[int]):
        """Draws a highlighted gold/emerald glow halo and feathered pulsing ring around the active turn seat betting spot."""
        if getattr(self, "_halo_pulse_timer_id", None):
            try:
                self.after_cancel(self._halo_pulse_timer_id)
            except Exception:
                pass
            self._halo_pulse_timer_id = None

        self.active_turn_seat = seat_index
        self.delete("turn_halo")
        self.delete("turn_halo_pulse")
        if seat_index is not None and self.table_seats == 3:
            self._render_turn_halo(seat_index)

    def _render_turn_halo(self, seat_index: int):
        if self.table_seats == 1 or seat_index not in (1, 2, 3):
            return
        s = getattr(self, "scale_factor", 1.0)
        origin = self._get_live_seat_origin(seat_index)
        cx, cy = int(origin["x"]), int(origin["y"])
        rx, ry = int(54 * s), int(22 * s)

        # 1. Base dashed emerald boundary disc
        self.create_oval(
            cx - rx, cy - ry, cx + rx, cy + ry,
            outline="#00e676", width=max(2, int(2.5 * s)), dash=(4, 2), fill="",
            tags=("betting_spot", "turn_halo")
        )

        # 2. Feathered transparent pulsing halo sprite
        frames = self._get_halo_pulse_frames(s)
        if frames:
            self._halo_pulse_frame_idx = 0
            photo = frames[0]
            self.create_image(
                cx, cy, image=photo,
                tags=("betting_spot", "turn_halo", "turn_halo_pulse")
            )
            # Position the soft glow under the betting spot text and chips
            spot_tag = f"spot_main_{seat_index}"
            if self.find_withtag(spot_tag):
                self.tag_lower("turn_halo_pulse", spot_tag)
            self._start_halo_pulse()

    def _start_halo_pulse(self):
        if getattr(self, "_halo_pulse_timer_id", None):
            try:
                self.after_cancel(self._halo_pulse_timer_id)
            except Exception:
                pass
            self._halo_pulse_timer_id = None
        if self.active_turn_seat is None or self.table_seats == 1:
            return
        self._schedule_halo_pulse_step()

    def _schedule_halo_pulse_step(self):
        # 16 frames per 1400ms cycle -> ~88ms per frame
        interval_ms = 88
        try:
            self._halo_pulse_timer_id = self.after(interval_ms, self._halo_pulse_step)
        except Exception:
            self._halo_pulse_timer_id = None

    def _halo_pulse_step(self):
        self._halo_pulse_timer_id = None
        if self.active_turn_seat is None or self.table_seats == 1:
            self.delete("turn_halo_pulse")
            return
        s = getattr(self, "scale_factor", 1.0)
        frames = self._get_halo_pulse_frames(s)
        if not frames:
            return
        self._halo_pulse_frame_idx = (self._halo_pulse_frame_idx + 1) % len(frames)
        try:
            self.itemconfigure("turn_halo_pulse", image=frames[self._halo_pulse_frame_idx])
            self._schedule_halo_pulse_step()
        except Exception:
            self._halo_pulse_timer_id = None

    def draw_chip_tray(self, available_bankroll: Optional[int] = None):
        """Draws the 5 interactive denomination 2.5D chip piles ($5, $25, $100, $500, $1K) on the lower felt baize in 3-seat mode."""
        self.delete("felt_chip_tray")
        if self.table_seats == 1:
            return

        if available_bankroll is not None:
            self.available_bankroll = max(0, int(available_bankroll))
        avail = self.available_bankroll

        s = getattr(self, "scale_factor", 1.0)
        tbl_fs = float(getattr(self, "_table_font_scale", s))
        tray_mult = 1.2 if (s < 1.5 and tbl_fs >= 1.35) else 1.0
        from config import CHIP_STYLES
        from rules import breakdown_bankroll_piles
        from ui_chip_renderer import draw_single_25d_chip

        w = max(100, self.winfo_width() if self.winfo_width() > 1 else self.canvas_width)
        h = max(100, self.winfo_height() if self.winfo_height() > 1 else self.canvas_height)
        cx = w // 2
        base_y = max(int(260 * s), h - int((48 if tray_mult > 1.0 else 44) * s))

        denoms = (5, 25, 100, 500, 1000)
        piles = breakdown_bankroll_piles(avail)
        spacing = int(52 * s * tray_mult)
        total_span = spacing * (len(denoms) - 1)
        start_x = cx - (total_span // 2)

        for idx, denom in enumerate(denoms):
            col_x = start_x + (idx * spacing)
            count = piles.get(denom, 0)
            style = CHIP_STYLES.get(denom, CHIP_STYLES[5])
            pile_tag = f"bank_pile_{denom}"
            tags = ("felt_chip_tray", pile_tag, f"chip_tray_pile_{denom}")

            # Draw stacked chip cylinder
            visible_count = min(count, 5) if count > 0 else 1
            for c_idx in range(visible_count):
                chip_y = base_y - int(c_idx * 3 * s)
                is_top = (c_idx == visible_count - 1)
                draw_single_25d_chip(
                    self, col_x, chip_y, denom, style,
                    scale=s * 0.9,
                    count=count if is_top else None,
                    tags=tags,
                    compact=False,
                )

            # Denomination label below
            short_lbl = "$1K" if denom == 1000 else f"${denom}"
            lbl_y = base_y + int(18 * s)
            self.create_text(
                col_x, lbl_y, text=short_lbl, fill="#ffd700",
                font=get_element_font("chip_denomination_label", scale=s),
                tags=("felt_chip_tray", pile_tag)
            )

        # Bankroll and instruction badge below denomination labels
        badge_y = base_y + int((35 if tray_mult > 1.0 else 33) * s)
        self.create_text(
            cx, badge_y,
            text=f"CHIPS: ${avail:,}  (L-Click: Bet on active seat | R-Click: Deduct)",
            fill="#ffd700",
            font=get_element_font("chip_bet_badge", scale=s),
            tags=("felt_chip_tray", "felt_tray_badge")
        )

    def trigger_chip_tray_click(self, denom: int):
        """Invokes chip staging callback when a 2.5D chip pile on the felt is clicked."""
        if callable(self.on_chip_click_callback):
            self.on_chip_click_callback(denom)

    def trigger_chip_tray_deduct(self, denom: int):
        """Invokes chip deduction callback when a 2.5D chip pile on the felt is right-clicked."""
        if callable(self.on_chip_deduct_callback):
            self.on_chip_deduct_callback(denom)

    def _get_chip_tray_col_coords(self) -> tuple[int, int, int, tuple[int, ...]]:
        s = getattr(self, "scale_factor", 1.0)
        tbl_fs = float(getattr(self, "_table_font_scale", s))
        tray_mult = 1.2 if (s < 1.5 and tbl_fs >= 1.35) else 1.0
        w = max(100, self.winfo_width() if self.winfo_width() > 1 else self.canvas_width)
        h = max(100, self.winfo_height() if self.winfo_height() > 1 else self.canvas_height)
        cx = w // 2
        base_y = max(int(260 * s), h - int((48 if tray_mult > 1.0 else 44) * s))
        denoms = (5, 25, 100, 500, 1000)
        spacing = int(52 * s * tray_mult)
        total_span = spacing * (len(denoms) - 1)
        start_x = cx - (total_span // 2)
        return start_x, base_y, spacing, denoms

    def _on_felt_motion(self, event):
        if self.table_seats == 1:
            return
        s = getattr(self, "scale_factor", 1.0)
        start_x, base_y, spacing, denoms = self._get_chip_tray_col_coords()

        hovered = None
        for idx, denom in enumerate(denoms):
            col_x = start_x + (idx * spacing)
            if abs(event.x - col_x) <= int(20 * s) and abs(event.y - base_y) <= int(22 * s):
                hovered = denom
                break

        if hovered != self._hovered_denom:
            lift = max(2, int(3 * s))
            if self._hovered_denom is not None:
                self.move(f"bank_pile_{self._hovered_denom}", 0, lift)
            if hovered is not None:
                self.move(f"bank_pile_{hovered}", 0, -lift)
            self._hovered_denom = hovered

        if hovered is not None:
            try:
                self.configure(cursor="hand2")
            except Exception:
                pass
        else:
            try:
                self.configure(cursor="")
            except Exception:
                pass

    def _on_canvas_click(self, event):
        """Geometric coordinate hit dispatcher for left clicks on 3-seat betting spots and chip tray."""
        if self.table_seats == 1:
            return
        s = getattr(self, "scale_factor", 1.0)

        # 1. Check Chip Tray clicks on lower baize
        start_x, base_y, spacing, denoms = self._get_chip_tray_col_coords()
        for idx, denom in enumerate(denoms):
            col_x = start_x + (idx * spacing)
            if abs(event.x - col_x) <= int(20 * s) and abs(event.y - base_y) <= int(22 * s):
                self.trigger_chip_tray_click(denom)
                return

        # 2. Check 3-Seat Betting Spots
        for s_idx in (1, 2, 3):
            origin = self._get_live_seat_origin(s_idx)
            cx = int(origin["x"])
            cy = int(origin["y"])
            sb_offset_x = int(origin.get("side_bet_offset_x", int(76 * s)))
            side_y = int(origin.get("side_bet_y", cy))

            # Check Perfect Pairs side bet (left flank)
            pp_x = cx - sb_offset_x
            if ((event.x - pp_x) / (32.0 * s)) ** 2 + ((event.y - side_y) / (16.0 * s)) ** 2 <= 1.25:
                if self.on_spot_click_callback:
                    self.on_spot_click_callback(s_idx, "perfect_pairs")
                return

            # Check 21+3 side bet (right flank)
            t13_x = cx + sb_offset_x
            if ((event.x - t13_x) / (32.0 * s)) ** 2 + ((event.y - side_y) / (16.0 * s)) ** 2 <= 1.25:
                if self.on_spot_click_callback:
                    self.on_spot_click_callback(s_idx, "21_plus_3")
                return

            # Check Main Betting Spot (center)
            if ((event.x - cx) / (50.0 * s)) ** 2 + ((event.y - cy) / (20.0 * s)) ** 2 <= 1.35:
                if self.on_spot_click_callback:
                    self.on_spot_click_callback(s_idx, None)
                return

    def _on_canvas_right_click(self, event):
        """Geometric coordinate hit dispatcher for right clicks (clearing seat wager or deducting chip)."""
        if self.table_seats == 1:
            return
        s = getattr(self, "scale_factor", 1.0)

        # 1. Check Chip Tray right-clicks (deduct denomination)
        start_x, base_y, spacing, denoms = self._get_chip_tray_col_coords()
        for idx, denom in enumerate(denoms):
            col_x = start_x + (idx * spacing)
            if abs(event.x - col_x) <= int(20 * s) and abs(event.y - base_y) <= int(22 * s):
                self.trigger_chip_tray_deduct(denom)
                return

        # 2. Check 3-Seat Betting Spots (clear wager)
        for s_idx in (1, 2, 3):
            origin = self._get_live_seat_origin(s_idx)
            cx = int(origin["x"])
            cy = int(origin["y"])
            if abs(event.x - cx) <= int(80 * s) and abs(event.y - cy) <= int(32 * s):
                if self.on_spot_clear_callback:
                    self.on_spot_clear_callback(s_idx)
                return


class MahoganyRailCanvas(tkinter.Canvas):
    """
    Renders the bottom mahogany wood and leather armrest rail framing the card table.
    Houses the contextual player control docks (Betting Phase vs In-Play Phase) with brass rivets and gold trim.
    """

    def __init__(
        self,
        master,
        height: int = 72,
        background: str = "#140a05",
        display_profile: Optional[Any] = None,
        art_scale: Optional[int] = None,
        **kwargs,
    ):
        eff_art = (
            int(getattr(display_profile, "art_scale", 1))
            if display_profile is not None
            else (int(art_scale) if art_scale is not None else 1)
        )
        eff_h = int(getattr(display_profile, "rail_h", height)) if display_profile is not None else height
        super().__init__(
            master, height=eff_h, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.display_profile = display_profile
        self.grid_propagate(False)
        self.pack_propagate(False)
        self.rail_height = eff_h
        self.art_scale: int = max(1, eff_art)
        self.scale_factor: float = float(self.art_scale)
        self._current_width: int = 0
        self._panel: Optional[Any] = None
        self.bind("<Configure>", self._on_configure)
        self._draw_rail()

    def _draw_rail(self):
        w = max(100, self.winfo_width() if self.winfo_width() > 1 else 1280)
        h = self.rail_height
        s = getattr(self, "scale_factor", 1.0)
        self.delete("rail_bg")

        try:
            from pixel_ui import CanvasPixelPanel
            self._panel = CanvasPixelPanel(
                self, x=0, y=0, width=w, height=h,
                bg="#2b170e", border="#140a05", inner_hi="#593322", inner_sh="#1a0d07",
                rivet_color="#d4af37", recessed=False, scale=max(1, int(s * 2)), tag="rail_bg"
            )
        except Exception:
            self.create_rectangle(0, 0, w, h, fill="#2b170e", outline="#140a05", tags="rail_bg")

        self.tag_lower("rail_bg")
        # Top brass gold trim line
        rail_cfg = get_ui_layout("mahogany_rail")
        trim_y = int(rail_cfg.get("trim_line_y", 0) * s)
        accent_y = int(rail_cfg.get("accent_line_y", 2) * s)
        self.create_line(0, trim_y, w, trim_y, fill="#d4af37", width=max(1, int(2 * s)), tags="rail_bg")
        self.create_line(0, accent_y, w, accent_y, fill="#7d5b10", width=1, tags="rail_bg")

    def _on_configure(self, event):
        if event.width > 20 and event.width != self._current_width:
            self._current_width = int(event.width)
            self._draw_rail()

    def _on_resize(self, event):
        self._on_configure(event)

    def set_display_profile(self, profile: Any) -> None:
        """Applies `rail_h` and integer `art_scale` from an active `DisplayProfile`."""
        self.display_profile = profile
        art_scale = max(1, int(getattr(profile, "art_scale", 1)))
        self.art_scale = art_scale
        self.scale_factor = float(art_scale)
        self.rail_height = int(getattr(profile, "rail_h", 72 * art_scale))
        self._current_width = 0
        try:
            self.configure(height=self.rail_height)
        except Exception:
            pass
        self._draw_rail()

    def set_scale(self, scale: float):
        art_scale = 2 if scale >= 1.8 else 1
        self.art_scale = art_scale
        self.scale_factor = float(art_scale)
        self.rail_height = 72 * art_scale
        self._current_width = 0
        try:
            self.configure(height=self.rail_height)
        except Exception:
            pass
        self._draw_rail()

