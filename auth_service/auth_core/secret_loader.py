"""
Secret loader for auth service.
Handles loading secrets using the central configuration validator (SSOT).

**UPDATED**: Uses central configuration validation for consistency across all services.
Maintains auth service independence while using shared validation logic.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Use auth_service's own isolated environment management - NEVER import from dev_launcher or netra_backend
from auth_service.auth_core.isolated_environment import get_env

# SSOT: Import central configuration validator
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from shared.configuration import get_central_validator
except ImportError as e:
    logger.error(f"Failed to import central configuration validator: {e}")
    # Fallback for development - can be removed once all environments have shared module
    get_central_validator = None

logger = logging.getLogger(__name__)


class AuthSecretLoader:
    """Load secrets for auth service based on environment."""
    
    @staticmethod
    def get_jwt_secret() -> str:
        """
        Get JWT secret using central configuration validator (SSOT).
        
        This method now delegates to the central validator to ensure consistency
        across all services and eliminate duplicate validation logic.
        """
        if get_central_validator is not None:
            # Use central validator (SSOT)
            try:
                validator = get_central_validator(lambda key, default=None: get_env().get(key, default))
                return validator.get_jwt_secret()
            except Exception as e:
                logger.error(f"Central validator failed: {e}")
                # If central validator fails, raise error - no legacy fallback
                raise ValueError(f"JWT secret configuration failed: {e}")
        
        # If central validator not available, raise error - no legacy fallback
        raise ValueError("Central configuration validator not available and legacy fallback removed")
    
    
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
        if env in ["development", "test"]:
            # Test environment uses same config as development
            # First check development-specific env var
            client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT")
            if client_id:
                logger.info(f"Using GOOGLE_OAUTH_CLIENT_ID_DEVELOPMENT from environment for {env}")
                return client_id
        elif env == "staging":
            # First check staging-specific env var
            client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_STAGING")
            if client_id:
                # CRITICAL: Log full client ID for staging debugging
                logger.info(f"🔍 STAGING OAuth: Using GOOGLE_OAUTH_CLIENT_ID_STAGING = {client_id}")
                logger.info(f"🔍 STAGING OAuth: Client ID length = {len(client_id)}")
                logger.info(f"🔍 STAGING OAuth: Client ID starts with: {client_id[:30]}...")
                return client_id
            else:
                # Log what variables are available
                logger.error("❌ STAGING OAuth: GOOGLE_OAUTH_CLIENT_ID_STAGING is NOT set!")
                available_vars = [k for k in env_manager.get_all().keys() if 'GOOGLE' in k and 'CLIENT' in k]
                logger.error(f"❌ STAGING OAuth: Available Google client vars: {available_vars}")
        elif env == "production":
            client_id = env_manager.get("GOOGLE_OAUTH_CLIENT_ID_PRODUCTION")
            if client_id:
                logger.info("Using GOOGLE_OAUTH_CLIENT_ID_PRODUCTION from environment")
                return client_id
        
        # No fallback to generic GOOGLE_CLIENT_ID - use environment-specific variables only
        logger.error(f"❌ CRITICAL: No Google Client ID found for {env} environment")
        logger.error(f"❌ CRITICAL: Expected variable for {env}: GOOGLE_OAUTH_CLIENT_ID_{env.upper()}")
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
        if env in ["development", "test"]:
            # Test environment uses same config as development
            # First check development-specific env var
            secret = env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT")
            if secret:
                logger.info(f"Using GOOGLE_OAUTH_CLIENT_SECRET_DEVELOPMENT from environment for {env}")
                return secret
        elif env == "staging":
            # First check staging-specific env var
            secret = env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_STAGING")
            if secret:
                # CRITICAL: Log secret presence for staging debugging (not the actual secret)
                logger.info(f"🔍 STAGING OAuth: Using GOOGLE_OAUTH_CLIENT_SECRET_STAGING (length={len(secret)})")
                logger.info(f"🔍 STAGING OAuth: Secret starts with: {secret[:5]}...")
                return secret
            else:
                logger.error("❌ STAGING OAuth: GOOGLE_OAUTH_CLIENT_SECRET_STAGING is NOT set!")
                available_vars = [k for k in env_manager.get_all().keys() if 'GOOGLE' in k and 'SECRET' in k]
                logger.error(f"❌ STAGING OAuth: Available Google secret vars: {available_vars}")
        elif env == "production":
            secret = env_manager.get("GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION")
            if secret:
                logger.info("Using GOOGLE_OAUTH_CLIENT_SECRET_PRODUCTION from environment")
                return secret
        
        # No fallback to generic GOOGLE_CLIENT_SECRET - use environment-specific variables only
        logger.error(f"❌ CRITICAL: No Google Client Secret found for {env} environment")
        logger.error(f"❌ CRITICAL: Expected variable for {env}: GOOGLE_OAUTH_CLIENT_SECRET_{env.upper()}")
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
                # Ensure async format for auth service
                from shared.database_url_builder import DatabaseURLBuilder
                return DatabaseURLBuilder.format_url_for_driver(secret_url, 'asyncpg')
        
        # Fall back to DATABASE_URL environment variable
        database_url = env_manager.get("DATABASE_URL", "")
        if not database_url:
            logger.warning("No database configuration found in secrets or environment")
            return ""
        
        # Ensure async format for auth service
        from shared.database_url_builder import DatabaseURLBuilder
        return DatabaseURLBuilder.format_url_for_driver(database_url, 'asyncpg')
    
    @staticmethod
    def get_E2E_OAUTH_SIMULATION_KEY() -> Optional[str]:
        """Get E2E test bypass key for staging environment.
        
        This key is used to authenticate E2E tests on staging without OAuth.
        Only available in staging environment for security.
        
        Returns:
            The E2E bypass key from Google Secret Manager or None if not configured
        """
        env_manager = get_env()
        env = env_manager.get("ENVIRONMENT", "development").lower()
        
        # Only allow loading bypass key in staging
        if env != "staging":
            logger.warning(f"E2E bypass key requested in {env} environment - not allowed")
            return None
        
        # Try environment variable first (for local testing)
        bypass_key = env_manager.get("E2E_OAUTH_SIMULATION_KEY")
        if bypass_key:
            logger.info("Using E2E_OAUTH_SIMULATION_KEY from environment variable")
            return bypass_key
        
        # Try to load from Google Secret Manager
        bypass_key = AuthSecretLoader._load_from_secret_manager("e2e-bypass-key")
        if bypass_key:
            logger.info("Using e2e-bypass-key from Google Secret Manager")
            return bypass_key
        
        logger.warning("E2E bypass key not configured in staging environment")
        return None