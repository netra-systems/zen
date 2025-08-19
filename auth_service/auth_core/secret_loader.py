"""
Secret loader for auth service.
Handles loading secrets from environment variables and Google Secret Manager.
Ensures consistency with main backend service.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AuthSecretLoader:
    """Load secrets for auth service based on environment."""
    
    @staticmethod
    def get_jwt_secret() -> str:
        """
        Get JWT secret with proper fallback chain.
        CRITICAL: Must match backend service secret loading for token validation consistency.
        
        Priority order:
        1. Environment-specific Google Secret Manager (staging/production)
        2. Environment-specific env vars (JWT_SECRET_STAGING, JWT_SECRET_PRODUCTION)
        3. Primary: JWT_SECRET_KEY (shared with backend service)
        4. Fallback: JWT_SECRET (auth service legacy)
        5. Development fallback (only in development)
        """
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        # Try environment-specific variables first
        if env == "staging":
            # In staging, check for staging-specific secret
            secret = os.getenv("JWT_SECRET_STAGING")
            if secret:
                logger.info("Using JWT_SECRET_STAGING from environment")
                return secret
                
            # Try to load from Google Secret Manager (if available)
            secret = AuthSecretLoader._load_from_secret_manager("staging-jwt-secret")
            if secret:
                logger.info("Using staging-jwt-secret from Secret Manager")
                return secret
                
        elif env == "production":
            # In production, check for production-specific secret
            secret = os.getenv("JWT_SECRET_PRODUCTION")
            if secret:
                logger.info("Using JWT_SECRET_PRODUCTION from environment")
                return secret
                
            # Try to load from Google Secret Manager (if available)
            secret = AuthSecretLoader._load_from_secret_manager("prod-jwt-secret")
            if secret:
                logger.info("Using prod-jwt-secret from Secret Manager")
                return secret
        
        # Fall back to generic variables (for all environments)
        # CRITICAL: Check JWT_SECRET_KEY first to match backend service behavior
        secret = os.getenv("JWT_SECRET_KEY")
        if secret:
            logger.info("Using JWT_SECRET_KEY from environment (shared with backend)")
            return secret
            
        # Legacy fallback for JWT_SECRET (auth service specific)
        secret = os.getenv("JWT_SECRET")
        if secret:
            logger.warning("Using JWT_SECRET from environment (legacy - should use JWT_SECRET_KEY)")
            return secret
        
        # Development fallback only
        if env == "development":
            logger.warning("No JWT secret found, using development default")
            return "dev-secret-key-DO-NOT-USE-IN-PRODUCTION"
        
        # No fallback in staging/production
        raise ValueError(f"JWT secret not configured for {env} environment")
    
    @staticmethod
    def _load_from_secret_manager(secret_name: str) -> Optional[str]:
        """
        Load secret from Google Secret Manager.
        This is a placeholder for actual Secret Manager integration.
        """
        try:
            # Check if running in GCP environment
            project_id = os.getenv("GCP_PROJECT_ID")
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
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        # Environment-specific
        if env == "staging":
            client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID_STAGING")
            if client_id:
                return client_id
        elif env == "production":
            client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
            if client_id:
                return client_id
        
        # Generic fallback
        return os.getenv("GOOGLE_CLIENT_ID", "")
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth client secret with proper fallback chain."""
        env = os.getenv("ENVIRONMENT", "development").lower()
        
        # Environment-specific
        if env == "staging":
            secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
            if secret:
                return secret
        elif env == "production":
            secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
            if secret:
                return secret
        
        # Generic fallback
        return os.getenv("GOOGLE_CLIENT_SECRET", "")