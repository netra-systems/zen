#!/usr/bin/env python
"""
ENHANCED TEST RUNNER - Improved version with better parallelization and organization
Features:
- Smart parallel execution with process pooling
- Dynamic timeout adjustments
- Better test categorization and grouping
- Detailed failure tracking with auto-fix suggestions
- Progressive test execution (fail-fast for critical paths)
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
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_reports/test_runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables
load_dotenv()

class TestPriority(Enum):
    """Test priority levels for smart execution"""
    CRITICAL = 1  # Must pass - blocks deployment
    HIGH = 2      # Should pass - core functionality
    MEDIUM = 3    # Important - feature functionality  
    LOW = 4       # Nice to have - edge cases

class TestCategory(Enum):
    """Test categories for better organization"""
    SMOKE = "smoke"
    UNIT = "unit"
    INTEGRATION = "integration"
    E2E = "e2e"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DATABASE = "database"
    API = "api"
    UI = "ui"
    AGENT = "agent"
    WEBSOCKET = "websocket"
    LLM = "llm"

@dataclass
class TestGroup:
    """Group of related tests to run together"""
    name: str
    category: TestCategory
    priority: TestPriority
    tests: List[str]
    timeout: int = 60
    parallel: bool = True
    max_workers: int = 4
    dependencies: List[str] = field(default_factory=list)
    
@dataclass
class TestResult:
    """Result of a test execution"""
    test_path: str
    status: str  # passed, failed, skipped, error, timeout
    duration: float
    output: str
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    fix_suggestion: Optional[str] = None
    
class EnhancedTestRunner:
    """Enhanced test runner with improved parallelization and organization"""
    
    def __init__(self):
        self.reports_dir = PROJECT_ROOT / "test_reports"
        self.reports_dir.mkdir(exist_ok=True)
        self.history_dir = self.reports_dir / "history"
        self.history_dir.mkdir(exist_ok=True)
        
        # Track test results
        self.results: Dict[str, List[TestResult]] = {
            "backend": [],
            "frontend": [],
            "e2e": []
        }
        
        # Track failing tests
        self.failing_tests_file = self.reports_dir / "failing_tests.json"
        self.failing_tests = self.load_failing_tests()
        
        # Test groups for organized execution
        self.test_groups = self._initialize_test_groups()
        
        # Performance metrics
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "timeouts": 0
        }
        
    def _initialize_test_groups(self) -> Dict[str, TestGroup]:
        """Initialize test groups with smart categorization"""
        groups = {}
        
        # Backend test groups
        groups["backend_critical"] = TestGroup(
            name="Backend Critical Path",
            category=TestCategory.SMOKE,
            priority=TestPriority.CRITICAL,
            tests=[
                "app/tests/test_internal_imports.py",
                "app/tests/test_external_imports.py",
                "app/tests/core/test_config.py",
                "app/tests/services/test_database_service.py"
            ],
            timeout=30,
            parallel=False  # Run critical tests sequentially
        )
        
        groups["backend_database"] = TestGroup(
            name="Backend Database",
            category=TestCategory.DATABASE,
            priority=TestPriority.HIGH,
            tests=[
                "app/tests/services/test_database_repositories.py",
                "app/tests/clickhouse/test_*.py",
                "app/tests/postgres/test_*.py"
            ],
            timeout=120,
            parallel=True,
            max_workers=4
        )
        
        groups["backend_agents"] = TestGroup(
            name="Backend Agents",
            category=TestCategory.AGENT,
            priority=TestPriority.HIGH,
            tests=[
                "app/tests/agents/test_*.py",
                "app/tests/services/test_agent_*.py"
            ],
            timeout=180,
            parallel=True,
            max_workers=6
        )
        
        groups["backend_llm"] = TestGroup(
            name="Backend LLM",
            category=TestCategory.LLM,
            priority=TestPriority.MEDIUM,
            tests=[
                "app/tests/llm/test_*.py",
                "app/tests/services/test_llm_*.py"
            ],
            timeout=300,
            parallel=True,
            max_workers=2  # LLM tests are resource intensive
        )
        
        groups["backend_websocket"] = TestGroup(
            name="Backend WebSocket",
            category=TestCategory.WEBSOCKET,
            priority=TestPriority.HIGH,
            tests=[
                "app/tests/services/test_websocket_*.py",
                "app/tests/test_ws_manager.py"
            ],
            timeout=120,
            parallel=True,
            max_workers=4
        )
        
        groups["backend_api"] = TestGroup(
            name="Backend API",
            category=TestCategory.API,
            priority=TestPriority.HIGH,
            tests=[
                "app/tests/routes/test_*.py",
                "app/tests/test_api_*.py"
            ],
            timeout=180,
            parallel=True,
            max_workers=8
        )
        
        # Frontend test groups
        groups["frontend_critical"] = TestGroup(
            name="Frontend Critical",
            category=TestCategory.SMOKE,
            priority=TestPriority.CRITICAL,
            tests=[
                "__tests__/setup.test.ts",
                "__tests__/components/App.test.tsx"
            ],
            timeout=30,
            parallel=False
        )
        
        groups["frontend_ui"] = TestGroup(
            name="Frontend UI",
            category=TestCategory.UI,
            priority=TestPriority.HIGH,
            tests=[
                "__tests__/components/*.test.tsx",
                "__tests__/hooks/*.test.tsx"
            ],
            timeout=180,
            parallel=True,
            max_workers=6
        )
        
        groups["frontend_integration"] = TestGroup(
            name="Frontend Integration",
            category=TestCategory.INTEGRATION,
            priority=TestPriority.MEDIUM,
            tests=[
                "__tests__/integration/*.test.ts",
                "__tests__/store/*.test.ts"
            ],
            timeout=240,
            parallel=True,
            max_workers=4
        )
        
        return groups
        
    def load_failing_tests(self) -> Dict:
        """Load previously failing tests for tracking"""
        if self.failing_tests_file.exists():
            with open(self.failing_tests_file, 'r') as f:
                return json.load(f)
        return {"backend": {}, "frontend": {}, "e2e": {}}
        
    def save_failing_tests(self):
        """Save current failing tests to file"""
        with open(self.failing_tests_file, 'w') as f:
            json.dump(self.failing_tests, f, indent=2)
            
    def run_test_group(self, group: TestGroup, component: str = "backend") -> List[TestResult]:
        """Run a group of tests with smart parallelization"""
        logger.info(f"Running test group: {group.name} (Priority: {group.priority.name})")
        
        results = []
        
        if group.parallel and group.max_workers > 1:
            # Run tests in parallel
            with ProcessPoolExecutor(max_workers=group.max_workers) as executor:
                futures = {}
                for test_pattern in group.tests:
                    # Expand glob patterns
                    test_files = self._expand_test_pattern(test_pattern, component)
                    for test_file in test_files:
                        future = executor.submit(self._run_single_test, test_file, component, group.timeout)
                        futures[future] = test_file
                        
                # Process results as they complete
                for future in as_completed(futures, timeout=group.timeout * 2):
                    try:
                        result = future.result()
                        results.append(result)
                        self._update_metrics(result)
                        
                        # Fail fast for critical tests
                        if group.priority == TestPriority.CRITICAL and result.status == "failed":
                            logger.error(f"Critical test failed: {result.test_path}")
                            # Cancel remaining futures
                            for f in futures:
                                if not f.done():
                                    f.cancel()
                            break
                    except Exception as e:
                        logger.error(f"Error running test {futures[future]}: {e}")
                        results.append(TestResult(
                            test_path=futures[future],
                            status="error",
                            duration=0,
                            output="",
                            error_message=str(e)
                        ))
        else:
            # Run tests sequentially
            for test_pattern in group.tests:
                test_files = self._expand_test_pattern(test_pattern, component)
                for test_file in test_files:
                    result = self._run_single_test(test_file, component, group.timeout)
                    results.append(result)
                    self._update_metrics(result)
                    
                    # Fail fast for critical tests
                    if group.priority == TestPriority.CRITICAL and result.status == "failed":
                        logger.error(f"Critical test failed: {result.test_path}")
                        break
                        
        return results
        
    def _expand_test_pattern(self, pattern: str, component: str) -> List[str]:
        """Expand glob patterns to actual test files"""
        if "*" in pattern:
            # Handle glob patterns
            base_path = PROJECT_ROOT / ("frontend" if component == "frontend" else ".")
            return [str(p) for p in base_path.glob(pattern)]
        return [pattern]
        
    def _run_single_test(self, test_file: str, component: str, timeout: int) -> TestResult:
        """Run a single test file and return result"""
        start_time = time.time()
        
        if component == "backend":
            cmd = [sys.executable, "-m", "pytest", test_file, "-xvs", "--tb=short"]
        else:
            # Frontend tests
            cmd = ["npm", "test", "--", test_file, "--silent"]
            
        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT if component == "backend" else PROJECT_ROOT / "frontend",
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            
            duration = time.time() - start_time
            
            # Parse test output to determine status
            status = "passed" if result.returncode == 0 else "failed"
            error_message = None
            stack_trace = None
            fix_suggestion = None
            
            if status == "failed":
                # Extract error details
                error_message, stack_trace = self._parse_error_output(result.stdout + result.stderr)
                # Generate fix suggestion
                fix_suggestion = self._generate_fix_suggestion(test_file, error_message)
                
            return TestResult(
                test_path=test_file,
                status=status,
                duration=duration,
                output=result.stdout + result.stderr,
                error_message=error_message,
                stack_trace=stack_trace,
                fix_suggestion=fix_suggestion
            )
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                test_path=test_file,
                status="timeout",
                duration=duration,
                output=f"Test timed out after {timeout}s",
                error_message=f"Timeout after {timeout}s"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_path=test_file,
                status="error",
                duration=duration,
                output=str(e),
                error_message=str(e)
            )
            
    def _parse_error_output(self, output: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse test output to extract error message and stack trace"""
        lines = output.split('\n')
        error_message = None
        stack_trace = []
        in_stack_trace = False
        
        for line in lines:
            if 'AssertionError' in line or 'TypeError' in line or 'AttributeError' in line or 'ValidationError' in line:
                error_message = line.strip()
                in_stack_trace = True
            elif in_stack_trace and line.strip():
                stack_trace.append(line)
            elif in_stack_trace and not line.strip():
                break
                
        return error_message, '\n'.join(stack_trace) if stack_trace else None
        
    def _generate_fix_suggestion(self, test_file: str, error_message: str) -> Optional[str]:
        """Generate intelligent fix suggestions based on error patterns"""
        if not error_message:
            return None
            
        suggestions = []
        
        # Common error patterns and their fixes
        if "AttributeError" in error_message and "NoneType" in error_message:
            suggestions.append("Check if object is properly initialized before accessing attributes")
            suggestions.append("Add null checks or use optional chaining")
            
        elif "TypeError" in error_message and "unexpected keyword argument" in error_message:
            # Extract the unexpected argument
            match = re.search(r"unexpected keyword argument '(\w+)'", error_message)
            if match:
                arg = match.group(1)
                suggestions.append(f"Remove or update the '{arg}' parameter in the function call")
                suggestions.append("Check if the function signature has changed")
                
        elif "TypeError" in error_message and "takes \d+ positional argument" in error_message:
            suggestions.append("Check the number of arguments being passed to the function")
            suggestions.append("Verify the function signature matches the test expectations")
            
        elif "ValidationError" in error_message:
            suggestions.append("Check required fields in the model/schema")
            suggestions.append("Ensure all required data is provided in the test")
            
        elif "ImportError" in error_message or "ModuleNotFoundError" in error_message:
            suggestions.append("Check if the module exists and is properly installed")
            suggestions.append("Verify import paths are correct")
            
        return " | ".join(suggestions) if suggestions else None
        
    def _update_metrics(self, result: TestResult):
        """Update test metrics based on result"""
        self.metrics["total_tests"] += 1
        
        if result.status == "passed":
            self.metrics["passed"] += 1
        elif result.status == "failed":
            self.metrics["failed"] += 1
        elif result.status == "skipped":
            self.metrics["skipped"] += 1
        elif result.status == "error":
            self.metrics["errors"] += 1
        elif result.status == "timeout":
            self.metrics["timeouts"] += 1
            
    def run_all_tests(self, level: str = "comprehensive", fix_mode: bool = False) -> int:
        """Run all tests based on level with smart execution"""
        self.metrics["start_time"] = time.time()
        
        logger.info(f"Starting test run at level: {level}")
        logger.info(f"Fix mode: {'Enabled' if fix_mode else 'Disabled'}")
        
        # Determine which groups to run based on level
        groups_to_run = self._get_groups_for_level(level)
        
        # Sort groups by priority
        groups_to_run.sort(key=lambda g: (g[1].priority.value, g[0]))
        
        overall_status = 0
        
        for component, group in groups_to_run:
            results = self.run_test_group(group, component)
            self.results[component].extend(results)
            
            # Check for failures in critical groups
            if group.priority == TestPriority.CRITICAL:
                failures = [r for r in results if r.status == "failed"]
                if failures:
                    logger.error(f"Critical failures detected in {group.name}")
                    overall_status = 1
                    
                    if fix_mode:
                        # Attempt to fix critical failures
                        for failure in failures:
                            self._attempt_fix(failure, component)
                    else:
                        # Stop execution on critical failures
                        break
                        
        self.metrics["end_time"] = time.time()
        
        # Generate reports
        self.generate_report()
        
        return overall_status
        
    def _get_groups_for_level(self, level: str) -> List[Tuple[str, TestGroup]]:
        """Get test groups to run based on level"""
        groups = []
        
        if level == "smoke":
            # Only critical tests
            for name, group in self.test_groups.items():
                if group.priority == TestPriority.CRITICAL:
                    component = "frontend" if "frontend" in name else "backend"
                    groups.append((component, group))
                    
        elif level == "unit":
            # Critical and high priority unit tests
            for name, group in self.test_groups.items():
                if group.category in [TestCategory.UNIT, TestCategory.SMOKE]:
                    component = "frontend" if "frontend" in name else "backend"
                    groups.append((component, group))
                    
        elif level == "integration":
            # All except performance and security
            for name, group in self.test_groups.items():
                if group.category not in [TestCategory.PERFORMANCE, TestCategory.SECURITY]:
                    component = "frontend" if "frontend" in name else "backend"
                    groups.append((component, group))
                    
        elif level == "comprehensive":
            # All test groups
            for name, group in self.test_groups.items():
                component = "frontend" if "frontend" in name else "backend"
                groups.append((component, group))
                
        return groups
        
    def _attempt_fix(self, failure: TestResult, component: str):
        """Attempt to automatically fix a failing test"""
        logger.info(f"Attempting to fix: {failure.test_path}")
        
        if failure.fix_suggestion:
            logger.info(f"Suggested fix: {failure.fix_suggestion}")
            
        # TODO: Implement auto-fix logic based on error patterns
        # This would involve:
        # 1. Reading the test file
        # 2. Reading the source file being tested
        # 3. Applying fixes based on error patterns
        # 4. Re-running the test to verify fix
        
    def generate_report(self):
        """Generate comprehensive test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "metrics": self.metrics,
            "duration": self.metrics["end_time"] - self.metrics["start_time"] if self.metrics["end_time"] else 0,
            "results": {}
        }
        
        # Aggregate results by component
        for component, results in self.results.items():
            report["results"][component] = {
                "total": len(results),
                "passed": len([r for r in results if r.status == "passed"]),
                "failed": len([r for r in results if r.status == "failed"]),
                "errors": len([r for r in results if r.status == "error"]),
                "timeouts": len([r for r in results if r.status == "timeout"]),
                "failures": [
                    {
                        "test": r.test_path,
                        "error": r.error_message,
                        "duration": r.duration,
                        "suggestion": r.fix_suggestion
                    }
                    for r in results if r.status in ["failed", "error", "timeout"]
                ]
            }
            
        # Save report
        report_file = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        # Also save to latest
        latest_file = self.reports_dir / "latest_report.json"
        with open(latest_file, 'w') as f:
            json.dump(report, f, indent=2)
            
        # Generate markdown report
        self._generate_markdown_report(report)
        
        logger.info(f"Report saved to: {report_file}")
        
    def _generate_markdown_report(self, report: Dict):
        """Generate markdown formatted report"""
        md_lines = []
        
        md_lines.append("# Test Execution Report")
        md_lines.append(f"\n**Generated:** {report['timestamp']}")
        md_lines.append(f"**Duration:** {report['duration']:.2f}s")
        
        md_lines.append("\n## Summary")
        md_lines.append(f"- **Total Tests:** {report['metrics']['total_tests']}")
        md_lines.append(f"- **Passed:** {report['metrics']['passed']} ({report['metrics']['passed']/max(report['metrics']['total_tests'], 1)*100:.1f}%)")
        md_lines.append(f"- **Failed:** {report['metrics']['failed']}")
        md_lines.append(f"- **Errors:** {report['metrics']['errors']}")
        md_lines.append(f"- **Timeouts:** {report['metrics']['timeouts']}")
        
        for component, data in report['results'].items():
            if data['failures']:
                md_lines.append(f"\n## {component.title()} Failures")
                
                for failure in data['failures']:
                    md_lines.append(f"\n### {failure['test']}")
                    md_lines.append(f"- **Error:** {failure['error']}")
                    md_lines.append(f"- **Duration:** {failure['duration']:.2f}s")
                    if failure['suggestion']:
                        md_lines.append(f"- **Fix Suggestion:** {failure['suggestion']}")
                        
        # Save markdown report
        md_file = self.reports_dir / "latest_report.md"
        with open(md_file, 'w') as f:
            f.write('\n'.join(md_lines))
            

def main():
    """Main entry point for enhanced test runner"""
    parser = argparse.ArgumentParser(description='Enhanced Test Runner')
    parser.add_argument('--level', choices=['smoke', 'unit', 'integration', 'comprehensive'],
                       default='comprehensive', help='Test level to run')
    parser.add_argument('--fix-mode', action='store_true', help='Enable auto-fix mode')
    parser.add_argument('--parallel', type=int, help='Override parallel workers')
    parser.add_argument('--timeout', type=int, help='Override timeout settings')
    parser.add_argument('--component', choices=['backend', 'frontend', 'all'],
                       default='all', help='Component to test')
    
    args = parser.parse_args()
    
    runner = EnhancedTestRunner()
    
    # Override settings if provided
    if args.parallel:
        for group in runner.test_groups.values():
            group.max_workers = min(args.parallel, group.max_workers)
            
    if args.timeout:
        for group in runner.test_groups.values():
            group.timeout = args.timeout
            
    # Run tests
    exit_code = runner.run_all_tests(level=args.level, fix_mode=args.fix_mode)
    
    sys.exit(exit_code)
    

if __name__ == "__main__":
    main()