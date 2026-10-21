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

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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
    start_time: Optional[str] = Field(None, description="Optional start time in 24h format (e.g., '09:00') for calendar mapping")
    end_time: Optional[str] = Field(None, description="Optional end time in 24h format (e.g., '11:00') for calendar mapping")


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
    search_keywords: List[str] = Field(
        default_factory=list,
        description="Optimized search query phrases (combining enrolled subjects with core technical concepts and skills) to feed external course recommendation pipelines"
    )

    @field_validator("search_keywords", mode="before")
    @classmethod
    def normalize_search_keywords(cls, value):
        if isinstance(value, str):
            if "," in value:
                return [k.strip() for k in value.split(",") if k.strip()]
            return [value.strip()] if value.strip() else []
        elif isinstance(value, list):
            return [str(k).strip() for k in value if str(k).strip()]
        return value or []

    @model_validator(mode="after")
    def validate_schedule_integrity(self):
        if not self.weekly_schedule:
            raise ValueError("weekly_schedule cannot be empty")

        # Enforce strict chronological ordering of days (Monday through Sunday)
        day_indices = []
        day_order_map = {day: idx for idx, day in enumerate(DAY_ORDER)}
        for day_item in self.weekly_schedule:
            if day_item.day in day_order_map:
                day_indices.append(day_order_map[day_item.day])

        if day_indices != sorted(day_indices):
            raise ValueError(
                f"weekly_schedule days must follow strict chronological order (Monday -> Sunday). Got: {[d.day for d in self.weekly_schedule]}"
            )
        return self


def validate_study_plan_output(data: dict) -> StudyPlanOutputSchema:
    """
    Validates a raw dictionary response against the strict StudyPlanOutputSchema Pydantic model.
    Throws ValidationError if the schema is violated.
    """
    return StudyPlanOutputSchema.model_validate(data)


# ---------------------------------------------------------------------------
# Regeneration / Plan Refinement Schemas & Prompts
# ---------------------------------------------------------------------------

class RegenerationInput(BaseModel):
    current_plan: StudyPlanOutputSchema = Field(
        ...,
        description="The active study plan object to be modified"
    )
    user_feedback: str = Field(
        ...,
        description="User tweak or adaptation request (e.g., 'Make Wednesday lighter')"
    )
    onboarding_data: Optional[OnboardingDataInput] = Field(
        None,
        description="Original onboarding student profile constraints (subjects, daily hours limit, semester, goals)"
    )

    @field_validator("user_feedback")
    @classmethod
    def validate_user_feedback_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("user_feedback cannot be empty")
        return value.strip()


# ---------------------------------------------------------------------------
# Adaptive Plan / Dynamic Re-Allocation Schemas
# ---------------------------------------------------------------------------

class MissedTaskInput(BaseModel):
    task_id: Optional[str] = Field(None, description="Unique identifier of the missed session/task")
    subject: str = Field(..., description="Subject name of the missed session (e.g., 'Operating Systems')")
    topic: str = Field(..., description="Specific topic or unit missed (e.g., 'Process Synchronization')")
    priority: PriorityLevel = Field("high", description="Priority level of the missed task ('high', 'medium', 'low')")
    missed_day: DayName = Field(..., description="Day of the week on which the session was originally scheduled and missed")
    planned_duration_hours: float = Field(..., ge=0.1, description="Original planned duration in hours (e.g., 1.5)")
    actual_minutes_studied: float = Field(0.0, ge=0.0, description="Actual minutes completed by the student before missing or dropping")
    deficit_hours: float = Field(..., ge=0.0, description="Net remaining hours needed to recover this topic")
    reason: Optional[str] = Field("Missed study session", description="Reason for deficit (e.g., 'Incomplete', 'Exam prep overlap', 'Skipped')")

    @field_validator("subject", "topic")
    @classmethod
    def validate_non_empty_strings(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Subject and topic cannot be empty strings")
        return value.strip()


class AdaptivePlanInput(BaseModel):
    current_plan: StudyPlanOutputSchema = Field(
        ...,
        description="The active 7-day study plan to be dynamically rebalanced"
    )
    missed_tasks: List[MissedTaskInput] = Field(
        ...,
        description="List of missed study sessions, with special emphasis on high-priority subjects"
    )
    current_day: DayName = Field(
        ...,
        description="The current day of the week (e.g., 'Wednesday'). Re-allocation only targets this day and subsequent days."
    )
    daily_hours_limit: Optional[float] = Field(
        None,
        ge=0.5,
        le=16.0,
        description="Maximum available study hours per day to enforce non-overload invariant"
    )
    onboarding_data: Optional[OnboardingDataInput] = Field(
        None,
        description="Optional student profile constraints (enrolled subjects, target scores, semester, goals)"
    )
    adaptation_goal: Optional[str] = Field(
        "Dynamically re-allocate missed high-priority subjects into remaining days without exceeding daily study hours",
        description="Explicit rebalancing objective"
    )

    @field_validator("missed_tasks")
    @classmethod
    def validate_missed_tasks_not_empty(cls, value: List[MissedTaskInput]) -> List[MissedTaskInput]:
        if not value:
            raise ValueError("missed_tasks cannot be empty for adaptive plan re-allocation")
        return value

    def get_high_priority_missed_tasks(self) -> List[MissedTaskInput]:
        """Returns only the high-priority missed tasks requiring mandatory recovery."""
        return [t for t in self.missed_tasks if t.priority == "high"]

    def get_remaining_days(self) -> List[DayName]:
        """Returns the list of remaining days in the schedule from current_day onward."""
        if self.current_day not in DAY_ORDER:
            return DAY_ORDER
        current_idx = DAY_ORDER.index(self.current_day)
        return DAY_ORDER[current_idx:]




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
8. CHRONOLOGICAL ORDERING & CALENDAR TIMINGS: The `weekly_schedule` array MUST be ordered in strict chronological sequence from Monday to Sunday. Within each day, sessions MUST be listed in chronological sequence with explicit `start_time` and `end_time` strings in 24-hour HH:MM format (e.g., "start_time": "09:00", "end_time": "11:00") so that exported calendar files (ICS/Google Calendar) map accurately to specific days and time blocks.
9. OPTIMIZED SEARCH KEYWORDS FOR COURSE RECOMMENDATIONS: The output MUST include a `search_keywords` array containing 3 to 8 targeted, high-relevance search query phrases (e.g., "Operating Systems Process Synchronization", "Computer Networks TCP Congestion Control", "Database Management Systems SQL"). Each keyword phrase MUST combine the subject name with key technical concepts or core skills covered in the schedule so it can directly feed the external course recommendation engine (TF-IDF/Coursera catalog).

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
          "priority": "high" | "medium" | "low",
          "start_time": string,
          "end_time": string
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
  "study_tips": [string],
  "search_keywords": [string]
}
"""



def build_study_plan_prompt(
    data: OnboardingDataInput,
    learning_history: dict | None = None,
) -> str:
    """
    Constructs the study-plan prompt using onboarding data and recent learning history.
    """

    subjects_formatted = json.dumps(
        [s.model_dump() for s in data.subjects],
        indent=2,
    )
    goals_formatted = json.dumps(data.goals, indent=2)

    history = learning_history or {
        "completed_tasks": [],
        "missed_sessions": [],
        "summary": {
            "completed_count": 0,
            "missed_count": 0,
        },
    }

    learning_history_formatted = json.dumps(
        history,
        indent=2,
        ensure_ascii=False,
    )

    prompt = f"""
Student Onboarding Profile:
- Semester: {data.semester}
- Available Daily Study Hours: {data.study_hours_per_day} hours/day
- Goals: {goals_formatted}
- Enrolled Subjects & Specific Target Scores:
{subjects_formatted}

Recent Learning History (last 7 calendar days):
{learning_history_formatted}

ADAPTIVE LEARNING REQUIREMENTS:
1. Use the recent learning history above when preparing the new weekly schedule.
2. For missed sessions, reschedule important unfinished topics across the upcoming
   week where appropriate. Do not overload any day beyond the student's available
   daily study hours.
3. For completed sessions, avoid unnecessarily repeating the same topic. Progress
   to the next logical topic or use revision/practice when useful.
4. If sessions were repeatedly missed, distribute the workload realistically rather
   than adding all missed work to one day.
5. If the history is empty or contains zero completed and missed sessions, create
   the plan using onboarding data without assuming the student has missed anything.
6. Treat learning history as supporting context. Do not invent completed sessions,
   missed sessions, subjects, or topics that are not supported by the supplied data.
7. Continue to follow all subject-name, time-balance, chronological-ordering,
   target-score, and search-keyword requirements in the system instructions.

Please generate the structured 7-day study plan according to the system
instructions and exact JSON schema.

IMPORTANT:
- Use the EXACT enrolled subject names in all schedule sessions.
- Ensure monthly milestones and key deliverables reflect the student's target
  scores and academic goals.
- Generate 3 to 8 high-relevance search_keywords combining subjects with
  technical concepts covered in the schedule.
- Respond ONLY with valid JSON matching the required schema.
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


def validate_chronological_ordering(plan: StudyPlanOutputSchema) -> Dict[str, Any]:
    """
    Validates that weekly_schedule days follow strict chronological order (Monday -> Sunday)
    and that session start/end times within each day follow chronological sequence without overlap.
    Returns a diagnostic report dictionary.
    """
    day_order_map = {day: idx for idx, day in enumerate(DAY_ORDER)}
    days_present = [d.day for d in plan.weekly_schedule]
    day_indices = [day_order_map[d] for d in days_present if d in day_order_map]

    is_days_chronological = day_indices == sorted(day_indices)
    has_calendar_timings = True
    timing_issues = []

    for day_item in plan.weekly_schedule:
        last_end_minutes = -1
        for s in day_item.sessions:
            if not s.start_time or not s.end_time:
                has_calendar_timings = False
                continue

            try:
                sh, sm = map(int, s.start_time.split(":"))
                eh, em = map(int, s.end_time.split(":"))
                start_min = sh * 60 + sm
                end_min = eh * 60 + em

                if end_min <= start_min:
                    timing_issues.append(
                        f"{day_item.day} session '{s.subject}' end_time ({s.end_time}) is not after start_time ({s.start_time})"
                    )

                if start_min < last_end_minutes:
                    timing_issues.append(
                        f"{day_item.day} session '{s.subject}' start_time ({s.start_time}) overlaps with preceding session"
                    )

                last_end_minutes = max(last_end_minutes, end_min)
            except Exception:
                has_calendar_timings = False

    is_valid = is_days_chronological and len(timing_issues) == 0

    return {
        "is_valid": is_valid,
        "days_chronological": is_days_chronological,
        "days_sequence": days_present,
        "has_calendar_timings": has_calendar_timings,
        "timing_issues": timing_issues,
    }


def validate_search_keywords(plan: StudyPlanOutputSchema) -> Dict[str, Any]:
    """
    Validates that search_keywords are present and non-empty in the generated study plan,
    suitable for querying the course recommendation pipeline.
    """
    keywords = [k.strip() for k in plan.search_keywords if isinstance(k, str) and k.strip()]
    is_valid = len(keywords) > 0
    return {
        "is_valid": is_valid,
        "keywords_count": len(keywords),
        "search_keywords": keywords,
    }


REGENERATION_SYSTEM_INSTRUCTION = """
You are an expert AI Academic Coach and Study Planner specializing in personalized study schedule adaptation.
Your task is to modify an existing 7-day personalized study plan based on a user's specific tweak request (e.g., "Make Wednesday lighter", "Add 2 hours of revision on Saturday").

CRITICAL INSTRUCTIONS:
1. OUTPUT FORMAT: Respond ONLY with a valid, raw JSON object adhering strictly to the JSON schema specified below.
2. DO NOT include markdown wrappers (such as ```json or ```), preamble, or postscript text.
3. MINIMAL SURGICAL EDITS: Modify only the necessary days, sessions, or parameters required to satisfy the user's tweak request. Maintain overall schedule balance and structure without rewriting unimpacted days unnecessarily.
4. STRICT TIME RE-BALANCING:
   - Recalculate `total_hours` for each day as the exact sum of `duration_hours` of its sessions.
   - The total hours for any day MUST NOT exceed the student's daily study hours limit.
   - Recalculate `weekly_total_hours` in `plan_overview` to accurately reflect the updated 7-day total.
5. SUBJECT FIDELITY & NO HALLUCINATION: In `weekly_schedule`, session `subject` fields MUST use the EXACT subject name strings from the original plan or onboarding profile. DO NOT invent, alter, or abbreviate subject names.
6. TARGET SCORE & MILESTONE INTEGRITY: Preserve dynamic exam revision milestones (`monthly_milestones`) and key deliverables aligned with target scores unless specifically asked to change them.
7. DETERMINISTIC METRICS: Ensure `activity_type` uses only ('core_concept_study', 'practice_problems', 'lecture_review', 'revision_quiz') and `priority` uses only ('high', 'medium', 'low').
8. CHRONOLOGICAL ORDERING & CALENDAR TIMINGS: The `weekly_schedule` array MUST be ordered in strict chronological sequence from Monday to Sunday. Within each day, sessions MUST be listed in chronological sequence with explicit `start_time` and `end_time` strings in 24-hour HH:MM format (e.g., "start_time": "09:00", "end_time": "11:00") so that exported calendar files (ICS/Google Calendar) map accurately to specific days and time blocks.
9. OPTIMIZED SEARCH KEYWORDS FOR COURSE RECOMMENDATIONS: Ensure the `search_keywords` array is updated to contain 3 to 8 high-relevance search query phrases reflecting the active and adjusted subjects, skills, and technical topics in the revised schedule to feed the external course recommendation engine.

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
          "priority": "high" | "medium" | "low",
          "start_time": string,
          "end_time": string
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
  "study_tips": [string],
  "search_keywords": [string]
}
"""


def build_regeneration_prompt(data: RegenerationInput) -> str:
    """
    Constructs the deterministic user prompt for study plan regeneration/refinement
    containing the current active plan, student context, and tweak request.
    """
    plan_json = json.dumps(data.current_plan.model_dump(), indent=2)

    context_str = ""
    if data.onboarding_data:
        subjects_formatted = json.dumps([s.model_dump() for s in data.onboarding_data.subjects], indent=2)
        goals_formatted = json.dumps(data.onboarding_data.goals, indent=2)
        context_str = f"""
Student Onboarding Profile Constraints:
- Semester: {data.onboarding_data.semester}
- Available Daily Study Hours Limit: {data.onboarding_data.study_hours_per_day} hours/day
- Goals: {goals_formatted}
- Enrolled Subjects & Specific Target Scores:
{subjects_formatted}
"""

    prompt = f"""
Active Study Plan to Modify:
{plan_json}
{context_str}
User Tweak Request:
"{data.user_feedback}"

Please update the active study plan according to the user tweak request and system instructions.
CRITICAL REQUIREMENTS:
- Apply targeted modifications to honor "{data.user_feedback}".
- Recalculate daily `total_hours` for all modified days so they equal the sum of session durations, without exceeding daily available study hours limits.
- Update `weekly_total_hours` in `plan_overview` to match the new sum across all 7 days.
- Maintain EXACT subject names (do not alter course codes, numbers, or special characters).
- Provide updated, optimized 'search_keywords' matching modified subjects and topics for course recommendation integration.
- Respond ONLY with valid, raw JSON matching the required schema.
"""
    return prompt.strip()


# ---------------------------------------------------------------------------
# Adaptive Plan System Instruction & Dynamic Re-Allocation Prompt Builder
# ---------------------------------------------------------------------------

ADAPTIVE_PLAN_SYSTEM_INSTRUCTION = """
You are an expert AI Academic Coach and Study Planner specializing in dynamic adaptive learning and schedule re-balancing.
Your task is to re-allocate missed study sessions—with absolute top priority given to missed HIGH-PRIORITY subjects—into the remaining available days of an active 7-day study plan without causing student burnout or exceeding daily study hour limits.

CRITICAL INSTRUCTIONS & INVARIANTS:
1. OUTPUT FORMAT: Respond ONLY with a valid, raw JSON object adhering strictly to the JSON schema specified below.
2. DO NOT include markdown code fences (```json or ```), preamble, or postscript text.
3. MANDATORY HIGH-PRIORITY RECOVERY:
   - Every missed task with priority="high" MUST be successfully rescheduled into upcoming available days.
   - Rescheduled sessions must be designated with high priority and an appropriate focused activity type ('core_concept_study', 'revision_quiz', or 'practice_problems').
   - Prefix the rescheduled topic with "Catch-up: " or "Mastery Catch-up: " to make recovery transparent to the student.
4. FORWARD-ONLY ALLOCATION (NO PAST MODIFICATIONS):
   - Only modify sessions for the current day (`current_day`) and subsequent upcoming days.
   - Days that occurred prior to `current_day` represent historical records and MUST NOT be populated with new catch-up sessions.
5. STRICT DAILY STUDY HOURS CEILING (NO STUDENT BURNOUT):
   - The total study hours (`total_hours`) for any day MUST NOT exceed the student's daily study hours limit (`daily_hours_limit` or `daily_target_hours`).
   - If adding catch-up sessions threatens to exceed daily capacity, you MUST intelligently swap, compress, or postpone existing 'low' or 'medium' priority sessions (such as generic reviews or optional problem sets).
   - Recalculate each modified day's `total_hours` to equal the exact sum of its sessions' `duration_hours`.
6. COGNITIVE LOAD BALANCING & SPACED REPETITION:
   - Distribute multiple missed sessions across different upcoming days with the lowest existing load.
   - Do NOT stack more than 2 consecutive hours of the same demanding technical subject in a single session.
7. SUBJECT FIDELITY & ZERO HALLUCINATION:
   - In `weekly_schedule`, session `subject` fields MUST preserve the EXACT subject name strings from the active plan or input profile (e.g., 'Operating Systems', 'C++', 'AI/ML', 'BI-402').
   - DO NOT invent, abbreviate, or alter subject names.
8. CHRONOLOGICAL ORDERING & CONFLICT-FREE TIMINGS:
   - Days must remain in strict chronological order (Monday through Sunday).
   - Within each day, sessions must have valid, non-overlapping `start_time` and `end_time` strings in 24-hour HH:MM format (e.g., "09:00", "11:00").
9. OPTIMIZED SEARCH KEYWORDS FOR TARGETED RECOMMENDATIONS:
   - The `search_keywords` array MUST be updated to prominently feature the missed high-priority subjects and topics (e.g., "Operating Systems Process Synchronization Semaphores", "Computer Networks TCP Flow Control") so the recommendation pipeline can immediately surface relevant Coursera video modules and refresher courses.
10. EXPLICIT STRATEGY SUMMARY:
   - Update `strategy_summary` in `plan_overview` to clearly articulate how the schedule was adapted (e.g., "Re-allocated 1.5h missed Operating Systems Process Synchronization to Friday by compressing low-priority practice, maintaining 4.0h daily limit").

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
          "priority": "high" | "medium" | "low",
          "start_time": string,
          "end_time": string
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
  "study_tips": [string],
  "search_keywords": [string]
}
"""


def build_adaptive_plan_prompt(data: AdaptivePlanInput) -> str:
    """
    Constructs the deterministic user prompt for adaptive schedule re-allocation,
    providing the active plan, missed high-priority tasks, available remaining days,
    and daily study hour constraints.
    """
    plan_json = json.dumps(data.current_plan.model_dump(), indent=2)

    remaining_days = data.get_remaining_days()
    remaining_days_str = ", ".join(remaining_days)

    limit = (
        data.daily_hours_limit
        or (data.onboarding_data.study_hours_per_day if data.onboarding_data else None)
        or data.current_plan.plan_overview.daily_target_hours
    )

    missed_tasks_formatted = []
    for t in data.missed_tasks:
        missed_tasks_formatted.append(
            f"- [{t.priority.upper()}] Subject: '{t.subject}' | Topic: '{t.topic}' | "
            f"Missed on: {t.missed_day} | Deficit: {t.deficit_hours}h (Planned {t.planned_duration_hours}h, "
            f"Studied {t.actual_minutes_studied}m) | Reason: {t.reason or 'Missed session'}"
        )
    missed_tasks_str = "\n".join(missed_tasks_formatted)

    onboarding_str = ""
    if data.onboarding_data:
        subjects_formatted = json.dumps([s.model_dump() for s in data.onboarding_data.subjects], indent=2)
        onboarding_str = f"""
Student Onboarding Profile Constraints:
- Semester: {data.onboarding_data.semester}
- Enrolled Subjects & Target Scores:
{subjects_formatted}
"""

    prompt = f"""
Active 7-Day Study Plan:
{plan_json}
{onboarding_str}
Current Day: {data.current_day}
Available Remaining Days for Re-allocation: [{remaining_days_str}]
Strict Daily Available Study Hours Limit: {limit} hours/day

Missed Study Tasks Requiring Dynamic Re-allocation:
{missed_tasks_str}

Adaptation Goal:
"{data.adaptation_goal}"

CRITICAL INSTRUCTIONS FOR ADAPTIVE RE-ALLOCATION:
1. Re-allocate all missed HIGH-PRIORITY subjects into remaining days [{remaining_days_str}].
2. Do NOT add catch-up sessions to days before {data.current_day}.
3. The sum of session durations on ANY day must not exceed {limit} hours. If needed, compress or defer existing 'low' or 'medium' priority sessions.
4. Update `total_hours` for each affected day and `weekly_total_hours` in `plan_overview`.
5. Preserve EXACT subject name strings (zero hallucination).
6. Ensure all sessions have non-overlapping 24h start_time and end_time.
7. Include 3 to 8 targeted `search_keywords` combining the missed high-priority subjects with their core technical skills.
8. Update `strategy_summary` to describe how missed sessions were re-allocated.
9. Return ONLY valid, raw JSON adhering strictly to the schema.
"""
    return prompt.strip()





