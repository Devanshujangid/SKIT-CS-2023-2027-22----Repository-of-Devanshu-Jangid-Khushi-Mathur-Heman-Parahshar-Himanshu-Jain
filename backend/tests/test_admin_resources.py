"""
Unit Tests for:
1. Top-Level GET /api/v1/leaderboard Endpoint.
2. Admin Resource Management Endpoints (POST, PATCH, DELETE, GET /api/v1/admin/resources).
3. Student Resource Discovery (GET /api/v1/resources).
4. Role-Based Access Control (RBAC) enforcing Admin only for mutation operations.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import require_admin
from fastapi import HTTPException
from pydantic import ValidationError
from main import leaderboard_direct_alias
from routes.resources import (
    create_admin_resource,
    delete_admin_resource,
    list_admin_resources,
    list_learning_resources,
    update_admin_resource,
)
from schemas.resources import (
    ResourceCreateRequest,
    ResourceUpdateRequest,
    ResourceResponse,
)


def run_async(coroutine):
    """Executes a coroutine synchronously."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


class TestLeaderboardAndAdminResources(unittest.TestCase):
    def setUp(self):
        self.admin_uuid = "99999999-9999-9999-9999-999999999999"
        self.student_uuid = "11111111-1111-1111-1111-111111111111"
        self.sample_resource_id = "55555555-5555-5555-5555-555555555555"

        self.admin_payload = {
            "sub": "user_admin_999",
            "email": "faculty@skit.ac.in",
            "role": "admin",
        }
        self.student_payload = {
            "sub": "user_student_111",
            "email": "student@skit.ac.in",
            "role": "student",
        }

    # =========================================================================
    # 1. Top-Level Leaderboard Endpoint (GET /api/v1/leaderboard)
    # =========================================================================

    @patch("routes.analytics.get_db")
    def test_direct_leaderboard_alias_endpoint(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_uuid}]
        )

        mock_rpc_data = [
            {
                "rank": 1,
                "user_id": self.student_uuid,
                "display_name": "stu***@skit.ac.in",
                "semester": 5,
                "target_hours_per_day": 3.0,
                "goal_status": "ahead",
                "calculated_goal_status": "ahead",
                "primary_goals": ["GATE 2027"],
                "total_tasks": 15,
                "completed_tasks": 14,
                "planned_study_hours": 22.5,
                "actual_study_hours": 21.0,
                "completion_rate": 93.3,
            }
        ]
        mock_db.rpc.return_value.execute.return_value = MagicMock(data=mock_rpc_data)

        res = run_async(leaderboard_direct_alias(limit=25, offset=0, user_payload=self.student_payload))
        self.assertTrue(res["success"])
        self.assertEqual(len(res["leaderboard"]), 1)
        self.assertEqual(res["leaderboard"][0]["rank"], 1)
        self.assertEqual(res["current_user_rank"]["user_id"], self.student_uuid)

    # =========================================================================
    # 2. Admin Create Resource (POST /api/v1/admin/resources)
    # =========================================================================

    @patch("routes.resources.get_db")
    def test_create_admin_resource_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Admin user lookup
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.admin_uuid}]
        )

        created_data = {
            "id": self.sample_resource_id,
            "title": "Operating Systems: Three Easy Pieces (OSTEP)",
            "description": "Comprehensive textbook covering virtualization, concurrency, and persistence.",
            "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/",
            "category": "book",
            "subject": "Operating Systems",
            "provider": "University of Wisconsin-Madison",
            "difficulty": "intermediate",
            "rating": 4.9,
            "tags": ["Operating Systems", "Concurrency", "Semaphores"],
            "is_active": True,
            "created_by": self.admin_uuid,
            "created_at": "2026-11-12T12:00:00Z",
            "updated_at": "2026-11-12T12:00:00Z",
        }
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[created_data]
        )

        req = ResourceCreateRequest(
            title="Operating Systems: Three Easy Pieces (OSTEP)",
            description="Comprehensive textbook covering virtualization, concurrency, and persistence.",
            url="https://pages.cs.wisc.edu/~remzi/OSTEP/",
            category="book",
            subject="Operating Systems",
            provider="University of Wisconsin-Madison",
            difficulty="intermediate",
            rating=4.9,
            tags=["Operating Systems", "Concurrency", "Semaphores"],
        )

        res = run_async(create_admin_resource(payload=req, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["resource"]["id"], self.sample_resource_id)
        self.assertEqual(res["resource"]["category"], "book")

    def test_create_admin_resource_student_forbidden(self):
        checker = require_admin
        caught = False
        status_code = None
        try:
            run_async(checker(token_payload=self.student_payload))
        except HTTPException as exc:
            caught = True
            status_code = exc.status_code

        self.assertTrue(caught)
        self.assertEqual(status_code, 403)

    def test_create_admin_resource_schema_validation(self):
        # Invalid URL without http/https
        with self.assertRaises(ValidationError):
            ResourceCreateRequest(
                title="Invalid Resource",
                url="ftp://invalid.com/file",
                category="book",
            )

        # Invalid category
        with self.assertRaises(ValidationError):
            ResourceCreateRequest(
                title="Invalid Category Resource",
                url="https://example.com",
                category="podcast",
            )

    # =========================================================================
    # 3. Admin Update Resource (PATCH /api/v1/admin/resources/{id})
    # =========================================================================

    @patch("routes.resources.get_db")
    def test_update_admin_resource_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Existence check returns resource
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_resource_id}]
        )

        updated_data = {
            "id": self.sample_resource_id,
            "title": "Updated OSTEP Guide",
            "rating": 5.0,
            "difficulty": "advanced",
        }
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[updated_data]
        )

        req = ResourceUpdateRequest(title="Updated OSTEP Guide", rating=5.0, difficulty="advanced")
        res = run_async(update_admin_resource(id=self.sample_resource_id, payload=req, admin_payload=self.admin_payload))

        self.assertTrue(res["success"])
        self.assertEqual(res["resource"]["title"], "Updated OSTEP Guide")
        self.assertEqual(res["resource"]["rating"], 5.0)

    @patch("routes.resources.get_db")
    def test_update_admin_resource_not_found(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Existence check returns empty
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        req = ResourceUpdateRequest(title="New Title")
        with self.assertRaises(HTTPException) as ctx:
            run_async(update_admin_resource(id="non-existent-id", payload=req, admin_payload=self.admin_payload))

        self.assertEqual(ctx.exception.status_code, 404)

    # =========================================================================
    # 4. Admin Delete Resource (DELETE /api/v1/admin/resources/{id})
    # =========================================================================

    @patch("routes.resources.get_db")
    def test_delete_admin_resource_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Existence check
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_resource_id, "title": "Resource To Delete"}]
        )
        mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_resource_id}]
        )

        res = run_async(delete_admin_resource(id=self.sample_resource_id, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["id"], self.sample_resource_id)
        self.assertIn("deleted successfully", res["message"])

    @patch("routes.resources.get_db")
    def test_delete_admin_resource_not_found(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )

        with self.assertRaises(HTTPException) as ctx:
            run_async(delete_admin_resource(id="non-existent-id", admin_payload=self.admin_payload))

        self.assertEqual(ctx.exception.status_code, 404)

    # =========================================================================
    # 5. List Resources (Admin & Student)
    # =========================================================================

    @patch("routes.resources.get_db")
    def test_list_admin_resources(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": "r1", "title": "Resource 1"}, {"id": "r2", "title": "Resource 2"}]
        )

        res = run_async(list_admin_resources(category=None, limit=50, offset=0, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 2)

    @patch("routes.resources.get_db")
    def test_list_student_resources(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
            data=[{"id": "r1", "title": "Active Course", "is_active": True}]
        )

        res = run_async(list_learning_resources(limit=10, offset=0, user_data=self.student_payload))
        self.assertTrue(res["success"])
        self.assertEqual(len(res["resources"]), 1)


if __name__ == "__main__":
    unittest.main()

