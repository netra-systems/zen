"""
Auth Service Configuration
Handles environment variable loading with staging/production awareness
"""
import logging
import os

from auth_service.auth_core.secret_loader import AuthSecretLoader

logger = logging.getLogger(__name__)

class AuthConfig:
    """Centralized configuration for auth service"""
    
    # Class-level attributes for settings compatibility
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
    LOG_ASYNC_CHECKOUT = os.getenv("LOG_ASYNC_CHECKOUT", "false").lower() == "true"
    
    @staticmethod
    def get_environment() -> str:
        """Get current environment"""
        env = os.getenv("ENVIRONMENT", "development").lower()
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
        return AuthSecretLoader.get_jwt_secret()
    
    @staticmethod
    def get_service_secret() -> str:
        """Get service secret for enhanced JWT security (distinct from JWT secret)"""
        service_secret = os.getenv("SERVICE_SECRET", "")
        if not service_secret:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_SECRET must be set in production/staging")
            logger.warning("Using default service secret for development")
            return "dev-service-secret-DO-NOT-USE-IN-PRODUCTION"
        
        # Validate service secret is distinct from JWT secret
        jwt_secret = AuthSecretLoader.get_jwt_secret()
        if service_secret == jwt_secret:
            raise ValueError("SERVICE_SECRET must be different from JWT_SECRET")
        
        if len(service_secret) < 32:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_SECRET must be at least 32 characters in production")
        
        return service_secret
    
    @staticmethod
    def get_service_id() -> str:
        """Get service instance ID for enhanced JWT security"""
        service_id = os.getenv("SERVICE_ID", "")
        if not service_id:
            env = AuthConfig.get_environment()
            # Check for test mode conditions
            fast_test_mode = os.getenv("AUTH_FAST_TEST_MODE", "false").lower() == "true"
            if env in ["staging", "production"] and not (env == "test" or fast_test_mode):
                raise ValueError("SERVICE_ID must be set in production/staging")
            logger.warning("Using default service ID for development")
            return "netra-auth-dev-instance"
        
        return service_id
    
    @staticmethod
    def get_jwt_algorithm() -> str:
        """Get JWT algorithm"""
        # @marked: JWT algorithm configuration for token generation
        return os.getenv("JWT_ALGORITHM", "HS256")
    
    @staticmethod
    def get_jwt_access_expiry_minutes() -> int:
        """Get JWT access token expiry in minutes"""
        # @marked: JWT access token expiry configuration
        return int(os.getenv("JWT_ACCESS_EXPIRY_MINUTES", "15"))
    
    @staticmethod
    def get_jwt_refresh_expiry_days() -> int:
        """Get JWT refresh token expiry in days"""
        # @marked: JWT refresh token expiry configuration
        return int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "7"))
    
    @staticmethod
    def get_jwt_service_expiry_minutes() -> int:
        """Get JWT service token expiry in minutes"""
        # @marked: JWT service token expiry configuration
        return int(os.getenv("JWT_SERVICE_EXPIRY_MINUTES", "60"))
    
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL based on environment"""
        env = AuthConfig.get_environment()
        
        if env == "staging":
            return "https://app.staging.netrasystems.ai"
        elif env == "production":
            return "https://netrasystems.ai"
        
        return os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    @staticmethod
    def get_auth_service_url() -> str:
        """Get auth service URL based on environment"""
        env = AuthConfig.get_environment()
        
        if env == "staging":
            return "https://auth.staging.netrasystems.ai"
        elif env == "production":
            return "https://auth.netrasystems.ai"
        
        return os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL for auth service"""
        # Use the same DATABASE_URL as the main application
        # @marked: Database URL for auth service data persistence
        database_url = os.getenv("DATABASE_URL", "")
        
        if not database_url:
            logger.warning("No database URL configured, will use in-memory SQLite")
            return database_url
        
        # Return raw URL from environment - normalization happens at connection time
        return database_url
    
    @staticmethod
    def get_database_url_for_connection() -> str:
        """Get database URL normalized for asyncpg connections"""
        database_url = AuthConfig.get_database_url()
        
        if not database_url:
            return database_url
        
        # Import here to avoid circular imports
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        
        # Return normalized URL for auth service compatibility
        return AuthDatabaseManager._normalize_database_url(database_url)
    
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL for session management"""
        env = AuthConfig.get_environment()
        # @marked: Redis URL for session storage
        if env == "staging":
            # In staging, use Redis container name unless explicitly overridden
            default_redis_url = "redis://redis:6379/1"
        elif env == "production":
            # In production, use Redis container name
            default_redis_url = "redis://redis:6379/0"
        elif env in ["development", "test"]:
            # In development/test, use localhost
            default_redis_url = "redis://localhost:6379/1"
        else:
            # Fallback for unknown environments
            default_redis_url = "redis://redis:6379/1"
        
        return os.getenv("REDIS_URL", default_redis_url)
    
    @staticmethod
    def get_session_ttl_hours() -> int:
        """Get session TTL in hours"""
        # @marked: Session TTL configuration for session expiry
        return int(os.getenv("SESSION_TTL_HOURS", "24"))
    
    @staticmethod
    def is_redis_disabled() -> bool:
        """Check if Redis is explicitly disabled"""
        # @marked: Redis disable flag for testing/development
        return os.getenv("REDIS_DISABLED", "false").lower() == "true"
    
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