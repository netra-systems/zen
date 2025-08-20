"""Configuration for E2E tests in unified/e2e directory."""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class TestUser:
    """Test user data structure."""
    id: str
    email: str
    role: str = "user"


# Test users for different segments
TEST_USERS = {
    "free": TestUser(id="test_user_free", email="free@test.com", role="user"),
    "early": TestUser(id="test_user_early", email="early@test.com", role="user"), 
    "mid": TestUser(id="test_user_mid", email="mid@test.com", role="user"),
    "enterprise": TestUser(id="test_user_enterprise", email="enterprise@test.com", role="admin")
}


# Test configuration
TEST_CONFIG = {
    "redis_enabled": False,  # Set to False for environments without Redis
    "auth_service_url": "http://localhost:8001",
    "websocket_timeout": 30.0,
    "token_expiry_seconds": 3600,
    "reconnection_timeout": 2.0,
    "performance_thresholds": {
        "reconnection_time": 2.0,
        "token_validation_time": 0.1,
        "connection_time": 1.0
    }
}