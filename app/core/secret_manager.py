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
        
        # Log which project we're using for Secret Manager
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        if environment in ["staging", "production"] or os.environ.get("K_SERVICE"):
            self._logger.info(f"Secret Manager initialized with project ID: {self._project_id} for environment: {environment}")
        
    def load_secrets(self) -> Dict[str, Any]:
        """Load secrets from Secret Manager with environment variables as base, Google Secrets supersede."""
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        
        # Check if we should load from Secret Manager
        should_load_secrets = (
            os.environ.get("LOAD_SECRETS", "false").lower() == "true" or
            environment == "staging" or
            environment == "production" or
            os.environ.get("K_SERVICE")  # Running in Cloud Run
        )
        
        # Start with environment variables as base
        self._logger.info(f"Starting secret loading process for environment: {environment}")
        secrets = self._load_from_environment()
        env_secret_count = len(secrets)
        
        # Skip Google Cloud Secret Manager in local development unless explicitly enabled
        if not should_load_secrets and environment in ["development", "testing"]:
            self._logger.info(f"Using only environment variables for secrets (local development mode): {env_secret_count} secrets loaded")
            return secrets
        
        # Load and merge Google Secrets (they supersede environment variables)
        self._logger.info(f"Attempting to load Google Secrets for environment: {environment}")
        try:
            google_secrets = self._load_from_secret_manager()
            if google_secrets:
                # Google secrets supersede environment variables
                before_merge = len(secrets)
                secrets.update(google_secrets)  # This will overwrite env vars with Google Secrets
                self._logger.info(f"Google Secrets loaded successfully: {len(google_secrets)} secrets from Google Secret Manager")
                self._logger.info(f"Total secrets after merge: {len(secrets)} (Base env: {env_secret_count}, Google overrides: {len(google_secrets)})")
                
                # Log which secrets were superseded
                superseded = [key for key in google_secrets if key in secrets]
                if superseded:
                    self._logger.debug(f"Google Secrets superseded environment variables for: {', '.join(superseded)}")
            else:
                self._logger.warning("No secrets loaded from Google Secret Manager")
        except Exception as e:
            self._logger.error(f"Failed to load from Google Secret Manager, using environment variables only: {e}")
        
        return secrets
    
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
            self._logger.info(f"Initializing Google Secret Manager client for project: {self._project_id}")
            client = self._get_secret_client()
            secrets = {}
            
            # Check if we're in staging environment
            environment = os.environ.get("ENVIRONMENT", "development").lower()
            k_service = os.environ.get("K_SERVICE")
            is_staging = environment == "staging" or (k_service and "staging" in k_service.lower())
            
            self._logger.info(f"Secret Manager environment detection - Environment: {environment}, K_SERVICE: {k_service}, Is Staging: {is_staging}")
            
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
            
            successful_secrets = []
            failed_secrets = []
            
            for secret_name in secret_names:
                try:
                    # In staging, append -staging suffix to secret names
                    actual_secret_name = f"{secret_name}-staging" if is_staging else secret_name
                    
                    secret_value = self._fetch_secret(client, actual_secret_name)
                    if secret_value:
                        # Store with original name as key for config mapping
                        secrets[secret_name] = secret_value
                        successful_secrets.append(secret_name)
                        self._logger.debug(f"✓ Successfully loaded: {actual_secret_name}")
                    else:
                        failed_secrets.append(secret_name)
                except Exception as e:
                    failed_secrets.append(secret_name)
                    self._logger.debug(f"✗ Failed to fetch {secret_name}: {str(e)[:100]}")
            
            # Detailed summary
            self._logger.info(f"Google Secret Manager loading complete:")
            self._logger.info(f"  - Successfully loaded: {len(successful_secrets)} secrets")
            if successful_secrets:
                self._logger.info(f"  - Loaded secrets: {', '.join(successful_secrets[:5])}{'...' if len(successful_secrets) > 5 else ''}")
            if failed_secrets:
                critical_failed = [s for s in failed_secrets if s in ['gemini-api-key', 'jwt-secret-key', 'fernet-key']]
                if critical_failed:
                    self._logger.warning(f"  - CRITICAL secrets not found: {', '.join(critical_failed)}")
                self._logger.debug(f"  - Optional secrets not found: {', '.join([s for s in failed_secrets if s not in critical_failed])}")
            
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
            return secret_value
        except Exception as e:
            # More detailed error for debugging without exposing sensitive info
            error_msg = str(e)
            if "404" in error_msg or "NOT_FOUND" in error_msg:
                self._logger.debug(f"Secret {secret_name} not found in project {self._project_id}")
            elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
                self._logger.warning(f"Permission denied accessing secret {secret_name} in project {self._project_id}")
            else:
                self._logger.debug(f"Error fetching {secret_name}: {error_msg[:100]}")
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
        
        if secrets:
            self._logger.info(f"Loaded {len(secrets)} secrets from environment variables")
            # Log which critical secrets are present without exposing values
            critical_env_secrets = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
            present_critical = [s for s in critical_env_secrets if s in secrets]
            if present_critical:
                self._logger.debug(f"Critical secrets present in env: {', '.join(present_critical)}")
        else:
            self._logger.info("No secrets loaded from environment variables")
        return secrets