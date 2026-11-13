"""
Modal Dialogs and Toplevel Overlays for Blackjack.

Provides:
- StoryDialogueDialog: Atmospheric narrative story modal with speaker portraits.
- AngelicDraftDialog: Balatro-style Roguelike celestial blessing card drafting dialog.
- SettingsDialog: Preferences modal with audio/scaling toggles and save reset safety.
- ShortcutsDialog: Clean 2x2 categorized grid illustrating all keyboard & mouse controls.
- WelcomeSplashDialog: First-launch splash screen introducing game modes, rules, and hotkeys.
"""

from __future__ import annotations

import tkinter
from typing import Any, Callable, List, Optional

import config
from audio_assets import KeyboardIconLoader
from config import ASSETS_EXTRA_DIR, PANEL_BACKGROUND_COLOR, TABLE_BACKGROUND_COLOR
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
    get_digital_font,
)
from ui_chip_renderer import draw_25d_grade_medallion

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


# ============================================================================
# 1. StoryDialogueDialog
# ============================================================================

class StoryDialogueDialog(tkinter.Toplevel):
    """
    Atmospheric narrative dialogue modal featuring custom speaker portraits,
    dark gothic or celestial styling, and responsive proceed controls.
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
        super().__init__(parent)
        self.on_close_cb = on_close
        self.title(title)
        try:
            if parent.winfo_ismapped():
                self.transient(parent)
        except Exception:
            pass
        self.resizable(False, False)

        bg_col = "#041421" if is_celestial else "#0d0204"
        border_col = "#00e5ff" if is_celestial else "#8b0000"
        header_col = "#80cbc4" if is_celestial else "#ff5252"
        btn_bg = "#00695c" if is_celestial else "#b71c1c"
        btn_active = "#00897b" if is_celestial else "#d32f2f"

        self.configure(background=bg_col, padx=14, pady=14)

        port_w = portrait_img.width() if portrait_img is not None else 0
        is_hi_dpi = port_w > 140
        speaker_font = get_element_font("story_dialog_speaker", scale=2.0 if is_hi_dpi else 1.0)
        body_font = get_element_font("story_dialog_body", scale=2.0 if is_hi_dpi else 1.0)
        btn_font = get_element_font("story_dialog_button", scale=2.0 if is_hi_dpi else 1.0)
        wrap_w = 540 if is_hi_dpi else 500

        frame = tkinter.Frame(
            self, background=bg_col, relief="ridge", borderwidth=2,
            highlightbackground=border_col, highlightthickness=1
        )
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        # Portrait container
        self.portrait_img = portrait_img
        if portrait_img:
            port_lbl = tkinter.Label(frame, image=portrait_img, background=bg_col)
            port_lbl.image = portrait_img
            port_lbl.pack(side="left", padx=14, pady=12)
            self.portrait_label = port_lbl

        # Content container
        self.content_box = tkinter.Frame(frame, background=bg_col)
        self.content_box.pack(side="left", fill="both", expand=True, padx=(10, 16), pady=12)

        self.speaker_label = tkinter.Label(
            self.content_box, text=speaker, font=speaker_font,
            fg=header_col, background=bg_col, anchor="w", justify="left"
        )
        self.speaker_label.pack(side="top", anchor="w", fill="x")

        self.action_button = tkinter.Button(
            self.content_box, text=button_text, font=btn_font,
            background=btn_bg, foreground="#ffffff", activebackground=btn_active,
            activeforeground="#ffffff", relief="flat", borderwidth=0,
            highlightthickness=0, cursor="hand2", padx=20, pady=8,
            takefocus=False, command=self._dismiss
        )
        self.action_button.pack(side="bottom", anchor="e", pady=(8, 0))

        self.message_label = tkinter.Label(
            self.content_box, text=text_content, font=body_font,
            fg="#eceff1", background=bg_col, anchor="w", justify="left", wraplength=wrap_w
        )
        self.message_label.pack(side="top", anchor="w", fill="x", expand=True, pady=(8, 12))

        def _on_content_configure(event):
            if event.width > 120:
                new_wrap = max(240, event.width - 16)
                if abs(int(self.message_label.cget("wraplength")) - new_wrap) > 4:
                    self.message_label.configure(wraplength=new_wrap)

        self.content_box.bind("<Configure>", _on_content_configure)

        try:
            self.update_idletasks()
            req_w = self.winfo_reqwidth()
            req_h = self.winfo_reqheight()
            min_w = 820 if is_hi_dpi else 720
            min_h = 360 if is_hi_dpi else 290
            screen_w = max(800, parent.winfo_screenwidth())
            screen_h = max(600, parent.winfo_screenheight())
            w = min(max(min_w, req_w + 16), screen_w - 80)
            h = min(max(min_h, req_h + 16), screen_h - 80)
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.dialog_width = w
            self.dialog_height = h
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
            self.update_idletasks()
        except Exception:
            self.dialog_width = 720
            self.dialog_height = 290
            self.geometry("720x290")

        self.bind("<Return>", lambda e: self._dismiss())
        self.bind("<space>", lambda e: self._dismiss())
        self.bind("<Escape>", lambda e: self._dismiss())
        self.protocol("WM_DELETE_WINDOW", self._dismiss)
        self.focus_set()

    def _dismiss(self):
        cb = self.on_close_cb
        try:
            self.destroy()
        except Exception:
            pass
        if cb:
            cb()


# ============================================================================
# 2. AngelicDraftDialog
# ============================================================================

class AngelicDraftDialog(tkinter.Toplevel):
    """
    Balatro-style Roguelike celestial blessing draft dialog.
    Presents 3 relic cards side-by-side with icon, title, tagline, description, and draft buttons.
    """

    def __init__(self, parent: tkinter.Misc, choices: list[Blessing], relic_icons: dict, on_select: Callable[[Blessing], None]):
        super().__init__(parent)
        self.on_select = on_select
        self.title("✦ CELESTIAL BLESSINGS - DRAFT A SACRED RELIC ✦")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#03101c", padx=18, pady=16)

        w, h = 780, 420
        try:
            screen_w = max(800, parent.winfo_screenwidth())
            screen_h = max(600, parent.winfo_screenheight())
            w = min(w, screen_w - 80)
            h = min(h, screen_h - 80)
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
        except Exception:
            self.geometry(f"{w}x{h}")

        tkinter.Label(
            self, text="✦ CHOOSE YOUR CELESTIAL BLESSING ✦",
            font=get_element_font("dialog_title"), fg="#ffd700", background="#03101c"
        ).pack(pady=(0, 4))

        tkinter.Label(
            self, text="The Angel intervenes! Draft one divine relic to aid in the struggle for your soul.",
            font=get_element_font("angelic_draft_subtitle"), fg="#80cbc4", background="#03101c"
        ).pack(pady=(0, 14))

        cards_frame = tkinter.Frame(self, background="#03101c")
        cards_frame.pack(fill="both", expand=True)

        for blessing in choices:
            details = BLESSING_REGISTRY[blessing]
            card_f = tkinter.Frame(
                cards_frame, background="#051f38", relief="ridge", borderwidth=2,
                highlightbackground="#00e5ff", highlightthickness=1, padx=12, pady=10
            )
            card_f.pack(side="left", fill="both", expand=True, padx=6)

            icon = relic_icons.get(blessing.value)
            if icon:
                ilbl = tkinter.Label(card_f, image=icon, background="#051f38")
                ilbl.image = icon
                ilbl.pack(pady=(2, 6))

            tkinter.Label(
                card_f, text=details.title, font=get_element_font("angelic_draft_title"),
                fg="#ffd700", background="#051f38"
            ).pack(pady=(0, 2))

            tkinter.Label(
                card_f, text=details.tagline, font=get_element_font("angelic_draft_tagline"),
                fg="#80cbc4", background="#051f38"
            ).pack(pady=(0, 6))

            tkinter.Label(
                card_f, text=details.description, font=get_element_font("angelic_draft_description"),
                fg="#eceff1", background="#051f38", justify="center", wraplength=205
            ).pack(fill="both", expand=True, pady=(0, 10))

            btn = tkinter.Button(
                card_f, text="Equip Relic", font=get_element_font("angelic_draft_button"),
                background="#00838f", foreground="#ffffff", activebackground="#00acc1",
                activeforeground="#ffffff", relief="raised", borderwidth=2, cursor="hand2",
                padx=14, pady=4,
                command=lambda b=blessing: self._pick(b)
            )
            btn.pack(side="bottom", pady=4)

        try:
            self.update_idletasks()
            screen_w = max(800, parent.winfo_screenwidth())
            screen_h = max(600, parent.winfo_screenheight())
            w = min(max(780, self.winfo_reqwidth() + 16), screen_w - 80)
            h = min(max(420, self.winfo_reqheight() + 16), screen_h - 80)
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Must draft a blessing to proceed

    def _pick(self, blessing: Blessing):
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_select:
            self.on_select(blessing)


# ============================================================================
# 2.5 MultiSeatInsuranceDialog
# ============================================================================

class MultiSeatInsuranceDialog(tkinter.Toplevel):
    """
    Unified multi-seat insurance modal dialog presented when the dealer shows an Ace.
    Allows independent insurance decisions per active seat with 'Insure All' and 'Decline All' shortcuts.
    Clamps options by available bankroll.
    Safely intercepts WM_DELETE_WINDOW and <Escape> to decline all and prevent FSM deadlocks.
    """

    def __init__(
        self,
        parent: tkinter.Tk | tkinter.Misc,
        seats: List[Any],
        bankroll: int,
        on_confirm: Callable[[dict[int, int]], None],
        on_decline: Callable[[], None],
    ):
        super().__init__(parent)
        self.seats = [s for s in seats if getattr(s, "is_active", True) and getattr(s, "main_bet", 0) > 0]
        self.bankroll = bankroll
        self.on_confirm_cb = on_confirm
        self.on_decline_cb = on_decline
        self._closed = False

        self.title("🛡 Dealer Shows Ace - Insurance")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background=PANEL_BACKGROUND_COLOR)

        dialog_w, dialog_h = 500, 420
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            x = max(0, root_x + (root_w - dialog_w) // 2)
            y = max(0, root_y + (root_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self.seat_vars: dict[int, tkinter.BooleanVar] = {}
        self.seat_costs: dict[int, int] = {}
        for s in self.seats:
            cost = max(1, s.main_bet // 2)
            self.seat_costs[s.seat_index] = cost
            self.seat_vars[s.seat_index] = tkinter.BooleanVar(value=False)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_decline)
        self.bind("<Escape>", lambda e: self._on_decline())
        self.focus_set()

    def _build_ui(self):
        content = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR, padx=16, pady=14)
        content.pack(fill="both", expand=True)

        header = tkinter.Label(
            content, text="🛡 DEALER SHOWS AN ACE",
            font=get_element_font("dialog_title"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        )
        header.pack(pady=(0, 4))

        sub = tkinter.Label(
            content,
            text=f"Insurance pays 2:1 if Dealer has Natural Blackjack.\nAvailable Bankroll: ${self.bankroll}",
            font=get_body_font(18), fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR, justify="center"
        )
        sub.pack(pady=(0, 10))

        list_frame = tkinter.LabelFrame(
            content, text=" Active Seats Wagering Insurance ", font=get_header_font(16),
            fg="#80cbc4", background=PANEL_BACKGROUND_COLOR, padx=12, pady=8
        )
        list_frame.pack(fill="x", pady=(0, 10))

        self.cb_widgets = {}
        total_all_cost = sum(self.seat_costs.values())
        seat_labels = {1: "Seat 1 (Right / First Base)", 2: "Seat 2 (Center / Main)", 3: "Seat 3 (Left / Third Base)"}

        for s in self.seats:
            s_idx = s.seat_index
            cost = self.seat_costs[s_idx]
            lbl_text = f"{seat_labels.get(s_idx, f'Seat {s_idx}')}: Main Bet ${s.main_bet} -> Insurance ${cost}"
            can_afford = (self.bankroll >= cost)

            cb = tkinter.Checkbutton(
                list_frame,
                text=lbl_text,
                variable=self.seat_vars[s_idx],
                command=self._on_check_toggle,
                font=get_body_font(18),
                fg="#ffffff" if can_afford else "#888888",
                selectcolor="#004d40",
                activebackground=PANEL_BACKGROUND_COLOR,
                background=PANEL_BACKGROUND_COLOR,
                state="normal" if can_afford else "disabled",
                cursor="hand2" if can_afford else "arrow",
                anchor="w",
            )
            cb.pack(fill="x", pady=3)
            self.cb_widgets[s_idx] = cb

        self.total_cost_lbl = tkinter.Label(
            content, text="Selected Insurance: $0",
            font=get_badge_font(16), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        )
        self.total_cost_lbl.pack(pady=(0, 8))

        btn_row = tkinter.Frame(content, background=PANEL_BACKGROUND_COLOR)
        btn_row.pack(fill="x", pady=(4, 0))
        btn_row.columnconfigure(0, weight=1)
        btn_row.columnconfigure(1, weight=1)
        btn_row.columnconfigure(2, weight=1)

        can_insure_all = (self.bankroll >= total_all_cost and len(self.seats) > 0)
        self.btn_insure_all = tkinter.Button(
            btn_row, text=f"Insure All (${total_all_cost})",
            font=get_button_font(15), background="#ff9800", fg="#111111",
            activebackground="#ffa726", activeforeground="#000000",
            state="normal" if can_insure_all else "disabled",
            cursor="hand2" if can_insure_all else "arrow",
            command=self._on_insure_all, padx=4, pady=5
        )
        self.btn_insure_all.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.btn_confirm = tkinter.Button(
            btn_row, text="Confirm",
            font=get_button_font(15), background="#1b5e20", fg="white",
            activebackground="#2e7d32", activeforeground="white",
            cursor="hand2", command=self._on_confirm, padx=4, pady=5
        )
        self.btn_confirm.grid(row=0, column=1, sticky="ew", padx=3)

        self.btn_decline_all = tkinter.Button(
            btn_row, text="Decline All",
            font=get_button_font(15), background="#37474f", fg="white",
            activebackground="#455a64", activeforeground="white",
            cursor="hand2", command=self._on_decline, padx=4, pady=5
        )
        self.btn_decline_all.grid(row=0, column=2, sticky="ew", padx=(3, 0))

    def _on_check_toggle(self):
        total = sum(self.seat_costs[s_idx] for s_idx, var in self.seat_vars.items() if var.get())
        if total > self.bankroll:
            for s_idx, var in self.seat_vars.items():
                if var.get() and total > self.bankroll:
                    var.set(False)
                    total -= self.seat_costs[s_idx]
        self.total_cost_lbl.config(text=f"Selected Insurance: ${total}")

    def _on_insure_all(self):
        total_all_cost = sum(self.seat_costs.values())
        if self.bankroll < total_all_cost:
            return
        for var in self.seat_vars.values():
            var.set(True)
        self._on_confirm()

    def _on_confirm(self):
        if self._closed:
            return
        self._closed = True
        chosen = {s_idx: self.seat_costs[s_idx] for s_idx, var in self.seat_vars.items() if var.get()}
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_confirm_cb:
            self.on_confirm_cb(chosen)

    def _on_decline(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_decline_cb:
            self.on_decline_cb()


# ============================================================================
# 3. SettingsDialog
# ============================================================================

class SettingsDialog(tkinter.Toplevel):
    """
    Casino Settings & Save Data Management Dialog.
    Provides options for sound, scaling, dealer stage, and persistent save data
    management, including an irreversible 'Clear Save File' reset with safety confirmation.
    Embedded in a scrollable frame for display-fit resilience.
    """

    def __init__(self, parent: tkinter.Tk, app: Any):
        super().__init__(parent)
        self.app = app
        self.title("⚙ Settings & Casino Records")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background=PANEL_BACKGROUND_COLOR)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        dialog_w, dialog_h = 620, 620
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            screen_h = parent.winfo_screenheight()
            scale = getattr(app, "scale_factor", 1.0)
            cfg_max_h = int(config.DEFAULT_WINDOW_HEIGHT * scale)
            dialog_h = min(dialog_h, max(460, min(screen_h - 80, cfg_max_h)))
            x = max(0, root_x + (root_w - dialog_w) // 2)
            y = max(0, root_y + (root_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self.active_tab: int = 0
        initial_rules = getattr(app, "house_rules", None)
        self._draft_rules: HouseRules = (
            initial_rules.normalized() if isinstance(initial_rules, HouseRules) else HouseRules()
        )
        self.status_msg_var = tkinter.StringVar(value="All casino records active.")
        self.rules_status_var = tkinter.StringVar(value="")

        # Persistent Header & Paginated Tab Bar
        self.header_frame = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR, padx=16, pady=8)
        self.header_frame.pack(side="top", fill="x")

        header = tkinter.Label(
            self.header_frame,
            text="⚙ CASINO SETTINGS & HOUSE RULES",
            font=get_header_font(16, weight="bold"),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        )
        header.pack(pady=(0, 6))

        tab_bar = tkinter.Frame(self.header_frame, background=PANEL_BACKGROUND_COLOR)
        tab_bar.pack(fill="x")
        tab_bar.columnconfigure(0, weight=1, uniform="settings_tabs")
        tab_bar.columnconfigure(1, weight=1, uniform="settings_tabs")

        self.tab_general_btn = tkinter.Button(
            tab_bar,
            text="[1] Table & Audio",
            font=get_button_font(15),
            background="#1b5e20",
            fg="#ffd700",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            relief="sunken",
            borderwidth=2,
            cursor="hand2",
            padx=10,
            pady=4,
            command=lambda: self._switch_tab(0),
        )
        self.tab_general_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.tab_rules_btn = tkinter.Button(
            tab_bar,
            text="[2] House Rules",
            font=get_button_font(15),
            background="#082415",
            fg="#b0bec5",
            activebackground="#143d26",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=10,
            pady=4,
            command=lambda: self._switch_tab(1),
        )
        self.tab_rules_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Persistent Bottom Action Buttons Row: Green "Done" and Red "Reset Data"
        action_row = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR, padx=16, pady=8)
        action_row.pack(side="bottom", fill="x")
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        self.done_btn = tkinter.Button(
            action_row,
            text="✔ Done",
            font=get_button_font(15),
            background="#2e7d32",
            fg="white",
            activebackground="#388e3c",
            activeforeground="white",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            command=self._on_close,
            padx=12,
            pady=6,
        )
        self.done_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.clear_save_btn = tkinter.Button(
            action_row,
            text="🗑 Reset Data",
            font=get_button_font(15),
            background="#b71c1c",
            fg="#ffffff",
            activebackground="#d32f2f",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            command=self._on_click_clear_save,
            padx=12,
            pady=6,
        )
        self.clear_save_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Scrollable container setup
        self.canvas = tkinter.Canvas(
            self,
            background=PANEL_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
            height=240,
        )
        self.v_scrollbar = tkinter.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scroll_content = tkinter.Frame(self.canvas, background=PANEL_BACKGROUND_COLOR, padx=16, pady=6)

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scroll_content, anchor="nw"
        )
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
        self.bind("1", lambda e: self._switch_tab(0))
        self.bind("2", lambda e: self._switch_tab(1))

        self._build_ui()
        self._switch_tab(0)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.focus_set()

    def _on_prev_tab(self):
        self._switch_tab((self.active_tab - 1) % 2)
        return "break"

    def _on_next_tab(self):
        self._switch_tab((self.active_tab + 1) % 2)
        return "break"

    def _on_tab_key(self):
        self._switch_tab((self.active_tab + 1) % 2)
        return "break"

    def _switch_tab(self, tab_idx: int) -> None:
        """Switches between Tab 0 (Table & Audio) and Tab 1 (House Rules)."""
        self.active_tab = 0 if int(tab_idx) == 0 else 1
        if self.active_tab == 0:
            self.tab_rules_frame.pack_forget()
            self.tab_general_frame.pack(fill="x", expand=True)
            self.tab_general_btn.configure(background="#1b5e20", fg="#ffd700", relief="sunken")
            self.tab_rules_btn.configure(background="#082415", fg="#b0bec5", relief="raised")
        else:
            self.tab_general_frame.pack_forget()
            self.tab_rules_frame.pack(fill="x", expand=True)
            self.tab_general_btn.configure(background="#082415", fg="#b0bec5", relief="raised")
            self.tab_rules_btn.configure(background="#1b5e20", fg="#ffd700", relief="sunken")
            self._refresh_house_rules_controls()
        try:
            self.canvas.yview_moveto(0.0)
            self.scroll_content.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _on_scroll_update(self, first, last):
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack_forget()
        else:
            if not self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_ui(self):
        self.tab_general_frame = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        self.tab_rules_frame = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)

        # ====================================================================
        # TAB 0: Table & Audio Preferences + Save Data & Hall of Fame Records
        # ====================================================================
        ctrl_frame = tkinter.LabelFrame(
            self.tab_general_frame, text=" Table Preferences ", font=get_header_font(16),
            fg="#80cbc4", background=PANEL_BACKGROUND_COLOR, padx=12, pady=8
        )
        ctrl_frame.pack(fill="x", pady=(0, 10))

        tier1_lbl = tkinter.Label(
            ctrl_frame, text="Audio & Dialogue:", font=get_badge_font(15),
            fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR
        )
        tier1_lbl.pack(anchor="w", pady=(0, 2))

        audio_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        audio_row.pack(fill="x", pady=(0, 6))
        audio_row.columnconfigure(0, weight=1)
        audio_row.columnconfigure(1, weight=1)

        self.sound_btn = tkinter.Button(
            audio_row, textvariable=self.app.sound_status_var, font=get_button_font(15),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_sound,
            padx=10, pady=4
        )
        self.sound_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        if hasattr(self.app, "voice_status_var"):
            self.voice_btn = tkinter.Button(
                audio_row, textvariable=self.app.voice_status_var, font=get_button_font(15),
                background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
                relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_voice,
                padx=10, pady=4
            )
            self.voice_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        tier2_lbl = tkinter.Label(
            ctrl_frame, text="Display & Customization:", font=get_badge_font(15),
            fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR
        )
        tier2_lbl.pack(anchor="w", pady=(2, 2))

        disp_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        disp_row.pack(fill="x", pady=(0, 2))
        disp_row.columnconfigure(0, weight=1)
        disp_row.columnconfigure(1, weight=1)

        self.dealer_btn = tkinter.Button(
            disp_row, textvariable=self.app.dealer_view_status_var, font=get_button_font(15),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_dealer_view,
            padx=8, pady=4
        )
        self.dealer_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.wardrobe_btn = tkinter.Button(
            disp_row, text="🎩 Wardrobe", font=get_button_font(15),
            background="#1b5e20", fg="white", activebackground="#2e7d32", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._open_wardrobe_dialog,
            padx=8, pady=4
        )
        self.wardrobe_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        tier3_lbl = tkinter.Label(
            ctrl_frame, text="Play Mode & Onboarding:", font=get_badge_font(15),
            fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR
        )
        tier3_lbl.pack(anchor="w", pady=(4, 2))

        mode_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        mode_row.pack(fill="x", pady=(0, 2))
        mode_row.columnconfigure(0, weight=1)
        mode_row.columnconfigure(1, weight=1)

        mode_name = getattr(self.app, "play_mode", "betting").capitalize()
        self.mode_btn = tkinter.Button(
            mode_row, text=f"🎮 Mode: {mode_name}", font=get_button_font(15),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self._on_cycle_play_mode,
            padx=8, pady=4
        )
        self.mode_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.welcome_btn = tkinter.Button(
            mode_row, text="🌟 Welcome Screen...", font=get_button_font(15),
            background="#1b5e20", fg="white", activebackground="#2e7d32", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self._on_open_welcome_screen,
            padx=8, pady=4
        )
        self.welcome_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        tier4_lbl = tkinter.Label(
            ctrl_frame, text="Table Wagering Seats:", font=get_badge_font(15),
            fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR
        )
        tier4_lbl.pack(anchor="w", pady=(4, 2))

        seats_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        seats_row.pack(fill="x", pady=(0, 2))
        seats_row.columnconfigure(0, weight=1)
        seats_row.columnconfigure(1, weight=1)

        seats_count = getattr(self.app, "table_seats", 1)
        self.seats_btn = tkinter.Button(
            seats_row, text=f"🪑 Table Seats: {seats_count} Seat{'s' if seats_count > 1 else ''}",
            font=get_button_font(15),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self._on_toggle_table_seats,
            padx=8, pady=4
        )
        self.seats_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.bootcamp_btn = tkinter.Button(
            seats_row, text="🎓 Counting Bootcamp...",
            font=get_button_font(15),
            background="#1b5e20", fg="white", activebackground="#2e7d32", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self._on_open_counting_bootcamp,
            padx=8, pady=4
        )
        self.bootcamp_btn.grid(row=0, column=1, sticky="ew", padx=(3, 0))

        save_frame = tkinter.LabelFrame(
            self.tab_general_frame, text=" Save Data & Hall of Fame Records ", font=get_header_font(16),
            fg="#ffd700", background=PANEL_BACKGROUND_COLOR, padx=12, pady=8
        )
        save_frame.pack(fill="x", pady=(0, 6))

        self.stats_frame = tkinter.Frame(save_frame, background=PANEL_BACKGROUND_COLOR)
        self.stats_frame.pack(fill="x", pady=(0, 6))

        self.lbl_peak = tkinter.Label(
            self.stats_frame, text="", font=get_body_font(15),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_peak.pack(fill="x", pady=1)

        self.lbl_hands = tkinter.Label(
            self.stats_frame, text="", font=get_body_font(15),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_hands.pack(fill="x", pady=1)

        self.lbl_counting = tkinter.Label(
            self.stats_frame, text="", font=get_body_font(15),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_counting.pack(fill="x", pady=1)

        self.lbl_side_bets = tkinter.Label(
            self.stats_frame, text="", font=get_body_font(15),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_side_bets.pack(fill="x", pady=1)

        self.lbl_exorcist = tkinter.Label(
            self.stats_frame, text="", font=get_body_font(15),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_exorcist.pack(fill="x", pady=1)

        self._refresh_stats_display()

        lbl_status = tkinter.Label(
            save_frame, textvariable=self.status_msg_var, font=get_body_font(15),
            fg="#ffeb3b", background=PANEL_BACKGROUND_COLOR
        )
        lbl_status.pack(pady=(2, 4))

        # ====================================================================
        # TAB 1: Configurable Casino House Rules & Table Limits
        # ====================================================================
        self._build_house_rules_tab()

    def _build_house_rules_tab(self) -> None:
        """Builds Tab 1 (House Rules) with discrete <=3-button-per-row grids."""
        edge_banner = tkinter.Frame(
            self.tab_rules_frame,
            background="#082415",
            highlightbackground="#d4af37",
            highlightthickness=1,
            padx=10,
            pady=6,
        )
        edge_banner.pack(fill="x", pady=(0, 8))

        self.house_edge_label = tkinter.Label(
            edge_banner,
            text="",
            font=get_header_font(15, weight="bold"),
            fg="#ffd700",
            background="#082415",
        )
        self.house_edge_label.pack(anchor="w")

        self.active_rules_badge_label = tkinter.Label(
            edge_banner,
            text="",
            font=get_body_font(13),
            fg="#80cbc4",
            background="#082415",
        )
        self.active_rules_badge_label.pack(anchor="w")

        # 1. Built-In Venue Presets (2x3 grid)
        presets_box = tkinter.LabelFrame(
            self.tab_rules_frame,
            text=" Casino Venue Presets ",
            font=get_header_font(15),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
            padx=10,
            pady=6,
        )
        presets_box.pack(fill="x", pady=(0, 8))
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
                font=get_button_font(13),
                background="#004d40",
                fg="#ffffff",
                activebackground="#00695c",
                activeforeground="#ffffff",
                relief="ridge",
                borderwidth=1,
                cursor="hand2",
                padx=6,
                pady=4,
                command=lambda p=pid: self._select_preset(p),
            )
            btn.grid(row=r, column=c, sticky="ew", padx=3, pady=2)
            self._preset_buttons[pid] = btn

        # 2. Shoe & Dealer Rules
        rules_box = tkinter.LabelFrame(
            self.tab_rules_frame,
            text=" Shoe, Payout & Player Options ",
            font=get_header_font(15),
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
            padx=10,
            pady=6,
        )
        rules_box.pack(fill="x", pady=(0, 8))

        def make_section_label(parent: tkinter.Misc, title: str) -> None:
            tkinter.Label(
                parent,
                text=title,
                font=get_badge_font(14),
                fg="#b2dfdb",
                background=PANEL_BACKGROUND_COLOR,
            ).pack(anchor="w", pady=(4, 2))

        def make_option_grid(
            parent: tkinter.Misc,
            options: list[tuple[Any, str]],
            cols: int,
            on_pick: Callable[[Any], None],
            uniform_tag: str,
        ) -> dict[Any, tkinter.Button]:
            frame = tkinter.Frame(parent, background=PANEL_BACKGROUND_COLOR)
            frame.pack(fill="x", pady=(0, 4))
            for col in range(cols):
                frame.columnconfigure(col, weight=1, uniform=uniform_tag)
            mapping: dict[Any, tkinter.Button] = {}
            for idx, (val, label) in enumerate(options):
                r, c = divmod(idx, cols)
                b = tkinter.Button(
                    frame,
                    text=label,
                    font=get_button_font(13),
                    background="#004d40",
                    fg="#ffffff",
                    activebackground="#00695c",
                    activeforeground="#ffffff",
                    relief="ridge",
                    borderwidth=1,
                    cursor="hand2",
                    padx=6,
                    pady=3,
                    command=lambda v=val: on_pick(v),
                )
                b.grid(row=r, column=c, sticky="ew", padx=3, pady=2)
                mapping[val] = b
            return mapping

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

        # 3. Table Betting Limits
        limits_box = tkinter.LabelFrame(
            self.tab_rules_frame,
            text=" Table Betting Limits (Min & Max) ",
            font=get_header_font(15),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
            padx=10,
            pady=6,
        )
        limits_box.pack(fill="x", pady=(0, 8))

        make_section_label(limits_box, "Minimum Main Bet:")
        self._min_bet_buttons = make_option_grid(
            limits_box,
            [(m, f"${m:,}") for m in ALLOWED_MINIMUM_BETS],
            3,
            lambda v: self._update_draft(minimum_bet=v),
            "hr_minbet",
        )

        make_section_label(limits_box, "Maximum Main Bet:")
        self._max_bet_buttons = make_option_grid(
            limits_box,
            [(0, "No Limit")] + [(m, f"${m:,}") for m in ALLOWED_MAXIMUM_BETS if m > 0],
            3,
            lambda v: self._update_draft(maximum_bet=v),
            "hr_maxbet",
        )

        # 4. Staged Apply & Reset Defaults Row
        commit_row = tkinter.Frame(self.tab_rules_frame, background=PANEL_BACKGROUND_COLOR)
        commit_row.pack(fill="x", pady=(4, 4))
        commit_row.columnconfigure(0, weight=1, uniform="hr_commit")
        commit_row.columnconfigure(1, weight=1, uniform="hr_commit")

        self.apply_rules_btn = tkinter.Button(
            commit_row,
            text="✔ Apply Rules",
            font=get_button_font(15),
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=10,
            pady=6,
            command=self._on_apply_house_rules,
        )
        self.apply_rules_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.reset_rules_defaults_btn = tkinter.Button(
            commit_row,
            text="↺ Classic Defaults",
            font=get_button_font(15),
            background="#37474f",
            fg="#ffffff",
            activebackground="#455a64",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=10,
            pady=6,
            command=self._on_reset_draft_rules,
        )
        self.reset_rules_defaults_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        self.rules_status_lbl = tkinter.Label(
            self.tab_rules_frame,
            textvariable=self.rules_status_var,
            font=get_body_font(14),
            fg="#ffeb3b",
            background=PANEL_BACKGROUND_COLOR,
        )
        self.rules_status_lbl.pack(pady=(2, 4))

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
        self.house_edge_label.configure(
            text=f"Estimated House Edge: {edge:.2f}%  ({preset_title})"
        )
        live_rules = getattr(self.app, "house_rules", HouseRules())
        self.active_rules_badge_label.configure(
            text=f"Live Table: {live_rules.short_badge()}   |   Draft: {r.short_badge()}"
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
            self.apply_rules_btn.configure(state="normal", background="#2e7d32")
            if self.rules_status_var.get().startswith("🔒"):
                self.rules_status_var.set("")
        else:
            self.apply_rules_btn.configure(state="disabled", background="#455a64")
            if getattr(self.app, "tour_active", False):
                self.rules_status_var.set("🔒 Active Casino Tour Salon rules are fixed. Exit Tour to customize.")
            else:
                self.rules_status_var.set("🔒 Finish current hand to change House Rules.")

    def _refresh_stats_display(self):
        """Refreshes the high scores, counting records, and achievement badges displayed in the dialog."""
        data = self.app.save_manager.data
        hs = data.highscores
        pct = (hs.total_hands_won / hs.total_hands_played * 100.0) if hs.total_hands_played > 0 else 0.0
        self.lbl_peak.configure(
            text=f"• All-Time Peak Bankroll: ${hs.peak_bankroll:,}"
        )
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
        exorcist_str = "✦ UNLOCKED (Cursed Stakes Active)" if data.achievements.exorcist else "Locked (Survive Hell's Table)"
        self.lbl_exorcist.configure(
            text=f"• Exorcist Title: {exorcist_str}"
        )

    def _ask_confirm_clear_save(self) -> bool:
        """
        Displays an explicit confirmation modal warning that clearing the save file is irreversible.
        Isolated for headless unit testing.
        """
        import tkinter.messagebox as msgbox
        return msgbox.askyesno(
            title="⚠️ Confirm Save Reset",
            message=(
                "WARNING: This action is irreversible!\n\n"
                "Clearing your save file will permanently reset all high scores, "
                "achievements (including Exorcist status), statistics, and "
                "unlocked dealer costumes back to an initial blank slate.\n\n"
                "Are you sure you want to clear your save file?"
            ),
            icon="warning",
            default="no",
            parent=self,
        )

    def _on_click_clear_save(self):
        """Handles clear save file button click with confirmation."""
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

    def _on_cycle_play_mode(self):
        """Cycles through casual -> betting -> training modes and updates app."""
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Exit the Casino Venue Tour before switching play mode.")
            return
        current = getattr(self.app, "play_mode", "betting")
        modes = ["casual", "betting", "training"]
        try:
            next_idx = (modes.index(current) + 1) % len(modes)
        except ValueError:
            next_idx = 0
        next_mode = modes[next_idx]
        if next_mode == "training" and hasattr(self.app, "activate_training_mode_entry"):
            self.app.activate_training_mode_entry(sync_save=True)
        else:
            if hasattr(self.app, "set_table_seats"):
                self.app.set_table_seats(3 if next_mode == "training" else 1)
            if hasattr(self.app, "apply_play_mode"):
                self.app.apply_play_mode(next_mode)
        if hasattr(self, "seats_btn"):
            seats_count = getattr(self.app, "table_seats", 1)
            self.seats_btn.config(text=f"🪑 Table Seats: {seats_count} Seat{'s' if seats_count > 1 else ''}")
        self.mode_btn.configure(text=f"🎮 Mode: {next_mode.capitalize()}")
        self.status_msg_var.set(f"Play mode switched to {next_mode.capitalize()}.")

    def _on_toggle_table_seats(self):
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Casino Venue Tour salons are 1-Seat high-stakes tables.")
            return
        current = getattr(self.app, "table_seats", 1)
        new_count = 3 if current == 1 else 1
        if hasattr(self.app, "set_table_seats"):
            self.app.set_table_seats(new_count)
        else:
            self.app.table_seats = new_count
        self.seats_btn.config(text=f"🪑 Table Seats: {new_count} Seat{'s' if new_count > 1 else ''}")
        if new_count == 3:
            self.status_msg_var.set("3-Seat Wagering enabled. Haunted Mode disabled for multi-seat play.")
        else:
            self.status_msg_var.set("Standard 1-Seat Wagering enabled.")

    def _on_open_welcome_screen(self):
        """Relaunches the Welcome & Play Mode Selection splash dialog (blocked during Tour)."""
        if getattr(self.app, "tour_active", False):
            self.status_msg_var.set("🔒 Exit the Casino Venue Tour before switching Free-Play modes.")
            return
        if hasattr(self.app, "_open_welcome_splash_dialog"):
            self.app._open_welcome_splash_dialog()

    def _on_open_counting_bootcamp(self):
        """Closes Settings and launches the MIT Hi-Lo Counting Bootcamp stage map."""
        self._on_close()
        if hasattr(self.app, "enter_counting_bootcamp"):
            self.app.enter_counting_bootcamp(start_view="map")

    def _on_close(self):
        self.app._close_settings_dialog()


# ============================================================================
# 4. ShortcutsDialog
# ============================================================================

class ShortcutsDialog(tkinter.Toplevel):
    """
    Displays a clean modal HUD dialog illustrating all keyboard and mouse controls.
    Features a two-tab categorized navigation layout with an embedded scrollable
    canvas container and arrow-key/mousewheel navigation for zero-clipping guarantee.
    """

    def __init__(
        self,
        parent: tkinter.Misc,
        icon_loader: KeyboardIconLoader,
        icon_photo: Optional[Any] = None,
        on_close: Optional[Callable[[], None]] = None,
    ):
        super().__init__(parent)
        self.icon_loader = icon_loader
        self.on_close_cb = on_close
        self.title("Blackjack - Keyboard Shortcuts & Controls")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background=PANEL_BACKGROUND_COLOR)

        if icon_photo:
            try:
                self.iconphoto(False, icon_photo)
            except Exception:
                pass

        dialog_w, dialog_h = 760, 600
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            screen_h = parent.winfo_screenheight()
            dialog_h = min(dialog_h, max(380, screen_h - 80))
            pos_x = max(root_x + (root_w - dialog_w) // 2, 0)
            pos_y = max(root_y + (root_h - dialog_h) // 2, 0)
            self.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self.current_tab = 0
        self._tab_frames: list[tkinter.Frame] = []

        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", self._on_close)
        self.bind("<Left>", lambda e: self._switch_tab(0))
        self.bind("<Right>", lambda e: self._switch_tab(1))
        self.bind("<Tab>", lambda e: self._switch_tab(1 if self.current_tab == 0 else 0))
        self.bind("1", lambda e: self._switch_tab(0))
        self.bind("2", lambda e: self._switch_tab(1))
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.focus_set()

    def _on_mousewheel(self, event):
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_scroll_update(self, first, last):
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack_forget()
        else:
            if not self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _build_ui(self):
        # 1. Top Header Bar
        header_frame = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        header_frame.pack(fill="x", padx=14, pady=(5, 2))

        q_icon = self.icon_loader.get_icon("keyboard_question", scale_div=2)
        if q_icon:
            q_lbl = tkinter.Label(header_frame, image=q_icon, background=PANEL_BACKGROUND_COLOR)
            q_lbl.image = q_icon
            q_lbl.pack(side="left", padx=(0, 8))

        title_box = tkinter.Frame(header_frame, background=PANEL_BACKGROUND_COLOR)
        title_box.pack(side="left")

        tkinter.Label(
            title_box, text="KEYBOARD SHORTCUTS & CONTROLS",
            font=get_element_font("dialog_title"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="w")

        tkinter.Label(
            title_box, text="Full hands-free keyboard accessibility for authentic casino gameplay",
            font=get_header_font(16), fg="#80cbc4", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="w")

        close_btn = tkinter.Button(
            header_frame, text="✕ Close (Esc)", font=get_button_font(15),
            background="#c62828", foreground="#ffffff", activebackground="#e53935",
            activeforeground="#ffffff", relief="raised", borderwidth=1, cursor="hand2",
            takefocus=False, command=self._on_close
        )
        close_btn.pack(side="right")

        # 2. Tab Navigation Bar
        tab_nav = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        tab_nav.pack(fill="x", padx=14, pady=(2, 3))

        self.btn_tab_gameplay = tkinter.Button(
            tab_nav, text="🃏 Gameplay & Betting", font=get_button_font(15),
            background="#2e7d32", fg="white", activebackground="#388e3c",
            activeforeground="white", relief="raised", borderwidth=2, cursor="hand2",
            padx=14, pady=3, command=lambda: self._switch_tab(0)
        )
        self.btn_tab_gameplay.pack(side="left", padx=(0, 8))

        self.btn_tab_system = tkinter.Button(
            tab_nav, text="⚙️ System & Controls", font=get_button_font(15),
            background="#1e382b", fg="#cfd8dc", activebackground="#2e5441",
            activeforeground="white", relief="raised", borderwidth=1, cursor="hand2",
            padx=14, pady=3, command=lambda: self._switch_tab(1)
        )
        self.btn_tab_system.pack(side="left")

        # 3. Scrollable Canvas Area
        self.canvas = tkinter.Canvas(
            self, background=PANEL_BACKGROUND_COLOR, highlightthickness=0, borderwidth=0
        )
        self.v_scrollbar = tkinter.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scroll_content = tkinter.Frame(self.canvas, background=PANEL_BACKGROUND_COLOR, padx=14, pady=1)

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scroll_content, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self._on_scroll_update)

        self.scroll_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.pack(side="top", fill="both", expand=True)

        def make_panel(parent_f, title_text):
            panel = tkinter.Frame(
                parent_f, background="#053612", relief="ridge", borderwidth=2,
                padx=8, pady=2
            )
            panel.pack(fill="both", expand=True, padx=4, pady=1)
            tkinter.Label(
                panel, text=title_text, font=get_header_font(16),
                fg="#ffeb3b", background="#053612"
            ).pack(anchor="w", pady=(0, 2))
            return panel

        def add_row(parent_panel, icon_names: list[str], action_text: str, hint_text: str = ""):
            r = tkinter.Frame(parent_panel, background="#053612")
            r.pack(fill="x", pady=1)

            badges = tkinter.Frame(r, background="#053612")
            badges.pack(side="left")

            for i, name in enumerate(icon_names):
                if i > 0:
                    tkinter.Label(
                        badges, text="or", font=get_badge_font(14),
                        fg="#80cbc4", background="#053612"
                    ).pack(side="left", padx=2)

                icon = self.icon_loader.get_icon(name, scale_div=2)
                if icon:
                    l = tkinter.Label(badges, image=icon, background="#053612")
                    l.image = icon
                    l.pack(side="left", padx=1)
                else:
                    disp = name.replace("keyboard_", "").replace("mouse_", "").upper()
                    tkinter.Label(
                        badges, text=f"[{disp}]", font=get_badge_font(14),
                        background="#ffffff", foreground="#000000",
                        padx=3, pady=1, relief="raised", bd=1
                    ).pack(side="left", padx=1)

            tkinter.Label(
                r, text=action_text, font=get_element_font("dialog_action_label"),
                fg="#fff176", background="#053612"
            ).pack(side="left", padx=(5, 2))

            if hint_text:
                tkinter.Label(
                    r, text=hint_text, font=get_element_font("dialog_hint_label"),
                    fg="#eceff1", background="#053612"
                ).pack(side="left")

        # --------------------------------------------------------------------
        # Tab 0: Gameplay & Betting Content
        # --------------------------------------------------------------------
        self.tab_gameplay = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        grid_gameplay = tkinter.Frame(self.tab_gameplay, background=PANEL_BACKGROUND_COLOR)
        grid_gameplay.pack(fill="both", expand=True)
        grid_gameplay.columnconfigure(0, weight=1)
        grid_gameplay.columnconfigure(1, weight=1)

        # Left Column: Table Actions & Insurance
        left_col_g = tkinter.Frame(grid_gameplay, background=PANEL_BACKGROUND_COLOR)
        left_col_g.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        panel_actions = make_panel(left_col_g, "🃏 TABLE ACTIONS")
        add_row(panel_actions, ["keyboard_space", "keyboard_enter"], "Deal / Hit / Next", "(Context-sensitive)")
        add_row(panel_actions, ["keyboard_h"], "Hit", "(Draw another card)")
        add_row(panel_actions, ["keyboard_s"], "Stand", "(End turn, dealer plays)")
        add_row(panel_actions, ["keyboard_d"], "Double Down", "(Double bet, draw 1 card)")
        add_row(panel_actions, ["keyboard_p"], "Split Pair", "(Split equal rank cards)")
        add_row(panel_actions, ["keyboard_r"], "Surrender", "(Forfeit half bet before hitting)")

        panel_insurance = make_panel(left_col_g, "🛡️ INSURANCE DECISIONS")
        add_row(panel_insurance, ["keyboard_y"], "Take Insurance", "(Pays 2:1 on Dealer Ace)")
        add_row(panel_insurance, ["keyboard_n", "keyboard_escape"], "Decline Insurance", "(Skip side bet)")

        # Right Column: Chips & Wagering
        right_col_g = tkinter.Frame(grid_gameplay, background=PANEL_BACKGROUND_COLOR)
        right_col_g.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

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

        # --------------------------------------------------------------------
        # Tab 1: System & Controls Content
        # --------------------------------------------------------------------
        self.tab_system = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        grid_system = tkinter.Frame(self.tab_system, background=PANEL_BACKGROUND_COLOR)
        grid_system.pack(fill="both", expand=True)
        grid_system.columnconfigure(0, weight=1)
        grid_system.columnconfigure(1, weight=1)

        # Left Column: Display & Wardrobe
        left_col_s = tkinter.Frame(grid_system, background=PANEL_BACKGROUND_COLOR)
        left_col_s.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

        panel_display = make_panel(left_col_s, "🖥️ AUDIO & DISPLAY")
        add_row(panel_display, ["keyboard_m"], "Toggle Sound", "(Mute / Unmute audio)")
        add_row(panel_display, ["keyboard_f11"], "Toggle Fullscreen", "(F11 or Escape to exit)")
        add_row(panel_display, ["keyboard_v"], "Dealer Portrait", "(Toggle upper stage view)")

        panel_wardrobe = make_panel(left_col_s, "🎩 WARDROBE & RECORDS")
        add_row(panel_wardrobe, ["keyboard_shift", "keyboard_w"], "Dealer Wardrobe", "(Costumes & customizer)")
        add_row(panel_wardrobe, ["keyboard_shift", "keyboard_h"], "Hall of Fame", "(Trophy shelf & records)")

        # Right Column: Trainer & Accessibility
        right_col_s = tkinter.Frame(grid_system, background=PANEL_BACKGROUND_COLOR)
        right_col_s.grid(row=0, column=1, sticky="nsew", padx=(4, 0))

        panel_trainer = make_panel(right_col_s, "🧮 TRAINER & SUPERNATURAL")
        add_row(panel_trainer, ["keyboard_k", "keyboard_shift", "keyboard_c"], "Card Counter HUD", "(K or Shift+C)")
        add_row(panel_trainer, ["keyboard_t"], "Strategy Tripometer", "(Hand review & grades)")
        add_row(panel_trainer, ["keyboard_shift", "keyboard_t"], "Casino Venue Tour", "(Shift+T · Post-Exorcist)")
        add_row(panel_trainer, ["keyboard_shift", "keyboard_m"], "Cycle Play Mode", "(Casual / Betting / Training)")
        add_row(panel_trainer, ["keyboard_x"], "Miracle Draw", "(Hell's Table relic redraw)")

        panel_help = make_panel(right_col_s, "🖱️ ACCESSIBILITY & HELP")
        add_row(panel_help, ["keyboard_question", "keyboard_f1"], "Toggle Help", "(Show / Hide this HUD)")
        add_row(panel_help, ["keyboard_escape"], "Dismiss Dialog", "(Close active overlay)")
        add_row(panel_help, ["mouse_left"], "Click Button / Chip", "(Direct mouse interaction)")

        self._tab_frames = [self.tab_gameplay, self.tab_system]

        # 4. Footer Tip Banner
        footer_frame = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        footer_frame.pack(fill="x", padx=14, pady=(3, 5))

        tkinter.Label(
            footer_frame,
            text="💡 Tip: Switch tabs with [Left] / [Right] arrow keys or [1] / [2]. Shortcuts activate when controls are enabled.",
            font=get_element_font("dialog_tip_label"), fg="#ffe082", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="center")

        # Initial tab presentation
        self._switch_tab(0)

    def _switch_tab(self, tab_idx: int):
        """Switches between Gameplay & Betting (0) and System & Controls (1)."""
        self.current_tab = max(0, min(1, tab_idx))
        if self.current_tab == 0:
            self.tab_system.pack_forget()
            self.tab_gameplay.pack(fill="both", expand=True)
            self.btn_tab_gameplay.configure(background="#2e7d32", fg="white", borderwidth=2)
            self.btn_tab_system.configure(background="#1e382b", fg="#cfd8dc", borderwidth=1)
        else:
            self.tab_gameplay.pack_forget()
            self.tab_system.pack(fill="both", expand=True)
            self.btn_tab_system.configure(background="#2e7d32", fg="white", borderwidth=2)
            self.btn_tab_gameplay.configure(background="#1e382b", fg="#cfd8dc", borderwidth=1)

        self.canvas.yview_moveto(0.0)
        self.scroll_content.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_close(self, event=None):
        cb = self.on_close_cb
        try:
            self.destroy()
        except Exception:
            pass
        if cb:
            cb()
        return "break"


# ============================================================================
# 5. WelcomeSplashDialog
# ============================================================================

class WelcomeSplashDialog(tkinter.Toplevel):
    """
    First-run onboarding splash and play mode preference selector.
    Presents:
    - Retro pixel-art style game logo.
    - Default dealer greeting banner & speech dialogue.
    - 3 distinct selectable play modes:
      1) Casual Mode: Fun simple blackjack, no betting.
      2) Casino Betting Mode: Standard bankroll wagering & Hall of Fame records.
      3) Strategy & Counting Trainer: Live Hi-Lo count HUD, True Count, Ideal Bet Sizing,
         and Basic Strategy decision hints for every hand.
    - Persistent preference saving and immediate application.
    - Display-fit resilience via dynamic configuration derivation and auto-hiding scrollbar.
    """

    def __init__(
        self,
        parent: tkinter.Tk | tkinter.Misc,
        app: Any,
        on_confirm: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(parent)
        self.app = app
        self.on_confirm_cb = on_confirm
        self.title("Welcome to Blackjack!")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background=PANEL_BACKGROUND_COLOR)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        # Dynamic dialog geometry derived from live configuration and screen bounds
        scale = getattr(app, "scale_factor", 1.0)
        target_w = int(760 * (1.0 if scale <= 1.0 else 1.15))
        target_h = int(730 * (1.0 if scale <= 1.0 else 1.15))
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            screen_w = parent.winfo_screenwidth()
            screen_h = parent.winfo_screenheight()
            dialog_w = min(target_w, screen_w - 40)
            dialog_h = min(target_h, max(420, screen_h - 80))
            pos_x = max(0, root_x + (root_w - dialog_w) // 2)
            pos_y = max(0, root_y + (root_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
        except Exception:
            self.geometry(f"{target_w}x{target_h}")

        # Active mode selection (defaults to current preference or 'betting')
        current_pref = getattr(app.save_manager.data, "play_mode", "betting") if hasattr(app, "save_manager") else "betting"
        self.selected_mode = current_pref if current_pref in ("casual", "betting", "training") else "betting"
        self.remember_var = tkinter.BooleanVar(value=True)

        self._mode_cards: dict[str, dict[str, Any]] = {}

        # Scrollable container setup with auto-hiding scrollbar
        self.canvas = tkinter.Canvas(
            self, background=PANEL_BACKGROUND_COLOR, highlightthickness=0, borderwidth=0
        )
        self.v_scrollbar = tkinter.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scroll_content = tkinter.Frame(
            self.canvas, background=PANEL_BACKGROUND_COLOR, padx=14, pady=8
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.scroll_content, anchor="nw"
        )
        self.canvas.configure(yscrollcommand=self._on_scroll_update)

        self.scroll_content.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self.canvas.pack(side="left", fill="both", expand=True)

        self.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.bind("<Button-5>", lambda e: self.canvas.yview_scroll(1, "units"))
        self.bind("1", lambda e: self._select_mode("casual"))
        self.bind("2", lambda e: self._select_mode("betting"))
        self.bind("3", lambda e: self._select_mode("training"))
        self.bind("<Return>", lambda e: self._on_confirm())
        self.bind("<Escape>", lambda e: self._on_close())

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.focus_set()

    def _on_scroll_update(self, first, last):
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack_forget()
        else:
            if not self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        if hasattr(self, "canvas") and self.canvas.winfo_exists():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _build_ui(self):
        # 1. Retro Pixel Art Logo
        scale = getattr(self.app, "scale_factor", 1.0)
        logo_file = "pixel_logo_blackjack_2x.png" if scale > 1.5 else "pixel_logo_blackjack.png"
        logo_path = ASSETS_EXTRA_DIR / logo_file
        if not logo_path.exists():
            logo_path = ASSETS_EXTRA_DIR / "pixel_logo_blackjack.png"

        self._logo_photo = None
        if logo_path.exists() and Image is not None and ImageTk is not None:
            try:
                pil_logo = Image.open(logo_path)
                self._logo_photo = ImageTk.PhotoImage(pil_logo)
                logo_lbl = tkinter.Label(
                    self.scroll_content, image=self._logo_photo, background=PANEL_BACKGROUND_COLOR
                )
                logo_lbl.pack(pady=(0, 6))
            except Exception:
                self._logo_photo = None

        if self._logo_photo is None:
            tkinter.Label(
                self.scroll_content,
                text="♠  B L A C K J A C K  ♥",
                font=get_element_font("dialog_title"),
                fg="#ffd700",
                background=PANEL_BACKGROUND_COLOR,
            ).pack(pady=(0, 6))

        # 2. Dealer Greeting Banner
        dealer_photo = None
        dealer_name = "Tiffany"
        dealer_title = "The Velvet Croupier"
        if hasattr(self.app, "dealer_actor") and self.app.dealer_actor:
            try:
                profile = self.app.dealer_actor.get_profile()
                if profile:
                    dealer_name = profile.name
                    dealer_title = profile.title
                dealer_photo = self.app.dealer_actor.get_bust_photo_image(scale_factor=1.0)
            except Exception:
                pass
        if dealer_photo is None and hasattr(self.app, "haunted_assets"):
            dealer_photo = self.app.haunted_assets.get("dealer_classic")

        dealer_banner = tkinter.Frame(
            self.scroll_content, background="#072b17", relief="ridge", borderwidth=1,
            highlightbackground="#ffd700", highlightthickness=1, padx=10, pady=6
        )
        dealer_banner.pack(fill="x", pady=(0, 6))

        if dealer_photo:
            self._dealer_photo_ref = dealer_photo
            avatar_lbl = tkinter.Label(dealer_banner, image=dealer_photo, background="#072b17")
            avatar_lbl.pack(side="left", padx=(2, 10), pady=2)

        text_box = tkinter.Frame(dealer_banner, background="#072b17")
        text_box.pack(side="left", fill="both", expand=True)

        name_lbl = tkinter.Label(
            text_box, text=f"♠ {dealer_name} — {dealer_title}",
            font=get_header_font(18), fg="#ffd700", background="#072b17", anchor="w"
        )
        name_lbl.pack(anchor="w", pady=(0, 2))

        speech_lbl = tkinter.Label(
            text_box,
            text=(
                "Welcome to the table! How would you like to play today?\n"
                "Select your preferred table experience below — you can change your mode "
                "anytime in Settings (F2) or with Shift+M."
            ),
            font=get_body_font(16), fg="#e0f2f1", background="#072b17", justify="left",
            anchor="w", wraplength=560
        )
        speech_lbl.pack(anchor="w")

        # 3. Interactive Play Mode Cards (Vertical Stack for display fit resilience)
        modes_spec = [
            (
                "casual",
                "1",
                "🃏 Casual Mode (No Betting)",
                "Pure card play & relaxation",
                [
                    "• Deal hands immediately with zero bankroll pressure or wagering",
                    "• Full standard Blackjack rules: Hit, Stand, Double, Split, Surrender",
                    "• Perfect for quick, stress-free hands and pure card fun",
                ],
                "#10b981",  # Emerald Green
            ),
            (
                "betting",
                "2",
                "💰 Casino Betting Mode",
                "Authentic bankroll stakes & Hall of Fame records",
                [
                    "• Start with $1,000 bankroll and 5 authentic casino chip denominations",
                    "• Interactive 2.5D chip visualizer with animated betting spot & rakes",
                    "• Full wagering features: Insurance, peak bankroll & Hall of Fame",
                ],
                "#f59e0b",  # Vegas Gold
            ),
            (
                "training",
                "3",
                "🧠 Strategy & Counting Trainer",
                "MIT Hi-Lo Counting Bootcamp + 3-Seat Wagering & Count HUD",
                [
                    "• Interactive 14-Node MIT Hi-Lo Counting Bootcamp (Lectures & Drills)",
                    "• Full 3-Seat Wagering baize with multi-hand bet spreading practice",
                    "• Real-time Hi-Lo Running Count, Decks Remaining & True Count HUD",
                    "• Dynamic Ideal Bet Sizing & Basic Strategy hints for every hand",
                ],
                "#00e5ff",  # Cyan
            ),
        ]

        for mode_id, key_str, title_text, subtitle_text, bullets, accent_col in modes_spec:
            card_f = tkinter.Frame(
                self.scroll_content,
                background="#081f14",
                relief="ridge",
                borderwidth=2,
                highlightthickness=2,
                highlightbackground="#1a402d",
                padx=10,
                pady=5,
                cursor="hand2",
            )
            card_f.pack(fill="x", pady=2)

            # Header row
            hdr_row = tkinter.Frame(card_f, background="#081f14", cursor="hand2")
            hdr_row.pack(fill="x")

            key_lbl = tkinter.Label(
                hdr_row, text=f"[{key_str}]", font=get_button_font(15),
                fg="#b0bec5", background="#1b382b", padx=6, pady=1, relief="ridge", borderwidth=1
            )
            key_lbl.pack(side="left", padx=(0, 6))

            title_lbl = tkinter.Label(
                hdr_row, text=title_text, font=get_header_font(18),
                fg=accent_col, background="#081f14", cursor="hand2"
            )
            title_lbl.pack(side="left")

            badge_lbl = tkinter.Label(
                hdr_row, text=f"Press [{key_str}] or Click", font=get_badge_font(15),
                fg="#78909c", background="#081f14", cursor="hand2"
            )
            badge_lbl.pack(side="right")

            # Subtitle
            sub_lbl = tkinter.Label(
                card_f, text=subtitle_text, font=get_body_font(16),
                fg="#b2dfdb", background="#081f14", anchor="w", cursor="hand2"
            )
            sub_lbl.pack(fill="x", pady=(1, 2))

            # Bullet points
            bullet_labels = []
            for bp in bullets:
                b_lbl = tkinter.Label(
                    card_f, text=bp, font=get_body_font(16),
                    fg="#cfd8dc", background="#081f14", anchor="w", cursor="hand2"
                )
                b_lbl.pack(fill="x", pady=0)
                bullet_labels.append(b_lbl)

            sync_widgets = [hdr_row, title_lbl, badge_lbl, sub_lbl] + bullet_labels
            self._mode_cards[mode_id] = {
                "frame": card_f,
                "badge": badge_lbl,
                "key_btn": key_lbl,
                "accent": accent_col,
                "key": key_str,
                "sync_widgets": sync_widgets,
            }

            # Click binding across entire card and children
            for w in [card_f, hdr_row, key_lbl, title_lbl, badge_lbl, sub_lbl] + bullet_labels:
                w.bind("<Button-1>", lambda e, m=mode_id: self._select_mode(m))

        # Initial selection visual state
        self._select_mode(self.selected_mode)

        # 4. Remember Preference Checkbox
        remember_chk = tkinter.Checkbutton(
            self.scroll_content,
            text="Remember my preference (don't show again on startup; can reopen anytime in Settings)",
            variable=self.remember_var,
            font=get_body_font(16),
            fg="#cfd8dc",
            background=PANEL_BACKGROUND_COLOR,
            selectcolor="#004d40",
            activebackground=PANEL_BACKGROUND_COLOR,
            activeforeground="#ffffff",
            cursor="hand2",
        )
        remember_chk.pack(pady=(4, 6))

        # 5. Action Controls Row
        action_row = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        action_row.pack(fill="x", pady=(2, 2))
        action_row.columnconfigure(0, weight=1)
        action_row.columnconfigure(1, weight=1)

        self.confirm_btn = tkinter.Button(
            action_row,
            text="Take My Seat & Play (Enter)",
            font=get_button_font(16),
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            command=self._on_confirm,
            padx=16,
            pady=5,
        )
        self.confirm_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        self.cancel_btn = tkinter.Button(
            action_row,
            text="Skip (Current Settings)",
            font=get_button_font(16),
            background="#37474f",
            fg="#cfd8dc",
            activebackground="#455a64",
            activeforeground="#ffffff",
            relief="ridge",
            borderwidth=1,
            cursor="hand2",
            command=self._on_close,
            padx=12,
            pady=5,
        )
        self.cancel_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

    def _select_mode(self, mode: str):
        """Highlights the selected mode card and updates internal choice."""
        if mode not in self._mode_cards:
            return
        self.selected_mode = mode
        for m_id, card in self._mode_cards.items():
            is_sel = (m_id == mode)
            bg_col = "#0f3826" if is_sel else "#081f14"
            border_col = card["accent"] if is_sel else "#1a402d"
            card["frame"].configure(background=bg_col, highlightbackground=border_col)
            for w in card["sync_widgets"]:
                w.configure(background=bg_col)
            if is_sel:
                card["badge"].configure(text="✓ SELECTED", fg="#00e676", font=get_badge_font(15))
                card["key_btn"].configure(background=card["accent"], fg="#000000")
            else:
                card["badge"].configure(text=f"Press [{card['key']}] or Click", fg="#78909c", font=get_badge_font(15))
                card["key_btn"].configure(background="#1b382b", fg="#b0bec5")

    def _on_confirm(self):
        """Applies mode choice, optionally saves onboarding completion, and dismisses modal."""
        mode = self.selected_mode
        if self.remember_var.get():
            if hasattr(self.app, "save_manager") and self.app.save_manager:
                self.app.save_manager.complete_onboarding()
        if mode == "training" and hasattr(self.app, "activate_training_mode_entry"):
            self._on_close()
            self.app.activate_training_mode_entry(sync_save=True)
            return
        if hasattr(self.app, "set_table_seats"):
            if mode == "training":
                self.app.set_table_seats(3)
            else:
                self.app.set_table_seats(1)
        if hasattr(self.app, "apply_play_mode"):
            self.app.apply_play_mode(mode)
        if self.on_confirm_cb:
            try:
                self.on_confirm_cb(mode)
            except Exception:
                pass
        self._on_close()

    def _on_close(self, event=None):
        try:
            self.destroy()
        except Exception:
            pass
        return "break"


# ============================================================================
# 7. TripometerDialog (Persistent Strategy Tripometer & 50-Hand Audit Log)
# ============================================================================

class TripometerDialog(tkinter.Toplevel):
    """
    Modal Strategy Tripometer & Hand Review overlay.
    Displays Hands Since Reset, Net Trip P&L, 3 independent skill grade plaques
    (Basic Strategy, Illustrious 18, Kelly Bet Sizing), an All Hands / Mistakes Only
    filter bar, and the 50-hand rolling audit log using crisp native-grid pixel fonts.
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
        super().__init__(parent)
        self.app = app
        self.filter_mode: str = "all"  # "all" | "mistakes"
        self._rendered_hand_frames: list[tkinter.Frame] = []

        self.title("Strategy Tripometer & Hand Review")
        self.configure(background=PANEL_BACKGROUND_COLOR)
        self.resizable(False, False)
        self.transient(parent)
        if hasattr(app, "_icon_photo") and app._icon_photo is not None:
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        target_w, target_h = 820, 640
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            screen_w = parent.winfo_screenwidth()
            screen_h = parent.winfo_screenheight()
            scale = getattr(app, "scale_factor", 1.0)
            cfg_max_h = int(config.DEFAULT_WINDOW_HEIGHT * scale)
            dialog_w = min(target_w, max(640, screen_w - 40))
            dialog_h = min(target_h, max(420, min(screen_h - 80, cfg_max_h)))
            x = max(0, root_x + (root_w - dialog_w) // 2)
            y = max(0, root_y + (root_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{target_w}x{target_h}")

        # Persistent Header (crisp BoldPixels title + m6x11plus 16px subtitle, zero synthetic bold)
        header_bar = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR, padx=18, pady=8)
        header_bar.pack(side="top", fill="x")

        tkinter.Label(
            header_bar,
            text="STRATEGY TRIPOMETER & HAND REVIEW",
            font=get_title_font(28),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).pack(anchor="center")

        self.subtitle_lbl = tkinter.Label(
            header_bar,
            text="",
            font=get_header_font(16),
            fg="#80cbc4",
            background=PANEL_BACKGROUND_COLOR,
        )
        self.subtitle_lbl.pack(anchor="center", pady=(2, 0))

        # Persistent Bottom Footer: Green Done + Red Reset Trip (confirmation-guarded)
        footer_row = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR, padx=18, pady=8)
        footer_row.pack(side="bottom", fill="x")
        footer_row.columnconfigure(0, weight=1, uniform="trip_footer")
        footer_row.columnconfigure(1, weight=1, uniform="trip_footer")

        self.done_btn = tkinter.Button(
            footer_row,
            text="Done (Esc)",
            font=get_button_font(16),
            background="#2e7d32",
            fg="#ffffff",
            activebackground="#388e3c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._on_close,
        )
        self.done_btn.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.reset_trip_btn = tkinter.Button(
            footer_row,
            text="Reset Trip Stats",
            font=get_button_font(16),
            background="#b71c1c",
            fg="#ffffff",
            activebackground="#d32f2f",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2,
            cursor="hand2",
            padx=14,
            pady=6,
            command=self._on_click_reset_trip,
        )
        self.reset_trip_btn.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # Adaptive Scroll Container
        self.canvas = tkinter.Canvas(
            self,
            background=PANEL_BACKGROUND_COLOR,
            highlightthickness=0,
            borderwidth=0,
            height=220,
        )
        self.v_scrollbar = tkinter.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scroll_content = tkinter.Frame(self.canvas, background=PANEL_BACKGROUND_COLOR, padx=18, pady=6)
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
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        self._render_tripometer_contents()
        self.focus_set()

    def _on_scroll_update(self, first: Any, last: Any) -> None:
        self.v_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack_forget()
        else:
            if not self.v_scrollbar.winfo_ismapped():
                self.v_scrollbar.pack(side="right", fill="y")

    def _on_frame_configure(self, event: Any) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event: Any) -> None:
        self.canvas.itemconfig(self.canvas_window, width=event.width)

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

    def _render_tripometer_contents(self) -> None:
        for child in self.scroll_content.winfo_children():
            child.destroy()
        self._rendered_hand_frames = []

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

        # 1. Trip Summary Strip (Hands Since Reset & Net Trip P&L)
        top_strip = tkinter.Frame(
            self.scroll_content,
            background="#082415",
            highlightbackground="#d4af37",
            highlightthickness=1,
            padx=14,
            pady=8,
        )
        top_strip.pack(fill="x", pady=(0, 10))
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
            font=get_header_font(18),
            fg="#ffffff",
            background="#082415",
        ).grid(row=0, column=0, sticky="w")

        tkinter.Label(
            top_strip,
            text=f"Net Trip P&L: {pnl_str}",
            font=get_header_font(18),
            fg=pnl_col,
            background="#082415",
        ).grid(row=0, column=1, sticky="e")

        # 2. Three Independent Skill Grade Plaques
        plaques_row = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        plaques_row.pack(fill="x", pady=(0, 12))
        for col in range(3):
            plaques_row.columnconfigure(col, weight=1, uniform="trip_plaques")

        plaque_specs = [
            ("BASIC STRATEGY", summary["bs_pct"], summary["bs_optimal"], summary["bs_total"], "decisions"),
            ("ILLUSTRIOUS 18", summary["i18_pct"], summary["i18_optimal"], summary["i18_opportunities"], "index spots"),
            ("KELLY BET SIZING", summary["kelly_pct"], summary["kelly_optimal"], summary["kelly_total"], "rounds"),
        ]
        for idx, (title, pct, opt, tot, unit_lbl) in enumerate(plaque_specs):
            letter, col_hex = self._grade_letter_and_color(pct)
            border_hex = "#d4af37" if letter in ("S", "A") else col_hex
            card = tkinter.Frame(
                plaques_row,
                background="#0b2919",
                highlightbackground=border_hex,
                highlightthickness=1,
                padx=8,
                pady=8,
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=4)

            tkinter.Label(
                card,
                text=title,
                font=get_header_font(16),
                fg="#ffd700",
                background="#0b2919",
            ).pack(anchor="center")

            hero_row = tkinter.Frame(card, background="#0b2919")
            hero_row.pack(anchor="center", pady=(4, 2))

            chip_canvas = tkinter.Canvas(
                hero_row,
                width=88,
                height=62,
                background="#0b2919",
                highlightthickness=0,
                borderwidth=0,
            )
            chip_canvas.pack(side="left", padx=(0, 8))
            draw_25d_grade_medallion(
                chip_canvas,
                x=42,
                y=25,
                grade=letter,
                scale=1.22,
            )

            pct_str = f"{pct:.1f}%" if pct is not None else "N/A"
            tkinter.Label(
                hero_row,
                text=pct_str,
                font=get_display_font(32),
                fg=col_hex,
                background="#0b2919",
            ).pack(side="left")

            sub_str = f"{opt:,} / {tot:,} {unit_lbl}" if tot > 0 else f"0 {unit_lbl}"
            tkinter.Label(
                card,
                text=sub_str,
                font=get_header_font(16),
                fg="#cfd8dc",
                background="#0b2919",
            ).pack(anchor="center")

        # 3. Audit Log Header + Filter Controls (All Hands | Mistakes Only)
        recent_hands = list(tracker.data.recent_hands) if tracker is not None else []
        mistake_hands = [r for r in recent_hands if r.has_mistake]

        filter_bar = tkinter.Frame(self.scroll_content, background=PANEL_BACKGROUND_COLOR)
        filter_bar.pack(fill="x", pady=(0, 6))
        filter_bar.columnconfigure(0, weight=1)

        tkinter.Label(
            filter_bar,
            text="RECENT 50-HAND AUDIT LOG",
            font=get_header_font(16),
            fg="#ffd700",
            background=PANEL_BACKGROUND_COLOR,
        ).grid(row=0, column=0, sticky="w")

        btn_strip = tkinter.Frame(filter_bar, background=PANEL_BACKGROUND_COLOR)
        btn_strip.grid(row=0, column=1, sticky="e")

        is_all = self.filter_mode == "all"
        self.filter_all_btn = tkinter.Button(
            btn_strip,
            text=f"[1] All Hands ({len(recent_hands)})",
            font=get_button_font(16),
            background="#1b5e20" if is_all else "#0b2919",
            fg="#ffd700" if is_all else "#cfd8dc",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            relief="sunken" if is_all else "ridge",
            borderwidth=1,
            cursor="hand2",
            padx=12,
            pady=3,
            command=lambda: self._set_filter_mode("all"),
        )
        self.filter_all_btn.grid(row=0, column=0, padx=(0, 6))

        self.filter_mistakes_btn = tkinter.Button(
            btn_strip,
            text=f"[2] Mistakes Only ({len(mistake_hands)})",
            font=get_button_font(16),
            background="#7f1d1d" if not is_all else "#0b2919",
            fg="#ffd54f" if not is_all else "#cfd8dc",
            activebackground="#991b1b",
            activeforeground="#ffffff",
            relief="sunken" if not is_all else "ridge",
            borderwidth=1,
            cursor="hand2",
            padx=12,
            pady=3,
            command=lambda: self._set_filter_mode("mistakes"),
        )
        self.filter_mistakes_btn.grid(row=0, column=1)

        # 4. 50-Hand Rolling Audit Cards
        audit_box = tkinter.Frame(
            self.scroll_content,
            background=PANEL_BACKGROUND_COLOR,
        )
        audit_box.pack(fill="x", pady=(0, 4))

        displayed_hands = recent_hands if is_all else mistake_hands
        if not recent_hands:
            empty_card = tkinter.Frame(
                audit_box,
                background="#092114",
                highlightbackground="#1f5736",
                highlightthickness=1,
                padx=14,
                pady=12,
            )
            empty_card.pack(fill="x", pady=2)
            tkinter.Label(
                empty_card,
                text="No hands recorded since reset. Play a round to see strategy, index, and bet-sizing feedback.",
                font=get_header_font(16),
                fg="#b0bec5",
                background="#092114",
                anchor="w",
            ).pack(fill="x")
        elif not displayed_hands:
            clean_card = tkinter.Frame(
                audit_box,
                background="#092114",
                highlightbackground="#2e7d32",
                highlightthickness=1,
                padx=14,
                pady=12,
            )
            clean_card.pack(fill="x", pady=2)
            tkinter.Label(
                clean_card,
                text="[OK] Flawless play! Zero Basic Strategy, Illustrious 18, or Kelly bet-sizing mistakes in recent hands.",
                font=get_header_font(16),
                fg="#69f0ae",
                background="#092114",
                anchor="w",
            ).pack(fill="x")
        else:
            for idx, rec in enumerate(displayed_hands, start=1):
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
                    highlightthickness=1,
                    padx=12,
                    pady=8,
                )
                row_frame.pack(fill="x", pady=3)
                self._rendered_hand_frames.append(row_frame)

                # Row 1: Hand # + Rules Badge + True Count (Left) | Outcome + Net P&L (Right)
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
                    font=get_header_font(16),
                    fg="#ffd54f" if rec.ungraded_reason is None else "#9fa8da",
                    background=row_bg,
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                outcome_badge, outcome_col = self._format_outcome_badge(rec.outcome, rec.net_profit)
                tkinter.Label(
                    top_row,
                    text=outcome_badge,
                    font=get_header_font(16),
                    fg=outcome_col,
                    background=row_bg,
                    anchor="e",
                ).grid(row=0, column=1, sticky="e")

                # Row 2: Player vs Dealer Cards (Left) | Wager & Kelly Evaluation (Right)
                mid_row = tkinter.Frame(row_frame, background=row_bg)
                mid_row.pack(fill="x", pady=(4, 3))
                mid_row.columnconfigure(0, weight=1)

                p_cards = " ".join(rec.player_cards) if rec.player_cards else "-"
                d_cards = " ".join(rec.dealer_cards) if rec.dealer_cards else "-"
                tkinter.Label(
                    mid_row,
                    text=f"Player: [ {p_cards} ]    vs    Dealer: [ {d_cards} ]",
                    font=get_header_font(16),
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
                    font=get_header_font(16),
                    fg=kelly_col,
                    background=row_bg,
                    anchor="e",
                ).grid(row=0, column=1, sticky="e")

                # Row 3+: Decision & Coaching Lines
                if not rec.decisions:
                    tkinter.Label(
                        row_frame,
                        text="Resolved on initial deal (no voluntary action required)",
                        font=get_header_font(16),
                        fg="#90a4ae",
                        background=row_bg,
                        anchor="w",
                    ).pack(fill="x", pady=(2, 0))
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

                        tkinter.Label(
                            row_frame,
                            text=step_txt,
                            font=get_header_font(16),
                            fg=step_col,
                            background=row_bg,
                            anchor="w",
                            justify="left",
                            wraplength=730,
                        ).pack(fill="x", pady=(2, 0))

        self._bind_mousewheel_recursive(self.scroll_content)
        try:
            self.scroll_content.update_idletasks()
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        except Exception:
            pass

    def _ask_confirm_reset_trip(self) -> bool:
        import tkinter.messagebox as msgbox

        return msgbox.askyesno(
            title="⚠️ Reset Strategy Tripometer?",
            message=(
                "Reset the Strategy Tripometer counters, Net Trip P&L, and 50-hand audit log?\n\n"
                "Your career bankroll, Hall of Fame records, Bootcamp badges, and unlocked costumes "
                "will NOT be affected."
            ),
            icon="warning",
            default="no",
            parent=self,
        )

    def _on_click_reset_trip(self) -> None:
        if not self._ask_confirm_reset_trip():
            return
        if hasattr(self.app, "tripometer") and self.app.tripometer is not None:
            self.app.tripometer.reset()
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
