"""
Central Authentication Constants Module

SSOT (Single Source of Truth) for all auth-related string literals.
Business Value: Platform/Internal - Security & Stability - Centralizes auth configuration
to reduce security vulnerabilities and ensure consistent authentication across services.

All authentication-related constants are defined here to prevent duplication
and ensure consistency across the entire codebase.

Usage:
    from netra_backend.app.core.auth_constants import AuthConstants, JWTConstants, HeaderConstants
    
    # Use constants instead of hardcoded strings
    headers = {HeaderConstants.AUTHORIZATION: f"{HeaderConstants.BEARER_PREFIX}{token}"}
"""

from typing import Final


class AuthConstants:
    """Core authentication constants."""
    
    # Service endpoints
    AUTH_SERVICE_URL: Final[str] = "auth_service_url"
    AUTH_SERVICE_ENABLED: Final[str] = "auth_service_enabled" 
    AUTH_FAST_TEST_MODE: Final[str] = "auth_fast_test_mode"
    AUTH_CACHE_TTL_SECONDS: Final[str] = "auth_cache_ttl_seconds"
    
    # Service identification
    SERVICE_ID: Final[str] = "service_id"
    SERVICE_SECRET: Final[str] = "service_secret"
    
    # OAuth endpoints and URIs
    TOKEN_URI: Final[str] = "https://oauth2.googleapis.com/token"
    AUTH_URI: Final[str] = "https://accounts.google.com/o/oauth2/v2/auth"
    USERINFO_ENDPOINT: Final[str] = "https://www.googleapis.com/oauth2/userinfo"
    
    # OAuth scopes
    OAUTH_SCOPES: Final[list[str]] = ["openid", "email", "profile"]
    
    # Environment detection
    TESTING_FLAG: Final[str] = "testing"
    PYTEST_CURRENT_TEST: Final[str] = "pytest_current_test"
    
    # Cloud Run variables
    K_SERVICE: Final[str] = "k_service"
    K_REVISION: Final[str] = "k_revision"
    
    # PR environment
    PR_NUMBER: Final[str] = "pr_number"


class JWTConstants:
    """JWT token-related constants."""
    
    # Environment variables
    JWT_SECRET_KEY: Final[str] = "JWT_SECRET_KEY"
    SECRET_KEY: Final[str] = "SECRET_KEY"
    FERNET_KEY: Final[str] = "FERNET_KEY"
    
    # Token fields
    ACCESS_TOKEN: Final[str] = "access_token"
    REFRESH_TOKEN: Final[str] = "refresh_token"
    TOKEN_TYPE: Final[str] = "token_type"
    EXPIRES_IN: Final[str] = "expires_in"
    
    # Token types
    ACCESS_TOKEN_TYPE: Final[str] = "access"
    REFRESH_TOKEN_TYPE: Final[str] = "refresh"
    SERVICE_TOKEN_TYPE: Final[str] = "service"
    
    # JWT payload fields
    SUBJECT: Final[str] = "sub"
    EMAIL: Final[str] = "email"
    ISSUED_AT: Final[str] = "iat"
    EXPIRES_AT: Final[str] = "exp"
    ISSUER: Final[str] = "iss"
    PERMISSIONS: Final[str] = "permissions"
    
    # Issuer values
    NETRA_AUTH_SERVICE: Final[str] = "netra-auth-service"
    
    # Algorithms
    HS256_ALGORITHM: Final[str] = "HS256"
    
    # Default values
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES: Final[int] = 30
    DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS: Final[int] = 7


class HeaderConstants:
    """HTTP header constants."""
    
    AUTHORIZATION: Final[str] = "Authorization"
    CONTENT_TYPE: Final[str] = "Content-Type"
    USER_AGENT: Final[str] = "User-Agent"
    X_FORWARDED_FOR: Final[str] = "X-Forwarded-For"
    
    # Authorization prefixes
    BEARER_PREFIX: Final[str] = "Bearer "
    BASIC_PREFIX: Final[str] = "Basic "
    
    # Content types
    APPLICATION_JSON: Final[str] = "application/json"
    APPLICATION_FORM_URLENCODED: Final[str] = "application/x-www-form-urlencoded"


class CredentialConstants:
    """OAuth and API credential constants."""
    
    # Google OAuth environment variables
    # TOMBSTONE: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET superseded by environment-specific variables
    GOOGLE_CLIENT_ID: Final[str] = "OAUTH_GOOGLE_CLIENT_ID_ENV"  # Updated to new naming convention
    GOOGLE_CLIENT_SECRET: Final[str] = "OAUTH_GOOGLE_CLIENT_SECRET_ENV"  # Updated to new naming convention
    GOOGLE_OAUTH_CLIENT_ID: Final[str] = "OAUTH_GOOGLE_CLIENT_ID_ENV"  # Alias for consistency
    GOOGLE_OAUTH_CLIENT_SECRET: Final[str] = "OAUTH_GOOGLE_CLIENT_SECRET_ENV"  # Alias for consistency
    
    # API keys
    API_KEY: Final[str] = "api_key"
    GEMINI_API_KEY: Final[str] = "GEMINI_API_KEY"
    
    # Database credentials
    REDIS_URL: Final[str] = "REDIS_URL"
    REDIS_PASSWORD: Final[str] = "REDIS_PASSWORD"
    
    # Password field
    PASSWORD: Final[str] = "password"


class AuthErrorConstants:
    """Authentication error message constants."""
    
    # Error codes
    UNAUTHORIZED: Final[str] = "unauthorized"
    FORBIDDEN: Final[str] = "forbidden"
    TOKEN_EXPIRED: Final[str] = "token_expired"
    TOKEN_INVALID: Final[str] = "token_invalid"
    INVALID_CREDENTIALS: Final[str] = "invalid_credentials"
    MISSING_TOKEN: Final[str] = "missing_token"
    
    # Error messages
    UNAUTHORIZED_MESSAGE: Final[str] = "Authentication required"
    FORBIDDEN_MESSAGE: Final[str] = "Access denied"
    TOKEN_EXPIRED_MESSAGE: Final[str] = "Token has expired"
    TOKEN_INVALID_MESSAGE: Final[str] = "Invalid token"
    INVALID_CREDENTIALS_MESSAGE: Final[str] = "Invalid username or password"
    MISSING_TOKEN_MESSAGE: Final[str] = "Authentication token is required"
    
    # Service error messages
    AUTH_SERVICE_UNAVAILABLE: Final[str] = "Authentication service unavailable"
    AUTH_SERVICE_ERROR: Final[str] = "Authentication service error"


class OAuthConstants:
    """OAuth-specific constants."""
    
    # OAuth grant types
    AUTHORIZATION_CODE: Final[str] = "authorization_code"
    REFRESH_TOKEN_GRANT: Final[str] = "refresh_token"
    
    # OAuth response types
    CODE: Final[str] = "code"
    
    # OAuth parameters
    CLIENT_ID: Final[str] = "client_id"
    CLIENT_SECRET: Final[str] = "client_secret"
    REDIRECT_URI: Final[str] = "redirect_uri"
    SCOPE: Final[str] = "scope"
    STATE: Final[str] = "state"
    CODE_VERIFIER: Final[str] = "code_verifier"
    CODE_CHALLENGE: Final[str] = "code_challenge"
    CODE_CHALLENGE_METHOD: Final[str] = "code_challenge_method"
    
    # OAuth URLs and paths
    OAUTH_CALLBACK_PATH: Final[str] = "/auth/callback"
    OAUTH_LOGIN_PATH: Final[str] = "/auth/login"
    OAUTH_LOGOUT_PATH: Final[str] = "/auth/logout"
    
    # OAuth provider names
    GOOGLE: Final[str] = "google"
    GITHUB: Final[str] = "github"


class CacheConstants:
    """Authentication cache-related constants."""
    
    # Cache keys
    USER_TOKEN_PREFIX: Final[str] = "user_token:"
    SERVICE_TOKEN_PREFIX: Final[str] = "service_token:"
    USER_PROFILE_PREFIX: Final[str] = "user_profile:"
    
    # Cache TTL (in seconds)
    DEFAULT_TOKEN_CACHE_TTL: Final[int] = 300  # 5 minutes
    USER_PROFILE_CACHE_TTL: Final[int] = 900   # 15 minutes
    SERVICE_TOKEN_CACHE_TTL: Final[int] = 1800 # 30 minutes


class ValidationConstants:
    """Authentication validation constants."""
    
    # Password requirements
    MIN_PASSWORD_LENGTH: Final[int] = 8
    MAX_PASSWORD_LENGTH: Final[int] = 128
    
    # Token validation
    MIN_TOKEN_LENGTH: Final[int] = 10
    MAX_TOKEN_LENGTH: Final[int] = 2048
    
    # Email validation
    EMAIL_REGEX: Final[str] = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    MAX_EMAIL_LENGTH: Final[int] = 254


# Module-level exports for backward compatibility
JWT_SECRET_KEY = JWTConstants.JWT_SECRET_KEY
SECRET_KEY = JWTConstants.SECRET_KEY
AUTHORIZATION = HeaderConstants.AUTHORIZATION
BEARER_PREFIX = HeaderConstants.BEARER_PREFIX


# Convenience export of all constant classes
__all__ = [
    'AuthConstants',
    'JWTConstants', 
    'HeaderConstants',
    'CredentialConstants',
    'AuthErrorConstants',
    'OAuthConstants',
    'CacheConstants',
    'ValidationConstants',
    # Module-level exports for backward compatibility
    'JWT_SECRET_KEY',
    'SECRET_KEY',
    'AUTHORIZATION',
    'BEARER_PREFIX'
]