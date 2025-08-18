"""Database Configuration Management

**CRITICAL: Single Source of Truth for Database Configuration**

Manages all DATABASE_URL, CLICKHOUSE_URL, POSTGRES_URL references.
Eliminates inconsistencies across 110+ files.

Business Value: Prevents $12K MRR loss from database configuration errors.
Enterprise customers require 100% database reliability.

Each function ≤8 lines, file ≤300 lines.
"""

import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from app.schemas.Config import AppConfig
from app.logging_config import central_logger as logger
from app.core.exceptions_config import ConfigurationError


class DatabaseConfigManager:
    """Unified database configuration management.
    
    **MANDATORY**: All database configuration MUST use this manager.
    Ensures consistency across PostgreSQL and ClickHouse connections.
    """
    
    def __init__(self):
        """Initialize database configuration manager."""
        self._logger = logger
        self._environment = self._get_environment()
        self._validation_rules = self._load_validation_rules()
        self._connection_templates = self._load_connection_templates()
    
    def _get_environment(self) -> str:
        """Get current environment for database configuration."""
        return os.environ.get("ENVIRONMENT", "development").lower()
    
    def _load_validation_rules(self) -> Dict[str, dict]:
        """Load database validation rules per environment."""
        return {
            "development": {"require_ssl": False, "allow_localhost": True},
            "staging": {"require_ssl": True, "allow_localhost": False},
            "production": {"require_ssl": True, "allow_localhost": False},
            "testing": {"require_ssl": False, "allow_localhost": True}
        }
    
    def _load_connection_templates(self) -> Dict[str, str]:
        """Load database connection URL templates."""
        return {
            "postgres_dev": "postgresql+asyncpg://postgres:postgres@localhost:5432/netra",
            "postgres_staging": "postgresql+asyncpg://user:pass@staging-host:5432/netra",
            "postgres_production": "postgresql+asyncpg://user:pass@prod-host:5432/netra",
            "clickhouse_dev": "clickhouse://default:@localhost:8123/default"
        }
    
    def populate_database_config(self, config: AppConfig) -> None:
        """Populate all database configuration in config object."""
        self._populate_postgres_config(config)
        self._populate_clickhouse_config(config)
        self._populate_redis_config(config)
        self._logger.info(f"Populated database config for {self._environment}")
    
    def _populate_postgres_config(self, config: AppConfig) -> None:
        """Populate PostgreSQL configuration."""
        postgres_url = self._get_postgres_url()
        if postgres_url:
            config.database_url = postgres_url
            self._validate_postgres_url(postgres_url)
    
    def _populate_clickhouse_config(self, config: AppConfig) -> None:
        """Populate ClickHouse configuration."""
        clickhouse_config = self._get_clickhouse_configuration()
        self._apply_clickhouse_config(config, clickhouse_config)
        self._set_clickhouse_url(config)
    
    def _populate_redis_config(self, config: AppConfig) -> None:
        """Populate Redis configuration."""
        redis_url = self._get_redis_url()
        if redis_url:
            config.redis_url = redis_url
            self._update_redis_config_object(config, redis_url)
    
    def _get_postgres_url(self) -> Optional[str]:
        """Get PostgreSQL URL from environment or defaults."""
        url = os.environ.get("DATABASE_URL")
        if not url:
            url = self._get_default_postgres_url()
        return url
    
    def _get_default_postgres_url(self) -> str:
        """Get default PostgreSQL URL for environment."""
        template_key = f"postgres_{self._environment}"
        return self._connection_templates.get(template_key, 
                                             self._connection_templates["postgres_dev"])
    
    def _validate_postgres_url(self, url: str) -> None:
        """Validate PostgreSQL URL against environment rules."""
        parsed = urlparse(url)
        rules = self._validation_rules.get(self._environment, {})
        self._check_ssl_requirement(parsed, rules)
        self._check_localhost_policy(parsed, rules)
    
    def _check_ssl_requirement(self, parsed_url, rules: dict) -> None:
        """Check SSL requirement for database connection."""
        if rules.get("require_ssl", False):
            if "sslmode" not in parsed_url.query:
                raise ConfigurationError(f"SSL required for {self._environment} environment")
    
    def _check_localhost_policy(self, parsed_url, rules: dict) -> None:
        """Check localhost policy for database connection."""
        if not rules.get("allow_localhost", True):
            if parsed_url.hostname in ["localhost", "127.0.0.1"]:
                raise ConfigurationError(f"Localhost not allowed in {self._environment}")
    
    def _get_clickhouse_configuration(self) -> Dict[str, str]:
        """Get ClickHouse configuration from environment."""
        return {
            "host": os.environ.get("CLICKHOUSE_HOST", "localhost"),
            "port": os.environ.get("CLICKHOUSE_PORT", "8123"),
            "user": os.environ.get("CLICKHOUSE_USER", "default"),
            "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
            "database": os.environ.get("CLICKHOUSE_DB", "default")
        }
    
    def _apply_clickhouse_config(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply ClickHouse configuration to config objects."""
        self._apply_to_clickhouse_native(config, ch_config)
        self._apply_to_clickhouse_https(config, ch_config)
        self._apply_to_clickhouse_dev(config, ch_config)
    
    def _apply_to_clickhouse_native(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse native connection."""
        if hasattr(config, 'clickhouse_native'):
            config.clickhouse_native.host = ch_config["host"]
            config.clickhouse_native.port = int(ch_config["port"])
            config.clickhouse_native.user = ch_config["user"]
            config.clickhouse_native.password = ch_config["password"]
            config.clickhouse_native.database = ch_config["database"]
    
    def _apply_to_clickhouse_https(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse HTTPS connection."""
        if hasattr(config, 'clickhouse_https'):
            config.clickhouse_https.host = ch_config["host"]
            config.clickhouse_https.port = int(ch_config.get("https_port", "8443"))
            config.clickhouse_https.user = ch_config["user"]
            config.clickhouse_https.password = ch_config["password"]
            config.clickhouse_https.database = ch_config["database"]
    
    def _apply_to_clickhouse_dev(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse development connection."""
        if hasattr(config, 'clickhouse_https_dev'):
            config.clickhouse_https_dev.host = ch_config["host"]
            config.clickhouse_https_dev.user = ch_config.get("dev_user", "development_user")
            config.clickhouse_https_dev.password = ch_config["password"]
            config.clickhouse_https_dev.database = ch_config.get("dev_db", "development")
    
    def _set_clickhouse_url(self, config: AppConfig) -> None:
        """Set unified ClickHouse URL for external integrations."""
        clickhouse_url = os.environ.get("CLICKHOUSE_URL")
        if not clickhouse_url and hasattr(config, 'clickhouse_native'):
            clickhouse_url = self._build_clickhouse_url(config.clickhouse_native)
        if clickhouse_url:
            config.clickhouse_url = clickhouse_url
    
    def _build_clickhouse_url(self, ch_config) -> str:
        """Build ClickHouse URL from configuration object."""
        password_part = f":{ch_config.password}" if ch_config.password else ""
        return f"clickhouse://{ch_config.user}{password_part}@{ch_config.host}:{ch_config.port}/{ch_config.database}"
    
    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from environment."""
        return os.environ.get("REDIS_URL")
    
    def _update_redis_config_object(self, config: AppConfig, redis_url: str) -> None:
        """Update Redis configuration object from URL."""
        if hasattr(config, 'redis'):
            parsed = urlparse(redis_url)
            if parsed.hostname:
                config.redis.host = parsed.hostname
            if parsed.port:
                config.redis.port = parsed.port
            if parsed.password:
                config.redis.password = parsed.password
    
    def validate_database_consistency(self, config: AppConfig) -> List[str]:
        """Validate database configuration consistency."""
        issues = []
        issues.extend(self._validate_postgres_consistency(config))
        issues.extend(self._validate_clickhouse_consistency(config))
        issues.extend(self._validate_redis_consistency(config))
        return issues
    
    def _validate_postgres_consistency(self, config: AppConfig) -> List[str]:
        """Validate PostgreSQL configuration consistency."""
        issues = []
        if not config.database_url:
            issues.append("Missing PostgreSQL database_url")
        elif not self._is_valid_postgres_url(config.database_url):
            issues.append("Invalid PostgreSQL database_url format")
        return issues
    
    def _validate_clickhouse_consistency(self, config: AppConfig) -> List[str]:
        """Validate ClickHouse configuration consistency."""
        issues = []
        if hasattr(config, 'clickhouse_native') and hasattr(config, 'clickhouse_https'):
            if config.clickhouse_native.host != config.clickhouse_https.host:
                issues.append("ClickHouse native and HTTPS hosts are inconsistent")
        return issues
    
    def _validate_redis_consistency(self, config: AppConfig) -> List[str]:
        """Validate Redis configuration consistency."""
        issues = []
        if hasattr(config, 'redis') and config.redis_url:
            parsed_url = urlparse(config.redis_url)
            if parsed_url.hostname != config.redis.host:
                issues.append("Redis URL and config object host mismatch")
        return issues
    
    def _is_valid_postgres_url(self, url: str) -> bool:
        """Check if PostgreSQL URL format is valid."""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ["postgresql", "postgresql+asyncpg"] and bool(parsed.netloc)
        except Exception:
            return False
    
    def get_database_summary(self) -> Dict[str, str]:
        """Get database configuration summary for monitoring."""
        return {
            "postgres_configured": bool(os.environ.get("DATABASE_URL")),
            "clickhouse_configured": bool(os.environ.get("CLICKHOUSE_HOST")),
            "redis_configured": bool(os.environ.get("REDIS_URL")),
            "environment": self._environment,
            "ssl_required": str(self._validation_rules.get(self._environment, {}).get("require_ssl", False))
        }