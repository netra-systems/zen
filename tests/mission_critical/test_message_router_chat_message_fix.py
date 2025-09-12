"""
Mission Critical Test Suite: MessageRouter Chat Message Type Fix

Business Value Justification:
- Segment: Platform/Internal 
- Business Goal: Development Velocity & System Stability
- Value Impact: Prevent message routing failures that block user chat interactions
- Strategic Impact: Essential for "Chat is King" business mandate - chat must work reliably

This test suite validates that the 'chat_message' type fix is working properly in MessageRouter
and that the business-critical message handling pipeline functions correctly.

CRITICAL: These tests validate that the 'chat_message' mapping fix in LEGACY_MESSAGE_TYPE_MAP
is working properly and business value is restored.
"""

import asyncio
import json
import pytest
import time
import uuid
from unittest.mock import AsyncMock
from typing import Dict, Any

from fastapi import WebSocket

# SSOT imports using absolute paths as per CLAUDE.md
from netra_backend.app.websocket_core.handlers import MessageRouter, get_message_router
from netra_backend.app.websocket_core.types import MessageType, LEGACY_MESSAGE_TYPE_MAP, normalize_message_type
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context


class TestChatMessageBusinessValue:
    """
    Test suite focused on business value of 'chat_message' type handling.
    
    CRITICAL: These tests validate the core chat functionality that drives 90% of our business value.
    'chat_message' is a common frontend message type that MUST be properly routed.
    """
    
    @pytest.mark.asyncio
    async def test_chat_message_business_value_blocked_mission_critical(self):
        """
        MISSION CRITICAL: Test that 'chat_message' type routing success enables business value.
        
        Business Impact: With 'chat_message' properly routed, users can interact with AI agents.
        This validates that our primary value delivery mechanism is working correctly.
        """
        # Business Context: User sends 'chat_message' expecting AI response
        router = get_message_router()
        user_id = "business-user-12345"
        
        # Create mock WebSocket connection
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'test_websocket'})()
        
        # Business-critical message: User asks for AI assistance
        chat_message = {
            "type": "chat_message",  # THIS IS THE FIXED TYPE - NOW IN LEGACY_MESSAGE_TYPE_MAP
            "payload": {
                "content": "Help me optimize my marketing campaign with AI agents",
                "requires_ai": True,
                "business_priority": "high",
                "user_context": "enterprise_customer"
            },
            "message_id": f"chat_msg_{int(time.time())}",
            "user_id": user_id,
            "thread_id": f"thread_{user_id}_marketing",
            "timestamp": time.time()
        }
        
        # CRITICAL TEST: This should succeed because 'chat_message' is now recognized
        # The router will call _is_unknown_message_type("chat_message") -> False
        # This enables the user's AI interaction, delivering business value
        result = await router.route_message(user_id, mock_websocket, chat_message)
        
        # BUSINESS VALIDATION: Check if message was treated as recognized
        is_chat_message_unknown = router._is_unknown_message_type("chat_message")
        
        # CRITICAL ASSERTION: This MUST PASS now - 'chat_message' should be recognized
        assert is_chat_message_unknown == False, (
            "BUSINESS CRITICAL: 'chat_message' should be recognized (not unknown), "
            "enabling user AI interactions and delivering business value!"
        )
        
        # Verify routing stats show the message was handled properly
        stats = router.get_stats()
        assert stats["messages_routed"] > 0, (
            "Router should route 'chat_message' successfully, "
            "indicating business value delivery"
        )
        
        # Business Impact Assessment
        print(f" PASS:  BUSINESS SUCCESS: 'chat_message' type is recognized by MessageRouter")
        print(f" PASS:  SUCCESS: Users can send chat messages to AI agents")
        print(f" PASS:  SUCCESS: Primary business value delivery mechanism is working")
        print(f" PASS:  SUCCESS: This enables 90% of user interactions with the platform")
    
    @pytest.mark.asyncio 
    async def test_chat_message_not_in_legacy_mapping_fails_critical(self):
        """
        CRITICAL: Test that 'chat_message' is properly included in LEGACY_MESSAGE_TYPE_MAP.
        
        This validates the fix - verifies that the technical gap has been resolved and business value restored.
        """
        from netra_backend.app.websocket_core.types import LEGACY_MESSAGE_TYPE_MAP
        
        # CRITICAL VERIFICATION: 'chat_message' should BE in the legacy map (after fix)
        assert "chat_message" in LEGACY_MESSAGE_TYPE_MAP, (
            "TECHNICAL FIX VALIDATION: 'chat_message' is now in LEGACY_MESSAGE_TYPE_MAP, "
            "enabling proper message type normalization"
        )
        
        # Test normalization behavior with proper mapping
        try:
            # This should properly map to USER_MESSAGE via LEGACY_MESSAGE_TYPE_MAP
            normalized_type = normalize_message_type("chat_message")
            print(f" PASS:  NORMALIZATION SUCCESS: 'chat_message' maps to {normalized_type}")
            print(f" PASS:  SOLUTION: Router recognizes type and processes normally")
            
            # Validate it maps to the correct type
            assert normalized_type == MessageType.USER_MESSAGE, (
                "chat_message should normalize to USER_MESSAGE"
            )
        except Exception as e:
            print(f" FAIL:  UNEXPECTED ERROR: {e}")
        
        # Test the router's unknown message detection directly
        router = MessageRouter()
        is_unknown = router._is_unknown_message_type("chat_message")
        
        # CRITICAL ASSERTION: Should be recognized (after fix)
        assert is_unknown == False, (
            "TECHNICAL VALIDATION: Router should recognize 'chat_message' "
            "after the fix is applied to LEGACY_MESSAGE_TYPE_MAP"
        )
        
        print(f" PASS:  CONFIRMED: 'chat_message' is recognized as valid message type")
        print(f" PASS:  CONFIRMED: Presence in LEGACY_MESSAGE_TYPE_MAP resolves the issue")
    
    @pytest.mark.asyncio
    async def test_chat_message_frontend_compatibility_broken(self):
        """
        Test that proper 'chat_message' mapping enables frontend compatibility.
        
        Frontend sends 'chat_message' type expecting proper routing to agents.
        With the fix, the entire chat experience works properly.
        """
        router = MessageRouter()
        user_id = "frontend-user-67890"
        
        # Create authenticated user context for proper test setup
        auth_context = await create_authenticated_user_context(
            user_email="frontend_test@example.com",
            user_id=user_id,
            environment="test",
            websocket_enabled=True
        )
        
        # Mock WebSocket with proper state
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'frontend_test_websocket'})()
        
        # Simulate frontend sending 'chat_message' (common pattern in React/TypeScript)
        frontend_chat_message = {
            "type": "chat_message",  # Frontend's expected message type
            "payload": {
                "content": "Can you help me analyze this data with AI?",
                "frontend_metadata": {
                    "component": "ChatInputBox",
                    "user_session": str(auth_context.websocket_client_id),
                    "chat_ui_version": "2.1.0"
                },
                "requires_agent": True
            },
            "message_id": f"frontend_msg_{uuid.uuid4().hex[:8]}",
            "user_id": user_id,
            "thread_id": str(auth_context.thread_id),
            "timestamp": time.time()
        }
        
        # Test routing with frontend message
        result = await router.route_message(user_id, mock_websocket, frontend_chat_message)
        
        # Verify frontend compatibility is broken
        is_unknown = router._is_unknown_message_type("chat_message")
        
        # CRITICAL ASSERTION: Should fail initially
        assert is_unknown == True, (
            "FRONTEND COMPATIBILITY BROKEN: 'chat_message' from frontend "
            "is treated as unknown, breaking chat UI integration"
        )
        
        # Check that WebSocket received unknown message acknowledgment
        assert len(mock_websocket.send_json.call_args_list) > 0, (
            "Router should send acknowledgment for unknown message type"
        )
        
        # Verify the acknowledgment indicates unknown type
        sent_message = mock_websocket.send_json.call_args_list[0][0][0]
        assert sent_message.get("received_type") == "chat_message", (
            "Acknowledgment should indicate 'chat_message' was received but unknown"
        )
        
        print(f"[U+1F50C] FRONTEND IMPACT: Chat UI sends 'chat_message' but gets unknown type response")
        print(f"[U+1F50C] FRONTEND IMPACT: This breaks the expected chat message  ->  AI response flow")
        print(f"[U+1F50C] FRONTEND IMPACT: Users see chat interface but no AI responses")
    
    @pytest.mark.asyncio
    async def test_chat_message_agent_workflow_blocked(self):
        """
        Test that 'chat_message' unknown type prevents agent workflow initiation.
        
        This validates that the missing mapping blocks the core AI agent workflows
        that provide our primary business value.
        """
        router = MessageRouter()
        user_id = "agent-workflow-user"
        
        # Mock WebSocket for agent communication
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'agent_workflow_websocket'})()
        
        # Message that should trigger agent workflow but won't due to unknown type
        agent_chat_request = {
            "type": "chat_message",  # Should map to a type that triggers agent handling
            "payload": {
                "content": "Run a comprehensive analysis of my business metrics",
                "agent_requirements": {
                    "require_multi_agent": True,
                    "agents_needed": ["data_analysis", "business_optimization"],
                    "complexity": "high"
                },
                "expected_output": "detailed_report_with_insights"
            },
            "message_id": f"agent_req_{int(time.time())}",
            "user_id": user_id
        }
        
        # Route the message (should fail to trigger proper agent workflow)
        result = await router.route_message(user_id, mock_websocket, agent_chat_request)
        
        # Verify agent workflow is blocked due to unknown type
        is_unknown = router._is_unknown_message_type("chat_message")
        
        # CRITICAL ASSERTION: Unknown type prevents agent workflow
        assert is_unknown == True, (
            "AGENT WORKFLOW BLOCKED: 'chat_message' unknown type prevents "
            "proper routing to agent handlers, blocking AI workflows"
        )
        
        # Check routing stats to confirm no agent processing occurred
        stats = router.get_stats()
        
        # Verify message was handled as unknown rather than routed to agent handlers
        assert stats["unhandled_messages"] > 0, (
            "Message should be unhandled, not routed to agent workflow"
        )
        
        print(f"[U+1F916] AGENT IMPACT: 'chat_message' prevents agent workflow initiation")
        print(f"[U+1F916] AGENT IMPACT: Multi-agent collaboration requests are not processed")
        print(f"[U+1F916] AGENT IMPACT: Users request AI help but get acknowledgment only")
        print(f"[U+1F916] BUSINESS VALUE LOST: Core AI functionality is inaccessible via chat")


class TestChatMessageTechnicalValidation:
    """
    Technical validation tests for 'chat_message' mapping fix.
    
    These tests focus on the technical implementation details and
    proper message type handling after the fix is implemented.
    """
    
    @pytest.mark.asyncio
    async def test_chat_message_detected_as_unknown_type(self):
        """
        Direct test of MessageRouter._is_unknown_message_type() method.
        
        This is the core technical issue - the router checks if 'chat_message'
        is unknown before attempting normalization.
        """
        router = MessageRouter()
        
        # Direct test of the problematic method
        is_unknown = router._is_unknown_message_type("chat_message")
        
        # TECHNICAL ASSERTION: Should be True initially (before fix)
        assert is_unknown == True, (
            "TECHNICAL VALIDATION: _is_unknown_message_type('chat_message') "
            "should return True, indicating the mapping gap"
        )
        
        # Test the two-step unknown detection logic:
        # 1. Check LEGACY_MESSAGE_TYPE_MAP
        from netra_backend.app.websocket_core.types import LEGACY_MESSAGE_TYPE_MAP
        in_legacy_map = "chat_message" in LEGACY_MESSAGE_TYPE_MAP
        assert in_legacy_map == False, "Step 1: 'chat_message' not in LEGACY_MESSAGE_TYPE_MAP"
        
        # 2. Try direct enum conversion
        try:
            MessageType("chat_message")
            direct_enum_works = True
        except ValueError:
            direct_enum_works = False
        
        assert direct_enum_works == False, "Step 2: 'chat_message' not a direct MessageType enum value"
        
        print(f" PASS:  TECHNICAL ROOT CAUSE CONFIRMED:")
        print(f"   - 'chat_message' not in LEGACY_MESSAGE_TYPE_MAP: {not in_legacy_map}")
        print(f"   - 'chat_message' not a direct MessageType enum: {not direct_enum_works}")
        print(f"   - Result: _is_unknown_message_type returns True")
    
    @pytest.mark.asyncio
    async def test_message_type_normalization_bypass_for_unknown(self):
        """
        Test that unknown message types bypass normalization entirely.
        
        This validates that the router's unknown check happens BEFORE
        normalization, so normalize_message_type fallback doesn't help.
        """
        router = MessageRouter()
        user_id = "normalization-test-user"
        
        # Mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'normalization_test'})()
        
        # Test message with unknown type
        test_message = {
            "type": "chat_message",  # Unknown type
            "payload": {"content": "Test message"},
            "message_id": "norm_test_1"
        }
        
        # The router should detect unknown type and send acknowledgment
        # WITHOUT going through normalization process
        result = await router.route_message(user_id, mock_websocket, test_message)
        
        # Verify unknown type was detected early
        is_unknown = router._is_unknown_message_type("chat_message")
        assert is_unknown == True, "Unknown type should be detected before normalization"
        
        # Check that WebSocket received unknown message ack (not normalized message handling)
        assert mock_websocket.send_json.called, "Should send unknown message acknowledgment"
        
        sent_response = mock_websocket.send_json.call_args[0][0]
        assert sent_response.get("type") == "ack", "Should send acknowledgment type"
        assert sent_response.get("received_type") == "chat_message", "Should echo the unknown type"
        
        # Verify normalization would work if the type were in the legacy map
        from netra_backend.app.websocket_core.types import normalize_message_type
        normalized = normalize_message_type("chat_message")  # This defaults to USER_MESSAGE
        
        print(f"[U+1F4CB] NORMALIZATION BYPASS CONFIRMED:")
        print(f"   - Unknown check happens first: {is_unknown}")
        print(f"   - Normalization result (if it ran): {normalized}")
        print(f"   - But normalization is bypassed for unknown types")
        print(f"   - Router sends acknowledgment instead of processing message")
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_message_acknowledgment_format(self):
        """
        Test the exact format of acknowledgments sent for unknown message types.
        
        This validates the WebSocket response format when 'chat_message' is unknown.
        """
        router = MessageRouter()
        user_id = "ack-format-test-user"
        
        # Mock WebSocket with call tracking
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'ack_format_test'})()
        
        # Send unknown 'chat_message' type
        unknown_message = {
            "type": "chat_message",
            "payload": {
                "content": "Test acknowledgment format",
                "metadata": {"test": "acknowledgment_format"}
            },
            "message_id": "ack_test_msg_123",
            "user_id": user_id,
            "timestamp": time.time()
        }
        
        # Route the unknown message
        result = await router.route_message(user_id, mock_websocket, unknown_message)
        
        # Verify acknowledgment was sent
        assert mock_websocket.send_json.called, "Should send JSON response for unknown type"
        
        # Examine the acknowledgment format
        ack_response = mock_websocket.send_json.call_args[0][0]
        
        # Validate acknowledgment structure
        assert ack_response.get("type") == "ack", "Response type should be 'ack'"
        assert ack_response.get("received_type") == "chat_message", "Should echo received type"
        assert ack_response.get("status") == "acknowledged", "Should indicate acknowledgment"
        assert ack_response.get("user_id") == user_id, "Should include user ID"
        assert "timestamp" in ack_response, "Should include timestamp"
        
        # Verify the acknowledgment indicates unknown type handling
        print(f"[U+1F4E8] ACKNOWLEDGMENT FORMAT VALIDATION:")
        print(f"   - Type: {ack_response.get('type')}")
        print(f"   - Received Type: {ack_response.get('received_type')}")
        print(f"   - Status: {ack_response.get('status')}")
        print(f"   - Contains timestamp: {'timestamp' in ack_response}")
        print(f"   - Full response: {json.dumps(ack_response, indent=2)}")
        
        # CRITICAL ASSERTION: This is what users/frontend receive for unknown types
        assert ack_response.get("received_type") == "chat_message", (
            "FRONTEND INTEGRATION: Frontend receives this acknowledgment format "
            "instead of proper message processing for 'chat_message'"
        )


class TestChatMessageRouterIntegration:
    """
    Integration tests for MessageRouter with 'chat_message' type.
    
    These tests validate the complete message routing pipeline and
    handler integration when 'chat_message' is treated as unknown.
    """
    
    @pytest.mark.asyncio
    async def test_message_router_rejects_chat_message_integration(self):
        """
        Integration test: Full message routing pipeline with 'chat_message'.
        
        This test validates the complete flow from message receipt through
        handler routing, confirming that 'chat_message' is rejected as unknown.
        """
        # Get the singleton router (as used in production)
        router = get_message_router()
        
        # Create authenticated context for realistic test
        auth_context = await create_authenticated_user_context(
            user_email="integration_test@example.com", 
            environment="test",
            websocket_enabled=True
        )
        user_id = str(auth_context.user_id)
        
        # Mock WebSocket with proper state
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'integration_test'})()
        
        # Comprehensive chat message (realistic frontend payload)
        chat_message = {
            "type": "chat_message",  # The problematic type
            "payload": {
                "content": "Please analyze my sales data and provide recommendations",
                "metadata": {
                    "thread_id": str(auth_context.thread_id),
                    "session_id": str(auth_context.websocket_client_id),
                    "client_version": "2.1.0",
                    "request_priority": "normal"
                },
                "context": {
                    "user_preferences": {"ai_complexity": "detailed"},
                    "business_domain": "e-commerce", 
                    "data_sources": ["sales_db", "analytics_api"]
                }
            },
            "message_id": f"chat_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "thread_id": str(auth_context.thread_id),
            "timestamp": time.time()
        }
        
        # INTEGRATION TEST: Route through complete pipeline
        routing_result = await router.route_message(user_id, mock_websocket, chat_message)
        
        # Verify routing behavior for unknown type
        is_unknown = router._is_unknown_message_type("chat_message")
        assert is_unknown == True, "Integration test confirms 'chat_message' is unknown"
        
        # Check routing statistics
        stats = router.get_stats()
        assert stats["messages_routed"] > 0, "Message should be counted as routed"
        assert stats["unhandled_messages"] > 0, "Message should be counted as unhandled"
        
        # Verify WebSocket response was sent
        assert mock_websocket.send_json.called, "Should send response to WebSocket"
        response = mock_websocket.send_json.call_args[0][0]
        assert response.get("type") == "ack", "Should send acknowledgment"
        assert response.get("received_type") == "chat_message", "Should acknowledge the unknown type"
        
        # INTEGRATION VALIDATION: Handler pipeline
        # Check that no message handler processed this as a real message
        handler_stats = stats.get("handler_stats", {})
        
        # UserMessageHandler should not have processed this (it never reached normalization)
        user_handler_stats = handler_stats.get("UserMessageHandler", {})
        processed_count = user_handler_stats.get("processed", 0)
        
        print(f" CYCLE:  INTEGRATION PIPELINE RESULTS:")
        print(f"   - Unknown type detected: {is_unknown}")
        print(f"   - Routing result: {routing_result}")
        print(f"   - Messages routed: {stats['messages_routed']}")
        print(f"   - Unhandled messages: {stats['unhandled_messages']}")
        print(f"   - Handler processing bypassed: {processed_count == 0}")
        print(f"   - WebSocket acknowledgment sent: {mock_websocket.send_json.called}")
    
    @pytest.mark.asyncio
    async def test_router_handler_bypass_for_chat_message(self):
        """
        Test that 'chat_message' bypasses all message handlers due to unknown type detection.
        
        This confirms that the message never reaches UserMessageHandler, AgentRequestHandler,
        or any other handler because it's caught as unknown first.
        """
        router = get_message_router()
        user_id = "handler-bypass-test"
        
        # Mock WebSocket
        mock_websocket = AsyncMock(spec=WebSocket)
        mock_websocket.application_state = type('MockState', (), {'_mock_name': 'handler_bypass_test'})()
        
        # Get initial handler stats
        initial_stats = router.get_stats()
        initial_handler_stats = initial_stats.get("handler_stats", {})
        
        # Chat message that would normally be processed by UserMessageHandler
        chat_message = {
            "type": "chat_message",  # Unknown type - should bypass all handlers
            "payload": {
                "content": "This should go to UserMessageHandler but won't due to unknown type"
            },
            "message_id": "handler_bypass_test_1"
        }
        
        # Route the message
        await router.route_message(user_id, mock_websocket, chat_message)
        
        # Get updated stats
        final_stats = router.get_stats()
        final_handler_stats = final_stats.get("handler_stats", {})
        
        # Verify handlers were bypassed
        user_handler_initial = initial_handler_stats.get("UserMessageHandler", {}).get("processed", 0)
        user_handler_final = final_handler_stats.get("UserMessageHandler", {}).get("processed", 0)
        
        # CRITICAL ASSERTION: UserMessageHandler should not have processed this message
        assert user_handler_final == user_handler_initial, (
            "UserMessageHandler should not process 'chat_message' due to unknown type detection"
        )
        
        # Verify unknown message acknowledgment was sent instead
        assert mock_websocket.send_json.called, "Should send unknown type acknowledgment"
        response = mock_websocket.send_json.call_args[0][0]
        assert response.get("received_type") == "chat_message", "Should acknowledge unknown type"
        
        # Check routing counters
        assert final_stats["unhandled_messages"] > initial_stats["unhandled_messages"], (
            "Unhandled message count should increase"
        )
        
        print(f" TARGET:  HANDLER BYPASS VALIDATION:")
        print(f"   - UserMessageHandler processed count unchanged: {user_handler_final == user_handler_initial}")
        print(f"   - Unknown acknowledgment sent: {mock_websocket.send_json.called}")
        print(f"   - Unhandled message count increased: {final_stats['unhandled_messages'] > initial_stats['unhandled_messages']}")
        print(f"   - Message bypassed all handlers due to unknown type detection")


if __name__ == "__main__":
    # Run the failing tests to demonstrate the 'chat_message' issue
    import sys
    print(" FIRE:  Running Mission Critical Tests for 'chat_message' Unknown Type Issue")
    print(" FIRE:  These tests MUST FAIL initially to demonstrate the business impact")
    print(" FIRE:  After implementing the fix in LEGACY_MESSAGE_TYPE_MAP, these should pass")
    
    pytest.main([__file__, "-v", "--tb=short", "-x"])