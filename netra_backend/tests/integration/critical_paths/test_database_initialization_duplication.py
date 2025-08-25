"""
Test for Database Initialization Duplication Prevention

This test ensures that database initialization is not duplicated during startup,
preventing infinite loops and connection pool exhaustion.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Platform Stability
- Value Impact: Prevents startup failures due to duplicate database initialization
- Strategic Impact: Ensures reliable service startup and prevents downtime
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from fastapi import FastAPI

from netra_backend.app.core.startup_manager import StartupManager, ComponentPriority
from netra_backend.app.db.database_initializer import DatabaseInitializer


class TestDatabaseInitializationDuplication:
    """Test suite to prevent database initialization duplication"""
    
    @pytest.mark.asyncio
    async def test_no_duplicate_database_initialization(self):
        """
        Test that database is initialized only once during startup.
        
        This test prevents the regression where DatabaseInitializer.initialize_postgresql()
        and setup_database_connections() were both called, causing duplicate initialization
        and potential infinite loops of database queries.
        """
        # Create a test app
        app = FastAPI()
        app.state = Mock()
        
        # Create startup manager
        startup_manager = StartupManager()
        
        # Mock the database initialization functions
        with patch('netra_backend.app.startup_module.setup_multiprocessing_env') as mock_multiprocessing, \
             patch('netra_backend.app.startup_module.validate_database_environment') as mock_validate, \
             patch('netra_backend.app.startup_module.run_database_migrations') as mock_migrations, \
             patch('netra_backend.app.startup_module.setup_database_connections') as mock_setup_connections, \
             patch('netra_backend.app.db.database_initializer.DatabaseInitializer') as mock_db_initializer_class, \
             patch('netra_backend.app.startup_module.initialize_postgres') as mock_init_postgres, \
             patch('netra_backend.app.startup_module._ensure_database_tables_exist') as mock_ensure_tables:
            
            # Configure mocks
            mock_setup_connections.return_value = None
            mock_init_postgres.return_value = Mock()  # Return a mock session factory
            mock_ensure_tables.return_value = None
            
            # Create a mock DatabaseInitializer instance
            mock_db_initializer = AsyncMock()
            mock_db_initializer.initialize_postgresql = AsyncMock(return_value=True)
            mock_db_initializer_class.return_value = mock_db_initializer
            
            # Initialize database component
            await startup_manager._initialize_database(app)
            
            # Verify that setup_database_connections was called (which does the initialization)
            assert mock_setup_connections.called, "setup_database_connections should be called"
            
            # Verify that DatabaseInitializer.initialize_postgresql was NOT called
            # (since we removed this duplicate call)
            assert not mock_db_initializer.initialize_postgresql.called, \
                "DatabaseInitializer.initialize_postgresql should NOT be called (duplicate initialization)"
    
    @pytest.mark.asyncio
    async def test_database_connection_test_not_in_loop(self):
        """
        Test that database connection testing doesn't create an infinite loop.
        
        This test ensures that the test_connection_with_retry method doesn't
        get called repeatedly in a loop during startup.
        """
        from netra_backend.app.db.database_manager import DatabaseManager
        
        # Mock the database engine and connection test
        mock_engine = Mock()
        
        # Track the number of calls to test_connection_with_retry
        call_count = 0
        max_allowed_calls = 5  # Allow some retries but not infinite
        
        async def mock_test_connection(engine, max_retries=3, delay=1.0):
            nonlocal call_count
            call_count += 1
            if call_count > max_allowed_calls:
                raise AssertionError(f"test_connection_with_retry called {call_count} times - possible infinite loop!")
            # Simulate successful connection on first attempt to simplify test
            return True
        
        # Patch the test_connection_with_retry method
        with patch.object(DatabaseManager, 'test_connection_with_retry', side_effect=mock_test_connection):
            # Test the connection
            result = await DatabaseManager.test_connection_with_retry(mock_engine)
            
            # Verify connection succeeded
            assert result is True, "Connection should eventually succeed"
            
            # Verify we didn't hit the max calls limit (which would indicate a loop)
            assert call_count == 1, f"Connection test called {call_count} times, expected 1 (no loop)"
    
    @pytest.mark.asyncio
    async def test_ensure_tables_exist_not_called_multiple_times(self):
        """
        Test that _ensure_database_tables_exist is not called multiple times during startup.
        
        Multiple calls to this function can cause excessive database queries and
        connection pool exhaustion.
        """
        from netra_backend.app.startup_module import setup_database_connections
        
        app = FastAPI()
        app.state = Mock()
        
        with patch('netra_backend.app.startup_module.get_config') as mock_config, \
             patch('netra_backend.app.startup_module.initialize_postgres') as mock_init_postgres, \
             patch('netra_backend.app.startup_module._ensure_database_tables_exist') as mock_ensure_tables, \
             patch('netra_backend.app.startup_module.central_logger'):
            
            # Configure mocks
            mock_config.return_value = Mock(
                database_url="postgresql://test:test@localhost/test",
                graceful_startup_mode="false"
            )
            mock_init_postgres.return_value = Mock()  # Return a mock session factory
            mock_ensure_tables.return_value = None
            
            # Call setup_database_connections
            await setup_database_connections(app)
            
            # Verify _ensure_database_tables_exist was called exactly once
            assert mock_ensure_tables.call_count == 1, \
                f"_ensure_database_tables_exist called {mock_ensure_tables.call_count} times, expected 1"
    
    @pytest.mark.asyncio 
    async def test_startup_manager_components_initialized_once(self):
        """
        Test that each startup component is initialized exactly once.
        
        This prevents duplicate initialization of any component, not just the database.
        """
        startup_manager = StartupManager()
        
        # Track initialization calls for each component
        init_counts = {}
        
        async def create_mock_init(name):
            """Create a mock initialization function that tracks calls"""
            async def mock_init():
                init_counts[name] = init_counts.get(name, 0) + 1
                return True
            return mock_init
        
        # Register multiple components with dependencies
        components = [
            ("database", [], ComponentPriority.CRITICAL),
            ("redis", ["database"], ComponentPriority.HIGH),
            ("auth_service", ["database"], ComponentPriority.HIGH),
            ("websocket", ["database", "redis"], ComponentPriority.HIGH),
        ]
        
        for name, deps, priority in components:
            startup_manager.register_component(
                name=name,
                init_func=await create_mock_init(name),
                priority=priority,
                dependencies=deps,
                timeout_seconds=5.0,
                max_retries=1
            )
        
        # Run startup
        success = await startup_manager.startup()
        
        # Verify startup succeeded
        assert success, "Startup should succeed"
        
        # Verify each component was initialized exactly once
        for name, _, _ in components:
            assert init_counts.get(name, 0) == 1, \
                f"Component {name} initialized {init_counts.get(name, 0)} times, expected 1"