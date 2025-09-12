#!/usr/bin/env python3
"""
Code review orchestrator.
Coordinates all review modules and manages the review workflow.
"""

from scripts.review.ai_detector import AIDetector
from scripts.review.cli import DisplayFormatter
from scripts.review.command_runner import CommandRunner
from scripts.review.core import ReviewConfig, ReviewData, create_review_data
from scripts.review.git_analyzer import GitAnalyzer
from scripts.review.performance_checker import PerformanceChecker
from scripts.review.report_generator import ReportGenerator
from scripts.review.security_checker import SecurityChecker
from scripts.review.smoke_tester import SmokeTester
from scripts.review.spec_checker import SpecChecker


class CodeReviewer:
    """Orchestrates the complete code review process"""
    
    def __init__(self, config: ReviewConfig):
        self.config = config
        self.review_data = create_review_data()
        self.command_runner = CommandRunner(config)
        self._initialize_checkers()
    
    def _initialize_checkers(self) -> None:
        """Initialize all checker modules"""
        self.smoke_tester = SmokeTester(self.config, self.command_runner)
        self.git_analyzer = GitAnalyzer(self.config, self.command_runner)
        self.spec_checker = SpecChecker(self.config, self.command_runner)
        self.ai_detector = AIDetector(self.config, self.command_runner)
        self.performance_checker = PerformanceChecker(self.config, self.command_runner)
        self.security_checker = SecurityChecker(self.config, self.command_runner)
        self.report_generator = ReportGenerator(self.config)
    
    def run(self) -> bool:
        """Execute the complete review process"""
        DisplayFormatter.print_header(self.config)
        if not self._run_smoke_tests_if_needed():
            return False
        self._run_analysis_steps()
        report = self.report_generator.generate_report(self.review_data)
        DisplayFormatter.display_summary(self.review_data)
        self.report_generator.save_report(report)
        return DisplayFormatter.determine_final_status(self.review_data)
    
    def _run_smoke_tests_if_needed(self) -> bool:
        """Run smoke tests if needed and return success status"""
        if not self.config.should_run_smoke_tests():
            return True
        all_passed = self.smoke_tester.run_all_smoke_tests(self.review_data)
        if not all_passed and self.config.is_quick_mode():
            print("\n FAIL:  Critical smoke tests failed. Stopping review.")
            print("   Fix critical issues before continuing.")
            return False
        return True
    
    def _run_analysis_steps(self) -> None:
        """Run all analysis steps based on configuration"""
        self.git_analyzer.analyze_recent_changes(self.review_data)
        if self.config.should_run_spec_check():
            self.spec_checker.check_spec_code_alignment(self.review_data)
        self.ai_detector.detect_ai_coding_issues(self.review_data)
        if self.config.should_run_performance_check():
            self.performance_checker.check_performance_issues(self.review_data)
        if self.config.should_run_security_check():
            self.security_checker.check_security_issues(self.review_data)