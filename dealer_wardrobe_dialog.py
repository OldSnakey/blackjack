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

import os
import tkinter
from typing import Any, Callable, Dict, List, Optional
from PIL import Image, ImageTk

import config
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
from ui_dialogs import InWindowScreenHost


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
    "professor": (
        "Blackjack isn't a game of luck, scholar—it's a game of conditional probability and memory!"
    ),
}

COSTUME_VOICE_QUOTES: Dict[str, str] = {
    **CHARACTER_VOICE_QUOTES,
    "julian_monte_carlo": (
        "Evening at the Monte Carlo salon—ivory silk, golden lapels, and a fresh six-deck shoe."
    ),
    "julian_high_roller": (
        "Welcome to the burgundy VIP room. High limits, sharp tailoring, and pure casino tradition."
    ),
    "julian_emerald": (
        "Dressed in Emerald Club velvet—may the green felt favor your boldest doubles tonight."
    ),
    "julian_bond": (
        "The name is Julian. Shaken, not stirred—and I always stand on a hard seventeen, double-oh."
    ),
    "julian_godfather": (
        "Welcome to the 1920s speakeasy, pal. Keep your fedora low and your chips stacked high."
    ),
    "julian_maverick": (
        "Out on the frontier saloon circuit, a cool hand beats a fast draw every single time."
    ),
    "julian_miami": (
        "Neon palms, white linen, and sunset shades—welcome to the 1980s high-roller strip!"
    ),
    "tiffany_velvet": (
        "Velvet cards and sharp minds. Let's see how well you handle the house edge tonight, darling!"
    ),
    "tiffany_sequin": (
        "Deep crimson sequins and a single strap, darling—keep your eyes on the cards if you can!"
    ),
    "tiffany_rose": (
        "Crimson velvet corset and satin opera gloves—welcome to the private VIP lounge, sweetheart!"
    ),
    "tiffany_champagne": (
        "Twenty-four karat gold halter and a ruby drop! Raise your glass and place your chips, darling."
    ),
    "tiffany_amethyst": (
        "Midnight sapphire lace and diamonds for the after-hours tables. Deal me in, honey!"
    ),
    "tiffany_bunny": (
        "Satin bunny ears and French cuffs, sugar! VIP service is hopping at my table tonight!"
    ),
    "tiffany_showgirl": (
        "Feathers, rubies, and Vegas Jubilee lights! Every hand's a headliner on the Strip, darling!"
    ),
    "tiffany_cheongsam": (
        "Imperial crimson silk and golden dragons from the Macau high-limit salon. Feeling lucky?"
    ),
    "tiffany_noir": (
        "Arctic-fox fur, emerald satin, and a velvet veil... In a noir casino, every card has a secret."
    ),
    "professor_ivy": (
        "In Cambridge tweed, we treat every shoe like a seminar on expected value and risk management."
    ),
    "professor_oxford": (
        "Oxford navy and brass—remember, scholar, basic strategy is your foundation, the count is your edge."
    ),
    "professor_vegas": (
        "When the MIT team hit Vegas undercover, blending in at the pit was half the science!"
    ),
    "professor_vegas_disguise": (
        "Pit bosses never suspect a tourist in a Hawaiian shirt and Panama hat counting a +4 shoe!"
    ),
    "professor_sherlock": (
        "Elementary, my dear player! When you eliminate the dealt tens, whatever remains is the true count!"
    ),
    "professor_mad_scientist": (
        "Quantum goggles calibrated! By my stochastic equations, this shoe has reached critical mass!"
    ),
    "professor_dean": (
        "By the authority vested in the Academy of Advantage Play, I hereby confer a natural twenty-one!"
    ),
    "selene_chrome": (
        "Full liquid-chrome chassis online. Mirror-finish optics locked onto the shoe at 120 hertz."
    ),
    "selene_netrunner": (
        "Cyber-magenta neural uplinks synced. Slicing through house variance on the neon grid."
    ),
    "selene_arasaka": (
        "Executive syndicate armor engaged. High-limit protocol authorized—place your credits, runner."
    ),
    "selene_ghost": (
        "Ghost Protocol stealth weave active. Zero thermal signature, one hundred percent card precision."
    ),
    "selene_kunoichi": (
        "Oni stealth mask locked. In the Neo-Tokyo shadows, the unseen blade always draws twenty-one."
    ),
    "selene_valkyrie": (
        "Orbital Valkyrie exosuit online—arc reactor humming at full output. Ready to launch the deal."
    ),
    "selene_synthwave": (
        "Cat-ear headphones cranked to 1988 synthwave! Drop a coin in the slot and beat the high score!"
    ),
    "selene_bounty": (
        "Beskar T-visor locked on target. I can bring your chips in warm... or I can bring them in cold."
    ),
    "malphas_hellfire": (
        "Clad in molten Hellfire embers! Every bust feeds the furnace of the lower pit!"
    ),
    "malphas_brimstone": (
        "Brimstone gold and blood-crimson silk—let us see if your nerve survives the infernal shoe!"
    ),
    "malphas_abyssal": (
        "From the deepest violet void of the abyss, I deal the cards of fate, mortal!"
    ),
    "malphas_warlord": (
        "Crowned in black iron and bone pauldrons! Bow before the Warlord of the Seventh Pit!"
    ),
    "malphas_mephisto": (
        "A Victorian top hat and a Faustian contract... Care to sign on the dotted line for an Ace?"
    ),
    "malphas_biker": (
        "Born to raise Hell on the brimstone highway! Rev the engine and double down, road-warrior!"
    ),
    "malphas_pharaoh": (
        "By the golden scales of Anubis, your wager shall be weighed against the feather of truth!"
    ),
    "uriel_alabaster": (
        "Clothed in pearl and burnished gold—may pure serenity bless every hand dealt upon this felt."
    ),
    "uriel_sapphire": (
        "Under the deep sapphire firmament of the high heavens, steadfast courage commands the shoe."
    ),
    "uriel_obsidian": (
        "Even when garbed in twilight obsidian, the golden light of the sanctuary never falters."
    ),
    "uriel_archangel": (
        "Clad in silver Crusader battleplate and the Solar Cross—stand firm against the house edge!"
    ),
    "uriel_olympian": (
        "Crowned in golden laurel from Mount Olympus! May Apollo's sunlight shine upon your draw."
    ),
    "uriel_pontiff": (
        "Carved in eternal Carrara marble—I have contemplated every permutation of this shoe for two millennia."
    ),
    "uriel_fallen": (
        "Ah, ha, ha, ha, stayin' alive at twenty-one! Let the mirror ball spin and deal the groove."
    ),
    "mortimer_baron": (
        "Cackle! The Crimson Baron of the crypt deals tonight—stake your gold before the bell tolls!"
    ),
    "mortimer_lich": (
        "Glowing with emerald soulfire! Even my old ribs tingle when a blackjack hits the felt!"
    ),
    "mortimer_gilded": (
        "Draped in gilded burial brocade! Who says you cannot take your gold to the grave? Hehehe!"
    ),
    "mortimer_pirate": (
        "Yarrr! Dead men tell no tales, matey—but they sure know how to deal a pirate's twenty-one!"
    ),
    "mortimer_mariachi": (
        "¡Viva la fiesta de los muertos! Marigolds, charro silver, and a serenade for your bankroll!"
    ),
    "mortimer_jester": (
        "Jingle, jangle! In the Court of Fools, the wild harlequin laughs last when the dealer busts!"
    ),
    "mortimer_reaper": (
        "Two coins for the Ferryman... Step aboard the River Styx and let the hourglass deal your fate."
    ),
    "vladimir_nosferatu": (
        "Wrapped in shadow velvet, I have watched fortunes rise and vanish before the break of dawn."
    ),
    "vladimir_royal": (
        "Imperial Wallachian purple and gold—worthy of a midnight wager in the grandest courts of Europe."
    ),
    "vladimir_frost": (
        "Cold as a Carpathian winter night... keep your pulse steady as the next card turns."
    ),
    "vladimir_dracul": (
        "In the dragon-crest armor of old Wallachia, I impale the house edge before the moon sets."
    ),
    "vladimir_phantom": (
        "Behind this porcelain mask, the Phantom of the Casino conducts the music of the night!"
    ),
    "vladimir_alucard": (
        "Crimson hat, orange shades, and silver rounds—what a glorious night to hunt for a twenty-one."
    ),
    "vladimir_masquerade": (
        "Welcome to the Venetian Carnival! Behind a gilded masquerade mask, every bluff is art."
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
        card_width: int = 436,
        card_height: int = 222,
        art_scale: int = 1,
        **kwargs,
    ):
        s = max(1, int(art_scale))
        compact_2x = bool(s >= 2 and getattr(dialog, "is_compact_2x", False))
        cw = max(436 * s, int(card_width))
        ch = max((182 * s) if compact_2x else (222 * s), int(card_height))
        super().__init__(
            master,
            width=cw,
            height=ch,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            **kwargs,
        )
        self.char_id = char_id
        self.profile = profile
        self.dialog = dialog
        self.scale = scale * s if scale == 2 and s > 1 else scale
        self.art_scale = s
        self.card_width = cw
        self.card_height = ch
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

        # Responsive geometry anchors inside (cw, ch)
        pad_xy = 10 * s if compact_2x else 16 * s
        px = pad_xy
        py = pad_xy
        btn_h = (25 * s) if compact_2x else (34 * s)
        btn_cy = ch - ((18 * s) if compact_2x else (26 * s))
        max_p = (126 * s) if compact_2x else (182 * s if s == 1 else 156 * s)
        p_size = max(116 * s, min(max_p, btn_cy - btn_h // 2 - py - 6 * s))
        p_cx = px + p_size // 2
        p_cy = py + p_size // 2
        rx = px + p_size + 18 * s
        r_end = cw - 18 * s
        right_w = max(240 * s, r_end - rx)
        self._layout_geom = (px, py, p_size, p_cx, p_cy, rx, r_end, right_w, btn_cy, btn_h)

        # 1. 9-slice background panel with corner brass rivets
        border_col = "#ecc260" if is_equipped else "#06140b"
        inner_hi_col = "#ffd700" if is_equipped else "#1f4d30"
        self.panel = CanvasPixelPanel(
            self,
            x=0,
            y=0,
            width=cw,
            height=ch,
            bg="#0c2917",
            border=border_col,
            inner_hi=inner_hi_col,
            inner_sh="#071a0e",
            rivet_color="#d4af37",
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="card_panel",
        )

        # 2. Left Column: Recessed Gold Portrait Frame
        self.portrait_frame = CanvasPixelPanel(
            self,
            x=px,
            y=py,
            width=p_size,
            height=p_size,
            bg="#060c08",
            border="#8a6d1b",
            inner_hi="#12271c",
            inner_sh="#040805",
            rivet_color=None,
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="portrait_frame",
        )

        cur_variant = self.costumes[self.costume_idx] if self.costumes else None
        init_costume_id = cur_variant.costume_id if cur_variant else char_id
        bust_scale = 2.0 if s >= 2 else 1.0
        bust_pil = dialog.app.dealer_actor.get_bust_image(char_id, scale_factor=bust_scale, costume_id=init_costume_id)
        if bust_pil:
            self.portrait_photo = ImageTk.PhotoImage(bust_pil, master=self)
            dialog._photo_cache[f"bust_{init_costume_id}_{s}"] = self.portrait_photo
            self.portrait_item = self.create_image(p_cx, p_cy, image=self.portrait_photo, anchor="center")
        else:
            self.portrait_photo = None
            self.portrait_item = self.create_text(
                p_cx,
                p_cy,
                text="[No Bust]",
                font=get_role_font("body", size_override=-16 * s),
                fill="#b0bec5",
                anchor="center",
            )

        # Voice Button: aligned on bottom button baseline under portrait
        self.voice_btn = CanvasPixelButton(
            self,
            x=p_cx,
            y=btn_cy,
            width=p_size,
            height=btn_h,
            text="🔊 Voice",
            theme="neutral",
            font=("Tiny5", -16 * s, "bold"),
            scale=2 * s,
            command=self._play_voice,
        )

        # 3. Right Column:
        top_title_y = (8 * s) if compact_2x else (14 * s)
        sub_y = (31 * s) if compact_2x else (50 * s if s == 1 else 48 * s)
        name_font = ("Tiny5", -24 * s if compact_2x else (-32 * s), "bold")
        self.name_text_id = self.create_text(
            rx,
            top_title_y,
            text=profile.name.upper(),
            font=name_font,
            fill="#ffd700",
            anchor="nw",
        )

        self.subtitle_text_id = self.create_text(
            rx,
            sub_y,
            text=profile.title,
            font=("Tiny5", -16 * s, "bold"),
            fill=profile.nameplate_fg,
            anchor="nw",
        )

        status_text, status_col = self._get_status_info()
        self.status_badge_id = self.create_text(
            r_end,
            sub_y,
            text=status_text,
            font=("Tiny5", -16 * s, "bold"),
            fill=status_col,
            anchor="ne",
        )

        # In-Card Costume Carousel Row
        has_multi = len(self.costumes) > 1
        car_y = (50 * s) if compact_2x else (74 * s)
        car_h = (21 * s) if compact_2x else (28 * s)
        car_cy = car_y + car_h // 2
        arrow_w = (26 * s) if compact_2x else (30 * s)
        strip_x = rx + arrow_w + 6 * s
        strip_w = max(140 * s, right_w - 2 * (arrow_w + 6 * s))

        self.prev_costume_btn = CanvasPixelButton(
            self,
            x=rx + arrow_w // 2,
            y=car_cy,
            width=arrow_w,
            height=car_h,
            text="◄",
            theme="neutral",
            font=("Tiny5", -16 * s, "bold"),
            scale=2 * s,
            enabled=has_multi,
            command=self._prev_costume,
        )

        self.carousel_panel = CanvasPixelPanel(
            self,
            x=strip_x,
            y=car_y,
            width=strip_w,
            height=car_h,
            bg="#08140c",
            border="#040a06",
            inner_hi="#0e2416",
            inner_sh="#020503",
            rivet_color=None,
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="carousel_panel",
        )
        c_label = self._get_carousel_label()
        self.carousel_text_id = self.create_text(
            strip_x + strip_w // 2,
            car_cy,
            text=c_label,
            font=("Tiny5", -16 * s, "bold"),
            fill="#f0f4f1",
            anchor="center",
        )

        self.next_costume_btn = CanvasPixelButton(
            self,
            x=r_end - arrow_w // 2,
            y=car_cy,
            width=arrow_w,
            height=car_h,
            text="►",
            theme="neutral",
            font=("Tiny5", -16 * s, "bold"),
            scale=2 * s,
            enabled=has_multi,
            command=self._next_costume,
        )

        # Lore Blurb (when unlocked) or Unlock Requirement (when locked) + Live Costume Quote
        lore_top_y = car_y + car_h + (4 * s if compact_2x else 10 * s)
        lore_wrap = max(240 * s, right_w - 4 * s)
        bio_font = ("Tiny5", -16 * s, "normal")
        quote_font = ("Tiny5", -24 if compact_2x else (-16 * s), "italic")
        if self.unlocked:
            self.req_header_id = None
            self.lore_text_id = self.create_text(
                rx,
                lore_top_y,
                text=profile.lore,
                font=bio_font,
                fill="#d8e2dc",
                width=lore_wrap,
                anchor="nw",
            )
        else:
            self.req_header_id = self.create_text(
                rx,
                lore_top_y,
                text="🔒 UNLOCK REQUIREMENT:",
                font=("Tiny5", -24 if compact_2x else (-16 * s), "bold"),
                fill="#ffd54f",
                anchor="nw",
            )
            crit = self.dialog.UNLOCK_CRITERIA.get(self.char_id, "Complete casino objectives to unlock.")
            self.lore_text_id = self.create_text(
                rx,
                lore_top_y + (16 * s if compact_2x else 22 * s),
                text=crit,
                font=bio_font,
                fill="#f0f4f1",
                width=lore_wrap,
                anchor="nw",
            )
        self.bio_text_id = self.lore_text_id

        # Position live costume flavor quote cleanly in the lower right space above Equip button
        max_quote_bot = btn_cy - btn_h // 2 - (4 * s if compact_2x else 6 * s)
        self._max_quote_bot = max_quote_bot
        min_quote_reserve = 30 if compact_2x else (18 * s)
        lore_bbox = self.bbox(self.lore_text_id)
        if compact_2x and lore_bbox and lore_bbox[3] > max_quote_bot - min_quote_reserve:
            cur_lore = self.itemcget(self.lore_text_id, "text")
            while lore_bbox and lore_bbox[3] > max_quote_bot - min_quote_reserve and len(cur_lore) > 36:
                cut = cur_lore.rfind(" ", 0, max(24, len(cur_lore) - 10))
                if cut <= 20:
                    break
                cur_lore = f"{cur_lore[:cut].rstrip(',;:- ')}..."
                self.itemconfigure(self.lore_text_id, text=cur_lore)
                lore_bbox = self.bbox(self.lore_text_id)
        quote_top_y = (lore_bbox[3] + (3 * s if compact_2x else 10 * s)) if lore_bbox else (lore_top_y + 42 * s)
        init_quote_txt = self._get_costume_quote_preview() if (max_quote_bot - quote_top_y >= (24 if compact_2x else 16 * s)) else ""
        self.costume_quote_id = self.create_text(
            rx,
            quote_top_y,
            text=init_quote_txt,
            font=quote_font,
            fill="#80cbc4",
            width=lore_wrap,
            anchor="nw",
        )
        self._clamp_quote_to_button_clearance()

        # Equip / Equipped Button sharing baseline with Voice Button
        btn_text, btn_theme, btn_enabled, dis_text_color = self._get_action_state()
        self.equip_btn = CanvasPixelButton(
            self,
            x=rx + right_w // 2,
            y=btn_cy,
            width=right_w,
            height=btn_h,
            text=btn_text,
            theme=btn_theme,
            font=("Tiny5", -16 * s, "bold"),
            scale=3 * s,
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

    def _get_costume_quote_preview(self) -> str:
        cur_variant = self.costumes[self.costume_idx] if self.costumes else None
        costume_id = cur_variant.costume_id if cur_variant else self.char_id
        raw = (
            COSTUME_VOICE_QUOTES.get(costume_id)
            or CHARACTER_VOICE_QUOTES.get(self.char_id)
            or f"Greetings from {self.profile.name}!"
        )
        return f'"{raw}"'

    def _clamp_quote_to_button_clearance(self) -> None:
        """Guarantees costume flavor quote never overlaps or touches the bottom Equip Costume button."""
        if not getattr(self, "costume_quote_id", None):
            return
        max_bot = getattr(self, "_max_quote_bot", 0)
        if max_bot <= 0:
            return
        q_txt = self.itemcget(self.costume_quote_id, "text")
        if not q_txt:
            return
        q_bbox = self.bbox(self.costume_quote_id)
        while q_bbox and q_bbox[3] > max_bot and len(q_txt) > 28:
            trimmed = q_txt.strip('"')
            cut = trimmed.rfind(" ", 0, max(20, len(trimmed) - 10))
            if cut <= 16:
                break
            q_txt = f'"{trimmed[:cut].rstrip(",;:- ")}..."'
            self.itemconfigure(self.costume_quote_id, text=q_txt)
            q_bbox = self.bbox(self.costume_quote_id)

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
        cur_variant = self.costumes[self.costume_idx] if self.costumes else None
        variant_id = cur_variant.costume_id if cur_variant else self.char_id
        s = getattr(self, "art_scale", 1)
        bust_scale = 2.0 if s >= 2 else 1.0
        bust_pil = self.dialog.app.dealer_actor.get_bust_image(
            self.char_id,
            scale_factor=bust_scale,
            costume_id=variant_id,
        )
        if bust_pil and self.portrait_item and self.type(self.portrait_item) == "image":
            cache_key = f"bust_{variant_id}_{s}"
            photo = self.dialog._photo_cache.get(cache_key)
            if photo is None:
                photo = ImageTk.PhotoImage(bust_pil, master=self)
                self.dialog._photo_cache[cache_key] = photo
            self.portrait_photo = photo
            self.itemconfigure(self.portrait_item, image=self.portrait_photo)
        btn_text, btn_theme, btn_enabled, dis_text_color = self._get_action_state()
        self.equip_btn.set_text(btn_text)
        self.equip_btn.configure(theme=btn_theme)
        self.equip_btn.set_disabled_text_color(dis_text_color)
        self.equip_btn.set_enabled(btn_enabled)
        if getattr(self, "costume_quote_id", None):
            self.itemconfigure(self.costume_quote_id, text=self._get_costume_quote_preview())
            self._clamp_quote_to_button_clearance()

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

        # 5. Render responsive speech balloon geometry
        s = getattr(self, "art_scale", 1)
        px, py, p_size, p_cx, p_cy, rx, r_end, right_w, btn_cy, btn_h = self._layout_geom
        x1 = rx - 14 * s
        y1 = 14 * s
        x2 = self.card_width - 14 * s
        y2 = btn_cy - btn_h // 2 - 8 * s

        # A. Directional pointer tail pointing directly to dealer's head
        tail_base_top = (x1 + 1, py + 28 * s)
        tail_base_bot = (x1 + 1, py + 46 * s)
        tail_tip = (px + p_size - 24 * s, py + 36 * s)
        self.create_polygon(
            tail_base_top[0], tail_base_top[1],
            tail_tip[0], tail_tip[1],
            tail_base_bot[0], tail_base_bot[1],
            fill=bg_col,
            outline=border_col,
            width=2 * s,
            tags="speech_bubble",
        )

        # B. Notched retro pixel balloon background
        self.create_rectangle(
            x1 + 2 * s, y1, x2 - 2 * s, y2,
            fill=bg_col,
            outline="",
            tags="speech_bubble",
        )
        self.create_rectangle(
            x1, y1 + 2 * s, x2, y2 - 2 * s,
            fill=bg_col,
            outline="",
            tags="speech_bubble",
        )

        # C. Balloon borders
        self.create_line(x1 + 2 * s, y1, x2 - 2 * s, y1, fill=border_col, width=2 * s, tags="speech_bubble")
        self.create_line(x1 + 2 * s, y2, x2 - 2 * s, y2, fill=border_col, width=2 * s, tags="speech_bubble")
        self.create_line(x1, y1 + 2 * s, x1, tail_base_top[1], fill=border_col, width=2 * s, tags="speech_bubble")
        self.create_line(x1, tail_base_bot[1], x1, y2 - 2 * s, fill=border_col, width=2 * s, tags="speech_bubble")
        self.create_line(x2, y1 + 2 * s, x2, y2 - 2 * s, fill=border_col, width=2 * s, tags="speech_bubble")

        # Seam bridge between tail and balloon interior
        self.create_line(
            x1 + 1, tail_base_top[1] + s, x1 + 1, tail_base_bot[1] - s,
            fill=bg_col,
            width=3 * s,
            tags="speech_bubble",
        )

        # D. Header & dismiss button
        self.create_text(
            x1 + 14 * s, y1 + 10 * s,
            text=f"✦ {self.profile.name.upper()}",
            font=get_role_font("header", size_override=-16 * s),
            fill=header_col,
            anchor="nw",
            tags="speech_bubble",
        )
        self.create_text(
            x2 - 10 * s, y1 + 10 * s,
            text="[✕]",
            font=get_role_font("body", size_override=-16 * s),
            fill="#78909c",
            anchor="ne",
            tags="speech_bubble",
        )

        # E. Text body item (starts empty and streams character-by-character)
        self._speech_text_id = self.create_text(
            x1 + 14 * s, y1 + 34 * s,
            text="",
            font=get_role_font("body", size_override=-16 * s),
            fill=text_col,
            width=max(240 * s, (x2 - x1) - 28 * s),
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
    Renders a responsive recessed mystery silhouette card for empty grid slots.
    Guarantees the 2x2 grid is always visually balanced on every page.
    """

    def __init__(
        self,
        master: Any,
        scale: int = 2,
        card_width: int = 436,
        card_height: int = 222,
        art_scale: int = 1,
        **kwargs,
    ):
        s = max(1, int(art_scale))
        cw = max(436 * s, int(card_width))
        ch = max(222 * s, int(card_height))
        super().__init__(
            master,
            width=cw,
            height=ch,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            **kwargs,
        )
        px = 16 * s
        py = 16 * s
        btn_h = 34 * s
        btn_cy = ch - 26 * s
        p_size = max(128 * s, min(156 * s, btn_cy - btn_h // 2 - py - 12 * s))
        p_cx = px + p_size // 2
        p_cy = py + p_size // 2
        rx = px + p_size + 20 * s
        r_end = cw - 20 * s
        right_w = max(240 * s, r_end - rx)

        self.panel = CanvasPixelPanel(
            self,
            x=0,
            y=0,
            width=cw,
            height=ch,
            bg="#08140c",
            border="#040a06",
            inner_hi="#0e2416",
            inner_sh="#020503",
            rivet_color="#555544",
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="mystery_card_panel",
        )

        self.portrait_frame = CanvasPixelPanel(
            self,
            x=px,
            y=py,
            width=p_size,
            height=p_size,
            bg="#040805",
            border="#1c3022",
            inner_hi="#0a150e",
            inner_sh="#020403",
            rivet_color=None,
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="mystery_portrait_frame",
        )

        self.bust_photo = get_pixel_icon("mystery_bust", scale=2 * s, master=self)
        if self.bust_photo:
            self.create_image(p_cx, p_cy, image=self.bust_photo, anchor="center")

        self.voice_btn = CanvasPixelButton(
            self,
            x=p_cx,
            y=btn_cy,
            width=p_size,
            height=btn_h,
            text="???",
            theme="neutral",
            font=get_role_font("button", size_override=-16 * s),
            scale=2 * s,
            enabled=False,
        )

        self.create_text(
            rx,
            16 * s,
            text="??? (COMING SOON)",
            font=get_role_font("header", size_override=-32 * s),
            fill="#8a6d1b",
            anchor="nw",
        )
        self.create_text(
            rx,
            48 * s,
            text="Unknown Casino Persona",
            font=get_role_font("header", size_override=-16 * s),
            fill="#3e5948",
            anchor="nw",
        )
        self.create_text(
            r_end,
            48 * s,
            text="[🔒] Mystery",
            font=get_role_font("badge", size_override=-16 * s),
            fill="#8a6d1b",
            anchor="ne",
        )

        car_y = 76 * s
        car_h = 26 * s
        strip_x = rx + 32 * s
        strip_w = max(140 * s, right_w - 64 * s)
        self.carousel_panel = CanvasPixelPanel(
            self,
            x=strip_x,
            y=car_y,
            width=strip_w,
            height=car_h,
            bg="#050d08",
            border="#020503",
            inner_hi="#09180e",
            inner_sh="#010302",
            rivet_color=None,
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="mystery_carousel_panel",
        )
        self.create_text(
            strip_x + strip_w // 2,
            car_y + car_h // 2,
            text="Classified",
            font=get_role_font("body", size_override=-16 * s),
            fill="#557766",
            anchor="center",
        )

        self.create_text(
            rx,
            car_y + car_h + 10 * s,
            text="A mysterious casino figure shrouded in secrecy. Check back in future table updates!",
            font=get_role_font("body", size_override=-16 * s),
            fill="#557766",
            width=max(240 * s, right_w - 6 * s),
            anchor="nw",
        )

        self.equip_btn = CanvasPixelButton(
            self,
            x=rx + right_w // 2,
            y=btn_cy,
            width=right_w,
            height=btn_h,
            text="[ Locked ]",
            theme="neutral",
            font=get_role_font("button", size_override=-16 * s),
            scale=3 * s,
            enabled=False,
        )


class WardrobeDialog(InWindowScreenHost):
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
        "professor": "Graduate the Card Counting Bootcamp (Pass Stage C5)",
    }

    PAGE_CONFIG = [
        {
            "title": "Casino Floor & High Rollers",
            "characters": ["julian", "tiffany", "professor", "selene"],
        },
        {
            "title": "Nocturne & Supernatural Legends",
            "characters": ["vladimir", "mortimer", "malphas", "uriel"],
        },
    ]

    DEBUG_PAGE_ENTRY = {
        "title": "Puppet Rig & Testing Workshop",
        "characters": ["dummy"],
    }

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
            "reward": "Selene Persona",
            "criteria": "5 Counting Quiz Streak",
        },
        {
            "id": "master_counter",
            "title": "🦇 Master Counter",
            "desc": "Achieve a flawless streak of 20 consecutive correct card counting drill quizzes.",
            "reward": "Vladimir Persona",
            "criteria": "20 Counting Quiz Streak",
        },
        {
            "id": "shoe_whisperer",
            "title": "👞 Shoe Whisperer",
            "desc": "Complete an entire card shoe to the cut card maintaining 100% quiz accuracy (min 3 quizzes).",
            "reward": "Counting Savant",
            "criteria": "100% Shoe Accuracy",
        },
        {
            "id": "count_capitalist",
            "title": "📈 Count Capitalist",
            "desc": "Exploit player advantage by winning a $1,000+ wager when True Count is +3.0 or higher.",
            "reward": "Advantage Playmaker",
            "criteria": "Win $1,000+ at TC ≥ +3.0",
        },
        {
            "id": "pair_perfectionist",
            "title": "💎 Pair Perfectionist",
            "desc": "Hit an authentic 25:1 payout with an identical suit and rank Perfect Pair.",
            "reward": "Diamond Payout",
            "criteria": "Win 25:1 Perfect Pair",
        },
        {
            "id": "poker_face",
            "title": "🃏 Poker Face",
            "desc": "Hit Three of a Kind, Straight Flush, or Suited Trips on a 21+3 side bet.",
            "reward": "Card Sharp Title",
            "criteria": "Win 21+3 Premium Hand",
        },
        {
            "id": "tour_champion",
            "title": "🏆 Grand Tour Champion",
            "desc": "Conquer all 8 Casino Venue Tour Salons and reach the $150,000 Sanctum summit.",
            "reward": "VIP Circuit Free-Roam",
            "criteria": "Complete 8/8 Tour Salons",
        },
        {
            "id": "ironman_legend",
            "title": "♦ Ironman Legend",
            "desc": "Conquer all 8 Casino Venue Tour Salons in a single Ironman Gauntlet run ($0 re-buys).",
            "reward": "8/8 Obsidian Medallions",
            "criteria": "Complete 8/8 Ironman Gauntlet",
        },
    ]

    HOF_PAGE_CONFIG = [
        {"title": "Casino Honors & Supernatural Lore", "slice": (0, 6)},
        {"title": "Advantage Counting & Side Bets", "slice": (6, 12)},
        {"title": "Grand Casino Venue Tour", "slice": (12, 14)},
    ]

    def __init__(
        self,
        parent: tkinter.Tk,
        app: Any,
        initial_tab: int = 0,
        on_close_callback: Optional[Callable[[], None]] = None,
        include_debug_dummy: Optional[bool] = None,
    ):
        super().__init__(
            parent,
            app=app,
            profile=getattr(app, "display_profile", None),
            background="#0d1f14",
            base_pad=22,
        )
        self.app = app
        self._external_close_cb = on_close_callback
        self._include_debug_dummy = include_debug_dummy
        self.title("🎩 Dealer Wardrobe & Dressing Room")

        current_char = getattr(getattr(self.app, "dealer_actor", None), "current_character", "julian")
        show_dummy = (
            bool(include_debug_dummy)
            if include_debug_dummy is not None
            else (os.environ.get("BLACKJACK_DEBUG_RIG") == "1" or current_char == "dummy")
        )
        self.page_config: List[Dict[str, Any]] = [dict(p) for p in self.PAGE_CONFIG]
        if show_dummy:
            self.page_config.append(dict(self.DEBUG_PAGE_ENTRY))

        self.current_tab = 0
        self.current_page = 0
        self.current_hof_page = 0
        self.cards: Dict[str, Dict[str, Any]] = {}
        self.plaque_widgets: Dict[str, Dict[str, Any]] = {}
        self._photo_cache: Dict[str, ImageTk.PhotoImage] = {}
        self._page_frames: Dict[int, tkinter.Frame] = {}
        self._hof_page_frames: Dict[int, tkinter.Frame] = {}
        self._built_content_wh: Optional[tuple[int, int, int]] = None

        self._build_ui()
        if initial_tab in (0, 1) and initial_tab != 0:
            self._switch_tab(initial_tab)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())
        self.bind("<Left>", lambda e: self._prev_page() if self.current_tab == 0 else self._prev_hof_page())
        self.bind("<Right>", lambda e: self._next_page() if self.current_tab == 0 else self._next_hof_page())
        self.bind("1", lambda e: self._switch_tab(0))
        self.bind("2", lambda e: self._switch_tab(1))
        self.bind("<Tab>", lambda e: self._switch_tab(1 if self.current_tab == 0 else 0))
        self.bind("<MouseWheel>", self._on_mousewheel, add="+")
        self.focus_set()

    def handle_modal_key(self, event: Any) -> Optional[str]:
        ks = getattr(event, "keysym", "")
        ch = str(getattr(event, "char", "") or "")
        if ks == "Escape":
            self._on_close()
        elif ks in ("Left", "Prior"):
            if self.current_tab == 0:
                self._prev_page()
            else:
                self._prev_hof_page()
        elif ks in ("Right", "Next"):
            if self.current_tab == 0:
                self._next_page()
            else:
                self._next_hof_page()
        elif ch == "1":
            self._switch_tab(0)
        elif ch == "2":
            self._switch_tab(1)
        elif ks == "Tab":
            self._switch_tab(1 if self.current_tab == 0 else 0)
        elif self.current_tab == 0 and ch.lower() in ("q", "e", "v", "[", "]"):
            chars = self.page_config[self.current_page]["characters"]
            if chars:
                focus_cid = getattr(self, "_focused_char_id", chars[0])
                if focus_cid not in chars:
                    focus_cid = chars[0]
                panel = self.cards.get(focus_cid, {}).get("panel")
                if panel is not None:
                    if ch.lower() in ("q", "["):
                        panel._prev_costume()
                    elif ch.lower() in ("e", "]"):
                        panel._next_costume()
                    elif ch.lower() == "v":
                        panel._play_voice()
        return "break"

    def _compute_wardrobe_metrics(self) -> tuple[int, int, int]:
        s = self.menu_scale
        compact = self.is_compact_2x
        vw, vh = self._resolve_host_wh()
        outer_px = (12 * s) if compact else self.compute_outer_padx(vw)
        v_pad = (6 * s) if compact else (10 * s)
        content_w = max(908 * s, vw - 2 * outer_px)
        content_h = max(500 * s, vh - 2 * v_pad)
        return (content_w, content_h, outer_px)

    def _on_viewport_resized(self, width: int, height: int) -> None:
        if not hasattr(self, "_built_content_wh") or self._built_content_wh is None:
            return
        cw, ch, _ = self._compute_wardrobe_metrics()
        prev_cw, prev_ch, prev_s = self._built_content_wh
        if abs(cw - prev_cw) > 12 or abs(ch - prev_ch) > 12 or self.menu_scale != prev_s:
            saved_tab = self.current_tab
            saved_page = self.current_page
            saved_hof_page = self.current_hof_page
            self._stop_all_voices()
            for child in list(self.winfo_children()):
                child.destroy()
            self.cards.clear()
            self.plaque_widgets.clear()
            self._page_frames.clear()
            self._hof_page_frames.clear()
            self._build_ui()
            self._switch_page(saved_page)
            self._switch_hof_page(saved_hof_page)
            self._switch_tab(saved_tab)

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

        if char_id == "professor":
            bp = getattr(save_data, "bootcamp", None) if save_data else None
            if bp and getattr(bp, "graduated", False):
                return True
            return False

        return False

    def _build_ui(self):
        s = self.menu_scale
        compact = self.is_compact_2x
        content_w, content_h, outer_px = self._compute_wardrobe_metrics()
        self._built_content_wh = (content_w, content_h, s)
        cx = content_w // 2

        v_pad = (6 * s) if compact else (10 * s)
        root_wrap = tkinter.Frame(self, background="#0d1f14", padx=outer_px, pady=v_pad)
        root_wrap.pack(fill="both", expand=True)
        self._root_wrap = root_wrap

        # 1. Full-Width Header Banner with Pixel Top Hat
        hdr_h = (28 * s) if compact else (38 * s)
        header_canvas = tkinter.Canvas(
            root_wrap,
            width=content_w,
            height=hdr_h,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
        )
        header_canvas.pack(fill="x", pady=(0, (2 * s) if compact else (4 * s)))

        top_hat_icon = get_pixel_icon("top_hat", scale=2 * s, master=self)
        banner_font = ("BoldPixels", -48 if compact else (-32 * s), "normal")
        title_id = header_canvas.create_text(
            cx + 14 * s,
            hdr_h // 2,
            text="CASINO WARDROBE & HALL OF FAME",
            font=banner_font,
            fill="#ffd700",
            anchor="center",
        )
        if top_hat_icon:
            self._photo_cache["top_hat_header"] = top_hat_icon
            t_bbox = header_canvas.bbox(title_id)
            hat_x = (t_bbox[0] - 20 * s) if t_bbox else (cx - 310 * s)
            header_canvas.create_image(hat_x, hdr_h // 2, image=top_hat_icon, anchor="center")

        # 2. Full-Width Tab Navigation Bar
        tab_nav_frame = tkinter.Frame(root_wrap, background="#0d1f14")
        tab_nav_frame.pack(fill="x", pady=((1 * s) if compact else (2 * s), (4 * s) if compact else (8 * s)))

        tab_bar_h = (30 * s) if compact else (38 * s)
        tab_btn_h = (27 * s) if compact else (34 * s)
        tab_canvas = tkinter.Canvas(
            tab_nav_frame,
            width=content_w,
            height=tab_bar_h,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
        )
        tab_canvas.pack(fill="x")

        tab_btn_w = min(440 * s, max(240 * s, (content_w - 24 * s) // 2))
        tab_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        self.btn_tab_wardrobe = CanvasPixelButton(
            tab_canvas,
            x=cx - tab_btn_w // 2 - 6 * s,
            y=tab_bar_h // 2,
            width=tab_btn_w,
            height=tab_btn_h,
            text="[1] 🎩 Wardrobe Closet",
            theme="green",
            font=tab_font,
            scale=2 * s,
            command=lambda: self._switch_tab(0),
        )

        self.btn_tab_hof = CanvasPixelButton(
            tab_canvas,
            x=cx + tab_btn_w // 2 + 6 * s,
            y=tab_bar_h // 2,
            width=tab_btn_w,
            height=tab_btn_h,
            text="[2] 🏆 Hall of Fame & Trophies",
            theme="neutral",
            font=tab_font,
            scale=2 * s,
            command=lambda: self._switch_tab(1),
        )

        # 3. Footer with Close Button (packed bottom before content_container so it stays anchored)
        footer_frame = tkinter.Frame(root_wrap, background="#0d1f14")
        footer_frame.pack(side="bottom", fill="x", pady=((4 * s) if compact else (6 * s), 0))

        foot_h = (30 * s) if compact else (40 * s)
        foot_btn_h = (27 * s) if compact else (34 * s)
        close_canvas = tkinter.Canvas(
            footer_frame,
            width=content_w,
            height=foot_h,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
        )
        close_canvas.pack(fill="x")

        self.close_btn = CanvasPixelButton(
            close_canvas,
            x=cx,
            y=foot_h // 2,
            width=320 * s,
            height=foot_btn_h,
            text="✔ Return to Table (Esc)",
            theme="green",
            font=tab_font,
            scale=3 * s,
            command=self._on_close,
        )

        # 4. Content Container
        self.content_container = tkinter.Frame(root_wrap, background="#0d1f14")
        self.content_container.pack(side="top", fill="both", expand=True)

        self.tab_wardrobe_frame = tkinter.Frame(self.content_container, background="#0d1f14")
        self.tab_hof_frame = tkinter.Frame(self.content_container, background="#0d1f14")

        self._build_wardrobe_tab(content_w, content_h)
        self._build_hof_tab(content_w, content_h)

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

    # ------------------------------------------------------------------------
    # Tab 1: Wardrobe Closet Implementation
    # ------------------------------------------------------------------------

    def _build_wardrobe_tab(self, content_w: int, content_h: int):
        s = self.menu_scale
        compact = self.is_compact_2x
        nav_h = (28 * s) if compact else (34 * s)
        nav_btn_h = (25 * s) if compact else (30 * s)
        nav_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        # Navigation Bar: Prev | Page X of Y : Title | Next
        nav_canvas = tkinter.Canvas(
            self.tab_wardrobe_frame,
            width=content_w,
            height=nav_h,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
        )
        nav_canvas.pack(fill="x", pady=(0, (3 * s) if compact else (6 * s)))

        nav_btn_w = 136 * s
        self.prev_btn = CanvasPixelButton(
            nav_canvas,
            x=nav_btn_w // 2 + 4 * s,
            y=nav_h // 2,
            width=nav_btn_w,
            height=nav_btn_h,
            text="◀ Previous",
            theme="neutral",
            font=nav_font,
            scale=2 * s,
            disabled_text_color="#a1887f",
            command=self._prev_page,
        )

        self.page_lbl_id = nav_canvas.create_text(
            content_w // 2,
            nav_h // 2,
            text="",
            font=nav_font,
            fill="#ffd700",
            anchor="center",
        )
        self.page_lbl = _TextLabelShim(nav_canvas, self.page_lbl_id)

        self.next_btn = CanvasPixelButton(
            nav_canvas,
            x=content_w - nav_btn_w // 2 - 4 * s,
            y=nav_h // 2,
            width=nav_btn_w,
            height=nav_btn_h,
            text="Next ▶",
            theme="neutral",
            font=nav_font,
            scale=2 * s,
            disabled_text_color="#a1887f",
            command=self._next_page,
        )

        cards_container = tkinter.Frame(self.tab_wardrobe_frame, background="#0d1f14")
        cards_container.pack(fill="both", expand=True, pady=(0, 2 * s))

        # Compute expanded 2x2 card dimensions utilizing full viewport width & height without clipping Row 2
        chrome_used = (132 * s) if compact else (178 * s)
        min_grid_h = (376 * s) if compact else (456 * s)
        avail_grid_h = max(min_grid_h, content_h - chrome_used)
        grid_pady = (3 * s) if compact else (4 * s)
        card_w = max(436 * s, (content_w - 20 * s) // 2)
        card_h = max((182 * s) if compact else (222 * s), (avail_grid_h - 4 * grid_pady - 4 * s) // 2)

        current_char = getattr(getattr(self.app, "dealer_actor", None), "current_character", "julian")

        for p_idx, p_data in enumerate(self.page_config):
            p_frame = tkinter.Frame(cards_container, background="#0d1f14")
            self._page_frames[p_idx] = p_frame

            characters_list = p_data["characters"]
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
                        card_width=card_w,
                        card_height=card_h,
                        art_scale=s,
                    )
                    card_panel.grid(row=row, column=col, padx=6 * s, pady=grid_pady)

                    self.cards[char_id] = {
                        "panel": card_panel,
                        "frame": card_panel,
                        "unlocked": unlocked,
                        "is_equipped": is_equipped,
                        "action_widget": card_panel.equip_btn,
                        "action_frame": card_panel,
                    }
                else:
                    mystery_panel = MysteryDealerCardPanel(
                        p_frame,
                        card_width=card_w,
                        card_height=card_h,
                        art_scale=s,
                    )
                    mystery_panel.grid(row=row, column=col, padx=6 * s, pady=4 * s)

        initial_page = 0
        for p_idx, p_data in enumerate(self.page_config):
            if current_char in p_data["characters"]:
                initial_page = p_idx
                break
        self._switch_page(initial_page)

    def _switch_page(self, page_idx: int):
        self._stop_all_voices()
        total = len(self.page_config)
        self.current_page = max(0, min(total - 1, page_idx))
        for p_idx, frame in self._page_frames.items():
            if p_idx == self.current_page:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        cfg = self.page_config[self.current_page]
        title_str = f"Page {self.current_page + 1} of {total} : {cfg['title']}"
        self.page_lbl.configure(text=title_str)
        self.prev_btn.set_enabled(self.current_page > 0)
        self.next_btn.set_enabled(self.current_page < total - 1)

    def _prev_page(self):
        if self.current_page > 0:
            self._switch_page(self.current_page - 1)

    def _next_page(self):
        if self.current_page < len(self.page_config) - 1:
            self._switch_page(self.current_page + 1)

    def _equip_costume(self, char_id: str, costume_id: Optional[str] = None):
        """Swaps active character and costume persona, updates saves, and refreshes UI."""
        if hasattr(self.app, "save_manager") and hasattr(self.app.save_manager, "data"):
            self.app.save_manager.data.equipped_costume = costume_id or char_id
            self.app.save_manager.save()

        if not getattr(self.app, "tour_active", False):
            self.app.dealer_actor.equip_costume(char_id, costume_id=costume_id)
            self.app._update_dealer_avatar()
        else:
            if hasattr(self.app, "result_var"):
                self.app.result_var.set("Costume saved for Free Play! Active Casino Tour hosts are fixed.")
        if hasattr(self.app, "sound_manager") and hasattr(self.app.sound_manager, "play_chip_add"):
            self.app.sound_manager.play_chip_add()

        self._refresh_card_actions()

    def _refresh_card_actions(self):
        if getattr(self.app, "tour_active", False) and hasattr(self.app, "save_manager"):
            saved_eq = getattr(self.app.save_manager.data, "equipped_costume", "classic")
            legacy_map = {"classic": "julian", "grim": "mortimer", "grim_bones": "mortimer", "seraph": "uriel"}
            active_char = legacy_map.get(saved_eq, saved_eq)
            if active_char not in CHARACTERS:
                for cid, prof in CHARACTERS.items():
                    if any(c.costume_id == saved_eq for c in prof.get_costumes()):
                        active_char = cid
                        break
        else:
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

    def _build_hof_tab(self, content_w: int, content_h: int):
        s = self.menu_scale
        compact = self.is_compact_2x
        rec_h = (94 * s) if compact else (106 * s)
        # 1. Full-Width Statistics Summary Card in CanvasPixelPanel
        records_canvas = tkinter.Canvas(
            self.tab_hof_frame,
            width=content_w,
            height=rec_h,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
        )
        records_canvas.pack(fill="x", pady=(0, (4 * s) if compact else (6 * s)))

        self.records_panel = CanvasPixelPanel(
            records_canvas,
            x=0,
            y=0,
            width=content_w,
            height=rec_h,
            bg="#0c2917",
            border="#06140b",
            inner_hi="#1f4d30",
            inner_sh="#071a0e",
            rivet_color="#d4af37",
            scale=2 * s,
            recessed=True,
            anchor="nw",
            tag="records_panel",
        )

        col_mid = int(content_w * 0.37)
        col_right = int(content_w * 0.72)
        col_b_2 = int(content_w * 0.28)
        col_b_3 = int(content_w * 0.50)

        rec_hdr_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        rec_row1_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        rec_body_font = ("Tiny5", -24 if compact else (-16 * s), "normal")
        y_hdr = (9 * s) if compact else (12 * s)
        y_r1 = (32 * s) if compact else (38 * s)
        y_dot1 = (y_r1 + 1) if s >= 2 else 41
        y_r2 = (52 * s) if compact else (60 * s)
        y_r3 = (71 * s) if compact else (82 * s)

        records_canvas.create_text(
            16 * s,
            y_hdr,
            text="📊 ALL-TIME CASINO RECORDS & FINANCIAL TELEMETRY",
            font=rec_hdr_font,
            fill="#ffd700",
            anchor="nw",
        )
        self.lbl_tour_record = records_canvas.create_text(
            content_w - 16 * s,
            y_hdr + (1 * s),
            text="🗺 Tour: ★ 0/8 • ♦ 0/8",
            font=rec_row1_font,
            fill="#ffd54f",
            anchor="ne",
        )

        self.dot_peak_record = records_canvas.create_text(
            24 * s, y_dot1, text="•", font=rec_row1_font, fill="#5ce6b5", anchor="nw"
        )
        self.lbl_peak_record = records_canvas.create_text(
            36 * s, y_r1, text="Peak Bankroll: $1,000", font=rec_row1_font, fill="#5ce6b5", anchor="nw"
        )
        self.dot_streak_record = records_canvas.create_text(
            col_mid, y_dot1, text="•", font=rec_row1_font, fill="#ffd54f", anchor="nw"
        )
        self.lbl_streak_record = records_canvas.create_text(
            col_mid + 12 * s, y_r1, text="Longest Win Streak: 0 hands", font=rec_row1_font, fill="#ffd54f", anchor="nw"
        )
        self.dot_clears_record = records_canvas.create_text(
            col_right, y_dot1, text="•", font=rec_row1_font, fill="#ff8a80", anchor="nw"
        )
        self.lbl_clears_record = records_canvas.create_text(
            col_right + 12 * s, y_r1, text="Hell's Table Clears: 0", font=rec_row1_font, fill="#ff8a80", anchor="nw"
        )

        self.lbl_hands_record = records_canvas.create_text(
            24 * s, y_r2, text="• Hands Won / Played: 0 / 0 (0.0% Win Rate)", font=rec_body_font, fill="#e0e0e0", anchor="nw"
        )
        self.lbl_bjs_record = records_canvas.create_text(
            col_right, y_r2, text="• Total Blackjacks: 0", font=rec_body_font, fill="#80d8ff", anchor="nw"
        )

        self.lbl_net_pl_record = records_canvas.create_text(
            24 * s, y_r3, text="• Net P/L: $0", font=rec_body_font, fill="#5ce6b5", anchor="nw"
        )
        self.lbl_bankruptcies_record = records_canvas.create_text(
            col_b_2, y_r3, text="• Bankruptcies: 0", font=rec_body_font, fill="#e0e0e0", anchor="nw"
        )
        self.lbl_bailouts_record = records_canvas.create_text(
            col_b_3, y_r3, text="• Bailouts: $0", font=rec_body_font, fill="#e0e0e0", anchor="nw"
        )
        self.lbl_wagered_record = records_canvas.create_text(
            col_right, y_r3, text="• Total Wagered: $0", font=rec_body_font, fill="#ffd54f", anchor="nw"
        )
        self._records_canvas = records_canvas

        # 2. Controller-Friendly Page Navigation Bar (◀ Previous | Page X of 3 | Next ▶)
        nav_h = (28 * s) if compact else (34 * s)
        nav_btn_h = (25 * s) if compact else (30 * s)
        nav_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        hof_nav_canvas = tkinter.Canvas(
            self.tab_hof_frame,
            width=content_w,
            height=nav_h,
            background="#0d1f14",
            highlightthickness=0,
            borderwidth=0,
        )
        hof_nav_canvas.pack(fill="x", pady=(0, (3 * s) if compact else (6 * s)))

        nav_btn_w = 136 * s
        self.hof_prev_btn = CanvasPixelButton(
            hof_nav_canvas,
            x=nav_btn_w // 2 + 4 * s,
            y=nav_h // 2,
            width=nav_btn_w,
            height=nav_btn_h,
            text="◀ Previous",
            theme="neutral",
            font=nav_font,
            scale=2 * s,
            disabled_text_color="#a1887f",
            command=self._prev_hof_page,
        )

        self.hof_page_lbl_id = hof_nav_canvas.create_text(
            content_w // 2,
            nav_h // 2,
            text="",
            font=nav_font,
            fill="#ffd700",
            anchor="center",
        )
        self.hof_page_lbl = _TextLabelShim(hof_nav_canvas, self.hof_page_lbl_id)

        self.hof_next_btn = CanvasPixelButton(
            hof_nav_canvas,
            x=content_w - nav_btn_w // 2 - 4 * s,
            y=nav_h // 2,
            width=nav_btn_w,
            height=nav_btn_h,
            text="Next ▶",
            theme="neutral",
            font=nav_font,
            scale=2 * s,
            disabled_text_color="#a1887f",
            command=self._next_hof_page,
        )

        # 3. Zero-Scroll 3x2 Paged Grid for 14 Achievement Plaques + Page 3 Venue Tour Medallion Shelf
        plaques_container = tkinter.Frame(self.tab_hof_frame, background="#0d1f14")
        plaques_container.pack(fill="both", expand=True)
        self._plaques_container = plaques_container

        chrome_hof = (232 * s) if compact else (292 * s)
        avail_hof_h = max(280 * s, content_h - chrome_hof)
        plaque_w = max(436 * s, (content_w - 24 * s) // 2)
        plaque_h = max(92 * s, min(168 * s, (avail_hof_h - 24 * s) // 3))

        plaque_hdr_font = ("Tiny5 Duo", -32 if compact else (-24 if s == 1 else -48), "bold")
        plaque_bdg_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        plaque_desc_font = ("Tiny5", -24 if compact else (-16 * s), "normal")

        trophy_scale = 2 if s >= 2 else 1
        ped_size = 76 if s == 1 else (144 if compact else 152)
        ped_x = 12 if s == 1 else (16 if compact else 24)
        text_x = ped_x + ped_size + (14 if s == 1 else (18 if compact else 22))
        text_w = max(200 * s, plaque_w - text_x - 14 * s)
        title_y = 8 if s == 1 else (14 if compact else 18)
        reward_y = title_y + (4 if s == 1 else (6 if compact else 10))
        desc_y = 34 if s == 1 else (title_y + (38 if compact else 56))
        status_y = plaque_h - (22 if s == 1 else (34 if compact else 44))

        for p_idx, p_cfg in enumerate(self.HOF_PAGE_CONFIG):
            p_frame = tkinter.Frame(plaques_container, background="#0d1f14")
            self._hof_page_frames[p_idx] = p_frame
            for col in range(2):
                p_frame.grid_columnconfigure(col, weight=1)
            row_count = 1 if p_idx == 2 else 3
            for row in range(row_count):
                p_frame.grid_rowconfigure(row, weight=0 if p_idx == 2 else 1)

            i_start, i_end = p_cfg["slice"]
            page_specs = self.ACHIEVEMENT_SPECS[i_start:i_end]
            for slot_idx, spec in enumerate(page_specs):
                row = slot_idx // 2
                col = slot_idx % 2
                ach_id = spec["id"]

                p_canvas = tkinter.Canvas(
                    p_frame,
                    width=plaque_w,
                    height=plaque_h,
                    background="#0d1f14",
                    highlightthickness=0,
                    borderwidth=0,
                )
                p_canvas.grid(row=row, column=col, padx=6 * s, pady=(3 * s) if compact else (4 * s))

                panel = CanvasPixelPanel(
                    p_canvas,
                    x=0,
                    y=0,
                    width=plaque_w,
                    height=plaque_h,
                    bg="#0c2917",
                    border="#06140b",
                    inner_hi="#1f4d30",
                    inner_sh="#071a0e",
                    rivet_color="#d4af37",
                    scale=2 * s,
                    recessed=True,
                    anchor="nw",
                    tag=f"plaque_{ach_id}",
                )

                ped_y = max(6 * s, (plaque_h - ped_size) // 2)
                trophy_pedestal = CanvasPixelPanel(
                    p_canvas,
                    x=ped_x,
                    y=ped_y,
                    width=ped_size,
                    height=ped_size,
                    bg="#071a0e",
                    border="#040d07",
                    inner_hi="#143320",
                    inner_sh="#030a05",
                    rivet_color=None,
                    scale=2 * s,
                    recessed=True,
                    anchor="nw",
                    tag=f"trophy_pedestal_{ach_id}",
                )

                init_photo = self._get_achievement_trophy_photo(ach_id, unlocked=False, scale=trophy_scale, master=p_canvas)
                trophy_image_id = p_canvas.create_image(
                    ped_x + ped_size // 2,
                    ped_y + ped_size // 2,
                    image=init_photo if init_photo is not None else "",
                    anchor="center",
                    tags=(f"trophy_img_{ach_id}",),
                )

                clean_title = self._clean_achievement_title(spec["title"])
                title_text_id = p_canvas.create_text(
                    text_x,
                    title_y,
                    text=clean_title,
                    font=plaque_hdr_font,
                    fill="#ffd700",
                    anchor="nw",
                )
                reward_text_id = p_canvas.create_text(
                    plaque_w - 14 * s,
                    reward_y,
                    text=f"[{spec['reward']}]",
                    font=plaque_bdg_font,
                    fill="#80cbc4",
                    anchor="ne",
                )
                title_bbox = p_canvas.bbox(title_text_id)
                reward_bbox = p_canvas.bbox(reward_text_id)
                if title_bbox and reward_bbox and (title_bbox[2] + 10 * s > reward_bbox[0]):
                    p_canvas.coords(reward_text_id, plaque_w - 14 * s, status_y)
                p_canvas.create_text(
                    text_x,
                    desc_y,
                    text=spec["desc"],
                    font=plaque_desc_font,
                    fill="#d8e2dc",
                    width=text_w,
                    anchor="nw",
                )
                status_text_id = p_canvas.create_text(
                    text_x,
                    status_y,
                    text="🔒 LOCKED",
                    font=plaque_bdg_font,
                    fill="#ff8a80",
                    anchor="nw",
                )

                status_lbl_shim = _CanvasTextShim(p_canvas, status_text_id)

                self.plaque_widgets[ach_id] = {
                    "frame": p_canvas,
                    "panel": panel,
                    "trophy_pedestal": trophy_pedestal,
                    "trophy_image_id": trophy_image_id,
                    "trophy_scale": trophy_scale,
                    "title_text_id": title_text_id,
                    "status_lbl": status_lbl_shim,
                    "status_text_id": status_text_id,
                    "spec": spec,
                }

        # 4. Page 3 Companion Showcase: 8-Salon Grand Casino Venue Tour Medallion Board
        self.hof_tour_shelf_frame = tkinter.Frame(
            plaques_container,
            background="#0c2917",
            highlightbackground="#8a6d1b",
            highlightthickness=max(1, 2 * s),
            padx=12 * s,
            pady=(6 * s) if compact else (10 * s),
        )
        self._tour_salon_labels: List[tkinter.Label] = []
        self._build_hof_tour_shelf(s, compact)

        self._switch_hof_page(0)

    def _build_hof_tour_shelf(self, s: int, compact: bool) -> None:
        from tour_domain import SALON_SPECS

        hdr_font = ("Tiny5", -24 if compact else (-16 * s if s == 1 else -32), "bold")
        cell_title_font = ("Tiny5", -24 if compact else (-16 * s), "bold")
        cell_sub_font = ("Tiny5", -24 if compact else (-16 * s), "normal")

        tkinter.Label(
            self.hof_tour_shelf_frame,
            text="🗺 GRAND CASINO VENUE TOUR — 8-SALON MEDALLION SHOWCASE",
            font=hdr_font,
            fg="#ffd700",
            background="#0c2917",
            anchor="w",
        ).pack(fill="x", pady=(0, (4 * s) if compact else (8 * s)))

        grid_box = tkinter.Frame(self.hof_tour_shelf_frame, background="#0c2917")
        grid_box.pack(fill="both", expand=True)
        for c in range(4):
            grid_box.columnconfigure(c, weight=1)
        for r in range(2):
            grid_box.rowconfigure(r, weight=1)

        self._tour_salon_labels.clear()
        for idx, spec in enumerate(SALON_SPECS):
            r = idx // 4
            c = idx % 4
            cell = tkinter.Frame(
                grid_box,
                background="#071a0e",
                highlightbackground="#1f4d30",
                highlightthickness=max(1, s),
                padx=8 * s,
                pady=(4 * s) if compact else (6 * s),
            )
            cell.grid(row=r, column=c, sticky="nsew", padx=4 * s, pady=3 * s)
            lbl_name = tkinter.Label(
                cell,
                text=f"S{idx + 1}. {spec.short_name}",
                font=cell_title_font,
                fg="#d8e2dc",
                background="#071a0e",
                anchor="w",
            )
            lbl_name.pack(fill="x")
            lbl_med = tkinter.Label(
                cell,
                text="☆ Locked  •  ♢ Locked",
                font=cell_sub_font,
                fg="#8fa89b",
                background="#071a0e",
                anchor="w",
            )
            lbl_med.pack(fill="x")
            self._tour_salon_labels.append((lbl_name, lbl_med, spec))

    def _switch_hof_page(self, page_idx: int) -> None:
        total = len(self.HOF_PAGE_CONFIG)
        self.current_hof_page = max(0, min(total - 1, int(page_idx)))
        if hasattr(self, "hof_tour_shelf_frame"):
            self.hof_tour_shelf_frame.pack_forget()
        for p_idx, frame in self._hof_page_frames.items():
            if p_idx == self.current_hof_page:
                if p_idx == 2:
                    frame.pack(fill="x", expand=False)
                else:
                    frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
        if self.current_hof_page == 2 and hasattr(self, "hof_tour_shelf_frame"):
            self.hof_tour_shelf_frame.pack(fill="both", expand=True, padx=6 * self.menu_scale, pady=(4 * self.menu_scale, 2 * self.menu_scale))
        cfg = self.HOF_PAGE_CONFIG[self.current_hof_page]
        self.hof_page_lbl.configure(
            text=f"Page {self.current_hof_page + 1} of {total} : {cfg['title']}"
        )
        self.hof_prev_btn.set_enabled(self.current_hof_page > 0)
        self.hof_next_btn.set_enabled(self.current_hof_page < total - 1)

    _show_hof_page = _switch_hof_page

    def _prev_hof_page(self) -> None:
        if self.current_hof_page > 0:
            self._switch_hof_page(self.current_hof_page - 1)

    def _next_hof_page(self) -> None:
        if self.current_hof_page < len(self.HOF_PAGE_CONFIG) - 1:
            self._switch_hof_page(self.current_hof_page + 1)

    def _on_mousewheel(self, event: Any) -> None:
        """Allows mousewheel up/down to flip pages cleanly across Tab 0 and Tab 1."""
        delta = int(getattr(event, "delta", 0) or 0)
        if delta > 0:
            if self.current_tab == 0:
                self._prev_page()
            else:
                self._prev_hof_page()
        elif delta < 0:
            if self.current_tab == 0:
                self._next_page()
            else:
                self._next_hof_page()

    _on_hof_mousewheel = _on_mousewheel

    def _refresh_hof_display(self):
        """Refreshes all-time statistics and achievement plaques in Tab 2."""
        save_data = getattr(getattr(self.app, "save_manager", None), "data", None)
        if not save_data:
            return

        hs = save_data.highscores
        vt = getattr(save_data, "venue_tour", None)
        if vt is not None and hasattr(self, "lbl_tour_record"):
            self._records_canvas.itemconfigure(
                self.lbl_tour_record,
                text=f"🗺 Tour: ★ {vt.forgiving_salons_cleared}/8 • ♦ {vt.ironman_salons_cleared}/8",
            )
            f_cleared = int(getattr(vt, "forgiving_salons_cleared", 0) or 0)
            i_cleared = int(getattr(vt, "ironman_salons_cleared", 0) or 0)
            for idx, (lbl_name, lbl_med, spec) in enumerate(getattr(self, "_tour_salon_labels", [])):
                discovered = idx <= max(f_cleared, i_cleared)
                lbl_name.configure(
                    text=f"S{idx + 1}. {spec.short_name}" if discovered else f"S{idx + 1}. Mystery Salon",
                    fg="#ffd700" if idx < f_cleared else ("#d8e2dc" if discovered else "#607d8b"),
                )
                std_tag = "★ Gold" if idx < f_cleared else "☆ Locked"
                iro_tag = "♦ Obsidian" if idx < i_cleared else "♢ Locked"
                lbl_med.configure(
                    text=f"{std_tag}  •  {iro_tag}",
                    fg="#5ce6b5" if idx < f_cleared else "#8fa89b",
                )
        self._records_canvas.itemconfigure(self.lbl_peak_record, text=f"Peak Bankroll: ${hs.peak_bankroll:,}")
        self._records_canvas.itemconfigure(self.lbl_streak_record, text=f"Longest Win Streak: {hs.longest_win_streak:,} hands")
        self._records_canvas.itemconfigure(self.lbl_clears_record, text=f"Hell's Table Clears: {hs.hell_table_clears:,}")

        pct = (hs.total_hands_won / hs.total_hands_played * 100.0) if hs.total_hands_played > 0 else 0.0
        self._records_canvas.itemconfigure(
            self.lbl_hands_record,
            text=f"• Hands Won / Played: {hs.total_hands_won:,} / {hs.total_hands_played:,} ({pct:.1f}% Win Rate)",
        )
        self._records_canvas.itemconfigure(self.lbl_bjs_record, text=f"• Total Blackjacks: {hs.total_blackjacks:,}")

        # Financial Telemetry
        net_pl = getattr(getattr(self.app, "save_manager", None), "get_net_profit_loss", lambda: 0)()
        pl_str = f"+${net_pl:,}" if net_pl >= 0 else f"-${abs(net_pl):,}"
        pl_color = "#5ce6b5" if net_pl >= 0 else "#ff8a80"
        self._records_canvas.itemconfigure(self.lbl_net_pl_record, text=f"• Net P/L: {pl_str}", fill=pl_color)
        self._records_canvas.itemconfigure(
            self.lbl_bankruptcies_record, text=f"• Bankruptcies: {getattr(hs, 'bankruptcies', 0):,}"
        )
        self._records_canvas.itemconfigure(
            self.lbl_bailouts_record, text=f"• Bailouts: ${getattr(hs, 'total_bailout_funds', 0):,}"
        )
        self._records_canvas.itemconfigure(
            self.lbl_wagered_record, text=f"• Total Wagered: ${getattr(hs, 'lifetime_wagered', 0):,}"
        )

        achs = save_data.achievements
        for ach_id, p_info in self.plaque_widgets.items():
            unlocked = bool(getattr(achs, ach_id, False))
            spec = p_info["spec"]
            panel = p_info.get("panel")
            pedestal = p_info.get("trophy_pedestal")
            p_canvas = p_info.get("frame")
            trophy_img_id = p_info.get("trophy_image_id")
            trophy_scale = int(p_info.get("trophy_scale", 1))
            lbl = p_info["status_lbl"]

            if p_canvas is not None and trophy_img_id is not None:
                photo = self._get_achievement_trophy_photo(
                    ach_id, unlocked=unlocked, scale=trophy_scale, master=p_canvas
                )
                if photo is not None:
                    p_canvas.itemconfigure(trophy_img_id, image=photo)

            if unlocked:
                if panel:
                    panel.update_palette(border="#ffd700", inner_hi="#ffe082")
                if pedestal:
                    pedestal.update_palette(border="#d4af37", inner_hi="#ffd54f")
                lbl.configure(text="✓ UNLOCKED", fg="#5ce6b5")
            else:
                if panel:
                    panel.update_palette(border="#06140b", inner_hi="#1f4d30")
                if pedestal:
                    pedestal.update_palette(border="#040d07", inner_hi="#143320")
                lbl.configure(text=f"🔒 LOCKED: {spec['criteria']}", fg="#ff8a80")

    @staticmethod
    def _clean_achievement_title(raw_title: str) -> str:
        """Strips the leading decorative emoji glyph from an achievement title for clean plaque display."""
        txt = str(raw_title or "").strip()
        if " " in txt:
            head, tail = txt.split(" ", 1)
            if not any(ch.isascii() and ch.isalnum() for ch in head):
                return tail.strip()
        return txt

    def _get_achievement_trophy_photo(
        self,
        ach_id: str,
        *,
        unlocked: bool,
        scale: int = 1,
        master: Optional[tkinter.Misc] = None,
    ) -> Optional[ImageTk.PhotoImage]:
        """Loads and caches the 1x (64x64) or 2x (128x128) crunchy pixel-art achievement trophy or locked '?' silhouette."""
        s_tag = "2x" if int(scale) >= 2 else "1x"
        state_tag = "u" if unlocked else "l"
        cache_key = f"trophy_{ach_id}_{state_tag}_{s_tag}"
        cached = self._photo_cache.get(cache_key)
        if cached is not None:
            return cached

        prefix = "" if unlocked else "locked_"
        suffix = "_2x" if int(scale) >= 2 else ""
        path = config.ACHIEVEMENTS_ASSETS_DIR / f"{prefix}{ach_id}{suffix}.png"
        if not path.exists():
            return None
        try:
            with Image.open(path) as im:
                rgba = im.convert("RGBA")
            photo = ImageTk.PhotoImage(rgba, master=master or self)
            self._photo_cache[cache_key] = photo
            return photo
        except Exception:
            return None

    refresh_hof_records = _refresh_hof_display

    def _stop_all_voices(self, except_panel: Optional[Any] = None):
        """Dismisses any active speech bubbles and stops streaming timers across all cards."""
        for card_data in self.cards.values():
            panel = card_data.get("panel")
            if panel and panel is not except_panel and hasattr(panel, "dismiss_speech_bubble"):
                panel.dismiss_speech_bubble()

    def _on_close(self):
        """Dismisses the wardrobe dialog gracefully."""
        self._stop_all_voices()
        cb = getattr(self, "_external_close_cb", None)
        try:
            if hasattr(self.app, "_wardrobe_dialog") and self.app._wardrobe_dialog is self:
                self.app._wardrobe_dialog = None
            self.destroy()
        except Exception:
            pass
        if cb:
            try:
                cb()
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
