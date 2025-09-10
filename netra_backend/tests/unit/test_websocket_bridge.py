"""
Test WebSocket Bridge Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure WebSocket events deliver business value through chat
- Value Impact: WebSocket events enable real-time AI interaction visibility for users
- Strategic Impact: Mission critical - WebSocket events are core to chat functionality
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
from netra_backend.app.services.websocket_bridge_factory import (
    WebSocketBridgeFactory,
    UserWebSocketEmitter,
    UserWebSocketContext,
    UserWebSocketConnection,
    WebSocketEvent,
    WebSocketFactoryConfig,
    ConnectionStatus,
    get_websocket_bridge_factory
)


class TestWebSocketBridgeAdapter:
    """Test WebSocketBridgeAdapter business logic"""
    
    @pytest.mark.unit
    def test_adapter_initialization(self):
        """Test adapter initialization with proper defaults"""
        adapter = WebSocketBridgeAdapter()
        
        assert adapter._bridge is None
        assert adapter._run_id is None
        assert adapter._agent_name is None
        assert adapter.has_websocket_bridge() is False
    
    @pytest.mark.unit
    def test_websocket_bridge_configuration(self):
        """Test proper WebSocket bridge configuration"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = Mock()
        run_id = "test-run-123"
        agent_name = "cost_optimizer"
        
        adapter.set_websocket_bridge(mock_bridge, run_id, agent_name)
        
        assert adapter._bridge is mock_bridge
        assert adapter._run_id == run_id
        assert adapter._agent_name == agent_name
        assert adapter.has_websocket_bridge() is True
    
    @pytest.mark.unit
    def test_bridge_configuration_validation(self):
        """Test validation of bridge configuration parameters"""
        adapter = WebSocketBridgeAdapter()
        
        # Test None bridge
        adapter.set_websocket_bridge(None, "run_id", "agent_name")
        assert adapter._bridge is None
        assert adapter.has_websocket_bridge() is False
        
        # Test None run_id
        mock_bridge = Mock()
        adapter.set_websocket_bridge(mock_bridge, None, "agent_name")
        assert adapter._bridge is mock_bridge
        assert adapter._run_id is None
        assert adapter.has_websocket_bridge() is False
        
        # Test valid configuration
        adapter.set_websocket_bridge(mock_bridge, "valid_run", "valid_agent")
        assert adapter.has_websocket_bridge() is True
    
    @pytest.mark.unit
    async def test_agent_started_event_success(self):
        """Test successful agent_started event emission"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        
        # Mock WebSocket validator
        mock_validator = Mock()
        mock_validator.validate_event.return_value = Mock(is_valid=True)
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.get_websocket_validator', 
                   return_value=mock_validator):
            adapter.set_websocket_bridge(mock_bridge, "run-123", "test_agent")
            
            await adapter.emit_agent_started("Starting optimization analysis")
            
            # Verify bridge was called with correct parameters
            mock_bridge.notify_agent_started.assert_called_once()
            call_args = mock_bridge.notify_agent_started.call_args
            assert call_args[0][0] == "run-123"  # run_id
            assert call_args[0][1] == "test_agent"  # agent_name
            assert "message" in call_args[1]["context"]
    
    @pytest.mark.unit
    async def test_agent_started_missing_bridge_failure(self):
        """Test agent_started event fails when bridge missing - HARD FAILURE"""
        adapter = WebSocketBridgeAdapter()
        adapter._agent_name = "test_agent"
        
        # Should raise RuntimeError for missing bridge (CLAUDE.MD requirement)
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.emit_agent_started("Test message")
        
        error_msg = str(exc_info.value)
        assert "Missing WebSocket bridge for agent_started event" in error_msg
        assert "test_agent" in error_msg
        assert "SSOT requirement" in error_msg
    
    @pytest.mark.unit
    async def test_thinking_event_success(self):
        """Test successful agent_thinking event emission"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-456", "thinking_agent")
        
        thought = "Analyzing cost patterns in AWS spend data"
        await adapter.emit_thinking(thought, step_number=1)
        
        mock_bridge.notify_agent_thinking.assert_called_once_with(
            "run-456",
            "thinking_agent", 
            thought,
            step_number=1
        )
    
    @pytest.mark.unit
    async def test_thinking_event_missing_bridge_failure(self):
        """Test agent_thinking event fails when bridge missing"""
        adapter = WebSocketBridgeAdapter()
        adapter._agent_name = "thinking_agent"
        
        with pytest.raises(RuntimeError) as exc_info:
            await adapter.emit_thinking("Some thought")
        
        error_msg = str(exc_info.value)
        assert "Missing WebSocket bridge for agent_thinking event" in error_msg
        assert "thinking_agent" in error_msg
    
    @pytest.mark.unit
    async def test_tool_executing_event_success(self):
        """Test successful tool_executing event emission"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-789", "tool_agent")
        
        tool_name = "cost_analyzer"
        parameters = {"timeframe": "last_30_days", "service": "EC2"}
        
        await adapter.emit_tool_executing(tool_name, parameters)
        
        mock_bridge.notify_tool_executing.assert_called_once_with(
            "run-789",
            "tool_agent",
            tool_name,
            parameters=parameters
        )
    
    @pytest.mark.unit
    async def test_tool_completed_event_success(self):
        """Test successful tool_completed event emission"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-101", "completion_agent")
        
        tool_name = "cost_analyzer"
        result = {"savings_identified": 1500, "recommendations": 3}
        
        await adapter.emit_tool_completed(tool_name, result)
        
        mock_bridge.notify_tool_completed.assert_called_once_with(
            "run-101",
            "completion_agent",
            tool_name,
            result=result
        )
    
    @pytest.mark.unit
    async def test_agent_completed_event_success(self):
        """Test successful agent_completed event emission"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-202", "final_agent")
        
        result = {
            "analysis_complete": True,
            "total_savings": 1500,
            "recommendations": ["Resize instances", "Use reserved instances"]
        }
        
        await adapter.emit_agent_completed(result)
        
        mock_bridge.notify_agent_completed.assert_called_once_with(
            "run-202",
            "final_agent",
            result=result
        )
    
    @pytest.mark.unit
    async def test_all_critical_events_fail_without_bridge(self):
        """Test all 5 critical events fail without bridge - Business Value Protection"""
        adapter = WebSocketBridgeAdapter()
        adapter._agent_name = "critical_agent"
        
        # All 5 critical events should raise RuntimeError
        with pytest.raises(RuntimeError):
            await adapter.emit_agent_started()
            
        with pytest.raises(RuntimeError):
            await adapter.emit_thinking("thought")
            
        with pytest.raises(RuntimeError):
            await adapter.emit_tool_executing("tool")
            
        with pytest.raises(RuntimeError):
            await adapter.emit_tool_completed("tool")
            
        with pytest.raises(RuntimeError):
            await adapter.emit_agent_completed()
    
    @pytest.mark.unit
    async def test_bridge_exception_handling(self):
        """Test adapter handles bridge exceptions gracefully"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        mock_bridge.notify_agent_started.side_effect = Exception("Bridge connection failed")
        
        # Mock validator to pass
        mock_validator = Mock()
        mock_validator.validate_event.return_value = Mock(is_valid=True)
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.get_websocket_validator', 
                   return_value=mock_validator):
            adapter.set_websocket_bridge(mock_bridge, "run-303", "error_agent")
            
            # Should not raise exception - adapter handles bridge failures
            await adapter.emit_agent_started("test message")
            
            # Verify bridge was called despite failure
            mock_bridge.notify_agent_started.assert_called_once()
    
    @pytest.mark.unit
    async def test_backward_compatibility_methods(self):
        """Test backward compatibility methods work correctly"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, "run-404", "compat_agent")
        
        # Test emit_tool_started maps to emit_tool_executing
        await adapter.emit_tool_started("legacy_tool", {"param": "value"})
        
        mock_bridge.notify_tool_executing.assert_called_once_with(
            "run-404",
            "compat_agent",
            "legacy_tool",
            parameters={"param": "value"}
        )


class TestWebSocketBridgeFactory:
    """Test WebSocketBridgeFactory business logic"""
    
    @pytest.mark.unit
    def test_factory_initialization(self):
        """Test factory initialization with proper configuration"""
        config = WebSocketFactoryConfig(
            max_events_per_user=500,
            event_timeout_seconds=15.0
        )
        factory = WebSocketBridgeFactory(config)
        
        assert factory.config.max_events_per_user == 500
        assert factory.config.event_timeout_seconds == 15.0
        assert factory._user_contexts == {}
        assert factory._factory_metrics['emitters_created'] == 0
        assert factory._factory_metrics['emitters_active'] == 0
    
    @pytest.mark.unit
    def test_factory_configuration_validation(self):
        """Test factory configuration requirements"""
        factory = WebSocketBridgeFactory()
        
        # Should require connection pool
        with pytest.raises(ValueError):
            factory.configure(None, Mock(), Mock())
        
        # Should accept valid configuration
        mock_pool = Mock()
        mock_registry = Mock()
        mock_monitor = Mock()
        
        factory.configure(mock_pool, mock_registry, mock_monitor)
        assert factory._connection_pool is mock_pool
        assert factory._agent_registry is mock_registry
        assert factory._health_monitor is mock_monitor
    
    @pytest.mark.unit
    async def test_user_context_creation(self):
        """Test user context creation and isolation"""
        factory = WebSocketBridgeFactory()
        
        # Create user context
        user_id = "user123"
        thread_id = "thread456"
        connection_id = "conn789"
        
        context = await factory._get_or_create_user_context(user_id, thread_id, connection_id)
        
        assert context.user_id == user_id
        assert context.thread_id == thread_id
        assert context.connection_id == connection_id
        assert context.connection_status == ConnectionStatus.INITIALIZING
        assert isinstance(context.event_queue, asyncio.Queue)
        assert len(context.sent_events) == 0
        assert len(context.failed_events) == 0
    
    @pytest.mark.unit
    async def test_user_context_isolation(self):
        """Test complete isolation between user contexts"""
        factory = WebSocketBridgeFactory()
        
        # Create contexts for two different users
        context1 = await factory._get_or_create_user_context("user1", "thread1", "conn1")
        context2 = await factory._get_or_create_user_context("user2", "thread2", "conn2")
        
        # Contexts should be completely separate
        assert context1.user_id != context2.user_id
        assert context1.event_queue is not context2.event_queue
        assert context1.sent_events is not context2.sent_events
        
        # Same user, different connection should create separate context
        context3 = await factory._get_or_create_user_context("user1", "thread1", "conn3")
        assert context3 is not context1
        assert context3.connection_id != context1.connection_id
    
    @pytest.mark.unit
    async def test_user_emitter_creation(self):
        """Test user emitter creation with valid WebSocket"""
        factory = WebSocketBridgeFactory()
        
        # Mock connection pool with valid WebSocket
        mock_websocket = AsyncMock()
        mock_connection_info = Mock()
        mock_connection_info.websocket = mock_websocket
        
        mock_pool = AsyncMock()
        mock_pool.get_connection.return_value = mock_connection_info
        
        factory.configure(mock_pool, Mock(), Mock())
        
        # Mock notification monitor
        mock_monitor = Mock()
        mock_monitor.track_bridge_initialization_started.return_value = "correlation-123"
        mock_monitor.track_bridge_initialization_success = Mock()
        factory.notification_monitor = mock_monitor
        
        # Create emitter
        emitter = await factory.create_user_emitter("user123", "thread456", "conn789")
        
        assert isinstance(emitter, UserWebSocketEmitter)
        assert emitter.user_context.user_id == "user123"
        assert factory._factory_metrics['emitters_created'] == 1
        assert factory._factory_metrics['emitters_active'] == 1
    
    @pytest.mark.unit
    async def test_emitter_creation_fails_without_websocket(self):
        """Test emitter creation fails without real WebSocket connection"""
        factory = WebSocketBridgeFactory()
        
        # Mock connection pool returning None or no websocket
        mock_pool = AsyncMock()
        mock_pool.get_connection.return_value = None
        
        factory.configure(mock_pool, Mock(), Mock())
        
        # Mock notification monitor
        mock_monitor = Mock()
        mock_monitor.track_bridge_initialization_started.return_value = "correlation-123"
        mock_monitor.track_bridge_initialization_failed = Mock()
        factory.notification_monitor = mock_monitor
        
        # Should fail without real WebSocket
        with pytest.raises(RuntimeError) as exc_info:
            await factory.create_user_emitter("user123", "thread456", "conn789")
        
        assert "No active WebSocket connection found" in str(exc_info.value)
        assert factory._factory_metrics['emitters_created'] == 0
    
    @pytest.mark.unit
    async def test_user_context_cleanup(self):
        """Test user context cleanup removes context properly"""
        factory = WebSocketBridgeFactory()
        
        # Create user context
        context = await factory._get_or_create_user_context("user123", "thread456", "conn789")
        assert len(factory._user_contexts) == 1
        
        # Cleanup context
        await factory.cleanup_user_context("user123", "conn789")
        
        assert len(factory._user_contexts) == 0
        assert factory._factory_metrics['emitters_cleaned'] == 1
    
    @pytest.mark.unit
    def test_factory_metrics_tracking(self):
        """Test factory metrics are properly tracked"""
        factory = WebSocketBridgeFactory()
        
        # Check initial metrics
        metrics = factory.get_factory_metrics()
        assert metrics['emitters_created'] == 0
        assert metrics['emitters_active'] == 0
        assert metrics['emitters_cleaned'] == 0
        assert metrics['active_contexts'] == 0
        assert 'config' in metrics
        assert 'timestamp' in metrics
    
    @pytest.mark.unit
    def test_singleton_factory_pattern(self):
        """Test singleton factory pattern works correctly"""
        factory1 = get_websocket_bridge_factory()
        factory2 = get_websocket_bridge_factory()
        
        assert factory1 is factory2


class TestUserWebSocketEmitter:
    """Test UserWebSocketEmitter business logic"""
    
    @pytest.mark.unit
    def test_emitter_initialization(self):
        """Test emitter initialization with proper components"""
        user_context = UserWebSocketContext(
            user_id="user123",
            thread_id="thread456", 
            connection_id="conn789"
        )
        
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn789", mock_websocket)
        
        delivery_config = {
            'max_retries': 3,
            'timeout': 5.0,
            'heartbeat_interval': 30.0
        }
        
        mock_factory = Mock()
        mock_factory._factory_metrics = {'events_sent_total': 0, 'events_failed_total': 0}
        
        emitter = UserWebSocketEmitter(user_context, connection, delivery_config, mock_factory)
        
        assert emitter.user_context is user_context
        assert emitter.connection is connection
        assert emitter.delivery_config is delivery_config
        assert emitter._shutdown is False
        assert isinstance(emitter._processor_task, asyncio.Task)
    
    @pytest.mark.unit
    async def test_agent_started_notification(self):
        """Test agent started notification creates proper event"""
        user_context = UserWebSocketContext("user123", "thread456", "conn789")
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn789", mock_websocket)
        mock_factory = Mock()
        mock_factory._factory_metrics = {'events_sent_total': 0, 'events_failed_total': 0}
        
        # Mock notification monitor
        mock_monitor = AsyncMock()
        mock_monitor.monitor_notification.return_value.__aenter__.return_value = "corr-123"
        
        emitter = UserWebSocketEmitter(user_context, connection, {}, mock_factory)
        emitter.notification_monitor = mock_monitor
        
        # Call notification method
        await emitter.notify_agent_started("cost_optimizer", "run-123")
        
        # Should have queued event
        assert not user_context.event_queue.empty()
        
        # Get the event and verify
        event = await user_context.event_queue.get()
        assert event.event_type == "agent_started"
        assert event.user_id == "user123"
        assert event.data["agent_name"] == "cost_optimizer"
        assert event.data["run_id"] == "run-123"
    
    @pytest.mark.unit
    async def test_event_queue_overflow_protection(self):
        """Test event queue overflow protection drops oldest events"""
        user_context = UserWebSocketContext("user123", "thread456", "conn789")
        # Create small queue for testing
        user_context.event_queue = asyncio.Queue(maxsize=2)
        
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn789", mock_websocket) 
        mock_factory = Mock()
        mock_factory._factory_metrics = {'events_sent_total': 0, 'events_failed_total': 0}
        
        emitter = UserWebSocketEmitter(user_context, connection, {}, mock_factory)
        
        # Create events that exceed queue capacity
        event1 = WebSocketEvent("type1", "user123", "thread456", {"data": "1"})
        event2 = WebSocketEvent("type2", "user123", "thread456", {"data": "2"})
        event3 = WebSocketEvent("type3", "user123", "thread456", {"data": "3"})
        
        # Queue first two events
        await emitter._queue_event(event1)
        await emitter._queue_event(event2)
        assert user_context.event_queue.qsize() == 2
        
        # Third event should trigger overflow protection
        await emitter._queue_event(event3)
        
        # Should still have 2 events but oldest should be dropped
        assert user_context.event_queue.qsize() == 2
        
        # Verify newest event is in queue
        first_event = await user_context.event_queue.get()
        second_event = await user_context.event_queue.get()
        
        # Should have event2 and event3 (event1 was dropped)
        event_types = [first_event.event_type, second_event.event_type]
        assert "type2" in event_types
        assert "type3" in event_types
    
    @pytest.mark.unit
    async def test_event_sanitization(self):
        """Test event data sanitization protects business IP"""
        user_context = UserWebSocketContext("user123", "thread456", "conn789") 
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn789", mock_websocket)
        mock_factory = Mock()
        mock_factory._factory_metrics = {'events_sent_total': 0, 'events_failed_total': 0}
        
        emitter = UserWebSocketEmitter(user_context, connection, {}, mock_factory)
        
        # Test tool input sanitization
        sensitive_input = {
            "query": "SELECT * FROM costs",
            "api_key": "secret-key-123",
            "password": "super-secret",
            "large_data": "x" * 300
        }
        
        sanitized = emitter._sanitize_tool_input(sensitive_input)
        
        assert sanitized["query"] == "SELECT * FROM costs"
        assert sanitized["api_key"] == "[REDACTED]"
        assert sanitized["password"] == "[REDACTED]" 
        assert len(sanitized["large_data"]) == 203  # 200 + "..."
        
        # Test error message sanitization
        error_with_path = "Error in /Users/developer/project/secret_file.py line 42"
        sanitized_error = emitter._sanitize_error_message(error_with_path)
        assert "/Users/developer" not in sanitized_error
        assert "[PATH]" in sanitized_error
    
    @pytest.mark.unit
    async def test_emitter_cleanup(self):
        """Test emitter cleanup properly releases resources"""
        user_context = UserWebSocketContext("user123", "thread456", "conn789")
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn789", mock_websocket)
        mock_factory = AsyncMock()
        mock_factory._factory_metrics = {'events_sent_total': 0, 'events_failed_total': 0}
        
        emitter = UserWebSocketEmitter(user_context, connection, {}, mock_factory)
        
        # Add some pending events and data
        await emitter._queue_event(WebSocketEvent("test", "user123", "thread456", {}))
        emitter._pending_events["event1"] = WebSocketEvent("pending", "user123", "thread456", {})
        
        # Cleanup
        await emitter.cleanup()
        
        # Verify cleanup
        assert emitter._shutdown is True
        assert len(emitter._pending_events) == 0
        assert len(emitter._event_batch) == 0
        
        # Factory cleanup should be called
        mock_factory.cleanup_user_context.assert_called_once_with("user123", "conn789")


class TestUserWebSocketConnection:
    """Test UserWebSocketConnection business logic"""
    
    @pytest.mark.unit
    def test_connection_initialization(self):
        """Test connection initialization with WebSocket"""
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        
        assert connection.user_id == "user123"
        assert connection.connection_id == "conn456"
        assert connection.websocket is mock_websocket
        assert connection._closed is False
        assert isinstance(connection.created_at, datetime)
        assert isinstance(connection.last_activity, datetime)
    
    @pytest.mark.unit
    async def test_event_sending_success(self):
        """Test successful event sending through WebSocket"""
        mock_websocket = AsyncMock()
        mock_websocket.send_json = AsyncMock()
        
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        
        event = WebSocketEvent(
            event_type="test_event",
            user_id="user123",
            thread_id="thread456",
            data={"message": "test"}
        )
        
        await connection.send_event(event)
        
        # Verify WebSocket send was called
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args['event_type'] == "test_event"
        assert call_args['data']['message'] == "test"
    
    @pytest.mark.unit
    async def test_event_sending_closed_connection(self):
        """Test event sending fails on closed connection"""
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        connection._closed = True
        
        event = WebSocketEvent("test", "user123", "thread456", {})
        
        with pytest.raises(ConnectionError) as exc_info:
            await connection.send_event(event)
        
        assert "Connection closed for user user123" in str(exc_info.value)
    
    @pytest.mark.unit
    async def test_connection_ping_success(self):
        """Test successful connection ping"""
        mock_websocket = AsyncMock()
        mock_websocket.ping = AsyncMock()
        
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        
        is_healthy = await connection.ping()
        
        assert is_healthy is True
        mock_websocket.ping.assert_called_once()
        # last_activity should be updated
        assert connection.last_activity >= connection.created_at
    
    @pytest.mark.unit
    async def test_connection_ping_failure(self):
        """Test connection ping failure handling"""
        mock_websocket = AsyncMock()
        mock_websocket.ping.side_effect = Exception("Connection lost")
        
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        
        is_healthy = await connection.ping()
        
        assert is_healthy is False
        assert connection._closed is True
    
    @pytest.mark.unit
    def test_connection_stale_detection(self):
        """Test stale connection detection"""
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        
        # Fresh connection should not be stale
        current_time = datetime.now(timezone.utc)
        assert connection.is_stale(current_time, stale_threshold=1800) is False
        
        # Simulate old last_activity
        connection.last_activity = datetime.now(timezone.utc).replace(year=2020)
        assert connection.is_stale(current_time, stale_threshold=1800) is True
    
    @pytest.mark.unit
    async def test_connection_close(self):
        """Test connection close functionality"""
        mock_websocket = AsyncMock()
        mock_websocket.close = AsyncMock()
        
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        
        await connection.close()
        
        assert connection._closed is True
        mock_websocket.close.assert_called_once()


class TestWebSocketEvent:
    """Test WebSocketEvent business logic"""
    
    @pytest.mark.unit
    def test_event_initialization(self):
        """Test WebSocket event initialization"""
        data = {"message": "test", "agent": "cost_optimizer"}
        event = WebSocketEvent("agent_started", "user123", "thread456", data)
        
        assert event.event_type == "agent_started"
        assert event.user_id == "user123"
        assert event.thread_id == "thread456"
        assert event.data == data
        assert event.retry_count == 0
        assert event.max_retries == 3
        assert isinstance(event.timestamp, datetime)
        assert len(event.event_id) > 0
    
    @pytest.mark.unit
    def test_event_retry_logic(self):
        """Test event retry count logic"""
        event = WebSocketEvent("test_event", "user123", "thread456", {}, max_retries=2)
        
        # Initial state
        assert event.retry_count == 0
        assert event.max_retries == 2
        
        # Simulate retries
        event.retry_count += 1
        assert event.retry_count == 1
        
        event.retry_count += 1
        assert event.retry_count == 2
        
        # Should be at max retries
        assert event.retry_count == event.max_retries


class TestWebSocketFactoryConfig:
    """Test WebSocketFactoryConfig business logic"""
    
    @pytest.mark.unit
    def test_config_defaults(self):
        """Test configuration default values"""
        config = WebSocketFactoryConfig()
        
        assert config.max_events_per_user == 1000
        assert config.event_timeout_seconds == 30.0
        assert config.heartbeat_interval_seconds == 30.0
        assert config.max_reconnect_attempts == 3
        assert config.delivery_retries == 3
        assert config.delivery_timeout_seconds == 5.0
        assert config.enable_event_compression is True
        assert config.enable_event_batching is True
    
    @pytest.mark.unit
    def test_config_custom_values(self):
        """Test configuration with custom values"""
        config = WebSocketFactoryConfig(
            max_events_per_user=500,
            event_timeout_seconds=15.0,
            delivery_retries=5
        )
        
        assert config.max_events_per_user == 500
        assert config.event_timeout_seconds == 15.0
        assert config.delivery_retries == 5
        # Other values should remain default
        assert config.heartbeat_interval_seconds == 30.0
    
    @pytest.mark.unit
    def test_config_from_environment(self):
        """Test configuration creation from environment variables"""
        mock_env = Mock()
        mock_env.get.side_effect = lambda key, default: {
            'WEBSOCKET_MAX_EVENTS_PER_USER': '750',
            'WEBSOCKET_EVENT_TIMEOUT': '20.0',
            'WEBSOCKET_DELIVERY_RETRIES': '4'
        }.get(key, default)
        
        with patch('netra_backend.app.services.websocket_bridge_factory.get_env', 
                   return_value=mock_env):
            config = WebSocketFactoryConfig.from_env()
        
        assert config.max_events_per_user == 750
        assert config.event_timeout_seconds == 20.0
        assert config.delivery_retries == 4


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.mark.unit
    async def test_adapter_event_validation_failure(self):
        """Test adapter handles validation failures properly"""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        
        # Mock validator that fails
        mock_validator = Mock()
        mock_validator.validate_event.return_value = Mock(
            is_valid=False, 
            error_message="Invalid event structure"
        )
        
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.get_websocket_validator', 
                   return_value=mock_validator):
            adapter.set_websocket_bridge(mock_bridge, "run-123", "test_agent")
            
            # Should still try to send despite validation failure
            await adapter.emit_agent_started("test message")
            
            # Bridge should still be called
            mock_bridge.notify_agent_started.assert_called_once()
    
    @pytest.mark.unit
    async def test_emitter_without_processor_task(self):
        """Test emitter behavior when processor task fails to start"""
        user_context = UserWebSocketContext("user123", "thread456", "conn789")
        mock_websocket = AsyncMock()
        connection = UserWebSocketConnection("user123", "conn789", mock_websocket)
        mock_factory = Mock()
        mock_factory._factory_metrics = {'events_sent_total': 0, 'events_failed_total': 0}
        
        # Create emitter but immediately cancel the processor
        emitter = UserWebSocketEmitter(user_context, connection, {}, mock_factory)
        emitter._processor_task.cancel()
        
        # Should still be able to queue events
        await emitter._queue_event(WebSocketEvent("test", "user123", "thread456", {}))
        assert not user_context.event_queue.empty()
        
        # Cleanup should handle cancelled task gracefully
        await emitter.cleanup()
        assert emitter._shutdown is True
    
    @pytest.mark.unit
    async def test_connection_with_unsupported_websocket_type(self):
        """Test connection handling with unsupported WebSocket type"""
        # Create mock WebSocket without standard methods
        mock_websocket = Mock()
        # Remove standard WebSocket methods
        delattr(mock_websocket, 'send_json') if hasattr(mock_websocket, 'send_json') else None
        delattr(mock_websocket, 'send') if hasattr(mock_websocket, 'send') else None
        
        connection = UserWebSocketConnection("user123", "conn456", mock_websocket)
        event = WebSocketEvent("test", "user123", "thread456", {})
        
        with pytest.raises(ConnectionError) as exc_info:
            await connection.send_event(event)
        
        assert "WebSocket type unsupported" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_user_context_multiple_cleanup_calls(self):
        """Test user context handles multiple cleanup calls gracefully"""
        context = UserWebSocketContext("user123", "thread456", "conn789")
        
        # First cleanup
        asyncio.run(context.cleanup())
        assert context._is_cleaned is True
        
        # Second cleanup should not raise error
        asyncio.run(context.cleanup())
        assert context._is_cleaned is True
    
    @pytest.mark.unit
    async def test_factory_emitter_creation_race_condition(self):
        """Test factory handles concurrent emitter creation for same user"""
        factory = WebSocketBridgeFactory()
        
        # Mock connection pool
        mock_websocket = AsyncMock()
        mock_connection_info = Mock()
        mock_connection_info.websocket = mock_websocket
        mock_pool = AsyncMock()
        mock_pool.get_connection.return_value = mock_connection_info
        factory.configure(mock_pool, Mock(), Mock())
        
        # Mock monitor
        mock_monitor = Mock()
        mock_monitor.track_bridge_initialization_started.return_value = "correlation-123"
        mock_monitor.track_bridge_initialization_success = Mock()
        factory.notification_monitor = mock_monitor
        
        # Create multiple emitters concurrently for same user but different connections
        tasks = []
        for i in range(3):
            task = asyncio.create_task(
                factory.create_user_emitter("user123", "thread456", f"conn{i}")
            )
            tasks.append(task)
        
        emitters = await asyncio.gather(*tasks)
        
        # Should create separate emitters for different connections
        assert len(emitters) == 3
        assert len(set(e.user_context.connection_id for e in emitters)) == 3
        assert factory._factory_metrics['emitters_created'] == 3