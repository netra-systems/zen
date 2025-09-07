"""E2E Test Configuration - SSOT for test settings

This module provides configuration and utilities for E2E testing.
Implements SSOT patterns for test environment management.

Business Value Justification (BVJ):
- Segment: Internal/Platform stability
- Business Goal: Enable reliable E2E testing across environments
- Value Impact: Ensures test consistency and deployment reliability
- Revenue Impact: Protects release quality and customer experience
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import os

from shared.isolated_environment import IsolatedEnvironment


# Test secrets for authentication testing
TEST_SECRETS = {
    "JWT_SECRET_KEY": "test_jwt_secret_key_for_e2e_testing_only",
    "AUTH_SERVICE_SECRET": "test_auth_service_secret",
    "ENCRYPTION_KEY": "test_encryption_key_32_bytes_long"
}

# Test users for E2E testing
TEST_USERS = {
    "free": {
        "id": "test_free_user",
        "email": "test_free_user@test.example.com",
        "tier": "free"
    },
    "early": {
        "id": "test_early_user",
        "email": "test_early_user@test.example.com",
        "tier": "early"
    },
    "mid": {
        "id": "test_mid_user",
        "email": "test_mid_user@test.example.com",
        "tier": "mid"
    },
    "enterprise": {
        "id": "test_enterprise_user",
        "email": "test_enterprise_user@test.example.com",
        "tier": "enterprise"
    }
}


class CustomerTier(str, Enum):
    """Customer tier definitions for testing."""
    FREE = "free"
    EARLY = "early" 
    MID = "mid"
    ENTERPRISE = "enterprise"


@dataclass
class UnifiedTestConfig:
    """Unified test configuration."""
    environment: str = "test"
    use_real_services: bool = True
    use_real_llm: bool = False
    timeout_seconds: float = 30.0
    max_retries: int = 3
    customer_tier: CustomerTier = CustomerTier.FREE
    debug_mode: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestUser:
    """Test user data structure."""
    id: str
    email: str
    tier: CustomerTier
    metadata: Dict[str, Any] = field(default_factory=dict)


def get_test_config() -> UnifiedTestConfig:
    """Get test configuration from environment."""
    env = IsolatedEnvironment()
    
    return UnifiedTestConfig(
        environment=env.get("TEST_ENVIRONMENT", "test"),
        use_real_services=env.get_bool("USE_REAL_SERVICES", True),
        use_real_llm=env.get_bool("USE_REAL_LLM", False),
        timeout_seconds=env.get_float("TEST_TIMEOUT", 30.0),
        debug_mode=env.get_bool("DEBUG_MODE", False)
    )


def get_test_user(tier: CustomerTier = CustomerTier.FREE) -> TestUser:
    """Get a test user for the specified tier."""
    test_id = f"test_user_{tier.value}_{int(__import__('time').time())}"
    
    return TestUser(
        id=test_id,
        email=f"{test_id}@test.example.com", 
        tier=tier,
        metadata={
            "created_for_testing": True,
            "tier": tier.value
        }
    )


def get_service_urls() -> Dict[str, str]:
    """Get service URLs for testing."""
    env = IsolatedEnvironment()
    
    return {
        "backend": env.get("BACKEND_URL", "http://localhost:8000"),
        "auth": env.get("AUTH_SERVICE_URL", "http://localhost:8081"), 
        "frontend": env.get("FRONTEND_URL", "http://localhost:3000"),
        "websocket": env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
    }


def get_database_urls() -> Dict[str, str]:
    """Get database URLs for testing."""
    env = IsolatedEnvironment()
    
    return {
        "postgres": env.get("POSTGRES_URL", "postgresql://postgres:netra@localhost:5432/netra_test"),
        "redis": env.get("REDIS_URL", "redis://localhost:6379/0"),
        "clickhouse": env.get("CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_test")
    }


class TestTokenManager:
    """Test token manager for authentication testing."""
    
    def __init__(self):
        """Initialize test token manager."""
        self.env = IsolatedEnvironment()
        self.tokens: Dict[str, Dict[str, Any]] = {}
    
    def generate_test_token(self, user_id: str, permissions: Optional[List[str]] = None) -> str:
        """Generate a test JWT token."""
        import time
        import uuid
        
        token_id = str(uuid.uuid4())
        self.tokens[token_id] = {
            "user_id": user_id,
            "permissions": permissions or [],
            "created_at": time.time(),
            "expires_at": time.time() + 3600  # 1 hour
        }
        return f"test_jwt_{token_id}"
    
    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a test token."""
        if not token.startswith("test_jwt_"):
            return None
        
        token_id = token[9:]  # Remove "test_jwt_" prefix
        return self.tokens.get(token_id)
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a test token."""
        if not token.startswith("test_jwt_"):
            return False
        
        token_id = token[9:]
        if token_id in self.tokens:
            del self.tokens[token_id]
            return True
        return False


# Dictionary-style TEST_CONFIG for backward compatibility
# Tests expect this format for accessing URLs and settings
TEST_CONFIG = {
    # Service URLs (test environment)
    "auth_service_url": "http://localhost:8081",
    "backend_url": "http://localhost:8000",
    "frontend_url": "http://localhost:3000",
    "websocket_url": "ws://localhost:8000/ws",
    
    # Staging URLs (for staging environment)
    "staging_auth_url": "https://auth-staging.netra.ai",
    "staging_backend_url": "https://api-staging.netra.ai",
    "staging_frontend_url": "https://app-staging.netra.ai",
    "staging_websocket_url": "wss://api-staging.netra.ai/ws",
    
    # Database URLs
    "postgres_url": "postgresql://postgres:netra@localhost:5434/netra_test",
    "redis_url": "redis://localhost:6381/0",
    "clickhouse_url": "clickhouse://localhost:8123/netra_test",
    
    # Test configuration
    "timeout": 30.0,
    "max_retries": 3,
    "debug_mode": False,
    "use_real_services": True,
    "use_real_llm": False,
}


# Additional missing classes and functions expected by tests
class DatabaseTestManager:
    """Test database manager for E2E testing."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize test database manager."""
        self.config = config or TEST_CONFIG
        self.env = IsolatedEnvironment()
    
    def get_postgres_url(self) -> str:
        """Get PostgreSQL URL for testing."""
        return self.env.get("TEST_POSTGRES_URL", self.config["postgres_url"])
    
    def get_redis_url(self) -> str:
        """Get Redis URL for testing."""
        return self.env.get("TEST_REDIS_URL", self.config["redis_url"])
    
    def get_clickhouse_url(self) -> str:
        """Get ClickHouse URL for testing."""
        return self.env.get("TEST_CLICKHOUSE_URL", self.config["clickhouse_url"])


class TestDataFactory:
    """Test data factory for generating test data."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize test data factory."""
        self.config = config or TEST_CONFIG
    
    def create_test_user_data(self, tier: CustomerTier = CustomerTier.FREE) -> Dict[str, Any]:
        """Create test user data."""
        return {
            "id": f"test_user_{tier.value}_{int(__import__('time').time())}",
            "email": f"test_{tier.value}@test.example.com",
            "tier": tier.value,
            "permissions": ["chat", "agents"] if tier != CustomerTier.FREE else ["chat"]
        }
    
    def create_test_message_data(self) -> Dict[str, Any]:
        """Create test message data."""
        return {
            "id": str(__import__('uuid').uuid4()),
            "content": "Test message for E2E testing",
            "type": "user_message",
            "timestamp": __import__('time').time()
        }


# Test endpoints for service health checks
TEST_ENDPOINTS = {
    "auth_health": "/health",
    "backend_health": "/health",
    "frontend_health": "/",
    "websocket_health": "/ws/health"
}


def get_test_environment_config() -> Dict[str, Any]:
    """Get test environment configuration."""
    env = IsolatedEnvironment()
    environment = env.get("TEST_ENVIRONMENT", "test")
    
    if environment == "staging":
        return {
            "auth_url": TEST_CONFIG["staging_auth_url"],
            "backend_url": TEST_CONFIG["staging_backend_url"],
            "frontend_url": TEST_CONFIG["staging_frontend_url"],
            "websocket_url": TEST_CONFIG["staging_websocket_url"],
        }
    else:
        return {
            "auth_url": TEST_CONFIG["auth_service_url"],
            "backend_url": TEST_CONFIG["backend_url"],
            "frontend_url": TEST_CONFIG["frontend_url"],
            "websocket_url": TEST_CONFIG["websocket_url"],
        }


class TestEnvironmentType(str, Enum):
    """Test environment types."""
    LOCAL = "local"
    STAGING = "staging" 
    PRODUCTION = "production"