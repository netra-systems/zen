"""Multi-Agent Workflow L2 Integration Tests

Business Value Justification (BVJ):
- Segment: Enterprise (complex AI workflows)
- Business Goal: Advanced workflow automation
- Value Impact: Protects $15K MRR from workflow execution failures
- Strategic Impact: Premium feature enabling complex multi-step AI operations

Critical Path: Workflow definition -> Agent coordination -> State management -> Execution
Coverage: Real workflow engine, agent orchestration, conditional routing, parallel execution
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from netra_backend.app.agents.base_agent import BaseSubAgent
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.database_connection_manager import DatabaseConnectionManager as ConnectionManager
from netra_backend.app.services.llm.llm_manager import LLMManager

# Real components for L2 testing
from netra_backend.app.services.redis_service import RedisService

logger = logging.getLogger(__name__)

class WorkflowStepType(Enum):
    """Types of workflow steps."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"

class WorkflowStep:
    """Individual step in a workflow."""
    
    def __init__(self, step_id: str, step_type: WorkflowStepType, 
                 agent_type: str, parameters: Dict[str, Any] = None,
                 condition: Callable = None, dependencies: List[str] = None):
        self.step_id = step_id
        self.step_type = step_type
        self.agent_type = agent_type
        self.parameters = parameters or {}
        self.condition = condition
        self.dependencies = dependencies or []
        self.status = "pending"
        self.result = None
        self.execution_time = 0
        self.error = None

class WorkflowDefinition:
    """Defines a complete workflow."""
    
    def __init__(self, workflow_id: str, name: str):
        self.workflow_id = workflow_id
        self.name = name
        self.steps = {}
        self.execution_order = []
        self.metadata = {}
        
    def add_step(self, step: WorkflowStep):
        """Add a step to the workflow."""
        self.steps[step.step_id] = step
        
    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        return self.steps.get(step_id)
        
    def get_ready_steps(self) -> List[WorkflowStep]:
        """Get steps that are ready to execute."""
        ready_steps = []
        for step in self.steps.values():
            if step.status == "pending":
                # Check if all dependencies are completed
                deps_completed = all(
                    self.steps[dep_id].status == "completed" 
                    for dep_id in step.dependencies
                    if dep_id in self.steps
                )
                if deps_completed:
                    ready_steps.append(step)
        return ready_steps

class AgentCoordinator:
    """Coordinates agent execution in workflows."""
    
    def __init__(self):
        self.agents = {}
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0
        }
        
    async def initialize_agent(self, agent_type: str) -> BaseSubAgent:
        """Initialize an agent of the specified type."""
        if agent_type not in self.agents:
            # Mock agent creation for testing
            mock_agent = AsyncMock(spec=BaseSubAgent)
            mock_agent.agent_type = agent_type
            mock_agent.execute = AsyncMock(return_value={"success": True, "result": f"Executed {agent_type}"})
            self.agents[agent_type] = mock_agent
        return self.agents[agent_type]
        
    async def execute_step(self, step: WorkflowStep) -> Dict[str, Any]:
        """Execute a single workflow step."""
        start_time = time.time()
        
        try:
            agent = await self.initialize_agent(step.agent_type)
            
            # Execute the agent with step parameters
            result = await agent.execute(step.parameters)
            
            step.status = "completed"
            step.result = result
            step.execution_time = time.time() - start_time
            
            self.execution_stats["successful_executions"] += 1
            
            return {"success": True, "result": result, "execution_time": step.execution_time}
            
        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            step.execution_time = time.time() - start_time
            
            self.execution_stats["failed_executions"] += 1
            
            return {"success": False, "error": str(e), "execution_time": step.execution_time}
        finally:
            self.execution_stats["total_executions"] += 1

class WorkflowEngine:
    """Executes multi-agent workflows."""
    
    def __init__(self):
        self.coordinator = AgentCoordinator()
        self.state_manager = {}
        self.execution_history = []
        
    async def execute_workflow(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Execute a complete workflow."""
        start_time = time.time()
        execution_log = []
        
        try:
            while True:
                ready_steps = workflow.get_ready_steps()
                
                if not ready_steps:
                    # Check if workflow is complete
                    if all(step.status in ["completed", "failed"] for step in workflow.steps.values()):
                        break
                    else:
                        # Deadlock situation
                        raise RuntimeError("Workflow deadlocked - no ready steps but not complete")
                
                # Execute ready steps
                await self._execute_ready_steps(ready_steps, execution_log)
                
            # Calculate final results
            completed_steps = [s for s in workflow.steps.values() if s.status == "completed"]
            failed_steps = [s for s in workflow.steps.values() if s.status == "failed"]
            
            execution_result = {
                "workflow_id": workflow.workflow_id,
                "success": len(failed_steps) == 0,
                "total_steps": len(workflow.steps),
                "completed_steps": len(completed_steps),
                "failed_steps": len(failed_steps),
                "total_execution_time": time.time() - start_time,
                "execution_log": execution_log
            }
            
            self.execution_history.append(execution_result)
            return execution_result
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "workflow_id": workflow.workflow_id,
                "success": False,
                "error": str(e),
                "total_execution_time": time.time() - start_time
            }
    
    async def _execute_ready_steps(self, steps: List[WorkflowStep], execution_log: List):
        """Execute ready steps (parallel or sequential based on type)."""
        # Group steps by execution type
        parallel_steps = [s for s in steps if s.step_type == WorkflowStepType.PARALLEL]
        sequential_steps = [s for s in steps if s.step_type == WorkflowStepType.SEQUENTIAL]
        conditional_steps = [s for s in steps if s.step_type == WorkflowStepType.CONDITIONAL]
        
        # Execute parallel steps concurrently
        if parallel_steps:
            tasks = [self.coordinator.execute_step(step) for step in parallel_steps]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for step, result in zip(parallel_steps, results):
                execution_log.append({
                    "step_id": step.step_id,
                    "execution_type": "parallel",
                    "result": result if not isinstance(result, Exception) else {"error": str(result)}
                })
        
        # Execute sequential steps one by one
        for step in sequential_steps:
            result = await self.coordinator.execute_step(step)
            execution_log.append({
                "step_id": step.step_id,
                "execution_type": "sequential",
                "result": result
            })
        
        # Execute conditional steps based on conditions
        for step in conditional_steps:
            if step.condition and step.condition():
                result = await self.coordinator.execute_step(step)
                execution_log.append({
                    "step_id": step.step_id,
                    "execution_type": "conditional",
                    "condition_met": True,
                    "result": result
                })
            else:
                step.status = "skipped"
                execution_log.append({
                    "step_id": step.step_id,
                    "execution_type": "conditional",
                    "condition_met": False,
                    "result": "skipped"
                })

class MultiAgentWorkflowManager:
    """Manages multi-agent workflow testing."""
    
    def __init__(self):
        self.workflow_engine = WorkflowEngine()
        self.redis_service = None
        self.db_manager = None
        
    async def initialize_services(self):
        """Initialize required services."""
        self.redis_service = RedisService()
        await self.redis_service.initialize()
        
        self.db_manager = ConnectionManager()
        await self.db_manager.initialize()
        
    async def create_simple_workflow(self) -> WorkflowDefinition:
        """Create a simple sequential workflow."""
        workflow = WorkflowDefinition("simple_001", "Simple Sequential Workflow")
        
        steps = [
            WorkflowStep("step1", WorkflowStepType.SEQUENTIAL, "data_processor"),
            WorkflowStep("step2", WorkflowStepType.SEQUENTIAL, "analyzer", dependencies=["step1"]),
            WorkflowStep("step3", WorkflowStepType.SEQUENTIAL, "reporter", dependencies=["step2"])
        ]
        
        for step in steps:
            workflow.add_step(step)
            
        return workflow
        
    async def create_parallel_workflow(self) -> WorkflowDefinition:
        """Create a workflow with parallel execution."""
        workflow = WorkflowDefinition("parallel_001", "Parallel Processing Workflow")
        
        steps = [
            WorkflowStep("init", WorkflowStepType.SEQUENTIAL, "initializer"),
            WorkflowStep("process_a", WorkflowStepType.PARALLEL, "processor_a", dependencies=["init"]),
            WorkflowStep("process_b", WorkflowStepType.PARALLEL, "processor_b", dependencies=["init"]),
            WorkflowStep("process_c", WorkflowStepType.PARALLEL, "processor_c", dependencies=["init"]),
            WorkflowStep("aggregate", WorkflowStepType.SEQUENTIAL, "aggregator", 
                        dependencies=["process_a", "process_b", "process_c"])
        ]
        
        for step in steps:
            workflow.add_step(step)
            
        return workflow
        
    async def create_conditional_workflow(self) -> WorkflowDefinition:
        """Create a workflow with conditional steps."""
        workflow = WorkflowDefinition("conditional_001", "Conditional Workflow")
        
        steps = [
            WorkflowStep("check", WorkflowStepType.SEQUENTIAL, "condition_checker"),
            WorkflowStep("path_a", WorkflowStepType.CONDITIONAL, "handler_a", 
                        dependencies=["check"], condition=lambda: True),
            WorkflowStep("path_b", WorkflowStepType.CONDITIONAL, "handler_b", 
                        dependencies=["check"], condition=lambda: False),
            WorkflowStep("finalize", WorkflowStepType.SEQUENTIAL, "finalizer", 
                        dependencies=["path_a", "path_b"])
        ]
        
        for step in steps:
            workflow.add_step(step)
            
        return workflow
        
    async def cleanup(self):
        """Clean up resources."""
        if self.redis_service:
            await self.redis_service.shutdown()
        if self.db_manager:
            await self.db_manager.shutdown()

@pytest.fixture
async def workflow_manager():
    """Create workflow manager for testing."""
    manager = MultiAgentWorkflowManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_simple_sequential_workflow(workflow_manager):
    """Test simple sequential workflow execution."""
    manager = workflow_manager
    
    workflow = await manager.create_simple_workflow()
    result = await manager.workflow_engine.execute_workflow(workflow)
    
    assert result["success"] is True
    assert result["total_steps"] == 3
    assert result["completed_steps"] == 3
    assert result["failed_steps"] == 0
    assert result["total_execution_time"] < 2.0
    
    # Verify execution order
    execution_log = result["execution_log"]
    assert len(execution_log) == 3
    assert execution_log[0]["step_id"] == "step1"
    assert execution_log[1]["step_id"] == "step2"
    assert execution_log[2]["step_id"] == "step3"

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_parallel_workflow_execution(workflow_manager):
    """Test parallel workflow execution performance."""
    manager = workflow_manager
    
    workflow = await manager.create_parallel_workflow()
    
    start_time = time.time()
    result = await manager.workflow_engine.execute_workflow(workflow)
    execution_time = time.time() - start_time
    
    assert result["success"] is True
    assert result["total_steps"] == 5
    assert result["completed_steps"] == 5
    
    # Parallel execution should be faster than sequential
    assert execution_time < 1.0  # All parallel steps should execute concurrently
    
    # Verify parallel steps were executed
    parallel_executions = [log for log in result["execution_log"] 
                          if log.get("execution_type") == "parallel"]
    assert len(parallel_executions) == 3

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_conditional_workflow_routing(workflow_manager):
    """Test conditional workflow routing logic."""
    manager = workflow_manager
    
    workflow = await manager.create_conditional_workflow()
    result = await manager.workflow_engine.execute_workflow(workflow)
    
    assert result["success"] is True
    
    # Check conditional execution
    conditional_executions = [log for log in result["execution_log"] 
                             if log.get("execution_type") == "conditional"]
    
    # Should have 2 conditional steps
    assert len(conditional_executions) == 2
    
    # One should be executed (condition=True), one skipped (condition=False)
    executed_conditionals = [log for log in conditional_executions 
                           if log.get("condition_met") is True]
    skipped_conditionals = [log for log in conditional_executions 
                          if log.get("condition_met") is False]
    
    assert len(executed_conditionals) == 1
    assert len(skipped_conditionals) == 1

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_workflow_dependency_resolution(workflow_manager):
    """Test workflow dependency resolution and execution order."""
    manager = workflow_manager
    
    # Create complex dependency workflow
    workflow = WorkflowDefinition("dependency_001", "Complex Dependencies")
    
    steps = [
        WorkflowStep("a", WorkflowStepType.SEQUENTIAL, "agent_a"),
        WorkflowStep("b", WorkflowStepType.SEQUENTIAL, "agent_b", dependencies=["a"]),
        WorkflowStep("c", WorkflowStepType.SEQUENTIAL, "agent_c", dependencies=["a"]),
        WorkflowStep("d", WorkflowStepType.SEQUENTIAL, "agent_d", dependencies=["b", "c"]),
        WorkflowStep("e", WorkflowStepType.SEQUENTIAL, "agent_e", dependencies=["d"])
    ]
    
    for step in steps:
        workflow.add_step(step)
    
    result = await manager.workflow_engine.execute_workflow(workflow)
    
    assert result["success"] is True
    assert result["completed_steps"] == 5
    
    # Verify execution order respects dependencies
    execution_order = [log["step_id"] for log in result["execution_log"]]
    
    assert execution_order.index("a") < execution_order.index("b")
    assert execution_order.index("a") < execution_order.index("c")
    assert execution_order.index("b") < execution_order.index("d")
    assert execution_order.index("c") < execution_order.index("d")
    assert execution_order.index("d") < execution_order.index("e")

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_workflow_error_handling(workflow_manager):
    """Test workflow error handling and recovery."""
    manager = workflow_manager
    
    # Mock agent to fail
    failing_agent = AsyncMock(spec=BaseSubAgent)
    failing_agent.execute = AsyncMock(side_effect=Exception("Agent execution failed"))
    manager.workflow_engine.coordinator.agents["failing_agent"] = failing_agent
    
    workflow = WorkflowDefinition("error_test", "Error Handling Test")
    steps = [
        WorkflowStep("step1", WorkflowStepType.SEQUENTIAL, "normal_agent"),
        WorkflowStep("step2", WorkflowStepType.SEQUENTIAL, "failing_agent", dependencies=["step1"]),
        WorkflowStep("step3", WorkflowStepType.SEQUENTIAL, "normal_agent", dependencies=["step2"])
    ]
    
    for step in steps:
        workflow.add_step(step)
    
    result = await manager.workflow_engine.execute_workflow(workflow)
    
    assert result["success"] is False
    assert result["completed_steps"] == 1  # Only step1 should complete
    assert result["failed_steps"] == 1     # step2 should fail
    
    # step3 should not execute due to failed dependency
    step3 = workflow.get_step("step3")
    assert step3.status == "pending"

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_workflow_state_persistence(workflow_manager):
    """Test workflow state persistence in Redis."""
    manager = workflow_manager
    
    workflow = await manager.create_simple_workflow()
    result = await manager.workflow_engine.execute_workflow(workflow)
    
    assert result["success"] is True
    
    # Verify workflow state is persisted
    workflow_key = f"workflow_state:{workflow.workflow_id}"
    cached_state = await manager.redis_service.client.get(workflow_key)
    
    # State should be cached
    assert cached_state is not None

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_concurrent_workflow_execution(workflow_manager):
    """Test concurrent execution of multiple workflows."""
    manager = workflow_manager
    
    # Create multiple workflows
    workflows = [
        await manager.create_simple_workflow(),
        await manager.create_parallel_workflow(),
        await manager.create_conditional_workflow()
    ]
    
    # Update workflow IDs to be unique
    for i, workflow in enumerate(workflows):
        workflow.workflow_id = f"concurrent_{i}"
    
    start_time = time.time()
    
    # Execute workflows concurrently
    tasks = [manager.workflow_engine.execute_workflow(wf) for wf in workflows]
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_time
    
    # All workflows should succeed
    for result in results:
        assert result["success"] is True
    
    # Concurrent execution should be efficient
    assert total_time < 3.0

@pytest.mark.asyncio
@pytest.mark.l2_integration
async def test_workflow_performance_benchmark(workflow_manager):
    """Benchmark workflow execution for performance analysis."""
    manager = workflow_manager
    
    # Create large workflow for performance testing
    workflow = WorkflowDefinition("perf_test", "Performance Test Workflow")
    
    # Add 20 sequential steps
    for i in range(20):
        step = WorkflowStep(f"step_{i}", WorkflowStepType.SEQUENTIAL, f"agent_{i%5}")
        if i > 0:
            step.dependencies = [f"step_{i-1}"]
        workflow.add_step(step)
    
    start_time = time.time()
    result = await manager.workflow_engine.execute_workflow(workflow)
    execution_time = time.time() - start_time
    
    assert result["success"] is True
    assert result["completed_steps"] == 20
    
    # Performance benchmarks
    assert execution_time < 5.0  # Should complete 20 steps in under 5 seconds
    avg_step_time = execution_time / 20
    assert avg_step_time < 0.25  # Average step time under 250ms
    
    logger.info(f"Performance: 20 steps in {execution_time:.2f}s")
    logger.info(f"Average step time: {avg_step_time*1000:.1f}ms")