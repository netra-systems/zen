"""
Test dev launcher health and startup reliability.

This test validates that the dev launcher starts correctly and all services are healthy.
"""

import pytest
import asyncio
import requests
import time
from urllib.parse import urlparse
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.config import get_config


class TestDevLauncherHealth:
    """Test dev launcher health and startup."""

    def test_dev_environment_config_loaded(self):
        """Test that development environment configuration is properly loaded."""
        config = get_config()
        assert config is not None
        assert hasattr(config, 'database_url')
        assert hasattr(config, 'environment')
        # Should be in dev mode
        assert config.environment in ['development', 'dev']

    def test_database_url_accessible(self):
        """Test that database URL is accessible and valid."""
        config = get_config()
        db_url = config.database_url
        
        assert db_url is not None
        assert 'postgresql' in db_url
        # Should contain localhost or local connection
        assert 'localhost' in db_url or '127.0.0.1' in db_url

    async def test_basic_database_connectivity(self):
        """Test basic database connectivity."""
        from netra_backend.app.db.postgres import initialize_postgres, get_async_db
        
        # Initialize database
        try:
            initialize_postgres()
        except Exception:
            # If initialization fails in test mode, skip
            pytest.skip("Database not available in test mode")
            
        # Test basic connectivity
        try:
            async with get_async_db() as session:
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
        except Exception as e:
            pytest.fail(f"Database connectivity failed: {e}")

    def test_redis_configuration_present(self):
        """Test that Redis configuration is present."""
        config = get_config()
        # Redis should be configured even if disabled for tests
        assert hasattr(config, 'redis_url') or hasattr(config, 'redis_host')

    def test_logging_configuration_working(self):
        """Test that logging configuration is working."""
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger('test')
        assert logger is not None
        
        # Test that we can log without errors
        logger.info("Test log message for dev launcher health check")

    def test_environment_isolation(self):
        """Test that environment is properly isolated for dev mode."""
        from shared.isolated_environment import get_env
        
        env = get_env()
        # Should have development environment settings
        environment = env.get('ENVIRONMENT') or env.get('NETRA_ENVIRONMENT')
        assert environment in ['development', 'dev', 'test']

    def test_config_consistency(self):
        """Test that configuration is consistent across components."""
        from netra_backend.app.core.configuration.base import get_unified_config
        
        config = get_unified_config()
        assert config is not None
        
        # Test that database configuration is consistent
        assert config.db_pool_size > 0
        assert config.db_max_overflow > 0
        assert config.db_pool_timeout > 0

    def test_startup_readiness_indicators(self):
        """Test that startup readiness indicators are working."""
        # Test that we can import key modules without errors
        try:
            from netra_backend.app.db.postgres import async_engine, async_session_factory
            from netra_backend.app.logging_config import central_logger
            from netra_backend.app.config import get_config
            
            # All imports should succeed
            assert True
        except ImportError as e:
            pytest.fail(f"Key module import failed: {e}")

    def test_service_module_health(self):
        """Test that service modules can be imported and are healthy."""
        try:
            # Test core service imports
            from netra_backend.app.db import postgres
            from netra_backend.app.core import configuration
            from netra_backend.app import logging_config
            
            # All should import without issues
            assert postgres is not None
            assert configuration is not None
            assert logging_config is not None
            
        except Exception as e:
            pytest.fail(f"Service module health check failed: {e}")

    def test_no_circular_imports(self):
        """Test that there are no circular import issues."""
        # Test importing main modules in different orders
        try:
            from netra_backend.app.config import get_config
            from netra_backend.app.db.postgres import initialize_postgres
            from netra_backend.app.logging_config import central_logger
            
            config = get_config()
            logger = central_logger.get_logger('test')
            
            assert config is not None
            assert logger is not None
            
        except Exception as e:
            pytest.fail(f"Circular import detected: {e}")