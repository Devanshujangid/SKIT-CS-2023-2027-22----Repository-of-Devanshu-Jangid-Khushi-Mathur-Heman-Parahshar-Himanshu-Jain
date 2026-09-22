"""
Deterministic prompt template and schemas for generating structured JSON study plans
based on student onboarding data (goals, hours, semester, subjects).
"""
import json
from typing import List, Literal, Optional, Union, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class SubjectInput(BaseModel):
    name: str = Field(..., description="Subject or course name")
    difficulty: Optional[str] = Field("medium", description="Difficulty level: easy, medium, hard")
    target_score: Optional[str] = Field(None, description="Target grade or goal for this subject")


class OnboardingDataInput(BaseModel):
    semester: int = Field(..., description="Current academic semester or year")
    study_hours_per_day: float = Field(..., description="Daily available study hours")
    goals: List[str] = Field(..., description="List of academic/career goals")
    subjects: List[SubjectInput] = Field(..., description="List of enrolled subjects")

    @field_validator("subjects", mode="before")
    @classmethod
    def normalize_subjects(cls, value):
        if isinstance(value, list):
            return [
                {"name": subject, "difficulty": "medium"}
                if isinstance(subject, str)
                else subject
                for subject in value
            ]
        return value

    @field_validator("goals", mode="before")
    @classmethod
    def normalize_goals(cls, value):
        if isinstance(value, str):
            return [value]
        return value


# ---------------------------------------------------------------------------
# Output Pydantic Schemas for Strict Response Validation
# ---------------------------------------------------------------------------

DayName = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
ActivityType = Literal["core_concept_study", "practice_problems", "lecture_review", "revision_quiz"]
PriorityLevel = Literal["high", "medium", "low"]


class PlanOverview(BaseModel):
    student_semester: int = Field(..., description="Academic semester of the student")
    daily_target_hours: float = Field(..., description="Target daily study hours")
    weekly_total_hours: float = Field(..., description="Total planned study hours for the week")
    primary_focus: str = Field(..., description="Primary academic goal/focus for the plan")
    strategy_summary: str = Field(..., description="Summary of the strategic approach")


class SessionItem(BaseModel):
    subject: str = Field(..., description="Name of the subject")
    topic: str = Field(..., description="Specific topic or unit to cover")
    duration_hours: float = Field(..., description="Session duration in hours")
    activity_type: ActivityType = Field(..., description="Type of study activity")
    priority: PriorityLevel = Field(..., description="Session priority level")


class DaySchedule(BaseModel):
    day: DayName = Field(..., description="Day of the week")
    total_hours: float = Field(..., description="Total allocated study hours for this day")
    sessions: List[SessionItem] = Field(default_factory=list, description="List of study sessions for the day")


class MonthlyMilestone(BaseModel):
    week: int = Field(..., description="Week number (1-4)")
    milestone: str = Field(..., description="High-level milestone description")
    key_deliverable: str = Field(..., description="Tangible deliverable or assessment")


class StudyPlanOutputSchema(BaseModel):
    plan_overview: PlanOverview
    weekly_schedule: List[DaySchedule]
    monthly_milestones: List[MonthlyMilestone]
    study_tips: List[str]

    @model_validator(mode="after")
    def validate_schedule_integrity(self):
        if not self.weekly_schedule:
            raise ValueError("weekly_schedule cannot be empty")
        return self


def validate_study_plan_output(data: dict) -> StudyPlanOutputSchema:
    """
    Validates a raw dictionary response against the strict StudyPlanOutputSchema Pydantic model.
    Throws ValidationError if the schema is violated.
    """
    return StudyPlanOutputSchema.model_validate(data)


STUDY_PLAN_SYSTEM_INSTRUCTION = """
You are an expert AI Academic Coach and Study Planner.
Your task is to convert student onboarding information into a deterministic, highly structured, 7-day personalized study plan.

CRITICAL INSTRUCTIONS:
1. OUTPUT FORMAT: Respond ONLY with a valid, raw JSON object adhering strictly to the JSON schema specified below.
2. DO NOT include markdown wrappers (such as ```json or ```), preamble, or postscript text.
3. TIME BALANCE: The sum of `duration_hours` for sessions on any day MUST NOT exceed the student's specified daily available study hours (`study_hours_per_day`).
4. SUBJECT COVERAGE: Every subject provided in the input must be addressed across the weekly schedule with frequency proportional to its difficulty.
5. DETERMINISM: Use consistent, structured activity types ('core_concept_study', 'practice_problems', 'lecture_review', 'revision_quiz') and priorities ('high', 'medium', 'low').

JSON SCHEMA SPECIFICATION:
{
  "plan_overview": {
    "student_semester": number,
    "daily_target_hours": number,
    "weekly_total_hours": number,
    "primary_focus": string,
    "strategy_summary": string
  },
  "weekly_schedule": [
    {
      "day": "Monday" | "Tuesday" | "Wednesday" | "Thursday" | "Friday" | "Saturday" | "Sunday",
      "total_hours": number,
      "sessions": [
        {
          "subject": string,
          "topic": string,
          "duration_hours": number,
          "activity_type": "core_concept_study" | "practice_problems" | "lecture_review" | "revision_quiz",
          "priority": "high" | "medium" | "low"
        }
      ]
    }
  ],
  "monthly_milestones": [
    {
      "week": number,
      "milestone": string,
      "key_deliverable": string
    }
  ],
  "study_tips": [string]
}
"""


def build_study_plan_prompt(data: OnboardingDataInput) -> str:
    """
    Constructs the deterministic user prompt with serialized onboarding data.
    """
    subjects_formatted = json.dumps([s.model_dump() for s in data.subjects], indent=2)
    goals_formatted = json.dumps(data.goals, indent=2)

    prompt = f"""
Student Onboarding Profile:
- Semester: {data.semester}
- Available Daily Study Hours: {data.study_hours_per_day} hours/day
- Goals: {goals_formatted}
- Enrolled Subjects:
{subjects_formatted}

Please generate the structured 7-day study plan according to the system instructions and exact JSON schema.
"""
    return prompt.strip()

