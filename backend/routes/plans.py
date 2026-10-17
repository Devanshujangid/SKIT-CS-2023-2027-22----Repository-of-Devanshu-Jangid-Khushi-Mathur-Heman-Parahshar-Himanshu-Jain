import logging

from fastapi import APIRouter, Depends, HTTPException

from auth import verify_clerk_token
from database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/plans",
    tags=["Plans"],
)


@router.get("")
async def get_plans(
    user_data: dict = Depends(verify_clerk_token),
):
    clerk_id = user_data.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=401,
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
            status_code=500,
            detail="Failed to fetch study plans",
        ) from exc