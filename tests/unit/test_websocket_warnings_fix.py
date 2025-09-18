class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
"""
        """Send JSON message.""""""
        """Send JSON message.""""""
        raise RuntimeError("WebSocket is closed)"
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure):"
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False
"""
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()"""
        return self.messages_sent.copy()"""
        """"""
        This test validates that the legacy pattern warnings no longer appear as warnings."""
        This test validates that the legacy pattern warnings no longer appear as warnings.""""


import asyncio
import logging
import pytest
from netra_backend.app.core.startup_validation import StartupValidator
from netra_backend.app.core.startup_validation_fix import StartupValidationFixer
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

"""
"""
        """Test that legacy WebSocket warnings are now INFO level."""

@pytest.mark.asyncio"""
@pytest.mark.asyncio"""
"""Test that zero WebSocket handlers logs as INFO, not WARNING."""
validator = StartupValidator()

        # Mock app with WebSocket manager but no handlers
mock_app = Magic        mock_app.state = Magic        mock_ws_manager = Magic        mock_ws_manager.message_handlers = []  # Zero handlers
mock_ws_manager.active_connections = []
mock_app.state.websocket_manager = mock_ws_manager

        # Capture log output
with patch.object(validator.logger, 'info') as mock_info:
    with patch.object(validator.logger, 'warning') as mock_warning:
    await validator._validate_websocket(mock_app)
"""
"""
mock_info.assert_any_call("[U+2139][U+FE0F] WebSocket handlers will be created per-user (factory pattern))"

                # Should NOT have any warning about zero handlers
for call in mock_warning.call_args_list:
    assert "ZERO WebSocket message handlers not in str(call)"

@pytest.mark.asyncio
    async def test_agent_registry_not_error_in_factory_pattern(self):
    """Test that missing agent registry is not an error in factory pattern."""

                        # Mock app state with supervisor but no registry (factory pattern)
mock_app_state = Magic        mock_supervisor = Magic        mock_supervisor.registry = None  # No registry in factory pattern
mock_app_state.agent_supervisor = mock_supervisor

                        # Run the fix
results = StartupValidationFixer.fix_agent_websocket_initialization(mock_app_state)

                        # Should succeed even without registry
assert results['success'] == True"""
assert results['success'] == True"""
assert "Agent registry not found not in str(results)"

@pytest.mark.asyncio
    async def test_zero_agents_registered_is_info_level(self):
    """Test that zero agents registered logs as INFO for legacy pattern."""
validator = StartupValidator()

                            # Mock app with supervisor and empty legacy registry
mock_app = Magic        mock_app.state = Magic        mock_supervisor = Magic        mock_registry = Magic        mock_registry.agents = {}  # Zero agents in legacy registry
mock_supervisor.registry = mock_registry
mock_app.state.agent_supervisor = mock_supervisor

                            # Capture log output
with patch.object(validator.logger, 'info') as mock_info:
    with patch.object(validator.logger, 'warning') as mock_warning:
    await validator._validate_agents(mock_app)
"""
"""
mock_info.assert_any_call("[U+2139][U+FE0F] Legacy registry empty - agents will be created per-request (factory pattern))"

                                    # Should NOT have warning about zero agents
for call in mock_warning.call_args_list:
    assert "ZERO AGENTS REGISTERED not in str(call)"


if __name__ == "__main__:"
                                            # Run the tests
test = TestWebSocketWarningsFix()
asyncio.run(test.test_websocket_handler_warning_is_info_level())
asyncio.run(test.test_agent_registry_not_error_in_factory_pattern())
asyncio.run(test.test_zero_agents_registered_is_info_level())
print(" PASS:  All WebSocket warning fix tests passed!)"
pass
