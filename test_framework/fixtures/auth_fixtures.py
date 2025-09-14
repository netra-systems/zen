"""
Authentication-related test fixtures.
Consolidates auth fixtures from across the project.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def test_user_token():
    """Test user with JWT token"""
    return {
        "user_id": "test-user-123",
        "email": "test@example.com",
        "token": "test-jwt-token-for-websocket-auth",
        "expires_at": "2025-12-31T23:59:59Z"
    }

@pytest.fixture
def mock_auth_client():
    """Mock authentication client"""
    auth_client = AsyncMock()
    auth_client.signup = AsyncMock(return_value={
        "user_id": "test_user_123", 
        "email": "newuser@test.com", 
        "plan": "free"
    })
    auth_client.validate_token = AsyncMock(return_value={
        "valid": True, 
        "user_id": "test_user_123"
    })
    auth_client.initiate_oauth = AsyncMock(return_value={
        "oauth_url": "https://auth.example.com", 
        "state": "test_state"
    })
    return auth_client

@pytest.fixture 
def mock_jwt_handler():
    """Mock JWT token handler"""
    handler = MagicMock()
    handler.create_token = MagicMock(return_value="test-jwt-token")
    handler.validate_token = MagicMock(return_value={
        "valid": True,
        "user_id": "test-user-123", 
        "email": "test@example.com"
    })
    handler.decode_token = MagicMock(return_value={
        "sub": "test@example.com",
        "user_id": "test-user-123",
        "exp": 9999999999
    })
    return handler

@pytest.fixture
def auth_headers():
    """Common authorization headers for tests"""
    return {
        "Authorization": "Bearer test-jwt-token",
        "Content-Type": "application/json"
    }

@pytest.fixture
def mock_oauth_provider():
    """Mock OAuth provider (Google, etc.)"""
    provider = MagicMock()
    provider.get_authorization_url = MagicMock(return_value=(
        "https://accounts.google.com/oauth/authorize?...",
        "test-state"
    ))
    provider.get_access_token = AsyncMock(return_value={
        "access_token": "test-oauth-token",
        "refresh_token": "test-refresh-token",
        "expires_in": 3600
    })
    provider.get_user_info = AsyncMock(return_value={
        "id": "google-user-123",
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/avatar.jpg"
    })
    return provider

@pytest.fixture
def mock_session_manager():
    """Mock session manager"""
    manager = AsyncMock()
    manager.create_session = AsyncMock(return_value={
        "session_id": "test-session-123",
        "expires_at": "2025-12-31T23:59:59Z"
    })
    manager.get_session = AsyncMock(return_value={
        "session_id": "test-session-123",
        "user_id": "test-user-123",
        "active": True
    })
    manager.invalidate_session = AsyncMock(return_value=True)
    return manager

@pytest.fixture
def mock_permission_system():
    """Mock permission system for tier limitations"""
    system = MagicMock()
    system.check_tier_limits = AsyncMock(return_value={
        "tier": "free",
        "limits_reached": ["api_calls", "data_storage"],
        "upgrade_required": True,
        "remaining_usage": 0
    })
    system.has_permission = MagicMock(return_value=True)
    system.get_user_tier = MagicMock(return_value="free")
    return system
@pytest.fixture
async def auth_service_client():
    """HTTP client for auth service integration testing."""
    import httpx
    import os
    
    try:
        from dev_launcher.isolated_environment import IsolatedEnvironment
        env = IsolatedEnvironment()
        auth_service_url = env.get("AUTH_SERVICE_URL", "http://localhost:8001")
    except ImportError:
        # Fallback if IsolatedEnvironment not available
        auth_service_url = os.environ.get("AUTH_SERVICE_URL", "http://localhost:8001")
    
    async with httpx.AsyncClient(base_url=auth_service_url) as client:
        yield client
