"""
Authentication Token Validation Tests - JWT token validation and security verification

Tests JWT token validation scenarios including signature verification, expiry checking,
token type validation, and security boundary enforcement in the auth service.

Business Value Justification (BVJ):
- Segment: Platform/Security | Goal: Auth Security | Impact: Core Security
- Ensures secure JWT token validation across all authentication flows
- Validates security boundaries and prevents unauthorized access
- Critical for maintaining authentication integrity in production

Test Coverage:
- Valid token validation across different token types
- Invalid token type rejection and security boundaries
- Token expiry validation and time-based security
- Signature verification and tampering detection
- Token structure validation and malformed token handling
"""

import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt

from auth_service.auth_core.core.jwt_handler import JWTHandler


class TestJWTTokenValidation(unittest.TestCase):
    """Test JWT token validation scenarios"""
    
    def setUp(self):
        """Setup test environment"""
        self.jwt_handler = JWTHandler()
        self.test_user_id = "test-user-456"
        self.test_email = "valid@example.com"
    
    def test_validate_valid_access_token(self):
        """Test validation of valid access token"""
        token = self.jwt_handler.create_access_token(
            self.test_user_id, 
            self.test_email
        )
        payload = self.jwt_handler.validate_token(token, "access")
        
        assert payload is not None
        assert payload["sub"] == self.test_user_id
        assert payload["email"] == self.test_email
        assert payload["token_type"] == "access"
    
    def test_validate_valid_refresh_token(self):
        """Test validation of valid refresh token"""
        token = self.jwt_handler.create_refresh_token(self.test_user_id)
        payload = self.jwt_handler.validate_token(token, "refresh")
        
        assert payload is not None
        assert payload["sub"] == self.test_user_id
        assert payload["token_type"] == "refresh"
    
    def test_validate_valid_service_token(self):
        """Test validation of valid service token"""
        service_id = "test-service"
        service_name = "test-service-name"
        
        token = self.jwt_handler.create_service_token(service_id, service_name)
        payload = self.jwt_handler.validate_token(token, "service")
        
        assert payload is not None
        assert payload["sub"] == service_id
        assert payload["service"] == service_name
        assert payload["token_type"] == "service"
    
    def test_validate_invalid_token_type(self):
        """Test validation with wrong token type"""
        refresh_token = self.jwt_handler.create_refresh_token(self.test_user_id)
        
        # Try to validate refresh token as access token
        payload = self.jwt_handler.validate_token(refresh_token, "access")
        assert payload is None
    
    def test_validate_expired_token(self):
        """Test validation of expired token"""
        # Create an expired token by manually creating JWT with past timestamps
        past_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        expired_payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "token_type": "access",  # Fixed: was "type", should be "token_type"
            "iat": int(past_time.timestamp()),
            "exp": int((past_time + timedelta(seconds=5)).timestamp()),  # Expired 5 seconds ago
            "iss": "netra-auth-service",
            "aud": "netra-platform",  # Required audience claim
            "jti": f"access_{int(time.time())}_expired",  # JWT ID for replay protection
            "env": "development",  # Required environment claim
            "svc_id": "netra-auth-dev-instance"  # Required service ID claim
        }
        
        # Manually create expired token using PyJWT
        expired_token = jwt.encode(expired_payload, self.jwt_handler._get_jwt_secret(), algorithm="HS256")
        
        # Validation should fail for expired token
        payload = self.jwt_handler.validate_token(expired_token, "access")
        assert payload is None
    
    def test_validate_malformed_token(self):
        """Test validation of malformed token"""
        malformed_tokens = [
            "not.a.token",
            "invalid-token-format",
            "too.few.parts",
            "too.many.parts.here.extra",
            "",
            None
        ]
        
        for malformed_token in malformed_tokens:
            if malformed_token is None:
                continue
            payload = self.jwt_handler.validate_token(malformed_token, "access")
            assert payload is None, f"Malformed token should be invalid: {malformed_token}"
    
    def test_validate_token_with_invalid_signature(self):
        """Test validation of token with invalid signature"""
        # Create valid token
        valid_token = self.jwt_handler.create_access_token(
            self.test_user_id,
            self.test_email
        )
        
        # Tamper with signature
        parts = valid_token.split('.')
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        # Validation should fail
        payload = self.jwt_handler.validate_token(tampered_token, "access")
        assert payload is None
    
    def test_validate_token_without_required_claims(self):
        """Test validation of token missing required claims"""
        # Create token with minimal payload (missing required claims)
        minimal_payload = {
            "sub": self.test_user_id,
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp())
            # Missing token_type, iss, etc.
        }
        
        # Get JWT secret for token creation
        secret = os.environ.get("JWT_SECRET_KEY", "test-secret")
        minimal_token = jwt.encode(minimal_payload, secret, algorithm="HS256")
        
        # Validation should fail due to missing required claims
        payload = self.jwt_handler.validate_token(minimal_token, "access")
        assert payload is None
    
    def test_validate_token_with_wrong_issuer(self):
        """Test validation of token with wrong issuer"""
        # Create token with wrong issuer
        wrong_issuer_payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "token_type": "access",
            "iss": "wrong-issuer",  # Should be "netra-auth-service"
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "aud": "netra-platform",  # Required audience claim
            "jti": f"access_{int(time.time())}_wrong_issuer",  # JWT ID for replay protection
            "env": "development",  # Required environment claim
            "svc_id": "netra-auth-dev-instance"  # Required service ID claim
        }
        
        # Get JWT secret for token creation
        secret = os.environ.get("JWT_SECRET_KEY", "test-secret")
        wrong_issuer_token = jwt.encode(wrong_issuer_payload, secret, algorithm="HS256")
        
        # Validation should fail due to wrong issuer
        payload = self.jwt_handler.validate_token(wrong_issuer_token, "access")
        assert payload is None
    
    def test_validate_token_performance(self):
        """Test token validation performance"""
        # Create valid token
        token = self.jwt_handler.create_access_token(
            self.test_user_id,
            self.test_email
        )
        
        # Measure validation performance
        start_time = time.time()
        
        # Perform multiple validations
        validation_count = 100
        successful_validations = 0
        
        for _ in range(validation_count):
            payload = self.jwt_handler.validate_token(token, "access")
            if payload is not None:
                successful_validations += 1
        
        validation_time = time.time() - start_time
        
        # All validations should succeed
        assert successful_validations == validation_count
        
        # Validation should be fast
        avg_validation_time = validation_time / validation_count
        assert avg_validation_time < 0.01, f"Average validation time: {avg_validation_time:.4f}s"
        assert validation_time < 1.0, f"Total validation time: {validation_time:.3f}s"
    
    def test_validate_token_type_boundaries(self):
        """Test validation enforces token type boundaries"""
        # Create different token types
        access_token = self.jwt_handler.create_access_token(self.test_user_id, self.test_email)
        refresh_token = self.jwt_handler.create_refresh_token(self.test_user_id)
        service_token = self.jwt_handler.create_service_token("test-service", "test")
        
        # Test access token boundaries
        assert self.jwt_handler.validate_token(access_token, "access") is not None
        assert self.jwt_handler.validate_token(access_token, "refresh") is None
        assert self.jwt_handler.validate_token(access_token, "service") is None
        
        # Test refresh token boundaries
        assert self.jwt_handler.validate_token(refresh_token, "refresh") is not None
        assert self.jwt_handler.validate_token(refresh_token, "access") is None
        assert self.jwt_handler.validate_token(refresh_token, "service") is None
        
        # Test service token boundaries
        assert self.jwt_handler.validate_token(service_token, "service") is not None
        assert self.jwt_handler.validate_token(service_token, "access") is None
        assert self.jwt_handler.validate_token(service_token, "refresh") is None
    
    def test_validate_token_with_future_issued_time(self):
        """Test validation of token with issued time in the future"""
        # Create token with future issued time
        future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        future_payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "token_type": "access",
            "iss": "netra-auth-service",
            "iat": int(future_time.timestamp()),
            "exp": int((future_time + timedelta(minutes=15)).timestamp()),
            "aud": "netra-platform",  # Required audience claim
            "jti": f"access_{int(time.time())}_future",  # JWT ID for replay protection
            "env": "development",  # Required environment claim
            "svc_id": "netra-auth-dev-instance"  # Required service ID claim
        }
        
        # Get JWT secret for token creation
        secret = os.environ.get("JWT_SECRET_KEY", "test-secret")
        future_token = jwt.encode(future_payload, secret, algorithm="HS256")
        
        # Validation should fail for future-issued token
        payload = self.jwt_handler.validate_token(future_token, "access")
        assert payload is None
    
    def test_validate_token_edge_case_timing(self):
        """Test validation edge cases around timing"""
        # Create a token that expires very soon by directly encoding with JWT
        import jwt
        near_expiry_time = datetime.now(timezone.utc) + timedelta(seconds=1)
        
        # Create payload manually with short expiry - include all required claims
        payload = {
            "sub": self.test_user_id,
            "email": self.test_email,
            "token_type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int(near_expiry_time.timestamp()),
            "jti": f"access_{int(time.time())}",
            "iss": "netra-auth-service",
            "aud": "netra-platform",        # Required audience claim for access tokens
            "env": "development",         # Required environment claim (matches AuthConfig default)
            "svc_id": "netra-auth-dev-instance"  # Required service ID claim (matches AuthConfig default)
        }
        
        # Encode token with short expiry
        secret = self.jwt_handler.secret
        token = jwt.encode(payload, secret, algorithm=self.jwt_handler.algorithm)
        
        # Should be valid immediately
        validation_payload = self.jwt_handler.validate_token(token, "access")
        assert validation_payload is not None
        
        # Wait for expiry and test again
        time.sleep(2)
        validation_payload = self.jwt_handler.validate_token(token, "access")
        assert validation_payload is None
    
    def test_validate_token_concurrent_validation(self):
        """Test concurrent token validation for race conditions"""
        import queue
        import threading
        
        # Create valid token
        token = self.jwt_handler.create_access_token(self.test_user_id, self.test_email)
        
        # Setup concurrent validation
        results = queue.Queue()
        thread_count = 10
        validations_per_thread = 10
        
        def validate_tokens():
            thread_results = []
            for _ in range(validations_per_thread):
                payload = self.jwt_handler.validate_token(token, "access")
                thread_results.append(payload is not None)
            results.put(thread_results)
        
        # Start concurrent validation threads
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=validate_tokens)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Collect results
        all_results = []
        while not results.empty():
            thread_results = results.get()
            all_results.extend(thread_results)
        
        # All validations should succeed
        successful_validations = sum(all_results)
        total_validations = thread_count * validations_per_thread
        
        assert successful_validations == total_validations, \
            f"Concurrent validation failed: {successful_validations}/{total_validations}"


# Business Impact Summary for Token Validation Tests
"""
Authentication Token Validation Tests - Business Impact

Security Foundation: Authentication Integrity Protection
- Ensures secure JWT token validation across all authentication flows
- Validates security boundaries and prevents unauthorized access
- Critical for maintaining authentication integrity in production

Technical Excellence:
- Token validation: comprehensive validation for access, refresh, and service tokens
- Security boundaries: proper token type enforcement and access control
- Signature verification: tampered token detection and integrity protection
- Expiry validation: time-based security and token lifecycle management
- Performance validation: fast token validation (<10ms average) for responsive auth
- Concurrent validation: thread-safe validation for production scalability

Platform Security:
- Platform: Secure token validation foundation for all authentication flows
- Security: Comprehensive validation prevents security vulnerabilities and attacks
- Performance: Fast validation ensures responsive authentication experience
- Boundaries: Token type enforcement prevents privilege escalation
- Integrity: Signature and timing validation maintains authentication trust
"""