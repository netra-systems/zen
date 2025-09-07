"""
Backend Service Environment Configuration - SINGLE SOURCE OF TRUTH

This module provides the BackendEnvironment configuration for netra_backend service.
All environment variable access in netra_backend MUST go through this implementation.

CRITICAL: This ensures service independence and configuration consistency.
"""
from typing import Optional, Dict, Any
from shared.isolated_environment import IsolatedEnvironment, get_env
import logging

logger = logging.getLogger(__name__)


class BackendEnvironment:
    """
    Backend-specific environment configuration.
    
    This class provides a service-specific interface to environment variables
    for the netra_backend service, ensuring all access goes through IsolatedEnvironment.
    """
    
    def __init__(self):
        """Initialize backend environment configuration."""
        self.env = get_env()
        self._validate_backend_config()
    
    def _validate_backend_config(self) -> None:
        """Validate backend-specific configuration on initialization."""
        # Core backend requirements
        # Database URL can come from DATABASE_URL directly or built from POSTGRES_* variables
        required_vars = [
            "JWT_SECRET_KEY",
            "SECRET_KEY"
        ]
        
        missing = []
        for var in required_vars:
            if not self.env.get(var):
                missing.append(var)
        
        if missing:
            logger.warning(f"Missing required backend environment variables: {missing}")
        
        # Check database configuration - DATABASE_URL takes priority
        if self.env.get("DATABASE_URL"):
            logger.info(f"Using DATABASE_URL for database connection")
        else:
            # Check if we can build a database URL from POSTGRES_* variables
            db_url = self.get_database_url()
            if not db_url:
                logger.info("Database URL will be built from POSTGRES_* environment variables")
            else:
                logger.info("Built database URL from POSTGRES_* environment variables")
    
    # Authentication & Security
    def get_jwt_secret_key(self) -> str:
        """
        Get JWT secret key for authentication.
        
        Uses unified secrets manager to properly handle environment-specific JWT secrets.
        This ensures consistency with auth service which uses environment-specific secrets.
        
        Priority order:
        1. Environment-specific JWT_SECRET_{ENVIRONMENT} (e.g., JWT_SECRET_STAGING)
        2. Generic JWT_SECRET_KEY
        3. Legacy JWT_SECRET
        4. Development fallback
        """
        from netra_backend.app.core.configuration.unified_secrets import get_jwt_secret
        return get_jwt_secret()
    
    def get_secret_key(self) -> str:
        """Get general secret key for session/encryption."""
        return self.env.get("SECRET_KEY", "")
    
    def get_fernet_key(self) -> str:
        """Get Fernet encryption key."""
        return self.env.get("FERNET_KEY", "")
    
    # Database Configuration
    def get_database_url(self, sync: bool = False) -> str:
        """Get database connection URL using DatabaseURLBuilder.
        
        Args:
            sync: If True, return synchronous URL (for Alembic, etc.)
        """
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Use DatabaseURLBuilder to construct URL from components
        builder = DatabaseURLBuilder(self.env.as_dict())
        
        # Get URL for current environment (async by default, sync if requested)
        database_url = builder.get_url_for_environment(sync=sync)
        
        if database_url:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(builder.get_safe_log_message())
            return database_url
        
        # No fallback - let caller handle missing URL
        return ""
    
    def get_postgres_host(self) -> str:
        """Get PostgreSQL host."""
        return self.env.get("POSTGRES_HOST", "localhost")
    
    def get_postgres_port(self) -> int:
        """Get PostgreSQL port."""
        port_str = self.env.get("POSTGRES_PORT", "5432")
        try:
            return int(port_str)
        except ValueError:
            logger.warning(f"Invalid POSTGRES_PORT: {port_str}, using default 5432")
            return 5432
    
    def get_postgres_user(self) -> str:
        """Get PostgreSQL username."""
        return self.env.get("POSTGRES_USER", "postgres")
    
    def get_postgres_password(self) -> str:
        """Get PostgreSQL password."""
        return self.env.get("POSTGRES_PASSWORD", "")
    
    def get_postgres_db(self) -> str:
        """Get PostgreSQL database name."""
        return self.env.get("POSTGRES_DB", "netra_db")
    
    # Redis Configuration
    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        return self.env.get("REDIS_URL", "redis://localhost:6379/0")
    
    def get_redis_host(self) -> str:
        """Get Redis host."""
        return self.env.get("REDIS_HOST", "localhost")
    
    def get_redis_port(self) -> int:
        """Get Redis port."""
        port_str = self.env.get("REDIS_PORT", "6379")
        try:
            return int(port_str)
        except ValueError:
            logger.warning(f"Invalid REDIS_PORT: {port_str}, using default 6379")
            return 6379
    
    # API Keys
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key."""
        return self.env.get("OPENAI_API_KEY", "")
    
    def get_anthropic_api_key(self) -> str:
        """Get Anthropic API key."""
        return self.env.get("ANTHROPIC_API_KEY", "")
    
    # Service URLs
    def get_auth_service_url(self) -> str:
        """Get Auth Service URL."""
        return self.env.get("AUTH_SERVICE_URL", "http://localhost:8081")
    
    def get_frontend_url(self) -> str:
        """Get Frontend URL."""
        return self.env.get("FRONTEND_URL", "http://localhost:3000")
    
    def get_backend_url(self) -> str:
        """Get Backend URL (self)."""
        return self.env.get("BACKEND_URL", "http://localhost:8000")
    
    # Environment & Deployment
    def get_environment(self) -> str:
        """Get current environment name."""
        return self.env.get("ENVIRONMENT", "development").lower()
    
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.get_environment() == "production"
    
    def is_staging(self) -> bool:
        """Check if running in staging."""
        return self.get_environment() == "staging"
    
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.get_environment() in ["development", "dev", "local"]
    
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.get_environment() in ["test", "testing"] or self.env.get("TESTING", "false").lower() == "true"
    
    # CORS Configuration
    def get_cors_origins(self) -> list[str]:
        """Get allowed CORS origins."""
        origins_str = self.env.get("CORS_ORIGINS", "http://localhost:3000")
        return [origin.strip() for origin in origins_str.split(",")]
    
    # Logging Configuration
    def get_log_level(self) -> str:
        """Get logging level."""
        return self.env.get("LOG_LEVEL", "INFO").upper()
    
    def should_enable_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.env.get("DEBUG", "false").lower() == "true"
    
    # Feature Flags
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        flag_key = f"FEATURE_{feature_name.upper()}"
        return self.env.get(flag_key, "false").lower() == "true"
    
    # Rate Limiting
    def get_rate_limit_requests(self) -> int:
        """Get rate limit requests per period."""
        try:
            return int(self.env.get("RATE_LIMIT_REQUESTS", "100"))
        except ValueError:
            return 100
    
    def get_rate_limit_period(self) -> int:
        """Get rate limit period in seconds."""
        try:
            return int(self.env.get("RATE_LIMIT_PERIOD", "60"))
        except ValueError:
            return 60
    
    # WebSocket Configuration
    def get_websocket_timeout(self) -> int:
        """Get WebSocket connection timeout in seconds."""
        try:
            return int(self.env.get("WEBSOCKET_TIMEOUT", "300"))
        except ValueError:
            return 300
    
    def get_websocket_ping_interval(self) -> int:
        """Get WebSocket ping interval in seconds."""
        try:
            return int(self.env.get("WEBSOCKET_PING_INTERVAL", "30"))
        except ValueError:
            return 30
    
    # Agent Configuration
    def get_agent_timeout(self) -> int:
        """Get agent execution timeout in seconds."""
        try:
            return int(self.env.get("AGENT_TIMEOUT", "600"))
        except ValueError:
            return 600
    
    def get_max_agent_retries(self) -> int:
        """Get maximum agent retry attempts."""
        try:
            return int(self.env.get("MAX_AGENT_RETRIES", "3"))
        except ValueError:
            return 3
    
    # Cache Configuration
    def get_cache_ttl(self) -> int:
        """Get default cache TTL in seconds."""
        try:
            return int(self.env.get("CACHE_TTL", "3600"))
        except ValueError:
            return 3600
    
    def is_cache_enabled(self) -> bool:
        """Check if caching is enabled."""
        return self.env.get("CACHE_ENABLED", "true").lower() == "true"
    
    # Generic getter for backward compatibility
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get any environment variable (for backward compatibility)."""
        return self.env.get(key, default)
    
    def set(self, key: str, value: str, source: str = "backend") -> bool:
        """Set an environment variable (mainly for testing)."""
        return self.env.set(key, value, source)
    
    def exists(self, key: str) -> bool:
        """Check if an environment variable exists."""
        return self.env.exists(key)
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables."""
        return self.env.get_all()
    
    def validate(self) -> Dict[str, Any]:
        """Validate backend environment configuration."""
        issues = []
        warnings = []
        
        # Required variables (DATABASE_URL is built dynamically, not required as env var)
        required = {
            "JWT_SECRET_KEY": self.get_jwt_secret_key(),
            "SECRET_KEY": self.get_secret_key()
        }
        
        for name, value in required.items():
            if not value:
                issues.append(f"Missing required variable: {name}")
        
        # Check database configuration separately
        db_url = self.get_database_url()
        if not db_url:
            issues.append("Unable to build database URL from POSTGRES_* variables")
        
        # Check for insecure defaults in non-development
        if not self.is_development():
            if self.get_jwt_secret_key() == "dev-jwt-secret":
                issues.append("Using development JWT_SECRET_KEY in non-development environment")
            if self.get_secret_key() == "dev-secret-key":
                issues.append("Using development SECRET_KEY in non-development environment")
        
        # Warnings for optional but recommended
        if not self.get_openai_api_key() and not self.get_anthropic_api_key():
            warnings.append("No AI API keys configured (OPENAI_API_KEY or ANTHROPIC_API_KEY)")
        
        if self.is_production() and self.should_enable_debug():
            warnings.append("DEBUG mode enabled in production")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "environment": self.get_environment()
        }


# Singleton instance
_backend_env = BackendEnvironment()


def get_backend_env() -> BackendEnvironment:
    """Get the singleton BackendEnvironment instance."""
    return _backend_env


# Convenience functions for direct access
def get_jwt_secret_key() -> str:
    """Get JWT secret key."""
    return get_backend_env().get_jwt_secret_key()


def get_database_url(sync: bool = False) -> str:
    """Get database URL.
    
    Args:
        sync: If True, return synchronous URL (for Alembic, etc.)
    """
    return get_backend_env().get_database_url(sync=sync)


def get_environment() -> str:
    """Get current environment."""
    return get_backend_env().get_environment()


def is_production() -> bool:
    """Check if in production."""
    return get_backend_env().is_production()


def is_development() -> bool:
    """Check if in development."""
    return get_backend_env().is_development()