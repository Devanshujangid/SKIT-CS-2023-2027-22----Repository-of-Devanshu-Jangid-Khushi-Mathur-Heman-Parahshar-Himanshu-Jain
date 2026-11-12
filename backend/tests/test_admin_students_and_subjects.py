"""
Unit Tests for:
1. Admin Student Account Management (GET /api/v1/admin/students, PATCH status, DELETE account).
2. Global Subjects Catalog (CRUD: /api/v1/admin/subjects & public GET /api/v1/subjects).
3. Admin Notification Sender Direct Wiring (/api/v1/admin/notifications).
4. Midnight Leaderboard Recalculation Trigger (/api/v1/admin/leaderboard/refresh).
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import HTTPException
from pydantic import ValidationError
from routes.admin import (
    admin_notifications_direct,
    create_admin_subject,
    delete_admin_subject,
    delete_student_account,
    list_active_subjects_for_students,
    list_admin_students,
    list_admin_subjects,
    trigger_leaderboard_refresh,
    update_admin_subject,
    update_student_account_status,
)
from schemas.admin import (
    StudentStatusUpdateRequest,
    SubjectCreateRequest,
    SubjectUpdateRequest,
)
from schemas.notifications import AdminBroadcastNotificationRequest


def run_async(coroutine):
    """Executes a coroutine synchronously."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


class TestAdminStudentsAndSubjects(unittest.TestCase):
    def setUp(self):
        self.admin_uuid = "99999999-9999-9999-9999-999999999999"
        self.student_uuid = "11111111-1111-1111-1111-111111111111"
        self.sample_subject_id = "88888888-8888-8888-8888-888888888888"

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
    # 1. Student Account Management (GET, PATCH status, DELETE)
    # =========================================================================

    @patch("routes.admin.get_db")
    def test_list_admin_students(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        students_mock = [
            {"id": self.student_uuid, "clerk_id": "c1", "email": "s1@skit.ac.in", "role": "student", "status": "active"},
            {"id": "22222222-2222-2222-2222-222222222222", "clerk_id": "c2", "email": "s2@skit.ac.in", "role": "student", "status": "suspended"},
        ]
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=students_mock)

        def table_side_effect(name):
            t = MagicMock()
            if name == "users":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=students_mock)
            elif name == "student_profiles":
                t.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                    data=[{"semester": 5, "study_hours_per_day": 3.0, "goals": ["GATE"], "subjects": ["OS"]}]
                )
            elif name == "study_plans":
                t.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"id": "p1"}])
            elif name == "tasks":
                t.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"id": "t1", "is_completed": True}])
            return t

        mock_db.table.side_effect = table_side_effect

        res = run_async(list_admin_students(status_filter=None, semester=None, search=None, limit=10, offset=0, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["total_students"], 2)
        self.assertEqual(res["students"][0]["status"], "active")
        self.assertEqual(res["students"][1]["status"], "suspended")

    @patch("routes.admin.get_db")
    def test_update_student_status_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_uuid, "role": "student", "status": "active"}]
        )
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_uuid, "status": "suspended"}]
        )

        req = StudentStatusUpdateRequest(status="suspended", reason="Academic misconduct investigation")
        res = run_async(update_student_account_status(id=self.student_uuid, payload=req, admin_payload=self.admin_payload))

        self.assertTrue(res["success"])
        self.assertEqual(res["status"], "suspended")
        self.assertEqual(res["id"], self.student_uuid)

    @patch("routes.admin.get_db")
    def test_update_student_status_prevent_admin_suspension(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.admin_uuid, "role": "admin", "status": "active"}]
        )

        req = StudentStatusUpdateRequest(status="suspended")
        with self.assertRaises(HTTPException) as ctx:
            run_async(update_student_account_status(id=self.admin_uuid, payload=req, admin_payload=self.admin_payload))

        self.assertEqual(ctx.exception.status_code, 403)

    @patch("routes.admin.get_db")
    def test_delete_student_account_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_uuid, "email": "student@skit.ac.in", "role": "student"}]
        )
        mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": self.student_uuid}]
        )

        res = run_async(delete_student_account(id=self.student_uuid, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["id"], self.student_uuid)
        self.assertIn("permanently deleted", res["message"])

    # =========================================================================
    # 2. Global Curriculum Subjects (CRUD)
    # =========================================================================

    @patch("routes.admin.get_db")
    def test_create_admin_subject_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Duplicate check returns empty
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        created_mock = {
            "id": self.sample_subject_id,
            "code": "5CS4-01",
            "name": "Operating Systems",
            "semester": 5,
            "department": "Computer Science",
            "credits": 3.0,
            "is_active": True,
        }
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[created_mock]
        )

        req = SubjectCreateRequest(
            code="5CS4-01",
            name="Operating Systems",
            semester=5,
            department="Computer Science",
            credits=3.0,
        )
        res = run_async(create_admin_subject(payload=req, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["subject"]["code"], "5CS4-01")
        self.assertEqual(res["subject"]["name"], "Operating Systems")

    @patch("routes.admin.get_db")
    def test_create_admin_subject_duplicate_code(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Duplicate check returns existing
        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "existing-sub-id"}]
        )

        req = SubjectCreateRequest(
            code="5CS4-01",
            name="Operating Systems Duplicate",
            semester=5,
        )
        with self.assertRaises(HTTPException) as ctx:
            run_async(create_admin_subject(payload=req, admin_payload=self.admin_payload))

        self.assertEqual(ctx.exception.status_code, 409)

    @patch("routes.admin.get_db")
    def test_update_admin_subject_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_subject_id, "code": "5CS4-01"}]
        )
        mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_subject_id, "name": "Advanced Operating Systems", "credits": 4.0}]
        )

        req = SubjectUpdateRequest(name="Advanced Operating Systems", credits=4.0)
        res = run_async(update_admin_subject(id=self.sample_subject_id, payload=req, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["subject"]["name"], "Advanced Operating Systems")

    @patch("routes.admin.get_db")
    def test_delete_admin_subject_success(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_subject_id, "name": "Operating Systems"}]
        )
        mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": self.sample_subject_id}]
        )

        res = run_async(delete_admin_subject(id=self.sample_subject_id, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["id"], self.sample_subject_id)

    @patch("routes.admin.get_db")
    def test_list_active_subjects_public(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        q_mock = MagicMock()
        q_mock.eq.return_value = q_mock
        q_mock.order.return_value = q_mock
        q_mock.execute.return_value = MagicMock(
            data=[{"id": "sub1", "code": "CS501", "name": "Theory of Computation"}]
        )
        mock_db.table.return_value.select.return_value = q_mock

        res = run_async(list_active_subjects_for_students(semester=5, department=None, user_data=self.student_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)

    # =========================================================================
    # 3. Direct Admin Notification Sender Wiring
    # =========================================================================

    @patch("routes.notifications.get_db")
    def test_admin_notifications_direct_wiring(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_users = [
            {"id": self.student_uuid, "email": "s1@skit.ac.in", "role": "student"},
        ]
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_users)
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=mock_users)

        req = AdminBroadcastNotificationRequest(
            title="Campus Holiday Notice",
            message="College will remain closed on Friday for festival celebrations.",
            type="announcement",
            target_role="student",
        )
        res = run_async(admin_notifications_direct(payload=req, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertEqual(res["recipient_count"], 1)

    # =========================================================================
    # 4. Midnight Leaderboard Recalculation Trigger
    # =========================================================================

    @patch("cron.daily_leaderboard_job.get_db")
    def test_trigger_leaderboard_refresh_dry_run(self, mock_get_db):
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{"user_id": self.student_uuid, "rank": 1}]
        )

        res = run_async(trigger_leaderboard_refresh(dry_run=True, admin_payload=self.admin_payload))
        self.assertTrue(res["success"])
        self.assertTrue(res["result"]["dry_run"])
        self.assertEqual(res["result"]["evaluated_students"], 1)


if __name__ == "__main__":
    unittest.main()
