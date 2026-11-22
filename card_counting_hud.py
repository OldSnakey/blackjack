"""
Card Counting Trainer HUD (LeftFeltWing Counting Slate), Floating Card Tags, and Drill Challenge Modals.

Implements:
- CardCountingHud: Collapsible vertical Mahogany & Brass Counting Slate mounted in LeftFeltWing,
  displaying Running Count, Estimated Decks Remaining, True Count, Player Edge, Kelly Bet Guide
  with 1-click [Stage] button, Basic Strategy + Illustrious 18 Advisor, and a compact [Count (K)]
  collapsed edge tab with zero vertical table reflow.
- FloatingCountBadge: Lightweight transient tag particles (+1, -1, 0) spawning above dealt cards.
- CardCountingQuizDialog: Interactive drill quiz testing Count Check and Illustrious 18 Deviations.
"""

from __future__ import annotations

import sys
import tkinter
from typing import Any, Callable, Optional

from card_counter import HiLoCardCounter, MIT_KELLY_UNIT_RAMP
from rules import HouseRules, effective_minimum_bet
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
    snap_pixel_font_size,
)


class FloatingCountBadge(tkinter.Label):
    """
    Transient floating tag particle (+1, -1, 0) that briefly appears above
    dealt cards to provide visual feedback during card counting practice.
    """

    _ACTIVE_INSTANCES: set["FloatingCountBadge"] = set()

    def __init__(
        self,
        master: tkinter.Misc,
        tag_value: int,
        duration_ms: int = 800,
        font_scale: int = 1,
        **kwargs,
    ):
        if tag_value > 0:
            text = f"+{tag_value}"
            fg_col = "#00e676"  # Emerald Green for positive tags (low cards removed)
        elif tag_value < 0:
            text = f"{tag_value}"
            fg_col = "#ff5252"  # Coral Red for negative tags (high cards removed)
        else:
            text = "0"
            fg_col = "#b0bec5"  # Slate Gray for neutral tags

        fs = max(1, int(font_scale))
        super().__init__(
            master,
            text=text,
            font=get_element_font("hilo_floating_badge", scale=float(fs)),
            fg=fg_col,
            background="#102027",
            padx=6 * fs,
            pady=2 * fs,
            relief="solid",
            borderwidth=1,
            highlightbackground=fg_col,
            highlightthickness=1,
            **kwargs,
        )
        self._timer_id: Optional[str] = None
        FloatingCountBadge._ACTIVE_INSTANCES.add(self)
        try:
            self._timer_id = self.after(duration_ms, self._safe_destroy)
        except Exception:
            pass

    def _safe_destroy(self):
        """Cancels any pending callback and removes widget."""
        FloatingCountBadge._ACTIVE_INSTANCES.discard(self)
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

    def destroy(self):
        FloatingCountBadge._ACTIVE_INSTANCES.discard(self)
        if getattr(self, "_timer_id", None):
            try:
                self.after_cancel(self._timer_id)
            except Exception:
                pass
            self._timer_id = None
        super().destroy()


class CardCountingHud(tkinter.Frame):
    """
    Vertical Mahogany & Brass Counting Slate mounted in `LeftFeltWing`.
    Collapses into a compact `[Count (K)]` edge tab when hidden so toggling
    never shifts Dealer or Player card coordinates vertically.
    """

    MAHOGANY_BG = "#26110d"
    RECESSED_BG = "#1b0c09"
    GOLD_TRIM = "#d4af37"
    SUBTLE_GOLD = "#7c5c26"
    GOLD_TEXT = "#ffd700"
    GOLD_BTN_BG = "#d4a942"
    GOLD_BTN_TEXT = "#141008"
    BTN_BG = "#3e1a14"
    BTN_ACTIVE_BG = "#5d2a1f"
    DIVIDER_COLOR = "#5d2a1f"
    SLATE_BASE_WIDTH = 196

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
        display_profile: Optional[Any] = None,
        show_edge_tab: bool = True,
        **kwargs,
    ):
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
        self._display_profile = display_profile
        self._art_scale: int = int(getattr(display_profile, "art_scale", 1) or 1)
        self._font_scale: float = float(getattr(display_profile, "table_font_scale", self._art_scale) or 1.0)

        if placement_mode is not None:
            self.placement_mode = placement_mode
        elif use_grid:
            self.placement_mode = "grid"
        else:
            self.placement_mode = "pack"

        self.is_visible = False
        self.drill_mode = False
        self._edge_tab_enabled: bool = bool(show_edge_tab and self.placement_mode == "wing")
        self._house_rules: HouseRules = HouseRules()
        self._last_rec_bet = 25
        self._last_bankroll: Optional[int] = None
        self._last_active_seats: int = 1
        self._last_cards_remaining = int(getattr(self.counter, "deck_count", 4)) * 52
        self._last_hint: Optional[Any] = None
        self._last_hint_text: Optional[str] = None
        self._last_deviation: Optional[Any] = None
        self._active_badges: list[FloatingCountBadge] = []

        self._build_ui()
        if self._edge_tab_enabled and not self.is_visible:
            self._map_edge_tab()

    def set_house_rules(self, rules: HouseRules) -> None:
        """Synchronizes active HouseRules used for edge estimation and Kelly bet targets."""
        self._house_rules = rules.normalized() if isinstance(rules, HouseRules) else HouseRules()
        if hasattr(self, "decks_label") and self.decks_label.winfo_exists():
            try:
                decks = self.counter.decks_remaining(self._last_cards_remaining)
                self.decks_label.configure(text=f"{decks:.1f}")
            except Exception:
                pass

    def _build_ui(self):
        fs = float(self._font_scale)
        pad_s = self._art_scale

        # Collapsed Edge Tab button in master (when placement_mode == "wing")
        self.edge_tab_btn = tkinter.Button(
            self.master,
            text="📊 Count [K]",
            font=get_element_font("hilo_trainer_button", scale=fs),
            background=self.MAHOGANY_BG,
            foreground=self.GOLD_TEXT,
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="solid",
            borderwidth=1,
            highlightbackground=self.GOLD_TRIM,
            highlightthickness=1,
            padx=8 * pad_s,
            pady=3 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=self.toggle_visibility,
        )

        # Top brass molding accent line (single 1px gold trim)
        self.brass_trim = tkinter.Frame(self, height=max(1, pad_s), background=self.GOLD_TRIM)
        self.brass_trim.pack(side="top", fill="x")

        # 1. Title Tab Header Row (top of the vertical slate)
        self.tab_frame = tkinter.Frame(
            self,
            background=self.MAHOGANY_BG,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6 * pad_s,
            pady=2 * pad_s,
        )
        self.tab_frame.pack(side="top", fill="x")

        self.title_lbl = tkinter.Label(
            self.tab_frame,
            text="Hi-Lo Slate",
            font=get_element_font("hilo_trainer_title", scale=fs),
            fg=self.GOLD_TEXT,
            background=self.MAHOGANY_BG,
        )
        self.title_lbl.pack(side="left")

        btn_font = get_element_font("hilo_trainer_button", scale=fs)
        self.close_btn = tkinter.Button(
            self.tab_frame,
            text="✖",
            font=btn_font,
            background=self.MAHOGANY_BG,
            foreground=self.GOLD_TRIM,
            activebackground=self.BTN_BG,
            activeforeground="#ffffff",
            relief="flat",
            padx=3 * pad_s,
            pady=0,
            cursor="hand2",
            takefocus=False,
            command=self.toggle_visibility,
        )
        self.close_btn.pack(side="right")

        # 2. Main Vertical Slate Body Frame
        self.bar_frame = tkinter.Frame(
            self,
            background=self.MAHOGANY_BG,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=6 * pad_s,
            pady=3 * pad_s,
        )
        self.bar_frame.pack(side="top", fill="both", expand=True)

        f_lbl = get_element_font("hilo_trainer_label", scale=fs)
        f_val = get_element_font("hilo_trainer_value", scale=fs)
        self._stat_name_labels: list[tkinter.Label] = []

        # 2x2 Compact Telemetry Grid (RC | TC / Decks | Edge)
        self._is_betting_phase: bool = True
        self.stats_grid = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.stats_grid.pack(side="top", fill="x", pady=(0, 2 * pad_s))
        self.stats_grid.columnconfigure(0, weight=1, minsize=int(76 * pad_s))
        self.stats_grid.columnconfigure(1, weight=1, minsize=int(82 * pad_s))

        # Running Count (RC)
        self.rc_frame = tkinter.Frame(self.stats_grid, background=self.MAHOGANY_BG)
        self.rc_frame.grid(row=0, column=0, sticky="w", padx=(0, 4 * pad_s), pady=1)
        rc_name = tkinter.Label(
            self.rc_frame, text="RC:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        )
        rc_name.pack(side="left")
        self._stat_name_labels.append(rc_name)
        self.rc_label = tkinter.Label(
            self.rc_frame, text="+0", font=f_val, fg="#ffffff", background=self.MAHOGANY_BG
        )
        self.rc_label.pack(side="left", padx=(2 * pad_s, 0))

        # True Count (TC)
        self.tc_frame = tkinter.Frame(self.stats_grid, background=self.MAHOGANY_BG)
        self.tc_frame.grid(row=0, column=1, sticky="w", pady=1)
        tc_name = tkinter.Label(
            self.tc_frame, text="TC:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        )
        tc_name.pack(side="left")
        self._stat_name_labels.append(tc_name)
        self.tc_label = tkinter.Label(
            self.tc_frame, text="+0.0", font=f_val, fg="#ffffff", background=self.MAHOGANY_BG
        )
        self.tc_label.pack(side="left", padx=(2 * pad_s, 0))

        # Decks Remaining
        self.decks_frame = tkinter.Frame(self.stats_grid, background=self.MAHOGANY_BG)
        self.decks_frame.grid(row=1, column=0, sticky="w", padx=(0, 4 * pad_s), pady=1)
        dk_name = tkinter.Label(
            self.decks_frame, text="Dks:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        )
        dk_name.pack(side="left")
        self._stat_name_labels.append(dk_name)
        default_decks_text = f"{float(getattr(self.counter, 'deck_count', 4)):.1f}"
        self.decks_label = tkinter.Label(
            self.decks_frame, text=default_decks_text, font=f_val, fg="#ffffff", background=self.MAHOGANY_BG
        )
        self.decks_label.pack(side="left", padx=(2 * pad_s, 0))

        # Player Advantage (Edge %)
        self.edge_frame = tkinter.Frame(self.stats_grid, background=self.MAHOGANY_BG)
        self.edge_frame.grid(row=1, column=1, sticky="w", pady=1)
        ed_name = tkinter.Label(
            self.edge_frame, text="Edge:", font=f_lbl, fg=self.GOLD_TRIM, background=self.MAHOGANY_BG
        )
        ed_name.pack(side="left")
        self._stat_name_labels.append(ed_name)
        self.edge_label = tkinter.Label(
            self.edge_frame, text="-0.5%", font=f_val, fg="#80cbc4", background=self.MAHOGANY_BG
        )
        self.edge_label.pack(side="left", padx=(2 * pad_s, 0))

        # Horizontal Divider
        self.divider = tkinter.Frame(self.bar_frame, height=max(1, pad_s), background=self.DIVIDER_COLOR)
        self.divider.pack(side="top", fill="x", pady=3 * pad_s)

        # Kelly Bet Sizing Row + [Stage] Button
        self.bet_guide_frame = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.bet_guide_frame.pack(side="top", fill="x", pady=(0, 3 * pad_s))
        bet_name = tkinter.Label(
            self.bet_guide_frame, text="Bet:", font=f_lbl, fg="#ffd54f", background=self.MAHOGANY_BG
        )
        bet_name.pack(side="left")
        self._stat_name_labels.append(bet_name)
        self.bet_guide_label = tkinter.Label(
            self.bet_guide_frame,
            text="1u ($25)",
            font=btn_font,
            fg="#fff59d",
            background=self.MAHOGANY_BG,
            cursor="hand2",
        )
        self.bet_guide_label.pack(side="left", padx=(2 * pad_s, 2 * pad_s))
        self.bet_guide_label.bind("<Button-1>", lambda e: self._on_stage_bet_click())

        self.stage_bet_btn = tkinter.Button(
            self.bet_guide_frame,
            text="Stage",
            font=btn_font,
            background=self.GOLD_BTN_BG,
            foreground=self.GOLD_BTN_TEXT,
            activebackground="#ecc260",
            activeforeground=self.GOLD_BTN_TEXT,
            disabledforeground="#7a5a4b",
            relief="raised",
            borderwidth=1,
            padx=4 * pad_s,
            pady=0,
            cursor="hand2",
            takefocus=False,
            command=self._on_stage_bet_click,
        )
        self.stage_bet_btn.pack(side="right")

        # Basic Strategy & Illustrious 18 Recessed Advisor Panel
        self.strategy_frame = tkinter.Frame(
            self.bar_frame,
            background=self.RECESSED_BG,
            relief="flat",
            borderwidth=0,
            highlightbackground=self.SUBTLE_GOLD,
            highlightcolor=self.GOLD_TRIM,
            highlightthickness=1,
            padx=5 * pad_s,
            pady=3 * pad_s,
        )
        self.strategy_frame.pack(side="top", fill="x", pady=(0, 4 * pad_s))

        self.strategy_title_lbl = tkinter.Label(
            self.strategy_frame,
            text="STRATEGY",
            font=f_lbl,
            fg=self.GOLD_TRIM,
            background=self.RECESSED_BG,
        )
        self.strategy_title_lbl.pack(side="top", anchor="center")

        self.strategy_label = tkinter.Label(
            self.strategy_frame,
            text="-",
            font=btn_font,
            fg="#ffffff",
            background=self.RECESSED_BG,
            justify="center",
            anchor="center",
            wraplength=int(172 * fs),
        )
        self.strategy_label.pack(side="top", anchor="center", pady=(1, 0))

        self.deviation_badge = tkinter.Label(
            self.strategy_frame,
            text="",
            font=btn_font,
            fg=self.GOLD_TEXT,
            background=self.BTN_BG,
            padx=4 * pad_s,
            pady=1,
            relief="solid",
            borderwidth=1,
            highlightbackground=self.GOLD_TRIM,
            highlightthickness=1,
            justify="center",
            wraplength=int(166 * fs),
        )

        # Compact 2-Row Action Controls Grid
        self.controls_grid = tkinter.Frame(self.bar_frame, background=self.MAHOGANY_BG)
        self.controls_grid.pack(side="top", fill="x")
        self.controls_grid.columnconfigure(0, weight=1)
        self.controls_grid.columnconfigure(1, weight=1)

        self.mode_btn = tkinter.Button(
            self.controls_grid,
            text="👁 Assisted",
            font=btn_font,
            background="#1b382d",
            foreground="#80cbc4",
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            padx=3 * pad_s,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=lambda: self.toggle_drill_mode(self._last_cards_remaining),
        )
        self.mode_btn.grid(row=0, column=0, sticky="ew", padx=(0, 2 * pad_s), pady=(0, 2 * pad_s))

        self.quiz_btn = tkinter.Button(
            self.controls_grid,
            text="🎯 Quiz",
            font=btn_font,
            background=self.BTN_BG,
            foreground=self.GOLD_TEXT,
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            padx=3 * pad_s,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=self._on_quiz_click,
        )
        self.quiz_btn.grid(row=0, column=1, sticky="ew", padx=(2 * pad_s, 0), pady=(0, 2 * pad_s))

        self.bootcamp_btn = tkinter.Button(
            self.controls_grid,
            text="🎓 Bootcamp",
            font=btn_font,
            background=self.BTN_BG,
            foreground=self.GOLD_TEXT,
            activebackground=self.BTN_ACTIVE_BG,
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=1,
            padx=4 * pad_s,
            pady=1,
            cursor="hand2",
            takefocus=False,
            command=self._on_bootcamp_click,
        )
        self.bootcamp_btn.grid(row=1, column=0, columnspan=2, sticky="ew")

    def _map_edge_tab(self) -> None:
        """Maps the compact `[Count (K)]` edge tab at the top of `LeftFeltWing` when collapsed."""
        if not self._edge_tab_enabled or not hasattr(self, "edge_tab_btn"):
            return
        if not self.edge_tab_btn.winfo_exists():
            return
        if not bool(self.edge_tab_btn.winfo_manager()):
            siblings = [
                ch for ch in self.master.winfo_children()
                if ch is not self.edge_tab_btn and ch is not self and ch.winfo_manager() == "pack"
            ]
            pack_kw = {"before": siblings[0]} if siblings else {}
            self.edge_tab_btn.pack(side="top", anchor="w", pady=(0, 4 * self._art_scale), **pack_kw)

    def _unmap_edge_tab(self) -> None:
        if hasattr(self, "edge_tab_btn") and self.edge_tab_btn.winfo_exists():
            if bool(self.edge_tab_btn.winfo_manager()):
                self.edge_tab_btn.pack_forget()

    def set_edge_tab_enabled(self, enabled: bool) -> None:
        """Enables or hides the collapsed `[Count (K)]` edge tab (e.g. during Bootcamp/Tour map)."""
        self._edge_tab_enabled = bool(enabled and self.placement_mode == "wing")
        if not self._edge_tab_enabled:
            self._unmap_edge_tab()
        elif not self.is_visible:
            self._map_edge_tab()

    def set_display_profile(self, profile: Any) -> None:
        """Updates fonts, wraplengths, and paddings cleanly for a new DisplayProfile."""
        self._display_profile = profile
        self._art_scale = int(getattr(profile, "art_scale", 1) or 1)
        self._font_scale = float(getattr(profile, "table_font_scale", self._art_scale) or 1.0)
        fs = float(self._font_scale)
        pad_s = self._art_scale
        col_mult = 1.25 if (pad_s == 1 and fs >= 1.35) else 1.0

        self.brass_trim.configure(height=max(1, pad_s))
        self.divider.configure(height=max(1, pad_s))
        self.tab_frame.configure(padx=6 * pad_s, pady=2 * pad_s)
        self.bar_frame.configure(padx=6 * pad_s, pady=3 * pad_s)
        self.strategy_frame.configure(padx=5 * pad_s, pady=3 * pad_s)
        self.stats_grid.columnconfigure(0, weight=1, minsize=int(76 * pad_s * col_mult))
        self.stats_grid.columnconfigure(1, weight=1, minsize=int(82 * pad_s * col_mult))

        f_title = get_element_font("hilo_trainer_title", scale=fs)
        f_btn = get_element_font("hilo_trainer_button", scale=fs)
        f_lbl = get_element_font("hilo_trainer_label", scale=fs)
        f_val = get_element_font("hilo_trainer_value", scale=fs)

        self.title_lbl.configure(font=f_title)
        self.edge_tab_btn.configure(font=f_btn, padx=8 * pad_s, pady=3 * pad_s)
        for btn in (self.close_btn, self.stage_bet_btn, self.mode_btn, self.quiz_btn, self.bootcamp_btn):
            btn.configure(font=f_btn)
        for lbl in self._stat_name_labels:
            lbl.configure(font=f_lbl)
        self.strategy_title_lbl.configure(font=f_lbl)
        self.bet_guide_label.configure(font=f_btn)
        for val_lbl in (self.rc_label, self.tc_label, self.decks_label, self.edge_label):
            val_lbl.configure(font=f_val)

        self.strategy_label.configure(wraplength=int(172 * fs))
        self.deviation_badge.configure(wraplength=int(166 * fs))
        self.update_strategy_hint(
            hint=self._last_hint,
            text=self._last_hint_text,
            deviation=self._last_deviation,
        )

    def spawn_floating_badge(
        self,
        master: tkinter.Misc,
        tag_value: int,
        x: Optional[int] = None,
        y: Optional[int] = None,
        duration_ms: int = 800,
    ) -> FloatingCountBadge:
        """Spawns and tracks a transient FloatingCountBadge particle on `master`."""
        badge = FloatingCountBadge(
            master=master,
            tag_value=tag_value,
            duration_ms=duration_ms,
            font_scale=self._font_scale,
        )
        if x is not None and y is not None:
            badge.place(x=x, y=y, anchor="center")
        else:
            badge.place(relx=0.5, rely=0.5, anchor="center")
        self._active_badges.append(badge)
        return badge

    def cancel_floating_badges(self) -> None:
        """Destroys all active FloatingCountBadge timers/widgets during profile transitions."""
        for badge in list(self._active_badges):
            try:
                badge._safe_destroy()
            except Exception:
                pass
        self._active_badges.clear()
        for badge in list(FloatingCountBadge._ACTIVE_INSTANCES):
            try:
                badge._safe_destroy()
            except Exception:
                pass
        FloatingCountBadge._ACTIVE_INSTANCES.clear()

    def _on_quiz_click(self):
        if self.on_quiz_request:
            self.on_quiz_request()

    def _on_bootcamp_click(self):
        if self.on_bootcamp_request:
            self.on_bootcamp_request()

    def _on_stage_bet_click(self):
        """Dispatches stage bet callback if registered (blocked in Drill Mode or outside Betting Phase)."""
        if self.drill_mode or not getattr(self, "_is_betting_phase", True):
            return
        if self.on_stage_bet_request:
            self.on_stage_bet_request(self._last_rec_bet)

    def set_betting_phase(self, is_betting: bool) -> None:
        """Synchronizes [Stage] button enabled/disabled appearance with active Betting Phase."""
        self._is_betting_phase = bool(is_betting)
        if hasattr(self, "stage_bet_btn") and self.stage_bet_btn.winfo_exists():
            can_stage = self._is_betting_phase and not self.drill_mode
            self.stage_bet_btn.configure(
                state="normal" if can_stage else "disabled",
                background=self.GOLD_BTN_BG if can_stage else "#2c1810",
                relief="raised" if can_stage else "sunken",
            )

    def set_visible(self, visible: bool) -> bool:
        """Explicitly sets HUD visibility state."""
        if self.is_visible != visible:
            self.toggle_visibility()
        return self.is_visible

    def toggle_visibility(self) -> bool:
        """Toggles visibility of the vertical Counting Slate vs. collapsed `[Count (K)]` edge tab."""
        if self.is_visible:
            if self.placement_mode == "wing":
                self.pack_forget()
                self._map_edge_tab()
            elif self.use_grid:
                self.grid_remove()
            else:
                self.pack_forget()
            self.is_visible = False
        else:
            if self.placement_mode == "wing":
                self._unmap_edge_tab()
                siblings = [
                    ch for ch in self.master.winfo_children()
                    if ch is not self.edge_tab_btn and ch is not self and ch.winfo_manager() == "pack"
                ]
                pack_kw = {"before": siblings[0]} if siblings else {}
                self.pack(side="top", anchor="w", pady=(0, 6 * self._art_scale), **pack_kw)
            elif self.use_grid:
                self.grid(row=self.grid_row, column=0, columnspan=3, sticky="ew", padx=12, pady=(4, 4))
            else:
                self.pack(side="top", fill="x", padx=12, pady=(4, 4))
            self.is_visible = True
        return self.is_visible

    def on_dealer_view_toggled(self):
        """Retained as a safe no-op for legacy compatibility (Hide Dealer toggle is retired)."""
        return

    def _format_strategy_display(
        self,
        hint: Optional[Any],
        text: Optional[str],
    ) -> tuple[str, str, tuple]:
        """
        Formats strategy text into up to 2 stacked lines with integer pixel-font scaling
        and strict character limits to prevent overflow inside the 196px Counting Slate.
        """
        fs = max(1, int(self._font_scale))
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

        sz_sm = -snap_pixel_font_size(16, fs, family="Tiny5")
        sz_lg = -snap_pixel_font_size(24, fs, family="Tiny5")

        if hint is None and not text:
            return "-", "#78909c", ("Tiny5", sz_sm, "normal")

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
                reason = reason.replace("Hard ", "H").replace("Soft ", "S").replace("Pair of ", "").replace("Pair ", "")
                if len(reason) > 13:
                    reason = reason[:12] + "…"
                display_text = f"{action_name}\n({reason})"
                font_spec = ("Tiny5", sz_sm, "bold")
            else:
                display_text = action_name
                font_spec = ("Tiny5", sz_lg, "bold")

            return display_text, fg_col, font_spec

        clean_text = str(text).strip()
        fg_col = "#ffffff"

        if " (" in clean_text and clean_text.endswith(")"):
            part1, part2 = clean_text.split(" (", 1)
            display_text = f"{part1}\n({part2}"
            fg_col = color_palette.get(part1.strip().upper(), "#ffffff")
            font_spec = ("Tiny5", sz_sm, "normal") if max(len(part1), len(part2) + 1) > 11 else ("Tiny5", sz_sm, "bold")
        elif len(clean_text) > 14:
            if len(clean_text) > 22:
                clean_text = clean_text[:20] + "…"
            display_text = clean_text
            fg_col = color_palette.get(clean_text.strip().upper(), "#ffffff")
            font_spec = ("Tiny5", sz_sm, "normal")
        else:
            display_text = clean_text
            fg_col = color_palette.get(clean_text.strip().upper(), "#ffffff")
            font_spec = ("Tiny5", sz_sm, "bold") if len(clean_text) > 8 else ("Tiny5", sz_lg, "bold")

        return display_text, fg_col, font_spec

    def update_strategy_hint(
        self,
        hint: Optional[Any] = None,
        text: Optional[str] = None,
        deviation: Optional[Any] = None,
    ):
        """Updates the Basic Strategy recommendation label and Illustrious 18 deviation badge."""
        if not hasattr(self, "strategy_label") or not self.strategy_label.winfo_exists():
            return

        self._last_hint = hint
        self._last_hint_text = text
        self._last_deviation = deviation
        fs = float(self._font_scale)
        sz_sm = -snap_pixel_font_size(16, fs, family="Tiny5")

        if self.drill_mode and hint is None and text:
            display_text, fg_col, font_spec = "DRILL\n(Count!)", "#ffd54f", ("Tiny5", sz_sm, "bold")
        else:
            display_text, fg_col, font_spec = self._format_strategy_display(hint, text)
        self.strategy_label.configure(text=display_text, fg=fg_col, font=font_spec)

        if hasattr(self, "deviation_badge"):
            is_active_dev = bool(deviation and getattr(deviation, "is_deviation_active", False))
            badge_txt = getattr(deviation, "badge_text", "") if is_active_dev else ""
            if is_active_dev and badge_txt and not self.drill_mode:
                display_badge = badge_txt
                if len(display_badge) > 22 and " (" in display_badge:
                    display_badge = display_badge.split(" (")[0]
                self.deviation_badge.configure(text=display_badge, font=("Tiny5", sz_sm, "normal"))
                if not bool(self.deviation_badge.winfo_manager()):
                    self.deviation_badge.pack(side="top", anchor="center", pady=(2 * self._art_scale, 0))
            else:
                if bool(self.deviation_badge.winfo_manager()):
                    self.deviation_badge.pack_forget()

    def set_drill_mode(self, enabled: bool, cards_remaining: int = 208, base_bet: int = 25) -> bool:
        """Sets Drill Challenge Mode (masks live RC/TC/Edge as '?' when enabled)."""
        self.drill_mode = bool(enabled)
        if hasattr(self, "mode_btn") and self.mode_btn.winfo_exists():
            if self.drill_mode:
                self.mode_btn.configure(text="🧠 Drill", foreground="#ffd54f", background="#3e2723")
            else:
                self.mode_btn.configure(text="👁 Assisted", foreground="#80cbc4", background="#1b382d")
        if hasattr(self, "stage_bet_btn") and self.stage_bet_btn.winfo_exists():
            can_stage = getattr(self, "_is_betting_phase", True) and not self.drill_mode
            self.stage_bet_btn.configure(
                state="normal" if can_stage else "disabled",
                background=self.GOLD_BTN_BG if can_stage else "#2c1810",
                relief="raised" if can_stage else "sunken",
            )
        if self.drill_mode and hasattr(self, "deviation_badge") and bool(self.deviation_badge.winfo_manager()):
            self.deviation_badge.pack_forget()
        self.update_counts(
            cards_remaining=cards_remaining,
            base_bet=base_bet,
            bankroll=self._last_bankroll,
            active_seats=self._last_active_seats,
        )
        return self.drill_mode

    def toggle_drill_mode(self, cards_remaining: int = 208, base_bet: int = 25) -> bool:
        """Toggles between Assisted HUD Mode and Drill Challenge Mode."""
        return self.set_drill_mode(not self.drill_mode, cards_remaining=cards_remaining, base_bet=base_bet)

    def update_counts(
        self,
        cards_remaining: int,
        base_bet: int = 25,
        bankroll: Optional[int] = None,
        active_seats: int = 1,
    ) -> None:
        """Refreshes HUD count badges from internal counter state."""
        self._last_cards_remaining = cards_remaining
        self._last_bankroll = bankroll
        self._last_active_seats = max(1, int(active_seats))
        rc = self.counter.running_count
        decks = self.counter.decks_remaining(cards_remaining)
        tc = self.counter.true_count(cards_remaining)
        if bankroll is not None:
            adv = self.counter.get_player_advantage(cards_remaining, rules=self._house_rules)
            rec_bet, tier_idx, _ = HiLoCardCounter.get_kelly_bet_target(
                self._house_rules, tc, int(bankroll), self._last_active_seats
            )
            raw_units = MIT_KELLY_UNIT_RAMP[tier_idx]
            eff_min = effective_minimum_bet(self._house_rules, int(bankroll))
            max_bet = int(getattr(self._house_rules, "maximum_bet", 0) or 0)
            if max_bet > 0 and rec_bet >= max_bet and eff_min > 0 and rec_bet < raw_units * eff_min:
                eff_units = max(1, round(rec_bet / eff_min))
                bet_guide_str = f"{eff_units}u MAX (${rec_bet:,})"
            elif eff_min > 0 and rec_bet > 0 and rec_bet < raw_units * eff_min:
                eff_units = max(1, round(rec_bet / eff_min))
                bet_guide_str = f"{eff_units}u (${rec_bet:,})"
            else:
                bet_guide_str = f"{raw_units}u (${rec_bet:,})"
        else:
            adv = self.counter.get_player_advantage(cards_remaining)
            rec_bet = self.counter.get_recommended_bet(base_bet, tc)
            rec_units = max(1, rec_bet // max(1, base_bet))
            bet_guide_str = f"{rec_units}u (${rec_bet:,})"
        self._last_rec_bet = rec_bet

        self.decks_label.configure(text=f"{decks:.1f}")

        if self.drill_mode:
            self.rc_label.configure(text="?", fg="#ffd54f")
            self.tc_label.configure(text="?", fg="#ffd54f")
            self.edge_label.configure(text="?", fg="#ffd54f")
            self.bet_guide_label.configure(text="? (Drill)")
            return

        rc_sign = "+" if rc > 0 else ""
        self.rc_label.configure(
            text=f"{rc_sign}{rc}",
            fg="#00e676" if rc > 0 else ("#ff5252" if rc < 0 else "#ffffff"),
        )

        tc_sign = "+" if tc > 0 else ""
        self.tc_label.configure(
            text=f"{tc_sign}{tc:.1f}",
            fg="#00e676" if tc >= 1.0 else ("#ff5252" if tc <= -1.0 else "#ffffff"),
        )

        adv_sign = "+" if adv > 0 else ""
        edge_col = "#4ade80" if tc >= 2.0 else ("#f87171" if tc < -1.0 else "#38bdf8")
        self.edge_label.configure(
            text=f"{adv_sign}{adv:.1f}%",
            fg=edge_col,
        )

        self.bet_guide_label.configure(text=bet_guide_str)


from ui_dialogs import InWindowScreenHost


class CardCountingQuizDialog(InWindowScreenHost):
    """
    In-window full-screen Card Counting & Illustrious 18 Deviation drill quiz screen.
    Tracks correct answer streaks and triggers achievement unlocks without spawning an OS Toplevel.
    """

    def __init__(
        self,
        parent: tkinter.Tk,
        counter: HiLoCardCounter,
        cards_remaining: int,
        on_result: Optional[Callable[[bool, int, float], None]] = None,
        quiz_mode: str = "count",
        deviation_question: Optional[Any] = None,
        display_profile: Optional[Any] = None,
    ):
        app_ref = getattr(parent.winfo_toplevel(), "_active_blackjack_app", None)
        prof = display_profile or getattr(app_ref, "display_profile", None)
        art_s = int(getattr(prof, "art_scale", 1) or 1)
        tbl_fs = float(getattr(prof, "table_font_scale", art_s) or 1.0)
        is_fhd = (art_s == 1 and tbl_fs >= 1.35)
        ov_wh = (840, 480) if is_fhd else (720, 412)
        super().__init__(
            parent,
            app=app_ref,
            profile=prof,
            background="#0a1a15",
            base_pad=16,
            overlay_wh=ov_wh,
            overlay_rely=0.57,
        )
        self.counter = counter
        self.cards_remaining = cards_remaining
        self.on_result = on_result
        self.quiz_mode = quiz_mode
        self.deviation_question = deviation_question
        self.deviation_choice_buttons: dict[str, tkinter.Button] = {}
        self._deviation_options: list[str] = []
        self.focused_deviation_idx: int = 0
        self._close_timer_id: Optional[str] = None

        self.rc_val: int = 0
        self.tc_val: float = 0.0
        self.active_count_field: str = "rc"
        self._submitted: bool = False

        self._font_scale: float = tbl_fs
        self.title("🎯 Card Counting Drill Quiz")

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.bind("1", lambda e: self._switch_mode("count"))
        self.bind("2", lambda e: self._switch_mode("deviation"))
        self.bind("<Prior>", lambda e: self._switch_mode("count"))
        self.bind("<Next>", lambda e: self._switch_mode("deviation"))
        self.bind("<Up>", lambda e: self._on_vertical_step(-1))
        self.bind("<Down>", lambda e: self._on_vertical_step(1))
        self.bind("<Tab>", lambda e: self._on_tab_step())
        self.bind("<Left>", lambda e: self._on_horizontal_step(-1))
        self.bind("<Right>", lambda e: self._on_horizontal_step(1))
        self.bind("<minus>", lambda e: self._on_horizontal_step(-1))
        self.bind("<plus>", lambda e: self._on_horizontal_step(1))
        self.bind("<equal>", lambda e: self._on_horizontal_step(1))
        self.bind("<Return>", lambda e: self._on_activate_primary())
        self.bind("<KP_Enter>", lambda e: self._on_activate_primary())
        self.bind("<space>", lambda e: self._on_activate_primary())
        self.focus_set()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape":
            self._on_close()
            return "break"
        if ch == "1" or ks == "Prior":
            self._switch_mode("count")
            return "break"
        if ch == "2" or ks == "Next":
            self._switch_mode("deviation")
            return "break"
        if self.quiz_mode == "count":
            if ks in ("Up", "Down", "Tab"):
                self._on_vertical_step(-1 if ks == "Up" else 1)
                return "break"
            if ks in ("Left", "minus") or ch == "-":
                self._on_horizontal_step(-1)
                return "break"
            if ks in ("Right", "plus", "equal") or ch in ("+", "="):
                self._on_horizontal_step(1)
                return "break"
            if ks in ("Return", "KP_Enter", "space"):
                self._on_submit_count()
                return "break"
        else:
            if ks == "Left":
                self._step_deviation_focus(-1)
                return "break"
            if ks in ("Right", "Tab"):
                self._step_deviation_focus(1)
                return "break"
            if ks in ("Return", "KP_Enter", "space"):
                self._submit_focused_deviation()
                return "break"
            low = ch.lower()
            hotkey_map = {
                "h": "HIT",
                "s": "STAND",
                "d": "DOUBLE",
                "p": "SPLIT",
                "y": "INSURANCE",
                "n": "DECLINE",
            }
            mapped = hotkey_map.get(low)
            if mapped and mapped in self.deviation_choice_buttons and not self._submitted:
                self.submit_deviation_answer(mapped)
                return "break"
        return "break"

    def _build_ui(self):
        fs = float(self._font_scale)
        pad_s = max(1, int(self.art_scale))
        prompt_font = ("Tiny5", -snap_pixel_font_size(24, fs, family="Tiny5"), "normal")

        card = tkinter.Frame(
            self,
            background="#0a1a15",
            relief="ridge",
            borderwidth=2 * pad_s,
            highlightbackground="#00bfa5",
            highlightthickness=2 * pad_s,
            padx=22 * pad_s,
            pady=14 * pad_s,
        )
        card.pack(fill="both", expand=True)
        self._quiz_card = card

        top_bar = tkinter.Frame(card, background="#0a1a15")
        top_bar.pack(fill="x", pady=(0, 10 * pad_s))

        # 1. Mode Tab Selector Bar
        self.mode_bar = tkinter.Frame(top_bar, background="#0a1a15")
        self.mode_bar.pack(side="left")

        tab_font = get_element_font("hilo_trainer_button", scale=fs)
        self.count_tab_btn = tkinter.Button(
            self.mode_bar,
            text="[1] 📊 Count Check",
            font=tab_font,
            background="#004d40" if self.quiz_mode == "count" else "#142621",
            foreground="#ffffff" if self.quiz_mode == "count" else "#80cbc4",
            activebackground="#00695c",
            activeforeground="#ffffff",
            relief="flat",
            padx=14 * pad_s,
            pady=4 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._switch_mode("count"),
        )
        self.count_tab_btn.pack(side="left", padx=4 * pad_s)

        self.dev_tab_btn = tkinter.Button(
            self.mode_bar,
            text="[2] ⚡ Deviation Check",
            font=tab_font,
            background="#004d40" if self.quiz_mode == "deviation" else "#142621",
            foreground="#ffffff" if self.quiz_mode == "deviation" else "#80cbc4",
            activebackground="#00695c",
            activeforeground="#ffffff",
            relief="flat",
            padx=14 * pad_s,
            pady=4 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._switch_mode("deviation"),
        )
        self.dev_tab_btn.pack(side="left", padx=4 * pad_s)

        tkinter.Button(
            top_bar,
            text="✕ Close (Esc)",
            font=tab_font,
            background="#37474f",
            foreground="#ffffff",
            activebackground="#455a64",
            activeforeground="#ffffff",
            relief="flat",
            padx=12 * pad_s,
            pady=4 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=self._on_close,
        ).pack(side="right")

        # Title Label
        self.header_title = tkinter.Label(
            card,
            text="🎯 TEST YOUR COUNT" if self.quiz_mode == "count" else "⚡ ILLUSTRIOUS 18 DEVIATION",
            font=get_element_font("dialog_title", scale=fs),
            fg="#ffd700",
            background="#0a1a15",
        )
        self.header_title.pack(pady=(4 * pad_s, 8 * pad_s))

        # 2. Count Check Mode Frame
        self.count_frame = tkinter.Frame(card, background="#0a1a15")
        self.count_desc_lbl = tkinter.Label(
            self.count_frame,
            text="Estimate the current Running Count and True Count from all revealed cards:",
            font=prompt_font,
            fg="#eceff1",
            background="#0a1a15",
            wraplength=int(640 * fs),
            justify="center",
        )
        self.count_desc_lbl.pack(pady=(0, 8 * pad_s))

        input_frame = tkinter.Frame(self.count_frame, background="#0a1a15")
        input_frame.pack(pady=2 * pad_s)

        lbl_font = ("Tiny5", -snap_pixel_font_size(24, fs, family="Tiny5"), "bold")
        step_btn_font = ("Tiny5 Duo", -snap_pixel_font_size(24, fs, family="Tiny5 Duo"), "bold")
        val_font = ("Tiny5 Duo", -snap_pixel_font_size(32, fs, family="Tiny5 Duo"), "bold")

        # Row 0: Running Count (RC) Stepper (±1)
        tkinter.Label(
            input_frame,
            text="Running Count (RC):",
            font=lbl_font,
            fg="#80cbc4",
            background="#0a1a15",
        ).grid(row=0, column=0, sticky="e", padx=(4 * pad_s, 14 * pad_s), pady=5 * pad_s)

        rc_ctrl = tkinter.Frame(input_frame, background="#0a1a15")
        rc_ctrl.grid(row=0, column=1, pady=5 * pad_s)

        self.rc_minus_btn = tkinter.Button(
            rc_ctrl,
            text="−",
            font=step_btn_font,
            background="#8e2424",
            foreground="#ffffff",
            activebackground="#b71c1c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2 * pad_s,
            padx=16 * pad_s,
            pady=1 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._adjust_rc(-1),
        )
        self.rc_minus_btn.pack(side="left")

        self.rc_readout_frame = tkinter.Frame(
            rc_ctrl,
            background="#06120e",
            highlightbackground="#ffd700",
            highlightthickness=2 * pad_s,
            padx=14 * pad_s,
            pady=3 * pad_s,
        )
        self.rc_readout_frame.pack(side="left", padx=8 * pad_s)

        self.rc_value_label = tkinter.Label(
            self.rc_readout_frame,
            text="0",
            width=5,
            font=val_font,
            fg="#ffffff",
            background="#06120e",
            justify="center",
            cursor="hand2",
        )
        self.rc_value_label.pack()
        for w_rc in (self.rc_readout_frame, self.rc_value_label):
            w_rc.bind("<Button-1>", lambda e: self._set_active_count_field("rc"))

        self.rc_plus_btn = tkinter.Button(
            rc_ctrl,
            text="+",
            font=step_btn_font,
            background="#1b5e20",
            foreground="#ffffff",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2 * pad_s,
            padx=16 * pad_s,
            pady=1 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._adjust_rc(1),
        )
        self.rc_plus_btn.pack(side="left")

        # Row 1: True Count (TC) Stepper (±0.5)
        tkinter.Label(
            input_frame,
            text="True Count (TC):",
            font=lbl_font,
            fg="#80cbc4",
            background="#0a1a15",
        ).grid(row=1, column=0, sticky="e", padx=(4 * pad_s, 14 * pad_s), pady=5 * pad_s)

        tc_ctrl = tkinter.Frame(input_frame, background="#0a1a15")
        tc_ctrl.grid(row=1, column=1, pady=5 * pad_s)

        self.tc_minus_btn = tkinter.Button(
            tc_ctrl,
            text="−",
            font=step_btn_font,
            background="#8e2424",
            foreground="#ffffff",
            activebackground="#b71c1c",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2 * pad_s,
            padx=16 * pad_s,
            pady=1 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._adjust_tc(-0.5),
        )
        self.tc_minus_btn.pack(side="left")

        self.tc_readout_frame = tkinter.Frame(
            tc_ctrl,
            background="#06120e",
            highlightbackground="#1e4d40",
            highlightthickness=2 * pad_s,
            padx=14 * pad_s,
            pady=3 * pad_s,
        )
        self.tc_readout_frame.pack(side="left", padx=8 * pad_s)

        self.tc_value_label = tkinter.Label(
            self.tc_readout_frame,
            text="0.0",
            width=5,
            font=val_font,
            fg="#ffffff",
            background="#06120e",
            justify="center",
            cursor="hand2",
        )
        self.tc_value_label.pack()
        for w_tc in (self.tc_readout_frame, self.tc_value_label):
            w_tc.bind("<Button-1>", lambda e: self._set_active_count_field("tc"))

        self.tc_plus_btn = tkinter.Button(
            tc_ctrl,
            text="+",
            font=step_btn_font,
            background="#1b5e20",
            foreground="#ffffff",
            activebackground="#2e7d32",
            activeforeground="#ffffff",
            relief="raised",
            borderwidth=2 * pad_s,
            padx=16 * pad_s,
            pady=1 * pad_s,
            cursor="hand2",
            takefocus=False,
            command=lambda: self._adjust_tc(0.5),
        )
        self.tc_plus_btn.pack(side="left")

        tkinter.Label(
            self.count_frame,
            text="D-Pad / Keys: [▲ / ▼] Select Row   •   [◄ / ►] Adjust (− / +)   •   [Enter] Submit",
            font=get_element_font("dialog_hint_label", scale=fs),
            fg="#80cbc4",
            background="#0a1a15",
        ).pack(pady=(4 * pad_s, 0))

        self.submit_btn = tkinter.Button(
            self.count_frame,
            text="Submit Answer (Enter)",
            font=get_element_font("dialog_button", scale=fs),
            background="#00695c",
            foreground="#ffffff",
            activebackground="#00897b",
            activeforeground="#ffffff",
            relief="flat",
            padx=20 * pad_s,
            pady=6 * pad_s,
            cursor="hand2",
            command=self._on_submit_count,
        )
        self.submit_btn.pack(pady=(12 * pad_s, 0))

        # 3. Deviation Check Mode Frame
        self.deviation_frame = tkinter.Frame(card, background="#0a1a15")
        if self.deviation_question is None and hasattr(self.counter, "generate_deviation_question"):
            self.deviation_question = self.counter.generate_deviation_question()

        prompt_text = getattr(self.deviation_question, "prompt", "Do you deviate from basic strategy?")
        self.deviation_prompt_label = tkinter.Label(
            self.deviation_frame,
            text=prompt_text,
            font=prompt_font,
            fg="#eceff1",
            background="#0a1a15",
            wraplength=int(640 * fs),
            justify="center",
        )
        self.deviation_prompt_label.pack(pady=(6 * pad_s, 16 * pad_s))

        self.choices_frame = tkinter.Frame(self.deviation_frame, background="#0a1a15")
        self.choices_frame.pack(pady=6 * pad_s)

        options = list(getattr(self.deviation_question, "options", ("HIT", "STAND")))
        self._deviation_options = options
        self.focused_deviation_idx = 0
        self.deviation_choice_buttons.clear()
        self._deviation_choice_frames: dict[str, tkinter.Frame] = {}
        for idx, opt in enumerate(options):
            wrap_f = tkinter.Frame(
                self.choices_frame,
                background="#0a1a15",
                highlightbackground="#ffd700" if idx == 0 else "#1e4d40",
                highlightthickness=2 * pad_s,
            )
            wrap_f.pack(side="left", padx=10 * pad_s)
            btn = tkinter.Button(
                wrap_f,
                text=opt,
                font=get_element_font("dialog_button", scale=fs),
                background="#00695c",
                foreground="#ffffff",
                activebackground="#00897b",
                activeforeground="#ffffff",
                relief="flat",
                borderwidth=0,
                padx=24 * pad_s,
                pady=8 * pad_s,
                cursor="hand2",
                takefocus=False,
                command=lambda a=opt, i=idx: (self._set_deviation_focus(i), self.submit_deviation_answer(a)),
            )
            btn.pack()
            self.deviation_choice_buttons[opt] = btn
            self._deviation_choice_frames[opt] = wrap_f

        tkinter.Label(
            self.deviation_frame,
            text="D-Pad / Keys: [◄ / ►] Select Action   •   [Enter / Space] Confirm   •   [1 / 2] Mode",
            font=get_element_font("dialog_hint_label", scale=fs),
            fg="#80cbc4",
            background="#0a1a15",
        ).pack(pady=(8 * pad_s, 0))
        self._sync_deviation_focus_styles()

        # 4. Common Feedback label anchored at bottom so active mode sits flush beneath header
        self.feedback_var = tkinter.StringVar(value="")
        self.feedback_label = tkinter.Label(
            card,
            textvariable=self.feedback_var,
            font=get_element_font("dialog_body", scale=fs),
            background="#0a1a15",
            wraplength=int(600 * fs),
            justify="center",
        )
        self.feedback_label.pack(side="bottom", pady=(6 * pad_s, 0))

        # Mask Assisted Hi-Lo Slate live RC/TC while graded quiz is open to prevent open-book answer leak
        self._masked_assisted_hud = False
        hud_ref = getattr(self._host_app, "card_counting_hud", None)
        if hud_ref is not None and not getattr(hud_ref, "drill_mode", False):
            try:
                hud_ref.rc_label.configure(text="?", fg="#ffd54f")
                hud_ref.tc_label.configure(text="?", fg="#ffd54f")
                hud_ref.edge_label.configure(text="?", fg="#ffd54f")
                hud_ref.bet_guide_label.configure(text="? (Quiz)")
                self._masked_assisted_hud = True
            except Exception:
                pass

        # Map active mode
        if self.quiz_mode == "deviation":
            self.deviation_frame.pack(fill="x", pady=(4 * pad_s, 4 * pad_s))
            self._sync_deviation_focus_styles()
        else:
            self.count_frame.pack(fill="x")
            self._set_active_count_field("rc")
        self.fit_overlay_to_requested(pad_w=8 * self._font_scale, pad_h=8 * self._font_scale)

    def _set_deviation_focus(self, idx: int) -> None:
        if not self._deviation_options:
            self.focused_deviation_idx = 0
            return
        self.focused_deviation_idx = int(idx) % len(self._deviation_options)
        self._sync_deviation_focus_styles()

    def _step_deviation_focus(self, delta: int) -> None:
        if self._submitted or not self._deviation_options:
            return
        self._set_deviation_focus(self.focused_deviation_idx + delta)

    def _sync_deviation_focus_styles(self) -> None:
        frames = getattr(self, "_deviation_choice_frames", {})
        for idx, opt in enumerate(self._deviation_options):
            btn = self.deviation_choice_buttons.get(opt)
            wrap_f = frames.get(opt)
            if btn is None or not btn.winfo_exists():
                continue
            is_foc = (idx == self.focused_deviation_idx)
            btn.configure(
                background="#00897b" if is_foc else "#004d40",
                foreground="#ffd700" if is_foc else "#ffffff",
            )
            if wrap_f is not None and wrap_f.winfo_exists():
                wrap_f.configure(highlightbackground="#ffd700" if is_foc else "#1e4d40")

    def _submit_focused_deviation(self) -> None:
        if self._submitted or not self._deviation_options:
            return
        opt = self._deviation_options[self.focused_deviation_idx % len(self._deviation_options)]
        self.submit_deviation_answer(opt)

    def _on_tab_step(self) -> str:
        if self.quiz_mode == "deviation":
            self._step_deviation_focus(1)
            return "break"
        return self._on_vertical_step(1)

    def _on_activate_primary(self) -> str:
        if self.quiz_mode == "deviation":
            self._submit_focused_deviation()
        else:
            self._on_submit_count()
        return "break"

    def _set_active_count_field(self, field: str) -> None:
        if field not in ("rc", "tc"):
            return
        self.active_count_field = field
        if hasattr(self, "rc_readout_frame") and self.rc_readout_frame.winfo_exists():
            self.rc_readout_frame.configure(
                highlightbackground="#ffd700" if field == "rc" else "#1e4d40"
            )
        if hasattr(self, "tc_readout_frame") and self.tc_readout_frame.winfo_exists():
            self.tc_readout_frame.configure(
                highlightbackground="#ffd700" if field == "tc" else "#1e4d40"
            )

    def _on_vertical_step(self, _delta: int) -> str:
        if self.quiz_mode != "count" or self._submitted:
            return "break"
        self._set_active_count_field("tc" if self.active_count_field == "rc" else "rc")
        return "break"

    def _on_horizontal_step(self, direction: int) -> str:
        if self._submitted:
            return "break"
        if self.quiz_mode == "deviation":
            self._step_deviation_focus(1 if direction > 0 else -1)
            return "break"
        if self.active_count_field == "rc":
            self._adjust_rc(1 if direction > 0 else -1)
        else:
            self._adjust_tc(0.5 if direction > 0 else -0.5)
        return "break"

    def _adjust_rc(self, delta: int) -> None:
        if self._submitted:
            return
        self._set_active_count_field("rc")
        self.rc_val = max(-60, min(60, int(self.rc_val + delta)))
        txt = f"{self.rc_val:+d}" if self.rc_val != 0 else "0"
        fg = "#69f0ae" if self.rc_val > 0 else ("#ff8a80" if self.rc_val < 0 else "#ffffff")
        self.rc_value_label.configure(text=txt, fg=fg)

    def _adjust_tc(self, delta: float) -> None:
        if self._submitted:
            return
        self._set_active_count_field("tc")
        self.tc_val = max(-30.0, min(30.0, round((self.tc_val + delta) * 2.0) / 2.0))
        if abs(self.tc_val) < 1e-6:
            self.tc_val = 0.0
            txt = "0.0"
            fg = "#ffffff"
        else:
            txt = f"{self.tc_val:+.1f}"
            fg = "#69f0ae" if self.tc_val > 0 else "#ff8a80"
        self.tc_value_label.configure(text=txt, fg=fg)

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
            self.count_frame.pack(fill="x")
            self._set_active_count_field(self.active_count_field)
            self.focus_set()
        else:
            self.count_tab_btn.configure(background="#142621", foreground="#80cbc4")
            self.dev_tab_btn.configure(background="#004d40", foreground="#ffffff")
            self.header_title.configure(text="⚡ ILLUSTRIOUS 18 DEVIATION")
            self.count_frame.pack_forget()
            if self.deviation_question is None and hasattr(self.counter, "generate_deviation_question"):
                self.deviation_question = self.counter.generate_deviation_question()
                if hasattr(self, "deviation_prompt_label"):
                    self.deviation_prompt_label.configure(text=self.deviation_question.prompt)
            self.deviation_frame.pack(fill="x", pady=(4 * self._font_scale, 4 * self._font_scale))
            self._sync_deviation_focus_styles()
            self.focus_set()
        self.fit_overlay_to_requested(pad_w=8 * self._font_scale, pad_h=8 * self._font_scale)

    def submit_deviation_answer(self, action: str) -> bool:
        """Validates the submitted action for the Illustrious 18 deviation drill."""
        if not self.deviation_question or self._submitted:
            return False
        self._submitted = True

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

        for btn in self.deviation_choice_buttons.values():
            try:
                btn.configure(state="disabled")
            except Exception:
                pass

        if self.on_result:
            self.on_result(is_correct, actual_rc, actual_tc)

        self._schedule_auto_close()
        return is_correct

    def _on_submit_count(self):
        if self._submitted:
            return
        self._submitted = True
        rc_val = int(self.rc_val)
        tc_val = float(self.tc_val)

        for btn_attr in ("rc_minus_btn", "rc_plus_btn", "tc_minus_btn", "tc_plus_btn", "submit_btn"):
            b = getattr(self, btn_attr, None)
            if b is not None and b.winfo_exists():
                b.configure(state="disabled")

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

        self._schedule_auto_close()

    def _schedule_auto_close(self) -> None:
        if self._close_timer_id is not None:
            try:
                self.after_cancel(self._close_timer_id)
            except Exception:
                pass
        try:
            self._close_timer_id = self.after(1600, self._on_close)
        except Exception:
            self._close_timer_id = None

    def destroy(self) -> None:
        if getattr(self, "_masked_assisted_hud", False) and self._host_app is not None:
            self._masked_assisted_hud = False
            try:
                if hasattr(self._host_app, "_sync_counting_hud_counts"):
                    self._host_app._sync_counting_hud_counts()
            except Exception:
                pass
        super().destroy()

    def _on_close(self):
        if getattr(self, "_close_timer_id", None) is not None:
            try:
                self.after_cancel(self._close_timer_id)
            except Exception:
                pass
            self._close_timer_id = None
        try:
            self.destroy()
        except Exception:
            pass
