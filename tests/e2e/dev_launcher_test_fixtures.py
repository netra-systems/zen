"""
Dev Launcher Test Fixtures

Provides TestEnvironmentManager for setting up test environments with real services.
This is a minimal implementation focused on fixing import errors.
"""

import logging
from shared.isolated_environment import get_env
from test_framework.environment_isolation import get_test_env_manager

logger = logging.getLogger(__name__)


class TestEnvironmentManager:
    """
    Test environment manager for dev launcher integration.
    
    This provides the interface expected by comprehensive websocket tests.
    """
    
    def __init__(self):
        self.env = get_env()
        self.test_env_manager = get_test_env_manager()
        self.initialized = False
        
    async def initialize(self):
        """Initialize the test environment."""
        if not self.initialized:
            self.env.enable_isolation()
            self.test_env_manager.enable_isolation()
            self.initialized = True
            logger.debug("Test environment initialized")
    
    def setup_test_db(self):
        """Setup test database configuration."""
        # Set database configuration for testing
        self.env.set("DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/test_db", "test_db")
        self.env.set("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5434/test_db", "test_db")
        self.env.set("USE_REAL_SERVICES", "true", "test_db")
        logger.debug("Test database setup completed")
    
    def setup_test_redis(self):
        """Setup test Redis configuration."""
        # Set Redis configuration for testing  
        self.env.set("REDIS_URL", "redis://localhost:6381/0", "test_redis")
        self.env.set("TEST_REDIS_URL", "redis://localhost:6381/0", "test_redis")
        self.env.set("REDIS_HOST", "localhost", "test_redis")
        self.env.set("REDIS_PORT", "6381", "test_redis")
        logger.debug("Test Redis setup completed")
    
    def setup_test_secrets(self):
        """Setup test secrets and authentication."""
        # Set test secrets
        test_secrets = {
            "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-long-for-testing-only",
            "SERVICE_SECRET": "test-service-secret-32-characters-long-for-cross-service-auth",
            "FERNET_KEY": "test-fernet-key-for-encryption-32-characters-long-base64-encoded=",
            "GOOGLE_CLIENT_ID": "test-google-client-id",
            "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
            "GEMINI_API_KEY": "test-gemini-api-key",
            "ANTHROPIC_API_KEY": "test-anthropic-api-key"
        }
        
        for key, value in test_secrets.items():
            self.env.set(key, value, "test_secrets")
            
        logger.debug("Test secrets setup completed")
    
    def cleanup(self):
        """Cleanup test environment."""
        if self.initialized:
            self.test_env_manager.restore_env_vars()
            self.env.clear()
            self.initialized = False
            logger.debug("Test environment cleanup completed")


# Export for compatibility
__all__ = ['TestEnvironmentManager']