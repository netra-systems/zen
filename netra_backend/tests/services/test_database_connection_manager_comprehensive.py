"""
Comprehensive tests for Database Connection Manager.

Tests database connection pooling, failover, SSL configuration,
and connection lifecycle management across environments.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.exc import OperationalError, DisconnectionError
from sqlalchemy.pool import QueuePool

from netra_backend.app.services.database.connection_manager import ConnectionManager
from netra_backend.app.core.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.config import get_settings


class TestDatabaseConnectionManager:
    """Tests for database connection manager functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.database_url = "postgresql://test:test@localhost:5432/test_db"
        settings.database_pool_size = 5
        settings.database_max_overflow = 10
        settings.database_pool_timeout = 30
        settings.database_ssl_mode = "require"
        settings.database_ssl_cert = None
        settings.database_ssl_key = None
        settings.database_ssl_ca = None
        return settings

    @pytest.fixture
    def connection_manager(self, mock_settings):
        """Create a connection manager for testing."""
        with patch('netra_backend.app.services.database.connection_manager.get_settings') as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            manager = ConnectionManager()
            return manager

    @pytest.mark.asyncio
    async def test_connection_pool_initialization(self, connection_manager, mock_settings):
        """Test that connection pool is initialized with correct parameters."""
        with patch('sqlalchemy.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            
            await connection_manager.initialize()
            
            # Verify engine creation with correct parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args
            
            # Check URL
            assert str(call_args[0][0]) == mock_settings.database_url
            
            # Check pooling configuration
            kwargs = call_args[1]
            assert kwargs['poolclass'] == QueuePool
            assert kwargs['pool_size'] == mock_settings.database_pool_size
            assert kwargs['max_overflow'] == mock_settings.database_max_overflow
            assert kwargs['pool_timeout'] == mock_settings.database_pool_timeout

    @pytest.mark.asyncio
    async def test_connection_with_ssl_configuration(self, connection_manager):
        """Test connection with SSL configuration."""
        with patch('sqlalchemy.create_engine') as mock_create_engine:
            mock_engine = Mock()
            mock_create_engine.return_value = mock_engine
            
            await connection_manager.initialize()
            
            # Verify SSL parameters are passed
            call_args = mock_create_engine.call_args
            kwargs = call_args[1]
            
            # Check connect_args for SSL
            connect_args = kwargs.get('connect_args', {})
            assert 'sslmode' in connect_args
            assert connect_args['sslmode'] == 'require'

    @pytest.mark.asyncio
    async def test_connection_retry_logic(self, connection_manager):
        """Test connection retry logic on failure."""
        with patch('sqlalchemy.create_engine') as mock_create_engine:
            # First two attempts fail, third succeeds
            mock_create_engine.side_effect = [
                OperationalError("Connection failed", None, None),
                OperationalError("Connection failed", None, None),
                Mock()
            ]
            
            with patch('asyncio.sleep', new_callable=AsyncMock):
                await connection_manager.initialize()
                
                # Should have attempted 3 times
                assert mock_create_engine.call_count == 3

    @pytest.mark.asyncio
    async def test_connection_pool_health_check(self, connection_manager):
        """Test connection pool health checking."""
        mock_engine = Mock()
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            # Mock successful connection test
            mock_connection = Mock()
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            mock_connection.execute.return_value = Mock()
            
            health_status = await connection_manager.check_health()
            
            assert health_status['status'] == 'healthy'
            assert health_status['active_connections'] >= 0
            assert health_status['pool_size'] == 5

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion_handling(self, connection_manager):
        """Test handling of connection pool exhaustion."""
        mock_engine = Mock()
        
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            # Simulate pool exhaustion
            mock_engine.connect.side_effect = Exception("QueuePool limit exceeded")
            
            with pytest.raises(Exception) as exc_info:
                async with connection_manager.get_connection():
                    pass
            
            assert "QueuePool limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_error(self, connection_manager):
        """Test proper connection cleanup on errors."""
        mock_engine = Mock()
        mock_connection = Mock()
        
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            mock_engine.connect.return_value.__exit__.return_value = None
            
            # Test cleanup happens even with errors
            try:
                async with connection_manager.get_connection() as conn:
                    raise ValueError("Test error")
            except ValueError:
                pass
            
            # Verify connection was properly closed
            mock_engine.connect.return_value.__exit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_connection_metrics_tracking(self, connection_manager):
        """Test connection metrics are properly tracked."""
        mock_engine = Mock()
        
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            # Mock pool state
            mock_pool = Mock()
            mock_pool.size.return_value = 5
            mock_pool.checkedout.return_value = 2
            mock_pool.overflow.return_value = 1
            mock_engine.pool = mock_pool
            
            metrics = await connection_manager.get_metrics()
            
            assert metrics['pool_size'] == 5
            assert metrics['checked_out'] == 2
            assert metrics['overflow'] == 1
            assert 'uptime' in metrics

    @pytest.mark.asyncio
    async def test_connection_isolation_per_tenant(self, connection_manager):
        """Test connection isolation for multi-tenant scenarios."""
        mock_engine = Mock()
        
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            # Mock connection with different schemas
            mock_connection = Mock()
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            
            # Test tenant A
            async with connection_manager.get_connection(tenant_id="tenant_a") as conn:
                assert conn == mock_connection
            
            # Test tenant B
            async with connection_manager.get_connection(tenant_id="tenant_b") as conn:
                assert conn == mock_connection
            
            # Verify schema was set appropriately
            assert mock_connection.execute.call_count >= 2

    @pytest.mark.asyncio
    async def test_connection_failover_to_readonly(self, connection_manager):
        """Test failover to read-only replica on primary failure."""
        with patch('sqlalchemy.create_engine') as mock_create_engine:
            # Primary fails, replica succeeds
            primary_engine = Mock()
            replica_engine = Mock()
            
            mock_create_engine.side_effect = [primary_engine, replica_engine]
            
            # Configure failover URLs
            connection_manager.replica_urls = ["postgresql://replica:5432/db"]
            
            # Primary connection fails
            primary_engine.connect.side_effect = DisconnectionError("Primary down", None, None)
            replica_engine.connect.return_value.__enter__.return_value = Mock()
            
            async with connection_manager.get_connection(allow_readonly=True) as conn:
                assert conn is not None
            
            # Should have created both engines
            assert mock_create_engine.call_count == 2

    @pytest.mark.asyncio
    async def test_environment_specific_configuration(self, connection_manager):
        """Test environment-specific database configuration."""
        with patch('netra_backend.app.core.unified_environment.IsolatedEnvironment.get_current') as mock_get_env:
            mock_get_env.return_value = Mock(name="staging")
            
            with patch('sqlalchemy.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_create_engine.return_value = mock_engine
                
                await connection_manager.initialize()
                
                # Verify environment-specific settings applied
                call_args = mock_create_engine.call_args
                kwargs = call_args[1]
                
                # Staging should have different pool settings
                assert kwargs['pool_size'] >= 5
                assert 'connect_args' in kwargs

    @pytest.mark.asyncio
    async def test_connection_statement_timeout(self, connection_manager):
        """Test statement timeout configuration."""
        mock_engine = Mock()
        
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            mock_connection = Mock()
            mock_engine.connect.return_value.__enter__.return_value = mock_connection
            
            # Test statement with timeout
            async with connection_manager.get_connection() as conn:
                await connection_manager.execute_with_timeout(
                    conn, "SELECT 1", timeout=5.0
                )
            
            # Verify timeout was set
            mock_connection.execute.assert_called()

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, connection_manager):
        """Test graceful shutdown closes all connections."""
        mock_engine = Mock()
        
        with patch('sqlalchemy.create_engine', return_value=mock_engine):
            await connection_manager.initialize()
            
            # Test shutdown
            await connection_manager.shutdown()
            
            # Verify engine disposal
            mock_engine.dispose.assert_called_once()

    @pytest.mark.parametrize("environment", ["test", "dev", "staging", "prod"])
    @pytest.mark.asyncio
    async def test_environment_aware_configuration(self, connection_manager, environment):
        """Test configuration varies by environment."""
        with patch('netra_backend.app.core.unified_environment.IsolatedEnvironment.get_current') as mock_get_env:
            mock_env = Mock(name=environment)
            mock_get_env.return_value = mock_env
            
            with patch('sqlalchemy.create_engine') as mock_create_engine:
                mock_engine = Mock()
                mock_create_engine.return_value = mock_engine
                
                await connection_manager.initialize()
                
                call_args = mock_create_engine.call_args
                kwargs = call_args[1]
                
                # Production should have more conservative settings
                if environment == "prod":
                    assert kwargs['pool_timeout'] >= 30
                    assert kwargs['pool_size'] >= 5
                else:
                    # Dev/test can be more aggressive
                    assert kwargs['pool_timeout'] >= 10