"""Configuration validation utilities."""

from typing import List, Optional
from pydantic import ValidationError
from app.logging_config import central_logger as logger

try:
    from app.schemas.Config import AppConfig
except ImportError:
    from schemas.Config import AppConfig


class ConfigurationValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


class ConfigValidator:
    """Validates application configuration for consistency and completeness."""
    
    def __init__(self):
        self._logger = logger
        
    def validate_config(self, config: AppConfig) -> None:
        """Validate the complete configuration object."""
        try:
            self._validate_database_config(config)
            self._validate_auth_config(config)
            self._validate_llm_config(config)
            self._validate_external_services(config)
            self._logger.info("Configuration validation completed successfully")
            
        except ConfigurationValidationError as e:
            self._logger.error(f"Configuration validation failed: {e}")
            raise
        except Exception as e:
            self._logger.error(f"Unexpected error during validation: {e}")
            raise ConfigurationValidationError(f"Validation failed: {e}")
    
    def _validate_database_config(self, config: AppConfig) -> None:
        """Validate database configuration."""
        errors = []
        
        # Check database URL (more lenient for staging/Cloud Run)
        import os
        is_cloud_run = os.getenv("K_SERVICE") is not None
        
        if not config.database_url:
            # In Cloud Run/staging, database URL might be set via env var
            if not is_cloud_run and config.environment not in ["staging", "development"]:
                errors.append("Database URL is not configured")
        elif not config.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            errors.append("Database URL must be a PostgreSQL connection string")
            
        # Check ClickHouse configurations
        if config.clickhouse_logging.enabled:
            clickhouse_configs = [
                ("clickhouse_native", config.clickhouse_native),
                ("clickhouse_https", config.clickhouse_https),
                ("clickhouse_https_dev", config.clickhouse_https_dev)
            ]
            
            for name, ch_config in clickhouse_configs:
                if not ch_config.host:
                    errors.append(f"{name} host is not configured")
                # Only require passwords in actual production, not staging
                if not ch_config.password and config.environment == "production":
                    errors.append(f"{name} password is required in production")
        
        if errors:
            raise ConfigurationValidationError(f"Database configuration errors: {', '.join(errors)}")
    
    def _validate_auth_config(self, config: AppConfig) -> None:
        """Validate authentication configuration."""
        errors = []
        
        # Check JWT configuration
        if not config.jwt_secret_key:
            errors.append("JWT secret key is not configured")
        elif config.environment == "production":
            # Check for weak or default secrets in production
            if len(config.jwt_secret_key) < 32:
                errors.append("JWT secret key must be at least 32 characters in production")
            if "development" in config.jwt_secret_key.lower() or "test" in config.jwt_secret_key.lower():
                errors.append("JWT secret key appears to be a development/test key - not suitable for production")
            
        # Check Fernet key
        if not config.fernet_key:
            errors.append("Fernet key is not configured")
            
        # Check OAuth configuration
        oauth = config.oauth_config
        if not oauth.client_id and config.environment not in ["testing", "development", "staging"]:
            errors.append("OAuth client ID is not configured")
        if not oauth.client_secret and config.environment not in ["testing", "development", "staging"]:
            errors.append("OAuth client secret is not configured")
            
        if errors:
            raise ConfigurationValidationError(f"Authentication configuration errors: {', '.join(errors)}")
    
    def _validate_llm_config(self, config: AppConfig) -> None:
        """Validate LLM configuration - only Gemini API key is required."""
        errors = []
        warnings = []
        
        # Skip LLM validation if LLMs are disabled in dev mode
        if hasattr(config, 'dev_mode_llm_enabled') and not config.dev_mode_llm_enabled:
            self._logger.info("LLMs disabled in dev mode - skipping API key validation")
            return
        
        if not config.llm_configs:
            errors.append("No LLM configurations defined")
        else:
            # Check for Gemini API key - this is the only required key
            gemini_key_found = False
            missing_keys = []
            
            for name, llm_config in config.llm_configs.items():
                if not llm_config.model_name:
                    errors.append(f"LLM '{name}' is missing model name")
                if not llm_config.provider:
                    errors.append(f"LLM '{name}' is missing provider")
                    
                # Check if this config has the Gemini API key
                if llm_config.api_key:
                    # If any config has an API key, we assume Gemini key was loaded
                    gemini_key_found = True
                elif config.environment != "testing":
                    missing_keys.append(name)
            
            # Only require Gemini API key to be present in at least one config
            if not gemini_key_found and config.environment != "testing":
                errors.append("Gemini API key is not configured (required for all LLM operations)")
            elif missing_keys:
                # Just log as warning if some configs don't have keys (they should inherit from Gemini)
                self._logger.info(f"LLM configs without explicit keys (will use Gemini key): {', '.join(missing_keys)}")
        
        if errors:
            self._logger.warning(f"LLM configuration warnings: {', '.join(errors)}")
            # Only fail in production/staging if Gemini key is missing
            if config.environment in ["production", "staging"] and not gemini_key_found:
                raise ConfigurationValidationError(f"LLM configuration errors: {', '.join(errors)}")
    
    def _validate_external_services(self, config: AppConfig) -> None:
        """Validate external service configurations."""
        errors = []
        
        # Check Redis configuration (if used)
        if hasattr(config, 'redis') and config.redis:
            if not config.redis.host:
                errors.append("Redis host is not configured")
            if not config.redis.password and config.environment == "production":
                errors.append("Redis password is required in production")
        
        # Check Langfuse configuration (if used for monitoring)
        if config.langfuse:
            if not config.langfuse.secret_key and config.environment == "production":
                self._logger.warning("Langfuse secret key not configured - monitoring may be limited")
            if not config.langfuse.public_key and config.environment == "production":
                self._logger.warning("Langfuse public key not configured - monitoring may be limited")
        
        if errors:
            raise ConfigurationValidationError(f"External service configuration errors: {', '.join(errors)}")
    
    def get_validation_report(self, config: AppConfig) -> List[str]:
        """Get a detailed validation report without raising exceptions."""
        report = []
        
        try:
            self.validate_config(config)
            report.append("✓ All configuration checks passed")
        except ConfigurationValidationError as e:
            report.append(f"✗ Configuration validation failed: {e}")
        except Exception as e:
            report.append(f"✗ Unexpected validation error: {e}")
        
        # Add informational items
        report.append(f"Environment: {config.environment}")
        report.append(f"Database: {'Configured' if config.database_url else 'Not configured'}")
        report.append(f"LLM Configs: {len(config.llm_configs)} configured")
        report.append(f"Auth: {'JWT+OAuth' if config.jwt_secret_key and config.oauth_config.client_id else 'Partial'}")
        
        return report