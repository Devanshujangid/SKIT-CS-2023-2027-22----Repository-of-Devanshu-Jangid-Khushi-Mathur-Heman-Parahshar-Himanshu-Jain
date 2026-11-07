import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_admin, verify_clerk_token
from database import get_db, get_or_create_user
from services.notification_engine import notification_engine
from schemas.notifications import (
    AdminBroadcastNotificationRequest,
    AdminBroadcastNotificationResponse,
    NotificationBulkReadResponse,
    NotificationCreateRequest,
    NotificationListResponse,
    NotificationStatusUpdateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/notifications",
    tags=["Notifications"],
)


def get_authenticated_user_id(user_data: dict) -> str:
    """Resolve the authenticated Clerk user to the internal database UUID."""
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


# ============================================================
# GET /api/v1/notifications
# ============================================================

@router.get("", response_model=NotificationListResponse)
async def get_notifications(
    unread_only: bool = Query(False, description="Filter for unread notifications only"),
    limit: int = Query(50, ge=1, le=100, description="Max notifications to retrieve"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Retrieve notifications for the authenticated student.
    Supports unread filtering, pagination, and recency ordering.
    """
    try:
        db = get_db()
        user_id = get_authenticated_user_id(user_data)

        # 1. Calculate unread count for badge indicators
        unread_query = (
            db.table("notifications")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("is_read", False)
            .execute()
        )
        unread_count = (
            unread_query.count
            if hasattr(unread_query, "count") and unread_query.count is not None
            else len(unread_query.data or [])
        )

        # 2. Query notifications with optional filtering & pagination
        query = (
            db.table("notifications")
            .select("id, user_id, type, title, message, is_read, read_at, created_at")
            .eq("user_id", user_id)
        )

        if unread_only:
            query = query.eq("is_read", False)

        result = (
            query.order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        items = result.data or []
        for item in items:
            if not item.get("description"):
                item["description"] = item.get("message")

        return {
            "success": True,
            "unread_count": unread_count,
            "total_count": len(items),
            "notifications": items,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch notifications for user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch notifications",
        ) from exc


# ============================================================
# POST /api/v1/notifications
# ============================================================

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_notification(
    payload: NotificationCreateRequest,
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Create a new notification for the authenticated student.
    Can be invoked by system events, rebalance triggers, or reminders.
    """
    try:
        db = get_db()
        user_id = get_authenticated_user_id(user_data)
        now = datetime.now(timezone.utc).isoformat()

        insert_data = {
            "user_id": user_id,
            "type": payload.type.strip().lower() if payload.type else "system",
            "title": payload.title.strip() if payload.title else None,
            "message": payload.message.strip(),
            "is_read": False,
            "created_at": now,
        }

        result = (
            db.table("notifications")
            .insert(insert_data)
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create notification",
            )

        return {
            "success": True,
            "message": "Notification created successfully",
            "notification": result.data[0],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to create notification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create notification",
        ) from exc


# ============================================================
# PATCH /api/v1/notifications/read-all
# ============================================================

@router.patch("/read-all", response_model=NotificationBulkReadResponse)
@router.post("/mark-all-read", response_model=NotificationBulkReadResponse)
async def mark_all_notifications_as_read(
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Mark all unread notifications as read for the authenticated student.
    """
    try:
        db = get_db()
        user_id = get_authenticated_user_id(user_data)
        now = datetime.now(timezone.utc).isoformat()

        result = (
            db.table("notifications")
            .update({
                "is_read": True,
                "read_at": now,
            })
            .eq("user_id", user_id)
            .eq("is_read", False)
            .select("id")
            .execute()
        )

        updated_rows = result.data or []

        return {
            "success": True,
            "updated_count": len(updated_rows),
            "message": f"{len(updated_rows)} notification(s) marked as read",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to mark all notifications as read")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark notifications as read",
        ) from exc


# ============================================================
# PATCH /api/v1/notifications/{id}/read
# ============================================================

@router.patch("/{id}/read", response_model=NotificationStatusUpdateResponse)
async def mark_notification_as_read(
    id: str,
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Mark a specific notification as read.
    Enforces student ownership to prevent unauthorized status changes.
    """
    try:
        notification_uuid = str(UUID(id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid notification ID format. Must be a valid UUID.",
        )

    try:
        db = get_db()
        user_id = get_authenticated_user_id(user_data)
        now = datetime.now(timezone.utc).isoformat()

        result = (
            db.table("notifications")
            .update({
                "is_read": True,
                "read_at": now,
            })
            .eq("id", notification_uuid)
            .eq("user_id", user_id)
            .select()
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        return {
            "success": True,
            "message": "Notification marked as read",
            "notification": result.data[0],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to mark notification %s as read", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update notification status",
        ) from exc


# ============================================================
# DELETE /api/v1/notifications/{id}
# ============================================================

@router.delete("/{id}")
async def delete_notification(
    id: str,
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Delete a specific notification belonging to the authenticated student.
    """
    try:
        notification_uuid = str(UUID(id))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid notification ID format. Must be a valid UUID.",
        )

    try:
        db = get_db()
        user_id = get_authenticated_user_id(user_data)

        result = (
            db.table("notifications")
            .delete()
            .eq("id", notification_uuid)
            .eq("user_id", user_id)
            .select("id")
            .execute()
        )

        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found",
            )

        return {
            "success": True,
            "message": "Notification deleted successfully",
            "id": notification_uuid,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to delete notification %s", id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete notification",
        ) from exc


# ============================================================
# POST /api/v1/notifications/dispatch-daily
# ============================================================

@router.post("/dispatch-daily")
async def trigger_daily_notification_dispatch(
    dry_run: bool = Query(False, description="Simulate evaluation without inserting rows"),
    batch: bool = Query(False, description="Run batch dispatch for all students (admin only) or current student"),
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Automated Notification Engine trigger.
    Evaluates 'Upcoming Exams' and 'Unresolved Weak Topics'.
    Pushes deterministic study alerts into the notifications table.
    """
    try:
        db = get_db()
        user_id = get_authenticated_user_id(user_data)
        role = user_data.get("role", "student")

        if batch:
            if role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Batch evaluation across all students requires admin role.",
                )
            result = notification_engine.run_daily_notification_dispatch(db=db, dry_run=dry_run)
            return result

        result = notification_engine.dispatch_for_student(user_id=user_id, db=db, dry_run=dry_run)
        return {
            "success": True,
            "dry_run": dry_run,
            "result": result,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to execute daily notification dispatch")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to execute notification dispatch",
        ) from exc


# ============================================================
# POST /api/v1/notifications/admin/broadcast
# ============================================================

@router.post(
    "/admin/broadcast",
    response_model=AdminBroadcastNotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def admin_broadcast_notification(
    payload: AdminBroadcastNotificationRequest,
    admin_payload: dict = Depends(require_admin),
):
    """
    Push manual system-wide or cohort-targeted alerts to students.
    Enforces strict Role-Based Access Control (RBAC): restricted to 'admin'.
    """
    admin_sub = admin_payload.get("sub")
    logger.info("Admin %s initiating manual notification broadcast: '%s'", admin_sub, payload.title)

    try:
        db = get_db()

        # 1. Resolve target student recipients
        if payload.target_user_ids:
            query = db.table("users").select("id, email, clerk_id, role")
            # Filter targeted user UUIDs
            users_res = query.in_("id", payload.target_user_ids).execute()
        elif payload.target_role == "all":
            users_res = db.table("users").select("id, email, clerk_id, role").execute()
        else:
            # Default: all students
            users_res = db.table("users").select("id, email, clerk_id, role").eq("role", "student").execute()

        target_users = users_res.data or []
        if not target_users:
            # Fallback: if no users with explicit role='student' exist, broadcast to all users
            all_users_res = db.table("users").select("id, email, clerk_id, role").execute()
            target_users = all_users_res.data or []

        if not target_users:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No eligible student recipients found to receive broadcast",
            )

        # 2. Build notification rows
        now = datetime.now(timezone.utc).isoformat()
        clean_title = payload.title.strip()
        clean_message = payload.message.strip()
        clean_type = payload.type.strip().lower() if payload.type else "system"

        rows = [
            {
                "user_id": str(u["id"]),
                "type": clean_type,
                "title": clean_title,
                "message": clean_message,
                "is_read": False,
                "created_at": now,
            }
            for u in target_users
        ]

        # 3. Batch insert notifications
        insert_res = db.table("notifications").insert(rows).execute()
        inserted_rows = insert_res.data or rows

        logger.info(
            "Admin broadcast successful: '%s' sent to %d student(s)",
            clean_title,
            len(inserted_rows),
        )

        return {
            "success": True,
            "message": f"Successfully broadcast notification to {len(inserted_rows)} student(s)",
            "recipient_count": len(inserted_rows),
            "title": clean_title,
            "type": clean_type,
            "timestamp": now,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to broadcast admin notification")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast notification",
        ) from exc


# ============================================================
# GET /api/v1/notifications/admin/broadcasts
# ============================================================

@router.get("/admin/broadcasts")
async def get_admin_recent_broadcasts(
    limit: int = Query(20, ge=1, le=100),
    admin_payload: dict = Depends(require_admin),
):
    """
    Retrieve recently broadcast notifications for admin dashboard monitoring.
    Restricted to 'admin' role.
    """
    try:
        db = get_db()
        result = (
            db.table("notifications")
            .select("id, type, title, message, created_at, is_read, user_id")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )

        items = result.data or []
        return {
            "success": True,
            "count": len(items),
            "broadcasts": items,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch recent admin broadcasts")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch broadcast history",
        ) from exc


