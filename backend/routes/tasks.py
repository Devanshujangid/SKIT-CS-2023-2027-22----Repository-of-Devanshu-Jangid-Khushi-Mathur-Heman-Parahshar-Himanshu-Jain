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
    is_completed: Optional[bool] = None
    status: Optional[str] = None
    actual_minutes: Optional[int] = Field(default=None, ge=0)
    notes: Optional[str] = None


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class StudySessionCreate(BaseModel):
    started_at: datetime
    ended_at: datetime
    focus_rating: Optional[int] = Field(default=None, ge=1, le=5)
    notes: Optional[str] = Field(default=None, max_length=2000)


# -------------------- SHARED HELPERS --------------------

def get_authenticated_user(user_data: dict) -> str:
    """Resolve the authenticated Clerk user to the internal database user ID."""

    clerk_id = user_data.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user Clerk ID is missing",
        )

    db = get_db()

    user_id = get_or_create_user(
        db,
        clerk_id,
        email=user_data.get("email"),
    )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to resolve authenticated user",
        )

    return user_id


def resolve_task_status(payload: TaskStatusRequest):
    """
    Validate the requested task status and resolve its completion boolean.

    Supported statuses:
    completed, done, pending, not_started, in_progress.
    """

    allowed_statuses = {
        "completed": "completed",
        "done": "completed",
        "pending": "pending",
        "not_started": "pending",
        "in_progress": "in_progress",
    }

    requested_status = None

    if payload.status is not None:
        requested_status = payload.status.strip().lower()

        if requested_status not in allowed_statuses:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "Invalid status. Use completed, done, pending, "
                    "not_started, or in_progress."
                ),
            )

        requested_status = allowed_statuses[requested_status]

    if payload.is_completed is None and requested_status is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either is_completed or status",
        )

    # Explicit is_completed takes precedence, unless status contradicts it.
    if payload.is_completed is not None:
        is_completed = payload.is_completed

        if requested_status is not None:
            status_completion = requested_status == "completed"

            if is_completed != status_completion:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="is_completed and status contradict each other",
                )

        status_value = (
            "completed" if is_completed
            else requested_status or "pending"
        )
    else:
        status_value = requested_status
        is_completed = status_value == "completed"

    return is_completed, status_value


# -------------------- GET TASKS --------------------

@router.get("")
async def get_tasks(
    user_data: dict = Depends(verify_clerk_token),
):
    try:
        db = get_db()
        user_id = get_authenticated_user(user_data)

        result = (
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
            "tasks": result.data or [],
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
    try:
        db = get_db()
        user_id = get_authenticated_user(user_data)

        now = datetime.now(timezone.utc).isoformat()

        insert_data = {
            "user_id": user_id,
            "title": payload.title.strip(),
            "description": payload.description,
            "is_completed": False,
            "created_at": now,
            "updated_at": now,
        }

        result = (
            db.table("tasks")
            .insert(insert_data)
            .execute()
        )

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
    try:
        db = get_db()
        user_id = get_authenticated_user(user_data)

        # Resolve and validate the requested status.
        is_completed, status_val = resolve_task_status(payload)

        now = datetime.now(timezone.utc).isoformat()

        # UUID IDs belong to standalone rows in the tasks table.
        try:
            task_uuid = UUID(id)
        except ValueError:
            task_uuid = None

        if task_uuid is not None:
            # Update only the task owned by the authenticated student.
            update_data = {
                "is_completed": is_completed,
                "completed_at": now if is_completed else None,
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

            if not result.data:
                # Do not fall back to a study plan for a UUID.
                # This prevents confusing an unrelated/missing UUID
                # with a task embedded in a study-plan JSON object.
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Task not found",
                )

            return {
                "success": True,
                "message": "Task status updated",
                "task": result.data[0],
            }

        # Non-UUID IDs represent tasks embedded in a study plan.
        plan_res = (
            db.table("study_plans")
            .select("id, plan_data")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        # Preserve compatibility with installations that have no
        # active-plan flag set on the user's existing plan.
        if not plan_res.data:
            plan_res = (
                db.table("study_plans")
                .select("id, plan_data")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

        if not plan_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Study plan or task not found",
            )

        plan_row = plan_res.data[0]
        plan_data = plan_row.get("plan_data") or {}

        if not isinstance(plan_data, dict):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Study plan data has an invalid format",
            )

        # Preserve previous completion records.
        completed_ids = plan_data.get("completed_task_ids") or []

        if not isinstance(completed_ids, list):
            completed_ids = []

        completed_set = set(completed_ids)

        if is_completed:
            completed_set.add(id)
        else:
            completed_set.discard(id)

        # Preserve earlier execution details when a field is omitted.
        task_executions = plan_data.get("task_executions") or {}

        if not isinstance(task_executions, dict):
            task_executions = {}

        previous_execution = task_executions.get(id, {})

        if not isinstance(previous_execution, dict):
            previous_execution = {}

        execution_data = {
            **previous_execution,
            "status": status_val,
            "is_completed": is_completed,
            "updated_at": now,
        }

        if payload.actual_minutes is not None:
            execution_data["actual_minutes"] = payload.actual_minutes

        if payload.notes is not None:
            execution_data["notes"] = payload.notes

        task_executions[id] = execution_data

        plan_data["completed_task_ids"] = list(completed_set)
        plan_data["task_executions"] = task_executions

        update_result = (
            db.table("study_plans")
            .update({
                "plan_data": plan_data,
                "updated_at": now,
            })
            .eq("id", plan_row["id"])
            .eq("user_id", user_id)
            .execute()
        )

        # Supabase may return no rows for an update unless selected;
        # therefore, don't rely on update_result.data to detect success.

        return {
            "success": True,
            "message": "Study plan task execution updated",
            "task": {
                "id": id,
                "is_completed": is_completed,
                "status": status_val,
                "actual_minutes": execution_data.get("actual_minutes"),
                "notes": execution_data.get("notes"),
                "updated_at": now,
            },
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to update task status")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task status",
        ) from exc


# -------------------- RECORD STUDY SESSION --------------------

@router.post(
    "/{id}/session",
    status_code=status.HTTP_201_CREATED,
)
async def create_study_session(
    id: UUID,
    payload: StudySessionCreate,
    user_data: dict = Depends(verify_clerk_token),
):
    try:
        db = get_db()
        user_id = get_authenticated_user(user_data)

        # Confirm that the standalone task belongs to this student.
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

        # Require timezone-aware timestamps.
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

        # Convert timestamps to UTC before storing.
        started_at = payload.started_at.astimezone(timezone.utc)
        ended_at = payload.ended_at.astimezone(timezone.utc)

        duration_seconds = (
            ended_at - started_at
        ).total_seconds()

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