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
    # REMOVED_SYNTAX_ERROR: Comprehensive unit tests for agent isolation architecture.

    # REMOVED_SYNTAX_ERROR: This test suite verifies that the new AgentClassRegistry + AgentInstanceFactory
    # REMOVED_SYNTAX_ERROR: architecture properly isolates user contexts and prevents data leakage between
    # REMOVED_SYNTAX_ERROR: concurrent users.

    # REMOVED_SYNTAX_ERROR: Business Value: Ensures 10+ concurrent users can operate safely without
    # REMOVED_SYNTAX_ERROR: context contamination or data leakage.
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: import uuid
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, Optional
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_class_registry import ( )
    # REMOVED_SYNTAX_ERROR: AgentClassRegistry,
    # REMOVED_SYNTAX_ERROR: get_agent_class_registry,
    # REMOVED_SYNTAX_ERROR: create_test_registry
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_instance_factory import ( )
    # REMOVED_SYNTAX_ERROR: AgentInstanceFactory,
    # REMOVED_SYNTAX_ERROR: UserWebSocketEmitter
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_context import ( )
    # REMOVED_SYNTAX_ERROR: UserExecutionContext,
    # REMOVED_SYNTAX_ERROR: InvalidContextError
    
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.registry.universal_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.base_agent import BaseAgent
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class MockAgent(BaseAgent):
    # REMOVED_SYNTAX_ERROR: """Mock agent for testing isolation."""

# REMOVED_SYNTAX_ERROR: def __init__(self, name: str = "mock_agent", user_id: Optional[str] = None, **kwargs):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: super().__init__()
    # REMOVED_SYNTAX_ERROR: self.name = name
    # REMOVED_SYNTAX_ERROR: self.user_id = user_id
    # REMOVED_SYNTAX_ERROR: self.description = "Mock agent for testing"
    # REMOVED_SYNTAX_ERROR: self.version = "1.0.0"
    # REMOVED_SYNTAX_ERROR: self.dependencies = []
    # REMOVED_SYNTAX_ERROR: self.websocket_bridge = None
    # REMOVED_SYNTAX_ERROR: self.run_id = None
    # REMOVED_SYNTAX_ERROR: self.execution_calls = []

# REMOVED_SYNTAX_ERROR: def set_websocket_bridge(self, bridge, run_id: Optional[str] = None):
    # REMOVED_SYNTAX_ERROR: """Set WebSocket bridge and run_id."""
    # REMOVED_SYNTAX_ERROR: self.websocket_bridge = bridge
    # REMOVED_SYNTAX_ERROR: self.run_id = run_id

# REMOVED_SYNTAX_ERROR: async def execute(self, state: Dict[str, Any], run_id: str) -> Dict[str, Any]:
    # REMOVED_SYNTAX_ERROR: """Mock execute method that records execution context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: execution_record = { )
    # REMOVED_SYNTAX_ERROR: 'agent_name': self.name,
    # REMOVED_SYNTAX_ERROR: 'user_id': self.user_id,
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'websocket_run_id': self.run_id,
    # REMOVED_SYNTAX_ERROR: 'timestamp': datetime.now(timezone.utc),
    # REMOVED_SYNTAX_ERROR: 'state_keys': list(state.keys()) if state else []
    
    # REMOVED_SYNTAX_ERROR: self.execution_calls.append(execution_record)

    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'success': True,
    # REMOVED_SYNTAX_ERROR: 'agent_name': self.name,
    # REMOVED_SYNTAX_ERROR: 'user_id': self.user_id,
    # REMOVED_SYNTAX_ERROR: 'run_id': run_id,
    # REMOVED_SYNTAX_ERROR: 'execution_id': len(self.execution_calls)
    


# REMOVED_SYNTAX_ERROR: class TestAgentClassRegistry:
    # REMOVED_SYNTAX_ERROR: """Test AgentClassRegistry infrastructure-only functionality."""

# REMOVED_SYNTAX_ERROR: def test_registry_initialization(self):
    # REMOVED_SYNTAX_ERROR: """Test registry initializes properly."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # REMOVED_SYNTAX_ERROR: assert len(registry) == 0
    # REMOVED_SYNTAX_ERROR: assert not registry.is_frozen()
    # REMOVED_SYNTAX_ERROR: assert registry.list_agent_names() == []
    # REMOVED_SYNTAX_ERROR: assert registry.get_registry_stats()['health_status'] == 'unhealthy'  # No classes yet

# REMOVED_SYNTAX_ERROR: def test_agent_class_registration(self):
    # REMOVED_SYNTAX_ERROR: """Test agent class registration works correctly."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register agent class
    # REMOVED_SYNTAX_ERROR: registry.register( )
    # REMOVED_SYNTAX_ERROR: name="mock_agent",
    # REMOVED_SYNTAX_ERROR: agent_class=MockAgent,
    # REMOVED_SYNTAX_ERROR: description="Test mock agent",
    # REMOVED_SYNTAX_ERROR: version="2.0.0",
    # REMOVED_SYNTAX_ERROR: dependencies=["llm_manager"],
    # REMOVED_SYNTAX_ERROR: metadata={"test": True}
    

    # REMOVED_SYNTAX_ERROR: assert len(registry) == 1
    # REMOVED_SYNTAX_ERROR: assert registry.has_agent_class("mock_agent")
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_class("mock_agent") == MockAgent

    # REMOVED_SYNTAX_ERROR: agent_info = registry.get_agent_info("mock_agent")
    # REMOVED_SYNTAX_ERROR: assert agent_info.name == "mock_agent"
    # REMOVED_SYNTAX_ERROR: assert agent_info.agent_class == MockAgent
    # REMOVED_SYNTAX_ERROR: assert agent_info.description == "Test mock agent"
    # REMOVED_SYNTAX_ERROR: assert agent_info.version == "2.0.0"
    # REMOVED_SYNTAX_ERROR: assert agent_info.dependencies == ("llm_manager")
    # REMOVED_SYNTAX_ERROR: assert agent_info.metadata == {"test": True}

# REMOVED_SYNTAX_ERROR: def test_duplicate_registration_same_class(self):
    # REMOVED_SYNTAX_ERROR: """Test duplicate registration with same class is handled gracefully."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register twice with same class
    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", MockAgent, "First registration")
    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", MockAgent, "Second registration")

    # REMOVED_SYNTAX_ERROR: assert len(registry) == 1
    # Should keep first registration
    # REMOVED_SYNTAX_ERROR: assert registry.get_agent_info("mock_agent").description == "First registration"

# REMOVED_SYNTAX_ERROR: def test_duplicate_registration_different_class(self):
    # REMOVED_SYNTAX_ERROR: """Test duplicate registration with different class raises error."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

# REMOVED_SYNTAX_ERROR: class AnotherMockAgent(BaseAgent):
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", MockAgent)

    # REMOVED_SYNTAX_ERROR: with pytest.raises(ValueError, match="already registered with different class"):
        # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", AnotherMockAgent)

# REMOVED_SYNTAX_ERROR: def test_freeze_functionality(self):
    # REMOVED_SYNTAX_ERROR: """Test registry freeze prevents modifications."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register before freezing
    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", MockAgent)

    # Freeze registry
    # REMOVED_SYNTAX_ERROR: registry.freeze()
    # REMOVED_SYNTAX_ERROR: assert registry.is_frozen()
    # REMOVED_SYNTAX_ERROR: assert registry.get_registry_stats()['health_status'] == 'healthy'

    # Try to register after freezing
    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
        # REMOVED_SYNTAX_ERROR: registry.register("another_agent", MockAgent)

# REMOVED_SYNTAX_ERROR: def test_thread_safety(self):
    # REMOVED_SYNTAX_ERROR: """Test registry is thread-safe during registration."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: import threading
    # REMOVED_SYNTAX_ERROR: import time

    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()
    # REMOVED_SYNTAX_ERROR: results = []
    # REMOVED_SYNTAX_ERROR: errors = []

# REMOVED_SYNTAX_ERROR: def register_agent(agent_num):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: try:
        # REMOVED_SYNTAX_ERROR: agent_name = "formatted_string"
        # REMOVED_SYNTAX_ERROR: registry.register(agent_name, MockAgent, "formatted_string")
        # REMOVED_SYNTAX_ERROR: results.append(agent_name)
        # REMOVED_SYNTAX_ERROR: except Exception as e:
            # REMOVED_SYNTAX_ERROR: errors.append("formatted_string")

            # Create multiple threads
            # REMOVED_SYNTAX_ERROR: threads = []
            # REMOVED_SYNTAX_ERROR: for i in range(10):
                # REMOVED_SYNTAX_ERROR: thread = threading.Thread(target=register_agent, args=(i))
                # REMOVED_SYNTAX_ERROR: threads.append(thread)

                # Start all threads
                # REMOVED_SYNTAX_ERROR: for thread in threads:
                    # REMOVED_SYNTAX_ERROR: thread.start()

                    # Wait for completion
                    # REMOVED_SYNTAX_ERROR: for thread in threads:
                        # REMOVED_SYNTAX_ERROR: thread.join()

                        # REMOVED_SYNTAX_ERROR: assert len(errors) == 0, "formatted_string"
                        # REMOVED_SYNTAX_ERROR: assert len(results) == 10
                        # REMOVED_SYNTAX_ERROR: assert len(registry) == 10

# REMOVED_SYNTAX_ERROR: def test_dependency_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test dependency validation functionality."""
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # Register agents with dependencies
    # REMOVED_SYNTAX_ERROR: registry.register("base_agent", MockAgent, dependencies=[])
    # REMOVED_SYNTAX_ERROR: registry.register("dependent_agent", MockAgent, dependencies=["base_agent", "missing_agent"])

    # REMOVED_SYNTAX_ERROR: missing_deps = registry.validate_dependencies()

    # REMOVED_SYNTAX_ERROR: assert "base_agent" not in missing_deps
    # REMOVED_SYNTAX_ERROR: assert "dependent_agent" in missing_deps
    # REMOVED_SYNTAX_ERROR: assert missing_deps["dependent_agent"] == ["missing_agent"]

# REMOVED_SYNTAX_ERROR: def test_immutability_after_freeze(self):
    # REMOVED_SYNTAX_ERROR: """Test registry is truly immutable after freeze."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()

    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", MockAgent)
    # REMOVED_SYNTAX_ERROR: agent_info_before = registry.get_agent_info("mock_agent")

    # REMOVED_SYNTAX_ERROR: registry.freeze()

    # Agent info should be same object (immutable)
    # REMOVED_SYNTAX_ERROR: agent_info_after = registry.get_agent_info("mock_agent")
    # REMOVED_SYNTAX_ERROR: assert agent_info_before is agent_info_after

    # List should be consistent
    # REMOVED_SYNTAX_ERROR: names_before = registry.list_agent_names()
    # REMOVED_SYNTAX_ERROR: names_after = registry.list_agent_names()
    # REMOVED_SYNTAX_ERROR: assert names_before == names_after


# REMOVED_SYNTAX_ERROR: class TestUserExecutionContext:
    # REMOVED_SYNTAX_ERROR: """Test UserExecutionContext isolation and validation."""

# REMOVED_SYNTAX_ERROR: def test_valid_context_creation(self):
    # REMOVED_SYNTAX_ERROR: """Test valid context creation."""
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: run_id="run789"
    

    # REMOVED_SYNTAX_ERROR: assert context.user_id == "user123"
    # REMOVED_SYNTAX_ERROR: assert context.thread_id == "thread456"
    # REMOVED_SYNTAX_ERROR: assert context.run_id == "run789"
    # REMOVED_SYNTAX_ERROR: assert context.request_id is not None
    # REMOVED_SYNTAX_ERROR: assert isinstance(context.created_at, datetime)
    # REMOVED_SYNTAX_ERROR: assert context.metadata == {}

# REMOVED_SYNTAX_ERROR: def test_placeholder_value_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test that placeholder values are rejected."""
    # REMOVED_SYNTAX_ERROR: pass
    # Test exact dangerous values
    # REMOVED_SYNTAX_ERROR: dangerous_values = ['registry', 'placeholder', 'default', 'temp', 'none', 'null']

    # REMOVED_SYNTAX_ERROR: for dangerous_value in dangerous_values:
        # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError, match="forbidden placeholder value"):
            # REMOVED_SYNTAX_ERROR: UserExecutionContext.from_request( )
            # REMOVED_SYNTAX_ERROR: user_id=dangerous_value,
            # REMOVED_SYNTAX_ERROR: thread_id="thread456",
            # REMOVED_SYNTAX_ERROR: run_id="run789"
            

            # Test dangerous patterns
            # REMOVED_SYNTAX_ERROR: dangerous_patterns = ['placeholder_123', 'registry_temp', 'default_xxx']

            # REMOVED_SYNTAX_ERROR: for dangerous_pattern in dangerous_patterns:
                # REMOVED_SYNTAX_ERROR: with pytest.raises(InvalidContextError, match="placeholder pattern"):
                    # REMOVED_SYNTAX_ERROR: UserExecutionContext.from_request( )
                    # REMOVED_SYNTAX_ERROR: user_id=dangerous_pattern,
                    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
                    # REMOVED_SYNTAX_ERROR: run_id="run789"
                    

# REMOVED_SYNTAX_ERROR: def test_context_immutability(self):
    # REMOVED_SYNTAX_ERROR: """Test that context is truly immutable."""
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: run_id="run789",
    # REMOVED_SYNTAX_ERROR: metadata={"key": "value"}
    

    # Try to modify (should fail)
    # REMOVED_SYNTAX_ERROR: with pytest.raises(AttributeError):
        # REMOVED_SYNTAX_ERROR: context.user_id = "modified"

        # Metadata should be a separate copy
        # REMOVED_SYNTAX_ERROR: original_metadata = context.metadata
        # REMOVED_SYNTAX_ERROR: original_metadata["new_key"] = "new_value"

        # Context metadata should be unchanged
        # REMOVED_SYNTAX_ERROR: assert "new_key" not in context.metadata

# REMOVED_SYNTAX_ERROR: def test_child_context_creation(self):
    # REMOVED_SYNTAX_ERROR: """Test child context creation preserves parent data."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: parent_context = UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: run_id="run789",
    # REMOVED_SYNTAX_ERROR: metadata={"parent": "data"}
    

    # REMOVED_SYNTAX_ERROR: child_context = parent_context.create_child_context( )
    # REMOVED_SYNTAX_ERROR: "sub_operation",
    # REMOVED_SYNTAX_ERROR: {"child": "data"}
    

    # Child should inherit parent identifiers
    # REMOVED_SYNTAX_ERROR: assert child_context.user_id == parent_context.user_id
    # REMOVED_SYNTAX_ERROR: assert child_context.thread_id == parent_context.thread_id
    # REMOVED_SYNTAX_ERROR: assert child_context.run_id == parent_context.run_id

    # Child should have new request_id
    # REMOVED_SYNTAX_ERROR: assert child_context.request_id != parent_context.request_id

    # Child metadata should include parent + child + operation data
    # REMOVED_SYNTAX_ERROR: assert child_context.metadata["parent"] == "data"
    # REMOVED_SYNTAX_ERROR: assert child_context.metadata["child"] == "data"
    # REMOVED_SYNTAX_ERROR: assert child_context.metadata["operation_name"] == "sub_operation"
    # REMOVED_SYNTAX_ERROR: assert child_context.metadata["parent_request_id"] == parent_context.request_id
    # REMOVED_SYNTAX_ERROR: assert child_context.metadata["operation_depth"] == 1

# REMOVED_SYNTAX_ERROR: def test_context_isolation_verification(self):
    # REMOVED_SYNTAX_ERROR: """Test context isolation verification."""
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user123",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456",
    # REMOVED_SYNTAX_ERROR: run_id="run789"
    

    # Should pass isolation check
    # REMOVED_SYNTAX_ERROR: assert context.verify_isolation() is True

# REMOVED_SYNTAX_ERROR: def test_correlation_id_generation(self):
    # REMOVED_SYNTAX_ERROR: """Test correlation ID generation."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = UserExecutionContext.from_request( )
    # REMOVED_SYNTAX_ERROR: user_id="user123456789",
    # REMOVED_SYNTAX_ERROR: thread_id="thread456789012",
    # REMOVED_SYNTAX_ERROR: run_id="run789012345")

    # REMOVED_SYNTAX_ERROR: correlation_id = context.get_correlation_id()

    # Should contain truncated versions of IDs
    # REMOVED_SYNTAX_ERROR: assert correlation_id.startswith("user1234:")
    # REMOVED_SYNTAX_ERROR: assert "thread45:" in correlation_id
    # REMOVED_SYNTAX_ERROR: assert "run78901:" in correlation_id


# REMOVED_SYNTAX_ERROR: class TestAgentInstanceFactory:
    # REMOVED_SYNTAX_ERROR: """Test AgentInstanceFactory per-request isolation."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_bridge():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket bridge."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_started = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_executing = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.notify_tool_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_thinking = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.notify_agent_error = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: bridge.unregister_run_mapping = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: return bridge

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def configured_factory(self, mock_websocket_bridge):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create configured AgentInstanceFactory."""
    # REMOVED_SYNTAX_ERROR: pass
    # Setup registry
    # REMOVED_SYNTAX_ERROR: registry = create_test_registry()
    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent", MockAgent, "Test agent")

    # Setup factory
    # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()
    # REMOVED_SYNTAX_ERROR: factory.configure( )
    # REMOVED_SYNTAX_ERROR: agent_class_registry=registry,
    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
    

    # REMOVED_SYNTAX_ERROR: return factory

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_user_context_creation(self, configured_factory):
        # REMOVED_SYNTAX_ERROR: """Test user execution context creation."""
        # REMOVED_SYNTAX_ERROR: context = await configured_factory.create_user_execution_context( )
        # REMOVED_SYNTAX_ERROR: user_id="user123",
        # REMOVED_SYNTAX_ERROR: thread_id="thread456",
        # REMOVED_SYNTAX_ERROR: run_id="run789"
        

        # REMOVED_SYNTAX_ERROR: assert context.user_id == "user123"
        # REMOVED_SYNTAX_ERROR: assert context.thread_id == "thread456"
        # REMOVED_SYNTAX_ERROR: assert context.run_id == "run789"
        # REMOVED_SYNTAX_ERROR: assert context.request_id is not None

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_agent_instance_creation(self, configured_factory):
            # REMOVED_SYNTAX_ERROR: """Test agent instance creation with proper context binding."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: context = await configured_factory.create_user_execution_context( )
            # REMOVED_SYNTAX_ERROR: user_id="user123",
            # REMOVED_SYNTAX_ERROR: thread_id="thread456",
            # REMOVED_SYNTAX_ERROR: run_id="run789"
            

            # REMOVED_SYNTAX_ERROR: agent = await configured_factory.create_agent_instance("mock_agent", context)

            # REMOVED_SYNTAX_ERROR: assert isinstance(agent, MockAgent)
            # REMOVED_SYNTAX_ERROR: assert agent.user_id == "user123"
            # REMOVED_SYNTAX_ERROR: assert agent.run_id == "run789"  # Should be set from context
            # REMOVED_SYNTAX_ERROR: assert agent.websocket_bridge is not None

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_user_execution_scope(self, configured_factory):
                # REMOVED_SYNTAX_ERROR: """Test user execution scope context manager."""
                # REMOVED_SYNTAX_ERROR: async with configured_factory.user_execution_scope( )
                # REMOVED_SYNTAX_ERROR: user_id="user123",
                # REMOVED_SYNTAX_ERROR: thread_id="thread456",
                # REMOVED_SYNTAX_ERROR: run_id="run789"
                # REMOVED_SYNTAX_ERROR: ) as context:
                    # REMOVED_SYNTAX_ERROR: assert context.user_id == "user123"

                    # Create agent within scope
                    # REMOVED_SYNTAX_ERROR: agent = await configured_factory.create_agent_instance("mock_agent", context)
                    # REMOVED_SYNTAX_ERROR: assert agent.user_id == "user123"

                    # Context should be cleaned up after scope
                    # Factory should track cleanup
                    # REMOVED_SYNTAX_ERROR: metrics = configured_factory.get_factory_metrics()
                    # REMOVED_SYNTAX_ERROR: assert metrics['total_contexts_cleaned'] >= 1

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_concurrent_user_isolation(self, configured_factory):
                        # REMOVED_SYNTAX_ERROR: """Test that concurrent users have completely isolated contexts."""
                        # REMOVED_SYNTAX_ERROR: pass
# REMOVED_SYNTAX_ERROR: async def user_workflow(user_id: str, results: list):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: async with configured_factory.user_execution_scope( )
    # REMOVED_SYNTAX_ERROR: user_id=user_id,
    # REMOVED_SYNTAX_ERROR: thread_id="formatted_string",
    # REMOVED_SYNTAX_ERROR: run_id="formatted_string"
    # REMOVED_SYNTAX_ERROR: ) as context:
        # REMOVED_SYNTAX_ERROR: agent = await configured_factory.create_agent_instance("mock_agent", context)

        # Execute agent with user-specific data
        # REMOVED_SYNTAX_ERROR: result = await agent.execute( )
        # REMOVED_SYNTAX_ERROR: {"user_data": "formatted_string"},
        # REMOVED_SYNTAX_ERROR: context.run_id
        

        # REMOVED_SYNTAX_ERROR: results.append({ ))
        # REMOVED_SYNTAX_ERROR: 'user_id': user_id,
        # REMOVED_SYNTAX_ERROR: 'agent_user_id': agent.user_id,
        # REMOVED_SYNTAX_ERROR: 'context_user_id': context.user_id,
        # REMOVED_SYNTAX_ERROR: 'run_id': context.run_id,
        # REMOVED_SYNTAX_ERROR: 'result': result
        

        # Run multiple concurrent users
        # REMOVED_SYNTAX_ERROR: results = []
        # REMOVED_SYNTAX_ERROR: tasks = []
        # REMOVED_SYNTAX_ERROR: for i in range(5):
            # REMOVED_SYNTAX_ERROR: user_id = "formatted_string"
            # REMOVED_SYNTAX_ERROR: task = asyncio.create_task(user_workflow(user_id, results))
            # REMOVED_SYNTAX_ERROR: tasks.append(task)

            # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

            # Verify isolation
            # REMOVED_SYNTAX_ERROR: assert len(results) == 5

            # REMOVED_SYNTAX_ERROR: user_ids = [r['user_id'] for r in results]
            # REMOVED_SYNTAX_ERROR: agent_user_ids = [r['agent_user_id'] for r in results]
            # REMOVED_SYNTAX_ERROR: context_user_ids = [r['context_user_id'] for r in results]
            # REMOVED_SYNTAX_ERROR: run_ids = [r['run_id'] for r in results]

            # All user IDs should match their respective contexts/agents
            # REMOVED_SYNTAX_ERROR: for result in results:
                # REMOVED_SYNTAX_ERROR: assert result['user_id'] == result['agent_user_id']
                # REMOVED_SYNTAX_ERROR: assert result['user_id'] == result['context_user_id']
                # REMOVED_SYNTAX_ERROR: assert result['run_id'].endswith(result['user_id'])

                # All run_ids should be unique
                # REMOVED_SYNTAX_ERROR: assert len(set(run_ids)) == 5

                # All user_ids should be unique
                # REMOVED_SYNTAX_ERROR: assert len(set(user_ids)) == 5

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_websocket_emitter_isolation(self, configured_factory):
                    # REMOVED_SYNTAX_ERROR: """Test that WebSocket emitters are properly isolated per user."""
                    # Create contexts for two different users
                    # REMOVED_SYNTAX_ERROR: context1 = await configured_factory.create_user_execution_context( )
                    # REMOVED_SYNTAX_ERROR: user_id="user1",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread1",
                    # REMOVED_SYNTAX_ERROR: run_id="run1"
                    

                    # REMOVED_SYNTAX_ERROR: context2 = await configured_factory.create_user_execution_context( )
                    # REMOVED_SYNTAX_ERROR: user_id="user2",
                    # REMOVED_SYNTAX_ERROR: thread_id="thread2",
                    # REMOVED_SYNTAX_ERROR: run_id="run2"
                    

                    # Create agents for both users
                    # REMOVED_SYNTAX_ERROR: agent1 = await configured_factory.create_agent_instance("mock_agent", context1)
                    # REMOVED_SYNTAX_ERROR: agent2 = await configured_factory.create_agent_instance("mock_agent", context2)

                    # Agents should have different run_ids bound to their WebSocket
                    # REMOVED_SYNTAX_ERROR: assert agent1.run_id == "run1"
                    # REMOVED_SYNTAX_ERROR: assert agent2.run_id == "run2"
                    # REMOVED_SYNTAX_ERROR: assert agent1.user_id == "user1"
                    # REMOVED_SYNTAX_ERROR: assert agent2.user_id == "user2"

                    # WebSocket bridges should be set but with different run contexts
                    # REMOVED_SYNTAX_ERROR: assert agent1.websocket_bridge is not None
                    # REMOVED_SYNTAX_ERROR: assert agent2.websocket_bridge is not None
                    # Same bridge instance but different run_id contexts
                    # REMOVED_SYNTAX_ERROR: assert agent1.websocket_bridge is agent2.websocket_bridge
                    # REMOVED_SYNTAX_ERROR: assert agent1.run_id != agent2.run_id

# REMOVED_SYNTAX_ERROR: def test_factory_metrics_tracking(self, configured_factory):
    # REMOVED_SYNTAX_ERROR: """Test factory tracks metrics properly."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: initial_metrics = configured_factory.get_factory_metrics()

    # REMOVED_SYNTAX_ERROR: assert 'total_instances_created' in initial_metrics
    # REMOVED_SYNTAX_ERROR: assert 'active_contexts' in initial_metrics
    # REMOVED_SYNTAX_ERROR: assert 'total_contexts_cleaned' in initial_metrics
    # REMOVED_SYNTAX_ERROR: assert 'creation_errors' in initial_metrics
    # REMOVED_SYNTAX_ERROR: assert 'cleanup_errors' in initial_metrics


# REMOVED_SYNTAX_ERROR: class TestAgentRegistryMigration:
    # REMOVED_SYNTAX_ERROR: """Test AgentRegistry migration to new architecture."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def legacy_registry(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create legacy AgentRegistry for migration testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: llm_manager = Magic        tool_dispatcher = Magic
    # Create and configure infrastructure registry for testing
    # REMOVED_SYNTAX_ERROR: test_infrastructure_registry = create_test_registry()

    # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

    # Manually register some test agents
    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent_1", MockAgent("mock_agent_1"))
    # REMOVED_SYNTAX_ERROR: registry.register("mock_agent_2", MockAgent("mock_agent_2"))

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return registry

# REMOVED_SYNTAX_ERROR: def test_get_infrastructure_registry(self, legacy_registry):
    # REMOVED_SYNTAX_ERROR: """Test getting infrastructure registry from legacy registry."""
    # REMOVED_SYNTAX_ERROR: infrastructure_registry = legacy_registry.get_infrastructure_registry()

    # REMOVED_SYNTAX_ERROR: assert infrastructure_registry is not None
    # REMOVED_SYNTAX_ERROR: assert isinstance(infrastructure_registry, AgentClassRegistry)

# REMOVED_SYNTAX_ERROR: def test_migration_to_new_architecture(self, legacy_registry):
    # REMOVED_SYNTAX_ERROR: """Test migration from legacy to new architecture."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: migration_status = legacy_registry.migrate_to_new_architecture()

    # REMOVED_SYNTAX_ERROR: assert migration_status['infrastructure_registry_available'] is True
    # REMOVED_SYNTAX_ERROR: assert migration_status['legacy_agents_count'] == 2
    # REMOVED_SYNTAX_ERROR: assert migration_status['agent_classes_migrated'] >= 2
    # REMOVED_SYNTAX_ERROR: assert migration_status['migration_complete'] is True
    # REMOVED_SYNTAX_ERROR: assert len(migration_status['migration_errors']) == 0

    # Verify agents are in infrastructure registry
    # REMOVED_SYNTAX_ERROR: infrastructure_registry = legacy_registry.get_infrastructure_registry()
    # REMOVED_SYNTAX_ERROR: assert infrastructure_registry.has_agent_class("mock_agent_1")
    # REMOVED_SYNTAX_ERROR: assert infrastructure_registry.has_agent_class("mock_agent_2")

    # Verify recommendations
    # REMOVED_SYNTAX_ERROR: assert any("AgentInstanceFactory" in rec for rec in migration_status['recommendations'])
    # REMOVED_SYNTAX_ERROR: assert any("UserExecutionContext" in rec for rec in migration_status['recommendations'])

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_create_request_factory(self, legacy_registry):
        # REMOVED_SYNTAX_ERROR: """Test creating request factory from legacy registry."""
        # Create a user context
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext.from_request( )
        # REMOVED_SYNTAX_ERROR: user_id="test_user",
        # REMOVED_SYNTAX_ERROR: thread_id="test_thread",
        # REMOVED_SYNTAX_ERROR: run_id="test_run"
        

        # Create factory from legacy registry
        # REMOVED_SYNTAX_ERROR: factory = legacy_registry.create_request_factory(context)

        # REMOVED_SYNTAX_ERROR: assert isinstance(factory, AgentInstanceFactory)

        # Factory should be configured
        # REMOVED_SYNTAX_ERROR: metrics = factory.get_factory_metrics()
        # REMOVED_SYNTAX_ERROR: assert metrics['configuration_status']['agent_registry_configured'] is True

# REMOVED_SYNTAX_ERROR: def test_deprecation_warnings(self):
    # REMOVED_SYNTAX_ERROR: """Test that deprecation warnings are issued for legacy usage."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: llm_manager = Magic        tool_dispatcher = Magic
    # REMOVED_SYNTAX_ERROR: with patch('warnings.warn') as mock_warn:
        # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

        # Should have issued deprecation warning
        # REMOVED_SYNTAX_ERROR: mock_warn.assert_called_once()
        # REMOVED_SYNTAX_ERROR: args, kwargs = mock_warn.call_args
        # REMOVED_SYNTAX_ERROR: assert "deprecated" in args[0].lower()
        # REMOVED_SYNTAX_ERROR: assert kwargs.get('category') == DeprecationWarning


# REMOVED_SYNTAX_ERROR: class TestBackwardCompatibility:
    # REMOVED_SYNTAX_ERROR: """Test backward compatibility during migration."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def configured_environment(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Set up both old and new architecture components."""
    # REMOVED_SYNTAX_ERROR: pass
    # Legacy components
    # REMOVED_SYNTAX_ERROR: llm_manager = Magic        tool_dispatcher = Magic
    # REMOVED_SYNTAX_ERROR: legacy_registry = AgentRegistry()

    # Register test agents
    # REMOVED_SYNTAX_ERROR: legacy_registry.register("test_agent", MockAgent("test_agent"))

    # New components
    # REMOVED_SYNTAX_ERROR: infrastructure_registry = legacy_registry.get_infrastructure_registry()
    # REMOVED_SYNTAX_ERROR: factory = AgentInstanceFactory()

    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: mock_bridge.notify_agent_started = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: mock_bridge.notify_agent_error = AsyncMock(return_value=True)

    # REMOVED_SYNTAX_ERROR: factory.configure( )
    # REMOVED_SYNTAX_ERROR: agent_class_registry=infrastructure_registry,
    # REMOVED_SYNTAX_ERROR: agent_registry=legacy_registry,
    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_bridge
    

    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return { )
    # REMOVED_SYNTAX_ERROR: 'legacy_registry': legacy_registry,
    # REMOVED_SYNTAX_ERROR: 'infrastructure_registry': infrastructure_registry,
    # REMOVED_SYNTAX_ERROR: 'factory': factory,
    # REMOVED_SYNTAX_ERROR: 'websocket_bridge': mock_bridge
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_old_and_new_coexistence(self, configured_environment):
        # REMOVED_SYNTAX_ERROR: """Test that old and new patterns can coexist."""
        # REMOVED_SYNTAX_ERROR: legacy_registry = configured_environment['legacy_registry']
        # REMOVED_SYNTAX_ERROR: factory = configured_environment['factory']

        # Old pattern still works
        # REMOVED_SYNTAX_ERROR: old_agent = legacy_registry.get("test_agent")
        # REMOVED_SYNTAX_ERROR: assert old_agent is not None
        # REMOVED_SYNTAX_ERROR: assert isinstance(old_agent, MockAgent)

        # New pattern also works
        # REMOVED_SYNTAX_ERROR: context = await factory.create_user_execution_context( )
        # REMOVED_SYNTAX_ERROR: user_id="new_user",
        # REMOVED_SYNTAX_ERROR: thread_id="new_thread",
        # REMOVED_SYNTAX_ERROR: run_id="new_run"
        

        # REMOVED_SYNTAX_ERROR: new_agent = await factory.create_agent_instance("test_agent", context)
        # REMOVED_SYNTAX_ERROR: assert new_agent is not None
        # REMOVED_SYNTAX_ERROR: assert isinstance(new_agent, MockAgent)

        # They should be different instances
        # REMOVED_SYNTAX_ERROR: assert old_agent is not new_agent
        # REMOVED_SYNTAX_ERROR: assert old_agent.user_id != new_agent.user_id

# REMOVED_SYNTAX_ERROR: def test_legacy_methods_still_work(self, configured_environment):
    # REMOVED_SYNTAX_ERROR: """Test that legacy methods continue to function."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: legacy_registry = configured_environment['legacy_registry']

    # Legacy methods should work
    # REMOVED_SYNTAX_ERROR: assert len(legacy_registry.list_agents()) > 0
    # REMOVED_SYNTAX_ERROR: assert legacy_registry.get("test_agent") is not None

    # REMOVED_SYNTAX_ERROR: health = legacy_registry.get_registry_health()
    # REMOVED_SYNTAX_ERROR: assert health['total_agents'] > 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_migration_path_examples(self, configured_environment):
        # REMOVED_SYNTAX_ERROR: """Test examples of migration path usage."""
        # REMOVED_SYNTAX_ERROR: legacy_registry = configured_environment['legacy_registry']

        # Example 1: Get infrastructure registry
        # REMOVED_SYNTAX_ERROR: infrastructure_registry = legacy_registry.get_infrastructure_registry()
        # REMOVED_SYNTAX_ERROR: assert infrastructure_registry.has_agent_class("test_agent")

        # Example 2: Create request-scoped factory
        # REMOVED_SYNTAX_ERROR: context = UserExecutionContext.from_request( )
        # REMOVED_SYNTAX_ERROR: user_id="example_user",
        # REMOVED_SYNTAX_ERROR: thread_id="example_thread",
        # REMOVED_SYNTAX_ERROR: run_id="example_run"
        

        # REMOVED_SYNTAX_ERROR: factory = legacy_registry.create_request_factory(context)
        # REMOVED_SYNTAX_ERROR: agent = await factory.create_agent_instance("test_agent", context)

        # REMOVED_SYNTAX_ERROR: assert agent.user_id == "example_user"
        # REMOVED_SYNTAX_ERROR: assert agent.run_id == "example_run"

        # Example 3: Use migration status
        # REMOVED_SYNTAX_ERROR: migration_status = legacy_registry.migrate_to_new_architecture()
        # REMOVED_SYNTAX_ERROR: assert migration_status['migration_complete'] is True


        # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
            # Run tests with: python -m pytest tests/netra_backend/agents/test_agent_isolation.py -v
            # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v"])
            # REMOVED_SYNTAX_ERROR: pass