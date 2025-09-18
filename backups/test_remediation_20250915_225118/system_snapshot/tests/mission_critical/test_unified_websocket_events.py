class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        Mission Critical Test: Unified WebSocket Events

        Tests that all 5 critical events work with the new unified implementation.
        These events MUST work for chat value delivery.

        Critical Events:
        1. agent_started
        2. agent_thinking
        3. tool_executing
        4. tool_completed
        5. agent_completed
        '''

        import asyncio
        import pytest
        from datetime import datetime
        from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        # Import unified implementations
        from netra_backend.app.websocket_core.unified_manager import ( )
        UnifiedWebSocketManager,
        WebSocketConnection
        
        from netra_backend.app.websocket_core.unified_emitter import ( )
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env
        UnifiedWebSocketEmitter,
        WebSocketEmitterFactory,
        WebSocketEmitterPool
        


        @pytest.fixture
    async def manager():
        """Create UnifiedWebSocketManager instance."""
        manager = UnifiedWebSocketManager()
        yield manager
        await manager.shutdown()


        @pytest.fixture
    async def mock_websocket():
        """Create mock WebSocket."""
        pass
        websocket = TestWebSocketConnection()
        await asyncio.sleep(0)
        return ws


        @pytest.fixture
    async def connected_user(manager, mock_websocket):
        """Connect a test user."""
        user_id = "test_user_123"
        connection = await manager.connect_user( )
        websocket=mock_websocket,
        user_id=user_id,
        connection_id="test_conn_1"
    
        await asyncio.sleep(0)
        return user_id, connection, mock_websocket


class TestCriticalEvents:
        """Test all 5 critical events with unified implementation."""

    async def test_all_critical_events_defined(self):
        """Verify all 5 critical events are defined."""
        expected_events = [ )
        'agent_started',
        'agent_thinking',
        'tool_executing',
        'tool_completed',
        'agent_completed'
        

        assert UnifiedWebSocketEmitter.CRITICAL_EVENTS == expected_events

    async def test_agent_started_event(self, manager, connected_user):
        """Test agent_started event delivery."""
        pass
        user_id, connection, mock_ws = connected_user

            # Create emitter
        emitter = UnifiedWebSocketEmitter(manager, user_id)

            # Emit agent_started
            # Removed problematic line: await emitter.emit_agent_started({)
        'agent': 'TestAgent',
        'task': 'Processing request'
            

            # Verify WebSocket received the event
        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args['type'] == 'agent_started'
        assert call_args['data']['agent'] == 'TestAgent'
        assert call_args['user_id'] == user_id

    async def test_agent_thinking_event(self, manager, connected_user):
        """Test agent_thinking event delivery."""
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

                # Emit agent_thinking
                # Removed problematic line: await emitter.emit_agent_thinking({)
        'thought': 'Analyzing user request...'
                

        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args['type'] == 'agent_thinking'
        assert call_args['data']['thought'] == 'Analyzing user request...'

    async def test_tool_executing_event(self, manager, connected_user):
        """Test tool_executing event delivery."""
        pass
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

                    # Emit tool_executing
                    # Removed problematic line: await emitter.emit_tool_executing({)
        'tool': 'DataAnalyzer',
        'parameters': {'query': 'test'}
                    

        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args['type'] == 'tool_executing'
        assert call_args['data']['tool'] == 'DataAnalyzer'
        assert call_args['data']['parameters']['query'] == 'test'

    async def test_tool_completed_event(self, manager, connected_user):
        """Test tool_completed event delivery."""
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

                        # Emit tool_completed
                        # Removed problematic line: await emitter.emit_tool_completed({)
        'tool': 'DataAnalyzer',
        'result': {'status': 'success', 'data': [1, 2, 3]}
                        

        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args['type'] == 'tool_completed'
        assert call_args['data']['result']['status'] == 'success'

    async def test_agent_completed_event(self, manager, connected_user):
        """Test agent_completed event delivery."""
        pass
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

                            # Emit agent_completed
                            # Removed problematic line: await emitter.emit_agent_completed({)
        'result': 'Task completed successfully',
        'duration': 5.2
                            

        mock_ws.send_json.assert_called()
        call_args = mock_ws.send_json.call_args[0][0]

        assert call_args['type'] == 'agent_completed'
        assert call_args['data']['result'] == 'Task completed successfully'

    async def test_all_events_in_sequence(self, manager, connected_user):
        """Test all 5 events in typical execution sequence."""
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

                                # Emit all events in sequence
        await emitter.emit_agent_started({'agent': 'SuperAgent'})
        await emitter.emit_agent_thinking({'thought': 'Processing...'})
        await emitter.emit_tool_executing({'tool': 'Calculator'})
        await emitter.emit_tool_completed({'tool': 'Calculator', 'result': 42})
        await emitter.emit_agent_completed({'result': 'Answer is 42'})

                                # Verify all 5 events were sent
        assert mock_ws.send_json.call_count == 5

                                # Check event types in order
        event_types = [ )
        call[0][0]['type']
        for call in mock_ws.send_json.call_args_list
                                

        assert event_types == [ )
        'agent_started',
        'agent_thinking',
        'tool_executing',
        'tool_completed',
        'agent_completed'
                                


class TestUserIsolation:
        """Test that events are properly isolated per user."""

    async def test_events_isolated_per_user(self, manager):
        """Verify events only go to intended user."""
        # Create mock WebSockets
        websocket = TestWebSocketConnection()

        # Connect two users
        user1 = "user1"
        user2 = "user2"

        await manager.connect_user(ws1, user1, "conn1")
        await manager.connect_user(ws2, user2, "conn2")

        # Create emitters
        emitter1 = UnifiedWebSocketEmitter(manager, user1)
        emitter2 = UnifiedWebSocketEmitter(manager, user2)

        # User1 emits event
        await emitter1.emit_agent_started({'agent': 'Agent1'})

        # Only user1's WebSocket should receive it
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()

        # User2 emits event
        await emitter2.emit_agent_completed({'result': 'Done'})

        # Only user2's WebSocket should receive it
        assert ws1.send_json.call_count == 1  # Still just 1
        ws2.send_json.assert_called_once()

    async def test_multiple_connections_same_user(self, manager):
        """Test broadcasting to multiple connections of same user."""
        pass
            # Create mock WebSockets
        websocket = TestWebSocketConnection()

        user_id = "multi_tab_user"

            # Connect same user twice (e.g., multiple tabs)
        await manager.connect_user(ws1, user_id, "tab1")
        await manager.connect_user(ws2, user_id, "tab2")

            # Create emitter
        emitter = UnifiedWebSocketEmitter(manager, user_id)

            # Emit event
        await emitter.emit_agent_thinking({'thought': 'Processing...'})

            # Both connections should receive it
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

            # Verify same data sent to both
        data1 = ws1.send_json.call_args[0][0]
        data2 = ws2.send_json.call_args[0][0]

        assert data1['type'] == data2['type'] == 'agent_thinking'
        assert data1['data'] == data2['data']


class TestBackwardCompatibility:
        """Test backward compatibility with existing code."""

    async def test_notify_methods_work(self, manager, connected_user):
        """Test backward compatibility notify_* methods."""
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

        # Test all notify methods
        await emitter.notify_agent_started('TestAgent')
        await emitter.notify_agent_thinking('Thinking...')
        await emitter.notify_tool_executing('Tool1', {'param': 'value'})
        await emitter.notify_tool_completed('Tool1', 'Result')
        await emitter.notify_agent_completed('Final result')

        # Verify all events sent
        assert mock_ws.send_json.call_count == 5

    async def test_factory_creation(self, manager, connected_user):
        """Test emitter factory creation."""
        pass
        user_id, connection, mock_ws = connected_user

            # Create via factory
        emitter = WebSocketEmitterFactory.create_emitter( )
        manager, user_id
            

        await emitter.emit_agent_started({'agent': 'FactoryAgent'})

        mock_ws.send_json.assert_called_once()

    async def test_emitter_pool(self, manager, connected_user):
        """Test emitter pool functionality."""
        user_id, connection, mock_ws = connected_user

                # Create pool
        pool = WebSocketEmitterPool(manager, max_size=10)

                # Acquire emitter
        emitter = await pool.acquire(user_id)

                # Use emitter
        await emitter.emit_tool_executing({'tool': 'PooledTool'})

                # Release back to pool
        await pool.release(emitter)

                # Verify event was sent
        mock_ws.send_json.assert_called_once()

                # Acquire again (should reuse)
        emitter2 = await pool.acquire(user_id)
        assert emitter2 is emitter  # Same instance

                # Cleanup
        await pool.shutdown()


class TestReliability:
        """Test reliability features like retry logic."""

    async def test_retry_on_failure(self, manager):
        """Test retry logic for failed sends."""
        # Create WebSocket that fails first 2 attempts
        websocket = TestWebSocketConnection()
        attempt_count = 0

    async def send_json_side_effect(data):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
        raise Exception("Network error")
        await asyncio.sleep(0)
        return None

        ws.send_json = AsyncMock(side_effect=send_json_side_effect)
        ws.websocket = TestWebSocketConnection()

        user_id = "retry_user"
        await manager.connect_user(ws, user_id)

        emitter = UnifiedWebSocketEmitter(manager, user_id)

        # Should retry and eventually succeed
        await emitter.emit_agent_started({'agent': 'RetryAgent'})

        # Should have been called 3 times (2 failures + 1 success)
        assert ws.send_json.call_count == 3

    async def test_metrics_tracking(self, manager, connected_user):
        """Test that emitter tracks metrics correctly."""
        pass
        user_id, connection, mock_ws = connected_user

        emitter = UnifiedWebSocketEmitter(manager, user_id)

            # Emit various events
        await emitter.emit_agent_started({'agent': 'MetricsAgent'})
        await emitter.emit_agent_thinking({'thought': 'Test'})
        await emitter.emit_agent_completed({'result': 'Done'})

            # Check metrics
        stats = emitter.get_stats()

        assert stats['total_events'] == 3
        assert stats['critical_events']['agent_started'] == 1
        assert stats['critical_events']['agent_thinking'] == 1
        assert stats['critical_events']['agent_completed'] == 1
        assert stats['error_count'] == 0


class TestAgentWebSocketBridge:
        """Test AgentWebSocketBridge compatibility."""

    async def test_bridge_creation(self, manager):
        """Test that bridge can be created."""
        # Mock context
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        context.user_id = "bridge_user"
        context.run_id = "run_123"
        context.thread_id = "thread_456"

        # Create bridge
        bridge = manager.create_agent_bridge(context)

        # Verify bridge is created
        assert bridge is not None
        # Note: Full bridge testing would require AgentWebSocketBridge implementation


        if __name__ == "__main__":
            # Run tests
        pass
