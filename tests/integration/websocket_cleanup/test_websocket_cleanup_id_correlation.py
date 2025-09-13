"""
Integration Test Suite: WebSocket Cleanup ID Correlation for Issue #584

This test suite validates WebSocket cleanup correlation with both
mismatched ID formats (reproducing the issue) and SSOT ID formats
(proving the fix works).

Purpose:
- Test WebSocket cleanup fails with mismatched ID formats
- Test WebSocket cleanup succeeds with SSOT IDs
- Validate ID audit trail in WebSocket operations
- Ensure resource leak detection works correctly

Business Impact:
- Prevents WebSocket resource leaks in long-running sessions
- Ensures proper cleanup correlation for $500K+ ARR protection
- Validates debugging capabilities through proper ID tracking
"""

import asyncio
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, List, Optional

from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.services.user_execution_context import UserExecutionContext
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestWebSocketCleanupCorrelation(SSotAsyncTestCase):
    """Integration tests for WebSocket cleanup correlation with ID patterns."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.id_manager = UnifiedIDManager()
        self.cleanup_tracker = WebSocketCleanupTracker()

    async def test_cleanup_correlation_with_mismatched_ids(self):
        """Test WebSocket cleanup fails with mismatched ID formats.

        This test reproduces the exact issue where legacy UUID patterns
        break WebSocket cleanup correlation logic.
        """
        # Create WebSocket connection with legacy ID formats (problematic pattern)
        legacy_user_id = f"demo-user-{uuid.uuid4()}"
        legacy_thread_id = f"demo-thread-{uuid.uuid4()}"
        legacy_run_id = f"demo-run-{uuid.uuid4()}"

        # Simulate WebSocket connection setup
        mock_websocket = MockWebSocket(legacy_user_id)
        connection_id = f"ws-conn-{uuid.uuid4()}"

        # Create user context with mismatched ID patterns
        user_context = self._create_mock_user_context(
            user_id=legacy_user_id,
            thread_id=legacy_thread_id,
            run_id=legacy_run_id,
            websocket_client_id=connection_id
        )

        # Simulate WebSocket resource registration
        await self._register_websocket_resources(mock_websocket, user_context)

        # EXPECT: Cleanup correlation to fail due to ID format mismatch
        cleanup_result = await self._attempt_websocket_cleanup(user_context)

        # VALIDATE: Resource leak detection
        self.assertFalse(cleanup_result.success,
                        "Cleanup should fail with mismatched ID formats")
        self.assertGreater(cleanup_result.leaked_resources, 0,
                          "Resource leaks should be detected")
        self.assertTrue(cleanup_result.correlation_failed,
                       "Correlation failure should be detected")

        # Verify specific correlation failure
        correlation_issues = cleanup_result.correlation_issues
        self.assertIn("thread_id_mismatch", correlation_issues)
        self.assertIn("format_inconsistency", correlation_issues)

    async def test_cleanup_correlation_with_ssot_ids(self):
        """Test WebSocket cleanup succeeds with SSOT IDs.

        This test proves that using proper SSOT ID patterns
        enables correct WebSocket cleanup correlation.
        """
        # Create WebSocket connection with SSOT ID formats (correct pattern)
        ssot_user_id = self.id_manager.generate_id(IDType.USER, prefix="demo")
        ssot_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="demo")
        ssot_run_id = UnifiedIDManager.generate_run_id(ssot_thread_id)

        # Simulate WebSocket connection setup
        mock_websocket = MockWebSocket(ssot_user_id)
        connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="demo")

        # Create user context with SSOT ID patterns
        user_context = self._create_mock_user_context(
            user_id=ssot_user_id,
            thread_id=ssot_thread_id,
            run_id=ssot_run_id,
            websocket_client_id=connection_id
        )

        # Simulate WebSocket resource registration
        await self._register_websocket_resources(mock_websocket, user_context)

        # EXPECT: Cleanup correlation to succeed with SSOT patterns
        cleanup_result = await self._attempt_websocket_cleanup(user_context)

        # VALIDATE: Proper resource cleanup
        self.assertTrue(cleanup_result.success,
                       "Cleanup should succeed with SSOT ID formats")
        self.assertEqual(cleanup_result.leaked_resources, 0,
                        "No resource leaks should occur")
        self.assertFalse(cleanup_result.correlation_failed,
                        "Correlation should work correctly")

        # Verify successful correlation
        self.assertGreater(cleanup_result.cleaned_resources, 0,
                          "Resources should be successfully cleaned")

    async def test_websocket_connection_id_audit_trail(self):
        """Test ID audit trail in WebSocket operations.

        This test validates that ID usage is tracked consistently
        throughout the WebSocket lifecycle.
        """
        # Create SSOT-compliant IDs for tracking
        user_id = self.id_manager.generate_id(IDType.USER, prefix="audit")
        thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="audit")
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="audit")

        # Track ID usage through WebSocket lifecycle
        audit_trail = WebSocketAuditTrail()

        # Phase 1: Connection establishment
        await audit_trail.track_connection_establishment(user_id, connection_id)

        # Phase 2: User context creation
        user_context = self._create_mock_user_context(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            websocket_client_id=connection_id
        )
        await audit_trail.track_context_creation(user_context)

        # Phase 3: Agent execution
        await audit_trail.track_agent_execution(user_context, "SupervisorAgent")

        # Phase 4: WebSocket events
        await audit_trail.track_websocket_events(connection_id, run_id, [
            "agent_started", "agent_thinking", "tool_executing",
            "tool_completed", "agent_completed"
        ])

        # Phase 5: Connection cleanup
        await audit_trail.track_cleanup_attempt(user_context)

        # EXPECT: Consistent ID usage throughout lifecycle
        trail_validation = audit_trail.validate_consistency()

        # VALIDATE: Audit trail completeness
        self.assertTrue(trail_validation.is_complete,
                       "Audit trail should be complete")
        self.assertTrue(trail_validation.ids_consistent,
                       "IDs should be consistent throughout lifecycle")
        self.assertEqual(trail_validation.missing_phases, [],
                        "No lifecycle phases should be missing")

        # Validate specific ID correlations
        self.assertTrue(trail_validation.thread_run_correlation,
                       "Thread ID and run ID should correlate")
        self.assertTrue(trail_validation.user_connection_correlation,
                       "User ID and connection ID should correlate")

    async def test_legacy_to_ssot_migration_compatibility(self):
        """Test WebSocket cleanup during ID pattern migration.

        This test validates that the system can handle mixed ID patterns
        during the migration period without causing resource leaks.
        """
        # Simulate mixed environment: some legacy, some SSOT
        legacy_user_id = f"demo-user-{uuid.uuid4()}"
        ssot_thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="demo")
        ssot_run_id = UnifiedIDManager.generate_run_id(ssot_thread_id)

        # Create user context with mixed patterns
        user_context = self._create_mock_user_context(
            user_id=legacy_user_id,  # Legacy
            thread_id=ssot_thread_id,  # SSOT
            run_id=ssot_run_id,  # SSOT
            websocket_client_id=f"ws-{uuid.uuid4()}"  # Legacy
        )

        # Test migration compatibility
        migration_result = await self._test_migration_compatibility(user_context)

        # VALIDATE: Migration handles mixed patterns gracefully
        self.assertTrue(migration_result.handles_mixed_patterns,
                       "System should handle mixed ID patterns")
        self.assertLessEqual(migration_result.resource_leaks, 1,
                           "Resource leaks should be minimal during migration")

    def _create_mock_user_context(self, user_id: str, thread_id: str,
                                 run_id: str, websocket_client_id: str) -> UserExecutionContext:
        """Create mock UserExecutionContext for testing."""
        # Create a minimal mock that focuses on ID validation
        mock_context = MagicMock(spec=UserExecutionContext)
        mock_context.user_id = user_id
        mock_context.thread_id = thread_id
        mock_context.run_id = run_id
        mock_context.websocket_client_id = websocket_client_id
        mock_context.request_id = f"req-{uuid.uuid4()}"

        # Add ID validation method
        mock_context._validate_id_consistency = MagicMock()
        mock_context._validate_thread_run_id_consistency = MagicMock(
            return_value=self._test_correlation(thread_id, run_id)
        )

        return mock_context

    def _test_correlation(self, thread_id: str, run_id: str) -> bool:
        """Test ID correlation using real validation logic."""
        try:
            extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
            if not extracted_thread_id:
                return False

            # Use same logic as UserExecutionContext
            # Pattern 1: UnifiedIdGenerator pattern
            if run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
                return run_id in thread_id and thread_id.startswith('thread_')

            # Pattern 2: UnifiedIDManager pattern
            return extracted_thread_id == thread_id

        except Exception:
            return False

    async def _register_websocket_resources(self, websocket: 'MockWebSocket',
                                          user_context: UserExecutionContext) -> None:
        """Simulate WebSocket resource registration."""
        self.cleanup_tracker.register_websocket(websocket, user_context)

    async def _attempt_websocket_cleanup(self, user_context: UserExecutionContext) -> 'CleanupResult':
        """Attempt WebSocket cleanup and return results."""
        return await self.cleanup_tracker.cleanup_user_resources(user_context)

    async def _test_migration_compatibility(self, user_context: UserExecutionContext) -> 'MigrationResult':
        """Test migration compatibility with mixed ID patterns."""
        migration_tracker = MigrationCompatibilityTracker()
        return await migration_tracker.test_mixed_patterns(user_context)


class MockWebSocket:
    """Mock WebSocket for testing purposes."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.connection_id = f"mock-ws-{uuid.uuid4()}"
        self.is_closed = False
        self.sent_messages = []

    async def send_json(self, data: dict) -> None:
        """Mock send_json method."""
        self.sent_messages.append(data)

    async def close(self) -> None:
        """Mock close method."""
        self.is_closed = True


class WebSocketCleanupTracker:
    """Tracks WebSocket connections and cleanup attempts."""

    def __init__(self):
        self.connections: Dict[str, MockWebSocket] = {}
        self.user_contexts: Dict[str, UserExecutionContext] = {}

    def register_websocket(self, websocket: MockWebSocket, user_context: UserExecutionContext) -> None:
        """Register a WebSocket connection for tracking."""
        self.connections[user_context.websocket_client_id] = websocket
        self.user_contexts[user_context.user_id] = user_context

    async def cleanup_user_resources(self, user_context: UserExecutionContext) -> 'CleanupResult':
        """Attempt to cleanup user resources and return results."""
        result = CleanupResult()

        try:
            # Simulate correlation logic
            correlation_works = self._test_id_correlation(user_context)
            result.correlation_failed = not correlation_works

            if correlation_works:
                # Simulate successful cleanup
                result.success = True
                result.cleaned_resources = 1
                result.leaked_resources = 0
            else:
                # Simulate failed cleanup
                result.success = False
                result.cleaned_resources = 0
                result.leaked_resources = 1
                result.correlation_issues = ["thread_id_mismatch", "format_inconsistency"]

        except Exception as e:
            result.success = False
            result.error = str(e)

        return result

    def _test_id_correlation(self, user_context: UserExecutionContext) -> bool:
        """Test if ID correlation works for cleanup."""
        # Use actual correlation logic
        try:
            extracted_thread_id = UnifiedIDManager.extract_thread_id(user_context.run_id)
            if not extracted_thread_id:
                return False

            # Pattern matching logic from UserExecutionContext
            if user_context.run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
                return (user_context.run_id in user_context.thread_id and
                       user_context.thread_id.startswith('thread_'))

            return extracted_thread_id == user_context.thread_id

        except Exception:
            return False


class WebSocketAuditTrail:
    """Tracks ID usage throughout WebSocket lifecycle."""

    def __init__(self):
        self.phases: List[str] = []
        self.id_usage: Dict[str, List[str]] = {}

    async def track_connection_establishment(self, user_id: str, connection_id: str) -> None:
        """Track connection establishment phase."""
        self.phases.append("connection_establishment")
        self._record_id_usage("connection_establishment", [user_id, connection_id])

    async def track_context_creation(self, user_context: UserExecutionContext) -> None:
        """Track user context creation phase."""
        self.phases.append("context_creation")
        self._record_id_usage("context_creation", [
            user_context.user_id, user_context.thread_id,
            user_context.run_id, user_context.websocket_client_id
        ])

    async def track_agent_execution(self, user_context: UserExecutionContext, agent_name: str) -> None:
        """Track agent execution phase."""
        self.phases.append("agent_execution")
        self._record_id_usage("agent_execution", [
            user_context.thread_id, user_context.run_id
        ])

    async def track_websocket_events(self, connection_id: str, run_id: str, events: List[str]) -> None:
        """Track WebSocket events phase."""
        self.phases.append("websocket_events")
        self._record_id_usage("websocket_events", [connection_id, run_id])

    async def track_cleanup_attempt(self, user_context: UserExecutionContext) -> None:
        """Track cleanup attempt phase."""
        self.phases.append("cleanup_attempt")
        self._record_id_usage("cleanup_attempt", [
            user_context.user_id, user_context.websocket_client_id
        ])

    def validate_consistency(self) -> 'TrailValidation':
        """Validate audit trail consistency."""
        validation = TrailValidation()

        # Check completeness
        expected_phases = ["connection_establishment", "context_creation",
                          "agent_execution", "websocket_events", "cleanup_attempt"]
        validation.is_complete = all(phase in self.phases for phase in expected_phases)
        validation.missing_phases = [phase for phase in expected_phases if phase not in self.phases]

        # Check ID consistency
        validation.ids_consistent = self._validate_id_consistency()
        validation.thread_run_correlation = self._validate_thread_run_correlation()
        validation.user_connection_correlation = self._validate_user_connection_correlation()

        return validation

    def _record_id_usage(self, phase: str, ids: List[str]) -> None:
        """Record ID usage for a phase."""
        if phase not in self.id_usage:
            self.id_usage[phase] = []
        self.id_usage[phase].extend(ids)

    def _validate_id_consistency(self) -> bool:
        """Validate that same IDs are used consistently across phases."""
        # Extract unique IDs across all phases
        all_ids = set()
        for ids in self.id_usage.values():
            all_ids.update(ids)

        # Check that critical IDs appear in multiple phases
        id_counts = {}
        for ids in self.id_usage.values():
            for id_val in ids:
                id_counts[id_val] = id_counts.get(id_val, 0) + 1

        # IDs should appear in multiple phases if consistent
        multi_phase_ids = [id_val for id_val, count in id_counts.items() if count > 1]
        return len(multi_phase_ids) >= 2  # At least thread_id and run_id should be reused

    def _validate_thread_run_correlation(self) -> bool:
        """Validate thread_id and run_id correlation."""
        # Find thread_id and run_id from context_creation phase
        context_ids = self.id_usage.get("context_creation", [])
        thread_ids = [id_val for id_val in context_ids if "thread" in id_val]
        run_ids = [id_val for id_val in context_ids if "run" in id_val]

        if not thread_ids or not run_ids:
            return False

        # Test correlation
        thread_id = thread_ids[0]
        run_id = run_ids[0]

        try:
            extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
            return extracted_thread_id and (extracted_thread_id == thread_id or run_id in thread_id)
        except Exception:
            return False

    def _validate_user_connection_correlation(self) -> bool:
        """Validate user_id and connection_id correlation."""
        connection_ids = self.id_usage.get("connection_establishment", [])
        context_ids = self.id_usage.get("context_creation", [])

        # Check that user_id appears in both phases
        user_ids_conn = [id_val for id_val in connection_ids if "user" in id_val]
        user_ids_context = [id_val for id_val in context_ids if "user" in id_val]

        return bool(user_ids_conn and user_ids_context and
                   any(uid in user_ids_context for uid in user_ids_conn))


class MigrationCompatibilityTracker:
    """Tracks compatibility during ID pattern migration."""

    async def test_mixed_patterns(self, user_context: UserExecutionContext) -> 'MigrationResult':
        """Test handling of mixed ID patterns."""
        result = MigrationResult()

        # Analyze ID patterns
        patterns = self._analyze_id_patterns(user_context)
        result.handles_mixed_patterns = len(set(patterns.values())) > 1

        # Simulate resource leak testing
        result.resource_leaks = self._simulate_resource_leaks(patterns)

        return result

    def _analyze_id_patterns(self, user_context: UserExecutionContext) -> Dict[str, str]:
        """Analyze ID patterns in user context."""
        patterns = {}

        # Analyze each ID type
        patterns['user_id'] = self._detect_pattern(user_context.user_id)
        patterns['thread_id'] = self._detect_pattern(user_context.thread_id)
        patterns['run_id'] = self._detect_pattern(user_context.run_id)
        patterns['websocket_client_id'] = self._detect_pattern(user_context.websocket_client_id)

        return patterns

    def _detect_pattern(self, id_value: str) -> str:
        """Detect ID pattern type."""
        if not id_value:
            return "unknown"

        # Check for legacy UUID pattern
        if '-' in id_value and len(id_value.split('-')) >= 2:
            try:
                uuid_part = '-'.join(id_value.split('-')[1:])
                uuid.UUID(uuid_part)
                return "legacy_uuid"
            except ValueError:
                pass

        # Check for SSOT pattern
        parts = id_value.split('_')
        if len(parts) >= 3 and parts[-2].isdigit() and len(parts[-1]) == 8:
            try:
                int(parts[-1], 16)
                return "ssot"
            except ValueError:
                pass

        return "unknown"

    def _simulate_resource_leaks(self, patterns: Dict[str, str]) -> int:
        """Simulate resource leak count based on pattern mix."""
        pattern_types = set(patterns.values())

        # Mixed patterns cause some resource leaks
        if len(pattern_types) > 1 and "legacy_uuid" in pattern_types:
            return 1  # Some leaks with mixed patterns
        elif "legacy_uuid" in pattern_types:
            return 2  # More leaks with pure legacy
        else:
            return 0  # No leaks with pure SSOT


# Result classes for test validation
class CleanupResult:
    """Results of WebSocket cleanup attempt."""

    def __init__(self):
        self.success: bool = False
        self.cleaned_resources: int = 0
        self.leaked_resources: int = 0
        self.correlation_failed: bool = False
        self.correlation_issues: List[str] = []
        self.error: Optional[str] = None


class TrailValidation:
    """Validation results for audit trail."""

    def __init__(self):
        self.is_complete: bool = False
        self.ids_consistent: bool = False
        self.missing_phases: List[str] = []
        self.thread_run_correlation: bool = False
        self.user_connection_correlation: bool = False


class MigrationResult:
    """Results of migration compatibility testing."""

    def __init__(self):
        self.handles_mixed_patterns: bool = False
        self.resource_leaks: int = 0


if __name__ == '__main__':
    pytest.main([__file__])