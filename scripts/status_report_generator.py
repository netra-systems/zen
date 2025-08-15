#!/usr/bin/env python3
"""
System Status Report Generator - Main Module
Orchestrates status report generation using modular architecture.
Complies with 300-line and 8-line function limits.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from .status_types import StatusConfig, StatusReportData
    from .status_collector import (
        StatusDataCollector, ComponentHealthCollector, 
        WipItemsCollector, TestResultsCollector
    )
    from .status_analyzer import (
        IntegrationAnalyzer, AgentSystemAnalyzer, 
        TestCoverageAnalyzer, HealthScoreCalculator
    )
    from .status_renderer import StatusReportRenderer
except ImportError:
    from status_types import StatusConfig, StatusReportData
    from status_collector import (
        StatusDataCollector, ComponentHealthCollector, 
        WipItemsCollector, TestResultsCollector
    )
    from status_analyzer import (
        IntegrationAnalyzer, AgentSystemAnalyzer, 
        TestCoverageAnalyzer, HealthScoreCalculator
    )
    from status_renderer import StatusReportRenderer


class StatusReportGenerator:
    """Main status report orchestrator"""
    
    def __init__(self, spec_path: str = "SPEC/Status.xml"):
        self.config = StatusConfig(
            project_root=Path(__file__).parent.parent,
            spec_path=spec_path
        )
        self._initialize_collectors()
        self._initialize_analyzers()
        self.renderer = StatusReportRenderer()
    
    def _initialize_collectors(self):
        """Initialize data collectors"""
        self.data_collector = StatusDataCollector(self.config)
        self.health_collector = ComponentHealthCollector(self.data_collector)
        self.wip_collector = WipItemsCollector(self.data_collector)
        self.test_collector = TestResultsCollector(self.config)
    
    def _initialize_analyzers(self):
        """Initialize status analyzers"""
        self.integration_analyzer = IntegrationAnalyzer(self.config)
        self.agent_analyzer = AgentSystemAnalyzer(self.config)
        self.coverage_analyzer = TestCoverageAnalyzer(self.config)
        self.health_calculator = HealthScoreCalculator()
    
    def generate_report(self) -> str:
        """Generate complete status report"""
        spec = self.data_collector.load_spec_root()
        data = self._gather_report_data(spec)
        health_score = self._calculate_health_score(data)
        return self.renderer.build_complete_report(data, health_score)
    
    def _gather_report_data(self, spec) -> StatusReportData:
        """Gather all data for report"""
        component_health = self.health_collector.analyze_component_health(spec)
        wip_items = self.wip_collector.collect_wip_items(spec)
        integration_status = self.integration_analyzer.check_integration_status()
        agent_status = self.agent_analyzer.check_agent_system()
        test_coverage = self.coverage_analyzer.check_test_coverage()
        test_results = self.test_collector.run_quick_tests()
        
        return StatusReportData(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            component_health=component_health,
            wip_items=wip_items,
            integration_status=integration_status,
            agent_status=agent_status,
            test_coverage=test_coverage,
            test_results=test_results
        )
    
    def _calculate_health_score(self, data: StatusReportData) -> int:
        """Calculate overall health score"""
        return self.health_calculator.calculate_health_score(
            data.component_health,
            data.integration_status,
            data.test_results
        )
    
    def save_report(self, report: str, filename: str = None) -> tuple:
        """Save report to files"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_status_report_{timestamp}.md"
        
        reports_dir = self.config.project_root / "reports"
        reports_dir.mkdir(exist_ok=True)
        
        report_path = reports_dir / filename
        latest_path = reports_dir / "system_status_report.md"
        
        self._write_report_file(report_path, report)
        self._write_report_file(latest_path, report)
        
        return report_path, latest_path
    
    def _write_report_file(self, file_path: Path, content: str):
        """Write report content to file"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)


def main():
    """Main execution function"""
    print("System Status Report Generator")
    print("=" * 50)
    
    generator = StatusReportGenerator()
    
    print("Analyzing codebase according to Status.xml specification...")
    report = generator.generate_report()
    
    print("Saving report...")
    report_path, latest_path = generator.save_report(report)
    
    _print_completion_message(report_path, latest_path)
    _print_report_summary(report)
    
    return 0


def _print_completion_message(report_path, latest_path):
    """Print completion message"""
    print(f"\nReport generated successfully!")
    print(f"- Full report: {report_path}")
    print(f"- Latest report: {latest_path}")


def _print_report_summary(report: str):
    """Print report summary"""
    lines = report.split('\n')
    for line in lines[:30]:  # Print first 30 lines as summary
        print(line)
    print("\n... (see full report for complete details)")


if __name__ == "__main__":
    exit(main())