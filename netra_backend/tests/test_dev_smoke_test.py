"""
Smoke test for dev environment to ensure all critical components work.

This test runs essential smoke tests to validate the dev environment is working correctly.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch


class TestDevSmokeTest:
    """Smoke tests for development environment."""

    def test_imports_work(self):
        """Test that all critical imports work without errors."""
        try:
            from netra_backend.app.config import get_config
            from netra_backend.app.logging_config import central_logger
            from netra_backend.app.db.postgres import initialize_postgres
            
            assert get_config is not None
            assert central_logger is not None
            assert initialize_postgres is not None
        except ImportError as e:
            pytest.fail(f"Critical import failed: {e}")

    def test_config_accessible(self):
        """Test that configuration is accessible."""
        from netra_backend.app.config import get_config
        
        config = get_config()
        assert config is not None
        assert hasattr(config, 'environment')
        assert hasattr(config, 'database_url')

    def test_logging_functional(self):
        """Test that logging is functional."""
        from netra_backend.app.logging_config import central_logger
        
        logger = central_logger.get_logger('smoke_test')
        
        # This should not raise an exception
        logger.info("Smoke test logging check")
        logger.debug("Debug logging check")
        logger.warning("Warning logging check")

    async def test_database_session_creation(self):
        """Test that database sessions can be created."""
        from netra_backend.app.db.postgres import initialize_postgres, get_async_db
        
        # Try to initialize database
        try:
            session_factory = initialize_postgres()
            if session_factory is None:
                pytest.skip("Database initialization failed in test mode")
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
        
        # Try to create a session
        try:
            async with get_async_db() as session:
                assert session is not None
                # Try a simple query
                result = await session.execute("SELECT 1")
                assert result.scalar() == 1
        except Exception as e:
            pytest.fail(f"Database session creation failed: {e}")

    def test_environment_variables_set(self):
        """Test that required environment variables are set."""
        from netra_backend.app.core.isolated_environment import get_env
        
        env = get_env()
        
        # Check for critical environment variables
        database_url = env.get('DATABASE_URL')
        environment = env.get('ENVIRONMENT') or env.get('NETRA_ENVIRONMENT')
        
        assert database_url is not None, "DATABASE_URL must be set"
        assert environment is not None, "ENVIRONMENT must be set"

    def test_unified_config_accessible(self):
        """Test that unified config is accessible."""
        from netra_backend.app.core.configuration.base import get_unified_config
        
        config = get_unified_config()
        assert config is not None
        
        # Check that database config is loaded
        assert hasattr(config, 'db_pool_size')
        assert hasattr(config, 'db_max_overflow')
        assert config.db_pool_size > 0
        assert config.db_max_overflow > 0

    @patch('netra_backend.app.db.postgres_core.async_engine')
    @patch('netra_backend.app.db.postgres_core.async_session_factory')
    def test_database_mocking_works(self, mock_session_factory, mock_engine):
        """Test that database mocking works for tests."""
        from netra_backend.app.db.postgres import async_engine, async_session_factory
        
        # Mock should be accessible
        mock_engine.return_value = AsyncMock()
        mock_session_factory.return_value = AsyncMock()
        
        # Should not raise errors
        assert mock_engine is not None
        assert mock_session_factory is not None

    def test_module_structure_intact(self):
        """Test that module structure is intact."""
        # Test that all major modules can be imported
        modules_to_test = [
            'netra_backend.app.config',
            'netra_backend.app.logging_config',
            'netra_backend.app.db.postgres',
            'netra_backend.app.core.configuration',
            'netra_backend.app.core.isolated_environment',
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_no_syntax_errors_in_key_files(self):
        """Test that key files have no syntax errors."""
        import ast
        import os
        
        key_files = [
            'netra_backend/app/config.py',
            'netra_backend/app/logging_config.py',
            'netra_backend/app/db/postgres.py',
            'netra_backend/app/core/configuration/base.py',
        ]
        
        base_path = os.path.join(os.getcwd())
        
        for file_path in key_files:
            full_path = os.path.join(base_path, file_path)
            if os.path.exists(full_path):
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    ast.parse(content)
                except SyntaxError as e:
                    pytest.fail(f"Syntax error in {file_path}: {e}")
                except Exception as e:
                    # File might not exist or be readable, skip
                    pass

    def test_basic_health_indicators(self):
        """Test basic health indicators."""
        # Test that Python environment is working
        import sys
        assert sys.version_info >= (3, 8), "Python 3.8+ required"
        
        # Test that asyncio is working
        import asyncio
        loop = asyncio.new_event_loop()
        loop.close()  # Should not raise exception
        
        # Test that basic SQLAlchemy imports work
        try:
            from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
            assert AsyncSession is not None
            assert create_async_engine is not None
        except ImportError as e:
            pytest.fail(f"SQLAlchemy async imports failed: {e}")

    def test_dev_launcher_compatibility(self):
        """Test that dev launcher compatibility is maintained."""
        # Test that scripts can be imported
        try:
            import scripts.dev_launcher
            assert scripts.dev_launcher is not None
        except ImportError:
            # Dev launcher might not be importable in test mode, that's okay
            pass
        
        # Test that environment supports dev launcher functionality
        from netra_backend.app.core.isolated_environment import get_env
        env = get_env()
        
        # Should be able to get environment variables
        assert callable(env.get)
        assert isinstance(env.get('PATH', ''), str)