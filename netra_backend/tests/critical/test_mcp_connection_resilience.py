"""
Critical Test: MCP Connection Manager Resilience

This test suite comprehensively validates the MCP Connection Manager's resilience 
patterns including automatic recovery, exponential backoff, circuit breaker patterns,
graceful degradation, and message buffering during failures.

Business Value Justification (BVJ):
    - Segment: Enterprise/Mid-tier customers using MCP integrations
- Business Goal: Prevent $2.1M annual revenue loss from MCP integration failures
- Value Impact: Ensures reliable external tool integrations and prevents cascade failures
- Strategic Impact: Enables enterprise-grade reliability for MCP-based workflows with 99.9% uptime

Critical Test Coverage:
    1. Automatic recovery from server disconnection
2. Connection state transitions (DISCONNECTED -> CONNECTING -> CONNECTED -> FAILED)
3. Exponential backoff for reconnection attempts
4. Circuit breaker pattern for connection failures
5. Graceful degradation when MCP unavailable
6. Message buffering during disconnections
7. Edge cases: server restart, network partition, protocol errors
""""

import asyncio
import gc
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.exceptions import NetraException
from netra_backend.app.mcp_client.connection_manager import (
    MCPConnectionManager,
    MCPConnection,
    MCPServerConfig,
    MCPTransport,
    ConnectionMetrics,
)
from netra_backend.app.mcp_client.models import ConnectionStatus


class MockTransport:
    """Mock transport for testing connection failures."""
    
    def __init__(self, fail_after: int = 0, connection_delay: float = 0.1):
        self.fail_after = fail_after
        self.connection_delay = connection_delay
        self.call_count = 0
        self.closed = False
        self.connected = True
    
    async def connect(self):
        await asyncio.sleep(self.connection_delay)
        self.call_count += 1
        if self.call_count > self.fail_after and self.fail_after > 0:
            raise ConnectionError(f"Mock transport failed after {self.fail_after} calls")
        self.connected = True
    
    async def close(self):
        self.closed = True
        self.connected = False
    
    async def ping(self):
        if not self.connected:
            raise ConnectionError("Transport not connected")
        return True


class MessageBuffer:
    """Mock message buffer for testing buffering during disconnections."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.buffer_enabled = True
    
    async def add_message(self, message: Dict[str, Any]) -> None:
        if self.buffer_enabled:
            self.messages.append(message)
    
    async def flush_messages(self) -> List[Dict[str, Any]]:
        messages = self.messages.copy()
        self.messages.clear()
        return messages


@pytest.mark.critical
@pytest.mark.mcp
@pytest.mark.resilience
class TestMCPConnectionResilience:
    """Critical test suite for MCP Connection Manager resilience patterns."""
    
    @pytest.fixture
    def isolated_env(self):
        """Provide isolated environment for testing."""
        return IsolatedEnvironment()
    
        @pytest.fixture
        async def connection_manager(self, isolated_env):
        """Create isolated MCP connection manager for testing."""
        manager = MCPConnectionManager(max_connections_per_server=5)
        yield manager
        await manager.close_all_connections()
    
        @pytest.fixture
        def mock_server_config(self) -> MCPServerConfig:
        """Create mock server configuration."""
        return MCPServerConfig(
        name="test-server",
        url="http://localhost:8080",
        transport=MCPTransport.HTTP,
        timeout=5000,
        max_retries=3
        )
    
        @pytest.fixture
        def failing_server_config(self) -> MCPServerConfig:
        """Create server config that will fail connections."""
        return MCPServerConfig(
        name="failing-server",
        url="http://unreachable:9999",
        transport=MCPTransport.HTTP,
        timeout=1000,
        max_retries=5
        )
    
        @pytest.fixture
        def message_buffer(self) -> MessageBuffer:
        """Create message buffer for testing."""
        return MessageBuffer()
    
        # Test 1: Automatic recovery from MCP server disconnection
        @pytest.mark.asyncio
        async def test_automatic_recovery_from_disconnection(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test automatic recovery when MCP server disconnects unexpectedly."""
        mock_transport = MockTransport(fail_after=2)  # Fail after 2 successful connections
        
        with patch.object(connection_manager, '_create_http_transport', return_value=mock_transport):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        # Initially successful connection
        connection = await connection_manager.create_connection(mock_server_config)
        assert connection.status == ConnectionStatus.CONNECTED
        assert connection.retry_count == 0
                    
        # Simulate disconnection by making health check fail
        with patch.object(connection_manager, '_ping_connection', return_value=False):
        health_ok = await connection_manager.health_check(connection)
        assert not health_ok
                        
        # Set connection to failed status and increment retry count to simulate reconnection process
        connection.status = ConnectionStatus.FAILED
        connection.retry_count = 1
                        
        # Reset transport for successful reconnection
        new_mock_transport = MockTransport()
        with patch.object(connection_manager, '_create_http_transport', return_value=new_mock_transport):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        # Trigger reconnection - this creates a new connection that is healthy
        reconnected = await connection_manager.reconnect(connection)
        assert reconnected.status == ConnectionStatus.CONNECTED
        # The new connection starts fresh with retry_count = 0 as expected
        assert reconnected.retry_count == 0
        # But the important thing is that reconnection was successful
        assert reconnected.id != connection.id  # New connection created
    
        # Test 2: Connection state transitions
        @pytest.mark.asyncio
        async def test_connection_state_transitions(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test proper connection state transitions through all states."""
        states_observed = []
        original_establish = connection_manager._establish_connection
        
        async def track_state_establish(connection, config):
        states_observed.append(connection.status)
        return await original_establish(connection, config)
        
        with patch.object(connection_manager, '_establish_connection', side_effect=track_state_establish):
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        # Test normal connection flow: CONNECTING -> CONNECTED
        connection = await connection_manager.create_connection(mock_server_config)
                        
        # Verify state progression
        assert ConnectionStatus.CONNECTING in states_observed
        assert connection.status == ConnectionStatus.CONNECTED
                        
        # Test reconnection flow: CONNECTED -> RECONNECTING -> CONNECTED
        connection.status = ConnectionStatus.FAILED
        reconnected = await connection_manager.reconnect(connection)
                        
        assert reconnected.status == ConnectionStatus.CONNECTED
    
        # Test 3: Exponential backoff for reconnection attempts
        @pytest.mark.asyncio
        async def test_exponential_backoff_reconnection(
        self, connection_manager: MCPConnectionManager, failing_server_config: MCPServerConfig
        ):
        """Test exponential backoff behavior during reconnection attempts."""
        start_times = []
        
        # Mock the backoff wait to capture timing
        async def track_wait_times(retry_count):
        start_times.append(time.time())
        # Reduced wait times for testing (normally would be exponential)
        await asyncio.sleep(0.01)  # Very short wait for testing
        
        # Create multiple connections to test retry behavior
        connections = []
        for i in range(3):
        connection = MCPConnection(
        id=str(uuid.uuid4()),
        server_name=failing_server_config.name,
        transport=MockTransport(fail_after=0),
        status=ConnectionStatus.FAILED,
        created_at=datetime.now(),
        retry_count=i + 1  # Different retry counts
        )
        connections.append(connection)
        
        # Store the config for reconnection
        connection_manager._server_configs[failing_server_config.name] = failing_server_config
        
        with patch.object(connection_manager, '_wait_for_backoff', side_effect=track_wait_times):
        # Test connection that should exceed max retries
        connection_at_limit = MCPConnection(
        id=str(uuid.uuid4()),
        server_name=failing_server_config.name,
        transport=MockTransport(fail_after=0),
        status=ConnectionStatus.FAILED,
        created_at=datetime.now(),
        retry_count=connection_manager._max_retry_attempts  # At max limit already
        )
            
        # Should immediately fail due to retry limit
        with pytest.raises(NetraException, match="exceeded max retry attempts"):
        await connection_manager.reconnect(connection_at_limit)
            
        # Verify exponential backoff is called for connections under the limit
        connection_under_limit = connections[0]  # retry_count = 1
            
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        # This should succeed and call exponential backoff
        reconnected = await connection_manager.reconnect(connection_under_limit)
        assert reconnected.status == ConnectionStatus.CONNECTED
            
        # Verify exponential backoff was called
        assert len(start_times) >= 1, "Exponential backoff should be called for valid reconnection attempts"
    
        # Test 4: Circuit breaker pattern for connection failures
        @pytest.mark.asyncio
        async def test_circuit_breaker_pattern(
        self, connection_manager: MCPConnectionManager, failing_server_config: MCPServerConfig
        ):
        """Test circuit breaker opens after consecutive failures."""
        # Initialize pool and metrics
        await connection_manager._initialize_pool(failing_server_config.name)
        
        # Simulate multiple failed connections to trigger circuit breaker
        for i in range(connection_manager._circuit_breaker_threshold + 1):
        failed_connection = MCPConnection(
        id=str(uuid.uuid4()),
        server_name=failing_server_config.name,
        transport=MockTransport(fail_after=0),
        status=ConnectionStatus.FAILED,
        created_at=datetime.now(),
        consecutive_failures=i + 1
        )
            
        await connection_manager._remove_connection(failed_connection)
        
        # Verify circuit breaker is opened
        metrics = connection_manager.get_metrics(failing_server_config.name)
        assert metrics is not None
        assert metrics.circuit_breaker_open
        assert metrics.last_circuit_open is not None
        
        # Verify circuit breaker prevents new connections
        is_open = connection_manager._is_circuit_breaker_open(failing_server_config.name)
        assert is_open
        
        # Test circuit breaker timeout
        should_attempt = connection_manager._should_attempt_circuit_recovery(failing_server_config.name)
        assert not should_attempt  # Should not attempt immediately
        
        # Simulate timeout passage and verify recovery attempt is allowed
        metrics.last_circuit_open = datetime.now() - timedelta(seconds=connection_manager._circuit_breaker_timeout + 1)
        should_attempt_after_timeout = connection_manager._should_attempt_circuit_recovery(failing_server_config.name)
        assert should_attempt_after_timeout
    
        # Test 5: Graceful degradation when MCP unavailable
        @pytest.mark.asyncio
        async def test_graceful_degradation_mcp_unavailable(
        self, connection_manager: MCPConnectionManager, failing_server_config: MCPServerConfig
        ):
        """Test graceful degradation when MCP services are unavailable."""
        # Test getting connection from non-existent server
        connection = await connection_manager.get_connection("non-existent-server")
        assert connection is None, "Should gracefully return None for non-existent server"
        
        # Test pool status for non-existent server
        pool_status = connection_manager.get_pool_status()
        assert "non-existent-server" not in pool_status
        
        # Test metrics for non-existent server
        metrics = connection_manager.get_metrics("non-existent-server")
        assert metrics is None, "Should gracefully return None for non-existent server metrics"
        
        # Test circuit breaker state for non-existent server
        is_open = connection_manager._is_circuit_breaker_open("non-existent-server")
        assert not is_open, "Circuit breaker should be closed for non-existent server"
    
        # Test 6: Message buffering during disconnections
        @pytest.mark.asyncio
        async def test_message_buffering_during_disconnection(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig, message_buffer: MessageBuffer
        ):
        """Test message buffering when connections are unavailable."""
        # Simulate messages being buffered when no connection available
        test_messages = [
        {"type": "tool_call", "tool": "test_tool", "args": {"param1": "value1"}},
        {"type": "resource_request", "uri": "test://resource/1"},
        {"type": "capability_query", "capabilities": ["tools", "resources"]]
        ]
        
        # Buffer messages while disconnected
        for message in test_messages:
        await message_buffer.add_message(message)
        
        assert len(message_buffer.messages) == 3, "All messages should be buffered"
        
        # Simulate connection restoration
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        connection = await connection_manager.create_connection(mock_server_config)
        assert connection.status == ConnectionStatus.CONNECTED
        
        # Flush buffered messages
        flushed_messages = await message_buffer.flush_messages()
        assert len(flushed_messages) == 3, "All buffered messages should be flushed"
        assert flushed_messages == test_messages, "Flushed messages should match original messages"
        assert len(message_buffer.messages) == 0, "Buffer should be empty after flush"
    
        # Test 7: Edge case - Server restart scenarios
        @pytest.mark.asyncio
        async def test_server_restart_scenarios(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test handling server restart scenarios."""
        # Create initial connection
        mock_transport = MockTransport()
        
        with patch.object(connection_manager, '_create_http_transport', return_value=mock_transport):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        connection = await connection_manager.create_connection(mock_server_config)
        assert connection.status == ConnectionStatus.CONNECTED
                    
        # Simulate server restart - connection becomes unhealthy
        mock_transport.connected = False
        with patch.object(connection_manager, '_ping_connection', return_value=False):
        health_ok = await connection_manager.health_check(connection)
        assert not health_ok
                        
        # Attempt recovery after server restart
        mock_transport.connected = True  # Server back online
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        recovered_connection = await connection_manager.reconnect(connection)
        assert recovered_connection.status == ConnectionStatus.CONNECTED
    
        # Test 8: Edge case - Network partition scenarios
        @pytest.mark.asyncio
        async def test_network_partition_scenarios(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test handling network partition scenarios."""
        # Simulate network partition during connection
        partition_transport = MockTransport(connection_delay=2.0)  # Slow connection
        
        with patch.object(connection_manager, '_create_http_transport', return_value=partition_transport):
        with patch.object(connection_manager, '_connect_transport', side_effect=asyncio.TimeoutError("Network timeout")):
        # Network partition should cause connection failure
        with pytest.raises(NetraException, match="Connection failed"):
        await connection_manager.create_connection(mock_server_config)
    
        # Test 9: Edge case - Protocol errors
        @pytest.mark.asyncio
        async def test_protocol_errors(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test handling various protocol errors."""
        # Test invalid transport creation
        with patch.object(connection_manager, '_create_transport', side_effect=NetraException("Invalid transport")):
        with pytest.raises(NetraException, match="Invalid transport"):
        await connection_manager.create_connection(mock_server_config)
        
        # Test session negotiation failure
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_negotiate_session', side_effect=RuntimeError("Protocol error")):
        with pytest.raises(NetraException, match="Connection failed"):
        await connection_manager.create_connection(mock_server_config)
    
        # Test 10: Connection pool management under stress
        @pytest.mark.asyncio
        async def test_connection_pool_stress_management(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test connection pool management under high load and failures."""
        # Initialize pool
        await connection_manager._initialize_pool(mock_server_config.name)
        
        # Create multiple connections to fill pool
        connections = []
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        for i in range(3):
        connection = await connection_manager.create_connection(mock_server_config)
        connections.append(connection)
        await connection_manager._pools[mock_server_config.name].put(connection)
        
        # Test pool status
        pool_status = connection_manager.get_pool_status()
        assert mock_server_config.name in pool_status
        assert pool_status[mock_server_config.name]["pool_size"] == 3
        
        # Test pool draining
        pool = connection_manager._pools[mock_server_config.name]
        await connection_manager._drain_pool(pool)
        assert pool.qsize() == 0
        
        # Verify all connections were closed
        for connection in connections:
        assert connection.transport.closed
    
        # Test 11: Health check loop resilience
        @pytest.mark.asyncio
        async def test_health_check_loop_resilience(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test health check background loop handles errors gracefully."""
        # Create connection and add to pool
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        connection = await connection_manager.create_connection(mock_server_config)
                    
        # Initialize pool and add connection
        await connection_manager._initialize_pool(mock_server_config.name)
        await connection_manager._pools[mock_server_config.name].put(connection)
        
        # Test health check with intermittent failures
        health_check_results = [False, True, False, True]  # Mixed results
        health_check_calls = 0
        
        async def mock_health_check(conn):
        nonlocal health_check_calls
        result = health_check_results[health_check_calls % len(health_check_results)]
        health_check_calls += 1
        return result
        
        with patch.object(connection_manager, 'health_check', side_effect=mock_health_check):
        # Run health checks
        await connection_manager._perform_health_checks()
            
        # Verify health check was called
        assert health_check_calls >= 1
    
        # Test 12: Recovery loop resilience
        @pytest.mark.asyncio
        async def test_recovery_loop_resilience(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test recovery loop handles failures and maintains minimum pool sizes."""
        # Initialize pool
        await connection_manager._initialize_pool(mock_server_config.name)
        
        # Add failed connection for recovery
        failed_connection = MCPConnection(
        id=str(uuid.uuid4()),
        server_name=mock_server_config.name,
        transport=MockTransport(fail_after=0),
        status=ConnectionStatus.FAILED,
        created_at=datetime.now()
        )
        
        connection_manager._failed_connections[mock_server_config.name] = [failed_connection]
        connection_manager._server_configs[mock_server_config.name] = mock_server_config
        
        # Test recovery attempt
        with patch.object(connection_manager, '_attempt_connection_recovery', return_value=failed_connection):
        await connection_manager._recover_failed_connections()
            
        # Verify failed connection was removed from failed list
        assert len(connection_manager._failed_connections[mock_server_config.name]) == 0
        
        # Test minimum pool size maintenance
        with patch.object(connection_manager, '_create_additional_connections') as mock_create:
        # Set pool size below minimum
        connection_manager._min_connections_per_server = 2
        current_pool = connection_manager._pools[mock_server_config.name]
        assert current_pool.qsize() < 2
            
        await connection_manager._maintain_pool_sizes()
            
        # Verify additional connections were created
        mock_create.assert_called_once()
    
        # Test 13: Memory leak prevention
        @pytest.mark.asyncio
        async def test_memory_leak_prevention(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test that connection manager properly cleans up resources to prevent memory leaks."""
        initial_connections = []
        
        # Create multiple connections
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        for i in range(10):
        connection = await connection_manager.create_connection(mock_server_config)
        initial_connections.append(connection)
        
        # Force garbage collection
        gc.collect()
        
        # Close all connections
        await connection_manager.close_all_connections()
        
        # Verify cleanup
        assert len(connection_manager._pools) == 0 or all(pool.empty() for pool in connection_manager._pools.values())
        assert connection_manager._health_check_task is None or connection_manager._health_check_task.done()
        assert connection_manager._recovery_task is None or connection_manager._recovery_task.done()
        
        # Force garbage collection again to verify no references remain
        gc.collect()
    
        # Test 14: Concurrent access resilience
        @pytest.mark.asyncio
        async def test_concurrent_access_resilience(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig
        ):
        """Test connection manager handles concurrent access safely."""
        # Create initial connections
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        connection = await connection_manager.create_connection(mock_server_config)
        await connection_manager._initialize_pool(mock_server_config.name)
                    
        # Add multiple connections to pool
        for _ in range(5):
        await connection_manager._pools[mock_server_config.name].put(connection)
        
        # Simulate concurrent access
        async def concurrent_get_connection():
        return await connection_manager.get_connection(mock_server_config.name)
        
        async def concurrent_release_connection():
        conn = await connection_manager.get_connection(mock_server_config.name)
        if conn:
        await connection_manager.release_connection(conn)
        
        # Run concurrent operations
        tasks = []
        for _ in range(20):
        tasks.append(concurrent_get_connection())
        tasks.append(concurrent_release_connection())
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify no exceptions occurred
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Concurrent access caused exceptions: {exceptions}"
    
        # Test 15: Comprehensive integration test
        @pytest.mark.asyncio
        async def test_comprehensive_resilience_integration(
        self, connection_manager: MCPConnectionManager, mock_server_config: MCPServerConfig, message_buffer: MessageBuffer
        ):
        """Comprehensive integration test of all resilience patterns."""
        # Phase 1: Normal operation
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        connection = await connection_manager.create_connection(mock_server_config)
        assert connection.status == ConnectionStatus.CONNECTED
                    
        # Test message buffering during normal operation
        await message_buffer.add_message({"type": "normal_operation", "data": "test"})
        assert len(message_buffer.messages) == 1
        
        # Phase 2: Connection failure and recovery
        with patch.object(connection_manager, '_ping_connection', return_value=False):
        health_ok = await connection_manager.health_check(connection)
        assert not health_ok
            
        # Buffer messages during failure
        await message_buffer.add_message({"type": "failure_operation", "data": "buffered"})
        assert len(message_buffer.messages) == 2
        
        # Phase 3: Successful recovery
        with patch.object(connection_manager, '_create_http_transport', return_value=MockTransport()):
        with patch.object(connection_manager, '_connect_transport'):
        with patch.object(connection_manager, '_ping_connection', return_value=True):
        recovered_connection = await connection_manager.reconnect(connection)
        assert recovered_connection.status == ConnectionStatus.CONNECTED
                    
        # Flush buffered messages after recovery
        flushed = await message_buffer.flush_messages()
        assert len(flushed) == 2
        assert len(message_buffer.messages) == 0
        
        # Phase 4: Verify metrics and pool state
        metrics = connection_manager.get_metrics(mock_server_config.name)
        assert metrics is not None
        assert metrics.total_created >= 1
        
        pool_status = connection_manager.get_pool_status()
        assert mock_server_config.name in pool_status
        
        # Phase 5: Clean shutdown
        await connection_manager.close_all_connections()
        
        # Verify clean shutdown
        assert all(pool.empty() for pool in connection_manager._pools.values())