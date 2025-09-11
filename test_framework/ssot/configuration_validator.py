"""SSOT Configuration Validation for Test Environments.

This module provides comprehensive validation of test configuration consistency
across all services in the Netra platform. It implements the standardized
patterns defined in the Test Configuration Standardization Report.

Usage:
    from test_framework.ssot.configuration_validator import validate_test_config
    
    # Validate environment before running tests
    validate_test_config("backend")  # Service-specific validation
    validate_test_config()           # General validation

Key Features:
- Database configuration validation
- Service enable/disable flag consistency checking  
- Environment variable precedence validation
- Docker vs non-Docker mode compatibility
- Port conflict detection
- Comprehensive error reporting with remediation suggestions
"""

import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse

from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)

class ConfigurationValidator:
    """Validates test configuration consistency across services."""
    
    __test__ = False  # Tell pytest this is not a test class
    
    # SSOT: Required test environment variables
    REQUIRED_TEST_VARS = [
        "TESTING",
        "ENVIRONMENT", 
        "JWT_SECRET_KEY",
        "SERVICE_SECRET"
    ]
    
    # SSOT: Valid environment values
    VALID_ENVIRONMENTS = ["testing", "test", "staging", "development", "dev"]
    
    # SSOT: Service-specific configuration requirements
    SERVICE_CONFIGS = {
        "backend": {
            "required_ports": ["8000"],
            "database": "backend_test_db",
            "redis_db": 0,
            "postgres_port": 5434,
            "clickhouse_optional": True
        },
        "auth": {
            "required_ports": ["8081"], 
            "database": "auth_test_db",
            "redis_db": 1,
            "postgres_port": 5435,
            "clickhouse_required": False
        },
        "analytics": {
            "required_ports": ["8082"],
            "database": "analytics_test_db", 
            "redis_db": 2,
            "postgres_port": 5436,
            "clickhouse_required": True
        },
        "test_framework": {
            "required_ports": [],
            "database": "framework_test_db",
            "redis_db": 3,
            "postgres_port": 5433,
            "clickhouse_required": False
        }
    }
    
    # SSOT: Service enable/disable flag patterns
    SERVICE_FLAGS = {
        "clickhouse": {
            "enable_flag": "CLICKHOUSE_ENABLED",
            "disable_flag": "TEST_DISABLE_CLICKHOUSE",
            "dev_disable_flag": "DEV_MODE_DISABLE_CLICKHOUSE",
            "default_enabled": False  # Disabled by default in tests
        },
        "redis": {
            "enable_flag": "REDIS_ENABLED", 
            "disable_flag": "TEST_DISABLE_REDIS",
            "dev_disable_flag": None,
            "default_enabled": True   # Enabled by default
        },
        "postgres": {
            "enable_flag": "POSTGRES_ENABLED",
            "disable_flag": "TEST_DISABLE_POSTGRES",
            "dev_disable_flag": None,
            "default_enabled": True
        }
    }
    
    # SSOT: Port allocation map (prevents conflicts)
    PORT_ALLOCATION = {
        # PostgreSQL ports
        5433: "test_framework",
        5434: "backend",
        5435: "auth",
        5436: "analytics",
        
        # Redis ports  
        6379: "default_redis",
        6380: "dev_redis",
        6381: "test_redis",
        6382: "alpine_test_redis",
        
        # ClickHouse ports
        8123: "default_clickhouse",
        8124: "dev_clickhouse", 
        8125: "test_clickhouse",
        8126: "alpine_test_clickhouse",
        
        # Application ports
        8000: "backend",
        8001: "backend_dev",
        8002: "backend_alpine_test",
        8081: "auth",
        8082: "analytics",
        8083: "auth_alpine_test",
        
        # Frontend ports
        3000: "frontend",
        3001: "frontend_dev", 
        3002: "frontend_alpine_test"
    }
    
    def __init__(self):
        self.env = get_env()
        
    def validate_test_environment(self, service_name: str = None) -> Tuple[bool, List[str]]:
        """Validate test environment configuration.
        
        Args:
            service_name: Optional service name for service-specific validation
            
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        # Check required variables
        missing_vars = []
        for var in self.REQUIRED_TEST_VARS:
            if not self.env.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            errors.append(f"Missing required test variables: {missing_vars}")
            errors.append("REMEDY: Ensure test environment setup calls ensure_test_isolation()")
        
        # Validate environment value
        env_value = self.env.get("ENVIRONMENT", "") or ""
        env_value = env_value.lower()
        if env_value not in self.VALID_ENVIRONMENTS:
            errors.append(f"Invalid ENVIRONMENT value: '{env_value}'. Valid values: {self.VALID_ENVIRONMENTS}")
            errors.append("REMEDY: Set ENVIRONMENT to 'testing' for test execution")
        
        # Validate TESTING flag consistency
        testing_flag = self.env.get("TESTING", "0")
        if env_value in ["testing", "test"] and testing_flag != "1":
            errors.append(f"Inconsistent TESTING flag: ENVIRONMENT={env_value} but TESTING={testing_flag}")
            errors.append("REMEDY: Set TESTING=1 when ENVIRONMENT=testing")
        
        # Service-specific validation
        if service_name and service_name in self.SERVICE_CONFIGS:
            service_errors = self._validate_service_config(service_name)
            errors.extend(service_errors)
        
        return len(errors) == 0, errors
    
    def validate_database_configuration(self, service_name: str) -> Tuple[bool, List[str]]:
        """Validate database configuration for service.
        
        Args:
            service_name: Name of service to validate database config for
            
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        # Validate DATABASE_URL if present
        db_url = self.env.get("DATABASE_URL")
        if db_url:
            url_errors = self._validate_database_url(db_url)
            errors.extend(url_errors)
        
        # Validate PostgreSQL configuration
        postgres_errors = self._validate_postgres_config(service_name)
        errors.extend(postgres_errors)
        
        # Check for port conflicts
        if service_name in self.SERVICE_CONFIGS:
            expected_port = self.SERVICE_CONFIGS[service_name]["postgres_port"]
            port_errors = self._validate_port_allocation(expected_port, service_name)
            errors.extend(port_errors)
        
        return len(errors) == 0, errors
    
    def validate_service_flags(self) -> Tuple[bool, List[str]]:
        """Validate service enable/disable flag consistency.
        
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        # Check each service's flag consistency
        for service_name, flags in self.SERVICE_FLAGS.items():
            flag_errors = self._validate_service_flags_for_service(service_name, flags)
            errors.extend(flag_errors)
        
        # Check for conflicting global flags
        global_conflicts = [
            ("USE_REAL_SERVICES", "SKIP_MOCKS", "Cannot use real services and skip mocks simultaneously"),
            ("ENABLE_REAL_LLM_TESTING", "USE_MOCK_LLM", "Cannot use real LLM and mock LLM simultaneously")
        ]
        
        for flag1, flag2, message in global_conflicts:
            if (self.env.get(flag1, "false").lower() == "true" and 
                self.env.get(flag2, "false").lower() == "true"):
                errors.append(f"Conflicting flags: {message}")
                errors.append(f"REMEDY: Set only one of {flag1} or {flag2} to true")
        
        return len(errors) == 0, errors
    
    def validate_docker_configuration(self, use_docker: bool = None) -> Tuple[bool, List[str]]:
        """Validate Docker vs non-Docker configuration consistency.
        
        Args:
            use_docker: Whether Docker mode is expected (auto-detected if None)
            
        Returns:
            Tuple of (is_valid, error_list)
        """
        errors = []
        
        # Auto-detect Docker mode if not specified
        if use_docker is None:
            use_docker = self._detect_docker_mode()
        
        docker_errors = self._validate_docker_service_config(use_docker)
        errors.extend(docker_errors)
        
        return len(errors) == 0, errors
    
    def is_service_enabled(self, service_name: str) -> bool:
        """Check if a service is enabled using SSOT flag logic.
        
        Args:
            service_name: Name of service to check
            
        Returns:
            True if service is enabled, False otherwise
        """
        service_name_lower = service_name.lower()
        flags = self.SERVICE_FLAGS.get(service_name_lower)
        
        if not flags:
            logger.warning(f"Unknown service '{service_name}', defaulting to enabled")
            return True
        
        # Check explicit disable first (highest priority)
        disable_flag = flags.get("disable_flag")
        if disable_flag and self.env.get(disable_flag, "false").lower() == "true":
            return False
        
        # Check dev mode disable
        dev_disable_flag = flags.get("dev_disable_flag")
        if dev_disable_flag and self.env.get(dev_disable_flag, "false").lower() == "true":
            return False
        
        # Check explicit enable
        enable_flag = flags.get("enable_flag")
        if enable_flag:
            enable_value = self.env.get(enable_flag, str(flags["default_enabled"])).lower()
            return enable_value == "true"
        
        # Default to service default
        return flags["default_enabled"]
    
    def get_service_port(self, service_name: str, port_type: str = "postgres") -> Optional[int]:
        """Get the expected port for a service.
        
        Args:
            service_name: Name of service
            port_type: Type of port (postgres, redis, clickhouse, app)
            
        Returns:
            Port number or None if not defined
        """
        if service_name not in self.SERVICE_CONFIGS:
            return None
        
        config = self.SERVICE_CONFIGS[service_name]
        
        if port_type == "postgres":
            return config.get("postgres_port")
        elif port_type == "redis":
            # Calculate Redis port offset from PostgreSQL port
            postgres_port = config.get("postgres_port", 5433)
            return postgres_port + 1000  # Redis ports are PostgreSQL + 1000
        elif port_type == "app" and config.get("required_ports"):
            return int(config["required_ports"][0])
        
        return None
    
    def _validate_service_config(self, service_name: str) -> List[str]:
        """Validate service-specific configuration."""
        errors = []
        config = self.SERVICE_CONFIGS[service_name]
        
        # Check ClickHouse requirement
        if config.get("clickhouse_required"):
            if not self.is_service_enabled("clickhouse"):
                errors.append(f"Service '{service_name}' requires ClickHouse but it's disabled")
                errors.append(f"REMEDY: Set CLICKHOUSE_ENABLED=true or TEST_DISABLE_CLICKHOUSE=false")
        
        # Validate expected database name
        expected_db = config.get("database")
        if expected_db:
            db_name = self.env.get("POSTGRES_DB")
            if db_name and expected_db not in db_name:
                errors.append(f"Database name mismatch for {service_name}: expected '{expected_db}' pattern, got '{db_name}'")
                errors.append(f"REMEDY: Ensure POSTGRES_DB contains '{expected_db}' for service isolation")
        
        return errors
    
    def _validate_database_url(self, db_url: str) -> List[str]:
        """Validate database URL format and content."""
        errors = []
        
        try:
            parsed = urlparse(db_url)
            
            # Check scheme
            valid_schemes = ["postgresql", "sqlite", "sqlite+aiosqlite"]
            if parsed.scheme not in valid_schemes:
                errors.append(f"Invalid database URL scheme: '{parsed.scheme}'. Valid: {valid_schemes}")
                errors.append("REMEDY: Use postgresql:// for real DB or sqlite:// for test DB")
            
            # For PostgreSQL URLs, validate components
            if parsed.scheme == "postgresql":
                if not parsed.hostname:
                    errors.append("PostgreSQL URL missing hostname")
                if not parsed.port:
                    errors.append("PostgreSQL URL missing port")
                if not parsed.username:
                    errors.append("PostgreSQL URL missing username")
                if not parsed.path or parsed.path == "/":
                    errors.append("PostgreSQL URL missing database name")
            
        except Exception as e:
            errors.append(f"Invalid database URL format: {e}")
            errors.append("REMEDY: Use valid URL format like postgresql://user:pass@host:port/db")
        
        return errors
    
    def _validate_postgres_config(self, service_name: str) -> List[str]:
        """Validate PostgreSQL configuration variables."""
        errors = []
        
        # Required PostgreSQL variables
        postgres_vars = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": str(self.SERVICE_CONFIGS[service_name]["postgres_port"]),
            "POSTGRES_USER": f"test_{service_name}" if service_name != "test_framework" else "test_user",
            "POSTGRES_DB": f"{service_name}_test_db"
        }
        
        # Check each variable
        for var, expected_pattern in postgres_vars.items():
            value = self.env.get(var)
            if not value:
                errors.append(f"Missing PostgreSQL variable: {var}")
                errors.append(f"REMEDY: Set {var}={expected_pattern}")
            elif var == "POSTGRES_PORT":
                try:
                    port = int(value)
                    expected_port = self.SERVICE_CONFIGS[service_name]["postgres_port"]
                    if port != expected_port:
                        errors.append(f"PostgreSQL port mismatch for {service_name}: expected {expected_port}, got {port}")
                        errors.append(f"REMEDY: Set POSTGRES_PORT={expected_port} for {service_name}")
                except ValueError:
                    errors.append(f"Invalid PostgreSQL port: {value}")
                    errors.append("REMEDY: Set POSTGRES_PORT to a valid integer")
        
        return errors
    
    def _validate_port_allocation(self, port: int, service_name: str) -> List[str]:
        """Validate port allocation against conflicts."""
        errors = []
        
        if port in self.PORT_ALLOCATION:
            allocated_service = self.PORT_ALLOCATION[port]
            if allocated_service != service_name:
                errors.append(f"Port conflict: {port} is allocated to '{allocated_service}' but used by '{service_name}'")
                errors.append(f"REMEDY: Use port {self.SERVICE_CONFIGS[service_name]['postgres_port']} for {service_name}")
        
        return errors
    
    def _validate_service_flags_for_service(self, service_name: str, flags: Dict[str, Any]) -> List[str]:
        """Validate flags for a specific service."""
        errors = []
        
        enable_flag = flags.get("enable_flag")
        disable_flag = flags.get("disable_flag") 
        dev_disable_flag = flags.get("dev_disable_flag")
        
        # Check for explicit conflicts
        enabled = enable_flag and self.env.get(enable_flag, "false").lower() == "true"
        disabled = disable_flag and self.env.get(disable_flag, "false").lower() == "true"
        dev_disabled = dev_disable_flag and self.env.get(dev_disable_flag, "false").lower() == "true"
        
        if enabled and disabled:
            errors.append(f"Conflicting {service_name} flags: {enable_flag}=true and {disable_flag}=true")
            errors.append(f"REMEDY: Set only one of {enable_flag} or {disable_flag}")
        
        if enabled and dev_disabled:
            errors.append(f"Conflicting {service_name} flags: {enable_flag}=true and {dev_disable_flag}=true")
            errors.append(f"REMEDY: Set {dev_disable_flag}=false when enabling {service_name}")
        
        return errors
    
    def _detect_docker_mode(self) -> bool:
        """Detect if running in Docker mode."""
        # Check for Docker-specific environment indicators
        docker_indicators = [
            self.env.get("USE_DOCKER_MODE", "false").lower() == "true",
            self.env.get("DOCKER_MODE", "false").lower() == "true", 
            self.env.get("POSTGRES_HOST", "") in ["test-postgres", "alpine-test-postgres"],
            self.env.get("REDIS_HOST", "") in ["test-redis", "alpine-test-redis"]
        ]
        
        return any(docker_indicators)
    
    def _validate_docker_service_config(self, use_docker: bool) -> List[str]:
        """Validate Docker vs non-Docker service configuration."""
        errors = []
        
        postgres_host = self.env.get("POSTGRES_HOST", "localhost")
        redis_host = self.env.get("REDIS_HOST", "localhost")
        
        if use_docker:
            # Docker mode expectations
            if postgres_host == "localhost":
                errors.append("Docker mode detected but POSTGRES_HOST=localhost (should be service name)")
                errors.append("REMEDY: Set POSTGRES_HOST=test-postgres for Docker mode")
            
            if redis_host == "localhost":
                errors.append("Docker mode detected but REDIS_HOST=localhost (should be service name)")
                errors.append("REMEDY: Set REDIS_HOST=test-redis for Docker mode")
        else:
            # Non-Docker mode expectations
            if postgres_host != "localhost":
                errors.append(f"Non-Docker mode detected but POSTGRES_HOST={postgres_host} (should be localhost)")
                errors.append("REMEDY: Set POSTGRES_HOST=localhost for non-Docker mode")
            
            if redis_host != "localhost":
                errors.append(f"Non-Docker mode detected but REDIS_HOST={redis_host} (should be localhost)")
                errors.append("REMEDY: Set REDIS_HOST=localhost for non-Docker mode")
        
        return errors


# =============================================================================
# GLOBAL VALIDATOR INSTANCE AND HELPER FUNCTIONS
# =============================================================================

_validator_instance: Optional[ConfigurationValidator] = None

def get_config_validator() -> ConfigurationValidator:
    """Get SSOT configuration validator singleton instance."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = ConfigurationValidator()
    return _validator_instance

def validate_test_config(service_name: str = None, skip_on_failure: bool = True) -> None:
    """Validate test configuration and fail fast on errors.
    
    Args:
        service_name: Optional service name for service-specific validation
        skip_on_failure: Whether to skip tests on validation failure (default: True)
        
    Raises:
        RuntimeError: If validation fails and skip_on_failure is False
        pytest.skip: If validation fails and skip_on_failure is True
    """
    validator = get_config_validator()
    all_errors = []
    
    # Validate environment
    env_valid, env_errors = validator.validate_test_environment(service_name)
    if not env_valid:
        all_errors.extend([f"Environment: {err}" for err in env_errors])
    
    # Validate database if service specified
    if service_name:
        db_valid, db_errors = validator.validate_database_configuration(service_name)
        if not db_valid:
            all_errors.extend([f"Database: {err}" for err in db_errors])
    
    # Validate service flags
    flags_valid, flag_errors = validator.validate_service_flags()
    if not flags_valid:
        all_errors.extend([f"Service Flags: {err}" for err in flag_errors])
    
    # Validate Docker configuration
    docker_valid, docker_errors = validator.validate_docker_configuration()
    if not docker_valid:
        all_errors.extend([f"Docker Config: {err}" for err in docker_errors])
    
    if all_errors:
        error_message = f"Test configuration validation failed for {service_name or 'all services'}:\n" + "\n".join(all_errors)
        
        if skip_on_failure:
            try:
                import pytest
                pytest.skip(error_message)
            except ImportError:
                # pytest not available, raise RuntimeError instead
                raise RuntimeError(error_message)
        else:
            raise RuntimeError(error_message)
    else:
        logger.info(f"Test configuration validation passed for {service_name or 'all services'}")

def is_service_enabled(service_name: str) -> bool:
    """Check if a service is enabled using SSOT logic.
    
    Args:
        service_name: Name of service to check
        
    Returns:
        True if service is enabled, False otherwise
    """
    validator = get_config_validator()
    return validator.is_service_enabled(service_name)

def get_service_port(service_name: str, port_type: str = "postgres") -> Optional[int]:
    """Get the expected port for a service using SSOT allocation.
    
    Args:
        service_name: Name of service
        port_type: Type of port (postgres, redis, clickhouse, app)
        
    Returns:
        Port number or None if not defined
    """
    validator = get_config_validator()
    return validator.get_service_port(service_name, port_type)

# Legacy alias for backward compatibility
TestConfigurationValidator = ConfigurationValidator

# Export key classes and functions
__all__ = [
    "ConfigurationValidator",
    "TestConfigurationValidator",  # Legacy alias
    "get_config_validator", 
    "validate_test_config",
    "is_service_enabled",
    "get_service_port"
]