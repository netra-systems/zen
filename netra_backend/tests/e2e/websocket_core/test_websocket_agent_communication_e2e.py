"""
Test WebSocket Agent Communication E2E - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Real-time agent communication and user experience
- Value Impact: Enables live agent feedback and responsive user interactions
- Strategic Impact: Core foundation for competitive AI chat experience

CRITICAL REQUIREMENTS:
- Tests real WebSocket connections with authentication
- Validates all 5 critical agent events are sent
- Ensures message delivery and user isolation
- No mocks - uses real WebSocket infrastructure
"""

import asyncio
import pytest
import json
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.websocket import WebSocketTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.websocket_core.handlers import WebSocketHandler
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.agents.agent_registry import get_agent_registry


class TestWebSocketAgentCommunicationE2E(SSotBaseTestCase):
    """
    End-to-end WebSocket agent communication tests.
    
    Tests critical real-time communication that delivers business value:
    - Agent execution with live WebSocket events
    - User isolation in multi-user WebSocket environment
    - Event delivery reliability and ordering
    - Authentication and security in WebSocket context
    - Performance under realistic load
    """
    
    def __init__(self):
        """Initialize WebSocket agent communication test suite."""
        super().__init__()
        self.env = get_env()
        self.websocket_helper = WebSocketTestHelper()
        
        # Test configuration
        self.test_prefix = f"ws_agent_e2e_{uuid.uuid4().hex[:8]}"
        self.websocket_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Critical agent events that MUST be sent
        self.required_agent_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
    
    def setup_websocket_auth(self, user_suffix: str = "default") -> E2EWebSocketAuthHelper:
        """Set up WebSocket authentication helper."""
        return E2EWebSocketAuthHelper(
            environment=self.env.get("TEST_ENV", "test")
        )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_agent_execution_with_websocket_events(self):
        """
        Test complete agent execution with all required WebSocket events.
        
        BUSINESS CRITICAL: Agent events enable real-time user experience.
        Missing events make the system appear unresponsive to users.
        """
        ws_auth = self.setup_websocket_auth("agent_execution")
        
        try:
            # Connect to WebSocket with authentication
            websocket = await ws_auth.connect_authenticated_websocket(timeout=15.0)
            
            # Create test message for agent execution
            test_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Help me understand my system performance",
                "thread_id": f"thread_{uuid.uuid4().hex[:8]}",
                "request_id": f"req_{uuid.uuid4().hex[:8]}"
            }
            
            # Send agent request
            await websocket.send(json.dumps(test_message))
            
            # Collect all events until agent completion
            received_events = []
            agent_completed = False
            timeout_seconds = 30.0
            
            start_time = datetime.now()
            
            while not agent_completed and (datetime.now() - start_time).total_seconds() < timeout_seconds:
                try:
                    # Wait for event with timeout
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    
                    received_events.append({
                        "event": event,
                        "timestamp": datetime.now(),
                        "order": len(received_events)
                    })
                    
                    # Check if agent completed
                    if event.get("type") == "agent_completed":
                        agent_completed = True
                        
                except asyncio.TimeoutError:
                    # No event received in 5 seconds - check if we got completion
                    break
                except json.JSONDecodeError as e:
                    pytest.fail(f"Received invalid JSON from WebSocket: {e}")
            
            # Validate agent execution completed
            assert agent_completed, f"Agent did not complete within {timeout_seconds}s. Events: {[e['event']['type'] for e in received_events]}"
            
            # Extract event types for validation
            event_types = [event["event"]["type"] for event in received_events]
            
            # CRITICAL: Validate all 5 required events were sent
            missing_events = []
            for required_event in self.required_agent_events:
                if required_event not in event_types:
                    missing_events.append(required_event)
            
            assert len(missing_events) == 0, \
                f"CRITICAL: Missing required agent events: {missing_events}. Received: {event_types}"
            
            # Validate event ordering makes sense
            event_order_validation = self._validate_event_ordering(received_events)
            assert event_order_validation.is_valid, \
                f"Event ordering invalid: {event_order_validation.error_message}"
            
            # Validate event data completeness
            for event_record in received_events:
                event = event_record["event"]
                event_type = event.get("type")
                
                # Validate basic event structure
                assert "timestamp" in event, f"Event {event_type} missing timestamp"
                assert "data" in event, f"Event {event_type} missing data field"
                
                # Validate event-specific data
                if event_type == "agent_started":
                    assert "agent_type" in event["data"], "agent_started missing agent_type"
                    assert "request_id" in event["data"], "agent_started missing request_id"
                    
                elif event_type == "agent_thinking":
                    assert "thought_process" in event["data"] or "thinking_status" in event["data"], \
                        "agent_thinking missing thought content"
                        
                elif event_type in ["tool_executing", "tool_completed"]:
                    assert "tool_name" in event["data"], f"{event_type} missing tool_name"
                    
                elif event_type == "agent_completed":
                    assert "result" in event["data"] or "response" in event["data"], \
                        "agent_completed missing result/response"
                    assert "execution_time" in event["data"], "agent_completed missing execution_time"
            
            # Close WebSocket connection
            await websocket.close()
            
        except Exception as e:
            pytest.fail(f"WebSocket agent communication test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_websocket_isolation(self):
        """
        Test user isolation in multi-user WebSocket environment.
        
        BUSINESS CRITICAL: User isolation prevents data leakage between customers.
        One user must never see another user's agent responses.
        """
        # Create two separate authenticated users
        user1_auth = self.setup_websocket_auth("isolation_user1")
        user2_auth = self.setup_websocket_auth("isolation_user2")
        
        try:
            # Connect both users to WebSocket
            user1_ws = await user1_auth.connect_authenticated_websocket(timeout=15.0)
            user2_ws = await user2_auth.connect_authenticated_websocket(timeout=15.0)
            
            # Create distinct messages for each user
            user1_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "User 1 confidential request about financial data",
                "thread_id": f"user1_thread_{uuid.uuid4().hex[:8]}",
                "request_id": f"user1_req_{uuid.uuid4().hex[:8]}",
                "user_context": {"user_id": "user_1_sensitive"}
            }
            
            user2_message = {
                "type": "agent_request", 
                "agent": "triage_agent",
                "message": "User 2 confidential request about customer database",
                "thread_id": f"user2_thread_{uuid.uuid4().hex[:8]}",
                "request_id": f"user2_req_{uuid.uuid4().hex[:8]}",
                "user_context": {"user_id": "user_2_sensitive"}
            }
            
            # Send requests concurrently
            await asyncio.gather(
                user1_ws.send(json.dumps(user1_message)),
                user2_ws.send(json.dumps(user2_message))
            )
            
            # Collect events from both users
            user1_events = []
            user2_events = []
            
            # Event collection with timeout
            collection_timeout = 30.0
            start_time = datetime.now()
            
            both_completed = {"user1": False, "user2": False}
            
            while not all(both_completed.values()) and (datetime.now() - start_time).total_seconds() < collection_timeout:
                # Check for events from both users
                try:
                    # Non-blocking check for user1
                    user1_event_raw = await asyncio.wait_for(user1_ws.recv(), timeout=1.0)
                    user1_event = json.loads(user1_event_raw)
                    user1_events.append(user1_event)
                    
                    if user1_event.get("type") == "agent_completed":
                        both_completed["user1"] = True
                        
                except asyncio.TimeoutError:
                    pass  # No event from user1
                
                try:
                    # Non-blocking check for user2
                    user2_event_raw = await asyncio.wait_for(user2_ws.recv(), timeout=1.0)
                    user2_event = json.loads(user2_event_raw)
                    user2_events.append(user2_event)
                    
                    if user2_event.get("type") == "agent_completed":
                        both_completed["user2"] = True
                        
                except asyncio.TimeoutError:
                    pass  # No event from user2
            
            # Validate both users received responses
            assert both_completed["user1"], f"User 1 did not receive agent completion. Events: {len(user1_events)}"
            assert both_completed["user2"], f"User 2 did not receive agent completion. Events: {len(user2_events)}"
            
            # CRITICAL: Validate no cross-user data leakage
            user1_all_text = " ".join(
                json.dumps(event).lower() for event in user1_events
            )
            user2_all_text = " ".join(
                json.dumps(event).lower() for event in user2_events
            )
            
            # User 1 should not see User 2's data
            user2_sensitive_terms = [
                "user_2_sensitive", "customer database", 
                user2_message["thread_id"], user2_message["request_id"]
            ]
            
            for sensitive_term in user2_sensitive_terms:
                assert sensitive_term.lower() not in user1_all_text, \
                    f"User 1 received User 2's data: '{sensitive_term}' found in User 1's events"
            
            # User 2 should not see User 1's data
            user1_sensitive_terms = [
                "user_1_sensitive", "financial data",
                user1_message["thread_id"], user1_message["request_id"] 
            ]
            
            for sensitive_term in user1_sensitive_terms:
                assert sensitive_term.lower() not in user2_all_text, \
                    f"User 2 received User 1's data: '{sensitive_term}' found in User 2's events"
            
            # Validate each user received their own data correctly
            assert user1_message["thread_id"] in user1_all_text, \
                "User 1 did not receive their own thread data"
            assert user2_message["thread_id"] in user2_all_text, \
                "User 2 did not receive their own thread data"
            
            # Close connections
            await user1_ws.close()
            await user2_ws.close()
            
        except Exception as e:
            pytest.fail(f"Multi-user isolation test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_reliability_and_reconnection(self):
        """
        Test WebSocket reliability and reconnection handling.
        
        BUSINESS CRITICAL: Connection failures must not lose user data.
        System must handle reconnections gracefully without data loss.
        """
        ws_auth = self.setup_websocket_auth("reliability")
        
        try:
            # Initial connection and agent request
            websocket = await ws_auth.connect_authenticated_websocket(timeout=15.0)
            
            initial_message = {
                "type": "agent_request",
                "agent": "data_analyzer",
                "message": "Analyze system performance for reliability test",
                "thread_id": f"reliability_thread_{uuid.uuid4().hex[:8]}",
                "request_id": f"reliability_req_{uuid.uuid4().hex[:8]}"
            }
            
            await websocket.send(json.dumps(initial_message))
            
            # Receive first few events
            initial_events = []
            for _ in range(3):  # Get first 3 events
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    initial_events.append(event)
                except asyncio.TimeoutError:
                    break
            
            # Simulate connection interruption
            await websocket.close(code=1000, reason="Simulated interruption")
            
            # Wait before reconnection
            await asyncio.sleep(2.0)
            
            # Reconnect and continue
            reconnected_websocket = await ws_auth.connect_authenticated_websocket(timeout=15.0)
            
            # Send continuation message or status check
            status_message = {
                "type": "status_check",
                "thread_id": initial_message["thread_id"],
                "request_id": initial_message["request_id"]
            }
            
            await reconnected_websocket.send(json.dumps(status_message))
            
            # Collect remaining events
            remaining_events = []
            agent_completed = False
            
            timeout_start = datetime.now()
            while not agent_completed and (datetime.now() - timeout_start).total_seconds() < 20.0:
                try:
                    event_data = await asyncio.wait_for(reconnected_websocket.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    remaining_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        agent_completed = True
                        
                except asyncio.TimeoutError:
                    break
            
            # Validate reliability
            all_events = initial_events + remaining_events
            all_event_types = [event["type"] for event in all_events]
            
            # Should have received completion despite reconnection
            assert "agent_completed" in all_event_types, \
                f"Agent completion lost during reconnection. Events: {all_event_types}"
            
            # Should not have duplicate events after reconnection
            event_type_counts = {}
            for event_type in all_event_types:
                event_type_counts[event_type] = event_type_counts.get(event_type, 0) + 1
            
            # Critical events should not be excessively duplicated
            for event_type in ["agent_started", "agent_completed"]:
                if event_type in event_type_counts:
                    assert event_type_counts[event_type] <= 2, \
                        f"Event {event_type} duplicated {event_type_counts[event_type]} times after reconnection"
            
            # Validate thread/request consistency
            thread_consistency = True
            request_consistency = True
            
            for event in all_events:
                if "data" in event and isinstance(event["data"], dict):
                    event_thread = event["data"].get("thread_id")
                    event_request = event["data"].get("request_id") 
                    
                    if event_thread and event_thread != initial_message["thread_id"]:
                        thread_consistency = False
                    if event_request and event_request != initial_message["request_id"]:
                        request_consistency = False
            
            assert thread_consistency, "Thread ID inconsistency detected after reconnection"
            assert request_consistency, "Request ID inconsistency detected after reconnection"
            
            await reconnected_websocket.close()
            
        except Exception as e:
            pytest.fail(f"WebSocket reliability test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_websocket_performance_under_load(self):
        """
        Test WebSocket performance under realistic load.
        
        BUSINESS CRITICAL: Poor performance impacts user experience.
        System must handle multiple concurrent users efficiently.
        """
        # Create multiple concurrent users
        concurrent_users = 5
        user_auths = []
        
        for i in range(concurrent_users):
            auth = self.setup_websocket_auth(f"load_user_{i}")
            user_auths.append(auth)
        
        try:
            # Connect all users concurrently
            connection_start = datetime.now()
            websockets_list = await asyncio.gather(*[
                auth.connect_authenticated_websocket(timeout=15.0) 
                for auth in user_auths
            ])
            connection_time = (datetime.now() - connection_start).total_seconds()
            
            # Connection time should be reasonable
            assert connection_time < 10.0, \
                f"Concurrent connections too slow: {connection_time:.2f}s for {concurrent_users} users"
            
            # Create concurrent agent requests
            agent_requests = []
            for i, websocket in enumerate(websockets_list):
                message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Load test request from user {i}",
                    "thread_id": f"load_thread_{i}_{uuid.uuid4().hex[:8]}",
                    "request_id": f"load_req_{i}_{uuid.uuid4().hex[:8]}"
                }
                agent_requests.append((websocket, message))
            
            # Send all requests concurrently
            send_start = datetime.now()
            await asyncio.gather(*[
                ws.send(json.dumps(msg)) for ws, msg in agent_requests
            ])
            send_time = (datetime.now() - send_start).total_seconds()
            
            assert send_time < 5.0, \
                f"Concurrent message sending too slow: {send_time:.2f}s"
            
            # Collect responses from all users
            user_completions = [False] * concurrent_users
            response_times = [None] * concurrent_users
            user_events = [[] for _ in range(concurrent_users)]
            
            collection_start = datetime.now()
            timeout_seconds = 45.0  # Longer timeout for concurrent processing
            
            while not all(user_completions) and (datetime.now() - collection_start).total_seconds() < timeout_seconds:
                
                # Check each user's WebSocket for events
                for user_idx, websocket in enumerate(websockets_list):
                    if user_completions[user_idx]:
                        continue  # Skip completed users
                        
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        event = json.loads(event_data)
                        user_events[user_idx].append(event)
                        
                        if event.get("type") == "agent_completed":
                            user_completions[user_idx] = True
                            response_times[user_idx] = (datetime.now() - collection_start).total_seconds()
                            
                    except asyncio.TimeoutError:
                        continue  # No event from this user
            
            # Validate performance results
            completed_users = sum(user_completions)
            assert completed_users >= int(concurrent_users * 0.8), \
                f"Too many users failed to complete: {completed_users}/{concurrent_users}"
            
            # Validate response times are reasonable
            successful_response_times = [t for t in response_times if t is not None]
            if successful_response_times:
                avg_response_time = sum(successful_response_times) / len(successful_response_times)
                max_response_time = max(successful_response_times)
                
                assert avg_response_time < 30.0, \
                    f"Average response time too slow: {avg_response_time:.2f}s"
                assert max_response_time < 60.0, \
                    f"Maximum response time too slow: {max_response_time:.2f}s"
            
            # Validate all completed users received required events
            for user_idx in range(concurrent_users):
                if user_completions[user_idx]:
                    user_event_types = [e["type"] for e in user_events[user_idx]]
                    
                    # Should have received core events
                    core_events = ["agent_started", "agent_completed"]
                    missing_core = [e for e in core_events if e not in user_event_types]
                    
                    assert len(missing_core) == 0, \
                        f"User {user_idx} missing core events: {missing_core}"
            
            # Close all connections
            await asyncio.gather(*[
                ws.close() for ws in websockets_list
            ], return_exceptions=True)
            
        except Exception as e:
            pytest.fail(f"WebSocket load test failed: {e}")
    
    def _validate_event_ordering(self, received_events: List[Dict[str, Any]]) -> Any:
        """Validate that events are received in logical order."""
        event_types = [event["event"]["type"] for event in received_events]
        
        # Define expected ordering rules
        ordering_rules = [
            ("agent_started should come before agent_thinking", "agent_started", "agent_thinking"),
            ("agent_thinking should come before tool_executing", "agent_thinking", "tool_executing"), 
            ("tool_executing should come before tool_completed", "tool_executing", "tool_completed"),
            ("agent_completed should be last", "agent_completed", None)
        ]
        
        errors = []
        
        for rule_name, first_event, second_event in ordering_rules:
            if second_event is None:
                # Special case: event should be last
                if first_event in event_types:
                    first_idx = event_types.index(first_event)
                    if first_idx != len(event_types) - 1:
                        errors.append(f"{rule_name}: {first_event} not at end (position {first_idx}/{len(event_types)})")
            else:
                # Normal ordering rule
                if first_event in event_types and second_event in event_types:
                    first_idx = event_types.index(first_event)
                    second_idx = event_types.index(second_event)
                    
                    if first_idx >= second_idx:
                        errors.append(f"{rule_name}: {first_event}({first_idx}) should come before {second_event}({second_idx})")
        
        # Return validation result
        class ValidationResult:
            def __init__(self, is_valid: bool, error_message: str = ""):
                self.is_valid = is_valid
                self.error_message = error_message
        
        if errors:
            return ValidationResult(False, "; ".join(errors))
        else:
            return ValidationResult(True)


if __name__ == "__main__":
    # Allow running individual tests
    pytest.main([__file__, "-v", "--tb=short"])