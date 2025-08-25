"""
Auth Service Configuration
Handles environment variable loading with staging/production awareness

**UPDATED**: Now uses auth_service's own IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml and SPEC/independent_services.xml for consistent 
environment access while maintaining complete microservice independence.
"""
import logging

# Use auth_service's own isolated environment management - NEVER import from dev_launcher or netra_backend
from auth_service.auth_core.isolated_environment import get_env
from auth_service.auth_core.secret_loader import AuthSecretLoader

logger = logging.getLogger(__name__)

class AuthConfig:
    """Centralized configuration for auth service"""
    
    # Class-level attributes for settings compatibility
    _env = get_env()  # Use IsolatedEnvironment singleton
    ENVIRONMENT = _env.get("ENVIRONMENT", "development").lower()
    LOG_ASYNC_CHECKOUT = _env.get("LOG_ASYNC_CHECKOUT", "false").lower() == "true"
    
    @staticmethod
    def get_environment() -> str:
        """Get current environment"""
        env = get_env().get("ENVIRONMENT", "development").lower()
        if env in ["staging", "production", "development", "test"]:
            return env
        return "development"
    
    @staticmethod
    def get_google_client_id() -> str:
        """Get Google OAuth Client ID using unified secret loader"""
        return AuthSecretLoader.get_google_client_id()
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth Client Secret using unified secret loader"""
        return AuthSecretLoader.get_google_client_secret()
    
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT secret key using unified secret loader"""
        secret = AuthSecretLoader.get_jwt_secret()
        env = AuthConfig.get_environment()
        
        # Validate secret in staging/production
        if env in ["staging", "production"] and not secret:
            raise ValueError(f"JWT_SECRET_KEY must be set in {env} environment")
        
        if env in ["staging", "production"] and len(secret) < 32:
            raise ValueError(f"JWT_SECRET_KEY must be at least 32 characters in {env} environment")
        
        return secret
    
    @staticmethod
    def get_service_secret() -> str:
        """Get service secret for enhanced JWT security (distinct from JWT secret)"""
        env_manager = get_env()
        service_secret = env_manager.get("SERVICE_SECRET", "")
        if not service_secret:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = env_manager.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_SECRET must be set in production/staging")
            # For test/development environments, allow empty but warn
            if env in ["test", "development"] or fast_test_mode:
                logger.warning(f"SERVICE_SECRET not configured for {env} environment")
                return ""  # Return empty string for test/dev
            # For any other environment, fail loudly
            raise ValueError(
                f"SERVICE_SECRET is not configured for {env} environment. "
                "This must be explicitly set via environment variables."
            )
        
        # Validate service secret is distinct from JWT secret
        jwt_secret = AuthSecretLoader.get_jwt_secret()
        if service_secret == jwt_secret:
            raise ValueError("SERVICE_SECRET must be different from JWT_SECRET_KEY")
        
        if len(service_secret) < 32:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = get_env().get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_SECRET must be at least 32 characters in production")
        
        return service_secret
    
    @staticmethod
    def get_service_id() -> str:
        """Get service instance ID for enhanced JWT security"""
        env_manager = get_env()
        service_id = env_manager.get("SERVICE_ID", "")
        if not service_id:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = env_manager.get("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_ID must be set in production/staging")
            # For test/development environments, allow empty but warn
            if env in ["test", "development"] or fast_test_mode:
                logger.warning(f"SERVICE_ID not configured for {env} environment")
                return "test-service-id"  # Return test ID for test/dev
            # For any other environment, fail loudly
            raise ValueError(
                f"SERVICE_ID is not configured for {env} environment. "
                "This must be explicitly set via environment variables."
            )
        
        return service_id
    
    @staticmethod
    def get_jwt_algorithm() -> str:
        """Get JWT algorithm"""
        # @marked: JWT algorithm configuration for token generation
        return get_env().get("JWT_ALGORITHM", "HS256")
    
    @staticmethod
    def get_jwt_access_expiry_minutes() -> int:
        """Get JWT access token expiry in minutes"""
        # @marked: JWT access token expiry configuration
        return int(get_env().get("JWT_ACCESS_EXPIRY_MINUTES", "15"))
    
    @staticmethod
    def get_jwt_refresh_expiry_days() -> int:
        """Get JWT refresh token expiry in days"""
        # @marked: JWT refresh token expiry configuration
        return int(get_env().get("JWT_REFRESH_EXPIRY_DAYS", "7"))
    
    @staticmethod
    def get_jwt_service_expiry_minutes() -> int:
        """Get JWT service token expiry in minutes"""
        # @marked: JWT service token expiry configuration
        return int(get_env().get("JWT_SERVICE_EXPIRY_MINUTES", "60"))
    
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL based on environment"""
        env = AuthConfig.get_environment()
        
        if env == "staging":
            return "https://app.staging.netrasystems.ai"
        elif env == "production":
            return "https://netrasystems.ai"
        
        return get_env().get("FRONTEND_URL", "http://localhost:3000")
    
    @staticmethod
    def get_auth_service_url() -> str:
        """Get auth service URL based on environment"""
        env = AuthConfig.get_environment()
        
        if env == "staging":
            return "https://auth.staging.netrasystems.ai"
        elif env == "production":
            return "https://auth.netrasystems.ai"
        
        return get_env().get("AUTH_SERVICE_URL", "http://localhost:8081")
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL for auth service.
        
        Constructs URL from individual POSTGRES_* environment variables.
        Falls back to DATABASE_URL if individual variables not set.
        """
        env_manager = get_env()
        
        # Try to construct URL from individual PostgreSQL variables
        postgres_host = env_manager.get("POSTGRES_HOST")
        postgres_port = env_manager.get("POSTGRES_PORT")
        postgres_db = env_manager.get("POSTGRES_DB")
        postgres_user = env_manager.get("POSTGRES_USER")
        postgres_password = env_manager.get("POSTGRES_PASSWORD")
        
        if postgres_host and postgres_user and postgres_db:
            # Construct URL from individual variables
            port_part = f":{postgres_port}" if postgres_port else ":5432"
            pass_part = f":{postgres_password}" if postgres_password else ""
            
            # Check for Cloud SQL Unix socket (staging/production)
            if "/cloudsql/" in postgres_host:
                # Unix socket format for Cloud SQL
                database_url = f"postgresql+asyncpg://{postgres_user}{pass_part}@/{postgres_db}?host={postgres_host}"
            else:
                # Standard TCP connection
                database_url = f"postgresql+asyncpg://{postgres_user}{pass_part}@{postgres_host}{port_part}/{postgres_db}"
                
                # Add SSL mode for staging/production
                env = AuthConfig.get_environment()
                if env in ["staging", "production"]:
                    database_url += "?sslmode=require" if "?" not in database_url else "&sslmode=require"
            
            logger.info(f"Constructed database URL from individual PostgreSQL variables")
            return database_url
        
        # Fall back to DATABASE_URL if individual variables not set
        database_url = env_manager.get("DATABASE_URL", "")
        
        if not database_url:
            env = AuthConfig.get_environment()
            # Fail loudly in staging/production if no database config
            if env in ["staging", "production"]:
                raise ValueError(
                    f"No PostgreSQL configuration found for {env} environment. "
                    "Set either POSTGRES_HOST/USER/DB or DATABASE_URL environment variables."
                )
            # Only warn in development/test
            logger.warning("No database configuration found for development/test environment")
            return database_url
        
        # Import here to avoid circular imports
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        # Return normalized URL for auth service compatibility
        return AuthDatabaseManager._normalize_database_url(database_url)
    
    @staticmethod
    def get_raw_database_url() -> str:
        """Get raw database URL from environment without normalization.
        
        Constructs URL from individual POSTGRES_* environment variables.
        Falls back to DATABASE_URL if individual variables not set.
        """
        env_manager = get_env()
        
        # Try to construct URL from individual PostgreSQL variables
        postgres_host = env_manager.get("POSTGRES_HOST")
        postgres_port = env_manager.get("POSTGRES_PORT")
        postgres_db = env_manager.get("POSTGRES_DB")
        postgres_user = env_manager.get("POSTGRES_USER")
        postgres_password = env_manager.get("POSTGRES_PASSWORD")
        
        if postgres_host and postgres_user and postgres_db:
            # Construct URL from individual variables
            port_part = f":{postgres_port}" if postgres_port else ":5432"
            pass_part = f":{postgres_password}" if postgres_password else ""
            
            # Check for Cloud SQL Unix socket (staging/production)
            if "/cloudsql/" in postgres_host:
                # Unix socket format for Cloud SQL (raw format without driver)
                return f"postgresql://{postgres_user}{pass_part}@/{postgres_db}?host={postgres_host}"
            else:
                # Standard TCP connection (raw format without driver)
                database_url = f"postgresql://{postgres_user}{pass_part}@{postgres_host}{port_part}/{postgres_db}"
                
                # Add SSL mode for staging/production
                env = AuthConfig.get_environment()
                if env in ["staging", "production"]:
                    database_url += "?sslmode=require" if "?" not in database_url else "&sslmode=require"
                
                return database_url
        
        # Fall back to DATABASE_URL if individual variables not set
        return env_manager.get("DATABASE_URL", "")
    
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL for session management"""
        env = AuthConfig.get_environment()
        # @marked: Redis URL for session storage
        redis_url = get_env().get("REDIS_URL")
        
        if not redis_url:
            # Fail loudly in staging/production if no Redis configuration
            if env in ["staging", "production"]:
                raise ValueError(
                    f"REDIS_URL not configured for {env} environment. "
                    "Redis is required for session management in production/staging."
                )
            # Only warn in development/test
            logger.warning("REDIS_URL not configured for development/test environment")
            return ""  # Return empty string for development/test
        
        return redis_url
    
    @staticmethod
    def get_session_ttl_hours() -> int:
        """Get session TTL in hours"""
        # @marked: Session TTL configuration for session expiry
        return int(get_env().get("SESSION_TTL_HOURS", "24"))
    
    @staticmethod
    def is_redis_disabled() -> bool:
        """Check if Redis is explicitly disabled"""
        # @marked: Redis disable flag for testing/development
        return get_env().get("REDIS_DISABLED", "false").lower() == "true"
    
    @staticmethod
    def log_configuration():
        """Log current configuration (without secrets)"""
        env = AuthConfig.get_environment()
        logger.info(f"Auth Service Configuration:")
        logger.info(f"  Environment: {env}")
        logger.info(f"  Frontend URL: {AuthConfig.get_frontend_url()}")
        logger.info(f"  Auth Service URL: {AuthConfig.get_auth_service_url()}")
        logger.info(f"  Google Client ID: {'*' * 10 if AuthConfig.get_google_client_id() else 'NOT SET'}")
        logger.info(f"  Google Client Secret: {'*' * 10 if AuthConfig.get_google_client_secret() else 'NOT SET'}")
        logger.info(f"  JWT Secret: {'*' * 10 if AuthConfig.get_jwt_secret() else 'NOT SET'}")
        logger.info(f"  Service Secret: {'*' * 10 if AuthConfig.get_service_secret() else 'NOT SET'}")
        logger.info(f"  Service ID: {AuthConfig.get_service_id()}")
        logger.info(f"  JWT Algorithm: {AuthConfig.get_jwt_algorithm()}")
        logger.info(f"  JWT Access Expiry: {AuthConfig.get_jwt_access_expiry_minutes()} minutes")
        logger.info(f"  JWT Refresh Expiry: {AuthConfig.get_jwt_refresh_expiry_days()} days")
        logger.info(f"  JWT Service Expiry: {AuthConfig.get_jwt_service_expiry_minutes()} minutes")
        
        # Log database URL (masked)
        db_url = AuthConfig.get_database_url()
        if db_url:
            # Mask credentials in database URL for logging
            if "://" in db_url:
                protocol, rest = db_url.split("://", 1)
                if "@" in rest:
                    _, host_part = rest.split("@", 1)
                    logger.info(f"  Database URL: {protocol}://***@{host_part}")
                else:
                    logger.info(f"  Database URL: {db_url}")
            else:
                logger.info(f"  Database URL: {'*' * 10 if db_url else 'NOT SET'}")
        else:
            logger.info(f"  Database URL: NOT SET (will use in-memory SQLite)")


def get_config() -> AuthConfig:
    """Get auth service configuration instance.
    
    Provides compatibility with test imports that expect get_config function.
    Returns a singleton instance of AuthConfig for consistent configuration access.
    """
    return AuthConfig()