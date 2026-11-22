"""
Gamepad Input & Dynamic Input Prompt Manager (`input_manager.py`).

Responsibilities:
- Detects Steam Deck / Gamescope environments and connected SDL2 gamepads (`pygame.joystick`).
- Tracks active input prompt mode (`"kb_mouse"` vs `"gamepad"`) using last-input-wins
  switching (with mouse jitter deadzone and optional explicit user override in Settings).
- Detects controller glyph family (`"xbox"` for Xbox / Steam Deck / XInput vs `"playstation"`
  for DualSense / DualShock / Sony controllers).
- Polls `pygame.joystick` non-blockingly (invoked via Tkinter `root.after(...)`) with button
  rising-edge detection, stick deadzone (`0.55`), and directional repeat debouncing (`220ms`).
- Emits `GameEventType.INPUT_MODE_CHANGED` on `EventHub` whenever active mode or glyph family changes.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from config import VALID_INPUT_PROMPT_MODES
from display_profile import DisplayEnvironmentProbe
from event_bus import EventHub, GameEventType

try:
    import pygame
    from pygame import joystick as pygame_joystick
    PYGAME_JOYSTICK_AVAILABLE = True
except Exception:
    pygame = None
    pygame_joystick = None
    PYGAME_JOYSTICK_AVAILABLE = False


# Standard SDL2 / XInput button index -> semantic action mapping
# 0: A / Cross, 1: B / Circle, 2: X / Square, 3: Y / Triangle,
# 4: LB / L1, 5: RB / R1, 6: View / Share, 7: Menu / Options
DEFAULT_BUTTON_MAP: dict[int, str] = {
    0: "confirm",
    1: "cancel",
    2: "action_x",
    3: "action_y",
    4: "tab_prev",
    5: "tab_next",
    6: "help",
    7: "menu",
}

ACTION_ICONS_KB: dict[str, str] = {
    "confirm": "keyboard_enter",
    "cancel": "keyboard_escape",
    "hit": "keyboard_h",
    "stand": "keyboard_s",
    "double": "keyboard_d",
    "split": "keyboard_p",
    "surrender": "keyboard_r",
    "deal": "keyboard_space",
    "clear_bet": "keyboard_c",
    "all_in": "keyboard_a",
    "bet_chip": "mouse_left",
    "nav_lr": "keyboard_arrow_left",
    "nav_ud": "keyboard_arrow_left",
    "menu": "keyboard_o",
    "help": "keyboard_f1",
    "tab_prev": "keyboard_arrow_left",
    "tab_next": "keyboard_arrow_right",
}

ACTION_ICONS_XBOX: dict[str, str] = {
    "confirm": "gamepad_a",
    "cancel": "gamepad_b",
    "hit": "gamepad_a",
    "stand": "gamepad_b",
    "double": "gamepad_x",
    "split": "gamepad_y",
    "surrender": "gamepad_lb",
    "miracle": "gamepad_rb",
    "deal": "gamepad_rt",
    "clear_bet": "gamepad_x",
    "all_in": "gamepad_y",
    "bet_chip": "gamepad_a",
    "chip_cycle": "gamepad_lb",
    "nav_lr": "gamepad_dpad_lr",
    "nav_ud": "gamepad_dpad_ud",
    "dpad": "gamepad_dpad",
    "menu": "gamepad_menu",
    "help": "gamepad_view",
    "tab_prev": "gamepad_lb",
    "tab_next": "gamepad_rb",
}

ACTION_ICONS_PS: dict[str, str] = {
    **ACTION_ICONS_XBOX,
    "confirm": "ps_cross",
    "cancel": "ps_circle",
    "hit": "ps_cross",
    "stand": "ps_circle",
    "double": "ps_square",
    "split": "ps_triangle",
    "surrender": "ps_l1",
    "miracle": "ps_r1",
    "deal": "ps_r2",
    "clear_bet": "ps_square",
    "all_in": "ps_triangle",
    "bet_chip": "ps_cross",
    "chip_cycle": "ps_l1",
    "tab_prev": "ps_l1",
    "tab_next": "ps_r1",
}


def detect_glyph_style(controller_name: str) -> str:
    """Detects PlayStation vs Xbox/Steam Deck glyph family from SDL2 controller name."""
    low = str(controller_name or "").lower()
    if any(tok in low for tok in ("dualsense", "dualshock", "playstation", "ps5", "ps4", "ps3", "sony")):
        return "playstation"
    return "xbox"


class InputManager:
    """
    Central coordinator for gamepad polling, Steam Deck detection, and dynamic
    Keyboard/Mouse <-> Gamepad prompt switching.
    """

    STICK_DEADZONE = 0.55
    TRIGGER_THRESHOLD = 0.60
    REPEAT_MS = 220
    MOUSE_TRAVEL_THRESHOLD_PX = 24.0
    HOTPLUG_SCAN_MS = 1500

    def __init__(
        self,
        *,
        event_bus: Optional[EventHub] = None,
        env_probe: Optional[DisplayEnvironmentProbe] = None,
        user_override: str = "auto",
        enable_pygame_joystick: bool = True,
    ) -> None:
        self.event_bus = event_bus
        self.env_probe = env_probe
        self.user_override = user_override if user_override in VALID_INPUT_PROMPT_MODES else "auto"
        self._enable_pygame_joystick = bool(enable_pygame_joystick and PYGAME_JOYSTICK_AVAILABLE)

        self._joysticks: list[Any] = []
        self._prev_buttons: dict[int, list[int]] = {}
        self._prev_hats: dict[int, tuple[int, int]] = {}
        self._prev_rt: dict[int, bool] = {}
        self._last_nav_action: Optional[str] = None
        self._last_nav_ms: int = 0
        self._mouse_travel_accum: float = 0.0
        self._last_hotplug_scan_ms: int = 0
        self._joystick_inited: bool = False

        if self._enable_pygame_joystick:
            self._init_pygame_joysticks()

        self.glyph_style: str = "xbox"
        if self._joysticks:
            try:
                self.glyph_style = detect_glyph_style(self._joysticks[0].get_name())
            except Exception:
                self.glyph_style = "xbox"

        self.active_mode: str = self._resolve_initial_mode()

    def _init_pygame_joysticks(self) -> None:
        if not PYGAME_JOYSTICK_AVAILABLE or pygame is None or pygame_joystick is None:
            return
        try:
            if not pygame.get_init():
                pygame.init()
            if not pygame_joystick.get_init():
                pygame_joystick.init()
            self._joystick_inited = True
            self._refresh_pygame_joysticks()
        except Exception:
            self._joystick_inited = False

    def _refresh_pygame_joysticks(self) -> None:
        if not self._joystick_inited or pygame_joystick is None:
            return
        try:
            count = pygame_joystick.get_count()
            if count == len(self._joysticks):
                return
            self._joysticks.clear()
            self._prev_buttons.clear()
            self._prev_hats.clear()
            self._prev_rt.clear()
            for idx in range(count):
                j = pygame_joystick.Joystick(idx)
                j.init()
                self._joysticks.append(j)
            if self._joysticks:
                self.glyph_style = detect_glyph_style(self._joysticks[0].get_name())
        except Exception:
            pass

    def attach_mock_joystick(self, joy: Any) -> None:
        """Attaches a mock joystick object for headless unit testing."""
        self._joysticks = [joy]
        self._prev_buttons.clear()
        self._prev_hats.clear()
        self._prev_rt.clear()
        try:
            self.glyph_style = detect_glyph_style(joy.get_name())
        except Exception:
            self.glyph_style = "xbox"

    def _is_steam_deck_env(self) -> bool:
        return bool(
            self.env_probe is not None
            and (getattr(self.env_probe, "is_steam_deck", False) or getattr(self.env_probe, "is_gamescope", False))
        )

    def _resolve_initial_mode(self) -> str:
        if self.user_override == "gamepad":
            return "gamepad"
        if self.user_override == "kb_mouse":
            return "kb_mouse"
        if self._is_steam_deck_env() or len(self._joysticks) > 0:
            return "gamepad"
        return "kb_mouse"

    def _set_state(self, new_mode: str, new_glyph: Optional[str] = None, source: str = "auto") -> bool:
        target_glyph = new_glyph or self.glyph_style
        if new_mode == self.active_mode and target_glyph == self.glyph_style:
            return False
        self.active_mode = new_mode
        self.glyph_style = target_glyph
        if self.event_bus is not None:
            self.event_bus.emit(
                GameEventType.INPUT_MODE_CHANGED,
                {
                    "mode": self.active_mode,
                    "glyph_style": self.glyph_style,
                    "override": self.user_override,
                    "source": source,
                },
            )
        return True

    def set_user_override(self, override: str) -> str:
        """Updates user preference ('auto' | 'kb_mouse' | 'gamepad') and immediately resolves active_mode."""
        val = override if override in VALID_INPUT_PROMPT_MODES else "auto"
        self.user_override = val
        target = self._resolve_initial_mode()
        self._set_state(target, self.glyph_style, source="settings_override")
        return self.active_mode

    def notify_gamepad_input(self, controller_name: str = "") -> None:
        """Records gamepad activity and switches active_mode to 'gamepad' unless locked to kb_mouse."""
        self._mouse_travel_accum = 0.0
        glyph = detect_glyph_style(controller_name) if controller_name else self.glyph_style
        if self.user_override == "kb_mouse":
            if glyph != self.glyph_style:
                self._set_state(self.active_mode, glyph, source="gamepad")
            return
        self._set_state("gamepad", glyph, source="gamepad")

    def notify_keyboard_input(self) -> None:
        """Records keyboard activity and switches active_mode to 'kb_mouse' in Auto mode."""
        if self.user_override != "auto":
            return
        # On Steam Deck / Gamescope, Steam Input frequently maps Deck buttons to keyboard keys;
        # keep gamepad prompts active unless the user clicks the mouse or overrides in Settings.
        if self._is_steam_deck_env():
            return
        self._set_state("kb_mouse", self.glyph_style, source="keyboard")

    def notify_mouse_input(self, *, is_click: bool = False, delta_px: float = 0.0) -> None:
        """Records mouse activity; requires click or >= 24px accumulated travel to avoid jitter flicker."""
        if self.user_override != "auto":
            return
        if is_click:
            self._mouse_travel_accum = 0.0
            self._set_state("kb_mouse", self.glyph_style, source="mouse_click")
            return
        self._mouse_travel_accum += abs(float(delta_px))
        if self._mouse_travel_accum >= self.MOUSE_TRAVEL_THRESHOLD_PX:
            self._mouse_travel_accum = 0.0
            self._set_state("kb_mouse", self.glyph_style, source="mouse_motion")

    def poll_actions(self, now_ms: Optional[int] = None) -> list[str]:
        """
        Non-blocking poll of connected joysticks. Returns a list of semantic action tokens
        triggered since the previous poll. Safe no-op if no controller is attached.
        """
        ts = int(now_ms) if now_ms is not None else int(time.monotonic() * 1000)

        if self._joystick_inited and pygame is not None:
            try:
                pygame.event.pump()
                if ts - self._last_hotplug_scan_ms >= self.HOTPLUG_SCAN_MS:
                    self._last_hotplug_scan_ms = ts
                    self._refresh_pygame_joysticks()
            except Exception:
                return []

        if not self._joysticks:
            return []

        actions: list[str] = []
        any_input_name = ""

        for j_idx, joy in enumerate(self._joysticks):
            try:
                j_name = str(joy.get_name() or "")
                num_btn = int(joy.get_numbuttons())
                prev_b = self._prev_buttons.get(j_idx)
                if prev_b is None or len(prev_b) != num_btn:
                    prev_b = [0] * num_btn
                cur_b = [int(joy.get_button(i)) for i in range(num_btn)]
                for i, val in enumerate(cur_b):
                    if val and not prev_b[i]:
                        act = DEFAULT_BUTTON_MAP.get(i)
                        if act:
                            actions.append(act)
                        any_input_name = j_name or "Gamepad"
                self._prev_buttons[j_idx] = cur_b

                # Right Trigger (axis 5 on Xbox/SDL2 standard mapping, value -1..+1 -> pressed > 0.6)
                num_axes = int(joy.get_numaxes())
                if num_axes >= 6:
                    rt_pressed = float(joy.get_axis(5)) >= self.TRIGGER_THRESHOLD
                    if rt_pressed and not self._prev_rt.get(j_idx, False):
                        actions.append("deal")
                        any_input_name = j_name or "Gamepad"
                    self._prev_rt[j_idx] = rt_pressed

                # Directional input: D-Pad hat + Left Stick
                nav_dir: Optional[str] = None
                if int(joy.get_numhats()) > 0:
                    hx, hy = joy.get_hat(0)
                    prev_h = self._prev_hats.get(j_idx, (0, 0))
                    self._prev_hats[j_idx] = (hx, hy)
                    if hx < 0:
                        nav_dir = "nav_left"
                    elif hx > 0:
                        nav_dir = "nav_right"
                    elif hy > 0:
                        nav_dir = "nav_up"
                    elif hy < 0:
                        nav_dir = "nav_down"
                    if (hx, hy) != (0, 0):
                        any_input_name = j_name or "Gamepad"
                        if prev_h == (0, 0) and nav_dir:
                            actions.append(nav_dir)
                            self._last_nav_action = nav_dir
                            self._last_nav_ms = ts
                            continue

                if nav_dir is None and num_axes >= 2:
                    ax_x = float(joy.get_axis(0))
                    ax_y = float(joy.get_axis(1))
                    if abs(ax_x) >= self.STICK_DEADZONE or abs(ax_y) >= self.STICK_DEADZONE:
                        any_input_name = j_name or "Gamepad"
                        if abs(ax_x) >= abs(ax_y):
                            nav_dir = "nav_right" if ax_x > 0 else "nav_left"
                        else:
                            nav_dir = "nav_down" if ax_y > 0 else "nav_up"

                if nav_dir is not None:
                    if nav_dir != self._last_nav_action or (ts - self._last_nav_ms) >= self.REPEAT_MS:
                        actions.append(nav_dir)
                        self._last_nav_action = nav_dir
                        self._last_nav_ms = ts
                else:
                    self._last_nav_action = None
            except Exception:
                continue

        if any_input_name:
            self.notify_gamepad_input(any_input_name)

        return actions

    def get_icon_name(self, action: str) -> str:
        """Returns the overlay icon filename stem for `action` under the active mode & glyph family."""
        if self.active_mode == "gamepad":
            table = ACTION_ICONS_PS if self.glyph_style == "playstation" else ACTION_ICONS_XBOX
            return table.get(action, "gamepad_a")
        return ACTION_ICONS_KB.get(action, "keyboard_enter")

    def get_button_badge_text(self, action: str) -> str:
        """Returns a compact inline badge like '[A]' or '[✕]' in gamepad mode, or '' in kb_mouse mode."""
        if self.active_mode != "gamepad":
            return ""
        if self.glyph_style == "playstation":
            ps_map = {
                "hit": "[✕]",
                "stand": "[○]",
                "double": "[□]",
                "split": "[△]",
                "surrender": "[L1]",
                "miracle": "[R1]",
                "deal": "[R2]",
                "clear_bet": "[□]",
                "all_in": "[△]",
                "new_game": "[✕]",
            }
            return ps_map.get(action, "")
        xb_map = {
            "hit": "[A]",
            "stand": "[B]",
            "double": "[X]",
            "split": "[Y]",
            "surrender": "[LB]",
            "miracle": "[RB]",
            "deal": "[RT]",
            "clear_bet": "[X]",
            "all_in": "[Y]",
            "new_game": "[A]",
        }
        return xb_map.get(action, "")

    def get_footer_hint(self, context: str = "picker", *, n_opts: int = 3) -> str:
        """Returns context-aware modal footer hint text matching active input mode & glyph family."""
        if self.active_mode == "gamepad":
            a_lbl = "✕" if self.glyph_style == "playstation" else "A"
            b_lbl = "○" if self.glyph_style == "playstation" else "B"
            lb_lbl = "L1/R1" if self.glyph_style == "playstation" else "LB/RB"
            if context == "picker":
                return f"[D-Pad] Navigate  •  [{a_lbl}] Apply  •  [{b_lbl}] Cancel"
            if context == "shortcuts":
                return f"💡 Tip: Switch tabs with [{lb_lbl}] or [D-Pad ◄/►]. Press [{b_lbl}] or [View] to return to the table."
            return f"[{lb_lbl}] Tabs  •  [{a_lbl}] Select  •  [{b_lbl}] Close"
        if context == "picker":
            return f"[↑/↓] Navigate  •  [Enter] Apply  •  [1-{n_opts}] Quick Pick  •  [Esc] Cancel"
        if context == "shortcuts":
            return "💡 Tip: Switch tabs with [◄ / ►] or [1] / [2]. Press [Esc], [?], or [F1] to return to the table."
        return "Switch Tabs: [1] / [2] or [◄ / ►]  •  Close: [Esc]"

    def format_current_summary(self) -> str:
        """Human-readable status summary for Settings -> Input Prompts subtitle."""
        active_lbl = (
            "Gamepad (PS)" if (self.active_mode == "gamepad" and self.glyph_style == "playstation")
            else ("Gamepad" if self.active_mode == "gamepad" else "KB & Mouse")
        )
        if self.user_override == "auto":
            return f"Current: Auto ({active_lbl})"
        return f"Current: {active_lbl}"
