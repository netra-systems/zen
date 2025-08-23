"""
WebsocketTestHelpers

Helper module for websocket test helpers.
"""

import asyncio
from typing import Dict, Any, List, Optional

class WebsocketTestHelpersHelper:
    """Helper class for websocket test helpers."""
    
    def __init__(self):
        self.initialized = True
    
    async def setup(self) -> bool:
        """Setup helper resources."""
        return True
    
    async def teardown(self) -> bool:
        """Teardown helper resources."""
        return True
    
    async def execute_operation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Execute a generic operation."""
        return {
            "operation": operation,
            "success": True,
            "result": kwargs
        }

# Compatibility aliases
WebsocketTestsHelper = WebsocketTestHelpersHelper

class WebSocketTestManager:
    """Manager for WebSocket test operations."""
    
    def __init__(self):
        self.helper = WebsocketTestHelpersHelper()
        self.connections = {}
        self.event_log = []
    
    async def setup_test_environment(self) -> bool:
        """Setup WebSocket test environment."""
        return await self.helper.setup()
    
    async def teardown_test_environment(self) -> bool:
        """Teardown WebSocket test environment."""
        return await self.helper.teardown()
    
    async def validate_event_completeness(self, expected_events: List[str]) -> bool:
        """Validate that all expected events were received."""
        received_events = [event.get("type") for event in self.event_log]
        return all(event in received_events for event in expected_events)
    
    async def record_websocket_event(self, event_type: str, data: Dict[str, Any]):
        """Record a WebSocket event for validation."""
        self.event_log.append({
            "type": event_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        })
    
    async def clear_event_log(self):
        """Clear the event log."""
        self.event_log.clear()
    
    def get_recorded_events(self) -> List[Dict[str, Any]]:
        """Get all recorded events."""
        return self.event_log.copy()

class WebSocketEventValidator:
    """Validator for WebSocket events."""
    
    def __init__(self, manager: WebSocketTestManager):
        self.manager = manager
    
    async def validate_event_sequence(self, expected_sequence: List[str]) -> bool:
        """Validate that events occurred in expected sequence."""
        events = self.manager.get_recorded_events()
        event_types = [event["type"] for event in events]
        
        if len(event_types) != len(expected_sequence):
            return False
            
        return event_types == expected_sequence
    
    async def validate_event_data(self, event_type: str, expected_data: Dict[str, Any]) -> bool:
        """Validate that an event contains expected data."""
        events = [e for e in self.manager.get_recorded_events() if e["type"] == event_type]
        
        if not events:
            return False
            
        event_data = events[-1]["data"]  # Get most recent event of this type
        return all(event_data.get(key) == value for key, value in expected_data.items())


def create_agent_request(agent_type: str, thread_id: str, content: str, **kwargs) -> Dict[str, Any]:
    """Create an agent request for WebSocket testing.
    
    Args:
        agent_type: Type of agent to request
        thread_id: Thread ID for the request
        content: Content/prompt for the agent
        **kwargs: Additional request parameters
        
    Returns:
        Dictionary containing the agent request
    """
    import time
    import uuid
    
    request = {
        "type": "agent_request",
        "agent_type": agent_type,
        "thread_id": thread_id,
        "request_id": kwargs.get("request_id", str(uuid.uuid4())),
        "content": content,
        "timestamp": time.time(),
        "user_id": kwargs.get("user_id", f"test_user_{thread_id}"),
        "parameters": kwargs.get("parameters", {}),
        "metadata": kwargs.get("metadata", {
            "test_request": True,
            "created_by": "websocket_test_helpers"
        })
    }
    
    return request

def create_test_websocket_message(message_type: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    """Create a test WebSocket message with proper structure.
    
    Args:
        message_type: Type of the message
        data: Message data
        **kwargs: Additional message parameters
        
    Returns:
        Properly structured WebSocket message
    """
    
    return {
        "type": message_type,
        "message_id": kwargs.get("message_id", str(uuid.uuid4())),
        "timestamp": time.time(),
        "data": data,
        "metadata": kwargs.get("metadata", {
            "test_message": True,
            "created_by": "websocket_test_helpers"
        })
    }

def extract_events_by_type(events: List[Dict[str, Any]], event_type: str) -> List[Dict[str, Any]]:
    """Extract events of a specific type from a list of events.
    
    Args:
        events: List of events to filter
        event_type: Type of events to extract
        
    Returns:
        List of events matching the specified type
    """
    return [event for event in events if event.get("type") == event_type]

def group_events_by_type(events: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group events by their type.
    
    Args:
        events: List of events to group
        
    Returns:
        Dictionary with event types as keys and lists of events as values
    """
    grouped = {}
    for event in events:
        event_type = event.get("type", "unknown")
        if event_type not in grouped:
            grouped[event_type] = []
        grouped[event_type].append(event)
    
    return grouped

def validate_event_sequence(events: List[Dict[str, Any]], expected_types: List[str]) -> bool:
    """Validate that events occur in expected sequence.
    
    Args:
        events: List of events to validate
        expected_types: Expected sequence of event types
        
    Returns:
        True if events match expected sequence, False otherwise
    """
    if len(events) != len(expected_types):
        return False
        
    for i, event in enumerate(events):
        if event.get("type") != expected_types[i]:
            return False
            
    return True

def validate_event_payload(event: Dict[str, Any], expected_fields: List[str]) -> bool:
    """Validate that an event contains expected payload fields.
    
    Args:
        event: Event to validate
        expected_fields: List of expected field names
        
    Returns:
        True if all expected fields are present, False otherwise
    """
    if not event or not isinstance(event, dict):
        return False
        
    return all(field in event for field in expected_fields)
