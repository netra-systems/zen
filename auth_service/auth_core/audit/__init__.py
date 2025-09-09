"""
Audit Package - Auth Service

Audit and compliance tracking for authentication events, user actions,
and security policy enforcement.

Following SSOT principles for audit logging and compliance reporting.
"""

from auth_service.auth_core.audit.audit_business_logic import (
    AuditBusinessLogic,
    AuditEventResult,
)

__all__ = [
    "AuditBusinessLogic",
    "AuditEventResult",
]