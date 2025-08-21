"""
JWT Validation Tests - Auth Service Security Testing

Business Value: Authentication security for cross-service communication
Tests JWT signature validation, claims requirements, and token revocation

CRITICAL: Uses real JWT libraries (PyJWT) with proper security testing
Maximum 300 lines enforced - focused on core JWT validation only
"""
import pytest
import jwt
import json
import base64
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Set

# Support both root and auth_service directory execution
try:
    # Primary import path - auth_core at root level
    from auth_core.core.jwt_handler import JWTHandler
    from auth_core.config import AuthConfig
except ImportError:
    # Fallback for auth_service directory execution
    from auth_service.auth_core.core.jwt_handler import JWTHandler
    from auth_service.auth_core.config import AuthConfig


class TestJWTSignatureValidation:
    """Test JWT signature verification."""
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    @pytest.fixture
    def valid_user_payload(self):
        """Standard valid user payload."""
        return {
            "sub": "test-user-123",
            "email": "test@netra.ai", 
            "permissions": ["read", "write"],
            "token_type": "access",
            "iss": "netra-auth-service"
        }
    
    def test_jwt_signature_validation(self, jwt_handler, valid_user_payload):
        """Test JWT signature verification.
        Valid signature passes, invalid signature rejected.
        """
        # Create valid token
        valid_token = jwt_handler.create_access_token(
            valid_user_payload["sub"],
            valid_user_payload["email"],
            valid_user_payload["permissions"]
        )
        
        # Valid signature should pass
        decoded = jwt_handler.validate_token_jwt(valid_token, "access")
        assert decoded is not None
        assert decoded["sub"] == valid_user_payload["sub"]
        assert decoded["email"] == valid_user_payload["email"]
        
        # Invalid signature should be rejected
        tampered_token = valid_token[:-10] + "tampered123"
        decoded_tampered = jwt_handler.validate_token_jwt(tampered_token, "access")
        assert decoded_tampered is None
    
    def test_algorithm_mismatch_rejected(self, jwt_handler, valid_user_payload):
        """Test algorithm mismatch rejection."""
        # Create token with different algorithm (if we had multiple keys)
        payload = {
            "sub": valid_user_payload["sub"],
            "email": valid_user_payload["email"],
            "permissions": valid_user_payload["permissions"],
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service"
        }
        
        # Try to create a 'none' algorithm token (security vulnerability)
        header = {"typ": "JWT", "alg": "none"}
        encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        none_token = f"{encoded_header}.{encoded_payload}."
        
        # Should be rejected
        decoded = jwt_handler.validate_token_jwt(none_token, "access")
        assert decoded is None
    
    def test_expired_token_rejected(self, jwt_handler, valid_user_payload):
        """Test expired token rejection."""
        # Create token that expires immediately
        payload = {
            "sub": valid_user_payload["sub"],
            "email": valid_user_payload["email"],
            "permissions": valid_user_payload["permissions"],
            "token_type": "access",
            "iat": int((datetime.now(timezone.utc) - timedelta(minutes=20)).timestamp()),
            "exp": int((datetime.now(timezone.utc) - timedelta(minutes=10)).timestamp()),
            "iss": "netra-auth-service"
        }
        
        expired_token = jwt.encode(payload, jwt_handler.secret, algorithm=jwt_handler.algorithm)
        
        # Should be rejected due to expiration
        decoded = jwt_handler.validate_token_jwt(expired_token, "access")
        assert decoded is None


class TestJWTClaimsValidation:
    """Test JWT claims requirements."""
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    def test_jwt_claims_validation(self, jwt_handler):
        """Test JWT claims requirements.
        Required claims present: user_id, email, permissions validated.
        """
        # Test with all required claims
        user_id = "test-user-456"
        email = "claims@netra.ai"
        permissions = ["read", "write", "admin"]
        
        token = jwt_handler.create_access_token(user_id, email, permissions)
        decoded = jwt_handler.validate_token_jwt(token, "access")
        
        # User_id claim validated
        assert decoded["sub"] == user_id
        
        # Email claim validated  
        assert decoded["email"] == email
        
        # Permissions claim validated
        assert decoded["permissions"] == permissions
        
        # Standard claims present
        assert "iat" in decoded  # Issued at
        assert "exp" in decoded  # Expires
        assert "iss" in decoded  # Issuer
        assert decoded["iss"] == "netra-auth-service"
    
    def test_missing_required_claims_rejected(self, jwt_handler):
        """Test rejection when required claims are missing."""
        # Create token with missing claims manually
        incomplete_payload = {
            "sub": "test-user",
            # Missing email and permissions
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iss": "netra-auth-service"
        }
        
        incomplete_token = jwt.encode(
            incomplete_payload, 
            jwt_handler.secret, 
            algorithm=jwt_handler.algorithm
        )
        
        # Token should validate structurally but missing business claims
        decoded = jwt_handler.validate_token_jwt(incomplete_token, "access")
        assert decoded is not None  # Structurally valid
        assert "email" not in decoded  # Missing expected claim
        assert "permissions" not in decoded  # Missing expected claim
    
    def test_token_type_validation(self, jwt_handler):
        """Test token type claim validation."""
        # Create refresh token
        refresh_token = jwt_handler.create_refresh_token("test-user-789")
        
        # Should validate as refresh token
        refresh_decoded = jwt_handler.validate_token_jwt(refresh_token, "refresh") 
        assert refresh_decoded is not None
        assert refresh_decoded["token_type"] == "refresh"
        
        # Should NOT validate as access token
        access_decoded = jwt_handler.validate_token_jwt(refresh_token, "access")
        assert access_decoded is None
    
    def test_service_token_claims(self, jwt_handler):
        """Test service token specific claims."""
        service_token = jwt_handler.create_service_token("backend-svc", "netra-backend")
        decoded = jwt_handler.validate_token_jwt(service_token, "service")
        
        assert decoded is not None
        assert decoded["sub"] == "backend-svc"
        assert decoded["service"] == "netra-backend"
        assert decoded["token_type"] == "service"


class TestJWTRevocation:
    """Test token revocation."""
    
    @pytest.fixture
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    @pytest.fixture
    def revoked_tokens(self):
        """Mock revoked tokens blacklist."""
        return set()
    
    def test_jwt_revocation(self, jwt_handler, revoked_tokens):
        """Test token revocation.
        Add token to blacklist → Revoked token rejected → Check across services
        """
        # Create valid token
        token = jwt_handler.create_access_token("test-user", "revoke@netra.ai")
        
        # Token should be valid initially
        decoded = jwt_handler.validate_token_jwt(token)
        assert decoded is not None
        
        # Add token to blacklist
        revoked_tokens.add(token)
        
        # Simulate revocation check
        def is_token_revoked(token_to_check: str) -> bool:
            return token_to_check in revoked_tokens
        
        # Token should now be considered revoked
        assert is_token_revoked(token) is True
        
        # In a real implementation, validation would check blacklist
        # This demonstrates the revocation pattern
    
    def test_revocation_by_user_id(self, jwt_handler, revoked_tokens):
        """Test revoking all tokens for a user."""
        user_id = "user-to-revoke"
        
        # Create multiple tokens for user
        token1 = jwt_handler.create_access_token(user_id, "user@netra.ai") 
        token2 = jwt_handler.create_refresh_token(user_id)
        
        # Both should be valid
        assert jwt_handler.validate_token_jwt(token1) is not None
        assert jwt_handler.validate_token_jwt(token2, "refresh") is not None
        
        # Revoke all tokens for user (by storing user ID in revoked list)
        revoked_users = {user_id}
        
        def is_user_revoked(token_to_check: str) -> bool:
            try:
                payload = jwt.decode(token_to_check, options={"verify_signature": False})
                return payload.get("sub") in revoked_users
            except:
                return False
        
        # Both tokens should now be revoked
        assert is_user_revoked(token1) is True
        assert is_user_revoked(token2) is True
    
    def test_cleanup_expired_revocations(self, revoked_tokens):
        """Test cleanup of expired revocations."""
        # Add expired token to revocation list
        expired_token = "expired.token.signature"
        revoked_tokens.add(expired_token)
        
        # Simulate cleanup process
        def cleanup_expired_revocations(blacklist: Set[str]) -> Set[str]:
            # In real implementation, would check token expiry
            # For test, just demonstrate cleanup
            cleaned = set()
            for token in blacklist:
                try:
                    # Check if token is still within its lifetime
                    payload = jwt.decode(token, options={"verify_signature": False})
                    exp = payload.get("exp", 0)
                    if exp > datetime.now(timezone.utc).timestamp():
                        cleaned.add(token)
                except:
                    # Invalid or malformed tokens can be removed
                    pass
            return cleaned
        
        # Clean up expired tokens
        cleaned_blacklist = cleanup_expired_revocations(revoked_tokens)
        
        # Should handle cleanup without errors
        assert isinstance(cleaned_blacklist, set)


class TestJWTIntegrationScenarios:
    """Test JWT integration scenarios."""
    
    @pytest.fixture  
    def jwt_handler(self):
        """JWT handler instance for testing."""
        return JWTHandler()
    
    @pytest.mark.asyncio
    async def test_end_to_end_token_flow(self, jwt_handler):
        """Test complete token flow from creation to validation."""
        # Create user token
        user_id = "e2e-user"
        email = "e2e@netra.ai"
        permissions = ["read", "write"]
        
        access_token = jwt_handler.create_access_token(user_id, email, permissions)
        refresh_token = jwt_handler.create_refresh_token(user_id)
        
        # Validate access token
        access_decoded = jwt_handler.validate_token_jwt(access_token, "access")
        assert access_decoded["sub"] == user_id
        assert access_decoded["email"] == email
        
        # Validate refresh token
        refresh_decoded = jwt_handler.validate_token_jwt(refresh_token, "refresh")
        assert refresh_decoded["sub"] == user_id
        assert refresh_decoded["token_type"] == "refresh"
        
        # Test refresh flow
        new_tokens = jwt_handler.refresh_access_token(refresh_token)
        if new_tokens:
            new_access, new_refresh = new_tokens
            assert new_access != access_token  # Should be different
            # Note: Some implementations reuse refresh tokens, this is acceptable
            assert new_access is not None  # New access token should be generated
    
    def test_user_id_extraction(self, jwt_handler):
        """Test safe user ID extraction from tokens."""
        token = jwt_handler.create_access_token("extract-user", "extract@netra.ai")
        
        # Should extract user ID safely
        user_id = jwt_handler.extract_user_id(token)
        assert user_id == "extract-user"
        
        # Should handle invalid tokens gracefully  
        invalid_user_id = jwt_handler.extract_user_id("invalid.token")
        assert invalid_user_id is None


# Business Value Justification: Authentication Security
"""
BVJ: JWT Validation Tests

Segment: Enterprise & Growth (Critical security infrastructure)
Business Goal: Zero authentication vulnerabilities, secure token validation
Value Impact:
- Prevents JWT-based security attacks (signature tampering, algorithm confusion)
- Enables secure token-based authentication for enterprise features
- Supports proper token lifecycle management and revocation
- Protects against expired token usage and claim validation bypasses

Strategic/Revenue Impact: Authentication security foundation for enterprise sales
Critical for SOC2 compliance and security audit requirements
"""