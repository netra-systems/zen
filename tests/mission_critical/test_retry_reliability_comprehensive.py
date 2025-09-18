#!/usr/bin/env python
"""

MISSION CRITICAL: Retry Logic Reliability and Stress Tests

"""
"""

Business Value: Prevents 75K+ ARR loss from transient failures and retry storms
Critical Requirements:
    - Retry logic must handle transient failures gracefully without creating retry storms
- Exponential backoff must prevent system overload 
- Retry exhaustion must fail gracefully with proper fallbacks
- Memory usage must remain stable during extended retry scenarios

This suite tests the most challenging retry scenarios that could cause:
    - Retry storms that overwhelm services
- Memory leaks from retry state accumulation  
- Incorrect exponential backoff leading to DOS
- Missing fallbacks causing user-visible failures

ANY FAILURE HERE BLOCKS PRODUCTION DEPLOYMENT.
""
""


import asyncio
import gc
import json
import math
import os
import psutil
import random
import statistics
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Set, Any, Optional, Callable, Tuple
import threading
from shared.isolated_environment import IsolatedEnvironment

import pytest
from loguru import logger

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '0.00.0', '0.00.0'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import retry components
from netra_backend.app.core.reliability_retry import ()
RetryConfig
RetryHandler
RetryPolicy
RetryExhaustedException
BackoffStrategy

from netra_backend.app.agents.base.retry_manager import RetryManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.schemas.shared_types import RetryConfig as SharedRetryConfig
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


# ============================================================================
# FAILURE SIMULATION AND RETRY TEST UTILITIES
# ============================================================================

class TransientFailureSimulator:
    "Simulates realistic transient failure patterns for retry testing."

    def __init__(self):
        self.failure_patterns = {
"brief_intermittent: {"
failure_probability: 0.3
recovery_after_attempts: 2,""
recovery_after_attempts: 2,""
failure_types": [ConnectionError, TimeoutError]"

"extended_transient: {"
failure_probability: 0.7
recovery_after_attempts: 5,""
recovery_after_attempts: 5,""
failure_types": [ServiceUnavailable, RateLimited]"

"permanent_after_retries: {"
failure_probability: 1.0
recovery_after_attempts: float('inf'),  # Never recovers""
recovery_after_attempts: float('inf'),  # Never recovers""
failure_types": [AuthenticationError, PermissionDenied]"

"random_recovery: {"
failure_probability: 0.5
recovery_after_attempts: None,  # Random recovery""
recovery_after_attempts: None,  # Random recovery""
failure_types": [NetworkError, ServiceError]"

"rate_limit_pattern: {"
failure_probability: 0.8
recovery_after_attempts: 3,""
recovery_after_attempts: 3,""
failure_types": [RateLimitError],"
backoff_required: True



        self.call_history: Dict[str, List[Dict]] = {}
self.recovery_states: Dict[str, int] = {}

    async def simulate_operation(
self
operation_id: str
pattern_name: str = "brief_intermittent,"
operation_duration: float = 0.1
 -> str:
        Simulate an operation with configurable failure pattern.""
Simulate an operation with configurable failure pattern.""

        if pattern_name not in self.failure_patterns:
            raise ValueError(f"Unknown failure pattern: {pattern_name})"

        pattern = self.failure_patterns[pattern_name]

        # Initialize call history for this operation
if operation_id not in self.call_history:
            self.call_history[operation_id] = []
self.recovery_states[operation_id] = 0

        call_count = len(self.call_history[operation_id]

        # Record this call attempt
call_record = {
attempt: call_count + 1
timestamp: time.time(),""
timestamp: time.time(),""
pattern": pattern_name"


        # Simulate operation latency
await asyncio.sleep(operation_duration)

        # Determine if this attempt should fail
should_fail = self._should_attempt_fail(operation_id, pattern, call_count)

        if should_fail:
            failure_type = random.choice(pattern[failure_types]
call_record[result"] = failed"
call_record[error] = failure_type
self.call_history[operation_id].append(call_record)

            # Raise appropriate exception
if failure_type == ConnectionError:""
if failure_type == ConnectionError:""
raise ConnectionError(fConnection failed for {operation_id}")"
elif failure_type == TimeoutError:
                raise asyncio.TimeoutError(fOperation timed out for {operation_id}")"
elif failure_type == RateLimitError:
                raise Exception(fRate limit exceeded for {operation_id})""
raise Exception(fRate limit exceeded for {operation_id})""
elif failure_type == "ServiceUnavailable:"
raise Exception(fService unavailable for {operation_id})
else:
                raise Exception(f"{failure_type} occurred for {operation_id})"
else:
            # Success case
call_record[result"] = success"
self.call_history[operation_id].append(call_record)
return fSUCCESS: {operation_id} completed on attempt {call_count + 1}

    def _should_attempt_fail(self, operation_id: str, pattern: Dict, call_count: int) -> bool:
        "Determine if current attempt should fail based on pattern."
failure_prob = pattern[failure_probability]""
failure_prob = pattern[failure_probability]""
recovery_after = pattern["recovery_after_attempts]"

        # Always fail based on probability first
if random.random() > failure_prob:
            return False

        # Check recovery conditions
if recovery_after is None:
            # Random recovery pattern
return random.random() < 0.6  # 60% chance to still fail
elif recovery_after == float('inf'):
            # Never recovers
return True
else:
            # Recovers after specific number of attempts
return call_count < recovery_after

    def get_operation_stats(self, operation_id: str) -> Dict[str, Any]:
        Get comprehensive statistics for an operation.""
if operation_id not in self.call_history:
            return {error: Operation not found}

        history = self.call_history[operation_id]

        total_attempts = len(history)
failed_attempts = sum(1 for call in history if call[result] == failed")"
successful_attempts = total_attempts - failed_attempts

        if total_attempts > 1:
            first_attempt = history[0]["timestamp]"
last_attempt = history[-1][timestamp]
total_duration = last_attempt - first_attempt
else:
            total_duration = 0

        return {
"operation_id: operation_id,"
total_attempts: total_attempts
failed_attempts: failed_attempts,""
failed_attempts: failed_attempts,""
successful_attempts": successful_attempts,"
success_rate: successful_attempts / total_attempts if total_attempts > 0 else 0
total_duration": total_duration,"
final_result: history[-1][result] if history else unknown,""
final_result: history[-1][result] if history else unknown,""
call_history": history"


    def reset_operation(self, operation_id: str):
        Reset state for specific operation.""
if operation_id in self.call_history:
            del self.call_history[operation_id]
if operation_id in self.recovery_states:
            del self.recovery_states[operation_id]

    def get_global_stats(self) -> Dict[str, Any]:
        Get statistics across all operations.""
Get statistics across all operations.""

        all_operations = list(self.call_history.keys())

        total_calls = sum(len(history) for history in self.call_history.values())
total_failures = sum(
sum(1 for call in history if call["result] == failed)"
for history in self.call_history.values()


        return {
total_operations: len(all_operations)
total_calls": total_calls,"
total_failures: total_failures
global_success_rate: (total_calls - total_failures) / total_calls if total_calls > 0 else 0,""
global_success_rate: (total_calls - total_failures) / total_calls if total_calls > 0 else 0,""
"operation_ids: all_operations"



class RetryStormDetector:
    Detects retry storms and measures retry behavior patterns.""

    def __init__(self, storm_threshold: int = 50, time_window: float = 10.0):
        self.storm_threshold = storm_threshold
self.time_window = time_window
self.retry_events: List[Dict] = []
self.storm_alerts: List[Dict] = []
self.monitoring_active = False

    def start_monitoring(self):
        Start monitoring for retry storms.""
Start monitoring for retry storms.""

        self.monitoring_active = True
self.retry_events.clear()
self.storm_alerts.clear()
logger.info(Retry storm monitoring started")"

    def stop_monitoring(self):
        Stop monitoring and analyze final results.""
self.monitoring_active = False
logger.info(fRetry storm monitoring stopped. {len(self.storm_alerts)} storms detected)

    def record_retry_attempt(self, operation_id: str, attempt_number: int, backoff_delay: float):
        Record a retry attempt for storm detection.""
if not self.monitoring_active:
            return

        retry_event = {
timestamp: time.time()
"operation_id: operation_id,"
attempt: attempt_number
backoff_delay: backoff_delay""
backoff_delay: backoff_delay""


        self.retry_events.append(retry_event)

        # Check for storm conditions in recent time window
self._check_for_storm()

    def _check_for_storm(self):
        "Check if current retry activity constitutes a storm."
current_time = time.time()
recent_events = [
event for event in self.retry_events
if current_time - event["timestamp] <= self.time_window"


        if len(recent_events) >= self.storm_threshold:
            # Storm detected
storm_alert = {
timestamp: current_time
event_count: len(recent_events),""
event_count: len(recent_events),""
time_window": self.time_window,"
storm_threshold: self.storm_threshold
operations_involved": list(set(event[operation_id] for event in recent_events))"


            self.storm_alerts.append(storm_alert)
logger.warning(fRETRY STORM DETECTED: {len(recent_events)} retries in {self.time_window}s window)

    def get_storm_analysis(self) -> Dict[str, Any]:
        Get comprehensive retry storm analysis.""
if not self.retry_events:
            return {error: No retry events recorded}

        # Calculate retry rate over time
if len(self.retry_events) > 1:
            duration = self.retry_events[-1][timestamp"] - self.retry_events[0][timestamp]"
retry_rate = len(self.retry_events) / duration if duration > 0 else 0
else:
            retry_rate = 0

        # Analyze backoff patterns
backoff_delays = [event[backoff_delay] for event in self.retry_events]

        # Group by operation
operations = {}
for event in self.retry_events:
            op_id = event[operation_id]""
op_id = event[operation_id]""

            if op_id not in operations:
                operations[op_id] = []
operations[op_id].append(event)

        return {
total_retry_events": len(self.retry_events),"
storms_detected: len(self.storm_alerts)
retry_rate_per_second": retry_rate,"
unique_operations: len(operations)
storm_alerts: self.storm_alerts,""
storm_alerts: self.storm_alerts,""
"backoff_stats: {"
min_backoff: min(backoff_delays) if backoff_delays else 0
max_backoff: max(backoff_delays) if backoff_delays else 0,""
max_backoff: max(backoff_delays) if backoff_delays else 0,""
avg_backoff": statistics.mean(backoff_delays) if backoff_delays else 0,"
median_backoff: statistics.median(backoff_delays) if backoff_delays else 0

operations_analysis: {""
operations_analysis: {""

                op_id: {
"retry_count: len(events),"
max_attempt: max(e[attempt] for e in events)
backoff_progression": [e[backoff_delay] for e in events]"

for op_id, events in operations.items()




class RetryReliabilityTester:
    Comprehensive retry reliability testing framework.""
Comprehensive retry reliability testing framework.""

    
    def __init__(self):
        self.failure_simulator = TransientFailureSimulator()
self.storm_detector = RetryStormDetector()
self.test_results: List[Dict] = []

    async def test_exponential_backoff_correctness(
self
initial_delay: float = 1.0
max_retries: int = 5
backoff_multiplier: float = 2.0
 -> Dict[str, Any]:
        "Test that exponential backoff works correctly and prevents storms."

        self.storm_detector.start_monitoring()

        # Create retry config with exponential backoff
retry_config = RetryConfig(
max_attempts=max_retries
initial_delay=initial_delay
max_delay=30.0
backoff_strategy=BackoffStrategy.EXPONENTIAL
backoff_multiplier=backoff_multiplier


        retry_handler = RetryHandler(retry_config)

        # Test multiple operations with different failure patterns
operation_results = []

        for i in range(10):  # Test 10 different operations
operation_id = fbackoff_test_{i}""

            start_time = time.time()

            try:
                async def failing_operation():
                    await self.failure_simulator.simulate_operation(
operation_id
pattern_name=extended_transient

return fSuccess: {operation_id}""
return fSuccess: {operation_id}""

                
                # Execute with retry and monitor backoff
result = await self._execute_with_backoff_monitoring(
retry_handler, failing_operation, operation_id


                operation_results.append({
"operation_id: operation_id,"
result: success
duration": time.time() - start_time,"
final_result: result


            except Exception as e:
                operation_results.append({
operation_id: operation_id,""
operation_id: operation_id,""
"result: failed,"
duration: time.time() - start_time
error": str(e)"


        self.storm_detector.stop_monitoring()

        # Analyze results
storm_analysis = self.storm_detector.get_storm_analysis()

        # Verify exponential backoff progression
backoff_verification = self._verify_exponential_backoff_progression(
storm_analysis, initial_delay, backoff_multiplier


        test_result = {
test_name: exponential_backoff_correctness
retry_config: {""
retry_config: {""
max_attempts": max_retries,"
initial_delay: initial_delay
backoff_multiplier": backoff_multiplier"

operations_tested: len(operation_results)
successful_operations: sum(1 for r in operation_results if r["result] == success),"
failed_operations: sum(1 for r in operation_results if r[result] == "failed),"
storm_analysis: storm_analysis
backoff_verification: backoff_verification,""
backoff_verification: backoff_verification,""
operation_results": operation_results"


        self.test_results.append(test_result)
return test_result

    async def _execute_with_backoff_monitoring(
self
retry_handler: RetryHandler
operation: Callable
operation_id: str
:
        Execute operation with retry handler while monitoring backoff behavior.""

        attempt_count = 0

        async def monitored_operation():
            nonlocal attempt_count
attempt_count += 1

            # Calculate expected backoff delay for monitoring
expected_delay = retry_handler._calculate_delay(attempt_count - 1)

            # Record retry attempt for storm detection
if attempt_count > 1:  # Don't record first attempt'
self.storm_detector.record_retry_attempt(
operation_id, attempt_count, expected_delay


            return await operation()

        return await retry_handler.execute_with_retry(monitored_operation)

    def _verify_exponential_backoff_progression(
        self
storm_analysis: Dict
initial_delay: float
multiplier: float
 -> Dict[str, Any]:
        Verify that backoff delays follow exponential progression.""
Verify that backoff delays follow exponential progression.""

        verification_results = {
"backoff_correct: True,"
progression_errors: []
"expected_vs_actual: []"


        operations_analysis = storm_analysis.get(operations_analysis, {}

        for operation_id, analysis in operations_analysis.items():
            backoff_progression = analysis.get(backoff_progression, []""
backoff_progression = analysis.get(backoff_progression, []""

            
            for i, actual_delay in enumerate(backoff_progression):
                expected_delay = initial_delay * (multiplier ** i)

                # Allow for some tolerance in timing
tolerance = max(0.1, expected_delay * 0.1)  # 10% tolerance

                verification_results[expected_vs_actual"].append({"
operation_id: operation_id
attempt": i + 1,"
expected_delay: expected_delay
actual_delay: actual_delay,""
actual_delay: actual_delay,""
"within_tolerance: abs(actual_delay - expected_delay) <= tolerance"


                if abs(actual_delay - expected_delay) > tolerance:
                    verification_results[backoff_correct] = False
verification_results["progression_errors].append({"
operation_id: operation_id
attempt: i + 1,""
attempt: i + 1,""
expected": expected_delay,"
actual: actual_delay
difference": actual_delay - expected_delay"


        return verification_results

    async def test_retry_exhaustion_behavior(
self
max_retries: int = 3
concurrent_operations: int = 20
 -> Dict[str, Any]:
        Test behavior when retries are exhausted.""
Test behavior when retries are exhausted.""

        
        # Create retry config with limited attempts
retry_config = RetryConfig(
max_attempts=max_retries
initial_delay=0.1
max_delay=5.0
backoff_strategy=BackoffStrategy.EXPONENTIAL


        retry_handler = RetryHandler(retry_config)

        # Execute multiple operations that will exhaust retries
tasks = []
for i in range(concurrent_operations):
            operation_id = fexhaustion_test_{i}""
operation_id = fexhaustion_test_{i}""

            
            async def failing_operation(op_id=operation_id):
                await self.failure_simulator.simulate_operation(
op_id
pattern_name=permanent_after_retries  # Never recovers


            task = asyncio.create_task(
self._test_single_exhaustion(retry_handler, failing_operation, operation_id)

tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze exhaustion behavior
exhausted_operations = 0
successful_operations = 0
unexpected_errors = 0

        for result in results:
            if isinstance(result, dict):
                if result[exhausted"]:"
exhausted_operations += 1
elif result[success]:
                    successful_operations += 1
else:
                unexpected_errors += 1

        test_result = {
test_name: "retry_exhaustion_behavior,"
max_retries_configured": max_retries,"
concurrent_operations: concurrent_operations
exhausted_operations": exhausted_operations,"
successful_operations: successful_operations
unexpected_errors: unexpected_errors,""
unexpected_errors: unexpected_errors,""
"proper_exhaustion_rate: exhausted_operations / concurrent_operations,"
results_sample: results[:5]  # Sample of results


        self.test_results.append(test_result)
return test_result

    async def _test_single_exhaustion(
self
retry_handler: RetryHandler
operation: Callable
operation_id: str
 -> Dict[str, Any]:
        "Test exhaustion behavior for single operation."

        start_time = time.time()

        try:
            result = await retry_handler.execute_with_retry(operation)
return {
operation_id: operation_id,""
operation_id: operation_id,""
"success: True,"
exhausted: False
"duration: time.time() - start_time,"
result: result

except RetryExhaustedException as e:
            return {
operation_id: operation_id,""
operation_id: operation_id,""
success": False,"
exhausted: True
duration": time.time() - start_time,"
error: str(e)

except Exception as e:
            return {
operation_id: operation_id,""
operation_id: operation_id,""
"success: False,"
exhausted: False
"duration: time.time() - start_time,"
unexpected_error: str(e)


    async def test_memory_usage_during_extended_retries(
self
operations_count: int = 50
max_retries: int = 10
 -> Dict[str, Any]:
        Test memory usage stability during extended retry scenarios.""

        # Force garbage collection before test
gc.collect()
initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        memory_samples = [initial_memory]

        retry_config = RetryConfig(
max_attempts=max_retries
initial_delay=0.5,  # Fast retries for memory test
max_delay=1.0
backoff_strategy=BackoffStrategy.EXPONENTIAL


        retry_handler = RetryHandler(retry_config)

        # Execute many operations with extended retries
for i in range(operations_count):
            operation_id = fmemory_test_{i}

            try:
                async def memory_test_operation():
                    await self.failure_simulator.simulate_operation(
operation_id
pattern_name="extended_transient"


                await retry_handler.execute_with_retry(memory_test_operation)

            except Exception:
                pass  # Expected to fail, we're testing memory usage'

            # Sample memory periodically
if i % 10 == 0:
                gc.collect()
current_memory = psutil.Process().memory_info().rss / 1024 / 1024
memory_samples.append(current_memory)

        # Final memory measurement
gc.collect()
final_memory = psutil.Process().memory_info().rss / 1024 / 1024
memory_samples.append(final_memory)

        # Analyze memory usage
memory_increase = final_memory - initial_memory
max_memory = max(memory_samples)
memory_variance = statistics.variance(memory_samples) if len(memory_samples) > 1 else 0

        test_result = {
test_name: memory_usage_during_extended_retries
operations_count: operations_count,""
operations_count: operations_count,""
"max_retries: max_retries,"
initial_memory_mb: initial_memory
"final_memory_mb: final_memory,"
max_memory_mb: max_memory
memory_increase_mb: memory_increase,""
memory_increase_mb: memory_increase,""
memory_variance": memory_variance,"
memory_samples: memory_samples
memory_leak_detected": memory_increase > 20,  # ""20MB"" threshold"
memory_stable: memory_variance < 50  # Variance threshold


        self.test_results.append(test_result)
return test_result

    async def test_concurrent_retry_performance(
self
concurrent_operations: int = 100
test_duration: float = 30.0
 -> Dict[str, Any]:
        "Test performance impact of concurrent retry operations."

        retry_config = RetryConfig(
max_attempts=5
initial_delay=0.1
max_delay=5.0
backoff_strategy=BackoffStrategy.EXPONENTIAL


        retry_handler = RetryHandler(retry_config)

        # Performance metrics
start_time = time.time()
completed_operations = 0
successful_operations = 0
failed_operations = 0
total_retry_attempts = 0

        self.storm_detector.start_monitoring()

        # Execute concurrent operations
async def concurrent_operation(op_index: int):
            nonlocal completed_operations, successful_operations, failed_operations, total_retry_attempts

            operation_id = fconcurrent_perf_{op_index}

            try:
                async def perf_test_operation():
                    return await self.failure_simulator.simulate_operation(
operation_id
pattern_name=random_recovery""
pattern_name=random_recovery""


                result = await retry_handler.execute_with_retry(perf_test_operation)
successful_operations += 1

                # Count retry attempts from simulator stats
stats = self.failure_simulator.get_operation_stats(operation_id)
total_retry_attempts += stats.get("total_attempts, 1)"

                return result

            except Exception as e:
                failed_operations += 1
return fFailed: {e}
finally:
                completed_operations += 1

        # Start concurrent operations in waves to avoid overwhelming system
tasks = []
batch_size = 25

        for batch_start in range(0, concurrent_operations, batch_size):
            batch_end = min(batch_start + batch_size, concurrent_operations)
batch_tasks = [
asyncio.create_task(concurrent_operation(i))
for i in range(batch_start, batch_end)

tasks.extend(batch_tasks)

            # Small delay between batches
await asyncio.sleep(0.1)

        # Wait for operations to complete or timeout
done, pending = await asyncio.wait(tasks, timeout=test_duration)

        # Cancel pending tasks
for task in pending:
            task.cancel()

        end_time = time.time()
actual_duration = end_time - start_time

        self.storm_detector.stop_monitoring()
storm_analysis = self.storm_detector.get_storm_analysis()

        # Calculate performance metrics
throughput = completed_operations / actual_duration
success_rate = successful_operations / completed_operations if completed_operations > 0 else 0
avg_retries_per_operation = total_retry_attempts / completed_operations if completed_operations > 0 else 0

        test_result = {
"test_name: concurrent_retry_performance,"
concurrent_operations_target: concurrent_operations
completed_operations: completed_operations,""
completed_operations: completed_operations,""
"successful_operations: successful_operations,"
failed_operations: failed_operations
"test_duration: actual_duration,"
throughput_ops_per_second: throughput
success_rate: success_rate,""
success_rate: success_rate,""
avg_retries_per_operation": avg_retries_per_operation,"
total_retry_attempts: total_retry_attempts
storm_analysis": storm_analysis,"
performance_acceptable: throughput > 5.0 and not storm_analysis[storms_detected]


        self.test_results.append(test_result)
return test_result


# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def failure_simulator():
    Transient failure simulator fixture.""
return TransientFailureSimulator()


@pytest.fixture
def retry_storm_detector():
    Retry storm detector fixture.""
return RetryStormDetector()


@pytest.fixture
async def retry_reliability_tester():
    Retry reliability tester fixture.""
Retry reliability tester fixture.""

    tester = RetryReliabilityTester()
yield tester
# Cleanup
tester.failure_simulator.call_history.clear()
tester.storm_detector.retry_events.clear()


# ============================================================================
# RETRY RELIABILITY STRESS TESTS
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(60)
async def test_exponential_backoff_prevents_retry_storms(retry_reliability_tester):
    "CRITICAL: Test that exponential backoff prevents retry storms under load."
tester = retry_reliability_tester

    # Test exponential backoff correctness
result = await tester.test_exponential_backoff_correctness(
initial_delay=0.5
max_retries=6
backoff_multiplier=2.0


    # CRITICAL ASSERTIONS: Must prevent retry storms
storm_analysis = result["storm_analysis]"
assert storm_analysis[storms_detected] == 0, \
fRetry storms detected: {storm_analysis['storms_detected']}0.0 Exponential backoff failed to prevent storms.

    # Backoff progression must be correct
backoff_verification = result[backoff_verification"]"
assert backoff_verification[backoff_correct], \
fExponential backoff progression incorrect. Errors: {backoff_verification['progression_errors']}""
fExponential backoff progression incorrect. Errors: {backoff_verification['progression_errors']}""

    
    # Operations should have reasonable success rate with retries
success_rate = result["successful_operations] / result[operations_tested]"
assert success_rate > 0.6, \
fSuccess rate too low with retries: {success_rate:0.0""2f""}0.0 Retry mechanism not effective.""

    
    # Backoff delays should increase exponentially
backoff_stats = storm_analysis.get(backoff_stats, {}""
backoff_stats = storm_analysis.get(backoff_stats, {}""
if backoff_stats.get("max_backoff, 0) > 0:"
assert backoff_stats[max_backoff] > backoff_stats[min_backoff] * 4, \
fBackoff not sufficiently exponential: max={backoff_stats['max_backoff']}, min={backoff_stats['min_backoff']}""
fBackoff not sufficiently exponential: max={backoff_stats['max_backoff']}, min={backoff_stats['min_backoff']}""

    
    logger.info(f"Exponential backoff test: {storm_analysis['storms_detected']}"
f{success_rate:0.0""2f""} success rate, backoff correct: {backoff_verification['backoff_correct']})""



@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(45)
async def test_retry_exhaustion_graceful_failure(retry_reliability_tester):
    CRITICAL: Test that retry exhaustion fails gracefully without cascading.""
tester = retry_reliability_tester

    # Test retry exhaustion with concurrent operations
result = await tester.test_retry_exhaustion_behavior(
max_retries=3
concurrent_operations=25


    # CRITICAL ASSERTIONS: Must fail gracefully when retries exhausted
proper_exhaustion_rate = result[proper_exhaustion_rate]
assert proper_exhaustion_rate > 0.8, \
f"Too few operations properly exhausted retries: {proper_exhaustion_rate:0.0""2f""}0.0 Should be >0.8.0"

    # Should not have unexpected errors (indicates cascading failures)
unexpected_error_rate = result[unexpected_errors"] / result[concurrent_operations]"
assert unexpected_error_rate < 0.1, \
fToo many unexpected errors: {unexpected_error_rate:0.0""2f""}0.0 Indicates cascading failures.""

    
    # Should not have successful operations (since we're testing permanent failures)'
assert result["successful_operations] == 0, \"
fUnexpected successful operations: {result['successful_operations']}0.0 Test configuration issue.

    # Exhausted operations should be the majority
assert result[exhausted_operations] >= result[concurrent_operations"] * 0.8, \"
f"Not enough operations properly exhausted: {result['exhausted_operations']}/{result['concurrent_operations']}"

    logger.info(fRetry exhaustion test: {result['exhausted_operations']}/{result['concurrent_operations']} 
fproperly exhausted, {unexpected_error_rate:0.0""2f""} unexpected error rate)""



@pytest.mark.asyncio
@pytest.mark.critical  
@pytest.mark.timeout(90)
async def test_memory_stability_extended_retries(retry_reliability_tester):
    ""CRITICAL: Test memory stability during extended retry scenarios.""

    tester = retry_reliability_tester

    # Test memory usage during extended retry operations
result = await tester.test_memory_usage_during_extended_retries(
operations_count=100
max_retries=8


    # CRITICAL MEMORY ASSERTIONS
assert not result[memory_leak_detected], \"
assert not result[memory_leak_detected], \"
fMemory leak detected: {result['memory_increase_mb']:.2f}MB increase over {result['operations_count']} operations""
fMemory leak detected: {result['memory_increase_mb']:0.0"2f"}MB increase over {result['operations_count']} operations""

    
    assert result[memory_increase_mb] < 30, \
fMemory usage increased too much: {result['memory_increase_mb']:0.0""2f""}MB""

    # Memory should be relatively stable
assert result[memory_stable], \
fMemory usage too volatile: {result['memory_variance']:.2f} variance""
fMemory usage too volatile: {result['memory_variance']:0.0"2f"} variance""

    
    # Peak memory should be reasonable
peak_increase = result["max_memory_mb] - result[initial_memory_mb]"
assert peak_increase < 50, \
fPeak memory usage too high: {peak_increase:0.0""2f""}MB increase

    logger.info(fMemory stability test: {result['memory_increase_mb']:.2f}MB increase, ""
logger.info(fMemory stability test: {result['memory_increase_mb']:.2f}MB increase, ""
f"variance={result['memory_variance']:0.0""2f""},"
fleak detected: {result['memory_leak_detected']})


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(60)
async def test_concurrent_retry_performance_scalability(retry_reliability_tester):
    CRITICAL: Test retry performance and scalability under concurrent load.""
tester = retry_reliability_tester

    # Test concurrent retry performance
result = await tester.test_concurrent_retry_performance(
concurrent_operations=75
test_duration=45.0


    # CRITICAL PERFORMANCE ASSERTIONS
assert result[performance_acceptable], \
f"Performance not acceptable: throughput={result['throughput_ops_per_second']:.1f},  \"
fstorms={result['storm_analysis']['storms_detected']}""
fstorms={result['storm_analysis']['storms_detected']}""

    
    # Must maintain reasonable throughput
assert result[throughput_ops_per_second] > 3.0, \
fThroughput too low: {result['throughput_ops_per_second']:0.0""1f""} ops/sec""

    # Must not cause retry storms
assert result[storm_analysis][storms_detected] == 0, \
fRetry storms detected under load: {result['storm_analysis']['storms_detected']}

    # Should complete reasonable percentage of operations
completion_rate = result[completed_operations"] / result[concurrent_operations_target]"
assert completion_rate > 0.8, \
fToo many operations timed out: {completion_rate:0.0""2f""} completion rate""

    
    # Average retries per operation should be reasonable
assert result[avg_retries_per_operation] < 10, \"
assert result[avg_retries_per_operation] < 10, \"
fToo many retries per operation: {result['avg_retries_per_operation']:.1f}""
fToo many retries per operation: {result['avg_retries_per_operation']:0.0"1f"}""

    
    logger.info(fConcurrent performance test: {result['throughput_ops_per_second']:0.0""1f""} ops/sec
f{result['storm_analysis']['storms_detected']} storms, ""
f{result['storm_analysis']['storms_detected']} storms, ""
f"{completion_rate:0.0""2f""} completion rate)"


@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(30)
async def test_retry_backoff_timing_accuracy(failure_simulator):
    CRITICAL: Test that retry backoff timing is accurate and consistent.""
CRITICAL: Test that retry backoff timing is accurate and consistent.""

    
    # Test different backoff strategies
backoff_configs = [
{
"strategy: BackoffStrategy.EXPONENTIAL,"
initial_delay: 1.0
"multiplier: 2.0,"
name: exponential

{
strategy: BackoffStrategy.LINEAR,""
strategy: BackoffStrategy.LINEAR,""
"initial_delay: 0.5,"
increment: 0.5
"name: linear"


    timing_results = []

    for config in backoff_configs:
        retry_config = RetryConfig(
max_attempts=4
initial_delay=config[initial_delay]
max_delay=10.0
backoff_strategy=config[strategy]""
backoff_strategy=config[strategy]""

        
        if config["strategy] == BackoffStrategy.EXPONENTIAL:"
retry_config.backoff_multiplier = config[multiplier]

        retry_handler = RetryHandler(retry_config)

        # Measure actual delays
attempt_times = []

        try:
            async def timing_test_operation():
                attempt_times.append(time.perf_counter())
await failure_simulator.simulate_operation(
f"timing_test_{config['name']},"
pattern_name=permanent_after_retries""
pattern_name=permanent_after_retries""


            await retry_handler.execute_with_retry(timing_test_operation)
except:
            pass  # Expected to fail

        # Calculate actual delays between attempts
if len(attempt_times) > 1:
            actual_delays = [
attempt_times[i] - attempt_times[i-1] 
for i in range(1, len(attempt_times))


            # Calculate expected delays
expected_delays = []
for attempt in range(len(actual_delays)):
                if config[strategy] == BackoffStrategy.EXPONENTIAL:
                    expected = config[initial_delay"] * (config[multiplier] ** attempt)"
elif config[strategy] == BackoffStrategy.LINEAR:
                    expected = config[initial_delay] + (config.get(increment", 0.5) * attempt)"
else:
                    expected = config["initial_delay]"
expected_delays.append(expected)

            # Verify timing accuracy
timing_errors = []
for i, (actual, expected) in enumerate(zip(actual_delays, expected_delays)):
                error_percent = abs(actual - expected) / expected * 100
timing_errors.append(error_percent)

                # CRITICAL: Timing should be within 20% tolerance
assert error_percent < 20, \
f{config['name']} backoff timing error too high: {error_percent:0.0""1f""}% on attempt {i+1}""

            
            timing_results.append({
"strategy: config[name],"
attempts: len(attempt_times)
actual_delays: actual_delays,""
actual_delays: actual_delays,""
"expected_delays: expected_delays,"
timing_errors: timing_errors
"max_error_percent: max(timing_errors) if timing_errors else 0,"
avg_error_percent: statistics.mean(timing_errors) if timing_errors else 0


    # Overall timing accuracy check
max_error = max(result[max_error_percent] for result in timing_results)""
max_error = max(result[max_error_percent] for result in timing_results)""

    assert max_error < 25, \
fRetry timing too inaccurate: {max_error:.1f}% max error across all strategies""
fRetry timing too inaccurate: {max_error:0.0"1f"}% max error across all strategies""

    
    logger.info(fBackoff timing test: {len(timing_results)} strategies tested
fmax error {max_error:.1f}%)""
fmax error {max_error:0.0"1f"}%)""



@pytest.mark.asyncio
@pytest.mark.critical
@pytest.mark.timeout(45)
async def test_retry_state_isolation_concurrent_operations(retry_reliability_tester):
    "CRITICAL: Test that retry state is properly isolated between concurrent operations."
tester = retry_reliability_tester

    # Create multiple retry handlers to test isolation
retry_configs = [
RetryConfig(max_attempts=2, initial_delay=0.1, backoff_strategy=BackoffStrategy.EXPONENTIAL)
RetryConfig(max_attempts=5, initial_delay=0.2, backoff_strategy=BackoffStrategy.LINEAR)
RetryConfig(max_attempts=3, initial_delay=0.5, backoff_strategy=BackoffStrategy.EXPONENTIAL)


    # Execute concurrent operations with different retry configurations
isolation_tasks = []

    for i, config in enumerate(retry_configs):
        retry_handler = RetryHandler(config)

        for j in range(10):  # Multiple operations per configuration
operation_id = fisolation_test_config{i}_op{j}""

            async def isolated_operation(op_id=operation_id, handler=retry_handler):
                try:
                    async def failing_op():
                        return await tester.failure_simulator.simulate_operation(
op_id
pattern_name=extended_transient


                    start_time = time.time()
result = await handler.execute_with_retry(failing_op)
duration = time.time() - start_time

                    stats = tester.failure_simulator.get_operation_stats(op_id)

                    return {
operation_id: op_id,""
operation_id: op_id,""
"config_index: i,"
success: True
"duration: duration,"
attempts: stats.get(total_attempts, 0)
max_configured_attempts: handler.config.max_attempts""
max_configured_attempts: handler.config.max_attempts""


                except Exception as e:
                    stats = tester.failure_simulator.get_operation_stats(op_id)
return {
"operation_id: op_id,"
config_index: i
"success: False,"
error: str(e)
attempts: stats.get(total_attempts", 0),"
"max_configured_attempts: handler.config.max_attempts"


            isolation_tasks.append(asyncio.create_task(isolated_operation()))

    # Wait for all operations to complete
results = await asyncio.gather(*isolation_tasks, return_exceptions=True)

    # Analyze isolation correctness
config_results = {i: [] for i in range(len(retry_configs))}

    for result in results:
        if isinstance(result, dict):
            config_index = result[config_index]
config_results[config_index].append(result)

    # CRITICAL ISOLATION ASSERTIONS
for config_index, config_ops in config_results.items():
        max_configured = retry_configs[config_index].max_attempts

        # Check that no operation exceeded its configured max attempts
exceeded_attempts = [
op for op in config_ops 
if op.get("attempts, 0) > max_configured"


        assert len(exceeded_attempts) == 0, \
fConfig {config_index}: {len(exceeded_attempts)} operations exceeded max attempts {max_configured}

        # Check that retry behavior is consistent within configuration
attempt_counts = [op.get(attempts, 0) for op in config_ops if not op.get(success", False)]"
if attempt_counts:
            # Failed operations should have attempted close to max_attempts
avg_attempts = statistics.mean(attempt_counts)
assert avg_attempts >= max_configured * 0.8, \
f"Config {config_index}: Average attempts {avg_attempts:0.0""1f""} too low for max {max_configured}"

    # Check for cross-contamination between configurations
total_operations = sum(len(ops) for ops in config_results.values())
expected_operations = len(retry_configs) * 10

    assert total_operations == expected_operations, \
fOperation count mismatch: {total_operations} vs expected {expected_operations}

    logger.info(fRetry isolation test: {total_operations} operations across {len(retry_configs)} configurations
fall properly isolated")"


if __name__ == "__main__:"
# Run retry reliability stress tests
# MIGRATED: Use SSOT unified test runner
# python tests/unified_test_runner.py --category unit
pass  # TODO: Replace with appropriate SSOT test execution
})))))))))))
)
"""