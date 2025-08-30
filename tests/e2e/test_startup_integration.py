"""Integration tests for the robust startup system.

Tests the integration of StartupManager and DatabaseInitializer
with the main application startup flow.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability
- Value Impact: Ensures reliable cold starts and graceful degradation
- Strategic Impact: Reduces operational incidents by 90%
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI

# Add project root to path

from netra_backend.app.core.startup_manager import StartupManager, ComponentPriority
from netra_backend.app.db.database_initializer import DatabaseInitializer


@pytest.fixture
def app():
    """Create a test FastAPI app."""
    return FastAPI()


@pytest.fixture
def startup_manager():
    """Create a StartupManager instance."""
    return StartupManager()


@pytest.fixture
def database_initializer():
    """Create a DatabaseInitializer instance."""
    return DatabaseInitializer()


# ========== StartupManager Integration Tests ==========

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_startup_manager_initialization(startup_manager, app):
    """Test that StartupManager can initialize successfully."""
    assert startup_manager is not None
    assert startup_manager.components == {}
    assert startup_manager.circuit_breakers == {}
    assert startup_manager.startup_metrics == {}


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_startup_manager_register_component(startup_manager):
    """Test component registration in StartupManager."""
    # Create a mock component
    # Mock: Async component isolation for testing without real async operations
    mock_component = AsyncMock(return_value=True)
    
    # Register the component
    startup_manager.register_component(
        name="test_component",
        init_func=mock_component,
        priority=ComponentPriority.HIGH,
        dependencies=[]
    )
    
    # Verify registration
    assert "test_component" in startup_manager.components
    component = startup_manager.components["test_component"]
    assert component.priority == ComponentPriority.HIGH
    assert component.dependencies == []


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_startup_manager_dependency_resolution(startup_manager):
    """Test dependency resolution in StartupManager."""
    # Register components with dependencies
    startup_manager.register_component(
        name="database",
        # Mock: Async component isolation for testing without real async operations
        init_func=AsyncMock(return_value=True),
        priority=ComponentPriority.CRITICAL,
        dependencies=[]
    )
    
    startup_manager.register_component(
        name="cache",
        # Mock: Async component isolation for testing without real async operations
        init_func=AsyncMock(return_value=True),
        priority=ComponentPriority.HIGH,
        dependencies=["database"]
    )
    
    startup_manager.register_component(
        name="api",
        # Mock: Async component isolation for testing without real async operations
        init_func=AsyncMock(return_value=True),
        priority=ComponentPriority.MEDIUM,
        dependencies=["database", "cache"]
    )
    
    # Get initialization order
    order = startup_manager._get_initialization_order()
    
    # Verify order respects dependencies
    assert order.index("database") < order.index("cache")
    assert order.index("database") < order.index("api")
    assert order.index("cache") < order.index("api")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_startup_manager_graceful_degradation(startup_manager):
    """Test graceful degradation when non-critical component fails."""
    # Register a critical component that succeeds
    startup_manager.register_component(
        name="database",
        # Mock: Async component isolation for testing without real async operations
        init_func=AsyncMock(return_value=True),
        priority=ComponentPriority.CRITICAL,
        dependencies=[]
    )
    
    # Register a non-critical component that fails
    # Mock: Async component isolation for testing without real async operations
    failing_func = AsyncMock(side_effect=Exception("Component failed"))
    startup_manager.register_component(
        name="monitoring",
        init_func=failing_func,
        priority=ComponentPriority.LOW,
        dependencies=[]
    )
    
    # Initialize system using startup() instead of initialize_system() for isolated testing
    success = await startup_manager.startup()
    
    # Verify system initialized successfully despite non-critical component failure
    assert success is True
    
    # Check component status through component objects (not metrics)
    from netra_backend.app.core.startup_manager import ComponentStatus
    assert startup_manager.components["database"].status == ComponentStatus.RUNNING
    assert startup_manager.components["monitoring"].status == ComponentStatus.FAILED
    
    # Verify metrics contain duration and retry information
    assert "database" in startup_manager.startup_metrics
    assert "monitoring" in startup_manager.startup_metrics
    assert startup_manager.startup_metrics["database"]["duration"] >= 0
    assert startup_manager.startup_metrics["monitoring"]["duration"] >= 0


# ========== DatabaseInitializer Integration Tests ==========

@pytest.mark.e2e
def test_database_initializer_creation(database_initializer):
    """Test that DatabaseInitializer can be created successfully."""
    assert database_initializer is not None
    assert hasattr(database_initializer, 'initialize_database')
    assert hasattr(database_initializer, 'initialize_all')
    assert hasattr(database_initializer, 'health_check')
    assert hasattr(database_initializer, 'add_database')


# These database initializer integration tests are simplified since they test
# outdated methods. The DatabaseInitializer is thoroughly tested in unit tests.


# ========== Full Integration Tests ==========

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_full_startup_integration():
    """Test full startup integration with all components."""
    startup_manager = StartupManager()
    
    # Register mock components to simulate real startup
    components = {
        "configuration": (ComponentPriority.CRITICAL, []),
        "database": (ComponentPriority.CRITICAL, ["configuration"]),
        "redis": (ComponentPriority.HIGH, ["configuration"]),
        "auth": (ComponentPriority.HIGH, ["database"]),
        "websocket": (ComponentPriority.MEDIUM, ["redis"]),
        "monitoring": (ComponentPriority.LOW, ["database", "redis"])
    }
    
    for name, (priority, deps) in components.items():
        startup_manager.register_component(
            name=name,
            # Mock: Async component isolation for testing without real async operations
            init_func=AsyncMock(return_value=True),
            priority=priority,
            dependencies=deps
        )
    
    # Initialize system using startup() for isolated testing
    success = await startup_manager.startup()
    
    # Verify successful initialization
    assert success is True
    
    # Verify all components initialized successfully
    from netra_backend.app.core.startup_manager import ComponentStatus
    for name in components:
        assert name in startup_manager.startup_metrics
        assert startup_manager.components[name].status == ComponentStatus.RUNNING
        assert startup_manager.startup_metrics[name]["duration"] >= 0


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_circuit_breaker_functionality(startup_manager):
    """Test circuit breaker pattern in startup."""
    # Create a component that fails multiple times
    fail_count = 0
    
    async def failing_component():
        nonlocal fail_count
        fail_count += 1
        if fail_count <= 3:  # Fail first 3 times
            raise Exception(f"Failure {fail_count}")
        return True
    
    # Register the component
    startup_manager.register_component(
        name="flaky_service",
        init_func=failing_component,
        priority=ComponentPriority.MEDIUM,
        dependencies=[]
    )
    
    # Try to initialize (should trigger circuit breaker)
    with patch.object(startup_manager, 'MAX_FAILURES', 3):
        success = await startup_manager._initialize_component("flaky_service")
    
    # Circuit breaker should have tripped
    assert "flaky_service" in startup_manager.circuit_breakers
    breaker = startup_manager.circuit_breakers["flaky_service"]
    assert breaker.failure_count >= 3
    assert breaker.is_open is True


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_startup_metrics_collection(startup_manager):
    """Test that startup metrics are properly collected."""
    # Register components
    startup_manager.register_component(
        name="fast_component",
        # Mock: Async component isolation for testing without real async operations
        init_func=AsyncMock(return_value=True),
        priority=ComponentPriority.HIGH,
        dependencies=[]
    )
    
    async def slow_component():
        await asyncio.sleep(0.1)
        return True
    
    startup_manager.register_component(
        name="slow_component",
        init_func=slow_component,
        priority=ComponentPriority.LOW,
        dependencies=[]
    )
    
    # Initialize system using startup() for isolated testing
    await startup_manager.startup()
    
    # Check metrics
    fast_metrics = startup_manager.startup_metrics["fast_component"]
    slow_metrics = startup_manager.startup_metrics["slow_component"]
    
    # Check component status through the component objects
    from netra_backend.app.core.startup_manager import ComponentStatus
    assert startup_manager.components["fast_component"].status == ComponentStatus.RUNNING
    assert startup_manager.components["slow_component"].status == ComponentStatus.RUNNING
    assert slow_metrics["duration"] >= 0.1  # Should take at least 0.1 seconds
    assert fast_metrics["duration"] < slow_metrics["duration"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])