from datetime import datetime, timezone
import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from auth import verify_clerk_token
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/plans",
    tags=["Plans"],
)


def find_missed_tasks(plan_data: Dict[str, Any], current_day_idx: int = 2) -> List[Dict[str, Any]]:
    """
    Identifies missed tasks or deficit study sessions from weekly_schedule and task_executions.
    """
    missed: List[Dict[str, Any]] = []
    weekly_schedule = plan_data.get("weekly_schedule") or []
    completed_ids = set(plan_data.get("completed_task_ids") or [])
    executions = plan_data.get("task_executions") or {}

    for day_idx, day_item in enumerate(weekly_schedule, start=1):
        day_name = day_item.get("day", f"Day {day_idx}")
        sessions = day_item.get("sessions") or []

        for s_idx, sess in enumerate(sessions, start=1):
            sess_id = sess.get("id") or f"live-d{day_idx}-t{s_idx}"
            exec_info = executions.get(sess_id) or {}
            exec_status = exec_info.get("status")
            planned_mins = int((sess.get("duration_hours") or 1.0) * 60)
            actual_mins = exec_info.get("actual_minutes")

            # 1. Explicitly recorded as missed
            if exec_status == "missed":
                missed.append({
                    "id": sess_id,
                    "subject": sess.get("subject", "General"),
                    "topic": sess.get("topic", "Core Topic"),
                    "day": day_name,
                    "day_number": day_idx,
                    "planned_minutes": planned_mins,
                    "actual_minutes": 0,
                    "missed_minutes": planned_mins,
                    "reason": "Flagged as Missed",
                })
            # 2. Partially completed with substantial deficit
            elif exec_status == "partially_completed" and actual_mins is not None and actual_mins < planned_mins:
                deficit = planned_mins - actual_mins
                if deficit >= 15:
                    missed.append({
                        "id": sess_id,
                        "subject": sess.get("subject", "General"),
                        "topic": sess.get("topic", "Core Topic"),
                        "day": day_name,
                        "day_number": day_idx,
                        "planned_minutes": planned_mins,
                        "actual_minutes": actual_mins,
                        "missed_minutes": deficit,
                        "reason": f"Partial deficit (-{deficit}m)",
                    })
            # 3. Previous day session not completed and not rebalanced
            elif day_idx < current_day_idx and sess_id not in completed_ids and exec_status not in ["completed", "rebalanced"]:
                missed.append({
                    "id": sess_id,
                    "subject": sess.get("subject", "General"),
                    "topic": sess.get("topic", "Core Topic"),
                    "day": day_name,
                    "day_number": day_idx,
                    "planned_minutes": planned_mins,
                    "actual_minutes": actual_mins or 0,
                    "missed_minutes": planned_mins - (actual_mins or 0),
                    "reason": "Incomplete from previous day",
                })

    return missed


from services.weak_topics import compute_weak_topics, WeakTopicsService



@router.get("/weak-topics")
async def get_weak_topics(
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Deterministically computes subjects and topics flagged as Needs Revision with explainability tags.
    """
    clerk_id = user_data.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

    try:
        db = get_db()
        user_res = db.table("users").select("id").eq("clerk_id", clerk_id).limit(1).execute()
        if not user_res.data:
            return {"success": True, "count": 0, "weak_topics": []}

        user_id = user_res.data[0]["id"]
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not plan_res.data:
            return {"success": True, "count": 0, "weak_topics": []}

        plan_data = plan_res.data[0].get("plan_data") or {}
        weak_topics = compute_weak_topics(plan_data)

        return {
            "success": True,
            "count": len(weak_topics),
            "weak_topics": weak_topics,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get weak topics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute weak topics",
        ) from exc


@router.get("")
async def get_plans(
    user_data: dict = Depends(verify_clerk_token),
):
    clerk_id = user_data.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

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
            return {"success": True, "plans": []}

        user_id = user_res.data[0]["id"]

        plans_res = (
            db.table("study_plans")
            .select("id, plan_data, created_at, updated_at, is_active")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        return {
            "success": True,
            "plans": plans_res.data or [],
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to fetch study plans")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch study plans",
        ) from exc


@router.get("/adaptive-status")
async def get_adaptive_status(
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Evaluates active study plan for missed tasks from previous days and returns adaptive rebalance status.
    """
    clerk_id = user_data.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

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
            return {
                "success": True,
                "needs_rebalance": False,
                "missed_task_count": 0,
                "missed_minutes": 0,
                "affected_subjects": [],
                "missed_tasks": [],
                "summary": "No active profile found.",
            }

        user_id = user_res.data[0]["id"]
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not plan_res.data:
            return {
                "success": True,
                "needs_rebalance": False,
                "missed_task_count": 0,
                "missed_minutes": 0,
                "affected_subjects": [],
                "missed_tasks": [],
                "summary": "No active study plan found.",
            }

        plan_data = plan_res.data[0].get("plan_data") or {}
        missed_tasks = find_missed_tasks(plan_data)
        affected_subjects = sorted(list(set(t["subject"] for t in missed_tasks)))
        total_missed_mins = sum(t["missed_minutes"] for t in missed_tasks)

        schedule_reeval_flag = bool(plan_data.get("schedule_reevaluation_required") or plan_data.get("requires_rebalance"))
        needs_rebalance = len(missed_tasks) > 0 or schedule_reeval_flag
        reeval_audit = plan_data.get("reevaluation_audit") or {}
        reeval_msg = reeval_audit.get("message")

        if missed_tasks and schedule_reeval_flag and reeval_msg:
            summary = (
                f"Detected {len(missed_tasks)} missed task(s) totaling {total_missed_mins} mins "
                f"in {', '.join(affected_subjects)}. In addition: {reeval_msg}"
            )
        elif missed_tasks:
            summary = (
                f"Detected {len(missed_tasks)} missed task(s) totaling {total_missed_mins} mins "
                f"in {', '.join(affected_subjects)} from previous days."
            )
        elif schedule_reeval_flag and reeval_msg:
            summary = reeval_msg
        elif schedule_reeval_flag:
            summary = "Daily study hours update requires schedule re-evaluation."
        else:
            summary = "All scheduled study sessions on track."

        return {
            "success": True,
            "needs_rebalance": needs_rebalance,
            "missed_task_count": len(missed_tasks),
            "missed_minutes": total_missed_mins,
            "affected_subjects": affected_subjects,
            "missed_tasks": missed_tasks,
            "schedule_reevaluation_required": schedule_reeval_flag,
            "reevaluation_audit": reeval_audit if schedule_reeval_flag else None,
            "summary": summary,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to get adaptive status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate adaptive schedule status",
        ) from exc


@router.post("/rebalance")
async def rebalance_plan(
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Dynamically adjusts and rebalances the study plan by redistributing missed tasks into upcoming days.
    """
    clerk_id = user_data.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_id = user_res.data[0]["id"]
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not plan_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active study plan not found",
            )

        plan_row = plan_res.data[0]
        plan_data = plan_row.get("plan_data") or {}
        missed_tasks = find_missed_tasks(plan_data)

        if not missed_tasks:
            return {
                "success": True,
                "message": "No missed tasks detected; schedule is already balanced",
                "rebalanced_count": 0,
                "plan_data": plan_data,
            }

        weekly_schedule = plan_data.get("weekly_schedule") or []
        executions = plan_data.get("task_executions") or {}
        now = datetime.now(timezone.utc).isoformat()

        # Allocate catch-up sessions into upcoming days with lowest load
        for idx, missed in enumerate(missed_tasks):
            # Target day in upcoming schedule
            target_idx = min(len(weekly_schedule) - 1, max(missed["day_number"], (missed["day_number"] + idx) % len(weekly_schedule)))
            target_day = weekly_schedule[target_idx]
            sessions = target_day.setdefault("sessions", [])

            rebalanced_id = f"rebalanced-{missed['id']}"
            if not any(s.get("id") == rebalanced_id for s in sessions):
                catchup_session = {
                    "id": rebalanced_id,
                    "subject": missed["subject"],
                    "topic": f"Catch-up Revision: {missed['topic']}",
                    "duration_hours": round(missed["missed_minutes"] / 60.0, 1) or 1.0,
                    "activity_type": "revision_quiz",
                    "priority": "high",
                    "completed": False,
                    "is_completed": False,
                }
                sessions.append(catchup_session)
                target_day["total_hours"] = round(sum(s.get("duration_hours", 1) for s in sessions), 1)

            # Mark original missed task as rebalanced so alert clears
            executions[missed["id"]] = {
                **(executions.get(missed["id"]) or {}),
                "status": "rebalanced",
                "notes": f"Rebalanced to {target_day.get('day')}",
                "updated_at": now,
            }

        plan_data["weekly_schedule"] = weekly_schedule
        plan_data["task_executions"] = executions

        db.table("study_plans").update({
            "plan_data": plan_data,
            "updated_at": now,
        }).eq("id", plan_row["id"]).execute()

        return {
            "success": True,
            "message": f"Successfully rebalanced {len(missed_tasks)} task(s) into upcoming schedule",
            "rebalanced_count": len(missed_tasks),
            "plan_data": plan_data,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to rebalance study plan")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rebalance study plan",
        ) from exc