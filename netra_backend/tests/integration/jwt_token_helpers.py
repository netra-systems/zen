"""
JWT Token Test Helpers

Utilities for testing JWT token functionality in integration tests.
"""

import jwt
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from unittest.mock import MagicMock


class JWTTestHelper:
    """Helper class for JWT token testing."""
    
    def __init__(self, secret_key: str = "test_secret_key"):
        """Initialize JWT test helper."""
        self.secret_key = secret_key
        self.algorithm = "HS256"
    
    def create_test_token(
        self, 
        user_id: str = "test_user_123",
        email: str = "test@example.com",
        expires_in: int = 3600,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a test JWT token."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=expires_in)
        
        payload = {
            "sub": user_id,
            "email": email,
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "iss": "netra-test",
            "aud": "netra-api"
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_expired_token(self, user_id: str = "test_user_123") -> str:
        """Create an expired JWT token."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        
        payload = {
            "sub": user_id,
            "email": "test@example.com",
            "iat": int(past_time.timestamp()),
            "exp": int(past_time.timestamp()) + 1,  # Expired 1 second after issue
            "iss": "netra-test",
            "aud": "netra-api"
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_invalid_signature_token(self, user_id: str = "test_user_123") -> str:
        """Create a JWT token with invalid signature."""
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(hours=1)
        
        payload = {
            "sub": user_id,
            "email": "test@example.com",
            "iat": int(now.timestamp()),
            "exp": int(expiry.timestamp()),
            "iss": "netra-test",
            "aud": "netra-api"
        }
        
        # Use different secret key to create invalid signature
        return jwt.encode(payload, "wrong_secret_key", algorithm=self.algorithm)
    
    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode a JWT token."""
        try:
            return jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm],
                audience="netra-api",
                issuer="netra-test"
            )
        except jwt.InvalidTokenError as e:
            return {"error": str(e)}
    
    def create_websocket_token(
        self, 
        user_id: str = "test_user_123",
        connection_id: str = "conn_123"
    ) -> str:
        """Create a WebSocket-specific JWT token."""
        return self.create_test_token(
            user_id=user_id,
            additional_claims={
                "connection_id": connection_id,
                "scope": "websocket",
                "connection_type": "websocket"
            }
        )
    
    def create_api_token(
        self,
        user_id: str = "test_user_123",
        permissions: list = None
    ) -> str:
        """Create an API-specific JWT token."""
        return self.create_test_token(
            user_id=user_id,
            additional_claims={
                "scope": "api",
                "permissions": permissions or ["read", "write"]
            }
        )
    
    def create_refresh_token(self, user_id: str = "test_user_123") -> str:
        """Create a refresh token."""
        return self.create_test_token(
            user_id=user_id,
            expires_in=86400 * 7,  # 7 days
            additional_claims={
                "token_type": "refresh",
                "scope": "refresh"
            }
        )
    
    def mock_jwt_validation(self, should_succeed: bool = True) -> MagicMock:
        """Create a mock JWT validation function."""
        mock = MagicMock()
        
        if should_succeed:
            mock.return_value = {
                "sub": "test_user_123",
                "email": "test@example.com",
                "valid": True
            }
        else:
            mock.side_effect = jwt.InvalidTokenError("Token validation failed")
        
        return mock
    
    @staticmethod
    def create_bearer_header(token: str) -> Dict[str, str]:
        """Create Authorization header with Bearer token."""
        return {"Authorization": f"Bearer {token}"}
    
    @staticmethod
    def extract_token_from_header(authorization_header: str) -> Optional[str]:
        """Extract token from Authorization header."""
        if authorization_header.startswith("Bearer "):
            return authorization_header[7:]
        return None