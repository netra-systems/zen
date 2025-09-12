#!/usr/bin/env python3
"""
Enhanced compliance reporter with 4-tier severity system and business-aligned categorization.
"""

from typing import Dict, List, Optional
from collections import defaultdict

from scripts.compliance.core import Violation, ComplianceResults
from scripts.compliance.severity_tiers import SeverityTiers, SeverityLevel
from scripts.compliance.reporter_utils import ReporterUtils


class EnhancedComplianceReporter:
    """Enhanced reporter with tiered severity and deployment blocking"""
    
    def __init__(self, use_emoji: bool = True):
        self.use_emoji = use_emoji
        self.utils = ReporterUtils(use_emoji=use_emoji)
        self.severity_tiers = SeverityTiers()
    
    def generate_report(self, results: ComplianceResults) -> str:
        """Generate comprehensive compliance report with severity tiers"""
        lines = []
        
        # Header
        lines.append("=" * 80)
        lines.append("NETRA APEX COMPLIANCE REPORT - 4-TIER SEVERITY SYSTEM")
        lines.append("=" * 80)
        lines.append("")
        
        # Categorize violations by severity
        violations_by_severity = self._categorize_violations(results.violations)
        
        # Deployment readiness check
        is_ready, readiness_msg = SeverityTiers.check_deployment_readiness(violations_by_severity)
        lines.append(self._format_deployment_status(is_ready, readiness_msg))
        lines.append("")
        
        # Executive summary
        lines.append(self._format_executive_summary(violations_by_severity, results))
        lines.append("")
        
        # Severity breakdown with limits
        lines.append(self._format_severity_breakdown(violations_by_severity))
        lines.append("")
        
        # Critical violations (show ALL)
        if violations_by_severity.get(SeverityLevel.CRITICAL):
            lines.append(self._format_critical_violations(
                violations_by_severity[SeverityLevel.CRITICAL]
            ))
            lines.append("")
        
        # High severity violations (show up to 20)
        if violations_by_severity.get(SeverityLevel.HIGH):
            lines.append(self._format_high_violations(
                violations_by_severity[SeverityLevel.HIGH]
            ))
            lines.append("")
        
        # Medium severity violations (show up to 100)
        if violations_by_severity.get(SeverityLevel.MEDIUM):
            lines.append(self._format_medium_violations(
                violations_by_severity[SeverityLevel.MEDIUM]
            ))
            lines.append("")
        
        # Low severity violations (summary only)
        if violations_by_severity.get(SeverityLevel.LOW):
            lines.append(self._format_low_violations(
                violations_by_severity[SeverityLevel.LOW]
            ))
            lines.append("")
        
        # Action items by timeline
        lines.append(self._format_action_items(violations_by_severity))
        lines.append("")
        
        # Business impact summary
        lines.append(self._format_business_impact(violations_by_severity))
        
        return "\n".join(lines)
    
    def _categorize_violations(self, violations: List[Violation]) -> Dict[SeverityLevel, List[Violation]]:
        """Categorize violations by severity level"""
        categorized = defaultdict(list)
        
        for violation in violations:
            # Map string severity to enum
            severity_map = {
                'critical': SeverityLevel.CRITICAL,
                'high': SeverityLevel.HIGH,
                'medium': SeverityLevel.MEDIUM,
                'low': SeverityLevel.LOW
            }
            severity = severity_map.get(violation.severity, SeverityLevel.LOW)
            categorized[severity].append(violation)
        
        # Sort violations within each severity
        for severity in categorized:
            categorized[severity] = self.utils.sort_violations_by_severity(categorized[severity])
        
        return dict(categorized)
    
    def _format_deployment_status(self, is_ready: bool, message: str) -> str:
        """Format deployment readiness status"""
        if is_ready:
            status = " PASS:  DEPLOYMENT READY" if self.use_emoji else "[READY] DEPLOYMENT READY"
        else:
            status = "[U+1F6AB] DEPLOYMENT BLOCKED" if self.use_emoji else "[BLOCKED] DEPLOYMENT BLOCKED"
        
        return f"{status}\n{message}"
    
    def _format_executive_summary(self, violations_by_severity: Dict, results: ComplianceResults) -> str:
        """Format executive summary"""
        lines = ["EXECUTIVE SUMMARY", "-" * 40]
        
        total_violations = sum(len(v) for v in violations_by_severity.values())
        lines.append(f"Total Violations: {total_violations}")
        lines.append(f"Compliance Score: {results.compliance_score:.1f}%")
        lines.append("")
        
        # Severity counts with limits
        for severity in SeverityLevel:
            config = SeverityTiers.SEVERITY_CONFIGS[severity]
            count = len(violations_by_severity.get(severity, []))
            marker = self.utils.get_severity_marker(severity.value)
            
            if config.blocks_deployment:
                status = " PASS: " if count <= config.max_violations else " FAIL: "
                line = f"{marker} {config.display_name}: {count}/{config.max_violations} {status}"
            else:
                line = f"{marker} {config.display_name}: {count}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_severity_breakdown(self, violations_by_severity: Dict) -> str:
        """Format detailed severity breakdown"""
        lines = ["SEVERITY BREAKDOWN", "-" * 40]
        
        for severity in SeverityLevel:
            config = SeverityTiers.SEVERITY_CONFIGS[severity]
            violations = violations_by_severity.get(severity, [])
            count = len(violations)
            
            marker = self.utils.get_severity_marker(severity.value)
            lines.append(f"\n{marker} {config.display_name} VIOLATIONS ({count})")
            lines.append(f"   Business Impact: {config.business_impact}")
            lines.append(f"   Timeline: {config.remediation_timeline}")
            
            if config.blocks_deployment and count > config.max_violations:
                over = count - config.max_violations
                lines.append(f"    WARNING: [U+FE0F]  OVER LIMIT by {over} violations!")
        
        return "\n".join(lines)
    
    def _format_critical_violations(self, violations: List[Violation]) -> str:
        """Format critical violations - show ALL"""
        lines = [" ALERT:  CRITICAL VIOLATIONS - IMMEDIATE ACTION REQUIRED", "=" * 60]
        
        for i, v in enumerate(violations, 1):
            lines.append(f"\n{i}. {v.file_path}")
            lines.append(f"   Type: {v.violation_type}")
            lines.append(f"   {v.description}")
            lines.append(f"   Impact: {v.business_impact or 'System stability at risk'}")
            lines.append(f"   Fix: {v.fix_suggestion}")
            if v.line_number:
                lines.append(f"   Line: {v.line_number}")
        
        return "\n".join(lines)
    
    def _format_high_violations(self, violations: List[Violation]) -> str:
        """Format high severity violations - show up to 20"""
        lines = ["[U+1F534] HIGH SEVERITY VIOLATIONS", "-" * 40]
        
        max_show = min(20, len(violations))
        for i, v in enumerate(violations[:max_show], 1):
            lines.append(f"\n{i}. {v.file_path}")
            lines.append(f"   {v.description}")
            if v.business_impact:
                lines.append(f"   Impact: {v.business_impact}")
        
        if len(violations) > max_show:
            lines.append(f"\n... and {len(violations) - max_show} more")
        
        return "\n".join(lines)
    
    def _format_medium_violations(self, violations: List[Violation]) -> str:
        """Format medium severity violations - show up to 100"""
        lines = ["[U+1F7E1] MEDIUM SEVERITY VIOLATIONS", "-" * 40]
        
        # Group by violation type
        by_type = defaultdict(list)
        for v in violations:
            by_type[v.violation_type].append(v)
        
        total_shown = 0
        max_show = 100
        
        for vtype, vlist in sorted(by_type.items(), key=lambda x: -len(x[1])):
            if total_shown >= max_show:
                break
            
            lines.append(f"\n{vtype} ({len(vlist)} violations):")
            show_count = min(5, len(vlist), max_show - total_shown)
            
            for v in vlist[:show_count]:
                lines.append(f"  - {v.file_path}: {v.description}")
                total_shown += 1
            
            if len(vlist) > show_count:
                lines.append(f"  ... and {len(vlist) - show_count} more")
        
        if len(violations) > max_show:
            lines.append(f"\nTotal: {len(violations)} medium violations (showing first {max_show})")
        
        return "\n".join(lines)
    
    def _format_low_violations(self, violations: List[Violation]) -> str:
        """Format low severity violations - summary only"""
        lines = ["[U+1F7E2] LOW SEVERITY VIOLATIONS - SUMMARY", "-" * 40]
        
        # Group by category and type
        by_category = defaultdict(lambda: defaultdict(int))
        for v in violations:
            category = v.category or "other"
            by_category[category][v.violation_type] += 1
        
        for category, types in sorted(by_category.items()):
            lines.append(f"\n{category.title()}:")
            for vtype, count in sorted(types.items(), key=lambda x: -x[1]):
                lines.append(f"  - {vtype}: {count} violations")
        
        lines.append(f"\nTotal: {len(violations)} low severity violations")
        lines.append("These can be addressed during regular refactoring cycles.")
        
        return "\n".join(lines)
    
    def _format_action_items(self, violations_by_severity: Dict) -> str:
        """Format action items grouped by timeline"""
        lines = ["ACTION ITEMS BY TIMELINE", "=" * 40]
        
        # Group by timeline
        by_timeline = defaultdict(list)
        for severity, violations in violations_by_severity.items():
            config = SeverityTiers.SEVERITY_CONFIGS[severity]
            if violations:
                by_timeline[config.remediation_timeline].append(
                    (severity, len(violations))
                )
        
        # Sort by urgency
        timeline_order = [
            "Immediate - Stop all work and fix",
            "Within 24 hours",
            "Current sprint",
            "Next refactor cycle"
        ]
        
        for timeline in timeline_order:
            if timeline in by_timeline:
                lines.append(f"\n{timeline}:")
                for severity, count in by_timeline[timeline]:
                    marker = self.utils.get_severity_marker(severity.value)
                    lines.append(f"  {marker} Fix {count} {severity.value} violations")
        
        return "\n".join(lines)
    
    def _format_business_impact(self, violations_by_severity: Dict) -> str:
        """Format business impact summary"""
        lines = ["BUSINESS IMPACT ASSESSMENT", "=" * 40]
        
        impacts = []
        for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]:
            if violations_by_severity.get(severity):
                config = SeverityTiers.SEVERITY_CONFIGS[severity]
                count = len(violations_by_severity[severity])
                impacts.append(f"- {count} {severity.value} violations: {config.business_impact}")
        
        if impacts:
            lines.append("\nImmediate Risks:")
            lines.extend(impacts)
        else:
            lines.append("\n PASS:  No immediate business risks detected")
        
        # Overall health
        total = sum(len(v) for v in violations_by_severity.values())
        critical_high = sum(len(violations_by_severity.get(s, [])) 
                           for s in [SeverityLevel.CRITICAL, SeverityLevel.HIGH])
        
        if critical_high == 0:
            health = "EXCELLENT"
        elif critical_high <= 5:
            health = "GOOD"
        elif critical_high <= 25:
            health = "NEEDS ATTENTION"
        else:
            health = "CRITICAL"
        
        lines.append(f"\nOverall System Health: {health}")
        
        return "\n".join(lines)