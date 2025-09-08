"""
Integration Authentication Test Fixtures - SSOT for WebSocket Integration Testing

Business Value Justification (BVJ):
- Segment: Platform/Internal (Test Infrastructure)
- Business Goal: Enable reliable WebSocket integration testing with real authentication
- Value Impact: Prevents auth regressions, enables multi-user testing, maintains SSOT compliance
- Strategic Impact: Critical foundation for integration test reliability and development velocity

These fixtures provide authentication services for WebSocket integration tests
while maintaining SSOT architecture compliance.
"""

import asyncio
import logging
import pytest
from typing import Dict, Any, Optional, Generator, AsyncGenerator

from test_framework.ssot.integration_auth_manager import (
    IntegrationAuthServiceManager,
    IntegrationTestAuthHelper,
    get_integration_auth_manager
)

logger = logging.getLogger(__name__)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def integration_auth_manager(event_loop) -> AsyncGenerator[IntegrationAuthServiceManager, None]:
    """
    Session-scoped fixture for integration auth service manager.
    
    This fixture starts the auth service once per test session and keeps it
    running for all integration tests that need authentication.
    """
    logger.info("Starting integration auth service manager for test session")
    
    auth_manager = await get_integration_auth_manager()
    
    try:
        # Start the auth service
        success = await auth_manager.start_auth_service()
        if not success:
            raise RuntimeError("Failed to start integration auth service")
        
        logger.info("Integration auth service is ready for test session")
        yield auth_manager
        
    finally:
        # Clean up after all tests complete
        logger.info("Stopping integration auth service after test session")
        await auth_manager.stop_auth_service()


@pytest.fixture
async def integration_auth_helper(integration_auth_manager: IntegrationAuthServiceManager) -> IntegrationTestAuthHelper:
    """
    Function-scoped fixture for integration test auth helper.
    
    Provides a fresh auth helper instance for each test that needs authentication.
    """
    helper = IntegrationTestAuthHelper(integration_auth_manager)
    
    # Create a test token for the test
    token = await helper.create_integration_test_token()
    logger.debug("Created integration test token for test")
    
    return helper


@pytest.fixture
async def authenticated_user_token(integration_auth_helper: IntegrationTestAuthHelper) -> str:
    """
    Function-scoped fixture that provides an authenticated user token.
    
    Returns a valid JWT token that can be used for API and WebSocket authentication.
    """
    # The helper already created a token during initialization
    token = integration_auth_helper._cached_token
    if not token:
        # Fallback - create a new token
        token = await integration_auth_helper.create_integration_test_token()
    
    return token


@pytest.fixture
async def authenticated_websocket_headers(integration_auth_helper: IntegrationTestAuthHelper) -> Dict[str, str]:
    """
    Function-scoped fixture that provides WebSocket authentication headers.
    
    Returns headers dict ready for WebSocket connection authentication.
    """
    return integration_auth_helper.get_integration_websocket_headers()


@pytest.fixture
async def authenticated_api_headers(integration_auth_helper: IntegrationTestAuthHelper) -> Dict[str, str]:
    """
    Function-scoped fixture that provides API authentication headers.
    
    Returns headers dict ready for HTTP API authentication.
    """
    return integration_auth_helper.get_integration_auth_headers()


@pytest.fixture
async def multi_user_tokens(integration_auth_helper: IntegrationTestAuthHelper) -> Dict[str, str]:
    """
    Function-scoped fixture that provides multiple user tokens for multi-user testing.
    
    Returns a dict mapping user IDs to their authentication tokens.
    """
    tokens = {}
    
    # Create tokens for multiple test users
    user_configs = [
        {"user_id": "test-user-1", "email": "user1@test.com"},
        {"user_id": "test-user-2", "email": "user2@test.com"},
        {"user_id": "test-user-3", "email": "user3@test.com"}
    ]
    
    for config in user_configs:
        token = await integration_auth_helper.create_integration_test_token(
            user_id=config["user_id"],
            email=config["email"]
        )
        tokens[config["user_id"]] = token
    
    logger.debug(f"Created tokens for {len(tokens)} test users")
    return tokens


@pytest.fixture
def auth_service_url(integration_auth_manager: IntegrationAuthServiceManager) -> str:
    """
    Function-scoped fixture that provides the auth service URL.
    
    Returns the URL of the running integration auth service.
    """
    return integration_auth_manager.get_auth_url()


@pytest.fixture
async def auth_service_health_check(integration_auth_manager: IntegrationAuthServiceManager) -> bool:
    """
    Function-scoped fixture that performs a health check on the auth service.
    
    Returns True if auth service is healthy, False otherwise.
    Useful for tests that need to verify auth service is operational.
    """
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{integration_auth_manager.get_auth_url()}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    is_healthy = data.get("status") == "healthy"
                    logger.debug(f"Auth service health check: {'healthy' if is_healthy else 'unhealthy'}")
                    return is_healthy
        
        return False
        
    except Exception as e:
        logger.warning(f"Auth service health check failed: {e}")
        return False


# Conditional fixture for WebSocket integration tests
@pytest.fixture
async def websocket_integration_auth(request, integration_auth_helper: IntegrationTestAuthHelper):
    """
    Conditional fixture for WebSocket integration tests.
    
    Only activates for tests marked with @pytest.mark.websocket_integration.
    Provides complete authentication setup for WebSocket testing.
    """
    # Check if test is marked for WebSocket integration
    if "websocket_integration" not in [mark.name for mark in request.node.iter_markers()]:
        pytest.skip("This fixture only applies to WebSocket integration tests")
    
    # Create authentication components
    token = await integration_auth_helper.create_integration_test_token()
    headers = integration_auth_helper.get_integration_websocket_headers()
    
    return {
        "token": token,
        "headers": headers,
        "auth_helper": integration_auth_helper,
        "auth_manager": integration_auth_helper.auth_manager
    }


# Utility fixture for cleaning up auth state between tests
@pytest.fixture(autouse=True)
async def cleanup_auth_state():
    """
    Auto-use fixture that cleans up authentication state between tests.
    
    This helps prevent test contamination and ensures each test
    starts with a clean authentication state.
    """
    # Pre-test: Nothing to clean up yet
    yield
    
    # Post-test: Clear any cached tokens or state
    # This is handled automatically by function-scoped fixtures
    pass


# Performance optimization fixture
@pytest.fixture(scope="session")
def auth_performance_mode():
    """
    Session-scoped fixture that enables auth performance optimizations for testing.
    
    Sets environment variables that optimize auth service performance during testing.
    """
    import os
    from shared.isolated_environment import get_env
    
    env = get_env()
    
    # Set performance optimization flags
    perf_settings = {
        "AUTH_FAST_TEST_MODE": "true",
        "ENABLE_AUTH_LOGGING": "false",
        "JWT_CACHE_SIZE": "100",  # Smaller cache for testing
        "AUTH_CIRCUIT_BREAKER_THRESHOLD": "10"  # Higher threshold for testing
    }
    
    original_values = {}
    
    # Apply performance settings
    for key, value in perf_settings.items():
        original_values[key] = env.get(key)
        env.set(key, value, source="test_performance")
        os.environ[key] = value
    
    logger.debug("Applied auth performance optimizations for testing")
    
    yield
    
    # Restore original values
    for key, original_value in original_values.items():
        if original_value is not None:
            env.set(key, original_value, source="test_cleanup") 
            os.environ[key] = original_value
        else:
            env.remove(key, source="test_cleanup")
            os.environ.pop(key, None)
    
    logger.debug("Restored original auth settings after testing")


# Error handling fixture for auth failures
@pytest.fixture
def auth_error_handler():
    """
    Function-scoped fixture that provides error handling utilities for auth failures.
    
    Returns functions for handling common auth failure scenarios in tests.
    """
    def handle_auth_service_down():
        """Handle auth service down scenario."""
        return pytest.skip("Auth service is not available for this test")
    
    def handle_token_invalid():
        """Handle invalid token scenario.""" 
        return pytest.fail("Token validation failed - check auth service configuration")
    
    def handle_websocket_auth_failure():
        """Handle WebSocket authentication failure."""
        return pytest.fail("WebSocket authentication failed - check token and headers")
    
    return {
        "service_down": handle_auth_service_down,
        "token_invalid": handle_token_invalid, 
        "websocket_auth_failure": handle_websocket_auth_failure
    }


# Integration test marker and configuration
def pytest_configure(config):
    """Configure pytest with integration test markers."""
    config.addinivalue_line(
        "markers",
        "websocket_integration: mark test as a WebSocket integration test requiring auth service"
    )
    config.addinivalue_line(
        "markers", 
        "multi_user: mark test as requiring multiple authenticated users"
    )
    config.addinivalue_line(
        "markers",
        "auth_required: mark test as requiring authentication service"
    )


# Conditional skips for missing dependencies
def pytest_runtest_setup(item):
    """Set up individual test runs with conditional skips."""
    # Skip WebSocket integration tests if auth service is not available
    if "websocket_integration" in [mark.name for mark in item.iter_markers()]:
        # This check will be done by the fixture - no need to skip here
        pass
    
    # Skip multi-user tests if requested
    if "multi_user" in [mark.name for mark in item.iter_markers()]:
        # Multi-user tests require additional setup - handled by fixture
        pass


# Export fixtures for easy importing
__all__ = [
    "integration_auth_manager",
    "integration_auth_helper", 
    "authenticated_user_token",
    "authenticated_websocket_headers",
    "authenticated_api_headers",
    "multi_user_tokens",
    "auth_service_url",
    "auth_service_health_check",
    "websocket_integration_auth",
    "cleanup_auth_state",
    "auth_performance_mode",
    "auth_error_handler"
]