"""WebSocket Missing Events Implementation Tests.

Tests for the 4 critical missing events identified in SPEC/websocket_communication.xml:
- agent_thinking (intermediate reasoning)
- partial_result (streaming content)  
- tool_executing (tool execution start)
- final_report (comprehensive results)

Business Value: Ensures complete real-time feedback loop for users, improving
engagement and perceived platform responsiveness.

BVJ: Enterprise/Mid - User Retention - Complete event coverage prevents user
confusion about system state and builds confidence in platform reliability.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient
from tests.e2e.config import UnifiedTestConfig


@pytest.mark.e2e
class TestWebSocketMissingEvents:
    """Test suite for missing WebSocket events per SPEC/websocket_communication.xml."""
    
    @pytest.fixture
    async def backend_client(self):
        """Get backend client with proper configuration."""
        config = UnifiedTestConfig()
        client = BackendTestClient(config.backend_service_url)
        try:
            yield client
        finally:
            await client.close()
    
    @pytest.fixture
    async def websocket_client(self):
        """Get WebSocket client with proper configuration."""
        config = UnifiedTestConfig()
        ws_client = WebSocketTestClient(config.endpoints.ws_url)
        try:
            yield ws_client
        finally:
            await ws_client.disconnect()
    
    @pytest.mark.e2e
    async def test_agent_thinking_event_implementation(self, websocket_client):
        """Test agent_thinking event is sent during agent reasoning."""
        # Trigger complex query that should generate thinking events
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {
                "content": "Analyze the performance bottlenecks in a distributed system with microservices"
            }
        })
        
        # Look for agent_thinking events
        thinking_events = []
        timeout = 20.0  # Longer timeout for complex reasoning
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") == "agent_thinking":
                    thinking_events.append(message)
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate agent_thinking events were sent
        assert len(thinking_events) > 0, (
            "agent_thinking events not implemented - required for intermediate reasoning display"
        )
        
        # Validate structure of thinking events
        for event in thinking_events:
            payload = event["payload"]
            
            # Required fields per SPEC/websocket_communication.xml
            assert "thought" in payload, "agent_thinking missing 'thought' field"
            assert isinstance(payload["thought"], str), "thought must be string"
            assert payload["thought"].strip(), "thought cannot be empty"
            
            assert "agent_name" in payload, "agent_thinking missing 'agent_name' field"
            assert isinstance(payload["agent_name"], str), "agent_name must be string"
            
            # Optional fields
            if "step_number" in payload:
                assert isinstance(payload["step_number"], int), "step_number must be integer"
            if "total_steps" in payload:
                assert isinstance(payload["total_steps"], int), "total_steps must be integer"
    
    @pytest.mark.e2e
    async def test_partial_result_event_implementation(self, websocket_client):
        """Test partial_result event for streaming content updates."""
        # Trigger request that should generate streaming results
        await websocket_client.send_message({
            "type": "user_message", 
            "payload": {
                "content": "Generate a detailed analysis report with multiple sections"
            }
        })
        
        # Look for partial_result events
        partial_events = []
        timeout = 25.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") == "partial_result":
                    partial_events.append(message)
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate partial_result events were sent
        assert len(partial_events) > 0, (
            "partial_result events not implemented - required for streaming content display"
        )
        
        # Validate structure and streaming behavior
        accumulated_content = ""
        has_completion_marker = False
        
        for i, event in enumerate(partial_events):
            payload = event["payload"]
            
            # Required fields per spec
            assert "content" in payload, f"partial_result {i} missing 'content' field"
            assert isinstance(payload["content"], str), f"content must be string in event {i}"
            
            assert "agent_name" in payload, f"partial_result {i} missing 'agent_name' field"
            assert isinstance(payload["agent_name"], str), f"agent_name must be string in event {i}"
            
            assert "is_complete" in payload, f"partial_result {i} missing 'is_complete' field"
            assert isinstance(payload["is_complete"], bool), f"is_complete must be boolean in event {i}"
            
            # Accumulate content to verify streaming
            accumulated_content += payload["content"]
            
            if payload["is_complete"]:
                has_completion_marker = True
        
        # Validate streaming behavior
        assert accumulated_content.strip(), "No content accumulated from partial_result events"
        assert has_completion_marker, "No completion marker found in partial_result stream"
    
    @pytest.mark.e2e
    async def test_tool_executing_event_implementation(self, websocket_client):
        """Test tool_executing event when tools are invoked."""
        # Trigger request that should invoke tools
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {
                "content": "Use tools to analyze current system status and performance metrics"
            }
        })
        
        # Look for tool_executing events
        tool_events = []
        timeout = 20.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") == "tool_executing":
                    tool_events.append(message)
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate tool_executing events were sent
        assert len(tool_events) > 0, (
            "tool_executing events not implemented - required for tool execution feedback"
        )
        
        # Validate structure of tool events
        for i, event in enumerate(tool_events):
            payload = event["payload"]
            
            # Required fields per spec
            assert "tool_name" in payload, f"tool_executing {i} missing 'tool_name' field"
            assert isinstance(payload["tool_name"], str), f"tool_name must be string in event {i}"
            assert payload["tool_name"].strip(), f"tool_name cannot be empty in event {i}"
            
            assert "agent_name" in payload, f"tool_executing {i} missing 'agent_name' field"
            assert isinstance(payload["agent_name"], str), f"agent_name must be string in event {i}"
            
            assert "timestamp" in payload, f"tool_executing {i} missing 'timestamp' field"
            assert isinstance(payload["timestamp"], (int, float)), f"timestamp must be number in event {i}"
    
    @pytest.mark.e2e
    async def test_final_report_event_implementation(self, websocket_client):
        """Test final_report event with comprehensive results."""
        # Trigger complete analysis that should generate final report
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {
                "content": "Perform complete system analysis and provide final comprehensive report"
            }
        })
        
        # Look for final_report event
        final_report_event = None
        timeout = 30.0  # Longer timeout for complete analysis
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=3.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and message.get("type") == "final_report":
                    final_report_event = message
                    break
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate final_report event was sent
        assert final_report_event is not None, (
            "final_report event not implemented - required for comprehensive results display"
        )
        
        payload = final_report_event["payload"]
        
        # Required fields per SPEC/websocket_communication.xml
        assert "report" in payload, "final_report missing 'report' field"
        assert isinstance(payload["report"], dict), "report must be object"
        assert payload["report"], "report cannot be empty"
        
        assert "total_duration_ms" in payload, "final_report missing 'total_duration_ms' field"
        assert isinstance(payload["total_duration_ms"], (int, float)), "total_duration_ms must be number"
        assert payload["total_duration_ms"] > 0, "total_duration_ms must be positive"
        
        # Optional fields validation
        if "agent_metrics" in payload:
            assert isinstance(payload["agent_metrics"], list), "agent_metrics must be array"
        if "recommendations" in payload:
            assert isinstance(payload["recommendations"], list), "recommendations must be array"
        if "action_plan" in payload:
            assert isinstance(payload["action_plan"], list), "action_plan must be array"
    
    @pytest.mark.e2e
    async def test_missing_events_workflow_completeness(self, websocket_client):
        """Test complete workflow includes all missing events."""
        # Trigger comprehensive workflow
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {
                "content": "Execute full analysis workflow with reasoning, tools, streaming, and final report"
            }
        })
        
        # Track all event types received
        received_events = set()
        missing_events = {"agent_thinking", "partial_result", "tool_executing", "final_report"}
        timeout = 35.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    event_type = message["type"]
                    received_events.add(event_type)
                    missing_events.discard(event_type)
                    
                    # Stop early if we got all missing events
                    if not missing_events:
                        break
                        
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Report implementation status
        implemented_events = received_events & {"agent_thinking", "partial_result", "tool_executing", "final_report"}
        
        # At minimum, we should have agent_started and some progress events
        assert "agent_started" in received_events, "Basic agent_started event missing"
        
        # Report missing critical events for implementation
        if missing_events:
            missing_list = sorted(missing_events)
            pytest.fail(
                f"Critical missing events not implemented: {missing_list}. "
                f"These are required per SPEC/websocket_communication.xml for complete user experience. "
                f"Implemented events: {sorted(implemented_events)}"
            )
    
    @pytest.mark.e2e
    async def test_event_sequence_logical_order(self, websocket_client):
        """Test missing events appear in logical sequence when implemented."""
        # Trigger workflow to test sequence
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {
                "content": "Test logical event sequence with multi-step analysis"
            }
        })
        
        # Collect events with timestamps
        events_sequence = []
        timeout = 25.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=2.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    # Add reception timestamp
                    message["_received_at"] = asyncio.get_event_loop().time()
                    events_sequence.append(message)
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Analyze sequence for logical ordering
        event_types = [event["type"] for event in events_sequence]
        
        # Logical rules for event ordering
        if "agent_started" in event_types and "final_report" in event_types:
            agent_started_idx = event_types.index("agent_started")
            final_report_idx = event_types.rindex("final_report")  # Last occurrence
            assert agent_started_idx < final_report_idx, "agent_started must come before final_report"
        
        if "tool_executing" in event_types and "agent_completed" in event_types:
            # Tools should execute before completion
            tool_indices = [i for i, t in enumerate(event_types) if t == "tool_executing"]
            completed_indices = [i for i, t in enumerate(event_types) if t == "agent_completed"]
            
            if tool_indices and completed_indices:
                last_tool = max(tool_indices)
                first_completion = min(completed_indices)
                assert last_tool < first_completion, "tool_executing should complete before agent_completed"
        
        # Partial results should be ordered
        partial_events = [e for e in events_sequence if e["type"] == "partial_result"]
        if len(partial_events) > 1:
            # Check is_complete ordering
            completion_states = [e["payload"]["is_complete"] for e in partial_events]
            # Should have False values before True
            if True in completion_states:
                last_incomplete = max(i for i, complete in enumerate(completion_states) if not complete) if False in completion_states else -1
                first_complete = min(i for i, complete in enumerate(completion_states) if complete)
                if last_incomplete >= 0:
                    assert last_incomplete < first_complete, "incomplete partial_results should come before complete ones"
    
    # Helper methods (each  <= 8 lines)
    def _extract_event_by_type(self, events: List[Dict], event_type: str) -> Optional[Dict]:
        """Extract first event of specified type from events list."""
        for event in events:
            if event.get("type") == event_type:
                return event
        return None
    
    def _validate_event_payload_not_empty(self, event: Dict, required_fields: List[str]):
        """Validate event payload has non-empty required fields."""
        payload = event.get("payload", {})
        for field in required_fields:
            assert field in payload, f"Missing required field: {field}"
            assert payload[field], f"Field {field} cannot be empty"