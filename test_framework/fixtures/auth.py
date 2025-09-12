"""
Authentication Fixtures for E2E Testing

This module provides authentication testing utilities including OAuth providers,
JWT token creation, and SSO testing components for comprehensive E2E testing.

BVJ (Business Value Justification):
- Segment: All customer segments (auth affects everyone)  
- Business Goal: Enable comprehensive auth testing protecting $500K+ ARR
- Value Impact: Prevents auth failures that block user conversions
- Revenue Impact: Each auth test failure caught saves $10K+ MRR monthly

CRITICAL: This module supports Golden Path user flow testing by providing
real authentication fixtures and OAuth provider mocking capabilities.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import jwt

from shared.isolated_environment import IsolatedEnvironment


@dataclass
class OAuthTokenData:
    """OAuth token data structure"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


@dataclass
class SAMLAssertion:
    """SAML assertion data structure"""
    assertion_id: str
    issuer: str
    subject: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    valid_until: datetime = field(default_factory=lambda: datetime.now() + timedelta(hours=8))


class MockOAuthProvider:
    """Mock OAuth provider for E2E testing.
    
    Provides realistic OAuth flows for testing without requiring external providers.
    Supports Google, GitHub, Microsoft OAuth patterns.
    
    CRITICAL: This enables comprehensive user journey testing for all auth methods
    protecting Enterprise SSO deals ($15K+ MRR per customer).
    """
    
    def __init__(self, provider_name: str):
        self.provider_name = provider_name
        self.client_id = f"test_client_{provider_name}"
        self.client_secret = f"test_secret_{provider_name}" 
        self.auth_codes = {}  # Store auth codes temporarily
        self.tokens = {}      # Store issued tokens
        
    def create_mock_auth_code(self, user_info: Dict[str, Any]) -> str:
        """Create a mock authorization code for OAuth flow."""
        auth_code = f"auth_code_{uuid.uuid4().hex[:16]}"
        self.auth_codes[auth_code] = {
            "user_info": user_info,
            "created_at": time.time(),
            "expires_at": time.time() + 600  # 10 minutes
        }
        return auth_code
    
    async def exchange_code_for_token(self, auth_code: str, redirect_uri: str) -> Optional[Dict[str, Any]]:
        """Exchange authorization code for access token."""
        if auth_code not in self.auth_codes:
            return None
            
        code_data = self.auth_codes[auth_code]
        
        # Check if code expired
        if time.time() > code_data["expires_at"]:
            del self.auth_codes[auth_code]
            return None
            
        # Create access token
        access_token = f"access_token_{uuid.uuid4().hex[:24]}"
        refresh_token = f"refresh_token_{uuid.uuid4().hex[:24]}"
        
        token_data = {
            "access_token": access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": refresh_token,
            "scope": "read_user email",
            "user_info": code_data["user_info"]
        }
        
        # Store token for validation
        self.tokens[access_token] = token_data
        
        # Clean up used auth code
        del self.auth_codes[auth_code]
        
        return token_data
    
    async def validate_token(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Validate an access token and return user info."""
        return self.tokens.get(access_token)
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh an access token using refresh token."""
        for token_data in self.tokens.values():
            if token_data.get("refresh_token") == refresh_token:
                # Create new access token
                new_access_token = f"access_token_{uuid.uuid4().hex[:24]}"
                new_token_data = {
                    **token_data,
                    "access_token": new_access_token,
                    "expires_in": 3600
                }
                
                self.tokens[new_access_token] = new_token_data
                return new_token_data
                
        return None


class MockSAMLProvider:
    """Mock SAML provider for Enterprise SSO testing.
    
    Provides realistic SAML flows for testing Enterprise authentication.
    Critical for validating $15K+ MRR Enterprise customer auth flows.
    """
    
    def __init__(self):
        self.issuer = "https://test-saml-provider.netra.ai"
        self.assertions = {}
        
    def create_mock_assertion(self, subject: str, attributes: Dict[str, Any] = None) -> str:
        """Create a mock SAML assertion."""
        assertion_id = f"saml_assertion_{uuid.uuid4().hex[:16]}"
        
        assertion = SAMLAssertion(
            assertion_id=assertion_id,
            issuer=self.issuer,
            subject=subject,
            attributes=attributes or {}
        )
        
        self.assertions[assertion_id] = assertion
        return assertion_id
    
    def validate_assertion(self, assertion_id: str) -> Optional[Dict[str, Any]]:
        """Validate a SAML assertion and return claims."""
        assertion = self.assertions.get(assertion_id)
        if not assertion:
            return None
            
        # Check if assertion expired
        if datetime.now() > assertion.valid_until:
            del self.assertions[assertion_id]
            return None
            
        return {
            "assertion_id": assertion.assertion_id,
            "issuer": assertion.issuer,
            "subject": assertion.subject,
            "attributes": assertion.attributes,
            "valid_until": assertion.valid_until.isoformat()
        }


class SSOTestComponents:
    """Collection of SSO testing components.
    
    Provides unified access to OAuth and SAML testing utilities.
    """
    
    def __init__(self):
        self.oauth_providers = {
            "google": MockOAuthProvider("google"),
            "github": MockOAuthProvider("github"), 
            "microsoft": MockOAuthProvider("microsoft")
        }
        self.saml_provider = MockSAMLProvider()
    
    def get_oauth_provider(self, provider_name: str) -> MockOAuthProvider:
        """Get OAuth provider by name."""
        return self.oauth_providers.get(provider_name)
    
    def get_saml_provider(self) -> MockSAMLProvider:
        """Get SAML provider."""
        return self.saml_provider


def create_real_jwt_token(user_id: str, permissions: List[str], email: Optional[str] = None, expires_in: int = 3600) -> str:
    """Create a real JWT token for testing.
    
    CRITICAL: Creates valid JWT tokens for Golden Path testing.
    Enables end-to-end authentication validation without mocking.
    
    Args:
        user_id: User identifier for the JWT subject
        permissions: List of permissions to include in the token
        email: User email (optional, defaults to {user_id}@test.netra.ai)
        expires_in: Token expiration in seconds (default: 3600)
    
    Returns:
        Encoded JWT token string
    
    Backwards Compatibility:
        - Supports old pattern: create_real_jwt_token(user_id, permissions)
        - Supports old pattern: create_real_jwt_token(user_id, permissions, expires_in=N)
        - Supports new pattern: create_real_jwt_token(user_id, permissions, email="x@y.com")
    """
    env = IsolatedEnvironment()
    secret = env.get("JWT_SECRET", "test_secret_key_for_integration_tests")
    
    # Generate intelligent default email if not provided (backwards compatibility)
    if email is None:
        email = f"{user_id}@test.netra.ai"
    
    now = datetime.utcnow()
    payload = {
        "sub": user_id,
        "email": email,
        "permissions": permissions,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": "netra-test",
        "aud": "netra-api"
    }
    
    return jwt.encode(payload, secret, algorithm="HS256")


def create_test_user_token(user_id: Optional[str] = None, permissions: Optional[List[str]] = None) -> str:
    """Create a test user token with default values."""
    if user_id is None:
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    if permissions is None:
        permissions = ["basic_chat", "agent_access"]
        
    email = f"{user_id}@test.netra.ai"
    return create_real_jwt_token(user_id, permissions, email)


# Export all components for easy importing
__all__ = [
    'MockOAuthProvider',
    'MockSAMLProvider', 
    'SSOTestComponents',
    'OAuthTokenData',
    'SAMLAssertion',
    'create_real_jwt_token',
    'create_test_user_token'
]