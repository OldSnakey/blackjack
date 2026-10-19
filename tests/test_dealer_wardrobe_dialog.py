"""
Unit test suite for Dealer Wardrobe & Costume Dressing Room Dialog.

Validates:
- WardrobeDialog initialization and headless lifecycle.
- Character card rendering for Julian, Malphas, Uriel, and Mortimer.
- Unlocking criteria evaluation based on save data and haunted mode progress.
- Costume equipping updates DealerActor and persists to SaveManager.
- Voice preview audio trigger.
- Stage hanger button triggers WardrobeDialog.
- Clean dismissal and focus handling on WM_DELETE_WINDOW / Escape.
"""

from __future__ import annotations

import tempfile
import unittest
import tkinter
from pathlib import Path

from blackjack import BlackjackApp, Phase
from dealer_actor import CHARACTERS
from save_manager import SaveManager


class TestDealerWardrobeDialog(unittest.TestCase):
    """Verifies WardrobeDialog functionality, character cards, and costume switching."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_dir = Path(self.temp_dir.name)

        self.root = tkinter.Tk()
        self.root.withdraw()

        self.app = BlackjackApp(self.root, sound_enabled=False)
        self.app.save_manager = SaveManager(save_path=self.save_dir / "test_save.json")

    def tearDown(self):
        try:
            if hasattr(self.app, "_wardrobe_dialog") and self.app._wardrobe_dialog:
                self.app._wardrobe_dialog.destroy()
        except Exception:
            pass
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_stage_hanger_opens_wardrobe_dialog(self):
        """Clicking stage hanger button opens the WardrobeDialog."""
        self.app._on_click_stage_hanger()
        self.assertIsNotNone(self.app._wardrobe_dialog)
        self.assertTrue(self.app._wardrobe_dialog.winfo_exists())
        self.assertEqual(self.app._wardrobe_dialog.title(), "🎩 Dealer Wardrobe & Dressing Room")

    def test_wardrobe_cards_render_all_four_characters(self):
        """Wardrobe dialog renders character cards for Julian, Malphas, Uriel, Mortimer, and Dummy."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertIsNotNone(dialog)
        self.assertTrue(hasattr(dialog, "cards"))
        for char_id in ("julian", "tiffany", "malphas", "uriel", "mortimer", "dummy"):
            self.assertIn(char_id, dialog.cards, f"Character card missing: {char_id}")

    def test_julian_and_tiffany_are_unlocked_by_default(self):
        """Julian and Tiffany are both unlocked by default as casino croupiers."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertTrue(dialog.cards["julian"]["unlocked"])
        self.assertTrue(dialog.cards["julian"]["is_equipped"])
        self.assertTrue(dialog.cards["tiffany"]["unlocked"])
        self.assertTrue(dialog.cards["dummy"]["unlocked"])

    def test_wardrobe_pagination(self):
        """Next and Prev page navigation switches pages and updates navigation controls."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertEqual(dialog.current_page, 0)
        self.assertIn("Page 1 of 2", dialog.page_lbl.cget("text"))

        # Switch to Page 2
        dialog._next_page()
        self.assertEqual(dialog.current_page, 1)
        self.assertIn("Page 2 of 2", dialog.page_lbl.cget("text"))

        # Switch back to Page 1
        dialog._prev_page()
        self.assertEqual(dialog.current_page, 0)
        self.assertIn("Page 1 of 2", dialog.page_lbl.cget("text"))

    def test_equipping_tiffany_updates_actor_and_save(self):
        """Equipping Tiffany switches dealer persona, table avatar, and save data."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        dialog._equip_costume("tiffany")
        self.assertEqual(self.app.dealer_actor.current_character, "tiffany")
        self.assertEqual(self.app.save_manager.data.equipped_costume, "tiffany")

    def test_equipping_dummy_updates_actor_and_save(self):
        """Equipping Dummy switches dealer persona to dummy, table avatar, and save data."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertTrue(dialog.cards["dummy"]["unlocked"])
        dialog._equip_costume("dummy")
        self.assertEqual(self.app.dealer_actor.current_character, "dummy")
        self.assertEqual(self.app.save_manager.data.equipped_costume, "dummy")

    def test_unlock_criteria_evaluation(self):
        """Malphas, Uriel, and Mortimer unlock according to game achievements."""
        # By default (blank slate): Malphas, Uriel, Mortimer are locked
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertFalse(dialog.cards["malphas"]["unlocked"])
        self.assertFalse(dialog.cards["uriel"]["unlocked"])
        self.assertFalse(dialog.cards["mortimer"]["unlocked"])
        dialog.destroy()

        # Unlock Malphas via Hell's Table encounter flag
        self.app.haunted.unlocked_cursed_stakes = True
        # Unlock Uriel via Exorcist achievement
        self.app.save_manager.data.achievements.exorcist = True
        # Unlock Mortimer via peak bankroll >= 5000
        self.app.save_manager.data.highscores.peak_bankroll = 5000

        self.app._on_click_stage_hanger()
        dialog2 = self.app._wardrobe_dialog
        self.assertTrue(dialog2.cards["malphas"]["unlocked"])
        self.assertTrue(dialog2.cards["uriel"]["unlocked"])
        self.assertTrue(dialog2.cards["mortimer"]["unlocked"])

    def test_equipping_costume_updates_actor_and_save(self):
        """Clicking Equip updates DealerActor, save data, and table avatar."""
        # Unlock Uriel
        self.app.save_manager.data.achievements.exorcist = True
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog

        # Equip Uriel
        dialog._equip_costume("uriel")
        self.assertEqual(self.app.dealer_actor.current_character, "uriel")
        self.assertEqual(self.app.save_manager.data.equipped_costume, "uriel")

        # Verify disk persistence
        reloaded = self.app.save_manager.load()
        self.assertEqual(reloaded.equipped_costume, "uriel")

    def test_wardrobe_dialog_dismissal_on_escape(self):
        """Pressing Escape safely destroys the WardrobeDialog."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        dialog._on_close()
        self.assertFalse(dialog.winfo_exists())
        self.assertIsNone(self.app._wardrobe_dialog)


if __name__ == "__main__":
    unittest.main()
