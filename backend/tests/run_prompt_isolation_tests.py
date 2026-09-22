"""
Standalone System Prompt Schema Adherence Isolation Test Runner.
Executes schema validation tests against real onboarding JSON profiles and verifies
strict adherence to Pydantic models and structural rules.
"""
import os
import sys
import json
from typing import Dict, Any, List

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from prompts.study_plan import (
    OnboardingDataInput,
    STUDY_PLAN_SYSTEM_INSTRUCTION,
    build_study_plan_prompt,
    validate_study_plan_output,
    StudyPlanOutputSchema,
)

# Real Onboarding JSON Payloads collected from frontend onboarding forms
REAL_ONBOARDING_PAYLOADS = [
    {
        "name": "Scenario A - Semester 5 CS Student (GATE & High CGPA Goal)",
        "payload": {
            "semester": 5,
            "study_hours_per_day": 4.5,
            "goals": ["Achieve 9.0+ CGPA", "Prepare for GATE CS 2026", "Master Operating Systems"],
            "subjects": [
                {"name": "Operating Systems", "difficulty": "hard", "target_score": "A+"},
                {"name": "Computer Networks", "difficulty": "medium", "target_score": "A"},
                {"name": "Database Management Systems", "difficulty": "medium", "target_score": "A+"},
                {"name": "Theory of Computation", "difficulty": "hard", "target_score": "A"}
            ]
        }
    },
    {
        "name": "Scenario B - Semester 3 Student (Simple String Subjects & Single Goal)",
        "payload": {
            "semester": 3,
            "study_hours_per_day": 3.5,
            "goals": "Master Data Structures and Algorithms",
            "subjects": ["Data Structures", "Discrete Mathematics", "Digital Electronics"]
        }
    },
    {
        "name": "Scenario C - Semester 7 Placement Candidate (Heavy Load)",
        "payload": {
            "semester": 7,
            "study_hours_per_day": 6.0,
            "goals": ["Software Engineering Placement Prep", "System Design & Architecture"],
            "subjects": [
                {"name": "System Design", "difficulty": "hard"},
                {"name": "Machine Learning", "difficulty": "hard"},
                "Compiler Design",
                "Cloud Computing"
            ]
        }
    }
]


# Representative AI Response Payloads adhering strictly to schema
REPRESENTATIVE_AI_RESPONSES = [
    {
        "plan_overview": {
            "student_semester": 5,
            "daily_target_hours": 4.5,
            "weekly_total_hours": 31.5,
            "primary_focus": "Academic Excellence & GATE CS Prep",
            "strategy_summary": "Daily balanced allocation focusing on hard subjects early in the week with practice sessions."
        },
        "weekly_schedule": [
            {
                "day": "Monday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "subject": "Operating Systems",
                        "topic": "Process Scheduling Algorithms & CPU Dispatching",
                        "duration_hours": 2.5,
                        "activity_type": "core_concept_study",
                        "priority": "high"
                    },
                    {
                        "subject": "Computer Networks",
                        "topic": "OSI & TCP/IP Stack Layers",
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
                        "subject": "Theory of Computation",
                        "topic": "DFA & NFA Construction",
                        "duration_hours": 2.5,
                        "activity_type": "core_concept_study",
                        "priority": "high"
                    },
                    {
                        "subject": "Database Management Systems",
                        "topic": "ER Diagrams & Relational Algebra",
                        "duration_hours": 2.0,
                        "activity_type": "lecture_review",
                        "priority": "medium"
                    }
                ]
            },
            {
                "day": "Wednesday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "subject": "Operating Systems",
                        "topic": "Semaphores & Mutex Locks",
                        "duration_hours": 2.5,
                        "activity_type": "core_concept_study",
                        "priority": "high"
                    },
                    {
                        "subject": "Computer Networks",
                        "topic": "IP Addressing & Subnetting",
                        "duration_hours": 2.0,
                        "activity_type": "practice_problems",
                        "priority": "high"
                    }
                ]
            },
            {
                "day": "Thursday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "subject": "Theory of Computation",
                        "topic": "Pumping Lemma for Regular Languages",
                        "duration_hours": 2.5,
                        "activity_type": "practice_problems",
                        "priority": "high"
                    },
                    {
                        "subject": "Database Management Systems",
                        "topic": "Normalization (1NF to BCNF)",
                        "duration_hours": 2.0,
                        "activity_type": "core_concept_study",
                        "priority": "medium"
                    }
                ]
            },
            {
                "day": "Friday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "subject": "Operating Systems",
                        "topic": "Memory Management & Paging",
                        "duration_hours": 2.5,
                        "activity_type": "core_concept_study",
                        "priority": "high"
                    },
                    {
                        "subject": "Computer Networks",
                        "topic": "Routing Algorithms (Dijkstra & DVR)",
                        "duration_hours": 2.0,
                        "activity_type": "revision_quiz",
                        "priority": "medium"
                    }
                ]
            },
            {
                "day": "Saturday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "subject": "Database Management Systems",
                        "topic": "SQL Queries & Joins",
                        "duration_hours": 2.5,
                        "activity_type": "practice_problems",
                        "priority": "high"
                    },
                    {
                        "subject": "Theory of Computation",
                        "topic": "Context-Free Grammars",
                        "duration_hours": 2.0,
                        "activity_type": "revision_quiz",
                        "priority": "medium"
                    }
                ]
            },
            {
                "day": "Sunday",
                "total_hours": 4.5,
                "sessions": [
                    {
                        "subject": "Operating Systems",
                        "topic": "Weekly Revision & Mock Quiz",
                        "duration_hours": 2.5,
                        "activity_type": "revision_quiz",
                        "priority": "high"
                    },
                    {
                        "subject": "Computer Networks",
                        "topic": "GATE PYQ Solving Session",
                        "duration_hours": 2.0,
                        "activity_type": "practice_problems",
                        "priority": "high"
                    }
                ]
            }
        ],
        "monthly_milestones": [
            {
                "week": 1,
                "milestone": "Master OS Process Management & Synchronization",
                "key_deliverable": "Solve 50 GATE PYQs on Process Sync"
            },
            {
                "week": 2,
                "milestone": "Complete Transport & Network Layer Protocols",
                "key_deliverable": "Complete 3 Network Simulation Labs"
            },
            {
                "week": 3,
                "milestone": "Normalize Databases to 3NF/BCNF",
                "key_deliverable": "Design E-Commerce Database Schema"
            },
            {
                "week": 4,
                "milestone": "TOC Automata & Grammars Proficiency",
                "key_deliverable": "Score > 85% in Weekly Subject Mock Test"
            }
        ],
        "study_tips": [
            "Use Pomodoro technique (50 mins study / 10 mins break) to maintain focus.",
            "Write down key formulas and theorems in an active recall notebook."
        ]
    }
]


def run_isolation_suite():
    print("=======================================================================")
    print("STARTING SYSTEM PROMPT & SCHEMA ISOLATION TEST SUITE")
    print("=======================================================================")

    success_count = 0
    total_tests = 0

    # Task 1: Ingestion & Prompt Building Tests
    for test_case in REAL_ONBOARDING_PAYLOADS:
        total_tests += 1
        name = test_case["name"]
        payload = test_case["payload"]
        print(f"\n[TEST {total_tests}] Validating Onboarding Ingestion & Prompt Building: {name}")

        try:
            onboarding_input = OnboardingDataInput.model_validate(payload)
            print(f"  |-- Input Normalized: Semester={onboarding_input.semester}, Daily Hours={onboarding_input.study_hours_per_day}")
            print(f"  |-- Goals Normalized: {onboarding_input.goals}")
            print(f"  |-- Subjects Count: {len(onboarding_input.subjects)}")

            prompt = build_study_plan_prompt(onboarding_input)
            assert len(prompt) > 50, "Prompt length too short"
            assert f"Semester: {onboarding_input.semester}" in prompt, "Semester missing from prompt"
            print("  |-- Prompt Construction: SUCCESS")
            success_count += 1
        except Exception as e:
            print(f"  |-- FAILED: {e}")

    # Task 2: Schema Validation Tests against Pydantic Output Schema
    for idx, raw_response in enumerate(REPRESENTATIVE_AI_RESPONSES, 1):
        total_tests += 1
        print(f"\n[TEST {total_tests}] Validating AI Response Schema Adherence (Sample {idx})")

        try:
            validated = validate_study_plan_output(raw_response)
            assert isinstance(validated, StudyPlanOutputSchema)

            overview = validated.plan_overview
            print(f"  |-- Plan Overview: {overview.primary_focus} (Semester {overview.student_semester})")
            print(f"  |-- Total Weekly Schedule Days: {len(validated.weekly_schedule)}")

            # Verify total hours on each day matches or respects daily limit
            daily_limit = overview.daily_target_hours
            for day_item in validated.weekly_schedule:
                day_hours = sum(s.duration_hours for s in day_item.sessions)
                print(f"     * {day_item.day}: {len(day_item.sessions)} sessions, {day_hours}h / {daily_limit}h max")
                assert day_hours <= daily_limit + 0.01, f"Day {day_item.day} total hours ({day_hours}) exceeds target ({daily_limit})"

            print(f"  |-- Monthly Milestones Count: {len(validated.monthly_milestones)}")
            print(f"  |-- Study Tips Count: {len(validated.study_tips)}")
            print("  |-- Schema Adherence: STRICT COMPLIANCE CONFIRMED")
            success_count += 1
        except Exception as e:
            print(f"  |-- FAILED: {e}")

    print("\n=======================================================================")
    print(f"TEST RESULTS: {success_count}/{total_tests} ISOLATION TESTS PASSED")
    print("=======================================================================")
    return success_count == total_tests


if __name__ == "__main__":
    passed = run_isolation_suite()
    sys.exit(0 if passed else 1)
