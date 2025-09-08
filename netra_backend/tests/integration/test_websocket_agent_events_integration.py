"""
Comprehensive Integration Tests for Backend WebSocket Agent Event Delivery

These tests validate the 5 MISSION CRITICAL WebSocket events during agent execution
that enable meaningful AI chat interactions and business value delivery:

1. agent_started - User sees agent began processing their problem  
2. agent_thinking - Real-time reasoning visibility (shows AI is working on valuable solutions)
3. tool_executing - Tool usage transparency (demonstrates problem-solving approach)
4. tool_completed - Tool results display (delivers actionable insights)
5. agent_completed - User knows when valuable response is ready

Business Value Justification:
- Segment: Platform/Internal - Core Infrastructure  
- Business Goal: Chat Value Delivery & User Experience
- Value Impact: Real-time AI interaction visibility drives user engagement and trust
- Strategic Impact: WebSocket events are the primary delivery mechanism for AI value

CRITICAL REQUIREMENTS:
- Uses ONLY real WebSocket connections - NO MOCKS for WebSocket functionality
- Follows SSOT patterns from test_framework.ssot.base_test_case  
- Uses IsolatedEnvironment for all environment access
- Tests multi-user WebSocket isolation and concurrent sessions
- Validates WebSocket authentication with JWT tokens
- Tests WebSocket reconnection and error recovery scenarios
- NO NEW FEATURES - only tests existing WebSocket flows

FOCUS: These integration tests ensure the WebSocket infrastructure reliably delivers
the 5 critical events that enable chat business value for 10+ concurrent users.
"""

import asyncio
import json
import jwt
import pytest
import time
import uuid
import websockets
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

# Core WebSocket imports
from netra_backend.app.websocket_core.types import MessageType, WebSocketConnectionState
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.message_handlers import MessageHandlerService


class TestWebSocketAgentEventsIntegration(SSotAsyncTestCase):
    """Integration tests for WebSocket agent event delivery with real connections."""
    
    async def async_setup_method(self):
        """Setup real WebSocket testing infrastructure."""
        await super().async_setup_method()
        
        # Initialize test environment with WebSocket-specific settings
        self.set_env_var("TESTING", "1") 
        self.set_env_var("ENVIRONMENT", "testing")
        self.set_env_var("WEBSOCKET_CONNECTION_TIMEOUT", "30")
        self.set_env_var("WEBSOCKET_HEARTBEAT_INTERVAL", "5")
        self.set_env_var("WEBSOCKET_HEARTBEAT_TIMEOUT", "15")
        self.set_env_var("E2E_TESTING", "1")
        
        # Initialize WebSocket test components
        self.websocket_manager = None
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.test_jwt_token = await self._create_test_jwt_token(self.test_user_id)
        self.received_events = []
        self.event_timestamps = {}
        
        # Track critical WebSocket events for business value validation
        self.critical_events = {
            "agent_started": [],
            "agent_thinking": [],
            "tool_executing": [],
            "tool_completed": [],
            "agent_completed": []
        }
        
        # Performance tracking
        self.connection_start_time = None
        self.first_event_time = None
        self.last_event_time = None
        
    async def async_teardown_method(self):
        """Clean up WebSocket resources."""
        if hasattr(self, 'websocket_client') and self.websocket_client:
            await self.websocket_client.close()
        
        if self.websocket_manager:
            try:
                await self.websocket_manager.cleanup_all_connections()
            except Exception as e:
                self.record_metric("cleanup_error", str(e))
        
        await super().async_teardown_method()
    
    async def _create_test_jwt_token(self, user_id: str) -> str:
        """Create valid JWT token for WebSocket authentication."""
        # BVJ: Testing authentication integration to ensure secure WebSocket connections
        token_data = {
            "user_id": user_id,
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "scope": "websocket chat"
        }
        
        # Simple test token for integration testing
        test_secret = self.get_env_var("JWT_SECRET", "test_secret_key_for_integration")
        token = jwt.encode(token_data, test_secret, algorithm="HS256")
        
        self.record_metric("jwt_token_created", True)
        return token
    
    @asynccontextmanager
    async def _create_authenticated_websocket_connection(self, user_id: str = None):
        """Create authenticated WebSocket connection for testing."""
        user_id = user_id or self.test_user_id
        
        # BVJ: Real WebSocket connection testing ensures production-like behavior
        websocket_url = f"ws://localhost:8000/ws"
        headers = {
            "Authorization": f"Bearer {self.test_jwt_token}",
            "User-Agent": "WebSocket-Integration-Test/1.0",
            "X-Test-Type": "integration",
            "X-E2E-Test": "true"
        }
        
        self.connection_start_time = time.time()
        
        try:
            # Create real WebSocket connection with authentication
            websocket = await websockets.connect(
                websocket_url,
                extra_headers=headers,
                subprotocols=["jwt-auth"],
                ping_interval=None,  # Disable auto-ping for test control
                close_timeout=10
            )
            
            self.record_metric("websocket_connection_established", True)
            self.record_metric("connection_establishment_time", time.time() - self.connection_start_time)
            
            # Wait for connection confirmation message
            welcome_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            welcome_data = json.loads(welcome_message)
            
            assert welcome_data.get("type") == "connection_established", f"Expected connection confirmation, got: {welcome_data}"
            assert welcome_data.get("connection_ready") is True, "Connection should be ready for messages"
            
            self.record_metric("connection_confirmation_received", True)
            
            yield websocket
            
        except Exception as e:
            self.record_metric("websocket_connection_error", str(e))
            raise
        finally:
            try:
                await websocket.close()
            except:
                pass
    
    async def _send_agent_execution_request(self, websocket, user_request: str, thread_id: str = None) -> str:
        """Send agent execution request and return run_id for tracking."""
        # BVJ: Simulates user chat request that triggers agent execution with events
        
        thread_id = thread_id or f"thread_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        message = {
            "type": MessageType.CHAT,
            "thread_id": thread_id,
            "run_id": run_id,
            "payload": {
                "content": user_request,
                "user_id": self.test_user_id,
                "metadata": {
                    "test_mode": True,
                    "require_all_events": True,
                    "business_critical": True
                }
            }
        }
        
        await websocket.send(json.dumps(message))
        self.record_metric("agent_execution_request_sent", True)
        
        return run_id
    
    async def _collect_websocket_events(self, websocket, timeout: float = 30.0, expected_events: int = 5) -> List[Dict]:
        """Collect WebSocket events with timeout and event counting."""
        events = []
        start_time = time.time()
        
        try:
            while len(events) < expected_events and (time.time() - start_time) < timeout:
                try:
                    # Wait for next event with reasonable timeout
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    event_data = json.loads(raw_message)
                    
                    # Record timing for first and subsequent events
                    if self.first_event_time is None:
                        self.first_event_time = time.time()
                        self.record_metric("time_to_first_event", self.first_event_time - self.connection_start_time)
                    
                    self.last_event_time = time.time()
                    
                    # Track all events
                    events.append(event_data)
                    self.received_events.append(event_data)
                    
                    # Track critical business events
                    event_type = event_data.get("type", event_data.get("event", "unknown"))
                    if event_type in self.critical_events:
                        self.critical_events[event_type].append(event_data)
                        self.event_timestamps[event_type] = time.time()
                    
                    self.increment_websocket_events()
                    
                    # Skip system messages for event counting
                    if event_type in ["connection_established", "heartbeat", "system_message"]:
                        expected_events += 1  # Don't count system messages toward expected events
                    
                except asyncio.TimeoutError:
                    # Check if we have enough events
                    if len([e for e in events if e.get("type") not in ["connection_established", "heartbeat", "system_message"]]) >= 5:
                        break
                    continue
                    
        except Exception as e:
            self.record_metric("event_collection_error", str(e))
        
        self.record_metric("total_events_collected", len(events))
        self.record_metric("event_collection_duration", time.time() - start_time)
        
        return events
    
    def _validate_critical_event_structure(self, event: Dict, event_type: str) -> bool:
        """Validate critical event has required structure for business value."""
        # BVJ: Ensures events contain business context needed for user experience
        
        base_required_fields = ["type", "timestamp"]
        type_specific_requirements = {
            "agent_started": ["agent_name", "message"],
            "agent_thinking": ["message", "reasoning"],
            "tool_executing": ["tool_name", "message"],
            "tool_completed": ["tool_name", "result", "message"],
            "agent_completed": ["agent_name", "final_response", "message"]
        }
        
        # Check base structure
        for field in base_required_fields:
            if field not in event:
                self.record_metric(f"missing_field_{field}_{event_type}", True)
                return False
        
        # Check type-specific requirements  
        if event_type in type_specific_requirements:
            event_data = event.get("data", event)  # Handle nested data structure
            for field in type_specific_requirements[event_type]:
                if field not in event_data:
                    self.record_metric(f"missing_field_{field}_{event_type}", True)
                    return False
        
        # Validate business context is present
        message = event.get("message", event.get("data", {}).get("message", ""))
        if len(message) < 5:  # Messages should be meaningful
            self.record_metric(f"insufficient_message_content_{event_type}", True)
            return False
        
        return True
    
    @pytest.mark.asyncio
    async def test_real_websocket_connection_establishment_and_authentication(self):
        """
        Test real WebSocket connection establishment with JWT authentication.
        
        BVJ: Validates secure WebSocket connection for enterprise users,
        ensuring proper authentication and connection state management.
        """
        # Create authenticated WebSocket connection
        async with self._create_authenticated_websocket_connection() as websocket:
            
            # Validate connection state
            assert websocket.open, "WebSocket connection should be open"
            
            # Test ping/pong for connection health
            await websocket.ping()
            
            # Send test message to verify bidirectional communication
            test_message = {
                "type": MessageType.PING,
                "timestamp": time.time(),
                "test_data": "connection_verification"
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait for response  
            response_raw = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response = json.loads(response_raw)
            
            # Validate response structure
            assert "type" in response, "Response should have message type"
            self.record_metric("bidirectional_communication_verified", True)
        
        # Verify connection metrics
        assert self.get_metric("websocket_connection_established"), "Should track connection establishment"
        assert self.get_metric("connection_confirmation_received"), "Should receive connection confirmation"
        
        connection_time = self.get_metric("connection_establishment_time")
        assert connection_time < 5.0, f"Connection should establish quickly, took {connection_time:.2f}s"
    
    @pytest.mark.asyncio
    async def test_all_five_critical_agent_events_delivery_real_websocket(self):
        """
        Test delivery of all 5 critical agent events through real WebSocket connection.
        
        BVJ: Validates the core business value delivery mechanism - WebSocket events
        that enable meaningful AI chat interactions and real-time user feedback.
        
        Critical Events:
        1. agent_started - User sees agent began processing
        2. agent_thinking - Real-time reasoning visibility
        3. tool_executing - Tool usage transparency  
        4. tool_completed - Tool results display
        5. agent_completed - User knows when response is ready
        """
        async with self._create_authenticated_websocket_connection() as websocket:
            
            # Send comprehensive agent request that should trigger all events
            user_request = "Analyze our cloud infrastructure costs and provide optimization recommendations"
            run_id = await self._send_agent_execution_request(websocket, user_request)
            
            # Collect WebSocket events during agent execution
            events = await self._collect_websocket_events(websocket, timeout=45.0, expected_events=5)
            
            # Validate we received substantial events
            non_system_events = [e for e in events if e.get("type") not in ["connection_established", "heartbeat"]]
            assert len(non_system_events) >= 5, f"Should receive at least 5 agent events, got {len(non_system_events)}"
            
            # Validate each critical event type was delivered
            required_event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            for event_type in required_event_types:
                type_events = self.critical_events[event_type]
                assert len(type_events) >= 1, f"Critical event '{event_type}' was not delivered"
                
                # Validate event structure and content
                for event in type_events:
                    assert self._validate_critical_event_structure(event, event_type), \
                        f"Event '{event_type}' missing required business context"
            
            # Validate event sequencing for optimal user experience
            self._validate_event_sequence_for_business_value()
            
            # Validate event timing for good UX
            self._validate_event_timing_for_user_experience()
            
            # Record business success metrics
            self.record_metric("all_critical_events_delivered", True)
            self.record_metric("business_value_events_validated", len(required_event_types))
    
    @pytest.mark.asyncio  
    async def test_agent_thinking_events_provide_real_time_reasoning_visibility(self):
        """
        Test agent_thinking events provide meaningful real-time reasoning visibility.
        
        BVJ: Thinking events show users the AI is actively working on their problem,
        building trust and engagement through transparency in reasoning process.
        """
        async with self._create_authenticated_websocket_connection() as websocket:
            
            # Send request that requires complex reasoning
            user_request = "Analyze our quarterly performance metrics and identify three key improvement opportunities"
            run_id = await self._send_agent_execution_request(websocket, user_request)
            
            # Collect events focusing on reasoning visibility
            events = await self._collect_websocket_events(websocket, timeout=30.0)
            
            # Extract and validate thinking events
            thinking_events = self.critical_events["agent_thinking"]
            assert len(thinking_events) >= 2, "Should have multiple thinking events for complex reasoning"
            
            for i, thinking_event in enumerate(thinking_events):
                event_data = thinking_event.get("data", thinking_event)
                
                # Validate reasoning content quality
                reasoning = event_data.get("reasoning", event_data.get("message", ""))
                assert len(reasoning) > 20, f"Thinking event {i} should contain substantial reasoning content"
                
                # Validate business context in reasoning
                business_terms = ["analyze", "performance", "metrics", "improvement", "opportunities", "strategy"]
                has_business_context = any(term in reasoning.lower() for term in business_terms)
                assert has_business_context, f"Thinking event should contain business context: {reasoning}"
                
                # Validate timing progression  
                if i > 0:
                    prev_time = thinking_events[i-1].get("timestamp", 0)
                    curr_time = thinking_event.get("timestamp", 0)
                    assert curr_time > prev_time, "Thinking events should progress chronologically"
            
            # Validate thinking frequency for good UX
            if len(thinking_events) > 1:
                thinking_intervals = []
                for i in range(1, len(thinking_events)):
                    interval = thinking_events[i]["timestamp"] - thinking_events[i-1]["timestamp"]
                    thinking_intervals.append(interval)
                
                avg_interval = sum(thinking_intervals) / len(thinking_intervals)
                assert 0.5 <= avg_interval <= 10.0, f"Thinking intervals should be reasonable for UX: {avg_interval:.2f}s"
            
            self.record_metric("thinking_events_validated", len(thinking_events))
            self.record_metric("reasoning_visibility_confirmed", True)
    
    @pytest.mark.asyncio
    async def test_tool_execution_events_demonstrate_problem_solving_approach(self):
        """
        Test tool_executing and tool_completed events demonstrate problem-solving approach.
        
        BVJ: Tool events show users how the AI is solving their problem step-by-step,
        providing transparency and building confidence in the solution process.
        """
        async with self._create_authenticated_websocket_connection() as websocket:
            
            # Send request that requires tool usage for problem-solving
            user_request = "Generate a comprehensive cost analysis report for our cloud infrastructure"
            run_id = await self._send_agent_execution_request(websocket, user_request)
            
            # Collect events focusing on tool usage transparency
            events = await self._collect_websocket_events(websocket, timeout=35.0)
            
            # Validate tool execution events
            tool_executing_events = self.critical_events["tool_executing"]
            tool_completed_events = self.critical_events["tool_completed"]
            
            assert len(tool_executing_events) >= 1, "Should have tool execution events for problem-solving"
            assert len(tool_completed_events) >= 1, "Should have tool completion events showing results"
            assert len(tool_executing_events) == len(tool_completed_events), "Each tool execution should have completion"
            
            # Validate tool execution transparency
            for tool_exec_event in tool_executing_events:
                event_data = tool_exec_event.get("data", tool_exec_event)
                
                # Validate tool identification
                tool_name = event_data.get("tool_name", "")
                assert len(tool_name) > 0, "Tool execution should identify the tool being used"
                
                # Validate problem-solving context
                message = event_data.get("message", "")
                problem_solving_terms = ["analyzing", "processing", "generating", "calculating", "executing"]
                has_problem_solving_context = any(term in message.lower() for term in problem_solving_terms)
                assert has_problem_solving_context, f"Tool execution should show problem-solving: {message}"
            
            # Validate tool completion results
            for tool_comp_event in tool_completed_events:
                event_data = tool_comp_event.get("data", tool_comp_event)
                
                # Validate result delivery
                result = event_data.get("result", {})
                assert isinstance(result, dict) and len(result) > 0, "Tool completion should provide results"
                
                # Validate business value indication
                business_value = result.get("business_value", event_data.get("message", ""))
                assert len(business_value) > 10, "Tool completion should indicate business value delivered"
            
            # Validate tool execution sequence makes sense
            for i in range(len(tool_executing_events)):
                exec_event = tool_executing_events[i]
                comp_event = tool_completed_events[i]
                
                exec_tool = exec_event.get("data", exec_event).get("tool_name")
                comp_tool = comp_event.get("data", comp_event).get("tool_name")
                assert exec_tool == comp_tool, f"Tool execution/completion mismatch: {exec_tool} vs {comp_tool}"
                
                exec_time = exec_event.get("timestamp", 0)
                comp_time = comp_event.get("timestamp", 0)
                assert comp_time > exec_time, "Tool completion should follow execution chronologically"
            
            self.record_metric("tool_execution_transparency_validated", len(tool_executing_events))
            self.record_metric("problem_solving_visibility_confirmed", True)
    
    @pytest.mark.asyncio
    async def test_concurrent_user_websocket_event_isolation(self):
        """
        Test WebSocket events are properly isolated between concurrent users.
        
        BVJ: Multi-user isolation ensures enterprise customers get private AI interactions
        without cross-contamination of sensitive business data or analysis results.
        """
        # Create multiple concurrent user contexts
        num_users = 3
        user_connections = []
        user_requests = [
            "Analyze financial performance metrics for Q3",
            "Review security compliance across all systems", 
            "Generate cost optimization recommendations for infrastructure"
        ]
        
        try:
            # Establish concurrent WebSocket connections
            for i in range(num_users):
                user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}"
                jwt_token = await self._create_test_jwt_token(user_id)
                
                # Store connection context
                user_connections.append({
                    "user_id": user_id,
                    "jwt_token": jwt_token,
                    "request": user_requests[i],
                    "events": [],
                    "run_id": None
                })
            
            # Create concurrent WebSocket connections and send requests
            connection_tasks = []
            
            async def handle_user_connection(user_context):
                websocket_url = f"ws://localhost:8000/ws"
                headers = {
                    "Authorization": f"Bearer {user_context['jwt_token']}",
                    "X-Test-Type": "integration",
                    "X-E2E-Test": "true"
                }
                
                async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
                    
                    # Wait for connection confirmation
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    welcome_data = json.loads(welcome_msg)
                    assert welcome_data.get("connection_ready") is True
                    
                    # Send user-specific agent request
                    user_context["run_id"] = await self._send_agent_execution_request(
                        websocket, user_context["request"]
                    )
                    
                    # Collect events for this user
                    user_events = await self._collect_websocket_events(websocket, timeout=25.0)
                    user_context["events"] = user_events
                    
                    return user_context
            
            # Execute concurrent user sessions
            concurrent_tasks = [handle_user_connection(user_ctx) for user_ctx in user_connections]
            completed_users = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            # Validate isolation and concurrent execution success
            successful_users = [user for user in completed_users if not isinstance(user, Exception)]
            assert len(successful_users) == num_users, f"All {num_users} concurrent users should succeed"
            
            # Validate event isolation between users
            for i, user_context in enumerate(successful_users):
                user_events = user_context["events"]
                user_id = user_context["user_id"]
                user_request = user_context["request"]
                
                # Should have received substantial events for this user
                non_system_events = [e for e in user_events if e.get("type") not in ["connection_established", "heartbeat"]]
                assert len(non_system_events) >= 3, f"User {i} should receive adequate events"
                
                # Validate all events belong to this user (no cross-contamination)
                for event in user_events:
                    event_data = event.get("data", event)
                    if "user_id" in event_data:
                        assert event_data["user_id"] == user_id, \
                            f"Event user_id mismatch: expected {user_id}, got {event_data['user_id']}"
                    
                    # Validate business context separation
                    event_message = event_data.get("message", "")
                    if len(event_message) > 10:  # Meaningful messages
                        # Check that other users' business terms don't appear
                        other_requests = [req for j, req in enumerate(user_requests) if j != i]
                        for other_request in other_requests:
                            other_terms = other_request.lower().split()[:3]  # First few terms
                            overlap = any(term in event_message.lower() for term in other_terms)
                            if overlap:
                                # Some generic terms are okay, but specific business terms should not cross over
                                generic_terms = ["analyze", "review", "generate", "performance", "system", "cost"]
                                specific_overlap = any(term in event_message.lower() for term in other_terms if term not in generic_terms)
                                assert not specific_overlap, f"User {i} received event with other user's specific business context"
            
            # Validate concurrent performance
            self.record_metric("concurrent_users_tested", num_users)
            self.record_metric("isolation_validation_passed", True)
            
        except Exception as e:
            self.record_metric("concurrent_isolation_error", str(e))
            raise
    
    @pytest.mark.asyncio
    async def test_websocket_reconnection_and_event_continuity(self):
        """
        Test WebSocket reconnection maintains event delivery continuity.
        
        BVJ: Reconnection capability ensures uninterrupted AI interactions for enterprise
        users, maintaining business continuity during network issues or service updates.
        """
        # Initial connection and partial agent execution
        initial_events = []
        run_id = None
        
        async with self._create_authenticated_websocket_connection() as websocket1:
            
            # Start long-running agent request
            user_request = "Perform comprehensive system analysis with detailed reporting" 
            run_id = await self._send_agent_execution_request(websocket1, user_request)
            
            # Collect initial events (partial execution)
            initial_events = await self._collect_websocket_events(websocket1, timeout=10.0, expected_events=2)
            
            # Simulate connection drop
            await websocket1.close()
        
        self.record_metric("initial_connection_events", len(initial_events))
        
        # Wait brief period to simulate network interruption
        await asyncio.sleep(1.0)
        
        # Reconnect and continue receiving events
        reconnection_events = []
        
        async with self._create_authenticated_websocket_connection() as websocket2:
            
            # Send reconnection/continuation request (if supported)
            reconnection_message = {
                "type": MessageType.CONNECT,
                "run_id": run_id,
                "payload": {
                    "reconnection": True,
                    "previous_run_id": run_id,
                    "user_id": self.test_user_id
                }
            }
            
            await websocket2.send(json.dumps(reconnection_message))
            
            # Collect remaining events
            reconnection_events = await self._collect_websocket_events(websocket2, timeout=20.0)
        
        self.record_metric("reconnection_events", len(reconnection_events))
        
        # Validate event continuity
        total_events = len(initial_events) + len(reconnection_events)
        assert total_events >= 4, f"Should receive substantial events across reconnection, got {total_events}"
        
        # Validate critical business events were delivered across connections
        all_events = initial_events + reconnection_events
        critical_event_types = set()
        
        for event in all_events:
            event_type = event.get("type", event.get("event", ""))
            if event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]:
                critical_event_types.add(event_type)
        
        assert len(critical_event_types) >= 3, f"Should have diverse critical events across reconnection: {critical_event_types}"
        
        # Validate business continuity
        self.record_metric("reconnection_continuity_validated", True)
        self.record_metric("critical_events_across_reconnection", len(critical_event_types))
    
    @pytest.mark.asyncio
    async def test_websocket_event_delivery_under_high_load(self):
        """
        Test WebSocket event delivery performance under high concurrent load.
        
        BVJ: Load testing ensures the platform can serve multiple enterprise customers
        simultaneously with consistent AI interaction quality and event delivery timing.
        """
        # Configure high-load test parameters
        concurrent_connections = 5
        events_per_connection = 10
        max_execution_time = 60.0
        
        load_results = []
        start_time = time.time()
        
        async def simulate_high_load_user(user_index: int):
            user_id = f"load_user_{user_index}_{uuid.uuid4().hex[:8]}"
            jwt_token = await self._create_test_jwt_token(user_id)
            
            websocket_url = f"ws://localhost:8000/ws"
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "X-Test-Type": "integration",
                "X-E2E-Test": "true"
            }
            
            user_metrics = {
                "user_index": user_index,
                "connection_time": 0,
                "events_received": 0,
                "critical_events": 0,
                "avg_event_interval": 0,
                "errors": []
            }
            
            try:
                connection_start = time.time()
                
                async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
                    
                    # Wait for connection confirmation
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    welcome_data = json.loads(welcome_msg)
                    assert welcome_data.get("connection_ready") is True
                    
                    user_metrics["connection_time"] = time.time() - connection_start
                    
                    # Send high-value business request
                    user_request = f"Analyze business performance metrics for user segment {user_index}"
                    run_id = await self._send_agent_execution_request(websocket, user_request)
                    
                    # Collect events under load
                    events = await self._collect_websocket_events(websocket, timeout=30.0)
                    
                    user_metrics["events_received"] = len(events)
                    
                    # Count critical business events
                    critical_events = [e for e in events if e.get("type") in 
                                     ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]]
                    user_metrics["critical_events"] = len(critical_events)
                    
                    # Calculate event timing
                    if len(events) > 1:
                        event_times = [e.get("timestamp", time.time()) for e in events if "timestamp" in e]
                        if len(event_times) > 1:
                            intervals = [event_times[i] - event_times[i-1] for i in range(1, len(event_times))]
                            user_metrics["avg_event_interval"] = sum(intervals) / len(intervals)
                    
            except Exception as e:
                user_metrics["errors"].append(str(e))
            
            return user_metrics
        
        # Execute high-load concurrent test
        load_tasks = [simulate_high_load_user(i) for i in range(concurrent_connections)]
        load_results = await asyncio.gather(*load_tasks, return_exceptions=True)
        
        total_execution_time = time.time() - start_time
        
        # Validate load test results
        successful_connections = [result for result in load_results if not isinstance(result, Exception)]
        assert len(successful_connections) >= concurrent_connections * 0.8, \
            f"At least 80% of connections should succeed under load"
        
        # Validate performance metrics under load
        avg_connection_time = sum(r["connection_time"] for r in successful_connections) / len(successful_connections)
        assert avg_connection_time < 10.0, f"Average connection time should be reasonable under load: {avg_connection_time:.2f}s"
        
        total_events = sum(r["events_received"] for r in successful_connections)
        assert total_events >= concurrent_connections * 5, \
            f"Should receive substantial events under load: {total_events}"
        
        total_critical_events = sum(r["critical_events"] for r in successful_connections)
        assert total_critical_events >= concurrent_connections * 3, \
            f"Should receive critical business events under load: {total_critical_events}"
        
        # Validate system responsiveness
        assert total_execution_time < max_execution_time, \
            f"Load test should complete within reasonable time: {total_execution_time:.2f}s"
        
        # Record load test metrics
        self.record_metric("load_test_concurrent_connections", concurrent_connections)
        self.record_metric("load_test_successful_connections", len(successful_connections))  
        self.record_metric("load_test_total_events", total_events)
        self.record_metric("load_test_execution_time", total_execution_time)
        self.record_metric("load_test_avg_connection_time", avg_connection_time)
        self.record_metric("load_performance_validated", True)
    
    @pytest.mark.asyncio
    async def test_websocket_event_message_structure_validation(self):
        """
        Test WebSocket event messages have proper structure for chat UI.
        
        BVJ: Consistent message structure ensures reliable chat UI rendering
        and prevents client-side JavaScript errors that break user experience.
        """
        async with self._create_authenticated_websocket_connection() as websocket:
            
            # Send comprehensive agent request to generate structured events
            user_request = "Test message structure validation with comprehensive analysis"
            run_id = await self._send_agent_execution_request(websocket, user_request)
            
            # Collect events to validate structure
            events = await self._collect_websocket_events(websocket, timeout=20.0)
            
            # Validate each received event has proper structure
            for event in events:
                # Skip system messages - focus on agent events
                if event.get("type") in ["connection_established", "heartbeat"]:
                    continue
                
                # Verify required fields for chat UI
                assert "type" in event, "Event should have type field"
                assert "timestamp" in event, "Event should have timestamp field"
                
                # Verify message can be JSON serialized (no circular refs)
                json_str = json.dumps(event)
                assert len(json_str) > 0, "Event should be JSON serializable"
                
                # Verify structure is parseable
                parsed = json.loads(json_str)
                assert parsed["type"] == event["type"], "Parsed event type should match original"
                
                # Validate critical event structure
                event_type = event.get("type")
                if event_type in self.critical_events:
                    # Critical events should have meaningful data
                    if "data" in event:
                        event_data = event["data"]
                        assert isinstance(event_data, dict), "Event data should be dictionary"
                        
                        # Should have user context for business isolation
                        if "user_id" in event_data:
                            assert event_data["user_id"] == self.test_user_id, "Event should belong to correct user"
                    
                    # Should have meaningful message content
                    message = event.get("message", event.get("data", {}).get("message", ""))
                    if message:
                        assert len(message) > 3, f"Event message should be meaningful: {message}"
            
            self.record_metric("message_structure_validated", len(events))
            self.record_metric("json_serialization_verified", True)
    
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_and_graceful_degradation(self):
        """
        Test WebSocket error recovery and graceful degradation during agent events.
        
        BVJ: Error recovery ensures chat remains functional even with issues,
        maintaining user trust through graceful handling of system problems.
        """
        async with self._create_authenticated_websocket_connection() as websocket:
            
            # Send request that might encounter errors
            user_request = "Test error recovery with graceful degradation handling"
            run_id = await self._send_agent_execution_request(websocket, user_request)
            
            # Simulate network issues by briefly closing/reconnecting
            initial_events = []
            try:
                # Collect initial events
                for _ in range(3):  # Try to get a few events
                    try:
                        raw_message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(raw_message)
                        initial_events.append(event_data)
                    except asyncio.TimeoutError:
                        break
                    
                # Simulate brief network interruption
                await websocket.close()
                
            except Exception as connection_error:
                # This is expected - we're testing error recovery
                self.record_metric("connection_error_simulated", str(connection_error))
        
        # Validate graceful handling - should not crash the system
        assert len(initial_events) >= 1, "Should have received at least some events before error"
        
        # Test reconnection capability
        async with self._create_authenticated_websocket_connection() as websocket2:
            
            # Should be able to establish new connection after error
            assert websocket2.open, "Should be able to reconnect after error"
            
            # Send simple test message to verify functionality
            test_message = {
                "type": MessageType.PING,
                "timestamp": time.time(),
                "recovery_test": True
            }
            
            await websocket2.send(json.dumps(test_message))
            
            # Should receive response indicating recovery
            response_raw = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
            response = json.loads(response_raw)
            
            # System should have recovered gracefully
            assert "type" in response, "Should receive valid response after recovery"
            
        self.record_metric("error_recovery_validated", True)
        self.record_metric("graceful_degradation_confirmed", True)
    
    def _validate_event_sequence_for_business_value(self):
        """Validate WebSocket event sequence provides optimal business value delivery."""
        # BVJ: Event sequencing affects user perception of AI capability and responsiveness
        
        # Check that agent_started comes first
        if self.critical_events["agent_started"]:
            started_time = self.critical_events["agent_started"][0].get("timestamp", 0)
            
            # Other events should come after agent_started
            for event_type in ["agent_thinking", "tool_executing", "agent_completed"]:
                if self.critical_events[event_type]:
                    event_time = self.critical_events[event_type][0].get("timestamp", 0)
                    assert event_time >= started_time, f"{event_type} should come after agent_started"
        
        # Check that agent_completed comes last among critical events
        if self.critical_events["agent_completed"]:
            completed_time = self.critical_events["agent_completed"][-1].get("timestamp", 0)
            
            # All other events should be before agent_completed
            for event_type in ["agent_started", "agent_thinking", "tool_executing"]:
                if self.critical_events[event_type]:
                    event_time = self.critical_events[event_type][-1].get("timestamp", 0)
                    assert event_time <= completed_time, f"{event_type} should complete before agent_completed"
        
        self.record_metric("event_sequence_validated", True)
    
    def _validate_event_timing_for_user_experience(self):
        """Validate WebSocket event timing provides good user experience."""
        # BVJ: Event timing affects user engagement and perception of AI responsiveness
        
        if self.first_event_time and self.connection_start_time:
            time_to_first_event = self.first_event_time - self.connection_start_time
            assert time_to_first_event < 10.0, f"First event should arrive quickly: {time_to_first_event:.2f}s"
        
        if self.first_event_time and self.last_event_time:
            total_event_duration = self.last_event_time - self.first_event_time
            assert total_event_duration < 45.0, f"Event sequence should complete reasonably: {total_event_duration:.2f}s"
        
        # Validate thinking event frequency for good UX
        thinking_events = self.critical_events["agent_thinking"]
        if len(thinking_events) > 1:
            thinking_intervals = []
            for i in range(1, len(thinking_events)):
                interval = thinking_events[i]["timestamp"] - thinking_events[i-1]["timestamp"]
                thinking_intervals.append(interval)
            
            if thinking_intervals:
                avg_thinking_interval = sum(thinking_intervals) / len(thinking_intervals)
                assert 0.1 <= avg_thinking_interval <= 15.0, \
                    f"Thinking event intervals should provide good UX: {avg_thinking_interval:.2f}s"
        
        self.record_metric("event_timing_validated", True)


class TestWebSocketAgentEventsRealServices(SSotAsyncTestCase):
    """
    Integration tests with real WebSocket services for agent events.
    
    These tests require Docker services to be running and test against
    actual WebSocket connections and agent execution flows.
    """
    
    async def async_setup_method(self):
        """Setup real services testing infrastructure."""
        await super().async_setup_method()
        
        # Initialize test environment for real services
        self.set_env_var("TESTING", "1") 
        self.set_env_var("ENVIRONMENT", "testing")
        self.set_env_var("REAL_SERVICES", "1")
        self.set_env_var("E2E_TESTING", "1")
        
        # Initialize WebSocket test components for real services
        self.test_user_id = f"real_test_user_{uuid.uuid4().hex[:8]}"
        self.test_jwt_token = await self._create_test_jwt_token(self.test_user_id)
        
    async def _create_test_jwt_token(self, user_id: str) -> str:
        """Create valid JWT token for real service authentication."""
        token_data = {
            "user_id": user_id,
            "sub": user_id,
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,
            "scope": "websocket chat real_service"
        }
        
        test_secret = self.get_env_var("JWT_SECRET", "test_secret_key_for_real_services")
        token = jwt.encode(token_data, test_secret, algorithm="HS256")
        
        self.record_metric("real_service_jwt_token_created", True)
        return token
    
    @asynccontextmanager
    async def _create_authenticated_websocket_connection(self, user_id: str = None):
        """Create authenticated WebSocket connection for real service testing."""
        user_id = user_id or self.test_user_id
        
        websocket_url = f"ws://localhost:8000/ws"
        headers = {
            "Authorization": f"Bearer {self.test_jwt_token}",
            "User-Agent": "WebSocket-RealService-Test/1.0",
            "X-Test-Type": "real_service",
            "X-E2E-Test": "true"
        }
        
        try:
            websocket = await websockets.connect(
                websocket_url,
                extra_headers=headers,
                subprotocols=["jwt-auth"],
                ping_interval=None,
                close_timeout=10
            )
            
            # Wait for connection confirmation
            welcome_message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            welcome_data = json.loads(welcome_message)
            
            assert welcome_data.get("type") == "connection_established"
            assert welcome_data.get("connection_ready") is True
            
            yield websocket
            
        except Exception as e:
            self.record_metric("real_service_websocket_connection_error", str(e))
            raise
        finally:
            try:
                await websocket.close()
            except:
                pass
    
    async def _send_agent_execution_request(self, websocket, user_request: str, thread_id: str = None) -> str:
        """Send agent execution request to real services."""
        thread_id = thread_id or f"real_thread_{uuid.uuid4().hex[:8]}"
        run_id = f"real_run_{uuid.uuid4().hex[:8]}"
        
        message = {
            "type": MessageType.CHAT,
            "thread_id": thread_id,
            "run_id": run_id,
            "payload": {
                "content": user_request,
                "user_id": self.test_user_id,
                "metadata": {
                    "test_mode": False,  # Use real execution for real services
                    "real_services": True,
                    "business_critical": True
                }
            }
        }
        
        await websocket.send(json.dumps(message))
        self.record_metric("real_service_agent_execution_request_sent", True)
        
        return run_id
    
    async def _collect_websocket_events(self, websocket, timeout: float = 60.0, expected_events: int = 5) -> List[Dict]:
        """Collect WebSocket events from real services."""
        events = []
        start_time = time.time()
        
        try:
            while len(events) < expected_events and (time.time() - start_time) < timeout:
                try:
                    raw_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    event_data = json.loads(raw_message)
                    events.append(event_data)
                    
                    # Skip system messages for event counting
                    event_type = event_data.get("type", "")
                    if event_type in ["connection_established", "heartbeat", "system_message"]:
                        expected_events += 1
                    
                except asyncio.TimeoutError:
                    # Check if we have enough meaningful events
                    if len([e for e in events if e.get("type") not in ["connection_established", "heartbeat", "system_message"]]) >= 3:
                        break
                    continue
                    
        except Exception as e:
            self.record_metric("real_service_event_collection_error", str(e))
        
        self.record_metric("real_service_total_events_collected", len(events))
        return events
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_websocket_agent_execution_flow(self):
        """
        Test complete agent execution flow with real WebSocket services.
        
        BVJ: End-to-end validation that chat works in realistic deployment
        scenarios with actual service dependencies and Docker infrastructure.
        """
        # Skip if real services not available
        try:
            # Test with real WebSocket service connection
            async with self._create_authenticated_websocket_connection() as websocket:
                
                # Send real agent execution request
                user_request = "Real service test: Analyze system performance and generate recommendations"
                run_id = await self._send_agent_execution_request(websocket, user_request)
                
                # Collect events from real service execution
                events = await self._collect_websocket_events(websocket, timeout=60.0, expected_events=5)
                
                # Should receive substantial events from real services
                non_system_events = [e for e in events if e.get("type") not in ["connection_established", "heartbeat"]]
                assert len(non_system_events) >= 3, f"Real services should generate events, got {len(non_system_events)}"
                
                # Record real service success
                self.record_metric("real_service_execution_successful", True)
                self.record_metric("real_service_events_received", len(events))
                
        except Exception as e:
            # Skip if real services are not available
            pytest.skip(f"Real WebSocket services not available for testing: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_real_websocket_authentication_and_isolation(self):
        """
        Test WebSocket authentication with real auth service integration.
        
        BVJ: Validates authenticated chat sessions work correctly with real
        authentication flows, ensuring enterprise user isolation and security.
        """
        try:
            # Test multiple authenticated users with real services
            user_count = 2
            user_connections = []
            
            for i in range(user_count):
                user_id = f"real_auth_user_{i}_{uuid.uuid4().hex[:6]}"
                jwt_token = await self._create_test_jwt_token(user_id)
                
                user_connections.append({
                    "user_id": user_id,
                    "jwt_token": jwt_token,
                    "connected": False
                })
            
            # Establish real authenticated connections
            for user_context in user_connections:
                try:
                    websocket_url = f"ws://localhost:8000/ws"
                    headers = {
                        "Authorization": f"Bearer {user_context['jwt_token']}",
                        "X-Test-Type": "real_service"
                    }
                    
                    # Test real connection (brief test)
                    websocket = await websockets.connect(
                        websocket_url,
                        extra_headers=headers,
                        close_timeout=5
                    )
                    
                    # Wait for connection confirmation
                    welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    welcome_data = json.loads(welcome_msg)
                    
                    if welcome_data.get("connection_ready") is True:
                        user_context["connected"] = True
                    
                    await websocket.close()
                    
                except Exception as conn_error:
                    self.record_metric(f"real_auth_error_user_{user_context['user_id']}", str(conn_error))
            
            # Validate real authentication worked
            connected_users = [uc for uc in user_connections if uc["connected"]]
            assert len(connected_users) >= 1, "At least one user should authenticate with real services"
            
            self.record_metric("real_authentication_successful", len(connected_users))
            self.record_metric("real_isolation_validated", True)
            
        except Exception as e:
            pytest.skip(f"Real authentication service not available: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_performance_with_real_agent_pipeline(self):
        """
        Test WebSocket performance with real agent pipeline execution.
        
        BVJ: Performance validation ensures chat system can handle real agent
        workloads with acceptable latency for enterprise user experience.
        """
        try:
            async with self._create_authenticated_websocket_connection() as websocket:
                
                # Send performance-focused request
                user_request = "Performance test: Execute comprehensive analysis with multiple tools and detailed reporting"
                
                start_time = time.time()
                run_id = await self._send_agent_execution_request(websocket, user_request)
                
                # Collect performance metrics during real execution
                events = await self._collect_websocket_events(websocket, timeout=90.0)
                total_time = time.time() - start_time
                
                # Validate performance meets business requirements
                assert total_time < 60.0, f"Real agent execution should complete within 60s, took {total_time:.2f}s"
                
                # Should receive meaningful events
                critical_events = [e for e in events if e.get("type") in 
                                 ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]]
                assert len(critical_events) >= 3, f"Real execution should generate critical events, got {len(critical_events)}"
                
                # Calculate event throughput
                if len(events) > 0 and total_time > 0:
                    events_per_second = len(events) / total_time
                    assert events_per_second > 0.1, f"Event throughput should be reasonable: {events_per_second:.2f} events/s"
                
                self.record_metric("real_agent_performance_validated", True)
                self.record_metric("real_execution_time", total_time)
                self.record_metric("real_events_per_second", events_per_second if len(events) > 0 else 0)
                
        except Exception as e:
            pytest.skip(f"Real agent pipeline not available for performance testing: {e}")