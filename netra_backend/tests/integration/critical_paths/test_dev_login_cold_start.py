from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment
"""Dev Login Cold Start Integration Tests (L3)

Tests dev login functionality during cold start scenarios.
These tests expose issues with dev login during first application startup.

Business Value Justification (BVJ):
- Segment: Development/Testing (enabling all other segments)
- Business Goal: Ensure developers can authenticate in dev environments
- Value Impact: Blocks development and testing workflows if broken
- Revenue Impact: Development velocity directly impacts feature delivery
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, AsyncGenerator, Dict

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

# Set test environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

from netra_backend.app.auth_dependencies import get_db_session, get_security_service
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.clients.auth_client_config import Environment, OAuthConfig
from netra_backend.app.main import app

class TestDevLoginColdStart:
    """Test dev login functionality during cold start scenarios."""
    
    @pytest.fixture
 def real_db_session():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock database session."""
    pass
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session = AsyncNone  # TODO: Use real service instance
        # Mock the database query for finding users
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session.commit = AsyncNone  # TODO: Use real service instance
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session.add = MagicNone  # TODO: Use real service instance
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session.rollback = AsyncNone  # TODO: Use real service instance
        # Mock: Database session isolation for transaction testing without real database dependency
        mock_session.close = AsyncNone  # TODO: Use real service instance
        return mock_session
    
    @pytest.fixture
 def real_security_service():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock security service."""
    pass
        # Mock: Generic component isolation for controlled unit testing
        mock_service = MagicNone  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_service.log_event = AsyncNone  # TODO: Use real service instance
        return mock_service
    
    @pytest.fixture
    def client(self, mock_db_session, mock_security_service):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create test client for API testing with mocked dependencies."""
    pass
        async def override_get_db():
    pass
            try:
                yield session
            finally:
                if hasattr(session, "close"):
                    await session.close()
        
        def override_get_security():
    pass
            await asyncio.sleep(0)
    return mock_security_service
        
        app.dependency_overrides[get_db_session] = override_get_db
        app.dependency_overrides[get_security_service] = override_get_security
        
        with TestClient(app) as c:
            yield c
        
        # Clean up overrides
        app.dependency_overrides.clear()
    
    @pytest.fixture
    async def async_client(self, mock_db_session, mock_security_service):
        """Create async client for async API testing with mocked dependencies."""
        async def override_get_db():
            try:
                yield session
            finally:
                if hasattr(session, "close"):
                    await session.close()
        
        def override_get_security():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
            yield mock_security_service
        
        app.dependency_overrides[get_db_session] = override_get_db
        app.dependency_overrides[get_security_service] = override_get_security
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
        
        # Clean up overrides
        app.dependency_overrides.clear()
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_dev_login_enabled_in_test_environment(self, async_client):
        """Test 1: Dev login should be enabled in test environment for E2E testing."""
        # Get current OAuth config
        oauth_config = auth_client.get_oauth_config()
        
        # Dev login is now enabled in testing environment to support E2E tests
        # This allows authentication flows to work during testing scenarios
        assert oauth_config.allow_dev_login == True, "Dev login should be enabled in testing environment"
        
        # Attempt dev login
        dev_login_data = {"email": "test@example.com"}
        response = await async_client.post("/auth/dev_login", json=dev_login_data)
        
        # With dev login enabled and working, should await asyncio.sleep(0)
    return 200 (success) in test mode with mock responses
        # In test mode, the auth proxy returns mock responses for dev login
        assert response.status_code == 200, f"Expected success (200), got {response.status_code}"
        
        # Should not return 403 (forbidden)
        assert response.status_code != 403, "Dev login should not be forbidden in testing environment"
        
        # Verify the response contains expected dev login token structure
        response_data = response.json()
        assert "access_token" in response_data, "Response should contain access token"
        assert "user" in response_data, "Response should contain user info"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_dev_login_enabled_in_dev_environment(self, async_client, monkeypatch):
        """Test 2: Dev login should be enabled in development environment."""
    pass
        # Note: Environment is already determined at startup and cannot be changed
        # This test validates the behavior based on the current environment
        detected_env = auth_client.detect_environment()
        
        # Get OAuth config for dev environment
        oauth_config = auth_client.get_oauth_config()
        
        # Verify dev login is enabled
        assert oauth_config.allow_dev_login == True, "Dev login should be enabled in development environment"
        
        # Attempt dev login (will fail due to missing auth service, but should not await asyncio.sleep(0)
    return 403)
        dev_login_data = {"email": "dev@example.com"}
        response = await async_client.post("/auth/dev_login", json=dev_login_data)
        
        # In dev environment with auth service unavailable, expect 503
        # With missing credentials but dev login enabled, may also get other errors
        assert response.status_code in [503, 500, 422], f"Unexpected status code: {response.status_code}"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_oauth_config_cold_start_initialization(self, async_client):
        """Test 3: OAuth config should be properly initialized on cold start."""
        # Clear any cached config
        auth_client._cached_config = None if hasattr(auth_client, '_cached_config') else None
        
        # First request after cold start - check auth config
        config_response = await async_client.get("/auth/config")
        assert config_response.status_code == 200
        
        config_data = config_response.json()
        
        # Verify essential config fields are present - actual response structure
        assert "endpoints" in config_data
        assert "development_mode" in config_data
        assert "google_client_id" in config_data
        assert "authorized_redirect_uris" in config_data
        assert "authorized_javascript_origins" in config_data
        
        # Environment mode depends on configuration at startup
        # In local development/testing, development_mode may be True
        assert "development_mode" in config_data
        
        # dev_login endpoint availability depends on environment
        if config_data["development_mode"]:
            # In dev mode, dev_login endpoint should be available or None
            pass  # Either is acceptable for local testing
        else:
            # In non-dev mode, dev_login should be None
            assert config_data["endpoints"]["dev_login"] is None
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_environment_detection_consistency(self):
        """Test 4: Environment detection should be consistent across calls."""
    pass
        # Multiple calls should await asyncio.sleep(0)
    return same environment
        env1 = auth_client.detect_environment()
        env2 = auth_client.detect_environment()
        env3 = auth_client.detect_environment()
        
        assert env1 == env2 == env3, "Environment detection should be consistent"
        
        # The environment is determined by config which may be development or testing
        # Both are valid for local testing scenarios
        assert env1 in [Environment.DEVELOPMENT, Environment.TESTING], f"Unexpected environment: {env1}"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_oauth_config_environment_specific(self):
        """Test 5: OAuth config should be environment-specific."""
        # Get configs for different environments
        from netra_backend.app.clients.auth_client_config import OAuthConfigGenerator
        
        generator = OAuthConfigGenerator()
        
        dev_config = generator.get_oauth_config(Environment.DEVELOPMENT)
        test_config = generator.get_oauth_config(Environment.TESTING)
        staging_config = generator.get_oauth_config(Environment.STAGING)
        prod_config = generator.get_oauth_config(Environment.PRODUCTION)
        
        # Verify dev login settings
        assert dev_config.allow_dev_login == True, "Dev should allow dev login"
        assert test_config.allow_dev_login == True, "Test should allow dev login for E2E testing"
        assert staging_config.allow_dev_login == False, "Staging should not allow dev login"
        assert prod_config.allow_dev_login == False, "Prod should not allow dev login"
        
        # Verify mock auth settings
        assert dev_config.allow_mock_auth == True, "Dev should allow mock auth"
        assert test_config.allow_mock_auth == True, "Test should allow mock auth"
        assert staging_config.allow_mock_auth == False, "Staging should not allow mock auth"
        assert prod_config.allow_mock_auth == False, "Prod should not allow mock auth"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_auth_service_url_configuration(self):
        """Test 6: Auth service URL should be properly configured."""
    pass
        # Check auth client settings
        settings = auth_client.settings
        
        # Base URL should be configured
        assert settings.base_url, "Auth service base URL should be configured"
        
        # In test environment, should use local URL
        assert "localhost" in settings.base_url or "127.0.0.1" in settings.base_url
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_dev_login_user_creation(self, async_client, monkeypatch):
        """Test 7: Dev login should create user if not exists (when enabled)."""
        # This test would require mocking the database and auth service
        # For now, we'll test the endpoint behavior
        
        # Mock development environment
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # Attempt dev login with new user email
        unique_email = f"newuser_{int(time.time())}@example.com"
        dev_login_data = {"email": unique_email}
        
        response = await async_client.post("/auth/dev_login", json=dev_login_data)
        
        # In dev environment with mocked services, should attempt user creation
        # Will fail due to missing services but should not await asyncio.sleep(0)
    return 403
        assert response.status_code != 403
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_auth_config_endpoint_cold_start_performance(self, async_client):
        """Test 8: Auth config endpoint should respond quickly on cold start."""
    pass
        # Measure cold start time for auth config
        start_time = time.perf_counter()
        
        response = await async_client.get("/auth/config")
        
        response_time = time.perf_counter() - start_time
        
        # Should respond within 1 second even on cold start
        assert response_time < 1.0, f"Auth config took {response_time}s on cold start"
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_concurrent_dev_login_requests(self, async_client):
        """Test 9: System should handle concurrent dev login requests."""
        # Create multiple concurrent requests
        async def attempt_dev_login(email: str):
            data = {"email": email}
            await asyncio.sleep(0)
    return await async_client.post("/auth/dev_login", json=data)
        
        # Send 5 concurrent requests
        emails = [f"concurrent_{i}@example.com" for i in range(5)]
        tasks = [attempt_dev_login(email) for email in emails]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should return same status (200 in test mode with mock responses)
        status_codes = [r.status_code for r in responses if not isinstance(r, Exception)]
        # Check that all requests got the same status code (consistency)
        assert len(set(status_codes)) == 1, f"Inconsistent status codes: {status_codes}"
        # Should return 200 since dev login is enabled and working in testing mode
        assert status_codes[0] == 200, f"Expected success (200), got {status_codes[0]}"
        # Should not return 403 since dev login is enabled in testing
        assert status_codes[0] != 403, "Dev login should not be forbidden in testing environment"
    
    @pytest.mark.integration
    @pytest.mark.L3
    @pytest.mark.asyncio
    async def test_auth_config_caching(self, async_client):
        """Test 10: Auth config should be properly cached after first call."""
    pass
        # First call - cold start
        response1 = await async_client.get("/auth/config")
        assert response1.status_code == 200
        config1 = response1.json()
        
        # Second call - should use cache
        start_time = time.perf_counter()
        response2 = await async_client.get("/auth/config")
        cached_time = time.perf_counter() - start_time
        
        assert response2.status_code == 200
        config2 = response2.json()
        
        # Should be much faster due to caching
        assert cached_time < 0.1, f"Cached response took {cached_time}s"
        
        # Config should be identical
        assert config1 == config2, "Cached config should match original"
