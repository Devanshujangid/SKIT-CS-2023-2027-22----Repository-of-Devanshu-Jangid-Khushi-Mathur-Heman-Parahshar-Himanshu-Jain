from fastapi import APIRouter, Depends

from auth import verify_clerk_token
from database import get_db

router = APIRouter(
    prefix="/api/v1/plans",
    tags=["Plans"]
)


@router.get("")
async def get_plans(
    user_data: dict = Depends(verify_clerk_token)
):
    clerk_id = user_data.get("sub", "dev_user_default")

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
            return {
                "success": True,
                "plans": []
            }

        user_id = user_res.data[0]["id"]

        # Fetch only required study-plan fields
        plans_res = (
            db.table("study_plans")
            .select("id, plan_data, created_at, updated_at")
            .eq("user_id", user_id)
            .execute()
        )

        return {
            "success": True,
            "plans": plans_res.data
        }

    except Exception as exc:
        raise Exception(f"Failed to fetch study plans: {exc}")