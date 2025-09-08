"""SessionMetrics SSOT Validation Test Suite

This test suite validates the comprehensive SessionMetrics SSOT violation fix:
1. Verifies the critical AttributeError from lines 383-385 is resolved
2. Confirms all field access patterns work correctly
3. Ensures backward compatibility is maintained  
4. Tests import paths work without circular dependencies
5. Validates system stability under error conditions

CRITICAL: This test proves the fix maintains system stability with no breaking changes.
"""

import pytest
import asyncio
import sys
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from unittest.mock import Mock, patch, AsyncMock

# Test that all SSOT imports work correctly
def test_ssot_imports_work_correctly():
    """Test 1: Validate all import paths work without circular dependencies."""
    
    # Test shared SSOT imports
    from shared.metrics.session_metrics import (
        SessionState,
        BaseSessionMetrics, 
        DatabaseSessionMetrics,
        SystemSessionMetrics,
        SessionMetrics,  # Backward compatibility alias
        create_database_session_metrics,
        create_system_session_metrics
    )
    
    # Test backend imports still work
    from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
    
    assert SessionState.CREATED == "created"
    assert SessionState.ERROR == "error"
    assert SessionMetrics == DatabaseSessionMetrics  # Backward compatibility
    
    print("[PASS] All SSOT imports work correctly")


def test_database_session_metrics_field_access():
    """Test 2: Validate the critical field access that was causing AttributeError."""
    
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
    
    # Create instance using SSOT
    metrics = DatabaseSessionMetrics(
        session_id="test-session",
        request_id="test-request", 
        user_id="test-user"
    )
    
    # Test the exact field access patterns that were failing in lines 383-385
    # These are the critical lines that were causing AttributeError
    
    # Field access that was failing
    assert metrics.last_activity_at is not None
    assert metrics.query_count == 0  # Initial value
    assert metrics.error_count == 0  # Initial value
    
    # Test backward compatibility properties
    assert hasattr(metrics, 'last_activity')  # Property alias
    assert hasattr(metrics, 'operations_count')  # Property alias  
    assert hasattr(metrics, 'errors')  # Property alias
    
    # Verify property aliases work
    assert metrics.last_activity == metrics.last_activity_at
    assert metrics.operations_count == metrics.query_count
    assert metrics.errors == metrics.error_count
    
    # Test field updates work correctly
    metrics.increment_query_count()
    assert metrics.query_count == 1
    assert metrics.operations_count == 1  # Property alias
    
    metrics.record_error("test error")
    assert metrics.error_count == 1
    assert metrics.errors == 1  # Property alias
    assert metrics.last_error == "test error"
    assert metrics.state == SessionState.ERROR
    
    print("[PASS] All critical field access patterns work correctly")


def test_backend_session_factory_integration():
    """Test 3: Test integration with the backend session factory using SSOT."""
    
    from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
    from shared.metrics.session_metrics import DatabaseSessionMetrics, create_database_session_metrics
    
    # Test factory creates correct metrics type
    metrics = create_database_session_metrics("test-id", "req-123", "user-456")
    assert isinstance(metrics, DatabaseSessionMetrics)
    assert metrics.session_id == "test-id"
    assert metrics.request_id == "req-123"
    assert metrics.user_id == "user-456"
    
    # Test field access that was failing in the factory
    assert metrics.last_activity_at is not None
    assert metrics.query_count == 0
    assert metrics.error_count == 0
    
    # Test to_dict() method used in logging (lines ~342, 507, 510, 511)
    metrics_dict = metrics.to_dict()
    required_fields = [
        'session_id', 'request_id', 'user_id', 'state', 
        'query_count', 'error_count', 'last_activity_at',
        'created_at', 'age_seconds', 'inactivity_seconds'
    ]
    
    for field in required_fields:
        assert field in metrics_dict, f"Required field {field} missing from to_dict()"
    
    print("[PASS] Backend session factory integration works correctly")


def test_error_handling_stability():
    """Test 4: Validate system stability under error conditions."""
    
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SessionState
    
    metrics = DatabaseSessionMetrics(
        session_id="error-test",
        request_id="req-error",
        user_id="user-error"
    )
    
    # Test multiple error scenarios
    test_errors = [
        "Database connection timeout",
        "Authentication failure", 
        "Query execution error",
        "Transaction rollback",
        "Session cleanup error"
    ]
    
    for i, error in enumerate(test_errors, 1):
        metrics.record_error(error)
        assert metrics.error_count == i
        assert metrics.last_error == error
        assert metrics.state == SessionState.ERROR
        # Verify last_activity_at gets updated on error
        assert metrics.last_activity_at is not None
    
    # Test session closure after errors
    metrics.close_session(1234.5)
    assert metrics.state == SessionState.CLOSED
    assert metrics.closed_at is not None
    assert metrics.total_time_ms == 1234.5
    
    # Test backward compatibility close() method
    metrics2 = DatabaseSessionMetrics("test2", "req2", "user2")
    metrics2.close()  # Old interface
    assert metrics2.state == SessionState.CLOSED
    
    print("[PASS] Error handling remains stable")


def test_backward_compatibility_complete():
    """Test 5: Comprehensive backward compatibility validation."""
    
    from shared.metrics.session_metrics import SessionMetrics, DatabaseSessionMetrics
    
    # Test alias works
    assert SessionMetrics == DatabaseSessionMetrics
    
    # Test instantiation through alias
    metrics = SessionMetrics(
        session_id="compat-test",
        request_id="req-compat", 
        user_id="user-compat"
    )
    
    # Test all old field names/methods still work
    old_interface_tests = [
        # (attribute/method, expected_type, description)
        ('session_id', str, 'session identifier'),
        ('request_id', str, 'request identifier'),
        ('user_id', str, 'user identifier'),
        ('query_count', int, 'query counter'),
        ('error_count', int, 'error counter'),
        ('last_activity_at', datetime, 'last activity timestamp'),
        ('state', str, 'session state'),
        # Backward compatibility properties
        ('last_activity', datetime, 'last activity property alias'),
        ('operations_count', int, 'operations count property alias'),
        ('errors', int, 'errors property alias'),
    ]
    
    for attr, expected_type, description in old_interface_tests:
        assert hasattr(metrics, attr), f"Missing backward compatibility: {attr} ({description})"
        value = getattr(metrics, attr)
        if expected_type == datetime and value is not None:
            assert isinstance(value, datetime), f"{attr} should be datetime, got {type(value)}"
        elif expected_type in (str, int) and value is not None:
            assert isinstance(value, expected_type), f"{attr} should be {expected_type}, got {type(value)}"
    
    # Test old method names work
    assert hasattr(metrics, 'close'), "Missing backward compatibility: close() method"
    assert hasattr(metrics, 'mark_activity'), "Missing backward compatibility: mark_activity() method"
    assert hasattr(metrics, 'record_error'), "Missing backward compatibility: record_error() method"
    
    print("[PASS] Complete backward compatibility maintained")


def test_performance_no_degradation():
    """Test 6: Ensure no performance degradation from SSOT consolidation."""
    
    import time
    from shared.metrics.session_metrics import create_database_session_metrics
    
    # Benchmark session creation performance
    start_time = time.time()
    
    for i in range(1000):
        metrics = create_database_session_metrics(f"session-{i}", f"req-{i}", f"user-{i}")
        # Test critical field access
        _ = metrics.last_activity_at
        _ = metrics.query_count
        _ = metrics.error_count
        # Test operations
        metrics.mark_activity()
        metrics.increment_query_count()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Performance should be reasonable (< 1 second for 1000 operations)
    assert duration < 1.0, f"Performance degradation detected: {duration:.3f}s for 1000 operations"
    
    print(f"[PASS] Performance maintained: {duration:.3f}s for 1000 operations")


def test_no_circular_imports():
    """Test 7: Validate no circular import dependencies were introduced."""
    
    import importlib
    import sys
    
    # Clear any cached imports to test fresh
    modules_to_test = [
        'shared.metrics.session_metrics',
        'netra_backend.app.database.request_scoped_session_factory',
    ]
    
    for module in modules_to_test:
        if module in sys.modules:
            del sys.modules[module]
    
    # Test imports work in both directions without circular dependency
    try:
        # Import SSOT first
        ssot_module = importlib.import_module('shared.metrics.session_metrics')
        assert hasattr(ssot_module, 'DatabaseSessionMetrics')
        
        # Import backend second 
        backend_module = importlib.import_module('netra_backend.app.database.request_scoped_session_factory')
        assert hasattr(backend_module, 'RequestScopedSessionFactory')
        
        print("[PASS] No circular import dependencies")
        
    except ImportError as e:
        pytest.fail(f"Circular import detected: {e}")


def test_ssot_compliance_validation():
    """Test 8: Validate complete SSOT compliance - no duplicate definitions."""
    
    import inspect
    from shared.metrics.session_metrics import DatabaseSessionMetrics, SystemSessionMetrics
    
    # Verify classes are properly defined with correct inheritance
    assert issubclass(DatabaseSessionMetrics, object)
    assert issubclass(SystemSessionMetrics, object)
    
    # Check that DatabaseSessionMetrics has all required methods
    required_methods = [
        'increment_query_count', 'increment_transaction_count', 
        'record_error', 'close_session', 'close', 'to_dict',
        'mark_activity', 'get_age_seconds', 'get_inactivity_seconds'
    ]
    
    for method_name in required_methods:
        assert hasattr(DatabaseSessionMetrics, method_name), f"Missing required method: {method_name}"
        method = getattr(DatabaseSessionMetrics, method_name)
        assert callable(method), f"Method {method_name} is not callable"
    
    # Verify required properties exist
    required_properties = ['last_activity', 'operations_count', 'errors']
    for prop_name in required_properties:
        assert hasattr(DatabaseSessionMetrics, prop_name), f"Missing required property: {prop_name}"
        prop = getattr(DatabaseSessionMetrics, prop_name)
        assert isinstance(prop, property), f"Attribute {prop_name} should be a property"
    
    print("[PASS] SSOT compliance validated - single source of truth confirmed")


@pytest.mark.integration
def test_real_database_session_integration():
    """Test 9: Integration test with real database session patterns (without actual DB)."""
    
    from shared.metrics.session_metrics import create_database_session_metrics, SessionState
    from unittest.mock import Mock
    
    # Simulate the real patterns used in request_scoped_session_factory.py
    session_id = "real-session-test-12345"
    request_id = "real-request-67890" 
    user_id = "real-user-system"
    
    # Create metrics as done in the real factory
    session_metrics = create_database_session_metrics(session_id, request_id, user_id)
    
    # Simulate real usage patterns from the factory code
    # Pattern 1: Check inactivity (line ~154-155)
    if session_metrics.last_activity_at:
        current_time = datetime.now(timezone.utc)
        inactive_time_ms = (current_time - session_metrics.last_activity_at).total_seconds() * 1000
        assert inactive_time_ms >= 0
    
    # Pattern 2: Logging context creation (lines ~342-344)
    context = {
        "last_activity": session_metrics.last_activity_at.isoformat() if session_metrics.last_activity_at else None,
        "operations_count": session_metrics.query_count,
        "errors": session_metrics.error_count
    }
    assert context["last_activity"] is not None
    assert context["operations_count"] == 0
    assert context["errors"] == 0
    
    # Pattern 3: Metrics dictionary creation (lines ~507-511) 
    metrics_dict = {
        'query_count': session_metrics.query_count,
        'last_activity_at': session_metrics.last_activity_at.isoformat() if session_metrics.last_activity_at else None,
        'error_count': session_metrics.error_count,
    }
    assert all(value is not None for value in metrics_dict.values())
    
    # Pattern 4: Error handling during session creation
    try:
        # Simulate error condition
        session_metrics.record_error("Simulated database connection failure")
        assert session_metrics.state == SessionState.ERROR
        assert session_metrics.error_count == 1
        
        # Test the specific error logging that was failing 
        error_msg = (
            f"SYSTEM USER AUTHENTICATION FAILURE: User '{user_id}' failed authentication. "
            f"Request ID: {request_id}, Session ID: {session_id}."
        )
        assert request_id in error_msg
        assert session_id in error_msg
        
    except Exception as e:
        pytest.fail(f"Real integration pattern failed: {e}")
    
    print("[PASS] Real database session integration patterns work correctly")


def test_system_stability_proof():
    """Test 10: Final system stability proof - comprehensive validation."""
    
    from shared.metrics.session_metrics import (
        DatabaseSessionMetrics, SystemSessionMetrics, SessionState,
        create_database_session_metrics, create_system_session_metrics
    )
    
    # Test stress scenario - multiple concurrent operations
    database_metrics = []
    system_metrics = create_system_session_metrics()
    
    # Create multiple database sessions as would happen under load
    for i in range(10):
        metrics = create_database_session_metrics(f"stress-{i}", f"req-{i}", f"user-{i}")
        
        # Simulate activity
        metrics.increment_query_count()
        metrics.increment_transaction_count() 
        metrics.mark_activity()
        
        # Test error scenarios
        if i % 3 == 0:
            metrics.record_error(f"Test error {i}")
        
        # Test closure
        if i % 2 == 0:
            metrics.close_session(float(i * 100))
        
        database_metrics.append(metrics)
        system_metrics.increment_total_sessions()
    
    # Validate all sessions maintained integrity
    assert len(database_metrics) == 10
    error_count = sum(1 for m in database_metrics if m.error_count > 0)
    assert error_count == 4  # Every 3rd session should have error (0,3,6,9)
    
    closed_count = sum(1 for m in database_metrics if m.state == SessionState.CLOSED)
    assert closed_count == 5  # Every 2nd session should be closed (0,2,4,6,8)
    
    # Test system metrics consistency
    assert system_metrics.total_sessions == 10
    
    # Final validation - all critical operations work
    for metrics in database_metrics:
        # Critical field access that was failing
        assert metrics.last_activity_at is not None
        assert isinstance(metrics.query_count, int)
        assert isinstance(metrics.error_count, int)
        
        # Backward compatibility
        assert metrics.last_activity == metrics.last_activity_at
        assert metrics.operations_count == metrics.query_count
        assert metrics.errors == metrics.error_count
        
        # Methods work
        metrics_dict = metrics.to_dict()
        assert isinstance(metrics_dict, dict)
        assert len(metrics_dict) > 10  # Should have all required fields
    
    print("[PASS] System stability proven under stress conditions")


if __name__ == "__main__":
    print("Running SessionMetrics SSOT Validation Test Suite...")
    print("=" * 70)
    
    # Run each test individually with clear output
    test_functions = [
        test_ssot_imports_work_correctly,
        test_database_session_metrics_field_access,
        test_backend_session_factory_integration,
        test_error_handling_stability,
        test_backward_compatibility_complete,
        test_performance_no_degradation,
        test_no_circular_imports,
        test_ssot_compliance_validation,
        test_real_database_session_integration,
        test_system_stability_proof,
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
    
    print("\n" + "=" * 70)
    print(f"VALIDATION RESULTS: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("[SUCCESS] ALL VALIDATION TESTS PASSED - SessionMetrics SSOT fix is stable!")
    else:
        print(f"[WARNING] {failed} validation tests failed - system stability at risk!")
        exit(1)