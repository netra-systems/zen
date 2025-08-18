"""Security compliance reporting and analysis utilities."""

from typing import Dict, List, Any
from datetime import datetime, timezone

from .compliance_types import ComplianceCheck, ComplianceStandard, ComplianceStatus


class ComplianceReporting:
    """Security compliance reporting and analysis."""
    
    def __init__(self, checks: Dict[str, ComplianceCheck]):
        self.checks = checks
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get overall compliance summary."""
        total_checks = len(self.checks)
        compliant = self._count_by_status(ComplianceStatus.COMPLIANT)
        non_compliant = self._count_by_status(ComplianceStatus.NON_COMPLIANT)
        partially_compliant = self._count_by_status(ComplianceStatus.PARTIALLY_COMPLIANT)
        needs_review = self._count_by_status(ComplianceStatus.NEEDS_REVIEW)
        
        compliance_percentage = self._calculate_percentage(compliant, total_checks)
        
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
    
    def _count_by_status(self, status: ComplianceStatus) -> int:
        """Count checks by status."""
        return len([c for c in self.checks.values() if c.status == status])
    
    def _calculate_percentage(self, compliant: int, total: int) -> float:
        """Calculate compliance percentage."""
        return (compliant / total) * 100 if total > 0 else 0
    
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
        non_compliant_checks = self._get_non_compliant_checks()
        sorted_checks = self._sort_by_priority(non_compliant_checks)
        
        remediation_plan = []
        for check in sorted_checks:
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
    
    def _get_non_compliant_checks(self) -> List[ComplianceCheck]:
        """Get non-compliant checks."""
        return [
            check for check in self.checks.values()
            if check.status in [ComplianceStatus.NON_COMPLIANT, 
                              ComplianceStatus.PARTIALLY_COMPLIANT,
                              ComplianceStatus.NEEDS_REVIEW]
        ]
    
    def _sort_by_priority(self, checks: List[ComplianceCheck]) -> List[ComplianceCheck]:
        """Sort checks by priority."""
        priority_order = {"high": 1, "medium": 2, "low": 3}
        return sorted(checks, key=lambda x: priority_order.get(x.priority, 999))
    
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
        
        report_lines = self._build_report_header(summary)
        report_lines.extend(self._build_remediation_section(remediation_plan))
        
        return "\n".join(report_lines)
    
    def _build_report_header(self, summary: Dict[str, Any]) -> List[str]:
        """Build report header with summary."""
        return [
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
    
    def _build_remediation_section(self, remediation_plan: List[Dict[str, Any]]) -> List[str]:
        """Build remediation section of report."""
        if not remediation_plan:
            return ["No remediation required - all checks compliant!"]
        
        report_lines = []
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
        
        return report_lines
