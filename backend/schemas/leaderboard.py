"""
Pydantic Schemas for Leaderboard and Student Goal Status Tracking.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


VALID_GOAL_STATUSES = {"ahead", "on_track", "behind", "completed", "paused"}


class LeaderboardEntry(BaseModel):
    """
    Representation of an individual student's standing on the Leaderboard.
    """
    rank: int = Field(..., ge=1, description="Rank position based on study hours and completion rate")
    user_id: str = Field(..., description="Student internal UUID")
    display_name: str = Field(..., description="Privacy-preserving student identifier")
    semester: int = Field(..., ge=1, le=8, description="Enrolled semester")
    target_hours_per_day: float = Field(..., ge=0.0, description="Daily target study hours")
    goal_status: str = Field("on_track", description="Configured or persisted goal status")
    calculated_goal_status: str = Field("on_track", description="Dynamically computed goal status from momentum")
    primary_goals: List[str] = Field(default_factory=list, description="Primary student academic objectives")
    total_tasks: int = Field(0, ge=0, description="Total study sessions or tasks assigned")
    completed_tasks: int = Field(0, ge=0, description="Total study sessions or tasks completed")
    planned_study_hours: float = Field(0.0, ge=0.0, description="Total scheduled study duration (hours)")
    actual_study_hours: float = Field(0.0, ge=0.0, description="Total verified completed study hours")
    completion_rate: float = Field(0.0, ge=0.0, le=100.0, description="Percentage of assigned tasks completed")


class LeaderboardResponse(BaseModel):
    """
    Structured response payload for the Leaderboard API.
    """
    success: bool = True
    total_students: int = Field(..., ge=0, description="Total number of students ranked")
    semester_filter: Optional[int] = Field(None, description="Semester filter applied if any")
    leaderboard: List[LeaderboardEntry] = Field(default_factory=list, description="Ranked student entries")
    current_user_rank: Optional[LeaderboardEntry] = Field(None, description="Leaderboard standing of the requesting user")


class UpdateGoalStatusRequest(BaseModel):
    """
    Payload for updating a student's personal goal status.
    """
    goal_status: str = Field(
        ...,
        description="Goal progress status: 'ahead', 'on_track', 'behind', 'completed', 'paused'"
    )

    @field_validator("goal_status")
    @classmethod
    def validate_goal_status(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in VALID_GOAL_STATUSES:
            raise ValueError(
                f"Invalid goal_status '{value}'. Allowed values: {sorted(VALID_GOAL_STATUSES)}"
            )
        return cleaned


class UpdateGoalStatusResponse(BaseModel):
    """
    Response acknowledging updated goal status.
    """
    success: bool = True
    user_id: str
    goal_status: str
    message: str = "Goal status updated successfully"

