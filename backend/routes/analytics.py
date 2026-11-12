import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status

from auth import require_admin, require_student
from database import get_db
from schemas.leaderboard import UpdateGoalStatusRequest
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
                .select("id, is_completed, completed_at")
                .eq("user_id", uid)
                .execute()
            )
            student_tasks = task_res.data or []
            tot_tasks = len(student_tasks)
            comp_tasks = sum(1 for t in student_tasks if t.get("is_completed") or (t.get("completed_at") is not None))
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


@router.get("/leaderboard")
async def get_student_leaderboard_endpoint(
    limit: int = 50,
    offset: int = 0,
    semester: Optional[int] = None,
    user_payload: dict = Depends(require_student),
):
    """
    Returns the student leaderboard ranking peers by study hours, completion rates, and goal status.
    Uses Supabase RPC 'get_student_leaderboard' with automatic SQL/Python aggregation fallback.
    Accessible by: 'student' or 'admin' roles.
    """
    clerk_id = user_payload.get("sub")
    limit = max(1, min(limit, 100))
    offset = max(0, offset)

    try:
        db = get_db()
        current_user_id = None
        if clerk_id:
            user_lookup = (
                db.table("users")
                .select("id")
                .eq("clerk_id", clerk_id)
                .limit(1)
                .execute()
            )
            if user_lookup.data:
                current_user_id = str(user_lookup.data[0]["id"])

        leaderboard_data = None
        # Attempt to invoke the optimized Supabase RPC stored procedure
        try:
            rpc_res = db.rpc(
                "get_student_leaderboard",
                {
                    "p_limit": limit,
                    "p_offset": offset,
                    "p_semester": semester,
                },
            ).execute()
            if rpc_res.data is not None:
                leaderboard_data = rpc_res.data
        except Exception as rpc_err:
            logger.info("Leaderboard RPC unavailable, falling back to application aggregation: %s", rpc_err)
            leaderboard_data = None

        if leaderboard_data is None:
            # Fallback: Query tables directly and perform aggregation
            users_query = db.table("users").select("id, email, role").eq("role", "student")
            users_res = users_query.execute()
            student_users = users_res.data or []

            raw_entries = []
            for u in student_users:
                uid = str(u["id"])
                email = u.get("email", "")

                # Mask email for privacy (e.g. joh***@skit.ac.in)
                if "@" in email:
                    parts = email.split("@")
                    local = parts[0]
                    domain = parts[1]
                    display_name = f"{local[:3]}***@{domain}" if len(local) > 3 else f"{local[:1]}***@{domain}"
                else:
                    display_name = "Student***"

                prof_res = (
                    db.table("student_profiles")
                    .select("semester, study_hours_per_day, goals, goal_status")
                    .eq("user_id", uid)
                    .limit(1)
                    .execute()
                )
                prof = prof_res.data[0] if prof_res.data else {}
                student_semester = prof.get("semester", 1)

                if semester is not None and student_semester != semester:
                    continue

                task_res = (
                    db.table("tasks")
                    .select("id, description, is_completed")
                    .eq("user_id", uid)
                    .execute()
                )
                tasks = task_res.data or []

                total_tasks = len(tasks)
                completed_tasks = 0
                planned_hours = 0.0
                actual_hours = 0.0

                for t in tasks:
                    desc = t.get("description") or ""
                    is_done = bool(t.get("is_completed")) or (t.get("completed_at") is not None)

                    duration = 1.0
                    if "Duration:" in desc:
                        try:
                            parts = desc.split("Duration:")[1].split("hours")[0].strip()
                            duration = float(parts)
                        except Exception:
                            duration = 1.0

                    planned_hours += duration
                    if is_done:
                        completed_tasks += 1
                        actual_hours += duration

                completion_rate = (
                    round((completed_tasks / total_tasks) * 100, 1)
                    if total_tasks > 0
                    else 0.0
                )

                stored_goal_status = prof.get("goal_status") or "on_track"

                if total_tasks == 0:
                    calculated_goal_status = "not_started"
                elif completion_rate >= 80.0:
                    calculated_goal_status = "ahead"
                elif completion_rate >= 50.0:
                    calculated_goal_status = "on_track"
                else:
                    calculated_goal_status = "behind"

                raw_entries.append({
                    "user_id": uid,
                    "display_name": display_name,
                    "semester": student_semester,
                    "target_hours_per_day": round(float(prof.get("study_hours_per_day", 2.0)), 1),
                    "goal_status": stored_goal_status,
                    "calculated_goal_status": calculated_goal_status,
                    "primary_goals": prof.get("goals", []),
                    "total_tasks": total_tasks,
                    "completed_tasks": completed_tasks,
                    "planned_study_hours": round(planned_hours, 1),
                    "actual_study_hours": round(actual_hours, 1),
                    "completion_rate": completion_rate,
                })

            # Sort: 1. actual_study_hours DESC, 2. completion_rate DESC, 3. completed_tasks DESC
            raw_entries.sort(
                key=lambda x: (x["actual_study_hours"], x["completion_rate"], x["completed_tasks"]),
                reverse=True,
            )

            # Assign Dense Rank
            current_rank = 1
            for i, entry in enumerate(raw_entries):
                if i > 0:
                    prev = raw_entries[i - 1]
                    if (
                        entry["actual_study_hours"],
                        entry["completion_rate"],
                        entry["completed_tasks"],
                    ) != (
                        prev["actual_study_hours"],
                        prev["completion_rate"],
                        prev["completed_tasks"],
                    ):
                        current_rank += 1
                entry["rank"] = current_rank

            total_count = len(raw_entries)
            paginated_entries = raw_entries[offset : offset + limit]
            leaderboard_data = paginated_entries
            all_entries_for_lookup = raw_entries
        else:
            total_count = len(leaderboard_data)
            all_entries_for_lookup = leaderboard_data

        # Locate current user standing
        current_user_rank = None
        if current_user_id:
            for entry in all_entries_for_lookup:
                if str(entry.get("user_id")) == current_user_id:
                    current_user_rank = entry
                    break

        return {
            "success": True,
            "total_students": total_count,
            "semester_filter": semester,
            "leaderboard": leaderboard_data,
            "current_user_rank": current_user_rank,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve student leaderboard")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate leaderboard aggregation",
        ) from exc


@router.patch("/goal-status")
async def update_student_goal_status_endpoint(
    payload: UpdateGoalStatusRequest,
    user_payload: dict = Depends(require_student),
):
    """
    Updates the authenticated student's persistent goal_status column in student_profiles.
    """
    clerk_id = user_payload.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

    try:
        db = get_db()

        # Resolve internal user UUID
        user_res = (
            db.table("users")
            .select("id")
            .eq("clerk_id", clerk_id)
            .limit(1)
            .execute()
        )
        if not user_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found",
            )

        user_id = str(user_res.data[0]["id"])

        db.table("student_profiles").update(
            {"goal_status": payload.goal_status}
        ).eq("user_id", user_id).execute()

        return {
            "success": True,
            "user_id": user_id,
            "goal_status": payload.goal_status,
            "message": "Goal status updated successfully",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update student goal status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update goal status",
        ) from exc
