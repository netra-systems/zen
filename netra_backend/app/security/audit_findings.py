"""
Security Audit Findings - Core data structures for security audit results.

This module provides the fundamental data structures used across the security audit framework
to represent findings, severity levels, categories, and audit results.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SecuritySeverity(Enum):
    """Security finding severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class SecurityCategory(Enum):
    """Security audit categories."""
    AUTHENTICATION = "AUTHENTICATION"
    AUTHORIZATION = "AUTHORIZATION"
    DATA_PROTECTION = "DATA_PROTECTION"
    CONFIGURATION = "CONFIGURATION"
    API_SECURITY = "API_SECURITY"
    SESSION_MANAGEMENT = "SESSION_MANAGEMENT"
    INPUT_VALIDATION = "INPUT_VALIDATION"
    LOGGING_MONITORING = "LOGGING_MONITORING"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    COMPLIANCE = "COMPLIANCE"


@dataclass
class SecurityFinding:
    """Represents a single security audit finding."""

    category: SecurityCategory
    severity: SecuritySeverity
    title: str
    description: str
    recommendation: str

    # Optional fields
    evidence: Optional[Dict[str, Any]] = None
    remediation_effort: Optional[str] = None
    compliance_references: Optional[List[str]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary representation."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "evidence": self.evidence,
            "remediation_effort": self.remediation_effort,
            "compliance_references": self.compliance_references,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class SecurityAuditResult:
    """Contains the complete results of a security audit."""

    audit_id: str
    audit_type: str
    timestamp: datetime
    findings: List[SecurityFinding]

    # Summary statistics
    total_findings: int = field(init=False)
    critical_count: int = field(init=False)
    high_count: int = field(init=False)
    medium_count: int = field(init=False)
    low_count: int = field(init=False)

    def __post_init__(self):
        """Calculate summary statistics after initialization."""
        self.total_findings = len(self.findings)
        self.critical_count = sum(1 for f in self.findings if f.severity == SecuritySeverity.CRITICAL)
        self.high_count = sum(1 for f in self.findings if f.severity == SecuritySeverity.HIGH)
        self.medium_count = sum(1 for f in self.findings if f.severity == SecuritySeverity.MEDIUM)
        self.low_count = sum(1 for f in self.findings if f.severity == SecuritySeverity.LOW)

    def get_findings_by_severity(self, severity: SecuritySeverity) -> List[SecurityFinding]:
        """Get all findings of a specific severity level."""
        return [f for f in self.findings if f.severity == severity]

    def get_findings_by_category(self, category: SecurityCategory) -> List[SecurityFinding]:
        """Get all findings of a specific category."""
        return [f for f in self.findings if f.category == category]

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit result to dictionary representation."""
        return {
            "audit_id": self.audit_id,
            "audit_type": self.audit_type,
            "timestamp": self.timestamp.isoformat(),
            "total_findings": self.total_findings,
            "severity_counts": {
                "critical": self.critical_count,
                "high": self.high_count,
                "medium": self.medium_count,
                "low": self.low_count
            },
            "findings": [f.to_dict() for f in self.findings]
        }


class SecurityFindingsManager:
    """Manages security audit findings and provides aggregation capabilities."""

    def __init__(self):
        self._findings_history: List[SecurityAuditResult] = []

    def add_audit_result(self, result: SecurityAuditResult) -> None:
        """Add an audit result to the history."""
        self._findings_history.append(result)
        logger.info(f"Added audit result {result.audit_id} with {result.total_findings} findings")

    def get_latest_audit(self, audit_type: Optional[str] = None) -> Optional[SecurityAuditResult]:
        """Get the most recent audit result, optionally filtered by type."""
        if not self._findings_history:
            return None

        if audit_type:
            filtered = [r for r in self._findings_history if r.audit_type == audit_type]
            return max(filtered, key=lambda r: r.timestamp) if filtered else None

        return max(self._findings_history, key=lambda r: r.timestamp)

    def get_all_findings(self) -> List[SecurityFinding]:
        """Get all findings from all audits."""
        all_findings = []
        for result in self._findings_history:
            all_findings.extend(result.findings)
        return all_findings

    def get_critical_findings(self) -> List[SecurityFinding]:
        """Get all critical severity findings."""
        return [f for f in self.get_all_findings() if f.severity == SecuritySeverity.CRITICAL]

    def clear_history(self) -> None:
        """Clear all audit history (use with caution)."""
        self._findings_history.clear()
        logger.warning("Security audit history cleared")


# Global instance for use across the security framework
security_findings_manager = SecurityFindingsManager()