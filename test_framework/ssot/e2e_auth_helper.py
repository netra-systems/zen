"""
SSOT E2E Authentication Helper - Single Source of Truth for All E2E Test Authentication

This module provides the CANONICAL authentication helper for ALL e2e tests.
It ensures proper JWT authentication flow for WebSocket and API connections.

Business Value:
- Prevents authentication-related test failures (403 errors)
- Ensures consistent authentication across all e2e tests
- Validates staging/production authentication flows

CRITICAL: This is the SINGLE SOURCE OF TRUTH for e2e test authentication.
All e2e tests MUST use this helper for authentication.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import httpx
import aiohttp
import jwt
from dataclasses import dataclass

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from tests.e2e.jwt_token_helpers import JWTTestHelper
from tests.e2e.staging_config import StagingTestConfig, staging_urls


@dataclass
class E2EAuthConfig:
    """Configuration for E2E authentication."""
    auth_service_url: str = "http://localhost:8083"  # Default test auth service
    backend_url: str = "http://localhost:8002"       # Default test backend
    websocket_url: str = "ws://localhost:8002/ws"    # Default test WebSocket
    test_user_email: str = "e2e_test@example.com"
    test_user_password: str = "test_password_123"
    jwt_secret: str = "test-jwt-secret-key-unified-testing-32chars"
    timeout: float = 10.0
    
    @classmethod
    def for_staging(cls) -> "E2EAuthConfig":
        """Create configuration for staging environment using centralized config."""
        staging_config = StagingTestConfig()
        return cls(
            auth_service_url=staging_config.urls.auth_url,
            backend_url=staging_config.urls.backend_url,
            websocket_url=staging_config.urls.websocket_url,
            test_user_email=staging_config.test_user_email,
            test_user_password="staging_test_password_123",
            jwt_secret="staging-jwt-secret-key",  # Will be overridden from env
            timeout=staging_config.timeout
        )
    
    @classmethod
    def for_environment(cls, environment: str = "test") -> "E2EAuthConfig":
        """Create configuration for specified environment."""
        if environment == "staging":
            return cls.for_staging()
        return cls()  # Default to test/local configuration


class E2EAuthHelper:
    """
    SSOT Authentication Helper for ALL E2E Tests.
    
    This helper provides:
    1. JWT token generation and validation
    2. Authentication flow (login/register)
    3. WebSocket authentication headers
    4. Bearer token headers for API calls
    5. Token refresh handling
    
    CRITICAL: All e2e tests MUST use this helper for authentication.
    """
    
    def __init__(self, config: Optional[E2EAuthConfig] = None, environment: Optional[str] = None):
        """Initialize E2E authentication helper.
        
        Args:
            config: Optional E2EAuthConfig to use
            environment: Optional environment name ('test', 'staging', etc.)
                        If not provided, detects from ENV or defaults to 'test'
        """
        self.env = get_env()
        
        # Determine environment
        if environment is None:
            environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Use provided config or create based on environment
        if config is None:
            self.config = E2EAuthConfig.for_environment(environment)
        else:
            self.config = config
            
        # Override JWT secret from environment if available
        env_jwt_secret = self.env.get("JWT_SECRET_KEY")
        if env_jwt_secret:
            self.config.jwt_secret = env_jwt_secret
            
        self.jwt_helper = JWTTestHelper(environment=environment)
        self._cached_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        
    def create_test_jwt_token(
        self,
        user_id: str = "test-user-123",
        email: Optional[str] = None,
        permissions: Optional[list] = None,
        exp_minutes: int = 30
    ) -> str:
        """
        Create a valid JWT token for testing.
        
        Args:
            user_id: User ID for the token
            email: User email (defaults to config email)
            permissions: User permissions (defaults to ["read", "write"])
            exp_minutes: Token expiry in minutes
            
        Returns:
            Valid JWT token string
        """
        email = email or self.config.test_user_email
        permissions = permissions or ["read", "write"]
        
        # Create token payload
        payload = {
            "sub": user_id,
            "email": email,
            "permissions": permissions,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=exp_minutes),
            "type": "access",
            "iss": "netra-auth-service",
            "jti": f"test-{int(time.time())}"
        }
        
        # Sign token with test secret
        token = jwt.encode(payload, self.config.jwt_secret, algorithm="HS256")
        
        # Cache token for reuse
        self._cached_token = token
        self._token_expiry = payload["exp"]
        
        return token
    
    def get_auth_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Args:
            token: JWT token (uses cached if not provided)
            
        Returns:
            Headers dict with Authorization Bearer token
        """
        token = token or self._get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    def get_websocket_headers(self, token: Optional[str] = None) -> Dict[str, str]:
        """
        Get authentication headers for WebSocket connections.
        
        Args:
            token: JWT token (uses cached if not provided)
            
        Returns:
            Headers dict for WebSocket authentication
        """
        token = token or self._get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-User-ID": self._extract_user_id(token),
            "X-Test-Mode": "true"
        }
    
    async def authenticate_user(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        force_new: bool = False
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Authenticate user via auth service (login or register).
        
        Args:
            email: User email (defaults to config)
            password: User password (defaults to config)
            force_new: Force new authentication even if cached
            
        Returns:
            Tuple of (token, user_data)
        """
        # Use cached token if valid and not forcing new
        if not force_new and self._cached_token and self._is_token_valid():
            user_data = self._decode_token(self._cached_token)
            return self._cached_token, user_data
        
        email = email or self.config.test_user_email
        password = password or self.config.test_user_password
        
        async with aiohttp.ClientSession() as session:
            # Try login first
            login_url = f"{self.config.auth_service_url}/auth/login"
            login_data = {"email": email, "password": password}
            
            async with session.post(login_url, json=login_data) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data.get("access_token")
                    self._cached_token = token
                    self._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
                    return token, data.get("user", {})
            
            # If login fails, try to register
            register_url = f"{self.config.auth_service_url}/auth/register"
            register_data = {
                "email": email,
                "password": password,
                "name": f"E2E Test User {int(time.time())}"
            }
            
            async with session.post(register_url, json=register_data) as resp:
                if resp.status in [200, 201]:
                    data = await resp.json()
                    token = data.get("access_token")
                    self._cached_token = token
                    self._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=30)
                    return token, data.get("user", {})
                else:
                    error_text = await resp.text()
                    raise Exception(f"Authentication failed: {resp.status} - {error_text}")
    
    async def validate_token(self, token: str) -> bool:
        """
        Validate JWT token with auth service.
        
        Args:
            token: JWT token to validate
            
        Returns:
            True if token is valid
        """
        validate_url = f"{self.config.auth_service_url}/auth/validate"
        headers = {"Authorization": f"Bearer {token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(validate_url, headers=headers) as resp:
                return resp.status == 200
    
    def _get_valid_token(self) -> str:
        """Get a valid token, creating new if needed."""
        if self._cached_token and self._is_token_valid():
            return self._cached_token
        
        # Create new token
        return self.create_test_jwt_token()
    
    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid."""
        if not self._cached_token or not self._token_expiry:
            return False
        
        # Check expiry with 1 minute buffer
        buffer = timedelta(minutes=1)
        return datetime.now(timezone.utc) < (self._token_expiry - buffer)
    
    def _decode_token(self, token: str) -> Dict[str, Any]:
        """Decode JWT token without validation (for testing)."""
        try:
            # Decode without verification for test inspection
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return {}
    
    def _extract_user_id(self, token: str) -> str:
        """Extract user ID from token."""
        decoded = self._decode_token(token)
        return decoded.get("sub", "unknown-user")
    
    async def create_authenticated_session(self) -> aiohttp.ClientSession:
        """
        Create an authenticated aiohttp session.
        
        Returns:
            ClientSession with auth headers set
        """
        token, _ = await self.authenticate_user()
        headers = self.get_auth_headers(token)
        return aiohttp.ClientSession(headers=headers)
    
    def create_sync_authenticated_client(self) -> httpx.Client:
        """
        Create an authenticated httpx client for sync tests.
        
        Returns:
            httpx.Client with auth headers set
        """
        token = self.create_test_jwt_token()
        headers = self.get_auth_headers(token)
        return httpx.Client(headers=headers, base_url=self.config.backend_url)
    
    async def get_staging_token_async(
        self,
        email: Optional[str] = None,
        bypass_key: Optional[str] = None
    ) -> str:
        """
        Get a valid staging token using E2E auth bypass (async-safe).
        This is the SSOT method for staging authentication in async contexts.
        
        Args:
            email: Test user email
            bypass_key: E2E bypass key (uses env if not provided)
            
        Returns:
            Valid JWT token for staging
        """
        email = email or self.config.test_user_email
        bypass_key = bypass_key or self.env.get("E2E_OAUTH_SIMULATION_KEY")
        
        if not bypass_key:
            # For staging tests, use a well-known test key
            bypass_key = "staging-e2e-test-bypass-key-2025"
            
        async with aiohttp.ClientSession() as session:
            # Try staging auth bypass endpoint
            bypass_url = f"{self.config.auth_service_url}/auth/e2e/test-auth"
            headers = {
                "X-E2E-Bypass-Key": bypass_key,
                "Content-Type": "application/json"
            }
            data = {
                "email": email,
                "name": f"E2E Test User {int(time.time())}",
                "permissions": ["read", "write"]
            }
            
            try:
                async with session.post(bypass_url, headers=headers, json=data, timeout=10) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        token = result.get("access_token")
                        if token:
                            self._cached_token = token
                            self._token_expiry = datetime.now(timezone.utc) + timedelta(minutes=14)
                            return token
            except Exception as e:
                # Fall back to creating a test JWT if bypass fails
                print(f"[INFO] Staging bypass failed ({e}), using test JWT")
                
        # Fallback to test JWT
        return self.create_test_jwt_token(user_id=f"staging-user-{int(time.time())}")


class E2EWebSocketAuthHelper(E2EAuthHelper):
    """
    Extended helper specifically for WebSocket authentication in E2E tests.
    """
    
    def __init__(self, config: Optional[E2EAuthConfig] = None, environment: Optional[str] = None):
        """Initialize WebSocket auth helper with proper environment config."""
        super().__init__(config=config, environment=environment)
        self.environment = environment or self.env.get("TEST_ENV", "test")
    
    async def get_authenticated_websocket_url(self, token: Optional[str] = None) -> str:
        """
        Get WebSocket URL with authentication token as query parameter.
        
        Args:
            token: JWT token (uses cached if not provided)
            
        Returns:
            WebSocket URL with auth token
        """
        token = token or self._get_valid_token()
        return f"{self.config.websocket_url}?token={token}"
    
    async def connect_authenticated_websocket(self, timeout: float = 10.0):
        """
        Connect to WebSocket with proper authentication.
        SSOT method that handles staging environment properly.
        
        Args:
            timeout: Connection timeout in seconds
            
        Returns:
            Authenticated WebSocket connection
        """
        import websockets
        
        # For staging, use async-safe token generation
        if self.environment == "staging":
            token = await self.get_staging_token_async()
        else:
            token = self._get_valid_token()
            
        headers = self.get_websocket_headers(token)
        
        # Add explicit timeout for staging connections
        try:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.config.websocket_url,
                    additional_headers=headers,
                    open_timeout=timeout
                ),
                timeout=timeout
            )
            return websocket
        except asyncio.TimeoutError:
            # Provide better error for debugging
            raise TimeoutError(
                f"WebSocket connection to {self.config.websocket_url} timed out after {timeout}s. "
                f"This may indicate auth rejection or network issues. Token provided: {bool(token)}"
            )
    
    async def test_websocket_auth_flow(self) -> bool:
        """
        Test complete WebSocket authentication flow.
        
        Returns:
            True if authentication successful
        """
        try:
            # Create token
            token = self.create_test_jwt_token()
            
            # Validate token
            is_valid = await self.validate_token(token)
            if not is_valid:
                return False
            
            # Connect to WebSocket
            ws = await self.connect_authenticated_websocket()
            
            # Send test message
            test_msg = json.dumps({
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await ws.send(test_msg)
            
            # Wait for response (with timeout)
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            
            # Close connection
            await ws.close()
            
            return True
            
        except Exception as e:
            print(f"WebSocket auth test failed: {e}")
            return False


# SSOT Export - All e2e tests MUST use these
__all__ = [
    "E2EAuthConfig",
    "E2EAuthHelper", 
    "E2EWebSocketAuthHelper"
]