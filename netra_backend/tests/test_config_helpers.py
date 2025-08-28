"""Test Configuration Helpers - Unified Config System Integration

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Zero configuration-related test failures
- Value Impact: Prevents $12K MRR loss from config inconsistencies
- Strategic Impact: Ensures all tests use unified configuration system

This module provides helper functions for tests to access configuration
through the unified system while maintaining test isolation.

Each function ≤8 lines, file ≤300 lines.
"""

from typing import Any, Dict, Optional
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from netra_backend.app.core.isolated_environment import get_env

# Import unified configuration system
try:
    from netra_backend.app.config import get_config, reload_config
    from netra_backend.app.core.configuration.base import get_unified_config
except ImportError:
    # Fallback for when running from within netra_backend directory
    import sys
    from pathlib import Path
    from netra_backend.app.config import get_config, reload_config
    from netra_backend.app.core.configuration.base import get_unified_config


def get_test_config():
    """Get configuration for tests using unified system.
    
    **PREFERRED METHOD**: Use this in tests that need app config.
    Ensures tests use the same config system as production.
    """
    return get_unified_config()


def with_test_config_override(config_overrides: Dict[str, Any]):
    """Context manager to temporarily override config for tests.
    
    Args:
        config_overrides: Dictionary of config attributes to override
        
    Usage:
        with with_test_config_override({"debug": True}):
            config = get_test_config()
            assert config.debug is True
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get original config
            original_config = get_test_config()
            
            # Apply overrides temporarily
            for key, value in config_overrides.items():
                setattr(original_config, key, value)
            
            try:
                return func(*args, **kwargs)
            finally:
                # Reload config to restore original state
                reload_config(force=True)
        return wrapper
    return decorator


@pytest.fixture
def test_config():
    """Pytest fixture providing unified config for tests."""
    return get_test_config()


@pytest.fixture  
def clean_test_config():
    """Pytest fixture ensuring clean config state for each test."""
    # Force reload to ensure clean state
    reload_config(force=True)
    config = get_test_config()
    yield config
    # Clean up after test
    reload_config(force=True)


@pytest.fixture
def mock_config_env_vars():
    """Pytest fixture for mocking environment variables safely.
    
    **IMPORTANT**: Use this instead of direct os.environ access in tests.
    Ensures proper cleanup and isolation between tests.
    """
    env_manager = get_env()
    original_env = env_manager.get_all()
    
    def set_env_var(key: str, value: str):
        """Set environment variable for test duration."""
        env_manager.set(key, value, "test_config_helpers")
        
    def get_env_var(key: str, default: Optional[str] = None) -> Optional[str]:
        """Get environment variable safely."""
        return env_manager.get(key, default)
        
    yield {
        'set': set_env_var,
        'get': get_env_var,
        'environ': env_manager.get_all()
    }
    
    # Restore original environment
    env_manager.clear()
    env_manager.update(original_env, "test_config_helpers_restore")
    # Reload config to pick up environment changes
    reload_config(force=True)


def assert_config_uses_unified_system():
    """Assertion helper to verify config is using unified system.
    
    Use in tests to ensure unified config integration.
    """
    config = get_test_config()
    assert hasattr(config, 'environment'), "Config missing environment attribute"
    assert hasattr(config, 'database_url'), "Config missing database_url attribute"
    # Verify it's from unified system by checking config type
    try:
        from netra_backend.app.schemas.config import AppConfig
    except ImportError:
        from netra_backend.app.schemas.config import AppConfig
    assert isinstance(config, AppConfig), "Config not from unified system"


def get_test_database_config() -> Dict[str, str]:
    """Get database configuration for tests using unified system."""
    config = get_test_config()
    return {
        'database_url': config.database_url,
        'redis_url': getattr(config, 'redis_url', 'redis://localhost:6379/0'),
        'environment': config.environment
    }


def get_test_llm_config() -> Dict[str, Any]:
    """Get LLM configuration for tests using unified system.""" 
    config = get_test_config()
    env_manager = get_env()
    return {
        'llm_configs': getattr(config, 'llm_configs', {}),
        'enable_real_llm': env_manager.get('ENABLE_REAL_LLM_TESTING') == 'true'
    }


def skip_if_not_test_environment():
    """Pytest skip decorator for tests requiring test environment."""
    config = get_test_config()
    return pytest.mark.skipif(
        config.environment != 'testing',
        reason="Test requires testing environment"
    )


def skip_if_no_database():
    """Pytest skip decorator for tests requiring database."""
    config = get_test_config()
    return pytest.mark.skipif(
        not config.database_url,
        reason="Test requires database configuration"
    )


def require_unified_config(func):
    """Decorator to ensure test function uses unified config system.
    
    Adds assertion at start of test to verify unified config usage.
    """
    def wrapper(*args, **kwargs):
        assert_config_uses_unified_system()
        return func(*args, **kwargs)
    return wrapper


# Test validation helpers
def validate_test_config_consistency():
    """Validate that test configuration is consistent and complete."""
    config = get_test_config()
    issues = []
    
    # Check required attributes
    required_attrs = ['environment', 'database_url']
    for attr in required_attrs:
        if not hasattr(config, attr):
            issues.append(f"Missing required config attribute: {attr}")
    
    # Check environment is appropriate for testing
    if hasattr(config, 'environment') and config.environment not in ['testing', 'development']:
        issues.append(f"Unexpected environment for tests: {config.environment}")
    
    return issues


class ConfigValidatorHelper:
    """Helper class for validating test configuration patterns."""
    
    def __init__(self):
        self.config = get_test_config()
    
    def is_test_environment(self) -> bool:
        """SSOT: Check test environment via centralized utils."""
        from netra_backend.app.core.project_utils import is_test_environment
        return is_test_environment()
    
    def has_database_config(self) -> bool:
        """Check if database is configured."""
        return bool(getattr(self.config, 'database_url', None))
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get summary of current test configuration."""
        return {
            'environment': self.config.environment,
            'has_database': self.has_database_config(),
            'database_url_set': bool(getattr(self.config, 'database_url', None)),
            'config_type': type(self.config).__name__
        }