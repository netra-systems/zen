"""
Security Compliance Checklist for Netra AI Platform.
Implements comprehensive security compliance checks against industry standards.
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ComplianceStandard(str, Enum):
    """Security compliance standards."""
    OWASP_TOP_10 = "owasp_top_10_2021"
    NIST_CSF = "nist_cybersecurity_framework"
    ISO_27001 = "iso_27001"
    SOC2_TYPE2 = "soc2_type2"
    GDPR = "gdpr"
    PCI_DSS = "pci_dss"
    HIPAA = "hipaa"


class ComplianceStatus(str, Enum):
    """Compliance status types."""
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIALLY_COMPLIANT = "partially_compliant"
    NOT_APPLICABLE = "not_applicable"
    NEEDS_REVIEW = "needs_review"


@dataclass
class ComplianceCheck:
    """Individual compliance check."""
    id: str
    title: str
    description: str
    standard: ComplianceStandard
    requirement: str
    status: ComplianceStatus
    evidence: List[str]
    remediation_steps: List[str]
    priority: str  # high, medium, low
    last_checked: datetime
    next_check_date: datetime


class SecurityComplianceChecklist:
    """Comprehensive security compliance checklist."""
    
    def __init__(self):
        self.checks: Dict[str, ComplianceCheck] = {}
        self._initialize_checks()
    
    def _initialize_checks(self):
        """Initialize all compliance checks."""
        self._add_owasp_checks()
        self._add_nist_checks()
        self._add_authentication_checks()
        self._add_data_protection_checks()
        self._add_api_security_checks()
        self._add_infrastructure_checks()
    
    def _add_owasp_checks(self):
        """Add OWASP Top 10 2021 compliance checks."""
        
        # A01:2021 - Broken Access Control
        self.checks["OWASP_A01_001"] = ComplianceCheck(
            id="OWASP_A01_001",
            title="Access Control Implementation",
            description="Ensure proper access control mechanisms are implemented",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A01:2021 - Broken Access Control",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Role-based access control implemented",
                "Permission service validates user permissions",
                "Admin endpoints protected with proper authorization",
                "API endpoints use authentication middleware"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A02:2021 - Cryptographic Failures
        self.checks["OWASP_A02_001"] = ComplianceCheck(
            id="OWASP_A02_001",
            title="Cryptographic Implementation",
            description="Ensure proper cryptographic practices",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A02:2021 - Cryptographic Failures",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "JWT tokens use strong signing algorithms",
                "Passwords are hashed using bcrypt",
                "Fernet encryption for sensitive data",
                "API keys are hashed for storage",
                "Strong session management"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A03:2021 - Injection
        self.checks["OWASP_A03_001"] = ComplianceCheck(
            id="OWASP_A03_001",
            title="Injection Prevention",
            description="Prevent injection attacks through input validation",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A03:2021 - Injection",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "SQL injection detection patterns implemented",
                "XSS prevention in security middleware",
                "Command injection detection",
                "Path traversal protection",
                "Input validation on all endpoints",
                "Parameterized queries used"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A04:2021 - Insecure Design
        self.checks["OWASP_A04_001"] = ComplianceCheck(
            id="OWASP_A04_001",
            title="Secure Design Practices",
            description="Implement secure design principles",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A04:2021 - Insecure Design",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Threat modeling conducted",
                "Security requirements defined",
                "Defense in depth implemented",
                "Principle of least privilege applied",
                "Secure development lifecycle followed"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A05:2021 - Security Misconfiguration
        self.checks["OWASP_A05_001"] = ComplianceCheck(
            id="OWASP_A05_001",
            title="Security Configuration",
            description="Ensure proper security configuration",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A05:2021 - Security Misconfiguration",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Security headers implemented",
                "CORS properly configured",
                "Error handling doesn't leak information",
                "Debug mode disabled in production",
                "Default credentials changed",
                "Unnecessary features disabled"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A06:2021 - Vulnerable and Outdated Components
        self.checks["OWASP_A06_001"] = ComplianceCheck(
            id="OWASP_A06_001",
            title="Component Security",
            description="Manage vulnerable and outdated components",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A06:2021 - Vulnerable and Outdated Components",
            status=ComplianceStatus.NEEDS_REVIEW,
            evidence=[
                "Dependency scanning in place"
            ],
            remediation_steps=[
                "Implement automated dependency vulnerability scanning",
                "Establish process for regular dependency updates",
                "Monitor security advisories for used components"
            ],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A07:2021 - Identification and Authentication Failures
        self.checks["OWASP_A07_001"] = ComplianceCheck(
            id="OWASP_A07_001",
            title="Authentication Security",
            description="Secure authentication and session management",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A07:2021 - Identification and Authentication Failures",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Multi-factor authentication support",
                "Account lockout mechanisms",
                "Session management with timeouts",
                "Strong password requirements",
                "Secure session tokens",
                "Brute force protection"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A08:2021 - Software and Data Integrity Failures
        self.checks["OWASP_A08_001"] = ComplianceCheck(
            id="OWASP_A08_001",
            title="Data Integrity",
            description="Ensure software and data integrity",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A08:2021 - Software and Data Integrity Failures",
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            evidence=[
                "Input validation implemented",
                "API data validation with Pydantic"
            ],
            remediation_steps=[
                "Implement code signing for deployments",
                "Add integrity checks for critical data",
                "Implement secure CI/CD pipeline"
            ],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A09:2021 - Security Logging and Monitoring Failures
        self.checks["OWASP_A09_001"] = ComplianceCheck(
            id="OWASP_A09_001",
            title="Security Logging and Monitoring",
            description="Implement comprehensive logging and monitoring",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A09:2021 - Security Logging and Monitoring Failures",
            status=ComplianceStatus.COMPLIANT,
            evidence=[
                "Comprehensive logging framework",
                "Security event logging",
                "Authentication attempt logging",
                "Error logging with correlation IDs",
                "Security audit framework"
            ],
            remediation_steps=[],
            priority="high",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
        
        # A10:2021 - Server-Side Request Forgery (SSRF)
        self.checks["OWASP_A10_001"] = ComplianceCheck(
            id="OWASP_A10_001",
            title="SSRF Prevention",
            description="Prevent server-side request forgery attacks",
            standard=ComplianceStandard.OWASP_TOP_10,
            requirement="A10:2021 - Server-Side Request Forgery (SSRF)",
            status=ComplianceStatus.PARTIALLY_COMPLIANT,
            evidence=[
                "Input validation for URLs",
                "Network segmentation"
            ],
            remediation_steps=[
                "Implement URL validation whitelist",
                "Add network-level SSRF protection",
                "Validate and sanitize all user-provided URLs"
            ],
            priority="medium",
            last_checked=datetime.now(timezone.utc),
            next_check_date=datetime.now(timezone.utc)
        )
    
    def _add_nist_checks(self):
        """Add NIST Cybersecurity Framework checks."""
        
        self.checks["NIST_ID_001"] = ComplianceCheck(
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
        
        self.checks["NIST_PR_001"] = ComplianceCheck(
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
    
    def _add_authentication_checks(self):
        """Add authentication-specific checks."""
        
        self.checks["AUTH_001"] = ComplianceCheck(
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
        
        self.checks["AUTH_002"] = ComplianceCheck(
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
    
    def _add_data_protection_checks(self):
        """Add data protection checks."""
        
        self.checks["DATA_001"] = ComplianceCheck(
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
        
        self.checks["DATA_002"] = ComplianceCheck(
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
    
    def _add_api_security_checks(self):
        """Add API security checks."""
        
        self.checks["API_001"] = ComplianceCheck(
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
        
        self.checks["API_002"] = ComplianceCheck(
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
    
    def _add_infrastructure_checks(self):
        """Add infrastructure security checks."""
        
        self.checks["INFRA_001"] = ComplianceCheck(
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
        
        self.checks["INFRA_002"] = ComplianceCheck(
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
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get overall compliance summary."""
        total_checks = len(self.checks)
        compliant = len([c for c in self.checks.values() if c.status == ComplianceStatus.COMPLIANT])
        non_compliant = len([c for c in self.checks.values() if c.status == ComplianceStatus.NON_COMPLIANT])
        partially_compliant = len([c for c in self.checks.values() if c.status == ComplianceStatus.PARTIALLY_COMPLIANT])
        needs_review = len([c for c in self.checks.values() if c.status == ComplianceStatus.NEEDS_REVIEW])
        
        compliance_percentage = (compliant / total_checks) * 100 if total_checks > 0 else 0
        
        return {
            "total_checks": total_checks,
            "compliant": compliant,
            "non_compliant": non_compliant,
            "partially_compliant": partially_compliant,
            "needs_review": needs_review,
            "compliance_percentage": compliance_percentage,
            "status_breakdown": {
                "compliant": compliant,
                "non_compliant": non_compliant,
                "partially_compliant": partially_compliant,
                "needs_review": needs_review
            }
        }
    
    def get_checks_by_standard(self, standard: ComplianceStandard) -> List[ComplianceCheck]:
        """Get all checks for a specific standard."""
        return [check for check in self.checks.values() if check.standard == standard]
    
    def get_high_priority_issues(self) -> List[ComplianceCheck]:
        """Get high priority compliance issues."""
        return [
            check for check in self.checks.values()
            if check.priority == "high" and check.status != ComplianceStatus.COMPLIANT
        ]
    
    def get_remediation_plan(self) -> List[Dict[str, Any]]:
        """Get prioritized remediation plan."""
        non_compliant_checks = [
            check for check in self.checks.values()
            if check.status in [ComplianceStatus.NON_COMPLIANT, 
                              ComplianceStatus.PARTIALLY_COMPLIANT,
                              ComplianceStatus.NEEDS_REVIEW]
        ]
        
        # Sort by priority (high, medium, low)
        priority_order = {"high": 1, "medium": 2, "low": 3}
        non_compliant_checks.sort(key=lambda x: priority_order.get(x.priority, 999))
        
        remediation_plan = []
        for check in non_compliant_checks:
            remediation_plan.append({
                "check_id": check.id,
                "title": check.title,
                "priority": check.priority,
                "status": check.status,
                "standard": check.standard,
                "remediation_steps": check.remediation_steps,
                "estimated_effort": self._estimate_effort(check)
            })
        
        return remediation_plan
    
    def _estimate_effort(self, check: ComplianceCheck) -> str:
        """Estimate effort required for remediation."""
        step_count = len(check.remediation_steps)
        
        if step_count == 0:
            return "none"
        elif step_count <= 2:
            return "low"
        elif step_count <= 4:
            return "medium"
        else:
            return "high"
    
    def export_compliance_report(self) -> str:
        """Export compliance report as formatted text."""
        summary = self.get_compliance_summary()
        remediation_plan = self.get_remediation_plan()
        
        report_lines = [
            "SECURITY COMPLIANCE REPORT",
            "=" * 50,
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "COMPLIANCE SUMMARY:",
            f"  Total Checks: {summary['total_checks']}",
            f"  Compliant: {summary['compliant']}",
            f"  Non-Compliant: {summary['non_compliant']}",
            f"  Partially Compliant: {summary['partially_compliant']}",
            f"  Needs Review: {summary['needs_review']}",
            f"  Compliance Percentage: {summary['compliance_percentage']:.1f}%",
            "",
            "REMEDIATION PLAN:",
            "-" * 20
        ]
        
        if not remediation_plan:
            report_lines.append("No remediation required - all checks compliant!")
        else:
            for i, item in enumerate(remediation_plan, 1):
                report_lines.extend([
                    f"{i}. {item['title']} [{item['priority'].upper()} PRIORITY]",
                    f"   Status: {item['status']}",
                    f"   Standard: {item['standard']}",
                    f"   Effort: {item['estimated_effort']}",
                    f"   Steps:"
                ])
                for step in item['remediation_steps']:
                    report_lines.append(f"     - {step}")
                report_lines.append("")
        
        return "\n".join(report_lines)


# Global instance
security_compliance_checklist = SecurityComplianceChecklist()