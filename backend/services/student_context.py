
import logging
from typing import Any, Dict

from database import get_db

logger = logging.getLogger(__name__)


def get_student_context(clerk_id: str) -> Dict[str, Any]:
    """
    Fetch verified student context for AI personalization.

    Missing leaderboard or goal-evaluation data is explicitly
    represented as unavailable. Never infer these values.
    """
    context = {
        "goals": [],
        "leaderboard_rank": None,
        "goal_status": "unknown",
    }

    if not clerk_id:
        return context

    try:
        db = get_db()

        if db is None:
            logger.warning("Student context unavailable: database not configured.")
            return context

        user_result = (
            db.table("users")
            .select("id")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )

        if not user_result.data:
            return context

        user_id = user_result.data[0]["id"]

        profile_result = (
            db.table("student_profiles")
            .select("goals")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if profile_result.data:
            goals = profile_result.data[0].get("goals") or []
            context["goals"] = goals if isinstance(goals, list) else []

    except Exception:
        logger.exception("Could not fetch student personalization context.")

    return context
