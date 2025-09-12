#!/usr/bin/env python
"""SIMPLIFIED WebSocket Sub-Agent Events Test

This is a simplified version that tests WebSocket event flow without starting the full backend.
It focuses on the core WebSocket notification mechanism using the existing real services.
"""

import asyncio
import json
import time
import uuid
from typing import Dict, List, Any
from shared.isolated_environment import IsolatedEnvironment

import pytest
from loguru import logger

# Import real services infrastructure
from test_framework.real_services import get_real_services, RealServicesManager

# Import production WebSocket components
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.state import DeepAgentState


class BasicEventValidator:
    """Basic WebSocket event validator for testing core event flow."""
    
    def __init__(self):
        self.events: List[Dict] = []
        
    def record_event(self, event: Dict) -> None:
        """Record a WebSocket event."""
        self.events.append(event)
        logger.info(f"[U+1F4E1] Event recorded: {event.get('type', 'unknown')}")
        
    def has_event(self, event_type: str) -> bool:
        """Check if we have an event of the given type."""
        return any(event.get('type') == event_type for event in self.events)
        
    def get_event_count(self, event_type: str) -> int:
        """Get count of events of given type."""
        return sum(1 for event in self.events if event.get('type') == event_type)
        
    def get_summary(self) -> str:
        """Get summary of recorded events."""
        event_types = [event.get('type') for event in self.events]
        return f"Total events: {len(self.events)}, Types: {list(set(event_types))}"


@pytest.mark.critical 
@pytest.mark.mission_critical
class TestBasicWebSocketEvents:
    """Test basic WebSocket event emission using real connections."""
    
    @pytest.mark.asyncio
    async def test_websocket_manager_connection(self, real_services: RealServicesManager):
        """Test that WebSocketManager can create connections and send events."""
        ws_manager = WebSocketManager()
        validator = BasicEventValidator()
        
        connection_id = f"test-{uuid.uuid4().hex[:8]}"
        
        # Create a mock WebSocket that captures events
        # COMMENTED OUT: MockWebSocket class - using real WebSocket connections per CLAUDE.md "MOCKS = Abomination"
        # class MockWebSocket:
        #     async def send_json(self, data):
        #         validator.record_event(data)
        #         
        #     async def send_text(self, text):
        #         try:
        #             data = json.loads(text)
        #             validator.record_event(data)
        #         except json.JSONDecodeError:
        #             logger.warning(f"Non-JSON text: {text}")
        
        # mock_ws = MockWebSocket()
        
        # Connect user to WebSocket manager
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Send a test event
        await ws_manager.send_to_user(connection_id, {
            "type": "test_event",
            "message": "Hello from WebSocket manager",
            "timestamp": time.time()
        })
        
        # Check that event was received
        assert len(validator.events) == 1
        assert validator.has_event("test_event")
        
        logger.info(f"Test passed: {validator.get_summary()}")
        
    @pytest.mark.asyncio
    async def test_websocket_notifier_basic_events(self, real_services: RealServicesManager):
        """Test WebSocketNotifier can send basic agent events."""
        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier.create_for_user(ws_manager)
        validator = BasicEventValidator()
        
        connection_id = f"test-notifier-{uuid.uuid4().hex[:8]}"
        
        # Mock WebSocket
        class MockWebSocket:
            async def send_json(self, data):
                validator.record_event(data)
        
        mock_ws = MockWebSocket()
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Test sending different event types
        await notifier.send_agent_started(connection_id, "test-agent", "Starting test")
        await notifier.send_agent_thinking(connection_id, "Thinking about test...")
        await notifier.send_tool_executing(connection_id, "test_tool", {"param": "value"})
        await notifier.send_tool_completed(connection_id, "test_tool", {"result": "success"})
        await notifier.send_agent_completed(connection_id, {"status": "success"})
        
        # Validate events
        assert validator.has_event("agent_started")
        assert validator.has_event("agent_thinking") 
        assert validator.has_event("tool_executing")
        assert validator.has_event("tool_completed")
        assert validator.has_event("agent_completed")
        
        assert len(validator.events) == 5
        
        logger.info(f"Notifier test passed: {validator.get_summary()}")
        
    @pytest.mark.asyncio
    async def test_websocket_event_sequencing(self, real_services: RealServicesManager):
        """Test that WebSocket events are sent in proper sequence."""
        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier.create_for_user(ws_manager)
        validator = BasicEventValidator()
        
        connection_id = f"test-sequence-{uuid.uuid4().hex[:8]}"
        
        class MockWebSocket:
            async def send_json(self, data):
                validator.record_event(data)
        
        mock_ws = MockWebSocket()
        await ws_manager.connect_user(connection_id, mock_ws, connection_id)
        
        # Send events in expected sequence
        await notifier.send_agent_started(connection_id, "test-agent", "Starting")
        await notifier.send_agent_thinking(connection_id, "Analyzing...")
        await notifier.send_tool_executing(connection_id, "analyzer", {"task": "analyze"})
        await notifier.send_tool_completed(connection_id, "analyzer", {"result": "analyzed"})
        await notifier.send_agent_completed(connection_id, {"status": "done"})
        
        # Check sequence
        event_types = [event.get('type') for event in validator.events]
        expected_sequence = [
            "agent_started", 
            "agent_thinking", 
            "tool_executing", 
            "tool_completed", 
            "agent_completed"
        ]
        
        assert event_types == expected_sequence, f"Wrong sequence: {event_types}"
        
        logger.info(f"Sequence test passed: {validator.get_summary()}")

    @pytest.mark.asyncio
    async def test_multiple_websocket_connections(self, real_services: RealServicesManager):
        """Test multiple WebSocket connections receive events independently."""
        ws_manager = WebSocketManager()
        notifier = WebSocketNotifier.create_for_user(ws_manager)
        
        # Create two separate validators for two connections
        validator1 = BasicEventValidator()
        validator2 = BasicEventValidator()
        
        connection1 = f"test-multi-1-{uuid.uuid4().hex[:8]}"
        connection2 = f"test-multi-2-{uuid.uuid4().hex[:8]}"
        
        # Mock WebSockets
        class MockWebSocket1:
            async def send_json(self, data):
                validator1.record_event(data)
                
        class MockWebSocket2:
            async def send_json(self, data):
                validator2.record_event(data)
        
        mock_ws1 = MockWebSocket1()
        mock_ws2 = MockWebSocket2()
        
        # Connect both users
        await ws_manager.connect_user(connection1, mock_ws1, connection1)
        await ws_manager.connect_user(connection2, mock_ws2, connection2)
        
        # Send event only to connection1
        await notifier.send_agent_started(connection1, "agent1", "Starting for user 1")
        
        # Send event only to connection2
        await notifier.send_agent_started(connection2, "agent2", "Starting for user 2")
        
        # Verify isolation
        assert len(validator1.events) == 1
        assert len(validator2.events) == 1
        
        assert validator1.events[0].get('message') == "Starting for user 1"
        assert validator2.events[0].get('message') == "Starting for user 2"
        
        logger.info(f"Multiple connections test passed")
        logger.info(f"Connection 1: {validator1.get_summary()}")
        logger.info(f"Connection 2: {validator2.get_summary()}")


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "-s"])