import os
import unittest
from pathlib import Path
import tkinter
import blackjack


class TestDeckAndAssets(unittest.TestCase):
    """Test suite for validating card assets and deck composition."""

    @classmethod
    def setUpClass(cls):
        # Determine the cards asset directory relative to project root
        cls.project_root = Path(__file__).resolve().parent.parent
        cls.cards_dir = cls.project_root / "cards"

    def test_asset_files_exist(self):
        suits = ["heart", "club", "diamond", "spade"]
        ranks = [str(n) for n in range(1, 11)] + ["jack", "queen", "king"]

        self.assertTrue(self.cards_dir.exists(), f"Cards directory not found at {self.cards_dir}")

        for suit in suits:
            for rank in ranks:
                card_filename = f"{rank}_{suit}.png"
                card_path = self.cards_dir / card_filename
                self.assertTrue(
                    card_path.is_file(),
                    f"Expected card asset does not exist: {card_filename}"
                )

        # Check for card back image
        back_path = self.cards_dir / "back.png"
        self.assertTrue(back_path.is_file(), "Expected card back image 'back.png' to exist.")

    def test_deck_distribution_values(self):
        """Simulate loading the 52 cards and verify value counts."""
        suits = ["heart", "club", "diamond", "spade"]
        face_cards = ["jack", "queen", "king"]

        card_values = []
        for suit in suits:
            for card in range(1, 11):
                card_values.append(card)
            for card in face_cards:
                card_values.append(10)

        self.assertEqual(len(card_values), 52)
        # 4 aces (value 1)
        self.assertEqual(card_values.count(1), 4)
        # 16 ten-value cards (10, jack, queen, king for each of 4 suits)
        self.assertEqual(card_values.count(10), 16)
        # 4 of each card 2 through 9
        for val in range(2, 10):
            self.assertEqual(card_values.count(val), 4, f"Value {val} should appear 4 times")

    def test_load_images_creates_52_cards(self):
        """Test load_images using a hidden Tk root."""
        root = tkinter.Tk()
        root.withdraw()
        try:
            # Change CWD temporarily if needed or test load_images
            old_cwd = os.getcwd()
            os.chdir(self.project_root)
            try:
                card_list = []
                blackjack.load_images(card_list)
                self.assertEqual(len(card_list), 52)
                # Verify each item is a (value, PhotoImage) tuple
                for val, img in card_list:
                    self.assertIsInstance(val, int)
                    self.assertIsInstance(img, tkinter.PhotoImage)
            finally:
                os.chdir(old_cwd)
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
