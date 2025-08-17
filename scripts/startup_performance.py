#!/usr/bin/env python
"""
Startup Performance Testing
Handles performance benchmarks and metrics
"""

import os
import subprocess
import time
import psutil
from typing import Dict, Any, Optional
from startup_test_executor import TestResult


class PerformanceMetrics:
    """Container for performance metrics"""
    
    def __init__(self):
        self.startup_time = 0.0
        self.memory_baseline = 0.0
        self.memory_after_startup = 0.0
        self.api_response_time = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization"""
        return {
            "startup_time": self.startup_time,
            "memory_baseline": self.memory_baseline,
            "memory_after_startup": self.memory_after_startup,
            "api_response_time": self.api_response_time
        }


class BackendProcess:
    """Manages backend process for performance testing"""
    
    def __init__(self):
        self.process = None
        self.env = None
    
    def setup_environment(self) -> Dict[str, str]:
        """Setup environment for backend process"""
        self.env = os.environ.copy()
        self.env["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
        self.env["TESTING"] = "1"
        return self.env
    
    def start(self) -> subprocess.Popen:
        """Start backend process"""
        self.process = subprocess.Popen(
            ["python", "run_server.py"],
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return self.process
    
    def measure_memory_usage(self) -> float:
        """Measure memory usage of process"""
        if self.process and self.process.poll() is None:
            try:
                p = psutil.Process(self.process.pid)
                return p.memory_info().rss / (1024**2)  # MB
            except:
                pass
        return 0.0
    
    def cleanup(self):
        """Cleanup backend process"""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)


class PerformanceTestExecutor:
    """Executes performance benchmarks"""
    
    def __init__(self, args):
        self.args = args
        self.metrics = PerformanceMetrics()
        self.backend = BackendProcess()
    
    def run_tests(self) -> Optional[TestResult]:
        """Run performance benchmarks"""
        if self._should_skip_tests():
            return None
        self._setup_and_print_header()
        self._run_startup_benchmark()
        self._display_results()
        passed = self._check_thresholds()
        test_result = self._create_result(passed)
        self._display_final_status(test_result)
        return test_result
    
    def _should_skip_tests(self) -> bool:
        """Check if performance tests should be skipped"""
        return self.args.mode not in ["full", "performance"]
    
    def _setup_and_print_header(self):
        """Setup performance test header"""
        print("\n" + "-"*40)
        print("Running Performance Tests")
        print("-"*40)
    
    def _run_startup_benchmark(self):
        """Run startup time benchmark"""
        self.backend.setup_environment()
        print("Measuring startup time...")
        start_time = time.time()
        self.backend.start()
        self.metrics.startup_time = time.time() - start_time
        self.metrics.memory_after_startup = self.backend.measure_memory_usage()
        self.backend.cleanup()
    
    def _display_results(self):
        """Display performance test results"""
        print(f"\nPerformance Metrics:")
        print(f"  Startup time: {self.metrics.startup_time:.2f}s")
        print(f"  Memory usage: {self.metrics.memory_after_startup:.2f} MB")
    
    def _check_thresholds(self) -> bool:
        """Check if metrics pass performance thresholds"""
        return (
            self.metrics.startup_time < 10 and  # Less than 10 seconds
            self.metrics.memory_after_startup < 500  # Less than 500MB
        )
    
    def _create_result(self, passed: bool) -> TestResult:
        """Create performance test result object"""
        result = TestResult(
            name="Performance Tests",
            duration=self.metrics.startup_time,
            passed=passed
        )
        result.metrics = self.metrics.to_dict()
        return result
    
    def _display_final_status(self, test_result: TestResult):
        """Display final performance test status"""
        status_msg = ("[OK] Performance tests passed" 
                     if test_result.passed 
                     else "[FAIL] Performance tests failed (exceeded thresholds)")
        print(status_msg)