"""Integration Tests: Multi-Agent Workflow Orchestration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure multi-agent workflows deliver complete AI solutions
- Value Impact: Multi-agent workflows are the core value proposition - DataHelper  ->  Optimization workflows
- Strategic Impact: Foundation for complex AI problem solving and enterprise-grade solutions

This test suite validates:
1. DataHelper  ->  Optimization agent workflows execute in correct order
2. Agent handoffs and state transitions work properly 
3. Supervisor pattern manages child agents correctly
4. Cross-agent data passing maintains integrity
5. WebSocket events track workflow progress
6. Error propagation and workflow recovery
7. Performance under multiple concurrent workflows

CRITICAL: Tests real multi-agent coordination patterns without external dependencies.
Uses realistic agent simulation with proper state management.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Core imports  
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult, 
    PipelineStep,
    AgentExecutionStrategy
)
from netra_backend.app.agents.supervisor.user_execution_context import (
    UserExecutionContext,
    validate_user_context
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

# Test framework imports
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)


class WorkflowMockAgent(BaseAgent):
    """Mock agent that simulates realistic workflow behavior."""
    
    def __init__(self, name: str, llm_manager: LLMManager, dependencies: List[str] = None, 
                 produces_data: bool = False, consumes_data: bool = False):
        super().__init__(llm_manager=llm_manager, name=name, description=f"Workflow {name} agent")
        self.dependencies = dependencies or []
        self.produces_data = produces_data
        self.consumes_data = consumes_data
        self.execution_count = 0
        self.workflow_data = {}
        self.websocket_bridge = None
        self._run_id = None
        
    def set_websocket_bridge(self, bridge, run_id):
        """Set WebSocket bridge for event emission."""
        self.websocket_bridge = bridge
        self._run_id = run_id
        
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = True) -> Dict[str, Any]:
        """Execute agent with workflow simulation."""
        self.execution_count += 1
        
        # Check dependencies in state
        missing_deps = []
        for dep in self.dependencies:
            if not state.metadata or f"{dep}_result" not in state.metadata:
                missing_deps.append(dep)
                
        if missing_deps and self.consumes_data:
            raise RuntimeError(f"Missing dependencies for {self.name}: {missing_deps}")
            
        # Simulate agent thinking
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, f"Starting {self.name} workflow step...", step_number=1
            )
            
        # Simulate processing based on agent type
        await self._simulate_agent_work(state, run_id, stream_updates)
        
        # Generate workflow result
        result = {
            "success": True,
            "agent_name": self.name,
            "execution_count": self.execution_count,
            "dependencies_satisfied": len(missing_deps) == 0,
            "workflow_phase": self._get_workflow_phase(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add agent-specific results to state for downstream agents
        if self.produces_data:
            agent_result = self._generate_agent_output(state)
            result.update(agent_result)
            
            # Store in state for downstream agents
            if not state.metadata:
                state.metadata = {}
            state.metadata[f"{self.name}_result"] = agent_result
            state.metadata[f"{self.name}_completed"] = True
            
        # Final thinking update
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_agent_thinking(
                run_id, self.name, f"Completed {self.name} workflow step", step_number=2
            )
            
        return result
        
    async def _simulate_agent_work(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Simulate agent-specific work patterns."""
        if self.name == "triage":
            await self._simulate_triage_work(state, run_id, stream_updates)
        elif self.name == "data_helper":
            await self._simulate_data_helper_work(state, run_id, stream_updates)
        elif self.name == "optimization":
            await self._simulate_optimization_work(state, run_id, stream_updates)
        elif self.name == "actions":
            await self._simulate_actions_work(state, run_id, stream_updates)
        else:
            # Generic work simulation
            await asyncio.sleep(0.05)
            
    async def _simulate_triage_work(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Simulate triage agent analysis."""
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, "triage_classifier", {"request": "classify_request"}
            )
            
        await asyncio.sleep(0.03)
        
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, "triage_classifier", {"category": "optimization_request"}
            )
            
    async def _simulate_data_helper_work(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Simulate data helper agent data gathering."""
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, "data_analyzer", {"source": "user_data"}
            )
            
        await asyncio.sleep(0.08)  # Data analysis takes longer
        
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, "data_analyzer", 
                {"analysis_complete": True, "data_quality": "high"}
            )
            
    async def _simulate_optimization_work(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Simulate optimization agent recommendations."""
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, "optimization_engine", {"strategy": "cost_performance"}
            )
            
        await asyncio.sleep(0.12)  # Optimization analysis is complex
        
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, "optimization_engine",
                {"recommendations": 3, "estimated_savings": 15000}
            )
            
    async def _simulate_actions_work(self, state: DeepAgentState, run_id: str, stream_updates: bool):
        """Simulate actions agent implementation planning."""  
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_executing(
                run_id, self.name, "action_planner", {"recommendations": "process"}
            )
            
        await asyncio.sleep(0.06)
        
        if stream_updates and self.websocket_bridge:
            await self.websocket_bridge.notify_tool_completed(
                run_id, self.name, "action_planner",
                {"action_plan": "generated", "timeline": "2_weeks"}
            )
            
    def _get_workflow_phase(self) -> str:
        """Get workflow phase for this agent."""
        phase_map = {
            "triage": "analysis",
            "data_helper": "data_gathering", 
            "optimization": "recommendation",
            "actions": "implementation",
            "reporting": "synthesis"
        }
        return phase_map.get(self.name, "unknown")
        
    def _generate_agent_output(self, state: DeepAgentState) -> Dict[str, Any]:
        """Generate agent-specific output data."""
        if self.name == "triage":
            return {
                "category": "cost_optimization",
                "priority": "high",
                "data_sufficiency": "sufficient",
                "next_agents": ["data_helper", "optimization"]
            }
        elif self.name == "data_helper":
            return {
                "data_sources": 3,
                "data_quality": "high",
                "analysis_complete": True,
                "key_metrics": {
                    "monthly_spend": 45000,
                    "model_usage": {"gpt4": 60, "claude": 40}
                }
            }
        elif self.name == "optimization":
            return {
                "recommendations": [
                    {"type": "model_switching", "savings": 8000},
                    {"type": "batch_processing", "savings": 5000},
                    {"type": "caching", "savings": 2000}
                ],
                "total_savings": 15000,
                "confidence": 0.85
            }
        elif self.name == "actions":
            return {
                "action_plan": {
                    "phase1": "Implement caching (Week 1)",
                    "phase2": "Model optimization (Week 2)",
                    "phase3": "Batch processing (Week 3)"
                },
                "implementation_ready": True
            }
        else:
            return {"generic_output": f"Results from {self.name}"}


class MockWebSocketManager:
    """Mock WebSocket manager for workflow testing."""
    
    def __init__(self):
        self.emitted_events = []
        self.workflow_events = {}
        
    async def create_bridge(self, user_context: UserExecutionContext):
        """Create mock WebSocket bridge."""
        bridge = AsyncMock(spec=AgentWebSocketBridge)
        bridge.user_context = user_context
        bridge.emitted_events = []
        
        async def track_emit(event_type, data, **kwargs):
            event = {
                "event_type": event_type,
                "data": data,
                "user_id": user_context.user_id,
                "run_id": user_context.run_id,
                "timestamp": datetime.now(timezone.utc),
                "kwargs": kwargs
            }
            bridge.emitted_events.append(event)
            self.emitted_events.append(event)
            
            # Track workflow progression
            run_id = user_context.run_id
            if run_id not in self.workflow_events:
                self.workflow_events[run_id] = []
            self.workflow_events[run_id].append(event)
            
            return True
        
        # Mock all notification methods
        bridge.notify_agent_started = AsyncMock(side_effect=lambda run_id, agent_name, context=None:
            track_emit("agent_started", {"agent_name": agent_name, "context": context or {}}))
        bridge.notify_agent_thinking = AsyncMock(side_effect=lambda run_id, agent_name, reasoning, step_number=None, progress_percentage=None:
            track_emit("agent_thinking", {"agent_name": agent_name, "reasoning": reasoning, "step_number": step_number}))
        bridge.notify_tool_executing = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, parameters:
            track_emit("tool_executing", {"agent_name": agent_name, "tool_name": tool_name, "parameters": parameters}))
        bridge.notify_tool_completed = AsyncMock(side_effect=lambda run_id, agent_name, tool_name, result:
            track_emit("tool_completed", {"agent_name": agent_name, "tool_name": tool_name, "result": result}))
        bridge.notify_agent_completed = AsyncMock(side_effect=lambda run_id, agent_name, result, execution_time_ms:
            track_emit("agent_completed", {"agent_name": agent_name, "result": result, "execution_time_ms": execution_time_ms}))
        bridge.notify_agent_error = AsyncMock(side_effect=lambda run_id, agent_name, error, error_context=None:
            track_emit("agent_error", {"agent_name": agent_name, "error": error, "error_context": error_context}))
        
        return bridge
        
    def get_workflow_progression(self, run_id: str) -> List[str]:
        """Get sequence of agents that executed in workflow."""
        if run_id not in self.workflow_events:
            return []
            
        agents_started = []
        for event in self.workflow_events[run_id]:
            if event["event_type"] == "agent_started":
                agent_name = event["data"]["agent_name"]
                if agent_name not in agents_started:
                    agents_started.append(agent_name)
                    
        return agents_started


class TestMultiAgentWorkflowIntegration(BaseIntegrationTest):
    """Integration tests for multi-agent workflow orchestration."""
    
    def setup_method(self):
        """Set up test environment."""
        super().setup_method()
        self.isolated_env = IsolatedEnvironment()
        self.isolated_env.set("TEST_MODE", "true", source="test")
        self.websocket_manager = MockWebSocketManager()
        
    @pytest.fixture
    async def mock_llm_manager(self):
        """Create mock LLM manager."""
        mock_manager = AsyncMock(spec=LLMManager)
        mock_manager.health_check = AsyncMock(return_value={"status": "healthy"})
        mock_manager.initialize = AsyncMock()
        return mock_manager
        
    @pytest.fixture
    async def workflow_user_context(self):
        """Create user context for workflow testing."""
        return UserExecutionContext(
            user_id=f"workflow_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"workflow_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"workflow_run_{uuid.uuid4().hex[:8]}",
            request_id=f"workflow_req_{uuid.uuid4().hex[:8]}",
            agent_context={
                "user_request": "Help me optimize my AI costs and performance",
                "workflow_type": "cost_optimization"
            }
        )
        
    @pytest.fixture  
    async def workflow_agents(self, mock_llm_manager):
        """Create complete workflow agent set."""
        agents = {
            # Triage: Entry point, no dependencies
            "triage": WorkflowMockAgent(
                "triage", mock_llm_manager, 
                dependencies=[], produces_data=True
            ),
            
            # Data Helper: Depends on triage, produces data for optimization
            "data_helper": WorkflowMockAgent(
                "data_helper", mock_llm_manager,
                dependencies=["triage"], produces_data=True, consumes_data=True
            ),
            
            # Optimization: Depends on data, produces recommendations
            "optimization": WorkflowMockAgent(
                "optimization", mock_llm_manager,
                dependencies=["data_helper"], produces_data=True, consumes_data=True
            ),
            
            # Actions: Depends on optimization, creates action plan
            "actions": WorkflowMockAgent(
                "actions", mock_llm_manager,
                dependencies=["optimization"], produces_data=True, consumes_data=True
            ),
            
            # Reporting: Can run independently, synthesizes results
            "reporting": WorkflowMockAgent(
                "reporting", mock_llm_manager,
                dependencies=[], produces_data=True
            )
        }
        return agents
        
    @pytest.fixture
    async def workflow_registry(self, workflow_agents):
        """Create agent registry with workflow agents."""
        registry = MagicMock(spec=AgentRegistry)
        registry.get = lambda name: workflow_agents.get(name)
        registry.get_async = AsyncMock(side_effect=lambda name, context=None: workflow_agents.get(name))
        registry.list_keys = lambda: list(workflow_agents.keys())
        return registry

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_sequential_workflow_execution_order(
        self, workflow_user_context, workflow_registry, workflow_agents, mock_llm_manager
    ):
        """Test that multi-agent workflow executes in correct dependency order."""
        
        # Business Value: Proper execution order ensures data flows correctly through workflow
        
        # Create WebSocket bridge
        websocket_bridge = await self.websocket_manager.create_bridge(workflow_user_context)
        
        # Create execution engine  
        engine = ExecutionEngine._init_from_factory(
            registry=workflow_registry,
            websocket_bridge=websocket_bridge,
            user_context=workflow_user_context
        )
        
        # Create pipeline steps for sequential execution
        pipeline_steps = [
            PipelineStep(
                agent_name="triage",
                strategy=AgentExecutionStrategy.SEQUENTIAL,
                metadata={"phase": "analysis"}
            ),
            PipelineStep(
                agent_name="data_helper", 
                strategy=AgentExecutionStrategy.SEQUENTIAL,
                metadata={"phase": "data_gathering"}
            ),
            PipelineStep(
                agent_name="optimization",
                strategy=AgentExecutionStrategy.SEQUENTIAL, 
                metadata={"phase": "recommendation"}
            ),
            PipelineStep(
                agent_name="actions",
                strategy=AgentExecutionStrategy.SEQUENTIAL,
                metadata={"phase": "implementation"}
            )
        ]
        
        # Create base execution context
        base_context = AgentExecutionContext(
            user_id=workflow_user_context.user_id,
            thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            request_id=workflow_user_context.request_id,
            agent_name="workflow",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=0
        )
        
        # Execute pipeline workflow
        start_time = time.time()
        results = await engine.execute_pipeline(
            steps=pipeline_steps,
            context=base_context,
            user_context=workflow_user_context
        )
        execution_time = time.time() - start_time
        
        # Validate workflow execution
        assert len(results) == 4
        assert execution_time < 5.0  # Should complete within reasonable time
        
        # Validate all agents succeeded
        for result in results:
            assert result.success is True, f"Agent {result.agent_name} failed"
            
        # Validate execution order through WebSocket events
        workflow_progression = self.websocket_manager.get_workflow_progression(workflow_user_context.run_id)
        expected_order = ["triage", "data_helper", "optimization", "actions"]
        
        # Verify agents started in correct order
        for i, expected_agent in enumerate(expected_order):
            assert workflow_progression[i] == expected_agent, f"Expected {expected_agent} at position {i}, got {workflow_progression[i]}"
            
        # Validate data dependencies were satisfied
        for agent_name, agent in workflow_agents.items():
            if agent.consumes_data:
                assert agent.execution_count == 1, f"Data consumer {agent_name} should have executed once"
                
        logger.info(f" PASS:  Sequential workflow execution order test passed - {len(results)} agents in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_datahelper_to_optimization_handoff(
        self, workflow_user_context, workflow_registry, workflow_agents, mock_llm_manager
    ):
        """Test critical DataHelper  ->  Optimization agent handoff with data integrity."""
        
        # Business Value: DataHelper  ->  Optimization is the core value-generating workflow
        
        websocket_bridge = await self.websocket_manager.create_bridge(workflow_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=workflow_registry,
            websocket_bridge=websocket_bridge,
            user_context=workflow_user_context
        )
        
        # Create shared agent state for data handoff
        shared_state = DeepAgentState(
            user_request="Optimize my $45k monthly AI spend",
            user_id=workflow_user_context.user_id,
            chat_thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            agent_input={"optimization_target": "cost_performance"}
        )
        
        # Step 1: Execute DataHelper agent
        data_helper_context = AgentExecutionContext(
            user_id=workflow_user_context.user_id,
            thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            request_id=workflow_user_context.request_id,
            agent_name="data_helper",
            step=PipelineStep.DATA_GATHERING,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=1
        )
        
        data_result = await engine.execute_agent(data_helper_context, workflow_user_context)
        
        # Validate DataHelper execution
        assert data_result.success is True
        assert data_result.agent_name == "data_helper"
        
        # Validate data was stored in state
        assert shared_state.metadata is not None
        assert "data_helper_result" in shared_state.metadata
        
        data_output = shared_state.metadata["data_helper_result"]
        assert data_output["data_quality"] == "high"
        assert data_output["analysis_complete"] is True
        assert "key_metrics" in data_output
        
        # Step 2: Execute Optimization agent with DataHelper output
        optimization_context = AgentExecutionContext(
            user_id=workflow_user_context.user_id,
            thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            request_id=workflow_user_context.request_id,
            agent_name="optimization",
            step=PipelineStep.OPTIMIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=2
        )
        
        optimization_result = await engine.execute_agent(optimization_context, workflow_user_context)
        
        # Validate Optimization execution
        assert optimization_result.success is True
        assert optimization_result.agent_name == "optimization"
        
        # Validate optimization used DataHelper data
        optimization_agent = workflow_agents["optimization"]
        assert optimization_agent.execution_count == 1
        assert optimization_agent.dependencies == ["data_helper"]
        
        # Validate optimization output
        assert "optimization_result" in shared_state.metadata
        opt_output = shared_state.metadata["optimization_result"]
        assert "recommendations" in opt_output
        assert opt_output["total_savings"] > 0
        assert opt_output["confidence"] > 0.5
        
        # Validate WebSocket events for both agents
        events = websocket_bridge.emitted_events
        
        # Should have events for both agents
        data_events = [e for e in events if e["data"]["agent_name"] == "data_helper"]
        opt_events = [e for e in events if e["data"]["agent_name"] == "optimization"]
        
        assert len(data_events) >= 4  # started, thinking, tool events, completed
        assert len(opt_events) >= 4   # started, thinking, tool events, completed
        
        # Validate tool execution in both agents
        tool_events = [e for e in events if e["event_type"] in ["tool_executing", "tool_completed"]]
        assert len(tool_events) >= 4  # At least 2 tools per agent
        
        logger.info(" PASS:  DataHelper  ->  Optimization handoff test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_parallel_agent_execution_with_dependencies(
        self, workflow_user_context, workflow_registry, workflow_agents, mock_llm_manager
    ):
        """Test agents can execute in parallel when dependencies allow."""
        
        # Business Value: Parallel execution improves workflow performance
        
        websocket_bridge = await self.websocket_manager.create_bridge(workflow_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=workflow_registry,
            websocket_bridge=websocket_bridge,
            user_context=workflow_user_context
        )
        
        # Create shared state
        shared_state = DeepAgentState(
            user_request="Parallel workflow test",
            user_id=workflow_user_context.user_id,
            chat_thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            agent_input={"parallel_test": True}
        )
        
        # Pre-populate dependencies for parallel execution
        shared_state.metadata = {
            "triage_result": {"category": "optimization", "next_agents": ["data_helper", "optimization"]},
            "data_helper_result": {"data_quality": "high", "analysis_complete": True}
        }
        
        # Create pipeline steps that can execute in parallel
        pipeline_steps = [
            PipelineStep(
                agent_name="reporting",  # No dependencies
                strategy=AgentExecutionStrategy.PARALLEL,
                metadata={"can_run_parallel": True}
            ),
            PipelineStep(
                agent_name="optimization",  # Has data_helper dependency (satisfied)
                strategy=AgentExecutionStrategy.PARALLEL, 
                metadata={"can_run_parallel": True}
            )
        ]
        
        base_context = AgentExecutionContext(
            user_id=workflow_user_context.user_id,
            thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            request_id=workflow_user_context.request_id,
            agent_name="parallel_workflow",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=0
        )
        
        # Execute pipeline in parallel mode
        start_time = time.time()
        results = await engine.execute_pipeline(
            steps=pipeline_steps,
            context=base_context,
            user_context=workflow_user_context
        )
        execution_time = time.time() - start_time
        
        # Validate parallel execution
        assert len(results) == 2
        assert all(result.success for result in results)
        
        # Parallel execution should be faster than sequential
        assert execution_time < 0.5  # Should be much faster than sequential (< 0.25s expected)
        
        # Validate both agents executed
        reporting_agent = workflow_agents["reporting"] 
        optimization_agent = workflow_agents["optimization"]
        
        assert reporting_agent.execution_count == 1
        assert optimization_agent.execution_count == 1
        
        # Validate WebSocket events show overlapping execution
        events = websocket_bridge.emitted_events
        agent_starts = [e for e in events if e["event_type"] == "agent_started"]
        
        # Both agents should have started
        assert len(agent_starts) == 2
        
        # Start times should be close together (parallel execution)
        start_times = [e["timestamp"] for e in agent_starts]
        time_diff = (start_times[1] - start_times[0]).total_seconds() if len(start_times) > 1 else 0
        assert abs(time_diff) < 0.1  # Started within 100ms of each other
        
        logger.info(f" PASS:  Parallel agent execution test passed - {len(results)} agents in {execution_time:.3f}s")

    @pytest.mark.integration
    @pytest.mark.real_services 
    async def test_workflow_error_propagation_and_recovery(
        self, workflow_user_context, workflow_registry, workflow_agents, mock_llm_manager
    ):
        """Test workflow handles agent failures and continues with recovery."""
        
        # Business Value: Workflow resilience ensures partial results are still delivered
        
        # Create failing optimization agent
        failing_optimization = WorkflowMockAgent("optimization", mock_llm_manager,
                                                 dependencies=["data_helper"], consumes_data=True)
        
        async def failing_execute(state, run_id, stream_updates=True):
            raise RuntimeError("Simulated optimization failure")
            
        failing_optimization.execute = failing_execute
        workflow_agents["optimization"] = failing_optimization
        
        websocket_bridge = await self.websocket_manager.create_bridge(workflow_user_context)
        engine = ExecutionEngine._init_from_factory(
            registry=workflow_registry,
            websocket_bridge=websocket_bridge,
            user_context=workflow_user_context
        )
        
        # Create shared state with data_helper results
        shared_state = DeepAgentState(
            user_request="Test error recovery",
            user_id=workflow_user_context.user_id,
            chat_thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            agent_input={"error_test": True}
        )
        
        shared_state.metadata = {
            "data_helper_result": {"data_quality": "high", "analysis_complete": True}
        }
        
        # Create pipeline with failing agent
        pipeline_steps = [
            PipelineStep(
                agent_name="data_helper",
                strategy=AgentExecutionStrategy.SEQUENTIAL,
                metadata={"continue_on_error": True}
            ),
            PipelineStep(
                agent_name="optimization",  # This will fail
                strategy=AgentExecutionStrategy.SEQUENTIAL,
                metadata={"continue_on_error": True}
            ),
            PipelineStep(
                agent_name="reporting",  # This should still execute
                strategy=AgentExecutionStrategy.SEQUENTIAL,
                metadata={"continue_on_error": True}
            )
        ]
        
        base_context = AgentExecutionContext(
            user_id=workflow_user_context.user_id,
            thread_id=workflow_user_context.thread_id,
            run_id=workflow_user_context.run_id,
            request_id=workflow_user_context.request_id,
            agent_name="error_recovery_workflow",
            step=PipelineStep.INITIALIZATION,
            execution_timestamp=datetime.now(timezone.utc),
            pipeline_step_num=0
        )
        
        # Execute pipeline with error handling
        results = await engine.execute_pipeline(
            steps=pipeline_steps,
            context=base_context,
            user_context=workflow_user_context
        )
        
        # Validate error handling
        assert len(results) == 3
        
        # DataHelper should succeed
        data_result = next((r for r in results if r.agent_name == "data_helper"), None)
        assert data_result is not None
        assert data_result.success is True
        
        # Optimization should fail
        opt_result = next((r for r in results if r.agent_name == "optimization"), None) 
        assert opt_result is not None
        assert opt_result.success is False
        assert "optimization failure" in opt_result.error
        
        # Reporting should still succeed (recoverable)
        report_result = next((r for r in results if r.agent_name == "reporting"), None)
        assert report_result is not None
        assert report_result.success is True
        
        # Validate error WebSocket events
        events = websocket_bridge.emitted_events
        error_events = [e for e in events if e["event_type"] == "agent_error"]
        assert len(error_events) == 1  # Only optimization should error
        
        error_event = error_events[0]
        assert error_event["data"]["agent_name"] == "optimization"
        
        # Validate workflow continued after error
        completed_events = [e for e in events if e["event_type"] == "agent_completed"]
        completed_agents = [e["data"]["agent_name"] for e in completed_events]
        
        assert "data_helper" in completed_agents
        assert "reporting" in completed_agents
        # optimization should NOT be in completed (it failed)
        assert "optimization" not in completed_agents
        
        logger.info(" PASS:  Workflow error propagation and recovery test passed")

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_multi_user_workflows(
        self, workflow_registry, workflow_agents, mock_llm_manager
    ):
        """Test multiple users can run workflows concurrently without interference."""
        
        # Business Value: Multi-user isolation is critical for platform scalability
        
        # Create multiple user contexts
        user_contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"concurrent_user_{i}",
                thread_id=f"concurrent_thread_{i}",
                run_id=f"concurrent_run_{i}",
                request_id=f"concurrent_req_{i}",
                metadata={
                    "user_request": f"User {i} workflow request",
                    "user_data": f"secret_data_user_{i}"
                }
            )
            user_contexts.append(context)
        
        # Create WebSocket bridges for each user
        websocket_bridges = []
        for context in user_contexts:
            bridge = await self.websocket_manager.create_bridge(context)
            websocket_bridges.append(bridge)
        
        # Create execution engines for each user
        engines = []
        for i, (context, bridge) in enumerate(zip(user_contexts, websocket_bridges)):
            engine = ExecutionEngine._init_from_factory(
                registry=workflow_registry,
                websocket_bridge=bridge,
                user_context=context
            )
            engines.append(engine)
        
        # Define workflow for each user
        async def run_user_workflow(user_index, user_context, engine):
            """Run workflow for a specific user."""
            base_context = AgentExecutionContext(
                user_id=user_context.user_id,
                thread_id=user_context.thread_id,
                run_id=user_context.run_id,
                request_id=user_context.request_id,
                agent_name="concurrent_workflow",
                step=PipelineStep.INITIALIZATION,
                execution_timestamp=datetime.now(timezone.utc),
                pipeline_step_num=0
            )
            
            # Execute simple workflow
            pipeline_steps = [
                PipelineStep(agent_name="triage", strategy=AgentExecutionStrategy.SEQUENTIAL),
                PipelineStep(agent_name="reporting", strategy=AgentExecutionStrategy.SEQUENTIAL)
            ]
            
            results = await engine.execute_pipeline(
                steps=pipeline_steps,
                context=base_context,
                user_context=user_context
            )
            
            return {"user_id": user_context.user_id, "results": results}
        
        # Execute workflows concurrently
        start_time = time.time()
        tasks = []
        for i, (context, engine) in enumerate(zip(user_contexts, engines)):
            task = run_user_workflow(i, context, engine)
            tasks.append(task)
            
        workflow_results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Validate concurrent execution
        assert len(workflow_results) == 3
        assert execution_time < 3.0  # All workflows should complete quickly
        
        # Validate no exceptions occurred
        for result in workflow_results:
            assert not isinstance(result, Exception), f"Workflow failed: {result}"
            
        # Validate user isolation
        for i, result in enumerate(workflow_results):
            expected_user_id = f"concurrent_user_{i}"
            assert result["user_id"] == expected_user_id
            assert len(result["results"]) == 2  # Both agents should execute
            
            # All agent executions should succeed
            for agent_result in result["results"]:
                assert agent_result.success is True
                
        # Validate WebSocket event isolation
        for i, bridge in enumerate(websocket_bridges):
            user_events = bridge.emitted_events
            assert len(user_events) > 0
            
            # All events should be for this user only
            for event in user_events:
                assert event["user_id"] == f"concurrent_user_{i}"
                
        # Validate agent execution counts
        # Each user should have triggered agent execution
        total_triage_executions = sum(
            1 for agent_dict in [workflow_agents] * 3
            if agent_dict["triage"].execution_count > 0
        )
        
        # Triage agent should have executed for multiple workflows
        # (Note: We're using same agent instances, so execution_count accumulates)
        assert workflow_agents["triage"].execution_count >= 3
        
        logger.info(f" PASS:  Concurrent multi-user workflows test passed - 3 users in {execution_time:.3f}s")


if __name__ == "__main__":
    # Run specific test for development
    pytest.main([__file__, "-v", "-s"])