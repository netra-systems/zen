"""Configuration validation utilities."""

from typing import Any, List, Optional, Tuple

from pydantic import ValidationError

from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.logging_config import central_logger as logger

try:
    from netra_backend.app.schemas.config import AppConfig
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
            self._validate_all_config_sections(config)
            self._logger.info("Configuration validation completed successfully")
        except ConfigurationValidationError as e:
            self._handle_config_validation_error(e)
        except Exception as e:
            self._handle_unexpected_validation_error(e)
    
    def _validate_all_config_sections(self, config: AppConfig) -> None:
        """Validate all configuration sections."""
        self._validate_database_config(config)
        self._validate_auth_config(config)
        self._validate_llm_config(config)
        self._validate_external_services(config)
    
    def _handle_config_validation_error(self, error: ConfigurationValidationError) -> None:
        """Handle configuration validation errors."""
        self._logger.error(f"Configuration validation failed: {error}")
        raise
    
    def _handle_unexpected_validation_error(self, error: Exception) -> None:
        """Handle unexpected validation errors."""
        self._logger.error(f"Unexpected error during validation: {error}")
        raise ConfigurationValidationError(f"Validation failed: {error}")
    
    def _validate_database_config(self, config: AppConfig) -> None:
        """Validate database configuration."""
        errors = []
        self._validate_database_url(config, errors)
        self._validate_clickhouse_config(config, errors)
        if errors:
            raise ConfigurationValidationError(f"Database configuration errors: {', '.join(errors)}")
    
    def _validate_database_url(self, config: AppConfig, errors: list) -> None:
        """Validate database URL configuration."""
        unified_config = get_unified_config()
        is_cloud_run = unified_config.deployment.is_cloud_run
        self._check_database_url_presence(config, errors, is_cloud_run)
        self._check_database_url_format(config, errors)
    
    def _check_database_url_presence(self, config: AppConfig, errors: list, is_cloud_run: bool) -> None:
        """Check if database URL is present when required."""
        if not config.database_url:
            if not is_cloud_run and config.environment not in ["staging", "development"]:
                errors.append("Database URL is not configured")
    
    def _check_database_url_format(self, config: AppConfig, errors: list) -> None:
        """Check database URL format requirements."""
        if config.database_url and config.environment != "testing":
            if not config.database_url.startswith(("postgresql://", "postgresql+asyncpg://")):
                errors.append("Database URL must be a PostgreSQL connection string")
    
    def _validate_clickhouse_config(self, config: AppConfig, errors: list) -> None:
        """Validate ClickHouse configuration if enabled."""
        if self._should_skip_clickhouse_validation(config):
            return
        if config.clickhouse_logging.enabled:
            self._check_clickhouse_hosts_and_passwords(config, errors)
    
    def _should_skip_clickhouse_validation(self, config: AppConfig) -> bool:
        """Check if ClickHouse validation should be skipped."""
        if hasattr(config, 'dev_mode_clickhouse_enabled') and not config.dev_mode_clickhouse_enabled:
            self._logger.info("ClickHouse disabled in dev mode - skipping ClickHouse validation")
            return True
        return False
    
    def _check_clickhouse_hosts_and_passwords(self, config: AppConfig, errors: list) -> None:
        """Check ClickHouse host and password configurations."""
        clickhouse_configs = [
            ("clickhouse_native", config.clickhouse_native),
            ("clickhouse_https", config.clickhouse_https)
        ]
        for name, ch_config in clickhouse_configs:
            self._validate_single_clickhouse_config(name, ch_config, config.environment, errors)
    
    def _validate_single_clickhouse_config(self, name: str, ch_config: Any, environment: str, errors: list) -> None:
        """Validate a single ClickHouse configuration."""
        if not ch_config.host:
            errors.append(f"{name} host is not configured")
        if not ch_config.password and environment == "production":
            errors.append(f"{name} password is required in production")
    
    def _validate_auth_config(self, config: AppConfig) -> None:
        """Validate authentication configuration."""
        errors = []
        self._validate_jwt_config(config, errors)
        self._validate_fernet_config(config, errors)
        self._validate_oauth_config(config, errors)
        if errors:
            raise ConfigurationValidationError(f"Authentication configuration errors: {', '.join(errors)}")
    
    def _validate_jwt_config(self, config: AppConfig, errors: List[str]) -> None:
        """Validate JWT configuration."""
        if not config.jwt_secret_key:
            errors.append("JWT secret key is not configured")
        elif config.environment == "production":
            self._validate_production_jwt_key(config, errors)
    
    def _validate_production_jwt_key(self, config: AppConfig, errors: List[str]) -> None:
        """Validate JWT key for production environment."""
        if len(config.jwt_secret_key) < 32:
            errors.append("JWT secret key must be at least 32 characters in production")
        if "development" in config.jwt_secret_key.lower() or "test" in config.jwt_secret_key.lower():
            errors.append("JWT secret key appears to be a development/test key - not suitable for production")
    
    def _validate_fernet_config(self, config: AppConfig, errors: List[str]) -> None:
        """Validate Fernet key configuration."""
        if not config.fernet_key:
            errors.append("Fernet key is not configured")
    
    def _validate_oauth_config(self, config: AppConfig, errors: List[str]) -> None:
        """Validate OAuth configuration."""
        oauth = config.oauth_config
        dev_environments = ["testing", "development", "staging"]
        if not oauth.client_id and config.environment not in dev_environments:
            errors.append("OAuth client ID is not configured")
        if not oauth.client_secret and config.environment not in dev_environments:
            errors.append("OAuth client secret is not configured")
    
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
        self._validate_redis_configuration(config, errors)
        self._validate_langfuse_configuration(config)
        
        if errors:
            raise ConfigurationValidationError(f"External service configuration errors: {', '.join(errors)}")
    
    def _validate_redis_configuration(self, config: AppConfig, errors: List[str]) -> None:
        """Validate Redis configuration if enabled."""
        if self._should_skip_redis_validation(config):
            self._logger.info("Redis disabled in dev mode - skipping Redis validation")
            return
        
        if hasattr(config, 'redis') and config.redis:
            self._check_redis_host_and_password(config, errors)
    
    def _should_skip_redis_validation(self, config: AppConfig) -> bool:
        """Check if Redis validation should be skipped."""
        return hasattr(config, 'dev_mode_redis_enabled') and not config.dev_mode_redis_enabled
    
    def _check_redis_host_and_password(self, config: AppConfig, errors: List[str]) -> None:
        """Check Redis host and password configuration."""
        if not config.redis.host:
            errors.append("Redis host is not configured")
        if not config.redis.password and config.environment == "production":
            errors.append("Redis password is required in production")
    
    def _validate_langfuse_configuration(self, config: AppConfig) -> None:
        """Validate Langfuse configuration for monitoring."""
        if not config.langfuse:
            return
        
        if config.environment == "production":
            self._check_langfuse_keys(config)
    
    def _check_langfuse_keys(self, config: AppConfig) -> None:
        """Check Langfuse key configuration for production."""
        if not config.langfuse.secret_key:
            self._logger.warning("Langfuse secret key not configured - monitoring may be limited")
        if not config.langfuse.public_key:
            self._logger.warning("Langfuse public key not configured - monitoring may be limited")
    
    def get_validation_report(self, config: AppConfig) -> List[str]:
        """Get a detailed validation report without raising exceptions."""
        report = []
        self._add_validation_status_to_report(config, report)
        self._add_informational_items_to_report(config, report)
        return report
    
    def _add_validation_status_to_report(self, config: AppConfig, report: List[str]) -> None:
        """Add validation status to report."""
        try:
            self.validate_config(config)
            report.append("[U+2713] All configuration checks passed")
        except ConfigurationValidationError as e:
            report.append(f"[U+2717] Configuration validation failed: {e}")
        except Exception as e:
            report.append(f"[U+2717] Unexpected validation error: {e}")
    
    def _add_informational_items_to_report(self, config: AppConfig, report: List[str]) -> None:
        """Add informational items to validation report."""
        report.append(f"Environment: {config.environment}")
        report.append(f"Database: {'Configured' if config.database_url else 'Not configured'}")
        report.append(f"LLM Configs: {len(config.llm_configs)} configured")
        auth_status = self._get_auth_status(config)
        report.append(f"Auth: {auth_status}")
    
    def _get_auth_status(self, config: AppConfig) -> str:
        """Get authentication configuration status."""
        if config.jwt_secret_key and config.oauth_config.client_id:
            return "JWT+OAuth"
        return "Partial"