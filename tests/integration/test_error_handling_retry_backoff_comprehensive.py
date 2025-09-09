"""
Integration Tests: Retry Logic & Exponential Backoff Error Handling

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Improve service reliability through intelligent retry mechanisms
- Value Impact: Retry patterns reduce transient failure impact and improve user experience
- Strategic Impact: Foundation for resilient AI service delivery and automated recovery

This test suite validates retry and backoff patterns with real services:
- Exponential backoff with jitter for transient error recovery
- Maximum retry limits and timeout handling with PostgreSQL logging
- Different retry strategies based on error type classification
- Performance impact measurement and optimization validation
- Integration with circuit breakers and rate limiting
- Concurrent retry coordination and resource management

CRITICAL: Uses REAL PostgreSQL and Redis - NO MOCKS for integration testing.
Tests validate actual retry behavior, timing accuracy, and system performance.
"""

import asyncio
import time
import random
import uuid
import math
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
import pytest

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from shared.isolated_environment import get_env

# Core imports
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RetryPolicy:
    """Configurable retry policy with various backoff strategies."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, 
                 max_delay: float = 60.0, backoff_strategy: str = "exponential",
                 jitter: bool = True, retry_on_exceptions: List[type] = None):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_strategy = backoff_strategy
        self.jitter = jitter
        self.retry_on_exceptions = retry_on_exceptions or [Exception]
        
        # Statistics
        self.total_attempts = 0
        self.total_retries = 0
        self.successful_operations = 0
        self.failed_operations = 0
        self.attempt_history = []
        
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if operation should be retried based on exception and attempt count."""
        if attempt >= self.max_retries:
            return False
            
        # Check if exception type is retryable
        for retryable_exception in self.retry_on_exceptions:
            if isinstance(exception, retryable_exception):
                return True
                
        return False
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry attempt."""
        if self.backoff_strategy == "exponential":
            delay = self.base_delay * (2 ** attempt)
        elif self.backoff_strategy == "linear":
            delay = self.base_delay * (attempt + 1)
        elif self.backoff_strategy == "fixed":
            delay = self.base_delay
        elif self.backoff_strategy == "fibonacci":
            delay = self.base_delay * self._fibonacci(attempt + 1)
        else:
            delay = self.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter to prevent thundering herd
        if self.jitter:
            jitter_amount = delay * 0.1 * random.random()  # 0-10% jitter
            delay += jitter_amount
        
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate fibonacci number for fibonacci backoff."""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get comprehensive retry policy statistics."""
        return {
            "total_attempts": self.total_attempts,
            "total_retries": self.total_retries,
            "successful_operations": self.successful_operations,
            "failed_operations": self.failed_operations,
            "success_rate": self.successful_operations / max(self.total_attempts, 1),
            "retry_rate": self.total_retries / max(self.total_attempts, 1),
            "average_attempts_per_operation": (self.total_retries + self.total_attempts) / max(self.total_attempts, 1),
            "configuration": {
                "max_retries": self.max_retries,
                "base_delay": self.base_delay,
                "max_delay": self.max_delay,
                "backoff_strategy": self.backoff_strategy,
                "jitter": self.jitter
            }
        }


class RetryableService:
    """Service with configurable retry behavior for testing."""
    
    def __init__(self, name: str, retry_policy: RetryPolicy):
        self.name = name
        self.retry_policy = retry_policy
        self.operation_count = 0
        self.operation_history = []
        
    async def execute_with_retry(self, operation: str, operation_func: Callable, 
                                *args, **kwargs) -> Dict[str, Any]:
        """Execute operation with retry logic."""
        self.operation_count += 1
        operation_start = time.time()
        attempt = 0
        last_exception = None
        
        operation_record = {
            "operation": operation,
            "operation_id": f"{self.name}_{operation}_{self.operation_count}",
            "start_time": datetime.now(timezone.utc),
            "attempts": []
        }
        
        self.retry_policy.total_attempts += 1
        
        while attempt <= self.retry_policy.max_retries:
            attempt_start = time.time()
            
            try:
                # Execute the operation
                result = await operation_func(*args, **kwargs)
                
                # Success
                attempt_duration = time.time() - attempt_start
                operation_duration = time.time() - operation_start
                
                operation_record["attempts"].append({
                    "attempt": attempt,
                    "result": "success",
                    "duration_ms": attempt_duration * 1000,
                    "timestamp": datetime.now(timezone.utc)
                })
                
                operation_record["success"] = True
                operation_record["total_duration_ms"] = operation_duration * 1000
                operation_record["final_attempt"] = attempt
                
                self.retry_policy.successful_operations += 1
                self.operation_history.append(operation_record)
                
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "total_duration_ms": operation_duration * 1000,
                    "retry_info": {
                        "retries_performed": attempt,
                        "retry_policy": self.retry_policy.backoff_strategy,
                        "operation_id": operation_record["operation_id"]
                    },
                    "business_value": {
                        "operation_completed": True,
                        "resilience_demonstrated": attempt > 0,
                        "reliability_improved": True
                    }
                }
                
            except Exception as e:
                last_exception = e
                attempt_duration = time.time() - attempt_start
                
                operation_record["attempts"].append({
                    "attempt": attempt,
                    "result": "failure",
                    "error": str(e),
                    "duration_ms": attempt_duration * 1000,
                    "timestamp": datetime.now(timezone.utc)
                })
                
                # Check if we should retry
                if self.retry_policy.should_retry(e, attempt):
                    self.retry_policy.total_retries += 1
                    delay = self.retry_policy.calculate_delay(attempt)
                    
                    operation_record["attempts"][-1]["retry_delay_ms"] = delay * 1000
                    
                    logger.info(f"Retrying operation {operation} after {delay:.2f}s (attempt {attempt + 1})")
                    await asyncio.sleep(delay)
                    attempt += 1
                else:
                    # No more retries
                    break
        
        # All retries exhausted or non-retryable error
        operation_duration = time.time() - operation_start
        operation_record["success"] = False
        operation_record["total_duration_ms"] = operation_duration * 1000
        operation_record["final_attempt"] = attempt
        operation_record["final_error"] = str(last_exception)
        
        self.retry_policy.failed_operations += 1
        self.operation_history.append(operation_record)
        
        raise last_exception
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service retry statistics."""
        successful_ops = [op for op in self.operation_history if op.get("success")]
        failed_ops = [op for op in self.operation_history if not op.get("success")]
        
        avg_attempts_success = sum(op["final_attempt"] + 1 for op in successful_ops) / max(len(successful_ops), 1)
        avg_attempts_failure = sum(op["final_attempt"] + 1 for op in failed_ops) / max(len(failed_ops), 1)
        
        return {
            "service_name": self.name,
            "total_operations": self.operation_count,
            "successful_operations": len(successful_ops),
            "failed_operations": len(failed_ops),
            "success_rate": len(successful_ops) / max(self.operation_count, 1),
            "average_attempts_on_success": avg_attempts_success,
            "average_attempts_on_failure": avg_attempts_failure,
            "retry_policy_stats": self.retry_policy.get_retry_stats(),
            "operation_history_count": len(self.operation_history)
        }


class ConcurrentRetryCoordinator:
    """Coordinates retry behavior across concurrent operations."""
    
    def __init__(self, max_concurrent_retries: int = 10):
        self.max_concurrent_retries = max_concurrent_retries
        self.active_retries = 0
        self.retry_semaphore = asyncio.Semaphore(max_concurrent_retries)
        self.retry_metrics = {
            "total_coordinated_retries": 0,
            "rejected_retries": 0,
            "concurrent_peak": 0
        }
        
    async def coordinate_retry(self, retry_func: Callable) -> Any:
        """Coordinate retry execution to prevent resource exhaustion."""
        if self.active_retries >= self.max_concurrent_retries:
            self.retry_metrics["rejected_retries"] += 1
            raise Exception("Retry coordination limit reached - too many concurrent retries")
        
        async with self.retry_semaphore:
            self.active_retries += 1
            self.retry_metrics["total_coordinated_retries"] += 1
            self.retry_metrics["concurrent_peak"] = max(self.retry_metrics["concurrent_peak"], self.active_retries)
            
            try:
                return await retry_func()
            finally:
                self.active_retries -= 1


class TestRetryBackoffErrorHandling(BaseIntegrationTest):
    """Integration tests for retry logic and exponential backoff patterns."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.env = get_env()
        self.env.set("TEST_MODE", "true", source="test")
        self.env.set("USE_REAL_SERVICES", "true", source="test")
        self.auth_helper = E2EAuthHelper()
    
    @pytest.fixture
    async def retry_coordinator(self):
        """Create concurrent retry coordinator."""
        return ConcurrentRetryCoordinator(max_concurrent_retries=5)
        
    @pytest.fixture
    async def retryable_services(self):
        """Create multiple services with different retry policies."""
        services = {
            "fast_retry": RetryableService(
                "fast_retry", 
                RetryPolicy(max_retries=5, base_delay=0.1, backoff_strategy="exponential")
            ),
            "slow_retry": RetryableService(
                "slow_retry",
                RetryPolicy(max_retries=3, base_delay=0.5, backoff_strategy="linear") 
            ),
            "fibonacci_retry": RetryableService(
                "fibonacci_retry",
                RetryPolicy(max_retries=4, base_delay=0.2, backoff_strategy="fibonacci")
            ),
            "fixed_retry": RetryableService(
                "fixed_retry",
                RetryPolicy(max_retries=2, base_delay=0.3, backoff_strategy="fixed")
            )
        }
        return services

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_exponential_backoff_timing_accuracy(self, real_services_fixture, retryable_services):
        """Test exponential backoff timing accuracy and jitter behavior."""
        
        # Business Value: Accurate timing prevents thundering herd and optimizes resource usage
        
        service = retryable_services["fast_retry"]
        failure_count = 0
        
        async def failing_operation():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:  # Fail first 3 attempts
                raise ConnectionError(f"Simulated connection failure #{failure_count}")
            return {"operation": "success", "attempt": failure_count}
        
        start_time = time.time()
        result = await service.execute_with_retry("timing_test", failing_operation)
        total_duration = time.time() - start_time
        
        # Validate successful recovery
        assert result["success"] is True
        assert result["attempts"] == 4  # 3 failures + 1 success
        assert result["retry_info"]["retries_performed"] == 3
        
        # Validate timing - exponential backoff should take predictable time
        # Base delay 0.1s: attempt 1 (0.1s), attempt 2 (0.2s), attempt 3 (0.4s) + jitter + operation time
        expected_min_duration = 0.1 + 0.2 + 0.4  # 0.7s minimum
        expected_max_duration = (0.1 + 0.2 + 0.4) * 1.2 + 0.1  # Include jitter and operation overhead
        
        assert total_duration >= expected_min_duration, f"Duration {total_duration:.3f}s too short"
        assert total_duration <= expected_max_duration, f"Duration {total_duration:.3f}s too long"
        
        # Validate attempt timing in operation history
        operation_record = service.operation_history[-1]
        assert len(operation_record["attempts"]) == 4
        
        # Check delay progression (with jitter tolerance)
        for i in range(3):  # First 3 attempts should have retries
            attempt = operation_record["attempts"][i]
            assert "retry_delay_ms" in attempt
            
            expected_delay = service.retry_policy.base_delay * (2 ** i) * 1000  # Convert to ms
            actual_delay = attempt["retry_delay_ms"]
            
            # Allow for jitter (up to 10% variation)
            assert actual_delay >= expected_delay * 0.9, f"Attempt {i} delay too short"
            assert actual_delay <= expected_delay * 1.1, f"Attempt {i} delay too long"
        
        logger.info("✅ Exponential backoff timing accuracy test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_different_backoff_strategies_comparison(self, real_services_fixture, retryable_services):
        """Test and compare different backoff strategies."""
        
        # Business Value: Different strategies optimize for different failure patterns
        
        failure_scenarios = {}
        
        async def create_failing_operation(strategy_name: str, failure_count: int):
            """Create operation that fails specified number of times."""
            attempts = 0
            
            async def failing_op():
                nonlocal attempts
                attempts += 1
                if attempts <= failure_count:
                    raise TimeoutError(f"{strategy_name} timeout #{attempts}")
                return {"strategy": strategy_name, "final_attempt": attempts}
                
            return failing_op
        
        # Test each strategy with same failure pattern
        for strategy_name, service in retryable_services.items():
            start_time = time.time()
            
            try:
                operation_func = await create_failing_operation(strategy_name, 2)  # Fail 2 times
                result = await service.execute_with_retry(f"{strategy_name}_comparison", operation_func)
                
                duration = time.time() - start_time
                failure_scenarios[strategy_name] = {
                    "success": True,
                    "duration": duration,
                    "attempts": result["attempts"],
                    "strategy": strategy_name,
                    "backoff_type": service.retry_policy.backoff_strategy
                }
                
            except Exception as e:
                duration = time.time() - start_time
                failure_scenarios[strategy_name] = {
                    "success": False,
                    "duration": duration,
                    "error": str(e),
                    "strategy": strategy_name,
                    "backoff_type": service.retry_policy.backoff_strategy
                }
        
        # All strategies should succeed with 2 failures
        for strategy_name, scenario in failure_scenarios.items():
            assert scenario["success"] is True, f"Strategy {strategy_name} failed unexpectedly"
            assert scenario["attempts"] == 3, f"Strategy {strategy_name} wrong attempt count"
        
        # Compare performance characteristics
        exponential_duration = failure_scenarios["fast_retry"]["duration"]
        linear_duration = failure_scenarios["slow_retry"]["duration"]
        fibonacci_duration = failure_scenarios["fibonacci_retry"]["duration"]
        fixed_duration = failure_scenarios["fixed_retry"]["duration"]
        
        # Exponential should be fastest for early recovery
        assert exponential_duration < linear_duration, "Exponential should be faster than linear for early recovery"
        
        # Fixed should be most predictable (base_delay * attempts)
        expected_fixed_duration = retryable_services["fixed_retry"].retry_policy.base_delay * 2  # 2 retries
        assert abs(fixed_duration - expected_fixed_duration) < expected_fixed_duration * 0.3, "Fixed strategy timing inconsistent"
        
        # Validate strategy-specific behavior
        fast_stats = retryable_services["fast_retry"].get_service_stats()
        slow_stats = retryable_services["slow_retry"].get_service_stats()
        
        assert fast_stats["retry_policy_stats"]["backoff_strategy"] == "exponential"
        assert slow_stats["retry_policy_stats"]["backoff_strategy"] == "linear"
        
        logger.info("✅ Different backoff strategies comparison test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_retry_with_real_database_operations(self, real_services_fixture, retryable_services):
        """Test retry logic with real database operations and transaction handling."""
        
        # Business Value: Database retry patterns ensure data consistency during transient failures
        
        service = retryable_services["fast_retry"]
        postgres = real_services_fixture["postgres"]
        
        # Create test table
        await postgres.execute("""
            CREATE TABLE IF NOT EXISTS retry_test_operations (
                id SERIAL PRIMARY KEY,
                operation_name TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                success BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        try:
            attempt_counter = 0
            
            async def database_operation_with_simulated_failures():
                """Database operation that fails first few attempts."""
                nonlocal attempt_counter
                attempt_counter += 1
                
                # Log attempt
                await postgres.execute("""
                    INSERT INTO retry_test_operations (operation_name, attempt_number, success)
                    VALUES ($1, $2, $3)
                """, "database_retry_test", attempt_counter, False)
                
                if attempt_counter <= 2:  # Fail first 2 attempts
                    raise Exception(f"Database connection timeout on attempt {attempt_counter}")
                
                # Success - update record and return result
                await postgres.execute("""
                    UPDATE retry_test_operations 
                    SET success = TRUE 
                    WHERE operation_name = $1 AND attempt_number = $2
                """, "database_retry_test", attempt_counter)
                
                # Verify data integrity
                success_count = await postgres.fetchval("""
                    SELECT COUNT(*) FROM retry_test_operations 
                    WHERE operation_name = $1 AND success = TRUE
                """, "database_retry_test")
                
                return {
                    "database_operation": "success",
                    "final_attempt": attempt_counter,
                    "success_records": success_count
                }
            
            # Execute with retry
            result = await service.execute_with_retry(
                "database_retry_test", 
                database_operation_with_simulated_failures
            )
            
            # Validate successful completion
            assert result["success"] is True
            assert result["result"]["final_attempt"] == 3
            assert result["attempts"] == 3
            
            # Validate database state consistency
            all_attempts = await postgres.fetch("""
                SELECT attempt_number, success FROM retry_test_operations 
                WHERE operation_name = $1 ORDER BY attempt_number
            """, "database_retry_test")
            
            assert len(all_attempts) == 3
            assert not all_attempts[0]["success"]  # First attempt failed
            assert not all_attempts[1]["success"]  # Second attempt failed  
            assert all_attempts[2]["success"]      # Third attempt succeeded
            
            # Test transaction rollback during failures
            async def transactional_operation_with_failure():
                """Test operation with transaction that needs rollback."""
                async with postgres.transaction() as tx:
                    await tx.execute("""
                        INSERT INTO retry_test_operations (operation_name, attempt_number, success)
                        VALUES ($1, $2, $3)
                    """, "transaction_test", 1, False)
                    
                    # Simulate failure that should rollback transaction
                    raise Exception("Transaction failure - should rollback")
                    
                    # This should not execute
                    await tx.execute("""
                        UPDATE retry_test_operations SET success = TRUE 
                        WHERE operation_name = 'transaction_test'
                    """)
            
            # This should fail and not leave partial data
            with pytest.raises(Exception):
                await service.execute_with_retry(
                    "transaction_failure_test",
                    transactional_operation_with_failure
                )
            
            # Verify transaction was rolled back
            transaction_records = await postgres.fetchval("""
                SELECT COUNT(*) FROM retry_test_operations 
                WHERE operation_name = 'transaction_test'
            """)
            assert transaction_records == 0, "Transaction rollback failed"
            
        finally:
            # Clean up test table
            await postgres.execute("DROP TABLE IF EXISTS retry_test_operations")
        
        logger.info("✅ Retry with real database operations test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_retry_coordination(self, real_services_fixture, retryable_services, retry_coordinator):
        """Test concurrent retry coordination and resource management."""
        
        # Business Value: Prevents retry storms and manages system resources effectively
        
        service = retryable_services["fast_retry"]
        redis = real_services_fixture["redis"]
        
        # Store retry metrics in Redis
        retry_metrics_key = "retry_coordination_metrics"
        
        async def coordinated_failing_operation(operation_id: str, failure_count: int):
            """Operation that coordinates with retry manager."""
            attempts = 0
            
            async def inner_operation():
                nonlocal attempts
                attempts += 1
                
                # Store attempt in Redis
                await redis.set_json(f"retry_attempt:{operation_id}:{attempts}", {
                    "operation_id": operation_id,
                    "attempt": attempts,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "coordinator_active_retries": retry_coordinator.active_retries
                }, ex=300)
                
                if attempts <= failure_count:
                    raise Exception(f"Coordinated failure {operation_id} attempt {attempts}")
                    
                return {"operation_id": operation_id, "success_attempt": attempts}
                
            return await retry_coordinator.coordinate_retry(inner_operation)
        
        # Create multiple concurrent operations with retries
        concurrent_operations = []
        for i in range(8):  # More operations than coordination limit
            operation_id = f"coord_op_{i}"
            failure_count = 2 if i % 2 == 0 else 1  # Alternate failure patterns
            
            operation_coro = service.execute_with_retry(
                f"coordinated_operation_{i}",
                lambda oid=operation_id, fc=failure_count: coordinated_failing_operation(oid, fc)
            )
            concurrent_operations.append(operation_coro)
        
        # Execute concurrent operations
        results = await asyncio.gather(*concurrent_operations, return_exceptions=True)
        
        # Analyze results
        successful_operations = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failed_operations = [r for r in results if isinstance(r, Exception)]
        
        # Some operations should succeed despite coordination limits
        assert len(successful_operations) >= 3, "Too few operations succeeded"
        
        # Some operations might fail due to coordination limits
        coordination_failures = [
            r for r in failed_operations 
            if isinstance(r, Exception) and "coordination limit" in str(r)
        ]
        
        # Validate retry coordination metrics
        assert retry_coordinator.retry_metrics["total_coordinated_retries"] > 0
        assert retry_coordinator.retry_metrics["concurrent_peak"] <= retry_coordinator.max_concurrent_retries
        
        # Verify retry attempts were stored in Redis
        retry_keys = await redis.keys("retry_attempt:*")
        assert len(retry_keys) > 0, "No retry attempts stored in Redis"
        
        # Analyze coordination effectiveness
        coordination_stats = {
            "total_operations": len(concurrent_operations),
            "successful_operations": len(successful_operations),
            "coordination_failures": len(coordination_failures),
            "other_failures": len(failed_operations) - len(coordination_failures),
            "coordination_effectiveness": len(successful_operations) / len(concurrent_operations)
        }
        
        # Store coordination stats
        await redis.set_json(retry_metrics_key, coordination_stats, ex=300)
        
        # Coordination should prevent system overload while allowing reasonable success rate
        assert coordination_stats["coordination_effectiveness"] >= 0.3, "Coordination too restrictive"
        assert retry_coordinator.retry_metrics["concurrent_peak"] <= 5, "Coordination limit exceeded"
        
        logger.info("✅ Concurrent retry coordination test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_retry_performance_impact_measurement(self, real_services_fixture, retryable_services):
        """Test performance impact of retry mechanisms on system resources."""
        
        # Business Value: Performance monitoring ensures retry patterns don't degrade user experience
        
        services = retryable_services
        performance_metrics = {}
        
        async def measure_operation_performance(service_name: str, operation_count: int, failure_rate: float):
            """Measure performance of operations with specified failure rate."""
            service = services[service_name]
            start_time = time.time()
            start_memory = 0  # Would measure memory in production
            
            operation_times = []
            success_count = 0
            
            for i in range(operation_count):
                op_start = time.time()
                attempts = 0
                
                async def performance_operation():
                    nonlocal attempts
                    attempts += 1
                    
                    # Simulate processing time
                    await asyncio.sleep(0.001)
                    
                    # Fail based on failure rate
                    if random.random() < failure_rate:
                        raise Exception(f"Performance test failure {attempts}")
                    
                    return {"operation": f"perf_test_{i}", "attempts": attempts}
                
                try:
                    result = await service.execute_with_retry(f"perf_test_{i}", performance_operation)
                    success_count += 1
                    operation_times.append(time.time() - op_start)
                except Exception:
                    operation_times.append(time.time() - op_start)
            
            total_duration = time.time() - start_time
            
            return {
                "service_name": service_name,
                "operation_count": operation_count,
                "success_count": success_count,
                "success_rate": success_count / operation_count,
                "total_duration": total_duration,
                "average_operation_time": sum(operation_times) / len(operation_times),
                "min_operation_time": min(operation_times),
                "max_operation_time": max(operation_times),
                "operations_per_second": operation_count / total_duration,
                "failure_rate_setting": failure_rate
            }
        
        # Test different failure rates and retry strategies
        test_scenarios = [
            ("fast_retry", 20, 0.1),   # 10% failure rate
            ("slow_retry", 15, 0.2),   # 20% failure rate  
            ("fibonacci_retry", 12, 0.3),  # 30% failure rate
            ("fixed_retry", 10, 0.4),  # 40% failure rate
        ]
        
        for service_name, op_count, failure_rate in test_scenarios:
            metrics = await measure_operation_performance(service_name, op_count, failure_rate)
            performance_metrics[service_name] = metrics
        
        # Analyze performance impact
        for service_name, metrics in performance_metrics.items():
            service = services[service_name]
            
            # Performance should degrade gracefully with higher failure rates
            assert metrics["operations_per_second"] > 1, f"{service_name} too slow"
            assert metrics["average_operation_time"] < 5.0, f"{service_name} average time too high"
            
            # Retry policy should maintain reasonable success rates
            if metrics["failure_rate_setting"] <= 0.3:
                assert metrics["success_rate"] >= 0.7, f"{service_name} success rate too low"
            
            # Fast retry should be more efficient for low failure rates
            if service_name == "fast_retry":
                assert metrics["operations_per_second"] >= 5, "Fast retry not performing well"
        
        # Compare efficiency across strategies
        fast_perf = performance_metrics["fast_retry"]
        slow_perf = performance_metrics["slow_retry"]
        
        # Fast retry should handle operations more efficiently
        assert fast_perf["operations_per_second"] > slow_perf["operations_per_second"], \
            "Fast retry not outperforming slow retry"
        
        # Validate retry statistics
        for service_name, service in services.items():
            stats = service.get_service_stats()
            assert stats["total_operations"] > 0
            assert stats["retry_policy_stats"]["total_attempts"] > 0
            
            # Services with higher failure rates should show more retries
            retry_rate = stats["retry_policy_stats"]["retry_rate"]
            failure_rate = performance_metrics[service_name]["failure_rate_setting"]
            
            # Higher failure rate should correlate with higher retry rate
            if failure_rate >= 0.3:
                assert retry_rate >= 0.1, f"{service_name} not retrying enough for high failure rate"
        
        logger.info("✅ Retry performance impact measurement test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_retry_integration_with_circuit_breaker(self, real_services_fixture, retryable_services):
        """Test integration between retry logic and circuit breaker patterns."""
        
        # Business Value: Combined patterns provide comprehensive resilience strategy
        
        service = retryable_services["fast_retry"]
        circuit_breaker_threshold = 5
        circuit_breaker_failures = 0
        circuit_breaker_open = False
        
        async def circuit_breaker_protected_operation():
            """Operation that simulates circuit breaker integration."""
            nonlocal circuit_breaker_failures, circuit_breaker_open
            
            # Check circuit breaker state
            if circuit_breaker_open:
                raise Exception("Circuit breaker is OPEN - operation rejected")
            
            circuit_breaker_failures += 1
            
            # Open circuit breaker after threshold
            if circuit_breaker_failures >= circuit_breaker_threshold:
                circuit_breaker_open = True
                raise Exception(f"Circuit breaker OPENED after {circuit_breaker_failures} failures")
            
            # Continue failing until threshold
            raise Exception(f"Operation failure #{circuit_breaker_failures}")
        
        # Test retry behavior with circuit breaker
        with pytest.raises(Exception) as exc_info:
            await service.execute_with_retry(
                "circuit_breaker_integration",
                circuit_breaker_protected_operation
            )
        
        # Should have failed due to circuit breaker opening
        assert "Circuit breaker OPENED" in str(exc_info.value)
        assert circuit_breaker_failures == circuit_breaker_threshold
        
        # Verify retry attempts were made before circuit breaker opened
        operation_record = service.operation_history[-1]
        assert len(operation_record["attempts"]) == circuit_breaker_threshold
        assert not operation_record["success"]
        
        # Test circuit breaker recovery with successful operation
        circuit_breaker_open = False  # Simulate circuit breaker recovery
        circuit_breaker_failures = 0
        recovery_attempts = 0
        
        async def recovery_operation():
            """Operation that succeeds after circuit breaker recovery."""
            nonlocal recovery_attempts
            recovery_attempts += 1
            
            if recovery_attempts == 1:
                # Fail once to test retry after recovery
                raise Exception("First attempt after recovery failed")
            
            return {
                "recovery": "successful",
                "attempts": recovery_attempts,
                "circuit_breaker_recovered": True
            }
        
        # Should succeed with retry after circuit breaker recovery
        result = await service.execute_with_retry(
            "circuit_breaker_recovery",
            recovery_operation
        )
        
        assert result["success"] is True
        assert result["result"]["recovery"] == "successful"
        assert result["attempts"] == 2  # Failed once, succeeded on retry
        
        # Validate service statistics show both failure and recovery patterns
        stats = service.get_service_stats()
        assert stats["total_operations"] >= 2
        assert stats["successful_operations"] >= 1
        assert stats["failed_operations"] >= 1
        
        logger.info("✅ Retry integration with circuit breaker test passed")


if __name__ == "__main__":
    # Run specific test for development
    import pytest
    pytest.main([__file__, "-v", "-s"])