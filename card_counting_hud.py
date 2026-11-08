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
    Sleek casino table HUD shelf displaying live Hi-Lo card counting statistics.
    Sits directly on the horizon rail as a low wall / partition shelf with the
    dealer standing behind it in Warm Mahogany Rail styling.
    """

    MAHOGANY_BG = "#26110d"
    GOLD_TRIM = "#d4af37"
    GOLD_TEXT = "#ffd700"
    BTN_BG = "#3e1a14"
    BTN_ACTIVE_BG = "#5d2a1f"
    DIVIDER_COLOR = "#5d2a1f"

    def __init__(
        self,
        master: tkinter.Misc,
        counter: HiLoCardCounter,
        on_quiz_request: Optional[Callable[[], None]] = None,
        on_stage_bet_request: Optional[Callable[[int], None]] = None,
        on_bootcamp_request: Optional[Callable[[], None]] = None,
        use_grid: bool = False,
        grid_row: int = 2,
        stage_canvas: Optional[tkinter.Canvas] = None,
        table_canvas: Optional[tkinter.Canvas] = None,
        dialogue_frame: Optional[tkinter.Misc] = None,
        placement_mode: Optional[str] = None,
        **kwargs,
    ):
        # Determine background matching Warm Mahogany Rail styling
        bg_col = kwargs.pop("background", None) or kwargs.pop("bg", None) or self.MAHOGANY_BG

        super().__init__(
            master,
            background=bg_col,
            relief="flat",
            borderwidth=0,
            highlightbackground=self.GOLD_TRIM,
            highlightcolor=self.GOLD_TRIM,
            highlightthickness=1,
            padx=0,
            pady=0,
            **kwargs,
        )
        self.counter = counter
        self.on_quiz_request = on_quiz_request
        self.on_stage_bet_request = on_stage_bet_request
        self.on_bootcamp_request = on_bootcamp_request
        self.use_grid = use_grid
        self.grid_row = grid_row
        self.stage_canvas = stage_canvas
        self.table_canvas = table_canvas
        self.dialogue_frame = dialogue_frame
        if placement_mode is not None:
            self.placement_mode = placement_mode
        elif stage_canvas is not None:
            self.placement_mode = "shelf"
        elif use_grid:
            self.placement_mode = "grid"
        else:
            self.placement_mode = "pack"

        self.is_visible = False
        self.drill_mode = False
        self._last_rec_bet = 25
        self._last_cards_remaining = int(getattr(self.counter, "deck_count", 4)) * 52

        self._build_ui()

    def mount_on_stage(
        self,
        stage_canvas: tkinter.Canvas,
        table_canvas: Optional[tkinter.Canvas] = None,
        dialogue_frame: Optional[tkinter.Misc] = None,
    ):
        """Mounts the HUD as a horizon shelf on dealer_stage_canvas."""
        self.stage_canvas = stage_canvas
        self.table_canvas = table_canvas
        self.dialogue_frame = dialogue_frame
        self.placement_mode = "shelf"
        self.use_grid = False

    def _build_ui(self):
        # Top brass molding accent line (single 1px gold trim)
        self.brass_trim = tkinter.Frame(self, height=1, background=self.GOLD_TRIM)
        self.brass_trim.pack(side="top", fill="x")

        # 1. Title Tab Header Frame (left side of the shelf)
        self.tab_frame = tkinter.Frame(
            self,
            background=self.MAHOGANY_BG,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=2,
        )
        self.tab_frame.pack(side="left", fill="y", padx=(2, 6))

        self.title_lbl = tkinter.Label(
            self.tab_frame,
            text="Hi-Lo",
            font=get_element_font("hilo_trainer_title"),
            fg=self.GOLD_TEXT,
            background=self.MAHOGANY_BG,
        )
        self.title_lbl.pack(side="left")

        # 2. Main HUD Statistics Bar Frame (Warm Mahogany woodwork aesthetic)
        self.bar_frame = tkinter.Frame(
            self,
            background=self.MAHOGANY_BG,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=4,
            pady=2,
        )
        self.bar_frame.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # Action Buttons (Packed side="right" first to guarantee they are never clipped)
        btn_font = get_element_font("hilo_trainer_button")
        self.close_btn = tkinter.Button(
            self.bar_frame,
            text="✖",
            font=btn_font,
            background=self.MAHOGANY_BG,
            foreground=self.GOLD_TRIM,
            activebackground=self.BTN_BG,
            activeforeground="#ffffff",
            relief="flat",
            cursor="hand2",
            takefocus=False,
            command=self.toggle_visibility,
        )
        self.close_btn.pack(side="right", padx=(4, 2))

        self.quiz_btn = tkinter.Button(
            self.bar_frame,
            text="🎯 Quiz",
            font=btn_font,
            background=self.BTN_BG,
            foreground=self.GOLD_TEXT,
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            padx=5,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=self._on_quiz_click,
        )
        self.quiz_btn.pack(side="right", padx=3)

        self.bootcamp_btn = tkinter.Button(
            self.bar_frame,
            text="🎓 Bootcamp",
            font=btn_font,
            background=self.BTN_BG,
            foreground=self.GOLD_TEXT,
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            padx=5,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=self._on_bootcamp_click,
        )
        self.bootcamp_btn.pack(side="right", padx=3)

        self.mode_btn = tkinter.Button(
            self.bar_frame,
            text="👁 Assisted",
            font=btn_font,
            background=self.BTN_BG,
            foreground="#80cbc4",
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            padx=4,
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
        self.rc_frame = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.rc_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.rc_frame, text="RC:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        ).pack(side="left")
        self.rc_label = tkinter.Label(
            self.rc_frame, text="+0", font=f_val, fg="#ffffff", background=self.MAHOGANY_BG
        )
        self.rc_label.pack(side="left", padx=(2, 0))

        # Decks Remaining
        self.decks_frame = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.decks_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.decks_frame, text="Decks:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        ).pack(side="left")
        default_decks_text = f"{float(getattr(self.counter, 'deck_count', 4)):.1f}"
        self.decks_label = tkinter.Label(
            self.decks_frame, text=default_decks_text, font=f_val, fg="#ffffff", background=self.MAHOGANY_BG
        )
        self.decks_label.pack(side="left", padx=(2, 0))

        # True Count (TC)
        self.tc_frame = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.tc_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.tc_frame, text="TC:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        ).pack(side="left")
        self.tc_label = tkinter.Label(
            self.tc_frame, text="+0.0", font=f_val, fg="#ffffff", background=self.MAHOGANY_BG
        )
        self.tc_label.pack(side="left", padx=(2, 0))

        # Player Advantage (Edge %)
        self.edge_frame = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.edge_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.edge_frame, text="Edge:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        ).pack(side="left")
        self.edge_label = tkinter.Label(
            self.edge_frame, text="-0.5%", font=f_val, fg="#80cbc4", background=self.MAHOGANY_BG
        )
        self.edge_label.pack(side="left", padx=(2, 0))

        # Separator divider bar
        self.divider = tkinter.Frame(self.bar_frame, width=1, background=self.DIVIDER_COLOR)
        self.divider.pack(side="left", fill="y", padx=6, pady=2)

        # Bet Sizing Guide
        self.bet_guide_frame = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.bet_guide_frame.pack(side="left", padx=3)
        tkinter.Label(
            self.bet_guide_frame, text="Bet:", font=f_lbl, fg="#ffd54f", background=self.MAHOGANY_BG
        ).pack(side="left")
        self.bet_guide_label = tkinter.Label(
            self.bet_guide_frame, text="1u ($25)", font=f_val, fg="#fff59d", background=self.MAHOGANY_BG,
            cursor="hand2"
        )
        self.bet_guide_label.pack(side="left", padx=(2, 0))
        self.bet_guide_label.bind("<Button-1>", lambda e: self._on_stage_bet_click())

        # Basic Strategy Advisor Hint & Illustrious 18 Deviation Badge
        # When table_canvas is provided (shelf mode), mount as a dedicated plaque on the felt
        # centered between the Dealer and Seat/Player score boxes.
        strategy_parent = self.table_canvas if (self.placement_mode == "shelf" and self.table_canvas is not None) else self.bar_frame
        self.strategy_frame = tkinter.Frame(
            strategy_parent,
            background=self.MAHOGANY_BG,
            relief="flat",
            borderwidth=0,
            highlightbackground=self.GOLD_TRIM,
            highlightcolor=self.GOLD_TRIM,
            highlightthickness=1 if strategy_parent is self.table_canvas else 0,
            padx=8 if strategy_parent is self.table_canvas else 3,
            pady=3 if strategy_parent is self.table_canvas else 0,
        )
        if strategy_parent is self.bar_frame:
            self.strategy_frame.pack(side="left", padx=3)

        self.strategy_title_lbl = tkinter.Label(
            self.strategy_frame,
            text="STRATEGY" if strategy_parent is self.table_canvas else "Strategy:",
            font=f_lbl,
            fg=self.GOLD_TRIM,
            background=self.MAHOGANY_BG,
        )
        if strategy_parent is self.table_canvas:
            self.strategy_title_lbl.pack(side="top", anchor="center")
        else:
            self.strategy_title_lbl.pack(side="left")

        self.strategy_label = tkinter.Label(
            self.strategy_frame,
            text="-",
            font=get_element_font("hilo_trainer_button"),
            fg="#ffffff",
            background=self.MAHOGANY_BG,
            justify="center" if strategy_parent is self.table_canvas else "left",
            anchor="center" if strategy_parent is self.table_canvas else "w",
        )
        if strategy_parent is self.table_canvas:
            self.strategy_label.pack(side="top", anchor="center", pady=(1, 0))
        else:
            self.strategy_label.pack(side="left", padx=(2, 0))

        # Deviation indicator badge (Illustrious 18)
        self.deviation_badge = tkinter.Label(
            self.strategy_frame,
            text="",
            font=get_element_font("hilo_trainer_button"),
            fg=self.GOLD_TEXT,
            background=self.BTN_BG,
            padx=4,
            pady=0,
            relief="solid",
            borderwidth=1,
            highlightbackground=self.GOLD_TRIM,
            highlightthickness=1,
        )

    def _on_quiz_click(self):
        if self.on_quiz_request:
            self.on_quiz_request()

    def _on_bootcamp_click(self):
        if self.on_bootcamp_request:
            self.on_bootcamp_request()

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
        """Toggles visibility of the counting HUD shelf and felt strategy plaque."""
        if self.is_visible:
            if self.placement_mode == "shelf":
                self.place_forget()
                if hasattr(self, "strategy_frame") and self.strategy_frame.master is self.table_canvas:
                    self.strategy_frame.place_forget()
            elif self.use_grid:
                self.grid_remove()
            else:
                self.pack_forget()
            self.is_visible = False
        else:
            if self.placement_mode == "shelf" and self.stage_canvas is not None:
                self._place_shelf()
            elif self.use_grid:
                self.grid(row=self.grid_row, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 4))
            else:
                self.pack(side="top", fill="x", padx=12, pady=(4, 4))
            self.is_visible = True
        return self.is_visible

    def _is_container_active(self, container: Optional[tkinter.Misc]) -> bool:
        """Determines if container is actively mapped or scheduled in grid (supports headless tests)."""
        if container is None:
            return False
        if container.winfo_ismapped():
            return True
        m = container
        while m and m != getattr(self, "master", None):
            if hasattr(m, "grid_info") and m.grid_info():
                return True
            m = getattr(m, "master", None)
        return False

    def _place_shelf(self):
        """
        Places the shelf on the horizon.
        - When dealer stage is active (Dealer ON): mounted directly on horizon at the bottom of dealer_stage_canvas.
        - When dealer stage is hidden (Dealer OFF): mounted on the horizon line at the exact same vertical coordinate,
          ensuring complete consistency and never blocking chip trays or mahogany rail buttons.
        """
        target_container = self.stage_canvas
        if self._is_container_active(target_container):
            # Mounted directly on horizon at the bottom of dealer_stage_canvas (y = 262 in root)
            self.place(
                in_=target_container,
                x=6,
                relx=0.0,
                rely=1.0,
                y=-44,
                relwidth=1.0,
                width=-12,
                height=44,
            )
            self.lift()
            # Ensure dealer dialogue and speech tail have the highest z-order
            if hasattr(target_container, "tag_raise"):
                target_container.tag_raise("speech_tail")
                target_container.tag_raise("dialogue_win")
            if self.dialogue_frame is not None and hasattr(self.dialogue_frame, "lift"):
                self.dialogue_frame.lift()
        elif self._is_container_active(self.table_canvas):
            # Consistent Horizon Placement: stays on the horizon line (y = 176 in table felt == y = 262 in root)
            self.place(
                in_=self.table_canvas,
                x=6,
                relx=0.0,
                rely=0.0,
                y=176,
                relwidth=1.0,
                width=-12,
                height=44,
            )
            self.lift()
        else:
            self.place(
                in_=self.master,
                x=6,
                relx=0.0,
                rely=0.0,
                y=262,
                relwidth=1.0,
                width=-12,
                height=44,
            )
            self.lift()
        self._place_strategy_plaque()

    def _place_strategy_plaque(self):
        """
        Positions `self.strategy_frame` on `self.table_canvas` centered horizontally and
        vertically between the Dealer score box (row 0, col 0) and the Player/Seat score box (row 1, col 0).
        """
        if not hasattr(self, "strategy_frame") or self.table_canvas is None:
            return
        if self.strategy_frame.master is not self.table_canvas:
            return
        cx, cy = 71, 114
        try:
            plaques = [
                ch for ch in self.table_canvas.winfo_children()
                if "pixelplaqueframe" in ch.__class__.__name__.lower() and bool(ch.grid_info())
            ]
            if len(plaques) >= 2:
                plaques.sort(key=lambda w: int(w.grid_info().get("row", 0)))
                top_p, bot_p = plaques[0], plaques[1]
                top_y = top_p.winfo_y()
                top_h = top_p.winfo_height() if top_p.winfo_height() > 1 else 60
                bot_y = bot_p.winfo_y()
                top_x = top_p.winfo_x() if top_p.winfo_x() > 0 else 14
                top_w = top_p.winfo_width() if top_p.winfo_width() > 1 else 114
                if bot_y > top_y + top_h:
                    cx = top_x + top_w // 2
                    cy = (top_y + top_h + bot_y) // 2
                    # When Dealer View is OFF, the HUD shelf sits at y=176..220; keep plaque centered between Dealer box and shelf
                    if not self._is_container_active(self.stage_canvas) and cy >= 150:
                        cy = (top_y + top_h + 176) // 2
            req_w = max(114, self.strategy_frame.winfo_reqwidth())
            cx = max(14 + req_w // 2, cx)
        except Exception:
            cx, cy = 71, 114

        self.strategy_frame.place(
            in_=self.table_canvas,
            x=cx,
            y=cy,
            anchor="center",
        )
        self.strategy_frame.lift()

    def on_dealer_view_toggled(self):
        """Updates shelf placement if visible when dealer stage is shown/hidden."""
        if self.is_visible and self.placement_mode == "shelf":
            self._place_shelf()

    def _format_strategy_display(
        self,
        hint: Optional[Any],
        text: Optional[str],
    ) -> tuple[str, str, tuple]:
        """
        Formats strategy text into up to 2 stacked lines with dynamic font scaling
        and strict character limits to prevent clipping.

        Returns:
            (display_text, fg_color, font_spec)
        """
        color_palette = {
            "HIT": "#4fc3f7",        # Sky Blue
            "STAND": "#ffb74d",      # Amber Orange
            "DOUBLE": "#69f0ae",     # Neon Emerald
            "SPLIT": "#ea80fc",      # Neon Violet
            "SURRENDER": "#ff5252",  # Vivid Coral
            "TAKE": "#69f0ae",       # Neon Emerald (Take Insurance when TC >= +3)
            "DECLINE": "#ff8a80",    # Soft Coral (Decline Insurance when TC < +3)
            "INSURANCE": "#ffd54f",  # Gold
        }

        # 1. Neither hint nor text: default dash
        if hint is None and not text:
            return "-", "#78909c", ("m6x11plus", -16, "bold")

        # 2. Hint object provided (BasicStrategyDecision or similar)
        if hint is not None:
            raw_action = getattr(hint, "action", "")
            if hasattr(raw_action, "value"):
                action_name = str(raw_action.value).upper()
            elif raw_action:
                action_name = str(raw_action).upper()
            else:
                raw_act_name = getattr(hint, "action_name", "")
                action_name = str(raw_act_name).upper() if raw_act_name else "HIT"

            fg_col = color_palette.get(action_name, "#ffffff")
            reason = getattr(hint, "reason", "").strip()

            if reason:
                # Abbreviate lengthy phrases if needed to enforce max char limits
                if len(reason) > 14:
                    reason = reason.replace("Hard ", "H").replace("Soft ", "S").replace("Pair ", "")
                if len(reason) > 14:
                    reason = reason[:13] + "…"

                # 2-line layout: Action on top, (Reason) below
                display_text = f"{action_name}\n({reason})"

                # Dynamic font sizing based on max line length
                max_line = max(len(action_name), len(reason) + 2)
                if max_line > 14:
                    font_spec = ("m6x11plus", -13, "bold")
                elif max_line > 10:
                    font_spec = ("m6x11plus", -14, "bold")
                else:
                    font_spec = ("m6x11plus", -15, "bold")
            else:
                display_text = action_name
                font_spec = ("m6x11plus", -16, "bold")

            return display_text, fg_col, font_spec

        # 3. Raw text string provided
        clean_text = str(text).strip()
        fg_col = "#ffffff"

        # Check if text has a natural 2-line split point like 'Bet $25 (1u)' or 'DECLINE (TC < +3)'
        if " (" in clean_text and clean_text.endswith(")"):
            part1, part2 = clean_text.split(" (", 1)
            display_text = f"{part1}\n({part2}"
            fg_col = color_palette.get(part1.strip().upper(), "#ffffff")
            max_line = max(len(part1), len(part2) + 1)
            font_spec = ("m6x11plus", -14, "bold") if max_line > 10 else ("m6x11plus", -15, "bold")
        elif len(clean_text) > 14:
            if len(clean_text) > 22:
                clean_text = clean_text[:20] + "…"
            display_text = clean_text
            fg_col = color_palette.get(clean_text.strip().upper(), "#ffffff")
            font_spec = ("m6x11plus", -13, "bold")
        else:
            display_text = clean_text
            fg_col = color_palette.get(clean_text.strip().upper(), "#ffffff")
            font_spec = ("m6x11plus", -15, "bold") if len(clean_text) > 8 else ("m6x11plus", -16, "bold")

        return display_text, fg_col, font_spec

    def update_strategy_hint(
        self,
        hint: Optional[Any] = None,
        text: Optional[str] = None,
        deviation: Optional[Any] = None,
    ):
        """
        Updates the Basic Strategy recommendation label and Illustrious 18 deviation badge.
        Supports BasicStrategyDecision dataclass or raw string text.
        Dynamically adjusts font size, splits into 2 stacked lines, and limits character length.
        """
        if not hasattr(self, "strategy_label") or not self.strategy_label.winfo_exists():
            return

        self._last_hint = hint
        self._last_hint_text = text
        self._last_deviation = deviation

        # 1. Update Basic Strategy label text, color, and dynamic font
        display_text, fg_col, font_spec = self._format_strategy_display(hint, text)
        self.strategy_label.configure(text=display_text, fg=fg_col, font=font_spec)

        # 2. Update Illustrious 18 deviation badge
        if hasattr(self, "deviation_badge"):
            is_active_dev = bool(deviation and getattr(deviation, "is_deviation_active", False))
            badge_txt = getattr(deviation, "badge_text", "") if is_active_dev else ""
            if is_active_dev and badge_txt and not self.drill_mode:
                # If badge text is long, strip redundant parenthesized condition so it fits cleanly
                display_badge = badge_txt
                if len(display_badge) > 22 and " (" in display_badge:
                    display_badge = display_badge.split(" (")[0]
                self.deviation_badge.configure(text=display_badge, font=("m5x7", -16, "bold"))
                if not bool(self.deviation_badge.winfo_manager()):
                    if self.strategy_frame.master is self.table_canvas:
                        self.deviation_badge.pack(side="top", anchor="center", pady=(2, 0))
                    else:
                        self.deviation_badge.pack(side="left", padx=(4, 0))
            else:
                if bool(self.deviation_badge.winfo_manager()):
                    self.deviation_badge.pack_forget()
        if self.is_visible and self.placement_mode == "shelf":
            self._place_strategy_plaque()

    def set_drill_mode(self, enabled: bool, cards_remaining: int = 208, base_bet: int = 25) -> bool:
        """Sets Drill Challenge Mode (masks live RC/TC/Edge as '?' when enabled)."""
        self.drill_mode = bool(enabled)
        if hasattr(self, "mode_btn") and self.mode_btn.winfo_exists():
            if self.drill_mode:
                self.mode_btn.configure(text="🧠 Drill", foreground="#ffd54f", background="#3e2723")
            else:
                self.mode_btn.configure(text="👁 Assisted", foreground="#80cbc4", background="#1b382d")
        if self.drill_mode and hasattr(self, "deviation_badge") and bool(self.deviation_badge.winfo_manager()):
            self.deviation_badge.pack_forget()
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
    Modal quiz dialog testing the player's card counting estimation and Illustrious 18 deviations.
    Tracks correct answer streaks and triggers achievement unlocks.
    """

    def __init__(
        self,
        parent: tkinter.Tk,
        counter: HiLoCardCounter,
        cards_remaining: int,
        on_result: Optional[Callable[[bool, int, float], None]] = None,
        quiz_mode: str = "count",
        deviation_question: Optional[Any] = None,
    ):
        super().__init__(parent)
        self.counter = counter
        self.cards_remaining = cards_remaining
        self.on_result = on_result
        self.quiz_mode = quiz_mode
        self.deviation_question = deviation_question
        self.deviation_choice_buttons: dict[str, tkinter.Button] = {}

        self.title("🎯 Card Counting Drill Quiz")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#0a1a15", padx=16, pady=12)

        dialog_w, dialog_h = 460, 340
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
        self.bind("<Left>", lambda e: self._switch_mode("count"))
        self.bind("<Right>", lambda e: self._switch_mode("deviation"))
        self.focus_set()

    def _build_ui(self):
        # 1. Mode Tab Selector Bar
        self.mode_bar = tkinter.Frame(self, background="#0a1a15")
        self.mode_bar.pack(pady=(0, 6))

        tab_font = get_element_font("hilo_trainer_button")
        self.count_tab_btn = tkinter.Button(
            self.mode_bar,
            text="📊 Count Check",
            font=tab_font,
            background="#004d40" if self.quiz_mode == "count" else "#142621",
            foreground="#ffffff" if self.quiz_mode == "count" else "#80cbc4",
            activebackground="#00695c",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._switch_mode("count"),
        )
        self.count_tab_btn.pack(side="left", padx=3)

        self.dev_tab_btn = tkinter.Button(
            self.mode_bar,
            text="⚡ Deviation Check",
            font=tab_font,
            background="#004d40" if self.quiz_mode == "deviation" else "#142621",
            foreground="#ffffff" if self.quiz_mode == "deviation" else "#80cbc4",
            activebackground="#00695c",
            activeforeground="#ffffff",
            relief="flat",
            padx=10,
            pady=2,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._switch_mode("deviation"),
        )
        self.dev_tab_btn.pack(side="left", padx=3)

        # Title Label
        self.header_title = tkinter.Label(
            self,
            text="🎯 TEST YOUR COUNT" if self.quiz_mode == "count" else "⚡ ILLUSTRIOUS 18 DEVIATION",
            font=get_element_font("dialog_title"),
            fg="#ffd700",
            background="#0a1a15",
        )
        self.header_title.pack(pady=(0, 4))

        # 2. Count Check Mode Frame
        self.count_frame = tkinter.Frame(self, background="#0a1a15")
        self.count_desc_lbl = tkinter.Label(
            self.count_frame,
            text="Estimate the current Running Count and True Count from all revealed cards:",
            font=get_element_font("dialog_body"),
            fg="#eceff1",
            background="#0a1a15",
            wraplength=400,
            justify="center",
        )
        self.count_desc_lbl.pack(pady=(0, 8))

        input_frame = tkinter.Frame(self.count_frame, background="#0a1a15")
        input_frame.pack(pady=4)

        tkinter.Label(
            input_frame, text="Running Count (RC):", font=get_element_font("dialog_badge"), fg="#80cbc4", background="#0a1a15"
        ).grid(row=0, column=0, sticky="e", padx=6, pady=4)
        self.rc_entry = tkinter.Entry(input_frame, width=8, font=get_element_font("hilo_trainer_value"), justify="center")
        self.rc_entry.grid(row=0, column=1, padx=6, pady=4)

        tkinter.Label(
            input_frame, text="True Count (TC):", font=get_element_font("dialog_badge"), fg="#80cbc4", background="#0a1a15"
        ).grid(row=1, column=0, sticky="e", padx=6, pady=4)
        self.tc_entry = tkinter.Entry(input_frame, width=8, font=get_element_font("hilo_trainer_value"), justify="center")
        self.tc_entry.grid(row=1, column=1, padx=6, pady=4)

        self.submit_btn = tkinter.Button(
            self.count_frame,
            text="Submit Answer",
            font=get_element_font("dialog_button"),
            background="#00695c",
            foreground="#ffffff",
            activebackground="#00897b",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=3,
            cursor="hand2",
            command=self._on_submit_count,
        )
        self.submit_btn.pack(pady=(8, 0))

        # 3. Deviation Check Mode Frame
        self.deviation_frame = tkinter.Frame(self, background="#0a1a15")
        if self.deviation_question is None and hasattr(self.counter, "generate_deviation_question"):
            self.deviation_question = self.counter.generate_deviation_question()

        prompt_text = getattr(self.deviation_question, "prompt", "Do you deviate from basic strategy?")
        self.deviation_prompt_label = tkinter.Label(
            self.deviation_frame,
            text=prompt_text,
            font=get_element_font("dialog_body"),
            fg="#eceff1",
            background="#0a1a15",
            wraplength=400,
            justify="center",
        )
        self.deviation_prompt_label.pack(pady=(4, 12))

        self.choices_frame = tkinter.Frame(self.deviation_frame, background="#0a1a15")
        self.choices_frame.pack(pady=4)

        options = getattr(self.deviation_question, "options", ("HIT", "STAND"))
        self.deviation_choice_buttons.clear()
        for opt in options:
            btn = tkinter.Button(
                self.choices_frame,
                text=opt,
                font=get_element_font("dialog_button"),
                background="#00695c",
                foreground="#ffffff",
                activebackground="#00897b",
                activeforeground="#ffffff",
                relief="flat",
                padx=16,
                pady=4,
                cursor="hand2",
                command=lambda a=opt: self.submit_deviation_answer(a),
            )
            btn.pack(side="left", padx=8)
            self.deviation_choice_buttons[opt] = btn

        # 4. Common Feedback label
        self.feedback_var = tkinter.StringVar(value="")
        self.feedback_label = tkinter.Label(
            self,
            textvariable=self.feedback_var,
            font=get_element_font("dialog_body", weight_override="bold"),
            background="#0a1a15",
            wraplength=420,
            justify="center",
        )
        self.feedback_label.pack(pady=(6, 0))

        # Map active mode
        if self.quiz_mode == "deviation":
            self.deviation_frame.pack(fill="x", expand=True)
        else:
            self.count_frame.pack(fill="x", expand=True)
            self.rc_entry.focus_set()
            self.bind("<Return>", lambda e: self._on_submit_count())

    def _switch_mode(self, mode: str):
        """Switches between Count Check and Deviation Check tabs."""
        if mode not in ("count", "deviation") or mode == self.quiz_mode:
            return
        self.quiz_mode = mode
        self.feedback_var.set("")

        if mode == "count":
            self.count_tab_btn.configure(background="#004d40", foreground="#ffffff")
            self.dev_tab_btn.configure(background="#142621", foreground="#80cbc4")
            self.header_title.configure(text="🎯 TEST YOUR COUNT")
            self.deviation_frame.pack_forget()
            self.count_frame.pack(fill="x", expand=True)
            self.rc_entry.focus_set()
            self.bind("<Return>", lambda e: self._on_submit_count())
        else:
            self.count_tab_btn.configure(background="#142621", foreground="#80cbc4")
            self.dev_tab_btn.configure(background="#004d40", foreground="#ffffff")
            self.header_title.configure(text="⚡ ILLUSTRIOUS 18 DEVIATION")
            self.count_frame.pack_forget()
            if self.deviation_question is None and hasattr(self.counter, "generate_deviation_question"):
                self.deviation_question = self.counter.generate_deviation_question()
                if hasattr(self, "deviation_prompt_label"):
                    self.deviation_prompt_label.configure(text=self.deviation_question.prompt)
            self.deviation_frame.pack(fill="x", expand=True)
            self.unbind("<Return>")

    def submit_deviation_answer(self, action: str) -> bool:
        """Validates the submitted action for the Illustrious 18 deviation drill."""
        if not self.deviation_question:
            return False

        is_correct = self.counter.verify_deviation_quiz_answer(self.deviation_question, action)
        actual_rc = self.counter.running_count
        actual_tc = self.counter.true_count(self.cards_remaining)

        exp = getattr(self.deviation_question, "explanation", "")
        if is_correct:
            self.feedback_var.set(f"★ Correct! {exp}")
            self.feedback_label.configure(fg="#00e676")
        else:
            self.feedback_var.set(f"Incorrect. {exp}")
            self.feedback_label.configure(fg="#ff5252")

        # Disable choice buttons to prevent duplicate submissions
        for btn in self.deviation_choice_buttons.values():
            try:
                btn.configure(state="disabled")
            except Exception:
                pass

        if self.on_result:
            self.on_result(is_correct, actual_rc, actual_tc)

        self.after(1600, self._on_close)
        return is_correct

    def _on_submit_count(self):
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
