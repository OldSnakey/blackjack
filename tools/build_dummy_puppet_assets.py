"""
Procedural Generator for Dummy Multi-Layer Puppet Actor Assets.

Generates high-contrast, discrete sprite layers for the 'dummy' character:
- 1x (112x112 px) and 2x (224x224 px) RGBA PNGs
- Layers:
  - shadow.png, shadow_2x.png (Grounding base on table rail)
  - torso.png, torso_2x.png (Royal Blue chest & jacket, clean shoulders)
  - neck.png, neck_2x.png (Warm Sand neck column)
  - head.png, head_2x.png (Coral Peach face base & ears, blank canvas)
  - eyes_open.png, eyes_half.png, eyes_closed.png (Electric Cyan eyes)
  - mouth_neutral.png (Rest / M, B, P viseme)
  - mouth_a.png (Open vowel A, I viseme)
  - mouth_o.png (Rounded puckered O, U viseme)
  - mouth_e.png (Wide dental smile E, C, S, T viseme)
  - mouth_f.png (Labiodental F, V viseme)
  - mouth_talk.png (Generic talk fallback)
  - mouth_smirk.png (Sardonic smirk)
  - mouth_gasp.png (Shock / gasp cavity)
  - arm_rest.png (Emerald Green left arm, Deep Violet right arm, Golden Amber hands)
  - arm_deal.png (Left arm reaching with card)
  - arm_peek.png (Right hand lifting hole card corner)
  - bust.png (Pre-composited reference portrait)
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
HAUNTED_DIR = BASE_DIR / "assets" / "haunted"
CHARACTERS_DIR = HAUNTED_DIR / "characters"
DUMMY_DIR = CHARACTERS_DIR / "dummy"

DUMMY_DIR.mkdir(parents=True, exist_ok=True)


def generate_dummy_layers(size: int = 112) -> dict[str, Image.Image]:
    """Generates all discrete puppet layers for the dummy test rig at the specified resolution."""
    s = size / 112.0
    layers: dict[str, Image.Image] = {}

    # -----------------------------------------------------------------------
    # 0. Grounding Shadow (Grounds actor on horizon rail)
    # -----------------------------------------------------------------------
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Oval shadow pool on the rail
    shadow_box = [int(22 * s), int(102 * s), int(90 * s), int(112 * s)]
    d.ellipse(shadow_box, fill=(20, 20, 25, 140), outline=(10, 10, 15, 180), width=max(1, int(s)))
    layers["shadow"] = img

    # -----------------------------------------------------------------------
    # 1. Torso & Jacket (Royal Blue with Dark Navy stroke, no arms/neck)
    # -----------------------------------------------------------------------
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    torso_pts = [
        (int(22 * s), int(112 * s)),
        (int(26 * s), int(84 * s)),
        (int(42 * s), int(76 * s)),
        (int(56 * s), int(84 * s)),  # Collar dip
        (int(70 * s), int(76 * s)),
        (int(86 * s), int(84 * s)),
        (int(90 * s), int(112 * s)),
    ]
    # Royal Blue fill
    d.polygon(torso_pts, fill=(35, 75, 185, 255), outline=(15, 30, 80, 255))
    # Lapel seams
    d.line([(int(42 * s), int(76 * s)), (int(56 * s), int(110 * s)), (int(70 * s), int(76 * s))],
           fill=(15, 30, 80, 255), width=max(1, int(2 * s)))
    # Central jacket button (Yellow gold accent)
    d.ellipse([int(54 * s), int(92 * s), int(58 * s), int(96 * s)], fill=(255, 215, 0, 255), outline=(180, 140, 0, 255))
    layers["torso"] = img

    # -----------------------------------------------------------------------
    # 2. Neck Column (Warm Sand with Dark Sepia stroke)
    # -----------------------------------------------------------------------
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    neck_box = [int(48 * s), int(64 * s), int(64 * s), int(78 * s)]
    d.rectangle(neck_box, fill=(225, 180, 130, 255), outline=(80, 50, 25, 255), width=max(1, int(1.5 * s)))
    layers["neck"] = img

    # -----------------------------------------------------------------------
    # 3. Head & Skull (Coral Peach with Dark Umber stroke, blank canvas)
    # -----------------------------------------------------------------------
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Ears
    d.ellipse([int(31 * s), int(42 * s), int(37 * s), int(54 * s)], fill=(225, 150, 110, 255), outline=(110, 40, 25, 255), width=max(1, int(s)))
    d.ellipse([int(75 * s), int(42 * s), int(81 * s), int(54 * s)], fill=(225, 150, 110, 255), outline=(110, 40, 25, 255), width=max(1, int(s)))
    # Face silhouette (No eyes, no mouth)
    d.ellipse([int(35 * s), int(24 * s), int(77 * s), int(68 * s)], fill=(245, 155, 115, 255), outline=(110, 40, 25, 255), width=max(1, int(2 * s)))
    # Test rig cap / hair band (Slate Grey)
    d.chord([int(35 * s), int(18 * s), int(77 * s), int(42 * s)], 180, 360, fill=(70, 80, 95, 255), outline=(35, 45, 55, 255), width=max(1, int(s)))
    # Nose (minimalist triangle marker)
    d.polygon([(int(56 * s), int(46 * s)), (int(53 * s), int(52 * s)), (int(59 * s), int(52 * s))], fill=(215, 130, 95, 255), outline=(110, 40, 25, 255))
    layers["head"] = img

    # -----------------------------------------------------------------------
    # 4. Eyes (Electric Cyan with Ink Black outline & pupils)
    # -----------------------------------------------------------------------
    # 4A. Open
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Left eye
    d.ellipse([int(42 * s), int(40 * s), int(49 * s), int(47 * s)], fill=(0, 225, 245, 255), outline=(10, 20, 30, 255), width=max(1, int(s)))
    d.ellipse([int(44 * s), int(42 * s), int(47 * s), int(45 * s)], fill=(10, 20, 30, 255))
    # Right eye
    d.ellipse([int(63 * s), int(40 * s), int(70 * s), int(47 * s)], fill=(0, 225, 245, 255), outline=(10, 20, 30, 255), width=max(1, int(s)))
    d.ellipse([int(65 * s), int(42 * s), int(68 * s), int(45 * s)], fill=(10, 20, 30, 255))
    layers["eyes_open"] = img

    # 4B. Half
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Left half eye
    d.rectangle([int(42 * s), int(43 * s), int(49 * s), int(47 * s)], fill=(0, 225, 245, 255), outline=(10, 20, 30, 255), width=max(1, int(s)))
    d.ellipse([int(44 * s), int(44 * s), int(47 * s), int(46 * s)], fill=(10, 20, 30, 255))
    # Right half eye
    d.rectangle([int(63 * s), int(43 * s), int(70 * s), int(47 * s)], fill=(0, 225, 245, 255), outline=(10, 20, 30, 255), width=max(1, int(s)))
    d.ellipse([int(65 * s), int(44 * s), int(68 * s), int(46 * s)], fill=(10, 20, 30, 255))
    layers["eyes_half"] = img

    # 4C. Closed
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Curved slit arcs
    d.arc([int(42 * s), int(41 * s), int(49 * s), int(47 * s)], 0, 180, fill=(10, 20, 30, 255), width=max(1, int(2 * s)))
    d.arc([int(63 * s), int(41 * s), int(70 * s), int(47 * s)], 0, 180, fill=(10, 20, 30, 255), width=max(1, int(2 * s)))
    layers["eyes_closed"] = img

    # -----------------------------------------------------------------------
    # 5. Viseme Mouths (Ruby Crimson with Deep Wine stroke)
    # -----------------------------------------------------------------------
    # 5A. mouth_neutral (Rest / M, B, P: closed horizontal slit)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(50 * s), int(58 * s)), (int(62 * s), int(58 * s))], fill=(210, 30, 65, 255), width=max(1, int(2.5 * s)))
    d.line([(int(52 * s), int(58 * s)), (int(60 * s), int(58 * s))], fill=(90, 10, 25, 255), width=max(1, int(s)))
    layers["mouth_neutral"] = img

    # 5B. mouth_a (Open 'A' viseme: tall vertical oval cavity)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(52 * s), int(55 * s), int(60 * s), int(63 * s)], fill=(210, 30, 65, 255), outline=(90, 10, 25, 255), width=max(1, int(s)))
    # Inner dark oral cavity & tongue
    d.ellipse([int(54 * s), int(56 * s), int(58 * s), int(61 * s)], fill=(60, 5, 15, 255))
    layers["mouth_a"] = img

    # 5C. mouth_o (Rounded 'O' viseme: puckered circle ring)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(53 * s), int(55 * s), int(59 * s), int(61 * s)], fill=(210, 30, 65, 255), outline=(90, 10, 25, 255), width=max(1, int(s)))
    d.ellipse([int(54 * s), int(56 * s), int(58 * s), int(60 * s)], fill=(50, 5, 10, 255))
    layers["mouth_o"] = img

    # 5D. mouth_e (Wide 'E' viseme: wide horizontal smile with exposed teeth)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([int(48 * s), int(56 * s), int(64 * s), int(60 * s)], fill=(210, 30, 65, 255), outline=(90, 10, 25, 255), width=max(1, int(s)))
    # White teeth strip
    d.rectangle([int(50 * s), int(57 * s), int(62 * s), int(59 * s)], fill=(255, 255, 255, 255))
    layers["mouth_e"] = img

    # 5E. mouth_f (Fricative 'F' viseme: upper teeth tucking on lower lip)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([int(50 * s), int(56 * s), int(62 * s), int(60 * s)], fill=(210, 30, 65, 255), outline=(90, 10, 25, 255), width=max(1, int(s)))
    # Upper teeth row
    d.rectangle([int(51 * s), int(56 * s), int(61 * s), int(58 * s)], fill=(250, 250, 250, 255))
    layers["mouth_f"] = img

    # 5F. mouth_talk (Generic talk fallback)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(51 * s), int(55 * s), int(61 * s), int(62 * s)], fill=(210, 30, 65, 255), outline=(90, 10, 25, 255), width=max(1, int(s)))
    d.rectangle([int(53 * s), int(56 * s), int(59 * s), int(58 * s)], fill=(250, 250, 250, 255))
    layers["mouth_talk"] = img

    # 5G. mouth_smirk (Emotional smirk)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.line([(int(50 * s), int(59 * s)), (int(57 * s), int(58 * s)), (int(63 * s), int(55 * s))],
           fill=(210, 30, 65, 255), width=max(1, int(2.5 * s)))
    layers["mouth_smirk"] = img

    # 5H. mouth_gasp (Shock / gasp cavity)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([int(52 * s), int(54 * s), int(60 * s), int(64 * s)], fill=(50, 5, 10, 255), outline=(90, 10, 25, 255), width=max(1, int(s)))
    layers["mouth_gasp"] = img

    # -----------------------------------------------------------------------
    # 6. Arms & Hands (High-contrast Emerald / Violet / Amber)
    # -----------------------------------------------------------------------
    # 6A. arm_rest (Left = Emerald Green, Right = Deep Violet, Hands = Golden Amber)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Left forearm (Emerald Green)
    d.polygon([(int(22 * s), int(86 * s)), (int(16 * s), int(106 * s)), (int(26 * s), int(106 * s)), (int(30 * s), int(88 * s))],
              fill=(30, 175, 110, 255), outline=(10, 60, 35, 255), width=max(1, int(s)))
    # Left hand (Golden Amber resting forward)
    d.ellipse([int(15 * s), int(102 * s), int(29 * s), int(112 * s)], fill=(250, 195, 40, 255), outline=(140, 100, 15, 255), width=max(1, int(s)))

    # Right forearm (Deep Violet)
    d.polygon([(int(90 * s), int(86 * s)), (int(96 * s), int(106 * s)), (int(86 * s), int(106 * s)), (int(82 * s), int(88 * s))],
              fill=(155, 45, 180, 255), outline=(60, 15, 75, 255), width=max(1, int(s)))
    # Right hand (Golden Amber resting forward)
    d.ellipse([int(83 * s), int(102 * s), int(97 * s), int(112 * s)], fill=(250, 195, 40, 255), outline=(140, 100, 15, 255), width=max(1, int(s)))
    layers["arm_rest"] = img

    # 6B. arm_deal (Left arm reaching with card)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Left extended arm
    d.polygon([(int(24 * s), int(84 * s)), (int(6 * s), int(96 * s)), (int(10 * s), int(104 * s)), (int(28 * s), int(88 * s))],
              fill=(30, 175, 110, 255), outline=(10, 60, 35, 255), width=max(1, int(s)))
    # Dealing hand holding card
    d.ellipse([int(4 * s), int(94 * s), int(14 * s), int(106 * s)], fill=(250, 195, 40, 255), outline=(140, 100, 15, 255), width=max(1, int(s)))
    # Dealt miniature white card with gold border
    d.rectangle([int(2 * s), int(86 * s), int(14 * s), int(104 * s)], fill=(255, 255, 255, 255), outline=(212, 175, 55, 255), width=max(1, int(s)))
    # Right rested arm
    d.polygon([(int(90 * s), int(86 * s)), (int(96 * s), int(106 * s)), (int(86 * s), int(106 * s)), (int(82 * s), int(88 * s))],
              fill=(155, 45, 180, 255), outline=(60, 15, 75, 255), width=max(1, int(s)))
    d.ellipse([int(83 * s), int(102 * s), int(97 * s), int(112 * s)], fill=(250, 195, 40, 255), outline=(140, 100, 15, 255), width=max(1, int(s)))
    layers["arm_deal"] = img

    # 6C. arm_peek (Right hand peeking hole card)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Left rested arm
    d.polygon([(int(22 * s), int(86 * s)), (int(16 * s), int(106 * s)), (int(26 * s), int(106 * s)), (int(30 * s), int(88 * s))],
              fill=(30, 175, 110, 255), outline=(10, 60, 35, 255), width=max(1, int(s)))
    d.ellipse([int(15 * s), int(102 * s), int(29 * s), int(112 * s)], fill=(250, 195, 40, 255), outline=(140, 100, 15, 255), width=max(1, int(s)))
    # Right arm angled upward for card peek
    d.polygon([(int(90 * s), int(84 * s)), (int(74 * s), int(98 * s)), (int(78 * s), int(106 * s)), (int(94 * s), int(88 * s))],
              fill=(155, 45, 180, 255), outline=(60, 15, 75, 255), width=max(1, int(s)))
    # Right hand curling fingers
    d.ellipse([int(70 * s), int(96 * s), int(82 * s), int(108 * s)], fill=(250, 195, 40, 255), outline=(140, 100, 15, 255), width=max(1, int(s)))
    # Bent card corner
    d.polygon([(int(78 * s), int(102 * s)), (int(88 * s), int(94 * s)), (int(86 * s), int(106 * s))], fill=(240, 240, 245, 255), outline=(180, 40, 40, 255))
    layers["arm_peek"] = img

    # -----------------------------------------------------------------------
    # 7. Bust (Pre-composited reference portrait)
    # -----------------------------------------------------------------------
    bust = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    for key in ("shadow", "torso", "neck", "head", "eyes_open", "mouth_neutral", "arm_rest"):
        bust.alpha_composite(layers[key])
    layers["bust"] = bust

    return layers


def build_and_save_all():
    """Generates and writes 1x and 2x PNG assets for the dummy character."""
    print("Generating 1x (112x112) dummy puppet layers...")
    layers_1x = generate_dummy_layers(size=112)
    for name, img in layers_1x.items():
        out_path = DUMMY_DIR / f"{name}.png"
        img.save(out_path, format="PNG")
        print(f"  [1x] Saved {out_path.name}")

    print("\nGenerating 2x (224x224) HiDPI dummy puppet layers...")
    layers_2x = generate_dummy_layers(size=224)
    for name, img in layers_2x.items():
        out_path = DUMMY_DIR / f"{name}_2x.png"
        img.save(out_path, format="PNG")
        print(f"  [2x] Saved {out_path.name}")

    print(f"\nAll dummy puppet assets successfully generated in: {DUMMY_DIR}")


if __name__ == "__main__":
    build_and_save_all()
