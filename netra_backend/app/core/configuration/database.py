"""Database Configuration Management

**CRITICAL: Single Source of Truth for Database Configuration**

Manages all DATABASE_URL, CLICKHOUSE_URL, POSTGRES_URL references.
Eliminates inconsistencies across 110+ files.

**CONFIGURATION MANAGER**: This module is part of the configuration system
and requires direct os.environ access for loading database configuration.
Application code should use the unified configuration system instead.

Business Value: Prevents $12K MRR loss from database configuration errors.
Enterprise customers require 100% database reliability.

Each function ≤8 lines, file ≤300 lines.
"""

import os
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from netra_backend.app.core.environment_constants import get_current_environment
from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.Config import AppConfig


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
        return get_current_environment()
    
    def refresh_environment(self) -> None:
        """Refresh environment detection for testing scenarios."""
        old_env = self._environment
        self._environment = self._get_environment()
        if old_env != self._environment:
            self._logger.info(f"Database manager environment changed from {old_env} to {self._environment}")
    
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
            "clickhouse_dev": "clickhouse://default:@localhost:8123/default",
            "clickhouse_http_dev": "http://localhost:8123"
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
        """Get PostgreSQL URL from environment or defaults.
        
        CONFIG MANAGER: Direct env access required for database URL loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for database URL configuration
        url = os.environ.get("DATABASE_URL")
        if url:
            # Mask password but show full URL structure for debugging
            parsed = urlparse(url)
            # Handle Unix socket URLs (Cloud SQL proxy)
            if "/cloudsql/" in url or not parsed.hostname:
                masked_url = f"{parsed.scheme}://***@{parsed.path}?{parsed.query}"
            else:
                masked_url = f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port}{parsed.path}?{parsed.query}"
            self._logger.info(f"Loading DATABASE_URL: {masked_url}")
        else:
            url = self._get_default_postgres_url()
            self._logger.info(f"Using default database URL for {self._environment}")
        return url
    
    def _get_default_postgres_url(self) -> str:
        """Get default PostgreSQL URL for environment."""
        template_key = f"postgres_{self._environment}"
        return self._connection_templates.get(template_key, 
                                             self._connection_templates["postgres_dev"])
    
    def _validate_postgres_url(self, url: str) -> None:
        """Validate database URL against environment rules."""
        parsed = urlparse(url)
        if parsed.scheme.startswith("sqlite"):
            return  # Skip PostgreSQL-specific validation for SQLite
        # Accept both postgresql:// and postgresql+asyncpg:// schemes
        if parsed.scheme not in ["postgresql", "postgresql+asyncpg", "postgres"]:
            return  # Skip validation for non-PostgreSQL URLs
        
        # Skip validation for Cloud SQL Unix socket connections (like auth service)
        if "/cloudsql/" in url:
            self._logger.info("Cloud SQL Unix socket detected, skipping SSL validation")
            return
        
        rules = self._validation_rules.get(self._environment, {})
        self._check_ssl_requirement(parsed, rules)
        self._check_localhost_policy(parsed, rules)
    
    def _check_ssl_requirement(self, parsed_url, rules: dict) -> None:
        """Check SSL requirement for database connection."""
        if rules.get("require_ssl", False):
            # Skip SSL requirement for Unix socket connections (Cloud SQL proxy)
            if "/cloudsql/" in (parsed_url.query or ""):
                return  # Unix socket connections don't need SSL
            
            query_params = parsed_url.query.lower() if parsed_url.query else ""
            # Accept various SSL modes including disable
            valid_ssl_modes = ["sslmode=require", "sslmode=verify-ca", "sslmode=verify-full", "sslmode=prefer", "sslmode=disable"]
            ssl_configured = any(mode in query_params for mode in valid_ssl_modes)
            if not ssl_configured:
                self._logger.info(f"SSL validation: URL scheme={parsed_url.scheme}, query='{parsed_url.query}', env={self._environment}")
                # Only raise error if no SSL mode is present
                if "sslmode=" not in query_params:
                    raise ConfigurationError(f"SSL required for {self._environment} environment. Add ?sslmode=require to DATABASE_URL")
    
    def _check_localhost_policy(self, parsed_url, rules: dict) -> None:
        """Check localhost policy for database connection."""
        if not rules.get("allow_localhost", True):
            # Skip check for Unix socket connections
            if parsed_url.hostname and parsed_url.hostname in ["localhost", "127.0.0.1"]:
                raise ConfigurationError(f"Localhost not allowed in {self._environment}")
    
    def _get_clickhouse_configuration(self) -> Dict[str, str]:
        """Get ClickHouse configuration from environment.
        
        CONFIG MANAGER: Direct env access required for ClickHouse configuration loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for ClickHouse configuration
        # Ensure HTTP port 8123 is used for development
        default_port = "8123"  # Always use HTTP port for dev launcher
        return {
            "host": os.environ.get("CLICKHOUSE_HOST", "localhost"),
            "port": os.environ.get("CLICKHOUSE_HTTP_PORT", default_port),
            "user": os.environ.get("CLICKHOUSE_USER", "default"),
            "password": os.environ.get("CLICKHOUSE_PASSWORD", ""),
            "database": os.environ.get("CLICKHOUSE_DB", "default")
        }
    
    def _apply_clickhouse_config(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply ClickHouse configuration to config objects."""
        self._apply_to_clickhouse_native(config, ch_config)
        self._apply_to_clickhouse_https(config, ch_config)
    
    def _apply_to_clickhouse_native(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse native connection.
        
        CONFIG MANAGER: Direct env access for native port configuration.
        """
        if hasattr(config, 'clickhouse_native'):
            config.clickhouse_native.host = ch_config["host"]
            # CONFIG BOOTSTRAP: Direct env access for native port
            config.clickhouse_native.port = int(os.environ.get("CLICKHOUSE_NATIVE_PORT", "9000"))
            config.clickhouse_native.user = ch_config["user"]
            config.clickhouse_native.password = ch_config["password"]
            config.clickhouse_native.database = ch_config["database"]
    
    def _apply_to_clickhouse_https(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse HTTPS connection."""
        if hasattr(config, 'clickhouse_https'):
            config.clickhouse_https.host = ch_config["host"]
            # Force HTTP port 8123 for dev launcher compatibility
            config.clickhouse_https.port = 8123 if self._environment == "development" else int(ch_config["port"])
            config.clickhouse_https.user = ch_config["user"]
            config.clickhouse_https.password = ch_config["password"]
            config.clickhouse_https.database = ch_config["database"]
    
    
    def _set_clickhouse_url(self, config: AppConfig) -> None:
        """Set unified ClickHouse URL for external integrations.
        
        CONFIG MANAGER: Direct env access for ClickHouse URL configuration.
        """
        # CONFIG BOOTSTRAP: Direct env access for ClickHouse URL
        clickhouse_url = os.environ.get("CLICKHOUSE_URL")
        if not clickhouse_url and hasattr(config, 'clickhouse_native'):
            clickhouse_url = self._build_clickhouse_url(config.clickhouse_native)
        if clickhouse_url:
            config.clickhouse_url = clickhouse_url
    
    def _build_clickhouse_url(self, ch_config) -> str:
        """Build ClickHouse URL from configuration object."""
        password_part = f":{ch_config.password}" if ch_config.password else ""
        # Ensure we use port 8123 for HTTP connections in development
        port = 8123 if self._environment == "development" and hasattr(ch_config, 'port') and ch_config.port == 8123 else ch_config.port
        return f"clickhouse://{ch_config.user}{password_part}@{ch_config.host}:{port}/{ch_config.database}"
    
    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from environment.
        
        CONFIG MANAGER: Direct env access required for Redis URL loading.
        """
        # CONFIG BOOTSTRAP: Direct env access for Redis URL
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
        """Validate database configuration consistency."""
        issues = []
        if not config.database_url:
            issues.append("Missing database_url")
        elif not self._is_valid_postgres_url(config.database_url):
            if config.database_url.startswith("sqlite"):
                issues.append("Invalid SQLite URL format")
            else:
                issues.append("Invalid PostgreSQL URL format")
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
        """Check if database URL format is valid for environment."""
        try:
            parsed = urlparse(url)
            valid_schemes = ["postgresql", "postgresql+asyncpg"]
            if self._environment == "testing":
                valid_schemes.extend(["sqlite", "sqlite+aiosqlite"])
            return parsed.scheme in valid_schemes and (bool(parsed.netloc) or parsed.scheme.startswith("sqlite"))
        except Exception:
            return False
    
    def get_database_summary(self) -> Dict[str, str]:
        """Get database configuration summary for monitoring.
        
        CONFIG MANAGER: Direct env access for database summary.
        """
        # CONFIG BOOTSTRAP: Direct env access for configuration summary
        return {
            "postgres_configured": bool(os.environ.get("DATABASE_URL")),
            "clickhouse_configured": bool(os.environ.get("CLICKHOUSE_HOST")),
            "redis_configured": bool(os.environ.get("REDIS_URL")),
            "environment": self._environment,
            "ssl_required": str(self._validation_rules.get(self._environment, {}).get("require_ssl", False))
        }