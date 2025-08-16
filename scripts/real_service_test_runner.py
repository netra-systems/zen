#!/usr/bin/env python
"""
Real Service Test Runner
ULTRA DEEP THINK: Module-based architecture - Test runner extracted for 300-line compliance
"""

import os
import sys
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple, Dict
from real_service_test_metrics import RealServiceTestMetrics

class EnhancedRealServiceTestRunner:
    """Enhanced runner for real service tests with detailed reporting"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.metrics = RealServiceTestMetrics()
        self.test_dir = Path(__file__).parent.parent / "app" / "tests"
        self.reports_dir = Path(__file__).parent.parent / "test_reports" / "real_services"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
    
    def run_tests(self, 
                  categories: Optional[List[str]] = None,
                  model: str = "gemini-1.5-flash",
                  parallel: int = 1,
                  timeout: int = 300) -> int:
        """Run real service tests with specified configuration"""
        self._print_test_header(model, parallel, timeout, categories)
        env = self._setup_test_environment(model, timeout)
        cmd, json_report = self._build_pytest_command(categories, parallel, timeout)
        return self._execute_tests_with_handling(cmd, env, json_report, timeout)
    
    def _print_test_header(self, model: str, parallel: int, timeout: int, categories: Optional[List[str]]):
        """Print test execution header"""
        print("\n" + "="*60)
        print("ENHANCED REAL SERVICE TEST RUNNER")
        print("="*60)
        print(f"Model: {model}")
        print(f"Parallel: {parallel}")
        print(f"Timeout: {timeout}s")
        print(f"Categories: {categories or 'all'}")
        print("="*60)
    
    def _setup_test_environment(self, model: str, timeout: int) -> Dict[str, str]:
        """Setup environment variables for test execution"""
        env = os.environ.copy()
        env["ENABLE_REAL_LLM_TESTING"] = "true"
        env["ENABLE_REAL_DB_TESTING"] = "true"
        env["ENABLE_REAL_REDIS_TESTING"] = "true"
        env["ENABLE_REAL_CLICKHOUSE_TESTING"] = "true"
        env["TEST_LLM_MODEL"] = model
        env["TEST_LLM_TIMEOUT"] = str(timeout)
        return env
    
    def _build_pytest_command(self, categories: Optional[List[str]], parallel: int, timeout: int) -> Tuple[List[str], Path]:
        """Build pytest command with all options"""
        cmd = self._create_base_pytest_command(timeout)
        cmd = self._add_test_markers(cmd, categories)
        cmd = self._add_parallelization(cmd, parallel)
        json_report = self._add_json_reporting(cmd)
        return cmd, json_report
    
    def _create_base_pytest_command(self, timeout: int) -> List[str]:
        """Create base pytest command"""
        return [
            sys.executable, "-m", "pytest",
            str(self.test_dir),
            "-v", "--tb=short",
            f"--timeout={timeout}",
            "-W", "ignore::DeprecationWarning"
        ]
    
    def _add_test_markers(self, cmd: List[str], categories: Optional[List[str]]) -> List[str]:
        """Add test markers to command"""
        if categories:
            markers = " or ".join(categories)
            cmd.extend(["-m", markers])
        else:
            cmd.extend(["-m", "real_services"])
        return cmd
    
    def _add_parallelization(self, cmd: List[str], parallel: int) -> List[str]:
        """Add parallelization options to command"""
        if parallel > 1:
            cmd.extend(["-n", str(parallel)])
        return cmd
    
    def _add_json_reporting(self, cmd: List[str]) -> Path:
        """Add JSON reporting to command and return report path"""
        json_report = self.reports_dir / f"pytest_report_{int(time.time())}.json"
        cmd.extend(["--json-report", "--json-report-file", str(json_report)])
        return json_report
    
    def _execute_tests_with_handling(self, cmd: List[str], env: Dict[str, str], json_report: Path, timeout: int) -> int:
        """Execute tests with comprehensive error handling"""
        print("\nRunning tests...")
        try:
            result = self._run_subprocess(cmd, env, timeout)
            return self._process_successful_execution(result, json_report)
        except subprocess.TimeoutExpired:
            return self._handle_test_timeout(timeout)
        except Exception as e:
            return self._handle_test_error(e)
    
    def _run_subprocess(self, cmd: List[str], env: Dict[str, str], timeout: int) -> subprocess.CompletedProcess:
        """Run subprocess with specified configuration"""
        return subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            timeout=timeout * 10  # Give extra time for all tests
        )
    
    def _process_successful_execution(self, result: subprocess.CompletedProcess, json_report: Path) -> int:
        """Process successful test execution results"""
        self._parse_test_output(result.stdout + result.stderr)
        if json_report.exists():
            self._parse_json_report(json_report)
        self.metrics.finalize()
        self._generate_reports()
        self._print_summary()
        return result.returncode
    
    def _handle_test_timeout(self, timeout: int) -> int:
        """Handle test execution timeout"""
        print(f"\n[TIMEOUT] Tests exceeded timeout of {timeout * 10}s")
        self.metrics.metrics["errors"].append(f"Test execution timeout after {timeout * 10}s")
        self.metrics.finalize()
        self._generate_reports()
        return -1
    
    def _handle_test_error(self, error: Exception) -> int:
        """Handle general test execution error"""
        print(f"\n[ERROR] Test execution failed: {error}")
        self.metrics.metrics["errors"].append(str(error))
        self.metrics.finalize()
        self._generate_reports()
        return -1
    
    def _parse_test_output(self, output: str):
        """Parse test output for metrics"""
        import re
        
        # Parse test counts
        passed_match = re.search(r'(\d+) passed', output)
        failed_match = re.search(r'(\d+) failed', output)
        
        if passed_match:
            passed = int(passed_match.group(1))
            for i in range(passed):
                self.metrics.track_test_result("unknown", f"test_{i}", True, 0)
        
        if failed_match:
            failed = int(failed_match.group(1))
            for i in range(failed):
                self.metrics.track_test_result("unknown", f"test_{i}", False, 0)
        
        # Parse LLM calls (if logged)
        llm_pattern = r"LLM call: (\w+) with (\d+) tokens"
        for match in re.finditer(llm_pattern, output):
            model = match.group(1)
            tokens = int(match.group(2))
            self.metrics.track_llm_call(model, tokens)
        
        # Parse quality scores (if logged)
        quality_pattern = r"Quality score: ([\d.]+) for (\w+)"
        for match in re.finditer(quality_pattern, output):
            score = float(match.group(1))
            test = match.group(2)
            self.metrics.track_quality_score(score, test)
        
        # Parse cache hits/misses
        if "cache hit" in output.lower():
            self.metrics.track_cache(True)
        if "cache miss" in output.lower():
            self.metrics.track_cache(False)
    
    def _parse_json_report(self, json_file: Path):
        """Parse pytest JSON report for detailed metrics"""
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            
            # Extract test results
            for test in data.get("tests", []):
                category = self._categorize_test(test["nodeid"])
                passed = test["outcome"] == "passed"
                duration = test.get("duration", 0)
                self.metrics.track_test_result(category, test["nodeid"], passed, duration)
            
            # Extract summary
            summary = data.get("summary", {})
            if "total" in summary:
                self.metrics.metrics["pytest_summary"] = summary
                
        except Exception as e:
            self.metrics.metrics["warnings"].append(f"Failed to parse JSON report: {e}")
    
    def _categorize_test(self, test_path: str) -> str:
        """Categorize test based on path"""
        if "real_llm" in test_path:
            return "llm"
        elif "real_database" in test_path:
            return "database"
        elif "real_redis" in test_path:
            return "redis"
        elif "real_clickhouse" in test_path:
            return "clickhouse"
        elif "e2e" in test_path:
            return "e2e"
        else:
            return "integration"
    
    def _generate_reports(self):
        """Generate all report formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON report
        json_report = self.reports_dir / f"real_service_report_{timestamp}.json"
        with open(json_report, 'w') as f:
            f.write(self.metrics.generate_report("json"))
        print(f"\nJSON report: {json_report}")
        
        # Markdown report
        md_report = self.reports_dir / f"real_service_report_{timestamp}.md"
        with open(md_report, 'w') as f:
            f.write(self.metrics.generate_report("markdown"))
        print(f"Markdown report: {md_report}")
        
        # HTML report
        html_report = self.reports_dir / f"real_service_report_{timestamp}.html"
        with open(html_report, 'w') as f:
            f.write(self.metrics.generate_report("html"))
        print(f"HTML report: {html_report}")
        
        # Update latest symlinks
        for ext in ["json", "md", "html"]:
            latest = self.reports_dir / f"latest_real_service_report.{ext}"
            if latest.exists():
                latest.unlink()
            latest.symlink_to(self.reports_dir / f"real_service_report_{timestamp}.{ext}")
    
    def _print_summary(self):
        """Print test execution summary"""
        print("\n" + "="*60)
        print("TEST EXECUTION SUMMARY")
        print("="*60)
        
        # Test results
        total_tests = sum(len(tests) for tests in self.metrics.metrics["test_results"].values())
        if total_tests > 0:
            passed_tests = sum(1 for tests in self.metrics.metrics["test_results"].values() 
                              for test in tests if test["passed"])
            print(f"Tests: {passed_tests}/{total_tests} passed ({passed_tests/total_tests*100:.1f}%)")
        
        # LLM usage
        if self.metrics.metrics["llm_calls"]:
            total_calls = sum(self.metrics.metrics["llm_calls"].values())
            print(f"LLM Calls: {total_calls} (Cost: ${self.metrics.metrics['total_llm_cost']:.4f})")
        
        # Cache performance
        cache_total = self.metrics.metrics["cache_stats"]["hits"] + self.metrics.metrics["cache_stats"]["misses"]
        if cache_total > 0:
            print(f"Cache Hit Rate: {self.metrics.metrics['cache_stats']['hit_rate']:.1%}")
        
        # Quality scores
        if "quality_summary" in self.metrics.metrics:
            print(f"Avg Quality Score: {self.metrics.metrics['quality_summary']['average']:.3f}")
        
        print(f"Duration: {self.metrics.metrics['duration']:.2f}s")
        print("="*60)