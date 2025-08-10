#!/usr/bin/env python
"""
Unified test runner for Netra AI Platform
Runs both backend and frontend tests with comprehensive reporting
Optimized for Claude Code and CI/CD pipelines
"""

import os
import sys
import json
import time
import argparse
import subprocess
import threading
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Test configuration
TEST_CONFIGS = {
    "quick": {
        "description": "Quick smoke tests (< 1 minute)",
        "backend": ["--category", "smoke", "--fail-fast"],
        "frontend": ["--category", "smoke"],
    },
    "standard": {
        "description": "Standard test suite (~ 5 minutes)",
        "backend": ["--category", "unit", "--parallel", "4"],
        "frontend": ["--category", "unit"],
    },
    "comprehensive": {
        "description": "Comprehensive test suite with coverage (~ 10 minutes)",
        "backend": ["--coverage", "--parallel", "auto"],
        "frontend": ["--coverage", "--lint", "--type-check"],
    },
    "ci": {
        "description": "Full CI/CD pipeline (~ 15 minutes)",
        "backend": ["--coverage", "--html-output", "--json-output", "--parallel", "auto", "--min-coverage", "70"],
        "frontend": ["--coverage", "--lint", "--type-check", "--build"],
    },
    "critical": {
        "description": "Critical path tests only",
        "backend": ["--category", "critical", "--fail-fast"],
        "frontend": ["--category", "auth", "--category", "websocket"],
    },
}


class TestRunner:
    def __init__(self):
        self.results = {
            "backend": {"status": "pending", "duration": 0, "exit_code": None},
            "frontend": {"status": "pending", "duration": 0, "exit_code": None},
            "overall": {"status": "pending", "start_time": None, "end_time": None},
        }
        self.reports_dir = PROJECT_ROOT / "reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_backend_tests(self, args: List[str]) -> int:
        """Run backend tests"""
        print("\n" + "=" * 80)
        print("RUNNING BACKEND TESTS")
        print("=" * 80)
        
        start_time = time.time()
        self.results["backend"]["status"] = "running"
        
        cmd = [sys.executable, "scripts/test_backend.py"] + args
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
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
        result = subprocess.run(cmd, cwd=PROJECT_ROOT)
        
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
    
    def generate_html_report(self, report, tests_dir, timestamp):
        """Generate HTML test report"""
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Netra AI Test Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .passed {{ color: green; font-weight: bold; }}
        .failed {{ color: red; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
    </style>
</head>
<body>
    <h1>Netra AI Platform - Test Report</h1>
    <div class="summary">
        <p><strong>Generated:</strong> {report['timestamp']}</p>
        <p><strong>Mode:</strong> {report['configuration'].get('mode', 'custom')}</p>
        <p><strong>Overall Status:</strong> 
            <span class="{'passed' if report['summary']['overall_passed'] else 'failed'}">
                {'PASSED' if report['summary']['overall_passed'] else 'FAILED'}
            </span>
        </p>
        <p><strong>Total Duration:</strong> {report['summary']['total_duration']:.2f}s</p>
    </div>
    
    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Component</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Exit Code</th>
        </tr>
        <tr>
            <td>Backend</td>
            <td class="{'passed' if report['results']['backend']['status'] == 'passed' else 'failed'}">
                {report['results']['backend']['status'].upper()}
            </td>
            <td>{report['results']['backend']['duration']:.2f}s</td>
            <td>{report['results']['backend']['exit_code']}</td>
        </tr>
        <tr>
            <td>Frontend</td>
            <td class="{'passed' if report['results']['frontend']['status'] == 'passed' else 'failed'}">
                {report['results']['frontend']['status'].upper()}
            </td>
            <td>{report['results']['frontend']['duration']:.2f}s</td>
            <td>{report['results']['frontend']['exit_code']}</td>
        </tr>
    </table>
</body>
</html>
"""
        
        html_path = tests_dir / f"test_report_{timestamp}.html"
        with open(html_path, "w", encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_report(self, args):
        """Generate test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "configuration": vars(args),
            "results": self.results,
            "summary": {
                "total_duration": self.results["backend"]["duration"] + self.results["frontend"]["duration"],
                "backend_passed": self.results["backend"]["status"] == "passed",
                "frontend_passed": self.results["frontend"]["status"] == "passed",
                "overall_passed": (
                    self.results["backend"]["status"] == "passed" and 
                    self.results["frontend"]["status"] == "passed"
                ),
            },
        }
        
        # Save JSON report
        report_path = self.reports_dir / "test_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self.generate_markdown_report(report)
        
        return report
    
    def generate_markdown_report(self, report):
        """Generate markdown test report"""
        md_content = f"""# Netra AI Platform - Test Report

Generated: {report['timestamp']}

## Summary

| Component | Status | Duration | Exit Code |
|-----------|--------|----------|-----------|
| Backend   | {self._status_emoji(report['results']['backend']['status'])} {report['results']['backend']['status']} | {report['results']['backend']['duration']:.2f}s | {report['results']['backend']['exit_code']} |
| Frontend  | {self._status_emoji(report['results']['frontend']['status'])} {report['results']['frontend']['status']} | {report['results']['frontend']['duration']:.2f}s | {report['results']['frontend']['exit_code']} |

**Total Duration**: {report['summary']['total_duration']:.2f}s

## Configuration

- Test Mode: {report['configuration'].get('mode', 'custom')}
- Backend Only: {report['configuration'].get('backend_only', False)}
- Frontend Only: {report['configuration'].get('frontend_only', False)}
- Parallel Execution: {report['configuration'].get('parallel', False)}

## Results

Overall Status: **{self._status_emoji(report['summary']['overall_passed'])} {'PASSED' if report['summary']['overall_passed'] else 'FAILED'}**

---
*This report was automatically generated by the Netra AI Platform test runner.*
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
        
        # Generate HTML report if pytest-html is available
        self.generate_html_report(report, tests_reports_dir, timestamp)
    
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
        """Print test summary"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        print(f"\nBackend Tests:")
        print(f"  Status: {self._status_emoji(self.results['backend']['status'])} {self.results['backend']['status'].upper()}")
        print(f"  Duration: {self.results['backend']['duration']:.2f}s")
        print(f"  Exit Code: {self.results['backend']['exit_code']}")
        
        print(f"\nFrontend Tests:")
        print(f"  Status: {self._status_emoji(self.results['frontend']['status'])} {self.results['frontend']['status'].upper()}")
        print(f"  Duration: {self.results['frontend']['duration']:.2f}s")
        print(f"  Exit Code: {self.results['frontend']['exit_code']}")
        
        total_duration = self.results['backend']['duration'] + self.results['frontend']['duration']
        overall_passed = (
            self.results['backend']['status'] == 'passed' and 
            self.results['frontend']['status'] == 'passed'
        )
        
        print(f"\nOverall:")
        print(f"  Status: {self._status_emoji(overall_passed)} {'PASSED' if overall_passed else 'FAILED'}")
        print(f"  Total Duration: {total_duration:.2f}s")
        
        print("\nReports:")
        print(f"  - Test Report: reports/test_report.json")
        print(f"  - Markdown Report: reports/test_report.md")
        print(f"  - Test History: reports/tests/")
        
        if (self.reports_dir / "coverage").exists():
            print(f"  - Backend Coverage: reports/coverage/html/index.html")
        if (self.reports_dir / "frontend-coverage").exists():
            print(f"  - Frontend Coverage: reports/frontend-coverage/lcov-report/index.html")
        
        print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Unified test runner for Netra AI Platform",
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
  python test_runner.py --mode quick
  
  # Run standard tests
  python test_runner.py --mode standard
  
  # Run comprehensive tests with coverage
  python test_runner.py --mode comprehensive
  
  # Run only backend tests
  python test_runner.py --backend-only
  
  # Run only frontend tests
  python test_runner.py --frontend-only
  
  # Run with custom arguments
  python test_runner.py --backend-args "--category unit" --frontend-args "--lint"
  
  # Run tests in parallel
  python test_runner.py --parallel --mode standard
  
  # Full CI/CD run
  python test_runner.py --mode ci --parallel
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
    
    # Determine test arguments
    backend_args = []
    frontend_args = []
    
    if args.mode:
        config = TEST_CONFIGS[args.mode]
        backend_args = config.get("backend", [])
        frontend_args = config.get("frontend", [])
        print(f"\nUsing test mode: {args.mode}")
        print(f"Description: {config['description']}")
    
    # Override with custom arguments if provided
    if args.backend_args:
        backend_args = args.backend_args.split()
    if args.frontend_args:
        frontend_args = args.frontend_args.split()
    
    # Add verbose flag if requested
    if args.verbose:
        if "--verbose" not in backend_args and "-v" not in backend_args:
            backend_args.append("--verbose")
        if "--verbose" not in frontend_args and "-v" not in frontend_args:
            frontend_args.append("--verbose")
    
    print("\n" + "=" * 80)
    print("NETRA AI PLATFORM - UNIFIED TEST RUNNER")
    print("=" * 80)
    
    # Record start time
    runner.results["overall"]["start_time"] = time.time()
    
    # Run tests
    backend_exit = 0
    frontend_exit = 0
    
    if args.backend_only:
        backend_exit = runner.run_backend_tests(backend_args)
        runner.results["frontend"]["status"] = "skipped"
    elif args.frontend_only:
        frontend_exit = runner.run_frontend_tests(frontend_args)
        runner.results["backend"]["status"] = "skipped"
    elif args.parallel:
        print("\nRunning tests in parallel...")
        backend_exit, frontend_exit = runner.run_parallel(backend_args, frontend_args)
    else:
        backend_exit = runner.run_backend_tests(backend_args)
        frontend_exit = runner.run_frontend_tests(frontend_args)
    
    # Record end time
    runner.results["overall"]["end_time"] = time.time()
    
    # Generate report
    if not args.no_report:
        report = runner.generate_report(args)
    
    # Print summary
    runner.print_summary()
    
    # Determine overall exit code
    if args.backend_only:
        exit_code = backend_exit
    elif args.frontend_only:
        exit_code = frontend_exit
    else:
        exit_code = max(backend_exit, frontend_exit)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()