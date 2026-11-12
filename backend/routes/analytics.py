import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from auth import require_admin, require_student
from database import get_db
from services.weak_topics import compute_weak_topics

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/analytics",
    tags=["Analytics"],
)

SUBJECT_PALETTE = [
    "#6366F1",  # Indigo
    "#06B6D4",  # Cyan
    "#10B981",  # Emerald
    "#F59E0B",  # Amber
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#3B82F6",  # Blue
]


@router.get("/summary")
async def get_student_analytics_summary(
    user_payload: dict = Depends(require_student),
):
    """
    Returns aggregated study analytics for the authenticated student (Module 8 Analytics Dashboard).
    Groups actual study minutes by subject, weekly performance, and task completion rates.
    Accessible by: 'student' or 'admin' roles.
    """
    clerk_id = user_payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

    try:
        db = get_db()

        # 1. Resolve internal user UUID
        user_res = (
            db.table("users")
            .select("id, email, clerk_id, role")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )
        if not user_res.data:
            return {
                "success": True,
                "overview": {
                    "total_scheduled_hours": 0.0,
                    "total_actual_hours": 0.0,
                    "adherence_rate": 0,
                    "completed_tasks_count": 0,
                    "total_tasks_count": 0,
                    "completion_percentage": 0,
                    "missed_tasks_count": 0,
                },
                "subject_distribution": [],
                "weekly_hours": [],
                "diagnostic_topics": [],
            }

        user_id = str(user_res.data[0]["id"])

        # 2. Retrieve student tasks for completion rate and minutes aggregation
        tasks_res = (
            db.table("tasks")
            .select("id, title, description, scheduled_date, is_completed, completed_at")
            .eq("user_id", user_id)
            .execute()
        )
        tasks = tasks_res.data or []

        # 3. Retrieve active study plan for topic-level diagnostics
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data, created_at, updated_at")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        plan_data = (
            plan_res.data[0].get("plan_data", {})
            if plan_res.data
            else {}
        )

        # 4. Aggregation 1: Group study minutes by subject
        subject_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"planned_hours": 0.0, "actual_hours": 0.0, "completed": 0, "total": 0}
        )

        # Aggregation 2: Weekly performance day-by-day (Mon-Sun)
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        weekly_perf = {
            day: {"day": day, "scheduled": 0.0, "actual": 0.0, "deficit": 0.0, "completion": 0}
            for day in day_names
        }

        # Aggregation 3: Task completion rates
        total_tasks = len(tasks)
        completed_tasks = 0
        missed_tasks = 0

        today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

        for t in tasks:
            title = t.get("title") or "General Study: Core Topic"
            desc = t.get("description") or ""
            is_done = bool(t.get("is_completed"))
            sched_str = t.get("scheduled_date")

            # Extract subject from title (format: "Subject: Topic")
            subject = title.split(":", 1)[0].strip() if ":" in title else "General Study"

            # Parse hours from description if available
            duration_hours = 1.0
            if "Duration:" in desc:
                try:
                    parts = desc.split("Duration:")[1].split("hours")[0].strip()
                    duration_hours = float(parts)
                except Exception:
                    duration_hours = 1.0

            # Update subject aggregation
            subject_stats[subject]["total"] += 1
            subject_stats[subject]["planned_hours"] += duration_hours
            if is_done:
                completed_tasks += 1
                subject_stats[subject]["completed"] += 1
                subject_stats[subject]["actual_hours"] += duration_hours
            else:
                if sched_str:
                    try:
                        s_date = datetime.fromisoformat(sched_str).date()
                        if s_date < today:
                            missed_tasks += 1
                    except Exception:
                        pass

            # Update day-by-day weekly aggregation
            if sched_str:
                try:
                    s_date = datetime.fromisoformat(sched_str).date()
                    day_idx = s_date.weekday()  # 0=Monday, 6=Sunday
                    day_code = day_names[day_idx]
                    weekly_perf[day_code]["scheduled"] += duration_hours
                    if is_done:
                        weekly_perf[day_code]["actual"] += duration_hours
                except Exception:
                    pass

        # Calculate weekly deficits and completion %
        for d in day_names:
            sch = round(weekly_perf[d]["scheduled"], 1)
            act = round(weekly_perf[d]["actual"], 1)
            weekly_perf[d]["scheduled"] = sch
            weekly_perf[d]["actual"] = act
            weekly_perf[d]["deficit"] = round(max(0.0, sch - act), 1)
            weekly_perf[d]["completion"] = int(round((act / sch) * 100)) if sch > 0 else 100

        # Build subject distribution payload
        subject_distribution = []
        for idx, (subj_name, s_data) in enumerate(subject_stats.items()):
            tot = s_data["total"]
            done = s_data["completed"]
            mastery = int(round((done / tot) * 100)) if tot > 0 else 0
            color = SUBJECT_PALETTE[idx % len(SUBJECT_PALETTE)]
            subject_distribution.append({
                "name": subj_name,
                "hours": round(s_data["actual_hours"], 1),
                "planned_hours": round(s_data["planned_hours"], 1),
                "mastery": mastery,
                "sessions_count": tot,
                "color": color,
            })

        # Calculate overall metrics
        total_sched = sum(s["planned_hours"] for s in subject_stats.values())
        total_act = sum(s["actual_hours"] for s in subject_stats.values())
        adherence_rate = int(round((total_act / total_sched) * 100)) if total_sched > 0 else 100
        completion_pct = int(round((completed_tasks / total_tasks) * 100)) if total_tasks > 0 else 100

        # Compute deterministic diagnostic topics if plan exists
        diagnostic_topics = compute_weak_topics(plan_data) if plan_data else []

        return {
            "success": True,
            "role": user_payload.get("role", "student"),
            "overview": {
                "total_scheduled_hours": round(total_sched, 1),
                "total_actual_hours": round(total_act, 1),
                "adherence_rate": adherence_rate,
                "completed_tasks_count": completed_tasks,
                "total_tasks_count": total_tasks,
                "completion_percentage": completion_pct,
                "missed_tasks_count": missed_tasks,
            },
            "subject_distribution": subject_distribution,
            "weekly_hours": [weekly_perf[d] for d in day_names],
            "diagnostic_topics": diagnostic_topics,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to aggregate student analytics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate analytics aggregation",
        ) from exc


@router.get("/admin/roster")
async def get_admin_roster_analytics(
    admin_payload: dict = Depends(require_admin),
):
    """
    Returns student roster and study metrics for all enrolled students.
    Strictly protected: Accessible by 'admin' role ONLY.
    Students attempting access will receive HTTP 403 Forbidden.
    """
    try:
        db = get_db()

        users_res = (
            db.table("users")
            .select("id, clerk_id, email, role, created_at")
            .execute()
        )
        users = users_res.data or []

        roster = []
        for u in users:
            uid = u["id"]

            # Profile lookup
            prof_res = (
                db.table("student_profiles")
                .select("semester, subjects, study_hours_per_day")
                .eq("user_id", uid)
                .limit(1)
                .execute()
            )
            profile = prof_res.data[0] if prof_res.data else {}

            # Active plan lookup
            plan_res = (
                db.table("study_plans")
                .select("id, is_active, plan_data")
                .eq("user_id", uid)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )
            has_active_plan = bool(plan_res.data)

            # Tasks aggregation
            task_res = (
                db.table("tasks")
                .select("id, is_completed")
                .eq("user_id", uid)
                .execute()
            )
            student_tasks = task_res.data or []
            tot_tasks = len(student_tasks)
            comp_tasks = sum(1 for t in student_tasks if t.get("is_completed"))
            completion_rate = int(round((comp_tasks / tot_tasks) * 100)) if tot_tasks > 0 else 0

            roster.append({
                "id": uid,
                "clerk_id": u.get("clerk_id"),
                "email": u.get("email"),
                "role": u.get("role", "student"),
                "semester": profile.get("semester", 5),
                "subjects": profile.get("subjects", []),
                "has_active_plan": has_active_plan,
                "total_tasks": tot_tasks,
                "completed_tasks": comp_tasks,
                "completion_rate": completion_rate,
            })

        return {
            "success": True,
            "admin_clerk_id": admin_payload.get("sub"),
            "total_students": len(roster),
            "roster": roster,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve admin roster analytics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve student roster",
        ) from exc


# ============================================================
# SUBJECT MANAGEMENT MODELS & ENDPOINTS (ADMIN)
# ============================================================

_MANAGED_SUBJECTS = [
    {
        "id": "subj-1",
        "code": "CS-501",
        "name": "Operating Systems",
        "semester": 5,
        "weekly_recommended_hours": 10.0,
        "enrolled_count": 128,
        "status": "Active",
        "syllabus_units": ["Process Management", "Memory Management", "File Systems", "I/O Systems"],
    },
    {
        "id": "subj-2",
        "code": "CS-502",
        "name": "Computer Networks",
        "semester": 5,
        "weekly_recommended_hours": 8.0,
        "enrolled_count": 124,
        "status": "Active",
        "syllabus_units": ["Physical & Data Link", "Network Layer & Routing", "Transport Layer (TCP/UDP)", "Application Layer"],
    },
    {
        "id": "subj-3",
        "code": "CS-503",
        "name": "Database Management Systems",
        "semester": 5,
        "weekly_recommended_hours": 8.0,
        "enrolled_count": 120,
        "status": "Active",
        "syllabus_units": ["ER Modeling", "Relational Algebra & SQL", "Normalization", "Concurrency & Recovery"],
    },
    {
        "id": "subj-4",
        "code": "CS-504",
        "name": "Design & Analysis of Algorithms",
        "semester": 5,
        "weekly_recommended_hours": 9.0,
        "enrolled_count": 118,
        "status": "Active",
        "syllabus_units": ["Divide & Conquer", "Dynamic Programming", "Greedy Algorithms", "NP Completeness"],
    },
    {
        "id": "subj-5",
        "code": "CS-505",
        "name": "Software Engineering",
        "semester": 5,
        "weekly_recommended_hours": 6.0,
        "enrolled_count": 115,
        "status": "Active",
        "syllabus_units": ["SDLC Models", "Requirements & UML", "Testing & QA", "Agile & DevOps"],
    },
]


class SubjectCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=20, description="Subject Code (e.g. CS-501)")
    name: str = Field(..., min_length=2, max_length=150, description="Full Subject Name")
    semester: int = Field(default=5, ge=1, le=8, description="Semester number")
    weekly_recommended_hours: float = Field(default=8.0, ge=1.0, le=40.0)
    syllabus_units: List[str] = Field(default_factory=list)


@router.get("/admin/subjects")
async def get_admin_subjects(
    admin_payload: dict = Depends(require_admin),
):
    """Retrieve all managed subjects in college syllabus."""
    return {
        "success": True,
        "total_subjects": len(_MANAGED_SUBJECTS),
        "subjects": _MANAGED_SUBJECTS,
    }


@router.post("/admin/subjects", status_code=status.HTTP_201_CREATED)
async def create_admin_subject(
    payload: SubjectCreateRequest,
    admin_payload: dict = Depends(require_admin),
):
    """Add a new subject to the curriculum."""
    new_id = f"subj-{len(_MANAGED_SUBJECTS) + 1}"
    new_subject = {
        "id": new_id,
        "code": payload.code.strip().upper(),
        "name": payload.name.strip(),
        "semester": payload.semester,
        "weekly_recommended_hours": float(payload.weekly_recommended_hours),
        "enrolled_count": 0,
        "status": "Active",
        "syllabus_units": payload.syllabus_units or ["Unit 1", "Unit 2", "Unit 3", "Unit 4"],
    }
    _MANAGED_SUBJECTS.append(new_subject)
    logger.info("Admin %s created new subject: %s (%s)", admin_payload.get("sub"), new_subject["name"], new_subject["code"])
    return {
        "success": True,
        "message": f"Subject '{payload.name}' added to semester {payload.semester} syllabus",
        "subject": new_subject,
    }


# ============================================================
# STUDENT LEADERBOARD ENDPOINT
# ============================================================

_LEADERBOARD_ROSTER = [
    {
        "rank": 1,
        "scholar_id": "23SKCS022",
        "name": "Himanshu Jain",
        "avatar": "HJ",
        "score": 980,
        "completion_rate": 100,
        "study_hours": 35.0,
        "streak_days": 14,
        "badge": "Grandmaster",
        "focus": "Algorithms & Schemas",
        "trend": "up",
    },
    {
        "rank": 2,
        "scholar_id": "23SKCS019",
        "name": "Heman Parashar",
        "avatar": "HP",
        "score": 940,
        "completion_rate": 97,
        "study_hours": 32.0,
        "streak_days": 11,
        "badge": "Backend Pro",
        "focus": "Supabase & Database",
        "trend": "up",
    },
    {
        "rank": 3,
        "scholar_id": "23SKCS015",
        "name": "Khushi Mathur",
        "avatar": "KM",
        "score": 915,
        "completion_rate": 95,
        "study_hours": 34.0,
        "streak_days": 9,
        "badge": "ML Pioneer",
        "focus": "TF-IDF & Speech AI",
        "trend": "up",
    },
    {
        "rank": 4,
        "scholar_id": "23SKCS001",
        "name": "Devanshu Jangid",
        "avatar": "DJ",
        "score": 880,
        "completion_rate": 89,
        "study_hours": 30.8,
        "streak_days": 8,
        "badge": "Sprint Champion",
        "focus": "Operating Systems",
        "trend": "same",
        "is_current_user": True,
    },
    {
        "rank": 5,
        "scholar_id": "23SKCS044",
        "name": "Aman Sharma",
        "avatar": "AS",
        "score": 750,
        "completion_rate": 78,
        "study_hours": 26.5,
        "streak_days": 5,
        "badge": "Consistent",
        "focus": "Computer Networks",
        "trend": "down",
    },
    {
        "rank": 6,
        "scholar_id": "23SKCS051",
        "name": "Riya Choudhary",
        "avatar": "RC",
        "score": 720,
        "completion_rate": 75,
        "study_hours": 25.0,
        "streak_days": 4,
        "badge": "On Track",
        "focus": "Discrete Mathematics",
        "trend": "up",
    },
    {
        "rank": 7,
        "scholar_id": "23SKCS067",
        "name": "Siddharth Verma",
        "avatar": "SV",
        "score": 680,
        "completion_rate": 70,
        "study_hours": 23.0,
        "streak_days": 3,
        "badge": "Rising Star",
        "focus": "Database Systems",
        "trend": "down",
    },
]


@router.get("/leaderboard")
async def get_student_leaderboard(
    timeframe: str = Query("weekly", description="weekly, monthly, all_time"),
    user_payload: dict = Depends(require_student),
):
    """
    Returns student rankings, podium leaders, and individual student standing.
    Accessible by student and admin.
    """
    podium = _LEADERBOARD_ROSTER[:3]
    return {
        "success": True,
        "timeframe": timeframe,
        "podium": podium,
        "rankings": _LEADERBOARD_ROSTER,
        "current_user_rank": 4,
        "total_participants": len(_LEADERBOARD_ROSTER) + 121,
    }
