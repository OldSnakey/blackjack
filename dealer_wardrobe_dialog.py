"""
Dealer Wardrobe & Dressing Room Dialog for Blackjack.

Provides:
- 4 interactive character cards for Julian, Malphas, Uriel, and Mortimer.
- High-resolution bust preview, title, lore, and audio voice preview.
- Dynamic unlock criteria checking against persistent save achievements and table milestones.
- Instant costume equipping with table avatar and stage synchronization.
- Disk persistence via SaveManager.
"""

from __future__ import annotations

import tkinter
from typing import Any, Dict
from PIL import ImageTk

from dealer_actor import CHARACTERS, CharacterProfile


class WardrobeDialog(tkinter.Toplevel):
    """
    Dealer Wardrobe & Dressing Room Modal.
    Displays character roster cards with unlocks, lore, audio preview, and equipping controls.
    """

    UNLOCK_CRITERIA: Dict[str, str] = {
        "julian": "Default Croupier (Always Unlocked)",
        "malphas": "Trigger or encounter Hell's Table",
        "uriel": "Banish The Pit Fiend at Hell's Table (Exorcist)",
        "mortimer": "Survive Card 13 or attain $5,000 Bankroll",
    }

    def __init__(self, parent: tkinter.Tk, app: Any):
        super().__init__(parent)
        self.app = app
        self.title("🎩 Dealer Wardrobe & Dressing Room")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#0d1f14", padx=16, pady=14)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        dialog_w, dialog_h = 760, 520
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

        self.cards: Dict[str, Dict[str, Any]] = {}
        self._photo_cache: Dict[str, ImageTk.PhotoImage] = {}

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.focus_set()

    def _is_character_unlocked(self, char_id: str) -> bool:
        """Evaluates whether the given character persona is unlocked."""
        if char_id == "julian":
            return True

        # Check save data explicit unlocks
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
        header_frame.pack(fill="x", pady=(0, 10))

        tkinter.Label(
            header_frame, text="🎩 CASINO WARDROBE & DEALER DRESSING ROOM",
            font=("Arial", 12, "bold"), fg="#ffd700", background="#0d1f14"
        ).pack(anchor="center")

        tkinter.Label(
            header_frame, text="Select your active table dealer persona. Unlock legendary croupiers through casino milestones.",
            font=("Arial", 9, "italic"), fg="#a5d6a7", background="#0d1f14"
        ).pack(anchor="center", pady=(2, 0))

        # Cards Container Grid (2x2)
        cards_container = tkinter.Frame(self, background="#0d1f14")
        cards_container.pack(fill="both", expand=True, pady=(0, 10))

        char_order = ["julian", "malphas", "uriel", "mortimer"]
        for idx, char_id in enumerate(char_order):
            row = idx // 2
            col = idx % 2
            profile = CHARACTERS.get(char_id, CHARACTERS["julian"])
            unlocked = self._is_character_unlocked(char_id)
            is_equipped = (self.app.dealer_actor.current_character == char_id)

            card_frame = tkinter.LabelFrame(
                cards_container, text=f" {profile.name} ", font=("Arial", 10, "bold"),
                fg=profile.nameplate_fg, background="#12271c", padx=8, pady=6, relief="groove"
            )
            card_frame.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")
            cards_container.grid_columnconfigure(col, weight=1)
            cards_container.grid_rowconfigure(row, weight=1)

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

            # Voice preview button under portrait
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

            # Status / Criteria badge
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

            # Lore
            lore_lbl = tkinter.Label(
                right_col, text=profile.lore, font=("Arial", 8),
                fg="#b0bec5", background="#12271c", wraplength=210, justify="left", anchor="w"
            )
            lore_lbl.pack(fill="both", expand=True, pady=(0, 4))

            # Action Frame
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

        # Footer with Close button
        footer_frame = tkinter.Frame(self, background="#0d1f14")
        footer_frame.pack(fill="x", pady=(4, 0))

        close_btn = tkinter.Button(
            footer_frame, text="Close Dressing Room", font=("Arial", 10, "bold"),
            background="#37474f", fg="white", activebackground="#455a64",
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_close
        )
        close_btn.pack(anchor="center")

    def _play_voice_preview(self, char_id: str):
        """Plays the selected character's vocal accent audio cue."""
        profile = CHARACTERS.get(char_id)
        if profile and hasattr(self.app, "sound_manager"):
            self.app.sound_manager.play_haunted_sound(profile.audio_cue)

    def _equip_costume(self, char_id: str):
        """Equips the chosen character costume, updates the live stage, and persists to save."""
        self.app.dealer_actor.equip_costume(char_id)

        # Update persistent save
        if hasattr(self.app, "save_manager") and hasattr(self.app.save_manager, "data"):
            self.app.save_manager.data.equipped_costume = char_id
            self.app.save_manager.save()

        # Update live game avatar & nameplate
        self.app._update_dealer_avatar()
        if hasattr(self.app, "sound_manager") and hasattr(self.app.sound_manager, "play_chip_add"):
            self.app.sound_manager.play_chip_add()

        # Refresh cards UI
        self._refresh_card_actions()

    def _refresh_card_actions(self):
        """Updates equip button states across all character cards."""
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

    def _on_close(self):
        """Dismisses the wardrobe dialog gracefully."""
        try:
            if hasattr(self.app, "_wardrobe_dialog"):
                self.app._wardrobe_dialog = None
            self.destroy()
        except Exception:
            pass
