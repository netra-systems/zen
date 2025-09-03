"""
Auth Service Environment Configuration - SINGLE SOURCE OF TRUTH

This module provides the AuthEnvironment configuration for auth_service.
All environment variable access in auth_service MUST go through this implementation.

CRITICAL: This ensures service independence and configuration consistency.
"""
from typing import Optional, Dict, Any
from shared.isolated_environment import IsolatedEnvironment, get_env
import logging

logger = logging.getLogger(__name__)


class AuthEnvironment:
    """
    Auth service-specific environment configuration.
    
    This class provides a service-specific interface to environment variables
    for the auth_service, ensuring all access goes through IsolatedEnvironment.
    """
    
    def __init__(self):
        """Initialize auth environment configuration."""
        self.env = get_env()
        self._validate_auth_config()
    
    def _validate_auth_config(self) -> None:
        """Validate auth-specific configuration on initialization."""
        # Core auth requirements
        required_vars = [
            "JWT_SECRET_KEY",
            "DATABASE_URL"
        ]
        
        missing = []
        for var in required_vars:
            if not self.env.get(var):
                missing.append(var)
        
        if missing:
            logger.warning(f"Missing required auth environment variables: {missing}")
    
    # JWT & Security Configuration
    def get_jwt_secret_key(self) -> str:
        """Get JWT secret key for token generation/validation."""
        return self.env.get("JWT_SECRET_KEY", "")
    
    def get_jwt_algorithm(self) -> str:
        """Get JWT algorithm."""
        return self.env.get("JWT_ALGORITHM", "HS256")
    
    def get_jwt_expiration_minutes(self) -> int:
        """Get JWT token expiration in minutes."""
        try:
            return int(self.env.get("JWT_EXPIRATION_MINUTES", "60"))
        except ValueError:
            logger.warning("Invalid JWT_EXPIRATION_MINUTES, using default 60")
            return 60
    
    def get_refresh_token_expiration_days(self) -> int:
        """Get refresh token expiration in days."""
        try:
            return int(self.env.get("REFRESH_TOKEN_EXPIRATION_DAYS", "30"))
        except ValueError:
            return 30
    
    def get_secret_key(self) -> str:
        """Get general secret key for encryption."""
        return self.env.get("SECRET_KEY", "")
    
    def get_bcrypt_rounds(self) -> int:
        """Get bcrypt hashing rounds."""
        try:
            return int(self.env.get("BCRYPT_ROUNDS", "12"))
        except ValueError:
            return 12
    
    # Database Configuration
    def get_database_url(self) -> str:
        """Get database connection URL."""
        return self.env.get("DATABASE_URL", "")
    
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
        return self.env.get("POSTGRES_DB", "auth_db")
    
    # Redis Configuration (for session management)
    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        return self.env.get("REDIS_URL", "redis://localhost:6379/1")
    
    def get_redis_host(self) -> str:
        """Get Redis host."""
        return self.env.get("REDIS_HOST", "localhost")
    
    def get_redis_port(self) -> int:
        """Get Redis port."""
        port_str = self.env.get("REDIS_PORT", "6379")
        try:
            return int(port_str)
        except ValueError:
            return 6379
    
    def get_session_ttl(self) -> int:
        """Get session TTL in seconds."""
        try:
            return int(self.env.get("SESSION_TTL", "3600"))
        except ValueError:
            return 3600
    
    # OAuth Configuration
    def get_oauth_google_client_id(self) -> str:
        """Get Google OAuth client ID."""
        return self.env.get("OAUTH_GOOGLE_CLIENT_ID", "")
    
    def get_oauth_google_client_secret(self) -> str:
        """Get Google OAuth client secret."""
        return self.env.get("OAUTH_GOOGLE_CLIENT_SECRET", "")
    
    def get_oauth_github_client_id(self) -> str:
        """Get GitHub OAuth client ID."""
        return self.env.get("OAUTH_GITHUB_CLIENT_ID", "")
    
    def get_oauth_github_client_secret(self) -> str:
        """Get GitHub OAuth client secret."""
        return self.env.get("OAUTH_GITHUB_CLIENT_SECRET", "")
    
    # Service URLs
    def get_auth_service_port(self) -> int:
        """Get auth service port."""
        try:
            return int(self.env.get("AUTH_SERVICE_PORT", "8081"))
        except ValueError:
            return 8081
    
    def get_auth_service_host(self) -> str:
        """Get auth service host."""
        return self.env.get("AUTH_SERVICE_HOST", "0.0.0.0")
    
    def get_backend_url(self) -> str:
        """Get backend service URL for callbacks."""
        return self.env.get("BACKEND_URL", "http://localhost:8000")
    
    def get_frontend_url(self) -> str:
        """Get frontend URL for redirects."""
        return self.env.get("FRONTEND_URL", "http://localhost:3000")
    
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
        origins_str = self.env.get("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
        return [origin.strip() for origin in origins_str.split(",")]
    
    # Logging Configuration
    def get_log_level(self) -> str:
        """Get logging level."""
        return self.env.get("LOG_LEVEL", "INFO").upper()
    
    def should_enable_debug(self) -> bool:
        """Check if debug mode is enabled."""
        return self.env.get("DEBUG", "false").lower() == "true"
    
    # Rate Limiting (for auth endpoints)
    def get_login_rate_limit(self) -> int:
        """Get login attempts rate limit."""
        try:
            return int(self.env.get("LOGIN_RATE_LIMIT", "5"))
        except ValueError:
            return 5
    
    def get_login_rate_limit_period(self) -> int:
        """Get login rate limit period in seconds."""
        try:
            return int(self.env.get("LOGIN_RATE_LIMIT_PERIOD", "300"))
        except ValueError:
            return 300
    
    def get_max_failed_login_attempts(self) -> int:
        """Get max failed login attempts before lockout."""
        try:
            return int(self.env.get("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
        except ValueError:
            return 5
    
    def get_account_lockout_duration(self) -> int:
        """Get account lockout duration in seconds."""
        try:
            return int(self.env.get("ACCOUNT_LOCKOUT_DURATION", "900"))
        except ValueError:
            return 900
    
    # Password Policy
    def get_min_password_length(self) -> int:
        """Get minimum password length."""
        try:
            return int(self.env.get("MIN_PASSWORD_LENGTH", "8"))
        except ValueError:
            return 8
    
    def require_password_complexity(self) -> bool:
        """Check if password complexity is required."""
        return self.env.get("REQUIRE_PASSWORD_COMPLEXITY", "true").lower() == "true"
    
    # Email Configuration (for password reset, etc.)
    def get_smtp_host(self) -> str:
        """Get SMTP host."""
        return self.env.get("SMTP_HOST", "")
    
    def get_smtp_port(self) -> int:
        """Get SMTP port."""
        try:
            return int(self.env.get("SMTP_PORT", "587"))
        except ValueError:
            return 587
    
    def get_smtp_username(self) -> str:
        """Get SMTP username."""
        return self.env.get("SMTP_USERNAME", "")
    
    def get_smtp_password(self) -> str:
        """Get SMTP password."""
        return self.env.get("SMTP_PASSWORD", "")
    
    def get_smtp_from_email(self) -> str:
        """Get SMTP from email address."""
        return self.env.get("SMTP_FROM_EMAIL", "noreply@netra.ai")
    
    def is_smtp_enabled(self) -> bool:
        """Check if SMTP is configured."""
        return bool(self.get_smtp_host() and self.get_smtp_username())
    
    # Generic getter for backward compatibility
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get any environment variable (for backward compatibility)."""
        return self.env.get(key, default)
    
    def set(self, key: str, value: str, source: str = "auth") -> bool:
        """Set an environment variable (mainly for testing)."""
        return self.env.set(key, value, source)
    
    def exists(self, key: str) -> bool:
        """Check if an environment variable exists."""
        return self.env.exists(key)
    
    def get_all(self) -> Dict[str, str]:
        """Get all environment variables."""
        return self.env.get_all()
    
    def validate(self) -> Dict[str, Any]:
        """Validate auth environment configuration."""
        issues = []
        warnings = []
        
        # Required variables
        required = {
            "JWT_SECRET_KEY": self.get_jwt_secret_key(),
            "DATABASE_URL": self.get_database_url()
        }
        
        for name, value in required.items():
            if not value:
                issues.append(f"Missing required variable: {name}")
        
        # Check for insecure defaults in non-development
        if not self.is_development():
            if self.get_jwt_secret_key() == "dev-jwt-secret":
                issues.append("Using development JWT_SECRET_KEY in non-development environment")
            
            if self.get_bcrypt_rounds() < 10:
                warnings.append(f"BCRYPT_ROUNDS ({self.get_bcrypt_rounds()}) is too low for production")
        
        # Check JWT configuration
        if self.get_jwt_expiration_minutes() > 1440:  # More than 24 hours
            warnings.append(f"JWT_EXPIRATION_MINUTES ({self.get_jwt_expiration_minutes()}) is very long")
        
        # Check password policy
        if self.get_min_password_length() < 8:
            warnings.append(f"MIN_PASSWORD_LENGTH ({self.get_min_password_length()}) is below recommended minimum")
        
        # Check rate limiting
        if self.is_production():
            if self.get_login_rate_limit() > 10:
                warnings.append(f"LOGIN_RATE_LIMIT ({self.get_login_rate_limit()}) may be too permissive for production")
        
        # Check email configuration
        if not self.is_smtp_enabled() and self.is_production():
            warnings.append("SMTP not configured - password reset emails will not work")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "environment": self.get_environment()
        }


# Singleton instance
_auth_env = AuthEnvironment()


def get_auth_env() -> AuthEnvironment:
    """Get the singleton AuthEnvironment instance."""
    return _auth_env


# Convenience functions for direct access
def get_jwt_secret_key() -> str:
    """Get JWT secret key."""
    return get_auth_env().get_jwt_secret_key()


def get_database_url() -> str:
    """Get database URL."""
    return get_auth_env().get_database_url()


def get_environment() -> str:
    """Get current environment."""
    return get_auth_env().get_environment()


def is_production() -> bool:
    """Check if in production."""
    return get_auth_env().is_production()


def is_development() -> bool:
    """Check if in development."""
    return get_auth_env().is_development()