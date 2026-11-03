"""
Unit tests for Settings API Pydantic Schemas.

Validates:
1. Study hours updates (range 0.5h-16h, consecutive study limit <= daily limit).
2. Academic goals updates (list normalization, string stripping, semester & CGPA bounds).
3. Password security updates (minimum length, uppercase, lowercase, digit, special character,
   common password rejection, mismatch detection, current password difference).
4. Consolidated SettingsUpdateRequest.
"""

import sys
import unittest
from pathlib import Path

# Add backend directory to sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from pydantic import ValidationError
from schemas.settings import (
    StudyHoursUpdateSchema,
    AcademicGoalsUpdateSchema,
    PasswordUpdateSchema,
    NotificationSettingsSchema,
    SettingsUpdateRequest,
    SettingsResponseSchema,
)


class TestStudyHoursUpdateSchema(unittest.TestCase):
    def test_valid_study_hours(self):
        schema = StudyHoursUpdateSchema(
            study_hours_per_day=4.5,
            max_consecutive_hours=2.0,
            preferred_time_slots=["Morning (06:00 - 09:00)", "Evening (18:00 - 21:00)"],
            session_pacing="Deep Work (50m study / 10m break)"
        )
        self.assertEqual(schema.study_hours_per_day, 4.5)
        self.assertEqual(schema.max_consecutive_hours, 2.0)
        self.assertTrue(schema.enforce_strict_ceiling)

    def test_study_hours_below_minimum_fails(self):
        with self.assertRaises(ValidationError):
            StudyHoursUpdateSchema(study_hours_per_day=0.2)

    def test_study_hours_above_maximum_fails(self):
        with self.assertRaises(ValidationError):
            StudyHoursUpdateSchema(study_hours_per_day=18.0)

    def test_consecutive_hours_exceeding_daily_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            StudyHoursUpdateSchema(
                study_hours_per_day=3.0,
                max_consecutive_hours=4.0
            )
        self.assertIn("cannot exceed total study_hours_per_day", str(ctx.exception))

    def test_time_slots_string_normalization(self):
        schema = StudyHoursUpdateSchema(
            study_hours_per_day=4.0,
            preferred_time_slots="Morning (06:00 - 09:00), Evening (18:00 - 21:00)"
        )
        self.assertEqual(len(schema.preferred_time_slots), 2)
        self.assertIn("Morning (06:00 - 09:00)", schema.preferred_time_slots)


class TestAcademicGoalsUpdateSchema(unittest.TestCase):
    def test_valid_academic_goals(self):
        schema = AcademicGoalsUpdateSchema(
            goals=["Score 9.0+ CGPA", "Crack GATE CS 2026", "Master Operating Systems"],
            target_goal_summary="Targeting 8.5+ CGPA and strong GATE CSE core foundation",
            primary_focus="Operating Systems",
            semester=5,
            target_cgpa=9.25,
            subjects=["Operating Systems", "Computer Networks", "DBMS"]
        )
        self.assertEqual(len(schema.goals), 3)
        self.assertEqual(schema.semester, 5)
        self.assertEqual(schema.target_cgpa, 9.25)

    def test_goals_string_normalization(self):
        schema = AcademicGoalsUpdateSchema(
            goals="Score 9.0+ CGPA, Crack GATE CS 2026",
            semester=5
        )
        self.assertEqual(schema.goals, ["Score 9.0+ CGPA", "Crack GATE CS 2026"])

    def test_empty_goals_fails(self):
        with self.assertRaises(ValidationError):
            AcademicGoalsUpdateSchema(goals=[])

        with self.assertRaises(ValidationError):
            AcademicGoalsUpdateSchema(goals="   ,  ")

    def test_semester_out_of_range_fails(self):
        with self.assertRaises(ValidationError):
            AcademicGoalsUpdateSchema(goals=["Goal 1"], semester=0)

        with self.assertRaises(ValidationError):
            AcademicGoalsUpdateSchema(goals=["Goal 1"], semester=9)

    def test_target_cgpa_out_of_range_fails(self):
        with self.assertRaises(ValidationError):
            AcademicGoalsUpdateSchema(goals=["Goal 1"], target_cgpa=10.5)

        with self.assertRaises(ValidationError):
            AcademicGoalsUpdateSchema(goals=["Goal 1"], target_cgpa=-1.0)


class TestPasswordUpdateSchema(unittest.TestCase):
    def test_valid_secure_password(self):
        schema = PasswordUpdateSchema(
            current_password="OldPassword123!",
            new_password="NewSecurePass2026@",
            confirm_password="NewSecurePass2026@"
        )
        self.assertEqual(schema.new_password, "NewSecurePass2026@")

    def test_password_too_short_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="Ab1!",
                confirm_password="Ab1!"
            )
        self.assertIn("at least 8 characters", str(ctx.exception))

    def test_password_missing_uppercase_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="newsecurepass2026@",
                confirm_password="newsecurepass2026@"
            )
        self.assertIn("uppercase letter", str(ctx.exception))

    def test_password_missing_lowercase_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="NEWSECUREPASS2026@",
                confirm_password="NEWSECUREPASS2026@"
            )
        self.assertIn("lowercase letter", str(ctx.exception))

    def test_password_missing_digit_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="NewSecurePassSpecial@",
                confirm_password="NewSecurePassSpecial@"
            )
        self.assertIn("numeric digit", str(ctx.exception))

    def test_password_missing_special_char_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="NewSecurePass2026",
                confirm_password="NewSecurePass2026"
            )
        self.assertIn("special character", str(ctx.exception))

    def test_common_weak_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="password123",
                confirm_password="password123"
            )
        self.assertIn("easily guessable", str(ctx.exception))

    def test_password_mismatch_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="NewSecurePass2026@",
                confirm_password="DifferentPass2026@"
            )
        self.assertIn("do not match", str(ctx.exception))

    def test_reusing_current_password_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            PasswordUpdateSchema(
                current_password="SamePassword2026@",
                new_password="SamePassword2026@",
                confirm_password="SamePassword2026@"
            )
        self.assertIn("cannot be the same as your current password", str(ctx.exception))


class TestUnifiedSettingsUpdateRequest(unittest.TestCase):
    def test_valid_partial_update_study_hours(self):
        req = SettingsUpdateRequest(
            study_hours=StudyHoursUpdateSchema(study_hours_per_day=5.0)
        )
        self.assertIsNotNone(req.study_hours)
        self.assertIsNone(req.academic_goals)

    def test_valid_full_update(self):
        req = SettingsUpdateRequest(
            study_hours=StudyHoursUpdateSchema(study_hours_per_day=4.5),
            academic_goals=AcademicGoalsUpdateSchema(goals=["Score 9.0+ CGPA"], semester=5),
            security=PasswordUpdateSchema(
                current_password="OldPass123!",
                new_password="NewPass123!@",
                confirm_password="NewPass123!@"
            ),
            notifications=NotificationSettingsSchema(daily_digest=True)
        )
        self.assertEqual(req.study_hours.study_hours_per_day, 4.5)
        self.assertEqual(req.academic_goals.semester, 5)
        self.assertTrue(req.notifications.daily_digest)

    def test_empty_update_request_fails(self):
        with self.assertRaises(ValidationError) as ctx:
            SettingsUpdateRequest()
        self.assertIn("At least one settings category", str(ctx.exception))

    def test_settings_response_schema(self):
        res = SettingsResponseSchema(
            success=True,
            message="Preferences updated successfully",
            updated_fields=["study_hours", "academic_goals"],
            data={"daily_hours": 4.5}
        )
        self.assertTrue(res.success)
        self.assertEqual(len(res.updated_fields), 2)


if __name__ == "__main__":
    unittest.main()
