"""Test to verify health monitoring fixes are working correctly."""

import pytest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch


class TestHealthMonitoringFixVerification:
    """Verify the health monitoring fixes work correctly."""
    
    def test_correct_health_import_from_unified_checker(self):
        """Test that we can correctly import backend_health_checker."""
        # This should work after the fix
        from netra_backend.app.core.health.unified_health_checker import backend_health_checker
        assert backend_health_checker is not None
        
        # The backend_health_checker is the SSOT for health status
        assert hasattr(backend_health_checker, '__class__')
    
    @pytest.mark.asyncio
    async def test_monitoring_integration_no_errors(self):
        """Test that monitoring integration doesn't have import or undefined variable errors."""
        # Create a mock environment for the function
        mock_logger = MagicMock()
        mock_logger.info = MagicMock()
        mock_logger.debug = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.error = MagicMock()
        
        # Mock the chat_event_monitor
        mock_monitor = MagicMock()
        mock_monitor.start_monitoring = AsyncMock(return_value=None)
        
        # Mock get_agent_websocket_bridge
        mock_get_bridge = MagicMock(return_value=None)
        
        # Mock backend_health_checker
        mock_health_checker = MagicMock()
        mock_health_checker.component_health = {}
        
        with patch('netra_backend.app.startup_module.central_logger.get_logger', return_value=mock_logger):
            with patch('netra_backend.app.websocket_core.event_monitor.chat_event_monitor', mock_monitor):
                with patch('netra_backend.app.services.agent_websocket_bridge.get_agent_websocket_bridge', mock_get_bridge):
                    with patch('netra_backend.app.core.health.unified_health_checker.backend_health_checker', mock_health_checker):
                        # Import the function after patching
                        from netra_backend.app.startup_module import initialize_monitoring_integration
                        
                        # Call the function - should not raise any errors
                        result = await initialize_monitoring_integration()
                        
                        # The function should return True (successful)
                        assert result == True
                        
                        # Verify no errors about undefined 'bridge' variable
                        error_calls = [str(call) for call in mock_logger.warning.call_args_list]
                        bridge_errors = [msg for msg in error_calls if 'bridge' in msg.lower() and 'not defined' in msg.lower()]
                        assert len(bridge_errors) == 0, f"Found undefined bridge errors: {bridge_errors}"
                        
                        # Verify no import errors for health_interface
                        import_errors = [msg for msg in error_calls if 'health_interface' in msg.lower()]
                        assert len(import_errors) == 0, f"Found health_interface import errors: {import_errors}"
    
    def test_no_legacy_bridge_registration(self):
        """Verify that the legacy bridge registration code has been removed."""
        # Read the startup_module code
        with open('netra_backend/app/startup_module.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # The problematic code that used undefined 'bridge' variable should not exist
        assert 'await chat_event_monitor.register_component_for_monitoring(' not in content
        assert 'bridge' not in content or 'websocket_bridge' in content.lower()  # Only allowed in proper context
        
        # The fixed code should be present
        assert 'CRITICAL FIX: Removed legacy bridge registration code' in content
        assert 'per-request bridges work independently' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])