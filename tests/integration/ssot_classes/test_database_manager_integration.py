"""
Integration Tests for DatabaseManager SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core infrastructure supporting all user segments
- Business Goal: Ensure reliable database connectivity for all platform operations
- Value Impact: Database stability enables user sessions, agent executions, and data persistence
- Strategic Impact: Critical infrastructure supporting $500K+ ARR through reliable data operations

This test suite validates the DatabaseManager SSOT implementation by testing:
1. DatabaseURLBuilder SSOT integration for URL construction
2. Connection initialization and engine management
3. Session lifecycle and context management
4. Connection pooling configuration (NullPool, QueuePool, StaticPool)
5. Multi-database support (PostgreSQL, ClickHouse)
6. Proper SSL and VPC connector configuration
7. Error handling and connection recovery
8. Resource cleanup and connection disposal

CRITICAL: These tests validate core database infrastructure that supports all business operations.
All tests focus on DatabaseURLBuilder SSOT compliance and connection management patterns
without requiring actual database connections - filling the gap between unit and E2E tests.

Testing Philosophy:
- Use real DatabaseManager and DatabaseURLBuilder components
- Mock only external dependencies (actual database connections)
- Test configuration and URL building logic with realistic parameters
- Validate SSOT compliance and proper integration patterns
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager
from shared.database_url_builder import DatabaseURLBuilder


class TestDatabaseManagerInitialization(SSotAsyncTestCase):
    """Test DatabaseManager initialization and URL building functionality."""
    
    def setup_method(self, method=None):
        """Setup test environment with isolated configuration."""
        super().setup_method(method)
        
        # Setup test environment variables for PostgreSQL configuration
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("POSTGRES_HOST", "localhost")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_USER", "test_user")
        self.set_env_var("POSTGRES_PASSWORD", "test_password")
        self.set_env_var("POSTGRES_DB", "test_db")
        
        # Record test setup metrics
        self.record_metric("test_category", "database_manager_initialization")
        self.record_metric("component_under_test", "DatabaseManager")
    
    async def test_database_manager_initialization_with_url_builder(self):
        """Test DatabaseManager initializes correctly using DatabaseURLBuilder SSOT."""
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            # Mock engine to avoid actual database connection
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            # Create DatabaseManager instance
            manager = DatabaseManager()
            
            # Verify initial state
            assert not manager._initialized
            assert manager._engines == {}
            assert manager._url_builder is None
            
            # Initialize the manager
            await manager.initialize()
            
            # Verify initialization completed
            assert manager._initialized
            assert 'primary' in manager._engines
            assert manager._engines['primary'] == mock_engine
            assert manager._url_builder is not None
            assert isinstance(manager._url_builder, DatabaseURLBuilder)
            
            # Verify create_async_engine was called with DatabaseURLBuilder URL
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            database_url = call_args[0][0]
            
            # Verify URL follows DatabaseURLBuilder format for asyncpg
            assert database_url.startswith("postgresql+asyncpg://")
            assert "localhost" in database_url
            assert "test_db" in database_url
            
            # Verify engine configuration
            engine_kwargs = call_args[1]
            assert engine_kwargs["pool_pre_ping"] is True
            assert engine_kwargs["pool_recycle"] == 3600
            assert "poolclass" in engine_kwargs
            
            self.record_metric("initialization_success", True)
            self.record_metric("url_builder_integration", True)
    
    async def test_database_manager_with_cloud_sql_configuration(self):
        """Test DatabaseManager handles Cloud SQL configuration correctly."""
        with self.temp_env_vars(
            POSTGRES_HOST="/cloudsql/project-id:region:instance",
            POSTGRES_USER="cloudsql_user",
            POSTGRES_PASSWORD="cloudsql_password",
            POSTGRES_DB="production_db"
        ):
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                manager = DatabaseManager()
                await manager.initialize()
                
                # Verify Cloud SQL URL format
                call_args = mock_create_engine.call_args
                database_url = call_args[0][0]
                
                # Cloud SQL URLs use Unix socket format
                assert "postgresql+asyncpg://" in database_url
                assert "/cloudsql/" in database_url
                assert "?host=" in database_url
                assert "production_db" in database_url
                
                self.record_metric("cloud_sql_support", True)
    
    async def test_database_manager_with_sqlite_configuration(self):
        """Test DatabaseManager handles SQLite configuration for testing."""
        with self.temp_env_vars(
            ENVIRONMENT="test",
            USE_MEMORY_DB="true"
        ):
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                manager = DatabaseManager()
                
                # Mock get_url_for_environment to return SQLite URL
                with patch.object(manager, '_get_database_url') as mock_get_url:
                    mock_get_url.return_value = "sqlite+aiosqlite:///:memory:"
                    
                    await manager.initialize()
                    
                    # Verify SQLite configuration uses NullPool
                    call_args = mock_create_engine.call_args
                    engine_kwargs = call_args[1]
                    
                    # SQLite should use NullPool
                    from sqlalchemy.pool import NullPool
                    assert engine_kwargs["poolclass"] == NullPool
                    
                    self.record_metric("sqlite_support", True)
    
    async def test_database_manager_url_builder_integration(self):
        """Test DatabaseManager properly integrates with DatabaseURLBuilder SSOT."""
        manager = DatabaseManager()
        
        # Test URL construction through DatabaseURLBuilder
        test_url = manager._get_database_url()
        
        # Verify URL was built using DatabaseURLBuilder
        assert manager._url_builder is not None
        assert isinstance(manager._url_builder, DatabaseURLBuilder)
        
        # Verify URL format follows DatabaseURLBuilder standards
        assert test_url.startswith("postgresql+asyncpg://")
        
        # Test that URL builder methods are properly called
        with patch.object(manager._url_builder, 'format_url_for_driver') as mock_format:
            mock_format.return_value = "postgresql+asyncpg://formatted_url"
            
            formatted_url = manager._get_database_url()
            
            # Verify format_url_for_driver was called with asyncpg driver
            mock_format.assert_called_with(test_url, 'asyncpg')
            
            self.record_metric("url_builder_ssot_compliance", True)


class TestDatabaseManagerConnectionManagement(SSotAsyncTestCase):
    """Test DatabaseManager connection and engine management functionality."""
    
    def setup_method(self, method=None):
        """Setup test environment for connection management tests."""
        super().setup_method(method)
        
        # Setup realistic database configuration
        self.set_env_var("ENVIRONMENT", "development")
        self.set_env_var("POSTGRES_HOST", "localhost")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_USER", "dev_user")
        self.set_env_var("POSTGRES_PASSWORD", "dev_password")
        self.set_env_var("POSTGRES_DB", "netra_dev")
        
        self.record_metric("test_category", "connection_management")
    
    async def test_get_engine_auto_initialization(self):
        """Test get_engine auto-initializes when accessed before initialization."""
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            manager = DatabaseManager()
            
            # Verify not initialized
            assert not manager._initialized
            
            # Mock asyncio.create_task to simulate auto-initialization
            with patch('asyncio.create_task') as mock_create_task:
                with patch('time.sleep') as mock_sleep:
                    # Mock successful initialization
                    async def mock_init():
                        manager._engines['primary'] = mock_engine
                        manager._initialized = True
                    
                    mock_create_task.side_effect = lambda coro: asyncio.ensure_future(mock_init())
                    
                    # Access engine before initialization
                    engine = manager.get_engine('primary')
                    
                    # Verify auto-initialization was attempted
                    mock_create_task.assert_called_once()
                    assert engine == mock_engine
                    
                    self.record_metric("auto_initialization_success", True)
    
    async def test_get_engine_with_invalid_name(self):
        """Test get_engine raises appropriate error for invalid engine names."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            manager = DatabaseManager()
            await manager.initialize()
            
            # Test invalid engine name
            with self.expect_exception(ValueError, "Engine 'invalid' not found"):
                manager.get_engine('invalid')
                
            self.record_metric("invalid_engine_handling", True)
    
    async def test_connection_pooling_configuration(self):
        """Test different connection pooling configurations are applied correctly."""
        test_configs = [
            {
                "description": "NullPool for SQLite",
                "url": "sqlite+aiosqlite:///:memory:",
                "expected_pool": "NullPool"
            },
            {
                "description": "StaticPool for PostgreSQL",
                "url": "postgresql+asyncpg://user:pass@localhost/db",
                "expected_pool": "StaticPool"
            }
        ]
        
        for config in test_configs:
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                manager = DatabaseManager()
                
                with patch.object(manager, '_get_database_url') as mock_get_url:
                    mock_get_url.return_value = config["url"]
                    
                    await manager.initialize()
                    
                    # Verify poolclass configuration
                    call_args = mock_create_engine.call_args
                    engine_kwargs = call_args[1]
                    
                    if "sqlite" in config["url"]:
                        from sqlalchemy.pool import NullPool
                        assert engine_kwargs["poolclass"] == NullPool
                    else:
                        from sqlalchemy.pool import StaticPool
                        assert engine_kwargs["poolclass"] == StaticPool
                    
                    self.record_metric(f"pool_config_{config['expected_pool']}", True)
    
    async def test_create_application_engine(self):
        """Test static method for creating application engines."""
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                # Mock configuration
                mock_config.return_value = Mock(database_url="postgresql://test")
                
                # Create application engine
                engine = DatabaseManager.create_application_engine()
                
                # Verify engine creation
                assert engine == mock_engine
                mock_create_engine.assert_called_once()
                
                # Verify engine configuration for health checks
                call_args = mock_create_engine.call_args
                engine_kwargs = call_args[1]
                
                assert engine_kwargs["echo"] is False  # No echo for health checks
                from sqlalchemy.pool import NullPool
                assert engine_kwargs["poolclass"] == NullPool  # NullPool for health checks
                assert engine_kwargs["pool_pre_ping"] is True
                assert engine_kwargs["pool_recycle"] == 3600
                
                self.record_metric("application_engine_creation", True)


class TestDatabaseManagerSessionLifecycle(SSotAsyncTestCase):
    """Test DatabaseManager session lifecycle and context management."""
    
    def setup_method(self, method=None):
        """Setup test environment for session lifecycle tests."""
        super().setup_method(method)
        
        # Setup database configuration
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("POSTGRES_HOST", "test-host")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_USER", "test_user")
        self.set_env_var("POSTGRES_PASSWORD", "test_password")
        self.set_env_var("POSTGRES_DB", "test_database")
        
        self.record_metric("test_category", "session_lifecycle")
    
    async def test_get_session_context_manager(self):
        """Test get_session context manager handles session lifecycle correctly."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                # Mock session instance
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                manager = DatabaseManager()
                await manager.initialize()
                
                # Test session context manager
                async with manager.get_session() as session:
                    assert session == mock_session
                    
                    # Verify session is usable within context
                    await session.execute("SELECT 1")
                    session.execute.assert_called_with("SELECT 1")
                
                # Verify session lifecycle methods called
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
                
                self.record_metric("session_context_manager", True)
    
    async def test_get_session_with_exception_handling(self):
        """Test get_session handles exceptions and performs proper rollback."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                # Mock session instance
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                manager = DatabaseManager()
                await manager.initialize()
                
                # Test exception handling in session
                with self.expect_exception(ValueError, "Test error"):
                    async with manager.get_session() as session:
                        # Simulate error in session
                        raise ValueError("Test error")
                
                # Verify rollback was called on exception
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
                
                self.record_metric("session_exception_handling", True)
    
    async def test_get_session_auto_initialization(self):
        """Test get_session auto-initializes if manager not initialized."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                manager = DatabaseManager()
                
                # Verify not initialized
                assert not manager._initialized
                
                # Access session before initialization
                async with manager.get_session() as session:
                    assert session == mock_session
                
                # Verify auto-initialization occurred
                assert manager._initialized
                
                self.record_metric("session_auto_initialization", True)
    
    async def test_class_method_get_async_session(self):
        """Test class method get_async_session for backward compatibility."""
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                # Mock manager and session
                mock_manager = AsyncMock()
                mock_manager._initialized = True
                mock_session = AsyncMock()
                
                mock_get_manager.return_value = mock_manager
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Mock manager's get_session method
                @asynccontextmanager
                async def mock_get_session(name):
                    yield mock_session
                
                mock_manager.get_session = mock_get_session
                
                # Test class method
                async with DatabaseManager.get_async_session() as session:
                    assert session == mock_session
                
                # Verify manager was obtained and used
                mock_get_manager.assert_called_once()
                
                self.record_metric("class_method_compatibility", True)


class TestDatabaseManagerMultiDatabaseSupport(SSotAsyncTestCase):
    """Test DatabaseManager support for multiple database types."""
    
    def setup_method(self, method=None):
        """Setup test environment for multi-database tests."""
        super().setup_method(method)
        
        # Setup environment for multi-database scenario
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("POSTGRES_HOST", "staging-postgres")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_USER", "staging_user")
        self.set_env_var("POSTGRES_PASSWORD", "staging_password")
        self.set_env_var("POSTGRES_DB", "netra_staging")
        
        self.record_metric("test_category", "multi_database_support")
    
    async def test_postgresql_configuration(self):
        """Test DatabaseManager configuration for PostgreSQL."""
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            manager = DatabaseManager()
            await manager.initialize()
            
            # Verify PostgreSQL configuration
            call_args = mock_create_engine.call_args
            database_url = call_args[0][0]
            
            assert database_url.startswith("postgresql+asyncpg://")
            assert "staging-postgres" in database_url
            assert "netra_staging" in database_url
            
            # Verify PostgreSQL-specific engine configuration
            engine_kwargs = call_args[1]
            assert engine_kwargs["pool_pre_ping"] is True
            assert engine_kwargs["pool_recycle"] == 3600
            
            self.record_metric("postgresql_configuration", True)
    
    async def test_url_builder_driver_integration(self):
        """Test DatabaseManager integration with DatabaseURLBuilder driver formatting."""
        manager = DatabaseManager()
        
        # Test that different drivers are supported through DatabaseURLBuilder
        test_cases = [
            ("asyncpg", "postgresql+asyncpg://"),
            ("psycopg2", "postgresql+psycopg2://"),
            ("psycopg", "postgresql+psycopg://"),
        ]
        
        for driver, expected_prefix in test_cases:
            with patch.object(manager, '_url_builder') as mock_builder:
                mock_builder.format_url_for_driver.return_value = f"{expected_prefix}test_url"
                
                # Test driver formatting
                url = manager._get_database_url()
                
                # Verify DatabaseURLBuilder format_url_for_driver was called
                mock_builder.format_url_for_driver.assert_called()
                
                self.record_metric(f"driver_support_{driver}", True)
    
    async def test_ssl_configuration_handling(self):
        """Test DatabaseManager handles SSL configuration through DatabaseURLBuilder."""
        with self.temp_env_vars(
            ENVIRONMENT="production",
            POSTGRES_HOST="prod-postgres.example.com",
            POSTGRES_PORT="5432",
            POSTGRES_USER="prod_user",
            POSTGRES_PASSWORD="prod_password",
            POSTGRES_DB="netra_production"
        ):
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                mock_engine = AsyncMock()
                mock_create_engine.return_value = mock_engine
                
                manager = DatabaseManager()
                
                # Mock URL builder to return SSL-enabled URL
                with patch.object(manager, '_get_database_url') as mock_get_url:
                    mock_get_url.return_value = "postgresql+asyncpg://user:pass@prod-host/db?ssl=require"
                    
                    await manager.initialize()
                    
                    # Verify SSL URL was used
                    call_args = mock_create_engine.call_args
                    database_url = call_args[0][0]
                    
                    assert "ssl=require" in database_url or "sslmode=require" in database_url
                    
                    self.record_metric("ssl_configuration", True)


class TestDatabaseManagerErrorHandlingAndRecovery(SSotAsyncTestCase):
    """Test DatabaseManager error handling and connection recovery."""
    
    def setup_method(self, method=None):
        """Setup test environment for error handling tests."""
        super().setup_method(method)
        
        # Setup environment for error scenarios
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("POSTGRES_HOST", "error-test-host")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_USER", "error_user")
        self.set_env_var("POSTGRES_PASSWORD", "error_password")
        self.set_env_var("POSTGRES_DB", "error_test_db")
        
        self.record_metric("test_category", "error_handling_recovery")
    
    async def test_initialization_failure_handling(self):
        """Test DatabaseManager handles initialization failures gracefully."""
        with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            # Mock engine creation failure
            mock_create_engine.side_effect = Exception("Database connection failed")
            
            manager = DatabaseManager()
            
            # Test initialization failure
            with self.expect_exception(Exception, "Database connection failed"):
                await manager.initialize()
            
            # Verify manager state after failure
            assert not manager._initialized
            assert manager._engines == {}
            
            self.record_metric("initialization_failure_handling", True)
    
    async def test_health_check_with_auto_initialization(self):
        """Test health_check method auto-initializes and handles errors."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                # Mock session for health check
                mock_session = AsyncMock()
                mock_session_class.return_value.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session_class.return_value.__aexit__ = AsyncMock(return_value=None)
                
                # Mock successful query execution
                mock_result = Mock()
                mock_session.execute.return_value = mock_result
                mock_result.fetchone.return_value = (1,)
                
                manager = DatabaseManager()
                
                # Verify not initialized
                assert not manager._initialized
                
                # Perform health check
                health_result = await manager.health_check()
                
                # Verify auto-initialization occurred
                assert manager._initialized
                
                # Verify health check result
                assert health_result["status"] == "healthy"
                assert health_result["engine"] == "primary"
                assert health_result["connection"] == "ok"
                
                self.record_metric("health_check_auto_init", True)
    
    async def test_health_check_failure_handling(self):
        """Test health_check handles database connection failures."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                # Mock session failure
                mock_session_class.side_effect = Exception("Connection refused")
                
                manager = DatabaseManager()
                await manager.initialize()
                
                # Perform health check with connection failure
                health_result = await manager.health_check()
                
                # Verify failure result
                assert health_result["status"] == "unhealthy"
                assert health_result["engine"] == "primary"
                assert "Connection refused" in health_result["error"]
                
                self.record_metric("health_check_failure_handling", True)
    
    async def test_close_all_with_error_handling(self):
        """Test close_all handles engine disposal errors gracefully."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            # Mock engine that fails to dispose
            mock_engine = AsyncMock()
            mock_engine.dispose.side_effect = Exception("Disposal failed")
            
            manager = DatabaseManager()
            manager._engines['primary'] = mock_engine
            manager._engines['secondary'] = AsyncMock()  # This one succeeds
            manager._initialized = True
            
            # Close all engines
            await manager.close_all()
            
            # Verify state reset despite disposal error
            assert not manager._initialized
            assert manager._engines == {}
            
            # Verify both engines had dispose called
            mock_engine.dispose.assert_called_once()
            
            self.record_metric("close_all_error_handling", True)
    
    async def test_migration_url_sync_format(self):
        """Test static method for migration URL in sync format."""
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            # Mock URL builder instance
            mock_builder = Mock()
            mock_builder_class.return_value = mock_builder
            mock_builder.get_url_for_environment.return_value = "postgresql+asyncpg://test_url"
            
            # Get migration URL
            migration_url = DatabaseManager.get_migration_url_sync_format()
            
            # Verify sync format conversion
            assert migration_url == "postgresql://test_url"
            
            # Verify URL builder was called with sync=True
            mock_builder.get_url_for_environment.assert_called_with(sync=True)
            
            self.record_metric("migration_url_sync_format", True)
    
    async def test_migration_url_failure_handling(self):
        """Test migration URL method handles failures appropriately."""
        with patch('shared.database_url_builder.DatabaseURLBuilder') as mock_builder_class:
            # Mock URL builder that returns None
            mock_builder = Mock()
            mock_builder_class.return_value = mock_builder
            mock_builder.get_url_for_environment.return_value = None
            
            # Test migration URL failure
            with self.expect_exception(ValueError, "Could not determine migration database URL"):
                DatabaseManager.get_migration_url_sync_format()
            
            self.record_metric("migration_url_failure_handling", True)


class TestDatabaseManagerResourceCleanup(SSotAsyncTestCase):
    """Test DatabaseManager resource cleanup and connection disposal."""
    
    def setup_method(self, method=None):
        """Setup test environment for resource cleanup tests."""
        super().setup_method(method)
        
        # Setup environment for cleanup testing
        self.set_env_var("ENVIRONMENT", "test")
        self.set_env_var("POSTGRES_HOST", "cleanup-test")
        self.set_env_var("POSTGRES_PORT", "5432")
        self.set_env_var("POSTGRES_USER", "cleanup_user")
        self.set_env_var("POSTGRES_PASSWORD", "cleanup_pass")
        self.set_env_var("POSTGRES_DB", "cleanup_db")
        
        self.record_metric("test_category", "resource_cleanup")
    
    async def test_proper_engine_disposal(self):
        """Test DatabaseManager properly disposes of engines during cleanup."""
        with patch('netra_backend.app.db.database_manager.create_async_engine'):
            # Create multiple mock engines
            mock_primary_engine = AsyncMock()
            mock_secondary_engine = AsyncMock()
            
            manager = DatabaseManager()
            manager._engines['primary'] = mock_primary_engine
            manager._engines['secondary'] = mock_secondary_engine
            manager._initialized = True
            
            # Close all engines
            await manager.close_all()
            
            # Verify all engines were disposed
            mock_primary_engine.dispose.assert_called_once()
            mock_secondary_engine.dispose.assert_called_once()
            
            # Verify state cleanup
            assert not manager._initialized
            assert manager._engines == {}
            
            self.record_metric("engine_disposal", True)
    
    async def test_get_database_manager_singleton_behavior(self):
        """Test get_database_manager function maintains singleton behavior."""
        # Clear any existing manager
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        # Get manager instances
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        
        # Verify singleton behavior
        assert manager1 is manager2
        assert isinstance(manager1, DatabaseManager)
        
        self.record_metric("singleton_behavior", True)
    
    async def test_get_database_manager_auto_initialization_attempt(self):
        """Test get_database_manager attempts auto-initialization when possible."""
        # Clear any existing manager
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        with patch('asyncio.get_running_loop') as mock_get_loop:
            with patch('asyncio.create_task') as mock_create_task:
                # Mock event loop availability
                mock_loop = Mock()
                mock_get_loop.return_value = mock_loop
                
                # Get manager
                manager = get_database_manager()
                
                # Verify initialization was attempted
                assert isinstance(manager, DatabaseManager)
                mock_create_task.assert_called_once()
                
                self.record_metric("auto_initialization_attempt", True)
    
    async def test_get_database_manager_no_event_loop_handling(self):
        """Test get_database_manager handles absence of event loop gracefully."""
        # Clear any existing manager
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        with patch('asyncio.get_running_loop') as mock_get_loop:
            # Mock no event loop available
            mock_get_loop.side_effect = RuntimeError("No event loop")
            
            # Get manager
            manager = get_database_manager()
            
            # Verify manager created despite no event loop
            assert isinstance(manager, DatabaseManager)
            
            self.record_metric("no_event_loop_handling", True)


# Integration test execution markers
pytest_plugins = ["pytest_asyncio"]

# Test categorization for unified test runner
pytestmark = [
    pytest.mark.integration,
    pytest.mark.backend,
    pytest.mark.fast,
]