"""
Promotes the 7 selected Tiny5 v3.000 pixel font files into `assets/fonts/`,
normalizes Windows GDI `OS/2` `usWinAscent` (960) and `usWinDescent` (256)
under SIL Open Font License 1.1 so Tkinter renders tight integer line heights
and dead-center button labels without clipping accented Latin or casino suit glyphs,
writes `assets/fonts/Tiny5-OFL.txt`, and removes `assets/fonts/pixel_fonts_to_review/`.
"""

from __future__ import annotations

import shutil
import struct
from pathlib import Path
from PIL import ImageFont

SELECTED_TINY5_FILES: tuple[str, ...] = (
    "Tiny5-Regular.ttf",
    "Tiny5-Bold.ttf",
    "Tiny5-Italic.ttf",
    "Tiny5Duo-Regular.ttf",
    "Tiny5Duo-Bold.ttf",
    "Tiny5SC-Regular.ttf",
    "Tiny5SC-Bold.ttf",
)

TARGET_WIN_ASCENT = 960
TARGET_WIN_DESCENT = 256

SIL_OFL_TEXT = """Copyright (c) 2022-2025, Stefan Schmidt (https://github.com/Gissio/font_Tiny5),
with Reserved Font Name "Tiny5".

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
https://openfontlicense.org

-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical
writer or other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote, endorse or advertise any
Modified Version, except to acknowledge the contribution(s) of the
Copyright Holder(s) and the Author(s) or with their explicit written
permission.

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE FONT SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE FONT SOFTWARE.
"""


def _calc_sfnt_checksum(blob: bytes | bytearray) -> int:
    pad_len = (-len(blob)) % 4
    padded = bytes(blob) + (b"\x00" * pad_len)
    total = 0
    for (word,) in struct.iter_unpack(">I", padded):
        total = (total + word) & 0xFFFFFFFF
    return total


def normalize_ttf_win_metrics(
    raw: bytes,
    win_ascent: int = TARGET_WIN_ASCENT,
    win_descent: int = TARGET_WIN_DESCENT,
) -> bytes:
    """Patches `OS/2.usWinAscent` & `OS/2.usWinDescent` and updates SFNT checksums."""
    buf = bytearray(raw)
    num_tables = struct.unpack(">H", buf[4:6])[0]

    os2_rec_off = None
    os2_off = os2_len = 0
    head_off = None

    for idx in range(num_tables):
        rec = 12 + idx * 16
        tag, _csum, toff, tlen = struct.unpack(">4sIII", buf[rec : rec + 16])
        if tag == b"OS/2":
            os2_rec_off = rec
            os2_off, os2_len = toff, tlen
        elif tag == b"head":
            head_off = toff

    if os2_rec_off is None or head_off is None:
        raise ValueError("Missing OS/2 or head SFNT table")

    # Patch usWinAscent (offset 74) and usWinDescent (offset 76) in OS/2 table
    struct.pack_into(">HH", buf, os2_off + 74, int(win_ascent), int(win_descent))

    # Recompute OS/2 table checksum in table directory
    new_os2_csum = _calc_sfnt_checksum(buf[os2_off : os2_off + os2_len])
    struct.pack_into(">I", buf, os2_rec_off + 4, new_os2_csum)

    # Recompute head.checkSumAdjustment (zero bytes 8..12 of head first per OpenType spec)
    struct.pack_into(">I", buf, head_off + 8, 0)
    whole_csum = _calc_sfnt_checksum(buf)
    check_adj = (0xB1B0AFBA - whole_csum) & 0xFFFFFFFF
    struct.pack_into(">I", buf, head_off + 8, check_adj)

    return bytes(buf)


def promote_tiny5_fonts(fonts_dir: Path | None = None, remove_staging: bool = True) -> list[Path]:
    root_dir = Path(__file__).resolve().parent.parent
    target_dir = Path(fonts_dir) if fonts_dir is not None else (root_dir / "assets" / "fonts")
    staging_dir = target_dir / "pixel_fonts_to_review"
    promoted: list[Path] = []

    for fname in SELECTED_TINY5_FILES:
        src = staging_dir / fname if (staging_dir / fname).exists() else (target_dir / fname)
        if not src.exists():
            raise FileNotFoundError(f"Could not find {fname} in {staging_dir} or {target_dir}")
        patched = normalize_ttf_win_metrics(src.read_bytes())
        dst = target_dir / fname
        dst.write_bytes(patched)
        # Validate loadability & suit glyph presence via Pillow FreeType
        f_test = ImageFont.truetype(str(dst), 24)
        for suit in ("♠", "♥", "♦", "♣"):
            bb = f_test.getbbox(suit)
            if not bb or (bb[2] - bb[0]) <= 0:
                raise RuntimeError(f"Suit glyph {suit!r} failed validation in {dst.name}")
        promoted.append(dst)

    ofl_path = target_dir / "Tiny5-OFL.txt"
    ofl_path.write_text(SIL_OFL_TEXT, encoding="utf-8")

    if remove_staging and staging_dir.exists():
        shutil.rmtree(staging_dir)

    return promoted


if __name__ == "__main__":
    out = promote_tiny5_fonts()
    print(f"Promoted and normalized {len(out)} Tiny5 TTFs into {out[0].parent}:")
    for p in out:
        print(f"  - {p.name} ({p.stat().st_size:,} bytes)")
