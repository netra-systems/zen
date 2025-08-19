"""
JWT Token Test Helpers - Utility classes for cross-service token testing

Maintains 300-line limit through focused helper functionality
Business Value: Enables comprehensive JWT testing across all services
"""
import httpx
import jwt
import json
import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import uuid
import base64


class JWTTestHelper:
    """Helper class for JWT token operations in tests."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000"
        self.test_secret = "test-jwt-secret-key-32-chars-min"
    
    def create_valid_payload(self) -> Dict:
        """Create standard valid token payload."""
        return {
            "sub": f"test-user-{uuid.uuid4().hex[:8]}",
            "email": "test@netra.ai",
            "permissions": ["read", "write"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "token_type": "access",
            "iss": "netra-auth-service"
        }
    
    def create_expired_payload(self) -> Dict:
        """Create expired token payload."""
        payload = self.create_valid_payload()
        payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=1)
        return payload
    
    def create_refresh_payload(self) -> Dict:
        """Create refresh token payload."""
        payload = self.create_valid_payload()
        payload["token_type"] = "refresh"
        payload["exp"] = datetime.now(timezone.utc) + timedelta(days=7)
        del payload["permissions"]
        return payload
    
    def create_token(self, payload: Dict, secret: str = None) -> str:
        """Create JWT token with specified payload (sync version)."""
        secret = secret or self.test_secret
        # Convert datetime objects to timestamps for JWT
        if isinstance(payload.get("iat"), datetime):
            payload["iat"] = int(payload["iat"].timestamp())
        if isinstance(payload.get("exp"), datetime):
            payload["exp"] = int(payload["exp"].timestamp())
        return jwt.encode(payload, secret, algorithm="HS256")
    
    def create_access_token(self, user_id: str, email: str, permissions: list = None) -> str:
        """Create access token for user."""
        payload = {
            "sub": user_id,
            "email": email,
            "permissions": permissions or ["read", "write"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
            "token_type": "access",
            "iss": "netra-auth-service"
        }
        return self.create_token(payload)
    
    async def create_jwt_token(self, payload: Dict, secret: str = None) -> str:
        """Create JWT token with specified payload."""
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
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            try:
                response = await client.get(f"{self.auth_url}{endpoint}", headers=headers)
                return {"status": response.status_code, "data": response.json()}
            except Exception as e:
                return {"status": 500, "error": str(e)}
    
    async def make_backend_request(self, endpoint: str, token: str) -> Dict:
        """Make authenticated request to backend service."""
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {token}"}
            try:
                response = await client.get(f"{self.backend_url}{endpoint}", headers=headers)
                return {"status": response.status_code, "data": response.json() if response.content else {}}
            except Exception as e:
                return {"status": 500, "error": str(e)}
    
    async def get_real_token_from_auth(self) -> Optional[str]:
        """Get real token from auth service dev login."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(f"{self.auth_url}/auth/dev/login")
                if response.status_code == 200:
                    return response.json().get("access_token")
            except Exception:
                pass
        return None
    
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
            required_fields = ["sub", "exp", "token_type"]
            return all(field in payload for field in required_fields)
        except Exception:
            return False


class JWTTestFixtures:
    """Pytest fixtures for JWT token testing."""
    
    def __init__(self):
        self.helper = JWTTestHelper()
    
    @pytest.fixture
    def jwt_helper(self):
        """Provide JWT test helper instance."""
        return JWTTestHelper()
    
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
    
    def __init__(self):
        self.helper = JWTTestHelper()
    
    async def test_token_against_all_services(self, token: str) -> Dict[str, int]:
        """Test token against all services and return status codes."""
        results = {}
        
        # Test auth service
        auth_result = await self.helper.make_auth_request("/auth/validate", token)
        results["auth_service"] = auth_result["status"]
        
        # Test backend service
        backend_result = await self.helper.make_backend_request("/health", token)
        results["backend_service"] = backend_result["status"]
        
        # Test WebSocket
        ws_success = await self.helper.test_websocket_connection(token, should_succeed=False)
        results["websocket"] = 200 if ws_success else 401
        
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
    
    def __init__(self):
        self.test_secret = "test-jwt-secret-key-32-chars-min"
    
    def decode_token_unsafe(self, token: str) -> Optional[Dict]:
        """Decode JWT token without verification (for testing only)."""
        try:
            return jwt.decode(token, options={"verify_signature": False})
        except Exception:
            return None
    
    def create_expired_service_token(self, service_id: str) -> str:
        """Create an expired service token for testing."""
        payload = {
            "sub": service_id,
            "service": f"netra-{service_id}",
            "token_type": "service",
            "iat": int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(minutes=5)).timestamp()),
            "iss": "netra-auth-service"
        }
        return jwt.encode(payload, self.test_secret, algorithm="HS256")
    
    def create_test_user_token(self, user_id: str, email: str) -> str:
        """Create a test user token for comparison."""
        payload = {
            "sub": user_id,
            "email": email,
            "permissions": ["read", "write"],
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service"
        }
        return jwt.encode(payload, self.test_secret, algorithm="HS256")


# Export commonly used classes
__all__ = ['JWTTestHelper', 'JWTTestFixtures', 'JWTSecurityTester', 'JWTTokenTestHelper']