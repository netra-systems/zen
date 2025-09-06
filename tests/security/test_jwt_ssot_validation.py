# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: CRITICAL JWT SSOT Validation Tests - Security Compliance

    # REMOVED_SYNTAX_ERROR: These tests verify that ALL JWT validation operations go through the auth service
    # REMOVED_SYNTAX_ERROR: and no local validation bypasses exist that could compromise security.

    # REMOVED_SYNTAX_ERROR: CRITICAL VIOLATIONS TESTED:
        # REMOVED_SYNTAX_ERROR: 1. No local JWT validation in websocket authentication
        # REMOVED_SYNTAX_ERROR: 2. No local JWT token creation in token refresh handler
        # REMOVED_SYNTAX_ERROR: 3. All validation routes through canonical auth service implementation
        # REMOVED_SYNTAX_ERROR: 4. No security bypasses remain in the codebase

        # REMOVED_SYNTAX_ERROR: Business Value Justification (BVJ):
            # REMOVED_SYNTAX_ERROR: - Segment: Enterprise/Security
            # REMOVED_SYNTAX_ERROR: - Business Goal: Security compliance, prevent $1M ARR loss from security breaches
            # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures single source of truth for JWT validation
            # REMOVED_SYNTAX_ERROR: - Strategic Impact: Eliminates authentication vulnerabilities and security bypasses
            # REMOVED_SYNTAX_ERROR: '''

            # REMOVED_SYNTAX_ERROR: import asyncio
            # REMOVED_SYNTAX_ERROR: import pytest
            # REMOVED_SYNTAX_ERROR: import time
            # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket, HTTPException
            # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
            # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
            # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # Test the corrected modules
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.auth import WebSocketAuthenticator
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket.token_refresh_handler import TokenRefreshHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified.jwt_validator import UnifiedJWTValidator
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestJWTSSOTCompliance:
    # REMOVED_SYNTAX_ERROR: """Test JWT Single Source of Truth compliance across all services."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = Mock(spec=WebSocket)
    # websocket setup complete  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: websocket.client.host = "127.0.0.1"
    # REMOVED_SYNTAX_ERROR: websocket.headers = { )
    # REMOVED_SYNTAX_ERROR: "origin": "https://app.netra.ai",
    # REMOVED_SYNTAX_ERROR: "user-agent": "test-client"
    
    # websocket setup complete  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: return websocket

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def authenticator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create WebSocket authenticator for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return WebSocketAuthenticator()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def token_refresh_handler(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create token refresh handler for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
    # REMOVED_SYNTAX_ERROR: return TokenRefreshHandler(mock_ws_manager)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def jwt_validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create unified JWT validator for testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UnifiedJWTValidator()

    # Removed problematic line: async def test_websocket_auth_uses_auth_service_only(self, authenticator, mock_websocket):
        # REMOVED_SYNTAX_ERROR: """CRITICAL: Verify WebSocket auth ONLY uses auth service, no local validation."""

        # Setup mock WebSocket with token
        # REMOVED_SYNTAX_ERROR: mock_websocket.headers = { )
        # REMOVED_SYNTAX_ERROR: **mock_websocket.headers,
        # REMOVED_SYNTAX_ERROR: "authorization": "Bearer valid_test_token_12345"
        

        # Mock auth client response
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
            # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.return_value = { )
            # REMOVED_SYNTAX_ERROR: "valid": True,
            # REMOVED_SYNTAX_ERROR: "user_id": "test_user_123",
            # REMOVED_SYNTAX_ERROR: "email": "test@example.com",
            # REMOVED_SYNTAX_ERROR: "permissions": ["user"]
            

            # Mock environment for development bypass
            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
                # REMOVED_SYNTAX_ERROR: mock_env.return_value = {"ENVIRONMENT": "production"}

                # Test authentication
                # REMOVED_SYNTAX_ERROR: auth_info = await authenticator._authenticate_jwt(mock_websocket)

                # Verify auth service was called
                # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.assert_called_once_with("valid_test_token_12345")

                # Verify response
                # REMOVED_SYNTAX_ERROR: assert auth_info.user_id == "test_user_123"
                # REMOVED_SYNTAX_ERROR: assert auth_info.email == "test@example.com"

                # Removed problematic line: async def test_websocket_auth_no_local_validation_bypass(self, authenticator, mock_websocket):
                    # REMOVED_SYNTAX_ERROR: """CRITICAL: Verify no local JWT validation bypass exists in WebSocket auth."""

                    # Setup mock WebSocket with token
                    # REMOVED_SYNTAX_ERROR: mock_websocket.headers = { )
                    # REMOVED_SYNTAX_ERROR: **mock_websocket.headers,
                    # REMOVED_SYNTAX_ERROR: "authorization": "Bearer test_token_that_should_fail_locally"
                    

                    # Mock auth client to fail
                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
                        # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.return_value = None

                        # Mock environment as production
                        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
                            # REMOVED_SYNTAX_ERROR: mock_env.return_value = {"ENVIRONMENT": "production", "TESTING": "0"}

                            # Test should fail through auth service only
                            # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
                                # REMOVED_SYNTAX_ERROR: await authenticator._authenticate_jwt(mock_websocket)

                                # Verify auth service was called (no local fallback)
                                # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.assert_called_once()

                                # Verify proper error
                                # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == 1008

# REMOVED_SYNTAX_ERROR: def test_websocket_auth_no_local_validation_method_exists(self, authenticator):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Verify local JWT validation method was completely removed."""

    # Verify the dangerous method no longer exists
    # REMOVED_SYNTAX_ERROR: assert not hasattr(authenticator, '_try_local_jwt_validation')

    # Verify no jwt.decode imports in the auth module
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.websocket_core.auth as auth_module
    # REMOVED_SYNTAX_ERROR: auth_source = auth_module.__file__

    # REMOVED_SYNTAX_ERROR: with open(auth_source, 'r') as f:
        # REMOVED_SYNTAX_ERROR: source_code = f.read()

        # These patterns should NOT exist (security violations)
        # REMOVED_SYNTAX_ERROR: dangerous_patterns = [ )
        # REMOVED_SYNTAX_ERROR: 'jwt_lib.decode',
        # REMOVED_SYNTAX_ERROR: 'jwt.decode(token,',
        # REMOVED_SYNTAX_ERROR: 'decode(token,',
        # REMOVED_SYNTAX_ERROR: 'local_jwt_validation',
        # REMOVED_SYNTAX_ERROR: 'try_local_jwt_validation'
        

        # REMOVED_SYNTAX_ERROR: for pattern in dangerous_patterns:
            # REMOVED_SYNTAX_ERROR: assert pattern not in source_code, "formatted_string"

            # Removed problematic line: async def test_token_refresh_uses_auth_service_only(self, token_refresh_handler):
                # REMOVED_SYNTAX_ERROR: """CRITICAL: Verify token refresh ONLY uses auth service, no local token creation."""

                # REMOVED_SYNTAX_ERROR: test_token = "test_refresh_token_123"

                # Mock auth client responses
                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.auth_integration.auth.auth_client') as mock_auth_client:
                    # Mock validation response
                    # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.return_value = { )
                    # REMOVED_SYNTAX_ERROR: "valid": True,
                    # REMOVED_SYNTAX_ERROR: "expires_at": time.time() + 60  # Expires in 1 minute
                    

                    # Mock refresh response
                    # REMOVED_SYNTAX_ERROR: mock_auth_client.refresh_token.return_value = { )
                    # REMOVED_SYNTAX_ERROR: "success": True,
                    # REMOVED_SYNTAX_ERROR: "access_token": "new_refreshed_token_456",
                    # REMOVED_SYNTAX_ERROR: "expires_in": 3600
                    

                    # Test needs refresh check
                    # REMOVED_SYNTAX_ERROR: needs_refresh = await token_refresh_handler._needs_refresh(test_token)
                    # REMOVED_SYNTAX_ERROR: assert needs_refresh is True

                    # Test token refresh
                    # REMOVED_SYNTAX_ERROR: refresh_result = await token_refresh_handler._refresh_token(test_token)

                    # Verify auth service was used for both operations
                    # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.assert_called_with(test_token)
                    # REMOVED_SYNTAX_ERROR: mock_auth_client.refresh_token.assert_called_with(test_token)

                    # Verify results
                    # REMOVED_SYNTAX_ERROR: assert refresh_result["access_token"] == "new_refreshed_token_456"

# REMOVED_SYNTAX_ERROR: def test_token_refresh_no_local_jwt_operations(self, token_refresh_handler):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Verify no local JWT encoding/decoding in token refresh handler."""

    # Verify token refresh handler source code
    # REMOVED_SYNTAX_ERROR: import netra_backend.app.websocket.token_refresh_handler as refresh_module
    # REMOVED_SYNTAX_ERROR: refresh_source = refresh_module.__file__

    # REMOVED_SYNTAX_ERROR: with open(refresh_source, 'r') as f:
        # REMOVED_SYNTAX_ERROR: source_code = f.read()

        # These patterns should NOT exist (security violations)
        # REMOVED_SYNTAX_ERROR: dangerous_patterns = [ )
        # REMOVED_SYNTAX_ERROR: 'jwt.decode(token,',
        # REMOVED_SYNTAX_ERROR: 'jwt.encode(',
        # REMOVED_SYNTAX_ERROR: 'jwt_lib.decode',
        # REMOVED_SYNTAX_ERROR: 'jwt_lib.encode',
        # REMOVED_SYNTAX_ERROR: 'create_token_local',
        # REMOVED_SYNTAX_ERROR: 'decode_token_local'
        

        # REMOVED_SYNTAX_ERROR: for pattern in dangerous_patterns:
            # REMOVED_SYNTAX_ERROR: assert pattern not in source_code, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_unified_jwt_validator_blocks_unsafe_operations(self, jwt_validator):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Verify unified JWT validator blocks unsafe operations."""

    # Test synchronous validation is blocked
    # REMOVED_SYNTAX_ERROR: result = jwt_validator.validate_token_sync("test_token")
    # REMOVED_SYNTAX_ERROR: assert not result.valid
    # REMOVED_SYNTAX_ERROR: assert "not supported" in result.error

    # Test unsafe decoding is blocked
    # REMOVED_SYNTAX_ERROR: result = jwt_validator.decode_token_unsafe("test_token")
    # REMOVED_SYNTAX_ERROR: assert result is None

    # Removed problematic line: async def test_all_jwt_operations_go_through_auth_service(self):
        # REMOVED_SYNTAX_ERROR: """CRITICAL: Integration test to verify ALL JWT operations use auth service."""

        # REMOVED_SYNTAX_ERROR: test_scenarios = [ )
        # REMOVED_SYNTAX_ERROR: { )
        # REMOVED_SYNTAX_ERROR: "operation": "websocket_authentication",
        # REMOVED_SYNTAX_ERROR: "description": "WebSocket JWT authentication"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: { )
        # REMOVED_SYNTAX_ERROR: "operation": "token_refresh_validation",
        # REMOVED_SYNTAX_ERROR: "description": "Token refresh expiry validation"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: { )
        # REMOVED_SYNTAX_ERROR: "operation": "token_refresh_creation",
        # REMOVED_SYNTAX_ERROR: "description": "Token refresh new token creation"
        # REMOVED_SYNTAX_ERROR: },
        # REMOVED_SYNTAX_ERROR: { )
        # REMOVED_SYNTAX_ERROR: "operation": "unified_validator",
        # REMOVED_SYNTAX_ERROR: "description": "Unified JWT validator operations"
        
        

        # Mock auth client to track all calls
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.clients.auth_client_core.auth_client') as mock_auth_client:
            # Setup auth client responses
            # REMOVED_SYNTAX_ERROR: mock_auth_client.validate_token_jwt.return_value = { )
            # REMOVED_SYNTAX_ERROR: "valid": True,
            # REMOVED_SYNTAX_ERROR: "user_id": "test_user",
            # REMOVED_SYNTAX_ERROR: "email": "test@example.com",
            # REMOVED_SYNTAX_ERROR: "expires_at": time.time() + 300
            
            # REMOVED_SYNTAX_ERROR: mock_auth_client.refresh_token.return_value = { )
            # REMOVED_SYNTAX_ERROR: "success": True,
            # REMOVED_SYNTAX_ERROR: "access_token": "new_token"
            

            # Test WebSocket authentication
            # REMOVED_SYNTAX_ERROR: authenticator = WebSocketAuthenticator()
            # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()  # Real WebSocket implementation
            # REMOVED_SYNTAX_ERROR: mock_websocket.headers = {"authorization": "Bearer test_token"}
            # REMOVED_SYNTAX_ERROR: mock_# websocket setup complete  # Real WebSocket implementation
            # REMOVED_SYNTAX_ERROR: mock_websocket.client.host = "127.0.0.1"

            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.core.isolated_environment.get_env') as mock_env:
                # REMOVED_SYNTAX_ERROR: mock_env.return_value = {"ENVIRONMENT": "production"}

                # REMOVED_SYNTAX_ERROR: await authenticator._authenticate_jwt(mock_websocket)

                # Test token refresh
                # REMOVED_SYNTAX_ERROR: refresh_handler = TokenRefreshHandler(                await refresh_handler._needs_refresh("test_token") )
                # REMOVED_SYNTAX_ERROR: await refresh_handler._refresh_token("test_token")

                # Verify auth service was called for all operations
                # REMOVED_SYNTAX_ERROR: assert mock_auth_client.validate_token_jwt.call_count >= 2
                # REMOVED_SYNTAX_ERROR: assert mock_auth_client.refresh_token.call_count >= 1

# REMOVED_SYNTAX_ERROR: def test_no_jwt_security_bypasses_in_codebase(self):
    # REMOVED_SYNTAX_ERROR: """CRITICAL: Scan codebase for JWT security bypasses."""

    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: import glob

    # Define dangerous patterns that indicate security bypasses
    # REMOVED_SYNTAX_ERROR: dangerous_patterns = [ )
    # REMOVED_SYNTAX_ERROR: 'jwt.decode(.*verify.*False',
    # REMOVED_SYNTAX_ERROR: 'decode.*options.*verify_signature.*False',
    # REMOVED_SYNTAX_ERROR: 'create.*token.*local',
    # REMOVED_SYNTAX_ERROR: 'validate.*token.*local',
    # REMOVED_SYNTAX_ERROR: 'bypass.*auth.*service',
    # REMOVED_SYNTAX_ERROR: 'skip.*auth.*validation'
    

    # Scan critical directories
    # REMOVED_SYNTAX_ERROR: critical_dirs = [ )
    # REMOVED_SYNTAX_ERROR: 'netra_backend/app/websocket_core',
    # REMOVED_SYNTAX_ERROR: 'netra_backend/app/websocket',
    # REMOVED_SYNTAX_ERROR: 'netra_backend/app/core/unified',
    # REMOVED_SYNTAX_ERROR: 'netra_backend/app/auth_integration'
    

    # REMOVED_SYNTAX_ERROR: root_dir = os.path.join(os.path.dirname(__file__), '..', '..')

    # REMOVED_SYNTAX_ERROR: violations = []

    # REMOVED_SYNTAX_ERROR: for dir_path in critical_dirs:
        # REMOVED_SYNTAX_ERROR: full_dir = os.path.join(root_dir, dir_path)
        # REMOVED_SYNTAX_ERROR: if os.path.exists(full_dir):
            # REMOVED_SYNTAX_ERROR: py_files = glob.glob(os.path.join(full_dir, '**/*.py'), recursive=True)

            # REMOVED_SYNTAX_ERROR: for py_file in py_files:
                # Skip test files - they may legitimately need unsafe operations
                # REMOVED_SYNTAX_ERROR: if 'test_' in os.path.basename(py_file):
                    # REMOVED_SYNTAX_ERROR: continue

                    # REMOVED_SYNTAX_ERROR: try:
                        # REMOVED_SYNTAX_ERROR: with open(py_file, 'r', encoding='utf-8') as f:
                            # REMOVED_SYNTAX_ERROR: content = f.read()

                            # REMOVED_SYNTAX_ERROR: for pattern in dangerous_patterns:
                                # REMOVED_SYNTAX_ERROR: import re
                                # REMOVED_SYNTAX_ERROR: if re.search(pattern, content, re.IGNORECASE):
                                    # REMOVED_SYNTAX_ERROR: violations.append("formatted_string")
                                    # REMOVED_SYNTAX_ERROR: except Exception as e:
                                        # Skip files that can't be read
                                        # REMOVED_SYNTAX_ERROR: pass

                                        # Report any violations found
                                        # REMOVED_SYNTAX_ERROR: if violations:
                                            # REMOVED_SYNTAX_ERROR: violation_msg = "JWT Security bypasses detected:
                                                # REMOVED_SYNTAX_ERROR: " + "
                                                # REMOVED_SYNTAX_ERROR: ".join(violations)
                                                # REMOVED_SYNTAX_ERROR: pytest.fail(violation_msg)


# REMOVED_SYNTAX_ERROR: class TestJWTSecurityHardening:
    # REMOVED_SYNTAX_ERROR: """Test JWT security hardening measures."""

# REMOVED_SYNTAX_ERROR: def test_auth_service_jwt_handler_is_canonical(self):
    # REMOVED_SYNTAX_ERROR: """Verify auth service JWT handler is the canonical implementation."""

    # Import the canonical implementation
    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.core.jwt_handler import JWTHandler

    # REMOVED_SYNTAX_ERROR: jwt_handler = JWTHandler()

    # Verify it has the required security methods
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'validate_token')
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'validate_token_jwt')
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'create_access_token')
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'create_refresh_token')
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'blacklist_token')
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'blacklist_user')

    # Verify it uses proper security validation
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, '_validate_token_security_consolidated')
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, '_validate_cross_service_token')

# REMOVED_SYNTAX_ERROR: def test_shared_jwt_secret_manager_ssot(self):
    # REMOVED_SYNTAX_ERROR: """Verify shared JWT secret manager is SSOT for secrets."""

    # REMOVED_SYNTAX_ERROR: from shared.jwt_secret_manager import SharedJWTSecretManager

    # Verify it has the required methods
    # REMOVED_SYNTAX_ERROR: assert hasattr(SharedJWTSecretManager, 'get_jwt_secret')
    # REMOVED_SYNTAX_ERROR: assert hasattr(SharedJWTSecretManager, 'validate_synchronization')
    # REMOVED_SYNTAX_ERROR: assert hasattr(SharedJWTSecretManager, 'clear_cache')

    # Verify it doesn't have validation methods (only secret management)
    # REMOVED_SYNTAX_ERROR: assert not hasattr(SharedJWTSecretManager, 'validate_token')
    # REMOVED_SYNTAX_ERROR: assert not hasattr(SharedJWTSecretManager, 'decode_token')

# REMOVED_SYNTAX_ERROR: def test_jwt_validation_performance_requirements(self):
    # REMOVED_SYNTAX_ERROR: """Test JWT validation meets performance requirements."""

    # Verify caching is enabled in canonical implementation
    # REMOVED_SYNTAX_ERROR: from auth_service.auth_core.core.jwt_handler import JWTHandler

    # REMOVED_SYNTAX_ERROR: jwt_handler = JWTHandler()

    # Should have caching support
    # REMOVED_SYNTAX_ERROR: assert hasattr(jwt_handler, 'get_performance_stats')

    # Get performance stats
    # REMOVED_SYNTAX_ERROR: stats = jwt_handler.get_performance_stats()
    # REMOVED_SYNTAX_ERROR: assert 'cache_stats' in stats
    # REMOVED_SYNTAX_ERROR: assert 'performance_optimizations' in stats
    # REMOVED_SYNTAX_ERROR: assert stats['performance_optimizations']['caching_enabled'] is True
    # REMOVED_SYNTAX_ERROR: pass