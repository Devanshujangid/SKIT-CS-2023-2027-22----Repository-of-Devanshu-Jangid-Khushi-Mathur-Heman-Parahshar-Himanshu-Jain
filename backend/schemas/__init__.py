"""
Pydantic Schemas Package for Smart Learning Planner API.
"""

from schemas.settings import (
    StudyHoursUpdateSchema,
    AcademicGoalsUpdateSchema,
    PasswordUpdateSchema,
    NotificationSettingsSchema,
    SettingsUpdateRequest,
    SettingsResponseSchema,
)

__all__ = [
    "StudyHoursUpdateSchema",
    "AcademicGoalsUpdateSchema",
    "PasswordUpdateSchema",
    "NotificationSettingsSchema",
    "SettingsUpdateRequest",
    "SettingsResponseSchema",
]
