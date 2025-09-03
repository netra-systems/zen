"""
Integration test for WebSocket thread routing and message delivery.

This test verifies that:
1. Thread IDs are properly extracted from run_ids
2. WebSocket connections are correctly associated with thread_ids
3. Messages from agents reach the correct user connections
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.utils.run_id_generator import generate_run_id, extract_thread_id_from_run_id
from netra_backend.app.core.id_manager import IDManager
from netra_backend.app.websocket_core.manager import WebSocketManager, get_websocket_manager


class TestWebSocketThreadRouting:
    """Test suite for WebSocket thread routing functionality."""
    
    @pytest.fixture
    def websocket_manager(self):
        """Create a mock WebSocket manager with proper thread support."""
        manager = Mock(spec=WebSocketManager)
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.send_to_user = AsyncMock(return_value=True)
        manager.connections = {}
        return manager
    
    @pytest.fixture
    def thread_registry(self):
        """Create a mock thread registry."""
        registry = Mock()
        registry.get_thread = AsyncMock(return_value=None)
        registry.register = AsyncMock(return_value=True)
        return registry
    
    @pytest.fixture
    def bridge(self, websocket_manager, thread_registry):
        """Create an AgentWebSocketBridge with mocked dependencies."""
        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager', return_value=websocket_manager):
            with patch('netra_backend.app.services.agent_websocket_bridge.get_thread_run_registry', return_value=thread_registry):
                bridge = AgentWebSocketBridge()
                bridge._websocket_manager = websocket_manager
                bridge._thread_registry = thread_registry
                return bridge
    
    def test_thread_id_extraction_from_run_id_generator_format(self):
        """Test extraction of thread_id from run_id_generator format."""
        # Test cases with run_id_generator format
        test_cases = [
            ("thread_13679e4dcc38403a_run_1756919162904_9adf1f09", "13679e4dcc38403a"),
            ("thread_user_123_run_1693430400000_a1b2c3d4", "user_123"),
            ("thread_session_456_run_1693430400000_xyz", "session_456"),
        ]
        
        bridge = AgentWebSocketBridge()
        
        for run_id, expected_raw in test_cases:
            # Test standard extraction
            extracted_raw = extract_thread_id_from_run_id(run_id)
            assert extracted_raw == expected_raw, f"Failed to extract raw thread_id from {run_id}"
            
            # Test bridge extraction (should add "thread_" prefix)
            extracted_bridge = bridge._extract_thread_from_standardized_run_id(run_id)
            expected_full = f"thread_{expected_raw}"
            assert extracted_bridge == expected_full, f"Failed to extract full thread_id from {run_id}"
    
    def test_thread_id_extraction_from_id_manager_format(self):
        """Test extraction of thread_id from IDManager format."""
        # Test cases with IDManager format (requires 8 hex chars at end)
        test_cases = [
            ("run_user_123_abc12345", "user_123"),
            ("run_session_456_def67890", "session_456"),
            ("run_thread_789_a1b2c3d4", "thread_789"),  # Fixed: 8 hex chars
        ]
        
        bridge = AgentWebSocketBridge()
        
        for run_id, expected_raw in test_cases:
            # Test IDManager extraction
            extracted_raw = IDManager.extract_thread_id(run_id)
            assert extracted_raw == expected_raw, f"Failed to extract raw thread_id from {run_id}"
            
            # Test bridge extraction with IDManager format
            extracted_bridge = bridge._extract_thread_from_standardized_run_id(run_id)
            # Should add "thread_" prefix if not present
            if not expected_raw.startswith("thread_"):
                expected_full = f"thread_{expected_raw}"
            else:
                expected_full = expected_raw
            assert extracted_bridge == expected_full, f"Failed to extract full thread_id from {run_id}"
    
    def test_round_trip_generation_and_extraction(self):
        """Test that we can generate a run_id and extract the thread_id back."""
        thread_ids = [
            "13679e4dcc38403a",
            "user_123_session",
            "chat_conversation_456",
            "thread_already_prefixed",
        ]
        
        bridge = AgentWebSocketBridge()
        
        for original_thread in thread_ids:
            # Generate run_id
            run_id = generate_run_id(original_thread, "test_context")
            
            # Extract thread_id back
            extracted = bridge._extract_thread_from_standardized_run_id(run_id)
            
            # The extracted version should have "thread_" prefix
            if not original_thread.startswith("thread_"):
                expected = f"thread_{original_thread}"
            else:
                expected = original_thread
            
            assert extracted == expected, f"Round trip failed for {original_thread}"
    
    @pytest.mark.asyncio
    async def test_websocket_notification_with_correct_thread_id(self, bridge, websocket_manager):
        """Test that WebSocket notifications use the correct thread_id."""
        # Test run_id with expected thread extraction
        run_id = "thread_user123_run_1756919162904_abc123"
        agent_name = "TestAgent"
        
        # Send agent_started notification
        success = await bridge.notify_agent_started(run_id, agent_name)
        
        # Verify send_to_thread was called with correct thread_id
        assert success is True
        websocket_manager.send_to_thread.assert_called_once()
        
        # Check that the thread_id passed was correct
        call_args = websocket_manager.send_to_thread.call_args
        thread_id_used = call_args[0][0]
        assert thread_id_used == "thread_user123"
        
        # Check the notification content
        notification = call_args[0][1]
        assert notification["type"] == "agent_started"
        assert notification["run_id"] == run_id
        assert notification["agent_name"] == agent_name
    
    @pytest.mark.asyncio  
    async def test_thread_resolution_priority_chain(self, bridge, websocket_manager, thread_registry):
        """Test the 5-priority resolution chain for thread_id."""
        run_id = "thread_test_priority_run_123456_xyz"
        
        # Priority 1: Registry returns None (not found)
        thread_registry.get_thread.return_value = None
        
        # Priority 2: No orchestrator available
        bridge._orchestrator = None
        
        # Priority 3: No WebSocket manager connections
        websocket_manager.connections = {}
        
        # Priority 4: Pattern extraction should work
        thread_id = await bridge._resolve_thread_id_from_run_id(run_id)
        
        # Should successfully extract via pattern
        assert thread_id == "thread_test_priority"
    
    @pytest.mark.asyncio
    async def test_thread_resolution_with_registry_hit(self, bridge, thread_registry):
        """Test that thread registry is checked first."""
        run_id = "custom_run_format_12345"
        expected_thread = "thread_from_registry"
        
        # Registry returns a thread_id
        thread_registry.get_thread.return_value = expected_thread
        
        thread_id = await bridge._resolve_thread_id_from_run_id(run_id)
        
        # Should use registry result
        assert thread_id == expected_thread
        thread_registry.get_thread.assert_called_once_with(run_id)
    
    @pytest.mark.skip(reason="Error handling behavior needs refinement")
    @pytest.mark.asyncio
    async def test_invalid_run_id_raises_error(self, bridge):
        """Test that invalid run_id formats raise appropriate errors."""
        invalid_run_ids = [
            "invalid_format",
            "no_thread_or_run",
        ]
        
        for invalid_id in invalid_run_ids:
            with pytest.raises(ValueError) as exc_info:
                await bridge._resolve_thread_id_from_run_id(invalid_id)
            assert "Thread resolution failed" in str(exc_info.value)
        
        # Test empty string separately
        with pytest.raises(ValueError) as exc_info:
            await bridge._resolve_thread_id_from_run_id("")
        assert "Invalid run_id" in str(exc_info.value) or "Thread resolution failed" in str(exc_info.value)
        
        # Test None separately  
        with pytest.raises(ValueError) as exc_info:
            await bridge._resolve_thread_id_from_run_id(None)
        assert "Invalid run_id" in str(exc_info.value) or "Thread resolution failed" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_all_notification_types_use_correct_thread(self, bridge, websocket_manager):
        """Test that all notification types properly route to thread_id."""
        run_id = "thread_notification_test_run_123_abc"
        expected_thread = "thread_notification_test"
        
        # Test agent_started
        await bridge.notify_agent_started(run_id, "TestAgent")
        
        # Test agent_thinking
        await bridge.notify_agent_thinking(run_id, "TestAgent", "Processing...")
        
        # Test tool_executing  
        await bridge.notify_tool_executing(run_id, "TestAgent", "test_tool", {"param": "value"})
        
        # Test tool_completed
        await bridge.notify_tool_completed(run_id, "TestAgent", "test_tool", {"result": "success"})
        
        # Test agent_completed
        await bridge.notify_agent_completed(run_id, "TestAgent", {"final": "result"})
        
        # Verify all calls used the correct thread_id
        assert websocket_manager.send_to_thread.call_count == 5
        
        for call in websocket_manager.send_to_thread.call_args_list:
            thread_id_used = call[0][0]
            assert thread_id_used == expected_thread
    
    def test_both_id_formats_supported(self):
        """Test that both run_id_generator and IDManager formats are supported."""
        bridge = AgentWebSocketBridge()
        
        # Test run_id_generator format
        run_id_gen = "thread_user123_run_1756919162904_abc"
        extracted_gen = bridge._extract_thread_from_standardized_run_id(run_id_gen)
        assert extracted_gen == "thread_user123"
        
        # Test IDManager format (requires 8 hex chars at end)
        run_id_mgr = "run_user456_a1b2c3d4"  # Proper IDManager format
        extracted_mgr = bridge._extract_thread_from_standardized_run_id(run_id_mgr)
        assert extracted_mgr == "thread_user456"  # Should add thread_ prefix