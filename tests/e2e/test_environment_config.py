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
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class TestEnvironmentConfig:
    """Configuration for test environments."""
    
    name: str = "test"
    api_base_url: str = "http://localhost:8000"
    websocket_url: str = "ws://localhost:8000/websocket"
    auth_service_url: str = "http://localhost:8001"
    
    # Service configurations
    services: Dict[str, Dict[str, Any]] = None
    
    # Database configurations
    postgres_url: Optional[str] = None
    clickhouse_url: Optional[str] = None
    redis_url: str = "redis://localhost:6379"
    
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
    
    def __post_init__(self):
        """Post-init processing."""
        if self.services is None:
            self.services = {}


class TestEnvironment:
    """Test environment manager."""
    
    def __init__(self, env_type: TestEnvironmentType = TestEnvironmentType.LOCAL):
        self.env_type = env_type
        self.config = self._create_config(env_type)
    
    def _create_config(self, env_type: TestEnvironmentType) -> TestEnvironmentConfig:
        """Create configuration based on environment type."""
        configs = {
            TestEnvironmentType.LOCAL: TestEnvironmentConfig(
                name="local",
                api_base_url="http://localhost:8000",
                websocket_url="ws://localhost:8000/ws",
                auth_service_url="http://localhost:8001"
            ),
            TestEnvironmentType.DEV: TestEnvironmentConfig(
                name="dev",
                api_base_url=os.getenv("DEV_API_URL", "http://localhost:8000"),
                websocket_url=os.getenv("DEV_WS_URL", "ws://localhost:8000/ws"),
                auth_service_url=os.getenv("DEV_AUTH_URL", "http://localhost:8001"),
                use_real_database=True
            ),
            TestEnvironmentType.STAGING: TestEnvironmentConfig(
                name="staging", 
                api_base_url=os.getenv("STAGING_API_URL", "https://staging.netra.ai"),
                websocket_url=os.getenv("STAGING_WS_URL", "wss://staging.netra.ai/ws"),
                auth_service_url=os.getenv("STAGING_AUTH_URL", "https://auth.staging.netra.ai"),
                use_real_database=True,
                use_real_llm=True
            ),
            TestEnvironmentType.PRODUCTION: TestEnvironmentConfig(
                name="production",
                api_base_url=os.getenv("PROD_API_URL", "https://api.netra.ai"),
                websocket_url=os.getenv("PROD_WS_URL", "wss://api.netra.ai/ws"),
                auth_service_url=os.getenv("PROD_AUTH_URL", "https://auth.netra.ai"),
                use_real_database=True,
                use_real_llm=True,
                enable_monitoring=True
            )
        }
        return configs[env_type]
    
    def get_config(self) -> TestEnvironmentConfig:
        """Get environment configuration."""
        return self.config


def get_test_config(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test configuration for specified environment."""
    return TestEnvironmentConfig(name=env_name)


def get_test_environment_config(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test environment configuration for specified environment."""
    return TestEnvironmentConfig(name=env_name)