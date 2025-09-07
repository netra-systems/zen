"""
Standardized Test Environment Fixtures - SINGLE SOURCE OF TRUTH

This module provides standardized fixtures for test environment management,
replacing direct patch.dict(os.environ) patterns with IsolatedEnvironment-based mocks.

CRITICAL: All tests MUST use these fixtures instead of direct os.environ patching.
"""
import pytest
from typing import Dict, Any, Optional, Generator
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from shared.isolated_environment import IsolatedEnvironment, get_env


@pytest.fixture
def isolated_test_env():
    """
    Provides an isolated test environment that doesn't affect os.environ.
    
    This fixture enables isolation mode, captures current state,
    and automatically restores it after the test.
    
    Usage:
        def test_something(isolated_test_env):
            env = isolated_test_env
            env.set('TEST_VAR', 'test_value')
            assert env.get('TEST_VAR') == 'test_value'
    """
    env = get_env()
    
    # Save current state
    was_isolated = env.is_isolated()
    original_vars = env.get_all().copy()
    
    # Enable isolation for test
    env.enable_isolation(backup_original=True)
    
    try:
        yield env
    finally:
        # Restore original state
        if was_isolated:
            env.enable_isolation(refresh_vars=False)
            # Restore original isolated vars
            env._isolated_vars = original_vars
        else:
            env.disable_isolation(restore_original=True)


@pytest.fixture
def mock_env_vars():
    """
    Provides a context manager for temporarily setting environment variables.
    
    This replaces patch.dict(os.environ) with IsolatedEnvironment-based approach.
    
    Usage:
        def test_something(mock_env_vars):
            with mock_env_vars({'JWT_SECRET_KEY': 'test-secret'}):
                env = get_env()
                assert env.get('JWT_SECRET_KEY') == 'test-secret'
    """
    @contextmanager
    def _mock_env_vars(variables: Dict[str, str]):
        env = get_env()
        
        # Save current values
        original_values = {}
        for key in variables:
            original_values[key] = env.get(key)
        
        # Set test values
        for key, value in variables.items():
            env.set(key, value, source='test_fixture')
        
        try:
            yield env
        finally:
            # Restore original values
            for key, original_value in original_values.items():
                if original_value is None:
                    env.delete(key, source='test_fixture')
                else:
                    env.set(key, original_value, source='test_fixture')
    
    return _mock_env_vars


@pytest.fixture
def clean_env():
    """
    Provides a completely clean environment for testing.
    
    This fixture creates an isolated environment with no variables,
    useful for testing default behaviors.
    
    Usage:
        def test_defaults(clean_env):
            env = clean_env
            assert env.get('NONEXISTENT') is None
            env.set('NEW_VAR', 'value')
            assert env.get('NEW_VAR') == 'value'
    """
    env = get_env()
    
    # Save current state
    was_isolated = env.is_isolated()
    original_vars = env.get_all().copy() if was_isolated else None
    
    # Enable isolation and clear all variables
    env.enable_isolation(backup_original=True)
    env.clear()
    
    try:
        yield env
    finally:
        # Restore original state
        if was_isolated:
            env.enable_isolation(refresh_vars=False)
            if original_vars:
                env._isolated_vars = original_vars
        else:
            env.disable_isolation(restore_original=True)


@pytest.fixture
def test_env_with_defaults():
    """
    Provides a test environment with common default values.
    
    This fixture sets up commonly needed test environment variables.
    
    Usage:
        def test_with_defaults(test_env_with_defaults):
            env = test_env_with_defaults
            assert env.get('ENVIRONMENT') == 'test'
            assert env.get('TESTING') == 'true'
    """
    env = get_env()
    
    # Save current state
    original_values = {}
    test_defaults = {
        'ENVIRONMENT': 'test',
        'TESTING': 'true',
        'DEBUG': 'false',
        'LOG_LEVEL': 'WARNING',
        'DATABASE_URL': 'postgresql://test:test@localhost:5432/test_db',
        'REDIS_URL': 'redis://localhost:6379/1',
        'JWT_SECRET_KEY': 'test-jwt-secret-key',
        'SECRET_KEY': 'test-secret-key',
    }
    
    # Save originals and set defaults
    for key, value in test_defaults.items():
        original_values[key] = env.get(key)
        env.set(key, value, source='test_defaults')
    
    try:
        yield env
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                env.delete(key, source='test_defaults')
            else:
                env.set(key, original_value, source='test_defaults')


@pytest.fixture
def backend_test_env():
    """
    Provides a test environment configured for backend service testing.
    
    Usage:
        def test_backend_config(backend_test_env):
            from netra_backend.app.core.backend_environment import get_backend_env
            backend_env = get_backend_env()
            assert backend_env.get_jwt_secret_key() == 'test-backend-jwt'
    """
    env = get_env()
    
    backend_config = {
        'ENVIRONMENT': 'test',
        'TESTING': 'true',
        'JWT_SECRET_KEY': 'test-backend-jwt',
        'SECRET_KEY': 'test-backend-secret',
        'DATABASE_URL': 'postgresql://test:test@localhost:5434/backend_test',
        'REDIS_URL': 'redis://localhost:6381/0',
        'AUTH_SERVICE_URL': 'http://localhost:8081',
        'FRONTEND_URL': 'http://localhost:3000',
        'BACKEND_URL': 'http://localhost:8000',
        'OPENAI_API_KEY': 'test-openai-key',
        'ANTHROPIC_API_KEY': 'test-anthropic-key',
    }
    
    original_values = {}
    for key, value in backend_config.items():
        original_values[key] = env.get(key)
        env.set(key, value, source='backend_test')
    
    try:
        yield env
    finally:
        for key, original_value in original_values.items():
            if original_value is None:
                env.delete(key, source='backend_test')
            else:
                env.set(key, original_value, source='backend_test')


@pytest.fixture
def auth_test_env():
    """
    Provides a test environment configured for auth service testing.
    
    Usage:
        def test_auth_config(auth_test_env):
            from auth_service.auth_core.auth_environment import get_auth_env
            auth_env = get_auth_env()
            assert auth_env.get_jwt_secret_key() == 'test-auth-jwt'
    """
    env = get_env()
    
    auth_config = {
        'ENVIRONMENT': 'test',
        'TESTING': 'true',
        'JWT_SECRET_KEY': 'test-auth-jwt',
        'SECRET_KEY': 'test-auth-secret',
        'DATABASE_URL': 'postgresql://test:test@localhost:5434/auth_test',
        'REDIS_URL': 'redis://localhost:6381/1',
        'AUTH_SERVICE_PORT': '8081',
        'AUTH_SERVICE_HOST': '0.0.0.0',
        'BACKEND_URL': 'http://localhost:8000',
        'FRONTEND_URL': 'http://localhost:3000',
        'BCRYPT_ROUNDS': '4',  # Lower for faster tests
        'JWT_EXPIRATION_MINUTES': '5',
    }
    
    original_values = {}
    for key, value in auth_config.items():
        original_values[key] = env.get(key)
        env.set(key, value, source='auth_test')
    
    try:
        yield env
    finally:
        for key, original_value in original_values.items():
            if original_value is None:
                env.delete(key, source='auth_test')
            else:
                env.set(key, original_value, source='auth_test')


@contextmanager
def temporary_env_var(key: str, value: str):
    """
    Context manager for temporarily setting a single environment variable.
    
    Usage:
        with temporary_env_var('DEBUG', 'true'):
            env = get_env()
            assert env.get('DEBUG') == 'true'
    """
    env = get_env()
    original_value = env.get(key)
    
    env.set(key, value, source='temporary')
    
    try:
        yield env
    finally:
        if original_value is None:
            env.delete(key, source='temporary')
        else:
            env.set(key, original_value, source='temporary')


@contextmanager
def mock_production_env():
    """
    Context manager for testing with production-like environment settings.
    
    Usage:
        with mock_production_env():
            env = get_env()
            assert env.get('ENVIRONMENT') == 'production'
            assert env.get('DEBUG') == 'false'
    """
    env = get_env()
    
    prod_config = {
        'ENVIRONMENT': 'production',
        'DEBUG': 'false',
        'LOG_LEVEL': 'INFO',
        'TESTING': 'false',
    }
    
    original_values = {}
    for key, value in prod_config.items():
        original_values[key] = env.get(key)
        env.set(key, value, source='mock_production')
    
    try:
        yield env
    finally:
        for key, original_value in original_values.items():
            if original_value is None:
                env.delete(key, source='mock_production')
            else:
                env.set(key, original_value, source='mock_production')


@contextmanager
def mock_staging_env():
    """
    Context manager for testing with staging environment settings.
    
    Usage:
        with mock_staging_env():
            env = get_env()
            assert env.get('ENVIRONMENT') == 'staging'
    """
    env = get_env()
    
    staging_config = {
        'ENVIRONMENT': 'staging',
        'DEBUG': 'false',
        'LOG_LEVEL': 'INFO',
        'TESTING': 'false',
    }
    
    original_values = {}
    for key, value in staging_config.items():
        original_values[key] = env.get(key)
        env.set(key, value, source='mock_staging')
    
    try:
        yield env
    finally:
        for key, original_value in original_values.items():
            if original_value is None:
                env.delete(key, source='mock_staging')
            else:
                env.set(key, original_value, source='mock_staging')


# Backward compatibility removed - use isolated_test_env or mock_env_vars instead


def replace_patch_dict_with_isolated_env(test_func):
    """
    Decorator to replace patch.dict(os.environ) with IsolatedEnvironment.
    
    This decorator can be used to quickly migrate existing tests.
    
    Usage:
        @replace_patch_dict_with_isolated_env
        def test_something():
            env = get_env()
            env.set('TEST_VAR', 'value')
            assert env.get('TEST_VAR') == 'value'
    """
    def wrapper(*args, **kwargs):
        env = get_env()
        was_isolated = env.is_isolated()
        original_vars = env.get_all().copy() if was_isolated else None
        
        env.enable_isolation(backup_original=True)
        
        try:
            return test_func(*args, **kwargs)
        finally:
            if was_isolated:
                env.enable_isolation(refresh_vars=False)
                if original_vars:
                    env._isolated_vars = original_vars
            else:
                env.disable_isolation(restore_original=True)
    
    return wrapper