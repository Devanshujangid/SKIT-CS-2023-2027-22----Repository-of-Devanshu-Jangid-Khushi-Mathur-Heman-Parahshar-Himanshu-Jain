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
    AdminBroadcastNotificationRequest,
    AdminBroadcastNotificationResponse,
)

from schemas.leaderboard import (
    LeaderboardEntry,
    LeaderboardResponse,
    UpdateGoalStatusRequest,
    UpdateGoalStatusResponse,
)

from schemas.resources import (
    ResourceCreateRequest,
    ResourceUpdateRequest,
    ResourceResponse,
    ResourceListResponse,
)

from schemas.admin import (
    StudentStatusUpdateRequest,
    StudentAccountItem,
    StudentListResponse,
    SubjectCreateRequest,
    SubjectUpdateRequest,
    SubjectResponse,
    SubjectListResponse,
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

from schemas.admin_and_leaderboard import (
    ResourceType,
    DifficultyLevel,
    UserRole,
    DiagnosticStatus,
    LeaderboardTimeframe,
    LeaderboardMetric,
    BadgeTier,
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
    "AdminBroadcastNotificationRequest",
    "AdminBroadcastNotificationResponse",
    # Leaderboard Schemas
    "LeaderboardEntry",
    "LeaderboardResponse",
    "UpdateGoalStatusRequest",
    "UpdateGoalStatusResponse",
    # Resource Schemas
    "ResourceCreateRequest",
    "ResourceUpdateRequest",
    "ResourceResponse",
    "ResourceListResponse",
    # Admin Student & Subject Schemas
    "StudentStatusUpdateRequest",
    "StudentAccountItem",
    "StudentListResponse",
    "SubjectCreateRequest",
    "SubjectUpdateRequest",
    "SubjectResponse",
    "SubjectListResponse",
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
    # Admin CRUD & Leaderboard Schemas
    "ResourceType",
    "DifficultyLevel",
    "UserRole",
    "DiagnosticStatus",
    "LeaderboardTimeframe",
    "LeaderboardMetric",
    "BadgeTier",
    "AdminCreateResource",
    "AdminUpdateResource",
    "AdminResourceResponse",
    "AdminResourceListResponse",
    "AdminResourceDeleteResponse",
    "AdminCreateStudent",
    "AdminUpdateStudent",
    "AdminStudentRecord",
    "AdminStudentMutationResponse",
    "AdminStudentListResponse",
    "AdminDeleteStudentResponse",
    "LeaderboardBadge",
    "LeaderboardEntry",
    "LeaderboardUserStanding",
    "LeaderboardResponse",
]
