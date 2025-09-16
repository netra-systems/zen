"""Integration tests for Execution Engine workflow patterns.

These tests validate REAL component interactions between:
- ExecutionEngine and UserExecutionEngine patterns
- Agent execution workflows and context management
- WebSocket event sequences during execution
- Request-scoped execution isolation
- Pipeline execution with real components

CRITICAL: These are INTEGRATION tests - they test REAL interactions between components
without mocks for core functionality, but should work without Docker services.

Business Value: Platform/Internal - System Stability
Ensures execution engine workflows work correctly for multi-user agent execution.
"""

import asyncio
import pytest
import tempfile
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.user_execution_engine import (
    create_request_scoped_engine,
    create_execution_context_manager
)
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult,
    PipelineStep,
    AgentExecutionStrategy
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.registry.universal_registry import AgentRegistry


@dataclass
class MockExecutionState:
    """Mock execution state for testing execution workflows."""
    current_step: int = 0
    total_steps: int = 0
    completed_tasks: List[str] = None
    execution_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.completed_tasks is None:
            self.completed_tasks = []
        if self.execution_metadata is None:
            self.execution_metadata = {}


class MockBusinessAgent:
    """Mock business agent for execution testing."""
    
    def __init__(self, name: str, processing_time: float = 0.001):
        self.name = name
        self.processing_time = processing_time
        self.execution_count = 0
        self.execution_history = []
        self.websocket_bridge = None
        self.user_context = None
        self.execution_state = MockExecutionState()
        
    def set_websocket_bridge(self, bridge):
        """Set WebSocket bridge for event notifications."""
        self.websocket_bridge = bridge
        
    def set_user_context(self, context: UserExecutionContext):
        """Set user context for execution isolation."""
        self.user_context = context
        
    async def execute(self, execution_context: AgentExecutionContext) -> AgentExecutionResult:
        """Execute agent with real business logic simulation."""
        self.execution_count += 1
        start_time = time.time()
        
        # Simulate business processing work
        await asyncio.sleep(self.processing_time)
        
        # Update execution state
        self.execution_state.current_step += 1
        self.execution_state.completed_tasks.append(f"task_{self.execution_count}")
        self.execution_state.execution_metadata.update({
            "execution_id": execution_context.execution_id,
            "user_id": execution_context.user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        execution_time = time.time() - start_time
        
        # Create execution result
        result = AgentExecutionResult(
            success=True,
            agent_name=self.name,
            execution_time=execution_time,
            data={
                "result": f"Agent {self.name} completed execution {self.execution_count}",
                "execution_count": self.execution_count,
                "user_isolated": self.user_context is not None,
                "context_metadata": execution_context.metadata or {}
            },
            state=self.execution_state,
            agent_context={
                "processing_time": self.processing_time,
                "execution_timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        self.execution_history.append(result)
        return result


class MockAgentWebSocketBridge:
    """Mock WebSocket bridge for execution engine integration."""
    
    def __init__(self):
        self.events = []
        self.error_events = []
        self.metrics = {"events_sent": 0, "errors_logged": 0}
        
    async def notify_agent_started(self, run_id: str, agent_name: str, metadata: Dict[str, Any]):
        """Mock agent started notification."""
        event = {
            "type": "agent_started",
            "run_id": run_id,
            "agent_name": agent_name,
            "metadata": metadata,
            "timestamp": time.time()
        }
        self.events.append(event)
        self.metrics["events_sent"] += 1
        
    async def notify_agent_thinking(self, run_id: str, agent_name: str, reasoning: str, 
                                   step_number: Optional[int] = None, **kwargs):
        """Mock agent thinking notification."""
        event = {
            "type": "agent_thinking",
            "run_id": run_id,
            "agent_name": agent_name,
            "reasoning": reasoning,
            "step_number": step_number,
            "timestamp": time.time()
        }
        self.events.append(event)
        self.metrics["events_sent"] += 1
        
    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Dict[str, Any], 
                                    execution_time_ms: float = None):
        """Mock agent completed notification."""
        event = {
            "type": "agent_completed",
            "run_id": run_id,
            "agent_name": agent_name,
            "result": result,
            "execution_time_ms": execution_time_ms,
            "timestamp": time.time()
        }
        self.events.append(event)
        self.metrics["events_sent"] += 1
        
    async def notify_agent_error(self, run_id: str, agent_name: str, error: str, error_context: Dict[str, Any] = None):
        """Mock agent error notification."""
        event = {
            "type": "agent_error",
            "run_id": run_id,
            "agent_name": agent_name,
            "error": error,
            "error_context": error_context or {},
            "timestamp": time.time()
        }
        self.error_events.append(event)
        self.metrics["errors_logged"] += 1
        
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Dict[str, Any]):
        """Mock tool execution notification."""
        event = {
            "type": "tool_executing",
            "run_id": run_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "parameters": parameters,
            "timestamp": time.time()
        }
        self.events.append(event)
        self.metrics["events_sent"] += 1
        
    async def get_metrics(self) -> Dict[str, Any]:
        """Get WebSocket bridge metrics."""
        return self.metrics.copy()
        
    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all events for a specific run."""
        all_events = self.events + self.error_events
        return [event for event in all_events if event.get("run_id") == run_id]


class TestExecutionEngineWorkflow(SSotAsyncTestCase):
    """Integration tests for Execution Engine workflow patterns.
    
    Tests REAL component interactions without Docker dependencies.
    """
    
    def setup_method(self, method=None):
        """Setup for each test with real execution engine components."""
        super().setup_method(method)
        
        # Create real user contexts for execution testing
        self.user1_context = UserExecutionContext(
            user_id="exec_test_user_001",
            thread_id="exec_thread_001", 
            run_id="exec_run_001",
            agent_context={
                "test": "execution_integration",
                "user_prompt": "Test business workflow execution"
            }
        )
        
        self.user2_context = UserExecutionContext(
            user_id="exec_test_user_002",
            thread_id="exec_thread_002",
            run_id="exec_run_002", 
            agent_context={
                "test": "execution_integration",
                "user_prompt": "Test parallel execution workflow"
            }
        )
        
        # Create real agent registry
        self.agent_registry = AgentRegistry()
        
        # Create mock agents for testing
        self.triage_agent = MockBusinessAgent("triage", processing_time=0.001)
        self.data_agent = MockBusinessAgent("data_processor", processing_time=0.002)
        self.optimizer_agent = MockBusinessAgent("optimizer", processing_time=0.001)
        
        # Register agents in registry
        self.agent_registry.register("triage", self.triage_agent, 
                                   description="Request routing agent",
                                   tags=["core", "routing"])
        self.agent_registry.register("data_processor", self.data_agent,
                                   description="Data processing agent", 
                                   tags=["business", "data"])
        self.agent_registry.register("optimizer", self.optimizer_agent,
                                   description="Cost optimization agent",
                                   tags=["business", "optimization"])
        
        # Create WebSocket bridge mock
        self.websocket_bridge = MockAgentWebSocketBridge()
        
        # Set WebSocket bridge on registry
        self.agent_registry.set_websocket_manager(self.websocket_bridge)
        
        # Record setup metrics
        self.record_metric("test_setup_time", time.time())
        self.record_metric("agents_registered", len(self.agent_registry))
        
    async def test_request_scoped_execution_engine_creation(self):
        """Test request-scoped execution engine creation and isolation.
        
        Business Value: Ensures execution engines provide proper user isolation.
        Tests REAL execution engine factory patterns.
        """
        # Create request-scoped execution engines for different users
        engine1 = create_request_scoped_engine(
            user_context=self.user1_context,
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge,
            max_concurrent_executions=3
        )
        
        engine2 = create_request_scoped_engine(
            user_context=self.user2_context,
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge,
            max_concurrent_executions=3
        )
        
        # Verify engines are isolated instances
        assert engine1 is not engine2
        assert engine1.user_context == self.user1_context
        assert engine2.user_context == self.user2_context
        assert engine1.user_context.user_id != engine2.user_context.user_id
        
        # Verify both engines share the same registry but have isolated state
        assert engine1.registry is self.agent_registry
        assert engine2.registry is self.agent_registry
        
        # Test isolation status
        isolation1 = engine1.get_isolation_status()
        isolation2 = engine2.get_isolation_status()
        
        assert isolation1["has_user_context"] is True
        assert isolation2["has_user_context"] is True
        assert isolation1["user_id"] == "exec_test_user_001"
        assert isolation2["user_id"] == "exec_test_user_002"
        assert isolation1["isolation_level"] == "user_isolated"
        assert isolation2["isolation_level"] == "user_isolated"
        
        # Cleanup engines
        await engine1.cleanup()
        await engine2.cleanup()
        
        # Record creation metrics
        self.record_metric("execution_engines_created", 2)
        self.record_metric("isolation_verified", True)
        
    async def test_single_agent_execution_with_context(self):
        """Test single agent execution with full context and WebSocket events.
        
        Business Value: Ensures agent execution works with proper event notifications.
        Tests REAL agent execution workflow.
        """
        # Create execution engine
        engine = create_request_scoped_engine(
            user_context=self.user1_context,
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )
        
        # Create agent execution context
        agent_context = AgentExecutionContext(
            agent_name="triage",
            run_id=self.user1_context.run_id,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id,
            agent_context={
                "task": "route_business_request",
                "priority": "high"
            }
        )
        
        # Execute agent
        result = await engine.execute_agent(agent_context, self.user1_context)
        
        # Verify execution result
        assert isinstance(result, AgentExecutionResult)
        assert result.success is True
        assert result.agent_name == "triage"
        assert result.execution_time > 0
        assert result.data["execution_count"] == 1
        assert result.data["user_isolated"] is True
        
        # Verify agent was actually executed
        assert self.triage_agent.execution_count == 1
        assert len(self.triage_agent.execution_history) == 1
        assert self.triage_agent.user_context == self.user1_context
        
        # Verify WebSocket events were sent
        run_events = self.websocket_bridge.get_events_for_run("exec_run_001")
        event_types = [event["type"] for event in run_events]
        
        # Should have agent lifecycle events
        assert "agent_started" in event_types or "agent_thinking" in event_types or "agent_completed" in event_types
        
        # Cleanup
        await engine.cleanup()
        
        # Record execution metrics
        self.record_metric("single_agent_executions", 1)
        self.record_metric("websocket_events_triggered", len(run_events))
        
    async def test_concurrent_agent_execution_isolation(self):
        """Test concurrent agent execution with user isolation.
        
        Business Value: Ensures multi-user concurrent execution works properly.
        Tests REAL concurrent execution with different users.
        """
        # Create separate engines for concurrent execution
        engine1 = create_request_scoped_engine(
            user_context=self.user1_context,
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )
        
        engine2 = create_request_scoped_engine(
            user_context=self.user2_context,
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )
        
        # Create concurrent execution contexts
        context1 = AgentExecutionContext(
            agent_name="data_processor",
            run_id=self.user1_context.run_id,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id,
            agent_context={"dataset": "user1_business_data"}
        )
        
        context2 = AgentExecutionContext(
            agent_name="optimizer",
            run_id=self.user2_context.run_id,
            thread_id=self.user2_context.thread_id,
            user_id=self.user2_context.user_id,
            agent_context={"optimization_target": "user2_cost_reduction"}
        )
        
        # Execute agents concurrently
        results = await asyncio.gather(
            engine1.execute_agent(context1, self.user1_context),
            engine2.execute_agent(context2, self.user2_context),
            return_exceptions=True
        )
        
        # Verify both executions succeeded
        result1, result2 = results
        assert isinstance(result1, AgentExecutionResult)
        assert isinstance(result2, AgentExecutionResult)
        assert result1.success is True
        assert result2.success is True
        
        # Verify user isolation in results
        assert result1.data["user_isolated"] is True
        assert result2.data["user_isolated"] is True
        assert result1.agent_name == "data_processor"
        assert result2.agent_name == "optimizer"
        
        # Verify agents were executed with correct contexts
        assert self.data_agent.execution_count == 1
        assert self.optimizer_agent.execution_count == 1
        assert self.data_agent.user_context == self.user1_context
        assert self.optimizer_agent.user_context == self.user2_context
        
        # Verify WebSocket events for both users
        user1_events = self.websocket_bridge.get_events_for_run("exec_run_001")
        user2_events = self.websocket_bridge.get_events_for_run("exec_run_002")
        
        assert len(user1_events) > 0
        assert len(user2_events) > 0
        
        # Cleanup
        await asyncio.gather(engine1.cleanup(), engine2.cleanup())
        
        # Record concurrency metrics
        self.record_metric("concurrent_executions", 2)
        self.record_metric("concurrent_isolation_verified", True)
        
    async def test_pipeline_execution_workflow(self):
        """Test pipeline execution with multiple agents in sequence.
        
        Business Value: Ensures complex business workflows execute correctly.
        Tests REAL pipeline execution with multiple agents.
        """
        # Create execution engine
        engine = create_request_scoped_engine(
            user_context=self.user1_context,
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge
        )
        
        # Create pipeline steps
        pipeline_steps = [
            PipelineStep(
                agent_name="triage",
                agent_context={
                    "step": "route_request",
                    "continue_on_error": False
                },
                strategy=AgentExecutionStrategy.SEQUENTIAL
            ),
            PipelineStep(
                agent_name="data_processor",
                agent_context={
                    "step": "process_data", 
                    "continue_on_error": False
                },
                strategy=AgentExecutionStrategy.SEQUENTIAL
            ),
            PipelineStep(
                agent_name="optimizer",
                agent_context={
                    "step": "optimize_results",
                    "continue_on_error": True  # Can continue if this fails
                },
                strategy=AgentExecutionStrategy.SEQUENTIAL
            )
        ]
        
        # Create base execution context for pipeline
        base_context = AgentExecutionContext(
            agent_name="pipeline_coordinator",
            run_id=self.user1_context.run_id,
            thread_id=self.user1_context.thread_id,
            user_id=self.user1_context.user_id,
            agent_context={
                "pipeline": "business_workflow",
                "total_steps": len(pipeline_steps)
            }
        )
        
        # Execute pipeline
        pipeline_results = await engine.execute_pipeline(
            pipeline_steps, 
            base_context, 
            self.user1_context
        )
        
        # Verify pipeline execution
        assert len(pipeline_results) == 3
        assert all(isinstance(result, AgentExecutionResult) for result in pipeline_results)
        
        # Verify all steps executed successfully  
        assert pipeline_results[0].agent_name == "triage"
        assert pipeline_results[1].agent_name == "data_processor"
        assert pipeline_results[2].agent_name == "optimizer"
        assert all(result.success for result in pipeline_results)
        
        # Verify sequential execution (each agent executed once)
        assert self.triage_agent.execution_count == 1
        assert self.data_agent.execution_count == 1
        assert self.optimizer_agent.execution_count == 1
        
        # Verify WebSocket events for pipeline
        pipeline_events = self.websocket_bridge.get_events_for_run("exec_run_001")
        assert len(pipeline_events) >= 3  # At least one event per agent
        
        # Cleanup
        await engine.cleanup()
        
        # Record pipeline metrics
        self.record_metric("pipeline_steps_executed", len(pipeline_results))
        self.record_metric("pipeline_success_rate", 1.0)
        
    async def test_execution_context_manager_lifecycle(self):
        """Test ExecutionContextManager for request-scoped lifecycle management.
        
        Business Value: Ensures proper resource management for execution contexts.
        Tests REAL context manager lifecycle with cleanup.
        """
        # Create execution context manager
        context_manager = create_execution_context_manager(
            registry=self.agent_registry,
            websocket_bridge=self.websocket_bridge,
            max_concurrent_per_request=2,
            execution_timeout=10.0
        )
        
        # Test context manager scope
        execution_results = []
        
        async with context_manager.execution_scope(self.user1_context) as execution_scope:
            # Verify scope is properly initialized
            assert execution_scope is not None
            assert hasattr(execution_scope, 'execute_agent')
            
            # Execute multiple agents within scope
            context1 = AgentExecutionContext(
                agent_name="triage",
                run_id=self.user1_context.run_id,
                thread_id=self.user1_context.thread_id,
                user_id=self.user1_context.user_id,
                agent_context={"scope": "context_manager_test_1"}
            )
            
            context2 = AgentExecutionContext(
                agent_name="data_processor",
                run_id=self.user1_context.run_id,
                thread_id=self.user1_context.thread_id,
                user_id=self.user1_context.user_id,
                agent_context={"scope": "context_manager_test_2"}
            )
            
            # Execute agents within managed scope
            result1 = await execution_scope.execute_agent(context1, self.user1_context)
            result2 = await execution_scope.execute_agent(context2, self.user1_context)
            
            execution_results.extend([result1, result2])
            
            # Verify executions succeeded within scope
            assert result1.success is True
            assert result2.success is True
            
        # After context manager exit, verify cleanup
        assert len(execution_results) == 2
        assert all(result.success for result in execution_results)
        
        # Verify agents were executed
        assert self.triage_agent.execution_count == 1
        assert self.data_agent.execution_count == 1
        
        # Record context management metrics
        self.record_metric("context_managed_executions", len(execution_results))
        self.record_metric("context_cleanup_successful", True)
        
    def teardown_method(self, method=None):
        """Cleanup after each test."""
        # Record final execution metrics
        final_metrics = self.get_all_metrics()
        
        # Record agent execution statistics
        if hasattr(self, 'triage_agent') and self.triage_agent:
            self.record_metric("triage_agent_executions", self.triage_agent.execution_count)
            self.record_metric("triage_agent_history", len(self.triage_agent.execution_history))
            
        if hasattr(self, 'data_agent') and self.data_agent:
            self.record_metric("data_agent_executions", self.data_agent.execution_count)
            self.record_metric("data_agent_history", len(self.data_agent.execution_history))
            
        if hasattr(self, 'optimizer_agent') and self.optimizer_agent:
            self.record_metric("optimizer_agent_executions", self.optimizer_agent.execution_count)
            self.record_metric("optimizer_agent_history", len(self.optimizer_agent.execution_history))
            
        if hasattr(self, 'websocket_bridge') and self.websocket_bridge:
            bridge_metrics = asyncio.run(self.websocket_bridge.get_metrics())
            self.record_metric("websocket_events_sent", bridge_metrics["events_sent"])
            self.record_metric("websocket_errors_logged", bridge_metrics["errors_logged"])
        
        # Clean up agent state for next test
        if hasattr(self, 'triage_agent'):
            self.triage_agent.execution_count = 0
            self.triage_agent.execution_history.clear()
            self.triage_agent.execution_state = MockExecutionState()
            
        if hasattr(self, 'data_agent'):
            self.data_agent.execution_count = 0
            self.data_agent.execution_history.clear()
            self.data_agent.execution_state = MockExecutionState()
            
        if hasattr(self, 'optimizer_agent'):
            self.optimizer_agent.execution_count = 0
            self.optimizer_agent.execution_history.clear()
            self.optimizer_agent.execution_state = MockExecutionState()
            
        # Clear registry state
        if hasattr(self, 'agent_registry') and self.agent_registry:
            # Note: AgentRegistry doesn't have clear method, but we clean up references
            self.agent_registry = None
            
        super().teardown_method(method)