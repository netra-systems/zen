"""
Enhanced Test Runner with Resilience for Issue #1278

Provides resilient test execution with retry logic, graceful degradation,
and enhanced error handling for infrastructure connectivity issues.

Business Value: Platform/Internal - Test Infrastructure Resilience
Enables reliable test execution during staging infrastructure failures.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, UTC
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Union
import subprocess
import sys
from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment, get_env
from .test_connectivity_validator import (
    TestConnectivityValidator,
    InfrastructureHealth,
    ConnectivityStatus
)

logger = logging.getLogger(__name__)


class TestExecutionMode(Enum):
    """Test execution modes for different infrastructure states."""
    FULL = "full"                      # All services available
    DEGRADED = "degraded"              # Some services available, others in fallback
    OFFLINE = "offline"                # No external services, all local/mocked
    CRITICAL_ONLY = "critical_only"    # Only critical path tests


class TestStatus(Enum):
    """Test execution status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_UNAVAILABLE = "infrastructure_unavailable"


@dataclass
class TestResult:
    """Result of test execution."""
    test_name: str
    status: TestStatus
    execution_time: float = 0.0
    error_message: Optional[str] = None
    retry_count: int = 0
    execution_mode: Optional[TestExecutionMode] = None
    infrastructure_health: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_success(self) -> bool:
        """Check if test was successful."""
        return self.status in {TestStatus.PASSED, TestStatus.SKIPPED}

    @property
    def needs_retry(self) -> bool:
        """Check if test should be retried."""
        return self.status in {TestStatus.FAILED, TestStatus.TIMEOUT, TestStatus.INFRASTRUCTURE_UNAVAILABLE}


@dataclass
class TestSuiteResult:
    """Result of test suite execution."""
    results: List[TestResult] = field(default_factory=list)
    execution_mode: Optional[TestExecutionMode] = None
    infrastructure_health: Optional[InfrastructureHealth] = None
    total_execution_time: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def total_tests(self) -> int:
        """Total number of tests."""
        return len(self.results)

    @property
    def passed_tests(self) -> int:
        """Number of passed tests."""
        return sum(1 for r in self.results if r.status == TestStatus.PASSED)

    @property
    def failed_tests(self) -> int:
        """Number of failed tests."""
        return sum(1 for r in self.results if r.status == TestStatus.FAILED)

    @property
    def skipped_tests(self) -> int:
        """Number of skipped tests."""
        return sum(1 for r in self.results if r.status == TestStatus.SKIPPED)

    @property
    def error_tests(self) -> int:
        """Number of tests with errors."""
        return sum(1 for r in self.results if r.status == TestStatus.ERROR)

    @property
    def infrastructure_unavailable_tests(self) -> int:
        """Number of tests skipped due to infrastructure."""
        return sum(1 for r in self.results if r.status == TestStatus.INFRASTRUCTURE_UNAVAILABLE)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100.0

    @property
    def is_successful(self) -> bool:
        """Check if overall suite execution was successful."""
        return self.failed_tests == 0 and self.error_tests == 0


class ResilientTestRunner:
    """
    Test runner with enhanced resilience for infrastructure failures.

    Provides retry logic, graceful degradation, and infrastructure-aware
    test execution to handle staging connectivity issues.
    """

    def __init__(self, env: Optional[IsolatedEnvironment] = None):
        """Initialize resilient test runner."""
        self.env = env or get_env()
        self.validator = TestConnectivityValidator(self.env)

        # Configuration from environment
        self.retry_attempts = int(self.env.get("TEST_RETRY_ATTEMPTS", "3"))
        self.retry_delay = float(self.env.get("TEST_RETRY_DELAY", "2"))
        self.graceful_degradation = self.env.get("TEST_GRACEFUL_DEGRADATION", "true").lower() == "true"
        self.skip_on_infrastructure_failure = self.env.get("TEST_SKIP_ON_INFRASTRUCTURE_FAILURE", "true").lower() == "true"

    async def assess_infrastructure_health(self, quick_check: bool = False) -> InfrastructureHealth:
        """Assess infrastructure health before running tests."""
        if quick_check:
            return await self.validator.validate_quick_health_check()
        else:
            return await self.validator.validate_all_services()

    def determine_execution_mode(self, health: InfrastructureHealth) -> TestExecutionMode:
        """Determine appropriate test execution mode based on infrastructure health."""
        if health.overall_status == ConnectivityStatus.AVAILABLE:
            return TestExecutionMode.FULL
        elif health.overall_status == ConnectivityStatus.DEGRADED:
            return TestExecutionMode.DEGRADED
        elif health.is_staging_available:
            return TestExecutionMode.CRITICAL_ONLY
        else:
            return TestExecutionMode.OFFLINE

    def apply_resilient_configuration(self, health: InfrastructureHealth, execution_mode: TestExecutionMode) -> None:
        """Apply resilient configuration based on infrastructure health."""
        fallback_config = self.validator.get_fallback_configuration(health)

        # Apply execution mode specific settings
        if execution_mode == TestExecutionMode.OFFLINE:
            fallback_config.update({
                "NO_REAL_SERVERS": "true",
                "TEST_OFFLINE": "true",
                "WEBSOCKET_MOCK_MODE": "true",
                "LLM_FALLBACK_MODE": "true"
            })
        elif execution_mode == TestExecutionMode.DEGRADED:
            fallback_config.update({
                "INFRASTRUCTURE_DEGRADED_MODE": "true",
                "TEST_GRACEFUL_DEGRADATION": "true"
            })
        elif execution_mode == TestExecutionMode.CRITICAL_ONLY:
            fallback_config.update({
                "TEST_CRITICAL_ONLY": "true",
                "SKIP_NON_CRITICAL_TESTS": "true"
            })

        # Apply configuration to environment
        for key, value in fallback_config.items():
            self.env.set(key, value, "resilient_test_runner")

        logger.info(f"Applied resilient configuration for {execution_mode.value} mode")

    async def run_single_test_with_retry(
        self,
        test_command: str,
        test_name: str,
        execution_mode: TestExecutionMode,
        infrastructure_health: str
    ) -> TestResult:
        """Run a single test with retry logic."""
        start_time = time.time()
        last_error = None

        for attempt in range(self.retry_attempts + 1):
            try:
                # Add delay between retries (except first attempt)
                if attempt > 0:
                    await asyncio.sleep(self.retry_delay)
                    logger.info(f"Retrying test {test_name} (attempt {attempt + 1}/{self.retry_attempts + 1})")

                # Execute test
                result = await self._execute_test_command(test_command, test_name)

                # If successful, return result
                if result.is_success:
                    result.retry_count = attempt
                    result.execution_mode = execution_mode
                    result.infrastructure_health = infrastructure_health
                    return result

                # If failed but not due to infrastructure, don't retry
                if not self._should_retry_test(result):
                    result.retry_count = attempt
                    result.execution_mode = execution_mode
                    result.infrastructure_health = infrastructure_health
                    return result

                last_error = result.error_message

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Test {test_name} attempt {attempt + 1} failed: {e}")

        # All retries exhausted
        execution_time = time.time() - start_time
        return TestResult(
            test_name=test_name,
            status=TestStatus.FAILED,
            execution_time=execution_time,
            error_message=f"Failed after {self.retry_attempts + 1} attempts. Last error: {last_error}",
            retry_count=self.retry_attempts,
            execution_mode=execution_mode,
            infrastructure_health=infrastructure_health
        )

    async def _execute_test_command(self, command: str, test_name: str) -> TestResult:
        """Execute a test command and return result."""
        start_time = time.time()

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd()
            )

            stdout, stderr = await process.communicate()
            execution_time = time.time() - start_time

            # Determine status based on return code
            if process.returncode == 0:
                status = TestStatus.PASSED
                error_message = None
            else:
                status = TestStatus.FAILED
                error_message = stderr.decode() if stderr else stdout.decode()

                # Check for infrastructure-related failures
                if self._is_infrastructure_failure(error_message):
                    status = TestStatus.INFRASTRUCTURE_UNAVAILABLE

            return TestResult(
                test_name=test_name,
                status=status,
                execution_time=execution_time,
                error_message=error_message
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.TIMEOUT,
                execution_time=execution_time,
                error_message="Test execution timed out"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status=TestStatus.ERROR,
                execution_time=execution_time,
                error_message=str(e)
            )

    def _should_retry_test(self, result: TestResult) -> bool:
        """Determine if a test should be retried based on its result."""
        # Retry infrastructure-related failures
        if result.status == TestStatus.INFRASTRUCTURE_UNAVAILABLE:
            return True

        # Retry timeouts
        if result.status == TestStatus.TIMEOUT:
            return True

        # Check error message for retryable patterns
        if result.error_message:
            retryable_patterns = [
                "connection refused",
                "connection timeout",
                "network unreachable",
                "service unavailable",
                "temporary failure",
                "502 bad gateway",
                "503 service unavailable",
                "504 gateway timeout"
            ]
            error_lower = result.error_message.lower()
            return any(pattern in error_lower for pattern in retryable_patterns)

        return False

    def _is_infrastructure_failure(self, error_message: str) -> bool:
        """Check if error message indicates infrastructure failure."""
        if not error_message:
            return False

        infrastructure_patterns = [
            "connection refused",
            "connection timeout",
            "network unreachable",
            "service unavailable",
            "database connection",
            "redis connection",
            "websocket connection",
            "backend not accessible",
            "staging backend not healthy",
            "vpc connector",
            "cloud sql"
        ]

        error_lower = error_message.lower()
        return any(pattern in error_lower for pattern in infrastructure_patterns)

    async def run_test_suite(
        self,
        test_commands: List[str],
        test_names: Optional[List[str]] = None,
        quick_health_check: bool = False
    ) -> TestSuiteResult:
        """Run a complete test suite with resilience."""
        start_time = time.time()

        # Assess infrastructure health
        logger.info("Assessing infrastructure health before test execution...")
        health = await self.assess_infrastructure_health(quick_health_check)

        # Determine execution mode
        execution_mode = self.determine_execution_mode(health)
        logger.info(f"Test execution mode: {execution_mode.value}")

        # Apply resilient configuration
        self.apply_resilient_configuration(health, execution_mode)

        # Check if tests should be skipped
        should_skip, skip_reason = self.validator.should_skip_tests(health)
        if should_skip and self.skip_on_infrastructure_failure:
            logger.warning(f"Skipping all tests: {skip_reason}")
            results = [
                TestResult(
                    test_name=test_names[i] if test_names else f"test_{i}",
                    status=TestStatus.INFRASTRUCTURE_UNAVAILABLE,
                    error_message=skip_reason,
                    execution_mode=execution_mode,
                    infrastructure_health=health.overall_status.value
                )
                for i in range(len(test_commands))
            ]
        else:
            # Execute tests
            results = []
            infrastructure_health_str = health.overall_status.value

            for i, command in enumerate(test_commands):
                test_name = test_names[i] if test_names else f"test_{i}"

                logger.info(f"Executing test: {test_name}")
                result = await self.run_single_test_with_retry(
                    command, test_name, execution_mode, infrastructure_health_str
                )
                results.append(result)

                # Log result
                if result.status == TestStatus.PASSED:
                    logger.info(f"✓ {test_name} passed ({result.execution_time:.3f}s)")
                elif result.status == TestStatus.SKIPPED:
                    logger.info(f"- {test_name} skipped")
                else:
                    logger.error(f"✗ {test_name} {result.status.value} ({result.execution_time:.3f}s)")
                    if result.error_message:
                        logger.error(f"  Error: {result.error_message}")

        total_execution_time = time.time() - start_time

        return TestSuiteResult(
            results=results,
            execution_mode=execution_mode,
            infrastructure_health=health,
            total_execution_time=total_execution_time
        )

    def generate_resilience_report(self, suite_result: TestSuiteResult) -> str:
        """Generate a comprehensive resilience report."""
        report_lines = [
            "# Test Resilience Report - Issue #1278",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Execution Mode:** {suite_result.execution_mode.value if suite_result.execution_mode else 'unknown'}",
            f"**Infrastructure Status:** {suite_result.infrastructure_health.overall_status.value if suite_result.infrastructure_health else 'unknown'}",
            f"**Total Execution Time:** {suite_result.total_execution_time:.2f} seconds",
            "",
            "## Executive Summary",
            "",
            f"- **Total Tests:** {suite_result.total_tests}",
            f"- **Passed:** {suite_result.passed_tests} ({suite_result.success_rate:.1f}%)",
            f"- **Failed:** {suite_result.failed_tests}",
            f"- **Skipped:** {suite_result.skipped_tests}",
            f"- **Infrastructure Unavailable:** {suite_result.infrastructure_unavailable_tests}",
            f"- **Errors:** {suite_result.error_tests}",
            "",
        ]

        # Infrastructure health details
        if suite_result.infrastructure_health:
            health = suite_result.infrastructure_health
            report_lines.extend([
                "## Infrastructure Health Assessment",
                "",
                "| Service | Status | Response Time | Endpoint |",
                "|---------|--------|---------------|----------|",
            ])

            for service_type, result in health.results.items():
                report_lines.append(
                    f"| {service_type.value} | {result.status.value} | {result.response_time:.3f}s | {result.endpoint or 'N/A'} |"
                )

            report_lines.extend([
                "",
                f"**Healthy Services:** {[s.value for s in health.get_healthy_services()]}",
                f"**Degraded Services:** {[s.value for s in health.get_degraded_services()]}",
                f"**Unavailable Services:** {[s.value for s in health.get_unavailable_services()]}",
                "",
            ])

        # Test results by status
        report_lines.extend([
            "## Test Results by Status",
            "",
        ])

        for status in TestStatus:
            status_results = [r for r in suite_result.results if r.status == status]
            if status_results:
                report_lines.extend([
                    f"### {status.value.upper()} Tests ({len(status_results)})",
                    "",
                    "| Test Name | Execution Time | Retry Count | Error Message |",
                    "|-----------|----------------|-------------|---------------|",
                ])

                for result in status_results:
                    error_msg = result.error_message or "N/A"
                    if len(error_msg) > 100:
                        error_msg = error_msg[:97] + "..."

                    report_lines.append(
                        f"| {result.test_name} | {result.execution_time:.3f}s | {result.retry_count} | {error_msg} |"
                    )

                report_lines.append("")

        # Recommendations
        report_lines.extend([
            "## Recommendations",
            "",
        ])

        if suite_result.infrastructure_health:
            health = suite_result.infrastructure_health

            if health.overall_status == ConnectivityStatus.UNAVAILABLE:
                report_lines.extend([
                    "⚠️ **Critical Infrastructure Issues Detected**",
                    "",
                    "- Multiple critical services are unavailable",
                    "- Consider running tests in offline mode with local services",
                    "- Check VPC connector and Cloud SQL connectivity (Issue #1278)",
                    "",
                ])
            elif health.overall_status == ConnectivityStatus.DEGRADED:
                report_lines.extend([
                    "⚠️ **Infrastructure Degradation Detected**",
                    "",
                    "- Some services are running in fallback mode",
                    "- Monitor for service recovery",
                    "- Consider limiting test scope to critical paths only",
                    "",
                ])
            else:
                report_lines.extend([
                    "✅ **Infrastructure Health Good**",
                    "",
                    "- All services are available and responsive",
                    "- Full test suite execution recommended",
                    "",
                ])

        # Retry statistics
        total_retries = sum(r.retry_count for r in suite_result.results)
        if total_retries > 0:
            report_lines.extend([
                f"**Total Retry Attempts:** {total_retries}",
                f"**Tests Requiring Retries:** {sum(1 for r in suite_result.results if r.retry_count > 0)}",
                "",
            ])

        report_lines.extend([
            "---",
            "*Report generated by ResilientTestRunner for Issue #1278*"
        ])

        return "\n".join(report_lines)


# Convenience functions
async def run_tests_with_resilience(
    test_commands: List[str],
    test_names: Optional[List[str]] = None,
    env: Optional[IsolatedEnvironment] = None,
    quick_health_check: bool = False
) -> TestSuiteResult:
    """Run tests with resilience (convenience function)."""
    runner = ResilientTestRunner(env)
    return await runner.run_test_suite(test_commands, test_names, quick_health_check)


async def assess_test_infrastructure_health(env: Optional[IsolatedEnvironment] = None) -> InfrastructureHealth:
    """Assess test infrastructure health (convenience function)."""
    runner = ResilientTestRunner(env)
    return await runner.assess_infrastructure_health()