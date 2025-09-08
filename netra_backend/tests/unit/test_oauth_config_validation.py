"""
env = get_env()
OAuth Configuration Validation Tests
===================================

This test suite validates OAuth configuration issues identified in staging environment.
These tests are designed to FAIL with the current staging configuration to demonstrate
the identified issues and pass once the configuration is properly set.

IDENTIFIED ISSUES FROM STAGING:
1. GOOGLE_CLIENT_ID not configured (missing or empty)
2. GOOGLE_CLIENT_SECRET not configured (missing or empty) 
3. OAuth authentication flows failing due to missing credentials
4. Service startup issues when OAuth providers are not properly configured

SECURITY IMPLICATIONS:
- Missing OAuth credentials prevent Google authentication
- Users cannot sign in with Google accounts
- Authentication fallback mechanisms may not work
- System functionality degraded without proper OAuth setup

BVJ (Business Value Justification):
- Segment: All tiers | Goal: Authentication & User Experience | Impact: Critical user access
- Enables Google OAuth sign-in for user convenience and adoption
- Prevents authentication failures that block user onboarding
- Maintains secure authentication flows with proper credential management
- Supports multi-provider authentication strategy

Expected Test Behavior:
- Tests SHOULD FAIL with current staging OAuth config (demonstrates missing credentials)
- Tests SHOULD PASS once GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are properly configured
- Validates proper OAuth credential format and security requirements
"""

import os
import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import pytest

from shared.isolated_environment import get_env


class TestOAuthCredentialsConfiguration:
    """Test OAuth credentials configuration for authentication providers."""
    
    def test_google_client_id_missing_current_staging_issue(self):
        """
        Test Google Client ID configuration - CURRENT STAGING ISSUE.
        
        This test should FAIL with current staging config to demonstrate missing credentials.
        GOOGLE_CLIENT_ID is required for Google OAuth authentication.
        
        Issue: Current staging GOOGLE_CLIENT_ID is not configured.
        """
        # Get the actual GOOGLE_CLIENT_ID from environment
        env_vars = get_env()
        google_client_id = env_vars.get("GOOGLE_CLIENT_ID", "")
        
        # This assertion should FAIL with current staging config
        assert google_client_id, (
            f"STAGING ISSUE: GOOGLE_CLIENT_ID is missing or empty. "
            f"Google OAuth authentication cannot work without client ID. "
            f"Current value: '{google_client_id}'. This test exposes the actual staging configuration problem."
        )
        
        # Additional validation for proper format
        assert len(google_client_id) > 10, (
            f"STAGING ISSUE: GOOGLE_CLIENT_ID is too short to be valid. "
            f"Google Client IDs are typically 72 characters. "
            f"Current length: {len(google_client_id)}"
        )
        
        # Google Client IDs should end with .googleusercontent.com
        assert google_client_id.endswith('.googleusercontent.com'), (
            f"STAGING ISSUE: GOOGLE_CLIENT_ID format is invalid. "
            f"Should end with '.googleusercontent.com'. "
            f"Current value: '{google_client_id}'"
        )
    
    def test_google_client_secret_missing_current_staging_issue(self):
        """
        Test Google Client Secret configuration - CURRENT STAGING ISSUE.
        
        This test should FAIL with current staging config to demonstrate missing secret.
        GOOGLE_CLIENT_SECRET is required for Google OAuth token exchange.
        
        Issue: Current staging GOOGLE_CLIENT_SECRET is not configured.
        """
        # Get the actual GOOGLE_CLIENT_SECRET from environment
        env_vars = get_env()
        google_client_secret = env_vars.get("GOOGLE_CLIENT_SECRET", "")
        
        # This assertion should FAIL with current staging config
        assert google_client_secret, (
            f"STAGING ISSUE: GOOGLE_CLIENT_SECRET is missing or empty. "
            f"Google OAuth token exchange cannot work without client secret. "
            f"This test exposes the actual staging configuration problem."
        )
        
        # Additional validation for proper format
        assert len(google_client_secret) >= 24, (
            f"STAGING ISSUE: GOOGLE_CLIENT_SECRET is too short to be valid. "
            f"Google Client Secrets are typically 24+ characters. "
            f"Current length: {len(google_client_secret)}"
        )
    
    def test_oauth_credentials_both_present_requirement(self):
        """
        Test that both OAuth credentials are present together.
        
        Partial OAuth configuration (only one credential) is not functional.
        Both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured.
        """
        env_vars = get_env()
        google_client_id = env_vars.get("GOOGLE_CLIENT_ID", "")
        google_client_secret = env_vars.get("GOOGLE_CLIENT_SECRET", "")
        
        # If one is present, both should be present
        has_client_id = bool(google_client_id)
        has_client_secret = bool(google_client_secret)
        
        if has_client_id or has_client_secret:
            assert has_client_id and has_client_secret, (
                f"CONFIGURATION ISSUE: Partial OAuth configuration detected. "
                f"Both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured together. "
                f"Has Client ID: {has_client_id}, Has Client Secret: {has_client_secret}"
            )
    
    def test_oauth_credentials_validation_empty_scenarios(self):
        """Test OAuth credentials validation with empty/invalid scenarios."""
        
        def validate_google_oauth_config(client_id: Optional[str], client_secret: Optional[str]) -> Tuple[bool, str]:
            """Mock OAuth credentials validation."""
            # Check if both are provided or both are missing
            has_id = bool(client_id and client_id.strip())
            has_secret = bool(client_secret and client_secret.strip())
            
            if not has_id and not has_secret:
                return False, "Both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET are missing"
            
            if has_id and not has_secret:
                return False, "GOOGLE_CLIENT_SECRET is missing but GOOGLE_CLIENT_ID is present"
            
            if not has_id and has_secret:
                return False, "GOOGLE_CLIENT_ID is missing but GOOGLE_CLIENT_SECRET is present"
            
            # Validate client ID format
            if not client_id.endswith('.googleusercontent.com'):
                return False, "Invalid GOOGLE_CLIENT_ID format"
            
            if len(client_id) < 50:  # Google Client IDs are typically ~72 characters
                return False, "GOOGLE_CLIENT_ID too short"
            
            # Validate client secret format
            if len(client_secret) < 24:  # Google Client Secrets are typically 24+ characters
                return False, "GOOGLE_CLIENT_SECRET too short"
            
            return True, "Valid OAuth configuration"
        
        # Test empty/invalid scenarios (should fail)
        invalid_scenarios = [
            (None, None, "both missing"),
            ("", "", "both empty"),
            ("   ", "   ", "both whitespace"),
            ("valid_client_id_123.googleusercontent.com", None, "missing secret"),
            (None, "valid_client_secret_123456789012345678901234", "missing client id"),
            ("invalid_client_id", "valid_secret", "invalid client id format"),
            ("short.googleusercontent.com", "valid_secret_123456789012345678901234", "client id too short"),
            ("valid_client_id_123456789012345678901234567890.googleusercontent.com", "short", "secret too short"),
        ]
        
        for client_id, client_secret, test_case in invalid_scenarios:
            is_valid, reason = validate_google_oauth_config(client_id, client_secret)
            assert not is_valid, (
                f"Invalid OAuth config should be rejected - {test_case}: "
                f"client_id='{client_id}', client_secret='{client_secret}', reason={reason}"
            )
    
    def test_oauth_credentials_validation_valid_scenarios(self):
        """Test OAuth credentials validation with valid scenarios."""
        
        def validate_google_oauth_config(client_id: str, client_secret: str) -> Tuple[bool, str]:
            """Mock OAuth credentials validation."""
            if not client_id or not client_secret:
                return False, "Missing credentials"
            
            if not client_id.endswith('.googleusercontent.com'):
                return False, "Invalid client ID format"
            
            if len(client_id) < 50 or len(client_secret) < 24:
                return False, "Credentials too short"
            
            return True, "Valid OAuth configuration"
        
        # Test valid scenarios (should pass)
        valid_scenarios = [
            (
                "123456789012345678901234567890123456789012.googleusercontent.com",
                "GOCSPX-abcdefghijklmnopqrstuvwxyz1234567890",
                "Standard Google OAuth credentials"
            ),
            (
                "987654321098765432109876543210987654321098.googleusercontent.com",
                "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87654321",
                "Alternative valid credentials"
            ),
        ]
        
        for client_id, client_secret, test_case in valid_scenarios:
            is_valid, reason = validate_google_oauth_config(client_id, client_secret)
            assert is_valid, (
                f"Valid OAuth config should be accepted - {test_case}: "
                f"client_id='{client_id[:20]}...', reason={reason}"
            )


class TestOAuthEnvironmentConfiguration:
    """Test OAuth configuration for different environments."""
    
    def test_oauth_environment_variable_loading(self):
        """Test OAuth credentials loading from environment variables."""
        
        test_scenarios = [
            # (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, should_be_valid, description)
            (
                "123456789012345678901234567890123456789012.googleusercontent.com",
                "GOCSPX-valid_secret_with_24_chars",
                True,
                "Valid credentials"
            ),
            (
                "invalid_client_id",
                "valid_secret_123456789012345678901234",
                False,
                "Invalid client ID format"
            ),
            (
                "",
                "",
                False,
                "Empty credentials"
            ),
            (
                "123456789012345678901234567890123456789012.googleusercontent.com",
                "",
                False,
                "Missing client secret"
            ),
        ]
        
        for client_id, client_secret, should_be_valid, description in test_scenarios:
            env_vars = {
                "GOOGLE_CLIENT_ID": client_id,
                "GOOGLE_CLIENT_SECRET": client_secret
            }
            
            with patch.dict(os.environ, env_vars, clear=False):
                loaded_id = env.get("GOOGLE_CLIENT_ID", "")
                loaded_secret = env.get("GOOGLE_CLIENT_SECRET", "")
                
                # Mock validation
                is_valid = (
                    bool(loaded_id) and 
                    bool(loaded_secret) and
                    loaded_id.endswith('.googleusercontent.com') and
                    len(loaded_id) >= 50 and
                    len(loaded_secret) >= 24
                )
                
                assert is_valid == should_be_valid, (
                    f"Environment OAuth validation failed - {description}: "
                    f"expected {should_be_valid}, got {is_valid}"
                )
    
    def test_oauth_redirect_uri_configuration(self):
        """Test OAuth redirect URI configuration for different environments."""
        
        def validate_oauth_redirect_uris(base_url: str, environment: str) -> Tuple[bool, str]:
            """Mock OAuth redirect URI validation."""
            if not base_url:
                return False, "Base URL is required"
            
            # Parse URL
            try:
                parsed = urlparse(base_url)
                if not parsed.scheme or not parsed.netloc:
                    return False, "Invalid URL format"
            except Exception:
                return False, "URL parsing failed"
            
            # Environment-specific validation
            if environment == "production":
                if parsed.scheme != "https":
                    return False, "Production must use HTTPS"
                if "localhost" in parsed.netloc:
                    return False, "Production cannot use localhost"
            
            elif environment == "staging":
                if parsed.scheme not in ["https", "http"]:
                    return False, "Staging must use HTTP/HTTPS"
            
            elif environment == "development":
                # Development allows localhost and HTTP
                pass
            
            return True, "Valid redirect URI configuration"
        
        # Test redirect URI scenarios
        redirect_tests = [
            ("https://netra-app.com", "production", True),
            ("http://localhost:3000", "development", True),
            ("https://staging.netra-app.com", "staging", True),
            ("http://netra-app.com", "production", False),  # production needs HTTPS
            ("https://localhost:3000", "production", False),  # production cannot use localhost
            ("", "staging", False),  # empty URL
            ("invalid-url", "development", False),  # invalid format
        ]
        
        for base_url, env, expected_valid in redirect_tests:
            is_valid, reason = validate_oauth_redirect_uris(base_url, env)
            assert is_valid == expected_valid, (
                f"OAuth redirect URI validation failed: "
                f"url='{base_url}', env='{env}', expected {expected_valid}, reason: {reason}"
            )


class TestOAuthSecurityConfiguration:
    """Test OAuth security configuration and validation."""
    
    def test_oauth_state_parameter_security(self):
        """Test OAuth state parameter generation and validation."""
        
        def generate_oauth_state() -> str:
            """Mock OAuth state generation."""
            import secrets
            return secrets.token_urlsafe(32)
        
        def validate_oauth_state(state: str) -> bool:
            """Mock OAuth state validation."""
            if not state:
                return False
            if len(state) < 16:  # Minimum length for security
                return False
            # Should be URL-safe base64
            import re
            if not re.match(r'^[A-Za-z0-9_-]+$', state):
                return False
            return True
        
        # Test state generation and validation
        for i in range(5):  # Test multiple generations
            state = generate_oauth_state()
            is_valid = validate_oauth_state(state)
            assert is_valid, f"Generated OAuth state should be valid: '{state}'"
            assert len(state) >= 32, f"OAuth state should be sufficiently long: {len(state)}"
        
        # Test invalid states
        invalid_states = [
            "",           # empty
            "short",      # too short
            "invalid chars!@#",  # invalid characters
            None,         # None value
        ]
        
        for invalid_state in invalid_states:
            if invalid_state is not None:
                is_valid = validate_oauth_state(invalid_state)
                assert not is_valid, f"Invalid OAuth state should be rejected: '{invalid_state}'"
    
    def test_oauth_scope_validation(self):
        """Test OAuth scope configuration and validation."""
        
        def validate_oauth_scopes(scopes: list) -> Tuple[bool, str]:
            """Mock OAuth scopes validation."""
            if not scopes:
                return False, "No scopes provided"
            
            if not isinstance(scopes, list):
                return False, "Scopes must be a list"
            
            # Check for required scopes
            required_scopes = ["openid", "email"]
            for required_scope in required_scopes:
                if required_scope not in scopes:
                    return False, f"Missing required scope: {required_scope}"
            
            # Check for valid scope format
            for scope in scopes:
                if not isinstance(scope, str) or not scope.strip():
                    return False, f"Invalid scope format: {scope}"
            
            return True, "Valid scopes"
        
        # Test scope scenarios
        scope_tests = [
            (["openid", "email"], True),                           # minimal valid
            (["openid", "email", "profile"], True),               # common scopes
            ([], False),                                           # empty scopes
            (["email"], False),                                    # missing openid
            (["openid"], False),                                   # missing email
            (["openid", "email", ""], False),                     # empty scope string
            ("not_a_list", False),                                 # wrong type
            (["openid", "email", None], False),                   # None in list
        ]
        
        for scopes, expected_valid in scope_tests:
            is_valid, reason = validate_oauth_scopes(scopes)
            assert is_valid == expected_valid, (
                f"OAuth scopes validation failed: scopes={scopes}, "
                f"expected {expected_valid}, reason: {reason}"
            )
    
    def test_oauth_token_security_validation(self):
        """Test OAuth token handling security requirements."""
        
        def validate_oauth_token_security(
            access_token: Optional[str], 
            refresh_token: Optional[str],
            expires_in: Optional[int]
        ) -> Tuple[bool, str]:
            """Mock OAuth token security validation."""
            
            # Access token validation
            if not access_token:
                return False, "Access token is required"
            
            if len(access_token) < 20:  # Reasonable minimum
                return False, "Access token too short"
            
            # Refresh token validation (if provided)
            if refresh_token is not None:
                if len(refresh_token) < 20:
                    return False, "Refresh token too short"
            
            # Token expiration validation
            if expires_in is not None:
                if expires_in <= 0:
                    return False, "Token expiration must be positive"
                if expires_in > 86400:  # 24 hours max
                    return False, "Token expiration too long for security"
            
            return True, "Valid token security"
        
        # Test token security scenarios
        token_tests = [
            ("valid_access_token_1234567890", "valid_refresh_token_1234567890", 3600, True),
            ("", "valid_refresh_token_1234567890", 3600, False),              # empty access token
            ("short", "valid_refresh_token_1234567890", 3600, False),         # access token too short
            ("valid_access_token_1234567890", "short", 3600, False),          # refresh token too short
            ("valid_access_token_1234567890", None, 3600, True),              # no refresh token (OK)
            ("valid_access_token_1234567890", "valid_refresh_token_1234567890", 0, False),     # invalid expiration
            ("valid_access_token_1234567890", "valid_refresh_token_1234567890", 100000, False), # expiration too long
            ("valid_access_token_1234567890", "valid_refresh_token_1234567890", None, True),   # no expiration (OK)
        ]
        
        for access_token, refresh_token, expires_in, expected_valid in token_tests:
            is_valid, reason = validate_oauth_token_security(access_token, refresh_token, expires_in)
            assert is_valid == expected_valid, (
                f"OAuth token security validation failed: "
                f"access='{access_token}', refresh='{refresh_token}', "
                f"expires={expires_in}, expected {expected_valid}, reason: {reason}"
            )


class TestOAuthProviderConfiguration:
    """Test multi-provider OAuth configuration."""
    
    def test_multiple_oauth_providers_configuration(self):
        """Test configuration for multiple OAuth providers."""
        
        def validate_multi_provider_config(providers_config: Dict[str, Dict]) -> Tuple[bool, str]:
            """Mock multi-provider OAuth configuration validation."""
            
            if not providers_config:
                return False, "No OAuth providers configured"
            
            required_fields = ["client_id", "client_secret"]
            
            for provider_name, provider_config in providers_config.items():
                if not isinstance(provider_config, dict):
                    return False, f"Invalid config format for {provider_name}"
                
                # Check required fields
                for field in required_fields:
                    if field not in provider_config or not provider_config[field]:
                        return False, f"Missing {field} for {provider_name}"
                
                # Provider-specific validation
                if provider_name == "google":
                    client_id = provider_config["client_id"]
                    if not client_id.endswith('.googleusercontent.com'):
                        return False, f"Invalid Google client_id format: {client_id}"
                
                elif provider_name == "github":
                    client_id = provider_config["client_id"]
                    if len(client_id) < 20:  # GitHub client IDs are typically 20 chars
                        return False, f"Invalid GitHub client_id length: {len(client_id)}"
            
            return True, "Valid multi-provider configuration"
        
        # Test multi-provider scenarios
        multi_provider_tests = [
            # Valid configurations
            ({
                "google": {
                    "client_id": "123456789012345678901234567890123456789012.googleusercontent.com",
                    "client_secret": "GOCSPX-valid_google_secret_123"
                }
            }, True),
            
            ({
                "google": {
                    "client_id": "123456789012345678901234567890123456789012.googleusercontent.com",
                    "client_secret": "GOCSPX-valid_google_secret_123"
                },
                "github": {
                    "client_id": "github_client_id_123456",
                    "client_secret": "github_client_secret_abcdefghijklmnop"
                }
            }, True),
            
            # Invalid configurations
            ({}, False),  # No providers
            
            ({
                "google": {
                    "client_id": "",  # Empty client ID
                    "client_secret": "valid_secret"
                }
            }, False),
            
            ({
                "google": {
                    "client_id": "invalid_google_client_id",  # Wrong format
                    "client_secret": "valid_secret"
                }
            }, False),
            
            ({
                "github": {
                    "client_id": "short",  # Too short for GitHub
                    "client_secret": "valid_secret"
                }
            }, False),
        ]
        
        for config, expected_valid in multi_provider_tests:
            is_valid, reason = validate_multi_provider_config(config)
            assert is_valid == expected_valid, (
                f"Multi-provider OAuth config validation failed: "
                f"config={config}, expected {expected_valid}, reason: {reason}"
            )
    
    def test_oauth_provider_fallback_configuration(self):
        """Test OAuth provider fallback and degradation strategies."""
        
        def validate_oauth_fallback_strategy(
            primary_providers: list, 
            fallback_providers: list,
            allow_local_auth: bool
        ) -> Tuple[bool, str]:
            """Mock OAuth fallback strategy validation."""
            
            all_providers = primary_providers + fallback_providers
            
            # Must have at least one authentication method
            if not all_providers and not allow_local_auth:
                return False, "No authentication methods available"
            
            # Validate provider names
            valid_providers = ["google", "github", "microsoft"]
            for provider in all_providers:
                if provider not in valid_providers:
                    return False, f"Unknown OAuth provider: {provider}"
            
            # No duplicate providers
            if len(set(all_providers)) != len(all_providers):
                return False, "Duplicate providers in configuration"
            
            return True, "Valid fallback strategy"
        
        # Test fallback scenarios
        fallback_tests = [
            (["google"], [], True, True),                    # Google primary, local fallback
            (["google", "github"], [], False, True),        # Multiple primary providers
            (["google"], ["github"], False, True),          # Primary and fallback providers
            ([], [], False, False),                          # No auth methods
            ([], [], True, True),                           # Only local auth
            (["invalid"], [], True, False),                 # Invalid provider
            (["google", "google"], [], True, False),        # Duplicate providers
        ]
        
        for primary, fallback, local_auth, expected_valid in fallback_tests:
            is_valid, reason = validate_oauth_fallback_strategy(primary, fallback, local_auth)
            assert is_valid == expected_valid, (
                f"OAuth fallback strategy validation failed: "
                f"primary={primary}, fallback={fallback}, local={local_auth}, "
                f"expected {expected_valid}, reason: {reason}"
            )