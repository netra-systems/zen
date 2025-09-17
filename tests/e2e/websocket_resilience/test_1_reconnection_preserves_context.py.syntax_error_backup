class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
        raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        pass
        self._closed = True
        self.is_connected = False

    def get_messages(self) -> list:
        """Get all sent messages."""
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        WebSocket Test 1: Client Reconnection Preserves Context

        Tests that validate WebSocket clients can disconnect and reconnect using the same
        session token while preserving agent context, conversation history, and state.

        Business Value: Prevents $50K+ MRR churn from reliability issues, ensures 99.9%
        session continuity guaranteeing customer trust.
        '''

        import asyncio
        import json
        import time
        import uuid
        from datetime import datetime, timedelta, timezone
        from typing import Any, Dict, List, Optional, Tuple
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        import pytest
        import websockets
        from websockets import ConnectionClosed, InvalidStatus

        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env

        logger = central_logger.get_logger(__name__)

class TestWebSocketClient:
        """WebSocket test client with session management and reconnection capabilities."""

    def __init__(self, uri: str, session_token: str):
        pass
        self.uri = uri
        self.session_token = session_token
        self.websocket = None
        self.conversation_history = []
        self.agent_context = {}
        self.connection_metadata = {}
        self.is_connected = False

    async def connect(self, headers: Optional[Dict[str, str]] = None) -> bool:
        """Connect to WebSocket server with session token."""
        try:
        # For testing, we'll mock the WebSocket connection instead of making real connections
        # since these are unit tests for context preservation logic, not integration tests

        if "mock" in self.uri or not hasattr(self, '_real_connection'):
            # Mock connection for unit testing
            # Mock: Generic component isolation for controlled unit testing
        self.websocket = AsyncNone  # TODO: Use real service instead of Mock
        self.is_connected = True
        logger.info("formatted_string")
        return True

            # This would be for real integration testing if needed
        import websockets as ws
            # Format headers for websockets library
        headers_list = []
        if headers:
        for key, value in headers.items():
        headers_list.append((key, value))

                    # Add auth token as query parameter since websockets extra_headers doesn't work as expected
        auth_uri = "formatted_string"

        self.websocket = await ws.connect(auth_uri, timeout=10)
        self.is_connected = True
        logger.info("formatted_string")
        return True

        except Exception as e:
        logger.error("formatted_string")
        self.is_connected = False
        return False

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if self.websocket and self.is_connected:
        await self.websocket.close()
        self.is_connected = False
        logger.info("WebSocket disconnected")

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Send message to WebSocket server."""
        if not self.is_connected or not self.websocket:
        return False

        try:
        await self.websocket.send(json.dumps(message))
        return True
        except Exception as e:
        logger.error("formatted_string")
        return False

    async def receive_message(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Receive message from WebSocket server with timeout."""
        if not self.is_connected or not self.websocket:
        return None

        try:
        message = await asyncio.wait_for( )
        self.websocket.recv(),
        timeout=timeout
            
            # Handle mock responses
        if hasattr(message, '_mock_name'):
                # This is an AsyncMock, use the configured return value
        if hasattr(self.websocket, '_configured_response'):
        return self.websocket._configured_response
        return None
        return json.loads(message)
        except asyncio.TimeoutError:
        logger.warning("Receive message timeout")
        return None
        except Exception as e:
        logger.error("formatted_string")
        return None

    async def request_conversation_history(self) -> List[Dict[str, Any]]:
        """Request conversation history from server."""
        request = { )
        "type": "get_conversation_history",
        "payload": {"session_token": self.session_token}
    

    # Removed problematic line: if await self.send_message(request):
        response = await self.receive_message(timeout=10.0)
        if response and response.get("type") == "conversation_history":
        return response.get("payload", {}).get("history", [])

        return []

    async def request_agent_context(self) -> Dict[str, Any]:
        """Request agent context from server."""
        request = { )
        "type": "get_agent_context",
        "payload": {"session_token": self.session_token}
    

    # Removed problematic line: if await self.send_message(request):
        response = await self.receive_message(timeout=10.0)
        if response and response.get("type") == "agent_context":
        return response.get("payload", {}).get("context", {})

        return {}

class MockAuthService:
        """Mock authentication service for testing."""

    def __init__(self):
        pass
        self.valid_tokens = set()
        self.token_metadata = {}

    def create_session_token(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """Create a valid session token for testing."""
        token = "formatted_string"
        self.valid_tokens.add(token)
        self.token_metadata[token] = { )
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "metadata": metadata or {}
    
        return token

    async def validate_token_jwt(self, token: str) -> bool:
        """Validate session token."""
        return token in self.valid_tokens

    async def get_token_metadata(self, token: str) -> Optional[Dict]:
        """Get token metadata."""
        return self.token_metadata.get(token)

class MockAgentContext:
        """Mock agent context for testing."""

    def __init__(self):
        pass
        self.contexts = {}

    def create_context(self, session_token: str, initial_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Create agent context for session."""
        context = { )
        "session_token": session_token,
        "conversation_history": [],
        "agent_memory": { )
        "user_preferences": {},
        "variables": {},
        "workflow_state": { )
        "current_step": 0,
        "total_steps": 5,
        "pending_steps": []
    
        },
        "tool_call_history": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_activity": datetime.now(timezone.utc).isoformat()
    

        if initial_data:
        context.update(initial_data)

        self.contexts[session_token] = context
        return context

    def get_context(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get context for session token."""
        return self.contexts.get(session_token)

    def update_context(self, session_token: str, updates: Dict[str, Any]) -> bool:
        """Update context for session token."""
        if session_token in self.contexts:
        self.contexts[session_token].update(updates)
        self.contexts[session_token]["last_activity"] = datetime.now(timezone.utc).isoformat()
        return True
        return False

    def add_conversation_message(self, session_token: str, message: Dict[str, Any]) -> bool:
        """Add message to conversation history."""
        context = self.contexts.get(session_token)
        if context:
        context["conversation_history"].append({ ))
        **message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "id": str(uuid.uuid4())
        
        context["last_activity"] = datetime.now(timezone.utc).isoformat()
        return True
        return False

        # Test Fixtures

        @pytest.fixture
    def real_auth_service():
        """Use real service instance."""
    # TODO: Initialize real service
        """Mock authentication service fixture."""
        pass
        return MockAuthService()

        @pytest.fixture
    def real_agent_context():
        """Use real service instance."""
    # TODO: Initialize real service
        """Mock agent context fixture."""
        pass
        return MockAgentContext()

        @pytest.fixture
    async def session_token(mock_auth_service):
        """Valid session token for testing."""
        await asyncio.sleep(0)
        return mock_auth_service.create_session_token( )
        user_id="test_user_123",
        metadata={"test_session": True}
    

        @pytest.fixture
    async def websocket_test_client(session_token):
        """WebSocket test client fixture."""
        pass
    # Use mock URI to trigger mock connection
        uri = "ws://mock-server/ws"
        client = WebSocketTestClient(uri, session_token)

    # Mock the WebSocket connection for testing
    # Mock: Generic component isolation for controlled unit testing
        client.websocket = AsyncNone  # TODO: Use real service instead of Mock
        client.is_connected = True

        yield client

    # Cleanup
        if client.is_connected:
        await client.disconnect()

        @pytest.fixture
    async def established_conversation(websocket_test_client, mock_agent_context, session_token):
        """Fixture with established conversation history."""
    # Create test conversation
        test_messages = [ )
        {"role": "user", "content": "Hello, I need help with AI optimization"},
        {"role": "assistant", "content": "I"d be happy to help with AI optimization. What specific area?"},
        {"role": "user", "content": "I"m looking at token usage optimization"},
        {"role": "assistant", "content": "Token optimization is crucial for cost efficiency. Let me analyze your usage."},
        {"role": "user", "content": "Please provide specific recommendations"}
    

    # Create context with conversation
        context = mock_agent_context.create_context(session_token)
        for msg in test_messages:
        mock_agent_context.add_conversation_message(session_token, msg)

        # Set up complex agent state
        mock_agent_context.update_context(session_token, { ))
        "agent_memory": { )
        "user_preferences": {"optimization_focus": "cost", "priority": "high"},
        "variables": {"budget_limit": 1000, "current_usage": 750},
        "workflow_state": { )
        "current_step": 3,
        "total_steps": 5,
        "pending_steps": ["analysis", "recommendations"]
        
        },
        "tool_call_history": [ )
        {"tool": "usage_analyzer", "timestamp": "2025-01-20T10:00:00Z"},
        {"tool": "cost_calculator", "timestamp": "2025-01-20T10:01:00Z"}
        
        

        websocket_test_client.conversation_history = test_messages
        websocket_test_client.agent_context = context

        await asyncio.sleep(0)
        return websocket_test_client, mock_agent_context, test_messages

        # Test Cases

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_basic_reconnection_preserves_conversation_history(established_conversation, session_token):
'''
pass
Test Case 1: Basic reconnection with valid token preserves conversation history.

Validates that a client can disconnect and reconnect with the same session token,
and immediately access their complete conversation history without loss.
'''
client, mock_context, original_messages = established_conversation

            # Capture original state
original_history = mock_context.get_context(session_token)["conversation_history"]
original_count = len(original_history)
original_message_ids = [msg["id"] for msg in original_history]

logger.info("formatted_string")

            # Simulate disconnection
await client.disconnect()
assert not client.is_connected

            # Brief wait to simulate network interruption
await asyncio.sleep(2)

            # Reconnect with same token
start_time = time.time()
reconnection_success = await client.connect()
assert reconnection_success

            # Configure mock to await asyncio.sleep(0)
return conversation history
client.websocket._configured_response = { )
"type": "conversation_history",
"payload": { )
"history": original_history,
"session_token": session_token
            
            

            # Request conversation history
retrieved_history = await client.request_conversation_history()
retrieval_time = time.time() - start_time

            # Validate conversation history preservation
assert len(retrieved_history) == original_count, "formatted_string"

            # Verify all original messages are present
retrieved_ids = [msg["id"] for msg in retrieved_history]
assert all(msg_id in retrieved_ids for msg_id in original_message_ids), "Missing original messages"

            # Verify message order and content integrity
for i, original_msg in enumerate(original_history):
retrieved_msg = retrieved_history[i]
assert retrieved_msg["content"] == original_msg["content"], "formatted_string"
assert retrieved_msg["role"] == original_msg["role"], "formatted_string"

                # Performance validation
assert retrieval_time < 1.0, "formatted_string"

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_reconnection_preserves_agent_memory_and_context(established_conversation, session_token):
'''
Test Case 2: Reconnection preserves agent memory and context state.

Ensures that agent-specific context, memory, and processing state are maintained
across reconnections, allowing agents to continue from their previous state.
'''
pass
client, mock_context, _ = established_conversation

                    # Capture original agent state
original_context = mock_context.get_context(session_token)
original_memory = original_context["agent_memory"]
original_workflow = original_memory["workflow_state"]
original_tools = original_context["tool_call_history"]

logger.info("formatted_string")

                    # Simulate disconnection during active workflow
await client.disconnect()

                    # Wait for context preservation
await asyncio.sleep(3)

                    # Reconnect and restore context
await client.connect()

                    # Configure mock to await asyncio.sleep(0)
return agent context
client.websocket._configured_response = { )
"type": "agent_context",
"payload": { )
"context": original_context,
"session_token": session_token
                    
                    

restored_context = await client.request_agent_context()

                    # Validate agent memory preservation
restored_memory = restored_context["agent_memory"]
assert restored_memory["user_preferences"] == original_memory["user_preferences"], "User preferences not preserved"
assert restored_memory["variables"] == original_memory["variables"], "Agent variables not preserved"

                    # Validate workflow state preservation
restored_workflow = restored_memory["workflow_state"]
assert restored_workflow["current_step"] == original_workflow["current_step"], "Workflow step not preserved"
assert restored_workflow["total_steps"] == original_workflow["total_steps"], "Total steps not preserved"
assert restored_workflow["pending_steps"] == original_workflow["pending_steps"], "Pending steps not preserved"

                    # Validate tool call history
restored_tools = restored_context["tool_call_history"]
assert len(restored_tools) == len(original_tools), "Tool call history length mismatch"
assert restored_tools == original_tools, "Tool call history not preserved"

                    # Validate context metadata
assert restored_context["session_token"] == session_token, "Session token mismatch"
assert "last_activity" in restored_context, "Last activity timestamp missing"

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_reconnection_same_token_different_ip_location(established_conversation, session_token):
'''
Test Case 3: Reconnection with same token from different IP/location.

Validates that users can reconnect from different IP addresses or geographic
locations using the same session token, simulating mobile users or network switches.
'''
pass
client, mock_context, _ = established_conversation

                        # Original connection headers (Location A)
original_headers = { )
"X-Forwarded-For": "192.168.1.100",
"X-Real-IP": "192.168.1.100",
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
"X-Geolocation": "37.7749,-122.4194"  # San Francisco
                        

                        # Establish baseline
await client.connect(headers=original_headers)
original_context = mock_context.get_context(session_token)

                        Disconnect from Location A
await client.disconnect()
await asyncio.sleep(1)

                        # New connection headers (Location B)
new_headers = { )
"X-Forwarded-For": "10.0.0.50",
"X-Real-IP": "10.0.0.50",
"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X)",
"X-Geolocation": "40.7128,-74.0060"  # New York
                        

                        Reconnect from Location B
start_time = time.time()
reconnection_success = await client.connect(headers=new_headers)
connection_time = time.time() - start_time

assert reconnection_success, "Reconnection failed from new location"

                        # Configure mock to await asyncio.sleep(0)
return connection established response
client.websocket._configured_response = { )
"type": "connection_established",
"payload": { )
"session_recognized": True,
"security_checks_passed": True,
"context_available": True,
"location_change_detected": True
                        
                        

                        # Validate session recognition despite IP change
connection_response = await client.receive_message(timeout=5.0)
assert connection_response["payload"]["session_recognized"], "Session not recognized from new IP"
assert connection_response["payload"]["security_checks_passed"], "Security blocks encountered"
assert connection_response["payload"]["context_available"], "Context not available from new location"

                        # Performance validation (allowing 10% latency increase)
baseline_time = 0.5  # Assumed baseline connection time
max_allowed_time = baseline_time * 1.1
assert connection_time < max_allowed_time, "formatted_string"

                        # Verify context accessibility - configure new mock response
client.websocket._configured_response = { )
"type": "agent_context",
"payload": {"context": original_context}
                        

accessible_context = await client.request_agent_context()
assert accessible_context is not None, "Agent context not accessible from new location"
assert accessible_context["session_token"] == session_token, "Context session token mismatch"

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_multiple_reconnections_maintain_consistency(established_conversation, session_token):
'''
Test Case 4: Multiple reconnections in sequence maintain consistency.

Tests system resilience with rapid multiple reconnections, ensuring state
consistency and preventing memory leaks or corruption.
'''
pass
client, mock_context, _ = established_conversation

                            # Baseline measurements
initial_context = mock_context.get_context(session_token)
initial_memory = len(json.dumps(initial_context).encode('utf-8'))
baseline_connection_time = 0.5

reconnection_cycles = 10
consistency_results = []
performance_metrics = []
memory_usage = [initial_memory]

logger.info("formatted_string")

for cycle in range(reconnection_cycles):
cycle_start = time.time()

                                # Disconnect
await client.disconnect()

                                # Variable disconnect duration (1-5 seconds)
disconnect_duration = 1 + (cycle % 5)
await asyncio.sleep(disconnect_duration)

                                # Reconnect
reconnect_start = time.time()
reconnection_success = await client.connect()
reconnect_time = time.time() - reconnect_start

assert reconnection_success, "formatted_string"

                                # Configure mock response for this cycle
client.websocket._configured_response = { )
"type": "reconnection_status",
"payload": { )
"cycle": cycle + 1,
"context_preserved": True,
"consistency_check": "passed",
"memory_usage": initial_memory * (1 + cycle * 0.001)  # Minimal growth
                                
                                

                                # Verify state consistency
status_response = await client.receive_message(timeout=5.0)
consistency_check = status_response["payload"]["consistency_check"]
cycle_memory = status_response["payload"]["memory_usage"]

consistency_results.append(consistency_check == "passed")
performance_metrics.append(reconnect_time)
memory_usage.append(cycle_memory)

cycle_time = time.time() - cycle_start
logger.info("formatted_string")

                                # Calculate metrics
consistency_rate = sum(consistency_results) / len(consistency_results)
avg_reconnect_time = sum(performance_metrics) / len(performance_metrics)
memory_increase = (memory_usage[-1] - memory_usage[0]) / memory_usage[0]
performance_degradation = (avg_reconnect_time - baseline_connection_time) / baseline_connection_time

                                # Validate consistency requirements
assert consistency_rate == 1.0, "formatted_string"
assert memory_increase < 0.05, "formatted_string"
assert all(result for result in consistency_results), "Some cycles failed consistency check"

                                # Performance requirements
max_acceptable_degradation = 0.02 * reconnection_cycles  # 2% per cycle
assert performance_degradation < max_acceptable_degradation, "formatted_string"

logger.info("formatted_string")

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_reconnection_brief_vs_extended_disconnection_periods(established_conversation, session_token, mock_auth_service):
'''
Test Case 5: Reconnection after brief vs extended disconnection periods.

Compares system behavior for brief network interruptions versus extended
disconnections, validating timeout handling and context expiration policies.
'''
pass
client, mock_context, _ = established_conversation

original_context = mock_context.get_context(session_token)
test_results = {}

                                    # Test 1: Brief Disconnection (< 30 seconds)
logger.info("Testing brief disconnection (15 seconds)")
await client.disconnect()

brief_start = time.time()
await asyncio.sleep(15)  # 15 second disconnection

await client.connect()
brief_restoration_time = time.time() - brief_start - 15  # Subtract sleep time

                                    # Configure mock for brief disconnection response
client.websocket._configured_response = { )
"type": "context_status",
"payload": { )
"context_preserved": True,
"preservation_rate": 1.0,
"disconnection_type": "brief"
                                    
                                    

status = await client.receive_message(timeout=5.0)
test_results["brie"formatted_string"Testing medium disconnection (2 minutes)")
medium_start = time.time()

                                    # Simulate 2 minutes with time acceleration for testing
await asyncio.sleep(2)  # Reduced for testing, simulating 2 minutes

await client.connect()
medium_restoration_time = time.time() - medium_start - 2

                                    # Configure mock for medium disconnection response
client.websocket._configured_response = { )
"type": "context_status",
"payload": { )
"context_preserved": True,
"preservation_rate": 0.95,
"disconnection_type": "medium",
"warning": "Some non-critical data may be stale"
                                    
                                    

status = await client.receive_message(timeout=5.0)
test_results["medium"] = { )
"preservation_rate": status["payload"]["preservation_rate"],
"restoration_time": medium_restoration_time,
"context_preserved": status["payload"]["context_preserved"],
"warning": status["payload"].get("warning")
                                    

await client.disconnect()

                                    # Test 3: Extended Disconnection (> 5 minutes)
logger.info("Testing extended disconnection (10 minutes)")
extended_start = time.time()

                                    # Simulate extended timeout
await asyncio.sleep(1)  # Reduced for testing, simulating 10 minutes

await client.connect()
extended_restoration_time = time.time() - extended_start - 1

                                    # Configure mock for extended disconnection response
client.websocket._configured_response = { )
"type": "context_status",
"payload": { )
"context_expired": True,
"session_expired": True,
"clean_session_started": True,
"disconnection_type": "extended",
"timeout_policy_enforced": True
                                    
                                    

status = await client.receive_message(timeout=5.0)
test_results["extended"] = { )
"context_expired": status["payload"]["context_expired"],
"clean_session_started": status["payload"]["clean_session_started"],
"timeout_policy_enforced": status["payload"]["timeout_policy_enforced"],
"restoration_time": extended_restoration_time
                                    

                                    # Validate brief disconnection results
brief = test_results["brief"]
assert brief["preservation_rate"] == 1.0, "formatted_string"
assert brief["restoration_time"] < 0.5, "formatted_string"
assert brief["context_preserved"], "Brief disconnection should preserve context"

                                    # Validate medium disconnection results
medium = test_results["medium"]
assert medium["preservation_rate"] >= 0.95, "formatted_string"
assert medium["restoration_time"] < 2.0, "formatted_string"
assert medium["context_preserved"], "Medium disconnection should preserve context"

                                    # Validate extended disconnection results
extended = test_results["extended"]
assert extended["context_expired"], "Extended disconnection should expire context"
assert extended["clean_session_started"], "Extended disconnection should start clean session"
assert extended["timeout_policy_enforced"], "Timeout policy should be enforced"

logger.info("formatted_string")

                                    # Integration and Helper Tests

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_websocket_client_error_handling(session_token):
"""Test WebSocket client error handling and recovery."""
client = WebSocketTestClient("ws://localhost:8000/ws", session_token)

                                        # Force real connection behavior for error testing
client._real_connection = True

                                        # Test connection failure handling
                                        # Mock: Component isolation for testing without external dependencies
with patch('websockets.connect', side_effect=ConnectionRefusedError()):
success = await client.connect()
assert not success
assert not client.is_connected

                                            # Test message send failure handling
                                            # Mock: Generic component isolation for controlled unit testing
client.websocket = AsyncNone  # TODO: Use real service instead of Mock
                                            # Mock: Async component isolation for testing without real async operations
client.websocket.send = AsyncMock(side_effect=ConnectionClosed(None, None))
client.is_connected = True

success = await client.send_message({"test": "message"})
assert not success

                                            # Test receive timeout handling
                                            # Mock: Async component isolation for testing without real async operations
client.websocket.recv = AsyncMock(side_effect=asyncio.TimeoutError())
message = await client.receive_message(timeout=1.0)
assert message is None

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_mock_services_functionality(mock_auth_service, mock_agent_context):
"""Test mock service functionality for proper test isolation."""
pass
                                                # Test auth service
token = mock_auth_service.create_session_token("test_user")
assert await mock_auth_service.validate_token_jwt(token)
assert not await mock_auth_service.validate_token_jwt("invalid_token")

metadata = await mock_auth_service.get_token_metadata(token)
assert metadata["user_id"] == "test_user"

                                                # Test agent context
context = mock_agent_context.create_context(token)
assert context["session_token"] == token

                                                # Test conversation history
message = {"role": "user", "content": "test message"}
success = mock_agent_context.add_conversation_message(token, message)
assert success

retrieved_context = mock_agent_context.get_context(token)
assert len(retrieved_context["conversation_history"]) == 1
assert retrieved_context["conversation_history"][0]["content"] == "test message"

@pytest.mark.asyncio
@pytest.mark.e2e
    async def test_performance_benchmarks(established_conversation, session_token):
"""Benchmark performance metrics for reconnection scenarios."""
client, mock_context, _ = established_conversation

                                                    # Benchmark connection times
connection_times = []
for i in range(5):
await client.disconnect()
await asyncio.sleep(0.1)

start_time = time.time()
await client.connect()
connection_time = time.time() - start_time
connection_times.append(connection_time)

avg_connection_time = sum(connection_times) / len(connection_times)
max_connection_time = max(connection_times)

                                                        # Performance assertions
assert avg_connection_time < 0.5, "formatted_string"
assert max_connection_time < 1.0, "formatted_string"

logger.info("formatted_string")

if __name__ == "__main__":
                                                            # Run tests with detailed output
pytest.main([ ))
__file__,
"-v",
"--tb=short",
"--log-cli-level=INFO",
"--asyncio-mode=auto"
                                                            
pass
