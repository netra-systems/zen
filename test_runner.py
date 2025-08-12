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
import multiprocessing
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from dotenv import load_dotenv

# Import enhanced reporter if available
try:
    from scripts.enhanced_test_reporter import EnhancedTestReporter
    ENHANCED_REPORTER_AVAILABLE = True
except ImportError:
    ENHANCED_REPORTER_AVAILABLE = False

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables from .env file
load_dotenv()

# Determine optimal parallelization
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT - 1, 8)  # Leave one CPU free

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
        "backend_args": ["--category", "unit", "-v", "--coverage", "--fail-fast", f"--parallel={min(4, OPTIMAL_WORKERS)}"],
        "frontend_args": ["--category", "unit"],
        "timeout": 120,
        "run_coverage": True,
        "run_both": True
    },
    "integration": {
        "description": "Integration tests for component interaction (3-5 minutes)",
        "purpose": "Feature validation, API testing",
        "backend_args": ["--category", "integration", "-v", "--coverage", "--fail-fast", f"--parallel={min(4, OPTIMAL_WORKERS)}"],
        "frontend_args": ["--category", "integration"],
        "timeout": 300,
        "run_coverage": True,
        "run_both": True
    },
    "comprehensive": {
        "description": "Full test suite with coverage (10-15 minutes)",
        "purpose": "Pre-release validation, full system testing",
        "backend_args": ["--coverage", f"--parallel={min(6, OPTIMAL_WORKERS)}", "--html-output", "--fail-fast"],
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
        "backend_args": ["--coverage", f"--parallel={OPTIMAL_WORKERS}", "--html-output", "--fail-fast"],
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
        self.cpu_count = CPU_COUNT
        self.optimal_workers = OPTIMAL_WORKERS
        self.test_categories = defaultdict(list)  # For organizing tests by category
        
        # Initialize enhanced reporter if available
        self.enhanced_reporter = None
        if ENHANCED_REPORTER_AVAILABLE:
            try:
                self.enhanced_reporter = EnhancedTestReporter()
                print("[INFO] Enhanced Test Reporter enabled")
            except Exception as e:
                print(f"[WARNING] Could not initialize Enhanced Reporter: {e}")
        
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
        
    def categorize_test(self, test_path: str, component: str = "backend") -> str:
        """Categorize test based on file path and name"""
        path_lower = test_path.lower()
        
        if component == "backend":
            if "unit" in path_lower:
                return "unit"
            elif "integration" in path_lower:
                return "integration"
            elif "service" in path_lower:
                return "service"
            elif "route" in path_lower or "api" in path_lower:
                return "api"
            elif "database" in path_lower or "repository" in path_lower:
                return "database"
            elif "agent" in path_lower:
                return "agent"
            elif "websocket" in path_lower or "ws_" in path_lower:
                return "websocket"
            elif "auth" in path_lower or "security" in path_lower:
                return "auth"
            elif "llm" in path_lower:
                return "llm"
            else:
                return "other"
        else:  # frontend
            if "component" in path_lower:
                return "component"
            elif "hook" in path_lower:
                return "hook"
            elif "service" in path_lower or "api" in path_lower:
                return "service"
            elif "store" in path_lower:
                return "store"
            elif "auth" in path_lower:
                return "auth"
            elif "websocket" in path_lower or "ws" in path_lower:
                return "websocket"
            elif "util" in path_lower or "helper" in path_lower:
                return "utility"
            else:
                return "other"
    
    def organize_failures_by_category(self, failures: List[Dict]) -> Dict[str, List[Dict]]:
        """Organize failures by category for better processing"""
        organized = defaultdict(list)
        for failure in failures:
            category = self.categorize_test(failure.get("test_path", ""), failure.get("component", "backend"))
            organized[category].append(failure)
        return dict(organized)
        
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
            
            # Extract and update failing tests
            if result.returncode != 0:
                failures = self._extract_failing_tests(result.stdout + result.stderr, "backend")
                if failures:
                    self.update_failing_tests("backend", failures)
            
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
            
            # Extract and update failing tests
            if result.returncode != 0:
                failures = self._extract_failing_tests(result.stdout + result.stderr, "frontend")
                if failures:
                    self.update_failing_tests("frontend", failures)
            
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
            
            # Extract and update failing tests
            if result.returncode != 0:
                failures = self._extract_failing_tests(result.stdout + result.stderr, "e2e")
                if failures:
                    self.update_failing_tests("e2e", failures)
            
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
    
    def _extract_failing_tests(self, output: str, component: str) -> List[Dict]:
        """Extract failing test details from test output"""
        failing_tests = []
        
        if component == "backend":
            # Parse pytest failures
            # Look for FAILED lines
            failure_pattern = r"FAILED\s+([^\s]+)::([^\s]+)(?:\[([^\]]+)\])?\s*-\s*(.+)"
            for match in re.finditer(failure_pattern, output):
                test_path = match.group(1)
                test_name = match.group(2)
                if match.group(3):  # Parametrized test
                    test_name += f"[{match.group(3)}]"
                error_msg = match.group(4)
                
                failing_tests.append({
                    "test_path": test_path,
                    "test_name": test_name,
                    "error_type": self._extract_error_type(error_msg),
                    "error_message": error_msg[:500],  # Limit message length
                    "traceback": self._extract_traceback(output, test_name)[:1000],
                    "first_failed": datetime.now().isoformat(),
                    "consecutive_failures": 1
                })
            
            # Also look for ERROR lines
            error_pattern = r"ERROR\s+([^\s]+)(?:::([^\s]+))?\s*-\s*(.+)"
            for match in re.finditer(error_pattern, output):
                test_path = match.group(1)
                test_name = match.group(2) or "setup/teardown"
                error_msg = match.group(3)
                
                failing_tests.append({
                    "test_path": test_path,
                    "test_name": test_name,
                    "error_type": "Error",
                    "error_message": error_msg[:500],
                    "traceback": "",
                    "first_failed": datetime.now().isoformat(),
                    "consecutive_failures": 1
                })
                
        elif component == "frontend":
            # Parse Jest/Cypress failures
            # Look for FAIL lines in Jest
            fail_pattern = r"FAIL\s+([^\s]+)"
            for match in re.finditer(fail_pattern, output):
                test_path = match.group(1)
                
                # Extract test names from the output after the FAIL line
                test_section = output[match.end():match.end() + 2000]
                test_name_pattern = r"✕\s+(.+?)\s*\(\d+\s*ms\)"
                for test_match in re.finditer(test_name_pattern, test_section):
                    test_name = test_match.group(1)
                    
                    failing_tests.append({
                        "test_path": test_path,
                        "test_name": test_name,
                        "error_type": "AssertionError",
                        "error_message": "Test failed",
                        "first_failed": datetime.now().isoformat(),
                        "consecutive_failures": 1
                    })
            
            # Look for Cypress failures
            cypress_pattern = r"\d+\)\s+(.+?)\n\s+(.+?):"
            for match in re.finditer(cypress_pattern, output):
                if "failing" in output[max(0, match.start()-100):match.start()]:
                    test_name = match.group(1)
                    test_path = match.group(2)
                    
                    failing_tests.append({
                        "test_path": test_path,
                        "test_name": test_name,
                        "error_type": "CypressError",
                        "error_message": "Cypress test failed",
                        "first_failed": datetime.now().isoformat(),
                        "consecutive_failures": 1
                    })
        
        return failing_tests
    
    def _extract_error_type(self, error_msg: str) -> str:
        """Extract error type from error message"""
        if "AssertionError" in error_msg:
            return "AssertionError"
        elif "ImportError" in error_msg or "ModuleNotFoundError" in error_msg:
            return "ImportError"
        elif "AttributeError" in error_msg:
            return "AttributeError"
        elif "TypeError" in error_msg:
            return "TypeError"
        elif "ValueError" in error_msg:
            return "ValueError"
        elif "KeyError" in error_msg:
            return "KeyError"
        elif "TimeoutError" in error_msg or "timeout" in error_msg.lower():
            return "TimeoutError"
        else:
            return "Error"
    
    def _extract_traceback(self, output: str, test_name: str) -> str:
        """Extract last few lines of traceback for a test"""
        # Find the test in output and get traceback
        test_pos = output.find(test_name)
        if test_pos == -1:
            return ""
        
        # Look for traceback after test name
        traceback_section = output[test_pos:min(test_pos + 3000, len(output))]
        
        # Get last 5 lines of traceback
        lines = traceback_section.split('\n')
        traceback_lines = []
        for line in lines:
            if line.strip().startswith('>') or 'assert' in line.lower() or '==' in line:
                traceback_lines.append(line)
            if len(traceback_lines) >= 5:
                break
        
        return '\n'.join(traceback_lines)
    
    def load_failing_tests(self) -> Dict:
        """Load existing failing tests from JSON file"""
        failing_tests_path = self.reports_dir / "failing_tests.json"
        
        if failing_tests_path.exists():
            try:
                with open(failing_tests_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        
        # Return default structure if file doesn't exist or is invalid
        return {
            "last_updated": datetime.now().isoformat(),
            "backend": {"count": 0, "failures": []},
            "frontend": {"count": 0, "failures": []},
            "e2e": {"count": 0, "failures": []}
        }
    
    def update_failing_tests(self, component: str, new_failures: List[Dict], passed_tests: List[str] = None):
        """Update failing tests log with new results"""
        failing_tests = self.load_failing_tests()
        
        # Update timestamp
        failing_tests["last_updated"] = datetime.now().isoformat()
        
        if component not in failing_tests:
            failing_tests[component] = {"count": 0, "failures": []}
        
        # Remove tests that passed
        if passed_tests:
            failing_tests[component]["failures"] = [
                f for f in failing_tests[component]["failures"]
                if f"{f['test_path']}::{f['test_name']}" not in passed_tests
            ]
        
        # Update or add new failures
        for new_failure in new_failures:
            existing = None
            for i, old_failure in enumerate(failing_tests[component]["failures"]):
                if (old_failure["test_path"] == new_failure["test_path"] and 
                    old_failure["test_name"] == new_failure["test_name"]):
                    existing = i
                    break
            
            if existing is not None:
                # Update existing failure
                old_failure = failing_tests[component]["failures"][existing]
                old_failure["consecutive_failures"] += 1
                old_failure["error_message"] = new_failure["error_message"]
                old_failure["error_type"] = new_failure["error_type"]
                if "traceback" in new_failure:
                    old_failure["traceback"] = new_failure["traceback"]
            else:
                # Add new failure
                failing_tests[component]["failures"].append(new_failure)
        
        # Update counts
        failing_tests[component]["count"] = len(failing_tests[component]["failures"])
        
        # Save updated failing tests
        failing_tests_path = self.reports_dir / "failing_tests.json"
        with open(failing_tests_path, 'w', encoding='utf-8') as f:
            json.dump(failing_tests, f, indent=2)
        
        return failing_tests
    
    def run_failing_tests(self, max_fixes: int = None, backend_only: bool = False, frontend_only: bool = False) -> int:
        """Run only the currently failing tests"""
        failing_tests = self.load_failing_tests()
        total_failures = 0
        fixed_count = 0
        
        # Run backend failing tests
        if not frontend_only and failing_tests["backend"]["count"] > 0:
            print(f"\n[FAILING TESTS] Running {failing_tests['backend']['count']} failing backend tests...")
            
            for failure in failing_tests["backend"]["failures"][:max_fixes]:
                test_spec = f"{failure['test_path']}::{failure['test_name']}"
                print(f"  Testing: {test_spec}")
                
                cmd = [sys.executable, "-m", "pytest", test_spec, "-xvs"]
                result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"    ✓ FIXED: {failure['test_name']}")
                    fixed_count += 1
                else:
                    print(f"    ✗ Still failing: {failure['test_name']}")
                    total_failures += 1
        
        # Run frontend failing tests  
        if not backend_only and failing_tests["frontend"]["count"] > 0:
            print(f"\n[FAILING TESTS] Running {failing_tests['frontend']['count']} failing frontend tests...")
            
            for failure in failing_tests["frontend"]["failures"][:max_fixes]:
                print(f"  Testing: {failure['test_path']} - {failure['test_name']}")
                
                # Run specific Jest test
                cmd = ["npm", "test", "--", failure["test_path"], "--testNamePattern", failure["test_name"]]
                result = subprocess.run(cmd, cwd=PROJECT_ROOT / "frontend", capture_output=True, text=True)
                
                if result.returncode == 0:
                    print(f"    ✓ FIXED: {failure['test_name']}")
                    fixed_count += 1
                else:
                    print(f"    ✗ Still failing: {failure['test_name']}")
                    total_failures += 1
        
        print(f"\n[SUMMARY] Fixed {fixed_count} tests, {total_failures} still failing")
        return total_failures
    
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
        
        # Track test files
        test_files = set()
        
        # Count test files first
        if component == "backend":
            # Extract test files from pytest output
            file_pattern = r"(\S+\.py)::"
            test_files = set(re.findall(file_pattern, output))
            counts["test_files"] = len(test_files)
        elif component == "frontend":
            # Extract test files from Jest output
            file_pattern = r"(PASS|FAIL)\s+(\S+\.(test|spec)\.(ts|tsx|js|jsx))"
            for match in re.finditer(file_pattern, output):
                test_files.add(match.group(2))
            counts["test_files"] = len(test_files)
        
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
        
        # Use enhanced reporter if available
        if self.enhanced_reporter:
            try:
                # Generate comprehensive report
                report_content = self.enhanced_reporter.generate_comprehensive_report(
                    level=level,
                    results=self.results,
                    config=config,
                    exit_code=exit_code
                )
                
                # Calculate metrics for enhanced reporter
                backend_counts = self.results["backend"]["test_counts"]
                frontend_counts = self.results["frontend"]["test_counts"]
                
                metrics = {
                    "total_tests": backend_counts["total"] + frontend_counts["total"],
                    "passed": backend_counts["passed"] + frontend_counts["passed"],
                    "failed": backend_counts["failed"] + frontend_counts["failed"],
                    "coverage": self.results["backend"].get("coverage") or self.results["frontend"].get("coverage")
                }
                
                # Save using enhanced reporter
                self.enhanced_reporter.save_report(
                    level=level,
                    report_content=report_content,
                    results=self.results,
                    metrics=metrics
                )
                
                # Also run cleanup periodically
                import random
                if random.random() < 0.1:  # 10% chance to run cleanup
                    print("[INFO] Running report cleanup...")
                    self.enhanced_reporter.cleanup_old_reports(keep_days=7)
                
                return
            except Exception as e:
                print(f"[WARNING] Enhanced reporter failed, using standard: {e}")
        
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
        
        if not self.enhanced_reporter:
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
    
    def generate_json_report(self, level: str, config: Dict, exit_code: int) -> Dict:
        """Generate JSON report for CI/CD integration"""
        timestamp = datetime.now().isoformat()
        duration = self.results["overall"]["end_time"] - self.results["overall"]["start_time"]
        
        # Calculate total test counts
        backend_counts = self.results["backend"]["test_counts"]
        frontend_counts = self.results["frontend"]["test_counts"]
        e2e_counts = self.results.get("e2e", {}).get("test_counts", {"total": 0, "passed": 0, "failed": 0})
        
        total_counts = {
            "total": backend_counts["total"] + frontend_counts["total"] + e2e_counts["total"],
            "passed": backend_counts["passed"] + frontend_counts["passed"] + e2e_counts["passed"],
            "failed": backend_counts["failed"] + frontend_counts["failed"] + e2e_counts["failed"],
            "skipped": backend_counts.get("skipped", 0) + frontend_counts.get("skipped", 0) + e2e_counts.get("skipped", 0),
            "errors": backend_counts.get("errors", 0) + frontend_counts.get("errors", 0) + e2e_counts.get("errors", 0),
        }
        
        return {
            "timestamp": timestamp,
            "level": level,
            "status": "passed" if exit_code == 0 else "failed",
            "exit_code": exit_code,
            "duration": duration,
            "environment": {
                "staging": getattr(self, "staging_mode", False),
                "staging_url": os.getenv("STAGING_URL", ""),
                "staging_api_url": os.getenv("STAGING_API_URL", ""),
                "pr_number": os.getenv("PR_NUMBER", ""),
                "pr_branch": os.getenv("PR_BRANCH", ""),
            },
            "summary": {
                "total": total_counts["total"],
                "passed": total_counts["passed"],
                "failed": total_counts["failed"],
                "skipped": total_counts["skipped"],
                "errors": total_counts["errors"],
                "duration": duration,
            },
            "components": {
                "backend": {
                    "status": self.results["backend"]["status"],
                    "duration": self.results["backend"]["duration"],
                    "tests": backend_counts,
                    "coverage": self.results["backend"]["coverage"],
                },
                "frontend": {
                    "status": self.results["frontend"]["status"],
                    "duration": self.results["frontend"]["duration"],
                    "tests": frontend_counts,
                    "coverage": self.results["frontend"]["coverage"],
                },
                "e2e": {
                    "status": self.results.get("e2e", {}).get("status", "skipped"),
                    "duration": self.results.get("e2e", {}).get("duration", 0),
                    "tests": e2e_counts,
                }
            },
            "configuration": {
                "level": level,
                "description": config.get("description", ""),
                "purpose": config.get("purpose", ""),
                "timeout": config.get("timeout", 300),
                "coverage_enabled": config.get("run_coverage", False),
            }
        }
    
    def generate_text_report(self, level: str, config: Dict, exit_code: int) -> str:
        """Generate plain text report"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        duration = self.results["overall"]["end_time"] - self.results["overall"]["start_time"]
        
        # Calculate total test counts
        backend_counts = self.results["backend"]["test_counts"]
        frontend_counts = self.results["frontend"]["test_counts"]
        
        total_counts = {
            "total": backend_counts["total"] + frontend_counts["total"],
            "passed": backend_counts["passed"] + frontend_counts["passed"],
            "failed": backend_counts["failed"] + frontend_counts["failed"],
        }
        
        report = []
        report.append("=" * 80)
        report.append("NETRA AI PLATFORM - TEST REPORT")
        report.append("=" * 80)
        report.append(f"Timestamp: {timestamp}")
        report.append(f"Test Level: {level}")
        report.append(f"Status: {'PASSED' if exit_code == 0 else 'FAILED'}")
        report.append(f"Duration: {duration:.2f}s")
        
        if getattr(self, "staging_mode", False):
            report.append("\nSTAGING ENVIRONMENT:")
            report.append(f"  Frontend: {os.getenv('STAGING_URL', 'N/A')}")
            report.append(f"  API: {os.getenv('STAGING_API_URL', 'N/A')}")
            report.append(f"  PR Number: {os.getenv('PR_NUMBER', 'N/A')}")
        
        report.append("\nTEST SUMMARY:")
        report.append(f"  Total: {total_counts['total']}")
        report.append(f"  Passed: {total_counts['passed']}")
        report.append(f"  Failed: {total_counts['failed']}")
        
        report.append("\nCOMPONENT RESULTS:")
        report.append(f"  Backend: {self.results['backend']['status'].upper()}")
        report.append(f"    Tests: {backend_counts['total']} total, {backend_counts['passed']} passed, {backend_counts['failed']} failed")
        if self.results["backend"]["coverage"]:
            report.append(f"    Coverage: {self.results['backend']['coverage']:.1f}%")
        
        report.append(f"  Frontend: {self.results['frontend']['status'].upper()}")
        report.append(f"    Tests: {frontend_counts['total']} total, {frontend_counts['passed']} passed, {frontend_counts['failed']} failed")
        if self.results["frontend"]["coverage"]:
            report.append(f"    Coverage: {self.results['frontend']['coverage']:.1f}%")
        
        report.append("=" * 80)
        
        return "\n".join(report)
    
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
    
    # Staging environment support
    parser.add_argument(
        "--staging",
        action="store_true",
        help="Run tests against staging environment (uses STAGING_URL and STAGING_API_URL env vars)"
    )
    parser.add_argument(
        "--staging-url",
        type=str,
        help="Override staging frontend URL"
    )
    parser.add_argument(
        "--staging-api-url",
        type=str,
        help="Override staging API URL"
    )
    parser.add_argument(
        "--report-format",
        type=str,
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Format for test report output (default: markdown)"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for test results (for CI/CD integration)"
    )
    
    # Failing test management options
    parser.add_argument(
        "--show-failing",
        action="store_true",
        help="Display currently failing tests from the log"
    )
    parser.add_argument(
        "--run-failing",
        action="store_true",
        help="Run only the currently failing tests"
    )
    parser.add_argument(
        "--fix-failing",
        action="store_true",
        help="Attempt to automatically fix failing tests (experimental)"
    )
    parser.add_argument(
        "--max-fixes",
        type=int,
        default=None,
        help="Maximum number of tests to attempt fixing (default: all)"
    )
    parser.add_argument(
        "--clear-failing",
        action="store_true",
        help="Clear the failing tests log"
    )
    
    args = parser.parse_args()
    
    # Print header
    print("=" * 80)
    print("NETRA AI PLATFORM - UNIFIED TEST RUNNER")
    print("=" * 80)
    
    # Configure staging environment if requested
    if args.staging or args.staging_url or args.staging_api_url:
        staging_url = args.staging_url or os.getenv("STAGING_URL")
        staging_api_url = args.staging_api_url or os.getenv("STAGING_API_URL")
        
        if not staging_url or not staging_api_url:
            print("[ERROR] Staging mode requires STAGING_URL and STAGING_API_URL")
            print("  Set via environment variables or --staging-url and --staging-api-url flags")
            sys.exit(1)
        
        print(f"[STAGING MODE] Testing against staging environment:")
        print(f"  Frontend: {staging_url}")
        print(f"  API: {staging_api_url}")
        
        # Set environment variables for tests to use
        os.environ["STAGING_MODE"] = "true"
        os.environ["STAGING_URL"] = staging_url
        os.environ["STAGING_API_URL"] = staging_api_url
        os.environ["BASE_URL"] = staging_url
        os.environ["API_BASE_URL"] = staging_api_url
        os.environ["CYPRESS_BASE_URL"] = staging_url
        os.environ["CYPRESS_API_URL"] = staging_api_url
    
    # Initialize test runner
    runner = UnifiedTestRunner()
    runner.results["overall"]["start_time"] = time.time()
    
    # Add staging flag to runner if needed
    if args.staging:
        runner.staging_mode = True
    
    # Handle failing test management commands
    if args.show_failing:
        # Display current failing tests
        failing_tests = runner.load_failing_tests()
        print("\n" + "=" * 80)
        print("CURRENTLY FAILING TESTS")
        print("=" * 80)
        print(f"Last Updated: {failing_tests.get('last_updated', 'N/A')}\n")
        
        for component in ["backend", "frontend", "e2e"]:
            if component in failing_tests and failing_tests[component]["count"] > 0:
                print(f"\n{component.upper()} ({failing_tests[component]['count']} failures):")
                print("-" * 40)
                for i, failure in enumerate(failing_tests[component]["failures"], 1):
                    print(f"{i}. {failure['test_path']}::{failure['test_name']}")
                    print(f"   Error: {failure['error_type']} - {failure['error_message'][:100]}...")
                    print(f"   Consecutive Failures: {failure.get('consecutive_failures', 1)}")
        
        if all(failing_tests.get(c, {}).get("count", 0) == 0 for c in ["backend", "frontend", "e2e"]):
            print("No failing tests found!")
        
        print("\n" + "=" * 80)
        sys.exit(0)
    
    elif args.clear_failing:
        # Clear the failing tests log
        failing_tests_path = runner.reports_dir / "failing_tests.json"
        if failing_tests_path.exists():
            failing_tests_path.unlink()
            print("[INFO] Failing tests log cleared")
        else:
            print("[INFO] No failing tests log to clear")
        sys.exit(0)
    
    elif args.run_failing:
        # Run only the currently failing tests
        print("\n" + "=" * 80)
        print("RUNNING FAILING TESTS")
        print("=" * 80)
        
        exit_code = runner.run_failing_tests(
            max_fixes=args.max_fixes,
            backend_only=args.backend_only if hasattr(args, 'backend_only') else False,
            frontend_only=args.frontend_only if hasattr(args, 'frontend_only') else False
        )
        
        print("\n" + "=" * 80)
        sys.exit(exit_code)
    
    elif args.fix_failing:
        # This would be where automatic fixing logic would go
        # For now, just inform that it's not yet implemented
        print("\n[INFO] Automatic test fixing is not yet implemented")
        print("Use --run-failing to run only failing tests")
        sys.exit(0)
    
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
        
        # Save in additional formats if requested
        if args.output:
            if args.report_format == "json":
                # Generate JSON report for CI/CD
                json_report = runner.generate_json_report(level, config, exit_code)
                with open(args.output, "w", encoding='utf-8') as f:
                    json.dump(json_report, f, indent=2)
                print(f"[REPORT] JSON report saved to: {args.output}")
            elif args.report_format == "text":
                # Generate text report
                text_report = runner.generate_text_report(level, config, exit_code)
                with open(args.output, "w", encoding='utf-8') as f:
                    f.write(text_report)
                print(f"[REPORT] Text report saved to: {args.output}")
    
    # Print summary
    runner.print_summary()
    
    # Exit with appropriate code
    sys.exit(exit_code)

if __name__ == "__main__":
    main()