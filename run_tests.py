"""
Tiered Test Runner for the Blackjack Desktop Application.

Provides fast smoke tests (~15s), targeted subsystem suites (~30-90s), and the full
system regression suite (~5-6m) using Python's built-in unittest framework.

Usage Examples:
    python run_tests.py                 # Runs fast smoke suite (default)
    python run_tests.py smoke           # Runs fast smoke suite (~15s)
    python run_tests.py core            # Runs core domain & rules subsystem (~25s)
    python run_tests.py betting         # Runs wagering & chip visualizer suite (~40s)
    python run_tests.py dealer          # Runs dealer actor, puppet & wardrobe suite (~75s)
    python run_tests.py haunted         # Runs supernatural & altar suite (~55s)
    python run_tests.py gui             # Runs Tkinter table felt, layout & modal suite (~90s)
    python run_tests.py full            # Runs complete 42+ module system suite (~6m)
    python run_tests.py --list          # Lists all available tiers and modules
    python run_tests.py smoke -v -f     # Verbose output, stop on first failure
    python run_tests.py gui -k split    # Filter tests matching pattern 'split'
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

REPO_ROOT = Path(__file__).resolve().parent
TESTS_DIR = REPO_ROOT / "tests"

TIERS: Dict[str, List[str]] = {
    "smoke": [
        "tests.test_basic_strategy",
        "tests.test_card_counter",
        "tests.test_chip_visualizer_interactions",
        "tests.test_deck",
        "tests.test_dialogue_voice_engine",
        "tests.test_event_bus",
        "tests.test_game_engine",
        "tests.test_game_rules",
        "tests.test_hand",
        "tests.test_house_rules",
        "tests.test_multi_seat_engine",
        "tests.test_pixel_ui",
        "tests.test_roster_puppet_conversion",
        "tests.test_save_manager",
        "tests.test_scoring",
        "tests.test_state_machine",
        "tests.test_table_hud",
        "tests.test_test_runner",
        "tests.test_tripometer",
        "tests.test_ui_layout",
        "tests.test_universal_puppet_faceplates",
        "tests.test_version",
    ],
    "core": [
        "tests.test_basic_strategy",
        "tests.test_card_counter",
        "tests.test_counting_bootcamp",
        "tests.test_deck",
        "tests.test_double_down",
        "tests.test_event_bus",
        "tests.test_game_engine",
        "tests.test_game_rules",
        "tests.test_hand",
        "tests.test_house_rules",
        "tests.test_multi_seat_engine",
        "tests.test_save_manager",
        "tests.test_scoring",
        "tests.test_shoe",
        "tests.test_sound",
        "tests.test_split",
        "tests.test_state_machine",
        "tests.test_surrender",
        "tests.test_test_runner",
        "tests.test_tripometer",
        "tests.test_version",
    ],
    "betting": [
        "tests.test_betting",
        "tests.test_chip_visualizer_interactions",
        "tests.test_house_rules",
        "tests.test_tripometer",
    ],
    "dealer": [
        "tests.test_dealer_actor",
        "tests.test_dealer_actor_layers",
        "tests.test_dealer_stage_canvas",
        "tests.test_dealer_wardrobe_dialog",
        "tests.test_dialogue_voice_engine",
        "tests.test_hall_of_fame_and_achievements",
        "tests.test_puppet_multi_layer_actor",
        "tests.test_roster_puppet_conversion",
        "tests.test_universal_puppet_faceplates",
    ],
    "haunted": [
        "tests.test_haunted_mode",
        "tests.test_typewriter_and_audio_accents",
    ],
    "gui": [
        "tests.test_architectural_integration",
        "tests.test_card_counting_hud",
        "tests.test_counting_bootcamp",
        "tests.test_gui_state",
        "tests.test_house_rules_and_tripometer_gui",
        "tests.test_living_animations",
        "tests.test_multi_seat_gui",
        "tests.test_multi_seat_normal_play",
        "tests.test_pixel_ui",
        "tests.test_scale_and_display_modes",
        "tests.test_settings_dialog",
        "tests.test_shortcuts_overlay",
        "tests.test_table_felt",
        "tests.test_table_hud",
        "tests.test_ui_geometry_and_rendering",
        "tests.test_ui_layout",
        "tests.test_welcome_splash_dialog",
    ],
}

TIER_META: Dict[str, Dict[str, str]] = {
    "smoke": {
        "duration": "~15s",
        "desc": "Fast core domain, state machine, rules, persistence & micro-UI smoke checks",
    },
    "core": {
        "duration": "~25s",
        "desc": "Pure card rules, payouts, splits, double down, surrender, shoe & state machine",
    },
    "betting": {
        "duration": "~40s",
        "desc": "Chips Mode wagering, bankroll persistence, all-in, insurance & chip stacks",
    },
    "dealer": {
        "duration": "~75s",
        "desc": "Dealer stage, multi-layer puppet compositor, wardrobe modal & voice synthesis",
    },
    "haunted": {
        "duration": "~55s",
        "desc": "Supernatural Haunted Mode, Omen Card 13, relic blessings & altar animations",
    },
    "gui": {
        "duration": "~90s",
        "desc": "Table felt canvas, layout geometry, HiDPI scaling, modals & shortcut overlays",
    },
    "full": {
        "duration": "~5-6m",
        "desc": "Complete system & regression suite across all test modules (for releases)",
    },
}


def discover_all_modules() -> List[str]:
    """Discovers all test_*.py files in tests/ and returns sorted dotted module names."""
    modules = []
    for path in sorted(TESTS_DIR.glob("test_*.py")):
        if path.is_file():
            modules.append(f"tests.{path.stem}")
    return modules


def resolve_modules(tier: str) -> List[str]:
    """Resolves the list of test module names for the requested tier."""
    key = tier.lower().strip()
    if key == "full":
        return discover_all_modules()
    if key not in TIERS:
        valid = ", ".join(list(TIERS.keys()) + ["full"])
        raise ValueError(f"Unknown test tier '{tier}'. Valid tiers: {valid}")
    return list(TIERS[key])


def _filter_suite_by_pattern(suite: unittest.TestSuite, pattern: str) -> unittest.TestSuite:
    """Recursively filters a TestSuite, keeping only TestCases whose id matches `pattern`."""
    filtered = unittest.TestSuite()
    pat = pattern.lower()
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            sub = _filter_suite_by_pattern(item, pattern)
            if sub.countTestCases() > 0:
                filtered.addTest(sub)
        else:
            if pat in item.id().lower():
                filtered.addTest(item)
    return filtered


def build_suite(modules: List[str], pattern: Optional[str] = None) -> unittest.TestSuite:
    """Loads all tests from `modules` into a unittest.TestSuite, optionally filtered by `pattern`."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for mod in modules:
        loaded = loader.loadTestsFromName(mod)
        suite.addTest(loaded)
    if pattern:
        suite = _filter_suite_by_pattern(suite, pattern)
    return suite


def print_tier_catalogue() -> None:
    """Prints a formatted summary table of all available test tiers and their modules."""
    print("=" * 84)
    print(" BLACKJACK TEST RUNNER - AVAILABLE TIERS & SUBSYSTEM SUITES")
    print("=" * 84)
    print(f"{'Tier':<10} | {'Est. Time':<10} | {'Modules':<8} | {'Description'}")
    print("-" * 84)
    for tier_name, meta in TIER_META.items():
        mods = resolve_modules(tier_name)
        print(f"{tier_name:<10} | {meta['duration']:<10} | {len(mods):<8} | {meta['desc']}")
    print("=" * 84)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for the tiered test runner."""
    valid_tiers = list(TIERS.keys()) + ["full"]
    parser = argparse.ArgumentParser(
        description="Tiered Test Runner for Blackjack (smoke, subsystem, and full release suites)."
    )
    parser.add_argument(
        "tier",
        nargs="?",
        default="smoke",
        choices=valid_tiers,
        help=f"Test tier or subsystem to execute (default: smoke). Choices: {', '.join(valid_tiers)}",
    )
    parser.add_argument(
        "--smoke",
        action="store_const",
        const="smoke",
        dest="tier_flag",
        help="Shortcut flag to run the fast smoke suite.",
    )
    parser.add_argument(
        "--full",
        action="store_const",
        const="full",
        dest="tier_flag",
        help="Shortcut flag to run the full system test suite.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        dest="list_tiers",
        help="List available test tiers, module counts, and estimated durations.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose per-test output (verbosity=2).",
    )
    parser.add_argument(
        "-f",
        "--failfast",
        action="store_true",
        help="Stop immediately on the first failing or erroring test.",
    )
    parser.add_argument(
        "-k",
        "--pattern",
        type=str,
        default=None,
        help="Only run test methods/classes matching this substring pattern.",
    )

    args = parser.parse_args(argv)
    if getattr(args, "tier_flag", None):
        args.tier = args.tier_flag
    return args


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point for CLI test execution. Returns 0 on success, 1 on failure."""
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    args = parse_args(argv)
    if args.list_tiers:
        print_tier_catalogue()
        return 0

    modules = resolve_modules(args.tier)
    suite = build_suite(modules, pattern=args.pattern)
    total_cases = suite.countTestCases()
    meta = TIER_META.get(args.tier, {"duration": "N/A", "desc": ""})

    print("=" * 76)
    print(f" RUNNING TIER: [{args.tier.upper()}] ({len(modules)} modules, {total_cases} test cases | Est: {meta['duration']})")
    if args.pattern:
        print(f" FILTER PATTERN: '{args.pattern}'")
    print("=" * 76, flush=True)

    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, failfast=args.failfast)

    start_time = time.perf_counter()
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    ran = result.testsRun
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    passed = ran - failed - errors - skipped
    status_str = "PASSED" if result.wasSuccessful() else "FAILED"

    print("-" * 76)
    print(
        f" SUMMARY [{args.tier.upper()}]: {status_str} | "
        f"Ran: {ran} | Passed: {passed} | Failed: {failed} | Errors: {errors} | Skipped: {skipped} | "
        f"Time: {elapsed:.2f}s"
    )
    print("-" * 76, flush=True)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
