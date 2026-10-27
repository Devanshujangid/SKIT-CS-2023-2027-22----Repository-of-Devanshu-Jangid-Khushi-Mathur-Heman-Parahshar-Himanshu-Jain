
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from auth import verify_clerk_token
from services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resource Discovery"],
)


@router.get("/search")
async def search_resources(
    query: str = Query(..., min_length=1, max_length=500),
    top_n: int = Query(5, ge=1, le=5),
    user_data: dict = Depends(verify_clerk_token),
):
    if not user_data.get("sub"):
        raise HTTPException(
            status_code=401,
            detail="Authenticated user ID is missing",
        )

    query = query.strip()
    if not query:
        raise HTTPException(
            status_code=422,
            detail="Search query cannot be empty",
        )

    try:
        results = await run_in_threadpool(
            recommendation_service.recommend_courses,
            query=query,
            top_n=top_n,
        )

        results = results or []

        return {
            "success": True,
            "count": len(results),
            "query": query,
            "resources": results,
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Failed to search learning resources")
        raise HTTPException(
            status_code=500,
            detail="Failed to search learning resources",
        )
