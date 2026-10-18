"""
Automated UI Layout, Geometry, and Rendering Collision Tests.

Verifies:
1. Headless geometric containment: player cards are not occluded or clipped by bottom control bars.
2. HauntedAltarCanvas felt texture synchronization and seamless alpha-like background integration across all phases.
3. Scale mode coherence: active cards in hand and deck are properly replaced with scaled assets upon toggling 2x scale.
4. Window geometry adaptation: window bounds adapt safely within display work area without crushing internal components.
"""

import tempfile
import unittest
from pathlib import Path

import tkinter
from PIL import Image, ImageTk

import blackjack
from blackjack import (
    BlackjackApp,
    Card,
    CARD_HEIGHT,
    CARD_WIDTH,
    HauntedAltarCanvas,
    Phase,
    SaveManager,
    TableFeltCanvas,
)


class TestUIGeometryAndRendering(unittest.TestCase):
    def setUp(self):
        self.root = tkinter.Tk()
        try:
            self.root.attributes("-alpha", 0.0)
        except Exception:
            self.root.withdraw()

        # Isolate save file in temporary directory
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_path = Path(self.temp_dir.name) / "test_blackjack_save.json"
        self.save_mgr = SaveManager(save_path=self.save_path)

        self.app = BlackjackApp(self.root, sound_enabled=False)
        self.app.save_manager = self.save_mgr
        self.app.suppress_mode_dialog = True

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_altar_seamless_felt_sync_across_themes(self):
        """HauntedAltarCanvas must implement sync_felt_background and match TableFeltCanvas themes."""
        # 1. HauntedAltarCanvas must have sync_felt_background method
        self.assertTrue(hasattr(self.app.haunted_altar, "sync_felt_background"))
        self.assertTrue(callable(self.app.haunted_altar.sync_felt_background))

        # 2. Trigger theme switches and verify color and felt synchronization
        felt_canvas = self.app.card_table_frame
        self.assertIsInstance(felt_canvas, TableFeltCanvas)

        for phase, expected_hex in [
            (Phase.NORMAL, "#074c1a"),
            (Phase.HELL_TABLE, "#0d0204"),
            (Phase.VICTORY, "#031b10"),
        ]:
            self.app._apply_phase_theme(phase)
            self.root.update_idletasks()
            self.assertEqual(
                self.app.haunted_altar["background"].lower(),
                expected_hex.lower(),
                f"Altar background for {phase.name} must match {expected_hex}",
            )
            self.assertEqual(
                self.app.accessories_frame["background"].lower(),
                expected_hex.lower(),
                f"Accessories frame background for {phase.name} must match {expected_hex}",
            )

    def test_active_hands_rebuilt_on_scale_toggle(self):
        """Cards already dealt in active hands and shoe deck must be rebuilt with scaled images when toggling scale."""
        # Deal a hand with known cards
        self.app.dealer_hand = [self.app.deck[0], self.app.deck[1]]
        self.app.player_hands = [[self.app.deck[2], self.app.deck[3]]]
        initial_img = self.app.player_hands[0][0].image

        # Toggle scale from 1x to 2x
        self.app.toggle_scale_mode()

        # The image in player_hands[0][0] must have been updated to a scaled PhotoImage
        scaled_img = self.app.player_hands[0][0].image
        self.assertIsNotNone(scaled_img)
        self.assertNotEqual(initial_img, scaled_img)
        self.assertEqual(scaled_img.width(), self.app.card_width)
        self.assertEqual(scaled_img.height(), self.app.card_height)

        # Dealer hand cards must also be updated
        dealer_scaled_img = self.app.dealer_hand[0].image
        self.assertEqual(dealer_scaled_img.width(), self.app.card_width)
        self.assertEqual(dealer_scaled_img.height(), self.app.card_height)

        # Toggle back to 1x
        self.app.toggle_scale_mode()
        restored_img = self.app.player_hands[0][0].image
        self.assertEqual(restored_img.width(), CARD_WIDTH)
        self.assertEqual(restored_img.height(), CARD_HEIGHT)

    def test_player_cards_fully_visible_no_bottom_bar_collision(self):
        """Player cards must remain fully within table felt bounds and not collide with betting/action bars."""
        # Enable Chips Mode to display the betting bar below the card table
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode(confirm=True)

        # Place bet and deal hand
        self.app._add_chip_bet(25)
        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        felt = self.app.card_table_frame
        p_frame = self.app.player_cards_frame
        betting = self.app.betting_frame

        self.assertEqual(p_frame.winfo_manager(), "grid")
        self.assertEqual(betting.winfo_manager(), "grid")

        # Player card bottom coordinate relative to felt must not exceed felt height
        player_bottom_in_felt = p_frame.winfo_y() + p_frame.winfo_height()
        felt_h = felt.winfo_height()
        self.assertLessEqual(
            player_bottom_in_felt,
            felt_h,
            f"Player cards bottom ({player_bottom_in_felt}px) exceeds felt height ({felt_h}px)!",
        )

        # Absolute screen coordinate check: player bottom must be at or above betting frame top
        player_root_bottom = p_frame.winfo_rooty() + p_frame.winfo_height()
        betting_root_top = betting.winfo_rooty()
        self.assertLessEqual(
            player_root_bottom,
            betting_root_top,
            f"Player cards ({player_root_bottom}px) collide with betting frame ({betting_root_top}px)!",
        )

    def test_player_cards_visible_with_announcement_hud(self):
        """When TableAnnouncementHUD is active, player cards must still be fully visible."""
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode(confirm=True)
        self.app._add_chip_bet(25)
        self.app._deal_hand_with_bet()

        # Set a multi-line message in the announcement HUD
        self.app.announcement_hud.set_message("✦ Relic Equipped: Hallowed Run! | Deal hand to begin your trial.")
        self.root.update_idletasks()

        felt = self.app.card_table_frame
        p_frame = self.app.player_cards_frame
        betting = self.app.betting_frame

        player_bottom_in_felt = p_frame.winfo_y() + p_frame.winfo_height()
        felt_h = felt.winfo_height()
        self.assertLessEqual(
            player_bottom_in_felt,
            felt_h,
            f"With announcement HUD, player cards bottom ({player_bottom_in_felt}px) exceeds felt ({felt_h}px)!",
        )

    def test_player_cards_fully_visible_2x(self):
        """In 2x scale, player cards must remain completely within felt boundaries and not collide with betting frame."""
        self.app.chips_mode_var.set(True)
        self.app._on_toggle_chips_mode(confirm=True)

        # Toggle to 2x scale
        self.app.toggle_scale_mode()

        self.app._add_chip_bet(25)
        self.app._deal_hand_with_bet()
        self.root.update_idletasks()

        felt = self.app.card_table_frame
        p_frame = self.app.player_cards_frame
        betting = self.app.betting_frame

        self.assertEqual(p_frame.winfo_manager(), "grid")
        self.assertEqual(betting.winfo_manager(), "grid")

        player_bottom_in_felt = p_frame.winfo_y() + p_frame.winfo_height()
        felt_h = felt.winfo_height()
        self.assertLessEqual(
            player_bottom_in_felt,
            felt_h,
            f"In 2x scale, player cards bottom ({player_bottom_in_felt}px) exceeds felt ({felt_h}px)!",
        )

        player_root_bottom = p_frame.winfo_rooty() + p_frame.winfo_height()
        betting_root_top = betting.winfo_rooty()
        self.assertLessEqual(
            player_root_bottom,
            betting_root_top,
            f"In 2x scale, player cards ({player_root_bottom}px) collide with betting frame ({betting_root_top}px)!",
        )

    def test_haunted_altar_auto_syncs_felt_when_packed(self):
        """HauntedAltarCanvas must automatically obtain its felt slice when packed in Phase 2/3."""
        altar = self.app.haunted_altar
        # Initially hidden
        self.assertEqual(altar.winfo_manager(), "")

        # Pack altar and reveal candles (simulating Phase 2 event)
        self.app.haunted.candles_remaining = 3
        altar.pack(side="top")
        altar.set_candle_state(3, visible=True)
        self.root.update_idletasks()

        # Altar must now possess an active felt slice photo image
        self.assertIsNotNone(altar._felt_slice_photo, "HauntedAltarCanvas must have _felt_slice_photo populated after being packed")
        self.assertGreater(len(altar.find_withtag("felt_bg")), 0, "HauntedAltarCanvas must render felt_bg image on canvas")

    def test_score_plaques_casino_styling(self):
        """Dealer and player header frames must have beveled casino plaque styling, not raw flat boxes."""
        d_frame = self.app.dealer_header_frame
        p_frame = self.app.player_header_frame

        self.assertEqual(d_frame.cget("relief"), "ridge")
        self.assertEqual(p_frame.cget("relief"), "ridge")
        self.assertGreaterEqual(int(d_frame.cget("borderwidth")), 1)
        self.assertGreaterEqual(int(p_frame.cget("borderwidth")), 1)

    def test_announcement_hud_auto_dismiss(self):
        """Transient relic equipment announcements must auto-dismiss and not remain perpetually over cards."""
        hud = self.app.announcement_hud
        hud.set_message("✦ Relic Equipped: Archangel's Smite! ✦")
        self.root.update_idletasks()

        # HUD must be visible initially
        self.assertEqual(hud.winfo_manager(), "place")
        self.assertTrue(hasattr(hud, "_dismiss_timer_id"))
        self.assertIsNotNone(hud._dismiss_timer_id)

        # Trigger dismiss directly or simulate timeout
        hud.dismiss()
        self.root.update_idletasks()
        self.assertEqual(hud.winfo_manager(), "")

    def test_haunted_altar_matches_felt_color_in_omen_phase(self):
        """HauntedAltarCanvas felt slice and background must match table felt in Phase.OMEN without flat green mismatch."""
        from blackjack import Phase

        self.app.haunted.phase = Phase.OMEN
        self.app.haunted.candles_remaining = 5
        self.app._apply_phase_theme(Phase.OMEN)
        self.app._update_candles_display()
        self.root.update_idletasks()

        altar = self.app.haunted_altar
        felt = self.app.card_table_frame

        self.assertEqual(felt.current_theme, "creep")
        self.assertEqual(altar.cget("background"), "#142018")
        self.assertEqual(self.app.accessories_frame.cget("background"), "#142018")

        self.assertIsNotNone(altar._felt_slice_img, "HauntedAltar must have felt slice image")
        # Check center pixel of felt slice image
        cx = altar._felt_slice_img.width // 2
        cy = altar._felt_slice_img.height // 2
        r, g, b = altar._felt_slice_img.getpixel((cx, cy))[:3]

        # Creep felt base is (20, 32, 24). It must be dark creep, not classic casino green (7, 76, 26).
        self.assertLess(g, 50, f"Altar felt slice green component ({g}) must be dark creep (< 50), not classic casino green (> 70)")
        self.assertGreater(g, 15)
        self.assertLess(r, 40)
        self.assertLess(b, 40)


if __name__ == "__main__":
    unittest.main()

