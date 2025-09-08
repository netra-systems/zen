"""SSOT Database Configuration for Test Environments.

This module provides standardized database configuration patterns for all
services in the Netra platform. It implements the SSOT database patterns
defined in the Test Configuration Standardization Report.

Usage:
    from test_framework.ssot.database_config import setup_database_config
    
    # Setup standardized database configuration for a service
    config = setup_database_config("backend", test_mode=True)
    
    # Get standardized database URL for a service
    db_url = get_database_url("backend", test_mode=True)

Key Features:
- Standardized database configuration across all services
- Port isolation to prevent conflicts between services
- Docker vs non-Docker mode support
- Test vs production configuration patterns
- Automatic URL building with validation
"""

import logging
from typing import Dict, Optional, Any
from urllib.parse import urlparse

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

class DatabaseConfigManager:
    """SSOT Database Configuration Manager for all services."""
    
    # SSOT: Service-specific database configurations
    SERVICE_DB_CONFIGS = {
        "backend": {
            "test_port": 5434,
            "docker_service": "test-postgres",
            "database": "backend_test_db",
            "user": "test_backend",
            "password": "test_backend_pass",
            "pool_size": 5,
            "max_overflow": 10
        },
        "auth": {
            "test_port": 5435,
            "docker_service": "auth-test-postgres",
            "database": "auth_test_db", 
            "user": "test_auth",
            "password": "test_auth_pass",
            "pool_size": 3,
            "max_overflow": 5
        },
        "analytics": {
            "test_port": 5436,
            "docker_service": "analytics-test-postgres", 
            "database": "analytics_test_db",
            "user": "test_analytics",
            "password": "test_analytics_pass",
            "pool_size": 3,
            "max_overflow": 5
        },
        "test_framework": {
            "test_port": 5433,
            "docker_service": "framework-test-postgres",
            "database": "framework_test_db",
            "user": "test_framework",
            "password": "test_framework_pass", 
            "pool_size": 2,
            "max_overflow": 2
        }
    }
    
    # SSOT: Default configuration patterns
    DEFAULT_CONFIG = {
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "database": "netra_dev",
        "pool_size": 5,
        "max_overflow": 10,
        "pool_timeout": 30,
        "pool_recycle": 3600
    }
    
    def __init__(self):
        self.env = get_env()
        
    def setup_database_config(self, service_name: str, test_mode: bool = True, use_docker: bool = None) -> Dict[str, Any]:
        """Setup standardized database configuration for a service.
        
        Args:
            service_name: Name of the service (backend, auth, analytics, test_framework)
            test_mode: Whether to use test configuration (default: True)
            use_docker: Whether to use Docker service names (auto-detected if None)
            
        Returns:
            Dictionary containing database configuration
        """
        # Get service-specific configuration
        if service_name not in self.SERVICE_DB_CONFIGS:
            logger.warning(f"Unknown service '{service_name}', using test_framework defaults")
            service_name = "test_framework"
        
        service_config = self.SERVICE_DB_CONFIGS[service_name]
        
        # Auto-detect Docker mode if not specified
        if use_docker is None:
            use_docker = self._detect_docker_mode()
        
        if test_mode:
            config = self._build_test_config(service_name, service_config, use_docker)
        else:
            config = self._build_production_config(service_name, service_config)
        
        # Set environment variables for the service
        self._set_environment_variables(service_name, config)
        
        logger.info(f"Database configuration setup for {service_name}: {config['host']}:{config['port']}/{config['database']}")
        return config
    
    def get_database_url(self, service_name: str, test_mode: bool = True, use_docker: bool = None) -> str:
        """Get standardized database URL for a service.
        
        Args:
            service_name: Name of the service
            test_mode: Whether to use test configuration
            use_docker: Whether to use Docker service names
            
        Returns:
            Database URL string
        """
        config = self.setup_database_config(service_name, test_mode, use_docker)
        return self._build_database_url(config)
    
    def validate_database_config(self, service_name: str) -> Dict[str, Any]:
        """Validate current database configuration for a service.
        
        Args:
            service_name: Name of the service to validate
            
        Returns:
            Dictionary with validation results
        """
        config = self._get_current_config(service_name)
        issues = []
        
        # Check required fields
        required_fields = ["host", "port", "user", "database"]
        for field in required_fields:
            if not config.get(field):
                issues.append(f"Missing required field: {field}")
        
        # Validate port
        try:
            port = int(config.get("port", 0))
            if port <= 0 or port > 65535:
                issues.append(f"Invalid port: {port}")
        except (ValueError, TypeError):
            issues.append(f"Invalid port format: {config.get('port')}")
        
        # Check for port conflicts
        if service_name in self.SERVICE_DB_CONFIGS:
            expected_port = self.SERVICE_DB_CONFIGS[service_name]["test_port"]
            actual_port = int(config.get("port", 0))
            if actual_port != expected_port:
                issues.append(f"Port mismatch: expected {expected_port}, got {actual_port}")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": config
        }
    
    def _build_test_config(self, service_name: str, service_config: Dict[str, Any], use_docker: bool) -> Dict[str, Any]:
        """Build test configuration for a service."""
        config = self.DEFAULT_CONFIG.copy()
        
        if use_docker:
            # Docker mode - use service names
            config.update({
                "host": service_config["docker_service"],
                "port": 5432,  # Internal PostgreSQL port in Docker
                "user": service_config["user"],
                "password": service_config["password"],
                "database": service_config["database"],
                "pool_size": service_config.get("pool_size", 3),
                "max_overflow": service_config.get("max_overflow", 5)
            })
        else:
            # Local mode - use localhost with specific ports
            config.update({
                "host": "localhost",
                "port": service_config["test_port"],
                "user": service_config["user"],
                "password": service_config["password"],
                "database": service_config["database"],
                "pool_size": service_config.get("pool_size", 3),
                "max_overflow": service_config.get("max_overflow", 5)
            })
        
        # Add test-specific optimizations
        config.update({
            "pool_timeout": 10,  # Faster timeout for tests
            "pool_recycle": 300,  # Shorter recycle for tests
            "echo": False,  # Disable SQL logging in tests
            "isolation_level": "AUTOCOMMIT"  # Faster for test operations
        })
        
        return config
    
    def _build_production_config(self, service_name: str, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build production configuration for a service."""
        config = self.DEFAULT_CONFIG.copy()
        
        # Get configuration from environment variables
        config.update({
            "host": self.env.get("POSTGRES_HOST", "localhost"),
            "port": int(self.env.get("POSTGRES_PORT", 5432)),
            "user": self.env.get("POSTGRES_USER", "postgres"),
            "password": self.env.get("POSTGRES_PASSWORD", ""),
            "database": self.env.get("POSTGRES_DB", f"{service_name}_db"),
            "pool_size": int(self.env.get("POSTGRES_POOL_SIZE", service_config.get("pool_size", 5))),
            "max_overflow": int(self.env.get("POSTGRES_MAX_OVERFLOW", service_config.get("max_overflow", 10)))
        })
        
        # Production-specific settings
        config.update({
            "pool_timeout": 30,
            "pool_recycle": 3600,
            "echo": self.env.get("SQL_ECHO", "false").lower() == "true",
            "isolation_level": "READ_COMMITTED"
        })
        
        return config
    
    def _set_environment_variables(self, service_name: str, config: Dict[str, Any]) -> None:
        """Set environment variables for database configuration."""
        source = f"{service_name}_database_config"
        
        # Set individual PostgreSQL variables
        self.env.set("POSTGRES_HOST", str(config["host"]), source)
        self.env.set("POSTGRES_PORT", str(config["port"]), source)
        self.env.set("POSTGRES_USER", config["user"], source)
        self.env.set("POSTGRES_PASSWORD", config["password"], source)
        self.env.set("POSTGRES_DB", config["database"], source)
        
        # Set database URL
        db_url = self._build_database_url(config)
        self.env.set("DATABASE_URL", db_url, source)
        
        # Set connection pool settings
        self.env.set("POSTGRES_POOL_SIZE", str(config.get("pool_size", 5)), source)
        self.env.set("POSTGRES_MAX_OVERFLOW", str(config.get("max_overflow", 10)), source)
        self.env.set("POSTGRES_POOL_TIMEOUT", str(config.get("pool_timeout", 30)), source)
        self.env.set("POSTGRES_POOL_RECYCLE", str(config.get("pool_recycle", 3600)), source)
    
    def _build_database_url(self, config: Dict[str, Any]) -> str:
        """Build PostgreSQL database URL from configuration."""
        user = config["user"]
        password = config["password"]
        host = config["host"] 
        port = config["port"]
        database = config["database"]
        
        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        else:
            return f"postgresql://{user}@{host}:{port}/{database}"
    
    def _get_current_config(self, service_name: str) -> Dict[str, Any]:
        """Get current database configuration from environment."""
        return {
            "host": self.env.get("POSTGRES_HOST", "localhost"),
            "port": self.env.get("POSTGRES_PORT", "5432"),
            "user": self.env.get("POSTGRES_USER", "postgres"),
            "password": self.env.get("POSTGRES_PASSWORD", ""),
            "database": self.env.get("POSTGRES_DB", f"{service_name}_db"),
            "pool_size": self.env.get("POSTGRES_POOL_SIZE", "5"),
            "max_overflow": self.env.get("POSTGRES_MAX_OVERFLOW", "10")
        }
    
    def _detect_docker_mode(self) -> bool:
        """Detect if running in Docker mode."""
        docker_indicators = [
            self.env.get("USE_DOCKER_MODE", "false").lower() == "true",
            self.env.get("DOCKER_MODE", "false").lower() == "true",
            self.env.get("POSTGRES_HOST", "localhost") != "localhost"
        ]
        return any(docker_indicators)

# =============================================================================
# SPECIALIZED DATABASE CONFIGURATIONS
# =============================================================================

class ClickHouseConfigManager:
    """SSOT ClickHouse Configuration Manager."""
    
    # SSOT: ClickHouse service configurations  
    CLICKHOUSE_CONFIGS = {
        "analytics": {
            "test_port": 8125,
            "docker_service": "test-clickhouse",
            "database": "test_analytics",
            "user": "test_user",
            "password": "test_pass"
        },
        "test_framework": {
            "test_port": 8126,
            "docker_service": "framework-test-clickhouse",
            "database": "framework_analytics",
            "user": "test_framework",
            "password": "test_framework_pass"
        }
    }
    
    def __init__(self):
        self.env = get_env()
    
    def setup_clickhouse_config(self, service_name: str = "analytics", test_mode: bool = True, use_docker: bool = None) -> Dict[str, Any]:
        """Setup standardized ClickHouse configuration."""
        if service_name not in self.CLICKHOUSE_CONFIGS:
            service_name = "analytics"  # Default to analytics service
        
        config = self.CLICKHOUSE_CONFIGS[service_name]
        
        # Auto-detect Docker mode
        if use_docker is None:
            use_docker = self._detect_docker_mode()
        
        if use_docker:
            clickhouse_config = {
                "host": config["docker_service"],
                "port": 8123,  # Internal ClickHouse port
                "user": config["user"],
                "password": config["password"],
                "database": config["database"]
            }
        else:
            clickhouse_config = {
                "host": "localhost",
                "port": config["test_port"],
                "user": config["user"],
                "password": config["password"], 
                "database": config["database"]
            }
        
        # Set environment variables
        source = f"{service_name}_clickhouse_config"
        self.env.set("CLICKHOUSE_HOST", clickhouse_config["host"], source)
        self.env.set("CLICKHOUSE_PORT", str(clickhouse_config["port"]), source)
        self.env.set("CLICKHOUSE_HTTP_PORT", str(clickhouse_config["port"]), source)  # HTTP port same as port
        self.env.set("CLICKHOUSE_USER", clickhouse_config["user"], source)
        self.env.set("CLICKHOUSE_PASSWORD", clickhouse_config["password"], source)
        self.env.set("CLICKHOUSE_DB", clickhouse_config["database"], source)
        
        # Build ClickHouse URL
        clickhouse_url = f"http://{clickhouse_config['host']}:{clickhouse_config['port']}"
        self.env.set("CLICKHOUSE_URL", clickhouse_url, source)
        
        return clickhouse_config
    
    def _detect_docker_mode(self) -> bool:
        """Detect if running in Docker mode."""
        return self.env.get("CLICKHOUSE_HOST", "localhost") != "localhost"

class RedisConfigManager:
    """SSOT Redis Configuration Manager."""
    
    # SSOT: Redis service configurations
    REDIS_CONFIGS = {
        "backend": {
            "test_port": 6381,
            "docker_service": "test-redis",
            "database": 0
        },
        "auth": {
            "test_port": 6382,
            "docker_service": "auth-test-redis", 
            "database": 1
        },
        "analytics": {
            "test_port": 6383,
            "docker_service": "analytics-test-redis",
            "database": 2
        },
        "test_framework": {
            "test_port": 6380,
            "docker_service": "framework-test-redis",
            "database": 3
        }
    }
    
    def __init__(self):
        self.env = get_env()
    
    def setup_redis_config(self, service_name: str, test_mode: bool = True, use_docker: bool = None) -> Dict[str, Any]:
        """Setup standardized Redis configuration."""
        if service_name not in self.REDIS_CONFIGS:
            service_name = "test_framework"  # Default fallback
        
        config = self.REDIS_CONFIGS[service_name]
        
        # Auto-detect Docker mode
        if use_docker is None:
            use_docker = self._detect_docker_mode()
        
        if use_docker:
            redis_config = {
                "host": config["docker_service"],
                "port": 6379,  # Internal Redis port
                "database": config["database"],
                "username": "",
                "password": ""
            }
        else:
            redis_config = {
                "host": "localhost",
                "port": config["test_port"],
                "database": config["database"],
                "username": "",
                "password": ""
            }
        
        # Set environment variables
        source = f"{service_name}_redis_config"
        self.env.set("REDIS_HOST", redis_config["host"], source)
        self.env.set("REDIS_PORT", str(redis_config["port"]), source)
        self.env.set("REDIS_DB", str(redis_config["database"]), source)
        self.env.set("REDIS_USERNAME", redis_config["username"], source)
        self.env.set("REDIS_PASSWORD", redis_config["password"], source)
        
        # Build Redis URL
        redis_url = f"redis://{redis_config['host']}:{redis_config['port']}/{redis_config['database']}"
        self.env.set("REDIS_URL", redis_url, source)
        
        return redis_config
    
    def _detect_docker_mode(self) -> bool:
        """Detect if running in Docker mode."""
        return self.env.get("REDIS_HOST", "localhost") != "localhost"

# =============================================================================
# GLOBAL INSTANCES AND HELPER FUNCTIONS
# =============================================================================

_db_manager_instance: Optional[DatabaseConfigManager] = None
_clickhouse_manager_instance: Optional[ClickHouseConfigManager] = None  
_redis_manager_instance: Optional[RedisConfigManager] = None

def get_database_manager() -> DatabaseConfigManager:
    """Get SSOT database configuration manager singleton."""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseConfigManager()
    return _db_manager_instance

def get_clickhouse_manager() -> ClickHouseConfigManager:
    """Get SSOT ClickHouse configuration manager singleton."""
    global _clickhouse_manager_instance
    if _clickhouse_manager_instance is None:
        _clickhouse_manager_instance = ClickHouseConfigManager()
    return _clickhouse_manager_instance

def get_redis_manager() -> RedisConfigManager:
    """Get SSOT Redis configuration manager singleton."""
    global _redis_manager_instance
    if _redis_manager_instance is None:
        _redis_manager_instance = RedisConfigManager()
    return _redis_manager_instance

# Helper functions for easy access
def setup_database_config(service_name: str, test_mode: bool = True, use_docker: bool = None) -> Dict[str, Any]:
    """Setup standardized database configuration for a service."""
    manager = get_database_manager()
    return manager.setup_database_config(service_name, test_mode, use_docker)

def get_database_url(service_name: str, test_mode: bool = True, use_docker: bool = None) -> str:
    """Get standardized database URL for a service."""
    manager = get_database_manager()
    return manager.get_database_url(service_name, test_mode, use_docker)

def setup_clickhouse_config(service_name: str = "analytics", test_mode: bool = True, use_docker: bool = None) -> Dict[str, Any]:
    """Setup standardized ClickHouse configuration."""
    manager = get_clickhouse_manager()
    return manager.setup_clickhouse_config(service_name, test_mode, use_docker)

def setup_redis_config(service_name: str, test_mode: bool = True, use_docker: bool = None) -> Dict[str, Any]:
    """Setup standardized Redis configuration."""
    manager = get_redis_manager()
    return manager.setup_redis_config(service_name, test_mode, use_docker)

def setup_all_service_configs(service_name: str, test_mode: bool = True, use_docker: bool = None) -> Dict[str, Dict[str, Any]]:
    """Setup all service configurations (PostgreSQL, Redis, ClickHouse) for a service."""
    configs = {
        "database": setup_database_config(service_name, test_mode, use_docker),
        "redis": setup_redis_config(service_name, test_mode, use_docker)
    }
    
    # Only setup ClickHouse for services that need it
    if service_name in ["analytics", "test_framework"]:
        configs["clickhouse"] = setup_clickhouse_config(service_name, test_mode, use_docker)
    
    logger.info(f"All service configurations setup for {service_name}")
    return configs

# Export key classes and functions
__all__ = [
    "DatabaseConfigManager",
    "ClickHouseConfigManager", 
    "RedisConfigManager",
    "get_database_manager",
    "get_clickhouse_manager",
    "get_redis_manager",
    "setup_database_config",
    "get_database_url",
    "setup_clickhouse_config",
    "setup_redis_config",
    "setup_all_service_configs"
]