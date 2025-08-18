"""
Standard compliance rule implementations.
Implements NIST, authentication, data protection, API, and infrastructure checks.
"""

from typing import List
from datetime import datetime, timezone

from app.logging_config import central_logger
from .compliance_checks import (
    ComplianceCheck, ComplianceCheckManager, ComplianceStandard, ComplianceStatus
)

logger = central_logger.get_logger(__name__)


class StandardRuleFactory:
    """Factory for creating standard compliance rules."""
    
    def __init__(self, check_manager: ComplianceCheckManager):
        self.check_manager = check_manager
    
    def add_all_standard_checks(self) -> None:
        """Add all standard compliance checks."""
        self._add_nist_checks()
        self._add_authentication_checks()
        self._add_data_protection_checks()
        self._add_api_security_checks()
        self._add_infrastructure_checks()
    
    def _add_nist_checks(self) -> None:
        """Add NIST Cybersecurity Framework checks."""
        self._add_nist_asset_management_check()
        self._add_nist_access_control_check()
    
    def _add_nist_asset_management_check(self) -> None:
        """Add NIST asset management check."""
        check = self._create_standard_check(
            "NIST_ID_001", "Asset Management", "Identify and manage organizational assets",
            ComplianceStandard.NIST_CSF, "ID.AM - Asset Management", ComplianceStatus.NEEDS_REVIEW,
            [], ["Create comprehensive asset inventory", "Implement asset classification", "Establish asset management procedures"], "medium"
        )
        self.check_manager.add_check(check)
    
    def _add_nist_access_control_check(self) -> None:
        """Add NIST access control check."""
        check = self._create_standard_check(
            "NIST_PR_001", "Access Control", "Implement access control measures",
            ComplianceStandard.NIST_CSF, "PR.AC - Identity Management and Access Control", ComplianceStatus.COMPLIANT,
            ["Role-based access control", "Multi-factor authentication", "Account management procedures", "Access reviews"], [], "high"
        )
        self.check_manager.add_check(check)
    
    def _add_authentication_checks(self) -> None:
        """Add authentication-specific checks."""
        self._add_password_policy_check()
        self._add_session_management_check()
    
    def _add_password_policy_check(self) -> None:
        """Add password policy check."""
        check = self._create_standard_check(
            "AUTH_001", "Password Policy", "Implement strong password policies",
            ComplianceStandard.NIST_CSF, "Authentication Security", ComplianceStatus.COMPLIANT,
            ["bcrypt password hashing", "Password complexity validation", "Account lockout after failed attempts"], [], "high"
        )
        self.check_manager.add_check(check)
    
    def _add_session_management_check(self) -> None:
        """Add session management check."""
        check = self._create_standard_check(
            "AUTH_002", "Session Management", "Secure session management implementation",
            ComplianceStandard.NIST_CSF, "Session Security", ComplianceStatus.COMPLIANT,
            ["Session timeout implementation", "Secure session tokens", "Session invalidation on logout", "CSRF protection"], [], "high"
        )
        self.check_manager.add_check(check)
    
    def _add_data_protection_checks(self) -> None:
        """Add data protection checks."""
        self._add_data_encryption_check()
        self._add_data_retention_check()
    
    def _add_data_encryption_check(self) -> None:
        """Add data encryption check."""
        check = self._create_standard_check(
            "DATA_001", "Data Encryption", "Implement data encryption at rest and in transit",
            ComplianceStandard.GDPR, "Data Protection", ComplianceStatus.COMPLIANT,
            ["HTTPS for data in transit", "Database encryption support", "Fernet encryption for sensitive data", "Encrypted API communications"], [], "high"
        )
        self.check_manager.add_check(check)
    
    def _add_data_retention_check(self) -> None:
        """Add data retention check."""
        check = self._create_standard_check(
            "DATA_002", "Data Retention", "Implement proper data retention policies",
            ComplianceStandard.GDPR, "Data Retention and Deletion", ComplianceStatus.NEEDS_REVIEW,
            [], ["Define data retention policies", "Implement automated data purging", "Create data deletion procedures"], "medium"
        )
        self.check_manager.add_check(check)
    
    def _add_api_security_checks(self) -> None:
        """Add API security checks."""
        self._add_api_authentication_check()
        self._add_api_rate_limiting_check()
    
    def _add_api_authentication_check(self) -> None:
        """Add API authentication check."""
        check = self._create_standard_check(
            "API_001", "API Authentication", "Secure API authentication and authorization",
            ComplianceStandard.OWASP_TOP_10, "API Security", ComplianceStatus.COMPLIANT,
            ["JWT token authentication", "API key management system", "Rate limiting implementation", "Input validation on all endpoints"], [], "high"
        )
        self.check_manager.add_check(check)
    
    def _add_api_rate_limiting_check(self) -> None:
        """Add API rate limiting check."""
        check = self._create_standard_check(
            "API_002", "API Rate Limiting", "Implement comprehensive API rate limiting",
            ComplianceStandard.OWASP_TOP_10, "DoS Protection", ComplianceStatus.COMPLIANT,
            ["Rate limiting middleware", "IP-based rate limiting", "User-based rate limiting", "Adaptive rate limiting for WebSockets"], [], "medium"
        )
        self.check_manager.add_check(check)
    
    def _add_infrastructure_checks(self) -> None:
        """Add infrastructure security checks."""
        self._add_security_headers_check()
        self._add_error_handling_check()
    
    def _add_security_headers_check(self) -> None:
        """Add security headers check."""
        check = self._create_standard_check(
            "INFRA_001", "Security Headers", "Implement comprehensive security headers",
            ComplianceStandard.OWASP_TOP_10, "Security Configuration", ComplianceStatus.COMPLIANT,
            ["Content Security Policy", "HSTS implementation", "X-Frame-Options", "X-Content-Type-Options", "Referrer Policy"], [], "medium"
        )
        self.check_manager.add_check(check)
    
    def _add_error_handling_check(self) -> None:
        """Add error handling check."""
        check = self._create_standard_check(
            "INFRA_002", "Error Handling", "Secure error handling without information disclosure",
            ComplianceStandard.OWASP_TOP_10, "Information Disclosure Prevention", ComplianceStatus.COMPLIANT,
            ["Generic error responses", "Structured error handling", "No stack traces in production", "Error correlation IDs"], [], "medium"
        )
        self.check_manager.add_check(check)
    
    def _create_standard_check(self, id: str, title: str, description: str,
                             standard: ComplianceStandard, requirement: str, status: ComplianceStatus,
                             evidence: List[str], remediation_steps: List[str], priority: str) -> ComplianceCheck:
        """Create a standard compliance check with common fields."""
        return ComplianceCheck(id=id, title=title, description=description, standard=standard,
                             requirement=requirement, status=status, evidence=evidence,
                             remediation_steps=remediation_steps, priority=priority,
                             last_checked=datetime.now(timezone.utc), next_check_date=datetime.now(timezone.utc))