"""
Procedural Generator for Dealer Layered Sprite Character Roster (Phase B).
Generates:
- 4 Characters: Julian, Malphas, Uriel, Mortimer.
- 13 Sprite Layers each:
  - torso.png, torso_2x.png
  - head.png, head_2x.png
  - eyes_open.png, eyes_open_2x.png
  - eyes_half.png, eyes_half_2x.png
  - eyes_closed.png, eyes_closed_2x.png
  - mouth_neutral.png, mouth_neutral_2x.png
  - mouth_talk.png, mouth_talk_2x.png
  - mouth_smirk.png, mouth_smirk_2x.png
  - mouth_gasp.png, mouth_gasp_2x.png
  - arm_rest.png, arm_rest_2x.png
  - arm_deal.png, arm_deal_2x.png
  - arm_peek.png, arm_peek_2x.png
  - bust.png, bust_2x.png
- Authentic audio accent files in audio/haunted/ (Julian, Malphas, Uriel, Mortimer)
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

BASE_DIR = Path(__file__).resolve().parent.parent
HAUNTED_DIR = BASE_DIR / "assets" / "haunted"
CHARACTERS_DIR = HAUNTED_DIR / "characters"
AUDIO_DIR = BASE_DIR / "audio" / "haunted"

CHARACTERS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Sprite Drawing Utilities
# ---------------------------------------------------------------------------

def draw_feather(draw: ImageDraw.ImageDraw, x: int, y: int, length: int, angle_deg: float, color: tuple):
    """Draws a jaunty quill feather with central quill and barbs."""
    rad = math.radians(angle_deg)
    ex = x + int(length * math.cos(rad))
    ey = y + int(length * math.sin(rad))
    draw.line([x, y, ex, ey], fill=color, width=2)
    # Side barbs
    for t in range(5, length - 3, 4):
        bx = x + int(t * math.cos(rad))
        by = y + int(t * math.sin(rad))
        perp = rad + math.pi / 2
        draw.line([bx, by, bx + int(6 * math.cos(perp)), by + int(6 * math.sin(perp))], fill=color, width=1)


# ---------------------------------------------------------------------------
# Character 1: Julian (The Classic Croupier)
# ---------------------------------------------------------------------------

def generate_julian_layers(size: int = 112) -> dict[str, Image.Image]:
    s = size / 112.0
    layers = {}

    # 1. Torso
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # White collar
    d.polygon([(int(44 * s), int(72 * s)), (int(68 * s), int(72 * s)), (int(56 * s), int(86 * s))], fill=(245, 245, 250, 255))
    # Dark tuxedo vest / shoulders
    d.polygon([
        (int(18 * s), int(112 * s)), (int(26 * s), int(82 * s)), (int(42 * s), int(74 * s)),
        (int(56 * s), int(86 * s)),
        (int(70 * s), int(74 * s)), (int(86 * s), int(82 * s)), (int(94 * s), int(112 * s))
    ], fill=(24, 26, 30, 255))
    # Vest lapel edges
    d.line([(int(42 * s), int(74 * s)), (int(56 * s), int(108 * s)), (int(70 * s), int(74 * s))], fill=(45, 48, 55, 255), width=int(2 * s))
    # Silver pocket watch chain
    d.arc([int(32 * s), int(88 * s), int(48 * s), int(98 * s)], 0, 180, fill=(200, 205, 215, 230), width=int(1.5 * s))
    # Black Bowtie
    d.polygon([(int(48 * s), int(73 * s)), (int(56 * s), int(76 * s)), (int(48 * s), int(79 * s))], fill=(15, 15, 18, 255))
    d.polygon([(int(64 * s), int(73 * s)), (int(56 * s), int(76 * s)), (int(64 * s), int(79 * s))], fill=(15, 15, 18, 255))
    d.rectangle([int(54 * s), int(74 * s), int(58 * s), int(78 * s)], fill=(30, 30, 35, 255))
    layers["torso"] = img

    # 2. Head
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Neck
    d.rectangle([int(48 * s), int(64 * s), int(64 * s), int(74 * s)], fill=(225, 185, 155, 255))
    # Face base
    d.ellipse([int(36 * s), int(30 * s), int(76 * s), int(70 * s)], fill=(240, 200, 170, 255))
    # Ears
    d.ellipse([int(33 * s), int(46 * s), int(39 * s), int(56 * s)], fill=(225, 185, 155, 255))
    d.ellipse([int(73 * s), int(46 * s), int(79 * s), int(56 * s)], fill=(225, 185, 155, 255))
    # Neatly parted dark brown hair
    d.chord([int(34 * s), int(22 * s), int(78 * s), int(48 * s)], 180, 360, fill=(45, 30, 20, 255))
    d.polygon([(int(34 * s), int(35 * s)), (int(56 * s), int(28 * s)), (int(42 * s), int(40 * s))], fill=(45, 30, 20, 255))
    # Eyebrows
    d.line([(int(42 * s), int(43 * s)), (int(50 * s), int(42 * s))], fill=(50, 35, 25, 255), width=int(2 * s))
    d.line([(int(62 * s), int(42 * s)), (int(70 * s), int(43 * s))], fill=(50, 35, 25, 255), width=int(2 * s))
    # Subtle nose
    d.line([(int(56 * s), int(46 * s)), (int(57 * s), int(54 * s)), (int(54 * s), int(55 * s))], fill=(210, 165, 135, 255), width=int(1.5 * s))
    layers["head"] = img

    # 3. Eyes
    # Open
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(43 * s), int(45 * s), int(49 * s), int(50 * s)], fill=(255, 255, 255, 255))
    d.ellipse([int(63 * s), int(45 * s), int(69 * s), int(50 * s)], fill=(255, 255, 255, 255))
    d.ellipse([int(45 * s), int(46 * s), int(48 * s), int(49 * s)], fill=(50, 30, 15, 255))
    d.ellipse([int(65 * s), int(46 * s), int(68 * s), int(49 * s)], fill=(50, 30, 15, 255))
    layers["eyes_open"] = img

    # Half
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([int(43 * s), int(47 * s), int(49 * s), int(50 * s)], fill=(255, 255, 255, 255))
    d.rectangle([int(63 * s), int(47 * s), int(69 * s), int(50 * s)], fill=(255, 255, 255, 255))
    d.line([(int(42 * s), int(47 * s)), (int(50 * s), int(47 * s))], fill=(90, 60, 45, 255), width=int(1.5 * s))
    d.line([(int(62 * s), int(47 * s)), (int(70 * s), int(47 * s))], fill=(90, 60, 45, 255), width=int(1.5 * s))
    layers["eyes_half"] = img

    # Closed
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.arc([int(43 * s), int(46 * s), int(49 * s), int(50 * s)], 0, 180, fill=(90, 60, 45, 255), width=int(1.5 * s))
    d.arc([int(63 * s), int(46 * s), int(69 * s), int(50 * s)], 0, 180, fill=(90, 60, 45, 255), width=int(1.5 * s))
    layers["eyes_closed"] = img

    # 4. Mouths
    # Neutral
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(51 * s), int(62 * s)), (int(61 * s), int(62 * s))], fill=(160, 80, 80, 255), width=int(1.5 * s))
    layers["mouth_neutral"] = img

    # Talk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(52 * s), int(60 * s), int(60 * s), int(65 * s)], fill=(120, 40, 40, 255))
    d.line([(int(53 * s), int(61 * s)), (int(59 * s), int(61 * s))], fill=(250, 250, 250, 255), width=1)
    layers["mouth_talk"] = img

    # Smirk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(50 * s), int(63 * s)), (int(57 * s), int(62 * s)), (int(63 * s), int(60 * s))], fill=(160, 75, 75, 255), width=int(1.5 * s))
    layers["mouth_smirk"] = img

    # Gasp
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(53 * s), int(59 * s), int(59 * s), int(66 * s)], fill=(90, 30, 30, 255), outline=(160, 80, 80, 255))
    layers["mouth_gasp"] = img

    # 5. Arms
    # Rest
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(20, 22, 26, 255))
    d.polygon([(int(92 * s), int(96 * s)), (int(76 * s), int(106 * s)), (int(82 * s), int(112 * s)), (int(96 * s), int(106 * s))], fill=(20, 22, 26, 255))
    # White cuffs
    d.rectangle([int(33 * s), int(104 * s), int(38 * s), int(108 * s)], fill=(245, 245, 250, 255))
    d.rectangle([int(74 * s), int(104 * s), int(79 * s), int(108 * s)], fill=(245, 245, 250, 255))
    layers["arm_rest"] = img

    # Deal
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(20, 22, 26, 255))
    # Right arm reaching forward smoothly
    d.polygon([(int(88 * s), int(86 * s)), (int(60 * s), int(106 * s)), (int(64 * s), int(112 * s)), (int(94 * s), int(92 * s))], fill=(22, 24, 28, 255))
    d.rectangle([int(58 * s), int(104 * s), int(64 * s), int(108 * s)], fill=(245, 245, 250, 255))
    # Hand reaching toward table felt
    d.ellipse([int(52 * s), int(106 * s), int(60 * s), int(112 * s)], fill=(235, 195, 165, 255))
    layers["arm_deal"] = img

    # Peek
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(20, 22, 26, 255))
    # Hand angled touching hole card corner
    d.polygon([(int(88 * s), int(88 * s)), (int(68 * s), int(96 * s)), (int(72 * s), int(104 * s)), (int(94 * s), int(94 * s))], fill=(22, 24, 28, 255))
    d.ellipse([int(62 * s), int(94 * s), int(70 * s), int(102 * s)], fill=(235, 195, 165, 255))
    layers["arm_peek"] = img

    return layers


# ---------------------------------------------------------------------------
# Character 2: Malphas (The Pit Fiend)
# ---------------------------------------------------------------------------

def generate_malphas_layers(size: int = 112) -> dict[str, Image.Image]:
    s = size / 112.0
    layers = {}

    # 1. Torso
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Jagged dark obsidian mantle
    d.polygon([
        (int(14 * s), int(112 * s)), (int(22 * s), int(80 * s)), (int(38 * s), int(72 * s)),
        (int(56 * s), int(88 * s)),
        (int(74 * s), int(72 * s)), (int(90 * s), int(80 * s)), (int(98 * s), int(112 * s))
    ], fill=(32, 10, 14, 255))
    # Molten lava fissure lines
    d.line([(int(46 * s), int(84 * s)), (int(52 * s), int(98 * s)), (int(48 * s), int(112 * s))], fill=(255, 69, 0, 230), width=int(2 * s))
    d.line([(int(66 * s), int(84 * s)), (int(60 * s), int(96 * s)), (int(64 * s), int(112 * s))], fill=(255, 140, 0, 230), width=int(1.5 * s))
    d.line([(int(56 * s), int(88 * s)), (int(56 * s), int(108 * s))], fill=(255, 215, 0, 255), width=int(1 * s))
    layers["torso"] = img

    # 2. Head
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Neck
    d.rectangle([int(46 * s), int(64 * s), int(66 * s), int(76 * s)], fill=(120, 25, 28, 255))
    # Obsidian Ram Horns (Left and Right curving out)
    # Left horn
    d.arc([int(12 * s), int(16 * s), int(50 * s), int(54 * s)], 120, 320, fill=(30, 25, 25, 255), width=int(8 * s))
    d.polygon([(int(14 * s), int(26 * s)), (int(22 * s), int(18 * s)), (int(10 * s), int(16 * s))], fill=(20, 18, 18, 255))
    # Right horn
    d.arc([int(62 * s), int(16 * s), int(100 * s), int(54 * s)], 220, 60, fill=(30, 25, 25, 255), width=int(8 * s))
    d.polygon([(int(98 * s), int(26 * s)), (int(90 * s), int(18 * s)), (int(102 * s), int(16 * s))], fill=(20, 18, 18, 255))
    # Demonic crimson face base
    d.polygon([
        (int(36 * s), int(34 * s)), (int(76 * s), int(34 * s)),
        (int(74 * s), int(58 * s)), (int(64 * s), int(72 * s)),
        (int(48 * s), int(72 * s)), (int(38 * s), int(58 * s))
    ], fill=(160, 30, 32, 255))
    # Pointed ears
    d.polygon([(int(36 * s), int(42 * s)), (int(24 * s), int(38 * s)), (int(34 * s), int(50 * s))], fill=(130, 24, 28, 255))
    d.polygon([(int(76 * s), int(42 * s)), (int(88 * s), int(38 * s)), (int(78 * s), int(50 * s))], fill=(130, 24, 28, 255))
    # Brow ridge
    d.polygon([(int(38 * s), int(40 * s)), (int(56 * s), int(44 * s)), (int(74 * s), int(40 * s)), (int(56 * s), int(42 * s))], fill=(100, 15, 18, 255))
    layers["head"] = img

    # 3. Eyes
    # Open
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Glowing yellow/orange ember slit eyes
    d.polygon([(int(43 * s), int(46 * s)), (int(50 * s), int(44 * s)), (int(48 * s), int(49 * s))], fill=(255, 215, 0, 255))
    d.polygon([(int(69 * s), int(46 * s)), (int(62 * s), int(44 * s)), (int(64 * s), int(49 * s))], fill=(255, 215, 0, 255))
    d.line([(int(47 * s), int(44 * s)), (int(46 * s), int(48 * s))], fill=(255, 69, 0, 255), width=int(1.5 * s))
    d.line([(int(65 * s), int(44 * s)), (int(66 * s), int(48 * s))], fill=(255, 69, 0, 255), width=int(1.5 * s))
    layers["eyes_open"] = img

    # Half
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(43 * s), int(47 * s)), (int(50 * s), int(46 * s))], fill=(255, 140, 0, 255), width=int(2 * s))
    d.line([(int(62 * s), int(46 * s)), (int(69 * s), int(47 * s))], fill=(255, 140, 0, 255), width=int(2 * s))
    layers["eyes_half"] = img

    # Closed
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(43 * s), int(47 * s)), (int(50 * s), int(48 * s))], fill=(90, 15, 20, 255), width=int(1.5 * s))
    d.line([(int(62 * s), int(48 * s)), (int(69 * s), int(47 * s))], fill=(90, 15, 20, 255), width=int(1.5 * s))
    layers["eyes_closed"] = img

    # 4. Mouths
    # Neutral
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(48 * s), int(64 * s)), (int(64 * s), int(64 * s))], fill=(60, 8, 12, 255), width=int(2 * s))
    # Two small white fangs
    d.polygon([(int(51 * s), int(64 * s)), (int(53 * s), int(67 * s)), (int(55 * s), int(64 * s))], fill=(240, 240, 240, 255))
    d.polygon([(int(57 * s), int(64 * s)), (int(59 * s), int(67 * s)), (int(61 * s), int(64 * s))], fill=(240, 240, 240, 255))
    layers["mouth_neutral"] = img

    # Talk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(48 * s), int(62 * s)), (int(64 * s), int(62 * s)), (int(56 * s), int(68 * s))], fill=(40, 6, 8, 255))
    d.polygon([(int(51 * s), int(62 * s)), (int(53 * s), int(65 * s)), (int(55 * s), int(62 * s))], fill=(240, 240, 240, 255))
    d.polygon([(int(57 * s), int(62 * s)), (int(59 * s), int(65 * s)), (int(61 * s), int(62 * s))], fill=(240, 240, 240, 255))
    layers["mouth_talk"] = img

    # Smirk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(47 * s), int(65 * s)), (int(56 * s), int(63 * s)), (int(66 * s), int(60 * s))], fill=(50, 8, 10, 255), width=int(2 * s))
    d.polygon([(int(60 * s), int(62 * s)), (int(62 * s), int(66 * s)), (int(64 * s), int(61 * s))], fill=(245, 245, 245, 255))
    layers["mouth_smirk"] = img

    # Gasp
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(50 * s), int(60 * s), int(62 * s), int(70 * s)], fill=(30, 4, 6, 255), outline=(180, 40, 40, 255))
    layers["mouth_gasp"] = img

    # 5. Arms
    # Rest
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(18 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(14 * s), int(106 * s))], fill=(130, 26, 30, 255))
    d.polygon([(int(94 * s), int(96 * s)), (int(76 * s), int(106 * s)), (int(82 * s), int(112 * s)), (int(98 * s), int(106 * s))], fill=(130, 26, 30, 255))
    # Claws
    d.line([(int(32 * s), int(108 * s)), (int(38 * s), int(112 * s))], fill=(20, 16, 16, 255), width=2)
    d.line([(int(80 * s), int(108 * s)), (int(74 * s), int(112 * s))], fill=(20, 16, 16, 255), width=2)
    layers["arm_rest"] = img

    # Deal
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(18 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(14 * s), int(106 * s))], fill=(130, 26, 30, 255))
    # Claw reaching toward shoe with fiery fingertip
    d.polygon([(int(90 * s), int(86 * s)), (int(60 * s), int(106 * s)), (int(64 * s), int(112 * s)), (int(96 * s), int(92 * s))], fill=(140, 28, 32, 255))
    d.ellipse([int(52 * s), int(106 * s), int(60 * s), int(112 * s)], fill=(255, 69, 0, 255))
    layers["arm_deal"] = img

    # Peek
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(18 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(14 * s), int(106 * s))], fill=(130, 26, 30, 255))
    d.polygon([(int(90 * s), int(88 * s)), (int(66 * s), int(96 * s)), (int(70 * s), int(104 * s)), (int(96 * s), int(94 * s))], fill=(140, 28, 32, 255))
    d.line([(int(66 * s), int(98 * s)), (int(60 * s), int(94 * s))], fill=(20, 16, 16, 255), width=2)
    layers["arm_peek"] = img

    return layers


# ---------------------------------------------------------------------------
# Character 3: Uriel (The Celestial Seraph)
# ---------------------------------------------------------------------------

def generate_uriel_layers(size: int = 112) -> dict[str, Image.Image]:
    s = size / 112.0
    layers = {}

    # 1. Torso
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Ivory vestments
    d.polygon([
        (int(18 * s), int(112 * s)), (int(26 * s), int(82 * s)), (int(40 * s), int(74 * s)),
        (int(56 * s), int(84 * s)),
        (int(72 * s), int(74 * s)), (int(86 * s), int(82 * s)), (int(94 * s), int(112 * s))
    ], fill=(245, 248, 252, 255))
    # Gold embroidered stole/collar
    d.line([(int(40 * s), int(74 * s)), (int(56 * s), int(108 * s)), (int(72 * s), int(74 * s))], fill=(218, 165, 32, 255), width=int(3 * s))
    # Azure gemstone broach
    d.ellipse([int(53 * s), int(82 * s), int(59 * s), int(88 * s)], fill=(0, 229, 255, 255), outline=(255, 215, 0, 255))
    layers["torso"] = img

    # 2. Head
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Floating Golden Halo above head
    halo_bbox = [int(32 * s), int(12 * s), int(80 * s), int(26 * s)]
    d.ellipse(halo_bbox, outline=(255, 215, 0, 240), width=int(3 * s))
    # Inner halo glow
    d.ellipse([int(36 * s), int(14 * s), int(76 * s), int(24 * s)], outline=(255, 245, 180, 180), width=1)
    # Neck
    d.rectangle([int(48 * s), int(64 * s), int(64 * s), int(76 * s)], fill=(245, 225, 205, 255))
    # Celestial serene face
    d.ellipse([int(36 * s), int(30 * s), int(76 * s), int(70 * s)], fill=(255, 235, 218, 255))
    # Flowing golden locks
    d.chord([int(34 * s), int(22 * s), int(78 * s), int(50 * s)], 170, 370, fill=(235, 195, 75, 255))
    d.line([(int(34 * s), int(36 * s)), (int(32 * s), int(62 * s))], fill=(225, 180, 60, 255), width=int(3 * s))
    d.line([(int(78 * s), int(36 * s)), (int(80 * s), int(62 * s))], fill=(225, 180, 60, 255), width=int(3 * s))
    # Graceful eyebrows
    d.line([(int(42 * s), int(42 * s)), (int(50 * s), int(41 * s))], fill=(190, 140, 45, 255), width=int(1.5 * s))
    d.line([(int(62 * s), int(41 * s)), (int(70 * s), int(42 * s))], fill=(190, 140, 45, 255), width=int(1.5 * s))
    layers["head"] = img

    # 3. Eyes
    # Open
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Radiant azure glowing eyes
    d.ellipse([int(43 * s), int(45 * s), int(49 * s), int(50 * s)], fill=(240, 255, 255, 255))
    d.ellipse([int(63 * s), int(45 * s), int(69 * s), int(50 * s)], fill=(240, 255, 255, 255))
    d.ellipse([int(45 * s), int(46 * s), int(48 * s), int(49 * s)], fill=(0, 229, 255, 255))
    d.ellipse([int(65 * s), int(46 * s), int(68 * s), int(49 * s)], fill=(0, 229, 255, 255))
    layers["eyes_open"] = img

    # Half
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(43 * s), int(47 * s)), (int(49 * s), int(47 * s))], fill=(0, 180, 215, 255), width=int(2 * s))
    d.line([(int(63 * s), int(47 * s)), (int(69 * s), int(47 * s))], fill=(0, 180, 215, 255), width=int(2 * s))
    layers["eyes_half"] = img

    # Closed
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.arc([int(43 * s), int(46 * s), int(49 * s), int(50 * s)], 0, 180, fill=(180, 130, 45, 255), width=int(1.5 * s))
    d.arc([int(63 * s), int(46 * s), int(69 * s), int(50 * s)], 0, 180, fill=(180, 130, 45, 255), width=int(1.5 * s))
    layers["eyes_closed"] = img

    # 4. Mouths
    # Neutral
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(51 * s), int(62 * s)), (int(61 * s), int(62 * s))], fill=(210, 120, 120, 255), width=int(1.5 * s))
    layers["mouth_neutral"] = img

    # Talk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(52 * s), int(60 * s), int(60 * s), int(65 * s)], fill=(160, 60, 60, 255))
    layers["mouth_talk"] = img

    # Smirk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(51 * s), int(63 * s)), (int(57 * s), int(62 * s)), (int(62 * s), int(60 * s))], fill=(210, 120, 120, 255), width=int(1.5 * s))
    layers["mouth_smirk"] = img

    # Gasp
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(53 * s), int(60 * s), int(59 * s), int(66 * s)], fill=(140, 50, 50, 255))
    layers["mouth_gasp"] = img

    # 5. Arms
    # Rest
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(238, 242, 248, 255))
    d.polygon([(int(92 * s), int(96 * s)), (int(76 * s), int(106 * s)), (int(82 * s), int(112 * s)), (int(96 * s), int(106 * s))], fill=(238, 242, 248, 255))
    d.line([(int(30 * s), int(106 * s)), (int(36 * s), int(106 * s))], fill=(218, 165, 32, 255), width=2)
    d.line([(int(76 * s), int(106 * s)), (int(82 * s), int(106 * s))], fill=(218, 165, 32, 255), width=2)
    layers["arm_rest"] = img

    # Deal
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(238, 242, 248, 255))
    d.polygon([(int(88 * s), int(86 * s)), (int(60 * s), int(106 * s)), (int(64 * s), int(112 * s)), (int(94 * s), int(92 * s))], fill=(242, 245, 250, 255))
    d.ellipse([int(52 * s), int(106 * s), int(60 * s), int(112 * s)], fill=(255, 245, 200, 255))
    layers["arm_deal"] = img

    # Peek
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(238, 242, 248, 255))
    d.polygon([(int(88 * s), int(88 * s)), (int(68 * s), int(96 * s)), (int(72 * s), int(104 * s)), (int(94 * s), int(94 * s))], fill=(242, 245, 250, 255))
    d.ellipse([int(62 * s), int(94 * s), int(70 * s), int(102 * s)], fill=(255, 245, 200, 255))
    layers["arm_peek"] = img

    return layers


# ---------------------------------------------------------------------------
# Character 4: Mortimer (Grim Bones)
# ---------------------------------------------------------------------------

def generate_mortimer_layers(size: int = 112) -> dict[str, Image.Image]:
    s = size / 112.0
    layers = {}

    # 1. Torso
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Skeletal ribcage inside purple silk waistcoat
    d.polygon([
        (int(18 * s), int(112 * s)), (int(26 * s), int(82 * s)), (int(42 * s), int(74 * s)),
        (int(56 * s), int(86 * s)),
        (int(70 * s), int(74 * s)), (int(86 * s), int(82 * s)), (int(94 * s), int(112 * s))
    ], fill=(58, 24, 76, 255))
    # Lapels & gold trim
    d.line([(int(42 * s), int(74 * s)), (int(56 * s), int(108 * s)), (int(70 * s), int(74 * s))], fill=(186, 140, 40, 255), width=int(2 * s))
    # Ribs visible in center gap
    for ry in range(int(88 * s), int(108 * s), int(6 * s)):
        d.line([(int(51 * s), ry), (int(61 * s), ry)], fill=(230, 230, 235, 255), width=int(2 * s))
    # Black Bowtie
    d.polygon([(int(48 * s), int(73 * s)), (int(56 * s), int(76 * s)), (int(48 * s), int(79 * s))], fill=(15, 12, 20, 255))
    d.polygon([(int(64 * s), int(73 * s)), (int(56 * s), int(76 * s)), (int(64 * s), int(79 * s))], fill=(15, 12, 20, 255))
    layers["torso"] = img

    # 2. Head
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Cervical spine / neck
    d.rectangle([int(52 * s), int(64 * s), int(60 * s), int(74 * s)], fill=(215, 215, 220, 255))
    # Bone skull base
    d.ellipse([int(38 * s), int(34 * s), int(74 * s), int(68 * s)], fill=(235, 235, 240, 255))
    d.rectangle([int(44 * s), int(56 * s), int(68 * s), int(70 * s)], fill=(235, 235, 240, 255))
    # Dark eye sockets (base)
    d.ellipse([int(42 * s), int(44 * s), int(51 * s), int(53 * s)], fill=(25, 15, 30, 255))
    d.ellipse([int(61 * s), int(44 * s), int(70 * s), int(53 * s)], fill=(25, 15, 30, 255))
    # Nasal cavity (inverted heart)
    d.polygon([(int(56 * s), int(54 * s)), (int(54 * s), int(58 * s)), (int(58 * s), int(58 * s))], fill=(25, 15, 30, 255))
    # Dapper Purple Silk Top Hat
    # Brim
    d.ellipse([int(26 * s), int(30 * s), int(86 * s), int(40 * s)], fill=(45, 16, 60, 255), outline=(20, 8, 28, 255))
    # Crown
    d.polygon([
        (int(36 * s), int(34 * s)), (int(40 * s), int(10 * s)),
        (int(72 * s), int(10 * s)), (int(76 * s), int(34 * s))
    ], fill=(52, 18, 70, 255), outline=(20, 8, 28, 255))
    # Gold Hatband
    d.polygon([(int(37 * s), int(31 * s)), (int(75 * s), int(31 * s)), (int(74 * s), int(26 * s)), (int(38 * s), int(26 * s))], fill=(218, 165, 32, 255))
    # Jaunty white quill feather
    draw_feather(d, int(68 * s), int(28 * s), int(22 * s), -60, (245, 245, 250, 255))
    layers["head"] = img

    # 3. Eyes (Spectral flame pinpoints inside dark sockets)
    # Open
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Bright purple/magenta pinpoints
    d.ellipse([int(45 * s), int(47 * s), int(48 * s), int(50 * s)], fill=(224, 64, 251, 255))
    d.ellipse([int(64 * s), int(47 * s), int(67 * s), int(50 * s)], fill=(224, 64, 251, 255))
    d.point([(int(46 * s), int(48 * s)), (int(65 * s), int(48 * s))], fill=(255, 255, 255, 255))
    layers["eyes_open"] = img

    # Half
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(45 * s), int(48 * s), int(48 * s), int(50 * s)], fill=(156, 39, 176, 200))
    d.ellipse([int(64 * s), int(48 * s), int(67 * s), int(50 * s)], fill=(156, 39, 176, 200))
    layers["eyes_half"] = img

    # Closed (extinguished sockets)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # Completely dark sockets
    layers["eyes_closed"] = img

    # 4. Mouths (Skeletal teeth & jaw states)
    # Neutral (toothy grin)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for tx in range(int(46 * s), int(66 * s), int(4 * s)):
        d.line([(tx, int(62 * s)), (tx, int(67 * s))], fill=(40, 30, 45, 255), width=int(1.5 * s))
    d.line([(int(45 * s), int(64 * s)), (int(67 * s), int(64 * s))], fill=(40, 30, 45, 255), width=1)
    layers["mouth_neutral"] = img

    # Talk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(48 * s), int(62 * s), int(64 * s), int(69 * s)], fill=(25, 15, 30, 255))
    for tx in range(int(50 * s), int(62 * s), int(3 * s)):
        d.line([(tx, int(61 * s)), (tx, int(63 * s))], fill=(235, 235, 240, 255), width=1)
    layers["mouth_talk"] = img

    # Smirk
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(46 * s), int(65 * s)), (int(56 * s), int(64 * s)), (int(67 * s), int(61 * s))], fill=(35, 20, 40, 255), width=int(2 * s))
    layers["mouth_smirk"] = img

    # Gasp
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(50 * s), int(62 * s), int(62 * s), int(72 * s)], fill=(20, 10, 25, 255), outline=(215, 215, 220, 255))
    layers["mouth_gasp"] = img

    # 5. Arms
    # Rest
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(48, 18, 64, 255))
    d.polygon([(int(92 * s), int(96 * s)), (int(76 * s), int(106 * s)), (int(82 * s), int(112 * s)), (int(96 * s), int(106 * s))], fill=(48, 18, 64, 255))
    # Bone hands
    d.ellipse([int(32 * s), int(106 * s), int(38 * s), int(112 * s)], fill=(235, 235, 240, 255))
    d.ellipse([int(74 * s), int(106 * s), int(80 * s), int(112 * s)], fill=(235, 235, 240, 255))
    layers["arm_rest"] = img

    # Deal
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(48, 18, 64, 255))
    d.polygon([(int(88 * s), int(86 * s)), (int(60 * s), int(106 * s)), (int(64 * s), int(112 * s)), (int(94 * s), int(92 * s))], fill=(52, 20, 68, 255))
    # Skeletal hand reaching forward
    d.ellipse([int(52 * s), int(106 * s), int(60 * s), int(112 * s)], fill=(235, 235, 240, 255))
    layers["arm_deal"] = img

    # Peek
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(int(20 * s), int(96 * s)), (int(36 * s), int(106 * s)), (int(30 * s), int(112 * s)), (int(16 * s), int(106 * s))], fill=(48, 18, 64, 255))
    d.polygon([(int(88 * s), int(88 * s)), (int(68 * s), int(96 * s)), (int(72 * s), int(104 * s)), (int(94 * s), int(94 * s))], fill=(52, 20, 68, 255))
    d.ellipse([int(62 * s), int(94 * s), int(70 * s), int(102 * s)], fill=(235, 235, 240, 255))
    layers["arm_peek"] = img

    return layers


# ---------------------------------------------------------------------------
# Composite Bust Creator
# ---------------------------------------------------------------------------

def create_bust_composite(layers: dict[str, Image.Image]) -> Image.Image:
    """Assembles torso + head + eyes_open + mouth_neutral + arm_rest into bust.png."""
    base = Image.new("RGBA", layers["torso"].size, (0, 0, 0, 0))
    for name in ("torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
        if name in layers:
            base.alpha_composite(layers[name])
    return base


# ---------------------------------------------------------------------------
# Audio Accents Synthesizer
# ---------------------------------------------------------------------------

def synthesize_wav(filepath: Path, duration_sec: float, sample_rate: int, wave_fn):
    """Synthesizes an uncompressed 16-bit mono PCM .wav file."""
    num_samples = int(sample_rate * duration_sec)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        val = wave_fn(t, duration_sec)
        val = max(-1.0, min(1.0, val))
        samples.append(int(val * 32767.0))

    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(data)


def build_audio_accents():
    """Synthesizes character audio accents if not already present."""
    sr = 44100

    # 1. Julian: Polite casino throat-clear / greeting murmur (low warm gentle sound)
    julian_wav = AUDIO_DIR / "dealer_julian.wav"
    julian_ogg = AUDIO_DIR / "dealer_julian.ogg"
    if not julian_wav.exists() and not julian_ogg.exists():
        def julian_snd(t, dur):
            env = math.exp(-t * 5.0)
            return (0.4 * math.sin(2 * math.pi * 140 * t) + 0.2 * math.sin(2 * math.pi * 280 * t)) * env
        synthesize_wav(julian_wav, 0.45, sr, julian_snd)
        try:
            julian_wav.rename(julian_ogg)
        except Exception:
            pass

    # 2. Malphas: Low guttural demon rumble
    malphas_wav = AUDIO_DIR / "dealer_malphas.wav"
    malphas_ogg = AUDIO_DIR / "dealer_malphas.ogg"
    if not malphas_wav.exists() and not malphas_ogg.exists():
        def malphas_snd(t, dur):
            env = math.exp(-t * 3.5)
            # Modulation with noise and deep rumble
            rumble = 0.5 * math.sin(2 * math.pi * 55 * t) + 0.3 * math.sin(2 * math.pi * 110 * t * (1.0 + 0.2 * math.sin(2 * math.pi * 12 * t)))
            return rumble * env
        synthesize_wav(malphas_wav, 0.65, sr, malphas_snd)
        try:
            malphas_wav.rename(malphas_ogg)
        except Exception:
            pass

    # 3. Uriel: Ethereal celestial chime
    uriel_wav = AUDIO_DIR / "dealer_uriel.wav"
    uriel_ogg = AUDIO_DIR / "dealer_uriel.ogg"
    if not uriel_wav.exists() and not uriel_ogg.exists():
        def uriel_snd(t, dur):
            env = math.exp(-t * 2.8)
            chime = (0.4 * math.sin(2 * math.pi * 587.33 * t) +  # D5
                     0.3 * math.sin(2 * math.pi * 880.00 * t) +  # A5
                     0.3 * math.sin(2 * math.pi * 1174.66 * t))  # D6
            return chime * env
        synthesize_wav(uriel_wav, 0.8, sr, uriel_snd)
        try:
            uriel_wav.rename(uriel_ogg)
        except Exception:
            pass

    # 4. Mortimer: Crisp bone clatter / dry chuckle
    mortimer_wav = AUDIO_DIR / "dealer_mortimer.wav"
    mortimer_ogg = AUDIO_DIR / "dealer_mortimer.ogg"
    if not mortimer_wav.exists() and not mortimer_ogg.exists():
        def mortimer_snd(t, dur):
            # Click train with bone resonant hollow pitches
            clicks = sum(math.exp(-((t - ct) ** 2) / (0.003 ** 2)) * math.sin(2 * math.pi * 420 * t) for ct in [0.05, 0.12, 0.18, 0.28])
            return clicks * 0.7
        synthesize_wav(mortimer_wav, 0.4, sr, mortimer_snd)
        try:
            mortimer_wav.rename(mortimer_ogg)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Main Generation Flow
# ---------------------------------------------------------------------------

def build_all_characters():
    print("Generating Layered Character Sprites...")
    generators = {
        "julian": generate_julian_layers,
        "malphas": generate_malphas_layers,
        "uriel": generate_uriel_layers,
        "mortimer": generate_mortimer_layers,
    }

    for char_id, gen_fn in generators.items():
        char_dir = CHARACTERS_DIR / char_id
        char_dir.mkdir(parents=True, exist_ok=True)
        print(f" -> Generating character: {char_id}...")

        # 1x Layers (112x112)
        layers_1x = gen_fn(size=112)
        for layer_name, img in layers_1x.items():
            path_1x = char_dir / f"{layer_name}.png"
            img.save(path_1x, "PNG")

        bust_1x = create_bust_composite(layers_1x)
        bust_1x.save(char_dir / "bust.png", "PNG")

        # 2x Layers (224x224)
        layers_2x = gen_fn(size=224)
        for layer_name, img in layers_2x.items():
            path_2x = char_dir / f"{layer_name}_2x.png"
            img.save(path_2x, "PNG")

        bust_2x = create_bust_composite(layers_2x)
        bust_2x.save(char_dir / "bust_2x.png", "PNG")

    print("Synthesizing character audio accents...")
    build_audio_accents()
    print("Character asset generation complete!")


if __name__ == "__main__":
    build_all_characters()
