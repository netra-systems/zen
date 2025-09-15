"""
Analytics Service Configuration

Service-independent configuration management following the unified environment pattern.
Uses service-specific IsolatedEnvironment to maintain microservice independence.

CRITICAL: This service MUST NOT import from other services (dev_launcher, netra_backend, auth_service)
"""
from typing import Optional
import logging
from pathlib import Path

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class AnalyticsConfig:
    """
    Configuration management for analytics service.
    
    Follows SPEC/unified_environment_management.xml patterns while maintaining
    complete service independence.
    """
    
    def __init__(self):
        """Initialize configuration with service-specific environment management."""
        self.env = get_env()

        # Enable isolation for development/testing - check after enabling isolation
        # so environment variables can be properly detected
        import sys
        if 'pytest' in sys.modules:
            self.env.enable_isolation()

        self._load_configuration()
        self._validate_configuration()
    
    def _is_development_environment(self) -> bool:
        """Determine if running in development environment."""
        import sys
        return (
            'pytest' in sys.modules or
            self.env.get("ENVIRONMENT", "development").lower() in ["development", "dev", "local", "test"] or
            self.env.get("ANALYTICS_DEV_MODE", "false").lower() == "true"
        )
    
    def _load_configuration(self):
        """Load all configuration values with defaults."""
        # Service Identity
        self.service_name = "analytics_service"
        self.service_version = self.env.get("ANALYTICS_SERVICE_VERSION", "1.0.0")
        self.service_port = int(self.env.get("ANALYTICS_SERVICE_PORT", "8090"))
        self.environment = self.env.get("ENVIRONMENT", "development")
        
        # Database Configuration - ClickHouse
        # CRITICAL: Use native protocol port 9000, not HTTP port 8123
        self.clickhouse_url = self.env.get(
            "CLICKHOUSE_ANALYTICS_URL",
            "clickhouse://localhost:9000/analytics"
        )
        self.clickhouse_host = self.env.get("CLICKHOUSE_HOST", "localhost")
        # FIXED: Changed from 8123 (HTTP) to 9000 (native protocol) for clickhouse-driver
        self.clickhouse_port = int(self.env.get("CLICKHOUSE_PORT", "9000"))
        self.clickhouse_database = self.env.get("CLICKHOUSE_DATABASE", "analytics")
        self.clickhouse_username = self.env.get("CLICKHOUSE_USERNAME", "default")
        self.clickhouse_password = self.env.get("CLICKHOUSE_PASSWORD", "")
        
        # Redis Configuration
        self.redis_url = self.env.get(
            "REDIS_ANALYTICS_URL",
            "redis://localhost:6379/2"
        )
        self.redis_host = self.env.get("REDIS_HOST", "localhost")
        self.redis_port = int(self.env.get("REDIS_PORT", "6379"))
        self.redis_db = int(self.env.get("REDIS_ANALYTICS_DB", "2"))
        self.redis_password = self.env.get("REDIS_PASSWORD", None)
        
        # Event Processing Configuration
        self.event_batch_size = int(self.env.get("EVENT_BATCH_SIZE", "100"))
        self.event_flush_interval_ms = int(self.env.get("EVENT_FLUSH_INTERVAL_MS", "5000"))
        self.max_events_per_user_per_minute = int(
            self.env.get("MAX_EVENTS_PER_USER_PER_MINUTE", "1000")
        )
        
        # Grafana Integration
        self.grafana_api_url = self.env.get("GRAFANA_API_URL", None)
        self.grafana_api_key = self.env.get("GRAFANA_API_KEY", None)
        
        # Security Configuration
        self.api_key = self.env.get("ANALYTICS_API_KEY", None)
        self.cors_origins = self.env.get("ANALYTICS_CORS_ORIGINS", "*").split(",")
        
        # Performance Configuration
        self.worker_count = int(self.env.get("ANALYTICS_WORKERS", "1"))
        self.connection_pool_size = int(self.env.get("CONNECTION_POOL_SIZE", "10"))
        self.query_timeout_seconds = int(self.env.get("QUERY_TIMEOUT_SECONDS", "30"))
        
        # Data Retention Configuration
        self.event_retention_days = int(self.env.get("EVENT_RETENTION_DAYS", "90"))
        self.analytics_retention_days = int(self.env.get("ANALYTICS_RETENTION_DAYS", "730"))
        
        # Logging Configuration
        self.log_level = self.env.get("ANALYTICS_LOG_LEVEL", "INFO").upper()
        self.enable_request_logging = self.env.get("ENABLE_REQUEST_LOGGING", "true").lower() == "true"
        
        logger.info(f"Analytics service configuration loaded for environment: {self.environment}")
    
    def _validate_configuration(self):
        """Validate critical configuration values."""
        errors = []
        warnings = []
        
        # Port validation
        if not (1024 <= self.service_port <= 65535):
            errors.append(f"Invalid service port: {self.service_port}")
        
        # Database URL validation in production/staging
        if self.environment in ["staging", "production"]:
            if not self.clickhouse_url:
                errors.append("ClickHouse URL is required in staging/production")
            elif "localhost" in self.clickhouse_url:
                errors.append("ClickHouse URL cannot use localhost in staging/production")
            
            if not self.redis_url:
                errors.append("Redis URL is required in staging/production")
            elif "localhost" in self.redis_url:
                errors.append("Redis URL cannot use localhost in staging/production")
        
        # Rate limiting validation
        if self.max_events_per_user_per_minute <= 0:
            errors.append("Max events per user per minute must be positive")
        
        # Batch size validation
        if self.event_batch_size <= 0 or self.event_batch_size > 1000:
            errors.append("Event batch size must be between 1 and 1000")
        
        # Environment-specific validation
        if self.environment in ["staging", "production"]:
            if not self.api_key:
                warnings.append("API key not configured for staging/production")
            
            if not self.grafana_api_key and self.grafana_api_url:
                warnings.append("Grafana API key not configured but URL is set")
        
        # Log validation results
        if errors:
            error_msg = f"Configuration validation failed: {'; '.join(errors)}"
            logger.error(error_msg)
            if self.environment in ["staging", "production"]:
                raise ValueError(error_msg)
            else:
                logger.warning(f"Continuing with invalid config in {self.environment} mode")
        
        if warnings:
            logger.warning(f"Configuration warnings: {'; '.join(warnings)}")
        else:
            logger.info("Configuration validation passed")
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.environment.lower() == "staging"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() in ["development", "dev", "local"]
    
    def get_clickhouse_connection_params(self) -> dict:
        """Get ClickHouse connection parameters."""
        return {
            "host": self.clickhouse_host,
            "port": self.clickhouse_port,
            "database": self.clickhouse_database,
            "user": self.clickhouse_username,
            "password": self.clickhouse_password,
        }
    
    def get_redis_connection_params(self) -> dict:
        """Get Redis connection parameters."""
        params = {
            "host": self.redis_host,
            "port": self.redis_port,
            "db": self.redis_db,
        }
        
        if self.redis_password:
            params["password"] = self.redis_password
        
        return params
    
    def mask_sensitive_config(self) -> dict:
        """Get configuration dict with sensitive values masked for logging."""
        config = {
            "service_name": self.service_name,
            "service_version": self.service_version,
            "service_port": self.service_port,
            "environment": self.environment,
            "clickhouse_host": self.clickhouse_host,
            "clickhouse_port": self.clickhouse_port,
            "clickhouse_database": self.clickhouse_database,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "event_batch_size": self.event_batch_size,
            "max_events_per_user_per_minute": self.max_events_per_user_per_minute,
        }
        
        # Mask sensitive values - always include keys for consistency
        config["clickhouse_password"] = "***masked***" if self.clickhouse_password else "***masked***"
        if self.redis_password:
            config["redis_password"] = "***masked***"
        if self.api_key:
            config["api_key"] = "***masked***"
        if self.grafana_api_key:
            config["grafana_api_key"] = "***masked***"
        
        return config


# Global configuration instance
_config: Optional[AnalyticsConfig] = None


def get_config() -> AnalyticsConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AnalyticsConfig()
    return _config


# Convenience functions for common config access
def get_service_port() -> int:
    """Get the service port."""
    return get_config().service_port


def get_environment() -> str:
    """Get the current environment."""
    return get_config().environment


def is_production() -> bool:
    """Check if running in production."""
    return get_config().is_production