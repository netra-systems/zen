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
    
    @staticmethod
    def get_environment() -> str:
        """Get current environment"""
        env = os.getenv("ENVIRONMENT", "development").lower()
        if env in ["staging", "production", "development"]:
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
        return int(os.getenv("JWT_SERVICE_EXPIRY_MINUTES", "5"))
    
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
    
    @staticmethod
    def get_redis_url() -> str:
        """Get Redis URL for session management"""
        env = AuthConfig.get_environment()
        # @marked: Redis URL for session storage
        default_redis_url = "redis://redis:6379" if env not in ["development", "test"] else "redis://localhost:6379"
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