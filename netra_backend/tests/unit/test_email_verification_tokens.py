"""
Unit Tests: Email Verification Token Generation

Business Value Justification (BVJ):
- Segment: All (email verification critical for user onboarding)
- Business Goal: Ensure secure email verification and user activation
- Value Impact: Proper email verification enables user account activation
- Strategic Impact: User onboarding flow - failures prevent user conversion

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT base test case patterns
"""

import pytest
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestEmailVerificationTokens(SSotBaseTestCase):
    """Unit tests for email verification token generation and validation."""
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        self.set_env_var("EMAIL_TOKEN_LENGTH", "32")
        self.set_env_var("EMAIL_TOKEN_EXPIRY_HOURS", "24")
        
    def _generate_verification_token(self, user_id: str, email: str) -> Dict[str, Any]:
        """Generate email verification token."""
        token = secrets.token_urlsafe(int(self.get_env_var("EMAIL_TOKEN_LENGTH")))
        expiry_hours = int(self.get_env_var("EMAIL_TOKEN_EXPIRY_HOURS"))
        
        return {
            "token": token,
            "user_id": user_id,
            "email": email,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
            "is_used": False,
            "hash": hashlib.sha256(token.encode()).hexdigest()
        }
        
    def _validate_verification_token(self, token_data: Dict[str, Any], provided_token: str) -> bool:
        """Validate email verification token."""
        if token_data.get("is_used", True):
            return False
        if token_data.get("expires_at", datetime.min.replace(tzinfo=timezone.utc)) <= datetime.now(timezone.utc):
            return False
        return token_data.get("token") == provided_token
    
    @pytest.mark.unit
    def test_token_generation(self):
        """Test email verification token generation."""
        token_data = self._generate_verification_token("user123", "test@example.com")
        
        assert "token" in token_data
        assert "user_id" in token_data
        assert "email" in token_data
        assert "hash" in token_data
        assert len(token_data["token"]) >= 32
        assert token_data["user_id"] == "user123"
        assert token_data["email"] == "test@example.com"
        assert not token_data["is_used"]
        
        self.record_metric("token_generation_success", True)
        
    @pytest.mark.unit
    def test_token_validation(self):
        """Test email verification token validation."""
        token_data = self._generate_verification_token("user123", "test@example.com")
        
        # Valid token should pass
        assert self._validate_verification_token(token_data, token_data["token"])
        
        # Invalid token should fail
        assert not self._validate_verification_token(token_data, "wrong_token")
        
        # Used token should fail
        token_data["is_used"] = True
        assert not self._validate_verification_token(token_data, token_data["token"])
        
        self.record_metric("token_validation_tests", 3)
        
    @pytest.mark.unit
    def test_token_expiry(self):
        """Test email verification token expiry."""
        token_data = self._generate_verification_token("user123", "test@example.com")
        
        # Set token as expired
        token_data["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
        
        assert not self._validate_verification_token(token_data, token_data["token"])
        self.record_metric("token_expiry_test", True)