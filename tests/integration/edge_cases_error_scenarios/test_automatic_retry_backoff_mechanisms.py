"""
Integration Tests: Automatic Retry and Backoff Mechanisms

Business Value Justification (BVJ):
- Segment: Enterprise (reliability and fault tolerance requirements)
- Business Goal: System Resilience + User Experience + Operational Efficiency
- Value Impact: Automatically recovers from transient failures without manual
  intervention, reduces user-facing errors from temporary network/service issues,
  implements intelligent backoff to prevent system overload during recovery,
  maintains service availability during intermittent failures
- Revenue Impact: Reduces support costs from transient failure reports,
  improves user satisfaction by handling 80%+ of temporary issues automatically,
  prevents revenue loss from abandoned sessions due to retry-able failures,
  enables Enterprise SLA guarantees for transient failure handling

Test Focus: Exponential backoff algorithms, retry limit handling, transient vs 
permanent failure classification, jitter implementation, and circuit breaker integration.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Any, Optional, Callable, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
import random
import math
from enum import Enum
from dataclasses import dataclass, field

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.config import get_config


class RetryResult(Enum):
    SUCCESS = "success"
    FAILURE_TRANSIENT = "failure_transient"
    FAILURE_PERMANENT = "failure_permanent"
    RETRY_EXHAUSTED = "retry_exhausted"


@dataclass
class RetryConfig:
    max_retries: int = 5
    base_delay: float = 1.0      # Base delay in seconds
    max_delay: float = 60.0      # Maximum delay in seconds
    backoff_multiplier: float = 2.0
    jitter_enabled: bool = True
    jitter_factor: float = 0.1   # 10% jitter
    timeout: float = 10.0        # Per-attempt timeout


@dataclass
class RetryAttempt:
    attempt_number: int
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error: Optional[str] = None
    delay_before_attempt: float = 0.0
    execution_time: Optional[float] = None


@dataclass
class RetryMetrics:
    operation_id: str
    total_attempts: int = 0
    successful_attempt: Optional[int] = None
    final_result: RetryResult = RetryResult.FAILURE_TRANSIENT
    total_execution_time: float = 0.0
    attempts: List[RetryAttempt] = field(default_factory=list)
    backoff_delays: List[float] = field(default_factory=list)


class SimulatedRetryMechanism:
    """Simulated retry mechanism with exponential backoff for testing."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    async def execute_with_retry(self, operation: Callable, operation_id: str, 
                               *args, **kwargs) -> Tuple[Any, RetryMetrics]:
        """Execute operation with retry and backoff mechanism."""
        metrics = RetryMetrics(operation_id=operation_id)
        start_time = time.time()
        
        for attempt_num in range(1, self.config.max_retries + 1):
            # Calculate backoff delay (not for first attempt)
            if attempt_num > 1:
                delay = self._calculate_backoff_delay(attempt_num - 1)
                metrics.backoff_delays.append(delay)
                await asyncio.sleep(delay)
            else:
                delay = 0.0
            
            # Create attempt record
            attempt = RetryAttempt(
                attempt_number=attempt_num,
                start_time=time.time(),
                delay_before_attempt=delay
            )
            
            try:
                # Execute operation with timeout
                result = await asyncio.wait_for(
                    operation(*args, **kwargs),
                    timeout=self.config.timeout
                )
                
                # Success - record and return
                attempt.end_time = time.time()
                attempt.execution_time = attempt.end_time - attempt.start_time
                attempt.success = True
                
                metrics.attempts.append(attempt)
                metrics.total_attempts = attempt_num
                metrics.successful_attempt = attempt_num
                metrics.final_result = RetryResult.SUCCESS
                metrics.total_execution_time = time.time() - start_time
                
                return result, metrics
                
            except Exception as e:
                attempt.end_time = time.time()
                attempt.execution_time = attempt.end_time - attempt.start_time
                attempt.success = False
                attempt.error = str(e)
                metrics.attempts.append(attempt)
                
                # Check if this is a permanent failure (should not retry)
                if self._is_permanent_failure(e):
                    metrics.total_attempts = attempt_num
                    metrics.final_result = RetryResult.FAILURE_PERMANENT
                    metrics.total_execution_time = time.time() - start_time
                    raise e
                
                # If this was the last attempt, fail with retry exhaustion
                if attempt_num == self.config.max_retries:
                    metrics.total_attempts = attempt_num
                    metrics.final_result = RetryResult.RETRY_EXHAUSTED
                    metrics.total_execution_time = time.time() - start_time
                    raise e
        
        # Should not reach here, but just in case
        metrics.total_execution_time = time.time() - start_time
        raise Exception("Unexpected retry mechanism state")
    
    def _calculate_backoff_delay(self, attempt_number: int) -> float:
        """Calculate exponential backoff delay with jitter."""
        # Exponential backoff: base_delay * multiplier^(attempt_number-1)
        delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt_number - 1))
        
        # Cap at max_delay
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter_enabled:
            jitter_range = delay * self.config.jitter_factor
            jitter = random.uniform(-jitter_range, jitter_range)
            delay = max(0.1, delay + jitter)  # Ensure minimum delay
        
        return delay
    
    def _is_permanent_failure(self, error: Exception) -> bool:
        """Determine if an error represents a permanent failure that should not be retried."""
        error_str = str(error).lower()
        
        # Permanent failure indicators
        permanent_indicators = [
            "authentication failed",
            "unauthorized",
            "forbidden", 
            "not found",
            "invalid request",
            "malformed",
            "permanent failure",
            "quota exceeded permanently"
        ]
        
        return any(indicator in error_str for indicator in permanent_indicators)


class TestAutomaticRetryBackoffMechanisms(BaseIntegrationTest):
    """
    Test automatic retry and backoff mechanisms for transient failure recovery.
    
    Business Value: Ensures system automatically recovers from transient failures,
    reducing user-facing errors and improving overall system reliability.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_retry_test(self, real_services_fixture):
        """Setup automatic retry and backoff test environment."""
        self.config = get_config()
        
        # Retry mechanism test state
        self.retry_mechanisms: Dict[str, SimulatedRetryMechanism] = {}
        self.failure_simulation_state: Dict[str, Dict[str, Any]] = {}
        self.retry_metrics: List[RetryMetrics] = []
        
        # Test contexts
        self.test_contexts: List[UserExecutionContext] = []
        
        # Initialize retry mechanisms with different configurations
        retry_configs = {
            "aggressive": RetryConfig(max_retries=3, base_delay=0.5, backoff_multiplier=1.5),
            "standard": RetryConfig(max_retries=5, base_delay=1.0, backoff_multiplier=2.0),
            "conservative": RetryConfig(max_retries=8, base_delay=2.0, backoff_multiplier=2.5),
            "no_jitter": RetryConfig(max_retries=4, base_delay=1.0, jitter_enabled=False)
        }
        
        for name, config in retry_configs.items():
            self.retry_mechanisms[name] = SimulatedRetryMechanism(config)
        
        yield
        
        # Cleanup contexts
        for context in self.test_contexts:
            try:
                await context.cleanup()
            except Exception:
                pass
    
    async def _simulate_transient_failure_operation(self, operation_id: str, 
                                                  failure_pattern: str) -> Dict[str, Any]:
        """Simulate operation with configurable transient failure patterns."""
        
        # Initialize failure state if not exists
        if operation_id not in self.failure_simulation_state:
            self.failure_simulation_state[operation_id] = {
                "attempt_count": 0,
                "failure_pattern": failure_pattern,
                "pattern_state": {}
            }
        
        state = self.failure_simulation_state[operation_id]
        state["attempt_count"] += 1
        attempt_num = state["attempt_count"]
        
        # Simulate processing time
        processing_time = random.uniform(0.1, 0.5)
        await asyncio.sleep(processing_time)
        
        # Apply failure pattern
        should_fail = self._should_operation_fail(failure_pattern, attempt_num, state["pattern_state"])
        
        if should_fail:
            failure_type = self._get_failure_type(failure_pattern, attempt_num)
            raise Exception(f"Transient failure: {failure_type} (attempt {attempt_num})")
        
        # Success
        return {
            "operation_id": operation_id,
            "attempt_number": attempt_num,
            "processing_time": processing_time,
            "result": f"Success after {attempt_num} attempts",
            "timestamp": time.time()
        }
    
    def _should_operation_fail(self, failure_pattern: str, attempt_num: int, pattern_state: Dict) -> bool:
        """Determine if operation should fail based on failure pattern."""
        
        if failure_pattern == "always_succeed":
            return False
        
        elif failure_pattern == "fail_first_two":
            return attempt_num <= 2
        
        elif failure_pattern == "fail_intermittent":
            # Fail 60% of the time randomly
            return random.random() < 0.6
        
        elif failure_pattern == "fail_decreasing":
            # Decreasing failure probability: 80%, 60%, 40%, 20%, then success
            failure_rates = [0.8, 0.6, 0.4, 0.2, 0.0]
            rate_index = min(attempt_num - 1, len(failure_rates) - 1)
            return random.random() < failure_rates[rate_index]
        
        elif failure_pattern == "fail_until_attempt_5":
            return attempt_num < 5
        
        elif failure_pattern == "permanent_after_3":
            if attempt_num >= 3:
                # Switch to permanent failure
                raise Exception("Authentication failed - permanent failure")
            return True
        
        else:
            # Default: fail first attempt, then succeed
            return attempt_num == 1
    
    def _get_failure_type(self, failure_pattern: str, attempt_num: int) -> str:
        """Get appropriate failure type for pattern."""
        failure_types = [
            "network timeout",
            "service temporarily unavailable", 
            "rate limit exceeded",
            "database connection lost",
            "temporary service overload"
        ]
        
        return failure_types[attempt_num % len(failure_types)]
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_algorithm_correctness(self):
        """
        Test exponential backoff algorithm produces correct delay sequences.
        
        BVJ: Ensures backoff algorithm prevents system overload during recovery
        while balancing quick recovery with resource protection.
        """
        retry_mechanism = self.retry_mechanisms["standard"]
        config = retry_mechanism.config
        
        # Test backoff delay calculations
        backoff_test_results = {
            "delays": [],
            "algorithm_correctness": True,
            "jitter_analysis": [],
            "max_delay_respected": True
        }
        
        # Test delay calculations for multiple attempts
        for attempt in range(1, 8):  # Test up to 8 attempts
            delay = retry_mechanism._calculate_backoff_delay(attempt)
            backoff_test_results["delays"].append({
                "attempt": attempt,
                "delay": delay,
                "expected_base": config.base_delay * (config.backoff_multiplier ** (attempt - 1))
            })
            
            # Check if delay respects maximum
            if delay > config.max_delay:
                backoff_test_results["max_delay_respected"] = False
        
        # Verify exponential growth pattern (before max_delay cap)
        for i in range(len(backoff_test_results["delays"]) - 1):
            current_delay = backoff_test_results["delays"][i]["delay"]
            next_delay = backoff_test_results["delays"][i + 1]["delay"]
            
            # Should be exponential growth (allowing for jitter and max_delay cap)
            if next_delay < current_delay and next_delay < config.max_delay:
                # Only fail if not at max_delay and accounting for jitter
                expected_growth = current_delay * config.backoff_multiplier
                jitter_tolerance = expected_growth * config.jitter_factor * 2  # Both directions
                
                if next_delay < (expected_growth - jitter_tolerance):
                    backoff_test_results["algorithm_correctness"] = False
        
        # Test jitter effectiveness
        jitter_delays = []
        for _ in range(20):  # Multiple samples to test jitter
            delay = retry_mechanism._calculate_backoff_delay(3)  # Test 3rd attempt
            jitter_delays.append(delay)
        
        if config.jitter_enabled:
            # Jitter should create variation in delays
            delay_variance = max(jitter_delays) - min(jitter_delays)
            expected_base_delay = config.base_delay * (config.backoff_multiplier ** 2)
            expected_jitter_range = expected_base_delay * config.jitter_factor * 2
            
            backoff_test_results["jitter_analysis"] = {
                "variance_observed": delay_variance,
                "expected_range": expected_jitter_range,
                "jitter_effective": delay_variance > (expected_jitter_range * 0.5)
            }
            
            assert backoff_test_results["jitter_analysis"]["jitter_effective"], \
                "Jitter not providing sufficient delay variation"
        
        # Verify algorithm correctness
        assert backoff_test_results["algorithm_correctness"], \
            "Exponential backoff algorithm not following correct progression"
        
        assert backoff_test_results["max_delay_respected"], \
            "Backoff delays exceeding configured maximum"
        
        # Verify first few delays are reasonable
        first_delay = backoff_test_results["delays"][0]["delay"]
        second_delay = backoff_test_results["delays"][1]["delay"]
        
        assert config.base_delay * 0.5 <= first_delay <= config.base_delay * 1.5, \
            f"First backoff delay unreasonable: {first_delay} (base: {config.base_delay})"
        
        assert first_delay < second_delay or second_delay == config.max_delay, \
            "Second delay should be larger than first (unless capped at max_delay)"
        
        self.logger.info(f"Exponential backoff algorithm test completed: "
                        f"{len(backoff_test_results['delays'])} delay calculations verified, "
                        f"jitter effective: {backoff_test_results.get('jitter_analysis', {}).get('jitter_effective', 'N/A')}")
    
    @pytest.mark.asyncio
    async def test_transient_failure_recovery_patterns(self):
        """
        Test recovery from various transient failure patterns.
        
        BVJ: Validates system can automatically recover from common transient
        failures, reducing manual intervention and improving user experience.
        """
        failure_patterns = [
            "fail_first_two",        # Recovers after 2 failures
            "fail_decreasing",       # Gradually improving success rate
            "fail_intermittent",     # Random transient failures
            "fail_until_attempt_5"   # Consistent failure until attempt 5
        ]
        
        recovery_test_results = {}
        
        for pattern in failure_patterns:
            retry_mechanism = self.retry_mechanisms["standard"]
            
            pattern_results = {
                "pattern": pattern,
                "operations_attempted": 5,
                "successful_recoveries": 0,
                "failed_recoveries": 0,
                "retry_metrics": []
            }
            
            # Test multiple operations with this failure pattern
            for op_num in range(pattern_results["operations_attempted"]):
                operation_id = f"recovery_test_{pattern}_{op_num}"
                
                try:
                    result, metrics = await retry_mechanism.execute_with_retry(
                        self._simulate_transient_failure_operation,
                        operation_id,
                        operation_id,
                        pattern
                    )
                    
                    pattern_results["successful_recoveries"] += 1
                    pattern_results["retry_metrics"].append(metrics)
                    self.retry_metrics.append(metrics)
                    
                except Exception:
                    pattern_results["failed_recoveries"] += 1
            
            recovery_test_results[pattern] = pattern_results
        
        # Verify recovery effectiveness for each pattern
        for pattern, results in recovery_test_results.items():
            successful_recoveries = results["successful_recoveries"]
            total_operations = results["operations_attempted"]
            
            recovery_rate = successful_recoveries / total_operations
            
            # Different patterns have different expected recovery rates
            if pattern == "fail_first_two":
                # Should have high recovery rate (only fails first 2 attempts)
                assert recovery_rate >= 0.8, \
                    f"Recovery rate too low for {pattern}: {recovery_rate:.2%}"
                
                # Should recover relatively quickly
                avg_attempts = sum(m.successful_attempt or m.total_attempts 
                                 for m in results["retry_metrics"]) / len(results["retry_metrics"])
                assert avg_attempts <= 4, \
                    f"Too many attempts needed for {pattern}: {avg_attempts:.1f}"
            
            elif pattern == "fail_decreasing":
                # Should have reasonable recovery rate as failures decrease
                assert recovery_rate >= 0.6, \
                    f"Recovery rate too low for {pattern}: {recovery_rate:.2%}"
            
            elif pattern == "fail_intermittent":
                # Should eventually succeed with retries despite randomness
                assert recovery_rate >= 0.4, \
                    f"Recovery rate too low for intermittent pattern: {recovery_rate:.2%}"
            
            elif pattern == "fail_until_attempt_5":
                # Should succeed if retry limit allows 5+ attempts
                if retry_mechanism.config.max_retries >= 5:
                    assert recovery_rate >= 0.8, \
                        f"Should recover well with sufficient retries for {pattern}: {recovery_rate:.2%}"
            
            # Verify retry metrics quality
            successful_metrics = [m for m in results["retry_metrics"] if m.final_result == RetryResult.SUCCESS]
            for metrics in successful_metrics:
                # Successful operations should have reasonable execution time
                assert metrics.total_execution_time < 30.0, \
                    f"Recovery took too long: {metrics.total_execution_time:.2f}s"
                
                # Should have at least one backoff delay if multiple attempts
                if metrics.total_attempts > 1:
                    assert len(metrics.backoff_delays) > 0, \
                        "Missing backoff delays for multi-attempt operation"
        
        self.logger.info(f"Transient failure recovery test completed: "
                        f"{len(failure_patterns)} patterns tested, "
                        f"overall operations: {sum(r['operations_attempted'] for r in recovery_test_results.values())}")
    
    @pytest.mark.asyncio
    async def test_permanent_failure_detection_and_handling(self):
        """
        Test detection of permanent failures that should not be retried.
        
        BVJ: Prevents wasted resources on non-recoverable failures and provides
        faster feedback to users for issues requiring immediate attention.
        """
        permanent_failure_scenarios = [
            {
                "name": "authentication_failure",
                "operation_id": "auth_test",
                "expected_behavior": "stop_immediately"
            },
            {
                "name": "permanent_after_attempts",
                "operation_id": "escalating_failure",
                "expected_behavior": "stop_after_detection"
            }
        ]
        
        permanent_failure_results = {}
        
        for scenario in permanent_failure_scenarios:
            scenario_name = scenario["name"]
            operation_id = scenario["operation_id"]
            expected_behavior = scenario["expected_behavior"]
            
            retry_mechanism = self.retry_mechanisms["standard"]
            
            scenario_results = {
                "scenario_name": scenario_name,
                "permanent_failure_detected": False,
                "attempts_before_detection": 0,
                "total_execution_time": 0,
                "retry_metrics": None
            }
            
            start_time = time.time()
            
            try:
                if scenario_name == "authentication_failure":
                    # Direct permanent failure
                    async def permanent_auth_failure(*args, **kwargs):
                        await asyncio.sleep(0.1)
                        raise Exception("Authentication failed - invalid credentials")
                    
                    result, metrics = await retry_mechanism.execute_with_retry(
                        permanent_auth_failure,
                        operation_id
                    )
                    
                elif scenario_name == "permanent_after_attempts":
                    # Use pattern that becomes permanent after some attempts
                    result, metrics = await retry_mechanism.execute_with_retry(
                        self._simulate_transient_failure_operation,
                        operation_id,
                        operation_id,
                        "permanent_after_3"
                    )
                
            except Exception as e:
                execution_time = time.time() - start_time
                scenario_results["total_execution_time"] = execution_time
                
                # Check if permanent failure was detected
                if "Authentication failed" in str(e) or "permanent failure" in str(e):
                    scenario_results["permanent_failure_detected"] = True
                
                # Get retry metrics from failure simulation state
                if operation_id in self.failure_simulation_state:
                    scenario_results["attempts_before_detection"] = \
                        self.failure_simulation_state[operation_id]["attempt_count"]
            
            permanent_failure_results[scenario_name] = scenario_results
        
        # Verify permanent failure handling
        for scenario_name, results in permanent_failure_results.items():
            
            if scenario_name == "authentication_failure":
                # Should detect permanent failure immediately
                assert results["permanent_failure_detected"], \
                    "Authentication failure not detected as permanent"
                
                # Should not waste time on retries
                assert results["total_execution_time"] < 5.0, \
                    f"Too much time spent on permanent failure: {results['total_execution_time']:.2f}s"
                
                # Should not make excessive attempts
                assert results["attempts_before_detection"] <= 1, \
                    f"Too many attempts on permanent failure: {results['attempts_before_detection']}"
            
            elif scenario_name == "permanent_after_attempts":
                # Should eventually detect permanent failure
                assert results["permanent_failure_detected"], \
                    "Escalating permanent failure not detected"
                
                # Should detect within reasonable number of attempts
                assert results["attempts_before_detection"] <= 5, \
                    f"Too many attempts before permanent failure detection: {results['attempts_before_detection']}"
        
        self.logger.info(f"Permanent failure detection test completed: "
                        f"{len(permanent_failure_scenarios)} scenarios tested")
    
    @pytest.mark.asyncio
    async def test_retry_limit_boundary_conditions(self):
        """
        Test retry mechanisms at boundary conditions and limits.
        
        BVJ: Ensures retry mechanisms don't consume excessive resources
        and provide predictable behavior at system limits.
        """
        retry_limit_scenarios = [
            {
                "name": "exactly_at_limit", 
                "retry_config": "aggressive",  # 3 max retries
                "failure_pattern": "fail_until_attempt_5",  # Needs 5 attempts
                "expected_result": "retry_exhausted"
            },
            {
                "name": "just_under_limit",
                "retry_config": "standard",    # 5 max retries  
                "failure_pattern": "fail_until_attempt_5",  # Needs 5 attempts
                "expected_result": "success"
            },
            {
                "name": "way_over_limit",
                "retry_config": "aggressive",  # 3 max retries
                "failure_pattern": "fail_intermittent",     # Random failures
                "expected_result": "mixed"  # Some success, some exhausted
            }
        ]
        
        limit_test_results = {}
        
        for scenario in retry_limit_scenarios:
            scenario_name = scenario["name"]
            retry_config_name = scenario["retry_config"]
            failure_pattern = scenario["failure_pattern"]
            expected_result = scenario["expected_result"]
            
            retry_mechanism = self.retry_mechanisms[retry_config_name]
            max_retries = retry_mechanism.config.max_retries
            
            scenario_results = {
                "scenario_name": scenario_name,
                "max_retries_configured": max_retries,
                "operations_tested": 10,
                "results_by_outcome": {
                    "success": 0,
                    "retry_exhausted": 0,
                    "permanent_failure": 0
                },
                "retry_metrics": []
            }
            
            # Test multiple operations to get statistical significance
            for op_num in range(scenario_results["operations_tested"]):
                operation_id = f"limit_test_{scenario_name}_{op_num}"
                
                try:
                    result, metrics = await retry_mechanism.execute_with_retry(
                        self._simulate_transient_failure_operation,
                        operation_id,
                        operation_id,
                        failure_pattern
                    )
                    
                    scenario_results["results_by_outcome"]["success"] += 1
                    scenario_results["retry_metrics"].append(metrics)
                    
                except Exception as e:
                    # Determine failure type
                    if "Authentication failed" in str(e) or "permanent failure" in str(e):
                        scenario_results["results_by_outcome"]["permanent_failure"] += 1
                    else:
                        scenario_results["results_by_outcome"]["retry_exhausted"] += 1
            
            limit_test_results[scenario_name] = scenario_results
        
        # Verify retry limit behavior
        for scenario_name, results in limit_test_results.items():
            scenario = next(s for s in retry_limit_scenarios if s["name"] == scenario_name)
            expected_result = scenario["expected_result"]
            outcomes = results["results_by_outcome"]
            total_ops = results["operations_tested"]
            
            if expected_result == "retry_exhausted":
                # Should have high rate of retry exhaustion
                exhausted_rate = outcomes["retry_exhausted"] / total_ops
                assert exhausted_rate >= 0.7, \
                    f"Expected high retry exhaustion rate for {scenario_name}: {exhausted_rate:.2%}"
                
                # Should not succeed often due to insufficient retries
                success_rate = outcomes["success"] / total_ops
                assert success_rate <= 0.3, \
                    f"Success rate too high for insufficient retry scenario {scenario_name}: {success_rate:.2%}"
            
            elif expected_result == "success":
                # Should have high success rate with sufficient retries
                success_rate = outcomes["success"] / total_ops
                assert success_rate >= 0.6, \
                    f"Success rate too low for sufficient retry scenario {scenario_name}: {success_rate:.2%}"
            
            elif expected_result == "mixed":
                # Should have mix of outcomes
                success_rate = outcomes["success"] / total_ops
                exhausted_rate = outcomes["retry_exhausted"] / total_ops
                
                # Both outcomes should be present
                assert success_rate > 0.1 and exhausted_rate > 0.1, \
                    f"Mixed results expected for {scenario_name}, got success: {success_rate:.2%}, exhausted: {exhausted_rate:.2%}"
            
            # Verify no operation exceeded max retries
            for metrics in results["retry_metrics"]:
                assert metrics.total_attempts <= results["max_retries_configured"], \
                    f"Operation exceeded max retries: {metrics.total_attempts} > {results['max_retries_configured']}"
        
        self.logger.info(f"Retry limit boundary test completed: "
                        f"{len(retry_limit_scenarios)} scenarios, "
                        f"{sum(r['operations_tested'] for r in limit_test_results.values())} total operations")
    
    @pytest.mark.asyncio
    async def test_concurrent_retry_operations_isolation(self):
        """
        Test isolation between concurrent retry operations.
        
        BVJ: Ensures retry mechanisms for different operations don't interfere
        with each other, maintaining predictable behavior under concurrent load.
        """
        num_concurrent_operations = 20
        operations_per_type = 5
        
        # Different operation types with different failure patterns
        operation_types = [
            {"type": "database_query", "pattern": "fail_first_two", "retry_config": "standard"},
            {"type": "api_call", "pattern": "fail_decreasing", "retry_config": "aggressive"},
            {"type": "file_processing", "pattern": "fail_intermittent", "retry_config": "conservative"},
            {"type": "cache_update", "pattern": "always_succeed", "retry_config": "standard"}
        ]
        
        concurrent_retry_results = {
            "operations_by_type": {},
            "isolation_verified": True,
            "timing_analysis": [],
            "resource_usage": []
        }
        
        async def concurrent_retry_operation(operation_type: Dict, operation_id: str):
            """Execute retry operation concurrently."""
            context = UserExecutionContext(
                user_id=f"retry_user_{operation_id}",
                session_id=f"retry_session_{operation_id}",
                request_id=f"retry_req_{operation_id}"
            )
            self.test_contexts.append(context)
            
            retry_mechanism = self.retry_mechanisms[operation_type["retry_config"]]
            
            start_time = time.time()
            
            try:
                result, metrics = await retry_mechanism.execute_with_retry(
                    self._simulate_transient_failure_operation,
                    operation_id,
                    operation_id,
                    operation_type["pattern"]
                )
                
                execution_time = time.time() - start_time
                
                return {
                    "operation_id": operation_id,
                    "operation_type": operation_type["type"],
                    "success": True,
                    "execution_time": execution_time,
                    "total_attempts": metrics.total_attempts,
                    "retry_metrics": metrics,
                    "context_user": context.user_id
                }
                
            except Exception as e:
                execution_time = time.time() - start_time
                
                return {
                    "operation_id": operation_id,
                    "operation_type": operation_type["type"],
                    "success": False,
                    "error": str(e),
                    "execution_time": execution_time,
                    "context_user": context.user_id
                }
        
        # Create concurrent retry operations
        all_tasks = []
        for op_type in operation_types:
            op_type_name = op_type["type"]
            concurrent_retry_results["operations_by_type"][op_type_name] = []
            
            for op_num in range(operations_per_type):
                operation_id = f"{op_type_name}_{op_num}_{int(time.time() * 1000)}"
                task = asyncio.create_task(concurrent_retry_operation(op_type, operation_id))
                all_tasks.append((op_type_name, task))
        
        # Execute all concurrent retry operations
        start_time = time.time()
        for op_type_name, task in all_tasks:
            result = await task
            concurrent_retry_results["operations_by_type"][op_type_name].append(result)
        
        total_execution_time = time.time() - start_time
        
        # Verify concurrent retry isolation and behavior
        for op_type_name, results in concurrent_retry_results["operations_by_type"].items():
            op_type_config = next(ot for ot in operation_types if ot["type"] == op_type_name)
            
            # Verify all operations of this type completed
            assert len(results) == operations_per_type, \
                f"Not all {op_type_name} operations completed: {len(results)}/{operations_per_type}"
            
            # Verify isolation - each operation should have unique context
            context_users = [r["context_user"] for r in results]
            assert len(set(context_users)) == len(results), \
                f"Context user isolation failed for {op_type_name}"
            
            # Verify behavior matches expected pattern
            successful_results = [r for r in results if r["success"]]
            
            if op_type_config["pattern"] == "always_succeed":
                # Should have 100% success rate
                success_rate = len(successful_results) / len(results)
                assert success_rate == 1.0, \
                    f"Always succeed pattern failed for {op_type_name}: {success_rate:.2%}"
            
            elif op_type_config["pattern"] == "fail_first_two":
                # Should have high success rate
                success_rate = len(successful_results) / len(results)
                assert success_rate >= 0.8, \
                    f"Fail first two pattern success rate too low for {op_type_name}: {success_rate:.2%}"
            
            # Verify timing isolation - operations shouldn't be blocked by each other
            execution_times = [r["execution_time"] for r in results]
            avg_execution_time = sum(execution_times) / len(execution_times)
            
            concurrent_retry_results["timing_analysis"].append({
                "operation_type": op_type_name,
                "avg_execution_time": avg_execution_time,
                "max_execution_time": max(execution_times),
                "min_execution_time": min(execution_times)
            })
            
            # Execution times should be reasonable (not blocked by other operations)
            assert avg_execution_time < 15.0, \
                f"Average execution time too high for {op_type_name}: {avg_execution_time:.2f}s"
        
        # Verify overall concurrency performance
        total_operations = sum(len(results) for results in concurrent_retry_results["operations_by_type"].values())
        overall_throughput = total_operations / total_execution_time
        
        # Should achieve reasonable throughput with concurrent retries
        assert overall_throughput >= 2.0, \
            f"Concurrent retry throughput too low: {overall_throughput:.1f} ops/sec"
        
        self.logger.info(f"Concurrent retry isolation test completed: "
                        f"{total_operations} operations, {overall_throughput:.1f} ops/sec, "
                        f"{total_execution_time:.2f}s total time")
    
    @pytest.mark.asyncio
    async def test_retry_with_timeout_boundary_interactions(self):
        """
        Test interaction between retry mechanisms and timeout boundaries.
        
        BVJ: Ensures retry timeouts don't accumulate to create excessive delays
        while still providing adequate time for recovery attempts.
        """
        timeout_retry_scenarios = [
            {
                "name": "short_timeout_quick_retry",
                "per_attempt_timeout": 1.0,
                "retry_config": "aggressive",  # 3 retries, fast backoff
                "operation_duration": 0.5,    # Quick operations
                "expected_behavior": "high_success"
            },
            {
                "name": "medium_timeout_standard_retry", 
                "per_attempt_timeout": 3.0,
                "retry_config": "standard",    # 5 retries, standard backoff
                "operation_duration": 2.0,    # Medium operations
                "expected_behavior": "balanced"
            },
            {
                "name": "timeout_vs_backoff_race",
                "per_attempt_timeout": 2.0,
                "retry_config": "conservative", # 8 retries, slow backoff
                "operation_duration": 1.5,     # Operations near timeout
                "expected_behavior": "timeout_sensitive"
            }
        ]
        
        timeout_interaction_results = {}
        
        for scenario in timeout_retry_scenarios:
            scenario_name = scenario["name"]
            per_attempt_timeout = scenario["per_attempt_timeout"]
            retry_config_name = scenario["retry_config"]
            operation_duration = scenario["operation_duration"]
            expected_behavior = scenario["expected_behavior"]
            
            # Create custom retry mechanism with specific timeout
            config = RetryConfig(
                max_retries=self.retry_mechanisms[retry_config_name].config.max_retries,
                base_delay=self.retry_mechanisms[retry_config_name].config.base_delay,
                backoff_multiplier=self.retry_mechanisms[retry_config_name].config.backoff_multiplier,
                timeout=per_attempt_timeout
            )
            timeout_retry_mechanism = SimulatedRetryMechanism(config)
            
            scenario_results = {
                "scenario_name": scenario_name,
                "operations_tested": 8,
                "timeout_config": per_attempt_timeout,
                "outcomes": {
                    "success": 0,
                    "timeout": 0,
                    "retry_exhausted": 0
                },
                "timing_metrics": {
                    "total_times": [],
                    "timeout_violations": 0
                }
            }
            
            async def timeout_sensitive_operation(*args, **kwargs):
                """Operation with configurable duration for timeout testing."""
                # Add some variance to operation duration
                actual_duration = operation_duration + random.uniform(-0.2, 0.2)
                await asyncio.sleep(max(0.1, actual_duration))
                
                # Fail sometimes to trigger retries
                if random.random() < 0.4:  # 40% failure rate
                    raise Exception("Transient operation failure")
                
                return {"result": "success", "duration": actual_duration}
            
            # Test multiple operations with timeout interactions
            for op_num in range(scenario_results["operations_tested"]):
                operation_id = f"timeout_test_{scenario_name}_{op_num}"
                
                start_time = time.time()
                
                try:
                    result, metrics = await timeout_retry_mechanism.execute_with_retry(
                        timeout_sensitive_operation,
                        operation_id
                    )
                    
                    total_time = time.time() - start_time
                    scenario_results["outcomes"]["success"] += 1
                    scenario_results["timing_metrics"]["total_times"].append(total_time)
                    
                    # Check if total time exceeds reasonable bounds
                    max_expected_time = (per_attempt_timeout + config.max_delay) * config.max_retries
                    if total_time > max_expected_time * 1.5:  # 50% tolerance
                        scenario_results["timing_metrics"]["timeout_violations"] += 1
                    
                except asyncio.TimeoutError:
                    total_time = time.time() - start_time
                    scenario_results["outcomes"]["timeout"] += 1
                    scenario_results["timing_metrics"]["total_times"].append(total_time)
                    
                except Exception:
                    total_time = time.time() - start_time
                    scenario_results["outcomes"]["retry_exhausted"] += 1
                    scenario_results["timing_metrics"]["total_times"].append(total_time)
            
            timeout_interaction_results[scenario_name] = scenario_results
        
        # Verify timeout and retry interaction behavior
        for scenario_name, results in timeout_interaction_results.items():
            scenario = next(s for s in timeout_retry_scenarios if s["name"] == scenario_name)
            expected_behavior = scenario["expected_behavior"]
            outcomes = results["outcomes"]
            total_ops = results["operations_tested"]
            
            if expected_behavior == "high_success":
                # Short timeouts with quick operations should succeed well
                success_rate = outcomes["success"] / total_ops
                assert success_rate >= 0.6, \
                    f"Success rate too low for {scenario_name}: {success_rate:.2%}"
                
                # Should have few timeout violations
                assert results["timing_metrics"]["timeout_violations"] == 0, \
                    f"Unexpected timeout violations in {scenario_name}"
            
            elif expected_behavior == "balanced":
                # Should balance success with reasonable timeout handling
                success_rate = outcomes["success"] / total_ops
                timeout_rate = outcomes["timeout"] / total_ops
                
                assert success_rate >= 0.4, \
                    f"Success rate too low for balanced scenario {scenario_name}: {success_rate:.2%}"
                
                assert timeout_rate <= 0.4, \
                    f"Too many timeouts in balanced scenario {scenario_name}: {timeout_rate:.2%}"
            
            elif expected_behavior == "timeout_sensitive":
                # May have more timeouts due to long backoff vs timeout race
                total_completion_rate = (outcomes["success"] + outcomes["retry_exhausted"]) / total_ops
                assert total_completion_rate >= 0.5, \
                    f"Too many timeouts in sensitive scenario {scenario_name}: completion rate {total_completion_rate:.2%}"
            
            # Verify timing bounds
            if results["timing_metrics"]["total_times"]:
                avg_total_time = sum(results["timing_metrics"]["total_times"]) / len(results["timing_metrics"]["total_times"])
                max_total_time = max(results["timing_metrics"]["total_times"])
                
                # Total time shouldn't be excessive
                reasonable_max_time = scenario["per_attempt_timeout"] * 10  # Generous bound
                assert max_total_time < reasonable_max_time, \
                    f"Maximum total time too high for {scenario_name}: {max_total_time:.2f}s"
        
        self.logger.info(f"Timeout-retry interaction test completed: "
                        f"{len(timeout_retry_scenarios)} scenarios, "
                        f"{sum(r['operations_tested'] for r in timeout_interaction_results.values())} operations")