"""
Environment Isolation for Testing.

This module provides environment isolation capabilities for tests,
ensuring that test environments don't interfere with each other
and with production environments.
"""

import logging
import os
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, Optional, Set, Callable, Generator
from unittest.mock import patch

logger = logging.getLogger(__name__)


# =============================================================================
# TEST ENVIRONMENT MANAGER
# =============================================================================

class EnvironmentTestManager:
    """
    Manages isolated environment variables for testing.
    
    This class provides environment isolation for tests, ensuring that
    environment variable changes don't leak between tests or to production.
    """
    
    def __init__(self):
        self.env = None
        self.original_env = {}
        self.isolated_vars: Set[str] = set()
        self.isolation_enabled = False
        self._lock = threading.Lock()
        
        # Initialize with isolated environment
        try:
            from shared.isolated_environment import get_env
            self.env = get_env()
            if hasattr(self.env, 'enable_isolation'):
                self.env.enable_isolation()
                self.isolation_enabled = True
        except ImportError:
            # Fallback to basic environment wrapper
            self.env = EnvironmentWrapper()
    
    def enable_isolation(self):
        """Enable environment isolation for tests."""
        with self._lock:
            if not self.isolation_enabled:
                if hasattr(self.env, 'enable_isolation'):
                    self.env.enable_isolation()
                self.isolation_enabled = True
                logger.debug("Environment isolation enabled")
    
    def disable_isolation(self):
        """Disable environment isolation."""
        with self._lock:
            if self.isolation_enabled:
                if hasattr(self.env, 'disable_isolation'):
                    self.env.disable_isolation()
                self.isolation_enabled = False
                logger.debug("Environment isolation disabled")
    
    def save_env_var(self, key: str):
        """Save original value of environment variable."""
        if key not in self.original_env:
            self.original_env[key] = os.environ.get(key)
            self.isolated_vars.add(key)
    
    def restore_env_vars(self):
        """Restore all saved environment variables."""
        for key in self.isolated_vars:
            original_value = self.original_env.get(key)
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
        
        self.original_env.clear()
        self.isolated_vars.clear()
    
    def set_test_var(self, key: str, value: str, source: str = "test"):
        """Set environment variable for testing."""
        self.save_env_var(key)
        if self.env:
            self.env.set(key, value, source)
        else:
            os.environ[key] = value
    
    def get_test_var(self, key: str, default: Any = None) -> Any:
        """Get environment variable value."""
        if self.env:
            return self.env.get(key, default)
        return os.environ.get(key, default)
    
    def delete_test_var(self, key: str, source: str = "test"):
        """Delete environment variable."""
        self.save_env_var(key)
        if self.env and hasattr(self.env, 'delete'):
            self.env.delete(key, source)
        else:
            os.environ.pop(key, None)


class EnvironmentWrapper:
    """
    Fallback environment wrapper when isolated_environment is not available.
    """
    
    def __init__(self):
        self._vars: Dict[str, str] = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get environment variable value."""
        return self._vars.get(key, os.environ.get(key, default))
    
    def set(self, key: str, value: str, source: str = "wrapper"):
        """Set environment variable."""
        self._vars[key] = value
        os.environ[key] = value
    
    def delete(self, key: str, source: str = "wrapper"):
        """Delete environment variable."""
        self._vars.pop(key, None)
        os.environ.pop(key, None)
    
    def enable_isolation(self):
        """Enable isolation (no-op for wrapper)."""
        pass
    
    def disable_isolation(self):
        """Disable isolation (no-op for wrapper)."""
        pass


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_test_env_manager: Optional[EnvironmentTestManager] = None
_manager_lock = threading.Lock()


def get_test_env_manager() -> EnvironmentTestManager:
    """Get or create the global test environment manager."""
    global _test_env_manager
    
    if _test_env_manager is None:
        with _manager_lock:
            if _test_env_manager is None:
                _test_env_manager = EnvironmentTestManager()
    
    return _test_env_manager


# =============================================================================
# SESSION AND TEST ISOLATION
# =============================================================================

@dataclass
class IsolatedSession:
    """Represents an isolated test session."""
    session_id: str
    temp_dir: str
    env_vars: Dict[str, str]
    cleanup_funcs: list
    
    def cleanup(self):
        """Clean up session resources."""
        for cleanup_func in reversed(self.cleanup_funcs):
            try:
                cleanup_func()
            except Exception as e:
                logger.warning(f"Session cleanup error: {e}")
        
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory {self.temp_dir}: {e}")


@contextmanager
def isolated_test_session(session_id: str = None) -> Generator[IsolatedSession, None, None]:
    """
    Create an isolated test session with its own environment and temporary directory.
    
    Args:
        session_id: Optional session identifier
        
    Yields:
        IsolatedSession: The isolated session
    """
    if session_id is None:
        import uuid
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    
    # Create temporary directory for session
    temp_dir = tempfile.mkdtemp(prefix=f"netra_test_{session_id}_")
    
    # Create session
    session = IsolatedSession(
        session_id=session_id,
        temp_dir=temp_dir,
        env_vars={},
        cleanup_funcs=[]
    )
    
    # Set up environment isolation
    manager = get_test_env_manager()
    manager.enable_isolation()
    
    # Set session-specific environment variables
    session_env_vars = {
        "TEST_SESSION_ID": session_id,
        "TEST_TEMP_DIR": temp_dir,
        "TEST_ISOLATION": "1",
        "NETRA_ENV": "testing",
        "ENVIRONMENT": "testing"
    }
    
    for key, value in session_env_vars.items():
        manager.set_test_var(key, value, f"session_{session_id}")
        session.env_vars[key] = value
    
    try:
        logger.info(f"Created isolated test session: {session_id}")
        yield session
    finally:
        # Clean up session
        session.cleanup()
        
        # Restore environment
        manager.restore_env_vars()
        logger.info(f"Cleaned up isolated test session: {session_id}")


@contextmanager
def isolated_test_env(**env_vars) -> Generator[EnvironmentTestManager, None, None]:
    """
    Create an isolated environment for a single test.
    
    Args:
        **env_vars: Environment variables to set for the test
        
    Yields:
        EnvironmentTestManager: The environment manager
    """
    manager = get_test_env_manager()
    manager.enable_isolation()
    
    # Set test-specific environment variables
    for key, value in env_vars.items():
        manager.set_test_var(key, str(value), "isolated_test")
    
    try:
        yield manager
    finally:
        # Restore environment
        manager.restore_env_vars()


# =============================================================================
# ENVIRONMENT SETUP HELPERS
# =============================================================================

def ensure_test_isolation():
    """Ensure that test environment isolation is enabled."""
    manager = get_test_env_manager()
    manager.enable_isolation()
    
    # Set basic test environment variables
    test_vars = {
        "TESTING": "1",
        "ENVIRONMENT": "testing",
        "NETRA_ENV": "testing",
        "LOG_LEVEL": "INFO"
    }
    
    for key, value in test_vars.items():
        if not manager.get_test_var(key):
            manager.set_test_var(key, value, "test_isolation")


def setup_mock_environment():
    """Set up a mock environment for testing."""
    manager = get_test_env_manager()
    manager.enable_isolation()
    
    mock_vars = {
        "USE_REAL_SERVICES": "false",
        "SKIP_SERVICE_HEALTH_CHECK": "true", 
        "TEST_DISABLE_CLICKHOUSE": "true",
        "TEST_DISABLE_REDIS": "true",
        "TEST_DISABLE_POSTGRES": "true",
        "MOCK_MODE": "true"
    }
    
    for key, value in mock_vars.items():
        manager.set_test_var(key, value, "mock_environment")
    
    logger.info("Mock environment configured")


def setup_real_services_environment():
    """Set up environment for real services testing."""
    manager = get_test_env_manager()
    manager.enable_isolation()
    
    real_service_vars = {
        "USE_REAL_SERVICES": "true",
        "SKIP_MOCKS": "true",
        "TEST_DISABLE_CLICKHOUSE": "false",
        "TEST_DISABLE_REDIS": "false", 
        "TEST_DISABLE_POSTGRES": "false",
        "CLICKHOUSE_ENABLED": "true"
    }
    
    for key, value in real_service_vars.items():
        manager.set_test_var(key, value, "real_services_environment")
    
    logger.info("Real services environment configured")


# =============================================================================
# ENVIRONMENT PATCHES
# =============================================================================

@contextmanager
def patch_environment(**env_vars):
    """
    Context manager to temporarily patch environment variables.
    
    Args:
        **env_vars: Environment variables to patch
        
    Yields:
        None
    """
    patches = []
    
    for key, value in env_vars.items():
        patcher = patch.dict(os.environ, {key: str(value)})
        patches.append(patcher)
        patcher.start()
    
    try:
        yield
    finally:
        for patcher in reversed(patches):
            patcher.stop()


def create_test_environment_patch(env_vars: Dict[str, str]):
    """
    Create a patch for environment variables that can be used as a decorator.
    
    Args:
        env_vars: Environment variables to patch
        
    Returns:
        patch.dict: The environment patch
    """
    return patch.dict(os.environ, env_vars)


# =============================================================================
# SECURITY HELPERS
# =============================================================================

def setup_test_security_environment():
    """Set up secure environment variables for testing."""
    manager = get_test_env_manager()
    
    security_vars = {
        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-long-for-testing-only",
        "SERVICE_SECRET": "test-service-secret-32-characters-long-for-cross-service-auth",
        "FERNET_KEY": "test-fernet-key-for-encryption-32-characters-long-base64-encoded=",
        "ENCRYPTION_KEY": "test-encryption-key-32-chars-long",
        "GOOGLE_CLIENT_ID": "test-google-client-id",
        "GOOGLE_CLIENT_SECRET": "test-google-client-secret",
        # OAuth Test Environment Credentials (required by CentralConfigurationValidator)
        "GOOGLE_OAUTH_CLIENT_ID_TEST": "test-oauth-client-id-for-automated-testing",
        "GOOGLE_OAUTH_CLIENT_SECRET_TEST": "test-oauth-client-secret-for-automated-testing",
        "GEMINI_API_KEY": "test-gemini-api-key",
        "GOOGLE_API_KEY": "test-google-api-key",
        "ANTHROPIC_API_KEY": "test-anthropic-api-key",
        "OPENAI_API_KEY": "test-openai-api-key"
    }
    
    for key, value in security_vars.items():
        manager.set_test_var(key, value, "test_security")
    
    logger.debug("Test security environment configured")


def validate_test_environment():
    """Validate that test environment is properly configured."""
    manager = get_test_env_manager()
    
    required_vars = [
        "TESTING",
        "ENVIRONMENT", 
        "JWT_SECRET_KEY",
        "SERVICE_SECRET"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not manager.get_test_var(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise RuntimeError(f"Missing required test environment variables: {missing_vars}")
    
    # Validate environment value
    env_value = manager.get_test_var("ENVIRONMENT")
    if env_value not in ["testing", "test"]:
        logger.warning(f"ENVIRONMENT is '{env_value}', expected 'testing' or 'test'")
    
    logger.debug("Test environment validation passed")


# =============================================================================
# LEGACY COMPATIBILITY FUNCTIONS REMOVED
# Use ensure_test_isolation() and setup_test_security_environment() directly
# =============================================================================


# =============================================================================
# EXPORT ALL FUNCTIONS AND CLASSES
# =============================================================================

__all__ = [
    # Main classes
    'EnvironmentTestManager',
    'EnvironmentWrapper',
    'IsolatedSession',
    
    # Global instance
    'get_test_env_manager',
    
    # Context managers
    'isolated_test_session',
    'isolated_test_env',
    'patch_environment',
    
    # Setup helpers
    'ensure_test_isolation',
    'setup_mock_environment',
    'setup_real_services_environment',
    'setup_test_security_environment',
    
    # Legacy compatibility
    # 'setup_test_environment', # Legacy compatibility removed
    # 'teardown_test_environment', # Legacy compatibility removed
    
    # Validation
    'validate_test_environment',
    
    # Patches
    'create_test_environment_patch'
]