"""
Authentication Test Fixtures

Provides comprehensive authentication fixtures for testing.
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock
import json
import uuid
from datetime import datetime, timezone, timedelta


class MockAuthToken:
    """Mock authentication token."""
    
    def __init__(self, user_id: str, permissions: List[str] = None,
                 expires_in: int = 3600):
        self.user_id = user_id
        self.permissions = permissions or []
        self.expires_in = expires_in
        self.created_at = time.time()
        self.token = f"mock_token_{uuid.uuid4().hex[:16]}"
    
    def is_expired(self) -> bool:
        """Check if token is expired."""
        return time.time() > (self.created_at + self.expires_in)
    
    def has_permission(self, permission: str) -> bool:
        """Check if token has permission."""
        return permission in self.permissions or "admin" in self.permissions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "token": self.token,
            "user_id": self.user_id,
            "permissions": self.permissions,
            "expires_at": self.created_at + self.expires_in,
            "created_at": self.created_at
        }


class MockAuthService:
    """Mock authentication service for testing."""
    
    def __init__(self):
        self.tokens: Dict[str, MockAuthToken] = {}
        self.users: Dict[str, Dict[str, Any]] = {}
        self.auth_attempts: List[Dict[str, Any]] = []
        
    async def authenticate(self, username: str, password: str) -> Optional[MockAuthToken]:
        """Mock authentication."""
        self.auth_attempts.append({
            "username": username,
            "password": password,
            "timestamp": time.time(),
            "success": False
        })
        
        # Mock successful auth for specific test users
        if username in ["test_user", "admin_user", "enterprise_user"]:
            permissions = []
            if username == "admin_user":
                permissions = ["admin", "user"]
            elif username == "enterprise_user":
                permissions = ["enterprise", "user"]
            else:
                permissions = ["user"]
            
            token = MockAuthToken(username, permissions)
            self.tokens[token.token] = token
            self.auth_attempts[-1]["success"] = True
            return token
        
        return None
    
    async def validate_token(self, token: str) -> Optional[MockAuthToken]:
        """Validate an authentication token."""
        mock_token = self.tokens.get(token)
        if mock_token and not mock_token.is_expired():
            return mock_token
        return None
    
    async def refresh_token(self, token: str) -> Optional[MockAuthToken]:
        """Refresh an authentication token."""
        old_token = await self.validate_token(token)
        if old_token:
            new_token = MockAuthToken(old_token.user_id, old_token.permissions)
            self.tokens[new_token.token] = new_token
            # Remove old token
            del self.tokens[token]
            return new_token
        return None
    
    async def revoke_token(self, token: str) -> bool:
        """Revoke an authentication token."""
        if token in self.tokens:
            del self.tokens[token]
            return True
        return False
    
    def create_user(self, user_id: str, email: str, permissions: List[str] = None) -> Dict[str, Any]:
        """Create a mock user."""
        user = {
            "user_id": user_id,
            "email": email,
            "permissions": permissions or ["user"],
            "created_at": time.time(),
            "active": True
        }
        self.users[user_id] = user
        return user
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information."""
        return self.users.get(user_id)
    
    def list_active_tokens(self) -> List[Dict[str, Any]]:
        """List all active tokens."""
        return [
            token.to_dict() for token in self.tokens.values()
            if not token.is_expired()
        ]


class MockJWTManager:
    """Mock JWT token manager."""
    
    def __init__(self, secret_key: str = "test_secret"):
        self.secret_key = secret_key
        self.issued_tokens: Dict[str, Dict[str, Any]] = {}
    
    def generate_token(self, user_id: str, permissions: List[str] = None,
                      expires_in: int = 3600) -> str:
        """Generate a mock JWT token."""
        token_id = str(uuid.uuid4())
        token_data = {
            "sub": user_id,
            "permissions": permissions or [],
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "jti": token_id
        }
        
        # Simulate JWT encoding (simplified)
        mock_jwt = f"mock.jwt.{token_id}"
        self.issued_tokens[mock_jwt] = token_data
        
        return mock_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode a mock JWT token."""
        token_data = self.issued_tokens.get(token)
        if token_data and token_data["exp"] > int(time.time()):
            return token_data
        return None
    
    def validate_token(self, token: str) -> bool:
        """Validate a JWT token."""
        return self.decode_token(token) is not None
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token."""
        if token in self.issued_tokens:
            del self.issued_tokens[token]
            return True
        return False


class MockOAuthProvider:
    """Mock OAuth provider for testing."""
    
    def __init__(self, provider_name: str = "test_oauth"):
        self.provider_name = provider_name
        self.client_id = f"mock_client_{uuid.uuid4().hex[:8]}"
        self.client_secret = f"mock_secret_{uuid.uuid4().hex[:16]}"
        self.auth_codes: Dict[str, Dict[str, Any]] = {}
        self.access_tokens: Dict[str, Dict[str, Any]] = {}
    
    def generate_auth_url(self, redirect_uri: str, state: str = None) -> str:
        """Generate OAuth authorization URL."""
        return f"https://mock-oauth.example.com/authorize?client_id={self.client_id}&redirect_uri={redirect_uri}&state={state or ''}"
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        if code in self.auth_codes:
            code_data = self.auth_codes[code]
            access_token = f"mock_access_token_{uuid.uuid4().hex[:16]}"
            refresh_token = f"mock_refresh_token_{uuid.uuid4().hex[:16]}"
            
            token_data = {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": code_data.get("scope", "read"),
                "user_info": code_data.get("user_info", {})
            }
            
            self.access_tokens[access_token] = token_data
            del self.auth_codes[code]  # Code is single use
            
            return token_data
        
        return None
    
    def create_mock_auth_code(self, user_info: Dict[str, Any], scope: str = "read") -> str:
        """Create a mock authorization code for testing."""
        auth_code = f"mock_auth_code_{uuid.uuid4().hex[:16]}"
        self.auth_codes[auth_code] = {
            "user_info": user_info,
            "scope": scope,
            "created_at": time.time(),
            "expires_at": time.time() + 600  # 10 minutes
        }
        return auth_code
    
    async def get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user info from access token."""
        token_data = self.access_tokens.get(access_token)
        if token_data:
            return token_data.get("user_info", {})
        return None


class MockSAMLProvider:
    """Mock SAML provider for testing."""
    
    def __init__(self, issuer: str = "https://mock-saml.example.com"):
        self.issuer = issuer
        self.certificates: List[str] = ["mock_cert_123"]
        self.assertions: Dict[str, Dict[str, Any]] = {}
    
    def create_mock_assertion(self, user_email: str, attributes: Dict[str, Any] = None) -> str:
        """Create a mock SAML assertion."""
        assertion_id = str(uuid.uuid4())
        assertion_data = {
            "id": assertion_id,
            "issuer": self.issuer,
            "subject": user_email,
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "attributes": attributes or {}
        }
        
        # Simulate base64 encoded SAML assertion
        mock_assertion = f"mock_saml_assertion_{assertion_id}"
        self.assertions[mock_assertion] = assertion_data
        
        return mock_assertion
    
    def validate_assertion(self, assertion: str) -> Optional[Dict[str, Any]]:
        """Validate a SAML assertion."""
        return self.assertions.get(assertion)


# Fixture functions for pytest

def create_mock_auth_service() -> MockAuthService:
    """Create a mock authentication service."""
    return MockAuthService()

def create_mock_jwt_manager() -> MockJWTManager:
    """Create a mock JWT manager."""
    return MockJWTManager()

def create_mock_oauth_provider() -> MockOAuthProvider:
    """Create a mock OAuth provider."""
    return MockOAuthProvider()

def create_mock_saml_provider() -> MockSAMLProvider:
    """Create a mock SAML provider."""
    return MockSAMLProvider()

def create_test_user_token(user_id: str = "test_user", 
                          permissions: List[str] = None) -> MockAuthToken:
    """Create a test user token."""
    return MockAuthToken(user_id, permissions or ["user"])

def create_admin_token(user_id: str = "admin_user") -> MockAuthToken:
    """Create an admin token."""
    return MockAuthToken(user_id, ["admin", "user"])

def create_enterprise_token(user_id: str = "enterprise_user") -> MockAuthToken:
    """Create an enterprise token."""
    return MockAuthToken(user_id, ["enterprise", "user"])

async def authenticate_test_user(auth_service: MockAuthService,
                               username: str = "test_user",
                               password: str = "test_password") -> Optional[MockAuthToken]:
    """Authenticate a test user."""
    return await auth_service.authenticate(username, password)

def mock_auth_middleware():
    """Create mock authentication middleware."""
    async def middleware(request, call_next):
        # Add mock auth token to request
        if hasattr(request, "headers") and "authorization" in request.headers:
            token = request.headers["authorization"].replace("Bearer ", "")
            # Mock validation - in real middleware would validate properly
            request.state.user_token = MockAuthToken("test_user", ["user"])
        
        return await call_next(request)
    
    return middleware

def create_auth_test_data() -> Dict[str, Any]:
    """Create comprehensive auth test data."""
    return {
        "users": [
            {"username": "test_user", "email": "test@example.com", "permissions": ["user"]},
            {"username": "admin_user", "email": "admin@example.com", "permissions": ["admin", "user"]},
            {"username": "enterprise_user", "email": "enterprise@example.com", "permissions": ["enterprise", "user"]}
        ],
        "oauth_providers": [
            {"name": "google", "client_id": "mock_google_client"},
            {"name": "github", "client_id": "mock_github_client"}
        ],
        "saml_providers": [
            {"issuer": "https://enterprise-idp.example.com", "name": "Enterprise IDP"}
        ]
    }