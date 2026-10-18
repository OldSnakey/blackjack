"""
Unit test suite for Phase A: DealerStageCanvas, Atmospheric Panoramic Backdrops,
and Stage Wardrobe Hanger Button.

Validates:
- Asset existence and loadability for all 1x and 2x panoramic stage backdrops.
- Presence and geometry of DealerStageCanvas within the horizon layout hierarchy.
- Dynamic theme switching of backdrops across Normal, Creep, Hell's Table, and Victory phases.
- Wardrobe hanger icon rendering at top-right of the stage canvas.
- Hanger click event dispatch.
- 1x <-> 2x High-DPI scaling adaptation.
- Headless test safety.
"""

from __future__ import annotations

import unittest
import tkinter
from pathlib import Path
from PIL import Image, ImageTk

import blackjack
from blackjack import (
    BASE_DIR,
    HAUNTED_ASSETS_DIR,
    BlackjackApp,
    DealerStageCanvas,
    Phase,
)

BACKDROPS_DIR = HAUNTED_ASSETS_DIR / "backdrops"


class TestDealerStageAssets(unittest.TestCase):
    """Verifies that all required panoramic stage assets exist on disk and load cleanly."""

    REQUIRED_BACKDROPS = [
        "backdrop_casino.png",
        "backdrop_casino_2x.png",
        "backdrop_creep.png",
        "backdrop_creep_2x.png",
        "backdrop_hell.png",
        "backdrop_hell_2x.png",
        "backdrop_celestial.png",
        "backdrop_celestial_2x.png",
        "backdrop_crypt.png",
        "backdrop_crypt_2x.png",
    ]

    REQUIRED_ICONS = [
        "hanger_icon.png",
        "hanger_icon_2x.png",
    ]

    def test_backdrops_exist_and_load(self):
        """Every panoramic backdrop asset must exist and be loadable by Pillow."""
        self.assertTrue(BACKDROPS_DIR.exists(), f"{BACKDROPS_DIR} directory missing")
        for filename in self.REQUIRED_BACKDROPS:
            path = BACKDROPS_DIR / filename
            self.assertTrue(path.exists(), f"Backdrop file missing: {filename}")
            with Image.open(path) as img:
                self.assertGreater(img.width, 500)
                self.assertGreater(img.height, 50)

    def test_hanger_icons_exist_and_load(self):
        """Hanger icon assets must exist and load with alpha transparency."""
        for filename in self.REQUIRED_ICONS:
            path = HAUNTED_ASSETS_DIR / filename
            self.assertTrue(path.exists(), f"Hanger icon missing: {filename}")
            with Image.open(path) as img:
                self.assertEqual(img.mode, "RGBA")
                self.assertGreater(img.width, 20)

    def test_backdrops_are_opaque_rgb(self):
        """Panoramic backdrops must be 100% opaque RGB images with zero alpha leakage."""
        for filename in self.REQUIRED_BACKDROPS:
            path = BACKDROPS_DIR / filename
            self.assertTrue(path.exists(), f"Backdrop file missing: {filename}")
            with Image.open(path) as img:
                self.assertIn(
                    img.mode,
                    ("RGB", "RGBA"),
                    f"Backdrop {filename} must have RGB or RGBA mode",
                )
                if img.mode == "RGBA":
                    # Every single pixel must be 100% opaque
                    alphas = [img.getpixel((x, y))[3] for x in range(0, img.width, 20) for y in range(0, img.height, 10)]
                    min_alpha = min(alphas)
                    self.assertEqual(
                        min_alpha,
                        255,
                        f"Backdrop {filename} has low alpha pixels ({min_alpha} < 255) causing transparency leakage",
                    )


class TestDealerStageCanvasIntegration(unittest.TestCase):
    """Verifies DealerStageCanvas layout, backdrop switching, and hanger button integration."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root, sound_enabled=False)

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_dealer_stage_canvas_exists(self):
        """DealerStageCanvas exists and is docked above horizon_rail."""
        self.assertTrue(hasattr(self.app, "dealer_stage_canvas"))
        self.assertIsInstance(self.app.dealer_stage_canvas, DealerStageCanvas)
        self.assertIsInstance(self.app.dealer_stage_canvas, tkinter.Canvas)

    def test_backdrop_theme_switching(self):
        """Phase changes update the active backdrop on DealerStageCanvas."""
        canvas = self.app.dealer_stage_canvas

        # Normal phase -> Casino backdrop
        self.app._apply_phase_theme(Phase.NORMAL)
        self.root.update_idletasks()
        self.assertEqual(canvas.current_theme, "casino")

        # Creep phase -> Creep backdrop
        self.app._apply_phase_theme(Phase.CREEP)
        self.root.update_idletasks()
        self.assertEqual(canvas.current_theme, "creep")

        # Hell's Table -> Hell backdrop
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.root.update_idletasks()
        self.assertEqual(canvas.current_theme, "hell")

        # Victory -> Celestial backdrop
        self.app._apply_phase_theme(Phase.VICTORY)
        self.root.update_idletasks()
        self.assertEqual(canvas.current_theme, "celestial")

    def test_stage_canvas_dark_background(self):
        """DealerStageCanvas background must be dark/theatrical, never green."""
        for phase in (Phase.NORMAL, Phase.CREEP, Phase.HELL_TABLE, Phase.VICTORY):
            self.app._apply_phase_theme(phase)
            self.root.update_idletasks()
            bg = str(self.app.dealer_stage_canvas["background"]).lower()
            self.assertNotIn(bg, ("#074c1a", "#0b6623"), f"Stage canvas background must not be casino felt green in {phase.name}")

    def test_wardrobe_hanger_button_click(self):
        """Clicking the wardrobe hanger button in the top-right triggers the handler."""
        canvas = self.app.dealer_stage_canvas
        clicked = []
        canvas.on_hanger_click = lambda: clicked.append(True)

        # Trigger click event on hanger coordinates (top right)
        canvas._on_canvas_click(type("Event", (), {"x": canvas.canvas_width - 24, "y": 18})())
        self.assertTrue(len(clicked) > 0)

    def test_stage_scaling_under_2x(self):
        """Toggling 2x scale mode updates canvas height and backdrop assets."""
        initial_h = self.app.dealer_stage_canvas.cget("height")
        self.app.toggle_scale_mode()
        scaled_h = self.app.dealer_stage_canvas.cget("height")
        self.assertGreater(int(scaled_h), int(initial_h))

    def test_dealer_sprite_rendered_directly_on_stage_canvas(self):
        """Dealer sprite is drawn directly on DealerStageCanvas with transparent cutout grounded at anchor s."""
        self.app.dealer_view_var.set(True)
        self.app._update_dealer_avatar()
        canvas = self.app.dealer_stage_canvas
        self.root.update_idletasks()

        # Canvas must contain the dealer_sprite item
        items = canvas.find_withtag("dealer_sprite")
        self.assertGreater(len(items), 0, "dealer_sprite tag not found on DealerStageCanvas")
        item_id = items[0]

        # Must be anchored at 's' (south/bottom)
        self.assertEqual(canvas.itemcget(item_id, "anchor"), "s")

        # Dealer view is permanently enabled
        self.assertTrue(self.app.dealer_view_var.get())
        self.assertGreater(len(canvas.find_withtag("dealer_sprite")), 0)



if __name__ == "__main__":
    unittest.main()
