"""
Unit tests for Notifications CRUD Endpoints, Pydantic Schemas, and Error Handling.
Verifies:
1. get_notifications returns student notifications and unread counter.
2. get_notifications with unread_only=True filters notifications.
3. create_notification successfully inserts a notification.
4. mark_notification_as_read sets is_read to True and read_at timestamp.
5. mark_notification_as_read raises 404 when notification does not exist or belongs to another student.
6. mark_notification_as_read raises 422 for malformed UUID.
7. mark_all_notifications_as_read marks all unread notifications as read.
8. delete_notification removes notification and returns success.
9. Missing Clerk ID raises 401 Unauthorized.
10. Notification schema validations (message length, valid types).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi import HTTPException
from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes.notifications import (
    create_notification,
    delete_notification,
    get_authenticated_user_id,
    get_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)
from schemas.notifications import (
    NotificationBulkReadResponse,
    NotificationCreateRequest,
    NotificationListResponse,
    NotificationResponse,
    NotificationStatusUpdateResponse,
)


def run_async(coroutine):
    """Executes a non-suspending coroutine synchronously without event loop socket overhead."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not complete synchronously")


class TestNotificationsEndpoints(unittest.TestCase):
    """Pure unit tests verifying notification CRUD logic, database queries, and security."""

    def setUp(self):
        self.mock_user_data = {
            "sub": "user_clerk_123",
            "email": "student@skit.ac.in",
        }
        self.user_uuid = "uuid-student-123"

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_get_notifications_success(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_unread_res = MagicMock()
        mock_unread_res.count = 1
        mock_unread_res.data = [{"id": "n1"}]

        mock_list_res = MagicMock()
        mock_list_res.data = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "user_id": self.user_uuid,
                "type": "reminder",
                "message": "Upcoming study session: Operating Systems",
                "is_read": False,
                "read_at": None,
                "created_at": "2026-11-05T10:00:00Z",
            }
        ]

        mock_table = MagicMock()
        mock_db.table.return_value = mock_table

        mock_unread_chain = MagicMock()
        mock_unread_chain.eq.return_value.eq.return_value.execute.return_value = mock_unread_res

        mock_list_chain = MagicMock()
        mock_list_chain.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_list_res

        def mock_select(*args, **kwargs):
            if kwargs.get("count") == "exact":
                return mock_unread_chain
            return mock_list_chain

        mock_table.select.side_effect = mock_select

        result = run_async(
            get_notifications(
                unread_only=False,
                limit=50,
                offset=0,
                user_data=self.mock_user_data,
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["unread_count"], 1)
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(len(result["notifications"]), 1)
        self.assertEqual(result["notifications"][0]["type"], "reminder")

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_get_notifications_unread_only(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_unread_res = MagicMock()
        mock_unread_res.count = 1
        mock_unread_res.data = [{"id": "n1"}]

        mock_list_res = MagicMock()
        mock_list_res.data = [
            {
                "id": "11111111-1111-1111-1111-111111111111",
                "user_id": self.user_uuid,
                "type": "alert",
                "message": "Overdue revision session",
                "is_read": False,
                "read_at": None,
                "created_at": "2026-11-05T10:00:00Z",
            }
        ]

        mock_table = MagicMock()
        mock_db.table.return_value = mock_table

        mock_unread_chain = MagicMock()
        mock_unread_chain.eq.return_value.eq.return_value.execute.return_value = mock_unread_res

        mock_list_chain = MagicMock()
        mock_list_chain.eq.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value = mock_list_res

        def mock_select(*args, **kwargs):
            if kwargs.get("count") == "exact":
                return mock_unread_chain
            return mock_list_chain

        mock_table.select.side_effect = mock_select

        result = run_async(
            get_notifications(
                unread_only=True,
                limit=50,
                offset=0,
                user_data=self.mock_user_data,
            )
        )

        self.assertTrue(result["success"])
        self.assertEqual(result["unread_count"], 1)
        self.assertEqual(len(result["notifications"]), 1)
        self.assertFalse(result["notifications"][0]["is_read"])

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_create_notification(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        created_item = {
            "id": "22222222-2222-2222-2222-222222222222",
            "user_id": self.user_uuid,
            "type": "rebalance",
            "title": "Adaptive Rebalance",
            "message": "AI schedule rebalance suggested for weak topics",
            "is_read": False,
            "read_at": None,
            "created_at": "2026-11-05T12:00:00Z",
        }
        mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[created_item])

        payload = NotificationCreateRequest(
            title="Adaptive Rebalance",
            message="AI schedule rebalance suggested for weak topics",
            type="rebalance",
        )
        result = run_async(create_notification(payload=payload, user_data=self.mock_user_data))

        self.assertTrue(result["success"])
        self.assertEqual(result["notification"]["type"], "rebalance")
        self.assertEqual(result["notification"]["title"], "Adaptive Rebalance")
        self.assertFalse(result["notification"]["is_read"])

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_mark_notification_as_read_success(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        target_uuid = "11111111-1111-1111-1111-111111111111"
        updated_item = {
            "id": target_uuid,
            "user_id": self.user_uuid,
            "type": "reminder",
            "message": "Upcoming study session",
            "is_read": True,
            "read_at": "2026-11-05T12:05:00Z",
            "created_at": "2026-11-05T10:00:00Z",
        }

        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
            data=[updated_item]
        )

        result = run_async(mark_notification_as_read(id=target_uuid, user_data=self.mock_user_data))

        self.assertTrue(result["success"])
        self.assertTrue(result["notification"]["is_read"])
        self.assertEqual(result["notification"]["id"], target_uuid)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_mark_notification_as_read_not_found(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
            data=[]
        )

        target_uuid = "99999999-9999-9999-9999-999999999999"
        with self.assertRaises(HTTPException) as ctx:
            run_async(mark_notification_as_read(id=target_uuid, user_data=self.mock_user_data))

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("Notification not found", ctx.exception.detail)

    def test_mark_notification_as_read_invalid_uuid(self):
        with self.assertRaises(HTTPException) as ctx:
            run_async(mark_notification_as_read(id="invalid-uuid-string", user_data=self.mock_user_data))

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIn("Must be a valid UUID", ctx.exception.detail)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_mark_all_notifications_as_read(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{"id": "n1"}, {"id": "n2"}]
        )

        result = run_async(mark_all_notifications_as_read(user_data=self.mock_user_data))

        self.assertTrue(result["success"])
        self.assertEqual(result["updated_count"], 2)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_delete_notification(self, mock_get_db, mock_get_or_create_user):
        mock_get_or_create_user.return_value = self.user_uuid
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        target_uuid = "11111111-1111-1111-1111-111111111111"
        mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
            data=[{"id": target_uuid}]
        )

        result = run_async(delete_notification(id=target_uuid, user_data=self.mock_user_data))

        self.assertTrue(result["success"])
        self.assertEqual(result["id"], target_uuid)

    def test_missing_clerk_id_raises_401(self):
        with self.assertRaises(HTTPException) as ctx:
            get_authenticated_user_id({})

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("Authenticated user Clerk ID is missing", ctx.exception.detail)

    def test_notification_schema_validation(self):
        # Empty message should fail
        with self.assertRaises(ValidationError):
            NotificationCreateRequest(message="")

        # Valid payload
        valid = NotificationCreateRequest(message="Valid notification message", type="achievement")
        self.assertEqual(valid.message, "Valid notification message")
        self.assertEqual(valid.type, "achievement")


if __name__ == "__main__":
    unittest.main()
