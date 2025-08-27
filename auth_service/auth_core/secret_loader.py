"""
Secret loader for auth service.
Handles loading secrets from environment variables and Google Secret Manager.
Ensures consistency with main backend service.

**UPDATED**: Now uses auth_service's own IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml and SPEC/independent_services.xml for consistent 
environment access while maintaining complete microservice independence.
"""
import logging
from typing import Optional

# Use auth_service's own isolated environment management - NEVER import from dev_launcher or netra_backend
from auth_service.auth_core.isolated_environment import get_env

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
        
        # No fallback in any environment - require explicit JWT secret configuration
        raise ValueError(
            f"JWT secret not configured for {env} environment. "
            "Set JWT_SECRET_KEY (recommended) or JWT_SECRET environment variable."
        )
    
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
        """Get Google OAuth client ID with proper fallback chain.
        
        TOMBSTONE: GOOGLE_CLIENT_ID variable superseded by environment-specific variables:
        - GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT
        - GOOGLE_OAUTH_CLIENT_ID_STAGING
        - GOOGLE_OAUTH_CLIENT_ID_PRODUCTION
        """
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # Environment-specific with higher priority than generic
        if env == "development":
            # First check development-specific env var
            client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
            if client_id:
                logger.info("Using GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT from environment")
                return client_id
        elif env == "staging":
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
        
        # No fallback to generic GOOGLE_CLIENT_ID - use environment-specific variables only
        logger.warning(f"No Google Client ID found for {env} environment")
        return ""
    
    @staticmethod
    def get_google_client_secret() -> str:
        """Get Google OAuth client secret with proper fallback chain.
        
        TOMBSTONE: GOOGLE_CLIENT_SECRET variable superseded by environment-specific variables:
        - GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT
        - GOOGLE_OAUTH_CLIENT_SECRET_STAGING
        - GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION
        """
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # Environment-specific with higher priority than generic
        if env == "development":
            # First check development-specific env var
            secret = env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT")
            if secret:
                logger.info("Using GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT from environment")
                return secret
        elif env == "staging":
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
        
        # No fallback to generic GOOGLE_CLIENT_SECRET - use environment-specific variables only
        logger.warning(f"No Google Client Secret found for {env} environment")
        return ""
    
    @staticmethod
    def get_database_url() -> str:
        """Get database URL from secrets with proper normalization.
        
        Constructs URL from individual POSTGRES_* environment variables.
        Falls back to DATABASE_URL if individual variables not set.
        
        Returns:
            Database URL normalized for auth service compatibility
        """
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # Try to construct URL from individual PostgreSQL variables
        postgres_host = env_manager.get("POSTGRES_HOST")
        postgres_port = env_manager.get("POSTGRES_PORT")
        postgres_db = env_manager.get("POSTGRES_DB")
        postgres_user = env_manager.get("POSTGRES_USER")
        postgres_password = env_manager.get("POSTGRES_PASSWORD")
        
        if postgres_host and postgres_user and postgres_db:
            # Use DatabaseURLBuilder for proper URL construction
            from shared.database_url_builder import DatabaseURLBuilder
            
            # Create env vars dict for builder
            env_vars = env_manager.get_all().copy()
            env_vars['POSTGRES_HOST'] = postgres_host
            env_vars['POSTGRES_PORT'] = postgres_port or '5432'
            env_vars['POSTGRES_DB'] = postgres_db
            env_vars['POSTGRES_USER'] = postgres_user
            if postgres_password:
                env_vars['POSTGRES_PASSWORD'] = postgres_password
            env_vars['ENVIRONMENT'] = env
            
            # Use builder to construct proper URL
            builder = DatabaseURLBuilder(env_vars)
            
            # Check for Cloud SQL
            if builder.cloud_sql.is_cloud_sql:
                database_url = builder.cloud_sql.async_url
            else:
                # Use TCP with SSL for staging/production
                if env in ["staging", "production"]:
                    database_url = builder.tcp.async_url_with_ssl
                else:
                    database_url = builder.tcp.async_url
            
            if database_url:
                logger.info(f"Constructed database URL from individual PostgreSQL variables using DatabaseURLBuilder")
                return database_url
        
        # Try to load from Secret Manager in staging/production (legacy support)
        if env in ["staging", "production"]:
            secret_name = f"{env}-database-url"
            secret_url = AuthSecretLoader._load_from_secret_manager(secret_name)
            if secret_url:
                logger.info(f"Using {secret_name} from Secret Manager")
                # Import here to avoid circular imports
                from auth_service.auth_core.database.database_manager import AuthDatabaseManager
                return AuthDatabaseManager._normalize_database_url(secret_url)
        
        # Fall back to DATABASE_URL environment variable
        database_url = env_manager.get("DATABASE_URL", "")
        if not database_url:
            logger.warning("No database configuration found in secrets or environment")
            return ""
        
        # Import here to avoid circular imports
        from auth_service.auth_core.database.database_manager import AuthDatabaseManager
        return AuthDatabaseManager._normalize_database_url(database_url)