"""
Dealer Wardrobe & Casino Hall of Fame Dialog for Blackjack.

Provides:
- Tab 1: 🎩 Wardrobe Closet
  - 5 interactive character cards for Julian, Tiffany, Malphas, Uriel, and Mortimer.
  - High-resolution bust preview, title, lore, and audio voice preview.
  - Dynamic unlock criteria checking against persistent save achievements and table milestones.
  - Instant costume equipping with table avatar and stage synchronization.
- Tab 2: 🏆 Hall of Fame & Trophy Shelf
  - All-time casino records banner (peak bankroll, longest streak, hands won/played, blackjacks).
  - 6 visual achievement plaques (The Exorcist, High Roller, Natural Born Winner,
    Cursed Survivor, Split Maestro, Big Spender) with unlock badges and criteria.
- Disk persistence via SaveManager.
"""

from __future__ import annotations

import tkinter
from typing import Any, Dict
from PIL import ImageTk

from dealer_actor import CHARACTERS, CharacterProfile


class WardrobeDialog(tkinter.Toplevel):
    """
    Dealer Wardrobe & Casino Hall of Fame Modal.
    Two-tab interface providing character dressing room and trophy achievements shelf.
    """

    UNLOCK_CRITERIA: Dict[str, str] = {
        "julian": "Default Croupier (Always Unlocked)",
        "tiffany": "Default Croupier (Always Unlocked)",
        "malphas": "Trigger or encounter Hell's Table",
        "uriel": "Banish The Pit Fiend at Hell's Table (Exorcist)",
        "mortimer": "Survive Card 13 or attain $5,000 Bankroll",
    }

    PAGE_CONFIG = [
        {
            "title": "Casino Floor (Classic & Velvet)",
            "characters": ["julian", "tiffany"],
        },
        {
            "title": "Supernatural Legends",
            "characters": ["malphas", "uriel", "mortimer"],
        },
    ]

    ACHIEVEMENT_SPECS = [
        {
            "id": "exorcist",
            "title": "✦ The Exorcist",
            "desc": "Banish The Pit Fiend at Hell's Table and restore sanctified balance.",
            "reward": "Seraph (Uriel) Persona",
            "criteria": "Defeat Hell's Table",
        },
        {
            "id": "high_roller",
            "title": "👑 High Roller",
            "desc": "Amass an all-time peak casino bankroll of $10,000 or greater.",
            "reward": "High Roller Title",
            "criteria": "Reach $10,000 Bankroll",
        },
        {
            "id": "natural_streak",
            "title": "⚡ Natural Born Winner",
            "desc": "Deal 3 Natural 21s (Blackjacks) within a single session.",
            "reward": "Master of Naturals",
            "criteria": "3 Natural Blackjacks in Session",
        },
        {
            "id": "cursed_survivor",
            "title": "💀 Cursed Survivor",
            "desc": "Overcome the eerie clock strike and win or push round with Card 13.",
            "reward": "Grim Bones (Mortimer) Persona",
            "criteria": "Survive Card 13 Round",
        },
        {
            "id": "split_maestro",
            "title": "⚔ Split Maestro",
            "desc": "Split matching cards and emerge victorious on both independent hands.",
            "reward": "Maestro Status",
            "criteria": "Win Both Split Hands",
        },
        {
            "id": "big_spender",
            "title": "💰 Big Spender",
            "desc": "Stake your entire fortune in an all-in bet of $1,000+ and conquer the house.",
            "reward": "Diamond Bettor",
            "criteria": "Win $1,000+ All-In Bet",
        },
    ]

    def __init__(self, parent: tkinter.Tk, app: Any):
        super().__init__(parent)
        self.app = app
        self.title("🎩 Dealer Wardrobe & Dressing Room")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#0d1f14", padx=16, pady=12)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        dialog_w, dialog_h = 780, 560
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

        self.current_tab = 0
        self.current_page = 0
        self.cards: Dict[str, Dict[str, Any]] = {}
        self.plaque_widgets: Dict[str, Dict[str, Any]] = {}
        self._photo_cache: Dict[str, ImageTk.PhotoImage] = {}
        self._page_frames: Dict[int, tkinter.Frame] = {}

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.bind("<Left>", lambda e: self._prev_page() if self.current_tab == 0 else None)
        self.bind("<Right>", lambda e: self._next_page() if self.current_tab == 0 else None)
        self.focus_set()

    def _is_character_unlocked(self, char_id: str) -> bool:
        """Evaluates whether the given character persona is unlocked."""
        if char_id in ("julian", "tiffany"):
            return True

        save_data = getattr(getattr(self.app, "save_manager", None), "data", None)
        if save_data and hasattr(save_data, "unlocked_costumes") and char_id in save_data.unlocked_costumes:
            return True

        haunted = getattr(self.app, "haunted", None)

        if char_id == "malphas":
            if haunted and (getattr(haunted, "unlocked_cursed_stakes", False) or getattr(haunted, "unlocked_exorcist", False)):
                return True
            if save_data and hasattr(save_data, "achievements") and getattr(save_data.achievements, "exorcist", False):
                return True
            return False

        if char_id == "uriel":
            if save_data and hasattr(save_data, "achievements") and getattr(save_data.achievements, "exorcist", False):
                return True
            if haunted and getattr(haunted, "unlocked_exorcist", False):
                return True
            return False

        if char_id == "mortimer":
            if save_data and hasattr(save_data, "achievements") and getattr(save_data.achievements, "cursed_survivor", False):
                return True
            hs = getattr(save_data, "highscores", None) or getattr(save_data, "high_scores", None)
            if hs and getattr(hs, "peak_bankroll", 0) >= 5000:
                return True
            if haunted and getattr(haunted, "unlocked_haunted_deck", False):
                return True
            return False

        return False

    def _build_ui(self):
        # Header banner
        header_frame = tkinter.Frame(self, background="#0d1f14")
        header_frame.pack(fill="x", pady=(0, 4))

        tkinter.Label(
            header_frame, text="🎩 CASINO WARDROBE & HALL OF FAME",
            font=("Arial", 12, "bold"), fg="#ffd700", background="#0d1f14"
        ).pack(anchor="center")

        # Tab Navigation Bar
        tab_nav_frame = tkinter.Frame(self, background="#0d1f14")
        tab_nav_frame.pack(fill="x", pady=(2, 6))

        self.btn_tab_wardrobe = tkinter.Button(
            tab_nav_frame, text="🎩 Wardrobe Closet", font=("Arial", 9, "bold"),
            background="#2e7d32", fg="white", activebackground="#388e3c",
            activeforeground="white", relief="raised", borderwidth=2, cursor="hand2",
            padx=16, pady=3, command=lambda: self._switch_tab(0)
        )
        self.btn_tab_wardrobe.pack(side="left", padx=(0, 8))

        self.btn_tab_hof = tkinter.Button(
            tab_nav_frame, text="🏆 Hall of Fame & Trophy Shelf", font=("Arial", 9, "bold"),
            background="#1e382b", fg="#cfd8dc", activebackground="#2e5441",
            activeforeground="white", relief="raised", borderwidth=1, cursor="hand2",
            padx=16, pady=3, command=lambda: self._switch_tab(1)
        )
        self.btn_tab_hof.pack(side="left")

        # Container Frames for Tabs
        self.content_container = tkinter.Frame(self, background="#0d1f14")
        self.content_container.pack(fill="both", expand=True)

        self.tab_wardrobe_frame = tkinter.Frame(self.content_container, background="#0d1f14")
        self.tab_hof_frame = tkinter.Frame(self.content_container, background="#0d1f14")

        # Build Tab 1: Wardrobe
        self._build_wardrobe_tab()

        # Build Tab 2: Hall of Fame
        self._build_hof_tab()

        # Footer with Close button
        footer_frame = tkinter.Frame(self, background="#0d1f14")
        footer_frame.pack(fill="x", pady=(6, 0))

        close_btn = tkinter.Button(
            footer_frame, text="Close Dialog", font=("Arial", 10, "bold"),
            background="#37474f", fg="white", activebackground="#455a64",
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_close
        )
        close_btn.pack(anchor="center")

        # Show initial tab
        self._switch_tab(0)

    def _switch_tab(self, tab_idx: int):
        """Switches between Wardrobe Closet (0) and Trophy Shelf (1)."""
        self.current_tab = tab_idx
        if tab_idx == 0:
            self.tab_hof_frame.pack_forget()
            self.tab_wardrobe_frame.pack(fill="both", expand=True)
            self.btn_tab_wardrobe.configure(background="#2e7d32", fg="white", borderwidth=2)
            self.btn_tab_hof.configure(background="#1e382b", fg="#cfd8dc", borderwidth=1)
        else:
            self.tab_wardrobe_frame.pack_forget()
            self.tab_hof_frame.pack(fill="both", expand=True)
            self.btn_tab_hof.configure(background="#2e7d32", fg="white", borderwidth=2)
            self.btn_tab_wardrobe.configure(background="#1e382b", fg="#cfd8dc", borderwidth=1)
            self._refresh_hof_display()

    # ------------------------------------------------------------------------
    # Tab 1: Wardrobe Closet Implementation
    # ------------------------------------------------------------------------

    def _build_wardrobe_tab(self):
        nav_frame = tkinter.Frame(self.tab_wardrobe_frame, background="#0d1f14")
        nav_frame.pack(fill="x", pady=(0, 4))

        self.prev_btn = tkinter.Button(
            nav_frame, text="◀ Previous", font=("Arial", 9, "bold"),
            background="#1e382b", fg="#e0e0e0", activebackground="#2e5441",
            activeforeground="white", relief="raised", borderwidth=1, cursor="hand2",
            padx=10, command=self._prev_page
        )
        self.prev_btn.pack(side="left")

        self.page_lbl = tkinter.Label(
            nav_frame, text="", font=("Arial", 10, "bold"),
            fg="#ffd700", background="#0d1f14"
        )
        self.page_lbl.pack(side="left", expand=True)

        self.next_btn = tkinter.Button(
            nav_frame, text="Next ▶", font=("Arial", 9, "bold"),
            background="#1e382b", fg="#e0e0e0", activebackground="#2e5441",
            activeforeground="white", relief="raised", borderwidth=1, cursor="hand2",
            padx=10, command=self._next_page
        )
        self.next_btn.pack(side="right")

        cards_container = tkinter.Frame(self.tab_wardrobe_frame, background="#0d1f14")
        cards_container.pack(fill="both", expand=True, pady=(0, 2))

        for p_idx, p_data in enumerate(self.PAGE_CONFIG):
            p_frame = tkinter.Frame(cards_container, background="#0d1f14")
            self._page_frames[p_idx] = p_frame

            for c_idx, char_id in enumerate(p_data["characters"]):
                row = c_idx // 2
                col = c_idx % 2
                profile = CHARACTERS.get(char_id, CHARACTERS["julian"])
                unlocked = self._is_character_unlocked(char_id)
                is_equipped = (self.app.dealer_actor.current_character == char_id)

                card_frame = tkinter.LabelFrame(
                    p_frame, text=f" {profile.name} ", font=("Arial", 10, "bold"),
                    fg=profile.nameplate_fg, background="#12271c", padx=8, pady=6, relief="groove"
                )
                card_frame.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")
                p_frame.grid_columnconfigure(col, weight=1)
                p_frame.grid_rowconfigure(row, weight=1)

                # Left side: Bust portrait
                left_col = tkinter.Frame(card_frame, background="#12271c")
                left_col.pack(side="left", padx=(0, 8), fill="y")

                bust_pil = self.app.dealer_actor.get_bust_image(char_id, scale_factor=1.0)
                if bust_pil:
                    photo = ImageTk.PhotoImage(bust_pil, master=self)
                    self._photo_cache[f"bust_{char_id}"] = photo
                    portrait_lbl = tkinter.Label(left_col, image=photo, background="#0a1a12", relief="ridge", borderwidth=1)
                    portrait_lbl.pack(pady=(2, 4))
                else:
                    portrait_lbl = tkinter.Label(left_col, text="[No Bust]", width=12, height=6, background="#0a1a12", fg="white")
                    portrait_lbl.pack(pady=(2, 4))

                voice_btn = tkinter.Button(
                    left_col, text="🔊 Voice", font=("Arial", 8, "bold"),
                    background="#1e382b", fg="#e0e0e0", activebackground="#2e5441",
                    activeforeground="white", relief="raised", borderwidth=1, cursor="hand2",
                    command=lambda cid=char_id: self._play_voice_preview(cid)
                )
                voice_btn.pack(fill="x", pady=(2, 0))

                # Right side: Title, Unlock status, Lore, Equip Button
                right_col = tkinter.Frame(card_frame, background="#12271c")
                right_col.pack(side="left", fill="both", expand=True)

                title_lbl = tkinter.Label(
                    right_col, text=profile.title, font=("Arial", 9, "bold"),
                    fg=profile.nameplate_fg, background="#12271c", anchor="w"
                )
                title_lbl.pack(fill="x")

                crit_text = self.UNLOCK_CRITERIA.get(char_id, "")
                if unlocked:
                    status_text = "✓ Unlocked"
                    status_col = "#69f0ae"
                else:
                    status_text = f"🔒 {crit_text}"
                    status_col = "#ff8a80"

                crit_lbl = tkinter.Label(
                    right_col, text=status_text, font=("Arial", 8, "bold" if unlocked else "italic"),
                    fg=status_col, background="#12271c", anchor="w"
                )
                crit_lbl.pack(fill="x", pady=(1, 3))

                lore_lbl = tkinter.Label(
                    right_col, text=profile.lore, font=("Arial", 8),
                    fg="#b0bec5", background="#12271c", wraplength=210, justify="left", anchor="w"
                )
                lore_lbl.pack(fill="both", expand=True, pady=(0, 4))

                action_frame = tkinter.Frame(right_col, background="#12271c")
                action_frame.pack(fill="x", side="bottom")

                action_widget: Any
                if is_equipped:
                    action_widget = tkinter.Label(
                        action_frame, text="✦ EQUIPPED", font=("Arial", 9, "bold"),
                        fg="#ffd700", background="#1a3a2a", relief="ridge", borderwidth=1, padx=6, pady=3
                    )
                    action_widget.pack(fill="x")
                elif unlocked:
                    action_widget = tkinter.Button(
                        action_frame, text="Equip Costume", font=("Arial", 9, "bold"),
                        background="#2e7d32", fg="white", activebackground="#388e3c",
                        activeforeground="white", relief="raised", borderwidth=2, cursor="hand2",
                        command=lambda cid=char_id: self._equip_costume(cid)
                    )
                    action_widget.pack(fill="x")
                else:
                    action_widget = tkinter.Button(
                        action_frame, text="Locked", font=("Arial", 9, "bold"),
                        background="#263238", fg="#78909c", state="disabled", relief="flat"
                    )
                    action_widget.pack(fill="x")

                self.cards[char_id] = {
                    "frame": card_frame,
                    "unlocked": unlocked,
                    "is_equipped": is_equipped,
                    "action_widget": action_widget,
                    "action_frame": action_frame,
                }

        initial_page = 0
        current_char = getattr(getattr(self.app, "dealer_actor", None), "current_character", "julian")
        for p_idx, p_data in enumerate(self.PAGE_CONFIG):
            if current_char in p_data["characters"]:
                initial_page = p_idx
                break
        self._switch_page(initial_page)

    def _switch_page(self, page_idx: int):
        total = len(self.PAGE_CONFIG)
        self.current_page = max(0, min(total - 1, page_idx))
        for p_idx, frame in self._page_frames.items():
            if p_idx == self.current_page:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        cfg = self.PAGE_CONFIG[self.current_page]
        self.page_lbl.config(text=f"Page {self.current_page + 1} of {total} : {cfg['title']}")
        self.prev_btn.config(state="normal" if self.current_page > 0 else "disabled")
        self.next_btn.config(state="normal" if self.current_page < total - 1 else "disabled")

    def _prev_page(self):
        if self.current_page > 0:
            self._switch_page(self.current_page - 1)

    def _next_page(self):
        if self.current_page < len(self.PAGE_CONFIG) - 1:
            self._switch_page(self.current_page + 1)

    def _play_voice_preview(self, char_id: str):
        profile = CHARACTERS.get(char_id)
        if profile and hasattr(self.app, "sound_manager"):
            self.app.sound_manager.play_haunted_sound(profile.audio_cue)

    def _equip_costume(self, char_id: str):
        self.app.dealer_actor.equip_costume(char_id)
        if hasattr(self.app, "save_manager") and hasattr(self.app.save_manager, "data"):
            self.app.save_manager.data.equipped_costume = char_id
            self.app.save_manager.save()

        self.app._update_dealer_avatar()
        if hasattr(self.app, "sound_manager") and hasattr(self.app.sound_manager, "play_chip_add"):
            self.app.sound_manager.play_chip_add()

        self._refresh_card_actions()

    def _refresh_card_actions(self):
        for char_id, card_data in self.cards.items():
            is_equipped = (self.app.dealer_actor.current_character == char_id)
            card_data["is_equipped"] = is_equipped
            action_frame = card_data["action_frame"]
            for child in action_frame.winfo_children():
                child.destroy()

            unlocked = card_data["unlocked"]
            if is_equipped:
                w = tkinter.Label(
                    action_frame, text="✦ EQUIPPED", font=("Arial", 9, "bold"),
                    fg="#ffd700", background="#1a3a2a", relief="ridge", borderwidth=1, padx=6, pady=3
                )
                w.pack(fill="x")
            elif unlocked:
                w = tkinter.Button(
                    action_frame, text="Equip Costume", font=("Arial", 9, "bold"),
                    background="#2e7d32", fg="white", activebackground="#388e3c",
                    activeforeground="white", relief="raised", borderwidth=2, cursor="hand2",
                    command=lambda cid=char_id: self._equip_costume(cid)
                )
                w.pack(fill="x")
            else:
                w = tkinter.Button(
                    action_frame, text="Locked", font=("Arial", 9, "bold"),
                    background="#263238", fg="#78909c", state="disabled", relief="flat"
                )
                w.pack(fill="x")

            card_data["action_widget"] = w

    # ------------------------------------------------------------------------
    # Tab 2: Hall of Fame & Trophy Shelf Implementation
    # ------------------------------------------------------------------------

    def _build_hof_tab(self):
        # 1. Statistics Summary Card
        records_frame = tkinter.LabelFrame(
            self.tab_hof_frame, text=" 📊 All-Time Casino Records ",
            font=("Arial", 10, "bold"), fg="#ffd700", background="#12271c",
            padx=10, pady=6, relief="groove"
        )
        records_frame.pack(fill="x", pady=(0, 8))

        self.lbl_peak_record = tkinter.Label(
            records_frame, text="• Peak Bankroll: $1,000", font=("Arial", 9, "bold"),
            fg="#69f0ae", background="#12271c"
        )
        self.lbl_peak_record.grid(row=0, column=0, sticky="w", padx=(0, 16), pady=2)

        self.lbl_streak_record = tkinter.Label(
            records_frame, text="• Longest Win Streak: 0 hands", font=("Arial", 9, "bold"),
            fg="#ffd54f", background="#12271c"
        )
        self.lbl_streak_record.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=2)

        self.lbl_clears_record = tkinter.Label(
            records_frame, text="• Hell's Table Clears: 0", font=("Arial", 9, "bold"),
            fg="#ff8a80", background="#12271c"
        )
        self.lbl_clears_record.grid(row=0, column=2, sticky="w", pady=2)

        self.lbl_hands_record = tkinter.Label(
            records_frame, text="• Hands Won / Played: 0 / 0 (0.0% Win Rate)", font=("Arial", 9),
            fg="#e0e0e0", background="#12271c"
        )
        self.lbl_hands_record.grid(row=1, column=0, columnspan=2, sticky="w", pady=2)

        self.lbl_bjs_record = tkinter.Label(
            records_frame, text="• Total Blackjacks: 0", font=("Arial", 9),
            fg="#80d8ff", background="#12271c"
        )
        self.lbl_bjs_record.grid(row=1, column=2, sticky="w", pady=2)

        # 2. 6 Core Achievement Plaques Grid (2 cols x 3 rows)
        plaques_container = tkinter.LabelFrame(
            self.tab_hof_frame, text=" 🏆 Core Casino Achievements ",
            font=("Arial", 10, "bold"), fg="#ffd700", background="#12271c",
            padx=8, pady=6, relief="groove"
        )
        plaques_container.pack(fill="both", expand=True)

        for idx, spec in enumerate(self.ACHIEVEMENT_SPECS):
            row = idx // 2
            col = idx % 2

            p_frame = tkinter.Frame(
                plaques_container, background="#0f2218", relief="ridge", borderwidth=1,
                padx=8, pady=4
            )
            p_frame.grid(row=row, column=col, padx=6, pady=4, sticky="nsew")
            plaques_container.grid_columnconfigure(col, weight=1)
            plaques_container.grid_rowconfigure(row, weight=1)

            # Plaque title and reward
            header_sub = tkinter.Frame(p_frame, background="#0f2218")
            header_sub.pack(fill="x")

            title_lbl = tkinter.Label(
                header_sub, text=spec["title"], font=("Arial", 9, "bold"),
                fg="#ffd700", background="#0f2218"
            )
            title_lbl.pack(side="left")

            reward_lbl = tkinter.Label(
                header_sub, text=f"[{spec['reward']}]", font=("Arial", 8, "italic"),
                fg="#80cbc4", background="#0f2218"
            )
            reward_lbl.pack(side="right")

            # Description
            desc_lbl = tkinter.Label(
                p_frame, text=spec["desc"], font=("Arial", 8),
                fg="#b0bec5", background="#0f2218", wraplength=290, justify="left"
            )
            desc_lbl.pack(fill="x", pady=(2, 3), anchor="w")

            # Status badge
            status_lbl = tkinter.Label(
                p_frame, text="🔒 LOCKED", font=("Arial", 8, "bold"),
                fg="#ff8a80", background="#0f2218", anchor="w"
            )
            status_lbl.pack(fill="x")

            self.plaque_widgets[spec["id"]] = {
                "frame": p_frame,
                "status_lbl": status_lbl,
                "spec": spec,
            }

    def _refresh_hof_display(self):
        """Refreshes all-time statistics and achievement plaques in Tab 2."""
        save_data = getattr(getattr(self.app, "save_manager", None), "data", None)
        if not save_data:
            return

        hs = save_data.highscores
        self.lbl_peak_record.configure(text=f"• Peak Bankroll: ${hs.peak_bankroll:,}")
        self.lbl_streak_record.configure(text=f"• Longest Win Streak: {hs.longest_win_streak:,} hands")
        self.lbl_clears_record.configure(text=f"• Hell's Table Clears: {hs.hell_table_clears:,}")

        pct = (hs.total_hands_won / hs.total_hands_played * 100.0) if hs.total_hands_played > 0 else 0.0
        self.lbl_hands_record.configure(
            text=f"• Hands Won / Played: {hs.total_hands_won:,} / {hs.total_hands_played:,} ({pct:.1f}% Win Rate)"
        )
        self.lbl_bjs_record.configure(text=f"• Total Blackjacks: {hs.total_blackjacks:,}")

        achs = save_data.achievements
        for ach_id, p_info in self.plaque_widgets.items():
            unlocked = getattr(achs, ach_id, False)
            spec = p_info["spec"]
            frame = p_info["frame"]
            lbl = p_info["status_lbl"]

            if unlocked:
                frame.configure(background="#132f20", highlightthickness=1, highlightbackground="#ffd700")
                lbl.configure(
                    text="✓ UNLOCKED", fg="#69f0ae", background="#132f20"
                )
            else:
                frame.configure(background="#0f2218", highlightthickness=0)
                lbl.configure(
                    text=f"🔒 LOCKED: {spec['criteria']}", fg="#ff8a80", background="#0f2218"
                )

    def _on_close(self):
        """Dismisses the wardrobe dialog gracefully."""
        try:
            if hasattr(self.app, "_wardrobe_dialog"):
                self.app._wardrobe_dialog = None
            self.destroy()
        except Exception:
            pass
