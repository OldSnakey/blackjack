"""
Unit test suite verifying application versioning governance in Blackjack.

Validates:
- Presence of __version__ at the module level in blackjack.py.
- Strict compliance with Semantic Versioning (MAJOR.MINOR.PATCH).
- Synchronization with the Tkinter root window title.
"""

from __future__ import annotations

import re
import unittest
import tkinter

import blackjack
from blackjack import BlackjackApp, __version__


class TestApplicationVersion(unittest.TestCase):
    """Ensures versioning invariants are strictly maintained across code and UI."""

    SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")

    def test_version_attribute_exists(self):
        """Module must expose a string __version__ attribute."""
        self.assertTrue(hasattr(blackjack, "__version__"))
        self.assertIsInstance(blackjack.__version__, str)

    def test_version_matches_semantic_versioning(self):
        """Version string must strictly adhere to Semantic Versioning (X.Y.Z)."""
        self.assertRegex(
            __version__,
            self.SEMVER_PATTERN,
            f"Version '{__version__}' does not adhere to SemVer format (e.g., 1.0.0)",
        )

    def test_window_title_includes_version(self):
        """Tkinter root window title must display the current version."""
        root = tkinter.Tk()
        root.withdraw()
        try:
            app = BlackjackApp(root, sound_enabled=False)
            expected_title = f"Blackjack v{__version__}"
            self.assertEqual(root.title(), expected_title)
        finally:
            app._on_close()

    def test_version_defined_solely_in_blackjack_module(self):
        """__version__ must be maintained solely in blackjack.py, not duplicated as APP_VERSION in config.py."""
        import config
        self.assertFalse(hasattr(config, "APP_VERSION"))


if __name__ == "__main__":
    unittest.main()
