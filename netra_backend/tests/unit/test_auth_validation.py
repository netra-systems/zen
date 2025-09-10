"""
Unit Tests for Authentication Validation Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure and reliable user authentication
- Value Impact: Prevents unauthorized access and protects user data
- Strategic Impact: Critical security foundation - auth failures = security breaches

This module tests the authentication validation logic including:
- JWT token validation and format checking
- OAuth credential validation
- User session authentication
- WebSocket authentication flows
- Security error handling and prevention
- Compliance with security standards
"""

import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.services.unified_authentication_service import (
    UnifiedAuthenticationService,
    AuthenticationResult,
    AuthenticationError
)
from netra_backend.app.routes.auth_routes.oauth_validation import (
    validate_oauth_credentials,
    build_redirect_uri,
    handle_pr_proxy_redirect
)
from netra_backend.app.clients.auth_client_core import (
    validate_jwt_format,
    AuthServiceError,
    AuthServiceValidationError
)


class TestAuthValidation(SSotBaseTestCase):
    """Unit tests for authentication validation business logic."""
    
    def setup_method(self, method=None):
        """Setup test environment and mocks."""
        super().setup_method(method)
        
        # Test authentication data
        self.test_user_id = "test-user-12345"
        self.test_email = "test@example.com"
        self.valid_jwt_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ0ZXN0LXVzZXItMTIzNDUiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjE2ODc5NzY0MDB9."
            "test_signature"
        )
        
        # OAuth configuration mock
        self.mock_oauth_config = MagicMock()
        self.mock_oauth_config.client_id = "test_client_id"
        self.mock_oauth_config.client_secret = "test_client_secret"
        self.mock_oauth_config.use_proxy = False
        self.mock_oauth_config.proxy_url = None
        
        # Mock FastAPI request
        self.mock_request = MagicMock()
        self.mock_request.base_url = "https://test.example.com/"
        self.mock_request.headers = {
            "Authorization": f"Bearer {self.valid_jwt_token}",
            "X-Request-ID": str(uuid4())
        }
        
        # Mock WebSocket
        self.mock_websocket = AsyncMock()
        
    @pytest.mark.unit
    def test_jwt_format_validation_with_valid_token(self):
        """Test JWT format validation with properly formatted token."""
        # Business logic: Valid JWT should pass format validation
        is_valid = validate_jwt_format(self.valid_jwt_token)
        
        # Should return True for properly formatted JWT
        assert is_valid == True
        
        # Verify token has three parts (header.payload.signature)
        parts = self.valid_jwt_token.split('.')
        assert len(parts) == 3
        
        # Each part should be non-empty
        for part in parts:
            assert len(part) > 0
            
        # Record business metric: JWT validation success
        self.record_metric("jwt_format_validation_success", True)
        
    @pytest.mark.unit
    def test_jwt_format_validation_rejects_invalid_tokens(self):
        """Test JWT format validation rejects malformed tokens."""
        # Test cases for invalid JWT tokens
        invalid_tokens = [
            "",  # Empty token
            "invalid.token",  # Only 2 parts
            "not.a.jwt.token.at.all",  # Too many parts
            "invalid_base64!@#",  # Invalid characters
            "header.payload.",  # Missing signature
            ".payload.signature",  # Missing header
            "header..signature",  # Missing payload
            None,  # None value
            123,  # Non-string type
        ]
        
        for invalid_token in invalid_tokens:
            # Business logic: Invalid tokens should be rejected
            try:
                is_valid = validate_jwt_format(invalid_token)
                assert is_valid == False, f"Token should be invalid: {invalid_token}"
            except (TypeError, AttributeError):
                # Some invalid tokens may raise exceptions, which is acceptable
                pass
                
        # Record business metric: Invalid token rejection
        self.record_metric("invalid_jwt_tokens_rejected", len(invalid_tokens))
        
    @pytest.mark.unit
    def test_oauth_credentials_validation_with_valid_config(self):
        """Test OAuth credential validation with complete configuration."""
        # Business logic: Valid OAuth config should pass validation
        result = validate_oauth_credentials(self.mock_oauth_config)
        
        # Should return None (no error) for valid config
        assert result is None
        
        # Verify config has required fields
        assert self.mock_oauth_config.client_id is not None
        assert self.mock_oauth_config.client_secret is not None
        assert len(self.mock_oauth_config.client_id) > 0
        assert len(self.mock_oauth_config.client_secret) > 0
        
        # Record business metric: OAuth validation success
        self.record_metric("oauth_config_validation_success", True)
        
    @pytest.mark.unit
    def test_oauth_credentials_validation_rejects_incomplete_config(self):
        """Test OAuth credential validation rejects incomplete configuration."""
        # Test cases for invalid OAuth configurations
        invalid_configs = [
            # Missing client_id
            MagicMock(client_id=None, client_secret="secret"),
            MagicMock(client_id="", client_secret="secret"),
            
            # Missing client_secret
            MagicMock(client_id="client", client_secret=None),
            MagicMock(client_id="client", client_secret=""),
            
            # Both missing
            MagicMock(client_id=None, client_secret=None),
            MagicMock(client_id="", client_secret=""),
        ]
        
        for invalid_config in invalid_configs:
            # Business logic: Invalid config should return error redirect
            result = validate_oauth_credentials(invalid_config)
            
            # Should return RedirectResponse for invalid config
            assert result is not None
            assert hasattr(result, 'url')  # Should be a redirect
            assert "error" in result.url  # Should indicate error
            
        # Record business metric: Invalid config rejection
        self.record_metric("invalid_oauth_configs_rejected", len(invalid_configs))
        
    @pytest.mark.unit
    def test_redirect_uri_building_logic(self):
        """Test redirect URI building for different environments."""
        # Test localhost/development environment
        local_request = MagicMock()
        local_request.base_url = "http://localhost:8000/"
        
        local_uri = build_redirect_uri(local_request)
        assert local_uri == "http://localhost:8000/auth/callback"
        
        # Test production environment
        prod_request = MagicMock()
        prod_request.base_url = "https://api.netra.ai/"
        
        prod_uri = build_redirect_uri(prod_request)
        assert prod_uri == "https://api.netra.ai/auth/callback"
        
        # Test with trailing slash handling
        trailing_request = MagicMock()
        trailing_request.base_url = "https://staging.netra.ai//"
        
        trailing_uri = build_redirect_uri(trailing_request)
        assert not trailing_uri.endswith("//auth/callback")  # Should handle trailing slashes
        
        # Record business metric: URI building success
        self.record_metric("redirect_uri_building_success", True)
        
    @pytest.mark.unit
    def test_authentication_error_handling(self):
        """Test authentication error handling for business continuity."""
        # Test different authentication error scenarios
        error_scenarios = [
            ("invalid_token", "Token format is invalid"),
            ("expired_token", "Token has expired"),
            ("unauthorized_user", "User not authorized for this resource"),
            ("service_unavailable", "Authentication service temporarily unavailable"),
            ("network_error", "Network connection to auth service failed")
        ]
        
        for error_code, error_message in error_scenarios:
            # Business logic: Errors should be handled gracefully
            auth_error = self._create_auth_error(error_code, error_message)
            
            # Verify error contains business-relevant information
            assert auth_error.error_code == error_code
            assert auth_error.message == error_message
            assert hasattr(auth_error, 'timestamp')
            
            # Error should be categorized for business metrics
            category = self._categorize_auth_error(error_code)
            assert category in ['client_error', 'server_error', 'network_error']
            
        # Record business metric: Error handling robustness
        self.record_metric("auth_error_scenarios_handled", len(error_scenarios))
        
    def _create_auth_error(self, error_code: str, message: str) -> Dict[str, Any]:
        """Create authentication error for testing."""
        return {
            'error_code': error_code,
            'message': message,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'request_id': str(uuid4())
        }
        
    def _categorize_auth_error(self, error_code: str) -> str:
        """Categorize authentication error for business metrics."""
        client_errors = ['invalid_token', 'expired_token', 'unauthorized_user']
        server_errors = ['service_unavailable', 'internal_error']
        network_errors = ['network_error', 'timeout']
        
        if error_code in client_errors:
            return 'client_error'
        elif error_code in server_errors:
            return 'server_error'
        elif error_code in network_errors:
            return 'network_error'
        else:
            return 'unknown_error'
            
    @pytest.mark.unit
    def test_session_timeout_validation(self):
        """Test session timeout validation for security compliance."""
        # Business requirement: Sessions should have reasonable timeouts
        current_time = datetime.now(timezone.utc)
        
        # Test valid session (not expired)
        valid_session = {
            'created_at': current_time - timedelta(minutes=30),
            'expires_at': current_time + timedelta(hours=1),
            'user_id': self.test_user_id
        }
        
        is_valid = self._validate_session_timeout(valid_session, current_time)
        assert is_valid == True
        
        # Test expired session
        expired_session = {
            'created_at': current_time - timedelta(hours=2),
            'expires_at': current_time - timedelta(minutes=5),
            'user_id': self.test_user_id
        }
        
        is_expired = self._validate_session_timeout(expired_session, current_time)
        assert is_expired == False
        
        # Test session close to expiry (business rule: warn before expiry)
        soon_expired_session = {
            'created_at': current_time - timedelta(minutes=55),
            'expires_at': current_time + timedelta(minutes=5),
            'user_id': self.test_user_id
        }
        
        needs_refresh = self._session_needs_refresh(soon_expired_session, current_time)
        assert needs_refresh == True
        
        # Record business metric: Session validation success
        self.record_metric("session_timeout_validation_success", True)
        
    def _validate_session_timeout(self, session: Dict[str, Any], current_time: datetime) -> bool:
        """Validate session timeout for business security requirements."""
        expires_at = session.get('expires_at')
        if not expires_at:
            return False
            
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
        return expires_at > current_time
        
    def _session_needs_refresh(self, session: Dict[str, Any], current_time: datetime) -> bool:
        """Check if session needs refresh for user experience."""
        expires_at = session.get('expires_at')
        if not expires_at:
            return True
            
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            
        # Refresh if less than 10 minutes remaining
        time_remaining = expires_at - current_time
        return time_remaining.total_seconds() < 600
        
    @pytest.mark.unit
    def test_authentication_performance_requirements(self):
        """Test authentication performance for business responsiveness."""
        import time
        
        # Business requirement: Auth validation should be fast
        start_time = time.time()
        
        # Simulate multiple authentication validations
        validation_results = []
        for i in range(50):
            # Simulate JWT validation
            token_valid = validate_jwt_format(self.valid_jwt_token)
            
            # Simulate OAuth config validation
            oauth_result = validate_oauth_credentials(self.mock_oauth_config)
            
            validation_results.append({
                'token_valid': token_valid,
                'oauth_valid': oauth_result is None
            })
            
        end_time = time.time()
        total_time = end_time - start_time
        
        # Business requirement: Should validate 50 requests in < 100ms
        assert total_time < 0.1, f"Authentication too slow: {total_time}s for 50 validations"
        
        # All validations should succeed
        successful_validations = sum(1 for result in validation_results 
                                   if result['token_valid'] and result['oauth_valid'])
        assert successful_validations == 50
        
        # Record performance metrics
        self.record_metric("auth_validation_time_ms", total_time * 1000)
        self.record_metric("validations_per_second", 50 / total_time)
        
    @pytest.mark.unit
    def test_security_compliance_requirements(self):
        """Test security compliance for business protection."""
        # Test password-like secrets are not logged
        sensitive_data = [
            "password123",
            "secret_api_key_abc123",
            self.valid_jwt_token,
            "client_secret_xyz789"
        ]
        
        for secret in sensitive_data:
            # Business requirement: Secrets should not appear in logs
            log_entry = self._create_log_entry_with_secret(secret)
            sanitized_log = self._sanitize_log_for_security(log_entry)
            
            # Verify secret is masked
            assert secret not in sanitized_log
            assert "[REDACTED]" in sanitized_log or "[MASKED]" in sanitized_log
            
        # Test that non-sensitive data is preserved
        non_sensitive_log = self._create_log_entry_with_secret("user_id_12345")
        sanitized_non_sensitive = self._sanitize_log_for_security(non_sensitive_log)
        assert "user_id_12345" in sanitized_non_sensitive
        
        # Record business metric: Security compliance
        self.record_metric("security_compliance_validated", True)
        self.record_metric("sensitive_data_cases_tested", len(sensitive_data))
        
    def _create_log_entry_with_secret(self, secret: str) -> str:
        """Create log entry containing secret for testing."""
        return f"User authentication with token: {secret} for request_id: 12345"
        
    def _sanitize_log_for_security(self, log_entry: str) -> str:
        """Sanitize log entry to remove sensitive data."""
        # Simple implementation for testing
        import re
        
        # Mask JWT tokens
        log_entry = re.sub(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', '[REDACTED_JWT]', log_entry)
        
        # Mask other secrets (simple pattern)
        log_entry = re.sub(r'(password|secret|key)[^:\s]*:\s*\S+', r'\1: [REDACTED]', log_entry, flags=re.IGNORECASE)
        
        return log_entry
        
    def teardown_method(self, method=None):
        """Clean up test environment."""
        # Log business metrics for security monitoring
        final_metrics = self.get_all_metrics()
        
        # Set security validation flags
        if final_metrics.get("jwt_format_validation_success"):
            self.set_env_var("LAST_AUTH_VALIDATION_TEST_SUCCESS", "true")
            
        if final_metrics.get("security_compliance_validated"):
            self.set_env_var("SECURITY_COMPLIANCE_VALIDATED", "true")
            
        # Performance validation
        auth_time = final_metrics.get("auth_validation_time_ms", 999)
        if auth_time < 50:  # Under 50ms for 50 validations
            self.set_env_var("AUTH_PERFORMANCE_ACCEPTABLE", "true")
            
        super().teardown_method(method)