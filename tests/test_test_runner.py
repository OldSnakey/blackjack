import os
import unittest
from pathlib import Path

import run_tests


class TestRunnerSuiteInvariants(unittest.TestCase):
    """Validates the tiered test runner configuration, module existence, and CLI parsing."""

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.tests_dir = self.repo_root / "tests"

    def test_tier_definitions_exist(self):
        """All required tiers ('smoke', 'core', 'betting', 'dealer', 'haunted', 'gui', 'full') are defined."""
        expected_tiers = {"smoke", "core", "betting", "dealer", "haunted", "gui", "full"}
        available = set(run_tests.TIERS.keys()) | {"full"}
        self.assertTrue(expected_tiers.issubset(available))

    def test_all_configured_test_modules_exist_on_disk(self):
        """Every module listed in run_tests.TIERS maps to an existing file in tests/."""
        for tier_name, modules in run_tests.TIERS.items():
            self.assertGreater(len(modules), 0, f"Tier '{tier_name}' must not be empty")
            for mod_name in modules:
                # mod_name is e.g. 'tests.test_hand'
                rel_path = mod_name.replace(".", os.sep) + ".py"
                full_path = self.repo_root / rel_path
                self.assertTrue(
                    full_path.is_file(),
                    f"Module '{mod_name}' in tier '{tier_name}' does not exist at {full_path}",
                )

    def test_resolve_modules_for_smoke_and_full(self):
        """resolve_modules returns the curated list for 'smoke' and all discovered files for 'full'."""
        smoke_mods = run_tests.resolve_modules("smoke")
        self.assertEqual(smoke_mods, run_tests.TIERS["smoke"])
        self.assertIn("tests.test_state_machine", smoke_mods)
        self.assertIn("tests.test_test_runner", smoke_mods)

        full_mods = run_tests.resolve_modules("full")
        self.assertGreaterEqual(len(full_mods), 42)
        for sm in smoke_mods:
            self.assertIn(sm, full_mods)

    def test_cli_parser_defaults_and_flags(self):
        """CLI parser defaults to 'smoke' tier and supports --list, --verbose, --failfast, and -k."""
        args_default = run_tests.parse_args([])
        self.assertEqual(args_default.tier, "smoke")
        self.assertFalse(args_default.list_tiers)
        self.assertFalse(args_default.failfast)

        args_custom = run_tests.parse_args(["dealer", "-v", "-f", "-k", "wardrobe"])
        self.assertEqual(args_custom.tier, "dealer")
        self.assertTrue(args_custom.verbose)
        self.assertTrue(args_custom.failfast)
        self.assertEqual(args_custom.pattern, "wardrobe")

    def test_build_test_suite_loads_cases(self):
        """build_suite constructs a valid non-empty unittest.TestSuite for a given module list."""
        suite = run_tests.build_suite(["tests.test_hand", "tests.test_version"])
        self.assertGreater(suite.countTestCases(), 0)

        # Pattern filter narrows down test cases
        filtered = run_tests.build_suite(["tests.test_version"], pattern="nonexistent_xyz_pattern")
        self.assertEqual(filtered.countTestCases(), 0)


if __name__ == "__main__":
    unittest.main()

