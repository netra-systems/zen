"""Configuration validation utilities."""

from typing import List, Optional, Tuple
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
        elif config.environment != "testing" and not config.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
            # Allow SQLite for testing environment
            errors.append("Database URL must be a PostgreSQL connection string")
            
        # Skip ClickHouse validation if ClickHouse is disabled in dev mode
        if hasattr(config, 'dev_mode_clickhouse_enabled') and not config.dev_mode_clickhouse_enabled:
            self._logger.info("ClickHouse disabled in dev mode - skipping ClickHouse validation")
        # Check ClickHouse configurations
        elif config.clickhouse_logging.enabled:
            clickhouse_configs = [
                ("clickhouse_native", config.clickhouse_native),
                ("clickhouse_https", config.clickhouse_https)
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
        if self._should_skip_llm_validation(config):
            return
        
        errors = self._check_llm_configurations(config)
        gemini_key_found = self._check_gemini_api_key(config, errors)
        self._handle_llm_validation_results(config, errors, gemini_key_found)
    
    def _should_skip_llm_validation(self, config: AppConfig) -> bool:
        """Check if LLM validation should be skipped."""
        if hasattr(config, 'dev_mode_llm_enabled') and not config.dev_mode_llm_enabled:
            self._logger.info("LLMs disabled in dev mode - skipping API key validation")
            return True
        return False
    
    def _check_llm_configurations(self, config: AppConfig) -> List[str]:
        """Check basic LLM configuration requirements."""
        errors = []
        if not config.llm_configs:
            errors.append("No LLM configurations defined")
        else:
            errors.extend(self._validate_individual_llm_configs(config))
        return errors
    
    def _validate_individual_llm_configs(self, config: AppConfig) -> List[str]:
        """Validate individual LLM configuration entries."""
        errors = []
        for name, llm_config in config.llm_configs.items():
            if not llm_config.model_name:
                errors.append(f"LLM '{name}' is missing model name")
            if not llm_config.provider:
                errors.append(f"LLM '{name}' is missing provider")
        return errors
    
    def _check_gemini_api_key(self, config: AppConfig, errors: List[str]) -> bool:
        """Check for Gemini API key availability."""
        if not config.llm_configs:
            return False
        
        gemini_key_found, missing_keys = self._scan_for_api_keys(config)
        self._log_missing_keys_warning(missing_keys)
        self._validate_gemini_key_requirement(config, gemini_key_found, errors)
        return gemini_key_found
    
    def _scan_for_api_keys(self, config: AppConfig) -> Tuple[bool, List[str]]:
        """Scan LLM configs for API keys."""
        gemini_key_found = False
        missing_keys = []
        
        for name, llm_config in config.llm_configs.items():
            if llm_config.api_key:
                gemini_key_found = True
            elif config.environment != "testing":
                missing_keys.append(name)
        
        return gemini_key_found, missing_keys
    
    def _log_missing_keys_warning(self, missing_keys: List[str]) -> None:
        """Log warning for configs without explicit keys."""
        if missing_keys:
            self._logger.info(f"LLM configs without explicit keys (will use Gemini key): {', '.join(missing_keys)}")
    
    def _validate_gemini_key_requirement(self, config: AppConfig, gemini_key_found: bool, errors: List[str]) -> None:
        """Validate Gemini API key requirement."""
        if not gemini_key_found and config.environment != "testing":
            errors.append("Gemini API key is not configured (required for all LLM operations)")
    
    def _handle_llm_validation_results(self, config: AppConfig, errors: List[str], gemini_key_found: bool) -> None:
        """Handle LLM validation results and errors."""
        if errors:
            self._logger.warning(f"LLM configuration warnings: {', '.join(errors)}")
            if config.environment in ["production", "staging"] and not gemini_key_found:
                raise ConfigurationValidationError(f"LLM configuration errors: {', '.join(errors)}")
    
    def _validate_external_services(self, config: AppConfig) -> None:
        """Validate external service configurations."""
        errors = []
        
        # Skip Redis validation if Redis is disabled in dev mode
        if hasattr(config, 'dev_mode_redis_enabled') and not config.dev_mode_redis_enabled:
            self._logger.info("Redis disabled in dev mode - skipping Redis validation")
        # Check Redis configuration (if used)
        elif hasattr(config, 'redis') and config.redis:
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