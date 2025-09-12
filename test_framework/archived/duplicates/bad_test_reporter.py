#!/usr/bin/env python
"""Bad Test Reporter - Command-line tool for viewing bad test reports.

Usage:
    python -m test_framework.bad_test_reporter [options]
    
Options:
    --summary       Show summary statistics only
    --details       Show detailed test histories
    --reset         Reset bad test data
    --test NAME     Show history for specific test
    --export        Export report to file
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from test_framework.archived.duplicates.bad_test_detector import BadTestDetector


def main():
    """Main entry point for bad test reporter."""
    args = parse_arguments()
    reporter = BadTestReporter()
    reporter.run(args)


class BadTestReporter:
    """Command-line reporter for bad tests."""
    
    def __init__(self):
        """Initialize the reporter."""
        self.detector = BadTestDetector()
    
    def run(self, args):
        """Run the reporter with given arguments.
        
        Args:
            args: Parsed command-line arguments
        """
        if args.reset:
            self._handle_reset(args.reset_test)
        elif args.test:
            self._show_test_history(args.test)
        elif args.summary:
            self._show_summary()
        elif args.export:
            self._export_report(args.export)
        else:
            self._show_full_report(args.details)
    
    def _handle_reset(self, test_name: Optional[str]):
        """Handle reset operation.
        
        Args:
            test_name: Specific test to reset (None for all)
        """
        if test_name:
            print(f"Resetting data for test: {test_name}")
            self.detector.reset_test_data(test_name)
            print("Test data reset successfully")
        else:
            response = input("Are you sure you want to reset ALL bad test data? (yes/no): ")
            if response.lower() == "yes":
                self.detector.reset_test_data()
                print("All bad test data reset successfully")
            else:
                print("Reset cancelled")
    
    def _show_test_history(self, test_name: str):
        """Show detailed history for a specific test.
        
        Args:
            test_name: Test name to show history for
        """
        history = self.detector.get_test_history(test_name)
        
        if not history:
            print(f"No history found for test: {test_name}")
            return
        
        print("\n" + "=" * 80)
        print(f"TEST HISTORY: {test_name}")
        print("=" * 80)
        
        self._print_test_stats(history)
        self._print_recent_failures(history)
    
    def _print_test_stats(self, history: dict):
        """Print test statistics.
        
        Args:
            history: Test history data
        """
        total = history["total_failures"] + history["total_passes"]
        failure_rate = history["total_failures"] / total if total > 0 else 0
        
        print(f"\nComponent: {history['component']}")
        print(f"First seen: {history['first_seen']}")
        print(f"Total runs: {total}")
        print(f"Failures: {history['total_failures']}")
        print(f"Passes: {history['total_passes']}")
        print(f"Failure rate: {failure_rate:.1%}")
        print(f"Consecutive failures: {history['consecutive_failures']}")
        
        if history.get("marked_as_bad"):
            print(f" WARNING: [U+FE0F]  MARKED AS BAD: {history.get('bad_reason', 'Unknown reason')}")
    
    def _print_recent_failures(self, history: dict):
        """Print recent failures.
        
        Args:
            history: Test history data
        """
        if not history.get("recent_failures"):
            return
        
        print("\nRecent Failures:")
        print("-" * 40)
        
        for failure in history["recent_failures"][-5:]:  # Show last 5
            timestamp = failure.get("timestamp", "Unknown")
            error_type = failure.get("error_type", "Unknown")
            error_msg = failure.get("error_message", "No message")
            
            print(f"\n  {timestamp}")
            print(f"  Type: {error_type}")
            print(f"  Message: {error_msg[:200]}")
    
    def _show_summary(self):
        """Show summary statistics."""
        stats = self.detector.get_statistics()
        
        print("\n" + "=" * 80)
        print("BAD TEST SUMMARY")
        print("=" * 80)
        
        print(f"\nTotal tracked tests: {stats['total_tracked_tests']}")
        print(f"Total test runs: {stats['total_runs']}")
        print(f"Consistently failing: {stats['consistently_failing']}")
        print(f"High failure rate: {stats['high_failure_rate']}")
        
        if stats.get("last_updated"):
            print(f"\nLast updated: {stats['last_updated']}")
        
        print("\n" + "=" * 80)
    
    def _show_full_report(self, detailed: bool = False):
        """Show full bad test report.
        
        Args:
            detailed: Whether to include detailed test histories
        """
        report = self.detector.get_bad_test_report()
        print(report)
        
        if detailed:
            self._show_detailed_histories()
    
    def _show_detailed_histories(self):
        """Show detailed histories for all bad tests."""
        bad_tests = self.detector._identify_bad_tests()
        all_bad_tests = set()
        
        for category in ["consistently_failing", "high_failure_rate"]:
            for test in bad_tests.get(category, []):
                all_bad_tests.add(test["test"])
        
        if not all_bad_tests:
            return
        
        print("\n" + "=" * 80)
        print("DETAILED TEST HISTORIES")
        print("=" * 80)
        
        for test_name in sorted(all_bad_tests):
            history = self.detector.get_test_history(test_name)
            if history:
                print(f"\n{test_name}:")
                print("-" * len(test_name))
                self._print_test_stats(history)
    
    def _export_report(self, filename: str):
        """Export report to file.
        
        Args:
            filename: Output filename
        """
        output_path = Path(filename)
        
        # Get all data
        stats = self.detector.get_statistics()
        bad_tests = self.detector._identify_bad_tests()
        report_text = self.detector.get_bad_test_report()
        
        # Create export data
        export_data = {
            "generated": datetime.now().isoformat(),
            "statistics": stats,
            "bad_tests": bad_tests,
            "report": report_text
        }
        
        # Write based on extension
        if output_path.suffix == ".json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, default=str)
        else:
            # Write as text
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_text)
        
        print(f"Report exported to: {output_path}")


def parse_arguments():
    """Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="Bad Test Reporter - View and manage bad test detection data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show full report
  python -m test_framework.bad_test_reporter
  
  # Show summary only
  python -m test_framework.bad_test_reporter --summary
  
  # Show detailed histories
  python -m test_framework.bad_test_reporter --details
  
  # Show history for specific test
  python -m test_framework.bad_test_reporter --test "app/tests/test_auth.py::test_login"
  
  # Export report to file
  python -m test_framework.bad_test_reporter --export bad_tests_report.txt
  
  # Reset all data
  python -m test_framework.bad_test_reporter --reset
  
  # Reset specific test
  python -m test_framework.bad_test_reporter --reset --reset-test "app/tests/test_auth.py::test_login"
        """
    )
    
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Show summary statistics only"
    )
    
    parser.add_argument(
        "--details", "-d",
        action="store_true",
        help="Include detailed test histories in report"
    )
    
    parser.add_argument(
        "--test", "-t",
        help="Show history for specific test"
    )
    
    parser.add_argument(
        "--reset", "-r",
        action="store_true",
        help="Reset bad test data"
    )
    
    parser.add_argument(
        "--reset-test",
        help="Specific test to reset (use with --reset)"
    )
    
    parser.add_argument(
        "--export", "-e",
        help="Export report to file (supports .txt and .json)"
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    main()