"""Domain-specific compliance checks for various security standards."""

from typing import Dict
from datetime import datetime, timezone

from .compliance_types import ComplianceCheck, ComplianceStandard, ComplianceStatus


class DomainComplianceChecks:
    """Domain-specific compliance check implementations."""
    
    def get_all_checks(self) -> Dict[str, ComplianceCheck]:
        """Get all domain compliance checks."""
        checks = {}
        self._add_nist_checks(checks)
        self._add_authentication_checks(checks)
        self._add_data_protection_checks(checks)
        self._add_api_security_checks(checks)
        self._add_infrastructure_checks(checks)
        return checks
    
    def _add_nist_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add NIST Cybersecurity Framework checks."""
        checks["NIST_ID_001"] = ComplianceCheck(
            id="NIST_ID_001",
            title="Asset Management",
            description="Identify and manage organizational assets",
            standard=ComplianceStandard.NIST_CSF,
            requirement="ID.AM - Asset Management",
            status=ComplianceStatus.NEEDS_REVIEW,
            evidence=[],
            remediation_steps=[
                "Create comprehensive asset inventory",
                "Implement asset classification",
                "Establish asset management procedures"
            ],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        checks["NIST_PR_001"] = ComplianceCheck(
            id="NIST_PR_001",
            title="Access Control",
            description="Implement access control measures",
            standard=ComplianceStandard.NIST_CSF,
            requirement="PR.AC - Identity Management and Access Control",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Role-based access control",
                "Multi-factor authentication",
                "Account management procedures",
                "Access reviews"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_authentication_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add authentication-specific checks."""
        checks["AUTH_001"] = ComplianceCheck(
            id="AUTH_001",
            title="Password Policy",
            description="Implement strong password policies",
            standard=ComplianceStandard.NIST_CSF,
            requirement="Authentication Security",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "bcrypt password hashing",
                "Password complexity validation",
                "Account lockout after failed attempts"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        checks["AUTH_002"] = ComplianceCheck(
            id="AUTH_002",
            title="Session Management",
            description="Secure session management implementation",
            standard=ComplianceStandard.NIST_CSF,
            requirement="Session Security",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Session timeout implementation",
                "Secure session tokens",
                "Session invalidation on logout",
                "CSRF protection"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_data_protection_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add data protection checks."""
        checks["DATA_001"] = ComplianceCheck(
            id="DATA_001",
            title="Data Encryption",
            description="Implement data encryption at rest and in transit",
            standard=ComplianceStandard.GDPR,
            requirement="Data Protection",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "HTTPS for data in transit",
                "Database encryption support",
                "Fernet encryption for sensitive data",
                "Encrypted API communications"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        checks["DATA_002"] = ComplianceCheck(
            id="DATA_002",
            title="Data Retention",
            description="Implement proper data retention policies",
            standard=ComplianceStandard.GDPR,
            requirement="Data Retention and Deletion",
            status=ComplianceStatus.NEEDS_REVIEW,
            evidence=[],
            remediation_steps=[
                "Define data retention policies",
                "Implement automated data purging",
                "Create data deletion procedures"
            ],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_api_security_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add API security checks."""
        checks["API_001"] = ComplianceCheck(
            id="API_001",
            title="API Authentication",
            description="Secure API authentication and authorization",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="API Security",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "JWT token authentication",
                "API key management system",
                "Rate limiting implementation",
                "Input validation on all endpoints"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        checks["API_002"] = ComplianceCheck(
            id="API_002",
            title="API Rate Limiting",
            description="Implement comprehensive API rate limiting",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="DoS Protection",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Rate limiting middleware",
                "IP-based rate limiting",
                "User-based rate limiting",
                "Adaptive rate limiting for WebSockets"
            ],
            remediation_steps=[],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_infrastructure_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add infrastructure security checks."""
        checks["INFRA_001"] = ComplianceCheck(
            id="INFRA_001",
            title="Security Headers",
            description="Implement comprehensive security headers",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="Security Configuration",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Content Security Policy",
                "HSTS implementation",
                "X-Frame-Options",
                "X-Content-Type-Options",
                "Referrer Policy"
            ],
            remediation_steps=[],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        checks["INFRA_002"] = ComplianceCheck(
            id="INFRA_002",
            title="Error Handling",
            description="Secure error handling without information disclosure",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="Information Disclosure Prevention",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Generic error responses",
                "Structured error handling",
                "No stack traces in production",
                "Error correlation IDs"
            ],
            remediation_steps=[],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
