"""
Test User-Friendly Error Message Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure error messages flow correctly through the system
- Value Impact: Users see consistent, helpful error messages across all channels
- Strategic Impact: Professional error handling reduces support burden and improves user trust

This test module validates that user-friendly error messages are properly
integrated into the WebSocket event system and flow correctly from backend to frontend.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.real_services_test_fixtures import real_services_fixture

from netra_backend.app.services.user_friendly_error_mapper import (
    UserFriendlyErrorMapper,
    ErrorCategory,
    UserFriendlyErrorMessage,
    ErrorSeverity
)
from netra_backend.app.websocket_core.error_recovery_handler import (
    ErrorType,
    WebSocketErrorContext
)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


class TestUserFriendlyErrorIntegration(SSotAsyncTestCase):
    """Test integration of user-friendly error messages with WebSocket system."""

    async def setup_method(self, method=None):
        """Set up test fixtures."""
        await super().setup_method(method)
        self.error_mapper = UserFriendlyErrorMapper()
        self.websocket_manager = None  # Will be set up in test with real services

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_error_message_flow(self, real_services_fixture):
        """Test that WebSocket errors flow through to user-friendly messages."""
        # This should FAIL until WebSocket integration is implemented

        # Set up real WebSocket manager
        self.websocket_manager = UnifiedWebSocketManager(
            config=real_services_fixture['config']
        )

        # Simulate a rate limit error in WebSocket
        error_context = WebSocketErrorContext(
            error_type=ErrorType.RATE_LIMIT_EXCEEDED,
            connection_id="test_connection_123",
            user_id="test_user_456",
            error_message="Rate limit exceeded: 100 requests per minute",
            timestamp=datetime.now(timezone.utc)
        )

        # The WebSocket manager should use UserFriendlyErrorMapper
        with patch.object(self.websocket_manager, 'send_error_message') as mock_send:
            await self.websocket_manager.handle_error_with_user_friendly_message(error_context)

            # Should have sent a user-friendly error message
            mock_send.assert_called_once()

            # Extract the message that was sent
            call_args = mock_send.call_args
            connection_id = call_args[0][0]
            error_payload = call_args[0][1]

            assert connection_id == "test_connection_123"
            assert isinstance(error_payload, dict)

            # Should contain user-friendly message fields
            assert 'type' in error_payload
            assert error_payload['type'] == 'user_friendly_error'
            assert 'user_message' in error_payload
            assert 'category' in error_payload
            assert 'severity' in error_payload
            assert 'actionable_advice' in error_payload

            # Should not contain technical details
            assert 'requests per minute' not in error_payload['user_message']
            assert 'rate limit' in error_payload['user_message'].lower()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_execution_error_integration(self, real_services_fixture):
        """Test agent execution errors are mapped to user-friendly messages."""
        # This should FAIL until agent integration is implemented

        from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine

        # Set up execution engine with error mapper
        execution_engine = ExecutionEngine(
            websocket_manager=self.websocket_manager,
            error_mapper=self.error_mapper
        )

        # Simulate agent execution failure
        error_context = WebSocketErrorContext(
            error_type=ErrorType.SERVICE_UNAVAILABLE,
            connection_id="agent_connection_789",
            user_id="agent_user_101",
            error_message="Agent execution failed: LLM service timeout after 30s",
            timestamp=datetime.now(timezone.utc),
            context_data={'agent_type': 'cost_optimizer', 'step': 'analysis'}
        )

        # Should send user-friendly error via WebSocket
        sent_messages = []

        async def mock_send_error(connection_id, error_payload):
            sent_messages.append((connection_id, error_payload))

        with patch.object(execution_engine.websocket_manager, 'send_error_message', mock_send_error):
            await execution_engine.handle_execution_error(error_context)

        # Should have sent exactly one error message
        assert len(sent_messages) == 1

        connection_id, error_payload = sent_messages[0]
        assert connection_id == "agent_connection_789"

        # Should be user-friendly format
        assert error_payload['type'] == 'user_friendly_error'
        assert 'processing' in error_payload['user_message'].lower() or 'agent' in error_payload['user_message'].lower()
        assert 'LLM service' not in error_payload['user_message']
        assert '30s' not in error_payload['user_message']

        # Should have actionable advice
        assert len(error_payload['actionable_advice']) > 0
        assert any('try again' in advice.lower() for advice in error_payload['actionable_advice'])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_authentication_error_websocket_integration(self, real_services_fixture):
        """Test authentication errors are sent as user-friendly messages via WebSocket."""
        # This should FAIL until auth integration is implemented

        from netra_backend.app.websocket_core.auth import WebSocketAuthenticator

        # Set up authenticator with error mapper
        authenticator = WebSocketAuthenticator(
            error_mapper=self.error_mapper
        )

        # Simulate authentication failure
        connection_id = "auth_test_connection"
        invalid_token = "invalid.jwt.token"

        sent_messages = []

        async def mock_send_auth_error(conn_id, error_payload):
            sent_messages.append((conn_id, error_payload))

        with patch.object(authenticator, 'send_authentication_error', mock_send_auth_error):
            result = await authenticator.authenticate_with_user_friendly_errors(
                connection_id, invalid_token
            )

        # Authentication should fail
        assert result is False

        # Should have sent user-friendly error
        assert len(sent_messages) == 1
        connection_id, error_payload = sent_messages[0]

        # Should hide technical JWT details
        assert 'JWT' not in error_payload['user_message']
        assert 'token' not in error_payload['user_message']
        assert 'signature' not in error_payload['user_message']

        # Should have user-friendly auth message
        assert 'authentication' in error_payload['user_message'].lower() or 'sign in' in error_payload['user_message'].lower()

        # Should suggest actionable steps
        assert any('sign in' in advice.lower() or 'login' in advice.lower() for advice in error_payload['actionable_advice'])

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_consistency_across_services(self, real_services_fixture):
        """Test that error messages are consistent across different services."""
        # This should FAIL until cross-service consistency is implemented

        # Create identical error contexts from different services
        base_context = {
            'error_type': ErrorType.RATE_LIMIT_EXCEEDED,
            'error_message': 'Rate limit exceeded: 100 requests per minute',
            'timestamp': datetime.now(timezone.utc)
        }

        # From WebSocket service
        websocket_context = WebSocketErrorContext(
            connection_id="ws_connection",
            user_id="user_123",
            **base_context
        )

        # From agent execution service
        agent_context = WebSocketErrorContext(
            connection_id="agent_connection",
            user_id="user_123",
            **base_context
        )

        # Map both errors
        websocket_message = self.error_mapper.map_error(websocket_context.__dict__)
        agent_message = self.error_mapper.map_error(agent_context.__dict__)

        # Should produce identical user-friendly messages
        assert websocket_message.user_message == agent_message.user_message
        assert websocket_message.category == agent_message.category
        assert websocket_message.severity == agent_message.severity
        assert websocket_message.actionable_advice == agent_message.actionable_advice

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_localization_ready(self, real_services_fixture):
        """Test that error messages support future localization."""
        # This should FAIL until localization support is implemented

        error_context = {
            'error_type': ErrorType.NETWORK_ERROR,
            'error_message': 'Connection lost',
            'timestamp': datetime.now(timezone.utc),
            'user_locale': 'en-US'  # Future localization support
        }

        result = self.error_mapper.map_error(error_context)

        # Should have localization metadata
        assert hasattr(result, 'locale')
        assert result.locale == 'en-US'

        # Should have message keys for translation
        assert hasattr(result, 'message_key')
        assert isinstance(result.message_key, str)
        assert len(result.message_key) > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_message_metrics_integration(self, real_services_fixture):
        """Test that error messages are properly tracked in metrics."""
        # This should FAIL until metrics integration is implemented

        from netra_backend.app.services.monitoring.error_metrics_collector import ErrorMetricsCollector

        metrics_collector = ErrorMetricsCollector()

        # Set up error mapper with metrics integration
        error_mapper_with_metrics = UserFriendlyErrorMapper(
            metrics_collector=metrics_collector
        )

        error_context = {
            'error_type': ErrorType.AUTHENTICATION_FAILED,
            'error_message': 'Authentication failed',
            'timestamp': datetime.now(timezone.utc),
            'user_id': 'metrics_test_user'
        }

        # Map error (should record metrics)
        result = error_mapper_with_metrics.map_error(error_context)

        # Should have recorded metrics
        metrics = metrics_collector.get_error_mapping_metrics()

        assert 'user_friendly_errors_generated' in metrics
        assert metrics['user_friendly_errors_generated'] > 0

        assert 'error_categories' in metrics
        assert ErrorCategory.AUTHENTICATION.name in metrics['error_categories']

        assert 'error_severities' in metrics
        assert ErrorSeverity.HIGH.name in metrics['error_severities']

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_frontend_error_payload_structure(self, real_services_fixture):
        """Test that WebSocket error payloads match frontend expectations."""
        # This should FAIL until frontend integration is complete

        error_context = WebSocketErrorContext(
            error_type=ErrorType.MESSAGE_DELIVERY_FAILED,
            connection_id="frontend_test_connection",
            user_id="frontend_test_user",
            error_message="WebSocket message delivery failed",
            timestamp=datetime.now(timezone.utc)
        )

        # Convert to WebSocket payload
        websocket_payload = self.websocket_manager.create_user_friendly_error_payload(error_context)

        # Should match frontend ErrorPayload interface
        expected_fields = {
            'type', 'user_message', 'error_type', 'category', 'severity',
            'actionable_advice', 'timestamp', 'technical_reference_id'
        }

        assert all(field in websocket_payload for field in expected_fields)

        # Should have correct types for frontend
        assert isinstance(websocket_payload['user_message'], str)
        assert isinstance(websocket_payload['error_type'], str)
        assert isinstance(websocket_payload['category'], str)
        assert isinstance(websocket_payload['severity'], str)
        assert isinstance(websocket_payload['actionable_advice'], list)
        assert isinstance(websocket_payload['timestamp'], str)  # ISO format
        assert isinstance(websocket_payload['technical_reference_id'], str)

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_error_recovery_with_user_friendly_messages(self, real_services_fixture):
        """Test that error recovery includes user-friendly progress messages."""
        # This should FAIL until recovery integration is implemented

        from netra_backend.app.websocket_core.error_recovery_handler import WebSocketErrorRecoveryHandler

        # Set up recovery handler with user-friendly messaging
        recovery_handler = WebSocketErrorRecoveryHandler(
            config=real_services_fixture['config'],
            websocket_manager=self.websocket_manager,
            message_buffer=Mock(),
            error_mapper=self.error_mapper
        )

        error_context = WebSocketErrorContext(
            error_type=ErrorType.CONNECTION_LOST,
            connection_id="recovery_test_connection",
            user_id="recovery_test_user",
            error_message="Connection lost",
            timestamp=datetime.now(timezone.utc)
        )

        sent_messages = []

        async def mock_send_message(connection_id, message):
            sent_messages.append((connection_id, message))

        with patch.object(self.websocket_manager, 'send_message', mock_send_message):
            recovery_result = await recovery_handler.handle_error_with_user_updates(error_context)

        # Should have sent user-friendly messages during recovery
        assert len(sent_messages) >= 2  # Initial error + recovery status

        # First message should be user-friendly error
        error_message = sent_messages[0][1]
        assert error_message['type'] == 'user_friendly_error'
        assert 'connection' in error_message['user_message'].lower()

        # Subsequent messages should be recovery updates
        recovery_message = sent_messages[1][1]
        assert recovery_message['type'] == 'recovery_update'
        assert 'reconnecting' in recovery_message['user_message'].lower()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_performance_under_high_error_load(self, real_services_fixture):
        """Test error mapping performance under high load."""
        # This should FAIL until performance optimizations are implemented

        import time

        # Create many error contexts
        error_contexts = []
        for i in range(100):
            error_contexts.append(WebSocketErrorContext(
                error_type=ErrorType.RATE_LIMIT_EXCEEDED if i % 2 == 0 else ErrorType.AUTHENTICATION_FAILED,
                connection_id=f"perf_test_connection_{i}",
                user_id=f"perf_test_user_{i}",
                error_message=f"Performance test error {i}",
                timestamp=datetime.now(timezone.utc)
            ))

        # Process all errors and measure time
        start_time = time.time()

        results = []
        for context in error_contexts:
            result = self.error_mapper.map_error(context.__dict__)
            results.append(result)

        end_time = time.time()

        total_time = (end_time - start_time) * 1000  # Convert to ms
        avg_time_per_error = total_time / len(error_contexts)

        # Should process errors quickly
        assert avg_time_per_error < 10, f"Average error mapping time {avg_time_per_error}ms too slow"
        assert total_time < 500, f"Total processing time {total_time}ms too slow"

        # All results should be valid
        assert len(results) == 100
        for result in results:
            assert isinstance(result, UserFriendlyErrorMessage)
            assert len(result.user_message) > 0