"""
Unit Tests: SessionMetrics SSOT Violation Detection

This test suite validates the SessionMetrics classes for SSOT compliance
and exposes field naming inconsistencies that cause AttributeError.

Business Value:
- Prevents runtime AttributeError crashes in session factory error handling
- Ensures consistent API surface across SessionMetrics implementations 
- Validates SSOT architectural principles for session management

CRITICAL: These tests are DESIGNED TO FAIL to expose SSOT violations.
When they fail, it proves the architectural inconsistency exists.

Expected Failures:
1. test_session_metrics_field_access_consistency - AttributeError on last_activity
2. test_session_metrics_interface_compatibility - Field name mismatch
3. test_request_scoped_session_factory_error_field_access - Exact bug reproduction

Related SSOT Violations:
- Line 383 in request_scoped_session_factory.py: session_metrics.last_activity 
- Field actually named: last_activity_at
- Additional mismatches: operations_count, errors fields
"""
import pytest
import sys
from datetime import datetime, timezone
from typing import Dict, Any
from dataclasses import dataclass
from netra_backend.app.database.request_scoped_session_factory import SessionMetrics as RequestScopedSessionMetrics, SessionState
try:
    from shared.session_management.user_session_manager import SessionMetrics as SharedSessionMetrics
    SHARED_SESSION_METRICS_AVAILABLE = True
except ImportError as e:
    SHARED_SESSION_METRICS_AVAILABLE = False
    pytest.skip(f'Shared SessionMetrics not available: {e}', allow_module_level=True)

class SessionMetricsSSotValidationTests:
    """
    Test suite to validate SessionMetrics SSOT compliance.
    
    This suite exposes the exact SSOT violation where two SessionMetrics
    classes exist with different field names, causing AttributeError.
    """

    def test_session_metrics_classes_exist(self):
        """Verify both SessionMetrics classes can be imported."""
        assert RequestScopedSessionMetrics is not None, 'RequestScopedSessionMetrics should be importable'
        assert SharedSessionMetrics is not None, 'SharedSessionMetrics should be importable'
        print(f'\n SEARCH:  DISCOVERED SESSIONMETRICS CLASSES:')
        print(f'  RequestScoped: {RequestScopedSessionMetrics}')
        print(f'  Shared: {SharedSessionMetrics}')

    def test_session_metrics_field_access_consistency(self):
        """
        CRITICAL TEST: This test reproduces the exact AttributeError bug.
        
        The request_scoped_session_factory.py tries to access:
        - session_metrics.last_activity (line 383)
        - session_metrics.operations_count (line 384) 
        - session_metrics.errors (line 385)
        
        But the actual field names are different, causing AttributeError.
        """
        request_metrics = RequestScopedSessionMetrics(session_id='test-session-123', request_id='test-request-456', user_id='test-user-789', created_at=datetime.now(timezone.utc))
        with pytest.raises(AttributeError, match="has no attribute 'last_activity'"):
            _ = request_metrics.last_activity
            pytest.fail("Expected AttributeError for 'last_activity' field access")
        with pytest.raises(AttributeError, match="has no attribute 'operations_count'"):
            _ = request_metrics.operations_count
            pytest.fail("Expected AttributeError for 'operations_count' field access")
        with pytest.raises(AttributeError, match="has no attribute 'errors'"):
            _ = request_metrics.errors
            pytest.fail("Expected AttributeError for 'errors' field access")
        assert hasattr(request_metrics, 'last_activity_at'), "Should have 'last_activity_at' field"
        assert hasattr(request_metrics, 'error_count'), "Should have 'error_count' field"

    def test_session_metrics_interface_compatibility(self):
        """
        Test that both SessionMetrics classes have compatible interfaces.
        
        This test will FAIL because the classes have different field names,
        proving the SSOT violation exists.
        """
        request_scoped_fields = set(RequestScopedSessionMetrics.__annotations__.keys())
        shared_fields = set(SharedSessionMetrics.__annotations__.keys())
        print(f'\n[U+1F4CB] FIELD COMPARISON:')
        print(f'  RequestScoped fields: {sorted(request_scoped_fields)}')
        print(f'  Shared fields: {sorted(shared_fields)}')
        print(f'  Common fields: {sorted(request_scoped_fields & shared_fields)}')
        print(f'  RequestScoped only: {sorted(request_scoped_fields - shared_fields)}')
        print(f'  Shared only: {sorted(shared_fields - request_scoped_fields)}')
        assert request_scoped_fields == shared_fields, f'SSOT VIOLATION: SessionMetrics classes have different fields!\nRequestScoped only: {request_scoped_fields - shared_fields}\nShared only: {shared_fields - request_scoped_fields}\nThis proves the SSOT violation exists.'

    def test_request_scoped_session_factory_error_field_access(self):
        """
        Test that reproduces the EXACT error from request_scoped_session_factory.py.
        
        This simulates the error handling code path where the bug occurs.
        """
        session_metrics = RequestScopedSessionMetrics(session_id='error-test-session', request_id='error-test-request', user_id='error-test-user', created_at=datetime.now(timezone.utc))
        try:
            error_context = {'session_metrics': {'state': session_metrics.state.value if session_metrics.state else 'unknown', 'created_at': session_metrics.created_at.isoformat() if session_metrics.created_at else None, 'last_activity': session_metrics.last_activity.isoformat() if session_metrics.last_activity else None, 'operations_count': session_metrics.operations_count, 'errors': session_metrics.errors}}
            pytest.fail(f'Expected AttributeError when accessing non-existent fields, but error_context was created: {error_context}')
        except AttributeError as e:
            assert 'last_activity' in str(e) or 'operations_count' in str(e) or 'errors' in str(e), f'AttributeError should mention the missing fields, got: {e}'
            print(f'\n PASS:  BUG REPRODUCED: {e}')
            print('This proves the SSOT violation in request_scoped_session_factory.py line 383-385')

    def test_session_metrics_correct_field_names(self):
        """
        Test the correct field names that actually exist in RequestScopedSessionMetrics.
        
        This test shows what the code SHOULD be accessing instead.
        """
        session_metrics = RequestScopedSessionMetrics(session_id='correct-test-session', request_id='correct-test-request', user_id='correct-test-user', created_at=datetime.now(timezone.utc))
        session_metrics.mark_activity()
        session_metrics.record_error('Test error')
        correct_context = {'session_metrics': {'state': session_metrics.state.value if session_metrics.state else 'unknown', 'created_at': session_metrics.created_at.isoformat() if session_metrics.created_at else None, 'last_activity': session_metrics.last_activity_at.isoformat() if session_metrics.last_activity_at else None, 'query_count': session_metrics.query_count, 'transaction_count': session_metrics.transaction_count, 'error_count': session_metrics.error_count, 'last_error': session_metrics.last_error}}
        assert correct_context['session_metrics']['query_count'] == 0
        assert correct_context['session_metrics']['error_count'] == 1
        assert correct_context['session_metrics']['last_error'] == 'Test error'
        print(f'\n PASS:  CORRECT USAGE EXAMPLE:')
        print(f'  Use: last_activity_at (not last_activity)')
        print(f'  Use: error_count (not errors)')
        print(f"  Use: query_count + transaction_count (operations_count doesn't exist)")

    def test_shared_session_metrics_structure(self):
        """Test the structure of SharedSessionMetrics for comparison."""
        if not SHARED_SESSION_METRICS_AVAILABLE:
            pytest.skip('SharedSessionMetrics not available', allow_module_level=True)
        shared_metrics = SharedSessionMetrics()
        fields = {'total_sessions': shared_metrics.total_sessions, 'active_sessions': shared_metrics.active_sessions, 'expired_sessions_cleaned': shared_metrics.expired_sessions_cleaned, 'sessions_created_today': shared_metrics.sessions_created_today, 'sessions_reused_today': shared_metrics.sessions_reused_today, 'average_session_duration_minutes': shared_metrics.average_session_duration_minutes, 'memory_usage_mb': shared_metrics.memory_usage_mb}
        print(f'\n CHART:  SHARED SESSIONMETRICS STRUCTURE:')
        for field_name, field_value in fields.items():
            print(f'  {field_name}: {field_value} ({type(field_value).__name__})')
        assert hasattr(shared_metrics, 'to_dict'), 'SharedSessionMetrics should have to_dict method'
        metrics_dict = shared_metrics.to_dict()
        assert isinstance(metrics_dict, dict), 'to_dict should return a dictionary'
        assert len(fields) > 0, 'SharedSessionMetrics should have fields'

class SessionMetricsArchitecturalIssuesTests:
    """
    Additional tests that highlight architectural problems with SessionMetrics.
    """

    def test_session_metrics_purpose_mismatch(self):
        """
        Test that shows the two SessionMetrics classes serve different purposes.
        
        This is an architectural issue - same class name, different purposes.
        """
        request_metrics = RequestScopedSessionMetrics(session_id='purpose-test-123', request_id='purpose-test-456', user_id='purpose-test-789', created_at=datetime.now(timezone.utc))
        shared_metrics = SharedSessionMetrics()
        print(f'\n TARGET:  PURPOSE ANALYSIS:')
        print(f'  RequestScoped: Single session lifecycle tracking')
        print(f'  Shared: Global session statistics and metrics')
        print(f'  ISSUE: Same class name, completely different purposes!')
        assert type(request_metrics).__name__ == 'SessionMetrics'
        assert type(shared_metrics).__name__ == 'SessionMetrics'
        pytest.fail("ARCHITECTURAL VIOLATION: Two classes named 'SessionMetrics' with different purposes. This violates SSOT principles and creates confusion.")

    def test_session_metrics_naming_convention_violation(self):
        """
        Test that exposes naming convention violations in SessionMetrics.
        
        Good naming would be:
        - SessionLifecycleMetrics (for per-session tracking)
        - SessionManagerMetrics or GlobalSessionMetrics (for aggregate stats)
        """
        request_metrics_name = RequestScopedSessionMetrics.__name__
        shared_metrics_name = SharedSessionMetrics.__name__
        print(f'\n[U+1F3F7][U+FE0F] NAMING ANALYSIS:')
        print(f'  Current RequestScoped class name: {request_metrics_name}')
        print(f'  Current Shared class name: {shared_metrics_name}')
        print(f"  PROBLEM: Both named 'SessionMetrics' - no differentiation")
        print(f'  SOLUTION: Use SessionLifecycleMetrics vs GlobalSessionMetrics')
        assert request_metrics_name != shared_metrics_name, f"NAMING VIOLATION: Both classes named '{request_metrics_name}' - this creates import confusion and violates SSOT principles"
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')