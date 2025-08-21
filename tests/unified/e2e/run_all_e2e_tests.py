#!/usr/bin/env python
"""
Simple E2E Test Runner - Business Value: $100K+ MRR Protection

BUSINESS VALUE JUSTIFICATION (BVJ):
1. Segment: All segments - critical for production stability
2. Business Goal: Validate complete user journey reliability  
3. Value Impact: Prevents production failures, protects user conversion
4. Revenue Impact: Safeguards $100K+ MRR from E2E regression failures

Simple, focused E2E test runner that:
- Discovers all E2E test files automatically
- Runs each test individually to avoid timeouts
- Collects results and generates summary report
- Handles failures gracefully and continues execution
- Provides clear pass/fail status for CI/CD integration
"""

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TestFileResult:
    """Result of running a single test file"""
    file_path: str
    status: str  # 'passed', 'failed', 'timeout', 'error'
    duration: float
    exit_code: int
    stdout: str = ""
    stderr: str = ""

@dataclass
class E2ETestSummary:
    """Summary of all E2E test execution"""
    total_files: int
    passed_files: int
    failed_files: int
    timeout_files: int
    error_files: int
    total_duration: float
    success_rate: float
    results: List[TestFileResult]

class E2ETestDiscovery:
    """Discover E2E test files in the project"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def find_e2e_test_files(self) -> List[Path]:
        """Find all E2E test files"""
        e2e_dir = self.project_root / "tests" / "unified" / "e2e"
        
        if not e2e_dir.exists():
            print(f"E2E directory not found: {e2e_dir}")
            return []
        
        # Find all test_*.py files
        test_files = list(e2e_dir.glob("test_*.py"))
        
        # Filter out invalid files
        valid_files = []
        for file_path in test_files:
            if self._is_valid_test_file(file_path):
                valid_files.append(file_path)
        
        # Sort by name for consistent ordering
        return sorted(valid_files)
    
    def _is_valid_test_file(self, file_path: Path) -> bool:
        """Check if file is a valid test file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            return 'def test_' in content or 'async def test_' in content
        except Exception:
            return False

class E2ETestExecutor:
    """Execute E2E tests individually"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        
    def run_test_file(self, test_file: Path) -> TestFileResult:
        """Run a single test file with timeout"""
        print(f"Running: {test_file.name}", flush=True)
        start_time = time.time()
        
        try:
            # Build pytest command with stricter timeouts
            cmd = [
                sys.executable, "-m", "pytest",
                str(test_file),
                "-v",
                "--tb=short", 
                "--timeout=15",  # 15 second timeout per individual test
                "-x"  # Stop on first failure
            ]
            
            # Run with timeout (25 seconds for entire file)
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=25  # 25 second timeout for entire file
            )
            
            duration = time.time() - start_time
            status = 'passed' if result.returncode == 0 else 'failed'
            
            print(f"  Completed in {duration:.1f}s", flush=True)
            
            return TestFileResult(
                file_path=str(test_file),
                status=status,
                duration=duration,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"  TIMEOUT after {duration:.1f}s", flush=True)
            return TestFileResult(
                file_path=str(test_file),
                status='timeout',
                duration=duration,
                exit_code=-1,
                stdout="",
                stderr="Test file timed out after 25 seconds"
            )
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"  ERROR after {duration:.1f}s: {e}", flush=True)
            return TestFileResult(
                file_path=str(test_file),
                status='error',
                duration=duration,
                exit_code=-1,
                stdout="",
                stderr=f"Error running test: {str(e)}"
            )

class E2EReportGenerator:
    """Generate test execution reports"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
    
    def generate_summary(self, results: List[TestFileResult]) -> E2ETestSummary:
        """Generate execution summary"""
        if not results:
            return E2ETestSummary(
                total_files=0,
                passed_files=0,
                failed_files=0,
                timeout_files=0,
                error_files=0,
                total_duration=0.0,
                success_rate=0.0,
                results=[]
            )
        
        passed = len([r for r in results if r.status == 'passed'])
        failed = len([r for r in results if r.status == 'failed'])
        timeout = len([r for r in results if r.status == 'timeout'])
        error = len([r for r in results if r.status == 'error'])
        total = len(results)
        
        success_rate = (passed / total * 100) if total > 0 else 0.0
        total_duration = sum(r.duration for r in results)
        
        return E2ETestSummary(
            total_files=total,
            passed_files=passed,
            failed_files=failed,
            timeout_files=timeout,
            error_files=error,
            total_duration=total_duration,
            success_rate=success_rate,
            results=results
        )
    
    def save_json_report(self, summary: E2ETestSummary) -> Path:
        """Save JSON report for CI/CD integration"""
        report_file = self.reports_dir / "e2e_results.json"
        
        with open(report_file, 'w') as f:
            json.dump(asdict(summary), f, indent=2, default=str)
        
        return report_file
    
    def print_summary_report(self, summary: E2ETestSummary):
        """Print comprehensive summary to console"""
        print("\n" + "="*60)
        print("E2E TEST EXECUTION SUMMARY")
        print("="*60)
        
        # Overall status
        if summary.failed_files == 0 and summary.timeout_files == 0 and summary.error_files == 0:
            print("ALL E2E TESTS PASSED")
        else:
            print("SOME E2E TESTS FAILED")
        
        # Test metrics
        print(f"\nResults:")
        print(f"   Total Files: {summary.total_files}")
        print(f"   Passed: {summary.passed_files}")
        print(f"   Failed: {summary.failed_files}")
        print(f"   Timeout: {summary.timeout_files}")
        print(f"   Error: {summary.error_files}")
        print(f"   Success Rate: {summary.success_rate:.1f}%")
        
        # Performance
        print(f"\nPerformance:")
        print(f"   Total Duration: {summary.total_duration:.1f}s")
        if summary.total_files > 0:
            print(f"   Average per File: {summary.total_duration/summary.total_files:.1f}s")
        
        # Show problem files
        problem_files = [
            r for r in summary.results 
            if r.status in ['failed', 'timeout', 'error']
        ]
        
        if problem_files:
            print(f"\nProblem Files ({len(problem_files)}):")
            for result in problem_files:
                file_name = Path(result.file_path).name
                print(f"   {self._status_text(result.status)} {file_name}: {result.status}")
                if result.stderr:
                    # Show first line of error
                    error_line = result.stderr.split('\n')[0][:80]
                    print(f"      -> {error_line}")
        
        # Business impact
        print(f"\nBusiness Impact:")
        if summary.success_rate == 100.0:
            print("   Production deployment ready")
            print("   User journey validation complete")
            print("   $100K+ MRR protected")
        else:
            print("   Production deployment at risk")
            print("   User experience may be impacted")
            print("   Revenue protection incomplete")
        
        print("="*60)
    
    def _status_text(self, status: str) -> str:
        """Get text indicator for status"""
        indicators = {
            'passed': '[PASS]',
            'failed': '[FAIL]',
            'timeout': '[TIME]',
            'error': '[ERR ]'
        }
        return indicators.get(status, '[UNK ]')

class E2ETestRunner:
    """Main E2E test runner"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.discovery = E2ETestDiscovery(self.project_root)
        self.executor = E2ETestExecutor(self.project_root)
        self.reporter = E2EReportGenerator(self.project_root)
    
    def run_all_e2e_tests(self) -> E2ETestSummary:
        """Run all discovered E2E tests"""
        print("Starting E2E Test Execution")
        print(f"Project Root: {self.project_root}")
        
        # Step 1: Discover test files
        test_files = self.discovery.find_e2e_test_files()
        print(f"Found {len(test_files)} E2E test files")
        
        if not test_files:
            print("No E2E test files found!")
            return self.reporter.generate_summary([])
        
        # Step 2: Run each test file
        results = []
        for i, test_file in enumerate(test_files, 1):
            print(f"\n[{i}/{len(test_files)}] {test_file.name}")
            result = self.executor.run_test_file(test_file)
            results.append(result)
            
            # Show immediate result
            status_text = self.reporter._status_text(result.status)
            print(f"   {status_text} {result.status} ({result.duration:.1f}s)")
            
            # Save intermediate results every 3 tests
            if i % 3 == 0 or i == len(test_files):
                intermediate_summary = self.reporter.generate_summary(results)
                intermediate_file = self.reporter.save_json_report(intermediate_summary)
                print(f"   Progress saved to {intermediate_file.name}")
        
        # Step 3: Generate summary
        summary = self.reporter.generate_summary(results)
        
        # Step 4: Save reports
        report_file = self.reporter.save_json_report(summary)
        print(f"\nReport saved: {report_file}")
        
        # Step 5: Display summary
        self.reporter.print_summary_report(summary)
        
        return summary

def main():
    """CLI entry point"""
    try:
        runner = E2ETestRunner()
        summary = runner.run_all_e2e_tests()
        
        # Exit with appropriate code for CI/CD
        exit_code = 0 if (summary.failed_files == 0 and 
                         summary.timeout_files == 0 and 
                         summary.error_files == 0) else 1
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()