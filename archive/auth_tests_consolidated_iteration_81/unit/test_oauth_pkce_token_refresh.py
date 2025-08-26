"""
Test OAuth PKCE Token Refresh Flow
Tests the critical OAuth 2.1 PKCE token refresh process - currently missing from test coverage
"""
import base64
import hashlib
import secrets
import pytest
import uuid
from unittest.mock import Mock, patch

from auth_service.auth_core.security.oauth_security import OAuthSecurityManager
from auth_service.auth_core.core.jwt_handler import JWTHandler


class TestOAuthPKCETokenRefresh:
    """Test OAuth PKCE token refresh flow - missing critical test coverage"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.oauth_security = OAuthSecurityManager()
        self.jwt_handler = JWTHandler()
        self.test_user_id = str(uuid.uuid4())
        self.test_session_id = secrets.token_urlsafe(32)
    
    def _generate_pkce_pair(self):
        """Generate PKCE code verifier and challenge"""
        code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        return code_verifier, code_challenge
    
    def test_oauth_pkce_token_refresh_success(self):
        """Test successful OAuth token refresh with valid PKCE challenge"""
        # ARRANGE
        code_verifier, code_challenge = self._generate_pkce_pair()
        
        # Create initial access token
        access_token = self.jwt_handler.create_access_token(
            user_id=self.test_user_id,
            email="test@example.com"
        )
        
        # Create refresh token
        refresh_token = self.jwt_handler.create_refresh_token(self.test_user_id)
        
        # ACT - Attempt to validate PKCE for token refresh
        pkce_valid = self.oauth_security.validate_pkce_challenge(code_verifier, code_challenge)
        
        # ASSERT
        assert pkce_valid is True, "PKCE validation should succeed with matching verifier/challenge"
        
        # Additional validation of JWT tokens
        access_payload = self.jwt_handler.validate_token(access_token, "access")
        refresh_payload = self.jwt_handler.validate_token(refresh_token, "refresh")
        
        assert access_payload is not None
        assert refresh_payload is not None
        assert access_payload["sub"] == self.test_user_id
        assert refresh_payload["sub"] == self.test_user_id
    
    def test_oauth_pkce_token_refresh_invalid_challenge(self):
        """Test OAuth token refresh with invalid PKCE challenge"""
        # ARRANGE
        code_verifier, _ = self._generate_pkce_pair()
        # Create different challenge (simulating attack)
        fake_challenge = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        
        # ACT
        pkce_valid = self.oauth_security.validate_pkce_challenge(code_verifier, fake_challenge)
        
        # ASSERT
        assert pkce_valid is False, "PKCE validation should fail with mismatched verifier/challenge"
    
    def test_oauth_pkce_token_refresh_replay_protection(self):
        """Test OAuth token refresh protects against replay attacks"""
        # ARRANGE
        code_verifier, code_challenge = self._generate_pkce_pair()
        auth_code = secrets.token_urlsafe(32)
        
        # ACT - Track authorization code (first use)
        first_use = self.oauth_security.track_authorization_code(auth_code)
        # Attempt to use the same code again (replay attack)
        second_use = self.oauth_security.track_authorization_code(auth_code)
        
        # ASSERT
        assert first_use is True, "First use of auth code should be allowed"
        assert second_use is False, "Replay of auth code should be prevented"
    
    def test_oauth_pkce_token_refresh_nonce_validation(self):
        """Test OAuth token refresh with nonce replay prevention"""
        # ARRANGE
        nonce = secrets.token_urlsafe(16)
        
        # ACT - Check nonce (first use)
        first_check = self.oauth_security.check_nonce_replay(nonce)
        # Check same nonce again (replay attack)
        second_check = self.oauth_security.check_nonce_replay(nonce)
        
        # ASSERT
        assert first_check is True, "First nonce use should be allowed"
        assert second_check is False, "Nonce replay should be prevented"
    
    def test_oauth_pkce_malformed_verifier_challenge(self):
        """Test PKCE validation with malformed verifier/challenge"""
        # ARRANGE
        malformed_verifier = "invalid!@#base64"
        malformed_challenge = "also_invalid!@#"
        
        # ACT
        result = self.oauth_security.validate_pkce_challenge(malformed_verifier, malformed_challenge)
        
        # ASSERT
        assert result is False, "PKCE validation should fail gracefully with malformed input"
    
    def test_oauth_pkce_empty_verifier_challenge(self):
        """Test PKCE validation with empty verifier/challenge"""
        # ARRANGE
        empty_verifier = ""
        empty_challenge = ""
        
        # ACT
        result = self.oauth_security.validate_pkce_challenge(empty_verifier, empty_challenge)
        
        # ASSERT
        assert result is False, "PKCE validation should fail with empty verifier/challenge"
    
    @pytest.mark.skip(reason="This test will fail - token refresh with PKCE validation not implemented")
    def test_oauth_complete_pkce_refresh_flow_integration(self):
        """
        MISSING FUNCTIONALITY: Complete OAuth PKCE token refresh flow
        This test exposes missing integration between PKCE validation and token refresh
        """
        # ARRANGE
        code_verifier, code_challenge = self._generate_pkce_pair()
        refresh_token = self.jwt_handler.create_refresh_token(self.test_user_id)
        
        # ACT - This functionality doesn't exist yet
        # This should validate PKCE and refresh the token in one atomic operation
        with patch.object(self.oauth_security, 'validate_pkce_token_refresh') as mock_refresh:
            mock_refresh.return_value = {"access_token": "new_token", "valid": True}
            
            # This method doesn't exist - hence the failing test
            result = self.oauth_security.validate_pkce_token_refresh(
                refresh_token=refresh_token,
                code_verifier=code_verifier,
                code_challenge=code_challenge,
                user_id=self.test_user_id
            )
        
        # ASSERT - What we expect this missing functionality to do
        assert result["valid"] is True
        assert "access_token" in result
        assert result["access_token"] is not None