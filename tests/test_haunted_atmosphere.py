"""
Unit and headless GUI integration tests for HauntedAtmosphereController
(haunted_atmosphere.py), SoundManager haunted audio caching, and canvas Z-order
invariants on DealerStageCanvas and TableFeltCanvas.
"""

from __future__ import annotations

import shutil
import tempfile
import tkinter
import unittest
from pathlib import Path
from unittest import mock

from audio_assets import SoundManager
from blackjack import BlackjackApp
from haunted_atmosphere import (
    HauntedAtmosphereController,
    compute_center_crop_box,
    compute_corruption_tier,
    compute_heartbeat_interval_ms,
)
from haunted_manager import Blessing, Phase
from rules import Card
from state_machine import RoundPhase


class TestHauntedAtmospherePureHelpers(unittest.TestCase):
    """Pure headless math tests for corruption tiers, heartbeat pacing, and center crops."""

    def test_compute_corruption_tier_boundaries(self):
        # Non-HELL_TABLE phases always return Tier 0 (no decals)
        self.assertEqual(compute_corruption_tier(Phase.NORMAL, 0.0), 0)
        self.assertEqual(compute_corruption_tier(Phase.CREEP, 0.1), 0)
        self.assertEqual(compute_corruption_tier(Phase.OMEN, 0.1), 0)
        self.assertEqual(compute_corruption_tier(Phase.SNUFFING, 0.1), 0)
        self.assertEqual(compute_corruption_tier(Phase.VICTORY, 0.0), 0)
        self.assertEqual(compute_corruption_tier(Phase.DEFEAT, 0.0), 0)

        # HELL_TABLE tiers step up as soul drops and recede as soul climbs
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.80), 0)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.75), 0)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.74), 1)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.50), 1)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.49), 2)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.25), 2)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.24), 3)
        self.assertEqual(compute_corruption_tier(Phase.HELL_TABLE, 0.05), 3)

    def test_compute_heartbeat_interval_ms_monotonic_ramp(self):
        self.assertIsNone(compute_heartbeat_interval_ms(0.50))
        self.assertIsNone(compute_heartbeat_interval_ms(0.25))

        t24 = compute_heartbeat_interval_ms(0.24)
        t20 = compute_heartbeat_interval_ms(0.20)
        t15 = compute_heartbeat_interval_ms(0.15)
        t10 = compute_heartbeat_interval_ms(0.10)
        t05 = compute_heartbeat_interval_ms(0.05)

        self.assertIsNotNone(t24)
        self.assertIsNotNone(t20)
        self.assertIsNotNone(t15)
        self.assertEqual(t10, 580)
        self.assertEqual(t05, 580)
        self.assertGreater(t24, t20)
        self.assertGreater(t20, t15)
        self.assertGreater(t15, t10)
        self.assertLessEqual(t24, 950)

    def test_compute_center_crop_box_preserves_20pct_corner_margins(self):
        x0, y0, x1, y1 = compute_center_crop_box(74, 107)
        self.assertEqual((x0, y0, x1, y1), (15, 21, 59, 86))

        x0_2x, y0_2x, x1_2x, y1_2x = compute_center_crop_box(148, 214)
        self.assertEqual((x0_2x, y0_2x, x1_2x, y1_2x), (30, 43, 118, 171))


class TestSoundManagerHauntedCache(unittest.TestCase):
    """Verifies SoundManager caches audio/haunted/*.ogg sounds in memory."""

    def test_haunted_sound_cache_avoids_repeated_disk_loads(self):
        sm = SoundManager(enabled=True)
        sm.is_available = True
        fake_sound = mock.MagicMock()

        with mock.patch("audio_assets.pygame_mixer") as mock_mixer:
            mock_mixer.Sound.return_value = fake_sound
            sm.play_haunted_sound("heartbeat")
            sm.play_haunted_sound("heartbeat.ogg")
            sm.play_haunted_sound("heartbeat")

            self.assertEqual(mock_mixer.Sound.call_count, 1)
            self.assertEqual(fake_sound.play.call_count, 3)
            self.assertIn("heartbeat", sm._haunted_sound_cache)

            # Volume changes propagate to cached haunted sounds
            sm.set_volume(0.35)
            fake_sound.set_volume.assert_called_with(0.35)


class TestHauntedAtmosphereGUI(unittest.TestCase):
    """Headless Tkinter integration tests for HauntedAtmosphereController & canvases."""

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.save_file = self.test_dir / "test_haunted_atmo_save.json"
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(
            self.root,
            sound_enabled=False,
            chips_mode=False,
            save_path=self.save_file,
        )
        self.app.suppress_mode_dialog = True
        self.root.update_idletasks()
        self.ctrl: HauntedAtmosphereController = self.app.haunted_atmosphere

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_zero_timers_in_normal_play_and_mode_isolation(self):
        self.assertEqual(len(self.ctrl._timers), 0)
        self.ctrl.sync_phase_and_soul(Phase.NORMAL, 0.5)
        self.assertEqual(len(self.ctrl._timers), 0)

        # Even if phase is CREEP, 3-seat / bootcamp / tour / open modal block effects
        self.app.haunted.phase = Phase.CREEP
        self.app.table_seats = 3
        self.assertFalse(self.ctrl._can_run_effect(ignore_mapped=True))
        self.app.table_seats = 1

        self.app.tour_active = True
        self.assertFalse(self.ctrl._can_run_effect(ignore_mapped=True))
        self.app.tour_active = False

        self.app.bootcamp_active = True
        self.assertFalse(self.ctrl._can_run_effect(ignore_mapped=True))
        self.app.bootcamp_active = False

        self.assertTrue(self.ctrl._can_run_effect(ignore_mapped=True))

        # Open modal blocks effects
        self.app._open_settings_dialog()
        self.assertFalse(self.ctrl._can_run_effect(ignore_mapped=True))
        self.app._close_settings_dialog()

    def test_comfort_settings_gating_and_global_cooldown(self):
        self.app.haunted.phase = Phase.SNUFFING
        self.ctrl.sync_phase_and_soul(Phase.SNUFFING, 0.5)
        self.assertIn("ambient_poll", self.ctrl._timers)

        # Reduced Flashes blocks transient flashes/flickers while keeping decals & heartbeat
        self.ctrl.apply_comfort_settings("reduced", True)
        self.assertFalse(self.ctrl.trigger_dealer_flash(ignore_mapped=True))
        self.assertFalse(self.ctrl.trigger_felt_text_flicker(ignore_mapped=True))

        # Crawling Bugs: Hide blocks spider and millipede immediately
        self.ctrl.apply_comfort_settings("full", False)
        self.assertFalse(self.ctrl.trigger_stage_spider(ignore_mapped=True))
        self.assertFalse(self.ctrl.trigger_perimeter_millipede(ignore_mapped=True))

        # Full scares + cooldown enforcement (< 3Hz / 6-8s global glitch cooldown)
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl._last_glitch_ts = 0.0
        fired = self.ctrl.trigger_dealer_flash(ignore_mapped=True)
        self.assertTrue(fired)
        # Immediate second trigger is blocked by active glitch / 6-8s cooldown
        self.assertFalse(self.ctrl.trigger_dealer_flash(ignore_mapped=True))

        self.ctrl.cancel_all()
        self.assertEqual(len(self.ctrl._timers), 0)

    def test_card_glitch_zorder_beneath_overlapping_card_and_cleanup(self):
        canvas = self.app.card_table_frame
        self.app.haunted.phase = Phase.HELL_TABLE
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl._last_glitch_ts = 0.0

        # Deal a hand so cards exist on the felt
        self.app.new_game()
        self.root.update_idletasks()

        # Stamp two overlapping dummy card sprites to verify exact Z-order sandwich
        img = self.app.back_image
        c1 = canvas.draw_card_sprite(img, 200, 300, tags=("card_sprite", "player_card"))
        c2 = canvas.draw_card_sprite(img, 226, 300, tags=("card_sprite", "player_card"))

        # Ineligible card returns False without arming cooldown
        ineligible = self.ctrl.trigger_card_glitch(c1, Card(7, None, rank="7", suit="club"), ignore_mapped=True)
        self.assertFalse(ineligible)
        self.assertEqual(self.ctrl._last_glitch_ts, 0.0)

        # Court card glitch stacks strictly above c1 and strictly below c2
        cache_len_before = len(canvas._felt_cache)
        fired = self.ctrl.trigger_card_glitch(c1, Card(10, None, rank="king", suit="heart"), ignore_mapped=True)
        self.assertTrue(fired)
        overlays = canvas.find_withtag("haunted_glitch_overlay")
        self.assertEqual(len(overlays), 1)
        self.assertEqual(canvas.itemcget(overlays[0], "state"), "disabled")

        all_items = list(canvas.find_all())
        self.assertLess(all_items.index(c1), all_items.index(overlays[0]))
        self.assertLess(all_items.index(overlays[0]), all_items.index(c2))
        self.assertLessEqual(len(canvas._felt_cache), 2)
        self.assertEqual(len(canvas._felt_cache), cache_len_before)

        # Moving a card in place clears stale glitch overlay automatically
        canvas.move_card_sprite(c1, 210, 300)
        self.assertEqual(len(canvas.find_withtag("haunted_glitch_overlay")), 0)

        # Bleeding heart glitch on non-court Hearts card also works & clears on clear_card_sprites()
        self.ctrl._last_glitch_ts = 0.0
        self.ctrl.clear_card_glitches()
        fired_heart = self.ctrl.trigger_card_glitch(c1, Card(5, None, rank="5", suit="heart"), ignore_mapped=True)
        self.assertTrue(fired_heart)
        self.assertEqual(len(canvas.find_withtag("haunted_glitch_overlay")), 1)
        canvas.clear_card_sprites()
        self.assertEqual(len(canvas.find_withtag("haunted_glitch_overlay")), 0)

    def test_visible_card_sprites_excludes_hidden_dealer_hole_card(self):
        self.app.new_game()
        self.root.update_idletasks()
        self.app.is_hole_card_hidden = True
        visible = self.app.get_visible_card_sprites()
        visible_ids = {cid for cid, _ in visible}
        hole_id = self.app.dealer_hole_widget.item_id
        if hole_id is not None:
            self.assertNotIn(hole_id, visible_ids)
        if getattr(self.app.dealer_hand, "sprite_ids", None):
            self.assertNotIn(self.app.dealer_hand.sprite_ids[0], visible_ids)

    def test_dealer_stage_zorder_preserves_overlays_above_dealer_sprite(self):
        stage = self.app.dealer_stage_canvas
        self.app.haunted.phase = Phase.SNUFFING
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl._last_glitch_ts = 0.0

        self.assertTrue(self.ctrl.trigger_dealer_flash(ignore_mapped=True))
        # Trigger 25 Hz loops + stage redraw
        stage.update_particles()
        stage._redraw_stage()

        all_items = list(stage.find_all())
        dealer_items = stage.find_withtag("dealer_sprite")
        flash_items = stage.find_withtag("haunted_dealer_flash")
        hanger_items = stage.find_withtag("hanger_btn")
        self.assertTrue(dealer_items and flash_items)
        self.assertLess(all_items.index(dealer_items[0]), all_items.index(flash_items[0]))
        if hanger_items:
            self.assertLess(all_items.index(flash_items[0]), all_items.index(hanger_items[0]))

    def test_decals_stay_below_card_sprite_and_clear_on_victory(self):
        canvas = self.app.card_table_frame
        self.app.new_game()
        self.root.update_idletasks()

        self.ctrl.sync_phase_and_soul(Phase.HELL_TABLE, 0.15)
        decals = canvas.find_withtag("haunted_decal")
        cards = canvas.find_withtag("card_sprite")
        self.assertEqual(len(decals), 12)
        if cards:
            all_items = list(canvas.find_all())
            max_decal_idx = max(all_items.index(d) for d in decals)
            min_card_idx = min(all_items.index(c) for c in cards)
            self.assertLess(max_decal_idx, min_card_idx)

        # Stepping back up to >= 75% or VICTORY clears decals
        self.ctrl.sync_phase_and_soul(Phase.VICTORY, 1.0)
        self.assertEqual(len(canvas.find_withtag("haunted_decal")), 0)
        self.assertEqual(len(self.ctrl._timers), 0)

    def test_blackout_headless_bypass_early_skip_and_fifth_candle_no_softlock(self):
        calls = []
        self.ctrl.play_pit_boss_blackout(
            on_swap_theme=lambda: calls.append("swap"),
            on_complete=lambda: calls.append("complete"),
            headless_bypass=True,
        )
        self.assertEqual(calls, ["swap", "complete"])

        # Interactive early skip before t=200ms still executes on_swap_theme exactly once
        calls2 = []
        self.ctrl.play_pit_boss_blackout(
            on_swap_theme=lambda: calls2.append("swap"),
            on_complete=lambda: calls2.append("complete"),
            headless_bypass=False,
        )
        self.assertTrue(self.ctrl.is_blackout_active)
        self.assertTrue(self.app._has_open_modal_dialog())
        self.ctrl._skip_blackout()
        self.assertFalse(self.ctrl.is_blackout_active)
        self.assertEqual(calls2, ["swap", "complete"])

        # Organic 5th-candle _trigger_hell_table in ROUND_OVER must re-enable new_game_button
        self.app.round_phase = RoundPhase.ROUND_OVER
        self.app.new_game_button.configure(state="disabled")
        self.app._trigger_hell_table(manual=False)
        self.assertEqual(str(self.app.new_game_button.cget("state")), "normal")

        # _open_angelic_draft(on_done=...) invokes on_done even when all blessings are equipped
        done_flag = []
        self.app.haunted.active_blessings = list(Blessing)
        self.app._open_angelic_draft(on_done=lambda: done_flag.append(True))
        self.assertEqual(done_flag, [True])

    def test_felt_text_flicker_preserves_felt_cache_and_cleans_up(self):
        canvas = self.app.card_table_frame
        self.app.haunted.phase = Phase.OMEN
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl._last_glitch_ts = 0.0

        cache_before = len(canvas._felt_cache)
        fired = self.ctrl.trigger_felt_text_flicker(ignore_mapped=True)
        self.assertTrue(fired)
        self.assertGreaterEqual(len(canvas.find_withtag("haunted_felt_flicker")), 2)
        self.assertLessEqual(len(canvas._felt_cache), 2)
        self.assertEqual(len(canvas._felt_cache), cache_before)

        self.ctrl.cancel_all()
        self.assertEqual(len(canvas.find_withtag("haunted_felt_flicker")), 0)
        self.assertEqual(len(self.ctrl._timers), 0)

    def test_focus_group_improvements_hesitation_topmost_cache_and_reduced_blackout(self):
        """Verifies focus-group upgrades: hesitation PLAYER_TURN guard, topmost card priority, reduced blackout, and cache eviction."""
        # 1. Hesitation taunt only arms in HELL_TABLE and refuses to fire outside PLAYER_TURN
        self.ctrl.sync_phase_and_soul(Phase.HELL_TABLE, 0.5)
        self.app.round_phase = RoundPhase.PLAYER_TURN
        self.ctrl.notify_player_turn_started()
        self.assertIn("hesitation", self.ctrl._timers)

        self.app.round_phase = RoundPhase.DEALER_TURN
        self.ctrl._fire_hesitation_taunt()
        self.assertFalse(self.ctrl._hesitation_fired_this_turn)

        self.ctrl.notify_player_turn_ended()
        self.assertNotIn("hesitation", self.ctrl._timers)

        # 2. Blackout skip hint renders in Full mode; Reduced Flashes skips eye pop
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl.play_pit_boss_blackout(lambda: None, lambda: None, headless_bypass=False)
        overlay = self.ctrl._blackout_overlay
        self.assertIsNotNone(overlay)
        self.assertTrue(overlay.canvas.find_withtag("blackout_skip_hint"))
        self.assertEqual(overlay.handle_modal_key(), "break")
        self.ctrl.cancel_all()

        # 3. on_display_profile_changed evicts stale scale cache entries
        self.ctrl._scale_sprite_cache[("spike_0", 99)] = "stale"
        self.ctrl._card_overlay_cache[("king", 1, 1)] = "stale_card"
        self.ctrl.on_display_profile_changed(self.app.display_profile)
        self.assertNotIn(("spike_0", 99), self.ctrl._scale_sprite_cache)
        self.assertNotIn(("king", 1, 1), self.ctrl._card_overlay_cache)

    def test_court_card_glitch_overlay_is_transparent_procedural(self):
        """Court-card glitches use transparent procedural ink/eye overlays (no gray *_haunted_1 background box)."""
        from haunted_atmosphere import _build_court_glitch_pil

        for kind in ("jack", "queen", "king"):
            im = _build_court_glitch_pil(kind)
            w, h = im.size
            # Corners must be fully transparent so crisp white card stock shines through
            for corner in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
                self.assertEqual(im.getpixel(corner)[3], 0, f"{kind} corner {corner} not transparent")
            pixels = list(im.getdata())
            transparent_ratio = sum(1 for p in pixels if p[3] == 0) / float(len(pixels))
            self.assertGreater(transparent_ratio, 0.65, f"{kind} overlay should be mostly transparent")
            crimson_pixels = sum(1 for r, g, b, a in pixels if a > 200 and r > 150 and g < 80 and b < 80)
            self.assertGreater(crimson_pixels, 8, f"{kind} overlay should contain crimson glitch accents")

            photo = self.ctrl._get_card_glitch_photo(kind, 74, 107)
            self.assertIsNotNone(photo)

    def test_soul_claimed_cinematic_sprite_builders(self):
        """Procedural demon claw hands and Malphas close-up laugh frames build crisp transparent 16-bit RGBA sprites."""
        from haunted_atmosphere import (
            HAUNTED_ASSETS_DIR,
            _build_crimson_abyss_glow_pil,
            _build_demon_claw_hand_pil,
            _build_malphas_laugh_frames_pil,
        )

        left_claw = _build_demon_claw_hand_pil("left")
        right_claw = _build_demon_claw_hand_pil("right")
        self.assertTrue((HAUNTED_ASSETS_DIR / "demon_claw_left.png").exists())
        self.assertEqual(left_claw.mode, "RGBA")
        self.assertEqual(left_claw.size, right_claw.size)
        w, h = left_claw.size
        # Corners transparent
        self.assertEqual(left_claw.getpixel((0, 0))[3], 0)
        self.assertEqual(left_claw.getpixel((w - 1, 0))[3], 0)
        # Exact horizontal mirror symmetry
        self.assertEqual(left_claw.getpixel((w // 3, h // 2)), right_claw.getpixel((w - 1 - (w // 3), h // 2)))
        # Contains crimson skin pixels and obsidian claw pixels
        px = list(left_claw.getdata())
        crimson_px = sum(1 for r, g, b, a in px if a > 200 and r > 150 and g < 80 and b < 80)
        obsidian_px = sum(1 for r, g, b, a in px if a > 200 and r < 40 and g < 40 and b < 50)
        self.assertGreater(crimson_px, 120)
        self.assertGreater(obsidian_px, 80)

        # Malphas laugh frames: 2 distinct RGBA frames with transparent top corners
        frame_open, frame_mid = _build_malphas_laugh_frames_pil(dealer_actor=getattr(self.app, "dealer_actor", None), target_h=336)
        self.assertEqual(frame_open.mode, "RGBA")
        self.assertEqual(frame_open.size, frame_mid.size)
        self.assertEqual(frame_open.getpixel((0, 0))[3], 0)
        self.assertNotEqual(frame_open.tobytes(), frame_mid.tobytes())

        glow = _build_crimson_abyss_glow_pil(320, 200)
        self.assertEqual(glow.size, (320, 200))

    def test_soul_claimed_cinematic_full_skip_reduced_and_cancel(self):
        """play_soul_claimed_cinematic supports headless bypass, Full mode + instant skip, Reduced mode, and cancel_all."""
        # 1. Headless bypass executes on_complete synchronously with 0 timers
        done = []
        self.ctrl.play_soul_claimed_cinematic(lambda: done.append("headless"), headless_bypass=True)
        self.assertEqual(done, ["headless"])
        self.assertFalse(self.ctrl._in_blackout)
        self.assertEqual(len(self.ctrl._timers), 0)

        # 2. Full mode mounts overlay, exposes skip hint, and instant skip fires on_complete once
        done.clear()
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl.play_soul_claimed_cinematic(lambda: done.append("full"), headless_bypass=False)
        self.assertTrue(self.ctrl._in_blackout)
        overlay = self.ctrl._blackout_overlay
        self.assertIsNotNone(overlay)
        self.assertTrue(overlay.canvas.find_withtag("blackout_skip_hint"))
        self.assertEqual(overlay.handle_modal_key(), "break")
        # Duplicate skip is idempotent
        self.assertEqual(overlay.handle_modal_key(), "break")
        self.assertEqual(done, ["full"])
        self.assertFalse(self.ctrl._in_blackout)
        self.assertIsNone(self.ctrl._blackout_overlay)
        self.assertEqual(len(self.ctrl._timers), 0)

        # 3. Reduced Flashes mode renders static boss + banner immediately and skips cleanly
        done.clear()
        self.ctrl.apply_comfort_settings("reduced", True)
        self.ctrl.play_soul_claimed_cinematic(lambda: done.append("reduced"), headless_bypass=False)
        self.assertTrue(self.ctrl._in_blackout)
        overlay = self.ctrl._blackout_overlay
        self.assertIsNotNone(overlay)
        self.assertTrue(overlay.canvas.find_withtag("cinematic_boss"))
        self.assertTrue(overlay.canvas.find_withtag("cinematic_banner"))
        self.assertNotIn("blackout_laugh", self.ctrl._timers)
        self.assertEqual(overlay.handle_modal_key(), "break")
        self.assertEqual(done, ["reduced"])
        self.assertEqual(len(self.ctrl._timers), 0)

        # 4. hold_black_backdrop=True keeps pure #060408 curtain until dismiss_blackout_backdrop()
        done.clear()
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl.play_soul_claimed_cinematic(
            lambda: done.append("held"),
            headless_bypass=False,
            hold_black_backdrop=True,
        )
        overlay = self.ctrl._blackout_overlay
        self.assertIsNotNone(overlay)
        self.assertEqual(overlay.handle_modal_key(), "break")
        self.assertEqual(done, ["held"])
        self.assertFalse(self.ctrl._in_blackout)
        self.assertIsNotNone(self.ctrl._blackout_overlay)
        self.assertEqual(len(overlay.canvas.find_withtag("blackout_skip_hint")), 0)
        self.assertEqual(len(overlay.canvas.find_withtag("cinematic_boss")), 0)
        self.ctrl.dismiss_blackout_backdrop()
        self.assertIsNone(self.ctrl._blackout_overlay)

        # 5. cancel_all aborts mid-cinematic without firing on_complete
        done.clear()
        self.ctrl.apply_comfort_settings("full", True)
        self.ctrl.play_soul_claimed_cinematic(lambda: done.append("aborted"), headless_bypass=False)
        self.assertTrue(self.ctrl._in_blackout)
        self.ctrl.cancel_all()
        self.assertFalse(self.ctrl._in_blackout)
        self.assertIsNone(self.ctrl._blackout_overlay)
        self.assertEqual(len(self.ctrl._timers), 0)
        self.assertEqual(done, [])


if __name__ == "__main__":
    unittest.main()
