from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from auth import require_admin, verify_clerk_token
from database import get_db
from schemas.resources import (
    ResourceCreateRequest as AdminResourceCreateRequest,
    ResourceUpdateRequest,
)
from services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)

# Student-facing discovery router
router = APIRouter(
    prefix="/api/v1/resources",
    tags=["Resource Discovery & Management"],
)

# Admin-only management router
admin_router = APIRouter(
    prefix="/api/v1/admin/resources",
    tags=["Admin Resources"],
)


# ===========================================================================
# 1. Student / Public Learning Resource Endpoints
# ===========================================================================

@router.get("")
async def list_learning_resources(
    category: Optional[str] = Query(None, description="Filter by resource category"),
    subject: Optional[str] = Query(None, description="Filter by subject area"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Returns curated active learning resources for enrolled students.
    """
    if not user_data.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    try:
        limit_val = limit if isinstance(limit, int) else 20
        offset_val = offset if isinstance(offset, int) else 0

        db = get_db()
        query = db.table("learning_resources").select("*").eq("is_active", True)

        if isinstance(category, str) and category.strip():
            query = query.eq("category", category.strip().lower())
        if isinstance(subject, str) and subject.strip():
            query = query.eq("subject", subject.strip())

        res = query.order("created_at", desc=True).range(offset_val, offset_val + limit_val - 1).execute()
        resources = res.data or []

        return {
            "success": True,
            "total": len(resources),
            "count": len(resources),
            "resources": resources,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve learning resources")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning resources",
        ) from exc


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
    """
    Searches online course catalog using TF-IDF cosine similarity.
    """
    if not user_data.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing",
        )

    query = query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
    except Exception as exc:
        logger.exception("Failed to search learning resources")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search learning resources",
        ) from exc


# ===========================================================================
# 2. Admin CRUD Endpoints (POST / PATCH / DELETE / GET)
# ===========================================================================

@admin_router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new learning resource (Admin only)",
)
async def create_admin_resource(
    payload: AdminResourceCreateRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Creates a new learning resource in the database.
    Restricted: 'admin' role ONLY (students receive 403 Forbidden).
    """
    try:
        db = get_db()
        admin_clerk_id = admin_payload.get("sub")
        admin_uuid = None

        if admin_clerk_id:
            user_lookup = (
                db.table("users")
                .select("id")
                .eq("clerk_id", admin_clerk_id)
                .limit(1)
                .execute()
            )
            if user_lookup.data:
                admin_uuid = str(user_lookup.data[0]["id"])

        record: Dict[str, Any] = {
            "title": payload.title,
            "description": payload.description,
            "url": payload.url,
            "category": payload.category,
            "subject": payload.subject,
            "provider": payload.provider,
            "difficulty": payload.difficulty,
            "rating": payload.rating,
            "tags": payload.tags,
            "is_active": payload.is_active,
            "created_by": admin_uuid,
        }

        insert_res = db.table("learning_resources").insert(record).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to insert learning resource into database",
            )

        created_item = insert_res.data[0]
        logger.info(
            "Admin created learning resource '%s' (id=%s)",
            created_item.get("title"),
            created_item.get("id"),
        )

        return {
            "success": True,
            "message": "Learning resource created successfully",
            "resource": created_item,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin resource creation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create learning resource",
        ) from exc


@admin_router.patch(
    "/{id}",
    summary="Update an existing learning resource (Admin only)",
)
async def update_admin_resource(
    id: str,
    payload: ResourceUpdateRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Updates an existing learning resource by ID.
    Restricted: 'admin' role ONLY (students receive 403 Forbidden).
    """
    try:
        db = get_db()

        # Check resource existence
        existing_res = (
            db.table("learning_resources")
            .select("id")
            .eq("id", id)
            .limit(1)
            .execute()
        )
        if not existing_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource with ID '{id}' not found",
            )

        update_fields = {
            k: v for k, v in payload.model_dump().items() if v is not None
        }

        if not update_fields:
            # Nothing to update, return current record
            curr_res = db.table("learning_resources").select("*").eq("id", id).limit(1).execute()
            return {
                "success": True,
                "message": "No fields provided to update",
                "resource": curr_res.data[0] if curr_res.data else {},
            }

        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()

        update_res = (
            db.table("learning_resources")
            .update(update_fields)
            .eq("id", id)
            .execute()
        )

        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update learning resource",
            )

        updated_item = update_res.data[0]
        logger.info("Admin updated learning resource '%s' (id=%s)", updated_item.get("title"), id)

        return {
            "success": True,
            "message": "Learning resource updated successfully",
            "resource": updated_item,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin resource update failed for id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update learning resource",
        ) from exc


@admin_router.delete(
    "/{id}",
    summary="Delete a learning resource (Admin only)",
)
async def delete_admin_resource(
    id: str,
    admin_payload: dict = Depends(require_admin),
):
    """
    Deletes a learning resource from the catalog by ID.
    Restricted: 'admin' role ONLY (students receive 403 Forbidden).
    """
    try:
        db = get_db()

        # Check existence before deletion
        existing_res = (
            db.table("learning_resources")
            .select("id, title")
            .eq("id", id)
            .limit(1)
            .execute()
        )
        if not existing_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource with ID '{id}' not found",
            )

        deleted_title = existing_res.data[0].get("title", "")

        delete_res = (
            db.table("learning_resources")
            .delete()
            .eq("id", id)
            .execute()
        )

        logger.info("Admin deleted learning resource '%s' (id=%s)", deleted_title, id)

        return {
            "success": True,
            "id": id,
            "message": f"Learning resource '{deleted_title}' deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin resource deletion failed for id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete learning resource",
        ) from exc


@admin_router.get(
    "",
    summary="List all learning resources for administration (Admin only)",
)
async def list_admin_resources(
    category: Optional[str] = Query(None),
    subject: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_payload: dict = Depends(require_admin),
):
    """
    Lists all resources (active and inactive) for administrative audit.
    Restricted: 'admin' role ONLY.
    """
    try:
        limit_val = limit if isinstance(limit, int) else 50
        offset_val = offset if isinstance(offset, int) else 0

        db = get_db()
        query = db.table("learning_resources").select("*")

        if isinstance(category, str) and category.strip():
            query = query.eq("category", category.strip().lower())
        if isinstance(subject, str) and subject.strip():
            query = query.eq("subject", subject.strip())
        if isinstance(is_active, bool):
            query = query.eq("is_active", is_active)

        res = query.order("created_at", desc=True).range(offset_val, offset_val + limit_val - 1).execute()
        resources = res.data or []

        return {
            "success": True,
            "count": len(resources),
            "admin_clerk_id": admin_payload.get("sub"),
            "resources": resources,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve admin learning resources")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve admin resources list",
        ) from exc
