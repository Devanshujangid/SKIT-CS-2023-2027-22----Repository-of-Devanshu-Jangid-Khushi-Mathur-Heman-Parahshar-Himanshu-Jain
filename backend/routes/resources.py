import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from auth import verify_clerk_token, require_admin
from services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resource Discovery & Management"],
)


# In-memory store for newly added custom resources
_CUSTOM_RESOURCES = [
    {
        "id": "res-1",
        "title": "Operating Systems and You: Becoming a Power User",
        "platform": "Google / Coursera",
        "subject": "Operating Systems",
        "url": "https://www.coursera.org/learn/operating-systems",
        "difficulty": "Beginner",
        "rating": 4.8,
        "enrolled_count": 89,
        "created_at": "2026-10-15T10:00:00Z",
    },
    {
        "id": "res-2",
        "title": "Computer Communications - Stanford University",
        "platform": "Coursera",
        "subject": "Computer Networks",
        "url": "https://www.coursera.org/learn/computer-networking",
        "difficulty": "Intermediate",
        "rating": 4.7,
        "enrolled_count": 64,
        "created_at": "2026-10-18T12:00:00Z",
    },
    {
        "id": "res-3",
        "title": "Database Management Essentials",
        "platform": "University of Colorado Boulder",
        "subject": "Database Management Systems",
        "url": "https://www.coursera.org/learn/database-management",
        "difficulty": "Intermediate",
        "rating": 4.6,
        "enrolled_count": 112,
        "created_at": "2026-10-20T09:30:00Z",
    },
    {
        "id": "res-4",
        "title": "Algorithms, Part I - Princeton University",
        "platform": "Princeton / Coursera",
        "subject": "Design & Analysis of Algorithms",
        "url": "https://www.coursera.org/learn/algorithms-part1",
        "difficulty": "Advanced",
        "rating": 4.9,
        "enrolled_count": 145,
        "created_at": "2026-10-22T14:15:00Z",
    },
    {
        "id": "res-5",
        "title": "Software Engineering: Introduction",
        "platform": "University of British Columbia",
        "subject": "Software Engineering",
        "url": "https://www.coursera.org/learn/software-engineering-introduction",
        "difficulty": "Beginner",
        "rating": 4.5,
        "enrolled_count": 42,
        "created_at": "2026-10-25T16:00:00Z",
    },
]


class ResourceCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255, description="Resource or Course Title")
    platform: str = Field(default="Coursera", max_length=100, description="Platform or University name")
    subject: str = Field(..., min_length=2, max_length=100, description="Target Subject")
    url: str = Field(..., min_length=5, max_length=500, description="URL link to resource")
    difficulty: str = Field(default="Intermediate", max_length=50, description="Beginner, Intermediate, Advanced")
    rating: float = Field(default=4.8, ge=1.0, le=5.0, description="Rating from 1.0 to 5.0")
    description: Optional[str] = Field(default=None, max_length=1000)


@router.get("")
@router.get("/")
async def get_all_resources(
    subject: Optional[str] = Query(None, description="Filter by subject"),
    user_data: dict = Depends(verify_clerk_token),
):
    """Retrieve all available academic resources for students and admin tables."""
    filtered = _CUSTOM_RESOURCES
    if subject:
        filtered = [r for r in filtered if r["subject"].lower() == subject.lower()]

    return {
        "success": True,
        "count": len(filtered),
        "resources": filtered,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_new_resource(
    payload: ResourceCreateRequest,
    admin_data: dict = Depends(require_admin),
):
    """Admin-only endpoint to add a new learning resource into the catalog."""
    new_id = f"res-{len(_CUSTOM_RESOURCES) + 1}"
    new_res = {
        "id": new_id,
        "title": payload.title.strip(),
        "platform": payload.platform.strip(),
        "subject": payload.subject.strip(),
        "url": payload.url.strip(),
        "difficulty": payload.difficulty.strip(),
        "rating": float(payload.rating),
        "enrolled_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _CUSTOM_RESOURCES.insert(0, new_res)
    logger.info("Admin %s created new resource: %s", admin_data.get("sub"), new_res["title"])

    return {
        "success": True,
        "message": f"Resource '{payload.title}' added successfully",
        "resource": new_res,
    }


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
