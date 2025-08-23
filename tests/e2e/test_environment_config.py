"""Test Environment Configuration

Provides configuration for E2E test environments.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


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
    
    # Feature flags
    use_real_llm: bool = False
    use_real_database: bool = False
    enable_monitoring: bool = False


def get_test_environment_config(environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Get test environment configuration.
    
    Args:
        environment: Optional environment type override
        
    Returns:
        TestEnvironmentConfig for the specified environment
    """
    # Auto-detect environment if not specified
    if environment is None:
        env_var = os.getenv("TEST_ENVIRONMENT", "test").lower()
        environment = TestEnvironmentType.TEST if env_var == "test" else TestEnvironmentType.DEV
    
    # Environment-specific configurations
    if environment == TestEnvironmentType.TEST:
        return TestEnvironmentConfig(
            environment=TestEnvironmentType.TEST,
            services=ServiceUrls(
                backend="http://localhost:8000",
                auth="http://localhost:8001",
                frontend="http://localhost:3000",
                websocket="ws://localhost:8000/ws"
            ),
            database=DatabaseConfig(
                url=os.getenv("TEST_DATABASE_URL", "postgresql://test:test@localhost:5432/test_db"),
                redis_url=os.getenv("TEST_REDIS_URL", "redis://localhost:6379"),
                clickhouse_url=os.getenv("TEST_CLICKHOUSE_URL", "clickhouse://localhost:8123")
            ),
            use_real_database=False
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
                url=os.getenv("DATABASE_URL", "postgresql://dev:dev@localhost:5432/dev_db"),
                redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
                clickhouse_url=os.getenv("CLICKHOUSE_URL", "clickhouse://localhost:8123")
            ),
            use_real_database=True
        )
    
    elif environment == TestEnvironmentType.STAGING:
        return TestEnvironmentConfig(
            environment=TestEnvironmentType.STAGING,
            services=ServiceUrls(
                backend=os.getenv("STAGING_API_URL", "https://staging.netra.ai"),
                auth=os.getenv("STAGING_AUTH_URL", "https://auth.staging.netra.ai"),
                frontend=os.getenv("STAGING_FRONTEND_URL", "https://staging.netra.ai"),
                websocket=os.getenv("STAGING_WS_URL", "wss://staging.netra.ai/ws")
            ),
            database=DatabaseConfig(
                url=os.getenv("STAGING_DATABASE_URL", "postgresql://staging:staging@localhost:5432/staging_db"),
                redis_url=os.getenv("STAGING_REDIS_URL", "redis://localhost:6379"),
                clickhouse_url=os.getenv("STAGING_CLICKHOUSE_URL", "clickhouse://localhost:8123")
            ),
            use_real_database=True,
            use_real_llm=True
        )
    
    else:
        # Default to local/test configuration
        return get_test_environment_config(TestEnvironmentType.TEST)


def get_test_config(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test configuration for specified environment name."""
    env_map = {
        "test": TestEnvironmentType.TEST,
        "dev": TestEnvironmentType.DEV,
        "staging": TestEnvironmentType.STAGING,
        "production": TestEnvironmentType.PRODUCTION
    }
    env_type = env_map.get(env_name, TestEnvironmentType.TEST)
    return get_test_environment_config(env_type)