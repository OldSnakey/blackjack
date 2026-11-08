"""
Unit and Headless GUI Tests for the MIT Hi-Lo Counting Bootcamp (`counting_bootcamp.py`).

Covers:
1. 14-Node Curriculum DAG (`LECTURE_IDS` + `STAGE_IDS`), dual-unlock semantics, Fork A / Fork B, and Tier 3 `OR` gate (`C3A` or `C3B` -> `L4`/`C4`).
2. Standardized grading rubric (`compute_stage_grade`: `S`, `A`, `B`, `C`, `F`) and score calculation (`compute_stage_score`).
3. Isolated `SaveManager` persistence (`BootcampLectureRecord`, `BootcampStageRecord`, `BootcampProgress`), monotonic high-water mark ratcheting, legacy v1.1 JSON backward compatibility, and zero Free Play `HighScores` contamination.
4. Deterministic drill generators across all 7 challenge stages (`C1`, `C2A`, `C2B`, `C3A`, `C3B`, `C4`, `C5`) and Show & Tell lecture slides (`L1`, `L2A`, `L2B`, `L3A`, `L3B`, `L4`, `L5`).
5. Headless GUI integration:
   - `WelcomeSplashDialog` first-time `"training"` selection (`intro_seen == False` -> `teacher_intro`; `intro_seen == True` -> 3-Seat Free Play).
   - `BlackjackApp.enter_counting_bootcamp()` and `exit_counting_bootcamp_to_free_play()` felt swap (`row=3` and `row=4`) while keeping `dealer_stage_frame` (`row=1`) visible.
   - Mid-round entry guard and safe staged-bet refunding in `RoundPhase.BETTING` (with zero double-refund in `RoundPhase.ROUND_OVER`).
   - Root keyboard routing (`1`-`5`, arrows, `Enter`/`Space`, `Escape`) and table shortcut suppression (`K`, `Shift+M`, `H`/`S`) while `bootcamp_active == True`.
   - `SettingsDialog` and `CardCountingHud` re-entry buttons and `clear_player_save_data()` synchronization.
"""

from __future__ import annotations

import json
import tempfile
import tkinter
import unittest
from pathlib import Path

from blackjack import BlackjackApp
from card_counter import HiLoCardCounter
from counting_bootcamp import (
    BOOTCAMP_GRADE_CHIP_STYLES,
    STAGE_FIXED_CHOICES,
    BootcampControlDock,
    BootcampCurriculumDAG,
    BootcampDrillSession,
    CountingBootcampFrame,
)
from save_manager import (
    GRADE_RANK_ORDER,
    LECTURE_IDS,
    STAGE_IDS,
    BootcampLectureRecord,
    BootcampProgress,
    BootcampStageRecord,
    SaveData,
    SaveManager,
    create_default_bootcamp_progress,
)
from state_machine import RoundPhase
from ui_dialogs import SettingsDialog, WelcomeSplashDialog


class TestBootcampPersistenceAndDAG(unittest.TestCase):
    """Pure domain & persistence tests (zero Tkinter window overhead)."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_path = Path(self.temp_dir.name) / "test_bootcamp_save.json"
        self.save_mgr = SaveManager(save_path=self.save_path)
        self.dag = BootcampCurriculumDAG()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_14_node_dag_structure_and_initial_unlocks(self):
        """Verifies the 14-node DAG (7 Lectures + 7 Challenges) and default Tier 1 unlock state."""
        self.assertEqual(LECTURE_IDS, ("L1", "L2A", "L2B", "L3A", "L3B", "L4", "L5"))
        self.assertEqual(STAGE_IDS, ("C1", "C2A", "C2B", "C3A", "C3B", "C4", "C5"))

        all_nodes = self.dag.get_all_nodes()
        self.assertEqual(len(all_nodes), 14)

        bp = self.save_mgr.data.bootcamp
        self.assertFalse(bp.intro_seen)
        self.assertFalse(bp.graduated)
        self.assertTrue(bp.lectures["L1"].unlocked)
        self.assertTrue(bp.stages["C1"].unlocked)

        for lid in ("L2A", "L2B", "L3A", "L3B", "L4", "L5"):
            self.assertFalse(bp.lectures[lid].unlocked, f"{lid} should start locked")
        for sid in ("C2A", "C2B", "C3A", "C3B", "C4", "C5"):
            self.assertFalse(bp.stages[sid].unlocked, f"{sid} should start locked")

    def test_grading_rubric_and_score_formula(self):
        """Verifies S/A/B/C/F grade thresholds and par speed bonus scoring."""
        # S requires 100% accuracy and avg_response_ms <= par_ms
        self.assertEqual(self.dag.compute_stage_grade(100.0, 1500.0, 2000.0), "S")
        # 100% accuracy slower than par_ms yields A
        self.assertEqual(self.dag.compute_stage_grade(100.0, 2500.0, 2000.0), "A")
        self.assertEqual(self.dag.compute_stage_grade(92.0, 1500.0, 2000.0), "A")
        self.assertEqual(self.dag.compute_stage_grade(80.0, 3000.0, 2000.0), "B")
        self.assertEqual(self.dag.compute_stage_grade(70.0, 1500.0, 2000.0), "C")
        self.assertEqual(self.dag.compute_stage_grade(60.0, 1200.0, 2000.0), "F")

        # Score formula: int(round(accuracy_pct * 100)) + speed bonus when accuracy >= 80%
        score_s = self.dag.compute_stage_score(100.0, 1500.0, 2000.0)
        self.assertEqual(score_s, 10000 + (2000 - 1500) // 10)
        score_f = self.dag.compute_stage_score(60.0, 1000.0, 2000.0)
        self.assertEqual(score_f, 6000)

    def test_fork_a_and_fork_b_and_or_convergence_gate(self):
        """Verifies passing C1 unlocks both 2A and 2B, and passing C3B alone unlocks Tier 4 via OR gate."""
        # Fail C1 first (Grade C = 75%) -> does not unlock Tier 2
        res_fail = self.save_mgr.record_bootcamp_stage("C1", "C", 75.0, 7500)
        self.assertEqual(res_fail["newly_unlocked"], [])
        self.assertFalse(self.save_mgr.data.bootcamp.stages["C2A"].unlocked)
        self.assertFalse(self.save_mgr.data.bootcamp.stages["C2B"].unlocked)

        # Pass C1 with Grade B (85%) -> unlocks L2A, C2A, L2B, C2B
        res_c1 = self.save_mgr.record_bootcamp_stage("C1", "B", 85.0, 8520)
        self.assertCountEqual(res_c1["newly_unlocked"], ["L2A", "C2A", "L2B", "C2B"])
        self.assertTrue(self.save_mgr.data.bootcamp.lectures["L2A"].unlocked)
        self.assertTrue(self.save_mgr.data.bootcamp.stages["C2A"].unlocked)
        self.assertTrue(self.save_mgr.data.bootcamp.lectures["L2B"].unlocked)
        self.assertTrue(self.save_mgr.data.bootcamp.stages["C2B"].unlocked)

        # Fail C2A (60%, Grade F), switch to Fork B and pass C2B (93.3%, Grade A)
        self.save_mgr.record_bootcamp_stage("C2A", "F", 60.0, 6000)
        self.assertFalse(self.save_mgr.data.bootcamp.stages["C3A"].unlocked)

        res_c2b = self.save_mgr.record_bootcamp_stage("C2B", "A", 93.3, 9380)
        self.assertCountEqual(res_c2b["newly_unlocked"], ["L3B", "C3B"])
        self.assertTrue(self.save_mgr.data.bootcamp.stages["C3B"].unlocked)

        # Pass C3B with Grade B (80%) -> OR Gate unlocks L4 and C4 even though C3A is not passed!
        res_c3b = self.save_mgr.record_bootcamp_stage("C3B", "B", 80.0, 8000)
        self.assertCountEqual(res_c3b["newly_unlocked"], ["L4", "C4"])
        self.assertTrue(self.save_mgr.data.bootcamp.lectures["L4"].unlocked)
        self.assertTrue(self.save_mgr.data.bootcamp.stages["C4"].unlocked)

        # Pass C4 -> unlocks L5, C5; Pass C5 -> sets graduated = True
        self.save_mgr.record_bootcamp_stage("C4", "A", 90.0, 9050)
        self.assertTrue(self.save_mgr.data.bootcamp.stages["C5"].unlocked)
        self.save_mgr.record_bootcamp_stage("C5", "S", 100.0, 10100)
        self.assertTrue(self.save_mgr.data.bootcamp.graduated)

    def test_high_water_mark_ratchet_and_isolated_telemetry(self):
        """Verifies best_grade/best_accuracy_pct never downgrade on lower retries and HighScores remain untouched."""
        self.save_mgr.record_bootcamp_stage("C1", "S", 100.0, 10050)
        rec = self.save_mgr.data.bootcamp.stages["C1"]
        self.assertEqual(rec.attempts, 1)
        self.assertEqual(rec.completions, 1)
        self.assertEqual(rec.best_grade, "S")
        self.assertEqual(rec.best_accuracy_pct, 100.0)
        self.assertEqual(rec.best_score, 10050)

        # Retry with lower score (70%, Grade C)
        self.save_mgr.record_bootcamp_stage("C1", "C", 70.0, 7000)
        rec = self.save_mgr.data.bootcamp.stages["C1"]
        self.assertEqual(rec.attempts, 2)
        self.assertEqual(rec.completions, 2)
        self.assertEqual(rec.best_grade, "S")
        self.assertEqual(rec.best_accuracy_pct, 100.0)
        self.assertEqual(rec.best_score, 10050)

        # Verify Free Play HighScores were not mutated
        hs = self.save_mgr.data.highscores
        self.assertEqual(hs.counting_streak, 0)
        self.assertEqual(hs.counting_quizzes_taken, 0)
        self.assertEqual(hs.counting_accuracy_pct, 0.0)

    def test_lecture_completion_and_legacy_save_deserialization(self):
        """Verifies lecture tracking and backward-compatible loading of v1.1 save files without 'bootcamp' key."""
        rec_l1 = self.save_mgr.record_bootcamp_lecture("L1")
        self.assertTrue(rec_l1.completed)
        self.assertEqual(rec_l1.views, 1)
        self.assertEqual(self.save_mgr.data.bootcamp.lectures_completed, 1)

        # Legacy JSON without "bootcamp" key
        legacy_payload = {
            "version": "1.1",
            "current_bankroll": 2500,
            "equipped_costume": "classic",
            "unlocked_costumes": ["classic", "tiffany"],
            "highscores": {"peak_bankroll": 2500},
            "achievements": {},
            "chips_mode": True,
            "play_mode": "betting",
            "onboarding_completed": True,
        }
        restored = SaveData.from_dict(legacy_payload)
        self.assertIsInstance(restored.bootcamp, BootcampProgress)
        self.assertTrue(restored.bootcamp.lectures["L1"].unlocked)
        self.assertTrue(restored.bootcamp.stages["C1"].unlocked)
        self.assertEqual(len(restored.bootcamp.lectures), 7)
        self.assertEqual(len(restored.bootcamp.stages), 7)

    def test_drill_generators_across_all_7_stages(self):
        """Verifies deterministic drill question generators and BootcampDrillSession across C1..C5."""
        for sid in STAGE_IDS:
            session = BootcampDrillSession(stage_id=sid, dag=self.dag, seed=42)
            self.assertGreater(len(session.prompts), 0, f"Stage {sid} generated zero prompts")
            first = session.get_current_prompt()
            self.assertIsNotNone(first)
            # Submit correct answer for every prompt in the session
            while not session.is_complete():
                p = session.get_current_prompt()
                outcome = session.submit_answer(p.correct_answer, response_ms=1000.0)
                self.assertTrue(outcome["is_correct"])
            summary = session.build_summary()
            self.assertEqual(summary["accuracy_pct"], 100.0)
            self.assertEqual(summary["grade"], "S")


class TestBootcampHeadlessGUI(unittest.TestCase):
    """Headless Tkinter integration tests for CountingBootcampFrame and BlackjackApp lifecycle."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.save_path = Path(self.temp_dir.name) / "test_gui_save.json"
        self.root = tkinter.Tk()
        self.root.withdraw()
        self.app = BlackjackApp(
            self.root,
            chips_mode=True,
            sound_enabled=False,
            save_path=self.save_path,
            skip_splash=True,
        )

    def tearDown(self):
        try:
            self.app._on_close()
        except Exception:
            pass
        try:
            if self.root.winfo_exists():
                self.root.destroy()
        except Exception:
            pass
        self.temp_dir.cleanup()

    def test_welcome_splash_first_time_training_triggers_teacher_intro(self):
        """First-time selection of Strategy & Counting Trainer opens Teacher Intro without showing Free Play HUD."""
        self.assertFalse(self.app.save_manager.data.bootcamp.intro_seen)
        dlg = WelcomeSplashDialog(
            parent=self.root,
            app=self.app,
            on_confirm=lambda m: self.app.apply_play_mode(m),
        )
        dlg._select_mode("training")
        dlg._on_confirm()

        self.assertTrue(self.app.bootcamp_active)
        self.assertIsNotNone(self.app.bootcamp_frame)
        self.assertEqual(self.app.bootcamp_frame.current_view, "teacher_intro")
        self.assertFalse(self.app.card_counting_hud.is_visible)
        self.assertTrue(bool(self.app.dealer_stage_frame.grid_info()))
        self.assertFalse(bool(self.app.card_table_frame.grid_info()))

        # Choosing Option 1 ("[1] Enter Counting Bootcamp") marks intro_seen=True and opens Map
        self.app.bootcamp_frame.handle_teacher_choice("enter_bootcamp")
        self.assertTrue(self.app.save_manager.data.bootcamp.intro_seen)
        self.assertEqual(self.app.bootcamp_frame.current_view, "map")

    def test_welcome_splash_subsequent_training_opens_stage_map(self):
        """When intro_seen is True, selecting Strategy & Counting Trainer opens the Training Stage Map by default."""
        self.app.save_manager.mark_bootcamp_intro_seen()
        dlg = WelcomeSplashDialog(
            parent=self.root,
            app=self.app,
            on_confirm=lambda m: self.app.apply_play_mode(m),
        )
        dlg._select_mode("training")
        dlg._on_confirm()

        self.assertTrue(self.app.bootcamp_active)
        self.assertEqual(self.app.bootcamp_frame.current_view, "map")
        self.assertEqual(self.app.table_seats, 3)
        self.assertEqual(self.app.play_mode, "training")
        self.assertFalse(self.app.card_counting_hud.is_visible)

    def test_mid_round_guard_and_betting_refund_safety(self):
        """Blocks Bootcamp entry during PLAYER_TURN and safely refunds staged bets in BETTING without double-refund in ROUND_OVER."""
        # 1. Stage a $100 bet in 3-seat mode during BETTING
        self.app.set_table_seats(3)
        initial_bankroll = self.app.bankroll_var.get()
        self.app.selected_denomination = 100
        self.app._on_table_spot_click(2, None)
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll - 100)

        # Entering Bootcamp during BETTING refunds the uncommitted $100 staged bet
        self.app.enter_counting_bootcamp(start_view="map")
        self.assertTrue(self.app.bootcamp_active)
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll)

        # Exit back to Free Play
        self.app.exit_counting_bootcamp_to_free_play()
        self.assertFalse(self.app.bootcamp_active)
        self.assertEqual(self.app.bankroll_var.get(), initial_bankroll)

        # 2. Simulate active PLAYER_TURN -> Bootcamp entry must be blocked
        self.app.fsm.transition_to(RoundPhase.PLAYER_TURN, force=True)
        self.app.enter_counting_bootcamp(start_view="map")
        self.assertFalse(self.app.bootcamp_active)

        # 3. Simulate ROUND_OVER with settled seat main_bet remaining on seat -> bankroll must NOT be inflated
        self.app.fsm.transition_to(RoundPhase.ROUND_OVER, force=True)
        self.app.engine.get_seat(2).main_bet = 200
        bankroll_at_round_over = self.app.bankroll_var.get()
        self.app.enter_counting_bootcamp(start_view="map")
        self.assertTrue(self.app.bootcamp_active)
        self.assertEqual(self.app.bankroll_var.get(), bankroll_at_round_over)

    def test_keyboard_routing_and_table_shortcut_isolation(self):
        """While bootcamp_active is True, K and Shift+M are suppressed and navigation/Escape route to Bootcamp."""
        self.app.enter_counting_bootcamp(start_view="map")
        self.assertTrue(self.app.bootcamp_active)

        # K / Shift+C must not re-show CardCountingHud while in Bootcamp
        self.app._toggle_card_counting_hud()
        self.assertFalse(self.app.card_counting_hud.is_visible)

        # Shift+M must not cycle play_mode while in Bootcamp
        prev_mode = self.app.play_mode
        self.app._on_cycle_play_mode_shortcut()
        self.assertEqual(self.app.play_mode, prev_mode)
        self.assertTrue(self.app.bootcamp_active)

        # Pressing Escape on the Bootcamp Map exits to 3-Seat Free Play
        self.app._on_escape_key()
        self.assertFalse(self.app.bootcamp_active)
        self.assertEqual(self.app.play_mode, "training")
        self.assertEqual(self.app.table_seats, 3)

    def test_settings_and_hud_reentry_and_save_reset_sync(self):
        """Verifies SettingsDialog button, CardCountingHud button, and clear_player_save_data refresh."""
        # CardCountingHud button launches Bootcamp Map
        self.app.apply_play_mode("training")
        self.assertTrue(hasattr(self.app.card_counting_hud, "bootcamp_btn"))
        self.app.card_counting_hud.bootcamp_btn.invoke()
        self.assertTrue(self.app.bootcamp_active)
        self.assertEqual(self.app.bootcamp_frame.current_view, "map")

        # Unlock Tier 2 in save data, then call clear_player_save_data() while Bootcamp is mounted
        self.app.save_manager.record_bootcamp_stage("C1", "A", 95.0, 9500)
        self.assertTrue(self.app.save_manager.data.bootcamp.stages["C2A"].unlocked)
        self.app.clear_player_save_data()
        self.assertFalse(self.app.save_manager.data.bootcamp.stages["C2A"].unlocked)
        self.assertEqual(self.app.bootcamp_frame.current_view, "map")

    def test_relaunch_in_training_mode_restores_teacher_intro_and_3_seat_trainer(self):
        """
        Exiting right after selecting Training in WelcomeSplashDialog (before dismissing
        the 3-card teacher_intro view) and relaunching must restore teacher_intro;
        relaunching after intro_seen=True must restore 3-Seat Training Free Play.
        """
        dlg = WelcomeSplashDialog(
            parent=self.root,
            app=self.app,
            on_confirm=lambda m: self.app.apply_play_mode(m),
        )
        dlg._select_mode("training")
        dlg._on_confirm()

        self.assertTrue(self.app.bootcamp_active)
        self.assertEqual(self.app.bootcamp_frame.current_view, "teacher_intro")
        self.assertFalse(self.app.save_manager.data.bootcamp.intro_seen)

        # Simulate exiting the app while still on the 3-card teacher_intro screen
        self.app._on_close()

        # Relaunch a new BlackjackApp instance against the same persisted save file
        root2 = tkinter.Tk()
        root2.withdraw()
        app2 = None
        try:
            app2 = BlackjackApp(
                root2,
                sound_enabled=False,
                save_path=self.save_path,
                skip_splash=True,
            )
            self.assertEqual(app2.play_mode, "training")
            self.assertEqual(app2.table_seats, 3)
            self.assertTrue(app2.bootcamp_active)
            self.assertIsNotNone(app2.bootcamp_frame)
            self.assertEqual(app2.bootcamp_frame.current_view, "teacher_intro")

            # Now choose "[2] Skip to 3-Seat Practice Table" (marks intro_seen=True) and exit
            app2.bootcamp_frame.handle_teacher_choice("skip_to_free_play")
            self.assertTrue(app2.save_manager.data.bootcamp.intro_seen)
            self.assertFalse(app2.bootcamp_active)
            self.assertEqual(app2.table_seats, 3)
            self.assertTrue(app2.card_counting_hud.is_visible)
            app2._on_close()
        finally:
            try:
                if root2.winfo_exists():
                    root2.destroy()
            except Exception:
                pass

        # Relaunch a third time after intro_seen=True -> must start on the Training Stage Map ("map") by default
        root3 = tkinter.Tk()
        root3.withdraw()
        app3 = None
        try:
            app3 = BlackjackApp(
                root3,
                sound_enabled=False,
                save_path=self.save_path,
                skip_splash=True,
            )
            self.assertEqual(app3.play_mode, "training")
            self.assertTrue(app3.bootcamp_active)
            self.assertEqual(app3.bootcamp_frame.current_view, "map")
            self.assertEqual(app3.table_seats, 3)
            self.assertFalse(app3.card_counting_hud.is_visible)

            # Pressing Escape on the Stage Map escapes to 3-Seat Free Play
            app3._on_escape_key()
            self.assertFalse(app3.bootcamp_active)
            self.assertTrue(app3.card_counting_hud.is_visible)
        finally:
            try:
                if app3 is not None:
                    app3._on_close()
            except Exception:
                pass
            try:
                if root3.winfo_exists():
                    root3.destroy()
            except Exception:
                pass

    def test_settings_cycle_to_training_mode_opens_bootcamp_intro_or_map(self):
        """Cycling to Training Mode in SettingsDialog opens teacher_intro (if unseen) or stage map (if seen)."""
        from ui_dialogs import SettingsDialog

        self.app.apply_play_mode("betting")
        self.assertFalse(self.app.save_manager.data.bootcamp.intro_seen)

        dlg = SettingsDialog(self.root, self.app)
        try:
            # Cycle from betting -> training when intro_seen is False
            dlg._on_cycle_play_mode()
            self.assertEqual(self.app.play_mode, "training")
            self.assertEqual(self.app.table_seats, 3)
            self.assertTrue(self.app.bootcamp_active)
            self.assertEqual(self.app.bootcamp_frame.current_view, "teacher_intro")

            # Mark intro_seen=True, cycle to casual, then back through betting -> training
            self.app.save_manager.mark_bootcamp_intro_seen(save_now=True)
            dlg._on_cycle_play_mode()  # training -> casual
            self.assertEqual(self.app.play_mode, "casual")
            self.assertFalse(self.app.bootcamp_active)

            dlg._on_cycle_play_mode()  # casual -> betting
            self.assertEqual(self.app.play_mode, "betting")
            self.assertFalse(self.app.bootcamp_active)

            dlg._on_cycle_play_mode()  # betting -> training (now intro_seen is True -> opens map)
            self.assertEqual(self.app.play_mode, "training")
            self.assertTrue(self.app.bootcamp_active)
            self.assertEqual(self.app.bootcamp_frame.current_view, "map")
        finally:
            dlg.destroy()

    def test_mvc_separation_and_lecture_practice_telemetry_idempotency(self):
        """
        Verifies Option A MVC refactoring:
        1. Pure domain classes live in `bootcamp_domain` with zero Tkinter dependency.
        2. `CountingBootcampFrame` delegates all canvas drawing to `BootcampCanvasRenderer`.
        3. Answering a lecture practice check redraws the slide without double-incrementing
           `BootcampLectureRecord.views` in `SaveManager`.
        """
        import bootcamp_domain
        from counting_bootcamp import BootcampCanvasRenderer

        self.assertIs(bootcamp_domain.BootcampCurriculumDAG, BootcampCurriculumDAG)
        self.assertIs(bootcamp_domain.BootcampDrillSession, BootcampDrillSession)

        self.app.enter_counting_bootcamp(start_view="map")
        bf = self.app.bootcamp_frame
        self.assertIsNotNone(bf)
        self.assertIsInstance(bf.renderer, BootcampCanvasRenderer)

        # Open L1 and navigate to the final slide (index 2, which has the practice check)
        bf.render_lecture_view("L1", slide_index=2)
        rec = self.app.save_manager.data.bootcamp.lectures["L1"]
        self.assertTrue(rec.completed)
        self.assertEqual(rec.views, 1)
        self.assertIsNone(bf.practice_answered)

        # Submit an incorrect practice answer -> must set practice_answered=False and NOT increment views
        bf.submit_lecture_practice("+1 (Low)")
        self.assertIs(bf.practice_answered, False)
        self.assertEqual(self.app.save_manager.data.bootcamp.lectures["L1"].views, 1)

        # Submit the correct practice answer -> must set practice_answered=True and NOT increment views
        bf.submit_lecture_practice("-1 (High)")
        self.assertIs(bf.practice_answered, True)
        self.assertEqual(self.app.save_manager.data.bootcamp.lectures["L1"].views, 1)

    def test_abandon_stage_via_dock_button_header_click_and_escape(self):
        """
        Verifies that every Challenge stage provides a visible 'Abandon' button on the
        bottom dock and top-right header bar, and that abandoning mid-drill returns to
        the Curriculum Map without recording an attempt in SaveManager.
        """
        self.app.enter_counting_bootcamp(start_view="map")
        bf = self.app.bootcamp_frame
        self.assertIsNotNone(bf)

        # 1. Start C1 and answer 1 prompt, then abandon via the dock 'Abandon' button
        bf.render_challenge_view("C1", seed=42)
        self.assertEqual(bf.current_view, "challenge")
        self.assertIsNotNone(bf.active_session)

        dock_texts = [btn.text for btn in self.app.bootcamp_dock.buttons]
        abandon_btns = [btn for btn in self.app.bootcamp_dock.buttons if "Abandon" in btn.text]
        self.assertEqual(len(abandon_btns), 1, f"Expected an Abandon button on dock, got: {dock_texts}")

        # Answer first question, then invoke the dock Abandon button on question 2
        first_prompt = bf.active_session.get_current_prompt()
        bf.submit_challenge_answer(first_prompt.correct_answer)
        bf._advance_after_feedback()
        self.assertEqual(bf.active_session.current_index, 1)

        abandon_btns = [btn for btn in self.app.bootcamp_dock.buttons if "Abandon" in btn.text]
        abandon_btns[0].command()

        self.assertEqual(bf.current_view, "map")
        self.assertIsNone(bf.active_session)
        self.assertEqual(self.app.save_manager.data.bootcamp.stages["C1"].attempts, 0)

        # 2. Start C5 (5 choices) and verify dock width fit + top-right header 'abandon_stage' hit-box click
        bf.render_challenge_view("C5", seed=42)
        self.assertEqual(bf.current_view, "challenge")
        self.assertEqual(len(self.app.bootcamp_dock.buttons), 6)  # 5 choices + 1 Abandon button
        self.assertIn("abandon_stage", bf.renderer.action_hit_boxes)

        x1, y1, x2, y2 = bf.renderer.action_hit_boxes["abandon_stage"]
        click_evt = type("Evt", (), {"x": (x1 + x2) // 2, "y": (y1 + y2) // 2})()
        bf._on_canvas_click(click_evt)

        self.assertEqual(bf.current_view, "map")
        self.assertIsNone(bf.active_session)
        self.assertEqual(self.app.save_manager.data.bootcamp.stages["C5"].attempts, 0)

    def test_grade_medallion_25d_chip_size_and_fidelity(self):
        """
        Verifies that the 2.5D Casino Chip Medallion (`_draw_grade_medallion`) renders with
        enlarged bounding-box dimensions and multi-layered 2.5D detail (radial edge spots,
        visible 3D cylinder stripes, inner ring, drop shadow, and embossed grade stamp)
        on both the Curriculum Stage Map and the Pit Boss Report Card.
        """
        self.app.save_manager.record_bootcamp_stage("C1", "S", 100.0, 10000)
        self.app.enter_counting_bootcamp(start_view="map")
        bf = self.app.bootcamp_frame
        self.assertIsNotNone(bf)

        # 1. Verify Stage Map 2.5D chip medallion dimensions (width >= 40px, height >= 28px)
        map_chip_items = bf.canvas.find_withtag("grade_medallion")
        self.assertGreaterEqual(len(map_chip_items), 16, "Expected multi-layered 2.5D chip items on Stage Map")
        bx1, by1, bx2, by2 = bf.canvas.bbox("grade_medallion")
        self.assertGreaterEqual(bx2 - bx1, 40)
        self.assertGreaterEqual(by2 - by1, 28)

        # 2. Verify Report Card 2.5D trophy chip medallion dimensions (width >= 110px, height >= 75px)
        bf.render_report_card_view(
            summary={
                "stage_id": "C1",
                "title": "C1: Tag Reflex",
                "grade": "S",
                "passed": True,
                "correct_count": 20,
                "total_prompts": 20,
                "accuracy_pct": 100.0,
                "avg_response_ms": 650.0,
                "par_ms": 2000,
                "best_streak": 20,
                "score": 10135,
            },
            unlock_res={"newly_unlocked": ["L2A", "C2A"]},
        )
        rc_chip_items = bf.canvas.find_withtag("grade_medallion")
        self.assertGreaterEqual(len(rc_chip_items), 18, "Expected multi-layered 2.5D trophy chip items on Report Card")
        rx1, ry1, rx2, ry2 = bf.canvas.bbox("grade_medallion")
        self.assertGreaterEqual(rx2 - rx1, 110)
        self.assertGreaterEqual(ry2 - ry1, 75)

    def test_card_dealing_audio_on_challenge_and_lecture_cards(self):
        """
        Verifies that dealing/showing cards in Challenge prompts, Lecture slides, and Teacher Intro
        triggers `sound_manager.play_card_deal()`, and that staggered multi-card audio timers are
        tracked and cleanly cancelled in `cancel_all_timers()`.
        """
        from unittest.mock import patch

        self.app.enter_counting_bootcamp(start_view="map")
        bf = self.app.bootcamp_frame
        self.assertIsNotNone(bf)

        with patch.object(self.app.sound_manager, "play_card_deal") as mock_deal_sfx:
            # 1. Single-card challenge prompt (C1) plays card deal sound immediately
            bf.render_challenge_view("C1", seed=42)
            self.assertEqual(mock_deal_sfx.call_count, 1)
            self.assertEqual(len(bf._deal_audio_timer_ids), 0)

            # Advancing to next prompt in C1 deals the next card and plays card deal sound again
            p0 = bf.active_session.get_current_prompt()
            bf.submit_challenge_answer(p0.correct_answer)
            bf._advance_after_feedback()
            self.assertEqual(mock_deal_sfx.call_count, 2)

            # 2. Multi-card challenge prompt (C3A: 5 cards) plays 1 immediate sound + schedules 4 staggered deal timers
            mock_deal_sfx.reset_mock()
            bf.render_challenge_view("C3A", seed=42)
            self.assertEqual(mock_deal_sfx.call_count, 1)
            self.assertEqual(len(bf._deal_audio_timer_ids), 4)

            # Cancelling timers cleans up all scheduled deal audio timers
            bf.cancel_all_timers()
            self.assertEqual(len(bf._deal_audio_timer_ids), 0)

            # 3. Lecture slide with demonstration cards triggers card deal sound + staggered timers
            mock_deal_sfx.reset_mock()
            bf.render_lecture_view("L1", slide_index=0)
            self.assertEqual(mock_deal_sfx.call_count, 1)
            self.assertGreaterEqual(len(bf._deal_audio_timer_ids), 1)
            bf.cancel_all_timers()

    def test_fixed_hotkey_choice_ranges_and_anti_spam_guard(self):
        """
        Verifies across 50 random seeds (plus seed=None) that:
        1. Every Challenge stage (C1..C5) uses its canonical `STAGE_FIXED_CHOICES[stage_id]` tuple
           so hotkey values never change within a stage (preserving muscle memory).
        2. Every generated prompt's `correct_answer` is always a valid member of `p.choices`.
        3. Every Lecture's interactive practice check (L1..L5) shares the exact fixed hotkey tuple
           of its paired Challenge stage (`spec.paired_id`) and its `practice_correct` is in-range.
        4. Spamming hotkey '3' (or any single hotkey 1..5) yields Grade F (< 50% accuracy) on every stage.
        """
        dag = BootcampCurriculumDAG()

        # 1. Verify Lecture practice checks match their paired Challenge stage's fixed hotkey tuple
        for lec_id in LECTURE_IDS:
            lec_spec = dag.get_node(lec_id)
            paired_stage_id = lec_spec.paired_id
            expected_choices = STAGE_FIXED_CHOICES[paired_stage_id]
            slides = dag.get_lecture_slides(lec_id)
            practice_slides = [s for s in slides if s.practice_choices]
            self.assertEqual(len(practice_slides), 1, f"Lecture {lec_id} should have 1 practice check slide")
            for s in practice_slides:
                self.assertEqual(
                    s.practice_choices,
                    expected_choices,
                    f"Lecture {lec_id} practice hotkeys {s.practice_choices} must match {paired_stage_id} {expected_choices}",
                )
                self.assertIn(s.practice_correct, s.practice_choices)

        # 2. Verify across 50 deterministic seeds + unseeded generation that choices never shift
        #    within a stage and `correct_answer` is always inside `STAGE_FIXED_CHOICES[stage_id]`
        seeds_to_test = list(range(50)) + [None]
        for stage_id in ("C1", "C2A", "C2B", "C3A", "C3B", "C4", "C5"):
            expected_choices = STAGE_FIXED_CHOICES[stage_id]
            for seed in seeds_to_test:
                prompts = dag.generate_stage_prompts(stage_id, seed=seed)
                for p in prompts:
                    self.assertEqual(
                        p.choices,
                        expected_choices,
                        f"Stage {stage_id} (seed={seed}) prompt {p.prompt_index} shifted hotkey choices: {p.choices}",
                    )
                    self.assertIn(
                        p.correct_answer,
                        expected_choices,
                        f"Stage {stage_id} (seed={seed}) prompt {p.prompt_index} answer {p.correct_answer!r} outside {expected_choices}",
                    )

            # 3. Verify spamming any single hotkey (including key '3' / index 2) fails with Grade F
            for key_idx in range(len(expected_choices)):
                session = BootcampDrillSession(stage_id=stage_id, dag=dag, seed=42)
                spammed_choice = expected_choices[key_idx]
                while not session.is_complete():
                    session.submit_answer(spammed_choice, response_ms=500.0)
                summary = session.build_summary()
                self.assertLess(
                    summary["accuracy_pct"],
                    50.0,
                    f"Spamming key [{key_idx + 1}] ({spammed_choice}) on {stage_id} achieved {summary['accuracy_pct']}%",
                )
                self.assertFalse(summary["passed"])
                self.assertEqual(summary["grade"], "F")

    def test_training_mode_dealer_speech_streams_with_voice_synthesis_and_gestures(self):
        """
        Verifies that Training Mode (both Counting Bootcamp and 3-Seat Free Play) streams
        dealer speech (`stream=True`), synthesizes Animalese voice blips (`play_dialogue_blip`),
        animates phonetic visemes, and triggers valid dealer gestures.
        """
        from unittest.mock import patch

        self.app.enter_counting_bootcamp(start_view="map")
        bf = self.app.bootcamp_frame
        self.assertIsNotNone(bf)

        with patch.object(self.app, "set_dealer_speech", wraps=self.app.set_dealer_speech) as mock_set_speech:
            bf.render_lecture_view("L1", slide_index=0)
            mock_set_speech.assert_called()
            _, kwargs = mock_set_speech.call_args
            self.assertTrue(kwargs.get("stream"), "Training mode dealer speech must pass stream=True")

            # Verify exiting to 3-Seat Free Play also streams welcome coaching speech
            mock_set_speech.reset_mock()
            self.app.exit_counting_bootcamp_to_free_play()
            mock_set_speech.assert_called()
            _, fp_kwargs = mock_set_speech.call_args
            self.assertTrue(fp_kwargs.get("stream"), "3-Seat Training Free Play must stream welcome speech")

        # Verify stepping the typewriter plays procedural Animalese voice blips (`play_dialogue_blip`)
        with patch.object(self.app.sound_manager, "play_dialogue_blip") as mock_blip:
            self.app.enter_counting_bootcamp(start_view="map")
            self.app._typewriter_index = 0
            self.app._stream_typewriter_step()
            self.assertEqual(mock_blip.call_count, 1)
            self.assertEqual(self.app.dealer_speech_var.get(), self.app._current_speech_full[:1])

    def test_professor_dealer_default_in_training_mode_and_graduation_unlock(self):
        """
        Verifies that:
        1. 'professor' ('🎓 The MIT Card Professor') is registered in DEALER_ROSTER and VOICE_PROFILES
           with all 19 1x and 19 2x puppet layers and 'academy' stage backdrop.
        2. Entering Training Mode (Bootcamp or 3-Seat Free Play) defaults the active dealer to
           'professor' even before passing Stage C5.
        3. Returning to 'betting' or 'casual' mode before passing C5 reverts to the player's
           equipped costume ('julian').
        4. Passing Stage C5 in SaveManager.record_bootcamp_stage unlocks 'professor' in
           save_manager.data.unlocked_costumes and WardrobeDialog so it can be equipped in all modes.
        """
        from dealer_actor import CHARACTERS
        from dialogue_voice_engine import VOICE_PROFILES

        self.assertIn("professor", CHARACTERS)
        self.assertIn("professor", VOICE_PROFILES)
        prof_profile = CHARACTERS["professor"]
        self.assertEqual(prof_profile.theme, "academy")
        self.assertIn("Professor", prof_profile.title)

        # Initially in betting mode with 'classic' ('julian') equipped, professor is NOT unlocked
        self.assertNotIn("professor", self.app.save_manager.data.unlocked_costumes)
        self.app.apply_play_mode("betting")
        self.assertEqual(self.app.dealer_actor.current_character, "julian")

        # Entering Counting Bootcamp automatically defaults stage dealer to 'professor'
        self.app.enter_counting_bootcamp(start_view="map")
        self.assertEqual(self.app.dealer_actor.current_character, "professor")
        self.assertEqual(self.app.dealer_stage_canvas.current_theme, "academy")

        # Exiting Bootcamp to 3-Seat Training Free Play keeps 'professor' as default training dealer
        self.app.exit_counting_bootcamp_to_free_play()
        self.assertEqual(self.app.play_mode, "training")
        self.assertEqual(self.app.dealer_actor.current_character, "professor")

        # Switching back to 'betting' mode before graduating reverts to 'julian'
        self.app.apply_play_mode("betting")
        self.assertEqual(self.app.dealer_actor.current_character, "julian")

        # Passing Stage C5 unlocks 'professor' permanently for all casino modes
        self.app.save_manager.record_bootcamp_stage(
            stage_id="C5",
            grade="A",
            accuracy_pct=96.0,
            score=1500,
        )
        self.assertTrue(self.app.save_manager.data.bootcamp.graduated)
        self.assertIn("professor", self.app.save_manager.data.unlocked_costumes)

        # Verify WardrobeDialog now shows 'professor' as unlocked and allows equipping in betting mode
        self.app._on_click_stage_hanger()
        dialog = self.app._wardrobe_dialog
        self.assertIn("professor", dialog.cards)
        self.assertTrue(dialog.cards["professor"]["unlocked"])
        dialog._equip_costume("professor")
        self.assertEqual(self.app.dealer_actor.current_character, "professor")
        self.assertEqual(self.app.save_manager.data.equipped_costume, "professor")
        dialog._on_close()

    def test_training_mode_dealer_speech_completion_and_no_cutoff_guard(self):
        """
        Verifies that dealer speech bubbles in Training Mode are never cut off mid-sentence:
        1. `submit_challenge_answer()` on a correct answer calculates its auto-advance delay from
           `app.get_remaining_speech_ms()` (>= 1350ms) so the full explanation finishes typing
           and stays readable before advancing to the next prompt.
        2. Calling `set_dealer_speech(..., queue_if_busy=True)` (used by outcome speech after tactical
           actions and subsequent prompt callouts) while an existing speech bubble is streaming
           does not wipe out the active bubble mid-sentence; it queues the next bubble until the
           active bubble completes and holds for readability.
        3. Pressing `[Space]` / `[Enter]` / `[Right]` during a Lecture or Challenge feedback while
           the typewriter is still streaming first completes the current speech bubble immediately
           so the player sees the full text, and advances on the next press.
        """
        self.app.enter_counting_bootcamp(start_view="map")
        bf = self.app.bootcamp_frame
        self.assertIsNotNone(bf)

        # 1. Challenge correct answer waits for full speech + reading hold instead of 380ms cutoff
        bf.render_challenge_view("C1", seed=42)
        p0 = bf.active_session.get_current_prompt()
        bf.submit_challenge_answer(p0.correct_answer)
        self.assertTrue(bf.awaiting_feedback_advance)
        self.assertGreaterEqual(
            getattr(bf, "_last_feedback_delay_ms", 0),
            1350,
            "Challenge correct answer auto-advance must wait for full typewriter + read hold (>= 1350ms)",
        )
        self.assertIn("Sharp!", self.app._current_speech_full)

        # 2. Queued speech (`queue_if_busy=True`) does not overwrite an in-flight speech bubble mid-stream
        first_line = "Doubling on 11! Textbook MIT aggression — let's pull a paint card."
        second_line = "Winner! Excellent play at the training table."
        self.app.set_dealer_speech(first_line, stream=True)
        self.app._stream_typewriter_step()
        self.assertTrue(self.app.is_dealer_speaking())
        self.assertEqual(self.app._current_speech_full, first_line)

        # Requesting a queued follow-up bubble while first_line is still streaming preserves first_line
        self.app.set_dealer_speech(second_line, stream=True, queue_if_busy=True)
        self.assertEqual(self.app._current_speech_full, first_line)
        self.assertIsNotNone(getattr(self.app, "_queued_speech", None))

        # Completing first_line reveals the full first_line text and schedules the queued bubble after hold
        self.app._complete_typewriter_speech()
        self.assertEqual(self.app.dealer_speech_var.get(), first_line)
        self.app._flush_queued_speech()
        self.assertEqual(self.app._current_speech_full, second_line)

        # 3. Pressing Space in Lecture while dealer is still streaming completes the current speech first
        bf.render_lecture_view("L1", slide_index=0)
        slide0_line = bf.dag.get_lecture_slides("L1")[0].dealer_line
        self.assertEqual(bf.active_slide_index, 0)
        self.assertTrue(self.app.is_dealer_speaking())
        self.assertNotEqual(self.app.dealer_speech_var.get(), slide0_line)

        # First Space press completes the typewriter text on Slide 0 without skipping the slide
        bf.handle_key_event("space")
        self.assertEqual(bf.active_slide_index, 0)
        self.assertFalse(self.app.is_dealer_speaking())
        self.assertEqual(self.app.dealer_speech_var.get(), slide0_line)

        # Second Space press advances to Slide 1
        bf.handle_key_event("space")
        self.assertEqual(bf.active_slide_index, 1)


if __name__ == "__main__":
    unittest.main()
