"""SSOT WebSocket Event Router Integration Tests - Issue #1058 Validation

Business Value Justification (BVJ):
- Segment: Platform/All Users (Free → Enterprise)
- Business Goal: Backward compatibility and service integration
- Value Impact: Ensures existing callers work unchanged after SSOT consolidation
- Strategic Impact: Enables safe production deployment with zero disruption

Tests validate the critical integration between:
1. Legacy WebSocketEventRouter adapter methods
2. SSOT WebSocketBroadcastService delegation
3. Existing caller compatibility preservation

CRITICAL MISSION: These tests validate that the completed Issue #1058 SSOT implementation
maintains backward compatibility while providing enhanced functionality.

Test Strategy: Integration testing with real service coordination (no Docker required).
Validates the working SSOT delegation patterns and adapter method compatibility.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter
from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService, BroadcastResult
from netra_backend.app.websocket_core.websocket_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from shared.types.core_types import ensure_user_id
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.integration
@pytest.mark.websocket_ssot
@pytest.mark.issue_1058_integration
@pytest.mark.no_docker
class SSOTEventRouterIntegrationTests:
    """Integration tests validating SSOT event router delegation patterns.

    CRITICAL: These tests validate that Issue #1058 SSOT consolidation maintains
    backward compatibility through proper adapter delegation patterns.

    Tests validate working integration between legacy adapters and SSOT service.
    """

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for integration testing."""
        manager = Mock(spec=WebSocketManagerProtocol)
        manager.send_to_user = AsyncMock()
        manager.get_user_connections = Mock(return_value=[
            {'connection_id': 'integration_conn_1', 'user_id': 'integration_user_123'},
            {'connection_id': 'integration_conn_2', 'user_id': 'integration_user_123'}
        ])
        return manager

    @pytest.fixture
    def event_router(self, mock_websocket_manager):
        """Create WebSocketEventRouter with mocked dependencies."""
        router = WebSocketEventRouter()
        # Mock the unified websocket manager dependency
        with patch.object(router, '_get_websocket_manager', return_value=mock_websocket_manager):
            yield router

    @pytest.fixture
    def user_scoped_router(self, mock_websocket_manager):
        """Create UserScopedWebSocketEventRouter with mocked dependencies."""
        router = UserScopedWebSocketEventRouter()
        # Mock the websocket manager dependency
        with patch.object(router, '_get_websocket_manager', return_value=mock_websocket_manager):
            yield router

    @pytest.fixture
    def sample_agent_event(self):
        """Create sample agent completion event."""
        return {
            'type': 'agent_completed',
            'data': {
                'agent_id': 'integration_agent_456',
                'result': 'Cost analysis completed successfully',
                'savings_identified': 15000,
                'recommendations': ['Optimize instance sizes', 'Use reserved instances']
            },
            'user_id': 'event_creator_789',
            'thread_id': 'integration_thread_123',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    @pytest.mark.asyncio
    async def test_legacy_adapter_delegation(
        self,
        event_router,
        mock_websocket_manager,
        sample_agent_event
    ):
        """Test legacy WebSocketEventRouter.broadcast_to_user delegates to SSOT service.

        ISSUE #1058 VALIDATION: Validates that existing legacy method properly
        delegates to the SSOT WebSocketBroadcastService while maintaining compatibility.
        """
        target_user_id = 'legacy_adapter_user_123'

        # Mock the SSOT service delegation
        with patch('netra_backend.app.services.websocket_event_router.create_broadcast_service') as mock_factory:
            mock_ssot_service = Mock(spec=WebSocketBroadcastService)
            mock_ssot_service.broadcast_to_user = AsyncMock(return_value=BroadcastResult(
                user_id=target_user_id,
                connections_attempted=2,
                successful_sends=2,
                event_type='agent_completed',
                errors=[]
            ))
            mock_factory.return_value = mock_ssot_service

            # Execute legacy adapter method
            result = await event_router.broadcast_to_user(target_user_id, sample_agent_event)

            # Validate delegation occurred
            mock_factory.assert_called_once_with(mock_websocket_manager)
            mock_ssot_service.broadcast_to_user.assert_called_once_with(
                target_user_id,
                sample_agent_event
            )

            # Validate result compatibility
            assert isinstance(result, BroadcastResult)
            assert result.user_id == target_user_id
            assert result.event_type == 'agent_completed'
            assert result.is_successful

        logger.info('✅ Legacy adapter delegation to SSOT service validated')
        logger.info('🔄 WebSocketEventRouter.broadcast_to_user → WebSocketBroadcastService')

    @pytest.mark.asyncio
    async def test_backward_compatibility_preservation(
        self,
        event_router,
        user_scoped_router,
        mock_websocket_manager,
        sample_agent_event
    ):
        """Test backward compatibility preserved for existing callers.

        ISSUE #1058 VALIDATION: Validates that all existing calling patterns
        continue to work unchanged after SSOT consolidation.
        """
        target_user_id = 'compatibility_user_456'

        # Mock SSOT service for both routers
        with patch('netra_backend.app.services.websocket_event_router.create_broadcast_service') as mock_factory_1, \
             patch('netra_backend.app.services.user_scoped_websocket_event_router.create_broadcast_service') as mock_factory_2:

            mock_ssot_service_1 = Mock(spec=WebSocketBroadcastService)
            mock_ssot_service_1.broadcast_to_user = AsyncMock(return_value=BroadcastResult(
                user_id=target_user_id,
                connections_attempted=2,
                successful_sends=2,
                event_type='agent_completed',
                errors=[]
            ))
            mock_factory_1.return_value = mock_ssot_service_1

            mock_ssot_service_2 = Mock(spec=WebSocketBroadcastService)
            mock_ssot_service_2.broadcast_to_user = AsyncMock(return_value=BroadcastResult(
                user_id=target_user_id,
                connections_attempted=2,
                successful_sends=2,
                event_type='agent_completed',
                errors=[]
            ))
            mock_factory_2.return_value = mock_ssot_service_2

            # Test multiple calling patterns work unchanged

            # Pattern 1: WebSocketEventRouter.broadcast_to_user
            result_1 = await event_router.broadcast_to_user(target_user_id, sample_agent_event)
            assert result_1.is_successful
            assert result_1.user_id == target_user_id

            # Pattern 2: UserScopedWebSocketEventRouter.broadcast_to_user
            result_2 = await user_scoped_router.broadcast_to_user(target_user_id, sample_agent_event)
            assert result_2.is_successful
            assert result_2.user_id == target_user_id

            # Validate both patterns delegate to SSOT
            mock_ssot_service_1.broadcast_to_user.assert_called_once()
            mock_ssot_service_2.broadcast_to_user.assert_called_once()

            # Validate identical behavior despite different entry points
            call_args_1 = mock_ssot_service_1.broadcast_to_user.call_args
            call_args_2 = mock_ssot_service_2.broadcast_to_user.call_args
            assert call_args_1[0][0] == call_args_2[0][0]  # Same user_id
            assert call_args_1[0][1] == call_args_2[0][1]  # Same event

        logger.info('✅ Backward compatibility preserved for all existing calling patterns')
        logger.info('🔄 Multiple entry points → Single SSOT service')
        logger.info('📊 Patterns tested: WebSocketEventRouter, UserScopedWebSocketEventRouter')

    @pytest.mark.asyncio
    async def test_import_path_consolidation(self, mock_websocket_manager):
        """Test import path consolidation works correctly.

        ISSUE #1058 VALIDATION: Validates that import path consolidation
        provides consistent access to SSOT functionality.
        """
        target_user_id = 'import_consolidation_user_789'
        test_event = {
            'type': 'import_test',
            'data': {'test': 'import_path_consolidation'},
            'user_id': 'test_creator_123'
        }

        # Test direct SSOT service import
        from netra_backend.app.services.websocket_broadcast_service import create_broadcast_service
        direct_service = create_broadcast_service(mock_websocket_manager)
        assert isinstance(direct_service, WebSocketBroadcastService)

        # Test legacy adapter imports still work
        from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
        from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter

        legacy_router = WebSocketEventRouter()
        user_scoped_router = UserScopedWebSocketEventRouter()

        # Both legacy imports should be available
        assert hasattr(legacy_router, 'broadcast_to_user')
        assert hasattr(user_scoped_router, 'broadcast_to_user')

        # Test factory import consistency
        from netra_backend.app.services.websocket_broadcast_service import WebSocketBroadcastService as DirectService
        factory_service = create_broadcast_service(mock_websocket_manager)
        assert isinstance(factory_service, DirectService)

        logger.info('✅ Import path consolidation validated')
        logger.info('📦 Direct SSOT service import: Available')
        logger.info('🔄 Legacy adapter imports: Preserved')
        logger.info('🏭 Factory pattern import: Consistent')

    @pytest.mark.asyncio
    async def test_error_handling_consistency(
        self,
        event_router,
        user_scoped_router,
        mock_websocket_manager
    ):
        """Test error handling consistency across adapters.

        ISSUE #1058 VALIDATION: Validates that error handling remains
        consistent across all adapter methods and SSOT service.
        """
        target_user_id = 'error_handling_user_999'
        error_event = {
            'type': 'error_test',
            'data': {'test': 'error_handling_consistency'}
        }

        # Simulate WebSocket manager failure
        mock_websocket_manager.send_to_user.side_effect = Exception("WebSocket connection failed")

        with patch('netra_backend.app.services.websocket_event_router.create_broadcast_service') as mock_factory_1, \
             patch('netra_backend.app.services.user_scoped_websocket_event_router.create_broadcast_service') as mock_factory_2:

            # Create SSOT services that will experience the failure
            real_ssot_service_1 = WebSocketBroadcastService(mock_websocket_manager)
            real_ssot_service_2 = WebSocketBroadcastService(mock_websocket_manager)

            mock_factory_1.return_value = real_ssot_service_1
            mock_factory_2.return_value = real_ssot_service_2

            # Test error handling through both adapters
            result_1 = await event_router.broadcast_to_user(target_user_id, error_event)
            result_2 = await user_scoped_router.broadcast_to_user(target_user_id, error_event)

            # Both should handle errors gracefully
            assert isinstance(result_1, BroadcastResult)
            assert isinstance(result_2, BroadcastResult)

            # Both should report the failure
            assert not result_1.is_successful
            assert not result_2.is_successful

            # Both should have error information
            assert len(result_1.errors) > 0
            assert len(result_2.errors) > 0

            # Error messages should be consistent
            assert any('WebSocket' in error for error in result_1.errors)
            assert any('WebSocket' in error for error in result_2.errors)

        logger.info('✅ Error handling consistency validated across adapters')
        logger.info('🚨 Both adapters gracefully handle failures')
        logger.info('📋 Consistent error reporting maintained')

    @pytest.mark.asyncio
    async def test_service_coordination_integration(
        self,
        event_router,
        mock_websocket_manager,
        sample_agent_event
    ):
        """Test service coordination integration works end-to-end.

        ISSUE #1058 VALIDATION: Validates that the complete service
        coordination chain works properly with SSOT consolidation.
        """
        target_user_id = 'coordination_user_123'

        # Mock successful coordination chain
        mock_websocket_manager.send_to_user.return_value = None  # Successful send

        with patch('netra_backend.app.services.websocket_event_router.create_broadcast_service') as mock_factory:
            # Use real SSOT service to validate actual coordination
            real_ssot_service = WebSocketBroadcastService(mock_websocket_manager)
            mock_factory.return_value = real_ssot_service

            # Execute the complete coordination chain
            result = await event_router.broadcast_to_user(target_user_id, sample_agent_event)

            # Validate successful coordination
            assert result.is_successful
            assert result.user_id == target_user_id
            assert result.connections_attempted >= 1
            assert result.successful_sends >= 1

            # Validate the coordination chain called the WebSocket manager
            mock_websocket_manager.send_to_user.assert_called_once_with(
                ensure_user_id(target_user_id),
                sample_agent_event
            )

            # Validate statistics tracking works in coordination
            stats = real_ssot_service.get_stats()
            assert stats['broadcast_stats']['total_broadcasts'] >= 1
            assert stats['broadcast_stats']['successful_broadcasts'] >= 1

        logger.info('✅ Service coordination integration validated end-to-end')
        logger.info('🔄 Adapter → SSOT Service → WebSocket Manager')
        logger.info('📊 Statistics tracking operational in coordination chain')

    @pytest.mark.asyncio
    async def test_multi_adapter_concurrent_coordination(
        self,
        event_router,
        user_scoped_router,
        mock_websocket_manager
    ):
        """Test multiple adapters work correctly with concurrent operations.

        ISSUE #1058 VALIDATION: Validates that concurrent operations through
        different adapters coordinate properly via SSOT service.
        """
        base_user_id = 'concurrent_coordination_user'
        user_ids = [f'{base_user_id}_{i}' for i in range(3)]

        concurrent_events = [
            {
                'type': 'concurrent_test',
                'data': {'task_id': i, 'message': f'Concurrent task {i}'},
                'user_id': f'task_creator_{i}',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            for i in range(3)
        ]

        # Mock successful concurrent operations
        mock_websocket_manager.send_to_user.return_value = None

        with patch('netra_backend.app.services.websocket_event_router.create_broadcast_service') as mock_factory_1, \
             patch('netra_backend.app.services.user_scoped_websocket_event_router.create_broadcast_service') as mock_factory_2:

            # Use real SSOT services for concurrent testing
            real_ssot_service_1 = WebSocketBroadcastService(mock_websocket_manager)
            real_ssot_service_2 = WebSocketBroadcastService(mock_websocket_manager)

            mock_factory_1.return_value = real_ssot_service_1
            mock_factory_2.return_value = real_ssot_service_2

            # Execute concurrent operations through different adapters
            async def adapter_1_task(user_id: str, event: Dict[str, Any]):
                return await event_router.broadcast_to_user(user_id, event)

            async def adapter_2_task(user_id: str, event: Dict[str, Any]):
                return await user_scoped_router.broadcast_to_user(user_id, event)

            # Mix of adapter types for concurrent execution
            tasks = [
                adapter_1_task(user_ids[0], concurrent_events[0]),
                adapter_2_task(user_ids[1], concurrent_events[1]),
                adapter_1_task(user_ids[2], concurrent_events[2])
            ]

            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Validate all concurrent operations succeeded
            successful_results = [r for r in results if isinstance(r, BroadcastResult)]
            assert len(successful_results) == 3

            for i, result in enumerate(successful_results):
                assert result.is_successful
                assert result.user_id == user_ids[i]
                assert result.event_type == 'concurrent_test'

            # Validate WebSocket manager received all calls
            assert mock_websocket_manager.send_to_user.call_count == 3

            # Validate statistics from both SSOT services
            stats_1 = real_ssot_service_1.get_stats()
            stats_2 = real_ssot_service_2.get_stats()
            total_broadcasts = (
                stats_1['broadcast_stats']['total_broadcasts'] +
                stats_2['broadcast_stats']['total_broadcasts']
            )
            assert total_broadcasts == 3

        logger.info('✅ Multi-adapter concurrent coordination validated')
        logger.info(f'🚀 Concurrent operations: {len(tasks)}')
        logger.info('🔄 Multiple adapters → SSOT services → WebSocket manager')
        logger.info('📊 All operations successful with proper statistics tracking')


if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --test-file netra_backend/tests/integration/websocket_core/test_ssot_event_router_integration.py')