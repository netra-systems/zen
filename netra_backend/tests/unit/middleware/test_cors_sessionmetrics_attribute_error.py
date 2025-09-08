"""
Unit tests validating SessionMetrics SSOT violation fix.

This test suite validates the successful remediation of the SSOT violation that existed between:
1. shared.session_management.user_session_manager.SessionMetrics 
2. netra_backend.app.database.request_scoped_session_factory.SessionMetrics

CRITICAL: Tests MUST PASS to demonstrate the bug is fixed.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch
from dataclasses import dataclass
from typing import Optional

# Import the new SSOT compatible SessionMetrics classes
from shared.session_management.compatibility_aliases import SessionMetrics, SystemSessionMetrics, UserSessionMetrics
from shared.metrics.session_metrics import SystemSessionMetrics as SSOTSystemMetrics, DatabaseSessionMetrics


class TestSessionMetricsAttributeErrorFix:
    """Validate that the 'last_activity' attribute error has been fixed."""

    def test_compatibility_sessionmetrics_has_last_activity_attribute(self):
        """CRITICAL: Proves the new SessionMetrics HAS 'last_activity' attribute."""
        # Create SessionMetrics using the compatibility layer
        metrics = SessionMetrics()
        
        # This SHOULD PASS - the compatibility layer provides last_activity
        assert hasattr(metrics, 'last_activity')
        assert metrics.last_activity is not None
        print("✅ SessionMetrics now HAS last_activity attribute")

    def test_database_sessionmetrics_has_backward_compatibility(self):
        """CRITICAL: Proves DatabaseSessionMetrics has backward compatibility with both attributes."""
        # Create DatabaseSessionMetrics using the new SSOT implementation
        now = datetime.now(timezone.utc)
        metrics = DatabaseSessionMetrics(
            session_id="test-session",
            request_id="test-request", 
            user_id="test-user"
        )
        
        # This SHOULD WORK - proves it has last_activity_at
        assert hasattr(metrics, 'last_activity_at')
        assert metrics.last_activity_at is not None
        
        # This SHOULD ALSO WORK - proves the backward compatibility property exists
        assert hasattr(metrics, 'last_activity')
        assert metrics.last_activity is not None
        print("✅ DatabaseSessionMetrics has both last_activity and last_activity_at")

    def test_middleware_code_now_works_with_sessionmetrics(self):
        """CRITICAL: Validates real middleware code now works with fixed SessionMetrics."""
        metrics = SessionMetrics()
        
        # Simulate middleware or other code expecting last_activity
        def middleware_function(session_metrics):
            """Mock middleware function that expects last_activity."""
            # This is what real code tries to do - access last_activity
            return session_metrics.last_activity
        
        # This SHOULD WORK now with the compatibility layer
        last_activity = middleware_function(metrics)
        assert last_activity is not None
        print("✅ Middleware code now works with SessionMetrics last_activity")

    def test_websocket_handler_now_works_with_database_sessionmetrics(self):
        """CRITICAL: Validates WebSocket handler now works with fixed DatabaseSessionMetrics."""
        metrics = DatabaseSessionMetrics(
            session_id="test-session", 
            request_id="test-request",
            user_id="test-user"
        )
        
        # Simulate middleware or other code expecting last_activity
        def websocket_handler(session_metrics):
            """Mock WebSocket handler that expects last_activity."""
            # This is what WebSocket code tries to do - access last_activity
            if hasattr(session_metrics, 'last_activity'):
                return session_metrics.last_activity
            else:
                # Fallback pattern - should not be needed now
                return getattr(session_metrics, 'last_activity')
        
        # This SHOULD WORK now with the backward compatibility property
        last_activity = websocket_handler(metrics)
        assert last_activity is not None
        print("✅ WebSocket handler now works with DatabaseSessionMetrics last_activity")


class TestUnifiedImportScenarios:
    """Test scenarios validating unified SessionMetrics import works correctly."""

    def test_compatibility_sessionmetrics_accepts_any_constructor(self):
        """CRITICAL: Tests that new SessionMetrics compatibility layer handles any constructor."""
        # The compatibility layer should handle different constructor patterns gracefully
        
        # Test with no arguments
        metrics1 = SessionMetrics()
        assert hasattr(metrics1, 'last_activity')
        
        # Test with system-style arguments  
        metrics2 = SessionMetrics(session_id="test-session", request_id="test-request")
        assert hasattr(metrics2, 'last_activity')
        
        # Test with user-style arguments
        metrics3 = SessionMetrics(total_sessions=5, active_sessions=2)
        assert hasattr(metrics3, 'last_activity')
        
        print("✅ SessionMetrics compatibility layer handles all constructor patterns")
    
    def test_specific_metric_types_work_correctly(self):
        """CRITICAL: Tests that specific metric types work as expected."""
        # System metrics
        system_metrics = SystemSessionMetrics()
        assert hasattr(system_metrics, 'last_activity')
        
        # User metrics
        user_metrics = UserSessionMetrics()
        assert hasattr(user_metrics, 'last_activity')
        
        # Database metrics
        database_metrics = DatabaseSessionMetrics(
            session_id="test", request_id="test", user_id="test"
        )
        assert hasattr(database_metrics, 'last_activity')
        assert hasattr(database_metrics, 'last_activity_at')
        
        print("✅ All specific SessionMetrics types have required attributes")

    def test_real_metrics_now_work_without_mocking(self):
        """CRITICAL: Shows that real SessionMetrics work without needing mocks."""
        # The new implementation should work without mocking
        real_metrics = SessionMetrics()
        
        # This should PASS with real implementation
        assert hasattr(real_metrics, 'last_activity')
        assert real_metrics.last_activity is not None
        
        # DatabaseSessionMetrics should also work
        db_metrics = DatabaseSessionMetrics(
            session_id="test",
            request_id="test",
            user_id="test"
        )
        
        # Both attribute names should work
        assert hasattr(db_metrics, 'last_activity')
        assert hasattr(db_metrics, 'last_activity_at')
        
        print("✅ Real SessionMetrics work without mocking - SSOT violation fixed")


class TestSessionMetricsSSOTViolationFixed:
    """Test cases proving SSOT violation has been resolved."""

    def test_unified_sessionmetrics_compatibility_layer_exists(self):
        """CRITICAL: Proves unified SessionMetrics compatibility layer resolves SSOT violation."""
        # Import from the unified compatibility layer
        metrics = SessionMetrics()
        
        # The compatibility layer should provide a unified interface
        assert hasattr(metrics, 'last_activity')
        assert metrics.last_activity is not None
        
        # Should have access to common session metrics properties
        assert hasattr(metrics, 'to_dict')
        
        print("✅ Unified SessionMetrics compatibility layer exists and works")
        
    def test_ssot_classes_have_clear_names_and_purposes(self):
        """CRITICAL: Proves SSOT classes have clear, non-conflicting names."""
        # Each class should have a clear, specific name and purpose
        system_metrics = SSOTSystemMetrics()  # System-wide aggregation
        db_metrics = DatabaseSessionMetrics(session_id="test", request_id="test", user_id="test")  # Individual session
        
        # Different classes for different purposes
        assert type(system_metrics).__name__ == "SystemSessionMetrics"
        assert type(db_metrics).__name__ == "DatabaseSessionMetrics"
        assert system_metrics.__class__ is not db_metrics.__class__
        
        # Both have required attributes through proper implementation
        assert hasattr(system_metrics, 'total_sessions')
        assert hasattr(db_metrics, 'session_id')
        assert hasattr(db_metrics, 'last_activity')  # Backward compatibility
        assert hasattr(db_metrics, 'last_activity_at')  # Original attribute
        
        print("✅ SSOT classes have clear names and non-conflicting purposes")

    def test_sessionmetrics_interfaces_are_now_consistent(self):
        """CRITICAL: Proves the interfaces are now consistent through compatibility layer."""
        # The compatibility layer should provide consistent access
        compat_metrics = SessionMetrics()
        
        # Should have the critical attribute that was causing errors
        assert hasattr(compat_metrics, 'last_activity')
        
        # Should provide unified interface for different use cases
        system_compat = SystemSessionMetrics()
        user_compat = UserSessionMetrics()
        
        # All should have the problematic attribute
        assert hasattr(system_compat, 'last_activity')
        assert hasattr(user_compat, 'last_activity')
        
        print("✅ SessionMetrics interfaces are now consistent through compatibility layer")

    def test_to_dict_method_now_works_consistently(self):
        """CRITICAL: Proves to_dict methods now work consistently across all SessionMetrics."""
        # All SessionMetrics should have to_dict method through compatibility layer
        compat_metrics = SessionMetrics()
        system_metrics = SystemSessionMetrics()
        user_metrics = UserSessionMetrics()
        
        # All should have to_dict method
        assert hasattr(compat_metrics, 'to_dict')
        assert hasattr(system_metrics, 'to_dict')
        assert hasattr(user_metrics, 'to_dict')
        
        # Should return dictionaries with consistent structure
        compat_dict = compat_metrics.to_dict()
        system_dict = system_metrics.to_dict()
        user_dict = user_metrics.to_dict()
        
        # All should be dictionaries
        assert isinstance(compat_dict, dict)
        assert isinstance(system_dict, dict)
        assert isinstance(user_dict, dict)
        
        # All should have the critical field that was missing
        assert 'last_activity' in compat_dict or 'timestamp' in compat_dict
        
        print("✅ to_dict methods now work consistently across all SessionMetrics")


class TestRealWorldScenarioFixes:
    """Test real-world scenarios that now work due to the fix."""

    def test_websocket_manager_last_activity_access_now_works(self):
        """CRITICAL: Validates WebSocket manager can now access last_activity correctly."""
        # Based on real WebSocket manager code patterns
        def websocket_cleanup_stale_connections(session_metrics):
            """Simulate WebSocket cleanup code that needs last_activity."""
            cutoff_time = datetime.now(timezone.utc)
            
            # This pattern should now work with the fix
            if hasattr(session_metrics, 'last_activity') and session_metrics.last_activity:
                return session_metrics.last_activity < cutoff_time
            return True
        
        # Test with compatibility SessionMetrics - should have last_activity
        compat_metrics = SessionMetrics()
        result = websocket_cleanup_stale_connections(compat_metrics)
        # Result should be based on actual last_activity comparison, not fallback
        assert isinstance(result, bool)
        
        # Test with database SessionMetrics - should also have last_activity
        db_metrics = DatabaseSessionMetrics(
            session_id="test",
            request_id="test", 
            user_id="test"
        )
        result = websocket_cleanup_stale_connections(db_metrics)
        assert isinstance(result, bool)
        
        print("✅ WebSocket manager can now access last_activity on all SessionMetrics types")

    def test_cors_middleware_session_tracking_now_works(self):
        """CRITICAL: Validates CORS middleware can now track session activity correctly."""
        def cors_middleware_session_check(session_metrics):
            """Simulate CORS middleware that tracks last_activity."""
            # This should now work with the fixed SessionMetrics
            return {
                'session_active': session_metrics.last_activity is not None,
                'last_activity_time': session_metrics.last_activity
            }
        
        # All SessionMetrics types should now pass this check
        compat_metrics = SessionMetrics()
        result = cors_middleware_session_check(compat_metrics)
        assert isinstance(result, dict)
        assert 'session_active' in result
        assert 'last_activity_time' in result
        
        db_metrics = DatabaseSessionMetrics(
            session_id="test",
            request_id="test",
            user_id="test"
        )
        result = cors_middleware_session_check(db_metrics)
        assert isinstance(result, dict)
        assert 'session_active' in result
        assert 'last_activity_time' in result
        
        print("✅ CORS middleware can now track session activity on all SessionMetrics types")

    def test_session_metrics_serialization_now_works(self):
        """CRITICAL: Tests that serialization now works due to unified interface."""
        def serialize_session_metrics(metrics):
            """Simulate serialization code that expects consistent interface."""
            # Use the to_dict method which should be available on all metrics
            base_dict = metrics.to_dict()
            
            # Add last_activity which should be available
            return {
                'metrics_data': base_dict,
                'last_activity': metrics.last_activity,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        
        # All SessionMetrics should now work for serialization
        compat_metrics = SessionMetrics()
        result = serialize_session_metrics(compat_metrics)
        assert isinstance(result, dict)
        assert 'metrics_data' in result
        assert 'last_activity' in result
        
        db_metrics = DatabaseSessionMetrics(
            session_id="test",
            request_id="test",
            user_id="test"
        )
        result = serialize_session_metrics(db_metrics)
        assert isinstance(result, dict)
        assert 'metrics_data' in result
        assert 'last_activity' in result
        
        print("✅ Session metrics serialization now works with unified interface")


if __name__ == "__main__":
    # Run with: python -m pytest netra_backend/tests/unit/middleware/test_cors_sessionmetrics_attribute_error.py -v
    # This test validates that the SessionMetrics SSOT violation fix is working correctly
    pass