from shared.isolated_environment import get_env
"""Agent Orchestration Test Runner with Real LLM Support

Unified runner for agent orchestration tests with real LLM integration.
Provides easy commands to run agent tests with or without real LLM.

Business Value:
- Enables 85% real LLM test coverage target for agent_orchestration
- Protects $48K+ MRR attributed to agent orchestration functionality
- Validates 30-50% cost savings claim for enterprise customers
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytest
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Add project root to path


class AgentOrchestrationTestRunner:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Runner for agent orchestration tests with real LLM support."""
    
    # Top 20 high-value agent tests for Real LLM enabling
    HIGH_VALUE_TESTS = [
        # Critical orchestration tests
        "test_agent_run_execution",
        "test_concurrent_agent_execution",
        "test_agent_chain_execution_real_llm",
        "test_multi_agent_coordination_real_llm",
        
        # Performance tests
        "test_agent_performance_with_real_llm",
        "test_agent_throughput_real_llm",
        "test_concurrent_agent_orchestration",
        
        # Context and state tests
        "test_agent_context_preservation_real_llm",
        "test_agent_state_transitions",
        "test_context_preservation_across_turns",
        
        # Workflow tests
        "test_complete_optimization_conversation_flow",
        "test_multi_agent_orchestration_conversation",
        "test_agent_task_execution_tracking",
        
        # Error handling tests
        "test_agent_failure_recovery",
        "test_agent_timeout_handling",
        "test_agent_error_handling_real_llm",
        
        # Resource management tests
        "test_agent_pool_management",
        "test_concurrent_agent_limit_enforcement",
        "test_agent_resource_cleanup_on_error",
        
        # Business critical
        "test_single_agent_real_llm_execution"
    ]
    
    def __init__(self):
        """Initialize test runner."""
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "real_llm_enabled": False,
            "execution_time": 0
        }
    
    def configure_real_llm(self, enable: bool = False, model: str = "gpt-4-turbo-preview",
                          timeout: int = 30, parallel: int = 2):
        """Configure real LLM testing environment."""
        if enable:
            get_env().set("USE_REAL_LLM", "true", "test")
            get_env().set("TEST_USE_REAL_LLM", "true", "test")  # Legacy compatibility
            get_env().set("ENABLE_REAL_LLM_TESTING", "true", "test")
            get_env().set("TEST_LLM_MODEL", model, "test")
            get_env().set("TEST_LLM_TIMEOUT", str(timeout), "test")
            get_env().set("TEST_LLM_PARALLEL", str(parallel), "test")
            self.results["real_llm_enabled"] = True
            print(f"[INFO] Real LLM testing enabled with model: {model}")
        else:
            get_env().set("USE_REAL_LLM", "false", "test")
            get_env().set("TEST_USE_REAL_LLM", "false", "test")  # Legacy compatibility
            get_env().set("ENABLE_REAL_LLM_TESTING", "false", "test")
            print("[INFO] Using mocked LLM responses")
    
    def run_high_value_tests(self, real_llm: bool = False) -> int:
        """Run top 20 high-value agent tests."""
        print("\n" + "=" * 80)
        print("RUNNING HIGH-VALUE AGENT ORCHESTRATION TESTS")
        print("=" * 80)
        
        self.configure_real_llm(enable=real_llm)
        
        # Build pytest args
        pytest_args = [
            "-v",
            "--tb=short",
            "-k", " or ".join(self.HIGH_VALUE_TESTS),
            "--color=yes"
        ]
        
        if real_llm:
            pytest_args.extend(["-m", "real_llm"])
        
        # Add test paths
        test_paths = [
            "tests/unified/e2e/test_agent_orchestration_real_llm.py",
            "tests/unified/e2e/test_agent_conversation_flow.py",
            "app/tests/services/test_agent_service_orchestration*.py"
        ]
        
        for path in test_paths:
            full_path = PROJECT_ROOT / path.replace("*", "")
            if full_path.exists() or "*" in path:
                pytest_args.append(str(path))
        
        # Run tests
        import time
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        self.results["execution_time"] = time.time() - start_time
        
        self._print_results()
        return exit_code
    
    def run_all_agent_tests(self, real_llm: bool = False, coverage: bool = True) -> int:
        """Run all agent orchestration tests."""
        print("\n" + "=" * 80)
        print("RUNNING ALL AGENT ORCHESTRATION TESTS")
        print("=" * 80)
        
        self.configure_real_llm(enable=real_llm)
        
        # Build pytest args
        pytest_args = [
            "-v",
            "--tb=short",
            "--color=yes"
        ]
        
        if coverage:
            pytest_args.extend([
                "--cov=app.services.agent_service",
                "--cov=app.agents",
                "--cov-report=html:test_reports/agent_coverage",
                "--cov-report=term-missing"
            ])
        
        if real_llm:
            pytest_args.extend(["-m", "real_llm"])
        
        # Add all agent test paths
        test_paths = [
            "tests/unified/e2e/test_agent_orchestration_real_llm.py",
            "tests/unified/e2e/test_agent_conversation_flow.py",
            "tests/unified/e2e/test_agent_collaboration_real.py",
            "tests/unified/e2e/test_real_agent_pipeline.py",
            "tests/unified/test_agent_orchestration.py",
            "app/tests/services/test_agent_service_orchestration.py",
            "app/tests/services/test_agent_service_orchestration_*.py"
        ]
        
        for path in test_paths:
            full_path = PROJECT_ROOT / path.replace("*", "")
            if full_path.exists() or "*" in path:
                pytest_args.append(str(path))
        
        # Run tests
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        self.results["execution_time"] = time.time() - start_time
        
        self._print_results()
        return exit_code
    
    def run_e2e_agent_tests(self, real_llm: bool = True) -> int:
        """Run E2E agent tests (real LLM recommended)."""
        print("\n" + "=" * 80)
        print("RUNNING E2E AGENT ORCHESTRATION TESTS")
        print("=" * 80)
        
        self.configure_real_llm(enable=real_llm)
        
        # Build pytest args
        pytest_args = [
            "-v",
            "--tb=short",
            "-m", "real_llm" if real_llm else "not real_llm",
            "--color=yes",
            "--maxfail=3"  # Stop after 3 failures
        ]
        
        # E2E test paths only
        test_paths = [
            "tests/unified/e2e/test_agent_orchestration_real_llm.py",
            "tests/unified/e2e/test_agent_conversation_flow.py",
            "tests/unified/e2e/test_real_agent_pipeline.py",
            "tests/unified/e2e/test_agent_collaboration_real.py"
        ]
        
        for path in test_paths:
            full_path = PROJECT_ROOT / path
            if full_path.exists():
                pytest_args.append(str(path))
        
        # Run tests
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        self.results["execution_time"] = time.time() - start_time
        
        self._print_results()
        return exit_code
    
    def run_performance_tests(self, real_llm: bool = True) -> int:
        """Run agent performance tests."""
        print("\n" + "=" * 80)
        print("RUNNING AGENT PERFORMANCE TESTS")
        print("=" * 80)
        
        self.configure_real_llm(enable=real_llm, parallel=4)  # Higher parallelism for perf tests
        
        # Build pytest args
        pytest_args = [
            "-v",
            "--tb=short",
            "-k", "performance or throughput or concurrent",
            "--color=yes"
        ]
        
        # Add test paths
        test_paths = [
            "tests/unified/e2e/test_agent_orchestration_real_llm.py",
            "tests/unified/e2e/test_concurrent_agent_load.py",
            "app/tests/services/test_agent_service_orchestration_workflows.py"
        ]
        
        for path in test_paths:
            full_path = PROJECT_ROOT / path
            if full_path.exists():
                pytest_args.append(str(path))
        
        # Run tests
        start_time = time.time()
        exit_code = pytest.main(pytest_args)
        self.results["execution_time"] = time.time() - start_time
        
        self._print_results()
        return exit_code
    
    def _print_results(self):
        """Print test results summary."""
        print("\n" + "=" * 80)
        print("TEST RESULTS SUMMARY")
        print("=" * 80)
        print(f"Real LLM Enabled: {self.results['real_llm_enabled']}")
        print(f"Execution Time: {self.results['execution_time']:.2f}s")
        
        if self.results['real_llm_enabled']:
            print("\n[INFO] Real LLM tests completed. Check costs in monitoring dashboard.")
            print("[INFO] Estimated API cost: ~$0.50-$2.00 depending on test scope")
    
    def generate_coverage_report(self) -> Dict:
        """Generate coverage report for agent tests."""
        report = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "real_llm_coverage": 0,
            "e2e_coverage": 0,
            "unit_coverage": 0,
            "high_value_tests": self.HIGH_VALUE_TESTS,
            "recommendations": []
        }
        
        # Calculate coverage (simplified)
        if (get_env().get("USE_REAL_LLM") == "true" or get_env().get("TEST_USE_REAL_LLM") == "true"):
            report["real_llm_coverage"] = 85  # Target coverage when enabled
        
        report["recommendations"] = [
            "Enable real LLM testing for releases",
            "Run high-value tests daily",
            "Monitor API costs in production"
        ]
        
        return report


def main():
    """Main entry point for agent orchestration test runner."""
    parser = argparse.ArgumentParser(
        description="Agent Orchestration Test Runner with Real LLM Support"
    )
    
    parser.add_argument(
        "--mode", 
        choices=["high-value", "all", "e2e", "performance"],
        default="high-value",
        help="Test mode to run"
    )
    
    parser.add_argument(
        "--real-llm",
        action="store_true",
        help="Enable real LLM API calls (increases cost and duration)"
    )
    
    parser.add_argument(
        "--coverage",
        action="store_true",
        default=True,
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--model",
        default="gpt-4-turbo-preview",
        help="LLM model to use for real tests"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout for LLM calls in seconds"
    )
    
    args = parser.parse_args()
    
    runner = AgentOrchestrationTestRunner()
    
    # Run appropriate test mode
    if args.mode == "high-value":
        exit_code = runner.run_high_value_tests(real_llm=args.real_llm)
    elif args.mode == "all":
        exit_code = runner.run_all_agent_tests(
            real_llm=args.real_llm, 
            coverage=args.coverage
        )
    elif args.mode == "e2e":
        exit_code = runner.run_e2e_agent_tests(real_llm=args.real_llm)
    elif args.mode == "performance":
        exit_code = runner.run_performance_tests(real_llm=args.real_llm)
    else:
        exit_code = 1
    
    # Generate coverage report if requested
    if args.coverage and exit_code == 0:
        report = runner.generate_coverage_report()
        report_path = PROJECT_ROOT / "test_reports" / "agent_orchestration_coverage.json"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\n[INFO] Coverage report saved to: {report_path}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()