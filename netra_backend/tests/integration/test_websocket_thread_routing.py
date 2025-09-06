from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Integration test for WebSocket thread routing and message delivery.

# REMOVED_SYNTAX_ERROR: This test verifies that:
    # REMOVED_SYNTAX_ERROR: 1. Thread IDs are properly extracted from run_ids
    # REMOVED_SYNTAX_ERROR: 2. WebSocket connections are correctly associated with thread_ids
    # REMOVED_SYNTAX_ERROR: 3. Messages from agents reach the correct user connections
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_id_manager import UnifiedIDManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager, get_websocket_manager


# REMOVED_SYNTAX_ERROR: class TestWebSocketThreadRouting:
    # REMOVED_SYNTAX_ERROR: """Test suite for WebSocket thread routing functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket manager with proper thread support."""
    # REMOVED_SYNTAX_ERROR: manager = Mock(spec=WebSocketManager)
    # REMOVED_SYNTAX_ERROR: manager.send_to_thread = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: manager.send_to_user = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: manager.connections = {}
    # REMOVED_SYNTAX_ERROR: return manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def thread_registry(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a mock thread registry."""
    # REMOVED_SYNTAX_ERROR: registry = registry_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: registry.get_thread = AsyncMock(return_value=None)
    # REMOVED_SYNTAX_ERROR: registry.register = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return registry

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def bridge(self, websocket_manager, thread_registry):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create an AgentWebSocketBridge with mocked dependencies."""
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', return_value=websocket_manager):
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.services.agent_websocket_bridge.get_thread_run_registry', return_value=thread_registry):
            # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()
            # REMOVED_SYNTAX_ERROR: bridge._websocket_manager = websocket_manager
            # REMOVED_SYNTAX_ERROR: bridge._thread_registry = thread_registry
            # REMOVED_SYNTAX_ERROR: return bridge

# REMOVED_SYNTAX_ERROR: def test_thread_id_extraction_from_run_id_generator_format(self):
    # REMOVED_SYNTAX_ERROR: """Test extraction of thread_id from run_id_generator format."""
    # Test cases with run_id_generator format (must have 8 hex char UUID suffix)
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # REMOVED_SYNTAX_ERROR: ("thread_13679e4dcc38403a_run_1756919162904_9adf1f09", "13679e4dcc38403a"),
    # REMOVED_SYNTAX_ERROR: ("thread_user_123_run_1693430400000_a1b2c3d4", "user_123"),
    # REMOVED_SYNTAX_ERROR: ("thread_session_456_run_1693430400000_12345678", "session_456"),  # Fixed: proper 8 hex chars
    

    # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()

    # REMOVED_SYNTAX_ERROR: for run_id, expected_raw in test_cases:
        # Test standard extraction
        # REMOVED_SYNTAX_ERROR: extracted_raw = UnifiedIDManager.extract_thread_id(run_id)
        # REMOVED_SYNTAX_ERROR: assert extracted_raw == expected_raw, "formatted_string"

        # Test bridge extraction (should add "thread_" prefix)
        # REMOVED_SYNTAX_ERROR: extracted_bridge = bridge._extract_thread_from_standardized_run_id(run_id)
        # REMOVED_SYNTAX_ERROR: expected_full = "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert extracted_bridge == expected_full, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_thread_id_extraction_from_unified_id_manager_format(self):
    # REMOVED_SYNTAX_ERROR: """Test extraction of thread_id from UnifiedIDManager format."""
    # Test cases with UnifiedIDManager format (requires 8 hex chars at end)
    # REMOVED_SYNTAX_ERROR: test_cases = [ )
    # REMOVED_SYNTAX_ERROR: ("run_user_123_abc12345", "user_123"),
    # REMOVED_SYNTAX_ERROR: ("run_session_456_def67890", "session_456"),
    # REMOVED_SYNTAX_ERROR: ("run_thread_789_a1b2c3d4", "thread_789"),  # Fixed: 8 hex chars
    

    # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()

    # REMOVED_SYNTAX_ERROR: for run_id, expected_raw in test_cases:
        # Test UnifiedIDManager extraction
        # REMOVED_SYNTAX_ERROR: extracted_raw = UnifiedIDManager.extract_thread_id(run_id)
        # REMOVED_SYNTAX_ERROR: assert extracted_raw == expected_raw, "formatted_string"

        # Test bridge extraction with UnifiedIDManager format
        # REMOVED_SYNTAX_ERROR: extracted_bridge = bridge._extract_thread_from_standardized_run_id(run_id)
        # Should add "thread_" prefix if not present
        # REMOVED_SYNTAX_ERROR: if not expected_raw.startswith("thread_"):
            # REMOVED_SYNTAX_ERROR: expected_full = "formatted_string"
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: expected_full = expected_raw
                # REMOVED_SYNTAX_ERROR: assert extracted_bridge == expected_full, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_round_trip_generation_and_extraction(self):
    # REMOVED_SYNTAX_ERROR: """Test that we can generate a run_id and extract the thread_id back."""
    # REMOVED_SYNTAX_ERROR: thread_ids = [ )
    # REMOVED_SYNTAX_ERROR: "13679e4dcc38403a",
    # REMOVED_SYNTAX_ERROR: "user_123_session",
    # REMOVED_SYNTAX_ERROR: "chat_conversation_456",
    # REMOVED_SYNTAX_ERROR: "thread_already_prefixed",
    

    # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()

    # REMOVED_SYNTAX_ERROR: for original_thread in thread_ids:
        # Generate run_id (UnifiedIDManager only takes thread_id parameter)
        # REMOVED_SYNTAX_ERROR: run_id = UnifiedIDManager.generate_run_id(original_thread)

        # Extract thread_id back
        # REMOVED_SYNTAX_ERROR: extracted = bridge._extract_thread_from_standardized_run_id(run_id)

        # The extracted version should have "thread_" prefix
        # REMOVED_SYNTAX_ERROR: if not original_thread.startswith("thread_"):
            # REMOVED_SYNTAX_ERROR: expected = "formatted_string"
            # REMOVED_SYNTAX_ERROR: else:
                # REMOVED_SYNTAX_ERROR: expected = original_thread

                # REMOVED_SYNTAX_ERROR: assert extracted == expected, "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_websocket_notification_with_correct_thread_id(self, bridge, websocket_manager):
                    # REMOVED_SYNTAX_ERROR: """Test that WebSocket notifications use the correct thread_id."""
                    # Test run_id with expected thread extraction (8 hex chars for UUID)
                    # REMOVED_SYNTAX_ERROR: run_id = "thread_user123_run_1756919162904_abc12345"
                    # REMOVED_SYNTAX_ERROR: agent_name = "TestAgent"

                    # Send agent_started notification
                    # REMOVED_SYNTAX_ERROR: success = await bridge.notify_agent_started(run_id, agent_name)

                    # Verify send_to_thread was called with correct thread_id
                    # REMOVED_SYNTAX_ERROR: assert success is True
                    # REMOVED_SYNTAX_ERROR: websocket_manager.send_to_thread.assert_called_once()

                    # Check that the thread_id passed was correct
                    # REMOVED_SYNTAX_ERROR: call_args = websocket_manager.send_to_thread.call_args
                    # REMOVED_SYNTAX_ERROR: thread_id_used = call_args[0][0]
                    # REMOVED_SYNTAX_ERROR: assert thread_id_used == "thread_user123"

                    # Check the notification content
                    # REMOVED_SYNTAX_ERROR: notification = call_args[0][1]
                    # REMOVED_SYNTAX_ERROR: assert notification["type"] == "agent_started"
                    # REMOVED_SYNTAX_ERROR: assert notification["run_id"] == run_id
                    # REMOVED_SYNTAX_ERROR: assert notification["agent_name"] == agent_name

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_thread_resolution_priority_chain(self, bridge, websocket_manager, thread_registry):
                        # REMOVED_SYNTAX_ERROR: """Test the 5-priority resolution chain for thread_id."""
                        # REMOVED_SYNTAX_ERROR: run_id = "thread_test_priority_run_123456_12345678"  # Fixed: 8 hex chars

                        # Priority 1: Registry returns None (not found)
                        # REMOVED_SYNTAX_ERROR: thread_registry.get_thread.return_value = None

                        # Priority 2: No orchestrator available
                        # REMOVED_SYNTAX_ERROR: bridge._orchestrator = None

                        # Priority 3: No WebSocket manager connections
                        # REMOVED_SYNTAX_ERROR: websocket_manager.connections = {}

                        # Priority 4: Pattern extraction should work
                        # REMOVED_SYNTAX_ERROR: thread_id = await bridge._resolve_thread_id_from_run_id(run_id)

                        # Should successfully extract via pattern
                        # REMOVED_SYNTAX_ERROR: assert thread_id == "thread_test_priority"

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_thread_resolution_with_registry_hit(self, bridge, thread_registry):
                            # REMOVED_SYNTAX_ERROR: """Test that thread registry is checked first."""
                            # REMOVED_SYNTAX_ERROR: run_id = "custom_run_format_12345"
                            # REMOVED_SYNTAX_ERROR: expected_thread = "thread_from_registry"

                            # Registry returns a thread_id
                            # REMOVED_SYNTAX_ERROR: thread_registry.get_thread.return_value = expected_thread

                            # REMOVED_SYNTAX_ERROR: thread_id = await bridge._resolve_thread_id_from_run_id(run_id)

                            # Should use registry result
                            # REMOVED_SYNTAX_ERROR: assert thread_id == expected_thread
                            # REMOVED_SYNTAX_ERROR: thread_registry.get_thread.assert_called_once_with(run_id)

                            # REMOVED_SYNTAX_ERROR: @pytest.fixture
                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_invalid_run_id_raises_error(self, bridge):
                                # REMOVED_SYNTAX_ERROR: """Test that invalid run_id formats raise appropriate errors."""
                                # REMOVED_SYNTAX_ERROR: invalid_run_ids = [ )
                                # REMOVED_SYNTAX_ERROR: "invalid_format",
                                # REMOVED_SYNTAX_ERROR: "no_thread_or_run",
                                

                                # REMOVED_SYNTAX_ERROR: for invalid_id in invalid_run_ids:
                                    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
                                        # REMOVED_SYNTAX_ERROR: await bridge._resolve_thread_id_from_run_id(invalid_id)
                                        # REMOVED_SYNTAX_ERROR: assert "Thread resolution failed" in str(exc_info.value)

                                        # Test empty string separately
                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
                                            # REMOVED_SYNTAX_ERROR: await bridge._resolve_thread_id_from_run_id("")
                                            # REMOVED_SYNTAX_ERROR: assert "Invalid run_id" in str(exc_info.value) or "Thread resolution failed" in str(exc_info.value)

                                            # Test None separately
                                            # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError) as exc_info:
                                                # REMOVED_SYNTAX_ERROR: await bridge._resolve_thread_id_from_run_id(None)
                                                # REMOVED_SYNTAX_ERROR: assert "Invalid run_id" in str(exc_info.value) or "Thread resolution failed" in str(exc_info.value)

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_all_notification_types_use_correct_thread(self, bridge, websocket_manager):
                                                    # REMOVED_SYNTAX_ERROR: """Test that all notification types properly route to thread_id."""
                                                    # REMOVED_SYNTAX_ERROR: run_id = "thread_notification_test_run_123_abc12345"  # Fixed: 8 hex chars
                                                    # REMOVED_SYNTAX_ERROR: expected_thread = "thread_notification_test"

                                                    # Test agent_started
                                                    # REMOVED_SYNTAX_ERROR: await bridge.notify_agent_started(run_id, "TestAgent")

                                                    # Test agent_thinking
                                                    # REMOVED_SYNTAX_ERROR: await bridge.notify_agent_thinking(run_id, "TestAgent", "Processing...")

                                                    # Test tool_executing
                                                    # REMOVED_SYNTAX_ERROR: await bridge.notify_tool_executing(run_id, "TestAgent", "test_tool", {"param": "value"})

                                                    # Test tool_completed
                                                    # REMOVED_SYNTAX_ERROR: await bridge.notify_tool_completed(run_id, "TestAgent", "test_tool", {"result": "success"})

                                                    # Test agent_completed
                                                    # REMOVED_SYNTAX_ERROR: await bridge.notify_agent_completed(run_id, "TestAgent", {"final": "result"})

                                                    # Verify all calls used the correct thread_id
                                                    # REMOVED_SYNTAX_ERROR: assert websocket_manager.send_to_thread.call_count == 5

                                                    # REMOVED_SYNTAX_ERROR: for call in websocket_manager.send_to_thread.call_args_list:
                                                        # REMOVED_SYNTAX_ERROR: thread_id_used = call[0][0]
                                                        # REMOVED_SYNTAX_ERROR: assert thread_id_used == expected_thread

# REMOVED_SYNTAX_ERROR: def test_both_id_formats_supported(self):
    # REMOVED_SYNTAX_ERROR: """Test that both run_id_generator and UnifiedIDManager formats are supported."""
    # REMOVED_SYNTAX_ERROR: bridge = AgentWebSocketBridge()

    # Test run_id_generator format
    # REMOVED_SYNTAX_ERROR: run_id_gen = "thread_user123_run_1756919162904_abc12345"  # Fixed: 8 hex chars
    # REMOVED_SYNTAX_ERROR: extracted_gen = bridge._extract_thread_from_standardized_run_id(run_id_gen)
    # REMOVED_SYNTAX_ERROR: assert extracted_gen == "thread_user123"

    # Test UnifiedIDManager format (requires 8 hex chars at end)
    # REMOVED_SYNTAX_ERROR: run_id_mgr = "run_user456_a1b2c3d4"  # Proper UnifiedIDManager format
    # REMOVED_SYNTAX_ERROR: extracted_mgr = bridge._extract_thread_from_standardized_run_id(run_id_mgr)
    # REMOVED_SYNTAX_ERROR: assert extracted_mgr == "thread_user456"  # Should add thread_ prefix
    # REMOVED_SYNTAX_ERROR: pass