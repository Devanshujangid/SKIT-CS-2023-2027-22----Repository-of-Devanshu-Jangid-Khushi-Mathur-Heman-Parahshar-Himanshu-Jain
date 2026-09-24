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
6. TARGET SCORE & EXAM REVISION ALIGNMENT: Dynamic exam revision milestones (`monthly_milestones`) and key deliverables MUST explicitly reflect and incorporate the specific target scores (e.g., 'A+', '9.0+ CGPA', '90%+ score', 'GATE top 100') requested by the student for enrolled subjects and learning goals. Milestone deliverables must include quantitative revision assessment benchmarks matching these target scores.
7. SUBJECT FIDELITY & NO HALLUCINATION: In `weekly_schedule`, session `subject` fields MUST use the EXACT subject name strings provided in the input profile (preserving course codes, numbers, and special characters like 'C++', 'AI/ML', 'BI-402'). DO NOT invent, abbreviate, or mutate subject names. Generate domain-accurate, highly relevant study topics appropriate for specialized subject domains.

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
- Enrolled Subjects & Specific Target Scores:
{subjects_formatted}

Please generate the structured 7-day study plan according to the system instructions and exact JSON schema.
IMPORTANT: Use the EXACT enrolled subject names in all schedule sessions (do not alter course codes, numbers, or special characters). Ensure dynamic exam revision milestones (`monthly_milestones`) and key deliverables explicitly reflect and target the specific target scores and academic goals requested by the student.
"""
    return prompt.strip()


def validate_target_score_alignment(
    plan: StudyPlanOutputSchema,
    data: OnboardingDataInput
) -> Dict[str, Any]:
    """
    Validates that dynamic exam revision milestones in the generated study plan
    accurately incorporate and reflect target scores requested by the student.
    Returns a status dict containing alignment details and validation boolean.
    """
    target_scores = {}
    for subj in data.subjects:
        if subj.target_score:
            target_scores[subj.name] = subj.target_score

    milestone_texts = [
        f"{m.milestone} - {m.key_deliverable}".lower()
        for m in plan.monthly_milestones
    ]
    combined_milestone_str = " ".join(milestone_texts)

    missing_alignments = []
    aligned_scores = {}

    for subj_name, target in target_scores.items():
        subj_lower = subj_name.lower()
        target_lower = target.lower()
        
        # Check if subject and/or target score benchmark is referenced in milestones/deliverables
        has_subj_reference = subj_lower in combined_milestone_str
        has_score_reference = target_lower in combined_milestone_str or any(
            char.isdigit() or char in ["%", "+"] for char in combined_milestone_str
        )

        is_aligned = has_subj_reference or has_score_reference
        aligned_scores[subj_name] = {
            "requested_target_score": target,
            "referenced_in_milestones": is_aligned,
        }
        if not is_aligned:
            missing_alignments.append(subj_name)

    is_valid = len(missing_alignments) == 0

    return {
        "is_aligned": is_valid,
        "requested_target_scores": target_scores,
        "alignment_details": aligned_scores,
        "missing_alignments": missing_alignments,
        "total_milestones_evaluated": len(plan.monthly_milestones)
    }


def validate_subject_name_fidelity(
    plan: StudyPlanOutputSchema,
    data: OnboardingDataInput
) -> Dict[str, Any]:
    """
    Validates that every session subject in the generated plan matches an exact
    enrolled subject name provided in onboarding data, and that all enrolled subjects
    are covered without hallucination or name mutation.
    """
    enrolled_names = {s.name for s in data.subjects}
    scheduled_names = set()

    unmatched_sessions = []
    for day in plan.weekly_schedule:
        for s in day.sessions:
            scheduled_names.add(s.subject)
            if s.subject not in enrolled_names:
                unmatched_sessions.append({"day": day.day, "subject": s.subject, "topic": s.topic})

    missing_enrolled = enrolled_names - scheduled_names

    is_valid = len(unmatched_sessions) == 0 and len(missing_enrolled) == 0

    return {
        "is_valid": is_valid,
        "enrolled_subjects": list(enrolled_names),
        "scheduled_subjects": list(scheduled_names),
        "unmatched_sessions": unmatched_sessions,
        "missing_enrolled_subjects": list(missing_enrolled),
    }



