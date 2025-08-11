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
import re
import shutil
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv()

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
        "backend_args": ["--category", "unit", "-v", "--coverage"],
        "frontend_args": ["--category", "unit"],
        "timeout": 120,
        "run_coverage": True,
        "run_both": True
    },
    "integration": {
        "description": "Integration tests for component interaction (3-5 minutes)",
        "purpose": "Feature validation, API testing",
        "backend_args": ["--category", "integration", "-v", "--coverage"],
        "frontend_args": ["--category", "integration"],
        "timeout": 300,
        "run_coverage": True,
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
        "backend_args": ["--category", "critical", "--fail-fast", "--coverage"],
        "frontend_args": ["--category", "smoke"],
        "timeout": 120,
        "run_coverage": True,
        "run_both": False  # Backend only for critical paths
    },
    "all": {
        "description": "All tests including backend, frontend, e2e, integration (20-30 minutes)",
        "purpose": "Complete system validation including all test types",
        "backend_args": ["--coverage", "--parallel=auto", "--html-output"],
        "frontend_args": ["--coverage", "--e2e"],
        "timeout": 1800,
        "run_coverage": True,
        "run_both": True,
        "run_e2e": True
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
            "backend": {
                "status": "pending", 
                "duration": 0, 
                "exit_code": None, 
                "output": "",
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
                "coverage": None
            },
            "frontend": {
                "status": "pending", 
                "duration": 0, 
                "exit_code": None, 
                "output": "",
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
                "coverage": None
            },
            "e2e": {
                "status": "pending",
                "duration": 0,
                "exit_code": None,
                "output": "",
                "test_counts": {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0},
                "coverage": None
            },
            "overall": {"status": "pending", "start_time": None, "end_time": None}
        }
        
        # Ensure test_reports directory and history subdirectory exist
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_dir = self.reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
    def run_backend_tests(self, args: List[str], timeout: int = 300, real_llm_config: Optional[Dict] = None) -> Tuple[int, str]:
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
        
        # Prepare environment with real LLM configuration if provided
        env = os.environ.copy()
        if real_llm_config:
            env["TEST_USE_REAL_LLM"] = "true"
            env["ENABLE_REAL_LLM_TESTING"] = "true"
            env["TEST_LLM_TIMEOUT"] = str(real_llm_config.get("timeout", 45))
            if real_llm_config.get("parallel"):
                env["TEST_PARALLEL"] = str(real_llm_config["parallel"])
            
            # Load .env file to get API keys
            load_dotenv()
            
            # Pass through API keys from environment - Use GEMINI_API_KEY for Google services
            api_keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]
            for key in api_keys:
                value = os.environ.get(key)
                if value:
                    env[key] = value
                    # Also set GOOGLE_API_KEY to GEMINI_API_KEY value for compatibility
                    if key == "GEMINI_API_KEY":
                        env["GOOGLE_API_KEY"] = value
                    print(f"[INFO] Found {key} in environment")
            
            model_name = real_llm_config.get("model", "gemini-2.5-flash")
            print(f"[INFO] Real LLM testing enabled with {model_name} (timeout: {env['TEST_LLM_TIMEOUT']}s)")
        
        try:
            result = subprocess.run(
                cmd, 
                cwd=PROJECT_ROOT,
                env=env,
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
            
            # Parse test counts from output
            self._parse_test_counts(result.stdout + result.stderr, "backend")
            
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
        # Check if this is a smoke test (empty args for frontend in smoke tests)
        if len(args) == 0 or ("--category" in args and "smoke" in str(args)):
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
            
            # Parse test counts from output
            self._parse_test_counts(result.stdout + result.stderr, "frontend")
            
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
    
    def run_e2e_tests(self, args: List[str], timeout: int = 600) -> Tuple[int, str]:
        """Run end-to-end Cypress tests"""
        print(f"\n{'='*60}")
        print("RUNNING E2E TESTS")
        print(f"{'='*60}")
        
        start_time = time.time()
        self.results["e2e"]["status"] = "running"
        
        # Change to frontend directory for Cypress
        frontend_dir = PROJECT_ROOT / "frontend"
        
        # Check if npm and cypress are available
        check_cmd = ["npm", "list", "cypress", "--depth=0"]
        try:
            subprocess.run(check_cmd, cwd=frontend_dir, capture_output=True, timeout=10)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("[ERROR] Cypress not found. Please run 'npm install' in frontend directory")
            self.results["e2e"]["status"] = "failed"
            self.results["e2e"]["exit_code"] = 1
            return 1, "Cypress not installed"
        
        # Run Cypress tests
        cmd = ["npm", "run", "cy:run", "--", "--reporter", "json"]
        
        try:
            result = subprocess.run(
                cmd,
                cwd=frontend_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=timeout
            )
            
            duration = time.time() - start_time
            self.results["e2e"]["duration"] = duration
            self.results["e2e"]["exit_code"] = result.returncode
            self.results["e2e"]["output"] = result.stdout + "\n" + result.stderr
            self.results["e2e"]["status"] = "passed" if result.returncode == 0 else "failed"
            
            # Parse test counts from Cypress output
            self._parse_cypress_counts(result.stdout + result.stderr)
            
            # Print output with proper encoding handling
            try:
                print(result.stdout)
            except (UnicodeEncodeError, UnicodeDecodeError):
                cleaned_output = result.stdout.encode('ascii', errors='replace').decode('ascii')
                print(cleaned_output)
            
            if result.stderr:
                try:
                    print(result.stderr, file=sys.stderr)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    cleaned_error = result.stderr.encode('ascii', errors='replace').decode('ascii')
                    print(cleaned_error, file=sys.stderr)
            
            print(f"[{'PASS' if result.returncode == 0 else 'FAIL'}] E2E tests completed in {duration:.2f}s")
            
            return result.returncode, result.stdout + result.stderr
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            self.results["e2e"]["duration"] = duration
            self.results["e2e"]["exit_code"] = -1
            self.results["e2e"]["status"] = "timeout"
            self.results["e2e"]["output"] = f"Tests timed out after {timeout}s"
            
            print(f"[TIMEOUT] E2E tests timed out after {timeout}s")
            return -1, f"Tests timed out after {timeout}s"
    
    def _parse_cypress_counts(self, output: str):
        """Parse test counts from Cypress output"""
        counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        
        # Cypress output patterns
        patterns = [
            (r"(\d+) passing", "passed"),
            (r"(\d+) failing", "failed"),
            (r"(\d+) pending", "skipped"),
            (r"Tests:\s+(\d+)", "total"),
            (r"Passing:\s+(\d+)", "passed"),
            (r"Failing:\s+(\d+)", "failed"),
            (r"Pending:\s+(\d+)", "skipped"),
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                if key == "total":
                    counts["total"] = value
                else:
                    counts[key] = max(counts[key], value)  # Take the max to avoid double counting
        
        # Calculate total if not explicitly found
        if counts["total"] == 0:
            counts["total"] = counts["passed"] + counts["failed"] + counts["skipped"]
        
        self.results["e2e"]["test_counts"] = counts
    
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
            self.results["backend"]["output"] = result.stdout + "\n" + result.stderr
            self.results["frontend"]["duration"] = duration / 2  
            self.results["frontend"]["exit_code"] = result.returncode
            self.results["frontend"]["status"] = "passed" if result.returncode == 0 else "failed"
            self.results["frontend"]["output"] = ""
            
            # Parse test counts from output
            self._parse_test_counts(result.stdout + result.stderr, "backend")
            
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
    
    def _parse_test_counts(self, output: str, component: str):
        """Parse test counts from pytest/jest output"""
        counts = {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}
        
        # Common pytest patterns
        patterns = [
            (r"(\d+) passed", "passed"),
            (r"(\d+) failed", "failed"),
            (r"(\d+) skipped", "skipped"),
            (r"(\d+) error", "errors"),
            (r"(\d+) deselected", "skipped"),
            (r"(\d+) xfailed", "skipped"),
            (r"(\d+) xpassed", "passed"),
        ]
        
        # Jest patterns for frontend
        if component == "frontend":
            patterns.extend([
                (r"Tests:\s+(\d+) passed", "passed"),
                (r"Tests:\s+(\d+) failed", "failed"),
                (r"Tests:\s+(\d+) skipped", "skipped"),
                (r"Tests:\s+(\d+) total", "total"),
            ])
        
        for pattern, key in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                value = int(match.group(1))
                if key == "total":
                    counts["total"] = value
                else:
                    counts[key] += value
        
        # Calculate total if not explicitly found
        if counts["total"] == 0:
            counts["total"] = counts["passed"] + counts["failed"] + counts["skipped"] + counts["errors"]
        
        # Parse coverage if present
        coverage_match = re.search(r"TOTAL\s+\d+\s+\d+\s+([\d.]+)%", output)
        if not coverage_match:
            coverage_match = re.search(r"Overall coverage:\s*([\d.]+)%", output)
        if not coverage_match:
            coverage_match = re.search(r"Statements\s*:\s*([\d.]+)%", output)
        
        if coverage_match:
            self.results[component]["coverage"] = float(coverage_match.group(1))
        
        self.results[component]["test_counts"] = counts
    
    def save_test_report(self, level: str, config: Dict, output: str, exit_code: int):
        """Save test report to test_reports directory with latest/history structure"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Calculate total test counts
        backend_counts = self.results["backend"]["test_counts"]
        frontend_counts = self.results["frontend"]["test_counts"]
        e2e_counts = self.results.get("e2e", {}).get("test_counts", {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0})
        total_counts = {
            "total": backend_counts["total"] + frontend_counts["total"] + e2e_counts["total"],
            "passed": backend_counts["passed"] + frontend_counts["passed"] + e2e_counts["passed"],
            "failed": backend_counts["failed"] + frontend_counts["failed"] + e2e_counts["failed"],
            "skipped": backend_counts["skipped"] + frontend_counts["skipped"] + e2e_counts["skipped"],
            "errors": backend_counts["errors"] + frontend_counts["errors"] + e2e_counts["errors"]
        }
        
        # Calculate overall coverage if available
        overall_coverage = None
        if self.results["backend"]["coverage"] is not None:
            overall_coverage = self.results["backend"]["coverage"]
            if self.results["frontend"]["coverage"] is not None:
                # Average of backend and frontend coverage
                overall_coverage = (self.results["backend"]["coverage"] + self.results["frontend"]["coverage"]) / 2
        elif self.results["frontend"]["coverage"] is not None:
            overall_coverage = self.results["frontend"]["coverage"]
        
        # Generate comprehensive report data
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
                "exit_code": exit_code,
                "test_counts": total_counts,
                "overall_coverage": overall_coverage
            }
        }
        
        # Generate markdown report following spec structure
        md_content = f"""# Netra AI Platform - Test Report

**Generated:** {report_data['timestamp']}  
**Test Level:** {level} - {config['description']}  
**Purpose:** {config['purpose']}

## Test Summary

**Total Tests:** {total_counts['total']}  
**Passed:** {total_counts['passed']}  
**Failed:** {total_counts['failed']}  
**Skipped:** {total_counts['skipped']}  
**Errors:** {total_counts['errors']}  
**Overall Status:** {self._status_badge(report_data['summary']['overall_passed'])}

### Component Breakdown

| Component | Total | Passed | Failed | Skipped | Errors | Duration | Status |
|-----------|-------|--------|--------|---------|--------|----------|--------|
| Backend   | {backend_counts['total']} | {backend_counts['passed']} | {backend_counts['failed']} | {backend_counts['skipped']} | {backend_counts['errors']} | {self.results['backend']['duration']:.2f}s | {self._status_badge(self.results['backend']['status'])} |
| Frontend  | {frontend_counts['total']} | {frontend_counts['passed']} | {frontend_counts['failed']} | {frontend_counts['skipped']} | {frontend_counts['errors']} | {self.results['frontend']['duration']:.2f}s | {self._status_badge(self.results['frontend']['status'])} |"""
        
        # Add E2E row if E2E tests were run
        if self.results.get("e2e", {}).get("status") != "pending":
            md_content += f"""
| E2E       | {e2e_counts['total']} | {e2e_counts['passed']} | {e2e_counts['failed']} | {e2e_counts['skipped']} | {e2e_counts['errors']} | {self.results['e2e']['duration']:.2f}s | {self._status_badge(self.results['e2e']['status'])} |"""
        
        md_content += """
"""
        
        # Add coverage summary if applicable
        if config.get('run_coverage', False) and overall_coverage is not None:
            md_content += f"""
## Coverage Summary

**Overall Coverage:** {overall_coverage:.1f}%
"""
            if self.results["backend"]["coverage"] is not None:
                md_content += f"**Backend Coverage:** {self.results['backend']['coverage']:.1f}%  \n"
            if self.results["frontend"]["coverage"] is not None:
                md_content += f"**Frontend Coverage:** {self.results['frontend']['coverage']:.1f}%  \n"
        
        md_content += f"""
## Environment and Configuration

- **Test Level:** {level}
- **Description:** {config['description']}
- **Purpose:** {config['purpose']}
- **Timeout:** {config.get('timeout', 300)}s
- **Coverage Enabled:** {'Yes' if config.get('run_coverage', False) else 'No'}
- **Total Duration:** {report_data['summary']['total_duration']:.2f}s
- **Exit Code:** {exit_code}

### Backend Configuration
```
{' '.join(config.get('backend_args', []))}
```

### Frontend Configuration
```
{' '.join(config.get('frontend_args', []))}
```

## Test Output

### Backend Output
```
{self.results['backend']['output'][:10000]}{'...(truncated)' if len(self.results['backend']['output']) > 10000 else ''}
```

### Frontend Output
```
{self.results['frontend']['output'][:10000]}{'...(truncated)' if len(self.results['frontend']['output']) > 10000 else ''}
```"""
        
        # Add E2E output if E2E tests were run
        if self.results.get("e2e", {}).get("status") != "pending":
            md_content += f"""

### E2E Output
```
{self.results['e2e']['output'][:10000]}{'...(truncated)' if len(self.results['e2e']['output']) > 10000 else ''}
```"""
        
        md_content += """
"""
        
        # Add error summary if there were failures
        if total_counts['failed'] > 0 or total_counts['errors'] > 0:
            md_content += """
## Error Summary

"""
            # Extract error details from output
            if backend_counts['failed'] > 0 or backend_counts['errors'] > 0:
                md_content += "### Backend Errors\n"
                # Extract FAILED lines from output
                for line in self.results['backend']['output'].split('\n'):
                    if 'FAILED' in line or 'ERROR' in line:
                        md_content += f"- {line.strip()}\n"
                md_content += "\n"
            
            if frontend_counts['failed'] > 0 or frontend_counts['errors'] > 0:
                md_content += "### Frontend Errors\n"
                for line in self.results['frontend']['output'].split('\n'):
                    if 'FAILED' in line or 'ERROR' in line or 'FAIL' in line:
                        md_content += f"- {line.strip()}\n"
                md_content += "\n"
        
        md_content += """
---
*Generated by Netra AI Unified Test Runner v3.0*
"""
        
        # Check if latest report exists and move to history
        latest_path = self.reports_dir / f"latest_{level}_report.md"
        if latest_path.exists():
            # Move existing latest to history with timestamp from file modification time
            mod_time = datetime.fromtimestamp(latest_path.stat().st_mtime)
            history_timestamp = mod_time.strftime('%Y%m%d_%H%M%S')
            history_path = self.history_dir / f"test_report_{level}_{history_timestamp}.md"
            shutil.move(str(latest_path), str(history_path))
            print(f"[ARCHIVE] Previous report moved to history: {history_path.name}")
        
        # Save new latest report (no more per-run files)
        with open(latest_path, "w", encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"\n[REPORT] Test report saved:")
        print(f"  - Latest: {latest_path}")
        print(f"  - History folder: {self.history_dir}")
    
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
        """Print final test summary with test counts"""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        
        # Calculate totals
        backend_counts = self.results["backend"]["test_counts"]
        frontend_counts = self.results["frontend"]["test_counts"]
        e2e_counts = self.results.get("e2e", {}).get("test_counts", {"total": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0})
        
        total_counts = {
            "total": backend_counts["total"] + frontend_counts["total"] + e2e_counts["total"],
            "passed": backend_counts["passed"] + frontend_counts["passed"] + e2e_counts["passed"],
            "failed": backend_counts["failed"] + frontend_counts["failed"] + e2e_counts["failed"],
            "skipped": backend_counts["skipped"] + frontend_counts["skipped"] + e2e_counts["skipped"],
            "errors": backend_counts["errors"] + frontend_counts["errors"] + e2e_counts["errors"]
        }
        
        total_duration = self.results["backend"]["duration"] + self.results["frontend"]["duration"] + self.results.get("e2e", {}).get("duration", 0)
        overall_passed = (
            self.results["backend"]["status"] in ["passed", "skipped"] and 
            self.results["frontend"]["status"] in ["passed", "skipped"] and
            (self.results.get("e2e", {}).get("status", "skipped") in ["passed", "skipped", "pending"])
        )
        
        # Print test counts
        print(f"Total Tests: {total_counts['total']}")
        print(f"  Passed:    {total_counts['passed']}")
        print(f"  Failed:    {total_counts['failed']}")
        print(f"  Skipped:   {total_counts['skipped']}")
        print(f"  Errors:    {total_counts['errors']}")
        print(f"{'='*60}")
        
        # Print component status
        print(f"Backend:  {self._status_badge(self.results['backend']['status'])} ({backend_counts['total']} tests, {self.results['backend']['duration']:.2f}s)")
        print(f"Frontend: {self._status_badge(self.results['frontend']['status'])} ({frontend_counts['total']} tests, {self.results['frontend']['duration']:.2f}s)")
        if self.results.get("e2e", {}).get("status") != "pending":
            print(f"E2E:      {self._status_badge(self.results['e2e']['status'])} ({e2e_counts['total']} tests, {self.results['e2e']['duration']:.2f}s)")
        print(f"Overall:  {self._status_badge(overall_passed)} ({total_duration:.2f}s)")
        
        # Print coverage if available
        if self.results["backend"]["coverage"] is not None or self.results["frontend"]["coverage"] is not None:
            print(f"{'='*60}")
            print("COVERAGE:")
            if self.results["backend"]["coverage"] is not None:
                print(f"  Backend:  {self.results['backend']['coverage']:.1f}%")
            if self.results["frontend"]["coverage"] is not None:
                print(f"  Frontend: {self.results['frontend']['coverage']:.1f}%")
        
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
  
  # Run ALL tests (backend, frontend, E2E) - comprehensive validation
  python test_runner.py --level all
  
  # Real LLM testing examples:
  # Unit tests with real LLM calls
  python test_runner.py --level unit --real-llm
  
  # Integration tests with specific model
  python test_runner.py --level integration --real-llm --llm-model gemini-2.5-pro
  
  # Critical tests sequentially to avoid rate limits
  python test_runner.py --level critical --real-llm --parallel 1
  
  # Comprehensive with extended timeout
  python test_runner.py --level comprehensive --real-llm --llm-timeout 120

Purpose Guide:
  - smoke:         Use before committing code, quick validation (never uses real LLM)
  - unit:          Use during development, test individual components  
  - integration:   Use when testing feature interactions
  - comprehensive: Use before releases, full system validation
  - critical:      Use to verify essential functionality only
  - all:           Complete validation including backend, frontend, and E2E tests
  
Real LLM Testing:
  - Adds --real-llm flag to use actual API calls instead of mocks
  - Increases test duration 3-5x and incurs API costs
  - Use gemini-2.5-flash (default) for cost efficiency
  - Run sequentially (--parallel 1) with production keys to avoid rate limits
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
    
    # Real LLM testing options
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Use real LLM API calls instead of mocks (increases test duration and cost)"
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gemini-2.5-flash",
        choices=["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4", "gpt-3.5-turbo", "claude-3-sonnet"],
        help="LLM model to use for real tests (default: gemini-2.5-flash for cost efficiency)"
    )
    parser.add_argument(
        "--llm-timeout",
        type=int,
        default=30,
        help="Timeout in seconds for individual LLM calls (default: 30, recommended: 30-120)"
    )
    parser.add_argument(
        "--parallel",
        type=str,
        default="auto",
        help="Parallelism for tests: auto, 1 (sequential), or number of workers"
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
        
        # Prepare real LLM configuration if requested
        real_llm_config = None
        if args.real_llm:
            # Smoke tests should never use real LLM for speed
            if level == "smoke":
                print("[WARNING] Real LLM testing disabled for smoke tests (use unit or higher)")
            else:
                real_llm_config = {
                    "model": args.llm_model,
                    "timeout": args.llm_timeout,
                    "parallel": args.parallel
                }
                print(f"[INFO] Real LLM testing enabled")
                print(f"  - Model: {args.llm_model}")
                print(f"  - Timeout: {args.llm_timeout}s per call")
                print(f"  - Parallelism: {args.parallel}")
                
                # Adjust test timeout for real LLM tests
                adjusted_timeout = config.get('timeout', 300) * 3  # Triple timeout for real LLM
                config['timeout'] = adjusted_timeout
                print(f"  - Adjusted test timeout: {adjusted_timeout}s")
        
        # Run tests based on selection
        backend_exit = 0
        frontend_exit = 0
        
        if args.backend_only:
            backend_exit, _ = runner.run_backend_tests(
                config['backend_args'], 
                config.get('timeout', 300),
                real_llm_config
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
                    config.get('timeout', 300),
                    real_llm_config
                )
                frontend_exit, _ = runner.run_frontend_tests(
                    config['frontend_args'], 
                    config.get('timeout', 300)
                )
                exit_code = max(backend_exit, frontend_exit)
                
                # Run E2E tests if specified
                if config.get('run_e2e', False):
                    e2e_exit, _ = runner.run_e2e_tests(
                        [],  # E2E tests don't need additional args
                        config.get('timeout', 600)
                    )
                    exit_code = max(exit_code, e2e_exit)
            else:
                # Backend only for critical tests
                backend_exit, _ = runner.run_backend_tests(
                    config['backend_args'],
                    config.get('timeout', 300),
                    real_llm_config
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