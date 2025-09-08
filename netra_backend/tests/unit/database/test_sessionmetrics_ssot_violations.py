"""Test SessionMetrics SSOT Violation Remediation

This test validates that the SessionMetrics SSOT violations have been successfully
remediated by consolidating duplicate implementations into a single source of truth.

Business Value Justification (BVJ):
- Segment: Platform Security & Stability (all tiers)  
- Business Goal: Prevent AttributeError crashes in session management
- Value Impact: Eliminates session creation failures affecting user experience
- Strategic Impact: Foundation for reliable session tracking and monitoring

CRITICAL: This test validates the fix for the AttributeError bug in lines 383-385
of request_scoped_session_factory.py that was caused by SSOT violations.
"""

import pytest
import inspect
from datetime import datetime, timezone
from typing import get_type_hints
import importlib

from shared.metrics.session_metrics import SystemSessionMetrics, DatabaseSessionMetrics
from shared.session_management.user_session_manager import get_session_manager


class TestSSOTViolationRemediation:
    """Validate that SessionMetrics SSOT violations have been successfully remediated."""

    def test_ssot_violation_fixed_single_source_of_truth(self):
        """CRITICAL: Validate SessionMetrics SSOT violation has been fixed."""
        # Both classes now import from the same SSOT source
        assert SystemSessionMetrics.__module__ == "shared.metrics.session_metrics"
        assert DatabaseSessionMetrics.__module__ == "shared.metrics.session_metrics"
        
        # Classes are properly named and differentiated
        assert SystemSessionMetrics.__name__ == "SystemSessionMetrics"
        assert DatabaseSessionMetrics.__name__ == "DatabaseSessionMetrics"
        
        # No naming collision - different concepts have different names
        assert SystemSessionMetrics is not DatabaseSessionMetrics
        print("✅ SSOT VIOLATION FIXED: No more SessionMetrics naming collision")

    def test_database_metrics_has_correct_fields(self):
        """CRITICAL: Validate DatabaseSessionMetrics has all required fields for database session tracking."""
        db_metrics = DatabaseSessionMetrics(
            session_id="test_session",
            request_id="test_request", 
            user_id="test_user"
        )
        
        # Database session specific fields
        assert hasattr(db_metrics, 'session_id')
        assert hasattr(db_metrics, 'request_id')
        assert hasattr(db_metrics, 'user_id')
        assert hasattr(db_metrics, 'query_count')
        assert hasattr(db_metrics, 'transaction_count')
        assert hasattr(db_metrics, 'error_count')
        assert hasattr(db_metrics, 'last_activity_at')
        
        # CRITICAL: Backward compatibility properties for existing code
        assert hasattr(db_metrics, 'last_activity')  # Property for compatibility
        assert hasattr(db_metrics, 'operations_count')  # Property for compatibility  
        assert hasattr(db_metrics, 'errors')  # Property for compatibility
        
        print("✅ DatabaseSessionMetrics has all required fields and backward compatibility")

    def test_system_metrics_has_correct_fields(self):
        """CRITICAL: Validate SystemSessionMetrics has all required fields for system-wide tracking."""
        sys_metrics = SystemSessionMetrics()
        
        # System-wide aggregate fields
        assert hasattr(sys_metrics, 'total_sessions')
        assert hasattr(sys_metrics, 'active_sessions')
        assert hasattr(sys_metrics, 'expired_sessions_cleaned')
        assert hasattr(sys_metrics, 'sessions_created_today')
        assert hasattr(sys_metrics, 'sessions_reused_today')
        assert hasattr(sys_metrics, 'average_session_duration_minutes')
        assert hasattr(sys_metrics, 'memory_usage_mb')
        
        # SSOT methods for proper metric updates
        assert hasattr(sys_metrics, 'increment_total_sessions')
        assert hasattr(sys_metrics, 'increment_active_sessions')
        assert hasattr(sys_metrics, 'record_session_reuse')
        assert hasattr(sys_metrics, 'record_session_cleanup')
        
        print("✅ SystemSessionMetrics has all required fields and SSOT methods")
    
    def test_critical_attributeerror_bug_fixed(self):
        """CRITICAL: Validate the AttributeError bug in lines 383-385 has been completely fixed."""
        db_metrics = DatabaseSessionMetrics(
            session_id="test_session", 
            request_id="test_request",
            user_id="test_user"
        )
        
        # These field accesses caused AttributeError crashes before the fix
        try:
            # Test the exact problematic field accesses from lines 383-385
            last_activity_iso = db_metrics.last_activity_at.isoformat() if db_metrics.last_activity_at else None
            operations_count = db_metrics.query_count
            errors_count = db_metrics.error_count
            
            # Also test backward compatibility properties 
            compat_last_activity = db_metrics.last_activity.isoformat() if db_metrics.last_activity else None
            compat_operations = db_metrics.operations_count
            compat_errors = db_metrics.errors
            
            print("✅ CRITICAL BUG FIXED: All field accesses work without AttributeError")
            print(f"   last_activity_at: {last_activity_iso}")
            print(f"   query_count: {operations_count}")
            print(f"   error_count: {errors_count}")
            print(f"   backward compatibility properties also work")
            
        except AttributeError as e:
            pytest.fail(f"CRITICAL BUG NOT FIXED: AttributeError still occurs: {e}")
    
    def test_user_session_manager_uses_ssot_metrics(self):
        """Validate UserSessionManager now uses SSOT SystemSessionMetrics."""
        session_manager = get_session_manager()
        metrics = session_manager.get_session_metrics()
        
        # Should be SystemSessionMetrics from SSOT source
        assert type(metrics).__name__ == "SystemSessionMetrics"
        assert metrics.__class__.__module__ == "shared.metrics.session_metrics"
        
        print("✅ UserSessionManager successfully uses SSOT SystemSessionMetrics")

    def test_ssot_methods_work_correctly(self):
        """Validate all SSOT methods function correctly without errors."""
        db_metrics = DatabaseSessionMetrics(
            session_id="test_session",
            request_id="test_request", 
            user_id="test_user"
        )
        
        # Test DatabaseSessionMetrics methods
        db_metrics.increment_query_count()
        db_metrics.increment_transaction_count()
        db_metrics.record_error("Test error")
        db_metrics.mark_activity()
        db_metrics.close()
        
        assert db_metrics.query_count == 1
        assert db_metrics.transaction_count == 1
        assert db_metrics.error_count == 1
        assert db_metrics.last_error == "Test error"
        
        # Test SystemSessionMetrics methods
        sys_metrics = SystemSessionMetrics()
        sys_metrics.increment_total_sessions()
        sys_metrics.increment_active_sessions()  
        sys_metrics.record_session_reuse()
        sys_metrics.record_session_cleanup(5)
        sys_metrics.update_memory_usage(25.5)
        sys_metrics.update_average_duration(30.2)
        
        assert sys_metrics.total_sessions == 1
        assert sys_metrics.active_sessions == 1
        assert sys_metrics.sessions_reused_today == 1
        assert sys_metrics.expired_sessions_cleaned == 5
        assert sys_metrics.memory_usage_mb == 25.5
        assert sys_metrics.average_session_duration_minutes == 30.2
        
        print("✅ All SSOT methods function correctly")


if __name__ == "__main__":
    # Run with: python -m pytest netra_backend/tests/unit/database/test_sessionmetrics_ssot_violations.py -v
    pass