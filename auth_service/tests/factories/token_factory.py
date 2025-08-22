"""
Token Test Data Factory
Creates JWT tokens and OAuth tokens for auth service testing.
Supports access tokens, refresh tokens, and service tokens with proper claims.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt

from auth_service.auth_core.models.auth_models import AuthProvider, TokenType


class TokenFactory:
    """Factory for creating test JWT tokens"""
    
    DEFAULT_SECRET = "test-jwt-secret-key-that-is-long-enough-for-testing-purposes"
    DEFAULT_ALGORITHM = "HS256"
    
    @staticmethod
    def create_token_claims(
        user_id: str = None,
        email: str = None,
        permissions: List[str] = None,
        token_type: str = TokenType.ACCESS,
        expires_in_minutes: int = 15,
        **kwargs
    ) -> Dict[str, Any]:
        """Create JWT token claims"""
        now = datetime.now(timezone.utc)
        user_id = user_id or str(uuid.uuid4())
        
        claims = {
            "sub": user_id,  # Subject (user ID)
            "email": email or f"user{user_id[:8]}@example.com",
            "type": token_type,
            "permissions": permissions or [],
            "iat": now,  # Issued at
            "exp": now + timedelta(minutes=expires_in_minutes),  # Expires at
            "jti": str(uuid.uuid4()),  # JWT ID
            **kwargs
        }
        
        return claims
    
    @staticmethod
    def create_access_token(
        user_id: str = None,
        email: str = None,
        permissions: List[str] = None,
        secret: str = None,
        algorithm: str = None,
        **kwargs
    ) -> str:
        """Create access token"""
        claims = TokenFactory.create_token_claims(
            user_id=user_id,
            email=email,
            permissions=permissions,
            token_type=TokenType.ACCESS,
            expires_in_minutes=15,
            **kwargs
        )
        
        return jwt.encode(
            claims,
            secret or TokenFactory.DEFAULT_SECRET,
            algorithm=algorithm or TokenFactory.DEFAULT_ALGORITHM
        )
    
    @staticmethod
    def create_refresh_token(
        user_id: str = None,
        email: str = None,
        secret: str = None,
        algorithm: str = None,
        **kwargs
    ) -> str:
        """Create refresh token"""
        claims = TokenFactory.create_token_claims(
            user_id=user_id,
            email=email,
            token_type=TokenType.REFRESH,
            expires_in_minutes=60 * 24 * 7,  # 7 days
            **kwargs
        )
        
        return jwt.encode(
            claims,
            secret or TokenFactory.DEFAULT_SECRET,
            algorithm=algorithm or TokenFactory.DEFAULT_ALGORITHM
        )
    
    @staticmethod
    def create_service_token(
        service_id: str = None,
        permissions: List[str] = None,
        secret: str = None,
        algorithm: str = None,
        **kwargs
    ) -> str:
        """Create service-to-service token"""
        claims = TokenFactory.create_token_claims(
            user_id=service_id or "test-service",
            email=None,
            permissions=permissions or ["service:read", "service:write"],
            token_type=TokenType.SERVICE,
            expires_in_minutes=60,  # 1 hour
            **kwargs
        )
        
        return jwt.encode(
            claims,
            secret or TokenFactory.DEFAULT_SECRET,
            algorithm=algorithm or TokenFactory.DEFAULT_ALGORITHM
        )
    
    @staticmethod
    def create_expired_token(
        user_id: str = None,
        token_type: str = TokenType.ACCESS,
        secret: str = None,
        algorithm: str = None,
        **kwargs
    ) -> str:
        """Create expired token"""
        now = datetime.now(timezone.utc)
        
        claims = {
            "sub": user_id or str(uuid.uuid4()),
            "type": token_type,
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),  # Expired 1 hour ago
            "jti": str(uuid.uuid4()),
            **kwargs
        }
        
        return jwt.encode(
            claims,
            secret or TokenFactory.DEFAULT_SECRET,
            algorithm=algorithm or TokenFactory.DEFAULT_ALGORITHM
        )
    
    @staticmethod
    def create_malformed_token() -> str:
        """Create malformed token for testing"""
        return "invalid.jwt.token"
    
    @staticmethod
    def create_token_with_wrong_secret(
        user_id: str = None,
        **kwargs
    ) -> str:
        """Create token with wrong secret"""
        return TokenFactory.create_access_token(
            user_id=user_id,
            secret="wrong-secret-key",
            **kwargs
        )
    
    @staticmethod
    def decode_token(
        token: str,
        secret: str = None,
        algorithm: str = None,
        verify: bool = True
    ) -> Dict[str, Any]:
        """Decode JWT token for testing"""
        return jwt.decode(
            token,
            secret or TokenFactory.DEFAULT_SECRET,
            algorithms=[algorithm or TokenFactory.DEFAULT_ALGORITHM],
            options={"verify_signature": verify, "verify_exp": verify}
        )


class OAuthTokenFactory:
    """Factory for creating OAuth tokens and responses"""
    
    @staticmethod
    def create_google_token_response(
        user_id: str = None,
        email: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create Google OAuth token response"""
        user_id = user_id or str(uuid.uuid4())
        email = email or f"user{user_id[:8]}@gmail.com"
        
        return {
            "access_token": f"google_access_{uuid.uuid4().hex}",
            "refresh_token": f"google_refresh_{uuid.uuid4().hex}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": "openid email profile",
            "id_token": TokenFactory.create_access_token(
                user_id=user_id,
                email=email,
                iss="https://accounts.google.com",
                aud="test-google-client-id",
                **kwargs
            )
        }
    
    @staticmethod
    def create_github_token_response(
        user_id: str = None,
        username: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create GitHub OAuth token response"""
        user_id = user_id or str(uuid.uuid4())
        username = username or f"user{user_id[:8]}"
        
        return {
            "access_token": f"github_access_{uuid.uuid4().hex}",
            "token_type": "Bearer",
            "scope": "user:email",
            "user": {
                "id": user_id,
                "login": username,
                "email": f"{username}@users.noreply.github.com",
                "name": f"GitHub User {username}",
                "avatar_url": f"https://avatars.githubusercontent.com/{username}"
            }
        }
    
    @staticmethod
    def create_oauth_state_token() -> str:
        """Create OAuth state token for CSRF protection"""
        return f"oauth_state_{uuid.uuid4().hex}"
    
    @staticmethod
    def create_authorization_code() -> str:
        """Create OAuth authorization code"""
        return f"auth_code_{uuid.uuid4().hex}"


class TokenTestUtils:
    """Utility functions for token testing"""
    
    @staticmethod
    def extract_user_id(token: str, secret: str = None) -> str:
        """Extract user ID from JWT token"""
        claims = TokenFactory.decode_token(token, secret=secret, verify=False)
        return claims.get("sub")
    
    @staticmethod
    def is_token_expired(token: str, secret: str = None) -> bool:
        """Check if token is expired"""
        try:
            TokenFactory.decode_token(token, secret=secret, verify=True)
            return False
        except jwt.ExpiredSignatureError:
            return True
        except jwt.InvalidTokenError:
            return False  # Invalid for other reasons
    
    @staticmethod
    def get_token_permissions(token: str, secret: str = None) -> List[str]:
        """Extract permissions from token"""
        claims = TokenFactory.decode_token(token, secret=secret, verify=False)
        return claims.get("permissions", [])