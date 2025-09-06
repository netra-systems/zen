"""
from test_framework.performance_helpers import fast_test, timeout_override
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment

Deployment Edge Cases and Failure Scenarios Tests

Based on Iteration 3 audit findings, tests edge cases:
1. What if startup takes too long?
2. What if memory is insufficient?
3. What if CPU boost is disabled?
4. What if health checks timeout?

Comprehensive edge case coverage to prevent deployment failures.
"""

import asyncio
import time
import pytest
import psutil
import signal
import os
from typing import Dict, Any, Optional

from netra_backend.app.core.configuration import unified_config_manager
from test_framework.base import BaseTestCase
from test_framework.performance_helpers import fast_test


class TestStartupTimeoutEdgeCases(BaseTestCase):
    """Test edge cases related to startup timeouts."""

    @pytest.mark.asyncio
    @fast_test
    async def test_startup_exceeds_cloud_run_timeout(self):
        """Test scenario where startup takes longer than Cloud Run allows."""
        cloud_run_timeout = 60  # seconds
        
        # Simulate very slow startup
        with patch('netra_backend.app.startup_module.startup_sequence') as mock_startup:
            async def extremely_slow_startup():
                await asyncio.sleep(70)  # Exceeds Cloud Run timeout
                return True
            
            mock_startup.side_effect = extremely_slow_startup
            
            # Test timeout handling
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    self._simulate_problematic_startup(),
                    timeout=cloud_run_timeout
                )
            
        # Record that timeout was properly detected
        self.record_metric("timeout_detection_working", True)

    @pytest.mark.asyncio
    @fast_test
    async def test_database_connection_timeout_during_startup(self):
        """Test database connection timeout during startup."""
        # Simulate database connection hanging
        with patch('netra_backend.app.db.postgres.get_postgres_db') as mock_db:
            async def hanging_db_connection():
                await asyncio.sleep(30)  # Long database connection time
                return MagicNone  # TODO: Use real service instance
            
            mock_db.side_effect = hanging_db_connection
            
            # Startup should timeout and handle gracefully
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    self._simulate_database_dependent_startup(),
                    timeout=20  # Shorter than DB connection timeout
                )

    @pytest.mark.asyncio
    @fast_test
    async def test_service_registration_timeout(self):
        """Test service registration timeout during startup."""
        # Simulate service registry being unresponsive
        with patch('netra_backend.app.core.service_registry') as mock_registry:
            async def slow_registration():
                await asyncio.sleep(45)  # Very slow registration
                return True
            
            mock_registry.register_service.side_effect = slow_registration
            
            # Should timeout and fail gracefully
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    self._simulate_service_registration(),
                    timeout=30
                )

    @pytest.mark.asyncio
    @fast_test
    async def test_health_check_timeout_cascade(self):
        """Test cascading failures when health checks timeout."""
        # Simulate health checks that hang
        timeout_scenarios = [
            ("postgres_health", 15),
            ("redis_health", 10),
            ("clickhouse_health", 20)
        ]
        
        for health_check, timeout_duration in timeout_scenarios:
            with patch(f'netra_backend.app.services.health.{health_check}') as mock_health:
                async def hanging_health_check():
                    await asyncio.sleep(timeout_duration)
                    return {"status": "healthy"}
                
                mock_health.side_effect = hanging_health_check
                
                # Health check should timeout
                with pytest.raises(asyncio.TimeoutError):
                    await asyncio.wait_for(
                        self._execute_health_check(health_check),
                        timeout=5  # Short timeout to test detection
                    )

    async def _simulate_problematic_startup(self):
        """Simulate startup with problems."""
        # Multiple stages that could timeout
        stages = ["config", "database", "services", "health"]
        
        for stage in stages:
            if stage == "database":
                await asyncio.sleep(20)  # Long database init
            else:
                await asyncio.sleep(5)   # Other stages
        
        return True

    async def _simulate_database_dependent_startup(self):
        """Simulate startup that depends on database."""
        # Database connection should be attempted - use proper context manager pattern
        from netra_backend.app.database import get_db
        # FIX: Use async context manager directly to prevent cleanup issues
        # This avoids the "aclose(): asynchronous generator is already running" errors
        try:
            async with get_db() as db_session:
                # Use the database session properly
                from sqlalchemy import text
                await db_session.execute(text("SELECT 1"))  # Simple test query
                return True
        except Exception as e:
            # Database connection failed during startup simulation
            raise RuntimeError(f"Database connection failed during startup: {e}")

    async def _simulate_service_registration(self):
        """Simulate service registration process."""
        # Service registration steps
        await asyncio.sleep(2)  # Registration process
        return True

    async def _execute_health_check(self, check_name: str):
        """Execute specific health check."""
        await asyncio.sleep(1)  # Health check execution
        return {"status": "healthy", "check": check_name}


class TestMemoryInsufficientEdgeCases(BaseTestCase):
    """Test edge cases when memory is insufficient."""

    def test_memory_pressure_during_startup(self):
        """Test startup behavior under memory pressure."""
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        # Simulate memory-intensive startup operations
        large_objects = []
        try:
            # Create large objects to simulate memory pressure
            for i in range(100):
                # Create 5MB chunks
                large_chunk = b'0' * (5 * 1024 * 1024)
                large_objects.append(large_chunk)
                
                current_memory = process.memory_info().rss / (1024 * 1024)
                
                # Check if approaching memory limit
                if current_memory > 800:  # 800MB threshold
                    # Should trigger memory management
                    self.record_metric("memory_pressure_detected_at_mb", current_memory)
                    break
                    
            # Memory usage should be monitored
            current_memory = process.memory_info().rss / (1024 * 1024)
            memory_growth = current_memory - initial_memory
            
            assert memory_growth > 0, "Memory growth should be detectable"
            
            # Record metrics
            self.record_metric("memory_growth_during_test_mb", memory_growth)
            
        finally:
            # Clean up large objects
            large_objects.clear()

    @fast_test
    def test_out_of_memory_recovery(self):
        """Test recovery from out-of-memory conditions."""
        process = psutil.Process()
        
        # Simulate approaching memory limit
        memory_chunks = []
        try:
            while True:
                current_memory = process.memory_info().rss / (1024 * 1024)
                
                if current_memory > 850:  # Near 1GB limit
                    # Should trigger cleanup/recovery
                    break
                
                # Add memory chunk
                chunk = b'0' * (10 * 1024 * 1024)  # 10MB chunks
                memory_chunks.append(chunk)
                
                if len(memory_chunks) > 50:  # Safety limit
                    break
            
            # Test memory recovery
            memory_before_cleanup = process.memory_info().rss / (1024 * 1024)
            
            # Simulate cleanup
            memory_chunks.clear()
            
            # Force garbage collection
            import gc
            gc.collect()
            
            time.sleep(1)  # Allow OS to reclaim memory
            
            memory_after_cleanup = process.memory_info().rss / (1024 * 1024)
            memory_recovered = memory_before_cleanup - memory_after_cleanup
            
            # Should recover significant memory
            assert memory_recovered > 0, "Memory recovery should be positive"
            
            # Record metrics
            self.record_metric("memory_recovered_mb", memory_recovered)
            self.record_metric("memory_recovery_effectiveness_percent", 
                             (memory_recovered / memory_before_cleanup) * 100)
            
        finally:
            memory_chunks.clear()

    def test_memory_limit_enforcement(self):
        """Test that memory limits are properly enforced."""
        process = psutil.Process()
        
        # Test memory allocation patterns
        allocation_sizes = [1, 5, 10, 25, 50]  # MB sizes
        
        for size_mb in allocation_sizes:
            try:
                # Allocate memory chunk
                chunk = b'0' * (size_mb * 1024 * 1024)
                
                current_memory = process.memory_info().rss / (1024 * 1024)
                
                # Check if still within reasonable limits
                if current_memory > 900:  # 900MB warning threshold
                    pytest.warn(f"Memory usage {current_memory:.1f}MB approaching limit")
                
                assert current_memory < 1000, f"Memory {current_memory:.1f}MB exceeds safe limit"
                
                # Record allocation success
                self.record_metric(f"allocation_{size_mb}mb_success", True)
                
                # Clean up
                del chunk
                
            except MemoryError:
                # Memory allocation failed - this might be expected
                self.record_metric(f"allocation_{size_mb}mb_failed", True)
                break

    def test_memory_fragmentation_handling(self):
        """Test handling of memory fragmentation."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / (1024 * 1024)
        
        # Create fragmented memory pattern
        fragments = []
        
        try:
            # Allocate many small fragments
            for i in range(100):
                fragment = b'0' * (1024 * 1024)  # 1MB fragments
                fragments.append(fragment)
                
                # Release every other fragment
                if i % 2 == 0 and fragments:
                    fragments.pop()
            
            fragmented_memory = process.memory_info().rss / (1024 * 1024)
            
            # Clean up all fragments
            fragments.clear()
            import gc
            gc.collect()
            
            final_memory = process.memory_info().rss / (1024 * 1024)
            
            # Measure fragmentation impact
            fragmentation_overhead = fragmented_memory - initial_memory
            memory_recovered = fragmented_memory - final_memory
            
            # Record metrics
            self.record_metric("fragmentation_overhead_mb", fragmentation_overhead)
            self.record_metric("fragmentation_recovery_mb", memory_recovered)
            
        finally:
            fragments.clear()


class TestCPUBoostDisabledEdgeCases(BaseTestCase):
    """Test edge cases when CPU boost is disabled."""

    def test_performance_without_cpu_boost(self):
        """Test performance degradation when CPU boost is disabled."""
        # Simulate CPU-intensive operations
        cpu_tasks = [
            self._fibonacci_calculation,
            self._prime_number_generation,
            self._matrix_multiplication,
            self._string_processing
        ]
        
        task_times = []
        
        for task in cpu_tasks:
            start_time = time.time()
            
            # Execute CPU task
            result = task()
            
            execution_time = time.time() - start_time
            task_times.append(execution_time)
            
            # Without CPU boost, tasks might take longer
            # But should still complete in reasonable time
            max_time = 5.0  # 5 seconds max per task
            assert execution_time < max_time, f"Task took {execution_time:.2f}s, too slow without CPU boost"
        
        avg_task_time = sum(task_times) / len(task_times)
        
        # Record performance metrics
        self.record_metric("avg_cpu_task_time_no_boost", avg_task_time)
        self.record_metric("max_cpu_task_time_no_boost", max(task_times))

    def test_concurrent_cpu_operations_no_boost(self):
        """Test concurrent CPU operations when boost is disabled."""
        import threading
        
        # Test concurrent CPU-bound operations
        num_threads = 4
        results = []
        
        def cpu_worker():
            start_time = time.time()
            # CPU-intensive work
            result = sum(i * i for i in range(100000))
            execution_time = time.time() - start_time
            results.append(execution_time)
            return result
        
        # Launch concurrent workers
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=cpu_worker)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Analyze concurrent performance
        avg_concurrent_time = sum(results) / len(results)
        max_concurrent_time = max(results)
        
        # Without CPU boost, concurrent operations might be slower
        # but should still complete
        assert max_concurrent_time < 10, f"Concurrent CPU task took {max_concurrent_time:.2f}s, too slow"
        
        # Record metrics
        self.record_metric("concurrent_cpu_avg_time_no_boost", avg_concurrent_time)
        self.record_metric("concurrent_cpu_max_time_no_boost", max_concurrent_time)

    def test_cpu_throttling_detection(self):
        """Test detection of CPU throttling."""
        process = psutil.Process()
        
        # Measure CPU performance over time
        cpu_measurements = []
        
        for i in range(5):
            start_time = time.time()
            cpu_before = process.cpu_percent()
            
            # CPU-intensive task
            self._cpu_intensive_operation()
            
            cpu_after = process.cpu_percent(interval=1)
            execution_time = time.time() - start_time
            
            cpu_measurements.append({
                "iteration": i,
                "execution_time": execution_time,
                "cpu_before": cpu_before,
                "cpu_after": cpu_after
            })
        
        # Analyze CPU performance consistency
        execution_times = [m["execution_time"] for m in cpu_measurements]
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_deviation = max(abs(t - avg_execution_time) for t in execution_times)
        
        # Performance should be relatively consistent
        max_acceptable_deviation = avg_execution_time * 0.5  # 50% deviation
        
        if max_deviation > max_acceptable_deviation:
            pytest.warn(f"High CPU performance variation detected: {max_deviation:.2f}s")
        
        # Record metrics
        self.record_metric("cpu_performance_consistency", max_acceptable_deviation - max_deviation)
        for i, measurement in enumerate(cpu_measurements):
            self.record_metric(f"cpu_measurement_{i}_time", measurement["execution_time"])

    def _fibonacci_calculation(self, n=30):
        """CPU-intensive Fibonacci calculation."""
        if n <= 1:
            return n
        return self._fibonacci_calculation(n-1) + self._fibonacci_calculation(n-2)

    def _prime_number_generation(self, limit=10000):
        """CPU-intensive prime number generation."""
        primes = []
        for num in range(2, limit):
            is_prime = True
            for i in range(2, int(num ** 0.5) + 1):
                if num % i == 0:
                    is_prime = False
                    break
            if is_prime:
                primes.append(num)
        return len(primes)

    def _matrix_multiplication(self, size=100):
        """CPU-intensive matrix multiplication."""
        import random
        
        # Create random matrices
        matrix_a = [[random.random() for _ in range(size)] for _ in range(size)]
        matrix_b = [[random.random() for _ in range(size)] for _ in range(size)]
        
        # Matrix multiplication
        result = [[0 for _ in range(size)] for _ in range(size)]
        
        for i in range(size):
            for j in range(size):
                for k in range(size):
                    result[i][j] += matrix_a[i][k] * matrix_b[k][j]
        
        return result[0][0]  # Return single value

    def _string_processing(self, iterations=100000):
        """CPU-intensive string processing."""
        text = "The quick brown fox jumps over the lazy dog"
        
        result = ""
        for i in range(iterations):
            # String manipulations
            processed = text.upper().lower().replace("fox", "cat")
            result = processed + str(i)
        
        return len(result)

    def _cpu_intensive_operation(self):
        """General CPU-intensive operation."""
        # Combination of operations
        result = 0
        for i in range(50000):
            result += i * i
            result = result % 1000000
        return result


class TestHealthCheckTimeoutEdgeCases(BaseTestCase):
    """Test edge cases when health checks timeout."""

    @pytest.mark.asyncio
    @fast_test
    async def test_health_check_cascade_timeout(self):
        """Test cascading timeouts in health check chain."""
        # Simulate health checks with different timeout characteristics
        health_checks = [
            ("database", 2.0, True),    # Should pass
            ("redis", 10.0, False),     # Will timeout
            ("clickhouse", 1.0, True),  # Should pass
            ("llm", 15.0, False),       # Will timeout
        ]
        
        results = {}
        
        for service, delay, should_pass in health_checks:
            try:
                result = await asyncio.wait_for(
                    self._simulate_health_check(service, delay),
                    timeout=5.0
                )
                results[service] = {"success": True, "result": result}
                
                if not should_pass:
                    pytest.warn(f"Expected {service} to timeout but it passed")
                    
            except asyncio.TimeoutError:
                results[service] = {"success": False, "timeout": True}
                
                if should_pass:
                    pytest.warn(f"Expected {service} to pass but it timed out")
        
        # At least some health checks should succeed
        successful_checks = sum(1 for result in results.values() if result.get("success"))
        total_checks = len(results)
        
        success_rate = (successful_checks / total_checks) * 100
        
        # Should have partial success even with some timeouts
        assert success_rate >= 30, f"Health check success rate {success_rate:.1f}% too low"
        
        # Record metrics
        self.record_metric("health_check_success_rate_with_timeouts", success_rate)

    @pytest.mark.asyncio
    @fast_test
    async def test_health_check_timeout_recovery(self):
        """Test recovery after health check timeouts."""
        # Initial health check that times out
        try:
            await asyncio.wait_for(
                self._simulate_slow_health_check(),
                timeout=2.0
            )
        except asyncio.TimeoutError:
            pass  # Expected timeout
        
        # Subsequent health check should work (recovery)
        try:
            result = await asyncio.wait_for(
                self._simulate_fast_health_check(),
                timeout=5.0
            )
            assert result["status"] == "healthy", "Recovery health check should succeed"
            
            self.record_metric("health_check_recovery_successful", True)
            
        except asyncio.TimeoutError:
            pytest.fail("Recovery health check should not timeout")

    @pytest.mark.asyncio
    @fast_test
    async def test_partial_health_check_failure(self):
        """Test system behavior with partial health check failures."""
        # Mix of passing and failing health checks
        health_components = [
            "core_database",      # Critical - should pass
            "cache_redis",        # Optional - might fail
            "analytics_clickhouse",  # Optional - might fail
            "external_llm",       # Optional - might timeout
        ]
        
        results = {}
        critical_failures = 0
        
        for component in health_components:
            is_critical = component.startswith("core_")
            
            try:
                result = await asyncio.wait_for(
                    self._simulate_component_health_check(component),
                    timeout=3.0
                )
                results[component] = {"success": True, "critical": is_critical}
                
            except (asyncio.TimeoutError, Exception):
                results[component] = {"success": False, "critical": is_critical}
                
                if is_critical:
                    critical_failures += 1
        
        # Critical components must not fail
        assert critical_failures == 0, f"Critical health check failures: {critical_failures}"
        
        # Calculate overall health
        total_components = len(results)
        successful_components = sum(1 for result in results.values() if result["success"])
        health_percentage = (successful_components / total_components) * 100
        
        # Record metrics
        self.record_metric("partial_health_check_percentage", health_percentage)
        self.record_metric("critical_health_failures", critical_failures)

    async def _simulate_health_check(self, service: str, delay: float):
        """Simulate health check with specific delay."""
        await asyncio.sleep(delay)
        return {"service": service, "status": "healthy", "delay": delay}

    async def _simulate_slow_health_check(self):
        """Simulate slow health check that will timeout."""
        await asyncio.sleep(10)  # Will timeout before this completes
        return {"status": "healthy"}

    async def _simulate_fast_health_check(self):
        """Simulate fast health check for recovery testing."""
        await asyncio.sleep(0.1)
        return {"status": "healthy", "response_time_ms": 100}

    async def _simulate_component_health_check(self, component: str):
        """Simulate health check for specific component."""
        # Different components have different characteristics
        delays = {
            "core_database": 0.5,      # Fast and reliable
            "cache_redis": 1.0,        # Moderate
            "analytics_clickhouse": 2.0,  # Slower
            "external_llm": 5.0,       # Very slow, might timeout
        }
        
        delay = delays.get(component, 1.0)
        await asyncio.sleep(delay)
        
        # Simulate occasional failures for non-critical components
        if not component.startswith("core_") and delay > 3.0:
            raise Exception(f"Component {component} unavailable")
        
        return {"component": component, "status": "healthy"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])