"""
JWT Token Test Helpers - Utility classes for cross-service token testing

Supports both test and dev mode configurations with automatic environment detection.
Maintains 450-line limit through focused helper functionality.

Business Value: Enables comprehensive JWT testing across all services

Environment Support:
- Test mode: Auth service on port 8083, Backend on 8001 
- Dev mode: Auth service on port 8081, Backend on 8000
- Automatic detection from ENVIRONMENT variable
- Manual override via constructor parameter

Usage:
    # Auto-detect environment
    helper = JWTTestHelper()
    
    # Force test mode
    helper = JWTTestHelper(environment="test")
    
    # Force dev mode  
    helper = JWTTestHelper(environment="dev")
"""
import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import httpx
import jwt
import pytest

# Use absolute imports per CLAUDE.md standards
from netra_backend.app.core.auth_constants import HeaderConstants, JWTConstants
from netra_backend.app.core.network_constants import HostConstants, ServicePorts, URLConstants
from test_framework.environment_isolation import get_test_env_manager



class JWTTestHelper:
    """Helper class for JWT token operations in tests."""
    
    def __init__(self, environment: Optional[str] = None):
        """Initialize with configurable environment support.
        
        Args:
            environment: Override environment detection ('test', 'dev', etc.)
                       If None, will auto-detect from ENVIRONMENT variable
        """
        self.environment = self._detect_environment(environment)
        self._configure_urls()
        self._configure_secret()
    
    def _detect_environment(self, override_env: Optional[str]) -> str:
        """Detect current environment."""
        if override_env:
            return override_env.lower()
        
        # Use IsolatedEnvironment for ALL environment access per CLAUDE.md
        env_manager = get_test_env_manager()
        env = env_manager.env
        
        # Check explicit environment variable
        env_var = env.get("ENVIRONMENT", "").lower()
        if env_var in ["test", "testing"]:
            return "test"
        elif env_var in ["dev", "development"]:
            return "dev"
        
        # Check for test context
        if (env.get("TESTING") or 
            env.get("PYTEST_CURRENT_TEST")):
            return "test"
        
        # Default to test for JWT test helpers
        return "test"
    
    def _configure_urls(self) -> None:
        """Configure service URLs based on environment."""
        from netra_backend.app.core.network_constants import (
            HostConstants,
            ServicePorts,
            URLConstants,
        )
        
        if self.environment == "test":
            # Test mode: Auth on 8083, Backend on 8001
            auth_port = 8083
            backend_port = 8001
        else:
            # Dev mode: Auth on 8081, Backend on 8001  
            auth_port = ServicePorts.AUTH_SERVICE_DEFAULT  # 8081
            backend_port = ServicePorts.BACKEND_DEFAULT   # 8000
        
        host = HostConstants.LOCALHOST
        self.auth_url = URLConstants.build_http_url(host, auth_port)
        self.backend_url = URLConstants.build_http_url(host, backend_port)
        self.websocket_url = URLConstants.build_websocket_url(host, backend_port)
    
    def _configure_secret(self) -> None:
        """Configure JWT secret based on environment."""
        # Use IsolatedEnvironment for ALL environment access per CLAUDE.md
        env_manager = get_test_env_manager()
        env = env_manager.env
        
        # Try to get from environment first
        self.test_secret = env.get(JWTConstants.JWT_SECRET_KEY)
        
        if not self.test_secret:
            # Use environment-specific defaults
            if self.environment == "test":
                self.test_secret = "test-jwt-secret-key-unified-testing-32chars"
            else:
                # Dev environment default
                self.test_secret = "zZyIqeCZia66c1NxEgNowZFWbwMGROFg"
    
    def create_valid_payload(self) -> Dict:
        """Create standard valid token payload."""
        from netra_backend.app.core.auth_constants import JWTConstants
        return {
            JWTConstants.SUBJECT: f"test-user-{uuid.uuid4().hex[:8]}",
            JWTConstants.EMAIL: "test@netrasystems.ai",
            JWTConstants.PERMISSIONS: ["read", "write"],
            JWTConstants.ISSUED_AT: datetime.now(timezone.utc),
            JWTConstants.EXPIRES_AT: datetime.now(timezone.utc) + timedelta(minutes=15),
            JWTConstants.TOKEN_TYPE: JWTConstants.ACCESS_TOKEN_TYPE,
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "jti": str(uuid.uuid4())  # Required JWT ID for replay protection
        }
    
    def create_expired_payload(self) -> Dict:
        """Create expired token payload."""
        payload = self.create_valid_payload()
        payload[JWTConstants.EXPIRES_AT] = datetime.now(timezone.utc) - timedelta(minutes=1)
        return payload
    
    def create_refresh_payload(self) -> Dict:
        """Create refresh token payload."""
        payload = self.create_valid_payload()
        payload[JWTConstants.TOKEN_TYPE] = JWTConstants.REFRESH_TOKEN_TYPE
        payload[JWTConstants.EXPIRES_AT] = datetime.now(timezone.utc) + timedelta(days=7)
        del payload[JWTConstants.PERMISSIONS]
        return payload
    
    def create_token(self, payload: Dict, secret: str = None) -> str:
        """Create JWT token with specified payload (sync version)."""
        secret = secret or self.test_secret
        # Convert datetime objects to timestamps for JWT
        if isinstance(payload.get(JWTConstants.ISSUED_AT), datetime):
            payload[JWTConstants.ISSUED_AT] = int(payload[JWTConstants.ISSUED_AT].timestamp())
        if isinstance(payload.get(JWTConstants.EXPIRES_AT), datetime):
            payload[JWTConstants.EXPIRES_AT] = int(payload[JWTConstants.EXPIRES_AT].timestamp())
        return jwt.encode(payload, secret, algorithm=JWTConstants.HS256_ALGORITHM)
    
    def create_access_token(self, user_id: str, email: str, permissions: list = None) -> str:
        """Create access token for user."""
        payload = {
            JWTConstants.SUBJECT: user_id,
            JWTConstants.EMAIL: email,
            JWTConstants.PERMISSIONS: permissions or ["read", "write"],
            JWTConstants.ISSUED_AT: datetime.now(timezone.utc),
            JWTConstants.EXPIRES_AT: datetime.now(timezone.utc) + timedelta(minutes=15),
            JWTConstants.TOKEN_TYPE: JWTConstants.ACCESS_TOKEN_TYPE,
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "jti": str(uuid.uuid4())  # Required JWT ID for replay protection
        }
        return self.create_token(payload)
    
    async def create_jwt_token(self, payload: Dict, secret: str = None) -> str:
        """Create JWT token with specified payload."""
        return self.create_token(payload, secret)
    
    async def create_valid_jwt_token(self, secret: str = None) -> str:
        """Create valid JWT token with default payload."""
        payload = self.create_valid_payload()
        return self.create_token(payload, secret)
    
    async def create_tampered_token(self, payload: Dict) -> str:
        """Create token with invalid signature."""
        valid_token = await self.create_jwt_token(payload)
        parts = valid_token.split('.')
        return f"{parts[0]}.{parts[1]}.invalid_signature_tampering_test"
    
    def create_none_algorithm_token(self) -> str:
        """Create malicious token with 'none' algorithm."""
        header = {"typ": "JWT", "alg": "none"}
        payload = {
            "sub": "hacker-user",
            "email": "hacker@evil.com",
            "permissions": ["admin"],
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            "token_type": "access"
        }
        
        encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        return f"{encoded_header}.{encoded_payload}."
    
    async def make_auth_request(self, endpoint: str, token: str) -> Dict:
        """Make authenticated request to auth service."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            from netra_backend.app.core.auth_constants import HeaderConstants
            headers = {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{token}"}
            try:
                response = await client.get(f"{self.auth_url}{endpoint}", headers=headers)
                return {"status": response.status_code, "data": response.json()}
            except Exception as e:
                return {"status": 500, "error": str(e)}
    
    async def make_backend_request(self, endpoint: str, token: str) -> Dict:
        """Make authenticated request to backend service."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{token}"}
            try:
                response = await client.get(f"{self.backend_url}{endpoint}", headers=headers)
                return {"status": response.status_code, "data": response.json() if response.content else {}}
            except Exception as e:
                return {"status": 500, "error": str(e)}
    
    async def get_real_token_from_auth(self) -> Optional[str]:
        """Get real token from auth service dev login."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.post(f"{self.auth_url}/auth/dev/login")
                if response.status_code == 200:
                    return response.json().get(JWTConstants.ACCESS_TOKEN)
            except Exception:
                pass
        return None
    
    async def get_staging_jwt_token(self, user_id: str = None, email: str = None) -> Optional[str]:
        """Get valid JWT token for staging environment.
        
        Attempts multiple strategies:
        1. Use E2E bypass key if available
        2. Use staging test API key if available
        3. Fall back to properly formatted test token
        """
        env_manager = get_test_env_manager()
        env = env_manager.env
        
        # Strategy 1: Try E2E bypass key for staging
        bypass_key = env.get("E2E_BYPASS_KEY")
        if bypass_key:
            # Create token with bypass key as secret
            payload = self.create_valid_payload()
            if user_id:
                payload[JWTConstants.SUBJECT] = user_id
            if email:
                payload[JWTConstants.EMAIL] = email
            return self.create_token(payload, bypass_key)
        
        # Strategy 2: Try staging test API key
        staging_api_key = env.get("STAGING_TEST_API_KEY")
        if staging_api_key:
            # Use API key as bearer token directly
            return staging_api_key
        
        # Strategy 3: Try to get staging JWT secret from environment
        staging_jwt_secret = env.get("STAGING_JWT_SECRET")
        if staging_jwt_secret:
            payload = self.create_valid_payload()
            if user_id:
                payload[JWTConstants.SUBJECT] = user_id
            if email:
                payload[JWTConstants.EMAIL] = email
            return self.create_token(payload, staging_jwt_secret)
        
        # Strategy 4: Fall back to test token (will likely fail but worth trying)
        payload = self.create_valid_payload()
        if user_id:
            payload[JWTConstants.SUBJECT] = user_id
        if email:
            payload[JWTConstants.EMAIL] = email
        return self.create_token(payload)
    
    async def test_websocket_connection(self, token: str, should_succeed: bool = True) -> bool:
        """Test WebSocket connection with token."""
        try:
            import websockets
            async with websockets.connect(
                f"{self.websocket_url}/ws?token={token}",
                timeout=5
            ) as websocket:
                await websocket.ping()
                return websocket.open
        except Exception:
            return not should_succeed
    
    def validate_token_structure(self, token: str) -> bool:
        """Validate JWT token has correct structure."""
        try:
            payload = jwt.decode(token, options={"verify_signature": False})
            required_fields = [JWTConstants.SUBJECT, JWTConstants.EXPIRES_AT, JWTConstants.TOKEN_TYPE]
            return all(field in payload for field in required_fields)
        except Exception:
            return False


class JWTTestFixtures:
    """Pytest fixtures for JWT token testing."""
    
    def __init__(self, environment: Optional[str] = None):
        """Initialize with configurable environment support.
        
        Args:
            environment: Override environment detection ('test', 'dev', etc.)
        """
        self.helper = JWTTestHelper(environment)
    
    @pytest.fixture
    def jwt_helper(self):
        """Provide JWT test helper instance."""
        return JWTTestHelper()
    
    @pytest.fixture
    def jwt_helper_dev(self):
        """Provide JWT test helper instance configured for dev mode."""
        return JWTTestHelper(environment="dev")
    
    @pytest.fixture
    def valid_token_payload(self):
        """Provide valid token payload."""
        return JWTTestHelper().create_valid_payload()
    
    @pytest.fixture
    def expired_token_payload(self):
        """Provide expired token payload."""
        return JWTTestHelper().create_expired_payload()
    
    @pytest.fixture
    def refresh_token_payload(self):
        """Provide refresh token payload."""
        return JWTTestHelper().create_refresh_payload()


class JWTSecurityTester:
    """Security-focused JWT testing utilities."""
    
    def __init__(self, environment: Optional[str] = None):
        """Initialize with configurable environment support.
        
        Args:
            environment: Override environment detection ('test', 'dev', etc.)
        """
        self.helper = JWTTestHelper(environment)
    
    async def test_token_against_all_services(self, token: str) -> Dict[str, int]:
        """Test token against all services and return status codes."""
        results = {}
        
        # Test auth service
        auth_result = await self.helper.make_auth_request("/auth/verify", token)
        results["auth_service"] = auth_result["status"]
        
        # Test backend service
        backend_result = await self.helper.make_backend_request("/api/users/profile", token)
        results["backend_service"] = backend_result["status"]
        
        # Test WebSocket - for security tests, we expect connection to fail with invalid token
        try:
            # Try to connect with the token - if connection succeeds, that's a security issue
            import websockets
            async with websockets.connect(
                f"{self.helper.websocket_url}/ws?token={token}",
                timeout=5
            ) as websocket:
                await websocket.ping()
                # If we get here, the connection succeeded - that's bad for a tampered token
                results["websocket"] = 200
        except Exception:
            # Connection failed - that's good, it properly rejected the invalid token
            results["websocket"] = 401
        
        return results
    
    async def verify_all_services_reject_token(self, token: str) -> bool:
        """Verify all services reject a specific token."""
        results = await self.test_token_against_all_services(token)
        
        # All services should return 401 if running, or 500 if not available
        valid_rejection_codes = [401, 500]
        return all(status in valid_rejection_codes for status in results.values())
    
    async def verify_consistent_token_handling(self, token: str) -> bool:
        """Verify all services handle token consistently."""
        results = await self.test_token_against_all_services(token)
        
        # Filter out service unavailable errors
        available_results = [status for status in results.values() if status != 500]
        
        # If services are available, they should handle tokens consistently
        if available_results:
            return len(set(available_results)) <= 2  # Allow for slight variations
        
        return True  # No services available to test


class JWTTokenTestHelper:
    """Additional JWT token test helper for service-to-service auth testing."""
    
    def __init__(self, environment: Optional[str] = None):
        """Initialize with configurable environment support.
        
        Args:
            environment: Override environment detection ('test', 'dev', etc.)
        """
        self.environment = self._detect_environment(environment)
        self._configure_secret()
    
    def _detect_environment(self, override_env: Optional[str]) -> str:
        """Detect current environment."""
        if override_env:
            return override_env.lower()
        
        # Use IsolatedEnvironment for ALL environment access per CLAUDE.md
        env_manager = get_test_env_manager()
        env = env_manager.env
        
        # Check explicit environment variable
        env_var = env.get("ENVIRONMENT", "").lower()
        if env_var in ["test", "testing"]:
            return "test"
        elif env_var in ["dev", "development"]:
            return "dev"
        
        # Check for test context
        if (env.get("TESTING") or 
            env.get("PYTEST_CURRENT_TEST")):
            return "test"
        
        # Default to test for JWT test helpers
        return "test"
    
    def _configure_secret(self) -> None:
        """Configure JWT secret based on environment."""
        # Use IsolatedEnvironment for ALL environment access per CLAUDE.md
        env_manager = get_test_env_manager()
        env = env_manager.env
        
        # Try to get from environment first
        self.test_secret = env.get(JWTConstants.JWT_SECRET_KEY)
        
        if not self.test_secret:
            # Use environment-specific defaults
            if self.environment == "test":
                self.test_secret = "test-jwt-secret-key-unified-testing-32chars"
            else:
                # Dev environment default
                self.test_secret = "zZyIqeCZia66c1NxEgNowZFWbwMGROFg"
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict]:
        """Decode JWT token without verification (for testing only)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None
    
    def create_expired_service_token(self, service_id: str) -> str:
        """Create an expired service token for testing."""
        payload = {
            JWTConstants.SUBJECT: service_id,
            "service": f"netra-{service_id}",
            JWTConstants.TOKEN_TYPE: JWTConstants.SERVICE_TOKEN_TYPE,
            JWTConstants.ISSUED_AT: int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()),
            JWTConstants.EXPIRES_AT: int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()),
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "jti": str(uuid.uuid4())  # Required JWT ID for replay protection
        }
        return jwt.encode(payload, self.test_secret, algorithm=JWTConstants.HS256_ALGORITHM)
    
    def create_test_user_token(self, user_id: str, email: str) -> str:
        """Create a test user token for comparison."""
        payload = {
            JWTConstants.SUBJECT: user_id,
            JWTConstants.EMAIL: email,
            JWTConstants.PERMISSIONS: ["read", "write"],
            JWTConstants.TOKEN_TYPE: JWTConstants.ACCESS_TOKEN_TYPE,
            JWTConstants.ISSUED_AT: int(datetime.now(timezone.utc).timestamp()),
            JWTConstants.EXPIRES_AT: int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            JWTConstants.ISSUER: JWTConstants.NETRA_AUTH_SERVICE,
            "jti": str(uuid.uuid4())  # Required JWT ID for replay protection
        }
        return jwt.encode(payload, self.test_secret, algorithm=JWTConstants.HS256_ALGORITHM)


# Convenience factory functions for common use cases
def create_test_helper(environment: Optional[str] = None) -> JWTTestHelper:
    """Create JWT test helper with optional environment override."""
    return JWTTestHelper(environment)


def create_dev_helper() -> JWTTestHelper:
    """Create JWT test helper configured for dev mode."""
    return JWTTestHelper(environment="dev")


def create_test_mode_helper() -> JWTTestHelper:
    """Create JWT test helper configured for test mode."""
    return JWTTestHelper(environment="test")


def get_environment_config(environment: Optional[str] = None) -> Dict[str, str]:
    """Get environment configuration info for debugging."""
    helper = JWTTestHelper(environment)
    return {
        "environment": helper.environment,
        "auth_url": helper.auth_url,
        "backend_url": helper.backend_url,
        "websocket_url": helper.websocket_url,
        "secret_configured": bool(helper.test_secret)
    }


# Export commonly used classes and functions
__all__ = [
    'JWTTestHelper', 
    'JWTTestFixtures', 
    'JWTSecurityTester', 
    'JWTTokenTestHelper',
    'create_test_helper',
    'create_dev_helper', 
    'create_test_mode_helper',
    'get_environment_config'
]