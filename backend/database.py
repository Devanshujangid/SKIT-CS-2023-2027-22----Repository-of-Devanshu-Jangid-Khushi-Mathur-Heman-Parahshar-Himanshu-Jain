import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.is_file():
    load_dotenv(dotenv_path=_env_path)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "") or os.getenv("SUPABASE_KEY", "")

# Check if a valid URL is provided; otherwise create a dummy/mock placeholder
supabase: Client = None

if SUPABASE_URL.startswith("http://") or SUPABASE_URL.startswith("https://"):
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        logger.warning("Could not initialize Supabase client: %s", e)
else:
    logger.warning("SUPABASE_URL is not configured with a valid HTTP/HTTPS URL. Running without active DB connection.")


def get_db() -> Client:
    if not supabase:
        raise RuntimeError("Database connection not initialized. Please configure SUPABASE_URL in .env")
    return supabase


def get_or_create_user(db: Client, clerk_id: str, email: str | None = None) -> str:
    """Return the internal UUID associated with a verified Clerk user, provisioning if not found."""
    if not clerk_id:
        raise ValueError("Clerk user ID is required")

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
        .insert({
            "clerk_id": clerk_id,
            "email": str(user_email),
            "role": "student",
        })
        .execute()
    )

    if not created.data:
        raise RuntimeError("Failed to provision new user")

    return str(created.data[0]["id"])


def upsert_study_plan(clerk_id: str, plan_data: dict, email: str | None = None):
    db = get_db()

    # Find or provision internal user UUID using Clerk ID
    user_id = get_or_create_user(db, clerk_id=clerk_id, email=email)

    now = datetime.now(timezone.utc).isoformat()

    # Insert or update the user's study plan
    response = (
        db.table("study_plans")
        .upsert(
            {
                "user_id": user_id,
                "plan_data": plan_data,
                "is_active": True,
                "updated_at": now,
            },
            on_conflict="user_id",
        )
        .execute()
    )

    return response.data


save_study_plan = upsert_study_plan


def save_plan_tasks(clerk_id: str, plan_data: dict):
    """Save generated weekly study sessions without duplicating existing tasks."""
    from datetime import date, datetime, timedelta
    from zoneinfo import ZoneInfo

    try:
        db = get_db()

        user_res = (
            db.table("users")
            .select("id")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )

        if not user_res.data:
            logger.warning("User not found while saving plan tasks for clerk_id: %s", clerk_id)
            return

        user_id = user_res.data[0]["id"]

        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
        monday = today - timedelta(days=today.weekday())

        weekly_schedule = plan_data.get("weekly_schedule", [])

        for day_index, day_data in enumerate(weekly_schedule):
            day_name = day_data.get("day", "")
            day_name = getattr(day_name, "value", day_name)

            scheduled_date = monday + timedelta(days=day_index)

            for session_index, session in enumerate(day_data.get("sessions", [])):
                subject = session.get("subject", "General Study")
                topic = session.get("topic", "Study Session")
                session_key = (
                    f"{monday.isoformat()}-"
                    f"{day_index}-{session_index}"
                )

                # Check if session already exists
                existing = None
                try:
                    res = (
                        db.table("tasks")
                        .select("id")
                        .eq("user_id", user_id)
                        .eq("plan_session_key", session_key)
                        .limit(1)
                        .execute()
                    )
                    existing = res.data
                except Exception:
                    pass

                if existing:
                    continue

                duration = session.get("duration_hours", 0)
                description = (
                    f"{topic} | Duration: {duration} hours"
                )

                try:
                    db.table("tasks").insert({
                        "user_id": user_id,
                        "title": f"{subject}: {topic}",
                        "description": description,
                        "scheduled_date": scheduled_date.isoformat(),
                        "plan_session_key": session_key,
                        "is_completed": False,
                    }).execute()
                except Exception as ins_exc:
                    # Fallback if scheduled_date or plan_session_key do not exist in the tasks table
                    logger.debug("Falling back to basic task insert without scheduled_date/plan_session_key: %s", ins_exc)
                    try:
                        db.table("tasks").insert({
                            "user_id": user_id,
                            "title": f"{subject}: {topic}",
                            "description": f"{description} | Date: {scheduled_date.isoformat()}",
                            "is_completed": False,
                        }).execute()
                    except Exception as fallback_exc:
                        logger.warning("Could not insert plan task: %s", fallback_exc)

    except Exception as exc:
        logger.warning("save_plan_tasks encountered an error: %s", exc)

