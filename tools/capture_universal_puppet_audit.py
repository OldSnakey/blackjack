"""
Visual Contact-Sheet Generator for Universal Dealer Puppet Audit.

Generates two high-resolution audit sheets in the artifact directory (or `scratch_puppet_audit.png`):
1. `universal_puppet_layers_sheet.png`: Exploded 7-layer strata breakdown (`shadow`, `neck`, `torso`,
   blank faceplate `head`, `eyes_open`, `mouth_neutral`, `arm_rest`, and final `composite`)
   across the portrait dealer roster.
2. `universal_puppet_poses_matrix.png`: 8x5 pose & kinematics matrix across all 8 dealers:
   - Col 1: Neutral Rest (`open` + `neutral` + `rest`)
   - Col 2: Autonomous Blink (`closed` + `neutral` + `rest`)
   - Col 3: Speaking 'O' + Deal Sweep (`open` + `o` + `deal` + `arm_offset=(0, 2)`, `gaze=(1, 1)`)
   - Col 4: Confident Smirk (`half` + `smirk` + `rest`)
   - Col 5: Shocked Gasp + Hole-Card Peek (`open` + `gasp` + `peek` + `head_offset=(0, 1)`, `gaze=(-1, 1)`)
"""

from __future__ import annotations

import sys
import tkinter
from pathlib import Path
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dealer_actor import DealerActor


def generate_audit_sheets(out_dir: Path | None = None) -> tuple[Path, Path]:
    if out_dir is None:
        out_dir = Path(r"C:\Users\wrehm\.gemini\antigravity\brain\512474a9-84d3-4595-8990-50d67f8c7b71")
        if not out_dir.exists():
            out_dir = BASE_DIR

    root = tkinter.Tk()
    root.withdraw()
    try:
        actor = DealerActor(master=root, scale_factor=2.0)

        # Sheet 1: Exploded 7-Layer Breakdown for the 7 main dealers
        roster = ["julian", "tiffany", "selene", "vladimir", "mortimer", "malphas", "uriel"]
        layers = ["shadow", "neck", "torso", "head", "eyes_open", "mouth_neutral", "arm_rest"]
        cell = 140
        cols = len(layers) + 1
        rows = len(roster)
        sheet1 = Image.new("RGBA", (cols * cell + 20, rows * cell + 40), (22, 26, 34, 255))
        d1 = ImageDraw.Draw(sheet1)

        headers = ["Shadow", "Neck", "Torso (De-occl)", "Head (Blank)", "Eyes Open", "Mouth", "Arm Rest", "Composite"]
        for c_idx, h_text in enumerate(headers):
            d1.text((14 + c_idx * cell, 12), h_text, fill=(220, 230, 242, 255))

        for r_idx, cid in enumerate(roster):
            actor.equip_costume(cid)
            actor.reset_kinematics()
            actor.set_eye_state("open")
            actor.set_mouth_state("neutral")
            actor.set_arm_state("rest")
            y0 = 34 + r_idx * cell

            for c_idx, lname in enumerate(layers):
                x0 = 10 + c_idx * cell
                d1.rectangle([x0 + 2, y0 + 2, x0 + cell - 4, y0 + cell - 4], fill=(34, 40, 52, 255), outline=(60, 70, 88, 255))
                limg = actor.get_layer_image(lname, force_2x=True)
                if limg is not None:
                    thumb = limg.resize((cell - 12, cell - 12), Image.Resampling.LANCZOS)
                    sheet1.alpha_composite(thumb, (x0 + 6, y0 + 6))

            # Final composite column
            x_comp = 10 + len(layers) * cell
            d1.rectangle([x_comp + 2, y0 + 2, x_comp + cell - 4, y0 + cell - 4], fill=(28, 52, 42, 255), outline=(90, 180, 130, 255))
            comp = actor.get_composite_image(force_2x=True).resize((cell - 12, cell - 12), Image.Resampling.LANCZOS)
            sheet1.alpha_composite(comp, (x_comp + 6, y0 + 6))
            d1.text((x_comp + 8, y0 + cell - 18), cid.upper(), fill=(255, 215, 0, 255))

        path1 = out_dir / "universal_puppet_layers_sheet.png"
        sheet1.save(path1)

        # Sheet 2: 8x5 Pose & Kinematics Matrix
        all_chars = ["julian", "tiffany", "selene", "vladimir", "mortimer", "malphas", "uriel", "dummy"]
        poses = [
            ("Neutral Rest", "open", "neutral", "rest", (0, 0), (0, 0), (0, 0)),
            ("Blink Closed", "closed", "neutral", "rest", (0, 0), (0, 0), (0, 0)),
            ("Speak 'O' + Deal", "open", "o", "deal", (0, 0), (0, 2), (2, 1)),
            ("Half-Eye + Smirk", "half", "smirk", "rest", (0, 0), (0, 0), (0, 0)),
            ("Gasp + Peek", "open", "gasp", "peek", (0, 1), (-1, 1), (-2, 1)),
        ]
        p_cell = 160
        sheet2 = Image.new("RGBA", (len(poses) * p_cell + 20, len(all_chars) * p_cell + 40), (18, 22, 28, 255))
        d2 = ImageDraw.Draw(sheet2)
        for c_idx, (p_label, *_rest) in enumerate(poses):
            d2.text((16 + c_idx * p_cell, 12), p_label, fill=(220, 235, 250, 255))

        for r_idx, cid in enumerate(all_chars):
            actor.equip_costume(cid)
            y0 = 34 + r_idx * p_cell
            for c_idx, (_label, estate, mstate, astate, h_off, a_off, g_off) in enumerate(poses):
                x0 = 10 + c_idx * p_cell
                actor.reset_kinematics()
                actor.set_eye_state(estate)
                actor.set_mouth_state(mstate)
                actor.set_arm_state(astate)
                actor.set_layer_offsets(head_offset=h_off, arm_offset=a_off, eye_gaze_offset=g_off)

                d2.rectangle([x0 + 3, y0 + 3, x0 + p_cell - 5, y0 + p_cell - 5], fill=(30, 38, 46, 255), outline=(65, 80, 95, 255))
                comp = actor.get_composite_image(force_2x=True).resize((p_cell - 14, p_cell - 14), Image.Resampling.LANCZOS)
                sheet2.alpha_composite(comp, (x0 + 7, y0 + 7))
                if c_idx == 0:
                    d2.text((x0 + 8, y0 + p_cell - 20), cid.upper(), fill=(255, 215, 0, 255))

        path2 = out_dir / "universal_puppet_poses_matrix.png"
        sheet2.save(path2)
        return path1, path2
    finally:
        root.destroy()


if __name__ == "__main__":
    p1, p2 = generate_audit_sheets()
    print(f"Saved audit sheets:\n  1. {p1}\n  2. {p2}")
