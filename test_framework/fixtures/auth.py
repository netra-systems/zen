"""
Authentication Test Fixtures

Provides comprehensive authentication fixtures for testing with support for both
mock tokens (unit tests) and real JWT tokens (integration/e2e tests).

Key Features:
- Environment guards prevent usage in production
- Configurable real JWT token generation for integration tests
- Backward compatibility with existing mock token tests
- Comprehensive SSO/SAML testing components

Usage Examples:

    # Unit tests - use mock tokens (default)
    token = create_test_user_token("user123")
    
    # Integration tests - use real JWTs
    token = create_test_user_token("user123", use_real_jwt=True)
    
    # Create real JWT directly
    jwt_token = create_real_jwt_token("user123", ["user", "admin"])
    
    # JWT manager with real tokens
    jwt_manager = create_mock_jwt_manager(use_real_jwt=True)
    
Environment Variables:
- NETRA_ENV: Environment name (prevents usage in production)
- JWT_SECRET: Secret key for JWT signing (defaults to test_secret_key)

Requirements:
- PyJWT library required for real JWT tokens: pip install pyjwt
"""

import asyncio
import os
import time
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock
import json
import uuid
from datetime import datetime, timezone, timedelta

try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    jwt = None


class MockAuthToken:
    """Mock authentication token."""
    
    def __init__(self, user_id: str, permissions: List[str] = None,
                 expires_in: int = 3600, use_real_jwt: bool = False):
        # Environment guard - prevent mock tokens in production
        current_env = os.getenv("NETRA_ENV", "development")
        if current_env == "production":
            raise ValueError("Mock tokens are not allowed in production environment")
            
        self.user_id = user_id
        self.permissions = permissions or []
        self.expires_in = expires_in
        self.created_at = time.time()
        
        if use_real_jwt and JWT_AVAILABLE:
            self.token = self._create_real_jwt_token()
        else:
            self.token = f"mock_token_{uuid.uuid4().hex[:16]}"
    
    def _create_real_jwt_token(self) -> str:
        """Create a real JWT token for integration/e2e tests."""
        secret = os.getenv("JWT_SECRET", "test_secret_key")
        payload = {
            "sub": self.user_id,
            "permissions": self.permissions,
            "type": "access",
            "exp": datetime.utcnow() + timedelta(seconds=self.expires_in),
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4())
        }
        return jwt.encode(payload, secret, algorithm="HS256")
    
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
    
    def __init__(self, secret_key: str = "test_secret", use_real_jwt: bool = False):
        # Environment guard - prevent usage in production
        current_env = os.getenv("NETRA_ENV", "development")
        if current_env == "production":
            raise ValueError("Mock JWT manager is not allowed in production environment")
            
        self.secret_key = secret_key
        self.issued_tokens: Dict[str, Dict[str, Any]] = {}
        self.use_real_jwt = use_real_jwt and JWT_AVAILABLE
    
    def generate_token(self, user_id: str, permissions: List[str] = None,
                      expires_in: int = 3600) -> str:
        """Generate a JWT token (real or mock based on configuration)."""
        token_id = str(uuid.uuid4())
        token_data = {
            "sub": user_id,
            "permissions": permissions or [],
            "iat": int(time.time()),
            "exp": int(time.time()) + expires_in,
            "jti": token_id
        }
        
        if self.use_real_jwt:
            # Generate real JWT token
            payload = {
                "sub": user_id,
                "permissions": permissions or [],
                "type": "access",
                "exp": datetime.utcnow() + timedelta(seconds=expires_in),
                "iat": datetime.utcnow(),
                "jti": token_id
            }
            real_jwt = jwt.encode(payload, self.secret_key, algorithm="HS256")
            self.issued_tokens[real_jwt] = token_data
            return real_jwt
        else:
            # Simulate JWT encoding (simplified)
            mock_jwt = f"mock.jwt.{token_id}"
            self.issued_tokens[mock_jwt] = token_data
            return mock_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode a JWT token (real or mock)."""
        if self.use_real_jwt and not token.startswith("mock.jwt."):
            try:
                # Decode real JWT token
                decoded = jwt.decode(token, self.secret_key, algorithms=["HS256"])
                # Convert to our internal format
                return {
                    "sub": decoded.get("sub"),
                    "permissions": decoded.get("permissions", []),
                    "iat": decoded.get("iat"),
                    "exp": decoded.get("exp"),
                    "jti": decoded.get("jti")
                }
            except jwt.InvalidTokenError:
                return None
        else:
            # Handle mock tokens
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

def create_mock_jwt_manager(use_real_jwt: bool = False) -> MockJWTManager:
    """Create a mock JWT manager."""
    return MockJWTManager(use_real_jwt=use_real_jwt)

def create_mock_oauth_provider() -> MockOAuthProvider:
    """Create a mock OAuth provider."""
    return MockOAuthProvider()

def create_mock_saml_provider() -> MockSAMLProvider:
    """Create a mock SAML provider."""
    return MockSAMLProvider()


class EnterpriseTokenManager:
    """Enterprise token management for SSO/SAML testing."""
    
    def __init__(self):
        self.tokens: Dict[str, Dict[str, Any]] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
    
    async def create_enterprise_session(self, saml_assertion: Dict[str, Any]) -> str:
        """Create enterprise session from SAML assertion."""
        session_id = f"enterprise_session_{uuid.uuid4().hex[:16]}"
        self.sessions[session_id] = {
            "assertion": saml_assertion,
            "created_at": time.time(),
            "expires_at": time.time() + 28800,  # 8 hours
            "user_id": saml_assertion.get("subject"),
            "attributes": saml_assertion.get("attributes", {})
        }
        return session_id
    
    async def validate_enterprise_token(self, token: str) -> bool:
        """Validate enterprise token."""
        token_data = self.tokens.get(token)
        if not token_data:
            return False
        return token_data["expires_at"] > time.time()


class MockIdPErrorGenerator:
    """Generate mock IdP errors for testing."""
    
    @staticmethod
    async def create_invalid_assertion() -> Dict[str, Any]:
        """Create SAML assertion with invalid issuer."""
        return {
            "id": str(uuid.uuid4()),
            "issuer": "https://invalid-issuer.malicious.com",  # Invalid issuer
            "subject": "test@example.com",
            "issued_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "attributes": {"role": "user"}
        }
    
    @staticmethod
    async def create_expired_assertion() -> Dict[str, Any]:
        """Create expired SAML assertion."""
        return {
            "id": str(uuid.uuid4()),
            "issuer": "https://enterprise-idp.example.com",
            "subject": "test@example.com",
            "issued_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),  # Already expired
            "attributes": {"role": "user"}
        }
    
    @staticmethod
    async def create_malformed_assertion() -> Dict[str, Any]:
        """Create malformed SAML assertion."""
        return {
            "id": str(uuid.uuid4()),
            "issuer": "https://enterprise-idp.example.com",
            "subject": "test@example.com",
            # Missing required fields like issued_at, expires_at
            "attributes": {"role": "user"}
        }


class SAMLAssertionValidator:
    """SAML assertion validator for testing."""
    
    def __init__(self):
        self.trusted_issuers = [
            "https://enterprise-idp.example.com",
            "https://trusted-saml.company.com"
        ]
    
    async def validate_assertion(self, assertion: Dict[str, Any]) -> bool:
        """Validate SAML assertion."""
        # Check issuer
        if assertion.get("issuer") not in self.trusted_issuers:
            raise ValueError("Invalid issuer")
        
        # Check expiration
        expires_at = assertion.get("expires_at")
        if expires_at:
            try:
                expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expiry_time < datetime.now(timezone.utc):
                    raise ValueError("Assertion expired")
            except ValueError as e:
                if "Assertion expired" in str(e):
                    raise
                raise ValueError("Invalid expiration format")
        
        # Check required fields
        required_fields = ["id", "issuer", "subject"]
        for field in required_fields:
            if field not in assertion or not assertion[field]:
                raise ValueError(f"Missing required field: {field}")
        
        return True
    
    async def extract_user_info(self, assertion: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from SAML assertion."""
        await self.validate_assertion(assertion)  # Validate first
        
        return {
            "user_id": assertion["subject"],
            "email": assertion["subject"],  # Assume subject is email
            "attributes": assertion.get("attributes", {}),
            "issuer": assertion["issuer"]
        }


class SSOTestComponents:
    """Comprehensive SSO test components."""
    
    def __init__(self):
        self.token_manager = EnterpriseTokenManager()
        self.saml_validator = SAMLAssertionValidator()
        self.error_generator = MockIdPErrorGenerator()
    
    async def create_test_scenario(self, scenario_type: str) -> Dict[str, Any]:
        """Create test scenario data."""
        if scenario_type == "invalid_issuer":
            return await self.error_generator.create_invalid_assertion()
        elif scenario_type == "expired_assertion":
            return await self.error_generator.create_expired_assertion()
        elif scenario_type == "malformed_assertion":
            return await self.error_generator.create_malformed_assertion()
        else:
            # Valid scenario
            return {
                "id": str(uuid.uuid4()),
                "issuer": "https://enterprise-idp.example.com",
                "subject": "test@example.com",
                "issued_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "attributes": {"role": "user", "department": "engineering"}
            }


def create_test_user_token(user_id: str = "test_user", 
                          permissions: List[str] = None,
                          use_real_jwt: bool = False) -> MockAuthToken:
    """Create a test user token."""
    return MockAuthToken(user_id, permissions or ["user"], use_real_jwt=use_real_jwt)

def create_admin_token(user_id: str = "admin_user", use_real_jwt: bool = False) -> MockAuthToken:
    """Create an admin token."""
    return MockAuthToken(user_id, ["admin", "user"], use_real_jwt=use_real_jwt)

def create_enterprise_token(user_id: str = "enterprise_user", use_real_jwt: bool = False) -> MockAuthToken:
    """Create an enterprise token."""
    return MockAuthToken(user_id, ["enterprise", "user"], use_real_jwt=use_real_jwt)

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

class SSOTestComponents:
    """Comprehensive SSO testing components for SAML and OAuth integration tests."""
    
    def __init__(self):
        self.oauth_provider = MockOAuthProvider()
        self.saml_provider = MockSAMLProvider()
        self.auth_service = MockAuthService()
        self.jwt_manager = MockJWTManager(use_real_jwt=False)
        self._setup_test_data()
    
    def _setup_test_data(self):
        """Initialize test data."""
        # Create test users
        self.auth_service.create_user("sso_user", "sso@example.com", ["user"])
        self.auth_service.create_user("enterprise_sso", "enterprise@example.com", ["enterprise", "user"])
        
    def create_saml_assertion(self, email: str = "test@example.com", 
                             attributes: Dict[str, Any] = None) -> str:
        """Create a SAML assertion for testing."""
        return self.saml_provider.create_mock_assertion(email, attributes)
    
    def create_oauth_code(self, user_info: Dict[str, Any] = None) -> str:
        """Create an OAuth authorization code for testing."""
        user_info = user_info or {"email": "oauth@example.com", "name": "OAuth User"}
        return self.oauth_provider.create_mock_auth_code(user_info)
    
    async def authenticate_with_saml(self, assertion: str) -> Optional[Dict[str, Any]]:
        """Mock SAML authentication flow."""
        assertion_data = self.saml_provider.validate_assertion(assertion)
        if assertion_data:
            # Create JWT token for successful SAML auth
            token = self.jwt_manager.generate_token(
                assertion_data["subject"], 
                ["user", "saml"]
            )
            return {
                "token": token,
                "user_email": assertion_data["subject"],
                "auth_method": "saml"
            }
        return None
    
    async def authenticate_with_oauth(self, code: str, redirect_uri: str = "http://localhost:3000/callback") -> Optional[Dict[str, Any]]:
        """Mock OAuth authentication flow."""
        token_data = await self.oauth_provider.exchange_code_for_token(code, redirect_uri)
        if token_data:
            user_info = token_data.get("user_info", {})
            token = self.jwt_manager.generate_token(
                user_info.get("email", "unknown"), 
                ["user", "oauth"]
            )
            return {
                "token": token,
                "user_info": user_info,
                "auth_method": "oauth"
            }
        return None
    
    def setup_enterprise_saml(self, domain: str = "enterprise.com") -> Dict[str, Any]:
        """Setup enterprise SAML configuration."""
        return {
            "issuer": f"https://idp.{domain}",
            "sso_url": f"https://idp.{domain}/sso",
            "certificate": "mock_enterprise_cert",
            "domain": domain
        }
    
    def create_test_scenarios(self) -> Dict[str, Any]:
        """Create comprehensive test scenarios."""
        return {
            "valid_saml": self.create_saml_assertion("valid@enterprise.com"),
            "expired_saml": self.create_saml_assertion("expired@enterprise.com", {"expired": True}),
            "valid_oauth_code": self.create_oauth_code({"email": "oauth@example.com"}),
            "invalid_oauth_code": "invalid_code_12345"
        }


def create_real_jwt_token(user_id: str, permissions: List[str] = None, 
                         token_type: str = "access", expires_in: int = 3600) -> str:
    """Create a real JWT token for integration/e2e tests.
    
    Args:
        user_id: User identifier
        permissions: List of user permissions
        token_type: Type of token ('access' or 'refresh')
        expires_in: Token expiration time in seconds
        
    Returns:
        Real JWT token string
        
    Raises:
        ValueError: If JWT library is not available or in production environment
    """
    current_env = os.getenv("NETRA_ENV", "development")
    if current_env == "production":
        raise ValueError("Real JWT creation is not allowed in production environment")
        
    if not JWT_AVAILABLE:
        raise ValueError("JWT library not available. Install with: pip install pyjwt")
    
    secret = os.getenv("JWT_SECRET", "test_secret_key")
    payload = {
        "sub": user_id,
        "permissions": permissions or [],
        "type": token_type,
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())
    }
    return jwt.encode(payload, secret, algorithm="HS256")


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