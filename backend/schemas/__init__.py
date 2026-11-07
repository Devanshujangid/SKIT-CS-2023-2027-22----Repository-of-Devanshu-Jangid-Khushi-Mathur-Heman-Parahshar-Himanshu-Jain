"""
Pydantic Schemas Package for Smart Learning Planner API.
"""

from schemas.settings import (
    StudyHoursUpdateSchema,
    AcademicGoalsUpdateSchema,
    PasswordUpdateSchema,
    NotificationSettingsSchema,
    SettingsUpdateRequest,
    SettingsResponseSchema,
)

from schemas.notifications import (
    NotificationCreateRequest,
    NotificationResponse,
    NotificationListResponse,
    NotificationStatusUpdateResponse,
    NotificationBulkReadResponse,
)

from schemas.assistant_tools import (
    SystemActionType,
    PriorityFilter,
    TaskStatusFilter,
    DateAlias,
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

__all__ = [
    # Settings Schemas
    "StudyHoursUpdateSchema",
    "AcademicGoalsUpdateSchema",
    "PasswordUpdateSchema",
    "NotificationSettingsSchema",
    "SettingsUpdateRequest",
    "SettingsResponseSchema",
    # Notification Schemas
    "NotificationCreateRequest",
    "NotificationResponse",
    "NotificationListResponse",
    "NotificationStatusUpdateResponse",
    "NotificationBulkReadResponse",
    # Assistant Tool & System Action Schemas
    "SystemActionType",
    "PriorityFilter",
    "TaskStatusFilter",
    "DateAlias",
    "ReadTasksTableParams",
    "GetActiveStudyPlanParams",
    "GetWeakTopicsParams",
    "GetAnalyticsSummaryParams",
    "TriggerAdaptiveRebalanceParams",
    "SearchLearningResourcesParams",
    "LogTaskExecutionParams",
    "UpdateStudyHoursCapacityParams",
    "AssistantToolCall",
    "AssistantActionResponseSchema",
    "TaskRecordItem",
    "ToolExecutionResult",
    "SYSTEM_ACTION_REGISTRY",
    "get_system_tool_declarations",
]
