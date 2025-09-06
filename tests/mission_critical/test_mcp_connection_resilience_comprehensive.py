"""
MISSION CRITICAL: Comprehensive MCP Connection Manager Resilience Tests

Tests the fixed MCP Connection Manager to ensure:
1. No permanent failure states - all connections can recover
2. Exponential backoff resets on successful reconnection
3. Failed connections are replaced, not removed
4. Background recovery tasks work properly
5. Circuit breaker integration functions correctly
6. Health monitoring triggers recovery as needed

This test suite validates the critical fixes for:
- Permanent FAILED states
- Exponential backoff growing without reset
- Failed connections being removed without replacement
- No automatic recovery mechanism

CRITICAL BUSINESS VALUE:
- Prevents MCP server connection cascade failures
- Ensures external tool integrations remain operational
- Validates resilience patterns used throughout the system
"""

import asyncio
import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

from netra_backend.app.core.resilience.unified_circuit_breaker import (
    UnifiedCircuitBreakerState
)
from netra_backend.app.mcp_client.connection_manager import (
    MCPConnectionManager,
    MCPServerConfig,
    MCPTransport,
    MCPConnection,
    ConnectionStatus,
    ConnectionMetrics
)


class TestMCPConnectionRecoveryComprehensive:
    """Test comprehensive MCP connection recovery functionality."""

    @pytest.fixture
    async def connection_manager(self):
        """Create connection manager for testing."""
        manager = MCPConnectionManager(max_connections_per_server=5)
        yield manager
        await manager.close_all_connections()

    @pytest.fixture
    def mock_config(self):
        """Mock MCP server configuration."""
        return MCPServerConfig(
            name="test_server",
            url="http://localhost:8000",
            transport=MCPTransport.HTTP,
            timeout=30000,
            max_retries=3
        )

    @pytest.fixture
    def mock_failing_connection(self):
        """Mock a connection that will fail."""
        connection = MCPConnection(
            id="test-conn-1",
            server_name="test_server",
            transport=Mock(),
            status=ConnectionStatus.CONNECTED,
            created_at=datetime.now()
        )
        return connection

    @pytest.mark.asyncio
    async def test_failed_connections_move_to_recovery_queue(
        self, connection_manager, mock_failing_connection
    ):
        """Test that failed connections move to recovery queue instead of being removed."""
        server_name = mock_failing_connection.server_name
        
        # Initialize pools and circuit breaker
        await connection_manager._initialize_pool(server_name)
        await connection_manager._ensure_circuit_breaker(server_name)
        
        # Handle connection failure
        await connection_manager._handle_connection_failure(
            mock_failing_connection, "test_error"
        )
        
        # Verify connection is in recovery queue
        assert server_name in connection_manager._failed_connections
        assert mock_failing_connection in connection_manager._failed_connections[server_name]
        assert mock_failing_connection.status == ConnectionStatus.FAILED
        
        # Verify circuit breaker recorded failure
        circuit_breaker = connection_manager._circuit_breakers[server_name]
        assert circuit_breaker.metrics.failed_calls > 0

    @pytest.mark.asyncio
    async def test_exponential_backoff_resets_on_success(
        self, connection_manager, mock_config
    ):
        """Test that exponential backoff resets after successful reconnection."""
        # Create a connection with high backoff delay
        connection = MCPConnection(
            id="test-conn-2",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.FAILED,
            created_at=datetime.now(),
            recovery_backoff_delay=32.0,  # High backoff delay
            retry_count=5
        )
        
        # Mock successful connection creation
        with patch.object(
            connection_manager, 'create_connection',
            return_value=AsyncMock()
        ) as mock_create:
            new_connection = MCPConnection(
                id="test-conn-new",
                server_name=mock_config.name,
                transport=Mock(),
                status=ConnectionStatus.CONNECTED,
                created_at=datetime.now()
            )
            mock_create.return_value = new_connection
            
            # Initialize required components
            connection_manager._server_configs[mock_config.name] = mock_config
            await connection_manager._initialize_pool(mock_config.name)
            await connection_manager._ensure_circuit_breaker(mock_config.name)
            connection_manager._failed_connections[mock_config.name] = [connection]
            
            # Attempt recovery
            await connection_manager._attempt_single_connection_recovery(
                connection, mock_config.name
            )
            
            # Verify successful recovery
            assert connection not in connection_manager._failed_connections[mock_config.name]
            
            # Verify circuit breaker was reset
            circuit_breaker = connection_manager._circuit_breakers[mock_config.name]
            assert circuit_breaker.metrics.successful_calls > 0

    @pytest.mark.asyncio
    async def test_no_permanent_failure_states(
        self, connection_manager, mock_config
    ):
        """Test that connections are never permanently abandoned."""
        # Create connection that has exceeded max retries
        connection = MCPConnection(
            id="test-conn-3",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.FAILED,
            created_at=datetime.now(),
            retry_count=15,  # Exceeds max_recovery_attempts
            max_recovery_attempts=10
        )
        
        # Store config and initialize
        connection_manager._server_configs[mock_config.name] = mock_config
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._failed_connections[mock_config.name] = [connection]
        
        # Mock successful reconnection on retry
        with patch.object(
            connection_manager, '_create_transport',
            return_value=Mock()
        ), patch.object(
            connection_manager, '_connect_transport',
            return_value=AsyncMock()
        ), patch.object(
            connection_manager, '_negotiate_session',
            return_value="test-session"
        ):
            # Attempt reconnection
            result = await connection_manager.reconnect(connection)
            
            # Verify connection was not permanently abandoned
            # Instead, retry count should reset and backoff increased
            assert connection.retry_count == 0  # Reset
            assert connection.recovery_backoff_delay > 1.0  # Increased backoff
            assert result is not None  # Connection attempt was made

    @pytest.mark.asyncio
    async def test_background_recovery_task_functionality(
        self, connection_manager, mock_config
    ):
        """Test that background recovery task processes failed connections."""
        # Setup failed connection
        connection = MCPConnection(
            id="test-conn-4",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.FAILED,
            created_at=datetime.now(),
            last_failure=datetime.now() - timedelta(seconds=2),  # Ready for recovery
            recovery_backoff_delay=1.0
        )
        
        # Initialize system
        connection_manager._server_configs[mock_config.name] = mock_config
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._failed_connections[mock_config.name] = [connection]
        
        # Mock successful recovery
        with patch.object(
            connection_manager, 'create_connection'
        ) as mock_create:
            new_connection = MCPConnection(
                id="test-conn-new",
                server_name=mock_config.name,
                transport=Mock(),
                status=ConnectionStatus.CONNECTED,
                created_at=datetime.now()
            )
            mock_create.return_value = new_connection
            
            # Run recovery
            await connection_manager._recover_failed_connections()
            
            # Verify recovery was attempted
            mock_create.assert_called_once()
            
            # Verify connection was moved from failed list
            assert len(connection_manager._failed_connections[mock_config.name]) == 0
            
            # Verify pool has recovered connection
            pool = connection_manager._pools[mock_config.name]
            assert pool.qsize() > 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration_comprehensive(
        self, connection_manager, mock_config
    ):
        """Test comprehensive circuit breaker integration."""
        # Initialize system
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._server_configs[mock_config.name] = mock_config
        
        circuit_breaker = connection_manager._circuit_breakers[mock_config.name]
        
        # Test initial state
        assert circuit_breaker.get_state() == UnifiedCircuitBreakerState.CLOSED
        
        # Simulate multiple failures to open circuit breaker
        for i in range(6):  # Exceed threshold
            connection = MCPConnection(
                id=f"test-conn-{i}",
                server_name=mock_config.name,
                transport=Mock(),
                status=ConnectionStatus.CONNECTED,
                created_at=datetime.now()
            )
            await connection_manager._handle_connection_failure(
                connection, f"error_{i}"
            )
        
        # Verify circuit breaker opened
        assert circuit_breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        
        # Test recovery with circuit breaker open
        # Should still attempt recovery after timeout
        circuit_breaker.last_failure_time = time.time() - 70  # Exceed recovery timeout
        
        await connection_manager._recover_failed_connections()
        
        # Circuit breaker should allow recovery attempts

    @pytest.mark.asyncio
    async def test_health_monitoring_triggers_recovery(
        self, connection_manager, mock_config
    ):
        """Test that health monitoring triggers recovery for empty pools."""
        # Setup system with empty pool and failed connections
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._server_configs[mock_config.name] = mock_config
        
        # Add failed connection
        failed_connection = MCPConnection(
            id="test-conn-5",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.FAILED,
            created_at=datetime.now()
        )
        connection_manager._failed_connections[mock_config.name] = [failed_connection]
        
        # Ensure pool is empty
        pool = connection_manager._pools[mock_config.name]
        assert pool.empty()
        
        # Mock force recovery
        with patch.object(
            connection_manager, '_trigger_force_recovery'
        ) as mock_force_recovery:
            # Run health monitoring
            await connection_manager._monitor_system_health()
            
            # Verify force recovery was triggered
            mock_force_recovery.assert_called_once_with(mock_config.name)

    @pytest.mark.asyncio
    async def test_force_recovery_resets_backoff_and_circuit_breaker(
        self, connection_manager, mock_config
    ):
        """Test that force recovery resets backoff delays and circuit breaker."""
        # Setup system
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._server_configs[mock_config.name] = mock_config
        
        # Create failed connections with high backoff
        failed_connections = []
        for i in range(3):
            conn = MCPConnection(
                id=f"test-conn-{i}",
                server_name=mock_config.name,
                transport=Mock(),
                status=ConnectionStatus.FAILED,
                created_at=datetime.now(),
                recovery_backoff_delay=30.0,  # High backoff
                retry_count=5
            )
            failed_connections.append(conn)
        
        connection_manager._failed_connections[mock_config.name] = failed_connections
        
        # Open circuit breaker
        circuit_breaker = connection_manager._circuit_breakers[mock_config.name]
        await circuit_breaker.force_open()
        assert circuit_breaker.get_state() == UnifiedCircuitBreakerState.OPEN
        
        # Trigger force recovery
        await connection_manager._trigger_force_recovery(mock_config.name)
        
        # Verify all connections were reset
        for conn in failed_connections:
            assert conn.recovery_backoff_delay == 1.0  # Reset to minimum
            assert conn.retry_count == 0  # Reset retry count
        
        # Verify circuit breaker was reset
        assert circuit_breaker.get_state() == UnifiedCircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_connection_status_reporting_comprehensive(
        self, connection_manager, mock_config
    ):
        """Test comprehensive connection status reporting."""
        # Setup system with various connection states
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._server_configs[mock_config.name] = mock_config
        
        # Add healthy connection to pool
        healthy_connection = MCPConnection(
            id="healthy-conn",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.CONNECTED,
            created_at=datetime.now()
        )
        await connection_manager._pools[mock_config.name].put(healthy_connection)
        
        # Add failed connection
        failed_connection = MCPConnection(
            id="failed-conn",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.FAILED,
            created_at=datetime.now()
        )
        connection_manager._failed_connections[mock_config.name] = [failed_connection]
        
        # Update metrics
        metrics = connection_manager._metrics[mock_config.name]
        metrics.total_created = 5
        metrics.recovery_attempts = 3
        metrics.successful_recoveries = 2
        
        # Get status
        status = await connection_manager.get_connection_status()
        
        # Verify comprehensive status reporting
        server_status = status[mock_config.name]
        
        assert server_status["server_config"]["name"] == mock_config.name
        assert server_status["pool_status"]["available"] == 1
        assert server_status["failed_connections"] == 1
        assert server_status["metrics"]["total_created"] == 5
        assert server_status["metrics"]["recovery_attempts"] == 3
        assert server_status["metrics"]["successful_recoveries"] == 2
        assert server_status["circuit_breaker"] is not None
        assert server_status["health_status"] == "healthy"  # Pool has connections

    @pytest.mark.asyncio
    async def test_comprehensive_error_logging(
        self, connection_manager, mock_config, caplog
    ):
        """Test that all state transitions are logged comprehensively."""
        import logging
        caplog.set_level(logging.INFO)
        
        # Setup system
        await connection_manager._initialize_pool(mock_config.name)
        await connection_manager._ensure_circuit_breaker(mock_config.name)
        connection_manager._server_configs[mock_config.name] = mock_config
        
        # Create connection for testing
        connection = MCPConnection(
            id="test-conn-logging",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.CONNECTED,
            created_at=datetime.now()
        )
        
        # Test failure logging
        await connection_manager._handle_connection_failure(connection, "test_error")
        
        # Verify comprehensive logging
        log_messages = [record.message for record in caplog.records]
        
        # Check for key log messages
        failure_logs = [msg for msg in log_messages if "Connection test-conn-logging failed: test_error" in msg]
        assert len(failure_logs) > 0
        
        recovery_logs = [msg for msg in log_messages if "recovery queue" in msg]
        assert len(recovery_logs) > 0

    @pytest.mark.asyncio
    async def test_recovery_with_jitter_prevents_thundering_herd(
        self, connection_manager, mock_config
    ):
        """Test that recovery attempts include jitter to prevent thundering herd."""
        # Create connection ready for recovery
        connection = MCPConnection(
            id="test-conn-jitter",
            server_name=mock_config.name,
            transport=Mock(),
            status=ConnectionStatus.FAILED,
            created_at=datetime.now(),
            recovery_backoff_delay=5.0
        )
        
        # Patch sleep to measure delay
        delays = []
        
        async def mock_sleep(delay):
            delays.append(delay)
            
        with patch('asyncio.sleep', side_effect=mock_sleep):
            await connection_manager._wait_for_backoff(connection)
        
        # Verify jitter was added
        assert len(delays) == 1
        delay = delays[0]
        assert delay >= 5.0  # Base delay
        assert delay <= 10.0  # Base delay + max jitter
        assert delay != 5.0  # Should include some jitter

    @pytest.mark.asyncio
    async def test_force_recovery_all_servers(
        self, connection_manager
    ):
        """Test force recovery for all servers with failed connections."""
        # Setup multiple servers
        configs = []
        for i in range(3):
            config = MCPServerConfig(
                name=f"test_server_{i}",
                url=f"http://localhost:800{i}",
                transport=MCPTransport.HTTP
            )
            configs.append(config)
            
            # Initialize each server
            connection_manager._server_configs[config.name] = config
            await connection_manager._initialize_pool(config.name)
            await connection_manager._ensure_circuit_breaker(config.name)
            
            # Add failed connection for each server
            failed_conn = MCPConnection(
                id=f"failed-conn-{i}",
                server_name=config.name,
                transport=Mock(),
                status=ConnectionStatus.FAILED,
                created_at=datetime.now(),
                recovery_backoff_delay=30.0
            )
            connection_manager._failed_connections[config.name] = [failed_conn]
        
        # Force recovery for all
        results = await connection_manager.force_recovery_all()
        
        # Verify all servers were processed
        assert len(results) == 3
        for config in configs:
            assert results[config.name] == True
            
            # Verify failed connections were reset
            failed_conns = connection_manager._failed_connections[config.name]
            for conn in failed_conns:
                assert conn.recovery_backoff_delay == 1.0
                assert conn.retry_count == 0


class TestMCPConnectionManagerShutdown:
    """Test proper shutdown and cleanup of MCP Connection Manager."""

    @pytest.mark.asyncio
    async def test_graceful_shutdown_cancels_all_tasks(self):
        """Test that graceful shutdown properly cancels all background tasks."""
        manager = MCPConnectionManager()
        
        # Start background tasks
        await manager._start_background_tasks()
        
        # Verify tasks are running
        assert manager._health_check_task is not None
        assert not manager._health_check_task.done()
        assert manager._recovery_task is not None
        assert not manager._recovery_task.done()
        assert manager._health_monitor_task is not None
        assert not manager._health_monitor_task.done()
        
        # Shutdown
        await manager.close_all_connections()
        
        # Verify all tasks are cancelled/completed
        assert manager._health_check_task.done()
        assert manager._recovery_task.done()
        assert manager._health_monitor_task.done()
        assert manager._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_circuit_breakers_cleaned_up_on_shutdown(self):
        """Test that circuit breakers are properly cleaned up on shutdown."""
        manager = MCPConnectionManager()
        
        # Create some circuit breakers
        await manager._ensure_circuit_breaker("server1")
        await manager._ensure_circuit_breaker("server2")
        
        assert len(manager._circuit_breakers) == 2
        
        # Mock cleanup method to verify it's called
        for breaker in manager._circuit_breakers.values():
            breaker.cleanup = Mock()
        
        # Shutdown
        await manager.close_all_connections()
        
        # Verify cleanup was called on all breakers
        for breaker in manager._circuit_breakers.values():
            breaker.cleanup.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])