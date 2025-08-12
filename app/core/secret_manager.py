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
        # Use numerical project ID for Secret Manager (required by API)
        # Staging: Use numerical ID if provided, otherwise use project name
        self._project_id = os.environ.get("GCP_PROJECT_ID_NUMERICAL_STAGING", 
                                         os.environ.get("SECRET_MANAGER_PROJECT_ID",
                                         "304612253870"))  # Default to production numerical ID
        
    def load_secrets(self) -> Dict[str, Any]:
        """Load secrets from Secret Manager or environment variables as fallback."""
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        
        # Check if we should load from Secret Manager
        should_load_secrets = (
            os.environ.get("LOAD_SECRETS", "false").lower() == "true" or
            environment == "staging" or
            environment == "production" or
            os.environ.get("K_SERVICE")  # Running in Cloud Run
        )
        
        # Skip Google Cloud Secret Manager in local development unless explicitly enabled
        if not should_load_secrets and environment in ["development", "testing"]:
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
            
            # Check if we're in staging environment
            environment = os.environ.get("ENVIRONMENT", "development").lower()
            is_staging = environment == "staging" or os.environ.get("K_SERVICE")  # Cloud Run indicator
            
            # Define the secrets we need to load from Google Secret Manager
            secret_names = [
                # LLM API Keys (gemini is required, others are optional)
                "gemini-api-key",       # Required - used for default LLM operations
                "anthropic-api-key",    # Optional - for Anthropic models
                "openai-api-key",       # Optional - for OpenAI models
                "cohere-api-key",       # Optional - for Cohere models
                "mistral-api-key",      # Optional - for Mistral models
                
                # OAuth and Authentication
                "google-client-id",     # Required for Google OAuth
                "google-client-secret", # Required for Google OAuth
                "jwt-secret-key",       # Required - JWT token signing
                "fernet-key",           # Required - encryption key
                
                # Observability
                "langfuse-secret-key",  # Optional - for LLM monitoring
                "langfuse-public-key",  # Optional - for LLM monitoring
                
                # Database Passwords
                "clickhouse-default-password",      # Optional - ClickHouse access
                "clickhouse-development-password",  # Optional - ClickHouse dev
                "redis-default",                    # Optional - Redis password
                
                # Additional secrets that may be needed
                "slack-webhook-url",    # Optional - for notifications
                "sendgrid-api-key",     # Optional - for email
                "sentry-dsn"            # Optional - for error tracking
            ]
            
            for secret_name in secret_names:
                try:
                    # In staging, append -staging suffix to secret names
                    actual_secret_name = f"{secret_name}-staging" if is_staging else secret_name
                    self._logger.debug(f"Fetching secret: {actual_secret_name} (original: {secret_name})")
                    
                    secret_value = self._fetch_secret(client, actual_secret_name)
                    if secret_value:
                        # Store with original name as key for config mapping
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
            secret_value = response.payload.data.decode("UTF-8")
            self._logger.debug(f"Successfully fetched secret: {secret_name}")
            return secret_value
        except Exception as e:
            self._logger.debug(f"Failed to fetch secret {secret_name} from project {self._project_id}: {e}")
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
            "redis-default": "REDIS_PASSWORD",
            # LLM API Keys
            "anthropic-api-key": "ANTHROPIC_API_KEY",
            "openai-api-key": "OPENAI_API_KEY",
            "cohere-api-key": "COHERE_API_KEY",
            "mistral-api-key": "MISTRAL_API_KEY",
            # Additional services
            "slack-webhook-url": "SLACK_WEBHOOK_URL",
            "sendgrid-api-key": "SENDGRID_API_KEY",
            "sentry-dsn": "SENTRY_DSN"
        }
        
        secrets = {}
        for secret_name, env_var in env_mapping.items():
            value = os.environ.get(env_var)
            if value:
                secrets[secret_name] = value
        
        self._logger.info(f"Loaded {len(secrets)} secrets from environment variables")
        return secrets