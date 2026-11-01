"""
Pydantic Schemas for AI Academic Assistant System Actions and Tool Invocations.

Validates the AI Assistant's structured output when it decides to trigger a system action
(such as querying the tasks table to check today's priorities, reading active study plans,
fetching weak topic diagnostics, triggering adaptive rebalances, or querying Coursera recommendations).

Grounding Invariants:
1. Grounded Queries: Tool parameters must be strictly typed to prevent SQL injection or arbitrary query execution.
2. Invariant Date Handling: Resolves 'today', 'tomorrow', 'this_week' relative to active calendar dates.
3. Read vs Write Separation: Distinguishes non-destructive queries from state-mutating actions requiring confirmation.
4. Extensible Tool Registry: Discriminated union of action types conforming to Gemini / OpenAI tool-call conventions.
"""

from datetime import date, datetime, timedelta
import re
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import uuid4
from zoneinfo import ZoneInfo
from pydantic import BaseModel, Field, field_validator, model_validator


# ===========================================================================
# 1. System Action Enumerations
# ===========================================================================

SystemActionType = Literal[
    "read_tasks_table",
    "get_active_study_plan",
    "get_weak_topics_telemetry",
    "get_analytics_summary",
    "trigger_adaptive_rebalance",
    "search_learning_resources",
    "log_task_execution",
    "update_study_hours_capacity",
]

PriorityFilter = Literal["high", "medium", "low", "all"]
TaskStatusFilter = Literal["pending", "completed", "all"]
DateAlias = Literal["today", "tomorrow", "yesterday", "this_week", "all"]


# ===========================================================================
# 2. Parameter Schemas for Individual Tool Actions
# ===========================================================================

class ReadTasksTableParams(BaseModel):
    """
    Parameters for querying the student's tasks table.
    Example query: "What is my priority today?" ->
    ReadTasksTableParams(target_date="today", priority="high", status="pending")
    """
    target_date: Union[date, DateAlias, str] = Field(
        default="today",
        description="Date filter: exact date 'YYYY-MM-DD' or relative alias ('today', 'tomorrow', 'this_week', 'all')"
    )
    priority: Optional[PriorityFilter] = Field(
        default=None,
        description="Filter by session priority: 'high' isolates critical exam/core concepts"
    )
    status: TaskStatusFilter = Field(
        default="pending",
        description="Filter by task status: 'pending' (uncompleted), 'completed', or 'all'"
    )
    subject: Optional[str] = Field(
        default=None,
        description="Optional filter by subject name (e.g., 'Operating Systems')"
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of task records to retrieve"
    )
    order_by: Literal["priority_desc", "scheduled_date_asc", "created_at_desc"] = Field(
        default="priority_desc",
        description="Ordering criteria for retrieved tasks"
    )

    @field_validator("target_date")
    @classmethod
    def validate_and_normalize_target_date(cls, value: Any) -> str:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            clean = value.strip().lower()
            if clean in ["today", "tomorrow", "yesterday", "this_week", "all"]:
                return clean
            # Validate ISO date format YYYY-MM-DD
            if re.match(r"^\d{4}-\d{2}-\d{2}$", clean):
                return clean
            raise ValueError(f"Invalid target_date format '{value}'. Expected YYYY-MM-DD or alias ('today', 'tomorrow', 'this_week', 'all').")
        raise ValueError(f"Unsupported target_date type: {type(value)}")

    def resolve_concrete_date_range(self, reference_date: Optional[date] = None) -> Dict[str, Optional[str]]:
        """
        Resolves relative date aliases into concrete ISO start_date and end_date strings.
        """
        ref = reference_date or datetime.now(ZoneInfo("Asia/Kolkata")).date()
        target = str(self.target_date).lower()

        if target == "today":
            return {"start_date": ref.isoformat(), "end_date": ref.isoformat()}
        elif target == "tomorrow":
            t_date = ref + timedelta(days=1)
            return {"start_date": t_date.isoformat(), "end_date": t_date.isoformat()}
        elif target == "yesterday":
            y_date = ref - timedelta(days=1)
            return {"start_date": y_date.isoformat(), "end_date": y_date.isoformat()}
        elif target == "this_week":
            # Monday of current week to Sunday
            start_of_week = ref - timedelta(days=ref.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            return {"start_date": start_of_week.isoformat(), "end_date": end_of_week.isoformat()}
        elif target == "all":
            return {"start_date": None, "end_date": None}
        else:
            return {"start_date": target, "end_date": target}


class GetActiveStudyPlanParams(BaseModel):
    """
    Parameters for retrieving the student's active 7-day study plan.
    """
    include_full_schedule: bool = Field(
        default=True,
        description="Whether to return all 7 days with sessions or just overview summary"
    )
    specific_day: Optional[Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]] = Field(
        default=None,
        description="Optional filter for a specific day's schedule"
    )


class GetWeakTopicsParams(BaseModel):
    """
    Parameters for fetching deterministic diagnostic weak topics from WeakTopicsService.
    """
    severity_filter: Optional[Literal["high", "medium", "low", "all"]] = Field(
        default="all",
        description="Filter by severity level"
    )
    min_deficit_minutes: int = Field(
        default=0,
        ge=0,
        description="Minimum study deficit threshold in minutes"
    )
    subject: Optional[str] = Field(
        default=None,
        description="Optional filter by subject name"
    )


class GetAnalyticsSummaryParams(BaseModel):
    """
    Parameters for fetching student telemetry, study velocity, and adherence rates.
    """
    timeframe: Literal["current_week", "last_30_days", "semester_to_date"] = Field(
        default="current_week",
        description="Timeframe window for analytics aggregation"
    )


class TriggerAdaptiveRebalanceParams(BaseModel):
    """
    Parameters for triggering schedule rebalance to redistribute missed tasks into upcoming days.
    """
    reason: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Student-articulated reason or diagnostic trigger for rebalancing"
    )
    preserve_completed_tasks: bool = Field(
        default=True,
        description="Invariant: Ensure completed sessions remain untouched"
    )


class SearchLearningResourcesParams(BaseModel):
    """
    Parameters for querying the TF-IDF recommendation engine for Coursera courses.
    """
    query: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Normalized subject/topic query string (e.g. 'Operating Systems Peterson Algorithm')"
    )
    top_n: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of recommended courses to return"
    )
    min_similarity_score: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        description="Cosine similarity cutoff threshold"
    )


class LogTaskExecutionParams(BaseModel):
    """
    Parameters for logging study execution telemetry for a scheduled task.
    """
    task_id: str = Field(
        ...,
        description="Unique identifier of the task being logged"
    )
    status: Literal["completed", "partially_completed", "missed"] = Field(
        ...,
        description="Execution outcome status"
    )
    actual_minutes: int = Field(
        ...,
        ge=0,
        le=480,
        description="Actual study minutes logged by the student"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional student notes or reflections"
    )


class UpdateStudyHoursCapacityParams(BaseModel):
    """
    Parameters for updating daily available study hours in settings.
    """
    new_daily_hours: float = Field(
        ...,
        ge=0.5,
        le=16.0,
        description="New daily study hours capacity"
    )
    reason: Optional[str] = Field(
        default="Adjusted via AI Assistant",
        description="Audit note for study hours change"
    )


# ===========================================================================
# 3. Tool Call & System Action Models
# ===========================================================================

class AssistantToolCall(BaseModel):
    """
    Validates a single system action/tool call triggered by the AI Assistant.
    Conforms to standard LLM tool invocation conventions.
    """
    call_id: str = Field(
        default_factory=lambda: f"call_{uuid4().hex[:12]}",
        description="Unique tool call execution ID"
    )
    action_type: SystemActionType = Field(
        ...,
        description="The specific system action being invoked"
    )
    parameters: Dict[str, Any] = Field(
        ...,
        description="Key-value arguments for the action"
    )
    thought_reasoning: str = Field(
        ...,
        min_length=5,
        description="Internal explanation of why this system action was chosen"
    )
    requires_user_confirmation: bool = Field(
        default=False,
        description="Whether explicit user confirmation is required before execution (True for state mutations)"
    )

    def parse_typed_parameters(self) -> Union[
        ReadTasksTableParams,
        GetActiveStudyPlanParams,
        GetWeakTopicsParams,
        GetAnalyticsSummaryParams,
        TriggerAdaptiveRebalanceParams,
        SearchLearningResourcesParams,
        LogTaskExecutionParams,
        UpdateStudyHoursCapacityParams,
    ]:
        """
        Parses and validates the raw parameters dict into its corresponding strongly-typed Pydantic model.
        """
        action_map = {
            "read_tasks_table": ReadTasksTableParams,
            "get_active_study_plan": GetActiveStudyPlanParams,
            "get_weak_topics_telemetry": GetWeakTopicsParams,
            "get_analytics_summary": GetAnalyticsSummaryParams,
            "trigger_adaptive_rebalance": TriggerAdaptiveRebalanceParams,
            "search_learning_resources": SearchLearningResourcesParams,
            "log_task_execution": LogTaskExecutionParams,
            "update_study_hours_capacity": UpdateStudyHoursCapacityParams,
        }
        schema_cls = action_map.get(self.action_type)
        if not schema_cls:
            raise ValueError(f"Unknown action_type: '{self.action_type}'")
        return schema_cls.model_validate(self.parameters)


# ===========================================================================
# 4. Top-Level Assistant Output Schema
# ===========================================================================

class AssistantActionResponseSchema(BaseModel):
    """
    Validates the overall output from the AI Assistant.
    Can be:
    1. 'conversational_response': Direct text answer with no system actions needed.
    2. 'system_action': Pure tool invocation (e.g. querying tasks table before answering).
    3. 'composite': Conversational text preamble accompanied by one or more system actions.
    """
    response_type: Literal["conversational_response", "system_action", "composite"] = Field(
        ...,
        description="Nature of the AI response"
    )
    message: Optional[str] = Field(
        default=None,
        description="Conversational explanation or answer displayed to the student"
    )
    tool_calls: List[AssistantToolCall] = Field(
        default_factory=list,
        description="List of system actions triggered by the assistant"
    )
    detected_intent: Optional[str] = Field(
        default=None,
        description="Identified user intention (e.g., 'check_daily_priorities', 'explain_weak_topic')"
    )
    suggested_follow_ups: List[str] = Field(
        default_factory=list,
        description="Suggested quick-reply prompt chips for the student"
    )

    @model_validator(mode="after")
    def validate_action_response_coherence(self) -> "AssistantActionResponseSchema":
        if self.response_type in ["system_action", "composite"] and not self.tool_calls:
            raise ValueError(
                f"response_type '{self.response_type}' requires at least one item in 'tool_calls'."
            )
        if self.response_type == "conversational_response" and self.tool_calls:
            raise ValueError(
                "response_type 'conversational_response' cannot contain tool_calls. Use 'composite' instead."
            )
        if self.response_type == "conversational_response" and not self.message:
            raise ValueError(
                "response_type 'conversational_response' must have a non-empty 'message'."
            )
        return self


# ===========================================================================
# 5. Tool Execution Result Schemas (Backend -> Assistant Context)
# ===========================================================================

class TaskRecordItem(BaseModel):
    """
    Normalized representation of a task record read from the tasks table.
    """
    id: str = Field(..., description="Task UUID")
    title: str = Field(..., description="Full task title (e.g. 'Operating Systems: Process Synchronization')")
    subject: str = Field(..., description="Parsed subject name")
    topic: str = Field(..., description="Parsed topic name")
    priority: Literal["high", "medium", "low"] = Field(..., description="Task priority")
    scheduled_date: Optional[str] = Field(None, description="Scheduled date in YYYY-MM-DD")
    duration_hours: float = Field(..., ge=0.1, description="Allocated study duration in hours")
    is_completed: bool = Field(..., description="Completion flag")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")

    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "TaskRecordItem":
        """Constructs a TaskRecordItem from a PostgreSQL/Supabase tasks table row."""
        title = row.get("title") or "General Study: Core Concept"
        desc = row.get("description") or ""

        # Parse subject and topic
        if ":" in title:
            parts = title.split(":", 1)
            subject = parts[0].strip()
            topic = parts[1].strip()
        else:
            subject = "General Study"
            topic = title.strip()

        # Parse duration from description
        dur = 1.0
        if "Duration:" in desc:
            try:
                dur_str = desc.split("Duration:")[1].split("hours")[0].strip()
                dur = float(dur_str)
            except Exception:
                dur = 1.0

        # Parse priority from description
        priority = "medium"
        if "Priority:" in desc:
            try:
                p_str = desc.split("Priority:")[1].split("|")[0].strip().lower()
                if p_str in ["high", "medium", "low"]:
                    priority = p_str
            except Exception:
                priority = "medium"

        return cls(
            id=str(row.get("id")),
            title=title,
            subject=subject,
            topic=topic,
            priority=priority,  # type: ignore
            scheduled_date=row.get("scheduled_date"),
            duration_hours=dur,
            is_completed=bool(row.get("is_completed")),
            completed_at=row.get("completed_at"),
        )


class ToolExecutionResult(BaseModel):
    """
    Validates the result payload returned after executing a system action,
    ready to be fed back into the AI Assistant context window.
    """
    call_id: str = Field(..., description="Matching call_id from AssistantToolCall")
    action_type: SystemActionType = Field(..., description="Action that was executed")
    success: bool = Field(..., description="Whether execution completed successfully")
    record_count: int = Field(0, ge=0, description="Number of records returned")
    data: Any = Field(None, description="Structured execution result data")
    error_message: Optional[str] = Field(None, description="Error detail if execution failed")
    executed_at: str = Field(
        default_factory=lambda: datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        description="Timestamp when tool was executed"
    )
