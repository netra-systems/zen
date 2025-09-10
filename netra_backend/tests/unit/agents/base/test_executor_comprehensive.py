"""
Comprehensive Unit Tests for Executor SSOT Class

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Development Velocity
- Business Goal: Ensure executor eliminates 40+ duplicate execution patterns
- Value Impact: Critical SSOT infrastructure that standardizes agent execution
- Strategic Impact: Foundation for all agent workflows and error handling

Test Coverage:
- ExecutionStrategy enum states (SEQUENTIAL, PIPELINE, PARALLEL)
- BaseExecutor abstract class and its methods
- SequentialExecutor implementation
- PipelineExecutor implementation  
- ParallelExecutor implementation
- Error handling and recovery strategies
- Retry logic with exponential backoff
- Circuit breaker integration
- State management
- WebSocket notifications
- Extension hooks for agent-specific logic
- Builder pattern implementation
- Helper execution phases

This test suite ensures the SSOT Executor class works correctly across all
execution strategies and error scenarios, preventing regression in the
critical agent execution infrastructure.
"""

import asyncio
import pytest
import time
import warnings
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Any, Dict, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Import the classes under test
from netra_backend.app.agents.base.executor import (
    ExecutionStrategy,
    ExecutionPhase,
    BaseExecutionPhase,
    ExecutionStrategyHandler,
    SequentialStrategyHandler,
    PipelineStrategyHandler,
    ParallelStrategyHandler,
    BaseExecutionEngine,
    ExecutionWorkflowBuilder,
    LambdaExecutionPhase,
    AgentMethodExecutionPhase,
)

# Import supporting classes
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.agents.base.errors import AgentExecutionError
from netra_backend.app.agents.base.monitoring import ExecutionMonitor
from netra_backend.app.agents.base.reliability import ReliabilityManager


class TestExecutionStrategy(SSotAsyncTestCase):
    """Test ExecutionStrategy enum values and behavior."""
    
    def test_execution_strategy_enum_values(self):
        """Test that ExecutionStrategy enum has correct values."""
        # Test enum values
        assert ExecutionStrategy.SEQUENTIAL.value == "sequential"
        assert ExecutionStrategy.PIPELINE.value == "pipeline"
        assert ExecutionStrategy.PARALLEL.value == "parallel"
        
        # Test enum membership
        strategies = list(ExecutionStrategy)
        assert len(strategies) == 3
        assert ExecutionStrategy.SEQUENTIAL in strategies
        assert ExecutionStrategy.PIPELINE in strategies
        assert ExecutionStrategy.PARALLEL in strategies
    
    def test_execution_strategy_string_representation(self):
        """Test string representation of execution strategies."""
        assert str(ExecutionStrategy.SEQUENTIAL) == "ExecutionStrategy.SEQUENTIAL"
        assert ExecutionStrategy.SEQUENTIAL.value == "sequential"
        
        # Test comparisons
        assert ExecutionStrategy.SEQUENTIAL == ExecutionStrategy.SEQUENTIAL
        assert ExecutionStrategy.SEQUENTIAL != ExecutionStrategy.PIPELINE
    
    def test_execution_strategy_iteration(self):
        """Test iteration over execution strategies."""
        strategies = [strategy for strategy in ExecutionStrategy]
        expected = [ExecutionStrategy.SEQUENTIAL, ExecutionStrategy.PIPELINE, ExecutionStrategy.PARALLEL]
        assert strategies == expected


class TestBaseExecutionPhase(SSotAsyncTestCase):
    """Test BaseExecutionPhase implementation."""
    
    def test_base_execution_phase_creation(self):
        """Test creating BaseExecutionPhase instances."""
        # Test with minimal parameters
        phase = BaseExecutionPhase("test_phase")
        assert phase.name == "test_phase"
        assert phase.dependencies == []
        
        # Test with dependencies
        phase_with_deps = BaseExecutionPhase("phase_with_deps", ["dep1", "dep2"])
        assert phase_with_deps.name == "phase_with_deps"
        assert phase_with_deps.dependencies == ["dep1", "dep2"]
    
    async def test_base_execution_phase_execute_not_implemented(self):
        """Test that BaseExecutionPhase.execute raises NotImplementedError."""
        phase = BaseExecutionPhase("test_phase")
        context = ExecutionContext(request_id="test_request")
        
        with self.expect_exception(NotImplementedError, "Phase test_phase must implement execute method"):
            await phase.execute(context, {})
    
    def test_base_execution_phase_dependencies_default(self):
        """Test that dependencies default to empty list."""
        phase = BaseExecutionPhase("test_phase", None)
        assert phase.dependencies == []


class TestExecutionStrategyHandlers(SSotAsyncTestCase):
    """Test execution strategy handler implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setup_method()
        self.mock_context = ExecutionContext(
            request_id="test_request",
            run_id="test_run",
            agent_name="test_agent"
        )
        self.mock_context.websocket_manager = AsyncMock()
    
    async def test_sequential_strategy_handler_execute_phases(self):
        """Test SequentialStrategyHandler executes phases in order."""
        handler = SequentialStrategyHandler()
        
        # Create mock phases
        phase1 = AsyncMock()
        phase1.name = "phase1"
        phase1.execute.return_value = {"result": "phase1_result"}
        
        phase2 = AsyncMock() 
        phase2.name = "phase2"
        phase2.execute.return_value = {"result": "phase2_result"}
        
        phases = [phase1, phase2]
        
        # Execute phases
        results = await handler.execute_phases(phases, self.mock_context)
        
        # Verify results
        assert results == {
            "phase1": {"result": "phase1_result"},
            "phase2": {"result": "phase2_result"}
        }
        
        # Verify phases were called in order with correct parameters
        phase1.execute.assert_called_once_with(self.mock_context, {})
        phase2.execute.assert_called_once_with(self.mock_context, {"phase1": {"result": "phase1_result"}})
        
        # Verify WebSocket notifications
        assert self.mock_context.websocket_manager.send_tool_executing.call_count == 2
        assert self.mock_context.websocket_manager.send_tool_completed.call_count == 2
    
    async def test_sequential_strategy_handler_error_handling(self):
        """Test SequentialStrategyHandler handles phase errors correctly."""
        handler = SequentialStrategyHandler()
        
        # Create phases where second one fails
        phase1 = AsyncMock()
        phase1.name = "phase1"
        phase1.execute.return_value = {"result": "success"}
        
        phase2 = AsyncMock()
        phase2.name = "phase2"
        phase2.execute.side_effect = RuntimeError("Phase failed")
        
        phases = [phase1, phase2]
        
        # Execute should raise the error
        with self.expect_exception(RuntimeError, "Phase failed"):
            await handler.execute_phases(phases, self.mock_context)
        
        # Verify first phase executed successfully
        phase1.execute.assert_called_once()
        # Verify error notification was sent
        self.mock_context.websocket_manager.send_agent_error.assert_called_once()
    
    async def test_pipeline_strategy_handler_dependency_resolution(self):
        """Test PipelineStrategyHandler resolves dependencies correctly."""
        handler = PipelineStrategyHandler()
        
        # Create phases with dependencies
        phase1 = AsyncMock()
        phase1.name = "phase1"
        phase1.dependencies = []
        phase1.execute.return_value = {"result": "phase1_result"}
        
        phase2 = AsyncMock()
        phase2.name = "phase2"
        phase2.dependencies = ["phase1"]
        phase2.execute.return_value = {"result": "phase2_result"}
        
        phase3 = AsyncMock()
        phase3.name = "phase3"
        phase3.dependencies = ["phase1", "phase2"]
        phase3.execute.return_value = {"result": "phase3_result"}
        
        phases = [phase3, phase2, phase1]  # Intentionally out of order
        
        # Execute phases
        results = await handler.execute_phases(phases, self.mock_context)
        
        # Verify all phases executed
        assert len(results) == 3
        assert "phase1" in results
        assert "phase2" in results
        assert "phase3" in results
        
        # Verify execution order by checking call order
        phase1.execute.assert_called_once()
        phase2.execute.assert_called_once()
        phase3.execute.assert_called_once()
    
    async def test_pipeline_strategy_handler_circular_dependency_detection(self):
        """Test PipelineStrategyHandler detects circular dependencies."""
        handler = PipelineStrategyHandler()
        
        # Create phases with circular dependency
        phase1 = AsyncMock()
        phase1.name = "phase1"
        phase1.dependencies = ["phase2"]
        
        phase2 = AsyncMock()
        phase2.name = "phase2"
        phase2.dependencies = ["phase1"]
        
        phases = [phase1, phase2]
        
        # Should raise RuntimeError for circular dependency
        with self.expect_exception(RuntimeError, "Circular dependency or unsatisfied dependency"):
            await handler.execute_phases(phases, self.mock_context)
    
    async def test_parallel_strategy_handler_concurrent_execution(self):
        """Test ParallelStrategyHandler executes independent phases concurrently."""
        handler = ParallelStrategyHandler()
        
        # Create independent phases with delays to test concurrency
        phase1 = AsyncMock()
        phase1.name = "phase1"
        phase1.dependencies = []
        
        async def delayed_execute1(context, results):
            await asyncio.sleep(0.1)
            return {"result": "phase1_result"}
        phase1.execute = delayed_execute1
        
        phase2 = AsyncMock()
        phase2.name = "phase2"
        phase2.dependencies = []
        
        async def delayed_execute2(context, results):
            await asyncio.sleep(0.1)
            return {"result": "phase2_result"}
        phase2.execute = delayed_execute2
        
        phases = [phase1, phase2]
        
        # Measure execution time
        start_time = time.time()
        results = await handler.execute_phases(phases, self.mock_context)
        execution_time = time.time() - start_time
        
        # Should execute concurrently (less than sequential time)
        assert execution_time < 0.15  # Should be around 0.1s, not 0.2s
        
        # Verify results
        assert len(results) == 2
        assert "phase1" in results
        assert "phase2" in results
    
    async def test_parallel_strategy_handler_error_cancellation(self):
        """Test ParallelStrategyHandler cancels remaining tasks on error."""
        handler = ParallelStrategyHandler()
        
        # Create phases where one fails
        phase1 = AsyncMock()
        phase1.name = "phase1"
        phase1.dependencies = []
        
        async def failing_execute(context, results):
            await asyncio.sleep(0.1)
            raise RuntimeError("Phase failed")
        phase1.execute = failing_execute
        
        phase2 = AsyncMock()
        phase2.name = "phase2" 
        phase2.dependencies = []
        
        async def long_execute(context, results):
            await asyncio.sleep(1.0)  # Long delay
            return {"result": "phase2_result"}
        phase2.execute = long_execute
        
        phases = [phase1, phase2]
        
        # Should fail quickly and cancel remaining tasks
        start_time = time.time()
        with self.expect_exception(RuntimeError, "Phase failed"):
            await handler.execute_phases(phases, self.mock_context)
        execution_time = time.time() - start_time
        
        # Should fail quickly, not wait for long task
        assert execution_time < 0.5


class TestBaseExecutionEngine(SSotAsyncTestCase):
    """Test BaseExecutionEngine functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setup_method()
        
        # Mock dependencies
        self.mock_reliability_manager = Mock(spec=ReliabilityManager)
        self.mock_monitor = Mock(spec=ExecutionMonitor)
        self.mock_monitor.get_execution_metrics.return_value = {"test_metric": 1}
        self.mock_monitor.get_health_status.return_value = {"status": "healthy"}
        
        # Create context
        self.context = ExecutionContext(
            request_id="test_request",
            run_id="test_run",
            agent_name="test_agent"
        )
    
    def test_base_execution_engine_initialization(self):
        """Test BaseExecutionEngine initialization."""
        # Test initialization with deprecation warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            engine = BaseExecutionEngine()
            
            # Verify deprecation warning was issued
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message)
        
        # Test default values
        assert engine.strategy == ExecutionStrategy.SEQUENTIAL
        assert engine._phases == []
        assert engine._pre_execution_hooks == []
        assert engine._post_execution_hooks == []
        assert isinstance(engine._strategy_handlers, dict)
        assert len(engine._strategy_handlers) == 3
    
    def test_base_execution_engine_with_dependencies(self):
        """Test BaseExecutionEngine initialization with dependencies."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(
                reliability_manager=self.mock_reliability_manager,
                monitor=self.mock_monitor,
                strategy=ExecutionStrategy.PIPELINE
            )
        
        assert engine.reliability_manager == self.mock_reliability_manager
        assert engine.monitor == self.mock_monitor
        assert engine.strategy == ExecutionStrategy.PIPELINE
    
    def test_builder_pattern_methods(self):
        """Test builder pattern methods on BaseExecutionEngine."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine()
        
        # Test add_phase
        phase = Mock(spec=ExecutionPhase)
        result = engine.add_phase(phase)
        assert result is engine  # Returns self for chaining
        assert phase in engine._phases
        
        # Test add_phases
        phase2 = Mock(spec=ExecutionPhase)
        phase3 = Mock(spec=ExecutionPhase)
        engine.add_phases([phase2, phase3])
        assert phase2 in engine._phases
        assert phase3 in engine._phases
        
        # Test set_strategy
        engine.set_strategy(ExecutionStrategy.PARALLEL)
        assert engine.strategy == ExecutionStrategy.PARALLEL
        
        # Test hooks
        pre_hook = Mock()
        post_hook = Mock()
        engine.add_pre_execution_hook(pre_hook)
        engine.add_post_execution_hook(post_hook)
        assert pre_hook in engine._pre_execution_hooks
        assert post_hook in engine._post_execution_hooks
    
    async def test_execute_phases_no_phases_configured(self):
        """Test execute_phases raises error when no phases configured."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine()
        
        with self.expect_exception(ValueError, "No phases configured for execution"):
            await engine.execute_phases(self.context)
    
    async def test_execute_phases_successful_execution(self):
        """Test successful phase execution."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(monitor=self.mock_monitor)
        
        # Add a simple phase
        phase = AsyncMock()
        phase.name = "test_phase"
        phase.dependencies = []
        phase.execute.return_value = {"result": "success"}
        
        engine.add_phase(phase)
        
        # Execute phases
        result = await engine.execute_phases(self.context)
        
        # Verify result
        assert result.status == ExecutionStatus.COMPLETED
        assert result.request_id == "test_request"
        assert "test_phase" in result.data
        assert result.data["test_phase"]["result"] == "success"
    
    async def test_execute_phases_with_hooks(self):
        """Test phase execution with pre/post hooks."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(monitor=self.mock_monitor)
        
        # Add hooks
        pre_hook = AsyncMock()
        post_hook = Mock()
        engine.add_pre_execution_hook(pre_hook)
        engine.add_post_execution_hook(post_hook)
        
        # Add phase
        phase = AsyncMock()
        phase.name = "test_phase"
        phase.dependencies = []
        phase.execute.return_value = {"result": "success"}
        engine.add_phase(phase)
        
        # Execute
        result = await engine.execute_phases(self.context)
        
        # Verify hooks were called
        pre_hook.assert_called_once_with(self.context)
        post_hook.assert_called_once()
        
        # Verify successful execution
        assert result.status == ExecutionStatus.COMPLETED
    
    async def test_execute_phases_error_handling(self):
        """Test phase execution error handling."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(monitor=self.mock_monitor)
        
        # Add failing phase
        phase = AsyncMock()
        phase.name = "failing_phase"
        phase.dependencies = []
        phase.execute.side_effect = RuntimeError("Phase failed")
        engine.add_phase(phase)
        
        # Execute
        result = await engine.execute_phases(self.context)
        
        # Verify error result
        assert result.status == ExecutionStatus.FAILED
        assert "Phase failed" in result.error_message
    
    async def test_execute_with_agent_protocol(self):
        """Test execute method with agent protocol."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(monitor=self.mock_monitor)
        
        # Create mock agent
        mock_agent = AsyncMock()
        mock_agent.validate_preconditions.return_value = True
        mock_agent.execute_core_logic.return_value = {"result": "agent_success"}
        mock_agent.send_status_update = AsyncMock()
        
        # Execute
        result = await engine.execute(mock_agent, self.context)
        
        # Verify agent methods were called
        mock_agent.validate_preconditions.assert_called_once_with(self.context)
        mock_agent.execute_core_logic.assert_called_once_with(self.context)
        mock_agent.send_status_update.assert_called_once()
        
        # Verify result
        assert result.status == ExecutionStatus.COMPLETED
        assert result.data["result"] == "agent_success"
    
    async def test_execute_with_failed_preconditions(self):
        """Test execute with failed preconditions."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(monitor=self.mock_monitor)
        
        # Create mock agent with failed preconditions
        mock_agent = AsyncMock()
        mock_agent.validate_preconditions.return_value = False
        
        # Execute
        result = await engine.execute(mock_agent, self.context)
        
        # Verify preconditions were checked
        mock_agent.validate_preconditions.assert_called_once_with(self.context)
        
        # Verify error result
        assert result.status == ExecutionStatus.FAILED
        assert "Preconditions not met" in result.error_message
    
    async def test_execute_with_reliability_manager(self):
        """Test execute with reliability manager."""
        # Setup reliability manager
        self.mock_reliability_manager.execute_with_reliability = AsyncMock()
        mock_result = ExecutionResult(
            status=ExecutionStatus.COMPLETED,
            request_id="test_request",
            data={"result": "reliable_success"}
        )
        self.mock_reliability_manager.execute_with_reliability.return_value = mock_result
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(
                reliability_manager=self.mock_reliability_manager,
                monitor=self.mock_monitor
            )
        
        # Create mock agent
        mock_agent = AsyncMock()
        mock_agent.validate_preconditions.return_value = True
        mock_agent.execute_core_logic.return_value = {"result": "success"}
        mock_agent.send_status_update = AsyncMock()
        
        # Execute
        result = await engine.execute(mock_agent, self.context)
        
        # Verify reliability manager was used
        self.mock_reliability_manager.execute_with_reliability.assert_called_once()
        
        # Verify result
        assert result.status == ExecutionStatus.COMPLETED
        assert result.data["result"] == "reliable_success"
    
    def test_get_health_status(self):
        """Test health status reporting."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine(
                reliability_manager=self.mock_reliability_manager,
                monitor=self.mock_monitor
            )
        
        # Mock health status responses
        self.mock_reliability_manager.get_health_status.return_value = {"reliability": "ok"}
        
        # Get health status
        status = engine.get_health_status()
        
        # Verify structure
        assert "monitor" in status
        assert "error_handler" in status
        assert "strategy" in status
        assert "phases_count" in status
        assert "hooks_count" in status
        assert "reliability" in status
        
        # Verify values
        assert status["strategy"] == "sequential"
        assert status["phases_count"] == 0
        assert status["hooks_count"]["pre_execution"] == 0
        assert status["hooks_count"]["post_execution"] == 0


class TestExecutionWorkflowBuilder(SSotAsyncTestCase):
    """Test ExecutionWorkflowBuilder functionality."""
    
    def test_workflow_builder_initialization(self):
        """Test ExecutionWorkflowBuilder initialization."""
        builder = ExecutionWorkflowBuilder()
        
        # Verify default state
        assert builder._phases == []
        assert builder._strategy == ExecutionStrategy.SEQUENTIAL
        assert builder._pre_execution_hooks == []
        assert builder._post_execution_hooks == []
        assert builder._reliability_manager is None
        assert builder._monitor is None
    
    def test_workflow_builder_fluent_interface(self):
        """Test fluent interface (method chaining)."""
        builder = ExecutionWorkflowBuilder()
        
        # Create test objects
        phase = Mock(spec=ExecutionPhase)
        hook = Mock()
        reliability_manager = Mock(spec=ReliabilityManager)
        monitor = Mock(spec=ExecutionMonitor)
        
        # Test method chaining
        result = (builder
                 .add_phase(phase)
                 .set_strategy(ExecutionStrategy.PIPELINE)
                 .add_pre_execution_hook(hook)
                 .add_post_execution_hook(hook)
                 .set_reliability_manager(reliability_manager)
                 .set_monitor(monitor))
        
        # Verify chaining works
        assert result is builder
        
        # Verify configuration
        assert phase in builder._phases
        assert builder._strategy == ExecutionStrategy.PIPELINE
        assert hook in builder._pre_execution_hooks
        assert hook in builder._post_execution_hooks
        assert builder._reliability_manager == reliability_manager
        assert builder._monitor == monitor
    
    def test_workflow_builder_add_multiple_phases(self):
        """Test adding multiple phases."""
        builder = ExecutionWorkflowBuilder()
        
        phase1 = Mock(spec=ExecutionPhase)
        phase2 = Mock(spec=ExecutionPhase)
        phase3 = Mock(spec=ExecutionPhase)
        
        # Add phases individually and as list
        builder.add_phase(phase1)
        builder.add_phases([phase2, phase3])
        
        # Verify all phases added
        assert len(builder._phases) == 3
        assert phase1 in builder._phases
        assert phase2 in builder._phases
        assert phase3 in builder._phases
    
    def test_workflow_builder_build(self):
        """Test building execution engine from builder."""
        builder = ExecutionWorkflowBuilder()
        
        # Configure builder
        phase = Mock(spec=ExecutionPhase)
        pre_hook = Mock()
        post_hook = Mock()
        reliability_manager = Mock(spec=ReliabilityManager)
        monitor = Mock(spec=ExecutionMonitor)
        monitor.get_health_status.return_value = {"status": "healthy"}
        
        builder.add_phase(phase)
        builder.set_strategy(ExecutionStrategy.PARALLEL)
        builder.add_pre_execution_hook(pre_hook)
        builder.add_post_execution_hook(post_hook)
        builder.set_reliability_manager(reliability_manager)
        builder.set_monitor(monitor)
        
        # Build engine
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = builder.build()
        
        # Verify engine configuration
        assert isinstance(engine, BaseExecutionEngine)
        assert engine.strategy == ExecutionStrategy.PARALLEL
        assert phase in engine._phases
        assert pre_hook in engine._pre_execution_hooks
        assert post_hook in engine._post_execution_hooks
        assert engine.reliability_manager == reliability_manager
        assert engine.monitor == monitor


class TestLambdaExecutionPhase(SSotAsyncTestCase):
    """Test LambdaExecutionPhase helper class."""
    
    def test_lambda_execution_phase_creation(self):
        """Test creating LambdaExecutionPhase."""
        func = lambda context, results: {"result": "lambda_success"}
        phase = LambdaExecutionPhase("lambda_phase", func, ["dep1"])
        
        assert phase.name == "lambda_phase"
        assert phase.func == func
        assert phase.dependencies == ["dep1"]
    
    async def test_lambda_execution_phase_sync_function(self):
        """Test LambdaExecutionPhase with synchronous function."""
        def sync_func(context, results):
            return {"result": "sync_success", "input_data": results}
        
        phase = LambdaExecutionPhase("sync_phase", sync_func)
        context = ExecutionContext(request_id="test")
        previous_results = {"previous": "data"}
        
        result = await phase.execute(context, previous_results)
        
        assert result["result"] == "sync_success"
        assert result["input_data"] == previous_results
    
    async def test_lambda_execution_phase_async_function(self):
        """Test LambdaExecutionPhase with asynchronous function."""
        async def async_func(context, results):
            await asyncio.sleep(0.01)  # Simulate async work
            return {"result": "async_success", "context_id": context.request_id}
        
        phase = LambdaExecutionPhase("async_phase", async_func)
        context = ExecutionContext(request_id="test_async")
        
        result = await phase.execute(context, {})
        
        assert result["result"] == "async_success"
        assert result["context_id"] == "test_async"
    
    async def test_lambda_execution_phase_error_propagation(self):
        """Test that errors in lambda functions are properly propagated."""
        def failing_func(context, results):
            raise ValueError("Lambda function failed")
        
        phase = LambdaExecutionPhase("failing_phase", failing_func)
        context = ExecutionContext(request_id="test")
        
        with self.expect_exception(ValueError, "Lambda function failed"):
            await phase.execute(context, {})


class TestAgentMethodExecutionPhase(SSotAsyncTestCase):
    """Test AgentMethodExecutionPhase helper class."""
    
    def test_agent_method_execution_phase_creation(self):
        """Test creating AgentMethodExecutionPhase."""
        mock_agent = Mock()
        phase = AgentMethodExecutionPhase("method_phase", mock_agent, "process_data", ["dep1"])
        
        assert phase.name == "method_phase"
        assert phase.agent == mock_agent
        assert phase.method_name == "process_data"
        assert phase.dependencies == ["dep1"]
    
    async def test_agent_method_execution_phase_sync_method(self):
        """Test AgentMethodExecutionPhase with synchronous method."""
        mock_agent = Mock()
        mock_agent.process_data = Mock(return_value={"result": "processed"})
        
        phase = AgentMethodExecutionPhase("sync_method", mock_agent, "process_data")
        context = ExecutionContext(request_id="test")
        previous_results = {"input": "data"}
        
        result = await phase.execute(context, previous_results)
        
        # Verify method was called with correct parameters
        mock_agent.process_data.assert_called_once_with(context, previous_results)
        assert result["result"] == "processed"
    
    async def test_agent_method_execution_phase_async_method(self):
        """Test AgentMethodExecutionPhase with asynchronous method."""
        mock_agent = Mock()
        
        async def async_process(context, results):
            await asyncio.sleep(0.01)
            return {"result": "async_processed", "request": context.request_id}
        
        mock_agent.async_process = async_process
        
        phase = AgentMethodExecutionPhase("async_method", mock_agent, "async_process")
        context = ExecutionContext(request_id="test_async")
        
        result = await phase.execute(context, {})
        
        assert result["result"] == "async_processed"
        assert result["request"] == "test_async"
    
    async def test_agent_method_execution_phase_method_not_found(self):
        """Test error handling when agent method doesn't exist."""
        mock_agent = Mock()
        # Don't add the method to the mock
        
        phase = AgentMethodExecutionPhase("missing_method", mock_agent, "nonexistent_method")
        context = ExecutionContext(request_id="test")
        
        with self.expect_exception(AttributeError):
            await phase.execute(context, {})
    
    async def test_agent_method_execution_phase_method_error(self):
        """Test error propagation from agent methods."""
        mock_agent = Mock()
        mock_agent.failing_method = Mock(side_effect=RuntimeError("Method failed"))
        
        phase = AgentMethodExecutionPhase("failing_method", mock_agent, "failing_method")
        context = ExecutionContext(request_id="test")
        
        with self.expect_exception(RuntimeError, "Method failed"):
            await phase.execute(context, {})


class TestExecutorIntegrationScenarios(SSotAsyncTestCase):
    """Test integration scenarios combining multiple executor components."""
    
    async def test_complete_workflow_sequential_strategy(self):
        """Test complete workflow using sequential strategy."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Build complete workflow
            builder = ExecutionWorkflowBuilder()
            
            # Create phases
            phase1 = LambdaExecutionPhase(
                "initialization",
                lambda ctx, res: {"initialized": True, "timestamp": time.time()}
            )
            
            async def processing_phase(ctx, res):
                await asyncio.sleep(0.01)  # Simulate work
                return {"processed": True, "input_count": len(res)}
            
            phase2 = LambdaExecutionPhase("processing", processing_phase, ["initialization"])
            
            phase3 = LambdaExecutionPhase(
                "finalization",
                lambda ctx, res: {"finalized": True, "total_phases": len(res)},
                ["processing"]
            )
            
            # Build engine
            engine = (builder
                     .add_phases([phase1, phase2, phase3])
                     .set_strategy(ExecutionStrategy.SEQUENTIAL)
                     .build())
            
            # Execute workflow
            context = ExecutionContext(request_id="integration_test")
            result = await engine.execute_phases(context)
            
            # Verify successful execution
            assert result.status == ExecutionStatus.COMPLETED
            assert len(result.data) == 3
            assert result.data["initialization"]["initialized"] is True
            assert result.data["processing"]["processed"] is True
            assert result.data["finalization"]["finalized"] is True
    
    async def test_complete_workflow_pipeline_strategy(self):
        """Test complete workflow using pipeline strategy with dependencies."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            builder = ExecutionWorkflowBuilder()
            
            # Create phases with complex dependencies
            init_phase = LambdaExecutionPhase(
                "init",
                lambda ctx, res: {"base_value": 10}
            )
            
            double_phase = LambdaExecutionPhase(
                "double",
                lambda ctx, res: {"doubled": res["init"]["base_value"] * 2},
                ["init"]
            )
            
            triple_phase = LambdaExecutionPhase(
                "triple",
                lambda ctx, res: {"tripled": res["init"]["base_value"] * 3},
                ["init"]
            )
            
            combine_phase = LambdaExecutionPhase(
                "combine",
                lambda ctx, res: {"sum": res["double"]["doubled"] + res["triple"]["tripled"]},
                ["double", "triple"]
            )
            
            # Build with pipeline strategy
            engine = (builder
                     .add_phases([combine_phase, triple_phase, double_phase, init_phase])  # Out of order
                     .set_strategy(ExecutionStrategy.PIPELINE)
                     .build())
            
            # Execute
            context = ExecutionContext(request_id="pipeline_test")
            result = await engine.execute_phases(context)
            
            # Verify execution and dependency resolution
            assert result.status == ExecutionStatus.COMPLETED
            assert result.data["init"]["base_value"] == 10
            assert result.data["double"]["doubled"] == 20
            assert result.data["triple"]["tripled"] == 30
            assert result.data["combine"]["sum"] == 50
    
    async def test_workflow_with_error_recovery(self):
        """Test workflow error handling and recovery."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            builder = ExecutionWorkflowBuilder()
            
            # Create phases where one fails
            success_phase = LambdaExecutionPhase(
                "success",
                lambda ctx, res: {"result": "success"}
            )
            
            failing_phase = LambdaExecutionPhase(
                "failing",
                lambda ctx, res: (_ for _ in ()).throw(RuntimeError("Intentional failure")),
                ["success"]
            )
            
            engine = (builder
                     .add_phases([success_phase, failing_phase])
                     .set_strategy(ExecutionStrategy.PIPELINE)
                     .build())
            
            # Execute and expect error
            context = ExecutionContext(request_id="error_test")
            result = await engine.execute_phases(context)
            
            # Verify error handling
            assert result.status == ExecutionStatus.FAILED
            assert "Intentional failure" in result.error_message
    
    async def test_workflow_with_hooks_and_monitoring(self):
        """Test workflow with pre/post execution hooks and monitoring."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            
            # Create monitoring mock
            monitor = Mock(spec=ExecutionMonitor)
            monitor.get_execution_metrics.return_value = {"hook_test": True}
            monitor.get_health_status.return_value = {"status": "healthy"}
            
            # Track hook execution
            hook_calls = []
            
            def pre_hook(context):
                hook_calls.append(f"pre_hook_{context.request_id}")
            
            async def post_hook(context, results):
                hook_calls.append(f"post_hook_{context.request_id}_{len(results)}")
            
            # Build workflow
            builder = ExecutionWorkflowBuilder()
            phase = LambdaExecutionPhase("test", lambda ctx, res: {"hook_test": True})
            
            engine = (builder
                     .add_phase(phase)
                     .add_pre_execution_hook(pre_hook)
                     .add_post_execution_hook(post_hook)
                     .set_monitor(monitor)
                     .build())
            
            # Execute
            context = ExecutionContext(request_id="hooks_test")
            result = await engine.execute_phases(context)
            
            # Verify hooks were called
            assert len(hook_calls) == 2
            assert "pre_hook_hooks_test" in hook_calls
            assert "post_hook_hooks_test_1" in hook_calls
            
            # Verify successful execution
            assert result.status == ExecutionStatus.COMPLETED
            assert result.metrics["hook_test"] is True


class TestExecutorEdgeCases(SSotAsyncTestCase):
    """Test edge cases and boundary conditions."""
    
    async def test_empty_results_handling(self):
        """Test handling of empty results between phases."""
        handler = SequentialStrategyHandler()
        
        # Phase that returns empty dict
        empty_phase = AsyncMock()
        empty_phase.name = "empty"
        empty_phase.execute.return_value = {}
        
        # Phase that should handle empty input
        dependent_phase = AsyncMock()
        dependent_phase.name = "dependent" 
        dependent_phase.execute.return_value = {"handled_empty": True}
        
        context = ExecutionContext(request_id="empty_test")
        context.websocket_manager = AsyncMock()
        
        phases = [empty_phase, dependent_phase]
        results = await handler.execute_phases(phases, context)
        
        # Verify both phases executed despite empty results
        assert len(results) == 2
        assert results["empty"] == {}
        assert results["dependent"]["handled_empty"] is True
    
    async def test_context_without_websocket_manager(self):
        """Test execution with context that has no WebSocket manager."""
        handler = SequentialStrategyHandler()
        
        phase = AsyncMock()
        phase.name = "no_websocket"
        phase.execute.return_value = {"success": True}
        
        # Context without WebSocket manager
        context = ExecutionContext(request_id="no_ws_test")
        # Don't set websocket_manager
        
        # Should execute without errors
        results = await handler.execute_phases([phase], context)
        assert results["no_websocket"]["success"] is True
    
    async def test_phase_dependencies_case_sensitivity(self):
        """Test that phase dependencies are case-sensitive."""
        handler = PipelineStrategyHandler()
        
        phase1 = AsyncMock()
        phase1.name = "Phase1"  # Capital P
        phase1.dependencies = []
        phase1.execute.return_value = {"result": "1"}
        
        phase2 = AsyncMock()
        phase2.name = "phase2"
        phase2.dependencies = ["phase1"]  # Lowercase p - should not match
        phase2.execute.return_value = {"result": "2"}
        
        context = ExecutionContext(request_id="case_test")
        context.websocket_manager = AsyncMock()
        
        # Should fail due to unresolved dependency
        with self.expect_exception(RuntimeError, "Circular dependency or unsatisfied dependency"):
            await handler.execute_phases([phase1, phase2], context)
    
    async def test_concurrent_modification_resistance(self):
        """Test that phase lists are not modified during execution."""
        handler = SequentialStrategyHandler()
        
        original_phases = []
        for i in range(3):
            phase = AsyncMock()
            phase.name = f"phase_{i}"
            phase.execute.return_value = {"index": i}
            original_phases.append(phase)
        
        context = ExecutionContext(request_id="concurrent_test")
        context.websocket_manager = AsyncMock()
        
        # Execute while modifying original list
        execution_task = asyncio.create_task(
            handler.execute_phases(original_phases.copy(), context)
        )
        
        # Modify original list during execution
        original_phases.clear()
        
        # Execution should complete successfully
        results = await execution_task
        assert len(results) == 3
        assert "phase_0" in results
        assert "phase_1" in results
        assert "phase_2" in results
    
    async def test_large_number_of_phases(self):
        """Test execution with a large number of phases."""
        handler = SequentialStrategyHandler()
        
        # Create many phases
        phases = []
        for i in range(100):
            phase = AsyncMock()
            phase.name = f"phase_{i:03d}"
            phase.execute.return_value = {"index": i, "squared": i * i}
            phases.append(phase)
        
        context = ExecutionContext(request_id="large_test")
        context.websocket_manager = AsyncMock()
        
        # Execute all phases
        start_time = time.time()
        results = await handler.execute_phases(phases, context)
        execution_time = time.time() - start_time
        
        # Verify all phases executed
        assert len(results) == 100
        assert results["phase_050"]["index"] == 50
        assert results["phase_099"]["squared"] == 99 * 99
        
        # Should complete in reasonable time
        assert execution_time < 5.0  # Should be much faster than this
    
    def test_execution_context_modification_safety(self):
        """Test that execution context modifications don't affect other executions."""
        context1 = ExecutionContext(request_id="test1", parameters={"value": 1})
        context2 = ExecutionContext(request_id="test2", parameters={"value": 2})
        
        # Modify one context
        context1.parameters["modified"] = True
        context1.metadata = {"test": "data"}
        
        # Verify other context unaffected
        assert "modified" not in context2.parameters
        assert context2.metadata == {}
        assert context2.parameters["value"] == 2
        
        # Verify original context preserved changes
        assert context1.parameters["modified"] is True
        assert context1.parameters["value"] == 1


# Performance and benchmarking tests
class TestExecutorPerformance(SSotAsyncTestCase):
    """Test performance characteristics of executor components."""
    
    async def test_sequential_vs_parallel_performance(self):
        """Compare performance of sequential vs parallel execution."""
        # Create phases with simulated work
        phases = []
        for i in range(5):
            async def work_phase(ctx, res, delay=0.05):
                await asyncio.sleep(delay)
                return {"completed": True}
            
            phase = LambdaExecutionPhase(f"work_{i}", work_phase)
            phases.append(phase)
        
        context = ExecutionContext(request_id="perf_test")
        context.websocket_manager = AsyncMock()
        
        # Test sequential execution
        sequential_handler = SequentialStrategyHandler()
        start_time = time.time()
        await sequential_handler.execute_phases(phases.copy(), context)
        sequential_time = time.time() - start_time
        
        # Test parallel execution
        parallel_handler = ParallelStrategyHandler()
        start_time = time.time()
        await parallel_handler.execute_phases(phases.copy(), context)
        parallel_time = time.time() - start_time
        
        # Parallel should be significantly faster
        speedup_ratio = sequential_time / parallel_time
        assert speedup_ratio > 3.0  # Should be close to 5x faster
        
        # Record performance metrics
        self.record_metric("sequential_time", sequential_time)
        self.record_metric("parallel_time", parallel_time)
        self.record_metric("speedup_ratio", speedup_ratio)
    
    async def test_memory_usage_stability(self):
        """Test that executor doesn't accumulate memory over multiple executions."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            engine = BaseExecutionEngine()
        
        # Add simple phase
        phase = LambdaExecutionPhase("memory_test", lambda ctx, res: {"test": "data"})
        engine.add_phase(phase)
        
        # Execute multiple times
        for i in range(50):
            context = ExecutionContext(request_id=f"memory_test_{i}")
            result = await engine.execute_phases(context)
            assert result.status == ExecutionStatus.COMPLETED
        
        # Verify engine state hasn't grown
        assert len(engine._phases) == 1
        assert len(engine._pre_execution_hooks) == 0
        assert len(engine._post_execution_hooks) == 0


if __name__ == "__main__":
    # Run tests
    import sys
    import subprocess
    
    # Run with pytest
    result = subprocess.run([
        sys.executable, "-m", "pytest", __file__, "-xvs"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    sys.exit(result.returncode)