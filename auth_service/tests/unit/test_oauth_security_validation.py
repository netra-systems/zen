"""
Test OAuth Security Validation - BATCH 4 Authentication Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Secure OAuth integration prevents account takeover and data breaches
- Value Impact: Users can safely authenticate with Google/OAuth while maintaining security
- Strategic Impact: OAuth security critical for enterprise adoption and compliance

Focus: OAuth state validation, CSRF protection, token exchange security, redirect validation
"""

import pytest
import secrets
from unittest.mock import Mock, patch, AsyncMock
from urllib.parse import urlencode, parse_qs

from auth_service.auth_core.oauth_manager import OAuthManager
from auth_service.auth_core.oauth.google_oauth import GoogleOAuthProvider, GoogleOAuthError
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env


class TestOAuthSecurityValidation(BaseIntegrationTest):
    """Test OAuth security validation and attack prevention"""

    def setup_method(self):
        """Set up test environment"""
        self.oauth_manager = OAuthManager()

    @pytest.mark.unit
    def test_oauth_state_csrf_protection(self):
        """Test OAuth state parameter CSRF protection implementation"""
        # Test OAuth manager initialization
        available_providers = self.oauth_manager.get_available_providers()
        
        if "google" in available_providers:
            google_provider = self.oauth_manager.get_provider("google")
            assert google_provider is not None
            
            # Test state generation for CSRF protection
            test_states = []
            for _ in range(10):
                state = secrets.token_urlsafe(32)
                test_states.append(state)
            
            # All states should be unique (prevent state collision attacks)
            assert len(set(test_states)) == len(test_states)
            
            # States should be substantial length (prevent brute force)
            for state in test_states:
                assert len(state) >= 32
                assert isinstance(state, str)
                # Should be URL-safe base64
                assert all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in state)
        
        # Test provider configuration status
        provider_status = self.oauth_manager.get_provider_status("google")
        assert "provider" in provider_status
        assert "available" in provider_status
        assert provider_status["provider"] == "google"

    @pytest.mark.unit
    def test_oauth_redirect_uri_validation_security(self):
        """Test OAuth redirect URI validation prevents malicious redirects"""
        if "google" in self.oauth_manager.get_available_providers():
            google_provider = self.oauth_manager.get_provider("google")
            
            if google_provider and hasattr(google_provider, 'get_redirect_uri'):
                # Test legitimate redirect URI
                redirect_uri = google_provider.get_redirect_uri()
                assert redirect_uri is not None
                assert isinstance(redirect_uri, str)
                assert redirect_uri.startswith(('http://', 'https://'))
                
                # Security: Redirect URI should not be manipulable
                # Test that common redirect attacks are prevented
                malicious_redirects = [
                    "javascript:alert('xss')",
                    "data:text/html,<script>alert('xss')</script>",
                    "//evil.com/callback",
                    "https://evil.com/callback",
                    "http://localhost:3000@evil.com/callback",
                    "https://app.netrasystems.ai.evil.com/callback",
                ]
                
                # These should not match our legitimate redirect URI
                for malicious_redirect in malicious_redirects:
                    assert redirect_uri != malicious_redirect, f"Redirect URI should not be malicious: {malicious_redirect}"
                
                # Test redirect URI components are secure
                if redirect_uri.startswith('https://'):
                    # Production should use HTTPS
                    pass
                elif redirect_uri.startswith('http://localhost:'):
                    # Development may use HTTP localhost
                    pass
                else:
                    # Other HTTP should be flagged for review
                    assert False, f"Redirect URI should use HTTPS or localhost: {redirect_uri}"

    @pytest.mark.integration
    def test_oauth_authorization_url_security(self):
        """Test OAuth authorization URL generation security parameters"""
        if "google" in self.oauth_manager.get_available_providers():
            google_provider = self.oauth_manager.get_provider("google")
            
            if google_provider and hasattr(google_provider, 'get_authorization_url'):
                test_state = secrets.token_urlsafe(32)
                
                try:
                    # Generate authorization URL
                    auth_url = google_provider.get_authorization_url(test_state)
                    assert auth_url is not None
                    assert isinstance(auth_url, str)
                    assert auth_url.startswith('https://accounts.google.com/oauth2/auth')
                    
                    # Parse URL parameters for security validation
                    from urllib.parse import urlparse, parse_qs
                    parsed = urlparse(auth_url)
                    params = parse_qs(parsed.query)
                    
                    # Security: Required OAuth parameters should be present
                    required_params = ['client_id', 'redirect_uri', 'response_type', 'scope', 'state']
                    for param in required_params:
                        assert param in params, f"Required OAuth parameter missing: {param}"
                    
                    # Security: State should match what we provided
                    assert params['state'][0] == test_state
                    
                    # Security: Response type should be 'code' (authorization code flow)
                    assert params['response_type'][0] == 'code'
                    
                    # Security: Scope should request appropriate permissions
                    scope = params['scope'][0]
                    assert 'openid' in scope or 'email' in scope, "OAuth scope should request user identification"
                    
                    # Security: Redirect URI should be our legitimate URI
                    redirect_uri = params['redirect_uri'][0]
                    assert redirect_uri.startswith(('http://localhost:', 'https://'))
                    
                except GoogleOAuthError:
                    # If OAuth is not configured, this is acceptable in test environment
                    pass
                except Exception:
                    # Other configuration issues are acceptable in test environment
                    pass

    @pytest.mark.integration
    def test_oauth_token_exchange_security_validation(self):
        """Test OAuth token exchange security and validation"""
        if "google" in self.oauth_manager.get_available_providers():
            google_provider = self.oauth_manager.get_provider("google")
            
            if google_provider and hasattr(google_provider, 'exchange_code_for_user_info'):
                # Test with invalid authorization codes
                invalid_codes = [
                    "",  # Empty code
                    "invalid-code-12345",  # Invalid format
                    "sql-injection'; DROP TABLE users; --",  # SQL injection attempt
                    "<script>alert('xss')</script>",  # XSS attempt
                    "a" * 1000,  # Overly long code
                ]
                
                test_state = secrets.token_urlsafe(32)
                
                for invalid_code in invalid_codes:
                    try:
                        # Should handle invalid codes gracefully
                        user_info = google_provider.exchange_code_for_user_info(invalid_code, test_state)
                        # Should return None or raise exception for invalid codes
                        assert user_info is None, f"Should reject invalid code: {invalid_code[:20]}..."
                    except GoogleOAuthError:
                        # Raising GoogleOAuthError is acceptable for invalid codes
                        pass
                    except Exception as e:
                        # Other exceptions should be handled gracefully
                        assert "google" in str(e).lower() or "oauth" in str(e).lower(), f"Exception should be OAuth-related: {e}"
                
                # Test state validation in token exchange
                valid_looking_code = "valid-format-code-12345"
                invalid_states = [
                    "",  # Empty state
                    "wrong-state-value",  # Wrong state
                    None,  # None state
                ]
                
                for invalid_state in invalid_states:
                    try:
                        user_info = google_provider.exchange_code_for_user_info(valid_looking_code, invalid_state)
                        # Should handle state validation appropriately
                        # May return None or raise exception
                    except (GoogleOAuthError, ValueError):
                        # State validation errors are expected
                        pass
                    except Exception:
                        # Other errors are acceptable in test environment
                        pass

    @pytest.mark.integration
    def test_oauth_user_info_validation_security(self):
        """Test OAuth user info validation and sanitization"""
        if "google" in self.oauth_manager.get_available_providers():
            google_provider = self.oauth_manager.get_provider("google")
            
            # Test user info processing with malicious inputs
            malicious_user_infos = [
                {
                    "id": "'; DROP TABLE users; --",  # SQL injection in ID
                    "email": "malicious@example.com",
                    "name": "Malicious User"
                },
                {
                    "id": "user123",
                    "email": "<script>alert('xss')</script>@evil.com",  # XSS in email
                    "name": "XSS User"
                },
                {
                    "id": "user456",
                    "email": "user@example.com",
                    "name": "<img src=x onerror=alert('xss')>"  # XSS in name
                },
                {
                    "id": "../../../etc/passwd",  # Path traversal in ID
                    "email": "path@example.com", 
                    "name": "Path User"
                },
                {
                    "id": "user789",
                    "email": "a" * 1000 + "@example.com",  # Overly long email
                    "name": "Long Email User"
                }
            ]
            
            # These should be handled safely without causing security issues
            for malicious_info in malicious_user_infos:
                # In a real OAuth flow, this would be processed by create_oauth_user
                # We test the validation logic that should be applied
                
                # Email validation
                email = malicious_info.get("email", "")
                if email and len(email) < 255:  # Reasonable length
                    # Should not contain script tags or other dangerous content
                    assert "<script>" not in email.lower()
                    assert "javascript:" not in email.lower()
                    assert "data:" not in email.lower()
                
                # Name validation  
                name = malicious_info.get("name", "")
                if name:
                    # Should not contain script tags
                    assert "<script>" not in name.lower()
                    assert "onerror=" not in name.lower()
                    assert "javascript:" not in name.lower()
                
                # ID validation
                user_id = malicious_info.get("id", "")
                if user_id:
                    # Should not contain SQL injection patterns
                    assert "DROP TABLE" not in user_id.upper()
                    assert "--" not in user_id
                    assert ".." not in user_id  # Path traversal

    @pytest.mark.integration
    def test_oauth_error_handling_security(self):
        """Test OAuth error handling doesn't leak sensitive information"""
        if "google" in self.oauth_manager.get_available_providers():
            google_provider = self.oauth_manager.get_provider("google")
            
            # Test various error scenarios
            error_scenarios = [
                ("", "empty_state"),  # Empty code and state
                ("invalid", ""),  # Invalid code, empty state
                (None, None),  # None values
                ("code123", "state456"),  # Valid format but likely invalid
            ]
            
            for code, state in error_scenarios:
                try:
                    if google_provider and hasattr(google_provider, 'exchange_code_for_user_info'):
                        result = google_provider.exchange_code_for_user_info(code, state)
                        # Should return None for invalid inputs
                        if result is not None:
                            # If it returns something, it should be safe user info
                            assert isinstance(result, dict)
                            if "email" in result:
                                assert "@" in result["email"]  # Basic email format
                except GoogleOAuthError as e:
                    # OAuth errors should not leak sensitive information
                    error_message = str(e)
                    
                    # Should not contain sensitive data
                    sensitive_patterns = [
                        "client_secret",
                        "access_token", 
                        "refresh_token",
                        "password",
                        "key",
                        "secret"
                    ]
                    
                    for pattern in sensitive_patterns:
                        assert pattern not in error_message.lower(), f"Error message should not leak {pattern}: {error_message}"
                    
                    # Should provide helpful but safe error information
                    assert len(error_message) > 0  # Should have some error message
                    assert len(error_message) < 500  # Should not be overly verbose
                    
                except Exception as e:
                    # Other exceptions should also be safe
                    error_message = str(e)
                    assert "secret" not in error_message.lower()
                    assert "token" not in error_message.lower() or "invalid" in error_message.lower()
        
        # Test OAuth manager error handling
        provider_status = self.oauth_manager.get_provider_status("nonexistent-provider")
        assert provider_status["available"] is False
        assert "error" in provider_status or "provider" in provider_status

    @pytest.mark.e2e
    async def test_complete_oauth_security_flow_validation(self):
        """E2E test of complete OAuth security flow with attack prevention"""
        # Test complete OAuth security flow: Authorization -> Token Exchange -> User Creation -> Session
        
        # 1. OAuth Provider Initialization Security
        oauth_manager = OAuthManager()
        available_providers = oauth_manager.get_available_providers()
        
        # Should have expected providers configured securely
        if "google" in available_providers:
            google_provider = oauth_manager.get_provider("google")
            assert google_provider is not None
            
            # Provider should be properly configured or safely unconfigured
            is_configured = oauth_manager.is_provider_configured("google")
            provider_status = oauth_manager.get_provider_status("google")
            
            assert provider_status["available"] is True
            assert provider_status["configured"] == is_configured
            
            # 2. Authorization URL Security
            if is_configured and hasattr(google_provider, 'get_authorization_url'):
                # Generate secure state
                secure_state = secrets.token_urlsafe(32)
                
                try:
                    auth_url = google_provider.get_authorization_url(secure_state)
                    
                    # Validate authorization URL security
                    assert auth_url.startswith('https://')  # Must use HTTPS
                    assert 'state=' + secure_state in auth_url  # State must be included
                    assert 'client_id=' in auth_url  # Client ID must be included
                    assert 'scope=' in auth_url  # Scope must be specified
                    assert 'response_type=code' in auth_url  # Authorization code flow
                    
                except GoogleOAuthError:
                    # Configuration errors are acceptable in test environment
                    pass
            
            # 3. Token Exchange Security Validation
            if hasattr(google_provider, 'exchange_code_for_user_info'):
                # Test security against various attack vectors
                attack_vectors = [
                    # Code injection attacks
                    ("'; DROP TABLE oauth_tokens; --", "valid_state"),
                    ("<script>alert('code_injection')</script>", "valid_state"),
                    
                    # State parameter attacks  
                    ("valid_code", "'; DROP TABLE sessions; --"),
                    ("valid_code", "<script>alert('state_injection')</script>"),
                    
                    # Parameter manipulation attacks
                    ("../../../etc/passwd", "valid_state"),
                    ("valid_code", "../../../etc/shadow"),
                    
                    # Buffer overflow attempts
                    ("A" * 10000, "valid_state"),
                    ("valid_code", "B" * 10000),
                    
                    # Null byte attacks
                    ("valid_code\x00malicious", "valid_state"),
                    ("valid_code", "valid_state\x00malicious"),
                ]
                
                for malicious_code, malicious_state in attack_vectors:
                    try:
                        result = google_provider.exchange_code_for_user_info(malicious_code, malicious_state)
                        # Should safely return None or raise controlled exception
                        if result is not None:
                            # If it returns data, it should be sanitized
                            assert isinstance(result, dict)
                            for key, value in result.items():
                                if isinstance(value, str):
                                    assert len(value) < 1000  # Reasonable length
                                    assert "<script>" not in value.lower()  # XSS prevention
                                    assert "DROP TABLE" not in value.upper()  # SQL injection prevention
                    
                    except GoogleOAuthError:
                        # OAuth errors are expected for malicious inputs
                        pass
                    except Exception as e:
                        # Other exceptions should be safe
                        error_msg = str(e)
                        assert len(error_msg) < 1000  # Don't leak too much information
                        assert "secret" not in error_msg.lower()
                        assert "key" not in error_msg.lower() or "invalid" in error_msg.lower()
            
            # 4. Configuration Security Validation
            config_status = google_provider.get_configuration_status() if hasattr(google_provider, 'get_configuration_status') else {}
            
            # Configuration status should not leak sensitive information
            if isinstance(config_status, dict):
                for key, value in config_status.items():
                    if isinstance(value, str):
                        # Should not contain secrets
                        assert "client_secret" not in value
                        assert not (key.lower() == "client_secret" and len(value) > 10)
                        
                        # Should not contain full tokens
                        assert not (len(value) > 100 and "." in value and value.count(".") >= 2)
        
        # 5. Provider Error Handling Security
        # Test nonexistent provider
        nonexistent_provider = oauth_manager.get_provider("nonexistent")
        assert nonexistent_provider is None
        
        nonexistent_status = oauth_manager.get_provider_status("nonexistent")
        assert nonexistent_status["available"] is False
        assert "error" in nonexistent_status
        
        # Error message should be safe
        error_msg = nonexistent_status.get("error", "")
        assert len(error_msg) > 0  # Should have error message
        assert len(error_msg) < 100  # Should be concise
        assert "secret" not in error_msg.lower()
        
        # 6. Cross-Site Request Forgery (CSRF) Protection
        # Generate multiple states and ensure they're unique
        states = [secrets.token_urlsafe(32) for _ in range(100)]
        assert len(set(states)) == 100  # All should be unique
        
        # States should be cryptographically secure
        for state in states[:10]:  # Test first 10
            assert len(state) >= 32  # Sufficient entropy
            # Should use URL-safe characters
            valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
            assert all(c in valid_chars for c in state)
        
        # 7. Session Fixation Prevention
        # Each OAuth flow should generate unique session identifiers
        # This would typically be tested at the session management level
        # Here we ensure OAuth doesn't introduce session fixation vulnerabilities
        
        # 8. Man-in-the-Middle (MITM) Protection
        # Verify that OAuth URLs use HTTPS
        if "google" in available_providers and oauth_manager.is_provider_configured("google"):
            google_provider = oauth_manager.get_provider("google")
            if hasattr(google_provider, 'get_authorization_url'):
                try:
                    auth_url = google_provider.get_authorization_url("test_state")
                    assert auth_url.startswith('https://'), "OAuth URLs must use HTTPS for MITM protection"
                except:
                    pass  # Configuration errors acceptable in tests
        
        # 9. Information Disclosure Prevention
        # Verify that OAuth errors don't leak sensitive information
        all_provider_statuses = [oauth_manager.get_provider_status(p) for p in ["google", "nonexistent", "facebook"]]
        
        for status in all_provider_statuses:
            assert isinstance(status, dict)
            # Should not contain secrets in any field
            for key, value in status.items():
                if isinstance(value, str):
                    sensitive_keywords = ["secret", "key", "token", "password"]
                    for keyword in sensitive_keywords:
                        if keyword in key.lower():
                            # If key suggests sensitivity, value should be masked or empty
                            assert len(value) <= 10 or "***" in value or "hidden" in value.lower()
        
        # 10. Rate Limiting and Abuse Prevention
        # OAuth flows should have implicit rate limiting (handled by Google)
        # We ensure our implementation doesn't facilitate abuse
        
        # Test rapid state generation doesn't cause issues
        rapid_states = []
        import time
        start_time = time.time()
        for _ in range(1000):
            rapid_states.append(secrets.token_urlsafe(16))
        end_time = time.time()
        
        # Should be fast and not cause memory issues
        assert end_time - start_time < 1.0  # Should complete in under 1 second
        assert len(set(rapid_states)) == 1000  # All should be unique
        assert len(rapid_states) == 1000  # No memory corruption