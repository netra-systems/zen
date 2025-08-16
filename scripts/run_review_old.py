#!/usr/bin/env python3
"""
Comprehensive Code Review Script
ULTRA DEEP THINK: Module-based architecture - Main coordinator ≤300 lines
Implements SPEC/review.xml for automated code quality validation
"""

import sys
import argparse
from pathlib import Path
from code_review_analyzer import CodeReviewAnalyzer
from code_review_reporter import CodeReviewReporter

class CodeReviewer:
    """Main coordinator for code review process"""
    
    def __init__(self, mode: str = "full", focus: str = None, recent_commits: int = 20):
        self.mode = mode
        self.focus = focus
        self.recent_commits = recent_commits
        self.project_root = Path(__file__).parent.parent
        
        # Initialize analyzer and reporter
        self.analyzer = CodeReviewAnalyzer(self.project_root, mode, recent_commits)
        self.reporter = CodeReviewReporter(self.project_root)
    
    def run(self) -> bool:
        """Execute the complete review process"""
        self._print_header()
        if not self._run_smoke_tests_if_needed():
            return False
        self._run_analysis_steps()
        report = self._generate_and_save_report()
        self.reporter.display_summary(self.analyzer.issues)
        return self.reporter.determine_final_status(self.analyzer.issues)

    def _print_header(self) -> None:
        """Print review header information."""
        print("=" * 60)
        print("NETRA CODE REVIEW SYSTEM")
        print(f"   Mode: {self.mode.upper()}")
        if self.focus:
            print(f"   Focus: {self.focus}")
        print("=" * 60)

    def _run_smoke_tests_if_needed(self) -> bool:
        """Run smoke tests if needed and return success status."""
        if self.mode == "ai-focus":
            return True
        all_passed = self.analyzer.run_smoke_tests()
        if not all_passed and self.mode == "quick":
            print("\n❌ Critical smoke tests failed. Stopping review.")
            print("   Fix critical issues before continuing.")
            return False
        return True

    def _run_analysis_steps(self) -> None:
        """Run all analysis steps based on mode."""
        self.analyzer.analyze_recent_changes()
        if self.mode != "quick":
            self.analyzer.check_spec_code_alignment()
        self.analyzer.detect_ai_coding_issues()
        if self.mode == "full":
            self.analyzer.check_performance_issues()
        if self.mode != "quick":
            self.analyzer.check_security_issues()

    def _generate_and_save_report(self) -> str:
        """Generate and save the review report."""
        report = self.reporter.generate_report(
            self.mode, self.focus, self.analyzer.issues,
            self.analyzer.smoke_test_results, self.analyzer.recent_changes,
            self.analyzer.spec_code_conflicts, self.analyzer.ai_issues_found,
            self.analyzer.performance_concerns, self.analyzer.security_issues
        )
        self.reporter.save_report(report)
        return report


def main():
    """Main entry point for code review script"""
    parser = argparse.ArgumentParser(description="Run comprehensive code review")
    parser.add_argument(
        "--mode",
        choices=["quick", "standard", "full", "ai-focus"],
        default="standard",
        help="Review mode (quick=5min, standard=10min, full=15min)"
    )
    parser.add_argument(
        "--focus",
        choices=["ai-issues", "security", "performance", "spec-alignment"],
        help="Focus area for targeted review"
    )
    parser.add_argument(
        "--recent-commits",
        type=int,
        default=20,
        help="Number of recent commits to analyze"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate detailed report (automatic in full mode)"
    )
    
    args = parser.parse_args()
    
    # Create and run reviewer
    reviewer = CodeReviewer(
        mode=args.mode,
        focus=args.focus,
        recent_commits=args.recent_commits
    )
    
    success = reviewer.run()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()