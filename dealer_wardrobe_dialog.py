"""
Dealer Wardrobe & Casino Hall of Fame Dialog for Blackjack.

Provides:
- Tab 1: 🎩 Wardrobe Closet
  - 8 interactive procedural pixel art character cards for Julian, Tiffany, Malphas, Uriel, Mortimer,
    Selene, Vladimir, and Dummy.
  - In-card costume carousel [◄] Costume (1/N) [►] architecture.
  - High-resolution bust preview in recessed gold picture frame with dark vignette backdrop.
  - Title, lore in crisp m5x7, and procedural pixel audio voice preview.
  - Dynamic unlock criteria checking against persistent save achievements and table milestones.
  - Instant costume equipping with table avatar and stage synchronization.
  - Empty grid slots balanced with a recessed Mystery Dealer silhouette card.
- Tab 2: 🏆 Hall of Fame & Trophy Shelf
  - All-time casino records banner in a 9-slice pixel plaque.
  - 8 visual achievement plaques with glowing gold frames when unlocked.
- Direct tab activation via `initial_tab` (`<Shift-W>` for Wardrobe, `<Shift-H>` for Hall of Fame).
- Disk persistence via SaveManager.
"""

from __future__ import annotations

import tkinter
from typing import Any, Dict, List, Optional
from PIL import ImageTk

from dealer_actor import CHARACTERS, CharacterProfile, CostumeVariant
from pixel_ui import (
    CanvasPixelButton,
    CanvasPixelPanel,
    get_pixel_icon,
    get_role_font,
    get_element_font,
    get_header_font,
    get_button_font,
    get_badge_font,
    get_body_font,
)


CHARACTER_VOICE_QUOTES: Dict[str, str] = {
    "julian": (
        "Care for another card, friend? Fortune favors the steady hand and a calm mind at my table."
    ),
    "tiffany": (
        "Place your bets, darling! Let's see if that radiant charm of yours brings a natural twenty-one."
    ),
    "dummy": (
        "Beep boop! All articulation servos calibrated. Ready to run high-stakes table stress tests!"
    ),
    "malphas": (
        "Your mortal soul burns brightly on this felt... Dare you double down into the inferno?!"
    ),
    "uriel": (
        "Fear no shadows in the dark, traveler. Sacred light shall guide your wager to grace."
    ),
    "mortimer": (
        "Rattle, rattle! The clock strikes thirteen, and every debt in the crypt must be settled!"
    ),
    "selene": (
        "Neural scan locked. Card shoe variance analyzed. Probability matrix favors an aggressive split."
    ),
    "vladimir": (
        "Centuries across the shadowy salons of Europe have taught me: the night belongs to patience."
    ),
}

COSTUME_VOICE_QUOTES: Dict[str, str] = {
    "tiffany_velvet": (
        "Velvet cards and sharp minds. Let's see how well you handle the house edge tonight, darling!"
    ),
}


class DealerCardPanel(tkinter.Canvas):
    """
    Renders a 436x222 procedural retro-casino pixel art card for a dealer character.
    Features:
    - 9-slice notched CanvasPixelPanel with corner rivets.
    - Equipped glowing gold outer border highlight (#ecc260).
    - Left column: 128x128 recessed gold portrait frame with dark background + 128x32 Voice button at cy=180.
    - Right column:
      - y=16: Dealer Name (m6x11plus @ -32) + Status badge (m6x11plus @ -16) right-aligned at x=414.
      - y=48: Subtitle (m6x11plus @ -16).
      - y=74: Costume Carousel [◄] (24x24 at x=176, y=86) + label strip (188x24 at x=192, y=74) + [►] (24x24 at x=396, y=86).
      - y=104: 3-line lore blurb (m5x7 @ -16 in #d8e2dc, width=250).
      - y=180: Equip / Equipped button (252x32, scale=3, center cx=290, cy=180) sharing baseline with Voice button!
    """

    def __init__(
        self,
        master: Any,
        char_id: str,
        profile: CharacterProfile,
        dialog: "WardrobeDialog",
        is_equipped: bool,
        unlocked: bool,
        scale: int = 2,
        **kwargs,
    ):
        super().__init__(
            master,
            width=436,
            height=222,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            **kwargs,
        )
        self.char_id = char_id
        self.profile = profile
        self.dialog = dialog
        self.scale = scale
        self.unlocked = unlocked
        self.is_equipped = is_equipped

        self.costumes: List[CostumeVariant] = list(profile.get_costumes())
        self.costume_idx = 0
        active_costume = getattr(getattr(dialog.app, "dealer_actor", None), "current_costume", char_id)
        for idx, c in enumerate(self.costumes):
            if c.costume_id == active_costume:
                self.costume_idx = idx
                break

        # Dialogue speech balloon tracking
        self._speech_timer_id: Optional[str] = None
        self._speech_full_text: str = ""
        self._speech_char_idx: int = 0
        self._speech_text_id: Optional[int] = None
        self._speech_active: bool = False

        # 1. 9-slice background panel with corner brass rivets
        border_col = "#ecc260" if is_equipped else "#06140b"
        inner_hi_col = "#ffd700" if is_equipped else "#1f4d30"
        self.panel = CanvasPixelPanel(
            self,
            x=0,
            y=0,
            width=436,
            height=222,
            bg="#0c2917",
            border=border_col,
            inner_hi=inner_hi_col,
            inner_sh="#071a0e",
            rivet_color="#d4af37",
            scale=scale,
            recessed=True,
            anchor="nw",
            tag="card_panel",
        )

        # 2. Left Column: 128x128 Recessed Gold Portrait Frame
        self.portrait_frame = CanvasPixelPanel(
            self,
            x=16,
            y=16,
            width=128,
            height=128,
            bg="#060c08",
            border="#8a6d1b",
            inner_hi="#12271c",
            inner_sh="#040805",
            rivet_color=None,
            scale=scale,
            recessed=True,
            anchor="nw",
            tag="portrait_frame",
        )

        bust_pil = dialog.app.dealer_actor.get_bust_image(char_id, scale_factor=1.0)
        if bust_pil:
            self.portrait_photo = ImageTk.PhotoImage(bust_pil, master=self)
            dialog._photo_cache[f"bust_{char_id}"] = self.portrait_photo
            self.portrait_item = self.create_image(80, 80, image=self.portrait_photo, anchor="center")
        else:
            self.portrait_photo = None
            self.portrait_item = self.create_text(
                80, 80, text="[No Bust]", font=get_role_font("body", size_override=-14), fill="#b0bec5", anchor="center"
            )

        # Voice Button: centered at cx=80, cy=180, width=128, height=32, scale=2
        self.voice_btn = CanvasPixelButton(
            self,
            x=80,
            y=180,
            width=128,
            height=32,
            text="🔊 Voice",
            theme="neutral",
            font=get_role_font("button", size_override=-14),
            scale=2,
            command=self._play_voice,
        )

        # 3. Right Column:
        # y=16: Dealer Name (m6x11plus @ -32) - spans full width
        self.name_text_id = self.create_text(
            164,
            16,
            text=profile.name.upper(),
            font=get_role_font("header", size_override=-32),
            fill="#ffd700",
            anchor="nw",
        )

        # y=48: Subtitle (m6x11plus @ -16) on left + Status Badge (m6x11plus @ -16) on right at x=414
        self.subtitle_text_id = self.create_text(
            164,
            48,
            text=profile.title,
            font=get_role_font("header", size_override=-16),
            fill=profile.nameplate_fg,
            anchor="nw",
        )

        status_text, status_col = self._get_status_info()
        self.status_badge_id = self.create_text(
            414,
            48,
            text=status_text,
            font=get_role_font("badge", size_override=-16),
            fill=status_col,
            anchor="ne",
        )

        # y=74: In-Card Costume Carousel Row
        # [◄] button: center x=176, y=86
        has_multi = len(self.costumes) > 1
        self.prev_costume_btn = CanvasPixelButton(
            self,
            x=176,
            y=86,
            width=24,
            height=24,
            text="◄",
            theme="neutral",
            scale=2,
            enabled=has_multi,
            command=self._prev_costume,
        )

        # Carousel label panel: x=192, y=74, w=188, h=24
        self.carousel_panel = CanvasPixelPanel(
            self,
            x=192,
            y=74,
            width=188,
            height=24,
            bg="#08140c",
            border="#040a06",
            inner_hi="#0e2416",
            inner_sh="#020503",
            rivet_color=None,
            scale=scale,
            recessed=True,
            anchor="nw",
            tag="carousel_panel",
        )
        c_label = self._get_carousel_label()
        self.carousel_text_id = self.create_text(
            286,
            86,
            text=c_label,
            font=get_role_font("body", size_override=-16),
            fill="#e0e0e0",
            anchor="center",
        )

        # [►] button: center x=396, y=86
        self.next_costume_btn = CanvasPixelButton(
            self,
            x=396,
            y=86,
            width=24,
            height=24,
            text="►",
            theme="neutral",
            scale=2,
            enabled=has_multi,
            command=self._next_costume,
        )

        # y=104: Lore Blurb (when unlocked) or Unlock Requirement (when locked)
        if self.unlocked:
            self.req_header_id = None
            self.lore_text_id = self.create_text(
                164,
                104,
                text=profile.lore,
                font=get_role_font("body", size_override=-16),
                fill="#d8e2dc",
                width=250,
                anchor="nw",
            )
        else:
            self.req_header_id = self.create_text(
                164,
                102,
                text="🔒 UNLOCK REQUIREMENT:",
                font=get_role_font("header", size_override=-14),
                fill="#ffd54f",
                anchor="nw",
            )
            crit = self.dialog.UNLOCK_CRITERIA.get(self.char_id, "Complete casino objectives to unlock.")
            self.lore_text_id = self.create_text(
                164,
                120,
                text=crit,
                font=get_role_font("body", size_override=-16),
                fill="#f0f4f1",
                width=250,
                anchor="nw",
            )

        # y=180: Equip / Equipped Button: cx=290, cy=180, width=252, height=32, scale=3
        btn_text, btn_theme, btn_enabled, dis_text_color = self._get_action_state()
        self.equip_btn = CanvasPixelButton(
            self,
            x=290,
            y=180,
            width=252,
            height=32,
            text=btn_text,
            theme=btn_theme,
            font=get_role_font("button", size_override=-16),
            scale=3,
            enabled=btn_enabled,
            disabled_text_color=dis_text_color,
            command=self._on_equip_click,
        )

    def _get_status_info(self) -> tuple[str, str]:
        if self.unlocked:
            return ("✓ Unlocked", "#5ce6b5")
        return ("🔒 Locked", "#ff8a80")

    def _get_carousel_label(self) -> str:
        total = len(self.costumes)
        cur = self.costumes[self.costume_idx] if self.costumes else None
        c_name = cur.name if cur else "Default"
        return f"{c_name} ({self.costume_idx + 1}/{total})"

    def _get_action_state(self) -> tuple[str, str, bool, Optional[str]]:
        active_char = getattr(getattr(self.dialog.app, "dealer_actor", None), "current_character", "julian")
        active_costume = getattr(getattr(self.dialog.app, "dealer_actor", None), "current_costume", active_char)

        cur_variant = self.costumes[self.costume_idx] if self.costumes else None
        variant_id = cur_variant.costume_id if cur_variant else self.char_id

        # 2D equipped state check: character AND costume
        # In EQUIPPED state: keep recessed slot sprite (disabled), but override text to bright gold (#ffd700)
        if self.char_id == active_char and variant_id == active_costume:
            return ("✦ EQUIPPED", "gold", False, "#ffd700")

        if not self.unlocked:
            return ("Locked", "neutral", False, None)

        # Unlocked variant ready to equip
        return ("Equip Costume", "green", True, None)

    def _prev_costume(self):
        if len(self.costumes) > 1:
            self.costume_idx = (self.costume_idx - 1) % len(self.costumes)
            self._update_costume_display()

    def _next_costume(self):
        if len(self.costumes) > 1:
            self.costume_idx = (self.costume_idx + 1) % len(self.costumes)
            self._update_costume_display()

    def _update_costume_display(self):
        c_label = self._get_carousel_label()
        self.itemconfigure(self.carousel_text_id, text=c_label)
        btn_text, btn_theme, btn_enabled, dis_text_color = self._get_action_state()
        self.equip_btn.set_text(btn_text)
        self.equip_btn.configure(theme=btn_theme)
        self.equip_btn.set_disabled_text_color(dis_text_color)
        self.equip_btn.set_enabled(btn_enabled)

    def _play_voice(self):
        """Renders speech balloon with directional tail to head and streams Animalese dialogue."""
        # 1. Stop any voices currently playing across all panels in the dialog
        self.dialog._stop_all_voices(except_panel=self)

        # 2. Dismiss any existing voice timer on this card
        self.dismiss_speech_bubble()

        # 3. Resolve character or costume dialogue quote
        cur_variant = self.costumes[self.costume_idx] if self.costumes else None
        costume_id = cur_variant.costume_id if cur_variant else self.char_id
        quote = (
            COSTUME_VOICE_QUOTES.get(costume_id)
            or CHARACTER_VOICE_QUOTES.get(self.char_id)
            or f"Greetings from {self.profile.name}! Welcome to the casino table."
        )
        self._speech_full_text = quote
        self._speech_char_idx = 0
        self._speech_active = True

        # 4. Color Palette from Character Profile
        bg_col = getattr(self.profile, "speech_bg", "#081b10") or "#081b10"
        border_col = getattr(self.profile, "nameplate_fg", "#ffd700") or "#ffd700"
        header_col = border_col
        text_col = "#ffffff"

        # 5. Render speech balloon geometry
        x1, y1, x2, y2 = 146, 14, 422, 162

        # A. Directional pointer tail pointing directly to dealer's head at (98, 52)
        tail_base_top = (147, 44)
        tail_base_bot = (147, 62)
        tail_tip = (98, 52)
        self.create_polygon(
            tail_base_top[0], tail_base_top[1],
            tail_tip[0], tail_tip[1],
            tail_base_bot[0], tail_base_bot[1],
            fill=bg_col,
            outline=border_col,
            width=2,
            tags="speech_bubble",
        )

        # B. Notched retro pixel balloon background
        self.create_rectangle(
            x1 + 2, y1, x2 - 2, y2,
            fill=bg_col,
            outline="",
            tags="speech_bubble",
        )
        self.create_rectangle(
            x1, y1 + 2, x2, y2 - 2,
            fill=bg_col,
            outline="",
            tags="speech_bubble",
        )

        # C. Balloon borders
        self.create_line(x1 + 2, y1, x2 - 2, y1, fill=border_col, width=2, tags="speech_bubble")
        self.create_line(x1 + 2, y2, x2 - 2, y2, fill=border_col, width=2, tags="speech_bubble")
        self.create_line(x1, y1 + 2, x1, tail_base_top[1], fill=border_col, width=2, tags="speech_bubble")
        self.create_line(x1, tail_base_bot[1], x1, y2 - 2, fill=border_col, width=2, tags="speech_bubble")
        self.create_line(x2, y1 + 2, x2, y2 - 2, fill=border_col, width=2, tags="speech_bubble")

        # Seam bridge between tail and balloon interior
        self.create_line(
            147, tail_base_top[1] + 1, 147, tail_base_bot[1] - 1,
            fill=bg_col,
            width=3,
            tags="speech_bubble",
        )

        # D. Header & dismiss button
        self.create_text(
            160, 24,
            text=f"✦ {self.profile.name.upper()}",
            font=get_role_font("header", size_override=-14),
            fill=header_col,
            anchor="nw",
            tags="speech_bubble",
        )
        self.create_text(
            412, 24,
            text="[✕]",
            font=get_role_font("body", size_override=-14),
            fill="#78909c",
            anchor="ne",
            tags="speech_bubble",
        )

        # E. Text body item (starts empty and streams character-by-character)
        self._speech_text_id = self.create_text(
            160, 48,
            text="",
            font=get_role_font("body", size_override=-16),
            fill=text_col,
            width=250,
            anchor="nw",
            tags="speech_bubble",
        )

        # Click bubble to dismiss early
        self.tag_bind("speech_bubble", "<Button-1>", lambda e: self.dismiss_speech_bubble())

        # Lift all bubble elements to top of canvas stack
        self.tag_raise("speech_bubble")

        # 6. Kick off typewriter streaming
        self._stream_speech_step()

    def _stream_speech_step(self):
        """Streams one character to the speech balloon and synthesizes Animalese audio."""
        if not self._speech_active or not self.winfo_exists():
            return

        if self._speech_char_idx < len(self._speech_full_text):
            char = self._speech_full_text[self._speech_char_idx]
            self._speech_char_idx += 1
            if self._speech_text_id:
                self.itemconfigure(
                    self._speech_text_id,
                    text=self._speech_full_text[:self._speech_char_idx]
                )

            # Play procedural Animalese dialogue voice synthesis
            sound_mgr = getattr(self.dialog.app, "sound_manager", None)
            if sound_mgr and hasattr(sound_mgr, "play_dialogue_blip"):
                inflection = "normal"
                tail_c = self._speech_full_text.rstrip()[-1:]
                if tail_c == "?":
                    inflection = "question"
                elif tail_c == "!":
                    inflection = "exclamation"
                elif tail_c == ".":
                    inflection = "period"

                sound_mgr.play_dialogue_blip(
                    self.char_id,
                    char,
                    self._speech_char_idx,
                    inflection=inflection,
                )

            delay = 30
            if char in (".", "!", "?"):
                delay = 60
            elif char in (",", ";", ":", "—"):
                delay = 42

            if self._speech_timer_id:
                try:
                    self.after_cancel(self._speech_timer_id)
                except Exception:
                    pass
                self._speech_timer_id = None

            if self.winfo_exists():
                self._speech_timer_id = self.after(delay, self._stream_speech_step)
        else:
            # Typewriter stream complete - auto dismiss after 4 seconds
            if self._speech_timer_id:
                try:
                    self.after_cancel(self._speech_timer_id)
                except Exception:
                    pass
                self._speech_timer_id = None
            if self.winfo_exists():
                self._speech_timer_id = self.after(4000, self.dismiss_speech_bubble)

    def dismiss_speech_bubble(self):
        """Cancels streaming timer and removes active speech bubble from the canvas."""
        if self._speech_timer_id:
            try:
                self.after_cancel(self._speech_timer_id)
            except Exception:
                pass
            self._speech_timer_id = None
        self._speech_active = False
        self._speech_text_id = None
        self.delete("speech_bubble")

    def destroy(self):
        """Cancels any pending speech timers upon widget destruction."""
        self.dismiss_speech_bubble()
        super().destroy()

    def _on_equip_click(self):
        cur_variant = self.costumes[self.costume_idx] if self.costumes else None
        costume_id = cur_variant.costume_id if cur_variant else self.char_id
        self.dialog._equip_costume(self.char_id, costume_id=costume_id)

    def set_equipped(self, equipped: bool):
        self.is_equipped = bool(equipped)
        if self.is_equipped:
            self.panel.update_palette(border="#ecc260", inner_hi="#ffd700")
        else:
            self.panel.update_palette(border="#06140b", inner_hi="#1f4d30")
        self._update_costume_display()


class MysteryDealerCardPanel(tkinter.Canvas):
    """
    Renders a 436x222 recessed mystery silhouette card for empty grid slots.
    Guarantees the 2x2 grid is always visually balanced on every page.
    """

    def __init__(self, master: Any, scale: int = 2, **kwargs):
        super().__init__(
            master,
            width=436,
            height=222,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            **kwargs,
        )
        self.panel = CanvasPixelPanel(
            self,
            x=0,
            y=0,
            width=436,
            height=222,
            bg="#08140c",
            border="#040a06",
            inner_hi="#0e2416",
            inner_sh="#020503",
            rivet_color="#555544",
            scale=scale,
            recessed=True,
            anchor="nw",
            tag="mystery_card_panel",
        )

        # Recessed silhouette frame at (16, 16)
        self.portrait_frame = CanvasPixelPanel(
            self,
            x=16,
            y=16,
            width=128,
            height=128,
            bg="#040805",
            border="#1c3022",
            inner_hi="#0a150e",
            inner_sh="#020403",
            rivet_color=None,
            scale=scale,
            recessed=True,
            anchor="nw",
            tag="mystery_portrait_frame",
        )

        self.bust_photo = get_pixel_icon("mystery_bust", scale=2, master=self)
        if self.bust_photo:
            self.create_image(80, 80, image=self.bust_photo, anchor="center")

        self.voice_btn = CanvasPixelButton(
            self,
            x=80,
            y=180,
            width=128,
            height=32,
            text="???",
            theme="neutral",
            font=get_role_font("button", size_override=-14),
            scale=2,
            enabled=False,
        )

        # Right column
        self.create_text(
            164,
            16,
            text="??? (COMING SOON)",
            font=get_role_font("header", size_override=-32),
            fill="#8a6d1b",
            anchor="nw",
        )
        self.create_text(
            164,
            48,
            text="Unknown Casino Persona",
            font=get_role_font("header", size_override=-16),
            fill="#3e5948",
            anchor="nw",
        )
        self.create_text(
            414,
            48,
            text="[🔒] Mystery",
            font=get_role_font("badge", size_override=-16),
            fill="#8a6d1b",
            anchor="ne",
        )

        # Carousel placeholder
        self.carousel_panel = CanvasPixelPanel(
            self,
            x=192,
            y=74,
            width=188,
            height=24,
            bg="#050d08",
            border="#020503",
            inner_hi="#09180e",
            inner_sh="#010302",
            rivet_color=None,
            scale=scale,
            recessed=True,
            anchor="nw",
            tag="mystery_carousel_panel",
        )
        self.create_text(
            286,
            86,
            text="Classified",
            font=get_role_font("body", size_override=-16),
            fill="#557766",
            anchor="center",
        )

        self.create_text(
            164,
            104,
            text="A mysterious casino figure shrouded in secrecy. Check back in future table updates!",
            font=get_role_font("body", size_override=-16),
            fill="#557766",
            width=250,
            anchor="nw",
        )

        self.equip_btn = CanvasPixelButton(
            self,
            x=290,
            y=180,
            width=252,
            height=32,
            text="[ Locked ]",
            theme="neutral",
            font=get_role_font("button", size_override=-16),
            scale=3,
            enabled=False,
        )


class WardrobeDialog(tkinter.Toplevel):
    """
    Dealer Wardrobe & Casino Hall of Fame Modal.
    Two-tab interface providing character dressing room and trophy achievements shelf.
    """

    UNLOCK_CRITERIA: Dict[str, str] = {
        "julian": "Default Croupier (Always Unlocked)",
        "tiffany": "Default Croupier (Always Unlocked)",
        "dummy": "Puppet Rig & Testing Lab (Always Unlocked)",
        "malphas": "Trigger or encounter Hell's Table",
        "uriel": "Banish The Pit Fiend at Hell's Table (Exorcist)",
        "mortimer": "Survive Card 13 or attain $5,000 Bankroll",
        "selene": "Answer 5 Card Counting Quizzes (Apprentice Counter)",
        "vladimir": "Answer 20 Card Counting Quizzes (Master Counter)",
    }

    PAGE_CONFIG = [
        {
            "title": "Casino Floor & Workshop",
            "characters": ["julian", "tiffany", "dummy"],
        },
        {
            "title": "Supernatural Legends",
            "characters": ["malphas", "uriel", "mortimer"],
        },
        {
            "title": "The Masters & High Rollers",
            "characters": ["selene", "vladimir"],
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
        {
            "id": "apprentice_counter",
            "title": "🧮 Apprentice Counter",
            "desc": "Answer 5 consecutive card counting drill quizzes correctly.",
            "reward": "Selene (Cyber Croupier) Persona",
            "criteria": "5 Counting Quiz Streak",
        },
        {
            "id": "master_counter",
            "title": "🦇 Master Counter",
            "desc": "Achieve a flawless streak of 20 consecutive correct card counting drill quizzes.",
            "reward": "Vladimir (Crimson Nocturne) Persona",
            "criteria": "20 Counting Quiz Streak",
        },
    ]

    def __init__(self, parent: tkinter.Tk, app: Any, initial_tab: int = 0):
        super().__init__(parent)
        self.app = app
        self.title("🎩 Dealer Wardrobe & Dressing Room")
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#0d1f14", padx=16, pady=10)

        if getattr(app, "_icon_photo", None):
            try:
                self.iconphoto(False, app._icon_photo)
            except Exception:
                pass

        dialog_w = 940
        screen_h = parent.winfo_screenheight() if parent else 800
        dialog_h = min(640, max(540, screen_h - 80))
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
        if initial_tab in (0, 1) and initial_tab != 0:
            self._switch_tab(initial_tab)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.bind("<Left>", lambda e: self._prev_page() if self.current_tab == 0 else None)
        self.bind("<Right>", lambda e: self._next_page() if self.current_tab == 0 else None)
        self.focus_set()

    def _is_character_unlocked(self, char_id: str) -> bool:
        """Evaluates whether the given character persona is unlocked."""
        if char_id in ("julian", "tiffany", "dummy"):
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

        if char_id == "selene":
            if save_data and hasattr(save_data, "achievements") and getattr(save_data.achievements, "apprentice_counter", False):
                return True
            hs = getattr(save_data, "highscores", None)
            if hs and getattr(hs, "best_counting_streak", 0) >= 5:
                return True
            return False

        if char_id == "vladimir":
            if save_data and hasattr(save_data, "achievements") and getattr(save_data.achievements, "master_counter", False):
                return True
            hs = getattr(save_data, "highscores", None)
            if hs and getattr(hs, "best_counting_streak", 0) >= 20:
                return True
            return False

        return False

    def _build_ui(self):
        # 1. Header Banner with Pixel Top Hat
        header_canvas = tkinter.Canvas(
            self, width=908, height=36, background="#0d1f14", highlightthickness=0, borderwidth=0
        )
        header_canvas.pack(fill="x", pady=(0, 2))

        top_hat_icon = get_pixel_icon("top_hat", scale=2, master=self)
        if top_hat_icon:
            self._photo_cache["top_hat_header"] = top_hat_icon
            header_canvas.create_image(174, 18, image=top_hat_icon, anchor="center")

        header_canvas.create_text(
            454,
            18,
            text="CASINO WARDROBE & HALL OF FAME",
            font=get_role_font("header", size_override=-32),
            fill="#ffd700",
            anchor="center",
        )

        # 2. Tab Navigation Bar
        tab_nav_frame = tkinter.Frame(self, background="#0d1f14")
        tab_nav_frame.pack(fill="x", pady=(2, 6))

        tab_canvas = tkinter.Canvas(
            tab_nav_frame, width=908, height=36, background="#0d1f14", highlightthickness=0, borderwidth=0
        )
        tab_canvas.pack(fill="x")

        self.btn_tab_wardrobe = CanvasPixelButton(
            tab_canvas,
            x=115,
            y=18,
            width=210,
            height=32,
            text="🎩 Wardrobe Closet",
            theme="green",
            font=get_role_font("button", size_override=-16),
            scale=2,
            command=lambda: self._switch_tab(0),
        )

        self.btn_tab_hof = CanvasPixelButton(
            tab_canvas,
            x=350,
            y=18,
            width=240,
            height=32,
            text="🏆 Hall of Fame & Trophy Shelf",
            theme="neutral",
            font=get_role_font("button", size_override=-16),
            scale=2,
            command=lambda: self._switch_tab(1),
        )

        # 3. Content Container
        self.content_container = tkinter.Frame(self, background="#0d1f14")
        self.content_container.pack(fill="both", expand=True)

        self.tab_wardrobe_frame = tkinter.Frame(self.content_container, background="#0d1f14")
        self.tab_hof_frame = tkinter.Frame(self.content_container, background="#0d1f14")

        # Build Tabs
        self._build_wardrobe_tab()
        self._build_hof_tab()

        # 4. Footer with Close Button
        footer_frame = tkinter.Frame(self, background="#0d1f14")
        footer_frame.pack(fill="x", pady=(4, 0))

        close_canvas = tkinter.Canvas(
            footer_frame, width=908, height=38, background="#0d1f14", highlightthickness=0, borderwidth=0
        )
        close_canvas.pack(fill="x")

        self.close_btn = CanvasPixelButton(
            close_canvas,
            x=454,
            y=19,
            width=144,
            height=34,
            text="Close Dialog",
            theme="neutral",
            font=get_role_font("button", size_override=-16),
            scale=3,
            command=self._on_close,
        )

        # Show initial tab
        self._switch_tab(0)

    def _switch_tab(self, tab_idx: int):
        """Switches between Wardrobe Closet (0) and Trophy Shelf (1)."""
        self._stop_all_voices()
        self.current_tab = tab_idx
        if tab_idx == 0:
            self.tab_hof_frame.pack_forget()
            self.tab_wardrobe_frame.pack(fill="both", expand=True)
            self.btn_tab_wardrobe.configure(theme="green")
            self.btn_tab_hof.configure(theme="neutral")
        else:
            self.tab_wardrobe_frame.pack_forget()
            self.tab_hof_frame.pack(fill="both", expand=True)
            self.btn_tab_hof.configure(theme="green")
            self.btn_tab_wardrobe.configure(theme="neutral")
            self._refresh_hof_display()
            if hasattr(self, "hof_canvas"):
                self.hof_canvas.yview_moveto(0.0)
                self.hof_scroll_frame.update_idletasks()
                self.hof_canvas.configure(scrollregion=self.hof_canvas.bbox("all"))

    # ------------------------------------------------------------------------
    # Tab 1: Wardrobe Closet Implementation
    # ------------------------------------------------------------------------

    def _build_wardrobe_tab(self):
        # Navigation Bar: Prev | Page X of Y : Title | Next
        nav_canvas = tkinter.Canvas(
            self.tab_wardrobe_frame, width=908, height=32, background="#0d1f14", highlightthickness=0, borderwidth=0
        )
        nav_canvas.pack(fill="x", pady=(0, 4))

        self.prev_btn = CanvasPixelButton(
            nav_canvas,
            x=50,
            y=16,
            width=90,
            height=28,
            text="◀ Previous",
            theme="neutral",
            font=get_role_font("button", size_override=-14),
            scale=2,
            command=self._prev_page,
        )

        self.page_lbl_id = nav_canvas.create_text(
            454,
            16,
            text="",
            font=get_role_font("header", size_override=-16),
            fill="#ffd700",
            anchor="center",
        )
        # Compatibility label proxy for existing test inspections
        self.page_lbl = _TextLabelShim(nav_canvas, self.page_lbl_id)

        self.next_btn = CanvasPixelButton(
            nav_canvas,
            x=858,
            y=16,
            width=90,
            height=28,
            text="Next ▶",
            theme="neutral",
            font=get_role_font("button", size_override=-14),
            scale=2,
            command=self._next_page,
        )

        cards_container = tkinter.Frame(self.tab_wardrobe_frame, background="#0d1f14")
        cards_container.pack(fill="both", expand=True, pady=(0, 2))

        current_char = getattr(getattr(self.app, "dealer_actor", None), "current_character", "julian")

        for p_idx, p_data in enumerate(self.PAGE_CONFIG):
            p_frame = tkinter.Frame(cards_container, background="#0d1f14")
            self._page_frames[p_idx] = p_frame

            characters_list = p_data["characters"]
            # 2x2 grid always has 4 slots (0..3)
            for slot_idx in range(4):
                row = slot_idx // 2
                col = slot_idx % 2
                p_frame.grid_columnconfigure(col, weight=1)
                p_frame.grid_rowconfigure(row, weight=1)

                if slot_idx < len(characters_list):
                    char_id = characters_list[slot_idx]
                    profile = CHARACTERS.get(char_id, CHARACTERS["julian"])
                    unlocked = self._is_character_unlocked(char_id)
                    is_equipped = (current_char == char_id)

                    card_panel = DealerCardPanel(
                        p_frame,
                        char_id=char_id,
                        profile=profile,
                        dialog=self,
                        is_equipped=is_equipped,
                        unlocked=unlocked,
                    )
                    card_panel.grid(row=row, column=col, padx=6, pady=4)

                    self.cards[char_id] = {
                        "panel": card_panel,
                        "frame": card_panel,
                        "unlocked": unlocked,
                        "is_equipped": is_equipped,
                        "action_widget": card_panel.equip_btn,
                        "action_frame": card_panel,
                    }
                else:
                    # Empty grid slot: render mystery silhouette card to balance the 2x2 grid
                    mystery_panel = MysteryDealerCardPanel(p_frame)
                    mystery_panel.grid(row=row, column=col, padx=6, pady=4)

        # Select initial page showing currently equipped character
        initial_page = 0
        for p_idx, p_data in enumerate(self.PAGE_CONFIG):
            if current_char in p_data["characters"]:
                initial_page = p_idx
                break
        self._switch_page(initial_page)

    def _switch_page(self, page_idx: int):
        self._stop_all_voices()
        total = len(self.PAGE_CONFIG)
        self.current_page = max(0, min(total - 1, page_idx))
        for p_idx, frame in self._page_frames.items():
            if p_idx == self.current_page:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        cfg = self.PAGE_CONFIG[self.current_page]
        title_str = f"Page {self.current_page + 1} of {total} : {cfg['title']}"
        self.page_lbl.configure(text=title_str)
        self.prev_btn.set_enabled(self.current_page > 0)
        self.next_btn.set_enabled(self.current_page < total - 1)

    def _prev_page(self):
        if self.current_page > 0:
            self._switch_page(self.current_page - 1)

    def _next_page(self):
        if self.current_page < len(self.PAGE_CONFIG) - 1:
            self._switch_page(self.current_page + 1)

    def _equip_costume(self, char_id: str, costume_id: Optional[str] = None):
        """Swaps active character and costume persona, updates saves, and refreshes UI."""
        self.app.dealer_actor.equip_costume(char_id, costume_id=costume_id)
        if hasattr(self.app, "save_manager") and hasattr(self.app.save_manager, "data"):
            self.app.save_manager.data.equipped_costume = costume_id or char_id
            self.app.save_manager.save()

        self.app._update_dealer_avatar()
        if hasattr(self.app, "sound_manager") and hasattr(self.app.sound_manager, "play_chip_add"):
            self.app.sound_manager.play_chip_add()

        self._refresh_card_actions()

    def _refresh_card_actions(self):
        active_char = self.app.dealer_actor.current_character
        for char_id, card_data in self.cards.items():
            is_equipped = (active_char == char_id)
            card_data["is_equipped"] = is_equipped
            panel = card_data.get("panel")
            if panel and hasattr(panel, "set_equipped"):
                panel.set_equipped(is_equipped)

    # ------------------------------------------------------------------------
    # Tab 2: Hall of Fame & Trophy Shelf Implementation
    # ------------------------------------------------------------------------

    def _build_hof_tab(self):
        # 1. Statistics Summary Card in CanvasPixelPanel
        records_canvas = tkinter.Canvas(
            self.tab_hof_frame, width=908, height=84, background="#0d1f14", highlightthickness=0, borderwidth=0
        )
        records_canvas.pack(fill="x", pady=(0, 6))

        self.records_panel = CanvasPixelPanel(
            records_canvas,
            x=0,
            y=0,
            width=908,
            height=84,
            bg="#0c2917",
            border="#06140b",
            inner_hi="#1f4d30",
            inner_sh="#071a0e",
            rivet_color="#d4af37",
            scale=2,
            recessed=True,
            anchor="nw",
            tag="records_panel",
        )

        records_canvas.create_text(
            16,
            12,
            text="📊 ALL-TIME CASINO RECORDS",
            font=get_role_font("header", size_override=-16),
            fill="#ffd700",
            anchor="nw",
        )

        self.dot_peak_record = records_canvas.create_text(
            24, 41, text="•", font=get_role_font("badge", size_override=-16), fill="#5ce6b5", anchor="nw"
        )
        self.lbl_peak_record = records_canvas.create_text(
            36, 38, text="Peak Bankroll: $1,000", font=get_role_font("badge", size_override=-16), fill="#5ce6b5", anchor="nw"
        )
        self.dot_streak_record = records_canvas.create_text(
            330, 41, text="•", font=get_role_font("badge", size_override=-16), fill="#ffd54f", anchor="nw"
        )
        self.lbl_streak_record = records_canvas.create_text(
            342, 38, text="Longest Win Streak: 0 hands", font=get_role_font("badge", size_override=-16), fill="#ffd54f", anchor="nw"
        )
        self.dot_clears_record = records_canvas.create_text(
            660, 41, text="•", font=get_role_font("badge", size_override=-16), fill="#ff8a80", anchor="nw"
        )
        self.lbl_clears_record = records_canvas.create_text(
            672, 38, text="Hell's Table Clears: 0", font=get_role_font("badge", size_override=-16), fill="#ff8a80", anchor="nw"
        )

        self.lbl_hands_record = records_canvas.create_text(
            24, 60, text="• Hands Won / Played: 0 / 0 (0.0% Win Rate)", font=get_role_font("body", size_override=-16), fill="#e0e0e0", anchor="nw"
        )
        self.lbl_bjs_record = records_canvas.create_text(
            660, 60, text="• Total Blackjacks: 0", font=get_role_font("body", size_override=-16), fill="#80d8ff", anchor="nw"
        )
        self._records_canvas = records_canvas

        # 2. Scrollable Canvas for 8 Achievement Plaques
        plaques_container = tkinter.Frame(self.tab_hof_frame, background="#0d1f14")
        plaques_container.pack(fill="both", expand=True)

        self.hof_canvas = tkinter.Canvas(
            plaques_container, background="#0d1f14", highlightthickness=0, borderwidth=0
        )
        self.hof_scrollbar = tkinter.Scrollbar(
            plaques_container, orient="vertical", command=self.hof_canvas.yview
        )
        self.hof_scroll_frame = tkinter.Frame(self.hof_canvas, background="#0d1f14")

        self.hof_canvas_win = self.hof_canvas.create_window(
            (0, 0), window=self.hof_scroll_frame, anchor="nw"
        )
        self.hof_canvas.configure(yscrollcommand=self._on_hof_scroll_update)

        self.hof_scroll_frame.bind("<Configure>", self._on_hof_frame_configure)
        self.hof_canvas.bind("<Configure>", self._on_hof_canvas_configure)

        self.hof_canvas.pack(side="left", fill="both", expand=True)

        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.hof_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.hof_scroll_frame.bind("<MouseWheel>", self._on_mousewheel)

        for idx, spec in enumerate(self.ACHIEVEMENT_SPECS):
            row = idx // 2
            col = idx % 2
            self.hof_scroll_frame.grid_columnconfigure(col, weight=1)
            self.hof_scroll_frame.grid_rowconfigure(row, weight=1)

            p_canvas = tkinter.Canvas(
                self.hof_scroll_frame,
                width=420,
                height=84,
                background="#0d1f14",
                highlightthickness=0,
                borderwidth=0,
            )
            p_canvas.grid(row=row, column=col, padx=8, pady=4, sticky="nsew")

            panel = CanvasPixelPanel(
                p_canvas,
                x=0,
                y=0,
                width=420,
                height=84,
                bg="#0c2917",
                border="#06140b",
                inner_hi="#1f4d30",
                inner_sh="#071a0e",
                rivet_color="#d4af37",
                scale=2,
                recessed=True,
                anchor="nw",
                tag=f"plaque_{spec['id']}",
            )

            p_canvas.create_text(
                14, 12, text=spec["title"], font=get_role_font("header", size_override=-16), fill="#ffd700", anchor="nw"
            )
            p_canvas.create_text(
                406, 12, text=f"[{spec['reward']}]", font=get_role_font("badge", size_override=-14), fill="#80cbc4", anchor="ne"
            )
            p_canvas.create_text(
                14, 34, text=spec["desc"], font=get_role_font("body", size_override=-16), fill="#d8e2dc", width=390, anchor="nw"
            )
            status_text_id = p_canvas.create_text(
                14, 60, text="🔒 LOCKED", font=get_role_font("badge", size_override=-14), fill="#ff8a80", anchor="nw"
            )

            status_lbl_shim = _CanvasTextShim(p_canvas, status_text_id)

            self.plaque_widgets[spec["id"]] = {
                "frame": p_canvas,
                "panel": panel,
                "status_lbl": status_lbl_shim,
                "status_text_id": status_text_id,
                "spec": spec,
            }

    def _on_hof_scroll_update(self, first, last):
        self.hof_scrollbar.set(first, last)
        if float(first) <= 0.0 and float(last) >= 1.0:
            if self.hof_scrollbar.winfo_ismapped():
                self.hof_scrollbar.pack_forget()
        else:
            if not self.hof_scrollbar.winfo_ismapped():
                self.hof_scrollbar.pack(side="right", fill="y")

    def _on_hof_frame_configure(self, event):
        self.hof_canvas.configure(scrollregion=self.hof_canvas.bbox("all"))

    def _on_hof_canvas_configure(self, event):
        self.hof_canvas.itemconfig(self.hof_canvas_win, width=event.width)

    def _on_mousewheel(self, event):
        if self.current_tab == 1 and hasattr(self, "hof_canvas") and self.hof_canvas.winfo_exists():
            self.hof_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    _on_hof_mousewheel = _on_mousewheel

    def _refresh_hof_display(self):
        """Refreshes all-time statistics and achievement plaques in Tab 2."""
        save_data = getattr(getattr(self.app, "save_manager", None), "data", None)
        if not save_data:
            return

        hs = save_data.highscores
        self._records_canvas.itemconfigure(self.lbl_peak_record, text=f"Peak Bankroll: ${hs.peak_bankroll:,}")
        self._records_canvas.itemconfigure(self.lbl_streak_record, text=f"Longest Win Streak: {hs.longest_win_streak:,} hands")
        self._records_canvas.itemconfigure(self.lbl_clears_record, text=f"Hell's Table Clears: {hs.hell_table_clears:,}")

        pct = (hs.total_hands_won / hs.total_hands_played * 100.0) if hs.total_hands_played > 0 else 0.0
        self._records_canvas.itemconfigure(
            self.lbl_hands_record,
            text=f"• Hands Won / Played: {hs.total_hands_won:,} / {hs.total_hands_played:,} ({pct:.1f}% Win Rate)",
        )
        self._records_canvas.itemconfigure(self.lbl_bjs_record, text=f"• Total Blackjacks: {hs.total_blackjacks:,}")

        achs = save_data.achievements
        for ach_id, p_info in self.plaque_widgets.items():
            unlocked = getattr(achs, ach_id, False)
            spec = p_info["spec"]
            panel = p_info.get("panel")
            lbl = p_info["status_lbl"]

            if unlocked:
                if panel:
                    panel.update_palette(border="#ffd700", inner_hi="#ffe082")
                lbl.configure(text="✓ UNLOCKED", fg="#5ce6b5")
            else:
                if panel:
                    panel.update_palette(border="#06140b", inner_hi="#1f4d30")
                lbl.configure(text=f"🔒 LOCKED: {spec['criteria']}", fg="#ff8a80")

    def _stop_all_voices(self, except_panel: Optional[Any] = None):
        """Dismisses any active speech bubbles and stops streaming timers across all cards."""
        for card_data in self.cards.values():
            panel = card_data.get("panel")
            if panel and panel is not except_panel and hasattr(panel, "dismiss_speech_bubble"):
                panel.dismiss_speech_bubble()

    def _on_close(self):
        """Dismisses the wardrobe dialog gracefully."""
        self._stop_all_voices()
        try:
            if hasattr(self.app, "_wardrobe_dialog"):
                self.app._wardrobe_dialog = None
            self.destroy()
        except Exception:
            pass


class _TextLabelShim:
    """Lightweight compatibility shim for Canvas text items used by automated test assertions."""

    def __init__(self, canvas: tkinter.Canvas, text_id: int):
        self.canvas = canvas
        self.text_id = text_id
        self._text = ""

    def cget(self, key: str) -> str:
        if key == "text":
            return self._text
        return ""

    def config(self, **kwargs):
        self.configure(**kwargs)

    def configure(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs["text"]
            try:
                self.canvas.itemconfigure(self.text_id, text=self._text)
            except Exception:
                pass


class _CanvasTextShim:
    """Lightweight shim for plaque status labels to satisfy .configure(text=..., fg=...) in tests."""

    def __init__(self, canvas: tkinter.Canvas, text_id: int):
        self.canvas = canvas
        self.text_id = text_id
        self._text = ""
        self._fg = ""

    def configure(self, **kwargs):
        if "text" in kwargs:
            self._text = kwargs["text"]
            try:
                self.canvas.itemconfigure(self.text_id, text=self._text)
            except Exception:
                pass
        if "fg" in kwargs:
            self._fg = kwargs["fg"]
            try:
                self.canvas.itemconfigure(self.text_id, fill=self._fg)
            except Exception:
                pass

    config = configure
