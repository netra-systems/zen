"""
Comprehensive Unit Tests for Database Manager SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/All Users  
- Business Goal: Data reliability and golden path enablement
- Value Impact: Ensures persistent data storage never fails - critical for $500K+ ARR chat functionality
- Revenue Impact: Prevents data loss that would destroy user trust and business continuity

This test suite validates the Database Manager as the SINGLE SOURCE OF TRUTH for all database operations.
Critical for golden path: user authentication → chat conversations → agent results → persistent storage.

SSOT Compliance:
- Tests the ONLY source for database connection management
- Validates DatabaseURLBuilder integration (NO manual string manipulation)
- Ensures proper auto-initialization for staging deployment
- Verifies thread-safe session management for multi-user isolation

Golden Path Coverage:
- User data persistence (authentication data, profiles)
- Chat conversation storage (threads, messages, agent responses)
- Agent execution results storage (optimization recommendations)
- Connection reliability under concurrent load
- SSL/TLS secure connections for production data
"""

import pytest
import asyncio
import threading
import time
from unittest.mock import Mock, patch, AsyncMock
from contextlib import asynccontextmanager

from sqlalchemy.exc import SQLAlchemyError, OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy import text

from netra_backend.app.db.database_manager import (
    DatabaseManager, 
    get_database_manager, 
    get_db_session
)


class TestDatabaseManagerSSO:
    """Test Database Manager as Single Source of Truth for database operations."""
    
    @pytest.fixture
    def database_manager(self):
        """Create fresh DatabaseManager instance for testing."""
        return DatabaseManager()
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        mock_config = Mock()
        mock_config.database_echo = False
        mock_config.database_pool_size = 5
        mock_config.database_max_overflow = 10
        mock_config.database_url = "postgresql+asyncpg://test:test@localhost:5432/test_db"
        return mock_config
    
    @pytest.mark.unit
    async def test_database_manager_initialization(self, database_manager, mock_config):
        """Test proper SSOT initialization with DatabaseURLBuilder integration.
        
        BVJ: Ensures reliable database connections that enable golden path data flow.
        Golden Path: User registration → conversation storage → results persistence.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config), \
             patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder, \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_engine:
            
            # Setup DatabaseURLBuilder mock
            mock_builder_instance = Mock()
            mock_builder.return_value = mock_builder_instance
            mock_builder_instance.get_url_for_environment.return_value = "postgresql+asyncpg://test:test@localhost:5432/test_db"
            mock_builder_instance.format_url_for_driver.return_value = "postgresql+asyncpg://test:test@localhost:5432/test_db"
            mock_builder_instance.get_safe_log_message.return_value = "Safe connection info"
            
            # Setup engine mock
            mock_engine_instance = Mock(spec=AsyncEngine)
            mock_engine.return_value = mock_engine_instance
            
            # Test initialization
            await database_manager.initialize()
            
            # Verify SSOT compliance: DatabaseURLBuilder must be used
            mock_builder.assert_called_once()
            mock_builder_instance.get_url_for_environment.assert_called_once_with(sync=False)
            mock_builder_instance.format_url_for_driver.assert_called_once_with(
                "postgresql+asyncpg://test:test@localhost:5432/test_db", 'asyncpg'
            )
            
            # Verify engine creation with proper parameters
            mock_engine.assert_called_once()
            engine_call_args = mock_engine.call_args
            assert engine_call_args[0][0] == "postgresql+asyncpg://test:test@localhost:5432/test_db"
            assert engine_call_args[1]['echo'] == False
            assert engine_call_args[1]['pool_pre_ping'] == True
            assert engine_call_args[1]['pool_recycle'] == 3600
            
            # Verify initialization state
            assert database_manager._initialized == True
            assert 'primary' in database_manager._engines
    
    @pytest.mark.unit
    async def test_auto_initialization_staging_fix(self, database_manager, mock_config):
        """Test critical auto-initialization fix for staging deployment.
        
        BVJ: Prevents "DatabaseManager not initialized" errors in staging - business critical.
        Golden Path: Staging environment must work for customer demos and business validation.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config), \
             patch.object(database_manager, 'initialize', new_callable=AsyncMock) as mock_init:
            
            # Test accessing engine before initialization triggers auto-init
            mock_init.return_value = None
            
            # Mock an engine for after initialization
            mock_engine = Mock(spec=AsyncEngine)
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            # Access engine - should trigger auto-init warning and work
            engine = database_manager.get_engine()
            
            # Verify auto-initialization was attempted
            mock_init.assert_called_once()
            assert engine == mock_engine
    
    @pytest.mark.unit
    async def test_session_management_with_auto_init(self, database_manager, mock_config):
        """Test session management with auto-initialization safety.
        
        BVJ: Ensures reliable database sessions for user data operations.
        Golden Path: Every user interaction requires reliable database session.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config), \
             patch.object(database_manager, 'initialize', new_callable=AsyncMock) as mock_init:
            
            # Setup mocks
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                # Test session context manager
                async with database_manager.get_session() as session:
                    assert session == mock_session
                
                # Verify proper session lifecycle
                mock_session.commit.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_session_rollback_on_error(self, database_manager, mock_config):
        """Test proper session rollback on database errors.
        
        BVJ: Ensures data consistency - critical for financial and user data integrity.
        Golden Path: Failed operations must not corrupt user data or conversation state.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock(side_effect=SQLAlchemyError("Test error"))
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                # Test session error handling
                with pytest.raises(SQLAlchemyError):
                    async with database_manager.get_session() as session:
                        assert session == mock_session
                        # Commit will raise error
                
                # Verify rollback was called
                mock_session.rollback.assert_called_once()
                mock_session.close.assert_called_once()
    
    @pytest.mark.unit
    async def test_health_check_with_auto_init(self, database_manager, mock_config):
        """Test health check functionality with auto-initialization.
        
        BVJ: Enables monitoring of database health for business operations reliability.
        Golden Path: Health checks ensure system availability for customer interactions.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            # Mock successful query execution
            mock_result = Mock()
            mock_result.fetchone.return_value = (1,)
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                # Test successful health check
                health_result = await database_manager.health_check()
                
                assert health_result['status'] == 'healthy'
                assert health_result['engine'] == 'primary'
                assert health_result['connection'] == 'ok'
                
                # Verify health check query was executed
                mock_session.execute.assert_called_once()
                call_args = mock_session.execute.call_args[0][0]
                assert str(call_args) == 'SELECT 1'
    
    @pytest.mark.unit
    async def test_health_check_failure(self, database_manager, mock_config):
        """Test health check failure handling.
        
        BVJ: Enables proper error detection and alerting for business continuity.
        Golden Path: System must detect and report database issues promptly.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks for failure scenario
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.execute = AsyncMock(side_effect=OperationalError("Connection failed", None, None))
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                # Test failed health check
                health_result = await database_manager.health_check()
                
                assert health_result['status'] == 'unhealthy'
                assert health_result['engine'] == 'primary'
                assert 'Connection failed' in health_result['error']
    
    @pytest.mark.unit
    async def test_concurrent_access_thread_safety(self, database_manager, mock_config):
        """Test thread-safe access for multi-user environment.
        
        BVJ: Ensures data isolation between different users - critical for SaaS platform.
        Golden Path: Multiple users must be able to access database simultaneously without conflicts.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks for concurrent access
            mock_engine = Mock(spec=AsyncEngine)
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            concurrent_results = []
            
            async def concurrent_health_check(check_id):
                """Simulate concurrent health check from different threads."""
                mock_session = Mock(spec=AsyncSession)
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock(return_value=None)
                
                mock_result = Mock()
                mock_result.fetchone.return_value = (check_id,)
                mock_session.execute = AsyncMock(return_value=mock_result)
                
                with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                    result = await database_manager.health_check()
                    concurrent_results.append((check_id, result['status']))
            
            # Run concurrent operations
            tasks = [concurrent_health_check(i) for i in range(5)]
            await asyncio.gather(*tasks)
            
            # Verify all operations completed successfully
            assert len(concurrent_results) == 5
            for check_id, status in concurrent_results:
                assert status == 'healthy'
    
    @pytest.mark.unit
    async def test_close_all_connections(self, database_manager, mock_config):
        """Test proper cleanup of all database connections.
        
        BVJ: Ensures clean resource management for system stability.
        Golden Path: System shutdown must not leave hanging connections.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup multiple mock engines
            mock_engine1 = Mock(spec=AsyncEngine)
            mock_engine1.dispose = AsyncMock()
            mock_engine2 = Mock(spec=AsyncEngine) 
            mock_engine2.dispose = AsyncMock()
            
            database_manager._engines['primary'] = mock_engine1
            database_manager._engines['secondary'] = mock_engine2
            database_manager._initialized = True
            
            # Test close all
            await database_manager.close_all()
            
            # Verify all engines were disposed
            mock_engine1.dispose.assert_called_once()
            mock_engine2.dispose.assert_called_once()
            
            # Verify cleanup state
            assert len(database_manager._engines) == 0
            assert database_manager._initialized == False
    
    @pytest.mark.unit
    def test_global_manager_singleton(self):
        """Test global database manager singleton pattern.
        
        BVJ: Ensures single source of truth for database connections across application.
        Golden Path: All components must use the same database manager instance.
        """
        # Get multiple instances
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        
        # Verify they are the same instance
        assert manager1 is manager2
        assert isinstance(manager1, DatabaseManager)
    
    @pytest.mark.unit
    async def test_class_method_compatibility(self, mock_config):
        """Test backward compatibility class method interface.
        
        BVJ: Ensures existing code continues to work during SSOT migration.
        Golden Path: Gradual migration without breaking existing functionality.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config), \
             patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            
            # Setup mocks
            mock_manager = Mock()
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_manager._initialized = True
            mock_manager.get_session = Mock(return_value=mock_session)
            mock_manager.initialize = AsyncMock()
            mock_get_manager.return_value = mock_manager
            
            # Test class method interface
            async with DatabaseManager.get_async_session() as session:
                assert session == mock_session
            
            # Verify manager was obtained and used
            mock_get_manager.assert_called_once()
            mock_manager.initialize.assert_called_once()
    
    @pytest.mark.unit
    def test_migration_url_generation(self, mock_config):
        """Test migration URL generation for Alembic compatibility.
        
        BVJ: Enables database schema migrations for feature development.
        Golden Path: Database migrations must work for schema evolution.
        """
        with patch('netra_backend.app.db.database_manager.get_env') as mock_get_env, \
             patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder:
            
            # Setup mocks
            mock_env = Mock()
            mock_env.as_dict.return_value = {'DATABASE_URL': 'postgresql://user:pass@host:5432/db'}
            mock_get_env.return_value = mock_env
            
            mock_builder_instance = Mock()
            mock_builder.return_value = mock_builder_instance
            mock_builder_instance.get_url_for_environment.return_value = "postgresql+asyncpg://user:pass@host:5432/db"
            
            # Test migration URL generation
            migration_url = DatabaseManager.get_migration_url_sync_format()
            
            # Verify sync format conversion
            assert "postgresql://" in migration_url
            assert "postgresql+asyncpg://" not in migration_url
            
            # Verify DatabaseURLBuilder was used
            mock_builder.assert_called_once_with(mock_env.as_dict.return_value)
            mock_builder_instance.get_url_for_environment.assert_called_once_with(sync=True)
    
    @pytest.mark.unit
    async def test_engine_creation_for_health_checks(self, mock_config):
        """Test application engine creation for isolated health checks.
        
        BVJ: Enables independent health monitoring without affecting main connections.
        Golden Path: Health checks must not interfere with user operations.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config), \
             patch('netra_backend.app.db.database_manager.get_env') as mock_get_env, \
             patch('netra_backend.app.db.database_manager.DatabaseURLBuilder') as mock_builder, \
             patch('netra_backend.app.db.database_manager.create_async_engine') as mock_create_engine:
            
            # Setup mocks
            mock_env = Mock()
            mock_env.as_dict.return_value = {}
            mock_get_env.return_value = mock_env
            
            mock_builder_instance = Mock()
            mock_builder.return_value = mock_builder_instance
            mock_builder_instance.get_url_for_environment.return_value = "postgresql+asyncpg://test:test@localhost:5432/test_db"
            mock_builder_instance.format_url_for_driver.return_value = "postgresql+asyncpg://test:test@localhost:5432/test_db"
            
            mock_engine = Mock(spec=AsyncEngine)
            mock_create_engine.return_value = mock_engine
            
            # Test application engine creation
            engine = DatabaseManager.create_application_engine()
            
            # Verify engine creation parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            assert call_args[0][0] == "postgresql+asyncpg://test:test@localhost:5432/test_db"
            assert call_args[1]['echo'] == False
            assert call_args[1]['pool_pre_ping'] == True
            assert call_args[1]['pool_recycle'] == 3600
            
            assert engine == mock_engine


class TestDatabaseSessionHelpers:
    """Test database session helper functions for golden path integration."""
    
    @pytest.mark.unit
    async def test_get_db_session_helper(self, mock_config):
        """Test database session helper function.
        
        BVJ: Provides convenient session access for application components.
        Golden Path: Simplified session access for user data operations.
        """
        with patch('netra_backend.app.db.database_manager.get_database_manager') as mock_get_manager:
            
            # Setup mocks
            mock_manager = Mock()
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            
            mock_manager.get_session.return_value = mock_session
            mock_get_manager.return_value = mock_manager
            
            # Test session helper
            async with get_db_session() as session:
                assert session == mock_session
            
            # Verify manager was used
            mock_get_manager.assert_called_once()
            mock_manager.get_session.assert_called_once_with('primary')


class TestDatabaseManagerBusinessScenarios:
    """Test business-critical database scenarios for golden path validation."""
    
    @pytest.mark.unit
    async def test_user_data_persistence_scenario(self, database_manager, mock_config):
        """Test user registration and data persistence scenario.
        
        BVJ: Core business functionality - user onboarding and profile management.
        Golden Path: New user registration → profile storage → authentication data persistence.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks for user data scenario
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.add = Mock()
            mock_session.execute = AsyncMock()
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                
                # Simulate user registration transaction
                async with database_manager.get_session() as session:
                    # Simulate adding user data
                    session.add(Mock())  # Mock user object
                    
                    # Simulate additional profile data
                    await session.execute(text("INSERT INTO user_profiles VALUES (...)"))
                
                # Verify transaction completed successfully
                mock_session.add.assert_called_once()
                mock_session.execute.assert_called_once()
                mock_session.commit.assert_called_once()
    
    @pytest.mark.unit
    async def test_chat_conversation_persistence_scenario(self, database_manager, mock_config):
        """Test chat conversation storage scenario.
        
        BVJ: Core product functionality - chat conversations are 90% of platform value.
        Golden Path: User message → agent processing → response storage → conversation history.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks for conversation scenario
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.add_all = Mock()
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                
                # Simulate chat conversation transaction
                async with database_manager.get_session() as session:
                    # Simulate storing thread, messages, and agent response
                    session.add_all([Mock(), Mock(), Mock()])  # Mock thread, user_message, agent_response
                
                # Verify conversation data was persisted
                mock_session.add_all.assert_called_once()
                mock_session.commit.assert_called_once()
    
    @pytest.mark.unit
    async def test_agent_results_persistence_scenario(self, database_manager, mock_config):
        """Test agent execution results storage scenario.
        
        BVJ: AI optimization recommendations storage - core platform differentiator.
        Golden Path: Agent execution → optimization analysis → results storage → user insights.
        """
        with patch('netra_backend.app.db.database_manager.get_config', return_value=mock_config):
            
            # Setup mocks for agent results scenario
            mock_engine = Mock(spec=AsyncEngine)
            mock_session = Mock(spec=AsyncSession)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.commit = AsyncMock()
            mock_session.close = AsyncMock()
            mock_session.execute = AsyncMock()
            
            database_manager._engines['primary'] = mock_engine
            database_manager._initialized = True
            
            with patch('netra_backend.app.db.database_manager.AsyncSession', return_value=mock_session):
                
                # Simulate agent results storage
                async with database_manager.get_session() as session:
                    # Simulate storing optimization results
                    await session.execute(text("INSERT INTO apex_optimizer_agent_runs VALUES (...)"))
                    await session.execute(text("INSERT INTO apex_optimizer_agent_run_reports VALUES (...)"))
                
                # Verify results were persisted
                assert mock_session.execute.call_count == 2
                mock_session.commit.assert_called_once()


@pytest.mark.integration  
class TestDatabaseManagerSSotIntegration:
    """Integration tests for Database Manager SSOT compliance with real database operations."""
    
    @pytest.mark.real_database
    async def test_real_database_connection_initialization(self):
        """Test real database connection with SSOT compliance.
        
        BVJ: Validates actual database connectivity for production reliability.
        Golden Path: Real database must work for actual user data operations.
        """
        database_manager = DatabaseManager()
        
        try:
            # Test real initialization
            await database_manager.initialize()
            
            # Verify initialization succeeded
            assert database_manager._initialized == True
            assert 'primary' in database_manager._engines
            
            # Test real health check
            health_result = await database_manager.health_check()
            assert health_result['status'] == 'healthy'
            
        finally:
            # Clean up
            await database_manager.close_all()
    
    @pytest.mark.real_database
    async def test_real_session_operations(self):
        """Test real session operations with actual database.
        
        BVJ: Validates session management works with real database constraints.
        Golden Path: Real session operations must handle actual database interactions.
        """
        database_manager = DatabaseManager()
        
        try:
            await database_manager.initialize()
            
            # Test real session usage
            async with database_manager.get_session() as session:
                # Execute actual query
                result = await session.execute(text("SELECT 1 as test_value"))
                row = result.fetchone()
                assert row[0] == 1
            
        finally:
            await database_manager.close_all()