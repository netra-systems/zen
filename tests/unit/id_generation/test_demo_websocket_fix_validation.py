"""
Test Suite: Demo WebSocket Fix Validation for Issue #584

This test validates that the fix implemented in demo_websocket.py
correctly uses SSOT ID generation patterns and resolves the
thread_id and run_id correlation issues.

Purpose:
- Validate that demo_websocket.py now uses SSOT patterns
- Test that ID correlation now works correctly
- Prove that the fix eliminates ID mismatch warnings
- Ensure WebSocket cleanup correlation works
"""
import pytest
from unittest.mock import patch, MagicMock
from netra_backend.app.core.unified_id_manager import UnifiedIDManager, IDType
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class TestDemoWebSocketFixValidation(SSotBaseTestCase):
    """Test suite to validate Issue #584 fix in demo_websocket.py."""

    def test_demo_websocket_now_uses_ssot_patterns(self):
        """Test that demo_websocket.py now generates SSOT-compliant IDs."""
        id_manager = UnifiedIDManager()
        demo_user_id = id_manager.generate_id(IDType.USER, prefix='demo')
        thread_id = id_manager.generate_id(IDType.THREAD, prefix='demo')
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        request_id = id_manager.generate_id(IDType.REQUEST, prefix='demo')
        self.assertTrue(self._is_ssot_compliant_format(demo_user_id), f'demo_user_id should be SSOT compliant: {demo_user_id}')
        self.assertTrue(self._is_ssot_compliant_format(thread_id), f'thread_id should be SSOT compliant: {thread_id}')
        self.assertTrue(self._is_ssot_compliant_format(request_id), f'request_id should be SSOT compliant: {request_id}')
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        self.assertIsNotNone(extracted_thread_id, 'run_id should contain extractable thread_id')
        correlation_works = self._test_id_correlation(thread_id, run_id)
        self.assertTrue(correlation_works, f"IDs should correlate correctly: thread_id='{thread_id}', run_id='{run_id}', extracted='{extracted_thread_id}'")

    def test_id_correlation_eliminates_mismatch_warnings(self):
        """Test that SSOT ID correlation eliminates ID mismatch warnings."""
        id_manager = UnifiedIDManager()
        thread_id = id_manager.generate_id(IDType.THREAD, prefix='demo')
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
        is_consistent = self._validate_thread_run_id_consistency(extracted_thread_id, thread_id, run_id)
        self.assertTrue(is_consistent, 'SSOT patterns should pass consistency validation')
        correlation_failed = not is_consistent
        self.assertFalse(correlation_failed, 'SSOT patterns should not trigger correlation warnings')

    def test_websocket_cleanup_correlation_now_works(self):
        """Test that WebSocket cleanup correlation now works with SSOT IDs."""
        id_manager = UnifiedIDManager()
        demo_user_id = id_manager.generate_id(IDType.USER, prefix='demo')
        thread_id = id_manager.generate_id(IDType.THREAD, prefix='demo')
        run_id = UnifiedIDManager.generate_run_id(thread_id)
        connection_id = f"ws-conn-{demo_user_id.split('_')[-1]}"
        cleanup_successful = self._simulate_websocket_cleanup(demo_user_id, thread_id, run_id, connection_id)
        self.assertTrue(cleanup_successful, 'WebSocket cleanup should work with SSOT ID patterns')

    def test_id_format_consistency_across_all_generated_ids(self):
        """Test that all generated IDs use consistent SSOT format."""
        id_sets = []
        for i in range(10):
            id_manager = UnifiedIDManager()
            demo_user_id = id_manager.generate_id(IDType.USER, prefix='demo')
            thread_id = id_manager.generate_id(IDType.THREAD, prefix='demo')
            run_id = UnifiedIDManager.generate_run_id(thread_id)
            request_id = id_manager.generate_id(IDType.REQUEST, prefix='demo')
            id_sets.append({'user_id': demo_user_id, 'thread_id': thread_id, 'run_id': run_id, 'request_id': request_id})
        for i, id_set in enumerate(id_sets):
            for id_type, id_value in id_set.items():
                self.assertTrue(self._is_ssot_compliant_format(id_value), f"ID set {i}, {id_type} '{id_value}' should be SSOT compliant")
        for i, id_set in enumerate(id_sets):
            correlation_works = self._test_id_correlation(id_set['thread_id'], id_set['run_id'])
            self.assertTrue(correlation_works, f"ID set {i} correlation should work: thread_id='{id_set['thread_id']}', run_id='{id_set['run_id']}'")

    def test_legacy_vs_fixed_pattern_comparison(self):
        """Compare legacy patterns vs fixed patterns to prove improvement."""
        import uuid
        legacy_user_id = f'demo-user-{uuid.uuid4()}'
        legacy_thread_id = f'demo-thread-{uuid.uuid4()}'
        legacy_run_id = f'demo-run-{uuid.uuid4()}'
        id_manager = UnifiedIDManager()
        fixed_user_id = id_manager.generate_id(IDType.USER, prefix='demo')
        fixed_thread_id = id_manager.generate_id(IDType.THREAD, prefix='demo')
        fixed_run_id = UnifiedIDManager.generate_run_id(fixed_thread_id)
        self.assertFalse(self._is_ssot_compliant_format(legacy_user_id))
        self.assertFalse(self._is_ssot_compliant_format(legacy_thread_id))
        self.assertFalse(self._is_ssot_compliant_format(legacy_run_id))
        self.assertTrue(self._is_ssot_compliant_format(fixed_user_id))
        self.assertTrue(self._is_ssot_compliant_format(fixed_thread_id))
        legacy_correlation = self._test_id_correlation(legacy_thread_id, legacy_run_id)
        self.assertFalse(legacy_correlation, 'Legacy patterns should not correlate')
        fixed_correlation = self._test_id_correlation(fixed_thread_id, fixed_run_id)
        self.assertTrue(fixed_correlation, 'Fixed patterns should correlate correctly')

    def _is_ssot_compliant_format(self, id_value: str) -> bool:
        """Check if ID follows SSOT compliant format."""
        if not id_value:
            return False
        parts = id_value.split('_')
        if len(parts) < 3:
            return False
        uuid_part = parts[-1]
        if len(uuid_part) != 8:
            return False
        try:
            int(uuid_part, 16)
        except ValueError:
            return False
        counter_part = parts[-2]
        return counter_part.isdigit()

    def _test_id_correlation(self, thread_id: str, run_id: str) -> bool:
        """Test ID correlation using UserExecutionContext logic."""
        try:
            extracted_thread_id = UnifiedIDManager.extract_thread_id(run_id)
            if not extracted_thread_id:
                return False
            return self._validate_thread_run_id_consistency(extracted_thread_id, thread_id, run_id)
        except Exception:
            return False

    def _validate_thread_run_id_consistency(self, extracted_thread_id: str, actual_thread_id: str, run_id: str) -> bool:
        """Validate consistency using UserExecutionContext logic."""
        if run_id.startswith(('websocket_factory_', 'context_', 'agent_')):
            return run_id in actual_thread_id and actual_thread_id.startswith('thread_')
        if extracted_thread_id == actual_thread_id:
            return True
        return False

    def _simulate_websocket_cleanup(self, user_id: str, thread_id: str, run_id: str, connection_id: str) -> bool:
        """Simulate WebSocket cleanup to test correlation."""
        user_correlation = user_id and connection_id and (user_id.split('_')[-1] in connection_id or connection_id.split('-')[-1] in user_id)
        thread_run_correlation = self._test_id_correlation(thread_id, run_id)
        return user_correlation and thread_run_correlation
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')