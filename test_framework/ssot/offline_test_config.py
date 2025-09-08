"""
SSOT Offline Test Configuration

This module provides configuration helpers for running tests in offline mode
when external services (databases, Redis, etc.) are not available.

Business Value: Platform/Internal - Development Velocity
Enables developers to run integration tests without requiring full infrastructure setup.

CRITICAL: Part of database connection failure remediation initiative.
"""

import logging
import os
from typing import Dict, Optional, Any

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class OfflineTestConfiguration:
    """
    Configuration manager for offline testing scenarios.
    
    This class provides fallback configurations when external services
    are unavailable, enabling integration tests to run in isolated environments.
    """
    
    def __init__(self):
        self.env = get_env()
        self.offline_mode = self._detect_offline_mode()
        
    def _detect_offline_mode(self) -> bool:
        """Detect if we should run in offline mode."""
        # Check explicit offline mode flag
        if self.env.get("OFFLINE_TEST_MODE", "").lower() == "true":
            return True
            
        # Check if no-docker flag was used (indicates offline testing)
        if self.env.get("NO_DOCKER", "").lower() == "true":
            return True
            
        # Check if we're in CI without database services
        if self.env.get("CI", "").lower() == "true" and not self.env.get("DATABASE_URL"):
            return True
            
        return False
    
    def get_database_config(self, service: str = "netra_backend") -> Dict[str, Any]:
        """
        Get database configuration for offline testing.
        
        Args:
            service: Service name (netra_backend, auth_service, etc.)
            
        Returns:
            Database configuration dictionary
        """
        if self.offline_mode:
            # Use in-memory SQLite for offline testing
            config = {
                "url": "sqlite+aiosqlite:///:memory:",
                "sync_url": "sqlite:///:memory:",
                "fallback_mode": True,
                "service": service,
                "echo": False,  # Reduce noise in offline mode
                "pool_size": 1,
                "max_overflow": 0,
                "connect_args": {"check_same_thread": False}
            }
            
            logger.info(f"Using offline SQLite configuration for {service}")
            return config
        else:
            # Use regular database configuration
            return self._get_online_database_config(service)
    
    def _get_online_database_config(self, service: str) -> Dict[str, Any]:
        """Get regular database configuration for online testing."""
        if service == "netra_backend":
            db_url = self.env.get("DATABASE_URL") or self.env.get("TEST_DATABASE_URL")
            if not db_url:
                # Build from components
                host = self.env.get("TEST_POSTGRES_HOST", "localhost")
                port = self.env.get("TEST_POSTGRES_PORT", "5432")
                user = self.env.get("TEST_POSTGRES_USER", "postgres")
                password = self.env.get("TEST_POSTGRES_PASSWORD", "postgres")
                database = self.env.get("TEST_POSTGRES_DB", "netra_test")
                db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        
        elif service == "auth_service":
            db_url = self.env.get("AUTH_DATABASE_URL")
            if not db_url:
                # Use same PostgreSQL instance, different database
                host = self.env.get("TEST_POSTGRES_HOST", "localhost")
                port = self.env.get("TEST_POSTGRES_PORT", "5432")
                user = self.env.get("TEST_POSTGRES_USER", "postgres")
                password = self.env.get("TEST_POSTGRES_PASSWORD", "postgres")
                database = self.env.get("TEST_AUTH_POSTGRES_DB", "auth_test")
                db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"
        
        else:
            # Generic service database URL
            db_url = f"postgresql+asyncpg://postgres:postgres@localhost:5432/{service}_test"
        
        return {
            "url": db_url,
            "sync_url": db_url.replace("postgresql+asyncpg://", "postgresql://") if db_url else None,
            "fallback_mode": False,
            "service": service,
            "echo": self.env.get("DATABASE_ECHO", "false").lower() == "true",
            "pool_size": 5,
            "max_overflow": 10,
        }
    
    def get_redis_config(self) -> Dict[str, Any]:
        """Get Redis configuration for offline testing."""
        if self.offline_mode:
            # Use in-memory fake Redis for offline testing
            config = {
                "host": "localhost",
                "port": 6379,
                "db": 0,
                "decode_responses": True,
                "socket_timeout": 1,
                "socket_connect_timeout": 1,
                "retry_on_timeout": False,
                "health_check_interval": 0,
                "fallback_mode": True,
                "disabled": True  # Disable Redis operations in offline mode
            }
            
            logger.info("Using disabled Redis configuration for offline mode")
            return config
        else:
            # Use regular Redis configuration
            return {
                "host": self.env.get("TEST_REDIS_HOST", "localhost"),
                "port": int(self.env.get("TEST_REDIS_PORT", "6379")),
                "db": int(self.env.get("TEST_REDIS_DB", "0")),
                "decode_responses": True,
                "socket_timeout": 30,
                "socket_connect_timeout": 10,
                "retry_on_timeout": True,
                "health_check_interval": 30,
                "fallback_mode": False,
                "disabled": False
            }
    
    def get_clickhouse_config(self) -> Dict[str, Any]:
        """Get ClickHouse configuration for offline testing."""
        if self.offline_mode:
            # Disable ClickHouse operations in offline mode
            config = {
                "host": "localhost",
                "port": 8123,
                "database": "default",
                "user": "default",
                "password": "",
                "fallback_mode": True,
                "disabled": True,  # Disable ClickHouse operations
                "use_sqlite_fallback": True
            }
            
            logger.info("Using disabled ClickHouse configuration for offline mode")
            return config
        else:
            # Use regular ClickHouse configuration
            return {
                "host": self.env.get("TEST_CLICKHOUSE_HOST", "localhost"),
                "port": int(self.env.get("TEST_CLICKHOUSE_HTTP_PORT", "8123")),
                "database": self.env.get("TEST_CLICKHOUSE_DB", "netra_test_analytics"),
                "user": self.env.get("TEST_CLICKHOUSE_USER", "default"),
                "password": self.env.get("TEST_CLICKHOUSE_PASSWORD", ""),
                "fallback_mode": False,
                "disabled": False,
                "use_sqlite_fallback": False
            }
    
    def configure_environment_for_offline_testing(self):
        """Configure environment variables for offline testing."""
        if not self.offline_mode:
            return
            
        # Set offline mode indicators
        self.env.set("OFFLINE_TEST_MODE", "true", "offline_config")
        
        # Configure database URLs to use SQLite
        self.env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "offline_config")
        self.env.set("AUTH_DATABASE_URL", "sqlite+aiosqlite:///:memory:", "offline_config")
        
        # Disable external services
        self.env.set("REDIS_ENABLED", "false", "offline_config")
        self.env.set("CLICKHOUSE_ENABLED", "false", "offline_config")
        self.env.set("DEV_MODE_DISABLE_CLICKHOUSE", "true", "offline_config")
        self.env.set("TEST_DISABLE_REDIS", "true", "offline_config")
        
        # Configure service timeouts for fast failure
        self.env.set("DATABASE_CONNECT_TIMEOUT", "3", "offline_config")
        self.env.set("REDIS_CONNECT_TIMEOUT", "1", "offline_config")
        self.env.set("CLICKHOUSE_CONNECT_TIMEOUT", "1", "offline_config")
        
        # Reduce logging noise
        self.env.set("LOG_LEVEL", "WARNING", "offline_config")
        
        logger.info("Environment configured for offline testing")
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """
        Get service-specific configuration for offline testing.
        
        Args:
            service_name: Name of the service (database, redis, clickhouse)
            
        Returns:
            Service configuration dictionary
        """
        if service_name.lower() == "database":
            return self.get_database_config()
        elif service_name.lower() == "redis":
            return self.get_redis_config()
        elif service_name.lower() == "clickhouse":
            return self.get_clickhouse_config()
        else:
            raise ValueError(f"Unknown service: {service_name}")
    
    def is_offline_mode(self) -> bool:
        """Check if we're running in offline mode."""
        return self.offline_mode
    
    def should_skip_external_service_tests(self) -> bool:
        """Check if tests requiring external services should be skipped."""
        return self.offline_mode
    
    def get_test_environment_summary(self) -> Dict[str, Any]:
        """Get summary of current test environment configuration."""
        return {
            "offline_mode": self.offline_mode,
            "database_config": self.get_database_config("netra_backend"),
            "redis_config": self.get_redis_config(),
            "clickhouse_config": self.get_clickhouse_config(),
            "skip_external_services": self.should_skip_external_service_tests(),
            "environment_vars": {
                "NO_DOCKER": self.env.get("NO_DOCKER", "false"),
                "OFFLINE_TEST_MODE": self.env.get("OFFLINE_TEST_MODE", "false"),
                "CI": self.env.get("CI", "false"),
                "DATABASE_URL": "***" if self.env.get("DATABASE_URL") else None,
                "REDIS_ENABLED": self.env.get("REDIS_ENABLED", "true"),
                "CLICKHOUSE_ENABLED": self.env.get("CLICKHOUSE_ENABLED", "true"),
            }
        }


# Global offline configuration instance
_offline_config = OfflineTestConfiguration()


def get_offline_test_config() -> OfflineTestConfiguration:
    """Get the global offline test configuration instance."""
    return _offline_config


def configure_offline_testing():
    """Configure the environment for offline testing."""
    config = get_offline_test_config()
    config.configure_environment_for_offline_testing()
    return config


def is_offline_mode() -> bool:
    """Check if we're running in offline mode."""
    return get_offline_test_config().is_offline_mode()


def get_database_config_for_service(service: str) -> Dict[str, Any]:
    """Get database configuration for a specific service."""
    return get_offline_test_config().get_database_config(service)


# Export utilities
__all__ = [
    'OfflineTestConfiguration',
    'get_offline_test_config',
    'configure_offline_testing',
    'is_offline_mode',
    'get_database_config_for_service'
]