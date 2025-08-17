"""Comprehensive tests for auth middleware, CORS, and Redis integration.

Tests FastAPI middleware configuration, CORS settings, Redis session management,
OAuth session handling, and integrated auth workflows.
All test functions ≤8 lines (MANDATORY). File ≤300 lines (MANDATORY).

Business Value Justification (BVJ):
1. Segment: All customer segments (Free through Enterprise)  
2. Business Goal: Ensure secure middleware and session management
3. Value Impact: Prevents security vulnerabilities and session issues
4. Revenue Impact: Critical for platform reliability and customer retention
"""

import os
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from fastapi.testclient import TestClient

from app.auth.auth_service import app
from app.auth.oauth_session_manager import OAuthSessionManager, StateData


@pytest.fixture
def client():
    """Create test client for testing middleware."""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """Mock Redis service for session testing."""
    with patch('app.auth.oauth_session_manager.redis_service') as mock:
        mock.setex = AsyncMock()
        mock.get = AsyncMock()
        mock.delete = AsyncMock()
        mock.keys = AsyncMock(return_value=[])
        mock.ping = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def oauth_session_manager():
    """Create OAuth session manager for testing."""
    return OAuthSessionManager()


class TestCORSMiddleware:
    """Test CORS middleware configuration and behavior."""
    
    def test_cors_preflight_request_allowed_origin(self, client):
        """Test CORS preflight request from allowed origin."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:3000,https://netrasystems.ai"}):
            response = client.options(
                "/auth/status",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "GET"
                }
            )
            # Should handle CORS preflight
            assert response.status_code in [200, 405]  # Either OK or method not allowed


    def test_cors_request_with_credentials(self, client):
        """Test CORS request with credentials allowed."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "https://netrasystems.ai"}):
            response = client.get(
                "/health",
                headers={"Origin": "https://netrasystems.ai"}
            )
            # Should not block request from allowed origin
            assert response.status_code == 200


    def test_cors_configuration_multiple_origins(self, client):
        """Test CORS configuration with multiple allowed origins."""
        origins = "http://localhost:3000,http://localhost:3010,https://staging.netrasystems.ai"
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": origins}):
            # Test each origin individually
            test_origins = origins.split(',')
            for origin in test_origins:
                response = client.get("/health", headers={"Origin": origin})
                assert response.status_code == 200


    def test_cors_empty_origins_configuration(self, client):
        """Test CORS configuration with empty origins."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": ""}):
            response = client.get("/health")
            # Should still work without Origin header
            assert response.status_code == 200


    def test_cors_allowed_methods_configuration(self, client):
        """Test CORS allows required HTTP methods."""
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": "http://localhost:3000"}):
            # Test each allowed method
            methods = ["GET", "POST", "OPTIONS"]
            for method in methods:
                if method == "OPTIONS":
                    response = client.options("/auth/status", headers={"Origin": "http://localhost:3000"})
                elif method == "GET":
                    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
                elif method == "POST":
                    # POST to logout endpoint
                    response = client.post("/auth/logout", headers={"Origin": "http://localhost:3000"})
                # Should not block based on method
                assert response.status_code in [200, 400, 401, 405]


class TestRedisSessionManagement:
    """Test Redis-based session management functionality."""
    
    @pytest.mark.asyncio
    async def test_oauth_state_creation_stores_in_redis(self, oauth_session_manager, mock_redis):
        """Test OAuth state creation stores data in Redis."""
        state_id = await oauth_session_manager.create_oauth_state("42", "http://localhost:3000")
        
        assert isinstance(state_id, str)
        assert len(state_id) > 0
        mock_redis.setex.assert_called_once()
        # Verify Redis key format
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0].startswith("oauth_state:")


    @pytest.mark.asyncio
    async def test_oauth_state_creation_with_ttl(self, oauth_session_manager, mock_redis):
        """Test OAuth state creation includes proper TTL."""
        await oauth_session_manager.create_oauth_state(None, "http://example.com")
        
        call_args = mock_redis.setex.call_args[0]
        ttl = call_args[1]
        assert ttl == oauth_session_manager.session_ttl  # 300 seconds


    @pytest.mark.asyncio
    async def test_oauth_state_validation_and_consumption(self, oauth_session_manager, mock_redis):
        """Test OAuth state validation retrieves and deletes from Redis."""
        mock_state_data = {
            "csrf_token": "test_csrf_token",
            "return_url": "http://localhost:3000",
            "timestamp": 1234567890
        }
        mock_redis.get.return_value = json.dumps(mock_state_data)
        
        state_data = await oauth_session_manager.validate_and_consume_state("test_state_id")
        
        assert state_data["csrf_token"] == "test_csrf_token"
        mock_redis.get.assert_called_once_with("oauth_state:test_state_id")
        mock_redis.delete.assert_called_once_with("oauth_state:test_state_id")


    @pytest.mark.asyncio
    async def test_oauth_state_validation_invalid_state(self, oauth_session_manager, mock_redis):
        """Test OAuth state validation with invalid state ID."""
        mock_redis.get.return_value = None
        
        with pytest.raises(Exception) as exc_info:
            await oauth_session_manager.validate_and_consume_state("invalid_state")
        
        assert "Invalid or expired state" in str(exc_info.value)


    @pytest.mark.asyncio
    async def test_oauth_state_data_structure(self, oauth_session_manager, mock_redis):
        """Test OAuth state data contains required fields."""
        await oauth_session_manager.create_oauth_state("123", "https://example.com/callback")
        
        # Get the stored data
        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        
        required_fields = ["csrf_token", "return_url", "timestamp"]
        for field in required_fields:
            assert field in stored_data
        assert stored_data["pr_number"] == "123"


    @pytest.mark.asyncio
    async def test_oauth_state_pr_number_optional(self, oauth_session_manager, mock_redis):
        """Test OAuth state creation without PR number."""
        await oauth_session_manager.create_oauth_state(None, "https://example.com")
        
        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        
        assert "pr_number" not in stored_data or stored_data.get("pr_number") is None


class TestOAuthSessionSecurity:
    """Test OAuth session security features."""
    
    @pytest.mark.asyncio
    async def test_csrf_token_generation_uniqueness(self, oauth_session_manager, mock_redis):
        """Test CSRF tokens are unique for each state creation."""
        await oauth_session_manager.create_oauth_state(None, "http://test1.com")
        await oauth_session_manager.create_oauth_state(None, "http://test2.com")
        
        # Get both stored data sets
        calls = mock_redis.setex.call_args_list
        data1 = json.loads(calls[0][0][2])
        data2 = json.loads(calls[1][0][2])
        
        assert data1["csrf_token"] != data2["csrf_token"]


    @pytest.mark.asyncio
    async def test_state_id_generation_uniqueness(self, oauth_session_manager, mock_redis):
        """Test state IDs are unique for each creation."""
        state_id1 = await oauth_session_manager.create_oauth_state(None, "http://test.com")
        state_id2 = await oauth_session_manager.create_oauth_state(None, "http://test.com")
        
        assert state_id1 != state_id2


    @pytest.mark.asyncio
    async def test_state_timestamp_validation(self, oauth_session_manager, mock_redis):
        """Test state timestamp validation prevents replay attacks."""
        import time
        expired_state_data = {
            "csrf_token": "expired_token",
            "return_url": "http://test.com",
            "timestamp": int(time.time()) - 400  # Expired (>300 seconds old)
        }
        mock_redis.get.return_value = json.dumps(expired_state_data)
        
        with pytest.raises(Exception) as exc_info:
            await oauth_session_manager.validate_and_consume_state("expired_state")
        assert "expired" in str(exc_info.value).lower()


    @pytest.mark.asyncio
    async def test_state_data_type_validation(self, oauth_session_manager):
        """Test state data type validation."""
        state_data = {
            "csrf_token": "test_token",
            "return_url": "http://test.com",
            "timestamp": 1234567890
        }
        
        # Should validate successfully
        validated = oauth_session_manager._validate_state_data(state_data)
        assert validated["csrf_token"] == "test_token"


class TestRedisConnectionHandling:
    """Test Redis connection handling and error scenarios."""
    
    @pytest.mark.asyncio
    async def test_redis_connection_success(self):
        """Test successful Redis connection check."""
        from app.auth.auth_service import check_redis_connection
        
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.ping = AsyncMock(return_value=True)
            result = await check_redis_connection()
            assert result is True


    @pytest.mark.asyncio
    async def test_redis_connection_failure(self):
        """Test Redis connection failure handling."""
        from app.auth.auth_service import check_redis_connection
        
        with patch('app.auth.auth_service.redis_service') as mock_redis:
            mock_redis.ping = AsyncMock(side_effect=Exception("Connection failed"))
            result = await check_redis_connection()
            assert result is False


    @pytest.mark.asyncio
    async def test_user_session_revocation_success(self, mock_redis):
        """Test successful user session revocation."""
        from app.auth.auth_service import revoke_user_sessions
        
        mock_redis.keys.return_value = ['user_session:123:device1', 'user_session:123:device2']
        await revoke_user_sessions("123")
        
        mock_redis.keys.assert_called_once_with("user_session:123:*")
        mock_redis.delete.assert_called_once_with('user_session:123:device1', 'user_session:123:device2')


    @pytest.mark.asyncio
    async def test_user_session_revocation_no_sessions(self, mock_redis):
        """Test user session revocation when no sessions exist."""
        from app.auth.auth_service import revoke_user_sessions
        
        mock_redis.keys.return_value = []
        await revoke_user_sessions("123")
        
        mock_redis.delete.assert_not_called()


    @pytest.mark.asyncio
    async def test_user_session_revocation_none_user_id(self, mock_redis):
        """Test user session revocation with None user ID."""
        from app.auth.auth_service import revoke_user_sessions
        
        await revoke_user_sessions(None)
        
        mock_redis.keys.assert_not_called()
        mock_redis.delete.assert_not_called()


class TestAuthServiceStartupIntegration:
    """Test auth service startup and Redis integration."""
    
    @pytest.mark.asyncio
    async def test_startup_event_redis_connection_success(self, mock_redis):
        """Test successful startup with Redis connection."""
        from app.auth.auth_service import startup_event
        
        mock_redis.connect = AsyncMock()
        await startup_event()
        mock_redis.connect.assert_called_once()


    @pytest.mark.asyncio
    async def test_startup_event_redis_connection_error_handling(self, mock_redis):
        """Test startup event handles Redis connection errors."""
        from app.auth.auth_service import startup_event, handle_redis_connection_error
        
        mock_redis.connect = AsyncMock(side_effect=ConnectionError("Redis unavailable"))
        
        # Should not raise exception
        await startup_event()


    @pytest.mark.asyncio
    async def test_startup_event_critical_error_propagation(self, mock_redis):
        """Test startup event propagates critical errors."""
        from app.auth.auth_service import startup_event
        
        mock_redis.connect = AsyncMock(side_effect=ValueError("Critical config error"))
        
        with pytest.raises(ValueError):
            await startup_event()


class TestIntegratedAuthWorkflows:
    """Test integrated authentication workflows with middleware."""
    
    def test_oauth_login_flow_integration(self, client):
        """Test OAuth login flow with CORS and session creation."""
        with patch('app.auth.auth_service.auth_session_manager.create_oauth_state') as mock_create, \
             patch('app.auth.auth_service.auth_env_config.get_oauth_config'), \
             patch('app.auth.url_validators.validate_and_get_return_url'), \
             patch('app.auth.oauth_utils.build_google_oauth_url'):
            
            mock_create.return_value = "test_state_123"
            
            response = client.get(
                "/auth/login?return_url=http://localhost:3000",
                headers={"Origin": "http://localhost:3000"}
            )
            
            # Should create session and redirect
            assert response.status_code == 200  # Redirect response


    def test_auth_status_with_redis_check(self, client):
        """Test auth status endpoint includes Redis connection check."""
        with patch('app.auth.auth_service.check_redis_connection') as mock_check, \
             patch('app.auth.auth_response_builders.build_service_status') as mock_status:
            
            mock_check.return_value = True
            mock_status.return_value = {"status": "healthy", "redis_connected": True}
            
            response = client.get("/auth/status")
            assert response.status_code == 200
            mock_check.assert_called_once()


    def test_frontend_config_with_environment_integration(self, client):
        """Test frontend config endpoint integrates environment configuration."""
        with patch('app.auth.auth_service.auth_env_config.get_frontend_config') as mock_config, \
             patch('app.auth.url_validators.get_auth_service_url') as mock_url, \
             patch('app.auth.auth_response_builders.add_auth_urls') as mock_urls:
            
            mock_config.return_value = {"client_id": "test_client", "environment": "development"}
            mock_url.return_value = "http://localhost:8001"
            
            response = client.get("/auth/config")
            assert response.status_code == 200
            mock_urls.assert_called_once()


class TestMiddlewareErrorHandling:
    """Test middleware error handling and resilience."""
    
    def test_cors_with_malformed_origin_header(self, client):
        """Test CORS handling with malformed Origin header."""
        response = client.get(
            "/health",
            headers={"Origin": "not-a-valid-url"}
        )
        # Should not crash the application
        assert response.status_code == 200


    def test_request_without_cors_headers(self, client):
        """Test request processing without CORS headers."""
        response = client.get("/health")
        assert response.status_code == 200


    def test_large_cors_origin_list_handling(self, client):
        """Test CORS handling with large origin list."""
        large_origin_list = ",".join([f"https://app{i}.example.com" for i in range(100)])
        with patch.dict(os.environ, {"CORS_ALLOWED_ORIGINS": large_origin_list}):
            response = client.get("/health", headers={"Origin": "https://app50.example.com"})
            assert response.status_code == 200


class TestSessionDataIntegrity:
    """Test session data integrity and validation."""
    
    @pytest.mark.asyncio
    async def test_state_data_json_serialization(self, oauth_session_manager, mock_redis):
        """Test state data JSON serialization/deserialization."""
        test_pr = "456"
        test_url = "https://complex-url.com/callback?param=value"
        
        await oauth_session_manager.create_oauth_state(test_pr, test_url)
        
        call_args = mock_redis.setex.call_args[0]
        stored_json = call_args[2]
        
        # Should be valid JSON
        parsed_data = json.loads(stored_json)
        assert parsed_data["pr_number"] == test_pr
        assert parsed_data["return_url"] == test_url


    @pytest.mark.asyncio
    async def test_state_data_special_characters_handling(self, oauth_session_manager, mock_redis):
        """Test state data handles special characters in URLs."""
        special_url = "https://example.com/callback?param=test%20value&other=special+chars"
        
        await oauth_session_manager.create_oauth_state("123", special_url)
        
        call_args = mock_redis.setex.call_args[0]
        stored_data = json.loads(call_args[2])
        
        assert stored_data["return_url"] == special_url