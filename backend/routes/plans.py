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


def compute_weak_topics(plan_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Deterministically computes weak topics and subjects needing revision,
    producing rule-based explainability tags.
    """
    weekly_schedule = plan_data.get("weekly_schedule") or []
    completed_ids = set(plan_data.get("completed_task_ids") or [])
    executions = plan_data.get("task_executions") or {}

    subject_map: Dict[str, Dict[str, Any]] = {}

    for day_idx, day_item in enumerate(weekly_schedule, start=1):
        sessions = day_item.get("sessions") or []
        for s_idx, sess in enumerate(sessions, start=1):
            subject = sess.get("subject", "General Study")
            topic = sess.get("topic", "Core Topic")
            sess_id = sess.get("id") or f"live-d{day_idx}-t{s_idx}"
            planned_mins = int((sess.get("duration_hours") or 1.0) * 60)
            exec_info = executions.get(sess_id) or {}
            exec_status = exec_info.get("status")

            if exec_status == "completed" or sess_id in completed_ids:
                actual_mins = exec_info.get("actual_minutes", planned_mins)
                is_done = True
            elif exec_status == "partially_completed":
                actual_mins = exec_info.get("actual_minutes", int(planned_mins / 2))
                is_done = False
            elif exec_status == "missed":
                actual_mins = 0
                is_done = False
            else:
                actual_mins = 0
                is_done = False

            key = f"{subject}::{topic}"
            if key not in subject_map:
                subject_map[key] = {
                    "id": f"wt-{sess_id}",
                    "subject": subject,
                    "topic": topic,
                    "planned_minutes": 0,
                    "actual_minutes": 0,
                    "total_sessions": 0,
                    "completed_sessions": 0,
                    "missed_sessions": 0,
                    "partial_sessions": 0,
                    "priority": sess.get("priority", "medium"),
                }

            entry = subject_map[key]
            entry["planned_minutes"] += planned_mins
            entry["actual_minutes"] += actual_mins
            entry["total_sessions"] += 1
            if is_done:
                entry["completed_sessions"] += 1
            elif exec_status == "missed":
                entry["missed_sessions"] += 1
            elif exec_status == "partially_completed":
                entry["partial_sessions"] += 1

    weak_topics: List[Dict[str, Any]] = []
    for key, data in subject_map.items():
        tags: List[str] = []
        is_needs_revision = False
        severity = "low"
        deficit = max(0, data["planned_minutes"] - data["actual_minutes"])

        # Deterministic Explainability Rules:
        # Rule 1: Explicitly missed session
        if data["missed_sessions"] > 0:
            is_needs_revision = True
            severity = "high"
            tags.append(f"Missed Task: {data['topic']}")

        # Rule 2: Substantial study deficit
        if deficit >= 30:
            is_needs_revision = True
            if deficit >= 60:
                severity = "high"
            tags.append(f"Study Deficit: -{deficit}m")

        # Rule 3: Low completion rate with incomplete sessions
        if data["total_sessions"] > 0:
            comp_rate = int((data["completed_sessions"] / data["total_sessions"]) * 100)
            if comp_rate < 50 and data["completed_sessions"] < data["total_sessions"]:
                is_needs_revision = True
                tags.append(f"Completion Rate: {comp_rate}% (Low Mastery)")

        # Rule 4: High priority subject
        if data["priority"] == "high" and is_needs_revision:
            tags.append("High Priority Exam Target")

        if is_needs_revision:
            weak_topics.append({
                "id": data["id"],
                "subject": data["subject"],
                "topic": data["topic"],
                "status": "Needs Revision",
                "severity": severity,
                "explainability_tags": tags,
                "missed_minutes": deficit,
                "planned_minutes": data["planned_minutes"],
                "actual_minutes": data["actual_minutes"],
                "missed_sessions": data["missed_sessions"],
                "recommended_query": f"{data['subject']} {data['topic']}",
            })

    # Sort explicitly missed topics and high severity first
    weak_topics.sort(
        key=lambda x: (
            x.get("missed_sessions", 0) > 0,
            x["severity"] == "high",
            x["missed_minutes"],
        ),
        reverse=True,
    )
    return weak_topics


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

        return {
            "success": True,
            "needs_rebalance": len(missed_tasks) > 0,
            "missed_task_count": len(missed_tasks),
            "missed_minutes": total_missed_mins,
            "affected_subjects": affected_subjects,
            "missed_tasks": missed_tasks,
            "summary": (
                f"Detected {len(missed_tasks)} missed task(s) totaling {total_missed_mins} mins "
                f"in {', '.join(affected_subjects)} from previous days."
                if missed_tasks
                else "All scheduled study sessions on track."
            ),
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