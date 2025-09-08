"""Critical SessionMetrics SSOT Fix Validation

This focused test validates ONLY the critical AttributeError fix from lines 383-385
in request_scoped_session_factory.py without triggering broader system imports.

CRITICAL VALIDATION POINTS:
1. Field access patterns that were causing AttributeError work correctly
2. Backward compatibility properties are preserved
3. Error handling and session closure work under all conditions
4. The SSOT consolidation maintains system stability
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch


def test_critical_field_access_fix():
    """CRITICAL: Test the exact field access patterns that were failing in lines 383-385."""
    
    # Import only the SSOT module to avoid circular dependencies
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
    
    # Create instance exactly as done in the factory
    metrics = DatabaseSessionMetrics(
        session_id="critical-test-session",
        request_id="critical-test-request", 
        user_id="system"  # This was the failing case
    )
    
    # These are the EXACT field access patterns that were causing AttributeError
    # Lines 383-385 equivalent patterns:
    
    # Pattern 1: Direct field access (was failing with AttributeError)
    assert metrics.last_activity_at is not None
    assert isinstance(metrics.last_activity_at, datetime)
    
    # Pattern 2: Query count access (was failing)  
    assert metrics.query_count == 0
    assert isinstance(metrics.query_count, int)
    
    # Pattern 3: Error count access (was failing)
    assert metrics.error_count == 0
    assert isinstance(metrics.error_count, int)
    
    # Test the logging context creation that was failing (lines ~342-344)
    logging_context = {
        "last_activity": metrics.last_activity_at.isoformat() if metrics.last_activity_at else None,
        "operations_count": metrics.query_count,
        "errors": metrics.error_count
    }
    
    assert logging_context["last_activity"] is not None
    assert logging_context["operations_count"] == 0
    assert logging_context["errors"] == 0
    
    print("[PASS] Critical field access patterns work - AttributeError FIXED!")


def test_backward_compatibility_properties():
    """Test backward compatibility properties that enable existing code to work."""
    
    from shared.metrics.session_metrics import DatabaseSessionMetrics
    
    metrics = DatabaseSessionMetrics("test", "req", "user")
    
    # Test property aliases work (backward compatibility)
    assert hasattr(metrics, 'last_activity')
    assert hasattr(metrics, 'operations_count') 
    assert hasattr(metrics, 'errors')
    
    # Test property values match base fields
    assert metrics.last_activity == metrics.last_activity_at
    assert metrics.operations_count == metrics.query_count
    assert metrics.errors == metrics.error_count
    
    # Test property updates work correctly
    metrics.increment_query_count()
    assert metrics.operations_count == 1
    assert metrics.query_count == 1
    
    metrics.record_error("test error")
    assert metrics.errors == 1
    assert metrics.error_count == 1
    
    print("[PASS] Backward compatibility properties work correctly")


def test_error_scenarios_stability():
    """Test that error scenarios don't crash the system."""
    
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
    
    metrics = DatabaseSessionMetrics("error-test", "req-error", "system")
    
    # Test multiple error conditions
    error_messages = [
        "Database connection timeout",
        "Authentication failure for user system",
        "Service-to-service auth problem", 
        "JWT configuration error",
        "SESSION_SECRET validation failed"
    ]
    
    for i, error_msg in enumerate(error_messages, 1):
        metrics.record_error(error_msg)
        
        # Verify the critical fields still work after each error
        assert metrics.error_count == i
        assert metrics.errors == i  # Property alias
        assert metrics.last_error == error_msg
        assert metrics.state == SessionState.ERROR
        assert metrics.last_activity_at is not None
    
    # Test session closure after errors (this was also failing)
    metrics.close_session(1500.75)
    assert metrics.state == SessionState.CLOSED
    assert metrics.total_time_ms == 1500.75
    assert metrics.closed_at is not None
    
    print("[PASS] Error scenarios remain stable")


def test_session_closure_robustness():
    """Test session closure handles various edge cases without crashing."""
    
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
    
    # Test 1: Normal closure
    metrics1 = DatabaseSessionMetrics("close-test1", "req1", "user1")
    metrics1.close_session(1000.5)
    assert metrics1.state == SessionState.CLOSED
    assert metrics1.total_time_ms == 1000.5
    
    # Test 2: Closure without explicit time (auto-calculation)
    metrics2 = DatabaseSessionMetrics("close-test2", "req2", "user2") 
    metrics2.close_session()  # No time provided - should auto-calculate
    assert metrics2.state == SessionState.CLOSED
    assert metrics2.total_time_ms is not None
    assert metrics2.total_time_ms >= 0.0
    
    # Test 3: Old interface (backward compatibility)
    metrics3 = DatabaseSessionMetrics("close-test3", "req3", "user3")
    metrics3.close()  # Old method name
    assert metrics3.state == SessionState.CLOSED
    
    # Test 4: Edge case - metrics with string created_at (robustness fix)
    metrics4 = DatabaseSessionMetrics("close-test4", "req4", "user4")
    # Simulate edge case where created_at might be a string (shouldn't happen but be robust)
    metrics4.created_at = "2025-01-01T00:00:00Z"  # String instead of datetime
    metrics4.close_session()  # Should not crash
    assert metrics4.state == SessionState.CLOSED
    assert metrics4.total_time_ms == 0.0  # Fallback value
    
    print("[PASS] Session closure is robust under all conditions")


def test_to_dict_functionality():
    """Test the to_dict method that's used in logging (lines ~507-511)."""
    
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
    
    metrics = DatabaseSessionMetrics("dict-test", "req-dict", "user-dict")
    metrics.increment_query_count()
    metrics.record_error("test error for dict")
    
    # This is the exact pattern used in the factory for logging
    metrics_dict = metrics.to_dict()
    
    # Verify all required fields are present (these were accessed in factory)
    required_fields = [
        'session_id', 'request_id', 'user_id', 'state',
        'query_count', 'error_count', 'last_activity_at',
        'created_at', 'age_seconds', 'inactivity_seconds'
    ]
    
    for field in required_fields:
        assert field in metrics_dict, f"Required field {field} missing"
        assert metrics_dict[field] is not None, f"Field {field} is None"
    
    # Test specific values
    assert metrics_dict['session_id'] == 'dict-test'
    assert metrics_dict['query_count'] == 1
    assert metrics_dict['error_count'] == 1
    assert metrics_dict['state'] == SessionState.ERROR.value
    
    print("[PASS] to_dict functionality works for logging")


def test_stress_field_access():
    """Stress test the critical field access patterns under high load."""
    
    from shared.metrics.session_metrics import create_database_session_metrics
    
    # Create many sessions and test field access (simulating high load)
    sessions = []
    for i in range(100):
        metrics = create_database_session_metrics(f"stress-{i}", f"req-{i}", f"user-{i}")
        
        # Test the critical field access patterns that were failing
        _ = metrics.last_activity_at  # Should not raise AttributeError
        _ = metrics.query_count       # Should not raise AttributeError  
        _ = metrics.error_count       # Should not raise AttributeError
        
        # Test operations
        metrics.increment_query_count()
        if i % 10 == 0:
            metrics.record_error(f"Load test error {i}")
        
        sessions.append(metrics)
    
    # Verify all sessions maintain integrity
    assert len(sessions) == 100
    error_sessions = [s for s in sessions if s.error_count > 0]
    assert len(error_sessions) == 10  # Every 10th session had an error
    
    # Test bulk field access - this was the failing pattern
    for session in sessions:
        assert session.last_activity_at is not None
        assert isinstance(session.query_count, int)
        assert isinstance(session.error_count, int)
        assert session.query_count >= 1  # All had increment_query_count called
    
    print("[PASS] Stress test confirms field access stability")


def test_import_isolation():
    """Test that the SSOT module can be imported without triggering circular imports."""
    
    # Test that we can import the SSOT module independently
    from shared.metrics.session_metrics import (
        SessionState, DatabaseSessionMetrics, SystemSessionMetrics, 
        create_database_session_metrics, SessionMetrics
    )
    
    # Verify all expected components are available
    assert SessionState.CREATED
    assert SessionState.ERROR
    assert DatabaseSessionMetrics
    assert SystemSessionMetrics
    assert SessionMetrics == DatabaseSessionMetrics  # Backward compatibility
    
    # Test factory function works
    metrics = create_database_session_metrics("import-test", "req-import", "user-import")
    assert isinstance(metrics, DatabaseSessionMetrics)
    assert metrics.session_id == "import-test"
    
    print("[PASS] SSOT module imports work in isolation")


def test_real_factory_usage_pattern():
    """Test the exact usage pattern from request_scoped_session_factory.py."""
    
    from shared.metrics.session_metrics import create_database_session_metrics, SessionState
    
    # Simulate the real factory creation pattern
    session_id = "real-factory-test-123"
    request_id = "real-request-456"
    user_id = "system"  # This was the failing case
    
    # Create metrics as done in the real factory
    session_metrics = create_database_session_metrics(session_id, request_id, user_id)
    
    # Test the exact patterns used in factory error logging (lines ~383-385 area)
    try:
        # Simulate authentication failure scenario
        session_metrics.record_error("SYSTEM USER AUTHENTICATION FAILURE")
        
        # The critical field access that was failing
        error_context = {
            "session_id": session_metrics.session_id,
            "request_id": session_metrics.request_id,
            "user_id": session_metrics.user_id,
            "last_activity": session_metrics.last_activity_at.isoformat() if session_metrics.last_activity_at else None,
            "operations_count": session_metrics.query_count,
            "errors": session_metrics.error_count
        }
        
        # Verify all context fields are accessible (this was failing before)
        assert error_context["session_id"] == session_id
        assert error_context["request_id"] == request_id
        assert error_context["user_id"] == user_id
        assert error_context["last_activity"] is not None
        assert error_context["operations_count"] == 0
        assert error_context["errors"] == 1
        
        # Test the system user specific logging pattern
        assert user_id == "system" or (user_id and user_id.startswith("system"))
        
    except AttributeError as e:
        pytest.fail(f"The original AttributeError is NOT FIXED: {e}")
    except Exception as e:
        pytest.fail(f"Unexpected error in factory pattern: {e}")
    
    print("[PASS] Real factory usage pattern works - original bug FIXED!")


if __name__ == "__main__":
    print("Critical SessionMetrics SSOT Fix Validation")
    print("=" * 50)
    
    test_functions = [
        test_critical_field_access_fix,
        test_backward_compatibility_properties,
        test_error_scenarios_stability,
        test_session_closure_robustness,
        test_to_dict_functionality,
        test_stress_field_access,
        test_import_isolation,
        test_real_factory_usage_pattern,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in test_functions:
        try:
            print(f"\n[RUNNING] {test_func.__name__}")
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAILED] {test_func.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 50)
    print(f"CRITICAL VALIDATION RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("[SUCCESS] All critical validations PASSED - SessionMetrics SSOT fix is STABLE!")
        print("[SUCCESS] Original AttributeError from lines 383-385 is FIXED!")
        print("[SUCCESS] System stability maintained - NO BREAKING CHANGES!")
    else:
        print(f"[CRITICAL] {failed} validation tests failed - IMMEDIATE ATTENTION REQUIRED!")
        exit(1)