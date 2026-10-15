
from fastapi import APIRouter, Depends, HTTPException, Query

from auth import verify_clerk_token
from services.recommendation_service import recommendation_service

router = APIRouter(
    prefix="/api/v1/recommendations",
    tags=["Recommendations"]
)


@router.get("")
async def get_recommendations(
    query: str = Query(..., min_length=1, max_length=500),
    top_n: int = Query(5, ge=1, le=20),
    user_data: dict = Depends(verify_clerk_token)
):
    # Ensure the verified Clerk token identifies a user.
    if not user_data.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID is missing"
        )

    try:
        results = recommendation_service.recommend_courses(
            query=query.strip(),
            top_n=top_n
        )

        return {
            "success": True,
            "count": len(results),
            "recommendations": results
        }

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to generate recommendations"
        )
