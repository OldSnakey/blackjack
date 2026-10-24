"""
Blackjack GUI Game in Python using Tkinter.

Architecture & Separation of Concerns:
- config.py: Centralized constants, asset paths, and atmospheric ThemePalettes.
- rules.py: Pure, stateless Blackjack math, card models, and shoe building (Zero Tkinter).
- card_counter.py: Hi-Lo card counting domain engine, True Count math, and bet sizing guide.
- card_counting_hud.py: Felt-embedded count HUD, floating count badges, and Count Check quiz modal.
- audio_assets.py: SoundManager, High-DPI AssetScaler, and Kenney KeyboardIconLoader.
- dialogue_voice_engine.py: Procedural in-memory Animalese phoneme synthesis per dealer persona.
- ui_canvases.py: Custom 2.5D visualizers (ChipVisualizer, SoulMeterCanvas, TableAnnouncementHUD,
  HauntedAltarCanvas, DealerStageCanvas, TableFeltCanvas).
- ui_dialogs.py: Toplevel modal dialogs (StoryDialogueDialog, AngelicDraftDialog,
  SettingsDialog, ShortcutsDialog, WelcomeSplashDialog).
- dealer_wardrobe_dialog.py: Two-tab Dealer Wardrobe & Casino Hall of Fame modal.
- save_manager.py: Persistent player records, achievements, and unlockables.
- dealer_actor.py: Multi-layer 7-strata sprite character roster and compositor.
- haunted_manager.py: Roguelike celestial blessing engine and tug-of-war combat state.
"""

from __future__ import annotations

import math
import os
import random
import sys
import tempfile
import time
import tkinter
from pathlib import Path
from typing import Optional, Callable, Any

# Re-exported configuration, constants, and paths
from config import (
    BASE_DIR,
    ASSETS_DIR,
    AUDIO_DIR,
    ASSETS_EXTRA_DIR,
    OVERLAY_ICONS_DIR,
    HAUNTED_ASSETS_DIR,
    HAUNTED_AUDIO_DIR,
    DEFAULT_SOUND_VOLUME,
    BLACKJACK_TARGET,
    DEALER_STAND_THRESHOLD,
    DEFAULT_DECK_COUNT,
    CUT_CARD_PENETRATION,
    STARTING_BANKROLL,
    MINIMUM_BET,
    CHIP_DENOMINATIONS,
    INSURANCE_PAYOUT_RATIO,
    DEALER_DRAW_DELAY_MS,
    DEFAULT_WINDOW_WIDTH,
    DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    CARD_WIDTH,
    CARD_HEIGHT,
    PLAYER_CARD_OVERLAP_OFFSET,
    TABLE_BACKGROUND_COLOR,
    PANEL_BACKGROUND_COLOR,
    CHIP_STYLES,
    hex_to_rgb,
    get_base_dir,
    ThemePalette,
    get_phase_palette,
)

# Application Version (Single Source of Truth)
__version__ = "1.3.1"
APP_VERSION = __version__

# Re-exported domain rules & card models (pure Python, zero GUI dependencies)
from rules import (
    Card,
    Hand,
    RoundPhase,
    score_hand,
    is_soft_hand,
    dealer_should_hit,
    can_split,
    determine_outcome,
    calculate_payout,
    calculate_insurance_payout,
    breakdown_chips,
    build_shoe,
    BasicStrategyDecision,
    get_basic_strategy_decision,
)

# Re-exported audio and asset subsystems
from audio_assets import (
    SoundManager,
    AssetScaler,
    KeyboardIconLoader,
    load_images,
    PYGAME_AVAILABLE,
    pygame_mixer,
    PIL_AVAILABLE,
    Image,
    ImageTk,
    ImageDraw,
    ImageFont,
)

# Re-exported 2.5D Canvas components & HUD overlays
from ui_canvases import (
    ChipVisualizer,
    SoulMeterCanvas,
    TableAnnouncementHUD,
    HauntedAltarCanvas,
    DealerStageCanvas,
    TableFeltCanvas,
    HUD_OUTCOME_FONT_FAMILY,
    HUD_OUTCOME_FONT_SIZE,
    HUD_OUTCOME_FONT_WEIGHT,
    HUD_LORE_FONT_FAMILY,
    HUD_LORE_FONT_SIZE,
    HUD_LORE_FONT_SLANT,
    HUD_DEFAULT_WRAPLENGTH,
)

# Re-exported Toplevel modal dialogs
from ui_dialogs import (
    StoryDialogueDialog,
    AngelicDraftDialog,
    SettingsDialog,
    ShortcutsDialog,
    WelcomeSplashDialog,
)

# Re-exported subsystems
from save_manager import SaveManager, DEFAULT_SAVE_FILE
from dealer_actor import DealerActor, CharacterProfile, CHARACTERS, COSTUME_ALIASES
from dealer_wardrobe_dialog import WardrobeDialog
from haunted_manager import HauntedManager, Phase, Blessing, BLESSING_REGISTRY
from card_counter import HiLoCardCounter
from card_counting_hud import CardCountingHud, CardCountingQuizDialog, FloatingCountBadge
from event_bus import EventHub, GameEventType, GameEvent
from game_engine import BlackjackEngine, RoundResult
from state_machine import GameStateMachine


# ============================================================================
# GUI Application: Object-Oriented Presentation Layer
# ============================================================================


class BlackjackApp:
    """
    Encapsulates the Blackjack GUI, card state, and game lifecycle.
    Eliminates all global variables by storing state in instance attributes.
    Supports hand splitting with independent turn progression and outcome resolution.
    """

    def __init__(
        self,
        root: tkinter.Tk,
        sound_enabled: bool = True,
        save_path: Optional[Path] = None,
        chips_mode: Optional[bool] = None,
        play_mode: Optional[str] = None,
        skip_splash: bool = False,
    ):
        self.root = root
        prev_app = getattr(self.root, "_active_blackjack_app", None)
        if prev_app is not None and prev_app is not self:
            try:
                prev_app._cancel_all_active_timers()
            except Exception:
                pass
        self.root._active_blackjack_app = self
        self.root.title(f"Blackjack v{__version__}")
        self.root.geometry(f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.root.configure(background=TABLE_BACKGROUND_COLOR, padx=10, pady=10)

        # Window icon configuration (supports .png via PhotoImage and .ico fallback)
        self._icon_photo = None
        icon_png = ASSETS_EXTRA_DIR / "icon.png"
        icon_ico = ASSETS_EXTRA_DIR / "icon.ico"
        try:
            if icon_png.exists():
                self._icon_photo = tkinter.PhotoImage(file=str(icon_png))
                self.root.iconphoto(False, self._icon_photo)
            elif icon_ico.exists():
                self.root.iconbitmap(default=str(icon_ico))
        except Exception:
            pass  # Graceful fallback if window icon fails on headless or unsupported display

        # Allow responsive centering/scaling on window resize
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(3, weight=1)

        # Async timer management & graceful window destruction
        self._dealer_timer_id = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Destroy>", lambda e: self._on_close() if e.widget == self.root else None, add="+")

        # Audio Manager & Reactive Sound State
        self.sound_manager = SoundManager(audio_dir=AUDIO_DIR, enabled=sound_enabled)
        self.sound_status_var = tkinter.StringVar(
            value="🔊 Sound: ON" if self.sound_manager.enabled else "🔇 Sound: OFF"
        )
        self.voice_status_var = tkinter.StringVar(
            value="🗣 Voice: ON" if (hasattr(self.sound_manager, "voice_engine") and self.sound_manager.voice_engine and self.sound_manager.voice_engine.enabled) else "🤐 Voice: OFF"
        )

        # Shoe and Multi-Deck Configuration
        self.deck_count = DEFAULT_DECK_COUNT
        self.shoe_needs_reshuffle = False
        self.shoe_info_var = tkinter.StringVar(value="")

        # In-Memory Event Hub & Headless Game Engine Architecture
        self.event_bus = EventHub()
        self.engine = BlackjackEngine(
            bankroll=STARTING_BANKROLL,
            deck_count=self.deck_count,
            event_bus=self.event_bus,
        )
        self.fsm = self.engine.fsm

        # Game State Collections
        self.deck = []
        self.all_cards = []
        self.player_hands = [Hand()]
        self.active_hand_index = 0
        self.dealer_hand = Hand()
        self.engine.player_hands = self.player_hands
        self.engine.dealer_hand = self.dealer_hand

        # EventHub Subscribers
        def _on_card_dealt_sync(ev: GameEvent):
            if hasattr(self, "card_table_frame") and hasattr(self.card_table_frame, "update_shoe_penetration"):
                total = max(1, len(self.all_cards) * self.deck_count if self.all_cards else self.deck_count * 52)
                self.card_table_frame.update_shoe_penetration(len(self.deck), total)
        self.event_bus.subscribe(GameEventType.CARD_DEALT, _on_card_dealt_sync)

        # Hi-Lo Card Counting Trainer Subsystem
        self.card_counter = HiLoCardCounter(deck_count=self.deck_count)
        self._hole_card_observed = False

        # Dealer Hole Card Tracking (Face-down card mechanics)
        self.dealer_hole_card = None        # Card of the hidden card
        self.dealer_hole_widget = None      # Tkinter Label displaying the card back
        self.back_image = None              # PhotoImage for cards/back.png

        # Reactive GUI Variables
        self.dealer_wins_var = tkinter.IntVar(value=0)
        self.player_wins_var = tkinter.IntVar(value=0)
        self.ties_var = tkinter.IntVar(value=0)
        self.dealer_score_var = tkinter.StringVar(value="0")
        self.player_score_var = tkinter.StringVar(value="0")
        self.result_var = tkinter.StringVar(value="")

        # Haunted Halloween & Hell's Table Controller
        self.haunted = HauntedManager()
        # Player Save Data & Hall of Fame Controller
        if save_path is None and "unittest" in sys.modules:
            save_path = Path(tempfile.mkdtemp()) / "isolated_test_save.json"
        self.save_manager = SaveManager(save_path=save_path)
        self._settings_dialog = None
        if self.save_manager.data.achievements.exorcist:
            self.haunted.unlocked_cursed_stakes = True
            self.haunted.unlocked_exorcist = True

        # Table Play Mode & Wagering State (casual, betting, training)
        if play_mode is not None:
            self.play_mode = play_mode
        elif chips_mode is False:
            self.play_mode = "casual"
        elif chips_mode is True:
            saved_mode = getattr(self.save_manager.data, "play_mode", "betting")
            self.play_mode = "betting" if saved_mode == "casual" else saved_mode
        else:
            self.play_mode = getattr(self.save_manager.data, "play_mode", "betting")

        initial_chips_mode = (self.play_mode in ("betting", "training"))
        self.chips_mode_var = tkinter.BooleanVar(value=initial_chips_mode)
        self.play_mode_var = tkinter.StringVar(value=self.play_mode)
        self.bankroll_var = tkinter.IntVar(value=STARTING_BANKROLL)
        self.current_bet_var = tkinter.IntVar(value=0)
        self.hand_bets = [0]
        self.is_betting_phase = False
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.is_insurance_phase = False
        self.round_phase: RoundPhase = RoundPhase.BETTING if initial_chips_mode else RoundPhase.PLAYER_TURN
        self.chip_buttons = []
        self._last_was_double = False
        self._ambient_timer_id = None
        self._anim_frame_toggle = False
        self._active_story_dialog = None
        self._welcome_splash_dialog = None
        if (
            not getattr(self.save_manager.data, "onboarding_completed", False)
            and not skip_splash
            and "unittest" not in sys.modules
        ):
            self.root.after(350, self._open_welcome_splash_dialog)
        self.dealer_view_var = tkinter.BooleanVar(value=True)
        self.dealer_view_status_var = tkinter.StringVar(value="👤 Dealer: ON")
        self.dealer_speech_var = tkinter.StringVar(value="")
        self.cursed_stakes_var = tkinter.BooleanVar(value=False)
        self.haunted_assets: dict[str, tkinter.PhotoImage] = {}
        self.card_13: Card | None = None
        self._last_gravestones_risen = 0
        self._candles_manifested = False

        # Scale and Fullscreen Display Mode State
        self.scale_factor: float = 1.0
        self.card_width: int = CARD_WIDTH
        self.card_height: int = CARD_HEIGHT
        self.card_overlap_offset: int = PLAYER_CARD_OVERLAP_OFFSET
        self.is_fullscreen: bool = False
        self.scale_status_var = tkinter.StringVar(value="🔍 2x")
        self.fullscreen_status_var = tkinter.StringVar(value="⛶ Full")
        self.is_hole_card_hidden: bool = False
        self._prev_geometry = None
        self._asset_scaler = None

        # Living Dealer Animation Engine
        self._wardrobe_dialog = None
        self._dealer_idle_timer_id = None
        self._dealer_blink_timer_id = None
        self._dealer_blink_restore_timer_id = None
        self._dealer_blink_timers: list[Any] = []
        self._dealer_gesture_timer_id = None
        self._dealer_mouth_timer_id = None
        self._dealer_speech_anim_timer_id = None
        self._typewriter_timer_id = None
        self._haunted_round_timer_id = None
        self._dealer_anim_step = 0.0
        self._session_blackjacks = 0

        # Load card visual assets
        self._load_assets()

        # Build interface layout
        self._build_ui()

        # Render dealer on stage canvas
        self._update_dealer_avatar()

        # Bind emergency timer cleanup when root is destroyed directly
        try:
            self.root.bind("<Destroy>", self._on_root_destroyed, add="+")
        except Exception:
            pass

        # Start ambient animations loop for haunted elements
        self._start_ambient_animations()

        # Start living dealer idle breathing & autonomous blinking
        self._start_dealer_idle_animation()
        self._schedule_dealer_blink()

        # Start first game
        self.new_game()


    @property
    def player_hand(self):
        """Backwards-compatible access to the currently active player hand."""
        if not self.player_hands:
            return []
        return self.player_hands[self.active_hand_index]

    @player_hand.setter
    def player_hand(self, cards):
        """Backwards-compatible setter for the currently active player hand."""
        if not self.player_hands:
            self.player_hands = [list(cards)]
            self.active_hand_index = 0
        else:
            self.player_hands[self.active_hand_index] = list(cards)

    def _load_assets(self):
        """Loads 52 card face images, card back image, keyboard overlay icons, and haunted assets."""
        self._asset_scaler = AssetScaler(master=self.root)
        w = int(CARD_WIDTH * self.scale_factor)
        h = int(CARD_HEIGHT * self.scale_factor)
        load_images(self.all_cards, master=self.root, scale=self.scale_factor, asset_scaler=self._asset_scaler)
        back_path = ASSETS_DIR / "back.png"
        self.back_image = self._asset_scaler.get_scaled_image(back_path, w, h)
        self.icon_loader = KeyboardIconLoader(OVERLAY_ICONS_DIR, master=self.root)
        self.icon_question_small = self.icon_loader.get_icon("keyboard_question", scale_div=3)
        self._shortcuts_dialog = None

        # Load Haunted PNG Assets safely
        if HAUNTED_ASSETS_DIR.exists():
            for p in HAUNTED_ASSETS_DIR.glob("*.png"):
                stem = p.stem
                if stem.startswith("card_") or stem == "back_haunted" or ("haunted" in stem and any(f in stem for f in ("jack", "queen", "king"))):
                    img_w, img_h = w, h
                elif "avatar" in stem or "dealer" in stem:
                    img_w, img_h = int(96 * self.scale_factor), int(96 * self.scale_factor)
                elif "pumpkin" in stem:
                    img_w, img_h = int(48 * self.scale_factor), int(48 * self.scale_factor)
                elif "gravestone" in stem:
                    img_w, img_h = int(48 * self.scale_factor), int(56 * self.scale_factor)
                elif "candle" in stem:
                    img_w, img_h = int(40 * self.scale_factor), int(40 * self.scale_factor)
                elif "relic" in stem:
                    img_w, img_h = int(48 * self.scale_factor), int(48 * self.scale_factor)
                else:
                    img_w, img_h = int(48 * self.scale_factor), int(48 * self.scale_factor)

                scaled = self._asset_scaler.get_scaled_image(p, img_w, img_h)
                if scaled:
                    self.haunted_assets[stem] = scaled

        if "card_13" in self.haunted_assets:
            self.card_13 = Card(13, self.haunted_assets["card_13"], rank="thirteen", suit="skulls")

    def _build_ui(self):
        """Builds all Tkinter frames, scoreboards, card tables, and action buttons."""
        # Top Scoreboard: Win/Tie counters and status message
        scoreboard_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        scoreboard_frame.grid(row=0, column=0, columnspan=3, pady=(0, 6))

        lbl_dw_t = tkinter.Label(
            scoreboard_frame, text="Dealer Wins: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_dw_t.grid(row=0, column=0)
        lbl_dw_v = tkinter.Label(
            scoreboard_frame, textvariable=self.dealer_wins_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_dw_v.grid(row=0, column=1, padx=(0, 15))

        lbl_pw_t = tkinter.Label(
            scoreboard_frame, text="Player Wins: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_pw_t.grid(row=0, column=2)
        lbl_pw_v = tkinter.Label(
            scoreboard_frame, textvariable=self.player_wins_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_pw_v.grid(row=0, column=3, padx=(0, 15))

        lbl_t_t = tkinter.Label(
            scoreboard_frame, text="Ties: ", font=("Arial", 11, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_t_t.grid(row=0, column=4)
        lbl_t_v = tkinter.Label(
            scoreboard_frame, textvariable=self.ties_var, font=("Arial", 11),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        lbl_t_v.grid(row=0, column=5)

        self.stat_labels = [
            (lbl_dw_t, True),
            (lbl_dw_v, False),
            (lbl_pw_t, True),
            (lbl_pw_v, False),
            (lbl_t_t, True),
            (lbl_t_v, False),
        ]

        # Shoe Cards Remaining Display
        self.shoe_label = tkinter.Label(
            scoreboard_frame, textvariable=self.shoe_info_var, font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#80cbc4"
        )
        self.shoe_label.grid(row=0, column=6, padx=(12, 0))

        # Spacer column to push utility buttons to the right
        scoreboard_frame.columnconfigure(7, weight=1)

        # Sound Mute Toggle Button
        self.sound_button = tkinter.Button(
            scoreboard_frame, textvariable=self.sound_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_toggle_sound
        )
        self.sound_button.grid(row=0, column=8, padx=(15, 0))

        # Shortcuts / Help Button
        help_btn_kwargs = {
            "font": ("Arial", 9, "bold"),
            "background": PANEL_BACKGROUND_COLOR,
            "fg": "#ffeb3b",
            "activebackground": TABLE_BACKGROUND_COLOR,
            "activeforeground": "#ffeb3b",
            "relief": "ridge",
            "borderwidth": 1,
            "cursor": "hand2",
            "command": self._toggle_shortcuts_overlay,
        }
        if self.icon_question_small:
            self.help_button = tkinter.Button(
                scoreboard_frame, text=" Help", image=self.icon_question_small, compound="left",
                **help_btn_kwargs
            )
        else:
            self.help_button = tkinter.Button(
                scoreboard_frame, text="[?] Help",
                **help_btn_kwargs
            )
        self.help_button.grid(row=0, column=9, padx=(10, 0))

        # Dealer View Toggle Button (retained as instance for compatibility, unmapped since dealer is permanent)
        self.dealer_view_button = tkinter.Button(
            scoreboard_frame, textvariable=self.dealer_view_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._on_toggle_dealer_view
        )
        # Omitted from header grid since dealer is always enabled


        # Scale Mode Toggle Button (1x <-> 2x High-DPI in-memory scaling)
        self.scale_button = tkinter.Button(
            scoreboard_frame, textvariable=self.scale_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self.toggle_scale_mode
        )
        self.scale_button.grid(row=0, column=11, padx=(6, 0))

        # Fullscreen Toggle Button (F11)
        self.fullscreen_button = tkinter.Button(
            scoreboard_frame, textvariable=self.fullscreen_status_var, font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self.toggle_fullscreen
        )
        self.fullscreen_button.grid(row=0, column=12, padx=(6, 0))

        # Settings & Save Management Button
        self.settings_button = tkinter.Button(
            scoreboard_frame, text="⚙ Settings", font=("Arial", 9, "bold"),
            background=PANEL_BACKGROUND_COLOR, fg="white", activebackground=TABLE_BACKGROUND_COLOR,
            activeforeground="white", relief="ridge", borderwidth=1, cursor="hand2",
            command=self._open_settings_dialog
        )
        self.settings_button.grid(row=0, column=13, padx=(6, 0))

        # Bankroll and Bet summary (visible in Chips Mode)
        self.bankroll_label = tkinter.Label(
            scoreboard_frame, text="Bankroll: $1,000  |  Bet: $0",
            font=("Arial", 11, "bold"), background=TABLE_BACKGROUND_COLOR, fg="#81c784"
        )
        self.bankroll_label.grid(row=1, column=0, columnspan=14, pady=(2, 2))
        if not self.chips_mode_var.get():
            self.bankroll_label.grid_remove()  # Hidden in Casual Mode

        # Status / Result banner (Preserved for backwards compatibility, hidden from crowded top bar)
        self.result_label = tkinter.Label(
            scoreboard_frame, textvariable=self.result_var, font=("Arial", 13, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="#ffeb3b"
        )
        self.result_label.grid(row=2, column=0, columnspan=14, pady=(2, 4))
        self.result_label.grid_remove()  # Moved to TableAnnouncementHUD between Dealer & Player hands

        # Tier 1: Dealer Stage Area (Phase 4 Horizon Layout - Above the Horizon Rail)
        self.dealer_stage_frame = tkinter.Frame(
            self.root, background=PANEL_BACKGROUND_COLOR, padx=0, pady=0
        )
        self.dealer_stage_frame.grid(row=1, column=0, sticky="ew", columnspan=3)
        self.dealer_panel = self.dealer_stage_frame

        # Panoramic Dealer Stage Canvas (Full width atmospheric backdrops & stage hanger)
        self.dealer_stage_canvas = DealerStageCanvas(
            self.dealer_stage_frame,
            app=self,
            on_hanger_click=self._on_click_stage_hanger,
        )
        self.dealer_stage_canvas.pack(fill="both", expand=True)

        # Living Dealer Actor Layer Compositor
        init_costume = "julian"
        if hasattr(self, "save_manager") and hasattr(self.save_manager, "data"):
            init_costume = getattr(self.save_manager.data, "equipped_costume", "julian")
        self.dealer_actor = DealerActor(
            master=self.root,
            scale_factor=self.scale_factor,
            initial_character=init_costume,
        )

        # Dealer Actor Frame (Portrait + Theatrical Nameplate + Reactive Speech Dialogue)
        self.dealer_header_row = tkinter.Frame(self.dealer_stage_canvas, background=PANEL_BACKGROUND_COLOR)
        stage_init_h = int(DealerStageCanvas.DEFAULT_HEIGHT * self.scale_factor)
        self.dealer_actor_frame = self.dealer_header_row

        # Flickering Jack-o'-Lantern
        pumpkin_img = self.haunted_assets.get("pumpkin_glow_0")
        self.pumpkin_label = tkinter.Label(
            self.dealer_header_row, image=pumpkin_img, background=PANEL_BACKGROUND_COLOR
        )
        if pumpkin_img:
            self.pumpkin_label.image = pumpkin_img
        self.pumpkin_label.pack(side="left", padx=(0, 6), pady=2)
        self.pumpkin_label.pack_forget()

        # Dealer Avatar Portrait (Retained inside dealer_header_row for legacy tests)
        dealer_img = self.dealer_actor.get_photo_image() or self.haunted_assets.get("dealer_classic")
        self.dealer_avatar_label = tkinter.Label(
            self.dealer_header_row, image=dealer_img, background=PANEL_BACKGROUND_COLOR
        )
        if dealer_img:
            self.dealer_avatar_label.image = dealer_img
            self.dealer_stage_canvas.set_dealer_image(dealer_img)
        self.dealer_avatar_label.pack(side="left", padx=2, pady=2)
        self.dealer_avatar_label.pack_forget()

        # Dealer Dialogue & Actor Info Column (placed directly on stage canvas)
        self.dealer_dialogue_frame = tkinter.Frame(
            self.dealer_stage_canvas, background="#141014", relief="ridge", borderwidth=1,
            highlightthickness=1, highlightbackground="#c8a038", padx=6, pady=4
        )
        bubble_x = 500 - int(76 * self.scale_factor)
        bubble_y = stage_init_h - int(90 * self.scale_factor)
        self.dealer_stage_canvas.create_window(bubble_x, bubble_y, window=self.dealer_dialogue_frame, anchor="se", tags="dialogue_win")

        self.dealer_nameplate_label = tkinter.Label(
            self.dealer_dialogue_frame, text="The Classic Croupier", font=("Arial", 10, "bold"),
            foreground="#ffd700", background="#141014"
        )
        self.dealer_nameplate_label.pack(anchor="w")

        self.dealer_speech_label = tkinter.Label(
            self.dealer_dialogue_frame, textvariable=self.dealer_speech_var,
            font=("Arial", 9, "italic"), fg="#f0f0f0", background="#1c161c",
            relief="flat", borderwidth=0, padx=6, pady=2, wraplength=int(270 * self.scale_factor), justify="left"
        )
        self.dealer_speech_label.pack(anchor="w", pady=(2, 0))
        self.dealer_speech_label.pack_forget()  # Hidden until speech is set

        for widget in (self.dealer_dialogue_frame, self.dealer_nameplate_label, self.dealer_speech_label):
            widget.bind("<Button-1>", self._on_dialogue_click)

        # Tier 2: 3D Beveled Horizon Rail (Separates Dealer Stage from Playing Felt)
        self.horizon_rail = tkinter.Frame(
            self.root, height=4, background="#073512", relief="raised", borderwidth=1
        )
        self.horizon_rail.grid(row=2, column=0, columnspan=3, sticky="ew")

        # Tier 3: Main Card Table Area (Below the Horizon Rail)
        card_table_frame = TableFeltCanvas(
            self.root, relief="sunken", borderwidth=2, background=PANEL_BACKGROUND_COLOR, padx=8, pady=3
        )
        card_table_frame.grid(row=3, column=0, sticky="nsew", columnspan=3)
        card_table_frame.columnconfigure(1, weight=1)
        card_table_frame.columnconfigure(2, weight=0)
        card_table_frame.rowconfigure(0, weight=1, minsize=118)
        card_table_frame.rowconfigure(1, weight=1, minsize=140)
        card_table_frame.rowconfigure(2, weight=0, minsize=58)
        self.scoreboard_frame = scoreboard_frame
        self.card_table_frame = card_table_frame

        # Table Accessories Frame (Haunted Altar: 5 Candles & 5 Rising Gravestones on Table Felt)
        self.accessories_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR, borderwidth=0, highlightthickness=0)
        self.accessories_frame.grid(row=0, column=2, sticky="ne", padx=0, pady=0)
        self.accessories_frame.grid_remove()

        # Unified 2.5D Haunted Altar Canvas (5 Candles, Directional Shadows, Rising Gravestones)
        self.haunted_altar = HauntedAltarCanvas(
            self.accessories_frame, assets=self.haunted_assets, width=260, height=135,
            background=PANEL_BACKGROUND_COLOR
        )
        self.haunted_altar.pack(side="top", pady=2)
        self.haunted_altar.pack_forget()

        # Legacy frames preserved for backwards compatibility with tests / extensions
        self.candle_bar_frame = tkinter.Frame(self.accessories_frame, background=PANEL_BACKGROUND_COLOR)
        self.candle_labels = []
        self.gravestones_frame = tkinter.Frame(self.accessories_frame, background=PANEL_BACKGROUND_COLOR)
        self.gravestone_labels = []

        # Dealer Section - Casino Plaque Styling
        self.dealer_header_frame = tkinter.Frame(
            card_table_frame, background="#082210", relief="ridge", borderwidth=1,
            highlightthickness=1, highlightbackground="#8a733f", padx=6, pady=3
        )
        self.dealer_header_frame.grid(row=0, column=0, sticky="nw", padx=(4, 6), pady=(4, 0))

        self.dealer_title_label = tkinter.Label(
            self.dealer_header_frame, text="Dealer", font=("Arial", 11, "bold"),
            background="#082210", fg="#d4af37"
        )
        self.dealer_title_label.pack(anchor="w")

        self.dealer_score_label = tkinter.Label(
            self.dealer_header_frame, textvariable=self.dealer_score_var, font=("Arial", 12, "bold"),
            background="#082210", fg="#ffffff"
        )
        self.dealer_score_label.pack(anchor="w", pady=(1, 0))

        self.dealer_cards_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR)
        self.dealer_cards_frame.grid(row=0, column=1, padx=10, pady=1)

        # In-Table Floating Dialog Overlay (unmapped when empty, floats over center when active)
        self.announcement_hud = TableAnnouncementHUD(
            card_table_frame, background=PANEL_BACKGROUND_COLOR
        )
        self.result_var.trace_add("write", lambda *_: self.announcement_hud.set_message(self.result_var.get()))
        self.announcement_hud.set_message(self.result_var.get())

        # Player Section - Casino Plaque Styling
        self.player_header_frame = tkinter.Frame(
            card_table_frame, background="#082210", relief="ridge", borderwidth=1,
            highlightthickness=1, highlightbackground="#8a733f", padx=6, pady=3
        )
        self.player_header_frame.grid(row=1, column=0, sticky="nw", padx=(4, 6), pady=(4, 0))

        self.player_title_label = tkinter.Label(
            self.player_header_frame, text="Player", font=("Arial", 11, "bold"),
            background="#082210", fg="#d4af37"
        )
        self.player_title_label.pack(anchor="w")

        self.player_score_label = tkinter.Label(
            self.player_header_frame, textvariable=self.player_score_var, font=("Arial", 12, "bold"),
            background="#082210", fg="#ffffff"
        )
        self.player_score_label.pack(anchor="w", pady=(1, 0))

        self.player_cards_frame = tkinter.Frame(card_table_frame, background=PANEL_BACKGROUND_COLOR)
        self.player_cards_frame.grid(row=1, column=1, padx=10, pady=1)

        # 2.5D Casino Felt Betting Spot Visualizer (visible in Chips Mode)
        self.chip_visualizer = ChipVisualizer(
            card_table_frame,
            width=200,
            height=135,
            background=PANEL_BACKGROUND_COLOR,
            on_chip_click=self._add_chip_bet,
        )
        self.chip_visualizer.grid(row=1, column=2, padx=(10, 5), pady=2, sticky="e")
        if not self.chips_mode_var.get():
            self.chip_visualizer.grid_remove()  # Hidden in Casual Mode

        # 2.5D Animated Tug-of-War Soul Meter (visible in Hell's Table Mode)
        self.soul_meter_canvas = SoulMeterCanvas(
            card_table_frame, width=180, height=135, background="#140508"
        )
        self.soul_meter_canvas.grid(row=1, column=2, padx=(10, 5), pady=2, sticky="e")
        self.soul_meter_canvas.grid_remove()  # Hidden until Hell's Table Mode

        # Hi-Lo Card Counting Trainer HUD pill (table felt overlay)
        self.card_counting_hud = CardCountingHud(
            master=card_table_frame,
            counter=self.card_counter,
            on_quiz_request=self._open_card_counting_quiz,
            on_stage_bet_request=self._stage_recommended_bet,
            use_grid=True,
            grid_row=2,
        )
        if self.play_mode == "training":
            self.card_counting_hud.set_visible(True)

        # Betting Controls Bar (visible in Chips Mode)
        self.betting_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        self.betting_frame.grid(row=4, column=0, columnspan=3, pady=(2, 4))
        if not self.chips_mode_var.get():
            self.betting_frame.grid_remove()  # Hidden in Casual Mode

        self.bet_chips_label = tkinter.Label(
            self.betting_frame, text="Bet Chips:", font=("Arial", 10, "bold"),
            background=TABLE_BACKGROUND_COLOR, fg="white"
        )
        self.bet_chips_label.pack(side="left", padx=(0, 6))

        self.chip_buttons.clear()
        for amount, bg_color, fg_color in CHIP_DENOMINATIONS:
            btn = tkinter.Button(
                self.betting_frame, text=f"${amount}", font=("Arial", 9, "bold"),
                width=5, background=bg_color, foreground=fg_color,
                activebackground=bg_color, activeforeground=fg_color,
                relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
                command=lambda a=amount: self._add_chip_bet(a)
            )
            btn.pack(side="left", padx=3)
            self.chip_buttons.append(btn)

        self.all_in_button = tkinter.Button(
            self.betting_frame, text="All In", font=("Arial", 9, "bold"),
            width=7, background="#e65100", foreground="#ffffff",
            activebackground="#f57c00", activeforeground="#ffffff",
            relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
            command=self._all_in
        )
        self.all_in_button.pack(side="left", padx=4)

        self.clear_bet_button = tkinter.Button(
            self.betting_frame, text="Clear Bet", font=("Arial", 9, "bold"),
            width=8, takefocus=False, command=self._clear_bet
        )
        self.clear_bet_button.pack(side="left", padx=5)

        self.deal_bet_button = tkinter.Button(
            self.betting_frame, text="Deal Hand", font=("Arial", 9, "bold"),
            width=10, background="#ffd700", foreground="#000000",
            activebackground="#ffea00", activeforeground="#000000",
            relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
            command=self._deal_hand_with_bet
        )
        self.deal_bet_button.pack(side="left", padx=5)

        self.rebuy_button = tkinter.Button(
            self.betting_frame, text="Rebuy ($1,000)", font=("Arial", 9, "bold"),
            width=13, background="#ff9800", foreground="#000000",
            activebackground="#ffa726", relief="raised", borderwidth=2,
            cursor="hand2", takefocus=False, command=self._rebuy
        )
        self.rebuy_button.pack(side="left", padx=5)

        # Insurance Prompt Bar (visible when dealer shows an Ace in Chips Mode)
        self.insurance_frame = tkinter.Frame(
            self.root, background=PANEL_BACKGROUND_COLOR, padx=10, pady=5,
            relief="ridge", borderwidth=2
        )
        self.insurance_frame.grid(row=5, column=0, columnspan=3, pady=(2, 6))
        self.insurance_frame.grid_remove()  # Hidden by default

        self.insurance_label = tkinter.Label(
            self.insurance_frame, text="Dealer shows an Ace! Insurance pays 2:1 against Dealer Blackjack.",
            font=("Arial", 10, "bold"), background=PANEL_BACKGROUND_COLOR, fg="#ffeb3b"
        )
        self.insurance_label.pack(side="left", padx=(0, 10))

        self.take_insurance_button = tkinter.Button(
            self.insurance_frame, text="Take Insurance ($25)", font=("Arial", 9, "bold"),
            background="#ff9800", foreground="#000000", activebackground="#ffa726",
            relief="raised", borderwidth=2, cursor="hand2", takefocus=False,
            command=self._on_take_insurance
        )
        self.take_insurance_button.pack(side="left", padx=5)

        self.decline_insurance_button = tkinter.Button(
            self.insurance_frame, text="Decline", font=("Arial", 9, "bold"),
            width=8, takefocus=False, command=self._on_decline_insurance
        )
        self.decline_insurance_button.pack(side="left", padx=5)

        # Bottom Button Bar
        button_frame = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        button_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(4, 10))
        self.button_frame = button_frame

        # Ornate Video Poker Gem Action Buttons (Polished glass / gem styling with crisp black text)
        self.hit_button = tkinter.Button(
            button_frame, text="Hit", width=8, font=("Arial", 10, "bold"),
            background="#00e676", foreground="#000000",
            activebackground="#69f0ae", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_hit
        )
        self.hit_button.grid(row=0, column=0, padx=6)

        self.stand_button = tkinter.Button(
            button_frame, text="Stand", width=8, font=("Arial", 10, "bold"),
            background="#ff5252", foreground="#000000",
            activebackground="#ff8a80", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_stand
        )
        self.stand_button.grid(row=0, column=1, padx=6)

        self.double_button = tkinter.Button(
            button_frame, text="Double", width=8, font=("Arial", 10, "bold"),
            background="#ffd740", foreground="#000000",
            activebackground="#ffe57f", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_double_down, state="disabled"
        )
        self.double_button.grid(row=0, column=2, padx=6)

        self.split_button = tkinter.Button(
            button_frame, text="Split", width=8, font=("Arial", 10, "bold"),
            background="#40c4ff", foreground="#000000",
            activebackground="#80d8ff", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_split, state="disabled"
        )
        self.split_button.grid(row=0, column=3, padx=6)

        self.surrender_button = tkinter.Button(
            button_frame, text="Surrender", width=9, font=("Arial", 10, "bold"),
            background="#cfd8dc", foreground="#000000",
            activebackground="#eceff1", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=3, cursor="hand2", takefocus=False,
            command=self.on_surrender, state="disabled"
        )
        self.surrender_button.grid(row=0, column=4, padx=6)

        self.new_game_button = tkinter.Button(
            button_frame, text="New Game", width=9, font=("Arial", 10, "bold"),
            background="#ffd700", foreground="#000000",
            activebackground="#ffea00", activeforeground="#000000",
            disabledforeground="#42554a",
            relief="raised", borderwidth=4, cursor="hand2", takefocus=False,
            command=self.new_game
        )
        self.new_game_button.grid(row=0, column=5, padx=6)

        self.miracle_button = tkinter.Button(
            button_frame, text="✨ Miracle", width=10, font=("Arial", 10, "bold"),
            background="#18ffff", foreground="#000000",
            activebackground="#84ffff", activeforeground="#000000",
            relief="raised", borderwidth=3, cursor="hand2",
            takefocus=False, command=self._on_miracle_draw, state="disabled"
        )
        self.miracle_button.grid(row=0, column=6, padx=6)
        self.miracle_button.grid_remove()

        # Spacer column to push right-hand action controls to the far right
        button_frame.columnconfigure(7, weight=1)

        # Cursed Stakes Mode Button (Unlocks upon surviving Hell's Table, placed left of Chips Mode)
        self.cursed_stakes_button = tkinter.Button(
            button_frame, text="🔥 Cursed Stakes", font=("Arial", 10, "bold"),
            background="#b71c1c", fg="#ffd700", activebackground="#d32f2f",
            activeforeground="#ffffff", relief="ridge", borderwidth=1, cursor="hand2",
            takefocus=False, command=self._on_toggle_cursed_stakes
        )
        self.cursed_stakes_button.grid(row=0, column=8, padx=(6, 8), sticky="e")
        if not self.haunted.unlocked_cursed_stakes:
            self.cursed_stakes_button.grid_remove()  # Hidden until unlocked

        # Celestial Blessings Display Tray (shows acquired relics in Hell's Table)
        self.blessings_tray = tkinter.Frame(self.root, background=TABLE_BACKGROUND_COLOR)
        self.blessings_tray.grid(row=7, column=0, columnspan=3, pady=(0, 4))
        self.blessings_tray.grid_remove()

        # Keyboard shortcuts initialization
        self._setup_keyboard_shortcuts()

    def _setup_keyboard_shortcuts(self):
        """Binds full keyboard shortcut support across the window for gameplay accessibility."""
        # Deal / Hit / New Game shortcuts (Enter and Space)
        for key in ("<Return>", "<KP_Enter>", "<space>"):
            self.root.bind(key, self._on_key_deal_or_hit)
            self.root.bind_class("Button", key, self._on_key_deal_or_hit)

        # Action shortcuts (case-insensitive)
        for key in ("<h>", "<H>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_hit, self.hit_button))
        for key in ("<s>", "<S>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_stand, self.stand_button))
        for key in ("<d>", "<D>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_double_down, self.double_button))
        for key in ("<p>", "<P>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_split, self.split_button))
        for key in ("<r>", "<R>"):
            self.root.bind(key, lambda e: self._on_key_action(self.on_surrender, self.surrender_button))
        for key in ("<c>", "<C>"):
            self.root.bind(key, lambda e: self._on_key_action(self._clear_bet, getattr(self, "clear_bet_button", None)))
        for key in ("<a>", "<A>"):
            self.root.bind(key, lambda e: self._on_key_action(self._all_in, getattr(self, "all_in_button", None)))
        for key in ("<m>", "<M>"):
            self.root.bind(key, lambda e: self._on_toggle_sound())
        for key in ("<v>", "<V>"):
            self.root.bind(key, lambda e: self._on_toggle_dealer_view())
        for key in ("<x>", "<X>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_miracle_draw, getattr(self, "miracle_button", None)))

        # Shortcuts / Help Overlay toggle shortcuts
        for key in ("<question>", "?", "/", "<F1>"):
            self.root.bind(key, lambda e: self._toggle_shortcuts_overlay())

        # Scale and Fullscreen display mode shortcuts
        for key in ("<F10>", "<Shift-S>", "<Shift-s>"):
            self.root.bind(key, lambda e: self.toggle_scale_mode())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())

        # Wardrobe & Hall of Fame shortcuts (Shift+W / Shift+H)
        for key in ("<Shift-W>", "<Shift-w>"):
            self.root.bind(key, lambda e: self._open_wardrobe_dialog(initial_tab=0))
        for key in ("<Shift-H>", "<Shift-h>"):
            self.root.bind(key, lambda e: self._open_wardrobe_dialog(initial_tab=1))

        # Settings dialog shortcuts
        for key in ("<o>", "<O>", "<F2>"):
            self.root.bind(key, lambda e: self._open_settings_dialog())

        # Card Counting Trainer HUD toggle shortcuts
        for key in ("<k>", "<K>", "<Shift-C>", "<Shift-c>"):
            self.root.bind(key, lambda e: self._toggle_card_counting_hud())

        # Table Play Mode cycle shortcut (Shift+M)
        for key in ("<Shift-M>", "<Shift-m>"):
            self.root.bind(key, lambda e: self._on_cycle_play_mode_shortcut())

        # Insurance shortcuts (Y = Take, N = Decline)
        for key in ("<y>", "<Y>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_take_insurance, getattr(self, "take_insurance_button", None)))
        for key in ("<n>", "<N>"):
            self.root.bind(key, lambda e: self._on_key_action(self._on_decline_insurance, getattr(self, "decline_insurance_button", None)))

        # Context-sensitive Escape: closes shortcuts HUD, declines insurance, or exits fullscreen
        self.root.bind("<Escape>", self._on_escape_key)

        # Chip denomination shortcuts: 1=$5, 2=$25, 3=$100, 4=$500, 5=$1000
        chip_keys = {
            "<Key-1>": 5, "<KP_1>": 5,
            "<Key-2>": 25, "<KP_2>": 25,
            "<Key-3>": 100, "<KP_3>": 100,
            "<Key-4>": 500, "<KP_4>": 500,
            "<Key-5>": 1000, "<KP_5>": 1000,
        }
        for k, amt in chip_keys.items():
            self.root.bind(k, lambda e, a=amt: self._on_key_chip(a))

    def _on_key_action(self, action_fn, button=None):
        """Invokes an action function if the corresponding button is currently enabled."""
        if button is not None:
            try:
                if str(button.cget("state")) != "normal":
                    return "break"
            except Exception:
                pass
        action_fn()
        return "break"

    def _on_key_chip(self, amount: int):
        """Adds chip bet if currently in the betting phase."""
        if getattr(self, "is_betting_phase", False) and self.chips_mode_var.get():
            self._add_chip_bet(amount)
        return "break"

    def _on_key_deal_or_hit(self, event=None):
        """
        Handles Enter and Space key presses dynamically based on game state:
        1. If insurance is offered -> takes insurance if enabled.
        2. If betting phase in Chips Mode -> deals hand if bet is valid.
        3. If player's turn -> hits if Hit is enabled.
        4. If round is over -> deals a new game.
        """
        phase = getattr(self, "round_phase", None)

        if phase == RoundPhase.INSURANCE:
            if hasattr(self, "take_insurance_button") and str(self.take_insurance_button.cget("state")) == "normal":
                self._on_take_insurance()
                return "break"

        elif phase == RoundPhase.BETTING:
            if self.chips_mode_var.get() and hasattr(self, "deal_bet_button") and str(self.deal_bet_button.cget("state")) == "normal":
                self._deal_hand_with_bet()
                return "break"

        elif phase == RoundPhase.PLAYER_TURN or (hasattr(self, "hit_button") and str(self.hit_button.cget("state")) == "normal"):
            if hasattr(self, "hit_button") and str(self.hit_button.cget("state")) == "normal":
                self.on_hit()
                return "break"

        elif phase == RoundPhase.ROUND_OVER:
            if hasattr(self, "new_game_button") and str(self.new_game_button.cget("state")) == "normal":
                self.new_game()
                return "break"

        # Fallback for dynamic button state verification
        if getattr(self, "is_insurance_phase", False):
            if hasattr(self, "take_insurance_button") and str(self.take_insurance_button.cget("state")) == "normal":
                self._on_take_insurance()
                return "break"
        if getattr(self, "is_betting_phase", False) and self.chips_mode_var.get():
            if hasattr(self, "deal_bet_button") and str(self.deal_bet_button.cget("state")) == "normal":
                self._deal_hand_with_bet()
                return "break"
        if hasattr(self, "hit_button") and str(self.hit_button.cget("state")) == "normal":
            self.on_hit()
            return "break"
        if hasattr(self, "new_game_button") and str(self.new_game_button.cget("state")) == "normal":
            self.new_game()
            return "break"

        return "break"

    def _on_toggle_sound(self):
        """Toggles sound playback on or off and updates the UI button text."""
        is_enabled = self.sound_manager.toggle_mute()
        self.sound_status_var.set("🔊 Sound: ON" if is_enabled else "🔇 Sound: OFF")
        return "break"

    def _on_toggle_voice(self):
        """Toggles Animalese dialogue voice synthesis on or off."""
        if hasattr(self, "sound_manager") and hasattr(self.sound_manager, "voice_engine") and self.sound_manager.voice_engine:
            self.sound_manager.voice_engine.enabled = not self.sound_manager.voice_engine.enabled
            is_on = self.sound_manager.voice_engine.enabled
            self.voice_status_var.set("🗣 Voice: ON" if is_on else "🤐 Voice: OFF")
        return "break"

    def _toggle_shortcuts_overlay(self):
        """Toggles the display of the keyboard shortcut help overlay dialog."""
        if self._shortcuts_dialog is not None and self._shortcuts_dialog.winfo_exists():
            self._close_shortcuts_overlay()
        else:
            self._show_shortcuts_overlay()
        return "break"

    def _close_shortcuts_overlay(self):
        """Closes and destroys the shortcuts help overlay dialog."""
        if self._shortcuts_dialog is not None:
            try:
                if self._shortcuts_dialog.winfo_exists():
                    self._shortcuts_dialog.destroy()
            except Exception:
                pass
            self._shortcuts_dialog = None

    def _show_shortcuts_overlay(self):
        """Displays a clean modal HUD dialog illustrating all keyboard and mouse controls."""
        if self._shortcuts_dialog is not None and self._shortcuts_dialog.winfo_exists():
            self._shortcuts_dialog.lift()
            self._shortcuts_dialog.focus_set()
            return

        self._shortcuts_dialog = ShortcutsDialog(
            parent=self.root,
            icon_loader=self.icon_loader,
            icon_photo=getattr(self, "_icon_photo", None),
            on_close=self._close_shortcuts_overlay,
        )

    def _open_settings_dialog(self):
        """Displays the casino settings and save management modal dialog."""
        if self._settings_dialog is not None and self._settings_dialog.winfo_exists():
            self._settings_dialog.lift()
            self._settings_dialog.focus_set()
            return "break"
        self._settings_dialog = SettingsDialog(self.root, self)
        return "break"

    def _close_settings_dialog(self):
        """Safely dismisses and destroys the settings dialog."""
        if self._settings_dialog is not None:
            try:
                if self._settings_dialog.winfo_exists():
                    self._settings_dialog.destroy()
            except Exception:
                pass
            self._settings_dialog = None

    def _open_welcome_splash_dialog(self):
        """Displays the initial table preference and welcome modal dialog."""
        if getattr(self, "_welcome_splash_dialog", None) is not None:
            try:
                if self._welcome_splash_dialog.winfo_exists():
                    self._welcome_splash_dialog.lift()
                    self._welcome_splash_dialog.focus_set()
                    return self._welcome_splash_dialog
            except Exception:
                pass
        self._welcome_splash_dialog = WelcomeSplashDialog(
            parent=self.root,
            app=self,
            on_confirm=lambda mode: self.apply_play_mode(mode),
        )
        return self._welcome_splash_dialog

    def _close_welcome_splash_dialog(self):
        """Safely dismisses and destroys the welcome splash dialog."""
        if getattr(self, "_welcome_splash_dialog", None) is not None:
            try:
                if self._welcome_splash_dialog.winfo_exists():
                    self._welcome_splash_dialog.destroy()
            except Exception:
                pass
            self._welcome_splash_dialog = None

    def _on_cycle_play_mode_shortcut(self):
        """Cycles play mode between Casual -> Betting -> Training."""
        modes = ["casual", "betting", "training"]
        try:
            curr_idx = modes.index(getattr(self, "play_mode", "betting"))
        except ValueError:
            curr_idx = 1
        next_mode = modes[(curr_idx + 1) % len(modes)]
        self.apply_play_mode(next_mode)
        self.set_dealer_speech(f"Table mode changed to {next_mode.capitalize()}.", stream=True)
        return "break"

    def apply_play_mode(self, mode: str, sync_save: bool = True):
        """
        Applies table play mode:
        - 'casual': Chips OFF, Card counting HUD hidden, Strategy hints hidden.
        - 'betting': Chips ON, Card counting HUD hidden, Strategy hints hidden.
        - 'training': Chips ON, Card counting HUD visible, Strategy hints active.
        """
        if mode not in ("casual", "betting", "training"):
            return
        self.play_mode = mode
        if hasattr(self, "play_mode_var"):
            self.play_mode_var.set(mode)
        if sync_save and hasattr(self, "save_manager"):
            self.save_manager.set_play_mode(mode)

        if mode == "casual":
            if self.chips_mode_var.get():
                self.chips_mode_var.set(False)
                self._on_toggle_chips_mode(confirm=True)
            if hasattr(self, "card_counting_hud") and self.card_counting_hud and self.card_counting_hud.is_visible:
                self.card_counting_hud.toggle_visibility()
        elif mode == "betting":
            if not self.chips_mode_var.get():
                self.chips_mode_var.set(True)
                self._on_toggle_chips_mode(confirm=True)
            if hasattr(self, "card_counting_hud") and self.card_counting_hud and self.card_counting_hud.is_visible:
                self.card_counting_hud.toggle_visibility()
        elif mode == "training":
            if not self.chips_mode_var.get():
                self.chips_mode_var.set(True)
                self._on_toggle_chips_mode(confirm=True)
            if hasattr(self, "card_counting_hud") and self.card_counting_hud:
                if not self.card_counting_hud.is_visible:
                    self.card_counting_hud.toggle_visibility()
                if not getattr(self, "is_fullscreen", False):
                    try:
                        cur_w = self.root.winfo_width()
                        cur_h = self.root.winfo_height()
                        if cur_h < DEFAULT_WINDOW_HEIGHT:
                            target_h = min(DEFAULT_WINDOW_HEIGHT, self.root.winfo_screenheight() - 80)
                            self.root.geometry(f"{cur_w}x{target_h}")
                    except Exception:
                        pass
                cards_rem = len(self.deck) if hasattr(self, "deck") else 0
                base_bet = self.hand_bets[0] if (hasattr(self, "hand_bets") and self.hand_bets and self.hand_bets[0] > 0) else 25
                self.card_counting_hud.update_counts(cards_remaining=cards_rem, base_bet=base_bet)
                self._refresh_strategy_hint()

    def _stage_recommended_bet(self, amount: int):
        """Sets the current bet to the recommended count amount if in betting phase."""
        if getattr(self, "is_betting_phase", False) and self.chips_mode_var.get():
            clamped_amt = max(MINIMUM_BET, min(self.bankroll_var.get(), amount))
            self.current_bet_var.set(clamped_amt)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.set_bet(clamped_amt, animate=True)
            self._update_bankroll_display()
            if hasattr(self, "deal_bet_button"):
                self.deal_bet_button.configure(state="normal")
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

    def get_current_strategy_hint(self) -> Optional[BasicStrategyDecision]:
        """Computes pure Basic Strategy advice for the active player hand against dealer upcard."""
        if getattr(self, "round_phase", RoundPhase.PLAYER_TURN) != RoundPhase.PLAYER_TURN:
            return None
        if not self.player_hands or not self.dealer_hand:
            return None
        if self.active_hand_index >= len(self.player_hands):
            return None
        player_hand = self.player_hands[self.active_hand_index]
        if not player_hand or not self.dealer_hand:
            return None
        if self._score_player_hand(player_hand) >= BLACKJACK_TARGET:
            return None
        dealer_upcard = self.dealer_hand[0]
        can_double = False
        if hasattr(self, "double_button"):
            try:
                can_double = str(self.double_button.cget("state")) == "normal"
            except Exception:
                pass
        can_split_act = False
        if hasattr(self, "split_button"):
            try:
                can_split_act = str(self.split_button.cget("state")) == "normal"
            except Exception:
                pass
        can_surr = False
        if hasattr(self, "surrender_button"):
            try:
                can_surr = str(self.surrender_button.cget("state")) == "normal"
            except Exception:
                pass
        return get_basic_strategy_decision(
            player_hand=player_hand,
            dealer_upcard=dealer_upcard,
            can_double=can_double,
            can_split=can_split_act,
            can_surrender=can_surr,
        )

    def _refresh_strategy_hint(self):
        """Synchronizes Basic Strategy recommendation with the card counting HUD."""
        if not hasattr(self, "card_counting_hud") or not self.card_counting_hud:
            return
        if getattr(self, "play_mode", "betting") != "training" and not self.card_counting_hud.is_visible:
            self.card_counting_hud.update_strategy_hint(hint=None)
            return
        if getattr(self, "is_betting_phase", False):
            cards_rem = len(self.deck) if hasattr(self, "deck") else 0
            tc = self.card_counter.true_count(cards_rem)
            rec_bet = self.card_counter.get_recommended_bet(25, tc)
            rec_units = max(1, rec_bet // 25)
            self.card_counting_hud.update_strategy_hint(text=f"Bet ${rec_bet} ({rec_units}u)")
            return
        hint = self.get_current_strategy_hint()
        self.card_counting_hud.update_strategy_hint(hint=hint)

    def _on_click_stage_hanger(self):
        """Callback when the wardrobe hanger button on the stage canvas is clicked."""
        self._open_wardrobe_dialog()

    def _open_wardrobe_dialog(self, initial_tab: int = 0):
        """Displays the Dealer Wardrobe & Dressing Room modal dialog."""
        if getattr(self, "_wardrobe_dialog", None) is not None and self._wardrobe_dialog.winfo_exists():
            if initial_tab in (0, 1):
                self._wardrobe_dialog._switch_tab(initial_tab)
            self._wardrobe_dialog.lift()
            self._wardrobe_dialog.focus_set()
            return "break"
        self._wardrobe_dialog = WardrobeDialog(self.root, self, initial_tab=initial_tab)
        return "break"

    def _close_wardrobe_dialog(self):
        """Safely dismisses and destroys the wardrobe dialog."""
        if getattr(self, "_wardrobe_dialog", None) is not None:
            try:
                if self._wardrobe_dialog.winfo_exists():
                    self._wardrobe_dialog.destroy()
            except Exception:
                pass
            self._wardrobe_dialog = None

    def clear_player_save_data(self):
        """Resets persistent save data to blank slate and synchronizes table unlocks."""
        self.save_manager.clear_save()
        self.haunted.unlocked_cursed_stakes = False
        self.haunted.unlocked_exorcist = False
        self.haunted.unlocked_haunted_deck = False
        self.cursed_stakes_var.set(False)
        if hasattr(self, "cursed_stakes_button"):
            self.cursed_stakes_button.grid_remove()

    # ------------------------------------------------------------------------
    # Haunted Halloween & Hell's Table Orchestration
    # ------------------------------------------------------------------------

    def _score_player_hand(self, hand):
        """Scores player hand, taking into account celestial blessings like Cherub's Shield."""
        raw = score_hand(hand)
        if hasattr(self, "haunted"):
            return self.haunted.modify_player_score(raw)
        return raw

    def _on_toggle_dealer_view(self):
        """Dealer view is permanently enabled."""
        self.dealer_view_var.set(True)
        self.dealer_view_status_var.set("👤 Dealer: ON")
        self._update_dealer_avatar()
        return "break"


    def _on_dialogue_click(self, event=None):
        """Fast-forwards in-flight typewriter speech immediately when clicking the dialogue bubble."""
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            self._complete_typewriter_speech()

    def play_dealer_accent(self, char_id_or_cue: Optional[str] = None):
        """Plays the active dealer's signature audio accent (chuckle, rumble, chime, bone clatter)."""
        if not hasattr(self, "sound_manager") or not self.sound_manager:
            return
        now = time.time()
        last_time = getattr(self, "_last_dealer_accent_time", 0.0)
        if now - last_time < 0.30:
            return
        self._last_dealer_accent_time = now

        cue = char_id_or_cue
        if not cue and hasattr(self, "dealer_actor"):
            costume_id = getattr(self.dealer_actor, "current_character", getattr(self.dealer_actor, "costume_id", "julian"))
            profile = CHARACTERS.get(costume_id)
            if profile:
                cue = profile.audio_cue
        if not cue:
            cue = "dealer_julian.ogg"

        self.sound_manager.play_haunted_sound(cue)

    def set_dealer_speech(self, text: str, stream: bool = False):
        """Sets dealer dialogue callout bubble text, updates visibility, draws pointer tail, and animates mouth."""
        if not hasattr(self, "dealer_speech_var"):
            self.dealer_speech_var = tkinter.StringVar(value="")
        self._current_speech_full = text
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            try:
                self.root.after_cancel(self._typewriter_timer_id)
            except Exception:
                pass
            self._typewriter_timer_id = None

        if not text:
            self.clear_dealer_speech()
            return

        # Synchronize palette with active character
        profile = self.dealer_actor.get_profile() if hasattr(self, "dealer_actor") else CHARACTERS["julian"]
        speech_bg = profile.speech_bg
        nameplate_fg = profile.nameplate_fg
        nameplate_title = profile.title

        # Apply palette to dialogue frame & nameplate
        if hasattr(self, "dealer_dialogue_frame"):
            self.dealer_dialogue_frame.configure(background=speech_bg, highlightbackground=nameplate_fg)
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(background=speech_bg, foreground=nameplate_fg, text=nameplate_title)
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.configure(background=speech_bg)
            self.dealer_speech_label.pack(anchor="w", pady=(2, 0))

        # Render vector speech balloon tail on DealerStageCanvas
        if hasattr(self, "dealer_stage_canvas") and hasattr(self.dealer_stage_canvas, "draw_speech_tail"):
            self.dealer_stage_canvas.draw_speech_tail(fill_col=speech_bg, border_col=nameplate_fg)

        # Trigger character signature audio accent (chuckle, rumble, chime, bone clatter)
        self.play_dealer_accent()

        is_headless = getattr(self, "suppress_mode_dialog", False) or (self.root.state() == "withdrawn")
        if stream and not is_headless:
            self._typewriter_index = 0
            self.dealer_speech_var.set("")
            self._stream_typewriter_step()
        elif stream and is_headless:
            self._typewriter_index = 0
            self.dealer_speech_var.set("")
            try:
                if self.root.winfo_exists():
                    self._typewriter_timer_id = self.root.after(28, self._stream_typewriter_step)
            except Exception:
                pass
        else:
            self.dealer_speech_var.set(text)
            if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
                self._animate_speech_mouth(remaining_flaps=min(max(2, len(text) // 8), 8))

    def _stream_typewriter_step(self):
        """Streams one character to the speech balloon at 25-35 ms intervals with conversational cadence."""
        if not hasattr(self, "_current_speech_full") or not self._current_speech_full:
            return
        if self._typewriter_index < len(self._current_speech_full):
            char = self._current_speech_full[self._typewriter_index]
            self._typewriter_index += 1
            self.dealer_speech_var.set(self._current_speech_full[:self._typewriter_index])
            self._step_speech_mouth(char)

            # Procedural Animalese dialogue voice synthesis
            if hasattr(self, "sound_manager") and self.sound_manager:
                inflection = "normal"
                if self._current_speech_full:
                    tail_c = self._current_speech_full.rstrip()[-1:]
                    if tail_c == "?":
                        inflection = "question"
                    elif tail_c == "!":
                        inflection = "exclamation"
                    elif tail_c == ".":
                        inflection = "period"
                cid = "tiffany"
                if hasattr(self, "dealer_actor") and self.dealer_actor:
                    cid = getattr(self.dealer_actor, "character_id", "tiffany")
                self.sound_manager.play_dialogue_blip(cid, char, self._typewriter_index, inflection=inflection)

            # Dynamic 25-35 ms cadence with natural punctuation pauses
            delay = 28
            if char in (".", "!", "?"):
                delay = 55
            elif char in (",", ";", ":", "—"):
                delay = 40

            if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
                try:
                    self.root.after_cancel(self._typewriter_timer_id)
                except Exception:
                    pass
                self._typewriter_timer_id = None

            try:
                if self.root.winfo_exists():
                    self._typewriter_timer_id = self.root.after(delay, self._stream_typewriter_step)
            except Exception:
                pass
        else:
            self._complete_typewriter_speech()

    def _complete_typewriter_speech(self):
        """Completes in-flight typewriter speech immediately."""
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            try:
                self.root.after_cancel(self._typewriter_timer_id)
            except Exception:
                pass
            self._typewriter_timer_id = None
        if hasattr(self, "_current_speech_full") and self._current_speech_full:
            self.dealer_speech_var.set(self._current_speech_full)
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_mouth_state("neutral")
            self._refresh_dealer_avatar_image()

    def clear_dealer_speech(self):
        """Hides dealer dialogue bubble, clears tail, and resets mouth to neutral."""
        if hasattr(self, "_dealer_speech_anim_timer_id") and self._dealer_speech_anim_timer_id:
            try:
                self.root.after_cancel(self._dealer_speech_anim_timer_id)
            except Exception:
                pass
            self._dealer_speech_anim_timer_id = None
        if hasattr(self, "_typewriter_timer_id") and self._typewriter_timer_id:
            try:
                self.root.after_cancel(self._typewriter_timer_id)
            except Exception:
                pass
            self._typewriter_timer_id = None
        self._current_speech_full = ""
        if hasattr(self, "dealer_speech_var"):
            self.dealer_speech_var.set("")
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.pack_forget()
        if hasattr(self, "dealer_stage_canvas") and hasattr(self.dealer_stage_canvas, "clear_speech_tail"):
            self.dealer_stage_canvas.clear_speech_tail()
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_mouth_state("neutral")
            self._refresh_dealer_avatar_image()

    def _calculate_breathing_offset(self, step: float) -> int:
        """Calculates sinusoidal vertical offset in [-2, +2] px for dealer respiration."""
        return int(round(1.8 * math.sin(step)))

    def _dealer_breathing_tick(self):
        """25-30 FPS idle ticker oscillating dealer avatar vertically to simulate breathing and stage particles."""
        if getattr(self, "_dealer_idle_timer_id", None):
            try:
                self.root.after_cancel(self._dealer_idle_timer_id)
            except Exception:
                pass
            self._dealer_idle_timer_id = None
        if not hasattr(self, "root") or not self.root.winfo_exists():
            return
        self._dealer_anim_step += 0.15
        y_off = self._calculate_breathing_offset(self._dealer_anim_step)
        if hasattr(self, "dealer_stage_canvas") and self.dealer_stage_canvas.find_withtag("dealer_sprite"):
            w = max(10, self.dealer_stage_canvas.canvas_width)
            h = max(10, self.dealer_stage_canvas.canvas_height)
            self.dealer_stage_canvas.coords("dealer_sprite", w // 2, h + y_off)

        if hasattr(self, "dealer_stage_canvas"):
            if random.random() < 0.35:
                self.dealer_stage_canvas.spawn_ambient_particles(count=1)
            self.dealer_stage_canvas.update_particles()

        if hasattr(self, "dealer_avatar_label") and self.dealer_avatar_label.winfo_manager() == "pack":
            try:
                self.dealer_avatar_label.pack_configure(pady=(max(0, 2 + y_off), max(0, 2 - y_off)))
            except Exception:
                pass

        try:
            if self.root.winfo_exists():
                self._dealer_idle_timer_id = self.root.after(40, self._dealer_breathing_tick)
        except Exception:
            pass

    def _start_dealer_idle_animation(self):
        """Starts the continuous idle breathing animation ticker."""
        if self._dealer_idle_timer_id is None:
            self._dealer_breathing_tick()

    def _schedule_dealer_blink(self, delay_ms: Optional[int] = None):
        """Schedules the next natural autonomous dealer eye blink."""
        if self._dealer_blink_timer_id:
            try:
                self.root.after_cancel(self._dealer_blink_timer_id)
            except Exception:
                pass
            self._dealer_blink_timer_id = None

        if delay_ms is None:
            delay_ms = random.randint(3000, 5500)

        try:
            if self.root.winfo_exists():
                self._dealer_blink_timer_id = self.root.after(delay_ms, self._trigger_dealer_blink)
        except Exception:
            pass

    def _cancel_blink_timers(self):
        """Safely cancels all active sub-timers for the 3-frame blink sequence."""
        if not hasattr(self, "_dealer_blink_timers"):
            self._dealer_blink_timers = []
        for tid in self._dealer_blink_timers:
            try:
                self.root.after_cancel(tid)
            except Exception:
                pass
        self._dealer_blink_timers.clear()
        if hasattr(self, "_dealer_blink_restore_timer_id") and self._dealer_blink_restore_timer_id:
            try:
                self.root.after_cancel(self._dealer_blink_restore_timer_id)
            except Exception:
                pass
            self._dealer_blink_restore_timer_id = None

    def _trigger_dealer_blink(self, duration_ms: int = 120):
        """Initiates a smooth 3-frame dealer eye blink (open -> half -> closed -> half -> open)."""
        self._cancel_blink_timers()
        self._advance_blink_step(1, duration_ms)

    def _advance_blink_step(self, step: int, duration_ms: int = 120):
        """Advances through the 3-frame eye blink sequence."""
        if not hasattr(self, "dealer_actor"):
            return
        if step == 1:
            self.dealer_actor.set_eye_state("half")
            self._refresh_dealer_avatar_image()
            try:
                if self.root.winfo_exists():
                    tid = self.root.after(int(duration_ms * 0.25), lambda: self._advance_blink_step(2, duration_ms))
                    self._dealer_blink_timers.append(tid)
            except Exception:
                pass
        elif step == 2:
            self.dealer_actor.set_eye_state("closed")
            self._refresh_dealer_avatar_image()
            try:
                if self.root.winfo_exists():
                    tid = self.root.after(int(duration_ms * 0.45), lambda: self._advance_blink_step(3, duration_ms))
                    self._dealer_blink_timers.append(tid)
            except Exception:
                pass
        elif step == 3:
            self.dealer_actor.set_eye_state("half")
            self._refresh_dealer_avatar_image()
            try:
                if self.root.winfo_exists():
                    tid = self.root.after(int(duration_ms * 0.25), lambda: self._advance_blink_step(4, duration_ms))
                    self._dealer_blink_timers.append(tid)
            except Exception:
                pass
        elif step == 4:
            self.dealer_actor.set_eye_state("open")
            self._refresh_dealer_avatar_image()
            self._schedule_dealer_blink()

    def _restore_dealer_eyes(self):
        """Restores dealer eyes to open state and schedules the next blink."""
        self._cancel_blink_timers()
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_eye_state("open")
            self._refresh_dealer_avatar_image()
        self._schedule_dealer_blink()

    def _get_scaled_dealer_photo(self) -> Optional[ImageTk.PhotoImage]:
        """Returns a high-resolution, scale-proportional PhotoImage for the horizon stage with curtain headroom."""
        if not hasattr(self, "dealer_actor"):
            return None
        pil_img = self.dealer_actor.get_composite_image(force_2x=True)
        stage_h = self.dealer_stage_canvas.winfo_height() if hasattr(self, "dealer_stage_canvas") else 250
        if stage_h <= 20:
            stage_h = getattr(self.dealer_stage_canvas, "canvas_height", 250) if hasattr(self, "dealer_stage_canvas") else 250
        max_h = max(100, int(stage_h * 0.88))
        target_size = min(int(190 * self.scale_factor), max_h)
        if pil_img.size != (target_size, target_size):
            resample_mode = getattr(Image, "Resampling", Image).LANCZOS
            pil_img = pil_img.resize((target_size, target_size), resample_mode)
        self._scaled_dealer_photo = ImageTk.PhotoImage(pil_img, master=self.root)
        return self._scaled_dealer_photo


    def _refresh_dealer_avatar_image(self):
        """Lightweight composite re-render on dealer_avatar_label without full UI refresh."""
        if hasattr(self, "dealer_avatar_label") and hasattr(self, "dealer_actor"):
            img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            if img:
                try:
                    self.dealer_avatar_label.configure(image=img)
                    self.dealer_avatar_label.image = img
                except Exception:
                    pass
                if hasattr(self, "dealer_stage_canvas") and getattr(self, "dealer_view_var", None) and self.dealer_view_var.get():
                    self.dealer_stage_canvas.set_dealer_image(img)

    def _step_speech_mouth(self, char: Optional[str] = None):
        """Advances mouth state during speech; drives phonetic visemes if char provided, else alternates."""
        if not hasattr(self, "dealer_actor"):
            return
        if char is not None:
            self.dealer_actor.set_mouth_for_char(char)
        else:
            curr = self.dealer_actor.mouth_state
            next_state = "talk" if curr == "neutral" else "neutral"
            self.dealer_actor.set_mouth_state(next_state)
        self._refresh_dealer_avatar_image()

    def _animate_speech_mouth(self, remaining_flaps: int = 4):
        """Animates mouth flapping while dealer is speaking."""
        if remaining_flaps <= 0:
            if hasattr(self, "dealer_actor"):
                self.dealer_actor.set_mouth_state("neutral")
                self._refresh_dealer_avatar_image()
            self._dealer_speech_anim_timer_id = None
            return

        self._step_speech_mouth()
        try:
            if self.root.winfo_exists():
                self._dealer_speech_anim_timer_id = self.root.after(
                    120, lambda: self._animate_speech_mouth(remaining_flaps - 1)
                )
        except Exception:
            pass

    def _trigger_dealer_deal_gesture(self, duration_ms: int = 350):
        """Animates dealer dealing arm gesture when sweeping cards onto table."""
        if not hasattr(self, "dealer_actor"):
            return
        if self._dealer_gesture_timer_id:
            try:
                self.root.after_cancel(self._dealer_gesture_timer_id)
            except Exception:
                pass
        self.dealer_actor.set_arm_state("deal")
        self.dealer_actor.set_layer_offsets(
            arm_offset=(0, 2),
            eye_gaze_offset=(random.choice([-1, 0, 1]), 1),
        )
        self._refresh_dealer_avatar_image()
        try:
            if self.root.winfo_exists():
                self._dealer_gesture_timer_id = self.root.after(duration_ms, self._restore_dealer_arms)
        except Exception:
            self._restore_dealer_arms()

    def _trigger_dealer_peek_gesture(self, duration_ms: int = 500):
        """Animates dealer peeking at hole card."""
        if not hasattr(self, "dealer_actor"):
            return
        if self._dealer_gesture_timer_id:
            try:
                self.root.after_cancel(self._dealer_gesture_timer_id)
            except Exception:
                pass
        self.dealer_actor.set_arm_state("peek")
        self.dealer_actor.set_layer_offsets(
            head_offset=(0, 1),
            arm_offset=(-1, 1),
            eye_gaze_offset=(-1, 1),
        )
        self._refresh_dealer_avatar_image()
        try:
            if self.root.winfo_exists():
                self._dealer_gesture_timer_id = self.root.after(duration_ms, self._restore_dealer_arms)
        except Exception:
            self._restore_dealer_arms()

    def _restore_dealer_arms(self):
        """Restores dealer arms to resting table position."""
        if hasattr(self, "_dealer_gesture_timer_id") and self._dealer_gesture_timer_id:
            try:
                self.root.after_cancel(self._dealer_gesture_timer_id)
            except Exception:
                pass
            self._dealer_gesture_timer_id = None
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_arm_state("rest")
            self.dealer_actor.set_layer_offsets(
                head_offset=(0, 0),
                arm_offset=(0, 0),
                eye_gaze_offset=(0, 0),
            )
            self._refresh_dealer_avatar_image()

    def _trigger_dealer_gasp(self, duration_ms: int = 1200):
        """Animates surprised gasp mouth expression and spawns sweat drop on busts."""
        if not hasattr(self, "dealer_actor"):
            return
        if hasattr(self, "_dealer_mouth_timer_id") and self._dealer_mouth_timer_id:
            try:
                self.root.after_cancel(self._dealer_mouth_timer_id)
            except Exception:
                pass
            self._dealer_mouth_timer_id = None
        self.dealer_actor.set_mouth_state("gasp")
        self._refresh_dealer_avatar_image()
        if hasattr(self, "dealer_stage_canvas"):
            self.dealer_stage_canvas.spawn_sweat_particle()
            self.dealer_stage_canvas.update_particles()
        try:
            if self.root.winfo_exists():
                self._dealer_mouth_timer_id = self.root.after(duration_ms, self._restore_dealer_mouth)
        except Exception:
            self._restore_dealer_mouth()

    def _trigger_dealer_smirk(self, duration_ms: int = 1500):
        """Animates confident smirk mouth expression on dealer natural or victory."""
        if not hasattr(self, "dealer_actor"):
            return
        if hasattr(self, "_dealer_mouth_timer_id") and self._dealer_mouth_timer_id:
            try:
                self.root.after_cancel(self._dealer_mouth_timer_id)
            except Exception:
                pass
            self._dealer_mouth_timer_id = None
        self.dealer_actor.set_mouth_state("smirk")
        self._refresh_dealer_avatar_image()
        try:
            if self.root.winfo_exists():
                self._dealer_mouth_timer_id = self.root.after(duration_ms, self._restore_dealer_mouth)
        except Exception:
            self._restore_dealer_mouth()

    def _restore_dealer_mouth(self):
        """Restores dealer mouth to neutral resting expression."""
        if hasattr(self, "_dealer_mouth_timer_id") and self._dealer_mouth_timer_id:
            try:
                self.root.after_cancel(self._dealer_mouth_timer_id)
            except Exception:
                pass
            self._dealer_mouth_timer_id = None
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_mouth_state("neutral")
            self._refresh_dealer_avatar_image()

    def _update_dealer_speech_for_outcome(self, outcome: str):
        """Selects theatrical dealer dialogue based on outcome and active haunted phase."""
        phase = self.haunted.phase
        if phase == Phase.HELL_TABLE:
            if outcome == 'NATURAL_BLACKJACK':
                text = "A natural 21?! Insolent mortal, you test my wrath!"
            elif outcome in ('PLAYER_WINS', 'DEALER_BUST'):
                text = "Arrrgh! The fire consumes me... but only for a moment!"
            elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                text = "Claimed! Another fragment of your soul burns in the pit!"
            elif outcome == 'PUSH':
                text = "A standoff... the abyss is patient."
            else:
                text = "Stake your next breath, mortal!"
        elif phase == Phase.VICTORY:
            text = "✦ The holy dawn breaks! The void is sealed! ✦"
        elif phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
            if outcome in ('PLAYER_WINS', 'NATURAL_BLACKJACK'):
                text = "Enjoy your luck while the candles still flicker..."
            elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                text = "The cold deepens. Another flame wavers..."
            else:
                text = "Do you hear the whispers in the dark?"
        else:
            if hasattr(self, "dealer_actor") and self.dealer_actor:
                text = self.dealer_actor.get_outcome_dialogue(outcome)
            elif outcome == 'NATURAL_BLACKJACK':
                text = "Blackjack! Natural 21 pays 3 to 2. Splendid hand."
            elif outcome == 'DEALER_BUST':
                text = "Dealer busts! The table pays all active hands."
            elif outcome == 'PLAYER_WINS':
                text = "Winner! Excellent play."
            elif outcome == 'PLAYER_BUST':
                text = "Bust! House takes the cards."
            elif outcome == 'DEALER_WINS':
                text = "House wins this hand."
            elif outcome == 'PUSH':
                text = "Push! Bets are returned."
            elif outcome == 'SURRENDER':
                text = "Surrendered. Live to wager another day."
            else:
                text = "Place your bets, cards on the felt."

        # Living dealer outcome reaction gestures
        if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
            if outcome == 'DEALER_BUST':
                self._trigger_dealer_gasp()
            elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
                self._trigger_dealer_smirk()
            elif outcome in ('PLAYER_WINS', 'NATURAL_BLACKJACK') and phase == Phase.HELL_TABLE:
                self._trigger_dealer_gasp()

        self.set_dealer_speech(text, stream=True)

    def _update_dealer_speech_for_tactical_action(self, trigger: str):
        """Triggers persona-specific dealer reaction to a mid-hand tactical or risky play."""
        if not hasattr(self, "dealer_actor") or not self.dealer_actor:
            return
        line = self.dealer_actor.get_tactical_dialogue(trigger)
        if line:
            self.set_dealer_speech(line, stream=True)

    def _update_dealer_avatar(self):
        """Updates the dealer avatar image based on toggle state and haunted phase."""
        if not hasattr(self, "dealer_avatar_label"):
            return

        if self.haunted.phase == Phase.HELL_TABLE:
            if hasattr(self, "dealer_actor"):
                self.dealer_actor.equip_costume("malphas")
                demon_img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            else:
                demon_img = self.haunted_assets.get("dealer_demon_0")
            if demon_img:
                self.dealer_avatar_label.configure(image=demon_img)
                self.dealer_avatar_label.image = demon_img
                if hasattr(self, "dealer_stage_canvas"):
                    self.dealer_stage_canvas.set_dealer_image(demon_img)
            self.dealer_avatar_label.pack(side="left", padx=2, pady=2)
            self.dealer_view_status_var.set("☠ The Pit Fiend")
            self.dealer_view_button.configure(state="disabled")
            if hasattr(self, "dealer_nameplate_label"):
                self.dealer_nameplate_label.configure(text="☠ The Pit Fiend", fg="#ff1744")
            self._sync_dealer_stage_colors("#140508")
            return

        self.dealer_view_button.configure(state="normal")
        self.dealer_view_status_var.set("👤 Dealer: ON")

        if hasattr(self, "dealer_actor"):
            if self.haunted.phase == Phase.VICTORY:
                self.dealer_actor.equip_costume("uriel")
            elif self.haunted.phase == Phase.NORMAL:
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)

        bg_col = PANEL_BACKGROUND_COLOR

        if self.haunted.phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
            if hasattr(self, "dealer_actor"):
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)
                img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
                profile = self.dealer_actor.get_profile()
                base_title = profile.title if profile else "The Classic Croupier"
            else:
                img = self.haunted_assets.get("dealer_creep")
                base_title = "The Classic Croupier"
            name_text = f"{base_title} (Hollow)"
            name_col = "#ce93d8"
            bg_col = "#0f0d1a"
        elif self.haunted.phase == Phase.VICTORY:
            if hasattr(self, "dealer_actor"):
                self.dealer_actor.equip_costume("uriel")
                img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
            else:
                img = self.haunted_assets.get("angel_avatar")
            name_text = "✨ Celestial Messenger"
            name_col = "#00e5ff"
            bg_col = "#0d2b26"
        else:
            if hasattr(self, "dealer_actor"):
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)
                img = self._get_scaled_dealer_photo() or self.dealer_actor.get_photo_image()
                profile = self.dealer_actor.get_profile()
                name_text = profile.title
                name_col = profile.nameplate_fg
                bg_col = profile.speech_bg
            else:
                img = self.haunted_assets.get("dealer_classic")
                name_text = "The Classic Croupier"
                name_col = "#ffd700"

        if img:
            self.dealer_avatar_label.configure(image=img)
            self.dealer_avatar_label.image = img
            if hasattr(self, "dealer_stage_canvas"):
                self.dealer_stage_canvas.set_dealer_image(img)
        self.dealer_avatar_label.pack(side="left", padx=2, pady=2)
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(text=name_text, fg=name_col)
        self._sync_dealer_stage_colors(bg_col)

    def _sync_dealer_stage_colors(self, bg_col: str):
        """Synchronizes dealer stage frames with active character/phase atmosphere."""
        if hasattr(self, "dealer_header_row"):
            self.dealer_header_row.configure(background=bg_col)
        if hasattr(self, "dealer_avatar_label"):
            self.dealer_avatar_label.configure(background=bg_col)
        if hasattr(self, "dealer_dialogue_frame"):
            self.dealer_dialogue_frame.configure(background=bg_col)
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(background=bg_col)

    def _sync_accessories_frame_visibility(self):
        """Maps accessories_frame only when Haunted Altar or legacy accessory bars are visible."""
        if not hasattr(self, "accessories_frame"):
            return
        altar_mapped = hasattr(self, "haunted_altar") and bool(self.haunted_altar.winfo_manager())
        candles_mapped = hasattr(self, "candle_bar_frame") and bool(self.candle_bar_frame.winfo_manager())
        graves_mapped = hasattr(self, "gravestones_frame") and bool(self.gravestones_frame.winfo_manager())
        if altar_mapped or candles_mapped or graves_mapped:
            self.accessories_frame.grid(row=0, column=2, sticky="ne", padx=0, pady=0)
        else:
            self.accessories_frame.grid_remove()

    def _update_candles_display(self):
        """Synchronizes 5-candle indicator bar and 2.5D Altar with remaining candles."""
        if hasattr(self, "haunted_altar"):
            if self.haunted.phase in (Phase.OMEN, Phase.SNUFFING) or (self.haunted.phase == Phase.HELL_TABLE and self.haunted.candles_remaining > 0):
                if hasattr(self, "accessories_frame"):
                    self.accessories_frame.grid(row=0, column=2, sticky="ne", padx=0, pady=0)
                if not getattr(self, "_candles_manifested", False):
                    self.haunted_altar.pack(side="top", pady=0)
                    self.haunted_altar.animate_candle_poof()
                    self._candles_manifested = True
                else:
                    self.haunted_altar.pack(side="top", pady=0)
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass
                if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
                    self.card_table_frame.sync_children_felt()
                self.haunted_altar.set_candle_state(self.haunted.candles_remaining, visible=True)
            else:
                self.haunted_altar.set_candle_state(0, visible=False)
                if getattr(self.haunted, "gravestones_risen", 0) <= 0:
                    self.haunted_altar.pack_forget()

        # Legacy fallback synchronization
        if hasattr(self, "candle_bar_frame") and self.candle_labels:
            if self.haunted.phase in (Phase.OMEN, Phase.SNUFFING) or (self.haunted.phase == Phase.HELL_TABLE and self.haunted.candles_remaining > 0):
                self.candle_bar_frame.pack(side="top", pady=2)
                lit_img = self.haunted_assets.get("candle_lit")
                unlit_img = self.haunted_assets.get("candle_unlit")
                for i, lbl in enumerate(self.candle_labels):
                    img = lit_img if i < self.haunted.candles_remaining else unlit_img
                    if img:
                        lbl.configure(image=img)
                        lbl.image = img
            else:
                self.candle_bar_frame.pack_forget()
        self._sync_accessories_frame_visibility()

    def _update_gravestones_display(self):
        """Displays gravestones rising through the felt on deaths / busts with kinetic eruption."""
        if hasattr(self, "haunted_altar"):
            if self.haunted.gravestones_risen <= 0 or self.haunted.phase == Phase.NORMAL:
                self.haunted_altar.set_gravestone_state(0, visible=False)
                if not (self.haunted.phase in (Phase.OMEN, Phase.SNUFFING) or (self.haunted.phase == Phase.HELL_TABLE and self.haunted.candles_remaining > 0)):
                    self.haunted_altar.pack_forget()
            else:
                if hasattr(self, "accessories_frame"):
                    self.accessories_frame.grid(row=0, column=2, sticky="ne", padx=0, pady=0)
                self.haunted_altar.pack(side="top", pady=0)
                try:
                    self.root.update_idletasks()
                except Exception:
                    pass
                if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
                    self.card_table_frame.sync_children_felt()
                new_risen = self.haunted.gravestones_risen
                last_risen = getattr(self, "_last_gravestones_risen", 0)
                if new_risen > last_risen:
                    stone_idx = min(new_risen, 5) - 1
                    self.haunted_altar.set_gravestone_state(new_risen, visible=True)
                    self.haunted_altar.animate_grave_eruption(stone_idx)
                    self._last_gravestones_risen = new_risen
                else:
                    self.haunted_altar.set_gravestone_state(new_risen, visible=True)

        # Legacy fallback synchronization (kept populated for compatibility, but never packed to avoid duplicate rendering)
        if hasattr(self, "gravestones_frame") and self.gravestone_labels is not None and self.gravestones_frame.winfo_exists():
            self.gravestones_frame.pack_forget()
            grave_img = self.haunted_assets.get("gravestone")
            for child in self.gravestones_frame.winfo_children():
                child.destroy()
            self.gravestone_labels.clear()
            if self.haunted.gravestones_risen > 0 and self.haunted.phase != Phase.NORMAL:
                count = min(self.haunted.gravestones_risen, 5)
                for _ in range(count):
                    lbl = tkinter.Label(self.gravestones_frame, image=grave_img, background=PANEL_BACKGROUND_COLOR)
                    lbl.image = grave_img
                    self.gravestone_labels.append(lbl)
        self._sync_accessories_frame_visibility()

    def _update_blessings_tray(self):
        """Renders equipped relic badges in the blessings tray."""
        if not hasattr(self, "blessings_tray"):
            return
        for child in self.blessings_tray.winfo_children():
            child.destroy()

        if self.haunted.phase != Phase.HELL_TABLE or not self.haunted.equipped_blessings:
            self.blessings_tray.grid_remove()
            if hasattr(self, "miracle_button"):
                self.miracle_button.grid_remove()
            return

        bg_col = self.root["background"]
        self.blessings_tray.configure(background=bg_col)
        self.blessings_tray.grid()
        tkinter.Label(
            self.blessings_tray, text="✦ RELICS: ", font=("Arial", 9, "bold"),
            fg="#ffd700", background=bg_col
        ).pack(side="left", padx=(0, 4))

        for b in sorted(self.haunted.equipped_blessings, key=lambda x: x.value):
            details = BLESSING_REGISTRY[b]
            img = self.haunted_assets.get(f"relic_{b.value}") or self.haunted_assets.get(b.value)
            f = tkinter.Frame(self.blessings_tray, background="#051f38", relief="ridge", borderwidth=1, padx=4, pady=2)
            f.pack(side="left", padx=3)
            if img:
                ilbl = tkinter.Label(f, image=img, background="#051f38")
                ilbl.image = img
                ilbl.pack(side="left", padx=2)
            tkinter.Label(
                f, text=details.title, font=("Arial", 8, "bold"),
                fg="#80cbc4", background="#051f38"
            ).pack(side="left")

        if Blessing.MIRACLE in self.haunted.equipped_blessings and hasattr(self, "miracle_button"):
            action_btn_pad = int(6 * self.scale_factor)
            btn_pady = int(3 * self.scale_factor)
            self.miracle_button.grid(row=0, column=6, padx=action_btn_pad, pady=btn_pady)
            can_miracle = self.haunted.can_use_miracle_draw()
            self.miracle_button.configure(state="normal" if can_miracle else "disabled")

    def _apply_phase_theme(self, phase: Phase):
        """Applies atmospheric table felt darkening and infernal/celestial colors via ThemePalette."""
        palette = get_phase_palette(phase, getattr(self.haunted, "hand_counter", 1))

        bg_tbl = palette.table_bg
        bg_pnl = palette.panel_bg
        fg_res = palette.result_fg
        stage_bg = palette.stage_bg
        plaque_bg = bg_pnl
        plaque_border = palette.plaque_border

        self.root.configure(background=bg_tbl)

        # Batch configure table-background container frames and labels
        for attr in ("scoreboard_frame", "bankroll_label", "betting_frame", "bet_chips_label", "button_frame", "blessings_tray"):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.configure(background=bg_tbl)

        # Result status label
        if hasattr(self, "result_label"):
            self.result_label.configure(background=bg_tbl, fg=fg_res)

        # Panel-background widgets
        for attr in ("chip_visualizer", "accessories_frame", "candle_bar_frame", "gravestones_frame", "insurance_frame", "insurance_label"):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.configure(background=bg_pnl)

        # Plaque score headers (dealer & player)
        for frame_attr, title_attr, score_attr in (
            ("dealer_header_frame", "dealer_title_label", "dealer_score_label"),
            ("player_header_frame", "player_title_label", "player_score_label"),
        ):
            f_widget = getattr(self, frame_attr, None)
            if f_widget is not None:
                f_widget.configure(background=plaque_bg, highlightbackground=plaque_border)
            t_widget = getattr(self, title_attr, None)
            if t_widget is not None:
                t_widget.configure(background=plaque_bg)
            s_widget = getattr(self, score_attr, None)
            if s_widget is not None:
                s_widget.configure(background=plaque_bg)

        # Controls with panel bg and table active bg
        for attr in ("dealer_view_button", "scale_button", "fullscreen_button"):
            btn = getattr(self, attr, None)
            if btn is not None:
                btn.configure(background=bg_pnl, activebackground=bg_tbl)

        # Card container frames (dealer & player)
        for frame_attr in ("dealer_cards_frame", "player_cards_frame"):
            cf = getattr(self, frame_attr, None)
            if cf is not None:
                cf.configure(background=bg_pnl)
                for child in cf.winfo_children():
                    try:
                        child.configure(background=bg_pnl)
                        for sub in child.winfo_children():
                            try:
                                sub.configure(background=bg_pnl)
                            except Exception:
                                pass
                    except Exception:
                        pass

        # Card table felt canvas
        if hasattr(self, "card_table_frame"):
            if isinstance(self.card_table_frame, TableFeltCanvas):
                self.card_table_frame.set_theme(palette.felt_theme)
            self.card_table_frame.configure(background=bg_pnl)

        # Stage background widgets
        for attr in ("dealer_stage_frame", "dealer_panel", "dealer_header_row", "dealer_actor_frame", "pumpkin_label", "dealer_avatar_label"):
            widget = getattr(self, attr, None)
            if widget is not None:
                widget.configure(background=stage_bg)

        if hasattr(self, "dealer_stage_canvas"):
            self.dealer_stage_canvas.configure(background=stage_bg)
            self.dealer_stage_canvas.set_theme(palette.felt_theme)

        # Dealer costume selection by phase
        if hasattr(self, "dealer_actor"):
            if phase == Phase.HELL_TABLE:
                self.dealer_actor.equip_costume("malphas")
            elif phase == Phase.VICTORY:
                self.dealer_actor.equip_costume("uriel")
            elif phase == Phase.NORMAL:
                equipped = getattr(getattr(self, "save_manager", None), "data", None).equipped_costume if hasattr(self, "save_manager") else "julian"
                self.dealer_actor.equip_costume(equipped)

        # Theatrical Dealer Dialogue Frame
        if hasattr(self, "dealer_dialogue_frame"):
            self.dealer_dialogue_frame.configure(background=palette.dialogue_bg)
        if hasattr(self, "dealer_nameplate_label"):
            profile = self.dealer_actor.get_profile() if hasattr(self, "dealer_actor") else None
            base_title = profile.title if profile else "The Classic Croupier"
            nameplate_fg = profile.nameplate_fg if profile else "#ffd700"
            nameplate_text = base_title
            if phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING):
                nameplate_fg = "#ce93d8"
                nameplate_text = f"{base_title} (Hollow)"
            elif phase == Phase.HELL_TABLE:
                nameplate_fg = "#ff1744"
                nameplate_text = "☠ The Pit Fiend"
            elif phase == Phase.VICTORY:
                nameplate_fg = "#00e5ff"
                nameplate_text = "✨ Celestial Messenger"
            self.dealer_nameplate_label.configure(background=palette.dialogue_bg, fg=nameplate_fg, text=nameplate_text)
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.configure(background=palette.speech_bg)
        if hasattr(self, "horizon_rail"):
            self.horizon_rail.configure(background=palette.rail_bg)

        # Table HUD and Altar
        if hasattr(self, "haunted_altar"):
            self.haunted_altar.set_theme_color(bg_pnl, is_hell_table=(phase == Phase.HELL_TABLE))
        if hasattr(self, "announcement_hud"):
            border_col = "#ff1744" if phase == Phase.HELL_TABLE else ("#00e5ff" if phase == Phase.VICTORY else None)
            self.announcement_hud.set_theme_color(bg_pnl, border_color=border_col)

        if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
            try:
                self.card_table_frame.sync_children_felt()
            except Exception:
                pass

    def _start_ambient_animations(self):
        """Starts non-blocking timer loop for flickering pumpkin and animated demonic eyes."""
        try:
            if self.root.state() == "withdrawn":
                return
        except Exception:
            return
        if self._ambient_timer_id is None:
            self._ambient_timer_id = self.root.after(600, self._tick_ambient_animations)

    def _tick_ambient_animations(self):
        """Ticks ambient animations non-blockingly."""
        self._ambient_timer_id = None
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return

        self._anim_frame_toggle = not self._anim_frame_toggle
        frame_idx = 1 if self._anim_frame_toggle else 0

        # 1. Flickering Pumpkin
        if hasattr(self, "pumpkin_label"):
            if self.haunted.phase in (Phase.CREEP, Phase.OMEN, Phase.SNUFFING, Phase.HELL_TABLE):
                pack_kw = {"before": self.dealer_avatar_label} if hasattr(self, "dealer_avatar_label") and self.dealer_avatar_label.winfo_manager() == "pack" else {}
                self.pumpkin_label.pack(side="left", padx=(0, 6), pady=2, **pack_kw)
                p_img = self.haunted_assets.get(f"pumpkin_glow_{frame_idx}")
                if p_img:
                    self.pumpkin_label.configure(image=p_img)
                    self.pumpkin_label.image = p_img
            else:
                self.pumpkin_label.pack_forget()

        # Schedule next tick safely
        try:
            if self.root.winfo_exists() and self.root.state() != "withdrawn":
                self._ambient_timer_id = self.root.after(600, self._tick_ambient_animations)
        except Exception:
            pass

    def _trigger_hell_table(self):
        """Transitions into Hell's Table mode with bell audio, dialogs, and draft."""
        self.haunted.start_hell_table()
        self.sound_manager.play_haunted_sound("hell_bell")
        self._apply_phase_theme(Phase.HELL_TABLE)
        self._update_candles_display()
        self._update_gravestones_display()

        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.grid_remove()
        self.soul_meter_canvas.grid()
        self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=False)

        self.dealer_view_var.set(True)
        self._update_dealer_avatar()
        self.set_dealer_speech("Your soul is on the line now, mortal! The pit claims all.", stream=True)
        self.sound_manager.play_haunted_sound("demon_reveal")

        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            self._open_angelic_draft()
            return

        def on_fiend_closed():
            self.sound_manager.play_haunted_sound("angel_chime")
            self._show_angel_dialog(on_close=self._open_angelic_draft)

        self._show_pit_fiend_dialog(on_close=on_fiend_closed)

    def _show_pit_fiend_dialog(self, on_close=None):
        """Displays atmospheric Pit Fiend narrative challenge."""
        text = (
            "Welcome to the Abyssal Wager, mortal.\n\n"
            "Your petty chips mean nothing here. The stakes are now your immortal Soul.\n\n"
            "Win hands to claw your way back to the light... Fail, and you belong to the Pit forever."
        )
        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("malphas", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("dealer_demon_0")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="☠ THE ABYSSAL WAGER ☠",
            speaker="☠ THE PIT FIEND ☠",
            portrait_img=port_img,
            text_content=text,
            button_text="Face Your Fate",
            on_close=on_close,
            is_celestial=False,
        )

    def _show_angel_dialog(self, on_close=None):
        """Displays Angelic messenger offering celestial intervention."""
        text = (
            "Be not afraid, mortal soul. The Heavens have witnessed this unholy trap.\n\n"
            "I grant you sacred blessings forged in celestial fire. Choose your relic wisely, "
            "and banish the Fiend with righteous hands."
        )
        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("uriel", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("angel_avatar")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="✦ CELESTIAL INTERVENTION ✦",
            speaker="✦ CELESTIAL MESSENGER ✦",
            portrait_img=port_img,
            text_content=text,
            button_text="Accept Divine Aid",
            on_close=on_close,
            is_celestial=True,
        )

    def _open_angelic_draft(self):
        """Opens Balatro-style Roguelike draft modal for celestial blessings."""
        choices = self.haunted.get_draft_choices(count=3)
        if not choices:
            return

        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            self.haunted.equip_blessing(choices[0])
            self._update_blessings_tray()
            return

        relic_map = {b.value: self.haunted_assets.get(f"relic_{b.value}") for b in choices}

        def on_drafted(b: Blessing):
            self.haunted.equip_blessing(b)
            self.sound_manager.play_haunted_sound("angel_chime")
            self._update_blessings_tray()
            self.result_var.set(f"✦ Relic Equipped: {BLESSING_REGISTRY[b].title}!")

        self._active_draft_dialog = AngelicDraftDialog(
            self.root, choices=choices, relic_icons=relic_map, on_select=on_drafted
        )

    def _show_victory_dialog(self):
        """Displays triumphant banishment dialogue and awards spoils."""
        self._apply_phase_theme(Phase.VICTORY)
        self.bankroll_var.set(self.bankroll_var.get() + 6666)
        if hasattr(self, "save_manager"):
            self.save_manager.unlock_achievement("exorcist")
            self.save_manager.record_bankroll(self.bankroll_var.get())
        if hasattr(self, "cursed_stakes_button"):
            s = self.scale_factor
            self.cursed_stakes_button.grid(row=0, column=8, padx=(int(6 * s), int(8 * s)), pady=int(3 * s), sticky="e")

        def on_victory_close():
            self.haunted.reset_after_victory()
            self._candles_manifested = False
            self._last_gravestones_risen = 0
            self._update_candles_display()
            self._update_gravestones_display()
            self._update_blessings_tray()
            if hasattr(self, "pumpkin_label"):
                self.pumpkin_label.pack_forget()
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.grid_remove()
            if hasattr(self, "chip_visualizer") and self.chips_mode_var.get():
                self.chip_visualizer.grid()
            self._apply_phase_theme(Phase.NORMAL)
            if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
                try:
                    self.card_table_frame.sync_children_felt()
                except Exception:
                    pass
            self._update_bankroll_display()
            self._update_dealer_avatar()
            self.set_dealer_speech("✦ Darkness is banished! Peace returns to the table. ✦", stream=True)
            self.result_var.set("VICTORY! +$6,666 Exorcist Bounty Claimed!")

        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            on_victory_close()
            return

        text = (
            "The Pit Fiend is banished back to the void! Your soul shines untarnished.\n\n"
            "The Heavens have bestowed upon you the EXORCIST title and +$6,666 casino bankroll.\n\n"
            "You have unlocked permanent Cursed Stakes mode at the bottom action bar!"
        )
        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("uriel", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("angel_avatar")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="✦ THE EXORCIST'S TRIUMPH ✦",
            speaker="✦ CELESTIAL MESSENGER ✦",
            portrait_img=port_img,
            text_content=text,
            button_text="Return to Table",
            on_close=on_victory_close,
            is_celestial=True,
        )

    def _show_defeat_dialog(self):
        """Displays defeat dialogue with choice to retry Hell's Table or flee."""
        is_headless = getattr(self, "suppress_mode_dialog", False)
        try:
            is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
        except Exception:
            is_withdrawn = True

        if is_headless or is_withdrawn:
            self.haunted.second_chance()
            self.new_game()
            return

        text = (
            "Your soul is claimed! Dragged down into the suffocating abyss...\n\n"
            "Yet the House of Damnation is ever insatiable. Will you stake your next life "
            "for another chance at redemption?"
        )

        def on_retry():
            self.haunted.second_chance()
            self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=False)
            self.new_game()

        port_img = None
        if hasattr(self, "dealer_actor"):
            port_img = self.dealer_actor.get_bust_photo_image("malphas", scale_factor=self.scale_factor)
        if port_img is None:
            port_img = self.haunted_assets.get("dealer_demon_0")
        self._active_story_dialog = StoryDialogueDialog(
            self.root,
            title="☠ SOUL FORFEIT ☠",
            speaker="☠ THE PIT FIEND ☠",
            portrait_img=port_img,
            text_content=text,
            button_text="Second Chance (25% Soul)",
            on_close=on_retry,
            is_celestial=False,
        )

    def _on_miracle_draw(self):
        """Miracle Draw: banishes the last dealt player card and draws a fresh one."""
        if getattr(self, "round_phase", RoundPhase.PLAYER_TURN) != RoundPhase.PLAYER_TURN:
            return
        if not self.haunted.can_use_miracle_draw():
            return
        if not self.player_hand:
            return

        self.haunted.use_miracle_draw()
        self.sound_manager.play_haunted_sound("angel_chime")

        self.player_hand.pop()
        self._deal_card_to_player(self.active_hand_index)
        self.result_var.set("🌟 Miracle Draw invoked! Card banished and redrawn.")
        if hasattr(self, "miracle_button"):
            self.miracle_button.configure(state="disabled")

    def _on_toggle_cursed_stakes(self):
        """Manually launches Hell's Table mode for replayability."""
        self._trigger_hell_table()
        self.new_game()

    # ------------------------------------------------------------------------
    # Game Flow & Actions
    # ------------------------------------------------------------------------

    def _update_shoe_display(self):
        """Updates the shoe cards remaining label text."""
        if hasattr(self, "shoe_info_var"):
            total = len(self.all_cards) * self.deck_count
            remaining = len(self.deck)
            cut_notice = " [Cut]" if self.shoe_needs_reshuffle else ""
            self.shoe_info_var.set(f"Shoe: {remaining}/{total}{cut_notice}")

    def _update_action_buttons(self):
        """Evaluates and applies eligibility for Hit, Stand, Double, Split, and Surrender."""
        if not self.player_hands or self.active_hand_index >= len(self.player_hands):
            self._set_action_buttons_state("disabled")
            return

        hand = self.player_hands[self.active_hand_index]
        score = self._score_player_hand(hand)

        if score >= BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            return

        # Hit & Stand are available for active hand
        self.hit_button.configure(state="normal")
        self.stand_button.configure(state="normal")

        # Double Down: exactly 2 cards in current hand, and sufficient bankroll if in Chips Mode
        can_double = (len(hand) == 2)
        if can_double and self.chips_mode_var.get() and self.hand_bets:
            current_bet = self.hand_bets[self.active_hand_index] if self.active_hand_index < len(self.hand_bets) else 0
            can_double = (self.bankroll_var.get() >= current_bet and current_bet > 0)
        self.double_button.configure(state="normal" if can_double else "disabled")

        # Split: only on initial 2 cards of non-split hand, matching rank, and sufficient bankroll
        can_sp = (len(self.player_hands) == 1 and can_split(self.player_hands[0]))
        if can_sp and self.chips_mode_var.get() and self.hand_bets:
            can_sp = (self.bankroll_var.get() >= self.hand_bets[0])
        self.split_button.configure(state="normal" if can_sp else "disabled")

        # Surrender: only on initial 2 cards of non-split hand (before any hit, double, or split)
        can_surr = (len(self.player_hands) == 1 and len(self.player_hands[0]) == 2)
        self.surrender_button.configure(state="normal" if can_surr else "disabled")

        self._refresh_strategy_hint()

    def new_game(self):
        """Starts a fresh round of Blackjack or enters betting phase depending on Chips Mode."""
        # 0. Cancel any active dealer timer from a prior round
        if self._dealer_timer_id:
            try:
                self.root.after_cancel(self._dealer_timer_id)
            except Exception:
                pass
            self._dealer_timer_id = None
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.clear_timers()
        if hasattr(self, "announcement_hud"):
            self.announcement_hud.dismiss()

        # 1. Reset deck/shoe and hands
        if not self.deck or self.shoe_needs_reshuffle or len(self.deck) < 15:
            self.deck = build_shoe(self.all_cards, self.deck_count)
            self.shoe_needs_reshuffle = False
            if hasattr(self, "card_counter") and self.card_counter:
                if hasattr(self, "save_manager") and self.save_manager:
                    self.save_manager.evaluate_shoe_whisperer(reset_shoe_tracker=True)
                self.card_counter.reset_shoe(deck_count=self.deck_count)
                self._hole_card_observed = False
                if hasattr(self, "card_counting_hud") and self.card_counting_hud:
                    self.card_counting_hud.update_counts(cards_remaining=len(self.deck))
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_card_shuffle()

        self._update_shoe_display()
        self.player_hands = [Hand()]
        self.active_hand_index = 0
        self.dealer_hand = Hand()
        if hasattr(self, "engine"):
            self.engine.player_hands = self.player_hands
            self.engine.dealer_hand = self.dealer_hand
        self.dealer_hole_card = None
        self.dealer_hole_widget = None
        self.is_hole_card_hidden = False
        self._hole_card_observed = False

        # 2. Clear card visuals from frames and unmap them to keep table felt clean during betting
        for child in self.dealer_cards_frame.winfo_children():
            child.destroy()
        for child in self.player_cards_frame.winfo_children():
            child.destroy()
        self.dealer_cards_frame.grid_remove()
        self.player_cards_frame.grid_remove()


        # 3. Reset scores and status
        self.dealer_score_var.set("0")
        self.player_score_var.set("0")
        self.result_var.set("")
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        self.is_insurance_phase = False
        if hasattr(self, "insurance_frame"):
            self.insurance_frame.grid_remove()

        # Haunted progression & table synchronization
        phase = self.haunted.on_new_hand()
        self._apply_phase_theme(phase)
        self._update_dealer_avatar()
        if hasattr(self, "dealer_actor"):
            self._restore_dealer_arms()
            self._restore_dealer_mouth()
        self.clear_dealer_speech()
        self._update_candles_display()
        self._update_gravestones_display()
        self._update_blessings_tray()

        if self.haunted.phase == Phase.HELL_TABLE:
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid_remove()
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.grid()
                self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=False)
            self.is_betting_phase = False
            self._start_round_deal()
        elif self.chips_mode_var.get():
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.grid_remove()
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid()
            self._enter_betting_phase()
        else:
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.grid_remove()
            self.is_betting_phase = False
            self._start_round_deal()

    def _enter_betting_phase(self):
        """Transitions game state into the betting phase where player places chips."""
        self.is_betting_phase = True
        self.round_phase = RoundPhase.BETTING
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")

        bankroll = self.bankroll_var.get()
        if bankroll < MINIMUM_BET and self.current_bet_var.get() < MINIMUM_BET:
            self.current_bet_var.set(0)
            self.result_var.set("Bankroll empty! Click Rebuy ($1,000) to keep playing.")
        else:
            # Default staged bet: preserve previous bet if affordable, or MINIMUM_BET
            if self.current_bet_var.get() == 0 or self.current_bet_var.get() > bankroll:
                if self.hand_bets and 0 < self.hand_bets[0] <= bankroll:
                    self.current_bet_var.set(self.hand_bets[0])
                elif bankroll >= MINIMUM_BET:
                    self.current_bet_var.set(MINIMUM_BET)
                else:
                    self.current_bet_var.set(0)
            self.result_var.set("Place your bet and click 'Deal Hand'")

        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.set_bet(self.current_bet_var.get(), animate=False)

        self._update_bankroll_display()
        self._update_betting_controls()
        self._refresh_strategy_hint()

    def _start_round_deal(self):
        """Authentic initial deal: 2 cards to player, 2 to dealer (1 face-down hole card)."""
        self.round_phase = RoundPhase.PLAYER_TURN
        self.result_var.set("")
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")
        self.insurance_bet = 0
        self.last_insurance_lost = 0
        if hasattr(self, "insurance_frame"):
            self.insurance_frame.grid_remove()

        if self.chips_mode_var.get():
            self._update_betting_controls()

        # Player gets 2 cards face-up
        self._deal_card_to_player(hand_index=0)
        self._deal_card_to_player(hand_index=0)

        # Dealer gets 1 card face-up and 1 card face-down (the hole card)
        self._deal_card_to_dealer(is_hole_card=False)
        self._deal_card_to_dealer(is_hole_card=True)

        # Check if player immediately busted on deal (e.g. Cursed Card 13)
        player_score = self._score_player_hand(self.player_hands[0])
        if player_score > BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            self._reveal_dealer_hole_card()
            self._conclude_round()
            return

        # Check for Insurance (Dealer upcard is Ace in Chips Mode)
        dealer_upcard = self.dealer_hand[0]
        is_ace = getattr(dealer_upcard, "rank", "") == "ace" or (isinstance(dealer_upcard, (tuple, list)) and dealer_upcard[0] == 1)
        if self.chips_mode_var.get() and is_ace:
            self._prompt_insurance()
        else:
            # Check for Natural Blackjack and Action eligibility
            self._check_initial_blackjack()

    def _on_toggle_chips_mode(self, confirm: bool = None):
        """Handles switching between Casual Mode (Chips OFF) and Casino Mode (Chips ON)."""
        if self.chips_mode_var.get():
            self.save_manager.set_chips_mode(True)
            # Chips Mode activated: reset bankroll to starting $1,000 as per policy
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.hand_bets = [0]
            self.bankroll_label.grid()
            self.betting_frame.grid()
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid()
                self.chip_visualizer.set_bet(0, animate=False)
                if hasattr(self, "card_table_frame"):
                    self.card_table_frame.sync_children_felt()
            self._update_bankroll_display()
            self.new_game()
        else:
            # Chips Mode deactivated: confirm forfeit of bankroll
            if confirm is None:
                # In headless test environments or withdrawn root, auto-confirm without modal popup
                is_headless = getattr(self, "suppress_mode_dialog", False)
                try:
                    is_withdrawn = (self.root.state() == "withdrawn") or (not self.root.winfo_ismapped())
                except Exception:
                    is_withdrawn = True

                if is_headless or is_withdrawn:
                    confirm = True
                else:
                    try:
                        import tkinter.messagebox as messagebox
                        confirm = messagebox.askyesno(
                            "Exit Chips Mode?",
                            "Leaving Chips Mode will forfeit your current bankroll progress and any active wagers.\n\n"
                            f"Returning to Chips Mode later will reset your bankroll to the starting ${STARTING_BANKROLL:,}.\n\n"
                            "Do you want to switch to Casual Mode?"
                        )
                    except Exception:
                        confirm = True

            if not confirm:
                # User cancelled: keep Chips Mode ON
                self.chips_mode_var.set(True)
                return

            self.save_manager.set_chips_mode(False)
            # User confirmed: reset bankroll to starting $1,000 and clear chips state
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.hand_bets = [0]
            self.bankroll_label.grid_remove()
            self.betting_frame.grid_remove()
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid_remove()
                self.chip_visualizer.clear_timers()
            if hasattr(self, "insurance_frame"):
                self.insurance_frame.grid_remove()
            self.last_insurance_lost = 0
            self.is_insurance_phase = False
            self.insurance_bet = 0
            self.is_betting_phase = False
            self.new_game()

    def _add_chip_bet(self, amount: int):
        """Adds chip amount to the staged bet, bounded by available bankroll."""
        if not self.is_betting_phase:
            return
        current_bet = self.current_bet_var.get()
        bankroll = self.bankroll_var.get()
        if current_bet + amount <= bankroll:
            new_bet = current_bet + amount
            self.current_bet_var.set(new_bet)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.animate_chip_drop(amount, new_bet)
            self._update_bankroll_display()
            self._update_betting_controls()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

    def _clear_bet(self):
        """Resets the staged bet back to 0."""
        if not self.is_betting_phase:
            return
        self.current_bet_var.set(0)
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.animate_clear()
        self._update_bankroll_display()
        self._update_betting_controls()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_chip_clear()

    def _all_in(self):
        """Sets the staged bet to the player's full remaining bankroll."""
        if not self.is_betting_phase:
            return
        bankroll = self.bankroll_var.get()
        if bankroll >= MINIMUM_BET:
            self.current_bet_var.set(bankroll)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.set_bet(bankroll, animate=False)
            self._update_bankroll_display()
            self._update_betting_controls()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_stack()

    def _deal_hand_with_bet(self):
        """Commits the staged bet, deducts it from bankroll, and begins the deal."""
        if not self.is_betting_phase:
            return
        bet = self.current_bet_var.get()
        bankroll = self.bankroll_var.get()
        if bet < MINIMUM_BET or bet > bankroll:
            return
        self.bankroll_var.set(bankroll - bet)
        self.hand_bets = [bet]
        self.is_betting_phase = False
        if hasattr(self, "engine"):
            self.engine.current_bet = bet
            self.engine.bankroll = self.bankroll_var.get()
        if hasattr(self, "event_bus") and self.event_bus:
            self.event_bus.emit(GameEventType.BET_COMMITTED, {"bet": bet, "bankroll": self.bankroll_var.get()})
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.set_bet(bet, animate=False)
        self._update_bankroll_display()
        self._update_betting_controls()
        self._start_round_deal()

    def _rebuy(self):
        """Replenishes player bankroll if it drops below the minimum bet."""
        if self.bankroll_var.get() < MINIMUM_BET and self.current_bet_var.get() < MINIMUM_BET:
            self.bankroll_var.set(STARTING_BANKROLL)
            self.current_bet_var.set(0)
            self.result_var.set("Bankroll replenished to $1,000! Place your bet.")
            self._update_bankroll_display()
            self._update_betting_controls()

    def _update_bankroll_display(self):
        """Updates the bankroll & bet label text and synchronizes the bottom-right bankroll chip piles."""
        if not hasattr(self, "bankroll_label"):
            return
        bankroll = self.bankroll_var.get()
        bet = self.current_bet_var.get() if self.is_betting_phase else sum(self.hand_bets)
        self.bankroll_label.configure(
            text=f"Bankroll: ${bankroll:,}  |  Bet: ${bet:,}"
        )
        if hasattr(self, "chip_visualizer"):
            available = max(0, bankroll - self.current_bet_var.get()) if self.is_betting_phase else max(0, bankroll)
            self.chip_visualizer.set_bankroll(available, interactive=self.is_betting_phase)

    def _update_betting_controls(self):
        """Updates states of chip buttons, clear bet, deal, and rebuy buttons."""
        if not self.chips_mode_var.get() or not hasattr(self, "chip_buttons") or not self.chip_buttons:
            return

        bankroll = self.bankroll_var.get()
        staged_bet = self.current_bet_var.get()
        remaining = max(0, bankroll - staged_bet)
        if hasattr(self, "chip_visualizer"):
            avail = remaining if self.is_betting_phase else max(0, bankroll)
            self.chip_visualizer.set_bankroll(avail, interactive=self.is_betting_phase)

        if self.is_betting_phase:
            for btn, (denom, _, _) in zip(self.chip_buttons, CHIP_DENOMINATIONS):
                btn.configure(state="normal" if remaining >= denom else "disabled")
            if hasattr(self, "all_in_button"):
                self.all_in_button.configure(state="normal" if bankroll >= MINIMUM_BET and staged_bet < bankroll else "disabled")
            self.clear_bet_button.configure(state="normal" if staged_bet > 0 else "disabled")
            self.deal_bet_button.configure(state="normal" if staged_bet >= MINIMUM_BET else "disabled")
            if bankroll < MINIMUM_BET and staged_bet < MINIMUM_BET:
                self.rebuy_button.configure(state="normal")
            else:
                self.rebuy_button.configure(state="disabled")
        else:
            # During active card play or dealer turn, betting controls are disabled
            for btn in self.chip_buttons:
                btn.configure(state="disabled")
            if hasattr(self, "all_in_button"):
                self.all_in_button.configure(state="disabled")
            self.clear_bet_button.configure(state="disabled")
            self.deal_bet_button.configure(state="disabled")
            self.rebuy_button.configure(state="disabled")

    def _prompt_insurance(self):
        """Offers the insurance side bet when the dealer shows an Ace in Chips Mode."""
        self.is_insurance_phase = True
        self.round_phase = RoundPhase.INSURANCE
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")

        main_bet = self.hand_bets[0] if self.hand_bets else 0
        insurance_cost = main_bet // 2
        bankroll = self.bankroll_var.get()
        can_afford = (bankroll >= insurance_cost and insurance_cost >= 1)

        self.take_insurance_button.configure(
            text=f"Take Insurance (${insurance_cost})",
            state="normal" if can_afford else "disabled"
        )
        self.result_var.set("Dealer shows an Ace. Take insurance?")
        self.insurance_frame.grid()

    def _on_take_insurance(self):
        """Handles player taking insurance."""
        if not self.is_insurance_phase:
            return
        main_bet = self.hand_bets[0] if self.hand_bets else 0
        insurance_cost = main_bet // 2
        if self.bankroll_var.get() < insurance_cost or insurance_cost < 1:
            return

        self.bankroll_var.set(self.bankroll_var.get() - insurance_cost)
        self.insurance_bet = insurance_cost
        self._update_bankroll_display()
        self._resolve_insurance_decision()

    def _on_decline_insurance(self):
        """Handles player declining insurance."""
        if not self.is_insurance_phase:
            return
        self.insurance_bet = 0
        self._resolve_insurance_decision()

    def _resolve_insurance_decision(self):
        """Concludes insurance phase, peeks at dealer hole card, and resolves or resumes play."""
        self.is_insurance_phase = False
        self.round_phase = RoundPhase.PLAYER_TURN
        self.insurance_frame.grid_remove()

        dealer_score = score_hand(self.dealer_hand)
        dealer_has_bj = (len(self.dealer_hand) == 2 and dealer_score == BLACKJACK_TARGET)

        if dealer_has_bj:
            # Dealer has Natural Blackjack
            if self.insurance_bet > 0:
                main_bet = self.hand_bets[0] if self.hand_bets else 0
                payout = calculate_insurance_payout(True, self.insurance_bet, main_bet=main_bet)
                self.bankroll_var.set(self.bankroll_var.get() + payout)
                self._update_bankroll_display()
            self._reveal_dealer_hole_card()
            self._conclude_round()
        else:
            # Dealer does not have Blackjack
            if self.insurance_bet > 0:
                lost_amount = self.insurance_bet
                self.last_insurance_lost = lost_amount
                self.insurance_bet = 0  # Insurance lost
                self.result_var.set(f"Dealer has no Blackjack. Insurance lost (-${lost_amount}). Your turn!")
            else:
                self.result_var.set("")

            # Check if player has Natural Blackjack or bust
            player_score = self._score_player_hand(self.player_hands[0])
            if player_score >= BLACKJACK_TARGET:
                self._reveal_dealer_hole_card()
                self._conclude_round()
            else:
                # Normal player turn: action buttons evaluated dynamically
                self._update_action_buttons()

    def _draw_card(self):
        """Pops the next card from the shoe, marking cut card if penetration threshold reached."""
        if not self.deck:
            self.deck = build_shoe(self.all_cards, self.deck_count)
            self.shoe_needs_reshuffle = False
            if hasattr(self, "card_counter") and self.card_counter:
                if hasattr(self, "save_manager") and self.save_manager:
                    self.save_manager.evaluate_shoe_whisperer(reset_shoe_tracker=True)
                self.card_counter.reset_shoe(deck_count=self.deck_count)
                self._hole_card_observed = False
                if hasattr(self, "card_counting_hud") and self.card_counting_hud:
                    self.card_counting_hud.update_counts(cards_remaining=len(self.deck))

        card = self.deck.pop()
        total_shoe_cards = len(self.all_cards) * self.deck_count
        if len(self.deck) <= int(total_shoe_cards * CUT_CARD_PENETRATION):
            self.shoe_needs_reshuffle = True

        if hasattr(self, "event_bus") and self.event_bus:
            self.event_bus.emit(GameEventType.CARD_DEALT, {"card": card, "cards_remaining": len(self.deck)})

        self._update_shoe_display()

        # In Hell's Table, transform face cards to animated demonic editions
        if getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE:
            rank = getattr(card, "rank", "")
            if rank in ("jack", "queen", "king"):
                haunted_img = self.haunted_assets.get(f"{rank}_haunted_0")
                if haunted_img:
                    card = Card(card.value, haunted_img, rank=rank, suit=card.suit)

        return card

    def _deal_card_to_player(self, hand_index=None):
        """Deals one card to the active player hand and updates visuals."""
        if hand_index is None:
            hand_index = self.active_hand_index

        # Hand 13 Omen injection check
        if getattr(self, "haunted", None) and self.haunted.phase == Phase.OMEN and len(self.player_hands[hand_index]) == 1 and self.card_13:
            card = self.card_13
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("clock_chime_13")
            self.result_var.set("The clock strikes 13... The 13 of Skulls is dealt!")
        else:
            card = self._draw_card()

        self.player_hands[hand_index].append(card)
        self._observe_card_face_up(card)

        # Seraph's Grace: once per hand, automatically banish and redraw a card that would cause a bust (> 21)
        if (
            len(self.player_hands[hand_index]) >= 2
            and self._score_player_hand(self.player_hands[hand_index]) > BLACKJACK_TARGET
            and getattr(self, "haunted", None)
            and self.haunted.can_use_seraph_redraw()
        ):
            self.haunted.use_seraph_redraw()
            self.player_hands[hand_index].pop()
            replacement = self._draw_card()
            self.player_hands[hand_index].append(replacement)
            self._observe_card_face_up(replacement)
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("angel_chime")
            self.result_var.set("✦ Seraph's Grace! Busting card banished and redrawn!")

        self._render_player_cards()
        self._update_player_score_display()
        if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
            self._trigger_dealer_deal_gesture()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_card_deal()

    def _get_or_create_dealer_cards_container(self, bg_pnl: str) -> tkinter.Frame:
        """Returns or creates the centered container for dealer cards."""
        self.dealer_cards_frame.grid()
        if not hasattr(self, "_dealer_cards_container") or not self._dealer_cards_container.winfo_exists():
            self._dealer_cards_container = tkinter.Frame(self.dealer_cards_frame, background=bg_pnl)
            self._dealer_cards_container.pack(anchor="center")
        return self._dealer_cards_container

    def _deal_card_to_dealer(self, is_hole_card=False):
        """
        Deals one card to the dealer.
        If `is_hole_card` is True, renders `back.png` and hides its score until Stand.
        """
        card = self._draw_card()
        self.dealer_hand.append(card)
        eye_revealed = bool(
            is_hole_card
            and getattr(self, "haunted", None)
            and Blessing.EYE in self.haunted.equipped_blessings
        )
        if not is_hole_card or eye_revealed:
            self._observe_card_face_up(card)
            if is_hole_card:
                self._hole_card_observed = True
        else:
            self._hole_card_observed = False
        if hasattr(self, "dealer_actor") and self.root.winfo_exists() and self.root.state() != "withdrawn":
            self._trigger_dealer_deal_gesture()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_card_deal()

        bg_pnl = self.card_table_frame["background"] if hasattr(self, "card_table_frame") else PANEL_BACKGROUND_COLOR
        container = self._get_or_create_dealer_cards_container(bg_pnl)
        padx = int(2 * self.scale_factor)

        if is_hole_card:
            # Face-down hole card
            self.dealer_hole_card = card
            self.is_hole_card_hidden = True
            if getattr(self, "haunted", None) and Blessing.EYE in self.haunted.equipped_blessings:
                # Eye of Providence Blessing reveals hole card immediately in halo!
                self.dealer_hole_widget = tkinter.Label(
                    container, image=card[1],
                    relief="solid", borderwidth=1, highlightthickness=1,
                    highlightbackground="#00e5ff", background=bg_pnl
                )
                self.dealer_hole_widget.pack(side="left", padx=padx)
                self.dealer_score_var.set(f"{score_hand(self.dealer_hand)} (Revealed)")
            else:
                back_img = self.haunted_assets.get("back_haunted") if (getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE) else self.back_image
                self.dealer_hole_widget = tkinter.Label(
                    container, image=back_img or self.back_image,
                    relief="flat", borderwidth=0, highlightthickness=0,
                    background=bg_pnl
                )
                self.dealer_hole_widget.pack(side="left", padx=padx)
                upcard_score = score_hand([self.dealer_hand[0]])
                self.dealer_score_var.set(f"{upcard_score} + ?")
        else:
            # Face-up card
            tkinter.Label(
                container, image=card[1],
                relief="flat", borderwidth=0, highlightthickness=0,
                background=bg_pnl
            ).pack(side="left", padx=padx)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))

    def _render_dealer_cards(self):
        """Renders visual card labels for dealer hand centered according to current scale factor."""
        for child in self.dealer_cards_frame.winfo_children():
            child.destroy()
        if hasattr(self, "_dealer_cards_container"):
            delattr(self, "_dealer_cards_container")

        bg_pnl = self.card_table_frame["background"] if hasattr(self, "card_table_frame") else PANEL_BACKGROUND_COLOR
        padx = int(2 * self.scale_factor)

        num_cards = len(self.dealer_hand)
        if num_cards == 0:
            self.dealer_cards_frame.configure(width=1, height=1)
            self.dealer_cards_frame.grid_remove()
            try:
                self.dealer_cards_frame.place(x=0, y=0, width=1, height=1)
                self.root.update_idletasks()
                self.dealer_cards_frame.place_forget()
            except Exception:
                pass
            return
        self.dealer_cards_frame.grid()
        container = self._get_or_create_dealer_cards_container(bg_pnl)

        if num_cards > 4:
            # Overlapping layout for 5+ cards to prevent table felt overflow
            card_w = getattr(self, "card_width", CARD_WIDTH)
            card_h = getattr(self, "card_height", CARD_HEIGHT)
            overlap = self._calculate_hand_overlap(num_cards, is_split=False)
            frame_width = card_w + (num_cards - 1) * overlap
            container.configure(width=frame_width, height=card_h)
            container.pack_propagate(False)
            for i, card in enumerate(self.dealer_hand):
                if i == 1 and getattr(self, "is_hole_card_hidden", False):
                    back_img = self.haunted_assets.get("back_haunted") if (getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE) else self.back_image
                    self.dealer_hole_widget = tkinter.Label(
                        container, image=back_img or self.back_image,
                        relief="flat", borderwidth=0, highlightthickness=0,
                        background=bg_pnl
                    )
                    self.dealer_hole_widget.place(x=i * overlap, y=0, width=card_w, height=card_h)
                else:
                    lbl = tkinter.Label(
                        container, image=card[1],
                        relief="flat", borderwidth=0, highlightthickness=0,
                        background=bg_pnl
                    )
                    lbl.place(x=i * overlap, y=0, width=card_w, height=card_h)
                    if i == 1 and not getattr(self, "is_hole_card_hidden", False):
                        self.dealer_hole_widget = lbl
        else:
            container.pack_propagate(True)
            for i, card in enumerate(self.dealer_hand):
                if i == 1 and getattr(self, "is_hole_card_hidden", False):
                    # Hole card face down (or revealed with halo by Eye of Providence)
                    if getattr(self, "haunted", None) and Blessing.EYE in self.haunted.equipped_blessings:
                        self.dealer_hole_widget = tkinter.Label(
                            container, image=card[1],
                            relief="solid", borderwidth=1, highlightthickness=1,
                            highlightbackground="#00e5ff", background=bg_pnl
                        )
                        self.dealer_hole_widget.pack(side="left", padx=padx)
                    else:
                        back_img = self.haunted_assets.get("back_haunted") if (getattr(self, "haunted", None) and self.haunted.phase == Phase.HELL_TABLE) else self.back_image
                        self.dealer_hole_widget = tkinter.Label(
                            container, image=back_img or self.back_image,
                            relief="flat", borderwidth=0, highlightthickness=0,
                            background=bg_pnl
                        )
                        self.dealer_hole_widget.pack(side="left", padx=padx)
                else:
                    lbl = tkinter.Label(
                        container, image=card[1],
                        relief="flat", borderwidth=0, highlightthickness=0,
                        background=bg_pnl
                    )
                    lbl.pack(side="left", padx=padx)
                    if i == 1 and not getattr(self, "is_hole_card_hidden", False):
                        self.dealer_hole_widget = lbl

    def _calculate_hand_overlap(self, num_cards: int, is_split: bool) -> int:
        """Dynamically compresses card overlap offset when hand has many cards to prevent right-edge overflow."""
        base_overlap = getattr(self, "card_overlap_offset", PLAYER_CARD_OVERLAP_OFFSET)
        if num_cards <= 4:
            return base_overlap
        # For hands with 5+ cards, compress overlap dynamically to prevent table overflow
        factor = 0.7 if is_split else 0.85
        compressed = int(base_overlap * (factor ** (num_cards - 4)))
        min_overlap = int(12 * self.scale_factor)
        return max(min_overlap, compressed)

    def _render_player_cards(self):
        """Renders visual card labels and hand frames for player hand(s) centered on table felt."""
        for child in self.player_cards_frame.winfo_children():
            child.destroy()

        if not any(len(h) > 0 for h in self.player_hands):
            self.player_cards_frame.configure(width=1, height=1)
            self.player_cards_frame.grid_remove()
            try:
                self.player_cards_frame.place(x=0, y=0, width=1, height=1)
                self.root.update_idletasks()
                self.player_cards_frame.place_forget()
            except Exception:
                pass
            return

        self.player_cards_frame.grid()
        is_split = len(self.player_hands) > 1
        bg_pnl = self.card_table_frame["background"] if hasattr(self, "card_table_frame") else PANEL_BACKGROUND_COLOR

        player_container = tkinter.Frame(self.player_cards_frame, background=bg_pnl)

        player_container.pack(anchor="center")

        for idx, hand in enumerate(self.player_hands):
            is_active = (idx == self.active_hand_index)
            container = tkinter.Frame(
                player_container,
                background=bg_pnl,
                padx=6,
                pady=4,
                relief="groove" if is_split else "flat",
                borderwidth=2 if is_split else 0
            )
            container.pack(side="left", padx=10 if is_split else 0)

            if is_split:
                status_suffix = " (Active)" if is_active else ""
                title = f"Hand {idx + 1}{status_suffix}"
                fg_color = "#ffeb3b" if is_active else "#cfd8dc"
                tkinter.Label(
                    container, text=title, font=("Arial", 9, "bold"),
                    background=bg_pnl, fg=fg_color
                ).pack(anchor="w", pady=(0, 2))

            num_cards = len(hand)
            card_w = getattr(self, "card_width", CARD_WIDTH)
            card_h = getattr(self, "card_height", CARD_HEIGHT)
            available_h = self.card_table_frame.winfo_height() if hasattr(self, "card_table_frame") else 0
            if available_h > 40 and available_h < (card_h * 2 + 10):
                card_h = max(36, (available_h - 14) // 2)
                card_w = max(24, int(card_h * (CARD_WIDTH / CARD_HEIGHT)))
            overlap = self._calculate_hand_overlap(num_cards, is_split)

            if num_cards == 0:
                frame_width = card_w
            else:
                frame_width = card_w + (num_cards - 1) * overlap

            cards_frame = tkinter.Frame(
                container, background=bg_pnl,
                width=frame_width, height=card_h
            )
            cards_frame.pack(side="top")
            cards_frame.pack_propagate(False)

            for i, card in enumerate(hand):
                lbl = tkinter.Label(
                    cards_frame, image=card[1],
                    relief="flat", borderwidth=0, highlightthickness=0,
                    background=bg_pnl
                )
                lbl.place(x=i * overlap, y=0, width=card_w, height=card_h)

    def _update_player_score_display(self):
        """Updates the reactive player score variable."""
        if len(self.player_hands) == 1:
            self.player_score_var.set(str(self._score_player_hand(self.player_hands[0])))
        else:
            scores = [str(self._score_player_hand(h)) for h in self.player_hands]
            self.player_score_var.set(f"H1: {scores[0]} | H2: {scores[1]}")

    def _check_initial_blackjack(self):
        """
        Inspects hands immediately after initial deal for Natural Blackjacks (21 on 2 cards)
        or immediate busts (e.g., cursed 13 card).
        Resolves immediately if either player or dealer has 21, or if player has busted.
        Otherwise, configures action buttons (Hit, Stand, Double, Split, Surrender).
        """
        player_score = self._score_player_hand(self.player_hands[0])
        dealer_score = score_hand(self.dealer_hand)
        if self.dealer_hand and self.dealer_hand[0][0] in (1, 10):
            if hasattr(self, "dealer_actor") and self.root.winfo_exists():
                self._trigger_dealer_peek_gesture()
        if player_score >= BLACKJACK_TARGET or dealer_score >= BLACKJACK_TARGET:
            self._set_action_buttons_state("disabled")
            self._reveal_dealer_hole_card()
            self._conclude_round()
        else:
            self._update_action_buttons()

    def _observe_card_face_up(self, card):
        """Observes a face-up card for Hi-Lo card counting and updates HUD & floating badge."""
        if not hasattr(self, "card_counter") or self.card_counter is None or card is None:
            return
        tag = self.card_counter.observe_card(card)
        if hasattr(self, "card_counting_hud") and self.card_counting_hud:
            cards_rem = len(self.deck) if hasattr(self, "deck") else 0
            base_bet = 25
            if hasattr(self, "hand_bets") and self.hand_bets and self.hand_bets[0] > 0:
                base_bet = self.hand_bets[0]
            self.card_counting_hud.update_counts(cards_remaining=cards_rem, base_bet=base_bet)
            # Spawn floating tag badge if HUD is visible and table felt exists
            if self.card_counting_hud.is_visible and hasattr(self, "card_table_frame") and self.root.winfo_exists() and self.root.state() != "withdrawn":
                FloatingCountBadge(master=self.card_table_frame, tag_value=tag).place(
                    relx=0.5, rely=0.5, anchor="center"
                )

    def _toggle_card_counting_hud(self):
        """Toggles the display of the Card Counting Trainer HUD."""
        if hasattr(self, "card_counting_hud") and self.card_counting_hud:
            is_vis = self.card_counting_hud.toggle_visibility()
            if is_vis:
                if not getattr(self, "is_fullscreen", False):
                    try:
                        cur_w = self.root.winfo_width()
                        cur_h = self.root.winfo_height()
                        if cur_h < DEFAULT_WINDOW_HEIGHT:
                            target_h = min(DEFAULT_WINDOW_HEIGHT, self.root.winfo_screenheight() - 80)
                            self.root.geometry(f"{cur_w}x{target_h}")
                    except Exception:
                        pass
                cards_rem = len(self.deck) if hasattr(self, "deck") else 0
                base_bet = self.hand_bets[0] if (hasattr(self, "hand_bets") and self.hand_bets and self.hand_bets[0] > 0) else 25
                self.card_counting_hud.update_counts(cards_remaining=cards_rem, base_bet=base_bet)
            self._refresh_strategy_hint()
        return "break"

    def _open_card_counting_quiz(self):
        """Opens the card counting drill quiz dialog."""
        if not hasattr(self, "card_counter") or not self.card_counter:
            return
        cards_rem = len(self.deck) if hasattr(self, "deck") else 0
        CardCountingQuizDialog(
            parent=self.root,
            counter=self.card_counter,
            cards_remaining=cards_rem,
            on_result=self._on_counting_quiz_result,
        )

    def _on_counting_quiz_result(self, is_correct: bool, actual_rc: int, actual_tc: float):
        """Handles result of card counting drill quiz and records persistence."""
        if hasattr(self, "save_manager") and self.save_manager:
            streak, unl_app, unl_mas = self.save_manager.record_counting_quiz(is_correct)
            if unl_app:
                self.set_dealer_speech("Impressive count! You've unlocked the Apprentice Counter achievement!", stream=True)
            elif unl_mas:
                self.set_dealer_speech("Masterful precision! You've unlocked the Master Counter achievement!", stream=True)

    def _reveal_dealer_hole_card(self):
        """Flips the dealer's hole card face-up and displays the full dealer score."""
        self.is_hole_card_hidden = False
        if not getattr(self, "_hole_card_observed", False) and len(self.dealer_hand) > 1:
            self._observe_card_face_up(self.dealer_hand[1])
            self._hole_card_observed = True
        if self.dealer_hole_widget and self.dealer_hole_card:
            self.dealer_hole_widget.configure(image=self.dealer_hole_card[1], relief="flat", borderwidth=0, highlightthickness=0)
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_card_place()

    def on_split(self):
        """
        Handles the 'Split' action. Separates the initial two matching cards
        into two independent hands and deals one card to each.
        In Chips Mode, requires and deducts a matching wager for the second hand.
        """
        if not can_split(self.player_hands[0]):
            return

        if self.chips_mode_var.get():
            hand1_bet = self.hand_bets[0] if self.hand_bets else 0
            if self.bankroll_var.get() < hand1_bet:
                return  # Insufficient funds to match bet
            self.bankroll_var.set(self.bankroll_var.get() - hand1_bet)
            self.hand_bets.append(hand1_bet)
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.set_bet(sum(self.hand_bets), animate=False)
            self._update_bankroll_display()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

        # 1. Separate into two hands
        card1 = self.player_hands[0][0]
        card2 = self.player_hands[0][1]
        hand1_bet = self.hand_bets[0] if self.hand_bets else 0
        h1 = Hand([card1], bet=hand1_bet, is_split=True)
        h2 = Hand([card2], bet=hand1_bet, is_split=True)
        self.player_hands = [h1, h2]
        self.active_hand_index = 0
        if hasattr(self, "engine"):
            self.engine.player_hands = self.player_hands
        if hasattr(self, "event_bus") and self.event_bus:
            self.event_bus.emit(GameEventType.HAND_SPLIT, {"hands": 2})

        # 2. Deal second card to both Hand 1 and Hand 2
        self._deal_card_to_player(hand_index=0)
        self._deal_card_to_player(hand_index=1)
        self._update_dealer_speech_for_tactical_action("SPLIT_PAIR")

        # 3. Update action buttons for Hand 1 (Double Down available on 2 cards if eligible)
        self._update_action_buttons()

        # 4. Check if Hand 1 reached 21 on the deal
        if score_hand(self.player_hands[0]) == BLACKJACK_TARGET:
            self.on_stand()

    def on_double_down(self):
        """
        Handles the 'Double' player action.
        Doubles the wager on the active hand, deals exactly 1 card, and automatically stands (or busts).
        """
        hand = self.player_hands[self.active_hand_index]
        if len(hand) != 2:
            return

        if self.chips_mode_var.get() and self.hand_bets:
            current_bet = self.hand_bets[self.active_hand_index]
            if self.bankroll_var.get() < current_bet:
                return  # Cannot afford double
            self.bankroll_var.set(self.bankroll_var.get() - current_bet)
            self.hand_bets[self.active_hand_index] += current_bet
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.animate_chip_drop(current_bet, sum(self.hand_bets))
            self._update_bankroll_display()
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_chip_add()

        # Mark double flag for Hell's Table scoring calculations
        self._last_was_double = True
        active_h = self.player_hands[self.active_hand_index]
        if isinstance(active_h, Hand):
            active_h.is_doubled = True
            if self.hand_bets and self.active_hand_index < len(self.hand_bets):
                active_h.bet = self.hand_bets[self.active_hand_index]

        # Disable double, split, and surrender buttons immediately
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")

        score_before_double = self._score_player_hand(hand)
        # Deal exactly 1 card
        self._deal_card_to_player()
        score = self._score_player_hand(self.player_hands[self.active_hand_index])
        if score_before_double == 11 and score <= BLACKJACK_TARGET:
            self._update_dealer_speech_for_tactical_action("DOUBLE_ELEVEN")

        if score > BLACKJACK_TARGET:
            # Busted on double down
            if self.active_hand_index < len(self.player_hands) - 1:
                # Advance to next split hand
                self.active_hand_index += 1
                self.result_var.set("Hand 1 busted on Double! Playing Hand 2...")
                self._render_player_cards()
                self._update_player_score_display()
                self._update_action_buttons()
                if self._score_player_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                    self.on_stand()
            else:
                all_busted = all(self._score_player_hand(h) > BLACKJACK_TARGET for h in self.player_hands)
                if all_busted:
                    self._reveal_dealer_hole_card()
                    self._conclude_round()
                else:
                    self.round_phase = RoundPhase.DEALER_TURN
                    self._set_action_buttons_state("disabled")
                    self.new_game_button.configure(state="disabled")
                    self._refresh_strategy_hint()
                    self._reveal_dealer_hole_card()
                    self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        else:
            # Automatically stand after receiving exactly one card
            self.on_stand()

    def on_surrender(self):
        """
        Handles the 'Surrender' player action (Late Surrender).
        Forfeits the hand after dealer checks for Blackjack, recovering 50% of the initial bet.
        """
        if len(self.player_hands) != 1 or len(self.player_hands[0]) != 2:
            return

        self.round_phase = RoundPhase.ROUND_OVER
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")
        self._reveal_dealer_hole_card()
        if hasattr(self, "sound_manager"):
            self.sound_manager.play_surrender()

        if self.chips_mode_var.get() and self.hand_bets:
            bet = self.hand_bets[0]
            refund = bet // 2
            loss = bet - refund
            self.bankroll_var.set(self.bankroll_var.get() + refund)
            self._update_bankroll_display()
            self._record_outcome('DEALER_WINS')
            self.result_var.set(f"Surrendered. Half bet returned (${refund:,}). (-${loss:,})")
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.animate_loss()
            self._update_betting_controls()
        else:
            self._record_outcome('DEALER_WINS')
            self.result_var.set("Surrendered. Hand forfeited.")

        self.new_game_button.configure(state="normal")
        self._refresh_strategy_hint()

    def on_hit(self):
        """
        Handles the 'Hit' player action.
        Deals a card to the currently active hand, checks for bust or 21.
        """
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")
        hand_before = self.player_hands[self.active_hand_index]
        score_before = self._score_player_hand(hand_before)
        is_risky_stiff = score_before in (15, 16) and not is_soft_hand(hand_before)
        self._deal_card_to_player()
        current_hand = self.player_hands[self.active_hand_index]
        current_score = self._score_player_hand(current_hand)
        if is_risky_stiff and current_score <= BLACKJACK_TARGET:
            self._update_dealer_speech_for_tactical_action("RISKY_HIT")

        if current_score > BLACKJACK_TARGET:
            # Current hand busted!
            if self.active_hand_index < len(self.player_hands) - 1:
                # Move to next split hand
                self.active_hand_index += 1
                self.result_var.set("Hand 1 busted! Playing Hand 2...")
                self._render_player_cards()
                self._update_player_score_display()
                self._update_action_buttons()
                if self._score_player_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                    self.on_stand()
            else:
                # Final hand has completed (busted)
                all_busted = all(self._score_player_hand(h) > BLACKJACK_TARGET for h in self.player_hands)
                if all_busted:
                    self._reveal_dealer_hole_card()
                    self._conclude_round()
                else:
                    # At least one earlier hand is still in play; dealer plays
                    self.round_phase = RoundPhase.DEALER_TURN
                    self._set_action_buttons_state("disabled")
                    self.new_game_button.configure(state="disabled")
                    self._refresh_strategy_hint()
                    self._reveal_dealer_hole_card()
                    self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        elif current_score == BLACKJACK_TARGET:
            self.on_stand()
        else:
            self._update_action_buttons()

    def on_stand(self):
        """
        Handles the 'Stand' player action.
        If playing split hands and Hand 1 stands, advances to Hand 2.
        Once all player hands have stood, begins dealer turn.
        """
        self.double_button.configure(state="disabled")
        self.split_button.configure(state="disabled")
        self.surrender_button.configure(state="disabled")

        if self.active_hand_index < len(self.player_hands) - 1:
            # Advance to Hand 2
            self.active_hand_index += 1
            self._render_player_cards()
            self._update_player_score_display()
            self._update_action_buttons()
            if score_hand(self.player_hands[self.active_hand_index]) == BLACKJACK_TARGET:
                self.on_stand()
            return

        # All player hands completed -> transition to dealer turn
        self.round_phase = RoundPhase.DEALER_TURN
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="disabled")
        self._refresh_strategy_hint()
        self._reveal_dealer_hole_card()
        self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)

    def _dealer_step(self):
        """
        Non-blocking recursive timer step for dealer draws.

        How it works:
        - Check if the dealer needs another card (< 17).
        - If YES: deals one card and reschedules itself via `root.after()`.
          Control immediately returns to the Tkinter event loop, keeping the UI responsive.
        - If NO: concludes the round and awards wins.
        """
        self._dealer_timer_id = None

        # Guard against window close during active callback
        if not self.root.winfo_exists():
            return

        if dealer_should_hit(self.dealer_hand):
            # Dealer must draw
            card = self._draw_card()
            self.dealer_hand.append(card)
            self._observe_card_face_up(card)
            self._render_dealer_cards()
            self.dealer_score_var.set(str(score_hand(self.dealer_hand)))
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_card_deal()

            # Schedule the next dealer step after the delay
            self._dealer_timer_id = self.root.after(DEALER_DRAW_DELAY_MS, self._dealer_step)
        else:
            # Dealer stands or busts; conclude round
            self._conclude_round()

    def _conclude_round(self):
        """Determines the winner for all player hands, updates win counters, resolves payouts, and enables 'New Game'."""
        self.round_phase = RoundPhase.ROUND_OVER
        is_split = len(self.player_hands) > 1

        outcomes = []
        messages = []
        payouts = []
        profits = []

        # 1. Evaluate each player hand independently
        for i, hand in enumerate(self.player_hands):
            score = self._score_player_hand(hand)
            outcome, message = determine_outcome(
                hand, self.dealer_hand, is_split=is_split, player_score_override=score
            )
            self._record_outcome(outcome)
            outcomes.append(outcome)
            messages.append(message)

            if self.chips_mode_var.get() and self.hand_bets:
                bet = self.hand_bets[i] if i < len(self.hand_bets) else 0
                payout = calculate_payout(outcome, bet)
                profit = payout - bet
                payouts.append(payout)
                profits.append(profit)

        # 2. Financial resolution and UI outcome formatting
        ins_profit = 0
        if self.chips_mode_var.get() and self.hand_bets:
            total_payout = sum(payouts)
            total_profit = sum(profits)
            self.bankroll_var.set(self.bankroll_var.get() + total_payout)

            # Insurance side bet resolution
            ins_str = ""
            dealer_has_bj = (len(self.dealer_hand) == 2 and score_hand(self.dealer_hand) == BLACKJACK_TARGET)
            if self.insurance_bet > 0 and dealer_has_bj:
                main_bet = self.hand_bets[0] if self.hand_bets else 0
                ins_payout = calculate_insurance_payout(True, self.insurance_bet, main_bet=main_bet)
                ins_profit = ins_payout - self.insurance_bet
                ins_str = f" | Insurance won (+${ins_profit})"
                self.insurance_bet = 0
            elif self.last_insurance_lost > 0:
                ins_str = f" | Insurance lost (-${self.last_insurance_lost})"
                self.last_insurance_lost = 0

            cur_msg = self.result_var.get()
            prefix = "The clock strikes 13... The 13 of Skulls is dealt! | " if "The clock strikes 13" in cur_msg else ""

            if not is_split:
                profit = profits[0]
                net_str = f" (+${profit})" if profit > 0 else (f" (-${abs(profit)})" if profit < 0 else " (Push)")
                self.result_var.set(f"{prefix}{messages[0]}{net_str}{ins_str}")
            else:
                p1_str = f"+${profits[0]}" if profits[0] > 0 else (f"-${abs(profits[0])}" if profits[0] < 0 else "Push")
                p2_str = f"+${profits[1]}" if profits[1] > 0 else (f"-${abs(profits[1])}" if profits[1] < 0 else "Push")
                ins_str = f" | Insurance lost (-${self.last_insurance_lost})" if self.last_insurance_lost > 0 else ""
                self.last_insurance_lost = 0
                self.result_var.set(f"Hand 1: {messages[0]} ({p1_str}) | Hand 2: {messages[1]} ({p2_str}){ins_str}")

            net_round = total_profit + ins_profit
            if hasattr(self, "engine"):
                self.engine.bankroll = self.bankroll_var.get()
            if hasattr(self, "fsm"):
                try:
                    self.fsm.transition_to(RoundPhase.ROUND_OVER, force=True)
                except Exception:
                    pass
            if hasattr(self, "event_bus") and self.event_bus:
                self.event_bus.emit(
                    GameEventType.ROUND_RESOLVED,
                    {"outcomes": outcomes, "payouts": payouts, "bankroll": self.bankroll_var.get()},
                )
            if hasattr(self, "chip_visualizer"):
                if net_round > 0:
                    self.chip_visualizer.animate_win(net_round)
                elif net_round < 0:
                    self.chip_visualizer.animate_loss()
                else:
                    self.chip_visualizer.animate_push()
            if hasattr(self, "sound_manager"):
                if net_round > 0:
                    self.sound_manager.play_payout()
                elif net_round < 0:
                    self.sound_manager.play_loss()
                else:
                    self.sound_manager.play_push()
        else:
            self.last_insurance_lost = 0
            cur_msg = self.result_var.get()
            prefix = "The clock strikes 13... The 13 of Skulls is dealt! | " if "The clock strikes 13" in cur_msg else ""
            if not is_split:
                self.result_var.set(f"{prefix}{messages[0]}")
                if hasattr(self, "sound_manager"):
                    if outcomes[0] in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
                        self.sound_manager.play_payout()
                    elif outcomes[0] in ('DEALER_WINS', 'PLAYER_BUST'):
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()
            else:
                self.result_var.set(f"Hand 1: {messages[0]} | Hand 2: {messages[1]}")
                if hasattr(self, "sound_manager"):
                    p_wins = sum(1 for o in outcomes if o in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'))
                    d_wins = sum(1 for o in outcomes if o in ('DEALER_WINS', 'PLAYER_BUST'))
                    if p_wins > d_wins:
                        self.sound_manager.play_payout()
                    elif d_wins > p_wins:
                        self.sound_manager.play_loss()
                    else:
                        self.sound_manager.play_push()

        # 3. Haunted Halloween progression & Hell's Table combat resolution
        primary_outcome = outcomes[0]
        is_double = getattr(self, "_last_was_double", False)
        self._last_was_double = False
        prev_phase = self.haunted.phase

        soul_delta, haunted_msg = self.haunted.on_round_outcome(
            primary_outcome, is_double=is_double, is_split=is_split
        )
        self._update_dealer_speech_for_outcome(primary_outcome)

        if prev_phase in (Phase.OMEN, Phase.SNUFFING):
            self._update_candles_display()
            if primary_outcome in ('DEALER_WINS', 'PLAYER_BUST', 'SURRENDER'):
                self._update_gravestones_display()
                if hasattr(self, "sound_manager"):
                    self.sound_manager.play_haunted_sound("candle_snuff")
                    self.sound_manager.play_haunted_sound("stone_scrape")
            if self.haunted.candles_remaining == 0:
                self._haunted_round_timer_id = self.root.after(800, self._trigger_hell_table)

        elif self.haunted.phase == Phase.HELL_TABLE:
            if hasattr(self, "chip_visualizer"):
                self.chip_visualizer.grid_remove()
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.grid()
                self.soul_meter_canvas.set_meter(self.haunted.soul_meter, animated=True)
            if primary_outcome in ('DEALER_WINS', 'PLAYER_BUST', 'SURRENDER'):
                self._update_gravestones_display()
                if hasattr(self, "sound_manager"):
                    self.sound_manager.play_haunted_sound("stone_scrape")

            if self.haunted.is_draft_pending:
                self._haunted_round_timer_id = self.root.after(700, self._open_angelic_draft)

        elif self.haunted.phase == Phase.VICTORY:
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.set_meter(1.0, animated=True)
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("banish")
            self._haunted_round_timer_id = self.root.after(600, self._show_victory_dialog)

        elif self.haunted.phase == Phase.DEFEAT:
            if hasattr(self, "soul_meter_canvas"):
                self.soul_meter_canvas.set_meter(0.0, animated=True)
            if hasattr(self, "sound_manager"):
                self.sound_manager.play_haunted_sound("demon_laugh")
            self.root.after(600, self._show_defeat_dialog)

        if haunted_msg:
            cur = self.result_var.get()
            if not cur.endswith(haunted_msg):
                sep = " | " if cur else ""
                self.result_var.set(f"{cur}{sep}{haunted_msg}")

        if self.chips_mode_var.get():
            self._update_bankroll_display()
            self._update_betting_controls()

        # 4. SaveManager Statistics & Gameplay Achievements Hookup
        if hasattr(self, "save_manager"):
            is_all_in = getattr(self, "_is_all_in_round", False) or (
                self.chips_mode_var.get() and len(payouts) > 0 and self.bankroll_var.get() == sum(payouts)
            )
            cur_tc = (
                self.card_counter.true_count(len(self.deck))
                if getattr(self, "card_counter", None) and hasattr(self, "deck")
                else 0.0
            )
            self._current_win_streak, self._session_blackjacks = self.save_manager.evaluate_round_achievements(
                outcomes=outcomes,
                player_hands=self.player_hands,
                dealer_hand=self.dealer_hand,
                hand_bets=self.hand_bets,
                current_bankroll=self.bankroll_var.get(),
                chips_mode=bool(self.chips_mode_var.get()),
                is_all_in=is_all_in,
                haunted_phase=self.haunted.phase,
                current_streak=getattr(self, "_current_win_streak", 0),
                session_blackjacks=getattr(self, "_session_blackjacks", 0),
                true_count=cur_tc,
            )
            self._is_all_in_round = False

        # Disable Hit/Stand/Double/Split/Surrender, enable New Game
        self._set_action_buttons_state("disabled")
        self.new_game_button.configure(state="normal")
        self._refresh_strategy_hint()

    def _update_ui_scaling(self):
        """Updates typography, button dimensions, and padding across the entire UI for the active scale factor."""
        s = self.scale_factor
        scale_ratio = 2.0 if s > 1.5 else 1.0

        # 1. Scoreboard Typography
        f_stat_title = ("Arial", int(11 * scale_ratio), "bold")
        f_stat_val = ("Arial", int(11 * scale_ratio))
        f_shoe = ("Arial", int(10 * scale_ratio), "bold")
        f_top_btn = ("Arial", int(9 * scale_ratio), "bold")
        f_bankroll = ("Arial", int(11 * scale_ratio), "bold")

        if hasattr(self, "stat_labels"):
            for lbl, is_bold in self.stat_labels:
                lbl.configure(font=f_stat_title if is_bold else f_stat_val)

        if hasattr(self, "shoe_label"):
            self.shoe_label.configure(font=f_shoe)

        for btn in (
            getattr(self, "sound_button", None),
            getattr(self, "help_button", None),
            getattr(self, "dealer_view_button", None),
            getattr(self, "scale_button", None),
            getattr(self, "fullscreen_button", None),
            getattr(self, "settings_button", None),
        ):
            if btn:
                btn.configure(font=f_top_btn)

        if hasattr(self, "bankroll_label"):
            self.bankroll_label.configure(font=f_bankroll)

        # Scale help button icon if present
        if getattr(self, "icon_loader", None) and hasattr(self, "help_button"):
            div = 1.5 if s > 1.5 else 3.0
            self.icon_question_small = self.icon_loader.get_icon("keyboard_question", scale_div=div)
            if self.icon_question_small:
                self.help_button.configure(image=self.icon_question_small)

        # 2. Hand Titles and Scores
        f_hand_title = ("Arial", int(11 * scale_ratio), "bold")
        f_hand_score = ("Arial", int(12 * scale_ratio), "bold" if s > 1.5 else "normal")
        if hasattr(self, "dealer_title_label"):
            self.dealer_title_label.configure(font=f_hand_title)
        if hasattr(self, "dealer_score_label"):
            self.dealer_score_label.configure(font=f_hand_score)
        if hasattr(self, "player_title_label"):
            self.player_title_label.configure(font=f_hand_title)
        if hasattr(self, "player_score_label"):
            self.player_score_label.configure(font=f_hand_score)

        # 3. Action Buttons & Chips Mode Toggle
        f_action_btn = ("Arial", int(10 * scale_ratio), "bold")
        action_btn_pad = int(6 * s)
        btn_pady = int(3 * s)
        action_buttons = [
            getattr(self, "hit_button", None),
            getattr(self, "stand_button", None),
            getattr(self, "double_button", None),
            getattr(self, "split_button", None),
            getattr(self, "surrender_button", None),
            getattr(self, "new_game_button", None),
            getattr(self, "miracle_button", None),
        ]
        for btn in action_buttons:
            if btn:
                btn.configure(font=f_action_btn)
                if bool(btn.grid_info()):
                    btn.grid_configure(padx=action_btn_pad, pady=btn_pady)

        if hasattr(self, "cursed_stakes_button"):
            self.cursed_stakes_button.configure(font=f_action_btn)
            if bool(self.cursed_stakes_button.grid_info()):
                self.cursed_stakes_button.grid_configure(padx=(int(6 * s), int(8 * s)), pady=btn_pady)

        # 4. Betting Buttons (when Chips Mode is on)
        f_bet_btn = ("Arial", int(9 * scale_ratio), "bold")
        f_bet_label = ("Arial", int(10 * scale_ratio), "bold")
        if hasattr(self, "bet_chips_label"):
            self.bet_chips_label.configure(font=f_bet_label)
        if hasattr(self, "chip_buttons"):
            for b in self.chip_buttons:
                b.configure(font=f_bet_btn)
                b.pack_configure(padx=int(3 * s), pady=int(2 * s))
        for b in (
            getattr(self, "all_in_button", None),
            getattr(self, "clear_bet_button", None),
            getattr(self, "deal_bet_button", None),
            getattr(self, "rebuy_button", None),
        ):
            if b:
                b.configure(font=f_bet_btn)
                b.pack_configure(padx=int(4 * s), pady=int(2 * s))

        # 5. Insurance prompt bar
        f_ins_label = ("Arial", int(10 * scale_ratio), "bold")
        f_ins_btn = ("Arial", int(9 * scale_ratio), "bold")
        if hasattr(self, "insurance_label"):
            self.insurance_label.configure(font=f_ins_label)
        if hasattr(self, "take_insurance_button"):
            self.take_insurance_button.configure(font=f_ins_btn)
        if hasattr(self, "decline_insurance_button"):
            self.decline_insurance_button.configure(font=f_ins_btn)

        # 6. Dealer Actor Elements (Phase 4)
        f_nameplate = ("Arial", int(10 * scale_ratio), "bold")
        f_speech = ("Arial", int(9 * scale_ratio), "italic")
        if hasattr(self, "dealer_nameplate_label"):
            self.dealer_nameplate_label.configure(font=f_nameplate)
        if hasattr(self, "dealer_speech_label"):
            self.dealer_speech_label.configure(
                font=f_speech,
                wraplength=int(270 * scale_ratio),
                padx=int(6 * s),
                pady=int(2 * s)
            )
        if hasattr(self, "dealer_stage_canvas"):
            self.dealer_stage_canvas.set_scale(self.scale_factor)
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_scale(self.scale_factor)
        if hasattr(self, "horizon_rail"):
            self.horizon_rail.configure(height=int(4 * s))
        if hasattr(self, "card_table_frame") and isinstance(self.card_table_frame, TableFeltCanvas):
            self.card_table_frame.set_scale(self.scale_factor)

    def toggle_scale_mode(self, event=None):
        """Toggles between 1.0x and 2.0x in-memory interface scaling."""
        new_scale = 2.0 if self.scale_factor == 1.0 else 1.0
        self.scale_factor = new_scale
        self.card_width = int(CARD_WIDTH * self.scale_factor)
        self.card_height = int(CARD_HEIGHT * self.scale_factor)
        self.card_overlap_offset = int(PLAYER_CARD_OVERLAP_OFFSET * self.scale_factor)
        target_scale = 1 if self.scale_factor == 2.0 else 2
        self.scale_status_var.set(f"🔍 {target_scale}x")

        # Re-scale card images in memory
        self._rebuild_scaled_assets(self.scale_factor)

        # Update table frames and widgets
        if hasattr(self, "card_table_frame"):
            if isinstance(self.card_table_frame, TableFeltCanvas):
                self.card_table_frame.set_scale(self.scale_factor)
            self.card_table_frame.rowconfigure(0, weight=1, minsize=int(118 * self.scale_factor))
            self.card_table_frame.rowconfigure(1, weight=1, minsize=int(118 * self.scale_factor))

        if hasattr(self, "announcement_hud"):
            self.announcement_hud.set_scale(self.scale_factor)
        if hasattr(self, "haunted_altar"):
            self.haunted_altar.set_scale(self.scale_factor, self.haunted_assets)
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.set_scale(self.scale_factor)
        if hasattr(self, "soul_meter_canvas"):
            self.soul_meter_canvas.set_scale(self.scale_factor)
        if hasattr(self, "dealer_actor"):
            self.dealer_actor.set_scale(self.scale_factor)

        # Update UI typography, button dimensions, and padding
        self._update_ui_scaling()

        # Redraw hands
        self._render_dealer_cards()
        self._render_player_cards()

        # Update ambient accessory images
        self._update_dealer_avatar()
        if hasattr(self, "pumpkin_label") and hasattr(self, "_anim_frame_toggle"):
            p_img = self.haunted_assets.get(f"pumpkin_glow_{1 if self._anim_frame_toggle else 0}")
            if p_img:
                self.pumpkin_label.configure(image=p_img)
                self.pumpkin_label.image = p_img

        # Resize window or exit fullscreen mode
        if self.is_fullscreen and self.scale_factor == 1.0:
            self.toggle_fullscreen()
        elif not self.is_fullscreen:
            try:
                screen_w = self.root.winfo_screenwidth()
                screen_h = self.root.winfo_screenheight()
                target_w = min(int(DEFAULT_WINDOW_WIDTH * self.scale_factor), max(DEFAULT_WINDOW_WIDTH, screen_w - 40))
                target_h = min(int(DEFAULT_WINDOW_HEIGHT * self.scale_factor), max(DEFAULT_WINDOW_HEIGHT, screen_h - 80))
                self.root.minsize(
                    int(MIN_WINDOW_WIDTH * (1.0 if self.scale_factor == 1.0 else 1.5)),
                    int(MIN_WINDOW_HEIGHT * (1.0 if self.scale_factor == 1.0 else 1.5))
                )
                self.root.geometry(f"{target_w}x{target_h}")
            except Exception:
                pass
        return "break"

    def _rebuild_scaled_assets(self, scale: float):
        """Re-scales all cards, card backs, and haunted assets in memory using AssetScaler."""
        w = int(CARD_WIDTH * scale)
        h = int(CARD_HEIGHT * scale)
        scaler = getattr(self, "_asset_scaler", None)
        if not scaler:
            self._asset_scaler = AssetScaler(master=self.root)
            scaler = self._asset_scaler

        # 1. Update all_cards
        new_all_cards = []
        for c in self.all_cards:
            fname = f"1_{c.suit}.png" if c.rank == "ace" else f"{c.rank}_{c.suit}.png"
            path = ASSETS_DIR / fname
            scaled_img = scaler.get_scaled_image(path, w, h)
            new_card = Card(value=c.value, image=scaled_img, rank=c.rank, suit=c.suit)
            new_all_cards.append(new_card)
        self.all_cards = new_all_cards

        # 2. Update card back
        back_path = ASSETS_DIR / "back.png"
        self.back_image = scaler.get_scaled_image(back_path, w, h)

        # 3. Update haunted assets
        if HAUNTED_ASSETS_DIR.exists():
            for p in HAUNTED_ASSETS_DIR.glob("*.png"):
                stem = p.stem
                if stem.startswith("card_") or stem == "back_haunted" or ("haunted" in stem and any(f in stem for f in ("jack", "queen", "king"))):
                    img_w, img_h = w, h
                elif "avatar" in stem or "dealer" in stem:
                    img_w, img_h = int(96 * scale), int(96 * scale)
                elif "pumpkin" in stem:
                    img_w, img_h = int(48 * scale), int(48 * scale)
                elif "gravestone" in stem:
                    img_w, img_h = int(48 * scale), int(56 * scale)
                elif "candle" in stem:
                    img_w, img_h = int(40 * scale), int(40 * scale)
                elif "relic" in stem:
                    img_w, img_h = int(48 * scale), int(48 * scale)
                else:
                    img_w, img_h = int(48 * scale), int(48 * scale)

                scaled = scaler.get_scaled_image(p, img_w, img_h)
                if scaled:
                    self.haunted_assets[stem] = scaled

        if "card_13" in self.haunted_assets:
            self.card_13 = Card(13, self.haunted_assets["card_13"], rank="thirteen", suit="skulls")

        # 4. Helper to find updated card matching rank and suit
        def find_updated_card(old_card: Card) -> Card:
            if old_card.rank == "thirteen" and self.card_13:
                return self.card_13
            for c in self.all_cards:
                if c.rank == old_card.rank and c.suit == old_card.suit:
                    return c
            return old_card

        # Update active deck and hands
        self.deck = [find_updated_card(c) for c in self.deck]
        self.dealer_hand = [find_updated_card(c) for c in self.dealer_hand]
        if self.dealer_hole_card:
            self.dealer_hole_card = find_updated_card(self.dealer_hole_card)
        self.player_hands = [[find_updated_card(c) for c in h] for h in self.player_hands]

    def toggle_fullscreen(self, event=None):
        """Toggles native Tkinter fullscreen mode and automatically upscales interface to 2x for full screens."""
        self.is_fullscreen = not self.is_fullscreen
        if self.is_fullscreen:
            try:
                self._prev_geometry = self.root.geometry()
                self._prev_scale_factor = self.scale_factor
            except Exception:
                self._prev_geometry = None
                self._prev_scale_factor = 1.0
            try:
                self.root.attributes("-fullscreen", True)
            except Exception:
                pass
            self.fullscreen_status_var.set("🗗 Window")
            # Automatically upscale to 2x if currently at 1x so cards and components fill the screen
            if self.scale_factor == 1.0:
                self.toggle_scale_mode()
        else:
            try:
                self.root.attributes("-fullscreen", False)
            except Exception:
                pass
            self.fullscreen_status_var.set("⛶ Full")
            # Restore previous scale factor if auto-upscaled upon entering fullscreen
            if getattr(self, "_prev_scale_factor", 1.0) == 1.0 and self.scale_factor == 2.0:
                self.toggle_scale_mode()
            if hasattr(self, "_prev_geometry") and self._prev_geometry:
                try:
                    self.root.geometry(self._prev_geometry)
                except Exception:
                    pass
        return "break"

    def exit_fullscreen(self, event=None):
        """Exits fullscreen mode if currently in fullscreen (Escape handler)."""
        if getattr(self, "is_fullscreen", False):
            self.toggle_fullscreen()
            return "break"

    def _on_escape_key(self, event=None):
        """Context-sensitive Escape key: closes shortcuts HUD, declines insurance, or exits fullscreen."""
        if getattr(self, "_shortcuts_dialog", None) is not None:
            self._close_shortcuts_overlay()
            return "break"
        if getattr(self, "is_insurance_phase", False) and getattr(self, "decline_insurance_button", None):
            try:
                if str(self.decline_insurance_button.cget("state")) == "normal":
                    self._on_decline_insurance()
                    return "break"
            except Exception:
                pass
        if getattr(self, "is_fullscreen", False):
            self.exit_fullscreen()
            return "break"
        return "break"

    def _record_outcome(self, outcome: str):
        """Updates win/loss/tie counters according to hand outcome."""
        if outcome in ('PLAYER_WINS', 'DEALER_BUST', 'NATURAL_BLACKJACK'):
            self.player_wins_var.set(self.player_wins_var.get() + 1)
        elif outcome in ('DEALER_WINS', 'PLAYER_BUST'):
            self.dealer_wins_var.set(self.dealer_wins_var.get() + 1)
        elif outcome == 'PUSH':
            self.ties_var.set(self.ties_var.get() + 1)

    def _set_action_buttons_state(self, state: str):
        """Helper to set the state of action buttons."""
        self.hit_button.configure(state=state)
        self.stand_button.configure(state=state)
        if state == "disabled":
            if hasattr(self, "double_button"):
                self.double_button.configure(state="disabled")
            if hasattr(self, "split_button"):
                self.split_button.configure(state="disabled")
            if hasattr(self, "surrender_button"):
                self.surrender_button.configure(state="disabled")

    def _cancel_all_active_timers(self):
        """Safely cancels all registered background and animation timers across subsystems."""
        self._cancel_blink_timers()
        for attr in (
            "_dealer_idle_timer_id",
            "_dealer_blink_timer_id",
            "_dealer_blink_restore_timer_id",
            "_dealer_gesture_timer_id",
            "_dealer_mouth_timer_id",
            "_dealer_speech_anim_timer_id",
            "_typewriter_timer_id",
            "_haunted_round_timer_id",
            "_ambient_timer_id",
            "_dealer_timer_id",
        ):
            timer_id = getattr(self, attr, None)
            if timer_id:
                try:
                    self.root.after_cancel(timer_id)
                except Exception:
                    pass
                setattr(self, attr, None)

    def _on_root_destroyed(self, event):
        """Emergency callback invoked when root is destroyed directly without _on_close."""
        if getattr(event, "widget", None) == self.root:
            self._cancel_all_active_timers()

    def _on_close(self):
        """Safely cleans up any pending timer callback before window destruction."""
        self._close_shortcuts_overlay()
        self._close_settings_dialog()
        self._close_wardrobe_dialog()
        self._cancel_all_active_timers()
        if hasattr(self, "chip_visualizer"):
            self.chip_visualizer.clear_timers()
        if hasattr(self, "soul_meter_canvas"):
            self.soul_meter_canvas._cancel_timer()
        if hasattr(self, "haunted_altar"):
            self.haunted_altar.cancel_animations()
        if hasattr(self, "sound_manager"):
            self.sound_manager.stop_all()
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except tkinter.TclError:
            pass


# ============================================================================
# Entry Point
# ============================================================================

def play_game():
    """
    Main entry point to initialize and launch the Blackjack GUI.
    Preserved as a top-level function for backward compatibility with import_test.py.
    """
    root = tkinter.Tk()
    BlackjackApp(root)
    root.mainloop()


if __name__ == "__main__":
    play_game()
