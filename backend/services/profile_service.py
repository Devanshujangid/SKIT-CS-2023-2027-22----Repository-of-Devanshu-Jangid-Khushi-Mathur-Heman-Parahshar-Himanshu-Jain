"""
Profile & Schedule Re-evaluation Service.

Handles student profile updates (specifically daily study hours in Settings/Onboarding)
and deterministically evaluates whether the new capacity requires re-evaluation/rebalancing
of the active weekly study schedule.

Invariants:
1. Invariant 3 (Time Balance): Sum of duration_hours on any day MUST NOT exceed daily available study hours.
2. If new_hours < previous_hours, schedule_reevaluation_required flag is safely triggered.
3. If any day in the active weekly schedule exceeds new_hours, overloaded days and overflow hours are flagged.
4. Full audit trail: records previous hours, new hours, reduction, overloaded days, and timestamp.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class OverloadedDay:
    day: str
    day_index: int
    planned_hours: float
    capacity_limit: float
    overflow_hours: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileReevaluationResult:
    schedule_reevaluation_required: bool
    hours_reduced: bool
    previous_hours: Optional[float]
    new_hours: float
    reduction_hours: float
    overloaded_days: List[Dict[str, Any]] = field(default_factory=list)
    total_overflow_hours: float = 0.0
    reasons: List[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_day_total_hours(day_data: Dict[str, Any]) -> float:
    """
    Deterministically computes total planned study hours for a single day.
    Uses 'total_hours' if explicitly given and valid; otherwise sums valid session duration_hours.
    """
    total_hours = day_data.get("total_hours")
    if total_hours is not None:
        try:
            val = float(total_hours)
            if val >= 0:
                return round(val, 2)
        except (ValueError, TypeError):
            pass

    # Fallback to summing sessions
    sessions = day_data.get("sessions") or []
    computed_sum = 0.0
    for sess in sessions:
        if isinstance(sess, dict):
            dur = sess.get("duration_hours")
            try:
                if dur is not None:
                    d_float = float(dur)
                    if d_float > 0:
                        computed_sum += d_float
            except (ValueError, TypeError):
                continue

    return round(computed_sum, 2)


def evaluate_profile_hours_update(
    new_hours: float,
    previous_hours: Optional[float] = None,
    weekly_schedule: Optional[List[Dict[str, Any]]] = None,
    enforce_strict_ceiling: bool = True,
) -> ProfileReevaluationResult:
    """
    Pure deterministic evaluation of daily study hours update.

    Args:
        new_hours: Newly specified daily study hours (must be > 0).
        previous_hours: Existing study hours per day (None for cold start / initial setup).
        weekly_schedule: List of day dicts from student's active study plan.
        enforce_strict_ceiling: Whether daily capacity ceiling is strictly enforced.

    Returns:
        ProfileReevaluationResult with schedule_reevaluation_required, overloaded_days, and audit details.
    """
    try:
        new_hours = round(float(new_hours), 2)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid new_hours '{new_hours}': must be a valid numeric value.") from exc

    if new_hours <= 0:
        raise ValueError(f"new_hours ({new_hours}) must be greater than 0.")

    # 1. Check whether hours were reduced
    hours_reduced = False
    reduction_hours = 0.0
    prev_h_clean: Optional[float] = None

    if previous_hours is not None:
        try:
            prev_h_clean = round(float(previous_hours), 2)
            if prev_h_clean > new_hours:
                hours_reduced = True
                reduction_hours = round(prev_h_clean - new_hours, 2)
        except (ValueError, TypeError):
            prev_h_clean = None

    # 2. Check each day in the active weekly schedule for capacity overflows
    overloaded_days: List[Dict[str, Any]] = []
    total_overflow = 0.0

    if weekly_schedule and isinstance(weekly_schedule, list):
        for idx, day_item in enumerate(weekly_schedule, start=1):
            if not isinstance(day_item, dict):
                continue
            day_name = day_item.get("day", f"Day {idx}")
            planned_hours = calculate_day_total_hours(day_item)

            if planned_hours > new_hours:
                overflow = round(planned_hours - new_hours, 2)
                total_overflow += overflow
                overloaded_day = OverloadedDay(
                    day=day_name,
                    day_index=idx,
                    planned_hours=planned_hours,
                    capacity_limit=new_hours,
                    overflow_hours=overflow,
                )
                overloaded_days.append(overloaded_day.to_dict())

    total_overflow = round(total_overflow, 2)

    # 3. Determine if schedule re-evaluation flag is required
    reasons: List[str] = []
    if hours_reduced:
        reasons.append("daily_study_hours_reduced")
    if overloaded_days and enforce_strict_ceiling:
        reasons.append("daily_capacity_exceeded")

    schedule_reevaluation_required = len(reasons) > 0

    # 4. Construct explainability summary message
    if schedule_reevaluation_required:
        if hours_reduced and overloaded_days:
            message = (
                f"Daily study hours reduced from {prev_h_clean}h to {new_hours}h. "
                f"{len(overloaded_days)} scheduled day(s) exceed new daily capacity by {total_overflow}h total; "
                f"schedule re-evaluation required."
            )
        elif hours_reduced and not overloaded_days:
            message = (
                f"Daily study hours reduced from {prev_h_clean}h to {new_hours}h. "
                f"Current schedule days are within capacity, but pacing re-evaluation is recommended."
            )
        else:
            message = (
                f"Active schedule has {len(overloaded_days)} day(s) exceeding daily capacity limit of {new_hours}h "
                f"by {total_overflow}h total; schedule re-evaluation required."
            )
    else:
        if prev_h_clean is not None and new_hours > prev_h_clean:
            message = (
                f"Daily study hours increased from {prev_h_clean}h to {new_hours}h. "
                f"All scheduled days within capacity; no re-evaluation required."
            )
        else:
            message = (
                f"Daily study hours set to {new_hours}h. "
                f"All scheduled days within capacity; no re-evaluation required."
            )

    return ProfileReevaluationResult(
        schedule_reevaluation_required=schedule_reevaluation_required,
        hours_reduced=hours_reduced,
        previous_hours=prev_h_clean,
        new_hours=new_hours,
        reduction_hours=reduction_hours,
        overloaded_days=overloaded_days,
        total_overflow_hours=total_overflow,
        reasons=reasons,
        message=message,
    )


def apply_reevaluation_to_plan(
    plan_data: Dict[str, Any],
    reevaluation: ProfileReevaluationResult,
) -> Dict[str, Any]:
    """
    Applies the re-evaluation flags and updated capacity limits to an active study plan dictionary.
    Preserves all existing completions, executions, and session structures.
    """
    updated_plan = dict(plan_data)

    # Update capacity constraints in overview and onboarding metadata
    overview = dict(updated_plan.get("plan_overview") or {})
    overview["daily_target_hours"] = reevaluation.new_hours
    updated_plan["plan_overview"] = overview

    onboarding = dict(updated_plan.get("onboarding_data") or {})
    onboarding["study_hours_per_day"] = reevaluation.new_hours
    updated_plan["onboarding_data"] = onboarding
    updated_plan["target_daily_hours"] = reevaluation.new_hours

    if reevaluation.schedule_reevaluation_required:
        updated_plan["requires_rebalance"] = True
        updated_plan["schedule_reevaluation_required"] = True
        updated_plan["rebalance_trigger"] = (
            "study_hours_reduced" if reevaluation.hours_reduced else "study_hours_capacity_overflow"
        )
        updated_plan["reevaluation_audit"] = reevaluation.to_dict()
        updated_plan["last_reevaluated_at"] = datetime.now(timezone.utc).isoformat()

    return updated_plan


def update_student_profile_with_reevaluation(
    db: Any,
    user_id: str,
    new_study_hours: float,
    semester: Optional[int] = None,
    goals: Optional[Union[str, List[str]]] = None,
    subjects: Optional[List[str]] = None,
    enforce_strict_ceiling: bool = True,
) -> Dict[str, Any]:
    """
    Executes profile update with automated schedule re-evaluation check against active study plan.
    Safe for mock DB in isolation tests and live Supabase client.
    """
    # 1. Fetch previous profile to retrieve prior daily study hours
    prev_profile_res = (
        db.table("student_profiles")
        .select("*")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    prev_profile = prev_profile_res.data[0] if (prev_profile_res and prev_profile_res.data) else {}
    previous_hours = prev_profile.get("study_hours_per_day")

    # 2. Fetch active study plan for user
    plan_res = (
        db.table("study_plans")
        .select("id, plan_data")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    plan_row = plan_res.data[0] if (plan_res and plan_res.data) else None
    plan_data = (plan_row.get("plan_data") or {}) if plan_row else {}
    weekly_schedule = plan_data.get("weekly_schedule") or []

    # 3. Deterministically evaluate whether hours change requires re-evaluation
    reeval_result = evaluate_profile_hours_update(
        new_hours=new_study_hours,
        previous_hours=previous_hours,
        weekly_schedule=weekly_schedule,
        enforce_strict_ceiling=enforce_strict_ceiling,
    )

    # 4. Upsert updated profile into student_profiles
    profile_payload: Dict[str, Any] = {
        "user_id": user_id,
        "study_hours_per_day": reeval_result.new_hours,
        "onboarding_completed": True,
    }
    if semester is not None:
        profile_payload["semester"] = semester
    elif "semester" in prev_profile:
        profile_payload["semester"] = prev_profile["semester"]

    if goals is not None:
        profile_payload["goals"] = goals if isinstance(goals, list) else [goals]
    elif "goals" in prev_profile:
        profile_payload["goals"] = prev_profile["goals"]

    if subjects is not None:
        profile_payload["subjects"] = subjects
    elif "subjects" in prev_profile:
        profile_payload["subjects"] = prev_profile["subjects"]

    saved_profile_res = (
        db.table("student_profiles")
        .upsert(profile_payload, on_conflict="user_id")
        .execute()
    )
    saved_profile = saved_profile_res.data[0] if (saved_profile_res and saved_profile_res.data) else profile_payload

    # 5. If schedule re-evaluation is required and active plan exists, update the plan
    plan_updated = False
    if plan_row and reeval_result.schedule_reevaluation_required:
        updated_plan_data = apply_reevaluation_to_plan(plan_data, reeval_result)
        now_iso = datetime.now(timezone.utc).isoformat()
        db.table("study_plans").update({
            "plan_data": updated_plan_data,
            "updated_at": now_iso,
        }).eq("id", plan_row["id"]).execute()
        plan_updated = True

    return {
        "success": True,
        "profile": saved_profile,
        "schedule_reevaluation": reeval_result.to_dict(),
        "active_plan_flagged": plan_updated,
    }
