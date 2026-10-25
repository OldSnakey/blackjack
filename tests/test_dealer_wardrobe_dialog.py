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
from unittest.mock import MagicMock
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
        total_pages = len(dialog.PAGE_CONFIG)
        self.assertEqual(dialog.current_page, 0)
        self.assertIn(f"Page 1 of {total_pages}", dialog.page_lbl.cget("text"))

        # Switch to Page 2
        dialog._next_page()
        self.assertEqual(dialog.current_page, 1)
        self.assertIn(f"Page 2 of {total_pages}", dialog.page_lbl.cget("text"))

        # Switch back to Page 1
        dialog._prev_page()
        self.assertEqual(dialog.current_page, 0)
        self.assertIn(f"Page 1 of {total_pages}", dialog.page_lbl.cget("text"))

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

    def test_wardrobe_tab2_hof_scrollable_plaques(self):
        """Tab 2 (Hall of Fame) contains all 8 plaques in a scrollable frame with mousewheel support."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertIsNotNone(dialog)

        # Switch to Tab 2
        dialog._switch_tab(1)
        self.assertEqual(dialog.current_tab, 1)

        # Check all 8 plaques are registered
        self.assertEqual(len(dialog.plaque_widgets), 8)
        for ach_id in ("exorcist", "high_roller", "natural_streak", "cursed_survivor",
                       "split_maestro", "big_spender", "apprentice_counter", "master_counter"):
            self.assertIn(ach_id, dialog.plaque_widgets)

        # Verify scrollable canvas or mousewheel support on Tab 2
        self.assertTrue(
            hasattr(dialog, "hof_canvas") or hasattr(dialog, "_on_hof_mousewheel") or hasattr(dialog, "_on_mousewheel")
        )

    def test_voice_button_triggers_speech_bubble_and_tail(self):
        """Clicking Voice on a character card renders a speech bubble with directional tail and streams Animalese."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertIsNotNone(dialog)

        # Mock sound manager play_dialogue_blip
        mock_blip = MagicMock()
        self.app.sound_manager.play_dialogue_blip = mock_blip

        panel = dialog.cards["julian"]["panel"]
        self.assertFalse(panel._speech_active)
        self.assertEqual(len(panel.find_withtag("speech_bubble")), 0)

        # Trigger voice preview
        panel._play_voice()
        self.assertTrue(panel._speech_active)

        # Verify speech bubble and tail items are created on canvas
        bubble_items = panel.find_withtag("speech_bubble")
        self.assertGreater(len(bubble_items), 0, "Speech bubble elements should be rendered on canvas")

        # Step typewriter
        dialog.update()
        self.assertTrue(mock_blip.called, "Animalese play_dialogue_blip should be called during speech stream")
        args, kwargs = mock_blip.call_args
        self.assertEqual(args[0], "julian")

        # Cleanup
        panel.dismiss_speech_bubble()
        self.assertFalse(panel._speech_active)
        self.assertEqual(len(panel.find_withtag("speech_bubble")), 0)
        dialog._on_close()

    def test_voice_speech_bubble_dismissal_and_navigation_cleanup(self):
        """Navigating pages or closing dialog cleanly dismisses active speech bubbles and stops timers."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog

        panel_julian = dialog.cards["julian"]["panel"]
        panel_julian._play_voice()
        self.assertTrue(panel_julian._speech_active)

        # Switching page dismisses voice bubble
        dialog._next_page()
        self.assertFalse(panel_julian._speech_active)
        self.assertIsNone(panel_julian._speech_timer_id)
        self.assertEqual(len(panel_julian.find_withtag("speech_bubble")), 0)

        dialog._on_close()

    def test_equipped_button_disabled_gold_text_override(self):
        """Equipped dealer button uses recessed disabled slot sprite with bright gold (#ffd700) text."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog

        # Julian is equipped by default
        julian_btn = dialog.cards["julian"]["panel"].equip_btn
        self.assertFalse(julian_btn.enabled)
        self.assertEqual(julian_btn.text, "✦ EQUIPPED")
        self.assertEqual(julian_btn.disabled_text_color, "#ffd700")

        # Verify canvas text fill color is bright gold #ffd700
        canvas = dialog.cards["julian"]["panel"]
        text_fill = canvas.itemcget(julian_btn.text_id, "fill")
        self.assertEqual(text_fill, "#ffd700")

        # Tiffany is unlocked and unequipped -> enabled green button
        tiffany_btn = dialog.cards["tiffany"]["panel"].equip_btn
        self.assertTrue(tiffany_btn.enabled)
        self.assertEqual(tiffany_btn.text, "Equip Costume")

        # Selene on Page 3 is locked -> disabled with default muted brown text
        dialog._switch_page(2)
        selene_btn = dialog.cards["selene"]["panel"].equip_btn
        self.assertFalse(selene_btn.enabled)
        self.assertEqual(selene_btn.text, "Locked")
        self.assertIsNone(selene_btn.disabled_text_color)
        canvas_selene = dialog.cards["selene"]["panel"]
        selene_fill = canvas_selene.itemcget(selene_btn.text_id, "fill")
        self.assertEqual(selene_fill, "#5e4337")

        dialog._on_close()

    def test_status_badge_bracket_free_and_tab2_styling(self):
        """Status badges on Tab 1 are bracket-free ('✓ Unlocked' / '🔒 Locked'), Tab 2 records bullets are aligned, and descriptions use m5x7 @ -16 #d8e2dc."""
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog

        # Tab 1: Julian (unlocked) status badge
        julian_panel = dialog.cards["julian"]["panel"]
        badge_text = julian_panel.itemcget(julian_panel.status_badge_id, "text")
        self.assertEqual(badge_text, "✓ Unlocked")
        self.assertNotIn("[", badge_text)
        self.assertNotIn("]", badge_text)

        # Tab 1: Selene on Page 3 (locked) status badge and header
        dialog._switch_page(2)
        selene_panel = dialog.cards["selene"]["panel"]
        selene_badge = selene_panel.itemcget(selene_panel.status_badge_id, "text")
        self.assertEqual(selene_badge, "🔒 Locked")
        self.assertNotIn("[", selene_badge)
        self.assertNotIn("]", selene_badge)

        req_header = selene_panel.itemcget(selene_panel.req_header_id, "text")
        self.assertEqual(req_header, "🔒 UNLOCK REQUIREMENT:")
        self.assertNotIn("[", req_header)
        self.assertNotIn("]", req_header)

        # Tab 2: Switch to Hall of Fame
        dialog._switch_tab(1)
        dialog.update()

        # Check records plaque bullet alignment
        self.assertEqual(dialog._records_canvas.itemcget(dialog.dot_peak_record, "text"), "•")
        self.assertEqual(dialog._records_canvas.coords(dialog.dot_peak_record)[1], 41.0)
        self.assertEqual(dialog._records_canvas.coords(dialog.lbl_peak_record)[1], 38.0)
        self.assertIn("Peak Bankroll", dialog._records_canvas.itemcget(dialog.lbl_peak_record, "text"))

        # Check achievement plaque description styling
        exorcist_plaque = dialog.plaque_widgets["exorcist"]["frame"]
        items = exorcist_plaque.find_all()
        # Find description text item (at y=34)
        desc_items = [it for it in items if exorcist_plaque.type(it) == "text" and exorcist_plaque.coords(it)[1] == 34.0]
        self.assertEqual(len(desc_items), 1)
        desc_id = desc_items[0]
        self.assertEqual(exorcist_plaque.itemcget(desc_id, "fill"), "#d8e2dc")

        dialog._on_close()


if __name__ == "__main__":
    unittest.main()



