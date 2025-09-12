#!/usr/bin/env python3
"""
Report generator for code review system.
Generates comprehensive markdown reports from review data.
"""

from datetime import datetime
from pathlib import Path
from typing import List

from scripts.review.core import ReviewConfig, ReviewData


class ReportGenerator:
    """Generates comprehensive review reports"""
    
    def __init__(self, config: ReviewConfig):
        self.config = config
    
    def generate_report(self, review_data: ReviewData) -> str:
        """Generate comprehensive review report"""
        report = []
        self._add_report_header(report)
        self._add_executive_summary(report, review_data)
        self._add_system_health(report, review_data)
        self._add_recent_changes(report, review_data)
        self._add_spec_conflicts(report, review_data)
        self._add_ai_issues(report, review_data)
        self._add_performance_concerns(report, review_data)
        self._add_security_issues(report, review_data)
        self._add_action_items(report, review_data)
        self._add_recommendations(report, review_data)
        self._add_report_footer(report)
        return "\n".join(report)
    
    def _add_report_header(self, report: List[str]) -> None:
        """Add header to the report"""
        report.append(f"# Code Review Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
    
    def _add_executive_summary(self, report: List[str], review_data: ReviewData) -> None:
        """Add executive summary section"""
        report.append("## Executive Summary")
        report.append(f"- Review Type: {self.config.mode.upper()}")
        if self.config.focus:
            report.append(f"- Focus Area: {self.config.focus}")
        counts = review_data.issue_tracker.get_counts_by_severity()
        self._add_issue_counts(report, counts)
        report.append("")
    
    def _add_issue_counts(self, report: List[str], counts: dict) -> None:
        """Add issue counts to report"""
        report.append(f"- Critical Issues Found: {counts['critical']}")
        report.append(f"- High Priority Issues: {counts['high']}")
        report.append(f"- Medium Priority Issues: {counts['medium']}")
        report.append(f"- Low Priority Issues: {counts['low']}")
    
    def _add_system_health(self, report: List[str], review_data: ReviewData) -> None:
        """Add system health section"""
        report.append("## System Health")
        report.append("### Smoke Test Results")
        for test, passed in review_data.smoke_test_results.items():
            status = " PASS:  PASS" if passed else " FAIL:  FAIL"
            report.append(f"- {test}: {status}")
        report.append("")
    
    def _add_recent_changes(self, report: List[str], review_data: ReviewData) -> None:
        """Add recent changes section if changes exist"""
        if not review_data.recent_changes:
            return
        report.append("## Recent Changes Analysis")
        report.append("### Recent Commits")
        for commit in review_data.recent_changes[:5]:
            report.append(f"- {commit}")
        report.append("")
    
    def _add_spec_conflicts(self, report: List[str], review_data: ReviewData) -> None:
        """Add spec-code alignment issues if any exist"""
        if not review_data.spec_code_conflicts:
            return
        report.append("## Spec-Code Alignment Issues")
        for conflict in review_data.spec_code_conflicts:
            report.append(f"- {conflict}")
        report.append("")
    
    def _add_ai_issues(self, report: List[str], review_data: ReviewData) -> None:
        """Add AI coding issues section if any exist"""
        if not review_data.ai_issues_found:
            return
        report.append("## AI Coding Issues Detected")
        for issue in review_data.ai_issues_found:
            report.append(f"- {issue}")
        report.append("")
    
    def _add_performance_concerns(self, report: List[str], review_data: ReviewData) -> None:
        """Add performance concerns section if any exist"""
        if not review_data.performance_concerns:
            return
        report.append("## Performance Concerns")
        for concern in review_data.performance_concerns:
            report.append(f"- {concern}")
        report.append("")
    
    def _add_security_issues(self, report: List[str], review_data: ReviewData) -> None:
        """Add security issues section if any exist"""
        if not review_data.security_issues:
            return
        report.append("## Security Issues")
        for issue in review_data.security_issues:
            report.append(f"- [WARNING] {issue}")
        report.append("")
    
    def _add_action_items(self, report: List[str], review_data: ReviewData) -> None:
        """Add action items section"""
        report.append("## Action Items")
        self._add_critical_action_items(report, review_data)
        self._add_high_action_items(report, review_data)
        self._add_medium_action_items(report, review_data)
    
    def _add_critical_action_items(self, report: List[str], review_data: ReviewData) -> None:
        """Add critical action items if any exist"""
        critical_issues = review_data.issue_tracker.get_issues_by_severity("critical")
        if not critical_issues:
            return
        report.append("### Critical (Must fix immediately)")
        for i, issue in enumerate(critical_issues, 1):
            report.append(f"{i}. {issue.description}")
        report.append("")
    
    def _add_high_action_items(self, report: List[str], review_data: ReviewData) -> None:
        """Add high priority action items if any exist"""
        high_issues = review_data.issue_tracker.get_issues_by_severity("high")
        if not high_issues:
            return
        report.append("### High (Fix before next release)")
        for i, issue in enumerate(high_issues, 1):
            report.append(f"{i}. {issue.description}")
        report.append("")
    
    def _add_medium_action_items(self, report: List[str], review_data: ReviewData) -> None:
        """Add medium priority action items if any exist"""
        medium_issues = review_data.issue_tracker.get_issues_by_severity("medium")
        if not medium_issues:
            return
        report.append("### Medium (Fix in next sprint)")
        for i, issue in enumerate(medium_issues[:10], 1):
            report.append(f"{i}. {issue.description}")
        if len(medium_issues) > 10:
            report.append(f"... and {len(medium_issues) - 10} more")
        report.append("")
    
    def _add_recommendations(self, report: List[str], review_data: ReviewData) -> None:
        """Add recommendations section"""
        report.append("## Recommendations")
        self._add_critical_recommendations(report, review_data)
        self._add_general_recommendations(report, review_data)
    
    def _add_critical_recommendations(self, report: List[str], review_data: ReviewData) -> None:
        """Add critical recommendations"""
        if review_data.issue_tracker.has_critical_issues():
            report.append("- **URGENT**: Address critical issues before any new development")
    
    def _add_general_recommendations(self, report: List[str], review_data: ReviewData) -> None:
        """Add general recommendations based on findings"""
        if len(review_data.ai_issues_found) > 5:
            report.append("- Consider manual review of recent AI-generated code")
        if len(review_data.spec_code_conflicts) > 0:
            report.append("- Update specifications to match current implementation")
        if len(review_data.security_issues) > 0:
            report.append("- Conduct thorough security audit immediately")
        if len(review_data.performance_concerns) > 0:
            report.append("- Profile application performance and optimize hotspots")
    
    def _add_report_footer(self, report: List[str]) -> None:
        """Add footer to the report"""
        report.append("")
        report.append("---")
        report.append("*Generated by run_review.py implementing SPEC/review.xml*")
    
    def save_report(self, report: str) -> Path:
        """Save report to file"""
        reports_dir = self.config.project_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = reports_dir / f"code_review_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"\n[REPORT] Report saved to: {report_file}")
        return report_file