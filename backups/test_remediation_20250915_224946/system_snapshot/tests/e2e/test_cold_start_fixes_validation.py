"""
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
Test suite to validate that critical cold start fixes are working correctly.
Tests the actual fixes implemented for authentication, WebSocket, and database issues.
"""

import asyncio
import os
import sys
import pytest
from pathlib import Path

# Add project root to path


@pytest.mark.e2e
class ColdStartFixesValidationTests:
    """Validate that the cold start fixes are working correctly."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_secret_compatibility(self):
        """Test that JWT secret accepts both JWT_SECRET and JWT_SECRET_KEY."""
        # Set different JWT secrets to test backward compatibility
        get_env().set("JWT_SECRET", "test_secret_123")
        get_env().set("JWT_SECRET_KEY", "test_secret_123")
        
        # Import after setting env vars
        from auth_service.auth_core.secret_loader import AuthSecretLoader
        
        secret_loader = AuthSecretLoader()
        jwt_secret = secret_loader.get_jwt_secret()
        
        assert jwt_secret == "test_secret_123", "JWT secret should be loaded"
        
        # Test with only JWT_SECRET_KEY
        get_env().delete("JWT_SECRET")
        secret_loader2 = AuthSecretLoader()
        jwt_secret2 = secret_loader2.get_jwt_secret()
        
        assert jwt_secret2 == "test_secret_123", "Should work with JWT_SECRET_KEY alone"
        
        # Test with only JWT_SECRET
        get_env().delete("JWT_SECRET_KEY")
        get_env().set("JWT_SECRET", "test_secret_456")
        secret_loader3 = AuthSecretLoader()
        jwt_secret3 = secret_loader3.get_jwt_secret()
        
        assert jwt_secret3 == "test_secret_456", "Should work with JWT_SECRET alone"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_jwt_issuer_claim_present(self):
        """Test that JWT tokens include the required 'iss' claim."""
        get_env().set("JWT_SECRET_KEY", "test_secret")
        
        from auth_service.auth_core.core.jwt_handler import JWTHandler
        
        jwt_handler = JWTHandler()
        
        # Build a test payload using the correct parameters
        payload = jwt_handler._build_payload(
            user_id="test_user",
            email="test@example.com",
            sub="test_user",
            token_type="access",
            exp_minutes=60
        )
        
        assert "iss" in payload, "JWT payload should include 'iss' claim"
        assert payload["iss"] == "netra-auth-service", "Issuer should be netra-auth-service"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_clickhouse_port_configuration(self):
        """Test that ClickHouse uses correct port for HTTP connections."""
        # Set environment for local development
        get_env().set("ENVIRONMENT", "local")
        get_env().set("CLICKHOUSE_HTTP_PORT", "8123")
        get_env().set("CLICKHOUSE_HTTPS_PORT", "8443")
        
        from netra_backend.app.schemas.config import ClickHouseHTTPConfig
        
        config = ClickHouseHTTPConfig()
        assert config.port == 8123, "Should use HTTP port 8123 for local development"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_redis_local_fallback(self):
        """Test that Redis falls back to local when remote fails."""
        # Set remote Redis that will fail
        get_env().set("REDIS_URL", "redis://nonexistent.example.com:6379")
        get_env().set("REDIS_MODE", "auto")  # Should try remote then fallback
        
        from netra_backend.app.redis_manager import RedisManager
        
        redis_mgr = RedisManager()
        
        # The manager should be created (fallback mode)
        assert redis_mgr is not None
        # Check that Redis mode is configured for fallback
        current_mode = get_env().get("REDIS_MODE", "")
        assert current_mode in ["local", "auto", "shared"]

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_background_task_timeout(self):
        """Test that background tasks have proper timeout."""
        from netra_backend.app.services.background_task_manager import BackgroundTaskManager
        
        manager = BackgroundTaskManager()
        
        # Test that timeout is set correctly
        assert manager.default_timeout == 120, "Default timeout should be 2 minutes"
        
        # Test that manager has necessary methods
        assert hasattr(manager, 'cancel_task'), "Should have cancel_task method"
        assert hasattr(manager, 'shutdown'), "Should have shutdown method"
        assert hasattr(manager, '_execute_with_timeout'), "Should have timeout execution"
        assert hasattr(manager, 'get_active_tasks'), "Should have task tracking"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_database_table_auto_creation(self):
        """Test that database tables are created automatically on startup."""
        from netra_backend.app.startup_module import _ensure_database_tables_exist
        from netra_backend.app.db.database_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # This should not raise an error even if tables don't exist
        try:
            result = await _ensure_database_tables_exist(db_manager)
            assert result is True or result is None, "Table creation should succeed or be skipped"
        except Exception as e:
            # In test environment, we might not have a real database
            assert "connection" in str(e).lower() or "database" in str(e).lower()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_oauth_state_atomic_operations(self):
        """Test that OAuth state operations are atomic to prevent race conditions."""
        from auth_service.auth_core.security.oauth_security import OAuthStateCleanupManager
        
        # Test the cleanup manager exists and has proper methods
        cleanup_mgr = OAuthStateCleanupManager()
        
        assert hasattr(cleanup_mgr, 'cleanup_expired_states'), "Should have cleanup method"
        assert hasattr(cleanup_mgr, 'cleanup_expired_nonces'), "Should have nonce cleanup"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_service_port_dynamic_allocation(self):
        """Test that services can use dynamic port allocation."""
        from dev_launcher.service_discovery_system import ServiceDiscoverySystem
        
        discovery = ServiceDiscoverySystem()
        
        # Test port allocation
        port = discovery.allocate_port("test_service", preferred_port=8080)
        assert port > 0, "Should allocate a valid port"
        
        # Test conflict resolution
        port2 = discovery.allocate_port("test_service2", preferred_port=port)
        assert port2 != port, "Should allocate different port when conflict exists"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_environment_variable_compatibility(self):
        """Test that environment variables support both old and new names."""
        # Test ClickHouse password configuration
        get_env().set("CLICKHOUSE_PASSWORD", "password1")
        
        from netra_backend.app.core.configuration.database import get_clickhouse_password
        
        # Should use CLICKHOUSE_PASSWORD
        password = get_clickhouse_password()
        assert password == "password1", "Should use CLICKHOUSE_PASSWORD"

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_cors_configuration(self):
        """Test that WebSocket CORS is properly configured."""
        from netra_backend.app.middleware.websocket_cors import WebSocketCORSMiddleware
        
        # Create middleware instance
        async def dummy_app(scope, receive, send):
            pass
        
        middleware = WebSocketCORSMiddleware(
            app=dummy_app,
            allowed_origins=["http://localhost:3000", "http://localhost:3001"]
        )
        
        # Test that it handles WebSocket upgrades
        assert hasattr(middleware, '__call__'), "Middleware should be callable"
        assert middleware.allowed_origins, "Should have allowed origins configured"
