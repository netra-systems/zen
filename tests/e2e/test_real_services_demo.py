"""
Demo test showing how to use RealServicesManager for E2E testing.
This is a demonstration of the real services infrastructure.
"""

import asyncio
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.e2e.real_services_health import RealServicesContext, ServiceHealthMonitor
from tests.e2e.real_services_manager import create_real_services_manager


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_real_services_manager_basic():
    """Test basic functionality of RealServicesManager."""
    # Test instantiation
    manager = create_real_services_manager()
    
    assert len(manager.services) == 3
    assert "auth" in manager.services
    assert "backend" in manager.services
    assert "frontend" in manager.services
    
    # Test port configuration
    assert manager.services["auth"].port == 8001
    assert manager.services["backend"].port == 8000
    assert manager.services["frontend"].port == 3000
    
    # Test health URLs
    assert manager.services["auth"].health_url == "/health"
    assert manager.services["backend"].health_url == "/health"
    assert manager.services["frontend"].health_url == "/"


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_urls():
    """Test service URL generation."""
    manager = create_real_services_manager()
    
    # Initially no services are ready
    urls = manager.get_service_urls()
    assert len(urls) == 0
    
    # Mark services as ready for testing
    manager.services["auth"].ready = True
    manager.services["backend"].ready = True
    
    urls = manager.get_service_urls()
    assert "auth" in urls
    assert "backend" in urls
    assert urls["auth"] == "http://localhost:8001"
    assert urls["backend"] == "http://localhost:8000"


@pytest.mark.asyncio 
@pytest.mark.e2e
async def test_health_monitor():
    """Test health monitoring functionality."""
    manager = create_real_services_manager()
    monitor = ServiceHealthMonitor(manager)
    
    # Test initial state
    assert not monitor.monitoring
    assert monitor.check_interval == 5
    assert monitor.monitor_task is None


@pytest.mark.e2e
def test_context_manager_creation():
    """Test context manager creation."""
    context = RealServicesContext()
    assert context.manager is not None
    assert context.monitor is not None


# NOTE: The following test is commented out as it would actually start services
# Uncomment and run manually if you want to test real service startup
"""
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.e2e
async def test_real_services_startup():
    '''Test actual service startup (manual test only).'''
    async with RealServicesContext() as manager:
        # Services should be started and healthy
        assert manager.is_all_ready()
        
        # Test service URLs
        urls = manager.get_service_urls()
        assert len(urls) == 3
        
        # Test health status
        status = await manager.health_status()
        assert all(s['ready'] for s in status.values())
        
        print(f"Services running at: {urls}")
        print(f"Health status: {status}")
"""
