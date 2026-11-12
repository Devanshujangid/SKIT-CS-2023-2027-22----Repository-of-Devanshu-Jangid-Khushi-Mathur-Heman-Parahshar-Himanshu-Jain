"""
Pydantic Schemas for Learning Resources Catalog and Admin Management.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator


VALID_CATEGORIES = {"course", "video", "book", "documentation", "tool", "article"}
VALID_DIFFICULTIES = {"beginner", "intermediate", "advanced", "all_levels"}


class ResourceCreateRequest(BaseModel):
    """
    Schema for creating a new learning resource by an administrator.
    """
    title: str = Field(..., min_length=2, max_length=255, description="Resource title")
    description: Optional[str] = Field(None, max_length=2000, description="Detailed resource summary")
    url: str = Field(..., min_length=5, max_length=1000, description="Direct URL to resource")
    category: str = Field("course", description="Category: 'course', 'video', 'book', 'documentation', 'tool', 'article'")
    subject: Optional[str] = Field(None, max_length=150, description="Academic subject area (e.g. Operating Systems)")
    provider: Optional[str] = Field(None, max_length=150, description="Provider/Platform (e.g. Coursera, NPTEL, YouTube)")
    difficulty: Optional[str] = Field("intermediate", description="Difficulty level ('beginner', 'intermediate', 'advanced')")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Quality rating on 5.0 scale")
    tags: List[str] = Field(default_factory=list, description="Searchable keyword tags")
    is_active: bool = Field(True, description="Whether resource is visible to students")

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{value}'. Allowed: {sorted(VALID_CATEGORIES)}")
        return cleaned

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return "intermediate"
        cleaned = value.strip().lower()
        if cleaned not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty '{value}'. Allowed: {sorted(VALID_DIFFICULTIES)}")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return cleaned


class ResourceUpdateRequest(BaseModel):
    """
    Schema for updating an existing learning resource. All fields optional.
    """
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    url: Optional[str] = Field(None, min_length=5, max_length=1000)
    category: Optional[str] = None
    subject: Optional[str] = Field(None, max_length=150)
    provider: Optional[str] = Field(None, max_length=150)
    difficulty: Optional[str] = None
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{value}'. Allowed: {sorted(VALID_CATEGORIES)}")
        return cleaned

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if cleaned not in VALID_DIFFICULTIES:
            raise ValueError(f"Invalid difficulty '{value}'. Allowed: {sorted(VALID_DIFFICULTIES)}")
        return cleaned

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        if not (cleaned.startswith("http://") or cleaned.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return cleaned


class ResourceResponse(BaseModel):
    """
    Structured learning resource output schema.
    """
    id: str
    title: str
    description: Optional[str] = None
    url: str
    category: str
    subject: Optional[str] = None
    provider: Optional[str] = None
    difficulty: Optional[str] = "intermediate"
    rating: Optional[float] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ResourceListResponse(BaseModel):
    """
    Paginated list of learning resources.
    """
    success: bool = True
    total: int
    count: int
    resources: List[ResourceResponse]

