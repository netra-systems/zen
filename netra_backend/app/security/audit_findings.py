"""
Security audit findings and results management.
Handles finding data models, remediation, export, and dashboard functionality.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

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


class SecurityFindingsManager:
    """Manages security findings, remediation, and reporting."""
    
    def __init__(self):
        self.active_findings: Dict[str, SecurityFinding] = {}
        self.audit_history: List[SecurityAuditResult] = []
    
    def add_findings(self, findings: List[SecurityFinding]) -> None:
        """Add new findings to active tracking."""
        for finding in findings:
            self.active_findings[finding.id] = finding
        logger.info(f"Added {len(findings)} findings to tracking")
    
    def get_active_findings(self, severity: Optional[SecuritySeverity] = None) -> List[SecurityFinding]:
        """Get active security findings."""
        findings = self._filter_unremediated_findings()
        if severity:
            findings = self._filter_by_severity(findings, severity)
        return self._sort_findings_by_priority(findings)
    
    def _filter_unremediated_findings(self) -> List[SecurityFinding]:
        """Filter to only unremediated findings."""
        return [f for f in self.active_findings.values() if not f.remediated]
    
    def _filter_by_severity(self, findings: List[SecurityFinding], severity: SecuritySeverity) -> List[SecurityFinding]:
        """Filter findings by severity level."""
        return [f for f in findings if f.severity == severity]
    
    def _sort_findings_by_priority(self, findings: List[SecurityFinding]) -> List[SecurityFinding]:
        """Sort findings by severity and timestamp."""
        return sorted(findings, key=lambda x: (x.severity.value, x.timestamp), reverse=True)
    
    def remediate_finding(self, finding_id: str, remediation_notes: str) -> bool:
        """Mark a finding as remediated."""
        if finding_id not in self.active_findings:
            return False
        return self._mark_finding_remediated(finding_id, remediation_notes)
    
    def _mark_finding_remediated(self, finding_id: str, remediation_notes: str) -> bool:
        """Mark finding as remediated with notes."""
        finding = self.active_findings[finding_id]
        finding.remediated = True
        finding.remediation_date = datetime.now(timezone.utc)
        finding.evidence["remediation_notes"] = remediation_notes
        logger.info(f"Finding {finding_id} marked as remediated: {remediation_notes}")
        return True
    
    def store_audit_result(self, result: SecurityAuditResult) -> None:
        """Store completed audit result in history."""
        self.audit_history.append(result)
        logger.info(f"Stored audit result {result.audit_id}")
    
    def export_audit_report(self, audit_id: str, format: str = "json") -> str:
        """Export audit report in specified format."""
        audit_result = self._find_audit_result(audit_id)
        if format == "json":
            return self._export_json_report(audit_result)
        elif format == "summary":
            return self._export_summary_report(audit_result)
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _find_audit_result(self, audit_id: str) -> SecurityAuditResult:
        """Find audit result by ID."""
        for result in self.audit_history:
            if result.audit_id == audit_id:
                return result
        raise ValueError(f"Audit {audit_id} not found")
    
    def _export_json_report(self, audit_result: SecurityAuditResult) -> str:
        """Export audit result as JSON."""
        return json.dumps(asdict(audit_result), default=str, indent=2)
    
    def _export_summary_report(self, audit_result: SecurityAuditResult) -> str:
        """Generate a human-readable summary report."""
        return SecurityReportGenerator().generate_summary(audit_result)
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        active_findings = self.get_active_findings()
        return {
            "overview": self._generate_dashboard_overview(active_findings),
            "compliance_scores": self._get_latest_compliance_scores(),
            "recent_findings": self._get_recent_findings_data(active_findings),
            "audit_history": self._get_audit_history_summary()
        }
    
    def _generate_dashboard_overview(self, active_findings: List[SecurityFinding]) -> Dict[str, Any]:
        """Generate dashboard overview section."""
        return {
            "total_active_findings": len(active_findings),
            "critical_findings": len([f for f in active_findings if f.severity == SecuritySeverity.CRITICAL]),
            "high_findings": len([f for f in active_findings if f.severity == SecuritySeverity.HIGH]),
            "last_audit": self.audit_history[-1].start_time if self.audit_history else None,
            "next_audit": self.audit_history[-1].next_audit_date if self.audit_history else None
        }
    
    def _get_latest_compliance_scores(self) -> Dict[str, float]:
        """Get compliance scores from latest audit."""
        return self.audit_history[-1].compliance_scores if self.audit_history else {}
    
    def _get_recent_findings_data(self, active_findings: List[SecurityFinding]) -> List[Dict[str, Any]]:
        """Get recent findings as data dictionary."""
        return [asdict(f) for f in active_findings[:10]]
    
    def _get_audit_history_summary(self) -> List[Dict[str, Any]]:
        """Get audit history summary data."""
        return [
            {
                "audit_id": r.audit_id,
                "date": r.start_time,
                "findings_count": len(r.findings),
                "duration": r.duration_seconds
            }
            for r in self.audit_history[-10:]  # Last 10 audits
        ]


class SecurityReportGenerator:
    """Generates security reports in various formats."""
    
    def generate_summary(self, audit_result: SecurityAuditResult) -> str:
        """Generate a human-readable summary report."""
        lines = self._generate_header_section(audit_result)
        lines.extend(self._generate_summary_section(audit_result))
        lines.extend(self._generate_severity_breakdown(audit_result))
        lines.extend(self._generate_recommendations_section(audit_result))
        lines.extend(self._generate_footer_section(audit_result))
        return "\n".join(lines)
    
    def _generate_header_section(self, audit_result: SecurityAuditResult) -> List[str]:
        """Generate report header section."""
        return [
            f"Security Audit Report - {audit_result.audit_id}",
            f"Date: {audit_result.start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Duration: {audit_result.duration_seconds:.2f} seconds",
            ""
        ]
    
    def _generate_summary_section(self, audit_result: SecurityAuditResult) -> List[str]:
        """Generate report summary section."""
        return [
            "Summary:",
            f"  Total Findings: {len(audit_result.findings)}",
            f"  Overall Compliance Score: {audit_result.compliance_scores.get('overall', 0):.2%}",
            ""
        ]
    
    def _generate_severity_breakdown(self, audit_result: SecurityAuditResult) -> List[str]:
        """Generate severity breakdown section."""
        lines = ["Findings by Severity:"]
        severity_counts = self._count_findings_by_severity(audit_result.findings)
        for severity in SecuritySeverity:
            count = severity_counts.get(severity, 0)
            lines.append(f"  {severity.value.upper()}: {count}")
        lines.append("")
        return lines
    
    def _count_findings_by_severity(self, findings: List[SecurityFinding]) -> Dict[SecuritySeverity, int]:
        """Count findings by severity level."""
        severity_counts = {}
        for finding in findings:
            severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        return severity_counts
    
    def _generate_recommendations_section(self, audit_result: SecurityAuditResult) -> List[str]:
        """Generate recommendations section."""
        lines = ["Top Recommendations:"]
        for i, rec in enumerate(audit_result.recommendations[:5], 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")
        return lines
    
    def _generate_footer_section(self, audit_result: SecurityAuditResult) -> List[str]:
        """Generate report footer section."""
        return [
            f"Next Audit Scheduled: {audit_result.next_audit_date.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        ]


# Global instance
security_findings_manager = SecurityFindingsManager()