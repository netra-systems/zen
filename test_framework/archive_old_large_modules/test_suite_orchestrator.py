#!/usr/bin/env python
"""
Test Suite Orchestrator - Advanced test organization and execution management
Provides intelligent test suite orchestration with failure pattern analysis
"""

import os
import sys
import json
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
import hashlib
import re
from enum import Enum

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

class TestPriority(Enum):
    """Test priority levels for execution ordering"""
    CRITICAL = 1  # Must pass for deployment
    HIGH = 2      # Core functionality
    MEDIUM = 3    # Important features
    LOW = 4       # Nice-to-have tests
    OPTIONAL = 5  # Can be skipped if needed

class TestStatus(Enum):
    """Test execution status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"
    FLAKY = "flaky"

@dataclass
class TestProfile:
    """Profile of a test with historical data"""
    path: str
    name: str
    category: str
    priority: TestPriority = TestPriority.MEDIUM
    avg_duration: float = 0.0
    failure_rate: float = 0.0
    last_status: TestStatus = TestStatus.PENDING
    last_run: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_passes: int = 0
    total_runs: int = 0
    total_failures: int = 0
    dependencies: List[str] = field(default_factory=list)
    tags: Set[str] = field(default_factory=set)
    flaky_score: float = 0.0  # 0-1, higher means more flaky
    
    def update_result(self, status: TestStatus, duration: float):
        """Update test profile with new result"""
        self.total_runs += 1
        self.last_status = status
        self.last_run = datetime.now()
        
        # Update average duration
        if self.avg_duration == 0:
            self.avg_duration = duration
        else:
            self.avg_duration = (self.avg_duration * (self.total_runs - 1) + duration) / self.total_runs
        
        # Update failure tracking
        if status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]:
            self.total_failures += 1
            self.consecutive_failures += 1
            self.consecutive_passes = 0
        elif status == TestStatus.PASSED:
            self.consecutive_passes += 1
            self.consecutive_failures = 0
        
        # Update failure rate
        self.failure_rate = self.total_failures / self.total_runs if self.total_runs > 0 else 0
        
        # Calculate flaky score (tests that sometimes pass, sometimes fail)
        if self.total_runs > 5:
            if 0.2 < self.failure_rate < 0.8:
                self.flaky_score = 1 - abs(0.5 - self.failure_rate) * 2
            else:
                self.flaky_score = 0.0

@dataclass
class TestSuite:
    """Collection of tests with metadata"""
    name: str
    tests: List[TestProfile]
    priority: TestPriority = TestPriority.MEDIUM
    parallel_safe: bool = True
    max_parallel: int = 4
    timeout: int = 300
    retry_failed: bool = False
    retry_count: int = 1
    tags: Set[str] = field(default_factory=set)
    
    def get_execution_order(self) -> List[TestProfile]:
        """Get optimal execution order based on priorities and dependencies"""
        # Sort by priority, then by failure rate (run stable tests first)
        return sorted(self.tests, key=lambda t: (
            t.priority.value if isinstance(t.priority, TestPriority) else t.priority,
            t.failure_rate, 
            -t.avg_duration
        ))

class TestSuiteOrchestrator:
    """
    Orchestrates test suite execution with intelligent scheduling and failure analysis
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or PROJECT_ROOT / "test_framework" / "test_config.json"
        self.profiles_path = PROJECT_ROOT / "test_framework" / "test_profiles.json"
        self.history_path = PROJECT_ROOT / "test_framework" / "test_history.json"
        
        # Create directories
        self.config_path.parent.mkdir(exist_ok=True)
        
        # Load configurations
        self.config = self._load_config()
        self.test_profiles = self._load_profiles()
        self.test_history = self._load_history()
        
        # Test suites
        self.suites: Dict[str, TestSuite] = self._initialize_suites()
        
        # Execution tracking
        self.execution_queue: deque = deque()
        self.running_tests: Dict[str, TestProfile] = {}
        self.completed_tests: Dict[str, TestStatus] = {}
        
        # Failure pattern analysis
        self.failure_patterns: Dict[str, List[str]] = defaultdict(list)
        self.common_error_patterns = self._load_error_patterns()
        
    def _load_config(self) -> Dict:
        """Load test configuration"""
        if self.config_path.exists():
            with open(self.config_path, 'r') as f:
                return json.load(f)
        
        # Default configuration
        return {
            "max_parallel": 8,
            "timeout_multiplier": 1.5,
            "retry_flaky": True,
            "fail_fast": False,
            "coverage_threshold": 80,
            "performance_regression_threshold": 1.2,
            "test_categories": {
                "unit": {"priority": 2, "parallel": True, "timeout": 60},
                "integration": {"priority": 3, "parallel": True, "timeout": 120},
                "e2e": {"priority": 4, "parallel": False, "timeout": 300},
                "smoke": {"priority": 1, "parallel": True, "timeout": 30},
                "performance": {"priority": 5, "parallel": False, "timeout": 600}
            }
        }
    
    def _load_profiles(self) -> Dict[str, TestProfile]:
        """Load test profiles with historical data"""
        if self.profiles_path.exists():
            try:
                with open(self.profiles_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    data = json.loads(content)
                    profiles = {}
                    for test_id, profile_data in data.items():
                        profile = TestProfile(**profile_data)
                        profiles[test_id] = profile
                    return profiles
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def _load_history(self) -> List[Dict]:
        """Load test execution history"""
        if self.history_path.exists():
            with open(self.history_path, 'r') as f:
                return json.load(f)
        return []
    
    def _load_error_patterns(self) -> Dict[str, str]:
        """Load common error patterns for classification"""
        return {
            r"ImportError|ModuleNotFoundError": "import_error",
            r"AttributeError.*has no attribute": "attribute_error",
            r"TypeError.*arguments?": "type_error",
            r"AssertionError": "assertion_error",
            r"TimeoutError|timed? out": "timeout_error",
            r"ConnectionError|ConnectionRefused": "connection_error",
            r"PermissionError|Access.*denied": "permission_error",
            r"KeyError": "key_error",
            r"ValueError": "value_error",
            r"IndexError|list index out of range": "index_error",
            r"ZeroDivisionError": "zero_division_error",
            r"MemoryError|out of memory": "memory_error",
            r"mock.*Mock.*assert": "mock_assertion_error",
            r"fixture.*not found": "fixture_error",
            r"database.*connection": "database_error",
            r"redis.*connection": "redis_error",
            r"websocket.*closed": "websocket_error"
        }
    
    def _initialize_suites(self) -> Dict[str, TestSuite]:
        """Initialize test suites based on configuration"""
        suites = {}
        
        for category, config in self.config["test_categories"].items():
            suite = TestSuite(
                name=category,
                tests=[],
                priority=TestPriority(config["priority"]),
                parallel_safe=config["parallel"],
                timeout=config["timeout"]
            )
            suites[category] = suite
        
        return suites
    
    def discover_tests(self, path: Path = None) -> Dict[str, List[str]]:
        """Discover all tests in the project"""
        path = path or PROJECT_ROOT
        discovered = defaultdict(list)
        
        # Backend tests
        backend_test_dirs = [
            path / "app" / "tests",
            path / "tests",
            path / "integration_tests"
        ]
        
        for test_dir in backend_test_dirs:
            if test_dir.exists():
                for test_file in test_dir.rglob("test_*.py"):
                    category = self._categorize_test(test_file)
                    discovered[category].append(str(test_file))
        
        # Frontend tests
        frontend_test_dir = path / "frontend" / "__tests__"
        if frontend_test_dir.exists():
            for test_file in frontend_test_dir.rglob("*.test.{ts,tsx,js,jsx}"):
                discovered["frontend"].append(str(test_file))
        
        # Cypress tests
        cypress_dir = path / "frontend" / "cypress" / "e2e"
        if cypress_dir.exists():
            for test_file in cypress_dir.rglob("*.cy.{ts,js}"):
                discovered["e2e"].append(str(test_file))
        
        return dict(discovered)
    
    def _categorize_test(self, test_path: Path) -> str:
        """Categorize a test based on its path and name"""
        path_str = str(test_path).lower()
        
        # Check for specific patterns
        if "unit" in path_str or "app/tests/core" in path_str:
            return "unit"
        elif "integration" in path_str:
            return "integration"
        elif "e2e" in path_str or "cypress" in path_str:
            return "e2e"
        elif "smoke" in path_str:
            return "smoke"
        elif "performance" in path_str or "perf" in path_str:
            return "performance"
        elif "security" in path_str or "auth" in path_str:
            return "security"
        elif "websocket" in path_str or "ws_" in path_str:
            return "websocket"
        elif "database" in path_str or "db" in path_str:
            return "database"
        elif "api" in path_str or "route" in path_str:
            return "api"
        elif "agent" in path_str:
            return "agent"
        elif "llm" in path_str:
            return "llm"
        else:
            return "other"
    
    def analyze_failure_patterns(self, test_results: List[Dict]) -> Dict[str, Any]:
        """Analyze failure patterns to identify common issues"""
        analysis = {
            "total_failures": 0,
            "error_categories": defaultdict(int),
            "failing_modules": defaultdict(int),
            "time_based_failures": defaultdict(int),
            "flaky_tests": [],
            "consistent_failures": [],
            "regression_candidates": [],
            "recommended_actions": []
        }
        
        for result in test_results:
            if result.get("status") in ["failed", "error"]:
                analysis["total_failures"] += 1
                
                # Categorize error
                error_msg = result.get("error", "")
                for pattern, category in self.common_error_patterns.items():
                    if re.search(pattern, error_msg, re.IGNORECASE):
                        analysis["error_categories"][category] += 1
                        break
                
                # Track failing modules
                test_path = result.get("path", "")
                module = self._extract_module(test_path)
                analysis["failing_modules"][module] += 1
                
                # Check time-based patterns
                timestamp = result.get("timestamp")
                if timestamp:
                    hour = datetime.fromisoformat(timestamp).hour
                    if hour < 6 or hour > 22:
                        analysis["time_based_failures"]["off_hours"] += 1
                    else:
                        analysis["time_based_failures"]["business_hours"] += 1
        
        # Identify flaky tests
        test_results_by_name = defaultdict(list)
        for result in test_results:
            test_results_by_name[result.get("name", "")].append(result.get("status"))
        
        for test_name, statuses in test_results_by_name.items():
            if len(set(statuses)) > 1:  # Mixed results
                analysis["flaky_tests"].append(test_name)
            elif all(s in ["failed", "error"] for s in statuses):
                analysis["consistent_failures"].append(test_name)
        
        # Generate recommendations
        analysis["recommended_actions"] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _extract_module(self, test_path: str) -> str:
        """Extract module name from test path"""
        parts = Path(test_path).parts
        if "tests" in parts:
            idx = parts.index("tests")
            if idx + 1 < len(parts):
                return parts[idx + 1].replace("test_", "").replace(".py", "")
        return "unknown"
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate actionable recommendations based on failure analysis"""
        recommendations = []
        
        # Check for import errors
        if analysis["error_categories"].get("import_error", 0) > 5:
            recommendations.append("Fix dependency issues - multiple import errors detected")
        
        # Check for database errors
        if analysis["error_categories"].get("database_error", 0) > 3:
            recommendations.append("Check database connectivity and migrations")
        
        # Check for flaky tests
        if len(analysis["flaky_tests"]) > 10:
            recommendations.append(f"Address {len(analysis['flaky_tests'])} flaky tests - consider adding retries or fixing race conditions")
        
        # Check for consistent failures
        if len(analysis["consistent_failures"]) > 0:
            recommendations.append(f"Priority: Fix {len(analysis['consistent_failures'])} consistently failing tests")
        
        # Check for module concentration
        top_failing_module = max(analysis["failing_modules"].items(), key=lambda x: x[1])[0] if analysis["failing_modules"] else None
        if top_failing_module and analysis["failing_modules"][top_failing_module] > 5:
            recommendations.append(f"Focus on {top_failing_module} module - highest failure concentration")
        
        return recommendations
    
    async def execute_suite(
        self,
        suite_name: str,
        parallel: bool = True,
        fail_fast: bool = False,
        retry_failed: bool = True
    ) -> Dict[str, Any]:
        """Execute a test suite with intelligent scheduling"""
        if suite_name not in self.suites:
            raise ValueError(f"Suite {suite_name} not found")
        
        suite = self.suites[suite_name]
        results = {
            "suite": suite_name,
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        
        # Get execution order
        tests = suite.get_execution_order()
        
        if parallel and suite.parallel_safe:
            results["tests"] = await self._execute_parallel(tests, suite.max_parallel, fail_fast)
        else:
            results["tests"] = await self._execute_sequential(tests, fail_fast)
        
        # Retry failed tests if configured
        if retry_failed:
            failed_tests = [t for t in results["tests"] if t["status"] in ["failed", "error"]]
            if failed_tests:
                retry_results = await self._retry_tests(failed_tests, suite.retry_count)
                # Update results with retry outcomes
                for retry in retry_results:
                    for i, test in enumerate(results["tests"]):
                        if test["name"] == retry["name"]:
                            results["tests"][i] = retry
                            break
        
        # Generate summary
        results["end_time"] = datetime.now().isoformat()
        results["summary"] = self._generate_summary(results["tests"])
        
        # Save results
        self._save_results(results)
        
        return results
    
    async def _execute_parallel(
        self,
        tests: List[TestProfile],
        max_parallel: int,
        fail_fast: bool
    ) -> List[Dict]:
        """Execute tests in parallel"""
        results = []
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def run_test(test: TestProfile):
            async with semaphore:
                if fail_fast and any(r["status"] == "failed" for r in results):
                    return {"name": test.name, "status": "skipped", "reason": "fail_fast"}
                
                result = await self._run_single_test(test)
                results.append(result)
                return result
        
        tasks = [run_test(test) for test in tests]
        await asyncio.gather(*tasks)
        
        return results
    
    async def _execute_sequential(
        self,
        tests: List[TestProfile],
        fail_fast: bool
    ) -> List[Dict]:
        """Execute tests sequentially"""
        results = []
        
        for test in tests:
            if fail_fast and any(r["status"] == "failed" for r in results):
                results.append({"name": test.name, "status": "skipped", "reason": "fail_fast"})
                continue
            
            result = await self._run_single_test(test)
            results.append(result)
        
        return results
    
    async def _run_single_test(self, test: TestProfile) -> Dict:
        """Run a single test and return result"""
        start_time = time.time()
        
        # Prepare test command based on test type
        if test.path.endswith(".py"):
            cmd = [sys.executable, "-m", "pytest", test.path, "-xvs", "--tb=short"]
        elif test.path.endswith((".ts", ".tsx", ".js", ".jsx")):
            cmd = ["npm", "test", "--", test.path]
        else:
            return {
                "name": test.name,
                "path": test.path,
                "status": "error",
                "error": "Unknown test type",
                "duration": 0
            }
        
        try:
            # Run test with timeout
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=test.avg_duration * 2 if test.avg_duration > 0 else 60
                )
                
                duration = time.time() - start_time
                status = TestStatus.PASSED if process.returncode == 0 else TestStatus.FAILED
                
                # Update test profile
                test.update_result(status, duration)
                
                return {
                    "name": test.name,
                    "path": test.path,
                    "status": status.value,
                    "duration": duration,
                    "output": stdout.decode() if stdout else "",
                    "error": stderr.decode() if stderr and process.returncode != 0 else "",
                    "exit_code": process.returncode
                }
                
            except asyncio.TimeoutError:
                process.kill()
                duration = time.time() - start_time
                test.update_result(TestStatus.TIMEOUT, duration)
                
                return {
                    "name": test.name,
                    "path": test.path,
                    "status": "timeout",
                    "duration": duration,
                    "error": f"Test timed out after {duration:.2f}s"
                }
                
        except Exception as e:
            duration = time.time() - start_time
            test.update_result(TestStatus.ERROR, duration)
            
            return {
                "name": test.name,
                "path": test.path,
                "status": "error",
                "duration": duration,
                "error": str(e)
            }
    
    async def _retry_tests(self, failed_tests: List[Dict], retry_count: int) -> List[Dict]:
        """Retry failed tests"""
        retry_results = []
        
        for test_result in failed_tests:
            test_name = test_result["name"]
            test_profile = self.test_profiles.get(test_name)
            
            if not test_profile:
                continue
            
            best_result = test_result
            for i in range(retry_count):
                print(f"Retrying {test_name} (attempt {i+1}/{retry_count})")
                retry_result = await self._run_single_test(test_profile)
                
                if retry_result["status"] == "passed":
                    best_result = retry_result
                    best_result["retried"] = True
                    best_result["retry_attempt"] = i + 1
                    break
            
            retry_results.append(best_result)
        
        return retry_results
    
    def _generate_summary(self, test_results: List[Dict]) -> Dict:
        """Generate test execution summary"""
        summary = {
            "total": len(test_results),
            "passed": sum(1 for t in test_results if t["status"] == "passed"),
            "failed": sum(1 for t in test_results if t["status"] == "failed"),
            "skipped": sum(1 for t in test_results if t["status"] == "skipped"),
            "errors": sum(1 for t in test_results if t["status"] == "error"),
            "timeouts": sum(1 for t in test_results if t["status"] == "timeout"),
            "retried": sum(1 for t in test_results if t.get("retried", False)),
            "total_duration": sum(t.get("duration", 0) for t in test_results),
            "avg_duration": sum(t.get("duration", 0) for t in test_results) / len(test_results) if test_results else 0
        }
        
        summary["pass_rate"] = (summary["passed"] / summary["total"] * 100) if summary["total"] > 0 else 0
        
        return summary
    
    def _save_results(self, results: Dict):
        """Save test results and update profiles"""
        # Update test profiles
        for test_result in results["tests"]:
            test_name = test_result["name"]
            if test_name not in self.test_profiles:
                self.test_profiles[test_name] = TestProfile(
                    path=test_result["path"],
                    name=test_name,
                    category=results["suite"]
                )
        
        # Save profiles
        with open(self.profiles_path, 'w', encoding='utf-8') as f:
            profiles_data = {
                name: {
                    "path": p.path,
                    "name": p.name,
                    "category": p.category,
                    "priority": p.priority.value if isinstance(p.priority, TestPriority) else p.priority,
                    "avg_duration": p.avg_duration,
                    "failure_rate": p.failure_rate,
                    "last_status": p.last_status.value if isinstance(p.last_status, TestStatus) else p.last_status,
                    "last_run": p.last_run.isoformat() if p.last_run else None,
                    "consecutive_failures": p.consecutive_failures,
                    "consecutive_passes": p.consecutive_passes,
                    "total_runs": p.total_runs,
                    "total_failures": p.total_failures,
                    "flaky_score": p.flaky_score
                }
                for name, p in self.test_profiles.items()
            }
            json.dump(profiles_data, f, indent=2)
        
        # Append to history
        self.test_history.append(results)
        with open(self.history_path, 'w') as f:
            json.dump(self.test_history[-1000:], f, indent=2)  # Keep last 1000 runs
    
    def get_test_insights(self) -> Dict[str, Any]:
        """Get insights about test suite health"""
        insights = {
            "total_tests": len(self.test_profiles),
            "categories": defaultdict(int),
            "priority_distribution": defaultdict(int),
            "health_metrics": {},
            "problem_tests": [],
            "recommended_fixes": []
        }
        
        # Categorize tests
        for profile in self.test_profiles.values():
            insights["categories"][profile.category] += 1
            insights["priority_distribution"][profile.priority.name] += 1
        
        # Calculate health metrics
        total_failure_rate = sum(p.failure_rate for p in self.test_profiles.values()) / len(self.test_profiles) if self.test_profiles else 0
        avg_duration = sum(p.avg_duration for p in self.test_profiles.values()) / len(self.test_profiles) if self.test_profiles else 0
        flaky_tests = [p for p in self.test_profiles.values() if p.flaky_score > 0.3]
        
        insights["health_metrics"] = {
            "overall_failure_rate": total_failure_rate,
            "avg_test_duration": avg_duration,
            "flaky_test_count": len(flaky_tests),
            "flaky_test_percentage": len(flaky_tests) / len(self.test_profiles) * 100 if self.test_profiles else 0
        }
        
        # Identify problem tests
        for profile in self.test_profiles.values():
            if profile.consecutive_failures >= 3:
                insights["problem_tests"].append({
                    "name": profile.name,
                    "category": profile.category,
                    "consecutive_failures": profile.consecutive_failures,
                    "failure_rate": profile.failure_rate
                })
        
        # Sort problem tests by severity
        insights["problem_tests"].sort(key=lambda x: x["consecutive_failures"], reverse=True)
        
        # Generate recommendations
        if insights["health_metrics"]["overall_failure_rate"] > 0.1:
            insights["recommended_fixes"].append("High overall failure rate - review test environment and dependencies")
        
        if insights["health_metrics"]["flaky_test_percentage"] > 10:
            insights["recommended_fixes"].append(f"Fix {len(flaky_tests)} flaky tests to improve reliability")
        
        if insights["problem_tests"]:
            insights["recommended_fixes"].append(f"Priority: Fix {len(insights['problem_tests'])} consistently failing tests")
        
        return insights


def main():
    """Example usage of the Test Suite Orchestrator"""
    orchestrator = TestSuiteOrchestrator()
    
    # Discover tests
    print("Discovering tests...")
    discovered = orchestrator.discover_tests()
    for category, tests in discovered.items():
        print(f"  {category}: {len(tests)} tests")
    
    # Get test insights
    print("\nTest Suite Insights:")
    insights = orchestrator.get_test_insights()
    print(f"  Total tests: {insights['total_tests']}")
    print(f"  Health metrics:")
    for metric, value in insights['health_metrics'].items():
        print(f"    {metric}: {value:.2f}")
    
    if insights['recommended_fixes']:
        print("\n  Recommendations:")
        for rec in insights['recommended_fixes']:
            print(f"    - {rec}")
    
    # Example: Run smoke tests
    print("\nExample: Running smoke tests...")
    # asyncio.run(orchestrator.execute_suite("smoke", parallel=True, fail_fast=True))


if __name__ == "__main__":
    main()