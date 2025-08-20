"""Unified Secret Management Module

Provides a unified interface for all secret management operations.
Wraps the existing SecretManager with additional functionality.

Business Value: Centralizes secret management, reducing security
incidents and ensuring compliance with Enterprise requirements.
"""

import os
from typing import Dict, Any, Optional, List
from functools import lru_cache
from app.logging_config import central_logger as logger
from .secrets import SecretManager
from .environment import EnvironmentDetector


class UnifiedSecretManager:
    """Unified interface for all secret management operations.
    
    Provides comprehensive secret loading from multiple sources
    with proper fallback and validation.
    """
    
    def __init__(self):
        """Initialize the unified secret manager."""
        self._secret_manager = SecretManager()
        self._environment_detector = EnvironmentDetector()
        self._logger = logger
        self._cache: Dict[str, Any] = {}
        
    def load_all_secrets(self) -> Dict[str, Any]:
        """Load all secrets from configured sources.
        
        Returns:
            Dict containing all loaded secrets
        """
        self._logger.info("Loading all secrets from configured sources")
        
        secrets = {}
        
        # Load from environment variables
        env_secrets = self._load_env_secrets()
        secrets.update(env_secrets)
        
        # Load from Google Secret Manager (if available)
        if self._is_gcp_available():
            gcp_secrets = self._load_gcp_secrets()
            secrets.update(gcp_secrets)
            
        # Load from AWS Secrets Manager (if available)
        if self._is_aws_available():
            aws_secrets = self._load_aws_secrets()
            secrets.update(aws_secrets)
            
        # Cache the loaded secrets
        self._cache = secrets
        
        self._logger.info(f"Loaded {len(secrets)} secrets")
        return secrets
    
    def _load_env_secrets(self) -> Dict[str, Any]:
        """Load secrets from environment variables.
        
        Returns:
            Dict of secrets from environment
        """
        secret_keys = [
            "JWT_SECRET_KEY",
            "DATABASE_PASSWORD",
            "REDIS_PASSWORD",
            "LLM_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "CLICKHOUSE_PASSWORD",
            "STRIPE_API_KEY",
            "SENDGRID_API_KEY",
            "TWILIO_AUTH_TOKEN",
            "AWS_SECRET_ACCESS_KEY",
            "GCP_SECRET_KEY"
        ]
        
        secrets = {}
        for key in secret_keys:
            value = os.environ.get(key)
            if value:
                secrets[key] = value
                self._logger.debug(f"Loaded secret from env: {key}")
                
        return secrets
    
    def _load_gcp_secrets(self) -> Dict[str, Any]:
        """Load secrets from Google Secret Manager.
        
        Returns:
            Dict of secrets from GCP
        """
        try:
            return self._secret_manager.load_all_secrets()
        except Exception as e:
            self._logger.warning(f"Failed to load GCP secrets: {e}")
            return {}
    
    def _load_aws_secrets(self) -> Dict[str, Any]:
        """Load secrets from AWS Secrets Manager.
        
        Returns:
            Dict of secrets from AWS
        """
        # Placeholder for AWS integration
        return {}
    
    def _is_gcp_available(self) -> bool:
        """Check if Google Cloud Platform is available.
        
        Returns:
            bool: True if GCP is available
        """
        return bool(os.environ.get("GOOGLE_CLOUD_PROJECT")) or \
               bool(os.environ.get("GCP_PROJECT"))
    
    def _is_aws_available(self) -> bool:
        """Check if AWS is available.
        
        Returns:
            bool: True if AWS is available
        """
        return bool(os.environ.get("AWS_REGION")) or \
               bool(os.environ.get("AWS_DEFAULT_REGION"))
    
    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a specific secret value.
        
        Args:
            key: Secret key to retrieve
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]
            
        # Try environment variable
        env_value = os.environ.get(key)
        if env_value:
            self._cache[key] = env_value
            return env_value
            
        # Try secret manager
        try:
            secret_value = self._secret_manager.get_secret(key)
            if secret_value:
                self._cache[key] = secret_value
                return secret_value
        except Exception as e:
            self._logger.debug(f"Failed to get secret {key}: {e}")
            
        return default
    
    def set_secret(self, key: str, value: str) -> bool:
        """Set a secret value (for testing/development).
        
        Args:
            key: Secret key
            value: Secret value
            
        Returns:
            bool: True if successful
        """
        if self._environment_detector.is_production():
            self._logger.error("Cannot set secrets in production")
            return False
            
        os.environ[key] = value
        self._cache[key] = value
        return True
    
    def validate_required_secrets(self, required: List[str]) -> bool:
        """Validate that all required secrets are present.
        
        Args:
            required: List of required secret keys
            
        Returns:
            bool: True if all required secrets are present
        """
        missing = []
        for key in required:
            if not self.get_secret(key):
                missing.append(key)
                
        if missing:
            self._logger.error(f"Missing required secrets: {missing}")
            return False
            
        return True
    
    def get_database_credentials(self) -> Dict[str, Any]:
        """Get database connection credentials.
        
        Returns:
            Dict with database credentials
        """
        return {
            "host": os.environ.get("DATABASE_HOST", "localhost"),
            "port": int(os.environ.get("DATABASE_PORT", "5432")),
            "database": os.environ.get("DATABASE_NAME", "netra"),
            "username": os.environ.get("DATABASE_USER", "postgres"),
            "password": self.get_secret("DATABASE_PASSWORD", "")
        }
    
    def get_redis_credentials(self) -> Dict[str, Any]:
        """Get Redis connection credentials.
        
        Returns:
            Dict with Redis credentials
        """
        return {
            "host": os.environ.get("REDIS_HOST", "localhost"),
            "port": int(os.environ.get("REDIS_PORT", "6379")),
            "db": int(os.environ.get("REDIS_DB", "0")),
            "password": self.get_secret("REDIS_PASSWORD", "")
        }
    
    def get_llm_credentials(self) -> Dict[str, Any]:
        """Get LLM API credentials.
        
        Returns:
            Dict with LLM credentials
        """
        provider = os.environ.get("LLM_PROVIDER", "openai")
        
        credentials = {
            "provider": provider,
            "model": os.environ.get("LLM_MODEL", "gpt-4")
        }
        
        # Get provider-specific API key
        if provider == "openai":
            credentials["api_key"] = self.get_secret("OPENAI_API_KEY", "")
        elif provider == "anthropic":
            credentials["api_key"] = self.get_secret("ANTHROPIC_API_KEY", "")
        elif provider == "gemini":
            credentials["api_key"] = self.get_secret("GEMINI_API_KEY", "")
        else:
            credentials["api_key"] = self.get_secret("LLM_API_KEY", "")
            
        return credentials
    
    def get_jwt_secret(self) -> str:
        """Get JWT secret key.
        
        Returns:
            str: JWT secret key
        """
        return self.get_secret("JWT_SECRET_KEY", "")
    
    def clear_cache(self):
        """Clear the secret cache."""
        self._cache.clear()
        
    @lru_cache(maxsize=1)
    def get_secret_mappings(self) -> Dict[str, str]:
        """Get mappings of secret keys to config fields.
        
        Returns:
            Dict mapping secret keys to configuration fields
        """
        return {
            "JWT_SECRET_KEY": "JWT_SECRET_KEY",
            "DATABASE_PASSWORD": "DATABASE_PASSWORD",
            "REDIS_PASSWORD": "REDIS_PASSWORD",
            "LLM_API_KEY": "LLM_API_KEY",
            "OPENAI_API_KEY": "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY": "GEMINI_API_KEY",
            "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD"
        }


# Global instance for easy access
_unified_secret_manager = UnifiedSecretManager()


def load_secrets() -> Dict[str, Any]:
    """Load all secrets from configured sources.
    
    Returns:
        Dict containing all secrets
    """
    return _unified_secret_manager.load_all_secrets()


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a specific secret value.
    
    Args:
        key: Secret key
        default: Default value if not found
        
    Returns:
        Secret value or default
    """
    return _unified_secret_manager.get_secret(key, default)