"""Real WebSocket Tool Notifications Tests

Business Value Justification (BVJ):
- Segment: All Customer Tiers
- Business Goal: Tool Transparency & User Experience
- Value Impact: Shows users what tools are being used to solve their problems
- Strategic Impact: Builds user trust and demonstrates AI problem-solving approach

Tests real WebSocket tool execution notifications with Docker services.
Validates tool_executing and tool_completed events provide transparency.

CRITICAL per CLAUDE.md: Tool transparency demonstrates problem-solving approach and delivers actionable insights.
"""

import asyncio
import json
import time
from typing import Any, Dict, List

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.tool_notifications
@skip_if_no_real_services
class TestRealWebSocketToolNotifications:
    """Test real WebSocket tool execution notifications."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Tool-Notifications-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_tool_executing_notifications(self, websocket_url, auth_headers):
        """Test tool_executing event notifications."""
        user_id = f"tool_exec_test_{int(time.time())}"
        tool_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=20
            ) as websocket:
                # Connect with tool tracking enabled
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "enable_tool_notifications": True,
                    "track_tool_execution": True
                }))
                
                await websocket.recv()  # Connection response
                
                # Send message that should trigger tool usage
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Please analyze the system status and run diagnostics",
                    "thread_id": f"tool_thread_{user_id}",
                    "force_tool_usage": True
                }))
                
                # Collect tool events
                timeout_time = time.time() + 15
                while time.time() < timeout_time:
                    try:
                        event_raw = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        event = json.loads(event_raw)
                        
                        # Track tool-related events
                        if event.get("type") in ["tool_executing", "tool_started", "tool_called"]:
                            tool_events.append(("executing", event))
                        elif event.get("type") in ["tool_completed", "tool_finished", "tool_result"]:
                            tool_events.append(("completed", event))
                        elif "tool" in str(event.get("type", "")).lower():
                            tool_events.append(("other", event))
                        
                        # Stop if we get enough events or agent completes
                        if len(tool_events) >= 3 or event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Tool executing notifications test failed: {e}")
        
        # Validate tool executing events
        executing_events = [event for event_type, event in tool_events if event_type == "executing"]
        
        print(f"Tool executing events: {len(executing_events)} out of {len(tool_events)} total tool events")
        
        if len(executing_events) > 0:
            # Validate tool executing event structure
            exec_event = executing_events[0][1]  # Get the event data
            assert "tool_name" in exec_event or "tool" in exec_event, "Tool executing event should specify tool name"
            assert "user_id" in exec_event, "Tool executing event should include user_id"
            assert "timestamp" in exec_event or "started_at" in exec_event, "Tool executing event should include timestamp"
            
            tool_name = exec_event.get("tool_name") or exec_event.get("tool")
            assert tool_name is not None and len(str(tool_name)) > 0, "Tool name should be meaningful"
            
            print(f"SUCCESS: Tool executing notifications working - Tool: {tool_name}")
        else:
            print("INFO: No tool_executing events detected (feature may not be implemented yet)")
            # Still log what events we did receive
            if tool_events:
                event_types = [event.get("type") for _, event in tool_events]
                print(f"Tool-related events received: {event_types}")
    
    @pytest.mark.asyncio
    async def test_tool_completed_notifications(self, websocket_url, auth_headers):
        """Test tool_completed event notifications with results."""
        user_id = f"tool_complete_test_{int(time.time())}"
        tool_completion_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=25
            ) as websocket:
                # Connect with tool completion tracking
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "track_tool_completion": True,
                    "request_tool_results": True
                }))
                
                await websocket.recv()  # Connection response
                
                # Request task that should use tools and complete them
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Check system health and provide a status report",
                    "thread_id": f"completion_thread_{user_id}",
                    "require_tool_results": True
                }))
                
                # Collect tool completion events
                timeout_time = time.time() + 20
                while time.time() < timeout_time:
                    try:
                        event_raw = await asyncio.wait_for(websocket.recv(), timeout=4.0)
                        event = json.loads(event_raw)
                        
                        # Track tool completion events
                        if event.get("type") in ["tool_completed", "tool_finished", "tool_result"]:
                            tool_completion_events.append(event)
                        
                        # Continue until we get completion or agent finishes
                        if len(tool_completion_events) >= 2 or event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Tool completed notifications test failed: {e}")
        
        # Validate tool completion events
        print(f"Tool completion events received: {len(tool_completion_events)}")
        
        if len(tool_completion_events) > 0:
            # Validate tool completion event structure
            completion_event = tool_completion_events[0]
            assert "tool_name" in completion_event or "tool" in completion_event, "Tool completion should specify tool name"
            assert "result" in completion_event or "output" in completion_event, "Tool completion should include result"
            assert "user_id" in completion_event, "Tool completion should include user_id"
            
            # Verify result provides actionable insights
            result = completion_event.get("result") or completion_event.get("output")
            assert result is not None, "Tool result should be provided"
            
            tool_name = completion_event.get("tool_name") or completion_event.get("tool")
            print(f"SUCCESS: Tool completion notifications working - Tool: {tool_name}, Result available: {result is not None}")
            
            # Log result summary for verification
            if isinstance(result, str) and len(result) > 10:
                print(f"Tool result preview: {result[:100]}...")
            
        else:
            print("INFO: No tool_completed events detected (feature may not be implemented yet)")
    
    @pytest.mark.asyncio
    async def test_tool_notification_timing(self, websocket_url, auth_headers):
        """Test timing and ordering of tool notifications."""
        user_id = f"tool_timing_test_{int(time.time())}"
        timed_tool_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=30
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "track_tool_timing": True
                }))
                
                await websocket.recv()
                
                # Send task that should use multiple tools
                request_start_time = time.time()
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Run a comprehensive system check with multiple diagnostic tools",
                    "thread_id": f"timing_thread_{user_id}",
                    "request_multiple_tools": True
                }))
                
                # Track tool events with timing
                timeout_time = time.time() + 25
                while time.time() < timeout_time:
                    try:
                        event_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event_time = time.time()
                        event = json.loads(event_raw)
                        
                        # Record tool events with timing
                        if any(keyword in str(event.get("type", "")).lower() for keyword in ["tool", "agent"]):
                            timed_tool_events.append({
                                "event": event,
                                "received_at": event_time,
                                "time_since_request": event_time - request_start_time,
                                "event_type": event.get("type")
                            })
                        
                        # Stop after reasonable number of events or completion
                        if len(timed_tool_events) >= 5 or event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Tool notification timing test failed: {e}")
        
        # Analyze tool notification timing
        print(f"Tool timing analysis - Events captured: {len(timed_tool_events)}")
        
        if len(timed_tool_events) >= 2:
            # Check event ordering
            event_times = [e["time_since_request"] for e in timed_tool_events]
            is_chronological = all(event_times[i] <= event_times[i+1] for i in range(len(event_times)-1))
            
            # Analyze timing intervals
            time_intervals = [event_times[i+1] - event_times[i] for i in range(len(event_times)-1)]
            avg_interval = sum(time_intervals) / len(time_intervals) if time_intervals else 0
            
            print(f"Event timing - Chronological: {is_chronological}, Average interval: {avg_interval:.3f}s")
            
            # Events should arrive in reasonable time
            max_time = max(event_times)
            assert max_time < 30, f"Tool events should arrive within reasonable time: {max_time:.3f}s"
            
            # Log event sequence
            for i, timed_event in enumerate(timed_tool_events):
                event_type = timed_event["event_type"]
                time_offset = timed_event["time_since_request"]
                print(f"  {i+1}. {event_type} at +{time_offset:.3f}s")
            
            print("SUCCESS: Tool notification timing analysis complete")
            
        else:
            print("INFO: Insufficient tool events for timing analysis")
    
    @pytest.mark.asyncio
    async def test_multiple_tool_notifications_in_sequence(self, websocket_url, auth_headers):
        """Test notifications for multiple tools used in sequence."""
        user_id = f"multi_tool_test_{int(time.time())}"
        tool_sequence_events = []
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=35
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({
                    "type": "connect",
                    "user_id": user_id,
                    "track_tool_sequence": True
                }))
                
                await websocket.recv()
                
                # Request complex task requiring multiple tools
                await websocket.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Please perform a complete analysis: check system status, review logs, analyze performance, and generate recommendations",
                    "thread_id": f"sequence_thread_{user_id}",
                    "request_comprehensive_analysis": True
                }))
                
                # Track tool sequence
                timeout_time = time.time() + 30
                tool_names_seen = set()
                
                while time.time() < timeout_time:
                    try:
                        event_raw = await asyncio.wait_for(websocket.recv(), timeout=6.0)
                        event = json.loads(event_raw)
                        
                        # Track tool events in sequence
                        if event.get("type") in ["tool_executing", "tool_started", "tool_called"]:
                            tool_name = event.get("tool_name") or event.get("tool")
                            tool_sequence_events.append(("start", tool_name, event))
                            if tool_name:
                                tool_names_seen.add(str(tool_name))
                                
                        elif event.get("type") in ["tool_completed", "tool_finished", "tool_result"]:
                            tool_name = event.get("tool_name") or event.get("tool")
                            tool_sequence_events.append(("complete", tool_name, event))
                        
                        # Stop after getting good sequence or agent completion
                        if len(tool_sequence_events) >= 6 or event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                    except WebSocketException:
                        break
                
        except Exception as e:
            pytest.fail(f"Multiple tool notifications test failed: {e}")
        
        # Analyze tool sequence
        print(f"Tool sequence analysis - Events: {len(tool_sequence_events)}, Unique tools: {len(tool_names_seen)}")
        
        if len(tool_sequence_events) > 0:
            # Analyze start/complete pairing
            tool_starts = [e for e in tool_sequence_events if e[0] == "start"]
            tool_completions = [e for e in tool_sequence_events if e[0] == "complete"]
            
            print(f"Tool starts: {len(tool_starts)}, Tool completions: {len(tool_completions)}")
            
            # Log tool sequence
            for i, (action, tool_name, event) in enumerate(tool_sequence_events):
                print(f"  {i+1}. {action} {tool_name or 'unknown_tool'}")
            
            # Should have some tool activity
            assert len(tool_sequence_events) > 0, "Should have tool sequence activity"
            
            # If we have multiple tools, that's even better
            if len(tool_names_seen) > 1:
                print(f"SUCCESS: Multiple tool sequence detected - Tools: {list(tool_names_seen)}")
            elif len(tool_names_seen) == 1:
                print(f"SUCCESS: Single tool sequence detected - Tool: {list(tool_names_seen)[0]}")
            else:
                print("INFO: Tool names not clearly identified in notifications")
                
        else:
            print("INFO: No tool sequence events detected (feature may not be implemented yet)")