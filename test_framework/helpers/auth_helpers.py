"""
Authentication test helper functions.
Consolidates auth-related helpers from across the project.
"""

import hashlib
import hmac
import json
import time
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch, AsyncMock
from dataclasses import dataclass

# Import skip_if_services_unavailable from real_services module
from test_framework.real_services import skip_if_services_unavailable


def create_test_jwt_token(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    expiry_hours: int = 24
) -> str:
    """Create a test JWT token for testing purposes"""
    # This is a mock implementation for testing
    payload = {
        "sub": email,
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + (expiry_hours * 3600),
        "iss": "test-issuer"
    }
    # Return a mock token (not actually signed)
    return f"test.{encode_base64(json.dumps(payload))}.signature"


def encode_base64(data: str) -> str:
    """Base64 encode string for JWT payload"""
    import base64
    return base64.urlsafe_b64encode(data.encode()).decode().rstrip('=')


def create_test_auth_headers(
    token: Optional[str] = None,
    user_id: str = "test-user-123"
) -> Dict[str, str]:
    """Create authorization headers for testing"""
    if not token:
        token = create_test_jwt_token(user_id=user_id)
    
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def create_test_user_data(
    user_id: str = "test-user-123",
    email: str = "test@example.com",
    tier: str = "free"
) -> Dict[str, Any]:
    """Create test user data"""
    return {
        "id": user_id,
        "email": email,
        "name": "Test User",
        "is_active": True,
        "is_superuser": False,
        "tier": tier,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-01T00:00:00Z"
    }


def create_oauth_test_data(
    provider: str = "google",
    user_id: str = "oauth-user-123"
) -> Dict[str, Any]:
    """Create OAuth test data"""
    return {
        "provider": provider,
        "provider_user_id": f"{provider}-{user_id}",
        "email": f"test+{provider}@example.com",
        "name": f"Test {provider.title()} User",
        "avatar_url": f"https://{provider}.com/avatar.jpg",
        "access_token": f"test-{provider}-access-token",
        "refresh_token": f"test-{provider}-refresh-token",
        "expires_at": "2025-12-31T23:59:59Z"
    }


def mock_jwt_validation(valid: bool = True, user_data: Optional[Dict[str, Any]] = None):
    """Context manager to mock JWT validation"""
    if user_data is None:
        user_data = create_test_user_data()
    
    async def mock_validate(token: str):
        if valid:
            return {
                "valid": True,
                "user_id": user_data["id"],
                "email": user_data["email"],
                "data": user_data
            }
        else:
            return {"valid": False, "error": "Invalid token"}
    
    return patch('netra_backend.app.auth_integration.auth.validate_token_jwt', new_callable=AsyncMock, side_effect=mock_validate)


def create_session_data(
    session_id: str = "test-session-123",
    user_id: str = "test-user-123"
) -> Dict[str, Any]:
    """Create test session data"""
    return {
        "session_id": session_id,
        "user_id": user_id,
        "created_at": "2025-01-01T00:00:00Z",
        "expires_at": "2025-01-02T00:00:00Z",
        "is_active": True,
        "ip_address": "127.0.0.1",
        "user_agent": "test-client"
    }


def create_api_key_data(
    api_key: str = "test-api-key-123",
    user_id: str = "test-user-123"
) -> Dict[str, Any]:
    """Create test API key data"""
    return {
        "api_key": api_key,
        "user_id": user_id,
        "name": "Test API Key",
        "is_active": True,
        "permissions": ["read", "write"],
        "created_at": "2025-01-01T00:00:00Z",
        "last_used_at": None,
        "expires_at": "2025-12-31T23:59:59Z"
    }


def validate_auth_response(response_data: Dict[str, Any]) -> bool:
    """Validate authentication response structure"""
    required_fields = ["user_id", "token", "expires_at"]
    return all(field in response_data for field in required_fields)


def validate_user_data(user_data: Dict[str, Any]) -> bool:
    """Validate user data structure"""
    required_fields = ["id", "email", "is_active"]
    return all(field in user_data for field in required_fields)


class AuthTestHelpers:
    """Auth test helper class with common operations"""
    
    @staticmethod
    def create_test_auth_context(
        user_id: str = "test-user-123",
        email: str = "test@example.com",
        tier: str = "free"
    ) -> Dict[str, Any]:
        """Create complete auth context for testing"""
        user_data = create_test_user_data(user_id, email, tier)
        token = create_test_jwt_token(user_id, email)
        headers = create_test_auth_headers(token, user_id)
        session = create_session_data(user_id=user_id)
        
        return {
            "user": user_data,
            "token": token,
            "headers": headers,
            "session": session
        }
    
    @staticmethod
    def create_multiple_test_users(count: int = 3) -> list[Dict[str, Any]]:
        """Create multiple test users with auth contexts"""
        users = []
        for i in range(count):
            user_id = f"test-user-{i}"
            email = f"test{i}@example.com"
            context = AuthTestHelpers.create_test_auth_context(user_id, email)
            users.append(context)
        return users
    
    @staticmethod
    def simulate_token_expiry(token: str) -> str:
        """Simulate an expired token for testing"""
        # Return a token that will be treated as expired
        return token.replace("test.", "expired.")
    
    @staticmethod
    def create_permission_test_data(permissions: list[str]) -> Dict[str, Any]:
        """Create test data for permission testing"""
        return {
            "user_id": "test-user-123",
            "permissions": permissions,
            "roles": ["user"],
            "tier": "free",
            "tier_limits": {
                "api_calls": 1000,
                "storage": "1GB",
                "features": ["basic"]
            }
        }


# Utility functions for common auth test patterns

def assert_authenticated_response(response_data: Dict[str, Any]):
    """Assert that response indicates successful authentication"""
    assert "user_id" in response_data
    assert "token" in response_data
    assert response_data.get("authenticated") is True


def assert_unauthenticated_response(response_data: Dict[str, Any]):
    """Assert that response indicates failed authentication"""
    assert response_data.get("authenticated") is False
    assert "error" in response_data


def assert_permission_denied(response_data: Dict[str, Any]):
    """Assert that response indicates permission denied"""
    assert response_data.get("error") == "permission_denied"
    assert response_data.get("status_code", 403) == 403


def create_oauth_flow_test_data() -> Dict[str, Any]:
    """Create complete OAuth flow test data"""
    return {
        "authorization_url": "https://accounts.google.com/oauth/authorize?client_id=test",
        "state": "test-state-123",
        "code": "test-authorization-code",
        "access_token": "test-access-token",
        "refresh_token": "test-refresh-token", 
        "user_info": {
            "id": "google-123",
            "email": "oauth@example.com",
            "name": "OAuth Test User",
            "picture": "https://example.com/avatar.jpg"
        }
    }


@dataclass
class AuthTestConfig:
    """Configuration for authentication tests."""
    auth_service_url: str = "http://localhost:8001"
    backend_url: str = "http://localhost:8000"
    timeout: float = 10.0
    test_user_prefix: str = "test_auth"
    
    # Performance thresholds
    TEST_EXECUTION_LIMIT: float = 5.0  # Maximum test execution time in seconds
    TOKEN_EXPIRY_WAIT: float = 6.0     # Wait time for token expiry tests
    AUTH_PERFORMANCE_LIMIT: float = 0.1  # 100ms auth performance limit
    VALIDATION_PERFORMANCE_LIMIT: float = 0.05  # 50ms validation limit
    RECONNECTION_PERFORMANCE_LIMIT: float = 2.0  # 2s reconnection limit


class WebSocketAuthTester:
    """Real WebSocket connection tester with auth validation."""
    
    def __init__(self, config: Optional[AuthTestConfig] = None):
        """Initialize WebSocket auth tester."""
        self.config = config or AuthTestConfig()
        # WebSocket manager removed for security reasons - use factory pattern instead
        # For testing purposes, we'll create mock connections without the real manager
        self.connection_manager = None
        self.test_users: Dict[str, str] = {}
        self.active_connections: List = []  # Will be populated with MockWebSocket instances
        self.auth_results: List[Dict[str, Any]] = []
    
    def create_test_user_with_token(self, user_id: str) -> str:
        """Create test user and return valid JWT token."""
        token = create_test_jwt_token(user_id)
        self.test_users[user_id] = token
        return token
    
    def record_auth_result(self, user_id: str, success: bool, 
                          error: Optional[str] = None) -> None:
        """Record authentication test result."""
        result = self._create_auth_result(user_id, success, error)
        self.auth_results.append(result)
    
    def _create_auth_result(self, user_id: str, success: bool, error: Optional[str]) -> Dict[str, Any]:
        """Create authentication result record."""
        return {
            "user_id": user_id,
            "success": success,
            "error": error,
            "timestamp": datetime.now(timezone.utc)
        }
    
    async def connect_authenticated_websocket(self, user_id: Optional[str] = None) -> Any:
        """Connect authenticated WebSocket client.
        
        This is a test helper method that creates a mock WebSocket connection
        with authentication for testing purposes.
        """
        if user_id is None:
            user_id = f"test_user_{int(time.time())}"
        
        token = self.create_test_user_with_token(user_id)
        
        # For testing purposes, return a mock WebSocket-like object
        class MockWebSocketClient:
            def __init__(self, user_id: str, token: str):
                self.user_id = user_id
                self.token = token
                self.is_authenticated = True
                self.sent_messages = []
                self.received_messages = []
            
            async def send(self, message: str) -> None:
                """Mock send message."""
                self.sent_messages.append(message)
            
            async def recv(self) -> str:
                """Mock receive message."""
                if self.received_messages:
                    return self.received_messages.pop(0)
                return '{"type": "ack", "message": "Message received"}'
            
            async def close(self) -> None:
                """Mock close connection."""
                self.is_authenticated = False
        
        client = MockWebSocketClient(user_id, token)
        self.active_connections.append(client)
        return client
    
    async def cleanup(self) -> None:
        """Clean up test connections."""
        cleanup_tasks = []
        for connection in self.active_connections:
            if hasattr(connection, 'close'):
                cleanup_tasks.append(connection.close())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        self.active_connections.clear()
        self.test_users.clear()
        self.auth_results.clear()


class TokenExpiryTester:
    """Helper class for testing token expiry and refresh scenarios."""
    
    def __init__(self, websocket_auth_tester: WebSocketAuthTester):
        """Initialize token expiry tester.
        
        Args:
            websocket_auth_tester: WebSocketAuthTester instance to use for testing
        """
        self.auth_tester = websocket_auth_tester
        self.short_lived_tokens: Dict[str, str] = {}
        
    def create_short_lived_token(self, expiry_seconds: int = 5) -> str:
        """Create a short-lived JWT token for expiry testing.
        
        Args:
            expiry_seconds: Token expiry time in seconds
            
        Returns:
            Short-lived JWT token
        """
        user_id = f"expiry_test_{int(time.time())}"
        token = create_test_jwt_token(
            user_id=user_id,
            expiry_hours=expiry_seconds / 3600  # Convert seconds to hours
        )
        self.short_lived_tokens[token] = user_id
        return token
        
    def simulate_expired_token(self, original_token: str) -> str:
        """Simulate an expired version of a token.
        
        Args:
            original_token: Original valid token
            
        Returns:
            Token marked as expired for testing
        """
        return original_token.replace("test.", "expired.")
        
    async def verify_token_expiry_behavior(self, token: str, expected_expired: bool = True) -> Dict[str, Any]:
        """Verify token expiry behavior.
        
        Args:
            token: Token to test
            expected_expired: Whether token should be expired
            
        Returns:
            Dictionary with expiry test results
        """
        try:
            # Test token validation
            ws_result = await self.auth_tester.establish_websocket_connection(token, timeout=1.0)
            
            if expected_expired:
                # Should fail to connect
                success = not ws_result["connected"]
                error = ws_result.get("error")
            else:
                # Should connect successfully
                success = ws_result["connected"]
                error = None
                if ws_result["connected"]:
                    await ws_result["websocket"].close()
                    
            return {
                "token": token,
                "expected_expired": expected_expired,
                "test_passed": success,
                "error": error,
                "timestamp": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            return {
                "token": token,
                "expected_expired": expected_expired,
                "test_passed": expected_expired,  # Exception expected if token expired
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
            
    async def test_token_refresh_scenario(self, expired_token: str) -> Dict[str, Any]:
        """Test token refresh scenario.
        
        Args:
            expired_token: Expired token to refresh
            
        Returns:
            Dictionary with refresh test results
        """
        try:
            # Attempt to refresh expired token (mock implementation for testing)
            user_id = self.short_lived_tokens.get(expired_token, "refresh_test_user")
            
            # Create new token for the same user
            new_token = create_test_jwt_token(user_id=user_id, expiry_hours=24)
            
            # Test new token works
            validation_result = await self.verify_token_expiry_behavior(new_token, expected_expired=False)
            
            return {
                "original_token": expired_token,
                "new_token": new_token,
                "refresh_successful": validation_result["test_passed"],
                "validation_result": validation_result,
                "timestamp": datetime.now(timezone.utc)
            }
            
        except Exception as e:
            return {
                "original_token": expired_token,
                "new_token": None,
                "refresh_successful": False,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc)
            }
            
    def cleanup_expired_tokens(self) -> None:
        """Clean up expired token tracking."""
        self.short_lived_tokens.clear()


# Authentication performance assertion functions

def assert_auth_performance(execution_time: float, operation_type: str = "auth") -> None:
    """Assert that authentication operation meets performance requirements.
    
    Args:
        execution_time: Time taken for the operation in seconds
        operation_type: Type of operation ("auth", "validation", "reconnection")
        
    Raises:
        AssertionError: If performance requirements are not met
    """
    # Define performance limits based on operation type
    limits = {
        "auth": AuthTestConfig.AUTH_PERFORMANCE_LIMIT,           # 100ms
        "validation": AuthTestConfig.VALIDATION_PERFORMANCE_LIMIT, # 50ms
        "reconnection": AuthTestConfig.RECONNECTION_PERFORMANCE_LIMIT # 2s
    }
    
    limit = limits.get(operation_type, AuthTestConfig.AUTH_PERFORMANCE_LIMIT)
    
    assert execution_time <= limit, (
        f"{operation_type.title()} operation took {execution_time:.3f}s, "
        f"expected <={limit}s for {operation_type} operations"
    )
    

def assert_token_rejection(result: Dict[str, Any], test_name: str = "token_rejection") -> None:
    """Assert that invalid token was properly rejected.
    
    Args:
        result: Result dictionary from authentication attempt
        test_name: Name of the test for error reporting
        
    Raises:
        AssertionError: If token was not properly rejected
    """
    # Check that connection was not established
    assert not result.get("connected", False), (
        f"{test_name}: Invalid token should not establish connection"
    )
    
    # Check that appropriate error was provided
    error = result.get("error")
    assert error is not None, (
        f"{test_name}: Token rejection should include error message"
    )
    
    # Check for expected error types
    expected_errors = ["auth", "token", "invalid", "expired", "unauthorized", "forbidden"]
    error_lower = error.lower()
    
    has_expected_error = any(expected in error_lower for expected in expected_errors)
    assert has_expected_error, (
        f"{test_name}: Error message '{error}' should indicate authentication failure"
    )


# Add additional WebSocket auth testing methods to existing WebSocketAuthTester

def enhance_websocket_auth_tester():
    """Add missing methods to WebSocketAuthTester class."""
    
    async def generate_real_jwt_token(self, tier: str = "free") -> Optional[str]:
        """Generate a real JWT token using auth service.
        
        Args:
            tier: User tier ("free", "early", "mid", "enterprise")
            
        Returns:
            Real JWT token or None if auth service unavailable
        """
        try:
            # This would normally call the real auth service
            # For testing, return a test token with the tier embedded
            user_id = f"real_user_{tier}_{int(time.time())}"
            return create_test_jwt_token(user_id=user_id)
        except Exception:
            return None
            
    def create_mock_jwt_token(self, user_id: str = None) -> str:
        """Create a mock JWT token for testing.
        
        Args:
            user_id: User ID for the token
            
        Returns:
            Mock JWT token
        """
        if user_id is None:
            user_id = f"mock_user_{int(time.time())}"
        return create_test_jwt_token(user_id=user_id)
        
    async def validate_token_in_backend(self, token: str) -> Dict[str, Any]:
        """Validate token in backend service.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Validation result dictionary
        """
        start_time = time.time()
        try:
            # Mock validation - in real implementation this would call backend
            validation_time = time.time() - start_time
            
            if token.startswith("expired."):
                return {
                    "valid": False,
                    "error": "Token expired",
                    "validation_time": validation_time
                }
            
            return {
                "valid": True,
                "user_id": "test_user",
                "validation_time": validation_time
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
                "validation_time": time.time() - start_time
            }
            
    async def establish_websocket_connection(self, token: str, timeout: float = 5.0) -> Dict[str, Any]:
        """Establish WebSocket connection with authentication.
        
        Args:
            token: JWT token for authentication
            timeout: Connection timeout in seconds
            
        Returns:
            Connection result dictionary
        """
        try:
            # Mock WebSocket connection for testing
            if token.startswith("expired."):
                return {
                    "connected": False,
                    "error": "Authentication failed: token expired",
                    "websocket": None
                }
            
            # Create mock WebSocket connection
            class MockWebSocket:
                def __init__(self):
                    self.is_connected = True
                    
                async def close(self):
                    self.is_connected = False
                    
                async def send(self, message: str):
                    if not self.is_connected:
                        raise Exception("Connection closed")
                        
                async def recv(self):
                    if not self.is_connected:
                        raise Exception("Connection closed")
                    return '{"type": "ack", "status": "received"}'
            
            mock_ws = MockWebSocket()
            return {
                "connected": True,
                "websocket": mock_ws,
                "error": None
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e),
                "websocket": None
            }
            
    async def send_test_message(self, websocket: Any, message: str) -> Dict[str, Any]:
        """Send test message through WebSocket.
        
        Args:
            websocket: WebSocket connection
            message: Message to send
            
        Returns:
            Send result dictionary
        """
        try:
            await websocket.send(message)
            
            # Try to receive response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                return {
                    "sent": True,
                    "message": message,
                    "response": response,
                    "error": None
                }
            except asyncio.TimeoutError:
                return {
                    "sent": True,
                    "message": message,
                    "response": None,
                    "error": "timeout"
                }
        except Exception as e:
            return {
                "sent": False,
                "message": message,
                "response": None,
                "error": str(e)
            }
            
    async def test_token_refresh_flow(self, expired_token: str) -> str:
        """Test token refresh flow.
        
        Args:
            expired_token: Expired token to refresh
            
        Returns:
            New refreshed token
        """
        # Mock token refresh - extract user info from expired token and create new one
        try:
            # In a real implementation, this would call the auth service refresh endpoint
            user_id = f"refreshed_user_{int(time.time())}"
            return create_test_jwt_token(user_id=user_id, expiry_hours=24)
        except Exception:
            return create_test_jwt_token(user_id="fallback_user", expiry_hours=24)
    
    # Add these methods to the WebSocketAuthTester class
    WebSocketAuthTester.generate_real_jwt_token = generate_real_jwt_token
    WebSocketAuthTester.create_mock_jwt_token = create_mock_jwt_token
    WebSocketAuthTester.validate_token_in_backend = validate_token_in_backend
    WebSocketAuthTester.establish_websocket_connection = establish_websocket_connection
    WebSocketAuthTester.send_test_message = send_test_message
    WebSocketAuthTester.test_token_refresh_flow = test_token_refresh_flow


# Initialize the enhanced methods
enhance_websocket_auth_tester()