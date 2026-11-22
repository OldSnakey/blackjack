"""
Unit tests for InputManager (gamepad/Steam Deck detection, last-input-wins switching,
PlayStation vs Xbox/Steam Deck glyph detection, mock joystick polling) and the
64x64 crunchy pixel-art gamepad icon set in assets/overlay_icons/.
"""

from __future__ import annotations

import tkinter
import unittest
from PIL import Image

import config
from audio_assets import KeyboardIconLoader
from display_profile import DisplayEnvironmentProbe
from event_bus import EventHub, GameEventType

GAMEPAD_ICON_NAMES = (
    "gamepad_a",
    "gamepad_b",
    "gamepad_x",
    "gamepad_y",
    "gamepad_lb",
    "gamepad_rb",
    "gamepad_lt",
    "gamepad_rt",
    "gamepad_dpad",
    "gamepad_dpad_lr",
    "gamepad_dpad_ud",
    "gamepad_menu",
    "gamepad_view",
    "ps_cross",
    "ps_circle",
    "ps_square",
    "ps_triangle",
    "ps_l1",
    "ps_r1",
    "ps_l2",
    "ps_r2",
)


class _FakeJoystick:
    """Deterministic headless mock for pygame.joystick.Joystick."""

    def __init__(self, name: str = "Xbox Wireless Controller", num_buttons: int = 10, num_axes: int = 6, num_hats: int = 1):
        self._name = name
        self.buttons = [0] * num_buttons
        self.axes = [0.0] * num_axes
        self.hats = [(0, 0)] * num_hats

    def get_name(self) -> str:
        return self._name

    def get_numbuttons(self) -> int:
        return len(self.buttons)

    def get_button(self, idx: int) -> int:
        return self.buttons[idx]

    def get_numaxes(self) -> int:
        return len(self.axes)

    def get_axis(self, idx: int) -> float:
        return self.axes[idx]

    def get_numhats(self) -> int:
        return len(self.hats)

    def get_hat(self, idx: int) -> tuple[int, int]:
        return self.hats[idx]


class TestInputManagerAndGamepadIcons(unittest.TestCase):
    """Validates InputManager state transitions, mock joystick polling, and 64x64 gamepad icons."""

    def test_startup_mode_resolution_desktop_steam_deck_and_overrides(self):
        from input_manager import InputManager

        desktop_probe = DisplayEnvironmentProbe((1920, 1080), (1920, 1030), is_steam_deck=False, is_gamescope=False)
        deck_probe = DisplayEnvironmentProbe((1280, 800), (1280, 800), is_steam_deck=True, is_gamescope=True)

        im_desktop = InputManager(env_probe=desktop_probe, user_override="auto", enable_pygame_joystick=False)
        self.assertEqual(im_desktop.active_mode, "kb_mouse")
        self.assertEqual(im_desktop.glyph_style, "xbox")

        im_deck = InputManager(env_probe=deck_probe, user_override="auto", enable_pygame_joystick=False)
        self.assertEqual(im_deck.active_mode, "gamepad")
        self.assertEqual(im_deck.glyph_style, "xbox")

        # Explicit user overrides win over hardware probe
        im_forced_kb = InputManager(env_probe=deck_probe, user_override="kb_mouse", enable_pygame_joystick=False)
        self.assertEqual(im_forced_kb.active_mode, "kb_mouse")

        im_forced_gp = InputManager(env_probe=desktop_probe, user_override="gamepad", enable_pygame_joystick=False)
        self.assertEqual(im_forced_gp.active_mode, "gamepad")

    def test_last_input_wins_mouse_jitter_deadzone_and_playstation_glyph_detection(self):
        from input_manager import InputManager

        events = []
        hub = EventHub()
        hub.subscribe(GameEventType.INPUT_MODE_CHANGED, lambda ev: events.append(ev.payload))
        desktop_probe = DisplayEnvironmentProbe((1920, 1080), (1920, 1030), is_steam_deck=False, is_gamescope=False)
        im = InputManager(event_bus=hub, env_probe=desktop_probe, user_override="auto", enable_pygame_joystick=False)
        self.assertEqual(im.active_mode, "kb_mouse")

        # Gamepad input from DualSense switches to gamepad + playstation glyphs and emits event
        im.notify_gamepad_input("Sony DualSense Wireless Controller")
        self.assertEqual(im.active_mode, "gamepad")
        self.assertEqual(im.glyph_style, "playstation")
        self.assertEqual(im.get_icon_name("confirm"), "ps_cross")
        self.assertEqual(im.get_icon_name("cancel"), "ps_circle")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[-1]["mode"], "gamepad")
        self.assertEqual(events[-1]["glyph_style"], "playstation")

        # Small mouse jitter (< 24px) must NOT flicker off gamepad mode
        im.notify_mouse_input(is_click=False, delta_px=8.0)
        im.notify_mouse_input(is_click=False, delta_px=10.0)
        self.assertEqual(im.active_mode, "gamepad")

        # Deliberate mouse click switches back to kb_mouse
        im.notify_mouse_input(is_click=True, delta_px=0.0)
        self.assertEqual(im.active_mode, "kb_mouse")
        self.assertEqual(im.get_icon_name("confirm"), "keyboard_enter")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[-1]["mode"], "kb_mouse")

        # Switching to Xbox controller updates glyph_style back to xbox
        im.notify_gamepad_input("Steam Deck Controller")
        self.assertEqual(im.active_mode, "gamepad")
        self.assertEqual(im.glyph_style, "xbox")
        self.assertEqual(im.get_icon_name("confirm"), "gamepad_a")
        self.assertEqual(im.get_icon_name("cancel"), "gamepad_b")

    def test_mock_joystick_polling_edge_detection_and_stick_deadzone(self):
        from input_manager import InputManager

        desktop_probe = DisplayEnvironmentProbe((1920, 1080), (1920, 1030), is_steam_deck=False, is_gamescope=False)
        im = InputManager(env_probe=desktop_probe, user_override="auto", enable_pygame_joystick=False)
        joy = _FakeJoystick(name="Xbox Series X Controller")
        im.attach_mock_joystick(joy)

        # Idle poll produces no actions
        self.assertEqual(im.poll_actions(now_ms=1000), [])

        # Button 0 (A) press fires 'confirm' once on rising edge, not while held
        joy.buttons[0] = 1
        self.assertEqual(im.poll_actions(now_ms=1020), ["confirm"])
        self.assertEqual(im.active_mode, "gamepad")
        self.assertEqual(im.poll_actions(now_ms=1040), [])
        joy.buttons[0] = 0
        self.assertEqual(im.poll_actions(now_ms=1060), [])

        # Stick movement inside deadzone (< 0.55) is ignored
        joy.axes[0] = 0.35
        self.assertEqual(im.poll_actions(now_ms=1100), [])

        # Stick movement past deadzone (>= 0.55) triggers nav_right and respects 220ms repeat debounce
        joy.axes[0] = 0.85
        self.assertEqual(im.poll_actions(now_ms=1120), ["nav_right"])
        self.assertEqual(im.poll_actions(now_ms=1200), [])  # < 220ms
        self.assertEqual(im.poll_actions(now_ms=1360), ["nav_right"])  # >= 220ms repeat

        # D-Pad hat left triggers nav_left
        joy.axes[0] = 0.0
        joy.hats[0] = (-1, 0)
        self.assertEqual(im.poll_actions(now_ms=1400), ["nav_left"])

    def test_all_gamepad_and_playstation_icons_exist_and_load_via_icon_loader(self):
        root = tkinter.Tk()
        root.withdraw()
        try:
            loader = KeyboardIconLoader(config.OVERLAY_ICONS_DIR, master=root)
            for name in GAMEPAD_ICON_NAMES:
                path = config.OVERLAY_ICONS_DIR / f"{name}.png"
                self.assertTrue(path.exists(), f"Missing controller prompt icon: {path}")
                with Image.open(path) as im:
                    self.assertEqual(im.mode, "RGBA", f"{name}.png must be RGBA")
                    self.assertEqual(im.size, (64, 64), f"{name}.png must be 64x64")
                    self.assertIsNotNone(im.getchannel("A").getbbox(), f"{name}.png is empty")
                tk_img = loader.get_icon(name, scale_div=2)
                self.assertIsNotNone(tk_img, f"KeyboardIconLoader failed to load {name}")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
