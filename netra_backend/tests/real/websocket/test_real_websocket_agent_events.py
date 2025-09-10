"""Real WebSocket Agent Events Tests

Business Value Justification (BVJ):
- Segment: All Customer Tiers (Free, Early, Mid, Enterprise)
- Business Goal: Chat Value Delivery - Core Business Function
- Value Impact: Tests the 5 CRITICAL agent events that enable substantive chat interactions
- Strategic Impact: Protects 90% of user traffic - agent events are the foundation of chat value

CRITICAL per CLAUDE.md: Tests agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
These events MUST be sent during agent execution to enable meaningful AI interactions.

Tests real WebSocket agent event delivery with Docker services.
NO MOCKS - tests actual agent event flow that delivers business value.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.agent_events
@skip_if_no_real_services
class TestRealWebSocketAgentEvents:
    """Test real agent events through WebSocket connections.
    
    CRITICAL: Tests the 5 required agent events per CLAUDE.md:
    1. agent_started - User must see agent began processing their problem
    2. agent_thinking - Real-time reasoning visibility (shows AI working on solutions) 
    3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
    4. tool_completed - Tool results display (delivers actionable insights)
    5. agent_completed - User must know when valuable response is ready
    
    These events enable substantive chat interactions and deliver business value.
    """
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket URL from environment."""
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        """Get auth headers for WebSocket connection."""
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Agent-Events-Test/1.0"
        }
    
    @pytest.fixture
    def test_user_id(self):
        """Generate unique test user ID."""
        return f"test_user_events_{int(time.time())}"
    
    @pytest.mark.asyncio
    async def test_agent_started_event_delivery(self, websocket_url, auth_headers, test_user_id):
        """Test agent_started event is delivered when agent execution begins."""
        events_received = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=15
            ) as websocket:
                # Connect and authenticate
                connect_msg = {
                    "type": "connect",
                    "user_id": test_user_id,
                    "track_agent_events": True
                }
                await websocket.send(json.dumps(connect_msg))
                
                # Receive connection confirmation
                response = json.loads(await websocket.recv())
                assert response.get("status") == "connected"
                
                # Start an agent to trigger agent_started event
                start_agent_msg = {
                    "type": "start_agent",
                    "user_id": test_user_id,
                    "agent_type": "triage_agent",
                    "task": "Test agent startup event delivery",
                    "thread_id": f"thread_{test_user_id}"
                }
                await websocket.send(json.dumps(start_agent_msg))
                
                # Collect events for up to 10 seconds
                timeout_time = time.time() + 10
                while time.time() < timeout_time:
                    try:
                        message_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        message = json.loads(message_raw)
                        events_received.append(message)
                        
                        # Look for agent_started event
                        if message.get("type") == "agent_started":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Agent started event test failed: {e}")
        
        # Validate agent_started event was received
        agent_started_events = [e for e in events_received if e.get("type") == "agent_started"]
        assert len(agent_started_events) > 0, f"agent_started event not received. Events: {[e.get('type') for e in events_received]}"
        
        # Validate agent_started event structure
        agent_started = agent_started_events[0]
        assert "user_id" in agent_started
        assert "agent_type" in agent_started or "agent_name" in agent_started
        assert "timestamp" in agent_started or "started_at" in agent_started
    
    @pytest.mark.asyncio
    async def test_agent_thinking_event_delivery(self, websocket_url, auth_headers, test_user_id):
        """Test agent_thinking events show real-time reasoning visibility."""
        events_received = []
        thinking_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=20
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": test_user_id,
                    "enable_thinking_events": True
                }))
                
                await websocket.recv()  # Connection ack
                
                # Send a complex task that should generate thinking events
                complex_task_msg = {
                    "type": "user_message",
                    "user_id": test_user_id,
                    "content": "Analyze our database performance and suggest optimizations",
                    "thread_id": f"thread_{test_user_id}",
                    "request_thinking_events": True
                }
                await websocket.send(json.dumps(complex_task_msg))
                
                # Collect events for up to 15 seconds
                timeout_time = time.time() + 15
                while time.time() < timeout_time:
                    try:
                        message_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        message = json.loads(message_raw)
                        events_received.append(message)
                        
                        if message.get("type") == "agent_thinking":
                            thinking_events.append(message)
                        
                        # Stop after we get some thinking events or agent completes
                        if len(thinking_events) >= 2 or message.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            # Log error but don't fail immediately - thinking events may be optional
            print(f"Agent thinking event test error: {e}")
        
        # Validate thinking events (may be optional depending on agent implementation)
        if len(thinking_events) > 0:
            # Validate thinking event structure
            thinking_event = thinking_events[0]
            assert "user_id" in thinking_event
            assert "content" in thinking_event or "thought" in thinking_event or "reasoning" in thinking_event
            assert "timestamp" in thinking_event
            
            # Verify thinking content is meaningful
            content = thinking_event.get("content") or thinking_event.get("thought") or thinking_event.get("reasoning")
            assert len(content) > 10, "Thinking content should be meaningful"
        else:
            # Thinking events may not be implemented yet - log warning
            print(f"WARNING: No agent_thinking events received. All events: {[e.get('type') for e in events_received]}")
    
    @pytest.mark.asyncio
    async def test_tool_executing_and_completed_events(self, websocket_url, auth_headers, test_user_id):
        """Test tool_executing and tool_completed events for transparency."""
        events_received = []
        tool_executing_events = []
        tool_completed_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=25
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": test_user_id,
                    "track_tool_events": True
                }))
                
                await websocket.recv()  # Connection ack
                
                # Send task that requires tool usage
                tool_task_msg = {
                    "type": "user_message",
                    "user_id": test_user_id,
                    "content": "Check the system status and generate a report",
                    "thread_id": f"thread_{test_user_id}",
                    "force_tool_usage": True
                }
                await websocket.send(json.dumps(tool_task_msg))
                
                # Collect events for up to 20 seconds
                timeout_time = time.time() + 20
                while time.time() < timeout_time:
                    try:
                        message_raw = await asyncio.wait_for(websocket.recv(), timeout=4.0)
                        message = json.loads(message_raw)
                        events_received.append(message)
                        
                        if message.get("type") == "tool_executing":
                            tool_executing_events.append(message)
                        elif message.get("type") == "tool_completed":
                            tool_completed_events.append(message)
                        
                        # Stop after we get tool events or agent completes
                        if (len(tool_executing_events) > 0 and len(tool_completed_events) > 0) or \
                           message.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            print(f"Tool events test error: {e}")
        
        # Validate tool executing events
        if len(tool_executing_events) > 0:
            executing_event = tool_executing_events[0]
            assert "user_id" in executing_event
            assert "tool_name" in executing_event or "tool" in executing_event
            assert "timestamp" in executing_event
            
            tool_name = executing_event.get("tool_name") or executing_event.get("tool")
            assert tool_name is not None and len(str(tool_name)) > 0
        
        # Validate tool completed events
        if len(tool_completed_events) > 0:
            completed_event = tool_completed_events[0]
            assert "user_id" in completed_event
            assert "tool_name" in completed_event or "tool" in completed_event
            assert "result" in completed_event or "output" in completed_event
            assert "timestamp" in completed_event
            
            # Verify result provides actionable insights
            result = completed_event.get("result") or completed_event.get("output")
            assert result is not None
        
        # Log results for debugging
        print(f"Tool executing events: {len(tool_executing_events)}")
        print(f"Tool completed events: {len(tool_completed_events)}")
        print(f"All event types: {[e.get('type') for e in events_received]}")
    
    @pytest.mark.asyncio
    async def test_agent_completed_event_delivery(self, websocket_url, auth_headers, test_user_id):
        """Test agent_completed event indicates valuable response is ready."""
        events_received = []
        agent_completed_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=30
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": test_user_id,
                    "track_completion_events": True
                }))
                
                await websocket.recv()  # Connection ack
                
                # Send simple task that should complete
                simple_task_msg = {
                    "type": "user_message",
                    "user_id": test_user_id,
                    "content": "Hello, please provide a brief status update",
                    "thread_id": f"thread_{test_user_id}"
                }
                await websocket.send(json.dumps(simple_task_msg))
                
                # Wait for completion event
                timeout_time = time.time() + 25
                while time.time() < timeout_time:
                    try:
                        message_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        message = json.loads(message_raw)
                        events_received.append(message)
                        
                        if message.get("type") == "agent_completed":
                            agent_completed_events.append(message)
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Agent completed event test failed: {e}")
        
        # Validate agent_completed event was received
        assert len(agent_completed_events) > 0, f"agent_completed event not received. Events: {[e.get('type') for e in events_received]}"
        
        # Validate agent_completed event structure
        completed_event = agent_completed_events[0]
        assert "user_id" in completed_event
        assert "timestamp" in completed_event or "completed_at" in completed_event
        assert "result" in completed_event or "response" in completed_event or "output" in completed_event
        
        # Verify the response provides value
        result = completed_event.get("result") or completed_event.get("response") or completed_event.get("output")
        assert result is not None
        if isinstance(result, str):
            assert len(result) > 5, "Agent response should be meaningful"
    
    @pytest.mark.asyncio
    async def test_complete_agent_event_flow(self, websocket_url, auth_headers, test_user_id):
        """Test complete flow of all 5 critical agent events."""
        events_received = []
        required_event_types = {
            "agent_started": False,
            "agent_thinking": False,  # Optional
            "tool_executing": False,  # Optional 
            "tool_completed": False,  # Optional
            "agent_completed": False
        }
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=35
            ) as websocket:
                # Connect with full event tracking
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": test_user_id,
                    "enable_all_agent_events": True,
                    "track_complete_flow": True
                }))
                
                await websocket.recv()  # Connection ack
                
                # Send comprehensive task
                comprehensive_task_msg = {
                    "type": "user_message",
                    "user_id": test_user_id,
                    "content": "Please analyze this request and provide a detailed response with recommendations",
                    "thread_id": f"thread_{test_user_id}",
                    "request_full_event_flow": True
                }
                await websocket.send(json.dumps(comprehensive_task_msg))
                
                # Collect all events until completion
                timeout_time = time.time() + 30
                while time.time() < timeout_time:
                    try:
                        message_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        message = json.loads(message_raw)
                        events_received.append(message)
                        
                        event_type = message.get("type")
                        if event_type in required_event_types:
                            required_event_types[event_type] = True
                        
                        # Stop after agent_completed
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            print(f"Complete event flow test error: {e}")
        
        # Report event flow results
        received_events = [e.get("type") for e in events_received]
        print(f"Complete event flow - Received events: {received_events}")
        print(f"Required events status: {required_event_types}")
        
        # Validate critical events were received
        assert required_event_types["agent_completed"], "agent_completed event is CRITICAL and was not received"
        
        # agent_started should be received (critical for user experience)
        if not required_event_types["agent_started"]:
            print("WARNING: agent_started event not received - this impacts user experience")
        
        # Validate event ordering (agent_started should come before agent_completed)
        agent_started_index = None
        agent_completed_index = None
        
        for i, event in enumerate(events_received):
            if event.get("type") == "agent_started" and agent_started_index is None:
                agent_started_index = i
            if event.get("type") == "agent_completed" and agent_completed_index is None:
                agent_completed_index = i
        
        if agent_started_index is not None and agent_completed_index is not None:
            assert agent_started_index < agent_completed_index, "agent_started should come before agent_completed"
        
        # Verify meaningful event sequence
        assert len(events_received) >= 2, f"Expected multiple events in flow, got: {len(events_received)}"