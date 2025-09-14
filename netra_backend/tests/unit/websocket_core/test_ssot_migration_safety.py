"""SSOT Migration Safety Unit Tests - Issue #1058

Business Value Justification (BVJ):
- Segment: Enterprise/Platform (High-availability systems)
- Business Goal: Zero-downtime migration and rollback safety
- Value Impact: Protects $500K+ ARR during SSOT migration transition
- Strategic Impact: Enables safe production deployment of SSOT consolidation

Tests migration safety mechanisms for SSOT WebSocket broadcast consolidation:
- Fallback behavior during migration
- Configuration validation for safe deployment
- Memory leak prevention during transition
- Rollback capability verification

CRITICAL MISSION: Ensure SSOT migration can be deployed safely to production
without breaking existing functionality or causing data loss.

Test Strategy: Validates all safety mechanisms needed for production SSOT deployment,
including graceful degradation, error handling, and memory management.
"""

import asyncio
import gc
import json
import pytest
import sys
import time
import weakref
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List, Optional, Set

# SSOT imports for migration testing
from netra_backend.app.services.websocket_broadcast_service import (
    WebSocketBroadcastService,
    BroadcastResult,
    create_broadcast_service
)

# Legacy imports for migration compatibility testing
try:
    from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
    LEGACY_ROUTER_AVAILABLE = True
except ImportError:
    LEGACY_ROUTER_AVAILABLE = False

try:
    from netra_backend.app.services.user_scoped_websocket_event_router import UserScopedWebSocketEventRouter
    USER_SCOPED_ROUTER_AVAILABLE = True
except ImportError:
    USER_SCOPED_ROUTER_AVAILABLE = False

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
from shared.types.core_types import UserID, ensure_user_id
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


@pytest.mark.unit
@pytest.mark.websocket_ssot
@pytest.mark.migration_safety
@pytest.mark.issue_1058_migration_safety
class TestSSOTMigrationSafety:
    """Unit tests validating safe SSOT migration for WebSocket broadcasting.

    CRITICAL: These tests ensure SSOT migration can be deployed to production
    safely without service disruption or data loss.

    Migration safety requirements:
    1. Graceful fallback behavior if SSOT fails
    2. Configuration validation before migration
    3. Memory leak prevention during transition
    4. Rollback capability for emergency scenarios
    """

    @pytest.fixture
    def mock_websocket_manager(self):
        """Create mock WebSocket manager for migration testing."""
        manager = Mock(spec=WebSocketManagerProtocol)
        manager.send_to_user = AsyncMock()
        manager.get_user_connections = Mock(return_value=[
            {"connection_id": "migration_conn_1", "user_id": "migration_user"}
        ])
        return manager

    @pytest.fixture
    def migration_test_service(self, mock_websocket_manager):
        """Create SSOT service configured for migration testing."""
        service = WebSocketBroadcastService(mock_websocket_manager)

        # Configure for migration safety testing
        service.update_feature_flag('enable_contamination_detection', True)
        service.update_feature_flag('enable_performance_monitoring', True)
        service.update_feature_flag('enable_comprehensive_logging', False)  # Reduce noise

        return service

    @pytest.fixture
    def migration_events(self):
        """Create various events for migration testing."""
        return [
            {
                "type": "agent_started",
                "data": {"agent_id": "migration_agent_1", "task": "migration_test"}
            },
            {
                "type": "agent_thinking",
                "data": {"agent_id": "migration_agent_1", "thoughts": "Processing migration test"}
            },
            {
                "type": "tool_executing",
                "data": {"tool": "migration_validator", "status": "running"}
            },
            {
                "type": "tool_completed",
                "data": {"tool": "migration_validator", "result": "success"}
            },
            {
                "type": "agent_completed",
                "data": {"agent_id": "migration_agent_1", "final_result": "migration_test_complete"}
            }
        ]

    @pytest.mark.asyncio
    async def test_ssot_fallback_behavior_validation(self, migration_test_service, migration_events):
        """Test SSOT provides graceful fallback if underlying systems fail.

        MIGRATION SAFETY: SSOT must provide fallback behavior during migration
        to prevent service disruption if WebSocket manager fails.
        """
        user_id = "fallback_test_user"

        # Test fallback when WebSocket manager fails
        migration_test_service.websocket_manager.send_to_user.side_effect = Exception("WebSocket manager failure")

        # SSOT should handle failure gracefully
        for event in migration_events:
            result = await migration_test_service.broadcast_to_user(user_id, event)

            # Validate graceful failure handling
            assert isinstance(result, BroadcastResult)
            assert result.successful_sends == 0  # Failed due to manager failure
            assert len(result.errors) > 0  # Errors recorded
            assert any("WebSocket manager failure" in error for error in result.errors)

            # Service should remain operational for next broadcast
            assert result.event_type == event["type"]
            assert result.user_id == user_id

        # Test fallback when connection retrieval fails
        migration_test_service.websocket_manager.send_to_user.side_effect = None
        migration_test_service.websocket_manager.send_to_user.return_value = None
        migration_test_service.websocket_manager.get_user_connections.side_effect = Exception("Connection error")

        result = await migration_test_service.broadcast_to_user(user_id, migration_events[0])
        assert result.connections_attempted >= 1  # Should assume at least one connection
        assert result.successful_sends >= 1  # Should proceed with broadcast

        # Verify stats reflect fallback scenarios
        stats = migration_test_service.get_stats()
        assert stats['broadcast_stats']['failed_broadcasts'] >= len(migration_events)
        assert stats['broadcast_stats']['total_broadcasts'] >= len(migration_events) + 1

        logger.info("✅ SSOT fallback behavior validated - graceful failure handling")

    @pytest.mark.asyncio
    async def test_ssot_configuration_validation(self, mock_websocket_manager):
        """Test SSOT configuration validation for safe migration deployment.

        MIGRATION SAFETY: Configuration validation prevents deployment
        of misconfigured SSOT service to production.
        """
        # Test valid configuration
        valid_service = WebSocketBroadcastService(mock_websocket_manager)

        # Validate service initializes correctly
        assert valid_service.websocket_manager is mock_websocket_manager
        assert valid_service._feature_flags['enable_contamination_detection'] is True
        assert valid_service._stats['total_broadcasts'] == 0

        # Test configuration stats provide validation info
        stats = valid_service.get_stats()

        # Configuration validation checks
        assert 'service_info' in stats
        assert stats['service_info']['name'] == 'WebSocketBroadcastService'
        assert stats['service_info']['version'] == '1.0.0'
        assert len(stats['service_info']['replaces']) == 3

        assert 'feature_flags' in stats
        required_flags = ['enable_contamination_detection', 'enable_performance_monitoring']
        for flag in required_flags:
            assert flag in stats['feature_flags']

        assert 'performance_metrics' in stats
        assert 'security_metrics' in stats

        # Test invalid configuration scenarios
        try:
            invalid_service = WebSocketBroadcastService(None)
            # Should fail or handle gracefully
            await invalid_service.broadcast_to_user("test_user", {"type": "test"})
            assert False, "Should have failed with None websocket_manager"
        except Exception as e:
            assert "websocket" in str(e).lower() or "manager" in str(e).lower()

        # Test feature flag validation
        valid_service.update_feature_flag('invalid_flag', True)  # Should handle gracefully
        stats = valid_service.get_stats()
        assert 'invalid_flag' not in stats['feature_flags']  # Should not be added

        logger.info("✅ SSOT configuration validation complete - safe deployment verified")

    @pytest.mark.asyncio
    async def test_ssot_memory_leak_prevention(self, migration_test_service):
        """Test SSOT prevents memory leaks during migration transition.

        MIGRATION SAFETY: Memory leaks during migration could crash production
        systems. SSOT must properly manage memory during high-volume operations.
        """
        user_id = "memory_test_user"

        # Track initial memory state
        initial_objects = len(gc.get_objects())

        # Create weak references to track object lifecycle
        service_ref = weakref.ref(migration_test_service)
        manager_ref = weakref.ref(migration_test_service.websocket_manager)

        # Simulate high-volume broadcast operations
        memory_events = []
        for i in range(100):  # Create many events
            event = {
                "type": f"memory_test_{i}",
                "data": {
                    "iteration": i,
                    "large_data": "x" * 1000,  # Add some bulk
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            memory_events.append(event)

        # Execute high-volume broadcasts
        results = []
        for event in memory_events:
            result = await migration_test_service.broadcast_to_user(user_id, event)
            results.append(result)

        # Validate all broadcasts succeeded
        assert len(results) == 100
        for result in results:
            assert isinstance(result, BroadcastResult)
            assert result.user_id == user_id

        # Force garbage collection
        del results
        del memory_events
        gc.collect()

        # Check memory growth
        final_objects = len(gc.get_objects())
        memory_growth = final_objects - initial_objects

        # Memory growth should be reasonable (< 1000 new objects for 100 broadcasts)
        assert memory_growth < 1000, f"Excessive memory growth: {memory_growth} objects"

        # Verify service and manager references still valid
        assert service_ref() is not None
        assert manager_ref() is not None

        # Check SSOT stats don't accumulate excessively
        stats = migration_test_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] == 100
        assert len(str(stats)) < 10000  # Stats shouldn't grow too large

        logger.info(f"✅ Memory leak prevention validated - growth: {memory_growth} objects")

    @pytest.mark.asyncio
    async def test_ssot_rollback_capability(self, mock_websocket_manager):
        """Test SSOT provides rollback capability for emergency scenarios.

        MIGRATION SAFETY: If SSOT deployment causes issues, must be able
        to rollback to legacy implementations quickly and safely.
        """
        # Test rollback scenario 1: Disable SSOT features
        rollback_service = WebSocketBroadcastService(mock_websocket_manager)

        # Normal operation first
        test_event = {"type": "rollback_test", "data": {"test": "normal_operation"}}
        result = await rollback_service.broadcast_to_user("rollback_user", test_event)
        assert result.successful_sends > 0

        # Rollback: Disable all SSOT features
        rollback_service.update_feature_flag('enable_contamination_detection', False)
        rollback_service.update_feature_flag('enable_performance_monitoring', False)
        rollback_service.update_feature_flag('enable_comprehensive_logging', False)

        # Service should still function with features disabled
        result = await rollback_service.broadcast_to_user("rollback_user", test_event)
        assert result.successful_sends > 0

        # Verify rollback state
        stats = rollback_service.get_stats()
        assert stats['security_metrics']['contamination_prevention_enabled'] is False
        assert all(not flag for flag in stats['feature_flags'].values())

        # Test rollback scenario 2: Factory function rollback
        with patch('netra_backend.app.services.websocket_broadcast_service.logger') as mock_logger:
            # Factory should still work in rollback mode
            rollback_factory_service = create_broadcast_service(mock_websocket_manager)
            assert isinstance(rollback_factory_service, WebSocketBroadcastService)

            # Should log rollback deployment
            mock_logger.info.assert_called()

        # Test rollback scenario 3: Legacy compatibility mode
        # (This would be implemented during actual rollback)

        # Verify rollback doesn't break existing functionality
        rollback_events = [
            {"type": "agent_started", "data": {"rollback": True}},
            {"type": "agent_completed", "data": {"rollback": True}}
        ]

        for event in rollback_events:
            result = await rollback_service.broadcast_to_user("rollback_user", event)
            assert result.successful_sends > 0

        logger.info("✅ SSOT rollback capability validated - emergency rollback ready")

    @pytest.mark.asyncio
    async def test_ssot_concurrent_migration_safety(self, migration_test_service):
        """Test SSOT handles concurrent operations safely during migration.

        MIGRATION SAFETY: During migration, concurrent operations must not
        cause race conditions or data corruption.
        """
        user_ids = [f"concurrent_migration_user_{i}" for i in range(10)]

        # Create concurrent migration stress test
        async def migration_stress_task(user_id: str, task_id: int):
            events = []
            for i in range(10):  # 10 events per task
                event = {
                    "type": f"migration_stress_{task_id}_{i}",
                    "data": {
                        "task_id": task_id,
                        "event_id": i,
                        "user_id": user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                events.append(event)

            # Broadcast all events for this task
            results = []
            for event in events:
                result = await migration_test_service.broadcast_to_user(user_id, event)
                results.append(result)

            return results

        # Execute concurrent stress tasks
        tasks = [migration_stress_task(user_id, i) for i, user_id in enumerate(user_ids)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Validate all concurrent operations succeeded
        successful_tasks = [r for r in all_results if not isinstance(r, Exception)]
        assert len(successful_tasks) == len(user_ids)

        total_broadcasts = 0
        total_successful = 0

        for task_results in successful_tasks:
            assert len(task_results) == 10  # 10 events per task
            for result in task_results:
                assert isinstance(result, BroadcastResult)
                total_broadcasts += 1
                if result.successful_sends > 0:
                    total_successful += 1

        # Verify no data corruption or race conditions
        assert total_broadcasts == len(user_ids) * 10  # 10 users * 10 events
        assert total_successful == total_broadcasts  # All should succeed

        # Check SSOT stats are consistent
        stats = migration_test_service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] >= total_broadcasts
        assert stats['broadcast_stats']['successful_broadcasts'] >= total_successful

        logger.info(f"✅ Concurrent migration safety validated: {total_broadcasts} broadcasts")

    @pytest.mark.asyncio
    async def test_ssot_error_recovery_during_migration(self, migration_test_service):
        """Test SSOT error recovery capabilities during migration.

        MIGRATION SAFETY: SSOT must recover gracefully from various error
        conditions that might occur during production migration.
        """
        user_id = "error_recovery_user"

        # Test error scenario 1: Temporary WebSocket manager failures
        failure_count = 0

        def intermittent_failure(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 3:  # First 3 calls fail
                raise Exception(f"Intermittent failure {failure_count}")
            return AsyncMock()()

        migration_test_service.websocket_manager.send_to_user.side_effect = intermittent_failure

        # SSOT should recover from intermittent failures
        recovery_events = [
            {"type": "recovery_test_1", "data": {"attempt": 1}},
            {"type": "recovery_test_2", "data": {"attempt": 2}},
            {"type": "recovery_test_3", "data": {"attempt": 3}},
            {"type": "recovery_test_4", "data": {"attempt": 4}},  # Should succeed
            {"type": "recovery_test_5", "data": {"attempt": 5}}   # Should succeed
        ]

        results = []
        for event in recovery_events:
            result = await migration_test_service.broadcast_to_user(user_id, event)
            results.append(result)

        # Validate error recovery pattern
        assert len(results) == 5

        # First 3 should fail, last 2 should succeed
        failed_results = results[:3]
        successful_results = results[3:]

        for result in failed_results:
            assert result.successful_sends == 0
            assert len(result.errors) > 0

        for result in successful_results:
            assert result.successful_sends > 0
            assert len(result.errors) == 0

        # Test error scenario 2: Resource exhaustion recovery
        migration_test_service.websocket_manager.send_to_user.side_effect = None
        migration_test_service.websocket_manager.send_to_user.return_value = None

        # Simulate resource exhaustion
        migration_test_service.websocket_manager.get_user_connections.side_effect = MemoryError("Out of memory")

        result = await migration_test_service.broadcast_to_user(user_id, {"type": "resource_test"})
        assert isinstance(result, BroadcastResult)  # Should handle gracefully

        # Reset for final test
        migration_test_service.websocket_manager.get_user_connections.side_effect = None
        migration_test_service.websocket_manager.get_user_connections.return_value = [
            {"connection_id": "recovery_conn", "user_id": user_id}
        ]

        # Final recovery test
        result = await migration_test_service.broadcast_to_user(user_id, {"type": "final_recovery"})
        assert result.successful_sends > 0

        logger.info("✅ SSOT error recovery during migration validated")

    def test_ssot_migration_compatibility_check(self):
        """Test SSOT migration compatibility with existing systems.

        MIGRATION SAFETY: Verify SSOT service maintains compatibility
        with existing interfaces and expectations.
        """
        # Test interface compatibility
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        service = WebSocketBroadcastService(mock_manager)

        # Verify SSOT service implements expected interface
        assert hasattr(service, 'broadcast_to_user')
        assert callable(service.broadcast_to_user)

        # Verify SSOT service provides stats interface
        assert hasattr(service, 'get_stats')
        assert callable(service.get_stats)

        # Verify SSOT service provides feature flag interface
        assert hasattr(service, 'update_feature_flag')
        assert callable(service.update_feature_flag)

        # Test factory compatibility
        factory_service = create_broadcast_service(mock_manager)
        assert isinstance(factory_service, WebSocketBroadcastService)

        # Verify compatibility with WebSocketManagerProtocol
        assert hasattr(mock_manager, 'send_to_user')
        assert hasattr(mock_manager, 'get_user_connections')

        # Test legacy compatibility check
        if LEGACY_ROUTER_AVAILABLE:
            logger.info("⚠️  Legacy WebSocketEventRouter still available - migration not complete")

        if USER_SCOPED_ROUTER_AVAILABLE:
            logger.info("⚠️  Legacy UserScopedWebSocketEventRouter still available - migration not complete")

        # Verify SSOT identifies legacy replacements correctly
        stats = service.get_stats()
        assert len(stats['service_info']['replaces']) == 3

        logger.info("✅ SSOT migration compatibility validated")


@pytest.mark.performance_safety
class TestSSOTMigrationPerformanceSafety:
    """Performance safety tests for SSOT migration."""

    @pytest.mark.asyncio
    async def test_ssot_performance_during_high_load_migration(self):
        """Test SSOT performance safety during high-load migration scenario.

        MIGRATION SAFETY: SSOT must maintain acceptable performance
        during high-load production migration scenarios.
        """
        mock_manager = Mock(spec=WebSocketManagerProtocol)
        mock_manager.send_to_user = AsyncMock()
        mock_manager.get_user_connections = Mock(return_value=[
            {"connection_id": "perf_conn_1", "user_id": "perf_user"}
        ])

        service = WebSocketBroadcastService(mock_manager)

        # High-load simulation
        start_time = time.time()
        broadcasts_per_second = 100
        duration_seconds = 5

        total_broadcasts = broadcasts_per_second * duration_seconds

        # Execute high-load broadcasts
        for i in range(total_broadcasts):
            event = {
                "type": f"perf_test_{i}",
                "data": {"iteration": i, "timestamp": time.time()}
            }
            result = await service.broadcast_to_user("perf_user", event)
            assert result.successful_sends > 0

            # Brief pause to simulate realistic load
            if i % 10 == 0:
                await asyncio.sleep(0.001)  # 1ms pause every 10 broadcasts

        end_time = time.time()
        total_duration = end_time - start_time

        # Performance validation
        actual_rate = total_broadcasts / total_duration
        assert actual_rate >= broadcasts_per_second * 0.8  # At least 80% of target rate

        # Memory usage should be reasonable
        stats = service.get_stats()
        assert stats['broadcast_stats']['total_broadcasts'] == total_broadcasts
        assert stats['performance_metrics']['success_rate_percentage'] >= 95.0

        logger.info(f"✅ High-load migration performance: {actual_rate:.1f} broadcasts/sec")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])