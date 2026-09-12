"""
Deterministic prompt template and schemas for generating structured JSON study plans
based on student onboarding data (goals, hours, semester, subjects).
"""
import json
from typing import List, Optional
from pydantic import BaseModel, Field


class SubjectInput(BaseModel):
    name: str = Field(..., description="Subject or course name")
    difficulty: Optional[str] = Field("medium", description="Difficulty level: easy, medium, hard")
    target_score: Optional[str] = Field(None, description="Target grade or goal for this subject")


class OnboardingDataInput(BaseModel):
    semester: int = Field(..., description="Current academic semester or year")
    study_hours_per_day: float = Field(..., description="Daily available study hours")
    goals: List[str] = Field(..., description="List of academic/career goals")
    subjects: List[SubjectInput] = Field(..., description="List of enrolled subjects")


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
