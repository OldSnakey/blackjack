"""
In-Window Full-Screen Menu Screens and Modal Overlays for Blackjack.

Provides:
- InWindowScreenHost: Full-viewport in-window Frame host (zero separate OS Toplevel popups on Steam Deck / Gamescope).
- InWindowConfirmModal: In-window destructive-action confirmation modal replacing tkinter.messagebox.askyesno.
- StoryDialogueDialog: Full-screen theatrical narrative cutscene view with speaker portraits.
- AngelicDraftDialog: Full-screen 3-column Balatro-style celestial blessing draft stage.
- MultiSeatInsuranceDialog: In-window widescreen multi-seat insurance prompt.
- SettingsDialog: Full-screen 2-column Casino Settings & House Rules control deck (zero-scroll on 800p/720p).
- ShortcutsDialog: Full-screen 2-column keyboard & mouse controls reference.
- WelcomeSplashDialog: Full-screen 3-column Play Mode showcase & onboarding screen.
- TripometerDialog: Full-screen Strategy Tripometer & 50-hand rolling audit dashboard.
"""

from __future__ import annotations

import tkinter
from typing import Any, Callable, List, Optional

import config
from audio_assets import KeyboardIconLoader
from config import ASSETS_EXTRA_DIR, PANEL_BACKGROUND_COLOR
from display_profile import get_window_mode_options, probe_display_environment
from haunted_manager import BLESSING_REGISTRY, Blessing
from rules import (
    ALLOWED_DECK_COUNTS,
    SETTINGS_MAX_BETS as ALLOWED_MAXIMUM_BETS,
    SETTINGS_MIN_BETS as ALLOWED_MINIMUM_BETS,
    HouseRules,
    RoundPhase,
    VENUE_PRESETS,
    VENUE_PRESET_LABELS,
    estimate_house_edge_pct,
)
from pixel_ui import (
    get_element_font,
    get_title_font,
    get_header_font,
    get_body_font,
    get_button_font,
    get_badge_font,
    get_display_font,
)
from ui_chip_renderer import draw_25d_grade_medallion

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


def _parse_geometry_wh(geom: str) -> Optional[tuple[int, int]]:
    try:
        size_part = str(geom or "").split("+")[0].split("-")[0]
        w_s, h_s = size_part.split("x")
        w, h = int(w_s), int(h_s)
        if w > 20 and h > 20:
            return (w, h)
    except Exception:
        pass
    return None


class InWindowScreenHost(tkinter.Frame):
    """
    Full-viewport in-window screen container mounted directly inside the root Tk window.
    Eliminates separate X11/Win32 Toplevel popup windows on SteamOS Gamescope and desktop
    while preserving Toplevel-like lifecycle methods (title, geometry, protocol, transient)
    for callers and automated tests.
    """

    def __init__(
        self,
        parent: Optional[tkinter.Misc],
        app: Any = None,
        profile: Any = None,
        background: str = PANEL_BACKGROUND_COLOR,
        base_pad: int = 18,
        overlay_wh: Optional[tuple[int, int]] = None,
        overlay_rely: float = 0.5,
        **kwargs: Any,
    ) -> None:
        host_root = parent.winfo_toplevel() if parent is not None else tkinter._default_root
        self._host_root: tkinter.Misc = host_root
        self._host_app: Any = (
            app
            if app is not None
            else (
                getattr(host_root, "_active_blackjack_app", None)
                or getattr(host_root, "_blackjack_app", None)
            )
        )
        self._explicit_profile: Any = profile
        self._screen_title: str = ""
        self._wm_delete_cb: Optional[Callable[[], Any]] = None
        self._explicit_size: Optional[tuple[int, int]] = None
        self._overlay_wh: Optional[tuple[int, int]] = overlay_wh
        self._overlay_rely: float = float(overlay_rely)
        self._has_grab: bool = False
        self._last_root_wh: Optional[tuple[int, int]] = None
        self._base_pad: int = base_pad
        self._root_cfg_bind_id: Optional[str] = None
        self._destroying: bool = False

        super().__init__(
            host_root,
            background=background,
            highlightthickness=kwargs.pop("highlightthickness", 0),
            borderwidth=kwargs.pop("borderwidth", 0),
            **kwargs,
        )
        self.pack_propagate(False)
        self.grid_propagate(False)

        stack: list[InWindowScreenHost] = getattr(host_root, "_active_inwindow_screens", None)
        if stack is None:
            stack = []
            setattr(host_root, "_active_inwindow_screens", stack)
        if self not in stack:
            stack.append(self)

        try:
            self._root_cfg_bind_id = host_root.bind("<Configure>", self._on_host_root_configure, add="+")
        except Exception:
            self._root_cfg_bind_id = None

        self.sync_host_geometry()
        self.lift()
        self._temporarily_hidden_plaques: list[tkinter.Widget] = []
        if self._overlay_wh is not None:
            app_ref = self._host_app
            if app_ref is not None:
                if hasattr(app_ref, "_complete_typewriter_speech") and getattr(app_ref, "_typewriter_timer_id", None):
                    try:
                        app_ref._complete_typewriter_speech()
                    except Exception:
                        pass
                felt_cv = getattr(app_ref, "card_table_frame", None)
                no_d_sprites = len(felt_cv.find_withtag("dealer_card")) == 0 if felt_cv is not None and hasattr(felt_cv, "find_withtag") else True
                no_p_sprites = len(felt_cv.find_withtag("player_card")) == 0 if felt_cv is not None and hasattr(felt_cv, "find_withtag") else True
                d_empty = no_d_sprites and len(getattr(app_ref, "dealer_hand", ())) == 0
                p_empty = no_p_sprites and len(getattr(app_ref, "player_hand", ())) == 0
                for p_attr, is_emp in (("dealer_header_frame", d_empty), ("player_header_frame", p_empty)):
                    plq = getattr(app_ref, p_attr, None)
                    if is_emp and plq is not None and bool(plq.place_info()):
                        try:
                            setattr(plq, "_hidden_by_overlay", True)
                            plq.place_forget()
                            self._temporarily_hidden_plaques.append(plq)
                        except Exception:
                            pass
            try:
                if self.winfo_ismapped():
                    tkinter.Widget.grab_set(self)
                    self._has_grab = True
            except Exception:
                pass

    def _resolve_profile(self) -> Any:
        if self._explicit_profile is not None:
            return self._explicit_profile
        if self._host_app is not None:
            return getattr(self._host_app, "display_profile", None)
        return None

    @property
    def art_scale(self) -> int:
        prof = self._resolve_profile()
        return max(1, int(getattr(prof, "art_scale", 1))) if prof is not None else 1

    @property
    def menu_scale(self) -> int:
        """
        Integer 1x or 2x pixel scale for full-screen menus:
        - 1280x720 (`hd_720p`) & 1280x800 (`deck_800p`): `1` (native 1x pixels)
        - 1920x1080 (`fhd_1080p`), 2560x1440 (`qhd_1440p`), & 3840x2160 (`uhd_4k`): `2`
          (true 2x crunchy integer portraits, keycap icons, bevels, and 2x pixel fonts!)
        """
        if self._overlay_wh is not None:
            return self.art_scale
        if self.art_scale >= 2:
            return 2
        vw, vh = self._resolve_host_wh()
        if vw >= 1800 and vh >= 1000:
            return 2
        return 1

    @property
    def is_compact_2x(self) -> bool:
        """True when running 2x crunchy integer menu assets/fonts inside a 1080p-class (< 1360px tall) viewport."""
        if self.menu_scale < 2:
            return False
        _, vh = self._resolve_host_wh()
        return vh < 1360

    def _resolve_host_wh(self) -> tuple[int, int]:
        if self._explicit_size is not None and self._overlay_wh is None:
            return self._explicit_size
        prof = self._resolve_profile()
        fallback_w, fallback_h = (
            getattr(prof, "window_wh", (config.DEFAULT_WINDOW_WIDTH, config.DEFAULT_WINDOW_HEIGHT))
            if prof is not None
            else (config.DEFAULT_WINDOW_WIDTH, config.DEFAULT_WINDOW_HEIGHT)
        )
        try:
            rw = int(self._host_root.winfo_width())
            rh = int(self._host_root.winfo_height())
            if rw > 80 and rh > 80:
                return (rw, rh)
            parsed = _parse_geometry_wh(self._host_root.wm_geometry())
            if parsed is not None:
                return parsed
        except Exception:
            pass
        return (int(fallback_w), int(fallback_h))

    def _has_fullscreen_menu_underneath(self) -> bool:
        stack = getattr(self._host_root, "_active_inwindow_screens", None) or []
        return any(
            scr is not self and getattr(scr, "_overlay_wh", None) is None and scr.winfo_exists()
            for scr in stack
        )

    def _clamp_overlay_y(self, oy: int, ov_h: int, vh: int) -> int:
        """Keeps gameplay overlays strictly below HorizonRail and above MahoganyRail."""
        if (
            self._overlay_wh is None
            or isinstance(self.master, InWindowScreenHost)
            or self._has_fullscreen_menu_underneath()
        ):
            return max(12, min(max(12, vh - ov_h - 12), oy))
        s = self.art_scale
        min_oy = 240 * s
        max_oy = max(min_oy, vh - 60 * s - ov_h)
        return max(min_oy, min(max_oy, oy))

    def _resolve_target_bounds(self) -> tuple[int, int, int, int]:
        vw, vh = self._resolve_host_wh()
        if self._explicit_size is not None:
            if self._overlay_wh is not None:
                ov_w = min(vw - 24, self._explicit_size[0])
                ov_h = min(vh - 24, self._explicit_size[1])
                ox = max(12, (vw - ov_w) // 2)
                oy = self._clamp_overlay_y(int((vh - ov_h) * self._overlay_rely), ov_h, vh)
                return (ox, oy, ov_w, ov_h)
            return (0, 0, self._explicit_size[0], self._explicit_size[1])
        if self._overlay_wh is not None:
            s = self.art_scale
            base_w, base_h = self._overlay_wh
            ov_w = max(280, min(vw - 48 * s, int(base_w * s)))
            ov_h = max(220, min(vh - 48 * s, int(base_h * s)))
            ox = max(12, (vw - ov_w) // 2)
            oy = self._clamp_overlay_y(int((vh - ov_h) * self._overlay_rely), ov_h, vh)
            return (ox, oy, ov_w, ov_h)
        return (0, 0, vw, vh)

    def fit_overlay_to_requested(self, pad_w: int = 8, pad_h: int = 8) -> None:
        """Expands a floating overlay up to requested child size while keeping it strictly inside the viewport."""
        if self._overlay_wh is None:
            return
        self.update_idletasks()
        vw, vh = self._resolve_host_wh()
        s = self.art_scale
        cur_w = max(int(self.cget("width") or 0), int(self.winfo_width()))
        cur_h = max(int(self.cget("height") or 0), int(self.winfo_height()))
        req_children_w = max((c.winfo_reqwidth() for c in self.winfo_children()), default=0) + pad_w
        req_children_h = max((c.winfo_reqheight() for c in self.winfo_children()), default=0) + pad_h
        max_felt_h = (
            vh - 48 * s
            if (isinstance(self.master, InWindowScreenHost) or self._has_fullscreen_menu_underneath())
            else vh - 300 * s
        )
        new_w = min(vw - 48 * s, max(cur_w, req_children_w))
        new_h = min(max(220, max_felt_h), max(cur_h, req_children_h))
        ox = max(12, (vw - new_w) // 2)
        oy = self._clamp_overlay_y(int((vh - new_h) * self._overlay_rely), new_h, vh)
        self._explicit_size = (new_w, new_h)
        self.configure(width=new_w, height=new_h)
        self.place_configure(x=ox, y=oy, width=new_w, height=new_h)

    def compute_outer_padx(self, viewport_w: Optional[int] = None) -> int:
        vw = int(viewport_w) if viewport_w is not None and viewport_w > 80 else self._resolve_host_wh()[0]
        prof = self._resolve_profile()
        art_s = self.art_scale
        pit_max = int(getattr(prof, "pit_max_width", max(1920, vw))) if prof is not None else max(1920, vw)
        # Allow full-screen menus on 1280p/1080p/1440p to use the entire screen width,
        # clamping horizontal spread only on >pit_max ultrawide / 4K displays.
        eff_max = max(1280 * art_s, pit_max)
        return max(int(self._base_pad * art_s), (vw - eff_max) // 2)

    def sync_host_geometry(self) -> tuple[int, int]:
        ox, oy, w, h = self._resolve_target_bounds()
        self._last_root_wh = self._resolve_host_wh()
        self.configure(width=w, height=h)
        self.place(x=ox, y=oy, width=w, height=h)
        self._on_viewport_resized(w, h)
        return (w, h)

    def _on_host_root_configure(self, event: Any) -> None:
        if self._destroying or not self.winfo_exists():
            return
        if getattr(event, "widget", None) is not self._host_root:
            return
        if self._explicit_size is not None and self._overlay_wh is None:
            return
        ew = int(getattr(event, "width", 0) or 0)
        eh = int(getattr(event, "height", 0) or 0)
        if ew > 80 and eh > 80 and (ew, eh) != self._last_root_wh:
            if self._overlay_wh is not None:
                self._explicit_size = None
            self.sync_host_geometry()

    def _on_viewport_resized(self, width: int, height: int) -> None:
        """Hook for subclasses to adjust responsive padding or canvas widths."""
        pass

    def on_display_profile_changed(self, new_profile: Any) -> None:
        """Invoked by BlackjackApp.apply_display_profile when resolution/fullscreen changes while open."""
        self._explicit_profile = None
        self.sync_host_geometry()
        self.lift()

    def handle_escape(self) -> bool:
        """Invoked by BlackjackApp._on_escape_key when this screen is top-most. Returns True if handled."""
        confirm_cancel = getattr(self, "_active_confirm_cancel", None)
        if callable(confirm_cancel):
            confirm_cancel()
            return True
        if self._wm_delete_cb is not None:
            self._wm_delete_cb()
            return True
        return True

    def handle_modal_key(self, event: Any) -> Optional[str]:
        """Optional hook for routing root-captured keys to the active in-window screen."""
        return "break"

    # ------------------------------------------------------------------
    # Toplevel Compatibility Shims
    # ------------------------------------------------------------------
    def title(self, value: Optional[str] = None) -> str:
        if value is not None:
            self._screen_title = str(value)
        return self._screen_title

    def geometry(self, spec: Optional[str] = None) -> str:
        if spec is not None:
            parsed = _parse_geometry_wh(spec)
            if parsed is not None:
                self._explicit_size = parsed
                ox, oy, gw, gh = self._resolve_target_bounds()
                self.configure(width=gw, height=gh)
                self.place_configure(x=ox, y=oy, width=gw, height=gh)
                self._on_viewport_resized(gw, gh)
            return spec
        w = int(self.winfo_width())
        h = int(self.winfo_height())
        if w <= 1 or h <= 1:
            _, _, w, h = self._resolve_target_bounds()
        p_info = self.place_info()
        px = int(float(p_info.get("x", 0) or 0))
        py = int(float(p_info.get("y", 0) or 0))
        return f"{w}x{h}+{px}+{py}"

    def transient(self, *args: Any, **kwargs: Any) -> None:
        return None

    def resizable(self, *args: Any, **kwargs: Any) -> tuple[bool, bool]:
        return (False, False)

    def iconphoto(self, *args: Any, **kwargs: Any) -> None:
        return None

    def protocol(self, name: Optional[str] = None, func: Optional[Callable[[], Any]] = None) -> Any:
        if name == "WM_DELETE_WINDOW" and func is not None:
            self._wm_delete_cb = func
        return None

    def grab_set(self) -> None:
        return None

    def grab_release(self) -> None:
        return None

    def event_generate(self, sequence: str, **kw: Any) -> None:
        # In Tcl/Tk (tkEvent.c), `event generate $w <KeyPress-...>` silently drops key
        # events when the root window is withdrawn (`root.withdraw()`) and OS focus is empty.
        if (
            isinstance(sequence, str)
            and not self.winfo_ismapped()
            and self.focus_displayof() is None
        ):
            seq = sequence.strip()
            key_token = seq[1:-1] if (seq.startswith("<") and seq.endswith(">")) else seq
            for prefix in ("KeyPress-", "Key-"):
                if key_token.startswith(prefix):
                    key_token = key_token[len(prefix):]
            key_char_map = {
                "space": " ",
                "1": "1",
                "2": "2",
                "3": "3",
                "a": "a",
                "A": "A",
                "y": "y",
                "Y": "Y",
                "n": "n",
                "N": "N",
                "r": "r",
                "R": "R",
                "question": "?",
                "slash": "/",
            }
            if key_token in (
                "Escape",
                "Left",
                "Right",
                "Up",
                "Down",
                "Prior",
                "Next",
                "Tab",
                "Return",
                "KP_Enter",
                "space",
                "minus",
                "plus",
                "equal",
                "1",
                "2",
                "3",
                "a",
                "A",
                "y",
                "Y",
                "n",
                "N",
                "r",
                "R",
                "question",
                "slash",
                "F1",
            ):
                class _SynthKeyEvent:
                    def __init__(self, widget: Any, keysym: str, char: str) -> None:
                        self.widget = widget
                        self.keysym = keysym
                        self.char = char

                self.handle_modal_key(
                    _SynthKeyEvent(self, key_token, key_char_map.get(key_token, ""))
                )
                return
        super().event_generate(sequence, **kw)

    def destroy(self) -> None:
        if self._destroying:
            return
        self._destroying = True
        if self._has_grab:
            try:
                tkinter.Widget.grab_release(self)
            except Exception:
                pass
            self._has_grab = False
        if self._root_cfg_bind_id is not None:
            try:
                self._host_root.unbind("<Configure>", self._root_cfg_bind_id)
            except Exception:
                pass
            self._root_cfg_bind_id = None

        stack: list[InWindowScreenHost] = getattr(self._host_root, "_active_inwindow_screens", [])
        if self in stack:
            stack.remove(self)

        if getattr(self, "_temporarily_hidden_plaques", None) and self._host_app is not None:
            still_overlay = any(getattr(scr, "_overlay_wh", None) is not None for scr in stack)
            if not still_overlay:
                for plq in self._temporarily_hidden_plaques:
                    try:
                        setattr(plq, "_hidden_by_overlay", False)
                    except Exception:
                        pass
                if hasattr(self._host_app, "_position_score_plaques"):
                    try:
                        self._host_app._position_score_plaques()
                    except Exception:
                        pass
            self._temporarily_hidden_plaques.clear()

        try:
            super().destroy()
        except Exception:
            pass

        # Restore focus cleanly to next active in-window screen or root
        try:
            while stack and not stack[-1].winfo_exists():
                stack.pop()
            if stack:
                stack[-1].lift()
                stack[-1].focus_set()
            elif self._host_root is not None and self._host_root.winfo_exists():
                self._host_root.focus_set()
        except Exception:
            pass


class InWindowConfirmModal(tkinter.Frame):
    """
    In-window destructive-action confirmation overlay replacing OS messagebox.askyesno
    so SteamOS Gamescope never spawns an external system dialog window.
    """

    @classmethod
    def ask_yes_no(
        cls,
        parent_screen: tkinter.Misc,
        title: str,
        message: str,
        confirm_label: str = "Yes, Reset",
        cancel_label: str = "Cancel (Esc)",
        art_scale: int = 1,
        allow_withdrawn: bool = True,
    ) -> bool:
        host_root = parent_screen.winfo_toplevel()
        if not allow_withdrawn:
            try:
                if host_root.state() == "withdrawn":
                    return False
            except Exception:
                return False

        s = max(1, int(art_scale))
        result_var = tkinter.BooleanVar(master=host_root, value=False)
        resolved = {"done": False, "focus": False}  # False = Cancel (safe default), True = Confirm

        outer_halo = tkinter.Frame(
            parent_screen,
            background="#070304",
            highlightbackground="#ef5350",
            highlightthickness=2 * s,
            padx=4 * s,
            pady=4 * s,
        )
        outer_halo.place(relx=0.5, rely=0.5, anchor="center")
        outer_halo.lift()

        card = cls(
            outer_halo,
            background="#190b0e",
            relief="ridge",
            borderwidth=2 * s,
            highlightbackground="#ffd54f",
            highlightthickness=1 * s,
            padx=26 * s,
            pady=20 * s,
        )
        card.pack(fill="both", expand=True)
        has_grab = False
        try:
            if outer_halo.winfo_ismapped():
                tkinter.Widget.grab_set(card)
                has_grab = True
        except Exception:
            pass

        tkinter.Label(
            card,
            text=title,
            font=("Tiny5 Duo", -24 * s, "bold"),
            fg="#ffd54f",
            background="#190b0e",
        ).pack(pady=(0, 10 * s))

        tkinter.Label(
            card,
            text=message,
            font=("Tiny5", -24 * s, "normal"),
            fg="#eceff1",
            background="#190b0e",
            justify="left",
            wraplength=520 * s,
        ).pack(pady=(0, 18 * s))

        btn_row = tkinter.Frame(card, background="#190b0e")
        btn_row.pack(fill="x")
        btn_row.columnconfigure(0, weight=1, uniform="confirm_btns")
        btn_row.columnconfigure(1, weight=1, uniform="confirm_btns")

        def _finish(choice: bool) -> str:
            if resolved["done"]:
                return "break"
            resolved["done"] = True
            setattr(parent_screen, "_active_confirm_cancel", None)
            setattr(parent_screen, "_active_confirm_key", None)
            if has_grab:
                try:
                    tkinter.Widget.grab_release(card)
                except Exception:
                    pass
            result_var.set(bool(choice))
            try:
                outer_halo.destroy()
            except Exception:
                pass
            return "break"

        no_wrap = tkinter.Frame(btn_row, background="#190b0e", highlightbackground="#ffd700", highlightthickness=2 * s)
        no_wrap.grid(row=0, column=0, sticky="ew", padx=(0, 8 * s))
        no_btn = tkinter.Button(
            no_wrap,
            text=cancel_label,
            font=("Tiny5", -24 * s, "bold"),
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            takefocus=False,
            cursor="hand2",
            padx=16 * s,
            pady=8 * s,
            command=lambda: _finish(False),
        )
        no_btn.pack(fill="both", expand=True)

        yes_wrap = tkinter.Frame(btn_row, background="#190b0e", highlightbackground="#190b0e", highlightthickness=2 * s)
        yes_wrap.grid(row=0, column=1, sticky="ew", padx=(8 * s, 0))
        yes_btn = tkinter.Button(
            yes_wrap,
            text=confirm_label,
            font=("Tiny5", -24 * s, "bold"),
            background="#b71c1c",
            fg="#ffffff",
            activebackground="#d32f2f",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            takefocus=False,
            cursor="hand2",
            padx=16 * s,
            pady=8 * s,
            command=lambda: _finish(True),
        )
        yes_btn.pack(fill="both", expand=True)

        def _set_focus_choice(val: bool) -> None:
            resolved["focus"] = bool(val)
            no_wrap.configure(highlightbackground="#190b0e" if val else "#ffd700")
            yes_wrap.configure(highlightbackground="#ffd700" if val else "#190b0e")

        def _handle_key(keysym_or_event: Any) -> str:
            ks = keysym_or_event if isinstance(keysym_or_event, str) else getattr(keysym_or_event, "keysym", "")
            if ks in ("Escape", "n", "N"):
                return _finish(False)
            if ks == "Left":
                _set_focus_choice(False)
                return "break"
            if ks == "Right":
                _set_focus_choice(True)
                return "break"
            if ks == "Tab":
                _set_focus_choice(not resolved["focus"])
                return "break"
            if ks in ("Return", "KP_Enter", "space"):
                return _finish(resolved["focus"])
            return "break"

        setattr(parent_screen, "_active_confirm_cancel", lambda: _finish(False))
        setattr(parent_screen, "_active_confirm_key", _handle_key)

        for w_btn in (outer_halo, card, no_btn, yes_btn):
            w_btn.bind("<Escape>", _handle_key)
            w_btn.bind("<Left>", _handle_key)
            w_btn.bind("<Right>", _handle_key)
            w_btn.bind("<Tab>", _handle_key)
            w_btn.bind("<Return>", _handle_key)
            w_btn.bind("<KP_Enter>", _handle_key)
            w_btn.bind("<space>", _handle_key)
        outer_halo.bind("<Destroy>", lambda e: result_var.set(result_var.get()) if not resolved["done"] else None)
        card.focus_set()

        try:
            parent_screen.wait_variable(result_var)
        except Exception:
            return False
        return bool(result_var.get())


def configure_modal_window(
    dlg: tkinter.Misc,
    parent: Optional[tkinter.Misc],
    profile: Any = None,
    target_w: int = 620,
    target_h: int = 620,
    min_safe_h: int = 380,
    max_cfg_mult: float = 1.0,
) -> tuple[int, int]:
    """
    Synchronizes an `InWindowScreenHost` to 100% of the active root viewport
    (with safe fallback for any legacy Toplevel caller).
    """
    if isinstance(dlg, InWindowScreenHost):
        if profile is not None:
            dlg._explicit_profile = profile
        return dlg.sync_host_geometry()

    try:
        w, h = int(target_w), int(target_h)
        dlg.geometry(f"{w}x{h}")  # type: ignore[attr-defined]
        return (w, h)
    except Exception:
        return (int(target_w), int(target_h))


# ============================================================================
# 0B. SettingsOptionPickerModal & Specialized Settings Pickers (Tier-2 Overlay)
# ============================================================================

class SettingsOptionPickerModal(InWindowScreenHost):
    """
    Reusable in-window floating overlay modal for explicit multi-option Settings
    pickers (Window Mode, Play Mode, Table Seats). Displays radio-style rows with
    descriptions, gold '✓ ACTIVE' badge, disabled reasons, and full mouse +
    keyboard/controller navigation ([↑/↓], [Enter], [1-N], [Esc]).
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Any,
        *,
        window_title: str,
        heading: str,
        subtitle: str,
        options: list[dict[str, Any]],
        active_key: str,
        on_select: Callable[[str], None],
        on_cancel: Optional[Callable[[], None]] = None,
        overlay_wh: tuple[int, int] = (680, 420),
        disabled_badge_text: str = "LOCKED",
    ) -> None:
        self.app = app
        self._heading = heading
        self._subtitle = subtitle
        self._disabled_badge_text = disabled_badge_text
        self._on_select_cb = on_select
        self._on_cancel_cb = on_cancel
        self._row_frames: dict[str, tkinter.Frame] = {}
        self.options: list[dict[str, Any]] = list(options)
        self._option_by_key: dict[str, dict[str, Any]] = {opt["key"]: opt for opt in self.options}

        super().__init__(
            parent,
            app=app,
            background="#0b1f14",
            overlay_wh=overlay_wh,
            overlay_rely=0.50,
            highlightbackground="#ffd700",
            highlightthickness=2,
        )
        self.title(window_title)

        self.active_key = str(active_key)
        if self.active_key not in self._option_by_key and self.options:
            self.active_key = str(self.options[0]["key"])

        self._focused_idx = next(
            (i for i, opt in enumerate(self.options) if opt["key"] == self.active_key),
            0,
        )

        self._build_ui()
        self.fit_overlay_to_requested(pad_w=16, pad_h=16)

    def _build_ui(self) -> None:
        s = self.menu_scale
        compact = self.is_compact_2x
        bg = "#0b1f14"

        title_font = ("Tiny5 Duo", -32 if compact else (-24 * s), "bold")
        sub_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        row_lbl_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        row_sub_font = ("Tiny5", -16 if compact else (-16 * s), "normal")
        badge_font = ("Tiny5", -16 if compact else (-16 * s), "bold")
        btn_font = ("Tiny5", -24 if compact else (-16 * s), "bold")

        body = tkinter.Frame(self, background=bg, padx=16 * s, pady=12 if compact else (12 * s))
        body.pack(fill="both", expand=True)

        tkinter.Label(
            body,
            text=self._heading,
            font=title_font,
            fg="#ffd700",
            background=bg,
        ).pack(anchor="w", pady=(0, 2 * s))

        tkinter.Label(
            body,
            text=self._subtitle,
            font=sub_font,
            fg="#80cbc4",
            background=bg,
        ).pack(anchor="w", pady=(0, 8 if compact else (10 * s)))

        list_frame = tkinter.Frame(body, background=bg)
        list_frame.pack(fill="both", expand=True)

        wrap_px = 460 * s if not compact else 640
        self._row_frames.clear()
        for idx, opt in enumerate(self.options):
            key = opt["key"]
            enabled = bool(opt.get("enabled", True))
            is_active = key == self.active_key

            row_bg = "#143d29" if is_active else ("#0f2d1e" if enabled else "#111c17")
            border_col = "#ffd700" if is_active else ("#2e7d32" if enabled else "#263238")

            row = tkinter.Frame(
                list_frame,
                background=row_bg,
                highlightbackground=border_col,
                highlightthickness=2 if is_active else 1,
                padx=10 * s,
                pady=6 if compact else (6 * s),
                cursor="hand2" if enabled else "arrow",
            )
            row.pack(fill="x", pady=3 if compact else (4 * s))
            row.columnconfigure(1, weight=1)
            self._row_frames[key] = row

            marker = "◉" if is_active else ("○" if enabled else "✕")
            marker_fg = "#ffd700" if is_active else ("#a5d6a7" if enabled else "#546e7a")
            num_lbl = tkinter.Label(
                row,
                text=f"[{idx + 1}] {marker}",
                font=row_lbl_font,
                fg=marker_fg,
                background=row_bg,
                width=6,
                anchor="w",
            )
            num_lbl.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 6 * s))

            title_lbl = tkinter.Label(
                row,
                text=opt["label"],
                font=row_lbl_font,
                fg="#ffd700" if is_active else ("#ffffff" if enabled else "#78909c"),
                background=row_bg,
                anchor="w",
            )
            title_lbl.grid(row=0, column=1, sticky="w")

            sub_text = opt["subtitle"] if enabled else (opt.get("disabled_reason") or "Unavailable")
            sub_fg = "#b2dfdb" if enabled else "#ef9a9a"
            sub_lbl = tkinter.Label(
                row,
                text=sub_text,
                font=row_sub_font,
                fg=sub_fg,
                background=row_bg,
                anchor="w",
                justify="left",
                wraplength=wrap_px,
            )
            sub_lbl.grid(row=1, column=1, sticky="w")

            if is_active:
                badge_text, badge_fg, badge_bg = "✓ ACTIVE", "#121016", "#ffd700"
            elif enabled:
                badge_text, badge_fg, badge_bg = "SELECT", "#e0f2f1", "#1b5e20"
            else:
                badge_text, badge_fg, badge_bg = self._disabled_badge_text, "#ffcdd2", "#372125"

            badge_lbl = tkinter.Label(
                row,
                text=badge_text,
                font=badge_font,
                fg=badge_fg,
                background=badge_bg,
                padx=8 * s,
                pady=2 * s,
            )
            badge_lbl.grid(row=0, column=2, rowspan=2, sticky="e", padx=(10 * s, 0))

            if enabled:
                for w in (row, num_lbl, title_lbl, sub_lbl, badge_lbl):
                    w.bind("<Button-1>", lambda _e, k=key: self.select_option(k))

        footer = tkinter.Frame(body, background=bg)
        footer.pack(fill="x", pady=(8 if compact else (10 * s), 0))

        n_opts = len(self.options)
        self._hint_lbl = tkinter.Label(
            footer,
            text=f"[↑/↓] Navigate  •  [Enter] Apply  •  [1-{n_opts}] Quick Pick  •  [Esc] Cancel",
            font=row_sub_font,
            fg="#80cbc4",
            background=bg,
        )
        self._hint_lbl.pack(side="left")

        self.cancel_btn = tkinter.Button(
            footer,
            text="✖ Cancel",
            font=btn_font,
            background="#37474f",
            fg="#ffffff",
            activebackground="#455a64",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=14 * s,
            pady=4 if compact else (5 * s),
            command=self._on_cancel,
        )
        self.cancel_btn.pack(side="right")
        self._refresh_focus_highlight()

    def _refresh_focus_highlight(self) -> None:
        for idx, opt in enumerate(self.options):
            key = opt["key"]
            row = self._row_frames.get(key)
            if row is None or not row.winfo_exists():
                continue
            enabled = bool(opt.get("enabled", True))
            is_active = key == self.active_key
            is_focused = idx == self._focused_idx
            if is_focused and enabled:
                row.configure(highlightbackground="#ffd700", highlightthickness=2)
            elif is_active:
                row.configure(highlightbackground="#ffd700", highlightthickness=2)
            else:
                row.configure(highlightbackground="#2e7d32" if enabled else "#263238", highlightthickness=1)

    def is_option_enabled(self, key: str) -> bool:
        opt = self._option_by_key.get(str(key))
        return bool(opt and opt.get("enabled", False))

    def select_option(self, key: str) -> bool:
        opt = self._option_by_key.get(str(key))
        if not opt or not opt.get("enabled", False):
            return False
        cb = self._on_select_cb
        self.destroy()
        if callable(cb):
            cb(str(key))
        return True

    def _on_cancel(self) -> None:
        cb = self._on_cancel_cb
        self.destroy()
        if callable(cb):
            cb()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape":
            self._on_cancel()
            return "break"
        if ks in ("Up", "Left"):
            for step in range(1, len(self.options) + 1):
                cand = (self._focused_idx - step) % len(self.options)
                if self.options[cand].get("enabled", True):
                    self._focused_idx = cand
                    break
            self._refresh_focus_highlight()
            return "break"
        if ks in ("Down", "Right", "Tab"):
            for step in range(1, len(self.options) + 1):
                cand = (self._focused_idx + step) % len(self.options)
                if self.options[cand].get("enabled", True):
                    self._focused_idx = cand
                    break
            self._refresh_focus_highlight()
            return "break"
        if ks in ("Return", "KP_Enter", "space"):
            opt = self.options[self._focused_idx]
            if opt.get("enabled", True):
                self.select_option(opt["key"])
            return "break"
        if ch.isdigit() and ch != "0":
            idx = int(ch) - 1
            if 0 <= idx < len(self.options) and self.options[idx].get("enabled", True):
                self.select_option(self.options[idx]["key"])
            return "break"
        return "break"


class WindowModePickerModal(SettingsOptionPickerModal):
    """
    In-window floating overlay modal for selecting Window Mode & Resolution
    (Auto, 1280x720, 1280x800, 1920x1080, 2560x1440, or Native Fullscreen).
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Any,
        on_select: Callable[[str], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        host_root = parent.winfo_toplevel() if parent is not None else tkinter._default_root
        probe = probe_display_environment(host_root)
        self._probe = probe
        options = get_window_mode_options(probe)
        is_fs = bool(getattr(app, "_is_fullscreen", False))
        save_data = getattr(getattr(app, "save_manager", None), "data", None)
        override = str(getattr(save_data, "window_profile_override", "auto") or "auto")
        active_key = "fullscreen" if is_fs else override
        mon_w, mon_h = probe.monitor_wh
        work_w, work_h = probe.usable_workarea_wh
        super().__init__(
            parent,
            app,
            window_title="Window Mode & Resolution",
            heading="🖥 WINDOW MODE & RESOLUTION",
            subtitle=f"Detected Monitor: {mon_w}x{mon_h}  •  Usable Work Area: {work_w}x{work_h}",
            options=options,
            active_key=active_key,
            on_select=on_select,
            on_cancel=on_cancel,
            overlay_wh=(680, 500),
            disabled_badge_text="TOO LARGE",
        )


class PlayModePickerModal(SettingsOptionPickerModal):
    """In-window floating overlay modal for selecting the active Blackjack Play Mode."""

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Any,
        on_select: Callable[[str], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        current_mode = str(getattr(app, "play_mode", "betting") or "betting").lower()
        tour_locked = bool(getattr(app, "tour_active", False))
        lock_msg = "Exit Casino Venue Tour before switching play mode."
        options = [
            {
                "key": "casual",
                "label": "Casual Play",
                "subtitle": "Pure Blackjack hands with no chips, wagering, or bankroll pressure.",
                "enabled": (not tour_locked) or (current_mode == "casual"),
                "disabled_reason": lock_msg,
            },
            {
                "key": "betting",
                "label": "Casino Betting",
                "subtitle": "Classic casino wagering with chips, bankroll tracking, side bets, and Haunted/Hell's Table.",
                "enabled": (not tour_locked) or (current_mode == "betting"),
                "disabled_reason": lock_msg,
            },
            {
                "key": "training",
                "label": "Card Counting Training",
                "subtitle": "3-seat advantage-play practice with the Hi-Lo Counting Slate, live quizzes, and Bootcamp.",
                "enabled": (not tour_locked) or (current_mode == "training"),
                "disabled_reason": lock_msg,
            },
        ]
        super().__init__(
            parent,
            app,
            window_title="Select Play Mode",
            heading="🎮 SELECT PLAY MODE",
            subtitle="Choose how you want to play at the Blackjack table.",
            options=options,
            active_key=current_mode,
            on_select=on_select,
            on_cancel=on_cancel,
            overlay_wh=(680, 360),
            disabled_badge_text="TOUR LOCKED",
        )


class TableSeatsPickerModal(SettingsOptionPickerModal):
    """In-window floating overlay modal for selecting 1-Seat vs 3-Seat wagering."""

    def __init__(
        self,
        parent: tkinter.Misc,
        app: Any,
        on_select: Callable[[str], None],
        on_cancel: Optional[Callable[[], None]] = None,
    ) -> None:
        current_seats = str(int(getattr(app, "table_seats", 1) or 1))
        tour_locked = bool(getattr(app, "tour_active", False))
        options = [
            {
                "key": "1",
                "label": "1 Seat  (Classic Solo)",
                "subtitle": "Standard single-hand table. Supports Haunted Mode, Hell's Table, and Venue Tour.",
                "enabled": True,
                "disabled_reason": "",
            },
            {
                "key": "3",
                "label": "3 Seats  (Multi-Seat Wagering)",
                "subtitle": "Play up to 3 independent betting spots per round. Haunted Mode is disabled in multi-seat play.",
                "enabled": not tour_locked,
                "disabled_reason": "Venue Tour uses 1-Seat high-stakes tables.",
            },
        ]
        super().__init__(
            parent,
            app,
            window_title="Select Table Seats",
            heading="🪑 SELECT TABLE SEATS",
            subtitle="Choose single-seat solo play or multi-seat table wagering.",
            options=options,
            active_key=current_seats,
            on_select=on_select,
            on_cancel=on_cancel,
            overlay_wh=(680, 300),
            disabled_badge_text="TOUR LOCKED",
        )


# ============================================================================
# 1. StoryDialogueDialog (Full-Screen Theatrical Cutscene)
# ============================================================================

class StoryDialogueDialog(InWindowScreenHost):
    """
    Full-viewport theatrical narrative cutscene screen featuring custom speaker portraits,
    dark gothic or celestial vignette framing, and responsive proceed controls.
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        title: str,
        speaker: str,
        portrait_img: tkinter.PhotoImage | None,
        text_content: str,
        button_text: str = "Proceed...",
        on_close: Optional[Callable[[], None]] = None,
        is_celestial: bool = False,
    ):
        bg_col = "#041421" if is_celestial else "#0d0204"
        border_col = "#00e5ff" if is_celestial else "#8b0000"
        header_col = "#80cbc4" if is_celestial else "#ff5252"
        btn_bg = "#00695c" if is_celestial else "#b71c1c"
        btn_active = "#00897b" if is_celestial else "#d32f2f"

        port_w = portrait_img.width() if portrait_img is not None else 0
        root_w = parent.winfo_toplevel()
        host_app = getattr(root_w, "_active_blackjack_app", None) or getattr(root_w, "_blackjack_app", None)
        prof_s = max(1, int(getattr(getattr(host_app, "display_profile", None), "art_scale", 1)))
        live_char = getattr(getattr(host_app, "dealer_actor", None), "current_character", "")
        speaker_on_stage = (not is_celestial and live_char in ("malphas", "demon") and port_w <= 140 * prof_s)
        show_portrait = bool(portrait_img is not None and not speaker_on_stage)
        eff_port_w = port_w if show_portrait else 0
        base_ov_wh = (1080, 410) if port_w > 140 * prof_s else ((740, 215) if not show_portrait else (760, 235))
        super().__init__(
            parent,
            background=bg_col,
            base_pad=18,
            overlay_wh=base_ov_wh,
            overlay_rely=0.57,
        )
        self.on_close_cb = on_close
        self.title(title)

        # Hide background stage speech balloon + tail while cutscene banner is active so speaker doesn't double-speak
        self._hidden_stage_speech = False
        if self._host_app is not None and hasattr(self._host_app, "dealer_stage_canvas"):
            try:
                sc = self._host_app.dealer_stage_canvas
                if sc.find_withtag("dialogue_win") and sc.itemcget("dialogue_win", "state") != "hidden":
                    sc.itemconfigure("dialogue_win", state="hidden")
                    if sc.find_withtag("speech_tail"):
                        sc.itemconfigure("speech_tail", state="hidden")
                    self._hidden_stage_speech = True
                elif sc.find_withtag("speech_tail"):
                    sc.itemconfigure("speech_tail", state="hidden")
            except Exception:
                pass

        s = self.art_scale
        font_mult = 2.0 if (s >= 2 or port_w > 140) else 1.0
        speaker_font = ("BoldPixels", -int(16 * font_mult), "normal")
        body_font = get_element_font("story_dialog_body", scale=font_mult)
        btn_font = get_element_font("story_dialog_button", scale=font_mult)

        _, _, ov_w, ov_h = self._resolve_target_bounds()

        frame = tkinter.Frame(
            self,
            background=bg_col,
            relief="ridge",
            borderwidth=2 * s,
            highlightbackground=border_col,
            highlightthickness=2 * s,
            padx=18 * s,
            pady=14 * s,
        )
        frame.pack(fill="both", expand=True)
        self._stage_card = frame

        self.portrait_img = portrait_img
        if show_portrait and portrait_img is not None:
            port_lbl = tkinter.Label(
                frame,
                image=portrait_img,
                background="#060c14" if is_celestial else "#160408",
                highlightbackground=border_col,
                highlightthickness=max(1, s),
                padx=4 * s,
                pady=4 * s,
            )
            port_lbl.image = portrait_img
            port_lbl.pack(side="left", padx=(4 * s, 14 * s), pady=4 * s)
            self.portrait_label = port_lbl

        self.content_box = tkinter.Frame(frame, background=bg_col)
        self.content_box.pack(side="left", fill="both", expand=True, padx=(8 * s, 10 * s), pady=4 * s)

        self.speaker_label = tkinter.Label(
            self.content_box,
            text=speaker,
            font=speaker_font,
            fg=header_col,
            background=bg_col,
            anchor="w",
            justify="left",
        )
        self.speaker_label.pack(side="top", anchor="w", fill="x")

        btn_disp = button_text if "[" in button_text else f"{button_text} [Enter]"
        self.action_button = tkinter.Button(
            self.content_box,
            text=btn_disp,
            font=btn_font,
            background=btn_bg,
            foreground="#ffffff",
            activebackground=btn_active,
            activeforeground="#ffffff",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            cursor="hand2",
            padx=22 * s,
            pady=8 * s,
            takefocus=False,
            command=self._dismiss,
        )
        self.action_button.pack(side="bottom", anchor="e", pady=(8 * s, 0))

        wrap_w = max(280, ov_w - (eff_port_w + (108 * s if show_portrait else 76 * s)))
        self.message_label = tkinter.Label(
            self.content_box,
            text=text_content,
            font=body_font,
            fg="#eceff1",
            background=bg_col,
            anchor="w",
            justify="left",
            wraplength=wrap_w,
        )
        self.message_label.pack(side="top", anchor="w", fill="both", expand=True, pady=(8 * s, 8 * s))

        def _on_content_configure(event: Any) -> None:
            if event.width > 120:
                new_wrap = max(240, event.width - 20 * s)
                if abs(int(self.message_label.cget("wraplength")) - new_wrap) > 6:
                    self.message_label.configure(wraplength=new_wrap)

        self.content_box.bind("<Configure>", _on_content_configure)
        self.fit_overlay_to_requested(pad_w=8 * s, pad_h=8 * s)

        self.dialog_width = int(self.cget("width") or ov_w)
        self.dialog_height = int(self.cget("height") or ov_h)
        self.bind("<Return>", lambda e: self._dismiss())
        self.bind("<space>", lambda e: self._dismiss())
        self.bind("<Escape>", lambda e: self._dismiss())
        self.protocol("WM_DELETE_WINDOW", self._dismiss)
        self.focus_set()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        if ks in ("Return", "KP_Enter", "space", "Escape"):
            self._dismiss()
        return "break"

    def destroy(self) -> None:
        if getattr(self, "_hidden_stage_speech", False) and self._host_app is not None:
            try:
                sc = self._host_app.dealer_stage_canvas
                sc.itemconfigure("dialogue_win", state="normal")
                speech_txt = getattr(getattr(self._host_app, "dealer_speech_var", None), "get", lambda: "")()
                if sc.find_withtag("speech_tail") and str(speech_txt).strip():
                    sc.itemconfigure("speech_tail", state="normal")
            except Exception:
                pass
            self._hidden_stage_speech = False
        super().destroy()

    def _dismiss(self) -> str:
        cb = self.on_close_cb
        try:
            self.destroy()
        except Exception:
            pass
        if cb:
            cb()
        return "break"


# ============================================================================
# 2. AngelicDraftDialog (Full-Screen 3-Column Relic Draft Stage)
# ============================================================================

class AngelicDraftDialog(InWindowScreenHost):
    """
    Centered floating Balatro-style Roguelike celestial blessing draft overlay.
    Keeps the live Hell's Table stage, Pit Fiend, and Soul Meter visible around the 3 relic cards,
    supporting D-pad/Arrow + Enter/Space controller selection as well as [1]–[3] and direct click.
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        choices: list[Blessing],
        relic_icons: dict,
        on_select: Callable[[Blessing], None],
    ):
        super().__init__(
            parent,
            background="#03101c",
            base_pad=18,
            overlay_wh=(744, 348),
            overlay_rely=0.57,
        )
        self.choices = list(choices)
        self.on_select = on_select
        self.focused_idx: int = 0
        self._card_records: list[dict[str, Any]] = []
        self._zoomed_icons: list[Any] = []
        self.title("✦ CELESTIAL BLESSINGS - DRAFT A SACRED RELIC ✦")

        s = self.art_scale
        _, _, ov_w, _ = self._resolve_target_bounds()

        self._body = tkinter.Frame(
            self,
            background="#03101c",
            relief="ridge",
            borderwidth=2 * s,
            highlightbackground="#00e5ff",
            highlightthickness=2 * s,
            padx=10 * s,
            pady=8 * s,
        )
        self._body.pack(fill="both", expand=True)

        tkinter.Label(
            self._body,
            text="✦ CHOOSE YOUR CELESTIAL BLESSING ✦",
            font=get_element_font("dialog_title", scale=float(s)),
            fg="#ffd700",
            background="#03101c",
        ).pack(pady=(1 * s, 1 * s))

        tkinter.Label(
            self._body,
            text="Use [◄ / ► + Enter], [1]–[3], or Click to draft one divine relic:",
            font=get_element_font("angelic_draft_subtitle", scale=float(s)),
            fg="#80cbc4",
            background="#03101c",
        ).pack(pady=(0, 6 * s))

        cards_frame = tkinter.Frame(self._body, background="#03101c")
        cards_frame.pack(fill="both", expand=True, pady=(0, 1 * s))
        cards_frame.rowconfigure(0, weight=1)

        col_count = max(1, len(self.choices))
        est_col_w = max(195, (ov_w - 28 * s - 10 * s * col_count) // col_count)

        for idx, blessing in enumerate(self.choices):
            cards_frame.columnconfigure(idx, weight=1, uniform="relic_draft_cols")
            details = BLESSING_REGISTRY[blessing]
            card_f = tkinter.Frame(
                cards_frame,
                background="#051f38",
                relief="ridge",
                borderwidth=2 * s,
                highlightbackground="#00e5ff",
                highlightthickness=3 * s,
                padx=8 * s,
                pady=6 * s,
                cursor="hand2",
            )
            card_f.grid(row=0, column=idx, sticky="nsew", padx=4 * s, pady=1 * s)

            key_lbl = tkinter.Label(
                card_f,
                text=f"[{idx + 1}]",
                font=get_header_font(18 * s),
                fg="#ffd54f",
                background="#051f38",
            )
            key_lbl.pack(anchor="e")

            sync_labels = [key_lbl]
            icon = relic_icons.get(blessing.value) or relic_icons.get(blessing)
            if icon:
                disp_icon = icon
                try:
                    if hasattr(icon, "zoom") and int(icon.width()) <= 40 * s:
                        disp_icon = icon.zoom(2, 2)
                        self._zoomed_icons.append(disp_icon)
                except Exception:
                    disp_icon = icon
                shrine_box = tkinter.Frame(
                    card_f,
                    background="#031221",
                    highlightbackground="#00acc1",
                    highlightthickness=max(1, s),
                    padx=5 * s,
                    pady=4 * s,
                    cursor="hand2",
                )
                shrine_box.pack(pady=(0, 5 * s))
                ilbl = tkinter.Label(shrine_box, image=disp_icon, background="#031221", cursor="hand2")
                ilbl.image = disp_icon
                ilbl.pack()
                shrine_box.bind("<Button-1>", lambda e, i=idx, b=blessing: (self._set_focused_card(i), self._pick(b)))
                ilbl.bind("<Button-1>", lambda e, i=idx, b=blessing: (self._set_focused_card(i), self._pick(b)))

            t_lbl = tkinter.Label(
                card_f,
                text=details.title,
                font=get_element_font("angelic_draft_title", scale=float(s)),
                fg="#ffd700",
                background="#051f38",
                cursor="hand2",
            )
            t_lbl.pack(pady=(0, 2 * s))
            sync_labels.append(t_lbl)

            tag_lbl = tkinter.Label(
                card_f,
                text=details.tagline,
                font=get_element_font("angelic_draft_tagline", scale=float(s)),
                fg="#80cbc4",
                background="#051f38",
                cursor="hand2",
            )
            tag_lbl.pack(pady=(0, 6 * s))
            sync_labels.append(tag_lbl)

            desc_lbl = tkinter.Label(
                card_f,
                text=details.description,
                font=get_element_font("angelic_draft_description", scale=float(s)),
                fg="#eceff1",
                background="#051f38",
                justify="center",
                wraplength=max(180, est_col_w - 30 * s),
                cursor="hand2",
            )
            desc_lbl.pack(fill="both", expand=True, pady=(0, 8 * s))
            sync_labels.append(desc_lbl)

            btn = tkinter.Button(
                card_f,
                text=f"Equip Relic [{idx + 1}]",
                font=get_element_font("angelic_draft_button", scale=float(s)),
                background="#00838f",
                foreground="#ffffff",
                activebackground="#00acc1",
                activeforeground="#ffffff",
                relief="raised",
                borderwidth=2,
                takefocus=False,
                cursor="hand2",
                padx=12 * s,
                pady=6 * s,
                command=lambda b=blessing: self._pick(b),
            )
            btn.pack(side="bottom", pady=2 * s, fill="x")

            for w_click in [card_f] + sync_labels:
                w_click.bind("<Button-1>", lambda e, i=idx, b=blessing: (self._set_focused_card(i), self._pick(b)))
                w_click.bind("<Enter>", lambda e, i=idx: self._set_focused_card(i))

            self._card_records.append(
                {"frame": card_f, "labels": sync_labels, "btn": btn, "blessing": blessing, "idx": idx}
            )

        self._set_focused_card(0)
        self.fit_overlay_to_requested(pad_w=8 * s, pad_h=8 * s)

        for idx, blessing in enumerate(self.choices):
            self.bind(str(idx + 1), lambda e, b=blessing: self._pick(b))
        self.bind("<Left>", lambda e: self._move_focus(-1))
        self.bind("<Right>", lambda e: self._move_focus(1))
        self.bind("<Tab>", lambda e: self._move_focus(1))
        self.bind("<Return>", lambda e: self._confirm_focused())
        self.bind("<space>", lambda e: self._confirm_focused())
        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Mandatory relic draft
        self.focus_set()

    def _set_focused_card(self, idx: int) -> None:
        if not self._card_records:
            return
        self.focused_idx = max(0, min(len(self._card_records) - 1, int(idx)))
        for i, rec in enumerate(self._card_records):
            is_foc = i == self.focused_idx
            bg_c = "#093158" if is_foc else "#051f38"
            bd_c = "#ffd700" if is_foc else "#00e5ff"
            rec["frame"].configure(background=bg_c, highlightbackground=bd_c)
            for lbl in rec["labels"]:
                lbl.configure(background=bg_c)
            rec["btn"].configure(
                text=f"► Equip Relic [{i + 1}] ◄" if is_foc else f"Equip Relic [{i + 1}]",
                background="#ffd700" if is_foc else "#00838f",
                foreground="#141008" if is_foc else "#ffffff",
            )

    def _move_focus(self, delta: int) -> str:
        if self._card_records:
            self._set_focused_card((self.focused_idx + delta) % len(self._card_records))
        return "break"

    def _confirm_focused(self) -> str:
        if 0 <= self.focused_idx < len(self.choices):
            return self._pick(self.choices[self.focused_idx])
        return "break"

    def handle_escape(self) -> bool:
        # Must draft a blessing to proceed
        return True

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Left":
            return self._move_focus(-1)
        if ks in ("Right", "Tab"):
            return self._move_focus(1)
        if ks in ("Return", "KP_Enter", "space"):
            return self._confirm_focused()
        if ch in ("1", "2", "3"):
            idx = int(ch) - 1
            if 0 <= idx < len(self.choices):
                self._pick(self.choices[idx])
        return "break"

    def _pick(self, blessing: Blessing) -> str:
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_select:
            self.on_select(blessing)
        return "break"


# ============================================================================
# 2.5 MultiSeatInsuranceDialog (In-Window Widescreen Insurance Prompt)
# ============================================================================

class MultiSeatInsuranceDialog(InWindowScreenHost):
    """
    In-window widescreen multi-seat insurance prompt presented when the dealer shows an Ace.
    Allows independent insurance decisions per active seat with 'Insure All' and 'Decline All' shortcuts.
    """

    def __init__(
        self,
        parent: tkinter.Tk | tkinter.Misc,
        seats: List[Any],
        bankroll: int,
        on_confirm: Callable[[dict[int, int]], None],
        on_decline: Callable[[], None],
    ):
        super().__init__(
            parent,
            background=PANEL_BACKGROUND_COLOR,
            base_pad=18,
            overlay_wh=(800, 265),
            overlay_rely=0.50,
        )
        self.seats = [s for s in seats if getattr(s, "is_active", True) and getattr(s, "main_bet", 0) > 0]
        # Order seat cards visually left-to-right matching the physical table (Seat 3 Left, Seat 2 Center, Seat 1 Right)
        self.visual_seats = sorted(self.seats, key=lambda s_obj: -int(s_obj.seat_index))
        self.bankroll = bankroll
        self.on_confirm_cb = on_confirm
        self.on_decline_cb = on_decline
        self._closed = False
        self.focused_seat_pos: int = 0
        self._seat_cards: dict[int, dict[str, Any]] = {}

        self.title("🛡 Dealer Shows Ace - Insurance")

        self.seat_vars: dict[int, tkinter.BooleanVar] = {}
        self.seat_costs: dict[int, int] = {}
        for s_obj in self.seats:
            cost = max(1, s_obj.main_bet // 2)
            self.seat_costs[s_obj.seat_index] = cost
            self.seat_vars[s_obj.seat_index] = tkinter.BooleanVar(value=False)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_decline)
        self.bind("<Escape>", lambda e: self._on_decline())
        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<KP_Enter>", lambda e: self._on_confirm())
        self.bind("<Left>", lambda e: self._move_seat_focus(-1))
        self.bind("<Right>", lambda e: self._move_seat_focus(1))
        self.bind("<Tab>", lambda e: self._move_seat_focus(1))
        self.bind("<space>", lambda e: self._toggle_focused_seat())
        for k_num in ("1", "2", "3"):
            self.bind(k_num, lambda e, n=int(k_num): self._toggle_seat_by_index(n))
        for k_all in ("a", "A", "y", "Y"):
            self.bind(k_all, lambda e: self._on_insure_all())
        for k_dec in ("n", "N"):
            self.bind(k_dec, lambda e: self._on_decline())
        self.focus_set()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape" or ch.lower() == "n" or ks in ("n", "N"):
            self._on_decline()
        elif ks in ("Return", "KP_Enter"):
            self._on_confirm()
        elif ks == "Left":
            self._move_seat_focus(-1)
        elif ks in ("Right", "Tab"):
            self._move_seat_focus(1)
        elif ks == "space":
            self._toggle_focused_seat()
        elif ch in ("1", "2", "3") or ks in ("1", "2", "3", "KP_1", "KP_2", "KP_3"):
            digit = int(ch) if ch in ("1", "2", "3") else int(ks[-1])
            self._toggle_seat_by_index(digit)
        elif ch.lower() in ("a", "y") or ks in ("a", "A", "y", "Y"):
            self._on_insure_all()
        return "break"

    def _build_ui(self) -> None:
        s = self.art_scale
        content = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            relief="ridge",
            borderwidth=2 * s,
            highlightbackground="#d4af37",
            highlightthickness=2 * s,
            padx=16 * s,
            pady=8 * s,
        )
        content.pack(fill="both", expand=True)

        hdr_row = tkinter.Frame(content, background=PANEL_BACKGROUND_COLOR)
        hdr_row.pack(fill="x", pady=(0, 3 * s))
        tkinter.Label(
            hdr_row,
            text="🛡 DEALER SHOWS AN ACE — MULTI-SEAT INSURANCE",
            font=("Tiny5 Duo", -24 * s, "bold"),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(side="left")

        self.total_cost_lbl = tkinter.Label(
            hdr_row,
            text="Selected Insurance: $0",
            font=("Tiny5", -24 * s, "bold"),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        )
        self.total_cost_lbl.pack(side="right")

        tkinter.Label(
            content,
            text=f"Pays 2:1 on Dealer Blackjack  •  Bankroll: ${self.bankroll:,}  •  Toggle Seats: [1] [2] [3] or [◄/► + Space]",
            font=("Tiny5", -16 * s, "normal"),
            fg="#b2dfdb",
            background=PANEL_BACKGROUND_COLOR,
            anchor="w",
        ).pack(fill="x", pady=(0, 5 * s))

        cards_row = tkinter.Frame(content, background=PANEL_BACKGROUND_COLOR)
        cards_row.pack(fill="both", expand=True, pady=(0, 6 * s))
        cards_row.rowconfigure(0, weight=1)

        self.cb_widgets = {}
        total_all_cost = sum(self.seat_costs.values())
        seat_short = {1: "Seat 1 (Right)", 2: "Seat 2 (Center)", 3: "Seat 3 (Left)"}

        col_total = max(1, len(self.visual_seats))
        for col_i, s_obj in enumerate(self.visual_seats):
            cards_row.columnconfigure(col_i, weight=1, uniform="ms_ins_cards")
            s_idx = s_obj.seat_index
            cost = self.seat_costs[s_idx]
            can_afford = self.bankroll >= cost

            scard = tkinter.Frame(
                cards_row,
                background="#082415",
                relief="ridge",
                borderwidth=1 * s,
                highlightbackground="#1f5736",
                highlightthickness=2 * s,
                padx=10 * s,
                pady=5 * s,
                cursor="hand2" if can_afford else "arrow",
            )
            scard.grid(row=0, column=col_i, sticky="nsew", padx=4 * s)

            t_lbl = tkinter.Label(
                scard,
                text=f"[{s_idx}] {seat_short.get(s_idx, f'Seat {s_idx}')}",
                font=("Tiny5", -24 * s, "bold"),
                fg="#ffd54f" if can_afford else "#78909c",
                background="#082415",
                anchor="w",
            )
            t_lbl.pack(fill="x")

            m_lbl = tkinter.Label(
                scard,
                text=f"Main ${s_obj.main_bet:,}  ->  Insure ${cost:,}",
                font=("Tiny5", -16 * s, "normal"),
                fg="#ffffff" if can_afford else "#78909c",
                background="#082415",
                anchor="w",
            )
            m_lbl.pack(fill="x", pady=(2 * s, 4 * s))

            st_lbl = tkinter.Button(
                scard,
                text="[ SKIP ]" if can_afford else "[ NO FUNDS ]",
                font=("Tiny5", -24 * s, "bold"),
                fg="#90a4ae" if can_afford else "#546e7a",
                disabledforeground="#546e7a",
                background="#082415",
                activebackground="#123d24",
                activeforeground="#ffd700",
                relief="flat",
                borderwidth=0,
                takefocus=False,
                state="normal" if can_afford else "disabled",
                cursor="hand2" if can_afford else "arrow",
                command=lambda idx=s_idx, p=col_i: (self._set_seat_focus(p), self._toggle_seat_by_index(idx)),
            )
            st_lbl.pack(fill="x")

            if can_afford:
                for w_t in (scard, t_lbl, m_lbl):
                    w_t.bind("<Button-1>", lambda e, idx=s_idx, p=col_i: (self._set_seat_focus(p), self._toggle_seat_by_index(idx)))

            self._seat_cards[s_idx] = {
                "frame": scard,
                "labels": (t_lbl, m_lbl, st_lbl),
                "status": st_lbl,
                "can_afford": can_afford,
                "pos": col_i,
            }
            self.cb_widgets[s_idx] = st_lbl

        btn_row = tkinter.Frame(content, background=PANEL_BACKGROUND_COLOR)
        btn_row.pack(fill="x")
        btn_row.columnconfigure(0, weight=1, uniform="ms_ins_btns")
        btn_row.columnconfigure(1, weight=1, uniform="ms_ins_btns")
        btn_row.columnconfigure(2, weight=1, uniform="ms_ins_btns")

        can_insure_all = self.bankroll >= total_all_cost and len(self.seats) > 0
        ms_btn_f = ("Tiny5", -24 * s, "bold")
        self.btn_insure_all = tkinter.Button(
            btn_row,
            text=f"[A] Insure All (${total_all_cost:,})",
            font=ms_btn_f,
            background="#ff9800",
            fg="#141008",
            activebackground="#ffa726",
            activeforeground="#000000",
            state="normal" if can_insure_all else "disabled",
            takefocus=False,
            cursor="hand2" if can_insure_all else "arrow",
            command=self._on_insure_all,
            padx=10 * s,
            pady=4 * s,
        )
        self.btn_insure_all.grid(row=0, column=0, sticky="ew", padx=(0, 6 * s))

        self.btn_confirm = tkinter.Button(
            btn_row,
            text="Confirm Selection [Enter]",
            font=ms_btn_f,
            background="#1b5e20",
            fg="white",
            activebackground="#2e7d32",
            activeforeground="white",
            takefocus=False,
            cursor="hand2",
            command=self._on_confirm,
            padx=10 * s,
            pady=4 * s,
        )
        self.btn_confirm.grid(row=0, column=1, sticky="ew", padx=6 * s)

        self.btn_decline_all = tkinter.Button(
            btn_row,
            text="Decline All [Esc / N]",
            font=ms_btn_f,
            background="#37474f",
            fg="white",
            activebackground="#455a64",
            activeforeground="white",
            takefocus=False,
            cursor="hand2",
            command=self._on_decline,
            padx=10 * s,
            pady=4 * s,
        )
        self.btn_decline_all.grid(row=0, column=2, sticky="ew", padx=(6 * s, 0))
        self._refresh_seat_card_visuals()
        self.fit_overlay_to_requested(pad_w=8 * s, pad_h=4 * s)

    def _set_seat_focus(self, pos: int) -> None:
        if not self.visual_seats:
            return
        self.focused_seat_pos = max(0, min(len(self.visual_seats) - 1, int(pos)))
        self._refresh_seat_card_visuals()

    def _move_seat_focus(self, delta: int) -> str:
        if self.visual_seats:
            self.focused_seat_pos = (self.focused_seat_pos + delta) % len(self.visual_seats)
            self._refresh_seat_card_visuals()
        return "break"

    def _toggle_focused_seat(self) -> str:
        if 0 <= self.focused_seat_pos < len(self.visual_seats):
            self._toggle_seat_by_index(self.visual_seats[self.focused_seat_pos].seat_index)
        return "break"

    def _toggle_seat_by_index(self, s_idx: int) -> None:
        if s_idx not in self.seat_vars:
            return
        rec = self._seat_cards.get(s_idx)
        if rec and not rec["can_afford"]:
            return
        cur = self.seat_vars[s_idx].get()
        self.seat_vars[s_idx].set(not cur)
        if rec:
            self.focused_seat_pos = rec["pos"]
        self._on_check_toggle()

    def _refresh_seat_card_visuals(self) -> None:
        foc_seat_idx = self.visual_seats[self.focused_seat_pos].seat_index if self.visual_seats else -1
        for s_idx, rec in self._seat_cards.items():
            checked = self.seat_vars[s_idx].get()
            is_foc = s_idx == foc_seat_idx
            bg_c = "#134229" if checked else ("#0d311d" if is_foc else "#082415")
            bd_c = "#ffd700" if is_foc else ("#00e676" if checked else "#1f5736")
            rec["frame"].configure(background=bg_c, highlightbackground=bd_c)
            for lbl in rec["labels"]:
                lbl.configure(background=bg_c)
            if not rec["can_afford"]:
                rec["status"].configure(text="[ NO FUNDS ]", fg="#546e7a")
            elif checked:
                rec["status"].configure(text="✓ INSURED", fg="#00e676")
            else:
                rec["status"].configure(text="[ SKIP ]", fg="#b0bec5")

    def _on_check_toggle(self) -> None:
        total = sum(self.seat_costs[s_idx] for s_idx, var in self.seat_vars.items() if var.get())
        if total > self.bankroll:
            for s_idx, var in self.seat_vars.items():
                if var.get() and total > self.bankroll:
                    var.set(False)
                    total -= self.seat_costs[s_idx]
        self.total_cost_lbl.config(text=f"Selected Insurance: ${total}")
        self._refresh_seat_card_visuals()

    def _on_insure_all(self) -> None:
        total_all_cost = sum(self.seat_costs.values())
        if self.bankroll < total_all_cost:
            return
        for var in self.seat_vars.values():
            var.set(True)
        self._on_confirm()

    def _on_confirm(self) -> str:
        if self._closed:
            return "break"
        self._closed = True
        chosen = {s_idx: self.seat_costs[s_idx] for s_idx, var in self.seat_vars.items() if var.get()}
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_confirm_cb:
            self.on_confirm_cb(chosen)
        return "break"

    def _on_decline(self) -> str:
        if self._closed:
            return "break"
        self._closed = True
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_decline_cb:
            self.on_decline_cb()
        return "break"


# ============================================================================
# 3. SettingsDialog (Full-Screen 2-Column Casino Settings & House Rules)
# ============================================================================

class SettingsDialog(InWindowScreenHost):
    """
    Full-screen widescreen Casino Settings, House Rules & Save Management screen.
    Utilizes 2-column dashboard layouts across both Tab 0 (Table & Audio) and
    Tab 1 (House Rules) so every control fits on screen without vertical scrolling
    on Steam Deck (1280x800) and 720p (1280x720) displays.
    """

    def __init__(self, parent: tkinter.Tk, app: Any):
        super().__init__(
            parent,
            app=app,
            profile=getattr(app, "display_profile", None),
            background=PANEL_BACKGROUND_COLOR,
            base_pad=22,
        )
        self.app = app
        self.title("⚙ Settings & Casino Records")

        self.active_tab: int = 0
        initial_rules = getattr(app, "house_rules", None)
        self._draft_rules: HouseRules = (
            initial_rules.normalized() if isinstance(initial_rules, HouseRules) else HouseRules()
        )
        self.status_msg_var = tkinter.StringVar(value="All casino records active.")
        self.rules_status_var = tkinter.StringVar(value="")

        self._build_chrome_and_tabs()
        self._switch_tab(0)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.focus_set()

    def _compute_menu_outer_padx(self, viewport_w: Optional[int] = None) -> int:
        if self.is_compact_2x:
            return 24
        return self.compute_outer_padx(viewport_w)

    def _build_chrome_and_tabs(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        outer_px = self._compute_menu_outer_padx(vw)
        tight_720 = (s == 1 and vh < 760)

        hdr_pady = 4 if compact else (6 * s if tight_720 else 8 * s)
        title_font = ("BoldPixels", -48 if compact else (-32 * s), "normal")
        hint_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        tab_btn_font = ("Tiny5", -32 if compact else (-24 * s if not tight_720 else -16 * s), "bold")
        tab_pady = 3 if compact else (5 * s if tight_720 else 6 * s)
        foot_pady = 3 if compact else (6 * s if tight_720 else 7 * s)

        # 1. Persistent Full-Width Header & Tab Bar
        self.header_frame = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=hdr_pady,
        )
        self.header_frame.pack(side="top", fill="x")

        title_row = tkinter.Frame(self.header_frame, background=PANEL_BACKGROUND_COLOR)
        title_row.pack(fill="x")

        tkinter.Label(
            title_row,
            text="⚙ CASINO SETTINGS & HOUSE RULES",
            font=title_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(side="left")

        tkinter.Label(
            title_row,
            text="Switch Tabs: [1] / [2] or [◄ / ►]   •   Close: [Esc]",
            font=hint_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(side="right")

        self.tab_bar = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=2 if compact else (3 * s),
        )
        self.tab_bar.pack(side="top", fill="x")
        self.tab_bar.columnconfigure(0, weight=1, uniform="settings_tabs")
        self.tab_bar.columnconfigure(1, weight=1, uniform="settings_tabs")

        self.tab_general_btn = tkinter.Button(
            self.tab_bar,
            text="[1] Table, Audio & Records",
            font=tab_btn_font,
            background="#1b5e20",
            fg="#ffd700",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            relief="sunken",
            borderwidth=2,
            cursor="hand2",
            padx=14 * s,
            pady=tab_pady,
            command=lambda: self._switch_tab(0),
        )
        self.tab_general_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6 * s))

        self.tab_rules_btn = tkinter.Button(
            self.tab_bar,
            text="[2] Casino House Rules & Limits",
            font=tab_btn_font,
            background="#082415",
            fg="#b0bec5",
            activebackground="#143d26",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=14 * s,
            pady=tab_pady,
            command=lambda: self._switch_tab(1),
        )
        self.tab_rules_btn.grid(row=0, column=1, sticky="ew", padx=(6 * s, 0))

        # 2. Persistent Full-Width Bottom Footer: Green "Done" (2/3) + Red "Reset Data" (1/3)
        self.action_row = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=4 if compact else (8 * s),
        )
        self.action_row.pack(side="bottom", fill="x")
        self.action_row.columnconfigure(0, weight=2)
        self.action_row.columnconfigure(1, weight=1)

        self.done_btn = tkinter.Button(
            self.action_row,
            text="✔ Done (Esc)",
            font=tab_btn_font,
            background="#2e7d32",
            fg="white",
            activebackground="#388e3c",
            activeforeground="white",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            command=self._on_close,
            padx=16 * s,
            pady=foot_pady,
        )
        self.done_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8 * s))

        self.clear_save_btn = tkinter.Button(
            self.action_row,
            text="🗑 Reset Data",
            font=tab_btn_font,
            background="#b71c1c",
            fg="#ffffff",
            activebackground="#d32f2f",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            command=self._on_click_clear_save,
            padx=16 * s,
            pady=foot_pady,
        )
        self.clear_save_btn.grid(row=0, column=1, sticky="ew", padx=(8 * s, 0))

        # 3. Adaptive Scrollable Viewport Container
        self.canvas = tkinter.Canvas(
            self,
            background=PANEL_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
            height=240 * s,
        )
        self.v_scrollbar = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_content = tkinter.Frame(
            self.canvas,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=4 if compact else (6 * s),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll_update)

        self.scroll_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.bind("<Left>", lambda e: self._on_prev_tab())
        self.bind("<Right>", lambda e: self._on_next_tab())
        self.bind("<Tab>", lambda e: self._on_tab_key())
        self.bind("<Return>", lambda e: self._on_apply_house_rules() if self.active_tab == 1 else None)
        self.bind("1", lambda e: self._switch_tab(0))
        self.bind("2", lambda e: self._switch_tab(1))

        self._build_ui()

    def _on_viewport_resized(self, width: int, height: int) -> None:
        outer_px = self._compute_menu_outer_padx(width)
        for attr in ("header_frame", "tab_bar", "action_row", "scroll_content"):
            w = getattr(self, attr, None)
            if w is not None and w.winfo_exists():
                w.configure(padx=outer_px)

    def on_display_profile_changed(self, new_profile: Any) -> None:
        old_s = self.menu_scale
        old_c = self.is_compact_2x
        super().on_display_profile_changed(new_profile)
        if self.menu_scale != old_s or self.is_compact_2x != old_c:
            cur_tab = self.active_tab
            self._build_chrome_and_tabs()
            self._switch_tab(cur_tab)
        else:
            self._refresh_display_controls()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        for attr in ("_window_mode_picker", "_play_mode_picker", "_table_seats_picker"):
            picker = getattr(self, attr, None)
            if picker is not None and picker.winfo_exists():
                return picker.handle_modal_key(event)
        confirm_key = getattr(self, "_active_confirm_key", None)
        if callable(confirm_key):
            return confirm_key(event)
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape":
            self._on_close()
        elif ks == "Left":
            self._on_prev_tab()
        elif ks in ("Right", "Tab"):
            self._on_next_tab()
        elif ks in ("Return", "KP_Enter") and self.active_tab == 1:
            self._on_apply_house_rules()
        elif ch == "1":
            self._switch_tab(0)
        elif ch == "2":
            self._switch_tab(1)
        return "break"

    def _on_prev_tab(self) -> str:
        self._switch_tab((self.active_tab - 1) % 2)
        return "break"

    def _on_next_tab(self) -> str:
        self._switch_tab((self.active_tab + 1) % 2)
        return "break"

    def _on_tab_key(self) -> str:
        self._switch_tab((self.active_tab + 1) % 2)
        return "break"

    def _switch_tab(self, tab_idx: int) -> None:
        """Switches between Tab 0 (Table & Audio) and Tab 1 (House Rules)."""
        self.active_tab = 0 if int(tab_idx) == 0 else 1
        if self.active_tab == 0:
            self.tab_rules_frame.pack_forget()
            self.tab_general_frame.pack(fill="both", expand=True)
            self.tab_general_btn.configure(background="#1b5e20", fg="#ffd700", relief="sunken")
            self.tab_rules_btn.configure(background="#082415", fg="#b0bec5", relief="raised")
        else:
            self.tab_general_frame.pack_forget()
            self.tab_rules_frame.pack(fill="both", expand=True)
            self.tab_general_btn.configure(background="#082415", fg="#b0bec5", relief="raised")
            self.tab_rules_btn.configure(background="#1b5e20", fg="#ffd700", relief="sunken")
            self._refresh_house_rules_controls()
        try:
            self.canvas.yview_moveto(0.0)
            self.scroll_content.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _on_scroll_update(self, first: Any, last: Any) -> None:
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack_forget()
        else:
            if not bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack(side="right", fill="y")

    def _sync_canvas_scroll_fit(self) -> None:
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        cw = max(1, int(self.canvas.winfo_width()))
        ch = max(1, int(self.canvas.winfo_height()))
        req_h = int(self.scroll_content.winfo_reqheight())
        target_h = max(ch, req_h)
        self.canvas.itemconfig(self.canvas_window, width=cw, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, cw, target_h))

    def _on_frame_configure(self, event: Any) -> None:
        self._sync_canvas_scroll_fit()

    def _on_canvas_configure(self, event: Any) -> None:
        req_h = int(self.scroll_content.winfo_reqheight())
        target_h = max(int(event.height), req_h)
        self.canvas.itemconfig(self.canvas_window, width=event.width, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, max(1, int(event.width)), target_h))

    def _on_mousewheel(self, event: Any) -> None:
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_ui(self) -> None:
        s = self.menu_scale
        compact = self.is_compact_2x
        _, vh = self._resolve_host_wh()
        tight_720 = (s == 1 and vh < 760)
        hdr_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        btn_font = ("Tiny5", -32 if compact else (-24 if (s == 1 and not tight_720) else (-16 * s)), "bold")
        body_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "normal")
        btn_pady = 3 if compact else (4 if tight_720 else 5 * s)
        row_pady = 4 if compact else (5 if tight_720 else 7 * s)

        self.tab_general_frame = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        self.tab_rules_frame = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)

        # ====================================================================
        # TAB 0: 2-Column Widescreen Layout (Left: Preferences | Right: Records)
        # ====================================================================
        t0_grid = tkinter.Frame(self.tab_general_frame, background=PANEL_BACKGROUND_COLOR)
        t0_grid.pack(fill="both", expand=True)
        t0_grid.columnconfigure(0, weight=1, uniform="settings_t0_cols")
        t0_grid.columnconfigure(1, weight=1, uniform="settings_t0_cols")
        t0_grid.rowconfigure(0, weight=1)

        ctrl_frame = tkinter.LabelFrame(
            t0_grid,
            text=" Table, Audio & Display Preferences ",
            font=hdr_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
            padx=14 * s,
            pady=6 if compact else (8 * s),
        )
        ctrl_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8 * s), pady=(0, 4 * s))

        tkinter.Label(
            ctrl_frame,
            text="Audio & Dialogue:",
            font=hdr_font,
            fg="#b2dfdb",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="w", pady=(0, 3 * s if not compact else 3))

        audio_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        audio_row.pack(fill="x", pady=(0, row_pady))
        audio_row.columnconfigure(0, weight=1, uniform="st_aud")
        audio_row.columnconfigure(1, weight=1, uniform="st_aud")

        self.sound_btn = tkinter.Button(
            audio_row,
            textvariable=self.app.sound_status_var,
            font=btn_font,
            background="#004d40",
            fg="white",
            activebackground="#00695c",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=lambda: (self.app._on_toggle_sound(), self._refresh_audio_btn_colors()),
            padx=10 * s,
            pady=btn_pady,
        )
        self.sound_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4 * s))

        if hasattr(self.app, "voice_status_var"):
            self.voice_btn = tkinter.Button(
                audio_row,
                textvariable=self.app.voice_status_var,
                font=btn_font,
                background="#004d40",
                fg="white",
                activebackground="#00695c",
                activeforeground="white",
                relief="ridge",
                borderwidth=1,
                cursor="hand2",
                command=lambda: (self.app._on_toggle_voice(), self._refresh_audio_btn_colors()),
                padx=10 * s,
                pady=btn_pady,
            )
            self.voice_btn.grid(row=0, column=1, sticky="ew", padx=(4 * s, 0))
        self._refresh_audio_btn_colors()

        tkinter.Label(
            ctrl_frame,
            text="Display & Customization:",
            font=hdr_font,
            fg="#b2dfdb",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="w", pady=(2, 3))

        disp_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        disp_row.pack(fill="x", pady=(0, 4 if compact else 6 * s))
        disp_row.columnconfigure(0, weight=1, uniform="disp_r1")
        disp_row.columnconfigure(1, weight=1, uniform="disp_r1")

        self.wardrobe_btn = tkinter.Button(
            disp_row,
            text="🎩 Wardrobe",
            font=btn_font,
            background="#1b5e20",
            fg="white",
            activebackground="#2e7d32",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self.app._open_wardrobe_dialog,
            padx=8 * s,
            pady=btn_pady,
        )
        self.wardrobe_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4 * s))

        self.card_scale_btn = tkinter.Button(
            disp_row,
            text="🃏 Cards: Auto",
            font=btn_font,
            background="#004d40",
            fg="white",
            activebackground="#00695c",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_toggle_card_scale,
            padx=8 * s,
            pady=btn_pady,
        )
        self.card_scale_btn.grid(row=0, column=1, sticky="ew", padx=(4 * s, 0))

        disp_row2 = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        disp_row2.pack(fill="x", pady=(0, 4 if compact else 6 * s))
        disp_row2.columnconfigure(0, weight=1, uniform="disp_r2")
        disp_row2.columnconfigure(1, weight=1, uniform="disp_r2")

        self.window_size_btn = tkinter.Button(
            disp_row2,
            text="🖥 Window Mode: Auto",
            font=btn_font,
            background="#004d40",
            fg="white",
            activebackground="#00695c",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_open_window_mode_picker,
            padx=8 * s,
            pady=btn_pady,
        )
        self.window_size_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4 * s))

        self.fullscreen_btn = tkinter.Button(
            disp_row2,
            text="⛶ Fullscreen [F11]",
            font=btn_font,
            background="#004d40",
            fg="white",
            activebackground="#00695c",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_toggle_fullscreen_from_settings,
            padx=8 * s,
            pady=btn_pady,
        )
        self.fullscreen_btn.grid(row=0, column=1, sticky="ew", padx=(4 * s, 0))

        self.diagnostics_lbl = tkinter.Label(
            ctrl_frame,
            text="",
            font=("Tiny5", -24 if compact else (-16 * s), "normal"),
            fg="#80cbc4",
            background="#072214",
            padx=8 * s,
            pady=3 if compact else 4 * s,
            anchor="w",
            justify="left",
        )
        self.diagnostics_lbl.pack(fill="x", pady=(2, row_pady))
        self._refresh_display_controls()

        tkinter.Label(
            ctrl_frame,
            text="Play Mode & Onboarding:",
            font=hdr_font,
            fg="#b2dfdb",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="w", pady=(2, 3))

        sub_readout_font = ("Tiny5", -24 if compact else (-16 * s), "normal")

        mode_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        mode_row.pack(fill="x", pady=(0, row_pady))
        mode_row.columnconfigure(0, weight=1, uniform="st_mode")
        mode_row.columnconfigure(1, weight=1, uniform="st_mode")

        self.mode_btn = tkinter.Button(
            mode_row,
            text="🎮 Play Mode...",
            font=btn_font,
            background="#004d40",
            fg="white",
            activebackground="#00695c",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_open_play_mode_picker,
            padx=8 * s,
            pady=btn_pady,
        )
        self.mode_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4 * s))

        self.welcome_btn = tkinter.Button(
            mode_row,
            text="🌟 Welcome Screen...",
            font=btn_font,
            background="#1b5e20",
            fg="white",
            activebackground="#2e7d32",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_open_welcome_screen,
            padx=8 * s,
            pady=btn_pady,
        )
        self.welcome_btn.grid(row=0, column=1, sticky="ew", padx=(4 * s, 0))

        self.mode_current_lbl = tkinter.Label(
            mode_row,
            text="",
            font=sub_readout_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
            anchor="w",
            padx=4 * s,
        )
        self.mode_current_lbl.grid(row=1, column=0, sticky="ew", padx=(0, 4 * s), pady=(2, 0))

        tkinter.Label(
            ctrl_frame,
            text="Table Seats & Advantage Training:",
            font=hdr_font,
            fg="#b2dfdb",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="w", pady=(2, 3))

        seats_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        seats_row.pack(fill="x", pady=(0, 2 * s))
        seats_row.columnconfigure(0, weight=1, uniform="st_seats")
        seats_row.columnconfigure(1, weight=1, uniform="st_seats")

        self.seats_btn = tkinter.Button(
            seats_row,
            text="🪑 Table Seats...",
            font=btn_font,
            background="#004d40",
            fg="white",
            activebackground="#00695c",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_open_table_seats_picker,
            padx=8 * s,
            pady=btn_pady,
        )
        self.seats_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4 * s))

        self.bootcamp_btn = tkinter.Button(
            seats_row,
            text="🎓 Counting Bootcamp...",
            font=btn_font,
            background="#1b5e20",
            fg="white",
            activebackground="#2e7d32",
            activeforeground="white",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_open_counting_bootcamp,
            padx=8 * s,
            pady=btn_pady,
        )
        self.bootcamp_btn.grid(row=0, column=1, sticky="ew", padx=(4 * s, 0))

        self.seats_current_lbl = tkinter.Label(
            seats_row,
            text="",
            font=sub_readout_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
            anchor="w",
            padx=4 * s,
        )
        self.seats_current_lbl.grid(row=1, column=0, sticky="ew", padx=(0, 4 * s), pady=(2, 0))
        self._refresh_mode_and_seats_labels()

        # Right Column (Tab 0): Career Save Data & Quick Salon Launchers
        save_frame = tkinter.LabelFrame(
            t0_grid,
            text=" Save Data & Hall of Fame Records ",
            font=hdr_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
            padx=16 * s,
            pady=6 if compact else (10 * s),
        )
        save_frame.grid(row=0, column=1, sticky="nsew", padx=(8 * s, 0), pady=(0, 4 * s))

        self.stats_frame = tkinter.Frame(
            save_frame,
            background="#082415",
            highlightbackground="#1f5736",
            highlightthickness=1 * s,
            padx=12 * s,
            pady=6 if compact else (10 * s),
        )
        self.stats_frame.pack(fill="x", pady=(0, 8 if compact else 10 * s))

        stat_pady = 2 if compact else (3 * s)
        self.lbl_peak = tkinter.Label(
            self.stats_frame, text="", font=body_font, fg="#69f0ae", background="#082415", anchor="w",
        )
        self.lbl_peak.pack(fill="x", pady=stat_pady)

        self.lbl_hands = tkinter.Label(
            self.stats_frame, text="", font=body_font, fg="#e0e0e0", background="#082415", anchor="w",
        )
        self.lbl_hands.pack(fill="x", pady=stat_pady)

        self.lbl_counting = tkinter.Label(
            self.stats_frame, text="", font=body_font, fg="#80d8ff", background="#082415", anchor="w",
        )
        self.lbl_counting.pack(fill="x", pady=stat_pady)

        self.lbl_side_bets = tkinter.Label(
            self.stats_frame, text="", font=body_font, fg="#e0e0e0", background="#082415", anchor="w",
        )
        self.lbl_side_bets.pack(fill="x", pady=stat_pady)

        self.lbl_exorcist = tkinter.Label(
            self.stats_frame, text="", font=body_font, fg="#ffd54f", background="#082415", anchor="w",
        )
        self.lbl_exorcist.pack(fill="x", pady=stat_pady)

        self._refresh_stats_display()

        quick_hub = tkinter.Frame(
            save_frame,
            background="#092114",
            highlightbackground="#1f4d30",
            highlightthickness=1 * s,
            padx=12 * s,
            pady=6 if compact else (10 * s),
        )
        quick_hub.pack(fill="both", expand=True, pady=(0, 8 if compact else 10 * s))

        tkinter.Label(
            quick_hub,
            text="Quick Salon Launchers & Shortcuts",
            font=hdr_font,
            fg="#ffd700",
            background="#092114",
            anchor="w",
        ).pack(fill="x", pady=(0, 4 * s if not compact else 4))

        q_grid = tkinter.Frame(quick_hub, background="#092114")
        q_grid.pack(fill="x", pady=(0, 4))
        q_grid.columnconfigure(0, weight=1, uniform="q_hub")
        q_grid.columnconfigure(1, weight=1, uniform="q_hub")

        quick_specs = [
            ("🏆 Hall of Fame [Shift+H]", lambda: (self._on_close(), self.app._open_wardrobe_dialog(initial_tab=1))),
            ("📊 Tripometer [T]", lambda: (self._on_close(), self.app._on_tripometer_shortcut())),
            ("⌨ Controls Guide [F1]", lambda: (self._on_close(), self.app._toggle_shortcuts_overlay())),
            ("🗺 Venue Tour [Shift+T]", lambda: (self._on_close(), self.app._on_tour_shortcut())),
        ]
        for qi, (q_txt, q_cmd) in enumerate(quick_specs):
            qr, qc = divmod(qi, 2)
            qb = tkinter.Button(
                q_grid,
                text=q_txt,
                font=btn_font,
                background="#123824",
                fg="#e0f2f1",
                activebackground="#1b5e20",
                activeforeground="#ffffff",
                relief="ridge",
                borderwidth=1,
                cursor="hand2",
                padx=8 * s,
                pady=btn_pady,
                command=q_cmd,
            )
            qb.grid(row=qr, column=qc, sticky="ew", padx=3 * s, pady=3)

        lbl_status = tkinter.Label(
            save_frame,
            textvariable=self.status_msg_var,
            font=body_font,
            fg="#ffeb3b",
            background="#072214",
            padx=10 * s,
            pady=5 if compact else 8 * s,
            anchor="w",
        )
        lbl_status.pack(side="bottom", fill="x")

        # ====================================================================
        # TAB 1: 2-Column Widescreen House Rules & Betting Limits
        # ====================================================================
        self._build_house_rules_tab()

    def _refresh_audio_btn_colors(self) -> None:
        if hasattr(self, "sound_btn") and hasattr(self.app, "sound_status_var"):
            snd_on = "ON" in str(self.app.sound_status_var.get())
            self.sound_btn.configure(background="#1b5e20" if snd_on else "#263238", fg="#ffd700" if snd_on else "#cfd8dc")
        if hasattr(self, "voice_btn") and hasattr(self.app, "voice_status_var"):
            voc_on = "ON" in str(self.app.voice_status_var.get())
            self.voice_btn.configure(background="#1b5e20" if voc_on else "#263238", fg="#ffd700" if voc_on else "#cfd8dc")

    def _build_house_rules_tab(self) -> None:
        """Builds Tab 1 (House Rules) in a 2-column widescreen grid requiring zero scroll across 720p/800p/1080p/1440p."""
        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        tight_720 = (s == 1 and vh < 760)
        sec_hdr_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        pill_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        commit_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        pill_pady = 2 if compact else (2 if tight_720 else 4 * s)

        edge_banner = tkinter.Frame(
            self.tab_rules_frame,
            background="#082415",
            highlightbackground="#d4af37",
            highlightthickness=1 * s,
            padx=12 * s,
            pady=3 if compact else (4 * s),
        )
        edge_banner.pack(fill="x", pady=(0, 4 if compact else 5 * s))
        edge_banner.columnconfigure(0, weight=1)
        edge_banner.columnconfigure(1, weight=1)

        self.house_edge_label = tkinter.Label(
            edge_banner,
            text="",
            font=sec_hdr_font,
            fg="#ffd700",
            background="#082415",
            anchor="w",
        )
        self.house_edge_label.grid(row=0, column=0, sticky="w")

        self.active_rules_badge_label = tkinter.Label(
            edge_banner,
            text="",
            font=("Tiny5", -24 if compact else (-16 * s), "normal"),
            fg="#80cbc4",
            background="#082415",
            anchor="e",
        )
        self.active_rules_badge_label.grid(row=0, column=1, sticky="e")

        rules_grid = tkinter.Frame(self.tab_rules_frame, background=PANEL_BACKGROUND_COLOR)
        rules_grid.pack(fill="both", expand=True)
        rules_grid.columnconfigure(0, weight=1, uniform="settings_t1_cols")
        rules_grid.columnconfigure(1, weight=1, uniform="settings_t1_cols")
        rules_grid.rowconfigure(0, weight=1)

        left_col = tkinter.Frame(rules_grid, background=PANEL_BACKGROUND_COLOR)
        left_col.grid(row=0, column=0, sticky="nsew", padx=(0, 8 * s))

        right_col = tkinter.Frame(rules_grid, background=PANEL_BACKGROUND_COLOR)
        right_col.grid(row=0, column=1, sticky="nsew", padx=(8 * s, 0))

        def make_section_label(parent: tkinter.Misc, title: str) -> None:
            tkinter.Label(
                parent,
                text=title,
                font=sec_hdr_font,
                fg="#b2dfdb",
                background=PANEL_BACKGROUND_COLOR,
            ).pack(anchor="w", pady=(1, 1) if (compact or tight_720) else (2 * s, 1 * s))

        def make_option_grid(
            parent: tkinter.Misc,
            options: list[tuple[Any, str]],
            cols: int,
            on_pick: Callable[[Any], None],
            uniform_tag: str,
        ) -> dict[Any, tkinter.Button]:
            frame = tkinter.Frame(parent, background=PANEL_BACKGROUND_COLOR)
            frame.pack(fill="x", pady=(0, 2 if (compact or tight_720) else 3 * s))
            for col in range(cols):
                frame.columnconfigure(col, weight=1, uniform=uniform_tag)
            mapping: dict[Any, tkinter.Button] = {}
            for idx, (val, label) in enumerate(options):
                r, c = divmod(idx, cols)
                b = tkinter.Button(
                    frame,
                    text=label,
                    font=pill_font,
                    background="#004d40",
                    fg="#ffffff",
                    activebackground="#00695c",
                    activeforeground="#ffffff",
                    relief="ridge",
                    borderwidth=1,
                    cursor="hand2",
                    padx=6 * s,
                    pady=pill_pady,
                    command=lambda v=val: on_pick(v),
                )
                b.grid(row=r, column=c, sticky="ew", padx=3 * s, pady=1)
                mapping[val] = b
            return mapping

        # Left Column: 1. Built-In Venue Presets (2x3 grid) + 2. Table Betting Limits + Commit Bar
        presets_box = tkinter.LabelFrame(
            left_col,
            text=" Casino Venue Presets ",
            font=sec_hdr_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
            padx=10 * s,
            pady=3 if compact else (4 * s),
        )
        presets_box.pack(fill="x", pady=(0, 4 if compact else 5 * s))
        for col in range(3):
            presets_box.columnconfigure(col, weight=1, uniform="hr_presets")

        self._preset_buttons: dict[str, tkinter.Button] = {}
        preset_order = [
            ("classic_4_deck", "Classic 4D"),
            ("reno_single_deck", "1D Reno"),
            ("downtown_pitch", "2D Pitch"),
            ("vegas_strip", "6D Strip"),
            ("high_roller_vip", "VIP Salon"),
            ("tourist_trap_6_5", "8D 6:5 Trap"),
        ]
        for idx, (pid, short_lbl) in enumerate(preset_order):
            r, c = divmod(idx, 3)
            btn = tkinter.Button(
                presets_box,
                text=short_lbl,
                font=pill_font,
                background="#004d40",
                fg="#ffffff",
                activebackground="#00695c",
                activeforeground="#ffffff",
                relief="ridge",
                borderwidth=1,
                cursor="hand2",
                padx=6 * s,
                pady=pill_pady + 1,
                command=lambda p=pid: self._select_preset(p),
            )
            btn.grid(row=r, column=c, sticky="ew", padx=3 * s, pady=1)
            self._preset_buttons[pid] = btn

        limits_box = tkinter.LabelFrame(
            left_col,
            text=" Table Betting Limits (Min & Max) ",
            font=sec_hdr_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
            padx=10 * s,
            pady=3 if compact else (4 * s),
        )
        limits_box.pack(fill="both", expand=True, pady=(0, 4 if compact else 5 * s))

        make_section_label(limits_box, "Minimum Main Bet:")
        self._min_bet_buttons = make_option_grid(
            limits_box,
            [(m, f"${m:,}") for m in ALLOWED_MINIMUM_BETS],
            3,
            lambda v: self._update_draft(minimum_bet=v),
            "hr_minbet",
        )

        make_section_label(limits_box, "Maximum Main Bet:")
        max_bet_cols = 5 if vw >= 1600 else 4
        self._max_bet_buttons = make_option_grid(
            limits_box,
            [(0, "No Limit")] + [(m, f"${m:,}") for m in ALLOWED_MAXIMUM_BETS if m > 0],
            max_bet_cols,
            lambda v: self._update_draft(maximum_bet=v),
            "hr_maxbet",
        )

        commit_row = tkinter.Frame(left_col, background=PANEL_BACKGROUND_COLOR)
        commit_row.pack(fill="x", pady=(2, 2))
        commit_row.columnconfigure(0, weight=1, uniform="hr_commit")
        commit_row.columnconfigure(1, weight=1, uniform="hr_commit")

        self.apply_rules_btn = tkinter.Button(
            commit_row,
            text="✔ Apply Rules",
            font=commit_font,
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=10 * s,
            pady=4 if (compact or tight_720) else 6 * s,
            command=self._on_apply_house_rules,
        )
        self.apply_rules_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6 * s))

        self.reset_rules_defaults_btn = tkinter.Button(
            commit_row,
            text="↺ Classic Defaults",
            font=commit_font,
            background="#37474f",
            fg="#ffffff",
            activebackground="#455a64",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=10 * s,
            pady=4 if (compact or tight_720) else 6 * s,
            command=self._on_reset_draft_rules,
        )
        self.reset_rules_defaults_btn.grid(row=0, column=1, sticky="ew", padx=(6 * s, 0))

        self.rules_status_lbl = tkinter.Label(
            left_col,
            textvariable=self.rules_status_var,
            font=("Tiny5", -24 if compact else (-16 * s), "normal"),
            fg="#ffeb3b",
            background=PANEL_BACKGROUND_COLOR,
            anchor="w",
        )
        self.rules_status_lbl.pack(fill="x", pady=(2, 0))

        # Right Column: Shoe, Payout & Player Options
        rules_box = tkinter.LabelFrame(
            right_col,
            text=" Shoe, Payout & Player Options ",
            font=sec_hdr_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
            padx=12 * s,
            pady=4 if compact else (6 * s),
        )
        rules_box.pack(fill="both", expand=True)

        make_section_label(rules_box, "Shoe Deck Count:")
        self._deck_buttons = make_option_grid(
            rules_box,
            [(d, f"{d} Deck{'s' if d > 1 else ''}") for d in ALLOWED_DECK_COUNTS],
            3,
            lambda v: self._update_draft(deck_count=v),
            "hr_decks",
        )

        make_section_label(rules_box, "Dealer Soft 17 Rule:")
        self._s17_buttons = make_option_grid(
            rules_box,
            [(False, "Stand Soft 17 (S17)"), (True, "Hit Soft 17 (H17)")],
            2,
            lambda v: self._update_draft(dealer_hits_soft_17=v),
            "hr_s17",
        )

        make_section_label(rules_box, "Natural Blackjack Payout:")
        self._payout_buttons = make_option_grid(
            rules_box,
            [((3, 2), "Pays 3 to 2"), ((6, 5), "Pays 6 to 5")],
            2,
            lambda v: self._update_draft(blackjack_payout=v),
            "hr_payout",
        )

        make_section_label(rules_box, "Double After Split (DAS):")
        self._das_buttons = make_option_grid(
            rules_box,
            [(True, "DAS Allowed"), (False, "No DAS")],
            2,
            lambda v: self._update_draft(allow_das=v),
            "hr_das",
        )

        make_section_label(rules_box, "Double Down Restriction:")
        self._dbl_buttons = make_option_grid(
            rules_box,
            [
                ("any", "Any Two Cards"),
                ("9_10_11", "Hard 9 / 10 / 11"),
                ("10_11", "Hard 10 / 11"),
            ],
            3,
            lambda v: self._update_draft(double_restriction=v),
            "hr_dbl",
        )

        make_section_label(rules_box, "Late Surrender:")
        self._surr_buttons = make_option_grid(
            rules_box,
            [(True, "Surrender ON"), (False, "No Surrender")],
            2,
            lambda v: self._update_draft(allow_surrender=v),
            "hr_surr",
        )

        self._refresh_house_rules_controls()

    def _is_rules_change_allowed(self) -> bool:
        if getattr(self.app, "tour_active", False):
            return False
        phase = getattr(self.app, "round_phase", RoundPhase.BETTING)
        dealing = bool(getattr(self.app, "_dealing", False))
        return not dealing and phase in (RoundPhase.BETTING, RoundPhase.ROUND_OVER)

    def _select_preset(self, preset_id: str) -> None:
        if preset_id in VENUE_PRESETS:
            self._draft_rules = VENUE_PRESETS[preset_id]
            self.rules_status_var.set(
                f"Staged preset: {VENUE_PRESET_LABELS.get(preset_id, preset_id)} — click ✔ Apply Rules."
            )
            self._refresh_house_rules_controls()

    def _update_draft(self, **changes: Any) -> None:
        raw = self._draft_rules.to_dict()
        raw.update(changes)
        raw["preset_id"] = "custom"
        self._draft_rules = HouseRules.from_dict(raw)
        self.rules_status_var.set("Draft modified — click ✔ Apply Rules to reshuffle with new rules.")
        self._refresh_house_rules_controls()

    def _on_reset_draft_rules(self) -> None:
        self._draft_rules = HouseRules()
        self.rules_status_var.set("Draft reset to Classic 4-Deck defaults — click ✔ Apply Rules.")
        self._refresh_house_rules_controls()

    def _on_apply_house_rules(self) -> None:
        if getattr(self.app, "tour_active", False):
            self.rules_status_var.set("🔒 Active Casino Tour Salon rules are fixed. Exit Tour to customize.")
            self._refresh_house_rules_controls()
            return
        if not self._is_rules_change_allowed():
            self.rules_status_var.set("🔒 Finish current hand before changing House Rules.")
            self._refresh_house_rules_controls()
            return
        if hasattr(self.app, "apply_house_rules"):
            applied = self.app.apply_house_rules(self._draft_rules)
            if applied:
                self._draft_rules = self.app.house_rules
                self.rules_status_var.set(f"✓ Applied: {self.app.house_rules.short_badge()} (shoe reshuffled).")
            else:
                self.rules_status_var.set("🔒 Finish current hand before changing House Rules.")
        self._refresh_house_rules_controls()

    def _style_choice_buttons(self, mapping: dict[Any, tkinter.Button], selected_val: Any) -> None:
        for val, btn in mapping.items():
            is_sel = val == selected_val
            btn.configure(
                background="#1b5e20" if is_sel else "#0b2919",
                fg="#ffd700" if is_sel else "#cfd8dc",
                relief="sunken" if is_sel else "ridge",
            )

    def _refresh_house_rules_controls(self) -> None:
        r = self._draft_rules
        edge = estimate_house_edge_pct(r)
        preset_title = VENUE_PRESET_LABELS.get(r.preset_id, "Custom Rules")
        edge_col = "#69f0ae" if edge <= 0.55 else ("#ffd700" if edge <= 1.0 else "#ff8a80")
        self.house_edge_label.configure(
            text=f"Estimated House Edge: {edge:.2f}%  ({preset_title})",
            fg=edge_col,
        )
        live_rules = getattr(self.app, "house_rules", HouseRules())
        is_dirty = self._draft_rules != live_rules
        dirty_tag = "  [UNSAVED DRAFT]" if is_dirty else ""
        self.active_rules_badge_label.configure(
            text=f"Live: {live_rules.short_badge()}  |  Draft: {r.short_badge()}{dirty_tag}",
            fg="#ffd54f" if is_dirty else "#80cbc4",
        )

        self._style_choice_buttons(self._preset_buttons, r.preset_id)
        self._style_choice_buttons(self._deck_buttons, r.deck_count)
        self._style_choice_buttons(self._s17_buttons, r.dealer_hits_soft_17)
        self._style_choice_buttons(self._payout_buttons, r.blackjack_payout)
        self._style_choice_buttons(self._das_buttons, r.allow_das)
        self._style_choice_buttons(self._dbl_buttons, r.double_restriction)
        self._style_choice_buttons(self._surr_buttons, r.allow_surrender)
        self._style_choice_buttons(self._min_bet_buttons, r.minimum_bet)

        for max_val, btn in self._max_bet_buttons.items():
            if max_val != 0 and max_val < r.minimum_bet:
                btn.configure(state="disabled", background="#1c2621", fg="#546e7a", relief="flat")
            else:
                is_sel = max_val == r.maximum_bet
                btn.configure(
                    state="normal",
                    background="#1b5e20" if is_sel else "#0b2919",
                    fg="#ffd700" if is_sel else "#cfd8dc",
                    relief="sunken" if is_sel else "ridge",
                )

        unlocked = self._is_rules_change_allowed()
        if unlocked:
            is_dirty = self._draft_rules != live_rules
            self.apply_rules_btn.configure(
                state="normal",
                text="⚠ Apply Unsaved Rules [Enter]" if is_dirty else "✔ Apply Rules",
                background="#ef6c00" if is_dirty else "#2e7d32",
            )
            if self.rules_status_var.get().startswith("🔒"):
                self.rules_status_var.set("")
        else:
            self.apply_rules_btn.configure(state="disabled", text="✔ Apply Rules", background="#455a64")
            if getattr(self.app, "tour_active", False):
                self.rules_status_var.set("🔒 Active Casino Tour Salon rules are fixed. Exit Tour to customize.")
            else:
                self.rules_status_var.set("🔒 Finish current hand to change House Rules.")

    def _refresh_stats_display(self) -> None:
        """Refreshes the high scores, counting records, and achievement badges displayed in the dialog."""
        data = self.app.save_manager.data
        hs = data.highscores
        pct = (hs.total_hands_won / hs.total_hands_played * 100.0) if hs.total_hands_played > 0 else 0.0
        self.lbl_peak.configure(text=f"• All-Time Peak Bankroll: ${hs.peak_bankroll:,}")
        self.lbl_hands.configure(
            text=f"• Hands Won / Played: {hs.total_hands_won:,} / {hs.total_hands_played:,} ({pct:.1f}% Win Rate)  (Blackjacks: {hs.total_blackjacks:,})"
        )
        best_cnt = getattr(hs, "best_counting_streak", 0)
        curr_cnt = getattr(hs, "counting_streak", 0)
        self.lbl_counting.configure(
            text=f"• Card Counting Drill Streak: {curr_cnt} (All-Time Best: {best_cnt})"
        )
        sb_played = getattr(hs, "side_bets_played", 0)
        sb_won = getattr(hs, "side_bets_won", 0)
        sb_max = getattr(hs, "biggest_side_bet_win", 0)
        sb_pct = (sb_won / sb_played * 100.0) if sb_played > 0 else 0.0
        self.lbl_side_bets.configure(
            text=f"• Side Bets Won / Played: {sb_won:,} / {sb_played:,} ({sb_pct:.1f}% Win Rate)  (Best Win: ${sb_max:,})"
        )
        exorcist_str = "✦ UNLOCKED (Cursed Stakes & Tour Active)" if data.achievements.exorcist else "Locked (Survive Hell's Table)"
        self.lbl_exorcist.configure(text=f"• Exorcist Title: {exorcist_str}")

    def _ask_confirm_clear_save(self) -> bool:
        """
        Displays an explicit in-window confirmation modal warning that clearing the save file is irreversible.
        Isolated for headless unit testing.
        """
        return InWindowConfirmModal.ask_yes_no(
            parent_screen=self,
            title="⚠️ Confirm Irreversible Save Reset",
            message=(
                "WARNING: This action is irreversible!\n\n"
                "Clearing your save file will permanently reset all high scores, "
                "achievements (including Exorcist status), Tour medallions, statistics, and "
                "unlocked dealer costumes back to an initial blank slate.\n\n"
                "Are you sure you want to clear your save file?"
            ),
            confirm_label="🗑 Yes, Reset Save Data",
            cancel_label="✔ Keep My Save (Esc)",
            art_scale=self.menu_scale,
            allow_withdrawn=False,
        )

    def _on_click_clear_save(self) -> None:
        confirmed = self._ask_confirm_clear_save()
        if not confirmed:
            return

        self.app.clear_player_save_data()
        if hasattr(self.app, "apply_house_rules"):
            self.app.apply_house_rules(HouseRules())
        if hasattr(self.app, "tripometer") and self.app.tripometer is not None:
            self.app.tripometer.reset()
        if hasattr(self.app, "_refresh_trip_button_badge"):
            self.app._refresh_trip_button_badge()
        self._draft_rules = HouseRules()
        self._refresh_stats_display()
        self._refresh_house_rules_controls()
        self.status_msg_var.set("✓ Save file reset to initial blank slate.")

    def _refresh_mode_and_seats_labels(self) -> None:
        mode_name = str(getattr(self.app, "play_mode", "betting") or "betting").capitalize()
        if hasattr(self, "mode_current_lbl") and self.mode_current_lbl.winfo_exists():
            self.mode_current_lbl.configure(text=f"Current: {mode_name}")
        seats_count = int(getattr(self.app, "table_seats", 1) or 1)
        if hasattr(self, "seats_current_lbl") and self.seats_current_lbl.winfo_exists():
            self.seats_current_lbl.configure(
                text=f"Current: {seats_count} Seat{'s' if seats_count > 1 else ''}"
            )

    def _on_open_play_mode_picker(self) -> None:
        existing = getattr(self, "_play_mode_picker", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        self._play_mode_picker = PlayModePickerModal(
            self,
            self.app,
            on_select=self._on_play_mode_selected,
            on_cancel=lambda: setattr(self, "_play_mode_picker", None),
        )

    def _on_play_mode_selected(self, mode: str) -> None:
        self._play_mode_picker = None
        self._apply_play_mode_choice(mode)

    def _apply_play_mode_choice(self, next_mode: str) -> None:
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Exit the Casino Venue Tour before switching play mode.")
            return
        if next_mode == "training" and hasattr(self.app, "activate_training_mode_entry"):
            if hasattr(self, "mode_current_lbl") and self.mode_current_lbl.winfo_exists():
                self.mode_current_lbl.configure(text="Current: Training")
            self._on_close()
            self.app.activate_training_mode_entry(sync_save=True)
            return
        if hasattr(self.app, "set_table_seats"):
            self.app.set_table_seats(3 if next_mode == "training" else 1)
        if hasattr(self.app, "apply_play_mode"):
            self.app.apply_play_mode(next_mode)
        self._refresh_mode_and_seats_labels()
        self.status_msg_var.set(f"Play mode switched to {next_mode.capitalize()}.")

    def _on_cycle_play_mode(self) -> None:
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Exit the Casino Venue Tour before switching play mode.")
            return
        current = getattr(self.app, "play_mode", "betting")
        modes = ["casual", "betting", "training"]
        try:
            next_idx = (modes.index(current) + 1) % len(modes)
        except ValueError:
            next_idx = 0
        self._apply_play_mode_choice(modes[next_idx])

    def _on_open_table_seats_picker(self) -> None:
        existing = getattr(self, "_table_seats_picker", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        self._table_seats_picker = TableSeatsPickerModal(
            self,
            self.app,
            on_select=self._on_table_seats_selected,
            on_cancel=lambda: setattr(self, "_table_seats_picker", None),
        )

    def _on_table_seats_selected(self, seats_key: str) -> None:
        self._table_seats_picker = None
        try:
            new_count = int(seats_key)
        except ValueError:
            new_count = 1
        self._apply_table_seats_choice(new_count)

    def _apply_table_seats_choice(self, new_count: int) -> None:
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Casino Venue Tour salons are 1-Seat high-stakes tables.")
            return
        if hasattr(self.app, "set_table_seats"):
            self.app.set_table_seats(new_count)
        else:
            self.app.table_seats = new_count
        self._refresh_mode_and_seats_labels()
        if new_count == 3:
            self.status_msg_var.set("3-Seat Wagering enabled. Haunted Mode disabled for multi-seat play.")
        else:
            self.status_msg_var.set("Standard 1-Seat Wagering enabled.")

    def _on_toggle_table_seats(self) -> None:
        current = int(getattr(self.app, "table_seats", 1) or 1)
        self._apply_table_seats_choice(3 if current == 1 else 1)

    def _on_open_welcome_screen(self) -> None:
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Exit the Casino Venue Tour before switching Free-Play modes.")
            return
        if hasattr(self.app, "_open_welcome_splash_dialog"):
            self.app._open_welcome_splash_dialog()

    def _on_open_counting_bootcamp(self) -> None:
        self._on_close()
        if hasattr(self.app, "enter_counting_bootcamp"):
            self.app.enter_counting_bootcamp(start_view="map")

    def _refresh_display_controls(self) -> None:
        save_data = getattr(getattr(self.app, "save_manager", None), "data", None)
        strict_cards = bool(getattr(save_data, "strict_integer_cards", False))
        if hasattr(self, "card_scale_btn"):
            self.card_scale_btn.configure(
                text="🃏 Cards: 1x Crisp" if strict_cards else "🃏 Cards: Auto"
            )

        is_fs = bool(getattr(self.app, "_is_fullscreen", False))
        win_override = getattr(save_data, "window_profile_override", "auto") or "auto"
        win_labels = {
            "auto": "Auto",
            None: "Auto",
            "hd_720p": "720p",
            "deck_800p": "800p",
            "fhd_1080p": "1080p",
            "qhd_1440p": "1440p",
        }
        mode_lbl = "Fullscreen" if is_fs else win_labels.get(win_override, "Auto")
        if hasattr(self, "window_size_btn"):
            self.window_size_btn.configure(text=f"🖥 Window Mode: {mode_lbl}")

        if hasattr(self, "fullscreen_btn"):
            self.fullscreen_btn.configure(
                text="⛶ Exit Fullscreen [F11]" if is_fs else "⛶ Fullscreen [F11]"
            )

        prof = getattr(self.app, "display_profile", None)
        diag = getattr(self.app, "display_diagnostics", None)
        if hasattr(self, "diagnostics_lbl") and prof is not None:
            diag_str = diag.summary_line() if diag is not None and hasattr(diag, "summary_line") else ""
            suffix = f" • {diag_str}" if diag_str else ""
            self.diagnostics_lbl.configure(
                text=(
                    f"Display: {prof.name} ({prof.window_wh[0]}x{prof.window_wh[1]}) "
                    f"• Art {prof.art_scale}x | Cards {prof.card_scale:g}x{suffix}"
                )
            )

    def _on_toggle_card_scale(self) -> None:
        if hasattr(self.app, "save_manager") and self.app.save_manager is not None:
            cur = bool(getattr(self.app.save_manager.data, "strict_integer_cards", False))
            self.app.save_manager.set_display_preferences(strict_integer_cards=not cur)
        if hasattr(self.app, "refresh_display_profile_from_preferences"):
            self.app.refresh_display_profile_from_preferences()
        self._refresh_display_controls()
        strict_now = bool(getattr(self.app.save_manager.data, "strict_integer_cards", False))
        self.status_msg_var.set(
            "Card scaling set to 1x Crisp integer mode." if strict_now else "Card scaling set to Auto."
        )

    def _on_open_window_mode_picker(self) -> None:
        existing = getattr(self, "_window_mode_picker", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            return
        self._window_mode_picker = WindowModePickerModal(
            self,
            self.app,
            on_select=self._on_window_mode_selected,
            on_cancel=self._on_window_mode_picker_closed,
        )

    def _on_window_mode_picker_closed(self) -> None:
        self._window_mode_picker = None

    def _on_window_mode_selected(self, choice: str) -> None:
        self._window_mode_picker = None
        if hasattr(self.app, "set_window_mode_choice"):
            self.app.set_window_mode_choice(choice)
        elif hasattr(self.app, "save_manager") and self.app.save_manager is not None:
            self.app.save_manager.set_display_preferences(window_profile_override=choice)
            if hasattr(self.app, "refresh_display_profile_from_preferences"):
                self.app.refresh_display_profile_from_preferences()
        self._refresh_display_controls()
        prof = getattr(self.app, "display_profile", None)
        if prof is not None:
            if choice == "fullscreen":
                self.status_msg_var.set(
                    f"Window Mode set to Fullscreen ({prof.window_wh[0]}x{prof.window_wh[1]})."
                )
            else:
                self.status_msg_var.set(
                    f"Window Mode set to {prof.name} ({prof.window_wh[0]}x{prof.window_wh[1]})."
                )

    def _on_cycle_window_size(self) -> None:
        self._on_open_window_mode_picker()

    def _on_toggle_fullscreen_from_settings(self) -> None:
        if hasattr(self.app, "toggle_fullscreen"):
            self.app.toggle_fullscreen()
        self._refresh_display_controls()

    def _on_close(self) -> str:
        for attr in ("_window_mode_picker", "_play_mode_picker", "_table_seats_picker"):
            picker = getattr(self, attr, None)
            if picker is not None:
                setattr(self, attr, None)
                try:
                    if picker.winfo_exists():
                        picker.destroy()
                except Exception:
                    pass
        if hasattr(self.app, "_close_settings_dialog"):
            self.app._close_settings_dialog()
        else:
            self.destroy()
        return "break"


# ============================================================================
# 4. ShortcutsDialog (Full-Screen 2-Column Controls Reference)
# ============================================================================

class ShortcutsDialog(InWindowScreenHost):
    """
    Full-screen widescreen Keyboard Shortcuts & Controls reference screen.
    Utilizes 2 spacious side-by-side columns across the full viewport with
    two-tab category switching and adaptive scroll safety.
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        icon_loader: KeyboardIconLoader,
        icon_photo: Optional[Any] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent, background=PANEL_BACKGROUND_COLOR, base_pad=22)
        self.icon_loader = icon_loader
        self.on_close_cb = on_close
        self.title("Blackjack - Keyboard Shortcuts & Controls")

        self.current_tab = 0
        self._tab_frames: list[tkinter.Frame] = []

        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", self._on_close)
        self.bind("<question>", self._on_close)
        self.bind("?", self._on_close)
        self.bind("/", self._on_close)
        self.bind("<F1>", self._on_close)
        self.bind("<Left>", lambda e: self._switch_tab(0))
        self.bind("<Right>", lambda e: self._switch_tab(1))
        self.bind("<Tab>", lambda e: self._switch_tab(1 if self.current_tab == 0 else 0))
        self.bind("1", lambda e: self._switch_tab(0))
        self.bind("2", lambda e: self._switch_tab(1))
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.focus_set()

    def _on_viewport_resized(self, width: int, height: int) -> None:
        outer_px = 24 if self.is_compact_2x else self.compute_outer_padx(width)
        for attr in ("_header_frame", "_tab_nav", "scroll_content", "_footer_frame"):
            w = getattr(self, attr, None)
            if w is not None and w.winfo_exists():
                w.configure(padx=outer_px)

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks in ("Escape", "question", "slash", "F1") or ch in ("?", "/"):
            self._on_close()
        elif ks == "Left" or ch == "1":
            self._switch_tab(0)
        elif ks == "Right" or ch == "2":
            self._switch_tab(1)
        elif ks == "Tab":
            self._switch_tab(1 if self.current_tab == 0 else 0)
        return "break"

    def _on_mousewheel(self, event: Any) -> None:
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_scroll_update(self, first: Any, last: Any) -> None:
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack_forget()
        else:
            if not bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event: Any) -> None:
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        cw = max(1, int(self.canvas.winfo_width()))
        ch = max(1, int(self.canvas.winfo_height()))
        target_h = max(ch, int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=cw, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, cw, target_h))

    def _on_canvas_configure(self, event: Any) -> None:
        target_h = max(int(event.height), int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=event.width, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, max(1, int(event.width)), target_h))

    def _build_ui(self) -> None:
        s = self.menu_scale
        compact = self.is_compact_2x
        vw, _ = self._resolve_host_wh()
        outer_px = 24 if compact else self.compute_outer_padx(vw)
        icon_div = 1 if s >= 2 else 2
        title_font = ("BoldPixels", -48 if compact else (-32 * s), "normal")
        hdr_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        btn_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        act_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        hint_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        tip_font = ("Tiny5", -24 if compact else (-16 * s), "normal")

        # 1. Top Full-Width Header Bar
        self._header_frame = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=4 if compact else (8 * s),
        )
        self._header_frame.pack(side="top", fill="x")

        q_icon = self.icon_loader.get_icon("keyboard_question", scale_div=icon_div)
        if q_icon:
            q_lbl = tkinter.Label(self._header_frame, image=q_icon, background=PANEL_BACKGROUND_COLOR)
            q_lbl.image = q_icon
            q_lbl.pack(side="left", padx=(0, 10 * s))

        title_box = tkinter.Frame(self._header_frame, background=PANEL_BACKGROUND_COLOR)
        title_box.pack(side="left")

        tkinter.Label(
            title_box,
            text="KEYBOARD SHORTCUTS & CONTROLS",
            font=title_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="w")

        tkinter.Label(
            title_box,
            text="Full hands-free keyboard & tactile mouse controls for authentic casino gameplay",
            font=hdr_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="w")

        close_btn = tkinter.Button(
            self._header_frame,
            text="✕ Close (Esc)",
            font=btn_font,
            background="#c62828",
            foreground="#ffffff",
            activebackground="#e53935",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            cursor="hand2",
            padx=14 * s,
            pady=4 if compact else (6 * s),
            takefocus=False,
            command=self._on_close,
        )
        close_btn.pack(side="right")

        # 2. Full-Width 50/50 Tab Navigation Bar
        self._tab_nav = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=2 if compact else (4 * s),
        )
        self._tab_nav.pack(side="top", fill="x")
        self._tab_nav.columnconfigure(0, weight=1, uniform="sc_tabs")
        self._tab_nav.columnconfigure(1, weight=1, uniform="sc_tabs")

        self.btn_tab_gameplay = tkinter.Button(
            self._tab_nav,
            text="[1] 🃏 Gameplay & Betting",
            font=btn_font,
            background="#1b5e20",
            fg="#ffd700",
            activebackground="#2e7d32",
            activeforeground="white",
            relief="sunken",
            borderwidth=2,
            cursor="hand2",
            padx=14 * s,
            pady=4 if compact else (6 * s),
            command=lambda: self._switch_tab(0),
        )
        self.btn_tab_gameplay.grid(row=0, column=0, sticky="ew", padx=(0, 6 * s))

        self.btn_tab_system = tkinter.Button(
            self._tab_nav,
            text="[2] ⚙️ System, Trainer & Modes",
            font=btn_font,
            background="#082415",
            fg="#cfd8dc",
            activebackground="#143d26",
            activeforeground="white",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=14 * s,
            pady=4 if compact else (6 * s),
            command=lambda: self._switch_tab(1),
        )
        self.btn_tab_system.grid(row=0, column=1, sticky="ew", padx=(6 * s, 0))

        # 3. Persistent Footer Tip Banner + Return to Table Button
        self._footer_frame = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=4 if compact else (6 * s),
        )
        self._footer_frame.pack(side="bottom", fill="x")

        tkinter.Label(
            self._footer_frame,
            text="💡 Tip: Switch tabs with [◄ / ►] or [1] / [2]. Press [Esc], [?], or [F1] to return to the table.",
            font=tip_font,
            fg="#ffe082",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(side="left", pady=2)

        tkinter.Button(
            self._footer_frame,
            text="✔ Return to Table (Esc)",
            font=btn_font,
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=16 * s,
            pady=4 if compact else (5 * s),
            command=self._on_close,
        ).pack(side="right")

        # 4. Scrollable Canvas Area
        self.canvas = tkinter.Canvas(
            self,
            background=PANEL_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
        )
        self.v_scrollbar = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_content = tkinter.Frame(
            self.canvas,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=3 if compact else (6 * s),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll_update)

        self.scroll_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)

        def make_panel(parent_f: tkinter.Misc, title_text: str) -> tkinter.Frame:
            panel = tkinter.Frame(
                parent_f,
                background="#053612",
                relief="ridge",
                borderwidth=2 * s,
                padx=12 * s,
                pady=4 if compact else (8 * s),
            )
            panel.pack(fill="both", expand=True, pady=2 if compact else (4 * s))
            setattr(panel, "_row_counter", 0)
            tkinter.Label(
                panel,
                text=title_text,
                font=hdr_font,
                fg="#ffeb3b",
                background="#053612",
            ).pack(anchor="w", pady=(0, 2 if compact else 4 * s))
            return panel

        def add_row(parent_panel: tkinter.Misc, icon_names: list[str], action_text: str, hint_text: str = "") -> None:
            r_idx = int(getattr(parent_panel, "_row_counter", 0))
            setattr(parent_panel, "_row_counter", r_idx + 1)
            stripe_bg = "#063d15" if (r_idx % 2 == 0) else "#042e10"
            r = tkinter.Frame(parent_panel, background=stripe_bg, padx=4 * s, pady=1 if compact else 2)
            r.pack(fill="x", pady=1)

            badges = tkinter.Frame(r, background=stripe_bg)
            badges.pack(side="left")

            for i, name in enumerate(icon_names):
                if i > 0:
                    tkinter.Label(
                        badges,
                        text="or",
                        font=("Tiny5", -24 if compact else (-16 * s), "normal"),
                        fg="#80cbc4",
                        background=stripe_bg,
                    ).pack(side="left", padx=2 * s)

                icon = self.icon_loader.get_icon(name, scale_div=icon_div)
                if icon:
                    l = tkinter.Label(badges, image=icon, background=stripe_bg)
                    l.image = icon
                    l.pack(side="left", padx=1 * s)
                else:
                    disp = name.replace("keyboard_", "").replace("mouse_", "").upper()
                    tkinter.Label(
                        badges,
                        text=f"[{disp}]",
                        font=("Tiny5", -24 if compact else (-16 * s), "bold"),
                        background="#ffffff",
                        foreground="#000000",
                        padx=3 * s,
                        pady=1,
                        relief="raised",
                        bd=1,
                    ).pack(side="left", padx=1 * s)

            tkinter.Label(
                r,
                text=action_text,
                font=act_font,
                fg="#fff176",
                background=stripe_bg,
            ).pack(side="left", padx=(8 * s, 6 * s))

            if hint_text:
                tkinter.Label(
                    r,
                    text=hint_text,
                    font=hint_font,
                    fg="#eceff1",
                    background=stripe_bg,
                    anchor="e",
                ).pack(side="right")

        # Tab 0: Gameplay & Betting Content
        self.tab_gameplay = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        grid_gameplay = tkinter.Frame(self.tab_gameplay, background=PANEL_BACKGROUND_COLOR)
        grid_gameplay.pack(fill="both", expand=True)
        grid_gameplay.columnconfigure(0, weight=1, uniform="sc_col")
        grid_gameplay.columnconfigure(1, weight=1, uniform="sc_col")
        grid_gameplay.rowconfigure(0, weight=1)

        left_col_g = tkinter.Frame(grid_gameplay, background=PANEL_BACKGROUND_COLOR)
        left_col_g.grid(row=0, column=0, sticky="nsew", padx=(0, 8 * s))

        panel_actions = make_panel(left_col_g, "🃏 TABLE ACTIONS")
        add_row(panel_actions, ["keyboard_space", "keyboard_enter"], "Deal / Hit / Next", "(Context-sensitive)")
        add_row(panel_actions, ["keyboard_h"], "Hit", "(Draw another card)")
        add_row(panel_actions, ["keyboard_s"], "Stand", "(End turn, dealer plays)")
        add_row(panel_actions, ["keyboard_d"], "Double Down", "(Double bet, draw 1 card)")
        add_row(panel_actions, ["keyboard_p"], "Split Pair", "(Split equal rank cards)")
        add_row(panel_actions, ["keyboard_r"], "Surrender", "(Forfeit half bet before hitting)")

        panel_insurance = make_panel(left_col_g, "🛡 INSURANCE & MOUSE WAGERING")
        add_row(panel_insurance, ["keyboard_y"], "Take Insurance", "(Pays 2:1 on Dealer Ace)")
        add_row(panel_insurance, ["keyboard_n", "keyboard_escape"], "Decline Insurance", "(Skip side bet)")
        add_row(panel_insurance, ["mouse_left"], "Click Chip / Spot", "(Add chip to active bet)")
        add_row(panel_insurance, ["mouse_right"], "Right-Click Spot", "(Remove chip / Clear side bet)")

        right_col_g = tkinter.Frame(grid_gameplay, background=PANEL_BACKGROUND_COLOR)
        right_col_g.grid(row=0, column=1, sticky="nsew", padx=(8 * s, 0))

        panel_betting = make_panel(right_col_g, "💰 CHIPS & WAGERING")
        add_row(panel_betting, ["keyboard_1"], "Bet $5", "(White chip)")
        add_row(panel_betting, ["keyboard_2"], "Bet $25", "(Red chip)")
        add_row(panel_betting, ["keyboard_3"], "Bet $100", "(Green chip)")
        add_row(panel_betting, ["keyboard_4"], "Bet $500", "(Black & Gold chip)")
        add_row(panel_betting, ["keyboard_5"], "Bet $1,000", "(Platinum chip)")
        add_row(panel_betting, ["keyboard_q"], "Perfect Pairs +$5", "(Left spot / 6)")
        add_row(panel_betting, ["keyboard_e"], "21+3 Poker +$5", "(Right spot / 7)")
        add_row(panel_betting, ["keyboard_a"], "All In", "(Wager entire bankroll)")
        add_row(panel_betting, ["keyboard_c"], "Clear Bet", "(Reset bet to $0)")
        add_row(panel_betting, ["keyboard_arrow_left", "keyboard_arrow_right"], "Seat Focus", "(Cycle Seat 1-3 in 3-Seat)")

        # Tab 1: System & Controls Content
        self.tab_system = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        grid_system = tkinter.Frame(self.tab_system, background=PANEL_BACKGROUND_COLOR)
        grid_system.pack(fill="both", expand=True)
        grid_system.columnconfigure(0, weight=1, uniform="sc_col")
        grid_system.columnconfigure(1, weight=1, uniform="sc_col")
        grid_system.rowconfigure(0, weight=1)

        left_col_s = tkinter.Frame(grid_system, background=PANEL_BACKGROUND_COLOR)
        left_col_s.grid(row=0, column=0, sticky="nsew", padx=(0, 8 * s))

        panel_display = make_panel(left_col_s, "🖥 AUDIO & DISPLAY")
        add_row(panel_display, ["keyboard_o", "keyboard_f2"], "Casino Settings", "(Audio, Display & House Rules)")
        add_row(panel_display, ["keyboard_m"], "Toggle Sound", "(Mute / Unmute audio)")
        add_row(panel_display, ["keyboard_f11"], "Toggle Fullscreen", "(F11 or Escape to exit)")

        panel_wardrobe = make_panel(left_col_s, "🎩 WARDROBE & RECORDS")
        add_row(panel_wardrobe, ["keyboard_shift", "keyboard_w"], "Dealer Wardrobe", "(Costumes & customizer)")
        add_row(panel_wardrobe, ["keyboard_shift", "keyboard_h"], "Hall of Fame", "(Trophy shelf & records)")

        right_col_s = tkinter.Frame(grid_system, background=PANEL_BACKGROUND_COLOR)
        right_col_s.grid(row=0, column=1, sticky="nsew", padx=(8 * s, 0))

        panel_trainer = make_panel(right_col_s, "🧮 TRAINER & SUPERNATURAL")
        add_row(panel_trainer, ["keyboard_k", "keyboard_shift", "keyboard_c"], "Card Counter HUD", "(K or Shift+C)")
        add_row(panel_trainer, ["keyboard_t"], "Strategy Tripometer", "(Hand review & grades)")
        add_row(panel_trainer, ["keyboard_shift", "keyboard_t"], "Casino Venue Tour", "(Shift+T - Post-Exorcist)")
        add_row(panel_trainer, ["keyboard_shift", "keyboard_m"], "Cycle Play Mode", "(Casual / Betting / Training)")
        add_row(panel_trainer, ["keyboard_x"], "Miracle Draw", "(Hell's Table relic redraw)")

        panel_help = make_panel(right_col_s, "🖱 ACCESSIBILITY & HELP")
        add_row(panel_help, ["keyboard_question", "keyboard_f1"], "Toggle Help", "(Show / Hide this HUD)")
        add_row(panel_help, ["keyboard_escape"], "Dismiss Screen", "(Close active menu)")
        add_row(panel_help, ["mouse_left"], "Click Button / Chip", "(Direct mouse interaction)")

        self._tab_frames = [self.tab_gameplay, self.tab_system]
        self._switch_tab(0)

    def _switch_tab(self, tab_idx: int) -> None:
        self.current_tab = max(0, min(1, tab_idx))
        if self.current_tab == 0:
            self.tab_system.pack_forget()
            self.tab_gameplay.pack(fill="both", expand=True)
            self.btn_tab_gameplay.configure(background="#1b5e20", fg="#ffd700", relief="sunken", borderwidth=2)
            self.btn_tab_system.configure(background="#082415", fg="#cfd8dc", relief="raised", borderwidth=2)
        else:
            self.tab_gameplay.pack_forget()
            self.tab_system.pack(fill="both", expand=True)
            self.btn_tab_system.configure(background="#1b5e20", fg="#ffd700", relief="sunken", borderwidth=2)
            self.btn_tab_gameplay.configure(background="#082415", fg="#cfd8dc", relief="raised", borderwidth=2)

        self.canvas.yview_moveto(0.0)
        self.scroll_content.update_idletasks()
        cw = max(1, int(self.canvas.winfo_width()))
        ch = max(1, int(self.canvas.winfo_height()))
        target_h = max(ch, int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=cw, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, cw, target_h))

    def _on_close(self, event: Any = None) -> str:
        cb = self.on_close_cb
        try:
            self.destroy()
        except Exception:
            pass
        if cb:
            cb()
        return "break"


# ============================================================================
# 5. WelcomeSplashDialog (Full-Screen 3-Column Play Mode Showcase)
# ============================================================================

class WelcomeSplashDialog(InWindowScreenHost):
    """
    Full-screen widescreen onboarding splash and play-mode selector.
    Arranges the 3 Play Modes ([1] Casual, [2] Betting, [3] Strategy & Counting Trainer)
    side-by-side in 3 equal columns beneath a full-width retro logo + croupier banner,
    utilizing 100% of the 1280x800 / 1280x720 viewport with zero vertical scrolling.
    """

    _MODE_ORDER = ("casual", "betting", "training")

    def __init__(
        self,
        parent: tkinter.Tk | tkinter.Misc,
        app: Any,
        on_confirm: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(
            parent,
            app=app,
            profile=getattr(app, "display_profile", None),
            background=PANEL_BACKGROUND_COLOR,
            base_pad=22,
        )
        self.app = app
        self.on_confirm_cb = on_confirm
        self.title("Welcome to Blackjack!")

        current_pref = (
            getattr(app.save_manager.data, "play_mode", "betting")
            if hasattr(app, "save_manager")
            else "betting"
        )
        self.selected_mode = current_pref if current_pref in self._MODE_ORDER else "betting"
        self.remember_var = tkinter.BooleanVar(value=True)
        self._mode_cards: dict[str, dict[str, Any]] = {}

        self._build_chrome_and_content()

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.bind("1", lambda e: self._select_mode("casual"))
        self.bind("2", lambda e: self._select_mode("betting"))
        self.bind("3", lambda e: self._select_mode("training"))
        self.bind("<Left>", lambda e: self._cycle_mode(-1))
        self.bind("<Right>", lambda e: self._cycle_mode(1))
        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<space>", lambda e: self._on_confirm())
        self.bind("r", lambda e: self.remember_var.set(not self.remember_var.get()))
        self.bind("R", lambda e: self.remember_var.set(not self.remember_var.get()))
        self.bind("<Escape>", lambda e: self._on_close())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.focus_set()

    def _build_chrome_and_content(self) -> None:
        for child in self.winfo_children():
            child.destroy()

        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        outer_px = 24 if compact else self.compute_outer_padx(vw)
        tight_720 = (s == 1 and vh < 760)
        btn_font = ("Tiny5", -24 if compact else (-24 if s == 1 else -32), "bold")
        chk_font = ("Tiny5", -24 if compact else (-16 * s), "normal")

        # Persistent Bottom Footer Bar
        self._footer_bar = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=5 if compact else (8 * s if tight_720 else 10 * s),
        )
        self._footer_bar.pack(side="bottom", fill="x")

        remember_chk = tkinter.Checkbutton(
            self._footer_bar,
            text="Remember my preference [R] (don't show again on startup; reopen anytime in Settings)",
            variable=self.remember_var,
            font=chk_font,
            fg="#cfd8dc",
            background=PANEL_BACKGROUND_COLOR,
            selectcolor="#004d40",
            activebackground=PANEL_BACKGROUND_COLOR,
            activeforeground="#ffffff",
            cursor="hand2",
        )
        remember_chk.pack(pady=(0, 4 if compact else 6 * s))

        action_row = tkinter.Frame(self._footer_bar, background=PANEL_BACKGROUND_COLOR)
        action_row.pack(fill="x")
        action_row.columnconfigure(0, weight=2, uniform="welcome_actions")
        action_row.columnconfigure(1, weight=1, uniform="welcome_actions")

        self.confirm_btn = tkinter.Button(
            action_row,
            text="▶ Take My Seat & Play (Enter)",
            font=btn_font,
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            command=self._on_confirm,
            padx=20 * s,
            pady=5 if compact else (8 * s),
        )
        self.confirm_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8 * s))

        self.cancel_btn = tkinter.Button(
            action_row,
            text="Skip (Keep Current Settings) [Esc]",
            font=btn_font,
            background="#37474f",
            fg="#cfd8dc",
            activebackground="#455a64",
            activeforeground="#ffffff",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_close,
            padx=14 * s,
            pady=5 if compact else (8 * s),
        )
        self.cancel_btn.grid(row=0, column=1, sticky="ew", padx=(8 * s, 0))

        # Adaptive Scrollable Main Body
        self.canvas = tkinter.Canvas(
            self,
            background=PANEL_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
        )
        self.v_scrollbar = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_content = tkinter.Frame(
            self.canvas,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=6 if compact else (8 * s if tight_720 else 12 * s),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll_update)

        self.scroll_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)

        self._build_ui()

    def _on_viewport_resized(self, width: int, height: int) -> None:
        outer_px = 24 if self.is_compact_2x else self.compute_outer_padx(width)
        if hasattr(self, "_footer_bar") and self._footer_bar.winfo_exists():
            self._footer_bar.configure(padx=outer_px)
        if hasattr(self, "scroll_content") and self.scroll_content.winfo_exists():
            self.scroll_content.configure(padx=outer_px)

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape":
            self._on_close()
        elif ks in ("Return", "KP_Enter", "space"):
            self._on_confirm()
        elif ks == "Left":
            self._cycle_mode(-1)
        elif ks == "Right":
            self._cycle_mode(1)
        elif ch.lower() == "r" or ks in ("r", "R"):
            self.remember_var.set(not self.remember_var.get())
        elif ch == "1":
            self._select_mode("casual")
        elif ch == "2":
            self._select_mode("betting")
        elif ch == "3":
            self._select_mode("training")
        return "break"

    def _cycle_mode(self, delta: int) -> str:
        try:
            idx = self._MODE_ORDER.index(self.selected_mode)
        except ValueError:
            idx = 1
        self._select_mode(self._MODE_ORDER[(idx + delta) % len(self._MODE_ORDER)])
        return "break"

    def _on_scroll_update(self, first: Any, last: Any) -> None:
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack_forget()
        else:
            if not bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event: Any) -> None:
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        cw = max(1, int(self.canvas.winfo_width()))
        ch = max(1, int(self.canvas.winfo_height()))
        target_h = max(ch, int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=cw, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, cw, target_h))

    def _on_canvas_configure(self, event: Any) -> None:
        target_h = max(int(event.height), int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=event.width, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, max(1, int(event.width)), target_h))

    def _on_mousewheel(self, event: Any) -> None:
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_ui(self) -> None:
        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        tight_720 = (s == 1 and vh < 760)
        outer_px = 24 if compact else self.compute_outer_padx(vw)
        avail_w = max(800, vw - 2 * outer_px)
        hdr_font = ("Tiny5", -24 if compact else (-24 if s == 1 else -32), "bold")
        bullet_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        pill_font = ("Tiny5", -24 if compact else (-16 * s), "bold")

        # 1. Full-Width Top Hero Band: Retro Logo (Left) + Croupier Greeting Plaque (Right)
        hero_row = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        hero_row.pack(fill="x", pady=(0, 6 if compact else 10 * s))

        logo_file = "pixel_logo_blackjack_2x.png" if s >= 2 else "pixel_logo_blackjack.png"
        logo_path = ASSETS_EXTRA_DIR / logo_file
        if not logo_path.exists():
            logo_path = ASSETS_EXTRA_DIR / "pixel_logo_blackjack.png"

        self._logo_photo = None
        if logo_path.exists() and Image is not None and ImageTk is not None:
            try:
                pil_logo = Image.open(logo_path)
                self._logo_photo = ImageTk.PhotoImage(pil_logo, master=self)
                logo_lbl = tkinter.Label(
                    hero_row,
                    image=self._logo_photo,
                    background=PANEL_BACKGROUND_COLOR,
                )
                logo_lbl.pack(side="left", padx=(0, 16 * s))
            except Exception:
                self._logo_photo = None

        if self._logo_photo is None:
            tkinter.Label(
                hero_row,
                text="♠  B L A C K J A C K  ♥",
                font=get_element_font("dialog_title", scale=float(s)),
                fg="#ffd700",
                background=PANEL_BACKGROUND_COLOR,
            ).pack(side="left", padx=(0, 16 * s))

        dealer_photo = None
        dealer_name = "Tiffany"
        dealer_title = "The Velvet Croupier"
        if hasattr(self.app, "dealer_actor") and self.app.dealer_actor:
            try:
                profile = self.app.dealer_actor.get_profile()
                if profile:
                    dealer_name = profile.name
                    dealer_title = profile.title
                dealer_photo = self.app.dealer_actor.get_bust_photo_image(scale_factor=float(s))
            except Exception:
                pass
        if dealer_photo is None and hasattr(self.app, "haunted_assets"):
            dealer_photo = self.app.haunted_assets.get("dealer_classic")

        dealer_banner = tkinter.Frame(
            hero_row,
            background="#072b17",
            relief="ridge",
            borderwidth=1 * s,
            highlightbackground="#ffd700",
            highlightthickness=1 * s,
            padx=14 * s,
            pady=10 * s,
        )
        dealer_banner.pack(side="left", fill="both", expand=True)

        if dealer_photo:
            self._dealer_photo_ref = dealer_photo
            avatar_lbl = tkinter.Label(dealer_banner, image=dealer_photo, background="#072b17")
            avatar_lbl.pack(side="left", padx=(2 * s, 12 * s), pady=2 * s)

        text_box = tkinter.Frame(dealer_banner, background="#072b17")
        text_box.pack(side="left", fill="both", expand=True)

        tkinter.Label(
            text_box,
            text=f"♠ {dealer_name} — {dealer_title}",
            font=hdr_font,
            fg="#ffd700",
            background="#072b17",
            anchor="w",
        ).pack(anchor="w", pady=(0, 4))

        speech_lbl = tkinter.Label(
            text_box,
            text=(
                "Welcome to the salon! Choose your table experience below with [1], [2], [3] or [◄ / ►] — "
                "you can switch modes anytime in Settings (O / F2) or with Shift+M."
            ),
            font=bullet_font,
            fg="#e0f2f1",
            background="#072b17",
            justify="left",
            anchor="w",
            wraplength=max(320, avail_w - 620 * s),
        )
        speech_lbl.pack(fill="x", anchor="w")

        def _on_text_box_cfg(ev: Any) -> None:
            if ev.width > 160:
                speech_lbl.configure(wraplength=max(240, ev.width - 12 * s))

        text_box.bind("<Configure>", _on_text_box_cfg)

        # 2. Widescreen 3-Column Play Mode Deck
        modes_grid = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        modes_grid.pack(fill="both", expand=True, pady=(2 * s, 4 * s))
        for col in range(3):
            modes_grid.columnconfigure(col, weight=1, uniform="welcome_mode_cols")
        modes_grid.rowconfigure(0, weight=1)

        col_wrap = max(220, (avail_w - 48 * s) // 3 - 48 * s)

        modes_spec = [
            (
                "casual",
                "1",
                "🃏 Casual Mode",
                "Pure card play & zero bankroll stress",
                [
                    "• Deal hands immediately with zero bankroll pressure or chip staging",
                    "• Full casino Blackjack rules: Hit, Stand, Double, Split & Late Surrender",
                    "• Tracks session Win / Loss / Tie counters without financial risk",
                    "• Ideal for relaxing warm-up hands and learning core card flow",
                ],
                "#10b981",
            ),
            (
                "betting",
                "2",
                "💰 Casino Betting",
                "Authentic bankroll stakes & Hall of Fame",
                [
                    "• Start with a $1,000 bankroll across 5 tactile casino chip denominations",
                    "• Interactive 2.5D chip stacks, Perfect Pairs & 21+3 poker side bets",
                    "• Unlock Dealer Costumes, Hall of Fame trophies & the 8-Salon Venue Tour",
                    "• Optional Cursed Stakes & Pit Fiend boss encounters",
                ],
                "#f59e0b",
            ),
            (
                "training",
                "3",
                "🧠 Strategy Trainer",
                "MIT Hi-Lo Bootcamp + 3-Seat Advantage Play",
                [
                    "• Interactive 14-Node MIT Hi-Lo Counting Bootcamp (Lectures & Timed Drills)",
                    "• Full 3-Seat crescent baize for multi-hand True Count bet spreading",
                    "• Live Hi-Lo Running Count, True Count, Kelly Bet Guide & Strategy Slate",
                    "• Continuous Basic Strategy & Illustrious 18 grading in the Tripometer",
                ],
                "#00e5ff",
            ),
        ]

        self._mode_cards.clear()
        for col_idx, (mode_id, key_str, title_text, subtitle_text, bullets, accent_col) in enumerate(modes_spec):
            pad_l = 0 if col_idx == 0 else 6 * s
            pad_r = 0 if col_idx == 2 else 6 * s
            card_f = tkinter.Frame(
                modes_grid,
                background="#081f14",
                relief="ridge",
                borderwidth=2 * s,
                highlightthickness=2 * s,
                highlightbackground="#1a402d",
                padx=16 * s,
                pady=14 * s,
                cursor="hand2",
            )
            card_f.grid(row=0, column=col_idx, sticky="nsew", padx=(pad_l, pad_r), pady=2 * s)

            hdr_row = tkinter.Frame(card_f, background="#081f14", cursor="hand2")
            hdr_row.pack(fill="x", pady=(0, 6 * s))

            key_lbl = tkinter.Label(
                hdr_row,
                text=f"[{key_str}]",
                font=pill_font,
                fg="#b0bec5",
                background="#1b382b",
                padx=8 * s,
                pady=2,
                relief="ridge",
                borderwidth=1,
            )
            key_lbl.pack(side="left", padx=(0, 8 * s))

            title_lbl = tkinter.Label(
                hdr_row,
                text=title_text,
                font=hdr_font,
                fg=accent_col,
                background="#081f14",
                cursor="hand2",
            )
            title_lbl.pack(side="left")

            sub_lbl = tkinter.Label(
                card_f,
                text=subtitle_text,
                font=pill_font,
                fg="#b2dfdb",
                background="#081f14",
                anchor="w",
                justify="left",
                wraplength=col_wrap,
                cursor="hand2",
            )
            sub_lbl.pack(fill="x", pady=(0, 6 if compact else 8 * s))

            sep = tkinter.Frame(card_f, background="#1a402d", height=max(1, s))
            sep.pack(fill="x", pady=(0, 6 if compact else 8 * s))

            bullet_labels: list[tkinter.Label] = []
            for bp in bullets:
                b_lbl = tkinter.Label(
                    card_f,
                    text=bp,
                    font=bullet_font,
                    fg="#cfd8dc",
                    background="#081f14",
                    anchor="w",
                    justify="left",
                    wraplength=col_wrap,
                    cursor="hand2",
                )
                b_lbl.pack(fill="x", pady=2 if (compact or tight_720) else 4 * s)
                bullet_labels.append(b_lbl)

            badge_lbl = tkinter.Label(
                card_f,
                text=f"Press [{key_str}] or Click",
                font=pill_font,
                fg="#90a4ae",
                background="#05160e",
                relief="ridge",
                borderwidth=1,
                pady=4 if compact else 6 * s,
                cursor="hand2",
            )
            badge_lbl.pack(side="bottom", fill="x", pady=(8 * s, 0))

            def _on_card_cfg(ev: Any, sub_w: tkinter.Label = sub_lbl, b_list: list[tkinter.Label] = bullet_labels) -> None:
                if ev.width > 140:
                    w_px = max(180, ev.width - 48 * s)
                    sub_w.configure(wraplength=w_px)
                    for bl in b_list:
                        bl.configure(wraplength=w_px)

            card_f.bind("<Configure>", _on_card_cfg)

            sync_widgets = [hdr_row, title_lbl, sub_lbl] + bullet_labels
            self._mode_cards[mode_id] = {
                "frame": card_f,
                "badge": badge_lbl,
                "key_btn": key_lbl,
                "accent": accent_col,
                "key": key_str,
                "sync_widgets": sync_widgets,
            }

            def _on_card_click(_e: Any, m: str = mode_id) -> None:
                if self.selected_mode == m:
                    self._on_confirm()
                else:
                    self._select_mode(m)

            for w in [card_f, hdr_row, key_lbl, title_lbl, badge_lbl, sub_lbl] + bullet_labels:
                w.bind("<Button-1>", _on_card_click)

        self._select_mode(self.selected_mode)

    def _select_mode(self, mode: str) -> None:
        if mode not in self._mode_cards:
            return
        s = self.menu_scale
        compact = self.is_compact_2x
        pill_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        self.selected_mode = mode
        for m_id, card in self._mode_cards.items():
            is_sel = m_id == mode
            bg_col = "#0f3826" if is_sel else "#081f14"
            border_col = card["accent"] if is_sel else "#1a402d"
            card["frame"].configure(background=bg_col, highlightbackground=border_col)
            for w in card["sync_widgets"]:
                w.configure(background=bg_col)
            if is_sel:
                card["badge"].configure(
                    text="✓ SELECTED — CLICK OR ENTER TO PLAY",
                    fg="#00e676",
                    background="#09291b",
                    font=pill_font,
                )
                card["key_btn"].configure(background=card["accent"], fg="#141008")
            else:
                card["badge"].configure(
                    text=f"Press [{card['key']}] or Click",
                    fg="#90a4ae",
                    background="#05160e",
                    font=pill_font,
                )
                card["key_btn"].configure(background="#1b382b", fg="#b0bec5")

    def _on_confirm(self) -> str:
        mode = self.selected_mode
        if self.remember_var.get():
            if hasattr(self.app, "save_manager") and self.app.save_manager:
                self.app.save_manager.complete_onboarding()
        if mode == "training" and hasattr(self.app, "activate_training_mode_entry"):
            self._on_close()
            self.app.activate_training_mode_entry(sync_save=True)
            return "break"
        if hasattr(self.app, "set_table_seats"):
            self.app.set_table_seats(3 if mode == "training" else 1)
        if hasattr(self.app, "apply_play_mode"):
            self.app.apply_play_mode(mode)
        if self.on_confirm_cb:
            try:
                self.on_confirm_cb(mode)
            except Exception:
                pass
        self._on_close()
        return "break"

    def _on_close(self, event: Any = None) -> str:
        if hasattr(self.app, "_welcome_splash_dialog") and getattr(self.app, "_welcome_splash_dialog", None) is self:
            self.app._welcome_splash_dialog = None
        try:
            self.destroy()
        except Exception:
            pass
        return "break"


# ============================================================================
# 7. TripometerDialog (Full-Screen Strategy Tripometer & 50-Hand Audit Log)
# ============================================================================

class TripometerDialog(InWindowScreenHost):
    """
    Full-screen Strategy Tripometer & Hand Review dashboard.
    Expands the summary strip, 3 skill grade plaques, filter bar, and 50-hand
    rolling audit log across the full viewport width with dynamic coaching wraplength.
    """

    _OUTCOME_LABELS: dict[str, tuple[str, str]] = {
        "NATURAL_BLACKJACK": ("BLACKJACK", "#ffd700"),
        "BLACKJACK": ("BLACKJACK", "#ffd700"),
        "PLAYER_WINS": ("WIN", "#69f0ae"),
        "WIN": ("WIN", "#69f0ae"),
        "DEALER_WINS": ("LOSS", "#ff8a80"),
        "LOSS": ("LOSS", "#ff8a80"),
        "BUST": ("BUST", "#ff8a80"),
        "PLAYER_BUST": ("BUST", "#ff8a80"),
        "PUSH": ("PUSH", "#cfd8dc"),
        "TIE": ("PUSH", "#cfd8dc"),
        "SURRENDER": ("SURRENDER", "#ffb74d"),
    }

    def __init__(self, parent: tkinter.Misc, app: Any) -> None:
        super().__init__(
            parent,
            app=app,
            profile=getattr(app, "display_profile", None),
            background=PANEL_BACKGROUND_COLOR,
            base_pad=22,
        )
        self.app = app
        self.filter_mode: str = "all"
        self.current_page: int = 0
        self.page_size: int = 3
        self.total_pages: int = 1
        self.total_filtered_hands: int = 0
        self._rendered_hand_frames: list[tkinter.Frame] = []
        self._step_wrap_labels: list[tkinter.Label] = []

        self.title("Strategy Tripometer & Hand Review")

        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        tight_720 = (s == 1 and vh < 760)
        outer_px = 24 if compact else self.compute_outer_padx(vw)
        title_font = ("BoldPixels", -48 if compact else (-32 * s), "normal")
        sub_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        foot_btn_font = ("Tiny5", -24 if compact else (-24 if s == 1 else -32), "bold")

        self._header_bar = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=3 if compact else (5 * s),
        )
        self._header_bar.pack(side="top", fill="x")

        tkinter.Label(
            self._header_bar,
            text="STRATEGY TRIPOMETER & HAND REVIEW",
            font=title_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="center")

        self.subtitle_lbl = tkinter.Label(
            self._header_bar,
            text="",
            font=sub_font,
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
        )
        self.subtitle_lbl.pack(anchor="center", pady=(1, 0))

        self._footer_row = tkinter.Frame(
            self,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=4 if compact else (6 * s),
        )
        self._footer_row.pack(side="bottom", fill="x")
        self._footer_row.columnconfigure(0, weight=2)
        self._footer_row.columnconfigure(1, weight=1)

        self.done_btn = tkinter.Button(
            self._footer_row,
            text="✔ Done (Esc)",
            font=foot_btn_font,
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=16 * s,
            pady=4 if compact else (5 * s),
            command=self._on_close,
        )
        self.done_btn.grid(row=0, column=0, sticky="ew", padx=(0, 8 * s))

        self.reset_trip_btn = tkinter.Button(
            self._footer_row,
            text="🗑 Reset Trip Stats",
            font=foot_btn_font,
            background="#b71c1c",
            fg="#ffffff",
            activebackground="#d32f2f",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=16 * s,
            pady=4 if compact else (5 * s),
            command=self._on_click_reset_trip,
        )
        self.reset_trip_btn.grid(row=0, column=1, sticky="ew", padx=(8 * s, 0))

        self.canvas = tkinter.Canvas(
            self,
            background=PANEL_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
            height=220 * s,
        )
        self.v_scrollbar = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_content = tkinter.Frame(
            self.canvas,
            background=PANEL_BACKGROUND_COLOR,
            padx=outer_px,
            pady=2 if compact else (4 * s),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scroll_content, anchor="nw")
        self.canvas.configure(yscrollcommand=self._on_scroll_update)

        self.scroll_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.bind("1", lambda e: self._set_filter_mode("all"))
        self.bind("2", lambda e: self._set_filter_mode("mistakes"))
        self.bind("<Left>", lambda e: self._prev_page())
        self.bind("<Right>", lambda e: self._next_page())
        self.bind("<Prior>", lambda e: self._prev_page())
        self.bind("<Next>", lambda e: self._next_page())
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        self._render_tripometer_contents()
        self.focus_set()

    def _resolve_trip_page_size(self, vh: int) -> int:
        if self.is_compact_2x:
            return 3
        if self.menu_scale >= 2:
            return 4 if vh >= 1360 else 3
        return 4 if vh >= 780 else 3

    def _on_viewport_resized(self, width: int, height: int) -> None:
        outer_px = 24 if self.is_compact_2x else self.compute_outer_padx(width)
        for attr in ("_header_bar", "_footer_row", "scroll_content"):
            w = getattr(self, attr, None)
            if w is not None and w.winfo_exists():
                w.configure(padx=outer_px)
        new_ps = self._resolve_trip_page_size(height)
        if hasattr(self, "scroll_content") and new_ps != getattr(self, "page_size", 3):
            self._render_tripometer_contents()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        confirm_key = getattr(self, "_active_confirm_key", None)
        if callable(confirm_key):
            return confirm_key(event)
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape":
            self._on_close()
        elif ks in ("Left", "Prior"):
            self._prev_page()
        elif ks in ("Right", "Next"):
            self._next_page()
        elif ch == "1":
            self._set_filter_mode("all")
        elif ch == "2":
            self._set_filter_mode("mistakes")
        return "break"

    def _prev_page(self) -> str:
        if self.current_page > 0:
            self.current_page -= 1
            self.canvas.yview_moveto(0.0)
            self._render_tripometer_contents()
        return "break"

    def _next_page(self) -> str:
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.canvas.yview_moveto(0.0)
            self._render_tripometer_contents()
        return "break"

    def _on_scroll_update(self, first: Any, last: Any) -> None:
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack_forget()
        else:
            if not bool(self.v_scrollbar.winfo_manager()):
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event: Any) -> None:
        if not hasattr(self, "canvas") or not self.canvas.winfo_exists():
            return
        cw = max(1, int(self.canvas.winfo_width()))
        ch = max(1, int(self.canvas.winfo_height()))
        target_h = max(ch, int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=cw, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, cw, target_h))

    def _on_canvas_configure(self, event: Any) -> None:
        target_h = max(int(event.height), int(self.scroll_content.winfo_reqheight()))
        self.canvas.itemconfig(self.canvas_window, width=event.width, height=target_h)
        self.canvas.configure(scrollregion=(0, 0, max(1, int(event.width)), target_h))
        s = self.menu_scale
        outer_px = 24 if self.is_compact_2x else self.compute_outer_padx(event.width)
        target_wrap = max(480, int(event.width) - 2 * outer_px - 36 * s)
        for lbl in getattr(self, "_step_wrap_labels", ()):
            if lbl.winfo_exists():
                lbl.configure(wraplength=target_wrap)

    def _on_mousewheel(self, event: Any) -> None:
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _bind_mousewheel_recursive(self, widget: tkinter.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_mousewheel)
        widget.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _set_filter_mode(self, mode: str) -> None:
        if mode in ("all", "mistakes") and mode != self.filter_mode:
            self.filter_mode = mode
            self.current_page = 0
            self.canvas.yview_moveto(0.0)
            self._render_tripometer_contents()

    @classmethod
    def _format_outcome_badge(cls, raw_outcome: str, net_profit: int) -> tuple[str, str]:
        clean_key = str(raw_outcome or "").strip().upper()
        human, base_col = cls._OUTCOME_LABELS.get(clean_key, (clean_key.replace("_", " ") or "HAND", "#cfd8dc"))
        pnl_str = (
            f"+${net_profit:,}"
            if net_profit > 0
            else (f"-${abs(net_profit):,}" if net_profit < 0 else "$0")
        )
        return f"{human}  {pnl_str}", base_col

    @staticmethod
    def _grade_letter_and_color(pct: Optional[float]) -> tuple[str, str]:
        if pct is None:
            return "N/A", "#90a4ae"
        if pct >= 98.0:
            return "S", "#00e676"
        if pct >= 90.0:
            return "A", "#69f0ae"
        if pct >= 80.0:
            return "B", "#81c784"
        if pct >= 70.0:
            return "C", "#ffd54f"
        if pct >= 60.0:
            return "D", "#ffb74d"
        return "F", "#ff8a80"

    @staticmethod
    def _format_cards_with_total(cards: list[str]) -> str:
        if not cards:
            return "-"
        total = 0
        aces = 0
        for raw in cards:
            rk = str(raw).strip().rstrip("♠♥♦♣SHDCshdc").strip().upper()
            if rk in ("A", "ACE"):
                total += 11
                aces += 1
            elif rk in ("J", "Q", "K", "JACK", "QUEEN", "KING"):
                total += 10
            else:
                try:
                    total += int(rk)
                except ValueError:
                    pass
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        joined = " ".join(cards)
        return f"[ {joined} ] ({total})" if total > 0 else f"[ {joined} ]"

    def _render_tripometer_contents(self) -> None:
        for child in self.scroll_content.winfo_children():
            child.destroy()
        self._rendered_hand_frames = []
        self._step_wrap_labels = []

        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        tight_720 = (s == 1 and vh < 760)
        outer_px = 24 if compact else self.compute_outer_padx(vw)
        init_wrap = max(560, vw - 2 * outer_px - 36 * s)
        row_hdr_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        row_step_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        btn_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        disp_font = ("Round9x13", -48 if compact else (-32 * s), "normal")

        tracker = getattr(self.app, "tripometer", None)
        summary = tracker.get_summary() if tracker is not None else {
            "hands_recorded": 0,
            "rounds_recorded": 0,
            "trip_net_profit": 0,
            "bs_optimal": 0,
            "bs_total": 0,
            "bs_pct": None,
            "i18_optimal": 0,
            "i18_opportunities": 0,
            "i18_pct": None,
            "kelly_optimal": 0,
            "kelly_total": 0,
            "kelly_pct": None,
        }
        rules = getattr(self.app, "house_rules", HouseRules())
        min_str = f"${rules.minimum_bet:,}"
        max_str = f"${rules.maximum_bet:,}" if rules.maximum_bet > 0 else "No Limit"
        self.subtitle_lbl.configure(
            text=f"Active Table: {rules.short_badge()}   |   Limits: {min_str} - {max_str}"
        )

        # 1. Trip Summary Strip
        top_strip = tkinter.Frame(
            self.scroll_content,
            background="#082415",
            highlightbackground="#d4af37",
            highlightthickness=1 * s,
            padx=14 * s,
            pady=4 if compact else (5 * s),
        )
        top_strip.pack(fill="x", pady=(0, 4 if compact else 6 * s))
        top_strip.columnconfigure(0, weight=1)
        top_strip.columnconfigure(1, weight=1)

        hands_cnt = summary["hands_recorded"]
        rounds_cnt = summary["rounds_recorded"]
        pnl = summary["trip_net_profit"]
        pnl_str = f"+${pnl:,}" if pnl > 0 else (f"-${abs(pnl):,}" if pnl < 0 else "$0")
        pnl_col = "#69f0ae" if pnl > 0 else ("#ff8a80" if pnl < 0 else "#cfd8dc")

        tkinter.Label(
            top_strip,
            text=f"Hands Graded: {hands_cnt:,}  ({rounds_cnt:,} rounds)",
            font=row_hdr_font,
            fg="#ffffff",
            background="#082415",
        ).grid(row=0, column=0, sticky="w")

        tkinter.Label(
            top_strip,
            text=f"Net Trip P&L: {pnl_str}",
            font=row_hdr_font,
            fg=pnl_col,
            background="#082415",
        ).grid(row=0, column=1, sticky="e")

        # 2. Three Wide Skill Grade Plaques
        plaques_row = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        plaques_row.pack(fill="x", pady=(0, 4 if compact else 6 * s))
        for col in range(3):
            plaques_row.columnconfigure(col, weight=1, uniform="trip_plaques")

        plaque_specs = [
            ("BASIC STRATEGY", summary["bs_pct"], summary["bs_optimal"], summary["bs_total"], "decisions"),
            ("ILLUSTRIOUS 18", summary["i18_pct"], summary["i18_optimal"], summary["i18_opportunities"], "index spots"),
            ("KELLY BET SIZING", summary["kelly_pct"], summary["kelly_optimal"], summary["kelly_total"], "rounds"),
        ]
        chip_scale = (1.5 if compact else (1.22 * s))
        chip_w = int(108 if compact else (88 * s))
        chip_h = int(70 if compact else (58 * s))
        chip_cx = int(52 if compact else (42 * s))
        chip_cy = int(30 if compact else (24 * s))
        for idx, (title, pct, opt, tot, unit_lbl) in enumerate(plaque_specs):
            letter, col_hex = self._grade_letter_and_color(pct)
            border_hex = "#d4af37" if letter in ("S", "A") else col_hex
            pad_l = 0 if idx == 0 else 6 * s
            pad_r = 0 if idx == 2 else 6 * s
            card = tkinter.Frame(
                plaques_row,
                background="#0b2919",
                highlightbackground=border_hex,
                highlightthickness=1 * s,
                padx=10 * s,
                pady=3 if compact else (5 * s),
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=(pad_l, pad_r))

            tkinter.Label(
                card,
                text=title,
                font=row_hdr_font,
                fg="#ffd700",
                background="#0b2919",
            ).pack(anchor="center")

            hero_row = tkinter.Frame(card, background="#0b2919")
            hero_row.pack(anchor="center", pady=(2, 1))

            chip_canvas = tkinter.Canvas(
                hero_row,
                width=chip_w,
                height=chip_h,
                background="#0b2919",
                highlightthickness=0,
                borderwidth=0,
            )
            chip_canvas.pack(side="left", padx=(0, 8 * s))
            draw_25d_grade_medallion(
                chip_canvas,
                x=chip_cx,
                y=chip_cy,
                grade=letter,
                scale=chip_scale,
            )

            pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
            tkinter.Label(
                hero_row,
                text=pct_str,
                font=disp_font,
                fg=col_hex,
                background="#0b2919",
            ).pack(side="left")

            sub_str = f"{opt:,} / {tot:,} {unit_lbl}" if tot > 0 else f"0 {unit_lbl}"
            tkinter.Label(
                card,
                text=sub_str,
                font=row_step_font,
                fg="#cfd8dc",
                background="#0b2919",
            ).pack(anchor="center")

        # 3. Audit Log Header + Filter + Page Controls
        recent_hands = list(tracker.data.recent_hands) if tracker is not None else []
        mistake_hands = [r for r in recent_hands if r.has_mistake]
        is_all = self.filter_mode == "all"
        displayed_hands = recent_hands if is_all else mistake_hands

        self.page_size = self._resolve_trip_page_size(vh)
        self.total_filtered_hands = len(displayed_hands)
        self.total_pages = max(1, (self.total_filtered_hands + self.page_size - 1) // self.page_size)
        self.current_page = max(0, min(self.total_pages - 1, self.current_page))
        start_idx = self.current_page * self.page_size
        page_hands = displayed_hands[start_idx : start_idx + self.page_size]

        filter_bar = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        filter_bar.pack(fill="x", pady=(0, 4 if compact else 5 * s))
        filter_bar.columnconfigure(0, weight=1)

        tkinter.Label(
            filter_bar,
            text="RECENT 50-HAND AUDIT LOG",
            font=row_hdr_font,
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).grid(row=0, column=0, sticky="w")

        btn_strip = tkinter.Frame(filter_bar, background=PANEL_BACKGROUND_COLOR)
        btn_strip.grid(row=0, column=1, sticky="e")

        self.filter_all_btn = tkinter.Button(
            btn_strip,
            text=f"[1] All Hands ({len(recent_hands)})",
            font=btn_font,
            background="#1b5e20" if is_all else "#0b2919",
            fg="#ffd700" if is_all else "#cfd8dc",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            relief="sunken" if is_all else "ridge",
            borderwidth=1,
            cursor="hand2",
            padx=10 * s,
            pady=2 if compact else 3 * s,
            command=lambda: self._set_filter_mode("all"),
        )
        self.filter_all_btn.grid(row=0, column=0, padx=(0, 6 * s))

        has_err = len(mistake_hands) > 0
        self.filter_mistakes_btn = tkinter.Button(
            btn_strip,
            text=f"[2] Mistakes Only ({len(mistake_hands)})",
            font=btn_font,
            background="#7f1d1d" if not is_all else ("#261414" if has_err else "#0b2919"),
            fg="#ffd54f" if (not is_all or has_err) else "#cfd8dc",
            activebackground="#991b1b",
            activeforeground="#ffffff",
            relief="sunken" if not is_all else "ridge",
            borderwidth=1,
            cursor="hand2",
            padx=10 * s,
            pady=2 if compact else 3 * s,
            command=lambda: self._set_filter_mode("mistakes"),
        )
        self.filter_mistakes_btn.grid(row=0, column=1, padx=(0, 10 * s))

        can_prev = self.current_page > 0
        can_next = self.current_page < self.total_pages - 1

        self.prev_page_btn = tkinter.Button(
            btn_strip,
            text="◀ Previous [◄]",
            font=btn_font,
            background="#004d40" if can_prev else "#081f13",
            fg="#ffffff" if can_prev else "#607d8b",
            activebackground="#00695c",
            activeforeground="#ffffff",
            state="normal" if can_prev else "disabled",
            relief="ridge",
            borderwidth=1,
            cursor="hand2" if can_prev else "arrow",
            padx=14 * s,
            pady=2 if compact else 3 * s,
            command=self._prev_page,
        )
        self.prev_page_btn.grid(row=0, column=2, padx=(0, 6 * s))

        self.page_status_lbl = tkinter.Label(
            btn_strip,
            text=f"Page {self.current_page + 1} / {self.total_pages}",
            font=row_hdr_font,
            fg="#ffd54f",
            background=PANEL_BACKGROUND_COLOR,
            padx=6 * s,
        )
        self.page_status_lbl.grid(row=0, column=3)

        self.next_page_btn = tkinter.Button(
            btn_strip,
            text="Next Page [►] ▶",
            font=btn_font,
            background="#004d40" if can_next else "#081f13",
            fg="#ffffff" if can_next else "#607d8b",
            activebackground="#00695c",
            activeforeground="#ffffff",
            state="normal" if can_next else "disabled",
            relief="ridge",
            borderwidth=1,
            cursor="hand2" if can_next else "arrow",
            padx=14 * s,
            pady=2 if compact else 3 * s,
            command=self._next_page,
        )
        self.next_page_btn.grid(row=0, column=4, padx=(6 * s, 0))

        # 4. Paginated Rolling Audit Cards (3–4 hands per page, zero scroll across 720p/800p/1080p/1440p)
        audit_box = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        audit_box.pack(fill="x", pady=(0, 2))
        self.hands_list_frame = audit_box

        if not recent_hands:
            empty_card = tkinter.Frame(
                audit_box,
                background="#092114",
                highlightbackground="#1f5736",
                highlightthickness=1 * s,
                padx=16 * s,
                pady=12 * s,
            )
            empty_card.pack(fill="x", pady=2 * s)
            tkinter.Label(
                empty_card,
                text="No hands recorded since reset. Play a round to see strategy, index, and bet-sizing feedback.",
                font=row_hdr_font,
                fg="#b0bec5",
                background="#092114",
                anchor="w",
            ).pack(fill="x")
        elif not displayed_hands:
            clean_card = tkinter.Frame(
                audit_box,
                background="#092114",
                highlightbackground="#2e7d32",
                highlightthickness=1 * s,
                padx=16 * s,
                pady=12 * s,
            )
            clean_card.pack(fill="x", pady=2 * s)
            tkinter.Label(
                clean_card,
                text="[OK] Flawless play! Zero Basic Strategy, Illustrious 18, or Kelly bet-sizing mistakes in recent hands.",
                font=row_hdr_font,
                fg="#69f0ae",
                background="#092114",
                anchor="w",
            ).pack(fill="x")
        else:
            for offset, rec in enumerate(page_hands):
                idx = start_idx + offset + 1
                if rec.ungraded_reason is not None:
                    row_bg = "#151824"
                    border_col = "#5c6bc0"
                elif rec.has_mistake:
                    row_bg = "#211114"
                    border_col = "#ef5350"
                else:
                    row_bg = "#092315" if idx % 2 == 1 else "#0d2e1c"
                    border_col = "#1f5736"

                row_frame = tkinter.Frame(
                    audit_box,
                    background=row_bg,
                    highlightbackground=border_col,
                    highlightthickness=1 * s,
                    padx=12 * s,
                    pady=3 if compact else (5 * s),
                )
                row_frame.pack(fill="x", pady=2)
                self._rendered_hand_frames.append(row_frame)

                top_row = tkinter.Frame(row_frame, background=row_bg)
                top_row.pack(fill="x")
                top_row.columnconfigure(0, weight=1)

                seat_prefix = f"Seat {rec.seat_idx}  |  " if rec.seat_idx > 0 else ""
                ungraded_tag = f"  |  [UNGRADED: {rec.ungraded_reason.upper()}]" if rec.ungraded_reason else ""
                tc_sign = "+" if rec.pre_deal_tc > 0 else ""
                meta_text = (
                    f"#{idx}   |   {seat_prefix}{rec.rules_badge}   |   True Count: {tc_sign}{rec.pre_deal_tc:.1f}{ungraded_tag}"
                )
                tkinter.Label(
                    top_row,
                    text=meta_text,
                    font=row_hdr_font,
                    fg="#ffd54f" if rec.ungraded_reason is None else "#9fa8da",
                    background=row_bg,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                outcome_badge, outcome_col = self._format_outcome_badge(rec.outcome, rec.net_profit)
                tkinter.Label(
                    top_row,
                    text=outcome_badge,
                    font=row_hdr_font,
                    fg=outcome_col,
                    background=row_bg,
                    anchor="e",
                ).grid(row=0, column=1, sticky="e")

                mid_row = tkinter.Frame(row_frame, background=row_bg)
                mid_row.pack(fill="x", pady=(2, 2))
                mid_row.columnconfigure(0, weight=1)

                p_disp = self._format_cards_with_total(rec.player_cards)
                d_disp = self._format_cards_with_total(rec.dealer_cards)
                tkinter.Label(
                    mid_row,
                    text=f"Player: {p_disp}    vs    Dealer: {d_disp}",
                    font=row_hdr_font,
                    fg="#ffffff",
                    background=row_bg,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                if rec.kelly_status == "OPTIMAL":
                    kelly_txt = f"Wager: ${rec.wager:,}  (Kelly: OPTIMAL)"
                    kelly_col = "#69f0ae"
                elif rec.kelly_status in ("OVERBET", "UNDERBET"):
                    kelly_txt = f"Wager: ${rec.wager:,}  ({rec.kelly_status}: Target ${rec.kelly_target_bet:,})"
                    kelly_col = "#ffb74d"
                else:
                    kelly_txt = "Casual Mode (No Wager)" if rec.wager == 0 else f"Wager: ${rec.wager:,}"
                    kelly_col = "#90a4ae"

                tkinter.Label(
                    mid_row,
                    text=kelly_txt,
                    font=row_hdr_font,
                    fg=kelly_col,
                    background=row_bg,
                    anchor="e",
                ).grid(row=0, column=1, sticky="e")

                if not rec.decisions:
                    tkinter.Label(
                        row_frame,
                        text="Resolved on initial deal (no voluntary action required)",
                        font=row_step_font,
                        fg="#90a4ae",
                        background=row_bg,
                        anchor="w",
                    ).pack(fill="x", pady=(1, 0))
                else:
                    for d in rec.decisions:
                        clean_expl = str(d.explanation).replace("\u2014", "-").replace("\u2013", "-")
                        if not d.is_bs_optimal:
                            step_txt = (
                                f"[!] Mistake: Played {d.action_taken} -> Optimal: {d.optimal_action}  ({clean_expl})"
                            )
                            step_col = "#ff8a80"
                        elif d.is_i18_spot and not d.is_i18_optimal:
                            step_txt = (
                                f"[i] Played {d.action_taken} -> Missed I18 Index: {d.optimal_action}  ({clean_expl})"
                            )
                            step_col = "#ffd54f"
                        else:
                            step_txt = f"[OK] Optimal: {d.action_taken}  ({clean_expl})"
                            step_col = "#69f0ae"

                        step_lbl = tkinter.Label(
                            row_frame,
                            text=step_txt,
                            font=row_step_font,
                            fg=step_col,
                            background=row_bg,
                            anchor="w",
                            justify="left",
                            wraplength=init_wrap,
                        )
                        step_lbl.pack(fill="x", pady=(1, 0))
                        self._step_wrap_labels.append(step_lbl)

        self._bind_mousewheel_recursive(self.scroll_content)
        try:
            self.scroll_content.update_idletasks()
            cw = max(1, int(self.canvas.winfo_width()))
            ch = max(1, int(self.canvas.winfo_height()))
            target_h = max(ch, int(self.scroll_content.winfo_reqheight()))
            self.canvas.itemconfig(self.canvas_window, width=cw, height=target_h)
            self.canvas.configure(scrollregion=(0, 0, cw, target_h))
        except Exception:
            pass

    def _ask_confirm_reset_trip(self) -> bool:
        return InWindowConfirmModal.ask_yes_no(
            parent_screen=self,
            title="⚠️ Reset Strategy Tripometer?",
            message=(
                "Reset the Strategy Tripometer counters, Net Trip P&L, and 50-hand audit log?\n\n"
                "Your career bankroll, Hall of Fame records, Bootcamp badges, and unlocked costumes "
                "will NOT be affected."
            ),
            confirm_label="🗑 Reset Trip Stats",
            cancel_label="✔ Keep Trip Log (Esc)",
            art_scale=self.menu_scale,
            allow_withdrawn=False,
        )

    def _on_click_reset_trip(self) -> None:
        if not self._ask_confirm_reset_trip():
            return
        if hasattr(self.app, "tripometer") and self.app.tripometer is not None:
            self.app.tripometer.reset()
        self.current_page = 0
        if hasattr(self.app, "_refresh_trip_button_badge"):
            self.app._refresh_trip_button_badge()
        self._render_tripometer_contents()

    def _on_close(self, event: Any = None) -> str:
        if hasattr(self.app, "_close_tripometer_dialog"):
            self.app._close_tripometer_dialog()
        else:
            try:
                self.destroy()
            except Exception:
                pass
        return "break"
