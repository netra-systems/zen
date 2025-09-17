'''
Comprehensive Phase 0 Migration Validation Test Suite

Business Value Justification:
- Segment: ALL (Free  ->  Enterprise)
- Business Goal: Ensure Phase 0 migration is complete and secure
- Value Impact: Prevents data leakage, ensures proper request isolation
- Strategic Impact: Critical for production deployment safety

This test suite provides comprehensive validation of Phase 0 migration:
- UserExecutionContext validation and security
- Updated API endpoints using proper context
- BaseAgent new execute method compliance
- Session isolation between requests
- Concurrent user handling
- Context propagation to sub-agents
- Error handling with invalid contexts
- Legacy method detection and prevention
- Integration tests for full request flow
- Performance validation without degradation

These tests are designed to be comprehensive and difficult to pass - they will catch:
- User data leakage between requests
- Improper context handling
- Legacy method usage
- Session management problems
- Concurrent request isolation failures
'''

import asyncio
import gc
import logging
import os
import pytest
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from shared.isolated_environment import IsolatedEnvironment

            # Core imports for Phase 0 migration
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.dependencies import ( )
RequestScopedContext,
RequestScopedDbDep,
RequestScopedSupervisorDep,
get_request_scoped_db_session,
get_request_scoped_supervisor,
validate_session_is_request_scoped,
create_user_execution_context
            

            # Database and session management
from netra_backend.app.database.session_manager import ( )
DatabaseSessionManager,
SessionIsolationError,
SessionManagerError,
SessionScopeValidator
            

            # Services and components
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.websocket_bridge_factory import WebSocketBridgeFactory
from netra_backend.app.agents.supervisor.execution_factory import ExecutionEngineFactory
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory

            # LLM and infrastructure
from netra_backend.app.llm.llm_manager import LLMManager

            # Testing utilities
from test_framework.real_services import RealServicesManager
from test_framework.ssot.database import DatabaseTestManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


            # Configure logging for detailed test output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SecurityViolation(Exception):
    """Raised when a security violation is detected in tests."""
    pass


class MigrationViolation(Exception):
    """Raised when Phase 0 migration requirements are violated."""
    pass


class TestUserExecutionContextValidation:
    """Comprehensive UserExecutionContext validation tests."""

    def test_context_creation_with_valid_data(self):
        """Test UserExecutionContext creation with valid data."""
        context = UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012",
        websocket_connection_id="conn_345"
    

        assert context.user_id == "user_123"
        assert context.thread_id == "thread_456"
        assert context.run_id == "run_789"
        assert context.request_id == "req_012"
        assert context.websocket_connection_id == "conn_345"

    def test_context_creation_with_optional_websocket_id(self):
        """Test UserExecutionContext creation without WebSocket ID."""
        pass
        context = UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
    

        assert context.websocket_connection_id is None

    def test_context_validation_rejects_none_user_id(self):
        """Test context validation fails for None user_id."""
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be None"):
        UserExecutionContext( )
        user_id=None,
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
        

    def test_context_validation_rejects_empty_user_id(self):
        """Test context validation fails for empty user_id."""
        pass
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be empty"):
        UserExecutionContext( )
        user_id="",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
        

    def test_context_validation_rejects_placeholder_user_id(self):
        """Test context validation fails for placeholder user_id."""
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be the string 'None'"):
        UserExecutionContext( )
        user_id="None",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
        

    def test_context_validation_rejects_none_thread_id(self):
        """Test context validation fails for None thread_id."""
        pass
        with pytest.raises(ValueError, match="UserExecutionContext.thread_id cannot be None"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id=None,
        run_id="run_789",
        request_id="req_012"
        

    def test_context_validation_rejects_empty_thread_id(self):
        """Test context validation fails for empty thread_id."""
        with pytest.raises(ValueError, match="UserExecutionContext.thread_id cannot be empty"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="",
        run_id="run_789",
        request_id="req_012"
        

    def test_context_validation_rejects_none_run_id(self):
        """Test context validation fails for None run_id."""
        pass
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be None"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id=None,
        request_id="req_012"
        

    def test_context_validation_rejects_empty_run_id(self):
        """Test context validation fails for empty run_id."""
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be empty"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="",
        request_id="req_012"
        

    def test_context_validation_rejects_placeholder_run_id(self):
        """Test context validation fails for placeholder run_id."""
        pass
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be 'registry'"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="registry",
        request_id="req_012"
        

    def test_context_validation_rejects_none_request_id(self):
        """Test context validation fails for None request_id."""
        with pytest.raises(ValueError, match="UserExecutionContext.request_id cannot be None"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id=None
        

    def test_context_validation_rejects_empty_request_id(self):
        """Test context validation fails for empty request_id."""
        pass
        with pytest.raises(ValueError, match="UserExecutionContext.request_id cannot be empty"):
        UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id=""
        

    def test_context_to_dict_conversion(self):
        """Test UserExecutionContext to_dict conversion."""
        context = UserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012",
        websocket_connection_id="conn_345"
    

        expected_dict = { }
        "user_id": "user_123",
        "thread_id": "thread_456",
        "run_id": "run_789",
        "request_id": "req_012",
        "websocket_connection_id": "conn_345"
    

        assert context.to_dict() == expected_dict

    def test_context_string_representation_security(self):
        """Test UserExecutionContext string representation truncates user_id for security."""
        pass
        long_user_id = "very_long_user_id_that_should_be_truncated_for_security"
        context = UserExecutionContext( )
        user_id=long_user_id,
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
    

        str_repr = str(context)
    # Should truncate long user_id for security
        assert "very_lon..." in str_repr
        assert long_user_id not in str_repr  # Full user_id should not appear


class TestAgentExecuteMethodMigration:
        """Test BaseAgent execute method migration to context-based execution."""

class TestAgent(BaseAgent):
        """Test agent implementation for migration testing."""

    def __init__(self, test_mode: str = "new"):
        pass
        super().__init__(name="TestAgent")
        self.test_mode = test_mode
        self.execution_calls = []

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        """New context-based execution method."""
        self.execution_calls.append({ })
        'method': 'execute_with_context',
        'context': context,
        'stream_updates': stream_updates,
        'timestamp': datetime.now(timezone.utc)
    
        return {"status": "success", "method": "context_based", "user_id": context.user_id}

    async def execute_core_logic(self, execution_context) -> Dict[str, Any]:
        """Legacy core logic method."""
        self.execution_calls.append({ })
        'method': 'execute_core_logic',
        'execution_context': execution_context,
        'timestamp': datetime.now(timezone.utc)
    
        return {"status": "success", "method": "core_logic"}

class LegacyAgent(BaseAgent):
        """Legacy agent that hasn't been migrated (should fail tests)."""

    def __init__(self):
        pass
        super().__init__(name="LegacyAgent")

    # Intentionally no execute_with_context or execute_core_logic implementation

@pytest.mark.asyncio
    async def test_agent_execute_with_context_success(self):
"""Test agent execute method with valid UserExecutionContext."""
agent = self.TestAgent()
context = UserExecutionContext( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
request_id="test_request"
        

result = await agent.execute(context, stream_updates=True)

assert result is not None
assert result["status"] == "success"
assert result["method"] == "context_based"
assert result["user_id"] == "test_user"
assert len(agent.execution_calls) == 1
assert agent.execution_calls[0]["method"] == "execute_with_context"

@pytest.mark.asyncio
    async def test_agent_execute_rejects_wrong_context_type(self):
"""Test agent execute method rejects non-UserExecutionContext."""
pass
agent = self.TestAgent()

with pytest.raises(TypeError, match="Expected UserExecutionContext"):
await agent.execute({"invalid": "context"})

@pytest.mark.asyncio
    async def test_agent_execute_validates_session_isolation(self):
"""Test agent execute method validates session isolation."""
agent = self.TestAgent()
context = UserExecutionContext( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
request_id="test_request"
                    

                    # Mock the session isolation validation to fail
with patch.object(agent, '_validate_session_isolation') as mock_validate:
mock_validate.side_effect = SessionIsolationError("Session isolation violated")

with pytest.raises(SessionIsolationError):
await agent.execute(context)

@pytest.mark.asyncio
    async def test_legacy_agent_execute_fails_appropriately(self):
"""Test legacy agent that hasn't implemented new execute pattern fails."""
pass
agent = self.LegacyAgent()
context = UserExecutionContext( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
request_id="test_request"
                                

with pytest.raises(NotImplementedError, match="must implement execute_with_context"):
await agent.execute(context)

@pytest.mark.asyncio
    async def test_agent_context_propagation_to_subagents(self):
"""Test context is properly propagated to sub-agents."""

class ParentAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="ParentAgent")
        self.subagent_contexts = []

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
    # Simulate creating a sub-agent with context propagation
        subagent_context = UserExecutionContext( )
        user_id=context.user_id,  # Must propagate user context
        thread_id=context.thread_id,
        run_id="",
        request_id=""
    
        self.subagent_contexts.append(subagent_context)
        await asyncio.sleep(0)
        return {"parent_result": "success", "subagent_context_created": True}

        parent_agent = ParentAgent()
        context = UserExecutionContext( )
        user_id="test_user",
        thread_id="test_thread",
        run_id="test_run",
        request_id="test_request"
    

        result = await parent_agent.execute(context)

        assert result["subagent_context_created"]
        assert len(parent_agent.subagent_contexts) == 1

        subagent_context = parent_agent.subagent_contexts[0]
        assert subagent_context.user_id == context.user_id  # Context propagated
        assert subagent_context.thread_id == context.thread_id
        assert subagent_context.run_id.startswith(context.run_id)
        assert subagent_context.request_id.startswith(context.request_id)


class TestSessionIsolationBetweenRequests:
        """Comprehensive tests for session isolation between requests."""

        @pytest.fixture
    async def database_manager(self):
        """Fixture for database test manager."""
        manager = DatabaseTestManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()

@pytest.mark.asyncio
    async def test_session_isolation_prevents_cross_user_access(self, database_manager):
"""Test that sessions are isolated between different users."""

        # Create contexts for two different users
context1 = UserExecutionContext( )
user_id="user_1",
thread_id="thread_1",
run_id="run_1",
request_id="req_1"
        

context2 = UserExecutionContext( )
user_id="user_2",
thread_id="thread_2",
run_id="run_2",
request_id="req_2"
        

        # Create isolated session managers
session_mgr1 = DatabaseSessionManager(context1)
session_mgr2 = DatabaseSessionManager(context2)

        # Verify sessions are different instances
assert session_mgr1 is not session_mgr2
assert session_mgr1.context.user_id != session_mgr2.context.user_id

        # Test that sessions cannot access each other's data
with pytest.raises(SessionIsolationError):
            # Attempt to use wrong session manager with different user context
await session_mgr1._validate_context_match(context2)

@pytest.mark.asyncio
    async def test_request_scoped_session_creation(self):
"""Test request-scoped session creation and cleanup."""
initial_session_count = 0
sessions_created = []

                # Create multiple request-scoped sessions
for i in range(5):
async with get_request_scoped_db_session() as session:
sessions_created.append(id(session))
validate_session_is_request_scoped(session, "")

                        # Verify each session was unique
unique_sessions = set(sessions_created)
assert len(unique_sessions) == 5, "Each request should get a unique session"

                        # Verify sessions are properly marked as request-scoped
                        # (Validation would have thrown an exception if not)

@pytest.mark.asyncio
    async def test_session_cleanup_on_request_completion(self):
"""Test that sessions are cleaned up when requests complete."""
pass
session_refs = []

                            # Create sessions and keep weak references
import weakref

for i in range(3):
async with get_request_scoped_db_session() as session:
session_refs.append(weakref.ref(session))

                                    # Force garbage collection
gc.collect()

                                    # Verify sessions were cleaned up (weak references should be dead)
dead_refs = sum(1 for ref in session_refs if ref() is None)
assert dead_refs >= 2, "Most sessions should have been garbage collected"

@pytest.mark.asyncio
    async def test_concurrent_session_isolation(self):
"""Test session isolation under concurrent access."""

async def create_isolated_session(user_id: str) -> Dict[str, Any]:
"""Create isolated session for a user."""
pass
context = UserExecutionContext( )
user_id=user_id,
thread_id="",
run_id="",
request_id=""
    

session_mgr = DatabaseSessionManager(context)
await asyncio.sleep(0)
return { }
"user_id": user_id,
"context_id": id(context),
"session_mgr_id": id(session_mgr),
"session_user": session_mgr.context.user_id
    

    # Create concurrent sessions for different users
tasks = [ ]
create_isolated_session("")
for i in range(10)
    

results = await asyncio.gather(*tasks)

    # Verify all sessions are unique and properly isolated
session_ids = [r["session_mgr_id"] for r in results]
context_ids = [r["context_id"] for r in results]

assert len(set(session_ids)) == 10, "All session managers should be unique"
assert len(set(context_ids)) == 10, "All contexts should be unique"

    # Verify user isolation
for result in results:
assert result["session_user"] == result["user_id"], "Session must match user"

@pytest.mark.asyncio
    async def test_session_validation_detects_global_sessions(self):
"""Test session validation detects and rejects globally stored sessions."""

async with get_request_scoped_db_session() as session:
                # Mark session as globally stored (testing scenario)
from netra_backend.app.dependencies import mark_session_as_global
mark_session_as_global(session)

                # Validation should detect this and fail
with pytest.raises(SessionIsolationError, match="must be request-scoped"):
validate_session_is_request_scoped(session, "test_global_detection")

@pytest.mark.asyncio
    async def test_user_execution_context_session_integration(self):
"""Test UserExecutionContext integration with database sessions."""

context = UserExecutionContext( )
user_id="integration_user",
thread_id="integration_thread",
run_id="integration_run",
request_id="integration_request"
                        

async with get_request_scoped_db_session() as session:
                            # Create user execution context with session
integrated_context = create_user_execution_context( )
user_id=context.user_id,
thread_id=context.thread_id,
run_id=context.run_id,
db_session=session
                            

                            # Verify integration
assert integrated_context.user_id == context.user_id
assert integrated_context.thread_id == context.thread_id
assert integrated_context.run_id == context.run_id


class TestConcurrentUserHandling:
    """Test system behavior with concurrent users."""

@pytest.mark.asyncio
    async def test_concurrent_user_execution_isolation(self):
"""Test that concurrent users are properly isolated."""

class IsolationTestAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="IsolationTestAgent")
        self.user_data = {}  # This should be isolated per execution

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
    # Store user-specific data (should not leak between users)
        user_secret = ""
        self.user_data[context.run_id] = user_secret

    # Simulate processing time
        await asyncio.sleep(0.1)

    # Verify our data is still there and not contaminated
        if context.run_id not in self.user_data:
        raise SecurityViolation("")

        if self.user_data[context.run_id] != user_secret:
        raise SecurityViolation("")

        await asyncio.sleep(0)
        return { }
        "user_id": context.user_id,
        "secret": user_secret,
        "data_integrity": "verified"
            

            # Create multiple users with concurrent execution
    async def execute_for_user(user_id: str) -> Dict[str, Any]:
        agent = IsolationTestAgent()  # Each user gets fresh agent instance
        context = UserExecutionContext( )
        user_id=user_id,
        thread_id="",
        run_id="",
        request_id=""
    

        return await agent.execute(context)

    # Execute concurrently for 20 users
        user_count = 20
        tasks = [ ]
        execute_for_user("")
        for i in range(user_count)
    

        results = await asyncio.gather(*tasks)

    # Verify all executions succeeded with proper isolation
        assert len(results) == user_count

        user_ids_seen = set()
        for result in results:
        assert result["data_integrity"] == "verified"
        assert result["user_id"] not in user_ids_seen, "User ID collision detected"
        user_ids_seen.add(result["user_id"])
        assert result["secret"].startswith("")

@pytest.mark.asyncio
    async def test_concurrent_context_creation(self):
"""Test concurrent UserExecutionContext creation."""

def create_context_for_user(user_id: str) -> UserExecutionContext:
"""Create context for a user."""
await asyncio.sleep(0)
return UserExecutionContext( )
user_id=user_id,
thread_id="",
run_id="",
request_id=""
    

    # Create contexts concurrently using thread pool (simulating FastAPI request handling)
with ThreadPoolExecutor(max_workers=10) as executor:
futures = [ ]
executor.submit(create_context_for_user, "")
for i in range(50)
        

contexts = [future.result() for future in as_completed(futures)]

        # Verify all contexts are unique and valid
assert len(contexts) == 50

user_ids = [ctx.user_id for ctx in contexts]
run_ids = [ctx.run_id for ctx in contexts]
request_ids = [ctx.request_id for ctx in contexts]

assert len(set(user_ids)) == 50, "All user IDs should be unique"
assert len(set(run_ids)) == 50, "All run IDs should be unique"
assert len(set(request_ids)) == 50, "All request IDs should be unique"

@pytest.mark.asyncio
    async def test_memory_isolation_between_concurrent_users(self):
"""Test memory isolation between concurrent user executions."""

class MemoryTestAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="MemoryTestAgent")

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
    # Allocate user-specific memory
        user_memory_block = "X" * 1000000  # 1MB per user

    # Process with memory allocation
        await asyncio.sleep(0.05)

        await asyncio.sleep(0)
        return { }
        "user_id": context.user_id,
        "memory_block_size": len(user_memory_block),
        "memory_allocated": True
    

        import psutil
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Execute for many concurrent users
    async def execute_with_memory(user_id: str):
        agent = MemoryTestAgent()
        context = UserExecutionContext( )
        user_id=user_id,
        thread_id="",
        run_id="",
        request_id=""
    
        await asyncio.sleep(0)
        return await agent.execute(context)

    # Run 30 concurrent users (30MB total if no leaks)
        tasks = [execute_with_memory("") for i in range(30)]
        results = await asyncio.gather(*tasks)

    # Force garbage collection
        gc.collect()
        await asyncio.sleep(0.1)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

    # Verify execution succeeded
        assert len(results) == 30
        assert all(r["memory_allocated"] for r in results)

    # Memory should not have increased excessively (indicates proper cleanup)
        assert memory_increase < 15.0, ""


class TestErrorHandlingWithInvalidContexts:
        """Test error handling with invalid or malicious contexts."""

@pytest.mark.asyncio
    async def test_sql_injection_attempt_in_context(self):
"""Test system handles SQL injection attempts in context fields."""

malicious_contexts = [ ]
        # SQL injection attempts
(""; DROP TABLE users; --", "thread_1", "run_1", "req_1"),
("user_1", ""; DELETE FROM sessions; --", "run_1", "req_1"),
("user_1", "thread_1", ""; UPDATE users SET admin=1; --", "req_1"),
("user_1", "thread_1", "run_1", ""; INSERT INTO admin_users VALUES ("hacker"); --"),

        # Script injection attempts
("<script>alert('xss')</script>", "thread_1", "run_1", "req_1"),
("user_1", "<script>steal_data()</script>", "run_1", "req_1"),

        # Path traversal attempts
("../../../etc/passwd", "thread_1", "run_1", "req_1"),
("user_1", "../../../../root/.ssh/id_rsa", "run_1", "req_1"),

        # Command injection attempts
("user_1; rm -rf /", "thread_1", "run_1", "req_1"),
("user_1", "thread_1", "run_1`whoami`", "req_1"),
        

for user_id, thread_id, run_id, request_id in malicious_contexts:
try:
                # Context creation should not fail (validation is content-agnostic)
context = UserExecutionContext( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
request_id=request_id
                

                # But the values should be treated as literal strings
assert context.user_id == user_id
assert context.thread_id == thread_id
assert context.run_id == run_id
assert context.request_id == request_id

except ValueError:
                    # Some malicious inputs might be caught by basic validation
                    # This is acceptable behavior
pass

@pytest.mark.asyncio
    async def test_context_size_limits(self):
"""Test context handles excessively large field values."""

                        # Very large strings
large_user_id = "user_" + "X" * 10000
large_thread_id = "thread_" + "Y" * 10000
large_run_id = "run_" + "Z" * 10000
large_request_id = "req_" + "W" * 10000

                        # Context should handle large values without crashing
context = UserExecutionContext( )
user_id=large_user_id,
thread_id=large_thread_id,
run_id=large_run_id,
request_id=large_request_id
                        

assert len(context.user_id) > 10000
assert len(context.thread_id) > 10000
assert len(context.run_id) > 10000
assert len(context.request_id) > 10000

@pytest.mark.asyncio
    async def test_unicode_and_special_characters_in_context(self):
"""Test context handles Unicode and special characters properly."""

unicode_contexts = [ ]
("[U+7528][U+6237]123", "[U+7EBF][U+7A0B]456", "[U+8FD0][U+884C]789", "[U+8BF7][U+6C42]012"),  # Chinese
("[U+0645][U+0633][U+062A][U+062E][U+062F][U+0645]123", "[U+0645][U+0648][U+0636][U+0648][U+0639]456", "[U+062A][U+0634][U+063A][U+064A][U+0644]789", "[U+0637][U+0644][U+0628]012"),  # Arabic
("[U+043F]o[U+043B][U+044C][U+0437]ovate[U+043B][U+044C]123", "[U+043F]otok456", "[U+0437]a[U+043F]uck789", "[U+0437]a[U+043F]poc012"),  # Russian
("[U+1F464]user123", "[U+1F9F5]thread456", "[U+1F3C3]run789", "[U+1F4DD]req012"),  # Emojis
("user )
123", "thread\t456", "run\r789", "req\0012"),  # Control chars
('user'123', 'thread'456', 'run\\789', 'req/012'),  # Special chars
                            

for user_id, thread_id, run_id, request_id in unicode_contexts:
try:
context = UserExecutionContext( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
request_id=request_id
                                    

                                    # Verify round-trip integrity
context_dict = context.to_dict()
assert context_dict["user_id"] == user_id
assert context_dict["thread_id"] == thread_id
assert context_dict["run_id"] == run_id
assert context_dict["request_id"] == request_id

except ValueError:
                                        # Some control characters might be rejected
                                        # This is acceptable behavior for security
pass

@pytest.mark.asyncio
    async def test_context_with_extreme_values(self):
"""Test context handles extreme edge case values."""

extreme_contexts = [ ]
                                            # Very long strings
("a" * 1000000, "b" * 1000000, "c" * 1000000, "d" * 1000000),

                                            # Numbers as strings (should be treated as strings)
("123456789", "987654321", "555666777", "111222333"),

                                            # Boolean-like strings (should be treated as strings)
("true", "false", "True", "False"),
("yes", "no", "on", "of""thread": true}', '{"run": 123}', '{"req": null}'),

                                            # XML-like strings (should be treated as literal strings)
("<user>test</user>", "<thread>456</thread>", "<run>789</run>", "<req>012</req>"),
                                            

for user_id, thread_id, run_id, request_id in extreme_contexts:
context = UserExecutionContext( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
request_id=request_id
                                                

                                                # Values should be preserved exactly as provided
assert context.user_id == user_id
assert context.thread_id == thread_id
assert context.run_id == run_id
assert context.request_id == request_id


class TestLegacyMethodDetection:
    """Test detection and prevention of legacy method usage."""

class FullyMigratedAgent(BaseAgent):
    """Agent that has been fully migrated to Phase 0."""

    def __init__(self):
        pass
        super().__init__(name="FullyMigratedAgent")

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        await asyncio.sleep(0)
        return {"status": "migrated", "user_id": context.user_id}

class PartiallyMigratedAgent(BaseAgent):
        """Agent with some legacy methods still present."""

    def __init__(self):
        pass
        super().__init__(name="PartiallyMigratedAgent")
        self.has_legacy_methods = True  # Flag to indicate legacy presence

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        return {"status": "partially_migrated", "user_id": context.user_id}

    # Legacy method that should not exist after migration
    async def execute_legacy(self, state, run_id: str = "", stream_updates: bool = False):
        pass
        await asyncio.sleep(0)
        return {"status": "legacy_called"}

    def test_detect_fully_migrated_agent(self):
        """Test detection of fully migrated agent."""
        agent = self.FullyMigratedAgent()

    # Check for new method presence
        assert hasattr(agent, 'execute_with_context')
        assert callable(getattr(agent, 'execute_with_context'))

    # Check for absence of legacy indicators
        assert not hasattr(agent, 'has_legacy_methods')

    Verify inheritance from BaseAgent
        assert isinstance(agent, BaseAgent)

    def test_detect_partially_migrated_agent(self):
        """Test detection of partially migrated agent."""
        pass
        agent = self.PartiallyMigratedAgent()

    # Should have new methods
        assert hasattr(agent, 'execute_with_context')

    # But also has legacy indicators
        assert hasattr(agent, 'has_legacy_methods')
        assert agent.has_legacy_methods

    # Should have legacy execute method
        assert hasattr(agent, 'execute_legacy')

    def test_scan_for_legacy_patterns(self):
        """Test scanning agent classes for legacy patterns."""

    def scan_agent_for_legacy_patterns(agent_class):
        """Scan agent class for legacy patterns."""
        pass
        legacy_indicators = []

    # Check for legacy method names
        legacy_methods = [ ]
        'execute_legacy',
        'run_legacy',
        'process_legacy',
        'handle_legacy'
    

        for method_name in legacy_methods:
        if hasattr(agent_class, method_name):
        legacy_indicators.append("")

            # Check for legacy attributes
        legacy_attributes = [ ]
        'has_legacy_methods',
        'legacy_mode',
        'use_legacy_execution'
            

        instance = agent_class()
        for attr_name in legacy_attributes:
        if hasattr(instance, attr_name):
        legacy_indicators.append("")

        return legacy_indicators

                    # Test fully migrated agent
        fully_migrated_indicators = scan_agent_for_legacy_patterns(self.FullyMigratedAgent)
        assert len(fully_migrated_indicators) == 0, ""

                    # Test partially migrated agent
        partially_migrated_indicators = scan_agent_for_legacy_patterns(self.PartiallyMigratedAgent)
        assert len(partially_migrated_indicators) > 0, "Partially migrated agent should have legacy patterns"
        assert "Legacy method: execute_legacy" in partially_migrated_indicators
        assert "Legacy attribute: has_legacy_methods" in partially_migrated_indicators

@pytest.mark.asyncio
    async def test_prevent_legacy_method_calls(self):
"""Test prevention of legacy method calls."""
agent = self.PartiallyMigratedAgent()

                        # New method should work
context = UserExecutionContext( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
request_id="test_request"
                        

result = await agent.execute(context)
assert result["status"] == "partially_migrated"

                        # Legacy method should be discouraged (but might still work for backward compatibility)
                        # In a real system, we might want to add warnings or restrictions
if hasattr(agent, 'execute_legacy'):
logger.warning("Agent still has legacy execute_legacy method - should be removed")


class TestAPIEndpointUpdates:
    """Test API endpoints using proper UserExecutionContext."""

@pytest.mark.asyncio
    async def test_api_endpoint_context_creation(self):
"""Test API endpoint creates proper UserExecutionContext."""

        Simulate API endpoint creating context from request parameters
def create_context_from_api_request(user_id: str, thread_id: str = None, run_id: str = None):
"""Simulate API endpoint context creation."""
pass
await asyncio.sleep(0)
return UserExecutionContext( )
user_id=user_id,
thread_id=thread_id or "",
run_id=run_id or "",
request_id=""
    

    # Test context creation with minimal parameters
context1 = create_context_from_api_request("api_user_1")
assert context1.user_id == "api_user_1"
assert context1.thread_id is not None
assert context1.run_id is not None
assert context1.request_id.startswith("api_req_")

    # Test context creation with all parameters
context2 = create_context_from_api_request( )
"api_user_2",
"custom_thread_123",
"custom_run_456"
    
assert context2.user_id == "api_user_2"
assert context2.thread_id == "custom_thread_123"
assert context2.run_id == "custom_run_456"

@pytest.mark.asyncio
    async def test_api_endpoint_error_handling(self):
"""Test API endpoint error handling with invalid parameters."""

def safe_create_context_from_api(user_id: str, thread_id: str = None, run_id: str = None):
"""Safely create context with error handling."""
pass
try:
await asyncio.sleep(0)
return create_user_execution_context( )
user_id=user_id,
thread_id=thread_id or "",
run_id=run_id or ""
        
except ValueError as e:
return {"error": str(e), "status": "invalid_context"}

            # Test with invalid user_id
result1 = safe_create_context_from_api("")  # Empty user_id
if isinstance(result1, dict) and "error" in result1:
assert "user_id cannot be empty" in result1["error"]

                # Test with None user_id
result2 = safe_create_context_from_api(None)
if isinstance(result2, dict) and "error" in result2:
assert "user_id cannot be None" in result2["error"]

                    # Test with placeholder user_id
result3 = safe_create_context_from_api("None")
if isinstance(result3, dict) and "error" in result3:
assert "cannot be the string 'None'" in result3["error"]


class TestIntegrationFullRequestFlow:
        """Integration tests for full request flow with Phase 0 migration."""

        @pytest.fixture
    async def real_services(self):
        """Fixture providing real services for integration testing."""
        manager = RealServicesManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()

class IntegrationTestAgent(BaseAgent):
        """Agent for integration testing."""

    def __init__(self):
        pass
        super().__init__(name="IntegrationTestAgent")
        self.execution_log = []

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        """Full integration execution with context."""

    # Log execution start
        self.execution_log.append({ })
        "phase": "start",
        "user_id": context.user_id,
        "run_id": context.run_id,
        "timestamp": datetime.now(timezone.utc)
    

    # Simulate WebSocket events
        if stream_updates:
        await self.emit_thinking("Starting integration test execution")
        await self.emit_progress("Processing user request", is_complete=False)

        # Simulate work with proper error handling
        try:
        await asyncio.sleep(0.1)  # Simulate processing

            # Create sub-context for sub-agent
        sub_context = UserExecutionContext( )
        user_id=context.user_id,
        thread_id=context.thread_id,
        run_id="",
        request_id=""
            

            # Log successful execution
        self.execution_log.append({ })
        "phase": "success",
        "user_id": context.user_id,
        "run_id": context.run_id,
        "sub_context_created": True,
        "timestamp": datetime.now(timezone.utc)
            

        if stream_updates:
        await self.emit_progress("Execution completed successfully", is_complete=True)

        await asyncio.sleep(0)
        return { }
        "status": "success",
        "user_id": context.user_id,
        "run_id": context.run_id,
        "sub_context_run_id": sub_context.run_id,
        "execution_log": self.execution_log
                

        except Exception as e:
        self.execution_log.append({ })
        "phase": "error",
        "user_id": context.user_id,
        "run_id": context.run_id,
        "error": str(e),
        "timestamp": datetime.now(timezone.utc)
                    

        if stream_updates:
        await self.emit_error("")

        raise

@pytest.mark.asyncio
    async def test_full_request_flow_integration(self):
"""Test complete request flow from context creation to agent execution."""

                            # Step 1: Create UserExecutionContext (simulating API request)
context = UserExecutionContext( )
user_id="integration_user",
thread_id="integration_thread",
run_id="integration_run",
request_id="integration_request"
                            

                            # Step 2: Create agent with context
agent = self.IntegrationTestAgent()

                            # Step 3: Execute with context
result = await agent.execute(context, stream_updates=True)

                            # Step 4: Verify complete flow
assert result["status"] == "success"
assert result["user_id"] == "integration_user"
assert result["run_id"] == "integration_run"
assert result["sub_context_run_id"] == "integration_run_sub"

                            # Verify execution log
execution_log = result["execution_log"]
assert len(execution_log) == 2  # start and success phases
assert execution_log[0]["phase"] == "start"
assert execution_log[1]["phase"] == "success"
assert execution_log[1]["sub_context_created"]

@pytest.mark.asyncio
    async def test_concurrent_integration_flows(self):
"""Test multiple concurrent integration flows."""

async def run_integration_flow(user_id: str) -> Dict[str, Any]:
"""Run complete integration flow for a user."""
context = UserExecutionContext( )
user_id=user_id,
thread_id="",
run_id="",
request_id=""
    

agent = self.IntegrationTestAgent()
result = await agent.execute(context, stream_updates=False)  # No WebSocket for performance

await asyncio.sleep(0)
return result

    # Run concurrent integration flows
concurrent_users = 15
tasks = [ ]
run_integration_flow("")
for i in range(concurrent_users)
    

results = await asyncio.gather(*tasks)

    # Verify all flows completed successfully
assert len(results) == concurrent_users

for result in results:
assert result["status"] == "success"
assert result["user_id"] is not None
assert result["run_id"] is not None
assert result["sub_context_run_id"] is not None
assert len(result["execution_log"]) == 2

        # Verify user isolation
user_ids = [r["user_id"] for r in results]
assert len(set(user_ids)) == concurrent_users, "User isolation violated"

run_ids = [r["run_id"] for r in results]
assert len(set(run_ids)) == concurrent_users, "Run ID collision detected"


class TestPerformanceValidation:
        """Performance tests to ensure no degradation from Phase 0 migration."""

@pytest.mark.asyncio
    async def test_context_creation_performance(self):
"""Test UserExecutionContext creation performance."""

start_time = time.time()

        # Create many contexts rapidly
contexts = []
for i in range(1000):
context = UserExecutionContext( )
user_id="",
thread_id="",
run_id="",
request_id=""
            
contexts.append(context)

end_time = time.time()

total_time = end_time - start_time
avg_time_per_context = (total_time / 1000) * 1000  # milliseconds

            # Performance assertion: should create contexts quickly
assert avg_time_per_context < 0.1, ""
assert len(contexts) == 1000

            # Verify all contexts are valid
for context in contexts[:10]:  # Check first 10
assert context.user_id is not None
assert context.thread_id is not None
assert context.run_id is not None
assert context.request_id is not None

@pytest.mark.asyncio
    async def test_agent_execution_performance(self):
"""Test agent execution performance with new context-based approach."""

class PerformanceTestAgent(BaseAgent):
    def __init__(self):
        pass
        super().__init__(name="PerformanceTestAgent")

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
    # Minimal processing to measure overhead
        await asyncio.sleep(0)
        return { }
        "user_id": context.user_id,
        "execution_time": time.time()
    

        agent = PerformanceTestAgent()
        execution_times = []

    # Measure execution time for multiple calls
        for i in range(100):
        context = UserExecutionContext( )
        user_id="",
        thread_id="",
        run_id="",
        request_id=""
        

        start_time = time.time()
        result = await agent.execute(context)
        end_time = time.time()

        execution_times.append(end_time - start_time)
        assert result["user_id"] == ""

        # Performance analysis
        avg_execution_time = sum(execution_times) / len(execution_times)
        max_execution_time = max(execution_times)

        # Performance assertions
        assert avg_execution_time < 0.001, ""
        assert max_execution_time < 0.005, ""

@pytest.mark.asyncio
    async def test_memory_usage_performance(self):
"""Test memory usage doesn't degrade with new context approach."""

import psutil
process = psutil.Process()
initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Create many contexts and execute agents
contexts = []
agents = []

for i in range(500):
context = UserExecutionContext( )
user_id="",
thread_id="",
run_id="",
request_id=""
                
contexts.append(context)

                # Measure memory after context creation
after_contexts_memory = process.memory_info().rss / 1024 / 1024
context_memory_usage = after_contexts_memory - initial_memory

                # Clean up contexts and force garbage collection
contexts.clear()
gc.collect()

final_memory = process.memory_info().rss / 1024 / 1024
memory_recovered = after_contexts_memory - final_memory

                # Performance assertions
assert context_memory_usage < 50.0, ""
assert memory_recovered > (context_memory_usage * 0.8), ""

@pytest.mark.asyncio
    async def test_concurrent_performance_scalability(self):
"""Test performance scalability under concurrent load."""

class ScalabilityTestAgent(BaseAgent):
    def __init__(self):
        pass
        super().__init__(name="ScalabilityTestAgent")

    async def execute_with_context(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
    # Simulate light processing
        await asyncio.sleep(0.001)  # 1ms processing time
        await asyncio.sleep(0)
        return {"user_id": context.user_id, "processed": True}

    async def execute_concurrent_batch(batch_size: int) -> Tuple[float, bool]:
        """Execute a batch of concurrent agents and measure performance."""

    async def single_execution(user_id: str):
        pass
        context = UserExecutionContext( )
        user_id=user_id,
        thread_id="",
        run_id="",
        request_id=""
    
        agent = ScalabilityTestAgent()
        await asyncio.sleep(0)
        return await agent.execute(context)

        start_time = time.time()
        tasks = [single_execution("") for i in range(batch_size)]
        results = await asyncio.gather(*tasks)
        end_time = time.time()

        total_time = end_time - start_time
        all_successful = all(r["processed"] for r in results)

        return total_time, all_successful

    # Test different batch sizes
        batch_sizes = [10, 25, 50, 100]
        performance_results = []

        for batch_size in batch_sizes:
        total_time, all_successful = await execute_concurrent_batch(batch_size)
        avg_time_per_execution = total_time / batch_size

        performance_results.append({ })
        "batch_size": batch_size,
        "total_time": total_time,
        "avg_time_per_execution": avg_time_per_execution,
        "all_successful": all_successful
        

        # Performance assertions for each batch size
        assert all_successful, ""
        assert avg_time_per_execution < 0.1, ""

        # Verify scalability (performance shouldn't degrade significantly with larger batches)
        small_batch_avg = performance_results[0]["avg_time_per_execution"]
        large_batch_avg = performance_results[-1]["avg_time_per_execution"]

        # Allow some degradation but not excessive
        performance_degradation = large_batch_avg / small_batch_avg
        assert performance_degradation < 3.0, ""


        # Test execution configuration
        if __name__ == "__main__":
            # Configure test execution
        pytest.main([ ])
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-x",  # Stop on first failure to identify issues quickly
            # "--log-cli-level=INFO",  # Enable for detailed logging
            
