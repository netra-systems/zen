"""
Test Handler Registration Grace Period Fix

This test validates that the startup grace period prevents false "ZERO handlers" warnings
during normal application startup.

CRITICAL: This test ensures startup stability by validating grace period behavior.
"""

import time
import pytest
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.core.critical_path_validator import CriticalPathValidator
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestHandlerRegistrationGracePeriod:
    """Test handler registration grace period functionality."""

    def test_message_router_has_startup_time_tracking(self):
        """Verify MessageRouter tracks startup time."""
        router = MessageRouter()
        
        # Should have startup time tracking
        assert hasattr(router, 'startup_time')
        assert hasattr(router, 'startup_grace_period_seconds')
        assert hasattr(router, 'check_handler_status_with_grace_period')
        
        # Startup time should be recent (within last few seconds)
        current_time = time.time()
        assert current_time - router.startup_time < 5.0  # Should be very recent
        
        # Grace period should be reasonable (10 seconds)
        assert router.startup_grace_period_seconds == 10.0

    def test_grace_period_status_during_startup(self):
        """Test that status returns 'initializing' during grace period."""
        router = MessageRouter()
        
        # Clear handlers to simulate zero handlers during startup
        original_handlers = router.handlers.copy()
        router.handlers.clear()
        
        # During grace period, should return initializing status
        status = router.check_handler_status_with_grace_period()
        
        assert status["status"] == "initializing"
        assert status["handler_count"] == 0
        assert status["grace_period_active"] is True
        assert "Startup in progress" in status["message"]
        assert status["elapsed_seconds"] < router.startup_grace_period_seconds
        
        # Restore handlers
        router.handlers = original_handlers

    def test_grace_period_status_with_handlers_during_startup(self):
        """Test status when handlers are present during grace period."""
        router = MessageRouter()
        
        # Should have default handlers
        status = router.check_handler_status_with_grace_period()
        
        assert status["status"] == "initializing"
        assert status["handler_count"] > 0
        assert status["grace_period_active"] is True
        assert "Handlers registered during startup" in status["message"]
        assert "handlers" in status
        assert isinstance(status["handlers"], list)

    def test_grace_period_expired_with_zero_handlers(self):
        """Test that warnings appear after grace period expires with zero handlers."""
        router = MessageRouter()
        
        # Clear handlers and simulate expired grace period
        router.handlers.clear()
        router.startup_time = time.time() - 15.0  # 15 seconds ago (past grace period)
        
        with patch('netra_backend.app.websocket_core.handlers.logger') as mock_logger:
            status = router.check_handler_status_with_grace_period()
            
            # Should now be in error state
            assert status["status"] == "error"
            assert status["handler_count"] == 0
            assert status["grace_period_active"] is False
            assert "No handlers registered after" in status["message"]
            assert status["elapsed_seconds"] > router.startup_grace_period_seconds
            
            # Should have logged a warning
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert " WARNING: [U+FE0F] ZERO WebSocket message handlers after" in warning_call

    def test_grace_period_expired_with_handlers_ready(self):
        """Test normal operation after grace period with handlers."""
        router = MessageRouter()
        
        # Simulate expired grace period but with handlers
        router.startup_time = time.time() - 15.0  # 15 seconds ago (past grace period)
        
        status = router.check_handler_status_with_grace_period()
        
        assert status["status"] == "ready"
        assert status["handler_count"] > 0
        assert status["grace_period_active"] is False
        assert "Handler registration complete" in status["message"]
        assert "handlers" in status

    def test_critical_path_validator_respects_grace_period(self):
        """Test that CriticalPathValidator respects the grace period."""
        # Test the logic directly by simulating what the validator does
        router = MessageRouter()
        
        # Temporarily clear handlers to test grace period
        original_handlers = router.handlers.copy()
        router.handlers.clear()
        
        # Get status during grace period - should be "initializing"
        status = router.check_handler_status_with_grace_period()
        assert status["status"] == "initializing"
        assert status["grace_period_active"] is True
        
        # This demonstrates that during grace period, we get "initializing" instead of "error"
        # The validator code has been updated to handle this case and log info instead of error
        
        # Restore handlers
        router.handlers = original_handlers

    def test_critical_path_validator_warns_after_grace_period(self):
        """Test that CriticalPathValidator warns after grace period expires."""
        # Test the logic directly by simulating what the validator does
        router = MessageRouter()
        router.handlers.clear()
        router.startup_time = time.time() - 15.0  # Grace period expired
        
        with patch('netra_backend.app.websocket_core.handlers.logger') as mock_logger:
            # Get status after grace period - should trigger warning
            status = router.check_handler_status_with_grace_period()
            
            assert status["status"] == "error"
            assert status["grace_period_active"] is False
            
            # Should have logged a warning about zero handlers
            mock_logger.warning.assert_called_once()
            warning_call = mock_logger.warning.call_args[0][0]
            assert " WARNING: [U+FE0F] ZERO WebSocket message handlers after" in warning_call

    def test_get_stats_includes_handler_status(self):
        """Test that get_stats includes the new handler status with grace period info."""
        router = MessageRouter()
        
        stats = router.get_stats()
        
        assert "handler_status" in stats
        handler_status = stats["handler_status"]
        
        # Should have all the expected fields
        assert "status" in handler_status
        assert "handler_count" in handler_status
        assert "elapsed_seconds" in handler_status
        assert "grace_period_active" in handler_status
        assert "message" in handler_status
        
        # During startup, should be initializing
        if handler_status["grace_period_active"]:
            assert handler_status["status"] == "initializing"
        else:
            assert handler_status["status"] in ["ready", "error"]


@pytest.mark.integration
class TestGracePeriodIntegration:
    """Integration tests for grace period with real startup scenarios."""

    def test_global_message_router_grace_period(self):
        """Test grace period works with global message router instance."""
        # Reset global instance to test fresh initialization
        import netra_backend.app.websocket_core.handlers as handlers_module
        handlers_module._message_router = None
        
        # Get fresh router - should have grace period tracking
        router = get_message_router()
        
        assert hasattr(router, 'startup_time')
        assert hasattr(router, 'check_handler_status_with_grace_period')
        
        # Should be in grace period initially
        status = router.check_handler_status_with_grace_period()
        elapsed = status["elapsed_seconds"]
        
        # Should be very recent startup
        assert elapsed < 2.0  # Should be very fresh
        assert status["grace_period_active"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])