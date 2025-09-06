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
    
    # Get the SSOT instance
    _auth_env = get_auth_env()
    
    # Class-level attributes for legacy compatibility
    @property
    def ENVIRONMENT(self) -> str:
        return self._auth_env.get_environment()
    
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