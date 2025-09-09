"""
Compliance Package - Auth Service

Compliance management and regulatory requirements for authentication,
data protection, and user privacy regulations.

Following SSOT principles for compliance tracking and reporting.
"""

from auth_service.auth_core.compliance.compliance_business_logic import (
    ComplianceBusinessLogic,
    ComplianceResult,
)

__all__ = [
    "ComplianceBusinessLogic",
    "ComplianceResult",
]