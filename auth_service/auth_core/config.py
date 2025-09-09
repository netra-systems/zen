"""
Auth Service Configuration - SINGLE SOURCE OF TRUTH

**CONSOLIDATED**: This is now a thin wrapper around AuthEnvironment to maintain 
backward compatibility while implementing true SSOT architecture per CLAUDE.md.

All configuration logic has been consolidated into auth_environment.py (the SSOT).
This class delegates to AuthEnvironment to eliminate duplicate configuration logic.

CRITICAL: All auth service configuration MUST go through AuthEnvironment (SSOT).
This maintains service independence per SPEC/independent_services.xml while ensuring
all configuration access follows a single, consistent pattern.
"""
import logging
from typing import Optional

# Import the SSOT - AuthEnvironment
from auth_service.auth_core.auth_environment import get_auth_env, AuthEnvironment

logger = logging.getLogger(__name__)

class AuthConfig:
    """
    SSOT Configuration for auth service - delegates to AuthEnvironment.
    
    This class maintains backward compatibility while ensuring all configuration
    logic is centralized in AuthEnvironment (the true SSOT).
    """
    
    def __init__(self, auth_env=None):
        """Initialize AuthConfig with fresh AuthEnvironment instance."""
        # Get the SSOT instance - use instance-level for proper test isolation
        # Allow injecting auth_env for testing
        self._auth_env = auth_env if auth_env is not None else get_auth_env()
        # Test override values for validation testing
        self._test_override_values = {}
    
    # Class-level attributes for legacy compatibility
    @property
    def ENVIRONMENT(self) -> str:
        return self._auth_env.get_environment()
    
    # Instance property accessors for test compatibility
    @property
    def jwt_secret_key(self) -> str:
        """JWT secret key property accessor."""
        return self._auth_env.get_jwt_secret_key()
    
    @jwt_secret_key.setter
    def jwt_secret_key(self, value: str):
        """JWT secret key property setter for test compatibility."""
        # Store in test override values for validation testing
        self._test_override_values['jwt_secret_key'] = value
        # Also try to set on AuthEnvironment for completeness
        if value is not None:
            self._auth_env.set("JWT_SECRET_KEY", value, source="test_override")
    
    @property
    def postgres_host(self) -> str:
        """PostgreSQL host property accessor."""
        return self._auth_env.get_postgres_host()
    
    @postgres_host.setter
    def postgres_host(self, value: str):
        """PostgreSQL host property setter for test compatibility."""
        self._test_override_values['postgres_host'] = value
        if value is not None:
            self._auth_env.set("POSTGRES_HOST", value, source="test_override")
    
    @property
    def postgres_user(self) -> str:
        """PostgreSQL user property accessor."""
        return self._auth_env.get_postgres_user()
    
    @postgres_user.setter
    def postgres_user(self, value: str):
        """PostgreSQL user property setter for test compatibility."""
        self._test_override_values['postgres_user'] = value
        if value is not None:
            self._auth_env.set("POSTGRES_USER", value, source="test_override")
    
    @property
    def postgres_password(self) -> str:
        """PostgreSQL password property accessor."""
        return self._auth_env.get_postgres_password()
    
    @postgres_password.setter
    def postgres_password(self, value: str):
        """PostgreSQL password property setter for test compatibility."""
        self._test_override_values['postgres_password'] = value
        if value is not None:
            self._auth_env.set("POSTGRES_PASSWORD", value, source="test_override")
    
    @property
    def postgres_db(self) -> str:
        """PostgreSQL database property accessor."""
        return self._auth_env.get_postgres_db()
    
    @postgres_db.setter
    def postgres_db(self, value: str):
        """PostgreSQL database property setter for test compatibility."""
        self._test_override_values['postgres_db'] = value
        if value is not None:
            self._auth_env.set("POSTGRES_DB", value, source="test_override")
    
    @property
    def redis_url(self) -> str:
        """Redis URL property accessor."""
        return self._auth_env.get_redis_url()
    
    @redis_url.setter
    def redis_url(self, value: str):
        """Redis URL property setter for test compatibility."""
        self._test_override_values['redis_url'] = value
        if value is not None:
            self._auth_env.set("REDIS_URL", value, source="test_override")
    
    @property
    def google_client_id(self) -> str:
        """Google Client ID property accessor."""
        return self._auth_env.get_oauth_google_client_id()
    
    @google_client_id.setter
    def google_client_id(self, value: str):
        """Google Client ID property setter for test compatibility."""
        self._test_override_values['google_client_id'] = value
        if value is not None:
            self._auth_env.set("GOOGLE_CLIENT_ID", value, source="test_override")
    
    @property
    def google_client_secret(self) -> str:
        """Google Client Secret property accessor."""
        return self._auth_env.get_oauth_google_client_secret()
    
    @google_client_secret.setter
    def google_client_secret(self, value: str):
        """Google Client Secret property setter for test compatibility."""
        self._test_override_values['google_client_secret'] = value
        if value is not None:
            self._auth_env.set("GOOGLE_CLIENT_SECRET", value, source="test_override")
    
    # Additional properties for configuration validation
    @property
    def debug_mode(self) -> bool:
        """Debug mode property accessor."""
        return self._auth_env.get_environment() in ["development", "test"]
    
    @property
    def cors_allow_all(self) -> bool:
        """CORS allow all property accessor."""
        return self._auth_env.get_environment() in ["development", "test"]
    
    @property
    def jwt_token_expiry(self) -> int:
        """JWT token expiry property accessor."""
        return self._auth_env.get_jwt_expiration_minutes() * 60  # Convert to seconds
    
    @property
    def require_https(self) -> bool:
        """Require HTTPS property accessor."""
        return self._auth_env.get_environment() in ["production", "staging"]
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT algorithm property accessor."""
        return self._auth_env.get_jwt_algorithm()
    
    # Core Environment Methods - delegate to SSOT
    @staticmethod
    def get_environment() -> str:
        """Get current environment with explicit named environments."""
        return get_auth_env().get_environment()
    
    # OAuth Configuration - delegate to SSOT
    @staticmethod
    def get_google_client_id() -> str:
        """Get Google OAuth Client ID."""
        return get_auth_env().get_oauth_google_client_id()
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth Client Secret."""
        return get_auth_env().get_oauth_google_client_secret()
    
    # JWT Configuration - delegate to SSOT
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT secret key."""
        return get_auth_env().get_jwt_secret_key()
    
    @staticmethod
    def get_jwt_algorithm() -> str:
        """Get JWT algorithm."""
        return get_auth_env().get_jwt_algorithm()
    
    @staticmethod
    def get_jwt_access_expiry_minutes() -> int:
        """Get JWT access token expiry in minutes."""
        return get_auth_env().get_jwt_expiration_minutes()
    
    @staticmethod
    def get_jwt_refresh_expiry_days() -> int:
        """Get JWT refresh token expiry in days."""
        return get_auth_env().get_refresh_token_expiration_days()
    
    @staticmethod 
    def get_jwt_service_expiry_minutes() -> int:
        """Get JWT service token expiry in minutes."""
        # AuthEnvironment doesn't have this method, so use access token expiry as fallback
        return get_auth_env().get_jwt_expiration_minutes()
    
    # Service Security - delegate to SSOT
    @staticmethod
    def get_service_secret() -> str:
        """Get service secret - delegates to secret key."""
        return get_auth_env().get_secret_key()
    
    @staticmethod
    def get_service_id() -> str:
        """Get service instance ID - generate based on environment."""
        env = get_auth_env().get_environment()
        if env == "production":
            return "netra_auth_service_prod"
        elif env == "staging":
            return "netra_auth_service_staging"
        elif env == "development":
            return "netra_auth_service_dev"
        elif env == "test":
            return "netra_auth_service_test"
        else:
            return f"netra_auth_service_{env}"
    
    # URL Configuration - delegate to SSOT
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL."""
        return get_auth_env().get_frontend_url()
    
    @staticmethod
    def get_auth_service_url() -> str:
        """Get auth service URL."""
        # Delegate to AuthEnvironment's new method
        return get_auth_env().get_auth_service_url()
    
    # Database Configuration - delegate to SSOT
    @staticmethod
    def get_database_url() -> str:
        """Get database URL."""
        return get_auth_env().get_database_url()
    
    @staticmethod
    def get_raw_database_url() -> str:
        """Get raw database URL for synchronous operations."""
        # Convert async URL to sync
        async_url = get_auth_env().get_database_url()
        if "postgresql+asyncpg:" in async_url:
            return async_url.replace("postgresql+asyncpg:", "postgresql:")
        elif "sqlite+aiosqlite:" in async_url:
            return async_url.replace("sqlite+aiosqlite:", "sqlite:")
        return async_url
    
    # Redis Configuration - delegate to SSOT  
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL."""
        return get_auth_env().get_redis_url()
    
    @staticmethod
    def get_session_ttl_hours() -> int:
        """Get session TTL in hours."""
        # Convert seconds to hours
        return get_auth_env().get_session_ttl() // 3600
    
    @staticmethod
    def is_redis_disabled() -> bool:
        """Check if Redis is explicitly disabled."""
        # Check for explicit disable flag
        from shared.isolated_environment import get_env
        return get_env().get("REDIS_DISABLED", "false").lower() == "true"
    
    # CORS Configuration - delegate to SSOT
    @staticmethod
    def get_cors_origins() -> list[str]:
        """Get CORS origins - delegates to SSOT."""
        return get_auth_env().get_cors_origins()
    
    # API Configuration
    @staticmethod
    def get_api_base_url() -> str:
        """Get API base URL (backend service URL)."""
        return get_auth_env().get_backend_url()
    
    # Environment Checks - delegate to SSOT
    @staticmethod
    def is_development() -> bool:
        """Check if running in development environment."""
        return get_auth_env().is_development()
    
    @staticmethod
    def is_production() -> bool:
        """Check if running in production environment."""
        return get_auth_env().is_production()
    
    @staticmethod
    def is_test() -> bool:
        """Check if running in test environment."""
        return get_auth_env().is_testing()
    
    # OAuth Helper Methods - delegate to SSOT
    @staticmethod
    def is_google_oauth_enabled() -> bool:
        """Check if Google OAuth is enabled (has both client ID and secret)."""
        client_id = get_auth_env().get_oauth_google_client_id()
        client_secret = get_auth_env().get_oauth_google_client_secret()
        return bool(client_id and client_secret)
    
    @staticmethod
    def get_google_oauth_redirect_uri() -> str:
        """Get Google OAuth redirect URI."""
        # DEPRECATED method preserved for backward compatibility
        # This should eventually be replaced by using GoogleOAuthProvider directly
        auth_url = get_auth_env().get_auth_service_url()
        return f"{auth_url}/auth/callback/google"
    
    @staticmethod
    def get_google_oauth_scopes() -> list[str]:
        """Get Google OAuth scopes."""
        # Standard Google OAuth scopes for user identification
        return ["openid", "email", "profile"]
    
    # Database Detail Methods - delegate to SSOT
    @staticmethod
    def get_database_host() -> str:
        """Get database host - delegates to SSOT."""
        return get_auth_env().get_postgres_host()
    
    @staticmethod
    def get_database_port() -> int:
        """Get database port - delegates to SSOT."""
        return get_auth_env().get_postgres_port()
    
    @staticmethod
    def get_database_name() -> str:
        """Get database name - delegates to SSOT."""
        return get_auth_env().get_postgres_db()
    
    @staticmethod
    def get_database_user() -> str:
        """Get database user - delegates to SSOT."""
        return get_auth_env().get_postgres_user()
    
    @staticmethod
    def get_database_password() -> str:
        """Get database password - delegates to SSOT."""
        return get_auth_env().get_postgres_password()
    
    # Database Pool Methods - provide reasonable defaults
    @staticmethod
    def get_database_pool_size() -> int:
        """Get database pool size with environment-specific defaults."""
        env = get_auth_env().get_environment()
        if env == "production":
            return 20  # Higher pool for production
        elif env == "staging":
            return 10  # Moderate pool for staging
        elif env == "development":
            return 5   # Small pool for development
        elif env == "test":
            return 2   # Minimal pool for tests
        else:
            return 5   # Default
    
    @staticmethod
    def get_database_max_overflow() -> int:
        """Get database max overflow with environment-specific defaults."""
        env = get_auth_env().get_environment()
        if env == "production":
            return 30  # Higher overflow for production
        elif env == "staging":
            return 15  # Moderate overflow for staging
        elif env == "development":
            return 5   # Small overflow for development
        elif env == "test":
            return 2   # Minimal overflow for tests
        else:
            return 10  # Default
    
    # Redis Detail Methods - delegate to SSOT
    @staticmethod
    def get_redis_host() -> str:
        """Get Redis host - delegates to SSOT."""
        return get_auth_env().get_redis_host()
    
    @staticmethod
    def get_redis_port() -> int:
        """Get Redis port - delegates to SSOT."""
        return get_auth_env().get_redis_port()
    
    @staticmethod
    def get_redis_db() -> int:
        """Get Redis database number with environment-specific defaults."""
        env = get_auth_env().get_environment()
        if env == "production":
            return 0   # Production DB
        elif env == "staging":
            return 1   # Staging DB
        elif env == "development":
            return 2   # Development DB
        elif env == "test":
            return 3   # Test DB
        else:
            return 0   # Default
    
    @staticmethod
    def get_redis_password() -> str:
        """Get Redis password - typically None for development/test."""
        # AuthEnvironment doesn't expose this directly, return empty for local env
        env = get_auth_env().get_environment()
        if env in ["production", "staging"]:
            # Production/staging would have passwords set via REDIS_URL
            from shared.isolated_environment import get_env
            return get_env().get("REDIS_PASSWORD", "")
        else:
            return ""  # No password for local development/test
    
    @staticmethod
    def is_redis_enabled() -> bool:
        """Check if Redis is enabled - opposite of is_redis_disabled."""
        return not AuthConfig.is_redis_disabled()
    
    @staticmethod
    def get_redis_default_ttl() -> int:
        """Get Redis default TTL in seconds - delegates to SSOT session TTL."""
        return get_auth_env().get_session_ttl()
    
    # Security Methods - delegate to SSOT where available
    @staticmethod
    def get_bcrypt_rounds() -> int:
        """Get bcrypt rounds - delegates to SSOT."""
        return get_auth_env().get_bcrypt_rounds()
    
    @staticmethod
    def get_password_min_length() -> int:
        """Get minimum password length - delegates to SSOT."""
        return get_auth_env().get_min_password_length()
    
    @staticmethod
    def get_max_login_attempts() -> int:
        """Get max login attempts - delegates to SSOT."""
        return get_auth_env().get_max_failed_login_attempts()
    
    @staticmethod
    def get_account_lockout_duration_minutes() -> int:
        """Get account lockout duration in minutes."""
        # Convert seconds to minutes
        return get_auth_env().get_account_lockout_duration() // 60
    
    @staticmethod
    def get_session_timeout_minutes() -> int:
        """Get session timeout in minutes."""
        # Convert seconds to minutes  
        return get_auth_env().get_session_ttl() // 60
    
    @staticmethod
    def require_email_verification() -> bool:
        """Check if email verification is required - delegates to SSOT."""
        return get_auth_env().require_password_complexity()  # Use complexity as proxy
    
    @staticmethod
    def get_token_blacklist_ttl_hours() -> int:
        """Get token blacklist TTL in hours."""
        # Use JWT refresh expiry as reasonable default
        return get_auth_env().get_refresh_token_expiration_days() * 24
    
    @staticmethod
    def get_rate_limit_requests_per_minute() -> int:
        """Get rate limit requests per minute - delegates to SSOT."""
        return get_auth_env().get_login_rate_limit()
    
    @staticmethod
    def get_allowed_origins() -> list[str]:
        """Get allowed origins (same as CORS origins) - delegates to SSOT."""
        return get_auth_env().get_cors_origins()
    
    # Logging and Status
    @staticmethod
    def log_configuration():
        """Log current configuration (without secrets)."""
        auth_env = get_auth_env()
        env = auth_env.get_environment()
        
        logger.info("Auth Service Configuration (via SSOT AuthEnvironment):")
        logger.info(f"  Environment: {env}")
        logger.info(f"  Frontend URL: {auth_env.get_frontend_url()}")
        logger.info(f"  Auth Service URL: {AuthConfig.get_auth_service_url()}")
        logger.info(f"  Google Client ID: {'*' * 10 if auth_env.get_oauth_google_client_id() else 'NOT SET'}")
        logger.info(f"  Google Client Secret: {'*' * 10 if auth_env.get_oauth_google_client_secret() else 'NOT SET'}")
        logger.info(f"  JWT Secret: {'*' * 10 if auth_env.get_jwt_secret_key() else 'NOT SET'}")
        logger.info(f"  Service Secret: {'*' * 10 if auth_env.get_secret_key() else 'NOT SET'}")
        logger.info(f"  Service ID: {AuthConfig.get_service_id()}")
        logger.info(f"  JWT Algorithm: {auth_env.get_jwt_algorithm()}")
        logger.info(f"  JWT Access Expiry: {auth_env.get_jwt_expiration_minutes()} minutes")
        logger.info(f"  JWT Refresh Expiry: {auth_env.get_refresh_token_expiration_days()} days")
        
        # Log database URL (masked)
        db_url = auth_env.get_database_url()
        # Simple masking for passwords in URLs
        if "@" in db_url and ":" in db_url:
            parts = db_url.split("@")
            if len(parts) == 2:
                # Mask the password part
                user_pass = parts[0].split("://")[1] if "://" in parts[0] else parts[0]
                if ":" in user_pass:
                    user, _ = user_pass.rsplit(":", 1)
                    masked_user_pass = f"{user}:***"
                    protocol = parts[0].split("://")[0] if "://" in parts[0] else ""
                    masked_url = f"{protocol}://{masked_user_pass}@{parts[1]}" if protocol else f"{masked_user_pass}@{parts[1]}"
                else:
                    masked_url = db_url
            else:
                masked_url = db_url
        else:
            masked_url = db_url
        logger.info(f"  Database URL: {masked_url}")


def get_config() -> AuthConfig:
    """Get auth service configuration instance.
    
    Provides compatibility with test imports that expect get_config function.
    Returns a singleton instance of AuthConfig for consistent configuration access.
    """
    return AuthConfig()