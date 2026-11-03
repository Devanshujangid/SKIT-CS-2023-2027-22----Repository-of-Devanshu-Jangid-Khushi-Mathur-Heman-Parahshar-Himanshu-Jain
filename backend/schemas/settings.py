"""
Pydantic Schemas for Settings API.

Validates updates to:
1. Daily study hours, pacing, and time availability constraints.
2. Academic goals, focus areas, target CGPA, and semester enrollments.
3. User password changes with strict enterprise security policies.
4. Notification preferences and AI diagnostic toggles.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator


# Common weak or trivially guessed passwords to reject
COMMON_WEAK_PASSWORDS = {
    "password",
    "password123",
    "12345678",
    "123456789",
    "qwerty123",
    "admin123",
    "skit1234",
    "letmein123",
}


# ===========================================================================
# 1. Study Hours & Schedule Constraints Schema
# ===========================================================================

class StudyHoursUpdateSchema(BaseModel):
    """
    Validates daily study hours capacity, session pacing, and time window constraints.
    """
    study_hours_per_day: float = Field(
        ...,
        ge=0.5,
        le=16.0,
        description="Daily available study hours (must be between 0.5h and 16.0h)"
    )
    max_consecutive_hours: Optional[float] = Field(
        2.0,
        ge=0.5,
        le=6.0,
        description="Maximum continuous study duration before mandatory rest interval"
    )
    preferred_time_slots: Optional[List[str]] = Field(
        default_factory=lambda: ["Morning (06:00 - 09:00)", "Evening (18:00 - 21:00)"],
        description="Preferred time windows for study blocks (e.g., Morning, Afternoon, Evening, Night)"
    )
    session_pacing: Optional[str] = Field(
        "Deep Work (50m study / 10m break)",
        description="Session pacing style (e.g., Pomodoro, Deep Work, Standard Blocks)"
    )
    enforce_strict_ceiling: Optional[bool] = Field(
        True,
        description="Invariant: Prevents schedule total hours from overflowing daily limit"
    )
    forward_only_catchup: Optional[bool] = Field(
        True,
        description="Invariant: Catch-up tasks only allocated to current or future calendar days"
    )

    @field_validator("study_hours_per_day")
    @classmethod
    def round_hours(cls, value: float) -> float:
        return round(value, 2)

    @field_validator("preferred_time_slots", mode="before")
    @classmethod
    def normalize_time_slots(cls, value: Any) -> List[str]:
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        if isinstance(value, list):
            return [str(s).strip() for s in value if str(s).strip()]
        return []

    @model_validator(mode="after")
    def validate_consecutive_hours_not_exceeding_daily(self) -> "StudyHoursUpdateSchema":
        if self.max_consecutive_hours and self.max_consecutive_hours > self.study_hours_per_day:
            raise ValueError(
                f"max_consecutive_hours ({self.max_consecutive_hours}h) cannot exceed total study_hours_per_day ({self.study_hours_per_day}h)"
            )
        return self


# ===========================================================================
# 2. Academic Goals & Curricular Preferences Schema
# ===========================================================================

class AcademicGoalsUpdateSchema(BaseModel):
    """
    Validates updates to student academic objectives, target scores, CGPA, and subjects.
    """
    goals: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="List of academic and career objectives (1-10 goals)"
    )
    target_goal_summary: Optional[str] = Field(
        None,
        max_length=500,
        description="High-level target summary (e.g., 'Targeting 8.5+ CGPA and strong GATE CSE core foundation')"
    )
    primary_focus: Optional[str] = Field(
        None,
        max_length=120,
        description="Primary focus subject or core academic domain"
    )
    semester: Optional[int] = Field(
        None,
        ge=1,
        le=8,
        description="Current engineering semester (1 to 8)"
    )
    target_cgpa: Optional[float] = Field(
        None,
        ge=0.0,
        le=10.0,
        description="Target cumulative grade point average (0.0 to 10.0 scale)"
    )
    subjects: Optional[List[str]] = Field(
        default_factory=list,
        description="List of currently enrolled subjects"
    )

    @field_validator("goals", mode="before")
    @classmethod
    def normalize_goals(cls, value: Any) -> List[str]:
        if isinstance(value, str):
            cleaned = [g.strip() for g in value.split(",") if g.strip()]
            if not cleaned:
                raise ValueError("At least one non-empty goal is required")
            return cleaned
        if isinstance(value, list):
            cleaned = [str(g).strip() for g in value if str(g).strip()]
            if not cleaned:
                raise ValueError("Goals list cannot be empty or contain only whitespace")
            return cleaned
        raise ValueError("Goals must be provided as a non-empty string or list of strings")

    @field_validator("subjects", mode="before")
    @classmethod
    def normalize_subjects(cls, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(s).strip() for s in value if str(s).strip()]
        if isinstance(value, str):
            return [s.strip() for s in value.split(",") if s.strip()]
        return []

    @field_validator("target_cgpa")
    @classmethod
    def validate_target_cgpa(cls, value: Optional[float]) -> Optional[float]:
        if value is not None:
            return round(value, 2)
        return value


# ===========================================================================
# 3. Password & Security Verification Schema
# ===========================================================================

class PasswordUpdateSchema(BaseModel):
    """
    Enforces enterprise-grade security rules for user password updates:
    - Minimum 8 characters, maximum 128 characters.
    - Requires at least 1 uppercase letter (A-Z).
    - Requires at least 1 lowercase letter (a-z).
    - Requires at least 1 numeric digit (0-9).
    - Requires at least 1 special character (!@#$%^&*()_+-=[]{}|;:,.<>?).
    - Rejects common weak passwords.
    - Prevents reusing the current password.
    - Requires exact confirmation match.
    """
    current_password: str = Field(
        ...,
        min_length=1,
        description="Current active password for identity verification"
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New secure password"
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirmation of the new password"
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, password: str) -> str:
        # Check against common weak passwords
        if password.lower() in COMMON_WEAK_PASSWORDS:
            raise ValueError("The proposed password is too common or easily guessable. Please choose a stronger password.")

        # Length check
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if len(password) > 128:
            raise ValueError("Password cannot exceed 128 characters")

        # Uppercase letter check
        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter (A-Z)")

        # Lowercase letter check
        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter (a-z)")

        # Digit check
        if not re.search(r"\d", password):
            raise ValueError("Password must contain at least one numeric digit (0-9)")

        # Special character check
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?/~`]", password):
            raise ValueError("Password must contain at least one special character (e.g. !@#$%^&*)")

        return password

    @model_validator(mode="after")
    def validate_password_confirmation_and_difference(self) -> "PasswordUpdateSchema":
        # Check matching confirmation
        if self.new_password != self.confirm_password:
            raise ValueError("New password and confirm password do not match")

        # Check difference from current password
        if self.current_password == self.new_password:
            raise ValueError("New password cannot be the same as your current password")

        return self


# ===========================================================================
# 4. Notifications & Telemetry Toggles Schema
# ===========================================================================

class NotificationSettingsSchema(BaseModel):
    """
    Validates student notification preferences and reminder intervals.
    """
    daily_digest: bool = Field(True, description="Receive daily morning study agenda digest")
    missed_session_alerts: bool = Field(True, description="Immediate alerts when a scheduled session is missed")
    email_notifications: bool = Field(False, description="Send periodic progress updates via email")
    lead_time_minutes: int = Field(15, ge=0, le=120, description="Minutes before session start to trigger reminder")


# ===========================================================================
# 5. Unified Settings Update Request & Response Schemas
# ===========================================================================

class SettingsUpdateRequest(BaseModel):
    """
    Consolidated request model allowing partial or combined updates across all settings domains.
    """
    study_hours: Optional[StudyHoursUpdateSchema] = Field(
        None,
        description="Updated study capacity, time slots, and schedule limits"
    )
    academic_goals: Optional[AcademicGoalsUpdateSchema] = Field(
        None,
        description="Updated academic goals, focus subjects, and target CGPA"
    )
    security: Optional[PasswordUpdateSchema] = Field(
        None,
        description="Password change request with verification"
    )
    notifications: Optional[NotificationSettingsSchema] = Field(
        None,
        description="Updated notification and reminder preferences"
    )

    @model_validator(mode="after")
    def validate_at_least_one_field_provided(self) -> "SettingsUpdateRequest":
        if (
            self.study_hours is None
            and self.academic_goals is None
            and self.security is None
            and self.notifications is None
        ):
            raise ValueError("At least one settings category (study_hours, academic_goals, security, or notifications) must be provided for update")
        return self


class SettingsResponseSchema(BaseModel):
    """
    Standardized API response for settings operations.
    """
    success: bool = True
    message: str = "Settings updated successfully"
    updated_fields: List[str] = Field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
