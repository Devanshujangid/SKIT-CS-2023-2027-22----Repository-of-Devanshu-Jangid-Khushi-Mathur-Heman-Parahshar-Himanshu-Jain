"""
Pydantic Schemas for Admin CRUD Operations and Leaderboard API Responses.

Covers:
1. Admin Resource Management: Create, Update (PATCH), Response, List, and Delete schemas
   aligned with the Coursera/curated learning resource catalog.
2. Admin Student Management: Create, Update (PATCH), Record, List, and Delete schemas
   aligned with `users` and `student_profiles` tables.
3. Leaderboard API Responses: Privacy-preserving cohort ranking entries, badges,
   percentile standings, and timeframe-filtered response envelopes.
"""

from datetime import datetime, timezone
from typing import Any, List, Literal, Optional
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ===========================================================================
# Shared Constants & Normalization Helpers
# ===========================================================================

ResourceType = Literal["course", "video", "article", "documentation", "practice_set"]
DifficultyLevel = Literal["Beginner", "Intermediate", "Advanced", "All Levels"]
UserRole = Literal["student", "admin"]
DiagnosticStatus = Literal["On-Track", "Needs Revision", "At-Risk"]
LeaderboardTimeframe = Literal["weekly", "monthly", "semester", "all_time"]
LeaderboardMetric = Literal["xp_score", "adherence_rate", "logged_hours", "streak_days"]
BadgeTier = Literal["bronze", "silver", "gold", "platinum"]

_DIFFICULTY_MAP = {
    "beginner": "Beginner",
    "intermediate": "Intermediate",
    "advanced": "Advanced",
    "all levels": "All Levels",
    "all_levels": "All Levels",
    "conversant": "Intermediate",
}


def _normalize_string_list(value: Any, *, allow_empty: bool = True, field_name: str = "items") -> List[str]:
    """Normalizes a list or comma-separated string into deduplicated, trimmed strings."""
    if value is None:
        if allow_empty:
            return []
        raise ValueError(f"{field_name} cannot be None.")

    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        raw_items = [str(item).strip() for item in value if str(item).strip()]
    else:
        raise ValueError(f"{field_name} must be a list of strings or comma-separated string.")

    # Preserve order while deduplicating case-insensitively
    seen = set()
    deduped: List[str] = []
    for item in raw_items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    if not allow_empty and not deduped:
        raise ValueError(f"{field_name} must contain at least one non-empty entry.")
    return deduped


def _validate_http_url(value: str) -> str:
    """Validates that a resource URL uses http/https and includes a valid network host."""
    cleaned = value.strip()
    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            f"Invalid resource URL '{value}'. Must be a valid http:// or https:// URL."
        )
    return cleaned


def _normalize_difficulty(value: Any) -> str:
    """Normalizes difficulty labels to canonical title-cased values."""
    if not isinstance(value, str):
        raise ValueError("difficulty_level must be a string.")
    cleaned = value.strip()
    mapped = _DIFFICULTY_MAP.get(cleaned.lower())
    if mapped:
        return mapped
    return cleaned


# ===========================================================================
# 1. Admin Resource CRUD Schemas
# ===========================================================================

class AdminCreateResource(BaseModel):
    """
    Request payload for an administrator creating a curated learning resource.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Course or resource title (e.g., 'Operating Systems: Three Easy Pieces')",
    )
    description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Summary of syllabus coverage and learning outcomes",
    )
    url: str = Field(
        ...,
        max_length=1000,
        description="Canonical HTTP/HTTPS URL to the learning resource",
    )
    subject: str = Field(
        ...,
        min_length=2,
        max_length=120,
        description="Mapped academic subject (e.g., 'Operating Systems')",
    )
    provider: str = Field(
        default="Curated Academic",
        min_length=2,
        max_length=120,
        description="Issuing university, platform, or author",
    )
    difficulty_level: DifficultyLevel = Field(
        default="Intermediate",
        description="Target difficulty tier",
    )
    skills: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Skills or topic keywords used for TF-IDF indexing",
    )
    rating: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=5.0,
        description="Optional resource quality rating on a 0.0 - 5.0 scale",
    )
    estimated_hours: Optional[float] = Field(
        default=None,
        ge=0.1,
        le=500.0,
        description="Estimated completion time in hours",
    )
    resource_type: ResourceType = Field(
        default="course",
        description="Format of the learning resource",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this resource is visible in student recommendations",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return _validate_http_url(value)

    @field_validator("difficulty_level", mode="before")
    @classmethod
    def normalize_difficulty_level(cls, value: Any) -> str:
        return _normalize_difficulty(value)

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: Any) -> List[str]:
        return _normalize_string_list(value, allow_empty=True, field_name="skills")

    @field_validator("rating")
    @classmethod
    def round_rating(cls, value: Optional[float]) -> Optional[float]:
        return round(value, 2) if value is not None else None


class AdminUpdateResource(BaseModel):
    """
    Request payload for partially updating an existing learning resource (PATCH).
    At least one field must be provided.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=2, max_length=255)
    description: Optional[str] = Field(default=None, min_length=10, max_length=2000)
    url: Optional[str] = Field(default=None, max_length=1000)
    subject: Optional[str] = Field(default=None, min_length=2, max_length=120)
    provider: Optional[str] = Field(default=None, min_length=2, max_length=120)
    difficulty_level: Optional[DifficultyLevel] = Field(default=None)
    skills: Optional[List[str]] = Field(default=None, max_length=20)
    rating: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    estimated_hours: Optional[float] = Field(default=None, ge=0.1, le=500.0)
    resource_type: Optional[ResourceType] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: Optional[str]) -> Optional[str]:
        return _validate_http_url(value) if value is not None else None

    @field_validator("difficulty_level", mode="before")
    @classmethod
    def normalize_difficulty_level(cls, value: Any) -> Optional[str]:
        return _normalize_difficulty(value) if value is not None else None

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        return _normalize_string_list(value, allow_empty=True, field_name="skills")

    @field_validator("rating")
    @classmethod
    def round_rating(cls, value: Optional[float]) -> Optional[float]:
        return round(value, 2) if value is not None else None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdminUpdateResource":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided to update a resource.")
        return self


class AdminResourceResponse(BaseModel):
    """Serialized learning resource returned by Admin CRUD endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique resource identifier")
    title: str
    description: str
    url: str
    subject: str
    provider: str
    difficulty_level: DifficultyLevel
    skills: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    estimated_hours: Optional[float] = None
    resource_type: ResourceType
    is_active: bool
    created_by: Optional[str] = Field(default=None, description="Admin Clerk ID who created the resource")
    created_at: datetime
    updated_at: datetime


class AdminResourceListResponse(BaseModel):
    """Paginated list of curated resources for Admin management views."""
    success: bool = True
    total: int = Field(..., ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    resources: List[AdminResourceResponse] = Field(default_factory=list)


class AdminResourceDeleteResponse(BaseModel):
    """Confirmation payload after deleting a learning resource."""
    success: bool = True
    deleted_id: str
    message: str = "Learning resource deleted successfully"


# ===========================================================================
# 2. Admin Student CRUD Schemas
# ===========================================================================

class AdminCreateStudent(BaseModel):
    """
    Request payload for an administrator provisioning a student user and academic profile.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    clerk_id: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="External Clerk authentication subject identifier",
    )
    email: EmailStr = Field(..., description="Student university or personal email")
    full_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=120,
        description="Student display name",
    )
    role: UserRole = Field(default="student", description="RBAC role assignment")
    semester: int = Field(..., ge=1, le=8, description="Engineering semester (1-8)")
    study_hours_per_day: float = Field(
        ...,
        ge=0.5,
        le=16.0,
        description="Daily study hours capacity (0.5h - 16.0h)",
    )
    goals: List[str] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Academic goals list",
    )
    subjects: List[str] = Field(
        default_factory=list,
        max_length=15,
        description="Enrolled academic subjects",
    )
    onboarding_completed: bool = Field(default=True)

    @field_validator("study_hours_per_day")
    @classmethod
    def round_daily_hours(cls, value: float) -> float:
        return round(value, 2)

    @field_validator("goals", mode="before")
    @classmethod
    def normalize_goals(cls, value: Any) -> List[str]:
        return _normalize_string_list(value, allow_empty=False, field_name="goals")

    @field_validator("subjects", mode="before")
    @classmethod
    def normalize_subjects(cls, value: Any) -> List[str]:
        return _normalize_string_list(value, allow_empty=True, field_name="subjects")


class AdminUpdateStudent(BaseModel):
    """
    Request payload for an administrator updating a student's user or profile fields (PATCH).
    At least one field must be supplied.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    email: Optional[EmailStr] = Field(default=None)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    role: Optional[UserRole] = Field(default=None)
    semester: Optional[int] = Field(default=None, ge=1, le=8)
    study_hours_per_day: Optional[float] = Field(default=None, ge=0.5, le=16.0)
    goals: Optional[List[str]] = Field(default=None, min_length=1, max_length=10)
    subjects: Optional[List[str]] = Field(default=None, max_length=15)
    onboarding_completed: Optional[bool] = Field(default=None)
    is_suspended: Optional[bool] = Field(
        default=None,
        description="Administrative flag to suspend or reactivate student access",
    )
    admin_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional audit note explaining the administrative update",
    )

    @field_validator("study_hours_per_day")
    @classmethod
    def round_daily_hours(cls, value: Optional[float]) -> Optional[float]:
        return round(value, 2) if value is not None else None

    @field_validator("goals", mode="before")
    @classmethod
    def normalize_goals(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        return _normalize_string_list(value, allow_empty=False, field_name="goals")

    @field_validator("subjects", mode="before")
    @classmethod
    def normalize_subjects(cls, value: Any) -> Optional[List[str]]:
        if value is None:
            return None
        return _normalize_string_list(value, allow_empty=True, field_name="subjects")

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "AdminUpdateStudent":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided to update a student.")
        return self


class AdminStudentRecord(BaseModel):
    """Combined user, profile, and execution telemetry view for Admin roster/CRUD."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Internal user UUID")
    clerk_id: str
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = "student"
    semester: int = Field(..., ge=1, le=8)
    study_hours_per_day: float = Field(..., ge=0.5, le=16.0)
    goals: List[str] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)
    onboarding_completed: bool = True
    is_suspended: bool = False
    has_active_plan: bool = False
    total_tasks: int = Field(default=0, ge=0)
    completed_tasks: int = Field(default=0, ge=0)
    completion_rate: int = Field(default=0, ge=0, le=100)
    diagnostic_status: DiagnosticStatus = "On-Track"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AdminStudentMutationResponse(BaseModel):
    """Response envelope for Admin create/update student actions."""
    success: bool = True
    message: str
    student: AdminStudentRecord


class AdminStudentListResponse(BaseModel):
    """Paginated student roster response for Admin dashboard."""
    success: bool = True
    admin_clerk_id: str
    total_students: int = Field(..., ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    students: List[AdminStudentRecord] = Field(default_factory=list)


class AdminDeleteStudentResponse(BaseModel):
    """Confirmation payload after removing a student record."""
    success: bool = True
    deleted_user_id: str
    message: str = "Student record deleted successfully"


# ===========================================================================
# 3. Leaderboard API Response Schemas
# ===========================================================================

class LeaderboardBadge(BaseModel):
    """Achievement badge earned by a student for consistent study execution."""
    badge_id: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=80)
    tier: BadgeTier = "bronze"


class LeaderboardEntry(BaseModel):
    """
    A single ranked row on the student leaderboard.
    Excludes sensitive PII (no raw email or clerk_id exposed to peers).
    """
    model_config = ConfigDict(from_attributes=True)

    rank: int = Field(..., ge=1, description="1-based cohort leaderboard rank")
    student_id: str = Field(..., description="Internal anonymized student identifier")
    display_name: str = Field(..., min_length=1, max_length=100)
    semester: int = Field(..., ge=1, le=8)
    primary_focus: Optional[str] = Field(default=None, max_length=120)
    xp_score: int = Field(..., ge=0, description="Weighted gamification score")
    logged_hours: float = Field(..., ge=0.0, description="Verified actual study hours")
    scheduled_hours: float = Field(..., ge=0.0, description="Planned study hours in timeframe")
    adherence_rate: int = Field(..., ge=0, le=100, description="Percentage adherence (0-100)")
    completed_tasks: int = Field(..., ge=0)
    streak_days: int = Field(default=0, ge=0, description="Consecutive days meeting study target")
    rank_delta: int = Field(default=0, description="Rank change vs previous period (+ve = climbed)")
    badges: List[LeaderboardBadge] = Field(default_factory=list)
    is_current_user: bool = Field(default=False, description="True for the requesting student's row")

    @field_validator("logged_hours", "scheduled_hours")
    @classmethod
    def round_hours(cls, value: float) -> float:
        return round(value, 2)


class LeaderboardUserStanding(BaseModel):
    """Summary of the authenticated student's personal position on the leaderboard."""
    rank: Optional[int] = Field(default=None, ge=1)
    percentile: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    xp_score: int = Field(default=0, ge=0)
    points_to_next_rank: int = Field(default=0, ge=0)
    entry: Optional[LeaderboardEntry] = None


class LeaderboardResponse(BaseModel):
    """
    Top-level API response schema for GET /api/v1/leaderboard.
    Enforces ranking monotonicity and participant count consistency.
    """
    success: bool = True
    timeframe: LeaderboardTimeframe = "weekly"
    sorted_by: LeaderboardMetric = "xp_score"
    semester_filter: Optional[int] = Field(default=None, ge=1, le=8)
    subject_filter: Optional[str] = Field(default=None, max_length=120)
    total_participants: int = Field(..., ge=0)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    current_user_standing: Optional[LeaderboardUserStanding] = None
    entries: List[LeaderboardEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_ranking_integrity(self) -> "LeaderboardResponse":
        if self.total_participants < len(self.entries):
            raise ValueError(
                f"total_participants ({self.total_participants}) cannot be less than entries count ({len(self.entries)})."
            )

        for idx in range(1, len(self.entries)):
            prev_rank = self.entries[idx - 1].rank
            curr_rank = self.entries[idx].rank
            if curr_rank < prev_rank:
                raise ValueError(
                    f"Leaderboard entries must be ordered by non-decreasing rank (found rank {curr_rank} after {prev_rank})."
                )
        return self

