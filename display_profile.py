"""
Discrete DisplayProfile Resolver, Cross-OS DPI/Font Bootstrap & Display Diagnostics.

Owns:
- Pre-Tk() OS DPI awareness registration (Windows Per-Monitor v2 -> System fallback)
  and custom pixel font registration (Windows GDI FR_PRIVATE / Linux libfontconfig).
- Active monitor & usable desktop work-area probing (protecting Steam Deck 1280x800
  fullscreen while gracefully stepping down desktop Windowed mode to 1280x720 when
  usable work-area height < 840px).
- Discrete DisplayProfile tier matching using min(width_tier, height_tier) so dual-monitor
  virtual desktops (e.g. 3840x1080) never misclassify as 4K.
- Inspectable DisplayDiagnostics for SettingsDialog and automated test suites.
"""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import os
from pathlib import Path
import sys
import tkinter
from typing import Literal, Optional

from config import (
    CARD_HEIGHT,
    CARD_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    FALLBACK_WINDOW_HEIGHT,
    FONTS_DIR,
    VALID_WINDOW_PROFILE_OVERRIDES,
)
from pixel_ui import register_os_pixel_fonts


@dataclass(frozen=True)
class DisplayProfile:
    """Immutable geometry and orthogonal asset-scaling tokens for an active viewport."""

    name: str
    window_w: int
    window_h: int
    art_scale: Literal[1, 2]
    card_scale: Literal[1.0, 1.5, 2.0]
    font_scale: Literal[1, 2]
    stage_w: int
    stage_h: int
    rail_h: int
    divider_h: int
    pit_max_width: int
    is_fullscreen: bool = False

    @property
    def window_wh(self) -> tuple[int, int]:
        return (self.window_w, self.window_h)

    @property
    def card_width(self) -> int:
        if self.card_scale == 1.5:
            return 111
        return int(round(CARD_WIDTH * self.card_scale))

    @property
    def card_height(self) -> int:
        if self.card_scale == 1.5:
            return 160
        return int(round(CARD_HEIGHT * self.card_scale))

    @property
    def stage_wing_width(self) -> int:
        effective_w = min(self.window_w, self.pit_max_width)
        return max(0, (effective_w - self.stage_w) // 2)

    @property
    def felt_height(self) -> int:
        return max(360, self.window_h - self.stage_h - self.divider_h - self.rail_h)

    @property
    def multi_seat_dx(self) -> int:
        if self.art_scale >= 2:
            return 480
        if self.card_scale >= 1.5 or self.window_w >= 1600:
            return 345
        return 240


@dataclass(frozen=True)
class DisplayEnvironmentProbe:
    """Snapshot of active monitor geometry, usable desktop work-area, and SteamOS flags."""

    monitor_wh: tuple[int, int]
    usable_workarea_wh: tuple[int, int]
    is_steam_deck: bool = False
    is_gamescope: bool = False


@dataclass(frozen=True)
class DisplayDiagnostics:
    """Inspectable diagnostic record replacing silent OS/font exception swallowing."""

    os_platform: str
    dpi_awareness_mode: str
    font_registration_mode: str
    missing_font_families: tuple[str, ...]
    monitor_wh: tuple[int, int]
    usable_workarea_wh: tuple[int, int]
    is_steam_deck: bool
    is_gamescope: bool
    active_profile_name: str

    def format_summary(self, profile: Optional[DisplayProfile] = None) -> str:
        prof_name = profile.name if profile is not None else self.active_profile_name
        dims = (
            f"{profile.window_w}x{profile.window_h}"
            if profile is not None
            else f"{self.monitor_wh[0]}x{self.monitor_wh[1]}"
        )
        font_status = "OK" if not self.missing_font_families else f"Fallback ({len(self.missing_font_families)})"
        mode_tag = "Fullscreen" if (profile and profile.is_fullscreen) else "Windowed"
        return f"Display: {prof_name} ({dims} {mode_tag}) · Fonts: {font_status}"


_OS_BOOTSTRAP_RESULT: Optional[dict[str, str]] = None


def bootstrap_os_display_and_fonts(fonts_dir: Path = FONTS_DIR) -> dict[str, str]:
    """
    Idempotent pre-Tk() bootstrap for High-DPI awareness and OS-level font registration.
    Must be invoked before tkinter.Tk() in play_game() for crisp native pixels on Windows
    and Xft custom font discovery on Linux / SteamOS.
    """
    global _OS_BOOTSTRAP_RESULT
    if _OS_BOOTSTRAP_RESULT is not None:
        return dict(_OS_BOOTSTRAP_RESULT)

    dpi_mode = "not_applicable"
    if sys.platform.startswith("win"):
        dpi_mode = "unavailable"
        try:
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = (DPI_AWARENESS_CONTEXT)-4
            res = ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
            if res:
                dpi_mode = "per_monitor_v2"
        except Exception:
            pass
        if dpi_mode == "unavailable":
            try:
                # PROCESS_PER_MONITOR_DPI_AWARE = 2
                hr = ctypes.windll.shcore.SetProcessDpiAwareness(2)
                if hr in (0, -2147024891):  # S_OK or E_ACCESSDENIED (already set)
                    dpi_mode = "per_monitor_v1"
            except Exception:
                pass
        if dpi_mode == "unavailable":
            try:
                if ctypes.windll.user32.SetProcessDPIAware():
                    dpi_mode = "system_dpi_aware"
            except Exception:
                pass

    font_mode = register_os_pixel_fonts(fonts_dir)
    _OS_BOOTSTRAP_RESULT = {
        "dpi_awareness_mode": dpi_mode,
        "os_font_mode": font_mode,
    }
    return dict(_OS_BOOTSTRAP_RESULT)


def lock_tk_pixel_scaling(root: tkinter.Tk) -> str:
    """
    Locks Tk's internal point-to-pixel scaling factor to 96 DPI (96 / 72 = 1.3333333333333333)
    so positive font point sizes map deterministically to pixel heights across OS DPI settings.
    """
    try:
        root.tk.call("tk", "scaling", 96.0 / 72.0)
        return "tk_scaling_locked_96dpi"
    except Exception:
        return "tk_scaling_default"


def _query_windows_monitor_and_workarea(root: tkinter.Tk) -> Optional[tuple[tuple[int, int], tuple[int, int]]]:
    """Queries Win32 active monitor pixel dimensions and usable taskbar-free work-area."""
    if not sys.platform.startswith("win"):
        return None

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", RECT),
            ("rcWork", RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    try:
        hwnd = root.winfo_id()
        MONITOR_DEFAULTTONEAREST = 2
        hmon = ctypes.windll.user32.MonitorFromWindow(ctypes.c_void_p(hwnd), MONITOR_DEFAULTTONEAREST)
        if hmon:
            mi = MONITORINFO()
            mi.cbSize = ctypes.sizeof(MONITORINFO)
            if ctypes.windll.user32.GetMonitorInfoW(ctypes.c_void_p(hmon), ctypes.byref(mi)):
                mon_w = int(mi.rcMonitor.right - mi.rcMonitor.left)
                mon_h = int(mi.rcMonitor.bottom - mi.rcMonitor.top)
                work_w = int(mi.rcWork.right - mi.rcWork.left)
                work_h = int(mi.rcWork.bottom - mi.rcWork.top)
                if mon_w >= 640 and mon_h >= 480 and work_w >= 640 and work_h >= 400:
                    return ((mon_w, mon_h), (work_w, work_h))
    except Exception:
        pass

    try:
        SPI_GETWORKAREA = 0x0030
        rect = RECT()
        if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
            work_w = int(rect.right - rect.left)
            work_h = int(rect.bottom - rect.top)
            scr_w = int(root.winfo_screenwidth())
            scr_h = int(root.winfo_screenheight())
            if work_w >= 640 and work_h >= 400:
                return ((scr_w, scr_h), (work_w, work_h))
    except Exception:
        pass

    return None


def query_usable_workarea(root: tkinter.Tk) -> tuple[int, int]:
    """Returns usable desktop work-area (width, height) excluding OS taskbars/panels."""
    win_res = _query_windows_monitor_and_workarea(root)
    if win_res is not None:
        return win_res[1]

    scr_w = max(640, int(root.winfo_screenwidth()))
    scr_h = max(480, int(root.winfo_screenheight()))
    is_gamescope = bool(os.environ.get("GAMESCOPE_WAYLAND_DISPLAY")) or os.environ.get("SteamDeck") == "1"
    if is_gamescope:
        return (scr_w, scr_h)
    return (scr_w, max(480, scr_h - 64))


def probe_display_environment(root: tkinter.Tk) -> DisplayEnvironmentProbe:
    """Captures active monitor resolution, usable work-area, and Steam Deck / Gamescope flags."""
    is_steam_deck = os.environ.get("SteamDeck") == "1"
    is_gamescope = bool(os.environ.get("GAMESCOPE_WAYLAND_DISPLAY"))

    win_res = _query_windows_monitor_and_workarea(root)
    if win_res is not None:
        mon_wh, work_wh = win_res
    else:
        scr_w = max(640, int(root.winfo_screenwidth()))
        scr_h = max(480, int(root.winfo_screenheight()))
        # Guard against multi-monitor combined X11 virtual screen widths (e.g., 3840x1080):
        # if aspect ratio exceeds 24:9 while height <= 1200, cap per-monitor width estimate.
        if scr_h <= 1200 and scr_w > scr_h * 2.6:
            mon_w = int(round(scr_h * 16 / 9))
        else:
            mon_w = scr_w
        mon_wh = (mon_w, scr_h)
        work_wh = (mon_w, scr_h) if (is_steam_deck or is_gamescope) else (mon_w, max(480, scr_h - 64))

    return DisplayEnvironmentProbe(
        monitor_wh=mon_wh,
        usable_workarea_wh=work_wh,
        is_steam_deck=is_steam_deck,
        is_gamescope=is_gamescope,
    )


def make_profile_preset(
    name: str,
    *,
    window_w: Optional[int] = None,
    window_h: Optional[int] = None,
    window_wh: Optional[tuple[int, int]] = None,
    fullscreen: bool = False,
    is_fullscreen: Optional[bool] = None,
    strict_integer_cards: bool = False,
) -> DisplayProfile:
    """Constructs one of the 5 canonical DisplayProfile presets."""
    if window_wh is not None:
        if window_w is None:
            window_w = int(window_wh[0])
        if window_h is None:
            window_h = int(window_wh[1])
    fs_flag = bool(is_fullscreen) if is_fullscreen is not None else bool(fullscreen)
    if name == "hd_720p":
        return DisplayProfile(
            name="hd_720p",
            window_w=window_w or DEFAULT_WINDOW_WIDTH,
            window_h=window_h or FALLBACK_WINDOW_HEIGHT,
            art_scale=1,
            card_scale=1.0,
            font_scale=1,
            stage_w=1000,
            stage_h=220,
            rail_h=72,
            divider_h=4,
            pit_max_width=1280,
            is_fullscreen=fs_flag,
        )
    if name == "deck_800p":
        return DisplayProfile(
            name="deck_800p",
            window_w=window_w or DEFAULT_WINDOW_WIDTH,
            window_h=window_h or DEFAULT_WINDOW_HEIGHT,
            art_scale=1,
            card_scale=1.0,
            font_scale=1,
            stage_w=1000,
            stage_h=220,
            rail_h=72,
            divider_h=4,
            pit_max_width=1280,
            is_fullscreen=fs_flag,
        )
    if name == "fhd_1080p":
        return DisplayProfile(
            name="fhd_1080p",
            window_w=window_w or 1920,
            window_h=window_h or 1080,
            art_scale=1,
            card_scale=1.0 if strict_integer_cards else 1.5,
            font_scale=1,
            stage_w=1000,
            stage_h=220,
            rail_h=72,
            divider_h=4,
            pit_max_width=1920,
            is_fullscreen=fs_flag,
        )
    if name == "qhd_1440p":
        return DisplayProfile(
            name="qhd_1440p",
            window_w=window_w or 2560,
            window_h=window_h or 1440,
            art_scale=2,
            card_scale=2.0,
            font_scale=2,
            stage_w=2000,
            stage_h=440,
            rail_h=144,
            divider_h=8,
            pit_max_width=2560,
            is_fullscreen=fs_flag,
        )
    if name == "uhd_4k":
        return DisplayProfile(
            name="uhd_4k",
            window_w=window_w or 3840,
            window_h=window_h or 2160,
            art_scale=2,
            card_scale=2.0,
            font_scale=2,
            stage_w=2000,
            stage_h=440,
            rail_h=144,
            divider_h=8,
            pit_max_width=2560,
            is_fullscreen=fs_flag,
        )
    raise ValueError(f"Unknown DisplayProfile preset: {name!r}")


def _width_tier(w: int) -> int:
    if w >= 3840:
        return 4
    if w >= 2560:
        return 3
    if w >= 1600:
        return 2
    return 1


def _height_tier(h: int) -> int:
    if h >= 2000:
        return 4
    if h >= 1400:
        return 3
    if h >= 900:
        return 2
    if h >= 790:
        return 1
    return 0


def resolve_display_profile(
    probe: DisplayEnvironmentProbe,
    *,
    fullscreen: bool,
    strict_integer_cards: bool = False,
    window_profile_override: str = "auto",
) -> DisplayProfile:
    """
    Resolves the optimal discrete DisplayProfile for either Windowed or Fullscreen mode.
    - Fullscreen matches exact active monitor pixels via min(width_tier, height_tier)
      (preserving native 1280x800 on Steam Deck).
    - Windowed mode defaults to 1280x800 ('deck_800p') when usable work-area height >= 840px,
      stepping down automatically to 1280x720 ('hd_720p') on constrained laptops/taskbars,
      and clamping manual overrides so bordered windows never exceed usable desktop space.
    """
    mon_w, mon_h = probe.monitor_wh
    work_w, work_h = probe.usable_workarea_wh
    override = window_profile_override if window_profile_override in VALID_WINDOW_PROFILE_OVERRIDES else "auto"

    if fullscreen:
        w_tier = _width_tier(mon_w)
        h_tier = _height_tier(mon_h)
        if h_tier == 0:
            return make_profile_preset(
                "hd_720p",
                window_w=max(1280, mon_w),
                window_h=max(720, mon_h),
                fullscreen=True,
                strict_integer_cards=strict_integer_cards,
            )
        tier = min(w_tier, h_tier)
        if tier >= 4:
            return make_profile_preset(
                "uhd_4k",
                window_w=mon_w,
                window_h=mon_h,
                fullscreen=True,
                strict_integer_cards=strict_integer_cards,
            )
        if tier == 3:
            return make_profile_preset(
                "qhd_1440p",
                window_w=mon_w,
                window_h=mon_h,
                fullscreen=True,
                strict_integer_cards=strict_integer_cards,
            )
        if tier == 2:
            return make_profile_preset(
                "fhd_1080p",
                window_w=mon_w,
                window_h=mon_h,
                fullscreen=True,
                strict_integer_cards=strict_integer_cards,
            )
        return make_profile_preset(
            "deck_800p",
            window_w=max(1280, mon_w),
            window_h=max(800, mon_h),
            fullscreen=True,
            strict_integer_cards=strict_integer_cards,
        )

    # Windowed Mode (bordered OS window must leave >= ~40px titlebar/frame clearance inside work-area)
    can_fit_1440 = (work_w >= 2560) and (work_h >= 1480)
    can_fit_800 = work_h >= 840

    if override == "qhd_1440p" and can_fit_1440:
        return make_profile_preset("qhd_1440p", fullscreen=False, strict_integer_cards=strict_integer_cards)
    if override == "hd_720p":
        return make_profile_preset("hd_720p", fullscreen=False, strict_integer_cards=strict_integer_cards)
    if override == "deck_800p" and can_fit_800:
        return make_profile_preset("deck_800p", fullscreen=False, strict_integer_cards=strict_integer_cards)

    # Auto (or clamped override when requested window exceeds usable work-area)
    if can_fit_800:
        return make_profile_preset("deck_800p", fullscreen=False, strict_integer_cards=strict_integer_cards)
    return make_profile_preset("hd_720p", fullscreen=False, strict_integer_cards=strict_integer_cards)
