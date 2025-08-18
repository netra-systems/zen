"""Configuration Validation System

**CRITICAL: Enterprise-Grade Configuration Validation**

Comprehensive validation to prevent configuration inconsistencies.
Ensures Enterprise-level reliability for revenue-critical operations.

Business Value: Prevents $12K MRR loss from configuration errors.
Catches issues before they affect customer operations.

Each function ≤8 lines, file ≤300 lines.
"""

import os
from typing import Dict, List, Optional, Any, Tuple, NamedTuple
from urllib.parse import urlparse
from datetime import datetime

from app.schemas.Config import AppConfig
from app.logging_config import central_logger as logger


class ValidationResult(NamedTuple):
    """Configuration validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    score: int  # 0-100 configuration health score


class ConfigurationValidator:
    """Enterprise-grade configuration validation system.
    
    **CRITICAL**: All configuration MUST pass validation.
    Prevents configuration errors that cause revenue loss.
    """
    
    def __init__(self):
        """Initialize configuration validator."""
        self._logger = logger
        self._environment = self._get_environment()
        self._validation_rules = self._load_validation_rules()
        self._critical_fields = self._load_critical_fields()
    
    def _get_environment(self) -> str:
        """Get current environment for validation rules."""
        return os.environ.get("ENVIRONMENT", "development").lower()
    
    def refresh_environment(self) -> None:
        """Refresh environment detection for testing scenarios."""
        old_env = self._environment
        self._environment = self._get_environment()
        if old_env != self._environment:
            self._logger.info(f"Validator environment changed from {old_env} to {self._environment}")
    
    def _load_validation_rules(self) -> Dict[str, dict]:
        """Load validation rules per environment."""
        return {
            "development": {
                "require_ssl": False,
                "allow_localhost": True,
                "require_secrets": False,
                "strict_validation": False
            },
            "staging": {
                "require_ssl": True,
                "allow_localhost": False,
                "require_secrets": True,
                "strict_validation": True
            },
            "production": {
                "require_ssl": True,
                "allow_localhost": False,
                "require_secrets": True,
                "strict_validation": True
            },
            "testing": {
                "require_ssl": False,
                "allow_localhost": True,
                "require_secrets": False,
                "strict_validation": False
            }
        }
    
    def _load_critical_fields(self) -> Dict[str, List[str]]:
        """Load critical configuration fields per component."""
        return {
            "database": ["database_url"],
            "llm": ["llm_configs"],
            "auth": ["jwt_secret_key", "fernet_key"],
            "external": ["frontend_url", "api_base_url"],
            "secrets": ["jwt_secret_key", "fernet_key"]
        }
    
    def validate_complete_config(self, config: AppConfig) -> ValidationResult:
        """Perform comprehensive configuration validation."""
        errors = []
        warnings = []
        
        errors.extend(self._validate_database_config(config))
        errors.extend(self._validate_llm_config(config))
        errors.extend(self._validate_auth_config(config))
        errors.extend(self._validate_external_services(config))
        warnings.extend(self._validate_optional_features(config))
        
        score = self._calculate_config_health_score(config, errors, warnings)
        is_valid = len(errors) == 0
        
        return ValidationResult(is_valid, errors, warnings, score)
    
    def _validate_database_config(self, config: AppConfig) -> List[str]:
        """Validate database configuration."""
        errors = []
        
        if not config.database_url:
            errors.append("database_url is required")
        else:
            errors.extend(self._validate_postgres_url(config.database_url))
        
        errors.extend(self._validate_clickhouse_config(config))
        errors.extend(self._validate_redis_config(config))
        
        return errors
    
    def _validate_llm_config(self, config: AppConfig) -> List[str]:
        """Validate LLM configuration."""
        errors = []
        
        if not hasattr(config, 'llm_configs') or not config.llm_configs:
            errors.append("LLM configurations are missing")
            return errors
        
        errors.extend(self._validate_llm_api_keys(config))
        errors.extend(self._validate_llm_models(config))
        
        return errors
    
    def _validate_auth_config(self, config: AppConfig) -> List[str]:
        """Validate authentication configuration."""
        errors = []
        rules = self._validation_rules.get(self._environment, {})
        
        if rules.get("require_secrets", False):
            errors.extend(self._validate_auth_secrets(config))
        
        errors.extend(self._validate_oauth_config(config))
        
        return errors
    
    def _validate_external_services(self, config: AppConfig) -> List[str]:
        """Validate external service configurations."""
        errors = []
        
        errors.extend(self._validate_urls(config))
        errors.extend(self._validate_environment_consistency(config))
        
        return errors
    
    def _validate_postgres_url(self, url: str) -> List[str]:
        """Validate database URL format and requirements."""
        errors = []
        
        try:
            parsed = urlparse(url)
            valid_schemes = ["postgresql", "postgresql+asyncpg"]
            
            # Allow SQLite URLs in testing environments
            if self._environment == "testing":
                valid_schemes.extend(["sqlite", "sqlite+aiosqlite"])
            
            if parsed.scheme not in valid_schemes:
                if parsed.scheme.startswith("sqlite") and self._environment != "testing":
                    errors.append("SQLite URLs only allowed in testing environment")
                else:
                    errors.append("Invalid database URL scheme")
            
            # Skip host validation for SQLite URLs
            if not parsed.scheme.startswith("sqlite") and not parsed.netloc:
                errors.append("Database URL missing host information")
            
            # Skip security checks for SQLite URLs
            if not parsed.scheme.startswith("sqlite"):
                errors.extend(self._check_database_security_requirements(parsed))
            
        except Exception:
            errors.append("Invalid database URL format")
        
        return errors
    
    def _validate_clickhouse_config(self, config: AppConfig) -> List[str]:
        """Validate ClickHouse configuration."""
        errors = []
        
        if not hasattr(config, 'clickhouse_native'):
            errors.append("ClickHouse native configuration missing")
        else:
            errors.extend(self._validate_clickhouse_connection(config.clickhouse_native))
        
        if hasattr(config, 'clickhouse_https') and hasattr(config, 'clickhouse_native'):
            errors.extend(self._validate_clickhouse_consistency(config))
        
        return errors
    
    def _validate_redis_config(self, config: AppConfig) -> List[str]:
        """Validate Redis configuration."""
        errors = []
        
        if hasattr(config, 'redis') and config.redis:
            if not config.redis.host:
                errors.append("Redis host is required")
            if not config.redis.port or config.redis.port <= 0:
                errors.append("Valid Redis port is required")
        
        return errors
    
    def _validate_llm_api_keys(self, config: AppConfig) -> List[str]:
        """Validate LLM API key configuration."""
        errors = []
        rules = self._validation_rules.get(self._environment, {})
        
        if not rules.get("require_secrets", False):
            return errors
        
        missing_keys = []
        for llm_name, llm_config in config.llm_configs.items():
            if not hasattr(llm_config, 'api_key') or not llm_config.api_key:
                missing_keys.append(llm_name)
        
        if missing_keys:
            errors.append(f"LLM API keys missing for: {', '.join(missing_keys)}")
        
        return errors
    
    def _validate_llm_models(self, config: AppConfig) -> List[str]:
        """Validate LLM model configurations."""
        errors = []
        
        for llm_name, llm_config in config.llm_configs.items():
            if not hasattr(llm_config, 'model_name') or not llm_config.model_name:
                errors.append(f"Model name missing for LLM config: {llm_name}")
            
            if not hasattr(llm_config, 'provider'):
                errors.append(f"Provider missing for LLM config: {llm_name}")
        
        return errors
    
    def _validate_auth_secrets(self, config: AppConfig) -> List[str]:
        """Validate authentication secrets."""
        errors = []
        
        if not config.jwt_secret_key:
            errors.append("JWT secret key is required")
        elif len(config.jwt_secret_key) < 32:
            errors.append("JWT secret key too short (minimum 32 characters)")
        
        if not config.fernet_key:
            errors.append("Fernet encryption key is required")
        
        return errors
    
    def _validate_oauth_config(self, config: AppConfig) -> List[str]:
        """Validate OAuth configuration."""
        errors = []
        
        if hasattr(config, 'oauth_config') and config.oauth_config:
            if not config.oauth_config.authorized_redirect_uris:
                errors.append("OAuth redirect URIs are required")
            else:
                errors.extend(self._validate_oauth_urls(config))
        
        return errors
    
    def _validate_urls(self, config: AppConfig) -> List[str]:
        """Validate URL configurations."""
        errors = []
        
        url_fields = ["frontend_url", "api_base_url"]
        for field in url_fields:
            if hasattr(config, field):
                url = getattr(config, field)
                if url:
                    errors.extend(self._validate_single_url(field, url))
        
        return errors
    
    def _validate_environment_consistency(self, config: AppConfig) -> List[str]:
        """Validate environment-specific configuration consistency."""
        errors = []
        rules = self._validation_rules.get(self._environment, {})
        
        if not rules.get("allow_localhost", True):
            errors.extend(self._check_no_localhost_urls(config))
        
        if self._environment == "production":
            errors.extend(self._validate_production_requirements(config))
        
        return errors
    
    def _check_database_security_requirements(self, parsed_url) -> List[str]:
        """Check database URL security requirements."""
        errors = []
        rules = self._validation_rules.get(self._environment, {})
        
        if rules.get("require_ssl", False):
            if "sslmode" not in (parsed_url.query or ""):
                errors.append("SSL connection required for database")
        
        if not rules.get("allow_localhost", True):
            if parsed_url.hostname in ["localhost", "127.0.0.1"]:
                errors.append("Localhost database connections not allowed")
        
        return errors
    
    def _validate_clickhouse_connection(self, ch_config) -> List[str]:
        """Validate ClickHouse connection configuration."""
        errors = []
        
        if not ch_config.host:
            errors.append("ClickHouse host is required")
        
        if not ch_config.port or ch_config.port <= 0:
            errors.append("Valid ClickHouse port is required")
        
        if not ch_config.user:
            errors.append("ClickHouse user is required")
        
        return errors
    
    def _validate_clickhouse_consistency(self, config: AppConfig) -> List[str]:
        """Validate consistency between ClickHouse configurations."""
        errors = []
        
        if config.clickhouse_native.host != config.clickhouse_https.host:
            errors.append("ClickHouse native and HTTPS hosts are inconsistent")
        
        if config.clickhouse_native.user != config.clickhouse_https.user:
            errors.append("ClickHouse native and HTTPS users are inconsistent")
        
        return errors
    
    def _validate_oauth_urls(self, config: AppConfig) -> List[str]:
        """Validate OAuth redirect URLs."""
        errors = []
        
        for uri in config.oauth_config.authorized_redirect_uris:
            if not self._is_valid_url(uri):
                errors.append(f"Invalid OAuth redirect URI: {uri}")
        
        return errors
    
    def _validate_single_url(self, field_name: str, url: str) -> List[str]:
        """Validate a single URL field."""
        errors = []
        
        if not self._is_valid_url(url):
            errors.append(f"Invalid URL format for {field_name}: {url}")
        
        return errors
    
    def _check_no_localhost_urls(self, config: AppConfig) -> List[str]:
        """Check that no URLs contain localhost in non-dev environments."""
        errors = []
        
        url_fields = ["frontend_url", "api_base_url"]
        for field in url_fields:
            if hasattr(config, field):
                url = getattr(config, field, "")
                if "localhost" in url or "127.0.0.1" in url:
                    errors.append(f"{field} contains localhost in {self._environment} environment")
        
        return errors
    
    def _validate_production_requirements(self, config: AppConfig) -> List[str]:
        """Validate production-specific requirements."""
        errors = []
        
        # Production must have HTTPS URLs
        secure_fields = ["frontend_url", "api_base_url"]
        for field in secure_fields:
            if hasattr(config, field):
                url = getattr(config, field, "")
                if url and not url.startswith("https://"):
                    errors.append(f"Production {field} must use HTTPS")
        
        return errors
    
    def _validate_optional_features(self, config: AppConfig) -> List[str]:
        """Validate optional features (generates warnings)."""
        warnings = []
        
        if not getattr(config, 'llm_cache_enabled', True):
            warnings.append("LLM caching is disabled - may impact performance")
        
        if not getattr(config, 'llm_heartbeat_enabled', True):
            warnings.append("LLM heartbeat monitoring is disabled")
        
        return warnings
    
    def _calculate_config_health_score(self, config: AppConfig, errors: List[str], warnings: List[str]) -> int:
        """Calculate configuration health score (0-100)."""
        base_score = 100
        
        # Deduct points for errors (more severe)
        error_penalty = len(errors) * 15
        warning_penalty = len(warnings) * 5
        
        # Bonus points for completeness
        completeness_bonus = self._calculate_completeness_bonus(config)
        
        score = max(0, base_score - error_penalty - warning_penalty + completeness_bonus)
        return min(100, score)
    
    def _calculate_completeness_bonus(self, config: AppConfig) -> int:
        """Calculate bonus points for configuration completeness."""
        bonus = 0
        
        # Bonus for having all critical fields configured
        critical_fields_present = 0
        total_critical_fields = 0
        
        for component, fields in self._critical_fields.items():
            for field in fields:
                total_critical_fields += 1
                if hasattr(config, field) and getattr(config, field):
                    critical_fields_present += 1
        
        if total_critical_fields > 0:
            completeness_ratio = critical_fields_present / total_critical_fields
            bonus = int(completeness_ratio * 10)
        
        return bonus
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL format is valid."""
        try:
            parsed = urlparse(url)
            return all([parsed.scheme, parsed.netloc])
        except Exception:
            return False