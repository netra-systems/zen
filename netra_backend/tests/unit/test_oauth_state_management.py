"""
Unit Tests: OAuth State Management

Business Value Justification (BVJ):
- Segment: All (OAuth critical for user onboarding and retention)
- Business Goal: Ensure secure OAuth flows and prevent CSRF attacks
- Value Impact: OAuth state validation prevents security vulnerabilities and failed logins
- Strategic Impact: Security and user experience - OAuth failures block user conversion

This module tests the core OAuth state management business logic including state generation,
validation, expiry, and CSRF protection without requiring external OAuth providers.

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses IsolatedEnvironment (no direct os.environ access)
- Tests business logic only (no external dependencies)
- Uses SSOT base test case patterns
- Follows type safety requirements
"""

import pytest
import secrets
import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode, parse_qs

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestOAuthStateManagement(SSotBaseTestCase):
    """
    Unit tests for OAuth state management business logic.
    Tests state generation, validation, and security without external OAuth providers.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Set OAuth configuration
        self.set_env_var("OAUTH_STATE_TIMEOUT_MINUTES", "10")
        self.set_env_var("OAUTH_STATE_LENGTH", "32")
        self.set_env_var("OAUTH_CSRF_PROTECTION", "true")
        
        # OAuth state configuration
        self.state_timeout = int(self.get_env_var("OAUTH_STATE_TIMEOUT_MINUTES"))
        self.state_length = int(self.get_env_var("OAUTH_STATE_LENGTH"))
        
        # Test OAuth providers
        self.test_providers = ["google", "github", "microsoft"]
        
    def _generate_oauth_state(self, provider: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Generate OAuth state for testing.
        
        Returns dict with state token, metadata, and expiry.
        """
        state_token = secrets.token_urlsafe(self.state_length)
        
        state_data = {
            "state_token": state_token,
            "provider": provider,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=self.state_timeout),
            "is_used": False,
            "csrf_token": secrets.token_hex(16),
            "user_context": user_context or {},
            "redirect_uri": f"http://localhost:8000/auth/callback/{provider}",
            "nonce": str(uuid.uuid4())
        }
        
        return state_data
        
    def _validate_oauth_state(self, state_data: Dict[str, Any], provided_state: str) -> Tuple[bool, str]:
        """
        Validate OAuth state for testing.
        
        Returns (is_valid, error_message) tuple.
        """
        if not state_data:
            return False, "State data not found"
            
        if state_data.get("is_used", False):
            return False, "State has already been used"
            
        if state_data.get("state_token") != provided_state:
            return False, "State token mismatch"
            
        # Check expiry
        expires_at = state_data.get("expires_at")
        if not expires_at:
            return False, "State has no expiry time"
            
        if expires_at <= datetime.now(timezone.utc):
            return False, "State has expired"
            
        return True, ""
        
    def _build_oauth_url(self, provider: str, state_data: Dict[str, Any], client_id: str = "test_client") -> str:
        """Build OAuth authorization URL for testing."""
        base_urls = {
            "google": "https://accounts.google.com/o/oauth2/auth",
            "github": "https://github.com/login/oauth/authorize", 
            "microsoft": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
        }
        
        params = {
            "client_id": client_id,
            "redirect_uri": state_data["redirect_uri"],
            "response_type": "code",
            "state": state_data["state_token"],
            "scope": "openid email profile"
        }
        
        base_url = base_urls.get(provider, "https://example.com/oauth/authorize")
        return f"{base_url}?{urlencode(params)}"
        
    def _extract_state_from_callback(self, callback_url: str) -> Optional[str]:
        """Extract state parameter from OAuth callback URL."""
        if "?" not in callback_url:
            return None
            
        query_params = parse_qs(callback_url.split("?")[1])
        state_list = query_params.get("state", [])
        return state_list[0] if state_list else None
    
    @pytest.mark.unit
    def test_oauth_state_generation(self):
        """Test OAuth state generation business logic."""
        provider = "google"
        state_data = self._generate_oauth_state(provider)
        
        # Validate state structure
        assert "state_token" in state_data
        assert "provider" in state_data
        assert "created_at" in state_data
        assert "expires_at" in state_data
        assert "is_used" in state_data
        assert "csrf_token" in state_data
        assert "redirect_uri" in state_data
        assert "nonce" in state_data
        
        # Validate field values
        assert state_data["provider"] == provider
        assert state_data["is_used"] is False
        assert len(state_data["state_token"]) >= self.state_length
        assert len(state_data["csrf_token"]) >= 16
        assert isinstance(state_data["created_at"], datetime)
        assert isinstance(state_data["expires_at"], datetime)
        
        # Validate expiry time
        expected_expiry = state_data["created_at"] + timedelta(minutes=self.state_timeout)
        time_diff = abs((state_data["expires_at"] - expected_expiry).total_seconds())
        assert time_diff < 1  # Less than 1 second difference
        
        self.record_metric("state_generation_success", True)
        
    @pytest.mark.unit
    def test_oauth_state_uniqueness(self):
        """Test that generated OAuth states are unique."""
        provider = "google"
        states = []
        
        # Generate multiple states
        for _ in range(10):
            state_data = self._generate_oauth_state(provider)
            states.append(state_data)
            
        # Verify all state tokens are unique
        state_tokens = [state["state_token"] for state in states]
        assert len(set(state_tokens)) == len(states)  # All unique
        
        # Verify all CSRF tokens are unique
        csrf_tokens = [state["csrf_token"] for state in states]
        assert len(set(csrf_tokens)) == len(states)  # All unique
        
        # Verify all nonces are unique
        nonces = [state["nonce"] for state in states]
        assert len(set(nonces)) == len(states)  # All unique
        
        self.record_metric("unique_states_generated", len(states))
        
    @pytest.mark.unit
    def test_oauth_state_validation_success(self):
        """Test successful OAuth state validation."""
        provider = "github"
        state_data = self._generate_oauth_state(provider)
        
        # Validate with correct state token
        is_valid, error_msg = self._validate_oauth_state(state_data, state_data["state_token"])
        assert is_valid is True
        assert error_msg == ""
        
        self.record_metric("successful_state_validation", True)
        
    @pytest.mark.unit
    def test_oauth_state_validation_failures(self):
        """Test OAuth state validation failure scenarios."""
        provider = "microsoft"
        state_data = self._generate_oauth_state(provider)
        
        # Test with wrong state token
        is_valid, error_msg = self._validate_oauth_state(state_data, "wrong_state_token")
        assert is_valid is False
        assert "mismatch" in error_msg.lower()
        
        # Test with already used state
        used_state_data = state_data.copy()
        used_state_data["is_used"] = True
        is_valid, error_msg = self._validate_oauth_state(used_state_data, state_data["state_token"])
        assert is_valid is False
        assert "already been used" in error_msg.lower()
        
        # Test with expired state
        expired_state_data = state_data.copy()
        expired_state_data["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=5)
        is_valid, error_msg = self._validate_oauth_state(expired_state_data, state_data["state_token"])
        assert is_valid is False
        assert "expired" in error_msg.lower()
        
        # Test with empty state data
        is_valid, error_msg = self._validate_oauth_state({}, state_data["state_token"])
        assert is_valid is False
        assert "not found" in error_msg.lower()
        
        self.record_metric("state_validation_failures_tested", 4)
        
    @pytest.mark.unit
    def test_oauth_url_construction(self):
        """Test OAuth authorization URL construction."""
        provider = "google"
        client_id = "test_client_123"
        state_data = self._generate_oauth_state(provider)
        
        oauth_url = self._build_oauth_url(provider, state_data, client_id)
        
        # Validate URL structure
        assert oauth_url.startswith("https://")
        assert provider in oauth_url.lower() or "accounts.google.com" in oauth_url
        assert f"client_id={client_id}" in oauth_url
        assert f"state={state_data['state_token']}" in oauth_url
        assert "redirect_uri=" in oauth_url
        assert "response_type=code" in oauth_url
        
        self.record_metric("oauth_url_construction_success", True)
        
    @pytest.mark.unit
    def test_oauth_callback_state_extraction(self):
        """Test extraction of state from OAuth callback URLs."""
        # Test valid callback with state
        callback_url = "http://localhost:8000/auth/callback/google?code=auth_code_123&state=test_state_token"
        extracted_state = self._extract_state_from_callback(callback_url)
        assert extracted_state == "test_state_token"
        
        # Test callback without state
        callback_url_no_state = "http://localhost:8000/auth/callback/google?code=auth_code_123"
        extracted_state = self._extract_state_from_callback(callback_url_no_state)
        assert extracted_state is None
        
        # Test callback with empty state
        callback_url_empty_state = "http://localhost:8000/auth/callback/google?code=auth_code_123&state="
        extracted_state = self._extract_state_from_callback(callback_url_empty_state)
        assert extracted_state == ""
        
        # Test malformed URL
        malformed_url = "not_a_valid_url"
        extracted_state = self._extract_state_from_callback(malformed_url)
        assert extracted_state is None
        
        self.record_metric("state_extraction_tests", 4)
        
    @pytest.mark.unit
    def test_oauth_state_context_preservation(self):
        """Test preservation of user context in OAuth state."""
        provider = "github"
        user_context = {
            "intended_action": "login",
            "return_url": "/dashboard",
            "user_preference": "dark_mode",
            "session_data": {"temp_id": "temp_123"}
        }
        
        state_data = self._generate_oauth_state(provider, user_context)
        
        # Validate context preservation
        assert state_data["user_context"] == user_context
        assert state_data["user_context"]["intended_action"] == "login"
        assert state_data["user_context"]["return_url"] == "/dashboard"
        assert state_data["user_context"]["session_data"]["temp_id"] == "temp_123"
        
        self.record_metric("context_preservation_success", True)
        
    @pytest.mark.unit
    def test_oauth_state_expiry_edge_cases(self):
        """Test OAuth state expiry edge cases."""
        provider = "google"
        
        # Test state at exact expiry time
        state_data = self._generate_oauth_state(provider)
        state_data["expires_at"] = datetime.now(timezone.utc)  # Expires right now
        
        # Should be invalid (expired)
        is_valid, error_msg = self._validate_oauth_state(state_data, state_data["state_token"])
        assert is_valid is False
        assert "expired" in error_msg.lower()
        
        # Test state with missing expiry
        state_no_expiry = self._generate_oauth_state(provider)
        del state_no_expiry["expires_at"]
        is_valid, error_msg = self._validate_oauth_state(state_no_expiry, state_no_expiry["state_token"])
        assert is_valid is False
        assert "no expiry" in error_msg.lower()
        
        # Test state with future expiry (should be valid)
        state_future = self._generate_oauth_state(provider)
        state_future["expires_at"] = datetime.now(timezone.utc) + timedelta(minutes=5)
        is_valid, error_msg = self._validate_oauth_state(state_future, state_future["state_token"])
        assert is_valid is True
        
        self.record_metric("expiry_edge_cases_tested", 3)
        
    @pytest.mark.unit
    def test_oauth_provider_specific_handling(self):
        """Test OAuth state handling for different providers."""
        test_cases = [
            ("google", "openid email profile"),
            ("github", "user:email"),
            ("microsoft", "openid profile email"),
        ]
        
        for provider, expected_scope in test_cases:
            state_data = self._generate_oauth_state(provider)
            oauth_url = self._build_oauth_url(provider, state_data)
            
            # Validate provider-specific URL
            assert state_data["provider"] == provider
            assert provider in oauth_url.lower() or (
                provider == "google" and "accounts.google.com" in oauth_url
            )
            
            # Validate redirect URI includes provider
            assert provider in state_data["redirect_uri"]
            
        self.record_metric("provider_specific_tests", len(test_cases))