"""Comprehensive DatabaseManager Unit Test Suite

CRITICAL: Unit tests for DatabaseManager following TEST_CREATION_GUIDE.md patterns.
Tests core business functionality that protects $500K+ ARR through data integrity.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Foundation for ALL services
- Business Goal: Ensure DatabaseManager reliably manages database connections and transactions
- Value Impact: Prevents data corruption, connection leaks, and service outages 
- Strategic Impact: DatabaseManager failures cascade to all services causing total platform failure

TEST PHILOSOPHY: Unit Testing with Real Business Value
- Tests configuration management and URL construction logic
- Validates connection pool management and resource cleanup
- Tests auto-initialization safety patterns critical for staging
- Covers error handling preventing silent data corruption
- Tests DatabaseURLBuilder SSOT integration patterns

COVERAGE TARGETS:
1. DatabaseManager Initialization & Configuration (6 tests)
2. Connection Pool Management & Resource Cleanup (4 tests) 
3. DatabaseURLBuilder SSOT Integration & URL Construction (5 tests)
4. Session Management & Transaction Safety (3 tests)
5. Error Handling & Auto-initialization Safety (2 tests)

CRITICAL: No external dependencies - pure unit tests validating business logic.
Each test protects specific business value and revenue streams.
"""

import asyncio
import pytest
import logging
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.pool import NullPool, StaticPool
from sqlalchemy import text
import time

# SSOT imports - absolute paths required per CLAUDE.md
from netra_backend.app.db.database_manager import DatabaseManager, get_database_manager, get_db_session
from shared.database_url_builder import DatabaseURLBuilder
from shared.isolated_environment import IsolatedEnvironment
from test_framework.ssot.base_test_case import SSotBaseTestCase as BaseTestCase

logger = logging.getLogger(__name__)


class TestDatabaseManagerConfiguration(BaseTestCase):
    """Unit tests for DatabaseManager configuration and initialization.
    
    Business Value: Prevents configuration errors causing service startup failures ($500K+ ARR impact)
    """
    
    def setup_method(self):
        """Reset global state for each test."""
        super().setup_method()
        # Reset global database manager singleton
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    @pytest.mark.unit
    def test_database_manager_initialization_config_validation(self):
        """Test DatabaseManager initialization validates configuration correctly.
        
        Business Value: Prevents startup failures that block all user access.
        Protects: $500K+ ARR from total platform downtime
        """
        with patch('netra_backend.app.core.config.get_config') as mock_config:
            mock_config.return_value.database_echo = True
            mock_config.return_value.database_pool_size = 10
            mock_config.return_value.database_max_overflow = 20
            
            db_manager = DatabaseManager()
            
            # Verify initial state
            assert not db_manager._initialized
            assert len(db_manager._engines) == 0
            assert db_manager._url_builder is None
            
            # Verify config is stored
            assert db_manager.config is not None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_manager_initialization_creates_engines(self):
        """Test DatabaseManager initialization creates engines with correct configuration.
        
        Business Value: Ensures proper database connection pooling for scalability.
        Protects: User experience from connection timeout errors
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Verify initialization
            assert db_manager._initialized
            assert 'primary' in db_manager._engines
            assert db_manager._engines['primary'] is mock_engine
            
            # Verify engine creation called with correct parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            assert call_args[0][0] == test_url
            assert call_args[1]['echo'] is False
            assert call_args[1]['pool_pre_ping'] is True
            assert call_args[1]['pool_recycle'] == 3600
    
    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_database_manager_sqlite_pooling_configuration(self):
        """Test DatabaseManager uses correct pooling for SQLite databases.
        
        Business Value: Ensures proper SQLite handling for test environments.
        Protects: Test infrastructure reliability and developer productivity
        """
        test_url = "sqlite+aiosqlite:///test.db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5  # Should be ignored for SQLite
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Verify SQLite uses NullPool
            call_args = mock_create_engine.call_args
            assert call_args[1]['poolclass'] == NullPool
    
    @pytest.mark.unit
    def test_database_manager_pool_size_configuration(self):
        """Test DatabaseManager handles various pool size configurations.
        
        Business Value: Prevents connection pool exhaustion under load.
        Protects: Platform stability under concurrent user load
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        # Test zero pool size
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 0  # Zero pool size
            mock_config.return_value.database_max_overflow = 0
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            
            # Use asyncio.run for async initialization
            async def test_init():
                await db_manager.initialize()
                # Verify NullPool is used for zero pool size
                call_args = mock_create_engine.call_args
                assert call_args[1]['poolclass'] == NullPool
            
            asyncio.run(test_init())
    
    @pytest.mark.unit 
    def test_database_manager_config_attribute_fallbacks(self):
        """Test DatabaseManager handles missing config attributes gracefully.
        
        Business Value: Ensures backward compatibility during config changes.
        Protects: Deployment stability during configuration updates
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            # Mock config with missing attributes
            mock_config_obj = Mock()
            # Simulate missing database_echo attribute
            mock_config_obj.database_echo = None  # This will cause getattr to return default
            mock_config_obj.database_pool_size = None
            mock_config_obj.database_max_overflow = None
            
            # Use side_effect to simulate getattr behavior
            def getattr_side_effect(obj, attr, default=None):
                if attr == 'database_echo':
                    return False
                elif attr == 'database_pool_size':
                    return 5
                elif attr == 'database_max_overflow':
                    return 10
                return default
            
            mock_config.return_value = mock_config_obj
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            
            # Patch getattr to simulate attribute fallback
            with patch('netra_backend.app.db.database_manager.getattr', side_effect=getattr_side_effect):
                async def test_init():
                    await db_manager.initialize()
                    # Should succeed with default values
                    call_args = mock_create_engine.call_args
                    assert call_args[1]['echo'] is False
                
                asyncio.run(test_init())
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_database_manager_initialization_error_handling(self):
        """Test DatabaseManager handles initialization errors properly.
        
        Business Value: Provides clear error messages for troubleshooting.
        Protects: Developer productivity and deployment debugging
        """
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', side_effect=ValueError("Invalid database URL")):
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            db_manager = DatabaseManager()
            
            # Initialization should raise the original error
            with pytest.raises(ValueError, match="Invalid database URL"):
                await db_manager.initialize()
            
            # Manager should remain uninitialized
            assert not db_manager._initialized
            assert len(db_manager._engines) == 0


class TestDatabaseManagerConnectionPool(BaseTestCase):
    """Unit tests for DatabaseManager connection pool management.
    
    Business Value: Prevents connection leaks and resource exhaustion ($500K+ ARR impact)
    """
    
    def setup_method(self):
        """Reset global state for each test."""
        super().setup_method()
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    @pytest.mark.unit
    def test_get_engine_with_auto_initialization(self):
        """Test get_engine auto-initializes when needed for staging safety.
        
        Business Value: Prevents "not initialized" errors in staging deployments.
        Protects: Service availability during startup sequences
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine, \
             patch('asyncio.create_task') as mock_create_task, \
             patch('time.sleep') as mock_sleep:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            
            # Simulate successful auto-initialization
            def side_effect(coro):
                # Simulate initialization completing
                db_manager._initialized = True
                db_manager._engines['primary'] = mock_engine
                return Mock()
            
            mock_create_task.side_effect = side_effect
            
            # get_engine should auto-initialize
            engine = db_manager.get_engine('primary')
            
            assert engine is mock_engine
            assert db_manager._initialized
            mock_create_task.assert_called_once()
            mock_sleep.assert_called_once_with(0.1)
    
    @pytest.mark.unit
    def test_get_engine_auto_initialization_failure(self):
        """Test get_engine handles auto-initialization failure properly.
        
        Business Value: Provides clear error messages for deployment issues.
        Protects: Debugging efficiency during production issues
        """
        with patch('asyncio.create_task', side_effect=RuntimeError("Initialization failed")):
            db_manager = DatabaseManager()
            
            # Should raise descriptive error
            with pytest.raises(RuntimeError, match="DatabaseManager not initialized and auto-initialization failed"):
                db_manager.get_engine('primary')
    
    @pytest.mark.unit
    def test_get_engine_invalid_engine_name(self):
        """Test get_engine raises proper error for invalid engine names.
        
        Business Value: Prevents silent failures from typos in engine names.
        Protects: Data integrity from operations on wrong databases
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            
            async def test_invalid_engine():
                await db_manager.initialize()
                
                with pytest.raises(ValueError, match="Engine 'invalid_engine' not found"):
                    db_manager.get_engine('invalid_engine')
            
            asyncio.run(test_invalid_engine())
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_all_engines(self):
        """Test close_all properly disposes all engines and resets state.
        
        Business Value: Prevents connection leaks during service shutdowns.
        Protects: Resource utilization and clean deployment cycles
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            # Mock engine with dispose method
            mock_engine = AsyncMock()
            mock_create_engine.return_value = mock_engine
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Verify engine exists
            assert 'primary' in db_manager._engines
            assert db_manager._initialized
            
            # Close all engines
            await db_manager.close_all()
            
            # Verify cleanup
            mock_engine.dispose.assert_called_once()
            assert len(db_manager._engines) == 0
            assert not db_manager._initialized


class TestDatabaseURLBuilderIntegration(BaseTestCase):
    """Unit tests for DatabaseURLBuilder SSOT integration.
    
    Business Value: Ensures consistent URL construction preventing connection failures
    """
    
    def setup_method(self):
        super().setup_method()
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    @pytest.mark.unit
    def test_get_database_url_creates_url_builder(self):
        """Test _get_database_url creates DatabaseURLBuilder instance correctly.
        
        Business Value: Ensures SSOT compliance for URL construction.
        Protects: Connection reliability across all environments
        """
        mock_env_dict = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'POSTGRES_DB': 'test_db',
            'ENVIRONMENT': 'test'
        }
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch('shared.isolated_environment.get_env') as mock_get_env, \
             patch('shared.database_url_builder.DatabaseURLBuilder') as mock_url_builder_class:
            
            # Mock environment
            mock_env = Mock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env
            
            # Mock URL builder
            mock_url_builder = Mock()
            mock_url_builder.get_url_for_environment.return_value = "postgresql://test:test@localhost:5432/test_db"
            mock_url_builder.format_url_for_driver.return_value = "postgresql+asyncpg://test:test@localhost:5432/test_db"
            mock_url_builder.get_safe_log_message.return_value = "Database URL (test/TCP): postgresql+asyncpg://***@localhost:5432/test_db"
            mock_url_builder_class.return_value = mock_url_builder
            
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            result_url = db_manager._get_database_url()
            
            # Verify URL builder was created and used
            mock_url_builder_class.assert_called_once_with(mock_env_dict)
            mock_url_builder.get_url_for_environment.assert_called_once_with(sync=False)
            mock_url_builder.format_url_for_driver.assert_called_once_with(
                "postgresql://test:test@localhost:5432/test_db", 'asyncpg'
            )
            mock_url_builder.get_safe_log_message.assert_called_once()
            
            assert result_url == "postgresql+asyncpg://test:test@localhost:5432/test_db"
    
    @pytest.mark.unit
    def test_get_database_url_fallback_to_config(self):
        """Test _get_database_url falls back to config when URL builder fails.
        
        Business Value: Provides fallback mechanism for edge cases.
        Protects: Service availability when URL builder has issues
        """
        mock_env_dict = {'ENVIRONMENT': 'test'}
        fallback_url = "postgresql://fallback:fallback@localhost:5432/fallback_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch('shared.isolated_environment.get_env') as mock_get_env, \
             patch('shared.database_url_builder.DatabaseURLBuilder') as mock_url_builder_class:
            
            # Mock environment
            mock_env = Mock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env
            
            # Mock URL builder returning None
            mock_url_builder = Mock()
            mock_url_builder.get_url_for_environment.return_value = None
            mock_url_builder.format_url_for_driver.return_value = "postgresql+asyncpg://fallback:fallback@localhost:5432/fallback_db"
            mock_url_builder.get_safe_log_message.return_value = "Database URL (test/Custom): postgresql+asyncpg://***@localhost:5432/fallback_db"
            mock_url_builder_class.return_value = mock_url_builder
            
            # Mock config with fallback URL
            mock_config.return_value.database_url = fallback_url
            
            db_manager = DatabaseManager()
            result_url = db_manager._get_database_url()
            
            # Should use config fallback and format it
            mock_url_builder.format_url_for_driver.assert_called_once_with(fallback_url, 'asyncpg')
            assert result_url == "postgresql+asyncpg://fallback:fallback@localhost:5432/fallback_db"
    
    @pytest.mark.unit
    def test_get_database_url_no_fallback_raises_error(self):
        """Test _get_database_url raises error when both URL builder and config fail.
        
        Business Value: Provides clear error messages for configuration issues.
        Protects: Deployment troubleshooting efficiency
        """
        mock_env_dict = {'ENVIRONMENT': 'test'}
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch('shared.isolated_environment.get_env') as mock_get_env, \
             patch('shared.database_url_builder.DatabaseURLBuilder') as mock_url_builder_class:
            
            # Mock environment
            mock_env = Mock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env
            
            # Mock URL builder returning None
            mock_url_builder = Mock()
            mock_url_builder.get_url_for_environment.return_value = None
            mock_url_builder_class.return_value = mock_url_builder
            
            # Mock config with no fallback URL
            mock_config.return_value.database_url = None
            
            db_manager = DatabaseManager()
            
            with pytest.raises(ValueError, match="DatabaseURLBuilder failed to construct URL and no config fallback available"):
                db_manager._get_database_url()
    
    @pytest.mark.unit  
    def test_get_migration_url_sync_format(self):
        """Test get_migration_url_sync_format returns proper sync URL for Alembic.
        
        Business Value: Ensures database migrations work correctly.
        Protects: Schema consistency and deployment reliability
        """
        mock_env_dict = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432', 
            'POSTGRES_USER': 'migration_user',
            'POSTGRES_PASSWORD': 'migration_pass',
            'POSTGRES_DB': 'migration_db',
            'ENVIRONMENT': 'development'
        }
        
        with patch('shared.isolated_environment.get_env') as mock_get_env, \
             patch('shared.database_url_builder.DatabaseURLBuilder') as mock_url_builder_class:
            
            # Mock environment
            mock_env = Mock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env
            
            # Mock URL builder
            mock_url_builder = Mock()
            mock_url_builder.get_url_for_environment.return_value = "postgresql+asyncpg://migration_user:migration_pass@localhost:5432/migration_db"
            mock_url_builder_class.return_value = mock_url_builder
            
            # Test static method
            result_url = DatabaseManager.get_migration_url_sync_format()
            
            # Verify sync format
            mock_url_builder.get_url_for_environment.assert_called_once_with(sync=True)
            assert "postgresql://" in result_url  # Should be sync format
            assert "+asyncpg" not in result_url  # No async driver
    
    @pytest.mark.unit
    def test_create_application_engine_for_health_checks(self):
        """Test create_application_engine creates proper engine for health monitoring.
        
        Business Value: Ensures health check infrastructure works correctly.
        Protects: Monitoring and alerting system reliability
        """
        mock_env_dict = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_USER': 'health_user', 
            'POSTGRES_PASSWORD': 'health_pass',
            'POSTGRES_DB': 'health_db',
            'ENVIRONMENT': 'staging'
        }
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch('shared.isolated_environment.get_env') as mock_get_env, \
             patch('shared.database_url_builder.DatabaseURLBuilder') as mock_url_builder_class, \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            # Mock config
            mock_config.return_value.database_url = None
            
            # Mock environment  
            mock_env = Mock()
            mock_env.as_dict.return_value = mock_env_dict
            mock_get_env.return_value = mock_env
            
            # Mock URL builder
            mock_url_builder = Mock()
            mock_url_builder.get_url_for_environment.return_value = "postgresql://health_user:health_pass@localhost:5432/health_db"
            mock_url_builder.format_url_for_driver.return_value = "postgresql+asyncpg://health_user:health_pass@localhost:5432/health_db"
            mock_url_builder_class.return_value = mock_url_builder
            
            # Mock engine
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # Test static method
            result_engine = DatabaseManager.create_application_engine()
            
            # Verify engine creation with health check parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            assert call_args[1]['echo'] is False  # No echo in health checks
            assert call_args[1]['poolclass'] == NullPool  # NullPool for health checks
            assert call_args[1]['pool_pre_ping'] is True
            assert call_args[1]['pool_recycle'] == 3600
            
            assert result_engine is mock_engine


class TestDatabaseManagerSessionManagement(BaseTestCase):
    """Unit tests for DatabaseManager session management.
    
    Business Value: Ensures proper transaction handling preventing data corruption
    """
    
    def setup_method(self):
        super().setup_method()
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_session_auto_initialization(self):
        """Test get_session auto-initializes database manager when needed.
        
        Business Value: Prevents session access failures in staging environments.
        Protects: Application stability during startup sequences  
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine, \
             patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # Mock session context manager
            mock_session = AsyncMock()
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_session_context
            
            db_manager = DatabaseManager()
            
            # get_session should auto-initialize
            async with db_manager.get_session() as session:
                assert session is mock_session
                assert db_manager._initialized  # Should be initialized now
    
    @pytest.mark.unit
    @pytest.mark.asyncio  
    async def test_get_session_transaction_rollback_on_error(self):
        """Test get_session properly rolls back transactions on errors.
        
        Business Value: Prevents partial data corruption from failed transactions.
        Protects: Data integrity worth $500K+ ARR
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine, \
             patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # Mock session that raises error
            mock_session = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.commit = AsyncMock()
            
            async def mock_aenter():
                return mock_session
            
            async def mock_aexit(exc_type, exc_val, exc_tb):
                if exc_type is not None:
                    await mock_session.rollback()
                    raise exc_val
                else:
                    await mock_session.commit()
                await mock_session.close()
                return False
            
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__ = mock_aenter
            mock_session_context.__aexit__ = mock_aexit
            mock_session_class.return_value = mock_session_context
            
            db_manager = DatabaseManager() 
            await db_manager.initialize()
            
            # Test exception handling
            with pytest.raises(RuntimeError, match="Simulated transaction error"):
                async with db_manager.get_session() as session:
                    raise RuntimeError("Simulated transaction error")
            
            # Verify rollback was called
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_with_auto_initialization(self):
        """Test health_check auto-initializes and performs database connectivity test.
        
        Business Value: Ensures health monitoring works even after restarts.
        Protects: Monitoring system reliability and alerting accuracy
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine, \
             patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # Mock successful health check session
            mock_session = AsyncMock()
            mock_result = Mock()
            mock_result.fetchone.return_value = (1,)
            mock_session.execute.return_value = mock_result
            
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_session_context
            
            db_manager = DatabaseManager()
            
            # Health check should auto-initialize and succeed
            health_result = await db_manager.health_check()
            
            assert health_result["status"] == "healthy"
            assert health_result["engine"] == "primary"
            assert health_result["connection"] == "ok"
            assert db_manager._initialized


class TestDatabaseManagerErrorHandling(BaseTestCase):
    """Unit tests for DatabaseManager error handling and recovery.
    
    Business Value: Ensures proper error handling preventing silent failures
    """
    
    def setup_method(self):
        super().setup_method()
        import netra_backend.app.db.database_manager
        netra_backend.app.db.database_manager._database_manager = None
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_handles_database_errors(self):
        """Test health_check properly handles and reports database errors.
        
        Business Value: Provides accurate health status for monitoring systems.
        Protects: Alerting system reliability and incident response
        """
        test_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        
        with patch('netra_backend.app.core.config.get_config') as mock_config, \
             patch.object(DatabaseManager, '_get_database_url', return_value=test_url), \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine, \
             patch('netra_backend.app.db.database_manager.AsyncSession') as mock_session_class:
            
            mock_config.return_value.database_echo = False
            mock_config.return_value.database_pool_size = 5
            mock_config.return_value.database_max_overflow = 10
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # Mock session that raises database error
            mock_session = AsyncMock()
            mock_session.execute.side_effect = RuntimeError("Database connection failed")
            
            mock_session_context = AsyncMock()
            mock_session_context.__aenter__.return_value = mock_session
            mock_session_context.__aexit__.return_value = None
            mock_session_class.return_value = mock_session_context
            
            db_manager = DatabaseManager()
            await db_manager.initialize()
            
            # Health check should handle error gracefully
            health_result = await db_manager.health_check()
            
            assert health_result["status"] == "unhealthy"
            assert health_result["engine"] == "primary"
            assert "Database connection failed" in health_result["error"]
    
    @pytest.mark.unit
    def test_global_database_manager_singleton_behavior(self):
        """Test get_database_manager returns same instance (singleton pattern).
        
        Business Value: Ensures consistent database connection management.
        Protects: Resource efficiency and connection pool consistency
        """
        # First call should create instance
        manager1 = get_database_manager()
        assert manager1 is not None
        assert isinstance(manager1, DatabaseManager)
        
        # Second call should return same instance
        manager2 = get_database_manager()
        assert manager1 is manager2
        
        # Third call should still return same instance
        manager3 = get_database_manager()
        assert manager1 is manager3


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v", "--tb=short"])