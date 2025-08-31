"""
Test environment isolation management.

Provides isolated environment configuration for different test scenarios.
"""

import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Optional

from test_launcher.config import TestConfig, TestProfile


logger = logging.getLogger(__name__)


class TestEnvironmentManager:
    """Manages isolated test environments."""
    
    def __init__(self, config: TestConfig):
        """Initialize environment manager with test configuration."""
        self.config = config
        self.test_id = str(uuid.uuid4())[:8]
        self.original_env: Dict[str, str] = {}
        self.test_env_vars: Dict[str, str] = {}
        
    def setup(self):
        """Setup test environment variables."""
        logger.info(f"Setting up test environment for profile: {self.config.profile.value}")
        
        # Save original environment
        self.original_env = dict(os.environ)
        
        # Base test environment variables
        self.test_env_vars = {
            "TESTING": "1",
            "TEST_PROFILE": self.config.profile.value,
            "TEST_ID": self.test_id,
            "ENVIRONMENT": "test",
            "LOG_LEVEL": "DEBUG" if self.config.verbose else "INFO",
        }
        
        # Profile-specific environment
        profile_env = self._get_profile_environment()
        self.test_env_vars.update(profile_env)
        
        # Service URLs based on configuration
        service_urls = self._get_service_urls()
        self.test_env_vars.update(service_urls)
        
        # Apply environment variables
        for key, value in self.test_env_vars.items():
            os.environ[key] = value
        
        logger.debug(f"Applied {len(self.test_env_vars)} test environment variables")
    
    def _get_profile_environment(self) -> Dict[str, str]:
        """Get profile-specific environment variables."""
        env = {}
        
        if self.config.profile == TestProfile.UNIT:
            env.update({
                "USE_REAL_SERVICES": "false",
                "USE_REAL_LLM": "false",
                "DATABASE_URL": "sqlite:///:memory:",
                "REDIS_URL": "redis://mock",
                "CLICKHOUSE_URL": "http://mock",
            })
        
        elif self.config.profile in [TestProfile.INTEGRATION, TestProfile.E2E]:
            env.update({
                "USE_REAL_SERVICES": str(self.config.real_services).lower(),
                "USE_REAL_LLM": str(self.config.real_llm).lower(),
            })
            
            # Database configuration for test environment
            if self.config.real_services:
                postgres_port = self.config.services.get("postgres", {}).port or 5434
                redis_port = self.config.services.get("redis", {}).port or 6381
                clickhouse_port = self.config.services.get("clickhouse", {}).port or 8124
                
                env.update({
                    "DATABASE_URL": f"postgresql://test:test@localhost:{postgres_port}/netra_test",
                    "REDIS_URL": f"redis://localhost:{redis_port}/1",
                    "CLICKHOUSE_URL": f"http://localhost:{clickhouse_port}",
                })
        
        elif self.config.profile == TestProfile.PERFORMANCE:
            env.update({
                "PERFORMANCE_TESTING": "true",
                "DISABLE_RATE_LIMITING": "true",
                "DISABLE_CACHE_WARMING": "true",
            })
        
        elif self.config.profile == TestProfile.SECURITY:
            env.update({
                "SECURITY_TESTING": "true",
                "ENABLE_SECURITY_LOGGING": "true",
                "STRICT_MODE": "true",
            })
        
        # LLM configuration
        if self.config.real_llm:
            env.update({
                "NETRA_REAL_LLM_ENABLED": "true",
                "ENABLE_REAL_LLM_TESTING": "true",
                "TEST_LLM_MODE": "real",
                "LLM_PROVIDER": "gemini",
                "GEMINI_MODEL": "gemini-2.5-pro",
            })
        else:
            env.update({
                "NETRA_REAL_LLM_ENABLED": "false",
                "ENABLE_REAL_LLM_TESTING": "false",
                "TEST_LLM_MODE": "mock",
            })
        
        # Test secrets (never use real secrets in tests)
        env.update({
            "JWT_SECRET_KEY": f"test-jwt-secret-{self.test_id}-must-be-32-chars-minimum-length",
            "SERVICE_SECRET": f"test-service-secret-{self.test_id}-32-chars-minimum",
            "FERNET_KEY": "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=",
            "GOOGLE_CLIENT_ID": f"test-google-client-id-{self.test_id}",
            "GOOGLE_CLIENT_SECRET": f"test-google-client-secret-{self.test_id}",
        })
        
        return env
    
    def _get_service_urls(self) -> Dict[str, str]:
        """Get service URLs based on configuration."""
        urls = {}
        
        # Backend service
        if "backend" in self.config.services:
            backend_port = self.config.services["backend"].port or 8001
            urls["BACKEND_URL"] = f"http://localhost:{backend_port}"
            urls["WEBSOCKET_URL"] = f"ws://localhost:{backend_port}"
        
        # Auth service
        if "auth" in self.config.services:
            auth_port = self.config.services["auth"].port or 8082
            urls["AUTH_SERVICE_URL"] = f"http://localhost:{auth_port}"
        
        # Frontend service
        if "frontend" in self.config.services:
            frontend_port = self.config.services["frontend"].port or 3001
            urls["FRONTEND_URL"] = f"http://localhost:{frontend_port}"
        
        return urls
    
    def cleanup(self):
        """Restore original environment."""
        logger.info("Cleaning up test environment")
        
        # Remove test environment variables
        for key in self.test_env_vars:
            if key in os.environ:
                del os.environ[key]
        
        # Restore original values that were overwritten
        for key, value in self.original_env.items():
            if key not in os.environ or os.environ[key] != value:
                os.environ[key] = value
        
        logger.debug("Environment restored to original state")
    
    def get_test_data_dir(self) -> Path:
        """Get directory for test data."""
        test_data_dir = Path.cwd() / "test_data" / self.test_id
        test_data_dir.mkdir(parents=True, exist_ok=True)
        return test_data_dir
    
    def get_test_database_name(self) -> str:
        """Get unique database name for this test run."""
        return f"netra_test_{self.test_id}"
    
    def get_isolation_namespace(self) -> str:
        """Get namespace for isolated resources (e.g., Docker network)."""
        return f"test_{self.config.profile.value}_{self.test_id}"