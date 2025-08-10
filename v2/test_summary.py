#!/usr/bin/env python
"""
Test Summary Report - Shows failures first and provides actionable insights
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Tuple

class TestSummary:
    """Analyze and report test results with failures first"""
    
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "errors": [],
            "skipped": [],
            "slow": []
        }
        self.total_time = 0
        self.timestamp = datetime.now()
    
    def run_tests(self, test_path: str = "tests/", parallel: int = 4) -> int:
        """Run tests and capture results"""
        
        print("🧪 Running Test Suite...")
        print("=" * 60)
        
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            "--json-report",
            "--json-report-file=test_report.json",
            "-v",
            "--tb=short",
            "--durations=10",
            "-rf",  # Show failure summary
            "--failed-first",  # Run failed tests first
        ]
        
        if parallel > 0:
            cmd.extend(["-n", str(parallel)])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            self.parse_results()
            return result.returncode
            
        except subprocess.TimeoutExpired:
            print("❌ Tests timed out after 5 minutes")
            return 1
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return 1
    
    def parse_results(self):
        """Parse test results from JSON report"""
        
        try:
            with open("test_report.json", "r") as f:
                report = json.load(f)
            
            self.total_time = report.get("duration", 0)
            
            for test in report.get("tests", []):
                name = test.get("nodeid", "unknown")
                outcome = test.get("outcome", "unknown")
                duration = test.get("duration", 0)
                
                test_info = {
                    "name": name,
                    "duration": duration,
                    "file": test.get("file", ""),
                    "line": test.get("lineno", 0)
                }
                
                if outcome == "passed":
                    self.results["passed"].append(test_info)
                    if duration > 1.0:  # Tests taking more than 1 second
                        self.results["slow"].append(test_info)
                elif outcome == "failed":
                    test_info["error"] = test.get("call", {}).get("longrepr", "")
                    self.results["failed"].append(test_info)
                elif outcome == "error":
                    test_info["error"] = test.get("setup", {}).get("longrepr", "")
                    self.results["errors"].append(test_info)
                elif outcome == "skipped":
                    self.results["skipped"].append(test_info)
        
        except FileNotFoundError:
            # Fallback to basic pytest output parsing
            self.parse_basic_output()
        except Exception as e:
            print(f"Warning: Could not parse JSON report: {e}")
    
    def parse_basic_output(self):
        """Fallback parser for basic pytest output"""
        # This would parse stdout if JSON report is not available
        pass
    
    def print_summary(self):
        """Print comprehensive test summary with failures first"""
        
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 60)
        print(f"⏰ Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⌛ Total Duration: {self.total_time:.2f}s")
        print()
        
        # Overall statistics
        total_tests = sum(len(v) for v in self.results.values())
        print("📈 Overall Statistics:")
        print(f"  Total Tests: {total_tests}")
        print(f"  ✅ Passed: {len(self.results['passed'])}")
        print(f"  ❌ Failed: {len(self.results['failed'])}")
        print(f"  🔥 Errors: {len(self.results['errors'])}")
        print(f"  ⏭️  Skipped: {len(self.results['skipped'])}")
        print(f"  🐌 Slow: {len(self.results['slow'])}")
        
        if total_tests > 0:
            pass_rate = (len(self.results['passed']) / total_tests) * 100
            print(f"  📊 Pass Rate: {pass_rate:.1f}%")
        
        # FAILURES FIRST - Most important section
        if self.results["failed"]:
            print("\n" + "=" * 60)
            print("❌ FAILED TESTS (Fix these first!)")
            print("=" * 60)
            for i, test in enumerate(self.results["failed"], 1):
                print(f"\n{i}. {test['name']}")
                print(f"   📁 File: {test['file']}:{test['line']}")
                print(f"   ⏱️  Duration: {test['duration']:.3f}s")
                if test.get('error'):
                    error_lines = str(test['error']).split('\n')[:5]
                    print("   💥 Error:")
                    for line in error_lines:
                        print(f"      {line}")
        
        # Errors (setup/teardown failures)
        if self.results["errors"]:
            print("\n" + "=" * 60)
            print("🔥 TEST ERRORS (Setup/Teardown issues)")
            print("=" * 60)
            for i, test in enumerate(self.results["errors"], 1):
                print(f"\n{i}. {test['name']}")
                print(f"   📁 File: {test['file']}:{test['line']}")
                if test.get('error'):
                    error_lines = str(test['error']).split('\n')[:3]
                    for line in error_lines:
                        print(f"   {line}")
        
        # Slow tests (performance issues)
        if self.results["slow"]:
            print("\n" + "=" * 60)
            print("🐌 SLOW TESTS (Performance concerns)")
            print("=" * 60)
            slow_sorted = sorted(self.results["slow"], key=lambda x: x["duration"], reverse=True)
            for i, test in enumerate(slow_sorted[:5], 1):  # Top 5 slowest
                print(f"{i}. {test['name']}")
                print(f"   ⏱️  Duration: {test['duration']:.3f}s")
        
        # Quick wins - tests that are passing
        if self.results["passed"] and len(self.results["passed"]) <= 20:
            print("\n" + "=" * 60)
            print("✅ PASSING TESTS")
            print("=" * 60)
            for test in self.results["passed"][:10]:  # Show first 10
                print(f"  ✓ {test['name']} ({test['duration']:.3f}s)")
            if len(self.results["passed"]) > 10:
                print(f"  ... and {len(self.results['passed']) - 10} more")
        
        # Recommendations
        self.print_recommendations()
    
    def print_recommendations(self):
        """Print actionable recommendations based on test results"""
        
        print("\n" + "=" * 60)
        print("💡 RECOMMENDATIONS")
        print("=" * 60)
        
        recommendations = []
        
        if self.results["failed"]:
            recommendations.append(
                f"🔧 Fix {len(self.results['failed'])} failing tests first - "
                "they are blocking your test suite"
            )
        
        if self.results["errors"]:
            recommendations.append(
                "⚠️  Address setup/teardown errors - they indicate "
                "infrastructure issues"
            )
        
        if self.results["slow"]:
            avg_slow_time = sum(t["duration"] for t in self.results["slow"]) / len(self.results["slow"])
            recommendations.append(
                f"⚡ Optimize {len(self.results['slow'])} slow tests "
                f"(avg: {avg_slow_time:.2f}s) to improve CI/CD performance"
            )
        
        if not self.results["failed"] and not self.results["errors"]:
            recommendations.append("🎉 All tests are passing! Consider adding more test coverage")
        
        pass_rate = (len(self.results['passed']) / max(sum(len(v) for v in self.results.values()), 1)) * 100
        if pass_rate < 80:
            recommendations.append(
                f"📈 Pass rate is {pass_rate:.1f}% - aim for at least 80% for production readiness"
            )
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    
    def generate_html_report(self):
        """Generate an HTML report for better visualization"""
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Report - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .failed {{ background-color: #ffcccc; }}
                .passed {{ background-color: #ccffcc; }}
                .error {{ background-color: #ffeecc; }}
                .slow {{ background-color: #ffffcc; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <h1>Test Report</h1>
            <h2>Summary</h2>
            <ul>
                <li>Total: {sum(len(v) for v in self.results.values())}</li>
                <li>Passed: {len(self.results['passed'])}</li>
                <li>Failed: {len(self.results['failed'])}</li>
                <li>Errors: {len(self.results['errors'])}</li>
            </ul>
            
            <h2>Failed Tests (Priority)</h2>
            <table>
                <tr><th>Test</th><th>File</th><th>Error</th></tr>
                {''.join(f"<tr class='failed'><td>{t['name']}</td><td>{t['file']}</td><td>{t.get('error', '')[:100]}</td></tr>" for t in self.results['failed'])}
            </table>
        </body>
        </html>
        """
        
        with open("test_report.html", "w") as f:
            f.write(html_content)
        
        print("\n📄 HTML report generated: test_report.html")

def main():
    """Main entry point"""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Run tests with comprehensive reporting")
    parser.add_argument("--parallel", "-p", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--html", action="store_true", help="Generate HTML report")
    parser.add_argument("tests", nargs="?", default="tests/", help="Test path")
    
    args = parser.parse_args()
    
    summary = TestSummary()
    exit_code = summary.run_tests(args.tests, args.parallel)
    summary.print_summary()
    
    if args.html:
        summary.generate_html_report()
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()