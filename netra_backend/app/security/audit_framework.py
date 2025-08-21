"""
Security Audit Framework for comprehensive security assessments.
Core framework orchestrating security audits and coordinating with specialized modules.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple

from netra_backend.app.logging_config import central_logger
from netra_backend.app.security.audit_findings import (
    SecurityFinding, SecurityAuditResult, SecuritySeverity, SecurityCategory,
    security_findings_manager
)
from netra_backend.app.security.audit_compliance import (
    AuthenticationAuditor, ApiSecurityAuditor, SessionManagementAuditor,
    ConfigurationAuditor, SecurityAuditor
)
from netra_backend.app.security.audit_scoring import (
    compliance_score_calculator, security_recommendation_engine
)

logger = central_logger.get_logger(__name__)


class SecurityAuditFramework:
    """Main security audit framework."""
    
    def __init__(self):
        self.auditors: List[SecurityAuditor] = [
            AuthenticationAuditor(),
            ApiSecurityAuditor(),
            SessionManagementAuditor(),
            ConfigurationAuditor()
        ]
        
    async def run_audit(self, categories: Optional[List[SecurityCategory]] = None) -> SecurityAuditResult:
        """Run comprehensive security audit."""
        audit_id, start_time = self._initialize_audit()
        all_findings, audit_metrics = await self._execute_auditors(categories)
        end_time, duration = self._calculate_timing(start_time)
        compliance_scores = self._calculate_compliance_scores(all_findings)
        recommendations = self._generate_recommendations(all_findings)
        result = self._create_audit_result(audit_id, start_time, end_time, duration, all_findings, audit_metrics, compliance_scores, recommendations)
        self._finalize_audit(result, all_findings)
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
            if self._should_run_auditor(auditor, categories):
                findings, metrics = await self._run_single_auditor(auditor)
                all_findings.extend(findings)
                audit_metrics[auditor.get_category().value] = metrics
        return all_findings, audit_metrics
    
    def _should_run_auditor(self, auditor: SecurityAuditor, categories: Optional[List[SecurityCategory]]) -> bool:
        """Check if auditor should be run based on category filter."""
        return categories is None or auditor.get_category() in categories
    
    async def _run_single_auditor(self, auditor: SecurityAuditor) -> Tuple[List[SecurityFinding], Dict[str, Any]]:
        """Run a single auditor and return findings with metrics."""
        try:
            auditor_start = time.time()
            findings = await auditor.audit()
            auditor_duration = time.time() - auditor_start
            metrics = self._create_auditor_metrics(findings, auditor_duration)
            logger.info(f"Auditor {auditor.__class__.__name__} found {len(findings)} issues")
            return findings, metrics
        except Exception as e:
            logger.error(f"Error in auditor {auditor.__class__.__name__}: {e}")
            return [], {"error": str(e), "findings_count": 0}
    
    def _create_auditor_metrics(self, findings: List[SecurityFinding], duration: float) -> Dict[str, Any]:
        """Create metrics for auditor execution."""
        return {"findings_count": len(findings), "duration_seconds": duration}
    
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
            next_audit_date=self._calculate_next_audit_date()
        )
    
    def _calculate_next_audit_date(self) -> datetime:
        """Calculate next recommended audit date."""
        return datetime.now(timezone.utc) + timedelta(days=7)
    
    def _finalize_audit(self, result: SecurityAuditResult, all_findings: List[SecurityFinding]) -> None:
        """Finalize audit by storing results and updating active findings."""
        security_findings_manager.store_audit_result(result)
        security_findings_manager.add_findings(all_findings)
        logger.info(f"Security audit {result.audit_id} completed with {len(all_findings)} findings in {result.duration_seconds:.2f}s")
    
    def _calculate_compliance_scores(self, findings: List[SecurityFinding]) -> Dict[str, float]:
        """Calculate compliance scores based on findings."""
        return compliance_score_calculator.calculate_scores(findings)
    
    def _generate_recommendations(self, findings: List[SecurityFinding]) -> List[str]:
        """Generate high-level recommendations."""
        return security_recommendation_engine.generate_recommendations(findings)
    
    def get_active_findings(self, severity: Optional[SecuritySeverity] = None) -> List[SecurityFinding]:
        """Get active security findings."""
        return security_findings_manager.get_active_findings(severity)
    
    def remediate_finding(self, finding_id: str, remediation_notes: str) -> bool:
        """Mark a finding as remediated."""
        return security_findings_manager.remediate_finding(finding_id, remediation_notes)
    
    def export_audit_report(self, audit_id: str, format: str = "json") -> str:
        """Export audit report in specified format."""
        return security_findings_manager.export_audit_report(audit_id, format)
    
    def get_security_dashboard(self) -> Dict[str, Any]:
        """Get security dashboard data."""
        return security_findings_manager.get_security_dashboard()
    
    def add_custom_auditor(self, auditor: SecurityAuditor) -> None:
        """Add a custom auditor to the framework."""
        self.auditors.append(auditor)
        logger.info(f"Added custom auditor: {auditor.__class__.__name__}")
    
    def remove_auditor(self, category: SecurityCategory) -> bool:
        """Remove auditor by category."""
        for i, auditor in enumerate(self.auditors):
            if auditor.get_category() == category:
                removed_auditor = self.auditors.pop(i)
                logger.info(f"Removed auditor: {removed_auditor.__class__.__name__}")
                return True
        return False
    
    def get_auditor_status(self) -> Dict[str, Any]:
        """Get status of all registered auditors."""
        return {
            "total_auditors": len(self.auditors),
            "categories": [auditor.get_category().value for auditor in self.auditors],
            "auditor_classes": [auditor.__class__.__name__ for auditor in self.auditors]
        }


# Global instance
security_audit_framework = SecurityAuditFramework()