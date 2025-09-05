"""
Test to verify that WebSocket warnings have been properly downgraded to INFO level.
This test validates that the legacy pattern warnings no longer appear as warnings.
"""

import asyncio
import logging
from unittest.mock import MagicMock, patch
import pytest
from netra_backend.app.core.startup_validation import StartupValidator
from netra_backend.app.core.startup_validation_fix import StartupValidationFixer


class TestWebSocketWarningsFix:
    """Test that legacy WebSocket warnings are now INFO level."""
    
    @pytest.mark.asyncio
    async def test_websocket_handler_warning_is_info_level(self):
        """Test that zero WebSocket handlers logs as INFO, not WARNING."""
        validator = StartupValidator()
        
        # Mock app with WebSocket manager but no handlers
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        mock_ws_manager = MagicMock()
        mock_ws_manager.message_handlers = []  # Zero handlers
        mock_ws_manager.active_connections = []
        mock_app.state.websocket_manager = mock_ws_manager
        
        # Capture log output
        with patch.object(validator.logger, 'info') as mock_info:
            with patch.object(validator.logger, 'warning') as mock_warning:
                await validator._validate_websocket(mock_app)
                
                # Should log as INFO, not WARNING
                mock_info.assert_any_call("ℹ️ WebSocket handlers will be created per-user (factory pattern)")
                
                # Should NOT have any warning about zero handlers
                for call in mock_warning.call_args_list:
                    assert "ZERO WebSocket message handlers" not in str(call)
    
    @pytest.mark.asyncio
    async def test_agent_registry_not_error_in_factory_pattern(self):
        """Test that missing agent registry is not an error in factory pattern."""
        
        # Mock app state with supervisor but no registry (factory pattern)
        mock_app_state = MagicMock()
        mock_supervisor = MagicMock()
        mock_supervisor.registry = None  # No registry in factory pattern
        mock_app_state.agent_supervisor = mock_supervisor
        
        # Run the fix
        results = StartupValidationFixer.fix_agent_websocket_initialization(mock_app_state)
        
        # Should succeed even without registry
        assert results['success'] == True
        assert len(results['errors']) == 0
        assert "Agent registry not found" not in str(results)
    
    @pytest.mark.asyncio
    async def test_zero_agents_registered_is_info_level(self):
        """Test that zero agents registered logs as INFO for legacy pattern."""
        validator = StartupValidator()
        
        # Mock app with supervisor and empty legacy registry
        mock_app = MagicMock()
        mock_app.state = MagicMock()
        mock_supervisor = MagicMock()
        mock_registry = MagicMock()
        mock_registry.agents = {}  # Zero agents in legacy registry
        mock_supervisor.registry = mock_registry
        mock_app.state.agent_supervisor = mock_supervisor
        
        # Capture log output
        with patch.object(validator.logger, 'info') as mock_info:
            with patch.object(validator.logger, 'warning') as mock_warning:
                await validator._validate_agents(mock_app)
                
                # Should log as INFO about legacy pattern
                mock_info.assert_any_call("ℹ️ Legacy registry empty - agents will be created per-request (factory pattern)")
                
                # Should NOT have warning about zero agents
                for call in mock_warning.call_args_list:
                    assert "ZERO AGENTS REGISTERED" not in str(call)


if __name__ == "__main__":
    # Run the tests
    test = TestWebSocketWarningsFix()
    asyncio.run(test.test_websocket_handler_warning_is_info_level())
    asyncio.run(test.test_agent_registry_not_error_in_factory_pattern())
    asyncio.run(test.test_zero_agents_registered_is_info_level())
    print("✅ All WebSocket warning fix tests passed!")