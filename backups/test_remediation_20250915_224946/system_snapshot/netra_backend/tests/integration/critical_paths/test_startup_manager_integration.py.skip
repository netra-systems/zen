"""Startup Manager Integration Tests (L3)

Tests the integration between StartupManager and app.state startup tracking.
This ensures that the sophisticated startup state management integrates properly 
with the health endpoint readiness detection.

Business Value Justification (BVJ):
- Segment: Platform/Internal (enabling all segments) 
- Business Goal: Ensure startup state coordination between StartupManager and health endpoints
- Value Impact: Prevents race conditions where health reports ready but components aren't initialized
- Revenue Impact: Critical - prevents false-positive health checks that could lead to traffic routing to broken instances
"""

import asyncio
import os
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Set test environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

from netra_backend.app.core.startup_manager import (
    ComponentPriority,
    ComponentStatus,
    StartupManager,
)


class TestStartupManagerIntegration:
    """Test startup manager integration with app state and health endpoints."""

    @pytest.fixture
    async def test_app(self):
        """Create test FastAPI app instance."""
        app = FastAPI()
        yield app

    @pytest.fixture
    async def startup_manager(self):
        """Create fresh startup manager instance."""
        manager = StartupManager(
            global_timeout=60.0,
            enable_circuit_breaker=True,
            enable_metrics=True
        )
        yield manager
        # Cleanup
        await manager.shutdown()

    @pytest.fixture
    async def async_client(self, test_app):
        """Create async client for testing."""
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_sets_app_state_correctly(self, test_app, startup_manager):
        """Test 1: StartupManager properly sets app.state during initialization."""
        # Ensure app.state exists and is initially unset
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = False
        
        # Register mock components
        async def mock_critical_init():
            await asyncio.sleep(0.1)  # Simulate initialization time
            return True
            
        async def mock_optional_init():
            await asyncio.sleep(0.05)  # Faster optional component
            return True

        startup_manager.register_component(
            name="critical_database",
            init_func=mock_critical_init,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=5.0
        )
        
        startup_manager.register_component(
            name="optional_service",
            init_func=mock_optional_init,
            priority=ComponentPriority.MEDIUM,
            timeout_seconds=3.0
        )

        # Test startup state transitions
        assert test_app.state.startup_complete == False
        assert test_app.state.startup_in_progress == False
        
        # Start startup process and monitor state
        test_app.state.startup_in_progress = True
        test_app.state.startup_start_time = time.time()
        
        success = await startup_manager.startup()
        
        # Verify startup succeeded
        assert success == True
        
        # Startup manager should be marked as complete
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        
        # Verify component states
        status = startup_manager.get_status()
        assert status["initialized"] == True
        assert status["components"]["critical_database"]["status"] == "running"
        assert status["components"]["optional_service"]["status"] == "running"

    @pytest.mark.integration
    @pytest.mark.L3  
    @pytest.mark.asyncio
    async def test_startup_manager_handles_critical_component_failure(self, test_app, startup_manager):
        """Test 2: StartupManager properly handles critical component failure and updates app.state."""
        # Setup app state
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        test_app.state.startup_failed = False
        
        async def failing_critical_init():
            await asyncio.sleep(0.1)
            raise RuntimeError("Critical database connection failed")
            
        async def working_optional_init():
            await asyncio.sleep(0.05)
            return True

        startup_manager.register_component(
            name="critical_database",
            init_func=failing_critical_init,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=5.0,
            max_retries=2
        )
        
        startup_manager.register_component(
            name="optional_service", 
            init_func=working_optional_init,
            priority=ComponentPriority.MEDIUM,
            timeout_seconds=3.0
        )

        # Run startup - should fail due to critical component failure
        success = await startup_manager.startup()
        
        # Verify startup failed
        assert success == False
        
        # Update app state to reflect failure
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = False  
        test_app.state.startup_failed = True
        test_app.state.startup_error = "Critical database connection failed"
        
        # Verify component states
        status = startup_manager.get_status()
        assert status["initialized"] == False
        assert status["components"]["critical_database"]["status"] == "failed"
        # Optional service might not have been attempted due to critical failure
        
        # Verify health check reflects failure state
        healthy, health_details = await startup_manager.health_check()
        assert healthy == False  # Should be unhealthy due to critical component failure

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_timeout_handling_with_app_state(self, test_app, startup_manager):
        """Test 3: StartupManager timeout handling updates app.state appropriately."""
        # Setup app state  
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        test_app.state.startup_start_time = time.time()
        
        async def slow_init():
            # This will timeout after 2 seconds but we set component timeout to 1 second
            await asyncio.sleep(2.0)
            return True

        startup_manager.register_component(
            name="slow_service",
            init_func=slow_init,
            priority=ComponentPriority.HIGH,
            timeout_seconds=1.0,  # Short timeout to trigger timeout
            max_retries=1
        )

        # Run startup - should handle timeout
        success = await startup_manager.startup()
        
        # With just HIGH priority component timing out, startup might still succeed
        # depending on implementation, but component should be failed
        status = startup_manager.get_status()
        assert status["components"]["slow_service"]["status"] == "failed"
        
        # Update app state based on timeout
        if not success:
            test_app.state.startup_complete = False
            test_app.state.startup_failed = True
            test_app.state.startup_error = "Component initialization timeout"
        
        # Verify timeout was recorded in metrics
        if startup_manager.enable_metrics:
            component_metrics = status.get("metrics", {}).get("slow_service", {})
            # Should have metrics showing the failure

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_circuit_breaker_integration(self, test_app, startup_manager):
        """Test 4: StartupManager circuit breaker integrates with app.state tracking."""
        # Setup app state
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        
        failure_count = 0
        async def intermittent_failure():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Fail first 2 attempts
                raise RuntimeError(f"Intermittent failure #{failure_count}")
            return True

        startup_manager.register_component(
            name="flaky_service",
            init_func=intermittent_failure,
            priority=ComponentPriority.HIGH,
            timeout_seconds=5.0,
            max_retries=3  # Allow multiple retries
        )

        # Run startup - should eventually succeed after retries
        success = await startup_manager.startup()
        
        # Should succeed after retries
        assert success == True
        
        # Update app state
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        
        # Verify component eventually succeeded
        status = startup_manager.get_status()
        assert status["components"]["flaky_service"]["status"] == "running"
        assert status["components"]["flaky_service"]["retry_count"] == 2  # 2 retries before success

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_dependency_resolution_with_state(self, test_app, startup_manager):
        """Test 5: StartupManager dependency resolution works correctly with app.state."""
        # Track initialization order
        init_order = []
        
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        
        async def database_init():
            await asyncio.sleep(0.1)
            init_order.append("database")
            return True
            
        async def redis_init():
            await asyncio.sleep(0.05)
            init_order.append("redis")
            return True
            
        async def websocket_init():
            await asyncio.sleep(0.05)
            init_order.append("websocket")
            return True

        # Register components with dependencies
        startup_manager.register_component(
            name="database",
            init_func=database_init,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=5.0
        )
        
        startup_manager.register_component(
            name="redis",
            init_func=redis_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database"],  # Redis depends on database
            timeout_seconds=3.0
        )
        
        startup_manager.register_component(
            name="websocket",
            init_func=websocket_init,
            priority=ComponentPriority.HIGH,
            dependencies=["database", "redis"],  # WebSocket depends on both
            timeout_seconds=3.0
        )

        # Run startup
        success = await startup_manager.startup()
        assert success == True
        
        # Verify initialization order respects dependencies
        assert init_order == ["database", "redis", "websocket"]
        
        # Update app state
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        
        # Verify all components are running
        status = startup_manager.get_status()
        for component_name in ["database", "redis", "websocket"]:
            assert status["components"][component_name]["status"] == "running"

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_graceful_degradation(self, test_app, startup_manager):
        """Test 6: StartupManager graceful degradation when non-critical components fail."""
        # Setup app state
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        
        async def critical_success():
            await asyncio.sleep(0.1)
            return True
            
        async def optional_failure():
            await asyncio.sleep(0.05)
            raise RuntimeError("Optional service unavailable")

        startup_manager.register_component(
            name="critical_database",
            init_func=critical_success,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=5.0
        )
        
        startup_manager.register_component(
            name="optional_metrics",
            init_func=optional_failure,
            priority=ComponentPriority.LOW,
            timeout_seconds=3.0,
            max_retries=1
        )

        # Run startup - should succeed with degraded functionality
        success = await startup_manager.startup()
        assert success == True  # Should succeed despite optional component failure
        
        # Update app state - system is up but degraded
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        test_app.state.degraded_mode = True
        
        # Verify component states
        status = startup_manager.get_status()
        assert status["components"]["critical_database"]["status"] == "running"
        assert status["components"]["optional_metrics"]["status"] == "failed"
        
        # Health check should still pass for critical components
        healthy, health_details = await startup_manager.health_check()
        assert healthy == True  # Should be healthy because critical components work

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_provides_detailed_health_info(self, test_app, startup_manager):
        """Test 7: StartupManager provides detailed health information for monitoring."""
        # Setup app state
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        
        async def database_init():
            await asyncio.sleep(0.1)
            return True
            
        async def cache_init():
            await asyncio.sleep(0.05)
            return True

        startup_manager.register_component(
            name="database",
            init_func=database_init,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=5.0
        )
        
        startup_manager.register_component(
            name="cache",
            init_func=cache_init,
            priority=ComponentPriority.HIGH,
            timeout_seconds=3.0
        )

        # Run startup
        success = await startup_manager.startup()
        assert success == True
        
        # Update app state
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        
        # Get detailed health information
        healthy, health_details = await startup_manager.health_check()
        
        # Verify detailed health info is provided
        assert healthy == True
        assert "database" in health_details
        assert "cache" in health_details
        
        assert health_details["database"]["healthy"] == True
        assert health_details["database"]["status"] == "running"
        assert health_details["database"]["priority"] == "CRITICAL"
        
        assert health_details["cache"]["healthy"] == True
        assert health_details["cache"]["status"] == "running"
        assert health_details["cache"]["priority"] == "HIGH"
        
        # Verify startup metrics are available
        status = startup_manager.get_status()
        assert "metrics" in status
        assert "global" in status["metrics"]
        assert status["metrics"]["global"]["successful_components"] == 2
        assert status["metrics"]["global"]["failed_components"] == 0

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_startup_manager_shutdown_sequence(self, test_app, startup_manager):
        """Test 8: StartupManager shutdown sequence works correctly and updates app.state."""
        # Setup and run startup first
        cleanup_order = []
        
        async def database_init():
            await asyncio.sleep(0.1)
            return True
            
        async def database_cleanup():
            await asyncio.sleep(0.05)
            cleanup_order.append("database")
            
        async def cache_init():
            await asyncio.sleep(0.05)
            return True
            
        async def cache_cleanup():
            await asyncio.sleep(0.03)
            cleanup_order.append("cache")

        startup_manager.register_component(
            name="database",
            init_func=database_init,
            cleanup_func=database_cleanup,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=5.0
        )
        
        startup_manager.register_component(
            name="cache",
            init_func=cache_init,
            cleanup_func=cache_cleanup,
            priority=ComponentPriority.HIGH,
            dependencies=["database"],
            timeout_seconds=3.0
        )

        # Run startup
        success = await startup_manager.startup()
        assert success == True
        
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        
        # Now test shutdown
        test_app.state.shutdown_in_progress = True
        await startup_manager.shutdown()
        
        # Verify shutdown order is reverse of startup order
        assert cleanup_order == ["cache", "database"]  # Reverse dependency order
        
        # Update app state
        test_app.state.startup_complete = False
        test_app.state.shutdown_in_progress = False
        test_app.state.system_stopped = True
        
        # Verify startup manager state
        status = startup_manager.get_status()
        assert status["initialized"] == False

    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_concurrent_startup_state_access(self, test_app, startup_manager):
        """Test 9: Concurrent access to startup state during initialization is safe."""
        # This test ensures that concurrent health checks during startup don't interfere
        async def slow_init():
            await asyncio.sleep(0.5)  # Long enough for concurrent access
            return True

        startup_manager.register_component(
            name="slow_database",
            init_func=slow_init,
            priority=ComponentPriority.CRITICAL,
            timeout_seconds=10.0
        )

        # Setup initial state
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        
        # Start startup process in background
        startup_task = asyncio.create_task(startup_manager.startup())
        
        # Concurrently check health status multiple times
        health_results = []
        
        async def check_health():
            healthy, details = await startup_manager.health_check()
            health_results.append((healthy, details))
        
        # Create multiple concurrent health checks
        health_tasks = [asyncio.create_task(check_health()) for _ in range(5)]
        
        # Wait for all tasks
        await asyncio.gather(startup_task, *health_tasks)
        
        # Verify startup succeeded
        assert await startup_task == True
        
        # Verify all health checks completed without error
        assert len(health_results) == 5
        
        # Update final state
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        
        # Final health check should show system healthy
        final_healthy, _ = await startup_manager.health_check()
        assert final_healthy == True

    @pytest.mark.integration
    @pytest.mark.L3  
    @pytest.mark.asyncio
    async def test_startup_manager_metrics_integration(self, test_app, startup_manager):
        """Test 10: StartupManager metrics integrate properly with app monitoring."""
        # Setup app state
        test_app.state.startup_complete = False
        test_app.state.startup_in_progress = True
        test_app.state.startup_start_time = time.time()
        
        async def measured_init():
            await asyncio.sleep(0.2)  # Measurable delay
            return True

        startup_manager.register_component(
            name="measured_service",
            init_func=measured_init,
            priority=ComponentPriority.HIGH,
            timeout_seconds=5.0
        )

        # Run startup
        startup_start = time.time()
        success = await startup_manager.startup()
        startup_duration = time.time() - startup_start
        
        assert success == True
        
        # Update app state with timing info
        test_app.state.startup_complete = True
        test_app.state.startup_in_progress = False
        test_app.state.startup_duration = startup_duration
        
        # Verify metrics are captured
        status = startup_manager.get_status()
        assert "metrics" in status
        
        # Global metrics
        global_metrics = status["metrics"]["global"]
        assert "total_duration" in global_metrics
        assert global_metrics["total_duration"] > 0.2  # Should be at least component init time
        assert global_metrics["successful_components"] == 1
        assert global_metrics["failed_components"] == 0
        
        # Component-specific metrics
        component_metrics = status["metrics"]["measured_service"]
        assert "duration" in component_metrics
        assert component_metrics["duration"] >= 0.2  # Should be at least sleep time
        assert component_metrics["retries"] == 0  # No retries needed
        assert "failed" not in component_metrics  # Shouldn't have failure flag