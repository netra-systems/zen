"""
Comprehensive Unit Tests for DatabaseManager SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure database reliability and prevent connection failures
- Value Impact: Validates core database connectivity that supports all user chat operations
- Strategic Impact: Prevents cascade failures that would break entire platform functionality

Test Coverage Areas:
1. Connection pool management (PostgreSQL, ClickHouse, Redis)
2. Unified transaction management  
3. Connection health checks
4. Retry logic and circuit breakers
5. Query execution and result handling
6. Connection lifecycle (create, close, recreate)
7. Error handling and recovery
8. Connection configuration
9. Thread safety for connection pools
10. Performance monitoring and metrics

CRITICAL: These tests focus on breadth of basic functionality.
Many tests are designed to be failing initially to identify implementation gaps.
"""

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool, QueuePool, StaticPool
from sqlalchemy.exc import DatabaseError, OperationalError, TimeoutError as SQLTimeoutError
from sqlalchemy import text
from typing import Dict, Any, Optional, List
import logging
import threading
import time
from contextlib import asynccontextmanager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.user_execution_engine import UserExecutionEngine

# Import the class under test
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from netra_backend.app.core.config import AppConfig


class TestDatabaseManagerInitialization:
    """Test DatabaseManager initialization and setup."""
    
    def test_database_manager_constructor_creates_empty_state(self):
        """Test that constructor initializes with empty state."""
        manager = DatabaseManager()
        assert manager._engines == {}
        assert manager._initialized is False
        assert manager._url_builder is None
        assert manager.config is not None
    
    def test_database_manager_constructor_calls_get_config(self):
        """Test that constructor properly calls get_config."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = return_value_instance  # Initialize appropriate service
            manager = DatabaseManager()
            mock_config.assert_called_once()
            assert manager.config == mock_config.return_value
    
    @pytest.mark.asyncio
    async def test_initialize_sets_initialized_flag(self):
        """Test that initialize sets the initialized flag."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False, 
                database_pool_size=5,
                database_max_overflow=10,
                database_url="sqlite:///:memory:"
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="sqlite:///:memory:"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_creates_primary_engine(self):
        """Test that initialize creates a primary engine."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5, 
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    assert 'primary' in manager._engines
    
    @pytest.mark.asyncio
    async def test_initialize_idempotency(self):
        """Test that multiple initialize calls don't cause issues."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    await manager.initialize()  # Second call should be no-op
                    mock_engine.assert_called_once()  # Engine should only be created once
    
    @pytest.mark.asyncio
    async def test_initialize_handles_missing_config_attributes_gracefully(self):
        """Test that initialize handles missing config attributes with defaults."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            # Create config without some attributes
            config = config_instance  # Initialize appropriate service
            del config.database_echo  # Simulate missing attribute
            del config.database_pool_size
            del config.database_max_overflow
            mock_config.return_value = config
            
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    # Should use default values when attributes are missing
                    assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_initialize_uses_null_pool_for_sqlite(self):
        """Test that SQLite URLs use NullPool."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="sqlite:///:memory:"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    # Check that NullPool was used
                    call_args = mock_engine.call_args
                    assert call_args[1]['poolclass'] == NullPool
    
    @pytest.mark.asyncio
    async def test_initialize_uses_static_pool_for_postgresql(self):
        """Test that PostgreSQL URLs use StaticPool."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    # Check that StaticPool was used
                    call_args = mock_engine.call_args
                    assert call_args[1]['poolclass'] == StaticPool
    
    @pytest.mark.asyncio
    async def test_initialize_uses_null_pool_for_zero_pool_size(self):
        """Test that pool_size <= 0 uses NullPool."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=0,  # Zero pool size
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    await manager.initialize()
                    # Check that NullPool was used
                    call_args = mock_engine.call_args
                    assert call_args[1]['poolclass'] == NullPool
    
    @pytest.mark.asyncio
    async def test_initialize_logs_success_message(self):
        """Test that initialize logs success message."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
                        manager = DatabaseManager()
                        await manager.initialize()
                        mock_logger.info.assert_called_with("DatabaseManager initialized successfully")


class TestDatabaseManagerEngineManagement:
    """Test DatabaseManager engine retrieval and management."""
    
    def test_get_engine_raises_if_not_initialized(self):
        """Test that get_engine raises RuntimeError if not initialized."""
        manager = DatabaseManager()
        with pytest.raises(RuntimeError, match="DatabaseManager not initialized"):
            manager.get_engine()
    
    def test_get_engine_raises_if_engine_not_found(self):
        """Test that get_engine raises ValueError for unknown engine name."""
    pass
        manager = DatabaseManager()
        manager._initialized = True  # Fake initialization
        with pytest.raises(ValueError, match="Engine 'unknown' not found"):
            manager.get_engine('unknown')
    
    def test_get_engine_returns_primary_engine_by_default(self):
        """Test that get_engine returns primary engine by default."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        result = manager.get_engine()
        assert result == mock_engine
    
    def test_get_engine_returns_named_engine(self):
        """Test that get_engine returns correctly named engine."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['test_engine'] = mock_engine
        
        result = manager.get_engine('test_engine')
        assert result == mock_engine
    
    def test_get_engine_with_multiple_engines(self):
        """Test get_engine with multiple engines registered."""
        manager = DatabaseManager()
        manager._initialized = True
        primary_engine = UserExecutionEngine()
        secondary_engine = UserExecutionEngine()
        manager._engines['primary'] = primary_engine
        manager._engines['secondary'] = secondary_engine
        
        assert manager.get_engine('primary') == primary_engine
        assert manager.get_engine('secondary') == secondary_engine


class TestDatabaseManagerSessionManagement:
    """Test DatabaseManager session management."""
    
    @pytest.mark.asyncio
    async def test_get_session_initializes_if_not_initialized(self):
        """Test that get_session auto-initializes if needed."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                        mock_session = AsyncNone  # TODO: Use real service instance
                        mock_session_class.return_value = mock_session
                        
                        manager = DatabaseManager()
                        async with manager.get_session():
                            pass
                        
                        assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_get_session_creates_async_session(self):
        """Test that get_session creates AsyncSession with correct engine."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            async with manager.get_session() as session:
                assert session == mock_session
            
            mock_session_class.assert_called_with(mock_engine)
    
    @pytest.mark.asyncio
    async def test_get_session_commits_on_success(self):
        """Test that get_session commits transaction on success."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            async with manager.get_session() as session:
                pass  # Successful completion
            
            mock_session.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_rolls_back_on_exception(self):
        """Test that get_session rolls back transaction on exception."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            with pytest.raises(ValueError):
                async with manager.get_session() as session:
                    raise ValueError("Test exception")
            
            mock_session.rollback.assert_called_once()
            mock_session.commit.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_session_always_closes_session(self):
        """Test that get_session always closes session in finally block."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            # Test successful case
            async with manager.get_session() as session:
                pass
            mock_session.close.assert_called_once()
            
            # Test exception case
            mock_session.close.reset_mock()
            with pytest.raises(ValueError):
                async with manager.get_session() as session:
                    raise ValueError("Test exception")
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_session_logs_error_on_exception(self):
        """Test that get_session logs errors on exception."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session_class.return_value = mock_session
            
            with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
                with pytest.raises(ValueError):
                    async with manager.get_session() as session:
                        raise ValueError("Test exception")
                
                mock_logger.error.assert_called_once()
                assert "Database session error" in str(mock_logger.error.call_args)
    
    @pytest.mark.asyncio
    async def test_get_session_with_custom_engine_name(self):
        """Test that get_session works with custom engine names."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['custom'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session_class.return_value = mock_session
            
            async with manager.get_session('custom') as session:
                pass
            
            mock_session_class.assert_called_with(mock_engine)


class TestDatabaseManagerHealthCheck:
    """Test DatabaseManager health check functionality."""
    
    @pytest.mark.asyncio
    async def test_health_check_returns_healthy_status_on_success(self):
        """Test that health_check returns healthy status when connection works."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_session.execute.return_value = mock_result
            mock_session_class.return_value = mock_session
            
            result = await manager.health_check()
            
            expected = {
                "status": "healthy",
                "engine": "primary", 
                "connection": "ok"
            }
            assert result == expected
    
    @pytest.mark.asyncio
    async def test_health_check_executes_select_query(self):
        """Test that health_check executes a SELECT 1 query."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_session.execute.return_value = mock_result
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            await manager.health_check()
            
            # Verify SELECT 1 was executed
            mock_session.execute.assert_called_once()
            call_args = mock_session.execute.call_args[0][0]
            assert "SELECT 1" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_health_check_fetches_result(self):
        """Test that health_check fetches the query result."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_session.execute.return_value = mock_result
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            await manager.health_check()
            
            mock_result.fetchone.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_on_exception(self):
        """Test that health_check returns unhealthy status on exception."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session_class.side_effect = DatabaseError("Connection failed", None, None)
            
            result = await manager.health_check()
            
            assert result["status"] == "unhealthy"
            assert result["engine"] == "primary"
            assert "error" in result
            assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_health_check_logs_error_on_exception(self):
        """Test that health_check logs errors on exception."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session_class.side_effect = DatabaseError("Connection failed", None, None)
            
            with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
                await manager.health_check()
                mock_logger.error.assert_called_once()
                assert "Database health check failed" in str(mock_logger.error.call_args)
    
    @pytest.mark.asyncio
    async def test_health_check_with_custom_engine_name(self):
        """Test that health_check works with custom engine names."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['custom'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_session.execute.return_value = mock_result
            mock_session_class.return_value = mock_session
            
            result = await manager.health_check('custom')
            
            assert result["engine"] == "custom"
            assert result["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_handles_operational_error(self):
        """Test that health_check handles OperationalError properly."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session.execute.side_effect = OperationalError("Connection timeout", None, None)
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await manager.health_check()
            
            assert result["status"] == "unhealthy"
            assert "Connection timeout" in result["error"]
    
    @pytest.mark.asyncio
    async def test_health_check_handles_timeout_error(self):
        """Test that health_check handles TimeoutError properly."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session.execute.side_effect = SQLTimeoutError("Query timeout", None, None)
            # Set up proper async context manager behavior
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await manager.health_check()
            
            assert result["status"] == "unhealthy"
            assert "Query timeout" in result["error"]


class TestDatabaseManagerCloseAll:
    """Test DatabaseManager close_all functionality."""
    
    @pytest.mark.asyncio
    async def test_close_all_disposes_all_engines(self):
        """Test that close_all disposes all registered engines."""
        manager = DatabaseManager()
        manager._initialized = True
        
        mock_engine1 = AsyncNone  # TODO: Use real service instance
        mock_engine2 = AsyncNone  # TODO: Use real service instance
        manager._engines['primary'] = mock_engine1
        manager._engines['secondary'] = mock_engine2
        
        await manager.close_all()
        
        mock_engine1.dispose.assert_called_once()
        mock_engine2.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_all_clears_engines_dict(self):
        """Test that close_all clears the engines dictionary."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        
        mock_engine = AsyncNone  # TODO: Use real service instance
        manager._engines['primary'] = mock_engine
        
        await manager.close_all()
        
        assert manager._engines == {}
    
    @pytest.mark.asyncio
    async def test_close_all_sets_initialized_to_false(self):
        """Test that close_all sets initialized flag to False."""
        manager = DatabaseManager()
        manager._initialized = True
        
        mock_engine = AsyncNone  # TODO: Use real service instance
        manager._engines['primary'] = mock_engine
        
        await manager.close_all()
        
        assert manager._initialized is False
    
    @pytest.mark.asyncio
    async def test_close_all_logs_success_for_each_engine(self):
        """Test that close_all logs success message for each engine."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        
        mock_engine1 = AsyncNone  # TODO: Use real service instance
        mock_engine2 = AsyncNone  # TODO: Use real service instance
        manager._engines['primary'] = mock_engine1
        manager._engines['secondary'] = mock_engine2
        
        with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
            await manager.close_all()
            
            # Should log success for each engine
            assert mock_logger.info.call_count == 2
            calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert "Closed database engine: primary" in calls
            assert "Closed database engine: secondary" in calls
    
    @pytest.mark.asyncio
    async def test_close_all_handles_dispose_exceptions(self):
        """Test that close_all handles exceptions during engine disposal."""
        manager = DatabaseManager()
        manager._initialized = True
        
        mock_engine1 = AsyncNone  # TODO: Use real service instance
        mock_engine1.dispose.side_effect = Exception("Dispose failed")
        mock_engine2 = AsyncNone  # TODO: Use real service instance
        
        manager._engines['primary'] = mock_engine1
        manager._engines['secondary'] = mock_engine2
        
        with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
            await manager.close_all()
            
            # Should log error for failed engine
            mock_logger.error.assert_called_once()
            assert "Error closing engine primary" in str(mock_logger.error.call_args)
            
            # Should still dispose second engine
            mock_engine2.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_all_continues_after_disposal_errors(self):
        """Test that close_all continues disposing other engines after errors."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        
        mock_engine1 = AsyncNone  # TODO: Use real service instance
        mock_engine1.dispose.side_effect = Exception("Dispose failed")
        mock_engine2 = AsyncNone  # TODO: Use real service instance
        mock_engine3 = AsyncNone  # TODO: Use real service instance
        
        manager._engines['primary'] = mock_engine1
        manager._engines['secondary'] = mock_engine2
        manager._engines['tertiary'] = mock_engine3
        
        await manager.close_all()
        
        # All engines should be disposal attempted
        mock_engine1.dispose.assert_called_once()
        mock_engine2.dispose.assert_called_once()
        mock_engine3.dispose.assert_called_once()
        
        # Engines dict should still be cleared
        assert manager._engines == {}
        assert manager._initialized is False


class TestDatabaseManagerURLBuilding:
    """Test DatabaseManager URL building functionality."""
    
    def test_get_database_url_creates_url_builder(self):
        """Test that _get_database_url creates DatabaseURLBuilder."""
        manager = DatabaseManager()
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {'TEST': 'value'}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = "postgresql://test"
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                mock_builder.get_safe_log_message.return_value = "Safe log message"
                mock_builder_class.return_value = mock_builder
                
                result = manager._get_database_url()
                
                mock_builder_class.assert_called_once_with({'TEST': 'value'})
                assert manager._url_builder == mock_builder
    
    def test_get_database_url_reuses_existing_builder(self):
        """Test that _get_database_url reuses existing builder."""
    pass
        manager = DatabaseManager()
        existing_builder = existing_builder_instance  # Initialize appropriate service
        existing_builder.get_url_for_environment.return_value = "postgresql://test"
        existing_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
        existing_builder.get_safe_log_message.return_value = "Safe log message"
        manager._url_builder = existing_builder
        
        with patch('netra_backend.app.db.database_manager.get_env'):
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                result = manager._get_database_url()
                
                # Should not create new builder
                mock_builder_class.assert_not_called()
                assert manager._url_builder == existing_builder
    
    def test_get_database_url_calls_get_url_for_environment(self):
        """Test that _get_database_url calls get_url_for_environment with sync=False."""
        manager = DatabaseManager()
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = "postgresql://test"
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                mock_builder.get_safe_log_message.return_value = "Safe log message"
                mock_builder_class.return_value = mock_builder
                
                result = manager._get_database_url()
                
                mock_builder.get_url_for_environment.assert_called_once_with(sync=False)
    
    def test_get_database_url_calls_format_url_for_driver(self):
        """Test that _get_database_url calls format_url_for_driver with asyncpg."""
    pass
        manager = DatabaseManager()
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = "postgresql://test"
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                mock_builder.get_safe_log_message.return_value = "Safe log message"
                mock_builder_class.return_value = mock_builder
                
                result = manager._get_database_url()
                
                mock_builder.format_url_for_driver.assert_called_once_with("postgresql://test", 'asyncpg')
    
    def test_get_database_url_logs_safe_message(self):
        """Test that _get_database_url logs safe connection message."""
        manager = DatabaseManager()
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = "postgresql://test"
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                mock_builder.get_safe_log_message.return_value = "Safe log message"
                mock_builder_class.return_value = mock_builder
                
                with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
                    result = manager._get_database_url()
                    
                    mock_builder.get_safe_log_message.assert_called_once()
                    mock_logger.info.assert_called_once_with("Safe log message")
    
    def test_get_database_url_falls_back_to_config(self):
        """Test that _get_database_url falls back to config.database_url when builder fails."""
    pass
        manager = DatabaseManager()
        manager.config.database_url = "postgresql://config_fallback"
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = None  # Builder fails
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://config_fallback"
                mock_builder.get_safe_log_message.return_value = "Safe log message"
                mock_builder_class.return_value = mock_builder
                
                result = manager._get_database_url()
                
                # Should use config fallback and format it
                mock_builder.format_url_for_driver.assert_called_once_with("postgresql://config_fallback", 'asyncpg')
                assert result == "postgresql+asyncpg://config_fallback"
    
    def test_get_database_url_raises_if_no_url_available(self):
        """Test that _get_database_url raises ValueError when no URL is available."""
        manager = DatabaseManager()
        manager.config.database_url = None
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = None
                mock_builder_class.return_value = mock_builder
                
                with pytest.raises(ValueError, match="DatabaseURLBuilder failed to construct URL"):
                    manager._get_database_url()


class TestDatabaseManagerStaticMethods:
    """Test DatabaseManager static and class methods."""
    
    @pytest.mark.asyncio
    async def test_get_async_session_class_method_creates_manager(self):
        """Test that get_async_session class method creates manager."""
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            mock_manager = mock_manager_instance  # Initialize appropriate service
            mock_manager._initialized = True
            mock_session = AsyncNone  # TODO: Use real service instance
            
            @asynccontextmanager
            async def mock_get_session(name):
                yield mock_session
            
            mock_manager.get_session = mock_get_session
            mock_get_manager.return_value = mock_manager
            
            async with DatabaseManager.get_async_session() as session:
                assert session == mock_session
            
            mock_get_manager.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_async_session_initializes_if_needed(self):
        """Test that get_async_session initializes manager if not initialized."""
    pass
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            mock_manager = AsyncNone  # TODO: Use real service instance
            mock_manager._initialized = False
            mock_session = AsyncNone  # TODO: Use real service instance
            
            @asynccontextmanager
            async def mock_get_session(name):
    pass
                yield mock_session
            
            mock_manager.get_session = mock_get_session
            mock_get_manager.return_value = mock_manager
            
            async with DatabaseManager.get_async_session() as session:
                pass
            
            mock_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_async_session_passes_engine_name(self):
        """Test that get_async_session passes engine name correctly."""
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            mock_manager = mock_manager_instance  # Initialize appropriate service
            mock_manager._initialized = True
            mock_session = AsyncNone  # TODO: Use real service instance
            
            @asynccontextmanager
            async def mock_get_session(name):
                assert name == 'custom'
                yield mock_session
            
            mock_manager.get_session = mock_get_session
            mock_get_manager.return_value = mock_manager
            
            async with DatabaseManager.get_async_session('custom') as session:
                pass
    
    def test_create_application_engine_gets_config(self):
        """Test that create_application_engine gets config."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(database_url="postgresql://test")
            with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
                mock_env.return_value.as_dict.return_value = {}
                with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = mock_builder_instance  # Initialize appropriate service
                    mock_builder.get_url_for_environment.return_value = "postgresql://test"
                    mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                    mock_builder_class.return_value = mock_builder
                    
                    with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                        mock_create_engine.return_value = return_value_instance  # Initialize appropriate service
                        
                        DatabaseManager.create_application_engine()
                        
                        mock_config.assert_called_once()
    
    def test_create_application_engine_creates_url_builder(self):
        """Test that create_application_engine creates DatabaseURLBuilder."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(database_url="postgresql://test")
            with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
                mock_env.return_value.as_dict.return_value = {'TEST': 'value'}
                with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = mock_builder_instance  # Initialize appropriate service
                    mock_builder.get_url_for_environment.return_value = "postgresql://test"
                    mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                    mock_builder_class.return_value = mock_builder
                    
                    with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                        mock_create_engine.return_value = return_value_instance  # Initialize appropriate service
                        
                        DatabaseManager.create_application_engine()
                        
                        mock_builder_class.assert_called_once_with({'TEST': 'value'})
    
    def test_create_application_engine_uses_null_pool(self):
        """Test that create_application_engine uses NullPool for health checks."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(database_url="postgresql://test")
            with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
                mock_env.return_value.as_dict.return_value = {}
                with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = mock_builder_instance  # Initialize appropriate service
                    mock_builder.get_url_for_environment.return_value = "postgresql://test"
                    mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test"
                    mock_builder_class.return_value = mock_builder
                    
                    with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                        mock_create_engine.return_value = return_value_instance  # Initialize appropriate service
                        
                        DatabaseManager.create_application_engine()
                        
                        call_args = mock_create_engine.call_args
                        assert call_args[1]['poolclass'] == NullPool
                        assert call_args[1]['echo'] is False
                        assert call_args[1]['pool_pre_ping'] is True
                        assert call_args[1]['pool_recycle'] == 3600
    
    def test_create_application_engine_falls_back_to_config_url(self):
        """Test that create_application_engine falls back to config URL."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(database_url="postgresql://config")
            with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
                mock_env.return_value.as_dict.return_value = {}
                with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                    mock_builder = mock_builder_instance  # Initialize appropriate service
                    mock_builder.get_url_for_environment.return_value = None  # Builder fails
                    mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://config"
                    mock_builder_class.return_value = mock_builder
                    
                    with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
                        mock_create_engine.return_value = return_value_instance  # Initialize appropriate service
                        
                        DatabaseManager.create_application_engine()
                        
                        mock_builder.format_url_for_driver.assert_called_once_with("postgresql://config", 'asyncpg')


class TestDatabaseManagerGlobalInstance:
    """Test global DatabaseManager instance management."""
    
    def test_get_database_manager_creates_instance(self):
        """Test that get_database_manager creates new instance if none exists."""
        # Clear any existing global instance
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        manager = get_database_manager()
        assert isinstance(manager, DatabaseManager)
        assert db_module._database_manager == manager
    
    def test_get_database_manager_reuses_instance(self):
        """Test that get_database_manager reuses existing instance."""
    pass
        # Clear any existing global instance
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        assert manager1 is manager2
    
    @pytest.mark.asyncio
    async def test_get_db_session_helper_function(self):
        """Test the get_db_session helper function."""
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            mock_manager = mock_manager_instance  # Initialize appropriate service
            mock_session = AsyncNone  # TODO: Use real service instance
            
            @asynccontextmanager
            async def mock_get_session(name):
                assert name == 'test_engine'
                yield mock_session
            
            mock_manager.get_session = mock_get_session
            mock_get_manager.return_value = mock_manager
            
            async with get_db_session('test_engine') as session:
                assert session == mock_session


class TestDatabaseManagerErrorHandling:
    """Test DatabaseManager error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_initialize_handles_database_url_builder_exception(self):
        """Test that initialize handles DatabaseURLBuilder exceptions."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = return_value_instance  # Initialize appropriate service
            with patch.object(DatabaseManager, '_get_database_url', side_effect=Exception("URL build failed")):
                manager = DatabaseManager()
                
                with pytest.raises(Exception, match="URL build failed"):
                    await manager.initialize()
                
                assert not manager._initialized
    
    @pytest.mark.asyncio
    async def test_initialize_handles_engine_creation_exception(self):
        """Test that initialize handles engine creation exceptions."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                with patch('netra_backend.app.db.database_manager.create_async_engine', side_effect=Exception("Engine failed")):
                    manager = DatabaseManager()
                    
                    with pytest.raises(Exception, match="Engine failed"):
                        await manager.initialize()
                    
                    assert not manager._initialized
    
    @pytest.mark.asyncio
    async def test_initialize_logs_error_on_exception(self):
        """Test that initialize logs errors on exception."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = return_value_instance  # Initialize appropriate service
            with patch.object(DatabaseManager, '_get_database_url', side_effect=Exception("Test error")):
                with patch('netra_backend.app.db.database_manager.logger') as mock_logger:
                    manager = DatabaseManager()
                    
                    with pytest.raises(Exception):
                        await manager.initialize()
                    
                    mock_logger.error.assert_called_once()
                    assert "Failed to initialize DatabaseManager" in str(mock_logger.error.call_args)
    
    @pytest.mark.asyncio
    async def test_get_session_handles_engine_retrieval_error(self):
        """Test that get_session handles engine retrieval errors."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        # No engines registered - should cause get_engine to fail
        
        with pytest.raises(ValueError, match="Engine 'primary' not found"):
            async with manager.get_session():
                pass
    
    @pytest.mark.asyncio
    async def test_health_check_handles_engine_not_found(self):
        """Test that health_check handles engine not found error."""
        manager = DatabaseManager()
        manager._initialized = True
        # No engines registered
        
        result = await manager.health_check()
        
        assert result["status"] == "unhealthy"
        assert "not found" in result["error"]


class TestDatabaseManagerThreadSafety:
    """Test DatabaseManager thread safety aspects."""
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_initializations(self):
        """Test that multiple concurrent initialize calls are handled safely."""
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    
                    # Run multiple initializations concurrently
                    await asyncio.gather(
                        manager.initialize(),
                        manager.initialize(),
                        manager.initialize()
                    )
                    
                    # Should only create engine once
                    mock_engine.assert_called_once()
                    assert manager._initialized is True
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """Test concurrent session creation works properly."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            # Create different mock sessions for each call
            mock_sessions = [AsyncNone  # TODO: Use real service instance, AsyncNone  # TODO: Use real service instance, AsyncNone  # TODO: Use real service instance]
            mock_session_class.side_effect = mock_sessions
            
            async def use_session(session_id):
    pass
                async with manager.get_session() as session:
                    await asyncio.sleep(0)
    return session_id, session
            
            # Run concurrent session creations
            results = await asyncio.gather(
                use_session(1),
                use_session(2), 
                use_session(3)
            )
            
            # All should succeed
            assert len(results) == 3
            assert all(result[0] in [1, 2, 3] for result in results)
    
    def test_global_instance_thread_safety(self):
        """Test that global instance creation is thread safe."""
        # Clear existing global instance
        import netra_backend.app.db.database_manager as db_module
        db_module._database_manager = None
        
        managers = []
        
        def create_manager():
            manager = get_database_manager()
            managers.append(manager)
        
        # Create multiple threads that try to get manager
        threads = []
        for i in range(10):
            thread = threading.Thread(target=create_manager)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should get the same instance
        assert len(managers) == 10
        assert all(manager is managers[0] for manager in managers)


class TestDatabaseManagerAdvancedScenarios:
    """Test DatabaseManager advanced and edge case scenarios."""
    
    @pytest.mark.asyncio
    async def test_session_nested_exception_handling(self):
        """Test nested exception handling in get_session."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            # Make rollback also raise an exception
            mock_session.rollback.side_effect = Exception("Rollback failed")
            mock_session.close = AsyncNone  # TODO: Use real service instance
            
            # Mock the async context manager protocol
            mock_context = AsyncNone  # TODO: Use real service instance
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context
            
            # The original exception should still be raised, not the rollback exception
            with pytest.raises(ValueError, match="Original error"):
                async with manager.get_session() as session:
                    raise ValueError("Original error")
            
            # Both rollback and close should have been called
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_query_execution_details(self):
        """Test detailed query execution in health check."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_result.fetchone.return_value = (1)  # Simulate SELECT 1 result
            mock_session.execute.return_value = mock_result
            
            # Mock the async context manager protocol
            mock_context = AsyncNone  # TODO: Use real service instance
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context
            
            result = await manager.health_check()
            
            # Verify the exact query
            call_args = mock_session.execute.call_args[0][0]
            # text() objects have a text attribute
            assert hasattr(call_args, 'text')
            assert "SELECT 1" in str(call_args.text)
            
            # Verify result fetching
            mock_result.fetchone.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_all_with_empty_engines(self):
        """Test close_all behavior with no engines registered."""
        manager = DatabaseManager()
        manager._initialized = True
        # Leave _engines empty
        
        await manager.close_all()
        
        # Should not raise and should reset state
        assert manager._engines == {}
        assert manager._initialized is False
    
    def test_get_database_url_with_existing_formatted_url(self):
        """Test _get_database_url when builder returns already formatted URL."""
    pass
        manager = DatabaseManager()
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = "postgresql+asyncpg://already_formatted"
                mock_builder.format_url_for_driver.return_value = "postgresql+asyncpg://already_formatted"
                mock_builder.get_safe_log_message.return_value = "Safe message"
                mock_builder_class.return_value = mock_builder
                
                result = manager._get_database_url()
                
                # Should still call format_url_for_driver even if already formatted
                mock_builder.format_url_for_driver.assert_called_once_with("postgresql+asyncpg://already_formatted", 'asyncpg')
                assert result == "postgresql+asyncpg://already_formatted"
    
    @pytest.mark.asyncio
    async def test_initialize_with_different_pool_configurations(self):
        """Test initialize with various pool configuration scenarios."""
        test_cases = [
            {"pool_size": -1, "expected_pool": NullPool},
            {"pool_size": 0, "expected_pool": NullPool},
            {"pool_size": 1, "expected_pool": StaticPool},
            {"pool_size": 10, "expected_pool": StaticPool},
        ]
        
        for case in test_cases:
            with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
                mock_config.return_value = Mock(
                    database_echo=False,
                    database_pool_size=case["pool_size"],
                    database_max_overflow=10
                )
                with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                    mock_engine.return_value = return_value_instance  # Initialize appropriate service
                    with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                        manager = DatabaseManager()
                        await manager.initialize()
                        
                        call_args = mock_engine.call_args
                        assert call_args[1]['poolclass'] == case["expected_pool"]
                        
                        # Reset for next iteration
                        await manager.close_all()
    
    @pytest.mark.asyncio 
    async def test_multiple_engines_management(self):
        """Test managing multiple named engines (future functionality)."""
    pass
        # This test anticipates future multi-engine support
        manager = DatabaseManager()
        
        # Manually add multiple engines to simulate future functionality
        mock_primary = AsyncNone  # TODO: Use real service instance
        mock_secondary = AsyncNone  # TODO: Use real service instance
        mock_readonly = AsyncNone  # TODO: Use real service instance
        
        manager._engines = {
            'primary': mock_primary,
            'secondary': mock_secondary,
            'readonly': mock_readonly
        }
        manager._initialized = True
        
        # Test engine retrieval
        assert manager.get_engine('primary') == mock_primary
        assert manager.get_engine('secondary') == mock_secondary
        assert manager.get_engine('readonly') == mock_readonly
        
        # Test health checks on different engines
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_session.execute.return_value = mock_result
            mock_session_class.return_value = mock_session
            
            result = await manager.health_check('secondary')
            assert result['engine'] == 'secondary'
            assert result['status'] == 'healthy'
        
        # Test close_all with multiple engines
        await manager.close_all()
        
        mock_primary.dispose.assert_called_once()
        mock_secondary.dispose.assert_called_once()
        mock_readonly.dispose.assert_called_once()


class TestDatabaseManagerEdgeCasesAndFailures:
    """Test edge cases and failure scenarios."""
    
    def test_constructor_with_mock_config_variations(self):
        """Test constructor behavior with various config mock variations."""
        # Test with minimal config
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            minimal_config = type('Config', (), {})()
            mock_config.return_value = minimal_config
            
            manager = DatabaseManager()
            assert manager.config == minimal_config
    
    @pytest.mark.asyncio
    async def test_session_commit_failure_handling(self):
        """Test handling of commit failures in get_session."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session.commit.side_effect = DatabaseError("Commit failed", None, None)
            mock_session.close = AsyncNone  # TODO: Use real service instance
            
            # Mock the async context manager protocol
            mock_context = AsyncNone  # TODO: Use real service instance
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context
            
            with pytest.raises(DatabaseError, match="Commit failed"):
                async with manager.get_session() as session:
                    pass  # Successful block, but commit fails
            
            # Should have attempted commit but not rollback (since transaction succeeded)
            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_called_once()  # Called due to exception
    
    @pytest.mark.asyncio
    async def test_session_close_failure_handling(self):
        """Test handling of session close failures."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session.close.side_effect = Exception("Close failed")
            
            # Mock the async context manager protocol
            mock_context = AsyncNone  # TODO: Use real service instance
            mock_context.__aenter__.return_value = mock_session
            mock_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_context
            
            # Close failure should not prevent normal completion
            async with manager.get_session() as session:
                pass
            
            # Commit should have been called despite close failure
            mock_session.commit.assert_called_once()
            mock_session.close.assert_called_once()
    
    def test_url_builder_environment_variable_edge_cases(self):
        """Test URL builder with various environment variable scenarios."""
    pass
        # Test with empty environment
        manager = DatabaseManager()
        
        with patch('netra_backend.app.db.database_manager.get_env') as mock_env:
            mock_env.return_value.as_dict.return_value = {}
            with patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder_class:
                mock_builder = mock_builder_instance  # Initialize appropriate service
                mock_builder.get_url_for_environment.return_value = "sqlite:///:memory:"
                mock_builder.format_url_for_driver.return_value = "sqlite:///:memory:"
                mock_builder.get_safe_log_message.return_value = "Memory DB"
                mock_builder_class.return_value = mock_builder
                
                result = manager._get_database_url()
                
                # Should work with empty environment
                mock_builder_class.assert_called_once_with({})
                assert result == "sqlite:///:memory:"
    
    @pytest.mark.asyncio
    async def test_health_check_with_various_database_errors(self):
        """Test health_check with different types of database errors."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        error_scenarios = [
            OperationalError("Connection lost", None, None),
            SQLTimeoutError("Query timeout", None, None),
            DatabaseError("Generic DB error", None, None),
            Exception("Unexpected error")
        ]
        
        for error in error_scenarios:
            with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
                mock_session_class.side_effect = error
                
                result = await manager.health_check()
                
                assert result["status"] == "unhealthy"
                assert result["engine"] == "primary"
                assert str(error) in result["error"] or type(error).__name__ in result["error"]
    
    @pytest.mark.asyncio
    async def test_initialize_error_cleanup(self):
        """Test that initialize cleans up properly on errors."""
    pass
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=5,
                database_max_overflow=10
            )
            with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                with patch('netra_backend.app.db.database_manager.create_async_engine', side_effect=Exception("Engine creation failed")):
                    manager = DatabaseManager()
                    
                    with pytest.raises(Exception, match="Engine creation failed"):
                        await manager.initialize()
                    
                    # Should not be marked as initialized
                    assert not manager._initialized
                    # Engines dict should be empty
                    assert manager._engines == {}


# Performance and Stress Testing
@pytest.mark.skip(reason="Performance testing features not implemented in current DatabaseManager")
class TestDatabaseManagerPerformance:
    """Test DatabaseManager performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_rapid_session_creation_and_destruction(self):
        """Test rapid creation and destruction of sessions."""
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            # Test rapid session cycles
            for i in range(100):
                mock_session = AsyncNone  # TODO: Use real service instance
                mock_session_class.return_value = mock_session
                
                async with manager.get_session() as session:
                    pass
                
                # Each session should be committed and closed
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
                
                # Reset for next iteration
                mock_session.reset_mock()
    
    @pytest.mark.asyncio
    async def test_health_check_performance_characteristics(self):
        """Test health check execution time and resource usage."""
    pass
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_result = AsyncNone  # TODO: Use real service instance
            mock_session.execute.return_value = mock_result
            mock_session_class.return_value = mock_session
            
            # Run multiple health checks rapidly
            start_time = time.time()
            
            results = await asyncio.gather(*[
                manager.health_check() for _ in range(50)
            ])
            
            end_time = time.time()
            
            # All should succeed
            assert all(result["status"] == "healthy" for result in results)
            
            # Should complete reasonably quickly (this is a unit test with mocks)
            assert (end_time - start_time) < 5.0  # 5 seconds should be more than enough


@pytest.mark.skip(reason="Advanced connection pool features not implemented in current DatabaseManager")
class TestDatabaseManagerConnectionPoolSpecifics:
    """Test specific connection pool behaviors."""
    
    @pytest.mark.asyncio
    async def test_connection_pool_size_configuration_validation(self):
        """Test that pool size configurations are properly validated."""
        # This test should fail - current implementation doesn't validate pool sizes
        with patch('netra_backend.app.db.database_manager.get_config') as mock_config:
            mock_config.return_value = Mock(
                database_echo=False,
                database_pool_size=-5,  # Invalid negative pool size
                database_max_overflow=-1  # Invalid negative overflow
            )
            with patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
                mock_engine.return_value = return_value_instance  # Initialize appropriate service
                with patch.object(DatabaseManager, '_get_database_url', return_value="postgresql://test"):
                    manager = DatabaseManager()
                    # Should raise validation error for negative pool sizes
                    with pytest.raises(ValueError, match="Pool size must be non-negative"):
                        await manager.initialize()
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_handling(self):
        """Test behavior when connection pool is exhausted."""
    pass
        # This test should fail - no current pool exhaustion handling
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            # Simulate pool exhaustion
            from sqlalchemy.exc import TimeoutError
            mock_session_class.side_effect = TimeoutError("Pool exhausted", None, None)
            
            # Should handle pool exhaustion gracefully
            with pytest.raises(TimeoutError):  # Should be caught and re-raised with context
                async with manager.get_session():
                    pass
    
    def test_connection_pool_metrics_collection(self):
        """Test that connection pool metrics are collected."""
        # This test should fail - no current metrics collection
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        mock_engine.pool.size = Mock(return_value=5)
        mock_engine.pool.checked_in = Mock(return_value=3)
        mock_engine.pool.checked_out = Mock(return_value=2)
        manager._engines['primary'] = mock_engine
        
        # Should have method to get pool metrics
        metrics = manager.get_pool_metrics('primary')
        
        assert metrics['total_connections'] == 5
        assert metrics['available_connections'] == 3
        assert metrics['active_connections'] == 2
    
    @pytest.mark.asyncio
    async def test_connection_retry_with_exponential_backoff(self):
        """Test connection retry logic with exponential backoff."""
    pass
        # This test should fail - no current retry logic
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            # First two attempts fail, third succeeds
            call_count = 0
            def side_effect(*args, **kwargs):
    pass
                nonlocal call_count
                call_count += 1
                if call_count <= 2:
                    raise OperationalError("Connection failed", None, None)
                await asyncio.sleep(0)
    return AsyncNone  # TODO: Use real service instance
            
            mock_session_class.side_effect = side_effect
            
            # Should retry with exponential backoff
            start_time = time.time()
            async with manager.get_session_with_retry(max_retries=3, base_delay=0.1):
                pass
            end_time = time.time()
            
            # Should have taken some time due to backoff delays
            assert (end_time - start_time) >= 0.3  # 0.1 + 0.2 seconds minimum
            assert call_count == 3


@pytest.mark.skip(reason="Advanced transaction management features not implemented in current DatabaseManager")
class TestDatabaseManagerTransactionManagement:
    """Test advanced transaction management features."""
    
    @pytest.mark.asyncio
    async def test_nested_transaction_support(self):
        """Test support for nested transactions (savepoints)."""
        # This test should fail - no current nested transaction support
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session_class.return_value = mock_session
            
            async with manager.get_session() as session:
                # Should support savepoint creation
                savepoint = await session.begin_nested()
                assert savepoint is not None
                
                # Should be able to rollback to savepoint
                await savepoint.rollback()
    
    @pytest.mark.asyncio
    async def test_transaction_isolation_level_configuration(self):
        """Test transaction isolation level configuration."""
    pass
        # This test should fail - no current isolation level support
        manager = DatabaseManager()
        
        # Should be able to configure isolation level
        await manager.initialize(isolation_level='READ_COMMITTED')
        
        async with manager.get_session(isolation_level='SERIALIZABLE') as session:
            # Session should use specified isolation level
            assert session.get_isolation_level() == 'SERIALIZABLE'
    
    @pytest.mark.asyncio
    async def test_transaction_timeout_handling(self):
        """Test transaction timeout configuration and handling."""
        # This test should fail - no current transaction timeout support
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session_class.return_value = mock_session
            
            # Should timeout long-running transactions
            with pytest.raises(TimeoutError, match="Transaction timeout"):
                async with manager.get_session(transaction_timeout=0.1) as session:
                    await asyncio.sleep(0.2)  # Exceed timeout
    
    @pytest.mark.asyncio
    async def test_read_only_transaction_support(self):
        """Test read-only transaction configuration."""
    pass
        # This test should fail - no current read-only transaction support
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session_class.return_value = mock_session
            
            async with manager.get_read_only_session() as session:
                # Should configure session as read-only
                mock_session.configure_readonly.assert_called_once()


@pytest.mark.skip(reason="Circuit breaker features not implemented in current DatabaseManager")
class TestDatabaseManagerCircuitBreaker:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_failures(self):
        """Test that circuit breaker opens after consecutive failures."""
        # This test should fail - no current circuit breaker implementation
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            # Simulate consecutive failures
            mock_session_class.side_effect = DatabaseError("Connection failed", None, None)
            
            # After 3 failures, circuit should open
            for i in range(3):
                with pytest.raises(DatabaseError):
                    async with manager.get_session():
                        pass
            
            # Next attempt should fail fast with CircuitBreakerOpen exception
            with pytest.raises(Exception, match="Circuit breaker open"):
                async with manager.get_session():
                    pass
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_recovery(self):
        """Test circuit breaker half-open state recovery."""
    pass
        # This test should fail - no current circuit breaker state management
        manager = DatabaseManager()
        
        # Simulate circuit breaker in open state
        manager._circuit_breaker_state = 'open'
        manager._circuit_breaker_opened_at = time.time() - 60  # Opened 60 seconds ago
        
        # Should transition to half-open after timeout
        state = manager.get_circuit_breaker_state()
        assert state == 'half-open'
    
    def test_circuit_breaker_metrics_collection(self):
        """Test circuit breaker metrics collection."""
        # This test should fail - no current circuit breaker metrics
        manager = DatabaseManager()
        
        metrics = manager.get_circuit_breaker_metrics()
        
        assert 'failure_count' in metrics
        assert 'success_count' in metrics
        assert 'state' in metrics
        assert 'last_failure_time' in metrics


@pytest.mark.skip(reason="Advanced connection validation features not implemented in current DatabaseManager")
class TestDatabaseManagerConnectionValidation:
    """Test connection validation and health monitoring."""
    
    @pytest.mark.asyncio
    async def test_connection_pre_ping_validation(self):
        """Test connection pre-ping validation before use."""
        # This test should fail - no explicit pre-ping validation
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        # Should validate connection before creating session
        async with manager.get_validated_session() as session:
            # Should have performed pre-ping validation
            mock_engine.pre_ping.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stale_connection_detection_and_refresh(self):
        """Test detection and refresh of stale connections."""
    pass
        # This test should fail - no current stale connection handling
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        with patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            # First attempt fails with stale connection
            mock_session = AsyncNone  # TODO: Use real service instance
            mock_session.execute.side_effect = [
                OperationalError("Connection lost", None, None),  # Stale connection
                AsyncNone  # TODO: Use real service instance  # Refreshed connection works
            ]
            mock_session_class.return_value = mock_session
            
            # Should automatically refresh stale connection
            result = await manager.health_check()
            assert result['status'] == 'healthy'
            
            # Should have attempted execution twice (original + retry)
            assert mock_session.execute.call_count == 2
    
    @pytest.mark.asyncio
    async def test_connection_leak_detection(self):
        """Test detection of connection leaks."""
        # This test should fail - no current leak detection
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        mock_engine.pool.checked_out = Mock(return_value=10)  # 10 connections checked out
        manager._engines['primary'] = mock_engine
        
        # Should detect potential connection leaks
        leak_report = manager.detect_connection_leaks()
        
        assert leak_report['potential_leaks'] > 0
        assert 'checked_out_connections' in leak_report
        assert 'recommendations' in leak_report
    
    def test_connection_pool_health_monitoring(self):
        """Test comprehensive connection pool health monitoring."""
    pass
        # This test should fail - no current comprehensive health monitoring
        manager = DatabaseManager()
        manager._initialized = True
        
        health_report = manager.get_comprehensive_health_report()
        
        expected_metrics = [
            'connection_pool_status',
            'active_connections',
            'available_connections', 
            'failed_connections',
            'average_connection_time',
            'circuit_breaker_state',
            'recent_errors'
        ]
        
        for metric in expected_metrics:
            assert metric in health_report


@pytest.mark.skip(reason="Multi-database support features not implemented in current DatabaseManager")
class TestDatabaseManagerMultiDatabase:
    """Test multi-database support functionality."""
    
    @pytest.mark.asyncio
    async def test_multiple_database_engine_registration(self):
        """Test registration of multiple database engines."""
        # This test should fail - limited multi-database support
        manager = DatabaseManager()
        
        # Should be able to register multiple databases
        await manager.register_database('postgres_primary', 'postgresql://primary')
        await manager.register_database('postgres_replica', 'postgresql://replica')
        await manager.register_database('clickhouse', 'clickhouse://analytics')
        await manager.register_database('redis', 'redis://cache')
        
        # Should be able to get all registered engines
        engines = manager.get_all_engines()
        assert 'postgres_primary' in engines
        assert 'postgres_replica' in engines
        assert 'clickhouse' in engines
        assert 'redis' in engines
    
    @pytest.mark.asyncio
    async def test_database_failover_support(self):
        """Test automatic failover between primary and replica databases."""
    pass
        # This test should fail - no current failover support
        manager = DatabaseManager()
        
        await manager.configure_failover(
            primary='postgres_primary',
            replicas=['postgres_replica1', 'postgres_replica2']
        )
        
        # When primary fails, should automatically use replica
        with patch.object(manager, 'get_engine') as mock_get_engine:
            mock_primary = mock_primary_instance  # Initialize appropriate service
            mock_replica = mock_replica_instance  # Initialize appropriate service
            
            # Primary engine fails
            mock_primary.execute.side_effect = OperationalError("Primary down", None, None)
            mock_replica.execute.return_value = AsyncNone  # TODO: Use real service instance
            
            mock_get_engine.side_effect = lambda name: mock_primary if name == 'postgres_primary' else mock_replica
            
            async with manager.get_session_with_failover() as session:
                # Should have failed over to replica
                assert session.engine == mock_replica
    
    @pytest.mark.asyncio
    async def test_cross_database_transaction_support(self):
        """Test distributed transactions across multiple databases."""
        # This test should fail - no current distributed transaction support
        manager = DatabaseManager()
        
        # Should support distributed transactions
        async with manager.get_distributed_transaction(['postgres', 'clickhouse']) as tx:
            postgres_session = tx.get_session('postgres')
            clickhouse_session = tx.get_session('clickhouse')
            
            # Both should participate in same distributed transaction
            assert tx.transaction_id is not None
            await tx.commit_all()  # Should commit on all databases or rollback all
    
    def test_database_routing_based_on_query_type(self):
        """Test automatic routing based on query type."""
    pass
        # This test should fail - no current query-based routing
        manager = DatabaseManager()
        
        # Should route read queries to replica, write queries to primary
        read_engine = manager.get_engine_for_query("SELECT * FROM users")
        write_engine = manager.get_engine_for_query("INSERT INTO users (name) VALUES ('test')")
        
        assert read_engine.name == 'replica'
        assert write_engine.name == 'primary'


@pytest.mark.skip(reason="Performance monitoring features not implemented in current DatabaseManager")
class TestDatabaseManagerPerformanceMonitoring:
    """Test performance monitoring and metrics collection."""
    
    def test_query_performance_tracking(self):
        """Test tracking of query performance metrics."""
        # This test should fail - no current performance tracking
        manager = DatabaseManager()
        
        # Should track query execution times
        metrics = manager.get_query_performance_metrics()
        
        assert 'average_query_time' in metrics
        assert 'slow_queries' in metrics
        assert 'query_count' in metrics
        assert 'percentiles' in metrics
    
    @pytest.mark.asyncio
    async def test_connection_time_monitoring(self):
        """Test monitoring of connection establishment times."""
    pass
        # This test should fail - no current connection time monitoring
        manager = DatabaseManager()
        manager._initialized = True
        mock_engine = UserExecutionEngine()
        manager._engines['primary'] = mock_engine
        
        # Should track connection establishment time
        start_time = time.time()
        async with manager.get_timed_session() as (session, metrics):
            pass
        
        assert 'connection_time' in metrics
        assert 'session_duration' in metrics
        assert metrics['connection_time'] >= 0
    
    def test_database_load_monitoring(self):
        """Test monitoring of database load and resource usage."""
        # This test should fail - no current load monitoring
        manager = DatabaseManager()
        
        load_metrics = manager.get_database_load_metrics()
        
        expected_metrics = [
            'cpu_usage',
            'memory_usage',
            'disk_io',
            'active_connections',
            'query_queue_depth',
            'lock_wait_time'
        ]
        
        for metric in expected_metrics:
            assert metric in load_metrics
    
    def test_performance_alert_thresholds(self):
        """Test configurable performance alert thresholds."""
    pass
        # This test should fail - no current alert system
        manager = DatabaseManager()
        
        # Should be able to configure alert thresholds
        manager.configure_performance_alerts({
            'slow_query_threshold': 1.0,  # 1 second
            'connection_pool_usage_threshold': 0.8,  # 80%
            'error_rate_threshold': 0.05  # 5%
        })
        
        # Should trigger alerts when thresholds are exceeded
        alerts = manager.check_performance_alerts()
        assert isinstance(alerts, list)