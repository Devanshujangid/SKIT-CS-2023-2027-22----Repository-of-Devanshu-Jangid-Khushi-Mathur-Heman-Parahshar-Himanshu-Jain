"""
Unit tests for Admin CRUD and Leaderboard API Pydantic Schemas.

Verifies:
1. AdminCreateResource & AdminUpdateResource validation (URL check, difficulty normalization,
   skills deduplication, rating rounding, non-empty PATCH invariant).
2. AdminResourceResponse, AdminResourceListResponse, AdminResourceDeleteResponse serialization.
3. AdminCreateStudent & AdminUpdateStudent validation (email format, semester bounds 1-8,
   daily study hours bounds 0.5-16.0, goals normalization, non-empty PATCH invariant).
4. AdminStudentRecord, AdminStudentMutationResponse, AdminStudentListResponse serialization.
5. LeaderboardBadge, LeaderboardEntry, LeaderboardUserStanding, LeaderboardResponse validation
   (ranking monotonicity, participant count invariant, adherence bounds, PII exclusion).
"""

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

from pydantic import ValidationError

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.admin_and_leaderboard import (
    AdminCreateResource,
    AdminUpdateResource,
    AdminResourceResponse,
    AdminResourceListResponse,
    AdminResourceDeleteResponse,
    AdminCreateStudent,
    AdminUpdateStudent,
    AdminStudentRecord,
    AdminStudentMutationResponse,
    AdminStudentListResponse,
    AdminDeleteStudentResponse,
    LeaderboardBadge,
    LeaderboardEntry,
    LeaderboardUserStanding,
    LeaderboardResponse,
)


class TestAdminResourceSchemas(unittest.TestCase):
    """Tests for Admin Resource CRUD schemas."""

    def test_admin_create_resource_valid_and_normalizes(self):
        payload = AdminCreateResource(
            title="  Operating Systems: Three Easy Pieces  ",
            description="Comprehensive coverage of virtualization, concurrency, and persistence.",
            url="https://pages.cs.wisc.edu/~remzi/OSTEP/",
            subject="Operating Systems",
            provider="UW-Madison",
            difficulty_level="intermediate",
            skills="Concurrency, Semaphores, concurrency, Virtual Memory",
            rating=4.867,
            estimated_hours=24.0,
            resource_type="article",
        )
        self.assertEqual(payload.title, "Operating Systems: Three Easy Pieces")
        self.assertEqual(payload.difficulty_level, "Intermediate")
        self.assertEqual(payload.skills, ["Concurrency", "Semaphores", "Virtual Memory"])
        self.assertEqual(payload.rating, 4.87)
        self.assertTrue(payload.is_active)

    def test_admin_create_resource_rejects_invalid_url(self):
        for bad_url in ["not-a-url", "javascript:alert(1)", "ftp://files.example.com/os.pdf", "https://"]:
            with self.subTest(url=bad_url):
                with self.assertRaises(ValidationError):
                    AdminCreateResource(
                        title="Operating Systems Course",
                        description="Valid description of at least ten characters.",
                        url=bad_url,
                        subject="Operating Systems",
                    )

    def test_admin_update_resource_requires_at_least_one_field(self):
        with self.assertRaises(ValidationError):
            AdminUpdateResource()

        patch_payload = AdminUpdateResource(is_active=False, rating=4.5)
        self.assertFalse(patch_payload.is_active)
        self.assertEqual(patch_payload.rating, 4.5)
        self.assertIsNone(patch_payload.title)

    def test_admin_resource_response_and_list_envelopes(self):
        now = datetime.now(timezone.utc)
        item = AdminResourceResponse(
            id="res-001",
            title="Algorithms Part I",
            description="Princeton algorithms course covering sorting, graphs, and data structures.",
            url="https://www.coursera.org/learn/algorithms-part1",
            subject="Data Structures & Algorithms",
            provider="Princeton University",
            difficulty_level="Intermediate",
            skills=["Graphs", "Sorting"],
            rating=4.9,
            estimated_hours=30.0,
            resource_type="course",
            is_active=True,
            created_by="clerk_admin_01",
            created_at=now,
            updated_at=now,
        )
        listing = AdminResourceListResponse(total=1, page=1, page_size=20, resources=[item])
        self.assertEqual(listing.total, 1)
        self.assertEqual(listing.resources[0].id, "res-001")

        deleted = AdminResourceDeleteResponse(deleted_id="res-001")
        self.assertTrue(deleted.success)
        self.assertEqual(deleted.deleted_id, "res-001")


class TestAdminStudentSchemas(unittest.TestCase):
    """Tests for Admin Student CRUD schemas."""

    def test_admin_create_student_valid_and_normalizes(self):
        student = AdminCreateStudent(
            clerk_id="user_2abc123xyz",
            email="student@skit.ac.in",
            full_name="Himanshu Jain",
            semester=5,
            study_hours_per_day=4.567,
            goals="Achieve 9.0+ CGPA, GATE CS Prep, achieve 9.0+ cgpa",
            subjects=["Operating Systems", "Computer Networks", "Operating Systems"],
        )
        self.assertEqual(student.role, "student")
        self.assertEqual(student.study_hours_per_day, 4.57)
        self.assertEqual(student.goals, ["Achieve 9.0+ CGPA", "GATE CS Prep"])
        self.assertEqual(student.subjects, ["Operating Systems", "Computer Networks"])

    def test_admin_create_student_rejects_invalid_bounds(self):
        # Invalid email
        with self.assertRaises(ValidationError):
            AdminCreateStudent(
                clerk_id="user_123",
                email="invalid-email",
                semester=5,
                study_hours_per_day=4.0,
                goals=["GATE Prep"],
            )

        # Semester out of range (1-8)
        with self.assertRaises(ValidationError):
            AdminCreateStudent(
                clerk_id="user_123",
                email="student@skit.ac.in",
                semester=9,
                study_hours_per_day=4.0,
                goals=["GATE Prep"],
            )

        # Study hours out of range (0.5 - 16.0)
        with self.assertRaises(ValidationError):
            AdminCreateStudent(
                clerk_id="user_123",
                email="student@skit.ac.in",
                semester=5,
                study_hours_per_day=20.0,
                goals=["GATE Prep"],
            )

        # Empty goals rejected
        with self.assertRaises(ValidationError):
            AdminCreateStudent(
                clerk_id="user_123",
                email="student@skit.ac.in",
                semester=5,
                study_hours_per_day=4.0,
                goals="   ",
            )

    def test_admin_update_student_requires_at_least_one_field(self):
        with self.assertRaises(ValidationError):
            AdminUpdateStudent()

        update = AdminUpdateStudent(
            semester=6,
            is_suspended=False,
            admin_notes="Promoted to Semester 6",
        )
        self.assertEqual(update.semester, 6)
        self.assertFalse(update.is_suspended)

    def test_admin_student_response_envelopes(self):
        record = AdminStudentRecord(
            id="a0000000-0000-0000-0000-000000000001",
            clerk_id="user_2abc123xyz",
            email="student@skit.ac.in",
            full_name="Himanshu Jain",
            role="student",
            semester=5,
            study_hours_per_day=4.5,
            goals=["GATE CS Prep"],
            subjects=["Operating Systems"],
            has_active_plan=True,
            total_tasks=10,
            completed_tasks=9,
            completion_rate=90,
            diagnostic_status="On-Track",
        )
        mutation_res = AdminStudentMutationResponse(
            message="Student updated successfully",
            student=record,
        )
        self.assertTrue(mutation_res.success)
        self.assertEqual(mutation_res.student.completion_rate, 90)

        roster_res = AdminStudentListResponse(
            admin_clerk_id="admin_clerk_1",
            total_students=1,
            students=[record],
        )
        self.assertEqual(roster_res.total_students, 1)

        delete_res = AdminDeleteStudentResponse(deleted_user_id=record.id)
        self.assertEqual(delete_res.deleted_user_id, record.id)


class TestLeaderboardSchemas(unittest.TestCase):
    """Tests for Leaderboard API response schemas."""

    def test_leaderboard_response_validates_ordered_entries(self):
        entry_1 = LeaderboardEntry(
            rank=1,
            student_id="stu-uuid-1",
            display_name="Himanshu J.",
            semester=5,
            primary_focus="Operating Systems",
            xp_score=1450,
            logged_hours=35.0,
            scheduled_hours=35.0,
            adherence_rate=100,
            completed_tasks=14,
            streak_days=7,
            rank_delta=1,
            badges=[LeaderboardBadge(badge_id="streak_7", label="7-Day Streak", tier="gold")],
            is_current_user=True,
        )
        entry_2 = LeaderboardEntry(
            rank=2,
            student_id="stu-uuid-2",
            display_name="Khushi M.",
            semester=5,
            primary_focus="Computer Networks",
            xp_score=1320,
            logged_hours=32.5,
            scheduled_hours=34.0,
            adherence_rate=96,
            completed_tasks=13,
            streak_days=5,
            rank_delta=0,
        )

        response = LeaderboardResponse(
            timeframe="weekly",
            sorted_by="xp_score",
            semester_filter=5,
            total_participants=42,
            current_user_standing=LeaderboardUserStanding(
                rank=1,
                percentile=97.6,
                xp_score=1450,
                points_to_next_rank=0,
                entry=entry_1,
            ),
            entries=[entry_1, entry_2],
        )

        self.assertTrue(response.success)
        self.assertEqual(len(response.entries), 2)
        self.assertEqual(response.current_user_standing.rank, 1)
        # Ensure peer entries do not expose email or clerk_id fields
        dumped_entry = response.entries[1].model_dump()
        self.assertNotIn("email", dumped_entry)
        self.assertNotIn("clerk_id", dumped_entry)

    def test_leaderboard_rejects_descending_ranks_or_invalid_participant_count(self):
        e1 = LeaderboardEntry(
            rank=2,
            student_id="stu-1",
            display_name="Student A",
            semester=5,
            xp_score=900,
            logged_hours=10.0,
            scheduled_hours=12.0,
            adherence_rate=83,
            completed_tasks=5,
        )
        e2 = LeaderboardEntry(
            rank=1,
            student_id="stu-2",
            display_name="Student B",
            semester=5,
            xp_score=1000,
            logged_hours=12.0,
            scheduled_hours=12.0,
            adherence_rate=100,
            completed_tasks=6,
        )

        # Out-of-order ranks rejected
        with self.assertRaises(ValidationError):
            LeaderboardResponse(total_participants=10, entries=[e1, e2])

        # total_participants < len(entries) rejected
        with self.assertRaises(ValidationError):
            LeaderboardResponse(total_participants=1, entries=[e2, e1])


if __name__ == "__main__":
    unittest.main()

