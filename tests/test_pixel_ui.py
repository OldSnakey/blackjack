"""
Targeted Automated Test Suite for pixel_ui module.
Validates:
- Font registration and negative pixel sizing helpers.
- Vintage casino color palette completeness.
- CanvasPixelPanel 9-slice procedural generation and scale rebuilds.
- CanvasPixelButton states, tactile press physics, and Tkinter compatibility shims.
"""

from __future__ import annotations

import unittest
import tkinter
from pathlib import Path
from PIL import ImageTk
from pixel_ui import (
    PALETTE,
    load_pixel_font,
    get_pixel_font,
    CanvasPixelPanel,
    CanvasPixelButton,
)


class TestPixelUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tkinter.Tk()
        cls.root.withdraw()
        cls.font_family = load_pixel_font(cls.root)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.canvas = tkinter.Canvas(self.root, width=400, height=300, bg="#07200e")
        self.canvas.pack()

    def tearDown(self):
        try:
            self.canvas.destroy()
        except Exception:
            pass

    def test_palette_completeness(self):
        """Palette contains all required themes with highlight, shadow, and hover tokens."""
        required = ["green", "red", "gold", "blue", "neutral", "amber", "disabled", "wood", "slate"]
        for theme in required:
            self.assertIn(theme, PALETTE, f"Missing theme {theme} in PALETTE")
            self.assertIn("bg", PALETTE[theme], f"Missing 'bg' in theme {theme}")

    def test_font_registration_and_sizing(self):
        """Font registration succeeds and get_pixel_font returns negative pixel sizes."""
        self.assertIsInstance(self.font_family, str)
        self.assertTrue(len(self.font_family) > 0)

        f16 = get_pixel_font(16, "bold")
        self.assertEqual(f16[0], self.font_family)
        self.assertEqual(f16[1], -16, "Must use negative pixel size for exact grid rendering")
        self.assertEqual(f16[2], "bold")

        f32 = get_pixel_font(32, "normal")
        self.assertEqual(f32[1], -32)

    def test_canvas_pixel_panel_creation_and_rebuild(self):
        """CanvasPixelPanel generates PhotoImage on canvas and rebuilds cleanly on scale change."""
        panel = CanvasPixelPanel(
            self.canvas, x=20, y=20, width=90, height=60,
            scale=3, recessed=True, rivet_color="#d4af37"
        )
        self.assertIsNotNone(panel.photo)
        self.assertTrue(panel.item_id > 0)
        initial_img = panel.photo

        # Rebuild at scale 2
        panel.rebuild(scale=2)
        self.assertIsNotNone(panel.photo)
        self.assertNotEqual(panel.photo, initial_img)

        # Resize dimensions
        panel.resize(x=30, y=30, width=120, height=80, scale=2)
        self.assertEqual(panel.x, 30)
        self.assertEqual(panel.y, 30)

    def test_canvas_pixel_button_states_and_press_physics(self):
        """CanvasPixelButton manages normal, hover, pressed, and disabled states with press offset."""
        clicked = []
        btn = CanvasPixelButton(
            self.canvas, x=100, y=100, width=90, height=36,
            text="Hit", theme="green", scale=3,
            command=lambda: clicked.append("hit")
        )
        self.assertTrue(btn.enabled)
        initial_y = btn.y

        # Simulate hover and press
        btn._on_enter(None)
        self.assertTrue(btn._is_hovered)
        btn._on_press(None)
        self.assertTrue(btn._is_pressed)
        # Text must shift down by scale pixels
        coords_pressed = self.canvas.coords(btn.text_id)
        self.assertGreater(coords_pressed[1], initial_y - 1)

        # Simulate release and command invocation
        btn._on_release(None)
        self.assertFalse(btn._is_pressed)
        self.assertEqual(clicked, ["hit"])

        # Test disabled state
        btn.set_enabled(False)
        self.assertFalse(btn.enabled)
        clicked.clear()
        btn._on_press(None)
        btn._on_release(None)
        self.assertEqual(clicked, [], "Disabled button must not trigger command")

    def test_canvas_pixel_button_compatibility_shims(self):
        """CanvasPixelButton supports tk.Button __getitem__, cget, configure, and invoke."""
        invoked = []
        btn = CanvasPixelButton(
            self.canvas, x=150, y=150, width=90, height=36,
            text="Stand", theme="red", command=lambda: invoked.append("stand")
        )

        # 1. __getitem__ and cget
        self.assertEqual(btn["state"], "normal")
        self.assertEqual(btn.cget("state"), "normal")
        self.assertEqual(btn["text"], "Stand")
        self.assertEqual(btn.cget("text"), "Stand")

        # 2. configure / config
        btn.configure(state="disabled")
        self.assertFalse(btn.enabled)
        self.assertEqual(btn["state"], "disabled")

        btn.config(state="normal", text="Stand Now")
        self.assertTrue(btn.enabled)
        self.assertEqual(btn["text"], "Stand Now")

        # 3. invoke
        btn.invoke()
        self.assertEqual(invoked, ["stand"])

        # Invoke when disabled does nothing
        btn.configure(state="disabled")
        btn.invoke()
        self.assertEqual(invoked, ["stand"])

    def test_font_config_json_loaded(self):
        """Verifies assets/fonts/font_config.json loads cleanly and contains required fonts and roles."""
        from pixel_ui import load_font_config
        cfg = load_font_config()
        self.assertIn("fonts", cfg)
        self.assertIn("roles", cfg)
        for expected_role in ("title", "header", "display", "body", "button", "digital", "badge", "micro"):
            self.assertIn(expected_role, cfg["roles"], f"Missing role {expected_role} in font_config.json")

    def test_all_pixel_fonts_registered(self):
        """Verifies load_all_pixel_fonts registers families and returns availability dictionary."""
        from pixel_ui import load_all_pixel_fonts
        registered = load_all_pixel_fonts(self.root)
        self.assertIsInstance(registered, dict)
        self.assertTrue(registered.get("m5x7", False))
        self.assertTrue(registered.get("BoldPixels", False))
        self.assertTrue(registered.get("Round9x13", False))

    def test_semantic_font_getters(self):
        """Verifies all semantic font getters return valid Tkinter font tuples with negative pixel sizes."""
        from pixel_ui import (
            get_title_font,
            get_header_font,
            get_body_font,
            get_button_font,
            get_display_font,
            get_digital_font,
            get_badge_font,
            get_micro_font,
            get_role_font,
            load_font_config,
        )
        cfg = load_font_config()
        roles = cfg.get("roles", {})

        title_f = get_title_font()
        self.assertEqual(title_f[0], roles.get("title", {}).get("family", "BoldPixels"))
        self.assertEqual(title_f[1], -abs(roles.get("title", {}).get("base_size", 20)))
        self.assertEqual(title_f[2], roles.get("title", {}).get("weight", "normal"))

        hdr_f = get_header_font()
        self.assertEqual(hdr_f[0], roles.get("header", {}).get("family", "BoldPixels"))
        self.assertEqual(hdr_f[1], -abs(roles.get("header", {}).get("base_size", 16)))

        disp_f = get_display_font()
        self.assertEqual(disp_f[0], roles.get("display", {}).get("family", "Round9x13"))
        self.assertEqual(disp_f[1], -abs(roles.get("display", {}).get("base_size", 16)))

        body_f = get_body_font()
        self.assertEqual(body_f[0], roles.get("body", {}).get("family", "m5x7"))
        self.assertEqual(body_f[1], -abs(roles.get("body", {}).get("base_size", 14)))

        btn_f = get_button_font()
        self.assertEqual(btn_f[0], roles.get("button", {}).get("family", "m5x7"))
        self.assertEqual(btn_f[1], -abs(roles.get("button", {}).get("base_size", 16)))

        dig_f = get_digital_font()
        self.assertEqual(dig_f[0], roles.get("digital", {}).get("family", "Volt5x5"))
        self.assertEqual(dig_f[1], -abs(roles.get("digital", {}).get("base_size", 14)))

        bdg_f = get_badge_font()
        self.assertEqual(bdg_f[0], roles.get("badge", {}).get("family", "Mini3x5"))
        self.assertEqual(bdg_f[1], -abs(roles.get("badge", {}).get("base_size", 14)))

        mic_f = get_micro_font()
        self.assertEqual(mic_f[0], roles.get("micro", {}).get("family", "3x5_Block_Adjusted"))
        self.assertEqual(mic_f[1], -abs(roles.get("micro", {}).get("base_size", 12)))

        # Scale factor doubling
        title_2x = get_title_font(scale=2.0)
        self.assertEqual(title_2x[1], -abs(roles.get("title", {}).get("base_size", 20) * 2))

        # Custom fallback for unknown role
        fallback_f = get_role_font("nonexistent_role")
        self.assertIsInstance(fallback_f, tuple)
        self.assertLess(fallback_f[1], 0)

    def test_font_config_elements_schema(self):
        """Verifies assets/fonts/font_config.json contains expected UI textual elements."""
        from pixel_ui import load_font_config
        cfg = load_font_config()
        self.assertIn("elements", cfg, "font_config.json must have 'elements' mapping section")
        expected_elements = (
            "top_bar_button", "scoreboard_title", "scoreboard_value", "bankroll_label",
            "shoe_counter", "hand_title", "hand_score", "action_button", "strategy_hint",
            "betting_button", "betting_spot_watermark", "chip_bet_badge", "chip_bankroll_badge",
            "chip_denomination_label", "chip_face_value", "dealer_nameplate", "dealer_speech",
            "table_announcement", "hilo_trainer_title", "hilo_trainer_label", "hilo_trainer_value",
            "soul_meter_title", "dialog_title", "dialog_header", "dialog_body", "dialog_button",
            "story_dialog_speaker", "story_dialog_body", "story_dialog_button",
            "angelic_draft_subtitle", "angelic_draft_title", "angelic_draft_tagline",
            "angelic_draft_description", "angelic_draft_button",
        )
        for elem in expected_elements:
            self.assertIn(elem, cfg["elements"], f"Missing UI element definition '{elem}' in font_config.json")

    def test_get_element_font_resolution(self):
        """Verifies get_element_font resolves role-based and direct overridden elements properly."""
        from pixel_ui import get_element_font, load_font_config
        cfg = load_font_config()
        elem_cfg = cfg.get("elements", {})

        # 1. Action button element
        btn_font = get_element_font("action_button")
        self.assertIsInstance(btn_font, tuple)
        self.assertEqual(len(btn_font), 3)
        self.assertLess(btn_font[1], 0)

        # 2. Scaling propagation (2.0x)
        btn_font_2x = get_element_font("action_button", scale=2.0)
        self.assertEqual(btn_font_2x[1], btn_font[1] * 2)

        # 3. Direct size override
        btn_font_custom = get_element_font("action_button", size_override=24)
        self.assertEqual(btn_font_custom[1], -24)

        # 4. Unknown element fallback
        unknown_font = get_element_font("unknown_widget_xyz")
        self.assertIsInstance(unknown_font, tuple)
        self.assertLess(unknown_font[1], 0)

    def test_pixel_plaque_frame_auto_fit(self):
        """PixelPlaqueFrame dynamically fits long formatted score strings within rivet clearance (<= 90px)."""
        from pixel_ui import PixelPlaqueFrame
        score_var = tkinter.StringVar(value="10 + ?")
        plaque = PixelPlaqueFrame(self.root, width=114, height=60, title="Dealer", score_var=score_var, scale=2)
        plaque.pack()
        self.root.update_idletasks()

        # 1. Initial 10 + ? fits within clearance
        score_font = plaque.score_label.cget("font")
        self.assertIsNotNone(score_font)
        f_obj = tkinter.font.Font(font=score_font)
        self.assertLessEqual(f_obj.measure("10 + ?"), 90)

        # 2. Test long soft hands and split strings
        for test_str in ("Soft 17", "7 / 17", "21 (BJ)", "20 (Revealed)", "H1: 18 | H2: 20"):
            score_var.set(test_str)
            cur_font = plaque.score_label.cget("font")
            measure_w = tkinter.font.Font(font=cur_font).measure(test_str)
            self.assertLessEqual(
                measure_w, 90,
                f"Score string '{test_str}' width {measure_w}px exceeds 90px rivet clearance in plaque"
            )

        plaque.destroy()

    def test_pixel_dialogue_frame(self):
        """PixelDialogueFrame renders authentic wooden panel with rivets and supports dynamic speech packing."""
        from pixel_ui import PixelDialogueFrame
        speech_var = tkinter.StringVar(value="")
        dlg = PixelDialogueFrame(
            self.root, scale=2, bg="#2b170e", title="The Classic Croupier", speech_var=speech_var
        )
        dlg.pack()
        self.root.update_idletasks()

        # Nameplate label
        self.assertEqual(dlg.nameplate_label.cget("text"), "The Classic Croupier")
        self.assertEqual(dlg.height_px, dlg.nameplate_h)
        self.assertEqual(dlg.speech_label.winfo_manager(), "")

        # Pack speech -> height expands
        speech_var.set("Care to double down, traveler?")
        dlg.speech_label.pack()
        self.root.update_idletasks()
        self.assertEqual(dlg.speech_label.winfo_manager(), "pack")
        self.assertEqual(dlg.height_px, dlg.speech_h)

        # Pack forget speech -> height contracts back to nameplate height
        dlg.speech_label.pack_forget()
        self.root.update_idletasks()
        self.assertEqual(dlg.speech_label.winfo_manager(), "")
        self.assertEqual(dlg.height_px, dlg.nameplate_h)

        dlg.destroy()

    def test_pixel_button_widget(self):
        """PixelButtonWidget inherits from tkinter.Button and supports hover and click state events."""
        from pixel_ui import PixelButtonWidget
        clicks = []
        btn = PixelButtonWidget(
            self.root, text="Test", theme="neutral", scale=2, command=lambda: clicks.append(1)
        )
        btn.pack()
        self.root.update_idletasks()

        self.assertIsInstance(btn, tkinter.Button)
        self.assertEqual(btn.cget("relief"), "raised")

        # Hover states
        btn._on_enter(None)
        btn._on_press(None)
        self.assertEqual(btn.cget("relief"), "sunken")
        btn._on_release(None)
        self.assertEqual(btn.cget("relief"), "raised")
        btn._on_leave(None)

        btn.destroy()

    def test_keyboard_icon_clean_glyph(self):
        """KeyboardIconLoader.get_clean_glyph_icon extracts question glyph without opaque white keycap background."""
        from audio_assets import KeyboardIconLoader
        from blackjack import OVERLAY_ICONS_DIR
        loader = KeyboardIconLoader(OVERLAY_ICONS_DIR, master=self.root)
        clean_q = loader.get_clean_glyph_icon("keyboard_question", target_height=16, color="#ffd700")
        self.assertIsNotNone(clean_q)
        self.assertIsInstance(clean_q, ImageTk.PhotoImage)
        self.assertGreater(clean_q.width(), 0)
        self.assertGreater(clean_q.height(), 0)


if __name__ == "__main__":
    unittest.main()
