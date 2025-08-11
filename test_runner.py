#!/usr/bin/env python
"""
UNIFIED TEST RUNNER - Single Entry Point for all Netra AI Platform Testing
Replaces all individual test runners with a single, consistent interface.
Automatically saves reports to test_reports/ folder.
"""

import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Define test levels with clear purposes
TEST_LEVELS = {
    "smoke": {
        "description": "Quick smoke tests for basic functionality (< 30 seconds)",
        "purpose": "Pre-commit validation, basic health checks",
        "backend_args": ["--category", "smoke", "--fail-fast", "-x"],
        "frontend_args": [],
        "timeout": 30,
        "run_coverage": False,
        "run_both": True
    },
    "unit": {
        "description": "Unit tests for isolated components (1-2 minutes)",
        "purpose": "Development validation, component testing",
        "backend_args": ["--category", "unit", "-v"],
        "frontend_args": ["--category", "unit"],
        "timeout": 120,
        "run_coverage": False,
        "run_both": True
    },
    "integration": {
        "description": "Integration tests for component interaction (3-5 minutes)",
        "purpose": "Feature validation, API testing",
        "backend_args": ["--category", "integration", "-v"],
        "frontend_args": ["--category", "integration"],
        "timeout": 300,
        "run_coverage": False,
        "run_both": True
    },
    "comprehensive": {
        "description": "Full test suite with coverage (10-15 minutes)",
        "purpose": "Pre-release validation, full system testing",
        "backend_args": ["--coverage", "--parallel=auto", "--html-output"],
        "frontend_args": ["--coverage"],
        "timeout": 900,
        "run_coverage": True,
        "run_both": True
    },
    "critical": {
        "description": "Critical path tests only (1-2 minutes)",
        "purpose": "Essential functionality verification",
        "backend_args": ["--category", "critical", "--fail-fast"],
        "frontend_args": ["--category", "smoke"],
        "timeout": 120,
        "run_coverage": False,
        "run_both": False  # Backend only for critical paths
    }
}

# Test runner configurations
RUNNERS = {
    "simple": "test_scripts/simple_test_runner.py",
    "backend": "scripts/test_backend.py", 
    "frontend": "scripts/test_frontend.py"
}

class UnifiedTestRunner:
    """Unified test runner that manages all testing levels and report generation"""
    
    def __init__(self):
        self.results = {
            "backend": {"status": "pending", "duration": 0, "exit_code": None, "output": ""},
            "frontend": {"status": "pending", "duration": 0, "exit_code": None, "output": ""},
            "overall": {"status": "pending", "start_time": None, "end_time": None}
        }
        
        # Ensure test_reports directory exists
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        
    def run_backend_tests(self, args: List[str], timeout: int = 300) -> Tuple[int, str]:
        """Run backend tests with specified arguments"""
        print(f"\n{'='*60}")
        print("RUNNING BACKEND TESTS")
        print(f"{'='*60}")
        
        start_time = time.time()
        self.results["backend"]["status"] = "running"
        
        # Use backend test runner
        backend_script = PROJECT_ROOT / RUNNERS["backend"]
        if not backend_script.exists():
            print(f"[ERROR] Backend test runner not found: {backend_script}")
            return 1, "Backend test runner not found"
        
        cmd = [sys.executable, str(backend_script)] + args
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=PROJECT_ROOT, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            duration = time.time() - start_time
            self.results["backend"]["duration"] = duration
            self.results["backend"]["exit_code"] = result.returncode
            self.results["backend"]["output"] = result.stdout + "\n" + result.stderr
            self.results["backend"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Print output with proper encoding handling
            try:
                print(result.stdout)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Force ASCII output for Windows terminals with encoding issues
                cleaned_output = result.stdout.encode('ascii', errors='replace').decode('ascii')
                print(cleaned_output)
            
            if result.stderr:
                try:
                    print(result.stderr, file=sys.stderr)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Force ASCII output for Windows terminals with encoding issues
                    cleaned_error = result.stderr.encode('ascii', errors='replace').decode('ascii')
                    print(cleaned_error, file=sys.stderr)
            
            print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Backend tests completed in {duration:.2f}s")
            
            return result.returncode, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.results["backend"]["duration"] = duration
            self.results["backend"]["exit_code"] = -1
            self.results["backend"]["status"] = "timeout"
            self.results["backend"]["output"] = f"Tests timed out after {timeout}s"
            
            print(f"[TIMEOUT] Backend tests timed out after {timeout}s")
            return -1, f"Tests timed out after {timeout}s"
            
    def run_frontend_tests(self, args: List[str], timeout: int = 300) -> Tuple[int, str]:
        """Run frontend tests with specified arguments"""
        print(f"\n{'='*60}")
        print("RUNNING FRONTEND TESTS")
        print(f"{'='*60}")
        
        start_time = time.time()
        self.results["frontend"]["status"] = "running"
        
        # Use simple frontend test runner for smoke tests
        if "--category" in args and "smoke" in str(args):
            frontend_script = PROJECT_ROOT / "scripts" / "test_frontend_simple.py"
        else:
            frontend_script = PROJECT_ROOT / RUNNERS["frontend"]
            
        if not frontend_script.exists():
            print(f"[ERROR] Frontend test runner not found: {frontend_script}")
            return 1, "Frontend test runner not found"
            
        cmd = [sys.executable, str(frontend_script)] + args
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=PROJECT_ROOT, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            duration = time.time() - start_time
            self.results["frontend"]["duration"] = duration
            self.results["frontend"]["exit_code"] = result.returncode
            self.results["frontend"]["output"] = result.stdout + "\n" + result.stderr
            self.results["frontend"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Print output with proper encoding handling
            try:
                print(result.stdout)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Force ASCII output for Windows terminals with encoding issues
                cleaned_output = result.stdout.encode('ascii', errors='replace').decode('ascii')
                print(cleaned_output)
            
            if result.stderr:
                try:
                    print(result.stderr, file=sys.stderr)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Force ASCII output for Windows terminals with encoding issues
                    cleaned_error = result.stderr.encode('ascii', errors='replace').decode('ascii')
                    print(cleaned_error, file=sys.stderr)
            
            print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Frontend tests completed in {duration:.2f}s")
            
            return result.returncode, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.results["frontend"]["duration"] = duration
            self.results["frontend"]["exit_code"] = -1
            self.results["frontend"]["status"] = "timeout"
            self.results["frontend"]["output"] = f"Tests timed out after {timeout}s"
            
            print(f"[TIMEOUT] Frontend tests timed out after {timeout}s")
            return -1, f"Tests timed out after {timeout}s"
    
    def run_simple_tests(self) -> Tuple[int, str]:
        """Run simple test runner for basic validation"""
        print(f"\n{'='*60}")
        print("RUNNING SIMPLE TESTS")
        print(f"{'='*60}")
        
        start_time = time.time()
        
        # Use simple test runner
        simple_script = PROJECT_ROOT / RUNNERS["simple"]
        if not simple_script.exists():
            print(f"[ERROR] Simple test runner not found: {simple_script}")
            return 1, "Simple test runner not found"
            
        cmd = [sys.executable, str(simple_script)]
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=PROJECT_ROOT, 
                capture_output=True, 
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=60
            )
            
            duration = time.time() - start_time
            
            # Update results for both backend and frontend
            self.results["backend"]["duration"] = duration / 2
            self.results["backend"]["exit_code"] = result.returncode
            self.results["backend"]["status"] = "passed" if result.returncode == 0 else "failed"
            self.results["frontend"]["duration"] = duration / 2  
            self.results["frontend"]["exit_code"] = result.returncode
            self.results["frontend"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Print output with proper encoding handling
            try:
                print(result.stdout)
            except (UnicodeEncodeError, UnicodeDecodeError):
                # Force ASCII output for Windows terminals with encoding issues
                cleaned_output = result.stdout.encode('ascii', errors='replace').decode('ascii')
                print(cleaned_output)
            
            if result.stderr:
                try:
                    print(result.stderr, file=sys.stderr)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    # Force ASCII output for Windows terminals with encoding issues
                    cleaned_error = result.stderr.encode('ascii', errors='replace').decode('ascii')
                    print(cleaned_error, file=sys.stderr)
            
            print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] Simple tests completed in {duration:.2f}s")
            
            return result.returncode, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            print(f"[TIMEOUT] Simple tests timed out after 60s")
            return -1, "Tests timed out after 60s"
    
    def save_test_report(self, level: str, config: Dict, output: str, exit_code: int):
        """Save test report to test_reports directory"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Generate comprehensive report
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "test_level": level,
            "configuration": config,
            "results": self.results,
            "summary": {
                "total_duration": self.results["backend"]["duration"] + self.results["frontend"]["duration"],
                "overall_passed": (
                    self.results["backend"]["status"] in ["passed", "skipped"] and 
                    self.results["frontend"]["status"] in ["passed", "skipped"]
                ),
                "exit_code": exit_code
            }
        }
        
        # Save JSON report
        json_path = self.reports_dir / f"test_report_{level}_{timestamp}.json"
        with open(json_path, "w", encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        
        # Generate markdown report
        md_content = f"""# Netra AI Platform - Test Report

**Generated:** {report_data['timestamp']}  
**Test Level:** {level} - {config['description']}  
**Purpose:** {config['purpose']}

## Summary

| Component | Status | Duration | Exit Code |
|-----------|--------|----------|-----------|
| Backend   | {self._status_badge(self.results['backend']['status'])} | {self.results['backend']['duration']:.2f}s | {self.results['backend']['exit_code']} |
| Frontend  | {self._status_badge(self.results['frontend']['status'])} | {self.results['frontend']['duration']:.2f}s | {self.results['frontend']['exit_code']} |

**Overall Status:** {self._status_badge(report_data['summary']['overall_passed'])}  
**Total Duration:** {report_data['summary']['total_duration']:.2f}s  
**Final Exit Code:** {exit_code}

## Test Level Details

- **Description:** {config['description']}
- **Purpose:** {config['purpose']}
- **Timeout:** {config.get('timeout', 300)}s
- **Coverage Enabled:** {'Yes' if config.get('run_coverage', False) else 'No'}

## Configuration

### Backend Args
```
{' '.join(config.get('backend_args', []))}
```

### Frontend Args  
```
{' '.join(config.get('frontend_args', []))}
```

## Test Output

### Backend Output
```
{self.results['backend']['output'][:5000]}{'...(truncated)' if len(self.results['backend']['output']) > 5000 else ''}
```

### Frontend Output
```
{self.results['frontend']['output'][:5000]}{'...(truncated)' if len(self.results['frontend']['output']) > 5000 else ''}
```

---
*Generated by Netra AI Unified Test Runner*
"""
        
        # Save markdown report
        md_path = self.reports_dir / f"test_report_{level}_{timestamp}.md"
        with open(md_path, "w", encoding='utf-8') as f:
            f.write(md_content)
        
        # Save latest report (overwrites previous)
        latest_path = self.reports_dir / f"latest_{level}_report.md"
        with open(latest_path, "w", encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"\n[REPORT] Test report saved:")
        print(f"  - JSON: {json_path}")
        print(f"  - Markdown: {md_path}")
        print(f"  - Latest: {latest_path}")
    
    def _status_badge(self, status) -> str:
        """Convert status to markdown badge"""
        if status == "passed" or status is True:
            return "[PASSED]"
        elif status == "failed" or status is False:
            return "[FAILED]"
        elif status == "timeout":
            return "[TIMEOUT]"
        elif status == "skipped":
            return "[SKIPPED]"
        else:
            return "[PENDING]"
    
    def print_summary(self):
        """Print final test summary"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        total_duration = self.results["backend"]["duration"] + self.results["frontend"]["duration"]
        overall_passed = (
            self.results["backend"]["status"] in ["passed", "skipped"] and 
            self.results["frontend"]["status"] in ["passed", "skipped"]
        )
        
        print(f"Backend:  {self._status_badge(self.results['backend']['status'])} ({self.results['backend']['duration']:.2f}s)")
        print(f"Frontend: {self._status_badge(self.results['frontend']['status'])} ({self.results['frontend']['duration']:.2f}s)")
        print(f"Overall:  {self._status_badge(overall_passed)} ({total_duration:.2f}s)")
        print(f"{'='*60}")

def main():
    parser = argparse.ArgumentParser(
        description="Unified Test Runner for Netra AI Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Test Levels:
{chr(10).join([f"  {level:<12} - {config['description']}" for level, config in TEST_LEVELS.items()])}

Usage Examples:
  # Quick smoke tests (recommended for pre-commit)
  python test_runner.py --level smoke
  
  # Unit tests for development
  python test_runner.py --level unit
  
  # Full comprehensive testing
  python test_runner.py --level comprehensive
  
  # Backend only testing
  python test_runner.py --level unit --backend-only
  
  # Use simple test runner
  python test_runner.py --simple

Purpose Guide:
  - smoke:         Use before committing code, quick validation
  - unit:          Use during development, test individual components  
  - integration:   Use when testing feature interactions
  - comprehensive: Use before releases, full system validation
  - critical:      Use to verify essential functionality only
        """
    )
    
    # Main test level selection
    parser.add_argument(
        "--level", "-l",
        choices=list(TEST_LEVELS.keys()),
        default="smoke",
        help="Test level to run (default: smoke)"
    )
    
    # Alternative runners
    parser.add_argument(
        "--simple",
        action="store_true", 
        help="Use simple test runner (overrides --level)"
    )
    
    # Component selection
    parser.add_argument(
        "--backend-only",
        action="store_true",
        help="Run only backend tests"
    )
    parser.add_argument(
        "--frontend-only", 
        action="store_true",
        help="Run only frontend tests"
    )
    
    # Output options
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="Verbose output"
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip generating test reports"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 80)
    print("NETRA AI PLATFORM - UNIFIED TEST RUNNER")
    print("=" * 80)
    
    # Initialize test runner
    runner = UnifiedTestRunner()
    runner.results["overall"]["start_time"] = time.time()
    
    # Determine test configuration
    if args.simple:
        print(f"Running simple test validation...")
        exit_code, output = runner.run_simple_tests()
        config = {"description": "Simple test validation", "purpose": "Basic functionality check"}
        level = "simple"
    else:
        config = TEST_LEVELS[args.level]
        level = args.level
        
        print(f"Running {level} tests: {config['description']}")
        print(f"Purpose: {config['purpose']}")
        print(f"Timeout: {config.get('timeout', 300)}s")
        
        # Run tests based on selection
        backend_exit = 0
        frontend_exit = 0
        
        if args.backend_only:
            backend_exit, _ = runner.run_backend_tests(
                config['backend_args'], 
                config.get('timeout', 300)
            )
            runner.results["frontend"]["status"] = "skipped"
            exit_code = backend_exit
        elif args.frontend_only:
            frontend_exit, _ = runner.run_frontend_tests(
                config['frontend_args'],
                config.get('timeout', 300)  
            )
            runner.results["backend"]["status"] = "skipped"
            exit_code = frontend_exit
        else:
            # Run both if config specifies it, or if it's a comprehensive level
            if config.get('run_both', True):
                backend_exit, _ = runner.run_backend_tests(
                    config['backend_args'],
                    config.get('timeout', 300)
                )
                frontend_exit, _ = runner.run_frontend_tests(
                    config['frontend_args'], 
                    config.get('timeout', 300)
                )
                exit_code = max(backend_exit, frontend_exit)
            else:
                # Backend only for critical tests
                backend_exit, _ = runner.run_backend_tests(
                    config['backend_args'],
                    config.get('timeout', 300)
                )
                runner.results["frontend"]["status"] = "skipped"
                exit_code = backend_exit
    
    # Record end time
    runner.results["overall"]["end_time"] = time.time()
    runner.results["overall"]["status"] = "passed" if exit_code == 0 else "failed"
    
    # Generate and save report
    if not args.no_report:
        runner.save_test_report(level, config, "", exit_code)
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(exit_code)

if __name__ == "__main__":
    main()