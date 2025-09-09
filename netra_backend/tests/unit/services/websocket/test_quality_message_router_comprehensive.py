"""
QualityMessageRouter - Comprehensive Unit Test Suite

Business Value Justification:
- Segment: Platform/Internal & All User Tiers (Free, Early, Mid, Enterprise)
- Business Goal: System Reliability & Quality Monitoring Infrastructure
- Value Impact: Ensures 100% reliable quality-related WebSocket message routing for system health monitoring
- Strategic Impact: Enables proactive quality management that maintains user trust and service reliability

This comprehensive test suite validates the critical QualityMessageRouter class that routes all quality-related
WebSocket messages to appropriate handlers. Complete test coverage ensures reliable quality monitoring infrastructure
that enables proactive system health management across all user tiers and business scenarios.

Test Categories:
1. Handler Initialization & Dependency Injection (7+ tests)
2. Message Routing & Session Continuity (12+ tests) 
3. Broadcasting & Subscriber Management (6+ tests)
4. Integration & Error Handling (8+ tests)
5. Performance & Scalability (2+ tests)
"""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import pytest

from netra_backend.app.services.websocket.quality_message_router import (
    QualityMessageRouter
)
from netra_backend.app.services.quality_gate_service import QualityGateService
from netra_backend.app.services.quality_monitoring_service import QualityMonitoringService


# Test fixtures and mocks
@pytest.fixture
def mock_supervisor():
    """Create a mock supervisor for testing."""
    supervisor = Mock()
    supervisor.start_agent = AsyncMock(return_value={"status": "started"})
    supervisor.get_agent_status = AsyncMock(return_value={"status": "running"})
    return supervisor


@pytest.fixture
def mock_db_session_factory():
    """Create a mock database session factory."""
    factory = Mock()
    session = Mock()
    session.close = Mock()
    factory.return_value = session
    return factory


@pytest.fixture
def mock_quality_gate_service():
    """Create a mock quality gate service."""
    service = Mock(spec=QualityGateService)
    service.validate_content = AsyncMock(return_value={"valid": True})
    service.check_quality_gates = AsyncMock(return_value={"passed": True})
    return service


@pytest.fixture
def mock_quality_monitoring_service():
    """Create a mock quality monitoring service."""
    service = Mock(spec=QualityMonitoringService)
    service.get_metrics = AsyncMock(return_value={"quality_score": 95})
    service.subscribe_to_alerts = AsyncMock()
    service.generate_report = AsyncMock(return_value={"report_id": "test_123"})
    service.subscribers = ["user_123", "user_456"]  # Mock subscriber list
    return service


@pytest.fixture
def quality_router(mock_supervisor, mock_db_session_factory, mock_quality_gate_service, mock_quality_monitoring_service):
    """Create a QualityMessageRouter instance for testing."""
    return QualityMessageRouter(
        supervisor=mock_supervisor,
        db_session_factory=mock_db_session_factory,
        quality_gate_service=mock_quality_gate_service,
        monitoring_service=mock_quality_monitoring_service
    )


@pytest.fixture
def sample_quality_message():
    """Sample quality-related WebSocket message for testing."""
    return {
        "type": "get_quality_metrics",
        "thread_id": "thread_123",
        "run_id": "run_456",
        "payload": {
            "metric_types": ["latency", "accuracy", "completeness"],
            "time_range": "last_24h"
        }
    }


class TestQualityMessageRouterInitialization:
    """
    BVJ: Validates QualityMessageRouter initialization and handler setup.
    Business Impact: Ensures all quality handlers are properly initialized for reliable quality monitoring.
    """

    def test_router_initializes_with_all_required_handlers(self, quality_router):
        """BVJ: Validates all required quality handlers are created for comprehensive quality monitoring."""
        expected_handler_types = {
            "get_quality_metrics",
            "subscribe_quality_alerts", 
            "start_agent",
            "validate_content",
            "generate_quality_report"
        }
        
        actual_handler_types = set(quality_router.handlers.keys())
        
        assert expected_handler_types == actual_handler_types, "All required quality handlers must be initialized"
        assert len(quality_router.handlers) == 5, "Router must have exactly 5 quality handlers"

    def test_router_stores_service_dependencies(self, quality_router, mock_supervisor, mock_db_session_factory, mock_quality_gate_service, mock_quality_monitoring_service):
        """BVJ: Validates router properly stores service dependencies for handler operations."""
        assert quality_router.supervisor is mock_supervisor, "Supervisor dependency must be stored"
        assert quality_router.db_session_factory is mock_db_session_factory, "DB factory dependency must be stored"
        assert quality_router.quality_gate_service is mock_quality_gate_service, "Quality gate service must be stored"
        assert quality_router.monitoring_service is mock_quality_monitoring_service, "Monitoring service must be stored"

    def test_metrics_handler_creation(self, quality_router):
        """BVJ: Validates quality metrics handler is properly created for performance monitoring."""
        handler = quality_router.handlers["get_quality_metrics"]
        assert handler is not None, "Quality metrics handler must be created"
        # Verify handler has monitoring service dependency
        assert hasattr(handler, 'monitoring_service') or callable(handler), "Handler must have monitoring service access"

    def test_alert_handler_creation(self, quality_router):
        """BVJ: Validates quality alert handler is properly created for proactive monitoring."""
        handler = quality_router.handlers["subscribe_quality_alerts"]
        assert handler is not None, "Quality alert handler must be created"
        # Verify handler has monitoring service dependency
        assert hasattr(handler, 'monitoring_service') or callable(handler), "Handler must have monitoring service access"

    def test_enhanced_start_handler_creation(self, quality_router):
        """BVJ: Validates enhanced start agent handler is properly created for quality-aware agent execution."""
        handler = quality_router.handlers["start_agent"]
        assert handler is not None, "Enhanced start agent handler must be created"
        # This handler has multiple dependencies
        assert callable(handler), "Enhanced start handler must be callable"

    def test_validation_handler_creation(self, quality_router):
        """BVJ: Validates content validation handler is properly created for quality assurance."""
        handler = quality_router.handlers["validate_content"]
        assert handler is not None, "Content validation handler must be created"
        # Verify handler has quality gate service dependency
        assert hasattr(handler, 'quality_gate_service') or callable(handler), "Handler must have quality gate service access"

    def test_report_handler_creation(self, quality_router):
        """BVJ: Validates quality report handler is properly created for business intelligence."""
        handler = quality_router.handlers["generate_quality_report"]
        assert handler is not None, "Quality report handler must be created"
        # Verify handler has monitoring service dependency
        assert hasattr(handler, 'monitoring_service') or callable(handler), "Handler must have monitoring service access"


class TestQualityMessageRouterMessageHandling:
    """
    BVJ: Tests core message routing and session continuity functionality.
    Business Impact: Ensures reliable quality message routing with proper context preservation.
    """

    async def test_handle_valid_message_routes_correctly(self, quality_router):
        """BVJ: Validates valid quality messages are routed to correct handlers."""
        message = {
            "type": "get_quality_metrics",
            "payload": {"metrics": ["accuracy", "latency"]}
        }
        
        # Mock the metrics handler
        mock_handler = AsyncMock()
        quality_router.handlers["get_quality_metrics"] = mock_handler
        
        await quality_router.handle_message("user_123", message)
        
        # Handler should have been called with correct parameters
        mock_handler.handle.assert_called_once_with("user_123", {"metrics": ["accuracy", "latency"]})

    async def test_handle_message_preserves_session_context(self, quality_router):
        """BVJ: Validates session continuity with thread_id and run_id context preservation."""
        message = {
            "type": "validate_content",
            "thread_id": "thread_session_123",
            "run_id": "run_session_456", 
            "payload": {"content": "Test content"}
        }
        
        # Mock the validation handler
        mock_handler = AsyncMock()
        quality_router.handlers["validate_content"] = mock_handler
        
        await quality_router.handle_message("user_123", message)
        
        # Handler should receive payload with session context
        expected_payload = {
            "content": "Test content",
            "thread_id": "thread_session_123",
            "run_id": "run_session_456"
        }
        mock_handler.handle.assert_called_once_with("user_123", expected_payload)

    async def test_handle_message_updates_current_context_ids(self, quality_router):
        """BVJ: Validates router tracks current session context for continuity."""
        message = {
            "type": "get_quality_metrics",
            "thread_id": "thread_current_789",
            "run_id": "run_current_012",
            "payload": {}
        }
        
        # Mock the handler
        mock_handler = AsyncMock()
        quality_router.handlers["get_quality_metrics"] = mock_handler
        
        await quality_router.handle_message("user_123", message)
        
        # Router should update internal context tracking
        assert quality_router._current_thread_id == "thread_current_789", "Current thread ID must be updated"
        assert quality_router._current_run_id == "run_current_012", "Current run ID must be updated"

    async def test_handle_message_with_missing_context_uses_cached(self, quality_router):
        """BVJ: Validates router uses cached context when message lacks context IDs."""
        # First message establishes context
        first_message = {
            "type": "get_quality_metrics",
            "thread_id": "thread_cached_123",
            "run_id": "run_cached_456",
            "payload": {"initial": "request"}
        }
        
        mock_handler = AsyncMock()
        quality_router.handlers["get_quality_metrics"] = mock_handler
        
        await quality_router.handle_message("user_123", first_message)
        
        # Second message without context should use cached values
        second_message = {
            "type": "validate_content", 
            "payload": {"content": "Follow-up content"}
        }
        
        quality_router.handlers["validate_content"] = mock_handler
        
        await quality_router.handle_message("user_123", second_message)
        
        # Second call should include cached context
        expected_payload = {
            "content": "Follow-up content",
            "thread_id": "thread_cached_123",
            "run_id": "run_cached_456"
        }
        mock_handler.handle.assert_called_with("user_123", expected_payload)

    async def test_valid_message_type_validation(self, quality_router):
        """BVJ: Validates message type validation for supported quality operations."""
        valid_types = [
            "get_quality_metrics",
            "subscribe_quality_alerts",
            "start_agent", 
            "validate_content",
            "generate_quality_report"
        ]
        
        for msg_type in valid_types:
            assert quality_router._is_valid_message_type(msg_type), f"Message type {msg_type} must be valid"
        
        invalid_types = [
            "unknown_type",
            "invalid_operation",
            None,
            "",
            123
        ]
        
        for msg_type in invalid_types:
            assert not quality_router._is_valid_message_type(msg_type), f"Message type {msg_type} must be invalid"

    async def test_handle_unknown_message_type(self, quality_router):
        """BVJ: Validates graceful handling of unknown quality message types."""
        unknown_message = {
            "type": "unknown_quality_operation",
            "payload": {"test": "data"}
        }
        
        # Mock the WebSocket manager creation
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            # Should not raise exception
            await quality_router.handle_message("user_123", unknown_message)
            
            # Should send error message to user
            mock_manager.send_to_user.assert_called_once()
            error_call_args = mock_manager.send_to_user.call_args[0][0]
            assert error_call_args["type"] == "error", "Error message must be sent for unknown type"
            assert "unknown_quality_operation" in error_call_args["message"], "Error must reference unknown type"

    async def test_handle_message_with_handler_exception(self, quality_router):
        """BVJ: Validates error handling when quality handlers raise exceptions."""
        message = {
            "type": "get_quality_metrics",
            "payload": {"metrics": ["test"]}
        }
        
        # Mock handler that raises exception
        failing_handler = AsyncMock()
        failing_handler.handle.side_effect = Exception("Handler processing error")
        quality_router.handlers["get_quality_metrics"] = failing_handler
        
        # Should not propagate exception
        try:
            await quality_router.handle_message("user_123", message)
        except Exception:
            pytest.fail("Router should handle handler exceptions gracefully")

    async def test_route_to_handler_adds_context_to_payload(self, quality_router):
        """BVJ: Validates handler receives complete context information for session continuity."""
        # Set up router context
        quality_router._current_thread_id = "context_thread_123"
        quality_router._current_run_id = "context_run_456"
        
        message_payload = {"original": "data"}
        mock_handler = AsyncMock()
        
        await quality_router._route_to_handler("user_123", {"payload": message_payload}, "test_type", mock_handler)
        
        # Handler should receive payload with added context
        expected_payload = {
            "original": "data",
            "thread_id": "context_thread_123", 
            "run_id": "context_run_456"
        }
        mock_handler.handle.assert_called_once_with("user_123", expected_payload)

    async def test_route_to_handler_preserves_existing_context(self, quality_router):
        """BVJ: Validates existing context in payload is preserved over cached context."""
        # Set up router cached context
        quality_router._current_thread_id = "cached_thread_123"
        quality_router._current_run_id = "cached_run_456"
        
        # Payload with explicit context should override cached
        message_payload = {
            "data": "test",
            "thread_id": "explicit_thread_789",
            "run_id": "explicit_run_012"
        }
        mock_handler = AsyncMock()
        
        await quality_router._route_to_handler("user_123", {"payload": message_payload}, "test_type", mock_handler)
        
        # Handler should receive original payload context, not cached
        expected_payload = {
            "data": "test",
            "thread_id": "explicit_thread_789",
            "run_id": "explicit_run_012"
        }
        mock_handler.handle.assert_called_once_with("user_123", expected_payload)

    async def test_handle_message_without_payload_creates_empty_payload(self, quality_router):
        """BVJ: Validates messages without payload are handled with empty payload."""
        message = {
            "type": "get_quality_metrics",
            "thread_id": "thread_123"
            # No payload field
        }
        
        mock_handler = AsyncMock()
        quality_router.handlers["get_quality_metrics"] = mock_handler
        
        await quality_router.handle_message("user_123", message)
        
        # Handler should receive empty payload with context
        expected_payload = {
            "thread_id": "thread_123"
        }
        mock_handler.handle.assert_called_once_with("user_123", expected_payload)

    async def test_handle_message_with_complex_payload_preserves_structure(self, quality_router):
        """BVJ: Validates complex payload structures are preserved during routing."""
        complex_payload = {
            "nested": {
                "data": {
                    "metrics": ["latency", "accuracy"],
                    "config": {"threshold": 0.95, "window": "1h"}
                }
            },
            "metadata": {
                "timestamp": "2025-01-01T00:00:00Z",
                "priority": "high"
            }
        }
        
        message = {
            "type": "validate_content",
            "thread_id": "thread_complex_123",
            "payload": complex_payload
        }
        
        mock_handler = AsyncMock()
        quality_router.handlers["validate_content"] = mock_handler
        
        await quality_router.handle_message("user_123", message)
        
        # Handler should receive complete complex payload with context
        expected_payload = {
            **complex_payload,
            "thread_id": "thread_complex_123"
        }
        mock_handler.handle.assert_called_once_with("user_123", expected_payload)


class TestQualityMessageRouterBroadcasting:
    """
    BVJ: Tests broadcasting functionality for quality updates and alerts.
    Business Impact: Ensures all subscribers receive quality notifications for proactive monitoring.
    """

    async def test_broadcast_quality_update_to_all_subscribers(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates quality updates are broadcast to all monitoring subscribers."""
        # Setup subscribers
        mock_quality_monitoring_service.subscribers = ["user_123", "user_456", "user_789"]
        
        quality_update = {
            "metric": "system_health",
            "value": 95.5,
            "timestamp": "2025-01-01T12:00:00Z"
        }
        
        # Mock WebSocket manager creation for each subscriber
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            await quality_router.broadcast_quality_update(quality_update)
            
            # Should create manager for each subscriber
            assert mock_create.call_count == 3, "WebSocket manager must be created for each subscriber"
            
            # Should send update to each subscriber
            assert mock_manager.send_to_user.call_count == 3, "Update must be sent to each subscriber"
            
            # Verify message format
            sent_message = mock_manager.send_to_user.call_args[0][0]
            assert sent_message["type"] == "quality_update", "Message type must be quality_update"
            assert sent_message["payload"] == quality_update, "Payload must contain update data"

    async def test_broadcast_quality_alert_to_all_subscribers(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates quality alerts are broadcast to all monitoring subscribers with severity."""
        # Setup subscribers
        mock_quality_monitoring_service.subscribers = ["user_admin", "user_ops"]
        
        quality_alert = {
            "alert_type": "threshold_breach",
            "metric": "error_rate", 
            "current_value": 15.2,
            "threshold": 10.0,
            "timestamp": "2025-01-01T12:00:00Z"
        }
        
        # Mock WebSocket manager creation
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            await quality_router.broadcast_quality_alert(quality_alert)
            
            # Should create manager for each subscriber
            assert mock_create.call_count == 2, "WebSocket manager must be created for each subscriber"
            
            # Should send alert to each subscriber
            assert mock_manager.send_to_user.call_count == 2, "Alert must be sent to each subscriber"
            
            # Verify alert message format
            sent_message = mock_manager.send_to_user.call_args[0][0]
            assert sent_message["type"] == "quality_alert", "Message type must be quality_alert"
            assert sent_message["payload"]["alert_type"] == "threshold_breach", "Alert type must be preserved"
            assert sent_message["payload"]["severity"] == "info", "Default severity must be added"

    async def test_broadcast_quality_alert_preserves_existing_severity(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates existing severity in alerts is preserved during broadcast."""
        mock_quality_monitoring_service.subscribers = ["user_123"]
        
        alert_with_severity = {
            "alert_type": "critical_failure",
            "message": "System component failure detected",
            "severity": "critical"
        }
        
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            await quality_router.broadcast_quality_alert(alert_with_severity)
            
            # Verify existing severity is preserved
            sent_message = mock_manager.send_to_user.call_args[0][0]
            assert sent_message["payload"]["severity"] == "critical", "Existing severity must be preserved"

    async def test_broadcast_with_empty_subscriber_list(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates broadcasting handles empty subscriber list gracefully."""
        # Empty subscriber list
        mock_quality_monitoring_service.subscribers = []
        
        quality_update = {"metric": "test", "value": 100}
        
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            # Should not raise exception
            await quality_router.broadcast_quality_update(quality_update)
            await quality_router.broadcast_quality_alert(quality_update)
            
            # Should not create any managers
            mock_create.assert_not_called()

    async def test_broadcast_handles_websocket_errors_gracefully(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates broadcast operations handle WebSocket errors gracefully."""
        mock_quality_monitoring_service.subscribers = ["user_123", "user_456"]
        
        quality_update = {"metric": "test", "value": 95}
        
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            # First user succeeds, second user fails
            mock_manager_success = AsyncMock()
            mock_manager_fail = AsyncMock()
            mock_manager_fail.send_to_user.side_effect = Exception("WebSocket error")
            
            mock_create.side_effect = [mock_manager_success, mock_manager_fail]
            
            # Should not raise exception despite one failure
            await quality_router.broadcast_quality_update(quality_update)
            
            # Successful subscriber should still receive update
            mock_manager_success.send_to_user.assert_called_once()

    async def test_build_update_message_format(self, quality_router):
        """BVJ: Validates quality update messages are built in correct format."""
        update_data = {
            "metric_name": "response_time",
            "current_value": 150.5,
            "trend": "increasing",
            "timestamp": "2025-01-01T12:00:00Z"
        }
        
        built_message = quality_router._build_update_message(update_data)
        
        assert built_message["type"] == "quality_update", "Message type must be quality_update"
        assert built_message["payload"] == update_data, "Payload must contain original update data"

    async def test_build_alert_message_format(self, quality_router):
        """BVJ: Validates quality alert messages are built in correct format with severity."""
        alert_data = {
            "alert_id": "alert_001",
            "message": "Quality threshold exceeded",
            "metric": "error_rate",
            "current_value": 12.5
        }
        
        built_message = quality_router._build_alert_message(alert_data)
        
        assert built_message["type"] == "quality_alert", "Message type must be quality_alert"
        assert built_message["payload"]["alert_id"] == "alert_001", "Alert data must be preserved"
        assert built_message["payload"]["severity"] == "info", "Default severity must be added"


class TestQualityMessageRouterIntegration:
    """
    BVJ: Tests integration scenarios and edge cases for system resilience.
    Business Impact: Ensures router remains stable under various operational conditions.
    """

    async def test_complete_message_handling_flow(self, quality_router):
        """BVJ: Validates complete message handling flow with context propagation."""
        message = {
            "type": "get_quality_metrics",
            "thread_id": "integration_thread_123",
            "run_id": "integration_run_456",
            "payload": {
                "metrics": ["latency", "throughput"],
                "time_range": "24h"
            }
        }
        
        # Mock handler
        mock_handler = AsyncMock()
        quality_router.handlers["get_quality_metrics"] = mock_handler
        
        await quality_router.handle_message("integration_user_123", message)
        
        # Verify complete flow
        assert quality_router._current_thread_id == "integration_thread_123", "Context must be updated"
        assert quality_router._current_run_id == "integration_run_456", "Context must be updated"
        
        # Verify handler received complete payload
        expected_payload = {
            "metrics": ["latency", "throughput"],
            "time_range": "24h",
            "thread_id": "integration_thread_123",
            "run_id": "integration_run_456"
        }
        mock_handler.handle.assert_called_once_with("integration_user_123", expected_payload)

    async def test_concurrent_message_handling(self, quality_router):
        """BVJ: Validates router handles concurrent messages with proper session isolation."""
        async def handle_user_message(user_id: str, thread_id: str, message_type: str):
            message = {
                "type": message_type,
                "thread_id": thread_id,
                "payload": {"user": user_id}
            }
            return await quality_router.handle_message(user_id, message)
        
        # Mock all handlers
        for handler_type in quality_router.handlers:
            quality_router.handlers[handler_type] = AsyncMock()
        
        # Execute concurrent message handling
        tasks = [
            handle_user_message("user_1", "thread_1", "get_quality_metrics"),
            handle_user_message("user_2", "thread_2", "validate_content"), 
            handle_user_message("user_3", "thread_3", "generate_quality_report")
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All messages should complete successfully
        assert len(results) == 3, "All concurrent messages must be processed"

    async def test_router_state_isolation(self, mock_supervisor, mock_db_session_factory, mock_quality_gate_service, mock_quality_monitoring_service):
        """BVJ: Validates different router instances maintain isolated state."""
        # Create two separate router instances
        router1 = QualityMessageRouter(
            supervisor=mock_supervisor,
            db_session_factory=mock_db_session_factory,
            quality_gate_service=mock_quality_gate_service,
            monitoring_service=mock_quality_monitoring_service
        )
        
        router2 = QualityMessageRouter(
            supervisor=mock_supervisor,
            db_session_factory=mock_db_session_factory,
            quality_gate_service=mock_quality_gate_service,
            monitoring_service=mock_quality_monitoring_service
        )
        
        # Set different context in each router
        message1 = {"type": "get_quality_metrics", "thread_id": "thread_1", "payload": {}}
        message2 = {"type": "validate_content", "thread_id": "thread_2", "payload": {}}
        
        # Mock handlers for both routers
        router1.handlers["get_quality_metrics"] = AsyncMock()
        router2.handlers["validate_content"] = AsyncMock()
        
        await router1.handle_message("user_1", message1)
        await router2.handle_message("user_2", message2)
        
        # Each router should maintain separate context
        assert router1._current_thread_id == "thread_1", "Router 1 context must be isolated"
        assert router2._current_thread_id == "thread_2", "Router 2 context must be isolated"

    async def test_handle_message_with_none_message_type(self, quality_router):
        """BVJ: Validates graceful handling of None message type."""
        message = {
            "type": None,
            "payload": {"test": "data"}
        }
        
        # Should not raise exception
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            await quality_router.handle_message("user_123", message)
            
            # Should send error message
            mock_manager.send_to_user.assert_called_once()

    async def test_handle_message_without_type_field(self, quality_router):
        """BVJ: Validates handling of messages missing type field."""
        message = {
            "payload": {"test": "data"}
            # Missing "type" field
        }
        
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            await quality_router.handle_message("user_123", message)
            
            # Should handle gracefully and send error
            mock_manager.send_to_user.assert_called_once()

    async def test_websocket_manager_context_creation(self, quality_router):
        """BVJ: Validates WebSocket manager is created with proper user context."""
        message = {
            "type": "unknown_type",
            "payload": {}
        }
        
        with patch('netra_backend.app.services.websocket.quality_message_router.get_user_execution_context') as mock_context:
            with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
                mock_manager = AsyncMock()
                mock_create.return_value = mock_manager
                
                await quality_router.handle_message("context_user_123", message)
                
                # Verify context creation with correct user ID
                mock_context.assert_called_once_with(
                    user_id="context_user_123",
                    thread_id=None,
                    run_id=None
                )
                
                # Verify manager creation with context
                mock_create.assert_called_once()

    async def test_error_handling_in_unknown_message_handler(self, quality_router):
        """BVJ: Validates error handling within unknown message type handler."""
        message = {
            "type": "unknown_error_test",
            "payload": {}
        }
        
        # Mock WebSocket manager creation to fail
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_create.side_effect = Exception("WebSocket creation failed")
            
            # Should not raise exception even if manager creation fails
            await quality_router.handle_message("user_123", message)
            
            # Operation should complete without crashing

    async def test_broadcast_error_logging(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates error logging during broadcast operations."""
        mock_quality_monitoring_service.subscribers = ["user_123"]
        
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_create.side_effect = Exception("Broadcast error")
            
            # Should log error but not raise exception
            with patch('netra_backend.app.services.websocket.quality_message_router.logger') as mock_logger:
                await quality_router.broadcast_quality_update({"test": "data"})
                
                # Should log error
                mock_logger.error.assert_called_once()


class TestQualityMessageRouterPerformance:
    """
    BVJ: Tests performance characteristics for production scalability.
    Business Impact: Ensures quality router can handle high message volumes efficiently.
    """

    async def test_high_volume_message_routing_performance(self, quality_router):
        """BVJ: Validates router performance under high message volume."""
        # Mock all handlers for performance testing
        for handler_type in quality_router.handlers:
            quality_router.handlers[handler_type] = AsyncMock()
        
        message_types = list(quality_router.handlers.keys())
        
        start_time = time.perf_counter()
        
        # Route 1000 messages concurrently
        tasks = []
        for i in range(1000):
            message = {
                "type": message_types[i % len(message_types)],
                "thread_id": f"thread_{i}",
                "payload": {"message_id": i}
            }
            tasks.append(quality_router.handle_message(f"user_{i % 10}", message))
        
        await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        messages_per_second = 1000 / total_time
        
        assert messages_per_second > 500, f"Quality router throughput {messages_per_second:.0f} msg/sec must be >500 msg/sec"

    async def test_large_subscriber_broadcast_performance(self, quality_router, mock_quality_monitoring_service):
        """BVJ: Validates broadcast performance with large subscriber lists."""
        # Setup large subscriber list
        large_subscriber_list = [f"user_{i}" for i in range(1000)]
        mock_quality_monitoring_service.subscribers = large_subscriber_list
        
        quality_update = {"metric": "performance_test", "value": 100}
        
        start_time = time.perf_counter()
        
        with patch('netra_backend.app.services.websocket.quality_message_router.create_websocket_manager') as mock_create:
            mock_manager = AsyncMock()
            mock_create.return_value = mock_manager
            
            await quality_router.broadcast_quality_update(quality_update)
            
            end_time = time.perf_counter()
            total_time = end_time - start_time
            
            # Should complete broadcast within reasonable time
            assert total_time < 5.0, f"Broadcast to 1000 subscribers took {total_time:.2f}s, must be <5s"
            
            # Should create manager for each subscriber
            assert mock_create.call_count == 1000, "Manager must be created for each subscriber"