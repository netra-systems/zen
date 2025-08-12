#!/usr/bin/env python
"""
ENHANCED TEST RUNNER V2 - Comprehensive Test Management System
Improvements:
- Better parallel execution with dynamic worker allocation
- Improved test categorization and organization
- Enhanced error handling and recovery
- Detailed failure analysis and reporting
- Batch processing with automatic retries
- Better timeout management
"""

import os
import sys
import json
import time
import asyncio
import re
import subprocess
import multiprocessing
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
import traceback
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_reports/test_runner.log', mode='a'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# CPU and worker configuration
CPU_COUNT = multiprocessing.cpu_count()
OPTIMAL_WORKERS = min(CPU_COUNT - 1, 8)
MAX_RETRIES = 2
DEFAULT_TIMEOUT = 30

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"
    FLAKY = "flaky"

class TestPriority(Enum):
    """Test priority levels"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class TestCase:
    """Represents a single test case"""
    id: str
    file_path: str
    class_name: Optional[str]
    method_name: str
    category: str
    priority: TestPriority = TestPriority.MEDIUM
    status: TestStatus = TestStatus.PENDING
    duration: float = 0.0
    error_message: str = ""
    traceback: str = ""
    retries: int = 0
    flaky: bool = False
    dependencies: List[str] = field(default_factory=list)
    
    @property
    def full_path(self) -> str:
        """Get full test path for pytest"""
        if self.class_name:
            return f"{self.file_path}::{self.class_name}::{self.method_name}"
        return f"{self.file_path}::{self.method_name}"

@dataclass
class TestBatch:
    """Group of tests to run together"""
    id: int
    tests: List[TestCase]
    category: str
    priority: TestPriority
    parallel: bool = True
    timeout: int = DEFAULT_TIMEOUT
    
class TestCategorizer:
    """Categorize and prioritize tests"""
    
    CATEGORY_PATTERNS = {
        "auth": ["auth", "security", "permission", "access"],
        "database": ["database", "db", "repository", "migration", "clickhouse", "postgres"],
        "api": ["route", "endpoint", "api", "rest", "graphql"],
        "websocket": ["websocket", "ws", "realtime", "socket"],
        "agent": ["agent", "llm", "ai", "supervisor", "subagent"],
        "service": ["service", "business", "logic"],
        "integration": ["integration", "e2e", "system"],
        "unit": ["unit", "mock", "stub"],
        "performance": ["performance", "benchmark", "load", "stress"],
        "config": ["config", "settings", "environment"]
    }
    
    PRIORITY_MAP = {
        "auth": TestPriority.CRITICAL,
        "database": TestPriority.CRITICAL,
        "api": TestPriority.HIGH,
        "websocket": TestPriority.HIGH,
        "agent": TestPriority.HIGH,
        "service": TestPriority.MEDIUM,
        "integration": TestPriority.MEDIUM,
        "unit": TestPriority.LOW,
        "performance": TestPriority.LOW,
        "config": TestPriority.MEDIUM
    }
    
    @classmethod
    def categorize(cls, test_path: str, test_name: str = "") -> Tuple[str, TestPriority]:
        """Categorize test and assign priority"""
        combined = f"{test_path} {test_name}".lower()
        
        for category, patterns in cls.CATEGORY_PATTERNS.items():
            if any(pattern in combined for pattern in patterns):
                return category, cls.PRIORITY_MAP.get(category, TestPriority.MEDIUM)
        
        return "other", TestPriority.MEDIUM

class TestCollector:
    """Collect and discover tests"""
    
    def __init__(self, root_dir: Path = PROJECT_ROOT):
        self.root_dir = root_dir
        self.tests: List[TestCase] = []
        
    def collect_tests(self, paths: Optional[List[str]] = None) -> List[TestCase]:
        """Collect all tests from specified paths"""
        if paths is None:
            paths = ["app/tests", "frontend/__tests__", "e2e/cypress"]
        
        for path in paths:
            full_path = self.root_dir / path
            if full_path.exists():
                if full_path.is_file():
                    self._collect_from_file(full_path)
                else:
                    self._collect_from_directory(full_path)
        
        return self.tests
    
    def _collect_from_directory(self, directory: Path):
        """Recursively collect tests from directory"""
        for test_file in directory.rglob("test_*.py"):
            self._collect_from_file(test_file)
    
    def _collect_from_file(self, file_path: Path):
        """Collect tests from a single file"""
        try:
            # Use pytest collection
            result = subprocess.run(
                [sys.executable, "-m", "pytest", "--collect-only", "-q", str(file_path)],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=self.root_dir
            )
            
            if result.returncode == 0:
                self._parse_pytest_collection(result.stdout, file_path)
        except Exception as e:
            logger.warning(f"Failed to collect from {file_path}: {e}")
    
    def _parse_pytest_collection(self, output: str, file_path: Path):
        """Parse pytest collection output"""
        # Pattern: <Module test_file.py>::<Class TestClass>::<Function test_method>
        pattern = r"<Module [^>]+>::(?:<Class ([^>]+)>::)?<Function ([^>]+)>"
        
        for match in re.finditer(pattern, output):
            class_name = match.group(1)
            method_name = match.group(2)
            
            category, priority = TestCategorizer.categorize(str(file_path), method_name)
            
            test_case = TestCase(
                id=f"{file_path.stem}::{method_name}",
                file_path=str(file_path.relative_to(self.root_dir)),
                class_name=class_name,
                method_name=method_name,
                category=category,
                priority=priority
            )
            
            self.tests.append(test_case)

class TestExecutor:
    """Execute tests with improved parallelization and error handling"""
    
    def __init__(self, max_workers: int = OPTIMAL_WORKERS):
        self.max_workers = max_workers
        self.results: Dict[str, TestCase] = {}
        
    async def execute_batch(self, batch: TestBatch) -> List[TestCase]:
        """Execute a batch of tests"""
        if batch.parallel and len(batch.tests) > 1:
            return await self._execute_parallel(batch)
        else:
            return await self._execute_sequential(batch)
    
    async def _execute_parallel(self, batch: TestBatch) -> List[TestCase]:
        """Execute tests in parallel"""
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch.tests))) as executor:
            futures = []
            for test in batch.tests:
                future = loop.run_in_executor(
                    executor,
                    self._run_single_test,
                    test,
                    batch.timeout
                )
                futures.append((test, future))
            
            results = []
            for test, future in futures:
                try:
                    result = await asyncio.wait_for(future, timeout=batch.timeout + 5)
                    results.append(result)
                except asyncio.TimeoutError:
                    test.status = TestStatus.TIMEOUT
                    test.error_message = f"Test timed out after {batch.timeout}s"
                    results.append(test)
                except Exception as e:
                    test.status = TestStatus.ERROR
                    test.error_message = str(e)
                    test.traceback = traceback.format_exc()
                    results.append(test)
            
            return results
    
    async def _execute_sequential(self, batch: TestBatch) -> List[TestCase]:
        """Execute tests sequentially"""
        results = []
        for test in batch.tests:
            result = self._run_single_test(test, batch.timeout)
            results.append(result)
        return results
    
    def _run_single_test(self, test: TestCase, timeout: int) -> TestCase:
        """Run a single test case"""
        start_time = time.time()
        test.status = TestStatus.RUNNING
        
        cmd = [
            sys.executable, "-m", "pytest",
            test.full_path,
            "-xvs",
            "--tb=short",
            "--no-header",
            "--no-summary"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=PROJECT_ROOT,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            )
            
            test.duration = time.time() - start_time
            
            if result.returncode == 0:
                test.status = TestStatus.PASSED
            else:
                test.status = TestStatus.FAILED
                self._extract_error_info(test, result.stdout + result.stderr)
            
            return test
            
        except subprocess.TimeoutExpired:
            test.duration = time.time() - start_time
            test.status = TestStatus.TIMEOUT
            test.error_message = f"Timeout after {timeout}s"
            return test
        except Exception as e:
            test.duration = time.time() - start_time
            test.status = TestStatus.ERROR
            test.error_message = str(e)
            test.traceback = traceback.format_exc()
            return test
    
    def _extract_error_info(self, test: TestCase, output: str):
        """Extract error information from test output"""
        # Look for assertion errors
        if "AssertionError" in output:
            match = re.search(r"AssertionError: (.+?)(?:\n|$)", output)
            if match:
                test.error_message = match.group(1)
        
        # Look for other exceptions
        exception_pattern = r"(\w+Error): (.+?)(?:\n|$)"
        match = re.search(exception_pattern, output)
        if match:
            test.error_message = f"{match.group(1)}: {match.group(2)}"
        
        # Extract traceback (last few lines)
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if 'Traceback' in line:
                test.traceback = '\n'.join(lines[i:min(i+10, len(lines))])
                break

class TestBatchProcessor:
    """Process tests in batches with smart grouping"""
    
    def __init__(self, executor: TestExecutor):
        self.executor = executor
        self.batches: List[TestBatch] = []
        
    def create_batches(self, tests: List[TestCase], batch_size: int = 50) -> List[TestBatch]:
        """Create optimized test batches"""
        # Group by category and priority
        grouped = defaultdict(list)
        for test in tests:
            key = (test.category, test.priority)
            grouped[key].append(test)
        
        # Create batches
        batch_id = 0
        for (category, priority), group_tests in sorted(grouped.items(), key=lambda x: x[0][1].value):
            # Split large groups into smaller batches
            for i in range(0, len(group_tests), batch_size):
                batch = TestBatch(
                    id=batch_id,
                    tests=group_tests[i:i+batch_size],
                    category=category,
                    priority=priority,
                    parallel=self._should_parallelize(category),
                    timeout=self._get_timeout(category)
                )
                self.batches.append(batch)
                batch_id += 1
        
        return self.batches
    
    def _should_parallelize(self, category: str) -> bool:
        """Determine if category should run in parallel"""
        # Database and integration tests should run sequentially
        sequential_categories = ["database", "integration", "e2e"]
        return category not in sequential_categories
    
    def _get_timeout(self, category: str) -> int:
        """Get appropriate timeout for category"""
        timeout_map = {
            "integration": 60,
            "e2e": 120,
            "performance": 90,
            "agent": 45,
            "database": 45
        }
        return timeout_map.get(category, DEFAULT_TIMEOUT)
    
    async def process_all(self, tests: List[TestCase]) -> Dict[str, Any]:
        """Process all tests in batches"""
        batches = self.create_batches(tests)
        total_tests = len(tests)
        completed = 0
        failed = 0
        passed = 0
        
        results = {
            "batches": [],
            "summary": {},
            "failed_tests": [],
            "flaky_tests": []
        }
        
        for batch in batches:
            logger.info(f"Processing batch {batch.id + 1}/{len(batches)} - {batch.category} ({len(batch.tests)} tests)")
            
            batch_results = await self.executor.execute_batch(batch)
            
            batch_summary = {
                "id": batch.id,
                "category": batch.category,
                "priority": batch.priority.name,
                "total": len(batch_results),
                "passed": sum(1 for t in batch_results if t.status == TestStatus.PASSED),
                "failed": sum(1 for t in batch_results if t.status == TestStatus.FAILED),
                "errors": sum(1 for t in batch_results if t.status == TestStatus.ERROR),
                "timeouts": sum(1 for t in batch_results if t.status == TestStatus.TIMEOUT),
                "duration": sum(t.duration for t in batch_results)
            }
            
            results["batches"].append(batch_summary)
            
            # Track failed tests
            for test in batch_results:
                if test.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]:
                    results["failed_tests"].append({
                        "path": test.full_path,
                        "status": test.status.value,
                        "error": test.error_message,
                        "duration": test.duration,
                        "category": test.category,
                        "priority": test.priority.name
                    })
                    failed += 1
                elif test.status == TestStatus.PASSED:
                    passed += 1
            
            completed += len(batch_results)
            
            # Print progress
            progress = (completed / total_tests) * 100
            logger.info(f"Progress: {completed}/{total_tests} ({progress:.1f}%) - Passed: {passed}, Failed: {failed}")
        
        # Generate summary
        results["summary"] = {
            "total_tests": total_tests,
            "completed": completed,
            "passed": passed,
            "failed": failed,
            "success_rate": (passed / completed * 100) if completed > 0 else 0,
            "total_duration": sum(b["duration"] for b in results["batches"])
        }
        
        return results

class TestReportGenerator:
    """Generate comprehensive test reports"""
    
    def __init__(self, reports_dir: Path = PROJECT_ROOT / "test_reports"):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(exist_ok=True)
        
    def generate_report(self, results: Dict[str, Any], filename: str = None) -> Path:
        """Generate detailed test report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if filename is None:
            filename = f"test_report_{timestamp}.json"
        
        report_path = self.reports_dir / filename
        
        # Add metadata
        results["metadata"] = {
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "cpu_count": CPU_COUNT,
            "workers_used": OPTIMAL_WORKERS
        }
        
        # Save JSON report
        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        # Generate markdown summary
        self._generate_markdown_summary(results, timestamp)
        
        return report_path
    
    def _generate_markdown_summary(self, results: Dict[str, Any], timestamp: str):
        """Generate markdown summary report"""
        md_path = self.reports_dir / f"summary_{timestamp}.md"
        
        summary = results["summary"]
        
        content = f"""# Test Execution Report

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

- **Total Tests**: {summary['total_tests']}
- **Passed**: {summary['passed']} ({summary['passed'] / summary['total_tests'] * 100:.1f}%)
- **Failed**: {summary['failed']} ({summary['failed'] / summary['total_tests'] * 100:.1f}%)
- **Success Rate**: {summary['success_rate']:.1f}%
- **Total Duration**: {summary['total_duration']:.2f}s

## Batch Results

| Batch | Category | Priority | Total | Passed | Failed | Duration |
|-------|----------|----------|-------|--------|--------|----------|
"""
        
        for batch in results["batches"]:
            content += f"| {batch['id']} | {batch['category']} | {batch['priority']} | "
            content += f"{batch['total']} | {batch['passed']} | {batch['failed']} | "
            content += f"{batch['duration']:.2f}s |\n"
        
        if results["failed_tests"]:
            content += "\n## Failed Tests\n\n"
            
            # Group by category
            by_category = defaultdict(list)
            for test in results["failed_tests"]:
                by_category[test["category"]].append(test)
            
            for category, tests in sorted(by_category.items()):
                content += f"\n### {category.title()}\n\n"
                for test in tests[:10]:  # Limit to first 10 per category
                    content += f"- **{test['path']}**\n"
                    content += f"  - Status: {test['status']}\n"
                    content += f"  - Error: {test['error'][:200]}...\n" if len(test['error']) > 200 else f"  - Error: {test['error']}\n"
                    content += f"  - Duration: {test['duration']:.2f}s\n\n"
                
                if len(tests) > 10:
                    content += f"  ... and {len(tests) - 10} more\n\n"
        
        with open(md_path, 'w') as f:
            f.write(content)
        
        logger.info(f"Markdown summary saved to {md_path}")

async def main():
    """Main execution function"""
    logger.info("Starting Enhanced Test Runner V2")
    
    # Create test reports directory
    reports_dir = PROJECT_ROOT / "test_reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Collect tests
    logger.info("Collecting tests...")
    collector = TestCollector()
    tests = collector.collect_tests()
    logger.info(f"Collected {len(tests)} tests")
    
    if not tests:
        logger.error("No tests found!")
        return 1
    
    # Group tests by category
    by_category = defaultdict(int)
    for test in tests:
        by_category[test.category] += 1
    
    logger.info("Test distribution by category:")
    for category, count in sorted(by_category.items()):
        logger.info(f"  {category}: {count}")
    
    # Execute tests
    executor = TestExecutor(max_workers=OPTIMAL_WORKERS)
    processor = TestBatchProcessor(executor)
    
    logger.info(f"Starting test execution with {OPTIMAL_WORKERS} workers...")
    results = await processor.process_all(tests)
    
    # Generate report
    reporter = TestReportGenerator()
    report_path = reporter.generate_report(results)
    logger.info(f"Report saved to {report_path}")
    
    # Print summary
    summary = results["summary"]
    logger.info("="*60)
    logger.info("EXECUTION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total: {summary['total_tests']}")
    logger.info(f"Passed: {summary['passed']}")
    logger.info(f"Failed: {summary['failed']}")
    logger.info(f"Success Rate: {summary['success_rate']:.1f}%")
    logger.info(f"Duration: {summary['total_duration']:.2f}s")
    
    return 0 if summary['failed'] == 0 else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)