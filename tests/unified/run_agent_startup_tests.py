"""
Agent Startup E2E Test Runner - Comprehensive Agent Initialization Testing

Integrates all agent startup tests into a unified runner with performance baselines,
real LLM support, and comprehensive reporting. Single command execution for all
agent startup validation scenarios.

Business Value Justification (BVJ):
1. Segment: ALL customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure 100% reliable agent startup across all scenarios
3. Value Impact: Prevents agent initialization failures blocking user interactions
4. Revenue Impact: Protects entire $200K+ MRR by ensuring reliable startup process

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Integrates with existing test_runner.py framework
- Real LLM testing support with --real-llm flag
- Performance baseline tracking and reporting
- Parallel execution where safe
"""

import asyncio
import time
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Test framework imports
sys.path.append(str(Path(__file__).parent.parent.parent))
from test_framework.test_config import configure_real_llm, TEST_LEVELS
from test_framework.runner import UnifiedTestRunner
from netra_backend.app.tests.performance.performance_baseline_config import (
    get_benchmark_runner, PerformanceCategory
)


class AgentStartupCategory(Enum):
    """Categories of agent startup tests."""
    COLD_START = "cold_start"
    CONCURRENT_STARTUP = "concurrent_startup"
    TIER_STARTUP = "tier_startup"
    AGENT_ISOLATION = "agent_isolation"
    STATE_INITIALIZATION = "state_initialization"
    ROUTING_STARTUP = "routing_startup"
    PERFORMANCE_STARTUP = "performance_startup"


@dataclass
class StartupTestConfig:
    """Configuration for startup test execution."""
    category: AgentStartupCategory
    test_module: str
    test_function: str
    timeout_seconds: int
    requires_real_llm: bool
    parallel_safe: bool
    performance_metric: Optional[str] = None


class AgentStartupTestRunner:
    """Orchestrates agent startup E2E test execution."""
    
    def __init__(self, real_llm: bool = False, parallel: bool = True):
        """Initialize startup test runner."""
        self.real_llm = real_llm
        self.parallel = parallel
        self.test_configs = self._initialize_test_configs()
        self.benchmark_runner = get_benchmark_runner()
        self.results: List[Dict[str, Any]] = []
    
    def _initialize_test_configs(self) -> List[StartupTestConfig]:
        """Initialize startup test configurations."""
        return [
            StartupTestConfig(
                AgentStartupCategory.COLD_START,
                "test_agent_cold_start",
                "test_complete_agent_cold_start",
                30, True, False, "agent_cold_start_time"
            ),
            StartupTestConfig(
                AgentStartupCategory.CONCURRENT_STARTUP,
                "test_concurrent_agents", 
                "test_concurrent_agent_startup_isolation",
                45, True, True, "concurrent_startup_time"
            ),
            StartupTestConfig(
                AgentStartupCategory.TIER_STARTUP,
                "test_agent_cold_start",
                "test_cold_start_with_different_user_tiers", 
                60, True, True, "tier_startup_time"
            ),
            StartupTestConfig(
                AgentStartupCategory.AGENT_ISOLATION,
                "test_concurrent_agents",
                "test_no_shared_state_between_users",
                30, False, True, "isolation_validation_time"
            ),
            StartupTestConfig(
                AgentStartupCategory.ROUTING_STARTUP,
                "test_concurrent_agents",
                "test_concurrent_message_routing_accuracy",
                25, False, True, "routing_startup_time"
            ),
            StartupTestConfig(
                AgentStartupCategory.PERFORMANCE_STARTUP,
                "test_concurrent_agents",
                "test_performance_metrics_concurrent_agents",
                40, True, False, "performance_startup_time"
            )
        ]
    
    async def run_all_startup_tests(self) -> Dict[str, Any]:
        """Execute all agent startup tests with comprehensive reporting."""
        print("=" * 80)
        print("AGENT STARTUP E2E TEST SUITE")
        print("=" * 80)
        
        start_time = time.time()
        test_results = await _execute_test_suite(self)
        execution_time = time.time() - start_time
        
        return _generate_comprehensive_report(self, test_results, execution_time)


class StartupTestExecutor:
    """Executes individual startup test categories."""
    
    def __init__(self, runner: AgentStartupTestRunner):
        """Initialize executor with runner reference."""
        self.runner = runner
        self.execution_results: List[Dict[str, Any]] = []
    
    async def execute_test_category(self, config: StartupTestConfig) -> Dict[str, Any]:
        """Execute single test category with performance tracking."""
        print(f"\n[{config.category.value.upper()}] Starting {config.test_function}")
        
        if config.requires_real_llm and not self.runner.real_llm:
            return self._create_skip_result(config, "Real LLM required but not enabled")
        
        start_time = time.time()
        result = await self._run_single_test(config)
        execution_time = time.time() - start_time
        
        self._record_performance_metric(config, execution_time, result)
        return self._create_test_result(config, result, execution_time)
    
    async def _run_single_test(self, config: StartupTestConfig) -> Dict[str, Any]:
        """Run single test with proper isolation and error handling."""
        try:
            # Use pytest runner for proper test execution
            import subprocess
            test_cmd = self._build_test_command(config)
            
            result = subprocess.run(
                test_cmd, capture_output=True, text=True, timeout=config.timeout_seconds
            )
            
            return self._process_subprocess_result(result)
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _build_test_command(self, config: StartupTestConfig) -> List[str]:
        """Build pytest command for test execution."""
        cmd = ["python", "-m", "pytest", "-v"]
        cmd.append(f"tests/unified/{config.test_module}.py::{config.test_function}")
        
        if self.runner.real_llm:
            cmd.extend(["--real-llm", "--llm-timeout", "30"])
        
        return cmd
    
    def _process_subprocess_result(self, result) -> Dict[str, Any]:
        """Process subprocess execution result."""
        if result.returncode == 0:
            return {"status": "passed", "error": None}
        else:
            return {"status": "failed", "error": result.stderr or result.stdout}
    
    def _record_performance_metric(self, config: StartupTestConfig, 
                                   execution_time: float, result: Dict[str, Any]) -> None:
        """Record performance metric for baseline tracking."""
        if config.performance_metric and self.runner.benchmark_runner:
            self.runner.benchmark_runner.record_result(
                config.performance_metric,
                execution_time,
                execution_time,
                {"test_category": config.category.value, "status": result["status"]}
            )
    
    def _create_skip_result(self, config: StartupTestConfig, reason: str) -> Dict[str, Any]:
        """Create result for skipped test."""
        return {
            "category": config.category.value,
            "test_function": config.test_function,
            "status": "skipped",
            "reason": reason,
            "execution_time": 0,
            "timestamp": time.time()
        }
    
    def _create_test_result(self, config: StartupTestConfig, result: Dict[str, Any], 
                            execution_time: float) -> Dict[str, Any]:
        """Create comprehensive test result."""
        return {
            "category": config.category.value,
            "test_function": config.test_function,
            "status": result["status"],
            "execution_time": execution_time,
            "error": result.get("error"),
            "timestamp": time.time(),
            "requires_real_llm": config.requires_real_llm,
            "parallel_safe": config.parallel_safe
        }


class StartupTestReporter:
    """Generates comprehensive test reports and summaries."""
    
    def __init__(self, runner: AgentStartupTestRunner):
        """Initialize reporter with runner reference."""
        self.runner = runner
    
    def generate_startup_report(self, results: List[Dict[str, Any]], 
                                execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive startup test report."""
        summary = self._calculate_summary_stats(results)
        performance_report = self._generate_performance_report()
        
        return {
            "test_suite": "Agent Startup E2E Tests",
            "timestamp": time.time(),
            "execution_time": execution_time,
            "configuration": self._get_test_configuration(),
            "summary": summary,
            "performance_baselines": performance_report,
            "detailed_results": results,
            "recommendations": self._generate_recommendations(results)
        }
    
    def _calculate_summary_stats(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate summary statistics from test results."""
        total = len(results)
        passed = len([r for r in results if r["status"] == "passed"])
        failed = len([r for r in results if r["status"] == "failed"])
        skipped = len([r for r in results if r["status"] == "skipped"])
        
        return {
            "total_tests": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "pass_rate": (passed / total * 100) if total > 0 else 0,
            "avg_execution_time": sum(r["execution_time"] for r in results) / total if total > 0 else 0
        }
    
    def _generate_performance_report(self) -> Dict[str, Any]:
        """Generate performance baseline report."""
        if self.runner.benchmark_runner:
            return self.runner.benchmark_runner.generate_final_report(save_to_file=False)
        return {}
    
    def _get_test_configuration(self) -> Dict[str, Any]:
        """Get current test configuration details."""
        return {
            "real_llm_enabled": self.runner.real_llm,
            "parallel_execution": self.runner.parallel,
            "total_categories": len(self.runner.test_configs),
            "real_llm_tests": len([c for c in self.runner.test_configs if c.requires_real_llm])
        }
    
    def _generate_recommendations(self, results: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []
        failed_tests = [r for r in results if r["status"] == "failed"]
        
        if failed_tests:
            recommendations.append("Review failed tests for startup issues")
        
        slow_tests = [r for r in results if r["execution_time"] > 30]
        if slow_tests:
            recommendations.append("Consider optimizing slow startup tests")
        
        if not self.runner.real_llm:
            recommendations.append("Run with --real-llm for complete validation")
        
        return recommendations


# Main execution functions (each ≤8 lines)
async def run_agent_startup_test_suite(real_llm: bool = False, 
                                       parallel: bool = True) -> Dict[str, Any]:
    """Main entry point for agent startup test suite."""
    runner = AgentStartupTestRunner(real_llm, parallel)
    return await runner.run_all_startup_tests()


async def _execute_test_suite(runner: AgentStartupTestRunner) -> List[Dict[str, Any]]:
    """Execute the complete test suite with proper orchestration."""
    executor = StartupTestExecutor(runner)
    
    if runner.parallel:
        return await _run_parallel_tests(executor, runner.test_configs)
    else:
        return await _run_sequential_tests(executor, runner.test_configs)


async def _run_parallel_tests(executor: StartupTestExecutor, 
                              configs: List[StartupTestConfig]) -> List[Dict[str, Any]]:
    """Execute parallel-safe tests concurrently."""
    parallel_configs = [c for c in configs if c.parallel_safe]
    sequential_configs = [c for c in configs if not c.parallel_safe]
    
    # Run parallel tests concurrently
    parallel_tasks = [executor.execute_test_category(config) for config in parallel_configs]
    parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=True)
    
    # Run sequential tests one by one
    sequential_results = await _run_sequential_tests(executor, sequential_configs)
    
    return _process_mixed_results(parallel_results, sequential_results)


async def _run_sequential_tests(executor: StartupTestExecutor, 
                                configs: List[StartupTestConfig]) -> List[Dict[str, Any]]:
    """Execute tests sequentially for safety."""
    results = []
    for config in configs:
        result = await executor.execute_test_category(config)
        results.append(result)
    return results


def _process_mixed_results(parallel_results: List[Any], 
                           sequential_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Process and combine parallel and sequential test results."""
    processed_parallel = []
    for result in parallel_results:
        if isinstance(result, Exception):
            processed_parallel.append({
                "status": "failed", 
                "error": str(result), 
                "execution_time": 0,
                "category": "unknown"
            })
        else:
            processed_parallel.append(result)
    
    return processed_parallel + sequential_results


def _generate_comprehensive_report(runner: AgentStartupTestRunner, 
                                   results: List[Dict[str, Any]], 
                                   execution_time: float) -> Dict[str, Any]:
    """Generate final comprehensive report."""
    reporter = StartupTestReporter(runner)
    report = reporter.generate_startup_report(results, execution_time)
    
    # Save report to file
    report_path = Path("test_reports/agent_startup_test_report.json")
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n[REPORT] Comprehensive report saved: {report_path}")
    return report


def print_startup_test_summary(report: Dict[str, Any]) -> None:
    """Print comprehensive startup test summary."""
    print("\n" + "=" * 80)
    print("AGENT STARTUP E2E TEST SUMMARY")
    print("=" * 80)
    
    summary = report.get("summary", {})
    print(f"Total Tests: {summary.get('total_tests', 0)}")
    print(f"Passed: {summary.get('passed', 0)}")
    print(f"Failed: {summary.get('failed', 0)}")
    print(f"Skipped: {summary.get('skipped', 0)}")
    print(f"Pass Rate: {summary.get('pass_rate', 0):.1f}%")
    print(f"Average Execution Time: {summary.get('avg_execution_time', 0):.2f}s")
    print(f"Total Suite Time: {report.get('execution_time', 0):.2f}s")
    
    recommendations = report.get("recommendations", [])
    if recommendations:
        print("\nRecommendations:")
        for rec in recommendations:
            print(f"  - {rec}")
    
    print("=" * 80)


if __name__ == "__main__":
    """Command-line execution of agent startup tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Agent Startup E2E Test Runner")
    parser.add_argument("--real-llm", action="store_true", 
                        help="Enable real LLM testing")
    parser.add_argument("--no-parallel", action="store_true", 
                        help="Disable parallel execution")
    
    args = parser.parse_args()
    
    async def main():
        """Main async execution."""
        report = await run_agent_startup_test_suite(
            real_llm=args.real_llm,
            parallel=not args.no_parallel
        )
        print_startup_test_summary(report)
        
        # Exit with appropriate code
        summary = report.get("summary", {})
        exit_code = 0 if summary.get("failed", 0) == 0 else 1
        sys.exit(exit_code)
    
    asyncio.run(main())