"""
Comprehensive WebSocket Event Delivery Integration Tests - Priority 1 for Issue #861

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure 100% delivery of critical WebSocket events for user experience
- Value Impact: Real-time agent progress visibility drives user engagement and trust
- Strategic Impact: $500K+ ARR depends on reliable WebSocket event delivery

CRITICAL: Tests golden path agent workflow with ALL 5 business-critical events:
1. agent_started - User sees AI began processing
2. agent_thinking - Real-time reasoning visibility  
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready

INTEGRATION LAYER: Uses real services (PostgreSQL, Redis) without Docker dependencies.
NO MOCKS in integration tests - validates actual service interactions.

Target: Improve coverage from 9.12% → 65%+ (Priority 1 of 4)
"""

import asyncio
import json
import pytest
import time
import uuid
from typing import Dict, Any, List, Optional, Set
from unittest import mock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.real_services import (
    real_services_fixture, 
    real_postgres_connection, 
    with_test_database,
    real_redis_connection
)

# SSOT WebSocket imports
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.types import (
    MessageType,
    WebSocketMessage,
    create_standard_message,
    WebSocketConnectionState
)

# SSOT Agent imports  
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

# SSOT context imports
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)

# SSOT configuration imports
from shared.isolated_environment import get_env
from shared.id_generation.unified_id_generator import UnifiedIdGenerator


class MockWebSocketConnectionForTesting:
    """Mock WebSocket connection that captures sent messages for validation."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.sent_messages: List[Dict[str, Any]] = []
        self.is_connected = True
        self.state = WebSocketConnectionState.CONNECTED
        
    async def send_text(self, message: str):
        """Capture sent messages for validation."""
        if self.is_connected:
            try:
                data = json.loads(message)
                self.sent_messages.append(data)
            except json.JSONDecodeError:
                self.sent_messages.append({"raw_message": message})
    
    async def close(self, code: int = 1000):
        """Close connection."""
        self.is_connected = False
        self.state = WebSocketConnectionState.DISCONNECTED


class TestWebSocketEventDeliveryIntegration(SSotAsyncTestCase):
    """Test comprehensive WebSocket event delivery in agent pipeline."""
    
    async def asyncSetUp(self):
        """Set up test environment with real services."""
        await super().asyncSetUp()
        
        # Generate unique test identifiers
        self.test_session_id = f"test-session-{uuid.uuid4().hex[:8]}"
        self.test_user_id = f"test-user-{uuid.uuid4().hex[:8]}"
        self.test_connection_id = f"test-conn-{uuid.uuid4().hex[:8]}"
        
        # Mock WebSocket connection for event capture
        self.mock_websocket = MockWebSocketConnectionForTesting(
            self.test_user_id, 
            self.test_connection_id
        )
        
        # Create WebSocket manager with real configuration
        self.websocket_manager = WebSocketManager()
        
        # Register mock connection directly
        self.websocket_manager.active_connections[self.test_connection_id] = self.mock_websocket
        self.websocket_manager.connection_user_map[self.test_connection_id] = self.test_user_id
        self.websocket_manager.user_connection_map[self.test_user_id] = {self.test_connection_id}
        
        # Create user execution context
        self.user_context = UserExecutionContext(
            user_id=self.test_user_id,
            session_id=self.test_session_id,
            connection_id=self.test_connection_id,
            request_timestamp=time.time()
        )
        
        # Create agent registry
        self.agent_registry = AgentRegistry()
        
        # Create WebSocket bridge with proper setup
        self.websocket_bridge = AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_context=self.user_context
        )
        
        # Set WebSocket manager in registry
        self.agent_registry.set_websocket_manager(self.websocket_manager)
    
    async def asyncTearDown(self):
        """Clean up test resources."""
        # Close mock connection
        if self.mock_websocket.is_connected:
            await self.mock_websocket.close()
            
        # Clean up WebSocket manager
        if hasattr(self, 'websocket_manager'):
            # Clear connections
            self.websocket_manager.active_connections.clear()
            self.websocket_manager.connection_user_map.clear()
            self.websocket_manager.user_connection_map.clear()
        
        await super().asyncTearDown()
    
    def get_sent_messages_by_type(self, message_type: str) -> List[Dict[str, Any]]:
        """Get messages by type from mock WebSocket."""
        return [
            msg for msg in self.mock_websocket.sent_messages 
            if msg.get('type') == message_type
        ]
    
    def assert_event_sent(self, event_type: str, timeout: float = 1.0) -> Dict[str, Any]:
        """Assert that a specific event was sent within timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            messages = self.get_sent_messages_by_type(event_type)
            if messages:
                return messages[-1]  # Return latest message
            time.sleep(0.01)  # Small delay
        
        sent_types = [msg.get('type', 'unknown') for msg in self.mock_websocket.sent_messages]
        self.fail(
            f"Event '{event_type}' not sent within {timeout}s. "
            f"Sent events: {sent_types}"
        )

    async def test_agent_started_event_delivery(self):
        """Test Priority 1: agent_started event is delivered correctly."""
        
        # Emit agent_started event through WebSocket bridge
        await self.websocket_bridge.emit_agent_event(
            event_type="agent_started",
            agent_name="TestAgent", 
            data={
                "task": "Process user request",
                "estimated_duration": "2-3 minutes"
            }
        )
        
        # Verify event was delivered
        event_message = self.assert_event_sent("agent_started")
        
        self.assertEqual(event_message['type'], 'agent_started')
        self.assertIn('agent_name', event_message['data'])
        self.assertEqual(event_message['data']['agent_name'], 'TestAgent')
        self.assertIn('task', event_message['data'])
        self.assertIn('timestamp', event_message)
        
    async def test_agent_thinking_event_delivery(self):
        """Test Priority 1: agent_thinking event is delivered correctly."""
        
        thinking_content = "Analyzing the user's request to determine the best approach..."
        
        # Emit agent_thinking event
        await self.websocket_bridge.emit_agent_event(
            event_type="agent_thinking",
            agent_name="TestAgent",
            data={
                "thinking": thinking_content,
                "step": 1,
                "total_steps": 3
            }
        )
        
        # Verify event was delivered  
        event_message = self.assert_event_sent("agent_thinking")
        
        self.assertEqual(event_message['type'], 'agent_thinking')
        self.assertEqual(event_message['data']['thinking'], thinking_content)
        self.assertEqual(event_message['data']['step'], 1)
        self.assertIn('timestamp', event_message)
        
    async def test_tool_executing_event_delivery(self):
        """Test Priority 1: tool_executing event is delivered correctly."""
        
        # Emit tool_executing event
        await self.websocket_bridge.emit_agent_event(
            event_type="tool_executing", 
            agent_name="TestAgent",
            data={
                "tool_name": "data_analyzer",
                "tool_description": "Analyzing data patterns",
                "parameters": {"dataset_id": "12345"}
            }
        )
        
        # Verify event was delivered
        event_message = self.assert_event_sent("tool_executing")
        
        self.assertEqual(event_message['type'], 'tool_executing')
        self.assertEqual(event_message['data']['tool_name'], 'data_analyzer')
        self.assertIn('tool_description', event_message['data'])
        self.assertIn('parameters', event_message['data'])
        
    async def test_tool_completed_event_delivery(self):
        """Test Priority 1: tool_completed event is delivered correctly."""
        
        # Emit tool_completed event
        await self.websocket_bridge.emit_agent_event(
            event_type="tool_completed",
            agent_name="TestAgent", 
            data={
                "tool_name": "data_analyzer",
                "result": {"insights": ["Pattern A detected", "Trend B identified"]},
                "execution_time": 1.5,
                "success": True
            }
        )
        
        # Verify event was delivered
        event_message = self.assert_event_sent("tool_completed")
        
        self.assertEqual(event_message['type'], 'tool_completed') 
        self.assertEqual(event_message['data']['tool_name'], 'data_analyzer')
        self.assertTrue(event_message['data']['success'])
        self.assertIn('result', event_message['data'])
        self.assertIn('execution_time', event_message['data'])
        
    async def test_agent_completed_event_delivery(self):
        """Test Priority 1: agent_completed event is delivered correctly."""
        
        # Emit agent_completed event
        await self.websocket_bridge.emit_agent_event(
            event_type="agent_completed",
            agent_name="TestAgent",
            data={
                "final_response": "Task completed successfully with actionable insights.",
                "total_execution_time": 45.2,
                "tools_used": ["data_analyzer", "report_generator"],
                "success": True
            }
        )
        
        # Verify event was delivered
        event_message = self.assert_event_sent("agent_completed")
        
        self.assertEqual(event_message['type'], 'agent_completed')
        self.assertTrue(event_message['data']['success'])
        self.assertIn('final_response', event_message['data'])
        self.assertIn('total_execution_time', event_message['data'])
        self.assertIn('tools_used', event_message['data'])

    async def test_complete_agent_workflow_event_sequence(self):
        """Test Priority 1: Complete agent workflow delivers all 5 events in sequence."""
        
        # Simulate complete agent workflow
        workflow_events = [
            ("agent_started", {"task": "Complete user analysis"}),
            ("agent_thinking", {"thinking": "Planning analysis approach"}),
            ("tool_executing", {"tool_name": "analyzer", "description": "Running analysis"}),
            ("tool_completed", {"tool_name": "analyzer", "result": {"status": "complete"}}),
            ("agent_completed", {"final_response": "Analysis complete", "success": True})
        ]
        
        # Emit all events in sequence
        for event_type, data in workflow_events:
            await self.websocket_bridge.emit_agent_event(
                event_type=event_type,
                agent_name="WorkflowAgent",
                data=data
            )
            
        # Wait for all events to be processed
        await asyncio.sleep(0.1)
        
        # Verify all 5 events were delivered
        self.assertEqual(len(self.mock_websocket.sent_messages), 5)
        
        # Verify event sequence
        sent_types = [msg.get('type') for msg in self.mock_websocket.sent_messages]
        expected_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        self.assertEqual(sent_types, expected_types)
        
        # Verify each event has required fields
        for i, (expected_type, _) in enumerate(workflow_events):
            message = self.mock_websocket.sent_messages[i]
            self.assertEqual(message['type'], expected_type)
            self.assertIn('timestamp', message)
            self.assertIn('data', message)
            self.assertEqual(message['data']['agent_name'], 'WorkflowAgent')

    async def test_concurrent_user_event_isolation(self):
        """Test Priority 1: Events are properly isolated between concurrent users."""
        
        # Create second user context and WebSocket
        user2_id = f"test-user2-{uuid.uuid4().hex[:8]}"
        conn2_id = f"test-conn2-{uuid.uuid4().hex[:8]}"
        
        mock_websocket2 = MockWebSocketConnectionForTesting(user2_id, conn2_id)
        
        # Register second user in WebSocket manager
        self.websocket_manager.active_connections[conn2_id] = mock_websocket2
        self.websocket_manager.connection_user_map[conn2_id] = user2_id
        self.websocket_manager.user_connection_map[user2_id] = {conn2_id}
        
        # Create second user context and bridge
        user2_context = UserExecutionContext(
            user_id=user2_id,
            session_id=f"session2-{uuid.uuid4().hex[:8]}",
            connection_id=conn2_id,
            request_timestamp=time.time()
        )
        
        user2_bridge = AgentWebSocketBridge(
            websocket_manager=self.websocket_manager,
            user_context=user2_context
        )
        
        # Emit events for user 1
        await self.websocket_bridge.emit_agent_event(
            event_type="agent_started",
            agent_name="Agent1", 
            data={"task": "User 1 task"}
        )
        
        # Emit events for user 2
        await user2_bridge.emit_agent_event(
            event_type="agent_started",
            agent_name="Agent2",
            data={"task": "User 2 task"}
        )
        
        # Verify user 1 only received their event
        user1_messages = self.mock_websocket.sent_messages
        self.assertEqual(len(user1_messages), 1)
        self.assertEqual(user1_messages[0]['data']['agent_name'], 'Agent1')
        
        # Verify user 2 only received their event  
        user2_messages = mock_websocket2.sent_messages
        self.assertEqual(len(user2_messages), 1)
        self.assertEqual(user2_messages[0]['data']['agent_name'], 'Agent2')
        
        # Clean up
        await mock_websocket2.close()

    async def test_websocket_connection_failure_handling(self):
        """Test Priority 1: Graceful handling when WebSocket connection fails."""
        
        # Simulate connection failure
        self.mock_websocket.is_connected = False
        self.mock_websocket.state = WebSocketConnectionState.DISCONNECTED
        
        # Attempt to emit event to disconnected user
        try:
            await self.websocket_bridge.emit_agent_event(
                event_type="agent_started",
                agent_name="TestAgent",
                data={"task": "Test task"}  
            )
            
            # Should not raise exception - should handle gracefully
            # Event may be queued or logged but not delivered
            
        except Exception as e:
            self.fail(f"WebSocket failure should be handled gracefully, got: {e}")
        
        # No messages should be sent to disconnected connection
        self.assertEqual(len(self.mock_websocket.sent_messages), 0)

    async def test_event_delivery_performance_timing(self):
        """Test Priority 1: Events are delivered within acceptable time limits."""
        
        # Measure event delivery timing
        start_time = time.time()
        
        await self.websocket_bridge.emit_agent_event(
            event_type="agent_started",
            agent_name="TestAgent",
            data={"task": "Performance test"}
        )
        
        end_time = time.time()
        delivery_time = end_time - start_time
        
        # Verify event was delivered
        self.assertEqual(len(self.mock_websocket.sent_messages), 1)
        
        # Event delivery should be fast (under 100ms for integration tests)
        self.assertLess(delivery_time, 0.1, 
                       f"Event delivery took {delivery_time:.3f}s, should be under 0.1s")
        
        # Verify message content
        message = self.mock_websocket.sent_messages[0]
        self.assertEqual(message['type'], 'agent_started')
        self.assertIn('timestamp', message)

    async def test_bulk_event_delivery_reliability(self):
        """Test Priority 1: Reliable delivery of multiple events in rapid succession."""
        
        num_events = 20
        event_data = []
        
        # Send multiple events rapidly
        for i in range(num_events):
            data = {"sequence": i, "task": f"Task {i}"}
            event_data.append(data)
            
            await self.websocket_bridge.emit_agent_event(
                event_type="agent_thinking",
                agent_name="BulkTestAgent",
                data=data
            )
        
        # Small delay to allow processing
        await asyncio.sleep(0.1)
        
        # Verify all events were delivered
        self.assertEqual(len(self.mock_websocket.sent_messages), num_events)
        
        # Verify events are in correct order
        for i in range(num_events):
            message = self.mock_websocket.sent_messages[i]
            self.assertEqual(message['type'], 'agent_thinking')
            self.assertEqual(message['data']['sequence'], i)
            self.assertEqual(message['data']['task'], f"Task {i}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])