"""Secure Secret Management

**CRITICAL: Enterprise-Grade Secret Management**

Handles secure loading, rotation, and management of secrets.
Supports GCP Secret Manager integration and local development.

**UPDATED**: This module now uses IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml for consistent environment access.

Business Value: Prevents security breaches that could affect Enterprise customers.
Ensures compliance with security requirements for revenue-critical operations.

Each function ≤8 lines, file ≤300 lines.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from netra_backend.app.core.isolated_environment import get_env
from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.Config import AppConfig


class SecretManager:
    """Enterprise-grade secret management system.
    
    **CRITICAL**: All secret access MUST use this manager.
    Supports hot rotation and secure storage for Enterprise customers.
    """
    
    def __init__(self):
        """Initialize secure secret manager."""
        self._logger = logger
        self._env = get_env()  # Use IsolatedEnvironment for all env access
        self._environment = self._get_environment()
        self._secret_mappings = self._load_secret_mappings()
        self._secret_cache = {}
        self._cache_timestamp = None
        self._initialized = False
        self._populating_secrets = False  # Guard against recursive calls
    
    def _get_environment(self) -> str:
        """Get current environment for secret management.
        
        Uses IsolatedEnvironment for secure environment detection.
        """
        # Use IsolatedEnvironment for secure environment detection
        return self._env.get("ENVIRONMENT", "development").lower()
    
    def _load_secret_mappings(self) -> Dict[str, dict]:
        """Load secret to configuration field mappings."""
        mappings = {}
        mappings.update(self._get_llm_secret_mappings())
        mappings.update(self._get_oauth_secret_mappings())
        mappings.update(self._get_auth_secret_mappings())
        mappings.update(self._get_database_secret_mappings())
        return mappings
    
    def _get_llm_secret_mappings(self) -> Dict[str, dict]:
        """Get LLM-related secret mappings."""
        return {
            "GEMINI_API_KEY": self._get_gemini_api_key_mapping(),
            "ANTHROPIC_API_KEY": self._get_anthropic_api_key_mapping(),
            "GOOGLE_API_KEY": self._get_openai_api_key_mapping()
        }
    
    def _get_gemini_api_key_mapping(self) -> Dict[str, Any]:
        """Get Gemini API key mapping configuration."""
        return {
            "target_models": ["llm_configs.default", "llm_configs.triage", 
                            "llm_configs.data", "llm_configs.optimizations_core"],
            "target_field": "gemini_api_key", "required": False, "rotation_enabled": True
        }
    
    def _get_anthropic_api_key_mapping(self) -> Dict[str, Any]:
        """Get Anthropic API key mapping configuration."""
        return {
            "target_field": "anthropic_api_key",
            "required": False,
            "rotation_enabled": True
        }
    
    def _get_openai_api_key_mapping(self) -> Dict[str, Any]:
        """Get OpenAI API key mapping configuration."""
        return {
            "target_field": "openai_api_key",
            "required": False,
            "rotation_enabled": True
        }
    
    def _get_oauth_secret_mappings(self) -> Dict[str, dict]:
        """Get OAuth-related secret mappings."""
        google_client_id = self._get_google_client_id_mapping()
        google_client_secret = self._get_google_client_secret_mapping()
        return {"GOOGLE_CLIENT_ID": google_client_id, "GOOGLE_CLIENT_SECRET": google_client_secret}
    
    def _get_google_client_id_mapping(self) -> Dict[str, Any]:
        """Get Google Client ID mapping."""
        return {
            "target_models": ["google_cloud", "oauth_config"],
            "target_field": "client_id", 
            "required": True,
            "rotation_enabled": False
        }
    
    def _get_google_client_secret_mapping(self) -> Dict[str, Any]:
        """Get Google Client Secret mapping."""
        return {
            "target_models": ["google_cloud", "oauth_config"],
            "target_field": "client_secret",
            "required": True,
            "rotation_enabled": True
        }
    
    def _get_auth_secret_mappings(self) -> Dict[str, dict]:
        """Get authentication secret mappings."""
        jwt_mapping = self._get_jwt_secret_mapping()
        fernet_mapping = self._get_fernet_secret_mapping()
        service_mapping = self._get_service_secret_mapping()
        return {
            "JWT_SECRET_KEY": jwt_mapping, 
            "FERNET_KEY": fernet_mapping,
            "SERVICE_SECRET": service_mapping
        }
    
    def _get_jwt_secret_mapping(self) -> Dict[str, Any]:
        """Get JWT secret mapping."""
        return {
            "target_field": "jwt_secret_key",
            "required": True,
            "rotation_enabled": True
        }
    
    def _get_fernet_secret_mapping(self) -> Dict[str, Any]:
        """Get Fernet secret mapping."""
        return {
            "target_field": "fernet_key",
            "required": True,
            "rotation_enabled": True
        }
    
    def _get_service_secret_mapping(self) -> Dict[str, Any]:
        """Get service secret mapping for cross-service authentication."""
        return {
            "target_field": "service_secret",
            "required": True,
            "rotation_enabled": True
        }
    
    def _get_database_secret_mappings(self) -> Dict[str, dict]:
        """Get database-related secret mappings."""
        clickhouse_mapping = self._get_clickhouse_password_mapping()
        redis_mapping = self._get_redis_password_mapping()
        return {"CLICKHOUSE_PASSWORD": clickhouse_mapping, "REDIS_PASSWORD": redis_mapping}
    
    def _get_clickhouse_password_mapping(self) -> Dict[str, Any]:
        """Get ClickHouse password mapping."""
        # ClickHouse password is only required in production environments
        # For development, ClickHouse containers may not require authentication
        is_required = self._environment in ["production", "staging"]
        return {
            "target_models": ["clickhouse_native", "clickhouse_https"],
            "target_field": "password",
            "required": is_required,
            "rotation_enabled": True
        }
    
    def _get_redis_password_mapping(self) -> Dict[str, Any]:
        """Get Redis password mapping."""
        return {
            "target_models": ["redis"],
            "target_field": "password",
            "required": False,
            "rotation_enabled": True
        }
    
    def populate_secrets(self, config: AppConfig) -> None:
        """Populate all secrets in configuration object."""
        # Prevent recursive calls that cause infinite logging loops
        if self._populating_secrets:
            return
        
        self._populating_secrets = True
        try:
            self._load_secrets_from_sources()
            self._apply_secrets_to_config(config)
            self._validate_required_secrets()
            
            # Only log once when first populated
            if not self._initialized:
                self._logger.info(f"Populated secrets for {self._environment}")
                self._initialized = True
        finally:
            self._populating_secrets = False
    
    def _load_secrets_from_sources(self) -> None:
        """Load secrets from all available sources."""
        if self._is_cache_valid():
            return
        self._secret_cache = {}
        self._load_dotenv_if_development()
        self._load_from_environment_variables()
        self._load_from_gcp_secret_manager()
        self._load_from_local_files()
        self._cache_timestamp = datetime.now()
    
    def _load_dotenv_if_development(self) -> None:
        """Load .env files in development mode.
        
        CONFIG MANAGER: Direct env loading for development secrets.
        """
        if self._environment not in ["development", "testing"]:
            return
            
        try:
            from pathlib import Path
            from dotenv import load_dotenv
            
            # Find project root
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent
            
            # Load .env file if it exists
            env_path = project_root / ".env"
            if env_path.exists():
                load_dotenv(env_path, override=False)
                self._logger.debug(f"Loaded .env file from {env_path}")
            
            # Load .env.dev if it exists (higher priority)
            env_dev_path = project_root / ".env.dev"
            if env_dev_path.exists():
                load_dotenv(env_dev_path, override=True)
                self._logger.debug(f"Loaded .env.dev file from {env_dev_path}")
            
            # Load .env.test if in testing environment (higher priority than .env.dev)
            if self._environment == "testing":
                env_test_path = project_root / "netra_backend" / ".env.test"
                if env_test_path.exists():
                    load_dotenv(env_test_path, override=True)
                    self._logger.debug(f"Loaded .env.test file from {env_test_path}")
            
            # Load .env.local if it exists (highest priority)
            env_local_path = project_root / ".env.local"
            if env_local_path.exists():
                load_dotenv(env_local_path, override=True)
                self._logger.debug(f"Loaded .env.local file from {env_local_path}")
        except ImportError:
            # dotenv not available, skip
            pass
        except Exception as e:
            self._logger.debug(f"Could not load .env files: {e}")
    
    def _load_from_environment_variables(self) -> None:
        """Load secrets from environment variables.
        
        Uses IsolatedEnvironment for secure secret loading.
        """
        # Use IsolatedEnvironment for secure secret loading
        env_mapping = self._get_environment_variable_mapping()
        for secret_name, env_var in env_mapping.items():
            value = self._env.get(env_var)
            if value:
                self._secret_cache[secret_name] = value
                self._logger.debug(f"Loaded {secret_name} from environment")
    
    def _load_from_gcp_secret_manager(self) -> None:
        """Load secrets from GCP Secret Manager."""
        if not self._is_gcp_available():
            return
        try:
            gcp_secrets = self._fetch_gcp_secrets()
            self._secret_cache.update(gcp_secrets)
            self._logger.info(f"Loaded {len(gcp_secrets)} secrets from GCP")
        except Exception as e:
            self._handle_gcp_secret_error(e)
    
    def _load_from_local_files(self) -> None:
        """Load secrets from local development files."""
        if self._environment != "development":
            return
        local_secrets = self._read_local_secret_files()
        for secret_name, value in local_secrets.items():
            if secret_name not in self._secret_cache:
                self._secret_cache[secret_name] = value
    
    def _apply_secrets_to_config(self, config: AppConfig) -> None:
        """Apply loaded secrets to configuration object."""
        for secret_name, secret_mapping in self._secret_mappings.items():
            secret_value = self._secret_cache.get(secret_name)
            if secret_value:
                self._apply_single_secret(config, secret_name, secret_value, secret_mapping)
    
    def _apply_single_secret(self, config: AppConfig, name: str, value: str, mapping: dict) -> None:
        """Apply single secret to configuration."""
        target_models = mapping.get("target_models", [])
        target_field = mapping["target_field"]
        if target_models:
            self._apply_to_target_models(config, target_models, target_field, value)
        else:
            self._apply_to_root_config(config, target_field, value)
    
    def _apply_to_target_models(self, config: AppConfig, models: List[str], field: str, value: str) -> None:
        """Apply secret to target model objects."""
        for model_path in models:
            target_obj = self._navigate_to_target_object(config, model_path)
            if target_obj and hasattr(target_obj, field):
                setattr(target_obj, field, value)
    
    def _apply_to_root_config(self, config: AppConfig, field: str, value: str) -> None:
        """Apply secret to root configuration object."""
        if hasattr(config, field):
            setattr(config, field, value)
    
    def _navigate_to_target_object(self, config: AppConfig, path: str) -> Optional[object]:
        """Navigate to target object using dot notation path."""
        parts = path.split('.')
        obj = config
        for part in parts:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                return None
        return obj
    
    def _validate_required_secrets(self) -> None:
        """Validate that all required secrets are loaded."""
        missing_secrets = self._get_missing_required_secrets()
        if missing_secrets:
            error_msg = f"Required secrets missing: {missing_secrets}"
            
            # Only log error once, not repeatedly
            if not self._initialized:
                self._logger.error(error_msg)
                
            if self._environment == "production":
                raise ConfigurationError(error_msg)
    
    def _get_missing_required_secrets(self) -> List[str]:
        """Get list of missing required secrets."""
        missing = []
        for secret_name, mapping in self._secret_mappings.items():
            if mapping.get("required", False) and secret_name not in self._secret_cache:
                missing.append(secret_name)
        return missing
    
    def _get_environment_variable_mapping(self) -> Dict[str, str]:
        """Get mapping of secret names to environment variables.
        
        NOTE: For local development, secret names match environment variable names.
        This ensures direct mapping without transformation.
        """
        return {
            "GEMINI_API_KEY": "GEMINI_API_KEY",
            "GOOGLE_CLIENT_ID": "GOOGLE_CLIENT_ID", 
            "GOOGLE_CLIENT_SECRET": "GOOGLE_CLIENT_SECRET",
            "JWT_SECRET_KEY": "JWT_SECRET_KEY",
            "FERNET_KEY": "FERNET_KEY",
            "SERVICE_SECRET": "SERVICE_SECRET",
            "CLICKHOUSE_PASSWORD": "CLICKHOUSE_PASSWORD",
            "REDIS_PASSWORD": "REDIS_PASSWORD",
            "ANTHROPIC_API_KEY": "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY": "GOOGLE_API_KEY"
        }
    
    def _is_gcp_available(self) -> bool:
        """Check if GCP Secret Manager is available.
        
        Uses IsolatedEnvironment for GCP availability check.
        """
        # Use IsolatedEnvironment for GCP availability detection
        return (self._environment in ["staging", "production"] and 
                self._env.get("GCP_PROJECT_ID") is not None)
    
    def _fetch_gcp_secrets(self) -> Dict[str, str]:
        """Fetch secrets from GCP Secret Manager."""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = self._get_gcp_project_id()
            return self._retrieve_gcp_secrets(client, project_id)
        except ImportError:
            self._logger.warning("GCP Secret Manager client not available")
            return {}
    
    def _get_gcp_project_id(self) -> str:
        """Get GCP project ID for secret access.
        
        Uses IsolatedEnvironment for GCP project ID.
        """
        # Use IsolatedEnvironment for GCP project ID
        staging_project = "701982941522"
        production_project = "304612253870"
        return self._env.get("GCP_PROJECT_ID", 
                             staging_project if self._environment == "staging" else production_project)
    
    def _retrieve_gcp_secrets(self, client, project_id: str) -> Dict[str, str]:
        """Retrieve secrets from GCP Secret Manager."""
        secrets = {}
        for secret_name in self._secret_mappings.keys():
            try:
                secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
                response = client.access_secret_version(request={"name": secret_path})
                secrets[secret_name] = response.payload.data.decode("UTF-8")
            except Exception as e:
                self._logger.warning(f"Failed to load GCP secret {secret_name}: {e}")
        return secrets
    
    def _handle_gcp_secret_error(self, error: Exception) -> None:
        """Handle GCP secret loading errors."""
        self._logger.error(f"GCP Secret Manager error: {error}")
        if self._environment == "production":
            raise ConfigurationError(f"Critical secret loading failure: {error}")
    
    def _read_local_secret_files(self) -> Dict[str, str]:
        """Read secrets from local development files."""
        secrets = {}
        # .secrets file is only for ACT/GitHub Actions testing, not for dev mode
        # Real development should use .env.local or environment variables
        secret_files = [".env.local", "secrets.json"]
        from pathlib import Path
        for file_path in secret_files:
            if Path(file_path).exists():
                secrets.update(self._parse_secret_file(file_path))
        return secrets
    
    def _parse_secret_file(self, file_path: str) -> Dict[str, str]:
        """Parse individual secret file."""
        secrets = {}
        try:
            from pathlib import Path
            if Path(file_path).suffix == '.json':
                secrets = self._parse_json_secret_file(file_path)
            else:
                secrets = self._parse_env_secret_file(file_path)
        except Exception as e:
            self._logger.warning(f"Failed to parse secret file {file_path}: {e}")
        return secrets
    
    def _parse_json_secret_file(self, file_path: str) -> Dict[str, str]:
        """Parse JSON secret file."""
        with open(file_path, 'r') as f:
            return json.load(f)
    
    def _parse_env_secret_file(self, file_path: str) -> Dict[str, str]:
        """Parse environment-style secret file."""
        secrets = {}
        with open(file_path, 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    secrets[key.strip()] = value.strip().strip('"\'')
        return secrets
    
    def _is_cache_valid(self) -> bool:
        """Check if secret cache is still valid."""
        if not self._cache_timestamp:
            return False
        cache_ttl = timedelta(minutes=5)  # 5-minute cache
        return datetime.now() - self._cache_timestamp < cache_ttl
    
    def rotate_secret(self, secret_name: str) -> bool:
        """Rotate a specific secret (hot rotation capability)."""
        mapping = self._secret_mappings.get(secret_name)
        if not mapping or not mapping.get("rotation_enabled", False):
            return False
        self._invalidate_secret_cache()
        self._logger.info(f"Rotated secret: {secret_name}")
        return True
    
    def _invalidate_secret_cache(self) -> None:
        """Invalidate secret cache to force reload."""
        self._secret_cache = {}
        self._cache_timestamp = None
    
    def validate_secrets_consistency(self, config: AppConfig) -> List[str]:
        """Validate secrets configuration consistency."""
        issues = []
        issues.extend(self._validate_secret_presence())
        issues.extend(self._validate_secret_formats())
        issues.extend(self._validate_rotation_capability())
        return issues
    
    def _validate_secret_presence(self) -> List[str]:
        """Validate presence of required secrets."""
        issues = []
        for secret_name, mapping in self._secret_mappings.items():
            if mapping.get("required", False) and secret_name not in self._secret_cache:
                issues.append(f"Required secret missing: {secret_name}")
        return issues
    
    def _validate_secret_formats(self) -> List[str]:
        """Validate secret format requirements."""
        issues = []
        for secret_name, value in self._secret_cache.items():
            format_issues = self._check_secret_format(secret_name, value)
            issues.extend(format_issues)
        return issues
    
    def _validate_rotation_capability(self) -> List[str]:
        """Validate secret rotation capability."""
        issues = []
        if self._environment == "production":
            for secret_name, mapping in self._secret_mappings.items():
                if mapping.get("required") and not mapping.get("rotation_enabled"):
                    issues.append(f"Critical secret lacks rotation capability: {secret_name}")
        return issues
    
    def _check_secret_format(self, secret_name: str, value: str) -> List[str]:
        """Check secret format requirements."""
        issues = []
        if secret_name == "JWT_SECRET_KEY" and len(value) < 32:
            issues.append("JWT secret key too short (minimum 32 characters)")
        elif secret_name == "FERNET_KEY" and len(value) != 44:
            issues.append("Fernet key invalid format (must be 44 characters)")
        return issues
    
    def get_loaded_secrets_count(self) -> int:
        """Get count of loaded secrets for monitoring."""
        return len(self._secret_cache)
    
    def get_secret_summary(self) -> Dict[str, Any]:
        """Get secret management summary for monitoring."""
        return {
            "environment": self._environment,
            "secrets_loaded": len(self._secret_cache),
            "required_secrets": len([s for s, m in self._secret_mappings.items() if m.get("required")]),
            "rotation_enabled_count": len([s for s, m in self._secret_mappings.items() if m.get("rotation_enabled")]),
            "gcp_available": self._is_gcp_available(),
            "cache_valid": self._is_cache_valid()
        }
    
    def load_all_secrets(self) -> Dict[str, Any]:
        """Load all secrets from configured sources.
        
        Public method for UnifiedSecretManager compatibility.
        Returns a copy of the loaded secrets.
        """
        self._load_secrets_from_sources()
        return dict(self._secret_cache)