"""
Secret loader for auth service.
Handles loading secrets from environment variables and Google Secret Manager.
Ensures consistency with main backend service.

**UPDATED**: Now uses IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml for consistent environment access.
"""
import logging
from typing import Optional

from dev_launcher.isolated_environment import get_env

logger = logging.getLogger(__name__)


class AuthSecretLoader:
    """Load secrets for auth service based on environment."""
    
    @staticmethod
    def get_jwt_secret() -> str:
        """
        Get JWT secret with proper fallback chain.
        CRITICAL: Must match backend service secret loading for token validation consistency.
        
        Priority order:
        1. Environment-specific env vars (JWT_SECRET_STAGING, JWT_SECRET_PRODUCTION) 
        2. Environment-specific Google Secret Manager (staging/production)
        3. PRIMARY: JWT_SECRET_KEY (shared with backend service)
        4. DEPRECATED: JWT_SECRET (auth service legacy) - only for backward compatibility
        5. Development fallback (only in development)
        """
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # Try environment-specific variables first (highest priority)
        if env == "staging":
            # In staging, check for staging-specific secret first
            secret = env_manager.get("JWT_SECRET_STAGING")
            if secret:
                logger.info("Using JWT_SECRET_STAGING from environment")
                return secret
                
            # Try to load from Google Secret Manager (if available)
            secret = AuthSecretLoader._load_from_secret_manager("staging-jwt-secret")
            if secret:
                logger.info("Using staging-jwt-secret from Secret Manager")
                return secret
                
        elif env == "production":
            # In production, check for production-specific secret first
            secret = env_manager.get("JWT_SECRET_PRODUCTION")
            if secret:
                logger.info("Using JWT_SECRET_PRODUCTION from environment")
                return secret
                
            # Try to load from Google Secret Manager (if available)
            secret = AuthSecretLoader._load_from_secret_manager("prod-jwt-secret")
            if secret:
                logger.info("Using prod-jwt-secret from Secret Manager")
                return secret
        
        # CRITICAL: Check JWT_SECRET_KEY as primary fallback for consistency with backend service
        # This ensures both services use the same secret when environment-specific secrets are not available
        secret = env_manager.get("JWT_SECRET_KEY")
        if secret:
            logger.info("Using JWT_SECRET_KEY from environment (shared with backend)")
            return secret
            
        # DEPRECATED: Check JWT_SECRET for backward compatibility only
        # This should only be used when JWT_SECRET_KEY is not available
        secret = env_manager.get("JWT_SECRET")
        if secret:
            logger.warning("Using JWT_SECRET from environment (DEPRECATED - use JWT_SECRET_KEY instead)")
            return secret
        
        # Development fallback only
        if env == "development":
            logger.warning("No JWT secret found, using development default")
            return "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
        
        # No fallback in staging/production - require JWT_SECRET_KEY
        raise ValueError(f"JWT secret not configured for {env} environment. Set JWT_SECRET_KEY (recommended) or JWT_SECRET.")
    
    @staticmethod
    def _load_from_secret_manager(secret_name: str) -> Optional[str]:
        """
        Load secret from Google Secret Manager.
        This is a placeholder for actual Secret Manager integration.
        """
        try:
            # Check if running in GCP environment
            project_id = get_env().get("GCP_PROJECT_ID")
            if not project_id:
                return None
            
            # Try to import and use Secret Manager
            try:
                from google.cloud import secretmanager
                
                client = secretmanager.SecretManagerServiceClient()
                name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                
                response = client.access_secret_version(request={"name": name})
                return response.payload.data.decode("UTF-8")
                
            except ImportError:
                logger.debug("Google Cloud Secret Manager not available")
                return None
            except Exception as e:
                logger.error(f"Error accessing Secret Manager: {e}")
                return None
                
        except Exception as e:
            logger.debug(f"Secret Manager not configured: {e}")
            return None
    
    @staticmethod
    def get_google_client_id() -> str:
        """Get Google OAuth client ID with proper fallback chain."""
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        env_manager = get_env()
        # Environment-specific
        if env == "staging":
            # First check staging-specific env var
            client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_STAGING")
            if client_id:
                logger.info("Using GOOGLE_OAUTH_CLIENT_ID_STAGING from environment")
                return client_id
        elif env == "production":
            client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
            if client_id:
                logger.info("Using GOOGLE_OAUTH_CLIENT_ID_PRODUCTION from environment")
                return client_id
        
        # Generic fallback - this is what Cloud Run sets from secrets
        client_id = env_manager.get("GOOGLE_CLIENT_ID", "")
        if client_id:
            logger.info("Using GOOGLE_CLIENT_ID from environment")
        else:
            logger.warning("No Google Client ID found in environment")
        return client_id
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth client secret with proper fallback chain."""
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # Environment-specific
        if env == "staging":
            # First check staging-specific env var
            secret = env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
            if secret:
                logger.info("Using GOOGLE_OAUTH_CLIENT_SECRET_STAGING from environment")
                return secret
        elif env == "production":
            secret = env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
            if secret:
                logger.info("Using GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION from environment")
                return secret
        
        # Generic fallback - this is what Cloud Run sets from secrets
        secret = env_manager.get("GOOGLE_CLIENT_SECRET", "")
        if secret:
            logger.info("Using GOOGLE_CLIENT_SECRET from environment")
        else:
            logger.warning("No Google Client Secret found in environment")
        return secret
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL from secrets with proper normalization.
        
        Returns:
            Database URL normalized for auth service compatibility
        """
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # First try to load from Secret Manager in staging/production
        if env in ["staging", "production"]:
            secret_name = f"{env}-database-url"
            secret_url = AuthSecretLoader._load_from_secret_manager(secret_name)
            if secret_url:
                logger.info(f"Using {secret_name} from Secret Manager")
                # Import here to avoid circular imports
                from auth_service.auth_core.database.database_manager import AuthDatabaseManager
                return AuthDatabaseManager._normalize_database_url(secret_url)
        
        # Fall back to environment variable
        database_url = env_manager.get("DATABASE_URL", "")
        if not database_url:
            logger.warning("No database URL found in secrets or environment")
            return ""
        
        # Import here to avoid circular imports
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        return AuthDatabaseManager._normalize_database_url(database_url)