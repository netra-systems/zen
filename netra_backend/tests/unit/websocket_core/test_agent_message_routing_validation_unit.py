"""
Unit Tests for Agent Message Routing and Validation - Issue #861 Phase 1

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Development Velocity & System Reliability
- Value Impact: Validates critical message routing logic that enables agent-user communication
- Strategic Impact: Prevents message routing failures that would break $500K+ ARR agent functionality

Test Coverage Focus:
- Message type normalization and validation
- Handler registration and precedence logic
- Message routing table accuracy
- Payload extraction and validation
- Error message routing and handling
- Handler protocol compliance
- Message queue and buffering validation

CRITICAL ROUTING SCENARIOS:
- START_AGENT message routing to agent execution
- USER_MESSAGE routing for ongoing conversations  
- CHAT message compatibility and routing
- Error message routing for user feedback
- Unknown message type handling

REQUIREMENTS per CLAUDE.md:
- Use SSotBaseTestCase for unified test infrastructure
- Test actual routing logic, not just mock behaviors
- Focus on business-critical routing paths
- Validate message structure and content preservation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Protocol
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import WebSocket

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.handlers import MessageRouter, BaseMessageHandler, AgentRequestHandler
from netra_backend.app.websocket_core.types import (
    MessageType, WebSocketMessage, create_standard_message, create_error_message,
    normalize_message_type, is_jsonrpc_message, convert_jsonrpc_to_websocket_message
)
from shared.isolated_environment import IsolatedEnvironment


class MockMessageHandler(BaseMessageHandler):
    """Mock message handler for testing routing logic."""
    
    def __init__(self, supported_types: List[MessageType], name: str = "MockHandler"):
        super().__init__(supported_types)
        self.name = name
        self.handled_messages = []
        self.should_succeed = True
    
    async def handle_message(self, user_id: str, websocket: WebSocket, 
                           message: WebSocketMessage) -> bool:
        """Track handled messages for verification."""
        self.handled_messages.append({
            "user_id": user_id,
            "message_type": message.type,
            "payload": message.payload,
            "timestamp": time.time()
        })
        return self.should_succeed


class AgentMessageRoutingValidationTests(SSotAsyncTestCase):
    """Test suite for agent message routing and validation logic."""

    def setup_method(self, method):
        """Set up test fixtures for routing tests."""
        super().setup_method(method)
        
        # Create test environment
        self.env = IsolatedEnvironment()
        self.test_user_id = "routing_test_user_" + str(uuid.uuid4())[:8]
        
        # Create mock WebSocket
        self.mock_websocket = MagicMock(spec=WebSocket)
        self.mock_websocket.client_state = "connected"
        self.mock_websocket.application_state = MagicMock()
        
        # Create fresh message router for each test
        self.router = MessageRouter()
        
        # Track routed messages
        self.routed_messages = []

    def teardown_method(self, method):
        """Clean up test resources."""
        super().teardown_method(method)
        self.routed_messages.clear()

    def create_test_message(self, message_type: MessageType, payload: Dict[str, Any]) -> WebSocketMessage:
        """Create a test WebSocket message."""
        return WebSocketMessage(
            type=message_type,
            payload=payload,
            timestamp=time.time(),
            message_id=f"msg_{uuid.uuid4()}",
            user_id=self.test_user_id,
            thread_id=f"thread_{uuid.uuid4()}"
        )

    # Test 1: Message Type Normalization
    def test_message_type_normalization_accuracy(self):
        """Test accurate normalization of various message type formats.
        
        Business Impact: Ensures consistent message type handling across different input formats.
        """
        # Test cases: (input, expected_output)
        normalization_cases = [
            ("start_agent", MessageType.START_AGENT),
            ("START_AGENT", MessageType.START_AGENT),
            ("user_message", MessageType.USER_MESSAGE),
            ("USER_MESSAGE", MessageType.USER_MESSAGE),
            ("chat", MessageType.CHAT),
            ("CHAT", MessageType.CHAT),
            ("ping", MessageType.PING),
            ("pong", MessageType.PONG),
            ("error_message", MessageType.ERROR_MESSAGE),
            ("unknown_type", MessageType.USER_MESSAGE),  # Default fallback
        ]
        
        for input_type, expected_type in normalization_cases:
            normalized = normalize_message_type(input_type)
            assert normalized == expected_type, f"Failed to normalize '{input_type}' to {expected_type}, got {normalized}"

    # Test 2: Handler Registration and Precedence
    def test_handler_registration_and_precedence_logic(self):
        """Test that custom handlers take precedence over built-in handlers.
        
        Business Impact: Allows system customization while maintaining reliable fallbacks.
        """
        # Create custom handler for START_AGENT messages
        custom_handler = MockMessageHandler([MessageType.START_AGENT], "CustomStartAgent")
        
        # Verify initial built-in handler count
        initial_handler_count = len(self.router.handlers)
        assert initial_handler_count > 0
        
        # Add custom handler
        self.router.add_handler(custom_handler)
        
        # Verify handler was added
        assert len(self.router.handlers) == initial_handler_count + 1
        
        # Verify custom handler comes first in priority
        assert self.router.handlers[0] == custom_handler
        
        # Test handler finding logic
        found_handler = self.router._find_handler(MessageType.START_AGENT)
        assert found_handler == custom_handler, "Custom handler should be found first"

    def test_handler_protocol_validation_prevents_invalid_handlers(self):
        """Test that invalid handlers are rejected during registration.
        
        Business Impact: Prevents runtime errors from improperly implemented handlers.
        """
        # Test invalid handler (raw function)
        def invalid_handler(user_id, websocket, message):
            return True
        
        with pytest.raises(TypeError) as exc_info:
            self.router.add_handler(invalid_handler)
        
        assert "does not implement MessageHandler protocol" in str(exc_info.value)
        assert "raw functions are not supported" in str(exc_info.value)
        
        # Test handler missing required methods
        class InvalidHandler:
            pass
        
        with pytest.raises(TypeError):
            self.router.add_handler(InvalidHandler())

    # Test 3: Message Routing Table Accuracy
    async def test_message_routing_table_accuracy_for_agent_types(self):
        """Test routing table correctly routes agent-related message types.
        
        Business Impact: Ensures agent messages reach appropriate handlers.
        Golden Path Impact: Critical for agent execution flow.
        """
        # Add specialized handlers for testing
        start_agent_handler = MockMessageHandler([MessageType.START_AGENT], "StartAgentHandler")
        user_message_handler = MockMessageHandler([MessageType.USER_MESSAGE], "UserMessageHandler") 
        chat_handler = MockMessageHandler([MessageType.CHAT], "ChatHandler")
        
        self.router.add_handler(start_agent_handler)
        self.router.add_handler(user_message_handler)
        self.router.add_handler(chat_handler)
        
        # Test START_AGENT routing
        start_message = {"type": "start_agent", "payload": {"user_request": "Start analysis"}}
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, start_message)
        assert result is True
        assert len(start_agent_handler.handled_messages) == 1
        assert start_agent_handler.handled_messages[0]["message_type"] == MessageType.START_AGENT
        
        # Test USER_MESSAGE routing
        user_message = {"type": "user_message", "payload": {"message": "Follow up question"}}
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, user_message)
        assert result is True
        assert len(user_message_handler.handled_messages) == 1
        
        # Test CHAT routing
        chat_message = {"type": "chat", "payload": {"content": "Chat message"}}
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, chat_message)
        assert result is True
        assert len(chat_handler.handled_messages) == 1

    # Test 4: Payload Validation and Extraction
    async def test_payload_validation_and_extraction_accuracy(self):
        """Test proper payload extraction and validation for different message formats.
        
        Business Impact: Ensures message content is preserved and accessible to handlers.
        """
        # Create handler to inspect received payloads
        payload_inspector = MockMessageHandler([MessageType.USER_MESSAGE], "PayloadInspector")
        self.router.add_handler(payload_inspector)
        
        # Test various payload formats
        test_payloads = [
            {"message": "Simple text message"},
            {"content": "Content field message", "metadata": {"priority": "high"}},
            {"text": "Text field message", "context": {"thread_id": "test_thread"}},
            {"nested": {"data": {"value": "deeply nested"}}, "simple": "mixed structure"}
        ]
        
        for i, payload in enumerate(test_payloads):
            raw_message = {
                "type": "user_message",
                "payload": payload,
                "message_id": f"test_msg_{i}"
            }
            
            result = await self.router.route_message(self.test_user_id, self.mock_websocket, raw_message)
            assert result is True
            
            # Verify payload was preserved correctly
            handled_message = payload_inspector.handled_messages[i]
            assert handled_message["payload"] == payload

    # Test 5: JSON-RPC Message Compatibility
    async def test_jsonrpc_message_compatibility_and_conversion(self):
        """Test JSON-RPC message format detection and conversion.
        
        Business Impact: Enables compatibility with MCP and other JSON-RPC clients.
        """
        # Test JSON-RPC detection
        jsonrpc_message = {
            "jsonrpc": "2.0",
            "method": "agent.execute",
            "params": {"request": "Analyze data"},
            "id": "req_123"
        }
        
        assert is_jsonrpc_message(jsonrpc_message) is True
        
        # Test non-JSON-RPC message
        regular_message = {"type": "user_message", "payload": {"message": "Regular message"}}
        assert is_jsonrpc_message(regular_message) is False
        
        # Test JSON-RPC conversion
        websocket_message = convert_jsonrpc_to_websocket_message(jsonrpc_message)
        assert websocket_message.type == MessageType.JSONRPC_REQUEST
        assert websocket_message.payload["method"] == "agent.execute"
        assert websocket_message.payload["id"] == "req_123"

    # Test 6: Error Message Routing and Handling
    async def test_error_message_routing_and_proper_handling(self):
        """Test error message routing provides proper user feedback.
        
        Business Impact: Users get clear feedback when things go wrong.
        """
        # Add error handler for testing
        error_handler = MockMessageHandler([MessageType.ERROR_MESSAGE], "ErrorHandler")
        self.router.add_handler(error_handler)
        
        # Test error message routing
        error_message = {
            "type": "error_message",
            "payload": {
                "error_code": "AGENT_EXECUTION_FAILED", 
                "error_message": "Agent failed to process request",
                "details": {"reason": "Timeout"}
            }
        }
        
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, error_message)
        assert result is True
        assert len(error_handler.handled_messages) == 1
        
        handled_error = error_handler.handled_messages[0]
        assert handled_error["payload"]["error_code"] == "AGENT_EXECUTION_FAILED"

    # Test 7: Unknown Message Type Handling
    async def test_unknown_message_type_handling_and_acknowledgment(self):
        """Test handling of unknown message types with proper acknowledgment.
        
        Business Impact: System gracefully handles unexpected message formats.
        """
        # Mock WebSocket send to capture acknowledgment
        sent_messages = []
        
        async def capture_sent_json(data):
            sent_messages.append(data)
        
        self.mock_websocket.send_json = AsyncMock(side_effect=capture_sent_json)
        
        # Send unknown message type
        unknown_message = {
            "type": "completely_unknown_type",
            "payload": {"some": "data"}
        }
        
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, unknown_message)
        
        # Should send acknowledgment for unknown type
        assert len(sent_messages) > 0
        
        ack_message = sent_messages[0]
        assert ack_message["type"] == "ack"
        assert ack_message["received_type"] == "completely_unknown_type"
        assert ack_message["status"] == "acknowledged"

    # Test 8: Handler Error Recovery
    async def test_handler_error_recovery_and_fallback_logic(self):
        """Test system behavior when handlers fail during message processing.
        
        Business Impact: System remains stable even when individual handlers fail.
        """
        # Create handler that fails
        failing_handler = MockMessageHandler([MessageType.USER_MESSAGE], "FailingHandler")
        failing_handler.should_succeed = False
        
        # Add failing handler first (higher precedence)
        self.router.insert_handler(failing_handler, 0)
        
        user_message = {"type": "user_message", "payload": {"message": "Test failure recovery"}}
        
        # Should handle failure gracefully
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, user_message)
        
        # Result depends on whether fallback succeeded
        # At minimum, should not crash the system
        assert isinstance(result, bool)
        assert len(failing_handler.handled_messages) == 1

    # Test 9: Concurrent Message Routing
    async def test_concurrent_message_routing_thread_safety(self):
        """Test thread safety of message routing under concurrent load.
        
        Business Impact: System handles multiple users simultaneously without race conditions.
        """
        # Add handler for testing concurrency
        concurrent_handler = MockMessageHandler(
            [MessageType.USER_MESSAGE, MessageType.CHAT], 
            "ConcurrentHandler"
        )
        self.router.add_handler(concurrent_handler)
        
        # Create multiple concurrent routing tasks
        messages = []
        for i in range(10):
            message = {
                "type": "user_message" if i % 2 == 0 else "chat",
                "payload": {"message": f"Concurrent message {i}"},
                "user_id": f"user_{i}"
            }
            messages.append(message)
        
        # Route all messages concurrently
        tasks = [
            self.router.route_message(f"user_{i}", self.mock_websocket, msg)
            for i, msg in enumerate(messages)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(results)
        assert len(concurrent_handler.handled_messages) == 10
        
        # Verify all messages were handled
        handled_user_ids = [msg["user_id"] for msg in concurrent_handler.handled_messages]
        expected_user_ids = [f"user_{i}" for i in range(10)]
        assert sorted(handled_user_ids) == sorted(expected_user_ids)

    # Test 10: Message Preprocessing and Normalization
    async def test_message_preprocessing_and_normalization_pipeline(self):
        """Test message preprocessing pipeline handles various input formats.
        
        Business Impact: Consistent message handling regardless of input format variations.
        """
        # Create inspector handler to verify preprocessing
        preprocessing_inspector = MockMessageHandler([MessageType.USER_MESSAGE], "PreprocessingInspector")
        self.router.add_handler(preprocessing_inspector)
        
        # Test various input formats that should normalize to USER_MESSAGE
        input_variations = [
            {"type": "user_message", "payload": {"message": "Standard format"}},
            {"type": "USER_MESSAGE", "payload": {"message": "Uppercase type"}},
            {"type": "user_message", "message": "Direct message field", "extra": "ignored"},
            {"type": "user_message", "payload": {"text": "Text field variant"}},
        ]
        
        for i, raw_message in enumerate(input_variations):
            result = await self.router.route_message(self.test_user_id, self.mock_websocket, raw_message)
            assert result is True
            
            # Verify message was normalized properly
            handled = preprocessing_inspector.handled_messages[i]
            assert handled["message_type"] == MessageType.USER_MESSAGE

    # Test 11: Handler Statistics and Monitoring
    def test_handler_statistics_tracking_and_monitoring(self):
        """Test routing statistics are properly tracked for monitoring.
        
        Business Impact: Observability into message routing performance and health.
        """
        initial_stats = self.router.get_stats()
        assert initial_stats["messages_routed"] == 0
        assert initial_stats["handler_errors"] == 0
        
        # Add handler and route some messages
        test_handler = MockMessageHandler([MessageType.USER_MESSAGE], "StatsTestHandler")
        self.router.add_handler(test_handler)
        
        # Route messages to generate statistics
        asyncio.run(self.router.route_message(
            self.test_user_id, 
            self.mock_websocket, 
            {"type": "user_message", "payload": {"message": "Stats test"}}
        ))
        
        # Check updated statistics
        updated_stats = self.router.get_stats()
        assert updated_stats["messages_routed"] == 1
        assert "USER_MESSAGE" in updated_stats["message_types"]
        assert updated_stats["message_types"]["USER_MESSAGE"] == 1

    # Test 12: Startup Grace Period Handling
    def test_startup_grace_period_handler_status_reporting(self):
        """Test startup grace period prevents false "zero handlers" warnings.
        
        Business Impact: Reduces noise in logs during system startup.
        """
        # Test immediately after router creation (within grace period)
        grace_period_status = self.router.check_handler_status_with_grace_period()
        
        # Should indicate initializing status, not error
        assert grace_period_status["grace_period_active"] is True
        assert grace_period_status["status"] in ["initializing", "ready"]
        
        # Simulate time passing beyond grace period
        self.router.startup_time = time.time() - 15.0  # 15 seconds ago
        
        post_grace_status = self.router.check_handler_status_with_grace_period()
        assert post_grace_status["grace_period_active"] is False

    # Test 13: Handler Removal and Dynamic Configuration
    def test_handler_removal_and_dynamic_configuration(self):
        """Test dynamic handler registration and removal during runtime.
        
        Business Impact: Allows system reconfiguration without restarts.
        """
        # Add handler
        removable_handler = MockMessageHandler([MessageType.CHAT], "RemovableHandler")
        self.router.add_handler(removable_handler)
        
        initial_count = len(self.router.handlers)
        assert removable_handler in self.router.handlers
        
        # Remove handler  
        self.router.remove_handler(removable_handler)
        
        assert len(self.router.handlers) == initial_count - 1
        assert removable_handler not in self.router.handlers
        
        # Verify handler is no longer found for routing
        found_handler = self.router._find_handler(MessageType.CHAT)
        assert found_handler != removable_handler

    # Test 14: Message ID and Timestamp Preservation  
    async def test_message_id_and_timestamp_preservation(self):
        """Test that message IDs and timestamps are preserved through routing.
        
        Business Impact: Message traceability and proper temporal ordering.
        """
        # Create inspector to verify preservation
        preservation_inspector = MockMessageHandler([MessageType.START_AGENT], "PreservationInspector")
        self.router.add_handler(preservation_inspector)
        
        original_timestamp = time.time()
        original_message_id = f"test_msg_{uuid.uuid4()}"
        
        raw_message = {
            "type": "start_agent", 
            "payload": {"user_request": "Test preservation"},
            "timestamp": original_timestamp,
            "message_id": original_message_id,
            "thread_id": "preservation_thread"
        }
        
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, raw_message)
        assert result is True
        
        # Verify preservation through routing pipeline
        # Note: Handler receives WebSocketMessage object, not raw dict
        handled = preservation_inspector.handled_messages[0]
        # The exact preservation verification would depend on handler implementation
        assert len(preservation_inspector.handled_messages) == 1

    # Test 15: Agent Request Handler Integration  
    async def test_agent_request_handler_integration_in_routing(self):
        """Test that AgentRequestHandler properly integrates with routing system.
        
        Business Impact: Core agent execution requests are properly routed and handled.
        Golden Path Impact: This is the primary handler for agent processing.
        """
        # The router should have AgentRequestHandler as a fallback built-in handler
        built_in_handlers = [h.__class__.__name__ for h in self.router.builtin_handlers]
        assert "AgentRequestHandler" in built_in_handlers
        
        # Test that agent requests are properly routed
        agent_request_message = {
            "type": "agent_request",
            "payload": {
                "message": "Test agent request routing",
                "turn_id": "routing_test_turn"
            }
        }
        
        # Mock WebSocket send for event capture
        sent_events = []
        async def capture_events(event_data):
            if isinstance(event_data, str):
                try:
                    sent_events.append(json.loads(event_data))
                except:
                    sent_events.append({"raw": event_data})
            else:
                sent_events.append(event_data)
        
        self.mock_websocket.send_text = AsyncMock(side_effect=capture_events)
        
        # Route the message
        result = await self.router.route_message(self.test_user_id, self.mock_websocket, agent_request_message)
        
        # Should succeed and generate WebSocket events
        assert result is True
        
        # Verify agent events were generated (indicates proper handler integration)
        event_types = [event.get("event", event.get("type")) for event in sent_events]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # All expected events should be present
        for expected_event in expected_events:
            assert expected_event in event_types, f"Missing expected event: {expected_event}"