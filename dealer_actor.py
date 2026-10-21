"""
DealerActor Layered Sprite Compositor and Character Roster.

Provides:
- CharacterProfile metadata for Julian, Malphas, Uriel, and Mortimer.
- Dynamic alpha-compositing across 5 sprite strata:
  1. Torso (suit / mantle / robes)
  2. Head (facial structure / hair / horns / halo / top hat)
  3. Eyes (open / half-lidded / closed)
  4. Mouth (neutral / talk / smirk / gasp)
  5. Arms (rested / deal sweep / hole-card peek)
- In-memory PhotoImage caching for high-framerate rendering (25-30 FPS).
- High-DPI 1x <-> 2x display scaling.
- Costume switching with backwards-compatible alias normalization.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from PIL import Image, ImageTk

BASE_DIR = Path(__file__).resolve().parent
HAUNTED_ASSETS_DIR = BASE_DIR / "assets" / "haunted"
CHARACTERS_DIR = HAUNTED_ASSETS_DIR / "characters"


@dataclass(frozen=True)
class CharacterProfile:
    id: str
    name: str
    title: str
    theme: str
    nameplate_fg: str
    speech_bg: str
    audio_cue: str
    unlock_key: str
    lore: str
    is_puppet: bool = False


CHARACTERS: Dict[str, CharacterProfile] = {
    "julian": CharacterProfile(
        id="julian",
        name="Julian",
        title="The Classic Croupier",
        theme="casino",
        nameplate_fg="#ffd700",
        speech_bg="#141014",
        audio_cue="dealer_julian.ogg",
        unlock_key="classic",
        lore="Consummate casino gentleman who deals cards with effortless elegance and calm composure.",
        is_puppet=False,
    ),
    "malphas": CharacterProfile(
        id="malphas",
        name="Malphas",
        title="☠ The Pit Fiend",
        theme="hell",
        nameplate_fg="#ff1744",
        speech_bg="#140508",
        audio_cue="dealer_malphas.ogg",
        unlock_key="pit_fiend",
        lore="Menacing archfiend whose molten ram horns and smoldering embers crave mortal soul fragments.",
        is_puppet=False,
    ),
    "uriel": CharacterProfile(
        id="uriel",
        name="Uriel",
        title="✨ Celestial Seraph",
        theme="celestial",
        nameplate_fg="#00e5ff",
        speech_bg="#0d2b26",
        audio_cue="dealer_uriel.ogg",
        unlock_key="seraph",
        lore="Radiant heavenly messenger whose luminous halo and divine vestments banish ancient infernal curses.",
        is_puppet=False,
    ),
    "mortimer": CharacterProfile(
        id="mortimer",
        name="Mortimer",
        title="🎩 Grim Bones",
        theme="crypt",
        nameplate_fg="#ce93d8",
        speech_bg="#1a0924",
        audio_cue="dealer_mortimer.ogg",
        unlock_key="grim_bones",
        lore="Dapper skeleton croupier sporting a purple silk top hat who dryly chuckles at the roll of the bones.",
        is_puppet=False,
    ),
    "tiffany": CharacterProfile(
        id="tiffany",
        name="Tiffany",
        title="♥ The Velvet Croupier",
        theme="casino",
        nameplate_fg="#ff4081",
        speech_bg="#240a1b",
        audio_cue="dealer_tiffany.ogg",
        unlock_key="tiffany",
        lore="Glamorous and quick-witted croupier whose velvet touch and radiant smile charm even the sharpest card counters.",
        is_puppet=True,
    ),
    "dummy": CharacterProfile(
        id="dummy",
        name="Puppet Dummy",
        title="🧪 Test Puppet Dummy",
        theme="casino",
        nameplate_fg="#00e5ff",
        speech_bg="#0a1520",
        audio_cue="dealer_julian.ogg",
        unlock_key="dummy_test",
        lore="High-contrast multi-layer dummy puppet rigged to verify layer stacking, Z-order, and articulation.",
        is_puppet=True,
    ),
}

COSTUME_ALIASES: Dict[str, str] = {
    "classic": "julian",
    "dealer": "julian",
    "tiffany": "tiffany",
    "velvet": "tiffany",
    "pit_fiend": "malphas",
    "demon": "malphas",
    "hell": "malphas",
    "seraph": "uriel",
    "angel": "uriel",
    "celestial": "uriel",
    "grim_bones": "mortimer",
    "skeleton": "mortimer",
    "bones": "mortimer",
    "crypt": "mortimer",
    "dummy": "dummy",
    "puppet": "dummy",
    "test": "dummy",
}

VISEME_STATES = ("neutral", "talk", "a", "o", "e", "f", "smirk", "gasp")


def map_char_to_viseme(char: str) -> str:
    """
    Maps an individual character to its corresponding mouth viseme shape:
    - Rounded vowels ('o', 'u', 'w', 'q') -> 'o'
    - Open vowels ('a', 'i', 'y', 'h') -> 'a'
    - Wide dental / palatal consonants & vowels ('e', 'c', 'd', 'g', 'j', 'k', 'l', 'n', 'r', 's', 't', 'z') -> 'e'
    - Labiodental fricatives ('f', 'v') -> 'f'
    - Bilabials ('m', 'b', 'p'), whitespace, and punctuation -> 'neutral'
    - Fallback -> 'talk'
    """
    if not char:
        return "neutral"
    c = char.lower()
    if c in (" ", "\t", "\n", ".", ",", "!", "?", "-", "—", ";", ":", "'", '"', "(", ")", "m", "b", "p"):
        return "neutral"
    if c in ("o", "u", "w", "q"):
        return "o"
    if c in ("a", "i", "y", "h"):
        return "a"
    if c in ("e", "c", "d", "g", "j", "k", "l", "n", "r", "s", "t", "z"):
        return "e"
    if c in ("f", "v"):
        return "f"
    return "talk"


class DealerActor:
    """
    Dynamic 5-layer sprite compositor for the live dealer actor.
    Handles asset caching, layer state assembly, Tkinter PhotoImage caching,
    and responsive 1x / 2x coordinate scaling.
    """

    def __init__(
        self,
        master: Any,
        characters_dir: Optional[Path] = None,
        scale_factor: float = 1.0,
        initial_character: str = "julian",
    ):
        self.master = master
        self.characters_dir = characters_dir or CHARACTERS_DIR
        self.scale_factor = scale_factor

        self.current_character = self._resolve_character_id(initial_character)
        self.eye_state = "open"
        self.mouth_state = "neutral"
        self.arm_state = "rest"

        # Asset and composite caches
        self._raw_layers_cache: Dict[str, Image.Image] = {}
        self._cached_composite_pil: Optional[Image.Image] = None
        self._cached_composite_photo: Optional[ImageTk.PhotoImage] = None

    @staticmethod
    def _resolve_character_id(char_id: str) -> str:
        cid = (char_id or "").lower().strip()
        if cid in CHARACTERS:
            return cid
        return COSTUME_ALIASES.get(cid, "julian")

    def equip_costume(self, character_id: str) -> None:
        """Swaps active character persona. Guarantees game state immutability."""
        resolved = self._resolve_character_id(character_id)
        if resolved != self.current_character:
            self.current_character = resolved
            self._invalidate_composite()

    def set_eye_state(self, state: str) -> None:
        """Sets eye layer: 'open', 'half', or 'closed'."""
        if state not in ("open", "half", "closed"):
            state = "open"
        if self.eye_state != state:
            self.eye_state = state
            self._invalidate_composite()

    def set_mouth_state(self, state: str) -> None:
        """Sets mouth layer: 'neutral', 'talk', 'a', 'o', 'e', 'f', 'smirk', or 'gasp'."""
        if state not in VISEME_STATES:
            state = "neutral"
        if self.mouth_state != state:
            self.mouth_state = state
            self._invalidate_composite()

    def set_mouth_for_char(self, char: str) -> str:
        """Derives phonetic viseme mouth shape from typed character and updates mouth state."""
        viseme = map_char_to_viseme(char)
        profile = self.get_profile()
        if not profile.is_puppet:
            state = "neutral" if viseme == "neutral" else "talk"
        else:
            state = viseme
        self.set_mouth_state(state)
        return state

    def set_arm_state(self, state: str) -> None:
        """Sets arm layer: 'rest', 'deal', or 'peek'."""
        if state not in ("rest", "deal", "peek"):
            state = "rest"
        if self.arm_state != state:
            self.arm_state = state
            self._invalidate_composite()

    def set_scale(self, scale_factor: float) -> None:
        """Updates scale factor (1.0 vs 2.0) and clears cached images."""
        if self.scale_factor != scale_factor:
            self.scale_factor = scale_factor
            self._raw_layers_cache.clear()
            if hasattr(self, "_bust_photo_cache"):
                self._bust_photo_cache.clear()
            self._invalidate_composite()

    def _invalidate_composite(self) -> None:
        self._cached_composite_pil = None
        self._cached_composite_photo = None

    def get_profile(self, character_id: Optional[str] = None) -> CharacterProfile:
        """Returns the CharacterProfile for the current (or specified) character."""
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        return CHARACTERS.get(cid, CHARACTERS["julian"])

    def get_layer_image(self, layer_name: str) -> Optional[Image.Image]:
        """Public accessor for discrete layer images."""
        return self._get_layer_image(layer_name)

    def _get_layer_image(self, layer_name: str) -> Optional[Image.Image]:
        suffix = "_2x" if self.scale_factor > 1.5 else ""
        cache_key = f"{self.current_character}_{layer_name}{suffix}"
        if cache_key in self._raw_layers_cache:
            return self._raw_layers_cache[cache_key]

        char_dir = self.characters_dir / self.current_character
        file_path = char_dir / f"{layer_name}{suffix}.png"
        if not file_path.exists():
            # Fallback to 1x file if 2x not found
            file_path = char_dir / f"{layer_name}.png"

        # Viseme graceful degradation fallback for characters without phonetic visemes
        if not file_path.exists() and layer_name.startswith("mouth_") and layer_name not in ("mouth_talk", "mouth_neutral"):
            fallback_path = char_dir / f"mouth_talk{suffix}.png"
            if not fallback_path.exists():
                fallback_path = char_dir / "mouth_talk.png"
            if fallback_path.exists():
                file_path = fallback_path
            else:
                fallback_neutral = char_dir / f"mouth_neutral{suffix}.png"
                if not fallback_neutral.exists():
                    fallback_neutral = char_dir / "mouth_neutral.png"
                if fallback_neutral.exists():
                    file_path = fallback_neutral

        if file_path.exists():
            try:
                img = Image.open(file_path).convert("RGBA")
                self._raw_layers_cache[cache_key] = img
                return img
            except Exception:
                return None
        return None

    def get_composite_image(self) -> Image.Image:
        """Assembles active sprite strata according to character profile (puppet vs legacy)."""
        if self._cached_composite_pil is not None:
            return self._cached_composite_pil

        # Determine canvas size
        target_size = (224, 224) if self.scale_factor > 1.5 else (112, 112)
        composite = Image.new("RGBA", target_size, (0, 0, 0, 0))

        profile = self.get_profile()
        if profile.is_puppet:
            # Full discrete 7-layer puppet strata:
            # Shadow -> Neck -> Torso -> Head -> Eyes -> Mouth -> Arms
            layer_names = [
                "shadow",
                "neck",
                "torso",
                "head",
                f"eyes_{self.eye_state}",
                f"mouth_{self.mouth_state}",
                f"arm_{self.arm_state}",
            ]
        else:
            # Ordered legacy strata: Head already contains open eyes and neutral mouth.
            # Only overlay expressive morph targets (e.g. blink or talk) to prevent
            # double-blended feathered edge artifacts/banding on the face.
            layer_names = ["torso", "head"]
            if self.eye_state != "open":
                layer_names.append(f"eyes_{self.eye_state}")
            if self.mouth_state != "neutral":
                layer_names.append(f"mouth_{self.mouth_state}")
            layer_names.append(f"arm_{self.arm_state}")

        for lname in layer_names:
            l_img = self._get_layer_image(lname)
            if l_img is not None:
                if l_img.size != target_size:
                    resample = getattr(Image, "Resampling", Image).BILINEAR
                    l_img = l_img.resize(target_size, resample)
                composite.alpha_composite(l_img)

        self._cached_composite_pil = composite
        return composite

    def get_photo_image(self) -> Optional[ImageTk.PhotoImage]:
        """Returns a cached Tkinter PhotoImage for fast canvas or label rendering."""
        if self._cached_composite_photo is not None:
            return self._cached_composite_photo

        pil_img = self.get_composite_image()
        try:
            self._cached_composite_photo = ImageTk.PhotoImage(pil_img, master=self.master)
            return self._cached_composite_photo
        except Exception:
            return None

    def get_bust_image(self, character_id: Optional[str] = None, scale_factor: Optional[float] = None) -> Optional[Image.Image]:
        """Returns the pre-rendered bust portrait for a character (e.g. for wardrobe cards)."""
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        s = scale_factor if scale_factor is not None else self.scale_factor
        suffix = "_2x" if s > 1.5 else ""
        path = self.characters_dir / cid / f"bust{suffix}.png"
        if not path.exists():
            path = self.characters_dir / cid / "bust.png"
        if path.exists():
            try:
                return Image.open(path).convert("RGBA")
            except Exception:
                return None
        return None

    def get_bust_photo_image(self, character_id: Optional[str] = None, scale_factor: Optional[float] = None) -> Optional[ImageTk.PhotoImage]:
        """Returns a cached Tkinter PhotoImage bust for dialog portraits or UI cards."""
        pil_img = self.get_bust_image(character_id, scale_factor)
        if pil_img is None:
            return None
        if not hasattr(self, "_bust_photo_cache"):
            self._bust_photo_cache = {}
        cid = self._resolve_character_id(character_id) if character_id else self.current_character
        s = scale_factor if scale_factor is not None else self.scale_factor
        cache_key = f"{cid}_{s}"
        if cache_key in self._bust_photo_cache:
            return self._bust_photo_cache[cache_key]
        try:
            photo = ImageTk.PhotoImage(pil_img, master=self.master)
            self._bust_photo_cache[cache_key] = photo
            return photo
        except Exception:
            return None

