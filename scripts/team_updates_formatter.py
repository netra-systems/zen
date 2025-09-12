"""Human Formatter - Formats updates for human readability."""

from datetime import datetime
from typing import Any, Dict, List, Optional


class HumanFormatter:
    """Formats team updates for maximum readability."""
    
    def __init__(self):
        """Initialize formatter with emoji mappings."""
        self.status_emojis = {
            "healthy": " PASS: ", "minor_issues": " TARGET: ", 
            "degraded": " WARNING: [U+FE0F]", "critical": " ALERT: "
        }
        self.compliance_emojis = {
            "fully_compliant": " PASS: ", "mostly_compliant": " TARGET: ",
            "partially_compliant": " WARNING: [U+FE0F]", "non_compliant": " FAIL: "
        }
    
    def format_full_report(
        self, data: Dict, time_frame: str, report_id: str
    ) -> str:
        """Format complete team update report."""
        sections = []
        
        sections.append(self.format_header(time_frame, report_id))
        
        if data.get("critical_alerts"):
            sections.append(self.format_critical_alerts(data["critical_alerts"]))
        
        sections.append(self.format_executive_summary(data, time_frame))
        sections.append(self.format_features(data.get("commit_summary", {})))
        sections.append(self.format_bugs(data.get("commit_summary", {})))
        sections.append(self.format_test_health(data))
        sections.append(self.format_code_quality(data))
        sections.append(self.format_documentation(data))
        sections.append(self.format_action_items(data))
        
        return "\n\n".join(filter(None, sections))
    
    def format_header(self, time_frame: str, report_id: str) -> str:
        """Format report header."""
        time_desc = time_frame.replace("_", " ").title()
        return f"""#  CHART:  Team Update Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}
Time Frame: {time_desc}
Report ID: {report_id}"""
    
    def format_critical_alerts(self, alerts: List[Dict]) -> str:
        """Format critical issues section."""
        if not alerts:
            return ""
        
        lines = ["##  ALERT:  Critical Issues (Action Required)"]
        for alert in alerts:
            lines.append(f"- **{alert['type'].upper()}**: {alert['message']}")
        
        return "\n".join(lines)
    
    def format_executive_summary(self, data: Dict, time_frame: str) -> str:
        """Format executive summary section."""
        time_desc = time_frame.replace("_", " ")
        summary = data.get("commit_summary", {})
        metrics = data.get("test_metrics", {})
        
        features = len(summary.get("features", []))
        bugs = len(summary.get("bugs", []))
        pass_rate = metrics.get("pass_rate", 0)
        compliance = data.get("compliance_status", "unknown")
        
        contributors = data.get("contributors", [])[:3]
        top_names = ", ".join([c["name"] for c in contributors])
        
        return f"""## [U+1F4CB] Executive Summary
In the {time_desc}, the team:
- Completed **{features}** new features
- Fixed **{bugs}** bugs
- Tests are **{pass_rate}%** passing
- Code is **{compliance.replace('_', ' ')}**

**Top Contributors**: {top_names or "No commits in period"}"""
    
    def format_features(self, summary: Dict) -> str:
        """Format new features section."""
        features = summary.get("features", [])
        if not features:
            return ""
        
        lines = ["## [U+2728] New Features & Improvements"]
        
        for feat in features[:5]:
            lines.append(f"""
### {feat['title']}
- **What**: {self._make_readable(feat['title'])}
- **Who**: {feat['author']}
- **Commit**: {feat['hash']}""")
        
        if len(features) > 5:
            lines.append(f"\n*Plus {len(features) - 5} more features...*")
        
        return "\n".join(lines)
    
    def format_bugs(self, summary: Dict) -> str:
        """Format bug fixes section."""
        bugs = summary.get("bugs", [])
        if not bugs:
            return ""
        
        lines = ["## [U+1F41B] Bug Fixes"]
        
        for bug in bugs[:5]:
            readable_desc = self._make_readable(bug['title'])
            lines.append(f"- **Fixed**: {readable_desc} (by {bug['author']})")
        
        if len(bugs) > 5:
            lines.append(f"\n*Plus {len(bugs) - 5} more fixes...*")
        
        return "\n".join(lines)
    
    def format_test_health(self, data: Dict) -> str:
        """Format test health section."""
        status = data.get("test_status", "unknown")
        emoji = self.status_emojis.get(status, "[U+2753]")
        metrics = data.get("test_metrics", {})
        coverage = data.get("coverage_info", {})
        
        pass_rate = metrics.get("pass_rate", 0)
        total = metrics.get("total_tests", 0)
        passed = metrics.get("passed_tests", 0)
        coverage_current = coverage.get("current", 0)
        coverage_delta = coverage.get("delta", 0)
        
        delta_symbol = "[U+1F4C8]" if coverage_delta > 0 else "[U+1F4C9]" if coverage_delta < 0 else "[U+27A1][U+FE0F]"
        
        lines = [f"""## [U+1F9EA] Test Health
### Overall Status: {emoji} {status.replace('_', ' ').title()}
- **Pass Rate**: {pass_rate}% ({passed}/{total} tests)
- **Coverage**: {coverage_current}% ({delta_symbol} {abs(coverage_delta)}%)"""]
        
        failures = data.get("test_failures", [])
        if failures:
            lines.append("\n###  WARNING: [U+FE0F] Failing Tests")
            for fail in failures[:3]:
                lines.append(f"- {fail['test']}: {fail['reason']}")
        
        return "\n".join(lines)
    
    def format_code_quality(self, data: Dict) -> str:
        """Format code quality section."""
        compliance = data.get("compliance_status", "unknown")
        emoji = self.compliance_emojis.get(compliance, "[U+2753]")
        
        line_viols = data.get("line_violations", [])
        func_viols = data.get("function_violations", [])
        
        lines = [f"""## [U+1F4CF] Code Quality & Compliance
### Architecture Compliance: {emoji} {compliance.replace('_', ' ').title()}"""]
        
        if line_viols:
            lines.append(f"\n**Files exceeding 300 lines**: {len(line_viols)}")
            worst = line_viols[0] if line_viols else None
            if worst:
                lines.append(f"- Worst offender: {worst['file']} ({worst['lines']} lines)")
        
        if func_viols:
            lines.append(f"\n**Functions exceeding 8 lines**: {len(func_viols)}")
            worst = func_viols[0] if func_viols else None
            if worst:
                lines.append(f"- Worst offender: {worst['function']} ({worst['lines']} lines)")
        
        return "\n".join(lines)
    
    def format_documentation(self, data: Dict) -> str:
        """Format documentation updates section."""
        doc_changes = data.get("doc_changes", [])
        spec_updates = data.get("spec_updates", [])
        learnings = data.get("new_learnings", [])
        
        if not any([doc_changes, spec_updates, learnings]):
            return ""
        
        lines = ["## [U+1F4DA] Documentation Updates"]
        
        if doc_changes:
            lines.append("\n### Updated Docs")
            for doc in doc_changes[:3]:
                lines.append(f"- **{doc['file']}**: {doc['summary']}")
        
        if learnings:
            lines.append("\n### New Learnings")
            for learning in learnings[:3]:
                lines.append(f"- **{learning['category']}**: {learning['problem'][:50]}...")
        
        return "\n".join(lines)
    
    def format_action_items(self, data: Dict) -> str:
        """Extract and format actionable next steps."""
        lines = ["##  PASS:  Action Items"]
        
        # Generate action items based on data
        if data.get("test_failures"):
            lines.append("- **Fix failing tests** before next deployment")
        
        if data.get("compliance_violations", 0) > 10:
            lines.append("- **Refactor large files** to meet 450-line limit")
        
        if data.get("coverage_info", {}).get("delta", 0) < -5:
            lines.append("- **Add tests** to restore coverage levels")
        
        if len(lines) == 1:
            lines.append("- No urgent action items")
        
        return "\n".join(lines)
    
    def _make_readable(self, text: str) -> str:
        """Make technical text more readable."""
        # Remove common prefixes
        text = text.replace("_", " ")
        # Capitalize appropriately
        words = text.split()
        return " ".join(words).capitalize()[:100]