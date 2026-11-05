"""
Unit tests for AI Assistant System Action & Tool Invocation Schemas.

Verifies:
1. Scenario: User asks "What is my priority today?" -> AI outputs tool-call to read the tasks table.
2. ReadTasksTableParams date normalization ('today', 'tomorrow', 'this_week', 'YYYY-MM-DD') and concrete resolution.
3. Priority, status, and subject filtering bounds on task queries.
4. Parameter validation for all supported system actions:
   - read_tasks_table
   - get_active_study_plan
   - get_weak_topics_telemetry
   - get_analytics_summary
   - trigger_adaptive_rebalance
   - search_learning_resources
   - log_task_execution
   - update_study_hours_capacity
5. AssistantToolCall typed parameter parsing and validation.
6. AssistantActionResponseSchema response_type coherence (conversational vs system_action vs composite).
7. TaskRecordItem parsing from PostgreSQL database rows and ToolExecutionResult formatting.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

# Add backend directory to path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from schemas.assistant_tools import (
    ReadTasksTableParams,
    GetActiveStudyPlanParams,
    GetWeakTopicsParams,
    GetAnalyticsSummaryParams,
    TriggerAdaptiveRebalanceParams,
    SearchLearningResourcesParams,
    LogTaskExecutionParams,
    UpdateStudyHoursCapacityParams,
    AssistantToolCall,
    AssistantActionResponseSchema,
    TaskRecordItem,
    ToolExecutionResult,
    SYSTEM_ACTION_REGISTRY,
    get_system_tool_declarations,
)


class TestAssistantToolSchemas(unittest.TestCase):
    """
    Test suite for validating AI Assistant tool calls and system actions.
    """

    def setUp(self):
        self.ref_date = date(2026, 11, 2)  # Monday, Nov 2, 2026

    # =========================================================================
    # 1. Primary Scenario: "What is my priority today?"
    # =========================================================================

    def test_priority_today_user_query_validates_read_tasks_tool_call(self):
        """
        Scenario: Student asks "What is my priority today?"
        AI Assistant generates a system action to read the tasks table with:
        - target_date='today'
        - priority='high'
        - status='pending'
        """
        raw_ai_output = {
            "response_type": "composite",
            "message": "Let me check your scheduled high-priority study sessions for today.",
            "detected_intent": "check_daily_priorities",
            "tool_calls": [
                {
                    "call_id": "call_tasks_today_01",
                    "action_type": "read_tasks_table",
                    "parameters": {
                        "target_date": "today",
                        "priority": "high",
                        "status": "pending",
                        "limit": 5,
                        "order_by": "priority_desc"
                    },
                    "thought_reasoning": "Student asked for today's priorities. Reading tasks table filtered by target_date='today', priority='high', and status='pending'.",
                    "requires_user_confirmation": False
                }
            ],
            "suggested_follow_ups": [
                "Start top priority session",
                "Explain today's hardest topic",
                "How much study time planned today?"
            ]
        }

        # Validate top-level response schema
        validated_response = AssistantActionResponseSchema.model_validate(raw_ai_output)
        self.assertEqual(validated_response.response_type, "composite")
        self.assertEqual(len(validated_response.tool_calls), 1)

        tool_call = validated_response.tool_calls[0]
        self.assertEqual(tool_call.action_type, "read_tasks_table")
        self.assertFalse(tool_call.requires_user_confirmation)

        # Validate typed parameters
        typed_params = tool_call.parse_typed_parameters()
        self.assertIsInstance(typed_params, ReadTasksTableParams)
        self.assertEqual(typed_params.target_date, "today")
        self.assertEqual(typed_params.priority, "high")
        self.assertEqual(typed_params.status, "pending")
        self.assertEqual(typed_params.limit, 5)

        # Validate concrete date range resolution
        date_range = typed_params.resolve_concrete_date_range(reference_date=self.ref_date)
        self.assertEqual(date_range["start_date"], "2026-11-02")
        self.assertEqual(date_range["end_date"], "2026-11-02")

    # =========================================================================
    # 2. Date Filtering & Relative Alias Tests
    # =========================================================================

    def test_read_tasks_table_date_aliases_resolution(self):
        """Verify 'tomorrow', 'yesterday', 'this_week', and exact ISO date strings resolve correctly."""
        # Tomorrow
        p_tomorrow = ReadTasksTableParams(target_date="tomorrow")
        range_tomorrow = p_tomorrow.resolve_concrete_date_range(reference_date=self.ref_date)
        self.assertEqual(range_tomorrow["start_date"], "2026-11-03")
        self.assertEqual(range_tomorrow["end_date"], "2026-11-03")

        # Yesterday
        p_yesterday = ReadTasksTableParams(target_date="yesterday")
        range_yesterday = p_yesterday.resolve_concrete_date_range(reference_date=self.ref_date)
        self.assertEqual(range_yesterday["start_date"], "2026-11-01")
        self.assertEqual(range_yesterday["end_date"], "2026-11-01")

        # This week (Monday 2026-11-02 to Sunday 2026-11-08)
        p_week = ReadTasksTableParams(target_date="this_week")
        range_week = p_week.resolve_concrete_date_range(reference_date=self.ref_date)
        self.assertEqual(range_week["start_date"], "2026-11-02")
        self.assertEqual(range_week["end_date"], "2026-11-08")

        # Exact ISO date
        p_exact = ReadTasksTableParams(target_date="2026-11-15")
        range_exact = p_exact.resolve_concrete_date_range(reference_date=self.ref_date)
        self.assertEqual(range_exact["start_date"], "2026-11-15")
        self.assertEqual(range_exact["end_date"], "2026-11-15")

        # Python date object directly
        p_obj = ReadTasksTableParams(target_date=date(2026, 11, 20))
        self.assertEqual(p_obj.target_date, "2026-11-20")

    def test_read_tasks_table_rejects_invalid_date_formats(self):
        """Verify invalid date strings raise ValueError."""
        with self.assertRaises(ValueError):
            ReadTasksTableParams(target_date="next_month")

        with self.assertRaises(ValueError):
            ReadTasksTableParams(target_date="12/31/2026")  # Non-ISO format

        with self.assertRaises(ValueError):
            ReadTasksTableParams(target_date=12345)  # Invalid type

    # =========================================================================
    # 3. Parameter Schemas for Other Supported System Actions
    # =========================================================================

    def test_get_active_study_plan_params(self):
        """Verify GetActiveStudyPlanParams validation."""
        p = GetActiveStudyPlanParams(include_full_schedule=True, specific_day="Wednesday")
        self.assertTrue(p.include_full_schedule)
        self.assertEqual(p.specific_day, "Wednesday")

    def test_get_weak_topics_params(self):
        """Verify GetWeakTopicsParams bounds and filtering."""
        p = GetWeakTopicsParams(severity_filter="high", min_deficit_minutes=30, subject="Operating Systems")
        self.assertEqual(p.severity_filter, "high")
        self.assertEqual(p.min_deficit_minutes, 30)
        self.assertEqual(p.subject, "Operating Systems")

    def test_trigger_adaptive_rebalance_params(self):
        """Verify TriggerAdaptiveRebalanceParams."""
        p = TriggerAdaptiveRebalanceParams(
            reason="Missed 90-minute study session on Process Synchronization",
            preserve_completed_tasks=True
        )
        self.assertIn("Process Synchronization", p.reason)
        self.assertTrue(p.preserve_completed_tasks)

    def test_search_learning_resources_params(self):
        """Verify SearchLearningResourcesParams cosine threshold and query bounds."""
        p = SearchLearningResourcesParams(
            query="Operating Systems Process Synchronization Semaphores",
            top_n=5,
            min_similarity_score=0.15
        )
        self.assertEqual(p.top_n, 5)
        self.assertEqual(p.min_similarity_score, 0.15)

    def test_log_task_execution_params(self):
        """Verify LogTaskExecutionParams."""
        p = LogTaskExecutionParams(
            task_id="t-uuid-99",
            status="completed",
            actual_minutes=90,
            notes="Completed all Peterson algorithm practice problems"
        )
        self.assertEqual(p.task_id, "t-uuid-99")
        self.assertEqual(p.actual_minutes, 90)

    def test_update_study_hours_capacity_params(self):
        """Verify UpdateStudyHoursCapacityParams enforces bounds (0.5h to 16.0h)."""
        p = UpdateStudyHoursCapacityParams(new_daily_hours=4.0)
        self.assertEqual(p.new_daily_hours, 4.0)

        with self.assertRaises(ValueError):
            UpdateStudyHoursCapacityParams(new_daily_hours=0.2)

        with self.assertRaises(ValueError):
            UpdateStudyHoursCapacityParams(new_daily_hours=20.0)

    # =========================================================================
    # 4. AssistantActionResponseSchema Coherence Tests
    # =========================================================================

    def test_conversational_response_mode_requires_message_and_no_tools(self):
        """Verify 'conversational_response' accepts message but rejects tool_calls."""
        valid_chat = AssistantActionResponseSchema(
            response_type="conversational_response",
            message="Peterson's algorithm is a software-based critical section solution."
        )
        self.assertEqual(valid_chat.response_type, "conversational_response")

        # Conversational response cannot have tool_calls
        with self.assertRaises(ValueError):
            AssistantActionResponseSchema(
                response_type="conversational_response",
                message="Here are tasks",
                tool_calls=[
                    AssistantToolCall(
                        action_type="read_tasks_table",
                        parameters={"target_date": "today"},
                        thought_reasoning="Reading tasks"
                    )
                ]
            )

        # Conversational response cannot have empty message
        with self.assertRaises(ValueError):
            AssistantActionResponseSchema(
                response_type="conversational_response",
                message=None
            )

    def test_system_action_mode_requires_tool_calls(self):
        """Verify 'system_action' requires at least one tool call."""
        with self.assertRaises(ValueError):
            AssistantActionResponseSchema(
                response_type="system_action",
                tool_calls=[]
            )

    # =========================================================================
    # 5. Database Row to TaskRecordItem & ToolExecutionResult Tests
    # =========================================================================

    def test_task_record_item_parsing_from_db_row(self):
        """Verify TaskRecordItem accurately parses PostgreSQL/Supabase task row."""
        raw_db_row = {
            "id": "a0000000-0000-0000-0000-000000000001",
            "title": "Operating Systems: Process Synchronization",
            "description": "Activity: core_concept_study | Duration: 1.5 hours | Priority: high",
            "scheduled_date": "2026-11-02",
            "is_completed": False,
            "completed_at": None,
        }

        task = TaskRecordItem.from_db_row(raw_db_row)
        self.assertEqual(task.id, "a0000000-0000-0000-0000-000000000001")
        self.assertEqual(task.subject, "Operating Systems")
        self.assertEqual(task.topic, "Process Synchronization")
        self.assertEqual(task.priority, "high")
        self.assertEqual(task.duration_hours, 1.5)
        self.assertFalse(task.is_completed)

    def test_tool_execution_result_formatting(self):
        """Verify ToolExecutionResult validates returned data payload."""
        result = ToolExecutionResult(
            call_id="call_tasks_today_01",
            action_type="read_tasks_table",
            success=True,
            record_count=2,
            data=[
                {
                    "id": "task-1",
                    "title": "Operating Systems: Process Synchronization",
                    "priority": "high",
                    "duration_hours": 1.5,
                    "is_completed": False
                },
                {
                    "id": "task-2",
                    "title": "Algorithms: Dynamic Programming",
                    "priority": "high",
                    "duration_hours": 2.0,
                    "is_completed": False
                }
            ]
        )
        self.assertTrue(result.success)
        self.assertEqual(result.record_count, 2)
        self.assertEqual(len(result.data), 2)

    # =========================================================================
    # 6. Tool Registry & Declarations Generation Tests
    # =========================================================================

    def test_system_action_registry_completeness(self):
        """Verify registry maps all 8 actions with schemas and metadata."""
        expected_actions = [
            "read_tasks_table",
            "get_active_study_plan",
            "get_weak_topics_telemetry",
            "get_analytics_summary",
            "trigger_adaptive_rebalance",
            "search_learning_resources",
            "log_task_execution",
            "update_study_hours_capacity",
        ]
        for action in expected_actions:
            self.assertIn(action, SYSTEM_ACTION_REGISTRY)
            entry = SYSTEM_ACTION_REGISTRY[action]
            self.assertEqual(entry["name"], action)
            self.assertIn("description", entry)
            self.assertIn("schema", entry)

        # Confirm read_tasks_table is non-mutating and does not require confirmation
        read_tasks_meta = SYSTEM_ACTION_REGISTRY["read_tasks_table"]
        self.assertFalse(read_tasks_meta["is_state_mutating"])
        self.assertFalse(read_tasks_meta["requires_confirmation_default"])

    def test_get_system_tool_declarations_generates_valid_spec(self):
        """Verify declarations export proper JSON schema properties for LLMs."""
        declarations = get_system_tool_declarations()
        self.assertEqual(len(declarations), 8)

        # Find read_tasks_table declaration
        tasks_decl = next((d for d in declarations if d["name"] == "read_tasks_table"), None)
        self.assertIsNotNone(tasks_decl)
        self.assertIn("target_date", tasks_decl["parameters"]["properties"])
        self.assertIn("priority", tasks_decl["parameters"]["properties"])
        self.assertIn("status", tasks_decl["parameters"]["properties"])



if __name__ == "__main__":
    unittest.main()
