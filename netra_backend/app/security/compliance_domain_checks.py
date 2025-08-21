"""Domain-specific compliance checks for various security standards."""

from typing import Dict
from datetime import datetime, timezone

from netra_backend.app.compliance_types import ComplianceCheck, ComplianceStandard, ComplianceStatus


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
        self._add_nist_asset_management_check(checks)
        self._add_nist_access_control_check(checks)
    
    def _add_nist_asset_management_check(self, checks: Dict[str, ComplianceCheck]):
        """Add NIST asset management check."""
        checks["NIST_ID_001"] = self._create_compliance_check(
            "NIST_ID_001", "Asset Management", "Identify and manage organizational assets",
            ComplianceStandard.NIST_CSF, "ID.AM - Asset Management", ComplianceStatus.NEEDS_REVIEW,
            [], ["Create comprehensive asset inventory", "Implement asset classification", "Establish asset management procedures"], "medium"
        )
    
    def _add_nist_access_control_check(self, checks: Dict[str, ComplianceCheck]):
        """Add NIST access control check."""
        checks["NIST_PR_001"] = self._create_compliance_check(
            "NIST_PR_001", "Access Control", "Implement access control measures",
            ComplianceStandard.NIST_CSF, "PR.AC - Identity Management and Access Control", ComplianceStatus.COMPLIANT,
            ["Role-based access control", "Multi-factor authentication", "Account management procedures", "Access reviews"], [], "high"
        )
    
    def _add_authentication_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add authentication-specific checks."""
        self._add_password_policy_check(checks)
        self._add_session_management_check(checks)
    
    def _add_password_policy_check(self, checks: Dict[str, ComplianceCheck]):
        """Add password policy check."""
        checks["AUTH_001"] = self._create_compliance_check(
            "AUTH_001", "Password Policy", "Implement strong password policies",
            ComplianceStandard.NIST_CSF, "Authentication Security", ComplianceStatus.COMPLIANT,
            ["bcrypt password hashing", "Password complexity validation", "Account lockout after failed attempts"], [], "high"
        )
    
    def _add_session_management_check(self, checks: Dict[str, ComplianceCheck]):
        """Add session management check."""
        checks["AUTH_002"] = self._create_compliance_check(
            "AUTH_002", "Session Management", "Secure session management implementation",
            ComplianceStandard.NIST_CSF, "Session Security", ComplianceStatus.COMPLIANT,
            ["Session timeout implementation", "Secure session tokens", "Session invalidation on logout", "CSRF protection"], [], "high"
        )
    
    def _add_data_protection_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add data protection checks."""
        self._add_data_encryption_check(checks)
        self._add_data_retention_check(checks)
    
    def _add_data_encryption_check(self, checks: Dict[str, ComplianceCheck]):
        """Add data encryption check."""
        checks["DATA_001"] = self._create_compliance_check(
            "DATA_001", "Data Encryption", "Implement data encryption at rest and in transit",
            ComplianceStandard.GDPR, "Data Protection", ComplianceStatus.COMPLIANT,
            ["HTTPS for data in transit", "Database encryption support", "Fernet encryption for sensitive data", "Encrypted API communications"], [], "high"
        )
    
    def _add_data_retention_check(self, checks: Dict[str, ComplianceCheck]):
        """Add data retention check."""
        checks["DATA_002"] = self._create_compliance_check(
            "DATA_002", "Data Retention", "Implement proper data retention policies",
            ComplianceStandard.GDPR, "Data Retention and Deletion", ComplianceStatus.NEEDS_REVIEW,
            [], ["Define data retention policies", "Implement automated data purging", "Create data deletion procedures"], "medium"
        )
    
    def _add_api_security_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add API security checks."""
        self._add_api_authentication_check(checks)
        self._add_api_rate_limiting_check(checks)
    
    def _add_api_authentication_check(self, checks: Dict[str, ComplianceCheck]):
        """Add API authentication check."""
        checks["API_001"] = self._create_compliance_check(
            "API_001", "API Authentication", "Secure API authentication and authorization",
            ComplianceStandard.OWASP_TOP_10, "API Security", ComplianceStatus.COMPLIANT,
            ["JWT token authentication", "API key management system", "Rate limiting implementation", "Input validation on all endpoints"], [], "high"
        )
    
    def _add_api_rate_limiting_check(self, checks: Dict[str, ComplianceCheck]):
        """Add API rate limiting check."""
        checks["API_002"] = self._create_compliance_check(
            "API_002", "API Rate Limiting", "Implement comprehensive API rate limiting",
            ComplianceStandard.OWASP_TOP_10, "DoS Protection", ComplianceStatus.COMPLIANT,
            ["Rate limiting middleware", "IP-based rate limiting", "User-based rate limiting", "Adaptive rate limiting for WebSockets"], [], "medium"
        )
    
    def _add_infrastructure_checks(self, checks: Dict[str, ComplianceCheck]):
        """Add infrastructure security checks."""
        self._add_security_headers_check(checks)
        self._add_error_handling_check(checks)
    
    def _add_security_headers_check(self, checks: Dict[str, ComplianceCheck]):
        """Add security headers check."""
        checks["INFRA_001"] = self._create_compliance_check(
            "INFRA_001", "Security Headers", "Implement comprehensive security headers",
            ComplianceStandard.OWASP_TOP_10, "Security Configuration", ComplianceStatus.COMPLIANT,
            ["Content Security Policy", "HSTS implementation", "X-Frame-Options", "X-Content-Type-Options", "Referrer Policy"], [], "medium"
        )
    
    def _add_error_handling_check(self, checks: Dict[str, ComplianceCheck]):
        """Add error handling check."""
        checks["INFRA_002"] = self._create_compliance_check(
            "INFRA_002", "Error Handling", "Secure error handling without information disclosure",
            ComplianceStandard.OWASP_TOP_10, "Information Disclosure Prevention", ComplianceStatus.COMPLIANT,
            ["Generic error responses", "Structured error handling", "No stack traces in production", "Error correlation IDs"], [], "medium"
        )
    
    def _create_compliance_check(self, id: str, title: str, description: str,
                               standard: ComplianceStandard, requirement: str, status: ComplianceStatus,
                               evidence: list, remediation_steps: list, priority: str) -> ComplianceCheck:
        """Create a compliance check with common fields."""
        return ComplianceCheck(id=id, title=title, description=description, standard=standard,
                             requirement=requirement, status=status, evidence=evidence,
                             remediation_steps=remediation_steps, priority=priority,
                             last_checked=datetime.now(timezone.utc), next_check_date=datetime.now(timezone.utc))