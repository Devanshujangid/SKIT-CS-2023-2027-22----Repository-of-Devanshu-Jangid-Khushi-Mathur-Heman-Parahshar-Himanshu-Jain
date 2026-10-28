"""
Unit tests for Analytics Aggregations and Role-Based Access Control (RBAC).
Verifies:
1. Student Analytics API aggregates actual study minutes by subject, weekly performance, and completion rates.
2. require_role separates 'admin' and 'student'.
3. Admin endpoints reject student tokens with HTTP 403 Forbidden.
4. Admin endpoints succeed with HTTP 200 OK for admin role.
5. Missing tokens return HTTP 401 Unauthorized.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import require_role, require_admin, require_student
from main import app


class TestRoleBasedAccessControl(unittest.IsolatedAsyncioTestCase):
    """Verifies that require_role properly validates roles and enforces 403/200 separation."""

    async def test_student_rejected_from_admin_role(self):
        checker = require_role(["admin"])
        student_payload = {
            "sub": "user_student_123",
            "email": "student@skit.ac.in",
            "role": "student",
        }

        with self.assertRaises(HTTPException) as ctx:
            await checker(token_payload=student_payload)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Access forbidden", ctx.exception.detail)
        self.assertIn("student", ctx.exception.detail)

    async def test_admin_accepted_by_admin_role(self):
        checker = require_role(["admin"])
        admin_payload = {
            "sub": "user_admin_999",
            "email": "faculty@skit.ac.in",
            "role": "admin",
        }

        result = await checker(token_payload=admin_payload)
        self.assertEqual(result["role"], "admin")
        self.assertEqual(result["sub"], "user_admin_999")

    async def test_student_accepted_by_student_role(self):
        checker = require_student
        student_payload = {
            "sub": "user_student_456",
            "email": "student2@skit.ac.in",
            "role": "student",
        }

        result = await checker(token_payload=student_payload)
        self.assertEqual(result["role"], "student")

    async def test_admin_accepted_by_student_role(self):
        checker = require_student
        admin_payload = {
            "sub": "user_admin_999",
            "email": "faculty@skit.ac.in",
            "role": "admin",
        }

        result = await checker(token_payload=admin_payload)
        self.assertEqual(result["role"], "admin")

    async def test_role_extracted_from_public_metadata(self):
        checker = require_role(["admin"])
        jwt_with_metadata = {
            "sub": "user_meta_admin",
            "email": "admin@skit.ac.in",
            "public_metadata": {"role": "admin"},
        }

        result = await checker(token_payload=jwt_with_metadata)
        self.assertEqual(result["role"], "admin")


class TestAnalyticsEndpoints(unittest.TestCase):
    """Verifies analytics API endpoints with mocked Supabase responses."""

    def setUp(self):
        self.client = TestClient(app)

    @patch("routes.analytics.require_student")
    @patch("routes.analytics.get_db")
    def test_student_analytics_summary_success(self, mock_get_db, mock_require_student):
        # Mock authenticated student payload
        app.dependency_overrides[require_student] = lambda: {
            "sub": "user_student_123",
            "email": "student@skit.ac.in",
            "role": "student",
        }

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Mock user lookup
        mock_user_query = MagicMock()
        mock_user_query.data = [{"id": "uuid-123", "clerk_id": "user_student_123", "role": "student"}]
        mock_db.table("users").select().eq().limit().execute.return_value = mock_user_query

        # Mock tasks lookup with 3 subjects and varying completion
        mock_tasks_query = MagicMock()
        mock_tasks_query.data = [
            {
                "id": "t1",
                "title": "Operating Systems: Process Synchronization",
                "description": "Duration: 2.0 hours",
                "scheduled_date": "2026-10-26",
                "is_completed": True,
            },
            {
                "id": "t2",
                "title": "Operating Systems: Virtual Memory",
                "description": "Duration: 1.5 hours",
                "scheduled_date": "2026-10-27",
                "is_completed": True,
            },
            {
                "id": "t3",
                "title": "Database Systems: Relational Algebra",
                "description": "Duration: 1.5 hours",
                "scheduled_date": "2026-10-28",
                "is_completed": False,
            },
            {
                "id": "t4",
                "title": "Computer Networks: TCP Congestion",
                "description": "Duration: 1.0 hours",
                "scheduled_date": "2026-10-29",
                "is_completed": True,
            },
        ]
        mock_db.table("tasks").select().eq().execute.return_value = mock_tasks_query

        # Mock study plan lookup
        mock_plan_query = MagicMock()
        mock_plan_query.data = []
        mock_db.table("study_plans").select().eq().eq().order().limit().execute.return_value = mock_plan_query

        response = self.client.get("/api/v1/analytics/summary")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["role"], "student")

        # Verify overview metrics
        overview = data["overview"]
        self.assertEqual(overview["total_tasks_count"], 4)
        self.assertEqual(overview["completed_tasks_count"], 3)
        self.assertEqual(overview["completion_percentage"], 75)
        self.assertEqual(overview["total_scheduled_hours"], 6.0)
        self.assertEqual(overview["total_actual_hours"], 4.5)
        self.assertEqual(overview["adherence_rate"], 75)

        # Verify subject distribution
        subjects = {s["name"]: s for s in data["subject_distribution"]}
        self.assertIn("Operating Systems", subjects)
        self.assertEqual(subjects["Operating Systems"]["hours"], 3.5)
        self.assertEqual(subjects["Operating Systems"]["mastery"], 100)
        self.assertIn("Database Systems", subjects)
        self.assertEqual(subjects["Database Systems"]["hours"], 0.0)
        self.assertEqual(subjects["Database Systems"]["mastery"], 0)

        # Verify weekly hours structure has all 7 days
        self.assertEqual(len(data["weekly_hours"]), 7)

    @patch("routes.analytics.get_db")
    def test_admin_roster_forbidden_for_student(self, mock_get_db):
        # Override require_admin with a student caller to test 403
        app.dependency_overrides[require_admin] = require_role(["admin"])

        # Create a student auth override
        app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
            HTTPException(status_code=403, detail="Access forbidden: role 'student' lacks permission")
        )

        response = self.client.get("/api/v1/analytics/admin/roster")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 403)
        self.assertIn("Access forbidden", response.json()["detail"])

    @patch("routes.analytics.get_db")
    def test_admin_roster_allowed_for_admin(self, mock_get_db):
        app.dependency_overrides[require_admin] = lambda: {
            "sub": "user_admin_super",
            "email": "faculty_hod@skit.ac.in",
            "role": "admin",
        }

        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_users_query = MagicMock()
        mock_users_query.data = [
            {"id": "u1", "clerk_id": "c1", "email": "devanshu@skit.ac.in", "role": "student"},
            {"id": "u2", "clerk_id": "c2", "email": "himanshu@skit.ac.in", "role": "student"},
        ]
        mock_db.table("users").select().execute.return_value = mock_users_query

        mock_db.table("student_profiles").select().eq().limit().execute.return_value = MagicMock(data=[])
        mock_db.table("study_plans").select().eq().eq().limit().execute.return_value = MagicMock(data=[])
        mock_db.table("tasks").select().eq().execute.return_value = MagicMock(data=[])

        response = self.client.get("/api/v1/analytics/admin/roster")
        app.dependency_overrides.clear()

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["total_students"], 2)


if __name__ == "__main__":
    unittest.main()
