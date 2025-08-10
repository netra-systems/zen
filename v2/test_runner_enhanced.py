#!/usr/bin/env python
"""
Enhanced test runner for Netra AI Platform with test counts and history tracking
"""

import os
import sys
import json
import time
import argparse
import subprocess
import threading
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Project root directory
PROJECT_ROOT = Path(__file__).parent

# Test configurations for different modes
TEST_CONFIGS = {
    "quick": {
        "description": "Quick smoke tests (< 1 minute)",
        "backend_args": ["--category", "smoke", "--fail-fast", "--quiet"],
        "frontend_args": ["--category", "smoke"],
    },
    "standard": {
        "description": "Standard test suite (~ 5 minutes)",
        "backend_args": ["--category", "unit", "--category", "integration"],
        "frontend_args": ["--category", "unit", "--category", "components"],
    },
    "comprehensive": {
        "description": "Comprehensive test suite with coverage (~ 10 minutes)",
        "backend_args": ["--coverage", "--parallel", "auto"],
        "frontend_args": ["--coverage", "--lint", "--type-check"],
    },
    "ci": {
        "description": "Full CI/CD pipeline (~ 15 minutes)",
        "backend_args": ["--coverage", "--min-coverage", "70", "--parallel", "auto"],
        "frontend_args": ["--coverage", "--lint", "--type-check", "--e2e"],
    },
    "critical": {
        "description": "Critical path tests only",
        "backend_args": ["--category", "critical"],
        "frontend_args": ["--category", "critical"],
    }
}


class TestRunner:
    """Enhanced test runner with test counts and history tracking"""
    
    def __init__(self):
        self.results = {
            "backend": {"status": "pending", "duration": 0, "exit_code": None, "test_counts": {}},
            "frontend": {"status": "pending", "duration": 0, "exit_code": None, "test_counts": {}},
            "overall": {"status": "pending", "start_time": None, "end_time": None},
        }
        self.reports_dir = PROJECT_ROOT / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_file = self.reports_dir / "test_history.json"
    
    def parse_test_output(self, output_str):
        """Parse test output for pass/fail counts"""
        counts = {'passed': 0, 'failed': 0, 'skipped': 0, 'errors': 0, 'total': 0}
        
        # Try to parse pytest summary line
        # Match patterns like "5 passed, 2 failed, 1 skipped"
        pattern = r'(\d+)\s+(passed|failed|skipped|error|errors)'
        matches = re.findall(pattern, output_str.lower())
        
        for count, status in matches:
            if 'passed' in status:
                counts['passed'] = int(count)
            elif 'failed' in status:
                counts['failed'] = int(count)
            elif 'skipped' in status:
                counts['skipped'] = int(count)
            elif 'error' in status:
                counts['errors'] = int(count)
        
        counts['total'] = counts['passed'] + counts['failed'] + counts['skipped'] + counts['errors']
        return counts
    
    def load_test_history(self):
        """Load test history from file"""
        if self.history_file.exists():
            with open(self.history_file, 'r') as f:
                return json.load(f)
        return {
            "test_runs": [],
            "summary": {
                "total_runs": 0,
                "last_run": None,
                "success_rate": 0
            }
        }
    
    def save_test_history(self, test_result):
        """Save test result to history"""
        history = self.load_test_history()
        
        # Create history entry
        entry = {
            "timestamp": test_result["timestamp"],
            "mode": test_result["configuration"].get("mode", "custom"),
            "backend": {
                "status": test_result["results"]["backend"]["status"],
                "test_counts": test_result["results"]["backend"].get("test_counts", {}),
                "duration": test_result["results"]["backend"]["duration"]
            },
            "frontend": {
                "status": test_result["results"]["frontend"]["status"],
                "test_counts": test_result["results"]["frontend"].get("test_counts", {}),
                "duration": test_result["results"]["frontend"]["duration"]
            },
            "overall_passed": test_result["summary"]["overall_passed"]
        }
        
        # Add to history (keep last 100 runs)
        history["test_runs"].insert(0, entry)
        if len(history["test_runs"]) > 100:
            history["test_runs"] = history["test_runs"][:100]
        
        # Update summary
        history["summary"]["total_runs"] = len(history["test_runs"])
        history["summary"]["last_run"] = entry["timestamp"]
        
        # Calculate success rate
        successful_runs = sum(1 for run in history["test_runs"] if run["overall_passed"])
        history["summary"]["success_rate"] = (successful_runs / len(history["test_runs"]) * 100) if history["test_runs"] else 0
        
        # Save to file
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    def run_backend_tests(self, args: List[str]) -> int:
        """Run backend tests"""
        print("\n" + "=" * 80)
        print("RUNNING BACKEND TESTS")
        print("=" * 80)
        
        start_time = time.time()
        self.results["backend"]["status"] = "running"
        
        cmd = [sys.executable, "scripts/test_backend.py"] + args
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        # Parse test counts
        test_counts = self.parse_test_output(result.stdout + result.stderr)
        self.results["backend"]["test_counts"] = test_counts
        
        # Print output for visibility
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        duration = time.time() - start_time
        self.results["backend"]["duration"] = duration
        self.results["backend"]["exit_code"] = result.returncode
        self.results["backend"]["status"] = "passed" if result.returncode == 0 else "failed"
        
        return result.returncode
    
    def run_frontend_tests(self, args: List[str]) -> int:
        """Run frontend tests"""
        print("\n" + "=" * 80)
        print("RUNNING FRONTEND TESTS")
        print("=" * 80)
        
        start_time = time.time()
        self.results["frontend"]["status"] = "running"
        
        cmd = [sys.executable, "scripts/test_frontend.py"] + args
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        # Parse test counts
        test_counts = self.parse_test_output(result.stdout + result.stderr)
        self.results["frontend"]["test_counts"] = test_counts
        
        # Print output for visibility
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        duration = time.time() - start_time
        self.results["frontend"]["duration"] = duration
        self.results["frontend"]["exit_code"] = result.returncode
        self.results["frontend"]["status"] = "passed" if result.returncode == 0 else "failed"
        
        return result.returncode
    
    def run_parallel(self, backend_args: List[str], frontend_args: List[str]) -> Tuple[int, int]:
        """Run backend and frontend tests in parallel"""
        backend_result = [None]
        frontend_result = [None]
        
        def run_backend():
            backend_result[0] = self.run_backend_tests(backend_args)
        
        def run_frontend():
            frontend_result[0] = self.run_frontend_tests(frontend_args)
        
        backend_thread = threading.Thread(target=run_backend)
        frontend_thread = threading.Thread(target=run_frontend)
        
        backend_thread.start()
        frontend_thread.start()
        
        backend_thread.join()
        frontend_thread.join()
        
        return backend_result[0], frontend_result[0]
    
    def generate_test_report(self, mode=None, backend_only=False, frontend_only=False, parallel=False):
        """Generate comprehensive test report with counts"""
        # Calculate overall results
        overall_passed = (
            (self.results["backend"]["status"] == "passed" or backend_only) and
            (self.results["frontend"]["status"] == "passed" or frontend_only)
        )
        
        total_duration = self.results["backend"]["duration"] + self.results["frontend"]["duration"]
        
        # Calculate total test counts
        backend_counts = self.results["backend"].get("test_counts", {})
        frontend_counts = self.results["frontend"].get("test_counts", {})
        
        total_tests = backend_counts.get('total', 0) + frontend_counts.get('total', 0)
        total_passed = backend_counts.get('passed', 0) + frontend_counts.get('passed', 0)
        total_failed = backend_counts.get('failed', 0) + frontend_counts.get('failed', 0)
        total_skipped = backend_counts.get('skipped', 0) + frontend_counts.get('skipped', 0)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "mode": mode,
                "backend_only": backend_only,
                "frontend_only": frontend_only,
                "parallel": parallel,
            },
            "results": {
                "backend": self.results["backend"],
                "frontend": self.results["frontend"],
            },
            "summary": {
                "overall_passed": overall_passed,
                "total_duration": total_duration,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "total_skipped": total_skipped,
                "test_mode": TEST_CONFIGS[mode]["description"] if mode and mode in TEST_CONFIGS else "Custom configuration"
            },
        }
        
        # Save to history
        self.save_test_history(report)
        
        # Save JSON report
        report_path = self.reports_dir / "test_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self.generate_markdown_report(report)
        
        return report
    
    def generate_markdown_report(self, report):
        """Generate markdown test report with test counts"""
        md_content = f"""# Netra AI Platform - Test Report

Generated: {report['timestamp']}

## Summary

| Component | Status | Tests | Duration | Exit Code |
|-----------|--------|-------|----------|-----------|
| Backend   | {self._status_emoji(report['results']['backend']['status'])} {report['results']['backend']['status']} | {self._format_test_counts(report['results']['backend'].get('test_counts', {}))} | {report['results']['backend']['duration']:.2f}s | {report['results']['backend']['exit_code']} |
| Frontend  | {self._status_emoji(report['results']['frontend']['status'])} {report['results']['frontend']['status']} | {self._format_test_counts(report['results']['frontend'].get('test_counts', {}))} | {report['results']['frontend']['duration']:.2f}s | {report['results']['frontend']['exit_code']} |

**Total Tests**: {report['summary']['total_tests']} ({report['summary']['total_passed']} passed, {report['summary']['total_failed']} failed, {report['summary']['total_skipped']} skipped)
**Total Duration**: {report['summary']['total_duration']:.2f}s

## Configuration

- Test Mode: {report['configuration'].get('mode', 'custom')}
- Backend Only: {report['configuration'].get('backend_only', False)}
- Frontend Only: {report['configuration'].get('frontend_only', False)}
- Parallel Execution: {report['configuration'].get('parallel', False)}

## Results

Overall Status: **{self._status_emoji(report['summary']['overall_passed'])} {'PASSED' if report['summary']['overall_passed'] else 'FAILED'}**

## Test History

Check `reports/test_history.json` for historical test results and trends.

---
*This report was automatically generated by the Netra AI Platform enhanced test runner.*
"""
        
        # Save main report
        report_path = self.reports_dir / "test_report.md"
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(md_content)
        
        # Ensure reports/tests directory exists
        tests_reports_dir = self.reports_dir / "tests"
        tests_reports_dir.mkdir(exist_ok=True)
        
        # Save timestamped copy
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        timestamped_path = tests_reports_dir / f"test_report_{timestamp}.md"
        with open(timestamped_path, "w", encoding='utf-8') as f:
            f.write(md_content)
    
    def _format_test_counts(self, counts):
        """Format test counts for display"""
        if not counts or counts.get('total', 0) == 0:
            return "N/A"
        return f"{counts.get('passed', 0)}/{counts.get('total', 0)}"
    
    def _status_emoji(self, status):
        """Get emoji for status"""
        if status == "passed" or status is True:
            return "[PASS]"
        elif status == "failed" or status is False:
            return "[FAIL]"
        elif status == "running":
            return "[RUNNING]"
        else:
            return "[PENDING]"
    
    def print_summary(self):
        """Print enhanced test summary with counts"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        print(f"\nBackend Tests:")
        print(f"  Status: {self._status_emoji(self.results['backend']['status'])} {self.results['backend']['status'].upper()}")
        if self.results['backend'].get('test_counts', {}).get('total', 0) > 0:
            counts = self.results['backend']['test_counts']
            print(f"  Tests: {counts['passed']} passed, {counts['failed']} failed, {counts['skipped']} skipped ({counts['total']} total)")
        print(f"  Duration: {self.results['backend']['duration']:.2f}s")
        print(f"  Exit Code: {self.results['backend']['exit_code']}")
        
        print(f"\nFrontend Tests:")
        print(f"  Status: {self._status_emoji(self.results['frontend']['status'])} {self.results['frontend']['status'].upper()}")
        if self.results['frontend'].get('test_counts', {}).get('total', 0) > 0:
            counts = self.results['frontend']['test_counts']
            print(f"  Tests: {counts['passed']} passed, {counts['failed']} failed, {counts['skipped']} skipped ({counts['total']} total)")
        print(f"  Duration: {self.results['frontend']['duration']:.2f}s")
        print(f"  Exit Code: {self.results['frontend']['exit_code']}")
        
        # Overall summary
        backend_counts = self.results['backend'].get('test_counts', {})
        frontend_counts = self.results['frontend'].get('test_counts', {})
        
        total_tests = backend_counts.get('total', 0) + frontend_counts.get('total', 0)
        total_passed = backend_counts.get('passed', 0) + frontend_counts.get('passed', 0)
        total_failed = backend_counts.get('failed', 0) + frontend_counts.get('failed', 0)
        total_skipped = backend_counts.get('skipped', 0) + frontend_counts.get('skipped', 0)
        
        total_duration = self.results['backend']['duration'] + self.results['frontend']['duration']
        overall_passed = (
            self.results['backend']['status'] == 'passed' and 
            self.results['frontend']['status'] == 'passed'
        )
        
        print(f"\nOverall:")
        print(f"  Status: {self._status_emoji(overall_passed)} {'PASSED' if overall_passed else 'FAILED'}")
        if total_tests > 0:
            print(f"  Total Tests: {total_passed} passed, {total_failed} failed, {total_skipped} skipped ({total_tests} total)")
        print(f"  Total Duration: {total_duration:.2f}s")
        
        # Load and display history summary
        history = self.load_test_history()
        if history['summary']['total_runs'] > 0:
            print(f"\nTest History:")
            print(f"  Total Runs: {history['summary']['total_runs']}")
            print(f"  Success Rate: {history['summary']['success_rate']:.1f}%")
            print(f"  Last Run: {history['summary']['last_run']}")
        
        print("\nReports:")
        print(f"  - Test Report: reports/test_report.json")
        print(f"  - Markdown Report: reports/test_report.md")
        print(f"  - Test History: reports/test_history.json")
        print(f"  - Historical Reports: reports/tests/")
        
        if (self.reports_dir / "coverage").exists():
            print(f"  - Backend Coverage: reports/coverage/html/index.html")
        if (self.reports_dir / "frontend-coverage").exists():
            print(f"  - Frontend Coverage: reports/frontend-coverage/lcov-report/index.html")
        
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Enhanced test runner for Netra AI Platform with test counts and history",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Modes:
  quick         - Quick smoke tests (< 1 minute)
  standard      - Standard test suite (~ 5 minutes)
  comprehensive - Comprehensive tests with coverage (~ 10 minutes)
  ci            - Full CI/CD pipeline (~ 15 minutes)
  critical      - Critical path tests only

Examples:
  # Run quick smoke tests
  python test_runner_enhanced.py --mode quick
  
  # Run comprehensive tests with coverage
  python test_runner_enhanced.py --mode comprehensive
  
  # Run tests in parallel
  python test_runner_enhanced.py --parallel --mode standard
        """
    )
    
    # Test mode selection
    parser.add_argument(
        "--mode", "-m",
        choices=list(TEST_CONFIGS.keys()),
        help="Predefined test mode"
    )
    
    # Component selection
    parser.add_argument(
        "--backend-only", "-b",
        action="store_true",
        help="Run only backend tests"
    )
    parser.add_argument(
        "--frontend-only", "-f",
        action="store_true",
        help="Run only frontend tests"
    )
    
    # Custom arguments
    parser.add_argument(
        "--backend-args",
        help="Custom arguments for backend tests (quoted string)"
    )
    parser.add_argument(
        "--frontend-args",
        help="Custom arguments for frontend tests (quoted string)"
    )
    
    # Execution options
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run backend and frontend tests in parallel"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating test reports"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Initialize test runner
    runner = TestRunner()
    
    # Start overall timing
    runner.results["overall"]["start_time"] = datetime.now().isoformat()
    
    # Determine test arguments
    if args.mode:
        config = TEST_CONFIGS[args.mode]
        print(f"\nUsing test mode: {args.mode}")
        print(f"Description: {config['description']}")
        backend_args = config["backend_args"]
        frontend_args = config["frontend_args"]
    else:
        backend_args = args.backend_args.split() if args.backend_args else []
        frontend_args = args.frontend_args.split() if args.frontend_args else []
    
    # Convert to list if needed
    if isinstance(backend_args, str):
        import shlex
        backend_args = shlex.split(backend_args)
    if isinstance(frontend_args, str):
        import shlex
        frontend_args = shlex.split(frontend_args)
    
    # Print header
    print("\n" + "=" * 80)
    print("NETRA AI PLATFORM - ENHANCED TEST RUNNER")
    print("=" * 80)
    
    # Run tests
    backend_exit = 0
    frontend_exit = 0
    
    if args.parallel and not (args.backend_only or args.frontend_only):
        print("\nRunning tests in parallel...")
        backend_exit, frontend_exit = runner.run_parallel(backend_args, frontend_args)
    else:
        if not args.frontend_only:
            backend_exit = runner.run_backend_tests(backend_args)
        
        if not args.backend_only:
            frontend_exit = runner.run_frontend_tests(frontend_args)
    
    # End overall timing
    runner.results["overall"]["end_time"] = datetime.now().isoformat()
    
    # Generate reports
    if not args.no_report:
        runner.generate_test_report(
            mode=args.mode,
            backend_only=args.backend_only,
            frontend_only=args.frontend_only,
            parallel=args.parallel
        )
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    if args.backend_only:
        sys.exit(backend_exit)
    elif args.frontend_only:
        sys.exit(frontend_exit)
    else:
        sys.exit(max(backend_exit, frontend_exit))


if __name__ == "__main__":
    main()