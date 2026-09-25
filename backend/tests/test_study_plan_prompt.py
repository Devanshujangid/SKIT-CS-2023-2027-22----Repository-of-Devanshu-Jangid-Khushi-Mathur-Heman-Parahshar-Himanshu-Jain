"""
Isolation Test Suite for Study Plan System Prompt & Schema Adherence
Tests onboarding JSON payloads, prompt construction, and strict Pydantic output schema validation.
"""
import os
import sys
import json
import unittest
from typing import Dict, Any

# Ensure backend root is in PYTHONPATH
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from pydantic import ValidationError
from prompts.study_plan import (
    OnboardingDataInput,
    SubjectInput,
    STUDY_PLAN_SYSTEM_INSTRUCTION,
    build_study_plan_prompt,
    validate_study_plan_output,
    validate_target_score_alignment,
    validate_subject_name_fidelity,
    StudyPlanOutputSchema,
)


class TestOnboardingPayloadIngestion(unittest.TestCase):
    """
    Tests ingestion and normalization of realistic onboarding JSON payloads.
    """

    def setUp(self):
        self.payload_btech_sem5 = {
            "semester": 5,
            "study_hours_per_day": 4.5,
            "goals": ["Score > 9.0 CGPA", "Prepare for GATE CS 2026", "Master Backend Systems"],
            "subjects": [
                {"name": "Operating Systems", "difficulty": "hard", "target_score": "A+"},
                {"name": "Computer Networks", "difficulty": "medium", "target_score": "A"},
                {"name": "Database Management Systems", "difficulty": "medium", "target_score": "A+"},
                {"name": "Theory of Computation", "difficulty": "hard", "target_score": "A"},
            ],
        }

        self.payload_simple_strings = {
            "semester": 3,
            "study_hours_per_day": 3.0,
            "goals": "Build strong DSA foundations",
            "subjects": ["Data Structures", "Discrete Mathematics", "Digital Logic"],
        }

        self.payload_final_year = {
            "semester": 7,
            "study_hours_per_day": 6.0,
            "goals": ["Clear Campus Placements", "Publish Final Year Research Paper"],
            "subjects": [
                {"name": "Distributed Systems", "difficulty": "hard"},
                {"name": "Machine Learning", "difficulty": "hard"},
                "Cloud Computing",
            ],
        }

    def test_sem5_payload_parsing(self):
        input_data = OnboardingDataInput.model_validate(self.payload_btech_sem5)
        self.assertEqual(input_data.semester, 5)
        self.assertEqual(input_data.study_hours_per_day, 4.5)
        self.assertEqual(len(input_data.subjects), 4)
        self.assertEqual(input_data.subjects[0].name, "Operating Systems")
        self.assertEqual(input_data.subjects[0].difficulty, "hard")

    def test_string_subjects_and_goals_normalization(self):
        input_data = OnboardingDataInput.model_validate(self.payload_simple_strings)
        self.assertEqual(input_data.goals, ["Build strong DSA foundations"])
        self.assertEqual(len(input_data.subjects), 3)
        self.assertEqual(input_data.subjects[0].name, "Data Structures")
        self.assertEqual(input_data.subjects[0].difficulty, "medium")

    def test_mixed_subjects_format(self):
        input_data = OnboardingDataInput.model_validate(self.payload_final_year)
        self.assertEqual(len(input_data.subjects), 3)
        self.assertEqual(input_data.subjects[2].name, "Cloud Computing")
        self.assertEqual(input_data.subjects[2].difficulty, "medium")


class TestPromptConstruction(unittest.TestCase):
    """
    Tests prompt building and system instruction completeness.
    """

    def test_system_instruction_contains_required_schemas(self):
        self.assertIn("plan_overview", STUDY_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("weekly_schedule", STUDY_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("monthly_milestones", STUDY_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("study_tips", STUDY_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("core_concept_study", STUDY_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("practice_problems", STUDY_PLAN_SYSTEM_INSTRUCTION)

    def test_build_study_plan_prompt(self):
        input_data = OnboardingDataInput.model_validate({
            "semester": 5,
            "study_hours_per_day": 4.0,
            "goals": ["GATE CS"],
            "subjects": ["Algorithms", "OS"],
        })
        prompt = build_study_plan_prompt(input_data)
        self.assertIn("Semester: 5", prompt)
        self.assertIn("4.0 hours/day", prompt)
        self.assertIn("Algorithms", prompt)
        self.assertIn("OS", prompt)


class TestStrictSchemaAdherence(unittest.TestCase):
    """
    Tests Pydantic validation of model output against StudyPlanOutputSchema.
    """

    def setUp(self):
        self.valid_plan = {
            "plan_overview": {
                "student_semester": 5,
                "daily_target_hours": 4.5,
                "weekly_total_hours": 31.5,
                "primary_focus": "Academic Excellence & GATE CS Prep",
                "strategy_summary": "High intensity focus on core CS topics with daily revision."
            },
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 4.5,
                    "sessions": [
                        {
                            "subject": "Operating Systems",
                            "topic": "Process Synchronization & Semaphores",
                            "duration_hours": 2.5,
                            "activity_type": "core_concept_study",
                            "priority": "high"
                        },
                        {
                            "subject": "Computer Networks",
                            "topic": "TCP/IP Handshake & Congestion Control",
                            "duration_hours": 2.0,
                            "activity_type": "practice_problems",
                            "priority": "medium"
                        }
                    ]
                },
                {
                    "day": "Tuesday",
                    "total_hours": 4.5,
                    "sessions": [
                        {
                            "subject": "Database Management Systems",
                            "topic": "B+ Trees & Indexing",
                            "duration_hours": 2.5,
                            "activity_type": "core_concept_study",
                            "priority": "high"
                        },
                        {
                            "subject": "Operating Systems",
                            "topic": "Deadlock Handling",
                            "duration_hours": 2.0,
                            "activity_type": "revision_quiz",
                            "priority": "medium"
                        }
                    ]
                }
            ],
            "monthly_milestones": [
                {
                    "week": 1,
                    "milestone": "Master OS Process Management & Synchronization",
                    "key_deliverable": "Solve 50 GATE PYQs on Semaphores"
                },
                {
                    "week": 2,
                    "milestone": "Complete Transport Layer Protocols",
                    "key_deliverable": "Network packet analysis lab exercise"
                }
            ],
            "study_tips": [
                "Use Pomodoro 50/10 split for core concept study sessions.",
                "Review active recall flashcards before bed."
            ]
        }

    def test_valid_plan_passes_validation(self):
        validated = validate_study_plan_output(self.valid_plan)
        self.assertIsInstance(validated, StudyPlanOutputSchema)
        self.assertEqual(validated.plan_overview.student_semester, 5)
        self.assertEqual(len(validated.weekly_schedule), 2)
        self.assertEqual(validated.weekly_schedule[0].day, "Monday")

    def test_invalid_day_enum_raises_error(self):
        invalid_plan = json.loads(json.dumps(self.valid_plan))
        invalid_plan["weekly_schedule"][0]["day"] = "Funday"
        with self.assertRaises(ValidationError):
            validate_study_plan_output(invalid_plan)

    def test_invalid_activity_type_raises_error(self):
        invalid_plan = json.loads(json.dumps(self.valid_plan))
        invalid_plan["weekly_schedule"][0]["sessions"][0]["activity_type"] = "binge_watching"
        with self.assertRaises(ValidationError):
            validate_study_plan_output(invalid_plan)

    def test_invalid_priority_raises_error(self):
        invalid_plan = json.loads(json.dumps(self.valid_plan))
        invalid_plan["weekly_schedule"][0]["sessions"][0]["priority"] = "urgent_af"
        with self.assertRaises(ValidationError):
            validate_study_plan_output(invalid_plan)

class TestTargetScoreMilestoneAlignment(unittest.TestCase):
    """
    Tests that dynamic exam revision milestones accurately reflect specific target scores requested by the student.
    """

    def setUp(self):
        self.onboarding = OnboardingDataInput.model_validate({
            "semester": 5,
            "study_hours_per_day": 4.5,
            "goals": ["Achieve 9.0+ CGPA", "GATE CS Prep"],
            "subjects": [
                {"name": "Operating Systems", "difficulty": "hard", "target_score": "A+"},
                {"name": "Computer Networks", "difficulty": "medium", "target_score": "90%"},
            ]
        })

        self.valid_plan = StudyPlanOutputSchema.model_validate({
            "plan_overview": {
                "student_semester": 5,
                "daily_target_hours": 4.5,
                "weekly_total_hours": 31.5,
                "primary_focus": "Academic Excellence & Target Score Achievement",
                "strategy_summary": "Focused concept study and target score revision quizzes."
            },
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 4.5,
                    "sessions": [
                        {
                            "subject": "Operating Systems",
                            "topic": "Semaphores",
                            "duration_hours": 2.5,
                            "activity_type": "core_concept_study",
                            "priority": "high"
                        }
                    ]
                }
            ],
            "monthly_milestones": [
                {
                    "week": 1,
                    "milestone": "Master OS Process Synchronization targeting A+ Grade",
                    "key_deliverable": "Score >= 90% in OS Process Sync Mock Assessment"
                },
                {
                    "week": 2,
                    "milestone": "Complete Computer Networks TCP/IP revision aiming for 90% score",
                    "key_deliverable": "Complete Networks simulation lab with A grade benchmark"
                }
            ],
            "study_tips": ["Review mock test errors daily."]
        })

    def test_target_scores_reflected_in_milestones(self):
        alignment = validate_target_score_alignment(self.valid_plan, self.onboarding)
        self.assertTrue(alignment["is_aligned"])
        self.assertEqual(len(alignment["missing_alignments"]), 0)
        self.assertIn("Operating Systems", alignment["alignment_details"])
        self.assertEqual(alignment["alignment_details"]["Operating Systems"]["requested_target_score"], "A+")

    def test_missing_target_score_alignment_detected(self):
        unaligned_plan = StudyPlanOutputSchema.model_validate({
            "plan_overview": {
                "student_semester": 5,
                "daily_target_hours": 4.5,
                "weekly_total_hours": 31.5,
                "primary_focus": "General Prep",
                "strategy_summary": "General overview without target score benchmarks."
            },
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 4.5,
                    "sessions": [
                        {
                            "subject": "Unrelated Topic",
                            "topic": "Intro",
                            "duration_hours": 4.5,
                            "activity_type": "core_concept_study",
                            "priority": "low"
                        }
                    ]
                }
            ],
            "monthly_milestones": [
                {
                    "week": 1,
                    "milestone": "Read general chapters",
                    "key_deliverable": "Skim textbook"
                }
            ],
            "study_tips": ["Keep reading"]
        })
class TestEdgeCaseSubjectFidelity(unittest.TestCase):
    """
    Tests edge-case subjects (specialized courses, course codes, special characters)
    to ensure subject fidelity and zero hallucination/mutation.
    """

    def setUp(self):
        self.edge_case_onboarding = OnboardingDataInput.model_validate({
            "semester": 6,
            "study_hours_per_day": 5.0,
            "goals": ["Master Specialized Engineering Domains"],
            "subjects": [
                {"name": "Quantum Computing & Superconducting Qubits", "difficulty": "hard", "target_score": "A+"},
                {"name": "Bioinformatics & Genomic Sequence Alignment (BI-402)", "difficulty": "medium", "target_score": "A"},
                {"name": "CS 490: Special Topics - Distributed Consensus", "difficulty": "hard", "target_score": "A+"},
                {"name": "C++ & Rust Systems Programming", "difficulty": "hard", "target_score": "A"}
            ]
        })

        self.faithful_plan = StudyPlanOutputSchema.model_validate({
            "plan_overview": {
                "student_semester": 6,
                "daily_target_hours": 5.0,
                "weekly_total_hours": 35.0,
                "primary_focus": "Specialized Quantum & Distributed Systems",
                "strategy_summary": "Rigorous domain-specific concept study."
            },
            "weekly_schedule": [
                {
                    "day": "Monday",
                    "total_hours": 5.0,
                    "sessions": [
                        {
                            "subject": "Quantum Computing & Superconducting Qubits",
                            "topic": "Superposition & Transmon Qubit Gates",
                            "duration_hours": 2.5,
                            "activity_type": "core_concept_study",
                            "priority": "high"
                        },
                        {
                            "subject": "Bioinformatics & Genomic Sequence Alignment (BI-402)",
                            "topic": "Needleman-Wunsch & Smith-Waterman Algorithms",
                            "duration_hours": 2.5,
                            "activity_type": "practice_problems",
                            "priority": "medium"
                        }
                    ]
                },
                {
                    "day": "Tuesday",
                    "total_hours": 5.0,
                    "sessions": [
                        {
                            "subject": "CS 490: Special Topics - Distributed Consensus",
                            "topic": "Raft Leader Election & Log Replication",
                            "duration_hours": 2.5,
                            "activity_type": "core_concept_study",
                            "priority": "high"
                        },
                        {
                            "subject": "C++ & Rust Systems Programming",
                            "topic": "Rust Ownership, Borrowing & C++ RAII",
                            "duration_hours": 2.5,
                            "activity_type": "practice_problems",
                            "priority": "high"
                        }
                    ]
                }
            ],
            "monthly_milestones": [
                {
                    "week": 1,
                    "milestone": "Implement Raft Consensus State Machine",
                    "key_deliverable": "Pass all Raft consensus unit tests"
                }
            ],
            "study_tips": ["Implement algorithms in code to verify understanding."]
        })

    def test_edge_case_subject_prompt_construction(self):
        prompt = build_study_plan_prompt(self.edge_case_onboarding)
        self.assertIn("Quantum Computing & Superconducting Qubits", prompt)
        self.assertIn("Bioinformatics & Genomic Sequence Alignment (BI-402)", prompt)
        self.assertIn("CS 490: Special Topics - Distributed Consensus", prompt)
        self.assertIn("C++ & Rust Systems Programming", prompt)

    def test_exact_subject_name_fidelity_passes(self):
        report = validate_subject_name_fidelity(self.faithful_plan, self.edge_case_onboarding)
        self.assertTrue(report["is_valid"])
        self.assertEqual(len(report["unmatched_sessions"]), 0)

    def test_mutated_subject_name_fails_fidelity(self):
        mutated_plan_dict = self.faithful_plan.model_dump()
        # Mutate subject name to generic "Quantum Computing"
        mutated_plan_dict["weekly_schedule"][0]["sessions"][0]["subject"] = "Quantum Computing"
        mutated_plan = StudyPlanOutputSchema.model_validate(mutated_plan_dict)

        report = validate_subject_name_fidelity(mutated_plan, self.edge_case_onboarding)
        self.assertFalse(report["is_valid"])
        self.assertEqual(len(report["unmatched_sessions"]), 1)
        self.assertEqual(report["unmatched_sessions"][0]["subject"], "Quantum Computing")


if __name__ == "__main__":
    unittest.main()


