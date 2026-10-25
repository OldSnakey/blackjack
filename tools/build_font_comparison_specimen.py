"""
Generate comprehensive typography specimen sheet comparing all candidate pixel fonts:
- m5x7
- m6x11
- m6x11plus
- BoldPixels
- Round9x13

Includes:
1. Pangram: "The quick brown fox jumps over the lazy dog" (mixed-case and uppercase)
2. Numerals: 0 1 2 3 4 5 6 7 8 9 (evaluating zero open/slash, spacing, height)
3. Common symbols: $ ? ! + - / * = % & # @ : ; . , ( ) [ ]
4. Blackjack UI Context: BANKROLL: $1,000 | BET: $50 | Dealer Wins: 0 | Hand: 10 + ? | [Hit] [Stand]
Both at 1x (16px) and 2x (32px) scales.
"""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "assets" / "fonts"
ARTIFACT_DIR = Path(r"C:\Users\wrehm\.gemini\antigravity-ide\brain\4cc8d8d2-c72e-4a67-8d44-37320d173939")


FONTS = [
    {
        "name": "m5x7",
        "file": "m5x7.ttf",
        "desc": "5x7 Grid | Compact, clean, slender pixel workhorse font",
        "badge": "COMPACT WORKHORSE",
        "sizes": [16, 32],
    },
    {
        "name": "m6x11",
        "file": "m6x11.ttf",
        "desc": "6x11 Grid | Tall, proportional, elegant mixed-case pixel font with open 0s",
        "badge": "NEW ADDITION (TALL)",
        "sizes": [16, 32],
    },
    {
        "name": "m6x11plus",
        "file": "m6x11plus.ttf",
        "desc": "6x11 Grid | Enhanced 6x11 with extended punctuation, spacing & symbols",
        "badge": "NEW ADDITION (ENHANCED)",
        "sizes": [16, 32],
    },
    {
        "name": "BoldPixels",
        "file": "BoldPixels.ttf",
        "desc": "Arcade Grid | Punchy, chunky retro arcade font with wide-open 0s",
        "badge": "CHUNKY ARCADE",
        "sizes": [16, 32],
    },
    {
        "name": "Round9x13",
        "file": "Round9x13.ttf",
        "desc": "9x13 Grid | Rounded all-caps display font with slashed zero",
        "badge": "SLASHED-ZERO DISPLAY",
        "sizes": [16, 32],
    },
]


def build_comparison_image() -> Image.Image:
    # Canvas dimensions
    width = 1180
    section_height = 290
    top_header_height = 90
    footer_height = 60
    total_height = top_header_height + len(FONTS) * section_height + footer_height

    # Dark casino noir palette
    bg_color = (14, 20, 16)
    panel_bg = (19, 28, 22)
    panel_border = (38, 56, 44)
    gold_accent = (235, 194, 75)
    gold_dim = (180, 145, 55)
    text_white = (244, 244, 244)
    text_cyan = (90, 220, 200)
    badge_bg = (32, 50, 38)
    badge_border = (60, 95, 70)

    img = Image.new("RGB", (width, total_height), bg_color)
    draw = ImageDraw.Draw(img)

    # Standard labeling font for specimen frame headers
    lbl_font_bold = ImageFont.truetype(str(FONTS_DIR / "m6x11.ttf"), 18)
    lbl_font_sm = ImageFont.truetype(str(FONTS_DIR / "m5x7.ttf"), 14)
    lbl_font_badge = ImageFont.truetype(str(FONTS_DIR / "m5x7.ttf"), 14)

    # Top Master Banner
    draw.rectangle([16, 14, width - 16, top_header_height - 10], fill=(22, 34, 26), outline=(48, 74, 56), width=1)
    draw.text((32, 24), "BLACKJACK TYPOGRAPHY COMPARISON SPECIMEN", font=lbl_font_bold, fill=gold_accent)
    draw.text(
        (32, 50),
        "Pangram ('brown fox'), Numerals (0-9 with Zero comparison), Symbols ($ ? ! + - / =), and Casino UI Readouts",
        font=lbl_font_sm,
        fill=(160, 185, 170),
    )

    y_offset = top_header_height

    for idx, f_info in enumerate(FONTS):
        font_path = FONTS_DIR / f_info["file"]
        sec_top = y_offset
        sec_bottom = sec_top + section_height - 12

        # Section Card Background
        draw.rectangle([16, sec_top, width - 16, sec_bottom], fill=panel_bg, outline=panel_border, width=1)

        # Header bar for this font
        draw.rectangle([17, sec_top + 1, width - 17, sec_top + 34], fill=(24, 38, 29))
        draw.line([17, sec_top + 34, width - 17, sec_top + 34], fill=panel_border, width=1)

        # Font title & badge
        draw.text((28, sec_top + 8), f"{idx + 1}. {f_info['file']}  ({f_info['name']})", font=lbl_font_bold, fill=gold_accent)
        draw.text((320, sec_top + 11), f"-- {f_info['desc']}", font=lbl_font_sm, fill=(160, 185, 170))

        # Badge tag on the right
        badge_text = f"[{f_info['badge']}]"
        badge_w = 175
        draw.rectangle([width - badge_w - 28, sec_top + 6, width - 28, sec_top + 28], fill=badge_bg, outline=badge_border)
        draw.text((width - badge_w - 20, sec_top + 9), badge_text, font=lbl_font_badge, fill=gold_accent)

        # Load font at 16px and 32px
        font_16 = ImageFont.truetype(str(font_path), 16)
        font_32 = ImageFont.truetype(str(font_path), 32)

        # ---- Row 1: Size 16 (1x Standard HUD Scale) ----
        r1_y = sec_top + 46
        draw.rectangle([28, r1_y - 2, 85, r1_y + 16], fill=(30, 48, 36), outline=(48, 76, 58))
        draw.text((32, r1_y - 1), "@ 16 (1x):", font=lbl_font_sm, fill=gold_dim)

        # 16px Pangram
        draw.text((95, r1_y - 1), "The quick brown fox jumps over the lazy dog.", font=font_16, fill=text_white)

        # 16px Numerals & Symbols
        r2_y = r1_y + 24
        draw.text((95, r2_y), "0 1 2 3 4 5 6 7 8 9", font=font_16, fill=gold_accent)
        draw.text((260, r2_y), " |  $ ? ! + - / * = % & # @ : ; . , [ ] ( )", font=font_16, fill=(180, 205, 195))

        # 16px Realistic Casino Readout
        r3_y = r2_y + 24
        draw.text(
            (95, r3_y),
            "BANKROLL: $1,000  |  BET: $50  |  Dealer Wins: 0  |  10 + ?  |  [Hit] [Stand] [Double]",
            font=font_16,
            fill=text_cyan,
        )

        # Divider between 16 and 32
        div_y = r3_y + 28
        draw.line([28, div_y, width - 28, div_y], fill=(30, 44, 34), width=1)

        # ---- Row 2: Size 32 (2x High-Impact Score & Plaque Scale) ----
        r4_y = div_y + 10
        draw.rectangle([28, r4_y - 2, 85, r4_y + 16], fill=(42, 38, 22), outline=(78, 68, 38))
        draw.text((32, r4_y - 1), "@ 32 (2x):", font=lbl_font_sm, fill=gold_accent)

        # 32px Pangram
        draw.text((95, r4_y - 4), "The quick brown fox jumps over the lazy dog.", font=font_32, fill=text_white)

        # 32px Numerals & Symbols & Game Snippet
        r5_y = r4_y + 42
        draw.text((95, r5_y), "0 1 2 3 4 5 6 7 8 9  |  $ ? + - :  |  BANKROLL: $1,000 | 10 + ?", font=font_32, fill=gold_accent)

        y_offset += section_height

    # Footer note
    foot_y = total_height - footer_height + 14
    draw.text(
        (28, foot_y),
        "* Note: Round9x13 is an uppercase-only font; lowercase letters render as small capitals. Observe 0 glyph openness across fonts.",
        font=lbl_font_sm,
        fill=(130, 160, 140),
    )

    return img


def main():
    img = build_comparison_image()

    # Save to artifact directory
    out_artifact = ARTIFACT_DIR / "font_comparison_specimen_sheet.png"
    img.save(str(out_artifact), "PNG")
    print(f"SAVED: {out_artifact}")

    # Also save to verification/
    verif_dir = BASE_DIR / "verification"
    if verif_dir.exists():
        out_verif = verif_dir / "font_comparison_specimen_sheet.png"
        img.save(str(out_verif), "PNG")
        print(f"SAVED: {out_verif}")


if __name__ == "__main__":
    main()
