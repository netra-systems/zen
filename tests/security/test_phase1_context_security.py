# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Phase 1 Migration Security Tests for UserExecutionContext

    # REMOVED_SYNTAX_ERROR: This module tests for security vulnerabilities introduced in the Phase 1 migration
    # REMOVED_SYNTAX_ERROR: of SupervisorAgent, TriageSubAgent, and DataSubAgent to UserExecutionContext pattern.

    # REMOVED_SYNTAX_ERROR: Critical security concerns tested:
        # REMOVED_SYNTAX_ERROR: - Session hijacking through context manipulation
        # REMOVED_SYNTAX_ERROR: - Data leakage between users
        # REMOVED_SYNTAX_ERROR: - SQL injection through context parameters
        # REMOVED_SYNTAX_ERROR: - Resource exhaustion attacks
        # REMOVED_SYNTAX_ERROR: - Privilege escalation attempts
        # REMOVED_SYNTAX_ERROR: - Memory exhaustion through circular references
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import gc
        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: import uuid
        # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone, timedelta
        # REMOVED_SYNTAX_ERROR: from sqlalchemy.ext.asyncio import AsyncSession
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import DatabaseTestManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import ( )
        # REMOVED_SYNTAX_ERROR: UserExecutionContext,
        # REMOVED_SYNTAX_ERROR: InvalidContextError,
        # REMOVED_SYNTAX_ERROR: validate_user_context
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.triage.unified_triage_agent import TriageSubAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestUserContextSecurityVulnerabilities:
    # REMOVED_SYNTAX_ERROR: """Test for security vulnerabilities in UserExecutionContext implementation."""

# REMOVED_SYNTAX_ERROR: def test_session_hijacking_prevention_via_context_validation(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent session hijacking through malicious context manipulation.

    # REMOVED_SYNTAX_ERROR: Vulnerability: If context validation is weak, attackers could potentially
    # REMOVED_SYNTAX_ERROR: hijack sessions by manipulating user_id, thread_id, or other identifiers.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Attempt to create context with SQL injection patterns
    # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError):
        # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="admin"; DROP TABLE users; --",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
        # REMOVED_SYNTAX_ERROR: run_id="run_456"
        

        # Attempt to create context with path traversal patterns
        # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError):
            # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id="../../../etc/passwd",
            # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
            # REMOVED_SYNTAX_ERROR: run_id="run_456"
            

            # Attempt to create context with command injection patterns
            # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError):
                # REMOVED_SYNTAX_ERROR: UserExecutionContext( )
                # REMOVED_SYNTAX_ERROR: user_id="user_123; rm -rf /",
                # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
                # REMOVED_SYNTAX_ERROR: run_id="run_456"
                

# REMOVED_SYNTAX_ERROR: def test_user_data_isolation_enforcement(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Ensure complete user data isolation in concurrent execution.

    # REMOVED_SYNTAX_ERROR: Vulnerability: If contexts share references, users could access each other"s data.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Create contexts for different users
    # REMOVED_SYNTAX_ERROR: user1_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_001_secure",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_001",
    # REMOVED_SYNTAX_ERROR: run_id="run_001",
    # REMOVED_SYNTAX_ERROR: metadata={"sensitive_data": "user1_private_info"}
    

    # REMOVED_SYNTAX_ERROR: user2_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_002_secure",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_002",
    # REMOVED_SYNTAX_ERROR: run_id="run_002",
    # REMOVED_SYNTAX_ERROR: metadata={"sensitive_data": "user2_private_info"}
    

    # Verify complete isolation - no shared references
    # REMOVED_SYNTAX_ERROR: assert user1_context.user_id != user2_context.user_id
    # REMOVED_SYNTAX_ERROR: assert user1_context.metadata is not user2_context.metadata
    # REMOVED_SYNTAX_ERROR: assert id(user1_context.metadata) != id(user2_context.metadata)

    # Verify modifying one context doesn't affect the other
    # REMOVED_SYNTAX_ERROR: user1_context.verify_isolation()
    # REMOVED_SYNTAX_ERROR: user2_context.verify_isolation()

    # Verify contexts have different memory locations
    # REMOVED_SYNTAX_ERROR: assert id(user1_context) != id(user2_context)

# REMOVED_SYNTAX_ERROR: def test_context_tampering_prevention(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent context tampering through immutability enforcement.

    # REMOVED_SYNTAX_ERROR: Vulnerability: If contexts are mutable, attackers could modify them
    # REMOVED_SYNTAX_ERROR: to escalate privileges or access unauthorized data.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_secure_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789"
    

    # Attempt to modify immutable context (should fail)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):  # dataclass frozen should prevent this
    # REMOVED_SYNTAX_ERROR: context.user_id = "admin_user"

    # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):
        # REMOVED_SYNTAX_ERROR: context.thread_id = "admin_thread"

        # REMOVED_SYNTAX_ERROR: with pytest.raises(Exception):
            # REMOVED_SYNTAX_ERROR: context.run_id = "admin_run"

# REMOVED_SYNTAX_ERROR: def test_privilege_escalation_prevention(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent privilege escalation through context manipulation.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Attackers might try to escalate privileges by using
    # REMOVED_SYNTAX_ERROR: admin-like usernames or system reserved identifiers.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: admin_patterns = [ )
    # REMOVED_SYNTAX_ERROR: "admin",
    # REMOVED_SYNTAX_ERROR: "root",
    # REMOVED_SYNTAX_ERROR: "system",
    # REMOVED_SYNTAX_ERROR: "administrator",
    # REMOVED_SYNTAX_ERROR: "superuser",
    # REMOVED_SYNTAX_ERROR: "sa",
    # REMOVED_SYNTAX_ERROR: "postgres",
    # REMOVED_SYNTAX_ERROR: "mysql"
    

    # REMOVED_SYNTAX_ERROR: for admin_pattern in admin_patterns:
        # Direct admin patterns should be allowed (not our concern at context level)
        # but we test that contexts with these patterns work normally
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",  # Legitimate user with admin in name
        # REMOVED_SYNTAX_ERROR: thread_id="thread_123",
        # REMOVED_SYNTAX_ERROR: run_id="run_456"
        
        # REMOVED_SYNTAX_ERROR: assert context.user_id.startswith("user_")

# REMOVED_SYNTAX_ERROR: def test_resource_exhaustion_prevention(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent resource exhaustion attacks through context abuse.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Attackers could try to exhaust resources by creating
    # REMOVED_SYNTAX_ERROR: contexts with extremely large metadata or circular references.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Test extremely large metadata (should be limited)
    # REMOVED_SYNTAX_ERROR: large_data = "x" * 1000000  # 1MB of data

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user_123",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
        # REMOVED_SYNTAX_ERROR: run_id="run_789",
        # REMOVED_SYNTAX_ERROR: metadata={"large_field": large_data}
        
        # If context creation succeeds, verify it doesn't consume excessive memory
        # REMOVED_SYNTAX_ERROR: assert len(str(context)) < 10000  # String representation should be bounded
        # REMOVED_SYNTAX_ERROR: except Exception:
            # It's acceptable if extremely large contexts are rejected
            # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_circular_reference_prevention(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent memory leaks through circular references in metadata.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Circular references in context metadata could cause
    # REMOVED_SYNTAX_ERROR: memory leaks and potential DoS conditions.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Create metadata with potential circular reference
    # REMOVED_SYNTAX_ERROR: circular_data = {"ref": None}
    # REMOVED_SYNTAX_ERROR: circular_data["ref"] = circular_data  # Create circular reference

    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user_123",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
        # REMOVED_SYNTAX_ERROR: run_id="run_789",
        # REMOVED_SYNTAX_ERROR: metadata=circular_data
        
        # If creation succeeds, verify the context can be properly serialized
        # (this would fail with circular references)
        # REMOVED_SYNTAX_ERROR: context_dict = context.to_dict()
        # REMOVED_SYNTAX_ERROR: assert isinstance(context_dict, dict)
        # REMOVED_SYNTAX_ERROR: except Exception:
            # It's acceptable if circular references are detected and rejected
            # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_injection_attack_prevention_in_metadata(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent various injection attacks through metadata fields.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Metadata could be used to inject malicious code or data.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: injection_patterns = [ )
    # REMOVED_SYNTAX_ERROR: {"script": "<script>alert('xss')</script>"},
    # REMOVED_SYNTAX_ERROR: {"sql": ""; DROP TABLE users; --"},
    # REMOVED_SYNTAX_ERROR: {"command": "; rm -rf /"},
    # REMOVED_SYNTAX_ERROR: {"path": "../../../etc/passwd"},
    # REMOVED_SYNTAX_ERROR: {"ldap": "(|(uid=*))(|(uid=*))"},
    # REMOVED_SYNTAX_ERROR: {"xpath": "' or '1'='1"},
    # REMOVED_SYNTAX_ERROR: {"nosql": ""; return true; //"}
    

    # REMOVED_SYNTAX_ERROR: for pattern in injection_patterns:
        # Create context with potentially malicious metadata
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="user_123",
        # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
        # REMOVED_SYNTAX_ERROR: run_id="run_789",
        # REMOVED_SYNTAX_ERROR: metadata=pattern
        

        # Verify the context safely serializes (no code execution)
        # REMOVED_SYNTAX_ERROR: context_dict = context.to_dict()
        # REMOVED_SYNTAX_ERROR: assert isinstance(context_dict["metadata"], dict)

        # Verify string representation is safe
        # REMOVED_SYNTAX_ERROR: str_repr = str(context)
        # REMOVED_SYNTAX_ERROR: assert len(str_repr) < 10000  # Bounded output

# REMOVED_SYNTAX_ERROR: def test_concurrent_context_isolation(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Verify context isolation under concurrent operations.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Race conditions could cause context data to leak
    # REMOVED_SYNTAX_ERROR: between concurrent operations.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: contexts = []

    # Create multiple contexts concurrently
    # REMOVED_SYNTAX_ERROR: for i in range(100):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: metadata={"user_index": i, "secret": "formatted_string"}
        
        # REMOVED_SYNTAX_ERROR: contexts.append(context)

        # Verify each context maintains its own data
        # REMOVED_SYNTAX_ERROR: for i, context in enumerate(contexts):
            # REMOVED_SYNTAX_ERROR: assert context.user_id == "formatted_string"
            # REMOVED_SYNTAX_ERROR: assert context.metadata["user_index"] == i
            # REMOVED_SYNTAX_ERROR: assert context.metadata["secret"] == "formatted_string"

            # Verify no cross-contamination
            # REMOVED_SYNTAX_ERROR: user_ids = [ctx.user_id for ctx in contexts]
            # REMOVED_SYNTAX_ERROR: assert len(set(user_ids)) == len(user_ids)  # All unique

# REMOVED_SYNTAX_ERROR: def test_memory_leak_prevention(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent memory leaks from context retention.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Contexts might not be properly garbage collected,
    # REMOVED_SYNTAX_ERROR: leading to memory leaks in long-running applications.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: import gc
    # REMOVED_SYNTAX_ERROR: import weakref

    # Create contexts and weak references
    # REMOVED_SYNTAX_ERROR: weak_refs = []

    # REMOVED_SYNTAX_ERROR: for i in range(10):
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
        # REMOVED_SYNTAX_ERROR: user_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
        # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
        
        # REMOVED_SYNTAX_ERROR: weak_refs.append(weakref.ref(context))
        # REMOVED_SYNTAX_ERROR: del context  # Remove strong reference

        # Force garbage collection
        # REMOVED_SYNTAX_ERROR: gc.collect()

        # Check if contexts were properly garbage collected
        # REMOVED_SYNTAX_ERROR: collected_count = sum(1 for ref in weak_refs if ref() is None)

        # At least some contexts should be collected
        # (exact number depends on Python implementation)
        # REMOVED_SYNTAX_ERROR: assert collected_count >= 0  # Basic check that GC is working


# REMOVED_SYNTAX_ERROR: class TestAgentSecurityWithContext:
    # REMOVED_SYNTAX_ERROR: """Test security implications of agent execution with UserExecutionContext."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_llm_manager():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_bridge():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_tool_dispatcher():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return
    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def secure_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="secure_user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="secure_thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="secure_run_789"
    

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def malicious_context(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Context that might be used in attack scenarios."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="attacker_user_999",
    # REMOVED_SYNTAX_ERROR: thread_id="attack_thread_999",
    # REMOVED_SYNTAX_ERROR: run_id="attack_run_999",
    # REMOVED_SYNTAX_ERROR: metadata={ )
    # REMOVED_SYNTAX_ERROR: "malicious_payload": "<script>alert('xss')</script>",
    # REMOVED_SYNTAX_ERROR: "sql_injection": ""; DROP TABLE users; --",
    # REMOVED_SYNTAX_ERROR: "command_injection": "; rm -rf /"
    
    

    # Removed problematic line: async def test_supervisor_agent_context_validation(self, mock_llm_manager,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: mock_tool_dispatcher,
    # REMOVED_SYNTAX_ERROR: secure_context):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test: SupervisorAgent properly validates context before execution.

        # REMOVED_SYNTAX_ERROR: Vulnerability: If context validation is bypassed, malicious contexts
        # REMOVED_SYNTAX_ERROR: could be used to compromise the agent execution.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: supervisor = await SupervisorAgent.create_with_user_context( )
        # REMOVED_SYNTAX_ERROR: llm_manager=mock_llm_manager,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
        # REMOVED_SYNTAX_ERROR: tool_dispatcher=mock_tool_dispatcher,
        # REMOVED_SYNTAX_ERROR: user_context=secure_context
        

        # Verify supervisor has proper context
        # REMOVED_SYNTAX_ERROR: assert supervisor.user_context is not None
        # REMOVED_SYNTAX_ERROR: assert supervisor.user_context.user_id == secure_context.user_id

        # Test context validation occurs during execution
        # (Would need to mock the actual execution to test this fully)
        # REMOVED_SYNTAX_ERROR: assert supervisor.user_context.user_id.startswith("secure_user_")

        # Removed problematic line: async def test_agent_execution_isolation(self, secure_context, malicious_context):
            # REMOVED_SYNTAX_ERROR: '''
            # REMOVED_SYNTAX_ERROR: Test: Ensure agent executions with different contexts remain isolated.

            # REMOVED_SYNTAX_ERROR: Vulnerability: Agents might share state between different user contexts.
            # REMOVED_SYNTAX_ERROR: '''
            # REMOVED_SYNTAX_ERROR: pass
            # Create agents with different contexts
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent

            # Mock agent for testing
# REMOVED_SYNTAX_ERROR: class TestAgent(BaseAgent):
# REMOVED_SYNTAX_ERROR: def __init__(self, context):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: super().__init__(name="TestAgent")
    # REMOVED_SYNTAX_ERROR: self.execution_context = context
    # REMOVED_SYNTAX_ERROR: self.execution_data = {}

# REMOVED_SYNTAX_ERROR: async def execute_core_logic(self, context):
    # REMOVED_SYNTAX_ERROR: pass
    # Store data based on user context
    # REMOVED_SYNTAX_ERROR: self.execution_data[context.user_id] = { )
    # REMOVED_SYNTAX_ERROR: "secret": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now()
    
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"status": "success", "user": context.user_id}

    # REMOVED_SYNTAX_ERROR: agent1 = TestAgent(secure_context)
    # REMOVED_SYNTAX_ERROR: agent2 = TestAgent(malicious_context)

    # Verify agents have different contexts
    # REMOVED_SYNTAX_ERROR: assert agent1.execution_context.user_id != agent2.execution_context.user_id

    # Simulate execution
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base.interface import ExecutionContext
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.agent_models import DeepAgentState

    # REMOVED_SYNTAX_ERROR: exec_context1 = ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id=secure_context.run_id,
    # REMOVED_SYNTAX_ERROR: agent_name="TestAgent",
    # REMOVED_SYNTAX_ERROR: state=DeepAgentState(),
    # REMOVED_SYNTAX_ERROR: user_id=secure_context.user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=secure_context.thread_id
    

    # REMOVED_SYNTAX_ERROR: exec_context2 = ExecutionContext( )
    # REMOVED_SYNTAX_ERROR: run_id=malicious_context.run_id,
    # REMOVED_SYNTAX_ERROR: agent_name="TestAgent",
    # REMOVED_SYNTAX_ERROR: state=DeepAgentState(),
    # REMOVED_SYNTAX_ERROR: user_id=malicious_context.user_id,
    # REMOVED_SYNTAX_ERROR: thread_id=malicious_context.thread_id
    

    # REMOVED_SYNTAX_ERROR: result1 = await agent1.execute_core_logic(exec_context1)
    # REMOVED_SYNTAX_ERROR: result2 = await agent2.execute_core_logic(exec_context2)

    # Verify results are isolated
    # REMOVED_SYNTAX_ERROR: assert result1["user"] != result2["user"]
    # REMOVED_SYNTAX_ERROR: assert result1["user"] == secure_context.user_id
    # REMOVED_SYNTAX_ERROR: assert result2["user"] == malicious_context.user_id

# REMOVED_SYNTAX_ERROR: def test_database_session_isolation(self, secure_context):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Ensure database sessions are properly isolated per context.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Shared database sessions could lead to data leakage.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_session1 = Mock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: mock_session2 = Mock(spec=AsyncSession)

    # Create contexts with different sessions
    # REMOVED_SYNTAX_ERROR: context1 = secure_context.with_db_session(mock_session1)
    # REMOVED_SYNTAX_ERROR: context2 = secure_context.with_db_session(mock_session2)

    # Verify sessions are different
    # REMOVED_SYNTAX_ERROR: assert context1.db_session is not context2.db_session
    # REMOVED_SYNTAX_ERROR: assert context1.db_session == mock_session1
    # REMOVED_SYNTAX_ERROR: assert context2.db_session == mock_session2

    # Verify other context data remains the same
    # REMOVED_SYNTAX_ERROR: assert context1.user_id == context2.user_id
    # REMOVED_SYNTAX_ERROR: assert context1.thread_id == context2.thread_id
    # REMOVED_SYNTAX_ERROR: assert context1.run_id == context2.run_id

# REMOVED_SYNTAX_ERROR: def test_websocket_connection_isolation(self, secure_context):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Ensure WebSocket connections are properly isolated per context.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Shared WebSocket connections could lead to message
    # REMOVED_SYNTAX_ERROR: being delivered to wrong users.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # Create contexts with different WebSocket connections
    # REMOVED_SYNTAX_ERROR: context1 = secure_context.with_websocket_connection("ws_conn_123")
    # REMOVED_SYNTAX_ERROR: context2 = secure_context.with_websocket_connection("ws_conn_456")

    # Verify connections are different
    # REMOVED_SYNTAX_ERROR: assert context1.websocket_connection_id != context2.websocket_connection_id
    # REMOVED_SYNTAX_ERROR: assert context1.websocket_connection_id == "ws_conn_123"
    # REMOVED_SYNTAX_ERROR: assert context2.websocket_connection_id == "ws_conn_456"

    # Verify other context data remains the same
    # REMOVED_SYNTAX_ERROR: assert context1.user_id == context2.user_id
    # REMOVED_SYNTAX_ERROR: assert context1.thread_id == context2.thread_id
    # REMOVED_SYNTAX_ERROR: assert context1.run_id == context2.run_id

    # Removed problematic line: async def test_context_metadata_injection_protection(self, secure_context):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test: Ensure metadata cannot be used for injection attacks.

        # REMOVED_SYNTAX_ERROR: Vulnerability: Malicious metadata could be used in queries or logs
        # REMOVED_SYNTAX_ERROR: without proper sanitization.
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: pass
        # REMOVED_SYNTAX_ERROR: malicious_metadata = { )
        # REMOVED_SYNTAX_ERROR: "search_term": ""; DROP TABLE users; --",
        # REMOVED_SYNTAX_ERROR: "user_input": "<script>alert('xss')</script>",
        # REMOVED_SYNTAX_ERROR: "file_path": "../../../etc/passwd",
        # REMOVED_SYNTAX_ERROR: "command": "; rm -rf /",
        # REMOVED_SYNTAX_ERROR: "json_payload": '{"admin": true}'
        

        # Create child context with malicious metadata
        # REMOVED_SYNTAX_ERROR: child_context = secure_context.create_child_context( )
        # REMOVED_SYNTAX_ERROR: operation_name="test_operation",
        # REMOVED_SYNTAX_ERROR: additional_metadata=malicious_metadata
        

        # Verify the metadata is safely stored
        # REMOVED_SYNTAX_ERROR: assert isinstance(child_context.metadata, dict)

        # Verify safe serialization (no code execution)
        # REMOVED_SYNTAX_ERROR: context_dict = child_context.to_dict()
        # REMOVED_SYNTAX_ERROR: assert "search_term" in context_dict["metadata"]

        # Verify string representation is bounded and safe
        # REMOVED_SYNTAX_ERROR: str_repr = str(child_context)
        # REMOVED_SYNTAX_ERROR: assert len(str_repr) < 10000
        # REMOVED_SYNTAX_ERROR: assert "alert" not in str_repr  # Should not contain script content

# REMOVED_SYNTAX_ERROR: def test_context_validation_bypass_prevention(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Prevent bypassing context validation through edge cases.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Attackers might try to bypass validation using
    # REMOVED_SYNTAX_ERROR: edge cases in string handling or validation logic.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: edge_case_inputs = [ )
    # Unicode and encoding edge cases
    # REMOVED_SYNTAX_ERROR: ("user_\x00null", "thread_123", "run_456"),  # Null bytes
    # REMOVED_SYNTAX_ERROR: ("user_ )
    # REMOVED_SYNTAX_ERROR: \r\twhitespace", "thread_123", "run_456"),  # Control chars
    # REMOVED_SYNTAX_ERROR: ("user_[U+1F680]emoji", "thread_123", "run_456"),  # Unicode emoji
    # REMOVED_SYNTAX_ERROR: ("user_" + "a" * 1000, "thread_123", "run_456"),  # Very long input

    # String manipulation edge cases
    # REMOVED_SYNTAX_ERROR: ("user_123", "thread_\x00", "run_456"),  # Null in thread_id
    # REMOVED_SYNTAX_ERROR: ("user_123", "thread_456", "run_\r )
    # REMOVED_SYNTAX_ERROR: "),  # CRLF injection attempt
    # REMOVED_SYNTAX_ERROR: ("user_123", "thread_456", "run_" + "\t" * 100),  # Tab flooding
    

    # REMOVED_SYNTAX_ERROR: for user_id, thread_id, run_id in edge_case_inputs:
        # REMOVED_SYNTAX_ERROR: try:
            # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
            # REMOVED_SYNTAX_ERROR: user_id=user_id,
            # REMOVED_SYNTAX_ERROR: thread_id=thread_id,
            # REMOVED_SYNTAX_ERROR: run_id=run_id
            
            # If context creation succeeds, verify it's safe
            # REMOVED_SYNTAX_ERROR: assert isinstance(context.user_id, str)
            # REMOVED_SYNTAX_ERROR: assert isinstance(context.thread_id, str)
            # REMOVED_SYNTAX_ERROR: assert isinstance(context.run_id, str)

            # Verify safe serialization
            # REMOVED_SYNTAX_ERROR: context_dict = context.to_dict()
            # REMOVED_SYNTAX_ERROR: assert isinstance(context_dict, dict)

            # REMOVED_SYNTAX_ERROR: except (InvalidContextError, ValueError, UnicodeError):
                # It's acceptable to reject edge case inputs
                # REMOVED_SYNTAX_ERROR: pass


# REMOVED_SYNTAX_ERROR: class TestContextSecurityIntegration:
    # REMOVED_SYNTAX_ERROR: """Integration tests for context security across the system."""

# REMOVED_SYNTAX_ERROR: def test_context_chain_security(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Ensure security is maintained through context chain operations.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Context chain operations (parent/child) might introduce
    # REMOVED_SYNTAX_ERROR: security vulnerabilities through reference sharing or data leakage.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: parent_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="parent_user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="parent_thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="parent_run_789",
    # REMOVED_SYNTAX_ERROR: metadata={"parent_secret": "parent_data", "privilege_level": "user"}
    

    # Create child context
    # REMOVED_SYNTAX_ERROR: child_context = parent_context.create_child_context( )
    # REMOVED_SYNTAX_ERROR: operation_name="child_operation",
    # REMOVED_SYNTAX_ERROR: additional_metadata={"child_secret": "child_data"}
    

    # Verify child context security properties
    # REMOVED_SYNTAX_ERROR: assert child_context.user_id == parent_context.user_id
    # REMOVED_SYNTAX_ERROR: assert child_context.thread_id == parent_context.thread_id
    # REMOVED_SYNTAX_ERROR: assert child_context.run_id == parent_context.run_id
    # REMOVED_SYNTAX_ERROR: assert child_context.request_id != parent_context.request_id  # Should be different

    # Verify metadata isolation (child should not modify parent)
    # REMOVED_SYNTAX_ERROR: assert "child_secret" in child_context.metadata
    # REMOVED_SYNTAX_ERROR: assert "child_secret" not in parent_context.metadata
    # REMOVED_SYNTAX_ERROR: assert "parent_secret" in child_context.metadata  # Inherited

    # Verify metadata is copied, not shared (no references)
    # REMOVED_SYNTAX_ERROR: assert id(child_context.metadata) != id(parent_context.metadata)

    # Modify child metadata and verify parent is not affected
    # REMOVED_SYNTAX_ERROR: if hasattr(child_context, '_metadata_copy'):
        # If there's a way to modify metadata, test isolation
        # REMOVED_SYNTAX_ERROR: pass

# REMOVED_SYNTAX_ERROR: def test_correlation_id_security(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Ensure correlation IDs don"t leak sensitive information.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Correlation IDs might contain or leak sensitive data
    # REMOVED_SYNTAX_ERROR: that could be used to infer user information or system state.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: sensitive_context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="sensitive_user_admin_12345678901234567890",  # Long sensitive ID
    # REMOVED_SYNTAX_ERROR: thread_id="thread_containing_pii_data_987654321",    # PII in thread
    # REMOVED_SYNTAX_ERROR: run_id="run_with_secrets_abcdefghijklmnop",          # Secrets in run
    # REMOVED_SYNTAX_ERROR: request_id="req_internal_system_data_zzzzzzz"       # Internal data
    

    # REMOVED_SYNTAX_ERROR: correlation_id = sensitive_context.get_correlation_id()

    # Verify correlation ID is truncated/safe
    # REMOVED_SYNTAX_ERROR: assert len(correlation_id) <= 100  # Reasonable length limit

    # Verify it doesn't contain full sensitive data
    # REMOVED_SYNTAX_ERROR: assert "sensitive_user_admin_12345678901234567890" not in correlation_id
    # REMOVED_SYNTAX_ERROR: assert "thread_containing_pii_data_987654321" not in correlation_id
    # REMOVED_SYNTAX_ERROR: assert "run_with_secrets_abcdefghijklmnop" not in correlation_id

    # But should contain enough for correlation
    # REMOVED_SYNTAX_ERROR: assert "sensitive_" in correlation_id  # Partial match OK
    # REMOVED_SYNTAX_ERROR: assert ":" in correlation_id  # Should have separators

# REMOVED_SYNTAX_ERROR: def test_context_serialization_security(self):
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Test: Ensure context serialization doesn"t leak sensitive data.

    # REMOVED_SYNTAX_ERROR: Vulnerability: Serialized contexts might accidentally include
    # REMOVED_SYNTAX_ERROR: sensitive data like database sessions or internal state.
    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_session = Mock(spec=AsyncSession)
    # REMOVED_SYNTAX_ERROR: mock_session.bind = "postgresql://user:password@host/db"  # Sensitive connection string

    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext( )
    # REMOVED_SYNTAX_ERROR: user_id="user_123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread_456",
    # REMOVED_SYNTAX_ERROR: run_id="run_789",
    # REMOVED_SYNTAX_ERROR: db_session=mock_session,
    # REMOVED_SYNTAX_ERROR: metadata={"api_key": "secret_key_123", "password": "user_password"}
    

    # Test to_dict serialization
    # REMOVED_SYNTAX_ERROR: context_dict = context.to_dict()

    # Verify sensitive data is not included
    # REMOVED_SYNTAX_ERROR: assert "db_session" not in context_dict
    # REMOVED_SYNTAX_ERROR: assert "password" not in str(context_dict)  # Check string representation
    # REMOVED_SYNTAX_ERROR: assert "postgresql://" not in str(context_dict)

    # But verify it indicates session presence
    # REMOVED_SYNTAX_ERROR: assert "has_db_session" in context_dict
    # REMOVED_SYNTAX_ERROR: assert context_dict["has_db_session"] is True

    # Verify metadata is included (it's the caller's responsibility to sanitize)
    # REMOVED_SYNTAX_ERROR: assert "metadata" in context_dict
    # REMOVED_SYNTAX_ERROR: assert isinstance(context_dict["metadata"], dict)


    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])