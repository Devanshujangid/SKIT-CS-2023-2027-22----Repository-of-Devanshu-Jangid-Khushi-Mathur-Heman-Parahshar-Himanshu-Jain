import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from routes.notifications import (
    get_user_notifications,
    mark_single_notification_read,
    mark_all_notifications_read,
)


class TestNotificationsEndpoints(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_user = {
            "sub": "user_test_clerk_12345",
            "email": "teststudent@skit.ac.in",
            "role": "student",
        }

    async def test_get_notifications_returns_structured_payload(self):
        result = await get_user_notifications(user_payload=self.mock_user)
        self.assertTrue(result.get("success"))
        self.assertIn("notifications", result)
        self.assertIn("unread_count", result)
        self.assertIsInstance(result["notifications"], list)
        self.assertGreater(len(result["notifications"]), 0)

        # Validate item schema
        item = result["notifications"][0]
        self.assertIn("id", item)
        self.assertIn("type", item)
        self.assertIn("title", item)
        self.assertIn("description", item)
        self.assertIn("is_read", item)

    async def test_mark_single_notification_read(self):
        notif_id = "notif-exam-midterm-os"
        res = await mark_single_notification_read(
            notification_id=notif_id,
            user_payload=self.mock_user,
        )
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("is_read"))
        self.assertEqual(res.get("notification_id"), notif_id)

    async def test_mark_all_read(self):
        res = await mark_all_notifications_read(user_payload=self.mock_user)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("unread_count"), 0)


if __name__ == "__main__":
    unittest.main()
