"""
OAuth PKCE (Proof Key for Code Exchange) Validation Tests
Tests for RFC 7636 compliance and security vulnerabilities

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Security, Compliance, OAuth Standards
- Value Impact: Prevents authorization code interception attacks
- Strategic Impact: Critical for OAuth security compliance and user trust

PKCE Security Coverage:
- Valid PKCE challenge validation
- Invalid challenge rejection
- Timing attack resistance
- Malformed input handling
- Edge case security validation
"""
import base64
import hashlib
import secrets
import pytest
from unittest.mock import patch, Mock

from auth_service.auth_core.security.oauth_security import OAuthSecurityManager


class TestOAuthPKCEValidation:
    """Test OAuth PKCE validation according to RFC 7636"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.security_manager = OAuthSecurityManager()
    
    def test_valid_pkce_challenge_validation(self):
        """Test valid PKCE code challenge validation passes"""
        # Generate valid code verifier and challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        
        # Should pass validation
        result = self.security_manager.validate_pkce_challenge(code_verifier, code_challenge)
        assert result is True
    
    def test_invalid_pkce_challenge_validation_fails(self):
        """Test invalid PKCE code challenge validation fails - THIS SHOULD FAIL INITIALLY"""
        # Generate valid code verifier but use wrong challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        wrong_challenge = "invalid_challenge_value"
        
        # Should fail validation
        result = self.security_manager.validate_pkce_challenge(code_verifier, wrong_challenge)
        
        # DELIBERATELY FAILING ASSERTION TO EXPOSE MISSING EDGE CASE HANDLING
        # The current implementation might not properly handle malformed challenges
        assert result is False, "PKCE validation should fail for malformed challenges"
        
        # Additional check: ensure error logging occurred
        with patch('auth_service.auth_core.security.oauth_security.logger') as mock_logger:
            self.security_manager.validate_pkce_challenge(code_verifier, wrong_challenge)
            mock_logger.warning.assert_called_with("PKCE challenge validation failed")
    
    def test_pkce_challenge_timing_attack_resistance(self):
        """Test PKCE validation is resistant to timing attacks"""
        # Generate valid code verifier and challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        
        # Test that timing is consistent for valid and invalid challenges
        import time
        
        # Time valid validation
        start_time = time.time()
        self.security_manager.validate_pkce_challenge(code_verifier, code_challenge)
        valid_time = time.time() - start_time
        
        # Time invalid validation
        start_time = time.time()
        self.security_manager.validate_pkce_challenge(code_verifier, "invalid_challenge")
        invalid_time = time.time() - start_time
        
        # Times should be similar (within reasonable margin)
        time_difference = abs(valid_time - invalid_time)
        assert time_difference < 0.001, f"Timing difference too large: {time_difference}s"
    
    def test_pkce_challenge_malformed_base64_handling(self):
        """Test PKCE validation handles malformed base64 gracefully - EXPECTED TO FAIL"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        
        # Test various malformed challenges
        malformed_challenges = [
            "not_base64!@#$",  # Invalid base64 characters
            "",                # Empty string
            "a",               # Too short
            "invalid==base64", # Invalid padding
        ]
        
        for malformed_challenge in malformed_challenges:
            result = self.security_manager.validate_pkce_challenge(code_verifier, malformed_challenge)
            # THIS ASSERTION WILL FAIL if the implementation doesn't properly handle edge cases
            assert result is False, f"Should reject malformed challenge: {malformed_challenge}"
    
    def test_pkce_challenge_length_requirements(self):
        """Test PKCE validation enforces proper length requirements"""
        # Generate valid code verifier
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        
        # Test with too short challenge (less than minimum required)
        short_challenge = "abc"  # Way too short
        result = self.security_manager.validate_pkce_challenge(code_verifier, short_challenge)
        
        # EXPECTED TO FAIL - current implementation might not check length requirements
        assert result is False, "Should reject challenges that are too short"
    
    def test_pkce_challenge_unicode_handling(self):
        """Test PKCE validation properly handles unicode input - EXPECTED TO FAIL"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        
        # Test with unicode characters in challenge
        unicode_challenge = "chällenge_with_ünïcode"
        
        # This should fail gracefully, not crash
        try:
            result = self.security_manager.validate_pkce_challenge(code_verifier, unicode_challenge)
            # Should return False for invalid challenge
            assert result is False, "Should reject unicode challenges"
        except UnicodeEncodeError:
            # THIS WILL FAIL if implementation doesn't handle unicode properly
            pytest.fail("PKCE validation should handle unicode input gracefully, not crash")
    
    def test_pkce_code_verifier_null_handling(self):
        """Test PKCE validation handles null/None input gracefully - EXPECTED TO FAIL"""
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256("test".encode()).digest()
        ).decode().rstrip("=")
        
        # Test with None/null code verifier
        result = self.security_manager.validate_pkce_challenge(None, code_challenge)
        
        # THIS WILL FAIL if implementation doesn't handle None input
        assert result is False, "Should reject None code verifier"
        
        # Test with empty string code verifier
        result = self.security_manager.validate_pkce_challenge("", code_challenge)
        assert result is False, "Should reject empty code verifier"
    
    def test_pkce_challenge_case_sensitivity(self):
        """Test PKCE validation is case sensitive"""
        # Generate valid code verifier and challenge
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        
        # Test with uppercase challenge
        uppercase_challenge = code_challenge.upper()
        result = self.security_manager.validate_pkce_challenge(code_verifier, uppercase_challenge)
        
        # Should fail because PKCE is case sensitive
        assert result is False, "PKCE validation should be case sensitive"
    
    def test_pkce_sql_injection_prevention(self):
        """Test PKCE validation prevents SQL injection attempts"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        
        # SQL injection attempt in challenge
        sql_injection_challenge = "'; DROP TABLE users; --"
        
        result = self.security_manager.validate_pkce_challenge(code_verifier, sql_injection_challenge)
        
        # Should reject malicious input
        assert result is False, "Should reject SQL injection attempts"
    
    def test_pkce_validation_exception_handling(self):
        """Test PKCE validation handles exceptions properly"""
        # Mock hashlib.sha256 to raise an exception
        with patch('auth_service.auth_core.security.oauth_security.hashlib.sha256') as mock_sha256:
            mock_sha256.side_effect = Exception("Mocked exception")
            
            result = self.security_manager.validate_pkce_challenge("test_verifier", "test_challenge")
            
            # Should return False on exception, not crash
            assert result is False, "Should handle exceptions gracefully"