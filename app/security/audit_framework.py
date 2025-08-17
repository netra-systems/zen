"""
Security Audit Framework for comprehensive security assessments.
Implements automated security checks, vulnerability scanning, and compliance reporting.
"""

import asyncio
import time
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from app.logging_config import central_logger
from app.auth.enhanced_auth_security import enhanced_auth_security
from app.auth.api_key_manager import api_key_manager
from app.middleware.security_middleware import global_rate_limiter
from app.core.exceptions_auth import NetraSecurityException

logger = central_logger.get_logger(__name__)


class SecuritySeverity(str, Enum):
    """Security issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SecurityCategory(str, Enum):
    """Security audit categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INPUT_VALIDATION = "input_validation"
    SESSION_MANAGEMENT = "session_management"
    CRYPTOGRAPHY = "cryptography"
    API_SECURITY = "api_security"
    CONFIGURATION = "configuration"
    LOGGING_MONITORING = "logging_monitoring"
    INFRASTRUCTURE = "infrastructure"
    DATA_PROTECTION = "data_protection"


@dataclass
class SecurityFinding:
    """Security audit finding."""
    id: str
    title: str
    description: str
    severity: SecuritySeverity
    category: SecurityCategory
    cwe_id: Optional[str]
    owasp_category: Optional[str]
    recommendation: str
    evidence: Dict[str, Any]
    timestamp: datetime
    remediated: bool = False
    remediation_date: Optional[datetime] = None


@dataclass
class SecurityAuditResult:
    """Complete security audit result."""
    audit_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    findings: List[SecurityFinding]
    metrics: Dict[str, Any]
    compliance_scores: Dict[str, float]
    recommendations: List[str]
    next_audit_date: datetime


class SecurityAuditor(ABC):
    """Base class for security auditors."""
    
    @abstractmethod
    async def audit(self) -> List[SecurityFinding]:
        """Perform security audit and return findings."""
        pass
    
    @abstractmethod
    def get_category(self) -> SecurityCategory:
        """Get the security category this auditor covers."""
        pass


class AuthenticationAuditor(SecurityAuditor):
    """Auditor for authentication security."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit authentication security."""
        findings = []
        
        # Check authentication configuration
        auth_status = enhanced_auth_security.get_security_status()
        
        # Check for weak authentication settings
        if enhanced_auth_security.max_failed_attempts > 5:
            findings.append(SecurityFinding(
                id="AUTH001",
                title="High Failed Login Attempt Threshold",
                description=f"Max failed attempts set to {enhanced_auth_security.max_failed_attempts}, recommended <= 5",
                severity=SecuritySeverity.MEDIUM,
                category=SecurityCategory.AUTHENTICATION,
                cwe_id="CWE-307",
                owasp_category="A02:2021 - Cryptographic Failures",
                recommendation="Reduce max_failed_attempts to 5 or lower",
                evidence={"current_threshold": enhanced_auth_security.max_failed_attempts},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check lockout duration
        if enhanced_auth_security.lockout_duration.total_seconds() < 300:  # 5 minutes
            findings.append(SecurityFinding(
                id="AUTH002",
                title="Short Account Lockout Duration",
                description=f"Lockout duration is {enhanced_auth_security.lockout_duration.total_seconds()} seconds, recommended >= 300",
                severity=SecuritySeverity.LOW,
                category=SecurityCategory.AUTHENTICATION,
                cwe_id="CWE-307",
                owasp_category="A02:2021 - Cryptographic Failures",
                recommendation="Increase lockout duration to at least 5 minutes",
                evidence={"current_duration": enhanced_auth_security.lockout_duration.total_seconds()},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check for excessive failed login attempts
        if auth_status["metrics"]["failed_logins"] > 100:
            findings.append(SecurityFinding(
                id="AUTH003",
                title="High Number of Failed Login Attempts",
                description=f"Detected {auth_status['metrics']['failed_logins']} failed login attempts",
                severity=SecuritySeverity.HIGH,
                category=SecurityCategory.AUTHENTICATION,
                cwe_id="CWE-307",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                recommendation="Investigate potential brute force attacks and implement additional monitoring",
                evidence=auth_status["metrics"],
                timestamp=datetime.now(timezone.utc)
            ))
        
        return findings
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.AUTHENTICATION


class ApiSecurityAuditor(SecurityAuditor):
    """Auditor for API security."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit API security."""
        findings = []
        
        # Check API key security
        api_metrics = api_key_manager.get_security_metrics()
        
        # Check for expired keys that haven't been cleaned up
        if api_metrics["expired_keys"] > 0:
            findings.append(SecurityFinding(
                id="API001",
                title="Expired API Keys Not Cleaned Up",
                description=f"Found {api_metrics['expired_keys']} expired API keys",
                severity=SecuritySeverity.MEDIUM,
                category=SecurityCategory.API_SECURITY,
                cwe_id="CWE-613",
                owasp_category="A02:2021 - Cryptographic Failures",
                recommendation="Implement automated cleanup of expired API keys",
                evidence=api_metrics,
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check for keys needing rotation
        if api_metrics["rotation_needed"] > 0:
            findings.append(SecurityFinding(
                id="API002",
                title="API Keys Need Rotation",
                description=f"{api_metrics['rotation_needed']} API keys are approaching expiration",
                severity=SecuritySeverity.LOW,
                category=SecurityCategory.API_SECURITY,
                cwe_id="CWE-344",
                owasp_category="A02:2021 - Cryptographic Failures",
                recommendation="Rotate API keys before they expire",
                evidence={"rotation_candidates": api_key_manager.get_rotation_candidates()},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check for users with too many API keys
        if api_metrics["average_keys_per_user"] > 5:
            findings.append(SecurityFinding(
                id="API003",
                title="High Average API Keys Per User",
                description=f"Average of {api_metrics['average_keys_per_user']:.1f} keys per user",
                severity=SecuritySeverity.LOW,
                category=SecurityCategory.API_SECURITY,
                cwe_id="CWE-250",
                owasp_category="A01:2021 - Broken Access Control",
                recommendation="Review API key usage patterns and implement key limits",
                evidence=api_metrics,
                timestamp=datetime.now(timezone.utc)
            ))
        
        return findings
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.API_SECURITY


class SessionManagementAuditor(SecurityAuditor):
    """Auditor for session management security."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit session management security."""
        findings = []
        
        auth_status = enhanced_auth_security.get_security_status()
        
        # Check for too many active sessions
        if auth_status["active_sessions"] > 1000:
            findings.append(SecurityFinding(
                id="SESS001",
                title="High Number of Active Sessions",
                description=f"Found {auth_status['active_sessions']} active sessions",
                severity=SecuritySeverity.MEDIUM,
                category=SecurityCategory.SESSION_MANAGEMENT,
                cwe_id="CWE-613",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                recommendation="Implement session cleanup and monitor for unusual session patterns",
                evidence={"active_sessions": auth_status["active_sessions"]},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check session timeout configuration
        if enhanced_auth_security.session_timeout.total_seconds() > 28800:  # 8 hours
            findings.append(SecurityFinding(
                id="SESS002",
                title="Long Session Timeout",
                description=f"Session timeout is {enhanced_auth_security.session_timeout.total_seconds()} seconds",
                severity=SecuritySeverity.LOW,
                category=SecurityCategory.SESSION_MANAGEMENT,
                cwe_id="CWE-613",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                recommendation="Consider reducing session timeout for better security",
                evidence={"timeout_seconds": enhanced_auth_security.session_timeout.total_seconds()},
                timestamp=datetime.now(timezone.utc)
            ))
        
        return findings
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.SESSION_MANAGEMENT


class ConfigurationAuditor(SecurityAuditor):
    """Auditor for security configuration."""
    
    async def audit(self) -> List[SecurityFinding]:
        """Audit security configuration."""
        findings = []
        
        # Check environment-specific settings
        from app.config import settings
        
        # Check if running in debug mode in non-development environments
        if hasattr(settings, 'debug') and settings.debug and settings.environment != "development":
            findings.append(SecurityFinding(
                id="CONF001",
                title="Debug Mode Enabled in Non-Development Environment",
                description=f"Debug mode is enabled in {settings.environment} environment",
                severity=SecuritySeverity.HIGH,
                category=SecurityCategory.CONFIGURATION,
                cwe_id="CWE-489",
                owasp_category="A05:2021 - Security Misconfiguration",
                recommendation="Disable debug mode in production and staging environments",
                evidence={"environment": settings.environment, "debug": settings.debug},
                timestamp=datetime.now(timezone.utc)
            ))
        
        # Check for weak JWT secret
        if hasattr(settings, 'jwt_secret_key') and len(settings.jwt_secret_key) < 32:
            findings.append(SecurityFinding(
                id="CONF002",
                title="Weak JWT Secret Key",
                description=f"JWT secret key length is {len(settings.jwt_secret_key)} characters",
                severity=SecuritySeverity.CRITICAL,
                category=SecurityCategory.CRYPTOGRAPHY,
                cwe_id="CWE-326",
                owasp_category="A02:2021 - Cryptographic Failures",
                recommendation="Use a JWT secret key of at least 32 characters",
                evidence={"key_length": len(settings.jwt_secret_key)},
                timestamp=datetime.now(timezone.utc)
            ))
        
        return findings
    
    def get_category(self) -> SecurityCategory:
        return SecurityCategory.CONFIGURATION


class SecurityAuditFramework:
    """Main security audit framework."""
    
    def __init__(self):
        self.auditors: List[SecurityAuditor] = [
            AuthenticationAuditor(),
            ApiSecurityAuditor(),
            SessionManagementAuditor(),
            ConfigurationAuditor()
        ]
        self.audit_history: List[SecurityAuditResult] = []
        self.active_findings: Dict[str, SecurityFinding] = {}
        
    async def run_audit(self, categories: Optional[List[SecurityCategory]] = None) -> SecurityAuditResult:
        """Run comprehensive security audit."""
        audit_id, start_time = self._initialize_audit()
        all_findings, audit_metrics = await self._execute_auditors(categories)
        end_time, duration = self._calculate_timing(start_time)
        compliance_scores = self._calculate_compliance_scores(all_findings)
        recommendations = self._generate_recommendations(all_findings)
        result = self._create_audit_result(audit_id, start_time, end_time, duration, all_findings, audit_metrics, compliance_scores, recommendations)
        self._finalize_audit(result, all_findings, audit_id, duration)
        return result
    
    def _initialize_audit(self) -> Tuple[str, datetime]:
        """Initialize audit with ID and start time."""
        audit_id = f"audit_{int(time.time())}"
        start_time = datetime.now(timezone.utc)
        logger.info(f"Starting security audit {audit_id}")
        return audit_id, start_time
    
    async def _execute_auditors(self, categories: Optional[List[SecurityCategory]]) -> Tuple[List[SecurityFinding], Dict[str, Any]]:
        """Execute all auditors and collect findings."""
        all_findings = []
        audit_metrics = {}
        for auditor in self.auditors:
            if categories is None or auditor.get_category() in categories:
                findings, metrics = await self._run_single_auditor(auditor)
                all_findings.extend(findings)
                audit_metrics[auditor.get_category().value] = metrics
        return all_findings, audit_metrics
    
    async def _run_single_auditor(self, auditor: SecurityAuditor) -> Tuple[List[SecurityFinding], Dict[str, Any]]:
        """Run a single auditor and return findings with metrics."""
        try:
            auditor_start = time.time()
            findings = await auditor.audit()
            auditor_duration = time.time() - auditor_start
            metrics = {"findings_count": len(findings), "duration_seconds": auditor_duration}
            logger.info(f"Auditor {auditor.__class__.__name__} found {len(findings)} issues")
            return findings, metrics
        except Exception as e:
            logger.error(f"Error in auditor {auditor.__class__.__name__}: {e}")
            return [], {"error": str(e), "findings_count": 0}
    
    def _calculate_timing(self, start_time: datetime) -> Tuple[datetime, float]:
        """Calculate end time and duration."""
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        return end_time, duration
    
    def _create_audit_result(self, audit_id: str, start_time: datetime, end_time: datetime, 
                           duration: float, all_findings: List[SecurityFinding], 
                           audit_metrics: Dict[str, Any], compliance_scores: Dict[str, float], 
                           recommendations: List[str]) -> SecurityAuditResult:
        """Create the audit result object."""
        return SecurityAuditResult(
            audit_id=audit_id, start_time=start_time, end_time=end_time,
            duration_seconds=duration, findings=all_findings, metrics=audit_metrics,
            compliance_scores=compliance_scores, recommendations=recommendations,
            next_audit_date=datetime.now(timezone.utc) + timedelta(days=7)
        )
    
    def _finalize_audit(self, result: SecurityAuditResult, all_findings: List[SecurityFinding], 
                       audit_id: str, duration: float) -> None:
        """Finalize audit by storing results and updating active findings."""
        self.audit_history.append(result)
        for finding in all_findings:
            self.active_findings[finding.id] = finding
        logger.info(f"Security audit {audit_id} completed with {len(all_findings)} findings in {duration:.2f}s")
    
    def _calculate_compliance_scores(self, findings: List[SecurityFinding]) -> Dict[str, float]:
        """Calculate compliance scores based on findings."""
        scores = {}
        
        # Group findings by category
        category_findings = {}
        for finding in findings:
            category = finding.category.value
            if category not in category_findings:
                category_findings[category] = []
            category_findings[category].append(finding)
        
        # Calculate scores for each category
        for category, cat_findings in category_findings.items():
            severity_weights = {
                SecuritySeverity.CRITICAL: 10,
                SecuritySeverity.HIGH: 5,
                SecuritySeverity.MEDIUM: 2,
                SecuritySeverity.LOW: 1,
                SecuritySeverity.INFO: 0
            }
            
            total_weight = sum(severity_weights[f.severity] for f in cat_findings)
            max_possible = len(cat_findings) * severity_weights[SecuritySeverity.CRITICAL]
            
            if max_possible == 0:
                scores[category] = 1.0
            else:
                scores[category] = max(0.0, 1.0 - (total_weight / max_possible))
        
        # Overall compliance score
        if scores:
            scores["overall"] = sum(scores.values()) / len(scores)
        else:
            scores["overall"] = 1.0
        
        return scores
    
    def _generate_recommendations(self, findings: List[SecurityFinding]) -> List[str]:
        """Generate high-level recommendations."""
        recommendations = []
        
        # Count findings by severity
        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        
        # Generate recommendations based on findings
        if severity_counts.get(SecuritySeverity.CRITICAL, 0) > 0:
            recommendations.append("Immediately address all CRITICAL security findings before production deployment")
        
        if severity_counts.get(SecuritySeverity.HIGH, 0) > 2:
            recommendations.append("Implement a security remediation plan for HIGH severity findings")
        
        if len([f for f in findings if f.category == SecurityCategory.AUTHENTICATION]) > 0:
            recommendations.append("Review and strengthen authentication mechanisms")
        
        if len([f for f in findings if f.category == SecurityCategory.API_SECURITY]) > 0:
            recommendations.append("Implement comprehensive API security controls")
        
        recommendations.append("Schedule regular security audits (weekly recommended)")
        recommendations.append("Implement automated security monitoring and alerting")
        
        return recommendations
    
    def get_active_findings(self, severity: Optional[SecuritySeverity] = None) -> List[SecurityFinding]:
        """Get active security findings."""
        findings = [f for f in self.active_findings.values() if not f.remediated]
        
        if severity:
            findings = [f for f in findings if f.severity == severity]
        
        return sorted(findings, key=lambda x: (x.severity.value, x.timestamp), reverse=True)
    
    def remediate_finding(self, finding_id: str, remediation_notes: str) -> bool:
        """Mark a finding as remediated."""
        if finding_id in self.active_findings:
            finding = self.active_findings[finding_id]
            finding.remediated = True
            finding.remediation_date = datetime.now(timezone.utc)
            finding.evidence["remediation_notes"] = remediation_notes
            
            logger.info(f"Finding {finding_id} marked as remediated: {remediation_notes}")
            return True
        
        return False
    
    def export_audit_report(self, audit_id: str, format: str = "json") -> str:
        """Export audit report in specified format."""
        # Find audit result
        audit_result = None
        for result in self.audit_history:
            if result.audit_id == audit_id:
                audit_result = result
                break
        
        if not audit_result:
            raise ValueError(f"Audit {audit_id} not found")
        
        if format == "json":
            return json.dumps(asdict(audit_result), default=str, indent=2)
        elif format == "summary":
            return self._generate_summary_report(audit_result)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _generate_summary_report(self, audit_result: SecurityAuditResult) -> str:
        """Generate a human-readable summary report."""
        lines = [
            f"Security Audit Report - {audit_result.audit_id}",
            f"Date: {audit_result.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Duration: {audit_result.duration_seconds:.2f} seconds",
            f"",
            f"Summary:",
            f"  Total Findings: {len(audit_result.findings)}",
            f"  Overall Compliance Score: {audit_result.compliance_scores.get('overall', 0):.2%}",
            f"",
            f"Findings by Severity:",
        ]
        
        severity_counts = {}
        for finding in audit_result.findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        
        for severity in SecuritySeverity:
            count = severity_counts.get(severity, 0)
            lines.append(f"  {severity.value.upper()}: {count}")
        
        lines.extend([
            f"",
            f"Top Recommendations:",
        ])
        
        for i, rec in enumerate(audit_result.recommendations[:5], 1):
            lines.append(f"  {i}. {rec}")
        
        lines.extend([
            f"",
            f"Next Audit Scheduled: {audit_result.next_audit_date.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ])
        
        return "\n".join(lines)
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        active_findings = self.get_active_findings()
        
        return {
            "overview": {
                "total_active_findings": len(active_findings),
                "critical_findings": len([f for f in active_findings if f.severity == SecuritySeverity.CRITICAL]),
                "high_findings": len([f for f in active_findings if f.severity == SecuritySeverity.HIGH]),
                "last_audit": self.audit_history[-1].start_time if self.audit_history else None,
                "next_audit": self.audit_history[-1].next_audit_date if self.audit_history else None
            },
            "compliance_scores": self.audit_history[-1].compliance_scores if self.audit_history else {},
            "recent_findings": [asdict(f) for f in active_findings[:10]],
            "audit_history": [
                {
                    "audit_id": r.audit_id,
                    "date": r.start_time,
                    "findings_count": len(r.findings),
                    "duration": r.duration_seconds
                }
                for r in self.audit_history[-10:]  # Last 10 audits
            ]
        }


# Global instance
security_audit_framework = SecurityAuditFramework()