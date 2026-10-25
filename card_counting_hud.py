"""
Card Counting Trainer HUD, Floating Card Tags, and Drill Challenge Modals.

Implements:
- CardCountingHud: Compact table felt HUD pill displaying Running Count,
  Estimated Decks Remaining, True Count, and Bet Sizing Guide.
- FloatingCountBadge: Lightweight transient tag particles (+1, -1, 0)
  spawning above dealt cards to train recognition.
- CardCountingQuizDialog: Interactive drill quiz to test counter discipline,
  streak tracking, and achievement unlocks.
"""

from __future__ import annotations

import tkinter
from typing import Any, Callable, Optional
from card_counter import HiLoCardCounter
from pixel_ui import (
    get_element_font,
    get_pixel_font,
    get_title_font,
    get_header_font,
    get_body_font,
    get_button_font,
    get_display_font,
    get_digital_font,
    get_badge_font,
)


class FloatingCountBadge(tkinter.Label):
    """
    Transient floating tag particle (+1, -1, 0) that briefly appears above
    dealt cards to provide visual feedback during card counting practice.
    """

    def __init__(self, master: tkinter.Misc, tag_value: int, duration_ms: int = 800, **kwargs):
        if tag_value > 0:
            text = f"+{tag_value}"
            fg_col = "#00e676"  # Emerald Green for positive tags (low cards removed)
        elif tag_value < 0:
            text = f"{tag_value}"
            fg_col = "#ff5252"  # Coral Red for negative tags (high cards removed)
        else:
            text = "0"
            fg_col = "#b0bec5"  # Slate Gray for neutral tags

        super().__init__(
            master,
            text=text,
            font=get_element_font("hilo_floating_badge"),
            fg=fg_col,
            background="#102027",
            padx=6,
            pady=2,
            relief="solid",
            borderwidth=1,
            highlightbackground=fg_col,
            highlightthickness=1,
            **kwargs,
        )
        self._timer_id: Optional[str] = None
        try:
            self._timer_id = self.after(duration_ms, self._safe_destroy)
        except Exception:
            pass

    def _safe_destroy(self):
        """Cancels any pending callback and removes widget."""
        if self._timer_id:
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None
        try:
            self.destroy()
        except Exception:
            pass


class CardCountingHud(tkinter.Frame):
    """
    Sleek casino table HUD pill displaying live Hi-Lo card counting statistics.
    Positioned on the felt below the dealer horizon rail.
    """

    def __init__(
        self,
        master: tkinter.Misc,
        counter: HiLoCardCounter,
        on_quiz_request: Optional[Callable[[], None]] = None,
        on_stage_bet_request: Optional[Callable[[int], None]] = None,
        use_grid: bool = False,
        grid_row: int = 2,
        **kwargs,
    ):
        # Determine background matching master if available
        bg_col = kwargs.pop("background", None) or kwargs.pop("bg", None)
        if not bg_col:
            try:
                bg_col = master.cget("background")
            except Exception:
                bg_col = "#082210"

        super().__init__(
            master,
            background=bg_col,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=0,
            pady=0,
            **kwargs,
        )
        self.counter = counter
        self.on_quiz_request = on_quiz_request
        self.on_stage_bet_request = on_stage_bet_request
        self.use_grid = use_grid
        self.grid_row = grid_row
        self.is_visible = False
        self.drill_mode = False
        self._last_rec_bet = 25
        self._last_cards_remaining = int(getattr(self.counter, "deck_count", 4)) * 52

        self._build_ui()

    def _build_ui(self):
        # 1. Top Tab Header Frame (sits on top of the HUD bar on the far left)
        self.tab_frame = tkinter.Frame(
            self,
            background="#141a1d",
            relief="ridge",
            borderwidth=1,
            highlightbackground="#2c3940",
            highlightthickness=1,
            padx=6,
            pady=1,
        )
        self.tab_frame.pack(side="top", anchor="w", padx=(6, 0), pady=(0, 0))

        self.title_lbl = tkinter.Label(
            self.tab_frame,
            text="🧮 Hi-Lo Trainer",
            font=get_element_font("hilo_trainer_title"),
            fg="#5ce6b5",
            background="#141a1d",
        )
        self.title_lbl.pack(side="left")

        # 2. Main HUD Statistics Bar Frame (Dark slate calculator gadget aesthetic)
        self.bar_frame = tkinter.Frame(
            self,
            background="#141a1d",
            relief="ridge",
            borderwidth=2,
            highlightbackground="#2c3940",
            highlightthickness=1,
            padx=6,
            pady=3,
        )
        self.bar_frame.pack(side="top", fill="x", expand=True, padx=0, pady=(0, 0))

        # Action Buttons (Packed side="right" first to guarantee they are never clipped)
        btn_font = get_element_font("hilo_trainer_button")
        self.close_btn = tkinter.Button(
            self.bar_frame,
            text="✖",
            font=btn_font,
            background="#141a1d",
            foreground="#80cbc4",
            activebackground="#263238",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            takefocus=False,
            command=self.toggle_visibility,
        )
        self.close_btn.pack(side="right", padx=(2, 4))

        self.quiz_btn = tkinter.Button(
            self.bar_frame,
            text="🎯 Quiz",
            font=btn_font,
            background="#1b2e2b",
            foreground="#ffd54f",
            activebackground="#263238",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=self._on_quiz_click,
        )
        self.quiz_btn.pack(side="right", padx=3)

        self.mode_btn = tkinter.Button(
            self.bar_frame,
            text="👁️ Assisted",
            font=btn_font,
            background="#1b2e2b",
            foreground="#5ce6b5",
            activebackground="#263238",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=lambda: self.toggle_drill_mode(self._last_cards_remaining),
        )
        self.mode_btn.pack(side="right", padx=3)

        # Statistics & Guidance (Packed side="left" with compact padding)
        f_lbl = get_element_font("hilo_trainer_label")
        f_val = get_element_font("hilo_trainer_value")

        # Running Count (RC)
        self.rc_frame = tkinter.Frame(self.bar_frame, background="#141a1d")
        self.rc_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.rc_frame, text="RC:", font=f_lbl, fg="#80cbc4", background="#141a1d"
        ).pack(side="left")
        self.rc_label = tkinter.Label(
            self.rc_frame, text="+0", font=f_val, fg="#ffffff", background="#141a1d"
        )
        self.rc_label.pack(side="left", padx=(2, 0))

        # Decks Remaining
        self.decks_frame = tkinter.Frame(self.bar_frame, background="#141a1d")
        self.decks_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.decks_frame, text="Decks:", font=f_lbl, fg="#80cbc4", background="#141a1d"
        ).pack(side="left")
        default_decks_text = f"{float(getattr(self.counter, 'deck_count', 4)):.1f}"
        self.decks_label = tkinter.Label(
            self.decks_frame, text=default_decks_text, font=f_val, fg="#ffffff", background="#141a1d"
        )
        self.decks_label.pack(side="left", padx=(2, 0))

        # True Count (TC)
        self.tc_frame = tkinter.Frame(self.bar_frame, background="#141a1d")
        self.tc_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.tc_frame, text="TC:", font=f_lbl, fg="#80cbc4", background="#141a1d"
        ).pack(side="left")
        self.tc_label = tkinter.Label(
            self.tc_frame, text="+0.0", font=f_val, fg="#ffffff", background="#141a1d"
        )
        self.tc_label.pack(side="left", padx=(2, 0))

        # Player Advantage (Edge %)
        self.edge_frame = tkinter.Frame(self.bar_frame, background="#141a1d")
        self.edge_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.edge_frame, text="Edge:", font=f_lbl, fg="#80cbc4", background="#141a1d"
        ).pack(side="left")
        self.edge_label = tkinter.Label(
            self.edge_frame, text="-0.5%", font=f_val, fg="#38bdf8", background="#141a1d"
        )
        self.edge_label.pack(side="left", padx=(2, 0))

        # Bet Sizing Guide
        self.bet_guide_frame = tkinter.Frame(self.bar_frame, background="#141a1d")
        self.bet_guide_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.bet_guide_frame, text="Bet Guide:", font=f_lbl, fg="#ffd54f", background="#141a1d"
        ).pack(side="left")
        self.bet_guide_label = tkinter.Label(
            self.bet_guide_frame, text="1u ($25)", font=f_val, fg="#fff59d", background="#141a1d",
            cursor="hand2"
        )
        self.bet_guide_label.pack(side="left", padx=(2, 0))
        self.bet_guide_label.bind("<Button-1>", lambda e: self._on_stage_bet_click())

        # Basic Strategy Advisor Hint
        self.strategy_frame = tkinter.Frame(self.bar_frame, background="#141a1d")
        self.strategy_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.strategy_frame, text="Strategy:", font=f_lbl, fg="#80cbc4", background="#141a1d"
        ).pack(side="left")
        self.strategy_label = tkinter.Label(
            self.strategy_frame, text="-", font=f_val, fg="#b0bec5", background="#141a1d"
        )
        self.strategy_label.pack(side="left", padx=(2, 0))

    def _on_quiz_click(self):
        if self.on_quiz_request:
            self.on_quiz_request()

    def _on_stage_bet_click(self):
        """Dispatches stage bet callback if registered."""
        if self.on_stage_bet_request:
            self.on_stage_bet_request(self._last_rec_bet)

    def set_visible(self, visible: bool) -> bool:
        """Explicitly sets HUD visibility state."""
        if self.is_visible != visible:
            self.toggle_visibility()
        return self.is_visible

    def toggle_visibility(self) -> bool:
        """Toggles visibility of the counting HUD pill."""
        if self.is_visible:
            if self.use_grid:
                self.grid_remove()
            else:
                self.pack_forget()
            self.is_visible = False
        else:
            if self.use_grid:
                self.grid(row=self.grid_row, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 4))
            else:
                self.pack(side="top", fill="x", padx=12, pady=(4, 4))
            self.is_visible = True
        return self.is_visible

    def update_strategy_hint(self, hint: Optional[Any] = None, text: Optional[str] = None):
        """
        Updates the Basic Strategy recommendation label with color-coded feedback.
        Supports BasicStrategyDecision dataclass or raw string text.
        """
        if not hasattr(self, "strategy_label") or not self.strategy_label.winfo_exists():
            return
        if text:
            display_text = text if len(text) <= 28 else text[:26] + "…"
            self.strategy_label.configure(text=display_text, fg="#ffffff")
            return
        if hint is None:
            self.strategy_label.configure(text="-", fg="#78909c")
            return

        action_name = getattr(hint, "action_name", None)
        if action_name is None:
            action_name = str(hint.action.value if hasattr(hint.action, "value") else hint.action)

        color_palette = {
            "HIT": "#4fc3f7",        # Sky Blue
            "STAND": "#ffb74d",      # Amber Orange
            "DOUBLE": "#69f0ae",     # Neon Emerald
            "SPLIT": "#ea80fc",      # Neon Violet
            "SURRENDER": "#ff5252",  # Vivid Coral
        }
        fg_col = color_palette.get(action_name, "#ffffff")
        reason = getattr(hint, "reason", "")
        display_text = f"{action_name} ({reason})" if reason else action_name
        if len(display_text) > 28:
            display_text = display_text[:26] + "…"
        self.strategy_label.configure(text=display_text, fg=fg_col)

    def set_drill_mode(self, enabled: bool, cards_remaining: int = 208, base_bet: int = 25) -> bool:
        """Sets Drill Challenge Mode (masks live RC/TC/Edge as '?' when enabled)."""
        self.drill_mode = bool(enabled)
        if hasattr(self, "mode_btn") and self.mode_btn.winfo_exists():
            if self.drill_mode:
                self.mode_btn.configure(text="🧠 Drill", foreground="#ffd54f", background="#3e2723")
            else:
                self.mode_btn.configure(text="👁️ Assisted", foreground="#80cbc4", background="#1b382d")
        self.update_counts(cards_remaining=cards_remaining, base_bet=base_bet)
        return self.drill_mode

    def toggle_drill_mode(self, cards_remaining: int = 208, base_bet: int = 25) -> bool:
        """Toggles between Assisted HUD Mode and Drill Challenge Mode."""
        return self.set_drill_mode(not self.drill_mode, cards_remaining=cards_remaining, base_bet=base_bet)

    def update_counts(self, cards_remaining: int, base_bet: int = 25):
        """Refreshes HUD count badges from internal counter state."""
        self._last_cards_remaining = cards_remaining
        rc = self.counter.running_count
        decks = self.counter.decks_remaining(cards_remaining)
        tc = self.counter.true_count(cards_remaining)
        adv = self.counter.get_player_advantage(cards_remaining)
        rec_bet = self.counter.get_recommended_bet(base_bet, tc)
        self._last_rec_bet = rec_bet
        rec_units = max(1, rec_bet // max(1, base_bet))

        # Decks remaining is always visible (visual shoe estimation)
        self.decks_label.configure(text=f"{decks:.1f}")

        if self.drill_mode:
            self.rc_label.configure(text="?", fg="#ffd54f")
            self.tc_label.configure(text="?", fg="#ffd54f")
            self.edge_label.configure(text="?", fg="#ffd54f")
            self.bet_guide_label.configure(text="? (Drill)")
            return

        # Format RC with explicit +/- sign
        rc_sign = "+" if rc > 0 else ""
        self.rc_label.configure(
            text=f"{rc_sign}{rc}",
            fg="#00e676" if rc > 0 else ("#ff5252" if rc < 0 else "#ffffff"),
        )

        # Format TC with explicit +/- sign
        tc_sign = "+" if tc > 0 else ""
        self.tc_label.configure(
            text=f"{tc_sign}{tc:.1f}",
            fg="#00e676" if tc >= 1.0 else ("#ff5252" if tc <= -1.0 else "#ffffff"),
        )

        # Format Player Advantage (Edge %) with roadmap color coding
        adv_sign = "+" if adv > 0 else ""
        edge_col = "#4ade80" if tc >= 2.0 else ("#f87171" if tc < -1.0 else "#38bdf8")
        self.edge_label.configure(
            text=f"{adv_sign}{adv:.1f}%",
            fg=edge_col,
        )

        # Bet Guide recommendation
        self.bet_guide_label.configure(text=f"{rec_units}u (${rec_bet})")


class CardCountingQuizDialog(tkinter.Toplevel):
    """
    Modal quiz dialog testing the player's card counting estimation.
    Tracks correct answer streaks and triggers achievement unlocks.
    """

    def __init__(
        self,
        parent: tkinter.Tk,
        counter: HiLoCardCounter,
        cards_remaining: int,
        on_result: Optional[Callable[[bool, int, float], None]] = None,
    ):
        super().__init__(parent)
        self.counter = counter
        self.cards_remaining = cards_remaining
        self.on_result = on_result

        self.title("🎯 Card Counting Drill Quiz")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#0a1a15", padx=16, pady=14)

        dialog_w, dialog_h = 420, 310
        try:
            rx = parent.winfo_rootx()
            ry = parent.winfo_rooty()
            rw = parent.winfo_width()
            rh = parent.winfo_height()
            self.geometry(f"{dialog_w}x{dialog_h}+{max(0, rx + (rw - dialog_w) // 2)}+{max(0, ry + (rh - dialog_h) // 2)}")
        except Exception:
            self.geometry(f"{dialog_w}x{dialog_h}")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.focus_set()

    def _build_ui(self):
        tkinter.Label(
            self,
            text="🎯 TEST YOUR COUNT",
            font=get_element_font("dialog_title"),
            fg="#ffd700",
            background="#0a1a15",
        ).pack(pady=(0, 8))

        tkinter.Label(
            self,
            text="Estimate the current Running Count and True Count from all revealed cards:",
            font=get_element_font("dialog_body"),
            fg="#eceff1",
            background="#0a1a15",
            wraplength=380,
            justify="center",
        ).pack(pady=(0, 12))

        input_frame = tkinter.Frame(self, background="#0a1a15")
        input_frame.pack(pady=4)

        # Running Count input
        tkinter.Label(
            input_frame, text="Running Count (RC):", font=get_element_font("dialog_badge"), fg="#80cbc4", background="#0a1a15"
        ).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.rc_entry = tkinter.Entry(input_frame, width=8, font=get_element_font("hilo_trainer_value"), justify="center")
        self.rc_entry.grid(row=0, column=1, padx=6, pady=6)
        self.rc_entry.focus_set()

        # True Count input
        tkinter.Label(
            input_frame, text="True Count (TC):", font=get_element_font("dialog_badge"), fg="#80cbc4", background="#0a1a15"
        ).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.tc_entry = tkinter.Entry(input_frame, width=8, font=get_element_font("hilo_trainer_value"), justify="center")
        self.tc_entry.grid(row=1, column=1, padx=6, pady=6)

        # Feedback label
        self.feedback_var = tkinter.StringVar(value="")
        self.feedback_label = tkinter.Label(
            self, textvariable=self.feedback_var, font=get_element_font("dialog_body", weight_override="bold"), background="#0a1a15"
        )
        self.feedback_label.pack(pady=6)

        # Buttons
        btn_frame = tkinter.Frame(self, background="#0a1a15")
        btn_frame.pack(pady=(8, 0))

        self.submit_btn = tkinter.Button(
            btn_frame,
            text="Submit Answer",
            font=get_element_font("dialog_button"),
            background="#00695c",
            foreground="#ffffff",
            activebackground="#00897b",
            activeforeground="#ffffff",
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._on_submit,
        )
        self.submit_btn.pack(side="left", padx=6)

        self.bind("<Return>", lambda e: self._on_submit())

    def _on_submit(self):
        rc_str = self.rc_entry.get().strip()
        tc_str = self.tc_entry.get().strip()

        try:
            rc_val = int(rc_str)
        except ValueError:
            self.feedback_var.set("Please enter a valid whole number for RC.")
            self.feedback_label.configure(fg="#ff5252")
            return

        tc_val: Optional[float] = None
        if tc_str:
            try:
                tc_val = float(tc_str)
            except ValueError:
                self.feedback_var.set("Please enter a valid decimal for TC.")
                self.feedback_label.configure(fg="#ff5252")
                return

        actual_rc = self.counter.running_count
        actual_tc = self.counter.true_count(self.cards_remaining)

        is_correct = self.counter.verify_quiz_answer(
            submitted_rc=rc_val,
            submitted_tc=tc_val,
            cards_remaining=self.cards_remaining,
        )

        if is_correct:
            self.feedback_var.set(f"★ Correct! RC was {actual_rc:+d}, TC was {actual_tc:+.1f}!")
            self.feedback_label.configure(fg="#00e676")
        else:
            self.feedback_var.set(f"Incorrect. Actual RC: {actual_rc:+d}, TC: {actual_tc:+.1f}")
            self.feedback_label.configure(fg="#ff5252")

        if self.on_result:
            self.on_result(is_correct, actual_rc, actual_tc)

        self.after(1600, self._on_close)

    def _on_close(self):
        try:
            self.destroy()
        except Exception:
            pass
