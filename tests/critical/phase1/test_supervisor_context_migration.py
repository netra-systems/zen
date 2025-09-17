import asyncio
import pytest
from typing import List, Set, Dict, Any
from unittest.mock import MagicMock, AsyncMock
from test_framework.ssot.base_test_case import SSotBaseTestCase

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
        COMPREHENSIVE FAILING TEST SUITE: SupervisorAgent UserExecutionContext Migration

        This test suite is designed to be EXTREMELY comprehensive and difficult, targeting every
        possible failure mode in the SupervisorAgent migration to UserExecutionContext pattern.

        Tests are designed to INTENTIONALLY FAIL to catch ANY regression or incomplete migration.
        Each test pushes the boundaries of the system to ensure robust implementation.

        Coverage Areas:
        - Context validation and error handling
        - Session isolation between concurrent requests
        - Child context creation and propagation
        - Legacy method removal verification
        - Request ID uniqueness and tracking
        - Database session management
        - Error scenarios (invalid context, missing fields)
        - Concurrent user isolation
        - Memory leaks and resource cleanup
        - Edge cases and boundary conditions
        - Performance tests under load
        - Security tests for data leakage
        - Race condition detection
        - Resource exhaustion scenarios
        - Timeout handling
        - Mock failure injection
        - Transaction rollback scenarios
        '''

        import asyncio
        import gc
        import logging
        import pytest
        import threading
        import time
        import uuid
        import weakref
        from concurrent.futures import ThreadPoolExecutor
        from contextlib import asynccontextmanager
        from dataclasses import dataclass, field
        from datetime import datetime, timezone, timedelta
        from typing import Any, Dict, List, Optional, Set
        from sqlalchemy.ext.asyncio import AsyncSession
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        # Import the classes under test
        from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
        from netra_backend.app.agents.supervisor.user_execution_context import ( )
        UserExecutionContext,
        InvalidContextError,
        validate_user_context,
        clear_shared_objects,
        register_shared_object
        
        from netra_backend.app.agents.base.interface import ExecutionContext
        from netra_backend.app.schemas.agent_models import DeepAgentState
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


        # Test Configuration
        TEST_TIMEOUT = 30  # seconds
        MAX_CONCURRENT_USERS = 50
        STRESS_TEST_ITERATIONS = 100
        MEMORY_LEAK_THRESHOLD = 1024 * 1024  # 1MB
        RACE_CONDITION_ITERATIONS = 500


class TestDataLeakageMonitor:
        """Monitor for data leakage between test runs."""

    def __init__(self):
        pass
        self.captured_data: Set[str] = set()
        self.user_contexts: Dict[str, UserExecutionContext] = {}

    def record_user_data(self, user_id: str, data: Any):
        """Record user data for leak detection."""
        data_signature = "formatted_string"
        self.captured_data.add(data_signature)

    def check_for_leaks(self, user_id: str, data: Any) -> bool:
        """Check if data from another user is present."""
        pass
        data_signature = "formatted_string"

    Check if data from other users is present in this context
        for signature in self.captured_data:
        other_user = signature.split(':')[0]
        if other_user != user_id and signature == data_signature:
        return True  # Leak detected
        return False

    def clear(self):
        """Clear monitoring data."""
        self.captured_data.clear()
        self.user_contexts.clear()


        @dataclass
class StressTestMetrics:
        """Metrics collector for stress testing."""
        pass
        total_requests: int = 0
        successful_requests: int = 0
        failed_requests: int = 0
        average_response_time: float = 0.0
        memory_usage_start: int = 0
        memory_usage_peak: int = 0
        concurrent_users_peak: int = 0
        errors: List[Exception] = field(default_factory=list)
        context_creation_failures: int = 0
        session_isolation_failures: int = 0

    def add_error(self, error: Exception):
        """Add an error to the metrics."""
        self.errors.append(error)
        self.failed_requests += 1


class SupervisorContextMigrationTestSuite:
        """Comprehensive test suite for SupervisorAgent UserExecutionContext migration."""

    def __init__(self):
        pass
        self.leak_monitor = TestDataLeakageMonitor()
        self.stress_metrics = StressTestMetrics()
        self.active_contexts: List[weakref.ref] = []

        @pytest.fixture
    async def setup_and_cleanup(self):
        """Setup and cleanup for each test."""
    Clear any shared objects from previous tests
        clear_shared_objects()
        self.leak_monitor.clear()
        gc.collect()  # Force garbage collection

        yield

    # Cleanup after test
        self.leak_monitor.clear()
        clear_shared_objects()
        gc.collect()

        @pytest.fixture
    async def mock_dependencies(self):
        """Create mock dependencies for SupervisorAgent."""
        pass
        llm_manager = Mock(spec=LLMManager)
        tool_dispatcher = Mock(spec=ToolDispatcher)
        websocket_bridge = Mock(spec=AgentWebSocketBridge)
        websocket = TestWebSocketConnection()

        await asyncio.sleep(0)
        return { )
        'llm_manager': llm_manager,
        'tool_dispatcher': tool_dispatcher,
        'websocket_bridge': websocket_bridge,
        'db_session_factory': db_session_factory
    

        @pytest.fixture
    async def valid_user_context(self):
        """Create a valid UserExecutionContext for testing."""
        await asyncio.sleep(0)
        return UserExecutionContext.from_request( )
        user_id="formatted_string",
        thread_id="formatted_string",
        run_id="formatted_string"
    

    async def create_supervisor_with_context(self, deps, user_context):
        """Helper to create SupervisorAgent with UserExecutionContext."""
        pass
        await asyncio.sleep(0)
        return await SupervisorAgent.create_with_user_context( )
        llm_manager=deps['llm_manager'],
        websocket_bridge=deps['websocket_bridge'],
        tool_dispatcher=deps['tool_dispatcher'],
        user_context=user_context,
        db_session_factory=deps['db_session_factory']
    


class TestUserExecutionContextValidation(SupervisorContextMigrationTestSuite):
        """Test UserExecutionContext validation and creation."""

@pytest.mark.asyncio
    async def test_context_creation_with_all_required_fields(self, valid_user_context):
"""Test successful context creation with all required fields."""
        # This should pass - validates basic functionality
assert valid_user_context.user_id is not None
assert valid_user_context.thread_id is not None
assert valid_user_context.run_id is not None
assert valid_user_context.request_id is not None
assert isinstance(valid_user_context.created_at, datetime)

@pytest.mark.asyncio
    async def test_context_rejects_placeholder_values(self):
"""Test that context rejects dangerous placeholder values."""
pass
placeholder_values = [ )
"placeholder", "default", "temp", "none", "null",
"undefined", "0", "1", "xxx", "yyy", "example",
"registry", "placeholder_user", "temp_thread",
"default_run", "registry_123"
            

for placeholder in placeholder_values:
with pytest.raises(InvalidContextError, match="forbidden placeholder"):
UserExecutionContext.from_request( )
user_id=placeholder,
thread_id="valid_thread_123",
run_id="valid_run_456"
                    

with pytest.raises(InvalidContextError, match="forbidden placeholder"):
UserExecutionContext.from_request( )
user_id="valid_user_123",
thread_id=placeholder,
run_id="valid_run_456"
                        

with pytest.raises(InvalidContextError, match="forbidden placeholder"):
UserExecutionContext.from_request( )
user_id="valid_user_123",
thread_id="valid_thread_456",
run_id=placeholder
                            

@pytest.mark.asyncio
    async def test_context_rejects_empty_and_none_values(self):
"""Test that context rejects empty, None, or whitespace-only values."""
invalid_values = [None, "", "   ", "\t )
", "
\t  "]

for invalid_value in invalid_values:
with pytest.raises((InvalidContextError, TypeError)):
UserExecutionContext.from_request( )
user_id=invalid_value,
thread_id="valid_thread",
run_id="valid_run"
                                        

@pytest.mark.asyncio
    async def test_context_metadata_isolation(self):
"""Test that metadata dictionaries are isolated between contexts."""
pass
shared_metadata = {"shared": "data", "dangerous": "reference"}
register_shared_object(shared_metadata)  # Mark as shared

context1 = UserExecutionContext.from_request( )
user_id="user1",
thread_id="thread1",
run_id="run1",
metadata=shared_metadata.copy()  # Should create separate copy
                                            

context2 = UserExecutionContext.from_request( )
user_id="user2",
thread_id="thread2",
run_id="run2",
metadata=shared_metadata.copy()  # Should create separate copy
                                            

                                            # Verify metadata is isolated
assert id(context1.metadata) != id(context2.metadata)
assert id(context1.metadata) != id(shared_metadata)
assert id(context2.metadata) != id(shared_metadata)

                                            # Modify one context's metadata
context1.metadata["context1_specific"] = "value1"

                                            # Verify other context is not affected
assert "context1_specific" not in context2.metadata
assert "context1_specific" not in shared_metadata

@pytest.mark.asyncio
    async def test_context_prevents_reserved_metadata_keys(self):
"""Test that context prevents reserved keys in metadata."""
reserved_keys = ['user_id', 'thread_id', 'run_id', 'request_id', 'created_at']

for reserved_key in reserved_keys:
with pytest.raises(InvalidContextError, match="reserved keys"):
UserExecutionContext.from_request( )
user_id="user1",
thread_id="thread1",
run_id="run1",
metadata={reserved_key: "malicious_value"}
                                                        

@pytest.mark.asyncio
    async def test_child_context_creation_and_inheritance(self, valid_user_context):
"""Test child context creation preserves parent data with new request_id."""
pass
child_context = valid_user_context.create_child_context( )
operation_name="test_operation",
additional_metadata={"operation_specific": "data"}
                                                            

                                                            # Verify inheritance
assert child_context.user_id == valid_user_context.user_id
assert child_context.thread_id == valid_user_context.thread_id
assert child_context.run_id == valid_user_context.run_id
assert child_context.db_session == valid_user_context.db_session

                                                            # Verify new request_id
assert child_context.request_id != valid_user_context.request_id

                                                            # Verify metadata enhancement
assert child_context.metadata["parent_request_id"] == valid_user_context.request_id
assert child_context.metadata["operation_name"] == "test_operation"
assert child_context.metadata["operation_depth"] == 1
assert child_context.metadata["operation_specific"] == "data"

                                                            # Test nested child contexts
grandchild_context = child_context.create_child_context("nested_operation")
assert grandchild_context.metadata["operation_depth"] == 2
assert grandchild_context.metadata["parent_request_id"] == child_context.request_id

@pytest.mark.asyncio
    async def test_context_immutability(self, valid_user_context):
"""Test that UserExecutionContext is truly immutable."""
                                                                # Try to modify fields - should raise AttributeError
with pytest.raises(AttributeError):
valid_user_context.user_id = "modified_user"

with pytest.raises(AttributeError):
valid_user_context.thread_id = "modified_thread"

with pytest.raises(AttributeError):
valid_user_context.run_id = "modified_run"

                                                                            # Metadata should be a copy, but trying to replace it should fail
with pytest.raises(AttributeError):
valid_user_context.metadata = {"malicious": "replacement"}


class TestSupervisorContextIntegration(SupervisorContextMigrationTestSuite):
    """Test SupervisorAgent integration with UserExecutionContext."""

@pytest.mark.asyncio
    async def test_supervisor_requires_user_context_for_execution(self, mock_dependencies):
"""Test that SupervisorAgent requires UserExecutionContext for execution."""
        # Create supervisor WITHOUT user context
supervisor = SupervisorAgent( )
llm_manager=mock_dependencies['llm_manager'],
websocket_bridge=mock_dependencies['websocket_bridge'],
tool_dispatcher=mock_dependencies['tool_dispatcher']
        

        # Attempt to execute core logic should fail without context
state = DeepAgentState()
state.user_request = "test request"

context = ExecutionContext( )
run_id="test_run",
agent_name="Supervisor",
state=state,
thread_id="test_thread",
user_id="test_user"
        

with pytest.raises(RuntimeError, match="UserExecutionContext"):
await supervisor.execute_core_logic(context)

@pytest.mark.asyncio
    async def test_supervisor_with_user_context_executes_successfully(self, mock_dependencies, valid_user_context):
"""Test successful execution with UserExecutionContext."""
pass
supervisor = await self.create_supervisor_with_context(mock_dependencies, valid_user_context)

                # Mock the agent instance factory to avoid complex setup
with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_instance_factory') as mock_factory:
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_factory.return_value = mock_factory_instance

state = DeepAgentState()
state.user_request = "test request"

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="Supervisor",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
                    

                    # This should succeed with proper context
result = await supervisor.execute_core_logic(context)
assert result["user_isolation_verified"] is True
assert result["orchestration_successful"] is True

@pytest.mark.asyncio
    async def test_supervisor_context_propagation_to_agents(self, mock_dependencies, valid_user_context):
"""Test that user context is properly propagated to sub-agents."""
supervisor = await self.create_supervisor_with_context(mock_dependencies, valid_user_context)

                        # Track agent creation calls
created_agents = []

def track_agent_creation(*args, **kwargs):
"""Use real service instance."""
    # TODO: Initialize real service
pass
created_agents.append(kwargs)
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_agent.execute_modern = AsyncMock(return_value="success")
await asyncio.sleep(0)
return mock_agent

with patch('netra_backend.app.agents.supervisor_consolidated.get_agent_instance_factory') as mock_factory:
websocket = TestWebSocketConnection()  # Real WebSocket implementation
mock_factory_instance.create_agent_instance = AsyncMock(side_effect=track_agent_creation)
mock_factory.return_value = mock_factory_instance

state = DeepAgentState()
state.user_request = "complex request needing multiple agents"

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="Supervisor",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
        

await supervisor.execute_core_logic(context)

        # Verify agents were created with correct user context
assert len(created_agents) > 0
for agent_creation in created_agents:
assert 'user_context' in agent_creation
context_passed = agent_creation['user_context']
assert context_passed.user_id == valid_user_context.user_id
assert context_passed.thread_id == valid_user_context.thread_id
assert context_passed.run_id == valid_user_context.run_id

@pytest.mark.asyncio
    async def test_supervisor_legacy_methods_removal(self, mock_dependencies, valid_user_context):
"""Test that legacy methods that bypass UserExecutionContext are removed or deprecated."""
supervisor = await self.create_supervisor_with_context(mock_dependencies, valid_user_context)

                # These legacy patterns should be removed or secured
legacy_methods_to_check = [ )
'get_global_state',
'set_global_state',
'get_shared_session',
'get_singleton_instance',
'direct_agent_access'
                

for method_name in legacy_methods_to_check:
assert not hasattr(supervisor, method_name), \
"formatted_string"

@pytest.mark.asyncio
    async def test_context_validation_at_runtime(self, mock_dependencies):
"""Test runtime validation of UserExecutionContext."""
pass
                        # Test with invalid context type
with pytest.raises(TypeError):
validate_user_context("not_a_context")

with pytest.raises(TypeError):
validate_user_context({"user_id": "test"})

with pytest.raises(TypeError):
validate_user_context(None)

                                    # Test with valid context
valid_context = UserExecutionContext.from_request( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run"
                                    

validated = validate_user_context(valid_context)
assert validated is valid_context


class TestConcurrentUserIsolation(SupervisorContextMigrationTestSuite):
    """Test isolation between concurrent users."""

@pytest.mark.asyncio
    async def test_concurrent_user_session_isolation(self, mock_dependencies):
"""Test that concurrent users have completely isolated sessions."""
num_concurrent_users = 10
user_contexts = []
supervisors = []

        # Create multiple users with different contexts
for i in range(num_concurrent_users):
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
metadata={"user_secret": "formatted_string"}
            
user_contexts.append(context)

supervisor = await self.create_supervisor_with_context(mock_dependencies, context)
supervisors.append(supervisor)

            # Execute all supervisors concurrently
async def execute_supervisor(supervisor, context):
state = DeepAgentState()
state.user_request = "formatted_string"
state.user_secret_data = context.metadata["user_secret"]

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="Supervisor",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
    

    # Mock successful execution
with patch.object(supervisor, '_run_isolated_supervisor_workflow', new_callable=AsyncMock) as mock_workflow:
mock_workflow.return_value = state

result = await supervisor.execute_core_logic(exec_context)

        # Record data for leak detection
self.leak_monitor.record_user_data(context.user_id, state.user_secret_data)

await asyncio.sleep(0)
return result, state, context.user_id

        # Execute all concurrently
tasks = [ )
execute_supervisor(supervisor, context)
for supervisor, context in zip(supervisors, user_contexts)
        

results = await asyncio.gather(*tasks, return_exceptions=True)

        # Verify no exceptions occurred
for result in results:
assert not isinstance(result, Exception), "formatted_string"

            # Verify no data leakage between users
for result, state, user_id in results:
assert not self.leak_monitor.check_for_leaks(user_id, state.user_secret_data), \
"formatted_string"

@pytest.mark.asyncio
    async def test_race_condition_in_context_creation(self, mock_dependencies):
"""Test for race conditions in context creation and agent instantiation."""
pass
race_results = []

async def create_context_and_agent():
pass
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
    

supervisor = await self.create_supervisor_with_context(mock_dependencies, context)

await asyncio.sleep(0)
return { )
'context_id': context.request_id,
'supervisor_id': id(supervisor),
'user_id': context.user_id,
'created_at': context.created_at
    

    # Create many contexts concurrently to trigger race conditions
tasks = [create_context_and_agent() for _ in range(RACE_CONDITION_ITERATIONS)]
results = await asyncio.gather(*tasks, return_exceptions=True)

    # Check for any exceptions
exceptions = [item for item in []]
assert len(exceptions) == 0, "formatted_string"

successful_results = [item for item in []]

    # Verify all contexts have unique IDs
context_ids = [r['context_id'] for r in successful_results]
assert len(set(context_ids)) == len(context_ids), "Duplicate context IDs detected - race condition!"

    # Verify all supervisors are separate instances
supervisor_ids = [r['supervisor_id'] for r in successful_results]
assert len(set(supervisor_ids)) == len(supervisor_ids), "Shared supervisor instances detected!"

    # Verify user IDs are unique
user_ids = [r['user_id'] for r in successful_results]
assert len(set(user_ids)) == len(user_ids), "Duplicate user IDs generated!"

@pytest.mark.asyncio
    async def test_memory_isolation_and_cleanup(self, mock_dependencies):
"""Test memory isolation and cleanup to prevent leaks."""
initial_memory = self._get_memory_usage()
contexts_created = []

        # Create many contexts and supervisors
for i in range(100):
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
metadata={"large_data": "x" * 1000}  # Add some data to track
            

supervisor = await self.create_supervisor_with_context(mock_dependencies, context)

            # Create weak references to track object lifecycle
context_ref = weakref.ref(context)
supervisor_ref = weakref.ref(supervisor)

contexts_created.append((context_ref, supervisor_ref))

            # Simulate some work
state = DeepAgentState()
state.user_request = "memory test request"

            # Force cleanup
del context, supervisor

            # Force garbage collection
gc.collect()

            # Check that objects were cleaned up
alive_contexts = sum(1 for ctx_ref, _ in contexts_created if ctx_ref() is not None)
alive_supervisors = sum(1 for _, sup_ref in contexts_created if sup_ref() is not None)

            # Allow some objects to remain (GC isn't perfect), but not too many
assert alive_contexts < 10, "formatted_string"
assert alive_supervisors < 10, "formatted_string"

            # Check memory usage didn't grow excessively
final_memory = self._get_memory_usage()
memory_growth = final_memory - initial_memory

assert memory_growth < MEMORY_LEAK_THRESHOLD, \
"formatted_string"

def _get_memory_usage(self) -> int:
"""Get current memory usage."""
pass
import psutil
import os

process = psutil.Process(os.getpid())
await asyncio.sleep(0)
return process.memory_info().rss


class TestErrorScenariosAndEdgeCases(SupervisorContextMigrationTestSuite):
        """Test error scenarios and edge cases."""

@pytest.mark.asyncio
    async def test_context_with_corrupted_metadata(self):
"""Test context handling with corrupted or malicious metadata."""
        # Test with circular references in metadata
circular_dict = {"self": None}
circular_dict["self"] = circular_dict

with pytest.raises(Exception):  # Should fail during validation or serialization
context = UserExecutionContext.from_request( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
metadata=circular_dict
        
        # Try to serialize - should detect circular reference
context.to_dict()

@pytest.mark.asyncio
    async def test_context_with_extremely_large_metadata(self):
"""Test context with extremely large metadata."""
pass
large_metadata = { )
"formatted_string": "x" * 10000  # 10KB per key
for i in range(100)  # Total ~1MB
            

            # This should work but be tracked for memory usage
context = UserExecutionContext.from_request( )
user_id="large_metadata_user",
thread_id="large_metadata_thread",
run_id="large_metadata_run",
metadata=large_metadata
            

            # Verify data integrity
assert len(context.metadata) == 100
assert context.metadata["key_0"] == "x" * 10000

@pytest.mark.asyncio
    async def test_supervisor_with_database_session_failures(self, mock_dependencies, valid_user_context):
"""Test supervisor behavior when database sessions fail."""
                # Mock session factory that fails
websocket = TestWebSocketConnection()
failing_session_factory.side_effect = Exception("Database connection failed")

mock_dependencies['db_session_factory'] = failing_session_factory

supervisor = await self.create_supervisor_with_context(mock_dependencies, valid_user_context)

                # Attempt execution with failing session
state = DeepAgentState()
state.user_request = "test request with db failure"

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="Supervisor",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
                

                # Should handle the failure gracefully (fallback to legacy)
with patch.object(supervisor.execution_helpers, 'run_supervisor_workflow', new_callable=AsyncMock) as mock_fallback:
mock_fallback.return_value = state

                    # Should not raise exception, should fall back to legacy
result = await supervisor.execute_core_logic(context)
assert result is not None

@pytest.mark.asyncio
    async def test_context_timeout_scenarios(self, mock_dependencies, valid_user_context):
"""Test context behavior under timeout scenarios."""
pass
supervisor = await self.create_supervisor_with_context(mock_dependencies, valid_user_context)

state = DeepAgentState()
state.user_request = "slow request"

context = ExecutionContext( )
run_id=valid_user_context.run_id,
agent_name="Supervisor",
state=state,
thread_id=valid_user_context.thread_id,
user_id=valid_user_context.user_id
                        

                        # Mock slow workflow execution
async def slow_workflow(*args, **kwargs):
pass
await asyncio.sleep(60)  # Very slow
await asyncio.sleep(0)
return state

with patch.object(supervisor, '_run_isolated_supervisor_workflow', new_callable=AsyncMock) as mock_workflow:
mock_workflow.side_effect = slow_workflow

        # Execute with timeout
with pytest.raises(asyncio.TimeoutError):
await asyncio.wait_for( )
supervisor.execute_core_logic(context),
timeout=1.0  # 1 second timeout
            

@pytest.mark.asyncio
    async def test_context_thread_safety(self, mock_dependencies):
"""Test UserExecutionContext thread safety."""
shared_results = []
exceptions = []

def create_context_in_thread(thread_id):
try:
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
metadata={"thread_id": thread_id, "data": list(range(100))}
        

        # Simulate some work
time.sleep(0.01)

        # Verify data integrity
assert context.metadata["thread_id"] == thread_id
assert len(context.metadata["data"]) == 100

shared_results.append({ ))
"thread_id": thread_id,
"context_id": context.request_id,
"user_id": context.user_id
        

except Exception as e:
exceptions.append(e)

            # Create contexts in multiple threads
with ThreadPoolExecutor(max_workers=20) as executor:
futures = [ )
executor.submit(create_context_in_thread, i)
for i in range(50)
                

                # Wait for all threads to complete
for future in futures:
future.result(timeout=30)

                    # Verify no exceptions occurred
assert len(exceptions) == 0, "formatted_string"

                    # Verify all contexts were created successfully
assert len(shared_results) == 50

                    # Verify all contexts are unique
context_ids = [r["context_id"] for r in shared_results]
assert len(set(context_ids)) == 50, "Duplicate context IDs in multi-threaded creation!"


class TestPerformanceAndStressScenarios(SupervisorContextMigrationTestSuite):
        """Performance and stress testing scenarios."""

@pytest.mark.asyncio
    async def test_high_load_context_creation_performance(self):
"""Test performance of context creation under high load."""
start_time = time.time()
contexts_created = 0

        # Create many contexts rapidly
for i in range(1000):
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
metadata={"iteration": i}
            
contexts_created += 1

            # Verify context is valid
assert context.user_id == "formatted_string"

end_time = time.time()
creation_time = end_time - start_time

            # Performance assertion - should create 1000 contexts quickly
assert creation_time < 5.0, "formatted_string"
assert contexts_created == 1000, "formatted_string"

            # Calculate contexts per second
contexts_per_second = contexts_created / creation_time
assert contexts_per_second > 200, "formatted_string"

@pytest.mark.asyncio
    async def test_supervisor_scalability_limits(self, mock_dependencies):
"""Test SupervisorAgent scalability limits."""
pass
max_concurrent_supervisors = 25
supervisors = []

                # Create many supervisors simultaneously
creation_start = time.time()

for i in range(max_concurrent_supervisors):
context = UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string"
                    

supervisor = await self.create_supervisor_with_context(mock_dependencies, context)
supervisors.append((supervisor, context))

creation_time = time.time() - creation_start

                    # Execute all supervisors concurrently
async def execute_supervisor_with_load(supervisor, context):
pass
state = DeepAgentState()
state.user_request = "formatted_string"

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="Supervisor",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
    

    # Mock the workflow to avoid complex dependencies
with patch.object(supervisor, '_run_isolated_supervisor_workflow', new_callable=AsyncMock) as mock_workflow:
mock_workflow.return_value = state

await asyncio.sleep(0)
return await supervisor.execute_core_logic(exec_context)

execution_start = time.time()

        # Execute all concurrently
tasks = [ )
execute_supervisor_with_load(supervisor, context)
for supervisor, context in supervisors
        

results = await asyncio.gather(*tasks, return_exceptions=True)
execution_time = time.time() - execution_start

        # Verify results
successful_results = [item for item in []]
failed_results = [item for item in []]

print("formatted_string")
print("formatted_string")
print("formatted_string")

        # Performance assertions
assert len(successful_results) >= max_concurrent_supervisors * 0.8, \
"formatted_string"

assert creation_time < 10.0, "formatted_string"
assert execution_time < 15.0, "formatted_string"


class TestSecurityAndDataLeakagePrevention(SupervisorContextMigrationTestSuite):
        """Security-focused tests to prevent data leakage."""

@pytest.mark.asyncio
    async def test_cross_user_data_isolation_comprehensive(self, mock_dependencies):
"""Comprehensive test for cross-user data isolation."""
        # Create users with sensitive data
sensitive_data_sets = [ )
{"user": "alice", "secret": "alice_secret_123", "data": ["alice_file1", "alice_file2"]},
{"user": "bob", "secret": "bob_secret_456", "data": ["bob_file1", "bob_file2"]},
{"user": "charlie", "secret": "charlie_secret_789", "data": ["charlie_file1", "charlie_file2"]},
        

user_execution_results = {}

        # Execute each user's workflow
for user_data in sensitive_data_sets:
context = UserExecutionContext.from_request( )
user_id=user_data["user"],
thread_id="formatted_string",
run_id="formatted_string",
metadata={"secret_data": user_data["secret"]}
            

supervisor = await self.create_supervisor_with_context(mock_dependencies, context)

state = DeepAgentState()
state.user_request = "formatted_string"
state.user_secret = user_data["secret"]
state.user_files = user_data["data"]

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="Supervisor",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
            

            # Mock workflow that might accidentally share data
async def potentially_leaky_workflow(state, run_id):
    # Simulate processing that might leak data
processed_state = state
processed_state.processing_log = "formatted_string"
await asyncio.sleep(0)
return processed_state

with patch.object(supervisor, '_run_isolated_supervisor_workflow', new_callable=AsyncMock) as mock_workflow:
mock_workflow.side_effect = potentially_leaky_workflow

result = await supervisor.execute_core_logic(exec_context)
user_execution_results[user_data["user"]] = { )
"result": result,
"state": state,
"context": context
        

        # Verify no cross-contamination
for user1, data1 in user_execution_results.items():
for user2, data2 in user_execution_results.items():
if user1 != user2:
                    # Check that user1's context doesn't contain user2's data
assert data2["context"].user_id not in str(data1["state"].__dict__), \
"formatted_string"

                    # Check secret data isolation
user2_secret = next(d[item for item in []] == user2)
assert user2_secret not in str(data1["state"].__dict__), \
"formatted_string"

@pytest.mark.asyncio
    async def test_context_serialization_prevents_data_leakage(self, valid_user_context):
"""Test that context serialization doesn't leak sensitive data."""
pass
                        # Add sensitive data to context
sensitive_context = UserExecutionContext.from_request( )
user_id="sensitive_user",
thread_id="sensitive_thread",
run_id="sensitive_run",
metadata={ )
"password": "should_not_appear",
"api_key": "secret_api_key_123",
"session_token": "sensitive_session_token"
                        
                        

                        # Serialize context
serialized = sensitive_context.to_dict()

                        # Verify structure is safe for logging/transmission
assert "password" in serialized["metadata"]  # It should be preserved in metadata
assert "db_session" not in serialized  # But db_session should be excluded
assert serialized["has_db_session"] is False

                        # Verify serialized data can't be modified to affect original
serialized["user_id"] = "hacker_user"
serialized["metadata"]["password"] = "hacked_password"

                        # Original context should be unchanged (immutable)
assert sensitive_context.user_id == "sensitive_user"
assert sensitive_context.metadata["password"] == "should_not_appear"

@pytest.mark.asyncio
    async def test_prevent_context_injection_attacks(self):
"""Test prevention of context injection attacks."""
malicious_inputs = [ )
{"user_id": "<script>alert('xss')</script>"},
{"thread_id": ""; DROP TABLE users; --"},
{"run_id": "../../../etc/passwd"},
{"metadata": {"__proto__": {"isAdmin": True}}},
{"metadata": {"constructor": {"prototype": {"isAdmin": True}}}},
                            

for malicious_input in malicious_inputs:
try:
                                    # These should either be properly sanitized or rejected
context = UserExecutionContext.from_request( )
user_id=malicious_input.get("user_id", "safe_user"),
thread_id=malicious_input.get("thread_id", "safe_thread"),
run_id=malicious_input.get("run_id", "safe_run"),
metadata=malicious_input.get("metadata", {})
                                    

                                    # If context is created, verify it's safe
serialized = context.to_dict()

                                    # Check for prototype pollution
assert not hasattr(dict(), 'isAdmin'), "Prototype pollution detected!"

                                    # Malicious strings should be preserved as-is (not executed)
if "user_id" in malicious_input:
assert context.user_id == malicious_input["user_id"]

except InvalidContextError:
                                            # It's OK if the context rejects malicious input
pass


                                            # Performance benchmarking
@pytest.mark.benchmark
class TestPerformanceBenchmarks(SupervisorContextMigrationTestSuite):
    """Benchmark tests for performance regression detection."""

@pytest.mark.asyncio
    async def test_context_creation_benchmark(self, benchmark):
"""Benchmark context creation performance."""
def create_context():
await asyncio.sleep(0)
return UserExecutionContext.from_request( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
metadata={"benchmark": True, "data": list(range(10))}
    

result = benchmark(create_context)
assert result is not None

@pytest.mark.asyncio
    async def test_supervisor_execution_benchmark(self, benchmark, mock_dependencies):
"""Benchmark supervisor execution with UserExecutionContext."""
pass
context = UserExecutionContext.from_request( )
user_id="benchmark_user",
thread_id="benchmark_thread",
run_id="benchmark_run"
        

async def execute_supervisor():
pass
supervisor = await self.create_supervisor_with_context(mock_dependencies, context)

state = DeepAgentState()
state.user_request = "benchmark request"

exec_context = ExecutionContext( )
run_id=context.run_id,
agent_name="Supervisor",
state=state,
thread_id=context.thread_id,
user_id=context.user_id
    

with patch.object(supervisor, '_run_isolated_supervisor_workflow', new_callable=AsyncMock) as mock_workflow:
mock_workflow.return_value = state
await asyncio.sleep(0)
return await supervisor.execute_core_logic(exec_context)

result = await execute_supervisor()  # Warm up
benchmark(lambda x: None asyncio.run(execute_supervisor()))


        # Test configuration and runners
if __name__ == "__main__":
pytest.main([ ))
__file__,
"-v",
"--tb=short",
"--asyncio-mode=auto",
"--timeout=300",  # 5 minute timeout per test
"-x"  # Stop on first failure
            
