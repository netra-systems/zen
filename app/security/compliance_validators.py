"""
Compliance validation and summary functionality.
Provides analysis and reporting capabilities for compliance checks.
"""

from typing import Dict, List, Any
from datetime import datetime, timezone

from .compliance_checks import ComplianceCheckManager, ComplianceCheck, ComplianceStatus


class ComplianceValidator:
    """Validates and analyzes compliance data."""
    
    def __init__(self, check_manager: ComplianceCheckManager):
        self.check_manager = check_manager
    
    def get_compliance_summary(self) -> Dict[str, Any]:
        """Get overall compliance summary."""
        total_checks = len(self.check_manager.checks)
        status_counts = self._count_by_status()
        compliance_percentage = self._calculate_compliance_percentage(status_counts['compliant'], total_checks)
        return self._build_summary_dict(total_checks, status_counts, compliance_percentage)
    
    def _build_summary_dict(self, total_checks: int, status_counts: Dict[str, int], 
                           compliance_percentage: float) -> Dict[str, Any]:
        """Build the compliance summary dictionary."""
        base_data = self._get_base_summary_data(total_checks, compliance_percentage)
        status_data = self._get_status_summary_data(status_counts)
        return {**base_data, **status_data, "status_breakdown": status_counts}
    
    def _get_base_summary_data(self, total_checks: int, compliance_percentage: float) -> Dict[str, Any]:
        """Get base summary data."""
        return {
            "total_checks": total_checks,
            "compliance_percentage": compliance_percentage
        }
    
    def _get_status_summary_data(self, status_counts: Dict[str, int]) -> Dict[str, Any]:
        """Get status-specific summary data."""
        return {
            "compliant": status_counts['compliant'],
            "non_compliant": status_counts['non_compliant'],
            "partially_compliant": status_counts['partially_compliant'],
            "needs_review": status_counts['needs_review']
        }
    
    def _count_by_status(self) -> Dict[str, int]:
        """Count checks by status."""
        counts = {'compliant': 0, 'non_compliant': 0, 'partially_compliant': 0, 'needs_review': 0}
        for check in self.check_manager.checks.values():
            self._increment_status_count(counts, check.status)
        return counts
    
    def _increment_status_count(self, counts: Dict[str, int], status: ComplianceStatus) -> None:
        """Increment the appropriate status count."""
        status_map = self._get_status_count_mapping()
        if status in status_map:
            counts[status_map[status]] += 1
    
    def _get_status_count_mapping(self) -> Dict[ComplianceStatus, str]:
        """Get mapping of status to count key."""
        return {
            ComplianceStatus.COMPLIANT: 'compliant',
            ComplianceStatus.NON_COMPLIANT: 'non_compliant',
            ComplianceStatus.PARTIALLY_COMPLIANT: 'partially_compliant',
            ComplianceStatus.NEEDS_REVIEW: 'needs_review'
        }
    
    def _calculate_compliance_percentage(self, compliant: int, total: int) -> float:
        """Calculate compliance percentage."""
        return (compliant / total) * 100 if total > 0 else 0
    
    def get_high_priority_issues(self) -> List[ComplianceCheck]:
        """Get high priority compliance issues."""
        return [
            check for check in self.check_manager.checks.values()
            if check.priority == "high" and check.status != ComplianceStatus.COMPLIANT
        ]
    
    def get_remediation_plan(self) -> List[Dict[str, Any]]:
        """Get prioritized remediation plan."""
        non_compliant_checks = self._get_non_compliant_checks()
        sorted_checks = self._sort_by_priority(non_compliant_checks)
        return self._build_remediation_items(sorted_checks)
    
    def _get_non_compliant_checks(self) -> List[ComplianceCheck]:
        """Get all non-compliant checks."""
        non_compliant_statuses = self._get_non_compliant_statuses()
        return [
            check for check in self.check_manager.checks.values()
            if check.status in non_compliant_statuses
        ]
    
    def _get_non_compliant_statuses(self) -> List[ComplianceStatus]:
        """Get list of non-compliant status types."""
        return [
            ComplianceStatus.NON_COMPLIANT,
            ComplianceStatus.PARTIALLY_COMPLIANT,
            ComplianceStatus.NEEDS_REVIEW
        ]
    
    def _sort_by_priority(self, checks: List[ComplianceCheck]) -> List[ComplianceCheck]:
        """Sort checks by priority."""
        priority_order = {"high": 1, "medium": 2, "low": 3}
        return sorted(checks, key=lambda x: priority_order.get(x.priority, 999))
    
    def _build_remediation_items(self, checks: List[ComplianceCheck]) -> List[Dict[str, Any]]:
        """Build remediation plan items."""
        return [self._create_remediation_item(check) for check in checks]
    
    def _create_remediation_item(self, check: ComplianceCheck) -> Dict[str, Any]:
        """Create single remediation item."""
        return {
            "check_id": check.id, "title": check.title, "priority": check.priority,
            "status": check.status, "standard": check.standard,
            "remediation_steps": check.remediation_steps,
            "estimated_effort": self._estimate_effort(check)
        }
    
    def _estimate_effort(self, check: ComplianceCheck) -> str:
        """Estimate effort required for remediation."""
        step_count = len(check.remediation_steps)
        return self._classify_effort_by_steps(step_count)
    
    def _classify_effort_by_steps(self, step_count: int) -> str:
        """Classify effort level by step count."""
        effort_thresholds = self._get_effort_thresholds()
        return self._determine_effort_level(step_count, effort_thresholds)
    
    def _get_effort_thresholds(self) -> Dict[str, int]:
        """Get effort classification thresholds."""
        return {"none": 0, "low": 2, "medium": 4}
    
    def _determine_effort_level(self, step_count: int, thresholds: Dict[str, int]) -> str:
        """Determine effort level based on step count and thresholds."""
        level_checks = self._get_effort_level_checks(step_count, thresholds)
        return self._evaluate_effort_checks(level_checks)
    
    def _get_effort_level_checks(self, step_count: int, thresholds: Dict[str, int]) -> Dict[str, bool]:
        """Get effort level check results."""
        return {
            "none": step_count == thresholds["none"],
            "low": step_count <= thresholds["low"],
            "medium": step_count <= thresholds["medium"]
        }
    
    def _evaluate_effort_checks(self, checks: Dict[str, bool]) -> str:
        """Evaluate effort level checks to determine result."""
        priority_order = ["none", "low", "medium"]
        for level in priority_order:
            if checks[level]:
                return level
        return "high"
    
    def export_compliance_report(self) -> str:
        """Export compliance report as formatted text."""
        summary = self.get_compliance_summary()
        remediation_plan = self.get_remediation_plan()
        return self._build_report_text(summary, remediation_plan)
    
    def _build_report_text(self, summary: Dict[str, Any], 
                          remediation_plan: List[Dict[str, Any]]) -> str:
        """Build formatted report text."""
        report_lines = self._build_header_section()
        report_lines.extend(self._build_summary_section(summary))
        report_lines.extend(self._build_remediation_section(remediation_plan))
        return "\n".join(report_lines)
    
    def _build_header_section(self) -> List[str]:
        """Build report header section."""
        timestamp = self._get_formatted_timestamp()
        return self._create_header_lines(timestamp)
    
    def _get_formatted_timestamp(self) -> str:
        """Get formatted timestamp for report."""
        return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    
    def _create_header_lines(self, timestamp: str) -> List[str]:
        """Create header lines with timestamp."""
        return [
            "SECURITY COMPLIANCE REPORT",
            "=" * 50,
            f"Generated: {timestamp}",
            ""
        ]
    
    def _build_summary_section(self, summary: Dict[str, Any]) -> List[str]:
        """Build summary section of report."""
        header_lines = self._get_summary_header()
        status_lines = self._get_summary_status_lines(summary)
        footer_lines = self._get_summary_footer()
        return header_lines + status_lines + footer_lines
    
    def _get_summary_header(self) -> List[str]:
        """Get summary section header."""
        return ["COMPLIANCE SUMMARY:"]
    
    def _get_summary_status_lines(self, summary: Dict[str, Any]) -> List[str]:
        """Get summary status lines."""
        basic_lines = self._get_basic_status_lines(summary)
        detailed_lines = self._get_detailed_status_lines(summary)
        return basic_lines + detailed_lines
    
    def _get_basic_status_lines(self, summary: Dict[str, Any]) -> List[str]:
        """Get basic status lines."""
        return [
            f"  Total Checks: {summary['total_checks']}",
            f"  Compliant: {summary['compliant']}",
            f"  Non-Compliant: {summary['non_compliant']}"
        ]
    
    def _get_detailed_status_lines(self, summary: Dict[str, Any]) -> List[str]:
        """Get detailed status lines."""
        return [
            f"  Partially Compliant: {summary['partially_compliant']}",
            f"  Needs Review: {summary['needs_review']}",
            f"  Compliance Percentage: {summary['compliance_percentage']:.1f}%"
        ]
    
    def _get_summary_footer(self) -> List[str]:
        """Get summary section footer."""
        return ["", "REMEDIATION PLAN:", "-" * 20]
    
    def _build_remediation_section(self, remediation_plan: List[Dict[str, Any]]) -> List[str]:
        """Build remediation section of report."""
        if not remediation_plan:
            return ["No remediation required - all checks compliant!"]
        return self._compile_remediation_items(remediation_plan)
    
    def _compile_remediation_items(self, remediation_plan: List[Dict[str, Any]]) -> List[str]:
        """Compile all remediation items into lines."""
        lines = []
        for i, item in enumerate(remediation_plan, 1):
            lines.extend(self._build_remediation_item(i, item))
        return lines
    
    def _build_remediation_item(self, index: int, item: Dict[str, Any]) -> List[str]:
        """Build single remediation item text."""
        header_lines = self._build_item_header(index, item)
        step_lines = self._build_item_steps(item['remediation_steps'])
        return header_lines + step_lines + [""]
    
    def _build_item_header(self, index: int, item: Dict[str, Any]) -> List[str]:
        """Build remediation item header."""
        return [
            f"{index}. {item['title']} [{item['priority'].upper()} PRIORITY]",
            f"   Status: {item['status']}", f"   Standard: {item['standard']}",
            f"   Effort: {item['estimated_effort']}", f"   Steps:"
        ]
    
    def _build_item_steps(self, steps: List[str]) -> List[str]:
        """Build remediation item steps."""
        return [f"     - {step}" for step in steps]