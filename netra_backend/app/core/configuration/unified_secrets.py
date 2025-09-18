"""
Unified Secrets Management Module

Provides centralized secret management functionality for the Netra platform.
Follows SSOT principles for secret access and management.
"""

import os
import subprocess
from typing import Dict, Optional, Any
from dataclasses import dataclass

from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@dataclass
class SecretConfig:
    """Configuration for secret management"""
    use_gcp_secrets: bool = True  # Default to True in Cloud Run environments
    fallback_to_env: bool = True
    cache_secrets: bool = True
    gcp_project_id: Optional[str] = None


class UnifiedSecretsManager:
    """
    Unified secrets manager for the Netra platform.
    
    Provides centralized access to secrets from various sources
    including environment variables and GCP Secret Manager.
    """
    
    def __init__(self, config: Optional[SecretConfig] = None):
        self.config = config or SecretConfig()
        self._cache: Dict[str, Any] = {}
        self.env = get_env()

        # Auto-detect GCP project ID if not provided
        if not self.config.gcp_project_id:
            self.config.gcp_project_id = self._detect_gcp_project()

        # Auto-enable GCP secrets in Cloud Run environment
        if self.env.get("K_SERVICE"):  # Cloud Run environment
            self.config.use_gcp_secrets = True
            logger.info("Cloud Run environment detected - enabling GCP Secret Manager")

        logger.info(f"UnifiedSecretsManager initialized - GCP secrets: {self.config.use_gcp_secrets}, Project: {self.config.gcp_project_id}")

    def _detect_gcp_project(self) -> Optional[str]:
        """Auto-detect GCP project ID from environment or metadata service."""
        # Try environment variable first
        project_id = self.env.get("GCP_PROJECT_ID") or self.env.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id

        # Try metadata service (in GCP environments)
        try:
            import urllib.request
            import json

            req = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                headers={"Metadata-Flavor": "Google"}
            )

            with urllib.request.urlopen(req, timeout=3) as response:
                return response.read().decode().strip()

        except Exception as e:
            logger.debug(f"Could not get GCP project from metadata service: {e}")

        return None

    def _get_secret_from_gcp(self, secret_name: str) -> Optional[str]:
        """Retrieve secret from GCP Secret Manager."""
        if not self.config.gcp_project_id:
            logger.warning("No GCP project ID configured for secret retrieval")
            return None

        try:
            # Determine gcloud command based on platform
            gcloud_cmd = "gcloud.cmd" if os.name == "nt" else "gcloud"

            result = subprocess.run(
                [gcloud_cmd, "secrets", "versions", "access", "latest",
                 "--secret", secret_name, "--project", self.config.gcp_project_id],
                capture_output=True,
                text=True,
                check=False,
                timeout=10
            )

            if result.returncode == 0:
                value = result.stdout.strip()
                logger.debug(f"Successfully retrieved secret '{secret_name}' from GCP Secret Manager")
                return value
            else:
                logger.warning(f"Failed to retrieve secret '{secret_name}' from GCP: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout retrieving secret '{secret_name}' from GCP Secret Manager")
            return None
        except Exception as e:
            logger.error(f"Error retrieving secret '{secret_name}' from GCP Secret Manager: {e}")
            return None

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value by key.
        
        Args:
            key: Secret key to retrieve
            default: Default value if secret not found
            
        Returns:
            Secret value or default
        """
        if self.config.cache_secrets and key in self._cache:
            return self._cache[key]
        
        # Try environment variable first using SSOT environment access
        value = self.env.get(key, default)
        
        if self.config.cache_secrets and value is not None:
            self._cache[key] = value
        
        return value
    
    def set_secret(self, key: str, value: str) -> None:
        """
        Set a secret value (for testing/development).
        
        Args:
            key: Secret key
            value: Secret value
        """
        if self.config.cache_secrets:
            self._cache[key] = value
        self.env.set(key, value)
    
    def clear_cache(self) -> None:
        """Clear the secrets cache"""
        self._cache.clear()
    
    def get_jwt_secret(self) -> str:
        """
        Get JWT secret using the unified JWT secret manager for consistency.
        
        This delegates to shared.jwt_secret_manager to ensure consistency 
        with auth service, preventing JWT secret mismatches between services.
        
        Raises:
            ValueError: If no JWT secret is configured for production environment
            
        Returns:
            JWT secret string, properly stripped of whitespace
        """
        # Always use the unified JWT secret manager - no fallbacks
        from shared.jwt_secret_manager import get_unified_jwt_secret
        return get_unified_jwt_secret()


# Global instance
_secrets_manager = None


def get_secrets_manager() -> UnifiedSecretsManager:
    """Get the global secrets manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = UnifiedSecretsManager()
    return _secrets_manager


def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret"""
    return get_secrets_manager().get_secret(key, default)


def set_secret(key: str, value: str) -> None:
    """Convenience function to set a secret"""
    get_secrets_manager().set_secret(key, value)


def get_jwt_secret() -> str:
    """Get JWT secret using the global secrets manager"""
    return get_secrets_manager().get_jwt_secret()


# Alias for backwards compatibility
UnifiedSecretManager = UnifiedSecretsManager