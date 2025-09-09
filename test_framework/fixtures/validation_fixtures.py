"""SSOT Configuration Validation Fixtures for Pytest.

This module provides pytest fixtures that automatically validate test configuration
before test execution, ensuring consistent and correct test environments across
all services in the Netra platform.

Usage:
    # Automatic validation (enabled by default)
    from test_framework.fixtures.validation_fixtures import *
    
    # Manual validation in tests
    def test_something(config_validator):
        config_validator.validate_test_environment("backend")

Key Features:
- Automatic configuration validation before each test
- Service-specific validation based on test file location
- Manual validation fixtures for complex test scenarios
- Configuration drift detection and reporting
- Comprehensive error messages with remediation suggestions
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pytest

from test_framework.ssot.configuration_validator import (
    ConfigurationValidator,
    get_config_validator,
    validate_test_config
)
from test_framework.ssot.database_config import (
    setup_all_service_configs,
    get_database_manager,
    get_clickhouse_manager,
    get_redis_manager
)

logger = logging.getLogger(__name__)

# =============================================================================
# AUTOMATIC VALIDATION FIXTURES
# =============================================================================

@pytest.fixture(autouse=True, scope="function")
def validate_test_configuration(request):
    """Automatically validate test configuration before each test.
    
    This fixture runs before every test to ensure configuration consistency.
    It extracts the service name from the test file path and performs
    service-specific validation.
    
    Args:
        request: pytest request object containing test information
    """
    # Extract service name from test file path
    test_file = str(request.fspath) if hasattr(request, 'fspath') else str(request.node.path)
    service_name = _extract_service_name(test_file)
    
    # Skip validation for collection mode to prevent import errors
    if hasattr(request.config, 'option') and getattr(request.config.option, 'collect_only', False):
        return
    
    # Skip validation if explicitly disabled
    if request.node.get_closest_marker('skip_config_validation'):
        logger.info(f"Skipping configuration validation for {test_file} (marked to skip)")
        return
    
    # Skip validation for smoke tests (they should work without external dependencies)
    if request.node.get_closest_marker('smoke'):
        logger.debug(f"Skipping configuration validation for smoke test: {test_file}")
        return
    
    try:
        # Validate configuration with pytest-friendly error handling
        validate_test_config(service_name, skip_on_failure=True)
        logger.debug(f"Configuration validation passed for {service_name or 'unknown service'}: {test_file}")
        
    except Exception as e:
        # Log validation errors but don't fail the test setup
        logger.warning(f"Configuration validation warning for {test_file}: {e}")

@pytest.fixture(autouse=True, scope="session")
def setup_test_session_configuration():
    """Setup and validate test session configuration.
    
    This session-scoped fixture runs once per test session to ensure
    the overall test environment is properly configured.
    """
    logger.info("Setting up test session configuration validation...")
    
    try:
        # Perform general configuration validation
        validator = get_config_validator()
        env_valid, env_errors = validator.validate_test_environment()
        
        if not env_valid:
            logger.warning(f"Test session configuration issues: {env_errors}")
            # Don't fail session setup, but log issues for debugging
        
        # Validate service flags consistency
        flags_valid, flag_errors = validator.validate_service_flags()
        if not flags_valid:
            logger.warning(f"Service flag configuration issues: {flag_errors}")
        
        logger.info("Test session configuration validation completed")
        
    except Exception as e:
        logger.error(f"Test session configuration validation failed: {e}")
        # Don't fail session setup to allow tests to run

# =============================================================================
# MANUAL VALIDATION FIXTURES
# =============================================================================

@pytest.fixture
def config_validator() -> ConfigurationValidator:
    """Provide configuration validator for manual validation in tests.
    
    Usage:
        def test_custom_validation(config_validator):
            is_valid, errors = config_validator.validate_database_configuration("backend")
            assert is_valid, f"Database config invalid: {errors}"
    
    Returns:
        ConfigurationValidator instance
    """
    return get_config_validator()

@pytest.fixture
def database_config_manager():
    """Provide database configuration manager for tests.
    
    Usage:
        def test_database_setup(database_config_manager):
            config = database_config_manager.setup_database_config("backend", test_mode=True)
            assert config["host"] == "localhost"
    
    Returns:
        DatabaseConfigManager instance
    """
    return get_database_manager()

@pytest.fixture
def service_config_validator():
    """Provide service-specific configuration validation.
    
    Usage:
        def test_service_config(service_config_validator):
            results = service_config_validator("backend")
            assert results["database"]["valid"], f"DB config invalid: {results['database']['issues']}"
    
    Returns:
        Function that validates configuration for a given service
    """
    def validate_service_config(service_name: str) -> Dict[str, Dict[str, any]]:
        """Validate all aspects of a service's configuration."""
        validator = get_config_validator()
        
        results = {
            "environment": {},
            "database": {},
            "service_flags": {},
            "docker_config": {}
        }
        
        # Validate environment
        env_valid, env_errors = validator.validate_test_environment(service_name)
        results["environment"] = {"valid": env_valid, "issues": env_errors}
        
        # Validate database configuration
        db_valid, db_errors = validator.validate_database_configuration(service_name)
        results["database"] = {"valid": db_valid, "issues": db_errors}
        
        # Validate service flags
        flags_valid, flag_errors = validator.validate_service_flags()
        results["service_flags"] = {"valid": flags_valid, "issues": flag_errors}
        
        # Validate Docker configuration
        docker_valid, docker_errors = validator.validate_docker_configuration()
        results["docker_config"] = {"valid": docker_valid, "issues": docker_errors}
        
        return results
    
    return validate_service_config

# =============================================================================
# SERVICE-SPECIFIC CONFIGURATION FIXTURES
# =============================================================================

@pytest.fixture
def backend_test_config():
    """Setup and validate backend test configuration.
    
    Returns:
        Dictionary containing backend service configurations
    """
    configs = setup_all_service_configs("backend", test_mode=True)
    
    # Validate backend-specific requirements
    validator = get_config_validator()
    db_valid, db_errors = validator.validate_database_configuration("backend")
    
    if not db_valid:
        pytest.skip(f"Backend database configuration invalid: {db_errors}")
    
    return configs

@pytest.fixture
def auth_test_config():
    """Setup and validate auth service test configuration.
    
    Returns:
        Dictionary containing auth service configurations
    """
    configs = setup_all_service_configs("auth", test_mode=True)
    
    # Validate auth-specific requirements
    validator = get_config_validator()
    db_valid, db_errors = validator.validate_database_configuration("auth")
    
    if not db_valid:
        pytest.skip(f"Auth database configuration invalid: {db_errors}")
    
    return configs

@pytest.fixture
def analytics_test_config():
    """Setup and validate analytics service test configuration.
    
    Returns:
        Dictionary containing analytics service configurations
    """
    configs = setup_all_service_configs("analytics", test_mode=True)
    
    # Validate analytics-specific requirements (ClickHouse required)
    validator = get_config_validator()
    
    # Check ClickHouse requirement
    if not validator.is_service_enabled("clickhouse"):
        pytest.skip("Analytics service requires ClickHouse but it's disabled")
    
    db_valid, db_errors = validator.validate_database_configuration("analytics")
    if not db_valid:
        pytest.skip(f"Analytics database configuration invalid: {db_errors}")
    
    return configs

# =============================================================================
# CONFIGURATION REPORTING FIXTURES
# =============================================================================

@pytest.fixture
def config_report():
    """Generate comprehensive configuration report for debugging.
    
    Usage:
        def test_debug_config(config_report):
            print(config_report)  # Print full configuration state
    
    Returns:
        Dictionary containing detailed configuration information
    """
    validator = get_config_validator()
    
    # Collect all configuration information
    report = {
        "timestamp": str(pytest.current_timestamp) if hasattr(pytest, 'current_timestamp') else "unknown",
        "environment_validation": {},
        "service_flags": {},
        "docker_config": {},
        "port_allocation": validator.PORT_ALLOCATION.copy(),
        "service_configs": validator.SERVICE_CONFIGS.copy()
    }
    
    # Environment validation
    env_valid, env_errors = validator.validate_test_environment()
    report["environment_validation"] = {"valid": env_valid, "issues": env_errors}
    
    # Service flags validation
    flags_valid, flag_errors = validator.validate_service_flags()
    report["service_flags"] = {"valid": flags_valid, "issues": flag_errors}
    
    # Docker configuration
    docker_valid, docker_errors = validator.validate_docker_configuration()
    report["docker_config"] = {"valid": docker_valid, "issues": docker_errors}
    
    # Current environment variables (subset)
    env_vars = {}
    important_vars = [
        "TESTING", "ENVIRONMENT", "USE_REAL_SERVICES",
        "POSTGRES_HOST", "POSTGRES_PORT", "REDIS_HOST", "REDIS_PORT",
        "CLICKHOUSE_ENABLED", "TEST_DISABLE_REDIS", "TEST_DISABLE_CLICKHOUSE"
    ]
    
    for var in important_vars:
        env_vars[var] = validator.env.get(var, "NOT_SET")
    
    report["environment_variables"] = env_vars
    
    return report

# =============================================================================
# PERFORMANCE MONITORING FIXTURES
# =============================================================================

@pytest.fixture
def config_performance_monitor():
    """Monitor configuration-related performance metrics.
    
    Usage:
        def test_config_performance(config_performance_monitor):
            config_performance_monitor.start("database_setup")
            # ... database setup code ...
            duration = config_performance_monitor.end("database_setup")
            assert duration < 5.0, "Database setup too slow"
    
    Returns:
        Performance monitor instance
    """
    import time
    
    class ConfigPerformanceMonitor:
        def __init__(self):
            self.measurements = {}
        
        def start(self, operation: str):
            self.measurements[operation] = {"start": time.time()}
        
        def end(self, operation: str) -> float:
            if operation not in self.measurements:
                raise ValueError(f"No start time recorded for operation: {operation}")
            
            duration = time.time() - self.measurements[operation]["start"]
            self.measurements[operation]["duration"] = duration
            return duration
        
        def get_report(self) -> Dict[str, float]:
            return {op: data.get("duration", 0) for op, data in self.measurements.items()}
    
    return ConfigPerformanceMonitor()

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_service_name(test_file_path: str) -> Optional[str]:
    """Extract service name from test file path.
    
    Args:
        test_file_path: Path to the test file
        
    Returns:
        Service name or None if not determinable
    """
    path_lower = test_file_path.lower()
    
    # Service directory mappings
    service_mappings = {
        "netra_backend": "backend",
        "auth_service": "auth", 
        "analytics_service": "analytics",
        "test_framework": "test_framework",
        "frontend": "frontend"
    }
    
    # Check each mapping
    for path_part, service_name in service_mappings.items():
        if path_part in path_lower:
            return service_name
    
    # Check for test type in path
    if "e2e" in path_lower:
        return "backend"  # E2E tests typically test backend
    elif "integration" in path_lower:
        return "backend"  # Most integration tests are backend
    
    return None

# =============================================================================
# PYTEST MARKERS FOR CONFIGURATION CONTROL
# =============================================================================

def pytest_configure(config):
    """Register custom pytest markers for configuration control."""
    config.addinivalue_line(
        "markers", "skip_config_validation: skip automatic configuration validation for this test"
    )
    config.addinivalue_line(
        "markers", "requires_real_database: test requires real database connection"
    )
    config.addinivalue_line(
        "markers", "requires_clickhouse: test requires ClickHouse to be enabled"
    )
    config.addinivalue_line(
        "markers", "requires_redis: test requires Redis to be enabled"
    )

# Export all fixtures and helper functions
__all__ = [
    # Automatic validation fixtures
    "validate_test_configuration",
    "setup_test_session_configuration",
    
    # Manual validation fixtures
    "config_validator",
    "database_config_manager", 
    "service_config_validator",
    
    # Service-specific fixtures
    "backend_test_config",
    "auth_test_config",
    "analytics_test_config",
    
    # Reporting and monitoring
    "config_report",
    "config_performance_monitor"
]