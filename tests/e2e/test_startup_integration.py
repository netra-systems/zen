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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

# Add project root to path

from netra_backend.app.core.startup_manager import StartupManager
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
async def test_startup_manager_initialization(startup_manager, app):
    """Test that StartupManager can initialize successfully."""
    assert startup_manager is not None
    assert startup_manager.components == {}
    assert startup_manager.circuit_breakers == {}
    assert startup_manager.startup_metrics == {}


@pytest.mark.asyncio
async def test_startup_manager_register_component(startup_manager):
    """Test component registration in StartupManager."""
    # Create a mock component
    mock_component = AsyncMock(return_value=True)
    
    # Register the component
    startup_manager.register_component(
        name="test_component",
        init_func=mock_component,
        priority="HIGH",
        dependencies=[]
    )
    
    # Verify registration
    assert "test_component" in startup_manager.components
    component = startup_manager.components["test_component"]
    assert component["priority"] == "HIGH"
    assert component["dependencies"] == []


@pytest.mark.asyncio
async def test_startup_manager_dependency_resolution(startup_manager):
    """Test dependency resolution in StartupManager."""
    # Register components with dependencies
    startup_manager.register_component(
        name="database",
        init_func=AsyncMock(return_value=True),
        priority="CRITICAL",
        dependencies=[]
    )
    
    startup_manager.register_component(
        name="cache",
        init_func=AsyncMock(return_value=True),
        priority="HIGH",
        dependencies=["database"]
    )
    
    startup_manager.register_component(
        name="api",
        init_func=AsyncMock(return_value=True),
        priority="MEDIUM",
        dependencies=["database", "cache"]
    )
    
    # Get initialization order
    order = startup_manager._get_initialization_order()
    
    # Verify order respects dependencies
    assert order.index("database") < order.index("cache")
    assert order.index("database") < order.index("api")
    assert order.index("cache") < order.index("api")


@pytest.mark.asyncio
async def test_startup_manager_graceful_degradation(startup_manager, app):
    """Test graceful degradation when non-critical component fails."""
    # Register a critical component that succeeds
    startup_manager.register_component(
        name="database",
        init_func=AsyncMock(return_value=True),
        priority="CRITICAL",
        dependencies=[]
    )
    
    # Register a non-critical component that fails
    failing_func = AsyncMock(side_effect=Exception("Component failed"))
    startup_manager.register_component(
        name="monitoring",
        init_func=failing_func,
        priority="LOW",
        dependencies=[]
    )
    
    # Initialize system (should succeed despite monitoring failure)
    success = await startup_manager.initialize_system(app)
    
    # Verify system initialized successfully
    assert success is True
    assert startup_manager.startup_metrics["database"]["status"] == "SUCCESS"
    assert startup_manager.startup_metrics["monitoring"]["status"] == "FAILED"


# ========== DatabaseInitializer Integration Tests ==========

def test_database_initializer_creation(database_initializer):
    """Test that DatabaseInitializer can be created successfully."""
    assert database_initializer is not None
    assert hasattr(database_initializer, 'ensure_database_ready')
    assert hasattr(database_initializer, 'check_database_exists')


@patch('netra_backend.app.db.database_initializer.psycopg2.connect')
def test_database_initializer_check_exists(mock_connect, database_initializer):
    """Test database existence checking."""
    # Mock successful connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Test database exists check
    mock_cursor.fetchone.return_value = (True,)
    exists = database_initializer.check_database_exists("test_db")
    
    assert exists is True
    mock_cursor.execute.assert_called()


@patch('netra_backend.app.db.database_initializer.psycopg2.connect')
def test_database_initializer_create_database(mock_connect, database_initializer):
    """Test database creation."""
    # Mock connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_connect.return_value = mock_conn
    
    # Test database creation
    success = database_initializer.create_database("test_db")
    
    # Verify creation was attempted
    assert mock_cursor.execute.called


# ========== Full Integration Tests ==========

@pytest.mark.asyncio
async def test_full_startup_integration(app):
    """Test full startup integration with all components."""
    startup_manager = StartupManager()
    
    # Register mock components to simulate real startup
    components = {
        "configuration": ("CRITICAL", []),
        "database": ("CRITICAL", ["configuration"]),
        "redis": ("HIGH", ["configuration"]),
        "auth": ("HIGH", ["database"]),
        "websocket": ("MEDIUM", ["redis"]),
        "monitoring": ("LOW", ["database", "redis"])
    }
    
    for name, (priority, deps) in components.items():
        startup_manager.register_component(
            name=name,
            init_func=AsyncMock(return_value=True),
            priority=priority,
            dependencies=deps
        )
    
    # Initialize system
    success = await startup_manager.initialize_system(app)
    
    # Verify successful initialization
    assert success is True
    
    # Verify all components initialized
    for name in components:
        assert name in startup_manager.startup_metrics
        assert startup_manager.startup_metrics[name]["status"] == "SUCCESS"


@pytest.mark.asyncio
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
        priority="MEDIUM",
        dependencies=[]
    )
    
    # Try to initialize (should trigger circuit breaker)
    with patch.object(startup_manager, 'MAX_FAILURES', 3):
        success = await startup_manager._initialize_component("flaky_service")
    
    # Circuit breaker should have tripped
    assert "flaky_service" in startup_manager.circuit_breakers
    breaker = startup_manager.circuit_breakers["flaky_service"]
    assert breaker["failures"] >= 3
    assert breaker["is_open"] is True


@pytest.mark.asyncio
async def test_startup_metrics_collection(startup_manager, app):
    """Test that startup metrics are properly collected."""
    # Register components
    startup_manager.register_component(
        name="fast_component",
        init_func=AsyncMock(return_value=True),
        priority="HIGH",
        dependencies=[]
    )
    
    async def slow_component():
        await asyncio.sleep(0.1)
        return True
    
    startup_manager.register_component(
        name="slow_component",
        init_func=slow_component,
        priority="LOW",
        dependencies=[]
    )
    
    # Initialize system
    await startup_manager.initialize_system(app)
    
    # Check metrics
    fast_metrics = startup_manager.startup_metrics["fast_component"]
    slow_metrics = startup_manager.startup_metrics["slow_component"]
    
    assert fast_metrics["status"] == "SUCCESS"
    assert slow_metrics["status"] == "SUCCESS"
    assert slow_metrics["duration"] >= 0.1  # Should take at least 0.1 seconds
    assert fast_metrics["duration"] < slow_metrics["duration"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])