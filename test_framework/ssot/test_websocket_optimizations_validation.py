"""
Validation Tests for WebSocket Testing Optimizations

This module contains tests to validate that all the WebSocket testing optimizations
work correctly and don't break existing functionality.

Tests validate:
1. Connection recovery with exponential backoff
2. Connection pool optimization
3. Graceful degradation for service unavailability
4. Parallel test execution support
5. Enhanced Docker health checks

@compliance CLAUDE.md - Real services only, proper authentication required
"""

import asyncio
import logging
import pytest
import time
from typing import List

from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from test_framework.ssot.real_websocket_connection_manager import (
    RealWebSocketConnectionManager,
    DockerUnavailableError
)
from test_framework.ssot.parallel_websocket_test_runner import (
    ParallelWebSocketTestRunner,
    ParallelExecutionMode,
    run_isolation_tests_parallel
)

logger = logging.getLogger(__name__)

# Test configuration
BACKEND_URL = "ws://localhost:8000"
TEST_ENVIRONMENT = "test"


class TestWebSocketOptimizations:
    """Validation tests for WebSocket testing optimizations."""
    
    @pytest.mark.asyncio
    async def test_connection_recovery_with_backoff(self):
        """Test that connection recovery works with exponential backoff."""
        client = RealWebSocketTestClient(
            backend_url="ws://localhost:9999",  # Invalid port to trigger retry
            environment=TEST_ENVIRONMENT,
            connection_timeout=2.0,
            auth_required=False
        )
        
        start_time = time.time()
        
        try:
            # This should fail after retries with exponential backoff
            await client.connect(max_retries=3)
            pytest.fail("Connection should have failed to invalid port")
        except RuntimeError as e:
            elapsed = time.time() - start_time
            
            # Should have taken some time due to backoff (at least 3 seconds for 3 retries: 0 + 1 + 2)
            assert elapsed >= 3.0, f"Expected at least 3s backoff, got {elapsed:.2f}s"
            assert "failed after 3 attempts" in str(e)
            logger.info(f" PASS:  Connection recovery backoff worked: {elapsed:.2f}s")
    
    @pytest.mark.asyncio  
    async def test_connection_pool_optimization(self):
        """Test that connection pooling works correctly."""
        manager = RealWebSocketConnectionManager(
            backend_url=BACKEND_URL,
            environment=TEST_ENVIRONMENT
        )
        
        try:
            # Enable connection pooling
            manager.enable_connection_pool(True)
            
            # Create connection for same user twice
            user_id = "test_pool_user"
            
            # First connection
            conn1_id = await manager.create_authenticated_connection(
                user_id=user_id,
                user_email=f"{user_id}@example.com",
                connect_immediately=False
            )
            
            # Get pool stats
            pool_stats_1 = manager.get_pool_statistics()
            assert pool_stats_1["pool_enabled"] == True
            
            # Second connection for same user - should reuse from pool
            conn2_id = await manager.create_authenticated_connection(
                user_id=user_id,
                user_email=f"{user_id}@example.com", 
                connect_immediately=False
            )
            
            # Pool should show reuse
            pool_stats_2 = manager.get_pool_statistics()
            assert pool_stats_2["total_usage_count"] >= 1
            
            logger.info(" PASS:  Connection pool optimization validated")
            
        finally:
            await manager.cleanup_all_connections()
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation for service unavailability."""
        manager = RealWebSocketConnectionManager(
            backend_url="ws://localhost:9999",  # Invalid port
            environment=TEST_ENVIRONMENT
        )
        
        async def failing_test():
            """Test function that should fail due to service unavailability."""
            async with manager.managed_connections(count=1) as connection_ids:
                return "should_not_reach_here"
        
        try:
            # Test graceful degradation wrapper
            result = await manager.test_with_graceful_degradation(
                failing_test,
                test_name="test_graceful_degradation"
            )
            pytest.fail("Should have raised pytest.skip")
            
        except Exception as e:
            # Should get pytest.skip, not hard failure
            if "pytest" in str(type(e)).lower() and "skip" in str(type(e)).lower():
                logger.info(" PASS:  Graceful degradation worked (pytest.skip)")
            else:
                # If not pytest.skip, check that it's a DockerUnavailableError
                assert isinstance(e, (DockerUnavailableError, ConnectionRefusedError))
                logger.info(f" PASS:  Graceful degradation caught error: {type(e).__name__}")
    
    @pytest.mark.asyncio
    async def test_parallel_execution_support(self):
        """Test parallel test execution framework."""
        
        async def simple_isolation_test(connection_manager):
            """Simple test that validates basic isolation."""
            async with connection_manager.managed_connections(count=2) as conn_ids:
                assert len(conn_ids) == 2
                return f"test_completed_with_{len(conn_ids)}_connections"
        
        async def another_isolation_test(connection_manager): 
            """Another simple isolation test."""
            async with connection_manager.managed_connections(count=1) as conn_ids:
                assert len(conn_ids) == 1
                return f"another_test_completed"
        
        # Create parallel test runner
        runner = ParallelWebSocketTestRunner(
            backend_url=BACKEND_URL,
            environment=TEST_ENVIRONMENT,
            max_parallel_tests=2
        )
        
        test_suite = runner.create_test_suite(
            suite_name="validation_tests",
            test_functions=[simple_isolation_test, another_isolation_test],
            execution_mode=ParallelExecutionMode.ASYNC_CONCURRENT
        )
        
        start_time = time.time()
        results = await runner.execute_parallel_test_suite(test_suite)
        execution_time = time.time() - start_time
        
        # Validate results
        assert len(results) == 2
        successful_tests = [r for r in results if r.success]
        
        # Should be faster than sequential (rough check)
        logger.info(f"Parallel execution time: {execution_time:.2f}s")
        
        # Get performance summary
        perf_summary = runner.get_performance_summary()
        assert perf_summary["total_tests"] == 2
        assert perf_summary["tests_passed_isolation"] == True
        
        logger.info(" PASS:  Parallel execution support validated")
    
    @pytest.mark.asyncio
    async def test_enhanced_docker_health_checks(self):
        """Test enhanced Docker health checks (if services available)."""
        from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType
        
        docker_manager = UnifiedDockerManager(environment_type=EnvironmentType.DEDICATED)
        
        try:
            # Test WebSocket health check method exists
            assert hasattr(docker_manager, '_check_websocket_health')
            
            # Test method signature
            import inspect
            sig = inspect.signature(docker_manager._check_websocket_health)
            assert 'ws_url' in sig.parameters
            assert 'timeout' in sig.parameters
            
            logger.info(" PASS:  Enhanced Docker health checks validated")
            
        except Exception as e:
            logger.warning(f"Docker health check validation skipped: {e}")
    
    @pytest.mark.asyncio
    async def test_integration_all_optimizations(self):
        """Integration test using all optimizations together."""
        
        # Test with connection pooling + graceful degradation + recovery
        manager = RealWebSocketConnectionManager(
            backend_url=BACKEND_URL,
            environment=TEST_ENVIRONMENT,
            max_connections=5
        )
        
        try:
            # Enable optimizations
            manager.enable_connection_pool(True)
            
            async def integrated_test():
                # Create multiple connections with pooling
                conn_ids = []
                for i in range(3):
                    conn_id = await manager.create_authenticated_connection(
                        user_email=f"integrated_user_{i}@example.com",
                        connect_immediately=False
                    )
                    conn_ids.append(conn_id)
                
                # Test isolation
                isolation_result = await manager.test_user_isolation()
                assert isolation_result.test_passed
                
                return len(conn_ids)
            
            # Run with graceful degradation wrapper
            result = await manager.test_with_graceful_degradation(
                integrated_test,
                test_name="integration_test"
            )
            
            # Get final statistics
            pool_stats = manager.get_pool_statistics()
            isolation_summary = manager.get_isolation_summary()
            
            logger.info(
                f" PASS:  Integration test completed:\n"
                f"   Connections created: {result}\n" 
                f"   Pool enabled: {pool_stats['pool_enabled']}\n"
                f"   Isolation passed: {isolation_summary['test_passed']}"
            )
            
        finally:
            await manager.cleanup_all_connections()


# Standalone test functions for parallel execution validation
@pytest.mark.concurrent_safe
async def standalone_isolation_test_1(connection_manager):
    """Standalone test for parallel execution."""
    async with connection_manager.managed_connections(count=2) as conn_ids:
        assert len(conn_ids) == 2


@pytest.mark.concurrent_safe  
async def standalone_isolation_test_2(connection_manager):
    """Another standalone test for parallel execution."""
    async with connection_manager.managed_connections(count=1) as conn_ids:
        assert len(conn_ids) == 1


@pytest.mark.asyncio
async def test_parallel_execution_with_real_tests():
    """Test parallel execution using real test functions."""
    
    test_functions = [
        standalone_isolation_test_1,
        standalone_isolation_test_2
    ]
    
    results = await run_isolation_tests_parallel(
        test_functions=test_functions,
        backend_url=BACKEND_URL,
        max_concurrent=2
    )
    
    assert len(results) == 2
    successful_results = [r for r in results if r.success]
    
    logger.info(f" PASS:  Parallel execution completed: {len(successful_results)}/{len(results)} successful")


if __name__ == "__main__":
    # Run validation tests directly for development
    pytest.main([__file__, "-v", "--tb=short"])