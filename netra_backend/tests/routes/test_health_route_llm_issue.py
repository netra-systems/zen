from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from shared.isolated_environment import IsolatedEnvironment
"""
Test that exposes the LLM health check issue in the health route.
This test demonstrates why the 'settings' is not defined error occurs.
"""

import sys
from pathlib import Path

import asyncio
import os

import pytest
from fastapi.testclient import TestClient

# Get environment first
env = get_env()

# Set minimal test environment
env.set("TESTING", "1", "test")
env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")
env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "test")
@pytest.fixture
def client():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test client with proper app setup"""
    from netra_backend.app.main import app
    return TestClient(app)

def test_llm_health_check_missing_method(client):
    """
    Test that demonstrates the missing is_healthy() method on LLMManager.
    
    The DependencyHealthChecker tries to call llm_manager.is_healthy() 
    but this method doesn't exist in the services/llm_manager.py implementation.
    """
    # This should fail because llm_manager doesn't have is_healthy() method
    from netra_backend.app.services.llm_manager import llm_manager
    
    # This will raise AttributeError: 'LLMManager' object has no attribute 'is_healthy'
    with pytest.raises(AttributeError) as exc_info:
        result = llm_manager.is_healthy()
    
    assert "is_healthy" in str(exc_info.value)

def test_health_ready_endpoint_with_llm_check_fails(client):
    """
    Test that the /health/ready endpoint fails when LLM health check is invoked.
    
    This test shows that the health endpoint doesn't properly handle the missing
    is_healthy() method and returns a 503 error instead of gracefully degrading.
    """
    # The ready endpoint will try to check all dependencies including LLM
    response = client.get("/health/ready")
    
    # Currently this returns 503 due to the missing is_healthy() method
    assert response.status_code == 503
    
    # The error should be caught and logged but not exposed to the client
    data = response.json()
    assert data["detail"] == "Service Unavailable"

def test_health_standard_level_with_llm_dependency():
    """
    Test that directly calling health interface with STANDARD level causes issues.
    
    This test directly exercises the code path that leads to the error.
    """
    from netra_backend.app.core.health import HealthInterface, HealthLevel
    
    # Create a health interface and try to get standard health status
    health_interface = HealthInterface("test-service", "1.0.0")
    
    # This should handle the missing is_healthy() gracefully
    # Currently it will fail when DependencyHealthChecker tries to check LLM
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(
            health_interface.get_health_status(HealthLevel.STANDARD)
        )
        # If we get here, the error was handled gracefully
        assert result["status"] in ["healthy", "degraded", "unhealthy"]
    except Exception as e:
        # The error should not bubble up as an unhandled exception
        pytest.fail(f"Health check raised unhandled exception: {e}")
    finally:
        loop.close()

def test_dependency_health_checker_llm_check_directly():
    """
    Test the DependencyHealthChecker's LLM check directly to expose the issue.
    
    This is the most direct test of the problematic code path.
    """
    from netra_backend.app.core.health.checks import DependencyHealthChecker
    
    # Create an LLM dependency checker
    llm_checker = DependencyHealthChecker("llm")
    
    # Try to check health - this will fail internally
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(llm_checker.check_health())
        
        # The checker should return unhealthy when is_healthy() is missing
        assert result.status == "unhealthy"
        assert not result.details.get("success", False)
    finally:
        loop.close()

def test_llm_manager_instantiation_without_settings():
    """
    Test that shows various LLMManager instantiations without required settings.
    
    This demonstrates the inconsistency in how LLMManager is instantiated
    across the codebase.
    """
    # In llm/llm_manager.py, it requires settings parameter
    from netra_backend.app.config import AppConfig
    from netra_backend.app.llm.llm_manager import LLMManager as LLMManagerWithSettings
    
    # This requires settings
    settings = AppConfig()
    llm_with_settings = LLMManagerWithSettings(settings)
    assert llm_with_settings.settings == settings
    
    # In services/llm_manager.py, it doesn't require settings
    from netra_backend.app.services.llm_manager import (
        LLMManager as LLMManagerNoSettings,
    )
    
    # This doesn't require settings
    llm_no_settings = LLMManagerNoSettings()
    assert not hasattr(llm_no_settings, 'settings')
    
    # And it doesn't have is_healthy() method
    assert not hasattr(llm_no_settings, 'is_healthy')

# Mock: Component isolation for testing without external dependencies
def test_health_check_with_mocked_llm_manager(mock_llm_manager):
    """
    Test that shows how the health check works when llm_manager.is_healthy() exists.
    
    This demonstrates what the expected behavior should be.
    """
    # Mock the is_healthy method to return True
    mock_llm_manager.is_healthy.return_value = True
    
    from netra_backend.app.core.health.checks import DependencyHealthChecker
    
    # Create an LLM dependency checker
    llm_checker = DependencyHealthChecker("llm")
    
    # Check health with the mocked manager
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        result = loop.run_until_complete(llm_checker.check_health())
        
        # With the mock, it should return healthy
        assert result.status == "healthy"
        assert result.details.get("success", False)
    finally:
        loop.close()

if __name__ == "__main__":
    # Run tests individually to see which ones fail
    import sys
    
    print("Testing LLM health check issues...")
    print("-" * 50)
    
    # Create client for tests that need it
    from netra_backend.app.main import app
    test_client = TestClient(app)
    
    tests = [
        ("Missing is_healthy method", test_llm_health_check_missing_method),
        ("Ready endpoint fails", lambda: test_health_ready_endpoint_with_llm_check_fails(test_client)),
        ("Standard health level", test_health_standard_level_with_llm_dependency),
        ("Direct dependency check", test_dependency_health_checker_llm_check_directly),
        ("Instantiation inconsistency", test_llm_manager_instantiation_without_settings),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            print(f"\nRunning: {test_name}")
            test_func()
            print(f"[U+2713] PASSED: {test_name}")
        except Exception as e:
            print(f"[U+2717] FAILED: {test_name}")
            print(f"  Error: {e}")
            failed_tests.append((test_name, str(e)))
    
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    if failed_tests:
        print(f"\n{len(failed_tests)} tests failed:")
        for name, error in failed_tests:
            print(f"  - {name}: {error[:100]}...")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)