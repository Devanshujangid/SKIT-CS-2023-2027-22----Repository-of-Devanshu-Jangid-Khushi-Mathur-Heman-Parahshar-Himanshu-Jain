
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Load environment variables from backend/.env and the current environment.
_env_path = Path(__file__).resolve().parent / ".env"

if _env_path.is_file():
    load_dotenv(dotenv_path=_env_path)

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_KEY", "").strip()
)

# Initialize the Supabase client.
supabase: Client | None = None

if SUPABASE_URL.startswith(("http://", "https://")):
    if not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning(
            "Supabase URL is configured, but the service-role key is missing."
        )
    else:
        try:
            supabase = create_client(
                SUPABASE_URL,
                SUPABASE_SERVICE_ROLE_KEY,
            )
        except Exception:
            logger.exception("Could not initialize Supabase client.")
else:
    logger.warning(
        "SUPABASE_URL is not configured with a valid HTTP/HTTPS URL."
    )


def get_db() -> Client:
    """Return the initialized Supabase client."""
    if supabase is None:
        raise RuntimeError(
            "Database connection is not initialized. "
            "Check SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in backend/.env."
        )

    return supabase


def get_or_create_user(
    db: Client,
    clerk_id: str,
    email: str | None = None,
) -> str:
    """
    Return the internal UUID for a verified Clerk user.
    Create the user record if it does not already exist.
    """
    if not clerk_id:
        raise ValueError("Clerk user ID is required.")

    existing = (
        db.table("users")
        .select("id")
        .eq("clerk_id", clerk_id)
        .limit(1)
        .execute()
    )

    if existing.data:
        return str(existing.data[0]["id"])

    user_email = email or f"{clerk_id}@clerk.user"

    created = (
        db.table("users")
        .insert(
            {
                "clerk_id": clerk_id,
                "email": str(user_email),
                "role": "student",
            }
        )
        .execute()
    )

    if not created.data:
        raise RuntimeError("Failed to create the student user record.")

    return str(created.data[0]["id"])


def upsert_study_plan(
    clerk_id: str,
    plan_data: dict,
    email: str | None = None,
):
    """
    Create and activate a new study-plan version.

    Requires the PostgreSQL function:
        public.create_study_plan_version(p_user_id, p_plan_data)

    The database function handles the version insertion and activation
    in one transaction, preserving the previous active plan on failure.
    """
    if not isinstance(plan_data, dict):
        raise ValueError("plan_data must be a dictionary.")

    db = get_db()

    user_id = get_or_create_user(
        db,
        clerk_id=clerk_id,
        email=email,
    )

    response = (
        db.rpc(
            "create_study_plan_version",
            {
                "p_user_id": user_id,
                "p_plan_data": plan_data,
            },
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError(
            "The database did not return the newly saved study plan."
        )

    saved_plan = (
        response.data[0]
        if isinstance(response.data, list)
        else response.data
    )

    if not isinstance(saved_plan, dict) or not saved_plan.get("id"):
        raise RuntimeError(
            "The database returned an invalid study-plan record."
        )

    logger.info(
        "Created study-plan version %s for student %s",
        saved_plan["id"],
        user_id,
    )

    # Preserve the existing return convention: a list of returned rows.
    return response.data


# Keep existing imports and callers working.
save_study_plan = upsert_study_plan


def save_plan_tasks(
    clerk_id: str,
    plan_data: dict,
):
    """
    Save sessions from a study plan to the tasks table.

    Task keys include the active plan version ID so sessions from a
    newly generated plan are not mistaken for tasks from an older plan.
    Errors are logged; they do not silently overwrite study-plan history.
    """
    try:
        db = get_db()

        user_result = (
            db.table("users")
            .select("id")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )

        if not user_result.data:
            logger.warning(
                "User not found while saving plan tasks."
            )
            return

        user_id = str(user_result.data[0]["id"])

        # Get the active plan version so each version has its own task keys.
        active_result = (
            db.table("study_plans")
            .select("id")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if not active_result.data:
            logger.warning(
                "No active plan found; skipping task generation."
            )
            return

        plan_id = str(active_result.data[0]["id"])

        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        monday = today - timedelta(days=today.weekday())

        weekly_schedule = plan_data.get("weekly_schedule", [])

        if not isinstance(weekly_schedule, list):
            logger.warning("Invalid weekly_schedule format.")
            return

        for day_index, day_data in enumerate(weekly_schedule):
            if not isinstance(day_data, dict):
                continue

            scheduled_date = monday + timedelta(days=day_index)
            sessions = day_data.get("sessions", [])

            if not isinstance(sessions, list):
                continue

            for session_index, session in enumerate(sessions):
                if not isinstance(session, dict):
                    continue

                subject = session.get("subject") or "General Study"
                topic = session.get("topic") or "Study Session"

                # The version ID prevents a new plan's tasks from being
                # skipped because an older plan used the same day/index.
                session_key = (
                    f"{plan_id}-{monday.isoformat()}-"
                    f"{day_index}-{session_index}"
                )

                existing_result = (
                    db.table("tasks")
                    .select("id")
                    .eq("user_id", user_id)
                    .eq("plan_session_key", session_key)
                    .limit(1)
                    .execute()
                )

                if existing_result.data:
                    continue

                duration = session.get("duration_hours", 0)
                description = f"{topic} | Duration: {duration} hours"

                task_data = {
                    "user_id": user_id,
                    "title": f"{subject}: {topic}",
                    "description": description,
                    "scheduled_date": scheduled_date.isoformat(),
                    "plan_session_key": session_key,
                    "is_completed": False,
                }

                try:
                    db.table("tasks").insert(task_data).execute()
                except Exception:
                    logger.exception(
                        "Could not insert task for plan %s, session %s.",
                        plan_id,
                        session_key,
                    )

    except Exception:
        logger.exception("save_plan_tasks failed.")
