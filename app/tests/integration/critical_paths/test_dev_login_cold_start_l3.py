"""Dev Login Cold Start Integration Tests (L3)

Tests dev login functionality during cold start scenarios.
These tests expose issues with dev login during first application startup.

Business Value Justification (BVJ):
- Segment: Development/Testing (enabling all other segments)
- Business Goal: Ensure developers can authenticate in dev environments
- Value Impact: Blocks development and testing workflows if broken
- Revenue Impact: Development velocity directly impacts feature delivery
"""

import os
import pytest
import asyncio
import json
import time
from typing import Dict, Any
from datetime import datetime
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

# Set test environment before imports
os.environ["ENVIRONMENT"] = "testing"
os.environ["TESTING"] = "true"
os.environ["SKIP_STARTUP_CHECKS"] = "true"

from app.main import app
from app.clients.auth_client import auth_client
from app.clients.auth_client_config import Environment, OAuthConfig


class TestDevLoginColdStart:
    """Test dev login functionality during cold start scenarios."""
    
    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        with TestClient(app) as c:
            yield c
    
    @pytest.fixture
    async def async_client(self):
        """Create async client for async API testing."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_dev_login_disabled_in_test_environment(self, async_client):
        """Test 1: Dev login should be disabled in test environment by default."""
        # Get current OAuth config
        oauth_config = auth_client.get_oauth_config()
        
        # Verify dev login is disabled in test environment
        assert oauth_config.allow_dev_login == False, "Dev login should be disabled in test environment"
        
        # Attempt dev login
        dev_login_data = {"email": "test@example.com"}
        response = await async_client.post("/api/auth/dev_login", json=dev_login_data)
        
        # Should return 403 Forbidden
        assert response.status_code == 403
        error_data = response.json()
        assert "not available" in error_data.get("detail", "").lower()
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_dev_login_enabled_in_dev_environment(self, async_client, monkeypatch):
        """Test 2: Dev login should be enabled in development environment."""
        # Mock development environment
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # Force re-detection of environment
        detected_env = auth_client.detect_environment()
        assert detected_env == Environment.DEVELOPMENT
        
        # Get OAuth config for dev environment
        oauth_config = auth_client.get_oauth_config()
        
        # Verify dev login is enabled
        assert oauth_config.allow_dev_login == True, "Dev login should be enabled in development environment"
        
        # Attempt dev login (will fail due to missing auth service, but should not return 403)
        dev_login_data = {"email": "dev@example.com"}
        response = await async_client.post("/api/auth/dev_login", json=dev_login_data)
        
        # Should not return 403 (may return 503 if auth service unavailable)
        assert response.status_code != 403, "Dev login should not be forbidden in dev environment"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_config_cold_start_initialization(self, async_client):
        """Test 3: OAuth config should be properly initialized on cold start."""
        # Clear any cached config
        auth_client._cached_config = None if hasattr(auth_client, '_cached_config') else None
        
        # First request after cold start - check auth config
        config_response = await async_client.get("/api/auth/config")
        assert config_response.status_code == 200
        
        config_data = config_response.json()
        
        # Verify essential config fields are present
        assert "client_id" in config_data
        assert "redirect_uri" in config_data
        assert "auth_url" in config_data
        assert "dev_login_enabled" in config_data
        
        # In test environment, dev login should be disabled
        assert config_data["dev_login_enabled"] == False
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_environment_detection_consistency(self):
        """Test 4: Environment detection should be consistent across calls."""
        # Multiple calls should return same environment
        env1 = auth_client.detect_environment()
        env2 = auth_client.detect_environment()
        env3 = auth_client.detect_environment()
        
        assert env1 == env2 == env3, "Environment detection should be consistent"
        
        # In test environment, should detect as TESTING
        assert env1 == Environment.TESTING
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_oauth_config_environment_specific(self):
        """Test 5: OAuth config should be environment-specific."""
        # Get configs for different environments
        from app.clients.auth_client_config import OAuthConfigGenerator
        
        generator = OAuthConfigGenerator()
        
        dev_config = generator.get_oauth_config(Environment.DEVELOPMENT)
        test_config = generator.get_oauth_config(Environment.TESTING)
        staging_config = generator.get_oauth_config(Environment.STAGING)
        prod_config = generator.get_oauth_config(Environment.PRODUCTION)
        
        # Verify dev login settings
        assert dev_config.allow_dev_login == True, "Dev should allow dev login"
        assert test_config.allow_dev_login == False, "Test should not allow dev login"
        assert staging_config.allow_dev_login == False, "Staging should not allow dev login"
        assert prod_config.allow_dev_login == False, "Prod should not allow dev login"
        
        # Verify mock auth settings
        assert dev_config.allow_mock_auth == True, "Dev should allow mock auth"
        assert test_config.allow_mock_auth == True, "Test should allow mock auth"
        assert staging_config.allow_mock_auth == False, "Staging should not allow mock auth"
        assert prod_config.allow_mock_auth == False, "Prod should not allow mock auth"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_auth_service_url_configuration(self):
        """Test 6: Auth service URL should be properly configured."""
        # Check auth client settings
        settings = auth_client.settings
        
        # Base URL should be configured
        assert settings.base_url, "Auth service base URL should be configured"
        
        # In test environment, should use local URL
        assert "localhost" in settings.base_url or "127.0.0.1" in settings.base_url
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_dev_login_user_creation(self, async_client, monkeypatch):
        """Test 7: Dev login should create user if not exists (when enabled)."""
        # This test would require mocking the database and auth service
        # For now, we'll test the endpoint behavior
        
        # Mock development environment
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # Attempt dev login with new user email
        unique_email = f"newuser_{int(time.time())}@example.com"
        dev_login_data = {"email": unique_email}
        
        response = await async_client.post("/api/auth/dev_login", json=dev_login_data)
        
        # In dev environment with mocked services, should attempt user creation
        # Will fail due to missing services but should not return 403
        assert response.status_code != 403
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_auth_config_endpoint_cold_start_performance(self, async_client):
        """Test 8: Auth config endpoint should respond quickly on cold start."""
        # Measure cold start time for auth config
        start_time = time.perf_counter()
        
        response = await async_client.get("/api/auth/config")
        
        response_time = time.perf_counter() - start_time
        
        # Should respond within 1 second even on cold start
        assert response_time < 1.0, f"Auth config took {response_time}s on cold start"
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_dev_login_requests(self, async_client):
        """Test 9: System should handle concurrent dev login requests."""
        # Create multiple concurrent requests
        async def attempt_dev_login(email: str):
            data = {"email": email}
            return await async_client.post("/api/auth/dev_login", json=data)
        
        # Send 5 concurrent requests
        emails = [f"concurrent_{i}@example.com" for i in range(5)]
        tasks = [attempt_dev_login(email) for email in emails]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should return same status (403 in test environment)
        status_codes = [r.status_code for r in responses if not isinstance(r, Exception)]
        assert all(code == 403 for code in status_codes), "All requests should be handled consistently"
    
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_auth_config_caching(self, async_client):
        """Test 10: Auth config should be properly cached after first call."""
        # First call - cold start
        response1 = await async_client.get("/api/auth/config")
        assert response1.status_code == 200
        config1 = response1.json()
        
        # Second call - should use cache
        start_time = time.perf_counter()
        response2 = await async_client.get("/api/auth/config")
        cached_time = time.perf_counter() - start_time
        
        assert response2.status_code == 200
        config2 = response2.json()
        
        # Should be much faster due to caching
        assert cached_time < 0.1, f"Cached response took {cached_time}s"
        
        # Config should be identical
        assert config1 == config2, "Cached config should match original"