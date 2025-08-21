"""Team Updates Orchestrator - Main coordinator for generating team updates."""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from team_updates_compliance_analyzer import ComplianceAnalyzer
from team_updates_documentation_analyzer import DocumentationAnalyzer
from team_updates_formatter import HumanFormatter
from team_updates_git_analyzer import GitAnalyzer
from team_updates_test_analyzer import TestReportAnalyzer


class TeamUpdatesOrchestrator:
    """Orchestrates generation of team update reports."""
    
    def __init__(self, project_root: Path = Path.cwd()):
        """Initialize orchestrator with analyzers."""
        self.project_root = project_root
        self.git_analyzer = GitAnalyzer(project_root)
        self.test_analyzer = TestReportAnalyzer(project_root)
        self.compliance_analyzer = ComplianceAnalyzer(project_root)
        self.doc_analyzer = DocumentationAnalyzer(project_root)
        self.formatter = HumanFormatter()
    
    async def generate_update(self, time_frame: str = "last_day") -> str:
        """Generate complete team update for time frame."""
        start_time, end_time = self.get_time_range(time_frame)
        report_id = str(uuid4())[:8]
        
        data = await self._collect_all_data(start_time, end_time)
        prioritized = self.prioritize_changes(data)
        formatted = self.formatter.format_full_report(
            prioritized, time_frame, report_id
        )
        return formatted
    
    def get_time_range(self, time_frame: str) -> tuple[datetime, datetime]:
        """Convert time frame to datetime range."""
        end_time = datetime.now()
        hours_map = {
            "last_hour": 1, "last_5_hours": 5,
            "last_day": 24, "last_week": 168,
            "last_month": 720
        }
        hours = hours_map.get(time_frame, 24)
        start_time = end_time - timedelta(hours=hours)
        return start_time, end_time
    
    def prioritize_changes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sort changes by criticality."""
        critical = self._extract_critical_issues(data)
        data["critical_alerts"] = critical
        data["priority_order"] = self._calculate_priorities(data)
        return data
    
    async def _collect_all_data(
        self, start: datetime, end: datetime
    ) -> Dict[str, Any]:
        """Collect data from all analyzers."""
        tasks = [
            self.git_analyzer.analyze(start, end),
            self.test_analyzer.analyze(start, end),
            self.compliance_analyzer.analyze(start, end),
            self.doc_analyzer.analyze(start, end)
        ]
        results = await asyncio.gather(*tasks)
        return self._merge_results(results)
    
    def _extract_critical_issues(self, data: Dict) -> List[Dict]:
        """Extract critical issues needing immediate attention."""
        critical = []
        if len(data.get("test_failures", [])) > 5:
            critical.append({"type": "tests", "message": "Multiple test failures"})
        if data.get("compliance_violations", 0) > 10:
            critical.append({"type": "compliance", "message": "Architecture violations"})
        return critical
    
    def _calculate_priorities(self, data: Dict) -> List[str]:
        """Calculate section display priorities."""
        priorities = ["critical_alerts", "executive_summary"]
        if data.get("features"): priorities.append("features")
        if data.get("bugs"): priorities.append("bugs")
        priorities.extend(["test_health", "code_quality", "documentation"])
        return priorities
    
    def _merge_results(self, results: List[Dict]) -> Dict[str, Any]:
        """Merge results from all analyzers."""
        merged = {}
        for result in results:
            merged.update(result)
        return merged


async def main():
    """CLI entry point for team updates."""
    import argparse
    parser = argparse.ArgumentParser(description="Generate team update report")
    parser.add_argument(
        "--time-frame", default="last_day",
        choices=["last_hour", "last_5_hours", "last_day", "last_week", "last_month"]
    )
    parser.add_argument("--output", help="Output file path")
    args = parser.parse_args()
    
    orchestrator = TeamUpdatesOrchestrator()
    report = await orchestrator.generate_update(args.time_frame)
    
    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)


if __name__ == "__main__":
    asyncio.run(main())