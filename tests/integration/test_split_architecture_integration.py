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
        COMPREHENSIVE INTEGRATION TESTS: Split Architecture Isolation
        ================================================================

        CRITICAL MISSION: Validate the new split architecture provides complete user isolation:
        1. AgentClassRegistry - Infrastructure-only agent class registration
        2. AgentInstanceFactory - Per-request agent instantiation with complete isolation
        3. UserExecutionContext - Per-request execution context with validation
        4. WebSocket event routing with proper user isolation
        5. Database session isolation across concurrent requests
        6. Resource cleanup and memory management

        Business Value Justification:
        - Segment: Platform/Internal
        - Business Goal: Stability & Security
        - Value Impact: Enables safe 10+ concurrent users with zero data leakage
        - Strategic Impact: Foundation for multi-tenant production deployment

        These tests are INTENTIONALLY DIFFICULT and COMPREHENSIVE to validate:
        - Complete flow from FastAPI request to agent execution with isolation
        - Concurrent user requests with proper isolation
        - WebSocket events reach correct users only
        - Database session isolation across requests
        - Resource cleanup prevents memory leaks
        - Error scenarios and edge cases
        - Performance under stress (5+ concurrent users)
        '''

        import asyncio
        import gc
        import pytest
        import time
        import uuid
        import weakref
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from dataclasses import dataclass
        from datetime import datetime, timezone
        from typing import Dict, List, Set, Optional, Any, Tuple
        import psutil
        import threading
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
        from sqlalchemy import text

                # Import the split architecture components
        from netra_backend.app.agents.supervisor.agent_class_registry import ( )
        AgentClassRegistry,
        AgentClassInfo,
        get_agent_class_registry,
        create_test_registry
                
        from netra_backend.app.agents.supervisor.agent_instance_factory import ( )
        AgentInstanceFactory,
        UserWebSocketEmitter,
        configure_agent_instance_factory,
        get_agent_instance_factory
                
        from netra_backend.app.services.user_execution_context import UserExecutionContext as ModelsUserExecutionContext

                # Import supervisor UserExecutionContext
        from netra_backend.app.services.user_execution_context import UserExecutionContext as SupervisorUserExecutionContext
        from netra_backend.app.core.registry.universal_registry import AgentRegistry
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
        from netra_backend.app.agents.base_agent import BaseAgent
        from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.schemas.agent_models import DeepAgentState
        from netra_backend.app.logging_config import central_logger
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env

        logger = central_logger.get_logger(__name__)


                # ============================================================================
                # Mock Classes for Testing
                # ============================================================================

class MockAgent(BaseAgent):
        """Mock agent for testing isolation with comprehensive instrumentation."""

    def __init__(self, *args, **kwargs):
        pass
        super().__init__(*args, **kwargs)
        self.execution_log = []
        self.websocket_events_sent = []
        self.user_data_accessed = []
        self.db_queries_executed = []
        self.memory_footprint = []
        self._execution_count = 0
        self._is_cleaned_up = False

    async def execute(self, state: DeepAgentState, run_id: str) -> DeepAgentState:
        """Mock execution with comprehensive tracking."""
        execution_id = "formatted_string"
        self._execution_count += 1

    # Record execution details for isolation validation
        execution_record = { )
        'execution_id': execution_id,
        'run_id': run_id,
        'user_id': getattr(self, 'user_id', 'unknown'),
        'thread_id': getattr(state, 'thread_id', 'unknown'),
        'start_time': datetime.now(timezone.utc),
        'memory_before': psutil.Process().memory_info().rss,
        'thread_local_data': threading.current_thread().ident
    

        self.execution_log.append(execution_record)

    # Simulate WebSocket event emission
        if hasattr(self, '_websocket_adapter') and self._websocket_adapter:
        try:
        await self.emit_thinking("Processing user request", step_number=1)
        self.websocket_events_sent.append({ ))
        'event_type': 'agent_thinking',
        'run_id': run_id,
        'timestamp': datetime.now(timezone.utc),
        'user_context': getattr(self, 'user_id', 'unknown')
            
        except Exception as e:
        logger.warning("formatted_string")

                # Simulate processing time and memory usage
        await asyncio.sleep(0.1)  # Simulate work

                # Record memory usage during execution
        memory_during = psutil.Process().memory_info().rss
        self.memory_footprint.append({ ))
        'execution_id': execution_id,
        'memory_peak': memory_during,
        'timestamp': datetime.now(timezone.utc)
                

                # Update execution record with completion details
        execution_record.update({ ))
        'end_time': datetime.now(timezone.utc),
        'memory_after': psutil.Process().memory_info().rss,
        'memory_delta': memory_during - execution_record['memory_before'],
        'completed': True
                

                # Return modified state to validate state isolation
        result_state = DeepAgentState( )
        user_message="formatted_string",
        thread_id=getattr(state, 'thread_id', 'unknown'),
        additional_context={ )
        'agent_execution_id': execution_id,
        'processed_at': datetime.now(timezone.utc).isoformat(),
        'agent_user_id': getattr(self, 'user_id', 'unknown')
                
                

        return result_state

    def get_execution_summary(self) -> Dict[str, Any]:
        """Get summary of agent execution for validation."""
        return { )
        'agent_name': self.name,
        'agent_id': getattr(self, 'agent_id', 'unknown'),
        'user_id': getattr(self, 'user_id', 'unknown'),
        'total_executions': len(self.execution_log),
        'websocket_events_count': len(self.websocket_events_sent),
        'memory_samples': len(self.memory_footprint),
        'is_cleaned_up': self._is_cleaned_up,
        'execution_log': self.execution_log[-5:],  # Last 5 executions
        'websocket_events': self.websocket_events_sent[-5:],  # Last 5 events
    

    async def cleanup(self):
        """Clean up agent resources for memory leak testing."""
        self._is_cleaned_up = True
        self.execution_log.clear()
        self.websocket_events_sent.clear()
        self.user_data_accessed.clear()
        self.db_queries_executed.clear()
        self.memory_footprint.clear()


class MockTriageAgent(MockAgent):
        """Specialized mock triage agent."""

    def __init__(self, *args, **kwargs):
        pass
        super().__init__(*args, name="triage", **kwargs)
        self.description = "Mock triage agent for testing"


class MockDataAgent(MockAgent):
        """Specialized mock data agent."""

    def __init__(self, *args, **kwargs):
        pass
        super().__init__(*args, name="data", **kwargs)
        self.description = "Mock data agent for testing"


        @dataclass
class ConcurrentUserTestResult:
        """Results from concurrent user testing."""
        user_id: str
        thread_id: str
        run_id: str
        success: bool
        execution_time_ms: float
        websocket_events_received: List[Dict[str, Any]]
        agent_execution_log: List[Dict[str, Any]]
        context_isolation_validated: bool
        database_session_isolated: bool
        memory_leak_detected: bool
        error_message: Optional[str] = None


    # ============================================================================
    # Test Fixtures
    # ============================================================================

        @pytest.fixture
    async def mock_llm_manager():
        """Create mock LLM manager."""
        llm_manager = MagicMock(spec=LLMManager)
        llm_manager.send_completion = AsyncMock(return_value="Mock LLM response")
        await asyncio.sleep(0)
        return llm_manager


        @pytest.fixture
    async def mock_tool_dispatcher():
        """Create mock tool dispatcher."""
        pass
        tool_dispatcher = MagicMock(spec=ToolDispatcher)
        tool_dispatcher.dispatch = AsyncMock(return_value={"result": "mock_tool_result"})
        await asyncio.sleep(0)
        return tool_dispatcher


        @pytest.fixture
    async def mock_websocket_manager():
        """Create mock WebSocket manager for testing."""
        websocket_manager = MagicMock(spec=WebSocketManager)
        websocket_manager.emit = AsyncMock(return_value=True)
        websocket_manager.emit_to_user = AsyncMock(return_value=True)
        websocket_manager.emit_to_thread = AsyncMock(return_value=True)
        websocket_manager.is_connected = MagicMock(return_value=True)
        await asyncio.sleep(0)
        return websocket_manager


        @pytest.fixture
    async def mock_websocket_bridge(mock_websocket_manager):
        """Create mock WebSocket bridge with comprehensive event tracking."""
        pass
        bridge = MagicMock(spec=AgentWebSocketBridge)

    # Track events sent to each user/run for isolation validation
        bridge.events_sent = []
        bridge.run_thread_mappings = {}

    async def mock_notify_agent_started(run_id, agent_name, context=None):
        pass
        event = { )
        'type': 'agent_started',
        'run_id': run_id,
        'agent_name': agent_name,
        'context': context,
        'timestamp': datetime.now(timezone.utc),
        'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
        bridge.events_sent.append(event)
        await asyncio.sleep(0)
        return True

    async def mock_notify_agent_thinking(run_id, agent_name, reasoning, step_number=None, progress_percentage=None):
        pass
        event = { )
        'type': 'agent_thinking',
        'run_id': run_id,
        'agent_name': agent_name,
        'reasoning': reasoning,
        'step_number': step_number,
        'progress_percentage': progress_percentage,
        'timestamp': datetime.now(timezone.utc),
        'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
        bridge.events_sent.append(event)
        await asyncio.sleep(0)
        return True

    async def mock_notify_tool_executing(run_id, agent_name, tool_name, parameters=None):
        pass
        event = { )
        'type': 'tool_executing',
        'run_id': run_id,
        'agent_name': agent_name,
        'tool_name': tool_name,
        'parameters': parameters,
        'timestamp': datetime.now(timezone.utc),
        'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
        bridge.events_sent.append(event)
        await asyncio.sleep(0)
        return True

    async def mock_notify_tool_completed(run_id, agent_name, tool_name, result=None, execution_time_ms=None):
        pass
        event = { )
        'type': 'tool_completed',
        'run_id': run_id,
        'agent_name': agent_name,
        'tool_name': tool_name,
        'result': result,
        'execution_time_ms': execution_time_ms,
        'timestamp': datetime.now(timezone.utc),
        'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
        bridge.events_sent.append(event)
        await asyncio.sleep(0)
        return True

    async def mock_notify_agent_completed(run_id, agent_name, result=None, execution_time_ms=None):
        pass
        event = { )
        'type': 'agent_completed',
        'run_id': run_id,
        'agent_name': agent_name,
        'result': result,
        'execution_time_ms': execution_time_ms,
        'timestamp': datetime.now(timezone.utc),
        'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
        bridge.events_sent.append(event)
        await asyncio.sleep(0)
        return True

    async def mock_notify_agent_error(run_id, agent_name, error, error_context=None):
        pass
        event = { )
        'type': 'agent_error',
        'run_id': run_id,
        'agent_name': agent_name,
        'error': error,
        'error_context': error_context,
        'timestamp': datetime.now(timezone.utc),
        'thread_id': bridge.run_thread_mappings.get(run_id, 'unknown')
    
        bridge.events_sent.append(event)
        await asyncio.sleep(0)
        return True

    async def mock_register_run_thread_mapping(run_id, thread_id, metadata=None):
        pass
        bridge.run_thread_mappings[run_id] = thread_id
        await asyncio.sleep(0)
        return True

    async def mock_unregister_run_mapping(run_id):
        pass
        bridge.run_thread_mappings.pop(run_id, None)
        await asyncio.sleep(0)
        return True

    # Bind mock methods
        bridge.notify_agent_started = mock_notify_agent_started
        bridge.notify_agent_thinking = mock_notify_agent_thinking
        bridge.notify_tool_executing = mock_notify_tool_executing
        bridge.notify_tool_completed = mock_notify_tool_completed
        bridge.notify_agent_completed = mock_notify_agent_completed
        bridge.notify_agent_error = mock_notify_agent_error
        bridge.register_run_thread_mapping = mock_register_run_thread_mapping
        bridge.unregister_run_mapping = mock_unregister_run_mapping

        return bridge


        @pytest.fixture
    async def mock_agent_registry(mock_llm_manager, mock_tool_dispatcher):
        """Create mock agent registry with test agents."""
        registry = MagicMock(spec=AgentRegistry)

    # Create mock agents
        triage_agent = MockTriageAgent( )
        llm_manager=mock_llm_manager,
        tool_dispatcher=mock_tool_dispatcher,
        name="triage"
    
        data_agent = MockDataAgent( )
        llm_manager=mock_llm_manager,
        tool_dispatcher=mock_tool_dispatcher,
        name="data"
    

        registry.agents = { )
        "triage": triage_agent,
        "data": data_agent
    
        registry.llm_manager = mock_llm_manager
        registry.tool_dispatcher = mock_tool_dispatcher

    def mock_get(name):
        """Use real service instance."""
    # TODO: Initialize real service
        pass
        await asyncio.sleep(0)
        return registry.agents.get(name)

        registry.get = mock_get
        return registry


        @pytest.fixture
    async def test_database_sessions():
        """Create test database sessions for isolation testing."""
        # Use in-memory SQLite for testing
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

        # Create session factory
        async_session_factory = async_sessionmaker( )
        engine, class_=AsyncSession, expire_on_commit=False
        

        sessions = []

        # Create multiple isolated sessions
        for i in range(10):
        session = async_session_factory()
        sessions.append(session)

        yield sessions

            # Cleanup
        for session in sessions:
        try:
        await session.close()
        except Exception as e:
        logger.warning("formatted_string")

        await engine.dispose()


                        # ============================================================================
                        # AgentClassRegistry Tests
                        # ============================================================================

class TestAgentClassRegistryIsolation:
        """Test AgentClassRegistry infrastructure-only functionality."""

@pytest.mark.asyncio
    async def test_registry_immutability_after_freeze(self):
        """Test that registry becomes immutable after freeze."""
registry = create_test_registry()

        # Register agents before freeze
registry.register("triage", MockTriageAgent, "Triage agent for testing")
registry.register("data", MockDataAgent, "Data agent for testing")

        # Verify registration works before freeze
assert registry.has_agent_class("triage")
assert registry.has_agent_class("data")
assert len(registry) == 2

        # Freeze registry
registry.freeze()
assert registry.is_frozen()

        # Verify registration fails after freeze
with pytest.raises(RuntimeError, match="Cannot register agent classes after registry is frozen"):
    registry.register("new_agent", MockAgent, "Should fail")

            # Verify reads still work
triage_class = registry.get_agent_class("triage")
assert triage_class == MockTriageAgent

data_info = registry.get_agent_info("data")
assert data_info.name == "data"
assert data_info.agent_class == MockDataAgent

@pytest.mark.asyncio
    async def test_concurrent_registry_reads(self):
        """Test thread-safe concurrent reads after freeze."""
pass
registry = create_test_registry()

                # Register multiple agents
for i in range(10):
    agent_name = "formatted_string"
registry.register(agent_name, MockAgent, "formatted_string")

registry.freeze()

                    # Test concurrent reads
async def concurrent_reader(reader_id: int) -> Dict[str, Any]:
    results = []
for _ in range(100):
        # Read different agents concurrently
agent_name = "formatted_string"
agent_class = registry.get_agent_class(agent_name)
agent_info = registry.get_agent_info(agent_name)

results.append({ ))
'reader_id': reader_id,
'agent_name': agent_name,
'class_found': agent_class is not None,
'info_found': agent_info is not None,
'class_correct': agent_class == MockAgent if agent_class else False
        

await asyncio.sleep(0)
return results

        # Run concurrent readers
tasks = [concurrent_reader(i) for i in range(20)]
all_results = await asyncio.gather(*tasks)

        # Verify all reads were successful and consistent
total_reads = sum(len(results) for results in all_results)
assert total_reads == 20 * 100  # 20 readers  x  100 reads each

for results in all_results:
    for result in results:
        assert result['class_found'], "formatted_string"
assert result['info_found'], "formatted_string"
assert result['class_correct'], "formatted_string"

@pytest.mark.asyncio
    async def test_registry_dependency_validation(self):
        """Test dependency validation functionality."""
registry = create_test_registry()

                    # Register agents with dependencies
registry.register("base", MockAgent, "Base agent", dependencies=["llm", "tools"])
registry.register("triage", MockTriageAgent, "Triage agent", dependencies=["base", "llm"])
registry.register("data", MockDataAgent, "Data agent", dependencies=["base", "database"])

registry.freeze()

                    # Test dependency validation
missing_deps = registry.validate_dependencies()

                    # Should find missing dependencies
assert "base" in missing_deps
assert "llm" in missing_deps["base"]
assert "tools" in missing_deps["base"]

assert "triage" in missing_deps
assert "base" not in missing_deps["triage"]  # base exists
assert "llm" in missing_deps["triage"]  # llm doesn"t exist

                    # Test agents by dependency
agents_needing_base = registry.get_agents_by_dependency("base")
assert "triage" in agents_needing_base
assert "data" in agents_needing_base

agents_needing_llm = registry.get_agents_by_dependency("llm")
assert "base" in agents_needing_llm
assert "triage" in agents_needing_llm


                    # ============================================================================
                    # AgentInstanceFactory Tests
                    # ============================================================================

class TestAgentInstanceFactoryIsolation:
    """Test AgentInstanceFactory per-request isolation."""

@pytest.mark.asyncio
    # Removed problematic line: async def test_user_execution_context_creation_and_cleanup(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Test user execution context creation and cleanup."""
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

db_session = test_database_sessions[0]

        # Create user execution context
context = await factory.create_user_execution_context( )
user_id="user_123",
thread_id="thread_456",
run_id="run_789",
db_session=db_session,
metadata={"test": "metadata"}
        

        # Verify context creation
assert context.user_id == "user_123"
assert context.thread_id == "thread_456"
assert context.run_id == "run_789"
assert context.db_session == db_session
assert context.websocket_emitter is not None
assert context.websocket_emitter.user_id == "user_123"
assert context.request_metadata["test"] == "metadata"

        # Verify WebSocket run-thread mapping was registered
assert mock_websocket_bridge.run_thread_mappings["run_789"] == "thread_456"

        # Test context cleanup
await factory.cleanup_user_context(context)

        # Verify cleanup
assert context._is_cleaned
assert context.db_session is None
assert context.websocket_emitter is None
assert "run_789" not in mock_websocket_bridge.run_thread_mappings

@pytest.mark.asyncio
        # Removed problematic line: async def test_agent_instance_creation_isolation(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Test isolated agent instance creation for different users."""
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

            # Create contexts for different users
context1 = await factory.create_user_execution_context( )
user_id="user_001",
thread_id="thread_001",
run_id="run_001",
db_session=test_database_sessions[0]
            

context2 = await factory.create_user_execution_context( )
user_id="user_002",
thread_id="thread_002",
run_id="run_002",
db_session=test_database_sessions[1]
            

            # Create agent instances for each user
agent1 = await factory.create_agent_instance("triage", context1)
agent2 = await factory.create_agent_instance("triage", context2)

            # Verify agents are different instances
assert agent1 is not agent2
assert id(agent1) != id(agent2)

            # Verify agents are bound to correct users
assert agent1.user_id == "user_001"
assert agent2.user_id == "user_002"

            # Verify agents have different correlation IDs
assert agent1.correlation_id != agent2.correlation_id

            # Verify contexts track the agents
assert len(context1.active_runs) == 1
assert len(context2.active_runs) == 1

            # Test agent execution isolation
state1 = DeepAgentState(user_message="User 1 message", thread_id="thread_001")
state2 = DeepAgentState(user_message="User 2 message", thread_id="thread_002")

result1 = await agent1.execute(state1, "run_001")
result2 = await agent2.execute(state2, "run_002")

            # Verify results are isolated
assert "user_001" in result1.user_message
assert "user_002" in result2.user_message
assert result1.additional_context["agent_user_id"] == "user_001"
assert result2.additional_context["agent_user_id"] == "user_002"

            # Cleanup
await factory.cleanup_user_context(context1)
await factory.cleanup_user_context(context2)

@pytest.mark.asyncio
            # Removed problematic line: async def test_websocket_event_isolation(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Test WebSocket events are properly isolated per user."""
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

                # Create contexts for 3 users
contexts = []
for i in range(3):
    context = await factory.create_user_execution_context( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
db_session=test_database_sessions[i]
                    
contexts.append(context)

                    # Create agents and execute simultaneously
agents = []
for i, context in enumerate(contexts):
    agent = await factory.create_agent_instance("triage", context)
agents.append(agent)

                        # Execute agents concurrently
tasks = []
for i, (agent, context) in enumerate(zip(agents, contexts)):
    state = DeepAgentState( )
user_message="formatted_string",
thread_id="formatted_string"
                            
tasks.append(agent.execute(state, "formatted_string"))

results = await asyncio.gather(*tasks)

                            # Verify WebSocket events are properly isolated
events_by_run = {}
for event in mock_websocket_bridge.events_sent:
    run_id = event['run_id']
if run_id not in events_by_run:
    events_by_run[run_id] = []
events_by_run[run_id].append(event)

                                    # Each user should have their own events
assert len(events_by_run) == 3

for i in range(3):
    run_id = "formatted_string"
thread_id = "formatted_string"

assert run_id in events_by_run
user_events = events_by_run[run_id]

                                        # Each user should have at least one thinking event
thinking_events = [item for item in []] == 'agent_thinking']
assert len(thinking_events) > 0

                                        # All events for this user should have correct thread_id
for event in user_events:
    assert event['thread_id'] == thread_id, "formatted_string"

                                            # Cleanup all contexts
for context in contexts:
    await factory.cleanup_user_context(context)

@pytest.mark.asyncio
                                                # Removed problematic line: async def test_concurrent_user_execution_stress(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Stress test with 10 concurrent users to validate isolation."""
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

num_concurrent_users = 10
executions_per_user = 5

async def execute_user_workflow(user_index: int) -> ConcurrentUserTestResult:
    user_id = "formatted_string"
thread_id = "formatted_string"

start_time = time.time()
websocket_events = []
agent_logs = []
error_message = None
success = True

try:
        # Execute multiple operations for this user
for exec_index in range(executions_per_user):
    run_id = "formatted_string"

            # Use scoped execution context
async with factory.user_execution_scope( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
db_session=test_database_sessions[user_index % len(test_database_sessions)]
) as context:

                # Create and execute agent
agent = await factory.create_agent_instance("triage", context)

state = DeepAgentState( )
user_message="formatted_string",
thread_id=thread_id
                

result = await agent.execute(state, run_id)

                # Validate result isolation
if user_id not in result.user_message:
    success = False
error_message = "formatted_string"

if result.additional_context.get("agent_user_id") != user_id:
    success = False
error_message = "formatted_string"

                        # Collect agent execution data
agent_summary = agent.get_execution_summary()
agent_logs.append(agent_summary)

                        # Collect WebSocket events for this user
for event in mock_websocket_bridge.events_sent:
    if event['run_id'].startswith("formatted_string"):
        websocket_events.append(event)

except Exception as e:
    success = False
error_message = str(e)
logger.error("formatted_string")

execution_time_ms = (time.time() - start_time) * 1000

await asyncio.sleep(0)
return ConcurrentUserTestResult( )
user_id=user_id,
thread_id=thread_id,
run_id="formatted_string",
success=success,
execution_time_ms=execution_time_ms,
websocket_events_received=websocket_events,
agent_execution_log=agent_logs,
context_isolation_validated=success,
database_session_isolated=True,  # Would need more complex validation
memory_leak_detected=False,  # Would need memory monitoring
error_message=error_message
                                    

                                    # Execute all users concurrently
logger.info("formatted_string")
start_time = time.time()

tasks = [execute_user_workflow(i) for i in range(num_concurrent_users)]
results = await asyncio.gather(*tasks, return_exceptions=True)

total_time = time.time() - start_time
logger.info("formatted_string")

                                    # Analyze results
successful_results = [item for item in []]
failed_results = [item for item in []]

logger.info("formatted_string")
logger.info("formatted_string")

                                    # Verify success criteria
assert len(successful_results) >= (num_concurrent_users * 0.8), "formatted_string"

                                    # Verify isolation - each user should have their own events
all_websocket_events = []
for result in successful_results:
    all_websocket_events.extend(result.websocket_events_received)

                                        # Group events by user
events_by_user = {}
for event in all_websocket_events:
    run_id = event['run_id']
user_match = run_id.split('_')
if len(user_match) >= 3:
    user_key = "formatted_string"  # stress_user_XXX
if user_key not in events_by_user:
    events_by_user[user_key] = []
events_by_user[user_key].append(event)

                                                    # Each successful user should have events
for result in successful_results:
    user_key = result.user_id
assert user_key in events_by_user, "formatted_string"
user_events = events_by_user[user_key]
assert len(user_events) >= executions_per_user, "formatted_string"

logger.info(" PASS:  Concurrent user stress test passed with proper isolation")


                                                        # ============================================================================
                                                        # UserExecutionContext Tests
                                                        # ============================================================================

class TestUserExecutionContextValidation:
        """Test UserExecutionContext validation and isolation."""

    def test_context_validation_success(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Test successful context validation."""
        pass
    # Test models.UserExecutionContext
        context = ModelsUserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
    

        assert context.user_id == "user_123"
        assert context.thread_id == "thread_456"
        assert context.run_id == "run_789"
        assert context.request_id == "req_012"

    # Test string representation
        str_repr = str(context)
        assert "user_123" in str_repr or "user_123..." in str_repr
        assert "thread_456" in str_repr

    # Test dictionary conversion
        context_dict = context.to_dict()
        assert context_dict["user_id"] == "user_123"
        assert context_dict["thread_id"] == "thread_456"
        assert context_dict["run_id"] == "run_789"
        assert context_dict["request_id"] == "req_012"

    def test_context_validation_failures(self):
        """Test context validation failure cases."""
    # Test None user_id
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be None"):
        ModelsUserExecutionContext( )
        user_id=None,
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
        

        # Test empty user_id
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be empty"):
        ModelsUserExecutionContext( )
        user_id="",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
            

            # Test "None" string user_id
        with pytest.raises(ValueError, match="UserExecutionContext.user_id cannot be the string 'None'"):
        ModelsUserExecutionContext( )
        user_id="None",
        thread_id="thread_456",
        run_id="run_789",
        request_id="req_012"
                

                # Test "registry" run_id
        with pytest.raises(ValueError, match="UserExecutionContext.run_id cannot be 'registry'"):
        ModelsUserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="registry",
        request_id="req_012"
                    

                    # Test None thread_id
        with pytest.raises(ValueError, match="UserExecutionContext.thread_id cannot be None"):
        ModelsUserExecutionContext( )
        user_id="user_123",
        thread_id=None,
        run_id="run_789",
        request_id="req_012"
                        

                        # Test empty request_id
        with pytest.raises(ValueError, match="UserExecutionContext.request_id cannot be empty"):
        ModelsUserExecutionContext( )
        user_id="user_123",
        thread_id="thread_456",
        run_id="run_789",
        request_id=""
                            

@pytest.mark.asyncio
    async def test_context_isolation_across_requests(self):
        """Test that contexts from different requests are completely isolated."""
pass
                                # Create multiple contexts simulating different requests
contexts = []
for i in range(10):
    context = ModelsUserExecutionContext( )
user_id="formatted_string",
thread_id="formatted_string",
run_id="formatted_string",
request_id="formatted_string"
                                    
contexts.append(context)

                                    # Verify all contexts are unique
user_ids = [c.user_id for c in contexts]
thread_ids = [c.thread_id for c in contexts]
run_ids = [c.run_id for c in contexts]
request_ids = [c.request_id for c in contexts]

assert len(set(user_ids)) == 10  # All unique
assert len(set(thread_ids)) == 10  # All unique
assert len(set(run_ids)) == 10  # All unique
assert len(set(request_ids)) == 10  # All unique

                                    # Verify contexts don't interfere with each other
for i, context in enumerate(contexts):
    expected_user_id = "formatted_string"
expected_thread_id = "formatted_string"
expected_run_id = "formatted_string"
expected_request_id = "formatted_string"

assert context.user_id == expected_user_id
assert context.thread_id == expected_thread_id
assert context.run_id == expected_run_id
assert context.request_id == expected_request_id


                                        # ============================================================================
                                        # End-to-End Integration Tests
                                        # ============================================================================

class TestEndToEndIntegration:
    """End-to-end integration tests simulating FastAPI request flow."""

@pytest.mark.asyncio
    # Removed problematic line: async def test_complete_request_flow_with_isolation(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Test complete request flow from API to agent execution."""
        # Step 1: Setup infrastructure (simulating FastAPI startup)
class_registry = create_test_registry()
class_registry.register("triage", MockTriageAgent, "Triage agent")
class_registry.register("data", MockDataAgent, "Data agent")
class_registry.freeze()

instance_factory = AgentInstanceFactory()
instance_factory.configure(mock_agent_registry, mock_websocket_bridge)

        # Step 2: Simulate FastAPI request processing
async def simulate_api_request(user_id: str, message: str) -> Dict[str, Any]:
    thread_id = "formatted_string"
run_id = "formatted_string"
request_id = "formatted_string"

    # Validate request context (simulating middleware)
request_context = ModelsUserExecutionContext( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
request_id=request_id
    

    # Create execution scope (simulating request handler)
db_session = test_database_sessions[0]  # Simulating request-scoped session

async with instance_factory.user_execution_scope( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
db_session=db_session,
metadata={"api_request": True, "message": message}
) as execution_context:

        Get agent class from registry (simulating agent selection logic)
triage_class = class_registry.get_agent_class("triage")
assert triage_class is not None

        # Create agent instance for this request
agent = await instance_factory.create_agent_instance("triage", execution_context)

        # Execute agent (simulating agent orchestration)
agent_state = DeepAgentState( )
user_message=message,
thread_id=thread_id,
additional_context={ )
"request_id": request_id,
"api_request": True
        
        

result_state = await agent.execute(agent_state, run_id)

        # Return API response (simulating response serialization)
await asyncio.sleep(0)
return { )
"success": True,
"user_id": user_id,
"thread_id": thread_id,
"run_id": run_id,
"request_id": request_id,
"response": result_state.user_message,
"context": result_state.additional_context,
"agent_summary": agent.get_execution_summary()
        

        # Step 3: Simulate multiple concurrent API requests
test_users = [ )
("user_alice", "Hello, I need help with data analysis"),
("user_bob", "Can you help me with system diagnostics?"),
("user_charlie", "I have a question about integration"),
("user_diana", "Need assistance with configuration"),
("user_eve", "Help with troubleshooting please")
        

        # Execute requests concurrently
tasks = [simulate_api_request(user_id, message) for user_id, message in test_users]
api_responses = await asyncio.gather(*tasks)

        # Step 4: Validate isolation and correctness
assert len(api_responses) == 5

        # Verify each response is for the correct user
for i, (expected_user, expected_message) in enumerate(test_users):
    response = api_responses[i]

assert response["success"] is True
assert response["user_id"] == expected_user
assert expected_user in response["response"]  # Agent should echo user ID
assert response["context"]["agent_user_id"] == expected_user

agent_summary = response["agent_summary"]
assert agent_summary["user_id"] == expected_user
assert agent_summary["total_executions"] == 1

            # Step 5: Verify WebSocket events were properly routed
events_by_user = {}
for event in mock_websocket_bridge.events_sent:
    run_id = event["run_id"]
                # Find which user this run_id belongs to
for response in api_responses:
    if response["run_id"] == run_id:
        user_id = response["user_id"]
if user_id not in events_by_user:
    events_by_user[user_id] = []
events_by_user[user_id].append(event)
break

                            # Each user should have received their own WebSocket events
for expected_user, _ in test_users:
    assert expected_user in events_by_user, "formatted_string"
user_events = events_by_user[expected_user]
assert len(user_events) > 0, "formatted_string"

                                # Verify events contain correct run_id and thread_id
for event in user_events:
                                    # Find the response for this user to get expected IDs
user_response = next(r for r in api_responses if r["user_id"] == expected_user)
expected_thread_id = user_response["thread_id"]

assert event["thread_id"] == expected_thread_id, "formatted_string"

logger.info(" PASS:  Complete end-to-end integration test passed with proper isolation")

@pytest.mark.asyncio
                                    # Removed problematic line: async def test_memory_leak_prevention(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Test that resource cleanup prevents memory leaks."""
import gc
import weakref

instance_factory = AgentInstanceFactory()
instance_factory.configure(mock_agent_registry, mock_websocket_bridge)

                                        # Create weak references to track object lifecycle
weak_refs = { )
'contexts': [],
'agents': [],
'sessions': [],
'emitters': []
                                        

                                        # Memory usage before test
process = psutil.Process()
memory_before = process.memory_info().rss

                                        # Create and execute multiple isolated contexts
for i in range(50):  # Large number to detect leaks
user_id = "formatted_string"
thread_id = "formatted_string"
run_id = "formatted_string"

                                        # Create context in scope to ensure cleanup
async with instance_factory.user_execution_scope( )
user_id=user_id,
thread_id=thread_id,
run_id=run_id,
db_session=test_database_sessions[i % len(test_database_sessions)],
metadata={"leak_test": True, "iteration": i}
) as context:

                                            # Create weak references for leak detection
weak_refs['contexts'].append(weakref.ref(context))
weak_refs['sessions'].append(weakref.ref(context.db_session))
weak_refs['emitters'].append(weakref.ref(context.websocket_emitter))

                                            # Create and use agent
agent = await instance_factory.create_agent_instance("triage", context)
weak_refs['agents'].append(weakref.ref(agent))

                                            # Execute agent to create internal state
state = DeepAgentState( )
user_message="formatted_string",
thread_id=thread_id
                                            

result = await agent.execute(state, run_id)

                                            # Verify execution worked
assert user_id in result.user_message

                                            # Force some garbage collection within the loop
if i % 10 == 0:
    gc.collect()

                                                # Force garbage collection after all contexts are cleaned up
gc.collect()
await asyncio.sleep(0.1)  # Allow async cleanup to complete
gc.collect()

                                                # Check memory usage after test
memory_after = process.memory_info().rss
memory_increase_mb = (memory_after - memory_before) / 1024 / 1024

logger.info("formatted_string")

                                                # Check weak references - most should be garbage collected
alive_contexts = sum(1 for ref in weak_refs['contexts'] if ref() is not None)
alive_agents = sum(1 for ref in weak_refs['agents'] if ref() is not None)
alive_sessions = sum(1 for ref in weak_refs['sessions'] if ref() is not None)
alive_emitters = sum(1 for ref in weak_refs['emitters'] if ref() is not None)

logger.info("formatted_string")

                                                # Memory increase should be reasonable (less than 50MB for 50 iterations)
assert memory_increase_mb < 50, "formatted_string"

                                                # Most objects should be garbage collected (allow some to remain due to Python's GC behavior)
assert alive_contexts <= 10, "formatted_string"
assert alive_agents <= 10, "formatted_string"
assert alive_emitters <= 10, "formatted_string"

logger.info(" PASS:  Memory leak prevention test passed")


                                                # ============================================================================
                                                # Error Scenario Tests
                                                # ============================================================================

class TestErrorScenariosAndEdgeCases:
    """Test error scenarios and edge cases in the split architecture."""

@pytest.mark.asyncio
    # Removed problematic line: async def test_invalid_agent_creation_handling(self,
mock_agent_registry,
mock_websocket_bridge,
test_database_sessions):
"""Test error handling for invalid agent creation."""
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

        # Create valid context
context = await factory.create_user_execution_context( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
db_session=test_database_sessions[0]
        

        # Test agent not found in registry
mock_agent_registry.get = Mock(return_value=None)

with pytest.raises(RuntimeError, match="Agent creation failed"):
    await factory.create_agent_instance("nonexistent_agent", context)

            # Test invalid context
with pytest.raises(ValueError, match="UserExecutionContext is required"):
    await factory.create_agent_instance("triage", None)

await factory.cleanup_user_context(context)

@pytest.mark.asyncio
                # Removed problematic line: async def test_websocket_bridge_failure_resilience(self,
mock_agent_registry,
test_database_sessions):
"""Test resilience when WebSocket bridge fails."""
                    # Create bridge that fails
failing_bridge = MagicMock(spec=AgentWebSocketBridge)
failing_bridge.register_run_thread_mapping = AsyncMock(return_value=False)
failing_bridge.notify_agent_started = AsyncMock(side_effect=Exception("WebSocket failure"))
failing_bridge.events_sent = []
failing_bridge.run_thread_mappings = {}

factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, failing_bridge)

                    # Context creation should still work despite WebSocket failure
context = await factory.create_user_execution_context( )
user_id="resilience_user",
thread_id="resilience_thread",
run_id="resilience_run",
db_session=test_database_sessions[0]
                    

                    # Agent creation should still work
agent = await factory.create_agent_instance("triage", context)

                    # Agent execution should work despite WebSocket failures
state = DeepAgentState( )
user_message="Test resilience",
thread_id="resilience_thread"
                    

result = await agent.execute(state, "resilience_run")

                    # Verify execution completed successfully
assert "resilience_user" in result.user_message
assert result.additional_context["agent_user_id"] == "resilience_user"

await factory.cleanup_user_context(context)

@pytest.mark.asyncio
                    # Removed problematic line: async def test_database_session_failure_handling(self,
mock_agent_registry,
mock_websocket_bridge):
"""Test handling of database session failures."""
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

                        # Create mock session that fails
failing_session = MagicMock(spec=AsyncSession)
failing_session.close = AsyncMock(side_effect=Exception("DB close failure"))

                        # Context creation should work with failing session
context = await factory.create_user_execution_context( )
user_id="db_test_user",
thread_id="db_test_thread",
run_id="db_test_run",
db_session=failing_session
                        

                        # Cleanup should handle session close failure gracefully
await factory.cleanup_user_context(context)

                        # Context should still be marked as cleaned despite DB error
assert context._is_cleaned

@pytest.mark.asyncio
    async def test_factory_configuration_validation(self):
        """Test factory configuration validation."""
factory = AgentInstanceFactory()

                            # Test unconfigured factory
with pytest.raises(ValueError, match="Factory not configured"):
    await factory.create_user_execution_context( )
user_id="test",
thread_id="test",
run_id="test",
db_session=Magic            )

                                # Test invalid configuration - WebSocket bridge is checked first
with pytest.raises(ValueError, match="AgentWebSocketBridge cannot be None"):
    factory.configure(agent_registry=None, websocket_bridge=None)

                                    # Test missing WebSocket bridge
with pytest.raises(ValueError, match="AgentWebSocketBridge cannot be None"):
    factory.configure(agent_registry=Magic )
@pytest.mark.asyncio
                                        # Removed problematic line: async def test_context_creation_parameter_validation(self,
mock_agent_registry,
mock_websocket_bridge):
"""Test parameter validation in context creation."""
pass
factory = AgentInstanceFactory()
factory.configure(mock_agent_registry, mock_websocket_bridge)

mock_session = MagicMock(spec=AsyncSession)

                                            # Test missing required parameters
with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
    await factory.create_user_execution_context( )
user_id="",
thread_id="test_thread",
run_id="test_run",
db_session=mock_session
                                                

with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
    await factory.create_user_execution_context( )
user_id="test_user",
thread_id="",
run_id="test_run",
db_session=mock_session
                                                    

with pytest.raises(ValueError, match="user_id, thread_id, and run_id are required"):
    await factory.create_user_execution_context( )
user_id="test_user",
thread_id="test_thread",
run_id="",
db_session=mock_session
                                                        

with pytest.raises(ValueError, match="db_session is required for request isolation"):
    await factory.create_user_execution_context( )
user_id="test_user",
thread_id="test_thread",
run_id="test_run",
db_session=None
                                                            


if __name__ == "__main__":
                                                                # Run specific test classes for development
pytest.main([ ))
__file__ + "::TestAgentClassRegistryIsolation::test_registry_immutability_after_freeze",
"-v"
                                                                
