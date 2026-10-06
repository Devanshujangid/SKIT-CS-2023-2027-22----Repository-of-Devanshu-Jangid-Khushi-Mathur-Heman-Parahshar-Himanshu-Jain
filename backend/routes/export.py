from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from auth import verify_clerk_token
from database import get_db


router = APIRouter(
    prefix="/api/v1/plans",
    tags=["Plan Export"]
)


DAY_INDEX = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def escape_ics_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


@router.get("/export/ics")
async def export_ics(
    user_data: dict = Depends(verify_clerk_token)
):
    clerk_id = user_data.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token"
        )

    try:
        db = get_db()

        # Find internal user UUID using Clerk ID
        user_res = (
            db.table("users")
            .select("id")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )

        if not user_res.data:
            raise HTTPException(
                status_code=404,
                detail="User not found"
            )

        user_id = user_res.data[0]["id"]

        # Fetch latest active study plan
        plans_res = (
            db.table("study_plans")
            .select("plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not plans_res.data:
            raise HTTPException(
                status_code=404,
                detail="No active study plan found"
            )

        plan_data = plans_res.data[0]["plan_data"]
        weekly_schedule = plan_data.get("weekly_schedule", [])

        if not weekly_schedule:
            raise HTTPException(
                status_code=404,
                detail="Weekly schedule not found in study plan"
            )

        # Start from the current week's Monday
        today = datetime.now(timezone.utc).date()
        monday = today - timedelta(days=today.weekday())

        ics_events = []

        for day_data in weekly_schedule:
            day_name = day_data.get("day")
            day_offset = DAY_INDEX.get(day_name)

            if day_offset is None:
                continue

            event_date = monday + timedelta(days=day_offset)

            for session in day_data.get("sessions", []):
                start_time = session.get("start_time")
                end_time = session.get("end_time")

                if not start_time or not end_time:
                    continue

                start_dt = datetime.strptime(
                    f"{event_date} {start_time}",
                    "%Y-%m-%d %H:%M"
                )

                end_dt = datetime.strptime(
                    f"{event_date} {end_time}",
                    "%Y-%m-%d %H:%M"
                )

                # Handle sessions crossing midnight
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)

                uid = (
                    f"{user_id}-{event_date}-"
                    f"{start_time}-{session.get('topic', 'study')}"
                )

                subject = escape_ics_text(
                    session.get("subject", "Study")
                )

                topic = escape_ics_text(
                    session.get("topic", "Study Session")
                )

                priority = escape_ics_text(
                    session.get("priority", "medium")
                )

                activity_type = escape_ics_text(
                    session.get("activity_type", "study")
                )

                ics_events.append(
                    "\n".join([
                        "BEGIN:VEVENT",
                        f"UID:{escape_ics_text(uid)}",
                        f"DTSTART:{start_dt.strftime('%Y%m%dT%H%M%S')}",
                        f"DTEND:{end_dt.strftime('%Y%m%dT%H%M%S')}",
                        f"SUMMARY:{subject} - {topic}",
                        (
                            f"DESCRIPTION:"
                            f"Activity: {activity_type}\\n"
                            f"Priority: {priority}"
                        ),
                        "END:VEVENT",
                    ])
                )

        if not ics_events:
            raise HTTPException(
                status_code=404,
                detail="No valid study sessions found"
            )

        calendar = "\n".join([
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Smart Learning Planner//Study Schedule//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            *ics_events,
            "END:VCALENDAR",
        ])

        return Response(
            content=calendar,
            media_type="text/calendar",
            headers={
                "Content-Disposition": (
                    'attachment; filename="smart-learning-plan.ics"'
                )
            },
        )

    except HTTPException:
        raise

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to export study plan: {exc}"
        )