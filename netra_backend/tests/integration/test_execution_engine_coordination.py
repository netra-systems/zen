"""
Focused Integration Test: ExecutionEngine SSOT Coordination Patterns

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure ExecutionEngine provides reliable agent coordination
- Value Impact: Validates core agent execution patterns, prevents execution failures
- Strategic Impact: Critical for multi-user business model and agent reliability

Tests ExecutionEngine SSOT coordination patterns:
- Engine initialization and configuration validation
- Engine extension pattern coordination
- Agent execution coordination with UserExecutionContext
- WebSocket event coordination patterns
- Engine factory method patterns
- Request-scoped execution isolation patterns

This is a NON-DOCKER integration test that focuses on core ExecutionEngine SSOT patterns.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

# Core imports
from netra_backend.app.agents.execution_engine_consolidated import (
    ExecutionEngine,
    ExecutionEngineFactory,
    RequestScopedExecutionEngine,
    EngineConfig,
    AgentExecutionContext,
    AgentExecutionResult,
    UserExecutionExtension,
    WebSocketExtension,
    DataExecutionExtension,
    MCPExecutionExtension,
    execute_agent,
    execution_engine_context
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.state import DeepAgentState

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment


class TestExecutionEngineCoordination(BaseIntegrationTest):
    """Focused integration tests for ExecutionEngine coordination SSOT patterns."""
    
    def setup_method(self):
        """Set up test fixtures."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        
    @pytest.fixture
    async def test_engine_config(self):
        """Create test engine configuration."""
        config = EngineConfig(
            enable_user_features=True,
            enable_websocket_events=True,
            enable_data_features=False,
            enable_mcp=False,
            max_concurrent_agents=5,
            agent_execution_timeout=10.0,
            require_user_context=True
        )
        return config
    
    @pytest.fixture
    async def test_user_context(self):
        """Create test user execution context."""
        context = UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            websocket_connection_id=f"ws_conn_{uuid.uuid4().hex[:8]}",
            metadata={
                "user_request": "Test execution engine coordination",
                "request_type": "coordination_test"
            }
        )
        return context
    
    @pytest.fixture
    async def mock_agent_registry(self):
        """Create mock agent registry."""
        mock_registry = MagicMock()
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(return_value="test_agent_result")
        mock_registry.get_agent.return_value = mock_agent
        return mock_registry
    
    @pytest.fixture
    async def mock_websocket_bridge(self):
        """Create mock websocket bridge."""
        mock_bridge = AsyncMock()
        mock_bridge.notify_agent_started = AsyncMock()
        mock_bridge.notify_agent_completed = AsyncMock()
        mock_bridge.notify_agent_error = AsyncMock()
        return mock_bridge
    
    @pytest.mark.integration
    async def test_execution_engine_initialization_patterns(self, test_engine_config, test_user_context, mock_agent_registry, mock_websocket_bridge):
        """Test ExecutionEngine initialization SSOT patterns."""
        
        # Create engine with all components
        engine = ExecutionEngine(
            config=test_engine_config,
            registry=mock_agent_registry,
            websocket_bridge=mock_websocket_bridge,
            user_context=test_user_context
        )
        
        # Validate basic properties
        assert engine.config == test_engine_config
        assert engine.registry == mock_agent_registry
        assert engine.websocket_bridge == mock_websocket_bridge
        assert engine.user_context == test_user_context
        assert engine.engine_id.startswith("engine_")
        assert len(engine.engine_id) > 7
        
        # Validate extensions loaded based on config
        assert "user" in engine._extensions
        assert "websocket" in engine._extensions
        assert "data" not in engine._extensions  # Disabled in config
        assert "mcp" not in engine._extensions   # Disabled in config
        
        # Validate extension types
        assert isinstance(engine._extensions["user"], UserExecutionExtension)
        assert isinstance(engine._extensions["websocket"], WebSocketExtension)
        
        # Validate tracking structures initialized
        assert isinstance(engine.active_runs, dict)
        assert len(engine.active_runs) == 0
        assert isinstance(engine.run_history, list)
        assert len(engine.run_history) == 0
        assert engine.execution_tracker is not None
        
        # Validate metrics initialized
        assert engine._execution_times == []
        assert engine._success_count == 0
        assert engine._error_count == 0
        
        self.logger.info(" PASS:  ExecutionEngine initialization patterns validated")
    
    @pytest.mark.integration
    async def test_execution_engine_extension_coordination_patterns(self, test_engine_config, mock_agent_registry):
        """Test ExecutionEngine extension pattern coordination."""
        
        # Create engine with specific extensions enabled
        config_with_all = EngineConfig(
            enable_user_features=True,
            enable_data_features=True,
            enable_mcp=True,
            enable_websocket_events=True
        )
        
        engine = ExecutionEngine(
            config=config_with_all,
            registry=mock_agent_registry
        )
        
        # Validate all extensions loaded
        assert "user" in engine._extensions
        assert "data" in engine._extensions
        assert "mcp" in engine._extensions
        # websocket not loaded because no bridge provided
        assert "websocket" not in engine._extensions
        
        # Validate extension instances
        user_ext = engine._extensions["user"]
        data_ext = engine._extensions["data"]
        mcp_ext = engine._extensions["mcp"]
        
        assert isinstance(user_ext, UserExecutionExtension)
        assert isinstance(data_ext, DataExecutionExtension)
        assert isinstance(mcp_ext, MCPExecutionExtension)
        
        # Validate extension names
        assert user_ext.name() == "UserExecutionExtension"
        assert data_ext.name() == "DataExecutionExtension"
        assert mcp_ext.name() == "MCPExecutionExtension"
        
        # Test initialization coordination
        await engine.initialize()
        
        # Validate extension state after initialization
        assert user_ext.user_semaphores == {}
        assert user_ext.max_concurrent_per_user == 2
        assert data_ext.batch_size == 1000
        assert data_ext.cache_enabled is True
        assert data_ext.data_cache == {}
        
        self.logger.info(" PASS:  ExecutionEngine extension coordination patterns validated")
    
    @pytest.mark.integration
    async def test_execution_engine_user_context_coordination(self, test_engine_config, test_user_context, mock_agent_registry, mock_websocket_bridge):
        """Test ExecutionEngine coordination with UserExecutionContext."""
        
        # Create engine with user context
        engine = ExecutionEngine(
            config=test_engine_config,
            registry=mock_agent_registry,
            websocket_bridge=mock_websocket_bridge,
            user_context=test_user_context
        )
        
        await engine.initialize()
        
        # Execute agent with user context coordination
        result = await engine.execute(
            agent_name="test_coordination_agent",
            task="Test task for user context coordination"
        )
        
        # Validate execution result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.result == "test_agent_result"
        assert result.error is None
        assert result.execution_time_ms is not None
        assert result.execution_time_ms > 0
        
        # Validate user context was passed through
        assert "user_id" in result.metadata
        assert result.metadata["user_id"] == test_user_context.user_id
        
        # Validate agent registry was called properly
        mock_agent_registry.get_agent.assert_called_once_with("test_coordination_agent")
        
        # Validate WebSocket notifications coordination
        mock_websocket_bridge.notify_agent_started.assert_called_once()
        mock_websocket_bridge.notify_agent_completed.assert_called_once()
        
        # Validate metrics were tracked
        assert engine._success_count == 1
        assert engine._error_count == 0
        assert len(engine._execution_times) == 1
        
        self.logger.info(" PASS:  ExecutionEngine user context coordination validated")
    
    @pytest.mark.integration
    async def test_execution_engine_websocket_event_coordination(self, test_engine_config, mock_agent_registry, mock_websocket_bridge):
        """Test ExecutionEngine WebSocket event coordination patterns."""
        
        # Create engine with WebSocket coordination
        engine = ExecutionEngine(
            config=test_engine_config,
            registry=mock_agent_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        await engine.initialize()
        
        # Test successful execution WebSocket coordination
        result = await engine.execute(
            agent_name="websocket_test_agent",
            task="Test WebSocket event coordination"
        )
        
        # Validate WebSocket event sequence
        assert mock_websocket_bridge.notify_agent_started.call_count == 1
        assert mock_websocket_bridge.notify_agent_completed.call_count == 1
        assert mock_websocket_bridge.notify_agent_error.call_count == 0
        
        # Validate event parameters
        start_call_args = mock_websocket_bridge.notify_agent_started.call_args
        assert start_call_args[0][0] == "websocket_test_agent"
        assert start_call_args[0][1] == "Test WebSocket event coordination"
        
        complete_call_args = mock_websocket_bridge.notify_agent_completed.call_args
        assert complete_call_args[0][0] == "websocket_test_agent"
        assert complete_call_args[0][1] == "test_agent_result"
        
        # Test error execution WebSocket coordination
        mock_agent_registry.get_agent.return_value.execute = AsyncMock(side_effect=Exception("Test error"))
        mock_websocket_bridge.reset_mock()
        
        error_result = await engine.execute(
            agent_name="websocket_error_agent",
            task="Test WebSocket error coordination"
        )
        
        # Validate error WebSocket coordination
        assert error_result.success is False
        assert "Test error" in error_result.error
        assert mock_websocket_bridge.notify_agent_started.call_count == 1
        assert mock_websocket_bridge.notify_agent_completed.call_count == 0
        assert mock_websocket_bridge.notify_agent_error.call_count == 1
        
        self.logger.info(" PASS:  ExecutionEngine WebSocket event coordination validated")
    
    @pytest.mark.integration
    async def test_execution_engine_factory_patterns(self, test_user_context):
        """Test ExecutionEngineFactory coordination patterns."""
        
        # Test basic engine creation
        engine = ExecutionEngineFactory.create_engine()
        
        assert isinstance(engine, ExecutionEngine)
        assert isinstance(engine.config, EngineConfig)
        assert engine.registry is None  # No default registry
        assert engine.websocket_bridge is None  # No default bridge
        assert engine.user_context is None
        
        # Test user engine creation
        user_engine = ExecutionEngineFactory.create_user_engine(test_user_context)
        
        assert isinstance(user_engine, ExecutionEngine)
        assert user_engine.config.enable_user_features is True
        assert user_engine.config.enable_websocket_events is True
        assert user_engine.config.require_user_context is True
        assert user_engine.user_context == test_user_context
        
        # Test data engine creation
        data_engine = ExecutionEngineFactory.create_data_engine()
        
        assert isinstance(data_engine, ExecutionEngine)
        assert data_engine.config.enable_data_features is True
        assert data_engine.config.max_concurrent_agents == 20
        assert data_engine.config.agent_execution_timeout == 60.0
        
        # Test MCP engine creation
        mcp_engine = ExecutionEngineFactory.create_mcp_engine()
        
        assert isinstance(mcp_engine, ExecutionEngine)
        assert mcp_engine.config.enable_mcp is True
        assert mcp_engine.config.enable_websocket_events is True
        
        self.logger.info(" PASS:  ExecutionEngineFactory patterns validated")
    
    @pytest.mark.integration
    async def test_execution_engine_request_scoped_coordination(self, test_user_context, mock_agent_registry):
        """Test ExecutionEngine request-scoped coordination patterns."""
        
        # Create base engine
        base_engine = ExecutionEngine(
            registry=mock_agent_registry,
            user_context=test_user_context
        )
        
        await base_engine.initialize()
        
        # Create request-scoped engine
        request_id = f"test_request_{uuid.uuid4().hex[:8]}"
        scoped_engine = base_engine.with_request_scope(request_id)
        
        assert isinstance(scoped_engine, RequestScopedExecutionEngine)
        assert scoped_engine.engine == base_engine
        assert scoped_engine.request_id == request_id
        assert scoped_engine._closed is False
        
        # Execute through scoped engine
        result = await scoped_engine.execute(
            agent_name="scoped_test_agent",
            task="Test request scoped coordination"
        )
        
        # Validate execution result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.result == "test_agent_result"
        
        # Test scoped engine lifecycle
        await scoped_engine.close()
        assert scoped_engine._closed is True
        
        # Test that closed engine raises error
        with pytest.raises(RuntimeError, match="RequestScopedExecutionEngine has been closed"):
            await scoped_engine.execute("test_agent", "test_task")
        
        # Test factory method for request-scoped creation
        factory_scoped = ExecutionEngineFactory.create_request_scoped_engine(
            request_id=f"factory_request_{uuid.uuid4().hex[:8]}",
            user_context=test_user_context,
            registry=mock_agent_registry
        )
        
        assert isinstance(factory_scoped, RequestScopedExecutionEngine)
        assert factory_scoped.engine.user_context == test_user_context
        
        self.logger.info(" PASS:  ExecutionEngine request-scoped coordination validated")
    
    @pytest.mark.integration
    async def test_execution_engine_error_handling_coordination(self, mock_agent_registry, mock_websocket_bridge):
        """Test ExecutionEngine error handling coordination patterns."""
        
        # Create engine for error testing
        engine = ExecutionEngine(
            registry=mock_agent_registry,
            websocket_bridge=mock_websocket_bridge
        )
        
        await engine.initialize()
        
        # Test agent not found error
        mock_agent_registry.get_agent.return_value = None
        result = await engine.execute("nonexistent_agent", "test_task")
        
        assert result.success is False
        assert "Agent 'nonexistent_agent' not found in registry" in result.error
        assert result.execution_time_ms is not None
        
        # Test agent execution error
        mock_agent = MagicMock()
        mock_agent.execute = AsyncMock(side_effect=ValueError("Agent execution error"))
        mock_agent_registry.get_agent.return_value = mock_agent
        
        error_result = await engine.execute("error_agent", "test_task")
        
        assert error_result.success is False
        assert "Agent execution error" in error_result.error
        
        # Test timeout error
        mock_slow_agent = MagicMock()
        mock_slow_agent.execute = AsyncMock(side_effect=asyncio.sleep(30))  # Longer than timeout
        mock_agent_registry.get_agent.return_value = mock_slow_agent
        
        # Use shorter timeout for test
        engine.config.agent_execution_timeout = 0.1
        
        timeout_result = await engine.execute("slow_agent", "test_task")
        
        assert timeout_result.success is False
        assert "execution timed out" in timeout_result.error.lower()
        
        # Validate error metrics
        assert engine._error_count > 0
        
        self.logger.info(" PASS:  ExecutionEngine error handling coordination validated")
    
    @pytest.mark.integration
    async def test_execution_engine_concurrent_coordination_safety(self, test_user_context, mock_agent_registry):
        """Test ExecutionEngine maintains coordination safety under concurrent operations."""
        
        # Create engine for concurrent testing
        engine = ExecutionEngine(
            registry=mock_agent_registry,
            user_context=test_user_context,
            config=EngineConfig(max_concurrent_agents=3)
        )
        
        await engine.initialize()
        
        async def execute_concurrent_agent(agent_suffix: str) -> AgentExecutionResult:
            """Execute agent with unique suffix for concurrent testing."""
            return await engine.execute(
                agent_name=f"concurrent_agent_{agent_suffix}",
                task=f"Concurrent task {agent_suffix}"
            )
        
        # Run multiple concurrent executions
        tasks = []
        for i in range(5):
            task = execute_concurrent_agent(f"test_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Validate all executions completed successfully
        success_count = 0
        for result in results:
            if isinstance(result, AgentExecutionResult):
                if result.success:
                    success_count += 1
                assert result.result == "test_agent_result"
                assert result.execution_time_ms is not None
            else:
                # Should not have exceptions in this test
                assert False, f"Unexpected exception: {result}"
        
        assert success_count == 5
        
        # Validate metrics tracked correctly
        assert engine._success_count == 5
        assert len(engine._execution_times) == 5
        
        # Validate no active runs remain
        assert len(engine.active_runs) == 0
        
        self.logger.info(" PASS:  ExecutionEngine concurrent coordination safety validated")


# Additional helper functions for coordination validation

def validate_engine_configuration(engine: ExecutionEngine, expected_config: EngineConfig) -> None:
    """Validate that engine has expected configuration."""
    assert engine.config.enable_user_features == expected_config.enable_user_features
    assert engine.config.enable_websocket_events == expected_config.enable_websocket_events
    assert engine.config.enable_data_features == expected_config.enable_data_features
    assert engine.config.enable_mcp == expected_config.enable_mcp
    assert engine.config.max_concurrent_agents == expected_config.max_concurrent_agents


def validate_extension_coordination(engine: ExecutionEngine, expected_extensions: List[str]) -> None:
    """Validate that engine has expected extensions loaded."""
    actual_extensions = set(engine._extensions.keys())
    expected_set = set(expected_extensions)
    assert actual_extensions == expected_set, f"Expected {expected_set}, got {actual_extensions}"


def validate_execution_result_structure(result: AgentExecutionResult) -> None:
    """Validate that execution result has expected SSOT structure."""
    assert isinstance(result.success, bool)
    assert result.execution_time_ms is not None
    assert isinstance(result.execution_time_ms, float)
    assert result.execution_time_ms >= 0
    assert isinstance(result.metadata, dict)
    
    if result.success:
        assert result.result is not None
        assert result.error is None
    else:
        assert result.error is not None
        assert isinstance(result.error, str)
        assert len(result.error) > 0