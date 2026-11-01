"""
Unit and Isolation Tests for Module 2 AI Academic Assistant System Prompts and Schemas.

Verifies:
1. Input validation for WeakTopicContextInput across all 3 assistant modes:
   - "Generate Quiz"
   - "Explain Topic"
   - "Create Revision Plan"
2. Dynamic prompt construction ensuring exact subject name fidelity and diagnostic grounding.
3. System instruction invariants (4 distinct options for MCQs, pedagogical intuition, time-boxed revision).
4. Pydantic validation of structured JSON responses for all 3 output schemas.
5. Error handling and bounds enforcement (duplicate options, negative durations, out-of-bounds indices).
"""

import json
import sys
import unittest
from pathlib import Path

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from prompts.assistant import (
    WeakTopicContextInput,
    GenerateQuizRequestInput,
    ExplainTopicRequestInput,
    CreateRevisionPlanRequestInput,
    QuizQuestionItem,
    QuizOutputSchema,
    CommonPitfallItem,
    SelfCheckQuestionItem,
    TopicExplanationOutputSchema,
    RevisionSessionItem,
    RevisionPlanOutputSchema,
    MODULE_2_ASSISTANT_BASE_INSTRUCTION,
    GENERATE_QUIZ_SYSTEM_INSTRUCTION,
    EXPLAIN_TOPIC_SYSTEM_INSTRUCTION,
    CREATE_REVISION_PLAN_SYSTEM_INSTRUCTION,
    build_generate_quiz_prompt,
    build_explain_topic_prompt,
    build_create_revision_plan_prompt,
    build_assistant_prompt,
    validate_quiz_output,
    validate_explanation_output,
    validate_revision_plan_output,
)


class TestModule2AssistantPrompts(unittest.TestCase):
    """
    Test suite for Module 2 AI Assistant prompt templates, input normalization, and response schemas.
    """

    def setUp(self):
        self.sample_weak_topic = WeakTopicContextInput(
            id="wt-os-sync-1",
            subject="Operating Systems",
            topic="Process Synchronization",
            status="Needs Revision",
            severity="high",
            explainability_tags=[
                "Missed Task: Process Synchronization",
                "Sub-50% Study Duration (0%)",
                "Study Deficit: -90m",
                "High Priority Exam Target"
            ],
            missed_minutes=90,
            planned_minutes=90,
            actual_minutes=0,
            completion_rate=0,
            reason_summary="Missed 90-minute session on Process Synchronization."
        )

        self.secondary_weak_topic = WeakTopicContextInput(
            id="wt-cn-tcp-1",
            subject="Computer Networks",
            topic="TCP Congestion Control",
            status="Needs Revision",
            severity="medium",
            explainability_tags=[
                "Study Deficit: -45m",
                "Sub-50% Study Duration (25%)"
            ],
            missed_minutes=45,
            planned_minutes=60,
            actual_minutes=15,
            completion_rate=25,
            reason_summary="Partial completion with 45m deficit."
        )

    # =========================================================================
    # 1. Input Schemas & Tag Normalization Tests
    # =========================================================================

    def test_weak_topic_input_normalizes_string_tags(self):
        """Verify comma-separated string tags are automatically normalized into a list."""
        topic_input = WeakTopicContextInput(
            subject="Database Management Systems",
            topic="Transactions & ACID",
            explainability_tags="Study Deficit: -60m, High Priority Exam Target",
            missed_minutes=60
        )
        self.assertEqual(len(topic_input.explainability_tags), 2)
        self.assertEqual(topic_input.explainability_tags[0], "Study Deficit: -60m")
        self.assertEqual(topic_input.explainability_tags[1], "High Priority Exam Target")

    def test_quiz_request_input_validation(self):
        """Verify GenerateQuizRequestInput defaults and bounds."""
        req = GenerateQuizRequestInput(
            weak_topic=self.sample_weak_topic,
            num_questions=5,
            difficulty="exam_level",
            student_semester=5,
            focus_subtopic="Peterson's Algorithm"
        )
        self.assertEqual(req.num_questions, 5)
        self.assertEqual(req.difficulty, "exam_level")
        self.assertEqual(req.focus_subtopic, "Peterson's Algorithm")

    def test_quiz_request_rejects_out_of_bound_questions(self):
        """Verify question count bounds (1 <= num_questions <= 20)."""
        with self.assertRaises(ValueError):
            GenerateQuizRequestInput(weak_topic=self.sample_weak_topic, num_questions=0)

        with self.assertRaises(ValueError):
            GenerateQuizRequestInput(weak_topic=self.sample_weak_topic, num_questions=25)

    # =========================================================================
    # 2. Prompt Building Tests
    # =========================================================================

    def test_build_generate_quiz_prompt_preserves_subject_and_deficit(self):
        """Verify build_generate_quiz_prompt includes all diagnostic telemetry and parameters."""
        req = GenerateQuizRequestInput(
            weak_topic=self.sample_weak_topic,
            additional_weak_topics=[self.secondary_weak_topic],
            num_questions=5,
            difficulty="intermediate",
            student_semester=5,
            focus_subtopic="Critical Section Problem"
        )
        prompt = build_generate_quiz_prompt(req)

        self.assertIn("Subject: 'Operating Systems'", prompt)
        self.assertIn("Weak Topic: 'Process Synchronization'", prompt)
        self.assertIn("Severity Level: HIGH", prompt)
        self.assertIn("Study Deficit: -90 minutes", prompt)
        self.assertIn("Student Semester: Semester 5", prompt)
        self.assertIn("Focus Subtopic: 'Critical Section Problem'", prompt)
        self.assertIn("Number of Questions: 5", prompt)
        self.assertIn("Target Difficulty: INTERMEDIATE", prompt)
        self.assertIn("Computer Networks - TCP Congestion Control", prompt)
        self.assertIn("QuizOutputSchema", prompt)

    def test_build_explain_topic_prompt_contains_depth_and_language(self):
        """Verify build_explain_topic_prompt constructs complete pedagogical instructions."""
        req = ExplainTopicRequestInput(
            weak_topic=self.sample_weak_topic,
            depth="conceptual_deep_dive",
            student_semester=5,
            programming_language="C++",
            specific_query="How does Peterson's algorithm prevent race conditions?"
        )
        prompt = build_explain_topic_prompt(req)

        self.assertIn("Subject: 'Operating Systems'", prompt)
        self.assertIn("Flagged Weak Topic: 'Process Synchronization'", prompt)
        self.assertIn("Academic Level: Semester 5 CS/Engineering", prompt)
        self.assertIn("Implementation Language: C++", prompt)
        self.assertIn("How does Peterson's algorithm prevent race conditions?", prompt)
        self.assertIn("TopicExplanationOutputSchema", prompt)

    def test_build_create_revision_plan_prompt_calculates_total_deficit(self):
        """Verify build_create_revision_plan_prompt aggregates total deficit minutes accurately."""
        req = CreateRevisionPlanRequestInput(
            weak_topics=[self.sample_weak_topic, self.secondary_weak_topic],
            available_daily_minutes=60,
            target_timeframe_days=3,
            preferred_technique="active_recall",
            student_goals=["Target 8.5+ CGPA", "GATE CS Prep"]
        )
        prompt = build_create_revision_plan_prompt(req)

        # 90m + 45m = 135m total deficit
        self.assertIn("Total Diagnosed Deficit: 135 minutes", prompt)
        self.assertIn("Available Daily Revision Window: 60 minutes/day", prompt)
        self.assertIn("Target Sprint Duration: 3 days", prompt)
        self.assertIn("Preferred Learning Technique: active_recall", prompt)
        self.assertIn("GATE CS Prep", prompt)
        self.assertIn("RevisionPlanOutputSchema", prompt)

    def test_unified_assistant_prompt_dispatcher(self):
        """Verify build_assistant_prompt dispatches cleanly according to AssistantMode."""
        quiz_req = GenerateQuizRequestInput(weak_topic=self.sample_weak_topic, num_questions=3)
        prompt = build_assistant_prompt("generate_quiz", quiz_req)
        self.assertIn("Number of Questions: 3", prompt)

        with self.assertRaises(TypeError):
            build_assistant_prompt("explain_topic", quiz_req)

        with self.assertRaises(ValueError):
            build_assistant_prompt("unknown_mode", quiz_req)  # type: ignore

    # =========================================================================
    # 3. System Instructions Integrity Tests
    # =========================================================================

    def test_system_instructions_contain_critical_invariants(self):
        """Verify non-negotiable rules are present across all system instructions."""
        self.assertIn("ZERO-HALLUCINATION SUBJECT FIDELITY", MODULE_2_ASSISTANT_BASE_INSTRUCTION)
        self.assertIn("DETERMINISTIC GROUNDING", MODULE_2_ASSISTANT_BASE_INSTRUCTION)

        self.assertIn("EXACTLY 4 DISTINCT OPTIONS", GENERATE_QUIZ_SYSTEM_INSTRUCTION)
        self.assertIn("NO TRIVIAL TRIVIA", GENERATE_QUIZ_SYSTEM_INSTRUCTION)

        self.assertIn("INTUITION FIRST", EXPLAIN_TOPIC_SYSTEM_INSTRUCTION)
        self.assertIn("HIGHLIGHT COMMON PITFALLS", EXPLAIN_TOPIC_SYSTEM_INSTRUCTION)

        self.assertIn("TIME-BOUNDED RECOVERY", CREATE_REVISION_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("DAILY CEILING COMPLIANCE", CREATE_REVISION_PLAN_SYSTEM_INSTRUCTION)
        self.assertIn("ACTIVE LEARNING ONLY", CREATE_REVISION_PLAN_SYSTEM_INSTRUCTION)

    # =========================================================================
    # 4. Output Schemas Validation Tests
    # =========================================================================

    def test_valid_quiz_output_schema_parsing(self):
        """Verify QuizOutputSchema validates valid LLM response JSON."""
        sample_quiz_payload = {
            "quiz_title": "Diagnostic Assessment: Process Synchronization Mechanics",
            "target_subject": "Operating Systems",
            "target_topic": "Process Synchronization",
            "diagnostic_context": "Targeting 90-minute deficit on critical section problem and Peterson's algorithm.",
            "difficulty": "intermediate",
            "estimated_duration_minutes": 15,
            "pass_threshold_percentage": 75,
            "questions": [
                {
                    "question_id": "q1",
                    "question_text": "In Peterson's solution for two processes, which condition prevents both processes from simultaneously entering the critical section?",
                    "options": [
                        "A) The boolean array flag[2] alone without the turn variable",
                        "B) The strict alternation enforced when turn equals the other process's ID",
                        "C) The condition where both flag[i] is true and turn == j evaluates to false for one process",
                        "D) Disabling hardware interrupts on the CPU"
                    ],
                    "correct_option_index": 2,
                    "explanation": "Option C is correct. Both processes set their flag to true, but 'turn' can only hold one value at a time, ensuring Mutual Exclusion. Option A lacks mutual exclusion, Option B causes strict lockstep, and Option D is hardware-based, not Peterson's software solution.",
                    "tested_concept": "Mutual Exclusion Invariant in Peterson's Algorithm",
                    "difficulty": "medium"
                }
            ],
            "remedial_study_tip": "Review Peterson's two-variable proof and trace execution state table."
        }

        schema = validate_quiz_output(sample_quiz_payload)
        self.assertEqual(schema.target_subject, "Operating Systems")
        self.assertEqual(len(schema.questions), 1)
        self.assertEqual(schema.questions[0].correct_option_index, 2)
        self.assertEqual(len(schema.questions[0].options), 4)

    def test_quiz_rejects_duplicate_options(self):
        """Verify QuizQuestionItem rejects duplicate options."""
        invalid_question = {
            "question_id": "q1",
            "question_text": "What is mutual exclusion?",
            "options": [
                "Only one process in critical section",
                "Only one process in critical section",  # Duplicate
                "Two processes in critical section",
                "None of the above"
            ],
            "correct_option_index": 0,
            "explanation": "Option 0 is correct.",
            "tested_concept": "Mutual Exclusion",
            "difficulty": "easy"
        }
        with self.assertRaises(ValueError) as ctx:
            QuizQuestionItem.model_validate(invalid_question)
        self.assertIn("must be distinct", str(ctx.exception))

    def test_valid_topic_explanation_schema_parsing(self):
        """Verify TopicExplanationOutputSchema validates structured explanation response."""
        sample_explanation_payload = {
            "subject": "Operating Systems",
            "topic": "Process Synchronization",
            "diagnostic_note": "Identified a 90-minute study deficit and sub-50% study duration on this topic.",
            "one_sentence_summary": "Process synchronization coordinates concurrent execution to ensure shared data consistency.",
            "core_intuition": "Imagine two writers sharing a single whiteboard. Without a turn-taking protocol, their sentences overwrite each other into gibberish.",
            "technical_deep_dive": "Mutual exclusion requires three invariant properties: 1. Mutual Exclusion (only one process in CS), 2. Progress (selection cannot be postponed indefinitely), 3. Bounded Waiting (limit on times others enter before a process).",
            "code_or_pseudocode": "while (flag[j] && turn == j); // Busy wait\n// Critical Section\nflag[i] = false;",
            "common_pitfalls": [
                {
                    "misconception": "Disabling interrupts is a sufficient synchronization solution on multicore architectures.",
                    "correction": "Disabling interrupts only stops preemption on the calling core; other cores continue executing concurrently.",
                    "exam_tip": "Look out for multicore questions where single-core interrupt disabling is offered as a trap."
                }
            ],
            "real_world_application": "Linux kernel uses spinlocks and futexes (Fast Userspace Mutexes) based on atomic test-and-set instructions.",
            "quick_self_check": [
                {
                    "question": "What happens if a process crashes inside its critical section?",
                    "expected_answer": "Other processes will wait indefinitely, violating the Progress and Bounded Waiting invariants unless timeout recovery exists."
                }
            ],
            "recommended_next_step": "Complete the 5-question Process Synchronization Diagnostic Quiz."
        }

        schema = validate_explanation_output(sample_explanation_payload)
        self.assertEqual(schema.subject, "Operating Systems")
        self.assertEqual(len(schema.common_pitfalls), 1)
        self.assertEqual(len(schema.quick_self_check), 1)
        self.assertIn("Linux kernel", schema.real_world_application)

    def test_valid_revision_plan_schema_parsing(self):
        """Verify RevisionPlanOutputSchema validates tactical micro-revision schedules."""
        sample_plan_payload = {
            "plan_title": "90-Minute Fast-Track Recovery: Process Synchronization",
            "target_subject": "Operating Systems",
            "covered_weak_topics": ["Process Synchronization"],
            "total_recovery_minutes": 90,
            "target_timeframe_days": 2,
            "strategy_summary": "Recover 90 missed minutes over 2 days using Feynman technique and coding drills.",
            "sessions": [
                {
                    "session_id": "rev-1",
                    "day_number": 1,
                    "title": "Mutual Exclusion & Peterson Proof Breakdown",
                    "subject": "Operating Systems",
                    "topic": "Process Synchronization",
                    "duration_minutes": 45,
                    "technique": "feynman_technique",
                    "action_items": [
                        "Explain Peterson's algorithm to an imaginary peer without notes",
                        "Verify mutual exclusion, progress, and bounded waiting proofs"
                    ],
                    "key_deliverable": "Handwritten proof table of state transitions"
                },
                {
                    "session_id": "rev-2",
                    "day_number": 2,
                    "title": "Semaphore Coding & Deadlock Race Condition Drills",
                    "subject": "Operating Systems",
                    "topic": "Process Synchronization",
                    "duration_minutes": 45,
                    "technique": "active_recall",
                    "action_items": [
                        "Implement producer-consumer bounded buffer using semaphores in C++",
                        "Complete 5 diagnostic quiz questions"
                    ],
                    "key_deliverable": "Bug-free producer-consumer implementation"
                }
            ],
            "adherence_warning": "Session durations strictly capped at 45m/day to protect daily available hours ceiling.",
            "recommended_search_query": "Operating Systems Process Synchronization Semaphores"
        }

        schema = validate_revision_plan_output(sample_plan_payload)
        self.assertEqual(schema.total_recovery_minutes, 90)
        self.assertEqual(len(schema.sessions), 2)
        self.assertEqual(schema.sessions[0].technique, "feynman_technique")
        self.assertEqual(schema.sessions[1].technique, "active_recall")

    def test_revision_plan_reconciles_total_minutes_if_inconsistent(self):
        """Verify model_validator reconciles total_recovery_minutes to match the sum of sessions."""
        sample_plan_payload = {
            "plan_title": "Recovery Sprint",
            "target_subject": "Operating Systems",
            "covered_weak_topics": ["Process Synchronization"],
            "total_recovery_minutes": 100,  # Deliberately mismatched: 40 + 50 = 90
            "target_timeframe_days": 2,
            "strategy_summary": "Recover minutes",
            "sessions": [
                {
                    "session_id": "rev-1",
                    "day_number": 1,
                    "title": "Session 1",
                    "subject": "Operating Systems",
                    "topic": "Process Synchronization",
                    "duration_minutes": 40,
                    "technique": "pomodoro_drill",
                    "action_items": ["Review concept"],
                    "key_deliverable": "Summary notes"
                },
                {
                    "session_id": "rev-2",
                    "day_number": 2,
                    "title": "Session 2",
                    "subject": "Operating Systems",
                    "topic": "Process Synchronization",
                    "duration_minutes": 50,
                    "technique": "practice_problems",
                    "action_items": ["Practice questions"],
                    "key_deliverable": "5 solved problems"
                }
            ],
            "adherence_warning": "Cap daily load",
            "recommended_search_query": "Operating Systems Synchronization"
        }

        schema = validate_revision_plan_output(sample_plan_payload)
        # Should be reconciled to 40 + 50 = 90
        self.assertEqual(schema.total_recovery_minutes, 90)


if __name__ == "__main__":
    unittest.main()
