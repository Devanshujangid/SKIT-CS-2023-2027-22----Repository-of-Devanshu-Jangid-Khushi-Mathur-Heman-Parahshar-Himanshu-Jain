"""
Backend Services Package.
"""

from services.assistant_guardrail import (
    GuardrailCheckResult,
    check_academic_scope,
    NON_ACADEMIC_DOMAIN_PATTERNS,
    ACADEMIC_EXEMPTION_PATTERNS,
    ACADEMIC_INTENT_PATTERNS,
)
from services.notification_engine import (
    NotificationEngine,
    notification_engine,
)

__all__ = [
    "GuardrailCheckResult",
    "check_academic_scope",
    "NON_ACADEMIC_DOMAIN_PATTERNS",
    "ACADEMIC_EXEMPTION_PATTERNS",
    "ACADEMIC_INTENT_PATTERNS",
    "NotificationEngine",
    "notification_engine",
]
