#!/usr/bin/env python3
"""
Command line interface for code review system.
Handles argument parsing and display formatting.
"""

import argparse
import sys
from typing import Any

from .core import ReviewConfig, ReviewData


class CLIHandler:
    """Handles command line interface operations"""
    
    @staticmethod
    def create_argument_parser() -> argparse.ArgumentParser:
        """Create and configure argument parser"""
        parser = argparse.ArgumentParser(description="Run comprehensive code review")
        CLIHandler._add_mode_arguments(parser)
        CLIHandler._add_focus_arguments(parser)
        CLIHandler._add_other_arguments(parser)
        return parser
    
    @staticmethod
    def _add_mode_arguments(parser: argparse.ArgumentParser) -> None:
        """Add mode-related arguments"""
        parser.add_argument(
            "--mode",
            choices=["quick", "standard", "full", "ai-focus"],
            default="standard",
            help="Review mode (quick=5min, standard=10min, full=15min)"
        )
    
    @staticmethod
    def _add_focus_arguments(parser: argparse.ArgumentParser) -> None:
        """Add focus-related arguments"""
        parser.add_argument(
            "--focus",
            choices=["ai-issues", "security", "performance", "spec-alignment"],
            help="Focus area for targeted review"
        )
    
    @staticmethod
    def _add_other_arguments(parser: argparse.ArgumentParser) -> None:
        """Add other arguments"""
        parser.add_argument(
            "--recent-commits", type=int, default=20,
            help="Number of recent commits to analyze"
        )
        parser.add_argument(
            "--report", action="store_true",
            help="Generate detailed report (automatic in full mode)"
        )
    
    @staticmethod
    def create_config_from_args(args: Any) -> ReviewConfig:
        """Create review configuration from parsed arguments"""
        return ReviewConfig(
            mode=args.mode,
            focus=args.focus,
            recent_commits=args.recent_commits
        )


class DisplayFormatter:
    """Handles display formatting for review results"""
    
    @staticmethod
    def print_header(config: ReviewConfig) -> None:
        """Print review header information"""
        print("=" * 60)
        print("NETRA CODE REVIEW SYSTEM")
        print(f"   Mode: {config.mode.upper()}")
        if config.focus:
            print(f"   Focus: {config.focus}")
        print("=" * 60)
    
    @staticmethod
    def display_summary(review_data: ReviewData) -> None:
        """Display review summary"""
        print("\n" + "=" * 60)
        print("REVIEW SUMMARY")
        print("=" * 60)
        DisplayFormatter._display_critical_issues(review_data)
        DisplayFormatter._display_high_issues(review_data)
        DisplayFormatter._display_totals(review_data)
    
    @staticmethod
    def _display_critical_issues(review_data: ReviewData) -> None:
        """Display critical issues summary"""
        critical_issues = review_data.issue_tracker.get_issues_by_severity("critical")
        if len(critical_issues) > 0:
            print(f"[CRITICAL] Issues: {len(critical_issues)}")
            for issue in critical_issues[:3]:
                print(f"   - {issue.description}")
    
    @staticmethod
    def _display_high_issues(review_data: ReviewData) -> None:
        """Display high priority issues summary"""
        high_issues = review_data.issue_tracker.get_issues_by_severity("high")
        if len(high_issues) > 0:
            print(f"[HIGH] Priority Issues: {len(high_issues)}")
            for issue in high_issues[:3]:
                print(f"   - {issue.description}")
    
    @staticmethod
    def _display_totals(review_data: ReviewData) -> None:
        """Display total issues count"""
        counts = review_data.issue_tracker.get_counts_by_severity()
        total_issues = review_data.issue_tracker.get_total_count()
        print(f"\n[TOTAL] Issues Found: {total_issues}")
        print(f"   Critical: {counts['critical']}")
        print(f"   High: {counts['high']}")
        print(f"   Medium: {counts['medium']}")
        print(f"   Low: {counts['low']}")
    
    @staticmethod
    def determine_final_status(review_data: ReviewData) -> bool:
        """Determine and display final review status"""
        if review_data.issue_tracker.has_critical_issues():
            print("\n[FAILED] Review FAILED - Critical issues must be addressed")
            return False
        elif review_data.issue_tracker.has_high_issues():
            print("\n[WARNING] Review PASSED with warnings - Many high priority issues")
            return True
        else:
            print("\n[PASSED] Review PASSED")
            return True
    
    @staticmethod
    def handle_exit_code(success: bool) -> None:
        """Exit with appropriate code"""
        sys.exit(0 if success else 1)