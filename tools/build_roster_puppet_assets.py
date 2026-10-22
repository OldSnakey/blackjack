"""
Procedural Asset Pipeline: Roster Puppet Conversion and New Characters (Selene & Vladimir).

1. Converts remaining characters (Julian, Malphas, Uriel, Mortimer) to full 19-layer discrete puppet sets:
   - Synthesizes grounding contact shadow (shadow, shadow_2x).
   - Generates matching neck articulation pillar (neck, neck_2x).
   - Synthesizes distinct phonetic visemes (mouth_a, mouth_o, mouth_e, mouth_f, plus _2x) matching character mouth aesthetics.
2. Generates complete 19-layer discrete puppet strata in 2x (224x224) and 1x (112x112) for new dealer personalities:
   - Selene: Cyberpunk 2088 croupier with holographic cyan visor, neon trim, and chrome dealer arms.
   - Vladimir: Crimson Nocturne Victorian vampire count with aristocratic fangs, high velvet collar, and pale hands.
"""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = BASE_DIR / "assets" / "haunted" / "characters"


def create_grounding_shadow(width: int = 224, height: int = 224, radius_x: int = 65, radius_y: int = 14) -> Image.Image:
    """Creates a soft feathered contact shadow at the base of the actor."""
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = width // 2, height - 16
    bbox = [cx - radius_x, cy - radius_y, cx + radius_x, cy + radius_y]
    draw.ellipse(bbox, fill=(10, 10, 15, 140))
    return img.filter(ImageFilter.GaussianBlur(radius=4))


def generate_missing_visemes_for_character(char_dir: Path, mouth_color: tuple[int, int, int, int]):
    """
    Generates mouth_a, mouth_o, mouth_e, mouth_f in 1x and 2x if missing,
    deriving authentic apertures from character palette.
    """
    talk_path = char_dir / "mouth_talk_2x.png"
    neutral_path = char_dir / "mouth_neutral_2x.png"

    # Base center for mouth in 2x coordinates (typically around (112, 95))
    mc_x, mc_y = 112, 95

    # If neutral mouth exists, find its centroid
    if neutral_path.exists():
        with Image.open(neutral_path) as n_img:
            bbox = n_img.getbbox()
            if bbox:
                mc_x = (bbox[0] + bbox[2]) // 2
                mc_y = (bbox[1] + bbox[3]) // 2

    # Viseme dimensions (rx, ry) in 2x
    viseme_shapes = {
        "mouth_a": (7, 6, "ellipse"),    # Open round aperture
        "mouth_o": (5, 6, "ellipse"),    # Narrow rounded O
        "mouth_e": (9, 3, "rounded_rect"), # Wide smile/dental slit
        "mouth_f": (7, 2, "line"),       # Labiodental tuck
    }

    for vname, (rx, ry, shape) in viseme_shapes.items():
        p2x = char_dir / f"{vname}_2x.png"
        p1x = char_dir / f"{vname}.png"

        img2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        d2x = ImageDraw.Draw(img2x)

        bbox = [mc_x - rx, mc_y - ry, mc_x + rx, mc_y + ry]
        if shape == "ellipse":
            d2x.ellipse(bbox, fill=mouth_color, outline=(20, 10, 15, 230), width=1)
        elif shape == "rounded_rect":
            d2x.rounded_rectangle(bbox, radius=2, fill=mouth_color, outline=(20, 10, 15, 230), width=1)
        else:
            d2x.line([(mc_x - rx, mc_y), (mc_x + rx, mc_y)], fill=mouth_color, width=2)

        img2x.save(p2x)
        img1x = img2x.resize((112, 112), Image.Resampling.BILINEAR)
        img1x.save(p1x)


def upgrade_existing_character_to_puppet(char_id: str, neck_color: tuple[int, int, int, int], mouth_color: tuple[int, int, int, int]):
    """Adds missing puppet layers to an existing character directory."""
    cdir = CHARACTERS_DIR / char_id
    if not cdir.exists():
        return

    # 1. Shadow
    s2x_path = cdir / "shadow_2x.png"
    s1x_path = cdir / "shadow.png"
    if not s2x_path.exists():
        s2x = create_grounding_shadow(224, 224)
        s2x.save(s2x_path)
        s1x = s2x.resize((112, 112), Image.Resampling.BILINEAR)
        s1x.save(s1x_path)

    # 2. Neck
    n2x_path = cdir / "neck_2x.png"
    n1x_path = cdir / "neck.png"
    if not n2x_path.exists():
        neck2x = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        dneck = ImageDraw.Draw(neck2x)
        # Neck column: (103, 105) to (121, 132)
        dneck.rectangle([104, 106, 120, 130], fill=neck_color)
        neck2x.save(n2x_path)
        neck1x = neck2x.resize((112, 112), Image.Resampling.BILINEAR)
        neck1x.save(n1x_path)

    # 3. Visemes
    generate_missing_visemes_for_character(cdir, mouth_color)


def build_selene_cyberpunk_puppet():
    """Generates all 19 discrete layers for Selene (Cyberpunk Croupier)."""
    sdir = CHARACTERS_DIR / "selene"
    sdir.mkdir(parents=True, exist_ok=True)

    cyan = (0, 229, 255, 255)
    neon_pink = (255, 64, 129, 255)
    dark_synth = (18, 22, 32, 255)
    metal_gray = (90, 105, 120, 255)
    skin = (235, 195, 175, 255)

    layers: dict[str, Image.Image] = {}

    # Shadow
    layers["shadow"] = create_grounding_shadow(224, 224, radius_x=68, radius_y=15)

    # Neck
    neck = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dn = ImageDraw.Draw(neck)
    dn.rectangle([105, 108, 119, 132], fill=skin)
    # Cyber choker
    dn.rectangle([105, 120, 119, 124], fill=dark_synth)
    dn.line([(105, 122), (119, 122)], fill=cyan, width=1)
    layers["neck"] = neck

    # Torso (Cyberpunk synth-leather jacket with neon piping)
    torso = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dt = ImageDraw.Draw(torso)
    # Jacket body
    dt.polygon([(78, 224), (88, 134), (112, 142), (136, 134), (146, 224)], fill=dark_synth)
    # Lapels
    dt.polygon([(92, 136), (112, 168), (112, 140)], fill=metal_gray)
    dt.polygon([(132, 136), (112, 168), (112, 140)], fill=metal_gray)
    # Glowing neon lines
    dt.line([(88, 140), (80, 224)], fill=cyan, width=2)
    dt.line([(136, 140), (144, 224)], fill=cyan, width=2)
    dt.line([(100, 150), (100, 224)], fill=neon_pink, width=1)
    dt.line([(124, 150), (124, 224)], fill=neon_pink, width=1)
    layers["torso"] = torso

    # Head (sleek asymmetric bob haircut with glowing cyber visor)
    head = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dh = ImageDraw.Draw(head)
    # Face base
    dh.polygon([(92, 65), (132, 65), (128, 104), (112, 118), (96, 104)], fill=skin)
    # Hair
    dh.polygon([(84, 52), (140, 52), (142, 105), (134, 118), (130, 75), (94, 75), (86, 120)], fill=(30, 32, 45, 255))
    # Visor band
    dh.rectangle([90, 74, 134, 88], fill=(10, 20, 30, 240), outline=cyan, width=1)
    layers["head"] = head

    # Eyes (glowing digital readout behind visor)
    for estate, text in (("open", "●  ●"), ("half", "–  –"), ("closed", "—  —")):
        eimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        de = ImageDraw.Draw(eimg)
        if estate == "open":
            de.rectangle([98, 78, 106, 84], fill=cyan)
            de.rectangle([118, 78, 126, 84], fill=cyan)
        elif estate == "half":
            de.line([(98, 81), (106, 81)], fill=cyan, width=2)
            de.line([(118, 81), (126, 81)], fill=cyan, width=2)
        else:
            de.line([(98, 83), (106, 83)], fill=(0, 150, 180, 200), width=1)
            de.line([(118, 83), (126, 83)], fill=(0, 150, 180, 200), width=1)
        layers[f"eyes_{estate}"] = eimg

    # Mouth states
    for mname, (rx, ry, shape) in (
        ("neutral", (5, 2, "line")),
        ("talk", (6, 4, "rect")),
        ("a", (6, 5, "ellipse")),
        ("o", (4, 5, "ellipse")),
        ("e", (8, 3, "rect")),
        ("f", (6, 1, "line")),
        ("smirk", (6, 2, "smile")),
        ("gasp", (5, 6, "ellipse")),
    ):
        mimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        dm = ImageDraw.Draw(mimg)
        bx = [112 - rx, 102 - ry, 112 + rx, 102 + ry]
        if shape == "ellipse":
            dm.ellipse(bx, fill=neon_pink, outline=(40, 10, 20, 220), width=1)
        elif shape == "rect":
            dm.rounded_rectangle(bx, radius=1, fill=neon_pink, outline=(40, 10, 20, 220), width=1)
        elif shape == "smile":
            dm.arc([106, 99, 118, 105], start=0, end=180, fill=neon_pink, width=2)
        else:
            dm.line([(112 - rx, 102), (112 + rx, 102)], fill=neon_pink, width=2)
        layers[f"mouth_{mname}"] = mimg

    # Arms (rest, deal, peek) - Chrome cybernetic left arm, sleek jacketed right arm
    for astate in ("rest", "deal", "peek"):
        aimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        da = ImageDraw.Draw(aimg)
        # Left arm (cyber shoe holder)
        da.polygon([(65, 145), (86, 136), (72, 195), (55, 190)], fill=metal_gray)
        # Cyber shoe deck
        da.rectangle([45, 175, 70, 205], fill=(20, 30, 45, 255), outline=cyan, width=1)

        # Right arm
        if astate == "rest":
            da.polygon([(138, 136), (158, 145), (168, 205), (150, 210)], fill=dark_synth)
            da.rectangle([148, 205, 166, 218], fill=skin)
        elif astate == "deal":
            da.polygon([(138, 136), (158, 145), (135, 195), (120, 185)], fill=dark_synth)
            da.rectangle([115, 185, 135, 200], fill=skin)
            # Swept card
            da.rectangle([105, 188, 130, 218], fill=(245, 245, 250, 255), outline=cyan, width=1)
        else: # peek
            da.polygon([(138, 136), (158, 145), (140, 175), (124, 165)], fill=dark_synth)
            da.rectangle([120, 160, 138, 174], fill=skin)
            # Lifted card corner
            da.polygon([(115, 155), (130, 150), (132, 172), (117, 175)], fill=(255, 255, 255, 255), outline=neon_pink, width=1)

        layers[f"arm_{astate}"] = aimg

    # Bust composite
    bust = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    for k in ("shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
        bust.alpha_composite(layers[k])
    layers["bust"] = bust

    # Save 2x and 1x
    for name, img2x in layers.items():
        img2x.save(sdir / f"{name}_2x.png")
        img1x = img2x.resize((112, 112), Image.Resampling.BILINEAR)
        img1x.save(sdir / f"{name}.png")


def build_vladimir_vampire_puppet():
    """Generates all 19 discrete layers for Vladimir (Victorian Vampire Count)."""
    vdir = CHARACTERS_DIR / "vladimir"
    vdir.mkdir(parents=True, exist_ok=True)

    crimson = (198, 40, 40, 255)
    gold = (218, 165, 32, 255)
    velvet_black = (15, 12, 18, 255)
    pale_skin = (245, 240, 245, 255)
    ruby = (220, 20, 60, 255)

    layers: dict[str, Image.Image] = {}

    # Shadow
    layers["shadow"] = create_grounding_shadow(224, 224, radius_x=66, radius_y=14)

    # Neck
    neck = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dn = ImageDraw.Draw(neck)
    dn.rectangle([105, 106, 119, 130], fill=pale_skin)
    # Victorian ruffled cravat
    dn.polygon([(104, 120), (120, 120), (115, 134), (109, 134)], fill=(240, 240, 245, 255))
    layers["neck"] = neck

    # Torso (Victorian black waistcoat, crimson silk lining, high standing collar)
    torso = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dt = ImageDraw.Draw(torso)
    # High standing collar winging behind neck
    dt.polygon([(82, 142), (94, 98), (108, 130)], fill=crimson)
    dt.polygon([(142, 142), (130, 98), (116, 130)], fill=crimson)
    # Coat
    dt.polygon([(78, 224), (86, 132), (112, 140), (138, 132), (146, 224)], fill=velvet_black)
    # Crimson velvet vest
    dt.polygon([(92, 136), (112, 172), (132, 136), (126, 224), (98, 224)], fill=crimson)
    # Gold pocket watch chain
    dt.arc([100, 180, 124, 196], start=0, end=180, fill=gold, width=2)
    # Ruby brooch
    dt.ellipse([109, 132, 115, 138], fill=ruby, outline=gold, width=1)
    layers["torso"] = torso

    # Head (aristocratic pale features, slicked dark hair with widows peak)
    head = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    dh = ImageDraw.Draw(head)
    # Face base
    dh.polygon([(94, 66), (130, 66), (126, 102), (112, 116), (98, 102)], fill=pale_skin)
    # Dark slicked hair
    dh.polygon([(90, 68), (134, 68), (136, 95), (130, 60), (112, 70), (94, 60), (88, 95)], fill=(20, 18, 25, 255))
    # Elegant arched brows
    dh.line([(96, 75), (106, 73)], fill=(30, 25, 35, 255), width=2)
    dh.line([(118, 73), (128, 75)], fill=(30, 25, 35, 255), width=2)
    layers["head"] = head

    # Eyes (piercing crimson eyes)
    for estate in ("open", "half", "closed"):
        eimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        de = ImageDraw.Draw(eimg)
        if estate == "open":
            de.ellipse([98, 77, 105, 83], fill=ruby, outline=(30, 10, 15, 255), width=1)
            de.ellipse([119, 77, 126, 83], fill=ruby, outline=(30, 10, 15, 255), width=1)
        elif estate == "half":
            de.line([(98, 80), (105, 80)], fill=ruby, width=2)
            de.line([(119, 80), (126, 80)], fill=ruby, width=2)
        else:
            de.line([(98, 82), (105, 82)], fill=(60, 20, 30, 255), width=1)
            de.line([(119, 82), (126, 82)], fill=(60, 20, 30, 255), width=1)
        layers[f"eyes_{estate}"] = eimg

    # Mouth states (subtle fangs on open/talk/gasp visemes)
    for mname, (rx, ry, shape) in (
        ("neutral", (5, 2, "line")),
        ("talk", (6, 4, "fangs")),
        ("a", (6, 5, "fangs")),
        ("o", (4, 5, "ellipse")),
        ("e", (8, 3, "fangs")),
        ("f", (6, 1, "line")),
        ("smirk", (7, 2, "smile")),
        ("gasp", (5, 6, "fangs")),
    ):
        mimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        dm = ImageDraw.Draw(mimg)
        bx = [112 - rx, 101 - ry, 112 + rx, 101 + ry]
        if shape == "ellipse":
            dm.ellipse(bx, fill=ruby, outline=(40, 10, 20, 220), width=1)
        elif shape == "fangs":
            dm.rounded_rectangle(bx, radius=1, fill=(80, 10, 20, 255))
            # Two tiny white fangs
            dm.polygon([(110, 101 - ry), (111, 101 - ry + 4), (109, 101 - ry)], fill=(255, 255, 255, 255))
            dm.polygon([(114, 101 - ry), (115, 101 - ry + 4), (113, 101 - ry)], fill=(255, 255, 255, 255))
        elif shape == "smile":
            dm.arc([106, 98, 118, 104], start=0, end=180, fill=ruby, width=2)
        else:
            dm.line([(112 - rx, 101), (112 + rx, 101)], fill=ruby, width=2)
        layers[f"mouth_{mname}"] = mimg

    # Arms (rest, deal, peek) - Pale hands with gold ring
    for astate in ("rest", "deal", "peek"):
        aimg = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
        da = ImageDraw.Draw(aimg)
        # Left arm holding gothic velvet card shoe
        da.polygon([(66, 142), (86, 134), (72, 196), (54, 192)], fill=velvet_black)
        da.rectangle([46, 178, 70, 208], fill=crimson, outline=gold, width=1)
        # Pale hand holding shoe
        da.rectangle([64, 190, 76, 204], fill=pale_skin)
        # Gold ring
        da.rectangle([66, 196, 74, 198], fill=gold)

        # Right arm
        if astate == "rest":
            da.polygon([(138, 134), (158, 142), (168, 204), (150, 210)], fill=velvet_black)
            da.rectangle([148, 204, 166, 218], fill=pale_skin)
        elif astate == "deal":
            da.polygon([(138, 134), (158, 142), (136, 194), (120, 184)], fill=velvet_black)
            da.rectangle([115, 184, 135, 198], fill=pale_skin)
            # Swept playing card
            da.rectangle([106, 186, 132, 216], fill=(255, 255, 255, 255), outline=ruby, width=1)
        else: # peek
            da.polygon([(138, 134), (158, 142), (140, 174), (124, 164)], fill=velvet_black)
            da.rectangle([120, 158, 138, 172], fill=pale_skin)
            da.polygon([(115, 154), (130, 148), (132, 170), (117, 174)], fill=(255, 255, 255, 255), outline=ruby, width=1)

        layers[f"arm_{astate}"] = aimg

    # Bust composite
    bust = Image.new("RGBA", (224, 224), (0, 0, 0, 0))
    for k in ("shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"):
        bust.alpha_composite(layers[k])
    layers["bust"] = bust

    # Save 2x and 1x
    for name, img2x in layers.items():
        img2x.save(vdir / f"{name}_2x.png")
        img1x = img2x.resize((112, 112), Image.Resampling.BILINEAR)
        img1x.save(vdir / f"{name}.png")


def run_pipeline():
    """Runs the full puppet conversion and new character asset generation."""
    print("Upgrading Julian to puppet framework...")
    upgrade_existing_character_to_puppet("julian", neck_color=(235, 190, 160, 255), mouth_color=(190, 40, 50, 255))

    print("Upgrading Malphas to puppet framework...")
    upgrade_existing_character_to_puppet("malphas", neck_color=(80, 25, 25, 255), mouth_color=(255, 50, 20, 255))

    print("Upgrading Uriel to puppet framework...")
    upgrade_existing_character_to_puppet("uriel", neck_color=(245, 230, 210, 255), mouth_color=(220, 100, 120, 255))

    print("Upgrading Mortimer to puppet framework...")
    upgrade_existing_character_to_puppet("mortimer", neck_color=(230, 230, 230, 255), mouth_color=(40, 30, 45, 255))

    print("Building Selene (Cyberpunk Croupier) puppet assets...")
    build_selene_cyberpunk_puppet()

    print("Building Vladimir (Victorian Vampire Count) puppet assets...")
    build_vladimir_vampire_puppet()

    print("Puppet roster asset generation complete!")


if __name__ == "__main__":
    run_pipeline()
