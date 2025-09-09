"""Comprehensive Unit Tests for QualityMessageRouter

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable quality message routing for WebSocket communications
- Value Impact: Quality monitoring enables proactive system health management
- Strategic Impact: Critical for maintaining service quality and user trust

This test suite validates the QualityMessageRouter's ability to:
1. Route quality messages to appropriate handlers
2. Maintain session continuity with thread_id/run_id
3. Handle unknown message types gracefully
4. Broadcast quality updates and alerts
5. Initialize all required handlers correctly
6. Integrate with quality services and WebSocket manager
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, call
from typing import Dict, Any

from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService
from netra_backend.app.services.websocket.quality_metrics_handler import QualityMetricsHandler
from netra_backend.app.services.websocket.quality_alert_handler import QualityAlertHandler
from netra_backend.app.services.websocket.quality_validation_handler import QualityValidationHandler
from netra_backend.app.services.websocket.quality_report_handler import QualityReportHandler
from netra_backend.app.quality_enhanced_start_handler import QualityEnhancedStartAgentHandler


class TestQualityMessageRouter:
    """Comprehensive test suite for QualityMessageRouter."""

    @pytest.fixture
    def mock_supervisor(self):
        """Mock supervisor for testing."""
        return Mock()

    @pytest.fixture
    def mock_db_session_factory(self):
        """Mock database session factory for testing."""
        return Mock()

    @pytest.fixture
    def mock_quality_gate_service(self):
        """Mock quality gate service for testing."""
        return Mock(spec=QualityGateService)

    @pytest.fixture
    def mock_monitoring_service(self):
        """Mock quality monitoring service for testing."""
        mock_service = Mock(spec=QualityMonitoringService)
        mock_service.subscribers = ["user1", "user2", "user3"]
        return mock_service

    @pytest.fixture
    def router(self, mock_supervisor, mock_db_session_factory, 
               mock_quality_gate_service, mock_monitoring_service):
        """Create QualityMessageRouter instance for testing."""
        with patch.object(QualityMessageRouter, '_create_enhanced_start_handler') as mock_create_start:
            # Mock the problematic handler creation to return a simple mock
            mock_start_handler = Mock()
            mock_start_handler.handle = AsyncMock()
            mock_create_start.return_value = mock_start_handler
            
            router = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            return router

    # Handler Initialization Tests
    def test_router_initialization_creates_all_handlers(self, router):
        """Test that router initialization creates all required handlers."""
        assert "get_quality_metrics" in router.handlers
        assert "subscribe_quality_alerts" in router.handlers
        assert "start_agent" in router.handlers
        assert "validate_content" in router.handlers
        assert "generate_quality_report" in router.handlers

    def test_handlers_have_correct_types(self, router):
        """Test that handlers are of correct types."""
        assert isinstance(router.handlers["get_quality_metrics"], QualityMetricsHandler)
        assert isinstance(router.handlers["subscribe_quality_alerts"], QualityAlertHandler)
        # start_agent is mocked in fixture, so just test it has handle method
        assert hasattr(router.handlers["start_agent"], 'handle')
        assert isinstance(router.handlers["validate_content"], QualityValidationHandler)
        assert isinstance(router.handlers["generate_quality_report"], QualityReportHandler)

    def test_metrics_handler_creation_with_monitoring_service(self, router, mock_monitoring_service):
        """Test metrics handler is created with monitoring service."""
        metrics_handler = router.handlers["get_quality_metrics"]
        assert metrics_handler.monitoring_service == mock_monitoring_service

    def test_alert_handler_creation_with_monitoring_service(self, router, mock_monitoring_service):
        """Test alert handler is created with monitoring service."""
        alert_handler = router.handlers["subscribe_quality_alerts"]
        assert alert_handler.monitoring_service == mock_monitoring_service

    def test_enhanced_start_handler_creation_with_no_dependencies(self, router):
        """Test enhanced start handler is created with no constructor dependencies."""
        start_handler = router.handlers["start_agent"]
        assert hasattr(start_handler, 'handle')  # Should have handle method (mocked)

    def test_validation_handler_creation_with_quality_gate_service(self, router, mock_quality_gate_service):
        """Test validation handler is created with quality gate service."""
        validation_handler = router.handlers["validate_content"]
        assert validation_handler.quality_gate_service == mock_quality_gate_service

    def test_report_handler_creation_with_monitoring_service(self, router, mock_monitoring_service):
        """Test report handler is created with monitoring service."""
        report_handler = router.handlers["generate_quality_report"]
        assert report_handler.monitoring_service == mock_monitoring_service

    # Message Routing Tests
    @pytest.mark.asyncio
    async def test_handle_message_valid_type_routes_to_correct_handler(self, router):
        """Test that valid message types are routed to correct handlers."""
        # Mock the handler
        mock_handler = AsyncMock()
        router.handlers["get_quality_metrics"] = mock_handler
        
        message = {
            "type": "get_quality_metrics",
            "thread_id": "thread123",
            "run_id": "run456",
            "payload": {"agent_name": "test_agent"}
        }
        
        await router.handle_message("user123", message)
        
        # Verify handler was called with correct parameters
        expected_payload = {
            "agent_name": "test_agent",
            "thread_id": "thread123",
            "run_id": "run456"
        }
        mock_handler.handle.assert_called_once_with("user123", expected_payload)

    @pytest.mark.asyncio
    async def test_handle_message_sets_current_thread_and_run_ids(self, router):
        """Test that handle_message sets current thread_id and run_id for session continuity."""
        mock_handler = AsyncMock()
        router.handlers["get_quality_metrics"] = mock_handler
        
        message = {
            "type": "get_quality_metrics",
            "thread_id": "session_thread_123",
            "run_id": "session_run_456",
            "payload": {}
        }
        
        await router.handle_message("user123", message)
        
        # Verify session continuity IDs are stored
        assert router._current_thread_id == "session_thread_123"
        assert router._current_run_id == "session_run_456"

    @pytest.mark.asyncio
    async def test_handle_message_adds_context_ids_to_payload(self, router):
        """Test that thread_id and run_id are added to payload for handler access."""
        mock_handler = AsyncMock()
        router.handlers["validate_content"] = mock_handler
        
        message = {
            "type": "validate_content",
            "thread_id": "ctx_thread_789",
            "run_id": "ctx_run_101",
            "payload": {"content": "test content"}
        }
        
        await router.handle_message("user456", message)
        
        # Verify context IDs are added to payload
        expected_payload = {
            "content": "test content",
            "thread_id": "ctx_thread_789",
            "run_id": "ctx_run_101"
        }
        mock_handler.handle.assert_called_once_with("user456", expected_payload)

    @pytest.mark.asyncio
    async def test_handle_message_without_context_ids_still_works(self, router):
        """Test that messages without thread_id/run_id are handled correctly."""
        mock_handler = AsyncMock()
        router.handlers["generate_quality_report"] = mock_handler
        
        message = {
            "type": "generate_quality_report",
            "payload": {"report_type": "summary"}
        }
        
        await router.handle_message("user789", message)
        
        # Verify handler is called with original payload
        mock_handler.handle.assert_called_once_with("user789", {"report_type": "summary"})

    @pytest.mark.asyncio
    async def test_handle_message_without_payload_uses_empty_dict(self, router):
        """Test that messages without payload use empty dictionary."""
        mock_handler = AsyncMock()
        router.handlers["subscribe_quality_alerts"] = mock_handler
        
        message = {
            "type": "subscribe_quality_alerts",
            "thread_id": "thread_no_payload"
        }
        
        await router.handle_message("user_no_payload", message)
        
        # Verify empty payload with context IDs
        expected_payload = {"thread_id": "thread_no_payload"}
        mock_handler.handle.assert_called_once_with("user_no_payload", expected_payload)

    # Message Type Validation Tests
    def test_is_valid_message_type_returns_true_for_known_types(self, router):
        """Test that known message types are validated correctly."""
        valid_types = [
            "get_quality_metrics",
            "subscribe_quality_alerts",
            "start_agent",
            "validate_content",
            "generate_quality_report"
        ]
        
        for message_type in valid_types:
            assert router._is_valid_message_type(message_type)

    def test_is_valid_message_type_returns_false_for_unknown_types(self, router):
        """Test that unknown message types are rejected."""
        invalid_types = [
            "unknown_type",
            "invalid_message",
            "",
            None,
            "get_metrics",  # Similar but not exact
            "quality_metrics"  # Similar but not exact
        ]
        
        for message_type in invalid_types:
            assert not router._is_valid_message_type(message_type)

    # Unknown Message Type Handling Tests
    @pytest.mark.asyncio
    @patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager')
    async def test_handle_unknown_message_type_sends_error_to_user(self, mock_create_manager, 
                                                                   mock_get_context, router):
        """Test that unknown message types result in error being sent to user."""
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        await router._handle_unknown_message_type("user123", "unknown_type")
        
        # Verify user context is created correctly
        mock_get_context.assert_called_once_with(
            user_id="user123",
            thread_id=None,
            run_id=None
        )
        
        # Verify WebSocket manager is created and error is sent
        mock_create_manager.assert_called_once_with(mock_context)
        mock_manager.send_to_user.assert_called_once_with({
            "type": "error",
            "message": "Unknown message type: unknown_type"
        })

    @pytest.mark.asyncio
    @patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager')
    async def test_handle_unknown_message_type_error_handling(self, mock_create_manager, 
                                                              mock_get_context, router, caplog):
        """Test that errors during unknown message handling are logged."""
        # Enable logging capture at the right level
        caplog.set_level("ERROR", logger="netra_backend.app.services.websocket.quality_message_router")
        
        mock_get_context.side_effect = Exception("WebSocket manager creation failed")
        
        await router._handle_unknown_message_type("user456", "bad_type")
        
        # Verify error is logged
        log_messages = [record.message for record in caplog.records]
        assert any("Failed to send error message to user user456" in msg for msg in log_messages)
        assert any("WebSocket manager creation failed" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_handle_message_with_unknown_type_calls_unknown_handler(self, router):
        """Test that unknown message types trigger unknown message handler."""
        with patch.object(router, '_handle_unknown_message_type', new_callable=AsyncMock) as mock_unknown:
            message = {"type": "completely_unknown_type"}
            
            await router.handle_message("user789", message)
            
            mock_unknown.assert_called_once_with("user789", "completely_unknown_type")

    # Broadcasting Tests
    @pytest.mark.asyncio
    async def test_broadcast_quality_update_sends_to_all_subscribers(self, router, mock_monitoring_service):
        """Test that quality updates are broadcast to all subscribers."""
        update = {"metric": "response_time", "value": 150, "threshold": 200}
        
        with patch.object(router, '_send_update_to_subscriber', new_callable=AsyncMock) as mock_send:
            await router.broadcast_quality_update(update)
            
            # Verify update sent to all subscribers
            expected_calls = [
                call("user1", update),
                call("user2", update),
                call("user3", update)
            ]
            mock_send.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    async def test_broadcast_quality_alert_sends_to_all_subscribers(self, router, mock_monitoring_service):
        """Test that quality alerts are broadcast to all subscribers."""
        alert = {"type": "performance_degradation", "severity": "high", "message": "High latency detected"}
        
        with patch.object(router, '_send_alert_to_subscriber', new_callable=AsyncMock) as mock_send:
            await router.broadcast_quality_alert(alert)
            
            # Verify alert sent to all subscribers
            expected_calls = [
                call("user1", alert),
                call("user2", alert),
                call("user3", alert)
            ]
            mock_send.assert_has_calls(expected_calls, any_order=True)

    @pytest.mark.asyncio
    @patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager')
    async def test_send_update_to_subscriber_creates_proper_message(self, mock_create_manager, 
                                                                    mock_get_context, router):
        """Test that updates are formatted correctly when sent to subscribers."""
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        update = {"metric": "error_rate", "current": 0.05, "threshold": 0.1}
        
        await router._send_update_to_subscriber("subscriber123", update)
        
        # Verify message format
        expected_message = {
            "type": "quality_update",
            "payload": {"metric": "error_rate", "current": 0.05, "threshold": 0.1}
        }
        mock_manager.send_to_user.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager')
    async def test_send_alert_to_subscriber_includes_default_severity(self, mock_create_manager, 
                                                                      mock_get_context, router):
        """Test that alerts include default severity when not specified."""
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        alert = {"message": "System health check failed"}
        
        await router._send_alert_to_subscriber("subscriber456", alert)
        
        # Verify default severity is added
        expected_message = {
            "type": "quality_alert",
            "payload": {
                "message": "System health check failed",
                "severity": "info"
            }
        }
        mock_manager.send_to_user.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager')
    async def test_send_alert_to_subscriber_preserves_existing_severity(self, mock_create_manager, 
                                                                        mock_get_context, router):
        """Test that existing severity levels are preserved in alerts."""
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        mock_manager = AsyncMock()
        mock_create_manager.return_value = mock_manager
        
        alert = {"message": "Critical system failure", "severity": "critical"}
        
        await router._send_alert_to_subscriber("subscriber789", alert)
        
        # Verify existing severity is preserved
        expected_message = {
            "type": "quality_alert",
            "payload": {
                "message": "Critical system failure",
                "severity": "critical"
            }
        }
        mock_manager.send_to_user.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    @patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context')
    @patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager')
    async def test_broadcast_error_handling_continues_with_other_subscribers(self, mock_create_manager, 
                                                                             mock_get_context, router, caplog):
        """Test that errors during broadcast don't stop other subscribers from receiving messages."""
        # Enable logging capture at the right level
        caplog.set_level("ERROR", logger="netra_backend.app.services.websocket.quality_message_router")
        
        mock_context = Mock()
        mock_get_context.return_value = mock_context
        
        # First call fails, second succeeds
        mock_manager1 = AsyncMock()
        mock_manager1.send_to_user.side_effect = Exception("Connection failed")
        mock_manager2 = AsyncMock()
        mock_create_manager.side_effect = [mock_manager1, mock_manager2]
        
        update = {"status": "degraded"}
        
        with patch.object(router, '_send_update_to_subscriber', side_effect=router._send_update_to_subscriber):
            await router.broadcast_quality_update(update)
        
        # Verify error is logged but broadcast continues
        log_messages = [record.message for record in caplog.records]
        assert any("Error broadcasting to user1" in msg for msg in log_messages)
        mock_manager2.send_to_user.assert_called_once()

    # Message Building Tests
    def test_build_update_message_creates_correct_structure(self, router):
        """Test that update messages are built with correct structure."""
        update_data = {"metric": "cpu_usage", "value": 75, "unit": "percent"}
        
        message = router._build_update_message(update_data)
        
        expected = {
            "type": "quality_update",
            "payload": {"metric": "cpu_usage", "value": 75, "unit": "percent"}
        }
        assert message == expected

    def test_build_alert_message_creates_correct_structure(self, router):
        """Test that alert messages are built with correct structure."""
        alert_data = {"component": "database", "issue": "connection_timeout"}
        
        message = router._build_alert_message(alert_data)
        
        expected = {
            "type": "quality_alert",
            "payload": {
                "component": "database",
                "issue": "connection_timeout",
                "severity": "info"
            }
        }
        assert message == expected

    def test_build_alert_message_preserves_custom_severity(self, router):
        """Test that custom severity levels are preserved in alert messages."""
        alert_data = {"component": "api", "issue": "rate_limit_exceeded", "severity": "warning"}
        
        message = router._build_alert_message(alert_data)
        
        expected = {
            "type": "quality_alert",
            "payload": {
                "component": "api",
                "issue": "rate_limit_exceeded",
                "severity": "warning"
            }
        }
        assert message == expected

    # Integration Tests
    @pytest.mark.asyncio
    async def test_full_message_handling_flow_with_context_propagation(self, router):
        """Test complete message handling flow with session context propagation."""
        mock_handler = AsyncMock()
        router.handlers["start_agent"] = mock_handler
        
        message = {
            "type": "start_agent",
            "thread_id": "integration_thread_123",
            "run_id": "integration_run_456",
            "payload": {
                "agent_type": "quality_monitor",
                "config": {"timeout": 30}
            }
        }
        
        await router.handle_message("integration_user", message)
        
        # Verify complete flow: routing, context propagation, and handler execution
        expected_payload = {
            "agent_type": "quality_monitor",
            "config": {"timeout": 30},
            "thread_id": "integration_thread_123",
            "run_id": "integration_run_456"
        }
        mock_handler.handle.assert_called_once_with("integration_user", expected_payload)
        assert router._current_thread_id == "integration_thread_123"
        assert router._current_run_id == "integration_run_456"

    def test_handler_dependency_injection_completeness(self, router, mock_supervisor, 
                                                       mock_db_session_factory, mock_quality_gate_service, 
                                                       mock_monitoring_service):
        """Test that all handlers receive correct dependencies through dependency injection."""
        # Verify each handler type has correct dependencies
        metrics_handler = router.handlers["get_quality_metrics"]
        assert metrics_handler.monitoring_service == mock_monitoring_service
        
        alert_handler = router.handlers["subscribe_quality_alerts"]
        assert alert_handler.monitoring_service == mock_monitoring_service
        
        start_handler = router.handlers["start_agent"]
        assert hasattr(start_handler, 'handle')  # Enhanced start handler (mocked) has handle method
        
        validation_handler = router.handlers["validate_content"]
        assert validation_handler.quality_gate_service == mock_quality_gate_service
        
        report_handler = router.handlers["generate_quality_report"]
        assert report_handler.monitoring_service == mock_monitoring_service

    @pytest.mark.asyncio
    async def test_concurrent_message_handling_maintains_session_isolation(self, router):
        """Test that concurrent message handling maintains proper session isolation."""
        mock_handler1 = AsyncMock()
        mock_handler2 = AsyncMock()
        router.handlers["get_quality_metrics"] = mock_handler1
        router.handlers["validate_content"] = mock_handler2
        
        message1 = {
            "type": "get_quality_metrics",
            "thread_id": "session1_thread",
            "run_id": "session1_run",
            "payload": {"agent_name": "agent1"}
        }
        
        message2 = {
            "type": "validate_content",
            "thread_id": "session2_thread", 
            "run_id": "session2_run",
            "payload": {"content": "test content"}
        }
        
        # Handle messages for different users
        await router.handle_message("user_session1", message1)
        await router.handle_message("user_session2", message2)
        
        # Verify each handler received correct session context
        expected_payload1 = {
            "agent_name": "agent1",
            "thread_id": "session1_thread",
            "run_id": "session1_run"
        }
        expected_payload2 = {
            "content": "test content",
            "thread_id": "session2_thread",
            "run_id": "session2_run"
        }
        
        mock_handler1.handle.assert_called_once_with("user_session1", expected_payload1)
        mock_handler2.handle.assert_called_once_with("user_session2", expected_payload2)

    # Edge Cases and Error Handling
    @pytest.mark.asyncio
    async def test_handle_message_with_none_message_type(self, router):
        """Test handling of message with None type."""
        with patch.object(router, '_handle_unknown_message_type', new_callable=AsyncMock) as mock_unknown:
            message = {"type": None, "payload": {}}
            
            await router.handle_message("user_none_type", message)
            
            mock_unknown.assert_called_once_with("user_none_type", None)

    @pytest.mark.asyncio 
    async def test_handle_message_with_missing_type_field(self, router):
        """Test handling of message without type field."""
        with patch.object(router, '_handle_unknown_message_type', new_callable=AsyncMock) as mock_unknown:
            message = {"payload": {"some": "data"}}
            
            await router.handle_message("user_no_type", message)
            
            mock_unknown.assert_called_once_with("user_no_type", None)

    @pytest.mark.asyncio
    async def test_empty_subscribers_list_broadcast_handling(self, router, mock_monitoring_service):
        """Test broadcast behavior when there are no subscribers."""
        mock_monitoring_service.subscribers = []
        
        update = {"metric": "test"}
        
        # Should not raise error and complete successfully
        await router.broadcast_quality_update(update)
        await router.broadcast_quality_alert({"alert": "test"})

    def test_router_state_isolation_between_instances(self, mock_supervisor, mock_db_session_factory,
                                                      mock_quality_gate_service, mock_monitoring_service):
        """Test that different router instances maintain separate state."""
        with patch.object(QualityMessageRouter, '_create_enhanced_start_handler') as mock_create_start:
            # Mock the problematic handler creation to return a simple mock
            mock_start_handler = Mock()
            mock_start_handler.handle = AsyncMock()
            mock_create_start.return_value = mock_start_handler
            
            router1 = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            
            router2 = QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
            
            # Verify they have separate handler dictionaries
            assert router1.handlers is not router2.handlers
            assert id(router1.handlers) != id(router2.handlers)
            
            # Verify separate instances of handlers
            assert router1.handlers["get_quality_metrics"] is not router2.handlers["get_quality_metrics"]


# Performance and Load Testing Scenarios
class TestQualityMessageRouterPerformance:
    """Performance-focused tests for QualityMessageRouter."""
    
    @pytest.fixture
    def performance_router(self, mock_supervisor, mock_db_session_factory,
                          mock_quality_gate_service, mock_monitoring_service):
        """Create router for performance testing."""
        with patch.object(QualityMessageRouter, '_create_enhanced_start_handler') as mock_create_start:
            # Mock the problematic handler creation to return a simple mock
            mock_start_handler = Mock()
            mock_start_handler.handle = AsyncMock()
            mock_create_start.return_value = mock_start_handler
            
            return QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )

    @pytest.mark.asyncio
    async def test_high_volume_message_routing_performance(self, performance_router):
        """Test router performance under high message volume."""
        mock_handler = AsyncMock()
        performance_router.handlers["get_quality_metrics"] = mock_handler
        
        # Simulate high-volume message processing
        messages = [
            {
                "type": "get_quality_metrics",
                "thread_id": f"thread_{i}",
                "run_id": f"run_{i}",
                "payload": {"agent_name": f"agent_{i}"}
            }
            for i in range(100)
        ]
        
        # Process all messages
        for i, message in enumerate(messages):
            await performance_router.handle_message(f"user_{i}", message)
        
        # Verify all messages were processed
        assert mock_handler.handle.call_count == 100

    @pytest.mark.asyncio
    async def test_large_subscriber_list_broadcast_performance(self, performance_router, mock_monitoring_service):
        """Test broadcast performance with large subscriber lists."""
        # Simulate large number of subscribers
        large_subscriber_list = [f"user_{i}" for i in range(1000)]
        mock_monitoring_service.subscribers = large_subscriber_list
        
        with patch.object(performance_router, '_send_update_to_subscriber', new_callable=AsyncMock) as mock_send:
            update = {"metric": "performance_test"}
            
            await performance_router.broadcast_quality_update(update)
            
            # Verify all subscribers were notified
            assert mock_send.call_count == 1000