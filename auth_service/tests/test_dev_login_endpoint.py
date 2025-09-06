import asyncio
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
"""Test for dev login endpoint"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, UTC
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

@pytest.fixture
def test_client():
    """Use real service instance."""
    # TODO: Initialize real service
    """Create test client for auth service"""
    # Import after env setup
    from auth_service.main import app
    return TestClient(app)

@pytest.mark.asyncio
async def test_dev_login_endpoint_in_dev_environment(test_client):
    """Test that dev login works in development environment"""
    # Mock the environment to be development
    with patch('auth_service.auth_core.config.AuthConfig.get_environment', return_value = 'development'):
        # Mock the auth service methods
        with patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock_auth:
            mock_auth.create_access_token = AsyncMock(return_value = "dev-access-token")
            mock_auth.create_refresh_token = AsyncMock(return_value = "dev-refresh-token")
            
            response = test_client.post("/auth/dev/login", json = {})
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "dev-access-token"
            assert data["refresh_token"] == "dev-refresh-token"
            assert data["token_type"] == "Bearer"
            assert data["expires_in"] == 900

@pytest.mark.asyncio 
async def test_dev_login_blocked_in_production(test_client):
    """Test that dev login is blocked in production environment"""
    # Mock the environment to be production
    with patch('auth_service.auth_core.config.AuthConfig.get_environment', return_value = 'production'):
        response = test_client.post("/auth/dev/login", json = {})
        
        assert response.status_code == 403
        data = response.json()
        assert "only available in development" in data["detail"]

@pytest.mark.asyncio
async def test_dev_login_allowed_in_test_environment(test_client):
    """Test that dev login works in test environment"""
    # Mock the environment to be test
    with patch('auth_service.auth_core.config.AuthConfig.get_environment', return_value = 'test'):
        # Mock the auth service methods
        with patch('auth_service.auth_core.routes.auth_routes.auth_service') as mock_auth:
            mock_auth.create_access_token = AsyncMock(return_value = "test-access-token")
            mock_auth.create_refresh_token = AsyncMock(return_value = "test-refresh-token")
            
            response = test_client.post("/auth/dev/login", json = {})
            
            assert response.status_code == 200
            data = response.json()
            assert data["access_token"] == "test-access-token"
            assert data["refresh_token"] == "test-refresh-token"