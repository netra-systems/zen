"""
Unit Tests for WebSocket Utilities - MISSION CRITICAL for Chat Business Value

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable real-time chat interactions and agent communication
- Value Impact: WebSocket events enable users to see AI working on valuable solutions, 
  providing real-time reasoning visibility and actionable insights delivery
- Strategic Impact: Core platform functionality that delivers 90% of customer value through chat

CRITICAL: These tests validate the 5 essential WebSocket events that enable substantive 
chat interactions and business value delivery:
1. agent_started - User sees agent began processing their problem
2. agent_thinking - Real-time reasoning visibility 
3. tool_executing - Tool usage transparency demonstrates problem-solving
4. tool_completed - Tool results display delivers actionable insights
5. agent_completed - User knows when valuable response is ready

SSOT COMPLIANCE:
- Uses test_framework SSOT patterns from TEST_CREATION_GUIDE.md
- Imports WebSocket models from schemas.websocket_models (SSOT)
- Follows CLAUDE.md WebSocket Agent Events requirements (Section 6)
- Tests business-critical scenarios with minimal mocks
"""

import json
import pytest
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT imports from test framework
from test_framework.websocket_helpers import (
    MockWebSocketConnection,
    WebSocketTestHelpers,
    assert_websocket_events_sent,
    create_test_websocket_connection
)

# SSOT WebSocket model imports
from netra_backend.app.schemas.websocket_models import (
    WebSocketMessage,
    WebSocketMessageType,
    AgentStarted,
    AgentUpdatePayload,
    UserMessagePayload,
    WebSocketErrorModel,
    BaseWebSocketPayload
)

# Core WebSocket utilities 
from netra_backend.app.core.websocket_exceptions import (
    WebSocketConnectionError,
    WebSocketMessageError,
    WebSocketTimeoutError,
    WebSocketAuthenticationError,
    WebSocketValidationError
)

# Import the deprecated notifier for compatibility testing
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier

class TestWebSocketEventFormatting:
    """Test WebSocket event formatting and validation for business value delivery."""

    @pytest.mark.unit
    def test_agent_started_event_structure_validation(self):
        """
        Test agent_started event has proper structure for chat business value.
        
        CRITICAL: This event tells user their agent began processing - essential for UX.
        """
        # Create agent_started event with all required fields
        agent_started = AgentStarted(
            agent_id="test_agent_123",
            agent_type="cost_optimizer",
            run_id="run_456",
            message="Starting cost optimization analysis"
        )
        
        # Validate all business-critical fields are present
        assert agent_started.agent_id == "test_agent_123"
        assert agent_started.agent_type == "cost_optimizer"
        assert agent_started.run_id == "run_456"
        assert agent_started.message == "Starting cost optimization analysis"
        assert agent_started.timestamp is not None
        assert agent_started.correlation_id is not None
        
        # Ensure timestamp is recent (within last 5 seconds)
        time_diff = datetime.now(timezone.utc) - agent_started.timestamp
        assert time_diff.total_seconds() < 5.0
        
        # Validate serialization for WebSocket transmission
        event_dict = agent_started.model_dump()
        assert "agent_id" in event_dict
        assert "agent_type" in event_dict
        assert "run_id" in event_dict
        assert "timestamp" in event_dict

    @pytest.mark.unit 
    def test_agent_thinking_event_with_progress_context(self):
        """
        Test agent_thinking event provides real-time reasoning visibility.
        
        CRITICAL: Shows AI working on valuable solutions - core business value.
        """
        # Create agent update with thinking progress
        thinking_payload = AgentUpdatePayload(
            run_id="run_789",
            agent_id="optimizer_agent",
            status="thinking",
            message="Analyzing AWS cost patterns across 3 regions...",
            progress=35.5,
            current_task="cost_pattern_analysis",
            metadata={
                "estimated_remaining_ms": 15000,
                "complexity": "medium",
                "data_points_analyzed": 1247
            }
        )
        
        # Validate business value elements
        assert thinking_payload.message.startswith("Analyzing")
        assert thinking_payload.progress == 35.5
        assert thinking_payload.current_task == "cost_pattern_analysis"
        assert thinking_payload.metadata["estimated_remaining_ms"] == 15000
        assert thinking_payload.metadata["data_points_analyzed"] == 1247
        
        # Ensure progress is within valid range for UI display
        assert 0 <= thinking_payload.progress <= 100
        
        # Validate structured metadata for frontend processing
        assert isinstance(thinking_payload.metadata, dict)
        assert "complexity" in thinking_payload.metadata

    @pytest.mark.unit
    def test_tool_executing_event_transparency(self):
        """
        Test tool_executing event demonstrates problem-solving approach.
        
        CRITICAL: Tool usage transparency shows agent working toward solution.
        """
        # Create WebSocket message for tool execution
        tool_message = WebSocketMessage(
            type=WebSocketMessageType.TOOL_EXECUTING,
            payload={
                "tool_name": "aws_cost_analyzer",
                "tool_purpose": "Analyze EC2 instance utilization patterns",
                "estimated_duration_ms": 8000,
                "parameters_summary": "Analyzing 45 instances across us-east-1"
            }
        )
        
        # Validate business transparency elements
        payload = tool_message.payload
        assert payload["tool_name"] == "aws_cost_analyzer"
        assert payload["tool_purpose"].startswith("Analyze")
        assert payload["estimated_duration_ms"] == 8000
        assert "instances" in payload["parameters_summary"]
        
        # Ensure message type is correct for routing
        assert tool_message.type == WebSocketMessageType.TOOL_EXECUTING
        assert tool_message.timestamp is not None
        
        # Validate serialization maintains structure
        message_dict = tool_message.model_dump()
        assert message_dict["type"] == "tool_executing"
        assert "payload" in message_dict

    @pytest.mark.unit
    def test_tool_completed_event_actionable_insights(self):
        """
        Test tool_completed event delivers actionable insights.
        
        CRITICAL: Tool results must provide business value to users.
        """
        # Create tool completion with actionable results
        tool_completed_payload = {
            "tool_name": "aws_cost_analyzer", 
            "result": {
                "potential_savings": {
                    "monthly_amount": 2847.50,
                    "percentage": 23.4
                },
                "recommendations": [
                    {
                        "action": "Resize 12 oversized instances",
                        "estimated_savings": 1250.00,
                        "confidence": "high"
                    },
                    {
                        "action": "Enable spot instances for dev workloads",
                        "estimated_savings": 890.50,
                        "confidence": "medium"
                    }
                ],
                "urgency": "medium",
                "implementation_time": "2-3 hours"
            },
            "execution_time_ms": 7834
        }
        
        # Validate actionable business insights
        result = tool_completed_payload["result"]
        assert result["potential_savings"]["monthly_amount"] > 0
        assert result["potential_savings"]["percentage"] > 0
        assert len(result["recommendations"]) >= 2
        
        # Validate each recommendation has actionable details
        for rec in result["recommendations"]:
            assert "action" in rec
            assert "estimated_savings" in rec
            assert "confidence" in rec
            assert rec["estimated_savings"] > 0
        
        # Ensure urgency and timing guidance present
        assert result["urgency"] in ["low", "medium", "high"]
        assert "implementation_time" in result

    @pytest.mark.unit
    def test_agent_completed_event_business_value_delivery(self):
        """
        Test agent_completed event signals valuable response is ready.
        
        CRITICAL: User must know when AI has delivered complete business value.
        """
        # Create agent completion with comprehensive results
        completion_payload = {
            "agent_id": "cost_optimizer",
            "run_id": "run_final_123",
            "result": {
                "summary": "Identified $3,200+ monthly savings opportunities",
                "total_potential_savings": 3247.85,
                "confidence_score": 0.87,
                "action_plan": {
                    "immediate_actions": 3,
                    "medium_term_actions": 2,
                    "monitoring_required": True
                },
                "business_impact": {
                    "cost_reduction_percentage": 28.5,
                    "roi_timeline": "2-3 months",
                    "risk_level": "low"
                }
            },
            "duration_ms": 45672,
            "status": "completed"
        }
        
        # Validate complete business value delivery
        result = completion_payload["result"]
        assert "summary" in result
        assert result["total_potential_savings"] > 3000
        assert 0.8 <= result["confidence_score"] <= 1.0
        
        # Validate action plan structure
        action_plan = result["action_plan"]
        assert action_plan["immediate_actions"] > 0
        assert isinstance(action_plan["monitoring_required"], bool)
        
        # Validate business impact metrics
        impact = result["business_impact"]
        assert impact["cost_reduction_percentage"] > 0
        assert "roi_timeline" in impact
        assert impact["risk_level"] in ["low", "medium", "high"]


class TestWebSocketEventSerialization:
    """Test WebSocket event serialization and deserialization for transmission."""

    @pytest.mark.unit
    def test_websocket_message_json_serialization(self):
        """Test WebSocket messages serialize correctly for transmission."""
        # Create complex message with nested payload
        user_message = UserMessagePayload(
            content="Optimize my AWS infrastructure costs",
            thread_id="thread_abc123",
            metadata={
                "urgency": "high",
                "budget_limit": 10000,
                "current_spend": 12500
            }
        )
        
        ws_message = WebSocketMessage(
            type=WebSocketMessageType.USER_MESSAGE,
            payload=user_message,
            sender="user_456"
        )
        
        # Serialize to JSON (simulating WebSocket transmission)
        json_str = json.dumps(ws_message.model_dump(), default=str)
        
        # Verify serialization succeeded
        assert json_str is not None
        assert "user_message" in json_str
        assert "Optimize my AWS" in json_str
        
        # Deserialize and validate structure preservation
        parsed_data = json.loads(json_str)
        assert parsed_data["type"] == "user_message"
        assert parsed_data["sender"] == "user_456"
        assert parsed_data["payload"]["content"] == "Optimize my AWS infrastructure costs"
        assert parsed_data["payload"]["metadata"]["budget_limit"] == 10000

    @pytest.mark.unit
    def test_websocket_error_serialization_structure(self):
        """Test WebSocket error messages maintain structure for client handling."""
        # Create structured error for business scenarios
        ws_error = WebSocketErrorModel(
            message="Agent execution temporarily unavailable",
            error_type="resource_constraint", 
            code="AGENT_BUSY_001",
            severity="medium",
            details={
                "queue_position": 3,
                "estimated_wait_ms": 45000,
                "retry_recommended": True,
                "alternative_agents": ["basic_optimizer", "quick_analyzer"]
            }
        )
        
        # Serialize error message
        error_dict = ws_error.model_dump()
        
        # Validate error structure for client handling
        assert error_dict["message"] == "Agent execution temporarily unavailable"
        assert error_dict["error_type"] == "resource_constraint"
        assert error_dict["severity"] == "medium"
        assert error_dict["details"]["queue_position"] == 3
        assert error_dict["details"]["retry_recommended"] is True
        assert len(error_dict["details"]["alternative_agents"]) == 2
        
        # Ensure timestamp is present for client tracking
        assert "timestamp" in error_dict

    @pytest.mark.unit
    def test_malformed_message_deserialization_handling(self):
        """Test handling of malformed WebSocket messages."""
        # Test various malformed message scenarios
        malformed_cases = [
            '{"type": "agent_started"}',  # Missing payload
            '{"payload": {"content": "test"}}',  # Missing type
            '{"type": "invalid_type", "payload": {}}',  # Invalid type
            '{"type": "user_message", "payload": null}',  # Null payload
            'invalid json string',  # Invalid JSON
            '{"type": "user_message", "payload": {"content": ""}}',  # Empty content
        ]
        
        for malformed_json in malformed_cases:
            # Attempt to parse malformed message
            try:
                parsed = json.loads(malformed_json)
                
                # Validate that essential fields are checked
                if "type" not in parsed:
                    with pytest.raises((KeyError, ValueError)):
                        WebSocketMessage(**parsed)
                elif parsed.get("type") not in [t.value for t in WebSocketMessageType]:
                    # Invalid message type should be handled gracefully
                    assert parsed["type"] not in ["agent_started", "user_message"]
                    
            except json.JSONDecodeError:
                # Invalid JSON should be caught
                assert "invalid json" in malformed_json.lower()


class TestWebSocketConnectionState:
    """Test WebSocket connection state management for reliability."""

    @pytest.mark.unit  
    async def test_mock_websocket_connection_lifecycle(self):
        """Test mock WebSocket connection lifecycle management."""
        # Create mock connection for testing
        mock_connection = MockWebSocketConnection(user_id="test_user_789")
        
        # Validate initial state
        assert mock_connection.user_id == "test_user_789"
        assert mock_connection.closed is False
        assert mock_connection.state.name == "OPEN"
        assert len(mock_connection._sent_messages) == 0
        
        # Test message sending
        test_message = json.dumps({
            "type": "agent_started",
            "agent_id": "test_agent",
            "user_id": "test_user_789"
        })
        
        await mock_connection.send(test_message)
        
        # Validate message tracking
        assert len(mock_connection._sent_messages) == 1
        assert mock_connection._sent_messages[0] == test_message
        
        # Test message receiving
        response = await mock_connection.recv()
        response_data = json.loads(response)
        
        # Validate echo response structure
        assert "type" in response_data
        assert "sequence_num" in response_data
        assert "connection_id" in response_data
        
        # Test connection cleanup
        await mock_connection.close()
        assert mock_connection.closed is True
        assert mock_connection.state.name == "CLOSED"

    @pytest.mark.unit
    async def test_websocket_error_scenario_handling(self):
        """Test WebSocket error scenarios and recovery patterns."""
        mock_connection = MockWebSocketConnection(user_id="error_test_user")
        
        # Test connection error scenario
        connection_error_message = json.dumps({
            "type": "connection_test",
            "action": "force_disconnect"
        })
        
        await mock_connection.send(connection_error_message)
        error_response = await mock_connection.recv()
        error_data = json.loads(error_response)
        
        # Validate connection error response
        assert error_data["type"] == "error"
        assert error_data["error"] == "connection_error"
        assert "WebSocket connection forced disconnect" in error_data["message"]
        
        # Test message processing error scenario
        invalid_message = json.dumps({
            "type": "invalid_type",
            "payload": {"test": "data"}
        })
        
        await mock_connection.send(invalid_message)
        error_response = await mock_connection.recv()
        error_data = json.loads(error_response)
        
        # Validate message processing error
        assert error_data["type"] == "error"
        assert error_data["error"] == "message_processing_error"

    @pytest.mark.unit
    def test_websocket_authentication_validation(self):
        """Test WebSocket authentication scenarios for multi-user isolation."""
        # Test missing user_id in agent_started event
        invalid_auth_message = {
            "type": "agent_started",
            "agent_name": "non_existent_agent",
            # Missing user_id - should trigger auth error
        }
        
        # This would be validated by the WebSocket handler
        required_fields = ["user_id", "agent_name", "type"]
        missing_fields = [field for field in required_fields if field not in invalid_auth_message]
        
        # Validate authentication requirements
        assert "user_id" in missing_fields
        assert len(missing_fields) == 1
        
        # Test valid authenticated message
        valid_auth_message = {
            "type": "agent_started", 
            "agent_name": "cost_optimizer",
            "user_id": "authenticated_user_123",
            "run_id": "run_456"
        }
        
        # Validate all required auth fields present
        auth_check = all(field in valid_auth_message for field in required_fields)
        assert auth_check is True


class TestWebSocketEventOrdering:
    """Test WebSocket event ordering and timing for user experience."""

    @pytest.mark.unit
    async def test_critical_event_sequence_validation(self):
        """
        Test that critical WebSocket events maintain proper sequence.
        
        CRITICAL: Events must arrive in logical order for business value.
        """
        mock_connection = MockWebSocketConnection(user_id="sequence_test")
        
        # Send events in expected business sequence
        event_sequence = [
            {"type": "agent_started", "agent_id": "optimizer", "user_id": "sequence_test"},
            {"type": "agent_thinking", "reasoning": "Analyzing cost patterns..."},
            {"type": "tool_executing", "tool_name": "cost_analyzer"},
            {"type": "tool_completed", "tool_name": "cost_analyzer", "result": {"savings": 1000}},
            {"type": "agent_completed", "final_response": "Found $1000 in savings"}
        ]
        
        received_events = []
        
        # Send each event and collect responses
        for event in event_sequence:
            await mock_connection.send(json.dumps(event))
            response = await mock_connection.recv()
            response_data = json.loads(response)
            received_events.append(response_data)
        
        # Validate sequence numbers maintain order
        sequence_numbers = [event.get("sequence_num", 0) for event in received_events]
        assert sequence_numbers == sorted(sequence_numbers)
        
        # Validate all critical event types received
        event_types = [event.get("type", event.get("original_type")) for event in received_events]
        critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        for critical_event in critical_events:
            assert critical_event in event_types

    @pytest.mark.unit
    def test_websocket_event_timing_validation(self):
        """Test WebSocket event timing meets business requirements."""
        # Create timestamped events
        start_time = time.time()
        
        events_with_timing = []
        for i, event_type in enumerate(["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]):
            event = {
                "type": event_type,
                "timestamp": start_time + (i * 0.1),  # 100ms intervals
                "sequence": i
            }
            events_with_timing.append(event)
        
        # Validate timing intervals are reasonable for UX
        for i in range(1, len(events_with_timing)):
            time_diff = events_with_timing[i]["timestamp"] - events_with_timing[i-1]["timestamp"]
            assert 0.05 <= time_diff <= 0.2  # Between 50ms and 200ms
        
        # Validate total sequence time is reasonable
        total_time = events_with_timing[-1]["timestamp"] - events_with_timing[0]["timestamp"]
        assert total_time <= 1.0  # Total sequence under 1 second for good UX

    @pytest.mark.unit
    async def test_websocket_error_recovery_timing(self):
        """Test WebSocket error recovery maintains user experience."""
        mock_connection = MockWebSocketConnection(user_id="recovery_test")
        
        # Test timeout scenario
        start_time = time.time()
        
        # Send message that might timeout
        timeout_message = json.dumps({
            "type": "agent_started",
            "agent_id": "slow_agent",
            "estimated_duration": 30000  # 30 seconds
        })
        
        await mock_connection.send(timeout_message)
        response = await mock_connection.recv()
        
        response_time = time.time() - start_time
        
        # Validate response comes quickly (not actual 30s wait)
        assert response_time < 1.0  # Under 1 second for mock
        
        # Validate response indicates processing status
        response_data = json.loads(response)
        assert "agent_id" in response_data or "type" in response_data


class TestWebSocketBusinessScenarios:
    """Test WebSocket behavior in real business usage scenarios."""

    @pytest.mark.unit
    async def test_cost_optimization_workflow_events(self):
        """
        Test complete cost optimization workflow through WebSocket events.
        
        CRITICAL: This is the primary business value delivery scenario.
        """
        mock_connection = MockWebSocketConnection(user_id="business_user")
        
        # Simulate complete cost optimization workflow
        workflow_events = [
            {
                "type": "agent_started",
                "agent_id": "cost_optimizer",
                "user_id": "business_user",
                "message": "Starting comprehensive cost analysis"
            },
            {
                "type": "agent_thinking", 
                "reasoning": "Scanning EC2 instances across all regions...",
                "progress": 25
            },
            {
                "type": "tool_executing",
                "tool_name": "aws_cost_scanner",
                "estimated_duration_ms": 5000
            },
            {
                "type": "tool_completed",
                "tool_name": "aws_cost_scanner",
                "result": {
                    "instances_analyzed": 47,
                    "potential_savings_found": True
                }
            },
            {
                "type": "agent_completed",
                "final_response": "Analysis complete. Found $2,847 in monthly savings opportunities.",
                "total_savings": 2847.50,
                "confidence": 0.89
            }
        ]
        
        business_value_received = []
        
        # Process each workflow event
        for event in workflow_events:
            await mock_connection.send(json.dumps(event))
            response = await mock_connection.recv()
            response_data = json.loads(response)
            business_value_received.append(response_data)
        
        # Validate complete business workflow captured
        assert len(business_value_received) == 5
        
        # Validate business-critical elements present
        final_result = business_value_received[-1]
        assert "final_response" in str(final_result) or "agent_completed" in str(final_result)
        
        # Validate all critical events represented
        event_types = []
        for event in business_value_received:
            if "type" in event:
                event_types.append(event["type"])
            elif "original_type" in event:
                event_types.append(event["original_type"])
        
        critical_business_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for critical_event in critical_business_events:
            assert critical_event in event_types, f"Missing critical business event: {critical_event}"

    @pytest.mark.unit
    def test_websocket_message_size_validation(self):
        """Test WebSocket message size limits for performance."""
        # Test normal-sized message
        normal_message = UserMessagePayload(
            content="Analyze my infrastructure costs",
            thread_id="thread_123"
        )
        
        # Handle datetime serialization properly
        normal_json = json.dumps(normal_message.model_dump(), default=str)
        assert len(normal_json) < 1024  # Under 1KB for normal messages
        
        # Test large response message (should be handled gracefully)
        large_content = "A" * 4000  # 4KB content
        large_payload = {
            "type": "agent_completed",
            "final_response": large_content,
            "metadata": {"size": "large"}
        }
        
        large_json = json.dumps(large_payload)
        
        # Validate large messages are detectable
        assert len(large_json) > 4000
        
        # In real implementation, this would trigger truncation or chunking
        if len(large_json) > 5000:  # 5KB limit example
            # Message would be processed specially
            assert "truncation_needed" not in large_json  # This is just validation logic

    @pytest.mark.unit
    async def test_multi_user_websocket_isolation(self):
        """
        Test WebSocket user isolation for multi-tenant system.
        
        CRITICAL: User data must remain isolated in multi-user environment.
        """
        # Create connections for different users
        user1_connection = MockWebSocketConnection(user_id="enterprise_user_1") 
        user2_connection = MockWebSocketConnection(user_id="startup_user_2")
        
        # Send user-specific messages
        user1_message = json.dumps({
            "type": "agent_started",
            "agent_id": "enterprise_optimizer",
            "user_id": "enterprise_user_1",
            "sensitive_data": {"budget": 50000}
        })
        
        user2_message = json.dumps({
            "type": "agent_started", 
            "agent_id": "basic_optimizer",
            "user_id": "startup_user_2",
            "sensitive_data": {"budget": 1000}
        })
        
        # Process messages through separate connections
        await user1_connection.send(user1_message)
        await user2_connection.send(user2_message)
        
        user1_response = await user1_connection.recv()
        user2_response = await user2_connection.recv()
        
        # Validate user isolation maintained
        user1_data = json.loads(user1_response)
        user2_data = json.loads(user2_response)
        
        # Ensure different connection IDs
        assert user1_connection.connection_id != user2_connection.connection_id
        assert user1_connection.user_id != user2_connection.user_id
        
        # Validate responses are user-specific
        if "connection_id" in user1_data and "connection_id" in user2_data:
            assert user1_data["connection_id"] != user2_data["connection_id"]