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
        MISSION CRITICAL TEST SUITE: Eliminate Placeholder Values
        ==========================================================
        This test suite ensures NO placeholder values exist in the system:
        - No 'registry' run_ids
        - No None user_ids
        - Fail fast if context missing
        - Proper context validation throughout

        Business Impact: Without these fixes:
        - Cannot scale beyond 2-3 concurrent users
        - Risk of data leakage between users
        - WebSocket events may be delivered to wrong users
        - Database transaction conflicts under load
        '''

        import asyncio
        import pytest
        import sys
        import os
        from typing import Optional, Any, Dict, List
        import uuid
        import inspect
        from dataclasses import dataclass
        import re
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from shared.isolated_environment import IsolatedEnvironment

            # Add the backend directory to the path
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../netra_backend')))

        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
        from netra_backend.app.models.agent_models import AgentExecutionContext, AgentExecutionResult
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


        @dataclass
class UserExecutionContext:
        """Context that MUST be present for all user operations"""
        user_id: str
        thread_id: str
        run_id: str
        request_id: str

    def __post_init__(self):
        """Validate context on creation"""
        if not self.user_id or self.user_id == "None":
        raise ValueError("formatted_string")
        if not self.run_id or self.run_id == "registry":
        raise ValueError("formatted_string")
        if not self.thread_id:
        raise ValueError("formatted_string")
        if not self.request_id:
        raise ValueError("formatted_string")


class TestNoPlaceholderValues:
        """Test that NO placeholder values exist in the system"""

        @pytest.mark.critical
@pytest.mark.asyncio
    async def test_no_registry_run_id_in_agent_registration(self):
"""CRITICAL: Agent registration MUST NOT use 'registry' as run_id"""
registry = AgentRegistry()

        # Mock an agent
websocket = TestWebSocketConnection()  # Real WebSocket implementation

        # Register the agent
registry.register("test_agent", mock_agent)

        # Check if set_websocket_bridge was called
if mock_agent.set_websocket_bridge.called:
calls = mock_agent.set_websocket_bridge.call_args_list
for call in calls:
args, kwargs = call
                # The second argument should be run_id
if len(args) > 1:
run_id = args[1]
assert run_id != 'registry', "formatted_string"
assert run_id is not None, f"Found None run_id in agent registration"

@pytest.mark.critical
@pytest.mark.asyncio
    async def test_no_registry_run_id_in_websocket_bridge_setting(self):
"""CRITICAL: WebSocket bridge MUST NOT be set with 'registry' run_id"""
pass
registry = AgentRegistry()

                        # Create a mock WebSocket bridge
websocket = TestWebSocketConnection()  # Real WebSocket implementation

                        # Track all calls to set_websocket_bridge
original_method = None
called_with_registry = []

def track_websocket_bridge_calls(agent_name, agent):
"""Track all set_websocket_bridge calls"""
if hasattr(agent, 'set_websocket_bridge'):
original_set = agent.set_websocket_bridge
def wrapper(bridge, run_id):
if run_id == 'registry':
called_with_registry.append({ ))
'agent': agent_name,
'run_id': run_id
        
await asyncio.sleep(0)
return original_set(bridge, run_id)
agent.set_websocket_bridge = wrapper

        # Mock agent with WebSocket bridge support
websocket = TestWebSocketConnection()  # Real WebSocket implementation

        # Set WebSocket bridge on registry
registry.set_websocket_bridge(mock_bridge)

        # Register agent (this internally sets bridge)
registry.register("test_agent", mock_agent)

        # Check if any calls used 'registry' as run_id
if mock_agent.set_websocket_bridge.called:
for call in mock_agent.set_websocket_bridge.call_args_list:
args, _ = call
if len(args) > 1:
assert args[1] != 'registry', f"WebSocket bridge set with placeholder 'registry' run_id"

@pytest.mark.critical
@pytest.mark.asyncio
    async def test_no_none_user_id_in_execution(self):
"""CRITICAL: Execution MUST NOT proceed with None user_id"""
pass
engine = UserExecutionEngine()

                        # Try to execute with None user_id
with pytest.raises((ValueError, AttributeError, TypeError)) as exc_info:
context = AgentExecutionContext( )
agent_name="test_agent",
user_id=None,  # Invalid!
thread_id="thread_123",
run_id="run_123"
                            
                            # Should fail before execution
await engine.execute_agent(context, {"query": "test"})

                            # Verify it failed for the right reason
assert "user_id" in str(exc_info.value).lower() or \
"none" in str(exc_info.value).lower() or \
"required" in str(exc_info.value).lower()

@pytest.mark.critical
def test_user_context_validation(self):
"""CRITICAL: UserExecutionContext MUST validate all fields"""

    # Test invalid user_id
with pytest.raises(ValueError) as exc_info:
UserExecutionContext( )
user_id=None,
thread_id="thread_123",
run_id="run_123",
request_id="req_123"
        
assert "Invalid user_id" in str(exc_info.value)

        # Test 'None' string user_id
with pytest.raises(ValueError) as exc_info:
UserExecutionContext( )
user_id="None",
thread_id="thread_123",
run_id="run_123",
request_id="req_123"
            
assert "Invalid user_id" in str(exc_info.value)

            # Test 'registry' run_id
with pytest.raises(ValueError) as exc_info:
UserExecutionContext( )
user_id="user_123",
thread_id="thread_123",
run_id="registry",
request_id="req_123"
                
assert "Invalid run_id" in str(exc_info.value)

                # Test empty thread_id
with pytest.raises(ValueError) as exc_info:
UserExecutionContext( )
user_id="user_123",
thread_id="",
run_id="run_123",
request_id="req_123"
                    
assert "Invalid thread_id" in str(exc_info.value)

@pytest.mark.critical
@pytest.mark.asyncio
    async def test_concurrent_user_context_isolation(self):
"""CRITICAL: Concurrent users MUST have isolated contexts"""
pass
engine = UserExecutionEngine()

user1_context = AgentExecutionContext( )
agent_name="test_agent",
user_id="user_001",
thread_id="thread_001",
run_id="formatted_string"
                        

user2_context = AgentExecutionContext( )
agent_name="test_agent",
user_id="user_002",
thread_id="thread_002",
run_id="formatted_string"
                        

                        # Track contexts used
contexts_seen = []

async def mock_execute(context, input_data):
pass
contexts_seen.append({ ))
'user_id': context.user_id,
'run_id': context.run_id
    
await asyncio.sleep(0.1)  # Simulate work
await asyncio.sleep(0)
return AgentExecutionResult( )
success=True,
result="test",
error=None,
metadata={}
    

    # Patch the actual execution
with patch.object(engine, '_execute_agent_internal', mock_execute):
        # Execute concurrently
results = await asyncio.gather( )
engine.execute_agent(user1_context, {"query": "test1"}),
engine.execute_agent(user2_context, {"query": "test2"})
        

        # Verify both contexts were used
assert len(contexts_seen) == 2
assert any(c['user_id'] == 'user_001' for c in contexts_seen)
assert any(c['user_id'] == 'user_002' for c in contexts_seen)

        # Verify no context mixing
for context in contexts_seen:
assert context['user_id'] in ['user_001', 'user_002']
assert context['run_id'] != 'registry'


class TestAgentRegistryPlaceholders:
        """Deep dive into AgentRegistry placeholder issues"""

        @pytest.mark.critical
    def test_scan_agent_registry_source_for_placeholders(self):
        """CRITICAL: Scan AgentRegistry source code for 'registry' placeholders"""
    # Read the actual source file
        registry_path = os.path.join( )
        os.path.dirname(__file__),
        '../../netra_backend/app/agents/supervisor/agent_registry.py'
    

        with open(registry_path, 'r') as f:
        source = f.read()

        # Find all instances of 'registry' as run_id
        pattern = r"set_websocket_bridge\([^,]+,\s*['"]registry['"]\)"
        matches = re.findall(pattern, source)

        assert len(matches) == 0, "formatted_string"

        # Also check for any hardcoded 'registry' strings
        registry_lines = []
        for i, line in enumerate(source.split(" ))
        "), 1):
        if "'registry'" in line or '"registry"' in line:
        if 'run_id' in line or 'set_websocket_bridge' in line:
        registry_lines.append("formatted_string")

        assert len(registry_lines) == 0, f"Found "registry" placeholders:
        " + "
        ".join(registry_lines)

        @pytest.mark.critical
@pytest.mark.asyncio
    async def test_dynamic_agent_registration_with_proper_context(self):
"""CRITICAL: Dynamic agent registration MUST use proper context"""
pass
registry = AgentRegistry()

                            # Create proper user context
user_context = UserExecutionContext( )
user_id="user_123",
thread_id="thread_456",
run_id="formatted_string",
request_id="formatted_string"
                            

                            # Mock agent
websocket = TestWebSocketConnection()  # Real WebSocket implementation

                            # Register with context
registry.register("context_agent", mock_agent)

                            # If WebSocket bridge is set, it should use proper run_id
if mock_agent.set_websocket_bridge.called:
for call in mock_agent.set_websocket_bridge.call_args_list:
args, _ = call
if len(args) > 1:
run_id = args[1]
                                        # Should either be a valid UUID or context-based ID, NOT 'registry'
assert run_id != 'registry', "Still using 'registry' placeholder"
                                        # Could be None during registration, but NOT 'registry'
if run_id is not None:
assert len(run_id) > 10, "formatted_string"


class TestExecutionEngineContext:
    """Test ExecutionEngine context handling"""

    @pytest.mark.critical
@pytest.mark.asyncio
    async def test_execution_requires_valid_context(self):
"""CRITICAL: Execution MUST require valid context"""
engine = UserExecutionEngine()

invalid_contexts = [ )
        # None user_id
AgentExecutionContext( )
agent_name="test",
user_id=None,
thread_id="thread_123",
run_id="run_123"
),
        # Empty user_id
AgentExecutionContext( )
agent_name="test",
user_id="",
thread_id="thread_123",
run_id="run_123"
),
        # 'registry' run_id
AgentExecutionContext( )
agent_name="test",
user_id="user_123",
thread_id="thread_123",
run_id="registry"
        
        

for invalid_context in invalid_contexts:
            # Should either raise an error or handle gracefully
try:
result = await engine.execute_agent(invalid_context, {"query": "test"})
                # If it doesn't raise, it should at least fail
assert not result.success, "formatted_string"
except (ValueError, AttributeError, TypeError) as e:
                    # Good - it rejected invalid context
pass

@pytest.mark.critical
@pytest.mark.asyncio
    async def test_execution_context_propagation(self):
"""CRITICAL: Context MUST propagate through execution chain"""
pass
engine = UserExecutionEngine()

                        # Track context through execution
context_chain = []

class ContextTrackingAgent:
    async def execute(self, context, input_data):
        pass
        context_chain.append({ ))
        'user_id': getattr(context, 'user_id', None),
        'run_id': getattr(context, 'run_id', None),
        'thread_id': getattr(context, 'thread_id', None)
    
        await asyncio.sleep(0)
        return AgentExecutionResult( )
        success=True,
        result="tracked",
        error=None,
        metadata={}
    

    # Register tracking agent
        registry = AgentRegistry()
        registry.register("tracker", ContextTrackingAgent())
        engine.registry = registry

    # Execute with proper context
        context = AgentExecutionContext( )
        agent_name="tracker",
        user_id="user_789",
        thread_id="thread_789",
        run_id="formatted_string"
    

        result = await engine.execute_agent(context, {"query": "test"})

    # Verify context was propagated
        assert len(context_chain) > 0, "Context was not tracked"
        tracked = context_chain[0]
        assert tracked['user_id'] == "user_789"
        assert tracked['run_id'] != 'registry'
        assert tracked['thread_id'] == "thread_789"


class TestWebSocketBridgeContext:
        """Test WebSocket bridge context handling"""

        @pytest.mark.critical
@pytest.mark.asyncio
    async def test_websocket_events_require_user_context(self):
"""CRITICAL: WebSocket events MUST have user context"""
bridge = AgentWebSocketBridge()

        # Mock WebSocket manager
websocket = TestWebSocketConnection()
bridge._websocket_manager = mock_ws_manager

        # Try to emit event without proper context
with patch.object(bridge, '_websocket_manager') as mock_manager:
            # Emit with no run_id
await bridge.emit_agent_event( )
event_type="test_event",
data={"message": "test"},
run_id=None  # Invalid!
            

            # Should either not emit or emit with validation
if mock_manager.send_to_connection.called:
call_args = mock_manager.send_to_connection.call_args
                # Check that a valid run_id was used or error was raised
assert call_args is not None

@pytest.mark.critical
@pytest.mark.asyncio
    async def test_websocket_bridge_singleton_with_user_isolation(self):
"""CRITICAL: WebSocket bridge singleton MUST isolate user contexts"""
pass
bridge1 = AgentWebSocketBridge()
bridge2 = AgentWebSocketBridge()

                    # Should be same instance (singleton)
assert bridge1 is bridge2

                    # But should handle different user contexts
user1_events = []
user2_events = []

async def mock_send_user1(connection_id, message):
pass
if 'user_001' in str(message):
user1_events.append(message)

async def mock_send_user2(connection_id, message):
pass
if 'user_002' in str(message):
user2_events.append(message)

        # Test that events are properly routed
        # This test would need actual implementation to verify


class TestSystemWideContextValidation:
        """System-wide tests for context validation"""

        @pytest.mark.critical
    def test_find_all_placeholder_patterns(self):
        """CRITICAL: Find ALL placeholder patterns in codebase"""
        backend_path = os.path.join( )
        os.path.dirname(__file__),
        '../../netra_backend'
    

        placeholder_patterns = [ )
        (r"['"]registry['"]", "registry placeholder"),
        (r"user_id\s*=\s*None", "None user_id"),
        (r"user_id:\s*None", "None user_id in dict"),
        (r"run_id\s*=\s*['"]registry['"]", "registry run_id"),
    

        issues_found = []

        for root, dirs, files in os.walk(backend_path):
        # Skip test directories
        if 'test' in root or '__pycache__' in root:
        continue

        for file in files:
        if file.endswith('.py'):
        file_path = os.path.join(root, file)
        try:
        with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        for pattern, description in placeholder_patterns:
        matches = re.findall(pattern, content)
        if matches:
                                    # Additional context check
        lines = content.split(" )
        ")
        for i, line in enumerate(lines, 1):
        if re.search(pattern, line):
                                            # Check if it's actually a problem
        if 'test' not in file.lower():
        if 'run_id' in line or 'user_id' in line:
        issues_found.append({ ))
        'file': file_path.replace(backend_path, ''),
        'line': i,
        'issue': description,
        'content': line.strip()
                                                    
        except Exception as e:
        pass

                                                        # Report issues
        if issues_found:
        report = "
        ".join([ ))
        "formatted_string"
        for issue in issues_found[:10]  # Limit to first 10
                                                            
        print("formatted_string")

        @pytest.mark.critical
@pytest.mark.asyncio
    async def test_stress_concurrent_users_no_context_mixing(self):
"""CRITICAL: Stress test - 20 concurrent users with no context mixing"""
pass
engine = UserExecutionEngine()
registry = AgentRegistry()

                                                                # Create 20 unique user contexts
user_contexts = []
for i in range(20):
context = AgentExecutionContext( )
agent_name="stress_agent",
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
                                                                    
user_contexts.append(context)

                                                                    # Track executions
execution_log = []
execution_lock = asyncio.Lock()

class StressTestAgent:
    async def execute(self, context, input_data):
        pass
        async with execution_lock:
        execution_log.append({ ))
        'user_id': context.user_id,
        'run_id': context.run_id,
        'thread_id': context.thread_id,
        'timestamp': asyncio.get_event_loop().time()
        

        # Simulate work
        await asyncio.sleep(0.05)

        await asyncio.sleep(0)
        return AgentExecutionResult( )
        success=True,
        result="formatted_string",
        error=None,
        metadata={'user_id': context.user_id}
        

        # Register agent
        registry.register("stress_agent", StressTestAgent())
        engine.registry = registry

        # Execute all concurrently
        tasks = [ )
        engine.execute_agent(context, {"query": "formatted_string"})
        for i, context in enumerate(user_contexts)
        

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify results
        successful_results = [item for item in []]
        assert len(successful_results) >= 18, "formatted_string"

        # Verify no context mixing
        user_ids_seen = set()
        run_ids_seen = set()

        for log_entry in execution_log:
        user_ids_seen.add(log_entry['user_id'])
        run_ids_seen.add(log_entry['run_id'])

            # No placeholder values
        assert log_entry['run_id'] != 'registry'
        assert log_entry['user_id'] is not None
        assert 'None' not in log_entry['user_id']

            # Should have seen all users
        assert len(user_ids_seen) >= 18, "formatted_string"
        assert len(run_ids_seen) >= 18, "formatted_string"


class TestFailFastBehavior:
        """Test fail-fast behavior when context is missing"""

        @pytest.mark.critical
    def test_context_validation_fails_fast(self):
        """CRITICAL: Context validation MUST fail fast"""

    # Test various invalid contexts
        invalid_cases = [ )
        {'user_id': None, 'thread_id': 'thread', 'run_id': 'run'},
        {'user_id': '', 'thread_id': 'thread', 'run_id': 'run'},
        {'user_id': 'user', 'thread_id': None, 'run_id': 'run'},
        {'user_id': 'user', 'thread_id': 'thread', 'run_id': None},
        {'user_id': 'user', 'thread_id': 'thread', 'run_id': 'registry'},
    

        for invalid_case in invalid_cases:
        try:
        context = UserExecutionContext( )
        user_id=invalid_case.get('user_id'),
        thread_id=invalid_case.get('thread_id'),
        run_id=invalid_case.get('run_id'),
        request_id='req_123'
            
            # Should not reach here
        assert False, "formatted_string"
        except (ValueError, TypeError) as e:
                # Good - failed fast
        assert True

        @pytest.mark.critical
@pytest.mark.asyncio
    async def test_agent_execution_fails_fast_without_context(self):
"""CRITICAL: Agent execution MUST fail fast without proper context"""

class ContextRequiringAgent:
    async def execute(self, context, input_data):
        pass
    # Validate context immediately
        if not context.user_id or context.user_id == "None":
        raise ValueError("formatted_string")
        if context.run_id == "registry":
        raise ValueError("formatted_string")

        await asyncio.sleep(0)
        return AgentExecutionResult( )
        success=True,
        result="ok",
        error=None,
        metadata={}
            

        agent = ContextRequiringAgent()

            # Test with invalid context
        websocket = TestWebSocketConnection()  # Real WebSocket implementation
        invalid_context.user_id = None
        invalid_context.run_id = "registry"

        with pytest.raises(ValueError) as exc_info:
        await agent.execute(invalid_context, {})

        assert "Invalid" in str(exc_info.value)


                # Main test runner
        if __name__ == "__main__":
                    # Run with detailed output
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "-k", "critical",  # Run only critical tests
        "--maxfail=1",  # Stop on first failure
                    
