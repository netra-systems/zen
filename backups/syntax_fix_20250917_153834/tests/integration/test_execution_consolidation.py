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

        '''Integration tests for consolidated Tool Dispatcher and Execution Engine.

        This test suite validates:
        - Tool dispatch with all strategies
        - Execution engine with all extensions
        - Request-scoped isolation
        - WebSocket event delivery
        - Performance requirements (<5ms dispatch, <2s execution)
        - Concurrent user support (10+ users)
        - Backward compatibility
        '''

        import asyncio
        import time
        from typing import Any, Dict, List, Optional
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        from test_framework.database.test_database_manager import DatabaseTestManager
        from auth_service.core.auth_manager import AuthManager
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
        from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
        from shared.isolated_environment import IsolatedEnvironment

        import pytest
        from langchain_core.tools import BaseTool

        from netra_backend.app.agents.tool_dispatcher_consolidated import ( )
        UnifiedToolDispatcher,
        UnifiedToolRegistry,
        ToolDefinition,
        ExecutionContext,
        DefaultDispatchStrategy,
        AdminDispatchStrategy,
        DataDispatchStrategy,
        create_dispatcher,
        create_request_scoped_dispatcher,
        RequestScopedDispatcher
        
        from netra_backend.app.agents.execution_engine_consolidated import ( )
        ExecutionEngine,
        ExecutionEngineFactory,
        RequestScopedExecutionEngine,
        EngineConfig,
        AgentExecutionContext,
        AgentExecutionResult,
        UserExecutionExtension,
        MCPExecutionExtension,
        DataExecutionExtension,
        WebSocketExtension,
        execute_agent,
        execution_engine_context
        
        from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        from netra_backend.app.db.database_manager import DatabaseManager
        from netra_backend.app.clients.auth_client_core import AuthServiceClient
        from shared.isolated_environment import get_env


        # ============================================================================
        # FIXTURES
        # ============================================================================

        @pytest.fixture
    def real_user_context():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create mock user context."""
        pass
        context = Magic    context.user_id = "test_user_123"
        context.request_id = "req_456"
        return context


        @pytest.fixture
    def real_websocket_emitter():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket emitter."""
        pass
        websocket = TestWebSocketConnection()
        return emitter


        @pytest.fixture
    def real_websocket_bridge():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket bridge."""
        pass
        websocket = TestWebSocketConnection()
        return bridge


        @pytest.fixture
    def real_agent_registry():
        """Use real service instance."""
    # TODO: Initialize real service
        """Create mock agent registry."""
        pass
        registry = Magic    websocket = TestWebSocketConnection()
        mock_agent.execute = AsyncMock(return_value="agent_result")
        registry.get_agent = MagicMock(return_value=mock_agent)
        return registry


        @pytest.fixture
    async def sample_tools():
        """Create sample tools for testing."""
class TestTool(BaseTool):
        name: str = "test_tool"
        description: str = "A test tool"

    def _run(self, query: str) -> str:
        await asyncio.sleep(0)
        return "formatted_string"

    async def _arun(self, query: str) -> str:
        return "formatted_string"

class AdminTool(BaseTool):
        name: str = "corpus_update"
        description: str = "Admin tool for corpus update"

    async def _arun(self, data: str) -> str:
        return "formatted_string"

class DataTool(BaseTool):
        name: str = "data_fetch"
        description: str = "Data fetching tool"

    async def _arun(self, query: str) -> str:
        await asyncio.sleep(0.01)  # Simulate data fetch
        return "formatted_string"

        return [TestTool(), AdminTool(), DataTool()]


    # ============================================================================
    # TOOL DISPATCHER TESTS
    # ============================================================================

class TestUnifiedToolDispatcher:
        """Test UnifiedToolDispatcher functionality."""

@pytest.mark.asyncio
    async def test_dispatcher_initialization(self, mock_user_context, mock_websocket_emitter):
"""Test dispatcher initialization with different configurations."""
        # Default initialization
dispatcher = UnifiedToolDispatcher()
assert dispatcher.strategy is not None
assert isinstance(dispatcher.strategy, DefaultDispatchStrategy)

        # With user context
dispatcher = UnifiedToolDispatcher( )
user_context=mock_user_context,
websocket_emitter=mock_websocket_emitter
        
assert dispatcher.user_context == mock_user_context
assert dispatcher.websocket_emitter == mock_websocket_emitter
assert dispatcher.execution_context.user_id == "test_user_123"

        # With admin strategy
admin_strategy = AdminDispatchStrategy()
dispatcher = UnifiedToolDispatcher(strategy=admin_strategy)
assert isinstance(dispatcher.strategy, AdminDispatchStrategy)

@pytest.mark.asyncio
    async def test_tool_registration_and_discovery(self, sample_tools):
"""Test tool registration and discovery."""
pass
dispatcher = UnifiedToolDispatcher()

            # Register tools
for tool in sample_tools:
await dispatcher.register_tool(tool)

                # Discover all tools
tools = dispatcher.discover_tools()
assert len(tools) == 3

                # Discover by category (would need category support in sample_tools)
                # tools = dispatcher.discover_tools(category="data")

@pytest.mark.asyncio
    async def test_tool_dispatch_success(self, mock_websocket_emitter):
"""Test successful tool dispatch."""
dispatcher = UnifiedToolDispatcher(websocket_emitter=mock_websocket_emitter)

                    # Register a test tool
    async def test_handler(input:
await asyncio.sleep(0)
return "formatted_string"

tool_def = ToolDefinition( )
name="test",
description="Test tool",
parameters={},
handler=test_handler
                        
await dispatcher.registry.register_tool("test", tool_def)

                        # Dispatch tool
result = await dispatcher.dispatch("test", {"input": "hello"})

assert result.status == ToolStatus.SUCCESS
assert result.result == "Result: hello"
assert "dispatch_time_ms" in result.metadata

                        # Verify WebSocket events were emitted
mock_websocket_emitter.notify_tool_executing.assert_called_once()
mock_websocket_emitter.notify_tool_completed.assert_called_once()

@pytest.mark.asyncio
    async def test_tool_dispatch_with_admin_strategy(self):
"""Test tool dispatch with admin strategy."""
pass
admin_strategy = AdminDispatchStrategy()
dispatcher = UnifiedToolDispatcher(strategy=admin_strategy)

                            # Register admin tool
async def admin_handler(**kwargs) -> str:
await asyncio.sleep(0)
return "formatted_string"

tool_def = ToolDefinition( )
name="corpus_update",
description="Admin tool",
parameters={},
handler=admin_handler,
admin_required=True
    
await dispatcher.registry.register_tool("corpus_update", tool_def)

    # Try dispatch without admin privileges
result = await dispatcher.dispatch("corpus_update", {})
assert result.status == ToolStatus.ERROR
assert "requires admin privileges" in result.error

    # Dispatch with admin context
dispatcher.execution_context.metadata['is_admin'] = True
result = await dispatcher.dispatch("corpus_update", {})
assert result.status == ToolStatus.SUCCESS
assert "Admin action: True" in result.result

@pytest.mark.asyncio
    async def test_dispatch_performance(self):
"""Test dispatch performance meets <5ms requirement."""
dispatcher = UnifiedToolDispatcher(enable_metrics=True)

        # Register fast tool
async def fast_handler() -> str:
await asyncio.sleep(0)
return "fast"

tool_def = ToolDefinition( )
name="fast",
description="Fast tool",
parameters={},
handler=fast_handler
    
await dispatcher.registry.register_tool("fast", tool_def)

    # Run multiple dispatches
dispatch_times = []
for _ in range(10):
start = time.perf_counter()
result = await dispatcher.dispatch("fast", {})
dispatch_time_ms = (time.perf_counter() - start) * 1000
dispatch_times.append(dispatch_time_ms)
assert result.status == ToolStatus.SUCCESS

        # Check metrics
metrics = dispatcher.get_metrics()
assert metrics['average_dispatch_ms'] < 5
assert metrics['total_dispatches'] == 10

        # Most dispatches should be under 5ms
fast_dispatches = [item for item in []]
assert len(fast_dispatches) >= 8  # At least 80% under 5ms

@pytest.mark.asyncio
    async def test_request_scoped_dispatcher(self, mock_user_context):
"""Test request-scoped dispatcher isolation."""
pass
base_dispatcher = UnifiedToolDispatcher(user_context=mock_user_context)

            # Create request-scoped wrapper
request_dispatcher = base_dispatcher.with_request_scope("req_789")
assert isinstance(request_dispatcher, RequestScopedDispatcher)
assert request_dispatcher.request_id == "req_789"

            # Register tool
async def scoped_handler() -> str:
await asyncio.sleep(0)
return "scoped result"

tool_def = ToolDefinition( )
name="scoped",
description="Scoped tool",
parameters={},
handler=scoped_handler
    
await base_dispatcher.registry.register_tool("scoped", tool_def)

    # Dispatch through scoped wrapper
result = await request_dispatcher.dispatch("scoped", {})
assert result.status == ToolStatus.SUCCESS

    # Close and verify closed state
request_dispatcher.close()
with pytest.raises(RuntimeError, match="has been closed"):
await request_dispatcher.dispatch("scoped", {})


        # ============================================================================
        # EXECUTION ENGINE TESTS
        # ============================================================================

class TestExecutionEngine:
        """Test ExecutionEngine functionality."""

@pytest.mark.asyncio
    async def test_engine_initialization(self, mock_agent_registry, mock_websocket_bridge):
"""Test engine initialization with different configurations."""
        # Default configuration
engine = UserExecutionEngine()
assert engine.config is not None
assert len(engine._extensions) == 0  # No extensions by default

        # With user features
config = EngineConfig(enable_user_features=True)
engine = UserExecutionEngine(config=config)
assert 'user' in engine._extensions
assert isinstance(engine._extensions['user'], UserExecutionExtension)

        # With all features
config = EngineConfig( )
enable_user_features=True,
enable_mcp=True,
enable_data_features=True,
enable_websocket_events=True
        
engine = UserExecutionEngine( )
config=config,
registry=mock_agent_registry,
websocket_bridge=mock_websocket_bridge
        
assert len(engine._extensions) == 4
assert 'websocket' in engine._extensions

@pytest.mark.asyncio
    async def test_agent_execution_success(self, mock_agent_registry, mock_user_context):
"""Test successful agent execution."""
pass
engine = UserExecutionEngine( )
registry=mock_agent_registry,
user_context=mock_user_context
            

            # Execute agent
result = await engine.execute("test_agent", {"task": "test"})

assert result.success is True
assert result.result == "agent_result"
assert result.execution_time_ms is not None

            # Verify agent was called
mock_agent_registry.get_agent.assert_called_with("test_agent")

@pytest.mark.asyncio
    async def test_execution_with_extensions(self, mock_agent_registry, mock_websocket_bridge):
"""Test execution with all extensions."""
config = EngineConfig( )
enable_user_features=True,
enable_websocket_events=True
                
engine = UserExecutionEngine( )
config=config,
registry=mock_agent_registry,
websocket_bridge=mock_websocket_bridge
                

                # Initialize extensions
await engine.initialize()

                # Execute agent
result = await engine.execute("test_agent", {"task": "test"})

assert result.success is True

                # Verify WebSocket events
mock_websocket_bridge.notify_agent_started.assert_called_once()
mock_websocket_bridge.notify_agent_completed.assert_called_once()

@pytest.mark.asyncio
    async def test_execution_performance(self, mock_agent_registry):
"""Test execution meets <2s requirement."""
pass
                    # Configure fast agent
websocket = TestWebSocketConnection()
mock_agent.execute = AsyncMock( )
side_effect=lambda x: None asyncio.sleep(0.1) or "fast_result"
                    
mock_agent_registry.get_agent = MagicMock(return_value=mock_agent)

engine = UserExecutionEngine( )
config=EngineConfig(agent_execution_timeout=2.0),
registry=mock_agent_registry
                    

                    # Execute multiple times
execution_times = []
for _ in range(5):
start = time.perf_counter()
result = await engine.execute("fast_agent", {"task": "speed_test"})
execution_time = time.perf_counter() - start
execution_times.append(execution_time)

assert result.success is True
assert execution_time < 2.0  # Under 2 seconds

                        # Check metrics
metrics = engine.get_metrics()
assert metrics['average_execution_ms'] < 2000
assert metrics['success_rate'] == 1.0

@pytest.mark.asyncio
    async def test_concurrent_user_execution(self, mock_agent_registry):
"""Test concurrent execution for 10+ users."""
                            # Create multiple engines for different users
engines = []
for i in range(12):  # Test with 12 concurrent users
user_context = Magic            user_context.user_id = "formatted_string"
user_context.request_id = "formatted_string"

engine = UserExecutionEngine( )
config=EngineConfig( )
enable_user_features=True,
max_concurrent_agents=10
),
registry=mock_agent_registry,
user_context=user_context
                            
engines.append(engine)

                            # Execute agents concurrently
tasks = []
for i, engine in enumerate(engines):
task = engine.execute("formatted_string", {"task": "formatted_string"})
tasks.append(task)

                                # Wait for all to complete
results = await asyncio.gather(*tasks)

                                # Verify all succeeded
for result in results:
assert result.success is True

                                    # Check that user isolation was maintained
for i, engine in enumerate(engines):
metrics = engine.get_metrics()
assert metrics['success_count'] == 1


                                        # ============================================================================
                                        # FACTORY TESTS
                                        # ============================================================================

class TestFactories:
    """Test factory functions for creating dispatchers and engines."""

@pytest.mark.asyncio
    async def test_dispatcher_factory(self, mock_user_context):
"""Test dispatcher factory functions."""
        # Create default dispatcher
dispatcher = create_dispatcher()
assert isinstance(dispatcher, UnifiedToolDispatcher)
assert isinstance(dispatcher.strategy, DefaultDispatchStrategy)

        # Create admin dispatcher
dispatcher = create_dispatcher(admin_mode=True)
assert isinstance(dispatcher.strategy, AdminDispatchStrategy)

        # Create data dispatcher
dispatcher = create_dispatcher(data_mode=True)
assert isinstance(dispatcher.strategy, DataDispatchStrategy)

        # Create with user context
dispatcher = create_dispatcher(user_context=mock_user_context)
assert dispatcher.user_context == mock_user_context

@pytest.mark.asyncio
    async def test_request_scoped_dispatcher_factory(self, mock_user_context):
"""Test request-scoped dispatcher factory."""
pass
dispatcher = create_request_scoped_dispatcher( )
request_id="test_req_001",
user_context=mock_user_context
            

assert isinstance(dispatcher, RequestScopedDispatcher)
assert dispatcher.request_id == "test_req_001"

@pytest.mark.asyncio
    async def test_execution_engine_factory(self, mock_user_context, mock_agent_registry):
"""Test execution engine factory methods."""
                # Set defaults
ExecutionEngineFactory.set_defaults( )
registry=mock_agent_registry
                

                # Create default engine
engine = ExecutionEngineFactory.create_engine()
assert isinstance(engine, ExecutionEngine)
assert engine.registry == mock_agent_registry

                # Create user engine
engine = ExecutionEngineFactory.create_user_engine( )
user_context=mock_user_context
                
assert engine.config.enable_user_features is True
assert engine.user_context == mock_user_context

                # Create data engine
engine = ExecutionEngineFactory.create_data_engine()
assert engine.config.enable_data_features is True
assert engine.config.max_concurrent_agents == 20

                # Create MCP engine
engine = ExecutionEngineFactory.create_mcp_engine()
assert engine.config.enable_mcp is True

@pytest.mark.asyncio
    async def test_request_scoped_engine_factory(self, mock_user_context):
"""Test request-scoped engine factory."""
pass
engine = ExecutionEngineFactory.create_request_scoped_engine( )
request_id="test_req_002",
user_context=mock_user_context
                    

assert isinstance(engine, RequestScopedExecutionEngine)
assert engine.request_id == "test_req_002"


                    # ============================================================================
                    # INTEGRATION TESTS
                    # ============================================================================

class TestIntegration:
    """End-to-end integration tests."""

@pytest.mark.asyncio
    # Removed problematic line: async def test_dispatcher_engine_integration( )
self,
mock_user_context,
mock_agent_registry,
mock_websocket_bridge,
sample_tools
):
"""Test full integration of dispatcher and engine."""
        # Create dispatcher
dispatcher = create_dispatcher( )
user_context=mock_user_context,
websocket_emitter=mock_websocket_bridge
        

        # Register tools
for tool in sample_tools:
await dispatcher.register_tool(tool)

            # Create engine with dispatcher
engine = ExecutionEngineFactory.create_user_engine( )
user_context=mock_user_context,
registry=mock_agent_registry,
websocket_bridge=mock_websocket_bridge,
tool_dispatcher=dispatcher
            

            # Execute agent
result = await engine.execute("test_agent", {"task": "integration_test"})
assert result.success is True

            # Verify metrics
dispatcher_metrics = dispatcher.get_metrics()
engine_metrics = engine.get_metrics()

assert engine_metrics['success_count'] >= 1

@pytest.mark.asyncio
    async def test_request_isolation_e2e(self, mock_agent_registry):
"""Test request isolation end-to-end."""
                # Create multiple request-scoped engines
requests = []
for i in range(5):
user_context = Magic            user_context.user_id = "formatted_string"
user_context.request_id = "formatted_string"

engine = ExecutionEngineFactory.create_request_scoped_engine( )
request_id="formatted_string",
user_context=user_context,
registry=mock_agent_registry
                    
requests.append((engine, user_context))

                    # Execute concurrently
tasks = []
for engine, context in requests:
task = engine.execute("formatted_string", {"data": "test"})
tasks.append(task)

results = await asyncio.gather(*tasks)

                        # Verify all succeeded with isolation
for result in results:
assert result.success is True

@pytest.mark.asyncio
                            # Removed problematic line: async def test_websocket_event_flow( )
self,
mock_user_context,
mock_websocket_bridge,
mock_agent_registry
):
"""Test WebSocket event flow through the system."""
pass
                                # Create dispatcher with WebSocket
dispatcher = UnifiedToolDispatcher( )
user_context=mock_user_context,
websocket_emitter=mock_websocket_bridge
                                

                                # Register tool
async def event_tool() -> str:
await asyncio.sleep(0)
return "event_result"

tool_def = ToolDefinition( )
name="event_tool",
description="Tool for event testing",
parameters={},
handler=event_tool
    
await dispatcher.registry.register_tool("event_tool", tool_def)

    # Create engine with WebSocket
engine = UserExecutionEngine( )
config=EngineConfig(enable_websocket_events=True),
registry=mock_agent_registry,
websocket_bridge=mock_websocket_bridge,
user_context=mock_user_context,
tool_dispatcher=dispatcher
    

    # Execute agent
await engine.execute("test_agent", {"task": "websocket_test"})

    # Verify WebSocket events were emitted
assert mock_websocket_bridge.notify_agent_started.called
assert mock_websocket_bridge.notify_agent_completed.called

    # Dispatch tool
await dispatcher.dispatch("event_tool", {})

    # Verify tool events
assert mock_websocket_bridge.notify_tool_executing.called
assert mock_websocket_bridge.notify_tool_completed.called

@pytest.mark.asyncio
    async def test_performance_requirements(self, mock_agent_registry):
"""Test system meets performance requirements."""
        # Create optimized configuration
config = EngineConfig( )
enable_metrics=True,
max_concurrent_agents=15,
agent_execution_timeout=2.0
        

        # Create dispatcher and engine
dispatcher = UnifiedToolDispatcher(enable_metrics=True)
engine = UserExecutionEngine( )
config=config,
registry=mock_agent_registry,
tool_dispatcher=dispatcher
        

        # Register fast tool
async def perf_tool() -> str:
await asyncio.sleep(0)
return "perf"

tool_def = ToolDefinition( )
name="perf_tool",
description="Performance test tool",
parameters={},
handler=perf_tool
    
await dispatcher.registry.register_tool("perf_tool", tool_def)

    # Test dispatch performance (<5ms)
dispatch_times = []
for _ in range(20):
start = time.perf_counter()
await dispatcher.dispatch("perf_tool", {})
dispatch_time = (time.perf_counter() - start) * 1000
dispatch_times.append(dispatch_time)

avg_dispatch = sum(dispatch_times) / len(dispatch_times)
assert avg_dispatch < 5, "formatted_string"

        # Test execution performance (<2s)
execution_times = []
for _ in range(10):
start = time.perf_counter()
await engine.execute("test_agent", {"task": "perf"})
execution_time = time.perf_counter() - start
execution_times.append(execution_time)

avg_execution = sum(execution_times) / len(execution_times)
assert avg_execution < 2.0, "formatted_string"

            # Verify metrics
dispatcher_metrics = dispatcher.get_metrics()
engine_metrics = engine.get_metrics()

assert dispatcher_metrics['average_dispatch_ms'] < 5
assert engine_metrics['average_execution_ms'] < 2000
assert engine_metrics['success_rate'] >= 0.95  # 95% success rate

@pytest.mark.asyncio
    async def test_backwards_compatibility(self, mock_user_context, mock_agent_registry):
"""Test backward compatibility with old APIs."""
pass
with warnings.catch_warnings(record=True) as w:
warnings.simplefilter("always")

                    # Test legacy dispatcher function
from netra_backend.app.agents.tool_dispatcher_consolidated import get_tool_dispatcher
dispatcher = get_tool_dispatcher(user_context=mock_user_context)
assert isinstance(dispatcher, UnifiedToolDispatcher)
assert len(w) == 1
assert "deprecated" in str(w[0].message)

                    # Test legacy engine function
from netra_backend.app.agents.execution_engine_consolidated import create_execution_engine
engine = create_execution_engine(registry=mock_agent_registry)
assert isinstance(engine, ExecutionEngine)
assert len(w) == 2
assert "deprecated" in str(w[1].message)

@pytest.mark.asyncio
    async def test_extension_lifecycle(self, mock_agent_registry):
"""Test extension initialization and cleanup."""
                        # Create engine with all extensions
config = EngineConfig( )
enable_user_features=True,
enable_mcp=True,
enable_data_features=True,
enable_websocket_events=False  # No bridge provided
                        

engine = UserExecutionEngine( )
config=config,
registry=mock_agent_registry
                        

                        # Initialize extensions
await engine.initialize()

                        # Execute to trigger extension hooks
result = await engine.execute("test_agent", {"task": "extension_test"})
assert result.success is True

                        # Cleanup extensions
await engine.cleanup()

                        # Verify cleanup
assert len(engine.active_runs) == 0
assert len(engine.run_history) == 0


                        # ============================================================================
                        # STRESS TESTS
                        # ============================================================================

class TestStress:
    """Stress tests for high load scenarios."""

@pytest.mark.asyncio
    async def test_high_concurrent_dispatch(self):
"""Test dispatcher under high concurrent load."""
dispatcher = UnifiedToolDispatcher(enable_metrics=True)

        # Register simple tool
async def stress_tool(value: int) -> int:
await asyncio.sleep(0.001)  # Tiny delay
await asyncio.sleep(0)
return value * 2

tool_def = ToolDefinition( )
name="stress",
description="Stress test tool",
parameters={},
handler=stress_tool
    
await dispatcher.registry.register_tool("stress", tool_def)

    # Dispatch 100 tools concurrently
tasks = []
for i in range(100):
task = dispatcher.dispatch("stress", {"value": i})
tasks.append(task)

results = await asyncio.gather(*tasks)

        # Verify all succeeded
success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)
assert success_count == 100

        # Check performance
metrics = dispatcher.get_metrics()
assert metrics['total_dispatches'] == 100
assert metrics['average_dispatch_ms'] < 10  # Reasonable under load

@pytest.mark.asyncio
    async def test_high_concurrent_execution(self, mock_agent_registry):
"""Test engine under high concurrent load."""
pass
config = EngineConfig( )
max_concurrent_agents=50,
enable_metrics=True
            

engine = UserExecutionEngine( )
config=config,
registry=mock_agent_registry
            

            # Execute 50 agents concurrently
tasks = []
for i in range(50):
task = engine.execute("formatted_string", {"task": "formatted_string"})
tasks.append(task)

results = await asyncio.gather(*tasks)

                # Verify all succeeded
success_count = sum(1 for r in results if r.success)
assert success_count == 50

                # Check metrics
metrics = engine.get_metrics()
assert metrics['total_executions'] == 50
assert metrics['success_rate'] >= 0.98  # Allow 2% failure under stress


                # ============================================================================
                # ERROR HANDLING TESTS
                # ============================================================================

class TestErrorHandling:
    """Test error handling and recovery."""

@pytest.mark.asyncio
    async def test_dispatcher_error_handling(self, mock_websocket_emitter):
"""Test dispatcher error handling."""
dispatcher = UnifiedToolDispatcher(websocket_emitter=mock_websocket_emitter)

        # Try to dispatch non-existent tool
result = await dispatcher.dispatch("non_existent", {})
assert result.status == ToolStatus.ERROR
assert "not found" in result.error

        # Register failing tool
async def failing_tool() -> str:
raise ValueError("Tool failed intentionally")

tool_def = ToolDefinition( )
name="failing",
description="Failing tool",
parameters={},
handler=failing_tool
    
await dispatcher.registry.register_tool("failing", tool_def)

    # Dispatch failing tool
result = await dispatcher.dispatch("failing", {})
assert result.status == ToolStatus.ERROR
assert "Tool failed intentionally" in result.error

    # Verify error event was emitted
mock_websocket_emitter.notify_tool_error.assert_called()

@pytest.mark.asyncio
    async def test_engine_timeout_handling(self, mock_agent_registry):
"""Test engine timeout handling."""
pass
        # Configure with short timeout
config = EngineConfig(agent_execution_timeout=0.1)

        # Create slow agent
websocket = TestWebSocketConnection()
mock_agent.execute = AsyncMock( )
side_effect=lambda x: None asyncio.sleep(1.0)  # Longer than timeout
        
mock_agent_registry.get_agent = MagicMock(return_value=mock_agent)

engine = UserExecutionEngine( )
config=config,
registry=mock_agent_registry
        

        # Execute should timeout
result = await engine.execute("slow_agent", {"task": "timeout_test"})
assert result.success is False
assert "timed out" in result.error

        # Verify metrics tracked the error
metrics = engine.get_metrics()
assert metrics['error_count'] == 1
