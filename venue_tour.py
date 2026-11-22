"""
2.5D Casino Venue Tour Overworld Map View & Controller (`venue_tour.py`).

Architecture (MVC):
- **Model (`tour_domain.py`)**:
  `TourSalonSpec`, `SALON_SPECS`, `SalonVisualState`, `evaluate_tour_settlement`,
  `can_select_salon`, `can_top_up_forgiving`, `apply_forgiving_top_up`, and `switch_tour_mode`.
- **View (`VenueTourCanvasRenderer` + `TourControlDock`)**:
  Renders a Super Mario World–inspired 2.5D Overworld Map (`880x390`) on `row=3` and a
  dedicated 4-button `MahoganyRailCanvas` dock (`880x72`) on `row=4`, while keeping the live
  `DealerStageCanvas` (`row=1`) visible above the horizon rail (`row=2`) for Tour Coordinator
  congratulations and stage introductions.
- **Controller (`VenueTourFrame`)**:
  Manages node selection, single-source geometric canvas hitboxes, keyboard navigation,
  Standard <-> Ironman mode switching, Standard Top-Up, and Coordinator dialogue.
"""

from __future__ import annotations

from pathlib import Path
import tkinter
from typing import Any, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageTk

from config import ASSETS_EXTRA_DIR, CHIP_STYLES, TABLE_BACKGROUND_COLOR
from dealer_actor import CHARACTERS
from pixel_ui import (
    CanvasPixelButton,
    CanvasPixelPanel,
    get_badge_font,
    get_body_font,
    get_button_font,
    get_header_font,
    get_title_font,
)
from save_manager import VenueTourProgress
from tour_domain import (
    SALON_SPECS,
    TOUR_COORDINATOR_COSTUME,
    TOUR_STARTING_BANKROLL,
    SalonVisualState,
    TourSalonSpec,
    apply_forgiving_top_up,
    can_select_salon,
    can_top_up_forgiving,
    get_active_salon_index,
    get_active_tour_bankroll,
    get_forgiving_checkpoint_floor,
    get_forgiving_frontier_idx,
    get_salon_spec,
    get_salon_visual_state,
    get_top_up_threshold,
    reset_ironman_run,
    switch_tour_mode,
)
from ui_canvases import MahoganyRailCanvas
from ui_chip_renderer import draw_25d_grade_medallion, draw_single_25d_chip


# ============================================================================
# View Component 1: Bottom Mahogany Control Dock (row=4)
# ============================================================================

class TourControlDock(MahoganyRailCanvas):
    """
    Dedicated `row=3` full-width mahogany armrest control dock for the Casino Venue Tour Overworld Map.
    Exposes `self.buttons` keyed by semantic control ID (`enter_salon`, `toggle_mode`,
    `top_up`, `free_play`) with every button >= 100px wide and dark `#141008` ink on gold buttons.
    """

    def __init__(
        self,
        master: tkinter.Widget,
        height: int = 72,
        art_scale: int = 1,
        font_scale: float = 1.0,
        display_profile: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        eff_art = max(1, int(getattr(display_profile, "art_scale", art_scale))) if display_profile is not None else max(1, int(art_scale))
        self.font_scale = float(getattr(display_profile, "font_scale", font_scale)) if display_profile is not None else float(font_scale)
        self._last_specs: List[Dict[str, Any]] = []
        super().__init__(
            master,
            width=1280 * eff_art,
            height=height,
            display_profile=display_profile,
            art_scale=eff_art,
            background="#140a05",
            **kwargs,
        )
        self.buttons: Dict[str, CanvasPixelButton] = {}

    def _on_configure(self, event: Any) -> None:
        prev_w = self._current_width
        super()._on_configure(event)
        if self._current_width != prev_w and self._last_specs:
            self._render_specs(self._last_specs)

    def set_display_profile(self, profile: Any) -> None:
        self.art_scale = max(1, int(getattr(profile, "art_scale", 1)))
        self.font_scale = float(getattr(profile, "font_scale", 1.0))
        self.rail_height = 72 * self.art_scale
        self._current_width = 0
        self.configure(height=self.rail_height)
        self._draw_rail()
        if self._last_specs:
            self._render_specs(self._last_specs)

    def clear_controls(self) -> None:
        for btn in self.buttons.values():
            try:
                self.delete(btn.tag)
            except Exception:
                pass
        self.buttons.clear()
        self.delete("dock_fg")

    def set_buttons(self, specs: List[Dict[str, Any]]) -> None:
        """Stores button specs and renders centered `CanvasPixelButton` controls across the full-width mahogany rail."""
        self._last_specs = list(specs)
        self._render_specs(self._last_specs)

    def _render_specs(self, specs: List[Dict[str, Any]]) -> None:
        self.clear_controls()
        self._draw_rail()
        if not specs:
            return

        s = self.art_scale
        live_w = self.winfo_width()
        w = live_w if live_w > 20 else max(1000 * s, int(self._current_width) or 1280 * s)
        h = self.rail_height
        spacing = 12 * s
        btn_h = 42 * s
        widths = [max(100, int(sp.get("width", 190)) * s) for sp in specs]
        total_w = sum(widths) + spacing * max(0, len(specs) - 1)
        cur_x = (w - total_w) // 2
        cy = h // 2
        font_px = 18 * s

        for idx, (sp, bw) in enumerate(zip(specs, widths)):
            cx = cur_x + bw // 2
            key = str(sp.get("key", f"btn_{idx}"))
            theme = str(sp.get("theme", "green"))
            txt_col = str(sp.get("text_color") or ("#141008" if theme == "gold" else "#ffffff"))
            btn = CanvasPixelButton(
                self,
                x=cx,
                y=cy,
                width=bw,
                height=btn_h,
                text=str(sp.get("text", "Action")),
                command=sp.get("command"),
                theme=theme,
                font=get_button_font(font_px),
                text_color=txt_col,
                scale=2 * s,
                enabled=bool(sp.get("enabled", True)),
                group_tag="dock_fg",
            )
            self.buttons[key] = btn
            cur_x += bw + spacing


# ============================================================================
# View Component 2: 2.5D Super Mario World Overworld Map Renderer (row=2)
# ============================================================================

class VenueTourCanvasRenderer:
    """
    Stateless 2.5D pixel-art Overworld Map renderer (`1000x390` at `1x`, `2000x780` at `2x`,
    aligned 1:1 with `DealerStageCanvas`) for the 8-Salon Casino Venue Tour. Composites crunchy
    16-bit architectural salon miniatures in memory (sampling atmospheric window vignettes from
    `assets/haunted/backdrops/` PNGs) plus darkened `???` silhouettes for undiscovered stops and
    2.5D Gold/Obsidian medallions.
    """

    CANVAS_W = 1000
    CANVAS_H = 390
    BACKDROPS_DIR = ASSETS_EXTRA_DIR / "haunted" / "backdrops"

    def __init__(self, canvas: tkinter.Canvas, art_scale: int = 1) -> None:
        self.canvas = canvas
        self.art_scale = max(1, int(art_scale))
        self._photo_refs: List[Any] = []
        self._sprite_cache: Dict[Tuple[str, bool, int], ImageTk.PhotoImage] = {}
        self._backdrop_samples: Dict[Tuple[str, int], Image.Image] = {}
        self.node_hit_boxes: Dict[int, Tuple[int, int, int, int]] = {}
        self.action_hit_boxes: Dict[str, Tuple[int, int, int, int]] = {}

    def _s(self, v: int | float) -> int:
        return int(round(v * self.art_scale))

    def set_art_scale(self, art_scale: int) -> None:
        new_scale = max(1, int(art_scale))
        if new_scale != self.art_scale:
            self.art_scale = new_scale

    def _clear(self) -> None:
        self.canvas.delete("all")
        self._photo_refs.clear()
        self.node_hit_boxes.clear()
        self.action_hit_boxes.clear()

    def _map_xy(self, salon: TourSalonSpec) -> Tuple[int, int]:
        """Scales canonical 880px salon map coordinates across `CANVAS_W = 1000` symmetrically."""
        raw_x, raw_y = salon.map_pos
        return int(round(raw_x * self.CANVAS_W / 880.0)), int(raw_y)

    def _draw_shadow_text(
        self,
        x: int,
        y: int,
        text: str,
        fill: str = "#ffffff",
        shadow: str = "#041208",
        font: Optional[Tuple[Any, ...]] = None,
        anchor: str = "center",
        tags: Tuple[str, ...] = (),
    ) -> int:
        use_font = font or get_body_font(16 * self.art_scale)
        off = self.art_scale
        self.canvas.create_text(x + off, y + off, text=text, fill=shadow, font=use_font, anchor=anchor, tags=tags)
        return self.canvas.create_text(x, y, text=text, fill=fill, font=use_font, anchor=anchor, tags=tags)

    def _get_backdrop_sample(self, theme: str) -> Optional[Image.Image]:
        cache_key = (theme, self.art_scale)
        if cache_key in self._backdrop_samples:
            return self._backdrop_samples[cache_key]
        candidates = (
            [
                self.BACKDROPS_DIR / f"backdrop_{theme}_2x.png",
                self.BACKDROPS_DIR / f"backdrop_{theme}.png",
                self.BACKDROPS_DIR / "backdrop_casino_2x.png",
                self.BACKDROPS_DIR / "backdrop_casino.png",
            ]
            if self.art_scale >= 2
            else [
                self.BACKDROPS_DIR / f"backdrop_{theme}.png",
                self.BACKDROPS_DIR / "backdrop_casino.png",
            ]
        )
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            return None
        try:
            with Image.open(path) as src:
                k = max(1.0, src.width / 1000.0)
                box = (int(90 * k), int(24 * k), int(250 * k), int(124 * k))
                crop = src.convert("RGBA").crop(box).resize(
                    (20, 12), getattr(Image, "Resampling", Image).NEAREST
                )
                self._backdrop_samples[cache_key] = crop
                return crop
        except Exception:
            return None

    def _get_landmark_photo(self, salon: TourSalonSpec, discovered: bool) -> ImageTk.PhotoImage:
        cache_key = (salon.salon_id, bool(discovered), self.art_scale)
        cached = self._sprite_cache.get(cache_key)
        if cached is not None:
            return cached

        # Author on a 38x30 logical pixel grid, then upscale 2x NEAREST -> 76x60 crunchy 2.5D pixel sprite
        lw, lh = 38, 30
        img = Image.new("RGBA", (lw, lh), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        outline = (16, 14, 22, 255)

        kind = salon.landmark_kind
        # Base 2.5D isometric terrace plinth (y = 24..29)
        d.rectangle([3, 24, 34, 28], fill=(82, 74, 68, 255), outline=outline)
        d.line([4, 25, 33, 25], fill=(168, 152, 130, 255))

        # Paste subtle backdrop window glow inside central facade before drawing architectural frame
        sample = self._get_backdrop_sample(salon.stage_backdrop_theme)
        if sample is not None:
            img.paste(sample, (9, 11))

        if kind == "pit_gazebo":
            # Emerald & brass resort pavilion with striped casino awning
            d.rectangle([6, 11, 31, 24], fill=(22, 78, 48, 255), outline=outline)
            d.polygon([(3, 11), (19, 4), (34, 11)], fill=(26, 120, 68, 255), outline=outline)
            for sx in range(7, 31, 4):
                d.rectangle([sx, 9, sx + 1, 12], fill=(255, 215, 64, 255))
            for px in (8, 14, 23, 29):
                d.rectangle([px, 13, px + 1, 23], fill=(212, 175, 55, 255))
            d.rectangle([16, 16, 21, 23], fill=(255, 224, 130, 255), outline=outline)

        elif kind == "grand_rotunda":
            # Monte Carlo golden dome & marble colonnade
            d.ellipse([10, 2, 27, 14], fill=(218, 165, 32, 255), outline=outline)
            d.line([18, 0, 18, 3], fill=(255, 235, 120, 255))
            d.rectangle([6, 10, 31, 24], fill=(230, 220, 198, 255), outline=outline)
            d.rectangle([7, 10, 30, 12], fill=(212, 175, 55, 255))
            for px in (9, 14, 23, 28):
                d.rectangle([px, 13, px + 1, 23], fill=(250, 246, 236, 255))
            d.rectangle([16, 15, 21, 23], fill=(128, 28, 36, 255), outline=outline)

        elif kind == "neon_marquee":
            # Downtown Lounge retro neon marquee sign & velvet entrance
            d.rectangle([5, 9, 32, 24], fill=(42, 24, 62, 255), outline=outline)
            d.rectangle([8, 4, 29, 10], fill=(186, 28, 118, 255), outline=outline)
            d.rectangle([10, 6, 27, 8], fill=(0, 229, 255, 255))
            d.rectangle([8, 13, 13, 19], fill=(255, 64, 129, 255), outline=outline)
            d.rectangle([24, 13, 29, 19], fill=(0, 229, 255, 255), outline=outline)
            d.rectangle([16, 15, 21, 23], fill=(255, 213, 79, 255), outline=outline)

        elif kind == "ivy_hall":
            # MIT / Ivy League Georgian brick hall with clock tower pediment
            d.rectangle([5, 11, 32, 24], fill=(138, 56, 44, 255), outline=outline)
            d.polygon([(4, 11), (18, 4), (33, 11)], fill=(72, 46, 38, 255), outline=outline)
            d.rectangle([15, 2, 22, 9], fill=(158, 72, 54, 255), outline=outline)
            d.rectangle([17, 4, 20, 7], fill=(255, 248, 214, 255))
            for wx in (8, 26):
                d.rectangle([wx, 14, wx + 3, 19], fill=(178, 235, 242, 255), outline=outline)
            d.rectangle([16, 15, 21, 23], fill=(62, 39, 35, 255), outline=outline)

        elif kind == "gothic_crypt":
            # Mortimer's Bone Vault gothic stone mausoleum & iron spires
            d.rectangle([7, 10, 30, 24], fill=(78, 88, 96, 255), outline=outline)
            d.polygon([(6, 10), (18, 3), (31, 10)], fill=(52, 60, 68, 255), outline=outline)
            d.rectangle([6, 5, 9, 24], fill=(64, 72, 80, 255), outline=outline)
            d.rectangle([28, 5, 31, 24], fill=(64, 72, 80, 255), outline=outline)
            d.rectangle([14, 14, 23, 23], fill=(20, 28, 32, 255), outline=outline)
            for gx in (16, 18, 20):
                d.line([gx, 15, gx, 23], fill=(128, 203, 196, 255))

        elif kind == "cyber_spire":
            # Selene's Neon Cyber-Deck tower with holographic cyan grid
            d.rectangle([9, 6, 28, 24], fill=(18, 30, 52, 255), outline=outline)
            d.line([18, 0, 18, 6], fill=(0, 229, 255, 255))
            d.rectangle([12, 3, 25, 7], fill=(0, 184, 212, 255), outline=outline)
            for cy_line in (10, 14, 18):
                d.line([11, cy_line, 26, cy_line], fill=(234, 128, 252, 255))
            d.rectangle([15, 16, 22, 23], fill=(0, 229, 255, 255), outline=outline)

        elif kind == "crimson_manor":
            # Count Vladimir's Crimson Salon chateau & ruby rose window
            d.rectangle([6, 11, 31, 24], fill=(104, 18, 32, 255), outline=outline)
            d.polygon([(4, 11), (11, 4), (26, 4), (33, 11)], fill=(48, 14, 24, 255), outline=outline)
            d.ellipse([15, 6, 22, 13], fill=(255, 23, 68, 255), outline=outline)
            for wx in (8, 26):
                d.rectangle([wx, 14, wx + 3, 20], fill=(255, 138, 128, 255), outline=outline)
            d.rectangle([16, 16, 21, 23], fill=(212, 175, 55, 255), outline=outline)

        else:
            # Uriel's Sanctum of Light floating marble temple & golden halo arch
            d.ellipse([9, 1, 28, 13], fill=(255, 236, 148, 255), outline=outline)
            d.ellipse([12, 4, 25, 12], fill=(224, 247, 250, 255))
            d.rectangle([6, 10, 31, 24], fill=(245, 248, 252, 255), outline=outline)
            d.rectangle([7, 10, 30, 12], fill=(255, 215, 0, 255))
            for px in (8, 13, 24, 29):
                d.rectangle([px, 12, px + 1, 23], fill=(255, 224, 130, 255))
            d.rectangle([15, 14, 22, 23], fill=(128, 216, 255, 255), outline=outline)

        if not discovered:
            # Convert non-transparent pixels into a mysterious Super Mario World dark silhouette + '?' crest
            px_access = img.load()
            for py in range(lh):
                for px in range(lw):
                    r, g, b, a = px_access[px, py]
                    if a > 0:
                        if (r, g, b, a) == outline:
                            px_access[px, py] = (8, 12, 18, 255)
                        elif py <= 8:
                            px_access[px, py] = (28, 42, 58, 255)
                        else:
                            px_access[px, py] = (16, 25, 36, 255)
            # Crisp golden '?' mystery crest on silhouette center
            d.rectangle([15, 11, 22, 21], fill=(24, 36, 50, 255), outline=(255, 213, 79, 255))
            d.line([17, 13, 20, 13], fill=(255, 215, 0, 255))
            d.point((20, 14), fill=(255, 215, 0, 255))
            d.line([18, 15, 19, 16], fill=(255, 215, 0, 255))
            d.point((18, 19), fill=(255, 215, 0, 255))

        upscaled = img.resize(
            (lw * 2 * self.art_scale, lh * 2 * self.art_scale),
            getattr(Image, "Resampling", Image).NEAREST,
        )
        photo = ImageTk.PhotoImage(upscaled, master=self.canvas)
        self._sprite_cache[cache_key] = photo
        return photo

    def _draw_overworld_terrain(self) -> None:
        """Draws layered 2.5D casino district terrain zones from Resort Lawn (West) to Sanctum Summit (East)."""
        s = self._s
        k = self.art_scale
        w, h = s(self.CANVAS_W), s(self.CANVAS_H)
        self.canvas.create_rectangle(0, 0, w, h, fill="#072b15", outline="")

        zones = [
            (0, 294, "#08361a", "#0d4724"),     # Resort Emerald Lawn
            (294, 538, "#0b2e26", "#123f35"),   # Neon Lounge & Ivy Quad
            (538, 780, "#102332", "#183347"),   # Vault Stone & Cyber Terrace
            (780, self.CANVAS_W, "#1e162b", "#2b1d3d"),  # Crimson Ridge & Sanctum Summit
        ]
        for x1, x2, base_col, hill_col in zones:
            self.canvas.create_rectangle(s(x1), s(48), s(x2), s(316), fill=base_col, outline="")
            self.canvas.create_polygon(
                s(x1 + 14), s(185), s(x2 - 10), s(165), s(x2 - 4), s(290), s(x1 + 6), s(300),
                fill=hill_col, outline="",
            )

        self.canvas.create_oval(s(825), s(56), s(978), s(164), fill="#2e294e", outline="#ffd54f", width=k)
        self.canvas.create_oval(s(843), s(68), s(960), s(148), fill="#3b3363", outline="")

        trees = [(42, 132), (50, 286), (175, 276), (298, 96), (418, 92), (540, 286), (666, 282), (782, 96)]
        for tx, ty in trees:
            self.canvas.create_rectangle(s(tx - 3), s(ty + 6), s(tx + 3), s(ty + 16), fill="#4e342e", outline="#121016")
            self.canvas.create_oval(s(tx - 11), s(ty - 10), s(tx + 11), s(ty + 8), fill="#1b5e20", outline="#0a2910")
            self.canvas.create_oval(s(tx - 7), s(ty - 14), s(tx + 7), s(ty + 2), fill="#2e7d32", outline="")

        self.canvas.create_rectangle(s(2), s(2), w - s(3), h - s(3), outline="#d4af37", width=2 * k)

    def _draw_header_bar(self, progress: VenueTourProgress) -> None:
        s = self._s
        k = self.art_scale
        self.canvas.create_rectangle(s(4), s(4), s(self.CANVAS_W - 5), s(46), fill="#091f12", outline="#d4af37", width=k)
        self._draw_shadow_text(
            s(18), s(25),
            text="🗺 GRAND CASINO VENUE TOUR",
            fill="#ffd700",
            font=get_header_font(18 * k),
            anchor="w",
        )

        active_br = get_active_tour_bankroll(progress)
        g_clears = int(progress.forgiving_salons_cleared)
        im_clears = int(progress.ironman_salons_cleared)
        if progress.active_mode == "ironman":
            mode_lbl = "👑 IRONMAN LEGEND" if progress.ironman_completed else "💀 IRONMAN GAUNTLET"
            status = f"{mode_lbl}  •  Stack: ${active_br:,}  •  ★ {g_clears}/8  ♦ {im_clears}/8"
            pill_bg, pill_fg, pill_bd = "#2d0c14", "#ff8a80", "#ff5252"
        else:
            mode_lbl = "🏆 TOUR CHAMPION" if progress.forgiving_completed else "🛡 STANDARD TOUR"
            status = f"{mode_lbl}  •  Stack: ${active_br:,}  •  ★ {g_clears}/8  ♦ {im_clears}/8"
            pill_bg, pill_fg, pill_bd = "#103320", "#ffd54f", "#d4af37"

        pill_x1 = 490
        self.canvas.create_rectangle(s(pill_x1), s(9), s(self.CANVAS_W - 12), s(41), fill=pill_bg, outline=pill_bd, width=2 * k)
        self._draw_shadow_text(
            s((pill_x1 + self.CANVAS_W - 12) // 2),
            s(25),
            text=status,
            fill=pill_fg,
            font=get_badge_font(16 * k),
        )

    def _draw_winding_road(self, states: List[SalonVisualState]) -> None:
        """Draws the Super Mario World cobblestone/gold switchback road with milestone studs."""
        s = self._s
        k = self.art_scale
        for idx in range(len(SALON_SPECS) - 1):
            x1, y1 = self._map_xy(SALON_SPECS[idx])
            x2, y2 = self._map_xy(SALON_SPECS[idx + 1])
            next_discovered = states[idx + 1].discovered
            seg_cleared = states[idx].forgiving_cleared or states[idx].ironman_cleared

            mx = (x1 + x2) // 2
            my = (y1 + y2) // 2 + (-14 if idx % 2 == 0 else 14)
            pts = [s(x1), s(y1 + 12), s(mx), s(my + 12), s(x2), s(y2 + 12)]

            if seg_cleared or next_discovered:
                self.canvas.create_line(*pts, fill="#1a1208", width=16 * k, smooth=True, capstyle="round")
                self.canvas.create_line(*pts, fill="#9e7b22", width=12 * k, smooth=True, capstyle="round")
                self.canvas.create_line(*pts, fill="#ffd54f", width=4 * k, dash=(6 * k, 6 * k), smooth=True)
            else:
                self.canvas.create_line(*pts, fill="#091319", width=14 * k, smooth=True, capstyle="round")
                self.canvas.create_line(*pts, fill="#263238", width=10 * k, smooth=True, capstyle="round")
                self.canvas.create_line(*pts, fill="#546e7a", width=3 * k, dash=(4 * k, 6 * k), smooth=True)

    def _draw_salon_nodes(self, progress: VenueTourProgress, states: List[SalonVisualState]) -> None:
        """Renders all 8 2.5D salon stops, medallions, velvet ropes, and player token."""
        s = self._s
        k = self.art_scale
        for salon, st in zip(SALON_SPECS, states):
            cx, cy = self._map_xy(salon)
            hb = (s(cx - 48), s(cy - 42), s(cx + 48), s(cy + 56))
            self.node_hit_boxes[salon.index] = hb

            pad_fill = "#263829" if st.discovered else "#101a24"
            pad_bd = (
                "#00e5ff"
                if st.is_selected
                else ("#ffd700" if st.selectable else ("#ef5350" if st.velvet_rope_promoted else "#37474f"))
            )
            self.canvas.create_oval(s(cx - 40), s(cy + 8), s(cx + 40), s(cy + 28), fill="#050d08", outline="")
            self.canvas.create_oval(
                s(cx - 40), s(cy + 4), s(cx + 40), s(cy + 24),
                fill=pad_fill, outline=pad_bd, width=(3 if st.is_selected else 2) * k,
            )

            photo = self._get_landmark_photo(salon, discovered=st.discovered)
            self._photo_refs.append(photo)
            self.canvas.create_image(s(cx), s(cy - 8), image=photo, anchor="center")

            num_bg = "#ffd700" if st.selectable else ("#263238" if not st.discovered else "#37474f")
            num_fg = "#111111" if st.selectable else "#cfd8dc"
            self.canvas.create_rectangle(s(cx - 42), s(cy - 38), s(cx - 22), s(cy - 20), fill=num_bg, outline="#121016", width=k)
            self.canvas.create_text(s(cx - 32), s(cy - 29), text=f"{salon.index + 1}", fill=num_fg, font=get_badge_font(16 * k))

            if st.velvet_rope_promoted:
                for sx in (cx - 28, cx + 28):
                    self.canvas.create_rectangle(s(sx - 2), s(cy + 2), s(sx + 2), s(cy + 18), fill="#d4af37", outline="#121016")
                self.canvas.create_line(
                    s(cx - 28), s(cy + 8), s(cx), s(cy + 15), s(cx + 28), s(cy + 8),
                    fill="#d50000", width=3 * k, smooth=True,
                )

            if st.forgiving_cleared:
                draw_25d_grade_medallion(
                    self.canvas,
                    x=s(cx + 32),
                    y=s(cy - 31),
                    grade="TOUR_GOLD",
                    scale=float(k),
                    mini=True,
                    extra_tags=("tour_medallion_gold", f"tour_gold_{salon.index}"),
                )
            if st.ironman_cleared:
                im_x = cx + 32 if not st.forgiving_cleared else cx + 10
                draw_25d_grade_medallion(
                    self.canvas,
                    x=s(im_x),
                    y=s(cy - 31),
                    grade="TOUR_IRONMAN",
                    scale=float(k),
                    mini=True,
                    extra_tags=("tour_medallion_ironman", f"tour_ironman_{salon.index}"),
                )

            if st.is_current_frontier and st.selectable:
                chip_denom = 500 if progress.active_mode == "ironman" else 100
                draw_single_25d_chip(
                    self.canvas,
                    x=s(cx - 38),
                    y=s(cy + 14),
                    denom=chip_denom,
                    style=CHIP_STYLES[chip_denom],
                    scale=float(k),
                    compact=True,
                    tags=("tour_player_token",),
                )

            if st.is_selected:
                bx1, by1, bx2, by2 = s(cx - 45), s(cy - 41), s(cx + 45), s(cy + 55)
                for sx, sy, dx, dy in (
                    (bx1, by1, s(10), s(10)),
                    (bx2, by1, -s(10), s(10)),
                    (bx1, by2, s(10), -s(10)),
                    (bx2, by2, -s(10), -s(10)),
                ):
                    self.canvas.create_line(sx, sy, sx + dx, sy, fill="#00e5ff", width=2 * k)
                    self.canvas.create_line(sx, sy, sx, sy + dy, fill="#00e5ff", width=2 * k)

            title_txt = salon.short_name if st.discovered else "???"
            title_fg = (
                "#ffffff"
                if st.selectable
                else ("#b0bec5" if st.discovered else "#78909c")
            )
            if st.velvet_rope_promoted:
                sub_txt = "PROMOTED" if progress.active_mode == "ironman" else "BEAT FRONTIER"
                sub_fg = "#ff8a80"
            elif st.discovered:
                sub_txt = f"${salon.rules.minimum_bet:,}–${salon.rules.maximum_bet:,}"
                sub_fg = "#80cbc4" if st.selectable else "#90a4ae"
            else:
                sub_txt = f"Unlock: ${salon.entry_bankroll:,}"
                sub_fg = "#ffd54f"

            self.canvas.create_rectangle(
                s(cx - 52), s(cy + 22), s(cx + 52), s(cy + 56),
                fill="#081a10" if st.discovered else "#0c141c",
                outline="#00e5ff" if st.is_selected else ("#2e6b47" if st.discovered else "#263238"),
                width=k,
            )
            self._draw_shadow_text(s(cx), s(cy + 32), text=title_txt, fill=title_fg, font=get_badge_font(16 * k))
            self._draw_shadow_text(s(cx), s(cy + 47), text=sub_txt, fill=sub_fg, font=get_body_font(16 * k))

    def _draw_inspector_plaque(
        self,
        progress: VenueTourProgress,
        focused_idx: int,
        st: SalonVisualState,
        prev_discovered: bool = True,
    ) -> None:
        """Draws the bottom 2.5D Selected Salon Dossier plaque (`y = 318..384`)."""
        s = self._s
        k = self.art_scale
        salon = get_salon_spec(focused_idx)
        panel = CanvasPixelPanel(
            self.canvas,
            x=s(14),
            y=s(318),
            width=s(self.CANVAS_W - 28),
            height=s(66),
            bg="#140d09" if st.discovered else "#0d151e",
            border="#00e5ff" if st.is_selected else "#d4af37",
            inner_hi="#3b261a" if st.discovered else "#1c2c3d",
            inner_sh="#080503",
            rivet_color="#ffd700",
            scale=2 * k,
            tag="tour_inspector_panel",
        )
        self._photo_refs.append(panel)

        if not st.discovered:
            prev_salon = get_salon_spec(max(0, salon.index - 1))
            if prev_discovered:
                sub_line = (
                    f"Reach ${salon.entry_bankroll:,} inside Salon {prev_salon.index + 1} "
                    f"({prev_salon.name}) to part the velvet rope and unveil this venue!"
                )
            else:
                sub_line = (
                    f"Unveil Salon {prev_salon.index + 1} (???) and reach ${salon.entry_bankroll:,} "
                    f"there to part the velvet rope and unlock this venue!"
                )
            self._draw_shadow_text(
                s(self.CANVAS_W // 2),
                s(338),
                text=f"🔒 SALON {salon.index + 1}: ??? MYSTERY VENUE   —   UNLOCK TARGET: ${salon.entry_bankroll:,}",
                fill="#ffd54f",
                font=get_header_font(18 * k),
            )
            self._draw_shadow_text(
                s(self.CANVAS_W // 2),
                s(362),
                text=sub_line,
                fill="#cfd8dc",
                font=get_body_font(16 * k),
            )
            return

        profile = CHARACTERS.get(salon.dealer_id)
        host_name = profile.name if profile else salon.dealer_id.capitalize()
        he_pct = salon.house_edge_pct

        stamps = []
        if st.forgiving_cleared:
            stamps.append("★ Gold Cleared")
        if st.ironman_cleared:
            stamps.append("♦ Ironman Cleared")
        if st.velvet_rope_promoted:
            stamps.append(
                "🔒 Velvet Roped (Promoted)"
                if progress.active_mode == "ironman"
                else "🔒 Beat Frontier to Advance"
            )
        stamp_str = "  •  ".join(stamps) if stamps else "Open for Play"

        self._draw_shadow_text(
            s(28),
            s(337),
            text=f"SALON {salon.index + 1}: {salon.name.upper()}  ({host_name})   |   {salon.rules.short_badge()}  (HE {he_pct:.2f}%)",
            fill="#ffd700",
            font=get_badge_font(16 * k),
            anchor="w",
        )
        self._draw_shadow_text(
            s(self.CANVAS_W - 28),
            s(337),
            text=stamp_str,
            fill="#69f0ae" if (st.forgiving_cleared or st.ironman_cleared) else "#80cbc4",
            font=get_body_font(16 * k),
            anchor="e",
        )

        if progress.active_mode == "forgiving":
            floor_amt = get_forgiving_checkpoint_floor(progress)
            tu_thresh = get_top_up_threshold(progress)
            if progress.forgiving_completed:
                mode_note = f"★ VIP Free-Roam  |  Floor: ${floor_amt:,} (Top-Up <= ${tu_thresh:,})"
            elif salon.index < get_forgiving_frontier_idx(progress):
                f_spec = get_salon_spec(get_forgiving_frontier_idx(progress))
                mode_note = f"Frontier: Salon {f_spec.index + 1} (${f_spec.exit_bankroll:,})  |  Top-Up <= ${tu_thresh:,}"
            else:
                mode_note = f"Checkpoint Floor: ${floor_amt:,} (Top-Up <= ${tu_thresh:,})"
        else:
            mode_note = "Ironman: $0 Bust resets to Salon 1 ($500) — ♦ Obsidian Stamps permanent"

        self._draw_shadow_text(
            s(28),
            s(363),
            text=(
                f"Entry: ${salon.entry_bankroll:,} -> Target: ${salon.exit_bankroll:,}   |   "
                f"Limits: ${salon.rules.minimum_bet:,}-${salon.rules.maximum_bet:,}   |   {mode_note}"
            ),
            fill="#eceff1",
            font=get_body_font(16 * k),
            anchor="w",
        )

    def draw_overworld_map(self, progress: VenueTourProgress, focused_salon_idx: int) -> List[SalonVisualState]:
        """Full stateless pass rendering the 8-salon 2.5D Overworld Map."""
        self._clear()
        states = [
            get_salon_visual_state(progress, idx, focused_idx=focused_salon_idx)
            for idx in range(len(SALON_SPECS))
        ]
        self._draw_overworld_terrain()
        self._draw_header_bar(progress)
        self._draw_winding_road(states)
        self._draw_salon_nodes(progress, states)
        clamped_focus = max(0, min(len(SALON_SPECS) - 1, int(focused_salon_idx)))
        prev_idx = max(0, clamped_focus - 1)
        self._draw_inspector_plaque(
            progress,
            clamped_focus,
            states[clamped_focus],
            prev_discovered=states[prev_idx].discovered,
        )
        return states


# ============================================================================
# Controller Layer: VenueTourFrame (row=2 Host Frame & Tour Map Controller)
# ============================================================================

class VenueTourFrame(tkinter.Frame):
    """
    MVC Controller for the 2.5D Casino Venue Tour Overworld Map mounted on `row=2`
    beneath the live `DealerStageCanvas` (`row=0`, where Tour Coordinator Julian speaks).
    Centers an integer-scaled `880x390` (`1x`) or `1760x780` (`2x`) pixel-art board
    inside a full-width `#061c0e` salon frame.
    """

    CANVAS_W = VenueTourCanvasRenderer.CANVAS_W
    CANVAS_H = VenueTourCanvasRenderer.CANVAS_H

    def __init__(
        self,
        master: tkinter.Widget,
        app: Any,
        dock: TourControlDock,
        display_profile: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            background="#061c0e",
            borderwidth=0,
            highlightthickness=0,
            **kwargs,
        )
        self.app = app
        self.dock = dock
        self.focused_salon_idx: int = 0
        self._hovered_idx: Optional[int] = None
        self._timer_ids: List[Any] = []
        prof = display_profile if display_profile is not None else getattr(app, "display_profile", None)
        art_scale = max(1, int(getattr(prof, "art_scale", 1)))

        self.canvas = tkinter.Canvas(
            self,
            width=self.CANVAS_W * art_scale,
            height=self.CANVAS_H * art_scale,
            background="#072b15",
            highlightthickness=0,
            borderwidth=0,
        )
        self.canvas.pack(expand=True)
        self.renderer = VenueTourCanvasRenderer(self.canvas, art_scale=art_scale)

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Motion>", self._on_canvas_motion)

    def set_display_profile(self, profile: Any) -> None:
        """Re-scales the Overworld Map board (`880x390` at `1x`, `1760x780` at `2x`) and dock live."""
        art_scale = max(1, int(getattr(profile, "art_scale", 1)))
        self.renderer.set_art_scale(art_scale)
        self.canvas.configure(
            width=self.CANVAS_W * art_scale,
            height=self.CANVAS_H * art_scale,
        )
        self.dock.set_display_profile(profile)
        vt: VenueTourProgress = self.app.save_manager.data.venue_tour
        self.focused_salon_idx = max(0, min(len(SALON_SPECS) - 1, int(self.focused_salon_idx)))
        states = self.renderer.draw_overworld_map(vt, self.focused_salon_idx)
        salon = get_salon_spec(self.focused_salon_idx)
        self._sync_dock(vt, salon, states[self.focused_salon_idx])

    def cancel_all_timers(self) -> None:
        while self._timer_ids:
            tid = self._timer_ids.pop()
            try:
                self.after_cancel(tid)
            except Exception:
                pass

    def _coordinator_say(self, text: str) -> None:
        """Equips Tour Coordinator Julian (`julian_monte_carlo`) on `row=1` and speaks."""
        try:
            if hasattr(self.app, "dealer_actor") and self.app.dealer_actor is not None:
                self.app.dealer_actor.equip_costume("julian", costume_id=TOUR_COORDINATOR_COSTUME)
                img = self.app._get_scaled_dealer_photo() or self.app.dealer_actor.get_photo_image()
                if img and hasattr(self.app, "dealer_stage_canvas"):
                    self.app.dealer_stage_canvas.set_theme("casino")
                    self.app.dealer_stage_canvas.set_dealer_image(img)
            if hasattr(self.app, "set_dealer_speech"):
                self.app.set_dealer_speech(text, stream=True)
            if hasattr(self.app, "dealer_nameplate_label"):
                self.app.dealer_nameplate_label.configure(
                    text="🎩 Julian — Tour Coordinator",
                    fg="#ffd700",
                )
        except Exception:
            pass

    def refresh_map(self, speech_override: Optional[str] = None) -> None:
        """Re-renders the 2.5D Overworld Map, syncs dock controls, and updates top scoreboard banner."""
        vt: VenueTourProgress = self.app.save_manager.data.venue_tour
        self.focused_salon_idx = max(0, min(len(SALON_SPECS) - 1, int(self.focused_salon_idx)))
        states = self.renderer.draw_overworld_map(vt, self.focused_salon_idx)
        focused_state = states[self.focused_salon_idx]
        salon = get_salon_spec(self.focused_salon_idx)

        self._sync_dock(vt, salon, focused_state)
        if hasattr(self.app, "_update_bankroll_display"):
            self.app._update_bankroll_display()

        if speech_override is not None:
            self._coordinator_say(speech_override)
        else:
            if not focused_state.discovered:
                prev_idx = max(0, salon.index - 1)
                prev = get_salon_spec(prev_idx)
                if states[prev_idx].discovered:
                    self._coordinator_say(
                        f"Shrouded in mystery! Reach ${salon.entry_bankroll:,} at {prev.name} "
                        f"to unveil Salon {salon.index + 1}."
                    )
                else:
                    self._coordinator_say(
                        f"Shrouded in mystery! Unveil Salon {prev.index + 1} and build "
                        f"${salon.entry_bankroll:,} there to unlock Salon {salon.index + 1}."
                    )
            elif focused_state.velvet_rope_promoted:
                active_s = get_salon_spec(get_active_salon_index(vt))
                if vt.active_mode == "ironman":
                    self._coordinator_say(
                        f"You graduated past {salon.name} on this Ironman climb! "
                        f"Active frontier: {active_s.name}."
                    )
                else:
                    self._coordinator_say(
                        f"Your stack already clears {active_s.name}'s target! "
                        f"Step into {active_s.name} and win a hand to advance."
                    )
            else:
                self._coordinator_say(salon.coordinator_intro)

    def _sync_dock(
        self,
        vt: VenueTourProgress,
        salon: TourSalonSpec,
        st: SalonVisualState,
    ) -> None:
        if st.selectable:
            enter_txt = f"▶ Enter {salon.short_name} [Enter]"
            enter_theme = "gold"
        elif st.velvet_rope_promoted:
            enter_txt = (
                "🔒 Promoted (Ironman)"
                if vt.active_mode == "ironman"
                else "🔒 Play Frontier"
            )
            enter_theme = "neutral"
        else:
            enter_txt = f"🔒 Unlock ${salon.entry_bankroll:,}"
            enter_theme = "neutral"

        if vt.active_mode == "ironman":
            mode_txt = "💀 Mode: Ironman"
            mode_theme = "red"
            can_restart = (
                int(vt.ironman_stage_idx) > 0
                or int(vt.ironman_bankroll) != TOUR_STARTING_BANKROLL
            )
            top_up_spec = {
                "key": "top_up",
                "text": "↺ Reset Run ($500)",
                "theme": "amber",
                "width": 204,
                "enabled": can_restart,
                "command": self.restart_ironman_climb,
            }
        else:
            mode_txt = "🛡 Mode: Standard"
            mode_theme = "blue"
            floor_amt = get_forgiving_checkpoint_floor(vt)
            can_tu = can_top_up_forgiving(vt)
            top_up_spec = {
                "key": "top_up",
                "text": f"↺ Top Up ${floor_amt:,}",
                "theme": "amber",
                "width": 204,
                "enabled": can_tu,
                "command": self.app.top_up_tour_stake,
            }

        self.dock.set_buttons(
            [
                {
                    "key": "enter_salon",
                    "text": enter_txt,
                    "theme": enter_theme,
                    "width": 216,
                    "enabled": st.selectable,
                    "command": self.activate_focused_salon,
                },
                {
                    "key": "toggle_mode",
                    "text": mode_txt,
                    "theme": mode_theme,
                    "width": 204,
                    "enabled": True,
                    "command": self.toggle_tour_mode,
                },
                top_up_spec,
                {
                    "key": "free_play",
                    "text": "🚪 Free Play [Esc]",
                    "theme": "green",
                    "width": 180,
                    "enabled": True,
                    "command": self.app.exit_venue_tour,
                },
            ]
        )

    def move_focus(self, delta: int) -> None:
        """Moves node selection West (-1) or East (+1) along the 8-salon Overworld road."""
        self.focused_salon_idx = (self.focused_salon_idx + int(delta)) % len(SALON_SPECS)
        if hasattr(self.app, "sound_manager"):
            self.app.sound_manager.play_chip_add()
        self.refresh_map()

    def toggle_tour_mode(self) -> None:
        """Non-destructively switches between Standard ('forgiving') and Ironman ('ironman') slots."""
        vt: VenueTourProgress = self.app.save_manager.data.venue_tour
        target = "ironman" if vt.active_mode == "forgiving" else "forgiving"
        switch_tour_mode(vt, target)
        self.focused_salon_idx = get_active_salon_index(vt)
        self.app.save_manager.save_venue_tour()
        if hasattr(self.app, "sound_manager"):
            self.app.sound_manager.play_chip_stack()
        msg = (
            "Ironman Gauntlet! Zero re-buys—$0 bust resets to Salon 1, "
            "but Obsidian Medallions are permanent!"
            if target == "ironman"
            else "Standard Tour! Unlocked salons stay open and Top-Up protects your floor."
        )
        self.refresh_map(speech_override=msg)

    def _ask_confirm_ironman_reset(self) -> bool:
        """Prompts confirmation via InWindowConfirmModal before discarding an active Ironman climb."""
        try:
            top = self.winfo_toplevel()
            if (top.state() == "withdrawn") or (not top.winfo_ismapped()):
                return True
        except Exception:
            return True
        try:
            from ui_dialogs import InWindowConfirmModal

            vt: VenueTourProgress = self.app.save_manager.data.venue_tour
            cur_salon = get_salon_spec(get_active_salon_index(vt))
            return bool(
                InWindowConfirmModal.ask_yes_no(
                    parent=self.winfo_toplevel(),
                    title="Reset Ironman Gauntlet Run?",
                    message=(
                        f"Abandon your current Ironman climb at Salon {cur_salon.index + 1} "
                        f"({cur_salon.name}, Stack: ${vt.ironman_bankroll:,}) and restart at Salon 1 ($500)?\n\n"
                        f"Your {vt.ironman_salons_cleared}/8 ♦ Obsidian Medallions remain permanently saved."
                    ),
                    confirm_text="↺ Reset Run",
                    cancel_text="Keep Climbing",
                    app=self.app,
                )
            )
        except Exception:
            return True

    def restart_ironman_climb(self) -> None:
        """Resets current Ironman run to Salon 1 ($500) while keeping permanent Obsidian medallions."""
        vt: VenueTourProgress = self.app.save_manager.data.venue_tour
        if vt.active_mode != "ironman":
            return
        if int(vt.ironman_stage_idx) > 0 or int(vt.ironman_bankroll) != TOUR_STARTING_BANKROLL:
            if not self._ask_confirm_ironman_reset():
                return
        reset_ironman_run(vt)
        if hasattr(self.app, "invalidate_tour_shoe_cache"):
            self.app.invalidate_tour_shoe_cache(mode="ironman")
        self.focused_salon_idx = 0
        self.app.save_manager.save_venue_tour()
        self.refresh_map(
            speech_override="Fresh $500 Ironman stack on the felt at Salon 1! Good luck on the gauntlet."
        )

    def activate_focused_salon(self) -> bool:
        """Enters `self.focused_salon_idx` if selectable in the active Tour mode."""
        vt: VenueTourProgress = self.app.save_manager.data.venue_tour
        idx = self.focused_salon_idx
        if not can_select_salon(vt, idx):
            st = get_salon_visual_state(vt, idx, focused_idx=idx)
            salon = get_salon_spec(idx)
            if st.velvet_rope_promoted:
                active_s = get_salon_spec(get_active_salon_index(vt))
                if vt.active_mode == "ironman":
                    self._coordinator_say(
                        f"{salon.name} is roped off—in Ironman Mode you can only play your active frontier ({active_s.name})!"
                    )
                else:
                    self._coordinator_say(
                        f"Your stack already meets {active_s.name}'s target! Step into {active_s.name} and win a hand to unlock the next salon."
                    )
            else:
                self._coordinator_say(
                    f"Salon {idx + 1} requires a ${salon.entry_bankroll:,} stack in the prior salon first!"
                )
            return False

        if vt.active_mode == "forgiving":
            vt.forgiving_selected_idx = idx
            self.app.save_manager.save_venue_tour()
        self.app.enter_tour_salon(idx)
        return True

    def on_map_click(self, x: int, y: int) -> None:
        """Single-source geometric click dispatcher: first click focuses a stop; clicking focused stop enters it."""
        for idx, (x1, y1, x2, y2) in self.renderer.node_hit_boxes.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if self.focused_salon_idx == idx:
                    self.activate_focused_salon()
                else:
                    self.focused_salon_idx = idx
                    if hasattr(self.app, "sound_manager"):
                        self.app.sound_manager.play_chip_add()
                    self.refresh_map()
                return

    def _on_canvas_click(self, event: Any) -> None:
        self.on_map_click(int(event.x), int(event.y))

    def _on_canvas_motion(self, event: Any) -> None:
        x, y = int(event.x), int(event.y)
        hovered: Optional[int] = None
        for idx, (x1, y1, x2, y2) in self.renderer.node_hit_boxes.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                hovered = idx
                break
        if hovered != self._hovered_idx:
            self._hovered_idx = hovered
            try:
                self.canvas.configure(cursor="hand2" if hovered is not None else "")
            except Exception:
                pass

    def handle_key_event(self, keysym: str) -> bool:
        """Routes Overworld Map keyboard shortcuts (`Left`/`Right`/`Up`/`Down`, `Enter`/`Space`, `Escape`, `1`–`8`)."""
        key = str(keysym)
        if key == "Escape":
            self.app.exit_venue_tour()
            return True
        if key in ("Return", "KP_Enter", "space"):
            self.activate_focused_salon()
            return True
        if key in ("Right", "Down"):
            self.move_focus(1)
            return True
        if key in ("Left", "Up"):
            self.move_focus(-1)
            return True
        if key in ("1", "2", "3", "4", "5", "6", "7", "8"):
            self.focused_salon_idx = int(key) - 1
            self.refresh_map()
            return True
        return False
