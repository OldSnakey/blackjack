"""
Haunted Atmosphere & Psychological Dread Subsystem.

Encapsulates all escalating horror presentation for Haunted / Cursed Mode:
- Subliminal buildup cues (220-300ms court-card center-art shifts, bleeding-heart
  pip drips, 220ms Malphas silhouette flashes, 350ms felt-text flickers, reactive
  stage-ceiling spider, and rare perimeter millipede).
- Skippable ~1.4s Pit Boss power-outage blackout transition (_BlackoutVeilOverlay).
- Persistent Soul-Meter-linked HELL_TABLE perimeter black mold & iron spike decals
  ("haunted_decal", 0% idle CPU, zero TableFeltCanvas._felt_cache churn).
- Tempo-scaled cached heartbeat.ogg (< 25% Soul) and dry Pit Fiend hesitation taunts.
- Orthogonal comfort controls (Haunted Scares: full/reduced, Crawling Bugs: True/False).
"""

from __future__ import annotations

import random
import time
import tkinter
from typing import Any, Callable, Optional

from audio_assets import AssetScaler
from config import HAUNTED_ASSETS_DIR, VALID_HAUNTED_SCARES_MODES
from haunted_manager import Phase
from state_machine import RoundPhase
from ui_dialogs import InWindowScreenHost

try:
    from PIL import Image, ImageDraw, ImageTk

    PIL_AVAILABLE = True
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageTk = None  # type: ignore[assignment]
    PIL_AVAILABLE = False


# ============================================================================
# Pure Headless Helper Functions
# ============================================================================

def compute_corruption_tier(phase: Phase, soul_meter: float) -> int:
    """
    Maps (HauntedManager.Phase, soul_meter 0.0..1.0) to a static decal tier (0..3).
    Non-HELL_TABLE phases always return 0 (no decals).
    """
    if phase != Phase.HELL_TABLE:
        return 0
    s = float(soul_meter)
    if s >= 0.75:
        return 0
    if s >= 0.50:
        return 1
    if s >= 0.25:
        return 2
    return 3


def compute_heartbeat_interval_ms(soul_meter: float) -> Optional[int]:
    """
    Returns heartbeat interval in ms when soul_meter < 0.25, else None.
    Linearly ramps from ~950ms just below 0.25 down to 580ms at <= 0.10.
    """
    s = float(soul_meter)
    if s >= 0.25:
        return None
    if s <= 0.10:
        return 580
    ratio = (s - 0.10) / 0.15
    ms = int(round(580.0 + ratio * (950.0 - 580.0)))
    return max(580, min(950, ms))


def compute_center_crop_box(card_w: int, card_h: int) -> tuple[int, int, int, int]:
    """
    Returns the inner ~60% bounding box (x0, y0, x1, y1) preserving 20% corner
    rank and suit index margins on every side.
    """
    mx = int(round(card_w * 0.20))
    my = int(round(card_h * 0.20))
    return (mx, my, max(mx + 4, card_w - mx), max(my + 4, card_h - my))


# ============================================================================
# Constants & Anchor Tables
# ============================================================================

AMBIENT_POLL_MS = 2500
CONFIGURE_DEBOUNCE_MS = 80
HESITATION_DELAY_MS = 11000
GLOBAL_GLITCH_COOLDOWN_RANGE_S = (6.0, 8.0)
SPIDER_COOLDOWN_RANGE_S = (18.0, 30.0)
MILLIPEDE_COOLDOWN_RANGE_S = (25.0, 40.0)

PHASE_POLL_PROBABILITY = {
    Phase.CREEP: 0.20,
    Phase.OMEN: 0.30,
    Phase.SNUFFING: 0.38,
    Phase.HELL_TABLE: 0.38,
}

HESITATION_TAUNTS = (
    "Staring at the felt will not change the card underneath.",
    "Take your time. The debt collects interest either way.",
    "Every second you wait, the candles remember your name.",
    "Hit or stand. The house already knows the outcome.",
)

FELT_FLICKER_LINES = (
    "THE HOUSE CLAIMS ALL",
    "DO NOT LOOK UP",
    "THE DEALER NEVER LOSES",
    "YOUR SOUL IS ON THE LINE",
)

# 12 normalized perimeter anchors (rx, ry, sprite_kind, min_tier) inside
# app.get_unobstructed_felt_bounds(). Top-right anchors stay at ry >= 0.28
# to remain strictly clear of TableFeltCanvas.draw_shoe_tray().
DECAL_ANCHORS: tuple[tuple[float, float, str, int], ...] = (
    # Tier 1 (2 opposing corner molds)
    (0.08, 0.14, "mold_0", 1),
    (0.92, 0.86, "mold_1", 1),
    # Tier 2 (+2 corner molds + 3 balanced perimeter spikes)
    (0.08, 0.86, "mold_2", 2),
    (0.92, 0.30, "mold_3", 2),
    (0.04, 0.50, "spike_0", 2),
    (0.96, 0.56, "spike_1", 2),
    (0.22, 0.94, "spike_2", 2),
    # Tier 3 (+2 bottom molds + 3 perimeter spikes)
    (0.26, 0.92, "mold_3", 3),
    (0.74, 0.92, "mold_0", 3),
    (0.04, 0.32, "spike_1", 3),
    (0.96, 0.72, "spike_0", 3),
    (0.78, 0.94, "spike_2", 3),
)

ALL_HAUNTED_CANVAS_TAGS = (
    "haunted_glitch_overlay",
    "haunted_felt_flicker",
    "haunted_dealer_flash",
    "haunted_spider",
    "haunted_millipede",
    "haunted_decal",
)

TRANSIENT_FELT_TAGS = (
    "haunted_glitch_overlay",
    "haunted_felt_flicker",
    "haunted_millipede",
)

TRANSIENT_STAGE_TAGS = (
    "haunted_dealer_flash",
    "haunted_spider",
)


# ============================================================================
# Procedural 16-Bit Pixel Sprite Synthesizers
# ============================================================================

def _nearest_scale(img: Any, scale: int) -> Any:
    if scale <= 1 or Image is None:
        return img
    resampling = getattr(Image, "Resampling", Image)
    return img.resize((img.width * scale, img.height * scale), resampling.NEAREST)


def _build_spider_pil(frame: int) -> Any:
    """Synthesizes a high-contrast 22x22 RGBA pixel spider with silver-lavender rim & crimson eyes."""
    img = Image.new("RGBA", (22, 22), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    outline = (10, 6, 14, 255)
    body = (38, 28, 48, 255)
    rim = (154, 140, 180, 255)
    mark = (188, 28, 42, 255)
    eye = (255, 48, 64, 255)

    # Abdomen with lavender-silver rim highlight and subtle crimson hourglass mark
    d.ellipse([6, 2, 15, 11], fill=outline)
    d.ellipse([7, 3, 14, 10], fill=body)
    d.arc([7, 3, 14, 10], start=200, end=340, fill=rim)
    d.point((10, 6), fill=mark)
    d.point((11, 6), fill=mark)
    d.point((10, 7), fill=mark)
    d.point((11, 7), fill=mark)

    # Cephalothorax + 2x2 glowing crimson eyes
    d.ellipse([7, 10, 14, 16], fill=outline)
    d.ellipse([8, 11, 13, 15], fill=body)
    d.rectangle([8, 13, 9, 14], fill=eye)
    d.rectangle([12, 13, 13, 14], fill=eye)

    # 8 chunky articulated legs with rim knee highlights
    dy = 0 if frame == 0 else 2
    leg_coords = [
        [(7, 6), (4, 3 + dy), (1, 5 + dy)],
        [(7, 9), (3, 7 - dy), (0, 10 - dy)],
        [(8, 12), (4, 13 + dy), (1, 16 + dy)],
        [(8, 14), (5, 17 - dy), (3, 20)],
        [(14, 6), (17, 3 - dy), (20, 5 - dy)],
        [(14, 9), (18, 7 + dy), (21, 10 + dy)],
        [(13, 12), (17, 13 - dy), (20, 16 - dy)],
        [(13, 14), (16, 17 + dy), (18, 20)],
    ]
    for pts in leg_coords:
        d.line(pts, fill=outline, width=2)
        d.point(pts[1], fill=rim)
    return img


def _build_millipede_pil(frame: int) -> Any:
    """Synthesizes a high-contrast 32x16 RGBA pixel millipede with warm ochre/bone carapace."""
    img = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    shadow = (8, 5, 10, 160)
    outline = (16, 10, 14, 255)
    seg_dark = (88, 54, 36, 255)
    seg_ochre = (184, 130, 84, 255)
    seg_hi = (216, 166, 112, 255)
    head_col = (146, 36, 36, 255)
    eye = (255, 68, 68, 255)

    # Soft underside drop-shadow for crisp separation against dark baize
    d.ellipse([2, 10, 29, 14], fill=shadow)

    # 7 articulated glossy carapace segments
    for idx, sx in enumerate((2, 5, 8, 11, 14, 17, 20)):
        d.rectangle([sx, 5, sx + 3, 10], fill=outline)
        d.rectangle([sx + 1, 6, sx + 2, 9], fill=seg_ochre if idx % 2 == 0 else seg_dark)
        d.point((sx + 1, 6), fill=seg_hi)
        # Alternating scurrying legs
        leg_x = sx + (1 if (idx + frame) % 2 == 0 else 2)
        d.line([(leg_x, 4), (leg_x, 2 if (idx + frame) % 2 == 0 else 3)], fill=outline, width=1)
        d.line([(leg_x, 11), (leg_x, 13 if (idx + frame) % 2 == 0 else 12)], fill=outline, width=1)

    # Crimson head + mandibles + antennae on right
    d.rectangle([23, 5, 27, 10], fill=outline)
    d.rectangle([24, 6, 26, 9], fill=head_col)
    d.point((25, 6), fill=eye)
    d.line([(27, 6), (30, 3 if frame == 0 else 4)], fill=seg_hi, width=1)
    d.line([(27, 9), (30, 12 if frame == 0 else 11)], fill=seg_hi, width=1)
    return img


def _build_mold_pil(variant: int = 0) -> Any:
    """Synthesizes 4 organic 16-bit creeping black-mold variants with sickly-olive/ash spore rims."""
    large = variant in (0, 1)
    w, h = (56, 40) if large else (44, 34)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    seeds = (1337, 2468, 7331, 9012)
    rng = random.Random(seeds[variant % len(seeds)])

    rim_olive = (54, 60, 42, 185)
    rim_ash = (66, 48, 54, 165)
    mid = (24, 18, 28, 215)
    core = (10, 7, 12, 240)

    cx, cy = w // 2, h // 2
    # Outer sickly-olive / ashy spore halo
    for _ in range(16 if large else 12):
        ox = rng.randint(-w // 3, w // 3)
        oy = rng.randint(-h // 3, h // 3)
        rx = rng.randint(5, 12 if large else 9)
        ry = rng.randint(4, 9 if large else 7)
        d.ellipse([cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry], fill=rng.choice((rim_olive, rim_ash)))

    # Mid dark creeping tendrils
    for _ in range(14 if large else 10):
        ox = rng.randint(-w // 4, w // 4)
        oy = rng.randint(-h // 4, h // 4)
        rx = rng.randint(4, 9 if large else 7)
        ry = rng.randint(3, 7 if large else 5)
        d.ellipse([cx + ox - rx, cy + oy - ry, cx + ox + rx, cy + oy + ry], fill=mid)

    # Wet-rot dark inner heart
    d.ellipse([cx - 10, cy - 7, cx + 10, cy + 7], fill=core)

    # Scattered outer spore specks
    for _ in range(34 if large else 24):
        px = rng.randint(1, w - 2)
        py = rng.randint(1, h - 2)
        if abs(px - cx) < w * 0.48 and abs(py - cy) < h * 0.48:
            d.rectangle([px, py, min(w - 1, px + 1), min(h - 1, py + 1)], fill=rim_olive)

    if variant in (1, 3):
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    return img


def _build_spike_pil(variant: int = 0) -> Any:
    """Synthesizes 3 jagged 20x24 iron/obsidian spike variants erupting from torn crimson felt."""
    img = Image.new("RGBA", (20, 24), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    crater = (10, 5, 10, 240)
    flap = (92, 24, 34, 230)
    outline = (14, 10, 18, 255)
    iron_dark = (46, 40, 54, 255)
    iron_mid = (98, 90, 110, 255)
    iron_hi = (200, 190, 207, 255)
    crimson_tip = (216, 40, 56, 255)

    # Wider ragged felt-tear crater + torn crimson felt flaps
    d.ellipse([2, 16, 17, 23], fill=crater)
    d.polygon([(1, 19), (5, 16), (4, 21)], fill=flap)
    d.polygon([(18, 19), (14, 16), (15, 21)], fill=flap)

    def _draw_barb(tip_x: int, tip_y: int, base_l: int, base_r: int, base_y: int) -> None:
        mid_x = (base_l + base_r) // 2
        d.polygon([(tip_x, tip_y), (base_r + 1, base_y), (base_l - 1, base_y)], fill=outline)
        d.polygon([(tip_x, tip_y + 1), (base_r, base_y - 1), (base_l, base_y - 1)], fill=iron_dark)
        d.polygon([(tip_x, tip_y + 2), (mid_x, base_y - 1), (base_l + 1, base_y - 1)], fill=iron_mid)
        d.line([(tip_x, tip_y + 2), (base_l + 2, base_y - 2)], fill=iron_hi, width=1)
        d.rectangle([tip_x, tip_y, min(19, tip_x), min(23, tip_y + 2)], fill=crimson_tip)

    if variant == 0:
        # Left-leaning primary spike
        _draw_barb(7, 2, 5, 14, 20)
    elif variant == 1:
        # Right-leaning primary spike
        _draw_barb(13, 2, 6, 15, 20)
    else:
        # Twin-barb cluster
        _draw_barb(6, 6, 3, 10, 20)
        _draw_barb(13, 2, 9, 16, 20)
    return img


def _build_bleeding_heart_pil() -> Any:
    """Synthesizes a 28x32 crimson heart pip with dark ink-blood drips."""
    img = Image.new("RGBA", (28, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark_red = (108, 12, 22, 245)
    crimson = (188, 22, 34, 250)
    bright = (232, 54, 62, 255)
    drip_dark = (74, 8, 16, 235)

    # Classic pixel heart silhouette
    d.ellipse([4, 3, 14, 13], fill=dark_red)
    d.ellipse([14, 3, 24, 13], fill=dark_red)
    d.polygon([(4, 9), (24, 9), (14, 22)], fill=dark_red)

    d.ellipse([5, 4, 13, 12], fill=crimson)
    d.ellipse([15, 4, 23, 12], fill=crimson)
    d.polygon([(5, 9), (23, 9), (14, 20)], fill=crimson)
    d.rectangle([7, 6, 9, 8], fill=bright)

    # Dripping crimson streaks beneath heart
    d.rectangle([13, 20, 15, 29], fill=dark_red)
    d.rectangle([14, 21, 14, 28], fill=crimson)
    d.rectangle([13, 29, 15, 31], fill=drip_dark)

    d.rectangle([8, 14, 9, 25], fill=dark_red)
    d.point((8, 26), fill=drip_dark)

    d.rectangle([19, 15, 20, 23], fill=dark_red)
    d.point((20, 24), fill=drip_dark)
    return img


def _build_blackout_eyes_pil() -> Any:
    """Synthesizes dramatic 144x44 glowing crimson demon eyes framed by a faint horned-brow shadow."""
    img = Image.new("RGBA", (144, 44), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    brow_shadow = (18, 7, 12, 210)
    glow_far = (74, 6, 14, 130)
    glow_mid = (154, 16, 30, 220)
    core = (255, 50, 64, 255)
    pupil = (255, 214, 200, 255)

    # Faint horned-brow framing silhouette
    d.polygon([(12, 14), (32, 3), (42, 16)], fill=brow_shadow)
    d.polygon([(132, 14), (112, 3), (102, 16)], fill=brow_shadow)
    d.polygon([(24, 16), (72, 25), (120, 16), (110, 38), (34, 38)], fill=brow_shadow)

    # Left brow-slanted demon eye
    d.polygon([(18, 17), (44, 14), (62, 25), (42, 33), (24, 28)], fill=glow_far)
    d.polygon([(24, 19), (44, 17), (58, 25), (42, 30), (28, 26)], fill=glow_mid)
    d.polygon([(31, 21), (45, 20), (53, 25), (43, 27), (33, 25)], fill=core)
    d.rectangle([41, 20, 43, 27], fill=pupil)

    # Right brow-slanted demon eye (mirrored)
    d.polygon([(126, 17), (100, 14), (82, 25), (102, 33), (120, 28)], fill=glow_far)
    d.polygon([(120, 19), (100, 17), (86, 25), (102, 30), (116, 26)], fill=glow_mid)
    d.polygon([(113, 21), (99, 20), (91, 25), (101, 27), (111, 25)], fill=core)
    d.rectangle([100, 20, 102, 27], fill=pupil)
    return img


def _build_malphas_flash_pil(art_scale: int) -> Any:
    """
    Derives a dark Malphas silhouette + glowing crimson eyes from bundled
    assets/haunted/characters/malphas/bust.png (falling back to procedural
    112x112 silhouette if missing). Stamps crimson eyes inside Malphas's
    canonical 112x112 sockets (x=45..50, y=37..38 and x=61..66, y=37..38),
    upscales by 2 * art_scale via NEAREST, trims transparent top air via
    getbbox(), and bottom-crops to max_h = 214 * art_scale (matching
    BlackjackApp._get_scaled_dealer_photo force_2x=True).
    """
    bust_path = HAUNTED_ASSETS_DIR / "characters" / "malphas" / "bust.png"
    base_112 = Image.new("RGBA", (112, 112), (0, 0, 0, 0))
    loaded = False
    if bust_path.exists():
        try:
            with Image.open(bust_path) as raw:
                rgba = raw.convert("RGBA")
                if rgba.size != (112, 112):
                    resampling = getattr(Image, "Resampling", Image)
                    rgba = rgba.resize((112, 112), resampling.NEAREST)
                alpha = rgba.getchannel("A")
                sil = Image.new("RGBA", (112, 112), (11, 7, 14, 235))
                base_112 = Image.new("RGBA", (112, 112), (0, 0, 0, 0))
                base_112.paste(sil, (0, 0), alpha)
                loaded = True
        except Exception:
            loaded = False

    if not loaded:
        d_fb = ImageDraw.Draw(base_112)
        # Minimal horned silhouette fallback
        d_fb.polygon([(36, 18), (42, 30), (38, 34)], fill=(11, 7, 14, 235))
        d_fb.polygon([(76, 18), (70, 30), (74, 34)], fill=(11, 7, 14, 235))
        d_fb.ellipse([38, 24, 74, 62], fill=(11, 7, 14, 235))
        d_fb.polygon([(22, 111), (36, 62), (76, 62), (90, 111)], fill=(11, 7, 14, 235))

    # Stamp glowing crimson eyes inside canonical 112x112 Malphas sockets
    # (dealer_actor.py: x=45..50, y=37..38 and x=61..66, y=37..38)
    d = ImageDraw.Draw(base_112)
    glow = (176, 20, 34, 255)
    core = (255, 52, 64, 255)
    d.rectangle([45, 37, 50, 38], fill=glow)
    d.rectangle([47, 37, 48, 38], fill=core)
    d.rectangle([61, 37, 66, 38], fill=glow)
    d.rectangle([63, 37, 64, 38], fill=core)

    scale_mult = max(1, int(art_scale)) * 2
    scaled = _nearest_scale(base_112, scale_mult)

    # Match _get_scaled_dealer_photo(): trim transparent top air, then bottom-crop to 214 * art_scale
    bbox = scaled.getbbox()
    if bbox and bbox[1] > 0:
        scaled = scaled.crop((0, bbox[1], scaled.width, scaled.height))
    max_h = 214 * max(1, int(art_scale))
    if scaled.height > max_h:
        scaled = scaled.crop((0, 0, scaled.width, max_h))
    return scaled


# ============================================================================
# Full-Viewport Pit Boss Blackout Veil (InWindowScreenHost Subclass)
# ============================================================================

class _BlackoutVeilOverlay(InWindowScreenHost):
    """
    Full-viewport dark power-outage veil mounted on root._active_inwindow_screens.
    Blocks live table inputs & root menu shortcuts while allowing instant skip on
    click, Enter, Space, Escape, or Gamepad A/B.
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        on_skip: Callable[[], None],
        skip_hint: str = "Click / Space / Esc to Skip",
        hint_px: int = 16,
    ):
        super().__init__(parent, bg="#060408", overlay_wh=None)
        self._on_skip = on_skip
        self._skipped = False
        self._eyes_photo: Optional[Any] = None
        self._skip_hint_text = skip_hint
        self._hint_px = max(12, int(hint_px))

        self.canvas = tkinter.Canvas(
            self,
            bg="#060408",
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.protocol("WM_DELETE_WINDOW", self._trigger_skip)

        for widget in (self, self.canvas):
            widget.bind("<Button-1>", self._on_skip_event)
            widget.bind("<Return>", self._on_skip_event)
            widget.bind("<KP_Enter>", self._on_skip_event)
            widget.bind("<space>", self._on_skip_event)
            widget.bind("<Escape>", self._on_skip_event)
            widget.bind("<Key>", self._on_any_key)

        try:
            self.focus_set()
        except Exception:
            pass

        # Guarded Tk grab (only when viewable/mapped; never call InWindowScreenHost no-op grab_release)
        try:
            if self.winfo_ismapped():
                tkinter.Widget.grab_set(self)
                self._has_grab = True
        except Exception:
            pass

        self._draw_skip_hint()

    def _trigger_skip(self) -> None:
        if self._skipped:
            return
        self._skipped = True
        try:
            self._on_skip()
        except Exception:
            pass

    def _on_skip_event(self, _event=None) -> str:
        self._trigger_skip()
        return "break"

    def _on_any_key(self, event=None) -> Optional[str]:
        keysym = getattr(event, "keysym", "")
        if keysym == "F11":
            return None
        if keysym in ("Return", "KP_Enter", "space", "Escape"):
            self._trigger_skip()
        return "break"

    def handle_modal_key(self, event=None) -> str:
        keysym = getattr(event, "keysym", "")
        if keysym in ("Return", "KP_Enter", "space", "Escape", ""):
            self._trigger_skip()
        return "break"

    def set_veil_color(self, hex_color: str) -> None:
        try:
            if self.winfo_exists():
                self.configure(bg=hex_color)
                self.canvas.configure(bg=hex_color)
        except Exception:
            pass

    def _resolve_canvas_size(self, size: Optional[tuple[int, int]] = None) -> tuple[int, int]:
        if size is not None and size[0] > 10 and size[1] > 10:
            return (int(size[0]), int(size[1]))
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 10:
            cw = self.winfo_width() if self.winfo_width() > 10 else self.master.winfo_width()
        if ch <= 10:
            ch = self.winfo_height() if self.winfo_height() > 10 else self.master.winfo_height()
        return (max(100, cw or 1280), max(100, ch or 800))

    def _draw_skip_hint(self, size: Optional[tuple[int, int]] = None) -> None:
        try:
            if not self.winfo_exists() or not self.canvas.winfo_exists():
                return
            self.canvas.delete("blackout_skip_hint")
            w, h = self._resolve_canvas_size(size)
            self.canvas.create_text(
                w // 2,
                h - max(22, int(self._hint_px * 1.6)),
                text=self._skip_hint_text,
                fill="#685862",
                font=("Tiny5", -self._hint_px, "normal"),
                anchor="center",
                state="disabled",
                tags="blackout_skip_hint",
            )
        except Exception:
            pass

    def _on_canvas_configure(self, event=None) -> None:
        ev_size = (event.width, event.height) if event is not None else None
        self._draw_skip_hint(size=ev_size)
        if self._eyes_photo is not None:
            self.show_crimson_eyes(self._eyes_photo, size=ev_size)

    def show_crimson_eyes(self, photo: Optional[Any], size: Optional[tuple[int, int]] = None) -> None:
        self._eyes_photo = photo
        try:
            if not self.winfo_exists() or not self.canvas.winfo_exists():
                return
            self.canvas.delete("blackout_eyes")
            if photo is None:
                return
            w, h = self._resolve_canvas_size(size)
            self.canvas.create_image(
                w // 2,
                int(h * 0.44),
                image=photo,
                anchor="center",
                tags="blackout_eyes",
            )
        except Exception:
            pass

    def on_display_profile_changed(self, photo: Optional[Any]) -> None:
        try:
            self.sync_to_viewport()
        except Exception:
            pass
        if self._eyes_photo is not None or photo is not None:
            self.show_crimson_eyes(photo if photo is not None else self._eyes_photo)

    def destroy(self) -> None:
        if getattr(self, "_has_grab", False):
            try:
                tkinter.Widget.grab_release(self)
            except Exception:
                pass
            self._has_grab = False
        super().destroy()


# ============================================================================
# Main Atmosphere Controller
# ============================================================================

class HauntedAtmosphereController:
    """
    Decoupled presentation controller for Haunted / Cursed Mode psychological dread.
    Owns a single _timers registry, zero timers in Phase.NORMAL/VICTORY/DEFEAT,
    and deterministic cleanup via cancel_all().
    """

    def __init__(
        self,
        root: tkinter.Misc,
        app: Any,
        sound_manager: Any,
        scares_mode: str = "full",
        show_bugs: bool = True,
    ):
        self.root = root
        self.app = app
        self.sound_manager = sound_manager
        self.scares_mode: str = (
            scares_mode if scares_mode in VALID_HAUNTED_SCARES_MODES else "full"
        )
        self.show_bugs: bool = bool(show_bugs)

        self._timers: dict[str, str] = {}
        self._phase: Phase = Phase.NORMAL
        self._soul_meter: float = 0.5
        self._corruption_tier: int = 0

        # Cooldowns & runtime state
        self._last_glitch_ts: float = 0.0
        self._next_glitch_cooldown_s: float = 6.5
        self._last_spider_ts: float = 0.0
        self._next_spider_cooldown_s: float = 20.0
        self._last_millipede_ts: float = 0.0
        self._next_millipede_cooldown_s: float = 28.0
        self._active_transient_glitch: bool = False

        # Hesitation taunt state
        self._hesitation_fired_this_turn: bool = False
        self._last_taunt_idx: int = -1

        # Blackout state
        self._in_blackout: bool = False
        self._blackout_token: int = 0
        self._blackout_overlay: Optional[_BlackoutVeilOverlay] = None
        self._blackout_skip_cb: Optional[Callable[[], None]] = None

        # Spider & millipede animation state (reuse canvas item IDs per frame)
        self._spider_recoil_active: bool = False
        self._spider_x: int = 0
        self._spider_y: int = 0
        self._spider_target_y: int = 0
        self._spider_line_id: Optional[int] = None
        self._spider_img_id: Optional[int] = None
        self._millipede_img_id: Optional[int] = None
        self._last_flicker_idx: int = -1

        # Sprite PhotoImage caches
        self._scale_sprite_cache: dict[tuple[str, int], Any] = {}
        self._card_overlay_cache: dict[tuple[str, int, int], Any] = {}
        self._active_decal_photos: list[Any] = []
        self._active_felt_flicker_photo: Optional[Any] = None
        self._active_card_glitch_photo: Optional[Any] = None
        self._active_dealer_flash_photo: Optional[Any] = None

        # Bind debounced <Configure> on card_table_frame with add="+" so _on_resize is preserved
        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is not None:
            try:
                canvas.bind("<Configure>", self._on_felt_configure, add="+")
            except Exception:
                pass

    @property
    def is_blackout_active(self) -> bool:
        return self._in_blackout

    # ------------------------------------------------------------------------
    # Timer Registry Helpers
    # ------------------------------------------------------------------------

    def _schedule(self, key: str, delay_ms: int, callback: Callable[[], None]) -> None:
        self._cancel_timer(key)
        try:
            self._timers[key] = self.root.after(max(1, int(delay_ms)), callback)
        except Exception:
            self._timers.pop(key, None)

    def _cancel_timer(self, key: str) -> None:
        tid = self._timers.pop(key, None)
        if tid:
            try:
                self.root.after_cancel(tid)
            except Exception:
                pass

    def _get_art_scale(self) -> int:
        profile = getattr(self.app, "display_profile", None)
        if profile is not None:
            return max(1, int(getattr(profile, "art_scale", 1)))
        return 1

    def _get_card_scale(self) -> float:
        profile = getattr(self.app, "display_profile", None)
        if profile is not None:
            return float(getattr(profile, "card_scale", 1.0))
        return 1.0

    @staticmethod
    def _raise_above_felt_bg(canvas: Any, tag: str) -> None:
        """Places tag strictly above felt_bg if present, else lowers tag to bottom."""
        try:
            if canvas.find_withtag("felt_bg"):
                canvas.tag_raise(tag, "felt_bg")
            else:
                canvas.tag_lower(tag)
        except Exception:
            pass

    # ------------------------------------------------------------------------
    # Central Gate & Comfort Settings
    # ------------------------------------------------------------------------

    def _can_run_effect(self, ignore_mapped: bool = False) -> bool:
        if getattr(self.app, "table_seats", 1) != 1:
            return False
        if getattr(self.app, "bootcamp_active", False):
            return False
        if getattr(self.app, "tour_active", False):
            return False
        haunted = getattr(self.app, "haunted", None)
        live_phase = getattr(haunted, "phase", self._phase) if haunted is not None else self._phase
        if live_phase not in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING, Phase.HELL_TABLE):
            return False
        if self._in_blackout:
            return False
        has_modal = getattr(self.app, "_has_open_modal_dialog", None)
        if callable(has_modal) and has_modal():
            return False
        if not ignore_mapped:
            try:
                if not self.root.winfo_ismapped():
                    return False
            except Exception:
                return False
        return True

    def apply_comfort_settings(self, scares_mode: str, show_bugs: bool) -> None:
        """Applies comfort toggles live, cancelling any now-disallowed effects immediately."""
        self.scares_mode = (
            scares_mode if scares_mode in VALID_HAUNTED_SCARES_MODES else "full"
        )
        self.show_bugs = bool(show_bugs)

        if self.scares_mode == "reduced":
            self._cancel_timer("glitch_restore")
            self._active_transient_glitch = False
            self._delete_felt_tags(("haunted_glitch_overlay", "haunted_felt_flicker"))
            self._delete_stage_tags(("haunted_dealer_flash",))

        if not self.show_bugs:
            self._cancel_timer("spider_anim")
            self._cancel_timer("millipede_anim")
            self._spider_recoil_active = False
            self._delete_stage_tags(("haunted_spider",))
            self._delete_felt_tags(("haunted_millipede",))

    def _delete_felt_tags(self, tags: tuple[str, ...]) -> None:
        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is None:
            return
        for tag in tags:
            try:
                canvas.delete(tag)
            except Exception:
                pass

    def _delete_stage_tags(self, tags: tuple[str, ...]) -> None:
        stage = getattr(self.app, "dealer_stage_canvas", None)
        if stage is None:
            return
        for tag in tags:
            try:
                stage.delete(tag)
            except Exception:
                pass

    # ------------------------------------------------------------------------
    # Sprite Cache Accessors
    # ------------------------------------------------------------------------

    def _get_blackout_eyes_scale(self) -> int:
        art_s = self._get_art_scale()
        profile = getattr(self.app, "display_profile", None)
        win_w = int(getattr(profile, "window_w", 1280)) if profile is not None else 1280
        if art_s >= 2:
            return 3
        if win_w >= 1800:
            return 2
        return 1

    def _get_scaled_sprite(self, name: str, art_scale: int) -> Optional[Any]:
        if not PIL_AVAILABLE or Image is None or ImageTk is None:
            return None
        key = (name, art_scale)
        cached = self._scale_sprite_cache.get(key)
        if cached is not None:
            return cached

        pil_img = None
        if name == "spider_0":
            pil_img = _nearest_scale(_build_spider_pil(0), art_scale)
        elif name == "spider_1":
            pil_img = _nearest_scale(_build_spider_pil(1), art_scale)
        elif name == "millipede_0":
            pil_img = _nearest_scale(_build_millipede_pil(0), art_scale)
        elif name == "millipede_1":
            pil_img = _nearest_scale(_build_millipede_pil(1), art_scale)
        elif name.startswith("mold_"):
            try:
                variant = int(name.split("_")[1])
            except Exception:
                variant = 0
            pil_img = _nearest_scale(_build_mold_pil(variant=variant), art_scale)
        elif name.startswith("spike_"):
            try:
                variant = int(name.split("_")[1])
            except Exception:
                variant = 0
            pil_img = _nearest_scale(_build_spike_pil(variant=variant), art_scale)
        elif name == "spike":
            pil_img = _nearest_scale(_build_spike_pil(variant=0), art_scale)
        elif name == "blackout_eyes":
            pil_img = _nearest_scale(_build_blackout_eyes_pil(), art_scale)
        elif name == "malphas_flash":
            pil_img = _build_malphas_flash_pil(art_scale)

        if pil_img is None:
            return None
        try:
            photo = ImageTk.PhotoImage(pil_img, master=self.root)
            self._scale_sprite_cache[key] = photo
            return photo
        except Exception:
            return None

    def _get_card_glitch_photo(self, kind: str, card_w: int, card_h: int) -> Optional[Any]:
        if not PIL_AVAILABLE or Image is None or ImageTk is None:
            return None
        key = (kind, int(card_w), int(card_h))
        cached = self._card_overlay_cache.get(key)
        if cached is not None:
            return cached

        x0, y0, x1, y1 = compute_center_crop_box(card_w, card_h)
        crop_w = max(4, x1 - x0)
        crop_h = max(4, y1 - y0)

        pil_out = None
        if kind in ("jack", "queen", "king"):
            master_path = HAUNTED_ASSETS_DIR / f"{kind}_haunted_1.png"
            if master_path.exists():
                try:
                    with Image.open(master_path) as raw_im:
                        src_rgba = raw_im.convert("RGBA")
                    scaled = AssetScaler.scale_pil_image(
                        src_rgba,
                        int(card_w),
                        int(card_h),
                        element_type="cards",
                        is_haunted_card=True,
                    )
                    if scaled is not None:
                        pil_out = scaled.crop((x0, y0, x1, y1))
                except Exception:
                    pil_out = None
        elif kind == "bleeding_heart":
            try:
                heart_1x = _build_bleeding_heart_pil()
                # Integer scaling prevents fractional NEAREST mixels on 1080p 1.5x cards
                int_scale = 2 if self._get_card_scale() >= 1.8 else 1
                heart_scaled = _nearest_scale(heart_1x, int_scale)
                tw = min(crop_w, heart_scaled.width)
                th = min(crop_h, heart_scaled.height)
                if (tw, th) != heart_scaled.size:
                    heart_scaled = heart_scaled.crop((0, 0, tw, th))
                canvas_img = Image.new("RGBA", (crop_w, crop_h), (0, 0, 0, 0))
                canvas_img.paste(
                    heart_scaled,
                    ((crop_w - tw) // 2, (crop_h - th) // 2),
                    heart_scaled,
                )
                pil_out = canvas_img
            except Exception:
                pil_out = None

        if pil_out is None:
            return None
        try:
            photo = ImageTk.PhotoImage(pil_out, master=self.root)
            self._card_overlay_cache[key] = photo
            return photo
        except Exception:
            return None

    # ------------------------------------------------------------------------
    # Phase, Soul Meter, Decals & Heartbeat Scheduling
    # ------------------------------------------------------------------------

    def sync_phase_and_soul(self, phase: Phase, soul_meter: float) -> None:
        """Synchronizes decals, heartbeat pacing, and coarse ambient polling with Haunted state."""
        self._phase = phase
        self._soul_meter = float(soul_meter)

        if phase in (Phase.NORMAL, Phase.VICTORY, Phase.DEFEAT):
            self._corruption_tier = 0
            self._cancel_timer("ambient_poll")
            self._cancel_timer("heartbeat")
            self._cancel_timer("hesitation")
            self._cancel_timer("configure_debounce")
            self._clear_transient_effects()
            self._delete_felt_tags(("haunted_decal",))
            self._active_decal_photos.clear()
            return

        # 1. Update static HELL_TABLE perimeter decals
        new_tier = compute_corruption_tier(phase, self._soul_meter)
        tier_changed = new_tier != self._corruption_tier
        self._corruption_tier = new_tier
        if new_tier == 0:
            self._delete_felt_tags(("haunted_decal",))
            self._active_decal_photos.clear()
        elif tier_changed or not self._has_felt_decals():
            self._render_decals()

        # 2. Heartbeat pacing (< 25% Soul in HELL_TABLE)
        hb_ms = compute_heartbeat_interval_ms(self._soul_meter) if phase == Phase.HELL_TABLE else None
        if hb_ms is None:
            self._cancel_timer("heartbeat")
        elif "heartbeat" not in self._timers:
            self._schedule("heartbeat", hb_ms, self._heartbeat_tick)

        # 3. Start coarse 2.5s ambient poll if not already active
        if "ambient_poll" not in self._timers:
            self._schedule("ambient_poll", AMBIENT_POLL_MS, self._ambient_poll_tick)

    def _has_felt_decals(self) -> bool:
        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is None:
            return False
        try:
            return bool(canvas.find_withtag("haunted_decal"))
        except Exception:
            return False

    def _render_decals(self) -> None:
        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is None:
            return
        self._delete_felt_tags(("haunted_decal",))
        self._active_decal_photos.clear()

        if self._corruption_tier <= 0:
            return

        bounds_fn = getattr(self.app, "get_unobstructed_felt_bounds", None)
        if callable(bounds_fn):
            left, top, right, bottom = bounds_fn()
        else:
            w = max(200, getattr(canvas, "canvas_width", 1280))
            h = max(200, getattr(canvas, "canvas_height", 500))
            left, top, right, bottom = (40, 20, w - 40, h - 20)

        span_w = max(120, right - left)
        span_h = max(120, bottom - top)
        art_scale = self._get_art_scale()

        for rx, ry, kind, min_tier in DECAL_ANCHORS:
            if min_tier > self._corruption_tier:
                continue
            photo = self._get_scaled_sprite(kind, art_scale)
            if photo is None:
                continue
            px = int(round(left + rx * span_w))
            py = int(round(top + ry * span_h))
            # Clamp slightly inward so sprites stay within unobstructed felt bounds
            pad_x = max(12, photo.width() // 2)
            pad_y = max(12, photo.height() // 2)
            px = max(left + pad_x, min(right - pad_x, px))
            py = max(top + pad_y, min(bottom - pad_y, py))
            try:
                canvas.create_image(
                    px,
                    py,
                    image=photo,
                    anchor="center",
                    state="disabled",
                    tags="haunted_decal",
                )
                self._active_decal_photos.append(photo)
            except Exception:
                pass

        self._raise_above_felt_bg(canvas, "haunted_decal")

    def _heartbeat_tick(self) -> None:
        self._timers.pop("heartbeat", None)
        if self._phase != Phase.HELL_TABLE:
            return
        hb_ms = compute_heartbeat_interval_ms(self._soul_meter)
        if hb_ms is None:
            return
        # Keep timer scheduled across mute/modals; skip audio emission when blocked
        has_modal = getattr(self.app, "_has_open_modal_dialog", None)
        modal_open = callable(has_modal) and has_modal()
        if (
            not self._in_blackout
            and not modal_open
            and getattr(self.app, "table_seats", 1) == 1
            and not getattr(self.app, "tour_active", False)
            and not getattr(self.app, "bootcamp_active", False)
            and self.sound_manager is not None
            and not getattr(self.sound_manager, "is_muted", False)
        ):
            try:
                self.sound_manager.play_haunted_sound("heartbeat")
            except Exception:
                pass
        self._schedule("heartbeat", hb_ms, self._heartbeat_tick)

    # ------------------------------------------------------------------------
    # Coarse Ambient Poll Scheduler
    # ------------------------------------------------------------------------

    def _ambient_poll_tick(self) -> None:
        self._timers.pop("ambient_poll", None)
        if self._phase not in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING, Phase.HELL_TABLE):
            return

        if self._can_run_effect():
            prob = PHASE_POLL_PROBABILITY.get(self._phase, 0.25)
            if random.random() < prob:
                self._dispatch_random_ambient_effect()

        self._schedule("ambient_poll", AMBIENT_POLL_MS, self._ambient_poll_tick)

    def _dispatch_random_ambient_effect(self) -> bool:
        now = time.monotonic()
        candidates: list[Callable[[], bool]] = []

        # 1. Transient visual glitches (share 6-8s global cooldown + Reduced Flashes gate)
        glitch_ready = (
            self.scares_mode == "full"
            and not self._active_transient_glitch
            and (now - self._last_glitch_ts) >= self._next_glitch_cooldown_s
        )
        if glitch_ready:
            if self._phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
                candidates.append(self.trigger_dealer_flash)
                candidates.append(self.trigger_felt_text_flicker)
            if self._phase in (Phase.OMEN, Phase.SNUFFING, Phase.HELL_TABLE):
                candidates.append(self._trigger_random_card_glitch)

        # 2. Crawlers (independent cooldowns + Crawling Bugs gate)
        if self.show_bugs:
            if (
                "spider_anim" not in self._timers
                and (now - self._last_spider_ts) >= self._next_spider_cooldown_s
            ):
                candidates.append(self.trigger_stage_spider)
            if (
                self._phase in (Phase.SNUFFING, Phase.HELL_TABLE)
                and "millipede_anim" not in self._timers
                and (now - self._last_millipede_ts) >= self._next_millipede_cooldown_s
            ):
                candidates.append(self.trigger_perimeter_millipede)

        if not candidates:
            return False

        random.shuffle(candidates)
        for fn in candidates:
            if fn():
                return True
        return False

    def _trigger_random_card_glitch(self) -> bool:
        get_cards = getattr(self.app, "get_visible_card_sprites", None)
        if not callable(get_cards):
            return False
        visible = get_cards()
        if not visible:
            return False
        # Prioritize topmost/unoccluded cards (last card of each player hand + dealer upcard)
        top_ids: set[int] = set()
        for h_obj in getattr(self.app, "player_hands", []):
            sids = getattr(h_obj, "sprite_ids", None)
            if sids:
                top_ids.add(sids[-1])
        d_sids = getattr(getattr(self.app, "dealer_hand", None), "sprite_ids", None)
        if d_sids:
            top_ids.add(d_sids[-1])
        topmost = [pair for pair in visible if pair[0] in top_ids]
        under = [pair for pair in visible if pair[0] not in top_ids]
        random.shuffle(topmost)
        random.shuffle(under)
        for item_id, card_obj in topmost + under:
            if self.trigger_card_glitch(item_id, card_obj):
                return True
        return False

    def _arm_glitch_cooldown(self) -> None:
        self._last_glitch_ts = time.monotonic()
        self._next_glitch_cooldown_s = random.uniform(*GLOBAL_GLITCH_COOLDOWN_RANGE_S)

    # ------------------------------------------------------------------------
    # Individual Horror Micro-Effects
    # ------------------------------------------------------------------------

    def trigger_card_glitch(
        self,
        target_card_id: int,
        card_obj: Any,
        ignore_mapped: bool = False,
    ) -> bool:
        """
        Stamps a transient 220-300ms center-art overlay strictly above target_card_id
        and strictly below any overlapping card dealt on top.
        """
        if self.scares_mode != "full":
            return False
        if not self._can_run_effect(ignore_mapped=ignore_mapped):
            return False
        if self._active_transient_glitch:
            return False
        if (time.monotonic() - self._last_glitch_ts) < self._next_glitch_cooldown_s and self._last_glitch_ts > 0.0:
            return False

        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is None:
            return False
        if getattr(canvas, "has_active_card_animations", lambda: False)():
            return False

        rank = str(getattr(card_obj, "rank", "")).lower()
        suit = str(getattr(card_obj, "suit", "")).lower()

        # Precedence: J/Q/K court cards -> haunted face shift; non-court Hearts -> bleeding heart
        if rank in ("jack", "queen", "king"):
            kind = rank
            duration_ms = random.randint(220, 280)
        elif suit == "heart" and rank != "13":
            kind = "bleeding_heart"
            duration_ms = random.randint(250, 300)
        else:
            # Ineligible card returns False without arming global glitch cooldown
            return False

        try:
            coords = canvas.coords(target_card_id)
            if not coords or len(coords) < 2:
                return False
            card_x, card_y = int(coords[0]), int(coords[1])
        except Exception:
            return False

        card_w = int(getattr(self.app, "card_width", 74))
        card_h = int(getattr(self.app, "card_height", 107))
        photo = self._get_card_glitch_photo(kind, card_w, card_h)
        if photo is None:
            return False

        x0, y0, _, _ = compute_center_crop_box(card_w, card_h)
        try:
            canvas.delete("haunted_glitch_overlay")
            overlay_id = canvas.create_image(
                card_x + x0,
                card_y + y0,
                image=photo,
                anchor="nw",
                state="disabled",
                tags="haunted_glitch_overlay",
            )
            canvas.tag_raise(overlay_id, target_card_id)
            self._active_card_glitch_photo = photo
        except Exception:
            return False

        self._active_transient_glitch = True
        self._arm_glitch_cooldown()
        self._schedule("glitch_restore", duration_ms, self.clear_card_glitches)
        return True

    def clear_card_glitches(self) -> None:
        self._cancel_timer("glitch_restore")
        self._active_transient_glitch = False
        self._active_card_glitch_photo = None
        self._delete_felt_tags(("haunted_glitch_overlay",))

    def trigger_dealer_flash(self, ignore_mapped: bool = False) -> bool:
        """Stamps a 220ms dark Malphas silhouette + crimson eyes overlay over dealer_sprite."""
        if self.scares_mode != "full":
            return False
        if not self._can_run_effect(ignore_mapped=ignore_mapped):
            return False
        if self._active_transient_glitch:
            return False
        if (time.monotonic() - self._last_glitch_ts) < self._next_glitch_cooldown_s and self._last_glitch_ts > 0.0:
            return False

        stage = getattr(self.app, "dealer_stage_canvas", None)
        if stage is None:
            return False

        art_scale = self._get_art_scale()
        photo = self._get_scaled_sprite("malphas_flash", art_scale)
        if photo is None:
            return False

        w = max(10, getattr(stage, "canvas_width", 1000))
        h = max(10, getattr(stage, "canvas_height", 220))
        try:
            stage.delete("haunted_dealer_flash")
            stage.create_image(
                w // 2,
                h,
                image=photo,
                anchor="s",
                state="disabled",
                tags=("stage_overlay", "haunted_dealer_flash"),
            )
            self._active_dealer_flash_photo = photo
            sync_z = getattr(stage, "_sync_stage_zorder", None)
            if callable(sync_z):
                sync_z()
        except Exception:
            return False

        self._active_transient_glitch = True
        self._arm_glitch_cooldown()
        self._schedule("glitch_restore", 220, self._clear_dealer_flash)
        return True

    def _clear_dealer_flash(self) -> None:
        self._cancel_timer("glitch_restore")
        self._active_transient_glitch = False
        self._active_dealer_flash_photo = None
        self._delete_stage_tags(("haunted_dealer_flash",))

    def trigger_felt_text_flicker(self, ignore_mapped: bool = False) -> bool:
        """Stamps a 350ms un-engraved baize patch + desaturated eerie text over the middle rule band."""
        if self.scares_mode != "full":
            return False
        if not self._can_run_effect(ignore_mapped=ignore_mapped):
            return False
        if self._active_transient_glitch:
            return False
        if (time.monotonic() - self._last_glitch_ts) < self._next_glitch_cooldown_s and self._last_glitch_ts > 0.0:
            return False

        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is None:
            return False

        get_patch = getattr(canvas, "get_unmarked_rule_band_patch", None)
        if not callable(get_patch):
            return False
        patch_data = get_patch()
        if not patch_data:
            return False
        patch_photo, cx, cy = patch_data

        profile = getattr(self.app, "display_profile", None)
        px_size = int(profile.table_px(16)) if profile is not None and hasattr(profile, "table_px") else 16
        tk_font = ("Tiny5 SC", -px_size, "bold")
        s = self._get_art_scale()

        indices = [i for i in range(len(FELT_FLICKER_LINES)) if i != self._last_flicker_idx]
        idx = random.choice(indices) if indices else 0
        self._last_flicker_idx = idx
        line = FELT_FLICKER_LINES[idx]

        try:
            canvas.delete("haunted_felt_flicker")
            canvas.create_image(
                cx,
                cy,
                image=patch_photo,
                anchor="center",
                state="disabled",
                tags="haunted_felt_flicker",
            )
            canvas.create_text(
                cx + s,
                cy + s,
                text=line,
                fill="#14060a",
                font=tk_font,
                anchor="center",
                state="disabled",
                tags="haunted_felt_flicker",
            )
            canvas.create_text(
                cx,
                cy,
                text=line,
                fill="#c45650",
                font=tk_font,
                anchor="center",
                state="disabled",
                tags="haunted_felt_flicker",
            )
            self._active_felt_flicker_photo = patch_photo
            self._raise_above_felt_bg(canvas, "haunted_felt_flicker")
        except Exception:
            return False

        self._active_transient_glitch = True
        self._arm_glitch_cooldown()
        self._schedule("glitch_restore", 350, self._clear_felt_text_flicker)
        return True

    def _clear_felt_text_flicker(self) -> None:
        self._cancel_timer("glitch_restore")
        self._active_transient_glitch = False
        self._active_felt_flicker_photo = None
        self._delete_felt_tags(("haunted_felt_flicker",))

    # ------------------------------------------------------------------------
    # Crawlers: Reactive Stage Spider & Perimeter Millipede
    # ------------------------------------------------------------------------

    def trigger_stage_spider(self, ignore_mapped: bool = False) -> bool:
        """Lowers a crunchy 16x16/32x32 pixel spider on a 1px/2px silk thread in the clear upper-right alcove."""
        if not self.show_bugs:
            return False
        if not self._can_run_effect(ignore_mapped=ignore_mapped):
            return False
        if "spider_anim" in self._timers:
            return False

        stage = getattr(self.app, "dealer_stage_canvas", None)
        if stage is None:
            return False

        s = self._get_art_scale()
        w = max(320, getattr(stage, "canvas_width", 1000))
        min_x = w // 2 + 150 * s
        max_x = max(min_x + 10, w - 90 * s)
        self._spider_x = random.randint(min_x, max_x)
        self._spider_y = 0
        self._spider_target_y = random.randint(35 * s, 65 * s)
        self._spider_recoil_active = False
        self._last_spider_ts = time.monotonic()
        self._next_spider_cooldown_s = random.uniform(*SPIDER_COOLDOWN_RANGE_S)

        self._step_spider_anim(phase="descend", step=0, pause_ticks=0)
        return True

    def _step_spider_anim(self, phase: str, step: int, pause_ticks: int) -> None:
        self._timers.pop("spider_anim", None)
        stage = getattr(self.app, "dealer_stage_canvas", None)
        if stage is None or not self.show_bugs or self._in_blackout:
            self._delete_stage_tags(("haunted_spider",))
            return

        s = self._get_art_scale()
        if self._spider_recoil_active:
            phase = "recoil"

        if phase == "descend":
            self._spider_y += 3 * s
            if self._spider_y >= self._spider_target_y:
                self._spider_y = self._spider_target_y
                phase = "pause"
                pause_ticks = 14  # ~1.0s at 70ms/tick
        elif phase == "pause":
            pause_ticks -= 1
            if pause_ticks <= 0:
                phase = "recoil"
        elif phase == "recoil":
            self._spider_y -= 9 * s
            if self._spider_y <= 0:
                self._delete_stage_tags(("haunted_spider",))
                self._spider_recoil_active = False
                return

        photo = self._get_scaled_sprite("spider_0" if (step % 2 == 0) else "spider_1", s)
        if photo is None:
            self._delete_stage_tags(("haunted_spider",))
            return

        try:
            if (
                self._spider_line_id is not None
                and self._spider_img_id is not None
                and stage.find_withtag(self._spider_line_id)
                and stage.find_withtag(self._spider_img_id)
            ):
                stage.coords(self._spider_line_id, self._spider_x, 0, self._spider_x, self._spider_y)
                stage.coords(self._spider_img_id, self._spider_x, self._spider_y)
                stage.itemconfigure(self._spider_img_id, image=photo)
            else:
                stage.delete("haunted_spider")
                self._spider_line_id = stage.create_line(
                    self._spider_x,
                    0,
                    self._spider_x,
                    self._spider_y,
                    fill="#c8c4cc",
                    width=max(1, s),
                    state="disabled",
                    tags=("stage_overlay", "haunted_spider"),
                )
                self._spider_img_id = stage.create_image(
                    self._spider_x,
                    self._spider_y,
                    image=photo,
                    anchor="center",
                    state="disabled",
                    tags=("stage_overlay", "haunted_spider"),
                )
                sync_z = getattr(stage, "_sync_stage_zorder", None)
                if callable(sync_z):
                    sync_z()
        except Exception:
            return

        delay = 50 if phase == "recoil" else 70
        self._schedule(
            "spider_anim",
            delay,
            lambda: self._step_spider_anim(phase, step + 1, pause_ticks),
        )

    def notify_table_disruption(self) -> None:
        """Recoils any active stage spider upward immediately and clears stale card glitches."""
        if "spider_anim" in self._timers:
            self._spider_recoil_active = True
        self.clear_card_glitches()

    def trigger_perimeter_millipede(self, ignore_mapped: bool = False) -> bool:
        """Scuttles a 2-frame 24x12/48x24 millipede along the unobstructed bottom felt perimeter."""
        if not self.show_bugs:
            return False
        if not self._can_run_effect(ignore_mapped=ignore_mapped):
            return False
        if self._phase not in (Phase.SNUFFING, Phase.HELL_TABLE):
            return False
        if "millipede_anim" in self._timers:
            return False

        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is None or getattr(canvas, "has_active_card_animations", lambda: False)():
            return False

        bounds_fn = getattr(self.app, "get_unobstructed_felt_bounds", None)
        if callable(bounds_fn):
            left, top, right, bottom = bounds_fn()
        else:
            w = max(200, getattr(canvas, "canvas_width", 1280))
            h = max(200, getattr(canvas, "canvas_height", 500))
            left, top, right, bottom = (40, 20, w - 40, h - 20)

        span_w = max(120, right - left)
        span_h = max(120, bottom - top)
        start_x = int(round(left + 0.08 * span_w))
        end_x = int(round(left + 0.92 * span_w))
        y = int(round(top + 0.94 * span_h))

        self._last_millipede_ts = time.monotonic()
        self._next_millipede_cooldown_s = random.uniform(*MILLIPEDE_COOLDOWN_RANGE_S)
        self._step_millipede_anim(start_x, end_x, y, 0)
        return True

    def _step_millipede_anim(self, x: int, end_x: int, y: int, step: int) -> None:
        self._timers.pop("millipede_anim", None)
        canvas = getattr(self.app, "card_table_frame", None)
        if (
            canvas is None
            or not self.show_bugs
            or self._in_blackout
            or getattr(canvas, "has_active_card_animations", lambda: False)()
            or x >= end_x
        ):
            self._delete_felt_tags(("haunted_millipede",))
            return

        s = self._get_art_scale()
        photo = self._get_scaled_sprite("millipede_0" if (step % 2 == 0) else "millipede_1", s)
        if photo is None:
            self._delete_felt_tags(("haunted_millipede",))
            return

        try:
            if self._millipede_img_id is not None and canvas.find_withtag(self._millipede_img_id):
                canvas.coords(self._millipede_img_id, x, y)
                canvas.itemconfigure(self._millipede_img_id, image=photo)
            else:
                canvas.delete("haunted_millipede")
                self._millipede_img_id = canvas.create_image(
                    x,
                    y,
                    image=photo,
                    anchor="center",
                    state="disabled",
                    tags="haunted_millipede",
                )
                self._raise_above_felt_bg(canvas, "haunted_millipede")
        except Exception:
            return

        next_x = x + (3 * s)
        self._schedule(
            "millipede_anim",
            60,
            lambda: self._step_millipede_anim(next_x, end_x, y, step + 1),
        )

    # ------------------------------------------------------------------------
    # Hesitation Taunts (HELL_TABLE + PLAYER_TURN)
    # ------------------------------------------------------------------------

    def notify_player_turn_started(self) -> None:
        """Arms the 11s hesitation timer once per RoundPhase.PLAYER_TURN in HELL_TABLE."""
        self._hesitation_fired_this_turn = False
        self._cancel_timer("hesitation")
        if self._phase == Phase.HELL_TABLE and getattr(self.app, "table_seats", 1) == 1:
            self._schedule("hesitation", HESITATION_DELAY_MS, self._fire_hesitation_taunt)

    def notify_player_turn_ended(self) -> None:
        """Cancels the hesitation timer when leaving RoundPhase.PLAYER_TURN."""
        self._cancel_timer("hesitation")

    def notify_player_activity(self) -> None:
        """Resets the hesitation countdown on player actions while still in PLAYER_TURN."""
        self._cancel_timer("hesitation")
        if (
            self._phase == Phase.HELL_TABLE
            and not self._hesitation_fired_this_turn
            and getattr(self.app, "table_seats", 1) == 1
            and getattr(self.app, "round_phase", None) == RoundPhase.PLAYER_TURN
        ):
            self._schedule("hesitation", HESITATION_DELAY_MS, self._fire_hesitation_taunt)

    def _fire_hesitation_taunt(self) -> None:
        self._timers.pop("hesitation", None)
        if self._hesitation_fired_this_turn or self._phase != Phase.HELL_TABLE:
            return
        if getattr(self.app, "round_phase", None) != RoundPhase.PLAYER_TURN:
            return
        if not self._can_run_effect():
            return
        if getattr(self.app, "_typewriter_timer_id", None) is not None:
            return
        indices = [i for i in range(len(HESITATION_TAUNTS)) if i != self._last_taunt_idx]
        idx = random.choice(indices) if indices else 0
        self._last_taunt_idx = idx
        self._hesitation_fired_this_turn = True
        set_speech = getattr(self.app, "set_dealer_speech", None)
        if callable(set_speech):
            try:
                set_speech(HESITATION_TAUNTS[idx], stream=True)
            except Exception:
                pass

    # ------------------------------------------------------------------------
    # Pit Boss Power-Outage Blackout Reveal
    # ------------------------------------------------------------------------

    def play_pit_boss_blackout(
        self,
        on_swap_theme: Callable[[], None],
        on_complete: Callable[[], None],
        headless_bypass: bool = False,
    ) -> None:
        """
        Runs the skippable ~1.4s Pit Boss blackout transition.
        - When headless_bypass=True, executes on_swap_theme() and on_complete() synchronously.
        - Interactive mode mounts _BlackoutVeilOverlay(InWindowScreenHost) with idempotent
          theme_swapped guard so skipping before t=200ms still swaps themes cleanly.
        """
        if self._in_blackout:
            return

        # Cancel in-flight card animations before blackout
        canvas = getattr(self.app, "card_table_frame", None)
        if canvas is not None and hasattr(canvas, "cancel_animations"):
            try:
                canvas.cancel_animations()
            except Exception:
                pass

        if headless_bypass:
            on_swap_theme()
            on_complete()
            return

        self._in_blackout = True
        self._blackout_token += 1
        token = self._blackout_token
        state = {"theme_swapped": False, "finished": False}

        def _ensure_swap() -> None:
            if not state["theme_swapped"]:
                state["theme_swapped"] = True
                on_swap_theme()

        def _finish() -> None:
            if state["finished"] or token != self._blackout_token:
                return
            state["finished"] = True
            self._cancel_timer("blackout_step")
            _ensure_swap()
            self._close_blackout_overlay()
            self._in_blackout = False
            self._blackout_skip_cb = None
            on_complete()

        self._blackout_skip_cb = _finish
        self._clear_transient_effects()

        im = getattr(self.app, "input_manager", None)
        is_gp = bool(im is not None and getattr(im, "active_mode", "kb_mouse") == "gamepad")
        skip_hint = "[A] / [B] Skip" if is_gp else "Click / Space / Esc to Skip"
        profile = getattr(self.app, "display_profile", None)
        hint_px = int(profile.table_px(16)) if profile is not None and hasattr(profile, "table_px") else 16

        try:
            self._blackout_overlay = _BlackoutVeilOverlay(
                self.root,
                on_skip=_finish,
                skip_hint=skip_hint,
                hint_px=hint_px,
            )
        except Exception:
            self._in_blackout = False
            self._blackout_skip_cb = None
            on_swap_theme()
            on_complete()
            return

        # t = 0ms: single low-luminance 150ms dip under Full scares, or calm 450ms dark-crimson hold under Reduced Flashes
        if self.scares_mode == "full":
            if self._blackout_overlay is not None:
                self._blackout_overlay.set_veil_color("#181018")
            if self.sound_manager is not None:
                try:
                    self.sound_manager.play_haunted_sound("candle_snuff")
                except Exception:
                    pass
            self._schedule("blackout_step", 150, lambda: _step_lock_dark(token))
        else:
            if self._blackout_overlay is not None:
                self._blackout_overlay.set_veil_color("#16080c")
            if self.sound_manager is not None:
                try:
                    self.sound_manager.play_haunted_sound("candle_snuff")
                except Exception:
                    pass
            self._schedule("blackout_step", 180, lambda: _step_reduced_swap(token))

        def _step_reduced_swap(expected_token: int) -> None:
            if state["finished"] or expected_token != self._blackout_token:
                return
            if self.sound_manager is not None:
                try:
                    self.sound_manager.play_haunted_sound("hell_bell")
                    self.sound_manager.play_haunted_sound("demon_reveal")
                except Exception:
                    pass
            _ensure_swap()
            self._schedule("blackout_step", 270, _finish)

        def _step_lock_dark(expected_token: int) -> None:
            if state["finished"] or expected_token != self._blackout_token:
                return
            if self._blackout_overlay is not None:
                self._blackout_overlay.set_veil_color("#060408")
            self._schedule("blackout_step", 50, lambda: _step_swap_theme(expected_token))

        def _step_swap_theme(expected_token: int) -> None:
            if state["finished"] or expected_token != self._blackout_token:
                return
            if self.sound_manager is not None:
                try:
                    self.sound_manager.play_haunted_sound("stone_scrape")
                except Exception:
                    pass
            _ensure_swap()
            self._schedule("blackout_step", 650, lambda: _step_crimson_eyes(expected_token))

        def _step_crimson_eyes(expected_token: int) -> None:
            if state["finished"] or expected_token != self._blackout_token:
                return
            if self.sound_manager is not None:
                try:
                    self.sound_manager.play_haunted_sound("hell_bell")
                    self.sound_manager.play_haunted_sound("demon_reveal")
                except Exception:
                    pass
            eyes = self._get_scaled_sprite("blackout_eyes", self._get_blackout_eyes_scale())
            if self._blackout_overlay is not None:
                self._blackout_overlay.show_crimson_eyes(eyes)
            self._schedule("blackout_step", 350, _finish)

    def _skip_blackout(self) -> None:
        cb = self._blackout_skip_cb
        if callable(cb):
            cb()

    def _close_blackout_overlay(self) -> None:
        overlay = self._blackout_overlay
        self._blackout_overlay = None
        if overlay is not None:
            try:
                if overlay.winfo_exists():
                    overlay.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------------------
    # Display Profile, Resize & Full Teardown
    # ------------------------------------------------------------------------

    def _on_felt_configure(self, _event=None) -> None:
        # Strict 0-timer invariant in Phase.NORMAL/VICTORY/DEFEAT
        if self._corruption_tier <= 0:
            return
        self._schedule("configure_debounce", CONFIGURE_DEBOUNCE_MS, self._render_decals)

    def _clear_transient_effects(self) -> None:
        self._cancel_timer("glitch_restore")
        self._cancel_timer("spider_anim")
        self._cancel_timer("millipede_anim")
        self._active_transient_glitch = False
        self._spider_recoil_active = False
        self._spider_line_id = None
        self._spider_img_id = None
        self._millipede_img_id = None
        self._active_felt_flicker_photo = None
        self._active_card_glitch_photo = None
        self._active_dealer_flash_photo = None
        self._delete_felt_tags(TRANSIENT_FELT_TAGS)
        self._delete_stage_tags(TRANSIENT_STAGE_TAGS)

    def on_display_profile_changed(self, _profile: Any = None) -> None:
        """Clears transient animations, evicts stale scale caches, re-centers blackout eyes, and re-projects decals."""
        self._clear_transient_effects()
        cur_art = self._get_art_scale()
        cur_eyes = self._get_blackout_eyes_scale()
        for key in list(self._scale_sprite_cache.keys()):
            name, sc = key
            valid_sc = cur_eyes if name == "blackout_eyes" else cur_art
            if sc != valid_sc:
                self._scale_sprite_cache.pop(key, None)
        cur_cw = int(getattr(self.app, "card_width", 74))
        cur_ch = int(getattr(self.app, "card_height", 107))
        for key in list(self._card_overlay_cache.keys()):
            if (key[1], key[2]) != (cur_cw, cur_ch):
                self._card_overlay_cache.pop(key, None)

        if self._blackout_overlay is not None:
            eyes = self._get_scaled_sprite("blackout_eyes", cur_eyes)
            self._blackout_overlay.on_display_profile_changed(eyes)
        if self._corruption_tier > 0:
            self._render_decals()

    def cancel_all(self) -> None:
        """Cancels every tracked timer, closes blackout overlay, and deletes all haunted canvas items."""
        for key in list(self._timers.keys()):
            self._cancel_timer(key)
        self._timers.clear()
        self._blackout_token += 1
        self._in_blackout = False
        self._blackout_skip_cb = None
        self._close_blackout_overlay()
        self._clear_transient_effects()
        self._corruption_tier = 0
        self._delete_felt_tags(("haunted_decal",))
        self._active_decal_photos.clear()
