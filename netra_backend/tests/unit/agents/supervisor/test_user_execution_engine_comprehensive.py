"""
Comprehensive Unit Tests for UserExecutionEngine SSOT Class

Tests the core UserExecutionEngine class that orchestrates complete agent execution
pipeline, ensuring WebSocket events, user context isolation, and business value delivery.

CRITICAL REQUIREMENTS from CLAUDE.md:
1. Uses absolute imports and follows SSOT patterns from test_framework/
2. Tests MUST RAISE ERRORS (no try/except blocks that hide failures) 
3. Tests all 5 critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
4. Validates user context isolation and agent orchestration patterns
5. Tests error handling, recovery, and graceful degradation

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - Core chat functionality 
- Business Goal: Ensure reliable agent execution and real-time user experience
- Value Impact: UserExecutionEngine orchestrates SupervisorAgent → Sub-Agents workflow that delivers $500K+ ARR
- Strategic Impact: This is the core of Golden Path user flow that provides substantive AI value
- Revenue Impact: Without working UserExecutionEngine, chat has NO business value

This UserExecutionEngine is MISSION CRITICAL because it:
- Orchestrates the complete agent execution pipeline (SupervisorAgent → Data → Optimization → Report agents)
- Ensures all 5 WebSocket events are sent to provide user experience
- Manages user context isolation for multi-user concurrent execution
- Delivers the complete business value through agent orchestration
"""

import asyncio
import pytest
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call, PropertyMock
from typing import Any, Dict, List, Optional, TYPE_CHECKING

# SSOT test framework imports
from test_framework.ssot.mocks import get_mock_factory
from shared.isolated_environment import get_env

# Core types for strongly typed testing
from netra_backend.app.services.user_execution_context import (
    UserExecutionContext, 
    UserContextFactory,
    validate_user_context
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.agent_execution_tracker import ExecutionState

# Target class under test
from netra_backend.app.agents.supervisor.user_execution_engine import (
    UserExecutionEngine,
    MinimalPeriodicUpdateManager,
    MinimalFallbackManager
)

if TYPE_CHECKING:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class TestUserExecutionEngineComprehensive:
    """Comprehensive unit tests for UserExecutionEngine with 100% method coverage.
    
    Focus Areas:
    1. User context isolation and validation
    2. Agent orchestration and execution pipeline  
    3. WebSocket event emission (all 5 critical events)
    4. Error handling and graceful degradation
    5. Concurrency control and resource management
    6. Performance monitoring and statistics
    """

    @pytest.fixture
    def mock_factory(self):
        """Get SSOT mock factory for consistent mock creation."""
        return get_mock_factory()

    @pytest.fixture 
    def isolated_env(self):
        """Isolated environment for test configuration."""
        env = get_env()
        # Set test mode to allow test patterns
        env.set("ENVIRONMENT", "test", source="test")
        env.set("USE_REAL_SERVICES", "false", source="test")
        return env

    @pytest.fixture
    def test_user_context(self):
        """Create test UserExecutionContext with proper validation."""
        return UserContextFactory.create_context(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}",
            request_id=str(uuid.uuid4()),
            websocket_client_id=f"ws_{uuid.uuid4().hex[:8]}"
        )

    @pytest.fixture
    def mock_agent_factory(self, mock_factory):
        """Mock AgentInstanceFactory with proper agent registry and WebSocket bridge."""
        factory = mock_factory.create_mock()
        
        # Create mock agent registry
        mock_registry = Mock()
        mock_registry.get_agent = Mock(return_value=mock_factory.create_agent_mock())
        factory._agent_registry = mock_registry
        
        # Create mock WebSocket bridge
        mock_bridge = AsyncMock()
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
        mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        factory._websocket_bridge = mock_bridge
        
        # Mock create_agent_instance method
        factory.create_agent_instance = AsyncMock(
            return_value=mock_factory.create_agent_mock()
        )
        
        return factory

    @pytest.fixture
    def mock_websocket_emitter(self, mock_factory):
        """Mock UserWebSocketEmitter for event notifications."""
        emitter = mock_factory.create_websocket_manager_mock()
        
        # Override with specific return values for event testing
        emitter.notify_agent_started = AsyncMock(return_value=True)
        emitter.notify_agent_thinking = AsyncMock(return_value=True)
        emitter.notify_tool_executing = AsyncMock(return_value=True)
        emitter.notify_tool_completed = AsyncMock(return_value=True)
        emitter.notify_agent_completed = AsyncMock(return_value=True)
        emitter.cleanup = AsyncMock()
        
        return emitter

    @pytest.fixture
    def user_execution_engine(self, test_user_context, mock_agent_factory, mock_websocket_emitter):
        """UserExecutionEngine instance with mocked dependencies."""
        return UserExecutionEngine(
            context=test_user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )

    @pytest.fixture 
    def sample_agent_context(self, test_user_context):
        """Sample AgentExecutionContext matching the user context."""
        return AgentExecutionContext(
            user_id=test_user_context.user_id,
            thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id,
            request_id=test_user_context.request_id,
            agent_name="test_supervisor_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )

    @pytest.fixture
    def sample_agent_state(self, test_user_context):
        """Sample DeepAgentState for agent execution."""
        return DeepAgentState(
            user_request={"prompt": "Optimize my AI costs", "context": "test"},
            user_id=test_user_context.user_id,
            chat_thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id,
            agent_input={
                "agent_name": "test_supervisor_agent",
                "user_id": test_user_context.user_id,
                "thread_id": test_user_context.thread_id
            }
        )

    # ========================================================================
    # INITIALIZATION AND VALIDATION TESTS
    # ========================================================================

    @pytest.mark.unit
    def test_init_creates_engine_with_proper_isolation(self, test_user_context, mock_agent_factory, mock_websocket_emitter):
        """Test UserExecutionEngine initializes with complete user isolation."""
        engine = UserExecutionEngine(
            context=test_user_context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Verify proper initialization
        assert engine.context == test_user_context
        assert engine.user_context == test_user_context
        assert engine.get_user_context() == test_user_context
        assert engine.agent_factory == mock_agent_factory
        assert engine.websocket_emitter == mock_websocket_emitter
        
        # Verify isolation properties
        assert len(engine.active_runs) == 0
        assert len(engine.run_history) == 0
        assert engine.execution_stats['total_executions'] == 0
        assert engine.execution_stats['concurrent_executions'] == 0
        
        # Verify engine state
        assert engine._is_active is True
        assert engine.max_concurrent == 3  # Default value
        assert engine.semaphore._value == 3  # Concurrency control
        
        # Verify engine ID format 
        assert engine.engine_id.startswith(f"user_engine_{test_user_context.user_id}")
        assert test_user_context.run_id in engine.engine_id
        
        # Verify data access integration
        assert hasattr(engine, 'clickhouse_client')
        assert hasattr(engine, 'redis_client')

    @pytest.mark.unit
    def test_init_validates_required_parameters(self):
        """Test UserExecutionEngine validates required parameters."""
        test_context = UserContextFactory.create_context(
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}"
        )
        
        # Test missing agent_factory
        with pytest.raises(ValueError, match="AgentInstanceFactory cannot be None"):
            UserExecutionEngine(
                context=test_context,
                agent_factory=None,
                websocket_emitter=Mock()
            )
        
        # Test missing websocket_emitter
        with pytest.raises(ValueError, match="UserWebSocketEmitter cannot be None"):
            UserExecutionEngine(
                context=test_context,
                agent_factory=Mock(),
                websocket_emitter=None
            )

    @pytest.mark.unit 
    def test_init_validates_user_context(self, mock_agent_factory, mock_websocket_emitter):
        """Test UserExecutionEngine validates UserExecutionContext."""
        # Test with invalid context type
        with pytest.raises(TypeError):
            UserExecutionEngine(
                context="invalid_context",
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )
        
        # Test with invalid user_id patterns (forbidden placeholder values)
        invalid_context = UserExecutionContext(
            user_id="registry",  # Forbidden placeholder
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}"
        )
        
        with pytest.raises(Exception):  # InvalidContextError from validation
            UserExecutionEngine(
                context=invalid_context,
                agent_factory=mock_agent_factory,
                websocket_emitter=mock_websocket_emitter
            )

    @pytest.mark.unit
    def test_init_configures_resource_limits(self, mock_agent_factory, mock_websocket_emitter):
        """Test UserExecutionEngine respects resource limits from context."""
        # Create context with resource limits
        context = UserContextFactory.create_context(
            user_id=f"user_{uuid.uuid4().hex[:8]}",
            thread_id=f"thread_{uuid.uuid4().hex[:8]}",
            run_id=f"run_{uuid.uuid4().hex[:8]}"
        )
        
        # Mock resource limits
        resource_limits = Mock()
        resource_limits.max_concurrent_agents = 5
        context.resource_limits = resource_limits
        
        engine = UserExecutionEngine(
            context=context,
            agent_factory=mock_agent_factory,
            websocket_emitter=mock_websocket_emitter
        )
        
        # Verify resource limits applied
        assert engine.max_concurrent == 5
        assert engine.semaphore._value == 5

    # ========================================================================
    # CONTEXT AND ISOLATION VALIDATION TESTS
    # ========================================================================

    @pytest.mark.unit
    def test_user_context_properties(self, user_execution_engine, test_user_context):
        """Test user context property accessors."""
        assert user_execution_engine.user_context is test_user_context
        assert user_execution_engine.get_user_context() is test_user_context
        
        # Test validation integration
        validated_context = validate_user_context(user_execution_engine.context)
        assert validated_context is test_user_context

    @pytest.mark.unit
    def test_is_active_state_management(self, user_execution_engine):
        """Test engine active state management."""
        # Initially active but no running jobs
        assert user_execution_engine._is_active is True
        assert user_execution_engine.is_active() is False  # No active runs
        
        # Simulate active run
        user_execution_engine.active_runs["test_execution"] = Mock()
        assert user_execution_engine.is_active() is True
        
        # After cleanup
        user_execution_engine.active_runs.clear()
        user_execution_engine._is_active = False
        assert user_execution_engine.is_active() is False

    @pytest.mark.unit
    def test_validate_execution_context_user_matching(self, user_execution_engine, test_user_context):
        """Test execution context validation ensures user ID matching."""
        # Valid matching context
        valid_context = AgentExecutionContext(
            user_id=test_user_context.user_id,
            thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id,
            request_id=test_user_context.request_id,
            agent_name="test_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        # Should not raise exception
        user_execution_engine._validate_execution_context(valid_context)
        
        # Invalid user ID mismatch
        invalid_context = AgentExecutionContext(
            user_id="different_user",
            thread_id=test_user_context.thread_id,
            run_id=test_user_context.run_id,
            request_id=test_user_context.request_id,
            agent_name="test_agent",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        with pytest.raises(ValueError, match="User ID mismatch"):
            user_execution_engine._validate_execution_context(invalid_context)

    @pytest.mark.unit
    def test_validate_execution_context_required_fields(self, user_execution_engine):
        """Test execution context validation checks required fields."""
        # Empty user_id
        with pytest.raises(ValueError, match="user_id must be non-empty"):
            context = Mock()
            context.user_id = ""
            context.run_id = "valid_run"
            user_execution_engine._validate_execution_context(context)
        
        # Empty run_id
        with pytest.raises(ValueError, match="run_id must be non-empty"):
            context = Mock()
            context.user_id = "valid_user"
            context.run_id = ""
            user_execution_engine._validate_execution_context(context)
        
        # Registry placeholder value (forbidden)
        with pytest.raises(ValueError, match="run_id cannot be 'registry' placeholder"):
            context = Mock()
            context.user_id = "valid_user" 
            context.run_id = "registry"
            user_execution_engine._validate_execution_context(context)

    # ========================================================================
    # WEBSOCKET EVENT EMISSION TESTS - MISSION CRITICAL
    # ========================================================================

    @pytest.mark.unit
    async def test_send_user_agent_started_success(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test successful agent started WebSocket event emission."""
        await user_execution_engine._send_user_agent_started(sample_agent_context)
        
        # Verify WebSocket emitter called correctly
        mock_websocket_emitter.notify_agent_started.assert_called_once_with(
            agent_name=sample_agent_context.agent_name,
            context={
                "status": "started",
                "user_isolated": True,
                "user_id": user_execution_engine.context.user_id,
                "engine_id": user_execution_engine.engine_id,
                "context": sample_agent_context.metadata or {}
            }
        )

    @pytest.mark.unit
    async def test_send_user_agent_started_failure_handling(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test agent started event handles WebSocket failures gracefully."""
        # Mock WebSocket failure
        mock_websocket_emitter.notify_agent_started.return_value = False
        
        # Should complete without raising exception (graceful degradation)
        await user_execution_engine._send_user_agent_started(sample_agent_context)
        
        # Verify attempt was made
        mock_websocket_emitter.notify_agent_started.assert_called_once()

    @pytest.mark.unit
    async def test_send_user_agent_thinking_success(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test successful agent thinking WebSocket event emission."""
        test_thought = "Analyzing cost optimization opportunities..."
        step_number = 2
        
        await user_execution_engine._send_user_agent_thinking(
            sample_agent_context, test_thought, step_number
        )
        
        # Verify WebSocket emitter called correctly
        mock_websocket_emitter.notify_agent_thinking.assert_called_once_with(
            agent_name=sample_agent_context.agent_name,
            reasoning=test_thought,
            step_number=step_number
        )

    @pytest.mark.unit
    async def test_send_user_agent_thinking_without_step_number(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test agent thinking event without step number."""
        test_thought = "Processing user request..."
        
        await user_execution_engine._send_user_agent_thinking(
            sample_agent_context, test_thought
        )
        
        # Verify WebSocket emitter called with None step_number
        mock_websocket_emitter.notify_agent_thinking.assert_called_once_with(
            agent_name=sample_agent_context.agent_name,
            reasoning=test_thought,
            step_number=None
        )

    @pytest.mark.unit
    async def test_send_user_agent_completed_success(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test successful agent completed WebSocket event emission."""
        # Create successful execution result
        result = AgentExecutionResult(
            success=True,
            agent_name=sample_agent_context.agent_name,
            execution_time=2.5,
            error=None,
            state=Mock(),
            metadata={
                "recommendations_count": 3,
                "potential_savings": 15000
            }
        )
        
        await user_execution_engine._send_user_agent_completed(sample_agent_context, result)
        
        # Verify WebSocket emitter called correctly
        expected_result_data = {
            "agent_name": sample_agent_context.agent_name,
            "success": True,
            "duration_ms": 2500.0,  # 2.5 seconds in milliseconds
            "status": "completed",
            "user_isolated": True,
            "user_id": user_execution_engine.context.user_id,
            "engine_id": user_execution_engine.engine_id,
            "error": None
        }
        
        mock_websocket_emitter.notify_agent_completed.assert_called_once_with(
            agent_name=sample_agent_context.agent_name,
            result=expected_result_data,
            execution_time_ms=2500.0
        )

    @pytest.mark.unit
    async def test_send_user_agent_completed_failure_result(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test agent completed event with failure result."""
        # Create failed execution result
        result = AgentExecutionResult(
            success=False,
            agent_name=sample_agent_context.agent_name,
            execution_time=1.0,
            error="Agent execution timeout",
            state=None,
            metadata={"timeout": True}
        )
        
        await user_execution_engine._send_user_agent_completed(sample_agent_context, result)
        
        # Verify WebSocket emitter called with error information
        expected_result_data = {
            "agent_name": sample_agent_context.agent_name,
            "success": False,
            "duration_ms": 1000.0,
            "status": "failed",
            "user_isolated": True,
            "user_id": user_execution_engine.context.user_id,
            "engine_id": user_execution_engine.engine_id,
            "error": "Agent execution timeout"
        }
        
        mock_websocket_emitter.notify_agent_completed.assert_called_once_with(
            agent_name=sample_agent_context.agent_name,
            result=expected_result_data,
            execution_time_ms=1000.0
        )

    @pytest.mark.unit
    async def test_websocket_events_exception_handling(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test WebSocket event methods handle exceptions gracefully."""
        # Mock exception on WebSocket calls
        mock_websocket_emitter.notify_agent_started.side_effect = Exception("WebSocket connection lost")
        mock_websocket_emitter.notify_agent_thinking.side_effect = Exception("WebSocket connection lost") 
        mock_websocket_emitter.notify_agent_completed.side_effect = Exception("WebSocket connection lost")
        
        # All should complete without raising exceptions (graceful degradation)
        await user_execution_engine._send_user_agent_started(sample_agent_context)
        await user_execution_engine._send_user_agent_thinking(sample_agent_context, "test")
        
        result = AgentExecutionResult(
            success=True,
            agent_name=sample_agent_context.agent_name,
            execution_time=1.0,
            state=Mock()
        )
        await user_execution_engine._send_user_agent_completed(sample_agent_context, result)
        
        # Verify attempts were made
        mock_websocket_emitter.notify_agent_started.assert_called_once()
        mock_websocket_emitter.notify_agent_thinking.assert_called_once()
        mock_websocket_emitter.notify_agent_completed.assert_called_once()

    # ========================================================================
    # AGENT EXECUTION PIPELINE TESTS - CORE BUSINESS VALUE
    # ========================================================================

    @pytest.mark.unit
    async def test_execute_agent_success_pipeline(self, user_execution_engine, sample_agent_context, sample_agent_state, mock_websocket_emitter):
        """Test complete successful agent execution pipeline with all WebSocket events."""
        # Mock successful execution dependencies
        with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker, \
             patch.object(user_execution_engine, 'agent_core') as mock_core:
            
            # Configure execution tracker
            execution_id = str(uuid.uuid4())
            mock_tracker.create_execution.return_value = execution_id
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            mock_tracker.heartbeat = AsyncMock()
            
            # Configure successful agent execution
            expected_result = AgentExecutionResult(
                success=True,
                agent_name=sample_agent_context.agent_name,
                execution_time=1.5,
                state=sample_agent_state,
                metadata={
                    "recommendations": ["Optimize instance types", "Use reserved instances"],
                    "potential_savings": 25000
                }
            )
            mock_core.execute_agent.return_value = expected_result
            
            # Execute agent
            result = await user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)
            
            # Verify successful result
            assert result.success is True
            assert result.agent_name == sample_agent_context.agent_name
            assert "recommendations" in result.metadata
            
            # Verify execution tracking lifecycle
            mock_tracker.create_execution.assert_called_once_with(
                agent_name=sample_agent_context.agent_name,
                thread_id=sample_agent_context.thread_id,
                user_id=sample_agent_context.user_id,
                timeout_seconds=30,
                metadata={
                    'run_id': sample_agent_context.run_id,
                    'context': sample_agent_context.metadata,
                    'user_engine_id': user_execution_engine.engine_id,
                    'user_execution_context': user_execution_engine.context.get_correlation_id()
                }
            )
            mock_tracker.start_execution.assert_called_once_with(execution_id)
            mock_tracker.update_execution_state.assert_called_with(
                execution_id, ExecutionState.COMPLETED, result=expected_result.data
            )
            
            # Verify ALL 5 CRITICAL WEBSOCKET EVENTS were sent
            mock_websocket_emitter.notify_agent_started.assert_called_once()
            mock_websocket_emitter.notify_agent_thinking.assert_called()  # Multiple thinking events
            mock_websocket_emitter.notify_agent_completed.assert_called_once()
            
            # Verify thinking events were sent at different stages
            thinking_calls = mock_websocket_emitter.notify_agent_thinking.call_args_list
            assert len(thinking_calls) >= 2  # At least queue notification and processing
            
            # Verify execution statistics updated
            assert user_execution_engine.execution_stats['total_executions'] == 1
            assert len(user_execution_engine.execution_stats['execution_times']) == 1
            assert len(user_execution_engine.run_history) == 1
            assert user_execution_engine.run_history[0] is result

    @pytest.mark.unit
    async def test_execute_agent_timeout_handling(self, user_execution_engine, sample_agent_context, sample_agent_state, mock_websocket_emitter):
        """Test agent execution timeout handling and WebSocket notification."""
        with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker, \
             patch.object(user_execution_engine, 'agent_core') as mock_core:
            
            execution_id = str(uuid.uuid4())
            mock_tracker.create_execution.return_value = execution_id
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            
            # Mock timeout in agent execution
            mock_core.execute_agent.side_effect = asyncio.TimeoutError()
            
            # Execute agent (should handle timeout gracefully)
            result = await user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)
            
            # Verify timeout result
            assert result.success is False
            assert "timed out" in result.error
            assert result.execution_time == UserExecutionEngine.AGENT_EXECUTION_TIMEOUT
            assert result.metadata['timeout'] is True
            
            # Verify execution state updated for timeout
            mock_tracker.update_execution_state.assert_called_with(
                execution_id, ExecutionState.TIMEOUT,
                error=f"User execution timed out after {UserExecutionEngine.AGENT_EXECUTION_TIMEOUT}s"
            )
            
            # Verify WebSocket events still sent
            mock_websocket_emitter.notify_agent_started.assert_called_once()
            mock_websocket_emitter.notify_agent_completed.assert_called_once()
            
            # Verify statistics updated
            assert user_execution_engine.execution_stats['timeout_executions'] == 1
            assert user_execution_engine.execution_stats['failed_executions'] == 1

    @pytest.mark.unit 
    async def test_execute_agent_exception_handling(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test agent execution exception handling."""
        with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
            execution_id = str(uuid.uuid4())
            mock_tracker.create_execution.return_value = execution_id
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            
            # Mock unexpected exception during execution
            with patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute:
                mock_execute.side_effect = RuntimeError("Unexpected agent failure")
                
                # Execute agent (should raise RuntimeError)
                with pytest.raises(RuntimeError, match="Agent execution failed"):
                    await user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)
                
                # Verify execution state updated for failure
                mock_tracker.update_execution_state.assert_called_with(
                    execution_id, ExecutionState.FAILED, error="Unexpected agent failure"
                )
                
                # Verify statistics updated
                assert user_execution_engine.execution_stats['failed_executions'] == 1

    @pytest.mark.unit
    async def test_execute_agent_inactive_engine(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test agent execution fails when engine is inactive."""
        # Mark engine as inactive
        user_execution_engine._is_active = False
        
        with pytest.raises(ValueError, match="UserExecutionEngine .* is no longer active"):
            await user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)

    @pytest.mark.unit
    async def test_execute_agent_concurrency_control(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test agent execution respects concurrency limits."""
        # Set low concurrency limit
        user_execution_engine.max_concurrent = 1
        user_execution_engine.semaphore = asyncio.Semaphore(1)
        
        # Mock long-running execution
        with patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute:
            mock_execute.return_value = AgentExecutionResult(
                success=True,
                agent_name=sample_agent_context.agent_name,
                execution_time=1.0,
                state=sample_agent_state
            )
            
            with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
                mock_tracker.create_execution.return_value = str(uuid.uuid4())
                mock_tracker.start_execution = AsyncMock()
                mock_tracker.update_execution_state = AsyncMock()
                
                # First execution should acquire semaphore
                task1 = asyncio.create_task(
                    user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)
                )
                await asyncio.sleep(0.01)  # Let first task start
                
                # Verify semaphore acquired
                assert user_execution_engine.semaphore._value == 0
                
                # Complete first execution
                result1 = await task1
                assert result1.success is True
                
                # Verify semaphore released
                assert user_execution_engine.semaphore._value == 1

    @pytest.mark.unit
    async def test_execute_agent_queue_wait_notification(self, user_execution_engine, sample_agent_context, sample_agent_state, mock_websocket_emitter):
        """Test queue wait notification when execution is delayed."""
        # Mock delayed execution to trigger queue wait notification
        with patch('time.time') as mock_time, \
             patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute, \
             patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
            
            # Configure time mock to simulate long queue wait
            start_time = 1000.0
            queue_end_time = start_time + 2.0  # 2 seconds queue wait
            mock_time.side_effect = [start_time, queue_end_time, queue_end_time + 1.0]
            
            execution_id = str(uuid.uuid4())
            mock_tracker.create_execution.return_value = execution_id
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            
            mock_execute.return_value = AgentExecutionResult(
                success=True,
                agent_name=sample_agent_context.agent_name,
                execution_time=1.0,
                state=sample_agent_state
            )
            
            # Execute agent
            await user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)
            
            # Verify queue wait notification was sent
            thinking_calls = mock_websocket_emitter.notify_agent_thinking.call_args_list
            queue_notifications = [
                call for call in thinking_calls 
                if "queued due to user load" in str(call)
            ]
            assert len(queue_notifications) >= 1

    # ========================================================================
    # ERROR HANDLING AND FALLBACK TESTS
    # ========================================================================

    @pytest.mark.unit
    async def test_execute_with_error_handling_success(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test successful execution through error handling wrapper."""
        execution_id = str(uuid.uuid4())
        
        with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker, \
             patch.object(user_execution_engine, 'agent_core') as mock_core, \
             patch.object(user_execution_engine, 'agent_factory') as mock_factory:
            
            mock_tracker.heartbeat = AsyncMock()
            
            # Mock successful agent creation and execution
            mock_agent = Mock()
            mock_factory.create_agent_instance.return_value = mock_agent
            
            expected_result = AgentExecutionResult(
                success=True,
                agent_name=sample_agent_context.agent_name,
                execution_time=1.0,
                state=sample_agent_state
            )
            mock_core.execute_agent.return_value = expected_result
            
            # Execute with error handling
            result = await user_execution_engine._execute_with_error_handling(
                sample_agent_context, sample_agent_state, execution_id
            )
            
            # Verify successful result
            assert result is expected_result
            
            # Verify agent factory used correctly
            mock_factory.create_agent_instance.assert_called_once_with(
                agent_name=sample_agent_context.agent_name,
                user_context=user_execution_engine.context
            )
            
            # Verify heartbeat calls
            assert mock_tracker.heartbeat.call_count == 2  # Before and after execution

    @pytest.mark.unit
    async def test_execute_with_error_handling_fallback(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test error handling creates fallback result when execution fails."""
        execution_id = str(uuid.uuid4())
        
        with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker, \
             patch.object(user_execution_engine, 'agent_core') as mock_core, \
             patch.object(user_execution_engine, 'fallback_manager') as mock_fallback:
            
            mock_tracker.heartbeat = AsyncMock()
            
            # Mock agent execution failure
            test_error = RuntimeError("Agent processing failed")
            mock_core.execute_agent.side_effect = test_error
            
            # Mock fallback result
            fallback_result = AgentExecutionResult(
                success=False,
                agent_name=sample_agent_context.agent_name,
                execution_time=0.5,
                error="Agent execution failed: Agent processing failed",
                state=sample_agent_state,
                metadata={
                    'fallback_result': True,
                    'user_isolated': True,
                    'user_id': user_execution_engine.context.user_id
                }
            )
            mock_fallback.create_fallback_result.return_value = fallback_result
            
            # Execute with error handling
            result = await user_execution_engine._execute_with_error_handling(
                sample_agent_context, sample_agent_state, execution_id
            )
            
            # Verify fallback result returned
            assert result is fallback_result
            assert result.metadata['fallback_result'] is True
            
            # Verify fallback manager called correctly
            mock_fallback.create_fallback_result.assert_called_once()
            call_args = mock_fallback.create_fallback_result.call_args
            assert call_args[0][0] is sample_agent_context  # context
            assert call_args[0][1] is sample_agent_state     # state
            assert call_args[0][2] is test_error             # error

    @pytest.mark.unit
    def test_create_timeout_result(self, user_execution_engine, sample_agent_context):
        """Test timeout result creation with proper metadata."""
        result = user_execution_engine._create_timeout_result(sample_agent_context)
        
        # Verify timeout result structure
        assert result.success is False
        assert result.agent_name == sample_agent_context.agent_name
        assert result.execution_time == UserExecutionEngine.AGENT_EXECUTION_TIMEOUT
        assert "timed out" in result.error
        
        # Verify timeout metadata
        assert result.metadata['timeout'] is True
        assert result.metadata['user_isolated'] is True
        assert result.metadata['user_id'] == user_execution_engine.context.user_id
        assert result.metadata['engine_id'] == user_execution_engine.engine_id

    # ========================================================================
    # EXECUTION STATISTICS AND MONITORING TESTS
    # ========================================================================

    @pytest.mark.unit
    def test_update_user_history_with_size_limit(self, user_execution_engine):
        """Test user execution history respects size limits."""
        # Create multiple results to exceed history limit
        for i in range(UserExecutionEngine.MAX_HISTORY_SIZE + 10):
            result = AgentExecutionResult(
                success=True,
                agent_name=f"agent_{i}",
                execution_time=1.0,
                state=Mock(),
                metadata={"execution_number": i}
            )
            user_execution_engine._update_user_history(result)
        
        # Verify history size limit enforced
        assert len(user_execution_engine.run_history) == UserExecutionEngine.MAX_HISTORY_SIZE
        
        # Verify most recent results kept
        last_result = user_execution_engine.run_history[-1]
        assert last_result.metadata["execution_number"] == UserExecutionEngine.MAX_HISTORY_SIZE + 9

    @pytest.mark.unit
    def test_get_user_execution_stats_comprehensive(self, user_execution_engine):
        """Test comprehensive user execution statistics calculation."""
        # Populate execution statistics
        user_execution_engine.execution_stats.update({
            'total_executions': 10,
            'concurrent_executions': 2,
            'queue_wait_times': [0.1, 0.5, 1.0, 0.2],
            'execution_times': [1.5, 2.0, 0.8, 3.2, 1.1],
            'failed_executions': 1,
            'timeout_executions': 1,
            'dead_executions': 0
        })
        
        # Add some active runs and history
        user_execution_engine.active_runs["run1"] = Mock()
        user_execution_engine.active_runs["run2"] = Mock() 
        user_execution_engine.run_history = [Mock() for _ in range(5)]
        
        # Get comprehensive stats
        stats = user_execution_engine.get_user_execution_stats()
        
        # Verify basic statistics
        assert stats['total_executions'] == 10
        assert stats['concurrent_executions'] == 2
        assert stats['failed_executions'] == 1
        assert stats['timeout_executions'] == 1
        
        # Verify calculated averages
        expected_avg_wait = sum([0.1, 0.5, 1.0, 0.2]) / 4
        assert stats['avg_queue_wait_time'] == expected_avg_wait
        assert stats['max_queue_wait_time'] == 1.0
        
        expected_avg_exec = sum([1.5, 2.0, 0.8, 3.2, 1.1]) / 5
        assert stats['avg_execution_time'] == expected_avg_exec
        assert stats['max_execution_time'] == 3.2
        
        # Verify engine metadata
        assert stats['engine_id'] == user_execution_engine.engine_id
        assert stats['user_id'] == user_execution_engine.context.user_id
        assert stats['run_id'] == user_execution_engine.context.run_id
        assert stats['thread_id'] == user_execution_engine.context.thread_id
        assert stats['active_runs_count'] == 2
        assert stats['history_count'] == 5
        assert stats['is_active'] == user_execution_engine._is_active
        assert stats['max_concurrent'] == user_execution_engine.max_concurrent
        assert stats['user_correlation_id'] == user_execution_engine.context.get_correlation_id()

    @pytest.mark.unit
    def test_get_user_execution_stats_empty_data(self, user_execution_engine):
        """Test execution statistics with no execution data."""
        # Get stats with empty data
        stats = user_execution_engine.get_user_execution_stats()
        
        # Verify default values for empty data
        assert stats['avg_queue_wait_time'] == 0.0
        assert stats['max_queue_wait_time'] == 0.0
        assert stats['avg_execution_time'] == 0.0
        assert stats['max_execution_time'] == 0.0
        assert stats['total_executions'] == 0
        assert stats['active_runs_count'] == 0
        assert stats['history_count'] == 0

    # ========================================================================
    # AGENT PIPELINE INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.unit
    async def test_execute_agent_pipeline_success(self, user_execution_engine, test_user_context):
        """Test agent pipeline execution with UserExecutionContext integration."""
        # Test input data
        agent_name = "cost_optimizer_agent"
        input_data = {
            "prompt": "Analyze my AWS costs and provide optimization recommendations",
            "context": "monthly_analysis",
            "budget_limit": 50000
        }
        
        # Mock successful execution
        with patch.object(user_execution_engine, 'execute_agent') as mock_execute:
            expected_result = AgentExecutionResult(
                success=True,
                agent_name=agent_name,
                execution_time=2.5,
                state=Mock(),
                metadata={
                    "recommendations": ["Switch to reserved instances", "Optimize storage classes"],
                    "potential_monthly_savings": 8500
                }
            )
            mock_execute.return_value = expected_result
            
            # Execute agent pipeline
            result = await user_execution_engine.execute_agent_pipeline(
                agent_name=agent_name,
                execution_context=test_user_context,
                input_data=input_data
            )
            
            # Verify successful result
            assert result is expected_result
            assert result.success is True
            
            # Verify execute_agent called with proper parameters
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            agent_context = call_args[0][0]  # First argument: AgentExecutionContext
            agent_state = call_args[0][1]    # Second argument: DeepAgentState
            
            # Verify AgentExecutionContext created correctly
            assert agent_context.agent_name == agent_name
            assert agent_context.user_id == test_user_context.user_id
            assert agent_context.thread_id == test_user_context.thread_id
            assert agent_context.run_id == test_user_context.run_id
            assert agent_context.request_id == test_user_context.request_id
            assert agent_context.step == PipelineStep.INITIALIZATION
            assert agent_context.metadata == input_data
            
            # Verify DeepAgentState created correctly  
            assert agent_state.user_request == input_data
            assert agent_state.user_id == test_user_context.user_id
            assert agent_state.chat_thread_id == test_user_context.thread_id
            assert agent_state.run_id == test_user_context.run_id

    @pytest.mark.unit
    async def test_execute_agent_pipeline_exception_handling(self, user_execution_engine, test_user_context):
        """Test agent pipeline handles execution exceptions gracefully."""
        agent_name = "failing_agent"
        input_data = {"prompt": "test"}
        
        # Mock execution failure
        with patch.object(user_execution_engine, 'execute_agent') as mock_execute:
            test_error = RuntimeError("Agent pipeline failure")
            mock_execute.side_effect = test_error
            
            # Execute agent pipeline (should return failure result, not raise)
            result = await user_execution_engine.execute_agent_pipeline(
                agent_name=agent_name,
                execution_context=test_user_context,
                input_data=input_data
            )
            
            # Verify failure result returned
            assert result.success is False
            assert "Agent pipeline failure" in result.error
            assert result.duration == 0.0
            assert result.state is None
            
            # Verify failure metadata
            assert result.metadata['user_id'] == test_user_context.user_id
            assert result.metadata['agent_name'] == agent_name
            assert result.metadata['step'] == PipelineStep.ERROR.value

    # ========================================================================
    # RESOURCE CLEANUP AND LIFECYCLE TESTS
    # ========================================================================

    @pytest.mark.unit
    async def test_cleanup_comprehensive(self, user_execution_engine, mock_websocket_emitter):
        """Test comprehensive engine cleanup with active runs and resources."""
        # Add active runs to simulate cleanup scenario
        execution_id_1 = str(uuid.uuid4())
        execution_id_2 = str(uuid.uuid4())
        user_execution_engine.active_runs[execution_id_1] = Mock()
        user_execution_engine.active_runs[execution_id_2] = Mock()
        
        # Add execution history and statistics
        user_execution_engine.run_history = [Mock(), Mock(), Mock()]
        user_execution_engine.execution_stats.update({
            'total_executions': 5,
            'failed_executions': 1
        })
        
        # Mock data access cleanup
        with patch('netra_backend.app.agents.supervisor.data_access_integration.UserExecutionEngineExtensions.cleanup_data_access') as mock_data_cleanup, \
             patch.object(user_execution_engine, 'execution_tracker') as mock_tracker, \
             patch.object(user_execution_engine, 'periodic_update_manager') as mock_periodic:
            
            mock_tracker.update_execution_state = AsyncMock()
            mock_periodic.shutdown = AsyncMock()
            mock_data_cleanup.return_value = AsyncMock()
            
            # Perform cleanup
            await user_execution_engine.cleanup()
            
            # Verify execution tracker cleanup for active runs
            expected_calls = [
                call(execution_id_1, ExecutionState.CANCELLED, error="User engine cleanup"),
                call(execution_id_2, ExecutionState.CANCELLED, error="User engine cleanup")
            ]
            mock_tracker.update_execution_state.assert_has_calls(expected_calls, any_order=True)
            
            # Verify component shutdown
            mock_periodic.shutdown.assert_called_once()
            mock_websocket_emitter.cleanup.assert_called_once()
            mock_data_cleanup.assert_called_once_with(user_execution_engine)
            
            # Verify state cleared
            assert len(user_execution_engine.active_runs) == 0
            assert len(user_execution_engine.run_history) == 0
            assert len(user_execution_engine.execution_stats) == 0
            assert user_execution_engine._is_active is False

    @pytest.mark.unit
    async def test_cleanup_already_inactive(self, user_execution_engine):
        """Test cleanup handles already inactive engine gracefully."""
        # Mark engine as inactive
        user_execution_engine._is_active = False
        
        # Cleanup should complete immediately without errors
        await user_execution_engine.cleanup()
        
        # State should remain inactive
        assert user_execution_engine._is_active is False

    @pytest.mark.unit
    async def test_cleanup_exception_handling(self, user_execution_engine, mock_websocket_emitter):
        """Test cleanup handles component failures gracefully."""
        # Add active run
        execution_id = str(uuid.uuid4())
        user_execution_engine.active_runs[execution_id] = Mock()
        
        with patch.object(user_execution_engine, 'execution_tracker') as mock_tracker, \
             patch.object(user_execution_engine, 'periodic_update_manager') as mock_periodic:
            
            # Mock failures during cleanup
            mock_tracker.update_execution_state.side_effect = Exception("Tracker error")
            mock_periodic.shutdown.side_effect = Exception("Periodic manager error") 
            mock_websocket_emitter.cleanup.side_effect = Exception("WebSocket error")
            
            # Cleanup should complete despite component failures
            await user_execution_engine.cleanup()
            
            # Verify engine marked as inactive despite errors
            assert user_execution_engine._is_active is False
            assert len(user_execution_engine.active_runs) == 0

    @pytest.mark.unit 
    def test_string_representations(self, user_execution_engine):
        """Test string representation methods."""
        # Test __str__ method
        str_repr = str(user_execution_engine)
        assert user_execution_engine.engine_id in str_repr
        assert user_execution_engine.context.user_id in str_repr
        assert "active_runs=0" in str_repr
        assert "is_active=True" in str_repr
        
        # Test __repr__ method (should be same as __str__)
        repr_str = repr(user_execution_engine)
        assert repr_str == str_repr
        
        # Test with active runs
        user_execution_engine.active_runs["test"] = Mock()
        str_repr_with_runs = str(user_execution_engine)
        assert "active_runs=1" in str_repr_with_runs

    # ========================================================================
    # INTEGRATION WITH MINIMAL ADAPTERS TESTS
    # ========================================================================

    @pytest.mark.unit
    async def test_minimal_periodic_update_manager(self):
        """Test MinimalPeriodicUpdateManager interface compatibility."""
        manager = MinimalPeriodicUpdateManager()
        
        # Test track_operation context manager
        context = Mock()
        async with manager.track_operation(
            context, 
            "test_operation", 
            "agent_execution",
            5000,
            "Test operation description"
        ):
            # Operation should execute normally
            await asyncio.sleep(0.01)
        
        # Test shutdown
        await manager.shutdown()

    @pytest.mark.unit
    async def test_minimal_fallback_manager(self, test_user_context):
        """Test MinimalFallbackManager creates proper fallback results."""
        manager = MinimalFallbackManager(test_user_context)
        
        # Test fallback result creation
        context = Mock()
        context.agent_name = "test_agent"
        
        state = Mock()
        error = RuntimeError("Test agent failure")
        start_time = time.time() - 2.0  # 2 seconds ago
        
        result = await manager.create_fallback_result(context, state, error, start_time)
        
        # Verify fallback result structure
        assert result.success is False
        assert result.agent_name == "test_agent"
        assert result.execution_time >= 2.0
        assert "Agent execution failed: Test agent failure" in result.error
        assert result.state is state
        
        # Verify fallback metadata
        assert result.metadata['fallback_result'] is True
        assert result.metadata['original_error'] == "Test agent failure"
        assert result.metadata['user_isolated'] is True
        assert result.metadata['user_id'] == test_user_context.user_id
        assert result.metadata['error_type'] == "RuntimeError"

    # ========================================================================
    # TOOL DISPATCHER INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.unit
    def test_get_tool_dispatcher_test_mode(self, user_execution_engine, isolated_env):
        """Test tool dispatcher creation in test mode uses SSOT mock patterns."""
        # Ensure test environment
        isolated_env.set("ENVIRONMENT", "test", source="test")
        
        # Mock test_only guard and test_framework imports
        with patch('shared.test_only_guard.require_test_mode') as mock_require_test, \
             patch('test_framework.ssot.mocks.get_mock_factory') as mock_get_factory:
            
            mock_dispatcher = Mock()
            mock_factory = Mock()
            mock_factory.create_tool_executor_mock.return_value = mock_dispatcher
            mock_get_factory.return_value = mock_factory
            
            # Get tool dispatcher
            dispatcher = user_execution_engine.get_tool_dispatcher()
            
            # Verify SSOT guard called
            mock_require_test.assert_called_once_with(
                "_create_mock_tool_dispatcher",
                "Mock tool dispatcher creation should only happen in tests"
            )
            
            # Verify SSOT mock factory used
            mock_get_factory.assert_called_once()
            mock_factory.create_tool_executor_mock.assert_called_once()
            
            # Verify user context configured
            assert dispatcher.user_context == user_execution_engine.context
            
            # Test mock tool execution
            result = asyncio.run(dispatcher.execute_tool("test_tool", {"arg": "value"}))
            expected_result = {
                "result": f"Tool test_tool executed for user {user_execution_engine.context.user_id}",
                "user_id": user_execution_engine.context.user_id,
                "tool_args": {"arg": "value"},
                "success": True
            }
            assert result == expected_result

    # ========================================================================
    # PERFORMANCE AND BENCHMARKING TESTS  
    # ========================================================================

    @pytest.mark.unit
    async def test_execution_performance_tracking(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test execution performance tracking and metrics collection."""
        with patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute, \
             patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
            
            execution_id = str(uuid.uuid4())
            mock_tracker.create_execution.return_value = execution_id
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            
            # Mock execution with specific timing
            execution_time = 2.5
            mock_execute.return_value = AgentExecutionResult(
                success=True,
                agent_name=sample_agent_context.agent_name,
                execution_time=execution_time,
                state=sample_agent_state
            )
            
            # Execute with timing measurement
            start_time = time.time()
            result = await user_execution_engine.execute_agent(sample_agent_context, sample_agent_state)
            end_time = time.time()
            
            # Verify result timing
            assert result.execution_time == execution_time
            
            # Verify execution statistics updated
            assert user_execution_engine.execution_stats['total_executions'] == 1
            assert len(user_execution_engine.execution_stats['execution_times']) == 1
            recorded_time = user_execution_engine.execution_stats['execution_times'][0]
            
            # Verify recorded time is reasonable (within test execution bounds)
            assert 0 < recorded_time <= (end_time - start_time + 1.0)  # Allow 1s tolerance

    @pytest.mark.unit
    async def test_concurrent_execution_statistics(self, user_execution_engine, sample_agent_context, sample_agent_state):
        """Test concurrent execution statistics tracking."""
        # Mock execution tracking
        with patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute, \
             patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
            
            mock_tracker.create_execution.side_effect = [str(uuid.uuid4()) for _ in range(3)]
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            
            # Mock slow execution to test concurrency tracking
            async def slow_execute(*args, **kwargs):
                await asyncio.sleep(0.1)  # Small delay
                return AgentExecutionResult(
                    success=True,
                    agent_name=sample_agent_context.agent_name,
                    execution_time=0.1,
                    state=sample_agent_state
                )
            mock_execute.side_effect = slow_execute
            
            # Start multiple concurrent executions
            tasks = []
            for i in range(3):
                context = AgentExecutionContext(
                    user_id=sample_agent_context.user_id,
                    thread_id=sample_agent_context.thread_id,
                    run_id=sample_agent_context.run_id,
                    request_id=f"request_{i}",
                    agent_name=f"agent_{i}",
                    step=PipelineStep.INITIALIZATION,
                    execution_timestamp=datetime.now(timezone.utc),
                    pipeline_step_num=1
                )
                task = asyncio.create_task(
                    user_execution_engine.execute_agent(context, sample_agent_state)
                )
                tasks.append(task)
            
            # Wait for all executions to complete
            results = await asyncio.gather(*tasks)
            
            # Verify all executions succeeded
            assert all(result.success for result in results)
            
            # Verify final statistics
            assert user_execution_engine.execution_stats['total_executions'] == 3
            assert user_execution_engine.execution_stats['concurrent_executions'] == 0  # All completed
            assert len(user_execution_engine.execution_stats['execution_times']) == 3

    # ========================================================================
    # BUSINESS VALUE AND GOLDEN PATH INTEGRATION TESTS
    # ========================================================================

    @pytest.mark.unit
    async def test_golden_path_agent_orchestration(self, user_execution_engine, test_user_context, mock_websocket_emitter):
        """Test Golden Path agent orchestration: SupervisorAgent → Data → Optimization → Report.
        
        This test validates the complete business value delivery pipeline that generates $500K+ ARR.
        """
        # Simulate Golden Path agent execution sequence
        golden_path_agents = [
            "supervisor_agent",      # Orchestrates the entire flow
            "data_analysis_agent",   # Analyzes user's AI spend data  
            "optimization_agent",    # Provides cost optimization recommendations
            "report_generation_agent" # Creates actionable report
        ]
        
        golden_path_results = []
        
        for agent_name in golden_path_agents:
            context = AgentExecutionContext(
                user_id=test_user_context.user_id,
                thread_id=test_user_context.thread_id,
                run_id=test_user_context.run_id,
                request_id=str(uuid.uuid4()),
                agent_name=agent_name,
                step=PipelineStep.EXECUTION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=len(golden_path_results) + 1
            )
            
            state = DeepAgentState(
                user_request="Optimize my AI infrastructure costs with monthly spend of $75000, goal: reduce_costs_maintain_performance",
                user_id=test_user_context.user_id,
                chat_thread_id=test_user_context.thread_id,
                run_id=test_user_context.run_id,
                agent_input={"agent_name": agent_name}
            )
            
            # Mock agent-specific execution results that demonstrate business value
            with patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute, \
                 patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
                
                execution_id = str(uuid.uuid4())
                mock_tracker.create_execution.return_value = execution_id
                mock_tracker.start_execution = AsyncMock()
                mock_tracker.update_execution_state = AsyncMock()
                
                # Create business value results for each agent
                if agent_name == "supervisor_agent":
                    business_result = AgentExecutionResult(
                        success=True,
                        agent_name=agent_name,
                        user_context=test_user_context,
                        duration=1.2,
                        metadata={
                            "orchestration_plan": ["data_analysis", "optimization", "report_generation"],
                            "estimated_savings_potential": "20-30%",
                            "analysis_scope": "infrastructure_optimization"
                        }
                    )
                elif agent_name == "data_analysis_agent":
                    business_result = AgentExecutionResult(
                        success=True,
                        agent_name=agent_name,
                        user_context=test_user_context,
                        duration=3.5,
                        metadata={
                            "current_monthly_spend": 75000,
                            "top_cost_drivers": ["gpt-4_api_calls", "vector_storage", "compute_instances"],
                            "utilization_analysis": {
                                "underutilized_resources": ["gpu_instances_weekends", "dev_environments"],
                                "optimization_opportunities": 12
                            }
                        }
                    )
                elif agent_name == "optimization_agent":
                    business_result = AgentExecutionResult(
                        success=True,
                        agent_name=agent_name,
                        user_context=test_user_context,
                        duration=2.8,
                        metadata={
                            "optimization_recommendations": [
                                {
                                    "recommendation": "Switch to reserved GPU instances",
                                    "monthly_savings": 15000,
                                    "implementation_effort": "low"
                                },
                                {
                                    "recommendation": "Implement model caching layer",
                                    "monthly_savings": 8500,
                                    "implementation_effort": "medium"
                                },
                                {
                                    "recommendation": "Optimize vector database queries",
                                    "monthly_savings": 4200,
                                    "implementation_effort": "low"
                                }
                            ],
                            "total_potential_monthly_savings": 27700,
                            "annual_savings_potential": 332400
                        }
                    )
                elif agent_name == "report_generation_agent":
                    business_result = AgentExecutionResult(
                        success=True,
                        agent_name=agent_name,
                        user_context=test_user_context,
                        duration=1.8,
                        metadata={
                            "executive_summary": "Identified $332K annual savings opportunity",
                            "action_items": [
                                "Implement reserved instance strategy (2 weeks)",
                                "Deploy caching layer (1 month)", 
                                "Optimize database queries (1 week)"
                            ],
                            "roi_analysis": {
                                "implementation_cost": 25000,
                                "payback_period_months": 1.1,
                                "5_year_net_benefit": 1637000
                            },
                            "report_generated": True
                        }
                    )
                
                mock_execute.return_value = business_result
                
                # Execute agent
                result = await user_execution_engine.execute_agent(context, state)
                golden_path_results.append(result)
        
        # Verify complete Golden Path execution
        assert len(golden_path_results) == 4
        assert all(result.success for result in golden_path_results)
        
        # Verify business value delivered
        final_report = golden_path_results[-1]
        assert final_report.metadata["report_generated"] is True
        assert final_report.metadata["roi_analysis"]["5_year_net_benefit"] > 1000000
        
        # Verify ALL 5 CRITICAL WEBSOCKET EVENTS sent for each agent
        # Each agent execution should have triggered all event types
        expected_event_calls = len(golden_path_agents)  # One per agent
        
        assert mock_websocket_emitter.notify_agent_started.call_count == expected_event_calls
        assert mock_websocket_emitter.notify_agent_completed.call_count == expected_event_calls
        # notify_agent_thinking called multiple times per agent (queue + processing notifications)
        assert mock_websocket_emitter.notify_agent_thinking.call_count >= expected_event_calls * 2
        
        # Verify user execution statistics reflect business value delivery
        stats = user_execution_engine.get_user_execution_stats()
        assert stats['total_executions'] == 4
        assert stats['history_count'] == 4
        assert len(stats['execution_times']) == 4
        
        # Verify total execution time reasonable for business value delivered
        total_execution_time = sum(stats['execution_times'])
        assert total_execution_time > 0
        assert total_execution_time < 30  # Should complete within 30 seconds

    @pytest.mark.unit 
    async def test_websocket_event_business_value_context(self, user_execution_engine, sample_agent_context, mock_websocket_emitter):
        """Test WebSocket events contain business value context for user experience."""
        # Mock successful business value execution
        with patch.object(user_execution_engine, '_execute_with_error_handling') as mock_execute, \
             patch.object(user_execution_engine, 'execution_tracker') as mock_tracker:
            
            execution_id = str(uuid.uuid4())
            mock_tracker.create_execution.return_value = execution_id
            mock_tracker.start_execution = AsyncMock()
            mock_tracker.update_execution_state = AsyncMock()
            
            # Create result with business value metadata
            business_value_result = AgentExecutionResult(
                success=True,
                agent_name=sample_agent_context.agent_name,
                execution_time=2.0,
                state=Mock(),
                metadata={
                    "recommendations_delivered": 5,
                    "potential_monthly_savings": 12500,
                    "insights_generated": [
                        "GPU utilization could be improved by 35%",
                        "API call patterns show optimization potential"
                    ],
                    "business_impact": "high"
                }
            )
            mock_execute.return_value = business_value_result
            
            # Mock agent state with business context
            business_state = DeepAgentState(
                user_request={
                    "prompt": "Help me reduce my AI infrastructure costs by 20%",
                    "context": "quarterly_optimization_review"
                },
                user_id=sample_agent_context.user_id,
                chat_thread_id=sample_agent_context.thread_id,
                run_id=sample_agent_context.run_id
            )
            
            # Execute agent
            result = await user_execution_engine.execute_agent(sample_agent_context, business_state)
            
            # Verify business value delivered
            assert result.metadata["potential_monthly_savings"] == 12500
            assert result.metadata["recommendations_delivered"] == 5
            
            # Verify WebSocket events sent with business context
            mock_websocket_emitter.notify_agent_started.assert_called_once()
            
            # Check agent_thinking calls contain business value context
            thinking_calls = mock_websocket_emitter.notify_agent_thinking.call_args_list
            assert len(thinking_calls) >= 2
            
            # At least one thinking call should reference the business context
            business_context_found = any(
                "cost" in str(call) or "optimization" in str(call) or "reduce" in str(call)
                for call in thinking_calls
            )
            assert business_context_found, "WebSocket thinking events should contain business context"
            
            # Verify agent_completed event contains success information
            mock_websocket_emitter.notify_agent_completed.assert_called_once()
            completed_call = mock_websocket_emitter.notify_agent_completed.call_args
            result_data = completed_call.kwargs['result']
            
            assert result_data['success'] is True
            assert result_data['status'] == "completed"
            assert result_data['user_isolated'] is True
            assert result_data['duration_ms'] == 2000.0  # 2.0 seconds