"""Test Environment Configuration

from shared.isolated_environment import get_env
Provides configuration for E2E test environments.
Now integrates with service availability detection to provide intelligent
configuration based on actual service availability.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Reliability  
- Value Impact: Eliminates false test failures due to incorrect service detection
- Strategic Impact: Improves CI/CD reliability and developer experience
"""

import asyncio
import pytest
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

# Import service availability detection
try:
    from tests.e2e.service_availability import get_service_availability
    from tests.e2e.real_service_config import get_real_service_config, ServiceConfigHelper
except ImportError:
    # Fallback if service availability modules not available
    get_service_availability = None
    get_real_service_config = None
    ServiceConfigHelper = None


@pytest.mark.e2e
class TestEnvironmentType(Enum):
    """Test environment types."""
    LOCAL = "local"
    TEST = "test"
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ServiceUrls:
    """Service URL configuration."""
    backend: str
    auth: str
    frontend: str
    websocket: str


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str
    redis_url: str
    clickhouse_url: Optional[str] = None


@dataclass
@pytest.mark.e2e
class TestEnvironmentConfig:
    """Configuration for test environments."""
    
    environment: TestEnvironmentType
    services: ServiceUrls
    database: DatabaseConfig
    
    # Test user credentials
    test_user_email: str = "test@example.com"
    test_user_password: str = "Test123!@#"
    
    # Timeouts
    connection_timeout: float = 30.0
    request_timeout: float = 10.0
    websocket_timeout: float = 5.0
    
    # Feature flags (now dynamically determined)
    use_real_llm: bool = False
    use_real_database: bool = False
    enable_monitoring: bool = False
    
    # Service availability metadata
    service_detection_enabled: bool = True
    detected_services: Optional[Dict[str, Any]] = None


async def get_test_environment_config_async(environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Get test environment configuration with service availability detection.
    
    Args:
        environment: Optional environment type override
        
    Returns:
        TestEnvironmentConfig with intelligent service detection
    """
    # Get base configuration
    base_config = _get_base_test_environment_config(environment)
    
    # If service availability detection is available, enhance configuration
    if get_real_service_config and base_config.service_detection_enabled:
        try:
            real_service_config = await get_real_service_config()
            
            # Update database configuration based on availability
            base_config.database.url = real_service_config.database.postgres_url
            base_config.database.redis_url = real_service_config.database.redis_url
            if real_service_config.database.clickhouse_url:
                base_config.database.clickhouse_url = real_service_config.database.clickhouse_url
            
            # Update feature flags based on actual availability
            base_config.use_real_database = real_service_config.database.is_using_real_databases
            base_config.use_real_llm = real_service_config.llm.use_real_llm
            
            # Store service detection metadata
            base_config.detected_services = real_service_config.service_availability.summary
            
        except Exception as e:
            # Log error but continue with base configuration
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Service availability detection failed: {e}")
            logger.warning("Falling back to environment-based configuration")
    
    return base_config


def _get_base_test_environment_config(environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Get base test environment configuration without service detection.
    
    Args:
        environment: Optional environment type override
        
    Returns:
        TestEnvironmentConfig for the specified environment
    """
    # Auto-detect environment if not specified
    if environment is None:
        env_var = get_env().get("TEST_ENVIRONMENT", "test").lower()
        environment = TestEnvironmentType.TEST if env_var == "test" else TestEnvironmentType.DEV
    
    # Environment-specific configurations
    if environment == TestEnvironmentType.TEST:
        return TestEnvironmentConfig(
            environment=TestEnvironmentType.TEST,
            services=ServiceUrls(
                backend="http://localhost:8000",
                auth="http://localhost:8081",
                frontend="http://localhost:3000",
                websocket="ws://localhost:8000/ws"
            ),
            database=DatabaseConfig(
                url=get_env().get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:"),  # Default to SQLite for tests
                redis_url=get_env().get("TEST_REDIS_URL", "redis://localhost:6380/0"),  # Different port for tests
                clickhouse_url=get_env().get("TEST_CLICKHOUSE_URL", "clickhouse://localhost:8124")  # Different port for tests
            ),
            use_real_database=False,
            service_detection_enabled=True
        )
    
    elif environment == TestEnvironmentType.DEV:
        return TestEnvironmentConfig(
            environment=TestEnvironmentType.DEV,
            services=ServiceUrls(
                backend="http://localhost:8000",
                auth="http://localhost:8081",
                frontend="http://localhost:3000",
                websocket="ws://localhost:8000/ws"
            ),
            database=DatabaseConfig(
                url=get_env().get("DATABASE_URL", "postgresql://dev:dev@localhost:5432/dev_db"),
                redis_url=get_env().get("REDIS_URL", "redis://localhost:6379"),
                clickhouse_url=get_env().get("CLICKHOUSE_URL", "clickhouse://localhost:8123")
            ),
            use_real_database=True,
            service_detection_enabled=True
        )
    
    elif environment == TestEnvironmentType.STAGING:
        return TestEnvironmentConfig(
            environment=TestEnvironmentType.STAGING,
            services=ServiceUrls(
                backend=get_env().get("STAGING_API_URL", "https://staging.netra.ai"),
                auth=get_env().get("STAGING_AUTH_URL", "https://auth.staging.netra.ai"),
                frontend=get_env().get("STAGING_FRONTEND_URL", "https://staging.netra.ai"),
                websocket=get_env().get("STAGING_WS_URL", "wss://staging.netra.ai/ws")
            ),
            database=DatabaseConfig(
                url=get_env().get("STAGING_DATABASE_URL", "postgresql://staging:staging@localhost:5432/staging_db"),
                redis_url=get_env().get("STAGING_REDIS_URL", "redis://localhost:6379"),
                clickhouse_url=get_env().get("STAGING_CLICKHOUSE_URL", "clickhouse://localhost:8123")
            ),
            use_real_database=True,
            use_real_llm=True,
            service_detection_enabled=True
        )
    
    else:
        # Default to local/test configuration
        return _get_base_test_environment_config(TestEnvironmentType.TEST)


def get_test_environment_config(environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Synchronous wrapper for backward compatibility.
    
    WARNING: This function does not perform service availability detection.
    Use get_test_environment_config_async() for full functionality.
    """
    return _get_base_test_environment_config(environment)


def get_test_config(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test configuration for specified environment name.
    
    WARNING: This function does not perform service availability detection.
    Use get_test_config_async() for full functionality.
    """
    env_map = {
        "test": TestEnvironmentType.TEST,
        "dev": TestEnvironmentType.DEV,
        "staging": TestEnvironmentType.STAGING,
        "production": TestEnvironmentType.PRODUCTION
    }
    env_type = env_map.get(env_name, TestEnvironmentType.TEST)
    return _get_base_test_environment_config(env_type)


async def get_test_config_async(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test configuration for specified environment name with service detection.
    
    Args:
        env_name: Environment name ("test", "dev", "staging", "production")
        
    Returns:
        TestEnvironmentConfig with intelligent service detection
    """
    env_map = {
        "test": TestEnvironmentType.TEST,
        "dev": TestEnvironmentType.DEV,
        "staging": TestEnvironmentType.STAGING,
        "production": TestEnvironmentType.PRODUCTION
    }
    env_type = env_map.get(env_name, TestEnvironmentType.TEST)
    return await get_test_environment_config_async(env_type)


# Helper functions for common test patterns
async def should_skip_test_without_real_services(test_name: str = "") -> str:
    """Check if test should be skipped due to missing real services.
    
    Args:
        test_name: Optional test name for logging
        
    Returns:
        Skip reason string or empty string if test should run
    """
    if not ServiceConfigHelper:
        return ""  # No service detection available
    
    try:
        skip_reason = await ServiceConfigHelper.skip_test_if_no_real_services()
        if skip_reason and test_name:
            logger = logging.getLogger(__name__)
            logger.info(f"Skipping test '{test_name}': {skip_reason}")
        return skip_reason
    except Exception:
        return ""  # Don't skip on detection errors


async def should_skip_test_without_real_llm(test_name: str = "") -> str:
    """Check if test should be skipped due to missing real LLM APIs.
    
    Args:
        test_name: Optional test name for logging
        
    Returns:
        Skip reason string or empty string if test should run
    """
    if not ServiceConfigHelper:
        return ""  # No service detection available
    
    try:
        skip_reason = await ServiceConfigHelper.skip_test_if_no_real_llm()
        if skip_reason and test_name:
            logger = logging.getLogger(__name__)
            logger.info(f"Skipping test '{test_name}': {skip_reason}")
        return skip_reason
    except Exception:
        return ""  # Don't skip on detection errors