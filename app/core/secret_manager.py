"""Secret management utilities for configuration loading."""

import os
from typing import Dict, Any, Optional, List
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
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        
        # Set project ID based on environment
        if environment == "staging":
            # For staging, use staging numerical ID
            self._project_id = os.environ.get("GCP_PROJECT_ID_NUMERICAL_STAGING", 
                                             os.environ.get("SECRET_MANAGER_PROJECT_ID",
                                             "701982941522"))  # Default to staging numerical ID
        else:
            # For production or other environments
            self._project_id = os.environ.get("GCP_PROJECT_ID_NUMERICAL_STAGING", 
                                             os.environ.get("SECRET_MANAGER_PROJECT_ID",
                                             "304612253870"))  # Default to production numerical ID
        
        # Log which project we're using for Secret Manager
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
            client = self._initialize_secret_client()
            environment, is_staging = self._detect_environment()
            secrets = self._fetch_all_secrets(client, is_staging)
            return secrets
        except Exception as e:
            self._logger.error(f"Error loading secrets from Secret Manager: {e}")
            raise SecretManagerError(f"Secret Manager loading failed: {e}")
    
    def _initialize_secret_client(self) -> secretmanager.SecretManagerServiceClient:
        """Initialize Secret Manager client with logging."""
        self._logger.info(f"Initializing Google Secret Manager client for project: {self._project_id}")
        return self._get_secret_client()
    
    def _detect_environment(self) -> tuple:
        """Detect environment configuration and log details."""
        from .secret_manager_helpers import detect_environment_config
        environment, is_staging = detect_environment_config()
        k_service = os.environ.get("K_SERVICE")
        self._logger.info(f"Secret Manager environment detection - Environment: {environment}, K_SERVICE: {k_service}, Is Staging: {is_staging}")
        return environment, is_staging
    
    def _fetch_all_secrets(self, client: secretmanager.SecretManagerServiceClient, is_staging: bool) -> Dict[str, Any]:
        """Fetch all required secrets with proper tracking."""
        from .secret_manager_helpers import get_secret_names_list, initialize_fetch_tracking
        secret_names = get_secret_names_list()
        successful_secrets, failed_secrets = initialize_fetch_tracking()
        secrets = self._process_secret_names(client, secret_names, is_staging, successful_secrets, failed_secrets)
        self._log_fetch_summary(successful_secrets, failed_secrets)
        return secrets
    
    def _process_secret_names(self, client: secretmanager.SecretManagerServiceClient, 
                             secret_names: List[str], is_staging: bool,
                             successful_secrets: List[str], failed_secrets: List[str]) -> Dict[str, Any]:
        """Process all secret names and build secrets dictionary."""
        secrets = {}
        for secret_name in secret_names:
            secret_value = self._fetch_individual_secret(client, secret_name, is_staging)
            self._track_secret_fetch_result(secret_name, secret_value, secrets, successful_secrets, failed_secrets)
        return secrets
    
    def _fetch_individual_secret(self, client: secretmanager.SecretManagerServiceClient, 
                                secret_name: str, is_staging: bool) -> Optional[str]:
        """Fetch individual secret with error handling."""
        from .secret_manager_helpers import determine_actual_secret_name
        try:
            actual_secret_name = determine_actual_secret_name(secret_name, is_staging)
            return self._fetch_secret(client, actual_secret_name)
        except Exception as e:
            self._logger.debug(f"✗ Failed to fetch {secret_name}: {str(e)[:100]}")
            return None
    
    def _track_secret_fetch_result(self, secret_name: str, secret_value: Optional[str],
                                  secrets: Dict[str, Any], successful_secrets: List[str], failed_secrets: List[str]) -> None:
        """Track the result of secret fetching operation."""
        from .secret_manager_helpers import track_secret_result
        if secret_value:
            secrets[secret_name] = secret_value
            self._logger.debug(f"✓ Successfully loaded: {secret_name}")
        track_secret_result(secret_name, secret_value, successful_secrets, failed_secrets)
    
    def _log_fetch_summary(self, successful_secrets: List[str], failed_secrets: List[str]) -> None:
        """Log comprehensive summary of secret fetching results."""
        from .secret_manager_helpers import prepare_secrets_dict
        prepare_secrets_dict(successful_secrets, failed_secrets)
    
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
        
        # Check if we're in staging environment
        environment = os.environ.get("ENVIRONMENT", "development").lower()
        k_service = os.environ.get("K_SERVICE")
        is_staging = environment == "staging" or (k_service and "staging" in k_service.lower())
        
        secrets = {}
        for secret_name, env_var in env_mapping.items():
            # Try staging-suffixed env var first if in staging
            if is_staging:
                staging_env_var = f"{env_var}_STAGING"
                value = os.environ.get(staging_env_var)
                if value:
                    secrets[secret_name] = value
                    continue
            # Fall back to regular env var
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