"""
Audio Playback, High-DPI Image Scaling, and Sprite Loading Infrastructure.

Encapsulates:
- SoundManager: 16-channel low-latency polyphonic audio playback via pygame.mixer,
  with randomized sample pools and graceful headless fallback.
- AssetScaler: Dynamic in-memory image scaling using Pillow (LANCZOS/BILINEAR)
  for High-DPI 1x <-> 2x modes with zero disk duplication.
- KeyboardIconLoader: Caches and subsamples Kenney keyboard and mouse UI prompt icons.
- load_images(): Standard 52-card image loader for Card instances.
"""

from __future__ import annotations

import os
import random
import sys
import tkinter
from pathlib import Path
from typing import Any, Optional

from config import (
    ASSETS_DIR,
    AUDIO_DIR,
    BASE_DIR,
    CARD_HEIGHT,
    CARD_WIDTH,
    DEFAULT_SOUND_VOLUME,
    HAUNTED_AUDIO_DIR,
    OVERLAY_ICONS_DIR,
)
from rules import Card
from dialogue_voice_engine import AnimaleseVoiceEngine

# Silence pygame greeting message on import to ensure clean stdout in CLI pipelines
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Optional pygame.mixer support for authentic tactile casino audio
try:
    # pyrefly: ignore [missing-import]
    from pygame import mixer as pygame_mixer
    PYGAME_AVAILABLE = True
except (ImportError, Exception):
    pygame_mixer = None
    PYGAME_AVAILABLE = False

# Optional Pillow support for dynamic in-memory High-DPI scaling
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except (ImportError, Exception):
    Image = None
    ImageTk = None
    ImageDraw = None
    ImageFont = None
    PIL_AVAILABLE = False


# ============================================================================
# Asset Scaler (Pillow Dynamic In-Memory Resizing)
# ============================================================================

class AssetScaler:
    """
    Manages in-memory dynamic image scaling using Pillow (PIL) for cards,
    table accessories, character avatars, and relics across 1x and 2x display modes.
    Zero disk duplication.
    """
    def __init__(self, master=None):
        self.master = master
        self._source_pil_cache: dict[Path, Image.Image] = {}
        self._tk_cache: dict[tuple[Path, int, int], ImageTk.PhotoImage] = {}

    def get_scaled_image(self, file_path: Path, width: int, height: int):
        """Returns a scaled PhotoImage (or ImageTk.PhotoImage) resized in memory."""
        file_path = Path(file_path)
        if not PIL_AVAILABLE or Image is None or ImageTk is None:
            kw = {"master": self.master} if self.master is not None else {}
            try:
                return tkinter.PhotoImage(file=str(file_path), **kw)
            except Exception:
                return None

        key = (file_path, width, height)
        if key in self._tk_cache:
            return self._tk_cache[key]

        if file_path not in self._source_pil_cache:
            if not file_path.exists():
                return None
            try:
                self._source_pil_cache[file_path] = Image.open(file_path).convert("RGBA")
            except Exception:
                return None

        src = self._source_pil_cache[file_path]
        resized = src.resize((width, height), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(resized, master=self.master)
        self._tk_cache[key] = tk_img
        return tk_img


def load_images(card_images, master=None, scale: float = 1.0, asset_scaler: AssetScaler | None = None):
    """
    Loads all 52 card PNG images into a list of Card instances.
    Supports in-memory scaling when scale != 1.0 or asset_scaler is provided.
    Preserved for backward compatibility with test suites and external callers.
    """
    suits = ["heart", "club", "diamond", "spade"]
    face_cards = ["jack", "queen", "king"]
    use_scaler = (asset_scaler is not None) or (scale != 1.0)
    scaler = (asset_scaler or AssetScaler(master=master)) if use_scaler else None
    w = int(CARD_WIDTH * scale)
    h = int(CARD_HEIGHT * scale)

    for suit in suits:
        # Number cards 1 to 10 (1 = Ace)
        for card in range(1, 11):
            name = ASSETS_DIR / f"{card}_{suit}.png"
            if scaler:
                image = scaler.get_scaled_image(name, w, h)
            else:
                image = tkinter.PhotoImage(file=str(name), master=master)
            rank = "ace" if card == 1 else str(card)
            card_images.append(Card(value=card, image=image, rank=rank, suit=suit))

        # Face cards (Jack, Queen, King all value 10)
        for card in face_cards:
            name = ASSETS_DIR / f"{card}_{suit}.png"
            if scaler:
                image = scaler.get_scaled_image(name, w, h)
            else:
                image = tkinter.PhotoImage(file=str(name), master=master)
            card_images.append(Card(value=10, image=image, rank=card, suit=suit))


# ============================================================================
# Audio System: Pygame Mixer Sound Manager
# ============================================================================

class SoundManager:
    """
    Manages sound effects playback using pygame.mixer for .ogg audio assets.

    Features:
    - Low-latency asynchronous audio playback via pygame.mixer buffer configuration.
    - Polyphonic 16-channel mixing so cards and chips sound concurrently without clipping.
    - Natural acoustic variety through randomized sample pools (e.g. 8 card slides, 6 chip sounds).
    - Graceful headless degradation: silently no-ops if pygame is missing or audio hardware is absent.
    - Master volume control and mute toggling with Tkinter reactive updates.
    """

    def __init__(self, audio_dir: Path = AUDIO_DIR, enabled: bool = True, volume: float = DEFAULT_SOUND_VOLUME):
        self.audio_dir = Path(audio_dir)
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.is_available = False
        self.sounds: dict[str, list] = {
            "card_slide": [],
            "card_place": [],
            "card_shove": [],
            "card_shuffle": [],
            "card_fan": [],
            "cards_pack": [],
            "chip_lay": [],
            "chips_collide": [],
            "chips_stack": [],
            "chips_handle": [],
        }

        self.voice_engine = AnimaleseVoiceEngine(enabled=self.enabled, volume=self.volume)

        self._init_mixer()
        if self.is_available:
            self._load_sounds()

    def _init_mixer(self):
        """Initializes pygame.mixer safely with low latency and 16 channels."""
        if not PYGAME_AVAILABLE or pygame_mixer is None:
            self.is_available = False
            return
        try:
            if not pygame_mixer.get_init():
                pygame_mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame_mixer.set_num_channels(16)
            self.is_available = True
        except Exception:
            # Handles headless CI environments or missing sound card
            self.is_available = False

    def _load_sounds(self):
        """Pre-loads all .ogg sound files from audio_dir into categorized pools."""
        if not self.audio_dir.exists() or pygame_mixer is None:
            return

        patterns = {
            "card_slide": "card-slide-*.ogg",
            "card_place": "card-place-*.ogg",
            "card_shove": "card-shove-*.ogg",
            "card_shuffle": "card-shuffle.ogg",
            "card_fan": "card-fan-*.ogg",
            "cards_pack": "cards-pack-*.ogg",
            "chip_lay": "chip-lay-*.ogg",
            "chips_collide": "chips-collide-*.ogg",
            "chips_stack": "chips-stack-*.ogg",
            "chips_handle": "chips-handle-*.ogg",
        }

        for category, pattern in patterns.items():
            for file_path in sorted(self.audio_dir.glob(pattern)):
                try:
                    sound = pygame_mixer.Sound(str(file_path))
                    sound.set_volume(self.volume)
                    self.sounds[category].append(sound)
                except Exception:
                    pass

    def set_volume(self, volume: float):
        """Sets master volume (0.0 to 1.0) and updates all loaded sounds."""
        self.volume = max(0.0, min(1.0, volume))
        for sound_list in self.sounds.values():
            for sound in sound_list:
                try:
                    sound.set_volume(self.volume)
                except Exception:
                    pass
        if hasattr(self, "voice_engine") and self.voice_engine:
            self.voice_engine.set_volume(self.volume)

    def toggle_mute(self) -> bool:
        """Toggles mute state. Returns True if sound is now enabled, False if muted."""
        self.enabled = not self.enabled
        if hasattr(self, "voice_engine") and self.voice_engine:
            self.voice_engine.enabled = self.enabled
        return self.enabled

    def play_dialogue_blip(
        self,
        character_id: str,
        char: str,
        char_index: int = 0,
        inflection: str = "normal",
    ) -> bool:
        """Plays character-specific procedural Animalese voice blip for typewriter speech."""
        if not self.enabled or not self.is_available:
            return False
        if hasattr(self, "voice_engine") and self.voice_engine:
            return self.voice_engine.play_speech_blip(
                character_id=character_id,
                char=char,
                char_index=char_index,
                inflection=inflection,
            )
        return False

    @property
    def is_muted(self) -> bool:
        """Returns whether sound output is currently muted or unavailable."""
        return (not self.enabled) or (not self.is_available)

    def stop_all(self):
        """Stops all currently playing audio channels."""
        if self.is_available and pygame_mixer is not None:
            try:
                pygame_mixer.stop()
            except Exception:
                pass

    def play(self, category: str):
        """Plays a random sound from the specified category if sound is enabled."""
        if not self.enabled or not self.is_available:
            return
        sound_pool = self.sounds.get(category)
        if not sound_pool:
            return
        try:
            sound = random.choice(sound_pool)
            sound.play()
        except Exception:
            pass

    # Convenience domain event playback methods
    def play_card_deal(self):
        """Plays random card slide sound when dealing cards."""
        self.play("card_slide")

    def play_card_place(self):
        """Plays crisp card placement sound (e.g. flipping hole card or split)."""
        self.play("card_place")

    def play_card_shuffle(self):
        """Plays riffle shuffle sound when resetting or cutting shoe."""
        self.play("card_shuffle")

    def play_card_fan(self):
        """Plays card fanning sound."""
        self.play("card_fan")

    def play_chip_add(self):
        """Plays chip click or lay sound when placing/increasing bets."""
        cat = random.choice(["chip_lay", "chips_collide"])
        self.play(cat)

    def play_chip_stack(self):
        """Plays heavy chip stack sound for all-in or large bets."""
        self.play("chips_stack")

    def play_chip_clear(self):
        """Plays dealer chip handling sound when clearing bets."""
        self.play("chips_handle")

    def play_surrender(self):
        """Plays card shove sound when player surrenders their hand."""
        self.play("card_shove")

    def play_payout(self):
        """Plays dealer chip slide / handle sound on player win."""
        self.play("chips_handle")

    def play_loss(self):
        """Plays dealer scooping chips sound on player loss/bust."""
        self.play("chips_handle")

    def play_push(self):
        """Plays soft chip tap on push."""
        self.play("chip_lay")

    def play_haunted_sound(self, sound_name: str):
        """Plays a one-shot haunted audio effect from audio/haunted/ with extension safety."""
        if not self.enabled or not self.is_available:
            return
        clean_name = sound_name[:-4] if sound_name.endswith((".ogg", ".wav")) else sound_name
        sound_path = HAUNTED_AUDIO_DIR / f"{clean_name}.ogg"
        if not sound_path.exists():
            sound_path = HAUNTED_AUDIO_DIR / f"{clean_name}.wav"
        if sound_path.exists() and pygame_mixer is not None:
            try:
                sound = pygame_mixer.Sound(str(sound_path))
                sound.set_volume(self.volume)
                sound.play()
            except Exception:
                pass


# ============================================================================
# Keyboard & Input Prompts Asset Loader
# ============================================================================

class KeyboardIconLoader:
    """
    Loads, scales, and caches Kenney keyboard & mouse prompt PNG sprites.
    Provides graceful fallback to text-based badges if assets are missing.
    """

    def __init__(self, icons_dir: Path | None = None, master: tkinter.Misc | None = None):
        self.icons_dir = icons_dir or OVERLAY_ICONS_DIR
        self.master = master
        self._cache: dict[tuple[str, int], tkinter.PhotoImage] = {}

    def get_icon(self, icon_name: str, scale_div: int = 2) -> tkinter.PhotoImage | None:
        """
        Retrieves a cached PhotoImage for the given icon name and scale divisor.
        Example: get_icon('keyboard_space', 2) loads keyboard_space.png subsampled by (2, 2) -> 32x32.
        """
        key = (icon_name, scale_div)
        if key in self._cache:
            return self._cache[key]

        candidates = []
        if self.icons_dir:
            candidates.append(self.icons_dir / f"{icon_name}.png")
            if not icon_name.startswith("keyboard_") and not icon_name.startswith("mouse_"):
                candidates.append(self.icons_dir / f"keyboard_{icon_name}.png")

        # Local development fallback to raw Kenney pack if curated dir not yet populated
        raw_fallback = BASE_DIR / "Keyboard & Mouse" / "Default"
        candidates.append(raw_fallback / f"{icon_name}.png")
        if not icon_name.startswith("keyboard_") and not icon_name.startswith("mouse_"):
            candidates.append(raw_fallback / f"keyboard_{icon_name}.png")

        kw = {"master": self.master} if self.master is not None else {}
        for path in candidates:
            if path.exists():
                try:
                    img = tkinter.PhotoImage(file=str(path), **kw)
                    if scale_div > 1:
                        img = img.subsample(scale_div, scale_div)
                    self._cache[key] = img
                    return img
                except Exception:
                    continue

        return None
