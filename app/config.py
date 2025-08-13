"""Simplified configuration management with validation and reduced circular dependencies."""

import os
from functools import lru_cache
from typing import Optional, Dict, Any
from pydantic import ValidationError
from datetime import datetime

# Import the schemas without circular dependency
from app.schemas.Config import AppConfig, DevelopmentConfig, ProductionConfig, StagingConfig, NetraTestingConfig
from app.schemas.config_types import ConfigurationSummary, ConfigurationStatus, Environment
from app.logging_config import central_logger as logger
from app.core.secret_manager import SecretManager
from app.core.config_validator import ConfigValidator


class ConfigurationError(Exception):
    """Raised when configuration loading or validation fails."""
    pass


class ConfigManager:
    """Simplified configuration manager with clear separation of concerns."""
    
    def __init__(self):
        self._config: Optional[AppConfig] = None
        self._secret_manager = SecretManager()
        self._validator = ConfigValidator()
        self._logger = logger
        
    @lru_cache(maxsize=1)
    def get_config(self) -> AppConfig:
        """Get the application configuration (cached)."""
        if self._config is None:
            self._config = self._load_configuration()
        return self._config
    
    def _load_configuration(self) -> AppConfig:
        """Load and validate configuration from environment."""
        try:
            environment = self._get_environment()
            self._logger.info(f"Loading configuration for: {environment}")
            
            # Create base config
            config = self._create_base_config(environment)
            
            # Load critical environment variables (non-secrets like DATABASE_URL, REDIS_URL, etc)
            self._load_critical_env_vars(config)
            
            # Load secrets
            self._load_secrets_into_config(config)
            
            # Validate configuration
            self._validator.validate_config(config)
            
            return config
            
        except ValidationError as e:
            self._logger.error(f"Configuration loading failed: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
        except Exception as e:
            self._logger.error(f"Configuration loading failed: {e}")
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    def _get_environment(self) -> str:
        """Determine the current environment."""
        if os.environ.get("TESTING"):
            return "testing"
        
        # Check for Cloud Run deployment indicators
        k_service = os.environ.get("K_SERVICE")
        k_revision = os.environ.get("K_REVISION")
        
        if k_service or k_revision:
            # We're in Cloud Run - check for staging indicators
            if k_service and "staging" in k_service.lower():
                self._logger.debug(f"Detected staging environment from K_SERVICE: {k_service}")
                return "staging"
            if os.environ.get("PR_NUMBER"):
                self._logger.debug(f"Detected staging environment from PR_NUMBER: {os.environ.get('PR_NUMBER')}")
                return "staging"  # PR deployments are staging
        
        env = os.environ.get("ENVIRONMENT", "development").lower()
        self._logger.debug(f"Environment determined as: {env}")
        return env
    
    def _create_base_config(self, environment: str) -> AppConfig:
        """Create the base configuration object for the environment."""
        config_classes = {
            "production": ProductionConfig,
            "staging": StagingConfig,  # Staging now uses its own config
            "testing": NetraTestingConfig,
            "development": DevelopmentConfig
        }
        
        config_class = config_classes.get(environment, DevelopmentConfig)
        config = config_class()
        
        # Update WebSocket URL with actual server port if available
        server_port = os.environ.get('SERVER_PORT')
        if server_port:
            config.ws_config.ws_url = f"ws://localhost:{server_port}/ws"
            self._logger.info(f"Updated WebSocket URL to use port {server_port}")
        
        return config
    
    def _load_critical_env_vars(self, config: AppConfig):
        """Load critical environment variables that are not secrets."""
        critical_vars = {
            "DATABASE_URL": "database_url",
            "REDIS_URL": "redis_url", 
            "CLICKHOUSE_URL": "clickhouse_url",
            "CLICKHOUSE_HOST": None,  # Will be handled specially
            "CLICKHOUSE_PORT": None,  # Will be handled specially
            "CLICKHOUSE_PASSWORD": None,  # Will be handled specially
            "CLICKHOUSE_USER": None,  # Will be handled specially
            "JWT_SECRET_KEY": "jwt_secret_key",  # Critical for authentication
            "FERNET_KEY": "fernet_key",  # Critical for encryption
            "GEMINI_API_KEY": None,  # Will be handled specially for LLM configs
            "LOG_LEVEL": "log_level",
            "ENVIRONMENT": "environment",
            "PR_NUMBER": None,  # For staging environment tracking
        }
        
        for env_var, config_field in critical_vars.items():
            value = os.environ.get(env_var)
            if value:
                if config_field:
                    # Direct field assignment
                    if hasattr(config, config_field):
                        setattr(config, config_field, value)
                        self._logger.debug(f"Set {config_field} from {env_var}")
                
                # Handle special cases
                if env_var == "CLICKHOUSE_HOST" and hasattr(config, 'clickhouse_native'):
                    config.clickhouse_native.host = value
                    if hasattr(config, 'clickhouse_https'):
                        config.clickhouse_https.host = value
                    self._logger.debug(f"Set ClickHouse host from environment: {value}")
                    
                elif env_var == "CLICKHOUSE_PORT" and hasattr(config, 'clickhouse_native'):
                    try:
                        config.clickhouse_native.port = int(value)
                        if hasattr(config, 'clickhouse_https'):
                            config.clickhouse_https.port = int(value)
                        self._logger.debug(f"Set ClickHouse port from environment: {value}")
                    except ValueError:
                        self._logger.warning(f"Invalid CLICKHOUSE_PORT value: {value}")
                        
                elif env_var == "CLICKHOUSE_PASSWORD":
                    if hasattr(config, 'clickhouse_native'):
                        config.clickhouse_native.password = value
                    if hasattr(config, 'clickhouse_https'):
                        config.clickhouse_https.password = value
                    self._logger.debug("Set ClickHouse password from environment")
                    
                elif env_var == "CLICKHOUSE_USER" and hasattr(config, 'clickhouse_native'):
                    config.clickhouse_native.user = value
                    if hasattr(config, 'clickhouse_https'):
                        config.clickhouse_https.user = value
                    self._logger.debug(f"Set ClickHouse user from environment: {value}")
                    
                elif env_var == "GEMINI_API_KEY" and hasattr(config, 'llm_configs'):
                    # Set Gemini API key for all LLM configs that need it
                    for llm_name in ['default', 'analysis', 'triage', 'data', 
                                   'optimizations_core', 'actions_to_meet_goals', 
                                   'reporting', 'google']:
                        if llm_name in config.llm_configs and hasattr(config.llm_configs[llm_name], 'api_key'):
                            config.llm_configs[llm_name].api_key = value
                    self._logger.debug("Set Gemini API key from environment for LLM configs")
        
        # Log summary of critical vars loaded
        loaded_vars = [var for var in critical_vars.keys() if os.environ.get(var)]
        if loaded_vars:
            self._logger.info(f"Loaded {len(loaded_vars)} critical environment variables: {', '.join(loaded_vars)}")
    
    def _load_secrets_into_config(self, config: AppConfig):
        """Load secrets into the configuration object."""
        try:
            self._logger.info("Loading secrets into configuration...")
            secrets = self._secret_manager.load_secrets()
            
            if secrets:
                self._logger.info(f"Applying {len(secrets)} secrets to configuration")
                self._apply_secrets_to_config(config, secrets)
                
                # Log which critical secrets were successfully applied
                critical_secrets = ['gemini-api-key', 'jwt-secret-key', 'fernet-key']
                applied_critical = [s for s in critical_secrets if s in secrets]
                if applied_critical:
                    self._logger.info(f"Critical secrets applied: {', '.join(applied_critical)}")
                
                missing_critical = [s for s in critical_secrets if s not in secrets]
                if missing_critical:
                    self._logger.warning(f"Critical secrets missing: {', '.join(missing_critical)}")
            else:
                self._logger.warning("No secrets loaded, configuration may be incomplete")
                
        except Exception as e:
            self._logger.error(f"Failed to load secrets: {e}")
            # Don't fallback to environment variables - they should already be loaded in SecretManager
    
    def _apply_secrets_to_config(self, config: AppConfig, secrets: Dict[str, Any]):
        """Apply loaded secrets to configuration object."""
        # Apply secrets based on predefined mapping
        secret_mappings = self._get_secret_mappings()
        applied_count = 0
        
        for secret_name, secret_value in secrets.items():
            if secret_value and secret_name in secret_mappings:
                mapping = secret_mappings[secret_name]
                self._apply_secret_mapping(config, mapping, secret_value)
                applied_count += 1
                self._logger.debug(f"Applied secret: {secret_name} to {len(mapping.get('targets', [])) or 1} target(s)")
        
        self._logger.info(f"Successfully applied {applied_count} secrets to configuration")
    
    def _get_secret_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get the mapping of secrets to configuration fields."""
        return {
            "gemini-api-key": {
                # Gemini API key is used for Google/Gemini models and as default
                "targets": [
                    "llm_configs.default", 
                    "llm_configs.analysis",
                    "llm_configs.triage", 
                    "llm_configs.data", 
                    "llm_configs.optimizations_core", 
                    "llm_configs.actions_to_meet_goals", 
                    "llm_configs.reporting", 
                    "llm_configs.google"
                ],
                "field": "api_key"
            },
            # Branded LLM API Keys (optional - will skip init if not provided)
            "anthropic-api-key": {
                "targets": ["llm_configs.anthropic"],
                "field": "api_key"
            },
            "openai-api-key": {
                "targets": ["llm_configs.openai"],
                "field": "api_key"
            },
            "cohere-api-key": {
                "targets": ["llm_configs.cohere"],
                "field": "api_key"
            },
            "mistral-api-key": {
                "targets": ["llm_configs.mistral"],
                "field": "api_key"
            },
            "google-client-id": {
                "targets": ["google_cloud", "oauth_config"],
                "field": "client_id"
            },
            "google-client-secret": {
                "targets": ["google_cloud", "oauth_config"],
                "field": "client_secret"
            },
            "langfuse-secret-key": {
                "targets": ["langfuse"],
                "field": "secret_key"
            },
            "langfuse-public-key": {
                "targets": ["langfuse"],
                "field": "public_key"
            },
            "clickhouse-default-password": {
                "targets": ["clickhouse_native", "clickhouse_https"],
                "field": "password"
            },
            "clickhouse-development-password": {
                "targets": ["clickhouse_https_dev"],
                "field": "password"
            },
            "jwt-secret-key": {
                "targets": [],
                "field": "jwt_secret_key"
            },
            "fernet-key": {
                "targets": [],
                "field": "fernet_key"
            },
            "redis-default": {
                "targets": ["redis"],
                "field": "password"
            }
        }
    
    def get_configuration_summary(self) -> ConfigurationSummary:
        """Get a summary of the current configuration status."""
        config = self.get_config()
        
        # Count secrets
        secret_mappings = self._get_secret_mappings()
        total_secrets = len(secret_mappings)
        required_secrets = [name for name, mapping in secret_mappings.items() if mapping.required]
        
        return ConfigurationSummary(
            environment=Environment(config.environment),
            status=ConfigurationStatus.LOADED,
            loaded_at=datetime.now(),
            secrets_loaded=total_secrets,
            secrets_total=total_secrets,
            critical_secrets_missing=[],
            warnings=[],
            errors=[]
        )
    
    def _apply_secret_mapping(self, config: AppConfig, mapping: Dict[str, Any], secret_value: str):
        """Apply a single secret mapping to the configuration."""
        if not mapping["targets"]:
            # Direct field assignment
            setattr(config, mapping["field"], secret_value)
        else:
            # Nested field assignment
            for target in mapping["targets"]:
                self._set_nested_field(config, target, mapping["field"], secret_value)
    
    def _set_nested_field(self, config: AppConfig, target_path: str, field: str, value: str):
        """Set a nested field in the configuration object."""
        try:
            if '.' in target_path:
                parts = target_path.split('.', 1)
                parent_attr = getattr(config, parts[0])
                if isinstance(parent_attr, dict) and parts[1] in parent_attr:
                    target_obj = parent_attr[parts[1]]
                    if target_obj and hasattr(target_obj, field):
                        setattr(target_obj, field, value)
            else:
                target_obj = getattr(config, target_path, None)
                if target_obj and hasattr(target_obj, field):
                    setattr(target_obj, field, value)
        except AttributeError as e:
            self._logger.warning(f"Failed to set field {field} on {target_path}: {e}")
    
    def _load_from_environment_variables(self, config: AppConfig):
        """Fallback method to load configuration from environment variables."""
        env_mappings = {
            "GOOGLE_CLIENT_ID": ("oauth_config", "client_id"),
            "GOOGLE_CLIENT_SECRET": ("oauth_config", "client_secret"),
            "GEMINI_API_KEY": ("llm_configs.default", "api_key"),
            "JWT_SECRET_KEY": (None, "jwt_secret_key"),
            "FERNET_KEY": (None, "fernet_key"),
            "DATABASE_URL": (None, "database_url"),
            "LOG_LEVEL": (None, "log_level"),
        }
        
        for env_var, (target_path, field) in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                if target_path:
                    if target_path.startswith("llm_configs."):
                        # Handle LLM config specifically
                        llm_name = target_path.split(".")[1]
                        if llm_name in config.llm_configs:
                            setattr(config.llm_configs[llm_name], field, value)
                    else:
                        target_obj = getattr(config, target_path, None)
                        if target_obj:
                            setattr(target_obj, field, value)
                else:
                    setattr(config, field, value)
    
    def reload_config(self):
        """Force reload the configuration (clears cache)."""
        self.get_config.cache_clear()
        self._config = None


# Global configuration manager instance
_config_manager = ConfigManager()
config_manager = _config_manager  # Export for backward compatibility

# Convenient access functions
def get_config() -> AppConfig:
    """Get the current application configuration."""
    return _config_manager.get_config()

def reload_config():
    """Reload the configuration from environment."""
    _config_manager.reload_config()

# For backward compatibility
settings = get_config()