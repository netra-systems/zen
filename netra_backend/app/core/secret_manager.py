"""Secret management utilities for configuration loading."""

import os
from typing import Any, Dict, List, Optional

from google.cloud import secretmanager
from tenacity import retry, stop_after_attempt, wait_fixed

from netra_backend.app.core.configuration.base import config_manager
from netra_backend.app.logging_config import central_logger as logger


class SecretManagerError(Exception):
    """Raised when secret management operations fail."""
    pass


class SecretManager:
    """Manages loading secrets from Google Cloud Secret Manager with fallback to environment variables."""
    
    def __init__(self):
        self._logger = logger
        self._client: Optional[secretmanager.SecretManagerServiceClient] = None
        self._config = config_manager.get_config()
        self._project_id = self._initialize_project_id()
        self._log_initialization_status()
    
    def _initialize_project_id(self) -> str:
        """Initialize project ID based on environment."""
        # Use IsolatedEnvironment for consistent environment detection
        from shared.isolated_environment import get_env
        environment = get_env().get('ENVIRONMENT', getattr(self._config, 'environment', 'development')).lower()
        if environment == "staging":
            return self._get_staging_project_id()
        return self._get_production_project_id()
    
    def _get_staging_project_id(self) -> str:
        """Get staging project ID with fallbacks."""
        # Use IsolatedEnvironment for consistent environment access
        from shared.isolated_environment import get_env
        return get_env().get('GCP_PROJECT_ID_NUMERICAL_STAGING', 
                         getattr(self._config, 'gcp_project_id_numerical_staging', 
                                getattr(self._config, 'secret_manager_project_id', "701982941522")))
    
    def _get_production_project_id(self) -> str:
        """Get production project ID with fallbacks."""
        # Use IsolatedEnvironment for consistent environment access
        from shared.isolated_environment import get_env
        return get_env().get('GCP_PROJECT_ID_NUMERICAL_PRODUCTION', 
                         getattr(self._config, 'gcp_project_id_numerical_production', 
                                getattr(self._config, 'secret_manager_project_id', "304612253870")))
    
    def _log_initialization_status(self) -> None:
        """Log Secret Manager initialization status."""
        environment = getattr(self._config, 'environment', 'development').lower()
        k_service = getattr(self._config, 'k_service', None)
        if environment in ["staging", "production"] or k_service:
            self._logger.info(f"Secret Manager initialized with project ID: {self._project_id} for environment: {environment}")
        
    def load_secrets(self) -> Dict[str, Any]:
        """Load secrets from Secret Manager with environment variables as base, Google Secrets supersede."""
        environment = getattr(self._config, 'environment', 'development').lower()
        should_load_secrets = self._should_load_from_secret_manager(environment)
        secrets = self._load_base_environment_secrets(environment)
        return self._merge_google_secrets_if_needed(secrets, should_load_secrets, environment)
    
    def _should_load_from_secret_manager(self, environment: str) -> bool:
        """Determine if we should load from Secret Manager."""
        load_secrets = getattr(self._config, 'load_secrets', False)
        k_service = getattr(self._config, 'k_service', None)
        return (load_secrets or
                environment == "staging" or environment == "production" or
                bool(k_service))
    
    def _load_base_environment_secrets(self, environment: str) -> Dict[str, Any]:
        """Load base secrets from environment variables."""
        self._logger.info(f"Starting secret loading process for environment: {environment}")
        return self._load_from_environment()
    
    def _merge_google_secrets_if_needed(self, secrets: Dict[str, Any], should_load_secrets: bool, environment: str) -> Dict[str, Any]:
        """Merge Google secrets if needed, handling development mode."""
        env_secret_count = len(secrets)
        if not should_load_secrets and environment in ["development", "testing"]:
            return self._handle_development_mode_secrets(secrets, env_secret_count)
        return self._load_and_merge_google_secrets(secrets, environment, env_secret_count)
    
    def _handle_development_mode_secrets(self, secrets: Dict[str, Any], env_secret_count: int) -> Dict[str, Any]:
        """Handle secrets loading in development mode."""
        self._logger.info(f"Using only environment variables for secrets (local development mode): {env_secret_count} secrets loaded")
        return secrets
    
    def _load_and_merge_google_secrets(self, secrets: Dict[str, Any], environment: str, env_secret_count: int) -> Dict[str, Any]:
        """Load and merge Google secrets with environment secrets."""
        self._logger.info(f"Attempting to load Google Secrets for environment: {environment}")
        return self._attempt_google_secret_loading(secrets, env_secret_count)
    
    def _attempt_google_secret_loading(self, secrets: Dict[str, Any], env_secret_count: int) -> Dict[str, Any]:
        """Attempt to load Google secrets with error handling."""
        try:
            google_secrets = self._load_from_secret_manager()
            return self._merge_google_secrets_with_logging(secrets, google_secrets, env_secret_count)
        except Exception as e:
            self._logger.error(f"Failed to load from Google Secret Manager, using environment variables only: {e}")
            return secrets
    
    def _merge_google_secrets_with_logging(self, secrets: Dict[str, Any], google_secrets: Dict[str, Any], env_secret_count: int) -> Dict[str, Any]:
        """Merge Google secrets with comprehensive logging, overriding placeholders."""
        # Define placeholder values that should always be overridden by Google Secrets
        PLACEHOLDER_VALUES = [
            "",  # Empty strings
            "will-be-set-by-secrets",  # Staging placeholder pattern
            "placeholder",  # Generic placeholder
            "staging-jwt-secret-key-should-be-replaced-in-deployment",  # JWT staging placeholder
            "staging-fernet-key-should-be-replaced-in-deployment",  # Fernet staging placeholder
            "REPLACE",  # Replace placeholder
            "should-be-replaced",  # Generic replacement pattern
            "placeholder-value",  # Placeholder value pattern
            "default-value",  # Default value pattern
            "change-me",  # Change me pattern
            "update-in-production",  # Production update pattern
            None  # None values
        ]
        
        if google_secrets:
            # Import shared secret mappings for proper mapping
            from shared.secret_mappings import get_secret_mappings
            environment = getattr(self._config, 'environment', 'development').lower()
            secret_mappings = get_secret_mappings(environment)
            
            # Track changes for logging
            placeholder_overrides = []
            new_additions = []
            supersessions = []
            
            for google_secret_name, google_value in google_secrets.items():
                # Map Google secret name to environment variable name
                # First check if it's already in the mappings, if not use the key as-is
                env_var_name = secret_mappings.get(google_secret_name, google_secret_name)
                
                # Also check if the google_secret_name itself is already an env var name
                # (for backward compatibility with existing tests and direct mappings)
                if google_secret_name in secrets:
                    target_key = google_secret_name
                elif env_var_name in secrets:
                    target_key = env_var_name
                else:
                    # Use the mapped name for new additions
                    target_key = env_var_name
                
                # Check if we're overriding a placeholder
                if target_key in secrets:
                    existing_value = secrets[target_key]
                    if existing_value in PLACEHOLDER_VALUES:
                        placeholder_overrides.append(target_key)
                        self._logger.info(f"Overriding placeholder for {target_key} with Google Secret value")
                    elif existing_value != google_value:
                        supersessions.append(target_key)
                        self._logger.info(f"Google Secret superseding environment value for {target_key}")
                    # Always use Google value regardless
                    secrets[target_key] = google_value
                else:
                    # New secret from Google
                    new_additions.append(target_key)
                    self._logger.info(f"Adding {target_key} from Google Secret")
                    secrets[target_key] = google_value
            
            # Enhanced logging
            self._log_enhanced_google_merge(google_secrets, secrets, env_secret_count, 
                                          placeholder_overrides, new_additions, supersessions)
            
            # Validate critical secrets after merge
            self._validate_critical_secrets(secrets)
            return secrets
        
        self._logger.warning("No secrets loaded from Google Secret Manager")
        # Still validate critical secrets even without Google secrets
        self._validate_critical_secrets(secrets)
        return secrets
    
    def _validate_critical_secrets(self, secrets: Dict[str, Any]) -> None:
        """Validate that critical secrets don't contain placeholder values."""
        # Get current environment
        environment = getattr(self._config, 'environment', 'development').lower()
        
        # Only validate strictly in staging/production
        if environment in ['development', 'testing']:
            self._logger.debug("Skipping critical secret validation in development/testing environment")
            return
        
        # Define critical secrets that must not have placeholder values
        CRITICAL_SECRETS = [
            'POSTGRES_PASSWORD',
            'REDIS_PASSWORD', 
            'JWT_SECRET_KEY',
            'CLICKHOUSE_PASSWORD',
            'FERNET_KEY'
        ]
        
        # Define expanded placeholder patterns (including partial matches)
        PLACEHOLDER_PATTERNS = [
            "",  # Empty strings
            "will-be-set-by-secrets",
            "placeholder",
            "REPLACE",
            "should-be-replaced",
            "placeholder-value",
            "default-value",
            "change-me",
            "update-in-production",
            "staging-jwt-secret-key-should-be-replaced-in-deployment",
            "staging-fernet-key-should-be-replaced-in-deployment",
        ]
        
        validation_errors = []
        warnings = []
        
        for secret_name in CRITICAL_SECRETS:
            if secret_name not in secrets:
                warnings.append(f"Critical secret {secret_name} is missing from configuration")
                continue
                
            secret_value = secrets[secret_name]
            
            # Check for None values
            if secret_value is None:
                validation_errors.append(f"Critical secret {secret_name} is None")
                continue
                
            # Convert to string for pattern matching
            secret_str = str(secret_value).strip()
            
            # Check for exact placeholder matches
            if secret_str in PLACEHOLDER_PATTERNS:
                validation_errors.append(f"Critical secret {secret_name} contains placeholder value: '{secret_str}'")
                continue
                
            # Check for partial placeholder patterns
            secret_lower = secret_str.lower()
            for pattern in ["replace", "placeholder", "should-be-replaced", "change-me", "update"]:
                if pattern in secret_lower and len(secret_str) < 50:  # Short values likely to be placeholders
                    warnings.append(f"Critical secret {secret_name} may contain placeholder pattern: '{pattern}' in '{secret_str[:20]}...'")
                    break
        
        # Log warnings
        for warning in warnings:
            self._logger.warning(f"Secret validation warning: {warning}")
        
        # Handle validation errors based on environment
        if validation_errors:
            error_msg = f"Critical secret validation failed in {environment} environment: {'; '.join(validation_errors)}"
            self._logger.error(error_msg)
            
            if environment in ['staging', 'production']:
                # Raise exception in staging/production
                raise SecretManagerError(f"Invalid placeholder values detected in critical secrets for {environment} environment. "
                                       f"Google Secret Manager must override these placeholders. Errors: {'; '.join(validation_errors)}")
            else:
                # Just log warnings for other environments
                self._logger.warning(f"Would fail in staging/production: {error_msg}")
        else:
            self._logger.info(f"Critical secret validation passed for {environment} environment")
    
    def _log_successful_google_merge(self, google_secrets: Dict[str, Any], secrets: Dict[str, Any], env_secret_count: int) -> None:
        """Log successful Google secrets merge with statistics."""
        self._logger.info(f"Google Secrets loaded successfully: {len(google_secrets)} secrets from Google Secret Manager")
        self._logger.info(f"Total secrets after merge: {len(secrets)} (Base env: {env_secret_count}, Google overrides: {len(google_secrets)})")
        superseded = [key for key in google_secrets if key in secrets]
        if superseded:
            self._logger.debug(f"Google Secrets superseded environment variables for: {', '.join(superseded)}")
    
    def _log_enhanced_google_merge(self, google_secrets: Dict[str, Any], secrets: Dict[str, Any], env_secret_count: int,
                                  placeholder_overrides: List[str], new_additions: List[str], supersessions: List[str]) -> None:
        """Log enhanced Google secrets merge with detailed statistics."""
        self._logger.info(f"Google Secrets loaded successfully: {len(google_secrets)} secrets from Google Secret Manager")
        self._logger.info(f"Total secrets after merge: {len(secrets)} (Base env: {env_secret_count}, Google: {len(google_secrets)})")
        
        if placeholder_overrides:
            self._logger.info(f"Placeholder overrides ({len(placeholder_overrides)}): {', '.join(placeholder_overrides[:5])}{'...' if len(placeholder_overrides) > 5 else ''}")
        
        if new_additions:
            self._logger.info(f"New additions from Google ({len(new_additions)}): {', '.join(new_additions[:3])}{'...' if len(new_additions) > 3 else ''}")
        
        if supersessions:
            self._logger.debug(f"Value supersessions ({len(supersessions)}): {', '.join(supersessions[:3])}{'...' if len(supersessions) > 3 else ''}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _get_secret_client(self) -> secretmanager.SecretManagerServiceClient:
        """Get or create a Secret Manager client with retry logic."""
        if self._client is None:
            self._client = self._create_new_secret_client()
        return self._client
    
    def _create_new_secret_client(self) -> secretmanager.SecretManagerServiceClient:
        """Create new Secret Manager client with error handling."""
        try:
            return secretmanager.SecretManagerServiceClient()
        except Exception as e:
            raise SecretManagerError(f"Failed to create Secret Manager client: {e}")
    
    def _load_from_secret_manager(self) -> Dict[str, Any]:
        """Load secrets from Google Cloud Secret Manager."""
        try:
            return self._execute_secret_manager_loading()
        except Exception as e:
            self._logger.error(f"Error loading secrets from Secret Manager: {e}")
            raise SecretManagerError(f"Secret Manager loading failed: {e}")
    
    def _execute_secret_manager_loading(self) -> Dict[str, Any]:
        """Execute the main secret manager loading logic."""
        client = self._initialize_secret_client()
        environment, is_staging = self._detect_environment()
        return self._fetch_all_secrets(client, is_staging)
    
    def _initialize_secret_client(self) -> secretmanager.SecretManagerServiceClient:
        """Initialize Secret Manager client with logging."""
        self._logger.info(f"Initializing Google Secret Manager client for project: {self._project_id}")
        return self._get_secret_client()
    
    def _detect_environment(self) -> tuple:
        """Detect environment configuration and log details."""
        from netra_backend.app.core.secret_manager_helpers import detect_environment_config
        environment, is_staging = detect_environment_config()
        k_service = getattr(self._config, 'k_service', None)
        self._logger.info(f"Secret Manager environment detection - Environment: {environment}, K_SERVICE: {k_service}, Is Staging: {is_staging}")
        return environment, is_staging
    
    def _fetch_all_secrets(self, client: secretmanager.SecretManagerServiceClient, is_staging: bool) -> Dict[str, Any]:
        """Fetch all required secrets with proper tracking."""
        from .secret_manager_helpers import (
            get_secret_names_list,
            initialize_fetch_tracking,
        )
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
            self._process_single_secret_name(client, secret_name, is_staging, secrets, successful_secrets, failed_secrets)
        return secrets
    
    def _process_single_secret_name(self, client: secretmanager.SecretManagerServiceClient, secret_name: str, 
                                   is_staging: bool, secrets: Dict[str, Any], 
                                   successful_secrets: List[str], failed_secrets: List[str]) -> None:
        """Process a single secret name and update tracking."""
        secret_value = self._fetch_individual_secret(client, secret_name, is_staging)
        self._track_secret_fetch_result(secret_name, secret_value, secrets, successful_secrets, failed_secrets)
    
    def _fetch_individual_secret(self, client: secretmanager.SecretManagerServiceClient, 
                                secret_name: str, is_staging: bool) -> Optional[str]:
        """Fetch individual secret with error handling."""
        try:
            return self._attempt_secret_fetch(client, secret_name, is_staging)
        except Exception as e:
            self._logger.debug(f"[FAIL] Failed to fetch {secret_name}: {str(e)[:100]}")
            return None
    
    def _attempt_secret_fetch(self, client: secretmanager.SecretManagerServiceClient, 
                             secret_name: str, is_staging: bool) -> Optional[str]:
        """Attempt to fetch secret with proper naming."""
        from netra_backend.app.core.secret_manager_helpers import determine_actual_secret_name
        actual_secret_name = determine_actual_secret_name(secret_name, is_staging)
        return self._fetch_secret(client, actual_secret_name)
    
    def _track_secret_fetch_result(self, secret_name: str, secret_value: Optional[str],
                                  secrets: Dict[str, Any], successful_secrets: List[str], failed_secrets: List[str]) -> None:
        """Track the result of secret fetching operation."""
        from netra_backend.app.core.secret_manager_helpers import track_secret_result
        if secret_value:
            secrets[secret_name] = secret_value
            self._logger.debug(f"[PASS] Successfully loaded: {secret_name}")
        track_secret_result(secret_name, secret_value, successful_secrets, failed_secrets)
    
    def _log_fetch_summary(self, successful_secrets: List[str], failed_secrets: List[str]) -> None:
        """Log comprehensive summary of secret fetching results."""
        from netra_backend.app.core.secret_manager_helpers import prepare_secrets_dict
        prepare_secrets_dict(successful_secrets, failed_secrets)
    
    def _fetch_secret(self, client: secretmanager.SecretManagerServiceClient, secret_name: str, version: str = "latest") -> Optional[str]:
        """Fetch a single secret from Secret Manager."""
        try:
            return self._execute_secret_fetch(client, secret_name, version)
        except Exception as e:
            self._handle_secret_fetch_error(e, secret_name)
            return None
    
    def _execute_secret_fetch(self, client: secretmanager.SecretManagerServiceClient, secret_name: str, version: str) -> str:
        """Execute the actual secret fetch operation."""
        name = f"projects/{self._project_id}/secrets/{secret_name}/versions/{version}"
        response = client.access_secret_version(name=name)
        return response.payload.data.decode("UTF-8")
    
    def _handle_secret_fetch_error(self, error: Exception, secret_name: str) -> None:
        """Handle secret fetch errors with appropriate logging."""
        error_msg = str(error)
        if "404" in error_msg or "NOT_FOUND" in error_msg:
            self._log_secret_not_found_error(secret_name)
        elif "403" in error_msg or "PERMISSION_DENIED" in error_msg:
            self._log_secret_permission_error(secret_name)
        else: self._logger.debug(f"Error fetching {secret_name}: {error_msg[:100]}")
    
    def _log_secret_not_found_error(self, secret_name: str) -> None:
        """Log secret not found error."""
        self._logger.debug(f"Secret {secret_name} not found in project {self._project_id}")
    
    def _log_secret_permission_error(self, secret_name: str) -> None:
        """Log secret permission denied error."""
        self._logger.warning(f"Permission denied accessing secret {secret_name} in project {self._project_id}")
    
    def _get_environment_mapping(self) -> Dict[str, str]:
        """Get mapping of secret names to environment variable names."""
        return {
            **self._get_core_service_mapping(),
            **self._get_database_mapping(),
            **self._get_security_mapping()
        }
    
    def _get_core_service_mapping(self) -> Dict[str, str]:
        """Get core service environment mappings."""
        return {
            "gemini-api-key": "GEMINI_API_KEY", "google-client-id": "GOOGLE_CLIENT_ID",
            "google-client-secret": "GOOGLE_CLIENT_SECRET", "langfuse-secret-key": "LANGFUSE_SECRET_KEY",
            "langfuse-public-key": "LANGFUSE_PUBLIC_KEY"
        }
    
    def _get_database_mapping(self) -> Dict[str, str]:
        """Get database service environment mappings."""
        return {
            "clickhouse-password": "CLICKHOUSE_PASSWORD",
            "redis-default": "REDIS_PASSWORD"
        }
    
    def _get_security_mapping(self) -> Dict[str, str]:
        """Get security service environment mappings."""
        return {
            "jwt-secret-key": "JWT_SECRET_KEY",
            "fernet-key": "FERNET_KEY"
        }

    def _get_additional_environment_mapping(self) -> Dict[str, str]:
        """Get additional service environment variable mappings."""
        return {
            "anthropic-api-key": "ANTHROPIC_API_KEY", "openai-api-key": "GOOGLE_API_KEY",
            "cohere-api-key": "COHERE_API_KEY", "mistral-api-key": "MISTRAL_API_KEY",
            "slack-webhook-url": "SLACK_WEBHOOK_URL", "sendgrid-api-key": "SENDGRID_API_KEY",
            "sentry-dsn": "SENTRY_DSN"
        }

    def _detect_staging_environment(self) -> bool:
        """Detect if we're running in staging environment."""
        environment = getattr(self._config, 'environment', 'development').lower()
        k_service = getattr(self._config, 'k_service', None)
        return environment == "staging" or (k_service and "staging" in k_service.lower())

    def _get_secret_value_for_environment(self, env_var: str, is_staging: bool) -> Optional[str]:
        """Get secret value for environment, checking staging suffix if needed."""
        if is_staging:
            staging_attr = f"{env_var.lower()}_staging"
            staging_value = getattr(self._config, staging_attr, None)
            if staging_value:
                return staging_value
        return getattr(self._config, env_var.lower(), None)

    def _process_environment_secrets(self, env_mapping: Dict[str, str], is_staging: bool) -> Dict[str, Any]:
        """Process environment secrets using mapping and staging detection."""
        secrets = {}
        for secret_name, env_var in env_mapping.items():
            value = self._get_secret_value_for_environment(env_var, is_staging)
            if value:
                secrets[secret_name] = value
        return secrets

    def _log_environment_secrets_status(self, secrets: Dict[str, Any]) -> None:
        """Log status of loaded environment secrets."""
        if secrets:
            self._log_environment_secrets_summary(secrets)
        else:
            self._logger.info("No secrets loaded from environment variables")
    
    def _log_environment_secrets_summary(self, secrets: Dict[str, Any]) -> None:
        """Log summary of environment secrets with critical status."""
        self._logger.info(f"Loaded {len(secrets)} secrets from environment variables")
        critical_env_secrets = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
        present_critical = [s for s in critical_env_secrets if s in secrets]
        if present_critical:
            self._logger.debug(f"Critical secrets present in env: {', '.join(present_critical)}")

    def _load_from_environment(self) -> Dict[str, Any]:
        """Load secrets from environment variables as fallback."""
        env_mapping = {**self._get_environment_mapping(), **self._get_additional_environment_mapping()}
        is_staging = self._detect_staging_environment()
        secrets = self._process_environment_secrets(env_mapping, is_staging)
        self._log_environment_secrets_status(secrets)
        return secrets
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a specific secret by name.
        
        Loads secrets if not already cached and returns the requested secret.
        Handles SECRET_KEY mapping to JWT_SECRET_KEY for compatibility.
        Raises SecretManagerError for missing critical secrets in staging/production.
        """
        try:
            # Load secrets if not already loaded
            secrets = self.load_secrets()
            
            # Handle SECRET_KEY specially - it maps to JWT_SECRET_KEY
            if secret_name == "SECRET_KEY":
                # Check both JWT_SECRET_KEY and direct environment variable
                jwt_secret = secrets.get("JWT_SECRET_KEY") or secrets.get("jwt-secret-key")
                if jwt_secret:
                    # Validate it's not a placeholder value
                    if self._is_placeholder_value(jwt_secret):
                        raise SecretManagerError(f"SECRET_KEY contains placeholder value: '{jwt_secret}'")
                    return jwt_secret
                # Fallback to IsolatedEnvironment check
                from shared.isolated_environment import get_env
                env_secret = get_env().get("SECRET_KEY") or get_env().get("JWT_SECRET_KEY")
                if env_secret and not self._is_placeholder_value(env_secret):
                    return env_secret
                
                # If we're in staging/production, this is a critical error
                environment = getattr(self._config, 'environment', 'development').lower()
                if environment in ['staging', 'production']:
                    raise SecretManagerError(f"SECRET_KEY is missing or invalid in {environment} environment")
                
                # Return None for development environments
                return None
            
            # For other secrets, check both the secret name and its mapped version
            secret_value = secrets.get(secret_name)
            if secret_value and not self._is_placeholder_value(secret_value):
                return secret_value
                
            # Also check IsolatedEnvironment as fallback
            from shared.isolated_environment import get_env
            env_value = get_env().get(secret_name)
            if env_value and not self._is_placeholder_value(env_value):
                return env_value
            
            # Check if this is a critical secret in staging/production
            environment = getattr(self._config, 'environment', 'development').lower()
            critical_secrets = ['SECRET_KEY', 'JWT_SECRET_KEY', 'FERNET_KEY', 'POSTGRES_PASSWORD']
            if environment in ['staging', 'production'] and secret_name in critical_secrets:
                raise SecretManagerError(f"Critical secret {secret_name} is missing in {environment} environment")
            
            return None
            
        except SecretManagerError:
            # Re-raise SecretManagerError as-is
            raise
        except Exception as e:
            self._logger.error(f"Failed to get secret {secret_name}: {e}")
            raise SecretManagerError(f"Failed to retrieve secret {secret_name}: {e}")
    
    def _is_placeholder_value(self, value: str) -> bool:
        """Check if a value is a placeholder that should be replaced."""
        if not value or value.strip() == "":
            return True
            
        placeholder_patterns = [
            "will-be-set-by-secrets",
            "placeholder",
            "staging-jwt-secret-key-should-be-replaced-in-deployment",
            "staging-fernet-key-should-be-replaced-in-deployment",
            "REPLACE",
            "should-be-replaced",
            "placeholder-value",
            "default-value",
            "change-me",
            "update-in-production",
            "change-in-production"
        ]
        
        value_lower = value.lower().strip()
        for pattern in placeholder_patterns:
            if pattern.lower() in value_lower:
                return True
                
        return False
    
    def _get_secret_names(self) -> List[str]:
        """Get list of secret names from environment mappings.
        
        **TEST METHOD**: Provides interface for test mocking.
        Returns all known secret names from environment mappings.
        """
        all_mappings = {}
        all_mappings.update(self._get_environment_mapping())
        all_mappings.update(self._get_core_service_mapping())
        all_mappings.update(self._get_database_mapping())
        all_mappings.update(self._get_security_mapping())
        all_mappings.update(self._get_additional_environment_mapping())
        
        # Return the keys (secret names)
        return list(all_mappings.keys())