"""
Auth Service Configuration
Handles environment variable loading with staging/production awareness
"""
import os
import logging

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
        """Get Google OAuth Client ID based on environment"""
        env = AuthConfig.get_environment()
        
        # Check environment-specific variables first
        if env == "staging":
            client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID_STAGING")
            if client_id:
                return client_id
        elif env == "production":
            client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
            if client_id:
                return client_id
        
        # Fall back to generic variable
        return os.getenv("GOOGLE_CLIENT_ID", "")
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth Client Secret based on environment"""
        env = AuthConfig.get_environment()
        
        # Check environment-specific variables first
        if env == "staging":
            secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
            if secret:
                return secret
        elif env == "production":
            secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
            if secret:
                return secret
        
        # Fall back to generic variable
        return os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    @staticmethod
    def get_jwt_secret() -> str:
        """Get JWT secret key"""
        env = AuthConfig.get_environment()
        
        # Check environment-specific variables first
        if env == "staging":
            secret = os.getenv("JWT_SECRET_STAGING")
            if secret:
                return secret
        elif env == "production":
            secret = os.getenv("JWT_SECRET_PRODUCTION")
            if secret:
                return secret
        
        # Fall back to generic variable
        return os.getenv("JWT_SECRET", os.getenv("JWT_SECRET_KEY", ""))
    
    @staticmethod
    def get_frontend_url() -> str:
        """Get frontend URL based on environment"""
        env = AuthConfig.get_environment()
        
        if env == "staging":
            return "https://staging.netrasystems.ai"
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
        # Check for auth-specific database URL first
        database_url = os.getenv("DATABASE_URL", os.getenv("DATABASE_URL", ""))
        
        if not database_url:
            logger.warning("No database URL configured, will use in-memory SQLite")
        
        return database_url
    
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