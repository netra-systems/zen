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
        """Initialize services dictionary if not provided."""
        if self.services is None:
            self.services = {
                "backend": {
                    "url": self.api_base_url,
                    "port": 8000,
                    "health_endpoint": "/health"
                },
                "auth": {
                    "url": self.auth_service_url,
                    "port": 8001,
                    "health_endpoint": "/health"
                },
                "websocket": {
                    "url": self.websocket_url,
                    "port": 8000,
                    "path": "/websocket"
                }
            }
    
    @classmethod
    def from_env(cls, env_name: str = "test") -> "TestEnvironmentConfig":
        """Create config from environment variables."""
        config = cls(name=env_name)
        
        # Override from environment variables
        if api_url := os.getenv("NETRA_API_URL"):
            config.api_base_url = api_url
            
        if ws_url := os.getenv("NETRA_WEBSOCKET_URL"):
            config.websocket_url = ws_url
            
        if auth_url := os.getenv("NETRA_AUTH_URL"):
            config.auth_service_url = auth_url
            
        if pg_url := os.getenv("DATABASE_URL"):
            config.postgres_url = pg_url
            
        if ch_url := os.getenv("CLICKHOUSE_URL"):
            config.clickhouse_url = ch_url
            
        if redis_url := os.getenv("REDIS_URL"):
            config.redis_url = redis_url
            
        # Feature flags
        config.use_real_llm = os.getenv("USE_REAL_LLM", "false").lower() == "true"
        config.use_real_database = os.getenv("USE_REAL_DATABASE", "false").lower() == "true"
        config.enable_monitoring = os.getenv("ENABLE_MONITORING", "false").lower() == "true"
        
        return config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "api_base_url": self.api_base_url,
            "websocket_url": self.websocket_url,
            "auth_service_url": self.auth_service_url,
            "services": self.services,
            "postgres_url": self.postgres_url,
            "clickhouse_url": self.clickhouse_url,
            "redis_url": self.redis_url,
            "test_user_email": self.test_user_email,
            "test_user_password": self.test_user_password,
            "connection_timeout": self.connection_timeout,
            "request_timeout": self.request_timeout,
            "websocket_timeout": self.websocket_timeout,
            "use_real_llm": self.use_real_llm,
            "use_real_database": self.use_real_database,
            "enable_monitoring": self.enable_monitoring,
        }


def get_test_config(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test configuration for specified environment."""
    return TestEnvironmentConfig.from_env(env_name)


def get_test_environment_config(env_name: str = "test") -> TestEnvironmentConfig:
    """Get test environment configuration for specified environment."""
    return TestEnvironmentConfig.from_env(env_name)