"""
Comprehensive failing tests for ParallelTask system with focus on retry_count functionality.

These tests are designed to fail initially to expose issues in the ParallelTask retry system.
They stress-test edge cases, timing, dependencies, and error handling.
"""

import asyncio
import pytest
import time
import threading
from concurrent.futures import TimeoutError
from shared.isolated_environment import IsolatedEnvironment

from dev_launcher.parallel_executor import (
    ParallelExecutor,
    ParallelTask,
    TaskResult,
    TaskType,
    create_dependency_task,
    create_io_task
)


class TestParallelExecutorComprehensive:
    """Comprehensive test suite for ParallelExecutor retry functionality."""
    
    def setup_method(self):
        """Setup for each test method."""
        self.executor = ParallelExecutor(max_cpu_workers=2, max_io_workers=4)
        self.call_count = {}
        self.exception_count = {}
        self.timing_data = {}
        
    def teardown_method(self):
        """Cleanup after each test method."""
        if hasattr(self, 'executor') and self.executor:
            self.executor.cleanup()
    
    def create_tracked_function(self, task_id: str, success_on_attempt: int = 1, 
                              exception_type: Exception = RuntimeError, 
                              return_value: str = "success"):
        """Create a function that tracks call counts and succeeds on specified attempt."""
        def tracked_func():
            if task_id not in self.call_count:
                self.call_count[task_id] = 0
            self.call_count[task_id] += 1
            
            if task_id not in self.timing_data:
                self.timing_data[task_id] = []
            self.timing_data[task_id].append(time.time())
            
            if self.call_count[task_id] < success_on_attempt:
                if task_id not in self.exception_count:
                    self.exception_count[task_id] = 0
                self.exception_count[task_id] += 1
                raise exception_type(f"Deliberate failure on attempt {self.call_count[task_id]}")
            
            return f"{return_value}_{self.call_count[task_id]}"
        
        return tracked_func

    def test_parallel_task_with_retry_count_success_on_second_attempt(self):
        """
        FAILING TEST: Task fails first time, succeeds on retry.
        Tests that retry_count is respected and success is reported correctly.
        """
        # Create task that fails once, then succeeds
        task_func = self.create_tracked_function("retry_task", success_on_attempt=2)
        
        task = ParallelTask(
            task_id="retry_task",
            func=task_func,
            retry_count=2,  # Allow 2 retries (3 total attempts)
            timeout=10.0
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: These assertions should expose retry issues
        result = results["retry_task"]
        assert result.success is True, f"Task should succeed on retry, got success={result.success}, error={result.error}"
        assert result.result == "success_2", f"Expected 'success_2', got '{result.result}'"
        assert self.call_count["retry_task"] == 2, f"Expected 2 calls, got {self.call_count['retry_task']}"
        assert self.exception_count["retry_task"] == 1, f"Expected 1 exception, got {self.exception_count.get('retry_task', 0)}"
        
        # Verify timing shows retry delay
        timing = self.timing_data["retry_task"]
        assert len(timing) == 2, f"Expected 2 timing entries, got {len(timing)}"
        delay = timing[1] - timing[0]
        assert delay >= 0.5, f"Expected retry delay >= 0.5s, got {delay:.3f}s"

    def test_parallel_task_max_retries_exhausted(self):
        """
        FAILING TEST: Task fails all attempts (retry_count=3).
        Verify final failure is reported correctly with proper error context.
        """
        # Create task that always fails
        task_func = self.create_tracked_function("always_fail", success_on_attempt=10, exception_type=ValueError)
        
        task = ParallelTask(
            task_id="always_fail", 
            func=task_func,
            retry_count=3,  # 4 total attempts
            timeout=15.0
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: These assertions should expose retry limit handling
        result = results["always_fail"]
        assert result.success is False, f"Task should fail after exhausting retries, got success={result.success}"
        assert isinstance(result.error, ValueError), f"Expected ValueError, got {type(result.error)}"
        assert self.call_count["always_fail"] == 4, f"Expected 4 attempts, got {self.call_count['always_fail']}"
        assert self.exception_count["always_fail"] == 4, f"Expected 4 exceptions, got {self.exception_count.get('always_fail', 0)}"
        
        # Verify all retry delays were applied
        timing = self.timing_data["always_fail"]
        assert len(timing) == 4, f"Expected 4 timing entries, got {len(timing)}"
        
        # Check progressive delays: 0.5, 1.0, 1.5 seconds
        for i in range(1, len(timing)):
            expected_min_delay = 0.5 * i
            actual_delay = timing[i] - timing[i-1]
            assert actual_delay >= expected_min_delay * 0.8, f"Retry {i} delay too short: {actual_delay:.3f}s < {expected_min_delay * 0.8:.3f}s"

    def test_parallel_task_retry_with_timeout(self):
        """
        FAILING TEST: Task times out then succeeds on retry.
        Test interaction between timeout and retry mechanisms.
        """
        def timeout_then_succeed():
            if "timeout_task" not in self.call_count:
                self.call_count["timeout_task"] = 0
            self.call_count["timeout_task"] += 1
            
            if self.call_count["timeout_task"] == 1:
                # First attempt: simulate long operation that would timeout
                time.sleep(2.0)  # This should cause timeout
                return "should_not_reach_here"
            else:
                # Subsequent attempts: succeed quickly
                return f"success_attempt_{self.call_count['timeout_task']}"
        
        task = ParallelTask(
            task_id="timeout_task",
            func=timeout_then_succeed,
            retry_count=2,
            timeout=1.0  # 1 second timeout
        )
        
        self.executor.add_task(task)
        
        # EXPECTED TO FAIL: Timeout handling with retries is complex
        start_time = time.time()
        results = self.executor.execute_all(timeout=30)  # Overall timeout
        execution_time = time.time() - start_time
        
        result = results["timeout_task"]
        
        # The first attempt should timeout, second should succeed
        assert result.success is True, f"Task should succeed on retry after timeout, got success={result.success}, error={result.error}"
        assert "success_attempt_2" in str(result.result), f"Expected success on attempt 2, got '{result.result}'"
        assert self.call_count["timeout_task"] >= 2, f"Expected at least 2 attempts, got {self.call_count['timeout_task']}"
        
        # Execution should be longer than timeout but not too long
        assert 2.0 <= execution_time <= 10.0, f"Execution time {execution_time:.2f}s not in expected range [2.0, 10.0]"

    def test_parallel_task_dependency_with_retry(self):
        """
        FAILING TEST: Task with dependencies that needs retry.
        Verify dependency resolution works correctly with retries.
        """
        # Create dependency task that succeeds immediately
        dep_func = self.create_tracked_function("dep_task", success_on_attempt=1, return_value="dep_success")
        dep_task = ParallelTask(task_id="dep_task", func=dep_func)
        
        # Create dependent task that fails first, succeeds on retry
        dependent_func = self.create_tracked_function("dependent_task", success_on_attempt=2, return_value="dependent_success")
        dependent_task = ParallelTask(
            task_id="dependent_task",
            func=dependent_func,
            dependencies=["dep_task"],
            retry_count=3
        )
        
        self.executor.add_task(dep_task)
        self.executor.add_task(dependent_task)
        
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Dependency + retry interaction is complex
        dep_result = results["dep_task"]
        dependent_result = results["dependent_task"]
        
        assert dep_result.success is True, f"Dependency should succeed, got success={dep_result.success}, error={dep_result.error}"
        assert dependent_result.success is True, f"Dependent task should succeed on retry, got success={dependent_result.success}, error={dependent_result.error}"
        
        assert self.call_count["dep_task"] == 1, f"Dependency should be called once, got {self.call_count['dep_task']}"
        assert self.call_count["dependent_task"] == 2, f"Dependent task should be called twice, got {self.call_count['dependent_task']}"
        
        # Verify execution order: dependency completes before dependent starts retrying
        dep_timing = self.timing_data["dep_task"][0]
        dependent_timings = self.timing_data["dependent_task"]
        assert dep_timing < dependent_timings[0], "Dependency should complete before dependent task starts"

    def test_parallel_executor_mixed_retry_tasks(self):
        """
        FAILING TEST: Mix of tasks with different retry_count values.
        Some succeed, some fail after retries.
        """
        tasks_config = [
            ("task_0_retries", 0, 1),  # No retries, succeeds immediately
            ("task_1_retry", 1, 2),    # 1 retry, succeeds on second attempt
            ("task_3_retries_fail", 3, 10),  # 3 retries, always fails
            ("task_2_retries_success", 2, 3)  # 2 retries, succeeds on third attempt
        ]
        
        for task_id, retry_count, success_attempt in tasks_config:
            func = self.create_tracked_function(task_id, success_attempt, return_value=f"result_{task_id}")
            task = ParallelTask(
                task_id=task_id,
                func=func,
                retry_count=retry_count
            )
            self.executor.add_task(task)
        
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Mixed retry scenarios are complex
        # task_0_retries: should succeed immediately
        assert results["task_0_retries"].success is True
        assert self.call_count["task_0_retries"] == 1
        
        # task_1_retry: should succeed on second attempt
        assert results["task_1_retry"].success is True
        assert self.call_count["task_1_retry"] == 2
        
        # task_3_retries_fail: should fail after 4 attempts
        assert results["task_3_retries_fail"].success is False
        assert self.call_count["task_3_retries_fail"] == 4
        
        # task_2_retries_success: should succeed on third attempt
        assert results["task_2_retries_success"].success is True
        assert self.call_count["task_2_retries_success"] == 3
        
        # Verify performance stats
        stats = self.executor.get_performance_stats()
        assert stats["total_tasks"] == 4
        assert stats["successful_tasks"] == 3
        assert stats["failed_tasks"] == 1
        assert stats["success_rate"] == 0.75

    def test_parallel_task_retry_delay_progression(self):
        """
        FAILING TEST: Verify delays increase between retries.
        Check timing of retry attempts follows expected progression.
        """
        task_func = self.create_tracked_function("delay_task", success_on_attempt=5)  # Force 4 retries
        
        task = ParallelTask(
            task_id="delay_task",
            func=task_func,
            retry_count=4  # 5 total attempts
        )
        
        self.executor.add_task(task)
        
        start_time = time.time()
        results = self.executor.execute_all()
        total_time = time.time() - start_time
        
        # EXPECTED TO FAIL: Retry delay progression is precise timing logic
        result = results["delay_task"]
        assert result.success is True, f"Task should eventually succeed, got success={result.success}, error={result.error}"
        assert self.call_count["delay_task"] == 5, f"Expected 5 attempts, got {self.call_count['delay_task']}"
        
        # Verify timing progression
        timings = self.timing_data["delay_task"]
        assert len(timings) == 5, f"Expected 5 timing entries, got {len(timings)}"
        
        expected_delays = [0.5, 1.0, 1.5, 2.0]  # Progressive delays: 0.5*attempt
        for i in range(1, len(timings)):
            actual_delay = timings[i] - timings[i-1]
            expected_delay = expected_delays[i-1]
            tolerance = 0.2  # Allow 200ms tolerance
            
            assert actual_delay >= expected_delay - tolerance, \
                f"Delay {i} too short: {actual_delay:.3f}s < {expected_delay - tolerance:.3f}s"
            assert actual_delay <= expected_delay + tolerance, \
                f"Delay {i} too long: {actual_delay:.3f}s > {expected_delay + tolerance:.3f}s"
        
        # Total time should be approximately sum of delays plus execution time
        min_expected_time = sum(expected_delays) * 0.8  # Allow some tolerance
        assert total_time >= min_expected_time, f"Total execution time {total_time:.3f}s < {min_expected_time:.3f}s"

    def test_parallel_task_retry_count_zero_fails_immediately(self):
        """
        FAILING TEST: retry_count=0 should fail without retry.
        Verify no retries are attempted when retry_count is 0.
        """
        task_func = self.create_tracked_function("no_retry_task", success_on_attempt=2, exception_type=ConnectionError)
        
        task = ParallelTask(
            task_id="no_retry_task",
            func=task_func,
            retry_count=0  # No retries allowed
        )
        
        self.executor.add_task(task)
        
        start_time = time.time()
        results = self.executor.execute_all()
        execution_time = time.time() - start_time
        
        # EXPECTED TO FAIL: Zero retry handling edge case
        result = results["no_retry_task"]
        assert result.success is False, f"Task should fail immediately with retry_count=0, got success={result.success}"
        assert isinstance(result.error, ConnectionError), f"Expected ConnectionError, got {type(result.error)}"
        assert self.call_count["no_retry_task"] == 1, f"Expected exactly 1 call, got {self.call_count['no_retry_task']}"
        assert "no_retry_task" not in self.exception_count or self.exception_count["no_retry_task"] == 1, \
            f"Expected 1 exception, got {self.exception_count.get('no_retry_task', 0)}"
        
        # Execution should be fast (no retry delays)
        assert execution_time < 1.0, f"Execution with no retries should be fast, got {execution_time:.3f}s"

    def test_parallel_executor_batch_with_retries(self):
        """
        FAILING TEST: Batch execution with some tasks needing retries.
        Verify batch completion waits for all retries to complete.
        """
        # Create batch of tasks with different retry needs
        batch_tasks = []
        for i in range(3):
            func = self.create_tracked_function(f"batch_task_{i}", success_on_attempt=i+1, return_value=f"batch_result_{i}")
            task = ParallelTask(
                task_id=f"batch_task_{i}",
                func=func,
                retry_count=max(0, i),  # 0, 1, 2 retries respectively
                priority=i  # Different priorities
            )
            batch_tasks.append(task)
            self.executor.add_task(task)
        
        start_time = time.time()
        results = self.executor.execute_all()
        execution_time = time.time() - start_time
        
        # EXPECTED TO FAIL: Batch coordination with retries is complex
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        
        for i in range(3):
            task_id = f"batch_task_{i}"
            result = results[task_id]
            
            assert result.success is True, f"Batch task {i} should succeed, got success={result.success}, error={result.error}"
            assert self.call_count[task_id] == i + 1, f"Task {i} should be called {i+1} times, got {self.call_count[task_id]}"
        
        # All tasks should complete roughly simultaneously (batch execution)
        # But total time should account for the longest retry sequence
        min_expected_time = 0.5 + 1.0  # Delays for task_2 (0.5s + 1.0s)
        assert execution_time >= min_expected_time * 0.8, f"Execution time {execution_time:.3f}s < {min_expected_time * 0.8:.3f}s"
        
        # Verify stats
        stats = self.executor.get_performance_stats()
        assert stats["total_tasks"] == 3
        assert stats["successful_tasks"] == 3
        assert stats["success_rate"] == 1.0

    def test_parallel_task_exception_types_in_retry(self):
        """
        FAILING TEST: Different exception types during retries.
        Verify all exceptions are handled and final error is preserved.
        """
        exception_sequence = [ValueError("First error"), ConnectionError("Second error"), TimeoutError("Third error")]
        
        def multi_exception_func():
            if "multi_exception" not in self.call_count:
                self.call_count["multi_exception"] = 0
            self.call_count["multi_exception"] += 1
            
            attempt = self.call_count["multi_exception"]
            if attempt <= len(exception_sequence):
                raise exception_sequence[attempt - 1]
            return "finally_succeeded"
        
        task = ParallelTask(
            task_id="multi_exception",
            func=multi_exception_func,
            retry_count=4  # Should succeed on 4th attempt
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Exception type handling in retry sequences
        result = results["multi_exception"]
        assert result.success is True, f"Task should succeed after multiple exception types, got success={result.success}, error={result.error}"
        assert result.result == "finally_succeeded", f"Expected 'finally_succeeded', got '{result.result}'"
        assert self.call_count["multi_exception"] == 4, f"Expected 4 attempts, got {self.call_count['multi_exception']}"
        
        # If task had failed, the final error should be the last exception type
        # This tests error preservation logic

    def test_parallel_executor_performance_with_retries(self):
        """
        FAILING TEST: Large number of tasks with retries.
        Verify performance and resource usage under load.
        """
        num_tasks = 20
        tasks = []
        
        # Create mix of tasks: some succeed immediately, some need retries
        for i in range(num_tasks):
            retry_count = i % 4  # 0, 1, 2, 3 retries cycling
            success_attempt = (i % 3) + 1  # 1, 2, 3 attempts cycling
            
            func = self.create_tracked_function(f"perf_task_{i}", success_attempt, return_value=f"result_{i}")
            task = ParallelTask(
                task_id=f"perf_task_{i}",
                func=func,
                retry_count=retry_count,
                task_type=TaskType.IO_BOUND if i % 2 == 0 else TaskType.CPU_BOUND,
                priority=i % 5  # Mix priorities 0-4
            )
            tasks.append(task)
            self.executor.add_task(task)
        
        start_time = time.time()
        results = self.executor.execute_all(timeout=60)  # 1 minute timeout
        execution_time = time.time() - start_time
        
        # EXPECTED TO FAIL: Performance characteristics under load
        assert len(results) == num_tasks, f"Expected {num_tasks} results, got {len(results)}"
        
        # All tasks should eventually succeed (given sufficient retries)
        successful_count = sum(1 for r in results.values() if r.success)
        success_rate = successful_count / num_tasks
        
        assert success_rate >= 0.9, f"Expected success rate >= 90%, got {success_rate:.2%}"
        
        # Performance bounds
        assert execution_time < 30.0, f"Execution too slow: {execution_time:.2f}s > 30.0s"
        
        # Verify call distribution
        total_calls = sum(self.call_count.values())
        avg_calls_per_task = total_calls / num_tasks
        assert 1.0 <= avg_calls_per_task <= 3.0, f"Average calls per task {avg_calls_per_task:.2f} not in expected range [1.0, 3.0]"
        
        # Resource usage check
        stats = self.executor.get_performance_stats()
        assert stats["total_tasks"] == num_tasks
        assert stats["average_duration"] > 0
        assert stats["cpu_workers"] >= 2
        assert stats["io_workers"] >= 4
        
        # Memory usage should be reasonable (indirect test through successful completion)
        assert len(self.executor.completed) == num_tasks
        assert len(self.executor.pending) == 0  # All tasks should be completed

    def test_parallel_task_concurrent_modifications_during_retry(self):
        """
        FAILING TEST: Test thread safety during retry operations.
        Verify that concurrent modifications don't corrupt retry state.
        """
        modification_count = 0
        
        def concurrent_modify_func():
            nonlocal modification_count
            modification_count += 1
            
            if "concurrent_task" not in self.call_count:
                self.call_count["concurrent_task"] = 0
            self.call_count["concurrent_task"] += 1
            
            # Simulate concurrent state modifications during retry
            if self.call_count["concurrent_task"] == 1:
                # First attempt: fail while modifying shared state
                time.sleep(0.1)  # Allow for race conditions
                raise RuntimeError(f"Concurrent failure {modification_count}")
            
            return f"success_after_concurrent_modification_{modification_count}"
        
        task = ParallelTask(
            task_id="concurrent_task",
            func=concurrent_modify_func,
            retry_count=2
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Thread safety issues with concurrent modifications
        result = results["concurrent_task"]
        assert result.success is True, f"Concurrent task should succeed on retry, got success={result.success}, error={result.error}"
        assert "success_after_concurrent_modification" in str(result.result), f"Expected concurrent success result, got '{result.result}'"
        assert self.call_count["concurrent_task"] == 2, f"Expected 2 attempts, got {self.call_count['concurrent_task']}"

    def test_parallel_task_memory_pressure_with_retries(self):
        """
        FAILING TEST: Test memory usage under retry pressure.
        Verify system handles memory constraints during retries.
        """
        large_data = []
        
        def memory_pressure_func():
            nonlocal large_data
            if "memory_task" not in self.call_count:
                self.call_count["memory_task"] = 0
            self.call_count["memory_task"] += 1
            
            # Allocate memory on each attempt
            chunk_size = 1024 * 1024  # 1MB chunks
            large_data.extend([b'x' * chunk_size] * 10)  # 10MB per attempt
            
            if self.call_count["memory_task"] < 3:
                raise MemoryError(f"Memory pressure on attempt {self.call_count['memory_task']}")
            
            # Clean up memory before success
            large_data.clear()
            return f"memory_success_{self.call_count['memory_task']}"
        
        task = ParallelTask(
            task_id="memory_task",
            func=memory_pressure_func,
            retry_count=3
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Memory management during retries
        result = results["memory_task"]
        assert result.success is True, f"Memory task should succeed after cleanup, got success={result.success}, error={result.error}"
        assert "memory_success_3" in str(result.result), f"Expected memory success result, got '{result.result}'"
        assert len(large_data) == 0, f"Memory should be cleaned up, still have {len(large_data)} chunks"

    def test_parallel_task_nested_exception_chains_in_retry(self):
        """
        FAILING TEST: Test nested exception chains during retries.
        Verify complex exception handling preserves context.
        """
        def nested_exception_func():
            if "nested_task" not in self.call_count:
                self.call_count["nested_task"] = 0
            self.call_count["nested_task"] += 1
            
            attempt = self.call_count["nested_task"]
            
            try:
                if attempt == 1:
                    raise ValueError("Original value error")
                elif attempt == 2:
                    try:
                        raise ConnectionError("Connection failed")
                    except ConnectionError as e:
                        raise RuntimeError("Wrapped runtime error") from e
                elif attempt == 3:
                    try:
                        try:
                            raise KeyError("Deep key error")
                        except KeyError as e:
                            raise IndexError("Intermediate index error") from e
                    except IndexError as e:
                        raise TypeError("Final type error") from e
                else:
                    return f"nested_success_{attempt}"
            except Exception as e:
                # Re-raise with additional context
                raise RuntimeError(f"Attempt {attempt} context") from e
        
        task = ParallelTask(
            task_id="nested_task",
            func=nested_exception_func,
            retry_count=4
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Complex exception chain handling
        result = results["nested_task"]
        assert result.success is True, f"Nested exception task should succeed, got success={result.success}, error={result.error}"
        assert "nested_success_4" in str(result.result), f"Expected nested success result, got '{result.result}'"
        assert self.call_count["nested_task"] == 4, f"Expected 4 attempts, got {self.call_count['nested_task']}"

    def test_parallel_task_retry_with_changing_environment(self):
        """
        FAILING TEST: Test retries with changing environment conditions.
        Verify system adapts to environment changes during retry sequence.
        """
        environment_state = {"condition": "bad", "attempt": 0}
        
        def environment_sensitive_func():
            if "env_task" not in self.call_count:
                self.call_count["env_task"] = 0
            self.call_count["env_task"] += 1
            
            environment_state["attempt"] = self.call_count["env_task"]
            
            # Environment improves after second attempt
            if self.call_count["env_task"] >= 3:
                environment_state["condition"] = "good"
            
            if environment_state["condition"] == "bad":
                raise EnvironmentError(f"Bad environment on attempt {self.call_count['env_task']}")
            
            return f"env_success_{self.call_count['env_task']}_condition_{environment_state['condition']}"
        
        task = ParallelTask(
            task_id="env_task",
            func=environment_sensitive_func,
            retry_count=3
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Environment adaptation during retries
        result = results["env_task"]
        assert result.success is True, f"Environment task should succeed when conditions improve, got success={result.success}, error={result.error}"
        assert "env_success_3_condition_good" in str(result.result), f"Expected environment success result, got '{result.result}'"
        assert environment_state["condition"] == "good", f"Expected environment to improve, got '{environment_state['condition']}'"
        assert self.call_count["env_task"] == 3, f"Expected 3 attempts, got {self.call_count['env_task']}"

    def test_parallel_task_retry_statistics_accuracy(self):
        """
        FAILING TEST: Test accuracy of retry statistics and metrics.
        Verify all retry attempts are properly tracked and reported.
        """
        statistics = {"total_attempts": 0, "retry_attempts": 0, "failures": 0}
        
        def statistics_tracking_func():
            if "stats_task" not in self.call_count:
                self.call_count["stats_task"] = 0
            self.call_count["stats_task"] += 1
            statistics["total_attempts"] += 1
            
            if self.call_count["stats_task"] > 1:
                statistics["retry_attempts"] += 1
            
            if self.call_count["stats_task"] <= 2:
                statistics["failures"] += 1
                raise AssertionError(f"Statistics failure {statistics['failures']}")
            
            return f"stats_success_total_{statistics['total_attempts']}_retries_{statistics['retry_attempts']}_failures_{statistics['failures']}"
        
        task = ParallelTask(
            task_id="stats_task",
            func=statistics_tracking_func,
            retry_count=3
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Statistics tracking precision
        result = results["stats_task"]
        assert result.success is True, f"Statistics task should succeed, got success={result.success}, error={result.error}"
        
        # Verify detailed statistics
        assert statistics["total_attempts"] == 3, f"Expected 3 total attempts, got {statistics['total_attempts']}"
        assert statistics["retry_attempts"] == 2, f"Expected 2 retry attempts, got {statistics['retry_attempts']}"
        assert statistics["failures"] == 2, f"Expected 2 failures, got {statistics['failures']}"
        
        expected_result = "stats_success_total_3_retries_2_failures_2"
        assert expected_result in str(result.result), f"Expected '{expected_result}' in result, got '{result.result}'"
        
        # Cross-verify with executor statistics
        exec_stats = self.executor.get_performance_stats()
        assert exec_stats["successful_tasks"] == 1
        assert exec_stats["failed_tasks"] == 0
        assert exec_stats["success_rate"] == 1.0

    def test_parallel_task_retry_with_resource_cleanup(self):
        """
        FAILING TEST: Test resource cleanup between retry attempts.
        Verify resources are properly cleaned up even on retry failures.
        """
        resource_state = {"files_created": 0, "connections_open": 0, "cleanup_called": 0}
        
        def resource_managing_func():
            if "resource_task" not in self.call_count:
                self.call_count["resource_task"] = 0
            self.call_count["resource_task"] += 1
            
            try:
                # Simulate resource allocation
                resource_state["files_created"] += 1
                resource_state["connections_open"] += 1
                
                if self.call_count["resource_task"] <= 2:
                    raise IOError(f"Resource failure on attempt {self.call_count['resource_task']}")
                
                return f"resource_success_{self.call_count['resource_task']}"
            
            finally:
                # Simulate cleanup (should happen even on failures)
                resource_state["cleanup_called"] += 1
                if resource_state["connections_open"] > 0:
                    resource_state["connections_open"] -= 1
        
        task = ParallelTask(
            task_id="resource_task",
            func=resource_managing_func,
            retry_count=3
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Resource cleanup during retry sequences
        result = results["resource_task"]
        assert result.success is True, f"Resource task should succeed, got success={result.success}, error={result.error}"
        assert "resource_success_3" in str(result.result), f"Expected resource success result, got '{result.result}'"
        
        # Verify resource cleanup
        assert resource_state["files_created"] == 3, f"Expected 3 files created (one per attempt), got {resource_state['files_created']}"
        assert resource_state["cleanup_called"] == 3, f"Expected cleanup called 3 times, got {resource_state['cleanup_called']}"
        assert resource_state["connections_open"] == 0, f"Expected all connections closed, got {resource_state['connections_open']} still open"

    def test_parallel_task_retry_with_dynamic_timeout_adjustment(self):
        """
        FAILING TEST: Test dynamic timeout adjustment during retries.
        Verify timeout handling adapts based on retry attempt number.
        """
        timing_data = []
        
        def dynamic_timeout_func():
            start_time = time.time()
            if "dynamic_timeout_task" not in self.call_count:
                self.call_count["dynamic_timeout_task"] = 0
            self.call_count["dynamic_timeout_task"] += 1
            
            attempt = self.call_count["dynamic_timeout_task"]
            
            # Each attempt takes progressively longer
            sleep_time = attempt * 0.8  # 0.8, 1.6, 2.4 seconds
            time.sleep(sleep_time)
            
            timing_data.append({
                "attempt": attempt,
                "start_time": start_time,
                "sleep_time": sleep_time,
                "end_time": time.time()
            })
            
            if attempt <= 2:
                raise TimeoutError(f"Timeout simulation on attempt {attempt}")
            
            return f"dynamic_success_attempt_{attempt}_slept_{sleep_time}"
        
        # Task timeout should accommodate longer retry attempts
        task = ParallelTask(
            task_id="dynamic_timeout_task",
            func=dynamic_timeout_func,
            retry_count=3,
            timeout=5.0  # Should be enough for final attempt
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Dynamic timeout handling in retries
        result = results["dynamic_timeout_task"]
        assert result.success is True, f"Dynamic timeout task should succeed, got success={result.success}, error={result.error}"
        assert "dynamic_success_attempt_3_slept_2.4" in str(result.result), f"Expected dynamic success result, got '{result.result}'"
        
        # Verify timing progression
        assert len(timing_data) == 3, f"Expected 3 timing entries, got {len(timing_data)}"
        
        for i, entry in enumerate(timing_data):
            expected_sleep = (i + 1) * 0.8
            actual_sleep = entry["sleep_time"]
            assert abs(actual_sleep - expected_sleep) < 0.1, f"Attempt {i+1} sleep time {actual_sleep} not close to expected {expected_sleep}"

    def test_parallel_task_cascade_retry_failure_recovery(self):
        """
        FAILING TEST: Test recovery from cascading retry failures.
        Verify system remains stable when multiple retry chains fail.
        """
        cascade_state = {"failure_cascade": 0, "recovery_attempts": 0}
        
        def cascade_failure_func():
            if "cascade_task" not in self.call_count:
                self.call_count["cascade_task"] = 0
            self.call_count["cascade_task"] += 1
            
            attempt = self.call_count["cascade_task"]
            cascade_state["recovery_attempts"] += 1
            
            # Simulate cascading failures that eventually stabilize
            if attempt == 1:
                cascade_state["failure_cascade"] = 3  # Initial cascade depth
                raise ConnectionError("Initial cascade failure")
            elif attempt <= cascade_state["failure_cascade"]:
                cascade_state["failure_cascade"] -= 1  # Cascade diminishes
                raise RuntimeError(f"Cascade level {cascade_state['failure_cascade']} failure")
            else:
                # Recovery after cascade exhaustion
                return f"cascade_recovery_after_{cascade_state['recovery_attempts']}_attempts"
        
        task = ParallelTask(
            task_id="cascade_task",
            func=cascade_failure_func,
            retry_count=5  # Enough to recover from cascade
        )
        
        self.executor.add_task(task)
        results = self.executor.execute_all()
        
        # EXPECTED TO FAIL: Cascading failure recovery
        result = results["cascade_task"]
        assert result.success is True, f"Cascade task should recover, got success={result.success}, error={result.error}"
        assert "cascade_recovery_after_4_attempts" in str(result.result), f"Expected cascade recovery result, got '{result.result}'"
        assert cascade_state["failure_cascade"] == 0, f"Expected cascade exhausted, got level {cascade_state['failure_cascade']}"
        assert cascade_state["recovery_attempts"] == 4, f"Expected 4 recovery attempts, got {cascade_state['recovery_attempts']}"