"""
Procedural Animalese Dialogue Voice Engine for Dealer Actors.

Generates lightweight, high-fidelity PCM WAV audio buffers dynamically in memory
using Python's standard wave, math, and struct libraries.
Pre-caches sound objects directly into pygame.mixer.Sound with zero disk overhead.

Architecture Principles:
- 1:1 Viseme-to-Sound Consistency: Each viseme ('a', 'o', 'e', 'f', 'talk', 'smirk', 'gasp')
  is deterministically bound to a consistent, signature acoustic syllable per character.
  Letters mapping to the same viseme produce identical phoneme sounds.
- Character-Specific Registers: Character profiles define unique fundamental frequencies
  (e.g. Malphas 85 Hz bass growl vs Uriel 520 Hz celestial bell chime) and acoustic timbres.
- Dynamic Inflection: Sentence-ending punctuation applies deterministic pitch sweeps
  ('?' rising lilt, '.' falling cadence, '!' accented emphasis).
- Graceful Headless Fallback: Safe execution in environments lacking audio hardware or pygame.
"""

from __future__ import annotations

import io
import math
import os
import re
import struct
import time
import wave
from typing import Any, Dict, List, Optional, Tuple

# Silence pygame greeting message on import to ensure clean stdout in CLI pipelines
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Optional pygame.mixer support
try:
    from pygame import mixer as pygame_mixer
    PYGAME_AVAILABLE = True
except (ImportError, Exception):
    pygame_mixer = None
    PYGAME_AVAILABLE = False


# ============================================================================
# Voice Profile Registry
# ============================================================================

VOICE_PROFILES: Dict[str, Dict[str, Any]] = {
    "tiffany": {
        "base_freq": 380.0,
        "timbre": "warm_flute",
        "description": "Bright, warm, charming alto with gentle harmonic overtones.",
    },
    "julian": {
        "base_freq": 180.0,
        "timbre": "classic_baritone",
        "description": "Smooth, refined baritone with balanced, crisp casino diction.",
    },
    "malphas": {
        "base_freq": 85.0,
        "timbre": "guttural_brimstone",
        "description": "Deep, resonant infernal bass with low-frequency rumble and grit.",
    },
    "uriel": {
        "base_freq": 520.0,
        "timbre": "angelic_crystal",
        "description": "Luminous, crystalline soprano with bell-like acoustic purity.",
    },
    "mortimer": {
        "base_freq": 240.0,
        "timbre": "crypt_hollow",
        "description": "Eerie, hollow, spectral timbre with odd-harmonic wooden resonance.",
    },
    "dummy": {
        "base_freq": 300.0,
        "timbre": "synthetic_square",
        "description": "Clean, retro algorithmic square-wave test tone.",
    },
    "selene": {
        "base_freq": 440.0,
        "timbre": "cyber_synth",
        "description": "Futuristic vocoded synthesizer chime with metallic edge.",
    },
    "vladimir": {
        "base_freq": 140.0,
        "timbre": "crimson_velvet",
        "description": "Aristocratic, dark, brooding cello-like baritone.",
    },
    "professor": {
        "base_freq": 160.0,
        "timbre": "classic_baritone",
        "description": "Warm, articulate academic baritone with crisp lecture cadence.",
    },
}

SUPPORTED_VISEMES = ("a", "o", "e", "f", "talk", "smirk", "gasp", "neutral")


# ============================================================================
# Procedural Waveform Synthesis (In-Memory RIFF/WAVE PCM)
# ============================================================================

def synthesize_viseme_pcm(
    base_freq: float,
    viseme: str,
    timbre: str = "warm_flute",
    duration_ms: int = 45,
    sample_rate: int = 44100,
    inflection: str = "normal",
) -> bytes:
    """
    Synthesizes a 16-bit mono PCM WAV audio buffer for a specific mouth viseme.
    100% deterministic: identical parameters generate identical byte sequences.

    Returns:
        bytes: Complete RIFF/WAVE formatted byte buffer, or b"" for 'neutral' silence.
    """
    if viseme == "neutral":
        return b""

    num_samples = int(sample_rate * (duration_ms / 1000.0))
    if num_samples <= 0:
        return b""

    # Base frequency ratio based on phonetic viseme formant
    viseme_ratios = {
        "a": 1.0,         # Open vowel formant
        "o": 0.82,        # Rounded deep vowel formant
        "e": 1.18,        # Wide dental / bright vowel formant
        "f": 1.45,        # High-frequency fricative
        "talk": 1.05,     # Crisp generic consonant tap
        "smirk": 1.12,    # Playful micro-lilt
        "gasp": 1.30,     # Quick aspirated intake
    }
    freq_multiplier = viseme_ratios.get(viseme, 1.0)
    center_freq = base_freq * freq_multiplier

    samples: list[int] = []

    for i in range(num_samples):
        progress = i / float(num_samples)

        # Dynamic inflection pitch shift
        current_freq = center_freq
        if inflection == "question":
            # Pitch rises +18% toward the tail of the syllable
            current_freq *= 1.0 + (0.18 * progress)
        elif inflection == "period":
            # Pitch falls -12% toward the tail of the syllable
            current_freq *= 1.0 - (0.12 * progress)
        elif inflection in ("exclamation", "exclaim"):
            # Rising +20% pitch emphasis toward the tail of the exclaimed syllable
            current_freq *= 1.0 + (0.20 * progress)

        # Special viseme glide mechanics
        if viseme == "smirk":
            current_freq *= 1.0 + (0.25 * (progress ** 1.5))
        elif viseme == "gasp":
            current_freq *= 1.35 - (0.35 * (progress ** 0.5))

        # Phase accumulation: 2 * pi * f * t
        t = i / float(sample_rate)
        phi = 2.0 * math.pi * current_freq * t

        # Waveform generation based on character timbre and viseme shape
        val = 0.0
        if timbre == "warm_flute":
            val = math.sin(phi) + 0.35 * math.sin(2.0 * phi) + 0.12 * math.sin(3.0 * phi)
        elif timbre == "classic_baritone":
            val = math.sin(phi) + 0.45 * math.sin(2.0 * phi) + 0.25 * math.sin(3.0 * phi) + 0.10 * math.sin(4.0 * phi)
        elif timbre == "guttural_brimstone":
            # Sub-octave + odd harmonics for demonic growl
            val = 0.6 * math.sin(0.5 * phi) + 0.7 * math.sin(phi) + 0.4 * math.sin(3.0 * phi) + 0.2 * math.sin(5.0 * phi)
        elif timbre == "angelic_crystal":
            # Octave overtone shimmer
            val = 0.8 * math.sin(phi) + 0.5 * math.sin(2.0 * phi) + 0.3 * math.sin(4.0 * phi)
        elif timbre == "crypt_hollow":
            # Hollow square-like odd harmonics
            val = math.sin(phi) + 0.33 * math.sin(3.0 * phi) + 0.20 * math.sin(5.0 * phi)
        elif timbre == "synthetic_square":
            val = 1.0 if math.sin(phi) >= 0.0 else -1.0
        elif timbre == "cyber_synth":
            val = math.sin(phi) + 0.5 * math.sin(2.0 * phi) + 0.3 * math.cos(3.5 * phi)
        elif timbre == "crimson_velvet":
            val = math.sin(phi) + 0.5 * math.sin(1.5 * phi) + 0.25 * math.sin(2.5 * phi)
        else:
            val = math.sin(phi)

        # Viseme acoustic modifications
        if viseme == "f":
            # Fricative breath wash (high-frequency deterministic pseudo-noise)
            noise = math.sin(phi * 7.1) * 0.4 + math.sin(phi * 13.3) * 0.3 + math.sin(phi * 19.7) * 0.2
            val = 0.3 * val + 0.7 * noise
        elif viseme == "talk":
            # Snappy consonant impulse (percussive decay)
            percussion_env = math.exp(-4.5 * progress)
            val = val * (0.4 + 0.6 * percussion_env)

        # ADSR Amplitude Envelope (prevents acoustic clicking at window boundaries)
        # 10% attack, 60% sustain, 30% cosine decay release
        if progress < 0.10:
            env = progress / 0.10
        elif progress < 0.70:
            env = 1.0
        else:
            rel_prog = (progress - 0.70) / 0.30
            env = 0.5 * (1.0 + math.cos(math.pi * rel_prog))

        if inflection in ("exclamation", "exclaim"):
            env *= 1.20

        # Scale to 16-bit signed PCM range [-32767, 32767] with 0.7 headroom
        amplitude = 32767.0 * 0.70
        sample_val = int(max(-32767.0, min(32767.0, val * env * amplitude)))
        samples.append(sample_val)

    # Encode to binary WAV container in memory
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)       # Mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)
        # Pack samples as little-endian 16-bit signed integers
        raw_pcm = struct.pack(f"<{len(samples)}h", *samples)
        wav_file.writeframes(raw_pcm)

    return buf.getvalue()


# ============================================================================
# Lightweight Syllable-Nucleus Extractor
# ============================================================================

_SYLLABLE_TOKEN_RE = re.compile(
    r"\d+(?:[.,:]\d+)*|[A-Za-z]+(?:'[A-Za-z]+)*\d*|[A-Za-z0-9]+"
)


def _ends_with_consonant_l(stem: str) -> bool:
    """Returns True if `stem` ends with a syllabic consonant + 'l' (e.g. 'tabl', 'doubl')."""
    if len(stem) < 2 or stem[-1] != "l":
        return False
    prev = stem[-2]
    return prev.isalpha() and prev not in "aeiouy"


def extract_syllable_indices(text: str) -> Dict[int, str]:
    """
    Identifies ~1 character index per spoken syllable nucleus in `text` and maps
    each nucleus index to its deterministic Animalese viseme ('a', 'o', 'e', 'f', 'talk').

    Rules:
    - Contiguous vowel runs ('ea', 'ou', 'oo', 'ai') collapse into 1 nucleus at the lead vowel.
    - 'y' acts as a vowel when not word-initial and not adjacent to 'a', 'e', 'i', 'o', 'u'.
    - Multi-cluster words drop silent trailing '-e', '-ed', and '-es' while preserving
      syllabic '-le'/'-les'/'-led', voiced '-ted'/'-ded', and sibilant '-ces'/'-ses'/'-shes'.
    - Numeric or vowel-less tokens ('$150,000', '3:2', 'S17') emit 1 crisp tap at token start.
    """
    if not text:
        return {}

    from dealer_actor import map_char_to_viseme

    syllables: Dict[int, str] = {}
    for match in _SYLLABLE_TOKEN_RE.finditer(text):
        token = match.group(0)
        token_start = match.start()
        word_lower = token.lower()
        n = len(word_lower)

        has_alpha = any(ch.isalpha() for ch in word_lower)
        if not has_alpha:
            syllables[token_start] = "talk"
            continue

        clusters: List[Tuple[int, int]] = []
        i = 0
        while i < n:
            ch = word_lower[i]
            is_v = ch in "aeiou" or (
                ch == "y"
                and i > 0
                and word_lower[i - 1] not in "aeiou"
                and (i + 1 >= n or word_lower[i + 1] not in "aeiou")
            )
            if is_v:
                c_start = i
                i += 1
                while i < n:
                    nch = word_lower[i]
                    nv = nch in "aeiou" or (
                        nch == "y"
                        and word_lower[i - 1] not in "aeiou"
                        and (i + 1 >= n or word_lower[i + 1] not in "aeiou")
                    )
                    if not nv:
                        break
                    i += 1
                clusters.append((c_start, i))
            else:
                i += 1

        if len(clusters) >= 2:
            last_start, last_end = clusters[-1]
            # Silent trailing '-e' (e.g. 'please', 'game', 'house', 'style', 'you're')
            if (
                last_end == n
                and last_end - last_start == 1
                and word_lower[last_start] == "e"
            ):
                stem = word_lower[:last_start]
                if not _ends_with_consonant_l(stem):
                    clusters.pop()
            # Silent trailing '-ed' (e.g. 'played', 'staked', keeping 'busted', 'shuffled')
            elif (
                word_lower.endswith("ed")
                and last_start == n - 2
                and last_end == n - 1
            ):
                stem = word_lower[:-2]
                if not stem.endswith(("t", "d")) and not _ends_with_consonant_l(stem):
                    clusters.pop()
            # Silent trailing '-es' (e.g. 'stakes', 'games', 'rules', keeping 'aces', 'wishes', 'candles')
            elif (
                word_lower.endswith("es")
                and last_start == n - 2
                and last_end == n - 1
            ):
                stem = word_lower[:-2]
                if (
                    not stem.endswith(("s", "z", "x", "c", "g", "sh", "ch"))
                    and not _ends_with_consonant_l(stem)
                ):
                    clusters.pop()

        if not clusters:
            v = map_char_to_viseme(token[0])
            syllables[token_start] = "talk" if v == "neutral" else v
            continue

        for c_start, c_end in clusters:
            lead_ch = word_lower[c_start]
            if lead_ch == "y" and c_end == n:
                viseme = "e"
            else:
                viseme = map_char_to_viseme(lead_ch)
                if viseme == "neutral":
                    viseme = "talk"
            syllables[token_start + c_start] = viseme

    return syllables


# ============================================================================
# Animalese Voice Engine
# ============================================================================

class AnimaleseVoiceEngine:
    """
    Manages procedural Animalese dialogue voice synthesis and playback.
    Pre-renders and caches 1:1 viseme sound buffers in memory for zero-latency streaming.
    """

    def __init__(self, enabled: bool = True, volume: float = 0.8, min_interval_ms: float = 28.0):
        self.enabled = enabled
        self.volume = max(0.0, min(1.0, volume))
        self.min_interval_ms = max(0.0, float(min_interval_ms))
        self._sound_cache: Dict[str, Dict[str, Any]] = {}
        self._cached_text: Optional[str] = None
        self._cached_syllables: Dict[int, str] = {}
        self._last_blip_time: float = 0.0
        self.is_available = PYGAME_AVAILABLE and (pygame_mixer is not None)

        if self.is_available:
            self._ensure_mixer()

    def _ensure_mixer(self):
        """Ensures pygame.mixer is initialized."""
        if not self.is_available or pygame_mixer is None:
            return
        try:
            if not pygame_mixer.get_init():
                pygame_mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        except Exception:
            self.is_available = False

    def get_character_sounds(self, character_id: str) -> Dict[str, Any]:
        """
        Retrieves or generates the cached dictionary of viseme Sound objects
        for the given character profile.
        """
        cid = character_id.lower()
        if cid in self._sound_cache:
            return self._sound_cache[cid]

        profile = VOICE_PROFILES.get(cid, VOICE_PROFILES["dummy"])
        base_freq = profile["base_freq"]
        timbre = profile["timbre"]

        character_dict: Dict[str, Any] = {}
        for viseme in ("a", "o", "e", "f", "talk", "smirk", "gasp"):
            for inf in ("normal", "question", "period", "exclamation"):
                wav_bytes = synthesize_viseme_pcm(
                    base_freq=base_freq,
                    viseme=viseme,
                    timbre=timbre,
                    inflection=inf,
                )
                sound_obj = None
                if self.is_available and pygame_mixer is not None:
                    try:
                        sound_obj = pygame_mixer.Sound(io.BytesIO(wav_bytes))
                        sound_obj.set_volume(self.volume)
                    except Exception:
                        sound_obj = None
                entry = sound_obj or wav_bytes
                if inf == "normal":
                    character_dict[viseme] = entry
                character_dict[f"{viseme}_{inf}"] = entry

        self._sound_cache[cid] = character_dict
        return character_dict

    def _get_syllables_for_text(self, full_text: str) -> Dict[int, str]:
        """Returns cached `{char_index: viseme}` map for the active dialogue string."""
        if full_text != self._cached_text:
            self._cached_text = full_text
            self._cached_syllables = extract_syllable_indices(full_text)
            self._last_blip_time = 0.0
        return self._cached_syllables

    def play_speech_blip(
        self,
        character_id: str,
        char: str,
        char_index: int = 0,
        inflection: str = "normal",
        full_text: Optional[str] = None,
        step_end_index: Optional[int] = None,
        min_interval_ms: Optional[float] = None,
    ) -> bool:
        """
        Plays a single procedural speech blip when the typewriter reaches a syllable nucleus.

        Args:
            character_id: Character ID (e.g. 'tiffany', 'malphas').
            char: The individual character being streamed by typewriter.
            char_index: Start index in dialogue string for this typewriter step.
            inflection: "normal", "question", "period", or "exclamation".
            full_text: Full dialogue line for deterministic syllable-nucleus filtering.
            step_end_index: Exclusive end index for multi-char typewriter strides (`step_advance=2`).
            min_interval_ms: Optional override for minimum acoustic gap between blips.

        Returns:
            bool: True if sound was played, False if skipped, muted, or silent.
        """
        if not self.enabled or self.volume <= 0.0 or not char:
            return False

        viseme: Optional[str] = None
        if full_text is not None:
            syllables = self._get_syllables_for_text(full_text)
            end_idx = max(char_index + 1, step_end_index if step_end_index is not None else (char_index + 1))
            for idx in range(char_index, end_idx):
                if idx in syllables:
                    viseme = syllables[idx]
                    break
            if viseme is None:
                return False
        else:
            # Standalone single-character fallback (when full_text is not supplied)
            if char in (" ", "\t", "\n", "\r", ".", ",", "!", "?", "-", "—", ";", ":", "'", '"', "(", ")", "…"):
                return False
            from dealer_actor import map_char_to_viseme
            viseme = map_char_to_viseme(char)
            if viseme == "neutral":
                return False
            if char_index % 3 != 0 and char.lower() not in ("a", "e", "i", "o", "u"):
                return False

        effective_min_ms = self.min_interval_ms if min_interval_ms is None else max(0.0, float(min_interval_ms))
        now = time.perf_counter()
        if effective_min_ms > 0.0 and self._last_blip_time > 0.0:
            if (now - self._last_blip_time) * 1000.0 < effective_min_ms:
                return False

        sounds = self.get_character_sounds(character_id)
        norm_inf = "exclamation" if inflection == "exclaim" else inflection
        sound_entry = sounds.get(f"{viseme}_{norm_inf}") or sounds.get(viseme)

        if not sound_entry:
            return False

        if self.is_available and hasattr(sound_entry, "play"):
            try:
                sound_entry.play()
                self._last_blip_time = now
                return True
            except Exception:
                return False

        return False

    def set_volume(self, volume: float):
        """Updates voice blip playback volume for all cached character sounds."""
        self.volume = max(0.0, min(1.0, volume))
        for char_dict in self._sound_cache.values():
            for sound in char_dict.values():
                if hasattr(sound, "set_volume"):
                    try:
                        sound.set_volume(self.volume)
                    except Exception:
                        pass
