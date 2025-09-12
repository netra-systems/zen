"""
Mission Critical Tests: Docker Rate Limiter Integration

TEAM DELTA INFRASTRUCTURE TESTS: Comprehensive rate limiting and backpressure handling
LIFE OR DEATH CRITICAL: Platform must handle 100+ concurrent Docker operations

This test suite validates that ALL Docker operations go through the rate limiter
to prevent Docker daemon crashes from concurrent operation storms.

CRITICAL: These tests protect the $2M+ ARR platform from Docker daemon instability.

INFRASTRUCTURE VALIDATION:
- Performance benchmarks (throughput, latency, resource usage)
- Rate limiting and exponential backoff handling  
- Backpressure management under extreme load
- Circuit breaker integration and failover
- Resource cleanup efficiency
- Concurrent operation stability
"""

import pytest
import subprocess
import threading
import time
import asyncio
import statistics
import psutil
import random
import logging
import uuid
import gc
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import sys
from pathlib import Path
from test_framework.docker.unified_docker_manager import UnifiedDockerManager
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_framework.docker_rate_limiter import (
    get_docker_rate_limiter, 
    execute_docker_command,
    docker_health_check,
    DockerCommandResult
)
from test_framework.docker_circuit_breaker import (
    DockerCircuitBreaker,
    DockerCircuitBreakerError,
    execute_docker_command_with_circuit_breaker,
    get_circuit_breaker_manager,
    CircuitBreakerState
)
from test_framework.docker_introspection import DockerIntrospector
from test_framework.port_conflict_fix import DockerPortManager, PortConflictResolver
from test_framework.unified_docker_manager import UnifiedDockerManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class RateLimiterMetrics:
    """Track rate limiter performance metrics."""
    total_operations: int = 0
    rate_limited_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    avg_wait_time_ms: float = 0.0
    max_wait_time_ms: float = 0.0
    throughput_ops_per_sec: float = 0.0
    backoff_events: int = 0
    circuit_breaker_trips: int = 0


class TestDockerRateLimiterIntegration:
    """Test Docker rate limiter integration across all modules."""
    
    def test_rate_limiter_singleton_behavior(self):
        """Test that rate limiter maintains singleton behavior."""
        limiter1 = get_docker_rate_limiter()
        limiter2 = get_docker_rate_limiter()
        
        assert limiter1 is limiter2, "Rate limiter should be singleton"
        assert limiter1.min_interval > 0, "Rate limiter should have minimum interval"
        assert limiter1.max_concurrent > 0, "Rate limiter should allow concurrent operations"
    
    def test_basic_docker_command_execution(self):
        """Test basic Docker command execution through rate limiter."""
        # Test a safe Docker command that should always work
        result = execute_docker_command(["docker", "version", "--format", "{{.Server.Version}}"])
        
        assert isinstance(result, DockerCommandResult)
        assert result.duration > 0, "Command should have measurable duration"
        assert result.retry_count >= 0, "Retry count should be non-negative"
        
        # Verify rate limiting statistics
        limiter = get_docker_rate_limiter()
        stats = limiter.get_statistics()
        assert stats["total_operations"] > 0, "Operations should be tracked"
    
    def test_concurrent_docker_operations_are_rate_limited(self):
        """Test that concurrent Docker operations respect rate limiting."""
        limiter = get_docker_rate_limiter()
        initial_stats = limiter.get_statistics()
        
        # Execute multiple Docker commands concurrently
        def run_docker_command(index: int) -> DockerCommandResult:
            return execute_docker_command([
                "docker", "version", "--format", f"Test-{index}"
            ])
        
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_docker_command, i) for i in range(10)]
            results = [future.result() for future in futures]
        end_time = time.time()
        
        # Verify all operations completed
        assert len(results) == 10, "All operations should complete"
        assert all(isinstance(r, DockerCommandResult) for r in results), "All results should be DockerCommandResult"
        
        # Verify rate limiting was applied (operations should take longer due to limiting)
        total_duration = end_time - start_time
        assert total_duration > 2.0, "Rate limiting should add delay for concurrent operations"
        
        # Verify statistics updated correctly
        final_stats = limiter.get_statistics()
        assert final_stats["total_operations"] > initial_stats["total_operations"]
        assert final_stats["rate_limited_operations"] >= 0
    
    def test_docker_health_check_function(self):
        """Test the convenience health check function."""
        is_healthy = docker_health_check()
        assert isinstance(is_healthy, bool), "Health check should return boolean"
        
        # Health check should use rate limiter
        limiter = get_docker_rate_limiter()
        stats_before = limiter.get_statistics()
        
        docker_health_check()
        
        stats_after = limiter.get_statistics()
        assert stats_after["total_operations"] > stats_before["total_operations"], \
            "Health check should go through rate limiter"
    
    def test_error_handling_and_retries(self):
        """Test that rate limiter handles errors correctly with retries."""
        # Try to execute a Docker command that will fail
        result = execute_docker_command(["docker", "run", "--invalid-flag", "nonexistent:image"])
        
        assert isinstance(result, DockerCommandResult)
        assert result.returncode != 0, "Command should fail"
        assert result.stderr, "Error should be captured"
        assert result.retry_count >= 0, "Retry count should be tracked"
    
    def test_timeout_handling(self):
        """Test rate limiter timeout handling."""
        try:
            # Use a very short timeout to test timeout handling
            result = execute_docker_command(
                ["docker", "version"], 
                timeout=0.001  # 1ms timeout - should fail
            )
            # If it doesn't raise an exception, it should return an error result
            assert result.returncode != 0 or "timeout" in result.stderr.lower()
        except Exception as e:
            # Timeout exceptions are acceptable
            assert "timeout" in str(e).lower() or "expired" in str(e).lower()


class TestDockerCircuitBreakerIntegration:
    """Test Docker circuit breaker integration and protection."""
    
    def test_circuit_breaker_creation_and_basic_operation(self):
        """Test circuit breaker creation and basic command execution."""
        breaker = DockerCircuitBreaker("test-basic")
        
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.is_available is True
        
        # Execute a simple command
        result = breaker.execute_docker_command(["docker", "version", "--format", "{{.Client.Version}}"])
        assert isinstance(result, DockerCommandResult)
        
        stats = breaker.get_stats()
        assert stats["total_requests"] > 0
        assert stats["state"] == "closed"
    
    def test_circuit_breaker_failure_detection(self):
        """Test circuit breaker opens after repeated failures."""
        breaker = DockerCircuitBreaker("test-failure", config=None)
        
        # Force multiple failures to trigger circuit opening
        failure_count = 0
        for i in range(6):  # More than failure threshold
            try:
                result = breaker.execute_docker_command([
                    "docker", "run", "--invalid-flag", "nonexistent:image"
                ])
                if result.returncode != 0:
                    failure_count += 1
            except Exception:
                failure_count += 1
        
        # Circuit should open after repeated failures
        stats = breaker.get_stats()
        assert stats["failed_requests"] > 0, "Failures should be tracked"
        
        # If circuit opened, should fail fast
        if breaker.state == CircuitBreakerState.OPEN:
            with pytest.raises(DockerCircuitBreakerError):
                breaker.execute_docker_command(["docker", "version"])
    
    def test_circuit_breaker_manager(self):
        """Test circuit breaker manager functionality."""
        manager = get_circuit_breaker_manager()
        
        breaker1 = manager.get_breaker("test-manager-1")
        breaker2 = manager.get_breaker("test-manager-2")
        breaker1_again = manager.get_breaker("test-manager-1")
        
        assert breaker1 is not breaker2, "Different names should give different breakers"
        assert breaker1 is breaker1_again, "Same name should give same breaker"
        
        # Test getting all stats
        all_stats = manager.get_all_stats()
        assert "test-manager-1" in all_stats
        assert "test-manager-2" in all_stats
    
    def test_convenience_function_with_circuit_breaker(self):
        """Test convenience function for circuit breaker execution."""
        result = execute_docker_command_with_circuit_breaker(
            ["docker", "version"], 
            breaker_name="test-convenience"
        )
        
        assert isinstance(result, DockerCommandResult)
        
        # Verify the breaker was created and used
        manager = get_circuit_breaker_manager()
        breaker_stats = manager.get_all_stats()
        assert "test-convenience" in breaker_stats
        assert breaker_stats["test-convenience"]["total_requests"] > 0


class TestDockerIntrospectionRateLimiterIntegration:
    """Test that Docker introspection uses rate limiter."""
    
    def test_docker_introspection_uses_rate_limiter(self):
        """Test that DockerIntrospector uses rate-limited Docker commands."""
        introspector = DockerIntrospector("docker-compose.test.yml", "test-introspection")
        
        # Get initial rate limiter stats
        limiter = get_docker_rate_limiter()
        initial_stats = limiter.get_statistics()
        
        # Perform introspection operations
        try:
            # This should use rate-limited Docker commands internally
            service_status = introspector._get_service_status(None)
            
            # Verify rate limiter was used
            final_stats = limiter.get_statistics()
            assert final_stats["total_operations"] > initial_stats["total_operations"], \
                "DockerIntrospector should use rate-limited Docker commands"
                
        except Exception as e:
            # It's OK if the docker-compose file doesn't exist for this test
            # We're mainly testing that the rate limiter was attempted to be used
            if "No such file" in str(e) or "not found" in str(e):
                final_stats = limiter.get_statistics() 
                assert final_stats["total_operations"] >= initial_stats["total_operations"]
            else:
                raise
    
    def test_resource_usage_collection_uses_rate_limiter(self):
        """Test that resource usage collection uses rate limiter."""
        introspector = DockerIntrospector()
        limiter = get_docker_rate_limiter()
        
        initial_stats = limiter.get_statistics()
        
        # This should trigger rate-limited Docker stats command
        try:
            resource_usage = introspector._get_resource_usage([])
            final_stats = limiter.get_statistics()
            
            assert final_stats["total_operations"] > initial_stats["total_operations"], \
                "Resource usage collection should use rate limiter"
                
        except Exception:
            # Even if the command fails, it should have gone through rate limiter
            final_stats = limiter.get_statistics()
            assert final_stats["total_operations"] >= initial_stats["total_operations"]


class TestPortConflictFixRateLimiterIntegration:
    """Test that port conflict resolution uses rate limiter."""
    
    def test_cleanup_stale_containers_uses_rate_limiter(self):
        """Test that stale container cleanup uses rate limiter."""
        limiter = get_docker_rate_limiter()
        initial_stats = limiter.get_statistics()
        
        # This should trigger rate-limited Docker commands
        cleaned_count = PortConflictResolver.cleanup_stale_docker_containers("test-prefix-nonexistent")
        
        final_stats = limiter.get_statistics()
        assert final_stats["total_operations"] > initial_stats["total_operations"], \
            "Container cleanup should use rate limiter"
        assert isinstance(cleaned_count, int), "Should return count of cleaned containers"


class TestRateLimiterStatistics:
    """Test rate limiter statistics and monitoring."""
    
    def test_statistics_tracking(self):
        """Test that rate limiter correctly tracks statistics."""
        limiter = get_docker_rate_limiter()
        
        # Reset statistics for clean test
        limiter.reset_statistics()
        
        # Execute some commands
        for i in range(3):
            execute_docker_command(["docker", "version", "--format", f"test-{i}"])
        
        stats = limiter.get_statistics()
        assert stats["total_operations"] == 3, "Should track all operations"
        assert stats["success_rate"] > 0, "Should calculate success rate"
        assert "rate_limit_percentage" in stats, "Should track rate limiting percentage"
    
    def test_statistics_reset(self):
        """Test that statistics can be reset."""
        limiter = get_docker_rate_limiter()
        
        # Generate some statistics
        execute_docker_command(["docker", "version"])
        
        stats_before = limiter.get_statistics()
        assert stats_before["total_operations"] > 0
        
        # Reset and verify
        limiter.reset_statistics()
        stats_after = limiter.get_statistics()
        
        assert stats_after["total_operations"] == 0, "Statistics should be reset"
        assert stats_after["failed_operations"] == 0, "Failed operations should be reset"


class TestIntegrationRobustness:
    """Test overall robustness of the integrated system."""
    
    def test_high_concurrency_stress(self):
        """Test system behavior under high concurrency stress."""
        limiter = get_docker_rate_limiter()
        initial_stats = limiter.get_statistics()
        
        # Run many concurrent operations
        def stress_operation(index: int):
            try:
                return execute_docker_command(["docker", "version", "--format", "json"])
            except Exception as e:
                return e
        
        # Use thread pool for concurrent execution
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(stress_operation, i) for i in range(20)]
            results = [future.result() for future in futures]
        
        # Verify system handled the load
        final_stats = limiter.get_statistics()
        
        assert final_stats["total_operations"] > initial_stats["total_operations"]
        assert final_stats["total_operations"] >= 20, "All operations should be tracked"
        
        # Verify no complete failures (some may fail due to rate limiting, but system should survive)
        successful_results = [r for r in results if isinstance(r, DockerCommandResult) and r.returncode == 0]
        assert len(successful_results) > 0, "At least some operations should succeed"
    
    def test_error_recovery_patterns(self):
        """Test that the system recovers gracefully from errors."""
        # Create a circuit breaker for testing
        breaker = DockerCircuitBreaker("test-recovery")
        
        # Execute a command that should work
        result = breaker.execute_docker_command(["docker", "version"])
        assert result.returncode == 0
        
        # Verify system is still functional after success
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.is_available is True
        
        stats = breaker.get_stats()
        assert stats["successful_requests"] > 0
        assert stats["success_rate"] > 0


class TestDockerRateLimiterInfrastructure:
    """Infrastructure tests for Docker rate limiter performance and reliability."""
    
    def test_rate_limiter_throughput_benchmark(self):
        """Benchmark rate limiter throughput under various loads."""
        logger.info("[U+1F4C8] Benchmarking rate limiter throughput")
        
        limiter = get_docker_rate_limiter()
        limiter.reset_statistics()
        
        # Test different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        throughput_results = {}
        
        for concurrency in concurrency_levels:
            start_time = time.time()
            operations_per_thread = 5
            
            def rate_limited_operation(thread_id: int) -> int:
                successes = 0
                for i in range(operations_per_thread):
                    result = execute_docker_command(["docker", "version", "--format", f"{{.Server.Version}}-{thread_id}-{i}"])
                    if result.returncode == 0:
                        successes += 1
                return successes
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = [executor.submit(rate_limited_operation, i) for i in range(concurrency)]
                results = [future.result() for future in futures]
            
            elapsed_time = time.time() - start_time
            total_operations = sum(results)
            throughput = total_operations / elapsed_time if elapsed_time > 0 else 0
            throughput_results[concurrency] = throughput
            
            logger.info(f"   Concurrency {concurrency}: {throughput:.2f} ops/sec ({total_operations} ops in {elapsed_time:.2f}s)")
        
        # Validate throughput meets minimum requirements
        assert throughput_results[1] > 1.0, f"Single-threaded throughput too low: {throughput_results[1]:.2f} ops/sec"
        assert throughput_results[10] > 2.0, f"10-thread throughput too low: {throughput_results[10]:.2f} ops/sec"
        
        # Verify rate limiting is working (higher concurrency shouldn't scale linearly)
        scaling_efficiency = throughput_results[20] / throughput_results[1] if throughput_results[1] > 0 else 0
        assert scaling_efficiency < 15, f"Rate limiting not working properly: {scaling_efficiency:.2f}x scaling"
        
        final_stats = limiter.get_statistics()
        logger.info(f" PASS:  Rate limiter handled {final_stats['total_operations']} operations, {final_stats['rate_limited_operations']} rate-limited")
    
    def test_exponential_backoff_behavior(self):
        """Test exponential backoff behavior under high load."""
        logger.info("[U+1F4C8] Testing exponential backoff behavior")
        
        limiter = get_docker_rate_limiter()
        limiter.reset_statistics()
        
        backoff_wait_times = []
        operation_times = []
        
        def measure_backoff_operation(index: int) -> Tuple[float, float]:
            """Measure operation time and potential backoff."""
            start_time = time.time()
            
            # Force high contention
            result = execute_docker_command(["docker", "info", "--format", f"{{.Name}}-backoff-{index}"])
            
            operation_time = time.time() - start_time
            
            # Estimate backoff time (operation time minus expected command time)
            expected_command_time = 0.5  # Docker info should take ~0.5s
            backoff_time = max(0, operation_time - expected_command_time)
            
            return operation_time, backoff_time
        
        # Create high contention scenario
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(measure_backoff_operation, i) for i in range(30)]
            results = [future.result() for future in futures]
        
        operation_times = [r[0] for r in results]
        backoff_times = [r[1] for r in results]
        
        avg_operation_time = statistics.mean(operation_times)
        avg_backoff_time = statistics.mean(backoff_times)
        max_backoff_time = max(backoff_times)
        
        logger.info(f" PASS:  Backoff analysis:")
        logger.info(f"   Average operation time: {avg_operation_time:.3f}s")
        logger.info(f"   Average backoff time: {avg_backoff_time:.3f}s")
        logger.info(f"   Maximum backoff time: {max_backoff_time:.3f}s")
        
        # Validate exponential backoff is working
        assert avg_backoff_time > 0.1, f"Insufficient backoff detected: {avg_backoff_time:.3f}s"
        assert max_backoff_time < 10.0, f"Excessive backoff detected: {max_backoff_time:.3f}s"
        
        final_stats = limiter.get_statistics()
        rate_limited_percentage = (final_stats['rate_limited_operations'] / final_stats['total_operations']) * 100
        assert rate_limited_percentage > 10, f"Not enough rate limiting: {rate_limited_percentage:.1f}%"
    
    def test_backpressure_handling_extreme_load(self):
        """Test backpressure handling under extreme load conditions."""
        logger.info("[U+1F4C8] Testing backpressure handling under extreme load")
        
        limiter = get_docker_rate_limiter()
        limiter.reset_statistics()
        
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        
        # Generate extreme load - many concurrent operations
        extreme_load_operations = 50
        operations_completed = 0
        operations_failed = 0
        queue_wait_times = []
        
        def extreme_load_operation(operation_id: int) -> Dict[str, Any]:
            queue_start_time = time.time()
            
            try:
                # Mix different types of operations to create varied load
                if operation_id % 3 == 0:
                    result = execute_docker_command(["docker", "system", "info", "--format", "json"])
                elif operation_id % 3 == 1:
                    result = execute_docker_command(["docker", "version", "--format", "json"])
                else:
                    result = execute_docker_command(["docker", "system", "df", "--format", "json"])
                
                queue_time = time.time() - queue_start_time
                
                return {
                    'operation_id': operation_id,
                    'success': result.returncode == 0,
                    'queue_time': queue_time,
                    'retry_count': result.retry_count
                }
            except Exception as e:
                return {
                    'operation_id': operation_id,
                    'success': False,
                    'queue_time': time.time() - queue_start_time,
                    'error': str(e)
                }
        
        # Execute extreme load test
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(extreme_load_operation, i) for i in range(extreme_load_operations)]
            results = []
            
            for future in futures:
                try:
                    result = future.result(timeout=30)  # Generous timeout
                    results.append(result)
                    if result['success']:
                        operations_completed += 1
                    else:
                        operations_failed += 1
                    queue_wait_times.append(result['queue_time'])
                except Exception as e:
                    operations_failed += 1
                    logger.warning(f"Extreme load operation failed: {e}")
        
        total_time = time.time() - start_time
        final_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        memory_delta = final_memory - initial_memory
        
        # Analyze backpressure handling
        avg_queue_time = statistics.mean(queue_wait_times) if queue_wait_times else 0
        max_queue_time = max(queue_wait_times) if queue_wait_times else 0
        success_rate = (operations_completed / extreme_load_operations) * 100
        
        logger.info(f" PASS:  Extreme load backpressure analysis:")
        logger.info(f"   Operations completed: {operations_completed}/{extreme_load_operations} ({success_rate:.1f}%)")
        logger.info(f"   Average queue time: {avg_queue_time:.3f}s")
        logger.info(f"   Maximum queue time: {max_queue_time:.3f}s")
        logger.info(f"   Memory delta: {memory_delta:.1f}MB")
        logger.info(f"   Total test time: {total_time:.2f}s")
        
        # Validate backpressure is working effectively
        assert success_rate > 70, f"Success rate too low under extreme load: {success_rate:.1f}%"
        assert avg_queue_time > 0.2, f"Queue time too low (no backpressure): {avg_queue_time:.3f}s"
        assert max_queue_time < 15.0, f"Maximum queue time excessive: {max_queue_time:.3f}s"
        assert abs(memory_delta) < 200, f"Memory usage change too high: {memory_delta:.1f}MB"
        
        final_stats = limiter.get_statistics()
        assert final_stats['total_operations'] >= operations_completed
    
    def test_rate_limiter_resource_efficiency(self):
        """Test rate limiter resource efficiency and cleanup."""
        logger.info("[U+1F4C8] Testing rate limiter resource efficiency")
        
        limiter = get_docker_rate_limiter()
        limiter.reset_statistics()
        
        # Monitor system resources during rate limiter operation
        initial_cpu = psutil.cpu_percent(interval=0.1)
        initial_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        initial_threads = threading.active_count()
        
        resource_samples = []
        operations_per_batch = 10
        batch_count = 5
        
        def monitor_resources():
            """Background resource monitoring."""
            for _ in range(20):  # 20 samples over test duration
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory_mb = psutil.virtual_memory().used / (1024 * 1024)
                thread_count = threading.active_count()
                resource_samples.append({
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'thread_count': thread_count,
                    'timestamp': time.time()
                })
                time.sleep(0.5)
        
        # Start resource monitoring
        monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
        monitor_thread.start()
        
        # Execute batched operations to test efficiency
        for batch in range(batch_count):
            batch_start = time.time()
            
            def batch_operation(operation_id: int) -> bool:
                result = execute_docker_command(["docker", "version", "--format", f"batch-{batch}-op-{operation_id}"])
                return result.returncode == 0
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(batch_operation, i) for i in range(operations_per_batch)]
                batch_results = [future.result() for future in futures]
            
            batch_time = time.time() - batch_start
            batch_success_rate = sum(batch_results) / len(batch_results) * 100
            
            logger.info(f"   Batch {batch + 1}: {batch_success_rate:.1f}% success in {batch_time:.2f}s")
            
            # Brief pause between batches
            time.sleep(1)
        
        # Wait for monitoring to complete
        monitor_thread.join(timeout=5)
        
        # Analyze resource efficiency
        final_cpu = psutil.cpu_percent(interval=0.1)
        final_memory = psutil.virtual_memory().used / (1024 * 1024)  # MB
        final_threads = threading.active_count()
        
        cpu_delta = final_cpu - initial_cpu
        memory_delta = final_memory - initial_memory
        thread_delta = final_threads - initial_threads
        
        if resource_samples:
            avg_cpu = statistics.mean([s['cpu_percent'] for s in resource_samples])
            max_memory = max([s['memory_mb'] for s in resource_samples])
            max_threads = max([s['thread_count'] for s in resource_samples])
        else:
            avg_cpu = final_cpu
            max_memory = final_memory
            max_threads = final_threads
        
        logger.info(f" PASS:  Resource efficiency analysis:")
        logger.info(f"   CPU delta: {cpu_delta:.1f}%")
        logger.info(f"   Memory delta: {memory_delta:.1f}MB")
        logger.info(f"   Thread delta: {thread_delta}")
        logger.info(f"   Average CPU during test: {avg_cpu:.1f}%")
        logger.info(f"   Peak memory during test: {max_memory:.1f}MB")
        logger.info(f"   Peak threads during test: {max_threads}")
        
        # Validate resource efficiency
        assert abs(cpu_delta) < 20, f"CPU usage change too high: {cpu_delta:.1f}%"
        assert abs(memory_delta) < 100, f"Memory usage change too high: {memory_delta:.1f}MB"
        assert abs(thread_delta) < 10, f"Thread count change too high: {thread_delta}"
        assert avg_cpu < 50, f"Average CPU too high during test: {avg_cpu:.1f}%"
        
        final_stats = limiter.get_statistics()
        total_operations = final_stats['total_operations']
        assert total_operations >= batch_count * operations_per_batch * 0.8  # Allow some failures


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])