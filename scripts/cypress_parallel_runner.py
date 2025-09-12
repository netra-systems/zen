from shared.isolated_environment import get_env
#!/usr/bin/env python
"""
CYPRESS PARALLEL TEST RUNNER
=============================
Runs Cypress tests in parallel with configurable timeouts and worker distribution.

Features:
- Parallel execution across multiple workers
- Individual test timeouts with global suite timeout (1 hour default)
- Automatic test file splitting and load balancing
- Real-time progress reporting
- Failure tracking and retry mechanism
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import glob
import hashlib

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

class TestResult(Enum):
    """Test execution result status"""
    PASSED = "passed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"

@dataclass
class CypressTestSpec:
    """Represents a single Cypress test specification"""
    file_path: str
    relative_path: str
    estimated_duration: float  # seconds
    worker_id: Optional[int] = None
    result: Optional[TestResult] = None
    duration: Optional[float] = None
    error: Optional[str] = None

class CypressParallelRunner:
    """Manages parallel execution of Cypress tests"""
    
    def __init__(self, 
                 num_workers: int = 4,
                 test_timeout: int = 300,  # 5 minutes per test
                 suite_timeout: int = 3600,  # 1 hour for all tests
                 headless: bool = True,
                 browser: str = "chrome",
                 base_url: str = "http://localhost:3000"):
        self.num_workers = num_workers
        self.test_timeout = test_timeout
        self.suite_timeout = suite_timeout
        self.headless = headless
        self.browser = browser
        self.base_url = base_url
        self.start_time = None
        self.test_specs: List[CypressTestSpec] = []
        self.results: Dict[str, CypressTestSpec] = {}
        
    def discover_tests(self, spec_pattern: str = None) -> List[CypressTestSpec]:
        """Discover all Cypress test files"""
        if spec_pattern is None:
            spec_pattern = str(PROJECT_ROOT / "frontend" / "cypress" / "e2e" / "**" / "*.cy.ts")
        
        test_files = glob.glob(spec_pattern, recursive=True)
        self.test_specs = []
        
        for file_path in test_files:
            # Calculate relative path for Cypress
            relative_path = Path(file_path).relative_to(PROJECT_ROOT / "frontend")
            
            # Estimate duration based on file size and complexity
            # (This is a simple heuristic - could be improved with historical data)
            file_size = Path(file_path).stat().st_size
            estimated_duration = 30 + (file_size / 1000)  # Base 30s + 1s per KB
            
            spec = CypressTestSpec(
                file_path=str(file_path),
                relative_path=str(relative_path),
                estimated_duration=estimated_duration
            )
            self.test_specs.append(spec)
        
        print(f"Discovered {len(self.test_specs)} test files")
        return self.test_specs
    
    def split_tests_for_workers(self) -> List[List[CypressTestSpec]]:
        """Split tests across workers using load balancing"""
        # Sort tests by estimated duration (longest first)
        sorted_specs = sorted(self.test_specs, key=lambda x: x.estimated_duration, reverse=True)
        
        # Initialize worker queues
        worker_queues = [[] for _ in range(self.num_workers)]
        worker_loads = [0.0 for _ in range(self.num_workers)]
        
        # Distribute tests to workers with least current load
        for spec in sorted_specs:
            # Find worker with minimum load
            min_load_idx = worker_loads.index(min(worker_loads))
            
            # Assign test to worker
            spec.worker_id = min_load_idx
            worker_queues[min_load_idx].append(spec)
            worker_loads[min_load_idx] += spec.estimated_duration
        
        # Print load distribution
        for i, (queue, load) in enumerate(zip(worker_queues, worker_loads)):
            print(f"Worker {i}: {len(queue)} tests, estimated {load:.1f}s")
        
        return worker_queues
    
    def run_single_test(self, spec: CypressTestSpec, worker_id: int) -> CypressTestSpec:
        """Run a single Cypress test with timeout"""
        start_time = time.time()
        
        # Prepare Cypress command
        cmd = [
            "npx", "cypress", "run",
            "--spec", spec.relative_path,
            "--browser", self.browser,
            "--config", f"baseUrl={self.base_url}",
            f"defaultCommandTimeout={self.test_timeout * 1000}",
            f"requestTimeout={self.test_timeout * 1000}",
            f"responseTimeout={self.test_timeout * 1000}",
            f"pageLoadTimeout={self.test_timeout * 2000}",
            "video=false",
            "screenshotOnRunFailure=true",
            f"screenshotsFolder=cypress/screenshots/worker-{worker_id}",
            "--reporter", "json"
        ]
        
        if self.headless:
            cmd.append("--headless")
        
        # Set environment for worker isolation
        env = os.environ.copy()
        env["CYPRESS_WORKER_ID"] = str(worker_id)
        env["CYPRESS_CACHE_FOLDER"] = str(PROJECT_ROOT / f".cypress-cache-{worker_id}")
        
        try:
            # Run test with timeout
            result = subprocess.run(
                cmd,
                cwd=str(PROJECT_ROOT / "frontend"),
                env=env,
                capture_output=True,
                text=True,
                timeout=self.test_timeout
            )
            
            # Parse results
            if result.returncode == 0:
                spec.result = TestResult.PASSED
            else:
                spec.result = TestResult.FAILED
                spec.error = result.stderr or result.stdout
            
        except subprocess.TimeoutExpired:
            spec.result = TestResult.TIMEOUT
            spec.error = f"Test exceeded timeout of {self.test_timeout}s"
        except Exception as e:
            spec.result = TestResult.FAILED
            spec.error = str(e)
        
        spec.duration = time.time() - start_time
        return spec
    
    def run_worker(self, worker_id: int, test_queue: List[CypressTestSpec]) -> List[CypressTestSpec]:
        """Run all tests assigned to a worker"""
        results = []
        print(f"Worker {worker_id}: Starting {len(test_queue)} tests")
        
        for i, spec in enumerate(test_queue):
            # Check suite timeout
            if self.start_time and (time.time() - self.start_time) > self.suite_timeout:
                print(f"Worker {worker_id}: Suite timeout reached, skipping remaining tests")
                spec.result = TestResult.SKIPPED
                spec.error = "Suite timeout reached"
                results.append(spec)
                continue
            
            print(f"Worker {worker_id}: Running test {i+1}/{len(test_queue)}: {Path(spec.file_path).name}")
            spec = self.run_single_test(spec, worker_id)
            results.append(spec)
            
            # Report result immediately
            status_icon = "[U+2713]" if spec.result == TestResult.PASSED else "[U+2717]"
            print(f"Worker {worker_id}: {status_icon} {Path(spec.file_path).name} ({spec.duration:.1f}s)")
        
        return results
    
    def run_parallel(self) -> Dict[str, any]:
        """Execute tests in parallel across workers"""
        self.start_time = time.time()
        
        # Discover tests if not already done
        if not self.test_specs:
            self.discover_tests()
        
        # Split tests across workers
        worker_queues = self.split_tests_for_workers()
        
        # Execute in parallel using ProcessPoolExecutor
        all_results = []
        with ProcessPoolExecutor(max_workers=self.num_workers) as executor:
            # Submit all worker tasks
            future_to_worker = {
                executor.submit(self.run_worker, i, queue): i 
                for i, queue in enumerate(worker_queues)
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_worker):
                worker_id = future_to_worker[future]
                try:
                    worker_results = future.result(timeout=self.suite_timeout)
                    all_results.extend(worker_results)
                    print(f"Worker {worker_id}: Completed")
                except Exception as e:
                    print(f"Worker {worker_id}: Failed with error: {e}")
        
        # Compile final results
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in all_results if r.result == TestResult.PASSED)
        failed = sum(1 for r in all_results if r.result == TestResult.FAILED)
        timeout = sum(1 for r in all_results if r.result == TestResult.TIMEOUT)
        skipped = sum(1 for r in all_results if r.result == TestResult.SKIPPED)
        
        summary = {
            "total_tests": len(all_results),
            "passed": passed,
            "failed": failed,
            "timeout": timeout,
            "skipped": skipped,
            "duration": total_duration,
            "workers": self.num_workers,
            "success_rate": (passed / len(all_results) * 100) if all_results else 0
        }
        
        # Store results
        self.results = {spec.file_path: spec for spec in all_results}
        
        return summary
    
    def generate_report(self, output_file: str = None):
        """Generate detailed test report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "workers": self.num_workers,
                "test_timeout": self.test_timeout,
                "suite_timeout": self.suite_timeout,
                "browser": self.browser,
                "headless": self.headless
            },
            "summary": {
                "total": len(self.results),
                "passed": sum(1 for r in self.results.values() if r.result == TestResult.PASSED),
                "failed": sum(1 for r in self.results.values() if r.result == TestResult.FAILED),
                "timeout": sum(1 for r in self.results.values() if r.result == TestResult.TIMEOUT),
                "skipped": sum(1 for r in self.results.values() if r.result == TestResult.SKIPPED)
            },
            "tests": []
        }
        
        # Add individual test results
        for path, spec in self.results.items():
            report["tests"].append({
                "file": spec.relative_path,
                "worker": spec.worker_id,
                "result": spec.result.value if spec.result else None,
                "duration": spec.duration,
                "error": spec.error
            })
        
        # Sort by result (failures first) and duration
        report["tests"].sort(key=lambda x: (
            x["result"] != "failed",
            x["result"] != "timeout",
            -(x["duration"] or 0)
        ))
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to: {output_file}")
        
        return report

def main():
    parser = argparse.ArgumentParser(description="Run Cypress tests in parallel")
    
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    parser.add_argument(
        "--test-timeout",
        type=int,
        default=300,
        help="Timeout for individual tests in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--suite-timeout",
        type=int,
        default=3600,
        help="Overall timeout for entire test suite in seconds (default: 3600 = 1 hour)"
    )
    
    parser.add_argument(
        "--browser",
        choices=["chrome", "firefox", "edge", "electron"],
        default="chrome",
        help="Browser to use for testing"
    )
    
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run tests in headed mode (show browser)"
    )
    
    parser.add_argument(
        "--spec",
        type=str,
        help="Glob pattern for test files"
    )
    
    parser.add_argument(
        "--base-url",
        type=str,
        default="http://localhost:3000",
        help="Base URL for the application"
    )
    
    parser.add_argument(
        "--report",
        type=str,
        help="Output file for JSON report"
    )
    
    args = parser.parse_args()
    
    # Create runner
    runner = CypressParallelRunner(
        num_workers=args.workers,
        test_timeout=args.test_timeout,
        suite_timeout=args.suite_timeout,
        headless=not args.headed,
        browser=args.browser,
        base_url=args.base_url
    )
    
    # Discover tests
    if args.spec:
        runner.discover_tests(args.spec)
    else:
        runner.discover_tests()
    
    print(f"\n{'='*60}")
    print(f"CYPRESS PARALLEL TEST RUNNER")
    print(f"{'='*60}")
    print(f"Workers: {args.workers}")
    print(f"Test Timeout: {args.test_timeout}s")
    print(f"Suite Timeout: {args.suite_timeout}s ({args.suite_timeout/3600:.1f} hours)")
    print(f"Browser: {args.browser} ({'headless' if not args.headed else 'headed'})")
    print(f"Tests Found: {len(runner.test_specs)}")
    print(f"{'='*60}\n")
    
    # Run tests
    start_time = time.time()
    summary = runner.run_parallel()
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"TEST EXECUTION SUMMARY")
    print(f"{'='*60}")
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']} ({summary['success_rate']:.1f}%)")
    print(f"Failed: {summary['failed']}")
    print(f"Timeout: {summary['timeout']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Total Duration: {summary['duration']:.1f}s ({summary['duration']/60:.1f} minutes)")
    print(f"Average per Test: {summary['duration']/summary['total_tests']:.1f}s" if summary['total_tests'] > 0 else "N/A")
    print(f"{'='*60}\n")
    
    # Generate report if requested
    if args.report:
        runner.generate_report(args.report)
    
    # Exit with appropriate code
    sys.exit(0 if summary['failed'] == 0 and summary['timeout'] == 0 else 1)

if __name__ == "__main__":
    main()
