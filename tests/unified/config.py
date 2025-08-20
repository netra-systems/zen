"""Unified Test Configuration Manager

Phase 1 implementation for managing configuration across all unified tests.
Provides consistent environment variables, JWT secrets, WebSocket URLs,
test users for all tiers, and fixture factories.

Business Value Justification (BVJ):
- Segment: All customer tiers (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable testing infrastructure for value creation features
- Value Impact: Prevents production bugs that could impact customer trust and conversion
- Revenue Impact: Testing reliability directly supports revenue protection

Architecture:
- 450-line file limit enforced through modular design
- 25-line function limit for all functions
- Independent test configuration from main application
- Supports all customer tier testing scenarios
"""

import os
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum


class TestTier(Enum):
    """Customer tier enumeration for testing"""
    FREE = "free"
    EARLY = "early" 
    MID = "mid"
    ENTERPRISE = "enterprise"


@dataclass
class TestUser:
    """Test user data structure"""
    id: str
    email: str
    full_name: str
    plan_tier: str
    is_active: bool = True
    is_superuser: bool = False


@dataclass 
class TestSecrets:
    """Test JWT and encryption secrets"""
    jwt_secret: str
    fernet_key: str
    encryption_key: str


@dataclass
class TestEndpoints:
    """Test endpoint configuration"""
    ws_url: str
    api_base: str
    auth_base: str


class UnifiedTestConfig:
    """Main unified test configuration manager"""
    
    def __init__(self):
        """Initialize test configuration"""
        self._setup_environment()
        self.secrets = self._create_test_secrets()
        self.endpoints = self._create_test_endpoints()
        self.users = self._create_test_users()
    
    def _setup_environment(self) -> None:
        """Setup test environment variables"""
        test_env = self._get_base_test_env()
        for key, value in test_env.items():
            os.environ[key] = value
    
    def _get_base_test_env(self) -> Dict[str, str]:
        """Get base test environment variables"""
        core_env = self._get_core_env()
        db_env = self._get_db_env()
        return {**core_env, **db_env}
    
    def _get_core_env(self) -> Dict[str, str]:
        """Get core environment settings"""
        return {
            "TESTING": "1",
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "WARNING",
            "AUTH_FAST_TEST_MODE": "true",
            "CORS_ORIGINS": "*",
            "SECURE_HEADERS_ENABLED": "false"
        }
    
    def _get_db_env(self) -> Dict[str, str]:
        """Get database environment settings"""
        return {
            "REDIS_HOST": "localhost",
            "CLICKHOUSE_HOST": "localhost",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "CLICKHOUSE_URL": "clickhouse://localhost:8123",
            "REDIS_URL": "redis://localhost:6379/0"
        }
    
    def _create_test_secrets(self) -> TestSecrets:
        """Create test JWT and encryption secrets"""
        jwt_secret = "test-jwt-secret-key-unified-testing-32chars"
        fernet_key = "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao="
        encryption_key = "test-encryption-key-32-chars-long"
        self._set_secret_env_vars(jwt_secret, fernet_key, encryption_key)
        return TestSecrets(jwt_secret, fernet_key, encryption_key)
    
    def _set_secret_env_vars(self, jwt: str, fernet: str, encrypt: str) -> None:
        """Set secret environment variables"""
        os.environ["JWT_SECRET_KEY"] = jwt
        os.environ["FERNET_KEY"] = fernet
        os.environ["ENCRYPTION_KEY"] = encrypt
        # Set additional test secrets
        os.environ["GOOGLE_CLIENT_ID"] = "test-google-client-id"
        os.environ["GOOGLE_CLIENT_SECRET"] = "test-google-client-secret"
        os.environ["GEMINI_API_KEY"] = "test-gemini-api-key"
    
    def _create_test_endpoints(self) -> TestEndpoints:
        """Create test endpoint configuration"""
        ws_url = "ws://localhost:8000/ws"
        api_base = "http://localhost:8000"
        auth_base = "http://localhost:8001"
        # Set environment variables for service discovery
        os.environ["AUTH_SERVICE_URL"] = auth_base
        os.environ["BACKEND_SERVICE_URL"] = api_base
        return TestEndpoints(ws_url, api_base, auth_base)
    
    def _create_test_users(self) -> Dict[str, TestUser]:
        """Create test users for all tiers"""
        users = {}
        for tier in TestTier:
            user = self._create_tier_user(tier)
            users[tier.value] = user
        return users
    
    def _create_tier_user(self, tier: TestTier) -> TestUser:
        """Create test user for specific tier"""
        user_id = f"test-{tier.value}-{str(uuid.uuid4())[:8]}"
        email = f"test-{tier.value}@unified-test.com"
        full_name = f"Test {tier.value.title()} User"
        return TestUser(user_id, email, full_name, tier.value)


class TestDataFactory:
    """Factory for creating consistent test data"""
    
    @staticmethod
    def create_message_data(user_id: str, content: str) -> Dict[str, Any]:
        """Create test message data"""
        return {
            "user_id": user_id,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message_id": str(uuid.uuid4())
        }
    
    @staticmethod
    def create_websocket_auth(token: str) -> Dict[str, str]:
        """Create WebSocket auth headers"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    
    @staticmethod
    def create_api_headers(token: str) -> Dict[str, str]:
        """Create API request headers"""
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    @staticmethod
    def create_plan_data(tier: str) -> Dict[str, Any]:
        """Create test plan data"""
        expires = TestDataFactory._get_plan_expiry()
        plan_info = TestDataFactory._get_plan_info(tier, expires)
        return plan_info
    
    @staticmethod
    def _get_plan_expiry() -> datetime:
        """Get plan expiry date"""
        return datetime.now(timezone.utc) + timedelta(days=30)
    
    @staticmethod
    def _get_plan_info(tier: str, expires: datetime) -> Dict[str, Any]:
        """Get plan information dictionary"""
        return {
            "plan_tier": tier,
            "plan_expires_at": expires.isoformat(),
            "auto_renew": True,
            "payment_status": "active"
        }


class TestTokenManager:
    """Manager for test JWT tokens"""
    
    def __init__(self, secrets: TestSecrets):
        """Initialize with test secrets"""
        self.secrets = secrets
    
    def create_test_token(self, user_data: Dict[str, Any]) -> str:
        """Create test JWT token"""
        try:
            from app.auth_integration.auth import create_access_token
            return create_access_token(data={"sub": user_data["email"]})
        except ImportError:
            return f"mock-token-{user_data['id']}"
    
    def create_user_token(self, user: TestUser) -> str:
        """Create token for test user"""
        user_data = {"id": user.id, "email": user.email}
        return self.create_test_token(user_data)


class TestDatabaseManager:
    """Manager for test database operations"""
    
    @staticmethod
    def get_memory_db_url() -> str:
        """Get in-memory database URL"""
        return "sqlite+aiosqlite:///:memory:"
    
    @staticmethod
    def get_test_db_config() -> Dict[str, Any]:
        """Get test database configuration"""
        return {
            "url": TestDatabaseManager.get_memory_db_url(),
            "echo": False,
            "pool_pre_ping": True,
            "pool_recycle": 300
        }
    
    @staticmethod
    def create_test_session_config() -> Dict[str, Any]:
        """Create test session configuration"""
        return {
            "autocommit": False,
            "autoflush": False,
            "expire_on_commit": False
        }


def create_unified_config() -> UnifiedTestConfig:
    """Factory function to create unified test configuration"""
    return UnifiedTestConfig()


def get_test_user(tier: str, config: Optional[UnifiedTestConfig] = None) -> TestUser:
    """Get test user for specified tier"""
    if config is None:
        config = create_unified_config()
    return config.users.get(tier)


def get_test_endpoints(config: Optional[UnifiedTestConfig] = None) -> TestEndpoints:
    """Get test endpoints configuration"""
    if config is None:
        config = create_unified_config()
    return config.endpoints


def setup_test_environment() -> UnifiedTestConfig:
    """Setup complete test environment"""
    config = create_unified_config()
    return config


# Global test configuration instance
TEST_CONFIG = create_unified_config()

# Convenient exports for direct access
TEST_USERS = TEST_CONFIG.users
TEST_SECRETS = TEST_CONFIG.secrets
TEST_ENDPOINTS = TEST_CONFIG.endpoints