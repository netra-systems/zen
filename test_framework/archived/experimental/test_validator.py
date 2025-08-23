#!/usr/bin/env python3
"""
Test Validator Module
Orchestrates test execution, validation, and report generation
Complies with 450-line limit and 25-line function constraint
"""

from pathlib import Path
from typing import Any, Dict, List

# Import modular components
from test_framework.archived.experimental.test_executor import AutonomousReviewRunner, TestExecutionResult, TestExecutor
from test_framework.archived.experimental.test_reporter import ReportGenerator, TestProgressMonitor


class TestValidator:
    """Main test validation orchestrator"""
    
    __test__ = False  # Tell pytest this is not a test class
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.executor = TestExecutor(project_root)
        self.review_runner = AutonomousReviewRunner(project_root)
        self.report_generator = ReportGenerator(project_root)
        self.progress_monitor = TestProgressMonitor(project_root)

    async def validate_test_suite(self) -> TestExecutionResult:
        """Execute comprehensive test suite validation"""
        return await self.executor.run_comprehensive_tests()

    async def validate_unit_tests(self) -> TestExecutionResult:
        """Execute unit test validation"""
        return await self.executor.run_unit_tests()

    async def run_autonomous_review(self, ultra_think: bool = False) -> bool:
        """Execute autonomous review system"""
        if ultra_think:
            return await self.review_runner.run_comprehensive_review()
        return await self.review_runner.run_quick_review()

    async def generate_reports(self, metrics: Dict[str, Any]) -> List[Path]:
        """Generate comprehensive test reports"""
        reports = []
        
        coverage_report = await self.report_generator.generate_coverage_report(metrics)
        reports.append(coverage_report)
        
        return reports

    async def monitor_progress(self, metrics: Dict[str, Any]) -> None:
        """Monitor and display test progress"""
        current_coverage = metrics.get("coverage_percentage", 0.0)
        
        await self.progress_monitor.display_progress(current_coverage)
        await self.progress_monitor.show_trends()
        await self.progress_monitor.show_warnings(metrics)

    async def validate_and_report(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Execute validation and generate comprehensive reports"""
        # Run test validation
        test_result = await self.validate_test_suite()
        
        # Generate reports
        report_paths = await self.generate_reports(metrics)
        
        # Monitor progress
        await self.monitor_progress(metrics)
        
        return {
            "test_execution": test_result,
            "reports_generated": len(report_paths),
            "validation_success": test_result.success
        }