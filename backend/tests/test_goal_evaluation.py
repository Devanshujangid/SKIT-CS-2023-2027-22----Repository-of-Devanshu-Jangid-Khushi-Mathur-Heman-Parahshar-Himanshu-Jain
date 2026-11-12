"""
Unit tests for Deterministic Goal Evaluation Service.

Verifies:
1. Exact match (studied_hours == target_study_hours) triggers `status='achieved'` and `success_triggered=True`.
2. Surplus study hours trigger success status and calculate `surplus_hours`.
3. Partial progress bands ('on_track' >=75%, 'in_progress' 25-74.9%, 'behind' <25%) do not trigger success.
4. Floating-point precision handling (e.g., 0.1 + 0.2 matching 0.3, or 1.333 + 1.667 matching 3.0).
5. End-to-end aggregation from active study plan telemetry (`evaluate_goal_from_plan`),
   including `completed`, `partially_completed`, `missed`, and subject-filtered goals.
6. End-to-end aggregation from PostgreSQL `tasks` rows (`evaluate_goal_from_tasks`).
7. Strict input validation for negative hours, zero/negative targets, NaN/Inf, booleans, and invalid task counts.
"""

from pathlib import Path
import sys
import unittest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.goal_evaluation import (
    GoalEvaluationResult,
    evaluate_goal_from_plan,
    evaluate_goal_from_tasks,
    evaluate_goal_progress,
)


class TestGoalEvaluationProgress(unittest.TestCase):
    """Tests for direct studied_hours vs target_study_hours evaluation."""

    def test_exact_match_triggers_success_status(self):
        """When studied_hours matches target_study_hours, status is 'achieved' and success_triggered is True."""
        result = evaluate_goal_progress(
            studied_hours=10.0,
            target_study_hours=10.0,
            completed_tasks=5,
            total_tasks=5,
        )
        self.assertIsInstance(result, GoalEvaluationResult)
        self.assertEqual(result.status, "achieved")
        self.assertTrue(result.success_triggered)
        self.assertEqual(result.studied_hours, 10.0)
        self.assertEqual(result.target_study_hours, 10.0)
        self.assertEqual(result.remaining_hours, 0.0)
        self.assertEqual(result.surplus_hours, 0.0)
        self.assertEqual(result.progress_percentage, 100.0)
        self.assertIn("Goal achieved", result.message)

    def test_exceeding_target_triggers_success_with_surplus(self):
        """When studied_hours exceeds target_study_hours, success triggers and surplus_hours is computed."""
        result = evaluate_goal_progress(studied_hours=12.5, target_study_hours=10.0)
        self.assertEqual(result.status, "achieved")
        self.assertTrue(result.success_triggered)
        self.assertEqual(result.remaining_hours, 0.0)
        self.assertEqual(result.surplus_hours, 2.5)
        self.assertEqual(result.progress_percentage, 125.0)

    def test_floating_point_summation_matches_target(self):
        """IEEE-754 float drift (e.g., 0.1 + 0.2 or 1.334 + 1.666) still matches target cleanly."""
        result = evaluate_goal_progress(studied_hours=0.1 + 0.2, target_study_hours=0.3)
        self.assertEqual(result.status, "achieved")
        self.assertTrue(result.success_triggered)
        self.assertEqual(result.remaining_hours, 0.0)

    def test_progress_status_bands_and_boundaries(self):
        """Verify non-achieved statuses ('on_track', 'in_progress', 'behind') never trigger success."""
        # 75.0% -> on_track
        r_on_track = evaluate_goal_progress(studied_hours=7.5, target_study_hours=10.0)
        self.assertEqual(r_on_track.status, "on_track")
        self.assertFalse(r_on_track.success_triggered)
        self.assertEqual(r_on_track.remaining_hours, 2.5)
        self.assertEqual(r_on_track.progress_percentage, 75.0)

        # 74.9% -> in_progress
        r_below_75 = evaluate_goal_progress(studied_hours=7.49, target_study_hours=10.0)
        self.assertEqual(r_below_75.status, "in_progress")
        self.assertFalse(r_below_75.success_triggered)

        # 25.0% -> in_progress
        r_at_25 = evaluate_goal_progress(studied_hours=2.5, target_study_hours=10.0)
        self.assertEqual(r_at_25.status, "in_progress")
        self.assertFalse(r_at_25.success_triggered)

        # 24.9% -> behind
        r_behind = evaluate_goal_progress(studied_hours=2.49, target_study_hours=10.0)
        self.assertEqual(r_behind.status, "behind")
        self.assertFalse(r_behind.success_triggered)
        self.assertEqual(r_behind.remaining_hours, 7.51)

        # 0.0 hours -> behind
        r_zero = evaluate_goal_progress(studied_hours=0.0, target_study_hours=10.0)
        self.assertEqual(r_zero.status, "behind")
        self.assertFalse(r_zero.success_triggered)
        self.assertEqual(r_zero.progress_percentage, 0.0)

    def test_rejects_invalid_numeric_inputs(self):
        """Negative studied hours, non-positive targets, NaN/Inf, booleans, and bad counts raise ValueError."""
        with self.assertRaises(ValueError):
            evaluate_goal_progress(studied_hours=-1.0, target_study_hours=5.0)

        with self.assertRaises(ValueError):
            evaluate_goal_progress(studied_hours=2.0, target_study_hours=0.0)

        with self.assertRaises(ValueError):
            evaluate_goal_progress(studied_hours=2.0, target_study_hours=-4.0)

        with self.assertRaises(ValueError):
            evaluate_goal_progress(studied_hours=float("nan"), target_study_hours=5.0)

        with self.assertRaises(ValueError):
            evaluate_goal_progress(studied_hours=2.0, target_study_hours=float("inf"))

        with self.assertRaises(ValueError):
            evaluate_goal_progress(studied_hours=True, target_study_hours=5.0)  # type: ignore

        with self.assertRaises(ValueError):
            evaluate_goal_progress(
                studied_hours=2.0,
                target_study_hours=5.0,
                completed_tasks=4,
                total_tasks=3,
            )

    def test_to_dict_serialization(self):
        """Verify GoalEvaluationResult.to_dict() produces a clean JSON-serializable dictionary."""
        res = evaluate_goal_progress(
            studied_hours=4.0,
            target_study_hours=4.0,
            completed_tasks=2,
            total_tasks=2,
            subject_filter="Operating Systems",
        )
        d = res.to_dict()
        self.assertEqual(d["status"], "achieved")
        self.assertTrue(d["success_triggered"])
        self.assertEqual(d["subject_filter"], "Operating Systems")
        self.assertIn("Operating Systems", d["message"])


class TestGoalEvaluationFromPlanAndTasks(unittest.TestCase):
    """Tests for aggregating studied hours from study_plans and tasks tables."""

    def setUp(self):
        self.sample_plan = {
            "plan_overview": {
                "weekly_total_hours": 7.5,
            },
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "sessions": [
                        {
                            "id": "s1",
                            "subject": "Operating Systems",
                            "topic": "Process Synchronization",
                            "duration_hours": 2.0,
                        },
                        {
                            "id": "s2",
                            "subject": "Computer Networks",
                            "topic": "TCP Flow Control",
                            "duration_hours": 1.5,
                        },
                    ],
                },
                {
                    "day": "Tuesday",
                    "sessions": [
                        {
                            "id": "s3",
                            "subject": "Operating Systems",
                            "topic": "Deadlocks",
                            "duration_hours": 2.0,
                        },
                        {
                            "id": "s4",
                            "subject": "Database Management Systems",
                            "topic": "B-Trees",
                            "duration_hours": 2.0,
                        },
                    ],
                },
            ],
            "completed_task_ids": ["s1", "s2"],
            "task_executions": {
                "s1": {"status": "completed", "actual_minutes": 120},
                "s2": {"status": "completed"},  # Uses planned 1.5h = 90m
                "s3": {"status": "partially_completed", "actual_minutes": 60},  # 1.0h
                "s4": {"status": "missed", "actual_minutes": 0},  # 0.0h
            },
        }

    def test_evaluate_goal_from_plan_partial_progress(self):
        """Plan with 4.5h studied out of 7.5h target yields 60.0% 'in_progress'."""
        result = evaluate_goal_from_plan(self.sample_plan)
        self.assertEqual(result.target_study_hours, 7.5)
        self.assertEqual(result.studied_hours, 4.5)
        self.assertEqual(result.progress_percentage, 60.0)
        self.assertEqual(result.status, "in_progress")
        self.assertFalse(result.success_triggered)
        self.assertEqual(result.completed_tasks, 2)
        self.assertEqual(result.total_tasks, 4)

    def test_evaluate_goal_from_plan_all_completed_achieves_target(self):
        """Completing all sessions totaling target_study_hours triggers success status."""
        plan_done = {
            "plan_overview": {"weekly_total_hours": 5.5},
            "weekly_schedule": self.sample_plan["weekly_schedule"],
            "completed_task_ids": ["s1", "s2", "s3", "s4"],
            "task_executions": {
                "s1": {"status": "completed", "actual_minutes": 120},
                "s2": {"status": "completed", "actual_minutes": 90},
                "s3": {"status": "completed", "actual_minutes": 120},
                "s4": {"status": "completed", "actual_minutes": 120},
            },
        }
        result = evaluate_goal_from_plan(plan_done, target_study_hours=7.5)
        self.assertEqual(result.status, "achieved")
        self.assertTrue(result.success_triggered)
        self.assertEqual(result.studied_hours, 7.5)
        self.assertEqual(result.completed_tasks, 4)

    def test_evaluate_goal_from_plan_with_subject_filter(self):
        """Subject filter isolates Operating Systems (3.0h studied vs 3.0h target -> achieved)."""
        result = evaluate_goal_from_plan(
            self.sample_plan,
            target_study_hours=3.0,
            subject_filter="Operating Systems",
        )
        self.assertEqual(result.status, "achieved")
        self.assertTrue(result.success_triggered)
        self.assertEqual(result.studied_hours, 3.0)
        self.assertEqual(result.completed_tasks, 1)
        self.assertEqual(result.total_tasks, 2)
        self.assertEqual(result.subject_filter, "Operating Systems")

    def test_evaluate_goal_from_tasks_table_rows(self):
        """Aggregates studied hours from tasks rows using Duration metadata and actual_minutes."""
        task_rows = [
            {
                "id": "t1",
                "title": "Operating Systems: Process Synchronization",
                "description": "Activity: core_concept_study | Duration: 2.0 hours | Priority: high",
                "is_completed": True,
            },
            {
                "id": "t2",
                "title": "Operating Systems: Virtual Memory",
                "description": "Activity: practice_problems | Duration: 1.5 hours | Priority: medium",
                "is_completed": True,
                "actual_minutes": 90,
            },
            {
                "id": "t3",
                "title": "Computer Networks: TCP Congestion Control",
                "description": "Duration: 1.0 hours",
                "is_completed": False,
                "actual_minutes": 30,  # 0.5h logged before finishing
            },
        ]

        # Overall target 4.0h -> 2.0 + 1.5 + 0.5 = 4.0h -> achieved!
        overall = evaluate_goal_from_tasks(task_rows, target_study_hours=4.0)
        self.assertEqual(overall.status, "achieved")
        self.assertTrue(overall.success_triggered)
        self.assertEqual(overall.studied_hours, 4.0)
        self.assertEqual(overall.completed_tasks, 2)
        self.assertEqual(overall.total_tasks, 3)

        # Subject filter: Operating Systems -> 3.5h out of 4.0h -> on_track (87.5%)
        os_only = evaluate_goal_from_tasks(
            task_rows,
            target_study_hours=4.0,
            subject_filter="Operating Systems",
        )
        self.assertEqual(os_only.status, "on_track")
        self.assertFalse(os_only.success_triggered)
        self.assertEqual(os_only.studied_hours, 3.5)
        self.assertEqual(os_only.progress_percentage, 87.5)


if __name__ == "__main__":
    unittest.main()

