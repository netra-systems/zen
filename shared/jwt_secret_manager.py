"""
Shared JWT Secret Manager - CRITICAL INFRASTRUCTURE

This module provides a SINGLE source of truth for JWT secrets across ALL services.
This intentionally violates microservice independence because JWT secrets MUST
be identical between auth service and backend for authentication to work.

CRITICAL: This is the ONLY authorized source for JWT secrets in production.
"""
import os
import logging
from typing import Optional
from shared.isolated_environment import IsolatedEnvironment

logger = logging.getLogger(__name__)


class SharedJWTSecretManager:
    """
    Single source of truth for JWT secrets across all services.
    
    CRITICAL: Both auth service and backend MUST use this class
    to ensure JWT tokens can be validated across services.
    """
    
    _jwt_secret_cache: Optional[str] = None
    _validation_performed: bool = False
    
    @classmethod
    def get_jwt_secret(cls) -> str:
        """
        Get the JWT secret key that MUST be used by all services.
        
        This method implements a strict hierarchy with comprehensive logging:
        1. Cached value (if already loaded)
        2. Environment-specific secret (JWT_SECRET_STAGING, JWT_SECRET_PRODUCTION)
        3. Generic JWT_SECRET_KEY
        4. Legacy JWT_SECRET (with warning)
        5. GCP Secret Manager (for staging/production)
        6. FAIL in staging/production if not found
        
        Returns:
            str: The JWT secret key
            
        Raises:
            ValueError: If no JWT secret is configured in staging/production
        """
        # Return cached value if available
        if cls._jwt_secret_cache:
            logger.debug("JWT secret returned from cache")
            return cls._jwt_secret_cache
        
        # Determine environment using IsolatedEnvironment
        env_manager = IsolatedEnvironment.get_instance()
        environment = env_manager.get("ENVIRONMENT", "development").lower()
        
        logger.info(f"Loading JWT secret for environment: {environment}")
        
        # Log environment variables for debugging (without values)
        logger.debug(f"JWT_SECRET_STAGING available: {bool(env_manager.get('JWT_SECRET_STAGING'))}")
        logger.debug(f"JWT_SECRET_PRODUCTION available: {bool(env_manager.get('JWT_SECRET_PRODUCTION'))}")
        logger.debug(f"JWT_SECRET_KEY available: {bool(env_manager.get('JWT_SECRET_KEY'))}")
        logger.debug(f"JWT_SECRET available: {bool(env_manager.get('JWT_SECRET'))}")
        logger.debug(f"GCP_PROJECT_ID available: {bool(env_manager.get('GCP_PROJECT_ID'))}")
        
        # Try environment-specific secrets first (for staging/production)
        secret = None
        source = None
        
        if environment == "staging":
            secret = env_manager.get("JWT_SECRET_STAGING", "").strip()
            if secret:
                source = "JWT_SECRET_STAGING"
                logger.info(f"Found JWT secret from JWT_SECRET_STAGING (length: {len(secret)})")
        elif environment == "production":
            secret = env_manager.get("JWT_SECRET_PRODUCTION", "").strip()
            if secret:
                source = "JWT_SECRET_PRODUCTION"
                logger.info(f"Found JWT secret from JWT_SECRET_PRODUCTION (length: {len(secret)})")
        
        # Try generic JWT_SECRET_KEY
        if not secret:
            secret = env_manager.get("JWT_SECRET_KEY", "").strip()
            if secret:
                source = "JWT_SECRET_KEY"
                logger.info(f"Found JWT secret from JWT_SECRET_KEY (length: {len(secret)})")
        
        # Try legacy JWT_SECRET (with warning)
        if not secret:
            secret = env_manager.get("JWT_SECRET", "").strip()
            if secret:
                source = "JWT_SECRET (legacy)"
                logger.warning(
                    f"Using legacy JWT_SECRET environment variable (length: {len(secret)}). "
                    "Please migrate to JWT_SECRET_KEY"
                )
        
        # For GCP environments, try Secret Manager as last resort
        if not secret and environment in ["staging", "production"]:
            logger.info(f"Attempting to load JWT secret from GCP Secret Manager for {environment}")
            secret = cls._load_from_secret_manager(environment)
            if secret:
                source = "GCP Secret Manager"
                logger.info(f"Found JWT secret from GCP Secret Manager (length: {len(secret)})")
            else:
                logger.warning(f"Failed to load JWT secret from GCP Secret Manager for {environment}")
        
        # Validate secret exists for non-development environments
        if not secret:
            if environment in ["staging", "production"]:
                available_sources = []
                if env_manager.get("JWT_SECRET_STAGING"):
                    available_sources.append("JWT_SECRET_STAGING")
                if env_manager.get("JWT_SECRET_PRODUCTION"):
                    available_sources.append("JWT_SECRET_PRODUCTION")
                if env_manager.get("JWT_SECRET_KEY"):
                    available_sources.append("JWT_SECRET_KEY")
                if env_manager.get("JWT_SECRET"):
                    available_sources.append("JWT_SECRET")
                if env_manager.get("GCP_PROJECT_ID"):
                    available_sources.append("GCP Secret Manager (GCP_PROJECT_ID set)")
                
                error_msg = (
                    f"JWT secret is REQUIRED in {environment} environment. "
                    f"Set one of: JWT_SECRET_{environment.upper()}, JWT_SECRET_KEY. "
                    f"Available sources: {available_sources or 'NONE'}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                # Development/test fallback
                secret = "development-jwt-secret-minimum-32-characters-long"
                source = "development fallback"
                logger.warning(
                    f"Using development JWT secret fallback in {environment} environment"
                )
        
        # Validate secret quality
        cls._validate_jwt_secret(secret, environment)
        
        # Cache the secret
        cls._jwt_secret_cache = secret
        
        # Log success with hash for debugging
        import hashlib
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()[:16]
        logger.info(f"JWT secret successfully loaded from {source} for {environment} environment")
        logger.info(f"JWT secret hash (first 16 chars): {secret_hash}")
        
        return secret
    
    @classmethod
    def _load_from_secret_manager(cls, environment: str) -> Optional[str]:
        """
        Load JWT secret from GCP Secret Manager.
        
        Args:
            environment: The current environment (staging/production)
            
        Returns:
            Optional[str]: The JWT secret from Secret Manager, or None if not available
        """
        try:
            # Check for GCP environment indicators
            env_manager = IsolatedEnvironment.get_instance()
            project_id = env_manager.get("GCP_PROJECT_ID") or env_manager.get("GOOGLE_CLOUD_PROJECT")
            
            if not project_id:
                logger.debug("No GCP project ID found (GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT)")
                return None
            
            logger.info(f"Attempting to load JWT secret from GCP Secret Manager, project: {project_id}")
            
            # Import here to avoid dependency if not in GCP
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            # Try multiple possible secret names in order of preference
            secret_names = [
                f"jwt-secret-{environment}",  # Environment-specific (e.g., jwt-secret-staging)
                "jwt-secret-key",             # Generic JWT secret key
                "jwt-secret",                 # Legacy name
            ]
            
            for secret_name in secret_names:
                full_secret_name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                logger.debug(f"Trying GCP secret: {full_secret_name}")
                
                try:
                    response = client.access_secret_version(request={"name": full_secret_name})
                    secret_value = response.payload.data.decode("UTF-8").strip()
                    
                    if secret_value:
                        logger.info(f"Successfully loaded JWT secret '{secret_name}' from GCP Secret Manager for {environment} (length: {len(secret_value)})")
                        return secret_value
                    else:
                        logger.warning(f"GCP secret '{secret_name}' was empty")
                        
                except Exception as e:
                    logger.debug(f"Failed to load GCP secret '{secret_name}': {e}")
                    continue
            
            logger.warning(f"Could not load JWT secret from any GCP Secret Manager secret for {environment}")
            return None
                
        except ImportError as e:
            logger.warning(f"Google Cloud Secret Manager not available: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading from GCP Secret Manager: {e}")
            return None
    
    @classmethod
    def _validate_jwt_secret(cls, secret: str, environment: str) -> None:
        """
        Validate JWT secret meets security requirements.
        
        Args:
            secret: The JWT secret to validate
            environment: The current environment
            
        Raises:
            ValueError: If secret doesn't meet requirements
        """
        if cls._validation_performed:
            return
        
        # Length validation
        min_length = 32 if environment in ["staging", "production"] else 20
        if len(secret) < min_length:
            raise ValueError(
                f"JWT secret must be at least {min_length} characters in {environment} environment"
            )
        
        # Whitespace validation
        if secret != secret.strip():
            raise ValueError("JWT secret contains leading/trailing whitespace")
        
        # Warn about weak secrets
        if secret == "development-jwt-secret-minimum-32-characters-long" and environment != "development":
            logger.error(f"CRITICAL: Using development JWT secret in {environment} environment!")
        
        cls._validation_performed = True
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear the cached JWT secret (useful for testing).
        """
        cls._jwt_secret_cache = None
        cls._validation_performed = False
    
    @classmethod
    def validate_synchronization(cls) -> bool:
        """
        Validate that JWT secrets are properly synchronized.
        
        This method should be called during deployment validation
        to ensure all services will use the same JWT secret.
        
        Returns:
            bool: True if validation passes
            
        Raises:
            ValueError: If validation fails
        """
        secret = cls.get_jwt_secret()
        
        # Ensure secret exists and is valid
        if not secret:
            raise ValueError("JWT secret validation failed: No secret configured")
        
        # Ensure it's not a development secret in production
        env_manager = IsolatedEnvironment.get_instance()
        environment = env_manager.get("ENVIRONMENT", "development").lower()
        if environment in ["staging", "production"]:
            if "development" in secret.lower():
                raise ValueError(
                    f"JWT secret validation failed: Development secret used in {environment}"
                )
        
        logger.info(f"JWT secret synchronization validated for {environment}")
        return True
    
    @classmethod
    def force_environment_consistency(cls, target_environment: str) -> str:
        """
        Force consistent environment detection across all services.
        
        This method ensures that regardless of how each service detects the environment,
        they will all use the same JWT secret loading logic.
        
        Args:
            target_environment: The environment to force (staging, production, development)
            
        Returns:
            str: The JWT secret for the specified environment
            
        Raises:
            ValueError: If the environment is invalid or secret cannot be loaded
        """
        if target_environment not in ["staging", "production", "development", "test"]:
            raise ValueError(f"Invalid environment: {target_environment}")
        
        # Clear cache to force fresh loading
        cls.clear_cache()
        
        # Temporarily override environment
        env_manager = IsolatedEnvironment.get_instance()
        original_env = env_manager.get("ENVIRONMENT")
        
        try:
            # Set the target environment
            env_manager.set("ENVIRONMENT", target_environment, "jwt_secret_manager_override")
            
            # Load secret with forced environment
            secret = cls.get_jwt_secret()
            
            logger.info(f"Successfully loaded JWT secret for forced environment: {target_environment}")
            return secret
            
        finally:
            # Restore original environment if it existed
            if original_env:
                env_manager.set("ENVIRONMENT", original_env, "jwt_secret_manager_restore")
            else:
                env_manager.delete("ENVIRONMENT", "jwt_secret_manager_restore")
            
            # Clear cache again to prevent cross-contamination
            cls.clear_cache()
    
    @classmethod
    def get_secret_loading_diagnostics(cls) -> dict:
        """
        Get comprehensive diagnostics about JWT secret loading.
        
        This method provides detailed information about the current state
        of JWT secret loading for debugging purposes.
        
        Returns:
            dict: Diagnostic information
        """
        env_manager = IsolatedEnvironment.get_instance()
        environment = env_manager.get("ENVIRONMENT", "development").lower()
        
        diagnostics = {
            "current_environment": environment,
            "cache_status": {
                "has_cached_secret": cls._jwt_secret_cache is not None,
                "validation_performed": cls._validation_performed
            },
            "environment_variables": {
                "JWT_SECRET_STAGING": bool(env_manager.get("JWT_SECRET_STAGING")),
                "JWT_SECRET_PRODUCTION": bool(env_manager.get("JWT_SECRET_PRODUCTION")), 
                "JWT_SECRET_KEY": bool(env_manager.get("JWT_SECRET_KEY")),
                "JWT_SECRET": bool(env_manager.get("JWT_SECRET")),
                "GCP_PROJECT_ID": bool(env_manager.get("GCP_PROJECT_ID")),
                "GOOGLE_CLOUD_PROJECT": bool(env_manager.get("GOOGLE_CLOUD_PROJECT"))
            },
            "secret_source_priority": [
                f"JWT_SECRET_{environment.upper()}" if environment in ["staging", "production"] else "N/A",
                "JWT_SECRET_KEY",
                "JWT_SECRET (legacy)",
                "GCP Secret Manager" if environment in ["staging", "production"] else "N/A",
                "Development fallback" if environment in ["development", "test"] else "N/A"
            ]
        }
        
        # If we have a cached secret, add its hash for verification
        if cls._jwt_secret_cache:
            import hashlib
            secret_hash = hashlib.sha256(cls._jwt_secret_cache.encode()).hexdigest()[:16]
            diagnostics["cached_secret_hash"] = secret_hash
            diagnostics["cached_secret_length"] = len(cls._jwt_secret_cache)
        
        return diagnostics


# Module-level convenience function
def get_shared_jwt_secret() -> str:
    """
    Get the shared JWT secret for all services.
    
    This is a convenience function that delegates to SharedJWTSecretManager.
    
    Returns:
        str: The JWT secret key
    """
    return SharedJWTSecretManager.get_jwt_secret()


# Validation function for deployment
def validate_jwt_configuration() -> bool:
    """
    Validate JWT configuration for deployment.
    
    Returns:
        bool: True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    return SharedJWTSecretManager.validate_synchronization()