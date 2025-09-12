"""Database Configuration Validation

**CRITICAL: Enterprise-Grade Database Validation**

Database-specific validation helpers for configuration validation.
Business Value: Prevents database connection failures that impact operations.

Each function  <= 8 lines, file  <= 300 lines.
"""

from typing import List
from urllib.parse import urlparse

from netra_backend.app.schemas.config import AppConfig


class DatabaseValidator:
    """Database configuration validation helpers."""
    
    def __init__(self, validation_rules: dict, environment: str):
        """Initialize database validator."""
        self._validation_rules = validation_rules
        self._environment = environment
    
    def validate_database_config(self, config: AppConfig) -> List[str]:
        """Validate database configuration."""
        errors = []
        self._check_postgres_config(config, errors)
        errors.extend(self._validate_clickhouse_config(config))
        errors.extend(self._validate_redis_config(config))
        return errors
    
    def _check_postgres_config(self, config: AppConfig, errors: List[str]) -> None:
        """Check PostgreSQL configuration."""
        if not config.database_url:
            errors.append("database_url is required")
        else:
            errors.extend(self._validate_postgres_url(config.database_url))
    
    def _validate_postgres_url(self, url: str) -> List[str]:
        """Validate database URL format and requirements."""
        try:
            parsed = urlparse(url)
            return self._check_url_components(parsed)
        except Exception:
            return ["Invalid database URL format"]
    
    def _check_url_components(self, parsed_url) -> List[str]:
        """Check all URL components for validation."""
        errors = self._validate_url_scheme(parsed_url)
        errors.extend(self._validate_url_host(parsed_url))
        errors.extend(self._validate_url_security(parsed_url))
        return errors
    
    def _validate_url_scheme(self, parsed_url) -> List[str]:
        """Validate database URL scheme."""
        valid_schemes = self._get_valid_db_schemes()
        if parsed_url.scheme not in valid_schemes:
            return self._handle_invalid_scheme(parsed_url.scheme)
        return []
    
    def _get_valid_db_schemes(self) -> List[str]:
        """Get valid database schemes for current environment."""
        schemes = ["postgresql", "postgresql+asyncpg"]
        if self._environment == "testing":
            schemes.extend(["sqlite", "sqlite+aiosqlite"])
        return schemes
    
    def _handle_invalid_scheme(self, scheme: str) -> List[str]:
        """Handle invalid database scheme."""
        if scheme.startswith("sqlite") and self._environment != "testing":
            return ["SQLite URLs only allowed in testing environment"]
        return ["Invalid database URL scheme"]
    
    def _validate_url_host(self, parsed_url) -> List[str]:
        """Validate database URL host information."""
        if not parsed_url.scheme.startswith("sqlite") and not parsed_url.netloc:
            return ["Database URL missing host information"]
        return []
    
    def _validate_url_security(self, parsed_url) -> List[str]:
        """Validate database URL security requirements."""
        if not parsed_url.scheme.startswith("sqlite"):
            return self._check_database_security_requirements(parsed_url)
        return []
    
    def _check_database_security_requirements(self, parsed_url) -> List[str]:
        """Check database URL security requirements."""
        errors = self._check_ssl_requirement(parsed_url)
        errors.extend(self._check_localhost_restriction(parsed_url))
        return errors
    
    def _check_ssl_requirement(self, parsed_url) -> List[str]:
        """Check SSL requirement for database connection."""
        rules = self._validation_rules.get(self._environment, {})
        if rules.get("require_ssl", False):
            # Skip SSL requirement for Unix socket connections (Cloud SQL proxy)
            if "/cloudsql/" in (parsed_url.query or ""):
                return []  # Unix socket connections don't need SSL
            if "sslmode" not in (parsed_url.query or ""):
                return ["SSL connection required for database"]
        return []
    
    def _check_localhost_restriction(self, parsed_url) -> List[str]:
        """Check localhost restriction for database connection."""
        rules = self._validation_rules.get(self._environment, {})
        if not rules.get("allow_localhost", True):
            if parsed_url.hostname in ["localhost", "127.0.0.1"]:
                return ["Localhost database connections not allowed"]
        return []
    
    def _validate_clickhouse_config(self, config: AppConfig) -> List[str]:
        """Validate ClickHouse configuration."""
        errors = []
        self._check_clickhouse_native(config, errors)
        self._check_clickhouse_consistency(config, errors)
        return errors
    
    def _check_clickhouse_native(self, config: AppConfig, errors: List[str]) -> None:
        """Check ClickHouse native configuration."""
        if not hasattr(config, 'clickhouse_native'):
            errors.append("ClickHouse native configuration missing")
        else:
            errors.extend(self._validate_clickhouse_connection(config.clickhouse_native))
    
    def _check_clickhouse_consistency(self, config: AppConfig, errors: List[str]) -> None:
        """Check ClickHouse configuration consistency."""
        if hasattr(config, 'clickhouse_https') and hasattr(config, 'clickhouse_native'):
            errors.extend(self._validate_clickhouse_consistency(config))
    
    def _validate_clickhouse_connection(self, ch_config) -> List[str]:
        """Validate ClickHouse connection configuration."""
        errors = []
        errors.extend(self._check_clickhouse_host(ch_config))
        errors.extend(self._check_clickhouse_port(ch_config))
        errors.extend(self._check_clickhouse_user(ch_config))
        return errors
    
    def _check_clickhouse_host(self, ch_config) -> List[str]:
        """Check ClickHouse host configuration."""
        if not ch_config.host:
            return ["ClickHouse host is required"]
        return []
    
    def _check_clickhouse_port(self, ch_config) -> List[str]:
        """Check ClickHouse port configuration."""
        if not ch_config.port or ch_config.port <= 0:
            return ["Valid ClickHouse port is required"]
        return []
    
    def _check_clickhouse_user(self, ch_config) -> List[str]:
        """Check ClickHouse user configuration."""
        if not ch_config.user:
            return ["ClickHouse user is required"]
        return []
    
    def _validate_clickhouse_consistency(self, config: AppConfig) -> List[str]:
        """Validate consistency between ClickHouse configurations."""
        errors = self._check_clickhouse_host_consistency(config)
        errors.extend(self._check_clickhouse_user_consistency(config))
        return errors
    
    def _check_clickhouse_host_consistency(self, config: AppConfig) -> List[str]:
        """Check ClickHouse host consistency."""
        if config.clickhouse_native.host != config.clickhouse_https.host:
            return ["ClickHouse native and HTTPS hosts are inconsistent"]
        return []
    
    def _check_clickhouse_user_consistency(self, config: AppConfig) -> List[str]:
        """Check ClickHouse user consistency."""
        if config.clickhouse_native.user != config.clickhouse_https.user:
            return ["ClickHouse native and HTTPS users are inconsistent"]
        return []
    
    def _validate_redis_config(self, config: AppConfig) -> List[str]:
        """Validate Redis configuration."""
        if not self._has_redis_config(config):
            return []
        return self._check_redis_connection_params(config.redis)
    
    def _has_redis_config(self, config: AppConfig) -> bool:
        """Check if Redis configuration exists."""
        return hasattr(config, 'redis') and config.redis
    
    def _check_redis_connection_params(self, redis_config) -> List[str]:
        """Check Redis connection parameters."""
        errors = []
        errors.extend(self._validate_redis_host(redis_config))
        errors.extend(self._validate_redis_port(redis_config))
        return errors
    
    def _validate_redis_host(self, redis_config) -> List[str]:
        """Validate Redis host configuration."""
        if not redis_config.host:
            return ["Redis host is required"]
        return []
    
    def _validate_redis_port(self, redis_config) -> List[str]:
        """Validate Redis port configuration."""
        if not redis_config.port or redis_config.port <= 0:
            return ["Valid Redis port is required"]
        return []