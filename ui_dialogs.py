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
    """

    def __init__(self, parent: tkinter.Tk, app: Any):
        super().__init__(parent)
        self.app = app
        self.title("⚙ Settings & Casino Records")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background=PANEL_BACKGROUND_COLOR, padx=16, pady=14)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        dialog_w, dialog_h = 460, 440
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

        self.status_msg_var = tkinter.StringVar(value="All casino records active.")
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.focus_set()

    def _build_ui(self):
        # Header title
        header = tkinter.Label(
            self, text="⚙ CASINO SETTINGS & RECORDS",
            font=("Arial", 12, "bold"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
        )
        header.pack(pady=(0, 10))

        # Audio & Display Controls Frame
        ctrl_frame = tkinter.LabelFrame(
            self, text=" Table Preferences ", font=("Arial", 10, "bold"),
            fg="#80cbc4", background=PANEL_BACKGROUND_COLOR, padx=10, pady=8
        )
        ctrl_frame.pack(fill="x", pady=(0, 12))

        # Sound button
        self.sound_btn = tkinter.Button(
            ctrl_frame, textvariable=self.app.sound_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_sound
        )
        self.sound_btn.pack(side="left", padx=(0, 6), expand=True, fill="x")

        # Scale button
        self.scale_btn = tkinter.Button(
            ctrl_frame, textvariable=self.app.scale_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app.toggle_scale_mode
        )
        self.scale_btn.pack(side="left", padx=6, expand=True, fill="x")

        # Dealer view button
        self.dealer_btn = tkinter.Button(
            ctrl_frame, textvariable=self.app.dealer_view_status_var, font=("Arial", 9, "bold"),
            background="#004d40", fg="white", activebackground="#00695c", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._on_toggle_dealer_view
        )
        self.dealer_btn.pack(side="left", padx=6, expand=True, fill="x")

        # Dealer wardrobe button
        self.wardrobe_btn = tkinter.Button(
            ctrl_frame, text="🎩 Wardrobe", font=("Arial", 9, "bold"),
            background="#1b5e20", fg="white", activebackground="#2e7d32", activeforeground="white",
            relief="ridge", borderwidth=1, cursor="hand2", command=self.app._open_wardrobe_dialog
        )
        self.wardrobe_btn.pack(side="left", padx=(6, 0), expand=True, fill="x")

        # Save Data Management Frame
        save_frame = tkinter.LabelFrame(
            self, text=" Save Data & Hall of Fame Records ", font=("Arial", 10, "bold"),
            fg="#ffd700", background=PANEL_BACKGROUND_COLOR, padx=12, pady=10
        )
        save_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Stats labels
        self.stats_frame = tkinter.Frame(save_frame, background=PANEL_BACKGROUND_COLOR)
        self.stats_frame.pack(fill="x", pady=(0, 8))

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
        lbl_status.pack(pady=(4, 8))

        # Clear Save File Button
        self.clear_save_btn = tkinter.Button(
            save_frame, text="🗑 Clear Save File (Reset to Blank Slate)",
            font=("Arial", 10, "bold"), background="#b71c1c", fg="#ffffff",
            activebackground="#d32f2f", activeforeground="#ffffff",
            relief="raised", borderwidth=2, cursor="hand2",
            command=self._on_click_clear_save
        )
        self.clear_save_btn.pack(fill="x", pady=4)

        # Close Button
        close_btn = tkinter.Button(
            self, text="Close", font=("Arial", 10, "bold"),
            background="#37474f", fg="white", activebackground="#455a64",
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_close
        )
        close_btn.pack(pady=(4, 0))

    def _refresh_stats_display(self):
        """Refreshes the high scores and achievement badges displayed in the dialog."""
        data = self.app.save_manager.data
        self.lbl_peak.configure(
            text=f"• All-Time Peak Bankroll: ${data.highscores.peak_bankroll:,}"
        )
        self.lbl_hands.configure(
            text=f"• Hands Won / Played: {data.highscores.total_hands_won:,} / {data.highscores.total_hands_played:,}  (Blackjacks: {data.highscores.total_blackjacks:,})"
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
    Extracted from BlackjackApp for modularity, clean Toplevel lifecycle, and testability.
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
        self.configure(background=PANEL_BACKGROUND_COLOR, padx=14, pady=12)

        if icon_photo:
            try:
                self.iconphoto(False, icon_photo)
            except Exception:
                pass

        # Center dialog relative to main window
        dialog_w, dialog_h = 740, 530
        try:
            root_x = parent.winfo_rootx()
            root_y = parent.winfo_rooty()
            root_w = parent.winfo_width()
            root_h = parent.winfo_height()
            pos_x = max(root_x + (root_w - dialog_w) // 2, 0)
            pos_y = max(root_y + (root_h - dialog_h) // 2, 0)
            self.geometry(f"{dialog_w}x{dialog_h}+{pos_x}+{pos_y}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self._build_ui()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", self._on_close)
        self.focus_set()

    def _build_ui(self):
        # Top Header Bar
        header_frame = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        header_frame.pack(fill="x", pady=(0, 10))

        q_icon = self.icon_loader.get_icon("keyboard_question", scale_div=2)
        if q_icon:
            q_lbl = tkinter.Label(header_frame, image=q_icon, background=PANEL_BACKGROUND_COLOR)
            q_lbl.image = q_icon
            q_lbl.pack(side="left", padx=(0, 8))

        title_box = tkinter.Frame(header_frame, background=PANEL_BACKGROUND_COLOR)
        title_box.pack(side="left")

        tkinter.Label(
            title_box, text="KEYBOARD SHORTCUTS & CONTROLS",
            font=("Arial", 13, "bold"), fg="#ffd700", background=PANEL_BACKGROUND_COLOR
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

        # 2x2 Grid of Categorized Panels
        grid_frame = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        grid_frame.pack(fill="both", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)
        grid_frame.rowconfigure(0, weight=1)
        grid_frame.rowconfigure(1, weight=1)

        def make_panel(parent_f, title_text, row_idx, col_idx):
            panel = tkinter.Frame(
                parent_f, background="#053612", relief="ridge", borderwidth=2,
                padx=10, pady=8
            )
            panel.grid(row=row_idx, column=col_idx, sticky="nsew", padx=5, pady=5)
            tkinter.Label(
                panel, text=title_text, font=("Arial", 10, "bold"),
                fg="#ffeb3b", background="#053612"
            ).pack(anchor="w", pady=(0, 4))
            return panel

        def add_row(parent_panel, icon_names: list[str], action_text: str, hint_text: str = ""):
            r = tkinter.Frame(parent_panel, background="#053612")
            r.pack(fill="x", pady=2)

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

        # 1. Table Actions
        panel_actions = make_panel(grid_frame, "🃏 TABLE ACTIONS", 0, 0)
        add_row(panel_actions, ["keyboard_space", "keyboard_enter"], "Deal / Hit / Next", "(Context-sensitive)")
        add_row(panel_actions, ["keyboard_h"], "Hit", "(Draw another card)")
        add_row(panel_actions, ["keyboard_s"], "Stand", "(End turn, dealer plays)")
        add_row(panel_actions, ["keyboard_d"], "Double Down", "(Double bet, draw 1 card)")
        add_row(panel_actions, ["keyboard_p"], "Split Pair", "(Split equal rank cards)")
        add_row(panel_actions, ["keyboard_r"], "Surrender", "(Forfeit half bet before hitting)")

        # 2. Chips & Wagering
        panel_betting = make_panel(grid_frame, "💰 CHIPS & WAGERING", 0, 1)
        add_row(panel_betting, ["keyboard_1"], "Bet $5", "(White chip)")
        add_row(panel_betting, ["keyboard_2"], "Bet $25", "(Red chip)")
        add_row(panel_betting, ["keyboard_3"], "Bet $100", "(Green chip)")
        add_row(panel_betting, ["keyboard_4"], "Bet $500", "(Black & Gold chip)")
        add_row(panel_betting, ["keyboard_a"], "All In", "(Wager entire bankroll)")
        add_row(panel_betting, ["keyboard_c"], "Clear Bet", "(Reset bet to $0)")

        # 3. Insurance Phase
        panel_insurance = make_panel(grid_frame, "🛡️ INSURANCE DECISIONS", 1, 0)
        add_row(panel_insurance, ["keyboard_y"], "Take Insurance", "(Pays 2:1 on Dealer Ace)")
        add_row(panel_insurance, ["keyboard_n", "keyboard_escape"], "Decline", "(Decline side bet)")

        # 4. System & Controls
        panel_system = make_panel(grid_frame, "⚙️ SYSTEM & CONTROLS", 1, 1)
        add_row(panel_system, ["keyboard_m"], "Toggle Sound", "(Mute / Unmute)")
        add_row(panel_system, ["keyboard_f10"], "Scale 1x / 2x", "(Toggle High-DPI UI)")
        add_row(panel_system, ["keyboard_f11"], "Toggle Fullscreen", "(F11 or Escape to exit)")
        add_row(panel_system, ["keyboard_question", "keyboard_f1"], "Toggle Help", "(Show / Hide this overlay)")
        add_row(panel_system, ["mouse_left"], "Click Button / Chip", "(Direct mouse interaction)")

        # Footer Tip Banner
        footer_frame = tkinter.Frame(self, background=PANEL_BACKGROUND_COLOR)
        footer_frame.pack(fill="x", pady=(8, 0))

        tkinter.Label(
            footer_frame,
            text="💡 Tip: Keyboard shortcuts are context-sensitive and only activate when the corresponding button is enabled.",
            font=("Arial", 8, "italic"), fg="#ffe082", background=PANEL_BACKGROUND_COLOR
        ).pack(anchor="center")

    def _on_close(self, event=None):
        cb = self.on_close_cb
        try:
            self.destroy()
        except Exception:
            pass
        if cb:
            cb()
        return "break"
