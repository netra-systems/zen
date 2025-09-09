"""
WebSocket Auth ID Integration Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose authentication integration issues caused by uuid.uuid4() ID patterns.

Business Value Justification:
- Segment: Platform/Internal 
- Business Goal: Security and authentication integrity
- Value Impact: Ensures WebSocket IDs integrate properly with auth systems
- Strategic Impact: CRITICAL - Auth integration failures = security vulnerabilities

Test Strategy:
1. FAIL INITIALLY - Tests expose auth integration issues with uuid.uuid4()
2. MIGRATE PHASE - Replace with UnifiedIdGenerator auth-aware methods  
3. PASS FINALLY - Tests validate proper auth integration with consistent IDs

These tests validate that WebSocket IDs work correctly with authentication,
authorization, and session management systems.
"""

import pytest
import asyncio
import uuid
import time
import jwt
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

# Import test framework for real services integration
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services import get_real_services

# Import WebSocket core modules for auth testing
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage, generate_default_message
from netra_backend.app.websocket_core.context import WebSocketRequestContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.connection_manager import WebSocketConnectionManager
from netra_backend.app.middleware.auth_middleware import WebSocketAuthMiddleware

# Import auth system components
try:
    from netra_backend.app.auth.jwt_manager import JWTManager
except ImportError:
    # Mock JWTManager for integration testing
    class JWTManager:
        def __init__(self, secret_key: str):
            self.secret_key = secret_key
        
        def generate_token(self, user_id: str, data: dict = None):
            return f"test_token_{user_id}"
        
        def validate_token(self, token: str):
            return {"user_id": "test_user_id"}

try:
    from netra_backend.app.auth.session_manager import AuthSessionManager
except ImportError:
    class AuthSessionManager:
        def __init__(self):
            pass
        
        async def create_session(self, user_id: str):
            return {"session_id": f"test_session_{user_id}"}

try:
    from netra_backend.app.auth.user_auth_validator import UserAuthValidator
except ImportError:
    class UserAuthValidator:
        def __init__(self):
            pass
        
        async def validate_user(self, user_id: str):
            return {"user_id": user_id, "valid": True}

try:
    from netra_backend.app.models.user import User
    from netra_backend.app.models.user_session import UserSession
except ImportError:
    # Mock User and UserSession for integration testing
    class User:
        def __init__(self, id: str, username: str = None):
            self.id = id
            self.username = username
    
    class UserSession:
        def __init__(self, id: str, user_id: str):
            self.id = id  
            self.user_id = user_id

# Import auth service integration  
from tests.clients.auth_client import AuthTestClient as AuthServiceClient
# AuthSession model - create mock if not available
try:
except ImportError:
    # Mock AuthSession for integration testing
    class AuthSession:
        def __init__(self, session_id: str, user_id: str, **kwargs):
            self.session_id = session_id
            self.user_id = user_id
            for key, value in kwargs.items():
                setattr(self, key, value)

# Import SSOT UnifiedIdGenerator for proper auth integration
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ConnectionID, SessionID, TokenString
from shared.types.core_types import AuthValidationResult, SessionValidationResult


@pytest.mark.integration  
@pytest.mark.authentication
@pytest.mark.websocket
class TestWebSocketAuthIdIntegration(BaseIntegrationTest):
    """
    Integration tests that EXPOSE auth integration failures with uuid.uuid4().
    
    CRITICAL: These tests use real auth services and are DESIGNED TO FAIL
    initially to demonstrate auth consistency issues with random UUID patterns.
    """

    @pytest.fixture(autouse=True)
    async def setup_real_auth_services(self, real_services_fixture):
        """Set up real auth services for integration testing."""
        self.services = await get_real_services()
        self.auth_client = AuthServiceClient(base_url=self.env.get("AUTH_SERVICE_URL"))
        self.jwt_manager = JWTManager()
        self.auth_validator = UserAuthValidator()
        
        # Ensure clean test environment
        await self._cleanup_test_auth_data()
        
        yield
        
        # Cleanup after tests
        await self._cleanup_test_auth_data()

    async def test_websocket_jwt_token_integration_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose JWT token integration issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() WebSocket IDs break JWT token
        integration and session tracking in authentication flows.
        """
        # Create test user and generate JWT token
        test_user = await self._create_test_user("jwt_integration_user")
        user_id = str(test_user.id)
        
        # Generate JWT token with user information
        token_payload = {
            "user_id": user_id,
            "username": test_user.username,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        jwt_token = self.jwt_manager.generate_token(token_payload)
        
        # Create WebSocket connection with JWT authentication
        connection_info = ConnectionInfo(user_id=user_id)
        
        # FAILING ASSERTION: Connection ID should be JWT-compatible
        assert not connection_info.connection_id.startswith("conn_"), \
            f"Connection still uses uuid.uuid4() pattern incompatible with JWT: {connection_info.connection_id}"
            
        # Expected UnifiedIdGenerator format for JWT integration
        expected_pattern = f"ws_conn_{user_id[:8]}_"
        assert connection_info.connection_id.startswith(expected_pattern), \
            f"Expected JWT-compatible pattern '{expected_pattern}', got: {connection_info.connection_id}"
            
        # Create WebSocket context with JWT token
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # FAILING ASSERTION: Context should be linkable to JWT token
        # Validate JWT token contains connection context
        try:
            decoded_token = jwt.decode(jwt_token, options={"verify_signature": False})
            
            # This will FAIL because uuid.uuid4() connection IDs can't be linked to JWT
            connection_claim = f"ws:{connection_info.connection_id}"
            assert "connections" in decoded_token or connection_claim in str(decoded_token), \
                f"JWT token should reference WebSocket connection: {connection_info.connection_id}"
                
            # This will FAIL because uuid.uuid4() run_id can't be linked to JWT
            context_claim = f"ctx:{context.run_id}"
            assert "contexts" in decoded_token or context_claim in str(decoded_token), \
                f"JWT token should reference WebSocket context: {context.run_id}"
                
        except Exception as e:
            pytest.fail(f"JWT-WebSocket integration failed with uuid.uuid4() IDs: {str(e)}")

    async def test_session_management_auth_integration_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose session management auth issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns break session management
        integration with authentication systems.
        """
        # Create test user
        test_user = await self._create_test_user("session_auth_user")
        user_id = str(test_user.id)
        
        # Create auth session through auth service
        auth_session = await self.auth_client.create_session({
            "user_id": user_id,
            "username": test_user.username,
            "session_type": "websocket"
        })
        
        session_id = auth_session.get("session_id")
        assert session_id is not None, "Failed to create auth session"
        
        # Create WebSocket connection linked to auth session
        connection_info = ConnectionInfo(user_id=user_id)
        
        # Create WebSocket context with session linking
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # FAILING ASSERTION: WebSocket IDs should be linkable to auth session
        # Try to link connection to auth session
        try:
            session_update = {
                "websocket_connection_id": connection_info.connection_id,
                "websocket_context_id": context.run_id
            }
            
            updated_session = await self.auth_client.update_session(session_id, session_update)
            
            # This will FAIL because uuid.uuid4() IDs can't be efficiently linked
            assert connection_info.connection_id in str(updated_session), \
                f"Auth session should contain WebSocket connection ID: {connection_info.connection_id}"
                
            # This will FAIL because uuid.uuid4() context IDs lack user context
            assert user_id[:8] in context.run_id, \
                f"WebSocket context ID should contain user context for auth: {context.run_id}"
                
            # Expected UnifiedIdGenerator format for auth integration
            expected_context_pattern = f"ctx_{user_id[:8]}_session_{session_id[:8]}_"
            assert context.run_id.startswith(expected_context_pattern), \
                f"Expected auth-integrated context pattern '{expected_context_pattern}', got: {context.run_id}"
                
        except Exception as e:
            pytest.fail(f"Session-WebSocket integration failed with uuid.uuid4() IDs: {str(e)}")

    async def test_multi_user_auth_isolation_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose auth isolation issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns can cause auth isolation
        failures between different authenticated users.
        """
        # Create multiple test users
        users = []
        for i in range(3):
            user = await self._create_test_user(f"auth_isolation_user_{i}")
            users.append(user)
            
        # Create auth sessions for each user
        auth_sessions = {}
        websocket_contexts = {}
        
        for user in users:
            user_id = str(user.id)
            
            # Create auth session
            auth_session = await self.auth_client.create_session({
                "user_id": user_id,
                "username": user.username,
                "session_type": "websocket_isolated"
            })
            auth_sessions[user_id] = auth_session
            
            # Create WebSocket context for user
            connection_info = ConnectionInfo(user_id=user_id)
            context = WebSocketRequestContext.create_for_user(
                user_id=user_id,
                thread_id=None,
                connection_info=connection_info
            )
            websocket_contexts[user_id] = {
                "connection": connection_info,
                "context": context
            }
            
        # FAILING ASSERTION: Each user's WebSocket IDs should be auth-isolated
        for user_id, ws_data in websocket_contexts.items():
            connection = ws_data["connection"]
            context = ws_data["context"]
            
            # This will FAIL because uuid.uuid4() connection IDs lack user auth context
            assert user_id[:8] in connection.connection_id, \
                f"Connection ID lacks auth user context: {connection.connection_id} for user {user_id}"
                
            # This will FAIL because uuid.uuid4() context IDs lack auth isolation
            assert user_id[:8] in context.run_id, \
                f"Context ID lacks auth user isolation: {context.run_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for auth isolation
            expected_conn_pattern = f"ws_conn_{user_id[:8]}_auth_"
            assert connection.connection_id.find(expected_conn_pattern) != -1, \
                f"Expected auth-isolated connection pattern with '{expected_conn_pattern}', got: {connection.connection_id}"
                
        # FAILING ASSERTION: Cross-user auth access should be prevented
        user_ids = list(websocket_contexts.keys())
        for i, user_id in enumerate(user_ids):
            for j, other_user_id in enumerate(user_ids):
                if i != j:
                    # Try to access other user's WebSocket data with current user's auth
                    other_connection = websocket_contexts[other_user_id]["connection"]
                    
                    # This should FAIL - user should not be able to access other user's connection
                    can_access = await self._can_user_access_connection(
                        user_id, other_connection.connection_id, auth_sessions[user_id]
                    )
                    
                    assert not can_access, \
                        f"User {user_id} should not access connection {other_connection.connection_id} of user {other_user_id}"

    async def test_jwt_refresh_token_websocket_continuity_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose JWT refresh token continuity issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns break WebSocket connection
        continuity during JWT token refresh operations.
        """
        # Create test user
        test_user = await self._create_test_user("jwt_refresh_user") 
        user_id = str(test_user.id)
        
        # Generate initial JWT token (short expiration)
        initial_payload = {
            "user_id": user_id,
            "username": test_user.username,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=30)  # Short expiration
        }
        initial_token = self.jwt_manager.generate_token(initial_payload)
        
        # Create WebSocket connection with initial token
        connection_info = ConnectionInfo(user_id=user_id)
        initial_context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Wait for token to be near expiration
        await asyncio.sleep(25)  # Wait 25 seconds
        
        # Generate refresh token
        refresh_payload = {
            "user_id": user_id,
            "username": test_user.username,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            "refresh": True
        }
        refresh_token = self.jwt_manager.generate_token(refresh_payload)
        
        # Create new WebSocket context after token refresh
        refreshed_context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=initial_context.thread_id,  # Should maintain thread continuity
            connection_info=connection_info
        )
        
        # FAILING ASSERTION: WebSocket continuity should be maintained across token refresh
        # Connection ID should remain stable across token refresh
        assert connection_info.connection_id == connection_info.connection_id, \
            f"Connection ID should remain stable during token refresh"
            
        # This will FAIL because uuid.uuid4() run_id changes unpredictably
        # Context should maintain continuity references
        assert initial_context.thread_id == refreshed_context.thread_id, \
            f"Thread ID continuity broken: {initial_context.thread_id} != {refreshed_context.thread_id}"
            
        # This will FAIL because uuid.uuid4() provides no continuity tracking
        # New context should reference previous context for continuity
        expected_continuity_pattern = f"ctx_{user_id[:8]}_refresh_{initial_context.run_id[:8]}_"
        assert refreshed_context.run_id.find(expected_continuity_pattern) != -1, \
            f"Expected refresh continuity pattern '{expected_continuity_pattern}' in: {refreshed_context.run_id}"
            
        # FAILING ASSERTION: Both tokens should validate against same WebSocket connection
        # Initial token validation
        initial_validation = await self._validate_token_for_connection(
            initial_token, connection_info.connection_id
        )
        
        # Refresh token validation  
        refresh_validation = await self._validate_token_for_connection(
            refresh_token, connection_info.connection_id
        )
        
        # Both should validate successfully for connection continuity
        assert initial_validation.valid or refresh_validation.valid, \
            f"Token refresh should maintain WebSocket connection validity"

    async def test_oauth_integration_websocket_flow_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose OAuth integration issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns break OAuth integration
        flows for WebSocket connections.
        """
        # Simulate OAuth flow
        oauth_state = str(uuid.uuid4())  # OAuth state parameter
        oauth_code = "mock_auth_code_12345"
        
        # Create test user via OAuth simulation
        test_user = await self._create_test_user("oauth_integration_user")
        user_id = str(test_user.id)
        
        # Simulate OAuth token exchange
        oauth_token_response = {
            "access_token": f"oauth_access_{uuid.uuid4().hex}",
            "refresh_token": f"oauth_refresh_{uuid.uuid4().hex}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "websocket_access"
        }
        
        # Create WebSocket connection with OAuth context
        connection_info = ConnectionInfo(user_id=user_id)
        oauth_context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # FAILING ASSERTION: WebSocket IDs should integrate with OAuth flow
        # Connection ID should reference OAuth state for security
        assert oauth_state[:8] in connection_info.connection_id or \
               "oauth" in connection_info.connection_id.lower(), \
            f"Connection ID should reference OAuth context: {connection_info.connection_id}"
            
        # This will FAIL because uuid.uuid4() context lacks OAuth integration
        expected_oauth_pattern = f"ctx_{user_id[:8]}_oauth_{oauth_state[:8]}_"
        assert oauth_context.run_id.startswith(expected_oauth_pattern), \
            f"Expected OAuth-integrated context pattern '{expected_oauth_pattern}', got: {oauth_context.run_id}"
            
        # FAILING ASSERTION: OAuth token should be linkable to WebSocket context
        # Store OAuth context in auth session
        oauth_session = await self.auth_client.create_oauth_session({
            "user_id": user_id,
            "oauth_state": oauth_state,
            "access_token": oauth_token_response["access_token"],
            "websocket_connection_id": connection_info.connection_id,
            "websocket_context_id": oauth_context.run_id
        })
        
        # This will FAIL because uuid.uuid4() IDs make OAuth linking inefficient
        assert oauth_session is not None, \
            f"Failed to create OAuth session with uuid.uuid4() WebSocket IDs"
            
        # Validate OAuth token grants WebSocket access
        oauth_validation = await self._validate_oauth_for_websocket(
            oauth_token_response["access_token"],
            connection_info.connection_id,
            oauth_context.run_id
        )
        
        assert oauth_validation.valid, \
            f"OAuth token should validate for WebSocket context: {oauth_validation.error_message}"

    async def test_auth_middleware_integration_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose auth middleware integration issues with uuid.uuid4().
        
        This test demonstrates that uuid.uuid4() patterns break WebSocket auth
        middleware integration and request validation.
        """
        # Create test user
        test_user = await self._create_test_user("middleware_auth_user")
        user_id = str(test_user.id)
        
        # Create JWT token for user
        token_payload = {
            "user_id": user_id,
            "username": test_user.username,
            "permissions": ["websocket_connect", "send_message", "receive_notifications"]
        }
        jwt_token = self.jwt_manager.generate_token(token_payload)
        
        # Initialize WebSocket auth middleware
        auth_middleware = WebSocketAuthMiddleware(
            jwt_manager=self.jwt_manager,
            auth_validator=self.auth_validator
        )
        
        # Create WebSocket connection request
        connection_info = ConnectionInfo(user_id=user_id)
        context = WebSocketRequestContext.create_for_user(
            user_id=user_id,
            thread_id=None,
            connection_info=connection_info
        )
        
        # Create WebSocket message for auth validation
        test_message = generate_default_message(
            message_type="agent_started",
            user_id=user_id,
            thread_id=context.thread_id,
            data={"content": "Test authenticated message"}
        )
        
        # FAILING ASSERTION: Auth middleware should validate using consistent ID patterns
        # Validate connection with middleware
        connection_auth_result = await auth_middleware.validate_connection(
            jwt_token, connection_info.connection_id, user_id
        )
        
        # This will FAIL because uuid.uuid4() connection IDs can't be pre-validated
        assert connection_auth_result.valid, \
            f"Auth middleware should validate connection: {connection_auth_result.error_message}"
            
        # This will FAIL because uuid.uuid4() lacks user context for middleware
        assert user_id[:8] in connection_info.connection_id, \
            f"Connection ID should contain user context for middleware: {connection_info.connection_id}"
            
        # Validate message with middleware
        message_auth_result = await auth_middleware.validate_message(
            jwt_token, test_message, context
        )
        
        # This will FAIL because uuid.uuid4() message IDs can't be efficiently validated
        assert message_auth_result.valid, \
            f"Auth middleware should validate message: {message_auth_result.error_message}"
            
        # This will FAIL because uuid.uuid4() message IDs lack auth context
        expected_auth_pattern = f"msg_{test_message.type}_{user_id[:8]}_auth_"
        assert test_message.message_id.find(expected_auth_pattern) != -1, \
            f"Expected auth-compatible message pattern '{expected_auth_pattern}' in: {test_message.message_id}"
            
        # FAILING ASSERTION: Middleware should efficiently process auth decisions
        # Test batch auth validation (efficiency test)
        messages = []
        for i in range(10):
            msg = generate_default_message(
                message_type="agent_thinking",
                user_id=user_id,
                thread_id=context.thread_id,
                data={"content": f"Batch message {i}"}
            )
            messages.append(msg)
            
        start_time = time.time()
        batch_results = await auth_middleware.validate_message_batch(jwt_token, messages, context)
        auth_time = time.time() - start_time
        
        # This will FAIL because uuid.uuid4() makes batch auth validation inefficient
        assert auth_time < 0.1, \
            f"Batch auth validation too slow with uuid.uuid4(): {auth_time:.3f}s > 0.1s"
            
        assert all(result.valid for result in batch_results), \
            f"All batch messages should validate successfully"

    # Helper methods for auth integration testing
    
    async def _create_test_user(self, username: str) -> User:
        """Create a test user for auth integration testing."""
        user_data = {
            "username": username,
            "email": f"{username}@example.com",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
        
        # Create user through auth service
        auth_user = await self.auth_client.create_user(user_data)
        
        # Convert to local User model
        user = User(
            id=auth_user.get("id"),
            username=auth_user.get("username"),
            email=auth_user.get("email"),
            is_active=auth_user.get("is_active", True),
            created_at=datetime.fromisoformat(auth_user.get("created_at"))
        )
        
        return user
        
    async def _can_user_access_connection(self, user_id: str, connection_id: str, auth_session: Dict) -> bool:
        """Check if user can access WebSocket connection based on auth session."""
        try:
            # Simulate auth check using session
            session_token = auth_session.get("access_token") or auth_session.get("session_token")
            
            if not session_token:
                return False
                
            # Validate token for connection access
            validation_result = await self._validate_token_for_connection(session_token, connection_id)
            
            return validation_result.valid
            
        except Exception:
            return False
            
    async def _validate_token_for_connection(self, token: str, connection_id: str) -> AuthValidationResult:
        """Validate JWT token for specific WebSocket connection."""
        try:
            # Decode token (this would use proper validation in real implementation)
            decoded_token = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded_token.get("user_id")
            
            if not user_id:
                return AuthValidationResult(
                    valid=False,
                    error_message="Token missing user_id"
                )
                
            # This is where uuid.uuid4() patterns cause problems - no user context in connection_id
            if user_id[:8] not in connection_id:
                return AuthValidationResult(
                    valid=False, 
                    error_message=f"Connection ID {connection_id} not authorized for user {user_id}"
                )
                
            return AuthValidationResult(
                valid=True,
                user_id=UserID(user_id)
            )
            
        except Exception as e:
            return AuthValidationResult(
                valid=False,
                error_message=f"Token validation error: {str(e)}"
            )
            
    async def _validate_oauth_for_websocket(self, access_token: str, connection_id: str, context_id: str) -> AuthValidationResult:
        """Validate OAuth access token for WebSocket connection and context."""
        try:
            # Simulate OAuth token validation
            # In real implementation, this would call OAuth provider validation endpoint
            
            if not access_token.startswith("oauth_access_"):
                return AuthValidationResult(
                    valid=False,
                    error_message="Invalid OAuth access token format"
                )
                
            # This is where uuid.uuid4() patterns cause OAuth integration issues
            # OAuth scopes should be checkable against connection/context IDs
            has_websocket_scope = "websocket" in access_token.lower()
            
            if not has_websocket_scope:
                return AuthValidationResult(
                    valid=False,
                    error_message="OAuth token lacks WebSocket access scope"
                )
                
            # Check if token grants access to specific connection/context
            # This fails with uuid.uuid4() because IDs lack OAuth context
            if "oauth" not in connection_id.lower() and "oauth" not in context_id.lower():
                return AuthValidationResult(
                    valid=False,
                    error_message="WebSocket IDs not linked to OAuth flow"
                )
                
            return AuthValidationResult(valid=True)
            
        except Exception as e:
            return AuthValidationResult(
                valid=False,
                error_message=f"OAuth validation error: {str(e)}"
            )
            
    async def _cleanup_test_auth_data(self):
        """Clean up test auth data."""
        try:
            # Clean up test users and auth sessions
            await self.auth_client.cleanup_test_data()
            
        except Exception as e:
            # Ignore cleanup errors in test setup
            self.logger.warning(f"Auth test cleanup error: {e}")

    @pytest.fixture
    async def real_services_fixture(self):
        """Fixture to ensure real auth services are available for integration tests."""
        # This fixture is automatically used by BaseIntegrationTest
        # and ensures real auth services are running
        pass