"""
Test error recovery and compensation patterns
Focus on retry strategies, circuit breaker recovery, and transaction rollback patterns
"""

import pytest
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.exceptions_service import ServiceError


class TestRetryStrategies:
    """Test various retry strategies and patterns"""

    @pytest.mark.asyncio
    async def test_exponential_backoff_strategy(self):
        """Test exponential backoff retry strategy"""
        attempts = []
        
        async def failing_operation():
            """Operation that fails for first few attempts"""
            attempt_num = len(attempts) + 1
            attempts.append(attempt_num)
            
            if attempt_num < 4:  # Fail first 3 attempts
                raise ConnectionError(f"Attempt {attempt_num} failed")
            
            return "Success"

        async def retry_with_exponential_backoff(operation, max_attempts=5, base_delay=0.01):
            """Retry with exponential backoff"""
            for attempt in range(1, max_attempts + 1):
                try:
                    return await operation()
                except Exception as e:
                    if attempt == max_attempts:
                        raise e
                    
                    # Exponential backoff with jitter
                    delay = base_delay * (2 ** (attempt - 1))
                    await asyncio.sleep(delay)

        # Test successful retry after failures
        result = await retry_with_exponential_backoff(failing_operation)
        assert result == "Success"
        assert len(attempts) == 4  # Failed 3 times, succeeded on 4th

    @pytest.mark.asyncio
    async def test_adaptive_retry_strategy(self):
        """Test adaptive retry strategy based on error types"""
        retry_count = 0
        
        async def adaptive_operation(error_type="transient"):
            """Operation with different error types"""
            nonlocal retry_count
            retry_count += 1
            
            if retry_count < 3:
                if error_type == "transient":
                    raise ConnectionError("Temporary network issue")
                elif error_type == "permanent":
                    raise ValueError("Invalid input data")
                elif error_type == "rate_limit":
                    raise ConnectionResetError("Rate limit exceeded")
            
            return "Success"

        def should_retry(exception, attempt_count):
            """Determine if we should retry based on exception type"""
            if attempt_count >= 5:
                return False
            
            # Different retry strategies for different errors
            if isinstance(exception, ConnectionError):
                return True  # Always retry connection errors
            elif isinstance(exception, ConnectionResetError):
                return attempt_count <= 2  # Limited retries for rate limits
            elif isinstance(exception, ValueError):
                return False  # Don't retry validation errors
            
            return False

        async def adaptive_retry(operation, error_type):
            """Adaptive retry based on error classification"""
            attempt = 0
            while attempt < 5:
                attempt += 1
                try:
                    return await operation(error_type)
                except Exception as e:
                    if not should_retry(e, attempt):
                        raise
                    await asyncio.sleep(0.01 * attempt)

        # Test transient error retry
        retry_count = 0
        result = await adaptive_retry(adaptive_operation, "transient")
        assert result == "Success"
        
        # Test permanent error - should not retry
        retry_count = 0
        with pytest.raises(ValueError):
            await adaptive_retry(adaptive_operation, "permanent")
        assert retry_count == 1  # Only one attempt

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_pattern(self):
        """Test circuit breaker recovery patterns"""
        failure_count = 0
        circuit_open = False
        
        async def monitored_operation():
            """Operation monitored by circuit breaker"""
            nonlocal failure_count, circuit_open
            
            if circuit_open:
                raise ServiceError("Circuit breaker is open")
            
            failure_count += 1
            if failure_count <= 3:
                raise ConnectionError("Service temporarily unavailable")
            
            # Service recovers after 3 failures
            failure_count = 0
            return "Service recovered"

        class SimpleCircuitBreaker:
            def __init__(self, failure_threshold=3, recovery_timeout=0.1):
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout
                self.failure_count = 0
                self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
                self.last_failure_time = None
            
            async def call(self, operation):
                """Execute operation with circuit breaker protection"""
                nonlocal circuit_open
                
                # Check if we should attempt recovery
                if self.state == "OPEN":
                    import time
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.state = "HALF_OPEN"
                        circuit_open = False
                    else:
                        circuit_open = True
                        raise ServiceError("Circuit breaker is open")
                
                try:
                    result = await operation()
                    # Success - close circuit
                    self.failure_count = 0
                    self.state = "CLOSED"
                    circuit_open = False
                    return result
                except Exception as e:
                    import time
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    
                    if self.failure_count >= self.failure_threshold:
                        self.state = "OPEN"
                        circuit_open = True
                    
                    raise

        breaker = SimpleCircuitBreaker(failure_threshold=3, recovery_timeout=0.05)
        
        # First 3 calls should fail and open circuit
        for i in range(3):
            with pytest.raises((ConnectionError, ServiceError)):
                await breaker.call(monitored_operation)
        
        # Circuit should be open now
        assert breaker.state == "OPEN"
        
        # Wait for recovery timeout
        await asyncio.sleep(0.06)
        
        # Next call should succeed (service has recovered)
        result = await breaker.call(monitored_operation)
        assert result == "Service recovered"
        assert breaker.state == "CLOSED"


class TestCompensationPatterns:
    """Test compensation and rollback patterns"""

    @pytest.mark.asyncio
    async def test_saga_compensation_pattern(self):
        """Test saga pattern with compensation actions"""
        operations_completed = []
        compensations_executed = []
        
        class SagaStep:
            def __init__(self, name, operation, compensation):
                self.name = name
                self.operation = operation
                self.compensation = compensation
        
        async def operation_a():
            operations_completed.append("A")
            return "A completed"
        
        async def operation_b():
            operations_completed.append("B")
            return "B completed"
        
        async def operation_c():
            operations_completed.append("C")
            # This operation fails
            raise ServiceError("Operation C failed")
        
        async def compensate_a():
            compensations_executed.append("A")
        
        async def compensate_b():
            compensations_executed.append("B")
        
        async def compensate_c():
            compensations_executed.append("C")
        
        steps = [
            SagaStep("A", operation_a, compensate_a),
            SagaStep("B", operation_b, compensate_b),
            SagaStep("C", operation_c, compensate_c)
        ]
        
        async def execute_saga(saga_steps):
            """Execute saga with compensation on failure"""
            completed_steps = []
            
            try:
                for step in saga_steps:
                    await step.operation()
                    completed_steps.append(step)
                
                return "Saga completed successfully"
            
            except Exception as e:
                # Execute compensations in reverse order
                for step in reversed(completed_steps):
                    try:
                        await step.compensation()
                    except Exception:
                        pass  # Log compensation failure but continue
                
                raise e

        # Execute saga - should fail at step C and compensate A and B
        with pytest.raises(ServiceError):
            await execute_saga(steps)
        
        # Verify operations and compensations
        assert operations_completed == ["A", "B", "C"]
        assert compensations_executed == ["B", "A"]  # Reversed order

    @pytest.mark.asyncio
    async def test_transaction_rollback_pattern(self):
        """Test transaction rollback patterns"""
        database_state = {"users": [], "orders": []}
        transaction_log = []
        
        class MockTransaction:
            def __init__(self):
                self.operations = []
                self.committed = False
            
            async def __aenter__(self):
                transaction_log.append("Transaction started")
                return self
            
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type is None and not self.committed:
                    await self.commit()
                else:
                    await self.rollback()
            
            async def add_user(self, user):
                self.operations.append(("add_user", user))
                database_state["users"].append(user)
            
            async def add_order(self, order):
                self.operations.append(("add_order", order))
                if order.get("invalid"):
                    raise ServiceError("Invalid order")
                database_state["orders"].append(order)
            
            async def commit(self):
                self.committed = True
                transaction_log.append("Transaction committed")
            
            async def rollback(self):
                # Reverse all operations
                for operation, data in reversed(self.operations):
                    if operation == "add_user" and data in database_state["users"]:
                        database_state["users"].remove(data)
                    elif operation == "add_order" and data in database_state["orders"]:
                        database_state["orders"].remove(data)
                
                transaction_log.append("Transaction rolled back")

        # Test successful transaction
        async with MockTransaction() as tx:
            await tx.add_user({"id": 1, "name": "Alice"})
            await tx.add_order({"id": 1, "user_id": 1, "item": "Book"})
        
        assert len(database_state["users"]) == 1
        assert len(database_state["orders"]) == 1
        assert "Transaction committed" in transaction_log
        
        # Reset for failure test
        database_state = {"users": [], "orders": []}
        transaction_log = []
        
        # Test failed transaction with rollback
        with pytest.raises(ServiceError):
            async with MockTransaction() as tx:
                await tx.add_user({"id": 2, "name": "Bob"})
                await tx.add_order({"id": 2, "invalid": True})  # This will fail
        
        # Verify rollback occurred
        assert len(database_state["users"]) == 0
        assert len(database_state["orders"]) == 0
        assert "Transaction rolled back" in transaction_log


class TestErrorBoundaryPatterns:
    """Test error boundary and isolation patterns"""

    @pytest.mark.asyncio
    async def test_error_isolation_pattern(self):
        """Test error isolation to prevent cascading failures"""
        service_states = {"A": "healthy", "B": "healthy", "C": "healthy"}
        
        async def service_call(service_name, should_fail=False):
            """Simulate service call"""
            if should_fail:
                service_states[service_name] = "failed"
                raise ServiceError(f"Service {service_name} failed")
            
            return f"Service {service_name} response"
        
        async def isolated_service_call(service_name, fallback_value=None):
            """Service call with error isolation"""
            try:
                return await service_call(service_name)
            except ServiceError:
                # Isolate error - don't let it propagate
                return fallback_value or f"Service {service_name} unavailable"
        
        async def coordinated_operation():
            """Operation coordinating multiple services with isolation"""
            results = {}
            
            # These calls are isolated - failure of one doesn't affect others
            results["A"] = await isolated_service_call("A")
            results["B"] = await isolated_service_call("B", "Service B fallback")
            results["C"] = await isolated_service_call("C")
            
            return results

        # Test with service B failing - simulate by directly testing the isolation pattern
        async def failing_service_call(service_name, should_fail=False):
            """Mock service call that fails for service B"""
            if service_name == "B":
                raise ServiceError(f"Service {service_name} failed")
            return f"Service {service_name} response"
        
        async def isolated_service_call_test(service_name, fallback_value=None):
            """Service call with error isolation for testing"""
            try:
                return await failing_service_call(service_name)
            except ServiceError:
                # Isolate error - don't let it propagate
                return fallback_value or f"Service {service_name} unavailable"
        
        # Operation should complete even with B failing
        results = {}
        results["A"] = await isolated_service_call_test("A")
        results["B"] = await isolated_service_call_test("B", "Service B fallback")
        results["C"] = await isolated_service_call_test("C")
        
        # Verify isolation worked
        assert "Service A response" in results["A"]
        assert results["B"] == "Service B fallback"
        assert "Service C response" in results["C"]

    @pytest.mark.asyncio
    async def test_graceful_degradation_pattern(self):
        """Test graceful degradation under error conditions"""
        cache_available = True
        db_available = True
        
        async def get_data_from_cache(key):
            """Get data from cache"""
            if not cache_available:
                raise ServiceError("Cache unavailable")
            return {"data": f"cached_{key}", "source": "cache"}
        
        async def get_data_from_db(key):
            """Get data from database"""
            if not db_available:
                raise ServiceError("Database unavailable")
            await asyncio.sleep(0.01)  # DB is slower
            return {"data": f"db_{key}", "source": "database"}
        
        async def get_static_fallback(key):
            """Static fallback data"""
            return {"data": f"static_{key}", "source": "static"}
        
        async def get_data_with_degradation(key):
            """Get data with graceful degradation"""
            # Try cache first (fastest)
            try:
                return await get_data_from_cache(key)
            except ServiceError:
                pass
            
            # Fallback to database
            try:
                return await get_data_from_db(key)
            except ServiceError:
                pass
            
            # Final fallback to static data
            return await get_static_fallback(key)

        # Test normal operation (cache available)
        result = await get_data_with_degradation("test_key")
        assert result["source"] == "cache"
        assert "cached_test_key" in result["data"]
        
        # Test cache failure - should use DB
        cache_available = False
        result = await get_data_with_degradation("test_key")
        assert result["source"] == "database"
        assert "db_test_key" in result["data"]
        
        # Test both cache and DB failure - should use static fallback
        db_available = False
        result = await get_data_with_degradation("test_key")
        assert result["source"] == "static"
        assert "static_test_key" in result["data"]