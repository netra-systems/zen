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
            "JWT_SECRET_KEY"
            # DATABASE_URL is now built from components, not required directly
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
        env = self.get_environment()
        secret = self.env.get("JWT_SECRET_KEY", "")
        
        if not secret:
            if env == "development":
                # Development: Generate consistent dev secret
                import hashlib
                dev_secret = hashlib.sha256("netra_dev_jwt_key".encode()).hexdigest()[:32]
                self.env.set("JWT_SECRET_KEY", dev_secret, "auth_env_development")
                return dev_secret
            elif env == "test":
                # Test: Generate consistent test secret
                import hashlib
                test_secret = hashlib.sha256("netra_test_jwt_key".encode()).hexdigest()[:32]
                self.env.set("JWT_SECRET_KEY", test_secret, "auth_env_test")
                return test_secret
            elif env in ["staging", "production"]:
                raise ValueError(f"JWT_SECRET_KEY must be explicitly set in {env} environment")
        
        return secret
    
    def get_jwt_algorithm(self) -> str:
        """Get JWT algorithm with environment-specific defaults."""
        env = self.get_environment()
        
        if env == "production":
            # Production: Require explicit configuration
            algorithm = self.env.get("JWT_ALGORITHM")
            if not algorithm:
                raise ValueError("JWT_ALGORITHM must be explicitly set in production")
            return algorithm
        elif env == "staging":
            # Staging: Use production-like defaults but allow override
            return self.env.get("JWT_ALGORITHM") or "HS256"
        elif env == "development":
            # Development: Permissive default for fast iteration
            return self.env.get("JWT_ALGORITHM") or "HS256"
        elif env == "test":
            # Test: Fast algorithm for test performance
            return self.env.get("JWT_ALGORITHM") or "HS256"
        else:
            return "HS256"
    
    def get_jwt_expiration_minutes(self) -> int:
        """Get JWT token expiration in minutes with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("JWT_EXPIRATION_MINUTES")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 15  # Short expiration for production security
            elif env == "staging":
                return 30  # Moderate expiration for staging testing
            elif env == "development":
                return 120  # Longer expiration for dev convenience
            elif env == "test":
                return 5   # Short expiration for test speed
            else:
                return 60  # Default for unknown environments
        except ValueError:
            logger.warning(f"Invalid JWT_EXPIRATION_MINUTES in {env} environment, using environment default")
            if env == "production":
                return 15
            elif env == "staging":
                return 30
            elif env == "development":
                return 120
            elif env == "test":
                return 5
            return 60
    
    def get_refresh_token_expiration_days(self) -> int:
        """Get refresh token expiration in days with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("REFRESH_TOKEN_EXPIRATION_DAYS")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 7   # Weekly refresh for production
            elif env == "staging":
                return 14  # Bi-weekly for staging
            elif env == "development":
                return 30  # Monthly for development
            elif env == "test":
                return 1   # Daily for test isolation
            else:
                return 30  # Default for unknown environments
        except ValueError:
            logger.warning(f"Invalid REFRESH_TOKEN_EXPIRATION_DAYS in {env} environment")
            if env == "production":
                return 7
            elif env == "staging":
                return 14
            elif env == "development":
                return 30
            elif env == "test":
                return 1
            return 30
    
    def get_secret_key(self) -> str:
        """Get general secret key for encryption with environment-specific behavior."""
        env = self.get_environment()
        secret = self.env.get("SECRET_KEY", "")
        
        if not secret:
            if env == "development":
                # Development: Generate consistent dev secret
                import hashlib
                dev_secret = hashlib.sha256("netra_dev_secret_key".encode()).hexdigest()
                self.env.set("SECRET_KEY", dev_secret, "auth_env_development")
                return dev_secret
            elif env == "test":
                # Test: Generate consistent test secret  
                import hashlib
                test_secret = hashlib.sha256("netra_test_secret_key".encode()).hexdigest()
                self.env.set("SECRET_KEY", test_secret, "auth_env_test")
                return test_secret
            elif env in ["staging", "production"]:
                raise ValueError(f"SECRET_KEY must be explicitly set in {env} environment")
        
        return secret
    
    def get_bcrypt_rounds(self) -> int:
        """Get bcrypt hashing rounds with environment-specific security levels."""
        env = self.get_environment()
        
        try:
            value = self.env.get("BCRYPT_ROUNDS")
            if value:
                return int(value)
            
            # Environment-specific security levels (no fallback pattern)
            if env == "production":
                return 12  # High security for production
            elif env == "staging":
                return 10  # Moderate security for staging
            elif env == "development":
                return 8   # Lower rounds for dev speed
            elif env == "test":
                return 4   # Minimal rounds for test performance
            else:
                return 12  # Secure default for unknown environments
        except ValueError:
            logger.warning(f"Invalid BCRYPT_ROUNDS in {env} environment")
            if env == "production":
                return 12
            elif env == "staging":
                return 10
            elif env == "development":
                return 8
            elif env == "test":
                return 4
            return 12
    
    # Database Configuration
    def get_database_url(self) -> str:
        """Get database connection URL using DatabaseURLBuilder."""
        env = self.get_environment()
        
        # CRITICAL: Test environment gets SQLite in-memory for isolation and speed (per CLAUDE.md)
        # This takes priority over any explicit DATABASE_URL to ensure "permissive" test behavior
        if env == "test":
            # Test: Always use in-memory SQLite for isolation (permissive test behavior)
            url = "sqlite+aiosqlite:///:memory:"
            logger.info("Using in-memory SQLite for test environment (permissive test mode per CLAUDE.md)")
            return url
        
        # Use DatabaseURLBuilder for all non-test environments
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Build environment variables dict for DatabaseURLBuilder
        env_vars = {
            "ENVIRONMENT": env,
            "POSTGRES_HOST": self.env.get("POSTGRES_HOST"),
            "POSTGRES_PORT": self.env.get("POSTGRES_PORT"),
            "POSTGRES_DB": self.env.get("POSTGRES_DB"),
            "POSTGRES_USER": self.env.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": self.env.get("POSTGRES_PASSWORD"),
            "DATABASE_URL": self.env.get("DATABASE_URL")  # For backward compatibility
        }
        
        # Create URL builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Get URL for current environment - NO MANUAL FALLBACKS
        database_url = builder.get_url_for_environment(sync=False)  # async for auth service
        
        if not database_url:
            # NO MANUAL FALLBACKS - DatabaseURLBuilder is the SINGLE SOURCE OF TRUTH
            # Log the debug info to help diagnose the issue
            debug_info = builder.debug_info()
            logger.error(f"DatabaseURLBuilder failed to construct URL for {env} environment. Debug info: {debug_info}")
            
            # Provide helpful error message based on environment
            if env == "production" or env == "staging":
                raise ValueError(
                    f"DatabaseURLBuilder failed to construct URL for {env} environment. "
                    f"Ensure POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, and POSTGRES_DB are set, "
                    f"or DATABASE_URL is provided. Debug info: {debug_info}"
                )
            else:
                # For development/test, still fail but with more helpful message
                raise ValueError(
                    f"DatabaseURLBuilder failed to construct URL for {env} environment. "
                    f"For development, ensure DATABASE_URL is set or use default localhost configuration. "
                    f"Debug info: {debug_info}"
                )
        
        # Log safe connection info
        logger.info(builder.get_safe_log_message())
        return database_url
    
    def get_postgres_host(self) -> str:
        """Get PostgreSQL host with environment-specific defaults."""
        env = self.get_environment()
        
        host = self.env.get("POSTGRES_HOST")
        if host:
            return host
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production requires explicit host configuration
            raise ValueError("POSTGRES_HOST must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit host configuration
            raise ValueError("POSTGRES_HOST must be explicitly set in staging")
        elif env == "development":
            # Development: Standard local development host
            return "localhost"
        elif env == "test":
            # Test: Local test database (if not using in-memory SQLite)
            return "localhost"
        else:
            return "localhost"
    
    def get_postgres_port(self) -> int:
        """Get PostgreSQL port with environment-specific defaults."""
        env = self.get_environment()
        
        port_str = self.env.get("POSTGRES_PORT")
        if port_str:
            try:
                return int(port_str)
            except ValueError:
                logger.warning(f"Invalid POSTGRES_PORT: {port_str} in {env} environment")
                raise ValueError(f"POSTGRES_PORT must be a valid integer in {env} environment")
        
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production requires explicit port configuration
            raise ValueError("POSTGRES_PORT must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit port configuration  
            raise ValueError("POSTGRES_PORT must be explicitly set in staging")
        elif env == "development":
            # Development: Standard PostgreSQL port
            return 5432
        elif env == "test":
            # Test: Test database port (often different to avoid conflicts)
            return 5434
        else:
            return 5432
    
    def get_postgres_user(self) -> str:
        """Get PostgreSQL username with environment-specific defaults."""
        env = self.get_environment()
        
        user = self.env.get("POSTGRES_USER")
        if user:
            return user
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production requires explicit user configuration
            raise ValueError("POSTGRES_USER must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit user configuration
            raise ValueError("POSTGRES_USER must be explicitly set in staging")
        elif env == "development":
            # Development: Standard development user
            return "postgres"
        elif env == "test":
            # Test: Test-specific user
            return "postgres"
        else:
            return "postgres"
    
    def get_postgres_password(self) -> str:
        """Get PostgreSQL password with environment-specific behavior."""
        env = self.get_environment()
        
        password = self.env.get("POSTGRES_PASSWORD")
        if password:
            return password
            
        # Environment-specific behavior (no fallback pattern)
        if env == "production":
            # Production requires explicit password configuration
            raise ValueError("POSTGRES_PASSWORD must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit password configuration
            raise ValueError("POSTGRES_PASSWORD must be explicitly set in staging")
        elif env == "development":
            # Development: Allow empty password for local development
            logger.warning("Using empty password for development PostgreSQL - ensure local setup allows this")
            return ""
        elif env == "test":
            # Test: Allow empty password for test database
            return ""
        else:
            return ""
    
    def get_postgres_db(self) -> str:
        """Get PostgreSQL database name with environment-specific defaults."""
        env = self.get_environment()
        
        db_name = self.env.get("POSTGRES_DB")
        if db_name:
            return db_name
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production requires explicit database name
            raise ValueError("POSTGRES_DB must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit database name
            raise ValueError("POSTGRES_DB must be explicitly set in staging")
        elif env == "development":
            # Development: Standard development database
            return "netra_auth_dev"
        elif env == "test":
            # Test: Test-specific database
            return "netra_auth_test"
        else:
            return "auth_db"
    
    # Redis Configuration (for session management)
    def get_redis_url(self) -> str:
        """Get Redis connection URL with environment-specific behavior."""
        env = self.get_environment()
        
        url = self.env.get("REDIS_URL")
        if url:
            return url
            
        # Environment-specific behavior (no fallback pattern)
        if env == "production":
            # Production requires explicit Redis configuration
            raise ValueError("REDIS_URL must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit Redis configuration
            raise ValueError("REDIS_URL must be explicitly set in staging")
        elif env == "development":
            # Development: Standard local Redis with auth-specific database
            return "redis://localhost:6379/1"
        elif env == "test":
            # Test: Separate Redis database for test isolation
            return "redis://localhost:6379/2"
        else:
            return "redis://localhost:6379/1"
    
    def get_redis_host(self) -> str:
        """Get Redis host with environment-specific defaults."""
        env = self.get_environment()
        
        host = self.env.get("REDIS_HOST")
        if host:
            return host
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production requires explicit Redis host
            raise ValueError("REDIS_HOST must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit Redis host  
            raise ValueError("REDIS_HOST must be explicitly set in staging")
        elif env == "development":
            # Development: Local Redis
            return "localhost"
        elif env == "test":
            # Test: Local Redis
            return "localhost"
        else:
            return "localhost"
    
    def get_redis_port(self) -> int:
        """Get Redis port with environment-specific defaults."""
        env = self.get_environment()
        
        port_str = self.env.get("REDIS_PORT")
        if port_str:
            try:
                return int(port_str)
            except ValueError:
                logger.warning(f"Invalid REDIS_PORT: {port_str} in {env} environment")
                raise ValueError(f"REDIS_PORT must be a valid integer in {env} environment")
        
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production requires explicit Redis port
            raise ValueError("REDIS_PORT must be explicitly set in production")
        elif env == "staging":
            # Staging requires explicit Redis port
            raise ValueError("REDIS_PORT must be explicitly set in staging")
        elif env == "development":
            # Development: Standard Redis port
            return 6379
        elif env == "test":
            # Test: Alternative Redis port to avoid conflicts
            return 6381
        else:
            return 6379
    
    def get_session_ttl(self) -> int:
        """Get session TTL in seconds with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("SESSION_TTL")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 3600   # 1 hour for production security
            elif env == "staging":
                return 7200   # 2 hours for staging testing
            elif env == "development":
                return 86400  # 24 hours for dev convenience
            elif env == "test":
                return 300    # 5 minutes for test isolation
            else:
                return 3600   # Default for unknown environments
        except ValueError:
            logger.warning(f"Invalid SESSION_TTL in {env} environment")
            if env == "production":
                return 3600
            elif env == "staging":
                return 7200
            elif env == "development":
                return 86400
            elif env == "test":
                return 300
            return 3600
    
    # OAuth Configuration
    def get_oauth_google_client_id(self) -> str:
        """Get Google OAuth client ID with environment-specific behavior."""
        env = self.get_environment()
        
        # Try environment-specific OAuth variables first
        env_specific_keys = [
            f"GOOGLE_OAUTH_CLIENT_ID_{env.upper()}",
            f"OAUTH_GOOGLE_CLIENT_ID_{env.upper()}",
            "OAUTH_GOOGLE_CLIENT_ID",
            "GOOGLE_OAUTH_CLIENT_ID"
        ]
        
        for key in env_specific_keys:
            client_id = self.env.get(key)
            if client_id:
                return client_id
        
        # Environment-specific behavior (no fallback pattern)
        if env in ["production", "staging"]:
            # Production/staging require explicit OAuth configuration
            logger.warning(f"OAUTH_GOOGLE_CLIENT_ID not set in {env} - Google OAuth will be disabled")
            return ""
        elif env == "development":
            # Development: OAuth is optional
            logger.info("OAUTH_GOOGLE_CLIENT_ID not set in development - Google OAuth disabled")
            return ""
        elif env == "test":
            # Test: OAuth typically disabled
            return ""
        else:
            return ""
    
    def get_oauth_google_client_secret(self) -> str:
        """Get Google OAuth client secret with environment-specific behavior."""
        env = self.get_environment()
        
        # Try environment-specific OAuth variables first
        env_specific_keys = [
            f"GOOGLE_OAUTH_CLIENT_SECRET_{env.upper()}",
            f"OAUTH_GOOGLE_CLIENT_SECRET_{env.upper()}",
            "OAUTH_GOOGLE_CLIENT_SECRET",
            "GOOGLE_OAUTH_CLIENT_SECRET"
        ]
        
        for key in env_specific_keys:
            client_secret = self.env.get(key)
            if client_secret:
                return client_secret
        
        # Environment-specific behavior (no fallback pattern)
        if env in ["production", "staging"]:
            # Production/staging require explicit OAuth configuration
            logger.warning(f"OAUTH_GOOGLE_CLIENT_SECRET not set in {env} - Google OAuth will be disabled")
            return ""
        elif env == "development":
            # Development: OAuth is optional
            logger.info("OAUTH_GOOGLE_CLIENT_SECRET not set in development - Google OAuth disabled")
            return ""
        elif env == "test":
            # Test: OAuth typically disabled
            return ""
        else:
            return ""
    
    def get_oauth_github_client_id(self) -> str:
        """Get GitHub OAuth client ID."""
        return self.env.get("OAUTH_GITHUB_CLIENT_ID", "")
    
    def get_oauth_github_client_secret(self) -> str:
        """Get GitHub OAuth client secret."""
        return self.env.get("OAUTH_GITHUB_CLIENT_SECRET", "")
    
    # Service URLs
    def get_auth_service_port(self) -> int:
        """Get auth service port with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("AUTH_SERVICE_PORT")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                # Production runs on standard port (from Cloud Run)
                return 8080
            elif env == "staging":
                # Staging runs on standard port (from Cloud Run)
                return 8080
            elif env == "development":
                # Development: Standard development port
                return 8081
            elif env == "test":
                # Test: Alternative port to avoid conflicts
                return 8082
            else:
                return 8081  # Default for unknown environments
        except ValueError:
            logger.warning(f"Invalid AUTH_SERVICE_PORT in {env} environment")
            if env in ["production", "staging"]:
                return 8080
            elif env == "development":
                return 8081
            elif env == "test":
                return 8082
            return 8081
    
    def get_auth_service_host(self) -> str:
        """Get auth service host with environment-specific defaults."""
        env = self.get_environment()
        
        host = self.env.get("AUTH_SERVICE_HOST")
        if host:
            return host
            
        # Environment-specific defaults (no fallback pattern)
        if env in ["production", "staging"]:
            # Cloud Run binds to 0.0.0.0
            return "0.0.0.0"
        elif env == "development":
            # Development: Bind to all interfaces for Docker compatibility
            return "0.0.0.0"
        elif env == "test":
            # Test: Localhost for test isolation
            return "127.0.0.1"
        else:
            return "0.0.0.0"
    
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
        """Get allowed CORS origins with environment-specific defaults."""
        env = self.get_environment()
        
        origins_str = self.env.get("CORS_ORIGINS")
        if origins_str:
            return [origin.strip() for origin in origins_str.split(",")]
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            # Production: Only allow production domains
            return ["https://netrasystems.ai", "https://app.netrasystems.ai"]
        elif env == "staging":
            # Staging: Allow staging domains
            return ["https://app.staging.netrasystems.ai", "https://staging.netrasystems.ai"]
        elif env == "development":
            # Development: Allow local development servers
            return ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]
        elif env == "test":
            # Test: Allow test servers
            return ["http://localhost:3001", "http://localhost:8001", "http://127.0.0.1:3001"]
        else:
            # Default for unknown environments
            return ["http://localhost:3000"]
    
    # Logging Configuration
    def get_log_level(self) -> str:
        """Get logging level with environment-specific defaults."""
        env = self.get_environment()
        
        level = self.env.get("LOG_LEVEL")
        if level:
            return level.upper()
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            return "WARNING"  # Less verbose in production
        elif env == "staging":
            return "INFO"     # Standard info level for staging
        elif env == "development":
            return "DEBUG"    # Verbose debugging in development
        elif env == "test":
            return "ERROR"    # Minimal logging in tests
        else:
            return "INFO"     # Default for unknown environments
    
    def should_enable_debug(self) -> bool:
        """Check if debug mode is enabled with environment-specific behavior."""
        env = self.get_environment()
        
        debug_str = self.env.get("DEBUG")
        if debug_str:
            return debug_str.lower() == "true"
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            return False  # Never debug in production
        elif env == "staging":
            return False  # No debug in staging
        elif env == "development":
            return True   # Enable debug in development
        elif env == "test":
            return False  # No debug in tests for speed
        else:
            return False  # Safe default
    
    # Rate Limiting (for auth endpoints)
    def get_login_rate_limit(self) -> int:
        """Get login attempts rate limit with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("LOGIN_RATE_LIMIT")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 3   # Strict rate limiting in production
            elif env == "staging":
                return 5   # Moderate rate limiting for staging testing
            elif env == "development":
                return 10  # Relaxed rate limiting for development
            elif env == "test":
                return 100 # High limit for test performance
            else:
                return 5   # Safe default
        except ValueError:
            logger.warning(f"Invalid LOGIN_RATE_LIMIT in {env} environment")
            if env == "production":
                return 3
            elif env == "staging":
                return 5
            elif env == "development":
                return 10
            elif env == "test":
                return 100
            return 5
    
    def get_login_rate_limit_period(self) -> int:
        """Get login rate limit period in seconds with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("LOGIN_RATE_LIMIT_PERIOD")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 600  # 10 minutes for production security
            elif env == "staging":
                return 300  # 5 minutes for staging
            elif env == "development":
                return 60   # 1 minute for development
            elif env == "test":
                return 10   # 10 seconds for test speed
            else:
                return 300  # Safe default
        except ValueError:
            logger.warning(f"Invalid LOGIN_RATE_LIMIT_PERIOD in {env} environment")
            if env == "production":
                return 600
            elif env == "staging":
                return 300
            elif env == "development":
                return 60
            elif env == "test":
                return 10
            return 300
    
    def get_max_failed_login_attempts(self) -> int:
        """Get max failed login attempts before lockout with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("MAX_FAILED_LOGIN_ATTEMPTS")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 3   # Strict lockout in production
            elif env == "staging":
                return 5   # Moderate lockout for staging
            elif env == "development":
                return 10  # Relaxed lockout for development
            elif env == "test":
                return 100 # High threshold for tests
            else:
                return 5   # Safe default
        except ValueError:
            logger.warning(f"Invalid MAX_FAILED_LOGIN_ATTEMPTS in {env} environment")
            if env == "production":
                return 3
            elif env == "staging":
                return 5
            elif env == "development":
                return 10
            elif env == "test":
                return 100
            return 5
    
    def get_account_lockout_duration(self) -> int:
        """Get account lockout duration in seconds."""
        try:
            return int(self.env.get("ACCOUNT_LOCKOUT_DURATION", "900"))
        except ValueError:
            return 900
    
    # Password Policy
    def get_min_password_length(self) -> int:
        """Get minimum password length with environment-specific defaults."""
        env = self.get_environment()
        
        try:
            value = self.env.get("MIN_PASSWORD_LENGTH")
            if value:
                return int(value)
            
            # Environment-specific defaults (no fallback pattern)
            if env == "production":
                return 12  # Strong password requirement in production
            elif env == "staging":
                return 10  # Moderate requirement for staging
            elif env == "development":
                return 6   # Relaxed requirement for development
            elif env == "test":
                return 4   # Minimal requirement for tests
            else:
                return 8   # Safe default
        except ValueError:
            logger.warning(f"Invalid MIN_PASSWORD_LENGTH in {env} environment")
            if env == "production":
                return 12
            elif env == "staging":
                return 10
            elif env == "development":
                return 6
            elif env == "test":
                return 4
            return 8
    
    def require_password_complexity(self) -> bool:
        """Check if password complexity is required with environment-specific defaults."""
        env = self.get_environment()
        
        complexity_str = self.env.get("REQUIRE_PASSWORD_COMPLEXITY")
        if complexity_str:
            return complexity_str.lower() == "true"
            
        # Environment-specific defaults (no fallback pattern)
        if env == "production":
            return True   # Always require complexity in production
        elif env == "staging":
            return True   # Require complexity in staging
        elif env == "development":
            return False  # Optional complexity in development
        elif env == "test":
            return False  # No complexity required in tests
        else:
            return True   # Safe default
    
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
            "JWT_SECRET_KEY": self.get_jwt_secret_key()
            # DATABASE_URL is validated through DatabaseURLBuilder
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