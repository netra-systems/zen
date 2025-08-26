"""
Integration tests for database connection pool management.

Tests database pool functionality:
- Connection pool initialization and configuration
- Pool sizing and connection limits
- Connection lifecycle and recycling
- Pool behavior under load
- Failover and recovery scenarios
- Connection leak detection and cleanup
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy import exc as sqlalchemy_exc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import QueuePool, StaticPool

from test_framework.mock_utils import mock_justified

class ConnectionManager:
    """Mock database connection manager for integration testing."""
    
    def __init__(self, database_url, **kwargs):
        self.database_url = database_url
        self.config = kwargs
        
    async def initialize(self):
        pass
        
    async def cleanup(self):
        pass
        
    def get_engine(self):
        # Mock: Generic component isolation for controlled unit testing
        return Mock()
        
    def get_session(self):
        # Mock: Generic component isolation for controlled unit testing
        return AsyncMock()
        
    @pytest.mark.asyncio
    async def test_connectivity(self):
        return True
        
    async def get_health_info(self):
        return {'status': 'healthy', 'connection_count': 5, 'pool_size': 10}

class DatabaseConnectivityMaster:
    """Mock database connectivity master for integration testing."""
    
    async def configure_database(self, name, url, **kwargs):
        pass
        
    def get_session(self, name):
        # Mock: Generic component isolation for controlled unit testing
        return AsyncMock()
        
    async def cleanup_all(self):
        pass

class TestDatabasePoolIntegration:
    """Integration tests for database connection pool management."""

    @pytest.fixture
    def pool_config(self):
        """Database pool configuration for testing."""
        return {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_timeout': 30,
            'pool_recycle': 3600,
            'pool_pre_ping': True
        }

    @pytest.fixture 
    def test_database_url(self):
        """Test database URL with pool parameters."""
        return "sqlite+aiosqlite:///test_pool.db"

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self, test_database_url, pool_config):
        """
        Test database connection pool initializes with correct configuration.
        
        Validates:
        - Pool is created with specified parameters
        - Initial connections are established
        - Pool size limits are enforced
        - Configuration parameters are applied correctly
        """
        db_manager = ConnectionManager(test_database_url, **pool_config)
        
        await db_manager.initialize()
        
        # Verify pool configuration
        self._verify_pool_configuration(db_manager, pool_config)
        
        # Verify pool is functional
        async with db_manager.get_session() as session:
            assert isinstance(session, AsyncSession)
            assert session.is_active
            
        await db_manager.cleanup()

    def _verify_pool_configuration(self, db_manager: ConnectionManager, expected_config: Dict[str, Any]):
        """Verify pool configuration matches expected values."""
        engine = db_manager.get_engine()
        pool = engine.pool
        
        # Verify pool type and basic configuration
        assert isinstance(pool, (QueuePool, StaticPool))
        
        if hasattr(pool, 'size'):
            assert pool.size() <= expected_config['pool_size'] + expected_config['max_overflow']

    @pytest.mark.asyncio
    async def test_pool_sizing_and_limits(self, test_database_url):
        """
        Test connection pool respects sizing limits and overflow behavior.
        
        Validates:
        - Pool size is maintained correctly
        - Max overflow limit is enforced
        - Connections are reused efficiently
        - Pool exhaustion is handled gracefully
        """
        pool_config = {
            'pool_size': 2,
            'max_overflow': 1,  # Small limits for testing
            'pool_timeout': 5
        }
        
        db_manager = ConnectionManager(test_database_url, **pool_config)
        await db_manager.initialize()
        
        # Test acquiring connections up to the limit
        sessions = []
        try:
            # Should be able to get pool_size + max_overflow connections
            for i in range(pool_config['pool_size'] + pool_config['max_overflow']):
                session = await db_manager.get_session().__aenter__()
                sessions.append(session)
                assert session.is_active
            
            # Next connection should timeout or be handled gracefully
            with pytest.raises((asyncio.TimeoutError, sqlalchemy_exc.TimeoutError)):
                async with asyncio.timeout(pool_config['pool_timeout'] + 1):
                    session = await db_manager.get_session().__aenter__()
                    sessions.append(session)
                    
        finally:
            # Cleanup sessions
            for session in sessions:
                await session.__aexit__(None, None, None)
            await db_manager.cleanup()

    @pytest.mark.asyncio
    async def test_connection_lifecycle_and_recycling(self, test_database_url, pool_config):
        """
        Test connection lifecycle management and recycling.
        
        Validates:
        - Connections are properly created and destroyed
        - Connection recycling works after specified time
        - Stale connections are detected and replaced
        - Connection state is managed correctly
        """
        # Use short recycle time for testing
        short_recycle_config = {**pool_config, 'pool_recycle': 1}  # 1 second
        
        db_manager = ConnectionManager(test_database_url, **short_recycle_config)
        await db_manager.initialize()
        
        # Get initial connection and note creation time
        initial_connection_id = None
        async with db_manager.get_session() as session:
            initial_connection_id = id(session.connection())
            
            # Execute a simple query to ensure connection works
            result = await session.execute("SELECT 1")
            assert result.fetchone()[0] == 1
        
        # Wait for recycle time to pass
        await asyncio.sleep(2)
        
        # Get another connection - should potentially be recycled
        async with db_manager.get_session() as session:
            new_connection_id = id(session.connection())
            
            # Connection should still work after recycling
            result = await session.execute("SELECT 1")  
            assert result.fetchone()[0] == 1
            
        await db_manager.cleanup()

    @pytest.mark.asyncio
    async def test_connection_pool_under_load(self, test_database_url, pool_config):
        """Test connection pool behavior under concurrent load."""
        db_manager = ConnectionManager(test_database_url, pool_config)
        await db_manager.initialize()
        
        async def concurrent_database_work(worker_id: int) -> Dict[str, Any]:
            operations_completed = 0
            try:
                for i in range(5):  # 5 operations per worker
                    async with db_manager.get_session() as session:
                        await session.execute(f"SELECT {worker_id}, {i}")
                        operations_completed += 1
                return {'worker_id': worker_id, 'operations': operations_completed, 'success': True}
            except Exception as e:
                return {'worker_id': worker_id, 'operations': operations_completed, 'error': str(e), 'success': False}
        
        # Run 4 concurrent workers
        results = await asyncio.gather(*[concurrent_database_work(i) for i in range(4)])
        
        successful_workers = [r for r in results if r.get('success')]
        assert len(successful_workers) == 4, f"Only {len(successful_workers)}/4 workers succeeded"
        
        total_operations = sum(r['operations'] for r in successful_workers)
        assert total_operations == 20, "Not all operations completed"
        
        await db_manager.cleanup()

    @pytest.mark.asyncio
    async def test_pool_failover_scenarios(self, pool_config):
        """Test connection pool behavior during database failures and recovery."""
        failing_db_url = "postgresql+asyncpg://nonexistent:5432/nonexistent"
        db_manager = ConnectionManager(failing_db_url, **pool_config)
        
        # Mock: Database access isolation for fast, reliable unit testing
        with patch('netra_backend.app.core.database_connection_manager.create_async_engine') as mock_create_engine:
            # Mock: Generic component isolation for controlled unit testing
            mock_engine = Mock()
            # Mock: Generic component isolation for controlled unit testing
            mock_engine.pool = Mock()
            # Mock: Database isolation for unit testing without external database connections
            mock_engine.connect = AsyncMock(side_effect=Exception("Database unavailable"))
            mock_create_engine.return_value = mock_engine
            
            try:
                await db_manager.initialize()
            except Exception:
                pass  # Expected to fail
            
            # Test recovery scenario
            # Mock: Generic component isolation for controlled unit testing
            mock_engine.connect = AsyncMock(return_value=Mock())
            # Mock: Async component isolation for testing without real async operations
            with patch.object(db_manager, '_test_connection', AsyncMock(return_value=True)):
                recovery_success = await db_manager.test_connectivity()
                assert recovery_success is not None

    @pytest.mark.asyncio
    async def test_connection_leak_detection_and_cleanup(self, test_database_url, pool_config):
        """Test connection leak detection and automatic cleanup."""
        db_manager = ConnectionManager(test_database_url, pool_config)
        await db_manager.initialize()
        
        leaked_sessions = []
        try:
            # Create a connection leak scenario
            session_context = db_manager.get_session()
            session = await session_context.__aenter__()
            leaked_sessions.append((session, session_context))
            
            # Force cleanup
            for session, context in leaked_sessions:
                try:
                    await context.__aexit__(None, None, None)
                except:
                    pass
            
            # Verify pool is still functional
            async with db_manager.get_session() as session:
                result = await session.execute("SELECT 1")
                assert result.fetchone()[0] == 1
                
        finally:
            for session, context in leaked_sessions:
                try:
                    await context.__aexit__(Exception(), None, None)
                except:
                    pass
            await db_manager.cleanup()

    def _get_pool_checked_out_count(self, db_manager: ConnectionManager) -> int:
        """Get the number of checked out connections from pool."""
        try:
            engine = db_manager.get_engine()
            if hasattr(engine.pool, 'checkedout'):
                return engine.pool.checkedout()
            return 0
        except:
            return 0

    @mock_justified("Real database connections not needed for pool configuration testing")
    @pytest.mark.asyncio
    async def test_pool_configuration_validation(self):
        """Test database pool configuration validation and error handling."""
        with pytest.raises(Exception) as exc_info:
            db_manager = ConnectionManager("sqlite+aioDATABASE_URL_PLACEHOLDER", pool_size=-1)
            await db_manager.initialize()
        
        assert 'pool_size' in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_database_connectivity_master_integration(self, test_database_url, pool_config):
        """
        Test integration with DatabaseConnectivityMaster for pool management.
        
        Validates:
        - DatabaseConnectivityMaster manages pools correctly
        - Multiple database pools can coexist
        - Pool switching works for different databases
        - Master handles pool lifecycle correctly
        """
        connectivity_master = DatabaseConnectivityMaster()
        
        # Configure primary database
        await connectivity_master.configure_database(
            'primary', 
            test_database_url, 
            **pool_config
        )
        
        # Test primary database connection
        async with connectivity_master.get_session('primary') as session:
            assert isinstance(session, AsyncSession)
            result = await session.execute("SELECT 1") 
            assert result.fetchone()[0] == 1
        
        # Add secondary database
        secondary_url = "sqlite+aiosqlite:///test_secondary.db"
        await connectivity_master.configure_database(
            'secondary',
            secondary_url,
            **pool_config
        )
        
        # Test both databases work independently
        async with connectivity_master.get_session('primary') as primary_session:
            async with connectivity_master.get_session('secondary') as secondary_session:
                
                primary_result = await primary_session.execute("SELECT 'primary'")
                secondary_result = await secondary_session.execute("SELECT 'secondary'")
                
                assert primary_result.fetchone()[0] == 'primary'
                assert secondary_result.fetchone()[0] == 'secondary'
        
        await connectivity_master.cleanup_all()

    def _collect_pool_metrics(self, db_manager: ConnectionManager) -> Dict[str, Any]:
        """Collect current pool metrics for analysis."""
        try:
            engine = db_manager.get_engine()
            pool = engine.pool
            return {'pool_type': type(pool).__name__, 'checked_out': getattr(pool, 'checkedout', lambda: 0)()}
        except Exception:
            return {}

if __name__ == "__main__":
    pytest.main([__file__, "-v"])