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

    # REMOVED_SYNTAX_ERROR: '''Integration tests for consolidated Tool Dispatcher and Execution Engine.

    # REMOVED_SYNTAX_ERROR: This test suite validates:
        # REMOVED_SYNTAX_ERROR: - Tool dispatch with all strategies
        # REMOVED_SYNTAX_ERROR: - Execution engine with all extensions
        # REMOVED_SYNTAX_ERROR: - Request-scoped isolation
        # REMOVED_SYNTAX_ERROR: - WebSocket event delivery
        # REMOVED_SYNTAX_ERROR: - Performance requirements (<5ms dispatch, <2s execution)
        # REMOVED_SYNTAX_ERROR: - Concurrent user support (10+ users)
        # REMOVED_SYNTAX_ERROR: - Backward compatibility
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import asyncio
        # REMOVED_SYNTAX_ERROR: import time
        # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, List, Optional
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.agent_registry import AgentRegistry
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.user_execution_engine import UserExecutionEngine
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

        # REMOVED_SYNTAX_ERROR: import pytest
        # REMOVED_SYNTAX_ERROR: from langchain_core.tools import BaseTool

        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher_consolidated import ( )
        # REMOVED_SYNTAX_ERROR: UnifiedToolDispatcher,
        # REMOVED_SYNTAX_ERROR: UnifiedToolRegistry,
        # REMOVED_SYNTAX_ERROR: ToolDefinition,
        # REMOVED_SYNTAX_ERROR: ExecutionContext,
        # REMOVED_SYNTAX_ERROR: DefaultDispatchStrategy,
        # REMOVED_SYNTAX_ERROR: AdminDispatchStrategy,
        # REMOVED_SYNTAX_ERROR: DataDispatchStrategy,
        # REMOVED_SYNTAX_ERROR: create_dispatcher,
        # REMOVED_SYNTAX_ERROR: create_request_scoped_dispatcher,
        # REMOVED_SYNTAX_ERROR: RequestScopedDispatcher
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.execution_engine_consolidated import ( )
        # REMOVED_SYNTAX_ERROR: ExecutionEngine,
        # REMOVED_SYNTAX_ERROR: ExecutionEngineFactory,
        # REMOVED_SYNTAX_ERROR: RequestScopedExecutionEngine,
        # REMOVED_SYNTAX_ERROR: EngineConfig,
        # REMOVED_SYNTAX_ERROR: AgentExecutionContext,
        # REMOVED_SYNTAX_ERROR: AgentExecutionResult,
        # REMOVED_SYNTAX_ERROR: UserExecutionExtension,
        # REMOVED_SYNTAX_ERROR: MCPExecutionExtension,
        # REMOVED_SYNTAX_ERROR: DataExecutionExtension,
        # REMOVED_SYNTAX_ERROR: WebSocketExtension,
        # REMOVED_SYNTAX_ERROR: execute_agent,
        # REMOVED_SYNTAX_ERROR: execution_engine_context
        
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.schemas.tool import ToolResult, ToolStatus
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


        # ============================================================================
        # FIXTURES
        # ============================================================================

        # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_user_context():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock user context."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: context = Magic    context.user_id = "test_user_123"
    # REMOVED_SYNTAX_ERROR: context.request_id = "req_456"
    # REMOVED_SYNTAX_ERROR: return context


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_emitter():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket emitter."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: return emitter


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket_bridge():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock WebSocket bridge."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: return bridge


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_agent_registry():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock agent registry."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: registry = Magic    websocket = TestWebSocketConnection()
    # REMOVED_SYNTAX_ERROR: mock_agent.execute = AsyncMock(return_value="agent_result")
    # REMOVED_SYNTAX_ERROR: registry.get_agent = MagicMock(return_value=mock_agent)
    # REMOVED_SYNTAX_ERROR: return registry


    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def sample_tools():
    # REMOVED_SYNTAX_ERROR: """Create sample tools for testing."""
# REMOVED_SYNTAX_ERROR: class TestTool(BaseTool):
    # REMOVED_SYNTAX_ERROR: name: str = "test_tool"
    # REMOVED_SYNTAX_ERROR: description: str = "A test tool"

# REMOVED_SYNTAX_ERROR: def _run(self, query: str) -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

# REMOVED_SYNTAX_ERROR: async def _arun(self, query: str) -> str:
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

# REMOVED_SYNTAX_ERROR: class AdminTool(BaseTool):
    # REMOVED_SYNTAX_ERROR: name: str = "corpus_update"
    # REMOVED_SYNTAX_ERROR: description: str = "Admin tool for corpus update"

# REMOVED_SYNTAX_ERROR: async def _arun(self, data: str) -> str:
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

# REMOVED_SYNTAX_ERROR: class DataTool(BaseTool):
    # REMOVED_SYNTAX_ERROR: name: str = "data_fetch"
    # REMOVED_SYNTAX_ERROR: description: str = "Data fetching tool"

# REMOVED_SYNTAX_ERROR: async def _arun(self, query: str) -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.01)  # Simulate data fetch
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # REMOVED_SYNTAX_ERROR: return [TestTool(), AdminTool(), DataTool()]


    # ============================================================================
    # TOOL DISPATCHER TESTS
    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestUnifiedToolDispatcher:
    # REMOVED_SYNTAX_ERROR: """Test UnifiedToolDispatcher functionality."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_dispatcher_initialization(self, mock_user_context, mock_websocket_emitter):
        # REMOVED_SYNTAX_ERROR: """Test dispatcher initialization with different configurations."""
        # Default initialization
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher()
        # REMOVED_SYNTAX_ERROR: assert dispatcher.strategy is not None
        # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher.strategy, DefaultDispatchStrategy)

        # With user context
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher( )
        # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_emitter
        
        # REMOVED_SYNTAX_ERROR: assert dispatcher.user_context == mock_user_context
        # REMOVED_SYNTAX_ERROR: assert dispatcher.websocket_emitter == mock_websocket_emitter
        # REMOVED_SYNTAX_ERROR: assert dispatcher.execution_context.user_id == "test_user_123"

        # With admin strategy
        # REMOVED_SYNTAX_ERROR: admin_strategy = AdminDispatchStrategy()
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(strategy=admin_strategy)
        # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher.strategy, AdminDispatchStrategy)

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_tool_registration_and_discovery(self, sample_tools):
            # REMOVED_SYNTAX_ERROR: """Test tool registration and discovery."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher()

            # Register tools
            # REMOVED_SYNTAX_ERROR: for tool in sample_tools:
                # REMOVED_SYNTAX_ERROR: await dispatcher.register_tool(tool)

                # Discover all tools
                # REMOVED_SYNTAX_ERROR: tools = dispatcher.discover_tools()
                # REMOVED_SYNTAX_ERROR: assert len(tools) == 3

                # Discover by category (would need category support in sample_tools)
                # tools = dispatcher.discover_tools(category="data")

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_tool_dispatch_success(self, mock_websocket_emitter):
                    # REMOVED_SYNTAX_ERROR: """Test successful tool dispatch."""
                    # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(websocket_emitter=mock_websocket_emitter)

                    # Register a test tool
                    # Removed problematic line: async def test_handler(input: str) -> str:
                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
                        # REMOVED_SYNTAX_ERROR: return "formatted_string"

                        # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
                        # REMOVED_SYNTAX_ERROR: name="test",
                        # REMOVED_SYNTAX_ERROR: description="Test tool",
                        # REMOVED_SYNTAX_ERROR: parameters={},
                        # REMOVED_SYNTAX_ERROR: handler=test_handler
                        
                        # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("test", tool_def)

                        # Dispatch tool
                        # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("test", {"input": "hello"})

                        # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.SUCCESS
                        # REMOVED_SYNTAX_ERROR: assert result.result == "Result: hello"
                        # REMOVED_SYNTAX_ERROR: assert "dispatch_time_ms" in result.metadata

                        # Verify WebSocket events were emitted
                        # REMOVED_SYNTAX_ERROR: mock_websocket_emitter.notify_tool_executing.assert_called_once()
                        # REMOVED_SYNTAX_ERROR: mock_websocket_emitter.notify_tool_completed.assert_called_once()

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_tool_dispatch_with_admin_strategy(self):
                            # REMOVED_SYNTAX_ERROR: """Test tool dispatch with admin strategy."""
                            # REMOVED_SYNTAX_ERROR: pass
                            # REMOVED_SYNTAX_ERROR: admin_strategy = AdminDispatchStrategy()
                            # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(strategy=admin_strategy)

                            # Register admin tool
# REMOVED_SYNTAX_ERROR: async def admin_handler(**kwargs) -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "formatted_string"

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="corpus_update",
    # REMOVED_SYNTAX_ERROR: description="Admin tool",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=admin_handler,
    # REMOVED_SYNTAX_ERROR: admin_required=True
    
    # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("corpus_update", tool_def)

    # Try dispatch without admin privileges
    # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("corpus_update", {})
    # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.ERROR
    # REMOVED_SYNTAX_ERROR: assert "requires admin privileges" in result.error

    # Dispatch with admin context
    # REMOVED_SYNTAX_ERROR: dispatcher.execution_context.metadata['is_admin'] = True
    # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("corpus_update", {})
    # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.SUCCESS
    # REMOVED_SYNTAX_ERROR: assert "Admin action: True" in result.result

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_dispatch_performance(self):
        # REMOVED_SYNTAX_ERROR: """Test dispatch performance meets <5ms requirement."""
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(enable_metrics=True)

        # Register fast tool
# REMOVED_SYNTAX_ERROR: async def fast_handler() -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "fast"

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="fast",
    # REMOVED_SYNTAX_ERROR: description="Fast tool",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=fast_handler
    
    # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("fast", tool_def)

    # Run multiple dispatches
    # REMOVED_SYNTAX_ERROR: dispatch_times = []
    # REMOVED_SYNTAX_ERROR: for _ in range(10):
        # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
        # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("fast", {})
        # REMOVED_SYNTAX_ERROR: dispatch_time_ms = (time.perf_counter() - start) * 1000
        # REMOVED_SYNTAX_ERROR: dispatch_times.append(dispatch_time_ms)
        # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.SUCCESS

        # Check metrics
        # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
        # REMOVED_SYNTAX_ERROR: assert metrics['average_dispatch_ms'] < 5
        # REMOVED_SYNTAX_ERROR: assert metrics['total_dispatches'] == 10

        # Most dispatches should be under 5ms
        # REMOVED_SYNTAX_ERROR: fast_dispatches = [item for item in []]
        # REMOVED_SYNTAX_ERROR: assert len(fast_dispatches) >= 8  # At least 80% under 5ms

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_request_scoped_dispatcher(self, mock_user_context):
            # REMOVED_SYNTAX_ERROR: """Test request-scoped dispatcher isolation."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: base_dispatcher = UnifiedToolDispatcher(user_context=mock_user_context)

            # Create request-scoped wrapper
            # REMOVED_SYNTAX_ERROR: request_dispatcher = base_dispatcher.with_request_scope("req_789")
            # REMOVED_SYNTAX_ERROR: assert isinstance(request_dispatcher, RequestScopedDispatcher)
            # REMOVED_SYNTAX_ERROR: assert request_dispatcher.request_id == "req_789"

            # Register tool
# REMOVED_SYNTAX_ERROR: async def scoped_handler() -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "scoped result"

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="scoped",
    # REMOVED_SYNTAX_ERROR: description="Scoped tool",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=scoped_handler
    
    # REMOVED_SYNTAX_ERROR: await base_dispatcher.registry.register_tool("scoped", tool_def)

    # Dispatch through scoped wrapper
    # REMOVED_SYNTAX_ERROR: result = await request_dispatcher.dispatch("scoped", {})
    # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.SUCCESS

    # Close and verify closed state
    # REMOVED_SYNTAX_ERROR: request_dispatcher.close()
    # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="has been closed"):
        # REMOVED_SYNTAX_ERROR: await request_dispatcher.dispatch("scoped", {})


        # ============================================================================
        # EXECUTION ENGINE TESTS
        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestExecutionEngine:
    # REMOVED_SYNTAX_ERROR: """Test ExecutionEngine functionality."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_engine_initialization(self, mock_agent_registry, mock_websocket_bridge):
        # REMOVED_SYNTAX_ERROR: """Test engine initialization with different configurations."""
        # Default configuration
        # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine()
        # REMOVED_SYNTAX_ERROR: assert engine.config is not None
        # REMOVED_SYNTAX_ERROR: assert len(engine._extensions) == 0  # No extensions by default

        # With user features
        # REMOVED_SYNTAX_ERROR: config = EngineConfig(enable_user_features=True)
        # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine(config=config)
        # REMOVED_SYNTAX_ERROR: assert 'user' in engine._extensions
        # REMOVED_SYNTAX_ERROR: assert isinstance(engine._extensions['user'], UserExecutionExtension)

        # With all features
        # REMOVED_SYNTAX_ERROR: config = EngineConfig( )
        # REMOVED_SYNTAX_ERROR: enable_user_features=True,
        # REMOVED_SYNTAX_ERROR: enable_mcp=True,
        # REMOVED_SYNTAX_ERROR: enable_data_features=True,
        # REMOVED_SYNTAX_ERROR: enable_websocket_events=True
        
        # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
        # REMOVED_SYNTAX_ERROR: config=config,
        # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
        # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
        
        # REMOVED_SYNTAX_ERROR: assert len(engine._extensions) == 4
        # REMOVED_SYNTAX_ERROR: assert 'websocket' in engine._extensions

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_agent_execution_success(self, mock_agent_registry, mock_user_context):
            # REMOVED_SYNTAX_ERROR: """Test successful agent execution."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
            # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
            # REMOVED_SYNTAX_ERROR: user_context=mock_user_context
            

            # Execute agent
            # REMOVED_SYNTAX_ERROR: result = await engine.execute("test_agent", {"task": "test"})

            # REMOVED_SYNTAX_ERROR: assert result.success is True
            # REMOVED_SYNTAX_ERROR: assert result.result == "agent_result"
            # REMOVED_SYNTAX_ERROR: assert result.execution_time_ms is not None

            # Verify agent was called
            # REMOVED_SYNTAX_ERROR: mock_agent_registry.get_agent.assert_called_with("test_agent")

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_execution_with_extensions(self, mock_agent_registry, mock_websocket_bridge):
                # REMOVED_SYNTAX_ERROR: """Test execution with all extensions."""
                # REMOVED_SYNTAX_ERROR: config = EngineConfig( )
                # REMOVED_SYNTAX_ERROR: enable_user_features=True,
                # REMOVED_SYNTAX_ERROR: enable_websocket_events=True
                
                # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
                # REMOVED_SYNTAX_ERROR: config=config,
                # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
                # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge
                

                # Initialize extensions
                # REMOVED_SYNTAX_ERROR: await engine.initialize()

                # Execute agent
                # REMOVED_SYNTAX_ERROR: result = await engine.execute("test_agent", {"task": "test"})

                # REMOVED_SYNTAX_ERROR: assert result.success is True

                # Verify WebSocket events
                # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_started.assert_called_once()
                # REMOVED_SYNTAX_ERROR: mock_websocket_bridge.notify_agent_completed.assert_called_once()

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_execution_performance(self, mock_agent_registry):
                    # REMOVED_SYNTAX_ERROR: """Test execution meets <2s requirement."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # Configure fast agent
                    # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
                    # REMOVED_SYNTAX_ERROR: mock_agent.execute = AsyncMock( )
                    # REMOVED_SYNTAX_ERROR: side_effect=lambda x: None asyncio.sleep(0.1) or "fast_result"
                    
                    # REMOVED_SYNTAX_ERROR: mock_agent_registry.get_agent = MagicMock(return_value=mock_agent)

                    # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
                    # REMOVED_SYNTAX_ERROR: config=EngineConfig(agent_execution_timeout=2.0),
                    # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry
                    

                    # Execute multiple times
                    # REMOVED_SYNTAX_ERROR: execution_times = []
                    # REMOVED_SYNTAX_ERROR: for _ in range(5):
                        # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
                        # REMOVED_SYNTAX_ERROR: result = await engine.execute("fast_agent", {"task": "speed_test"})
                        # REMOVED_SYNTAX_ERROR: execution_time = time.perf_counter() - start
                        # REMOVED_SYNTAX_ERROR: execution_times.append(execution_time)

                        # REMOVED_SYNTAX_ERROR: assert result.success is True
                        # REMOVED_SYNTAX_ERROR: assert execution_time < 2.0  # Under 2 seconds

                        # Check metrics
                        # REMOVED_SYNTAX_ERROR: metrics = engine.get_metrics()
                        # REMOVED_SYNTAX_ERROR: assert metrics['average_execution_ms'] < 2000
                        # REMOVED_SYNTAX_ERROR: assert metrics['success_rate'] == 1.0

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_concurrent_user_execution(self, mock_agent_registry):
                            # REMOVED_SYNTAX_ERROR: """Test concurrent execution for 10+ users."""
                            # Create multiple engines for different users
                            # REMOVED_SYNTAX_ERROR: engines = []
                            # REMOVED_SYNTAX_ERROR: for i in range(12):  # Test with 12 concurrent users
                            # REMOVED_SYNTAX_ERROR: user_context = Magic            user_context.user_id = "formatted_string"
                            # REMOVED_SYNTAX_ERROR: user_context.request_id = "formatted_string"

                            # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
                            # REMOVED_SYNTAX_ERROR: config=EngineConfig( )
                            # REMOVED_SYNTAX_ERROR: enable_user_features=True,
                            # REMOVED_SYNTAX_ERROR: max_concurrent_agents=10
                            # REMOVED_SYNTAX_ERROR: ),
                            # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
                            # REMOVED_SYNTAX_ERROR: user_context=user_context
                            
                            # REMOVED_SYNTAX_ERROR: engines.append(engine)

                            # Execute agents concurrently
                            # REMOVED_SYNTAX_ERROR: tasks = []
                            # REMOVED_SYNTAX_ERROR: for i, engine in enumerate(engines):
                                # REMOVED_SYNTAX_ERROR: task = engine.execute("formatted_string", {"task": "formatted_string"})
                                # REMOVED_SYNTAX_ERROR: tasks.append(task)

                                # Wait for all to complete
                                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

                                # Verify all succeeded
                                # REMOVED_SYNTAX_ERROR: for result in results:
                                    # REMOVED_SYNTAX_ERROR: assert result.success is True

                                    # Check that user isolation was maintained
                                    # REMOVED_SYNTAX_ERROR: for i, engine in enumerate(engines):
                                        # REMOVED_SYNTAX_ERROR: metrics = engine.get_metrics()
                                        # REMOVED_SYNTAX_ERROR: assert metrics['success_count'] == 1


                                        # ============================================================================
                                        # FACTORY TESTS
                                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestFactories:
    # REMOVED_SYNTAX_ERROR: """Test factory functions for creating dispatchers and engines."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_dispatcher_factory(self, mock_user_context):
        # REMOVED_SYNTAX_ERROR: """Test dispatcher factory functions."""
        # Create default dispatcher
        # REMOVED_SYNTAX_ERROR: dispatcher = create_dispatcher()
        # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher, UnifiedToolDispatcher)
        # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher.strategy, DefaultDispatchStrategy)

        # Create admin dispatcher
        # REMOVED_SYNTAX_ERROR: dispatcher = create_dispatcher(admin_mode=True)
        # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher.strategy, AdminDispatchStrategy)

        # Create data dispatcher
        # REMOVED_SYNTAX_ERROR: dispatcher = create_dispatcher(data_mode=True)
        # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher.strategy, DataDispatchStrategy)

        # Create with user context
        # REMOVED_SYNTAX_ERROR: dispatcher = create_dispatcher(user_context=mock_user_context)
        # REMOVED_SYNTAX_ERROR: assert dispatcher.user_context == mock_user_context

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_request_scoped_dispatcher_factory(self, mock_user_context):
            # REMOVED_SYNTAX_ERROR: """Test request-scoped dispatcher factory."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: dispatcher = create_request_scoped_dispatcher( )
            # REMOVED_SYNTAX_ERROR: request_id="test_req_001",
            # REMOVED_SYNTAX_ERROR: user_context=mock_user_context
            

            # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher, RequestScopedDispatcher)
            # REMOVED_SYNTAX_ERROR: assert dispatcher.request_id == "test_req_001"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_execution_engine_factory(self, mock_user_context, mock_agent_registry):
                # REMOVED_SYNTAX_ERROR: """Test execution engine factory methods."""
                # Set defaults
                # REMOVED_SYNTAX_ERROR: ExecutionEngineFactory.set_defaults( )
                # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry
                

                # Create default engine
                # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_engine()
                # REMOVED_SYNTAX_ERROR: assert isinstance(engine, ExecutionEngine)
                # REMOVED_SYNTAX_ERROR: assert engine.registry == mock_agent_registry

                # Create user engine
                # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_user_engine( )
                # REMOVED_SYNTAX_ERROR: user_context=mock_user_context
                
                # REMOVED_SYNTAX_ERROR: assert engine.config.enable_user_features is True
                # REMOVED_SYNTAX_ERROR: assert engine.user_context == mock_user_context

                # Create data engine
                # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_data_engine()
                # REMOVED_SYNTAX_ERROR: assert engine.config.enable_data_features is True
                # REMOVED_SYNTAX_ERROR: assert engine.config.max_concurrent_agents == 20

                # Create MCP engine
                # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_mcp_engine()
                # REMOVED_SYNTAX_ERROR: assert engine.config.enable_mcp is True

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_request_scoped_engine_factory(self, mock_user_context):
                    # REMOVED_SYNTAX_ERROR: """Test request-scoped engine factory."""
                    # REMOVED_SYNTAX_ERROR: pass
                    # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_request_scoped_engine( )
                    # REMOVED_SYNTAX_ERROR: request_id="test_req_002",
                    # REMOVED_SYNTAX_ERROR: user_context=mock_user_context
                    

                    # REMOVED_SYNTAX_ERROR: assert isinstance(engine, RequestScopedExecutionEngine)
                    # REMOVED_SYNTAX_ERROR: assert engine.request_id == "test_req_002"


                    # ============================================================================
                    # INTEGRATION TESTS
                    # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestIntegration:
    # REMOVED_SYNTAX_ERROR: """End-to-end integration tests."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_dispatcher_engine_integration( )
    # REMOVED_SYNTAX_ERROR: self,
    # REMOVED_SYNTAX_ERROR: mock_user_context,
    # REMOVED_SYNTAX_ERROR: mock_agent_registry,
    # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: sample_tools
    # REMOVED_SYNTAX_ERROR: ):
        # REMOVED_SYNTAX_ERROR: """Test full integration of dispatcher and engine."""
        # Create dispatcher
        # REMOVED_SYNTAX_ERROR: dispatcher = create_dispatcher( )
        # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
        # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_bridge
        

        # Register tools
        # REMOVED_SYNTAX_ERROR: for tool in sample_tools:
            # REMOVED_SYNTAX_ERROR: await dispatcher.register_tool(tool)

            # Create engine with dispatcher
            # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_user_engine( )
            # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
            # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
            # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
            # REMOVED_SYNTAX_ERROR: tool_dispatcher=dispatcher
            

            # Execute agent
            # REMOVED_SYNTAX_ERROR: result = await engine.execute("test_agent", {"task": "integration_test"})
            # REMOVED_SYNTAX_ERROR: assert result.success is True

            # Verify metrics
            # REMOVED_SYNTAX_ERROR: dispatcher_metrics = dispatcher.get_metrics()
            # REMOVED_SYNTAX_ERROR: engine_metrics = engine.get_metrics()

            # REMOVED_SYNTAX_ERROR: assert engine_metrics['success_count'] >= 1

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_request_isolation_e2e(self, mock_agent_registry):
                # REMOVED_SYNTAX_ERROR: """Test request isolation end-to-end."""
                # Create multiple request-scoped engines
                # REMOVED_SYNTAX_ERROR: requests = []
                # REMOVED_SYNTAX_ERROR: for i in range(5):
                    # REMOVED_SYNTAX_ERROR: user_context = Magic            user_context.user_id = "formatted_string"
                    # REMOVED_SYNTAX_ERROR: user_context.request_id = "formatted_string"

                    # REMOVED_SYNTAX_ERROR: engine = ExecutionEngineFactory.create_request_scoped_engine( )
                    # REMOVED_SYNTAX_ERROR: request_id="formatted_string",
                    # REMOVED_SYNTAX_ERROR: user_context=user_context,
                    # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry
                    
                    # REMOVED_SYNTAX_ERROR: requests.append((engine, user_context))

                    # Execute concurrently
                    # REMOVED_SYNTAX_ERROR: tasks = []
                    # REMOVED_SYNTAX_ERROR: for engine, context in requests:
                        # REMOVED_SYNTAX_ERROR: task = engine.execute("formatted_string", {"data": "test"})
                        # REMOVED_SYNTAX_ERROR: tasks.append(task)

                        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

                        # Verify all succeeded with isolation
                        # REMOVED_SYNTAX_ERROR: for result in results:
                            # REMOVED_SYNTAX_ERROR: assert result.success is True

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_websocket_event_flow( )
                            # REMOVED_SYNTAX_ERROR: self,
                            # REMOVED_SYNTAX_ERROR: mock_user_context,
                            # REMOVED_SYNTAX_ERROR: mock_websocket_bridge,
                            # REMOVED_SYNTAX_ERROR: mock_agent_registry
                            # REMOVED_SYNTAX_ERROR: ):
                                # REMOVED_SYNTAX_ERROR: """Test WebSocket event flow through the system."""
                                # REMOVED_SYNTAX_ERROR: pass
                                # Create dispatcher with WebSocket
                                # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher( )
                                # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
                                # REMOVED_SYNTAX_ERROR: websocket_emitter=mock_websocket_bridge
                                

                                # Register tool
# REMOVED_SYNTAX_ERROR: async def event_tool() -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "event_result"

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="event_tool",
    # REMOVED_SYNTAX_ERROR: description="Tool for event testing",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=event_tool
    
    # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("event_tool", tool_def)

    # Create engine with WebSocket
    # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
    # REMOVED_SYNTAX_ERROR: config=EngineConfig(enable_websocket_events=True),
    # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
    # REMOVED_SYNTAX_ERROR: websocket_bridge=mock_websocket_bridge,
    # REMOVED_SYNTAX_ERROR: user_context=mock_user_context,
    # REMOVED_SYNTAX_ERROR: tool_dispatcher=dispatcher
    

    # Execute agent
    # REMOVED_SYNTAX_ERROR: await engine.execute("test_agent", {"task": "websocket_test"})

    # Verify WebSocket events were emitted
    # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_agent_started.called
    # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_agent_completed.called

    # Dispatch tool
    # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("event_tool", {})

    # Verify tool events
    # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_tool_executing.called
    # REMOVED_SYNTAX_ERROR: assert mock_websocket_bridge.notify_tool_completed.called

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_performance_requirements(self, mock_agent_registry):
        # REMOVED_SYNTAX_ERROR: """Test system meets performance requirements."""
        # Create optimized configuration
        # REMOVED_SYNTAX_ERROR: config = EngineConfig( )
        # REMOVED_SYNTAX_ERROR: enable_metrics=True,
        # REMOVED_SYNTAX_ERROR: max_concurrent_agents=15,
        # REMOVED_SYNTAX_ERROR: agent_execution_timeout=2.0
        

        # Create dispatcher and engine
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(enable_metrics=True)
        # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
        # REMOVED_SYNTAX_ERROR: config=config,
        # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry,
        # REMOVED_SYNTAX_ERROR: tool_dispatcher=dispatcher
        

        # Register fast tool
# REMOVED_SYNTAX_ERROR: async def perf_tool() -> str:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "perf"

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="perf_tool",
    # REMOVED_SYNTAX_ERROR: description="Performance test tool",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=perf_tool
    
    # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("perf_tool", tool_def)

    # Test dispatch performance (<5ms)
    # REMOVED_SYNTAX_ERROR: dispatch_times = []
    # REMOVED_SYNTAX_ERROR: for _ in range(20):
        # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
        # REMOVED_SYNTAX_ERROR: await dispatcher.dispatch("perf_tool", {})
        # REMOVED_SYNTAX_ERROR: dispatch_time = (time.perf_counter() - start) * 1000
        # REMOVED_SYNTAX_ERROR: dispatch_times.append(dispatch_time)

        # REMOVED_SYNTAX_ERROR: avg_dispatch = sum(dispatch_times) / len(dispatch_times)
        # REMOVED_SYNTAX_ERROR: assert avg_dispatch < 5, "formatted_string"

        # Test execution performance (<2s)
        # REMOVED_SYNTAX_ERROR: execution_times = []
        # REMOVED_SYNTAX_ERROR: for _ in range(10):
            # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
            # REMOVED_SYNTAX_ERROR: await engine.execute("test_agent", {"task": "perf"})
            # REMOVED_SYNTAX_ERROR: execution_time = time.perf_counter() - start
            # REMOVED_SYNTAX_ERROR: execution_times.append(execution_time)

            # REMOVED_SYNTAX_ERROR: avg_execution = sum(execution_times) / len(execution_times)
            # REMOVED_SYNTAX_ERROR: assert avg_execution < 2.0, "formatted_string"

            # Verify metrics
            # REMOVED_SYNTAX_ERROR: dispatcher_metrics = dispatcher.get_metrics()
            # REMOVED_SYNTAX_ERROR: engine_metrics = engine.get_metrics()

            # REMOVED_SYNTAX_ERROR: assert dispatcher_metrics['average_dispatch_ms'] < 5
            # REMOVED_SYNTAX_ERROR: assert engine_metrics['average_execution_ms'] < 2000
            # REMOVED_SYNTAX_ERROR: assert engine_metrics['success_rate'] >= 0.95  # 95% success rate

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_backwards_compatibility(self, mock_user_context, mock_agent_registry):
                # REMOVED_SYNTAX_ERROR: """Test backward compatibility with old APIs."""
                # REMOVED_SYNTAX_ERROR: pass
                # REMOVED_SYNTAX_ERROR: with warnings.catch_warnings(record=True) as w:
                    # REMOVED_SYNTAX_ERROR: warnings.simplefilter("always")

                    # Test legacy dispatcher function
                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.tool_dispatcher_consolidated import get_tool_dispatcher
                    # REMOVED_SYNTAX_ERROR: dispatcher = get_tool_dispatcher(user_context=mock_user_context)
                    # REMOVED_SYNTAX_ERROR: assert isinstance(dispatcher, UnifiedToolDispatcher)
                    # REMOVED_SYNTAX_ERROR: assert len(w) == 1
                    # REMOVED_SYNTAX_ERROR: assert "deprecated" in str(w[0].message)

                    # Test legacy engine function
                    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.execution_engine_consolidated import create_execution_engine
                    # REMOVED_SYNTAX_ERROR: engine = create_execution_engine(registry=mock_agent_registry)
                    # REMOVED_SYNTAX_ERROR: assert isinstance(engine, ExecutionEngine)
                    # REMOVED_SYNTAX_ERROR: assert len(w) == 2
                    # REMOVED_SYNTAX_ERROR: assert "deprecated" in str(w[1].message)

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_extension_lifecycle(self, mock_agent_registry):
                        # REMOVED_SYNTAX_ERROR: """Test extension initialization and cleanup."""
                        # Create engine with all extensions
                        # REMOVED_SYNTAX_ERROR: config = EngineConfig( )
                        # REMOVED_SYNTAX_ERROR: enable_user_features=True,
                        # REMOVED_SYNTAX_ERROR: enable_mcp=True,
                        # REMOVED_SYNTAX_ERROR: enable_data_features=True,
                        # REMOVED_SYNTAX_ERROR: enable_websocket_events=False  # No bridge provided
                        

                        # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
                        # REMOVED_SYNTAX_ERROR: config=config,
                        # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry
                        

                        # Initialize extensions
                        # REMOVED_SYNTAX_ERROR: await engine.initialize()

                        # Execute to trigger extension hooks
                        # REMOVED_SYNTAX_ERROR: result = await engine.execute("test_agent", {"task": "extension_test"})
                        # REMOVED_SYNTAX_ERROR: assert result.success is True

                        # Cleanup extensions
                        # REMOVED_SYNTAX_ERROR: await engine.cleanup()

                        # Verify cleanup
                        # REMOVED_SYNTAX_ERROR: assert len(engine.active_runs) == 0
                        # REMOVED_SYNTAX_ERROR: assert len(engine.run_history) == 0


                        # ============================================================================
                        # STRESS TESTS
                        # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestStress:
    # REMOVED_SYNTAX_ERROR: """Stress tests for high load scenarios."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_high_concurrent_dispatch(self):
        # REMOVED_SYNTAX_ERROR: """Test dispatcher under high concurrent load."""
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(enable_metrics=True)

        # Register simple tool
# REMOVED_SYNTAX_ERROR: async def stress_tool(value: int) -> int:
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.001)  # Tiny delay
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return value * 2

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="stress",
    # REMOVED_SYNTAX_ERROR: description="Stress test tool",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=stress_tool
    
    # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("stress", tool_def)

    # Dispatch 100 tools concurrently
    # REMOVED_SYNTAX_ERROR: tasks = []
    # REMOVED_SYNTAX_ERROR: for i in range(100):
        # REMOVED_SYNTAX_ERROR: task = dispatcher.dispatch("stress", {"value": i})
        # REMOVED_SYNTAX_ERROR: tasks.append(task)

        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

        # Verify all succeeded
        # REMOVED_SYNTAX_ERROR: success_count = sum(1 for r in results if r.status == ToolStatus.SUCCESS)
        # REMOVED_SYNTAX_ERROR: assert success_count == 100

        # Check performance
        # REMOVED_SYNTAX_ERROR: metrics = dispatcher.get_metrics()
        # REMOVED_SYNTAX_ERROR: assert metrics['total_dispatches'] == 100
        # REMOVED_SYNTAX_ERROR: assert metrics['average_dispatch_ms'] < 10  # Reasonable under load

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_high_concurrent_execution(self, mock_agent_registry):
            # REMOVED_SYNTAX_ERROR: """Test engine under high concurrent load."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: config = EngineConfig( )
            # REMOVED_SYNTAX_ERROR: max_concurrent_agents=50,
            # REMOVED_SYNTAX_ERROR: enable_metrics=True
            

            # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
            # REMOVED_SYNTAX_ERROR: config=config,
            # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry
            

            # Execute 50 agents concurrently
            # REMOVED_SYNTAX_ERROR: tasks = []
            # REMOVED_SYNTAX_ERROR: for i in range(50):
                # REMOVED_SYNTAX_ERROR: task = engine.execute("formatted_string", {"task": "formatted_string"})
                # REMOVED_SYNTAX_ERROR: tasks.append(task)

                # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)

                # Verify all succeeded
                # REMOVED_SYNTAX_ERROR: success_count = sum(1 for r in results if r.success)
                # REMOVED_SYNTAX_ERROR: assert success_count == 50

                # Check metrics
                # REMOVED_SYNTAX_ERROR: metrics = engine.get_metrics()
                # REMOVED_SYNTAX_ERROR: assert metrics['total_executions'] == 50
                # REMOVED_SYNTAX_ERROR: assert metrics['success_rate'] >= 0.98  # Allow 2% failure under stress


                # ============================================================================
                # ERROR HANDLING TESTS
                # ============================================================================

# REMOVED_SYNTAX_ERROR: class TestErrorHandling:
    # REMOVED_SYNTAX_ERROR: """Test error handling and recovery."""

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_dispatcher_error_handling(self, mock_websocket_emitter):
        # REMOVED_SYNTAX_ERROR: """Test dispatcher error handling."""
        # REMOVED_SYNTAX_ERROR: dispatcher = UnifiedToolDispatcher(websocket_emitter=mock_websocket_emitter)

        # Try to dispatch non-existent tool
        # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("non_existent", {})
        # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.ERROR
        # REMOVED_SYNTAX_ERROR: assert "not found" in result.error

        # Register failing tool
# REMOVED_SYNTAX_ERROR: async def failing_tool() -> str:
    # REMOVED_SYNTAX_ERROR: raise ValueError("Tool failed intentionally")

    # REMOVED_SYNTAX_ERROR: tool_def = ToolDefinition( )
    # REMOVED_SYNTAX_ERROR: name="failing",
    # REMOVED_SYNTAX_ERROR: description="Failing tool",
    # REMOVED_SYNTAX_ERROR: parameters={},
    # REMOVED_SYNTAX_ERROR: handler=failing_tool
    
    # REMOVED_SYNTAX_ERROR: await dispatcher.registry.register_tool("failing", tool_def)

    # Dispatch failing tool
    # REMOVED_SYNTAX_ERROR: result = await dispatcher.dispatch("failing", {})
    # REMOVED_SYNTAX_ERROR: assert result.status == ToolStatus.ERROR
    # REMOVED_SYNTAX_ERROR: assert "Tool failed intentionally" in result.error

    # Verify error event was emitted
    # REMOVED_SYNTAX_ERROR: mock_websocket_emitter.notify_tool_error.assert_called()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_engine_timeout_handling(self, mock_agent_registry):
        # REMOVED_SYNTAX_ERROR: """Test engine timeout handling."""
        # REMOVED_SYNTAX_ERROR: pass
        # Configure with short timeout
        # REMOVED_SYNTAX_ERROR: config = EngineConfig(agent_execution_timeout=0.1)

        # Create slow agent
        # REMOVED_SYNTAX_ERROR: websocket = TestWebSocketConnection()
        # REMOVED_SYNTAX_ERROR: mock_agent.execute = AsyncMock( )
        # REMOVED_SYNTAX_ERROR: side_effect=lambda x: None asyncio.sleep(1.0)  # Longer than timeout
        
        # REMOVED_SYNTAX_ERROR: mock_agent_registry.get_agent = MagicMock(return_value=mock_agent)

        # REMOVED_SYNTAX_ERROR: engine = ExecutionEngine( )
        # REMOVED_SYNTAX_ERROR: config=config,
        # REMOVED_SYNTAX_ERROR: registry=mock_agent_registry
        

        # Execute should timeout
        # REMOVED_SYNTAX_ERROR: result = await engine.execute("slow_agent", {"task": "timeout_test"})
        # REMOVED_SYNTAX_ERROR: assert result.success is False
        # REMOVED_SYNTAX_ERROR: assert "timed out" in result.error

        # Verify metrics tracked the error
        # REMOVED_SYNTAX_ERROR: metrics = engine.get_metrics()
        # REMOVED_SYNTAX_ERROR: assert metrics['error_count'] == 1