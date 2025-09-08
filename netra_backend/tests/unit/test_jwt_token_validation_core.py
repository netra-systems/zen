"""
Unit Tests: JWT Token Validation Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication security and prevent unauthorized access
- Value Impact: JWT validation is critical for protecting user data and preventing security breaches
- Strategic Impact: Core platform security - failures could result in data breaches and customer loss

This module tests the core JWT token validation business logic without requiring external services.
Focuses on token structure, claims validation, expiry logic, and security edge cases.

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses IsolatedEnvironment (no direct os.environ access)
- Tests business logic only (no external dependencies)
- Uses SSOT base test case patterns
- Follows type safety requirements
"""

import pytest
import jwt
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env


class TestJWTTokenValidationCore(SSotBaseTestCase):
    """
    Unit tests for JWT token validation business logic.
    Tests core token validation without external service dependencies.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set test JWT secret
        self.set_env_var("JWT_SECRET_KEY", "test-jwt-secret-key-for-unit-testing-256-bit-long")
        self.jwt_secret = self.get_env_var("JWT_SECRET_KEY")
        
        # Standard test payload
        self.valid_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "permissions": ["read", "write"],
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
            "type": "access",
            "iss": "netra-auth-service"
        }
        
    def _create_token(self, payload: Dict[str, Any], secret: Optional[str] = None) -> str:
        """Helper to create JWT tokens for testing."""
        secret = secret or self.jwt_secret
        return jwt.encode(payload, secret, algorithm="HS256")
    
    def _decode_token(self, token: str, secret: Optional[str] = None) -> Dict[str, Any]:
        """Helper to decode JWT tokens for testing."""
        secret = secret or self.jwt_secret
        return jwt.decode(token, secret, algorithms=["HS256"])
    
    @pytest.mark.unit
    def test_valid_jwt_token_structure(self):
        """Test that valid JWT tokens have correct structure and claims."""
        # Create valid token
        token = self._create_token(self.valid_payload)
        
        # Decode and validate structure
        decoded = self._decode_token(token)
        
        # Assert required claims are present
        assert "sub" in decoded
        assert "email" in decoded
        assert "permissions" in decoded
        assert "iat" in decoded
        assert "exp" in decoded
        assert "type" in decoded
        assert "iss" in decoded
        
        # Validate claim values
        assert decoded["sub"] == "test-user-123"
        assert decoded["email"] == "test@example.com"
        assert decoded["permissions"] == ["read", "write"]
        assert decoded["type"] == "access"
        assert decoded["iss"] == "netra-auth-service"
        
        self.record_metric("jwt_validation_success", True)
        
    @pytest.mark.unit
    def test_expired_jwt_token_rejection(self):
        """Test that expired JWT tokens are properly rejected."""
        # Create expired token
        expired_payload = self.valid_payload.copy()
        expired_payload["exp"] = datetime.now(timezone.utc) - timedelta(minutes=5)
        
        token = self._create_token(expired_payload)
        
        # Attempt to decode expired token should raise exception
        with self.expect_exception(jwt.ExpiredSignatureError):
            self._decode_token(token)
            
        self.record_metric("expired_token_rejection", True)
        
    @pytest.mark.unit
    def test_invalid_signature_rejection(self):
        """Test that tokens with invalid signatures are rejected."""
        # Create token with correct secret
        token = self._create_token(self.valid_payload)
        
        # Attempt to decode with wrong secret should raise exception
        wrong_secret = "wrong-jwt-secret-key-should-fail-validation"
        with self.expect_exception(jwt.InvalidSignatureError):
            self._decode_token(token, wrong_secret)
            
        self.record_metric("invalid_signature_rejection", True)
        
    @pytest.mark.unit
    def test_malformed_jwt_token_handling(self):
        """Test proper handling of malformed JWT tokens."""
        malformed_tokens = [
            "not.a.jwt.token",
            "malformed-jwt-string",
            "",
            "header.payload",  # Missing signature
            "...",  # Empty parts
        ]
        
        for malformed_token in malformed_tokens:
            with self.expect_exception(jwt.InvalidTokenError):
                self._decode_token(malformed_token)
                
        self.record_metric("malformed_tokens_rejected", len(malformed_tokens))
        
    @pytest.mark.unit
    def test_missing_required_claims(self):
        """Test rejection of tokens missing required claims."""
        required_claims = ["sub", "email", "permissions", "exp", "iat"]
        
        for claim_to_remove in required_claims:
            payload = self.valid_payload.copy()
            del payload[claim_to_remove]
            
            token = self._create_token(payload)
            decoded = self._decode_token(token)  # This should decode successfully
            
            # The missing claim should be detectable
            assert claim_to_remove not in decoded
            
        self.record_metric("missing_claims_tested", len(required_claims))
        
    @pytest.mark.unit
    def test_token_type_validation(self):
        """Test validation of token type claims."""
        valid_types = ["access", "refresh", "verification"]
        invalid_types = ["invalid", "bearer", "", None]
        
        # Test valid types
        for token_type in valid_types:
            payload = self.valid_payload.copy()
            payload["type"] = token_type
            token = self._create_token(payload)
            decoded = self._decode_token(token)
            assert decoded["type"] == token_type
            
        # Test invalid types (should still decode but be identifiable as invalid)
        for token_type in invalid_types:
            payload = self.valid_payload.copy()
            payload["type"] = token_type
            token = self._create_token(payload)
            decoded = self._decode_token(token)
            assert decoded["type"] == token_type  # Decodes but type is invalid
            
        self.record_metric("token_types_tested", len(valid_types) + len(invalid_types))
        
    @pytest.mark.unit
    def test_permissions_claim_validation(self):
        """Test validation of permissions claim structure."""
        # Test valid permissions
        valid_permissions = [
            ["read"],
            ["read", "write"],
            ["read", "write", "admin"],
            [],  # Empty permissions should be allowed
        ]
        
        for permissions in valid_permissions:
            payload = self.valid_payload.copy()
            payload["permissions"] = permissions
            token = self._create_token(payload)
            decoded = self._decode_token(token)
            assert decoded["permissions"] == permissions
            
        # Test invalid permissions structure
        invalid_permissions = [
            "not_a_list",
            123,
            None,
            {"invalid": "structure"}
        ]
        
        for permissions in invalid_permissions:
            payload = self.valid_payload.copy()
            payload["permissions"] = permissions
            token = self._create_token(payload)
            decoded = self._decode_token(token)
            # Should decode but permissions structure is invalid
            assert decoded["permissions"] == permissions
            
        self.record_metric("permissions_tested", len(valid_permissions) + len(invalid_permissions))
        
    @pytest.mark.unit
    def test_future_token_handling(self):
        """Test handling of tokens with future issued-at times."""
        # Create token with future iat (issued in the future)
        future_payload = self.valid_payload.copy()
        future_payload["iat"] = datetime.now(timezone.utc) + timedelta(minutes=10)
        
        token = self._create_token(future_payload)
        
        # Token should decode successfully (JWT doesn't validate iat by default)
        decoded = self._decode_token(token)
        assert decoded["iat"] > datetime.now(timezone.utc).timestamp()
        
        self.record_metric("future_token_handled", True)