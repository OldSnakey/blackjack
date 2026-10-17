"""
Unit test suite for Phase B: Layered Sprite Character Roster (4 Personalities) & DealerActor Compositor.

Validates:
- Asset existence and loadability for all 4 character layered sprite sets (13 layers each in 1x and 2x).
- Character audio accent existence in audio/haunted/.
- DealerActor layer compositor assembly, state management (eyes, mouth, arms), and alpha blending.
- Layer permutations produce visually distinct composite outputs.
- Costume switching across Julian, Malphas, Uriel, and Mortimer with alias normalization.
- Game state immutability when switching costumes (bankroll, hands, deck untouched).
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
    Phase,
)
from dealer_actor import (
    DealerActor,
    CharacterProfile,
    CHARACTERS,
    COSTUME_ALIASES,
)

CHARACTERS_DIR = HAUNTED_ASSETS_DIR / "characters"
AUDIO_DIR = BASE_DIR / "audio" / "haunted"


class TestCharacterAssets(unittest.TestCase):
    """Verifies that all required character layers and audio assets exist on disk."""

    REQUIRED_CHARACTERS = ["julian", "malphas", "uriel", "mortimer"]
    REQUIRED_LAYERS = [
        "torso.png", "torso_2x.png",
        "head.png", "head_2x.png",
        "eyes_open.png", "eyes_open_2x.png",
        "eyes_half.png", "eyes_half_2x.png",
        "eyes_closed.png", "eyes_closed_2x.png",
        "mouth_neutral.png", "mouth_neutral_2x.png",
        "mouth_talk.png", "mouth_talk_2x.png",
        "mouth_smirk.png", "mouth_smirk_2x.png",
        "mouth_gasp.png", "mouth_gasp_2x.png",
        "arm_rest.png", "arm_rest_2x.png",
        "arm_deal.png", "arm_deal_2x.png",
        "arm_peek.png", "arm_peek_2x.png",
        "bust.png", "bust_2x.png",
    ]

    def test_character_directories_and_layers_exist(self):
        """Every character directory must contain all 26 required layer assets."""
        self.assertTrue(CHARACTERS_DIR.exists(), f"Missing directory: {CHARACTERS_DIR}")
        for char_id in self.REQUIRED_CHARACTERS:
            char_path = CHARACTERS_DIR / char_id
            self.assertTrue(char_path.is_dir(), f"Character directory missing: {char_id}")
            for filename in self.REQUIRED_LAYERS:
                layer_file = char_path / filename
                self.assertTrue(layer_file.exists(), f"Layer file missing: {char_id}/{filename}")
                with Image.open(layer_file) as img:
                    self.assertEqual(img.mode, "RGBA", f"Layer {char_id}/{filename} must have RGBA alpha channel")
                    if "_2x" in filename:
                        self.assertEqual(img.size, (224, 224), f"2x layer {filename} must be 224x224")
                    else:
                        self.assertEqual(img.size, (112, 112), f"1x layer {filename} must be 112x112")

    def test_character_audio_accents_exist(self):
        """Audio accent files for all 4 characters must exist in audio/haunted/."""
        self.assertTrue(AUDIO_DIR.exists())
        expected_audio = [
            "dealer_julian.ogg",
            "dealer_malphas.ogg",
            "dealer_uriel.ogg",
            "dealer_mortimer.ogg",
        ]
        for audio_name in expected_audio:
            path = AUDIO_DIR / audio_name
            self.assertTrue(path.exists(), f"Audio accent missing: {audio_name}")
            self.assertGreater(path.stat().st_size, 1000, f"Audio accent file empty: {audio_name}")


class TestDealerActorCompositor(unittest.TestCase):
    """Verifies DealerActor layering, state permutations, costume swapping, and scaling."""

    def setUp(self):
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.actor = DealerActor(master=self.root, scale_factor=1.0)

    def tearDown(self):
        try:
            self.root.destroy()
        except Exception:
            pass

    def test_default_costume_is_julian(self):
        """DealerActor initializes with Julian as the default croupier."""
        self.assertEqual(self.actor.current_character, "julian")
        profile = self.actor.get_profile()
        self.assertEqual(profile.id, "julian")
        self.assertEqual(profile.name, "Julian")
        self.assertEqual(profile.title, "The Classic Croupier")
        self.assertEqual(profile.theme, "casino")

    def test_composite_image_geometry(self):
        """Compositing produces a 112x112 RGBA image in 1x mode and 224x224 in 2x mode."""
        img_1x = self.actor.get_composite_image()
        self.assertIsInstance(img_1x, Image.Image)
        self.assertEqual(img_1x.size, (112, 112))
        self.assertEqual(img_1x.mode, "RGBA")

        # 2x scaling
        self.actor.set_scale(2.0)
        img_2x = self.actor.get_composite_image()
        self.assertEqual(img_2x.size, (224, 224))
        self.assertEqual(img_2x.mode, "RGBA")

    def test_layer_state_permutations(self):
        """Changing eye, mouth, or arm states updates internal state and alters composite output."""
        self.actor.equip_costume("julian")
        self.actor.set_eye_state("open")
        self.actor.set_mouth_state("neutral")
        self.actor.set_arm_state("rest")
        img_neutral = self.actor.get_composite_image().tobytes()

        # Blink (eyes closed)
        self.actor.set_eye_state("closed")
        self.assertEqual(self.actor.eye_state, "closed")
        img_blink = self.actor.get_composite_image().tobytes()
        self.assertNotEqual(img_neutral, img_blink, "Blink must alter composite pixel data")

        # Talk (mouth talk)
        self.actor.set_eye_state("open")
        self.actor.set_mouth_state("talk")
        self.assertEqual(self.actor.mouth_state, "talk")
        img_talk = self.actor.get_composite_image().tobytes()
        self.assertNotEqual(img_neutral, img_talk, "Talking mouth must alter composite pixel data")

        # Deal arm
        self.actor.set_mouth_state("neutral")
        self.actor.set_arm_state("deal")
        self.assertEqual(self.actor.arm_state, "deal")
        img_deal = self.actor.get_composite_image().tobytes()
        self.assertNotEqual(img_neutral, img_deal, "Deal arm gesture must alter composite pixel data")

    def test_costume_switching_and_aliases(self):
        """Equipping costumes updates character identity and resolves alias keys."""
        # Direct character IDs
        for char_id in ("julian", "malphas", "uriel", "mortimer"):
            self.actor.equip_costume(char_id)
            self.assertEqual(self.actor.current_character, char_id)
            self.assertEqual(self.actor.get_profile().id, char_id)

        # Alias resolution
        self.actor.equip_costume("classic")
        self.assertEqual(self.actor.current_character, "julian")

        self.actor.equip_costume("pit_fiend")
        self.assertEqual(self.actor.current_character, "malphas")

        self.actor.equip_costume("seraph")
        self.assertEqual(self.actor.current_character, "uriel")

        self.actor.equip_costume("grim_bones")
        self.assertEqual(self.actor.current_character, "mortimer")

    def test_photo_image_caching(self):
        """get_photo_image returns a valid Tkinter PhotoImage and re-uses cache when unchanged."""
        photo1 = self.actor.get_photo_image()
        self.assertIsNotNone(photo1)
        photo2 = self.actor.get_photo_image()
        self.assertIs(photo1, photo2, "Unmodified state must return cached PhotoImage instance")

        # Modifying state invalidates cache
        self.actor.set_eye_state("closed")
        photo3 = self.actor.get_photo_image()
        self.assertIsNotNone(photo3)
        self.assertIsNot(photo1, photo3, "State change must regenerate PhotoImage cache")


class TestDealerActorAppIntegration(unittest.TestCase):
    """Verifies DealerActor integration within BlackjackApp and table state immutability."""

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

    def test_app_has_dealer_actor(self):
        """BlackjackApp instantiates and exposes dealer_actor."""
        self.assertTrue(hasattr(self.app, "dealer_actor"))
        self.assertIsInstance(self.app.dealer_actor, DealerActor)

    def test_costume_switch_immutability(self):
        """Equipping a costume does not mutate bankroll, hands, deck, or active bets."""
        initial_bankroll = self.app.bankroll_var.get()
        initial_deck_len = len(self.app.deck)
        initial_bet = self.app.current_bet_var.get()

        # Equip each character
        for costume in ("malphas", "uriel", "mortimer", "julian"):
            self.app.dealer_actor.equip_costume(costume)
            self.app._update_dealer_avatar()
            self.root.update_idletasks()

            self.assertEqual(self.app.bankroll_var.get(), initial_bankroll)
            self.assertEqual(len(self.app.deck), initial_deck_len)
            self.assertEqual(self.app.current_bet_var.get(), initial_bet)

    def test_phase_automatic_costume_sync(self):
        """Phase transitions synchronize the appropriate dealer character profile."""
        # Hell's Table -> Malphas
        self.app.haunted.start_hell_table()
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.app._update_dealer_avatar()
        self.assertEqual(self.app.dealer_actor.current_character, "malphas")

        # Victory -> Uriel
        self.app.haunted.phase = Phase.VICTORY
        self.app._apply_phase_theme(Phase.VICTORY)
        self.app._update_dealer_avatar()
        self.assertEqual(self.app.dealer_actor.current_character, "uriel")

        # Normal -> Default / Julian
        self.app.haunted.phase = Phase.NORMAL
        self.app._apply_phase_theme(Phase.NORMAL)
        self.app._update_dealer_avatar()
        self.assertEqual(self.app.dealer_actor.current_character, "julian")

    def test_hell_table_uses_malphas_and_bust_dialog(self):
        """Hell's table activates Malphas Graphic Novel sprite and uses high-res bust in dialogue."""
        bust_photo = self.app.dealer_actor.get_bust_photo_image("malphas")
        self.assertIsNotNone(bust_photo)
        self.assertIsInstance(bust_photo, (tkinter.PhotoImage, ImageTk.PhotoImage))

        # Transition to Hell's Table
        self.app.haunted.start_hell_table()
        self.app._apply_phase_theme(Phase.HELL_TABLE)
        self.app._update_dealer_avatar()

        current_avatar_img = self.app.dealer_avatar_label.image
        self.assertIsNotNone(current_avatar_img)
        self.assertNotEqual(current_avatar_img, self.app.haunted_assets.get("dealer_demon_0"))
        self.assertNotEqual(current_avatar_img, self.app.haunted_assets.get("dealer_demon_1"))

        # Ambient animations tick should NOT overwrite dealer_avatar_label with legacy sprite
        self.app._tick_ambient_animations()
        self.assertEqual(self.app.dealer_avatar_label.image, current_avatar_img)

        # Pit fiend dialogue must use the high-res Malphas bust portrait
        self.app._show_pit_fiend_dialog()
        self.assertIsNotNone(self.app._active_story_dialog)
        self.assertEqual(self.app._active_story_dialog.portrait_img, bust_photo)
        self.assertNotEqual(self.app._active_story_dialog.portrait_img, self.app.haunted_assets.get("dealer_demon_0"))
        if self.app._active_story_dialog.winfo_exists():
            self.app._active_story_dialog.destroy()


if __name__ == "__main__":
    unittest.main()
