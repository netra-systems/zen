"""
Test Environment Configuration
Manages environment variables and configuration for auth service tests.
Ensures test isolation and proper cleanup of environment state.
"""

import os
import tempfile
from typing import Dict, Any, Optional
from contextlib import contextmanager
from pathlib import Path

from auth_core.config import AuthConfig


class TestEnvironment:
    """Test environment management with isolation"""
    
    # Default test environment variables
    DEFAULT_TEST_ENV = {
        "ENVIRONMENT": "test",
        "JWT_SECRET": "test-jwt-secret-key-that-is-long-enough-for-testing-purposes-and-very-secure",
        "JWT_ALGORITHM": "HS256",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "15",
        "REFRESH_TOKEN_EXPIRE_DAYS": "7",
        
        # Database
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "TEST_DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        
        # Redis
        "REDIS_URL": "redis://localhost:6379/15",  # Use test database
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "REDIS_DB": "15",
        
        # OAuth Configuration
        "GOOGLE_CLIENT_ID": "test-google-client-id.apps.googleusercontent.com",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
        "GITHUB_CLIENT_ID": "test-github-client-id",
        "GITHUB_CLIENT_SECRET": "test-github-client-secret",
        
        # Service URLs
        "AUTH_SERVICE_URL": "http://localhost:8081",
        "FRONTEND_URL": "http://localhost:3000",
        "BACKEND_URL": "http://localhost:8000",
        
        # Test-specific settings
        "TESTING": "true",
        "DEBUG": "true",
        "LOG_LEVEL": "INFO",
        
        # Security
        "CORS_ORIGINS": "http://localhost:3000,http://localhost:3001",
        "ALLOWED_HOSTS": "localhost,127.0.0.1,0.0.0.0",
        
        # Rate limiting (disabled for tests)
        "RATE_LIMITING_ENABLED": "false",
        "MAX_LOGIN_ATTEMPTS": "10",
        "ACCOUNT_LOCKOUT_DURATION": "300",
    }
    
    def __init__(self, custom_env: Dict[str, str] = None):
        self.custom_env = custom_env or {}
        self.original_env = {}
        self.temp_files = []
    
    def setup(self):
        """Setup test environment variables"""
        # Combine default and custom environment
        test_env = {**self.DEFAULT_TEST_ENV, **self.custom_env}
        
        # Store original values for restoration
        for key, value in test_env.items():
            self.original_env[key] = os.environ.get(key)
            os.environ[key] = value
    
    def teardown(self):
        """Restore original environment variables"""
        for key, original_value in self.original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        
        # Clean up temporary files
        for temp_file in self.temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception:
                pass  # Best effort cleanup
        
        self.temp_files.clear()
    
    @contextmanager
    def isolated_environment(self):
        """Context manager for isolated test environment"""
        self.setup()
        try:
            yield self
        finally:
            self.teardown()
    
    def create_temp_config_file(self, config_data: Dict[str, Any]) -> Path:
        """Create temporary configuration file"""
        temp_file = Path(tempfile.mktemp(suffix='.yaml'))
        self.temp_files.append(temp_file)
        
        import yaml
        with open(temp_file, 'w') as f:
            yaml.dump(config_data, f)
        
        return temp_file
    
    def create_temp_env_file(self, env_vars: Dict[str, str]) -> Path:
        """Create temporary .env file"""
        temp_file = Path(tempfile.mktemp(suffix='.env'))
        self.temp_files.append(temp_file)
        
        with open(temp_file, 'w') as f:
            for key, value in env_vars.items():
                f.write(f"{key}={value}\n")
        
        return temp_file
    
    def get_test_database_url(self, use_file: bool = False) -> str:
        """Get test database URL"""
        if use_file:
            # Create temporary SQLite file
            temp_db = Path(tempfile.mktemp(suffix='.db'))
            self.temp_files.append(temp_db)
            return f"sqlite+aiosqlite:///{temp_db}"
        
        return "sqlite+aiosqlite:///:memory:"
    
    def override_config(self, **kwargs):
        """Override specific configuration values"""
        for key, value in kwargs.items():
            env_key = key.upper()
            self.custom_env[env_key] = str(value)
            if env_key in os.environ or env_key in self.DEFAULT_TEST_ENV:
                os.environ[env_key] = str(value)


def load_test_config() -> AuthConfig:
    """Load test configuration with proper environment setup"""
    # Ensure test environment is set
    if os.getenv("ENVIRONMENT") != "test":
        test_env = TestEnvironment()
        test_env.setup()
    
    return AuthConfig


class EnvironmentPresets:
    """Predefined environment configurations for different test scenarios"""
    
    @staticmethod
    def unit_test_env() -> TestEnvironment:
        """Environment for unit tests - minimal setup"""
        return TestEnvironment({
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "REDIS_URL": "redis://localhost:6379/15",
            "LOG_LEVEL": "WARNING",  # Reduce noise in unit tests
        })
    
    @staticmethod
    def integration_test_env() -> TestEnvironment:
        """Environment for integration tests - full setup"""
        return TestEnvironment({
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "REDIS_URL": "redis://localhost:6379/15",
            "LOG_LEVEL": "INFO",
            "DEBUG": "true",
        })
    
    @staticmethod
    def e2e_test_env() -> TestEnvironment:
        """Environment for E2E tests - production-like"""
        return TestEnvironment({
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "REDIS_URL": "redis://localhost:6379/15",
            "LOG_LEVEL": "DEBUG",
            "DEBUG": "true",
            "CORS_ORIGINS": "*",  # Allow all origins for E2E tests
        })
    
    @staticmethod
    def postgres_test_env() -> TestEnvironment:
        """Environment for PostgreSQL integration tests"""
        return TestEnvironment({
            "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/test_auth_service",
            "REDIS_URL": "redis://localhost:6379/15",
            "LOG_LEVEL": "INFO",
        })
    
    @staticmethod
    def oauth_test_env() -> TestEnvironment:
        """Environment for OAuth testing"""
        return TestEnvironment({
            "GOOGLE_CLIENT_ID": "test-oauth-client-id",
            "GOOGLE_CLIENT_SECRET": "test-oauth-secret",
            "GITHUB_CLIENT_ID": "test-github-client-id", 
            "GITHUB_CLIENT_SECRET": "test-github-secret",
            "OAUTH_REDIRECT_URL": "http://localhost:8081/auth/callback",
        })


def get_test_environment(test_type: str = "unit") -> TestEnvironment:
    """Get predefined test environment by type"""
    presets = {
        "unit": EnvironmentPresets.unit_test_env,
        "integration": EnvironmentPresets.integration_test_env,
        "e2e": EnvironmentPresets.e2e_test_env,
        "postgres": EnvironmentPresets.postgres_test_env,
        "oauth": EnvironmentPresets.oauth_test_env,
    }
    
    if test_type not in presets:
        raise ValueError(f"Unknown test type: {test_type}")
    
    return presets[test_type]()