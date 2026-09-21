"""
Unit tests for SoundManager audio subsystem and Tkinter GUI sound controls.
Validates asset loading, polyphony, volume control, mute toggling, and headless degradation.
"""

import unittest
import tkinter
from pathlib import Path
from blackjack import (
    SoundManager,
    BlackjackApp,
    AUDIO_DIR,
    DEFAULT_SOUND_VOLUME,
)


class TestSoundManager(unittest.TestCase):
    """Unit tests for the standalone SoundManager audio engine."""

    def setUp(self):
        self.manager = SoundManager(audio_dir=AUDIO_DIR, enabled=True, volume=0.7)

    def tearDown(self):
        if hasattr(self, "manager"):
            self.manager.stop_all()

    def test_audio_assets_loaded(self):
        """Verifies that all 42 .ogg audio assets in audio/ are loaded into their respective pools."""
        if not self.manager.is_available:
            self.skipTest("Audio device not available in this test environment.")

        expected_counts = {
            "card_slide": 8,
            "card_place": 4,
            "card_shove": 4,
            "card_shuffle": 1,
            "card_fan": 2,
            "cards_pack": 4,
            "chip_lay": 3,
            "chips_collide": 4,
            "chips_stack": 6,
            "chips_handle": 6,
        }

        total_sounds = 0
        for category, expected_count in expected_counts.items():
            loaded_count = len(self.manager.sounds.get(category, []))
            self.assertEqual(
                loaded_count, expected_count,
                f"Category '{category}' expected {expected_count} sounds, found {loaded_count}"
            )
            total_sounds += loaded_count

        self.assertEqual(total_sounds, 42)

    def test_toggle_mute(self):
        """Toggling mute alternates enabled status and is_muted property."""
        self.assertTrue(self.manager.enabled)
        # First toggle: mute
        res = self.manager.toggle_mute()
        self.assertFalse(res)
        self.assertFalse(self.manager.enabled)
        self.assertTrue(self.manager.is_muted)

        # Second toggle: unmute
        res2 = self.manager.toggle_mute()
        self.assertTrue(res2)
        self.assertTrue(self.manager.enabled)

    def test_set_volume_bounds(self):
        """set_volume clamps volume strictly between 0.0 and 1.0."""
        self.manager.set_volume(0.5)
        self.assertAlmostEqual(self.manager.volume, 0.5)

        # Clamp upper
        self.manager.set_volume(1.5)
        self.assertAlmostEqual(self.manager.volume, 1.0)

        # Clamp lower
        self.manager.set_volume(-0.5)
        self.assertAlmostEqual(self.manager.volume, 0.0)

    def test_play_all_event_methods_execute_without_error(self):
        """All domain event play methods run without exceptions regardless of enabled state."""
        event_methods = [
            self.manager.play_card_deal,
            self.manager.play_card_place,
            self.manager.play_card_shuffle,
            self.manager.play_card_fan,
            self.manager.play_chip_add,
            self.manager.play_chip_stack,
            self.manager.play_chip_clear,
            self.manager.play_surrender,
            self.manager.play_payout,
            self.manager.play_loss,
            self.manager.play_push,
        ]

        # Test with sound enabled
        for method in event_methods:
            try:
                method()
            except Exception as ex:
                self.fail(f"{method.__name__} raised exception: {ex}")

        # Test with sound disabled (mute)
        self.manager.enabled = False
        for method in event_methods:
            try:
                method()
            except Exception as ex:
                self.fail(f"{method.__name__} while muted raised exception: {ex}")

    def test_stop_all(self):
        """stop_all executes cleanly."""
        try:
            self.manager.stop_all()
        except Exception as ex:
            self.fail(f"stop_all raised exception: {ex}")

    def test_nonexistent_audio_directory_fails_safely(self):
        """SoundManager safely handles missing directories without throwing unhandled exceptions."""
        dummy_dir = Path("nonexistent_audio_dir_xyz_12345")
        mgr = SoundManager(audio_dir=dummy_dir, enabled=True)
        # Should initialize with empty sound pools
        for pool in mgr.sounds.values():
            self.assertEqual(len(pool), 0)
        # Play methods should safely no-op
        try:
            mgr.play_card_deal()
            mgr.play_chip_add()
            mgr.play_payout()
        except Exception as ex:
            self.fail(f"Safe degradation failed on missing dir: {ex}")


class TestSoundGuiIntegration(unittest.TestCase):
    """Integration tests for audio controls within the BlackjackApp Tkinter UI."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root, sound_enabled=True)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.app._on_close()
        except tkinter.TclError:
            pass

    def test_sound_button_exists_and_displays_initial_state(self):
        """The sound button is created with 🔊 Sound: ON initial text."""
        self.assertTrue(hasattr(self.app, "sound_button"))
        self.assertEqual(self.app.sound_status_var.get(), "🔊 Sound: ON")
        self.assertTrue(self.app.sound_manager.enabled)

    def test_toggle_sound_updates_button_text_and_manager_state(self):
        """Clicking the sound button toggles the manager and updates the label text."""
        # Toggle mute
        self.app._on_toggle_sound()
        self.assertFalse(self.app.sound_manager.enabled)
        self.assertEqual(self.app.sound_status_var.get(), "🔇 Sound: OFF")

        # Toggle unmute
        self.app._on_toggle_sound()
        self.assertTrue(self.app.sound_manager.enabled)
        self.assertEqual(self.app.sound_status_var.get(), "🔊 Sound: ON")


class TestSoundDisabledApp(unittest.TestCase):
    """Tests initializing BlackjackApp with sound_enabled=False."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(self.root, sound_enabled=False)

    def tearDown(self):
        try:
            if self.root.winfo_exists():
                self.app._on_close()
        except tkinter.TclError:
            pass

    def test_sound_disabled_initialization(self):
        """Passing sound_enabled=False initializes app with sound muted."""
        self.assertFalse(self.app.sound_manager.enabled)
        self.assertEqual(self.app.sound_status_var.get(), "🔇 Sound: OFF")


if __name__ == "__main__":
    unittest.main()
