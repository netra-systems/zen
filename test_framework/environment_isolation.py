"""
Test environment isolation utilities.

This module provides centralized utilities for managing test environment isolation,
ensuring compliance with unified_environment_management.xml specification.

Business Value: Platform/Internal - Test Stability  
Prevents test environment pollution and ensures reliable test execution.
"""
import pytest
from typing import Dict, Optional, Any
from pathlib import Path
import sys

# Add project root for imports

from dev_launcher.isolated_environment import get_env, IsolatedEnvironment


class TestEnvironmentManager:
    """
    Centralized test environment management with automatic isolation.
    
    Ensures all test environment configuration goes through IsolatedEnvironment,
    preventing global os.environ pollution.
    """
    
    # Default test environment variables
    BASE_TEST_ENV = {
        "TESTING": "1",
        "NETRA_ENV": "testing", 
        "ENVIRONMENT": "testing",
        "LOG_LEVEL": "ERROR",
        "TEST_COLLECTION_MODE": "0",
        
        # Database configuration
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "CLICKHOUSE_HOST": "localhost",
        
        # Authentication secrets
        "JWT_SECRET_KEY": "test-jwt-secret-key-for-testing-only-must-be-32-chars",
        "SERVICE_SECRET": "test-service-secret-for-cross-service-auth-32-chars-minimum-length",
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "FERNET_KEY": "iZAG-Kz661gRuJXEGzxgghUFnFRamgDrjDXZE6HdJkw=",
        "ENCRYPTION_KEY": "test-encryption-key-32-chars-long",
        
        # Service configuration
        "DEV_MODE_DISABLE_CLICKHOUSE": "true",
        "CLICKHOUSE_ENABLED": "false",
        "TEST_DISABLE_REDIS": "true",
        
        # OAuth test credentials
        "GOOGLE_CLIENT_ID": "test-google-client-id-for-integration-testing",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret-for-integration-testing",
        
        # LLM test keys
        "GEMINI_API_KEY": "test-gemini-api-key",
        "GOOGLE_API_KEY": "test-gemini-api-key",
        "OPENAI_API_KEY": "test-openai-api-key",
        "ANTHROPIC_API_KEY": "test-anthropic-api-key",
    }
    
    def __init__(self):
        """Initialize test environment manager."""
        self.env = get_env()
        self.original_state = None
        
    def setup_test_environment(
        self, 
        additional_vars: Optional[Dict[str, str]] = None,
        enable_real_llm: bool = False
    ) -> IsolatedEnvironment:
        """
        Set up isolated test environment.
        
        Args:
            additional_vars: Additional environment variables to set
            enable_real_llm: Whether to enable real LLM testing
            
        Returns:
            Configured IsolatedEnvironment instance
        """
        # Enable isolation mode
        self.env.enable_isolation(backup_original=True)
        
        # Set base test environment
        for key, value in self.BASE_TEST_ENV.items():
            self.env.set(key, value, source="test_environment_manager")
        
        # Handle real LLM testing
        if enable_real_llm:
            self._configure_real_llm()
        
        # Apply additional variables
        if additional_vars:
            for key, value in additional_vars.items():
                self.env.set(key, value, source="test_additional_vars")
        
        return self.env
    
    def _configure_real_llm(self) -> None:
        """Configure environment for real LLM testing."""
        self.env.set("ENABLE_REAL_LLM_TESTING", "true", source="test_environment_manager")
        
        # Check for real API keys
        gemini_key = self.env.get("GEMINI_API_KEY")
        if gemini_key and not gemini_key.startswith("test-"):
            # Real key available, mirror to GOOGLE_API_KEY
            self.env.set("GOOGLE_API_KEY", gemini_key, source="test_environment_manager")
        else:
            import warnings
            warnings.warn(
                "ENABLE_REAL_LLM_TESTING=true but no valid API keys found. "
                "Real LLM tests will fail.",
                stacklevel=2
            )
    
    def teardown_test_environment(self) -> None:
        """Clean up test environment and restore original state."""
        # Clear all test variables
        self.env.reset_to_original()
        
        # Disable isolation mode
        self.env.disable_isolation(restore_original=True)
    
    def get_subprocess_env(self, additional_vars: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get environment for subprocess execution.
        
        Args:
            additional_vars: Additional variables for subprocess
            
        Returns:
            Complete environment dictionary
        """
        return self.env.get_subprocess_env(additional_vars)


# Global test environment manager instance
_test_env_manager = TestEnvironmentManager()


def get_test_env_manager() -> TestEnvironmentManager:
    """Get the global test environment manager instance."""
    return _test_env_manager


# Pytest fixtures for automatic test isolation
@pytest.fixture(scope="session")
def isolated_test_session():
    """
    Session-scoped fixture for test environment isolation.
    
    Sets up isolated environment for entire test session.
    """
    manager = get_test_env_manager()
    env = manager.setup_test_environment()
    
    yield env
    
    # Cleanup after all tests
    manager.teardown_test_environment()


@pytest.fixture(scope="function")
def isolated_test_env():
    """
    Function-scoped fixture for test environment isolation.
    
    Provides fresh isolated environment for each test.
    """
    env = get_env()
    
    # Backup current state
    original_isolation = env.is_isolation_enabled()
    original_vars = env.get_all().copy()
    
    # Enable isolation
    env.enable_isolation()
    
    # Set test environment
    manager = get_test_env_manager()
    for key, value in manager.BASE_TEST_ENV.items():
        env.set(key, value, source="isolated_test_env_fixture")
    
    yield env
    
    # Restore original state
    if original_isolation:
        # Was already isolated, just restore vars
        env._isolated_vars = original_vars
    else:
        # Restore and disable isolation
        env.disable_isolation()
        for key in list(env.get_all().keys()):
            if key not in original_vars:
                env.delete(key, source="isolated_test_env_cleanup")
        for key, value in original_vars.items():
            env.set(key, value, source="isolated_test_env_restore")


@pytest.fixture
def test_env_with_llm(isolated_test_env):
    """
    Test environment with real LLM configuration.
    
    Extends isolated_test_env with real LLM API keys if available.
    """
    manager = get_test_env_manager()
    manager._configure_real_llm()
    
    return isolated_test_env


@pytest.fixture
def test_env_with_custom(isolated_test_env, request):
    """
    Test environment with custom variables.
    
    Usage:
        @pytest.mark.parametrize("test_env_with_custom", [
            {"CUSTOM_VAR": "value"}
        ], indirect=True)
        def test_something(test_env_with_custom):
            ...
    """
    custom_vars = request.param if hasattr(request, "param") else {}
    
    for key, value in custom_vars.items():
        isolated_test_env.set(key, value, source="test_env_with_custom")
    
    return isolated_test_env


# Helper functions for common test patterns
def with_test_environment(func):
    """
    Decorator to run function with isolated test environment.
    
    Usage:
        @with_test_environment
        def test_something():
            # Test code here
            pass
    """
    def wrapper(*args, **kwargs):
        manager = get_test_env_manager()
        env = manager.setup_test_environment()
        
        try:
            return func(*args, **kwargs)
        finally:
            manager.teardown_test_environment()
    
    return wrapper


def ensure_test_isolation():
    """
    Ensure test isolation is enabled.
    
    Call this at the start of test modules to guarantee isolation.
    """
    env = get_env()
    if not env.is_isolation_enabled():
        env.enable_isolation()
        
        # Set basic test environment
        manager = get_test_env_manager()
        for key, value in manager.BASE_TEST_ENV.items():
            env.set(key, value, source="ensure_test_isolation")