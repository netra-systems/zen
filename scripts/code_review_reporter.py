#!/usr/bin/env python3
"""
Code Review Report Generation
ULTRA DEEP THINK: Module-based architecture - Report generation extracted for 450-line compliance
"""

from datetime import datetime
from pathlib import Path
from typing import List


class CodeReviewReporter:
    """Handles all report generation operations for code review"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root

    def _add_report_header(self, report: List[str]) -> None:
        """Add header to the report."""
        report.append(f"# Code Review Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

    def _add_executive_summary(self, report: List[str], mode: str, focus: str, issues: dict) -> None:
        """Add executive summary section."""
        report.append("## Executive Summary")
        report.append(f"- Review Type: {mode.upper()}")
        if focus:
            report.append(f"- Focus Area: {focus}")
        report.append(f"- Critical Issues Found: {len(issues['critical'])}")
        report.append(f"- High Priority Issues: {len(issues['high'])}")
        report.append(f"- Medium Priority Issues: {len(issues['medium'])}")
        report.append(f"- Low Priority Issues: {len(issues['low'])}")
        report.append("")

    def _add_system_health(self, report: List[str], smoke_test_results: dict) -> None:
        """Add system health section."""
        report.append("## System Health")
        report.append("### Smoke Test Results")
        for test, passed in smoke_test_results.items():
            status = " PASS:  PASS" if passed else " FAIL:  FAIL"
            report.append(f"- {test}: {status}")
        report.append("")

    def _add_recent_changes(self, report: List[str], recent_changes: List[str]) -> None:
        """Add recent changes section if changes exist."""
        if not recent_changes:
            return
        report.append("## Recent Changes Analysis")
        report.append("### Recent Commits")
        for commit in recent_changes[:5]:
            report.append(f"- {commit}")
        report.append("")

    def _add_spec_conflicts(self, report: List[str], spec_code_conflicts: List[str]) -> None:
        """Add spec-code alignment issues if any exist."""
        if not spec_code_conflicts:
            return
        report.append("## Spec-Code Alignment Issues")
        for conflict in spec_code_conflicts:
            report.append(f"- {conflict}")
        report.append("")

    def _add_ai_issues(self, report: List[str], ai_issues_found: List[str]) -> None:
        """Add AI coding issues section if any exist."""
        if not ai_issues_found:
            return
        report.append("## AI Coding Issues Detected")
        for issue in ai_issues_found:
            report.append(f"- {issue}")
        report.append("")

    def _add_performance_concerns(self, report: List[str], performance_concerns: List[str]) -> None:
        """Add performance concerns section if any exist."""
        if not performance_concerns:
            return
        report.append("## Performance Concerns")
        for concern in performance_concerns:
            report.append(f"- {concern}")
        report.append("")

    def _add_security_issues(self, report: List[str], security_issues: List[str]) -> None:
        """Add security issues section if any exist."""
        if not security_issues:
            return
        report.append("## Security Issues")
        for issue in security_issues:
            report.append(f"- [WARNING] {issue}")
        report.append("")

    def _add_critical_action_items(self, report: List[str], issues: dict) -> None:
        """Add critical action items if any exist."""
        if not issues["critical"]:
            return
        report.append("### Critical (Must fix immediately)")
        for i, issue in enumerate(issues["critical"], 1):
            report.append(f"{i}. {issue}")
        report.append("")

    def _add_high_action_items(self, report: List[str], issues: dict) -> None:
        """Add high priority action items if any exist."""
        if not issues["high"]:
            return
        report.append("### High (Fix before next release)")
        for i, issue in enumerate(issues["high"], 1):
            report.append(f"{i}. {issue}")
        report.append("")

    def _add_medium_action_items(self, report: List[str], issues: dict) -> None:
        """Add medium priority action items if any exist."""
        if not issues["medium"]:
            return
        report.append("### Medium (Fix in next sprint)")
        for i, issue in enumerate(issues["medium"][:10], 1):
            report.append(f"{i}. {issue}")
        if len(issues["medium"]) > 10:
            report.append(f"... and {len(issues['medium']) - 10} more")
        report.append("")

    def _add_recommendations(self, report: List[str], issues: dict, ai_issues_found: List[str], 
                           spec_code_conflicts: List[str], security_issues: List[str], 
                           performance_concerns: List[str]) -> None:
        """Add recommendations section."""
        report.append("## Recommendations")
        
        if len(issues["critical"]) > 0:
            report.append("- **URGENT**: Address critical issues before any new development")
        if len(ai_issues_found) > 5:
            report.append("- Consider manual review of recent AI-generated code")
        if len(spec_code_conflicts) > 0:
            report.append("- Update specifications to match current implementation")
        if len(security_issues) > 0:
            report.append("- Conduct thorough security audit immediately")
        if len(performance_concerns) > 0:
            report.append("- Profile application performance and optimize hotspots")

    def _add_report_footer(self, report: List[str]) -> None:
        """Add footer to the report."""
        report.append("")
        report.append("---")
        report.append("*Generated by run_review.py implementing SPEC/review.xml*")

    def generate_report(self, mode: str, focus: str, issues: dict, smoke_test_results: dict,
                       recent_changes: List[str], spec_code_conflicts: List[str], 
                       ai_issues_found: List[str], performance_concerns: List[str], 
                       security_issues: List[str]) -> str:
        """Generate comprehensive review report"""
        report = []
        
        self._add_report_header(report)
        self._add_executive_summary(report, mode, focus, issues)
        self._add_system_health(report, smoke_test_results)
        self._add_recent_changes(report, recent_changes)
        self._add_spec_conflicts(report, spec_code_conflicts)
        self._add_ai_issues(report, ai_issues_found)
        self._add_performance_concerns(report, performance_concerns)
        self._add_security_issues(report, security_issues)
        
        report.append("## Action Items")
        self._add_critical_action_items(report, issues)
        self._add_high_action_items(report, issues)
        self._add_medium_action_items(report, issues)
        
        self._add_recommendations(report, issues, ai_issues_found, spec_code_conflicts, 
                                security_issues, performance_concerns)
        self._add_report_footer(report)
        
        return "\n".join(report)

    def save_report(self, report: str) -> Path:
        """Save report to file"""
        reports_dir = self.project_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"code_review_{timestamp}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n[REPORT] Report saved to: {report_file}")
        return report_file

    def display_summary(self, issues: dict) -> None:
        """Display review summary."""
        print("\n" + "=" * 60)
        print("REVIEW SUMMARY")
        print("=" * 60)
        self._display_critical_issues(issues)
        self._display_high_issues(issues)
        self._display_totals(issues)

    def _display_critical_issues(self, issues: dict) -> None:
        """Display critical issues summary."""
        if len(issues["critical"]) > 0:
            print(f"[CRITICAL] Issues: {len(issues['critical'])}")
            for issue in issues["critical"][:3]:
                print(f"   - {issue}")

    def _display_high_issues(self, issues: dict) -> None:
        """Display high priority issues summary."""
        if len(issues["high"]) > 0:
            print(f"[HIGH] Priority Issues: {len(issues['high'])}")
            for issue in issues["high"][:3]:
                print(f"   - {issue}")

    def _display_totals(self, issues: dict) -> None:
        """Display total issues count."""
        total_issues = sum(len(issues_list) for issues_list in issues.values())
        print(f"\n[TOTAL] Issues Found: {total_issues}")
        print(f"   Critical: {len(issues['critical'])}")
        print(f"   High: {len(issues['high'])}")
        print(f"   Medium: {len(issues['medium'])}")
        print(f"   Low: {len(issues['low'])}")

    def determine_final_status(self, issues: dict) -> bool:
        """Determine and display final review status."""
        if len(issues["critical"]) > 0:
            print("\n[FAILED] Review FAILED - Critical issues must be addressed")
            return False
        elif len(issues["high"]) > 5:
            print("\n[WARNING] Review PASSED with warnings - Many high priority issues")
            return True
        else:
            print("\n[PASSED] Review PASSED")
            return True