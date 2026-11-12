"""
Unit tests for Automated Notification Engine & Scheduled Dispatch.
Verifies:
1. Detection of unresolved weak topics from study plans.
2. Detection of upcoming exams from plan milestones and scheduled tasks.
3. Idempotent deduplication preventing spam within 24h or for unread alerts.
4. Targeted dispatch for individual students.
5. Batch dispatch across all students.
6. POST /api/v1/notifications/dispatch-daily endpoint permissions & execution.
"""

from datetime import date, datetime, timedelta, timezone
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes.notifications import trigger_daily_notification_dispatch
from services.notification_engine import NotificationEngine, notification_engine


def run_coro(coroutine):
    """Executes a coroutine synchronously."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


class TestNotificationEngine(unittest.TestCase):
    """Unit tests for NotificationEngine logic and deduplication."""

    def setUp(self):
        self.user_id = "11111111-1111-1111-1111-111111111111"
        self.sample_plan_data = {
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 2.0,
                    "sessions": [
                        {
                            "id": "sess-1",
                            "subject": "Operating Systems",
                            "topic": "Process Synchronization",
                            "duration_hours": 1.5,
                            "activity_type": "core_concept_study",
                            "priority": "high",
                        }
                    ],
                }
            ],
            "monthly_milestones": [
                {
                    "week": 2,
                    "milestone": "Operating Systems Midterm Exam Preparation",
                    "key_deliverable": "Score 85%+ on Unit 1-2 Revision Assessment",
                }
            ],
        }

    def test_detect_unresolved_weak_topics(self):
        # With default plan on day 7, an uncompleted past session produces a weak topic
        alerts = NotificationEngine.detect_unresolved_weak_topics(
            user_id=self.user_id,
            plan_data=self.sample_plan_data,
        )

        self.assertGreaterEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["type"], "weak_topic")
        self.assertEqual(alert["user_id"], self.user_id)
        self.assertIn("Operating Systems", alert["title"])
        self.assertIn("Process Synchronization", alert["message"])
        self.assertFalse(alert["is_read"])

    def test_detect_upcoming_exams_from_milestones(self):
        alerts = NotificationEngine.detect_upcoming_exams(
            user_id=self.user_id,
            plan_data=self.sample_plan_data,
            tasks=[],
        )

        self.assertGreaterEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["type"], "exam")
        self.assertIn("Week 2", alert["title"])
        self.assertIn("Midterm Exam", alert["message"])
        self.assertFalse(alert["is_read"])

    def test_detect_upcoming_exams_from_tasks(self):
        today = date.today()
        upcoming_date = today + timedelta(days=3)

        tasks = [
            {
                "id": "task-assessment-1",
                "title": "Database Systems Unit 2 Quiz Assessment",
                "description": "Midterm preparation quiz",
                "scheduled_date": upcoming_date.isoformat(),
                "is_completed": False,
            }
        ]

        alerts = NotificationEngine.detect_upcoming_exams(
            user_id=self.user_id,
            plan_data={"monthly_milestones": []},
            tasks=tasks,
        )

        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert["type"], "exam")
        self.assertIn("Upcoming Assessment", alert["title"])
        self.assertIn("Database Systems Unit 2 Quiz", alert["message"])

    def test_is_duplicate_prevention(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = [
            {
                "type": "weak_topic",
                "title": "Unresolved Weak Topic: Operating Systems",
                "is_read": False,
                "created_at": now_iso,
            }
        ]

        # Duplicate check on exact unread title
        is_dup = NotificationEngine.is_duplicate(
            existing_notifications=existing,
            alert_type="weak_topic",
            title="Unresolved Weak Topic: Operating Systems",
            lookback_hours=24,
        )
        self.assertTrue(is_dup)

        # Different subject is not a duplicate
        not_dup = NotificationEngine.is_duplicate(
            existing_notifications=existing,
            alert_type="weak_topic",
            title="Unresolved Weak Topic: Database Systems",
            lookback_hours=24,
        )
        self.assertFalse(not_dup)

    def test_dispatch_for_student_dry_run(self):
        mock_db = MagicMock()
        # Mock empty existing notifications
        mock_db.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        # Mock active study plan
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "plan-1", "plan_data": self.sample_plan_data}]
        )
        # Mock empty uncompleted tasks
        mock_db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )

        result = NotificationEngine.dispatch_for_student(
            user_id=self.user_id,
            db=mock_db,
            dry_run=True,
        )

        self.assertEqual(result["user_id"], self.user_id)
        self.assertGreaterEqual(result["total_created"], 1)
        # In dry run mode, db.insert must not be called
        mock_db.table("notifications").insert.assert_not_called()

    def test_run_daily_notification_dispatch_batch(self):
        mock_db = MagicMock()
        # Mock users query with 2 students
        mock_users = [
            {"id": "11111111-1111-1111-1111-111111111111", "email": "s1@skit.ac.in"},
            {"id": "22222222-2222-2222-2222-222222222222", "email": "s2@skit.ac.in"},
        ]
        mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(data=mock_users)

        with patch.object(NotificationEngine, "dispatch_for_student") as mock_dispatch:
            mock_dispatch.return_value = {
                "user_id": "mock",
                "weak_topic_alerts_count": 1,
                "exam_alerts_count": 1,
                "total_created": 2,
                "alerts": [{"type": "weak_topic"}, {"type": "exam"}],
            }

            summary = NotificationEngine.run_daily_notification_dispatch(db=mock_db, dry_run=False)

            self.assertTrue(summary["success"])
            self.assertEqual(summary["students_evaluated"], 2)
            self.assertEqual(summary["total_notifications_dispatched"], 4)
            self.assertEqual(mock_dispatch.call_count, 2)


class TestNotificationDispatchEndpoint(unittest.TestCase):
    """Verifies FastAPI route handler for triggering daily dispatches."""

    def setUp(self):
        self.student_data = {"sub": "clerk_student", "email": "student@skit.ac.in", "role": "student"}
        self.admin_data = {"sub": "clerk_admin", "email": "admin@skit.ac.in", "role": "admin"}
        self.user_uuid = "11111111-1111-1111-1111-111111111111"

    @patch("routes.notifications.get_authenticated_user_id")
    @patch("routes.notifications.get_db")
    @patch.object(NotificationEngine, "dispatch_for_student")
    def test_student_can_trigger_targeted_dispatch(self, mock_dispatch, mock_get_db, mock_get_user_id):
        mock_get_user_id.return_value = self.user_uuid
        mock_dispatch.return_value = {"user_id": self.user_uuid, "total_created": 2}

        res = run_coro(
            trigger_daily_notification_dispatch(
                dry_run=False,
                batch=False,
                user_data=self.student_data,
            )
        )
        self.assertTrue(res["success"])
        mock_dispatch.assert_called_once()

    @patch("routes.notifications.get_authenticated_user_id")
    @patch("routes.notifications.get_db")
    def test_student_rejected_from_batch_dispatch(self, mock_get_db, mock_get_user_id):
        mock_get_user_id.return_value = self.user_uuid

        with self.assertRaises(HTTPException) as ctx:
            run_coro(
                trigger_daily_notification_dispatch(
                    dry_run=False,
                    batch=True,
                    user_data=self.student_data,
                )
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Batch evaluation across all students requires admin role", ctx.exception.detail)

    @patch("routes.notifications.get_authenticated_user_id")
    @patch("routes.notifications.get_db")
    @patch.object(NotificationEngine, "run_daily_notification_dispatch")
    def test_admin_can_trigger_batch_dispatch(self, mock_run_batch, mock_get_db, mock_get_user_id):
        mock_get_user_id.return_value = self.user_uuid
        mock_run_batch.return_value = {
            "success": True,
            "students_evaluated": 5,
            "total_notifications_dispatched": 10,
        }

        res = run_coro(
            trigger_daily_notification_dispatch(
                dry_run=False,
                batch=True,
                user_data=self.admin_data,
            )
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["total_notifications_dispatched"], 10)
        mock_run_batch.assert_called_once()


if __name__ == "__main__":
    unittest.main()

