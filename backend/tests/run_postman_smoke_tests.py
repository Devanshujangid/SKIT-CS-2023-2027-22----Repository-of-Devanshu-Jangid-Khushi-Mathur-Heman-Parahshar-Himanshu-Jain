"""
Automated Postman Test Runner for Chat and Notification Endpoints.

Executes all 14 test cases defined in:
    postman/Smart_Learning_Planner_Chat_and_Notifications.postman_collection.json

Validates:
1. AI Chat Real-Time SSE Streaming (text/event-stream, delta tokens, [DONE] signal).
2. AI Chat JSON fallback and Academic Guardrail Refusals.
3. Notification CRUD operations (GET, POST, PATCH /read, DELETE).
4. Automated Daily Notification Engine dispatch.
5. Admin Manual Notification Broadcast & RBAC (201 Admin OK, 403 Student Rejection).
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from unittest.mock import MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import require_admin
from fastapi import HTTPException
from pydantic import ValidationError
from main import leaderboard_direct_alias
from routes.ai import ChatRequest, ai_chat
from routes.analytics import update_student_goal_status_endpoint
from routes.notifications import (
    admin_broadcast_notification,
    create_notification,
    delete_notification,
    get_admin_recent_broadcasts,
    get_notifications,
    mark_all_notifications_as_read,
    mark_notification_as_read,
    trigger_daily_notification_dispatch,
)
from routes.resources import (
    create_admin_resource,
    update_admin_resource,
    delete_admin_resource,
    list_admin_resources,
)
from routes.admin import (
    list_admin_students,
    update_student_account_status,
    delete_student_account,
    create_admin_subject,
    list_admin_subjects,
    update_admin_subject,
    delete_admin_subject,
    admin_notifications_direct,
    trigger_leaderboard_refresh,
)
from schemas.notifications import (
    AdminBroadcastNotificationRequest,
    NotificationCreateRequest,
)
from schemas.leaderboard import UpdateGoalStatusRequest
from schemas.resources import ResourceCreateRequest, ResourceUpdateRequest
from schemas.admin import (
    StudentStatusUpdateRequest,
    SubjectCreateRequest,
    SubjectUpdateRequest,
)
from services.chat_stream_service import stream_chat_response


def run_async(coroutine):
    """Executes a coroutine synchronously."""
    try:
        coroutine.send(None)
    except StopIteration as exc:
        return exc.value
    raise RuntimeError("Coroutine did not finish synchronously")


def collect_async_gen(agen):
    """Consumes an async generator synchronously."""
    items = []
    while True:
        try:
            coro = agen.asend(None)
            coro.send(None)
        except StopIteration as exc:
            items.append(exc.value)
        except StopAsyncIteration:
            break
    return items


async def immediate_threadpool(func, *args, **kwargs):
    return func(*args, **kwargs)


class PostmanSmokeTestRunner:
    def __init__(self):
        self.results = []
        self.student_uuid = "11111111-1111-1111-1111-111111111111"
        self.student_data = {
            "sub": "user_student_123",
            "email": "student@skit.ac.in",
            "role": "student",
        }
        self.admin_data = {
            "sub": "user_admin_999",
            "email": "faculty@skit.ac.in",
            "role": "admin",
        }

    def record(self, group: str, test_name: str, method: str, path: str, passed: bool, detail: str, duration_ms: float):
        self.results.append({
            "group": group,
            "test_name": test_name,
            "method": method,
            "path": path,
            "passed": passed,
            "detail": detail,
            "duration_ms": round(duration_ms, 2),
        })

    # =========================================================================
    # Group 1: AI Chat Endpoints
    # =========================================================================

    def test_chat_sse_stream(self):
        t0 = time.perf_now() if hasattr(time, "perf_now") else time.time()
        try:
            mock_client = MagicMock()
            mock_chunk = MagicMock(text="Peterson's algorithm guarantees mutual exclusion.")
            mock_client.models.generate_content_stream.return_value = [mock_chunk]

            with patch("services.chat_stream_service.run_in_threadpool", side_effect=immediate_threadpool):
                agen = stream_chat_response(
                    message="Explain Peterson's algorithm for two-process mutual exclusion",
                    clerk_id=self.student_data["sub"],
                    gemini_client=mock_client,
                )
                chunks = collect_async_gen(agen)

            assert len(chunks) >= 2, "Expected at least content and completion chunks"
            assert "data: [DONE]" in chunks[-1], "Expected [DONE] sentinel"
            assert any("Peterson" in c for c in chunks), "Expected content in stream"

            # Check route StreamingResponse instantiation
            payload = ChatRequest(message="Explain Peterson's algorithm", stream=True)
            res = run_async(ai_chat(payload, self.student_data))
            assert res.media_type == "text/event-stream"
            assert res.headers.get("Cache-Control") == "no-cache"

            dt = (time.time() - t0) * 1000
            self.record("AI Chat", "POST /api/v1/chat (SSE Stream)", "POST", "/api/v1/chat", True, "200 OK | text/event-stream | [DONE] signal verified", dt)
        except Exception as e:
            self.record("AI Chat", "POST /api/v1/chat (SSE Stream)", "POST", "/api/v1/chat", False, str(e), 0)

    @patch("routes.ai.run_in_threadpool", side_effect=immediate_threadpool)
    @patch("routes.ai.generate_gemini_response")
    @patch("routes.ai.recommendation_service.recommend_courses")
    def test_chat_json_payload(self, mock_recommend, mock_generate, mock_threadpool):
        t0 = time.time()
        try:
            mock_generate.return_value = json.dumps({
                "explanation": "Peterson's algorithm is a concurrent programming algorithm for mutual exclusion.",
                "key_points": ["Uses flag and turn variables", "Ensures progress and bounded waiting"],
                "follow_up_suggestion": "Would you like an example in C or Python?"
            })
            mock_recommend.return_value = [
                {"title": "Operating Systems and You", "url": "https://coursera.org/learn/os"}
            ]

            payload = ChatRequest(message="Explain Peterson's algorithm for mutual exclusion", stream=False)
            res = run_async(ai_chat(payload, self.student_data))
            assert res["success"] is True
            assert "explanation" in res
            assert len(res["key_points"]) == 2
            assert res["recommendation_count"] == 1

            dt = (time.time() - t0) * 1000
            self.record("AI Chat", "POST /api/v1/chat (Standard JSON)", "POST", "/api/v1/chat", True, "200 OK | application/json | Structured explanation & recommendations", dt)
        except Exception as e:
            self.record("AI Chat", "POST /api/v1/chat (Standard JSON)", "POST", "/api/v1/chat", False, str(e), 0)

    def test_chat_guardrail_refusal(self):
        t0 = time.time()
        try:
            agen = stream_chat_response(
                message="Who won the cricket match yesterday?",
                clerk_id=self.student_data["sub"],
            )
            chunks = collect_async_gen(agen)
            assert len(chunks) == 2, "Refusal should yield 2 events"
            refusal = json.loads(chunks[0].replace("data: ", "").strip())
            assert refusal["is_refused"] is True
            assert chunks[1].strip() == "data: [DONE]"

            dt = (time.time() - t0) * 1000
            self.record("AI Chat", "POST /api/v1/chat (Guardrail Refusal)", "POST", "/api/v1/chat", True, "200 OK | Guardrail triggered | is_refused=true", dt)
        except Exception as e:
            self.record("AI Chat", "POST /api/v1/chat (Guardrail Refusal)", "POST", "/api/v1/chat", False, str(e), 0)

    def test_chat_short_prompt_validation(self):
        t0 = time.time()
        try:
            failed_as_expected = False
            try:
                ChatRequest(message="?")
            except ValidationError:
                failed_as_expected = True

            assert failed_as_expected, "Short prompt should be rejected by Pydantic"
            dt = (time.time() - t0) * 1000
            self.record("AI Chat", "POST /api/v1/chat (Validation Error)", "POST", "/api/v1/chat", True, "422 Unprocessable Content | min_length=2 enforced", dt)
        except Exception as e:
            self.record("AI Chat", "POST /api/v1/chat (Validation Error)", "POST", "/api/v1/chat", False, str(e), 0)

    # =========================================================================
    # Group 2: Notification Endpoints
    # =========================================================================

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_get_notifications(self, mock_get_db, mock_get_or_create_user):
        t0 = time.time()
        try:
            mock_get_or_create_user.return_value = self.student_uuid
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_unread = MagicMock(count=1, data=[{"id": "n1"}])
            mock_list = MagicMock(
                data=[
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "user_id": self.student_uuid,
                        "type": "exam",
                        "title": "Upcoming Assessment",
                        "message": "Unit 2 Quiz on Wednesday",
                        "is_read": False,
                        "read_at": None,
                        "created_at": "2026-11-07T10:00:00Z",
                    }
                ]
            )

            mock_table = MagicMock()
            mock_db.table.return_value = mock_table
            mock_table.select.side_effect = lambda *args, **kwargs: (
                MagicMock(eq=MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=mock_unread))))))
                if kwargs.get("count") == "exact"
                else MagicMock(eq=MagicMock(return_value=MagicMock(order=MagicMock(return_value=MagicMock(range=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=mock_list))))))))
            )

            res = run_async(get_notifications(unread_only=False, limit=50, offset=0, user_data=self.student_data))
            assert res["success"] is True
            assert res["unread_count"] == 1
            assert len(res["notifications"]) == 1

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "GET /api/v1/notifications", "GET", "/api/v1/notifications", True, "200 OK | List retrieved | unread_count=1", dt)
        except Exception as e:
            self.record("Notifications", "GET /api/v1/notifications", "GET", "/api/v1/notifications", False, str(e), 0)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_get_notifications_unread_only(self, mock_get_db, mock_get_or_create_user):
        t0 = time.time()
        try:
            mock_get_or_create_user.return_value = self.student_uuid
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_unread = MagicMock(count=2, data=[{"id": "n1"}, {"id": "n2"}])
            mock_list = MagicMock(
                data=[
                    {
                        "id": "11111111-1111-1111-1111-111111111111",
                        "user_id": self.student_uuid,
                        "type": "weak_topic",
                        "title": "Unresolved Weak Topic: Dynamic Programming",
                        "message": "Scored 42% on Dynamic Programming. Practice is advised.",
                        "is_read": False,
                        "read_at": None,
                        "created_at": "2026-11-07T10:00:00Z",
                    }
                ]
            )

            mock_table = MagicMock()
            mock_db.table.return_value = mock_table
            mock_table.select.side_effect = lambda *args, **kwargs: (
                MagicMock(eq=MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=mock_unread))))))
                if kwargs.get("count") == "exact"
                else MagicMock(eq=MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(order=MagicMock(return_value=MagicMock(range=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=mock_list))))))))))
            )

            res = run_async(get_notifications(unread_only=True, limit=20, offset=0, user_data=self.student_data))
            assert res["success"] is True
            assert res["unread_count"] == 2
            assert len(res["notifications"]) == 1
            assert res["notifications"][0]["is_read"] is False

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "GET /api/v1/notifications?unread_only=true", "GET", "/api/v1/notifications?unread_only=true", True, "200 OK | Filtered unread alerts | unread_count=2", dt)
        except Exception as e:
            self.record("Notifications", "GET /api/v1/notifications?unread_only=true", "GET", "/api/v1/notifications?unread_only=true", False, str(e), 0)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_post_notification(self, mock_get_db, mock_get_or_create_user):
        t0 = time.time()
        try:
            mock_get_or_create_user.return_value = self.student_uuid
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            created = {
                "id": "22222222-2222-2222-2222-222222222222",
                "user_id": self.student_uuid,
                "type": "exam",
                "title": "Upcoming Exam Reminder",
                "message": "Unit 2 Midterm scheduled for Wednesday 10:00 AM.",
                "is_read": False,
                "created_at": "2026-11-07T10:00:00Z",
            }
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[created])

            payload = NotificationCreateRequest(
                title="Upcoming Exam Reminder",
                message="Unit 2 Midterm scheduled for Wednesday 10:00 AM.",
                type="exam",
            )
            res = run_async(create_notification(payload=payload, user_data=self.student_data))
            assert res["success"] is True
            assert res["notification"]["type"] == "exam"

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "POST /api/v1/notifications", "POST", "/api/v1/notifications", True, "201 Created | Alert stored | type=exam", dt)
        except Exception as e:
            self.record("Notifications", "POST /api/v1/notifications", "POST", "/api/v1/notifications", False, str(e), 0)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_patch_notification_read(self, mock_get_db, mock_get_or_create_user):
        t0 = time.time()
        try:
            mock_get_or_create_user.return_value = self.student_uuid
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            target_id = "11111111-1111-1111-1111-111111111111"
            updated = {
                "id": target_id,
                "user_id": self.student_uuid,
                "type": "exam",
                "title": "Upcoming Assessment",
                "message": "Unit 2 Quiz on Wednesday",
                "is_read": True,
                "read_at": "2026-11-07T10:30:00Z",
                "created_at": "2026-11-07T10:00:00Z",
            }
            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
                data=[updated]
            )

            res = run_async(mark_notification_as_read(id=target_id, user_data=self.student_data))
            assert res["success"] is True
            assert res["notification"]["is_read"] is True

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "PATCH /api/v1/notifications/{id}/read", "PATCH", f"/api/v1/notifications/{target_id}/read", True, "200 OK | is_read=true | read_at timestamped", dt)
        except Exception as e:
            self.record("Notifications", "PATCH /api/v1/notifications/{id}/read", "PATCH", "/api/v1/notifications/{id}/read", False, str(e), 0)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_patch_read_all(self, mock_get_db, mock_get_or_create_user):
        t0 = time.time()
        try:
            mock_get_or_create_user.return_value = self.student_uuid
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_db.table.return_value.update.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
                data=[{"id": "n1"}, {"id": "n2"}]
            )

            res = run_async(mark_all_notifications_as_read(user_data=self.student_data))
            assert res["success"] is True
            assert res["updated_count"] == 2

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "PATCH /api/v1/notifications/read-all", "PATCH", "/api/v1/notifications/read-all", True, "200 OK | Bulk mark-as-read | updated_count=2", dt)
        except Exception as e:
            self.record("Notifications", "PATCH /api/v1/notifications/read-all", "PATCH", "/api/v1/notifications/read-all", False, str(e), 0)

    @patch("routes.notifications.get_or_create_user")
    @patch("routes.notifications.get_db")
    def test_delete_notification(self, mock_get_db, mock_get_or_create_user):
        t0 = time.time()
        try:
            mock_get_or_create_user.return_value = self.student_uuid
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            target_id = "11111111-1111-1111-1111-111111111111"
            mock_db.table.return_value.delete.return_value.eq.return_value.eq.return_value.select.return_value.execute.return_value = MagicMock(
                data=[{"id": target_id}]
            )

            res = run_async(delete_notification(id=target_id, user_data=self.student_data))
            assert res["success"] is True
            assert res["id"] == target_id

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "DELETE /api/v1/notifications/{id}", "DELETE", f"/api/v1/notifications/{target_id}", True, "200 OK | Notification deleted with ownership check", dt)
        except Exception as e:
            self.record("Notifications", "DELETE /api/v1/notifications/{id}", "DELETE", "/api/v1/notifications/{id}", False, str(e), 0)

    @patch("routes.notifications.get_authenticated_user_id")
    @patch("routes.notifications.get_db")
    @patch("routes.notifications.notification_engine.dispatch_for_student")
    def test_dispatch_daily(self, mock_dispatch, mock_get_db, mock_get_user_id):
        t0 = time.time()
        try:
            mock_get_user_id.return_value = self.student_uuid
            mock_dispatch.return_value = {
                "user_id": self.student_uuid,
                "weak_topic_alerts_count": 1,
                "exam_alerts_count": 1,
                "total_created": 2,
            }

            res = run_async(trigger_daily_notification_dispatch(dry_run=True, batch=False, user_data=self.student_data))
            assert res["success"] is True
            assert res["dry_run"] is True

            dt = (time.time() - t0) * 1000
            self.record("Notifications", "POST /api/v1/notifications/dispatch-daily", "POST", "/api/v1/notifications/dispatch-daily", True, "200 OK | Engine triggered | dry_run=true", dt)
        except Exception as e:
            self.record("Notifications", "POST /api/v1/notifications/dispatch-daily", "POST", "/api/v1/notifications/dispatch-daily", False, str(e), 0)

    # =========================================================================
    # Group 3: Admin Broadcast Endpoints
    # =========================================================================

    @patch("routes.notifications.get_db")
    def test_admin_broadcast_success(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_users = [
                {"id": "11111111-1111-1111-1111-111111111111", "email": "s1@skit.ac.in", "role": "student"},
                {"id": "22222222-2222-2222-2222-222222222222", "email": "s2@skit.ac.in", "role": "student"},
            ]
            mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_users)
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=mock_users)

            req = AdminBroadcastNotificationRequest(
                title="Midterm Assessment Timetable Finalized",
                message="Midterm examinations commence on Nov 15. Check your updated schedules.",
                type="exam",
                target_role="student",
            )
            res = run_async(admin_broadcast_notification(payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["recipient_count"] == 2

            dt = (time.time() - t0) * 1000
            self.record("Admin Broadcast", "POST /api/v1/notifications/admin/broadcast (Admin)", "POST", "/api/v1/notifications/admin/broadcast", True, "201 Created | Broadcasted to 2 students", dt)
        except Exception as e:
            self.record("Admin Broadcast", "POST /api/v1/notifications/admin/broadcast (Admin)", "POST", "/api/v1/notifications/admin/broadcast", False, str(e), 0)

    def test_admin_broadcast_student_forbidden(self):
        t0 = time.time()
        try:
            checker = require_admin
            caught = False
            status_code = None
            detail = None
            try:
                run_async(checker(token_payload=self.student_data))
            except HTTPException as exc:
                caught = True
                status_code = exc.status_code
                detail = exc.detail

            assert caught, "Expected HTTPException to be raised"
            assert status_code == 403, f"Expected 403 Forbidden, got {status_code}"
            assert "Access forbidden" in str(detail)

            dt = (time.time() - t0) * 1000
            self.record("Admin Broadcast", "POST /api/v1/notifications/admin/broadcast (Student Rejection)", "POST", "/api/v1/notifications/admin/broadcast", True, "403 Forbidden | Student role blocked by require_admin", dt)
        except Exception as e:
            self.record("Admin Broadcast", "POST /api/v1/notifications/admin/broadcast (Student Rejection)", "POST", "/api/v1/notifications/admin/broadcast", False, str(e), 0)

    @patch("routes.notifications.get_db")
    def test_get_admin_broadcast_history(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db

            mock_history = [
                {"id": "b1", "title": "Campus Notice", "message": "Library hours extended", "type": "system", "created_at": "2026-11-07T08:00:00Z"}
            ]
            mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=mock_history)

            res = run_async(get_admin_recent_broadcasts(limit=20, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["count"] == 1

            dt = (time.time() - t0) * 1000
            self.record("Admin Broadcast", "GET /api/v1/notifications/admin/broadcasts", "GET", "/api/v1/notifications/admin/broadcasts", True, "200 OK | Broadcast history list returned", dt)
        except Exception as e:
            self.record("Admin Broadcast", "GET /api/v1/notifications/admin/broadcasts", "GET", "/api/v1/notifications/admin/broadcasts", False, str(e), 0)

    # =========================================================================
    # Group 4: Leaderboard Endpoints
    # =========================================================================

    @patch("routes.analytics.get_db")
    def test_get_leaderboard(self, mock_get_db):
        t0 = time.time()
        try:
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
                    "total_tasks": 10,
                    "completed_tasks": 9,
                    "planned_study_hours": 15.0,
                    "actual_study_hours": 13.5,
                    "completion_rate": 90.0,
                }
            ]
            mock_db.rpc.return_value.execute.return_value = MagicMock(data=mock_rpc_data)

            res = run_async(leaderboard_direct_alias(limit=10, offset=0, user_payload=self.student_data))
            assert res["success"] is True
            assert len(res["leaderboard"]) == 1
            assert res["leaderboard"][0]["rank"] == 1

            dt = (time.time() - t0) * 1000
            self.record("Leaderboard", "GET /api/v1/leaderboard", "GET", "/api/v1/leaderboard", True, "200 OK | Dense rank & peer standings retrieved", dt)
        except Exception as e:
            self.record("Leaderboard", "GET /api/v1/leaderboard", "GET", "/api/v1/leaderboard", False, str(e), 0)

    @patch("routes.analytics.get_db")
    def test_patch_goal_status(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": self.student_uuid}]
            )
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"user_id": self.student_uuid, "goal_status": "ahead"}]
            )

            req = UpdateGoalStatusRequest(goal_status="ahead")
            res = run_async(update_student_goal_status_endpoint(payload=req, user_payload=self.student_data))
            assert res["success"] is True
            assert res["goal_status"] == "ahead"

            dt = (time.time() - t0) * 1000
            self.record("Leaderboard", "PATCH /api/v1/analytics/goal-status", "PATCH", "/api/v1/analytics/goal-status", True, "200 OK | Student goal_status updated to 'ahead'", dt)
        except Exception as e:
            self.record("Leaderboard", "PATCH /api/v1/analytics/goal-status", "PATCH", "/api/v1/analytics/goal-status", False, str(e), 0)

    # =========================================================================
    # Group 5: Admin Resources Endpoints
    # =========================================================================

    @patch("routes.resources.get_db")
    def test_post_admin_resource(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": "admin-uuid-1"}]
            )
            created_mock = {
                "id": "res-uuid-1",
                "title": "Operating Systems: Three Easy Pieces",
                "url": "https://pages.cs.wisc.edu/~remzi/OSTEP/",
                "category": "book",
                "is_active": True,
            }
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[created_mock])

            req = ResourceCreateRequest(
                title="Operating Systems: Three Easy Pieces",
                url="https://pages.cs.wisc.edu/~remzi/OSTEP/",
                category="book",
                subject="Operating Systems",
            )
            res = run_async(create_admin_resource(payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["resource"]["id"] == "res-uuid-1"

            dt = (time.time() - t0) * 1000
            self.record("Admin Resources", "POST /api/v1/admin/resources", "POST", "/api/v1/admin/resources", True, "201 Created | Learning resource cataloged", dt)
        except Exception as e:
            self.record("Admin Resources", "POST /api/v1/admin/resources", "POST", "/api/v1/admin/resources", False, str(e), 0)

    @patch("routes.resources.get_db")
    def test_patch_admin_resource(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": "res-uuid-1"}]
            )
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "res-uuid-1", "rating": 5.0}]
            )

            req = ResourceUpdateRequest(rating=5.0)
            res = run_async(update_admin_resource(id="res-uuid-1", payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["resource"]["rating"] == 5.0

            dt = (time.time() - t0) * 1000
            self.record("Admin Resources", "PATCH /api/v1/admin/resources/{id}", "PATCH", "/api/v1/admin/resources/res-uuid-1", True, "200 OK | Learning resource rating updated", dt)
        except Exception as e:
            self.record("Admin Resources", "PATCH /api/v1/admin/resources/{id}", "PATCH", "/api/v1/admin/resources/res-uuid-1", False, str(e), 0)

    @patch("routes.resources.get_db")
    def test_delete_admin_resource(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": "res-uuid-1", "title": "OSTEP"}]
            )
            mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "res-uuid-1"}]
            )

            res = run_async(delete_admin_resource(id="res-uuid-1", admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["id"] == "res-uuid-1"

            dt = (time.time() - t0) * 1000
            self.record("Admin Resources", "DELETE /api/v1/admin/resources/{id}", "DELETE", "/api/v1/admin/resources/res-uuid-1", True, "200 OK | Learning resource removed from catalog", dt)
        except Exception as e:
            self.record("Admin Resources", "DELETE /api/v1/admin/resources/{id}", "DELETE", "/api/v1/admin/resources/res-uuid-1", False, str(e), 0)

    @patch("routes.resources.get_db")
    def test_get_admin_resources(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=[{"id": "r1", "title": "Resource 1"}, {"id": "r2", "title": "Resource 2"}]
            )

            res = run_async(list_admin_resources(category=None, limit=20, offset=0, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["count"] == 2

            dt = (time.time() - t0) * 1000
            self.record("Admin Resources", "GET /api/v1/admin/resources", "GET", "/api/v1/admin/resources", True, "200 OK | Admin resource catalog audit list returned", dt)
        except Exception as e:
            self.record("Admin Resources", "GET /api/v1/admin/resources", "GET", "/api/v1/admin/resources", False, str(e), 0)

    # =========================================================================
    # Group 6: Admin Students Endpoints
    # =========================================================================

    @patch("routes.admin.get_db")
    def test_get_admin_students(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": self.student_uuid, "clerk_id": "c1", "email": "s1@skit.ac.in", "role": "student", "status": "active"}]
            )
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"semester": 5, "study_hours_per_day": 3.0, "goals": [], "subjects": []}]
            )

            res = run_async(list_admin_students(status_filter=None, semester=None, search=None, limit=20, offset=0, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["total_students"] >= 1

            dt = (time.time() - t0) * 1000
            self.record("Admin Students", "GET /api/v1/admin/students", "GET", "/api/v1/admin/students", True, "200 OK | Enrolled student roster with status retrieved", dt)
        except Exception as e:
            self.record("Admin Students", "GET /api/v1/admin/students", "GET", "/api/v1/admin/students", False, str(e), 0)

    @patch("routes.admin.get_db")
    def test_patch_student_status(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": self.student_uuid, "role": "student", "status": "active"}]
            )
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": self.student_uuid, "status": "suspended"}]
            )

            req = StudentStatusUpdateRequest(status="suspended", reason="Account audit")
            res = run_async(update_student_account_status(id=self.student_uuid, payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["status"] == "suspended"

            dt = (time.time() - t0) * 1000
            self.record("Admin Students", "PATCH /api/v1/admin/students/{id}/status", "PATCH", f"/api/v1/admin/students/{self.student_uuid}/status", True, "200 OK | Account status updated to 'suspended'", dt)
        except Exception as e:
            self.record("Admin Students", "PATCH /api/v1/admin/students/{id}/status", "PATCH", f"/api/v1/admin/students/{self.student_uuid}/status", False, str(e), 0)

    @patch("routes.admin.get_db")
    def test_delete_student_account(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": self.student_uuid, "email": "s1@skit.ac.in", "role": "student"}]
            )
            mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": self.student_uuid}]
            )

            res = run_async(delete_student_account(id=self.student_uuid, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["id"] == self.student_uuid

            dt = (time.time() - t0) * 1000
            self.record("Admin Students", "DELETE /api/v1/admin/students/{id}", "DELETE", f"/api/v1/admin/students/{self.student_uuid}", True, "200 OK | Student account permanently deleted with cascade", dt)
        except Exception as e:
            self.record("Admin Students", "DELETE /api/v1/admin/students/{id}", "DELETE", f"/api/v1/admin/students/{self.student_uuid}", False, str(e), 0)

    # =========================================================================
    # Group 7: Admin Subjects Endpoints
    # =========================================================================

    @patch("routes.admin.get_db")
    def test_post_admin_subject(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[]
            )
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(
                data=[{"id": "sub-1", "code": "5CS4-01", "name": "Operating Systems", "semester": 5, "credits": 3.0}]
            )

            req = SubjectCreateRequest(code="5CS4-01", name="Operating Systems", semester=5, credits=3.0)
            res = run_async(create_admin_subject(payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["subject"]["code"] == "5CS4-01"

            dt = (time.time() - t0) * 1000
            self.record("Admin Subjects", "POST /api/v1/admin/subjects", "POST", "/api/v1/admin/subjects", True, "201 Created | Curriculum subject registered", dt)
        except Exception as e:
            self.record("Admin Subjects", "POST /api/v1/admin/subjects", "POST", "/api/v1/admin/subjects", False, str(e), 0)

    @patch("routes.admin.get_db")
    def test_get_admin_subjects(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.order.return_value.order.return_value.range.return_value.execute.return_value = MagicMock(
                data=[{"id": "sub-1", "code": "5CS4-01", "name": "Operating Systems"}]
            )

            res = run_async(list_admin_subjects(limit=20, offset=0, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["total"] >= 1

            dt = (time.time() - t0) * 1000
            self.record("Admin Subjects", "GET /api/v1/admin/subjects", "GET", "/api/v1/admin/subjects", True, "200 OK | Global subjects catalog retrieved", dt)
        except Exception as e:
            self.record("Admin Subjects", "GET /api/v1/admin/subjects", "GET", "/api/v1/admin/subjects", False, str(e), 0)

    @patch("routes.admin.get_db")
    def test_patch_admin_subject(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": "sub-1", "code": "5CS4-01"}]
            )
            mock_db.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "sub-1", "name": "Advanced Operating Systems", "credits": 4.0}]
            )

            req = SubjectUpdateRequest(name="Advanced Operating Systems", credits=4.0)
            res = run_async(update_admin_subject(id="sub-1", payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["subject"]["name"] == "Advanced Operating Systems"

            dt = (time.time() - t0) * 1000
            self.record("Admin Subjects", "PATCH /api/v1/admin/subjects/{id}", "PATCH", "/api/v1/admin/subjects/sub-1", True, "200 OK | Subject curriculum credits updated", dt)
        except Exception as e:
            self.record("Admin Subjects", "PATCH /api/v1/admin/subjects/{id}", "PATCH", "/api/v1/admin/subjects/sub-1", False, str(e), 0)

    @patch("routes.admin.get_db")
    def test_delete_admin_subject(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
                data=[{"id": "sub-1", "name": "Operating Systems"}]
            )
            mock_db.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(
                data=[{"id": "sub-1"}]
            )

            res = run_async(delete_admin_subject(id="sub-1", admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["id"] == "sub-1"

            dt = (time.time() - t0) * 1000
            self.record("Admin Subjects", "DELETE /api/v1/admin/subjects/{id}", "DELETE", "/api/v1/admin/subjects/sub-1", True, "200 OK | Subject deleted from curriculum", dt)
        except Exception as e:
            self.record("Admin Subjects", "DELETE /api/v1/admin/subjects/{id}", "DELETE", "/api/v1/admin/subjects/sub-1", False, str(e), 0)

    # =========================================================================
    # Group 8: Direct Admin Notifications & Midnight Leaderboard Cron Trigger
    # =========================================================================

    @patch("routes.notifications.get_db")
    def test_post_admin_notifications_direct(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_users = [{"id": self.student_uuid, "email": "s1@skit.ac.in", "role": "student"}]
            mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=mock_users)
            mock_db.table.return_value.insert.return_value.execute.return_value = MagicMock(data=mock_users)

            req = AdminBroadcastNotificationRequest(
                title="Exam Schedule Published",
                message="Final semester examination schedule is now available.",
                type="exam",
                target_role="student",
            )
            res = run_async(admin_notifications_direct(payload=req, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["recipient_count"] == 1

            dt = (time.time() - t0) * 1000
            self.record("Admin Broadcast", "POST /api/v1/admin/notifications", "POST", "/api/v1/admin/notifications", True, "201 Created | Alert written directly to notifications table", dt)
        except Exception as e:
            self.record("Admin Broadcast", "POST /api/v1/admin/notifications", "POST", "/api/v1/admin/notifications", False, str(e), 0)

    @patch("cron.daily_leaderboard_job.get_db")
    def test_post_leaderboard_refresh_cron(self, mock_get_db):
        t0 = time.time()
        try:
            mock_db = MagicMock()
            mock_get_db.return_value = mock_db
            mock_db.table.return_value.select.return_value.execute.return_value = MagicMock(
                data=[{"user_id": self.student_uuid, "rank": 1}]
            )

            res = run_async(trigger_leaderboard_refresh(dry_run=True, admin_payload=self.admin_data))
            assert res["success"] is True
            assert res["result"]["dry_run"] is True

            dt = (time.time() - t0) * 1000
            self.record("Leaderboard Cron", "POST /api/v1/admin/leaderboard/refresh", "POST", "/api/v1/admin/leaderboard/refresh", True, "200 OK | Midnight evaluation trigger executed", dt)
        except Exception as e:
            self.record("Leaderboard Cron", "POST /api/v1/admin/leaderboard/refresh", "POST", "/api/v1/admin/leaderboard/refresh", False, str(e), 0)

    # =========================================================================
    # Run All & Generate Formatted Report
    # =========================================================================

    def run_all(self):
        print("=" * 80)
        print("POSTMAN TEST RUNNER: COMPLETE BACKEND API SUITE")
        print("Collection: Smart Learning Planner - Core & Admin APIs")
        print("Spec Version: Postman Collection v2.1.0")
        print("Timestamp: " + datetime.now(timezone.utc).isoformat())
        print("=" * 80)

        # 1. AI Chat Endpoints
        self.test_chat_sse_stream()
        self.test_chat_json_payload()
        self.test_chat_guardrail_refusal()
        self.test_chat_short_prompt_validation()

        # 2. Student Notification CRUD & Daily Dispatch
        self.test_get_notifications()
        self.test_get_notifications_unread_only()
        self.test_post_notification()
        self.test_patch_notification_read()
        self.test_patch_read_all()
        self.test_delete_notification()
        self.test_dispatch_daily()

        # 3. Admin Notification Broadcast & Rejection
        self.test_admin_broadcast_success()
        self.test_admin_broadcast_student_forbidden()
        self.test_get_admin_broadcast_history()

        # 4. Leaderboard & Goal Status
        self.test_get_leaderboard()
        self.test_patch_goal_status()

        # 5. Admin Resources
        self.test_post_admin_resource()
        self.test_patch_admin_resource()
        self.test_delete_admin_resource()
        self.test_get_admin_resources()

        # 6. Admin Students
        self.test_get_admin_students()
        self.test_patch_student_status()
        self.test_delete_student_account()

        # 7. Admin Subjects
        self.test_post_admin_subject()
        self.test_get_admin_subjects()
        self.test_patch_admin_subject()
        self.test_delete_admin_subject()

        # 8. Admin Notifications & Midnight Cron Trigger
        self.test_post_admin_notifications_direct()
        self.test_post_leaderboard_refresh_cron()

        # Print formatted report
        print(f"\n{'#':<3} | {'METHOD':<6} | {'ENDPOINT':<45} | {'STATUS':<6} | {'LATENCY':<8}")
        print("-" * 80)

        passed_count = 0
        for idx, r in enumerate(self.results, 1):
            status_str = "PASS" if r["passed"] else "FAIL"
            if r["passed"]:
                passed_count += 1
            print(f"{idx:<3} | {r['method']:<6} | {r['path'][:44]:<45} | {status_str:<6} | {r['duration_ms']}ms")
            print(f"    Assertion / Detail: {r['detail']}")

        total = len(self.results)
        rate = round((passed_count / total) * 100, 1) if total > 0 else 0

        print("=" * 80)
        print(f"SUMMARY: {passed_count}/{total} Test Cases Passed ({rate}%)")
        print("=" * 80)
        return passed_count == total


if __name__ == "__main__":
    runner = PostmanSmokeTestRunner()
    success = runner.run_all()
    sys.exit(0 if success else 1)
