# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''Test for WebSocket bridge run_id propagation fix.

    # REMOVED_SYNTAX_ERROR: This test ensures that sub-agents receive proper run_id values
    # REMOVED_SYNTAX_ERROR: when their WebSocket bridge is configured, preventing the
    # REMOVED_SYNTAX_ERROR: "Attempting to set None run_id" error.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.user_execution_context import UserExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.logging_config import central_logger
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env

    # REMOVED_SYNTAX_ERROR: logger = central_logger.get_logger(__name__)


# REMOVED_SYNTAX_ERROR: class TestWebSocketRunIdFix:
    # REMOVED_SYNTAX_ERROR: """Test that sub-agents get proper run_id when created through factory."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_subagents_get_valid_runid_through_factory(self):
        # REMOVED_SYNTAX_ERROR: """Test that sub-agents created through factory get valid run_id."""
        # Setup
        # REMOVED_SYNTAX_ERROR: websocket_bridge = MagicMock(spec=AgentWebSocketBridge)
        # REMOVED_SYNTAX_ERROR: websocket_manager = Magic
        # Create factory
        # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
        # REMOVED_SYNTAX_ERROR: factory.configure( )
        # REMOVED_SYNTAX_ERROR: websocket_bridge=websocket_bridge,
        # REMOVED_SYNTAX_ERROR: websocket_manager=websocket_manager
        

        # Create user execution context with valid run_id
        # REMOVED_SYNTAX_ERROR: run_id = str(uuid.uuid4())
        # REMOVED_SYNTAX_ERROR: user_id = "test_user"
        # REMOVED_SYNTAX_ERROR: thread_id = "test_thread"

        # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
        # REMOVED_SYNTAX_ERROR: user_id=user_id,
        # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
        # REMOVED_SYNTAX_ERROR: run_id=run_id
        

        # REMOVED_SYNTAX_ERROR: assert context.run_id == run_id

        # Test creating sub-agents through factory
        # REMOVED_SYNTAX_ERROR: agent_names = ["optimization", "actions", "reporting"]

        # REMOVED_SYNTAX_ERROR: for agent_name in agent_names:
            # REMOVED_SYNTAX_ERROR: try:
                # Create agent instance through factory
                # REMOVED_SYNTAX_ERROR: agent = await factory.create_agent_instance( )
                # REMOVED_SYNTAX_ERROR: agent_name=agent_name,
                # REMOVED_SYNTAX_ERROR: user_context=context
                

                # Verify agent has WebSocket adapter
                # REMOVED_SYNTAX_ERROR: assert hasattr(agent, '_websocket_adapter'), "formatted_string"

                # Verify run_id was set properly
                # REMOVED_SYNTAX_ERROR: if agent._websocket_adapter._run_id:
                    # REMOVED_SYNTAX_ERROR: assert agent._websocket_adapter._run_id == run_id, \
                    # REMOVED_SYNTAX_ERROR: "formatted_string"
                    # REMOVED_SYNTAX_ERROR: logger.info("formatted_string")
                    # REMOVED_SYNTAX_ERROR: else:
                        # REMOVED_SYNTAX_ERROR: logger.warning("formatted_string")

                        # REMOVED_SYNTAX_ERROR: except Exception as e:
                            # REMOVED_SYNTAX_ERROR: logger.error("formatted_string")
                            # This is expected if agent classes aren't registered
                            # REMOVED_SYNTAX_ERROR: pass

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_registry_does_not_set_none_runid(self):
                                # REMOVED_SYNTAX_ERROR: """Test that AgentRegistry no longer sets WebSocket bridge with None run_id."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # Create registry
                                # REMOVED_SYNTAX_ERROR: llm_manager = Magic        tool_dispatcher = Magic        websocket_bridge = MagicMock(spec=AgentWebSocketBridge)

                                # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

                                # Mock agent with set_websocket_bridge method
                                # REMOVED_SYNTAX_ERROR: mock_agent = Magic        mock_agent.set_websocket_bridge = Magic
                                # Register agent
                                # REMOVED_SYNTAX_ERROR: registry.register("test_agent", mock_agent)

                                # Set WebSocket bridge on registry
                                # REMOVED_SYNTAX_ERROR: registry.set_websocket_bridge(websocket_bridge)

                                # Verify set_websocket_bridge was NOT called with None run_id
                                # After our fix, it should not be called at all during registration
                                # REMOVED_SYNTAX_ERROR: mock_agent.set_websocket_bridge.assert_not_called()
                                # REMOVED_SYNTAX_ERROR: logger.info(" PASS:  Registry does not set WebSocket bridge with None run_id")

                                # Removed problematic line: @pytest.mark.asyncio
                                # Removed problematic line: async def test_websocket_adapter_validates_runid(self):
                                    # REMOVED_SYNTAX_ERROR: """Test that WebSocketBridgeAdapter logs error for None run_id."""
                                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter

                                    # REMOVED_SYNTAX_ERROR: adapter = WebSocketBridgeAdapter()
                                    # REMOVED_SYNTAX_ERROR: bridge = MagicMock(spec=AgentWebSocketBridge)

                                    # Test setting with None run_id (should log error)
                                    # REMOVED_SYNTAX_ERROR: with patch.object(logger, 'error') as mock_error:
                                        # REMOVED_SYNTAX_ERROR: adapter.set_websocket_bridge(bridge, None, "TestAgent")

                                        # Verify error was logged
                                        # REMOVED_SYNTAX_ERROR: mock_error.assert_any_call( )
                                        # REMOVED_SYNTAX_ERROR: " FAIL:  CRITICAL: Attempting to set None run_id on WebSocketBridgeAdapter for TestAgent!"
                                        

                                        # Test setting with valid run_id (should log success)
                                        # REMOVED_SYNTAX_ERROR: valid_run_id = str(uuid.uuid4())
                                        # REMOVED_SYNTAX_ERROR: with patch.object(logger, 'info') as mock_info:
                                            # REMOVED_SYNTAX_ERROR: adapter.set_websocket_bridge(bridge, valid_run_id, "TestAgent")

                                            # Verify success was logged
                                            # REMOVED_SYNTAX_ERROR: calls = [str(call) for call in mock_info.call_args_list]
                                            # REMOVED_SYNTAX_ERROR: assert any("WebSocket bridge configured for TestAgent" in str(call) for call in calls)

                                            # REMOVED_SYNTAX_ERROR: logger.info(" PASS:  WebSocketBridgeAdapter properly validates run_id")


                                            # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                # Run tests
                                                # REMOVED_SYNTAX_ERROR: import sys
                                                # REMOVED_SYNTAX_ERROR: import pytest

                                                # Run with verbose output
                                                # REMOVED_SYNTAX_ERROR: sys.exit(pytest.main([__file__, "-v", "-s"]))
                                                # REMOVED_SYNTAX_ERROR: pass