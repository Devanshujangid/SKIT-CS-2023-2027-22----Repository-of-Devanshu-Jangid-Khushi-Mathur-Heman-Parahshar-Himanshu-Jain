"""
Pydantic Schemas for Notifications Subsystem.

Validates notification items, lists, status updates, and creation payloads.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class NotificationCreateRequest(BaseModel):
    """Payload for creating a notification."""
    title: Optional[str] = Field(default=None, max_length=255, description="Notification header/title")
    message: str = Field(..., min_length=1, max_length=1000, description="Content of the notification")
    type: str = Field(default="system", max_length=50, description="Category of notification: system, reminder, alert, rebalance, achievement")


class NotificationResponse(BaseModel):
    """Single notification representation."""
    id: str
    user_id: str
    type: str
    title: Optional[str] = None
    message: str
    description: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    """Response containing list of notifications and unread counters."""
    success: bool = True
    unread_count: int = Field(..., ge=0, description="Total unread notifications for current student")
    total_count: int = Field(..., ge=0, description="Total notifications returned in query")
    notifications: List[NotificationResponse] = Field(default_factory=list)


class NotificationStatusUpdateResponse(BaseModel):
    """Response after marking a notification as read."""
    success: bool = True
    message: str = "Notification marked as read"
    notification: NotificationResponse


class NotificationBulkReadResponse(BaseModel):
    """Response after marking multiple/all notifications as read."""
    success: bool = True
    updated_count: int = Field(..., ge=0)
    message: str = "Notifications marked as read"
