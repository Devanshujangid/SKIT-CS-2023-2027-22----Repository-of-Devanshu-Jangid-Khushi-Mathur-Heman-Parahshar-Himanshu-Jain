import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from auth import verify_clerk_token
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"],
)


class TaskStatusRequest(BaseModel):
    is_completed: bool


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None


@router.get("")
async def get_tasks(
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
            return {"success": True, "tasks": []}

        user_id = user_res.data[0]["id"]
        tasks_res = (
            db.table("tasks")
            .select(
                "id, user_id, title, description, is_completed, completed_at, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )

        return {
            "success": True,
            "tasks": tasks_res.data or [],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch tasks")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch tasks",
        ) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: TaskCreateRequest,
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_id = user_res.data[0]["id"]
        now = datetime.now(timezone.utc).isoformat()

        insert_data = {
            "user_id": user_id,
            "title": payload.title,
            "description": payload.description,
            "is_completed": False,
            "created_at": now,
            "updated_at": now,
        }

        result = db.table("tasks").insert(insert_data).execute()

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create task",
            )

        return {
            "success": True,
            "message": "Task created successfully",
            "task": result.data[0],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create task")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task",
        ) from exc


@router.patch("/{id}/status")
async def update_task_status(
    id: str,
    payload: TaskStatusRequest,
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        user_id = user_res.data[0]["id"]
        now = datetime.now(timezone.utc).isoformat()

        # 1. If ID is a valid UUID, attempt updating the standalone tasks table
        is_uuid = False
        try:
            UUID(id)
            is_uuid = True
        except ValueError:
            is_uuid = False

        if is_uuid:
            update_data = {
                "is_completed": payload.is_completed,
                "completed_at": now if payload.is_completed else None,
                "updated_at": now,
            }

            result = (
                db.table("tasks")
                .update(update_data)
                .eq("id", id)
                .eq("user_id", user_id)
                .select(
                    "id, user_id, title, description,is_completed,scheduled_date, completed_at, updated_at"
                )
                .execute()
            )

            if result.data:
                return {
                    "success": True,
                    "message": "Task status updated",
                    "task": result.data[0],
                }

        # 2. Fallback: Update completion in user's active study plan
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if plan_res.data:
            plan_row = plan_res.data[0]
            plan_data = plan_row.get("plan_data") or {}
            completed_set = set(plan_data.get("completed_task_ids") or [])

            if payload.is_completed:
                completed_set.add(id)
            else:
                completed_set.discard(id)

            plan_data["completed_task_ids"] = list(completed_set)

            db.table("study_plans").update({
                "plan_data": plan_data,
                "updated_at": now,
            }).eq("id", plan_row["id"]).execute()

            return {
                "success": True,
                "message": "Study plan task status updated",
                "task": {
                    "id": id,
                    "is_completed": payload.is_completed,
                },
            }

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to update task status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task status",
        ) from exc