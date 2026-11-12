"""
Deterministic Goal Evaluation Service.

Evaluates student academic goal attainment strictly from empirical study execution
telemetry (logged study hours, completed tasks, and task execution minutes) against
configured `target_study_hours`.

Invariants:
1. Purely deterministic: No speculative AI claims; goal status is derived strictly from
   quantifiable studied vs. target hours.
2. Float-safe threshold check: Uses 2-decimal rounding so summed session hours
   (e.g., 1.5 + 1.5 + 1.5 = 4.5) cleanly trigger success status when matching target_study_hours.
3. Supports direct hours evaluation, active study_plan JSON evaluation, and PostgreSQL
   tasks-table evaluation, with optional subject-level filtering.
"""

from dataclasses import asdict, dataclass
import math
import re
from typing import Any, Dict, List, Literal, Optional


GoalStatus = Literal["achieved", "on_track", "in_progress", "behind"]

_DURATION_PATTERN = re.compile(r"Duration:\s*([0-9]+(?:\.[0-9]+)?)\s*hours?", re.IGNORECASE)


@dataclass
class GoalEvaluationResult:
    """Structured outcome of evaluating study progress against target_study_hours."""

    status: GoalStatus
    success_triggered: bool
    studied_hours: float
    target_study_hours: float
    remaining_hours: float
    surplus_hours: float
    progress_percentage: float
    completed_tasks: int = 0
    total_tasks: int = 0
    subject_filter: Optional[str] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _validate_finite_number(value: Any, name: str) -> float:
    """Validates that a numeric input is finite and converts it to float."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a numeric value, got bool.")
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a valid number, got {value!r}.") from exc
    if not math.isfinite(num):
        raise ValueError(f"{name} must be finite, got {value!r}.")
    return num


def _parse_task_duration_hours(description: Optional[str], default: float = 1.0) -> float:
    """Parses `Duration: <float> hours` from a task description string."""
    if not description:
        return default
    match = _DURATION_PATTERN.search(description)
    if not match:
        return default
    try:
        hours = float(match.group(1))
        return hours if hours > 0 else default
    except (ValueError, TypeError):
        return default


def _parse_task_subject(title: Optional[str]) -> str:
    """Extracts the subject prefix from a `<Subject>: <Topic>` task title."""
    if not title or ":" not in title:
        return "General Study"
    return title.split(":", 1)[0].strip()


def evaluate_goal_progress(
    studied_hours: float,
    target_study_hours: float,
    *,
    completed_tasks: int = 0,
    total_tasks: int = 0,
    subject_filter: Optional[str] = None,
) -> GoalEvaluationResult:
    """
    Evaluates whether total studied hours meet `target_study_hours`.

    Triggers `status == "achieved"` and `success_triggered == True` when
    `round(studied_hours, 2) >= round(target_study_hours, 2)`.
    """
    studied_raw = _validate_finite_number(studied_hours, "studied_hours")
    target_raw = _validate_finite_number(target_study_hours, "target_study_hours")

    if studied_raw < 0:
        raise ValueError(f"studied_hours cannot be negative (got {studied_raw}).")
    if target_raw <= 0:
        raise ValueError(f"target_study_hours must be greater than 0 (got {target_raw}).")
    if completed_tasks < 0 or total_tasks < 0:
        raise ValueError("Task counts cannot be negative.")
    if total_tasks > 0 and completed_tasks > total_tasks:
        raise ValueError("completed_tasks cannot exceed total_tasks.")

    studied = round(studied_raw, 2)
    target = round(target_raw, 2)

    if studied >= target:
        status: GoalStatus = "achieved"
        success_triggered = True
        remaining = 0.0
        surplus = round(studied - target, 2)
    else:
        success_triggered = False
        remaining = round(target - studied, 2)
        surplus = 0.0
        ratio_pct = (studied / target) * 100.0
        if ratio_pct >= 75.0:
            status = "on_track"
        elif ratio_pct >= 25.0:
            status = "in_progress"
        else:
            status = "behind"

    progress_pct = round((studied / target) * 100.0, 1)
    scope_label = f" for '{subject_filter}'" if subject_filter else ""

    if success_triggered:
        message = (
            f"Goal achieved{scope_label}: studied {studied}h / {target}h target "
            f"({progress_pct}%)."
        )
    else:
        message = (
            f"Goal {status.replace('_', ' ')}{scope_label}: studied {studied}h / {target}h target "
            f"({remaining}h remaining)."
        )

    return GoalEvaluationResult(
        status=status,
        success_triggered=success_triggered,
        studied_hours=studied,
        target_study_hours=target,
        remaining_hours=remaining,
        surplus_hours=surplus,
        progress_percentage=progress_pct,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        subject_filter=subject_filter,
        message=message,
    )


def evaluate_goal_from_plan(
    plan_data: Dict[str, Any],
    target_study_hours: Optional[float] = None,
    *,
    subject_filter: Optional[str] = None,
) -> GoalEvaluationResult:
    """
    Aggregates studied hours from an active study plan (`weekly_schedule`,
    `completed_task_ids`, and `task_executions`) and evaluates against target_study_hours.

    If `target_study_hours` is omitted, derives it from the sum of scheduled session
    hours (matching `subject_filter` if given) or `plan_overview.weekly_total_hours`.
    """
    if not isinstance(plan_data, dict):
        raise ValueError("plan_data must be a dictionary.")

    weekly_schedule = plan_data.get("weekly_schedule") or []
    completed_ids = set(plan_data.get("completed_task_ids") or [])
    executions = plan_data.get("task_executions") or {}

    studied_minutes = 0.0
    planned_minutes = 0.0
    total_tasks = 0
    completed_tasks = 0
    subj_norm = subject_filter.strip().lower() if subject_filter else None

    for day_idx, day_item in enumerate(weekly_schedule, start=1):
        if not isinstance(day_item, dict):
            continue
        for sess_idx, sess in enumerate(day_item.get("sessions") or [], start=1):
            if not isinstance(sess, dict):
                continue
            sess_subject = str(sess.get("subject") or "").strip()
            if subj_norm and sess_subject.lower() != subj_norm:
                continue

            total_tasks += 1
            sess_id = sess.get("id") or f"sess-d{day_idx}-t{sess_idx}"
            dur_hours = float(sess.get("duration_hours") or 1.0)
            sess_planned_mins = max(0.0, dur_hours * 60.0)
            planned_minutes += sess_planned_mins

            exec_info = executions.get(sess_id) or {}
            exec_status = exec_info.get("status")
            is_done = exec_status == "completed" or sess_id in completed_ids

            if is_done:
                completed_tasks += 1
                actual_mins = exec_info.get("actual_minutes")
                studied_minutes += float(actual_mins) if actual_mins is not None else sess_planned_mins
            elif exec_status == "partially_completed":
                actual_mins = exec_info.get("actual_minutes", 0)
                studied_minutes += max(0.0, float(actual_mins or 0))
            elif exec_status == "missed":
                studied_minutes += 0.0
            elif "actual_minutes" in exec_info and exec_info["actual_minutes"] is not None:
                studied_minutes += max(0.0, float(exec_info["actual_minutes"]))

    resolved_target = target_study_hours
    if resolved_target is None:
        if not subj_norm:
            overview_total = (plan_data.get("plan_overview") or {}).get("weekly_total_hours")
            if overview_total is not None and float(overview_total) > 0:
                resolved_target = float(overview_total)
        if resolved_target is None:
            resolved_target = planned_minutes / 60.0

    return evaluate_goal_progress(
        studied_hours=studied_minutes / 60.0,
        target_study_hours=resolved_target,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        subject_filter=subject_filter,
    )


def evaluate_goal_from_tasks(
    tasks: List[Dict[str, Any]],
    target_study_hours: float,
    *,
    subject_filter: Optional[str] = None,
) -> GoalEvaluationResult:
    """
    Aggregates studied hours from PostgreSQL/Supabase `tasks` rows and evaluates
    against `target_study_hours`.
    """
    if not isinstance(tasks, list):
        raise ValueError("tasks must be a list of task dictionaries.")

    subj_norm = subject_filter.strip().lower() if subject_filter else None
    studied_hours = 0.0
    total_tasks = 0
    completed_tasks = 0

    for row in tasks:
        if not isinstance(row, dict):
            continue
        row_subject = _parse_task_subject(row.get("title"))
        if subj_norm and row_subject.lower() != subj_norm:
            continue

        total_tasks += 1
        is_completed = bool(row.get("is_completed"))
        actual_minutes = row.get("actual_minutes")

        if is_completed:
            completed_tasks += 1
            if actual_minutes is not None:
                studied_hours += max(0.0, float(actual_minutes)) / 60.0
            else:
                studied_hours += _parse_task_duration_hours(row.get("description"))
        elif actual_minutes is not None:
            studied_hours += max(0.0, float(actual_minutes)) / 60.0

    return evaluate_goal_progress(
        studied_hours=studied_hours,
        target_study_hours=target_study_hours,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        subject_filter=subject_filter,
    )

