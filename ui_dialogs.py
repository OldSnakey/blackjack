"""
Modal Dialogs and Toplevel Overlays for Blackjack.

Provides:
- StoryDialogueDialog: Atmospheric narrative story modal with speaker portraits.
- AngelicDraftDialog: Balatro-style Roguelike celestial blessing card drafting dialog.
- SettingsDialog: Preferences modal with audio/scaling toggles and save reset safety.
- ShortcutsDialog: Clean 2x2 categorized grid illustrating all keyboard & mouse controls.
"""

from __future__ import annotations

import tkinter
from typing import Any, Callable, List, Optional

from audio_assets import KeyboardIconLoader
from config import PANEL_BACKGROUND_COLOR
from haunted_manager import BLESSING_REGISTRY, Blessing


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
        self.transient(parent)
        self.resizable(False, False)

        bg_col = "#041421" if is_celestial else "#0d0204"
        border_col = "#00e5ff" if is_celestial else "#8b0000"
        header_col = "#80cbc4" if is_celestial else "#ff5252"
        btn_bg = "#00695c" if is_celestial else "#b71c1c"
        btn_active = "#00897b" if is_celestial else "#d32f2f"

        self.configure(background=bg_col, padx=14, pady=14)

        # Center relative to parent
        w, h = 540, 240
        try:
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
        except Exception:
            self.geometry(f"{w}x{h}")

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
            port_lbl.pack(side="left", padx=12, pady=10)
            self.portrait_label = port_lbl

        # Content container
        content_box = tkinter.Frame(frame, background=bg_col)
        content_box.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=10)

        tkinter.Label(
            content_box, text=speaker, font=("Arial", 11, "bold"),
            fg=header_col, background=bg_col
        ).pack(anchor="w")

        tkinter.Label(
            content_box, text=text_content, font=("Arial", 9),
            fg="#eceff1", background=bg_col, justify="left", wraplength=380
        ).pack(anchor="w", pady=(6, 12))

        btn = tkinter.Button(
            content_box, text=button_text, font=("Arial", 10, "bold"),
            background=btn_bg, foreground="#ffffff", activebackground=btn_active,
            activeforeground="#ffffff", relief="flat", borderwidth=0,
            highlightthickness=0, cursor="hand2", padx=16, pady=6,
            takefocus=False, command=self._dismiss
        )
        btn.pack(anchor="e")

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
        self.configure(background="#03101c", padx=16, pady=14)

        w, h = 680, 360
        try:
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{w}x{h}+{max(0, rx + (rw - w) // 2)}+{max(0, ry + (rh - h) // 2)}")
        except Exception:
            self.geometry(f"{w}x{h}")

        tkinter.Label(
            self, text="✦ CHOOSE YOUR CELESTIAL BLESSING ✦",
            font=("Arial", 13, "bold"), fg="#ffd700", background="#03101c"
        ).pack(pady=(0, 2))

        tkinter.Label(
            self, text="The Angel intervenes! Draft one divine relic to aid in the struggle for your soul.",
            font=("Arial", 9, "italic"), fg="#80cbc4", background="#03101c"
        ).pack(pady=(0, 12))

        cards_frame = tkinter.Frame(self, background="#03101c")
        cards_frame.pack(fill="both", expand=True)

        for blessing in choices:
            details = BLESSING_REGISTRY[blessing]
            card_f = tkinter.Frame(
                cards_frame, background="#051f38", relief="ridge", borderwidth=2,
                highlightbackground="#00e5ff", highlightthickness=1, padx=10, pady=8
            )
            card_f.pack(side="left", fill="both", expand=True, padx=5)

            icon = relic_icons.get(blessing.value)
            if icon:
                ilbl = tkinter.Label(card_f, image=icon, background="#051f38")
                ilbl.image = icon
                ilbl.pack(pady=(2, 4))

            tkinter.Label(
                card_f, text=details.title, font=("Arial", 10, "bold"),
                fg="#ffd700", background="#051f38"
            ).pack()

            tkinter.Label(
                card_f, text=details.tagline, font=("Arial", 8, "italic"),
                fg="#80cbc4", background="#051f38"
            ).pack(pady=(0, 4))

            tkinter.Label(
                card_f, text=details.description, font=("Arial", 8),
                fg="#eceff1", background="#051f38", justify="center", wraplength=170
            ).pack(fill="both", expand=True, pady=(0, 8))

            btn = tkinter.Button(
                card_f, text="Equip Relic", font=("Arial", 9, "bold"),
                background="#00838f", foreground="#ffffff", activebackground="#00acc1",
                activeforeground="#ffffff", relief="raised", borderwidth=2, cursor="hand2",
                command=lambda b=blessing: self._pick(b)
            )
            btn.pack(side="bottom", pady=4)

        self.protocol("WM_DELETE_WINDOW", lambda: None)  # Must draft a blessing to proceed

    def _pick(self, blessing: Blessing):
        try:
            self.destroy()
        except Exception:
            pass
        if self.on_select:
            self.on_select(blessing)


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

        dialog_w, dialog_h = 500, 470
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            screen_h = parent.winfo_screenheight()
            dialog_h = min(dialog_h, max(380, screen_h - 80))
            x = max(0, root_x + (root_w - dialog_w) // 2)
            y = max(0, root_y + (root_h - dialog_h) // 2)
            self.geometry(f"{dialog_w}x{dialog_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self.status_msg_var = tkinter.StringVar(value="All casino records active.")

        # Scrollable container setup
        self.canvas = tkinter.Canvas(
            self, background=PANEL_BACKGROUND_COLOR, highlightthickness=0, borderwidth=0
        )
        self.v_scrollbar = tkinter.Scrollbar(
            self, orient="vertical", command=self.canvas.yview
        )
        self.scroll_content = tkinter.Frame(self.canvas, background=PANEL_BACKGROUND_COLOR, padx=16, pady=12)

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

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
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
        # Header title
        header = tkinter.Label(
            self.scroll_content, text="⚙ CASINO SETTINGS & RECORDS",
            font=("Arial", 12, "bold"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        )
        header.pack(pady=(0, 8))

        # Audio & Display Controls Frame (Two-Tier Layout)
        ctrl_frame = tkinter.LabelFrame(
            self.scroll_content, text=" Table Preferences ", font=("Arial", 10, "bold"),
            fg="#80cbc4", background=PANEL_BACKGROUND_COLOR, padx=12, pady=8
        )
        ctrl_frame.pack(fill="x", pady=(0, 10))

        # Tier 1: Audio & Dialogue
        tier1_lbl = tkinter.Label(
            ctrl_frame, text="Audio & Dialogue:", font=("Arial", 8, "italic"),
            fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR
        )
        tier1_lbl.pack(anchor="w", pady=(0, 2))

        audio_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        audio_row.pack(fill="x", pady=(0, 6))
        audio_row.columnconfigure(0, weight=1)
        audio_row.columnconfigure(1, weight=1)

        self.sound_btn = tkinter.Button(
            audio_row, textvariable=self.app.sound_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_sound,
            padx=10, pady=4
        )
        self.sound_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))

        if hasattr(self.app, "voice_status_var"):
            self.voice_btn = tkinter.Button(
                audio_row, textvariable=self.app.voice_status_var, font=("Arial", 9, "bold"),
                background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
                relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_voice,
                padx=10, pady=4
            )
            self.voice_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))

        # Tier 2: Display & Customization
        tier2_lbl = tkinter.Label(
            ctrl_frame, text="Display & Customization:", font=("Arial", 8, "italic"),
            fg="#b2dfdb", background=PANEL_BACKGROUND_COLOR
        )
        tier2_lbl.pack(anchor="w", pady=(2, 2))

        disp_row = tkinter.Frame(ctrl_frame, background=PANEL_BACKGROUND_COLOR)
        disp_row.pack(fill="x", pady=(0, 2))
        disp_row.columnconfigure(0, weight=1)
        disp_row.columnconfigure(1, weight=1)
        disp_row.columnconfigure(2, weight=1)

        self.scale_btn = tkinter.Button(
            disp_row, textvariable=self.app.scale_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app.toggle_scale_mode,
            padx=8, pady=4
        )
        self.scale_btn.grid(row=0, column=0, sticky="ew", padx=(0, 3))

        self.dealer_btn = tkinter.Button(
            disp_row, textvariable=self.app.dealer_view_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_dealer_view,
            padx=8, pady=4
        )
        self.dealer_btn.grid(row=0, column=1, sticky="ew", padx=3)

        self.wardrobe_btn = tkinter.Button(
            disp_row, text="🎩 Wardrobe", font=("Arial", 9, "bold"),
            background="#1b5e20", fg="white", activebackground="#2e7d32", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._open_wardrobe_dialog,
            padx=8, pady=4
        )
        self.wardrobe_btn.grid(row=0, column=2, sticky="ew", padx=(3, 0))

        # Save Data Management Frame
        save_frame = tkinter.LabelFrame(
            self.scroll_content, text=" Save Data & Hall of Fame Records ", font=("Arial", 10, "bold"),
            fg="#ffd700", background=PANEL_BACKGROUND_COLOR, padx=12, pady=8
        )
        save_frame.pack(fill="x", pady=(0, 8))

        # Stats labels
        self.stats_frame = tkinter.Frame(save_frame, background=PANEL_BACKGROUND_COLOR)
        self.stats_frame.pack(fill="x", pady=(0, 6))

        self.lbl_peak = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_peak.pack(fill="x", pady=1)

        self.lbl_hands = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_hands.pack(fill="x", pady=1)

        self.lbl_counting = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_counting.pack(fill="x", pady=1)

        self.lbl_exorcist = tkinter.Label(
            self.stats_frame, text="", font=("Arial", 9),
            fg="#e0e0e0", background=PANEL_BACKGROUND_COLOR, anchor="w"
        )
        self.lbl_exorcist.pack(fill="x", pady=1)

        self._refresh_stats_display()

        # Status feedback label
        lbl_status = tkinter.Label(
            save_frame, textvariable=self.status_msg_var, font=("Arial", 9, "italic"),
            fg="#ffeb3b", background=PANEL_BACKGROUND_COLOR
        )
        lbl_status.pack(pady=(2, 6))

        # Clear Save File Button
        self.clear_save_btn = tkinter.Button(
            save_frame, text="🗑 Clear Save File (Reset to Blank Slate)",
            font=("Arial", 10, "bold"), background="#b71c1c", fg="#ffffff",
            activebackground="#d32f2f", activeforeground="#ffffff",
            relief="raised", borderwidth=2, cursor="hand2",
            command=self._on_click_clear_save
        )
        self.clear_save_btn.pack(fill="x", pady=2)

        # Close Button
        close_btn = tkinter.Button(
            self.scroll_content, text="Close", font=("Arial", 10, "bold"),
            background="#37474f", fg="white", activebackground="#455a64",
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_close
        )
        close_btn.pack(pady=(4, 0))

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
        self._refresh_stats_display()
        self.status_msg_var.set("✓ Save file reset to initial blank slate.")

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

        dialog_w, dialog_h = 760, 550
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
            font=("Arial", 12, "bold"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="w")

        tkinter.Label(
            title_box, text="Full hands-free keyboard accessibility for authentic casino gameplay",
            font=("Arial", 8, "italic"), fg="#80cbc4", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="w")

        close_btn = tkinter.Button(
            header_frame, text="✕ Close (Esc)", font=("Arial", 9, "bold"),
            background="#c62828", foreground="#ffffff", activebackground="#e53935",
            activeforeground="#ffffff", relief="raised", borderwidth=1, cursor="hand2",
            takefocus=False, command=self._on_close
        )
        close_btn.pack(side="right")

        # 2. Tab Navigation Bar
        tab_nav = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        tab_nav.pack(fill="x", padx=14, pady=(2, 3))

        self.btn_tab_gameplay = tkinter.Button(
            tab_nav, text="🃏 Gameplay & Betting", font=("Arial", 9, "bold"),
            background="#2e7d32", fg="white", activebackground="#388e3c",
            activeforeground="white", relief="raised", borderwidth=2, cursor="hand2",
            padx=14, pady=3, command=lambda: self._switch_tab(0)
        )
        self.btn_tab_gameplay.pack(side="left", padx=(0, 8))

        self.btn_tab_system = tkinter.Button(
            tab_nav, text="⚙️ System & Controls", font=("Arial", 9, "bold"),
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
            panel.pack(fill="both", expand=True, padx=4, pady=2)
            tkinter.Label(
                panel, text=title_text, font=("Arial", 9, "bold"),
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
                        badges, text="or", font=("Arial", 8, "bold"),
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
                        badges, text=f"[{disp}]", font=("Consolas", 8, "bold"),
                        background="#ffffff", foreground="#000000",
                        padx=3, pady=1, relief="raised", bd=1
                    ).pack(side="left", padx=1)

            tkinter.Label(
                r, text=action_text, font=("Arial", 9, "bold"),
                fg="#ffffff", background="#053612"
            ).pack(side="left", padx=(6, 2))

            if hint_text:
                tkinter.Label(
                    r, text=hint_text, font=("Arial", 8),
                    fg="#a5d6a7", background="#053612"
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
        add_row(panel_betting, ["keyboard_a"], "All In", "(Wager entire bankroll)")
        add_row(panel_betting, ["keyboard_c"], "Clear Bet", "(Reset bet to $0)")

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
        add_row(panel_display, ["keyboard_shift", "keyboard_s"], "Scale 1x / 2x", "(Shift+S or F10)")
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
            font=("Arial", 8, "italic"), fg="#ffe082", background=PANEL_BACKGROUND_COLOR
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
