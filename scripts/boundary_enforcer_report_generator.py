#!/usr/bin/env python3
"""
Report generation module for boundary enforcement system.
Handles all report formatting and output generation.
"""

from collections import defaultdict
from typing import Dict, List, Tuple

from boundary_enforcer_core_types import (
    BoundaryReport,
    BoundaryViolation,
    create_timestamp,
)


class BoundaryReportGenerator:
    """Generates comprehensive boundary enforcement reports"""
    
    def __init__(self, violations: List[BoundaryViolation], system_metrics: Dict):
        self.violations = violations
        self.system_metrics = system_metrics

    def generate_boundary_report(self) -> BoundaryReport:
        """Generate comprehensive boundary enforcement report"""
        violations_by_boundary = self._count_violations_by_boundary()
        emergency_actions = self._collect_emergency_actions()
        risk_level, remediation_plan = self._assess_growth_risk(emergency_actions)
        compliance_score = self._calculate_compliance_score(violations_by_boundary)
        return self._build_report_object(violations_by_boundary, emergency_actions, 
                                        risk_level, remediation_plan, compliance_score)

    def _count_violations_by_boundary(self) -> Dict[str, int]:
        """Count violations grouped by boundary type"""
        violations_by_boundary = defaultdict(int)
        for violation in self.violations:
            violations_by_boundary[violation.boundary_name] += 1
        return violations_by_boundary

    def _collect_emergency_actions(self) -> List[str]:
        """Collect emergency actions from critical violations"""
        emergency_actions = []
        for violation in self.violations:
            if violation.severity == "critical" and violation.impact_score >= 8:
                emergency_actions.append(f"EMERGENCY: {violation.fix_suggestion}")
        return emergency_actions

    def _assess_growth_risk(self, emergency_actions: List[str]) -> Tuple[str, List[str]]:
        """Assess growth risk level and generate remediation plan"""
        total_violations = len(self.violations)
        risk_score = sum(v.impact_score for v in self.violations)
        if risk_score > 500 or total_violations > 1000:
            return self._handle_critical_risk(emergency_actions)
        elif risk_score > 200 or total_violations > 500:
            return self._handle_high_risk()
        elif risk_score > 50 or total_violations > 100:
            return "MEDIUM - MONITOR CLOSELY", ["Weekly boundary compliance checks"]
        return "LOW - MANAGEABLE", []

    def _handle_critical_risk(self, emergency_actions: List[str]) -> Tuple[str, List[str]]:
        """Handle critical risk level response"""
        emergency_actions.extend([
            "IMMEDIATE: Stop all new feature development",
            "IMMEDIATE: Begin emergency refactoring sprint"
        ])
        return "CRITICAL - SYSTEM UNSTABLE", []

    def _handle_high_risk(self) -> Tuple[str, List[str]]:
        """Handle high risk level response"""
        return "HIGH - REQUIRES INTERVENTION", [
            "Schedule architecture review within 1 week",
            "Implement daily boundary monitoring"
        ]

    def _calculate_compliance_score(self, violations_by_boundary: Dict[str, int]) -> float:
        """Calculate boundary compliance score"""
        total_possible_violations = 7  # Number of boundary types
        return max(0, (total_possible_violations - len(violations_by_boundary)) / total_possible_violations * 100)

    def _build_report_object(self, violations_by_boundary: Dict[str, int], emergency_actions: List[str],
                           risk_level: str, remediation_plan: List[str], compliance_score: float) -> BoundaryReport:
        """Build the final boundary report object"""
        if not emergency_actions:
            remediation_plan.extend(["Continue enforcing pre-commit hooks", "Maintain CI/CD boundary gates", 
                                   "Regular automated compliance monitoring"])
        return BoundaryReport(
            total_violations=len(self.violations), boundary_compliance_score=compliance_score, 
            growth_risk_level=risk_level, timestamp=create_timestamp(), 
            violations_by_boundary=dict(violations_by_boundary), violations=self.violations, 
            system_metrics=self.system_metrics, remediation_plan=remediation_plan, emergency_actions=emergency_actions
        )

class ConsoleReportPrinter:
    """Prints human-readable reports to console"""
    
    @staticmethod
    def print_enforcement_report(report: BoundaryReport) -> str:
        """Generate human-readable enforcement report"""
        ConsoleReportPrinter._print_header(report)
        ConsoleReportPrinter._print_system_metrics(report)
        ConsoleReportPrinter._print_boundary_violations(report)
        ConsoleReportPrinter._print_emergency_actions(report)
        ConsoleReportPrinter._print_remediation_plan(report)
        ConsoleReportPrinter._print_critical_violations(report)
        return ConsoleReportPrinter._determine_status(report)

    @staticmethod
    def _print_header(report: BoundaryReport) -> None:
        """Print report header with basic info"""
        print("\n" + "=" * 80)
        print("BOUNDARY ENFORCEMENT REPORT")
        print("=" * 80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Growth Risk Level: {report.growth_risk_level}")
        print(f"Boundary Compliance: {report.boundary_compliance_score:.1f}%")
        print(f"Total Violations: {report.total_violations}")

    @staticmethod
    def _print_system_metrics(report: BoundaryReport) -> None:
        """Print system metrics section"""
        print(f"\n[SYSTEM METRICS]:")
        print(f"  Total Files: {report.system_metrics['total_files']}")
        print(f"  Total Lines: {report.system_metrics['total_lines']:,}")
        print(f"  Module Count: {report.system_metrics['module_count']}")
        print(f"  Avg File Size: {report.system_metrics['avg_file_size']:.1f} lines")
        print(f"  Growth Velocity: {report.system_metrics['growth_velocity']:.2f}")
        print(f"  Complexity Debt: {report.system_metrics['complexity_debt']:.2f}")

    @staticmethod
    def _print_boundary_violations(report: BoundaryReport) -> None:
        """Print boundary violations section"""
        print(f"\n[BOUNDARY VIOLATIONS]:")
        for boundary, count in report.violations_by_boundary.items():
            print(f"  {boundary}: {count} violations")

    @staticmethod
    def _print_emergency_actions(report: BoundaryReport) -> None:
        """Print emergency actions section if needed"""
        if report.emergency_actions:
            print(f"\n[EMERGENCY ACTIONS REQUIRED]:")
            for action in report.emergency_actions:
                print(f"  - {action}")

    @staticmethod
    def _print_remediation_plan(report: BoundaryReport) -> None:
        """Print remediation plan section if needed"""
        if report.remediation_plan:
            print(f"\n[REMEDIATION PLAN]:")
            for action in report.remediation_plan:
                print(f"  - {action}")

    @staticmethod
    def _print_critical_violations(report: BoundaryReport) -> None:
        """Print top critical violations section"""
        print(f"\n[TOP CRITICAL VIOLATIONS]:")
        critical_violations = [v for v in report.violations if v.severity == "critical"]
        ConsoleReportPrinter._print_top_violations(critical_violations)

    @staticmethod
    def _print_top_violations(critical_violations: List[BoundaryViolation]) -> None:
        """Print top critical violations with details"""
        top_violations = sorted(critical_violations, key=lambda x: x.impact_score, reverse=True)[:10]
        for i, violation in enumerate(top_violations, 1):
            print(f"  {i}. {violation.description}")
            print(f"     File: {violation.file_path}")
            if violation.auto_split_suggestion:
                print(f"     Auto-fix: {violation.auto_split_suggestion}")

    @staticmethod
    def _determine_status(report: BoundaryReport) -> str:
        """Determine final report status"""
        if report.emergency_actions:
            return "FAIL"
        elif report.total_violations > 0:
            return "MONITOR"
        return "PASS"

class PRCommentGenerator:
    """Generates PR comments with boundary status"""
    
    @staticmethod
    def generate_pr_comment(report: BoundaryReport) -> str:
        """Generate PR comment with boundary status"""
        status_emoji, status_text, status_color = PRCommentGenerator._determine_pr_status(report)
        comment = PRCommentGenerator._build_pr_header(status_emoji, status_text, status_color, report)
        comment += PRCommentGenerator._build_system_metrics_section(report)
        comment += PRCommentGenerator._build_boundary_status_section(report)
        comment += PRCommentGenerator._build_action_sections(report)
        comment += PRCommentGenerator._build_violations_section(report)
        comment += PRCommentGenerator._build_tools_section(report)
        return comment

    @staticmethod
    def _determine_pr_status(report: BoundaryReport) -> Tuple[str, str, str]:
        """Determine PR status emoji, text, and color"""
        if report.emergency_actions:
            return " ALERT: ", "EMERGENCY", "red"
        elif report.total_violations > 50:
            return " FAIL: ", "FAILING", "red"
        elif report.total_violations > 0:
            return " WARNING: [U+FE0F]", "WARNING", "yellow"
        return " PASS: ", "PASSING", "green"

    @staticmethod
    def _build_pr_header(emoji: str, status_text: str, color: str, report: BoundaryReport) -> str:
        """Build PR comment header section"""
        return f"""# {emoji} Boundary Enforcement Report

**Status:** <span style="color: {color}; font-weight: bold;">{status_text}</span>
**Growth Risk:** {report.growth_risk_level}
**Compliance Score:** {report.boundary_compliance_score:.1f}%
**Total Violations:** {report.total_violations}

"""

    @staticmethod
    def _build_system_metrics_section(report: BoundaryReport) -> str:
        """Build system metrics section"""
        return f"""## System Metrics
- **Total Files:** {report.system_metrics.get('total_files', 0)}
- **Total Lines:** {report.system_metrics.get('total_lines', 0):,}
- **Module Count:** {report.system_metrics.get('module_count', 0)}
- **Growth Velocity:** {report.system_metrics.get('growth_velocity', 0):.2f}

"""

    @staticmethod
    def _build_boundary_status_section(report: BoundaryReport) -> str:
        """Build boundary status section"""
        section = "## Boundary Status\n"
        for boundary, count in report.violations_by_boundary.items():
            emoji = "[U+1F534]" if count > 0 else " PASS: "
            boundary_name = boundary.replace('_', ' ').title()
            section += f"- **{boundary_name}:** {emoji} {count} violations\n"
        return section + "\n"

    @staticmethod
    def _build_action_sections(report: BoundaryReport) -> str:
        """Build emergency actions and remediation plan sections"""
        sections = ""
        if report.emergency_actions:
            sections += "##  ALERT:  Emergency Actions Required\n"
            sections += "\n".join(f"- {action}" for action in report.emergency_actions) + "\n\n"
        if report.remediation_plan:
            sections += "## [U+1F4CB] Remediation Plan\n"
            sections += "\n".join(f"- {action}" for action in report.remediation_plan) + "\n\n"
        return sections

    @staticmethod
    def _build_violations_section(report: BoundaryReport) -> str:
        """Build top critical violations section"""
        if not report.violations:
            return ""
        critical_violations = [v for v in report.violations if v.severity == "critical"][:5]
        if not critical_violations:
            return ""
        section = "##  SEARCH:  Top Critical Violations\n"
        for i, violation in enumerate(critical_violations, 1):
            section += f"{i}. **{violation.file_path}** - {violation.description}\n"
            if violation.auto_split_suggestion:
                section += f"    IDEA:  *{violation.auto_split_suggestion}*\n"
        return section + "\n"

    @staticmethod
    def _build_tools_section(report: BoundaryReport) -> str:
        """Build available tools section"""
        return f"""## [U+1F6E0][U+FE0F] Available Tools
- `python scripts/boundary_enforcer.py --enforce` - Full boundary check
- `python scripts/auto_split_files.py --scan` - Automated file splitting
- `python scripts/auto_decompose_functions.py --scan` - Function decomposition
- `python scripts/emergency_boundary_actions.py --assess` - Emergency assessment

---
*Generated by Boundary Enforcement System v2.0 | Timestamp: {report.timestamp}*
"""