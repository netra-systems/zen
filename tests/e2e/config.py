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
    env = IsolatedEnvironment(service_name="test_e2e_config")
    
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
    env = IsolatedEnvironment(service_name="test_e2e_urls")
    
    return {
        "backend": env.get("BACKEND_URL", "http://localhost:8000"),
        "auth": env.get("AUTH_SERVICE_URL", "http://localhost:8081"), 
        "frontend": env.get("FRONTEND_URL", "http://localhost:3000"),
        "websocket": env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
    }


def get_database_urls() -> Dict[str, str]:
    """Get database URLs for testing."""
    env = IsolatedEnvironment(service_name="test_e2e_db")
    
    return {
        "postgres": env.get("POSTGRES_URL", "postgresql://postgres:netra@localhost:5432/netra_test"),
        "redis": env.get("REDIS_URL", "redis://localhost:6379/0"),
        "clickhouse": env.get("CLICKHOUSE_URL", "clickhouse://localhost:8123/netra_test")
    }


class TestTokenManager:
    """Test token manager for authentication testing."""
    
    def __init__(self):
        """Initialize test token manager."""
        self.env = IsolatedEnvironment(service_name="test_token_manager")
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