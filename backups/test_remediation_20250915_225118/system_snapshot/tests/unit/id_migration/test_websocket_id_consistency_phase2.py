"""
WebSocket ID Consistency Tests - UnifiedIDManager Phase 2

This test suite validates consistent ID generation patterns across WebSocket
infrastructure components. Tests are designed to FAIL until complete migration
from uuid.uuid4() to UnifiedIDManager patterns.

Business Value Justification:
- Segment: Platform/All (WebSocket reliability affects all users)
- Business Goal: System Reliability & User Experience
- Value Impact: Ensures consistent WebSocket routing and prevents connection issues
- Strategic Impact: $500K+ ARR depends on reliable WebSocket infrastructure
"""

import pytest
import re
import ast
from pathlib import Path
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType


@pytest.mark.unit
class WebSocketIdConsistencyPhase2Tests(SSotBaseTestCase):
    """
    Validate WebSocket ID consistency across all components.

    These tests are designed to FAIL until WebSocket components
    are fully migrated to UnifiedIDManager patterns.
    """

    def setup_method(self, method=None):
        """Set up test environment."""
        super().setup_method(method)
        self.id_manager = UnifiedIDManager()
        self.websocket_core_path = Path(__file__).parent.parent.parent.parent / 'netra_backend' / 'app' / 'websocket_core'
        self.critical_websocket_files = [
            'connection_id_manager.py',
            'connection_executor.py',
            'context.py',
            'event_validation_framework.py',
            'state_coordinator.py',
            'migration_adapter.py'
        ]

    def test_connection_id_manager_uuid_elimination(self):
        """
        FAILING TEST: connection_id_manager.py must not use uuid.uuid4().

        Critical WebSocket connection IDs must use UnifiedIDManager
        to ensure consistent routing and user isolation.
        """
        file_path = self.websocket_core_path / 'connection_id_manager.py'
        if not file_path.exists():
            self.skip(f'Connection ID manager not found: {file_path}')

        uuid_violations = self._scan_file_for_uuid_violations(file_path)

        # Record metrics for tracking
        self.record_metric('connection_id_manager_uuid_violations', len(uuid_violations))
        self.record_metric('connection_id_manager_violation_details', uuid_violations)

        assert len(uuid_violations) == 0, \
            f"connection_id_manager.py has {len(uuid_violations)} uuid.uuid4() violations. " \
            f"This is critical for WebSocket routing consistency. Violations: {uuid_violations}"

    def test_connection_executor_uuid_elimination(self):
        """
        FAILING TEST: connection_executor.py must not use uuid.uuid4().

        Connection execution requires consistent thread_id and run_id
        generation for proper agent correlation.
        """
        file_path = self.websocket_core_path / 'connection_executor.py'
        if not file_path.exists():
            self.skip(f'Connection executor not found: {file_path}')

        uuid_violations = self._scan_file_for_uuid_violations(file_path)

        self.record_metric('connection_executor_uuid_violations', len(uuid_violations))
        self.record_metric('connection_executor_violation_details', uuid_violations)

        assert len(uuid_violations) == 0, \
            f"connection_executor.py has {len(uuid_violations)} uuid.uuid4() violations. " \
            f"Thread/Run ID consistency critical for agent execution. Violations: {uuid_violations}"

    def test_event_validation_framework_uuid_elimination(self):
        """
        FAILING TEST: event_validation_framework.py must not use uuid.uuid4().

        Event IDs must be structured and traceable for proper
        WebSocket event delivery validation.
        """
        file_path = self.websocket_core_path / 'event_validation_framework.py'
        if not file_path.exists():
            self.skip(f'Event validation framework not found: {file_path}')

        uuid_violations = self._scan_file_for_uuid_violations(file_path)

        self.record_metric('event_framework_uuid_violations', len(uuid_violations))
        self.record_metric('event_framework_violation_details', uuid_violations)

        assert len(uuid_violations) == 0, \
            f"event_validation_framework.py has {len(uuid_violations)} uuid.uuid4() violations. " \
            f"Event ID traceability critical for debugging. Violations: {uuid_violations}"

    def test_websocket_context_uuid_elimination(self):
        """
        FAILING TEST: context.py must not use uuid.uuid4().

        WebSocket context requires structured run_id generation
        for proper user session correlation.
        """
        file_path = self.websocket_core_path / 'context.py'
        if not file_path.exists():
            self.skip(f'WebSocket context not found: {file_path}')

        uuid_violations = self._scan_file_for_uuid_violations(file_path)

        self.record_metric('websocket_context_uuid_violations', len(uuid_violations))
        self.record_metric('websocket_context_violation_details', uuid_violations)

        assert len(uuid_violations) == 0, \
            f"context.py has {len(uuid_violations)} uuid.uuid4() violations. " \
            f"Context correlation critical for user isolation. Violations: {uuid_violations}"

    def test_state_coordinator_uuid_elimination(self):
        """
        FAILING TEST: state_coordinator.py must not use uuid.uuid4().

        State transitions require consistent request_id generation
        for proper state machine correlation.
        """
        file_path = self.websocket_core_path / 'state_coordinator.py'
        if not file_path.exists():
            self.skip(f'State coordinator not found: {file_path}')

        uuid_violations = self._scan_file_for_uuid_violations(file_path)

        self.record_metric('state_coordinator_uuid_violations', len(uuid_violations))
        self.record_metric('state_coordinator_violation_details', uuid_violations)

        assert len(uuid_violations) == 0, \
            f"state_coordinator.py has {len(uuid_violations)} uuid.uuid4() violations. " \
            f"State transition consistency critical. Violations: {uuid_violations}"

    def test_migration_adapter_cleanup_validation(self):
        """
        FAILING TEST: migration_adapter.py should minimize uuid.uuid4() usage.

        Migration adapter may temporarily use legacy patterns but
        should be moving toward UnifiedIDManager patterns.
        """
        file_path = self.websocket_core_path / 'migration_adapter.py'
        if not file_path.exists():
            self.skip(f'Migration adapter not found: {file_path}')

        uuid_violations = self._scan_file_for_uuid_violations(file_path)
        legacy_pattern_violations = self._scan_file_for_legacy_patterns(file_path)

        self.record_metric('migration_adapter_uuid_violations', len(uuid_violations))
        self.record_metric('migration_adapter_legacy_patterns', len(legacy_pattern_violations))

        # Migration adapter allowed some legacy patterns but should be cleaning up
        total_violations = len(uuid_violations) + len(legacy_pattern_violations)
        acceptable_violation_threshold = 5  # Temporary allowance

        assert total_violations <= acceptable_violation_threshold, \
            f"migration_adapter.py has {total_violations} violations (threshold: {acceptable_violation_threshold}). " \
            f"UUID violations: {len(uuid_violations)}, Legacy patterns: {len(legacy_pattern_violations)}"

    def test_websocket_id_format_consistency(self):
        """
        FAILING TEST: All WebSocket IDs should follow consistent format patterns.

        Validates that WebSocket components use structured ID formats
        that are compatible with UnifiedIDManager validation.
        """
        # Test various ID generation scenarios
        test_scenarios = [
            {'component': 'connection', 'id_type': IDType.WEBSOCKET},
            {'component': 'event', 'id_type': IDType.REQUEST},
            {'component': 'session', 'id_type': IDType.SESSION},
            {'component': 'execution', 'id_type': IDType.EXECUTION}
        ]

        format_consistency_results = {}

        for scenario in test_scenarios:
            component = scenario['component']
            id_type = scenario['id_type']

            # Generate test IDs using UnifiedIDManager
            test_ids = []
            for i in range(10):
                test_id = self.id_manager.generate_id(id_type, prefix=f"ws_{component}")
                test_ids.append(test_id)

            # Validate format consistency
            format_valid_count = 0
            for test_id in test_ids:
                if self.id_manager.is_valid_id_format_compatible(test_id):
                    format_valid_count += 1

            consistency_rate = format_valid_count / len(test_ids) * 100
            format_consistency_results[component] = {
                'total_generated': len(test_ids),
                'format_valid': format_valid_count,
                'consistency_rate': consistency_rate
            }

        self.record_metric('websocket_id_format_consistency', format_consistency_results)

        # All components should achieve 100% format consistency
        for component, results in format_consistency_results.items():
            assert results['consistency_rate'] == 100.0, \
                f"WebSocket {component} IDs only {results['consistency_rate']:.1f}% format consistent. " \
                f"Expected 100% consistency for UnifiedIDManager compatibility."

    def test_websocket_cross_component_id_correlation(self):
        """
        FAILING TEST: IDs should correlate properly across WebSocket components.

        Tests that thread_id, run_id, and connection_id maintain
        proper relationships for debugging and traceability.
        """
        # Generate correlated IDs using UnifiedIDManager patterns
        user_id = self.id_manager.generate_id(IDType.USER, prefix="test")
        session_id = self.id_manager.generate_id(IDType.SESSION, prefix="ws")
        connection_id = self.id_manager.generate_id(IDType.WEBSOCKET, prefix="conn")
        thread_id = self.id_manager.generate_id(IDType.THREAD, prefix="chat")
        run_id = self.id_manager.generate_id(IDType.EXECUTION, prefix="agent")

        # Validate all IDs are format compatible
        all_ids = [user_id, session_id, connection_id, thread_id, run_id]
        incompatible_ids = []

        for test_id in all_ids:
            if not self.id_manager.is_valid_id_format_compatible(test_id):
                incompatible_ids.append(test_id)

        self.record_metric('websocket_correlation_test_ids', {
            'user_id': user_id,
            'session_id': session_id,
            'connection_id': connection_id,
            'thread_id': thread_id,
            'run_id': run_id
        })

        self.record_metric('incompatible_correlation_ids', incompatible_ids)

        assert len(incompatible_ids) == 0, \
            f"Found {len(incompatible_ids)} incompatible IDs in correlation test: {incompatible_ids}"

    def _scan_file_for_uuid_violations(self, file_path: Path) -> list:
        """Scan file for uuid.uuid4() usage violations."""
        violations = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            for line_num, line in enumerate(lines, 1):
                if re.search(r'uuid\.uuid4\(', line, re.IGNORECASE):
                    violations.append({
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'violation_type': 'uuid4_usage'
                    })
                elif re.search(r'uuid4\(', line, re.IGNORECASE):
                    violations.append({
                        'line_number': line_num,
                        'line_content': line.strip(),
                        'violation_type': 'uuid4_import_usage'
                    })

        except Exception as e:
            violations.append({
                'line_number': 0,
                'line_content': f"Scan error: {str(e)}",
                'violation_type': 'scan_error'
            })

        return violations

    def _scan_file_for_legacy_patterns(self, file_path: Path) -> list:
        """Scan file for legacy ID generation patterns."""
        legacy_patterns = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()

            # Common legacy patterns
            patterns = [
                r'f"demo-.*{uuid',
                r'f"legacy_.*{uuid',
                r'\.hex\[:8\]',
                r'str\(uuid\.uuid4\(\)\)',
            ]

            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        legacy_patterns.append({
                            'line_number': line_num,
                            'line_content': line.strip(),
                            'pattern': pattern
                        })

        except Exception as e:
            legacy_patterns.append({
                'line_number': 0,
                'line_content': f"Scan error: {str(e)}",
                'pattern': 'scan_error'
            })

        return legacy_patterns


if __name__ == '__main__':
    # MIGRATED: Use SSOT unified test runner
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category unit --pattern "*websocket_id_consistency*"')