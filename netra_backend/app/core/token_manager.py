"""Token Manager for JWT token operations

Business Value Justification (BVJ):
- Segment: Platform/Internal (affects all authentication flows)
- Business Goal: Secure and efficient token management
- Value Impact: Enables secure user authentication and session management
- Strategic Impact: Foundation for all authenticated API operations
"""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import logging

logger = logging.getLogger(__name__)


class TokenType:
    """Token type constants"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    TEMPORARY = "temporary"


class TokenError(Exception):
    """Token-related errors"""
    pass


class TokenExpiredError(TokenError):
    """Token has expired"""
    pass


class TokenInvalidError(TokenError):
    """Token is invalid"""
    pass


class Token:
    """Token data model"""
    
    def __init__(
        self,
        token_id: str,
        token_type: str,
        user_id: str,
        payload: Dict[str, Any],
        expires_at: datetime,
        created_at: Optional[datetime] = None
    ):
        self.token_id = token_id
        self.token_type = token_type
        self.user_id = user_id
        self.payload = payload
        self.expires_at = expires_at
        self.created_at = created_at or datetime.now(UTC)
        self.is_revoked = False
        self.last_used = None


class TokenManager:
    """Manages JWT tokens and token operations"""
    
    def __init__(self, secret_key: str = "default-secret-key", algorithm: str = "HS256"):
        self.secret_key = secret_key.encode('utf-8')
        self.algorithm = algorithm
        self.tokens: Dict[str, Token] = {}
        self.user_tokens: Dict[str, List[str]] = {}  # user_id -> token_ids
        
        # Default token lifetimes
        self.access_token_lifetime = timedelta(hours=1)
        self.refresh_token_lifetime = timedelta(days=30)
        self.api_key_lifetime = timedelta(days=365)
        self.temporary_token_lifetime = timedelta(minutes=15)
    
    def generate_token(
        self,
        user_id: str,
        token_type: str = TokenType.ACCESS,
        additional_claims: Optional[Dict[str, Any]] = None,
        expires_in: Optional[timedelta] = None
    ) -> str:
        """Generate a new token"""
        token_id = self._generate_token_id()
        
        # Determine expiration
        if expires_in:
            expires_at = datetime.now(UTC) + expires_in
        else:
            expires_at = datetime.now(UTC) + self._get_default_lifetime(token_type)
        
        # Build payload
        payload = {
            "sub": user_id,  # Subject (user ID)
            "jti": token_id,  # JWT ID
            "typ": token_type,  # Token type
            "iat": int(datetime.now(UTC).timestamp()),  # Issued at
            "exp": int(expires_at.timestamp()),  # Expires at
        }
        
        if additional_claims:
            payload.update(additional_claims)
        
        # Create token object
        token = Token(token_id, token_type, user_id, payload, expires_at)
        self.tokens[token_id] = token
        
        # Track by user
        if user_id not in self.user_tokens:
            self.user_tokens[user_id] = []
        self.user_tokens[user_id].append(token_id)
        
        # Generate JWT
        jwt_token = self._encode_jwt(payload)
        
        logger.debug(f"Generated {token_type} token for user {user_id}")
        return jwt_token
    
    def validate_token(self, jwt_token: str) -> Dict[str, Any]:
        """Validate and decode a JWT token"""
        try:
            payload = self._decode_jwt(jwt_token)
            
            # Check if token exists in our store
            token_id = payload.get("jti")
            if not token_id or token_id not in self.tokens:
                raise TokenInvalidError("Token not found")
            
            token = self.tokens[token_id]
            
            # Check if token is revoked
            if token.is_revoked:
                raise TokenInvalidError("Token has been revoked")
            
            # Check expiration
            if datetime.now(UTC) >= token.expires_at:
                raise TokenExpiredError("Token has expired")
            
            # Update last used
            token.last_used = datetime.now(UTC)
            
            return payload
            
        except TokenError:
            raise
        except Exception as e:
            raise TokenInvalidError(f"Token validation failed: {str(e)}")
    
    def revoke_token(self, jwt_token: str) -> bool:
        """Revoke a specific token"""
        try:
            payload = self._decode_jwt(jwt_token)
            token_id = payload.get("jti")
            
            if token_id and token_id in self.tokens:
                self.tokens[token_id].is_revoked = True
                logger.info(f"Token {token_id} revoked")
                return True
            
            return False
        except Exception:
            return False
    
    def revoke_user_tokens(self, user_id: str, token_type: Optional[str] = None) -> int:
        """Revoke all tokens for a user"""
        revoked_count = 0
        
        if user_id in self.user_tokens:
            for token_id in self.user_tokens[user_id][:]:  # Copy list to avoid modification during iteration
                token = self.tokens.get(token_id)
                if token and not token.is_revoked:
                    if token_type is None or token.token_type == token_type:
                        token.is_revoked = True
                        revoked_count += 1
        
        logger.info(f"Revoked {revoked_count} tokens for user {user_id}")
        return revoked_count
    
    def refresh_token(self, refresh_jwt: str) -> str:
        """Generate new access token from refresh token"""
        payload = self.validate_token(refresh_jwt)
        
        if payload.get("typ") != TokenType.REFRESH:
            raise TokenInvalidError("Not a refresh token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise TokenInvalidError("Invalid token payload")
        
        # Generate new access token
        return self.generate_token(user_id, TokenType.ACCESS)
    
    def get_user_tokens(self, user_id: str, token_type: Optional[str] = None) -> List[Token]:
        """Get all tokens for a user"""
        tokens = []
        
        if user_id in self.user_tokens:
            for token_id in self.user_tokens[user_id]:
                token = self.tokens.get(token_id)
                if token and not token.is_revoked:
                    if token_type is None or token.token_type == token_type:
                        tokens.append(token)
        
        return tokens
    
    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens from storage"""
        current_time = datetime.now(UTC)
        expired_tokens = []
        
        for token_id, token in self.tokens.items():
            if current_time >= token.expires_at:
                expired_tokens.append(token_id)
        
        # Remove expired tokens
        for token_id in expired_tokens:
            token = self.tokens[token_id]
            del self.tokens[token_id]
            
            # Remove from user tokens
            if token.user_id in self.user_tokens:
                self.user_tokens[token.user_id] = [
                    tid for tid in self.user_tokens[token.user_id] if tid != token_id
                ]
        
        logger.info(f"Cleaned up {len(expired_tokens)} expired tokens")
        return len(expired_tokens)
    
    def get_token_info(self, jwt_token: str) -> Optional[Dict[str, Any]]:
        """Get token information without validation"""
        try:
            payload = self._decode_jwt(jwt_token, verify=False)
            token_id = payload.get("jti")
            
            if token_id and token_id in self.tokens:
                token = self.tokens[token_id]
                return {
                    "token_id": token.token_id,
                    "token_type": token.token_type,
                    "user_id": token.user_id,
                    "expires_at": token.expires_at.isoformat(),
                    "created_at": token.created_at.isoformat(),
                    "is_revoked": token.is_revoked,
                    "last_used": token.last_used.isoformat() if token.last_used else None
                }
            
            return None
        except Exception:
            return None
    
    def _generate_token_id(self) -> str:
        """Generate unique token ID"""
        timestamp = str(int(time.time() * 1000000))
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def _get_default_lifetime(self, token_type: str) -> timedelta:
        """Get default lifetime for token type"""
        lifetimes = {
            TokenType.ACCESS: self.access_token_lifetime,
            TokenType.REFRESH: self.refresh_token_lifetime,
            TokenType.API_KEY: self.api_key_lifetime,
            TokenType.TEMPORARY: self.temporary_token_lifetime
        }
        return lifetimes.get(token_type, self.access_token_lifetime)
    
    def _encode_jwt(self, payload: Dict[str, Any]) -> str:
        """Encode JWT token (simplified implementation)"""
        # Note: This is a simplified JWT implementation for testing
        # In production, use a proper JWT library like PyJWT
        
        header = {"typ": "JWT", "alg": self.algorithm}
        
        # Base64 encode header and payload
        import base64
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        
        # Create signature
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(self.secret_key, message.encode(), hashlib.sha256).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        
        return f"{header_b64}.{payload_b64}.{signature_b64}"
    
    def _decode_jwt(self, jwt_token: str, verify: bool = True) -> Dict[str, Any]:
        """Decode JWT token (simplified implementation)"""
        try:
            parts = jwt_token.split('.')
            if len(parts) != 3:
                raise TokenInvalidError("Invalid token format")
            
            header_b64, payload_b64, signature_b64 = parts
            
            if verify:
                # Verify signature
                message = f"{header_b64}.{payload_b64}"
                expected_signature = hmac.new(self.secret_key, message.encode(), hashlib.sha256).digest()
                
                import base64
                # Add padding if needed
                signature_b64_padded = signature_b64 + '=' * (4 - len(signature_b64) % 4)
                actual_signature = base64.urlsafe_b64decode(signature_b64_padded)
                
                if not hmac.compare_digest(expected_signature, actual_signature):
                    raise TokenInvalidError("Invalid token signature")
            
            # Decode payload
            import base64
            payload_b64_padded = payload_b64 + '=' * (4 - len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64_padded)
            payload = json.loads(payload_bytes.decode())
            
            return payload
            
        except json.JSONDecodeError:
            raise TokenInvalidError("Invalid token payload")
        except Exception as e:
            raise TokenInvalidError(f"Token decode failed: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get token manager statistics"""
        current_time = datetime.now(UTC)
        active_tokens = len([t for t in self.tokens.values() if not t.is_revoked and current_time < t.expires_at])
        expired_tokens = len([t for t in self.tokens.values() if current_time >= t.expires_at])
        revoked_tokens = len([t for t in self.tokens.values() if t.is_revoked])
        
        return {
            "total_tokens": len(self.tokens),
            "active_tokens": active_tokens,
            "expired_tokens": expired_tokens,
            "revoked_tokens": revoked_tokens,
            "users_with_tokens": len(self.user_tokens)
        }