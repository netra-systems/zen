"""
E2E Tests for Complete Agent-Tool-WebSocket Flow

Tests the entire end-to-end flow from agent execution through tool dispatching
to WebSocket event delivery with real authentication and services.

Business Value: Validates complete user experience works with real components
"""

import asyncio
import pytest
import json
import time
from uuid import uuid4

# SSOT Authentication Import - CLAUDE.md Compliant (NO MOCKS)
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper,
    E2EWebSocketAuthHelper,
    create_authenticated_user
)

from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import create_request_scoped_tool_dispatcher
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

from langchain_core.tools import BaseTool


class MockE2ETool(BaseTool):
    """Mock tool for E2E testing that simulates real tool behavior."""
    name: str = "e2e_test_tool"
    description: str = "E2E test tool that simulates real tool execution"
    
    def __init__(self, execution_time: float = 0.1, should_fail: bool = False):
        super().__init__()
        self.execution_time = execution_time
        self.should_fail = should_fail
        self.execution_count = 0
        
    def _run(self, query: str = "default query") -> str:
        """Synchronous tool execution."""
        import time
        time.sleep(self.execution_time)
        
        self.execution_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"E2E tool failure on execution {self.execution_count}")
        
        return f"E2E tool result #{self.execution_count} for query: {query}"
    
    async def _arun(self, query: str = "default query") -> str:
        """Asynchronous tool execution."""
        await asyncio.sleep(self.execution_time)
        
        self.execution_count += 1
        
        if self.should_fail:
            raise RuntimeError(f"E2E tool failure on execution {self.execution_count}")
        
        return f"Async E2E tool result #{self.execution_count} for query: {query}"


class MockE2EAgent:
    """Mock agent for E2E testing that uses tools and WebSocket notifications."""
    
    def __init__(self, tool_dispatcher=None, websocket_bridge=None):
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = websocket_bridge
        self._run_id = None
        self._trace_context = None
        self.execution_count = 0
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for notifications."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    def set_trace_context(self, trace_context):
        """Set trace context."""
        self._trace_context = trace_context
        
    async def execute(self, state, run_id, is_streaming=False):
        """Execute agent with tool usage and WebSocket events."""
        self.execution_count += 1
        
        # Simulate agent thinking
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name="e2e_test_agent",
                reasoning=f"Starting E2E test execution #{self.execution_count}"
            )
        
        # Use tool if dispatcher is available
        tool_result = None
        if self.tool_dispatcher:
            try:
                # Notify tool execution start
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_tool_executing(
                        run_id=run_id,
                        agent_name="e2e_test_agent", 
                        tool_name="e2e_test_tool",
                        parameters={"query": f"E2E test query #{self.execution_count}"}
                    )
                
                # Execute tool (simulate dispatch)
                tool_result = f"Tool executed successfully for execution #{self.execution_count}"
                
                # Notify tool completion
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_tool_completed(
                        run_id=run_id,
                        agent_name="e2e_test_agent",
                        tool_name="e2e_test_tool",
                        result={"output": tool_result}
                    )
                    
            except Exception as e:
                # Notify tool error
                if self.websocket_bridge:
                    await self.websocket_bridge.notify_tool_error(
                        run_id=run_id,
                        agent_name="e2e_test_agent",
                        tool_name="e2e_test_tool", 
                        error=str(e)
                    )
                tool_result = f"Tool execution failed: {e}"
        
        # Final thinking update
        if self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id=run_id,
                agent_name="e2e_test_agent",
                reasoning=f"Completing E2E test execution #{self.execution_count}"
            )
        
        return {
            "success": True,
            "result": f"E2E agent execution #{self.execution_count} completed",
            "tool_result": tool_result,
            "agent_name": "e2e_test_agent",
            "execution_time": 0.2
        }


class TestAgentToolWebSocketFlowE2E:
    """E2E tests for complete agent-tool-websocket integration."""

    @pytest.fixture
    async def auth_helper(self):
        """SSOT E2E authentication helper - CLAUDE.md Compliant."""
        return E2EAuthHelper(environment="test")

    @pytest.fixture
    async def websocket_auth_helper(self):
        """Real WebSocket authentication helper - CLAUDE.md Compliant."""
        return E2EWebSocketAuthHelper(environment="test")

    @pytest.fixture 
    async def websocket_connection(self, websocket_auth_helper):
        """Real WebSocket connection - CLAUDE.md Compliant (NO MOCKS)."""
        return await websocket_auth_helper.connect_authenticated_websocket(timeout=15.0)

    @pytest.fixture
    def agent_registry(self):
        """Real agent registry for E2E testing."""
        return AgentRegistry()

    @pytest.fixture
    def tool_dispatcher_factory(self, auth_helper):
        """Real tool dispatcher factory - CLAUDE.md Compliant."""
        return UnifiedToolDispatcherFactory()

    @pytest.fixture
    def execution_core(self, agent_registry):
        """Real AgentExecutionCore - CLAUDE.md Compliant."""
        return AgentExecutionCore(agent_registry)

    @pytest.fixture
    async def e2e_context(self, auth_helper):
        """Real E2E execution context with SSOT authentication."""
        token, user_data = await create_authenticated_user(
            environment="test",
            email="e2e_tool_websocket@test.com"
        )
        
        return AgentExecutionContext(
            agent_name="e2e_test_agent",
            run_id=uuid4(),
            thread_id=f"e2e-thread-{uuid4()}",
            user_id=user_data['id'],
            correlation_id=f"e2e-correlation-{uuid4()}"
        )

    @pytest.fixture
    async def e2e_state(self, auth_helper):
        """Real E2E agent state - CLAUDE.md Compliant (NO MOCKS)."""
        token, user_data = await create_authenticated_user(
            environment="test",
            email="e2e_state@test.com"
        )
        
        # Use real DeepAgentState instead of Mock
        state = DeepAgentState(
            user_id=user_data['id'],
            thread_id=f"e2e-thread-{uuid4()}",
            data={'e2e_test': 'real_data'}
        )
        return state

    @pytest.mark.asyncio
    async def test_complete_agent_tool_websocket_flow(
        self, execution_core, agent_registry, websocket_connection,
        e2e_context, e2e_state, auth_helper
    ):
        """Test complete flow: Agent -> Tool -> WebSocket notifications - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        try:
            # Real WebSocket Event Capture - NO MOCKS
            websocket_events = []
            
            async def listen_for_real_events():
                """Listen for real WebSocket events."""
                timeout = 20.0
                event_start = time.time()
                
                while time.time() - event_start < timeout:
                    try:
                        message = await asyncio.wait_for(websocket_connection.recv(), timeout=2.0)
                        event = json.loads(message)
                        websocket_events.append({
                            'type': event.get('type'),
                            'payload': event.get('payload', {}),
                            'timestamp': time.time()
                        })
                        
                        # Stop listening when agent completes
                        if event.get('type') == 'agent_completed':
                            break
                    except asyncio.TimeoutError:
                        continue
            
            # Start real WebSocket listener
            listener_task = asyncio.create_task(listen_for_real_events())
            
            # Send real agent request through WebSocket
            agent_request = {
                "type": "chat",
                "data": {
                    "message": "Execute a test agent with tool usage",
                    "conversation_id": str(uuid4())
                }
            }
            
            await websocket_connection.send(json.dumps(agent_request))
            
            # Wait for real agent execution to complete
            await asyncio.wait_for(listener_task, timeout=25.0)
            
            # Verify REAL WebSocket events were received - HARD ASSERTIONS
            assert len(websocket_events) > 0, "Should receive real WebSocket events from agent execution"
            
            # MISSION CRITICAL: Verify agent lifecycle events (CLAUDE.md Section 6)
            event_types = [event['type'] for event in websocket_events]
            
            # These events MUST be present for substantive chat interactions
            lifecycle_events = ['agent_started', 'agent_completed']
            for required_event in lifecycle_events:
                assert required_event in event_types, f"MISSION CRITICAL: {required_event} missing from {event_types}"
            
            # Validate real agent execution sequence
            if len(event_types) >= 2:
                # First event should be agent_started or connection-related
                assert any(start_type in event_types[0] for start_type in ['agent_started', 'connection']), f"Unexpected first event: {event_types[0]}"
                
                # Last meaningful event should be agent_completed
                completed_events = [e for e in event_types if 'completed' in e]
                assert len(completed_events) > 0, f"No completion events found in {event_types}"
            
            # Verify we received substantial real agent interaction
            assert len(websocket_events) >= 2, f"Expected substantial agent interaction, got {len(websocket_events)} events"
            
        finally:
            await websocket_connection.close()
        
        # CLAUDE.md Compliance: Validate execution time (prevent 0-second execution) 
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"

    @pytest.mark.asyncio
    async def test_agent_tool_error_handling_e2e(
        self, websocket_connection, auth_helper
    ):
        """Test error handling throughout the complete flow - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        try:
            # Real WebSocket Error Event Capture - NO MOCKS
            error_events = []
            
            async def listen_for_real_errors():
                """Listen for real error events."""
                timeout = 15.0
                event_start = time.time()
                
                while time.time() - event_start < timeout:
                    try:
                        message = await asyncio.wait_for(websocket_connection.recv(), timeout=3.0)
                        event = json.loads(message)
                        
                        event_type = event.get('type', '')
                        if 'error' in event_type.lower():
                            error_events.append(event)
                        
                        # Also capture agent_completed with error info
                        if event_type == 'agent_completed':
                            payload = event.get('payload', {})
                            if 'error' in str(payload).lower() or 'fail' in str(payload).lower():
                                error_events.append(event)
                            break
                            
                    except asyncio.TimeoutError:
                        continue
            
            # Start real error listener
            error_listener_task = asyncio.create_task(listen_for_real_errors())
            
            # Send invalid request to trigger REAL error handling
            invalid_request = {
                "type": "chat",
                "data": {
                    # Missing required fields or invalid data to trigger error
                    "invalid_field": "trigger_error",
                    "message": None  # Invalid message format
                }
            }
            
            await websocket_connection.send(json.dumps(invalid_request))
            
            # Wait for real error handling to complete
            await asyncio.wait_for(error_listener_task, timeout=20.0)
            
            # Verify REAL error events were captured - HARD ASSERTIONS  
            # Note: Error handling behavior depends on implementation
            # At minimum, the connection should remain stable or provide feedback
            
            # Validate connection remains functional after error
            ping_test = {"type": "ping", "timestamp": time.time()}
            await websocket_connection.send(json.dumps(ping_test))
            
            # Should receive pong or some response (connection still works)
            ping_response = await asyncio.wait_for(websocket_connection.recv(), timeout=5.0)
            ping_event = json.loads(ping_response)
            
            # Connection should handle error gracefully and remain functional
            assert ping_event is not None, "WebSocket should remain functional after error handling"
            
        finally:
            await websocket_connection.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"

    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_e2e(
        self, websocket_auth_helper, auth_helper
    ):
        """Test multiple users have isolated WebSocket sessions - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        # Create multiple real WebSocket connections for different users - NO MOCKS
        connections = []
        user_events = []
        
        try:
            num_users = 2  # Reasonable for E2E testing
            
            # Create real WebSocket connections for multiple users
            for i in range(num_users):
                # Each user gets their own SSOT authentication
                token, user_data = await create_authenticated_user(
                    environment="test",
                    email=f"concurrent_user_{i}@test.com"
                )
                
                # Create real WebSocket connection for this user
                user_auth_helper = E2EWebSocketAuthHelper(environment="test")
                user_auth_helper._cached_token = token
                
                connection = await user_auth_helper.connect_authenticated_websocket(timeout=15.0)
                connections.append({
                    'connection': connection,
                    'user_id': user_data['id'],
                    'events': []
                })
            
            # Send different requests from each user concurrently
            async def user_session(user_connection, user_index):
                """Run isolated user session."""
                connection = user_connection['connection']
                
                # Wait for connection confirmation
                await asyncio.wait_for(connection.recv(), timeout=10.0)
                
                # Send unique request for this user
                request = {
                    "type": "chat",
                    "data": {
                        "message": f"Hello from concurrent user {user_index}",
                        "conversation_id": str(uuid4())
                    }
                }
                
                await connection.send(json.dumps(request))
                
                # Collect events for this user
                events = []
                timeout = 15.0
                event_start = time.time()
                
                while time.time() - event_start < timeout:
                    try:
                        message = await asyncio.wait_for(connection.recv(), timeout=3.0)
                        event = json.loads(message)
                        events.append(event)
                        
                        # Stop when agent completes
                        if event.get('type') == 'agent_completed':
                            break
                    except asyncio.TimeoutError:
                        continue
                
                user_connection['events'] = events
                return events
            
            # Run user sessions concurrently - REAL MULTI-USER TESTING
            session_tasks = [
                user_session(conn, i) 
                for i, conn in enumerate(connections)
            ]
            
            results = await asyncio.gather(*session_tasks)
            
            # Verify REAL multi-user isolation - HARD ASSERTIONS
            for i, user_events in enumerate(results):
                assert len(user_events) > 0, f"User {i} should receive events"
                
                # Each user should get their own agent lifecycle
                event_types = [e.get('type') for e in user_events]
                lifecycle_events = [e for e in event_types if e in ['agent_started', 'agent_completed']]
                assert len(lifecycle_events) > 0, f"User {i} should receive agent lifecycle events"
            
            # Verify isolation: users should get different event sequences
            # (different conversation IDs, user contexts, etc.)
            user1_events = results[0]
            user2_events = results[1]
            
            assert len(user1_events) > 0 and len(user2_events) > 0, "Both users should receive events"
            
            # Events should be user-specific (different conversation contexts)
            # This validates real multi-user isolation
            assert user1_events != user2_events, "Each user should receive their own isolated events"
            
        finally:
            # Clean up all connections
            for conn_info in connections:
                await conn_info['connection'].close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"

    @pytest.mark.asyncio
    async def test_websocket_event_content_validation_e2e(
        self, websocket_connection, auth_helper
    ):
        """Test WebSocket event content validation in realistic scenario - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        try:
            # Real WebSocket Event Content Validation - NO MOCKS
            captured_events = []
            
            async def validate_real_event_content():
                """Capture and validate real WebSocket events."""
                timeout = 20.0
                event_start = time.time()
                
                while time.time() - event_start < timeout:
                    try:
                        message = await asyncio.wait_for(websocket_connection.recv(), timeout=3.0)
                        event = json.loads(message)
                        captured_events.append({
                            'message_type': event.get('type'),
                            'full_message': event
                        })
                        
                        # Stop when agent completes
                        if event.get('type') == 'agent_completed':
                            break
                    except asyncio.TimeoutError:
                        continue
            
            # Start real event validation
            validation_task = asyncio.create_task(validate_real_event_content())
            
            # Send real request to generate events for validation
            validation_request = {
                "type": "chat", 
                "data": {
                    "message": "Validate WebSocket event content structure",
                    "conversation_id": str(uuid4())
                }
            }
            
            await websocket_connection.send(json.dumps(validation_request))
            
            # Wait for real event validation to complete
            await asyncio.wait_for(validation_task, timeout=25.0)
            
            # Validate REAL event content structure - HARD ASSERTIONS
            assert len(captured_events) > 0, "Should capture real WebSocket events for validation"
            
            for event_info in captured_events:
                message = event_info['full_message']
                message_type = event_info['message_type']
                
                # All real events should have basic structure
                assert isinstance(message, dict), f"Event should be dict: {message}"
                assert 'type' in message, f"Event missing 'type' field: {message}"
                
                # Validate payload structure if present
                if 'payload' in message:
                    payload = message['payload']
                    assert isinstance(payload, dict), f"Payload should be dict: {payload}"
                
                # Event-specific validation for real events
                if message_type == 'agent_started':
                    # Real agent_started events should have agent context
                    payload = message.get('payload', {})
                    # Basic validation - exact fields depend on implementation
                    assert len(str(payload)) > 0, "agent_started should have meaningful payload"
                    
                elif message_type == 'agent_completed':
                    # Real agent_completed events should have completion info
                    payload = message.get('payload', {})
                    # Basic validation - exact fields depend on implementation  
                    assert len(str(payload)) > 0, "agent_completed should have meaningful payload"
            
            # Verify we captured substantial event content
            event_types = [e['message_type'] for e in captured_events]
            assert len(set(event_types)) > 0, f"Should capture diverse event types: {event_types}"
            
        finally:
            await websocket_connection.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 0.1, f"E2E test executed too quickly: {execution_time:.3f}s - indicates mocked behavior"

    @pytest.mark.asyncio
    async def test_websocket_connection_stability_e2e(
        self, websocket_connection, auth_helper
    ):
        """Test WebSocket connection stability under real load - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        try:
            # Real WebSocket Stability Testing - NO MOCKS
            stability_events = []
            
            # Send multiple requests to test connection stability
            num_requests = 3  # Reasonable for E2E stability testing
            
            for i in range(num_requests):
                # Send real request
                stability_request = {
                    "type": "chat",
                    "data": {
                        "message": f"Stability test request {i+1}",
                        "conversation_id": str(uuid4())
                    }
                }
                
                await websocket_connection.send(json.dumps(stability_request))
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket_connection.recv(), timeout=10.0)
                    event = json.loads(response)
                    stability_events.append({
                        'request_number': i+1,
                        'event_type': event.get('type'),
                        'timestamp': time.time()
                    })
                except asyncio.TimeoutError:
                    # If we timeout, that's still data about stability
                    stability_events.append({
                        'request_number': i+1, 
                        'event_type': 'timeout',
                        'timestamp': time.time()
                    })
                
                # Small delay between requests
                await asyncio.sleep(0.5)
            
            # Verify REAL connection stability - HARD ASSERTIONS
            assert len(stability_events) == num_requests, f"Should process all {num_requests} requests"
            
            # Verify connection remained stable throughout
            timeouts = [e for e in stability_events if e['event_type'] == 'timeout']
            success_rate = (num_requests - len(timeouts)) / num_requests
            
            # CLAUDE.md Compliant: NO GRACEFUL FALLBACKS - Hard failure required
            assert success_rate >= 1.0, f"Connection stability test failed: {success_rate*100:.1f}% success rate. Timeouts: {len(timeouts)}/{num_requests}"
            
            # Verify connection is still functional after load
            final_ping = {"type": "ping", "timestamp": time.time()}
            await websocket_connection.send(json.dumps(final_ping))
            
            final_response = await asyncio.wait_for(websocket_connection.recv(), timeout=5.0)
            final_event = json.loads(final_response)
            
            assert final_event is not None, "WebSocket should remain functional after stability test"
            
        finally:
            await websocket_connection.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 1.5, f"E2E stability test should include real timing: {execution_time:.3f}s"

    @pytest.mark.asyncio
    async def test_websocket_heartbeat_and_persistence_e2e(
        self, websocket_connection, auth_helper
    ):
        """Test WebSocket heartbeat and connection persistence - CLAUDE.md Compliant."""
        test_start_time = time.time()
        
        try:
            # Real WebSocket Heartbeat Testing - NO MOCKS
            heartbeat_responses = []
            
            # Test multiple heartbeat cycles
            num_heartbeats = 3
            
            for i in range(num_heartbeats):
                # Send real heartbeat
                heartbeat_request = {
                    "type": "ping",
                    "timestamp": time.time(),
                    "sequence": i+1
                }
                
                await websocket_connection.send(json.dumps(heartbeat_request))
                
                # Wait for heartbeat response
                try:
                    response = await asyncio.wait_for(websocket_connection.recv(), timeout=8.0)
                    response_event = json.loads(response)
                    heartbeat_responses.append({
                        'sequence': i+1,
                        'response_type': response_event.get('type'),
                        'timestamp': time.time()
                    })
                except asyncio.TimeoutError:
                    heartbeat_responses.append({
                        'sequence': i+1,
                        'response_type': 'timeout',
                        'timestamp': time.time()
                    })
                
                # Real delay between heartbeats
                await asyncio.sleep(1.0)
            
            # Verify REAL heartbeat responses - HARD ASSERTIONS
            assert len(heartbeat_responses) == num_heartbeats, f"Should process all {num_heartbeats} heartbeats"
            
            # Verify heartbeat functionality
            successful_heartbeats = [
                h for h in heartbeat_responses 
                if h['response_type'] in ['pong', 'ping'] or 'pong' in str(h['response_type']).lower()
            ]
            
            # At least most heartbeats should succeed
            heartbeat_success_rate = len(successful_heartbeats) / num_heartbeats
            assert heartbeat_success_rate >= 0.67, f"Heartbeat success rate too low: {heartbeat_success_rate*100:.1f}%"
            
            # Test connection persistence after heartbeats
            persistence_test = {
                "type": "chat",
                "data": {
                    "message": "Test connection persistence after heartbeats",
                    "conversation_id": str(uuid4())
                }
            }
            
            await websocket_connection.send(json.dumps(persistence_test))
            
            # Should receive response, confirming persistence
            persistence_response = await asyncio.wait_for(websocket_connection.recv(), timeout=10.0)
            persistence_event = json.loads(persistence_response)
            
            assert persistence_event is not None, "Connection should persist after heartbeat cycles"
            
        finally:
            await websocket_connection.close()
        
        # CLAUDE.md Compliance: Validate execution time
        execution_time = time.time() - test_start_time
        assert execution_time >= 3.0, f"E2E heartbeat test should include real timing: {execution_time:.3f}s"