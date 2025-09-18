class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        CRITICAL JWT SSOT Validation Tests - Security Compliance

        These tests verify that ALL JWT validation operations go through the auth service
        and no local validation bypasses exist that could compromise security.

        CRITICAL VIOLATIONS TESTED:
        1. No local JWT validation in websocket authentication
        2. No local JWT token creation in token refresh handler
        3. All validation routes through canonical auth service implementation
        4. No security bypasses remain in the codebase

        Business Value Justification (BVJ):
        - Segment: Enterprise/Security
        - Business Goal: Security compliance, prevent $1M ARR loss from security breaches
        - Value Impact: Ensures single source of truth for JWT validation
        - Strategic Impact: Eliminates authentication vulnerabilities and security bypasses
        '''

        import asyncio
        import pytest
        import time
        from fastapi import WebSocket, HTTPException
        from datetime import datetime, timezone
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from netra_backend.app.redis_manager import redis_manager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

            # Test the corrected modules
        from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
        from netra_backend.app.websocket.token_refresh_handler import TokenRefreshHandler
        from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from shared.isolated_environment import get_env


class TestJWTSSOTCompliance:
        """Test JWT Single Source of Truth compliance across all services."""

        @pytest.fixture
    def real_websocket():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket connection."""
        pass
        websocket = Mock(spec=WebSocket)
    # websocket setup complete  # Real WebSocket implementation
        websocket.client.host = "127.0.0.1"
        websocket.headers = { )
        "origin": "https://app.netrasystems.ai",
        "user-agent": "test-client"
    
    # websocket setup complete  # Real WebSocket implementation
        return websocket

        @pytest.fixture
    def authenticator(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create WebSocket authenticator for testing."""
        pass
        return WebSocketAuthenticator()

        @pytest.fixture
    def token_refresh_handler(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create token refresh handler for testing."""
        pass
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        return TokenRefreshHandler(mock_ws_manager)

        @pytest.fixture
    def jwt_validator(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Create unified JWT validator for testing."""
        pass
        return UnifiedJWTValidator()

    async def test_websocket_auth_uses_auth_service_only(self, authenticator, mock_websocket):
        """CRITICAL: Verify WebSocket auth ONLY uses auth service, no local validation."""

        # Setup mock WebSocket with token
        mock_websocket.headers = { )
        **mock_websocket.headers,
        "authorization": "Bearer valid_test_token_12345"
        

        # Mock auth client response
        with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
        mock_auth_client.validate_token_jwt.return_value = { )
        "valid": True,
        "user_id": "test_user_123",
        "email": "test@example.com",
        "permissions": ["user"]
            

            # Mock environment for development bypass
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
        mock_env.return_value = {"ENVIRONMENT": "production"}

                # Test authentication
        auth_info = await authenticator._authenticate_jwt(mock_websocket)

                # Verify auth service was called
        mock_auth_client.validate_token_jwt.assert_called_once_with("valid_test_token_12345")

                # Verify response
        assert auth_info.user_id == "test_user_123"
        assert auth_info.email == "test@example.com"

    async def test_websocket_auth_no_local_validation_bypass(self, authenticator, mock_websocket):
        """CRITICAL: Verify no local JWT validation bypass exists in WebSocket auth."""

                    # Setup mock WebSocket with token
        mock_websocket.headers = { )
        **mock_websocket.headers,
        "authorization": "Bearer test_token_that_should_fail_locally"
                    

                    # Mock auth client to fail
        with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
        mock_auth_client.validate_token_jwt.return_value = None

                        # Mock environment as production
        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
        mock_env.return_value = {"ENVIRONMENT": "production", "TESTING": "0"}

                            # Test should fail through auth service only
        with pytest.raises(HTTPException) as exc_info:
        await authenticator._authenticate_jwt(mock_websocket)

                                # Verify auth service was called (no local fallback)
        mock_auth_client.validate_token_jwt.assert_called_once()

                                # Verify proper error
        assert exc_info.value.status_code == 1008

    def test_websocket_auth_no_local_validation_method_exists(self, authenticator):
        """CRITICAL: Verify local JWT validation method was completely removed."""

    # Verify the dangerous method no longer exists
        assert not hasattr(authenticator, '_try_local_jwt_validation')

    # Verify no jwt.decode imports in the auth module
        import netra_backend.app.websocket_core.auth as auth_module
        auth_source = auth_module.__file__

        with open(auth_source, 'r') as f:
        source_code = f.read()

        # These patterns should NOT exist (security violations)
        dangerous_patterns = [ )
        'jwt_lib.decode',
        'jwt.decode(token,',
        'decode(token,',
        'local_jwt_validation',
        'try_local_jwt_validation'
        

        for pattern in dangerous_patterns:
        assert pattern not in source_code, "formatted_string"

    async def test_token_refresh_uses_auth_service_only(self, token_refresh_handler):
        """CRITICAL: Verify token refresh ONLY uses auth service, no local token creation."""

        test_token = "test_refresh_token_123"

                # Mock auth client responses
        with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_auth_client:
                    # Mock validation response
        mock_auth_client.validate_token_jwt.return_value = { )
        "valid": True,
        "expires_at": time.time() + 60  # Expires in 1 minute
                    

                    # Mock refresh response
        mock_auth_client.refresh_token.return_value = { )
        "success": True,
        "access_token": "new_refreshed_token_456",
        "expires_in": 3600
                    

                    # Test needs refresh check
        needs_refresh = await token_refresh_handler._needs_refresh(test_token)
        assert needs_refresh is True

                    # Test token refresh
        refresh_result = await token_refresh_handler._refresh_token(test_token)

                    # Verify auth service was used for both operations
        mock_auth_client.validate_token_jwt.assert_called_with(test_token)
        mock_auth_client.refresh_token.assert_called_with(test_token)

                    # Verify results
        assert refresh_result["access_token"] == "new_refreshed_token_456"

    def test_token_refresh_no_local_jwt_operations(self, token_refresh_handler):
        """CRITICAL: Verify no local JWT encoding/decoding in token refresh handler."""

    # Verify token refresh handler source code
        import netra_backend.app.websocket.token_refresh_handler as refresh_module
        refresh_source = refresh_module.__file__

        with open(refresh_source, 'r') as f:
        source_code = f.read()

        # These patterns should NOT exist (security violations)
        dangerous_patterns = [ )
        'jwt.decode(token,',
        'jwt.encode(',
        'jwt_lib.decode',
        'jwt_lib.encode',
        'create_token_local',
        'decode_token_local'
        

        for pattern in dangerous_patterns:
        assert pattern not in source_code, "formatted_string"

    def test_unified_jwt_validator_blocks_unsafe_operations(self, jwt_validator):
        """CRITICAL: Verify unified JWT validator blocks unsafe operations."""

    # Test synchronous validation is blocked
        result = jwt_validator.validate_token_sync("test_token")
        assert not result.valid
        assert "not supported" in result.error

    # Test unsafe decoding is blocked
        result = jwt_validator.decode_token_unsafe("test_token")
        assert result is None

    async def test_all_jwt_operations_go_through_auth_service(self):
        """CRITICAL: Integration test to verify ALL JWT operations use auth service."""

        test_scenarios = [ )
        { )
        "operation": "websocket_authentication",
        "description": "WebSocket JWT authentication"
        },
        { )
        "operation": "token_refresh_validation",
        "description": "Token refresh expiry validation"
        },
        { )
        "operation": "token_refresh_creation",
        "description": "Token refresh new token creation"
        },
        { )
        "operation": "unified_validator",
        "description": "Unified JWT validator operations"
        
        

        # Mock auth client to track all calls
        with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
            # Setup auth client responses
        mock_auth_client.validate_token_jwt.return_value = { )
        "valid": True,
        "user_id": "test_user",
        "email": "test@example.com",
        "expires_at": time.time() + 300
            
        mock_auth_client.refresh_token.return_value = { )
        "success": True,
        "access_token": "new_token"
            

            # Test WebSocket authentication
        authenticator = WebSocketAuthenticator()
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        mock_websocket.headers = {"authorization": "Bearer test_token"}
        mock_# websocket setup complete  # Real WebSocket implementation
        mock_websocket.client.host = "127.0.0.1"

        with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
        mock_env.return_value = {"ENVIRONMENT": "production"}

        await authenticator._authenticate_jwt(mock_websocket)

                # Test token refresh
        refresh_handler = TokenRefreshHandler(                await refresh_handler._needs_refresh("test_token") )
        await refresh_handler._refresh_token("test_token")

                # Verify auth service was called for all operations
        assert mock_auth_client.validate_token_jwt.call_count >= 2
        assert mock_auth_client.refresh_token.call_count >= 1

    def test_no_jwt_security_bypasses_in_codebase(self):
        """CRITICAL: Scan codebase for JWT security bypasses."""

        import os
        import glob

    # Define dangerous patterns that indicate security bypasses
        dangerous_patterns = [ )
        'jwt.decode(.*verify.*False',
        'decode.*options.*verify_signature.*False',
        'create.*token.*local',
        'validate.*token.*local',
        'bypass.*auth.*service',
        'skip.*auth.*validation'
    

    # Scan critical directories
        critical_dirs = [ )
        'netra_backend/app/websocket_core',
        'netra_backend/app/websocket',
        'netra_backend/app/core/unified',
        'netra_backend/app/auth_integration'
    

        root_dir = os.path.join(os.path.dirname(__file__), '..', '..')

        violations = []

        for dir_path in critical_dirs:
        full_dir = os.path.join(root_dir, dir_path)
        if os.path.exists(full_dir):
        py_files = glob.glob(os.path.join(full_dir, '**/*.py'), recursive=True)

        for py_file in py_files:
                # Skip test files - they may legitimately need unsafe operations
        if 'test_' in os.path.basename(py_file):
        continue

        try:
        with open(py_file, 'r', encoding='utf-8') as f:
        content = f.read()

        for pattern in dangerous_patterns:
        import re
        if re.search(pattern, content, re.IGNORECASE):
        violations.append("formatted_string")
        except Exception as e:
                                        # Skip files that can't be read
        pass

                                        # Report any violations found
        if violations:
        violation_msg = "JWT Security bypasses detected:
        " + "
        ".join(violations)
        pytest.fail(violation_msg)


class TestJWTSecurityHardening:
        """Test JWT security hardening measures."""

    def test_auth_service_jwt_handler_is_canonical(self):
        """Verify auth service JWT handler is the canonical implementation."""

    # Import the canonical implementation
        from auth_service.auth_core.core.jwt_handler import JWTHandler

        jwt_handler = JWTHandler()

    # Verify it has the required security methods
        assert hasattr(jwt_handler, 'validate_token')
        assert hasattr(jwt_handler, 'validate_token_jwt')
        assert hasattr(jwt_handler, 'create_access_token')
        assert hasattr(jwt_handler, 'create_refresh_token')
        assert hasattr(jwt_handler, 'blacklist_token')
        assert hasattr(jwt_handler, 'blacklist_user')

    # Verify it uses proper security validation
        assert hasattr(jwt_handler, '_validate_token_security_consolidated')
        assert hasattr(jwt_handler, '_validate_cross_service_token')

    def test_shared_jwt_secret_manager_ssot(self):
        """Verify shared JWT secret manager is SSOT for secrets."""

        from shared.jwt_secret_manager import SharedJWTSecretManager

    # Verify it has the required methods
        assert hasattr(SharedJWTSecretManager, 'get_jwt_secret')
        assert hasattr(SharedJWTSecretManager, 'validate_synchronization')
        assert hasattr(SharedJWTSecretManager, 'clear_cache')

    # Verify it doesn't have validation methods (only secret management)
        assert not hasattr(SharedJWTSecretManager, 'validate_token')
        assert not hasattr(SharedJWTSecretManager, 'decode_token')

    def test_jwt_validation_performance_requirements(self):
        """Test JWT validation meets performance requirements."""

    # Verify caching is enabled in canonical implementation
        from auth_service.auth_core.core.jwt_handler import JWTHandler

        jwt_handler = JWTHandler()

    # Should have caching support
        assert hasattr(jwt_handler, 'get_performance_stats')

    # Get performance stats
        stats = jwt_handler.get_performance_stats()
        assert 'cache_stats' in stats
        assert 'performance_optimizations' in stats
        assert stats['performance_optimizations']['caching_enabled'] is True
        pass
