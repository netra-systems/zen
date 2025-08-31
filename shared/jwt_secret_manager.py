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
        
        This method implements a strict hierarchy:
        1. Cached value (if already loaded)
        2. Environment-specific secret (JWT_SECRET_STAGING, JWT_SECRET_PRODUCTION)
        3. Generic JWT_SECRET_KEY
        4. Legacy JWT_SECRET (with warning)
        5. FAIL in staging/production if not found
        
        Returns:
            str: The JWT secret key
            
        Raises:
            ValueError: If no JWT secret is configured in staging/production
        """
        # Return cached value if available
        if cls._jwt_secret_cache:
            return cls._jwt_secret_cache
        
        # Determine environment
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        
        # Try environment-specific secrets first (for staging/production)
        secret = None
        source = None
        
        if environment == "staging":
            secret = os.environ.get("JWT_SECRET_STAGING", "").strip()
            if secret:
                source = "JWT_SECRET_STAGING"
        elif environment == "production":
            secret = os.environ.get("JWT_SECRET_PRODUCTION", "").strip()
            if secret:
                source = "JWT_SECRET_PRODUCTION"
        
        # Try generic JWT_SECRET_KEY
        if not secret:
            secret = os.environ.get("JWT_SECRET_KEY", "").strip()
            if secret:
                source = "JWT_SECRET_KEY"
        
        # Try legacy JWT_SECRET (with warning)
        if not secret:
            secret = os.environ.get("JWT_SECRET", "").strip()
            if secret:
                source = "JWT_SECRET (legacy)"
                logger.warning(
                    "Using legacy JWT_SECRET environment variable. "
                    "Please migrate to JWT_SECRET_KEY"
                )
        
        # For GCP environments, try Secret Manager as last resort
        if not secret and environment in ["staging", "production"]:
            secret = cls._load_from_secret_manager(environment)
            if secret:
                source = "GCP Secret Manager"
        
        # Validate secret exists for non-development environments
        if not secret:
            if environment in ["staging", "production"]:
                raise ValueError(
                    f"JWT secret is REQUIRED in {environment} environment. "
                    f"Set one of: JWT_SECRET_{environment.upper()}, JWT_SECRET_KEY"
                )
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
        logger.info(f"JWT secret loaded from {source} for {environment} environment")
        
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
            # Only attempt if we're in GCP environment
            project_id = os.environ.get("GCP_PROJECT_ID")
            if not project_id:
                return None
            
            # Import here to avoid dependency if not in GCP
            from google.cloud import secretmanager
            
            client = secretmanager.SecretManagerServiceClient()
            
            # Try to load jwt-secret-key from Secret Manager
            secret_name = f"projects/{project_id}/secrets/jwt-secret-key/versions/latest"
            
            try:
                response = client.access_secret_version(request={"name": secret_name})
                secret_value = response.payload.data.decode("UTF-8").strip()
                logger.info(f"Loaded JWT secret from GCP Secret Manager for {environment}")
                return secret_value
            except Exception as e:
                logger.warning(f"Could not load JWT secret from Secret Manager: {e}")
                return None
                
        except ImportError:
            logger.debug("Google Cloud Secret Manager not available")
            return None
        except Exception as e:
            logger.warning(f"Error loading from Secret Manager: {e}")
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
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        if environment in ["staging", "production"]:
            if "development" in secret.lower():
                raise ValueError(
                    f"JWT secret validation failed: Development secret used in {environment}"
                )
        
        logger.info(f"JWT secret synchronization validated for {environment}")
        return True


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