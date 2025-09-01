"""Unified Authentication Test Helpers

Consolidated authentication utilities for E2E testing. Provides common authentication
patterns, fixtures, and helpers to prevent duplication across test modules.

Business Value Justification (BVJ):
- Segment: Platform/Internal | Goal: Test Infrastructure | Impact: Development Velocity
- Reduces code duplication across auth test modules
- Ensures consistent authentication testing patterns
- Enables maintainable test infrastructure for critical auth flows

Key Components:
- AuthManager: Core authentication operations
- JWTTestHelper: JWT token management and validation
- WebSocketAuthTester: WebSocket authentication utilities
- OAuthFlowTester: OAuth flow testing utilities
- AuthTestConfig: Centralized auth test configuration
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

import httpx
import websockets
from websockets import ServerConnection
from websockets.exceptions import ConnectionClosedError, WebSocketException

from test_framework.http_client import AuthHTTPClient, ClientConfig, UnifiedHTTPClient


@dataclass
class AuthTestConfig:
    """Centralized authentication test configuration."""
    
    # Performance requirements
    AUTH_TIME_LIMIT: float = 0.1  # 100ms
    RECONNECTION_TIME_LIMIT: float = 2.0  # 2s
    TOKEN_VALIDATION_LIMIT: float = 0.05  # 50ms
    WEBSOCKET_TIMEOUT: float = 5.0
    
    # Test timeouts
    MESSAGE_RESPONSE_TIMEOUT: float = 3.0
    TOKEN_EXPIRY_WAIT: float = 6.0
    TEST_EXECUTION_LIMIT: float = 10.0
    
    # Service URLs
    auth_url: str = "http://localhost:8001"
    backend_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8000/websocket"
    
    # Test credentials
    test_username: str = "test_user"
    test_email: str = "test@example.com"
    test_password: str = "TestPassword123#"


class AuthManager:
    """Core authentication operations for testing."""
    
    def __init__(self, config: Optional[AuthTestConfig] = None):
        """Initialize auth manager with configuration."""
        self.config = config or AuthTestConfig()
        self.client = AuthHTTPClient(self.config.auth_url)
        self._cached_tokens: Dict[str, Dict[str, Any]] = {}
    
    async def create_test_user(self, username: Optional[str] = None, 
                              email: Optional[str] = None,
                              password: Optional[str] = None) -> Dict[str, Any]:
        """Create test user with optional custom credentials."""
        username = username or f"test_user_{uuid.uuid4().hex[:8]}"
        email = email or f"test_{uuid.uuid4().hex[:8]}@example.com"
        password = password or self.config.test_password
        
        try:
            result = await self.client.register(username, email, password)
            return {
                "success": True,
                "user_id": result.get("user_id"),
                "username": username,
                "email": email,
                "password": password
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "username": username,
                "email": email,
                "password": password
            }
    
    async def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login user and return tokens."""
        try:
            result = await self.client.login(username, password)
            
            # Cache tokens for reuse
            self._cached_tokens[username] = result
            
            return {
                "success": True,
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "user_id": result.get("user_id"),
                "expires_in": result.get("expires_in")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_valid_token(self, username: Optional[str] = None) -> Optional[str]:
        """Get or create valid token for testing."""
        if username and username in self._cached_tokens:
            cached = self._cached_tokens[username]
            # TODO: Check token expiry and refresh if needed
            return cached.get("access_token")
        
        # Create new test user and login
        user_result = await self.create_test_user(username)
        if not user_result["success"]:
            return None
        
        login_result = await self.login_user(
            user_result["username"], 
            user_result["password"]
        )
        
        if login_result["success"]:
            return login_result["access_token"]
        
        return None
    
    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate token and return user info."""
        try:
            result = await self.client.validate_token(token)
            return {
                "valid": True,
                "user_id": result.get("user_id"),
                "username": result.get("username"),
                "expires_at": result.get("expires_at")
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e)
            }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token."""
        try:
            result = await self.client.refresh_token(refresh_token)
            return {
                "success": True,
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "expires_in": result.get("expires_in")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def logout_user(self, token: str) -> Dict[str, Any]:
        """Logout user and invalidate token."""
        try:
            await self.client.logout(token)
            return {"success": True}
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def close(self):
        """Close HTTP client."""
        await self.client.close()


class JWTTestHelper:
    """JWT token management and validation utilities."""
    
    def __init__(self, auth_manager: Optional[AuthManager] = None):
        """Initialize JWT test helper."""
        self.auth_manager = auth_manager or AuthManager()
    
    async def create_test_token(self, username: Optional[str] = None) -> Optional[str]:
        """Create test token for authenticated requests."""
        return await self.auth_manager.get_valid_token(username)
    
    async def create_expired_token(self) -> str:
        """Create an expired token for testing token expiry scenarios."""
        # This is a placeholder - in real implementation, you'd create a token
        # with a very short expiry time or manipulate the token's exp claim
        token = await self.create_test_token()
        # Sleep to ensure expiry (for testing purposes)
        await asyncio.sleep(6)  # Assuming 5 second token expiry
        return token
    
    async def validate_token_claims(self, token: str) -> Dict[str, Any]:
        """Validate token and extract claims."""
        return await self.auth_manager.validate_token(token)
    
    def extract_token_payload(self, token: str) -> Dict[str, Any]:
        """Extract payload from JWT token without validation."""
        import base64
        import json
        
        try:
            # Split token into parts
            parts = token.split('.')
            if len(parts) != 3:
                return {"error": "Invalid token format"}
            
            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            
            decoded = base64.urlsafe_b64decode(payload)
            return json.loads(decoded)
        except Exception as e:
            return {"error": f"Failed to decode token: {str(e)}"}
    
    def create_expired_token_sync(self) -> str:
        """Create a synchronous expired token for malformed token testing."""
        # Create a basic expired JWT for testing purposes
        import base64
        import json
        import time
        
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": "test_user",
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200   # Issued 2 hours ago
        }
        
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Return unsigned token (will be invalid anyway due to expiry)
        return f"{header_b64}.{payload_b64}.invalid_signature"


class WebSocketAuthTester:
    """WebSocket authentication utilities for testing."""
    
    def __init__(self, config: Optional[AuthTestConfig] = None):
        """Initialize WebSocket auth tester."""
        self.config = config or AuthTestConfig()
        self.auth_manager = AuthManager(config)
        self.active_connections: List[websockets.ServerConnection] = []
    
    async def connect_authenticated_websocket(self, token: Optional[str] = None) -> websockets.ServerConnection:
        """Connect to WebSocket with authentication."""
        if not token:
            token = await self.auth_manager.get_valid_token()
        
        if not token:
            raise ValueError("Failed to get valid token for WebSocket connection")
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        try:
            websocket = await websockets.connect(
                self.config.websocket_url,
                extra_headers=headers,
                timeout=self.config.WEBSOCKET_TIMEOUT
            )
            self.active_connections.append(websocket)
            return websocket
        except Exception as e:
            raise ConnectionError(f"Failed to connect to WebSocket: {str(e)}")
    
    async def send_authenticated_message(self, websocket: websockets.ServerConnection, 
                                        message: Dict[str, Any]) -> None:
        """Send message through authenticated WebSocket."""
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            raise ConnectionError(f"Failed to send WebSocket message: {str(e)}")
    
    async def wait_for_message(self, websocket: websockets.ServerConnection, 
                              timeout: Optional[float] = None) -> Dict[str, Any]:
        """Wait for message from WebSocket."""
        timeout = timeout or self.config.MESSAGE_RESPONSE_TIMEOUT
        
        try:
            message = await asyncio.wait_for(websocket.recv(), timeout=timeout)
            return json.loads(message)
        except asyncio.TimeoutError:
            raise TimeoutError(f"No message received within {timeout} seconds")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON message: {str(e)}")
    
    async def test_websocket_reconnection(self, token: str) -> Dict[str, Any]:
        """Test WebSocket reconnection with authentication."""
        results = {
            "initial_connection": False,
            "reconnection": False,
            "message_preservation": False,
            "total_time": 0
        }
        
        start_time = time.time()
        
        try:
            # Initial connection
            ws1 = await self.connect_authenticated_websocket(token)
            results["initial_connection"] = True
            
            # Send test message
            test_message = {
                "type": "test_message",
                "content": "Test message before reconnection",
                "timestamp": time.time()
            }
            await self.send_authenticated_message(ws1, test_message)
            
            # Close connection
            await ws1.close()
            
            # Reconnect
            ws2 = await self.connect_authenticated_websocket(token)
            results["reconnection"] = True
            
            # Test if message preservation works
            response = await self.wait_for_message(ws2, timeout=2.0)
            if response.get("type") == "message_restored":
                results["message_preservation"] = True
            
            await ws2.close()
            
        except Exception as e:
            results["error"] = str(e)
        
        results["total_time"] = time.time() - start_time
        return results
    
    async def close_all_connections(self):
        """Close all active WebSocket connections."""
        for websocket in self.active_connections:
            try:
                await websocket.close()
            except Exception:
                pass
        self.active_connections.clear()
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.close_all_connections()
        await self.auth_manager.close()


class OAuthFlowTester:
    """OAuth flow testing utilities."""
    
    def __init__(self, config: Optional[AuthTestConfig] = None):
        """Initialize OAuth flow tester."""
        self.config = config or AuthTestConfig()
        self.client = UnifiedHTTPClient(self.config.auth_url)
    
    async def initiate_oauth_flow(self, provider: str = "google") -> Dict[str, Any]:
        """Initiate OAuth flow and return authorization URL."""
        try:
            result = await self.client.get(f"/auth/oauth/{provider}/authorize")
            return {
                "success": True,
                "authorization_url": result.get("authorization_url"),
                "state": result.get("state")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def complete_oauth_flow(self, code: str, state: str, 
                                 provider: str = "google") -> Dict[str, Any]:
        """Complete OAuth flow with authorization code."""
        try:
            result = await self.client.post(f"/auth/oauth/{provider}/callback", {
                "code": code,
                "state": state
            })
            return {
                "success": True,
                "access_token": result.get("access_token"),
                "refresh_token": result.get("refresh_token"),
                "user_info": result.get("user_info")
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_oauth_error_handling(self, provider: str = "google") -> Dict[str, Any]:
        """Test OAuth error handling scenarios."""
        results = {
            "invalid_code": False,
            "invalid_state": False,
            "expired_code": False
        }
        
        try:
            # Test invalid code
            invalid_result = await self.complete_oauth_flow("invalid_code", "valid_state", provider)
            results["invalid_code"] = not invalid_result["success"]
            
            # Test invalid state
            invalid_state_result = await self.complete_oauth_flow("valid_code", "invalid_state", provider)
            results["invalid_state"] = not invalid_state_result["success"]
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    async def close(self):
        """Close HTTP client."""
        await self.client.close()


# Convenience functions for common auth testing patterns
async def create_authenticated_user(config: Optional[AuthTestConfig] = None) -> Tuple[str, str, Dict[str, Any]]:
    """Create authenticated user and return username, token, and user_info."""
    auth_manager = AuthManager(config)
    
    try:
        user_result = await auth_manager.create_test_user()
        if not user_result["success"]:
            raise ValueError(f"Failed to create user: {user_result.get('error')}")
        
        login_result = await auth_manager.login_user(
            user_result["username"],
            user_result["password"]
        )
        
        if not login_result["success"]:
            raise ValueError(f"Failed to login: {login_result.get('error')}")
        
        return (
            user_result["username"],
            login_result["access_token"],
            {
                "user_id": user_result["user_id"],
                "username": user_result["username"],
                "email": user_result["email"]
            }
        )
    finally:
        await auth_manager.close()


async def get_test_token(username: Optional[str] = None, config: Optional[AuthTestConfig] = None) -> Optional[str]:
    """Get valid test token for authenticated requests."""
    auth_manager = AuthManager(config)
    try:
        return await auth_manager.get_valid_token(username)
    finally:
        await auth_manager.close()


async def validate_auth_token(token: str, config: Optional[AuthTestConfig] = None) -> Dict[str, Any]:
    """Validate authentication token."""
    auth_manager = AuthManager(config)
    try:
        return await auth_manager.validate_token(token)
    finally:
        await auth_manager.close()


# Test utility functions for service availability and performance
def skip_if_services_unavailable(error_message: str) -> None:
    """Skip test if services are unavailable based on error message patterns.
    
    This function analyzes error messages to determine if a test failure is due
    to service unavailability rather than actual code issues, and skips the test
    with an appropriate message.
    
    Args:
        error_message: Error message to analyze for service availability patterns
    """
    import pytest
    
    # Common patterns indicating service unavailability
    service_unavailable_patterns = [
        "connection refused",
        "connection failed",
        "service unavailable",
        "timeout",
        "could not connect",
        "refused to connect",
        "network unreachable",
        "host unreachable",
        "service not available",
        "backend service not available",
        "auth service not available",
        "websocket.*failed",
        "failed to connect",
        "connection error",
        "no route to host",
        "connection timed out"
    ]
    
    error_lower = error_message.lower()
    
    # Check if error indicates service unavailability
    for pattern in service_unavailable_patterns:
        if pattern in error_lower:
            pytest.skip(f"Service unavailable - skipping test: {error_message}")
    
    # If not a service availability issue, let the test continue/fail normally
    return


def assert_auth_performance(measured_time: float, operation_type: str) -> None:
    """Assert that authentication operation meets performance requirements.
    
    Args:
        measured_time: Time taken for the operation in seconds
        operation_type: Type of operation (auth, validation, reconnection)
    """
    # Performance thresholds based on AuthTestConfig
    thresholds = {
        "auth": AuthTestConfig.AUTH_TIME_LIMIT,  # 0.1s (100ms)
        "validation": AuthTestConfig.TOKEN_VALIDATION_LIMIT,  # 0.05s (50ms)
        "reconnection": AuthTestConfig.RECONNECTION_TIME_LIMIT  # 2.0s
    }
    
    threshold = thresholds.get(operation_type, 1.0)  # Default 1s if unknown type
    
    if measured_time > threshold:
        import pytest
        pytest.fail(
            f"{operation_type.capitalize()} performance requirement failed: "
            f"{measured_time:.3f}s > {threshold}s threshold"
        )


def assert_token_rejection(ws_result: Dict[str, Any], test_name: str) -> None:
    """Assert that token was properly rejected by WebSocket connection.
    
    Args:
        ws_result: Result from WebSocket connection attempt
        test_name: Name of the test case for better error reporting
    """
    import pytest
    
    # Token should be rejected (not connected)
    if ws_result.get("connected", False):
        pytest.fail(f"Invalid token should be rejected: {test_name}")
    
    # Should have proper error indication
    error = ws_result.get("error", "")
    if not error:
        pytest.fail(f"Token rejection should provide error message: {test_name}")


# Legacy compatibility classes
class WebSocketAuthTester_Legacy(WebSocketAuthTester):
    """Legacy WebSocketAuthTester for backward compatibility."""
    pass


class TokenExpiryTester:
    """Token expiry testing utilities."""
    
    def __init__(self, config: Optional[AuthTestConfig] = None):
        """Initialize token expiry tester."""
        self.jwt_helper = JWTTestHelper()
        self.config = config or AuthTestConfig()
    
    async def test_token_expiry_scenario(self) -> Dict[str, Any]:
        """Test token expiry and refresh scenarios."""
        results = {
            "token_created": False,
            "token_expired": False,
            "refresh_successful": False
        }
        
        try:
            # Create token
            token = await self.jwt_helper.create_test_token()
            results["token_created"] = bool(token)
            
            # Wait for expiry
            await asyncio.sleep(self.config.TOKEN_EXPIRY_WAIT)
            
            # Validate expired token
            validation = await self.jwt_helper.validate_token_claims(token)
            results["token_expired"] = not validation.get("valid", True)
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def create_malformed_tokens(self) -> List[Tuple[str, str]]:
        """Create various malformed tokens for testing rejection."""
        return [
            ("empty_token", ""),
            ("invalid_format", "not.a.jwt"),
            ("malformed_header", "invalid_header.eyJzdWIiOiIxMjMifQ.signature"),
            ("malformed_payload", "eyJhbGciOiJIUzI1NiJ9.invalid_payload.signature"),
            ("missing_signature", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ"),
            ("invalid_signature", "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.invalid_signature"),
            ("expired_token", self.jwt_helper.create_expired_token_sync()),
            ("null_token", None),
            ("very_long_token", "x" * 5000),
        ]


class MessagePreservationTester:
    """Message preservation testing utilities."""
    
    def __init__(self, config: Optional[AuthTestConfig] = None):
        """Initialize message preservation tester."""
        self.config = config or AuthTestConfig()
        self.websocket_tester = WebSocketAuthTester(config)
    
    async def test_message_preservation(self, token: str) -> Dict[str, Any]:
        """Test message preservation during reconnection."""
        return await self.websocket_tester.test_websocket_reconnection(token)
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.websocket_tester.cleanup()