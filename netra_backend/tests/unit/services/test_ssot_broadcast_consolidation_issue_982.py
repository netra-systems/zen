"""Unit tests for Issue #982 SSOT Broadcast Consolidation - Adapter Delegation Validation

These tests validate that the three broadcasting functions correctly delegate to the
SSOT WebSocketBroadcastService while maintaining backward compatibility:

1. WebSocketEventRouter.broadcast_to_user() (line 198)
2. UserScopedWebSocketEventRouter.broadcast_to_user() (line 234)
3. broadcast_user_event() (line 607)

The tests prove the adapter pattern is working correctly by mocking the SSOT service
and verifying that calls are properly delegated with correct parameters.

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Golden Path reliability and code consolidation
- Value Impact: Ensures WebSocket broadcasting works consistently across all usage patterns
- Revenue Impact: Protects $500K+ ARR through reliable event delivery
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter, broadcast_user_event
from netra_backend.app.services.websocket_broadcast_service import BroadcastResult
from netra_backend.app.core.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID


class TestSSotBroadcastAdapterDelegation:
    """Test suite for validating adapter delegation to SSOT WebSocket broadcast service."""

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create a mock WebSocket manager for testing."""
        mock_manager = AsyncMock()
        mock_manager.send_to_user = AsyncMock(return_value=True)
        mock_manager.get_user_connections = AsyncMock(return_value=['conn1', 'conn2'])
        return mock_manager

    @pytest.fixture
    def mock_user_context(self):
        """Create a mock UserExecutionContext for testing."""
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = "test_user_123"
        mock_context.request_id = "req_456"
        mock_context.thread_id = "thread_789"
        mock_context.get_scoped_key = Mock(return_value="scoped_key_test")
        return mock_context

    @pytest.fixture
    def mock_broadcast_result(self):
        """Create a mock BroadcastResult for SSOT service responses."""
        return BroadcastResult(
            user_id="test_user_123",
            connections_attempted=2,
            successful_sends=2,
            event_type="test_event",
            timestamp=datetime.now(timezone.utc),
            errors=[]
        )

    @pytest.fixture
    def sample_event(self):
        """Sample event payload for testing."""
        return {
            'type': 'test_event',
            'data': {'message': 'test message'},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    @pytest.mark.asyncio
    async def test_websocket_event_router_adapter_delegation(self, mock_websocket_manager, mock_broadcast_result, sample_event):
        """Test that WebSocketEventRouter.broadcast_to_user() delegates to SSOT service correctly.

        This validates the adapter at line 198 of websocket_event_router.py
        """
        # Arrange
        router = WebSocketEventRouter(mock_websocket_manager)

        with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
            mock_broadcast_service = AsyncMock()
            mock_broadcast_service.broadcast_to_user = AsyncMock(return_value=mock_broadcast_result)
            mock_create_service.return_value = mock_broadcast_service

            # Act
            result = await router.broadcast_to_user("test_user_123", sample_event)

            # Assert - Verify SSOT service creation
            mock_create_service.assert_called_once_with(mock_websocket_manager)

            # Assert - Verify delegation to SSOT service
            mock_broadcast_service.broadcast_to_user.assert_called_once_with("test_user_123", sample_event)

            # Assert - Verify return value conversion (BroadcastResult.successful_sends -> int)
            assert result == mock_broadcast_result.successful_sends
            assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_websocket_event_router_adapter_no_manager_error(self, sample_event):
        """Test WebSocketEventRouter adapter handles missing WebSocket manager gracefully."""
        # Arrange
        router = WebSocketEventRouter(None)  # No WebSocket manager

        # Act
        result = await router.broadcast_to_user("test_user_123", sample_event)

        # Assert
        assert result == 0  # Should return 0 for no manager

    @pytest.mark.asyncio
    async def test_websocket_event_router_adapter_fallback_on_error(self, mock_websocket_manager, sample_event):
        """Test WebSocketEventRouter adapter falls back to legacy implementation on SSOT failure."""
        # Arrange
        router = WebSocketEventRouter(mock_websocket_manager)

        with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
            # Simulate SSOT service creation failure
            mock_create_service.side_effect = Exception("SSOT service creation failed")

            with patch.object(router, '_legacy_broadcast_to_user', new_callable=AsyncMock) as mock_legacy:
                mock_legacy.return_value = 1

                # Act
                result = await router.broadcast_to_user("test_user_123", sample_event)

                # Assert - Verify fallback was called
                mock_legacy.assert_called_once_with("test_user_123", sample_event)
                assert result == 1

    @pytest.mark.asyncio
    async def test_user_scoped_router_adapter_delegation(self, mock_websocket_manager, mock_user_context, mock_broadcast_result, sample_event):
        """Test that UserScopedWebSocketEventRouter.broadcast_to_user() delegates to SSOT service correctly.

        This validates the adapter at line 234 of user_scoped_websocket_event_router.py
        """
        # Arrange
        router = UserScopedWebSocketEventRouter(mock_user_context, mock_websocket_manager)

        with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
            mock_broadcast_service = AsyncMock()
            mock_broadcast_service.broadcast_to_user = AsyncMock(return_value=mock_broadcast_result)
            mock_create_service.return_value = mock_broadcast_service

            # Act
            result = await router.broadcast_to_user(sample_event)

            # Assert - Verify SSOT service creation
            mock_create_service.assert_called_once_with(mock_websocket_manager)

            # Assert - Verify delegation with enriched event (user context added)
            call_args = mock_broadcast_service.broadcast_to_user.call_args
            assert call_args[0][0] == mock_user_context.user_id

            # Verify event was enriched with user context
            enriched_event = call_args[0][1]
            assert enriched_event['user_id'] == mock_user_context.user_id
            assert enriched_event['request_id'] == mock_user_context.request_id
            assert enriched_event['type'] == sample_event['type']  # Original event preserved

            # Assert - Verify return value conversion
            assert result == mock_broadcast_result.successful_sends
            assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_user_scoped_router_adapter_no_manager_error(self, mock_user_context, sample_event):
        """Test UserScopedWebSocketEventRouter adapter handles missing WebSocket manager gracefully."""
        # Arrange
        router = UserScopedWebSocketEventRouter(mock_user_context, None)  # No WebSocket manager

        # Act
        result = await router.broadcast_to_user(sample_event)

        # Assert
        assert result == 0  # Should return 0 for no manager

    @pytest.mark.asyncio
    async def test_user_scoped_router_adapter_fallback_on_error(self, mock_websocket_manager, mock_user_context, sample_event):
        """Test UserScopedWebSocketEventRouter adapter falls back to legacy implementation on SSOT failure."""
        # Arrange
        router = UserScopedWebSocketEventRouter(mock_user_context, mock_websocket_manager)

        with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
            # Simulate SSOT service creation failure
            mock_create_service.side_effect = Exception("SSOT service creation failed")

            with patch.object(router.registry.router, 'broadcast_to_user', new_callable=AsyncMock) as mock_legacy:
                mock_legacy.return_value = 1

                # Act
                result = await router.broadcast_to_user(sample_event)

                # Assert - Verify fallback was called
                mock_legacy.assert_called_once()
                assert result == 1

    @pytest.mark.asyncio
    async def test_broadcast_user_event_function_delegation(self, mock_user_context, mock_broadcast_result, sample_event):
        """Test that broadcast_user_event() function delegates to SSOT service correctly.

        This validates the adapter at line 607 of user_scoped_websocket_event_router.py
        """
        # Arrange - Mock WebSocketManager creation
        mock_websocket_manager = AsyncMock()

        with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager') as mock_ws_class:
            mock_ws_class.return_value = mock_websocket_manager

            with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
                mock_broadcast_service = AsyncMock()
                mock_broadcast_service.broadcast_to_user = AsyncMock(return_value=mock_broadcast_result)
                mock_create_service.return_value = mock_broadcast_service

                # Act
                result = await broadcast_user_event(sample_event, mock_user_context)

                # Assert - Verify WebSocket manager creation with user context
                mock_ws_class.assert_called_once_with(user_context=mock_user_context)

                # Assert - Verify SSOT service creation
                mock_create_service.assert_called_once_with(mock_websocket_manager)

                # Assert - Verify delegation with enriched event
                call_args = mock_broadcast_service.broadcast_to_user.call_args
                assert call_args[0][0] == mock_user_context.user_id

                # Verify event was enriched with full user context
                enriched_event = call_args[0][1]
                assert enriched_event['user_id'] == mock_user_context.user_id
                assert enriched_event['request_id'] == mock_user_context.request_id
                assert enriched_event['thread_id'] == mock_user_context.thread_id
                assert enriched_event['type'] == sample_event['type']  # Original event preserved

                # Assert - Verify return value conversion
                assert result == mock_broadcast_result.successful_sends
                assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_broadcast_user_event_function_manager_creation_failure(self, mock_user_context, sample_event):
        """Test broadcast_user_event() handles WebSocketManager creation failure gracefully."""
        # Arrange - Mock WebSocketManager creation failure
        with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager') as mock_ws_class:
            mock_ws_class.side_effect = Exception("WebSocket manager creation failed")

            # Act
            result = await broadcast_user_event(sample_event, mock_user_context)

            # Assert
            assert result == 0  # Should return 0 for manager creation failure

    @pytest.mark.asyncio
    async def test_broadcast_user_event_function_fallback_on_error(self, mock_user_context, sample_event):
        """Test broadcast_user_event() falls back to legacy implementation on SSOT failure."""
        # Arrange
        mock_websocket_manager = AsyncMock()

        with patch('netra_backend.app.websocket_core.websocket_manager.WebSocketManager') as mock_ws_class:
            mock_ws_class.return_value = mock_websocket_manager

            with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
                # Simulate SSOT service creation failure
                mock_create_service.side_effect = Exception("SSOT service creation failed")

                with patch('netra_backend.app.services.user_scoped_websocket_event_router._legacy_broadcast_user_event', new_callable=AsyncMock) as mock_legacy:
                    mock_legacy.return_value = 1

                    # Act
                    result = await broadcast_user_event(sample_event, mock_user_context)

                    # Assert - Verify fallback was called
                    mock_legacy.assert_called_once_with(sample_event, mock_user_context)
                    assert result == 1

    def test_function_signature_compatibility(self):
        """Test that all adapter functions maintain their original signatures for backward compatibility."""
        # Arrange - Use inspection to verify function signatures
        import inspect
        from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
        from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter, broadcast_user_event

        # Act & Assert - WebSocketEventRouter.broadcast_to_user
        router_method = WebSocketEventRouter.broadcast_to_user
        router_sig = inspect.signature(router_method)
        assert len(router_sig.parameters) == 3  # self, user_id, event
        assert 'user_id' in router_sig.parameters
        assert 'event' in router_sig.parameters

        # Act & Assert - UserScopedWebSocketEventRouter.broadcast_to_user
        user_scoped_method = UserScopedWebSocketEventRouter.broadcast_to_user
        user_scoped_sig = inspect.signature(user_scoped_method)
        assert len(user_scoped_sig.parameters) == 2  # self, event
        assert 'event' in user_scoped_sig.parameters

        # Act & Assert - broadcast_user_event function
        function_sig = inspect.signature(broadcast_user_event)
        assert len(function_sig.parameters) == 2  # event, user_context
        assert 'event' in function_sig.parameters
        assert 'user_context' in function_sig.parameters

    @pytest.mark.asyncio
    async def test_parameter_passing_validation(self, mock_websocket_manager, mock_user_context, mock_broadcast_result):
        """Test that parameters are passed correctly from adapters to SSOT service."""
        # Arrange
        test_event = {
            'type': 'parameter_test',
            'data': {'test': 'parameter_validation'},
            'custom_field': 'custom_value'
        }

        # Test WebSocketEventRouter parameter passing
        router = WebSocketEventRouter(mock_websocket_manager)

        with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
            mock_broadcast_service = AsyncMock()
            mock_broadcast_service.broadcast_to_user = AsyncMock(return_value=mock_broadcast_result)
            mock_create_service.return_value = mock_broadcast_service

            # Act
            await router.broadcast_to_user("param_user_123", test_event)

            # Assert - Verify exact parameters passed
            call_args = mock_broadcast_service.broadcast_to_user.call_args
            assert call_args[0][0] == "param_user_123"  # user_id
            assert call_args[0][1] == test_event  # event (unmodified)
            assert call_args[0][1]['custom_field'] == 'custom_value'  # Custom fields preserved

    @pytest.mark.asyncio
    async def test_error_handling_and_logging_validation(self, mock_websocket_manager, mock_user_context, sample_event):
        """Test that adapter error handling and logging work correctly."""
        import logging

        # Test WebSocketEventRouter error handling
        router = WebSocketEventRouter(mock_websocket_manager)

        with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
            # Simulate SSOT service method failure
            mock_broadcast_service = AsyncMock()
            mock_broadcast_service.broadcast_to_user = AsyncMock(side_effect=Exception("Broadcast failed"))
            mock_create_service.return_value = mock_broadcast_service

            with patch.object(router, '_legacy_broadcast_to_user', new_callable=AsyncMock) as mock_legacy:
                mock_legacy.return_value = 1

                # Mock the logger to capture log calls
                with patch('netra_backend.app.services.websocket_event_router.logger') as mock_logger:
                    # Act
                    result = await router.broadcast_to_user("error_user", sample_event)

                    # Assert
                    assert result == 1  # Fallback return value

                    # Verify error was logged
                    mock_logger.error.assert_called()
                    error_call_args = mock_logger.error.call_args[0][0]
                    assert "ADAPTER FAILURE" in error_call_args

                    mock_legacy.assert_called_once()

    @pytest.mark.asyncio
    async def test_return_value_type_consistency(self, mock_websocket_manager, mock_user_context, sample_event):
        """Test that all adapters return consistent integer types for backward compatibility."""
        # Create different BroadcastResult scenarios
        test_cases = [
            BroadcastResult(user_id="user1", connections_attempted=2, successful_sends=2, event_type="test"),
            BroadcastResult(user_id="user2", connections_attempted=1, successful_sends=0, event_type="test"),
            BroadcastResult(user_id="user3", connections_attempted=0, successful_sends=0, event_type="test")
        ]

        for broadcast_result in test_cases:
            # Test WebSocketEventRouter
            router = WebSocketEventRouter(mock_websocket_manager)

            with patch('netra_backend.app.services.websocket_broadcast_service.create_broadcast_service') as mock_create_service:
                mock_broadcast_service = AsyncMock()
                mock_broadcast_service.broadcast_to_user = AsyncMock(return_value=broadcast_result)
                mock_create_service.return_value = mock_broadcast_service

                result = await router.broadcast_to_user("test_user", sample_event)

                # Assert return type and value
                assert isinstance(result, int)
                assert result == broadcast_result.successful_sends