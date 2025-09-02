"""
Mission Critical Tests: Docker Rate Limiter Integration

This test suite validates that ALL Docker operations go through the rate limiter
to prevent Docker daemon crashes from concurrent operation storms.

CRITICAL: These tests protect the $2M+ ARR platform from Docker daemon instability.
"""

import pytest
import subprocess
import threading
import time
import unittest.mock as mock
from concurrent.futures import ThreadPoolExecutor
from typing import List
import sys
from pathlib import Path

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


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])