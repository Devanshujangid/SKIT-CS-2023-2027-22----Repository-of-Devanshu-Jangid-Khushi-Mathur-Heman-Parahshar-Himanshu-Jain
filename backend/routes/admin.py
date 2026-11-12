<<<<<<< HEAD
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
=======
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_admin, verify_clerk_token
from database import get_db
from routes.notifications import admin_broadcast_notification, get_admin_recent_broadcasts
from schemas.admin import (
    StudentStatusUpdateRequest,
    SubjectCreateRequest,
    SubjectUpdateRequest,
)
from schemas.notifications import (
    AdminBroadcastNotificationRequest,
    AdminBroadcastNotificationResponse,
>>>>>>> origin/main
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/admin",
<<<<<<< HEAD
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

=======
    tags=["Admin Management"],
)

subjects_public_router = APIRouter(
    prefix="/api/v1/subjects",
    tags=["Curriculum Subjects"],
)


# ===========================================================================
# 1. Student Account Management (GET / PATCH status / DELETE)
# ===========================================================================

@router.get("/students", summary="List enrolled students with account status")
async def list_admin_students(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status: 'active', 'suspended'"),
    semester: Optional[int] = Query(None, ge=1, le=8, description="Filter by semester"),
    search: Optional[str] = Query(None, description="Search by email"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_payload: dict = Depends(require_admin),
):
    """
    Returns student roster with account status, study hours, and plan adherence.
    Restricted: 'admin' role ONLY.
    """
    try:
        db = get_db()
        users_res = db.table("users").select("id, clerk_id, email, role, status, created_at").eq("role", "student").execute()
        students = users_res.data or []

        student_items = []
        for s in students:
            uid = str(s["id"])
            email = s.get("email", "")

            # Filters
            curr_status = s.get("status") or "active"
            if isinstance(status_filter, str) and status_filter.strip():
                if curr_status.lower() != status_filter.strip().lower():
                    continue
            if isinstance(search, str) and search.strip():
                if search.strip().lower() not in email.lower():
                    continue

            # Profile lookup
            prof_res = db.table("student_profiles").select("semester, study_hours_per_day, goals, subjects").eq("user_id", uid).limit(1).execute()
            prof = prof_res.data[0] if prof_res.data else {}
            student_sem = prof.get("semester", 1)

            if isinstance(semester, int) and student_sem != semester:
                continue

            # Active plan lookup
            plan_res = db.table("study_plans").select("id").eq("user_id", uid).eq("is_active", True).limit(1).execute()
            has_active_plan = bool(plan_res.data)

            # Tasks aggregation
            task_res = db.table("tasks").select("id, is_completed, completed_at").eq("user_id", uid).execute()
            tasks = task_res.data or []
            tot_tasks = len(tasks)
            comp_tasks = sum(1 for t in tasks if t.get("is_completed") or (t.get("completed_at") is not None))
            comp_rate = round((comp_tasks / tot_tasks) * 100, 1) if tot_tasks > 0 else 0.0

            student_items.append({
                "id": uid,
                "clerk_id": s.get("clerk_id"),
                "email": email,
                "role": s.get("role", "student"),
                "status": curr_status,
                "semester": student_sem,
                "study_hours_per_day": float(prof.get("study_hours_per_day", 2.0)),
                "goals": prof.get("goals", []),
                "subjects": prof.get("subjects", []),
                "has_active_plan": has_active_plan,
                "total_tasks": tot_tasks,
                "completed_tasks": comp_tasks,
                "completion_rate": comp_rate,
                "created_at": s.get("created_at"),
            })

        total_count = len(student_items)
        paginated = student_items[offset : offset + limit]

        return {
            "success": True,
            "total_students": total_count,
            "count": len(paginated),
            "students": paginated,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to retrieve admin students list")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve student roster",
        ) from exc


@router.patch("/students/{id}/status", summary="Suspend or activate a student account")
async def update_student_account_status(
    id: str,
    payload: StudentStatusUpdateRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Suspends or re-activates a student account.
    Restricted: 'admin' role ONLY.
    """
    try:
        db = get_db()
        user_res = db.table("users").select("id, email, role, status").eq("id", id).limit(1).execute()
        if not user_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student account with ID '{id}' not found",
            )

        target_user = user_res.data[0]
        if target_user.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative accounts cannot be suspended via this endpoint",
            )

        update_res = db.table("users").update({"status": payload.status}).eq("id", id).execute()
        logger.info("Admin %s updated status of student %s to '%s'", admin_payload.get("sub"), id, payload.status)

        return {
            "success": True,
            "id": id,
            "status": payload.status,
            "message": f"Student account status updated to '{payload.status}' successfully",
            "reason": payload.reason,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update student status for id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update student account status",
        ) from exc


@router.delete("/students/{id}", summary="Permanently delete a student account")
async def delete_student_account(
    id: str,
    admin_payload: dict = Depends(require_admin),
):
    """
    Permanently deletes a student account.
    Cascades to student_profiles, study_plans, tasks, and notifications.
    Restricted: 'admin' role ONLY.
    """
    try:
        db = get_db()
        user_res = db.table("users").select("id, email, role").eq("id", id).limit(1).execute()
        if not user_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Student account with ID '{id}' not found",
            )

        target_user = user_res.data[0]
        if target_user.get("role") == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative accounts cannot be deleted via student management",
            )

        db.table("users").delete().eq("id", id).execute()
        logger.info("Admin %s permanently deleted student %s (%s)", admin_payload.get("sub"), id, target_user.get("email"))

        return {
            "success": True,
            "id": id,
            "email": target_user.get("email"),
            "message": f"Student account '{target_user.get('email')}' permanently deleted",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete student account for id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete student account",
        ) from exc


# ===========================================================================
# 2. Global Subjects Management (/api/v1/admin/subjects & /api/v1/subjects)
# ===========================================================================

@router.get("/subjects", summary="List all subjects for administration")
async def list_admin_subjects(
    semester: Optional[int] = Query(None, ge=1, le=8),
    department: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin_payload: dict = Depends(require_admin),
):
    """
    Lists all subjects (active and inactive) for administrative curriculum management.
    """
    try:
        limit_val = limit if isinstance(limit, int) else 50
        offset_val = offset if isinstance(offset, int) else 0

        db = get_db()
        query = db.table("subjects").select("*")

        if isinstance(semester, int):
            query = query.eq("semester", semester)
        if isinstance(department, str) and department.strip():
            query = query.eq("department", department.strip())
        if isinstance(is_active, bool):
            query = query.eq("is_active", is_active)

        res = query.order("semester", desc=False).order("code", desc=False).range(offset_val, offset_val + limit_val - 1).execute()
        subjects = res.data or []

        return {
            "success": True,
            "total": len(subjects),
            "count": len(subjects),
            "subjects": subjects,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to list admin subjects")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subjects catalog",
        ) from exc


@router.post(
    "/subjects",
    status_code=status.HTTP_201_CREATED,
    summary="Add a new curriculum subject",
)
async def create_admin_subject(
    payload: SubjectCreateRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Creates a new subject in the global curriculum catalog.
    Restricted: 'admin' role ONLY.
    """
    try:
        db = get_db()

        # Check for duplicate subject code
        dup_res = db.table("subjects").select("id").eq("code", payload.code).limit(1).execute()
        if dup_res.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subject with code '{payload.code}' already exists",
            )

        record = {
            "code": payload.code,
            "name": payload.name,
            "semester": payload.semester,
            "department": payload.department,
            "credits": payload.credits,
            "description": payload.description,
            "is_active": payload.is_active,
        }

        insert_res = db.table("subjects").insert(record).execute()
        created_subject = insert_res.data[0] if insert_res.data else record

        logger.info("Admin created subject '%s - %s'", payload.code, payload.name)

        return {
            "success": True,
            "message": f"Subject '{payload.name}' ({payload.code}) created successfully",
            "subject": created_subject,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create subject")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subject",
        ) from exc


@router.patch("/subjects/{id}", summary="Update a curriculum subject")
async def update_admin_subject(
    id: str,
    payload: SubjectUpdateRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Updates an existing curriculum subject.
    Restricted: 'admin' role ONLY.
    """
    try:
        db = get_db()
        existing = db.table("subjects").select("id, code").eq("id", id).limit(1).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with ID '{id}' not found",
            )

        update_fields = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_fields:
            curr_res = db.table("subjects").select("*").eq("id", id).limit(1).execute()
            return {"success": True, "message": "No fields to update", "subject": curr_res.data[0]}

        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        update_res = db.table("subjects").update(update_fields).eq("id", id).execute()

        updated_item = update_res.data[0] if update_res.data else update_fields
        logger.info("Admin updated subject %s", id)

        return {
            "success": True,
            "message": "Subject updated successfully",
            "subject": updated_item,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to update subject id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subject",
        ) from exc


@router.delete("/subjects/{id}", summary="Delete a curriculum subject")
async def delete_admin_subject(
    id: str,
    admin_payload: dict = Depends(require_admin),
):
    """
    Deletes a subject from the curriculum catalog.
    Restricted: 'admin' role ONLY.
    """
    try:
        db = get_db()
        existing = db.table("subjects").select("id, code, name").eq("id", id).limit(1).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subject with ID '{id}' not found",
            )

        subj_name = existing.data[0].get("name", "")
        db.table("subjects").delete().eq("id", id).execute()
        logger.info("Admin deleted subject %s (%s)", id, subj_name)

        return {
            "success": True,
            "id": id,
            "message": f"Subject '{subj_name}' deleted successfully",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete subject id=%s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subject",
        ) from exc


@subjects_public_router.get("", summary="List active curriculum subjects for students")
async def list_active_subjects_for_students(
    semester: Optional[int] = Query(None, ge=1, le=8),
    department: Optional[str] = Query(None),
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Returns active subjects available for student enrollment and schedule generation.
    """
    try:
        db = get_db()
        query = db.table("subjects").select("id, code, name, semester, department, credits, description").eq("is_active", True)
        if semester:
            query = query.eq("semester", semester)
        if department:
            query = query.eq("department", department.strip())

        res = query.order("semester").order("code").execute()
        return {
            "success": True,
            "count": len(res.data or []),
            "subjects": res.data or [],
        }
    except Exception as exc:
        logger.exception("Failed to retrieve public subjects")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subjects catalog",
        ) from exc


# ===========================================================================
# 3. Direct Admin Notification Endpoints (/api/v1/admin/notifications)
# ===========================================================================

@router.post(
    "/notifications",
    status_code=status.HTTP_201_CREATED,
    summary="Push manual alerts to student notifications table",
)
@router.post(
    "/notifications/broadcast",
    status_code=status.HTTP_201_CREATED,
    summary="Alias: Broadcast notification to students",
)
async def admin_notifications_direct(
    payload: AdminBroadcastNotificationRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Direct alias wiring admin notification pushes to public.notifications.
    """
    return await admin_broadcast_notification(payload=payload, admin_payload=admin_payload)


@router.get("/notifications", summary="Retrieve recent broadcast notifications")
@router.get("/notifications/broadcasts", summary="Alias: Retrieve recent broadcasts")
async def get_admin_notifications_direct(
    limit: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(require_admin),
):
    """
    Retrieves recent administrative broadcast alerts.
    """
    return await get_admin_recent_broadcasts(limit=limit, admin_payload=admin_payload)


# ===========================================================================
# 4. Midnight Leaderboard Recalculation Trigger
# ===========================================================================

@router.post("/leaderboard/refresh", summary="Trigger Leaderboard evaluation immediately")
async def trigger_leaderboard_refresh(
    dry_run: bool = Query(False, description="Simulate evaluation without database mutation"),
    admin_payload: dict = Depends(require_admin),
):
    """
    Manually triggers the midnight Leaderboard rankings evaluation procedure.
    Restricted: 'admin' role ONLY.
    """
    from cron.daily_leaderboard_job import refresh_leaderboard

    try:
        result = refresh_leaderboard(dry_run=dry_run)
        return {
            "success": True,
            "admin_clerk_id": admin_payload.get("sub"),
            "result": result,
        }
    except Exception as exc:
        logger.exception("Failed to execute manual leaderboard refresh")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute leaderboard evaluation",
        ) from exc
>>>>>>> origin/main
