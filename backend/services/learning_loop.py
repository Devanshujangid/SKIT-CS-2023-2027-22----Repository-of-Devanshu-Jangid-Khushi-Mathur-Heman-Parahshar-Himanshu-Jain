
import json
import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from database import get_db

logger = logging.getLogger(__name__)

IST = ZoneInfo("Asia/Kolkata")


def get_learning_loop_payload(clerk_id: str) -> dict:
    """Build a 7-day learning-history payload for Gemini."""

    today = datetime.now(IST).date()
    start_date = today - timedelta(days=6)

    db = get_db()

    # Resolve the authenticated user's internal database ID.
    user_result = (
        db.table("users")
        .select("id")
        .eq("clerk_id", clerk_id)
        .limit(1)
        .execute()
    )

    if not user_result.data:
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": today.isoformat(),
            },
            "completed_tasks": [],
            "missed_sessions": [],
            "summary": {
                "completed_count": 0,
                "missed_count": 0,
            },
        }

    user_id = user_result.data[0]["id"]

    tasks = []
    try:
        # Fetch tasks scheduled during the last 7 calendar days.
        result = (
            db.table("tasks")
            .select(
                "id, title, description, is_completed, "
                "completed_at, scheduled_date"
            )
            .eq("user_id", user_id)
            .gte("scheduled_date", start_date.isoformat())
            .lte("scheduled_date", today.isoformat())
            .execute()
        )
        tasks = result.data or []
    except Exception as exc:
        logger.warning(
            "Could not query tasks by scheduled_date: %s. Using empty task history.",
            exc,
        )
        tasks = []

    completed_tasks = []
    missed_sessions = []

    for task in tasks:
        scheduled_date = task.get("scheduled_date")
        is_completed = task.get("is_completed", False)

        if is_completed:
            completed_tasks.append({
                "title": task.get("title"),
                "description": task.get("description"),
                "scheduled_date": scheduled_date,
                "completed_at": task.get("completed_at"),
            })

        elif scheduled_date and date.fromisoformat(scheduled_date) < today:
            missed_sessions.append({
                "title": task.get("title"),
                "description": task.get("description"),
                "scheduled_date": scheduled_date,
            })

    payload = {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
        },
        "completed_tasks": completed_tasks,
        "missed_sessions": missed_sessions,
        "summary": {
            "completed_count": len(completed_tasks),
            "missed_count": len(missed_sessions),
        },
    }

    logger.info(
        "Learning history prepared: %s completed, %s missed",
        len(completed_tasks),
        len(missed_sessions),
    )

    return payload


def get_learning_loop_json(clerk_id: str) -> str:
    """Return the learning-history payload as JSON for Gemini."""
    return json.dumps(
        get_learning_loop_payload(clerk_id),
        ensure_ascii=False,
        indent=2,
    )
