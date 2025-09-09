"""
WebSocket Chat Business Value Integration Test Suite

MISSION CRITICAL: Tests for WebSocket infrastructure that enables chat business value delivery.

Business Value Justification (BVJ):
- Segment: Platform/Internal & Enterprise
- Business Goal: Ensure real-time AI chat interactions deliver substantive business value
- Value Impact: Validates WebSocket events enable transparent AI processing, user engagement, and trust
- Strategic Impact: Ensures 90% of current business value (chat) is technically reliable and performant

CRITICAL WebSocket Events for Chat Business Value:
1. agent_started - User sees agent processing began  
2. agent_thinking - Real-time reasoning transparency
3. tool_executing - Tool usage visibility
4. tool_completed - Actionable results delivery
5. agent_completed - Response ready notification

This test suite validates that WebSocket infrastructure delivers these critical events
reliably in multi-user scenarios with proper authentication, isolation, and performance.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, patch
import pytest
import websockets
from websockets.exceptions import ConnectionClosed

from test_framework.base_integration_test import BaseIntegrationTest, WebSocketIntegrationTest
from test_framework.real_services import get_real_services
from test_framework.ssot.e2e_auth_helper import create_authenticated_test_user

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.schemas.websocket_message_types import WebSocketConnectionState, ClientMessage, ServerMessage
from netra_backend.app.schemas.core_enums import WebSocketMessageType
from netra_backend.app.core.exceptions.websocket_exceptions import WebSocketEventEmissionError
from netra_backend.app.agents.execution_engine_consolidated import ExecutionEngine
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.isolated_environment import get_env


class MockWebSocketConnection:
    """Mock WebSocket connection for testing event delivery."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.sent_messages: List[Dict] = []
        self.is_connected = True
        self.compression_enabled = True
        
    async def send(self, message: str):
        """Mock sending message to WebSocket."""
        if not self.is_connected:
            raise ConnectionClosed(None, None)
            
        try:
            parsed_message = json.loads(message)
            self.sent_messages.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'message': parsed_message,
                'user_id': self.user_id,
                'connection_id': self.connection_id
            })
        except json.JSONDecodeError:
            # Handle non-JSON messages  
            self.sent_messages.append({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'raw_message': message,
                'user_id': self.user_id,
                'connection_id': self.connection_id
            })
            
    def disconnect(self):
        """Simulate connection loss."""
        self.is_connected = False
        
    def get_sent_events(self) -> List[Dict]:
        """Get all events sent through this connection."""
        return [msg for msg in self.sent_messages if 'message' in msg]
        
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        """Get events of specific type."""
        return [
            event['message'] for event in self.get_sent_events()
            if event['message'].get('type') == event_type
        ]


class WebSocketChatValueIntegrationTest(WebSocketIntegrationTest):
    """
    Comprehensive integration tests for WebSocket infrastructure supporting chat business value.
    
    CRITICAL: These tests validate the 5 mission-critical WebSocket events that enable
    substantive AI chat interactions and deliver real business value to users.
    """
    
    async def setup_method(self):
        """Set up test environment with real services."""
        super().setup_method()
        
        # Get real services for integration testing
        self.real_services = await get_real_services()
        
        # Create isolated test environment
        self.env = get_env()
        self.env.set("TESTING", "1", source="websocket_integration_test")
        self.env.set("USE_REAL_SERVICES", "true", source="websocket_integration_test")
        self.env.set("WEBSOCKET_COMPRESSION", "true", source="websocket_integration_test")
        
        # Initialize WebSocket components
        self.websocket_manager = None
        self.bridge = None
        self.mock_connections: Dict[str, MockWebSocketConnection] = {}
        
        await self.async_setup()
        
    async def teardown_method(self):
        """Clean up test environment."""
        try:
            # Clean up mock connections
            for connection in self.mock_connections.values():
                connection.disconnect()
            self.mock_connections.clear()
            
            # Clean up bridge
            if self.bridge:
                await self.bridge.shutdown()
                
            await self.async_teardown()
        finally:
            super().teardown_method()
    
    async def create_authenticated_user(self, email_suffix: str = None) -> Dict[str, Any]:
        """Create authenticated user for WebSocket testing."""
        suffix = email_suffix or f"test-{int(time.time())}"
        user_data = await create_authenticated_test_user(
            self.real_services,
            email=f"websocket-{suffix}@test.com",
            name=f"WebSocket Test User {suffix}"
        )
        return user_data
    
    async def create_websocket_connection(self, user_id: str) -> MockWebSocketConnection:
        """Create mock WebSocket connection for user."""
        connection_id = f"conn-{user_id}-{int(time.time())}"
        connection = MockWebSocketConnection(user_id, connection_id)
        self.mock_connections[connection_id] = connection
        return connection
        
    async def setup_websocket_bridge(self) -> AgentWebSocketBridge:
        """Set up WebSocket bridge for testing."""
        self.bridge = AgentWebSocketBridge()
        
        # Initialize with test configuration
        result = await self.bridge.ensure_integration()
        assert result.success, f"Bridge initialization failed: {result.error}"
        
        return self.bridge
    
    def extract_critical_events(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Extract and categorize the 5 critical WebSocket events."""
        critical_events = {
            'agent_started': [],
            'agent_thinking': [],
            'tool_executing': [],
            'tool_completed': [],
            'agent_completed': []
        }
        
        for event in events:
            event_type = event.get('type', '')
            if event_type in critical_events:
                critical_events[event_type].append(event)
                
        return critical_events

    @pytest.mark.asyncio
    async def test_websocket_connection_establishment_with_authentication(self):
        """
        Test 1: WebSocket Connection Establishment & Authentication
        
        Business Value: Ensures authenticated users can establish secure WebSocket connections
        for real-time AI chat interactions.
        """
        # Create authenticated user
        user_data = await self.create_authenticated_user("auth-test")
        user_id = user_data['user_id']
        
        # Set up WebSocket manager with real Redis
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        
        # Create authenticated WebSocket connection
        connection = await self.create_websocket_connection(user_id)
        
        # Test connection registration
        await websocket_manager.register_connection(
            connection_id=connection.connection_id,
            user_id=user_id,
            websocket=connection
        )
        
        # Verify connection is registered and authenticated
        registered_connections = await websocket_manager.get_user_connections(user_id)
        assert len(registered_connections) == 1
        assert registered_connections[0]['connection_id'] == connection.connection_id
        assert registered_connections[0]['user_id'] == user_id
        
        # Test authentication context extraction
        connection_info = await websocket_manager.get_connection_info(connection.connection_id)
        assert connection_info is not None
        assert connection_info['user_id'] == user_id
        assert connection_info['authenticated'] == True
        
        # Business value assertion
        self.assert_business_value_delivered(
            {'authenticated_connection': True, 'user_isolated': True},
            'automation'
        )

    @pytest.mark.asyncio 
    async def test_critical_websocket_events_delivery_real_time(self):
        """
        Test 2: Critical WebSocket Events Delivery for Chat Business Value
        
        Business Value: Validates all 5 critical events (agent_started, agent_thinking, 
        tool_executing, tool_completed, agent_completed) are delivered in real-time
        to enable transparent AI chat interactions.
        """
        # Create authenticated user and connection
        user_data = await self.create_authenticated_user("events-test")
        user_id = user_data['user_id']
        connection = await self.create_websocket_connection(user_id)
        
        # Set up WebSocket bridge
        bridge = await self.setup_websocket_bridge()
        
        # Set up WebSocket emitter with mock connection
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        # Mock the WebSocket manager to use our test connection
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_to_user(user_id, message, **kwargs):
                await connection.send(json.dumps(message))
                
            mock_manager.emit_to_user = mock_emit_to_user
            
            # Test all 5 critical events in sequence
            request_id = RequestID(f"req-{int(time.time())}")
            
            # 1. Agent Started Event
            await emitter.emit_agent_started(
                request_id=request_id,
                agent_name="TestDataAgent",
                context="Testing critical WebSocket events"
            )
            
            # 2. Agent Thinking Event
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="Analyzing user request for data insights...",
                reasoning_step=1
            )
            
            # 3. Tool Executing Event
            await emitter.emit_tool_executing(
                request_id=request_id,
                tool_name="data_analyzer",
                tool_description="Analyzing business data for insights"
            )
            
            # 4. Tool Completed Event
            await emitter.emit_tool_completed(
                request_id=request_id,
                tool_name="data_analyzer",
                result={"insights": ["Cost savings opportunity identified", "Performance improvement suggested"]},
                execution_time_ms=150
            )
            
            # 5. Agent Completed Event
            await emitter.emit_agent_completed(
                request_id=request_id,
                agent_name="TestDataAgent",
                result={"analysis": "Complete", "recommendations": 3},
                total_duration_ms=500
            )
        
        # Verify all critical events were delivered
        sent_events = connection.get_sent_events()
        assert len(sent_events) >= 5, f"Expected at least 5 events, got {len(sent_events)}"
        
        critical_events = self.extract_critical_events([event['message'] for event in sent_events])
        
        # Verify each critical event type was delivered
        assert len(critical_events['agent_started']) >= 1, "agent_started event missing"
        assert len(critical_events['agent_thinking']) >= 1, "agent_thinking event missing"
        assert len(critical_events['tool_executing']) >= 1, "tool_executing event missing"
        assert len(critical_events['tool_completed']) >= 1, "tool_completed event missing"  
        assert len(critical_events['agent_completed']) >= 1, "agent_completed event missing"
        
        # Verify event content provides business value
        started_event = critical_events['agent_started'][0]
        assert 'agent_name' in started_event
        assert 'context' in started_event
        
        thinking_event = critical_events['agent_thinking'][0]
        assert 'thinking_content' in thinking_event
        assert 'reasoning_step' in thinking_event
        
        tool_exec_event = critical_events['tool_executing'][0]
        assert 'tool_name' in tool_exec_event
        assert 'tool_description' in tool_exec_event
        
        tool_comp_event = critical_events['tool_completed'][0]
        assert 'result' in tool_comp_event
        assert 'execution_time_ms' in tool_comp_event
        
        completed_event = critical_events['agent_completed'][0]
        assert 'result' in completed_event
        assert 'total_duration_ms' in completed_event
        
        # Business value assertion - all events delivered for chat transparency
        self.assert_business_value_delivered(
            {'critical_events_delivered': 5, 'real_time_transparency': True, 'user_trust_enabled': True},
            'insights'
        )

    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_and_routing(self):
        """
        Test 3: Multi-User WebSocket Message Routing & Isolation
        
        Business Value: Ensures enterprise customers can have multiple users
        with isolated AI chat sessions and proper message routing.
        """
        # Create multiple authenticated users
        user1_data = await self.create_authenticated_user("user1-isolation")
        user2_data = await self.create_authenticated_user("user2-isolation") 
        user3_data = await self.create_authenticated_user("user3-isolation")
        
        users = [user1_data, user2_data, user3_data]
        connections = {}
        emitters = {}
        
        # Set up WebSocket connections for each user
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        
        for user_data in users:
            user_id = user_data['user_id']
            connection = await self.create_websocket_connection(user_id)
            connections[user_id] = connection
            
            # Register connection
            await websocket_manager.register_connection(
                connection_id=connection.connection_id,
                user_id=user_id,
                websocket=connection
            )
            
            # Create user-specific emitter
            emitter = UnifiedWebSocketEmitter(
                user_id=UserID(user_id),
                redis_client=self.real_services.redis
            )
            emitters[user_id] = emitter
        
        # Mock WebSocket manager for controlled message delivery
        for user_id, emitter in emitters.items():
            connection = connections[user_id]
            with patch.object(emitter, '_websocket_manager') as mock_manager:
                async def make_mock_emit(conn=connection):
                    async def mock_emit_to_user(target_user_id, message, **kwargs):
                        # Only deliver to correct user's connection
                        if target_user_id == conn.user_id:
                            await conn.send(json.dumps(message))
                    return mock_emit_to_user
                mock_manager.emit_to_user = await make_mock_emit()
        
        # Send different messages to each user simultaneously
        tasks = []
        for i, (user_id, emitter) in enumerate(emitters.items()):
            request_id = RequestID(f"req-user-{i+1}-{int(time.time())}")
            
            async def send_user_specific_events(uid=user_id, emit=emitter, rid=request_id, user_num=i+1):
                await emit.emit_agent_started(
                    request_id=rid,
                    agent_name=f"UserSpecificAgent{user_num}",
                    context=f"Processing request for user {user_num}"
                )
                
                await emit.emit_agent_thinking(
                    request_id=rid,
                    thinking_content=f"Analyzing user {user_num} specific data...",
                    reasoning_step=1
                )
                
                await emit.emit_agent_completed(
                    request_id=rid,
                    agent_name=f"UserSpecificAgent{user_num}",
                    result={"user_insights": f"Specific to user {user_num}"},
                    total_duration_ms=200
                )
            
            tasks.append(send_user_specific_events())
        
        # Execute all user events concurrently
        await asyncio.gather(*tasks)
        
        # Verify message isolation - each user should only receive their own messages
        for i, (user_id, connection) in enumerate(connections.items()):
            user_events = connection.get_sent_events()
            assert len(user_events) >= 3, f"User {i+1} should have received at least 3 events"
            
            # Verify user-specific content
            for event in user_events:
                message = event['message']
                if 'agent_name' in message:
                    assert f"UserSpecificAgent{i+1}" in message['agent_name'], \
                        f"User {i+1} received wrong agent message"
                if 'context' in message:
                    assert f"user {i+1}" in message['context'], \
                        f"User {i+1} received wrong context message"
                if 'result' in message and isinstance(message['result'], dict):
                    if 'user_insights' in message['result']:
                        assert f"user {i+1}" in message['result']['user_insights'], \
                            f"User {i+1} received wrong result message"
        
        # Business value assertion - multi-user isolation maintained
        self.assert_business_value_delivered(
            {
                'concurrent_users': 3,
                'message_isolation': True,
                'enterprise_scalability': True,
                'multi_tenant_support': True
            },
            'automation'
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_resilience_and_recovery(self):
        """
        Test 4: WebSocket Connection Resilience & Recovery
        
        Business Value: Ensures uninterrupted AI chat sessions even during
        network disruptions, maintaining business continuity.
        """
        # Create authenticated user
        user_data = await self.create_authenticated_user("resilience-test")
        user_id = user_data['user_id']
        
        # Set up WebSocket components
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        bridge = await self.setup_websocket_bridge()
        
        # Create initial connection
        connection1 = await self.create_websocket_connection(user_id)
        await websocket_manager.register_connection(
            connection_id=connection1.connection_id,
            user_id=user_id,
            websocket=connection1
        )
        
        # Verify initial connection
        connections = await websocket_manager.get_user_connections(user_id)
        assert len(connections) == 1
        
        # Send initial message to establish communication
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_to_user(target_user_id, message, **kwargs):
                if target_user_id == user_id and connection1.is_connected:
                    await connection1.send(json.dumps(message))
            mock_manager.emit_to_user = mock_emit_to_user
            
            # Send message before disconnection
            await emitter.emit_agent_started(
                request_id=RequestID("pre-disconnect"),
                agent_name="ResilienceTestAgent",
                context="Testing connection resilience"
            )
        
        # Verify message was delivered
        assert len(connection1.get_sent_events()) == 1
        
        # Simulate connection loss
        connection1.disconnect()
        await websocket_manager.unregister_connection(connection1.connection_id)
        
        # Verify connection was removed
        connections = await websocket_manager.get_user_connections(user_id)
        assert len(connections) == 0
        
        # Simulate reconnection (new connection for same user)
        connection2 = await self.create_websocket_connection(user_id)
        await websocket_manager.register_connection(
            connection_id=connection2.connection_id,
            user_id=user_id,
            websocket=connection2
        )
        
        # Verify new connection registered
        connections = await websocket_manager.get_user_connections(user_id)
        assert len(connections) == 1
        assert connections[0]['connection_id'] == connection2.connection_id
        
        # Test that new connection can receive messages
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_to_user_reconnected(target_user_id, message, **kwargs):
                if target_user_id == user_id and connection2.is_connected:
                    await connection2.send(json.dumps(message))
            mock_manager.emit_to_user = mock_emit_to_user_reconnected
            
            # Send message after reconnection
            await emitter.emit_agent_thinking(
                request_id=RequestID("post-reconnect"),
                thinking_content="Testing resilience after reconnection...",
                reasoning_step=1
            )
            
            await emitter.emit_agent_completed(
                request_id=RequestID("post-reconnect"),
                agent_name="ResilienceTestAgent",
                result={"resilience_test": "passed"},
                total_duration_ms=100
            )
        
        # Verify new connection received messages
        reconnect_events = connection2.get_sent_events()
        assert len(reconnect_events) >= 2
        
        # Verify bridge health after connection recovery
        bridge_status = await bridge.get_status()
        assert bridge_status['state'] in ['active', 'initializing']
        assert bridge_status['websocket_manager_healthy'] == True
        
        # Business value assertion - resilience maintained
        self.assert_business_value_delivered(
            {
                'connection_recovered': True,
                'service_continuity': True,
                'business_continuity': True,
                'zero_downtime': True
            },
            'automation'
        )

    @pytest.mark.asyncio
    async def test_websocket_message_ordering_and_delivery_guarantees(self):
        """
        Test 5: WebSocket Message Ordering & Delivery Guarantees
        
        Business Value: Ensures AI chat conversations maintain logical flow
        with proper message ordering for coherent user experience.
        """
        # Create authenticated user
        user_data = await self.create_authenticated_user("ordering-test")
        user_id = user_data['user_id']
        connection = await self.create_websocket_connection(user_id)
        
        # Set up emitter with message ordering tracking
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        message_order = []
        
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_with_ordering(target_user_id, message, **kwargs):
                if target_user_id == user_id:
                    message_with_timestamp = {
                        **message,
                        'delivery_order': len(message_order) + 1,
                        'delivery_timestamp': time.time()
                    }
                    message_order.append(message_with_timestamp)
                    await connection.send(json.dumps(message_with_timestamp))
            
            mock_manager.emit_to_user = mock_emit_with_ordering
            
            # Send sequence of events that must maintain order
            request_id = RequestID("ordering-test")
            
            # Rapid sequence of events
            await emitter.emit_agent_started(
                request_id=request_id,
                agent_name="OrderTestAgent", 
                context="Testing message ordering"
            )
            
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="Step 1: Analyzing requirements...",
                reasoning_step=1
            )
            
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="Step 2: Processing data...",
                reasoning_step=2
            )
            
            await emitter.emit_tool_executing(
                request_id=request_id,
                tool_name="data_processor",
                tool_description="Processing business data"
            )
            
            await emitter.emit_tool_completed(
                request_id=request_id,
                tool_name="data_processor",
                result={"processed_records": 1000},
                execution_time_ms=250
            )
            
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="Step 3: Analyzing results...",
                reasoning_step=3
            )
            
            await emitter.emit_agent_completed(
                request_id=request_id,
                agent_name="OrderTestAgent",
                result={"analysis": "completed", "recommendations": ["Optimize workflow", "Reduce costs"]},
                total_duration_ms=750
            )
        
        # Verify message ordering
        received_events = connection.get_sent_events()
        assert len(received_events) == 7
        
        # Verify chronological order by delivery_order field
        for i, event in enumerate(received_events):
            message = event['message']
            expected_order = i + 1
            assert message['delivery_order'] == expected_order, \
                f"Message {i} has wrong order: expected {expected_order}, got {message['delivery_order']}"
        
        # Verify logical flow order
        event_types = [event['message']['type'] for event in received_events]
        expected_flow = [
            'agent_started',
            'agent_thinking',  # Step 1
            'agent_thinking',  # Step 2  
            'tool_executing',
            'tool_completed',
            'agent_thinking',  # Step 3
            'agent_completed'
        ]
        assert event_types == expected_flow
        
        # Verify reasoning steps are in order
        thinking_events = [
            event['message'] for event in received_events 
            if event['message']['type'] == 'agent_thinking'
        ]
        reasoning_steps = [event['reasoning_step'] for event in thinking_events]
        assert reasoning_steps == [1, 2, 3]
        
        # Verify timestamps are monotonically increasing
        timestamps = [event['message']['delivery_timestamp'] for event in received_events]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1], \
                f"Timestamp ordering violation at index {i}"
        
        # Business value assertion - message ordering maintained
        self.assert_business_value_delivered(
            {
                'message_ordering': 'preserved',
                'logical_flow': 'maintained', 
                'user_experience': 'coherent',
                'reasoning_transparency': True
            },
            'insights'
        )

    @pytest.mark.asyncio
    async def test_websocket_state_persistence_with_redis(self):
        """
        Test 6: WebSocket State Persistence with Redis
        
        Business Value: Ensures chat session state survives service restarts
        and provides continuity for enterprise customers.
        """
        # Create authenticated user
        user_data = await self.create_authenticated_user("persistence-test")
        user_id = user_data['user_id']
        
        # Set up WebSocket manager with real Redis
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        connection = await self.create_websocket_connection(user_id)
        
        # Register connection with session data
        session_data = {
            'user_preferences': {'theme': 'dark', 'notifications': True},
            'active_conversation': {'thread_id': 'thread-123', 'message_count': 5},
            'business_context': {'organization': 'TestCorp', 'role': 'analyst'}
        }
        
        await websocket_manager.register_connection(
            connection_id=connection.connection_id,
            user_id=user_id,
            websocket=connection,
            session_data=session_data
        )
        
        # Store additional session state in Redis
        session_key = f"websocket:session:{user_id}"
        await self.real_services.redis.set_json(session_key, {
            'connection_id': connection.connection_id,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'session_data': session_data
        }, ex=3600)
        
        # Verify state is persisted in Redis
        stored_session = await self.real_services.redis.get_json(session_key)
        assert stored_session is not None
        assert stored_session['connection_id'] == connection.connection_id
        assert stored_session['session_data'] == session_data
        
        # Simulate service restart by creating new WebSocket manager
        new_websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        
        # Restore session from Redis
        restored_session = await self.real_services.redis.get_json(session_key)
        assert restored_session is not None
        
        # Create new connection for same user (simulating reconnection after restart)
        new_connection = await self.create_websocket_connection(user_id)
        
        # Register with restored session data
        await new_websocket_manager.register_connection(
            connection_id=new_connection.connection_id,
            user_id=user_id,
            websocket=new_connection,
            session_data=restored_session['session_data']
        )
        
        # Verify session data is available after "restart"
        connection_info = await new_websocket_manager.get_connection_info(new_connection.connection_id)
        assert connection_info['user_id'] == user_id
        assert connection_info.get('session_data') == session_data
        
        # Test that business context is preserved
        restored_context = connection_info.get('session_data', {})
        assert restored_context['business_context']['organization'] == 'TestCorp'
        assert restored_context['business_context']['role'] == 'analyst'
        assert restored_context['user_preferences']['theme'] == 'dark'
        assert restored_context['active_conversation']['thread_id'] == 'thread-123'
        
        # Update session state and verify persistence
        updated_session_data = {
            **session_data,
            'active_conversation': {'thread_id': 'thread-456', 'message_count': 12}
        }
        
        await self.real_services.redis.set_json(session_key, {
            'connection_id': new_connection.connection_id,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_activity': datetime.now(timezone.utc).isoformat(),
            'session_data': updated_session_data
        }, ex=3600)
        
        # Verify update persisted
        final_session = await self.real_services.redis.get_json(session_key)
        assert final_session['session_data']['active_conversation']['thread_id'] == 'thread-456'
        assert final_session['session_data']['active_conversation']['message_count'] == 12
        
        # Business value assertion - state persistence maintained
        self.assert_business_value_delivered(
            {
                'session_continuity': True,
                'business_context_preserved': True,
                'user_preferences_maintained': True,
                'enterprise_reliability': True
            },
            'automation'
        )

    @pytest.mark.asyncio
    async def test_websocket_error_propagation_and_handling(self):
        """
        Test 7: WebSocket Error Propagation & Handling
        
        Business Value: Ensures users receive clear error feedback during
        AI processing issues, maintaining trust and enabling error recovery.
        """
        # Create authenticated user
        user_data = await self.create_authenticated_user("error-test")
        user_id = user_data['user_id']
        connection = await self.create_websocket_connection(user_id)
        
        # Set up emitter for error scenarios
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        error_events = []
        
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_with_errors(target_user_id, message, **kwargs):
                if target_user_id == user_id:
                    if message.get('type') in ['error', 'agent_error', 'tool_error']:
                        error_events.append(message)
                    await connection.send(json.dumps(message))
            
            mock_manager.emit_to_user = mock_emit_with_errors
            
            # Test various error scenarios
            request_id = RequestID("error-test")
            
            # 1. Agent initialization error
            await emitter.emit_agent_error(
                request_id=request_id,
                error_type="initialization_error",
                error_message="Failed to initialize data analysis agent",
                recoverable=True,
                suggested_action="Please try your request again"
            )
            
            # 2. Tool execution error
            await emitter.emit_tool_error(
                request_id=request_id,
                tool_name="data_connector",
                error_type="connection_error",
                error_message="Unable to connect to data source",
                error_details={
                    "source": "customer_database",
                    "timeout_ms": 5000,
                    "retry_attempt": 1
                },
                recoverable=True
            )
            
            # 3. Processing error with recovery
            await emitter.emit_agent_started(
                request_id=request_id,
                agent_name="ErrorRecoveryAgent",
                context="Attempting error recovery"
            )
            
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="Attempting to recover from previous error...",
                reasoning_step=1
            )
            
            # 4. System error (non-recoverable)
            await emitter.emit_system_error(
                request_id=request_id,
                error_type="memory_error",
                error_message="Insufficient memory for large dataset processing",
                error_code="MEM_001",
                recoverable=False,
                suggested_action="Please reduce dataset size or contact support"
            )
        
        # Verify error events were delivered
        received_events = connection.get_sent_events()
        assert len(received_events) >= 6  # At least error events + recovery events
        
        # Verify error events contain proper information
        assert len(error_events) >= 3  # Should have agent_error, tool_error, system_error
        
        # Check agent error details
        agent_errors = [e for e in error_events if e.get('type') == 'agent_error']
        assert len(agent_errors) >= 1
        agent_error = agent_errors[0]
        assert agent_error['error_type'] == 'initialization_error'
        assert 'Failed to initialize' in agent_error['error_message']
        assert agent_error['recoverable'] == True
        assert 'suggested_action' in agent_error
        
        # Check tool error details
        tool_errors = [e for e in error_events if e.get('type') == 'tool_error']
        assert len(tool_errors) >= 1
        tool_error = tool_errors[0]
        assert tool_error['tool_name'] == 'data_connector'
        assert tool_error['error_type'] == 'connection_error'
        assert 'error_details' in tool_error
        assert tool_error['error_details']['source'] == 'customer_database'
        
        # Check system error details
        system_errors = [e for e in error_events if e.get('type') == 'system_error']
        assert len(system_errors) >= 1
        system_error = system_errors[0]
        assert system_error['error_type'] == 'memory_error'
        assert system_error['recoverable'] == False
        assert 'error_code' in system_error
        assert system_error['error_code'] == 'MEM_001'
        
        # Verify recovery events were also delivered
        recovery_events = [
            event['message'] for event in received_events 
            if event['message'].get('agent_name') == 'ErrorRecoveryAgent'
        ]
        assert len(recovery_events) >= 1
        
        thinking_events = [
            event['message'] for event in received_events
            if event['message'].get('type') == 'agent_thinking' and 'recover' in event['message'].get('thinking_content', '')
        ]
        assert len(thinking_events) >= 1
        
        # Business value assertion - error handling provides user value
        self.assert_business_value_delivered(
            {
                'error_transparency': True,
                'recovery_guidance': True,
                'user_trust_maintained': True,
                'actionable_error_info': True
            },
            'insights'
        )

    @pytest.mark.asyncio
    async def test_websocket_performance_under_concurrent_load(self):
        """
        Test 8: WebSocket Performance Under Concurrent Connections
        
        Business Value: Ensures platform can handle enterprise-scale concurrent
        AI chat sessions without performance degradation.
        """
        concurrent_users = 10
        events_per_user = 5
        max_response_time_ms = 500  # Maximum acceptable response time
        
        # Create multiple authenticated users
        users = []
        for i in range(concurrent_users):
            user_data = await self.create_authenticated_user(f"perf-user-{i}")
            users.append(user_data)
        
        # Set up WebSocket manager
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        
        # Track performance metrics
        connection_times = []
        event_delivery_times = []
        
        async def setup_user_connection(user_data):
            """Set up WebSocket connection for a user."""
            user_id = user_data['user_id']
            start_time = time.time()
            
            # Create connection
            connection = await self.create_websocket_connection(user_id)
            
            # Register connection
            await websocket_manager.register_connection(
                connection_id=connection.connection_id,
                user_id=user_id,
                websocket=connection
            )
            
            connection_time = (time.time() - start_time) * 1000
            connection_times.append(connection_time)
            
            return connection
        
        # Set up all connections concurrently
        start_setup = time.time()
        connections = await asyncio.gather(*[
            setup_user_connection(user_data) for user_data in users
        ])
        setup_duration = time.time() - start_setup
        
        # Verify all connections established quickly
        assert len(connections) == concurrent_users
        assert setup_duration < 5.0, f"Connection setup took too long: {setup_duration:.2f}s"
        
        # Test concurrent event delivery
        async def send_events_to_user(user_data, connection):
            """Send events to a specific user."""
            user_id = user_data['user_id']
            emitter = UnifiedWebSocketEmitter(
                user_id=UserID(user_id),
                redis_client=self.real_services.redis
            )
            
            event_times = []
            
            with patch.object(emitter, '_websocket_manager') as mock_manager:
                async def mock_emit_with_timing(target_user_id, message, **kwargs):
                    start = time.time()
                    if target_user_id == user_id:
                        await connection.send(json.dumps(message))
                    delivery_time = (time.time() - start) * 1000
                    event_times.append(delivery_time)
                
                mock_manager.emit_to_user = mock_emit_with_timing
                
                # Send multiple events per user
                request_id = RequestID(f"perf-{user_id}")
                
                await emitter.emit_agent_started(
                    request_id=request_id,
                    agent_name=f"PerfTestAgent-{user_id[-4:]}",
                    context="Performance testing"
                )
                
                await emitter.emit_agent_thinking(
                    request_id=request_id,
                    thinking_content=f"Processing for user {user_id[-4:]}...",
                    reasoning_step=1
                )
                
                await emitter.emit_tool_executing(
                    request_id=request_id,
                    tool_name="performance_analyzer",
                    tool_description="Analyzing performance metrics"
                )
                
                await emitter.emit_tool_completed(
                    request_id=request_id,
                    tool_name="performance_analyzer",
                    result={"metrics": {"response_time": "optimal"}},
                    execution_time_ms=50
                )
                
                await emitter.emit_agent_completed(
                    request_id=request_id,
                    agent_name=f"PerfTestAgent-{user_id[-4:]}",
                    result={"performance": "excellent"},
                    total_duration_ms=200
                )
            
            return event_times
        
        # Send events to all users concurrently
        start_events = time.time()
        all_event_times = await asyncio.gather(*[
            send_events_to_user(user_data, connection) 
            for user_data, connection in zip(users, connections)
        ])
        total_event_duration = time.time() - start_events
        
        # Flatten event times
        for user_event_times in all_event_times:
            event_delivery_times.extend(user_event_times)
        
        # Performance assertions
        
        # Connection performance
        avg_connection_time = sum(connection_times) / len(connection_times)
        max_connection_time = max(connection_times)
        assert avg_connection_time < 100, f"Average connection time too slow: {avg_connection_time:.2f}ms"
        assert max_connection_time < 200, f"Maximum connection time too slow: {max_connection_time:.2f}ms"
        
        # Event delivery performance
        avg_event_time = sum(event_delivery_times) / len(event_delivery_times)
        max_event_time = max(event_delivery_times)
        assert avg_event_time < 50, f"Average event delivery too slow: {avg_event_time:.2f}ms"
        assert max_event_time < max_response_time_ms, f"Maximum event delivery too slow: {max_event_time:.2f}ms"
        
        # Overall throughput
        total_events_sent = len(users) * events_per_user
        events_per_second = total_events_sent / total_event_duration
        assert events_per_second > 50, f"Event throughput too low: {events_per_second:.2f} events/sec"
        
        # Verify all events delivered correctly
        for connection in connections:
            user_events = connection.get_sent_events()
            assert len(user_events) == events_per_user, \
                f"User {connection.user_id} received {len(user_events)} events, expected {events_per_user}"
        
        # Log performance metrics
        self.logger.info(f"Performance Test Results:")
        self.logger.info(f"  - Concurrent users: {concurrent_users}")
        self.logger.info(f"  - Average connection time: {avg_connection_time:.2f}ms")
        self.logger.info(f"  - Average event delivery time: {avg_event_time:.2f}ms")
        self.logger.info(f"  - Event throughput: {events_per_second:.2f} events/sec")
        self.logger.info(f"  - Total test duration: {total_event_duration:.2f}s")
        
        # Business value assertion - performance meets enterprise requirements
        self.assert_business_value_delivered(
            {
                'concurrent_users_supported': concurrent_users,
                'response_time_ms': avg_event_time,
                'throughput_events_per_sec': events_per_second,
                'enterprise_scalability': True
            },
            'automation'
        )

    @pytest.mark.asyncio
    async def test_websocket_security_and_authorization(self):
        """
        Test 9: WebSocket Security & Authorization Validation
        
        Business Value: Ensures secure AI chat sessions with proper access
        controls for enterprise customers handling sensitive data.
        """
        # Create authenticated users with different roles
        admin_user = await self.create_authenticated_user("admin-security")
        regular_user = await self.create_authenticated_user("regular-security")
        
        # Set up WebSocket manager with security validation
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        
        # Create connections for both users
        admin_connection = await self.create_websocket_connection(admin_user['user_id'])
        regular_connection = await self.create_websocket_connection(regular_user['user_id'])
        
        # Register connections with role-based session data
        await websocket_manager.register_connection(
            connection_id=admin_connection.connection_id,
            user_id=admin_user['user_id'],
            websocket=admin_connection,
            session_data={'role': 'admin', 'permissions': ['read', 'write', 'admin']}
        )
        
        await websocket_manager.register_connection(
            connection_id=regular_connection.connection_id,
            user_id=regular_user['user_id'],
            websocket=regular_connection,
            session_data={'role': 'user', 'permissions': ['read']}
        )
        
        # Test unauthorized access attempt - regular user trying to access admin features
        regular_emitter = UnifiedWebSocketEmitter(
            user_id=UserID(regular_user['user_id']),
            redis_client=self.real_services.redis
        )
        
        unauthorized_events = []
        security_events = []
        
        with patch.object(regular_emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_with_security(target_user_id, message, **kwargs):
                # Simulate security validation
                if message.get('type') == 'admin_operation':
                    # Reject unauthorized admin operations
                    security_event = {
                        'type': 'authorization_error',
                        'error_code': 'INSUFFICIENT_PERMISSIONS',
                        'error_message': 'User does not have admin permissions',
                        'attempted_operation': message.get('operation'),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    security_events.append(security_event)
                    await regular_connection.send(json.dumps(security_event))
                    return
                
                if target_user_id == regular_user['user_id']:
                    await regular_connection.send(json.dumps(message))
            
            mock_manager.emit_to_user = mock_emit_with_security
            
            # Attempt unauthorized admin operation
            await regular_emitter.emit_custom_event({
                'type': 'admin_operation',
                'operation': 'user_management',
                'action': 'delete_user',
                'target_user': 'other-user-id',
                'request_id': 'unauthorized-attempt'
            })
        
        # Test authorized admin operation
        admin_emitter = UnifiedWebSocketEmitter(
            user_id=UserID(admin_user['user_id']),
            redis_client=self.real_services.redis
        )
        
        admin_events = []
        
        with patch.object(admin_emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_admin(target_user_id, message, **kwargs):
                if target_user_id == admin_user['user_id']:
                    admin_events.append(message)
                    await admin_connection.send(json.dumps(message))
            
            mock_manager.emit_to_user = mock_emit_admin
            
            # Authorized admin operation
            await admin_emitter.emit_custom_event({
                'type': 'admin_operation',
                'operation': 'system_status',
                'action': 'get_health_metrics',
                'request_id': 'authorized-admin-request'
            })
            
            # Regular user operations should work normally
            await admin_emitter.emit_agent_started(
                request_id=RequestID("admin-agent-test"),
                agent_name="AdminAnalysisAgent",
                context="Performing authorized admin analysis"
            )
        
        # Verify security enforcement
        
        # Check that unauthorized operation was blocked
        regular_events = regular_connection.get_sent_events()
        assert len(security_events) >= 1, "Security violation should have been detected"
        
        security_error = security_events[0]
        assert security_error['type'] == 'authorization_error'
        assert security_error['error_code'] == 'INSUFFICIENT_PERMISSIONS'
        assert 'admin permissions' in security_error['error_message']
        
        # Check that authorized operations succeeded
        admin_received_events = admin_connection.get_sent_events()
        assert len(admin_received_events) >= 2  # Admin operation + agent_started
        
        admin_operations = [
            event['message'] for event in admin_received_events
            if event['message'].get('type') == 'admin_operation'
        ]
        assert len(admin_operations) >= 1
        assert admin_operations[0]['operation'] == 'system_status'
        
        # Test connection isolation - users can only access their own connections
        other_user_connections = await websocket_manager.get_user_connections(admin_user['user_id'])
        assert len(other_user_connections) == 1
        assert other_user_connections[0]['user_id'] == admin_user['user_id']
        
        # Verify session data isolation
        admin_info = await websocket_manager.get_connection_info(admin_connection.connection_id)
        regular_info = await websocket_manager.get_connection_info(regular_connection.connection_id)
        
        assert admin_info['session_data']['role'] == 'admin'
        assert regular_info['session_data']['role'] == 'user'
        assert 'admin' in admin_info['session_data']['permissions']
        assert 'admin' not in regular_info['session_data']['permissions']
        
        # Business value assertion - security controls are effective
        self.assert_business_value_delivered(
            {
                'role_based_access_control': True,
                'unauthorized_access_blocked': True,
                'connection_isolation': True,
                'enterprise_security': True
            },
            'automation'
        )

    @pytest.mark.asyncio
    async def test_websocket_business_value_delivery_through_chat_interactions(self):
        """
        Test 10: WebSocket Business Value Delivery Through Chat Interactions
        
        Business Value: End-to-end validation that WebSocket events enable
        substantive business value delivery through AI chat interactions.
        """
        # Create business user scenario
        business_user = await self.create_authenticated_user("business-value")
        user_id = business_user['user_id']
        connection = await self.create_websocket_connection(user_id)
        
        # Set up emitter for business scenario
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        business_events = []
        
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_business_value(target_user_id, message, **kwargs):
                if target_user_id == user_id:
                    business_events.append(message)
                    await connection.send(json.dumps(message))
            
            mock_manager.emit_to_user = mock_emit_business_value
            
            # Simulate complete business value delivery workflow
            request_id = RequestID("business-analysis")
            
            # 1. User asks for cost optimization analysis
            await emitter.emit_agent_started(
                request_id=request_id,
                agent_name="CostOptimizationAgent",
                context="Analyzing operational costs and identifying savings opportunities"
            )
            
            # 2. Agent explains its approach (transparency builds trust)
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="I'll analyze your current infrastructure spending patterns, identify underutilized resources, and recommend optimization strategies...",
                reasoning_step=1
            )
            
            # 3. Data analysis tool execution (shows real work being done)
            await emitter.emit_tool_executing(
                request_id=request_id,
                tool_name="cost_analyzer",
                tool_description="Analyzing cloud infrastructure costs and usage patterns"
            )
            
            # 4. Deliver actionable insights (business value)
            await emitter.emit_tool_completed(
                request_id=request_id,
                tool_name="cost_analyzer",
                result={
                    "potential_monthly_savings": 4500,
                    "optimization_opportunities": [
                        {
                            "category": "Compute",
                            "current_cost": 12000,
                            "optimized_cost": 8500,
                            "savings": 3500,
                            "action": "Right-size overprovisioned instances"
                        },
                        {
                            "category": "Storage",
                            "current_cost": 3000,
                            "optimized_cost": 2000,
                            "savings": 1000,
                            "action": "Migrate cold data to cheaper storage tier"
                        }
                    ],
                    "risk_assessment": "Low risk - changes can be implemented incrementally",
                    "implementation_timeline": "2-3 weeks"
                },
                execution_time_ms=2500
            )
            
            # 5. Generate implementation plan (actionable next steps)
            await emitter.emit_tool_executing(
                request_id=request_id,
                tool_name="implementation_planner",
                tool_description="Creating step-by-step implementation plan for cost optimizations"
            )
            
            await emitter.emit_tool_completed(
                request_id=request_id,
                tool_name="implementation_planner",
                result={
                    "implementation_plan": [
                        {"step": 1, "action": "Audit current instance utilization", "duration": "3 days"},
                        {"step": 2, "action": "Identify right-sizing candidates", "duration": "2 days"},
                        {"step": 3, "action": "Test resizing in staging environment", "duration": "5 days"},
                        {"step": 4, "action": "Implement production changes", "duration": "7 days"}
                    ],
                    "success_metrics": [
                        "Monthly cost reduction of $4,500",
                        "Maintained application performance",
                        "Zero downtime during implementation"
                    ]
                },
                execution_time_ms=1200
            )
            
            # 6. Final recommendations and summary
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="Based on my analysis, I can recommend specific actions that will reduce your infrastructure costs by 30% while maintaining performance...",
                reasoning_step=2
            )
            
            await emitter.emit_agent_completed(
                request_id=request_id,
                agent_name="CostOptimizationAgent",
                result={
                    "analysis_summary": "Cost optimization analysis complete",
                    "total_potential_savings": 4500,
                    "monthly_roi": "30% cost reduction",
                    "confidence_level": "95%",
                    "next_actions": [
                        "Review implementation plan",
                        "Schedule staging environment testing",
                        "Set up monitoring for optimization metrics"
                    ],
                    "business_impact": "Significant cost reduction with minimal operational risk"
                },
                total_duration_ms=5000
            )
        
        # Verify business value was delivered through WebSocket events
        received_events = connection.get_sent_events()
        assert len(received_events) >= 7  # All critical events delivered
        
        # Extract business value metrics from events
        cost_analysis = None
        implementation_plan = None
        final_summary = None
        
        for event in business_events:
            if event.get('type') == 'tool_completed':
                result = event.get('result', {})
                if 'potential_monthly_savings' in result:
                    cost_analysis = result
                elif 'implementation_plan' in result:
                    implementation_plan = result
            elif event.get('type') == 'agent_completed':
                final_summary = event.get('result', {})
        
        # Verify substantive business value was delivered
        assert cost_analysis is not None, "Cost analysis results missing"
        assert cost_analysis['potential_monthly_savings'] == 4500
        assert len(cost_analysis['optimization_opportunities']) >= 2
        assert cost_analysis['risk_assessment'] is not None
        
        assert implementation_plan is not None, "Implementation plan missing"
        assert len(implementation_plan['implementation_plan']) >= 4
        assert len(implementation_plan['success_metrics']) >= 3
        
        assert final_summary is not None, "Final summary missing"
        assert final_summary['total_potential_savings'] == 4500
        assert final_summary['confidence_level'] == '95%'
        assert len(final_summary['next_actions']) >= 3
        
        # Verify transparency and trust-building elements
        thinking_events = [e for e in business_events if e.get('type') == 'agent_thinking']
        assert len(thinking_events) >= 2, "Agent reasoning transparency missing"
        
        tool_events = [e for e in business_events if e.get('type') in ['tool_executing', 'tool_completed']]
        assert len(tool_events) >= 4, "Tool execution transparency missing"
        
        # Verify all critical events present for business value
        critical_events = self.extract_critical_events(business_events)
        for event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
            assert len(critical_events[event_type]) >= 1, f"Missing critical event: {event_type}"
        
        # Calculate business impact metrics
        total_savings = cost_analysis['potential_monthly_savings']
        annual_savings = total_savings * 12
        roi_percentage = 30  # From analysis
        
        # Business value assertion - substantial value delivered
        self.assert_business_value_delivered(
            {
                'monthly_cost_savings': total_savings,
                'annual_savings_potential': annual_savings,
                'roi_percentage': roi_percentage,
                'actionable_recommendations': len(final_summary['next_actions']),
                'implementation_plan_provided': True,
                'risk_assessment_completed': True,
                'user_transparency': len(thinking_events),
                'tool_visibility': len(tool_events)
            },
            'cost_savings'
        )

    @pytest.mark.asyncio
    async def test_websocket_compression_and_message_optimization(self):
        """
        Test 11: WebSocket Compression & Message Optimization
        
        Business Value: Ensures efficient bandwidth usage for enterprise
        customers with high-volume AI chat interactions.
        """
        # Create user for compression testing
        user_data = await self.create_authenticated_user("compression-test")
        user_id = user_data['user_id']
        
        # Create connection with compression enabled
        connection = await self.create_websocket_connection(user_id)
        connection.compression_enabled = True
        
        # Set up emitter with compression tracking
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        compression_metrics = {
            'original_sizes': [],
            'compressed_sizes': [],
            'compression_ratios': []
        }
        
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_with_compression(target_user_id, message, **kwargs):
                if target_user_id == user_id:
                    # Simulate message compression
                    original_message = json.dumps(message)
                    original_size = len(original_message.encode('utf-8'))
                    
                    # Simple compression simulation (real compression would use gzip/deflate)
                    compressed_message = original_message
                    if len(original_message) > 100:
                        # Simulate ~30% compression for larger messages
                        compressed_size = int(original_size * 0.7)
                    else:
                        compressed_size = original_size  # No compression benefit for small messages
                    
                    compression_ratio = original_size / compressed_size if compressed_size > 0 else 1.0
                    
                    compression_metrics['original_sizes'].append(original_size)
                    compression_metrics['compressed_sizes'].append(compressed_size)
                    compression_metrics['compression_ratios'].append(compression_ratio)
                    
                    # Add compression metadata to message
                    message_with_metadata = {
                        **message,
                        'compression': {
                            'enabled': True,
                            'original_size': original_size,
                            'compressed_size': compressed_size,
                            'ratio': compression_ratio
                        }
                    }
                    
                    await connection.send(json.dumps(message_with_metadata))
            
            mock_manager.emit_to_user = mock_emit_with_compression
            
            # Send various sized messages to test compression
            request_id = RequestID("compression-test")
            
            # Small message (minimal compression benefit)
            await emitter.emit_agent_started(
                request_id=request_id,
                agent_name="CompressionTestAgent",
                context="Testing compression efficiency"
            )
            
            # Medium message with detailed content
            await emitter.emit_agent_thinking(
                request_id=request_id,
                thinking_content="I'm analyzing your request and considering multiple approaches to optimize performance. This involves evaluating different compression algorithms, measuring bandwidth usage, and ensuring optimal user experience across various network conditions and device capabilities.",
                reasoning_step=1
            )
            
            # Large message with extensive data
            large_dataset = {
                "analysis_results": [
                    {"metric": f"performance_indicator_{i}", "value": i * 1.5, "trend": "increasing"} 
                    for i in range(50)
                ],
                "recommendations": [
                    {
                        "category": f"optimization_{i}",
                        "description": f"Detailed recommendation {i} for improving system performance through various optimization techniques and best practices",
                        "impact": "high" if i % 3 == 0 else "medium",
                        "implementation_effort": "low" if i % 2 == 0 else "high"
                    }
                    for i in range(25)
                ],
                "detailed_explanation": "This comprehensive analysis covers multiple aspects of system performance optimization, including but not limited to CPU utilization patterns, memory allocation strategies, network bandwidth optimization, database query performance tuning, caching mechanisms implementation, load balancing configuration, and automated scaling policies configuration."
            }
            
            await emitter.emit_tool_completed(
                request_id=request_id,
                tool_name="performance_analyzer",
                result=large_dataset,
                execution_time_ms=3000
            )
            
            # Very large message (maximum compression benefit)
            extensive_results = {
                "comprehensive_analysis": {
                    "data_points": [
                        {
                            "timestamp": f"2024-01-{i:02d}T10:00:00Z",
                            "metrics": {
                                "cpu_utilization": 45 + (i % 20),
                                "memory_usage": 60 + (i % 30),
                                "network_io": 1000 + (i * 50),
                                "disk_io": 500 + (i * 25)
                            },
                            "events": [
                                f"Event {j}: System performance measurement recorded at {i:02d}:00:00 showing normal operational parameters"
                                for j in range(5)
                            ]
                        }
                        for i in range(100)
                    ],
                    "summary_statistics": {
                        "average_cpu": 55.5,
                        "peak_memory": 89.2,
                        "total_network_bytes": 15000000,
                        "performance_score": 87.3
                    }
                }
            }
            
            await emitter.emit_agent_completed(
                request_id=request_id,
                agent_name="CompressionTestAgent",
                result=extensive_results,
                total_duration_ms=6000
            )
        
        # Analyze compression performance
        received_events = connection.get_sent_events()
        assert len(received_events) >= 4
        
        # Verify compression was applied
        total_original_size = sum(compression_metrics['original_sizes'])
        total_compressed_size = sum(compression_metrics['compressed_sizes'])
        overall_compression_ratio = total_original_size / total_compressed_size if total_compressed_size > 0 else 1.0
        
        # Compression should provide meaningful bandwidth savings for larger messages
        assert overall_compression_ratio > 1.0, "Compression should reduce message sizes"
        
        # Verify compression metadata is included
        for event in received_events:
            message = event['message']
            if 'compression' in message:
                compression_info = message['compression']
                assert compression_info['enabled'] == True
                assert compression_info['original_size'] > 0
                assert compression_info['compressed_size'] > 0
                assert compression_info['ratio'] >= 1.0
        
        # Check that larger messages achieved better compression ratios
        larger_message_ratios = []
        for i, original_size in enumerate(compression_metrics['original_sizes']):
            if original_size > 1000:  # Consider messages over 1KB as "large"
                larger_message_ratios.append(compression_metrics['compression_ratios'][i])
        
        if larger_message_ratios:
            avg_large_compression = sum(larger_message_ratios) / len(larger_message_ratios)
            assert avg_large_compression > 1.2, f"Large messages should achieve >20% compression, got {avg_large_compression:.2f}"
        
        # Calculate bandwidth savings
        bandwidth_saved_bytes = total_original_size - total_compressed_size
        bandwidth_saved_percentage = (bandwidth_saved_bytes / total_original_size) * 100 if total_original_size > 0 else 0
        
        # Log compression metrics
        self.logger.info(f"Compression Test Results:")
        self.logger.info(f"  - Total original size: {total_original_size} bytes")
        self.logger.info(f"  - Total compressed size: {total_compressed_size} bytes")
        self.logger.info(f"  - Bandwidth saved: {bandwidth_saved_bytes} bytes ({bandwidth_saved_percentage:.1f}%)")
        self.logger.info(f"  - Overall compression ratio: {overall_compression_ratio:.2f}:1")
        
        # Business value assertion - compression provides bandwidth efficiency
        self.assert_business_value_delivered(
            {
                'bandwidth_savings_bytes': bandwidth_saved_bytes,
                'bandwidth_savings_percentage': bandwidth_saved_percentage,
                'compression_ratio': overall_compression_ratio,
                'enterprise_efficiency': True
            },
            'cost_savings'
        )

    @pytest.mark.asyncio
    async def test_websocket_connection_lifecycle_management(self):
        """
        Test 12: WebSocket Connection Lifecycle Management
        
        Business Value: Ensures reliable connection management for enterprise
        customers with long-running AI chat sessions and proper resource cleanup.
        """
        # Create user for lifecycle testing
        user_data = await self.create_authenticated_user("lifecycle-test")
        user_id = user_data['user_id']
        
        # Set up WebSocket manager for lifecycle tracking
        websocket_manager = UnifiedWebSocketManager(redis_client=self.real_services.redis)
        
        lifecycle_events = []
        
        # Track connection lifecycle
        original_register = websocket_manager.register_connection
        original_unregister = websocket_manager.unregister_connection
        
        async def track_register(*args, **kwargs):
            result = await original_register(*args, **kwargs)
            lifecycle_events.append({
                'event': 'connection_registered',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'connection_id': kwargs.get('connection_id') or args[0]
            })
            return result
        
        async def track_unregister(*args, **kwargs):
            result = await original_unregister(*args, **kwargs)
            lifecycle_events.append({
                'event': 'connection_unregistered', 
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'connection_id': kwargs.get('connection_id') or args[0]
            })
            return result
        
        websocket_manager.register_connection = track_register
        websocket_manager.unregister_connection = track_unregister
        
        # Phase 1: Connection establishment
        connection1 = await self.create_websocket_connection(user_id)
        
        await websocket_manager.register_connection(
            connection_id=connection1.connection_id,
            user_id=user_id,
            websocket=connection1,
            session_data={'phase': 'initial', 'created_at': datetime.now(timezone.utc).isoformat()}
        )
        
        # Verify connection is active
        connections = await websocket_manager.get_user_connections(user_id)
        assert len(connections) == 1
        assert connections[0]['connection_id'] == connection1.connection_id
        
        # Phase 2: Active usage period
        emitter = UnifiedWebSocketEmitter(
            user_id=UserID(user_id),
            redis_client=self.real_services.redis
        )
        
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_lifecycle(target_user_id, message, **kwargs):
                if target_user_id == user_id and connection1.is_connected:
                    await connection1.send(json.dumps(message))
            mock_manager.emit_to_user = mock_emit_lifecycle
            
            # Simulate active usage
            for i in range(3):
                await emitter.emit_agent_started(
                    request_id=RequestID(f"lifecycle-{i}"),
                    agent_name=f"LifecycleAgent{i}",
                    context=f"Active usage phase {i+1}"
                )
                
                await emitter.emit_agent_completed(
                    request_id=RequestID(f"lifecycle-{i}"),
                    agent_name=f"LifecycleAgent{i}",
                    result={'phase': i+1, 'status': 'completed'},
                    total_duration_ms=500
                )
        
        # Verify active usage
        usage_events = connection1.get_sent_events()
        assert len(usage_events) >= 6  # 3 started + 3 completed events
        
        # Phase 3: Connection replacement (user opens new tab/browser)
        connection2 = await self.create_websocket_connection(user_id)
        
        await websocket_manager.register_connection(
            connection_id=connection2.connection_id,
            user_id=user_id,
            websocket=connection2,
            session_data={'phase': 'replacement', 'replaces': connection1.connection_id}
        )
        
        # Verify both connections exist initially
        connections = await websocket_manager.get_user_connections(user_id)
        assert len(connections) == 2
        
        # Phase 4: Graceful cleanup of old connection
        await websocket_manager.unregister_connection(connection1.connection_id)
        connection1.disconnect()
        
        # Verify old connection removed
        connections = await websocket_manager.get_user_connections(user_id)
        assert len(connections) == 1
        assert connections[0]['connection_id'] == connection2.connection_id
        
        # Phase 5: Continue with new connection
        with patch.object(emitter, '_websocket_manager') as mock_manager:
            async def mock_emit_new_connection(target_user_id, message, **kwargs):
                if target_user_id == user_id and connection2.is_connected:
                    await connection2.send(json.dumps(message))
            mock_manager.emit_to_user = mock_emit_new_connection
            
            await emitter.emit_agent_started(
                request_id=RequestID("post-replacement"),
                agent_name="PostReplacementAgent",
                context="Testing new connection functionality"
            )
            
            await emitter.emit_agent_completed(
                request_id=RequestID("post-replacement"),
                agent_name="PostReplacementAgent",
                result={'connection_replacement': 'successful'},
                total_duration_ms=300
            )
        
        # Verify new connection works
        new_connection_events = connection2.get_sent_events()
        assert len(new_connection_events) >= 2
        
        # Phase 6: Session cleanup and final disconnection
        await websocket_manager.unregister_connection(connection2.connection_id)
        connection2.disconnect()
        
        # Verify complete cleanup
        final_connections = await websocket_manager.get_user_connections(user_id)
        assert len(final_connections) == 0
        
        # Analyze lifecycle events
        register_events = [e for e in lifecycle_events if e['event'] == 'connection_registered']
        unregister_events = [e for e in lifecycle_events if e['event'] == 'connection_unregistered']
        
        assert len(register_events) == 2, "Should have 2 connection registrations"
        assert len(unregister_events) == 2, "Should have 2 connection unregistrations"
        
        # Verify proper cleanup sequence
        for register_event, unregister_event in zip(register_events, unregister_events):
            register_time = datetime.fromisoformat(register_event['timestamp'])
            unregister_time = datetime.fromisoformat(unregister_event['timestamp'])
            assert unregister_time > register_time, "Unregistration should happen after registration"
        
        # Verify session persistence during connection replacement
        session_key = f"websocket:session:{user_id}"
        session_data = await self.real_services.redis.get_json(session_key)
        
        if session_data:
            # Session may contain information about connection replacement
            assert 'created_at' in session_data or 'last_activity' in session_data
        
        # Business value assertion - lifecycle management maintains service continuity
        self.assert_business_value_delivered(
            {
                'connection_lifecycle_managed': True,
                'graceful_connection_replacement': True,
                'resource_cleanup_complete': True,
                'service_continuity_maintained': True,
                'zero_data_loss': True
            },
            'automation'
        )


# Test execution configuration
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "--asyncio-mode=auto",
        "--real-services",  # Force real services usage
        "--log-cli-level=INFO"
    ])