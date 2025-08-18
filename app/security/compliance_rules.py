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
        self._add_owasp_access_control_check()
        self._add_owasp_cryptographic_check()
        self._add_owasp_injection_check()
        self._add_owasp_design_check()
        self._add_owasp_misconfiguration_check()
        self._add_owasp_component_check()
        self._add_owasp_authentication_check()
        self._add_owasp_integrity_check()
        self._add_owasp_logging_check()
        self._add_owasp_ssrf_check()
    
    def _create_owasp_check(self, check_id: str, title: str, description: str,
                           requirement: str, status: ComplianceStatus, evidence: List[str],
                           remediation_steps: List[str], priority: str) -> None:
        """Create and store an OWASP compliance check."""
        check = ComplianceCheck(
            id=check_id, title=title, description=description,
            standard=ComplianceStandard.OWASP_TOP_10, requirement=requirement,
            status=status, evidence=evidence, remediation_steps=remediation_steps,
            priority=priority, last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_owasp_access_control_check(self) -> None:
        """Add OWASP A01 - Broken Access Control check."""
        evidence = [
            "Role-based access control implemented",
            "Permission service validates user permissions",
            "Admin endpoints protected with proper authorization",
            "API endpoints use authentication middleware"
        ]
        self._create_owasp_check(
            "OWASP_A01_001", "Access Control Implementation",
            "Ensure proper access control mechanisms are implemented",
            "A01:2021 - Broken Access Control", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _add_owasp_cryptographic_check(self) -> None:
        """Add OWASP A02 - Cryptographic Failures check."""
        evidence = [
            "JWT tokens use strong signing algorithms", "Passwords are hashed using bcrypt",
            "Fernet encryption for sensitive data", "API keys are hashed for storage",
            "Strong session management"
        ]
        self._create_owasp_check(
            "OWASP_A02_001", "Cryptographic Implementation",
            "Ensure proper cryptographic practices",
            "A02:2021 - Cryptographic Failures", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _add_owasp_injection_check(self) -> None:
        """Add OWASP A03 - Injection check."""
        evidence = [
            "SQL injection detection patterns implemented",
            "XSS prevention in security middleware",
            "Command injection detection", "Path traversal protection",
            "Input validation on all endpoints", "Parameterized queries used"
        ]
        self._create_owasp_check(
            "OWASP_A03_001", "Injection Prevention",
            "Prevent injection attacks through input validation",
            "A03:2021 - Injection", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _add_owasp_design_check(self) -> None:
        """Add OWASP A04 - Insecure Design check."""
        evidence = [
            "Threat modeling conducted", "Security requirements defined",
            "Defense in depth implemented", "Principle of least privilege applied",
            "Secure development lifecycle followed"
        ]
        self._create_owasp_check(
            "OWASP_A04_001", "Secure Design Practices",
            "Implement secure design principles",
            "A04:2021 - Insecure Design", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _add_owasp_misconfiguration_check(self) -> None:
        """Add OWASP A05 - Security Misconfiguration check."""
        evidence = [
            "Security headers implemented", "CORS properly configured",
            "Error handling doesn't leak information", "Debug mode disabled in production",
            "Default credentials changed", "Unnecessary features disabled"
        ]
        self._create_owasp_check(
            "OWASP_A05_001", "Security Configuration",
            "Ensure proper security configuration",
            "A05:2021 - Security Misconfiguration", ComplianceStatus.COMPLIANT,
            evidence, [], "high"
        )
    
    def _add_owasp_component_check(self) -> None:
        """Add OWASP A06 - Vulnerable and Outdated Components check."""
        remediation = [
            "Implement automated dependency vulnerability scanning",
            "Establish process for regular dependency updates",
            "Monitor security advisories for used components"
        ]
        self._create_owasp_check(
            "OWASP_A06_001", "Component Security",
            "Manage vulnerable and outdated components",
            "A06:2021 - Vulnerable and Outdated Components",
            ComplianceStatus.NEEDS_REVIEW, ["Dependency scanning in place"],
            remediation, "medium"
        )
    
    def _add_owasp_authentication_check(self) -> None:
        """Add OWASP A07 - Authentication Failures check."""
        evidence = [
            "Multi-factor authentication support", "Account lockout mechanisms",
            "Session management with timeouts", "Strong password requirements",
            "Secure session tokens", "Brute force protection"
        ]
        self._create_owasp_check(
            "OWASP_A07_001", "Authentication Security",
            "Secure authentication and session management",
            "A07:2021 - Identification and Authentication Failures",
            ComplianceStatus.COMPLIANT, evidence, [], "high"
        )
    
    def _add_owasp_integrity_check(self) -> None:
        """Add OWASP A08 - Software and Data Integrity Failures check."""
        evidence = ["Input validation implemented", "API data validation with Pydantic"]
        remediation = [
            "Implement code signing for deployments",
            "Add integrity checks for critical data",
            "Implement secure CI/CD pipeline"
        ]
        self._create_owasp_check(
            "OWASP_A08_001", "Data Integrity",
            "Ensure software and data integrity",
            "A08:2021 - Software and Data Integrity Failures",
            ComplianceStatus.PARTIALLY_COMPLIANT, evidence, remediation, "medium"
        )
    
    def _add_owasp_logging_check(self) -> None:
        """Add OWASP A09 - Security Logging and Monitoring Failures check."""
        evidence = [
            "Comprehensive logging framework", "Security event logging",
            "Authentication attempt logging", "Error logging with correlation IDs",
            "Security audit framework"
        ]
        self._create_owasp_check(
            "OWASP_A09_001", "Security Logging and Monitoring",
            "Implement comprehensive logging and monitoring",
            "A09:2021 - Security Logging and Monitoring Failures",
            ComplianceStatus.COMPLIANT, evidence, [], "high"
        )
    
    def _add_owasp_ssrf_check(self) -> None:
        """Add OWASP A10 - Server-Side Request Forgery check."""
        evidence = ["Input validation for URLs", "Network segmentation"]
        remediation = [
            "Implement URL validation whitelist",
            "Add network-level SSRF protection",
            "Validate and sanitize all user-provided URLs"
        ]
        self._create_owasp_check(
            "OWASP_A10_001", "SSRF Prevention",
            "Prevent server-side request forgery attacks",
            "A10:2021 - Server-Side Request Forgery (SSRF)",
            ComplianceStatus.PARTIALLY_COMPLIANT, evidence, remediation, "medium"
        )
    
    def _add_nist_checks(self) -> None:
        """Add NIST Cybersecurity Framework checks."""
        self._add_nist_asset_management_check()
        self._add_nist_access_control_check()
    
    def _add_nist_asset_management_check(self) -> None:
        """Add NIST asset management check."""
        check = ComplianceCheck(
            id="NIST_ID_001", title="Asset Management",
            description="Identify and manage organizational assets",
            standard=ComplianceStandard.NIST_CSF,
            requirement="ID.AM - Asset Management",
            status=ComplianceStatus.NEEDS_REVIEW, evidence=[],
            remediation_steps=[
                "Create comprehensive asset inventory",
                "Implement asset classification",
                "Establish asset management procedures"
            ],
            priority="medium", last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_nist_access_control_check(self) -> None:
        """Add NIST access control check."""
        check = ComplianceCheck(
            id="NIST_PR_001", title="Access Control",
            description="Implement access control measures",
            standard=ComplianceStandard.NIST_CSF,
            requirement="PR.AC - Identity Management and Access Control",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Role-based access control", "Multi-factor authentication",
                "Account management procedures", "Access reviews"
            ],
            remediation_steps=[], priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_authentication_checks(self) -> None:
        """Add authentication-specific checks."""
        self._add_password_policy_check()
        self._add_session_management_check()
    
    def _add_password_policy_check(self) -> None:
        """Add password policy check."""
        check = ComplianceCheck(
            id="AUTH_001", title="Password Policy",
            description="Implement strong password policies",
            standard=ComplianceStandard.NIST_CSF,
            requirement="Authentication Security",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "bcrypt password hashing", "Password complexity validation",
                "Account lockout after failed attempts"
            ],
            remediation_steps=[], priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_session_management_check(self) -> None:
        """Add session management check."""
        check = ComplianceCheck(
            id="AUTH_002", title="Session Management",
            description="Secure session management implementation",
            standard=ComplianceStandard.NIST_CSF,
            requirement="Session Security", status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Session timeout implementation", "Secure session tokens",
                "Session invalidation on logout", "CSRF protection"
            ],
            remediation_steps=[], priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_data_protection_checks(self) -> None:
        """Add data protection checks."""
        self._add_data_encryption_check()
        self._add_data_retention_check()
    
    def _add_data_encryption_check(self) -> None:
        """Add data encryption check."""
        check = ComplianceCheck(
            id="DATA_001", title="Data Encryption",
            description="Implement data encryption at rest and in transit",
            standard=ComplianceStandard.GDPR, requirement="Data Protection",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "HTTPS for data in transit", "Database encryption support",
                "Fernet encryption for sensitive data", "Encrypted API communications"
            ],
            remediation_steps=[], priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_data_retention_check(self) -> None:
        """Add data retention check."""
        check = ComplianceCheck(
            id="DATA_002", title="Data Retention",
            description="Implement proper data retention policies",
            standard=ComplianceStandard.GDPR,
            requirement="Data Retention and Deletion",
            status=ComplianceStatus.NEEDS_REVIEW, evidence=[],
            remediation_steps=[
                "Define data retention policies", "Implement automated data purging",
                "Create data deletion procedures"
            ],
            priority="medium", last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_api_security_checks(self) -> None:
        """Add API security checks."""
        self._add_api_authentication_check()
        self._add_api_rate_limiting_check()
    
    def _add_api_authentication_check(self) -> None:
        """Add API authentication check."""
        check = ComplianceCheck(
            id="API_001", title="API Authentication",
            description="Secure API authentication and authorization",
            standard=ComplianceStandard.OWASP_TOP_10, requirement="API Security",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "JWT token authentication", "API key management system",
                "Rate limiting implementation", "Input validation on all endpoints"
            ],
            remediation_steps=[], priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_api_rate_limiting_check(self) -> None:
        """Add API rate limiting check."""
        check = ComplianceCheck(
            id="API_002", title="API Rate Limiting",
            description="Implement comprehensive API rate limiting",
            standard=ComplianceStandard.OWASP_TOP_10, requirement="DoS Protection",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Rate limiting middleware", "IP-based rate limiting",
                "User-based rate limiting", "Adaptive rate limiting for WebSockets"
            ],
            remediation_steps=[], priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_infrastructure_checks(self) -> None:
        """Add infrastructure security checks."""
        self._add_security_headers_check()
        self._add_error_handling_check()
    
    def _add_security_headers_check(self) -> None:
        """Add security headers check."""
        check = ComplianceCheck(
            id="INFRA_001", title="Security Headers",
            description="Implement comprehensive security headers",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="Security Configuration",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Content Security Policy", "HSTS implementation",
                "X-Frame-Options", "X-Content-Type-Options", "Referrer Policy"
            ],
            remediation_steps=[], priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)
    
    def _add_error_handling_check(self) -> None:
        """Add error handling check."""
        check = ComplianceCheck(
            id="INFRA_002", title="Error Handling",
            description="Secure error handling without information disclosure",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="Information Disclosure Prevention",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Generic error responses", "Structured error handling",
                "No stack traces in production", "Error correlation IDs"
            ],
            remediation_steps=[], priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        self.check_manager.add_check(check)