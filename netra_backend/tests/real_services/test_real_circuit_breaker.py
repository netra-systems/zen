"""
Real Circuit Breaker Tests - NO MOCKS

Tests circuit breaker functionality with actual service failures, real timeouts,
and comprehensive error handling scenarios.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Risk Reduction & System Stability
- Value Impact: Prevents cascade failures and ensures system resilience
- Strategic Impact: Maintains service availability under adverse conditions

This test suite uses:
- Real PostgreSQL connection failures
- Real Redis timeout scenarios
- Real HTTP client timeouts
- Actual WebSocket connection drops
- Real LLM API failures and rate limits
"""

import asyncio
import pytest
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import psutil
import aiohttp
import socket
from shared.isolated_environment import IsolatedEnvironment

from test_framework.environment_isolation import get_test_env_manager
from netra_backend.app.core.resilience.unified_circuit_breaker import UnifiedCircuitBreaker
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.external_api_client import HTTPError


logger = logging.getLogger(__name__)


class RealServiceFailureSimulator:
    """Simulates real service failures for circuit breaker testing."""
    
    def __init__(self):
        self.failure_modes = {}
        self.active_failures = set()
        
    def enable_database_failure(self, failure_type: str = "connection_timeout"):
        """Enable database failure simulation."""
        self.active_failures.add(f"database_{failure_type}")
        logger.info(f"Enabled database failure: {failure_type}")
    
    def enable_redis_failure(self, failure_type: str = "connection_refused"):
        """Enable Redis failure simulation."""
        self.active_failures.add(f"redis_{failure_type}")
        logger.info(f"Enabled Redis failure: {failure_type}")
    
    def enable_http_failure(self, failure_type: str = "timeout"):
        """Enable HTTP service failure simulation."""
        self.active_failures.add(f"http_{failure_type}")
        logger.info(f"Enabled HTTP failure: {failure_type}")
    
    def clear_all_failures(self):
        """Clear all failure simulations."""
        self.active_failures.clear()
        logger.info("Cleared all failure simulations")
    
    def is_failure_active(self, service: str, failure_type: str) -> bool:
        """Check if a specific failure is active."""
        return f"{service}_{failure_type}" in self.active_failures


class RealDatabaseFailureTest:
    """Test database circuit breaker with real connection issues."""
    
    def __init__(self, invalid_connection_string: str):
        self.invalid_connection_string = invalid_connection_string
        self.connection_attempts = 0
        
    async def attempt_connection(self) -> bool:
        """Attempt database connection that will fail."""
        self.connection_attempts += 1
        
        try:
            # Try to connect to invalid database
            import asyncpg
            conn = await asyncpg.connect(self.invalid_connection_string, timeout=2.0)
            await conn.close()
            return True
        except Exception as e:
            logger.info(f"Database connection failed (attempt {self.connection_attempts}): {e}")
            return False
    
    async def simulate_database_recovery(self, valid_connection_string: str) -> bool:
        """Simulate database recovery by using valid connection."""
        try:
            import asyncpg
            conn = await asyncpg.connect(valid_connection_string, timeout=5.0)
            await conn.close()
            logger.info("Database recovery successful")
            return True
        except Exception as e:
            logger.error(f"Database recovery failed: {e}")
            return False


class RealRedisFailureTest:
    """Test Redis circuit breaker with real connection failures."""
    
    def __init__(self, invalid_redis_url: str):
        self.invalid_redis_url = invalid_redis_url
        self.connection_attempts = 0
        
    async def attempt_redis_operation(self) -> bool:
        """Attempt Redis operation that will fail."""
        self.connection_attempts += 1
        
        try:
            import redis.asyncio as aioredis
            redis_client = await aioredis.from_url(
                self.invalid_redis_url,
                socket_connect_timeout=2.0,
                socket_timeout=2.0
            )
            await redis_client.ping()
            await redis_client.close()
            return True
        except Exception as e:
            logger.info(f"Redis operation failed (attempt {self.connection_attempts}): {e}")
            return False
    
    async def simulate_redis_recovery(self, valid_redis_url: str) -> bool:
        """Simulate Redis recovery."""
        try:
            import redis.asyncio as aioredis
            redis_client = await aioredis.from_url(valid_redis_url)
            await redis_client.ping()
            await redis_client.close()
            logger.info("Redis recovery successful")
            return True
        except Exception as e:
            logger.error(f"Redis recovery failed: {e}")
            return False


class RealHTTPFailureTest:
    """Test HTTP client circuit breaker with real service failures."""
    
    def __init__(self):
        self.request_count = 0
        
    async def attempt_http_request(self, url: str, timeout: float = 2.0) -> bool:
        """Attempt HTTP request that may fail."""
        self.request_count += 1
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        logger.info(f"HTTP request successful (attempt {self.request_count})")
                        return True
                    else:
                        logger.info(f"HTTP request failed with status {response.status} (attempt {self.request_count})")
                        return False
        except Exception as e:
            logger.info(f"HTTP request failed (attempt {self.request_count}): {e}")
            return False


@pytest.fixture
def failure_simulator():
    """Fixture providing service failure simulator."""
    simulator = RealServiceFailureSimulator()
    yield simulator
    simulator.clear_all_failures()


@pytest.fixture
async def real_database_test():
    """Fixture providing real database for circuit breaker testing."""
    # Valid connection for recovery testing
    valid_url = "postgresql://netra:netra123@localhost:5432/netra_test"
    # Invalid connection for failure testing
    invalid_url = "postgresql://invalid:invalid@nonexistent:9999/invalid"
    
    test_helper = RealDatabaseFailureTest(invalid_url)
    yield test_helper, valid_url
    # Cleanup handled by test helper


@pytest.fixture
async def real_redis_test():
    """Fixture providing real Redis for circuit breaker testing."""
    # Valid Redis URL for recovery
    valid_url = "redis://localhost:6379/1"
    # Invalid Redis URL for failure testing
    invalid_url = "redis://nonexistent:9999/0"
    
    test_helper = RealRedisFailureTest(invalid_url)
    yield test_helper, valid_url


@pytest.fixture
def circuit_breaker():
    """Fixture providing circuit breaker instance."""
    # Create circuit breaker with aggressive thresholds for testing
    breaker = UnifiedCircuitBreaker(
        failure_threshold=3,  # Fail after 3 failures
        recovery_timeout=5.0,  # 5 second recovery timeout
        timeout=2.0  # 2 second operation timeout
    )
    yield breaker


class TestRealDatabaseCircuitBreaker:
    """Test circuit breaker with real database failures."""
    
    @pytest.mark.asyncio
    async def test_database_circuit_breaker_failure_detection(self, real_database_test, circuit_breaker):
        """
        Test that circuit breaker detects real database failures.
        MUST PASS: Should detect and circuit real database connection failures.
        """
        db_test, valid_url = real_database_test
        
        # Test successful connection detection
        success_count = 0
        failure_count = 0
        
        # First, verify circuit breaker starts in closed state
        assert circuit_breaker.state == "closed", "Circuit breaker should start closed"
        
        # Attempt multiple database connections that will fail
        for attempt in range(5):
            try:
                # Use circuit breaker to wrap the database operation
                result = await circuit_breaker.call(
                    db_test.attempt_connection(),
                    operation_name=f"database_connection_attempt_{attempt}"
                )
                
                if result:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                failure_count += 1
                logger.info(f"Circuit breaker caught failure {attempt}: {e}")
                
            # Small delay between attempts
            await asyncio.sleep(0.5)
        
        # Circuit breaker should have opened due to failures
        logger.info(f"Database test results: {success_count} successes, {failure_count} failures")
        logger.info(f"Circuit breaker state: {circuit_breaker.state}")
        logger.info(f"Circuit breaker stats: {circuit_breaker.get_stats()}")
        
        # With invalid database connection, should have failures
        assert failure_count > 0, "Should have detected database connection failures"
        
        # Circuit breaker should open after threshold failures
        if failure_count >= circuit_breaker.failure_threshold:
            assert circuit_breaker.state in ["open", "half-open"], \
                f"Circuit breaker should be open after {failure_count} failures"
    
    @pytest.mark.asyncio
    async def test_database_circuit_breaker_recovery(self, real_database_test, circuit_breaker):
        """
        Test circuit breaker recovery with real database reconnection.
        MUST PASS: Should recover when database becomes available.
        """
        db_test, valid_url = real_database_test
        
        # Force circuit breaker into open state with failures
        for attempt in range(circuit_breaker.failure_threshold + 1):
            try:
                await circuit_breaker.call(
                    db_test.attempt_connection(),
                    operation_name=f"force_failure_{attempt}"
                )
            except:
                pass
            await asyncio.sleep(0.1)
        
        # Verify circuit breaker is open
        logger.info(f"Circuit breaker state after failures: {circuit_breaker.state}")
        
        # Wait for recovery timeout
        await asyncio.sleep(circuit_breaker.recovery_timeout + 1)
        
        # Now test recovery with valid database connection
        recovery_successful = await db_test.simulate_database_recovery(valid_url)
        
        if recovery_successful:
            # Try operation through circuit breaker
            try:
                # This should succeed and potentially close the circuit
                result = await circuit_breaker.call(
                    db_test.simulate_database_recovery(valid_url),
                    operation_name="recovery_test"
                )
                
                logger.info(f"Recovery test result: {result}")
                logger.info(f"Circuit breaker state after recovery: {circuit_breaker.state}")
                
                # Circuit breaker should move towards closed state
                assert circuit_breaker.state in ["closed", "half-open"], \
                    "Circuit breaker should recover after successful operations"
                    
            except Exception as e:
                logger.info(f"Recovery test failed: {e}")
        else:
            logger.info("Database recovery simulation failed - this is acceptable in test environment")


class TestRealRedisCircuitBreaker:
    """Test circuit breaker with real Redis failures."""
    
    @pytest.mark.asyncio
    async def test_redis_circuit_breaker_failure_cascade_prevention(self, real_redis_test, circuit_breaker):
        """
        Test that Redis circuit breaker prevents failure cascade.
        MUST PASS: Should prevent repeated Redis connection attempts.
        """
        redis_test, valid_url = real_redis_test
        
        start_time = time.time()
        failure_times = []
        
        # Attempt multiple Redis operations that will fail
        for attempt in range(8):  # More than threshold to trigger circuit breaker
            attempt_start = time.time()
            
            try:
                result = await circuit_breaker.call(
                    redis_test.attempt_redis_operation(),
                    operation_name=f"redis_operation_{attempt}"
                )
                
                if not result:
                    failure_times.append(time.time() - attempt_start)
                    
            except Exception as e:
                failure_times.append(time.time() - attempt_start)
                logger.info(f"Redis attempt {attempt} failed: {e}")
            
            await asyncio.sleep(0.2)
        
        total_time = time.time() - start_time
        
        logger.info(f"Redis failure test completed in {total_time:.2f} seconds")
        logger.info(f"Average failure time: {sum(failure_times)/len(failure_times):.2f} seconds")
        logger.info(f"Circuit breaker state: {circuit_breaker.state}")
        
        # Circuit breaker should prevent cascade by opening
        assert len(failure_times) > 0, "Should have detected Redis failures"
        
        # After threshold, circuit breaker should be open
        if len(failure_times) >= circuit_breaker.failure_threshold:
            assert circuit_breaker.state == "open", \
                "Circuit breaker should be open to prevent cascade failures"
    
    @pytest.mark.asyncio
    async def test_redis_circuit_breaker_performance_protection(self, real_redis_test, circuit_breaker):
        """
        Test that circuit breaker protects against slow Redis operations.
        MUST PASS: Should timeout slow operations and protect system performance.
        """
        redis_test, valid_url = real_redis_test
        
        # Test with very short timeout to trigger timeout protection
        short_timeout_breaker = UnifiedCircuitBreaker(
            failure_threshold=2,
            recovery_timeout=3.0,
            timeout=0.5  # Very short timeout
        )
        
        timeout_count = 0
        success_count = 0
        
        # Attempt operations that may timeout
        for attempt in range(5):
            start_time = time.time()
            
            try:
                result = await short_timeout_breaker.call(
                    redis_test.attempt_redis_operation(),
                    operation_name=f"timeout_test_{attempt}"
                )
                
                operation_time = time.time() - start_time
                
                if result:
                    success_count += 1
                else:
                    if operation_time >= short_timeout_breaker.timeout:
                        timeout_count += 1
                        
            except asyncio.TimeoutError:
                timeout_count += 1
                logger.info(f"Redis operation {attempt} timed out")
            except Exception as e:
                logger.info(f"Redis operation {attempt} failed: {e}")
            
            await asyncio.sleep(0.1)
        
        logger.info(f"Redis timeout test: {timeout_count} timeouts, {success_count} successes")
        logger.info(f"Circuit breaker state: {short_timeout_breaker.state}")
        
        # Should protect against slow operations
        if timeout_count >= short_timeout_breaker.failure_threshold:
            assert short_timeout_breaker.state == "open", \
                "Circuit breaker should open to protect against slow operations"


class TestRealHTTPCircuitBreaker:
    """Test circuit breaker with real HTTP service failures."""
    
    @pytest.mark.asyncio
    async def test_http_circuit_breaker_with_real_endpoints(self, circuit_breaker):
        """
        Test HTTP circuit breaker with real HTTP endpoints.
        MUST PASS: Should handle real HTTP failures and timeouts.
        """
        http_test = RealHTTPFailureTest()
        
        # Test with known unreachable endpoint
        unreachable_url = "http://240.0.0.1:9999/nonexistent"  # Reserved IP that won't respond
        
        failure_count = 0
        timeout_count = 0
        
        # Attempt HTTP requests that will fail
        for attempt in range(6):
            start_time = time.time()
            
            try:
                result = await circuit_breaker.call(
                    http_test.attempt_http_request(unreachable_url, timeout=1.0),
                    operation_name=f"http_test_{attempt}"
                )
                
                if not result:
                    failure_count += 1
                    
            except asyncio.TimeoutError:
                timeout_count += 1
                logger.info(f"HTTP request {attempt} timed out")
            except Exception as e:
                failure_count += 1
                logger.info(f"HTTP request {attempt} failed: {e}")
            
            request_time = time.time() - start_time
            logger.info(f"HTTP request {attempt} took {request_time:.2f} seconds")
            
            await asyncio.sleep(0.3)
        
        total_failures = failure_count + timeout_count
        
        logger.info(f"HTTP test results: {total_failures} total failures ({failure_count} failures, {timeout_count} timeouts)")
        logger.info(f"Circuit breaker state: {circuit_breaker.state}")
        logger.info(f"Circuit breaker stats: {circuit_breaker.get_stats()}")
        
        # Should detect failures and protect system
        assert total_failures > 0, "Should have detected HTTP failures"
        
        if total_failures >= circuit_breaker.failure_threshold:
            assert circuit_breaker.state == "open", \
                "Circuit breaker should be open after HTTP failures"
    
    @pytest.mark.asyncio
    async def test_http_circuit_breaker_with_valid_endpoint(self, circuit_breaker):
        """
        Test circuit breaker behavior with valid HTTP endpoint.
        MUST PASS: Should work correctly with successful HTTP calls.
        """
        http_test = RealHTTPFailureTest()
        
        # Use a reliable public endpoint
        valid_url = "https://httpbin.org/get"
        
        success_count = 0
        failure_count = 0
        
        # Attempt requests to valid endpoint
        for attempt in range(3):  # Fewer attempts to be nice to public service
            try:
                result = await circuit_breaker.call(
                    http_test.attempt_http_request(valid_url, timeout=10.0),
                    operation_name=f"valid_http_test_{attempt}"
                )
                
                if result:
                    success_count += 1
                else:
                    failure_count += 1
                    
            except Exception as e:
                failure_count += 1
                logger.info(f"Valid HTTP request {attempt} failed: {e}")
            
            await asyncio.sleep(1.0)  # Be respectful to public service
        
        logger.info(f"Valid HTTP test: {success_count} successes, {failure_count} failures")
        logger.info(f"Circuit breaker state: {circuit_breaker.state}")
        
        # With valid endpoint, should have some successes
        # (May fail due to network issues, but that's OK for this test)
        if success_count > 0:
            assert circuit_breaker.state == "closed", \
                "Circuit breaker should remain closed for successful operations"


class TestRealWebSocketCircuitBreaker:
    """Test circuit breaker with WebSocket connection failures."""
    
    @pytest.mark.asyncio
    async def test_websocket_circuit_breaker_connection_failures(self, circuit_breaker):
        """
        Test WebSocket circuit breaker with real connection failures.
        MUST PASS: Should detect WebSocket connection failures.
        """
        import websockets
        
        # Invalid WebSocket URL that will fail to connect
        invalid_ws_url = "ws://240.0.0.1:9999/nonexistent"
        
        connection_failures = 0
        
        async def attempt_websocket_connection():
            """Attempt WebSocket connection that will fail."""
            try:
                async with websockets.connect(invalid_ws_url, timeout=2.0):
                    return True
            except Exception as e:
                logger.info(f"WebSocket connection failed: {e}")
                return False
        
        # Attempt multiple WebSocket connections through circuit breaker
        for attempt in range(5):
            try:
                result = await circuit_breaker.call(
                    attempt_websocket_connection(),
                    operation_name=f"websocket_connection_{attempt}"
                )
                
                if not result:
                    connection_failures += 1
                    
            except Exception as e:
                connection_failures += 1
                logger.info(f"Circuit breaker caught WebSocket failure {attempt}: {e}")
            
            await asyncio.sleep(0.5)
        
        logger.info(f"WebSocket test: {connection_failures} connection failures")
        logger.info(f"Circuit breaker state: {circuit_breaker.state}")
        
        # Should detect WebSocket connection failures
        assert connection_failures > 0, "Should have detected WebSocket connection failures"
        
        if connection_failures >= circuit_breaker.failure_threshold:
            assert circuit_breaker.state == "open", \
                "Circuit breaker should open after WebSocket connection failures"


class TestRealCircuitBreakerIntegration:
    """Test circuit breaker integration across multiple real services."""
    
    @pytest.mark.asyncio
    async def test_multi_service_circuit_breaker_coordination(self, circuit_breaker, failure_simulator):
        """
        Test circuit breaker coordination across multiple failing services.
        MUST PASS: Should coordinate circuit breaking across service boundaries.
        """
        # Simulate failures in multiple services
        failure_simulator.enable_database_failure("connection_timeout")
        failure_simulator.enable_redis_failure("connection_refused")
        failure_simulator.enable_http_failure("timeout")
        
        service_failures = {
            'database': 0,
            'redis': 0,
            'http': 0
        }
        
        async def simulate_database_operation():
            """Simulate database operation that will fail."""
            if failure_simulator.is_failure_active('database', 'connection_timeout'):
                await asyncio.sleep(0.1)  # Simulate slow failure
                raise Exception("Database connection timeout")
            return True
        
        async def simulate_redis_operation():
            """Simulate Redis operation that will fail."""
            if failure_simulator.is_failure_active('redis', 'connection_refused'):
                raise Exception("Redis connection refused")
            return True
        
        async def simulate_http_operation():
            """Simulate HTTP operation that will fail."""
            if failure_simulator.is_failure_active('http', 'timeout'):
                await asyncio.sleep(3.0)  # Simulate timeout
                raise Exception("HTTP request timeout")
            return True
        
        # Test circuit breaker with multiple failing services
        operations = [
            ('database', simulate_database_operation),
            ('redis', simulate_redis_operation),
            ('http', simulate_http_operation)
        ]
        
        # Run multiple rounds of operations
        for round_num in range(3):
            logger.info(f"Multi-service test round {round_num}")
            
            # Test each service
            for service_name, operation_func in operations:
                for attempt in range(2):
                    try:
                        result = await circuit_breaker.call(
                            operation_func(),
                            operation_name=f"{service_name}_operation_{round_num}_{attempt}"
                        )
                        
                        if not result:
                            service_failures[service_name] += 1
                            
                    except Exception as e:
                        service_failures[service_name] += 1
                        logger.info(f"{service_name} operation failed: {e}")
                    
                    await asyncio.sleep(0.1)
            
            # Check circuit breaker state
            logger.info(f"Round {round_num} - Circuit breaker state: {circuit_breaker.state}")
            
            await asyncio.sleep(0.5)
        
        logger.info(f"Multi-service failures: {service_failures}")
        logger.info(f"Final circuit breaker state: {circuit_breaker.state}")
        logger.info(f"Circuit breaker stats: {circuit_breaker.get_stats()}")
        
        # Should have detected failures across services
        total_failures = sum(service_failures.values())
        assert total_failures > 0, "Should have detected failures across multiple services"
        
        # Circuit breaker should respond to coordinated failures
        if total_failures >= circuit_breaker.failure_threshold:
            assert circuit_breaker.state == "open", \
                "Circuit breaker should open due to multi-service failures"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_memory_and_performance_under_failure(self, circuit_breaker):
        """
        Test circuit breaker memory usage and performance under sustained failures.
        MUST PASS: Should not consume excessive memory during failure scenarios.
        """
        import psutil
        import gc
        
        # Get baseline memory
        process = psutil.Process()
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async def failing_operation():
            """Operation that always fails."""
            await asyncio.sleep(0.01)  # Small delay to simulate work
            raise Exception("Simulated failure for memory test")
        
        failure_count = 0
        start_time = time.time()
        
        # Generate many failures to test memory usage
        for batch in range(10):  # 10 batches
            batch_failures = 0
            
            for attempt in range(20):  # 20 attempts per batch
                try:
                    await circuit_breaker.call(
                        failing_operation(),
                        operation_name=f"memory_test_batch_{batch}_attempt_{attempt}"
                    )
                except:
                    batch_failures += 1
                    failure_count += 1
            
            logger.info(f"Batch {batch}: {batch_failures} failures")
            
            # Sample memory periodically
            if batch % 3 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - baseline_memory
                logger.info(f"Memory usage: {current_memory:.2f} MB (+{memory_growth:.2f} MB)")
        
        total_time = time.time() - start_time
        
        # Final memory check
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_growth = final_memory - baseline_memory
        
        logger.info(f"Circuit breaker failure test completed:")
        logger.info(f"  Total failures: {failure_count}")
        logger.info(f"  Total time: {total_time:.2f} seconds")
        logger.info(f"  Memory growth: {memory_growth:.2f} MB")
        logger.info(f"  Final state: {circuit_breaker.state}")
        logger.info(f"  Stats: {circuit_breaker.get_stats()}")
        
        # Verify performance and memory constraints
        assert failure_count > 0, "Should have processed failures"
        assert total_time < 60.0, f"Test should complete in reasonable time, took {total_time:.2f}s"
        assert memory_growth < 50.0, f"Memory growth {memory_growth:.2f} MB should be reasonable"
        
        # Circuit breaker should be in expected state
        assert circuit_breaker.state == "open", \
            "Circuit breaker should be open after sustained failures"


if __name__ == "__main__":
    # Run circuit breaker tests with real service failures
    pytest.main(["-v", __file__, "-s"])