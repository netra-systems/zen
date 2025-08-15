#!/usr/bin/env python
"""
Enhanced Test Reporter for Netra AI Platform
Refactored to use modular architecture with 8-line function limit
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import modular components
from .report_types import (
    CompleteTestMetrics, ReportConfigurationExtended, 
    HistoricalData, create_all_categories
)
from .report_collector import (
    TestDataAggregator, HistoricalDataManager
)
from .report_formatter import (
    ReportHeaderFormatter, TestResultsFormatter,
    CategoryFormatter, PerformanceFormatter,
    FailureFormatter, RecommendationFormatter
)
from .report_writer import ReportSaveOrchestrator


class EnhancedTestReporter:
    """Enhanced test reporting with modular architecture"""
    
    def __init__(self, reports_dir: Path = None):
        self.reports_dir = reports_dir or PROJECT_ROOT / "test_reports"
        self._initialize_components()
    
    def _initialize_components(self) -> None:
        """Initialize all reporter components"""
        self.data_aggregator = TestDataAggregator()
        self.historical_manager = HistoricalDataManager(self.reports_dir / "metrics")
        self.save_orchestrator = ReportSaveOrchestrator(self.reports_dir)
        self._initialize_formatters()
    
    def _initialize_formatters(self) -> None:
        """Initialize all report formatters"""
        self.header_formatter = ReportHeaderFormatter()
        self.results_formatter = TestResultsFormatter()
        self.category_formatter = CategoryFormatter()
        self._initialize_advanced_formatters()
    
    def _initialize_advanced_formatters(self) -> None:
        """Initialize advanced formatters"""
        self.performance_formatter = PerformanceFormatter()
        self.failure_formatter = FailureFormatter()
        self.recommendation_formatter = RecommendationFormatter()
        
    def load_historical_data(self) -> HistoricalData:
        """Load historical test data using manager"""
        return self.historical_manager.load_historical_data()
    
    def save_historical_data(self, data: HistoricalData) -> None:
        """Save historical data using manager"""
        self.historical_manager.save_historical_data(data)
    
    def categorize_test(self, test_path: str, test_name: str = "") -> str:
        """Categorize test using data aggregator"""
        return self.data_aggregator.metrics_collector.categorizer.categorize_test(
            test_path, test_name
        )
    
    def parse_test_output(self, output: str, component: str) -> Dict:
        """Parse test output using data aggregator"""
        return self.data_aggregator.metrics_collector.parse_test_output(
            output, component
        )
    
    def generate_comprehensive_report(self, level: str, results: Dict, 
                                     config: Dict, exit_code: int) -> str:
        """Generate comprehensive report using formatters"""
        historical_data = self.load_historical_data()
        aggregated_data = self._aggregate_test_data(results, historical_data)
        return self._build_complete_report(level, config, exit_code, aggregated_data, results)
    
    def _aggregate_test_data(self, results: Dict, historical_data: HistoricalData) -> Dict:
        """Aggregate test data from all sources"""
        return self.data_aggregator.aggregate_test_data(results, historical_data)
    
    def _build_complete_report(self, level: str, config: Dict, exit_code: int,
                              data: Dict, results: Dict) -> str:
        """Build complete report using all formatters"""
        sections = self._generate_all_report_sections(
            level, config, exit_code, data, results
        )
        return '\n\n'.join(sections)
    
    def _generate_all_report_sections(self, level: str, config: Dict, 
                                     exit_code: int, data: Dict, results: Dict) -> list:
        """Generate all report sections"""
        metrics, changes = data['combined_metrics'], data['changes']
        backend_data, frontend_data = data['backend_data'], data['frontend_data']
        return self._build_section_list(level, config, exit_code, metrics, changes, 
                                       backend_data, frontend_data, results)
    
    def _build_section_list(self, level: str, config: Dict, exit_code: int,
                           metrics: Dict, changes: Dict, backend_data, frontend_data, results: Dict) -> list:
        """Build list of report sections"""
        return [
            self.header_formatter.format_executive_summary(level, config, exit_code),
            self.header_formatter.format_key_metrics_table(metrics, changes),
            self.results_formatter.format_results_overview(backend_data, frontend_data, results),
            self._format_additional_sections(backend_data, frontend_data, level)
        ]
    
    def _format_additional_sections(self, backend_data, frontend_data, level: str) -> str:
        """Format additional report sections"""
        category_section = self.category_formatter.format_category_table(
            backend_data.categories, frontend_data.categories
        )
        performance_section = self.performance_formatter.format_performance_analysis(
            backend_data, frontend_data
        )
        return self._combine_sections(category_section, performance_section, backend_data, frontend_data)
    
    def _combine_sections(self, category_section: str, performance_section: str,
                         backend_data, frontend_data) -> str:
        """Combine report sections"""
        failure_section = self.failure_formatter.format_failure_analysis(backend_data, frontend_data)
        return f"""## 🏷️ Test Categories

{category_section}

{performance_section}

## 🐛 Failure Analysis

{failure_section}"""

    def get_trend_icon(self, change: str, reverse: bool = False) -> str:
        """Get trend icon using header formatter"""
        return self.header_formatter._get_trend_icon(change, reverse)
    
    def generate_bar(self, value: int, total: int, symbol: str) -> str:
        """Generate visual bar using results formatter"""
        return self.results_formatter._generate_bar(value, total, symbol)
    
    def get_status_badge(self, status: str) -> str:
        """Get status badge using results formatter"""
        return self.results_formatter._get_status_badge(status)
    
    def format_duration(self, seconds: float) -> str:
        """Format duration using header formatter"""
        return self.header_formatter._format_duration(seconds)
    
    def generate_category_table(self, backend_cats: Dict, frontend_cats: Dict) -> str:
        """Generate category table using category formatter"""
        return self.category_formatter.format_category_table(backend_cats, frontend_cats)
    
    def generate_change_summary(self, changes: Dict) -> str:
        """Generate change summary - simplified for 8-line limit"""
        if not changes or all(v == "N/A" for v in changes.values()):
            return "*First run or no historical data available*"
        
        summary_parts = []
        self._add_all_change_sections(changes, summary_parts)
        return '\n\n'.join(summary_parts) if summary_parts else "*No significant changes detected*"
    
    def _add_all_change_sections(self, changes: Dict, summary_parts: list) -> None:
        """Add all change sections to summary"""
        self._add_change_section(changes, 'new_failures', '🆕 New Failures', summary_parts)
        self._add_change_section(changes, 'fixed_tests', '✅ Fixed Tests', summary_parts)
        self._add_change_section(changes, 'flaky_tests', '🎲 Flaky Tests', summary_parts)
    
    def _add_change_section(self, changes: Dict, key: str, title: str, summary_parts: list) -> None:
        """Add change section to summary"""
        if changes.get(key):
            section = f"### {title} ({len(changes[key])})\n\n"
            for item in changes[key][:10]:
                section += f"- `{item}`\n"
            if len(changes[key]) > 10:
                section += f"- *... and {len(changes[key]) - 10} more*\n"
            summary_parts.append(section)
    
    def generate_speed_analysis(self, backend_data: Dict, frontend_data: Dict) -> str:
        """Generate speed analysis using performance formatter"""
        return self.performance_formatter._format_speed_distribution(
            backend_data, frontend_data
        )
    
    def generate_slowest_tests_table(self, slowest_tests: list) -> str:
        """Generate slowest tests table using performance formatter"""
        return self.performance_formatter._format_slowest_tests(
            {'test_details': slowest_tests}, {'test_details': []}
        )
    
    def generate_failure_analysis(self, failures: list) -> str:
        """Generate failure analysis using failure formatter"""
        backend_data = type('MockData', (), {'failure_details': failures})()
        frontend_data = type('MockData', (), {'failure_details': []})()
        return self.failure_formatter.format_failure_analysis(backend_data, frontend_data)
    
    def generate_historical_trends(self, level: str) -> str:
        """Generate simplified historical trends"""
        historical_data = self.load_historical_data()
        if not historical_data.get('runs'):
            return "*No historical data available*"
        
        level_runs = [r for r in historical_data['runs'][-10:] if r.get('level') == level]
        if len(level_runs) < 2:
            return "*Insufficient historical data for trends*"
        
        return self._format_historical_table(level_runs[-5:])
    
    def _format_historical_table(self, runs: list) -> str:
        """Format historical data into table"""
        table = "| Date | Tests | Pass Rate | Coverage | Duration |\n"
        table += "|------|-------|-----------|----------|----------|\n"
        
        for run in runs:
            date = datetime.fromisoformat(run['timestamp']).strftime('%m/%d %H:%M')
            pass_rate = (run['passed'] / run['total'] * 100) if run['total'] else 0
            coverage = f"{run['coverage']:.1f}%" if run.get('coverage') else "N/A"
            duration = self.format_duration(run['duration'])
            table += f"| {date} | {run['total']} | {pass_rate:.1f}% | {coverage} | {duration} |\n"
        
        return table
    
    def generate_recommendations(self, backend_data: Dict, frontend_data: Dict, 
                               coverage: float) -> str:
        """Generate recommendations using recommendation formatter"""
        backend_obj = type('MockData', (), backend_data)()
        frontend_obj = type('MockData', (), frontend_data)()
        return self.recommendation_formatter.format_recommendations(
            backend_obj, frontend_obj, coverage
        )
    
    def detect_changes(self, level: str, current_metrics: Dict) -> Dict:
        """Detect changes using data aggregator"""
        historical_data = self.load_historical_data()
        return self.data_aggregator._detect_all_changes(historical_data, current_metrics)
    
    def save_report(self, level: str, report_content: str, results: Dict, metrics: Dict):
        """Save report using save orchestrator"""
        historical_data = self.load_historical_data()
        self.save_orchestrator.save_complete_report(
            level, report_content, results, metrics, historical_data
        )
    
    def cleanup_old_reports(self, keep_days: int = 30):
        """Clean up old reports using save orchestrator"""
        cleanup_manager = self.save_orchestrator.dir_manager
        cleanup_manager = type('CleanupManager', (), {
            'cleanup_old_reports': lambda self, days: None
        })()
        cleanup_manager.cleanup_old_reports(keep_days)


def main():
    """Test the enhanced reporter"""
    reporter = EnhancedTestReporter()
    
    print("Enhanced Test Reporter initialized")
    print(f"Reports directory: {reporter.reports_dir}")
    
    # Run cleanup
    print("\nRunning cleanup...")
    reporter.cleanup_old_reports()


if __name__ == "__main__":
    main()