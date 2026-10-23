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
            font=("Arial", 11, "bold"),
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
        super().__init__(
            master,
            background="#0d231b",
            relief="ridge",
            borderwidth=2,
            highlightbackground="#1de9b6",
            highlightthickness=1,
            padx=8,
            pady=4,
            **kwargs,
        )
        self.counter = counter
        self.on_quiz_request = on_quiz_request
        self.on_stage_bet_request = on_stage_bet_request
        self.use_grid = use_grid
        self.grid_row = grid_row
        self.is_visible = False
        self._last_rec_bet = 25

        self._build_ui()

    def _build_ui(self):
        # Header Badge
        self.title_lbl = tkinter.Label(
            self,
            text="🧮 Hi-Lo Trainer",
            font=("Arial", 9, "bold"),
            fg="#1de9b6",
            background="#0d231b",
        )
        self.title_lbl.pack(side="left", padx=(4, 8))

        # Running Count (RC)
        self.rc_frame = tkinter.Frame(self, background="#0d231b")
        self.rc_frame.pack(side="left", padx=5)
        tkinter.Label(
            self.rc_frame, text="RC:", font=("Arial", 8, "bold"), fg="#80cbc4", background="#0d231b"
        ).pack(side="left")
        self.rc_label = tkinter.Label(
            self.rc_frame, text="+0", font=("Arial", 9, "bold"), fg="#ffffff", background="#0d231b"
        )
        self.rc_label.pack(side="left", padx=(2, 0))

        # Decks Remaining
        self.decks_frame = tkinter.Frame(self, background="#0d231b")
        self.decks_frame.pack(side="left", padx=5)
        tkinter.Label(
            self.decks_frame, text="Decks:", font=("Arial", 8, "bold"), fg="#80cbc4", background="#0d231b"
        ).pack(side="left")
        default_decks_text = f"{float(getattr(self.counter, 'deck_count', 4)):.1f}"
        self.decks_label = tkinter.Label(
            self.decks_frame, text=default_decks_text, font=("Arial", 9, "bold"), fg="#ffffff", background="#0d231b"
        )
        self.decks_label.pack(side="left", padx=(2, 0))

        # True Count (TC)
        self.tc_frame = tkinter.Frame(self, background="#0d231b")
        self.tc_frame.pack(side="left", padx=5)
        tkinter.Label(
            self.tc_frame, text="TC:", font=("Arial", 8, "bold"), fg="#80cbc4", background="#0d231b"
        ).pack(side="left")
        self.tc_label = tkinter.Label(
            self.tc_frame, text="+0.0", font=("Arial", 9, "bold"), fg="#ffffff", background="#0d231b"
        )
        self.tc_label.pack(side="left", padx=(2, 0))

        # Bet Sizing Guide
        self.bet_guide_frame = tkinter.Frame(self, background="#0d231b")
        self.bet_guide_frame.pack(side="left", padx=5)
        tkinter.Label(
            self.bet_guide_frame, text="Bet Guide:", font=("Arial", 8, "bold"), fg="#ffd54f", background="#0d231b"
        ).pack(side="left")
        self.bet_guide_label = tkinter.Label(
            self.bet_guide_frame, text="1u ($25)", font=("Arial", 9, "bold"), fg="#fff59d", background="#0d231b",
            cursor="hand2"
        )
        self.bet_guide_label.pack(side="left", padx=(2, 0))
        self.bet_guide_label.bind("<Button-1>", lambda e: self._on_stage_bet_click())

        # Basic Strategy Advisor Hint
        self.strategy_frame = tkinter.Frame(self, background="#0d231b")
        self.strategy_frame.pack(side="left", padx=5)
        tkinter.Label(
            self.strategy_frame, text="Strategy:", font=("Arial", 8, "bold"), fg="#80cbc4", background="#0d231b"
        ).pack(side="left")
        self.strategy_label = tkinter.Label(
            self.strategy_frame, text="-", font=("Arial", 9, "bold"), fg="#b0bec5", background="#0d231b"
        )
        self.strategy_label.pack(side="left", padx=(2, 0))

        # Quiz Drill Challenge Button
        self.quiz_btn = tkinter.Button(
            self,
            text="🎯 Quiz",
            font=("Arial", 8, "bold"),
            background="#004d40",
            foreground="#ffffff",
            activebackground="#00796b",
            activeforeground="#ffffff",
            relief="flat",
            padx=5,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=self._on_quiz_click,
        )
        self.quiz_btn.pack(side="left", padx=(6, 4))

        # Hide toggle button
        self.close_btn = tkinter.Button(
            self,
            text="✖",
            font=("Arial", 8),
            background="#0d231b",
            foreground="#80cbc4",
            activebackground="#1b382d",
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            takefocus=False,
            command=self.toggle_visibility,
        )
        self.close_btn.pack(side="right", padx=(4, 0))

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
            self.strategy_label.configure(text=text, fg="#ffffff")
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
        self.strategy_label.configure(text=display_text, fg=fg_col)

    def update_counts(self, cards_remaining: int, base_bet: int = 25):
        """Refreshes HUD count badges from internal counter state."""
        rc = self.counter.running_count
        decks = self.counter.decks_remaining(cards_remaining)
        tc = self.counter.true_count(cards_remaining)
        rec_bet = self.counter.get_recommended_bet(base_bet, tc)
        self._last_rec_bet = rec_bet
        rec_units = max(1, rec_bet // max(1, base_bet))

        # Format RC with explicit +/- sign
        rc_sign = "+" if rc > 0 else ""
        self.rc_label.configure(
            text=f"{rc_sign}{rc}",
            fg="#00e676" if rc > 0 else ("#ff5252" if rc < 0 else "#ffffff"),
        )

        # Decks remaining
        self.decks_label.configure(text=f"{decks:.1f}")

        # Format TC with explicit +/- sign
        tc_sign = "+" if tc > 0 else ""
        self.tc_label.configure(
            text=f"{tc_sign}{tc:.1f}",
            fg="#00e676" if tc >= 1.0 else ("#ff5252" if tc <= -1.0 else "#ffffff"),
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

        dialog_w, dialog_h = 380, 290
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
            font=("Arial", 12, "bold"),
            fg="#ffd700",
            background="#0a1a15",
        ).pack(pady=(0, 8))

        tkinter.Label(
            self,
            text="Estimate the current Running Count and True Count from all revealed cards:",
            font=("Arial", 9),
            fg="#eceff1",
            background="#0a1a15",
            wraplength=340,
            justify="center",
        ).pack(pady=(0, 12))

        input_frame = tkinter.Frame(self, background="#0a1a15")
        input_frame.pack(pady=4)

        # Running Count input
        tkinter.Label(
            input_frame, text="Running Count (RC):", font=("Arial", 9, "bold"), fg="#80cbc4", background="#0a1a15"
        ).grid(row=0, column=0, sticky="e", padx=6, pady=6)
        self.rc_entry = tkinter.Entry(input_frame, width=8, font=("Arial", 10), justify="center")
        self.rc_entry.grid(row=0, column=1, padx=6, pady=6)
        self.rc_entry.focus_set()

        # True Count input
        tkinter.Label(
            input_frame, text="True Count (TC):", font=("Arial", 9, "bold"), fg="#80cbc4", background="#0a1a15"
        ).grid(row=1, column=0, sticky="e", padx=6, pady=6)
        self.tc_entry = tkinter.Entry(input_frame, width=8, font=("Arial", 10), justify="center")
        self.tc_entry.grid(row=1, column=1, padx=6, pady=6)

        # Feedback label
        self.feedback_var = tkinter.StringVar(value="")
        self.feedback_label = tkinter.Label(
            self, textvariable=self.feedback_var, font=("Arial", 9, "bold"), background="#0a1a15"
        )
        self.feedback_label.pack(pady=6)

        # Buttons
        btn_frame = tkinter.Frame(self, background="#0a1a15")
        btn_frame.pack(pady=(8, 0))

        self.submit_btn = tkinter.Button(
            btn_frame,
            text="Submit Answer",
            font=("Arial", 9, "bold"),
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
