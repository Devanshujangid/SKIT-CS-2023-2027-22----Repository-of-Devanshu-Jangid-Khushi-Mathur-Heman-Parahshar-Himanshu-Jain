
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import verify_clerk_token
from database import get_db

router = APIRouter(
    prefix="/api/v1/tasks",
    tags=["Tasks"]
)


class TaskStatusRequest(BaseModel):
    is_completed: bool


@router.patch("/{id}/status")
async def update_task_status(
    id: UUID,
    payload: TaskStatusRequest,
    user_data: dict = Depends(verify_clerk_token)
):
    clerk_id = user_data.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID is missing"
        )

    try:
        db = get_db()

        # Resolve the authenticated Clerk user to the internal UUID.
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

        # Update only a task owned by this user.
        now = datetime.now(timezone.utc).isoformat()

        update_data = {
            "is_completed": payload.is_completed,
            "completed_at": now if payload.is_completed else None,
            "updated_at": now
        }

        result = (
            db.table("tasks")
            .update(update_data)
            .eq("id", str(id))
            .eq("user_id", user_id)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Task not found"
            )

        return {
            "success": True,
            "message": "Task status updated",
            "task": result.data[0]
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to update task status"
        )
