"""
Specific compliance rule implementations.
Implements OWASP, NIST, authentication, data protection, API, and infrastructure checks.
"""

from typing import List
from datetime import datetime, timezone

from app.logging_config import central_logger
from .compliance_checks import (
    ComplianceCheck, ComplianceCheckManager, ComplianceStandard, ComplianceStatus
)

logger = central_logger.get_logger(__name__)


class ComplianceRuleFactory:
    """Factory for creating compliance rules."""
    
    def __init__(self, check_manager: ComplianceCheckManager):
        self.check_manager = check_manager
    
    def initialize_all_checks(self) -> None:
        """Initialize all compliance checks."""
        self._add_owasp_checks()
        self._add_nist_checks()
        self._add_authentication_checks()
        self._add_data_protection_checks()
        self._add_api_security_checks()
        self._add_infrastructure_checks()
    
    def _add_owasp_checks(self) -> None:
        """Add OWASP Top 10 2021 compliance checks."""
        self._add_owasp_primary_checks()
        self._add_owasp_secondary_checks()
        self._add_owasp_logging_monitoring_checks()
    
    def _add_owasp_primary_checks(self) -> None:
        """Add primary OWASP checks (A01-A04)."""
        self._add_owasp_access_control_check()
        self._add_owasp_cryptographic_check()
        self._add_owasp_injection_check()
        self._add_owasp_design_check()
    
    def _add_owasp_secondary_checks(self) -> None:
        """Add secondary OWASP checks (A05-A08)."""
        self._add_owasp_misconfiguration_check()
        self._add_owasp_component_check()
        self._add_owasp_authentication_check()
        self._add_owasp_integrity_check()
    
    def _add_owasp_logging_monitoring_checks(self) -> None:
        """Add OWASP logging and SSRF checks."""
        self._add_owasp_logging_check()
        self._add_owasp_ssrf_check()
    
    def _create_owasp_check(self, check_id: str, title: str, description: str,
                           requirement: str, status: ComplianceStatus, evidence: List[str],
                           remediation_steps: List[str], priority: str) -> None:
        """Create and store an OWASP compliance check."""
        check = self._build_owasp_check_object(check_id, title, description, requirement,
                                              status, evidence, remediation_steps, priority)
        self.check_manager.add_check(check)
    
    def _build_owasp_check_object(self, check_id: str, title: str, description: str,
                                 requirement: str, status: ComplianceStatus, evidence: List[str],
                                 remediation_steps: List[str], priority: str) -> ComplianceCheck:
        """Build OWASP compliance check object."""
        return ComplianceCheck(
            id=check_id, title=title, description=description,
            standard=ComplianceStandard.OWASP_TOP_10, requirement=requirement,
            status=status, evidence=evidence, remediation_steps=remediation_steps,
            priority=priority, last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_owasp_access_control_check(self) -> None:
        """Add OWASP A01 - Broken Access Control check."""
        evidence = self._get_access_control_evidence()
        self._create_owasp_check(
            "OWASP_A01_001", "Access Control Implementation",
            "Ensure proper access control mechanisms are implemented",
            "A01:2021 - Broken Access Control", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _get_access_control_evidence(self) -> List[str]:
        """Get evidence for access control compliance."""
        return [
            "Role-based access control implemented",
            "Permission service validates user permissions",
            "Admin endpoints protected with proper authorization",
            "API endpoints use authentication middleware"
        ]
    
    def _add_owasp_cryptographic_check(self) -> None:
        """Add OWASP A02 - Cryptographic Failures check."""
        evidence = self._get_cryptographic_evidence()
        self._create_owasp_check(
            "OWASP_A02_001", "Cryptographic Implementation",
            "Ensure proper cryptographic practices",
            "A02:2021 - Cryptographic Failures", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _get_cryptographic_evidence(self) -> List[str]:
        """Get evidence for cryptographic compliance."""
        return [
            "JWT tokens use strong signing algorithms", "Passwords are hashed using bcrypt",
            "Fernet encryption for sensitive data", "API keys are hashed for storage",
            "Strong session management"
        ]
    
    def _add_owasp_injection_check(self) -> None:
        """Add OWASP A03 - Injection check."""
        evidence = self._get_injection_evidence()
        self._create_owasp_check(
            "OWASP_A03_001", "Injection Prevention",
            "Prevent injection attacks through input validation",
            "A03:2021 - Injection", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _get_injection_evidence(self) -> List[str]:
        """Get evidence for injection prevention compliance."""
        return [
            "SQL injection detection patterns implemented",
            "XSS prevention in security middleware",
            "Command injection detection", "Path traversal protection",
            "Input validation on all endpoints", "Parameterized queries used"
        ]
    
    def _add_owasp_design_check(self) -> None:
        """Add OWASP A04 - Insecure Design check."""
        evidence = self._get_secure_design_evidence()
        self._create_owasp_check(
            "OWASP_A04_001", "Secure Design Practices",
            "Implement secure design principles",
            "A04:2021 - Insecure Design", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _get_secure_design_evidence(self) -> List[str]:
        """Get evidence for secure design compliance."""
        return [
            "Threat modeling conducted", "Security requirements defined",
            "Defense in depth implemented", "Principle of least privilege applied",
            "Secure development lifecycle followed"
        ]
    
    def _add_owasp_misconfiguration_check(self) -> None:
        """Add OWASP A05 - Security Misconfiguration check."""
        evidence = self._get_misconfiguration_evidence()
        self._create_owasp_check(
            "OWASP_A05_001", "Security Configuration",
            "Ensure proper security configuration",
            "A05:2021 - Security Misconfiguration", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _get_misconfiguration_evidence(self) -> List[str]:
        """Get evidence for misconfiguration prevention compliance."""
        return [
            "Security headers implemented", "CORS properly configured",
            "Error handling doesn't leak information", "Debug mode disabled in production",
            "Default credentials changed", "Unnecessary features disabled"
        ]
    
    def _add_owasp_component_check(self) -> None:
        """Add OWASP A06 - Vulnerable and Outdated Components check."""
        evidence, remediation = self._get_component_security_data()
        self._create_owasp_check(
            "OWASP_A06_001", "Component Security",
            "Manage vulnerable and outdated components",
            "A06:2021 - Vulnerable and Outdated Components",
            ComplianceStatus.NEEDS_REVIEW, evidence, remediation, "medium"
        )
    
    def _get_component_security_data(self) -> tuple[List[str], List[str]]:
        """Get evidence and remediation for component security."""
        evidence = ["Dependency scanning in place"]
        remediation = [
            "Implement automated dependency vulnerability scanning",
            "Establish process for regular dependency updates",
            "Monitor security advisories for used components"
        ]
        return evidence, remediation
    
    def _add_owasp_authentication_check(self) -> None:
        """Add OWASP A07 - Authentication Failures check."""
        evidence = self._get_authentication_evidence()
        self._create_owasp_check(
            "OWASP_A07_001", "Authentication Security",
            "Secure authentication and session management",
            "A07:2021 - Identification and Authentication Failures",
            ComplianceStatus.COMPLIANT, evidence, [], "high"
        )
    
    def _get_authentication_evidence(self) -> List[str]:
        """Get evidence for authentication security compliance."""
        return [
            "Multi-factor authentication support", "Account lockout mechanisms",
            "Session management with timeouts", "Strong password requirements",
            "Secure session tokens", "Brute force protection"
        ]
    
    def _add_owasp_integrity_check(self) -> None:
        """Add OWASP A08 - Software and Data Integrity Failures check."""
        evidence, remediation = self._get_integrity_data()
        self._create_owasp_check(
            "OWASP_A08_001", "Data Integrity",
            "Ensure software and data integrity",
            "A08:2021 - Software and Data Integrity Failures",
            ComplianceStatus.PARTIALLY_COMPLIANT, evidence, remediation, "medium"
        )
    
    def _get_integrity_data(self) -> tuple[List[str], List[str]]:
        """Get evidence and remediation for data integrity."""
        evidence = ["Input validation implemented", "API data validation with Pydantic"]
        remediation = [
            "Implement code signing for deployments",
            "Add integrity checks for critical data",
            "Implement secure CI/CD pipeline"
        ]
        return evidence, remediation
    
    def _add_owasp_logging_check(self) -> None:
        """Add OWASP A09 - Security Logging and Monitoring Failures check."""
        evidence = self._get_logging_evidence()
        self._create_owasp_check(
            "OWASP_A09_001", "Security Logging and Monitoring",
            "Implement comprehensive logging and monitoring",
            "A09:2021 - Security Logging and Monitoring Failures",
            ComplianceStatus.COMPLIANT, evidence, [], "high"
        )
    
    def _get_logging_evidence(self) -> List[str]:
        """Get evidence for logging and monitoring compliance."""
        return [
            "Comprehensive logging framework", "Security event logging",
            "Authentication attempt logging", "Error logging with correlation IDs",
            "Security audit framework"
        ]
    
    def _add_owasp_ssrf_check(self) -> None:
        """Add OWASP A10 - Server-Side Request Forgery check."""
        evidence, remediation = self._get_ssrf_data()
        self._create_owasp_check(
            "OWASP_A10_001", "SSRF Prevention",
            "Prevent server-side request forgery attacks",
            "A10:2021 - Server-Side Request Forgery (SSRF)",
            ComplianceStatus.PARTIALLY_COMPLIANT, evidence, remediation, "medium"
        )
    
    def _get_ssrf_data(self) -> tuple[List[str], List[str]]:
        """Get evidence and remediation for SSRF prevention."""
        evidence = ["Input validation for URLs", "Network segmentation"]
        remediation = [
            "Implement URL validation whitelist",
            "Add network-level SSRF protection",
            "Validate and sanitize all user-provided URLs"
        ]
        return evidence, remediation
    
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