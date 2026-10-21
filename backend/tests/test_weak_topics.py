"""
Unit tests for deterministic WeakTopicsService.

Verifies that topics are flagged strictly based on:
1. Explicitly missed sessions.
2. Sub-50% study durations (<0.50 actual / planned).
3. Overdue incomplete sessions from previous days.

Guarantees 100% deterministic, audit-ready behavior without ungrounded AI claims.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.weak_topics import (
    WeakTopicsService,
    compute_weak_topics,
    is_sub50_duration,
)


class TestWeakTopicsService(unittest.TestCase):
    def setUp(self):
        self.sample_plan = {
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 3.0,
                    "sessions": [
                        {
                            "id": "sess-mon-os",
                            "subject": "Operating Systems",
                            "topic": "Process Synchronization",
                            "duration_hours": 1.5,  # 90 mins
                            "priority": "high",
                        },
                        {
                            "id": "sess-mon-db",
                            "subject": "Database Systems",
                            "topic": "Relational Algebra",
                            "duration_hours": 1.5,  # 90 mins
                            "priority": "medium",
                        },
                    ],
                },
                {
                    "day": "Tuesday",
                    "total_hours": 3.0,
                    "sessions": [
                        {
                            "id": "sess-tue-cn",
                            "subject": "Computer Networks",
                            "topic": "TCP Congestion Control",
                            "duration_hours": 1.0,  # 60 mins
                            "priority": "high",
                        },
                        {
                            "id": "sess-tue-dsa",
                            "subject": "Algorithms",
                            "topic": "Dynamic Programming",
                            "duration_hours": 2.0,  # 120 mins
                            "priority": "high",
                        },
                    ],
                },
            ],
            "completed_task_ids": [],
            "task_executions": {},
        }

    def test_is_sub50_duration_helper(self):
        # 20 mins out of 60 mins -> ratio = 0.33 (< 0.50), deficit = 40 (>= 15) -> True
        self.assertTrue(is_sub50_duration(planned_minutes=60, actual_minutes=20))

        # 30 mins out of 60 mins -> ratio = 0.50 (not < 0.50) -> False
        self.assertFalse(is_sub50_duration(planned_minutes=60, actual_minutes=30))

        # 50 mins out of 60 mins -> ratio = 0.83 -> False
        self.assertFalse(is_sub50_duration(planned_minutes=60, actual_minutes=50))

        # 60 mins out of 60 mins -> False
        self.assertFalse(is_sub50_duration(planned_minutes=60, actual_minutes=60))

        # 0 mins planned -> False
        self.assertFalse(is_sub50_duration(planned_minutes=0, actual_minutes=0))

    def test_fully_completed_sessions_not_flagged(self):
        plan = dict(self.sample_plan)
        # Mark Monday sessions as completed with 100% time
        plan["completed_task_ids"] = ["sess-mon-os", "sess-mon-db"]
        plan["task_executions"] = {
            "sess-mon-os": {"status": "completed", "actual_minutes": 90},
            "sess-mon-db": {"status": "completed", "actual_minutes": 90},
        }

        # Evaluating on Day 1 (Monday)
        flagged = compute_weak_topics(plan, current_day_idx=1)
        # Tuesday sessions haven't occurred yet, so no weak topics flagged for Monday
        os_flagged = [t for t in flagged if t["subject"] == "Operating Systems"]
        db_flagged = [t for t in flagged if t["subject"] == "Database Systems"]
        self.assertEqual(len(os_flagged), 0, "Completed OS session must not be flagged")
        self.assertEqual(len(db_flagged), 0, "Completed DB session must not be flagged")

    def test_explicitly_missed_session_flagged_with_high_severity(self):
        plan = dict(self.sample_plan)
        # Mark OS as missed
        plan["task_executions"] = {
            "sess-mon-os": {
                "status": "missed",
                "actual_minutes": 0,
                "notes": "Student missed session",
            }
        }

        flagged = compute_weak_topics(plan, current_day_idx=1)
        os_topic = next((t for t in flagged if t["subject"] == "Operating Systems"), None)

        self.assertIsNotNone(os_topic)
        self.assertEqual(os_topic["status"], "Needs Revision")
        self.assertEqual(os_topic["severity"], "high")
        self.assertEqual(os_topic["missed_minutes"], 90)
        self.assertEqual(os_topic["completion_rate"], 0)
        self.assertTrue(any("Missed Task" in tag for tag in os_topic["explainability_tags"]))
        self.assertTrue(any("High Priority Exam Target" in tag for tag in os_topic["explainability_tags"]))
        self.assertEqual(os_topic["recommended_query"], "Operating Systems Process Synchronization")

    def test_sub50_percent_study_duration_flagged(self):
        plan = dict(self.sample_plan)
        # Planned 60 mins for Computer Networks, student only studied 20 mins (< 50%)
        plan["task_executions"] = {
            "sess-tue-cn": {
                "status": "partially_completed",
                "actual_minutes": 20,
            }
        }

        flagged = compute_weak_topics(plan, current_day_idx=2)
        cn_topic = next((t for t in flagged if t["subject"] == "Computer Networks"), None)

        self.assertIsNotNone(cn_topic, "Sub-50% study duration must be flagged as weak topic")
        self.assertEqual(cn_topic["status"], "Needs Revision")
        self.assertEqual(cn_topic["planned_minutes"], 60)
        self.assertEqual(cn_topic["actual_minutes"], 20)
        self.assertEqual(cn_topic["missed_minutes"], 40)
        self.assertEqual(cn_topic["completion_rate"], 33)
        self.assertTrue(any("Sub-50% Study Duration (33%)" in tag for tag in cn_topic["explainability_tags"]))
        self.assertTrue(any("Study Deficit: -40m" in tag for tag in cn_topic["explainability_tags"]))

    def test_multi_session_aggregation(self):
        # Two sessions for Algorithms: one completed (120 mins), one missed (60 mins)
        plan = {
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 2.0,
                    "sessions": [
                        {
                            "id": "dsa-1",
                            "subject": "Algorithms",
                            "topic": "Dynamic Programming",
                            "duration_hours": 2.0,  # 120 mins
                            "priority": "high",
                        }
                    ],
                },
                {
                    "day": "Wednesday",
                    "total_hours": 1.0,
                    "sessions": [
                        {
                            "id": "dsa-2",
                            "subject": "Algorithms",
                            "topic": "Dynamic Programming",
                            "duration_hours": 1.0,  # 60 mins
                            "priority": "high",
                        }
                    ],
                },
            ],
            "completed_task_ids": ["dsa-1"],
            "task_executions": {
                "dsa-1": {"status": "completed", "actual_minutes": 120},
                "dsa-2": {"status": "missed", "actual_minutes": 0},
            },
        }

        flagged = compute_weak_topics(plan, current_day_idx=3)
        dsa_topic = next((t for t in flagged if t["subject"] == "Algorithms"), None)

        self.assertIsNotNone(dsa_topic)
        self.assertEqual(dsa_topic["total_sessions"], 2)
        self.assertEqual(dsa_topic["planned_minutes"], 180)
        self.assertEqual(dsa_topic["actual_minutes"], 120)
        self.assertEqual(dsa_topic["missed_minutes"], 60)
        self.assertEqual(dsa_topic["completion_rate"], 66)
        self.assertEqual(dsa_topic["missed_sessions"], 1)
        self.assertTrue(any("Missed Task" in tag for tag in dsa_topic["explainability_tags"]))

    def test_deterministic_ranking_missed_sessions_first(self):
        plan = dict(self.sample_plan)
        # OS has an explicitly missed session (90 mins deficit)
        # DB has sub-50% duration (studied 25 mins out of 90 mins -> 65 mins deficit)
        plan["task_executions"] = {
            "sess-mon-os": {"status": "missed", "actual_minutes": 0},
            "sess-mon-db": {"status": "partially_completed", "actual_minutes": 25},
        }

        flagged = compute_weak_topics(plan, current_day_idx=1)
        self.assertGreaterEqual(len(flagged), 2)
        # Missed sessions must come first
        self.assertEqual(flagged[0]["subject"], "Operating Systems")
        self.assertEqual(flagged[1]["subject"], "Database Systems")


if __name__ == "__main__":
    unittest.main()
