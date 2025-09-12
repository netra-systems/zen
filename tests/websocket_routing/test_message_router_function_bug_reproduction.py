"""
WebSocket Message Router Function Bug Reproduction Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Bug Prevention  
- Value Impact: Prevent 'function' object has no attribute 'can_handle' errors
- Strategic Impact: Ensure proper MessageHandler interface compliance

CRITICAL BUG REPRODUCTION:
This test suite reproduces the exact error seen in staging logs:
"'function' object has no attribute 'can_handle'"

The bug occurs when websocket_ssot.py adds raw functions to MessageRouter
instead of proper MessageHandler instances.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from netra_backend.app.websocket_core.handlers import MessageRouter, MessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage


class TestMessageRouterFunctionBugReproduction:
    """Test suite that reproduces the exact function object bug from staging."""
    
    @pytest.fixture
    def message_router(self):
        """Create fresh MessageRouter for each test."""
        return MessageRouter()
    
    @pytest.fixture  
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = Mock()
        websocket.send_json = AsyncMock()
        websocket.application_state = Mock()
        websocket.application_state._mock_name = "test_websocket"  # Mark as mock
        return websocket
    
    @pytest.fixture
    def sample_message(self):
        """Create sample WebSocket message."""
        return {
            "type": "agent_request",
            "payload": {"message": "test request"},
            "user_id": "test_user_123",
            "timestamp": 1234567890.0
        }

    def test_function_object_bug_reproduction(self, message_router, mock_websocket, sample_message):
        """
        CRITICAL BUG REPRODUCTION: Adding function instead of MessageHandler
        
        This test reproduces the exact error from websocket_ssot.py line 1158:
        "message_router.add_handler(agent_handler)" where agent_handler is a function.
        
        EXPECTED: The error is caught by route_message and returns False, 
        but we can reproduce the raw AttributeError by calling _find_handler directly.
        """
        # Reproduce the exact bug from websocket_ssot.py
        async def agent_handler(user_id: str, websocket, message: Dict[str, Any]):
            """This is the problematic function from websocket_ssot.py line 1155-1156."""
            return True
        
        # BUG REPRODUCTION: Add function directly (this is the bug!)
        message_router.add_handler(agent_handler)
        
        # Verify the function was added (router doesn't validate at add time)
        assert len(message_router.custom_handlers) == 1
        assert message_router.custom_handlers[0] == agent_handler
        
        # THE CRITICAL FAILURE: This should raise AttributeError when calling _find_handler directly
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            # This directly triggers the bug without exception handling
            message_router._find_handler(MessageType.AGENT_REQUEST)
        
        # ALSO TEST: route_message catches the error and returns False
        result = asyncio.run(message_router.route_message("test_user", mock_websocket, sample_message))
        assert result is False, "route_message should return False when handler protocol is violated"

    def test_function_object_has_no_can_handle_method(self, message_router):
        """
        UNIT TEST: Direct verification that functions don't have can_handle method.
        
        This test proves that raw functions fail the MessageHandler protocol.
        EXPECTED: Test MUST FAIL with AttributeError.
        """
        # Create a function like the one in websocket_ssot.py
        async def problematic_handler(user_id: str, websocket, message: Dict[str, Any]):
            return True
        
        # Add the function to router (this doesn't fail)
        message_router.add_handler(problematic_handler)
        
        # But trying to call can_handle on it fails (this is the bug)
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            problematic_handler.can_handle(MessageType.AGENT_REQUEST)

    def test_function_object_has_no_handle_message_method_with_correct_signature(self, message_router):
        """
        UNIT TEST: Functions don't match MessageHandler.handle_message signature.
        
        Even if we bypass can_handle, the function signature is wrong for MessageHandler.
        """
        async def agent_handler(user_id: str, websocket, message: Dict[str, Any]):
            """Function with wrong signature - takes Dict not WebSocketMessage."""
            return True
        
        # The function exists but has wrong signature
        assert callable(agent_handler)
        assert hasattr(agent_handler, '__call__')
        
        # But it doesn't match the MessageHandler protocol signature
        # MessageHandler.handle_message expects WebSocketMessage, not Dict[str, Any]
        websocket_message = WebSocketMessage(
            type=MessageType.AGENT_REQUEST,
            payload={"test": "data"},
            timestamp=1234567890.0
        )
        
        # This would fail due to signature mismatch if we tried to call it as MessageHandler
        # We can't easily test this directly, but it's part of the overall protocol violation

    def test_proper_message_handler_works_correctly(self, message_router, mock_websocket, sample_message):
        """
        CONTROL TEST: Proper MessageHandler implementation works.
        
        This test shows how it SHOULD work with proper MessageHandler.
        EXPECTED: This test MUST PASS to show the correct implementation.
        """
        class ProperAgentHandler:
            """Proper MessageHandler implementation."""
            
            def can_handle(self, message_type: MessageType) -> bool:
                return message_type == MessageType.AGENT_REQUEST
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        # Add proper handler (this works correctly)
        proper_handler = ProperAgentHandler()
        message_router.add_handler(proper_handler)
        
        # This should work without errors
        result = asyncio.run(message_router.route_message("test_user", mock_websocket, sample_message))
        assert result is True

    def test_message_router_find_handler_calls_can_handle(self, message_router):
        """
        UNIT TEST: Verify _find_handler calls can_handle on each handler.
        
        This test proves that _find_handler is what triggers the AttributeError.
        EXPECTED: Test MUST FAIL when function is in handlers list.
        """
        # Add a function that doesn't have can_handle
        async def bad_handler(user_id, websocket, message):
            return True
        
        message_router.add_handler(bad_handler)
        
        # _find_handler tries to call can_handle on all handlers
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            message_router._find_handler(MessageType.AGENT_REQUEST)

    def test_websocket_ssot_exact_scenario_reproduction(self, message_router, mock_websocket):
        """
        INTEGRATION TEST: Exact reproduction of websocket_ssot.py scenario.
        
        This reproduces the exact code pattern from websocket_ssot.py lines 1155-1158.
        EXPECTED: Error occurs but is caught by route_message, returning False.
        """
        # Simulate the user_context and bridge creation from websocket_ssot.py
        mock_user_context = Mock()
        mock_user_context.user_id = "test_user_123"
        
        # Simulate the agent bridge creation
        mock_agent_bridge = Mock()
        mock_agent_bridge.handle_message = AsyncMock(return_value=True)
        
        # EXACT REPRODUCTION: This is the problematic code from websocket_ssot.py
        async def agent_handler(user_id: str, websocket, message: Dict[str, Any]):
            """Exact copy of the problematic function from websocket_ssot.py line 1155."""
            return await mock_agent_bridge.handle_message(message)
        
        # EXACT BUG: Add function instead of MessageHandler (line 1158)
        message_router.add_handler(agent_handler)
        
        # Create message that would trigger the bug
        agent_request_message = {
            "type": "agent_request", 
            "payload": {"message": "test agent request"},
            "user_id": "test_user_123"
        }
        
        # THE EXACT ERROR: Direct call to _find_handler reproduces the AttributeError
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            message_router._find_handler(MessageType.AGENT_REQUEST)
        
        # ALSO TEST: route_message catches error and returns False (current behavior)
        result = asyncio.run(message_router.route_message("test_user_123", mock_websocket, agent_request_message))
        assert result is False, "route_message should fail when function handler is used"

    def test_multiple_function_handlers_all_fail(self, message_router, mock_websocket, sample_message):
        """
        EDGE CASE: Multiple function handlers all cause the same error.
        
        This tests what happens when multiple problematic handlers are registered.
        EXPECTED: First function handler causes failure before others are checked.
        """
        # Add multiple function handlers (all problematic)
        async def handler1(user_id, ws, msg):
            return True
            
        async def handler2(user_id, ws, msg):
            return True
            
        message_router.add_handler(handler1)
        message_router.add_handler(handler2)
        
        # Should fail on first handler's can_handle call  
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            message_router._find_handler(MessageType.AGENT_REQUEST)
        
        # route_message catches error and returns False
        result = asyncio.run(message_router.route_message("test_user", mock_websocket, sample_message))
        assert result is False

    def test_mixed_handlers_function_prevents_proper_handlers(self, message_router, mock_websocket, sample_message):
        """
        CRITICAL EDGE CASE: Function handler prevents proper handlers from being reached.
        
        This shows that even one bad function handler breaks the entire routing system.
        EXPECTED: System fails even when proper handlers exist.
        """
        # Add proper handler first
        class GoodHandler:
            def can_handle(self, message_type: MessageType) -> bool:
                return True
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                return True
        
        good_handler = GoodHandler()
        message_router.add_handler(good_handler)
        
        # Add bad function handler (this breaks everything)
        async def bad_handler(user_id, ws, msg):
            return True
            
        message_router.add_handler(bad_handler)
        
        # Even though we have a good handler, the bad one breaks the system
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            message_router._find_handler(MessageType.AGENT_REQUEST)
        
        # route_message catches error and falls back, returning False
        result = asyncio.run(message_router.route_message("test_user", mock_websocket, sample_message))
        assert result is False


class TestWebSocketSSOTBugReproductionIntegration:
    """Integration tests that simulate the complete websocket_ssot.py scenario."""
    
    def test_agent_handler_registration_pattern(self):
        """
        INTEGRATION: Test the complete handler registration pattern from websocket_ssot.py.
        
        This reproduces the _setup_agent_handlers method behavior.
        EXPECTED: Test MUST FAIL due to function registration.
        """
        message_router = MessageRouter()
        
        # Simulate websocket_ssot.py _setup_agent_handlers method
        def setup_agent_handlers_simulation():
            # Simulate creating the agent bridge
            mock_agent_bridge = Mock()
            mock_agent_bridge.handle_message = AsyncMock(return_value=True)
            
            # The problematic code from websocket_ssot.py
            async def agent_handler(user_id: str, websocket, message: Dict[str, Any]):
                return await mock_agent_bridge.handle_message(message)
            
            # BUG: This adds a function instead of MessageHandler
            message_router.add_handler(agent_handler)
            return agent_handler
        
        # Execute the simulation
        registered_handler = setup_agent_handlers_simulation()
        
        # Verify the handler is registered
        assert len(message_router.custom_handlers) == 1
        assert message_router.custom_handlers[0] == registered_handler
        
        # But trying to use it fails
        with pytest.raises(AttributeError, match="'function' object has no attribute 'can_handle'"):
            message_router._find_handler(MessageType.AGENT_REQUEST)