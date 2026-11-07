"""
Automated Notification Engine.

Evaluates student study plans, pending tasks, and execution metrics to push
real-time and daily automated alerts into the notifications table:
1. "Unresolved Weak Topics": Flagged via deterministic WeakTopicsService
   (sessions with study deficits, low completion rates, or high severity).
2. "Upcoming Exams": Detected from monthly milestones, scheduled review quizzes,
   and upcoming assessment tasks.

Enforces strict idempotency and deduplication to prevent alert fatigue.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from services.weak_topics import compute_weak_topics

logger = logging.getLogger(__name__)

EXAM_KEYWORDS = (
    "exam",
    "midterm",
    "test",
    "quiz",
    "assessment",
    "gate",
    "final",
    "revision benchmark",
    "evaluation",
)


class NotificationEngine:
    """
    Automated notification engine for generating deterministic study alerts.
    """

    @staticmethod
    def is_duplicate(
        existing_notifications: List[Dict[str, Any]],
        alert_type: str,
        title: str,
        lookback_hours: int = 24,
    ) -> bool:
        """
        Returns True if a notification with matching type and title was dispatched
        recently (within lookback_hours) or is currently unread.
        """
        now = datetime.now(timezone.utc)
        normalized_title = title.strip().lower()

        for notif in existing_notifications:
            if notif.get("type") != alert_type:
                continue

            existing_title = (notif.get("title") or "").strip().lower()
            if existing_title != normalized_title:
                continue

            # If student has not read the prior notification, do not spam with duplicates
            if not notif.get("is_read", False):
                return True

            # Check timestamp window
            created_at_raw = notif.get("created_at")
            if created_at_raw:
                try:
                    if isinstance(created_at_raw, str):
                        # Support ISO formats with or without Z
                        clean_iso = created_at_raw.replace("Z", "+00:00")
                        created_dt = datetime.fromisoformat(clean_iso)
                    elif isinstance(created_at_raw, datetime):
                        created_dt = created_at_raw
                    else:
                        created_dt = now

                    if created_dt.tzinfo is None:
                        created_dt = created_dt.replace(tzinfo=timezone.utc)

                    if (now - created_dt).total_seconds() < (lookback_hours * 3600):
                        return True
                except Exception:
                    # On parse error, assume duplicate if unread
                    pass

        return False

    @classmethod
    def detect_unresolved_weak_topics(
        cls,
        user_id: str,
        plan_data: Dict[str, Any],
        existing_notifications: Optional[List[Dict[str, Any]]] = None,
        max_alerts: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates active study plan for unresolved weak topics requiring intervention.
        """
        if not plan_data:
            return []

        existing = existing_notifications or []
        try:
            weak_topics = compute_weak_topics(plan_data=plan_data)
        except Exception:
            logger.warning("Could not compute weak topics for student %s", user_id)
            return []

        alerts: List[Dict[str, Any]] = []

        for item in weak_topics:
            if item.get("status") != "Needs Revision":
                continue

            subject = item.get("subject", "General Subject")
            topic = item.get("topic", "Core Topic")
            deficit = item.get("missed_minutes", 0)
            severity = item.get("severity", "medium").upper()

            title = f"Unresolved Weak Topic: {subject}"
            if cls.is_duplicate(existing, "weak_topic", title):
                continue

            message = (
                f"[{severity} PRIORITY] You have a {deficit}m study deficit in '{topic}'. "
                f"Review your study schedule or initiate an adaptive plan rebalance."
            )

            alerts.append({
                "user_id": user_id,
                "type": "weak_topic",
                "title": title,
                "message": message,
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

            if len(alerts) >= max_alerts:
                break

        return alerts

    @classmethod
    def detect_upcoming_exams(
        cls,
        user_id: str,
        plan_data: Dict[str, Any],
        tasks: Optional[List[Dict[str, Any]]] = None,
        existing_notifications: Optional[List[Dict[str, Any]]] = None,
        max_alerts: int = 2,
    ) -> List[Dict[str, Any]]:
        """
        Detects upcoming exam milestones and high-priority assessments within study plans and tasks.
        """
        existing = existing_notifications or []
        alerts: List[Dict[str, Any]] = []
        today = date.today()

        # 1. Inspect Monthly Milestones
        milestones = (plan_data or {}).get("monthly_milestones", [])
        for m in milestones:
            milestone_desc = (m.get("milestone") or "").strip()
            deliverable = (m.get("key_deliverable") or "").strip()
            text_to_check = f"{milestone_desc} {deliverable}".lower()

            if any(k in text_to_check for k in EXAM_KEYWORDS):
                week_num = m.get("week", 1)
                title = f"Upcoming Exam Milestone: Week {week_num}"

                if not cls.is_duplicate(existing, "exam", title):
                    message = (
                        f"Milestone: '{milestone_desc}'. "
                        f"Target deliverable: '{deliverable}'. Review prerequisite revision sessions."
                    )
                    alerts.append({
                        "user_id": user_id,
                        "type": "exam",
                        "title": title,
                        "message": message,
                        "is_read": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    })

                    if len(alerts) >= max_alerts:
                        return alerts

        # 2. Inspect Tasks Scheduled in the next 7 days
        for task in (tasks or []):
            if task.get("is_completed", False):
                continue

            scheduled_date_raw = task.get("scheduled_date")
            if not scheduled_date_raw:
                continue

            try:
                if isinstance(scheduled_date_raw, str):
                    task_date = date.fromisoformat(scheduled_date_raw)
                elif isinstance(scheduled_date_raw, date):
                    task_date = scheduled_date_raw
                else:
                    continue
            except Exception:
                continue

            days_until = (task_date - today).days
            if 0 <= days_until <= 7:
                task_title = task.get("title", "")
                task_desc = task.get("description", "")
                combined = f"{task_title} {task_desc}".lower()

                if any(k in combined for k in EXAM_KEYWORDS):
                    title = f"Upcoming Assessment in {days_until} Day{'s' if days_until != 1 else ''}"
                    if not cls.is_duplicate(existing, "exam", title):
                        message = (
                            f"Assessment '{task_title}' is scheduled for {task_date.isoformat()}. "
                            "Ensure your topic reviews and practice sets are completed."
                        )
                        alerts.append({
                            "user_id": user_id,
                            "type": "exam",
                            "title": title,
                            "message": message,
                            "is_read": False,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                        })

                        if len(alerts) >= max_alerts:
                            break

        return alerts

    @classmethod
    def dispatch_for_student(
        cls,
        user_id: str,
        db: Any,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Dispatches all candidate notifications for a single student.
        """
        # 1. Fetch student's existing recent notifications for deduplication
        existing_res = (
            db.table("notifications")
            .select("id, user_id, type, title, message, is_read, created_at")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(30)
            .execute()
        )
        existing_notifications = existing_res.data or []

        # 2. Fetch student's active study plan
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        plan_data = plan_res.data[0]["plan_data"] if plan_res.data else {}

        # 3. Fetch student's uncompleted tasks
        tasks_res = (
            db.table("tasks")
            .select("id, title, description, scheduled_date, is_completed")
            .eq("user_id", user_id)
            .eq("is_completed", False)
            .execute()
        )
        tasks = tasks_res.data or []

        # 4. Generate candidate alerts
        weak_topic_alerts = cls.detect_unresolved_weak_topics(
            user_id=user_id,
            plan_data=plan_data,
            existing_notifications=existing_notifications,
        )

        exam_alerts = cls.detect_upcoming_exams(
            user_id=user_id,
            plan_data=plan_data,
            tasks=tasks,
            existing_notifications=existing_notifications,
        )

        all_new_alerts = weak_topic_alerts + exam_alerts

        # 5. Insert newly generated alerts
        created_records = []
        if all_new_alerts and not dry_run:
            insert_res = (
                db.table("notifications")
                .insert(all_new_alerts)
                .execute()
            )
            created_records = insert_res.data or []
        elif dry_run:
            created_records = all_new_alerts

        return {
            "user_id": user_id,
            "weak_topic_alerts_count": len(weak_topic_alerts),
            "exam_alerts_count": len(exam_alerts),
            "total_created": len(created_records),
            "alerts": created_records,
        }

    @classmethod
    def run_daily_notification_dispatch(
        cls,
        db: Optional[Any] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Executes daily automated notification dispatch across all registered students.
        """
        if db is None:
            from database import get_db
            db = get_db()

        start_time = datetime.now(timezone.utc)
        logger.info("Starting Daily Automated Notification Dispatch (dry_run=%s)", dry_run)

        # Retrieve all student user IDs
        users_res = (
            db.table("users")
            .select("id, email, clerk_id, role")
            .execute()
        )
        users = users_res.data or []

        total_alerts_pushed = 0
        student_results = []

        for u in users:
            uid = str(u["id"])
            try:
                res = cls.dispatch_for_student(user_id=uid, db=db, dry_run=dry_run)
                total_alerts_pushed += res["total_created"]
                if res["total_created"] > 0:
                    student_results.append(res)
            except Exception:
                logger.exception("Failed to dispatch daily notifications for user: %s", uid)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            "Daily Notification Dispatch finished in %.2fs. Evaluated %d students, dispatched %d alerts.",
            duration,
            len(users),
            total_alerts_pushed,
        )

        return {
            "success": True,
            "dry_run": dry_run,
            "students_evaluated": len(users),
            "students_with_alerts": len(student_results),
            "total_notifications_dispatched": total_alerts_pushed,
            "execution_duration_seconds": round(duration, 3),
            "timestamp": start_time.isoformat(),
            "details": student_results,
        }


# Singleton instance
notification_engine = NotificationEngine()

