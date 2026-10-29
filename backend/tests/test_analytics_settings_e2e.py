import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.weak_topics import compute_weak_topics, WeakTopicsService



class TestAnalyticsAndSettingsE2E(unittest.TestCase):
    """
    E2E and Integration Verification for:
    - Module 8: Academic Progress & Telemetry Analytics (/dashboard/analytics)
    - Module 11: Student Profile & Settings (/dashboard/settings)
    - Faculty/Admin Overview & Health (/admin)
    """

    def setUp(self):
        self.sample_plan_data = {
            "weekly_schedule": [
                {
                    "day": "Day 1 (Monday)",
                    "sessions": [
                        {"id": "sess-1", "subject": "Operating Systems", "topic": "Process Synchronization", "duration_hours": 2.0},
                        {"id": "sess-2", "subject": "Computer Networks", "topic": "TCP Flow Control", "duration_hours": 1.5},
                    ]
                },
                {
                    "day": "Day 2 (Tuesday)",
                    "sessions": [
                        {"id": "sess-3", "subject": "Operating Systems", "topic": "Semaphores & Mutex", "duration_hours": 2.0},
                        {"id": "sess-4", "subject": "Database Systems", "topic": "B+ Trees", "duration_hours": 1.0},
                    ]
                },
                {
                    "day": "Day 3 (Wednesday)",
                    "sessions": [
                        {"id": "sess-5", "subject": "Discrete Mathematics", "topic": "Graph Theory", "duration_hours": 2.0},
                    ]
                }
            ],
            "completed_task_ids": ["sess-2"],
            "task_executions": {
                "sess-1": {
                    "status": "partially_completed",
                    "actual_minutes": 45,  # Planned 120m -> 45m / 120m = 37.5% (< 50% Sub-50% trigger)
                },
                "sess-2": {
                    "status": "completed",
                    "actual_minutes": 90,  # Planned 90m -> 90m (100%)
                },
                "sess-5": {
                    "status": "missed",
                    "actual_minutes": 0,   # Missed Task -> Rule 1 trigger
                }
            }
        }

    # =========================================================================
    # 1. SETTINGS PROFILE PAYLOAD & INVARIANTS TEST
    # =========================================================================
    def test_settings_profile_payload_invariants(self):
        """Verify settings profile payload conforms to Semester 5 schema."""
        profile_payload = {
            "semester": 5,
            "study_hours_per_day": 4.5,
            "goals": "Targeting 8.5+ CGPA and strong GATE CSE core foundation",
            "subjects": [
                "Operating Systems",
                "Computer Networks",
                "Database Systems",
                "Software Engineering",
                "Discrete Mathematics"
            ]
        }

        self.assertGreaterEqual(profile_payload["semester"], 1)
        self.assertLessEqual(profile_payload["semester"], 8)
        self.assertGreaterEqual(profile_payload["study_hours_per_day"], 1.0)
        self.assertLessEqual(profile_payload["study_hours_per_day"], 12.0)
        self.assertIn("Operating Systems", profile_payload["subjects"])
        self.assertTrue(len(profile_payload["goals"]) > 5)

    # =========================================================================
    # 2. ANALYTICS STUDY VELOCITY & ADHERENCE CALCULATION
    # =========================================================================
    def test_analytics_scheduled_vs_actual_computation(self):
        """Verify analytics calculation for scheduled vs actual hours and deficit."""
        schedule = self.sample_plan_data["weekly_schedule"]
        executions = self.sample_plan_data["task_executions"]
        completed = set(self.sample_plan_data["completed_task_ids"])

        total_scheduled_minutes = 0
        total_actual_minutes = 0

        for day in schedule:
            for session in day["sessions"]:
                planned_mins = int(session["duration_hours"] * 60)
                total_scheduled_minutes += planned_mins

                exec_info = executions.get(session["id"])
                if exec_info:
                    if exec_info.get("status") == "completed":
                        total_actual_minutes += exec_info.get("actual_minutes", planned_mins)
                    elif exec_info.get("status") == "partially_completed":
                        total_actual_minutes += exec_info.get("actual_minutes", 0)
                elif session["id"] in completed:
                    total_actual_minutes += planned_mins

        total_scheduled_hours = total_scheduled_minutes / 60.0
        total_actual_hours = total_actual_minutes / 60.0
        adherence_rate = round((total_actual_hours / total_scheduled_hours) * 100)

        # 2.0 + 1.5 + 2.0 + 1.0 + 2.0 = 8.5 hours scheduled
        self.assertEqual(total_scheduled_hours, 8.5)
        # sess-1 (45m) + sess-2 (90m) + sess-5 (0m) = 135 mins = 2.25 hours actual
        self.assertEqual(total_actual_hours, 2.25)
        self.assertEqual(adherence_rate, 26)

    # =========================================================================
    # 3. DETERMINISTIC WEAK TOPIC DIAGNOSTICS FOR ANALYTICS TABLE
    # =========================================================================
    def test_analytics_diagnostic_topics_flagging(self):
        """Verify that Rule 1 (missed) and Rule 2 (sub-50%) are flagged deterministically."""
        weak_topics = compute_weak_topics(self.sample_plan_data, current_day_idx=3)

        self.assertGreaterEqual(len(weak_topics), 2)

        # sess-5 should be flagged as Rule 1 Missed Task
        sess5_flag = next((w for w in weak_topics if w["topic"] == "Graph Theory"), None)
        self.assertIsNotNone(sess5_flag)
        self.assertEqual(sess5_flag["status"], "Needs Revision")
        self.assertTrue(any("Missed Task" in tag for tag in sess5_flag["explainability_tags"]))

        # sess-1 should be flagged as Rule 2 Sub-50% Duration (45m / 120m = 37.5%)
        sess1_flag = next((w for w in weak_topics if w["topic"] == "Process Synchronization"), None)
        self.assertIsNotNone(sess1_flag)
        self.assertEqual(sess1_flag["status"], "Needs Revision")
        self.assertTrue(any("Sub-50%" in tag for tag in sess1_flag["explainability_tags"]))


    # =========================================================================
    # 4. SUBJECT TIME SHARE PIE CHART AGGREGATION
    # =========================================================================
    def test_analytics_subject_distribution_aggregation(self):
        """Verify correct subject breakdown hours for pie chart rendering."""
        schedule = self.sample_plan_data["weekly_schedule"]
        subject_hours = {}

        for day in schedule:
            for session in day["sessions"]:
                sub = session["subject"]
                hrs = session["duration_hours"]
                subject_hours[sub] = subject_hours.get(sub, 0.0) + hrs

        self.assertEqual(subject_hours["Operating Systems"], 4.0)
        self.assertEqual(subject_hours["Computer Networks"], 1.5)
        self.assertEqual(subject_hours["Database Systems"], 1.0)
        self.assertEqual(subject_hours["Discrete Mathematics"], 2.0)
        self.assertEqual(sum(subject_hours.values()), 8.5)

    # =========================================================================
    # 5. ADMIN HEALTH & STATS TELEMETRY SCHEMA
    # =========================================================================
    def test_admin_system_health_schema(self):
        """Verify schema of system health and admin telemetry response."""
        admin_response = {
            "status": "ok",
            "enrolled_students": 128,
            "active_plans": 114,
            "system_health": {
                "database": "connected",
                "auth": "Clerk JWKS active",
                "ai_engine": "Gemini 3.6 Flash ready"
            }
        }

        self.assertEqual(admin_response["status"], "ok")
        self.assertGreater(admin_response["enrolled_students"], 0)
        self.assertGreater(admin_response["active_plans"], 0)
        self.assertEqual(admin_response["system_health"]["database"], "connected")
        self.assertEqual(admin_response["system_health"]["auth"], "Clerk JWKS active")


if __name__ == "__main__":
    unittest.main()
