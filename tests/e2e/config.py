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
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

# Import IsolatedEnvironment per CLAUDE.md requirements
from test_framework.environment_isolation import get_env

# Import dynamic port manager for port allocation
try:
    from tests.e2e.dynamic_port_manager import get_port_manager, TestMode
except ImportError:
    # Fallback if import fails
    get_port_manager = None
    TestMode = None


class CustomerTier(Enum):
    """Customer tier enumeration for testing"""
    FREE = "free"
    EARLY = "early" 
    MID = "mid"
    ENTERPRISE = "enterprise"


class TestEnvironmentType(Enum):
    """Test environment types"""
    LOCAL = "local"
    DEV = "dev"
    STAGING = "staging"
    
    
@dataclass
class TestServices:
    """Test service URLs"""
    auth: str
    backend: str
    frontend: str = "http://localhost:3000"
    
    
@dataclass
class TestEnvironmentConfig:
    """Test environment configuration"""
    environment_type: TestEnvironmentType
    base_url: str
    ws_url: str
    auth_url: str
    services: TestServices
    redis_host: str = "localhost"
    redis_port: int = 6379
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123


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
    
    @property
    def auth_service_url(self) -> str:
        """Get auth service URL for backward compatibility"""
        return self.endpoints.auth_base
    
    @property
    def backend_service_url(self) -> str:
        """Get backend service URL for backward compatibility"""
        return self.endpoints.api_base
    
    def _setup_environment(self) -> None:
        """Setup test environment variables using IsolatedEnvironment"""
        # Use IsolatedEnvironment per CLAUDE.md unified_environment_management.xml
        env = get_env()
        env.enable_isolation()
        
        test_env = self._get_base_test_env()
        for key, value in test_env.items():
            env.set(key, value, source="unified_test_config")
    
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
        # Use the backend JWT secret if set, otherwise use test default - via IsolatedEnvironment
        env = get_env()
        jwt_secret = env.get("JWT_SECRET_KEY", "rsWwwvq8X6mCSuNv-TMXHDCfb96Xc-Dbay9MZy6EDCU")
        fernet_key = "cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao="
        encryption_key = "test-encryption-key-32-chars-long"
        self._set_secret_env_vars(jwt_secret, fernet_key, encryption_key)
        return TestSecrets(jwt_secret, fernet_key, encryption_key)
    
    def _set_secret_env_vars(self, jwt: str, fernet: str, encrypt: str) -> None:
        """Set secret environment variables using IsolatedEnvironment"""
        env = get_env()
        env.set("JWT_SECRET_KEY", jwt, source="test_secrets")
        env.set("FERNET_KEY", fernet, source="test_secrets")
        env.set("ENCRYPTION_KEY", encrypt, source="test_secrets")
        # Set additional test secrets
        env.set("GOOGLE_CLIENT_ID", "test-google-client-id", source="test_secrets")
        env.set("GOOGLE_CLIENT_SECRET", "test-google-client-secret", source="test_secrets")
        
        # REMOVED: Mock API key fallbacks are forbidden per CLAUDE.md
        # Configuration must require real API keys from environment
        # If GEMINI_API_KEY is missing, system should fail explicitly
    
    def _create_test_endpoints(self) -> TestEndpoints:
        """Create test endpoint configuration"""
        # Use dynamic port manager if available
        if get_port_manager:
            port_mgr = get_port_manager()
            urls = port_mgr.get_service_urls()
            ws_url = urls["websocket"]
            api_base = urls["backend"]
            auth_base = urls["auth"]
        else:
            # Fallback to environment or defaults (Docker uses 8081 for auth)
            env = get_env()
            backend_port = env.get("TEST_BACKEND_PORT", "8000")
            auth_port = env.get("TEST_AUTH_PORT", "8081")  # Docker default
            ws_url = f"ws://localhost:{backend_port}/ws"
            api_base = f"http://localhost:{backend_port}"
            auth_base = f"http://localhost:{auth_port}"
        # Set environment variables for service discovery using IsolatedEnvironment
        env = get_env()
        env.set("AUTH_SERVICE_URL", auth_base, source="test_endpoints")
        env.set("BACKEND_SERVICE_URL", api_base, source="test_endpoints")
        return TestEndpoints(ws_url, api_base, auth_base)
    
    def _create_test_users(self) -> Dict[str, TestUser]:
        """Create test users for all tiers"""
        users = {}
        for tier in CustomerTier:
            user = self._create_tier_user(tier)
            users[tier.value] = user
        return users
    
    def _create_tier_user(self, tier: CustomerTier) -> TestUser:
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
    
    @staticmethod
    def create_jwt_token(user_id: str, email: str = None) -> str:
        """Create JWT token for testing"""
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        jwt_helper = JWTTestHelper()
        email = email or f"{user_id}@test.com"
        return jwt_helper.create_access_token(user_id, email)


class TestTokenManager:
    """Manager for test JWT tokens"""
    
    def __init__(self, secrets: TestSecrets):
        """Initialize with test secrets"""
        self.secrets = secrets
    
    def create_test_token(self, user_data: Dict[str, Any]) -> str:
        """Create test JWT token"""
        try:
            # Since create_access_token is async, we fall back to mock token in this sync context
            # The test should use an async token manager if real tokens are needed
            return f"mock-token-{user_data['id']}"
        except (ImportError, Exception):
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


def get_test_environment_config(env_type: TestEnvironmentType = TestEnvironmentType.LOCAL, environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Get test environment configuration for specified environment type"""
    # Support both parameter names for backward compatibility
    target_env = environment or env_type
    if target_env == TestEnvironmentType.LOCAL:
        # Use dynamic port manager for local testing
        if get_port_manager:
            port_mgr = get_port_manager()
            urls = port_mgr.get_service_urls()
            return TestEnvironmentConfig(
                environment_type=TestEnvironmentType.LOCAL,
                base_url=urls["backend"],
                ws_url=urls["websocket"],
                auth_url=urls["auth"],
                services=TestServices(
                    auth=urls["auth"],
                    backend=urls["backend"],
                    frontend=urls["frontend"]
                ),
                postgres_port=port_mgr.ports.postgres,
                redis_port=port_mgr.ports.redis,
                clickhouse_port=port_mgr.ports.clickhouse
            )
        else:
            # Fallback to defaults (Docker uses 8081 for auth)
            env = get_env()
            backend_port = int(env.get("TEST_BACKEND_PORT", "8000"))
            auth_port = int(env.get("TEST_AUTH_PORT", "8081"))  # Docker default
            frontend_port = int(env.get("TEST_FRONTEND_PORT", "3000"))
            return TestEnvironmentConfig(
                environment_type=TestEnvironmentType.LOCAL,
                base_url=f"http://localhost:{backend_port}",
                ws_url=f"ws://localhost:{backend_port}/ws",
                auth_url=f"http://localhost:{auth_port}",
                services=TestServices(
                    auth=f"http://localhost:{auth_port}",
                    backend=f"http://localhost:{backend_port}",
                    frontend=f"http://localhost:{frontend_port}"
                )
            )
    elif target_env == TestEnvironmentType.DEV:
        return TestEnvironmentConfig(
            environment_type=TestEnvironmentType.DEV,
            base_url="https://dev.netra-apex.com",
            ws_url="wss://dev.netra-apex.com/ws",
            auth_url="https://auth-dev.netra-apex.com",
            services=TestServices(
                auth="https://auth-dev.netra-apex.com",
                backend="https://dev.netra-apex.com",
                frontend="https://dev.netra-apex.com"
            )
        )
    elif target_env == TestEnvironmentType.STAGING:
        # Import SSOT for staging URLs
        from netra_backend.app.core.network_constants import URLConstants
        return TestEnvironmentConfig(
            environment_type=TestEnvironmentType.STAGING,
            base_url=URLConstants.STAGING_BACKEND_URL,
            ws_url=URLConstants.STAGING_WEBSOCKET_URL,
            auth_url=URLConstants.STAGING_AUTH_URL,
            services=TestServices(
                auth=URLConstants.STAGING_AUTH_URL,
                backend=URLConstants.STAGING_BACKEND_URL,
                frontend=URLConstants.STAGING_FRONTEND_URL
            )
        )
    else:
        raise ValueError(f"Unknown environment type: {env_type}")


def get_auth_service_url() -> str:
    """Get the auth service URL."""
    # Check if already set in environment via IsolatedEnvironment
    env = get_env()
    auth_url = env.get("AUTH_SERVICE_URL")
    if auth_url:
        return auth_url
    # Try to get from port manager
    if get_port_manager:
        port_mgr = get_port_manager()
        urls = port_mgr.get_service_urls()
        return urls["auth"]
    # Fallback to default (Docker uses 8081 for auth)
    env = get_env()
    auth_port = env.get("TEST_AUTH_PORT", "8081")  # Docker default
    return f"http://localhost:{auth_port}"


def get_backend_service_url() -> str:
    """Get the backend service URL."""
    # Check if already set in environment via IsolatedEnvironment
    env = get_env()
    backend_url = env.get("BACKEND_SERVICE_URL")
    if backend_url:
        return backend_url
    # Try to get from port manager
    if get_port_manager:
        port_mgr = get_port_manager()
        urls = port_mgr.get_service_urls()
        return urls["backend"]
    # Fallback to default
    env = get_env()
    backend_port = env.get("TEST_BACKEND_PORT", "8000")
    return f"http://localhost:{backend_port}"


def get_test_config() -> UnifiedTestConfig:
    """Get the unified test configuration instance."""
    return TEST_CONFIG