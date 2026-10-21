"""
Deterministic Weak Topics Service.

Flags academic subjects and topics requiring targeted revision based STRICTLY on
empirically observed execution deficits:
  1. Explicitly missed study sessions (exec_status == 'missed' or 0 minutes logged).
  2. Sub-50% study durations (actual_minutes < 0.50 * planned_minutes).
  3. Overdue incomplete sessions from previous days.

Avoids ungrounded, speculative, or hallucinated AI claims by evaluating only
quantifiable, audit-ready metrics (timestamps, planned vs. actual minutes, and completion states).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum threshold in minutes to consider a partial duration deficit significant
MIN_DEFICIT_THRESHOLD_MINUTES = 15

# Sub-50% duration ratio threshold
SUB_50_PERCENT_RATIO = 0.50


def is_sub50_duration(planned_minutes: int, actual_minutes: int) -> bool:
    """
    Returns True if the student completed strictly less than 50% of the planned study duration
    and the remaining deficit is at least MIN_DEFICIT_THRESHOLD_MINUTES.
    """
    if planned_minutes <= 0:
        return False
    ratio = actual_minutes / planned_minutes
    deficit = planned_minutes - actual_minutes
    return ratio < SUB_50_PERCENT_RATIO and deficit >= MIN_DEFICIT_THRESHOLD_MINUTES


class WeakTopicsService:
    """
    Service responsible for deterministic diagnostic evaluation of student study plans.
    Produces auditable, rule-based explainability tags without generative AI speculation.
    """

    @staticmethod
    def extract_session_diagnostics(
        sess: Dict[str, Any],
        day_idx: int,
        current_day_idx: int,
        executions: Dict[str, Any],
        completed_ids: set,
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts planned vs actual metrics for a single study session.
        Returns None for future unattempted sessions so they are not falsely counted as deficits.
        """
        sess_id = sess.get("id") or f"sess-d{day_idx}"
        planned_mins = int((sess.get("duration_hours") or 1.0) * 60)
        exec_info = executions.get(sess_id) or {}
        exec_status = exec_info.get("status")
        has_exec_record = exec_status is not None or sess_id in completed_ids or "actual_minutes" in exec_info

        # Future session that has not arrived yet and has no logged record is on-track
        if day_idx > current_day_idx and not has_exec_record:
            return None

        is_done = False
        is_missed = False
        is_sub50 = False

        if exec_status == "completed" or sess_id in completed_ids:
            actual_mins = exec_info.get("actual_minutes", planned_mins)
            is_done = True
        elif exec_status == "missed":
            actual_mins = 0
            is_missed = True
        elif exec_status == "partially_completed":
            actual_mins = exec_info.get("actual_minutes", int(planned_mins / 2))
            if is_sub50_duration(planned_mins, actual_mins):
                is_sub50 = True
        elif day_idx < current_day_idx and sess_id not in completed_ids and exec_status not in ["completed", "rebalanced"]:
            # Past-due uncompleted session treated as missed
            actual_mins = exec_info.get("actual_minutes", 0)
            is_missed = True
        else:
            actual_mins = exec_info.get("actual_minutes", 0)
            if actual_mins > 0 and is_sub50_duration(planned_mins, actual_mins):
                is_sub50 = True
            elif exec_status == "in_progress":
                is_sub50 = False

        return {
            "sess_id": sess_id,
            "subject": sess.get("subject", "General Study"),
            "topic": sess.get("topic", "Core Topic"),
            "priority": sess.get("priority", "medium"),
            "planned_mins": planned_mins,
            "actual_mins": actual_mins,
            "is_done": is_done,
            "is_missed": is_missed,
            "is_sub50": is_sub50,
            "exec_status": exec_status,
        }

    @classmethod
    def compute_weak_topics(
        cls,
        plan_data: Dict[str, Any],
        current_day_idx: int = 7,
    ) -> List[Dict[str, Any]]:
        """
        Deterministically evaluates all sessions in the weekly schedule and groups them by
        Subject and Topic. Topics are flagged as 'Needs Revision' strictly when:
          - At least one session was explicitly missed.
          - Or study duration is sub-50% of the planned duration.
          - Or multi-session completion rate falls below 50%.
        """
        weekly_schedule = plan_data.get("weekly_schedule") or []
        completed_ids = set(plan_data.get("completed_task_ids") or [])
        executions = plan_data.get("task_executions") or {}

        subject_map: Dict[str, Dict[str, Any]] = {}

        for day_idx, day_item in enumerate(weekly_schedule, start=1):
            sessions = day_item.get("sessions") or []
            for s_idx, sess in enumerate(sessions, start=1):
                diag = cls.extract_session_diagnostics(
                    sess=sess,
                    day_idx=day_idx,
                    current_day_idx=current_day_idx,
                    executions=executions,
                    completed_ids=completed_ids,
                )

                if diag is None:
                    continue

                key = f"{diag['subject']}::{diag['topic']}"
                if key not in subject_map:
                    subject_map[key] = {
                        "id": f"wt-{diag['sess_id']}",
                        "subject": diag["subject"],
                        "topic": diag["topic"],
                        "planned_minutes": 0,
                        "actual_minutes": 0,
                        "total_sessions": 0,
                        "completed_sessions": 0,
                        "missed_sessions": 0,
                        "sub50_sessions": 0,
                        "priority": diag["priority"],
                    }

                entry = subject_map[key]
                entry["planned_minutes"] += diag["planned_mins"]
                entry["actual_minutes"] += diag["actual_mins"]
                entry["total_sessions"] += 1

                if diag["is_done"]:
                    entry["completed_sessions"] += 1
                if diag["is_missed"]:
                    entry["missed_sessions"] += 1
                if diag["is_sub50"]:
                    entry["sub50_sessions"] += 1

                # If any session for this topic is high priority, elevate topic priority
                if diag["priority"] == "high":
                    entry["priority"] = "high"

        weak_topics: List[Dict[str, Any]] = []

        for key, data in subject_map.items():
            tags: List[str] = []
            is_needs_revision = False
            severity = "low"
            deficit = max(0, data["planned_minutes"] - data["actual_minutes"])
            comp_rate = int((data["actual_minutes"] / max(1, data["planned_minutes"])) * 100)

            # -------------------------------------------------------------
            # Deterministic Diagnostic Rule 1: Explicitly Missed Sessions
            # -------------------------------------------------------------
            if data["missed_sessions"] > 0:
                is_needs_revision = True
                severity = "high"
                tags.append(f"Missed Task: {data['topic']}")
                if data["missed_sessions"] > 1:
                    tags.append(f"{data['missed_sessions']} Missed Sessions")

            # -------------------------------------------------------------
            # Deterministic Diagnostic Rule 2: Sub-50% Study Durations
            # -------------------------------------------------------------
            if data["sub50_sessions"] > 0 or comp_rate < 50:
                is_needs_revision = True
                tags.append(f"Sub-50% Study Duration ({comp_rate}%)")
                if severity != "high":
                    severity = "medium"

            # -------------------------------------------------------------
            # Deterministic Diagnostic Rule 3: Substantial Study Deficit
            # -------------------------------------------------------------
            if deficit >= MIN_DEFICIT_THRESHOLD_MINUTES:
                is_needs_revision = True
                if deficit >= 60:
                    severity = "high"
                elif severity == "low":
                    severity = "medium"
                tags.append(f"Study Deficit: -{deficit}m")

            # -------------------------------------------------------------
            # Deterministic Diagnostic Rule 4: Multi-Session Low Completion
            # -------------------------------------------------------------
            if data["total_sessions"] > 0 and data["completed_sessions"] < data["total_sessions"]:
                session_comp_rate = int((data["completed_sessions"] / data["total_sessions"]) * 100)
                if session_comp_rate < 50:
                    is_needs_revision = True
                    tags.append(f"Completion Rate: {session_comp_rate}% (Low Mastery)")

            # -------------------------------------------------------------
            # Deterministic Diagnostic Rule 5: High Priority Exam Target
            # -------------------------------------------------------------
            if data["priority"] == "high" and is_needs_revision:
                tags.append("High Priority Exam Target")

            if is_needs_revision:
                # Deduplicate explainability tags while preserving order
                unique_tags = list(dict.fromkeys(tags))

                weak_topics.append({
                    "id": data["id"],
                    "subject": data["subject"],
                    "topic": data["topic"],
                    "status": "Needs Revision",
                    "severity": severity,
                    "explainability_tags": unique_tags,
                    "missed_minutes": deficit,
                    "planned_minutes": data["planned_minutes"],
                    "actual_minutes": data["actual_minutes"],
                    "completion_rate": min(100, max(0, comp_rate)),
                    "missed_sessions": data["missed_sessions"],
                    "sub50_sessions": data["sub50_sessions"],
                    "total_sessions": data["total_sessions"],
                    "recommended_query": f"{data['subject']} {data['topic']}".strip(),
                    "reason_summary": f"Flagged based on {data['missed_sessions']} missed session(s) and {deficit}m deficit ({comp_rate}% completion).",
                })

        # Deterministic Ranking:
        # 1. Topics with explicitly missed sessions
        # 2. Severity ('high' > 'medium' > 'low')
        # 3. Greatest study deficit (missed minutes)
        severity_rank = {"high": 3, "medium": 2, "low": 1}
        weak_topics.sort(
            key=lambda x: (
                x.get("missed_sessions", 0) > 0,
                severity_rank.get(x["severity"], 0),
                x["missed_minutes"],
            ),
            reverse=True,
        )

        return weak_topics


# Module-level convenience function preserving existing function signature
def compute_weak_topics(
    plan_data: Dict[str, Any],
    current_day_idx: int = 7,
) -> List[Dict[str, Any]]:
    """
    Module-level entry point for deterministic weak topic computation.
    """
    return WeakTopicsService.compute_weak_topics(
        plan_data=plan_data,
        current_day_idx=current_day_idx,
    )


# Singleton instance
weak_topics_service = WeakTopicsService()
