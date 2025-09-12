"""WebSocket Event Structure Validation Tests.

Tests compliance with SPEC/websocket_communication.xml event format requirements.
Business Value: Ensures consistent {type, payload} message structure preventing
frontend/backend communication failures that impact user experience.

BVJ: Enterprise/Mid - Platform Stability - Event structure standardization
prevents costly debugging cycles and ensures reliable real-time features.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict
from shared.isolated_environment import IsolatedEnvironment

import pytest
from pydantic import ValidationError

from tests.clients.factory import TestClientFactory


@pytest.mark.e2e
class TestWebSocketEventStructure:
    """Test suite for WebSocket event structure validation."""
    
    @pytest.fixture
    async def client_factory(self):
        """Get test client factory."""
        factory = TestClientFactory()
        try:
            yield factory
        finally:
            await factory.cleanup()
    
    @pytest.fixture
    async def backend_client(self, client_factory):
        """Get authenticated backend client."""
        return await client_factory.create_authenticated_backend_client()
    
    @pytest.fixture
    async def websocket_client(self, client_factory):
        """Get authenticated WebSocket client."""
        return await client_factory.create_authenticated_websocket_client()
    
    @pytest.mark.e2e
    async def test_message_structure_compliance(self, websocket_client):
        """Test all WebSocket messages use {type, payload} structure."""
        # Trigger agent execution to generate WebSocket events
        await websocket_client.send({
            "type": "user_message", 
            "payload": {"content": "Test message for structure validation"}
        })
        
        # Collect messages for 5 seconds
        messages = []
        timeout = 5.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await websocket_client.receive(timeout=0.5)
                messages.append(message)
            except asyncio.TimeoutError:
                break
        
        # Validate all messages follow {type, payload} structure
        assert len(messages) > 0, "No WebSocket messages received"
        
        for i, message in enumerate(messages):
            # Each message must be valid JSON
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError:
                    pytest.fail(f"Message {i} is not valid JSON: {message}")
            
            # Must have 'type' field
            assert "type" in message, f"Message {i} missing 'type' field: {message}"
            assert isinstance(message["type"], str), f"Message {i} 'type' must be string: {message}"
            assert message["type"], f"Message {i} 'type' cannot be empty: {message}"
            
            # Must have 'payload' field  
            assert "payload" in message, f"Message {i} missing 'payload' field: {message}"
            assert isinstance(message["payload"], dict), f"Message {i} 'payload' must be dict: {message}"
            
            # Should not have legacy fields
            forbidden_fields = ["event", "data"]
            for field in forbidden_fields:
                assert field not in message, f"Message {i} contains forbidden field '{field}': {message}"
    
    @pytest.mark.e2e
    async def test_agent_started_event_structure(self, websocket_client):
        """Test agent_started event has required payload fields."""
        # Trigger agent execution
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Start analysis agent for testing"}
        })
        
        # Look for agent_started event
        agent_started_event = None
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if message.get("type") == "agent_started":
                    agent_started_event = message
                    break
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        assert agent_started_event is not None, "agent_started event not received"
        
        payload = agent_started_event["payload"]
        
        # Required fields per SPEC/websocket_communication.xml
        assert "run_id" in payload, "agent_started missing run_id"
        assert isinstance(payload["run_id"], str), "run_id must be string"
        assert payload["run_id"], "run_id cannot be empty"
        
        assert "agent_name" in payload, "agent_started missing agent_name"
        assert isinstance(payload["agent_name"], str), "agent_name must be string"
        assert payload["agent_name"], "agent_name cannot be empty"
        
        assert "timestamp" in payload, "agent_started missing timestamp"
        assert isinstance(payload["timestamp"], (int, float)), "timestamp must be number"
        assert payload["timestamp"] > 0, "timestamp must be positive"
    
    @pytest.mark.e2e
    async def test_tool_executing_event_structure(self, websocket_client):
        """Test tool_executing event structure when tools are invoked."""
        # Trigger message that will use tools
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Analyze system performance with tools"}
        })
        
        # Look for tool_executing event
        tool_event = None
        timeout = 15.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if message.get("type") == "tool_executing":
                    tool_event = message
                    break
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        if tool_event is not None:  # Only validate if we received the event
            payload = tool_event["payload"]
            
            # Required fields per spec
            assert "tool_name" in payload, "tool_executing missing tool_name"
            assert isinstance(payload["tool_name"], str), "tool_name must be string"
            
            assert "agent_name" in payload, "tool_executing missing agent_name"
            assert isinstance(payload["agent_name"], str), "agent_name must be string"
            
            assert "timestamp" in payload, "tool_executing missing timestamp"
            assert isinstance(payload["timestamp"], (int, float)), "timestamp must be number"
    
    @pytest.mark.e2e
    async def test_forbidden_legacy_structures(self, websocket_client):
        """Test that no messages use forbidden legacy {event, data} structure."""
        # Trigger various events
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Generate events for legacy structure check"}
        })
        
        # Collect messages
        messages = []
        timeout = 8.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=0.5
                )
                messages.append(message)
            except asyncio.TimeoutError:
                break
        
        # Check no legacy structures exist
        for i, message in enumerate(messages):
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError:
                    continue
            
            # Must not use legacy {event, data} pattern
            if isinstance(message, dict):
                assert not ("event" in message and "data" in message), \
                    f"Message {i} uses forbidden legacy {{event, data}} structure: {message}"
    
    @pytest.mark.e2e
    async def test_event_type_enum_compliance(self, websocket_client):
        """Test event types match expected enumerated values."""
        # Expected event types per SPEC/websocket_communication.xml
        expected_events = {
            "agent_started", "agent_completed", "sub_agent_update",
            "agent_thinking", "partial_result", "tool_executing", "final_report"
        }
        
        # Trigger comprehensive agent execution
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Run comprehensive analysis to test all event types"}
        })
        
        # Collect unique event types
        observed_events = set()
        timeout = 12.0
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    observed_events.add(message["type"])
                    
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Validate observed events are from expected set
        unexpected_events = observed_events - expected_events
        assert not unexpected_events, f"Unexpected event types: {unexpected_events}"
        
        # We should observe at least agent_started
        assert "agent_started" in observed_events, "Expected agent_started event not observed"
    
    @pytest.mark.e2e
    async def test_payload_schema_validation(self, websocket_client):
        """Test payload schemas are valid for each event type."""
        # Event schemas per SPEC/websocket_communication.xml
        schema_validators = {
            "agent_started": self._validate_agent_started_payload,
            "agent_completed": self._validate_agent_completed_payload,
            "tool_executing": self._validate_tool_executing_payload,
            "agent_thinking": self._validate_agent_thinking_payload,
            "partial_result": self._validate_partial_result_payload,
        }
        
        # Trigger events
        await websocket_client.send_message({
            "type": "user_message",
            "payload": {"content": "Test schema validation with comprehensive execution"}
        })
        
        # Validate schemas as events arrive
        timeout = 10.0
        start_time = asyncio.get_event_loop().time()
        validated_events = set()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            try:
                message = await asyncio.wait_for(
                    websocket_client.receive_message(),
                    timeout=1.0
                )
                
                if isinstance(message, str):
                    message = json.loads(message)
                
                if isinstance(message, dict) and "type" in message:
                    event_type = message["type"]
                    if event_type in schema_validators:
                        validator = schema_validators[event_type]
                        try:
                            validator(message["payload"])
                            validated_events.add(event_type)
                        except AssertionError as e:
                            pytest.fail(f"Schema validation failed for {event_type}: {e}")
                        except Exception as e:
                            pytest.fail(f"Unexpected error validating {event_type}: {e}")
                            
            except (asyncio.TimeoutError, json.JSONDecodeError):
                continue
        
        # Should validate at least agent_started
        assert len(validated_events) > 0, "No events were schema validated"
    
    # Schema validation helpers (each  <= 8 lines)
    def _validate_agent_started_payload(self, payload: Dict[str, Any]):
        """Validate agent_started payload schema."""
        assert "run_id" in payload and isinstance(payload["run_id"], str)
        assert "agent_name" in payload and isinstance(payload["agent_name"], str)
        assert "timestamp" in payload and isinstance(payload["timestamp"], (int, float))
    
    def _validate_agent_completed_payload(self, payload: Dict[str, Any]):
        """Validate agent_completed payload schema."""
        assert "agent_name" in payload and isinstance(payload["agent_name"], str)
        assert "duration_ms" in payload and isinstance(payload["duration_ms"], (int, float))
        assert "result" in payload and isinstance(payload["result"], dict)
    
    def _validate_tool_executing_payload(self, payload: Dict[str, Any]):
        """Validate tool_executing payload schema."""
        assert "tool_name" in payload and isinstance(payload["tool_name"], str)
        assert "agent_name" in payload and isinstance(payload["agent_name"], str)
        assert "timestamp" in payload and isinstance(payload["timestamp"], (int, float))
    
    def _validate_agent_thinking_payload(self, payload: Dict[str, Any]):
        """Validate agent_thinking payload schema."""
        assert "thought" in payload and isinstance(payload["thought"], str)
        assert "agent_name" in payload and isinstance(payload["agent_name"], str)
    
    def _validate_partial_result_payload(self, payload: Dict[str, Any]):
        """Validate partial_result payload schema."""
        assert "content" in payload and isinstance(payload["content"], str)
        assert "agent_name" in payload and isinstance(payload["agent_name"], str)
        assert "is_complete" in payload and isinstance(payload["is_complete"], bool)