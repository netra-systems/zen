#!/usr/bin/env python
"""
Unified test runner for Netra AI Platform
Runs both backend and frontend tests with comprehensive reporting
Optimized for Claude Code and CI/CD pipelines
Now with test isolation for concurrent execution
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
from typing import List, Dict, Tuple, Optional
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import test isolation utilities
try:
    from scripts.test_isolation import TestIsolationManager
except ImportError:
    TestIsolationManager = None

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
        "backend": ["--coverage", "--parallel", "-1"],
        "frontend": ["--coverage", "--lint", "--type-check"],
    },
    "ci": {
        "description": "Full CI/CD pipeline (~ 15 minutes)",
        "backend": ["--coverage", "--html-output", "--json-output", "--parallel", "-1", "--min-coverage", "70"],
        "frontend": ["--coverage", "--lint", "--type-check", "--build"],
    },
    "critical": {
        "description": "Critical path tests only",
        "backend": ["--category", "critical", "--fail-fast"],
        "frontend": ["--category", "auth", "--category", "websocket"],
    },
}


class TestRunner:
    def __init__(self, use_isolation=True):
        self.results = {
            "backend": {
                "status": "pending", 
                "duration": 0, 
                "exit_code": None,
                "test_details": {},  # Service-level test details
                "summary": {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
            },
            "frontend": {
                "status": "pending", 
                "duration": 0, 
                "exit_code": None,
                "test_details": {},  # Component-level test details
                "summary": {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
            },
            "overall": {"status": "pending", "start_time": None, "end_time": None},
        }
        
        # Set up test isolation if available and enabled
        self.isolation_manager = None
        if use_isolation and TestIsolationManager:
            self.isolation_manager = TestIsolationManager()
            self.isolation_manager.setup_environment()
            self.isolation_manager.apply_environment()
            self.isolation_manager.register_cleanup()
            self.reports_dir = self.isolation_manager.directories.get('reports', PROJECT_ROOT / "reports")
        else:
            self.reports_dir = PROJECT_ROOT / "reports"
            
        self.reports_dir.mkdir(exist_ok=True, parents=True)
        
    def parse_pytest_output(self, output: str) -> Dict:
        """Parse pytest output to extract test statistics per service"""
        service_stats = {}
        
        # Match patterns for test results
        test_pattern = re.compile(r'(app[\\/]tests[\\/][\w_]+)\.py::([\w]+)::([\w_]+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)')
        # Also match simpler pattern for single test files
        simple_pattern = re.compile(r'(app[\\/]tests[\\/]test_[\w_]+)\.py::([\w_]+)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)')
        # Match the final summary line
        summary_pattern = re.compile(r'=+\s*(\d+)\s+failed(?:,\s*)?(\d+)?\s*passed(?:,\s*)?(\d+)?\s*skipped')
        alt_summary_pattern = re.compile(r'=+\s*(\d+)\s+passed(?:,\s*)?(\d+)?\s*failed(?:,\s*)?(\d+)?\s*skipped')
        no_fail_pattern = re.compile(r'=+\s*(\d+)\s+passed(?:,\s*)?(\d+)?\s*skipped\s*in')
        
        total_stats = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
        
        for line in output.split('\n'):
            # Extract test results by file/service/class
            match = test_pattern.search(line)
            if match:
                file_path = match.group(1)
                class_name = match.group(2)
                test_name = match.group(3)
                status = match.group(4).lower()
                
                # Extract service name from file path
                file_parts = file_path.replace('\\', '/').split('/')
                if 'test_' in file_parts[-1]:
                    # Extract service from filename like test_demo_service.py
                    service = file_parts[-1].replace('test_', '').replace('.py', '')
                    if service.endswith('_service'):
                        service = service.replace('_service', '')
                else:
                    service = 'core'
                
                if service not in service_stats:
                    service_stats[service] = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
                
                if status in ['passed', 'failed', 'skipped', 'error']:
                    service_stats[service][status] += 1
            else:
                # Try simple pattern
                simple_match = simple_pattern.search(line)
                if simple_match:
                    file_path = simple_match.group(1)
                    test_name = simple_match.group(2)
                    status = simple_match.group(3).lower()
                    
                    # Extract service from filename
                    file_parts = file_path.replace('\\', '/').split('/')
                    filename = file_parts[-1].replace('test_', '').replace('.py', '')
                    if filename.endswith('_service'):
                        service = filename.replace('_service', '')
                    else:
                        service = filename or 'core'
                    
                    if service not in service_stats:
                        service_stats[service] = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
                    
                    if status in ['passed', 'failed', 'skipped', 'error']:
                        service_stats[service][status] += 1
            
            # Extract overall summary from lines like "1 failed, 6 passed, 1 skipped in 0.68s"
            if '====' in line and ('passed' in line or 'failed' in line):
                # Initialize counts
                passed_count = 0
                failed_count = 0
                skipped_count = 0
                
                # Extract individual counts using simple patterns
                failed_match = re.search(r'(\d+)\s+failed', line)
                if failed_match:
                    failed_count = int(failed_match.group(1))
                
                passed_match = re.search(r'(\d+)\s+passed', line)
                if passed_match:
                    passed_count = int(passed_match.group(1))
                
                skipped_match = re.search(r'(\d+)\s+skipped', line)
                if skipped_match:
                    skipped_count = int(skipped_match.group(1))
                
                # Update total stats if we found any matches
                if passed_match or failed_match or skipped_match:
                    total_stats = {
                        "passed": passed_count,
                        "failed": failed_count,
                        "skipped": skipped_count,
                        "error": 0
                    }
        
        return {"services": service_stats, "total": total_stats}
    
    def run_backend_tests(self, args: List[str]) -> int:
        """Run backend tests with detailed output capture"""
        print("\n" + "=" * 80)
        print("RUNNING BACKEND TESTS")
        print("=" * 80)
        
        start_time = time.time()
        self.results["backend"]["status"] = "running"
        
        # Add verbose flag to get detailed output
        if "-v" not in args and "--verbose" not in args:
            args = args + ["-v"]
        
        # Add isolation arguments if using isolation manager
        if self.isolation_manager:
            args = args + ["--isolation"]
        
        cmd = [sys.executable, "scripts/test_backend.py"] + args
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        # Print the output
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        # Parse test output for detailed statistics
        test_stats = self.parse_pytest_output(result.stdout)
        self.results["backend"]["test_details"] = test_stats.get("services", {})
        self.results["backend"]["summary"] = test_stats.get("total", {"passed": 0, "failed": 0, "skipped": 0, "error": 0})
        
        duration = time.time() - start_time
        self.results["backend"]["duration"] = duration
        self.results["backend"]["exit_code"] = result.returncode
        self.results["backend"]["status"] = "passed" if result.returncode == 0 else "failed"
        
        return result.returncode
    
    def parse_jest_output(self, output: str) -> Dict:
        """Parse Jest output to extract test statistics per component"""
        component_stats = {}
        
        # Match patterns for Jest test results
        suite_pattern = re.compile(r'\s+(PASS|FAIL)\s+([\w/]+\.test\.[tj]sx?)')
        test_summary_pattern = re.compile(r'Tests:\s+(\d+)\s+passed(?:,\s+(\d+)\s+failed)?(?:,\s+(\d+)\s+skipped)?(?:,\s+(\d+)\s+total)?')
        
        for line in output.split('\n'):
            # Extract test results by file/component
            match = suite_pattern.search(line)
            if match:
                status = match.group(1).lower()
                file_path = match.group(2)
                
                # Extract component name from path
                parts = file_path.replace('.test.tsx', '').replace('.test.ts', '').split('/')
                component = parts[-1] if parts else 'unknown'
                
                if component not in component_stats:
                    component_stats[component] = {"passed": 0, "failed": 0, "skipped": 0, "error": 0}
                
                if status == 'pass':
                    component_stats[component]["passed"] += 1
                else:
                    component_stats[component]["failed"] += 1
            
            # Extract overall summary
            summary_match = test_summary_pattern.search(line)
            if summary_match:
                total_stats = {
                    "passed": int(summary_match.group(1) or 0),
                    "failed": int(summary_match.group(2) or 0),
                    "skipped": int(summary_match.group(3) or 0),
                    "error": 0
                }
                return {"components": component_stats, "total": total_stats}
        
        return {"components": component_stats, "total": {"passed": 0, "failed": 0, "skipped": 0, "error": 0}}
    
    def run_frontend_tests(self, args: List[str]) -> int:
        """Run frontend tests with detailed output capture"""
        print("\n" + "=" * 80)
        print("RUNNING FRONTEND TESTS")
        print("=" * 80)
        
        start_time = time.time()
        self.results["frontend"]["status"] = "running"
        
        # Add isolation arguments if using isolation manager
        if self.isolation_manager:
            args = args + ["--isolation"]
        
        cmd = [sys.executable, "scripts/test_frontend.py"] + args
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        # Print the output
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        # Parse test output for detailed statistics
        test_stats = self.parse_jest_output(result.stdout)
        self.results["frontend"]["test_details"] = test_stats.get("components", {})
        self.results["frontend"]["summary"] = test_stats.get("total", {"passed": 0, "failed": 0, "skipped": 0, "error": 0})
        
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
        """Generate HTML test report with service-level statistics"""
        # Generate service details HTML
        backend_html = ""
        if report.get('service_details', {}).get('backend'):
            backend_html = "<h3>Backend Services Test Results</h3>\n<table>\n"
            backend_html += "<tr><th>Service</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Error</th><th>Total</th></tr>\n"
            for service, stats in report['service_details']['backend'].items():
                total = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
                backend_html += f"<tr><td>{service}</td><td>{stats['passed']}</td><td>{stats['failed']}</td><td>{stats['skipped']}</td><td>{stats['error']}</td><td>{total}</td></tr>\n"
            backend_html += "</table>\n"
        
        frontend_html = ""
        if report.get('service_details', {}).get('frontend'):
            frontend_html = "<h3>Frontend Components Test Results</h3>\n<table>\n"
            frontend_html += "<tr><th>Component</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Error</th><th>Total</th></tr>\n"
            for component, stats in report['service_details']['frontend'].items():
                total = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
                frontend_html += f"<tr><td>{component}</td><td>{stats['passed']}</td><td>{stats['failed']}</td><td>{stats['skipped']}</td><td>{stats['error']}</td><td>{total}</td></tr>\n"
            frontend_html += "</table>\n"
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Netra AI Test Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #666; margin-top: 20px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 5px; }}
        .passed {{ color: green; font-weight: bold; }}
        .failed {{ color: red; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .test-stats {{ margin: 20px 0; padding: 10px; background: #f9f9f9; border-left: 3px solid #4CAF50; }}
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
    
    <div class="test-stats">
        <h3>Test Statistics</h3>
        <p><strong>Backend:</strong> {report['summary'].get('backend_test_summary', {}).get('passed', 0)} passed, 
           {report['summary'].get('backend_test_summary', {}).get('failed', 0)} failed, 
           {report['summary'].get('backend_test_summary', {}).get('skipped', 0)} skipped</p>
        <p><strong>Frontend:</strong> {report['summary'].get('frontend_test_summary', {}).get('passed', 0)} passed, 
           {report['summary'].get('frontend_test_summary', {}).get('failed', 0)} failed, 
           {report['summary'].get('frontend_test_summary', {}).get('skipped', 0)} skipped</p>
    </div>
    
    <h2>Component Results</h2>
    <table>
        <tr>
            <th>Component</th>
            <th>Status</th>
            <th>Duration</th>
            <th>Exit Code</th>
            <th>Tests Passed</th>
            <th>Tests Failed</th>
        </tr>
        <tr>
            <td>Backend</td>
            <td class="{'passed' if report['results']['backend']['status'] == 'passed' else 'failed'}">
                {report['results']['backend']['status'].upper()}
            </td>
            <td>{report['results']['backend']['duration']:.2f}s</td>
            <td>{report['results']['backend']['exit_code']}</td>
            <td>{report['summary'].get('backend_test_summary', {}).get('passed', 0)}</td>
            <td>{report['summary'].get('backend_test_summary', {}).get('failed', 0)}</td>
        </tr>
        <tr>
            <td>Frontend</td>
            <td class="{'passed' if report['results']['frontend']['status'] == 'passed' else 'failed'}">
                {report['results']['frontend']['status'].upper()}
            </td>
            <td>{report['results']['frontend']['duration']:.2f}s</td>
            <td>{report['results']['frontend']['exit_code']}</td>
            <td>{report['summary'].get('frontend_test_summary', {}).get('passed', 0)}</td>
            <td>{report['summary'].get('frontend_test_summary', {}).get('failed', 0)}</td>
        </tr>
    </table>
    
    <h2>Detailed Service Results</h2>
    {backend_html}
    {frontend_html}
</body>
</html>
"""
        
        html_path = tests_dir / f"test_report_{timestamp}.html"
        with open(html_path, "w", encoding='utf-8') as f:
            f.write(html_content)
    
    def generate_report(self, args):
        """Generate test report with detailed service statistics"""
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
                "backend_test_summary": self.results["backend"]["summary"],
                "frontend_test_summary": self.results["frontend"]["summary"],
            },
            "service_details": {
                "backend": self.results["backend"]["test_details"],
                "frontend": self.results["frontend"]["test_details"]
            }
        }
        
        # Save JSON report
        report_path = self.reports_dir / "test_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        # Generate markdown report
        self.generate_markdown_report(report)
        
        return report
    
    def generate_markdown_report(self, report):
        """Generate markdown test report with service-level statistics"""
        # Generate service details tables
        backend_details = ""
        if report.get('service_details', {}).get('backend'):
            backend_details = "\n### Backend Services Test Results\n\n"
            backend_details += "| Service | Passed | Failed | Skipped | Error | Total |\n"
            backend_details += "|---------|--------|--------|---------|-------|-------|\n"
            
            for service, stats in report['service_details']['backend'].items():
                total = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
                backend_details += f"| {service} | {stats['passed']} | {stats['failed']} | {stats['skipped']} | {stats['error']} | {total} |\n"
            
            # Add backend summary
            summary = report['summary'].get('backend_test_summary', {})
            total = summary.get('passed', 0) + summary.get('failed', 0) + summary.get('skipped', 0) + summary.get('error', 0)
            backend_details += f"| **Total** | **{summary.get('passed', 0)}** | **{summary.get('failed', 0)}** | **{summary.get('skipped', 0)}** | **{summary.get('error', 0)}** | **{total}** |\n"
        
        frontend_details = ""
        if report.get('service_details', {}).get('frontend'):
            frontend_details = "\n### Frontend Components Test Results\n\n"
            frontend_details += "| Component | Passed | Failed | Skipped | Error | Total |\n"
            frontend_details += "|-----------|--------|--------|---------|-------|-------|\n"
            
            for component, stats in report['service_details']['frontend'].items():
                total = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
                frontend_details += f"| {component} | {stats['passed']} | {stats['failed']} | {stats['skipped']} | {stats['error']} | {total} |\n"
            
            # Add frontend summary
            summary = report['summary'].get('frontend_test_summary', {})
            total = summary.get('passed', 0) + summary.get('failed', 0) + summary.get('skipped', 0) + summary.get('error', 0)
            frontend_details += f"| **Total** | **{summary.get('passed', 0)}** | **{summary.get('failed', 0)}** | **{summary.get('skipped', 0)}** | **{summary.get('error', 0)}** | **{total}** |\n"
        
        md_content = f"""# Netra AI Platform - Test Report

Generated: {report['timestamp']}

## Summary

| Component | Status | Duration | Exit Code | Tests Passed | Tests Failed |
|-----------|--------|----------|-----------|--------------|---------------|
| Backend   | {self._status_emoji(report['results']['backend']['status'])} {report['results']['backend']['status']} | {report['results']['backend']['duration']:.2f}s | {report['results']['backend']['exit_code']} | {report['summary'].get('backend_test_summary', {}).get('passed', 0)} | {report['summary'].get('backend_test_summary', {}).get('failed', 0)} |
| Frontend  | {self._status_emoji(report['results']['frontend']['status'])} {report['results']['frontend']['status']} | {report['results']['frontend']['duration']:.2f}s | {report['results']['frontend']['exit_code']} | {report['summary'].get('frontend_test_summary', {}).get('passed', 0)} | {report['summary'].get('frontend_test_summary', {}).get('failed', 0)} |

**Total Duration**: {report['summary']['total_duration']:.2f}s

## Test Statistics

### Overall Test Results
- **Backend**: {report['summary'].get('backend_test_summary', {}).get('passed', 0)} passed, {report['summary'].get('backend_test_summary', {}).get('failed', 0)} failed, {report['summary'].get('backend_test_summary', {}).get('skipped', 0)} skipped
- **Frontend**: {report['summary'].get('frontend_test_summary', {}).get('passed', 0)} passed, {report['summary'].get('frontend_test_summary', {}).get('failed', 0)} failed, {report['summary'].get('frontend_test_summary', {}).get('skipped', 0)} skipped

{backend_details}
{frontend_details}

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
        """Print test summary with detailed statistics"""
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        
        print(f"\nBackend Tests:")
        print(f"  Status: {self._status_emoji(self.results['backend']['status'])} {self.results['backend']['status'].upper()}")
        print(f"  Duration: {self.results['backend']['duration']:.2f}s")
        print(f"  Exit Code: {self.results['backend']['exit_code']}")
        backend_summary = self.results['backend']['summary']
        print(f"  Test Results: {backend_summary['passed']} passed, {backend_summary['failed']} failed, {backend_summary['skipped']} skipped")
        
        # Print backend service details if available
        if self.results['backend']['test_details']:
            print("  Service Breakdown:")
            for service, stats in self.results['backend']['test_details'].items():
                total = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
                if total > 0:
                    print(f"    - {service}: {stats['passed']}/{total} passed")
        
        print(f"\nFrontend Tests:")
        print(f"  Status: {self._status_emoji(self.results['frontend']['status'])} {self.results['frontend']['status'].upper()}")
        print(f"  Duration: {self.results['frontend']['duration']:.2f}s")
        print(f"  Exit Code: {self.results['frontend']['exit_code']}")
        frontend_summary = self.results['frontend']['summary']
        print(f"  Test Results: {frontend_summary['passed']} passed, {frontend_summary['failed']} failed, {frontend_summary['skipped']} skipped")
        
        # Print frontend component details if available
        if self.results['frontend']['test_details']:
            print("  Component Breakdown:")
            for component, stats in self.results['frontend']['test_details'].items():
                total = stats['passed'] + stats['failed'] + stats['skipped'] + stats['error']
                if total > 0:
                    print(f"    - {component}: {stats['passed']}/{total} passed")
        
        total_duration = self.results['backend']['duration'] + self.results['frontend']['duration']
        overall_passed = (
            self.results['backend']['status'] == 'passed' and 
            self.results['frontend']['status'] == 'passed'
        )
        
        print(f"\nOverall:")
        print(f"  Status: {self._status_emoji(overall_passed)} {'PASSED' if overall_passed else 'FAILED'}")
        print(f"  Total Duration: {total_duration:.2f}s")
        total_tests_passed = backend_summary['passed'] + frontend_summary['passed']
        total_tests_failed = backend_summary['failed'] + frontend_summary['failed']
        print(f"  Total Tests: {total_tests_passed} passed, {total_tests_failed} failed")
        
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