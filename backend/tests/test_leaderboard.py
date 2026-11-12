"""
Unit Tests for Student Leaderboard Aggregation and Goal Status.

Validates:
1. Leaderboard ranking algorithm (dense rank by actual study hours, completion rate, completed tasks).
2. Computed goal status transitions ('not_started', 'ahead', 'on_track', 'behind').
3. Pydantic schemas (LeaderboardEntry, LeaderboardResponse, UpdateGoalStatusRequest).
4. GET /api/v1/analytics/leaderboard endpoint (pagination, semester filter, current_user_rank, RPC & fallback).
5. PATCH /api/v1/analytics/goal-status endpoint.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError
from routes.analytics import (
    get_student_leaderboard_endpoint,
    update_student_goal_status_endpoint,
)
from schemas.leaderboard import (
    LeaderboardEntry,
    LeaderboardResponse,
    UpdateGoalStatusRequest,
    VALID_GOAL_STATUSES,
)


def run_async(coroutine):
    """Executes a coroutine synchronously."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


class TestLeaderboardAggregation(unittest.TestCase):
    def setUp(self):
        self.student_1_id = "11111111-1111-1111-1111-111111111111"
        self.student_2_id = "22222222-2222-2222-2222-222222222222"
        self.student_3_id = "33333333-3333-3333-3333-333333333333"

        self.student_payload = {
            "sub": "user_student_111",
            "email": "alice@skit.ac.in",
            "role": "student",
        }

    # =========================================================================
    # 1. Pydantic Schema Validation Tests
    # =========================================================================

    def test_valid_goal_status_schema(self):
        for status in VALID_GOAL_STATUSES:
            req = UpdateGoalStatusRequest(goal_status=status)
            self.assertEqual(req.goal_status, status)

    def test_invalid_goal_status_raises_error(self):
        invalid_statuses = ["slacking", "unknown", "", "active"]
        for bad_status in invalid_statuses:
            with self.assertRaises(ValidationError):
                UpdateGoalStatusRequest(goal_status=bad_status)

    def test_leaderboard_entry_schema(self):
        entry = LeaderboardEntry(
            rank=1,
            user_id=self.student_1_id,
            display_name="ali***@skit.ac.in",
            semester=5,
            target_hours_per_day=3.0,
            goal_status="ahead",
            calculated_goal_status="ahead",
            primary_goals=["Maintain 8.5 CGPA", "GATE 2027"],
            total_tasks=10,
            completed_tasks=9,
            planned_study_hours=15.0,
            actual_study_hours=14.5,
            completion_rate=90.0,
        )
        self.assertEqual(entry.rank, 1)
        self.assertEqual(entry.completion_rate, 90.0)
        self.assertEqual(entry.goal_status, "ahead")

    # =========================================================================
    # 2. Leaderboard Endpoint Aggregation & Fallback Tests
    # =========================================================================

    @patch("routes.analytics.get_db")
    def test_leaderboard_fallback_aggregation_ranking(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # 1. Clerk user lookup returns Student 1
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_1_id}]
        )

        # 2. RPC call fails to trigger table fallback
        mock_db.rpc.side_effect = Exception("RPC not deployed")

        # 3. Mock student roster
        users_mock = [
            {"id": self.student_1_id, "email": "alice@skit.ac.in", "role": "student"},
            {"id": self.student_2_id, "email": "bob@skit.ac.in", "role": "student"},
            {"id": self.student_3_id, "email": "charlie@skit.ac.in", "role": "student"},
        ]

        def table_side_effect(table_name):
            t_mock = MagicMock()
            if table_name == "users":
                # Handle eq("role", "student")
                t_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=users_mock)
                # Handle clerk_id lookup
                t_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"id": self.student_1_id}]
                )
            elif table_name == "student_profiles":
                def prof_eq(col, val):
                    prof_data = {
                        self.student_1_id: [{"semester": 5, "study_hours_per_day": 3.0, "goals": ["GATE"], "goal_status": "ahead"}],
                        self.student_2_id: [{"semester": 5, "study_hours_per_day": 2.5, "goals": ["Placement"], "goal_status": "on_track"}],
                        self.student_3_id: [{"semester": 5, "study_hours_per_day": 1.5, "goals": ["Basics"], "goal_status": "behind"}],
                    }.get(val, [])
                    return MagicMock(limit=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=prof_data)))))
                t_mock.select.return_value.eq.side_effect = prof_eq
            elif table_name == "tasks":
                def task_eq(col, val):
                    # Student 1: 10 tasks, 9 completed (14.5 hours actual)
                    # Student 2: 8 tasks, 4 completed (6.0 hours actual)
                    # Student 3: 0 tasks (0.0 hours)
                    if val == self.student_1_id:
                        data = [
                            {"id": f"t1_{i}", "description": "Duration: 1.5 hours", "is_completed": True}
                            for i in range(9)
                        ] + [{"id": "t1_10", "description": "Duration: 1.5 hours", "is_completed": False}]
                    elif val == self.student_2_id:
                        data = [
                            {"id": f"t2_{i}", "description": "Duration: 1.5 hours", "is_completed": True}
                            for i in range(4)
                        ] + [{"id": f"t2_{i}", "description": "Duration: 1.5 hours", "is_completed": False} for i in range(4)]
                    else:
                        data = []
                    return MagicMock(execute=MagicMock(return_value=MagicMock(data=data)))
                t_mock.select.return_value.eq.side_effect = task_eq
            return t_mock

        mock_db.table.side_effect = table_side_effect

        res = run_async(get_student_leaderboard_endpoint(limit=10, offset=0, user_payload=self.student_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["total_students"], 3)
        self.assertEqual(len(res["leaderboard"]), 3)

        # Rank 1: Alice (13.5 actual hours, 90.0% completion)
        self.assertEqual(res["leaderboard"][0]["user_id"], self.student_1_id)
        self.assertEqual(res["leaderboard"][0]["rank"], 1)
        self.assertEqual(res["leaderboard"][0]["calculated_goal_status"], "ahead")

        # Rank 2: Bob (6.0 actual hours, 50.0% completion)
        self.assertEqual(res["leaderboard"][1]["user_id"], self.student_2_id)
        self.assertEqual(res["leaderboard"][1]["rank"], 2)
        self.assertEqual(res["leaderboard"][1]["calculated_goal_status"], "on_track")

        # Rank 3: Charlie (0 tasks, not_started)
        self.assertEqual(res["leaderboard"][2]["user_id"], self.student_3_id)
        self.assertEqual(res["leaderboard"][2]["rank"], 3)
        self.assertEqual(res["leaderboard"][2]["calculated_goal_status"], "not_started")

        # Verify current user rank
        self.assertIsNotNone(res["current_user_rank"])
        self.assertEqual(res["current_user_rank"]["user_id"], self.student_1_id)
        self.assertEqual(res["current_user_rank"]["rank"], 1)

    @patch("routes.analytics.get_db")
    def test_leaderboard_dense_rank_ties_and_behind_status(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.rpc.side_effect = Exception("Fallback")

        users_mock = [
            {"id": self.student_1_id, "email": "alice@skit.ac.in", "role": "student"},
            {"id": self.student_2_id, "email": "bob@skit.ac.in", "role": "student"},
            {"id": self.student_3_id, "email": "charlie@skit.ac.in", "role": "student"},
        ]

        def table_side_effect(table_name):
            t_mock = MagicMock()
            if table_name == "users":
                t_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=users_mock)
                t_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"id": self.student_1_id}]
                )
            elif table_name == "student_profiles":
                def prof_eq(col, val):
                    return MagicMock(limit=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[
                        {"semester": 5, "study_hours_per_day": 3.0, "goals": ["GATE"], "goal_status": "on_track"}
                    ])))))
                t_mock.select.return_value.eq.side_effect = prof_eq
            elif table_name == "tasks":
                def task_eq(col, val):
                    # Student 1 & 2: Identical study hours (5.0) and completion rate (100%) -> TIE for Rank 1
                    # Student 3: 10 tasks, 2 completed -> 20% completion rate (< 50%) -> 'behind'
                    if val in (self.student_1_id, self.student_2_id):
                        data = [{"id": f"t_{i}", "description": "Duration: 2.5 hours", "is_completed": True} for i in range(2)]
                    else:
                        data = [{"id": f"t3_{i}", "description": "Duration: 1.0 hours", "is_completed": i < 2} for i in range(10)]
                    return MagicMock(execute=MagicMock(return_value=MagicMock(data=data)))
                t_mock.select.return_value.eq.side_effect = task_eq
            return t_mock

        mock_db.table.side_effect = table_side_effect

        res = run_async(get_student_leaderboard_endpoint(limit=10, offset=0, user_payload=self.student_payload))
        self.assertTrue(res["success"])
        entries = res["leaderboard"]
        self.assertEqual(len(entries), 3)

        # Both tied for Rank 1
        self.assertEqual(entries[0]["rank"], 1)
        self.assertEqual(entries[1]["rank"], 1)
        self.assertEqual(entries[0]["actual_study_hours"], 5.0)
        self.assertEqual(entries[1]["actual_study_hours"], 5.0)

        # Student 3 gets Rank 2 (Dense Rank) and 'behind' calculated status
        self.assertEqual(entries[2]["rank"], 2)
        self.assertEqual(entries[2]["calculated_goal_status"], "behind")
        self.assertEqual(entries[2]["completion_rate"], 20.0)

    @patch("routes.analytics.get_db")
    def test_leaderboard_semester_filtering(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db
        mock_db.rpc.side_effect = Exception("Fallback")

        users_mock = [
            {"id": self.student_1_id, "email": "s1@skit.ac.in", "role": "student"},
            {"id": self.student_2_id, "email": "s2@skit.ac.in", "role": "student"},
        ]

        def table_side_effect(table_name):
            t_mock = MagicMock()
            if table_name == "users":
                t_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=users_mock)
                t_mock.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"id": self.student_1_id}]
                )
            elif table_name == "student_profiles":
                def prof_eq(col, val):
                    # Student 1 is Semester 5; Student 2 is Semester 7
                    sem = 5 if val == self.student_1_id else 7
                    return MagicMock(limit=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[
                        {"semester": sem, "study_hours_per_day": 2.0, "goals": [], "goal_status": "on_track"}
                    ])))))
                t_mock.select.return_value.eq.side_effect = prof_eq
            elif table_name == "tasks":
                t_mock.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
            return t_mock

        mock_db.table.side_effect = table_side_effect

        # Filter by semester 5 -> only student 1 returned
        res = run_async(get_student_leaderboard_endpoint(limit=10, offset=0, semester=5, user_payload=self.student_payload))
        self.assertTrue(res["success"])
        self.assertEqual(len(res["leaderboard"]), 1)
        self.assertEqual(res["leaderboard"][0]["user_id"], self.student_1_id)
        self.assertEqual(res["semester_filter"], 5)

    @patch("routes.analytics.get_db")
    def test_leaderboard_rpc_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Clerk lookup
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_1_id}]
        )

        mock_rpc_data = [
            {
                "rank": 1,
                "user_id": self.student_1_id,
                "display_name": "ali***@skit.ac.in",
                "semester": 5,
                "target_hours_per_day": 3.0,
                "goal_status": "ahead",
                "calculated_goal_status": "ahead",
                "primary_goals": ["GATE 2027"],
                "total_tasks": 20,
                "completed_tasks": 19,
                "planned_study_hours": 30.0,
                "actual_study_hours": 28.5,
                "completion_rate": 95.0,
            }
        ]
        mock_db.rpc.return_value.execute.return_value = MagicMock(data=mock_rpc_data)

        res = run_async(get_student_leaderboard_endpoint(limit=50, offset=0, user_payload=self.student_payload))
        self.assertTrue(res["success"])
        self.assertEqual(len(res["leaderboard"]), 1)
        self.assertEqual(res["leaderboard"][0]["rank"], 1)
        self.assertEqual(res["current_user_rank"]["user_id"], self.student_1_id)

    # =========================================================================
    # 3. PATCH /api/v1/analytics/goal-status Endpoint Tests
    # =========================================================================

    @patch("routes.analytics.get_db")
    def test_update_goal_status_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Lookup user UUID
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_1_id}]
        )
        # Update call
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"user_id": self.student_1_id, "goal_status": "ahead"}]
        )

        payload = UpdateGoalStatusRequest(goal_status="ahead")
        res = run_async(update_student_goal_status_endpoint(payload=payload, user_payload=self.student_payload))

        self.assertTrue(res["success"])
        self.assertEqual(res["goal_status"], "ahead")
        self.assertEqual(res["user_id"], self.student_1_id)


if __name__ == "__main__":
    unittest.main()
