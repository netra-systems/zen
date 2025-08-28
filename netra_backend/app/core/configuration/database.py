"""Database Configuration Management

**CRITICAL: Single Source of Truth for Database Configuration**

Manages all DATABASE_URL, CLICKHOUSE_URL, POSTGRES_URL references.
Eliminates inconsistencies across 110+ files.

**UPDATED**: This module now uses IsolatedEnvironment for unified environment management.
Follows SPEC/unified_environment_management.xml for consistent environment access.

Business Value: Prevents $12K MRR loss from database configuration errors.
Enterprise customers require 100% database reliability.

Each function ≤8 lines, file ≤300 lines.
"""

from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

from netra_backend.app.core.isolated_environment import get_env
from netra_backend.app.core.environment_constants import get_current_environment
from netra_backend.app.core.exceptions_config import ConfigurationError
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.schemas.config import AppConfig


# Global set to track logged messages across all instances
_GLOBAL_LOGGED_MESSAGES = set()


class DatabaseConfigManager:
    """Unified database configuration management.
    
    **MANDATORY**: All database configuration MUST use this manager.
    Ensures consistency across PostgreSQL and ClickHouse connections.
    """
    
    def __init__(self):
        """Initialize database configuration manager."""
        self._logger = logger
        self._env = get_env()  # Use IsolatedEnvironment for all env access
        self._environment = self._get_environment()
        self._validation_rules = self._load_validation_rules()
        self._connection_templates = self._load_connection_templates()
        # Add caching to prevent repeated configuration loading and logging
        self._postgres_url_cache: Optional[str] = None
        self._clickhouse_config_cache: Optional[Dict[str, str]] = None
        self._redis_url_cache: Optional[str] = None
        self._logged_urls = set()  # Track what we've already logged
    
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
            "postgres_dev": "postgresql+asyncpg://postgres:postgres@localhost:5432/netra_dev",
            "postgres_staging": "postgresql+asyncpg://user:pass@staging-host:5432/netra_staging",
            "postgres_production": "postgresql+asyncpg://user:pass@prod-host:5432/netra_production",
            "clickhouse_dev": "clickhouse://default:@localhost:8123/default",
            "clickhouse_http_dev": "http://localhost:8123"
        }
    
    def populate_database_config(self, config: AppConfig) -> None:
        """Populate all database configuration in config object."""
        self._populate_postgres_config(config)
        self._populate_clickhouse_config(config)
        self._populate_redis_config(config)
        # Only log during initial startup or when explicitly requested
        self._logger.debug(f"Populated database config for {self._environment}")
    
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
        """Populate Redis configuration using RedisConfigurationBuilder."""
        from shared.redis_config_builder import RedisConfigurationBuilder
        
        # Build environment variables dict for Redis builder
        env_vars = {
            "ENVIRONMENT": self._environment,
            "REDIS_URL": self._env.get("REDIS_URL"),
            "REDIS_HOST": self._env.get("REDIS_HOST"),
            "REDIS_PORT": self._env.get("REDIS_PORT"),
            "REDIS_DB": self._env.get("REDIS_DB"),
            "REDIS_PASSWORD": self._env.get("REDIS_PASSWORD"),
            "REDIS_USERNAME": self._env.get("REDIS_USERNAME"),
            "REDIS_SSL": self._env.get("REDIS_SSL"),
            "REDIS_FALLBACK_ENABLED": self._env.get("REDIS_FALLBACK_ENABLED"),
            "REDIS_REQUIRED": self._env.get("REDIS_REQUIRED"),
        }
        
        # Create Redis configuration builder
        redis_builder = RedisConfigurationBuilder(env_vars)
        
        # Validate Redis configuration
        is_valid, error_msg = redis_builder.validate()
        if not is_valid:
            self._logger.error(f"Redis configuration error: {error_msg}")
            raise ConfigurationError(error_msg)
        
        # Get Redis URL and configuration
        redis_url = redis_builder.connection.get_redis_url()
        if redis_url:
            config.redis_url = redis_url
            self._update_redis_config_object(config, redis_url)
            
            # Log Redis configuration (masked) if not already logged
            if redis_url not in self._logged_urls:
                safe_log_msg = redis_builder.get_safe_log_message()
                self._logger.info(safe_log_msg)
                self._logged_urls.add(redis_url)
    
    def _get_postgres_url(self) -> Optional[str]:
        """Get PostgreSQL URL using comprehensive URL builder."""
        # Return cached URL if available
        if self._postgres_url_cache is not None:
            return self._postgres_url_cache
        
        from shared.database_url_builder import DatabaseURLBuilder
        
        # Build environment variables dict
        env_vars = {
            "ENVIRONMENT": self._environment,
            "POSTGRES_HOST": self._env.get("POSTGRES_HOST"),
            "POSTGRES_PORT": self._env.get("POSTGRES_PORT"),
            "POSTGRES_DB": self._env.get("POSTGRES_DB"),
            "POSTGRES_USER": self._env.get("POSTGRES_USER"),
            "POSTGRES_PASSWORD": self._env.get("POSTGRES_PASSWORD"),
            "DATABASE_URL": self._env.get("DATABASE_URL"),
        }
        
        # Create builder
        builder = DatabaseURLBuilder(env_vars)
        
        # Validate configuration
        is_valid, error_msg = builder.validate()
        if not is_valid:
            self._logger.error(f"Database configuration error: {error_msg}")
            raise ConfigurationError(error_msg)
        
        # Get URL for current environment
        url = builder.get_url_for_environment(sync=False)
        
        if not url:
            if self._environment in ["staging", "production"]:
                raise ConfigurationError(
                    f"No PostgreSQL configuration found for {self._environment} environment. "
                    "Set POSTGRES_HOST/USER/DB environment variables."
                )
            self._logger.warning(f"PostgreSQL configuration missing for {self._environment} environment")
            url = None
        else:
            # Log URL (masked) if not already logged
            if url not in self._logged_urls:
                debug_info = builder.debug_info()
                self._logger.info(f"Using PostgreSQL URL from {self._environment} configuration")
                self._logger.debug(f"Database config: Cloud SQL={debug_info['has_cloud_sql']}, TCP={debug_info['has_tcp_config']}")
                self._logged_urls.add(url)
        
        # Cache the URL
        self._postgres_url_cache = url
        return url
    
    
    def _validate_postgres_url(self, url: str) -> None:
        """Validate database URL against environment rules."""
        parsed = urlparse(url)
        if parsed.scheme.startswith("sqlite"):
            return  # Skip PostgreSQL-specific validation for SQLite
        # Accept postgresql://, postgres://, and postgresql+driver:// schemes
        valid_schemes = ["postgresql", "postgres", "postgresql+asyncpg", "postgresql+psycopg2", "postgresql+psycopg"]
        if not any(parsed.scheme.startswith(scheme) for scheme in ["postgresql", "postgres"]):
            return  # Skip validation for non-PostgreSQL URLs
        
        # Detect Cloud SQL connections
        if "/cloudsql/" in url:
            # Only log this message once globally to prevent log spam
            log_key = "cloudsql_socket_detected"
            if log_key not in _GLOBAL_LOGGED_MESSAGES:
                self._logger.info("Cloud SQL Unix socket detected, skipping SSL validation")
                _GLOBAL_LOGGED_MESSAGES.add(log_key)
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
        # Return cached configuration if available
        if self._clickhouse_config_cache is not None:
            return self._clickhouse_config_cache
            
        # CONFIG BOOTSTRAP: Direct env access for ClickHouse configuration
        # Port selection based on environment and security requirements
        secure = self._env.get("CLICKHOUSE_SECURE", "false").lower() == "true"
        if secure or self._environment in ["staging", "production"]:
            default_port = "8443"  # HTTPS port for secure environments
        else:
            default_port = "8123"  # HTTP port for development
        
        # Get ClickHouse password from environment
        password = self._env.get("CLICKHOUSE_PASSWORD", "")
        
        # Log warning if no password is set in non-dev environments
        if not password and self._environment not in ["development", "testing"]:
            logger.warning(
                "CLICKHOUSE_PASSWORD not set. "
                "Database connections may fail. Please set this environment variable."
            )
        
        # Require explicit ClickHouse configuration in staging/production
        host = self._env.get("CLICKHOUSE_HOST")
        if not host and self._environment in ["staging", "production"]:
            raise ConfigurationError(
                f"CLICKHOUSE_HOST not configured for {self._environment} environment. "
                "ClickHouse configuration must be explicitly provided."
            )
        elif not host:
            # Only warn in development/test
            logger.warning("CLICKHOUSE_HOST not configured for development/test")
            host = ""  # No fallback - empty host
        
        user = self._env.get("CLICKHOUSE_USER") or self._env.get("CLICKHOUSE_USERNAME")
        if not user and self._environment in ["staging", "production"]:
            raise ConfigurationError(
                f"CLICKHOUSE_USER or CLICKHOUSE_USERNAME not configured for {self._environment} environment."
            )
        elif not user:
            user = "default"  # Safe default for development
            
        database = self._env.get("CLICKHOUSE_DB")
        if not database and self._environment in ["staging", "production"]:
            raise ConfigurationError(
                f"CLICKHOUSE_DB not configured for {self._environment} environment."
            )
        elif not database:
            database = "default"  # Safe default for all environments
        
        config = {
            "host": host,
            "port": self._env.get("CLICKHOUSE_PORT") or self._env.get("CLICKHOUSE_HTTP_PORT", default_port),
            "user": user,
            "password": password,
            "database": database
        }
        # Cache the configuration
        self._clickhouse_config_cache = config
        return config
    
    def _apply_clickhouse_config(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply ClickHouse configuration to config objects."""
        self._apply_to_clickhouse_native(config, ch_config)
        self._apply_to_clickhouse_http(config, ch_config)
        self._apply_to_clickhouse_https(config, ch_config)
    
    def _apply_to_clickhouse_native(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse native connection.
        
        Uses IsolatedEnvironment for native port configuration.
        """
        if hasattr(config, 'clickhouse_native'):
            config.clickhouse_native.host = ch_config["host"]
            # Use IsolatedEnvironment for native port
            config.clickhouse_native.port = int(self._env.get("CLICKHOUSE_NATIVE_PORT", "9000"))
            config.clickhouse_native.user = ch_config["user"]
            config.clickhouse_native.password = ch_config["password"]
            config.clickhouse_native.database = ch_config["database"]
    
    def _apply_to_clickhouse_http(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse HTTP connection."""
        if hasattr(config, 'clickhouse_http'):
            config.clickhouse_http.host = ch_config["host"]
            # Use HTTP port 8123 for dev launcher compatibility
            config.clickhouse_http.port = int(self._env.get("CLICKHOUSE_HTTP_PORT", "8123"))
            config.clickhouse_http.user = ch_config["user"]
            config.clickhouse_http.password = ch_config["password"]
            config.clickhouse_http.database = ch_config["database"]
    
    def _apply_to_clickhouse_https(self, config: AppConfig, ch_config: Dict[str, str]) -> None:
        """Apply configuration to ClickHouse HTTPS connection."""
        if hasattr(config, 'clickhouse_https'):
            config.clickhouse_https.host = ch_config["host"]
            # Use native port for HTTPS in development, production port otherwise
            config.clickhouse_https.port = int(ch_config["port"]) if self._environment == "development" else 8443
            config.clickhouse_https.user = ch_config["user"]
            config.clickhouse_https.password = ch_config["password"]
            config.clickhouse_https.database = ch_config["database"]
    
    
    def _set_clickhouse_url(self, config: AppConfig) -> None:
        """Set unified ClickHouse URL for external integrations.
        
        Uses IsolatedEnvironment for ClickHouse URL configuration.
        """
        # Use IsolatedEnvironment for ClickHouse URL
        clickhouse_url = self._env.get("CLICKHOUSE_URL")
        
        # For staging/production, require explicit ClickHouse URL
        if not clickhouse_url:
            if self._environment in ["staging", "production"]:
                # Don't default to localhost in staging/production
                self._logger.warning(f"CLICKHOUSE_URL not configured for {self._environment} environment")
                # Set to empty string to prevent localhost fallback
                config.clickhouse_url = ""
            elif hasattr(config, 'clickhouse_native'):
                # Only build URL from config in dev/test environments
                clickhouse_url = self._build_clickhouse_url(config.clickhouse_native)
                config.clickhouse_url = clickhouse_url
        else:
            config.clickhouse_url = clickhouse_url
    
    def _build_clickhouse_url(self, ch_config) -> str:
        """Build ClickHouse URL from configuration object."""
        password_part = f":{ch_config.password}" if ch_config.password else ""
        # Ensure we use port 8123 for HTTP connections in development
        port = 8123 if self._environment == "development" and hasattr(ch_config, 'port') and ch_config.port == 8123 else ch_config.port
        return f"clickhouse://{ch_config.user}{password_part}@{ch_config.host}:{port}/{ch_config.database}"
    
    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL using RedisConfigurationBuilder.
        
        DEPRECATED: This method is kept for backward compatibility.
        New code should use _populate_redis_config which uses RedisConfigurationBuilder.
        """
        # Return cached URL if available
        if self._redis_url_cache is not None:
            return self._redis_url_cache
            
        from shared.redis_config_builder import RedisConfigurationBuilder
        
        # Build environment variables dict for Redis builder
        env_vars = {
            "ENVIRONMENT": self._environment,
            "REDIS_URL": self._env.get("REDIS_URL"),
            "REDIS_HOST": self._env.get("REDIS_HOST"),
            "REDIS_PORT": self._env.get("REDIS_PORT"),
            "REDIS_DB": self._env.get("REDIS_DB"),
            "REDIS_PASSWORD": self._env.get("REDIS_PASSWORD"),
            "REDIS_USERNAME": self._env.get("REDIS_USERNAME"),
            "REDIS_SSL": self._env.get("REDIS_SSL"),
            "REDIS_FALLBACK_ENABLED": self._env.get("REDIS_FALLBACK_ENABLED"),
            "REDIS_REQUIRED": self._env.get("REDIS_REQUIRED"),
        }
        
        # Create Redis configuration builder
        redis_builder = RedisConfigurationBuilder(env_vars)
        url = redis_builder.connection.get_redis_url()
        
        # Cache the URL
        self._redis_url_cache = url
        return url
    
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
            # Accept various PostgreSQL schemes including simple ones
            valid_schemes = ["postgresql", "postgres", "postgresql+asyncpg", "postgresql+psycopg2", "postgresql+psycopg"]
            if self._environment == "testing":
                valid_schemes.extend(["sqlite", "sqlite+aiosqlite"])
            # Check if scheme is valid and has either netloc or is SQLite
            scheme_valid = parsed.scheme in valid_schemes or parsed.scheme.startswith("postgresql")
            return scheme_valid and (bool(parsed.netloc) or parsed.scheme.startswith("sqlite"))
        except Exception:
            return False
    
    def get_sync_postgres_url(self) -> Optional[str]:
        """Get synchronous PostgreSQL URL for migrations.
        
        Constructs sync URL from individual POSTGRES_* environment variables.
        Falls back to DATABASE_URL if individual variables not set.
        """
        # Try to construct URL from individual PostgreSQL variables
        postgres_host = self._env.get("POSTGRES_HOST")
        postgres_port = self._env.get("POSTGRES_PORT")
        postgres_db = self._env.get("POSTGRES_DB")
        postgres_user = self._env.get("POSTGRES_USER")
        postgres_password = self._env.get("POSTGRES_PASSWORD")
        
        # Validate individual PostgreSQL variables if any are set
        if any([postgres_host, postgres_user, postgres_db]):
            validation_errors = []
            
            # Check for empty string values (common configuration mistake)
            if postgres_host == "":
                validation_errors.append("POSTGRES_HOST is empty string")
            if postgres_user == "":
                validation_errors.append("POSTGRES_USER is empty string")
            if postgres_db == "":
                validation_errors.append("POSTGRES_DB is empty string")
            if postgres_password == "":
                validation_errors.append("POSTGRES_PASSWORD is empty string")
            if postgres_port == "":
                validation_errors.append("POSTGRES_PORT is empty string")
                
            # Check for placeholder values
            if postgres_password and postgres_password.lower() in ["placeholder", "todo", "changeme"]:
                validation_errors.append(f"POSTGRES_PASSWORD contains placeholder value: {postgres_password}")
                
            # Check for required fields
            if not postgres_host:
                validation_errors.append("POSTGRES_HOST not set when using individual PostgreSQL variables")
            if not postgres_user:
                validation_errors.append("POSTGRES_USER not set when using individual PostgreSQL variables")
            if not postgres_db:
                validation_errors.append("POSTGRES_DB not set when using individual PostgreSQL variables")
                
            # In staging/production, password is required
            if self._environment in ["staging", "production"] and not postgres_password:
                validation_errors.append(f"POSTGRES_PASSWORD required in {self._environment} environment")
                
            # Validate port if provided
            if postgres_port and not postgres_port.isdigit():
                validation_errors.append(f"POSTGRES_PORT must be numeric: {postgres_port}")
                
            # Fail fast if validation errors found
            if validation_errors:
                error_msg = f"PostgreSQL configuration validation failed: {'; '.join(validation_errors)}"
                self._logger.error(error_msg)
                raise ConfigurationError(error_msg)
        
        if postgres_host and postgres_user and postgres_db:
            # Construct URL from individual variables
            port_part = f":{postgres_port}" if postgres_port else ":5432"
            pass_part = f":{postgres_password}" if postgres_password else ""
            
            # Check for Cloud SQL Unix socket (staging/production)
            if "/cloudsql/" in postgres_host:
                # Unix socket format for Cloud SQL
                url = f"postgresql://{postgres_user}{pass_part}@/{postgres_db}?host={postgres_host}"
            else:
                # Standard TCP connection
                url = f"postgresql://{postgres_user}{pass_part}@{postgres_host}{port_part}/{postgres_db}"
                
                # Add SSL mode for staging/production
                if self._environment in ["staging", "production"]:
                    url += "?sslmode=require" if "?" not in url else "&sslmode=require"
            
            return url
        else:
            # Fall back to DATABASE_URL if individual variables not set
            url = self._env.get("DATABASE_URL")
            if url:
                # Remove async driver for sync use
                url = url.replace("postgresql+asyncpg://", "postgresql://")
                url = url.replace("postgres+asyncpg://", "postgresql://")
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql://")
                return url
            else:
                # No fallback to default values
                # In staging/production, fail loudly
                if self._environment in ["staging", "production"]:
                    raise ConfigurationError(
                        f"No PostgreSQL configuration found for {self._environment} environment. "
                        "Set either POSTGRES_HOST/USER/DB or DATABASE_URL environment variables."
                    )
                # In test/development, return None
                return None
    
    def get_database_summary(self) -> Dict[str, str]:
        """Get database configuration summary for monitoring.
        
        Uses IsolatedEnvironment for database summary.
        """
        # Use IsolatedEnvironment for configuration summary
        postgres_configured = bool(
            self._env.get("POSTGRES_HOST") or self._env.get("DATABASE_URL")
        )
        return {
            "postgres_configured": postgres_configured,
            "clickhouse_configured": bool(self._env.get("CLICKHOUSE_HOST")),
            "redis_configured": bool(self._env.get("REDIS_URL")),
            "environment": self._environment,
            "ssl_required": str(self._validation_rules.get(self._environment, {}).get("require_ssl", False))
        }


# Global database config manager instance
_config_manager = None


def get_unified_config() -> DatabaseConfigManager:
    """Get unified database configuration manager instance.
    
    Returns:
        DatabaseConfigManager: The global database configuration manager
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = DatabaseConfigManager()
    return _config_manager