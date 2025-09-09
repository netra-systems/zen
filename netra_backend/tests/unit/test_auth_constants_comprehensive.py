"""
Comprehensive Unit Tests for auth_constants.py - AUTH SSOT Constants

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Auth is the foundation of Golden Path
- Business Goal: Prevent CASCADE FAILURES from auth configuration errors
- Value Impact: Authentication enables $50K+ MRR from AI optimization services
- Strategic Impact: AUTH CONSTANTS are CRITICAL - one wrong constant breaks entire platform

MISSION CRITICAL: Auth constants enable the Golden Path by providing centralized
string literals that prevent typos and ensure consistent authentication across
all services. Without proper auth constants, users cannot access AI services.

Tests validate:
1. All auth constant values are proper strings and types
2. OAuth constants match external provider requirements  
3. JWT constants align with industry standards
4. Header constants prevent HTTP authentication failures
5. Error constants enable proper user feedback
6. Cache constants optimize auth performance
7. Validation constants enforce security requirements

These tests prevent AUTH CASCADE FAILURES that break the entire system.
"""

import pytest
import re
from typing import Final

from netra_backend.app.core.auth_constants import (
    AuthConstants,
    JWTConstants,
    HeaderConstants,
    CredentialConstants,
    AuthErrorConstants,
    OAuthConstants,
    CacheConstants,
    ValidationConstants
)


class TestAuthConstants:
    """Test core authentication constants for SSOT compliance."""

    def test_auth_service_url_constant_type(self):
        """Test AUTH_SERVICE_URL is proper string constant."""
        assert isinstance(AuthConstants.AUTH_SERVICE_URL, str)
        assert AuthConstants.AUTH_SERVICE_URL == "auth_service_url"
        # Verify it's a Final type constant
        assert hasattr(AuthConstants, '__annotations__')

    def test_auth_service_enabled_constant_type(self):
        """Test AUTH_SERVICE_ENABLED is proper string constant."""
        assert isinstance(AuthConstants.AUTH_SERVICE_ENABLED, str)
        assert AuthConstants.AUTH_SERVICE_ENABLED == "auth_service_enabled"

    def test_auth_fast_test_mode_constant_type(self):
        """Test AUTH_FAST_TEST_MODE is proper string constant."""
        assert isinstance(AuthConstants.AUTH_FAST_TEST_MODE, str)
        assert AuthConstants.AUTH_FAST_TEST_MODE == "auth_fast_test_mode"

    def test_auth_cache_ttl_constant_type(self):
        """Test AUTH_CACHE_TTL_SECONDS is proper string constant."""
        assert isinstance(AuthConstants.AUTH_CACHE_TTL_SECONDS, str)
        assert AuthConstants.AUTH_CACHE_TTL_SECONDS == "auth_cache_ttl_seconds"

    def test_service_identification_constants_business_critical(self):
        """Test service identification constants prevent inter-service auth failures."""
        # SERVICE_ID constant must be valid string
        assert isinstance(AuthConstants.SERVICE_ID, str)
        assert AuthConstants.SERVICE_ID == "service_id"
        
        # SERVICE_SECRET constant must be valid string
        assert isinstance(AuthConstants.SERVICE_SECRET, str)  
        assert AuthConstants.SERVICE_SECRET == "service_secret"

    def test_oauth_endpoint_constants_match_google_specs(self):
        """Test OAuth constants match Google OAuth 2.0 specifications."""
        # TOKEN_URI must match Google's OAuth token endpoint
        assert AuthConstants.TOKEN_URI == "https://oauth2.googleapis.com/token"
        assert AuthConstants.TOKEN_URI.startswith("https://")
        
        # AUTH_URI must match Google's OAuth authorization endpoint
        assert AuthConstants.AUTH_URI == "https://accounts.google.com/o/oauth2/v2/auth"
        assert AuthConstants.AUTH_URI.startswith("https://")
        
        # USERINFO_ENDPOINT must match Google's userinfo API
        assert AuthConstants.USERINFO_ENDPOINT == "https://www.googleapis.com/oauth2/userinfo"
        assert AuthConstants.USERINFO_ENDPOINT.startswith("https://")

    def test_oauth_scopes_are_valid_google_scopes(self):
        """Test OAuth scopes are valid Google OAuth scopes."""
        assert isinstance(AuthConstants.OAUTH_SCOPES, list)
        expected_scopes = ["openid", "email", "profile"]
        assert AuthConstants.OAUTH_SCOPES == expected_scopes
        
        # Verify all scopes are valid strings
        for scope in AuthConstants.OAUTH_SCOPES:
            assert isinstance(scope, str)
            assert len(scope) > 0

    def test_environment_detection_constants_prevent_misconfigurations(self):
        """Test environment detection constants prevent deployment misconfigurations."""
        # TESTING_FLAG constant
        assert isinstance(AuthConstants.TESTING_FLAG, str)
        assert AuthConstants.TESTING_FLAG == "testing"
        
        # PYTEST_CURRENT_TEST constant  
        assert isinstance(AuthConstants.PYTEST_CURRENT_TEST, str)
        assert AuthConstants.PYTEST_CURRENT_TEST == "pytest_current_test"

    def test_cloud_run_variables_for_gcp_deployment(self):
        """Test Cloud Run variables for proper GCP deployment detection."""
        # K_SERVICE for Cloud Run service detection
        assert isinstance(AuthConstants.K_SERVICE, str)
        assert AuthConstants.K_SERVICE == "k_service"
        
        # K_REVISION for Cloud Run revision detection
        assert isinstance(AuthConstants.K_REVISION, str)
        assert AuthConstants.K_REVISION == "k_revision"

    def test_pr_environment_variable_for_staging(self):
        """Test PR_NUMBER variable for staging environment detection."""
        assert isinstance(AuthConstants.PR_NUMBER, str)
        assert AuthConstants.PR_NUMBER == "pr_number"


class TestJWTConstants:
    """Test JWT constants for token security and standards compliance."""

    def test_jwt_secret_key_constants_prevent_configuration_errors(self):
        """Test JWT secret constants prevent cascade failures from missing secrets."""
        # JWT_SECRET_KEY constant
        assert isinstance(JWTConstants.JWT_SECRET_KEY, str)
        assert JWTConstants.JWT_SECRET_KEY == "JWT_SECRET_KEY"
        
        # SECRET_KEY fallback constant
        assert isinstance(JWTConstants.SECRET_KEY, str)
        assert JWTConstants.SECRET_KEY == "SECRET_KEY"
        
        # FERNET_KEY for encryption
        assert isinstance(JWTConstants.FERNET_KEY, str)
        assert JWTConstants.FERNET_KEY == "FERNET_KEY"

    def test_token_field_constants_match_oauth2_spec(self):
        """Test token field constants match OAuth 2.0 specification."""
        # Standard OAuth 2.0 token fields
        assert JWTConstants.ACCESS_TOKEN == "access_token"
        assert JWTConstants.REFRESH_TOKEN == "refresh_token" 
        assert JWTConstants.TOKEN_TYPE == "token_type"
        assert JWTConstants.EXPIRES_IN == "expires_in"

    def test_token_type_constants_are_industry_standard(self):
        """Test token type constants follow industry standards."""
        assert JWTConstants.ACCESS_TOKEN_TYPE == "access"
        assert JWTConstants.REFRESH_TOKEN_TYPE == "refresh"
        assert JWTConstants.SERVICE_TOKEN_TYPE == "service"

    def test_jwt_payload_fields_match_rfc7519_standard(self):
        """Test JWT payload fields match RFC 7519 JWT standard."""
        # Standard JWT claims from RFC 7519
        assert JWTConstants.SUBJECT == "sub"  # Subject
        assert JWTConstants.ISSUED_AT == "iat"  # Issued At
        assert JWTConstants.EXPIRES_AT == "exp"  # Expires At
        assert JWTConstants.ISSUER == "iss"  # Issuer
        
        # Custom claims
        assert JWTConstants.EMAIL == "email"
        assert JWTConstants.PERMISSIONS == "permissions"

    def test_issuer_values_identify_netra_services(self):
        """Test issuer values properly identify Netra auth services."""
        assert JWTConstants.NETRA_AUTH_SERVICE == "netra-auth-service"
        assert "netra" in JWTConstants.NETRA_AUTH_SERVICE
        assert "auth" in JWTConstants.NETRA_AUTH_SERVICE

    def test_jwt_algorithm_is_secure_standard(self):
        """Test JWT algorithm is secure industry standard."""
        assert JWTConstants.HS256_ALGORITHM == "HS256"
        # HS256 is secure HMAC algorithm recommended for JWT

    def test_default_token_expiry_times_are_secure(self):
        """Test default token expiry times follow security best practices."""
        # Access tokens should be short-lived (30 minutes is secure)
        assert isinstance(JWTConstants.DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert JWTConstants.DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert 15 <= JWTConstants.DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES <= 60  # Security range
        
        # Refresh tokens should be longer-lived (7 days is reasonable)
        assert isinstance(JWTConstants.DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS, int)
        assert JWTConstants.DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert 7 <= JWTConstants.DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS <= 30  # Security range


class TestHeaderConstants:
    """Test HTTP header constants prevent authentication header errors."""

    def test_standard_http_headers_match_rfc_specs(self):
        """Test HTTP header constants match RFC specifications."""
        # Standard HTTP headers from RFCs
        assert HeaderConstants.AUTHORIZATION == "Authorization"
        assert HeaderConstants.CONTENT_TYPE == "Content-Type" 
        assert HeaderConstants.USER_AGENT == "User-Agent"
        assert HeaderConstants.X_FORWARDED_FOR == "X-Forwarded-For"

    def test_authorization_prefixes_match_auth_schemes(self):
        """Test authorization prefixes match standard auth schemes."""
        # Bearer token prefix (OAuth 2.0 standard)
        assert HeaderConstants.BEARER_PREFIX == "Bearer "
        assert HeaderConstants.BEARER_PREFIX.endswith(" ")  # Must include space
        
        # Basic auth prefix (RFC 7617 standard)
        assert HeaderConstants.BASIC_PREFIX == "Basic "
        assert HeaderConstants.BASIC_PREFIX.endswith(" ")  # Must include space

    def test_content_type_constants_prevent_media_type_errors(self):
        """Test content type constants prevent HTTP media type errors."""
        # JSON content type
        assert HeaderConstants.APPLICATION_JSON == "application/json"
        
        # Form content type
        assert HeaderConstants.APPLICATION_FORM_URLENCODED == "application/x-www-form-urlencoded"


class TestCredentialConstants:
    """Test credential constants prevent OAuth configuration failures."""

    def test_google_oauth_credential_constants_prevent_misconfigurations(self):
        """Test Google OAuth constants prevent environment variable misconfigurations."""
        # Updated Google OAuth environment variables
        assert CredentialConstants.GOOGLE_CLIENT_ID == "OAUTH_GOOGLE_CLIENT_ID_ENV"
        assert CredentialConstants.GOOGLE_CLIENT_SECRET == "OAUTH_GOOGLE_CLIENT_SECRET_ENV"
        
        # Aliases for consistency
        assert CredentialConstants.GOOGLE_OAUTH_CLIENT_ID == "OAUTH_GOOGLE_CLIENT_ID_ENV"
        assert CredentialConstants.GOOGLE_OAUTH_CLIENT_SECRET == "OAUTH_GOOGLE_CLIENT_SECRET_ENV"

    def test_api_key_constants_are_properly_defined(self):
        """Test API key constants are properly defined for service authentication."""
        # Generic API key constant
        assert isinstance(CredentialConstants.API_KEY, str)
        assert CredentialConstants.API_KEY == "api_key"
        
        # Gemini API key constant
        assert isinstance(CredentialConstants.GEMINI_API_KEY, str)
        assert CredentialConstants.GEMINI_API_KEY == "GEMINI_API_KEY"

    def test_database_credential_constants_prevent_connection_failures(self):
        """Test database credential constants prevent Redis connection failures."""
        assert CredentialConstants.REDIS_URL == "REDIS_URL"
        assert CredentialConstants.REDIS_PASSWORD == "REDIS_PASSWORD"

    def test_password_field_constant_consistency(self):
        """Test password field constant for form consistency."""
        assert CredentialConstants.PASSWORD == "password"


class TestAuthErrorConstants:
    """Test auth error constants enable proper user feedback."""

    def test_error_codes_are_standard_http_semantics(self):
        """Test error codes follow standard HTTP authentication semantics."""
        # Standard HTTP auth error codes
        assert AuthErrorConstants.UNAUTHORIZED == "unauthorized"  # 401
        assert AuthErrorConstants.FORBIDDEN == "forbidden"  # 403
        assert AuthErrorConstants.TOKEN_EXPIRED == "token_expired"
        assert AuthErrorConstants.TOKEN_INVALID == "token_invalid" 
        assert AuthErrorConstants.INVALID_CREDENTIALS == "invalid_credentials"
        assert AuthErrorConstants.MISSING_TOKEN == "missing_token"

    def test_error_messages_provide_clear_user_guidance(self):
        """Test error messages provide clear guidance to users."""
        # User-friendly error messages
        assert AuthErrorConstants.UNAUTHORIZED_MESSAGE == "Authentication required"
        assert AuthErrorConstants.FORBIDDEN_MESSAGE == "Access denied"
        assert AuthErrorConstants.TOKEN_EXPIRED_MESSAGE == "Token has expired"
        assert AuthErrorConstants.TOKEN_INVALID_MESSAGE == "Invalid token"
        assert AuthErrorConstants.INVALID_CREDENTIALS_MESSAGE == "Invalid username or password"
        assert AuthErrorConstants.MISSING_TOKEN_MESSAGE == "Authentication token is required"

    def test_service_error_messages_help_debugging(self):
        """Test service error messages help with debugging cascade failures."""
        assert AuthErrorConstants.AUTH_SERVICE_UNAVAILABLE == "Authentication service unavailable"
        assert AuthErrorConstants.AUTH_SERVICE_ERROR == "Authentication service error"


class TestOAuthConstants:
    """Test OAuth constants match OAuth 2.0 specification."""

    def test_oauth_grant_types_match_rfc6749(self):
        """Test OAuth grant types match RFC 6749 OAuth 2.0 spec."""
        # Standard OAuth 2.0 grant types from RFC 6749
        assert OAuthConstants.AUTHORIZATION_CODE == "authorization_code"
        assert OAuthConstants.REFRESH_TOKEN_GRANT == "refresh_token"

    def test_oauth_response_types_match_spec(self):
        """Test OAuth response types match OAuth 2.0 specification."""
        assert OAuthConstants.CODE == "code"  # Authorization code flow

    def test_oauth_parameter_names_match_rfc6749(self):
        """Test OAuth parameter names match RFC 6749 specification."""
        # Standard OAuth 2.0 parameters from RFC 6749
        assert OAuthConstants.CLIENT_ID == "client_id"
        assert OAuthConstants.CLIENT_SECRET == "client_secret"
        assert OAuthConstants.REDIRECT_URI == "redirect_uri"
        assert OAuthConstants.SCOPE == "scope"
        assert OAuthConstants.STATE == "state"
        
        # PKCE parameters from RFC 7636
        assert OAuthConstants.CODE_VERIFIER == "code_verifier"
        assert OAuthConstants.CODE_CHALLENGE == "code_challenge"
        assert OAuthConstants.CODE_CHALLENGE_METHOD == "code_challenge_method"

    def test_oauth_url_paths_are_standard_endpoints(self):
        """Test OAuth URL paths are standard endpoint patterns."""
        assert OAuthConstants.OAUTH_CALLBACK_PATH == "/auth/callback"
        assert OAuthConstants.OAUTH_LOGIN_PATH == "/auth/login"
        assert OAuthConstants.OAUTH_LOGOUT_PATH == "/auth/logout"
        
        # All paths start with /auth
        assert OAuthConstants.OAUTH_CALLBACK_PATH.startswith("/auth")
        assert OAuthConstants.OAUTH_LOGIN_PATH.startswith("/auth")
        assert OAuthConstants.OAUTH_LOGOUT_PATH.startswith("/auth")

    def test_oauth_provider_names_match_services(self):
        """Test OAuth provider names match external service names."""
        assert OAuthConstants.GOOGLE == "google"
        assert OAuthConstants.GITHUB == "github"


class TestCacheConstants:
    """Test cache constants optimize auth performance without breaking security."""

    def test_cache_key_prefixes_prevent_key_collisions(self):
        """Test cache key prefixes prevent key collisions in Redis."""
        # Cache key prefixes must end with colon for proper namespacing
        assert CacheConstants.USER_TOKEN_PREFIX == "user_token:"
        assert CacheConstants.USER_TOKEN_PREFIX.endswith(":")
        
        assert CacheConstants.SERVICE_TOKEN_PREFIX == "service_token:"
        assert CacheConstants.SERVICE_TOKEN_PREFIX.endswith(":")
        
        assert CacheConstants.USER_PROFILE_PREFIX == "user_profile:"
        assert CacheConstants.USER_PROFILE_PREFIX.endswith(":")

    def test_cache_ttl_values_balance_performance_and_security(self):
        """Test cache TTL values balance performance with security requirements."""
        # Token cache TTL (5 minutes - good balance)
        assert isinstance(CacheConstants.DEFAULT_TOKEN_CACHE_TTL, int)
        assert CacheConstants.DEFAULT_TOKEN_CACHE_TTL == 300
        assert 300 <= CacheConstants.DEFAULT_TOKEN_CACHE_TTL <= 900  # 5-15 min range
        
        # User profile cache TTL (15 minutes - less sensitive data)
        assert isinstance(CacheConstants.USER_PROFILE_CACHE_TTL, int)
        assert CacheConstants.USER_PROFILE_CACHE_TTL == 900
        assert 300 <= CacheConstants.USER_PROFILE_CACHE_TTL <= 1800  # 5-30 min range
        
        # Service token cache TTL (30 minutes - inter-service tokens)
        assert isinstance(CacheConstants.SERVICE_TOKEN_CACHE_TTL, int)
        assert CacheConstants.SERVICE_TOKEN_CACHE_TTL == 1800
        assert 900 <= CacheConstants.SERVICE_TOKEN_CACHE_TTL <= 3600  # 15-60 min range


class TestValidationConstants:
    """Test validation constants enforce security requirements."""

    def test_password_length_requirements_meet_security_standards(self):
        """Test password length requirements meet NIST security standards."""
        # NIST recommends minimum 8 characters
        assert isinstance(ValidationConstants.MIN_PASSWORD_LENGTH, int)
        assert ValidationConstants.MIN_PASSWORD_LENGTH == 8
        assert ValidationConstants.MIN_PASSWORD_LENGTH >= 8
        
        # Maximum length prevents DoS attacks
        assert isinstance(ValidationConstants.MAX_PASSWORD_LENGTH, int)
        assert ValidationConstants.MAX_PASSWORD_LENGTH == 128
        assert ValidationConstants.MAX_PASSWORD_LENGTH >= 64

    def test_token_length_requirements_prevent_attacks(self):
        """Test token length requirements prevent brute force and DoS attacks."""
        # Minimum token length prevents brute force
        assert isinstance(ValidationConstants.MIN_TOKEN_LENGTH, int)
        assert ValidationConstants.MIN_TOKEN_LENGTH == 10
        assert ValidationConstants.MIN_TOKEN_LENGTH >= 10
        
        # Maximum token length prevents DoS attacks
        assert isinstance(ValidationConstants.MAX_TOKEN_LENGTH, int)
        assert ValidationConstants.MAX_TOKEN_LENGTH == 2048
        assert ValidationConstants.MAX_TOKEN_LENGTH >= 1000

    def test_email_validation_constants_prevent_injection_attacks(self):
        """Test email validation constants prevent injection attacks."""
        # Email regex pattern is secure
        assert isinstance(ValidationConstants.EMAIL_REGEX, str)
        email_pattern = ValidationConstants.EMAIL_REGEX
        assert "^" in email_pattern  # Anchored at start
        assert "$" in email_pattern  # Anchored at end
        
        # Test the regex works
        import re
        pattern = re.compile(email_pattern)
        assert pattern.match("test@example.com") is not None
        assert pattern.match("invalid-email") is None
        
        # Email length prevents DoS attacks
        assert isinstance(ValidationConstants.MAX_EMAIL_LENGTH, int)
        assert ValidationConstants.MAX_EMAIL_LENGTH == 254  # RFC 5321 standard


class TestConstantModuleExports:
    """Test that all constant classes are properly exported from the module."""

    def test_all_constant_classes_are_exported(self):
        """Test that __all__ exports all constant classes."""
        from netra_backend.app.core.auth_constants import __all__
        
        expected_exports = [
            'AuthConstants',
            'JWTConstants', 
            'HeaderConstants',
            'CredentialConstants',
            'AuthErrorConstants',
            'OAuthConstants',
            'CacheConstants',
            'ValidationConstants'
        ]
        
        assert isinstance(__all__, list)
        assert set(__all__) == set(expected_exports)
        assert len(__all__) == len(expected_exports)

    def test_all_exported_classes_exist(self):
        """Test that all exported classes actually exist in the module."""
        from netra_backend.app.core.auth_constants import (
            AuthConstants, JWTConstants, HeaderConstants, CredentialConstants,
            AuthErrorConstants, OAuthConstants, CacheConstants, ValidationConstants
        )
        
        # Verify all classes exist and have expected attributes
        assert hasattr(AuthConstants, 'AUTH_SERVICE_URL')
        assert hasattr(JWTConstants, 'JWT_SECRET_KEY')
        assert hasattr(HeaderConstants, 'AUTHORIZATION')
        assert hasattr(CredentialConstants, 'GOOGLE_CLIENT_ID')
        assert hasattr(AuthErrorConstants, 'UNAUTHORIZED')
        assert hasattr(OAuthConstants, 'AUTHORIZATION_CODE')
        assert hasattr(CacheConstants, 'USER_TOKEN_PREFIX')
        assert hasattr(ValidationConstants, 'MIN_PASSWORD_LENGTH')


class TestAuthConstantsBusinessValueValidation:
    """Test that auth constants deliver the expected business value."""

    def test_constants_prevent_hardcoded_string_errors(self):
        """Test constants prevent hardcoded string typos that break auth."""
        # All constants should be non-empty strings
        for constant_name in dir(AuthConstants):
            if not constant_name.startswith('_'):
                value = getattr(AuthConstants, constant_name)
                if isinstance(value, str):
                    assert len(value) > 0, f"{constant_name} should not be empty string"

    def test_constants_enable_consistent_oauth_integration(self):
        """Test constants enable consistent OAuth integration across services."""
        # OAuth URLs must be HTTPS for security
        assert AuthConstants.TOKEN_URI.startswith("https://")
        assert AuthConstants.AUTH_URI.startswith("https://")  
        assert AuthConstants.USERINFO_ENDPOINT.startswith("https://")
        
        # OAuth scopes must be valid
        assert all(isinstance(scope, str) for scope in AuthConstants.OAUTH_SCOPES)
        assert "openid" in AuthConstants.OAUTH_SCOPES  # Required for OIDC

    def test_constants_support_multi_environment_deployments(self):
        """Test constants support staging, production, and test environments."""
        # Environment detection constants exist
        assert AuthConstants.TESTING_FLAG is not None
        assert AuthConstants.K_SERVICE is not None  # Cloud Run detection
        assert AuthConstants.PR_NUMBER is not None  # PR environment detection

    def test_constants_enable_auth_cascade_failure_prevention(self):
        """Test constants enable prevention of auth cascade failures."""
        # Service identification constants prevent inter-service auth failures
        assert AuthConstants.SERVICE_ID is not None
        assert AuthConstants.SERVICE_SECRET is not None
        
        # Error constants enable proper error handling
        assert AuthErrorConstants.AUTH_SERVICE_UNAVAILABLE is not None
        assert AuthErrorConstants.AUTH_SERVICE_ERROR is not None

    def test_constants_optimize_auth_performance_without_breaking_security(self):
        """Test cache constants optimize performance without compromising security."""
        # Cache TTLs are reasonable (not too long for security, not too short for performance)
        assert 60 <= CacheConstants.DEFAULT_TOKEN_CACHE_TTL <= 1800  # 1-30 minutes
        assert 300 <= CacheConstants.USER_PROFILE_CACHE_TTL <= 3600  # 5-60 minutes
        assert 600 <= CacheConstants.SERVICE_TOKEN_CACHE_TTL <= 7200  # 10-120 minutes