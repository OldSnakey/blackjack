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

import math
import random
import tkinter
from pathlib import Path
from typing import Any, Callable, Optional

# Optional Pillow support
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except (ImportError, Exception):
    Image = None
    ImageTk = None
    ImageDraw = None
    ImageFont = None
    PIL_AVAILABLE = False

from config import (
    CHIP_STYLES,
    HAUNTED_ASSETS_DIR,
    PANEL_BACKGROUND_COLOR,
    TABLE_BACKGROUND_COLOR,
    hex_to_rgb,
)
from rules import breakdown_chips, breakdown_bankroll_piles

# Parameterized Typography & HUD Constants
HUD_OUTCOME_FONT_FAMILY = "Georgia"
HUD_OUTCOME_FONT_SIZE = 14
HUD_OUTCOME_FONT_WEIGHT = "bold"

HUD_LORE_FONT_FAMILY = "Georgia"
HUD_LORE_FONT_SIZE = 11
HUD_LORE_FONT_SLANT = "italic"
HUD_DEFAULT_WRAPLENGTH = 600


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
        width=200,
        height=135,
        background=PANEL_BACKGROUND_COLOR,
        on_chip_click: Optional[Callable[[int], None]] = None,
        **kwargs,
    ):
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.scale = 1.0
        self.base_width = width
        self.base_height = height
        self.canvas_width = width
        self.canvas_height = height
        self.cx = width // 2
        self.cy = int(height * 0.28)
        self.current_bet = 0
        self.available_bankroll = 1000
        self.interactive_bankroll = True
        self.on_chip_click = on_chip_click
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

    def set_scale(self, scale: float):
        """Scales visualizer canvas and re-renders base spot proportionally without table overflow."""
        self.scale = scale
        self.canvas_width = int(getattr(self, "base_width", 200) * scale)
        self.canvas_height = int(getattr(self, "base_height", 135) * (1.0 if scale <= 1.0 else 1.25))
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.cx = self.canvas_width // 2
        self.cy = int(self.canvas_height * 0.28)
        if self._felt_source_img and self._felt_coords:
            self.sync_felt_background(self._felt_source_img, self._felt_coords[0], self._felt_coords[1])
        self._draw_base_spot()
        if self.current_bet > 0:
            self.render_stacks(self.current_bet)
        self.render_bankroll_piles()

    def _draw_base_spot(self):
        """Draws the felt betting spot: outer dashed gold ellipse, inner accent ring, watermark, and badge."""
        self.delete("all")
        cx, cy = self.cx, self.cy
        s = getattr(self, "scale", 1.0)

        # 0. Underlying felt slice background
        if getattr(self, "_felt_slice_photo", None):
            self.create_image(0, 0, image=self._felt_slice_photo, anchor="nw", tags="felt_bg")

        # 1. Outer betting circle felt background and golden dashed ring
        self.create_oval(
            cx - int(72 * s), cy - int(25 * s), cx + int(72 * s), cy + int(25 * s),
            outline="#d4af37", width=max(1, int(2 * s)), dash=(4, 3), fill="", tags="spot_base"
        )
        # 2. Inner subtle gold accent ring
        self.create_oval(
            cx - int(65 * s), cy - int(20 * s), cx + int(65 * s), cy + int(20 * s),
            outline="#8a6d1b", width=1, dash=(2, 3), tags="spot_ring"
        )
        # 3. Felt watermark
        self.create_text(
            cx, cy + int(1 * s), text="BETTING SPOT", fill="#8a6d1b",
            font=("Arial", max(6, int(7 * s)), "bold"), tags="watermark"
        )
        # 4. Top badge for bet amount
        self.create_text(
            cx, int(9 * s), text="", fill="#ffd700",
            font=("Arial", max(7, int(8 * s)), "bold"), tags="badge"
        )
        # 5. Divider & Bankroll Tray Header
        tray_top_y = int(68 * s)
        self.create_line(
            int(10 * s), tray_top_y, self.canvas_width - int(10 * s), tray_top_y,
            fill="#8a6d1b", width=1, dash=(2, 2), tags="tray_divider"
        )
        self.create_text(
            cx, int(77 * s), text="", fill="#ffd54f",
            font=("Arial", max(6, int(7 * s)), "bold"), tags="bankroll_badge"
        )

    def set_bankroll(self, available_bankroll: int, interactive: bool = True):
        """Updates the player's available bankroll chip piles in the bottom reserve tray."""
        self.available_bankroll = max(0, int(available_bankroll))
        self.interactive_bankroll = bool(interactive)
        self.render_bankroll_piles()

    def trigger_pile_click(self, denom: int):
        """Invokes the chip bet callback when a denomination pile in the bankroll tray is clicked."""
        if self.interactive_bankroll and self.available_bankroll >= denom and callable(self.on_chip_click):
            self.on_chip_click(denom)

    def render_bankroll_piles(self):
        """Draws the 5 interactive denomination piles ($5, $25, $100, $500, $1,000) in the bottom reserve tray."""
        self.delete("bankroll_chip")
        s = getattr(self, "scale", 1.0)
        avail = getattr(self, "available_bankroll", 0)
        hint_suffix = " (Click Pile)" if getattr(self, "interactive_bankroll", False) and avail >= 5 else ""
        self.itemconfigure("bankroll_badge", text=f"CHIPS: ${avail:,}{hint_suffix}")

        piles = breakdown_bankroll_piles(avail)
        denoms = (5, 25, 100, 500, 1000)
        num_cols = len(denoms)
        margin_x = int(24 * s)
        usable_w = max(40, self.canvas_width - 2 * margin_x)
        spacing = usable_w / max(1, num_cols - 1)
        base_y = int(self.canvas_height - int(22 * s))

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
                    chip_y = base_y - int(c_idx * 3 * s)
                    is_top = (c_idx == visible_count - 1)
                    self._draw_single_chip(
                        col_x, chip_y, denom, style, is_top=is_top,
                        count=count if count > 5 and is_top else None,
                        tags=combined_tags, compact=True
                    )
                lbl_color = "#ffffff" if self.interactive_bankroll else "#b0bec5"
            else:
                rx, ry = int(12 * s), int(6 * s)
                self.create_oval(
                    col_x - rx, base_y - ry, col_x + rx, base_y + ry,
                    outline="#5d4a18", width=1, dash=(2, 2), fill="", tags=combined_tags
                )
                lbl_color = "#6e6e6e"

            self.create_text(
                col_x, base_y + int(11 * s), text=short_lbl, fill=lbl_color,
                font=("Arial", max(6, int(6 * s)), "bold"), tags=combined_tags
            )

            self.tag_bind(pile_tag, "<Button-1>", lambda e, d=denom: self.trigger_pile_click(d))
            if self.interactive_bankroll and count > 0:
                self.tag_bind(pile_tag, "<Enter>", lambda e: self.configure(cursor="hand2"))
                self.tag_bind(pile_tag, "<Leave>", lambda e: self.configure(cursor=""))
            else:
                self.tag_bind(pile_tag, "<Enter>", lambda e: self.configure(cursor=""))

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

    def clear_timers(self):
        """Cancels all active animation callbacks."""
        for tid in list(self._active_timers):
            try:
                self.after_cancel(tid)
            except Exception:
                pass
        self._active_timers.clear()

    def set_bet(self, amount: int, animate: bool = True):
        """Updates the visualized bet amount."""
        self.current_bet = amount
        if amount <= 0:
            self.animate_clear(animated=animate)
        else:
            self.render_stacks(amount)

    def render_stacks(self, amount: int):
        """Procedurally draws 2.5D chip stacks representing the specified amount."""
        self.delete("chip")
        self.delete("anim_chip")
        self.delete("floating_text")

        if amount <= 0:
            self.itemconfigure("badge", text="")
            return

        self.itemconfigure("badge", text=f"BET: ${amount:,}")

        breakdown = breakdown_chips(amount)
        if not breakdown:
            return

        num_stacks = len(breakdown)
        spacing = 26 if num_stacks >= 4 else 30
        total_span = (num_stacks - 1) * spacing
        start_x = self.cx - (total_span // 2)
        base_y = self.cy + 10

        for s_idx, (denom, count) in enumerate(breakdown):
            stack_x = start_x + (s_idx * spacing)
            style = CHIP_STYLES.get(denom, CHIP_STYLES[5])

            offset_y = 0
            if num_stacks >= 3 and s_idx % 2 == 1:
                offset_y = -3

            visible_count = min(count, 6)
            for c_idx in range(visible_count):
                chip_y = (base_y + offset_y) - (c_idx * 3)
                is_top = (c_idx == visible_count - 1)
                self._draw_single_chip(
                    stack_x, chip_y, denom, style, is_top=is_top,
                    count=count if count > 6 and is_top else None, tags="chip"
                )

    def _draw_single_chip(self, x: int, y: int, denom: int, style: dict, is_top: bool = False, count: int = None, tags="chip", compact: bool = False):
        """Draws one 2.5D chip with rim thickness, edge stripes, top face, and denomination."""
        s = getattr(self, "scale", 1.0)
        if compact:
            rx, ry, depth = int(12 * s), int(6 * s), int(3 * s)
        else:
            rx, ry, depth = int(14 * s), int(7 * s), int(4 * s)

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
        stripe_x = int((6 if compact else 8) * s)
        self.create_line(x - stripe_x, y + 1, x - stripe_x, y + depth, fill=style["stripe"], width=max(1, int(2 * s)), tags=tags)
        self.create_line(x + stripe_x, y + 1, x + stripe_x, y + depth, fill=style["stripe"], width=max(1, int(2 * s)), tags=tags)

        # 3. Top face
        self.create_oval(
            x - rx, y - ry, x + rx, y + ry,
            fill=style["bg"], outline="#ffffff", width=1, tags=tags
        )
        # Inner dashed circle
        self.create_oval(
            x - rx + int(3 * s), y - ry + int(2 * s), x + rx - int(3 * s), y + ry - int(2 * s),
            outline=style["fg"], dash=(2, 2), tags=tags
        )

        # 4. Text (denomination or count badge if stack is capped)
        short_denom = "$1K" if denom == 1000 else f"${denom}"
        cap_limit = 5 if compact else 6
        display_text = f"x{count}" if (count and count > cap_limit) else short_denom
        self.create_text(
            x, y, text=display_text, fill=style["fg"],
            font=("Arial", 6 if len(display_text) > 3 or compact else 7, "bold"), tags=tags
        )

    def animate_chip_drop(self, added_amount: int, new_total: int, animated: bool = True):
        """Plays a tactile drop-and-bounce animation when a chip is added."""
        self.current_bet = new_total
        if not animated or not self._is_animation_enabled():
            self.render_stacks(new_total)
            return

        style = CHIP_STYLES.get(added_amount, CHIP_STYLES[5])
        drop_x = self.cx
        target_y = self.cy + 10
        start_y = target_y - 24

        drop_tag = "anim_chip"
        self.delete(drop_tag)
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
        """Animates chips sliding downwards off the table when bet is cleared."""
        self.current_bet = 0
        if not animated or not self._is_animation_enabled():
            self.delete("chip")
            self.delete("anim_chip")
            self.delete("floating_text")
            self.itemconfigure("badge", text="")
            return

        def step(count=0):
            if count >= 4:
                self.delete("chip")
                self.delete("anim_chip")
                self.delete("floating_text")
                self.itemconfigure("badge", text="")
            else:
                self.move("chip", 0, 14)
                self.move("anim_chip", 0, 14)
                self._schedule(16, lambda: step(count + 1))

        step()

    def animate_win(self, profit: int, animated: bool = True):
        """Animates dealer payout sliding in from top, glowing +$XX text, and chip collection."""
        if not animated or not self._is_animation_enabled():
            return

        payout_tag = "payout_stack"
        text_tag = "floating_text"
        self.delete(payout_tag)
        self.delete(text_tag)

        breakdown = breakdown_chips(max(profit, 5))
        top_denom = breakdown[0][0] if breakdown else 25
        style = CHIP_STYLES.get(top_denom, CHIP_STYLES[25])

        for c in range(min(3, len(breakdown))):
            self._draw_single_chip(self.cx + 20, -20 - (c * 3), top_denom, style, is_top=(c == 2), tags=payout_tag)

        def slide_payout(frame=0):
            if frame >= 5:
                self.create_text(
                    self.cx, self.cy - 16, text=f"+${profit:,}", fill="#ffd700",
                    font=("Arial", 11, "bold"), tags=text_tag
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
                self.delete(payout_tag)
                self.delete("chip")
                self.delete(text_tag)
                self.itemconfigure("badge", text="")
            else:
                self.move(payout_tag, -12, 16)
                self.move("chip", -12, 16)
                self.move(text_tag, -4, 4)
                self._schedule(18, lambda: collect_chips(frame + 1))

        slide_payout()

    def animate_loss(self, animated: bool = True):
        """Animates dealer sweeping the chips upward toward the dealer tray."""
        if not animated or not self._is_animation_enabled():
            self.delete("chip")
            self.delete("anim_chip")
            self.delete("floating_text")
            self.itemconfigure("badge", text="")
            return

        text_tag = "floating_text"
        self.delete(text_tag)

        def sweep_chips(frame=0):
            if frame >= 5:
                self.delete("chip")
                self.delete("anim_chip")
                self.delete(text_tag)
                self.itemconfigure("badge", text="")
            else:
                self.move("chip", 0, -18)
                self.move("anim_chip", 0, -18)
                self._schedule(18, lambda: sweep_chips(frame + 1))

        sweep_chips()

    def animate_push(self, animated: bool = True):
        """Highlights the betting spot on push and returns chips to player."""
        if not animated or not self._is_animation_enabled():
            return

        text_tag = "floating_text"
        self.delete(text_tag)
        self.create_text(
            self.cx, self.cy - 16, text="PUSH", fill="#ffffff",
            font=("Arial", 10, "bold"), tags=text_tag
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

    def __init__(self, master, width=180, height=135, background="#140508", **kwargs):
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.scale = 1.0
        self.canvas_width = width
        self.canvas_height = height
        self.cx = width // 2
        self.cy = height // 2
        self.current_value = 0.25
        self.target_value = 0.25
        self._anim_timer_id = None
        self._draw_meter()

    def set_scale(self, scale: float):
        """Scales soul meter canvas dimensions proportionally."""
        self.scale = scale
        self.canvas_width = int(180 * scale)
        self.canvas_height = int(135 * scale)
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
        cx, cy = self.cx, self.cy
        s = getattr(self, "scale", 1.0)

        # 1. Dark ornate frame with ember trim
        self._draw_rounded_rect(5, 5, self.canvas_width - 5, self.canvas_height - 5, radius=int(8 * s), fill="#0d0204", outline="#8b0000", width=max(1, int(2 * s)))

        # 2. Header
        self.create_text(cx, int(16 * s), text="☠ SOUL WAGER ☠", fill="#ffd700", font=("Arial", max(7, int(8 * s)), "bold"))

        # 3. Bar dimensions
        bx1, by1 = int(16 * s), int(42 * s)
        bx2, by2 = self.canvas_width - int(16 * s), int(62 * s)
        bar_w = bx2 - bx1

        # Background track
        self.create_rectangle(bx1, by1, bx2, by2, fill="#240004", outline="#4a000a", width=1)

        # Milestones (50% and 75%)
        m50_x = bx1 + int(bar_w * 0.50)
        m75_x = bx1 + int(bar_w * 0.75)
        self.create_line(m50_x, by1 - 3, m50_x, by2 + 3, fill="#80cbc4", width=1, dash=(2, 2))
        self.create_line(m75_x, by1 - 3, m75_x, by2 + 3, fill="#ffd700", width=1, dash=(2, 2))
        self.create_text(m50_x, by1 - int(7 * s), text="50%", fill="#80cbc4", font=("Arial", max(6, int(6 * s)), "bold"))
        self.create_text(m75_x, by1 - int(7 * s), text="75%", fill="#ffd700", font=("Arial", max(6, int(6 * s)), "bold"))

        # Fill segment
        fill_x = bx1 + int(bar_w * self.current_value)
        if fill_x > bx1:
            fill_color = "#ff1744" if self.current_value < 0.35 else ("#ffd700" if self.current_value < 0.70 else "#00e5ff")
            self.create_rectangle(bx1, by1, fill_x, by2, fill=fill_color, outline="")

        # Tug pointer
        p_w = int(5 * s)
        p_h = int(6 * s)
        self.create_polygon([fill_x, by1 - 3, fill_x - p_w, by1 - 3 - p_h, fill_x + p_w, by1 - 3 - p_h], fill="#ffffff", outline="#ffd700")

        # 4. Labels
        self.create_text(bx1 + int(16 * s), by2 + int(10 * s), text="ABYSS 0%", fill="#ff5252", font=("Arial", max(6, int(7 * s)), "bold"))
        self.create_text(bx2 - int(16 * s), by2 + int(10 * s), text="LIGHT 100%", fill="#69f0ae", font=("Arial", max(6, int(7 * s)), "bold"))

        # 5. Status Text
        pct = int(self.current_value * 100)
        status_txt = f"{pct}% SOUL ESSENCE"
        status_color = "#ff5252" if pct <= 25 else ("#ffeb3b" if pct < 75 else "#00e5ff")
        self.create_text(cx, int(90 * s), text=status_txt, fill=status_color, font=("Arial", max(8, int(9 * s)), "bold"))

        # Tip
        hint = "Win to advance • 21 surges"
        self.create_text(cx, int(112 * s), text=hint, fill="#cfd8dc", font=("Arial", max(6, int(7 * s)), "italic"))

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
        self.outcome_font_family = outcome_family
        self.outcome_font_size = outcome_size
        self.outcome_font_weight = outcome_weight
        self.lore_font_family = lore_family
        self.lore_font_size = lore_size
        self.lore_font_slant = lore_slant
        self.wraplength = wraplength
        self.current_raw_message = ""
        self._dismiss_timer_id: Optional[str] = None

        # Outer felt badge with subtle gold border
        self.badge = tkinter.Frame(
            self, background="#07200e", highlightthickness=2,
            highlightbackground="#d4af37", relief="ridge", borderwidth=1, padx=22, pady=8, cursor="hand2"
        )
        self.badge.pack(anchor="center")

        # Tier 1: Outcome Label
        self.outcome_label = tkinter.Label(
            self.badge,
            text="",
            font=(self.outcome_font_family, self.outcome_font_size, self.outcome_font_weight),
            background="#07200e",
            fg="#f5f5f5",
            justify="center",
            cursor="hand2",
            wraplength=self.wraplength
        )
        self.outcome_label.pack(side="top", fill="x", expand=True)

        # Tier 2: Thematic Lore / Status Label
        self.lore_label = tkinter.Label(
            self.badge,
            text="",
            font=(self.lore_font_family, self.lore_font_size, self.lore_font_slant),
            background="#07200e",
            fg="#ffb74d",
            justify="center",
            cursor="hand2",
            wraplength=self.wraplength
        )
        # Hidden by default until lore text is present
        self.lore_label.pack_forget()

        # Click-to-dismiss bindings across dialog elements
        for w in (self, self.badge, self.outcome_label, self.lore_label):
            w.bind("<Button-1>", lambda e: self.dismiss())

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

        # Check for lore delimiter
        if " | " in text:
            parts = text.split(" | ", 1)
            outcome_text = parts[0].strip()
            lore_text = parts[1].strip()
        else:
            outcome_text = text
            lore_text = ""

        self.outcome_label.configure(text=outcome_text)
        self._update_outcome_color(outcome_text)
        if lore_text:
            self.lore_label.configure(text=lore_text)
            if not self.lore_label.winfo_manager():
                self.lore_label.pack(side="top", pady=(3, 0), fill="x", expand=True)
        else:
            self.lore_label.configure(text="")
            self.lore_label.pack_forget()

        # Float in center of parent table felt as an overlay dialog card
        if not self.winfo_manager() or self.winfo_manager() == "place":
            self.place(relx=0.5, rely=0.5, anchor="center")
            self.lift()

        # Automatically dismiss transient announcements after 2.5s
        tl = text.lower()
        if "relic" in tl or "equipped" in tl or "blessing" in tl or "achievement" in tl:
            self._dismiss_timer_id = self.after(2500, self.dismiss)

    @property
    def is_lore_visible(self) -> bool:
        return bool(self.lore_label.winfo_manager() == "pack" and self.lore_label.cget("text"))

    def _update_outcome_color(self, outcome_text: str):
        t = outcome_text.lower()
        if "dealer wins" in t or "bust" in t or "lose" in t or "lost" in t or "damnation" in t:
            fg = "#ff5252"  # Crisp Red
            border = "#ff1744"
        elif "blackjack" in t:
            fg = "#ffd700"  # Gold
            border = "#ffd700"
        elif "win" in t or "won" in t:
            fg = "#69f0ae"  # Vibrant Green
            border = "#00e676"
        elif "push" in t or "tie" in t or "draw" in t:
            fg = "#ffeb3b"  # Amber / Gold
            border = "#ffeb3b"
        else:
            fg = "#f5f5f5"  # Clean White
            border = "#80cbc4"
        self.outcome_label.configure(fg=fg)
        if hasattr(self, "badge"):
            self.badge.configure(highlightbackground=border)

    def set_typography(
        self,
        outcome_family: str | None = None,
        outcome_size: int | None = None,
        outcome_weight: str | None = None,
        lore_family: str | None = None,
        lore_size: int | None = None,
        lore_slant: str | None = None,
        wraplength: int | None = None,
    ):
        """Allows hot-swapping font parameters and wraplength dynamically."""
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
            font=(self.outcome_font_family, self.outcome_font_size, self.outcome_font_weight),
            wraplength=self.wraplength
        )
        self.lore_label.configure(
            font=(self.lore_font_family, self.lore_font_size, self.lore_font_slant),
            wraplength=self.wraplength
        )

    def set_scale(self, scale: float):
        """Scales outcome/lore typography and wraplength proportionally."""
        self.scale = scale
        self.set_typography(
            outcome_size=int(14 * scale),
            lore_size=int(11 * scale),
            wraplength=int(600 * scale),
        )
        if hasattr(self, "badge"):
            self.badge.configure(padx=int(22 * scale), pady=int(8 * scale))

    def set_theme_color(self, bg_color: str, border_color: str | None = None):
        """Cascades table felt background color to announcement HUD and badge."""
        self.configure(background=bg_color)
        if hasattr(self, "badge"):
            if border_color:
                border = border_color
            else:
                border = "#3a151b" if bg_color.lower() in ("#0d0204", "#140508", "#0e0306") else "#1b2a1b"
            self.badge.configure(background=bg_color, highlightbackground=border)
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
        width: int = 260,
        height: int = 135,
        background: str = PANEL_BACKGROUND_COLOR,
        **kwargs
    ):
        super().__init__(
            master, width=width, height=height, background=background,
            highlightthickness=0, borderwidth=0, relief="flat", **kwargs
        )
        self.scale = 1.0
        self.canvas_width = width
        self.canvas_height = height
        self.assets = assets or {}

        # 5 Candle positions along top row (y = 28)
        self.candle_y = 28
        self.candle_x_positions = [26 + i * 52 for i in range(5)]

        # Gravestone positions along bottom row (y = 80)
        self.gravestone_y = 80
        self.gravestone_x_positions = [36, 83, 130, 177, 224]

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

    def set_scale(self, scale: float, assets: dict[str, tkinter.PhotoImage] | None = None):
        """Scales canvas dimensions and re-projects candle/stone coordinates proportionally."""
        self.scale = scale
        if assets is not None:
            self.assets = assets
        self.canvas_width = int(260 * scale)
        self.canvas_height = int(135 * scale)
        self.configure(width=self.canvas_width, height=self.canvas_height)
        self.candle_y = int(28 * scale)
        self.candle_x_positions = [int((26 + i * 52) * scale) for i in range(5)]
        self.gravestone_y = int(80 * scale)
        self.gravestone_x_positions = [int(x * scale) for x in [36, 83, 130, 177, 224]]
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
                    self.create_oval(
                        cx - int(24 * s), cy - int(6 * s), cx + int(24 * s), cy + int(30 * s),
                        fill=glow_outer, outline="", tags="glow"
                    )
                    self.create_oval(
                        cx - int(16 * s), cy, cx + int(16 * s), cy + int(24 * s),
                        fill=glow_mid, outline="", tags="glow"
                    )
                    self.create_oval(
                        cx - int(8 * s), cy + int(6 * s), cx + int(8 * s), cy + int(18 * s),
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

                ground_y = gy + int(20 * s)
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

    DEFAULT_HEIGHT = 220

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Optional[Any] = None,
        width: int = 1000,
        height: int = 220,
        on_hanger_click: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        super().__init__(
            parent,
            width=width,
            height=height,
            background="#0a0a0a",
            highlightthickness=0,
            borderwidth=0,
            **kwargs
        )
        self.app = app
        self.current_theme = "casino"
        self.scale_factor = 1.0
        self.on_hanger_click = on_hanger_click
        self.canvas_width = width
        self.canvas_height = height

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

    def draw_speech_tail(self, fill_col: str = "#141014", border_col: str = "#c8a038"):
        """Draws directional callout tail from speech bubble pointing toward dealer avatar."""
        self._active_speech_tail = (fill_col, border_col)
        if not self.find_withtag("dialogue_win"):
            return
        s = self.scale_factor
        w = max(10, self.canvas_width)
        h = max(10, self.canvas_height)
        bubble_x = w // 2 - int(76 * s)
        bubble_y = h - int(90 * s)

        # Directional pointer tail projecting toward dealer avatar mouth at head level
        p1 = (bubble_x - int(4 * s), bubble_y - int(44 * s))
        p2 = (bubble_x - int(4 * s), bubble_y - int(30 * s))
        p3 = (w // 2 - int(44 * s), h - int(127 * s))

        self.delete("speech_tail")
        self.create_polygon(
            p1[0], p1[1], p2[0], p2[1], p3[0], p3[1],
            fill=fill_col, outline=border_col, width=max(1, int(s)),
            tags="speech_tail"
        )
        if self.find_withtag("dialogue_win"):
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
        }

        for theme, (f1x, f2x) in theme_files.items():
            p1x = backdrops_dir / f1x
            p2x = backdrops_dir / f2x
            if p1x.exists() and PIL_AVAILABLE and Image is not None and ImageTk is not None:
                try:
                    img1x = Image.open(p1x)
                    photo1x = ImageTk.PhotoImage(img1x)
                    img2x = Image.open(p2x) if p2x.exists() else img1x
                    photo2x = ImageTk.PhotoImage(img2x) if p2x.exists() else photo1x
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

        # 1. Draw scaled backdrop
        theme_data = self.backdrop_images.get(self.current_theme)
        if theme_data and PIL_AVAILABLE and Image is not None and ImageTk is not None:
            active_scale = 2.0 if self.scale_factor > 1.5 else 1.0
            raw_img, _ = theme_data.get(active_scale, (None, None))
            if raw_img:
                try:
                    resample_mode = getattr(Image, "Resampling", Image).BILINEAR
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

    def set_scale(self, scale_factor: float):
        self.scale_factor = scale_factor
        self.canvas_height = int(self.DEFAULT_HEIGHT * (1.0 if scale_factor <= 1.0 else 1.30))
        self.configure(height=self.canvas_height)
        self._redraw_stage()


# ============================================================================
# 6. TableFeltCanvas
# ============================================================================

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

    def __init__(self, parent: tkinter.Misc, background: str = PANEL_BACKGROUND_COLOR, **kwargs):
        hl = kwargs.pop("highlightthickness", 0)
        bw = kwargs.pop("borderwidth", 0)
        rel = kwargs.pop("relief", "flat")
        self.padx = kwargs.pop("padx", 0)
        self.pady = kwargs.pop("pady", 0)
        super().__init__(
            parent,
            background=background,
            highlightthickness=hl,
            borderwidth=bw,
            relief=rel,
            **kwargs
        )
        self.current_theme = "casino"
        self.scale_factor = 1.0
        self.canvas_width = 900
        self.canvas_height = 274
        self._bg_hex = background
        self._felt_photo: Optional[Any] = None
        self._felt_img: Optional[Any] = None
        self._felt_cache: dict[tuple[str, int, int, float], Any] = {}

        self.bind("<Configure>", self._on_resize)
        self._redraw_felt()

    def _on_resize(self, event):
        if event.width > 20 and (event.width != self.canvas_width or event.height != self.canvas_height):
            self.canvas_width = event.width
            self.canvas_height = event.height
            self._redraw_felt()

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

    def set_scale(self, scale_factor: float):
        if self.scale_factor != scale_factor:
            self.scale_factor = scale_factor
            self._redraw_felt()

    def _generate_felt_image(self, w: int, h: int) -> Optional[Any]:
        if not PIL_AVAILABLE or Image is None or ImageDraw is None:
            return None
        import numpy as np

        cfg = self.THEME_COLORS.get(self.current_theme, self.THEME_COLORS["casino"])
        base_rgb = np.array(cfg["base"], dtype=np.float32)

        rng = np.random.RandomState(42)
        noise = rng.normal(0, 5.0, (h, w, 1))

        y_idx, x_idx = np.indices((h, w))
        weave = ((x_idx + y_idx) % 4 == 0).astype(np.float32)[:, :, np.newaxis] * 2.5

        cx, cy = w / 2.0, h * 0.45
        dist = np.sqrt(((x_idx - cx) / (w * 0.6)) ** 2 + ((y_idx - cy) / (h * 0.7)) ** 2)
        vignette = np.clip(1.06 - 0.18 * dist, 0.85, 1.10)[:, :, np.newaxis]

        felt_arr = (base_rgb + noise + weave) * vignette
        felt_arr = np.clip(felt_arr, 0, 255).astype(np.uint8)

        felt_img = Image.fromarray(felt_arr, mode="RGB")
        draw = ImageDraw.Draw(felt_img)

        s = self.scale_factor
        gold = cfg["gold"]

        ribbon_y = int(h * 0.36)
        rx = int(w * 0.38)
        ry = int(h * 0.28)
        draw.arc([cx - rx, ribbon_y - int(10 * s), cx + rx, ribbon_y + ry], start=22, end=158, fill=gold, width=max(1, int(2 * s)))

        try:
            from PIL import ImageFont
            font_large = ImageFont.truetype("arial.ttf", int(12 * (1.0 if s <= 1.0 else 1.4)))
            font_small = ImageFont.truetype("arial.ttf", int(9 * (1.0 if s <= 1.0 else 1.3)))
        except Exception:
            font_large = font_small = None

        if font_large and font_small:
            draw.text((cx, ribbon_y + int(10 * s)), "BLACKJACK PAYS 3 TO 2", fill=gold, font=font_large, anchor="mm")
            draw.text((cx, ribbon_y + int(24 * s)), "Dealer must stand on 17 and must draw to 16", fill=cfg["rules_fg"], font=font_small, anchor="mm")
            draw.text((cx, ribbon_y + int(36 * s)), "INSURANCE PAYS 2 TO 1", fill=gold, font=font_small, anchor="mm")

        return felt_img

    def _redraw_felt(self):
        w = max(20, self.canvas_width)
        h = max(20, self.canvas_height)
        key = (self.current_theme, w, h, self.scale_factor)

        if key in self._felt_cache:
            self._felt_img, self._felt_photo = self._felt_cache[key]
        elif PIL_AVAILABLE and Image is not None and ImageTk is not None:
            try:
                img = self._generate_felt_image(w, h)
                if img:
                    self._felt_img = img
                    self._felt_photo = ImageTk.PhotoImage(img, master=self)
                    self._felt_cache[key] = (self._felt_img, self._felt_photo)
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
