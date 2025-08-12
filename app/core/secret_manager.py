"""Secret management utilities for configuration loading."""

import os
from typing import Dict, Any, Optional
from app.logging_config import central_logger as logger
from google.cloud import secretmanager
from tenacity import retry, stop_after_attempt, wait_fixed


class SecretManagerError(Exception):
    """Raised when secret management operations fail."""
    pass


class SecretManager:
    """Manages loading secrets from Google Cloud Secret Manager with fallback to environment variables."""
    
    def __init__(self):
        self._logger = logger
        self._client: Optional[secretmanager.SecretManagerServiceClient] = None
        self._project_id = "304612253870"  # Default project ID
        
    def load_secrets(self) -> Dict[str, Any]:
        """Load secrets from Secret Manager or environment variables as fallback."""
        # Skip Google Cloud Secret Manager in local development
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        if environment in ["development", "testing"] or not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            self._logger.info("Using environment variables for secrets (local development mode)")
            return self._load_from_environment()
        
        try:
            secrets = self._load_from_secret_manager()
            if secrets:
                return secrets
        except Exception as e:
            self._logger.warning(f"Failed to load from Secret Manager: {e}")
        
        # Fallback to environment variables
        return self._load_from_environment()
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_secret_client(self) -> secretmanager.SecretManagerServiceClient:
        """Get or create a Secret Manager client with retry logic."""
        if self._client is None:
            try:
                self._client = secretmanager.SecretManagerServiceClient()
                return self._client
            except Exception as e:
                raise SecretManagerError(f"Failed to create Secret Manager client: {e}")
        return self._client
    
    def _load_from_secret_manager(self) -> Dict[str, Any]:
        """Load secrets from Google Cloud Secret Manager."""
        try:
            client = self._get_secret_client()
            secrets = {}
            
            # Define the secrets we need to load
            secret_names = [
                "gemini-api-key",
                "google-client-id", 
                "google-client-secret",
                "langfuse-secret-key",
                "langfuse-public-key",
                "clickhouse-default-password",
                "clickhouse-development-password",
                "jwt-secret-key",
                "fernet-key",
                "redis-default"
            ]
            
            for secret_name in secret_names:
                try:
                    secret_value = self._fetch_secret(client, secret_name)
                    if secret_value:
                        secrets[secret_name] = secret_value
                except Exception as e:
                    self._logger.warning(f"Failed to fetch secret {secret_name}: {e}")
            
            return secrets
            
        except Exception as e:
            self._logger.error(f"Error loading secrets from Secret Manager: {e}")
            raise SecretManagerError(f"Secret Manager loading failed: {e}")
    
    def _fetch_secret(self, client: secretmanager.SecretManagerServiceClient, secret_name: str, version: str = "latest") -> Optional[str]:
        """Fetch a single secret from Secret Manager."""
        try:
            name = f"projects/{self._project_id}/secrets/{secret_name}/versions/{version}"
            response = client.access_secret_version(name=name)
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            self._logger.warning(f"Failed to fetch secret {secret_name}: {e}")
            return None
    
    def _load_from_environment(self) -> Dict[str, Any]:
        """Load secrets from environment variables as fallback."""
        env_mapping = {
            "gemini-api-key": "GEMINI_API_KEY",
            "google-client-id": "GOOGLE_CLIENT_ID",
            "google-client-secret": "GOOGLE_CLIENT_SECRET",
            "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
            "langfuse-public-key": "LANGFUSE_PUBLIC_KEY",
            "clickhouse-default-password": "CLICKHOUSE_DEFAULT_PASSWORD",
            "clickhouse-development-password": "CLICKHOUSE_DEVELOPMENT_PASSWORD",
            "jwt-secret-key": "JWT_SECRET_KEY",
            "fernet-key": "FERNET_KEY",
            "redis-default": "REDIS_PASSWORD"
        }
        
        secrets = {}
        for secret_name, env_var in env_mapping.items():
            value = os.environ.get(env_var)
            if value:
                secrets[secret_name] = value
        
        self._logger.info(f"Loaded {len(secrets)} secrets from environment variables")
        return secrets