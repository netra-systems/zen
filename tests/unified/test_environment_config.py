"""Unified Test Environment Configuration Module

Centralizes environment configuration for all unified tests across test, dev, and staging environments.
Provides consistent environment detection, service URLs, database connections, and test utilities.

Business Value Justification (BVJ):
- Segment: Platform/Internal - All customer tiers
- Business Goal: Testing reliability and infrastructure stability
- Value Impact: Prevents configuration-related test failures that could mask production issues
- Revenue Impact: Testing infrastructure stability enables faster deployment cycles

Architecture:
- Single source of truth for test environment configuration
- Environment-aware configuration with fallbacks
- Supports test isolation and concurrent test execution
- Integrates with existing configuration patterns

Usage Examples:
    # Basic usage - automatically detects environment
    from tests.unified.test_environment_config import get_test_environment_config
    config = get_test_environment_config()
    
    # Access configuration properties
    print(f"Environment: {config.environment.value}")
    print(f"Database URL: {config.database.url}")
    print(f"Backend URL: {config.services.backend}")
    
    # Force specific environment
    test_config = get_test_environment_config(environment="test")
    staging_config = get_test_environment_config(environment="staging")
    
    # Convenience functions
    from tests.unified.test_environment_config import (
        is_test_environment,
        get_service_urls,
        setup_test_environment
    )
    
    if is_test_environment():
        print("Running in test mode!")
    
    urls = get_service_urls()
    full_config = setup_test_environment()  # Sets up and validates everything

Integration with Existing Tests:
    This module complements the existing tests/unified/config.py module.
    Use this for environment-specific configuration, and the existing config.py
    for test users, tokens, and test data factories.
"""

import os
import sys
from typing import Dict, Any, Optional, Union, Literal
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import from existing modules following established patterns
from app.core.auth_constants import (
    JWTConstants, 
    CredentialConstants, 
    AuthConstants
)

# Environment types
TestEnvironmentType = Literal["test", "dev", "staging", "production"]


class TestEnvironment(Enum):
    """Test environment enumeration."""
    TEST = "test"
    DEV = "dev" 
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration for test environments."""
    url: str
    echo: bool = False
    pool_pre_ping: bool = True
    pool_recycle: int = 300
    
    @classmethod
    def for_environment(cls, env: TestEnvironment) -> "DatabaseConfig":
        """Create database config for specific environment."""
        if env == TestEnvironment.TEST:
            return cls(
                url="sqlite+aiosqlite:///:memory:",
                echo=False
            )
        elif env == TestEnvironment.DEV:
            # Use environment-specific default, but allow override via DATABASE_URL
            default_url = "postgresql://postgres:password@localhost:5432/netra_dev"
            return cls(
                url=os.getenv(CredentialConstants.DATABASE_URL, default_url),
                echo=True
            )
        elif env == TestEnvironment.STAGING:
            # Use environment-specific default, but allow override via DATABASE_URL
            default_url = "postgresql://postgres:password@staging:5432/netra_staging"
            return cls(
                url=os.getenv(CredentialConstants.DATABASE_URL, default_url),
                echo=False
            )
        else:
            raise ValueError(f"Unsupported environment: {env}")


@dataclass
class ServiceUrls:
    """Service URL configuration for test environments."""
    backend: str
    frontend: str
    auth: str
    websocket: str
    
    @classmethod 
    def for_environment(cls, env: TestEnvironment) -> "ServiceUrls":
        """Create service URLs for specific environment."""
        if env == TestEnvironment.TEST:
            return cls(
                backend="http://localhost:8000",
                frontend="http://localhost:3000", 
                auth="http://localhost:8001",
                websocket="ws://localhost:8000/ws"
            )
        elif env == TestEnvironment.DEV:
            return cls(
                backend="http://localhost:8000",
                frontend="http://localhost:3000",
                auth="http://localhost:8001", 
                websocket="ws://localhost:8000/ws"
            )
        elif env == TestEnvironment.STAGING:
            return cls(
                backend="https://api-staging.netra.app",
                frontend="https://staging.netra.app",
                auth="https://auth-staging.netra.app",
                websocket="wss://api-staging.netra.app/ws"
            )
        else:
            raise ValueError(f"Unsupported environment: {env}")


@dataclass
class TestSecrets:
    """Test secrets configuration."""
    jwt_secret_key: str
    fernet_key: str
    google_client_id: str
    google_client_secret: str
    gemini_api_key: str
    
    @classmethod
    def for_environment(cls, env: TestEnvironment) -> "TestSecrets":
        """Create test secrets for specific environment."""
        if env == TestEnvironment.TEST:
            return cls(
                jwt_secret_key="test-jwt-secret-key-unified-testing-32chars",
                fernet_key="cYpHdJm0e-zt3SWz-9h0gC_kh0Z7c3H6mRQPbPLFdao=",
                google_client_id="test-google-client-id",
                google_client_secret="test-google-client-secret",
                gemini_api_key="test-gemini-api-key"
            )
        else:
            # For dev/staging, use environment variables or fallbacks
            return cls(
                jwt_secret_key=os.getenv(JWTConstants.JWT_SECRET_KEY, "test-jwt-secret-fallback"),
                fernet_key=os.getenv(JWTConstants.FERNET_KEY, "test-fernet-key-fallback"),
                google_client_id=os.getenv(CredentialConstants.GOOGLE_CLIENT_ID, "test-google-client-id"),
                google_client_secret=os.getenv(CredentialConstants.GOOGLE_CLIENT_SECRET, "test-google-client-secret"),
                gemini_api_key=os.getenv(CredentialConstants.GEMINI_API_KEY, "test-gemini-api-key")
            )


class TestEnvironmentConfig:
    """Unified test environment configuration manager.
    
    Provides centralized configuration for all unified tests with environment-aware settings.
    """
    
    def __init__(self, environment: Optional[TestEnvironmentType] = None):
        """Initialize test environment configuration.
        
        Args:
            environment: Optional environment override. If not provided, will be detected.
        """
        self._environment = self._detect_environment(environment)
        self._service_urls = ServiceUrls.for_environment(self._environment)
        self._test_secrets = TestSecrets.for_environment(self._environment)
        # Create temporary database config for environment variable setup
        self._database_config = DatabaseConfig.for_environment(self._environment)
        self._setup_environment_variables()
        # Recreate database config after environment variables are set up to pick up any changes
        self._database_config = DatabaseConfig.for_environment(self._environment)
    
    @property
    def environment(self) -> TestEnvironment:
        """Get current test environment."""
        return self._environment
    
    @property 
    def database(self) -> DatabaseConfig:
        """Get database configuration."""
        return self._database_config
    
    @property
    def services(self) -> ServiceUrls:
        """Get service URLs configuration."""
        return self._service_urls
    
    @property
    def secrets(self) -> TestSecrets:
        """Get test secrets configuration."""
        return self._test_secrets
    
    def _detect_environment(self, override: Optional[TestEnvironmentType]) -> TestEnvironment:
        """Detect current test environment.
        
        Args:
            override: Optional environment override
            
        Returns:
            Detected test environment
        """
        if override:
            return TestEnvironment(override)
        
        # Check for testing indicators
        if self._is_test_environment():
            return TestEnvironment.TEST
        
        # Check environment variable
        env_var = os.getenv("ENVIRONMENT", "").lower()
        if env_var in ["staging", "stage"]:
            return TestEnvironment.STAGING
        elif env_var in ["production", "prod"]:
            return TestEnvironment.PRODUCTION
        else:
            return TestEnvironment.DEV
    
    def _is_test_environment(self) -> bool:
        """Check if running in test environment."""
        return (
            os.getenv("TESTING") == "1" or
            os.getenv("testing") == "1" or
            os.getenv(AuthConstants.TESTING_FLAG) == "true" or
            AuthConstants.PYTEST_CURRENT_TEST in os.environ or
            "pytest" in sys.modules
        )
    
    def _setup_environment_variables(self) -> None:
        """Setup environment variables for test environment."""
        env_vars = self._get_base_environment_variables()
        env_vars.update(self._get_secrets_environment_variables())
        env_vars.update(self._get_service_environment_variables())
        
        for key, value in env_vars.items():
            os.environ[key] = str(value)
    
    def _get_base_environment_variables(self) -> Dict[str, Union[str, int]]:
        """Get base environment variables."""
        base_vars = {
            "ENVIRONMENT": self._environment.value,
            "LOG_LEVEL": "WARNING" if self._environment == TestEnvironment.TEST else "INFO",
            "CORS_ORIGINS": "*",
            "SECURE_HEADERS_ENABLED": "false"
        }
        
        if self._environment == TestEnvironment.TEST:
            base_vars.update({
                "TESTING": "1",
                AuthConstants.AUTH_FAST_TEST_MODE: "true"
            })
        
        return base_vars
    
    def _get_secrets_environment_variables(self) -> Dict[str, str]:
        """Get secrets environment variables."""
        return {
            JWTConstants.JWT_SECRET_KEY: self._test_secrets.jwt_secret_key,
            JWTConstants.FERNET_KEY: self._test_secrets.fernet_key,
            CredentialConstants.GOOGLE_CLIENT_ID: self._test_secrets.google_client_id,
            CredentialConstants.GOOGLE_CLIENT_SECRET: self._test_secrets.google_client_secret,
            CredentialConstants.GEMINI_API_KEY: self._test_secrets.gemini_api_key,
        }
    
    def _get_service_environment_variables(self) -> Dict[str, str]:
        """Get service environment variables."""
        service_vars = {
            "BACKEND_SERVICE_URL": self._service_urls.backend,
            "FRONTEND_SERVICE_URL": self._service_urls.frontend,
            AuthConstants.AUTH_SERVICE_URL: self._service_urls.auth,
            "REDIS_URL": self._get_redis_url(),
            "CLICKHOUSE_URL": self._get_clickhouse_url()
        }
        
        # Only set DATABASE_URL for test environment to ensure in-memory database is used
        # For dev/staging, let the DatabaseConfig.for_environment method handle defaults
        if self._environment == TestEnvironment.TEST:
            service_vars[CredentialConstants.DATABASE_URL] = self._database_config.url
        
        return service_vars
    
    def _get_redis_url(self) -> str:
        """Get Redis URL for environment."""
        if self._environment == TestEnvironment.TEST:
            return "redis://localhost:6379/1"  # Use database 1 for tests
        elif self._environment == TestEnvironment.STAGING:
            return os.getenv("REDIS_URL", "redis://staging-redis:6379/0")
        else:
            return "redis://localhost:6379/0"
    
    def _get_clickhouse_url(self) -> str:
        """Get ClickHouse URL for environment."""
        if self._environment == TestEnvironment.TEST:
            return "clickhouse://localhost:8123/test"
        elif self._environment == TestEnvironment.STAGING:
            return os.getenv("CLICKHOUSE_URL", "clickhouse://staging-clickhouse:8123/staging")
        else:
            return "clickhouse://localhost:8123/netra_dev"
    
    def is_test_environment(self) -> bool:
        """Check if current environment is test."""
        return self._environment == TestEnvironment.TEST
    
    def is_dev_environment(self) -> bool:
        """Check if current environment is development."""
        return self._environment == TestEnvironment.DEV
    
    def is_staging_environment(self) -> bool:
        """Check if current environment is staging."""
        return self._environment == TestEnvironment.STAGING
    
    def is_production_environment(self) -> bool:
        """Check if current environment is production."""
        return self._environment == TestEnvironment.PRODUCTION
    
    def validate_configuration(self) -> tuple[bool, list[str]]:
        """Validate test environment configuration.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate required environment variables are set
        required_vars = [
            JWTConstants.JWT_SECRET_KEY,
            CredentialConstants.DATABASE_URL
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                errors.append(f"Required environment variable not set: {var}")
        
        # Validate service URLs are accessible (basic format check)
        if not self._service_urls.backend.startswith(("http://", "https://")):
            errors.append(f"Invalid backend URL format: {self._service_urls.backend}")
        
        if not self._service_urls.websocket.startswith(("ws://", "wss://")):
            errors.append(f"Invalid WebSocket URL format: {self._service_urls.websocket}")
        
        # Validate database URL format
        if not self._database_config.url.startswith(("sqlite", "postgresql", "mysql")):
            errors.append(f"Invalid database URL format: {self._database_config.url}")
        
        return len(errors) == 0, errors
    
    def get_test_client_config(self) -> Dict[str, Any]:
        """Get configuration for test clients.
        
        Returns:
            Dictionary with client configuration settings
        """
        return {
            "base_url": self._service_urls.backend,
            "auth_url": self._service_urls.auth,
            "websocket_url": self._service_urls.websocket,
            "timeout": 30.0 if self._environment == TestEnvironment.TEST else 60.0,
            "verify_ssl": self._environment == TestEnvironment.PRODUCTION,
            "follow_redirects": True
        }
    
    def get_test_database_session_config(self) -> Dict[str, Any]:
        """Get database session configuration for tests.
        
        Returns:
            Dictionary with database session settings
        """
        return {
            "autocommit": False,
            "autoflush": False,
            "expire_on_commit": False,
            "isolation_level": "READ_COMMITTED" if self._environment != TestEnvironment.TEST else None
        }


# Factory functions for easy access
def get_test_environment_config(environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Get test environment configuration instance.
    
    Args:
        environment: Optional environment override
        
    Returns:
        TestEnvironmentConfig instance
    """
    return TestEnvironmentConfig(environment=environment)


def get_current_test_environment() -> TestEnvironment:
    """Get current test environment.
    
    Returns:
        Current test environment enum value
    """
    config = get_test_environment_config()
    return config.environment


def is_test_environment() -> bool:
    """Check if currently running in test environment.
    
    Returns:
        True if in test environment, False otherwise
    """
    config = get_test_environment_config()
    return config.is_test_environment()


def get_service_urls(environment: Optional[TestEnvironmentType] = None) -> ServiceUrls:
    """Get service URLs for environment.
    
    Args:
        environment: Optional environment override
        
    Returns:
        ServiceUrls instance
    """
    config = get_test_environment_config(environment=environment)
    return config.services


def get_database_config(environment: Optional[TestEnvironmentType] = None) -> DatabaseConfig:
    """Get database configuration for environment.
    
    Args:
        environment: Optional environment override
        
    Returns:
        DatabaseConfig instance
    """
    config = get_test_environment_config(environment=environment)
    return config.database


def setup_test_environment(environment: Optional[TestEnvironmentType] = None) -> TestEnvironmentConfig:
    """Setup test environment with all configurations.
    
    Args:
        environment: Optional environment override
        
    Returns:
        Configured TestEnvironmentConfig instance
    """
    config = get_test_environment_config(environment=environment)
    
    # Validate configuration
    is_valid, errors = config.validate_configuration()
    if not is_valid:
        error_msg = f"Test environment configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(error_msg)
    
    return config


# Global configuration instance for backward compatibility
_global_config: Optional[TestEnvironmentConfig] = None


def get_global_test_config() -> TestEnvironmentConfig:
    """Get global test configuration instance.
    
    Returns:
        Global TestEnvironmentConfig instance
    """
    global _global_config
    if _global_config is None:
        _global_config = get_test_environment_config()
    return _global_config


# Convenient exports
__all__ = [
    "TestEnvironment",
    "TestEnvironmentConfig", 
    "DatabaseConfig",
    "ServiceUrls",
    "TestSecrets",
    "get_test_environment_config",
    "get_current_test_environment",
    "is_test_environment", 
    "get_service_urls",
    "get_database_config",
    "setup_test_environment",
    "get_global_test_config"
]