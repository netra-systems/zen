"""
ISOLATED ENVIRONMENT TEST FIXTURES
==================================

Provides standardized test fixtures for IsolatedEnvironment usage across ALL tests.
These fixtures ensure consistent environment isolation and prevent os.environ pollution.

CRITICAL REQUIREMENTS per CLAUDE.md:
- ALL environment access must go through IsolatedEnvironment
- NO direct os.environ, os.getenv, or environment patching
- Follow unified_environment_management.xml
- Maintain test functionality while enforcing compliance

Business Value: Platform/Internal - Test Infrastructure Stability
Prevents configuration failures and ensures reliable test isolation.

Author: Claude Code - Test Infrastructure
Date: 2025-09-02
"""

import pytest
import contextlib
from typing import Dict, Optional, Any, Generator
from pathlib import Path

from shared.isolated_environment import get_env, IsolatedEnvironment

# Standard test environment configurations
STANDARD_TEST_CONFIG = {
    "TESTING": "true",
    "ENVIRONMENT": "test",
    "LOG_LEVEL": "WARNING",
    "DATABASE_URL": "postgresql://test:test@localhost:5432/netra_test",
    "CLICKHOUSE_URL": "clickhouse://localhost:9000/test",
    "REDIS_URL": "redis://localhost:6379/1",
    "JWT_SECRET_KEY": "test-secret-key-for-testing-only-must-be-at-least-32-chars",
    "FERNET_KEY": "test-fernet-key-for-testing-only-base64encode=",
    "ANTHROPIC_API_KEY": "test-api-key",
    "OPENAI_API_KEY": "test-api-key",
    "GEMINI_API_KEY": "test-api-key",
    "GOOGLE_CLIENT_ID": "test-google-client",
    "GOOGLE_CLIENT_SECRET": "test-google-secret",
    "FRONTEND_URL": "http://localhost:3000"
}

STAGING_TEST_CONFIG = {
    "TESTING": "true",
    "ENVIRONMENT": "staging",
    "LOG_LEVEL": "INFO",
    "GCP_PROJECT_ID": "netra-staging",
    "JWT_SECRET_STAGING": "staging-jwt-secret-for-testing-only-must-be-at-least-32-chars",
    "DATABASE_URL": "postgresql://postgres:staging_password@staging-db:5432/netra_staging",
    "REDIS_URL": "redis://staging-redis:6379/0"
}

PRODUCTION_TEST_CONFIG = {
    "TESTING": "true",
    "ENVIRONMENT": "production", 
    "LOG_LEVEL": "ERROR",
    "GCP_PROJECT_ID": "netra-production"
}

@pytest.fixture(scope="function")
def isolated_env() -> Generator[IsolatedEnvironment, None, None]:
    """
    Provides isolated environment for tests.
    
    This fixture ensures:
    - Environment isolation is enabled
    - Original state is restored after test
    - No pollution of os.environ during testing
    
    Usage:
        def test_something(isolated_env):
            isolated_env.set("TEST_VAR", "test_value", "test_source")
            assert isolated_env.get("TEST_VAR") == "test_value"
    """
    env = get_env()
    
    # Enable isolation and capture original state
    original_isolated = env.is_isolated()
    original_state = env.get_all() if original_isolated else None
    
    if not original_isolated:
        env.enable_isolation()
    
    try:
        yield env
    finally:
        # Restore original state with error handling
        try:
            if not original_isolated:
                env.disable_isolation()
            elif original_state is not None:
                env.reset_to_original()
        except ValueError as e:
            # Handle illegal environment variable names that can't be synced to os.environ
            # This can happen when tests create variables with invalid names
            import logging
            logging.getLogger(__name__).warning(f"Failed to restore environment state: {e}")
            # Force reset to clean state
            try:
                env.reset()
            except Exception:
                pass  # Best effort cleanup

@pytest.fixture(scope="function")
def test_env() -> Generator[IsolatedEnvironment, None, None]:
    """
    Provides isolated environment pre-configured with standard test variables.
    
    This fixture automatically sets up common test environment variables
    that most tests need, preventing duplication across test files.
    
    Usage:
        def test_with_standard_config(test_env):
            # Standard test variables are already available
            assert test_env.get("TESTING") == "true"
            assert test_env.get("DATABASE_URL").startswith("postgresql://test")
    """
    env = get_env()
    
    # Enable isolation and capture original state
    original_isolated = env.is_isolated()
    original_state = env.get_all() if original_isolated else None
    
    if not original_isolated:
        env.enable_isolation()
    
    # Apply standard test configuration
    env.update(STANDARD_TEST_CONFIG, "test_fixture_standard")
    
    try:
        yield env
    finally:
        # Restore original state
        if not original_isolated:
            env.disable_isolation()
        elif original_state is not None:
            env.reset_to_original()

@pytest.fixture(scope="function") 
def staging_env() -> Generator[IsolatedEnvironment, None, None]:
    """
    Provides isolated environment configured for staging environment testing.
    
    Usage:
        def test_staging_behavior(staging_env):
            assert staging_env.get("ENVIRONMENT") == "staging"
            assert staging_env.is_staging()
    """
    env = get_env()
    
    # Enable isolation and capture original state
    original_isolated = env.is_isolated()
    original_state = env.get_all() if original_isolated else None
    
    if not original_isolated:
        env.enable_isolation()
    
    # Apply staging test configuration
    env.update(STAGING_TEST_CONFIG, "test_fixture_staging")
    
    try:
        yield env
    finally:
        # Restore original state
        if not original_isolated:
            env.disable_isolation()
        elif original_state is not None:
            env.reset_to_original()

@pytest.fixture(scope="function")
def production_env() -> Generator[IsolatedEnvironment, None, None]:
    """
    Provides isolated environment configured for production environment testing.
    
    Usage:
        def test_production_behavior(production_env):
            assert production_env.get("ENVIRONMENT") == "production"
            assert production_env.is_production()
    """
    env = get_env()
    
    # Enable isolation and capture original state
    original_isolated = env.is_isolated()
    original_state = env.get_all() if original_isolated else None
    
    if not original_isolated:
        env.enable_isolation()
    
    # Apply production test configuration
    env.update(PRODUCTION_TEST_CONFIG, "test_fixture_production")
    
    try:
        yield env
    finally:
        # Restore original state
        if not original_isolated:
            env.disable_isolation()
        elif original_state is not None:
            env.reset_to_original()

@contextlib.contextmanager
def temporary_env_vars(env_vars: Dict[str, str], source: str = "temp_context"):
    """
    Context manager for temporarily setting environment variables.
    
    This replaces patch.dict(os.environ) usage with IsolatedEnvironment.
    
    Args:
        env_vars: Dictionary of environment variables to set
        source: Source identifier for tracking
        
    Usage:
        with temporary_env_vars({"TEST_VAR": "test_value"}):
            assert get_env().get("TEST_VAR") == "test_value"
        # TEST_VAR is automatically cleaned up
    """
    env = get_env()
    
    # Enable isolation if not already enabled
    was_isolated = env.is_isolated()
    if not was_isolated:
        env.enable_isolation()
    
    # Store original values for cleanup
    original_values = {}
    for key in env_vars:
        if env.exists(key):
            original_values[key] = env.get(key)
        else:
            original_values[key] = None
    
    # Set temporary values
    env.update(env_vars, source)
    
    try:
        yield env
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is not None:
                env.set(key, original_value, f"{source}_restore")
            else:
                env.delete(key, f"{source}_cleanup")
        
        # Restore isolation state
        if not was_isolated:
            env.disable_isolation()

@contextlib.contextmanager
def clean_env_context(clear_all: bool = False):
    """
    Context manager for tests that need a completely clean environment.
    
    This replaces patch.dict(os.environ, {}, clear=True) usage.
    
    Args:
        clear_all: If True, clears all environment variables
        
    Usage:
        with clean_env_context(clear_all=True):
            # Environment is completely clean
            assert len(get_env().get_all()) == 0
        # Original environment is restored
    """
    env = get_env()
    
    # Enable isolation if not already enabled
    was_isolated = env.is_isolated()
    original_state = env.get_all() if was_isolated else None
    
    if not was_isolated:
        env.enable_isolation()
    
    if clear_all:
        env.clear()
    
    try:
        yield env
    finally:
        # Restore original state
        if not was_isolated:
            env.disable_isolation()
        elif original_state is not None:
            env.clear()
            env.update(original_state, "clean_context_restore")

class EnvironmentPatcher:
    """
    Drop-in replacement for unittest.mock.patch.dict(os.environ) usage.
    
    This class provides the same interface as patch.dict but uses IsolatedEnvironment.
    """
    
    def __init__(self, env_vars: Dict[str, str], clear: bool = False, source: str = "env_patcher"):
        self.env_vars = env_vars
        self.clear = clear
        self.source = source
        self.env = get_env()
        self.original_values = {}
        self.was_isolated = False
    
    def __enter__(self):
        """Enter context - set up temporary environment."""
        self.was_isolated = self.env.is_isolated()
        
        if not self.was_isolated:
            self.env.enable_isolation()
        
        if self.clear:
            # Save all current values for restoration
            self.original_values = self.env.get_all()
            self.env.clear()
        else:
            # Save only values we're going to change
            for key in self.env_vars:
                if self.env.exists(key):
                    self.original_values[key] = self.env.get(key)
                else:
                    self.original_values[key] = None
        
        # Set new values
        self.env.update(self.env_vars, self.source)
        
        return self.env
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context - restore original environment."""
        if self.clear:
            # Restore complete original environment
            self.env.clear()
            if self.original_values:
                self.env.update(self.original_values, f"{self.source}_restore")
        else:
            # Restore only changed values
            for key, original_value in self.original_values.items():
                if original_value is not None:
                    self.env.set(key, original_value, f"{self.source}_restore")
                else:
                    self.env.delete(key, f"{self.source}_cleanup")
        
        # Restore isolation state
        if not self.was_isolated:
            self.env.disable_isolation()

# Convenience function for easy migration
def patch_env(env_vars: Dict[str, str], clear: bool = False, source: str = "patch_env") -> EnvironmentPatcher:
    """
    Drop-in replacement for patch.dict(os.environ, ...).
    
    Usage:
        # Old way (FORBIDDEN):
        with patch.dict(os.environ, {"TEST_VAR": "value"}):
            ...
        
        # New way (COMPLIANT):  
        with patch_env({"TEST_VAR": "value"}):
            ...
    """
    return EnvironmentPatcher(env_vars, clear, source)

# Auto-registration with pytest
def pytest_configure(config):
    """Auto-configure pytest with isolated environment fixtures."""
    # Ensure IsolatedEnvironment is available for all tests
    env = get_env()
    env.enable_isolation()

def pytest_runtest_setup(item):
    """Set up isolated environment for each test."""
    env = get_env()
    if not env.is_isolated():
        env.enable_isolation()

def pytest_runtest_teardown(item, nextitem):
    """Clean up environment after each test."""
    env = get_env()
    # Reset to clean state for next test while maintaining isolation
    if env.is_isolated():
        env.reset_to_original()