import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth import verify_clerk_token
from database import get_db, get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"],
)


# -------------------- REQUEST MODELS --------------------

class TaskStatusRequest(BaseModel):
    is_completed: bool


class TaskCreateRequest(BaseModel):
    title: str
    description: Optional[str] = None


class StudySessionCreate(BaseModel):
    started_at: datetime
    ended_at: datetime
    focus_rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = Field(default=None, max_length=2000)


# -------------------- GET TASKS --------------------

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
        user_id = get_or_create_user(
            db, clerk_id, email=user_data.get("email")
        )

        tasks_res = (
            db.table("tasks")
            .select(
                "id, user_id, title, description, is_completed, "
                "completed_at, created_at, updated_at"
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


# -------------------- CREATE TASK --------------------

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
        user_id = get_or_create_user(
            db, clerk_id, email=user_data.get("email")
        )

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


# -------------------- UPDATE TASK STATUS --------------------

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
        user_id = get_or_create_user(
            db, clerk_id, email=user_data.get("email")
        )
        now = datetime.now(timezone.utc).isoformat()

        # Update a standalone task only if its ID is a UUID.
        try:
            task_uuid = UUID(id)
        except ValueError:
            task_uuid = None

        if task_uuid is not None:
            update_data = {
                "is_completed": payload.is_completed,
                "completed_at": now if payload.is_completed else None,
                "updated_at": now,
            }

            result = (
                db.table("tasks")
                .update(update_data)
                .eq("id", str(task_uuid))
                .eq("user_id", user_id)
                .select(
                    "id, user_id, title, description, is_completed, "
                    "completed_at, created_at, updated_at"
                )
                .execute()
            )

            if result.data:
                return {
                    "success": True,
                    "message": "Task status updated",
                    "task": result.data[0],
                }

        # Preserve the existing study-plan fallback for non-UUID task IDs.
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
            plan_res = (
                db.table("study_plans")
                .select("id, plan_data")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

        if plan_res.data:
            plan_row = plan_res.data[0]
            plan_data = plan_row.get("plan_data") or {}
            completed_set = set(
                plan_data.get("completed_task_ids") or []
            )

            if payload.is_completed:
                completed_set.add(id)
            else:
                completed_set.discard(id)

            plan_data["completed_task_ids"] = list(completed_set)

            (
                db.table("study_plans")
                .update({
                    "plan_data": plan_data,
                    "updated_at": now,
                })
                .eq("id", plan_row["id"])
                .execute()
            )

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


# -------------------- RECORD STUDY SESSION --------------------

@router.post("/{id}/session", status_code=status.HTTP_201_CREATED)
async def create_study_session(
    id: UUID,
    payload: StudySessionCreate,
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
        user_id = get_or_create_user(
            db, clerk_id, email=user_data.get("email")
        )


        # Verify that the task belongs to this student.
        task_res = (
            db.table("tasks")
            .select("id")
            .eq("id", str(id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if not task_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )

        # Both timestamps must include timezone information.
        if (
            payload.started_at.tzinfo is None
            or payload.started_at.utcoffset() is None
            or payload.ended_at.tzinfo is None
            or payload.ended_at.utcoffset() is None
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Timestamps must include a timezone",
            )

        started_at = payload.started_at.astimezone(timezone.utc)
        ended_at = payload.ended_at.astimezone(timezone.utc)

        duration_seconds = (ended_at - started_at).total_seconds()

        if duration_seconds <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="End time must be after start time",
            )

        duration_minutes = round(duration_seconds / 60, 2)

        session_data = {
            "task_id": str(id),
            "user_id": user_id,
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "duration_minutes": duration_minutes,
            "focus_rating": payload.focus_rating,
            "notes": payload.notes,
        }

        result = (
            db.table("study_sessions")
            .insert(session_data)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save study session",
            )

        return {
            "success": True,
            "message": "Study session recorded",
            "session": result.data[0],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create study session")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create study session",
        ) from exc
