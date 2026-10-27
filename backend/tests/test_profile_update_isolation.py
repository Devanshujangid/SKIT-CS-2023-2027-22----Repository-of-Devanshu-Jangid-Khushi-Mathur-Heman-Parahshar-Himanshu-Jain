"""
Comprehensive Isolation Tests for Student Profile & Settings Update Logic.

Verifies:
1. Deterministic evaluation of daily study hours updates.
2. Safe triggering of schedule re-evaluation flag when daily hours are lowered.
3. Accurate detection and calculation of overloaded days and overflow hours.
4. Non-triggering behavior when daily hours are increased or unchanged.
5. Safe cold-start onboarding handling when no prior profile or plan exists.
6. Plan state mutation preserving existing progress while injecting re-evaluation audit.
7. Mock database service execution testing profile and plan persistence.
8. FastAPI route endpoint isolation test with authentication override.
"""

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

# Ensure backend directory is in sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.profile_service import (
    OverloadedDay,
    ProfileReevaluationResult,
    calculate_day_total_hours,
    evaluate_profile_hours_update,
    apply_reevaluation_to_plan,
    update_student_profile_with_reevaluation,
)
from schemas.settings import StudyHoursUpdateSchema


class TestProfileUpdateIsolation(unittest.TestCase):
    """
    Pure isolation tests for profile hours reduction and schedule re-evaluation logic.
    Runs entirely in memory without requiring network or external database.
    """

    def setUp(self):
        # Realistic 7-day schedule with varying session loads
        self.sample_weekly_schedule = [
            {
                "day": "Monday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "id": "mon-os-1",
                        "subject": "Operating Systems",
                        "topic": "Process Scheduling",
                        "duration_hours": 2.5,
                        "priority": "high",
                    },
                    {
                        "id": "mon-db-1",
                        "subject": "Database Management",
                        "topic": "Transactions & ACID",
                        "duration_hours": 2.0,
                        "priority": "medium",
                    },
                ],
            },
            {
                "day": "Tuesday",
                "total_hours": 5.0,
                "sessions": [
                    {
                        "id": "tue-cn-1",
                        "subject": "Computer Networks",
                        "topic": "Routing Protocols",
                        "duration_hours": 3.0,
                        "priority": "high",
                    },
                    {
                        "id": "tue-dsa-1",
                        "subject": "Data Structures",
                        "topic": "Graph Algorithms",
                        "duration_hours": 2.0,
                        "priority": "high",
                    },
                ],
            },
            {
                "day": "Wednesday",
                "total_hours": 3.0,
                "sessions": [
                    {
                        "id": "wed-se-1",
                        "subject": "Software Engineering",
                        "topic": "Design Patterns",
                        "duration_hours": 3.0,
                        "priority": "medium",
                    },
                ],
            },
            {
                "day": "Thursday",
                "total_hours": 2.0,
                "sessions": [
                    {
                        "id": "thu-math-1",
                        "subject": "Discrete Mathematics",
                        "topic": "Combinatorics",
                        "duration_hours": 2.0,
                        "priority": "low",
                    },
                ],
            },
            {
                "day": "Friday",
                "total_hours": 4.0,
                "sessions": [
                    {
                        "id": "fri-os-2",
                        "subject": "Operating Systems",
                        "topic": "Deadlocks & Semaphores",
                        "duration_hours": 2.0,
                        "priority": "high",
                    },
                    {
                        "id": "fri-cn-2",
                        "subject": "Computer Networks",
                        "topic": "TCP Congestion Control",
                        "duration_hours": 2.0,
                        "priority": "medium",
                    },
                ],
            },
            {
                "day": "Saturday",
                "total_hours": 0.0,
                "sessions": [],  # Rest / flex day
            },
            {
                "day": "Sunday",
                "total_hours": 3.0,
                "sessions": [
                    {
                        "id": "sun-rev-1",
                        "subject": "Weekly Comprehensive Review",
                        "topic": "Mock Assessment",
                        "duration_hours": 3.0,
                        "priority": "high",
                    },
                ],
            },
        ]

        self.sample_plan_data = {
            "plan_overview": {
                "student_semester": 5,
                "daily_target_hours": 5.0,
                "weekly_total_hours": 21.5,
                "primary_focus": "Operating Systems",
            },
            "onboarding_data": {
                "study_hours_per_day": 5.0,
                "semester": 5,
            },
            "weekly_schedule": deepcopy(self.sample_weekly_schedule),
            "completed_task_ids": ["mon-os-1"],
            "task_executions": {
                "mon-os-1": {
                    "status": "completed",
                    "actual_minutes": 150,
                }
            },
        }

    # =========================================================================
    # 1. Core Deterministic Re-evaluation Tests
    # =========================================================================

    def test_lowering_hours_triggers_schedule_reevaluation_and_detects_overloaded_days(self):
        """
        Scenario: Student lowers daily study hours from 5.0h to 3.0h in Settings.
        Schedule contains days with 4.5h (Monday), 5.0h (Tuesday), and 4.0h (Friday).
        Expectation:
        - schedule_reevaluation_required is True
        - hours_reduced is True
        - reduction_hours == 2.0
        - overloaded_days identifies Monday (+1.5h), Tuesday (+2.0h), and Friday (+1.0h)
        - total_overflow_hours == 4.5
        - Wednesday (3.0h), Thursday (2.0h), Saturday (0.0h), Sunday (3.0h) NOT overloaded
        """
        result = evaluate_profile_hours_update(
            new_hours=3.0,
            previous_hours=5.0,
            weekly_schedule=self.sample_weekly_schedule,
        )

        self.assertTrue(result.schedule_reevaluation_required)
        self.assertTrue(result.hours_reduced)
        self.assertEqual(result.previous_hours, 5.0)
        self.assertEqual(result.new_hours, 3.0)
        self.assertEqual(result.reduction_hours, 2.0)
        self.assertIn("daily_study_hours_reduced", result.reasons)
        self.assertIn("daily_capacity_exceeded", result.reasons)

        # Check overloaded days
        self.assertEqual(len(result.overloaded_days), 3)
        day_names = [d["day"] for d in result.overloaded_days]
        self.assertEqual(day_names, ["Monday", "Tuesday", "Friday"])

        # Validate Monday overflow: 4.5h planned - 3.0h capacity = 1.5h overflow
        mon = next(d for d in result.overloaded_days if d["day"] == "Monday")
        self.assertEqual(mon["planned_hours"], 4.5)
        self.assertEqual(mon["capacity_limit"], 3.0)
        self.assertEqual(mon["overflow_hours"], 1.5)

        # Validate Tuesday overflow: 5.0h - 3.0h = 2.0h overflow
        tue = next(d for d in result.overloaded_days if d["day"] == "Tuesday")
        self.assertEqual(tue["planned_hours"], 5.0)
        self.assertEqual(tue["capacity_limit"], 3.0)
        self.assertEqual(tue["overflow_hours"], 2.0)

        # Validate Friday overflow: 4.0h - 3.0h = 1.0h overflow
        fri = next(d for d in result.overloaded_days if d["day"] == "Friday")
        self.assertEqual(fri["planned_hours"], 4.0)
        self.assertEqual(fri["capacity_limit"], 3.0)
        self.assertEqual(fri["overflow_hours"], 1.0)

        # Total overflow: 1.5 + 2.0 + 1.0 = 4.5h
        self.assertEqual(result.total_overflow_hours, 4.5)
        self.assertIn("Daily study hours reduced from 5.0h to 3.0h", result.message)
        self.assertIn("3 scheduled day(s) exceed new daily capacity by 4.5h", result.message)

    def test_lowering_hours_when_all_scheduled_days_within_new_capacity(self):
        """
        Scenario: Student lowers daily study hours from 6.0h to 5.0h.
        All days in the schedule are already <= 5.0h.
        Expectation:
        - hours_reduced is True
        - schedule_reevaluation_required is True (alerts student that capacity budget was cut)
        - overloaded_days is empty
        - total_overflow_hours == 0.0
        - message notes pacing re-evaluation recommended
        """
        result = evaluate_profile_hours_update(
            new_hours=5.0,
            previous_hours=6.0,
            weekly_schedule=self.sample_weekly_schedule,
        )

        self.assertTrue(result.schedule_reevaluation_required)
        self.assertTrue(result.hours_reduced)
        self.assertEqual(result.reduction_hours, 1.0)
        self.assertEqual(result.overloaded_days, [])
        self.assertEqual(result.total_overflow_hours, 0.0)
        self.assertEqual(result.reasons, ["daily_study_hours_reduced"])
        self.assertIn("Current schedule days are within capacity", result.message)

    def test_increasing_study_hours_does_not_trigger_reevaluation(self):
        """
        Scenario: Student increases daily hours from 3.0h to 5.0h (capacity expansion).
        Schedule days are within 5.0h.
        Expectation:
        - hours_reduced is False
        - schedule_reevaluation_required is False
        - reduction_hours == 0.0
        - overloaded_days is empty
        - reasons is empty
        """
        # Light schedule where all days are <= 3.0h
        light_schedule = [
            {"day": "Monday", "total_hours": 3.0, "sessions": []},
            {"day": "Tuesday", "total_hours": 2.5, "sessions": []},
        ]
        result = evaluate_profile_hours_update(
            new_hours=5.0,
            previous_hours=3.0,
            weekly_schedule=light_schedule,
        )

        self.assertFalse(result.schedule_reevaluation_required)
        self.assertFalse(result.hours_reduced)
        self.assertEqual(result.reduction_hours, 0.0)
        self.assertEqual(result.overloaded_days, [])
        self.assertEqual(result.total_overflow_hours, 0.0)
        self.assertEqual(result.reasons, [])
        self.assertIn("increased from 3.0h to 5.0h", result.message)

    def test_unchanged_hours_is_idempotent_no_reevaluation(self):
        """
        Scenario: Student re-saves profile with the exact same hours (4.5h -> 4.5h).
        Expectation:
        - hours_reduced is False
        - schedule_reevaluation_required is False
        """
        result = evaluate_profile_hours_update(
            new_hours=4.5,
            previous_hours=4.5,
            weekly_schedule=[{"day": "Monday", "total_hours": 4.0}],
        )

        self.assertFalse(result.schedule_reevaluation_required)
        self.assertFalse(result.hours_reduced)
        self.assertEqual(result.reduction_hours, 0.0)
        self.assertEqual(result.overloaded_days, [])

    def test_cold_start_onboarding_no_prior_hours(self):
        """
        Scenario: First-time student onboarding (previous_hours is None).
        Expectation:
        - No crash / graceful handling
        - hours_reduced is False
        - schedule_reevaluation_required is False when no schedule exists
        """
        result = evaluate_profile_hours_update(
            new_hours=4.0,
            previous_hours=None,
            weekly_schedule=None,
        )

        self.assertFalse(result.schedule_reevaluation_required)
        self.assertFalse(result.hours_reduced)
        self.assertIsNone(result.previous_hours)
        self.assertEqual(result.new_hours, 4.0)
        self.assertEqual(result.overloaded_days, [])
        self.assertIn("Daily study hours set to 4.0h", result.message)

    def test_cold_start_with_template_exceeding_capacity(self):
        """
        Scenario: Student onboards or imports template where Monday has 5.0h,
        but student specifies new_hours = 3.0h.
        Expectation:
        - hours_reduced is False (no previous profile)
        - But schedule_reevaluation_required is True due to capacity overflow
        - reason contains 'daily_capacity_exceeded'
        """
        result = evaluate_profile_hours_update(
            new_hours=3.0,
            previous_hours=None,
            weekly_schedule=[{"day": "Monday", "total_hours": 5.0}],
        )

        self.assertTrue(result.schedule_reevaluation_required)
        self.assertFalse(result.hours_reduced)
        self.assertEqual(result.reasons, ["daily_capacity_exceeded"])
        self.assertEqual(len(result.overloaded_days), 1)
        self.assertEqual(result.overloaded_days[0]["overflow_hours"], 2.0)

    def test_invalid_hours_raise_value_error(self):
        """
        Scenario: Non-positive or non-numeric hours submitted.
        Expectation: Raises ValueError cleanly without corrupting state.
        """
        with self.assertRaises(ValueError):
            evaluate_profile_hours_update(new_hours=0.0)

        with self.assertRaises(ValueError):
            evaluate_profile_hours_update(new_hours=-1.5)

        with self.assertRaises(ValueError):
            evaluate_profile_hours_update(new_hours="not_a_number")

    # =========================================================================
    # 2. Session Summation & Malformed Schedule Fallback Tests
    # =========================================================================

    def test_calculate_day_total_hours_falls_back_to_sessions_when_total_hours_missing(self):
        """
        Verify that if total_hours is missing or None in day dict,
        session duration_hours are accurately aggregated.
        """
        day_dict = {
            "day": "Monday",
            "sessions": [
                {"duration_hours": 1.5},
                {"duration_hours": 2.0},
                {"duration_hours": 0.5},
            ]
        }
        computed = calculate_day_total_hours(day_dict)
        self.assertEqual(computed, 4.0)

    def test_calculate_day_total_hours_handles_malformed_sessions_safely(self):
        """
        Verify that non-numeric or missing durations in sessions do not crash calculation.
        """
        day_dict = {
            "day": "Tuesday",
            "sessions": [
                {"duration_hours": 1.5},
                {"duration_hours": "corrupted"},
                {"duration_hours": None},
                {"duration_hours": -2.0},
                "not_a_dict_session",
            ]
        }
        computed = calculate_day_total_hours(day_dict)
        self.assertEqual(computed, 1.5)

    # =========================================================================
    # 3. Plan Mutation & Invariant Preservation Tests
    # =========================================================================

    def test_apply_reevaluation_to_plan_sets_flags_and_preserves_executions(self):
        """
        Verify that apply_reevaluation_to_plan:
        1. Sets requires_rebalance = True
        2. Sets schedule_reevaluation_required = True
        3. Sets rebalance_trigger = 'study_hours_reduced'
        4. Updates target_daily_hours, plan_overview, and onboarding_data
        5. Injects reevaluation_audit dict
        6. Keeps completed tasks and session objects intact
        """
        reeval = evaluate_profile_hours_update(
            new_hours=3.0,
            previous_hours=5.0,
            weekly_schedule=self.sample_weekly_schedule,
        )

        updated_plan = apply_reevaluation_to_plan(self.sample_plan_data, reeval)

        # Re-evaluation flags
        self.assertTrue(updated_plan["requires_rebalance"])
        self.assertTrue(updated_plan["schedule_reevaluation_required"])
        self.assertEqual(updated_plan["rebalance_trigger"], "study_hours_reduced")
        self.assertIn("reevaluation_audit", updated_plan)
        self.assertEqual(len(updated_plan["reevaluation_audit"]["overloaded_days"]), 3)

        # Capacity updates
        self.assertEqual(updated_plan["target_daily_hours"], 3.0)
        self.assertEqual(updated_plan["plan_overview"]["daily_target_hours"], 3.0)
        self.assertEqual(updated_plan["onboarding_data"]["study_hours_per_day"], 3.0)

        # Progress preservation
        self.assertEqual(updated_plan["completed_task_ids"], ["mon-os-1"])
        self.assertEqual(updated_plan["task_executions"]["mon-os-1"]["status"], "completed")
        self.assertEqual(len(updated_plan["weekly_schedule"]), 7)

    def test_apply_reevaluation_when_not_required_updates_capacity_without_rebalance_flag(self):
        """
        Verify that if reevaluation is NOT required (e.g. hours increased from 3.0h to 5.0h),
        capacity limits are updated without setting requires_rebalance = True.
        """
        reeval = evaluate_profile_hours_update(
            new_hours=5.0,
            previous_hours=3.0,
            weekly_schedule=[],
        )
        base_plan = {
            "plan_overview": {"daily_target_hours": 3.0},
            "onboarding_data": {"study_hours_per_day": 3.0},
            "weekly_schedule": [],
        }

        updated = apply_reevaluation_to_plan(base_plan, reeval)
        self.assertNotIn("requires_rebalance", updated)
        self.assertEqual(updated["plan_overview"]["daily_target_hours"], 5.0)
        self.assertEqual(updated["onboarding_data"]["study_hours_per_day"], 5.0)

    # =========================================================================
    # 4. Service Flow with Mock Database (Isolation)
    # =========================================================================

    def test_update_student_profile_service_with_mock_db_hours_reduced(self):
        """
        Test update_student_profile_with_reevaluation using a simulated Supabase DB.
        Verifies:
        - Previous profile query retrieves previous 5.0h
        - Active study plan query retrieves schedule with 4.5h Monday
        - Reducing to 3.0h triggers schedule_reevaluation
        - student_profiles table is upserted with 3.0h
        - study_plans table is updated with requires_rebalance = True
        """
        mock_db = MagicMock()

        # Mock student_profiles select response (previous hours = 5.0)
        mock_profile_query = MagicMock()
        mock_profile_query.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {
                "user_id": "test-uuid-1",
                "semester": 5,
                "study_hours_per_day": 5.0,
                "goals": ["Master Operating Systems"],
                "subjects": ["Operating Systems"],
            }
        ]

        # Mock study_plans select response (active plan with 4.5h Monday)
        mock_plan_query = MagicMock()
        mock_plan_query.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {
                "id": "plan-uuid-99",
                "plan_data": deepcopy(self.sample_plan_data),
            }
        ]

        # Mock table dispatch
        def table_side_effect(table_name):
            if table_name == "student_profiles":
                table_mock = MagicMock()
                table_mock.select = mock_profile_query.select
                table_mock.upsert.return_value.execute.return_value.data = [
                    {
                        "user_id": "test-uuid-1",
                        "study_hours_per_day": 3.0,
                        "semester": 5,
                    }
                ]
                return table_mock
            elif table_name == "study_plans":
                table_mock = MagicMock()
                table_mock.select = mock_plan_query.select
                table_mock.update.return_value.eq.return_value.execute.return_value.data = [{"id": "plan-uuid-99"}]
                return table_mock
            return MagicMock()

        mock_db.table.side_effect = table_side_effect

        # Call service
        result = update_student_profile_with_reevaluation(
            db=mock_db,
            user_id="test-uuid-1",
            new_study_hours=3.0,
            semester=5,
        )

        self.assertTrue(result["success"])
        self.assertTrue(result["active_plan_flagged"])
        reeval = result["schedule_reevaluation"]
        self.assertTrue(reeval["schedule_reevaluation_required"])
        self.assertTrue(reeval["hours_reduced"])
        self.assertEqual(reeval["previous_hours"], 5.0)
        self.assertEqual(reeval["new_hours"], 3.0)
        self.assertEqual(len(reeval["overloaded_days"]), 3)

    def test_update_student_profile_service_with_no_active_plan(self):
        """
        Test service when user has a profile but no active study plan.
        Verifies:
        - Profile is updated safely
        - schedule_reevaluation is computed (flags hours reduced)
        - active_plan_flagged is False
        - No unhandled exceptions
        """
        mock_db = MagicMock()

        # Previous profile has 4.5h
        mock_profile_table = MagicMock()
        mock_profile_table.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"user_id": "u-2", "study_hours_per_day": 4.5}
        ]
        mock_profile_table.upsert.return_value.execute.return_value.data = [
            {"user_id": "u-2", "study_hours_per_day": 3.5}
        ]

        # No active study plan
        mock_plan_table = MagicMock()
        mock_plan_table.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = []

        def table_side_effect(table_name):
            if table_name == "student_profiles":
                return mock_profile_table
            elif table_name == "study_plans":
                return mock_plan_table
            return MagicMock()

        mock_db.table.side_effect = table_side_effect

        result = update_student_profile_with_reevaluation(
            db=mock_db,
            user_id="u-2",
            new_study_hours=3.5,
        )

        self.assertTrue(result["success"])
        self.assertFalse(result["active_plan_flagged"])
        self.assertTrue(result["schedule_reevaluation"]["hours_reduced"])
        self.assertTrue(result["schedule_reevaluation"]["schedule_reevaluation_required"])

    # =========================================================================
    # 5. Pydantic Settings Schema Integration
    # =========================================================================

    def test_settings_schema_validates_and_feeds_profile_service(self):
        """
        Verify that StudyHoursUpdateSchema sanitizes and validates daily hours,
        and cleanly feeds into evaluate_profile_hours_update.
        """
        # Valid update
        schema = StudyHoursUpdateSchema(
            study_hours_per_day=3.5,
            max_consecutive_hours=2.0,
        )
        self.assertEqual(schema.study_hours_per_day, 3.5)

        reeval = evaluate_profile_hours_update(
            new_hours=schema.study_hours_per_day,
            previous_hours=5.0,
            weekly_schedule=self.sample_weekly_schedule,
        )
        self.assertTrue(reeval.schedule_reevaluation_required)
        self.assertEqual(reeval.reduction_hours, 1.5)

    # =========================================================================
    # 6. FastAPI Route Endpoint Isolation Test (TestClient)
    # =========================================================================

    def test_fastapi_profile_endpoint_triggers_reevaluation(self):
        """
        Full isolated API route test via FastAPI TestClient:
        POST /api/v1/profile
        - Overrides Clerk authentication dependency
        - Simulates reducing daily hours from 5.0h to 3.0h
        - Asserts HTTP 201 and schedule_reevaluation returned in JSON
        """
        from fastapi.testclient import TestClient
        from main import app
        from auth import verify_clerk_token

        # Mock Clerk auth
        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "mock_clerk_student_123",
            "email": "student@skit.ac.in",
        }

        # Mock DB operations
        mock_db = MagicMock()

        # Users table mock
        mock_users = MagicMock()
        mock_users.upsert.return_value.execute.return_value.data = [{"id": "internal-uuid-777"}]

        # Profiles table mock (prior hours 5.0h)
        mock_profiles = MagicMock()
        mock_profiles.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"user_id": "internal-uuid-777", "study_hours_per_day": 5.0, "semester": 5}
        ]
        mock_profiles.upsert.return_value.execute.return_value.data = [
            {"user_id": "internal-uuid-777", "study_hours_per_day": 3.0, "semester": 5}
        ]

        # Plans table mock (has active plan with 4.5h Monday)
        mock_plans = MagicMock()
        mock_plans.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "plan-uuid-777", "plan_data": deepcopy(self.sample_plan_data)}
        ]
        mock_plans.update.return_value.eq.return_value.execute.return_value.data = [{"id": "plan-uuid-777"}]

        def table_side_effect(table_name):
            if table_name == "users":
                return mock_users
            elif table_name == "student_profiles":
                return mock_profiles
            elif table_name == "study_plans":
                return mock_plans
            return MagicMock()

        mock_db.table.side_effect = table_side_effect

        with patch("main.get_db", return_value=mock_db):
            client = TestClient(app)
            response = client.post(
                "/api/v1/profile",
                json={
                    "email": "student@skit.ac.in",
                    "semester": 5,
                    "study_hours_per_day": 3.0,
                    "goals": ["Crack GATE 2027 with AIR < 100"],
                    "subjects": ["Operating Systems", "Computer Networks"],
                },
            )

        # Clear dependency overrides
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("schedule_reevaluation", data)

        reeval = data["schedule_reevaluation"]
        self.assertTrue(reeval["schedule_reevaluation_required"])
        self.assertTrue(reeval["hours_reduced"])
        self.assertEqual(reeval["previous_hours"], 5.0)
        self.assertEqual(reeval["new_hours"], 3.0)
        self.assertEqual(len(reeval["overloaded_days"]), 3)
        self.assertEqual(reeval["total_overflow_hours"], 4.5)

    def test_adaptive_status_endpoint_reflects_schedule_reevaluation_flag(self):
        """
        Verify that GET /api/v1/plans/adaptive-status immediately returns
        needs_rebalance = True and schedule_reevaluation_required = True
        when active plan has been flagged due to daily study hours reduction.
        """
        from fastapi.testclient import TestClient
        from main import app
        from auth import verify_clerk_token

        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "mock_clerk_student_999",
            "email": "student@skit.ac.in",
        }

        # Mock DB
        mock_db = MagicMock()
        mock_users = MagicMock()
        mock_users.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "internal-uuid-999"}
        ]

        flagged_plan_data = deepcopy(self.sample_plan_data)
        flagged_plan_data["requires_rebalance"] = True
        flagged_plan_data["schedule_reevaluation_required"] = True
        flagged_plan_data["rebalance_trigger"] = "study_hours_reduced"
        flagged_plan_data["reevaluation_audit"] = {
            "hours_reduced": True,
            "previous_hours": 5.0,
            "new_hours": 3.0,
            "message": "Daily study hours reduced from 5.0h to 3.0h. 3 scheduled day(s) exceed capacity.",
        }

        mock_plans = MagicMock()
        mock_plans.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "plan-uuid-999", "plan_data": flagged_plan_data}
        ]

        def table_side_effect(table_name):
            if table_name == "users":
                return mock_users
            elif table_name == "study_plans":
                return mock_plans
            return MagicMock()

        mock_db.table.side_effect = table_side_effect

        with patch("routes.plans.get_db", return_value=mock_db):
            client = TestClient(app)
            response = client.get("/api/v1/plans/adaptive-status")

        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["needs_rebalance"])
        self.assertTrue(data["schedule_reevaluation_required"])
        self.assertIn("Daily study hours reduced from 5.0h to 3.0h", data["summary"])

    def test_adaptive_status_endpoint_clean_when_no_rebalance_or_reduction(self):
        """
        Verify that GET /api/v1/plans/adaptive-status returns needs_rebalance = False
        when all tasks are on track and no hours reduction has occurred.
        """
        from fastapi.testclient import TestClient
        from main import app
        from auth import verify_clerk_token

        app.dependency_overrides[verify_clerk_token] = lambda: {
            "sub": "mock_clerk_student_100",
            "email": "ontrack@skit.ac.in",
        }

        mock_db = MagicMock()
        mock_users = MagicMock()
        mock_users.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "internal-uuid-100"}
        ]

        clean_plan_data = {
            "weekly_schedule": [],
            "completed_task_ids": [],
            "task_executions": {},
        }
        mock_plans = MagicMock()
        mock_plans.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "plan-clean-1", "plan_data": clean_plan_data}
        ]

        def table_side_effect(table_name):
            if table_name == "users":
                return mock_users
            elif table_name == "study_plans":
                return mock_plans
            return MagicMock()

        mock_db.table.side_effect = table_side_effect

        with patch("routes.plans.get_db", return_value=mock_db):
            client = TestClient(app)
            response = client.get("/api/v1/plans/adaptive-status")

        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertFalse(data["needs_rebalance"])
        self.assertFalse(data["schedule_reevaluation_required"])
        self.assertEqual(data["summary"], "All scheduled study sessions on track.")


if __name__ == "__main__":
    unittest.main()

