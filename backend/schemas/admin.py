"""
Pydantic Schemas for Admin Student Account Controls and Global Subjects Catalog.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


VALID_STUDENT_STATUSES = {"active", "suspended", "pending"}


class StudentStatusUpdateRequest(BaseModel):
    """
    Request payload to change student account status (suspend / activate).
    """
    status: str = Field(..., description="Account status: 'active', 'suspended', 'pending'")
    reason: Optional[str] = Field(None, max_length=500, description="Optional administrative justification")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in VALID_STUDENT_STATUSES:
            raise ValueError(f"Invalid status '{value}'. Allowed: {sorted(VALID_STUDENT_STATUSES)}")
        return cleaned


class StudentAccountItem(BaseModel):
    id: str
    clerk_id: str
    email: str
    role: str
    status: str
    semester: int = 1
    study_hours_per_day: float = 2.0
    goals: List[str] = Field(default_factory=list)
    subjects: List[str] = Field(default_factory=list)
    has_active_plan: bool = False
    total_tasks: int = 0
    completed_tasks: int = 0
    completion_rate: float = 0.0
    created_at: Optional[str] = None


class StudentListResponse(BaseModel):
    success: bool = True
    total_students: int
    count: int
    students: List[StudentAccountItem]


class SubjectCreateRequest(BaseModel):
    """
    Request payload to create a new university curriculum subject.
    """
    code: str = Field(..., min_length=2, max_length=50, description="Subject code (e.g. '5CS4-01', 'CS501')")
    name: str = Field(..., min_length=2, max_length=200, description="Full subject title (e.g. 'Operating Systems')")
    semester: int = Field(..., ge=1, le=8, description="Engineering semester (1-8)")
    department: str = Field("Computer Science", max_length=120, description="Academic department")
    credits: float = Field(3.0, ge=0.5, le=10.0, description="Academic credits")
    description: Optional[str] = Field(None, max_length=1000, description="Curriculum description")
    is_active: bool = Field(True, description="Whether subject is active for student enrollment")

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Subject code cannot be empty")
        return cleaned


class SubjectUpdateRequest(BaseModel):
    """
    Request payload to update subject details.
    """
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    semester: Optional[int] = Field(None, ge=1, le=8)
    department: Optional[str] = Field(None, max_length=120)
    credits: Optional[float] = Field(None, ge=0.5, le=10.0)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Subject code cannot be empty")
        return cleaned


class SubjectResponse(BaseModel):
    id: str
    code: str
    name: str
    semester: int
    department: str
    credits: float
    description: Optional[str] = None
    is_active: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SubjectListResponse(BaseModel):
    success: bool = True
    total: int
    count: int
    subjects: List[SubjectResponse]

