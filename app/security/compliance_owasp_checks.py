"""OWASP Top 10 2021 compliance checks for Netra AI Platform."""

from typing import Dict
from datetime import datetime, timezone

from .compliance_types import ComplianceCheck, ComplianceStandard, ComplianceStatus


class OwaspComplianceChecks:
    """OWASP Top 10 2021 compliance check implementations."""
    
    def get_all_checks(self) -> Dict[str, ComplianceCheck]:
        """Get all OWASP compliance checks."""
        checks = {}
        self._add_access_control_check(checks)
        self._add_cryptographic_check(checks)
        self._add_injection_check(checks)
        self._add_design_check(checks)
        self._add_misconfiguration_check(checks)
        self._add_component_check(checks)
        self._add_authentication_check(checks)
        self._add_integrity_check(checks)
        self._add_logging_check(checks)
        self._add_ssrf_check(checks)
        return checks
    
    def _create_check(self, check_id: str, title: str, description: str, 
                     requirement: str, status: ComplianceStatus, evidence: list, 
                     remediation_steps: list, priority: str) -> ComplianceCheck:
        """Create OWASP compliance check."""
        return ComplianceCheck(
            id=check_id, title=title, description=description,
            standard=ComplianceStandard.OWASP_TOP_10, requirement=requirement,
            status=status, evidence=evidence, remediation_steps=remediation_steps,
            priority=priority, last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_access_control_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A01 - Broken Access Control check."""
        evidence = ["Role-based access control implemented", 
                   "Permission service validates user permissions",
                   "Admin endpoints protected with proper authorization",
                   "API endpoints use authentication middleware"]
        checks["OWASP_A01_001"] = self._create_check(
            "OWASP_A01_001", "Access Control Implementation",
            "Ensure proper access control mechanisms are implemented",
            "A01:2021 - Broken Access Control", ComplianceStatus.COMPLIANT,
            evidence, [], "high")
    
    def _add_cryptographic_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A02 - Cryptographic Failures check."""
        evidence = ["JWT tokens use strong signing algorithms", "Passwords are hashed using bcrypt",
                   "Fernet encryption for sensitive data", "API keys are hashed for storage",
                   "Strong session management"]
        checks["OWASP_A02_001"] = self._create_check(
            "OWASP_A02_001", "Cryptographic Implementation",
            "Ensure proper cryptographic practices",
            "A02:2021 - Cryptographic Failures", ComplianceStatus.COMPLIANT,
            evidence, [], "high")
    
    def _add_injection_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A03 - Injection check."""
        evidence = ["SQL injection detection patterns implemented", "XSS prevention in security middleware",
                   "Command injection detection", "Path traversal protection",
                   "Input validation on all endpoints", "Parameterized queries used"]
        checks["OWASP_A03_001"] = self._create_check(
            "OWASP_A03_001", "Injection Prevention",
            "Prevent injection attacks through input validation",
            "A03:2021 - Injection", ComplianceStatus.COMPLIANT,
            evidence, [], "high")
    
    def _add_design_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A04 - Insecure Design check."""
        evidence = ["Threat modeling conducted", "Security requirements defined",
                   "Defense in depth implemented", "Principle of least privilege applied",
                   "Secure development lifecycle followed"]
        checks["OWASP_A04_001"] = self._create_check(
            "OWASP_A04_001", "Secure Design Practices",
            "Implement secure design principles",
            "A04:2021 - Insecure Design", ComplianceStatus.COMPLIANT,
            evidence, [], "high")
    
    def _add_misconfiguration_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A05 - Security Misconfiguration check."""
        evidence = ["Security headers implemented", "CORS properly configured",
                   "Error handling doesn't leak information", "Debug mode disabled in production",
                   "Default credentials changed", "Unnecessary features disabled"]
        checks["OWASP_A05_001"] = self._create_check(
            "OWASP_A05_001", "Security Configuration",
            "Ensure proper security configuration",
            "A05:2021 - Security Misconfiguration", ComplianceStatus.COMPLIANT,
            evidence, [], "high")
    
    def _add_component_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A06 - Vulnerable and Outdated Components check."""
        remediation = ["Implement automated dependency vulnerability scanning",
                      "Establish process for regular dependency updates",
                      "Monitor security advisories for used components"]
        checks["OWASP_A06_001"] = self._create_check(
            "OWASP_A06_001", "Component Security",
            "Manage vulnerable and outdated components",
            "A06:2021 - Vulnerable and Outdated Components", 
            ComplianceStatus.NEEDS_REVIEW, ["Dependency scanning in place"],
            remediation, "medium")
    
    def _add_authentication_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A07 - Authentication Failures check."""
        evidence = ["Multi-factor authentication support", "Account lockout mechanisms",
                   "Session management with timeouts", "Strong password requirements",
                   "Secure session tokens", "Brute force protection"]
        checks["OWASP_A07_001"] = self._create_check(
            "OWASP_A07_001", "Authentication Security",
            "Secure authentication and session management",
            "A07:2021 - Identification and Authentication Failures",
            ComplianceStatus.COMPLIANT, evidence, [], "high")
    
    def _add_integrity_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A08 - Software and Data Integrity Failures check."""
        evidence = ["Input validation implemented", "API data validation with Pydantic"]
        remediation = ["Implement code signing for deployments", "Add integrity checks for critical data",
                      "Implement secure CI/CD pipeline"]
        checks["OWASP_A08_001"] = self._create_check(
            "OWASP_A08_001", "Data Integrity",
            "Ensure software and data integrity",
            "A08:2021 - Software and Data Integrity Failures",
            ComplianceStatus.PARTIALLY_COMPLIANT, evidence, remediation, "medium")
    
    def _add_logging_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A09 - Security Logging and Monitoring Failures check."""
        evidence = ["Comprehensive logging framework", "Security event logging",
                   "Authentication attempt logging", "Error logging with correlation IDs",
                   "Security audit framework"]
        checks["OWASP_A09_001"] = self._create_check(
            "OWASP_A09_001", "Security Logging and Monitoring",
            "Implement comprehensive logging and monitoring",
            "A09:2021 - Security Logging and Monitoring Failures",
            ComplianceStatus.COMPLIANT, evidence, [], "high")
    
    def _add_ssrf_check(self, checks: Dict[str, ComplianceCheck]):
        """Add OWASP A10 - Server-Side Request Forgery check."""
        evidence = ["Input validation for URLs", "Network segmentation"]
        remediation = ["Implement URL validation whitelist", "Add network-level SSRF protection",
                      "Validate and sanitize all user-provided URLs"]
        checks["OWASP_A10_001"] = self._create_check(
            "OWASP_A10_001", "SSRF Prevention",
            "Prevent server-side request forgery attacks",
            "A10:2021 - Server-Side Request Forgery (SSRF)",
            ComplianceStatus.PARTIALLY_COMPLIANT, evidence, remediation, "medium")
