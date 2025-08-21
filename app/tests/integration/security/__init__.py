"""
Security Audit Integration Tests Package

BVJ:
- Segment: Enterprise ($200K+ MRR)
- Business Goal: Compliance reporting protecting $200K+ MRR
- Value Impact: Critical SOC2/GDPR/HIPAA compliance for Enterprise customers
- Revenue Impact: Protects and enables $200K+ enterprise revenue stream

This package contains focused integration tests for:
- Authentication Audit: Login/logout event capture and tamper-proof storage
- Data Access Audit: Resource-level access tracking with compliance flags
- Compliance Reporting: SOC2/GDPR/HIPAA report generation and validation

All tests maintain ≤8 lines per test function and ≤300 lines per module.
"""

from .shared_fixtures import (
    MockSecurityInfrastructure,
    AuthenticationAuditHelper,
    DataAccessAuditHelper,
    ComplianceReportingHelper,
    enterprise_security_infrastructure,
    auth_audit_helper,
    data_access_helper,
    compliance_helper
)

__all__ = [
    "MockSecurityInfrastructure",
    "AuthenticationAuditHelper",
    "DataAccessAuditHelper",
    "ComplianceReportingHelper",
    "enterprise_security_infrastructure",
    "auth_audit_helper",
    "data_access_helper",
    "compliance_helper"
]