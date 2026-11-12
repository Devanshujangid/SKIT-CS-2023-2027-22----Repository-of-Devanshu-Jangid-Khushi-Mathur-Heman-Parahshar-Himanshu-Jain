"""
Admin CRUD API Routes (Resources & Student Management).

All endpoints in this router are strictly protected by `require_admin` (RBAC),
returning HTTP 403 Forbidden to standard students and HTTP 401 Unauthorized to
unauthenticated callers.
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_admin
from database import get_db
from schemas.admin_and_leaderboard import (
    AdminCreateResource,
    AdminCreateStudent,
    AdminDeleteStudentResponse,
    AdminResourceDeleteResponse,
    AdminResourceListResponse,
    AdminResourceResponse,
    AdminStudentListResponse,
    AdminStudentMutationResponse,
    AdminStudentRecord,
    AdminUpdateResource,
    AdminUpdateStudent,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin"],
    dependencies=[Depends(require_admin)],
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ===========================================================================
# 1. Admin Resource CRUD Endpoints
# ===========================================================================

@router.get("/resources", response_model=AdminResourceListResponse)
async def list_admin_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    subject: Optional[str] = Query(default=None),
    admin_payload: dict = Depends(require_admin),
):
    """List paginated curated learning resources (Admin only)."""
    try:
        db = get_db()
        query = db.table("learning_resources").select("*")
        if subject:
            query = query.eq("subject", subject.strip())
        res = query.order("created_at", desc=True).execute()
        rows = res.data or []
        total = len(rows)
        start = (page - 1) * page_size
        sliced = rows[start : start + page_size]

        return AdminResourceListResponse(
            success=True,
            total=total,
            page=page,
            page_size=page_size,
            resources=[AdminResourceResponse.model_validate(r) for r in sliced],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to list resources (admin=%s)", admin_payload.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve learning resources",
        ) from exc


@router.post(
    "/resources",
    status_code=status.HTTP_201_CREATED,
    response_model=AdminResourceResponse,
)
async def create_admin_resource(
    payload: AdminCreateResource,
    admin_payload: dict = Depends(require_admin),
):
    """Create a curated learning resource (Admin only)."""
    try:
        db = get_db()
        now = _now_iso()
        insert_data = {
            "id": str(uuid4()),
            **payload.model_dump(),
            "created_by": admin_payload.get("sub"),
            "created_at": now,
            "updated_at": now,
        }
        res = db.table("learning_resources").insert(insert_data).execute()
        row = (res.data or [insert_data])[0]
        return AdminResourceResponse.model_validate(row)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to create resource (admin=%s)", admin_payload.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create learning resource",
        ) from exc


@router.patch("/resources/{resource_id}", response_model=AdminResourceResponse)
async def update_admin_resource(
    resource_id: str,
    payload: AdminUpdateResource,
    admin_payload: dict = Depends(require_admin),
):
    """Partially update an existing curated learning resource (Admin only)."""
    try:
        db = get_db()
        update_data = {
            **payload.model_dump(exclude_unset=True),
            "updated_at": _now_iso(),
        }
        res = (
            db.table("learning_resources")
            .update(update_data)
            .eq("id", resource_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource '{resource_id}' not found",
            )
        return AdminResourceResponse.model_validate(res.data[0])
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to update resource %s", resource_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update learning resource",
        ) from exc


@router.delete("/resources/{resource_id}", response_model=AdminResourceDeleteResponse)
async def delete_admin_resource(
    resource_id: str,
    admin_payload: dict = Depends(require_admin),
):
    """Delete a curated learning resource (Admin only)."""
    try:
        db = get_db()
        res = (
            db.table("learning_resources")
            .delete()
            .eq("id", resource_id)
            .execute()
        )
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learning resource '{resource_id}' not found",
            )
        return AdminResourceDeleteResponse(deleted_id=resource_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to delete resource %s", resource_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete learning resource",
        ) from exc


# ===========================================================================
# 2. Admin Student CRUD Endpoints
# ===========================================================================

@router.get("/students", response_model=AdminStudentListResponse)
async def list_admin_students(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(require_admin),
):
    """List paginated student records and profiles (Admin only)."""
    try:
        db = get_db()
        users_res = db.table("users").select("id, clerk_id, email, role, created_at").execute()
        users = users_res.data or []
        total = len(users)
        start = (page - 1) * page_size
        page_users = users[start : start + page_size]

        records = []
        for u in page_users:
            uid = str(u["id"])
            prof_res = (
                db.table("student_profiles")
                .select("semester, study_hours_per_day, goals, subjects, onboarding_completed")
                .eq("user_id", uid)
                .limit(1)
                .execute()
            )
            prof = prof_res.data[0] if prof_res.data else {}
            records.append(
                AdminStudentRecord(
                    id=uid,
                    clerk_id=u.get("clerk_id", ""),
                    email=u.get("email", "unknown@example.com"),
                    role=u.get("role", "student"),
                    semester=prof.get("semester", 1),
                    study_hours_per_day=prof.get("study_hours_per_day", 2.0),
                    goals=prof.get("goals") or [],
                    subjects=prof.get("subjects") or [],
                    onboarding_completed=bool(prof.get("onboarding_completed", False)),
                    created_at=u.get("created_at"),
                )
            )

        return AdminStudentListResponse(
            success=True,
            admin_clerk_id=str(admin_payload.get("sub", "")),
            total_students=total,
            page=page,
            page_size=page_size,
            students=records,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to list students")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve students",
        ) from exc


@router.post(
    "/students",
    status_code=status.HTTP_201_CREATED,
    response_model=AdminStudentMutationResponse,
)
async def create_admin_student(
    payload: AdminCreateStudent,
    admin_payload: dict = Depends(require_admin),
):
    """Provision a student user and profile (Admin only)."""
    try:
        db = get_db()
        user_id = str(uuid4())
        now = _now_iso()

        user_row = {
            "id": user_id,
            "clerk_id": payload.clerk_id,
            "email": str(payload.email),
            "role": payload.role,
            "created_at": now,
        }
        user_res = db.table("users").insert(user_row).execute()
        saved_user = (user_res.data or [user_row])[0]
        resolved_id = str(saved_user.get("id", user_id))

        profile_row = {
            "user_id": resolved_id,
            "semester": payload.semester,
            "study_hours_per_day": payload.study_hours_per_day,
            "goals": payload.goals,
            "subjects": payload.subjects,
            "onboarding_completed": payload.onboarding_completed,
        }
        db.table("student_profiles").upsert(profile_row, on_conflict="user_id").execute()

        record = AdminStudentRecord(
            id=resolved_id,
            clerk_id=payload.clerk_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            semester=payload.semester,
            study_hours_per_day=payload.study_hours_per_day,
            goals=payload.goals,
            subjects=payload.subjects,
            onboarding_completed=payload.onboarding_completed,
            created_at=saved_user.get("created_at"),
        )
        return AdminStudentMutationResponse(
            success=True,
            message="Student created successfully",
            student=record,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to create student (admin=%s)", admin_payload.get("sub"))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create student",
        ) from exc


@router.patch("/students/{user_id}", response_model=AdminStudentMutationResponse)
async def update_admin_student(
    user_id: str,
    payload: AdminUpdateStudent,
    admin_payload: dict = Depends(require_admin),
):
    """Update a student's account or academic profile fields (Admin only)."""
    try:
        db = get_db()
        user_res = (
            db.table("users")
            .select("id, clerk_id, email, role, created_at")
            .eq("id", user_id)
            .limit(1)
            .execute()
        )
        if not user_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student '{user_id}' not found",
            )
        user_data = user_res.data[0]

        updates = payload.model_dump(exclude_unset=True)
        user_fields = {k: updates[k] for k in ("email", "role") if k in updates}
        if user_fields:
            upd_user_res = db.table("users").update(user_fields).eq("id", user_id).execute()
            if upd_user_res.data:
                user_data = upd_user_res.data[0]

        prof_res = (
            db.table("student_profiles")
            .select("semester, study_hours_per_day, goals, subjects, onboarding_completed")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        prof_data = prof_res.data[0] if prof_res.data else {
            "semester": 1,
            "study_hours_per_day": 2.0,
            "goals": ["Academic Excellence"],
            "subjects": [],
            "onboarding_completed": True,
        }

        prof_fields = {
            k: updates[k]
            for k in ("semester", "study_hours_per_day", "goals", "subjects", "onboarding_completed")
            if k in updates
        }
        if prof_fields:
            upd_prof_res = (
                db.table("student_profiles")
                .update(prof_fields)
                .eq("user_id", user_id)
                .execute()
            )
            if upd_prof_res.data:
                prof_data = upd_prof_res.data[0]
            else:
                prof_data = {**prof_data, **prof_fields}

        record = AdminStudentRecord(
            id=str(user_data["id"]),
            clerk_id=user_data.get("clerk_id", ""),
            email=user_data.get("email"),
            full_name=updates.get("full_name"),
            role=user_data.get("role", "student"),
            semester=prof_data.get("semester", 1),
            study_hours_per_day=prof_data.get("study_hours_per_day", 2.0),
            goals=prof_data.get("goals") or [],
            subjects=prof_data.get("subjects") or [],
            onboarding_completed=bool(prof_data.get("onboarding_completed", True)),
            is_suspended=bool(updates.get("is_suspended", False)),
            created_at=user_data.get("created_at"),
            updated_at=datetime.now(timezone.utc),
        )
        return AdminStudentMutationResponse(
            success=True,
            message="Student updated successfully",
            student=record,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to update student %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update student",
        ) from exc


@router.delete("/students/{user_id}", response_model=AdminDeleteStudentResponse)
async def delete_admin_student(
    user_id: str,
    admin_payload: dict = Depends(require_admin),
):
    """Delete a student user record (Admin only)."""
    try:
        db = get_db()
        res = db.table("users").delete().eq("id", user_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student '{user_id}' not found",
            )
        return AdminDeleteStudentResponse(deleted_user_id=user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Admin failed to delete student %s", user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete student",
        ) from exc

