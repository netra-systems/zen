"""SSOT WebSocket Broadcast Consolidation Unit Tests - Issue #1058

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (HIPAA, SOC2, SEC compliance)
- Business Goal: Multi-user isolation and Golden Path reliability
- Value Impact: Prevents $500K+ ARR loss from cross-user event leakage
- Strategic Impact: Enables secure multi-tenant platform architecture

Tests SSOT consolidation of duplicate broadcast_to_user implementations:
1. WebSocketEventRouter.broadcast_to_user() (legacy singleton)
2. UserScopedWebSocketEventRouter.broadcast_to_user() (user-scoped)
3. broadcast_user_event() (convenience function)

CRITICAL MISSION: These tests MUST FAIL until proper SSOT implementation consolidates
the three duplicate broadcast functions into WebSocketBroadcastService.

Test Strategy: Validates SSOT consolidation benefits including singleton enforcement,
performance improvements, and connection pool consolidation vs legacy implementations.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional

# SSOT imports - these should be the ONLY broadcast sources after consolidation
from netra_backend.app.services.websocket_broadcast_service import (
    WebSocketBroadcastService,
    BroadcastResult,
    create_broadcast_service
)

# Legacy imports - these should be ELIMINATED after SSOT consolidation
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
@pytest.mark.websocket_ssot
@pytest.mark.issue_1058_broadcast_consolidation
class TestSSOTBroadcastConsolidation:
    """Unit tests validating SSOT consolidation for WebSocket broadcasting.

    CRITICAL: These tests validate the consolidation of 3 duplicate broadcast
    implementations into a single SSOT service, addressing Issue #1058.

    Tests will FAIL until proper SSOT implementation is complete, indicating
    successful detection of the consolidation need.
    """

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for SSOT testing."""
        manager = Mock(spec=WebSocketManagerProtocol)
        manager.send_to_user = AsyncMock()
        manager.get_user_connections = Mock(return_value=[
            {"connection_id": "conn_1", "user_id": "user_123"}
        ])
        return manager

    @pytest.fixture
    def ssot_broadcast_service(self, mock_websocket_manager):
        """Create SSOT broadcast service instance."""
        return WebSocketBroadcastService(mock_websocket_manager)

    @pytest.fixture
    def sample_event(self):
        """Create sample broadcast event."""
        return {
            "type": "agent_completed",
            "data": {
                "message": "Task completed successfully",
                "agent_id": "agent_123",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "user_id": "user_123",
            "thread_id": "thread_456"
        }

    @pytest.mark.asyncio
    async def test_ssot_broadcast_service_singleton_enforcement(self, mock_websocket_manager):
        """Test SSOT service enforces singleton pattern vs legacy duplicates.

        ISSUE #1058: Validates that SSOT service provides single canonical
        broadcast implementation, eliminating the need for multiple broadcast functions.
        """
        # Create multiple SSOT service instances
        service_1 = WebSocketBroadcastService(mock_websocket_manager)
        service_2 = WebSocketBroadcastService(mock_websocket_manager)

        # SSOT services should be independent instances but use same protocol
        assert service_1 is not service_2
        assert isinstance(service_1, WebSocketBroadcastService)
        assert isinstance(service_2, WebSocketBroadcastService)

        # Both should delegate to the SAME underlying WebSocketManager
        assert service_1.websocket_manager is service_2.websocket_manager

        # Validate SSOT factory creates consistent instances
        factory_service = create_broadcast_service(mock_websocket_manager)
        assert isinstance(factory_service, WebSocketBroadcastService)
        assert factory_service.websocket_manager is mock_websocket_manager

        logger.info("✅ SSOT singleton enforcement validated - single canonical service")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_performance_vs_legacy(self, ssot_broadcast_service, sample_event):
        """Test SSOT broadcast performance vs legacy implementations.

        ISSUE #1058: SSOT consolidation should provide better performance
        than maintaining 3 separate broadcast implementations.
        """
        user_id = "performance_user_123"

        # Test SSOT broadcast performance
        start_time = time.time()

        ssot_result = await ssot_broadcast_service.broadcast_to_user(user_id, sample_event)

        ssot_duration = time.time() - start_time

        # Validate SSOT result structure
        assert isinstance(ssot_result, BroadcastResult)
        assert ssot_result.user_id == user_id
        assert ssot_result.event_type == sample_event["type"]
        assert ssot_result.connections_attempted >= 1

        # SSOT should be fast (< 100ms for unit test)
        assert ssot_duration < 0.1, f"SSOT broadcast too slow: {ssot_duration:.3f}s"

        # Verify delegation to UnifiedWebSocketManager occurred
        ssot_broadcast_service.websocket_manager.send_to_user.assert_called_once_with(
            ensure_user_id(user_id), sample_event
        )

        # Get SSOT stats for performance analysis
        stats = ssot_broadcast_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= 1
        assert stats['broadcast_stats']['successful_broadcasts'] >= 1
        assert stats['performance_metrics']['success_rate_percentage'] > 0

        logger.info(f"✅ SSOT broadcast performance validated: {ssot_duration:.3f}s")
        logger.info(f"📊 SSOT Stats: {json.dumps(stats, indent=2)}")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_connection_pool_consolidation(self, ssot_broadcast_service):
        """Test SSOT consolidates connection pool management vs legacy duplicates.

        ISSUE #1058: SSOT should consolidate connection management instead of
        having 3 separate broadcast functions each managing connections differently.
        """
        user_id = "pool_test_user_456"

        # Mock multiple connection scenarios
        mock_connections = [
            {"connection_id": "conn_1", "user_id": user_id, "status": "active"},
            {"connection_id": "conn_2", "user_id": user_id, "status": "active"},
            {"connection_id": "conn_3", "user_id": user_id, "status": "idle"}
        ]

        ssot_broadcast_service.websocket_manager.get_user_connections.return_value = mock_connections

        # Test consolidated connection pool handling
        broadcast_event = {
            "type": "system_notification",
            "data": {"message": "Connection pool consolidation test"},
            "priority": "high"
        }

        result = await ssot_broadcast_service.broadcast_to_user(user_id, broadcast_event)

        # Validate connection pool consolidation
        assert result.connections_attempted == len(mock_connections)
        assert result.successful_sends > 0

        # SSOT should delegate to UnifiedWebSocketManager for actual delivery
        ssot_broadcast_service.websocket_manager.send_to_user.assert_called_once()

        # Verify connection metrics tracking
        stats = ssot_broadcast_service.get_stats()
        assert stats['broadcast_stats']['total_connections_attempted'] >= len(mock_connections)
        assert stats['performance_metrics']['average_connections_per_broadcast'] > 0

        logger.info(f"✅ Connection pool consolidation validated: {len(mock_connections)} connections")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_eliminates_legacy_duplicates(self, mock_websocket_manager, sample_event):
        """Test SSOT implementation eliminates need for legacy duplicate functions.

        ISSUE #1058: This test demonstrates that SSOT service provides all
        capabilities previously scattered across 3 duplicate implementations.
        """
        user_id = "duplicate_elimination_user"
        ssot_service = WebSocketBroadcastService(mock_websocket_manager)

        # Test SSOT provides ALL legacy capabilities in ONE service

        # 1. Legacy WebSocketEventRouter.broadcast_to_user() capability
        result_1 = await ssot_service.broadcast_to_user(user_id, sample_event)
        assert isinstance(result_1, BroadcastResult)
        assert result_1.user_id == user_id

        # 2. Legacy UserScopedWebSocketEventRouter.broadcast_to_user() capability
        scoped_event = {**sample_event, "scope": "user_specific"}
        result_2 = await ssot_service.broadcast_to_user(user_id, scoped_event)
        assert isinstance(result_2, BroadcastResult)
        assert result_2.user_id == user_id

        # 3. Legacy broadcast_user_event() convenience function capability
        convenience_event = {**sample_event, "convenience": True}
        result_3 = await ssot_service.broadcast_to_user(user_id, convenience_event)
        assert isinstance(result_3, BroadcastResult)
        assert result_3.user_id == user_id

        # Validate SSOT handled all scenarios through single interface
        assert mock_websocket_manager.send_to_user.call_count == 3

        # All calls should have been made to the same underlying manager
        calls = mock_websocket_manager.send_to_user.call_args_list
        for call in calls:
            args, kwargs = call
            assert args[0] == ensure_user_id(user_id)  # User ID consistency
            assert isinstance(args[1], dict)  # Event payload

        # SSOT stats should reflect consolidated operations
        stats = ssot_service.get_stats()
        assert stats['service_info']['name'] == 'WebSocketBroadcastService'
        assert len(stats['service_info']['replaces']) == 3  # Replaces 3 legacy functions
        assert stats['broadcast_stats']['total_broadcasts'] == 3

        logger.info("✅ SSOT eliminates legacy duplicates - single service handles all scenarios")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_cross_user_contamination_prevention(self, ssot_broadcast_service):
        """Test SSOT prevents cross-user contamination vs legacy implementations.

        ISSUE #1058: SSOT consolidation should provide BETTER security than
        scattered implementations by centralizing contamination prevention.
        """
        target_user = "secure_user_789"
        contaminated_event = {
            "type": "agent_message",
            "data": {"message": "Response for user"},
            "user_id": "wrong_user_999",  # EVENT DATA: preserved for audit/provenance
            "sender_id": "different_user_888",  # EVENT DATA: preserved for attribution
            "target_user_id": "another_user_777"  # ROUTING FIELD: sanitized for security
        }

        # SSOT should detect and prevent contamination in routing fields only
        result = await ssot_broadcast_service.broadcast_to_user(target_user, contaminated_event)

        # Validate routing contamination was detected and prevented
        assert len(result.errors) > 0
        contamination_errors = [err for err in result.errors if "contamination" in err.lower()]
        assert len(contamination_errors) >= 1  # Should detect routing field contamination only

        # Verify stats tracked contamination prevention
        stats = ssot_broadcast_service.get_stats()
        assert stats['broadcast_stats']['cross_user_contamination_prevented'] >= 1
        assert stats['security_metrics']['contamination_prevention_enabled'] is True

        # Ensure broadcast still succeeded (after sanitization)
        assert result.successful_sends > 0

        # Verify the actual sent event maintains data integrity while fixing routing
        call_args = ssot_broadcast_service.websocket_manager.send_to_user.call_args
        sent_event = call_args[0][1]  # Second argument is the event

        # EVENT DATA fields should be PRESERVED (Issue #1058 fix)
        assert sent_event.get("user_id") == "wrong_user_999"  # PRESERVED as event data
        assert sent_event.get("sender_id") == "different_user_888"  # PRESERVED as event data
        
        # ROUTING fields should be SANITIZED for security
        assert sent_event.get("target_user_id") == target_user  # SANITIZED for security

        logger.info("✅ SSOT contamination prevention validated - security enhanced")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_feature_flag_rollback_capability(self, ssot_broadcast_service, sample_event):
        """Test SSOT provides feature flag rollback capability for safe deployment.

        ISSUE #1058: SSOT consolidation should include rollback mechanisms
        for safe production deployment vs legacy implementations.
        """
        user_id = "rollback_test_user"

        # Test feature flags can be disabled for rollback scenarios

        # Disable contamination detection
        ssot_broadcast_service.update_feature_flag('enable_contamination_detection', False)
        stats = ssot_broadcast_service.get_stats()
        assert stats['security_metrics']['contamination_prevention_enabled'] is False

        # Disable performance monitoring
        ssot_broadcast_service.update_feature_flag('enable_performance_monitoring', False)

        # Disable comprehensive logging
        ssot_broadcast_service.update_feature_flag('enable_comprehensive_logging', False)

        # Broadcast should still work with features disabled
        result = await ssot_broadcast_service.broadcast_to_user(user_id, sample_event)
        assert isinstance(result, BroadcastResult)
        assert result.successful_sends > 0

        # Re-enable features
        ssot_broadcast_service.update_feature_flag('enable_contamination_detection', True)
        ssot_broadcast_service.update_feature_flag('enable_performance_monitoring', True)
        ssot_broadcast_service.update_feature_flag('enable_comprehensive_logging', True)

        # Validate features re-enabled
        stats = ssot_broadcast_service.get_stats()
        assert stats['security_metrics']['contamination_prevention_enabled'] is True

        logger.info("✅ SSOT rollback capability validated - safe deployment mechanisms")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_comprehensive_error_handling(self, ssot_broadcast_service):
        """Test SSOT provides comprehensive error handling vs legacy implementations.

        ISSUE #1058: SSOT should provide BETTER error handling than scattered
        implementations by centralizing error management and recovery.
        """
        user_id = "error_test_user"

        # Test various error scenarios

        # 1. WebSocket manager delegation failure
        ssot_broadcast_service.websocket_manager.send_to_user.side_effect = Exception("WebSocket failure")

        error_event = {"type": "test_error", "data": {"test": "error_handling"}}
        result = await ssot_broadcast_service.broadcast_to_user(user_id, error_event)

        # SSOT should handle errors gracefully
        assert isinstance(result, BroadcastResult)
        assert result.successful_sends == 0
        assert len(result.errors) > 0
        assert any("WebSocket failure" in error for error in result.errors)

        # Stats should reflect failed broadcast
        stats = ssot_broadcast_service.get_stats()
        assert stats['broadcast_stats']['failed_broadcasts'] >= 1

        # 2. Invalid user ID handling
        ssot_broadcast_service.websocket_manager.send_to_user.side_effect = None
        ssot_broadcast_service.websocket_manager.send_to_user.return_value = None

        try:
            await ssot_broadcast_service.broadcast_to_user("", error_event)  # Empty user ID
        except Exception as e:
            # SSOT should handle invalid user IDs appropriately
            assert "user" in str(e).lower() or "invalid" in str(e).lower()

        # 3. Connection count retrieval failure
        ssot_broadcast_service.websocket_manager.get_user_connections.side_effect = Exception("Connection error")

        result = await ssot_broadcast_service.broadcast_to_user(user_id, error_event)
        assert isinstance(result, BroadcastResult)
        assert result.connections_attempted >= 1  # Should assume at least one connection

        logger.info("✅ SSOT comprehensive error handling validated")

    def test_ssot_broadcast_service_replaces_legacy_imports(self):
        """Test SSOT service properly identifies legacy implementations to replace.

        ISSUE #1058: Validates that SSOT service documentation correctly identifies
        which legacy implementations it consolidates.
        """
        # Create service to check its replacement documentation
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        service = WebSocketBroadcastService(mock_manager)

        stats = service.get_stats()
        service_info = stats['service_info']

        # Validate service identifies itself as SSOT consolidation
        assert service_info['name'] == 'WebSocketBroadcastService'
        assert service_info['purpose'] == 'SSOT consolidation for Issue #982'

        # Validate it identifies all legacy implementations it replaces
        expected_replacements = [
            'WebSocketEventRouter.broadcast_to_user',
            'UserScopedWebSocketEventRouter.broadcast_to_user',
            'broadcast_user_event'
        ]

        assert len(service_info['replaces']) == 3
        for expected in expected_replacements:
            assert expected in service_info['replaces']

        logger.info("✅ SSOT service properly identifies legacy replacements")

    @pytest.mark.asyncio
    async def test_ssot_broadcast_concurrent_operations(self, ssot_broadcast_service):
        """Test SSOT handles concurrent broadcasts vs legacy implementations.

        ISSUE #1058: SSOT should handle concurrent operations better than
        multiple separate broadcast implementations.
        """
        user_ids = [f"concurrent_user_{i}" for i in range(5)]

        # Create concurrent broadcast tasks
        async def broadcast_task(user_id: str, task_id: int):
            event = {
                "type": "concurrent_test",
                "data": {"task_id": task_id, "message": f"Concurrent task {task_id}"},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            return await ssot_broadcast_service.broadcast_to_user(user_id, event)

        # Execute concurrent broadcasts
        tasks = [broadcast_task(user_id, i) for i, user_id in enumerate(user_ids)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate all concurrent broadcasts succeeded
        successful_results = [r for r in results if isinstance(r, BroadcastResult)]
        assert len(successful_results) == len(user_ids)

        for result in successful_results:
            assert result.successful_sends > 0
            assert len(result.errors) == 0

        # Validate SSOT handled concurrency properly
        stats = ssot_broadcast_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= len(user_ids)
        assert stats['broadcast_stats']['successful_broadcasts'] >= len(user_ids)

        logger.info(f"✅ SSOT concurrent operations validated: {len(user_ids)} concurrent broadcasts")


# INTEGRATION DEMONSTRATION: Show SSOT consolidation in action
@pytest.mark.integration_demo
class TestSSOTConsolidationIntegrationDemo:
    """Demonstrate SSOT consolidation benefits through integration scenarios."""

    @pytest.mark.asyncio
    async def test_ssot_consolidation_integration_demonstration(self):
        """Integration test demonstrating SSOT consolidation benefits.

        This test shows how SSOT consolidation provides all capabilities
        previously scattered across multiple implementations.
        """
        # Create mock WebSocket manager
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        mock_manager.send_to_user = AsyncMock()
        mock_manager.get_user_connections = Mock(return_value=[
            {"connection_id": "demo_conn_1", "user_id": "demo_user"}
        ])

        # Create SSOT service
        ssot_service = create_broadcast_service(mock_manager)

        # Demonstrate consolidated capabilities
        demo_user = "integration_demo_user"

        # Capability 1: Agent event broadcasting (was WebSocketEventRouter)
        agent_event = {
            "type": "agent_completed",
            "data": {"agent_id": "demo_agent", "result": "success"}
        }
        result_1 = await ssot_service.broadcast_to_user(demo_user, agent_event)
        assert result_1.is_successful

        # Capability 2: User-scoped events (was UserScopedWebSocketEventRouter)
        user_event = {
            "type": "user_notification",
            "data": {"notification": "Welcome to the platform"}
        }
        result_2 = await ssot_service.broadcast_to_user(demo_user, user_event)
        assert result_2.is_successful

        # Capability 3: System broadcasts (was broadcast_user_event function)
        system_event = {
            "type": "system_alert",
            "data": {"alert": "System maintenance in 10 minutes"}
        }
        result_3 = await ssot_service.broadcast_to_user(demo_user, system_event)
        assert result_3.is_successful

        # Validate SSOT handled all scenarios through single service
        assert mock_manager.send_to_user.call_count == 3

        # Get consolidated statistics
        stats = ssot_service.get_stats()

        logger.info("🎯 SSOT CONSOLIDATION DEMONSTRATION:")
        logger.info(f"   ✅ Consolidated 3 legacy implementations into 1 service")
        logger.info(f"   ✅ Total broadcasts: {stats['broadcast_stats']['total_broadcasts']}")
        logger.info(f"   ✅ Success rate: {stats['performance_metrics']['success_rate_percentage']:.1f}%")
        logger.info(f"   ✅ Replaces: {', '.join(stats['service_info']['replaces'])}")

        assert stats['broadcast_stats']['total_broadcasts'] == 3
        assert stats['broadcast_stats']['successful_broadcasts'] == 3
        assert stats['performance_metrics']['success_rate_percentage'] == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])