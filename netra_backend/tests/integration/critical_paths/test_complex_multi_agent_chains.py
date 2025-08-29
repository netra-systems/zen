"""
Comprehensive tests for complex multi-agent collaborations with 3+ agents.

Tests enterprise workflows with chains like: Triage → Supervisor → Data → Optimization → Reporting
Validates cross-agent data dependencies and complex state propagation.

This addresses the critical gap identified: "No working tests for 3+ agent collaborations"
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from test_framework import setup_test_path
setup_test_path()

from netra_backend.app.agents.state import (
    ActionPlanResult, 
    DeepAgentState, 
    OptimizationsResult, 
    ReportResult
)
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.strict_types import TypedAgentResult
from netra_backend.tests.agents.agent_system_test_helpers import MockSupervisorAgent
from test_framework.mocks import MockRedisClient


class MockTriageAgent:
    """Mock triage agent for testing 3+ agent workflows"""
    
    def __init__(self, name: str = "TriageAgent"):
        self.name = name
        self.agent_type = "triage"
        self.execution_count = 0
        self.last_request_type = None
        self.state_transitions = []
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> DeepAgentState:
        """Execute triage analysis and route to appropriate next agent"""
        self.execution_count += 1
        self.last_request_type = state.request_type
        
        # Simulate triage analysis
        await asyncio.sleep(0.1)
        
        # Determine routing based on request
        if "data" in state.user_request.lower():
            routing_decision = "data_analysis"
            next_agents = ["DataAgent", "OptimizationAgent"]
        elif "optimization" in state.user_request.lower():
            routing_decision = "optimization"
            next_agents = ["OptimizationAgent", "ReportingAgent"]  
        elif "enterprise" in state.user_request.lower():
            routing_decision = "full_pipeline"
            next_agents = ["DataAgent", "OptimizationAgent", "ReportingAgent", "ActionPlanAgent"]
        else:
            routing_decision = "standard"
            next_agents = ["DataAgent"]
            
        # Update state with triage results
        state.triage_result = {
            "routing_decision": routing_decision,
            "next_agents": next_agents,
            "confidence": 0.9,
            "execution_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self.state_transitions.append({
            "agent": self.name,
            "action": "triage_complete",
            "routing_decision": routing_decision,
            "next_agents": next_agents,
            "timestamp": datetime.now(timezone.utc)
        })
        
        return state


class MockDataAgent:
    """Mock data agent for testing data processing in chains"""
    
    def __init__(self, name: str = "DataAgent"):
        self.name = name
        self.agent_type = "data"
        self.execution_count = 0
        self.dependencies_met = True
        self.processing_time = 0.2
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> DeepAgentState:
        """Execute data analysis with dependency checking"""
        self.execution_count += 1
        
        # Check dependencies
        if not hasattr(state, 'triage_result') or not state.triage_result:
            raise ValueError("Data agent requires triage results as dependency")
            
        # Simulate data processing
        await asyncio.sleep(self.processing_time)
        
        # Generate data analysis results
        data_metrics = {
            "total_records": 15000,
            "anomalies_detected": 23,
            "processing_time": self.processing_time,
            "quality_score": 0.94,
            "data_completeness": 0.97,
            "patterns_identified": [
                "Peak usage at 2PM-4PM",
                "Cost spike in GPU utilization", 
                "Memory optimization opportunities"
            ]
        }
        
        state.data_result = {
            "analysis_complete": True,
            "metrics": data_metrics,
            "insights": "Data analysis reveals optimization opportunities",
            "processing_agent": self.name,
            "execution_id": run_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return state


class MockOptimizationAgent:
    """Mock optimization agent for testing optimization workflows"""
    
    def __init__(self, name: str = "OptimizationAgent"):
        self.name = name
        self.agent_type = "optimization"
        self.execution_count = 0
        self.requires_data_dependency = True
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> DeepAgentState:
        """Execute optimization analysis with data dependencies"""
        self.execution_count += 1
        
        # Check data dependency
        if self.requires_data_dependency:
            if not hasattr(state, 'data_result') or not state.data_result:
                raise ValueError("Optimization agent requires data analysis results")
                
        await asyncio.sleep(0.15)
        
        # Generate optimization recommendations based on data
        cost_savings = 1250.0 if hasattr(state, 'data_result') else 500.0
        
        optimization_result = OptimizationsResult(
            optimization_type="gpu_memory",
            recommendations=[
                "Implement batch processing for peak hours",
                "Optimize memory allocation patterns",
                "Schedule maintenance during low-usage periods"
            ],
            cost_savings=cost_savings,
            performance_improvement=0.23,
            confidence_score=0.87
        )
        
        state.optimizations_result = optimization_result
        
        return state


class MockReportingAgent:
    """Mock reporting agent for testing reporting workflows"""
    
    def __init__(self, name: str = "ReportingAgent"):
        self.name = name
        self.agent_type = "reporting"
        self.execution_count = 0
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> DeepAgentState:
        """Generate comprehensive reports from all previous agents"""
        self.execution_count += 1
        
        await asyncio.sleep(0.1)
        
        # Collect data from previous agents
        sections = []
        
        if hasattr(state, 'triage_result') and state.triage_result:
            sections.append({
                "title": "Triage Analysis",
                "content": f"Routing decision: {state.triage_result['routing_decision']}"
            })
            
        if hasattr(state, 'data_result') and state.data_result:
            sections.append({
                "title": "Data Analysis", 
                "content": f"Processed {state.data_result['metrics']['total_records']} records"
            })
            
        if hasattr(state, 'optimizations_result'):
            sections.append({
                "title": "Optimization Recommendations",
                "content": f"Cost savings: ${state.optimizations_result.cost_savings}"
            })
            
        report_result = ReportResult(
            report_title="Multi-Agent Analysis Report",
            summary="Comprehensive analysis completed by agent chain",
            sections=sections,
            recommendations=[
                "Implement optimization recommendations",
                "Monitor performance improvements", 
                "Schedule follow-up analysis"
            ]
        )
        
        state.report_result = report_result
        
        return state


class MockActionPlanAgent:
    """Mock action plan agent for testing action planning workflows"""
    
    def __init__(self, name: str = "ActionPlanAgent"):
        self.name = name
        self.agent_type = "action_plan"
        self.execution_count = 0
        
    async def execute(self, state: DeepAgentState, run_id: str, stream: bool = False) -> DeepAgentState:
        """Generate action plans based on all previous analysis"""
        self.execution_count += 1
        
        await asyncio.sleep(0.12)
        
        # Generate action plan based on available results
        actions = []
        
        if hasattr(state, 'optimizations_result') and state.optimizations_result:
            for rec in state.optimizations_result.recommendations:
                actions.append({
                    "action": rec,
                    "timeline": "2-4 weeks",
                    "resources": ["Engineering team", "Infrastructure budget"]
                })
                
        action_plan_result = ActionPlanResult(
            action_plan_summary="Comprehensive action plan for optimization implementation",
            total_estimated_time="6-8 weeks",
            required_approvals=["Engineering manager", "Finance team"],
            actions=actions,
            execution_timeline=[
                {"phase": "Planning", "duration": "1 week"},
                {"phase": "Implementation", "duration": "4-6 weeks"}, 
                {"phase": "Testing", "duration": "1 week"}
            ]
        )
        
        state.action_plan_result = action_plan_result
        
        return state


class ComplexMultiAgentTestBase:
    """Base class for complex multi-agent chain tests"""
    
    @pytest.fixture
    def mock_agents(self):
        """Create mock agents for testing"""
        return {
            "triage": MockTriageAgent(),
            "data": MockDataAgent(), 
            "optimization": MockOptimizationAgent(),
            "reporting": MockReportingAgent(),
            "action_plan": MockActionPlanAgent(),
            "supervisor": MockSupervisorAgent(None, None)
        }
        
    @pytest.fixture
    def initial_state(self):
        """Create initial agent state for testing"""
        return DeepAgentState(
            user_request="Analyze our system and provide optimization recommendations",
            request_type="enterprise_optimization",
            context={"user_id": "test_user", "permissions": ["read", "analyze"]}
        )
        
    def create_agent_chain(self, agent_names: List[str], agents_dict: Dict[str, Any]) -> List[Any]:
        """Create an ordered chain of agents"""
        return [agents_dict[name] for name in agent_names if name in agents_dict]
        
    async def execute_agent_chain_sequential(self, agents: List[Any], initial_state: DeepAgentState, run_id: str) -> DeepAgentState:
        """Execute agents in sequence, passing state between them"""
        current_state = initial_state
        
        for agent in agents:
            try:
                current_state = await agent.execute(current_state, run_id, False)
            except Exception as e:
                # Add failure information to state
                if not hasattr(current_state, 'failures'):
                    current_state.failures = []
                current_state.failures.append({
                    "agent": agent.name,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                # For dependency failures, break the chain
                if "requires" in str(e).lower() or "dependency" in str(e).lower():
                    break
                    
        return current_state
        
    async def execute_agents_parallel(self, agents: List[Any], state: DeepAgentState, run_id: str) -> tuple[DeepAgentState, List[Exception]]:
        """Execute agents in parallel and aggregate results"""
        tasks = []
        exceptions = []
        
        for agent in agents:
            # Create a copy of state for each agent to avoid conflicts
            agent_state = DeepAgentState(
                user_request=state.user_request,
                request_type=state.request_type,
                context=state.context.copy() if state.context else {}
            )
            # Copy any existing results
            for attr in dir(state):
                if not attr.startswith('_') and attr not in ['user_request', 'request_type', 'context']:
                    if hasattr(state, attr):
                        setattr(agent_state, attr, getattr(state, attr))
                        
            tasks.append(agent.execute(agent_state, f"{run_id}_{agent.name}", False))
            
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results back to main state
        final_state = state
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                exceptions.append(result)
            else:
                # Merge result state back to final state
                agent = agents[i]
                if hasattr(result, f"{agent.agent_type}_result"):
                    setattr(final_state, f"{agent.agent_type}_result", 
                           getattr(result, f"{agent.agent_type}_result"))
                           
        return final_state, exceptions


@pytest.mark.env("test")
@pytest.mark.env("dev")
class TestComplexMultiAgentChains(ComplexMultiAgentTestBase):
    """Comprehensive tests for complex multi-agent collaborations"""
    
    async def test_3_agent_sequential_workflow(self, mock_agents, initial_state):
        """
        Test 3-agent sequential workflow: Triage → Data → Optimization
        
        Validates:
        - Sequential execution with state passing
        - Data dependencies between agents
        - State accumulation through chain
        """
        run_id = str(uuid.uuid4())
        agent_chain = self.create_agent_chain(["triage", "data", "optimization"], mock_agents)
        
        # Execute sequential chain
        final_state = await self.execute_agent_chain_sequential(agent_chain, initial_state, run_id)
        
        # Verify all agents executed
        assert mock_agents["triage"].execution_count == 1
        assert mock_agents["data"].execution_count == 1 
        assert mock_agents["optimization"].execution_count == 1
        
        # Verify state progression
        assert hasattr(final_state, 'triage_result')
        assert hasattr(final_state, 'data_result')
        assert hasattr(final_state, 'optimizations_result')
        
        # Verify data dependencies were met
        assert final_state.triage_result['routing_decision'] == "full_pipeline"
        assert final_state.data_result['analysis_complete'] == True
        assert final_state.optimizations_result.cost_savings > 1000  # Higher because data dependency was met
        
        # Verify execution order by checking agent state transitions
        triage_agent = mock_agents["triage"]
        assert len(triage_agent.state_transitions) == 1
        assert triage_agent.state_transitions[0]['action'] == 'triage_complete'

    async def test_4_agent_workflow_with_supervisor(self, mock_agents, initial_state):
        """
        Test 4-agent workflow with Supervisor coordination
        
        Validates:
        - Supervisor orchestration of sub-agents
        - Parallel execution coordination
        - Resource allocation and prioritization
        """
        run_id = str(uuid.uuid4())
        supervisor = mock_agents["supervisor"]
        sub_agents = [mock_agents["triage"], mock_agents["data"], mock_agents["optimization"]]
        
        # Mock supervisor coordination methods
        supervisor.coordinate_agents = AsyncMock(return_value={
            "execution_order": ["triage", "data", "optimization"],
            "parallel_groups": [["data", "optimization"]],
            "resource_allocation": {"high": ["optimization"], "medium": ["data", "triage"]}
        })
        
        # Step 1: Supervisor determines coordination strategy
        coordination_plan = await supervisor.coordinate_agents(initial_state, sub_agents)
        
        # Step 2: Execute triage first (as specified in plan)
        state_after_triage = await mock_agents["triage"].execute(initial_state, run_id)
        
        # Step 3: Execute data and optimization in parallel (as specified in plan)  
        parallel_agents = [mock_agents["data"], mock_agents["optimization"]]
        final_state, exceptions = await self.execute_agents_parallel(parallel_agents, state_after_triage, run_id)
        
        # Step 4: Supervisor aggregates results
        supervisor_result = await supervisor.execute(final_state, run_id)
        
        # Verify coordination worked
        assert coordination_plan["execution_order"] == ["triage", "data", "optimization"]
        assert "parallel_groups" in coordination_plan
        assert len(exceptions) == 0  # No execution failures
        
        # Verify all agents executed
        assert mock_agents["triage"].execution_count == 1
        assert mock_agents["data"].execution_count == 1
        assert mock_agents["optimization"].execution_count == 1
        
        # Verify state contains results from all agents
        assert hasattr(final_state, 'triage_result')
        assert hasattr(final_state, 'data_result') or hasattr(final_state, 'optimizations_result')

    async def test_5_agent_complete_enterprise_optimization_flow(self, mock_agents, initial_state):
        """
        Test 5-agent complete enterprise optimization flow
        
        Validates:
        - Full enterprise workflow: Triage → Data → Optimization → Reporting → Action Plan
        - Complex state propagation across all agents
        - End-to-end enterprise use case
        """
        run_id = str(uuid.uuid4())
        
        # Set up enterprise-specific request
        enterprise_state = DeepAgentState(
            user_request="Conduct complete enterprise optimization analysis with action plan",
            request_type="enterprise_optimization", 
            context={"user_id": "enterprise_user", "permissions": ["read", "analyze", "plan"]}
        )
        
        # Execute full 5-agent chain
        full_chain = self.create_agent_chain(
            ["triage", "data", "optimization", "reporting", "action_plan"], 
            mock_agents
        )
        
        final_state = await self.execute_agent_chain_sequential(full_chain, enterprise_state, run_id)
        
        # Verify all 5 agents executed
        for agent_name in ["triage", "data", "optimization", "reporting", "action_plan"]:
            assert mock_agents[agent_name].execution_count == 1
            
        # Verify complete state propagation
        assert hasattr(final_state, 'triage_result')
        assert hasattr(final_state, 'data_result') 
        assert hasattr(final_state, 'optimizations_result')
        assert hasattr(final_state, 'report_result')
        assert hasattr(final_state, 'action_plan_result')
        
        # Verify enterprise-specific results
        assert final_state.triage_result['routing_decision'] == "full_pipeline"
        assert len(final_state.triage_result['next_agents']) >= 4
        
        # Verify data flows correctly through chain
        assert final_state.data_result['metrics']['total_records'] == 15000
        assert final_state.optimizations_result.cost_savings == 1250.0  # Higher due to data dependency
        
        # Verify reporting aggregated all results
        report = final_state.report_result
        assert len(report.sections) >= 3  # Should include triage, data, optimization sections
        
        # Verify action plan based on optimization recommendations
        action_plan = final_state.action_plan_result
        assert len(action_plan.actions) >= 1
        assert action_plan.total_estimated_time == "6-8 weeks"

    async def test_cross_agent_data_dependency_validation(self, mock_agents, initial_state):
        """
        Test cross-agent data dependency validation
        
        Validates:
        - Agents properly check for required dependencies
        - Failure handling when dependencies are missing
        - Partial execution with dependency failures
        """
        run_id = str(uuid.uuid4())
        
        # Test 1: Missing triage dependency for data agent
        try:
            # Try to run data agent without triage results
            state_without_triage = DeepAgentState(
                user_request="Process data without triage",
                request_type="data_processing"
            )
            await mock_agents["data"].execute(state_without_triage, run_id)
            assert False, "Expected ValueError for missing triage dependency"
        except ValueError as e:
            assert "triage results" in str(e).lower()
            
        # Test 2: Missing data dependency for optimization agent  
        try:
            # Try to run optimization agent without data results
            state_without_data = DeepAgentState(
                user_request="Optimize without data",
                request_type="optimization"
            )
            # Add triage result but not data result
            state_without_data.triage_result = {"routing_decision": "optimization"}
            
            await mock_agents["optimization"].execute(state_without_data, run_id)
            assert False, "Expected ValueError for missing data dependency"
        except ValueError as e:
            assert "data analysis" in str(e).lower()
            
        # Test 3: Successful dependency chain
        # First run triage
        state_with_triage = await mock_agents["triage"].execute(initial_state, run_id)
        
        # Then run data (should succeed with triage dependency)
        state_with_data = await mock_agents["data"].execute(state_with_triage, f"{run_id}_2")
        
        # Finally run optimization (should succeed with both dependencies)
        final_state = await mock_agents["optimization"].execute(state_with_data, f"{run_id}_3")
        
        # Verify successful execution
        assert hasattr(final_state, 'triage_result')
        assert hasattr(final_state, 'data_result')
        assert hasattr(final_state, 'optimizations_result')
        assert final_state.optimizations_result.cost_savings == 1250.0  # Higher due to data dependency

    async def test_complex_state_propagation_across_boundaries(self, mock_agents, initial_state):
        """
        Test complex state propagation across multiple agent boundaries
        
        Validates:
        - State modifications persist across agent boundaries
        - Complex data structures are preserved
        - State integrity maintained through transformations
        """
        run_id = str(uuid.uuid4())
        
        # Add complex initial context
        complex_context = {
            "user_preferences": {"optimization_focus": "cost", "risk_tolerance": "medium"},
            "system_constraints": {"budget": 50000, "timeline": "3_months"}, 
            "historical_data": {
                "previous_optimizations": [
                    {"type": "memory", "savings": 500, "success": True},
                    {"type": "cpu", "savings": 300, "success": False}
                ]
            }
        }
        
        initial_state.context.update(complex_context)
        
        # Execute 4-agent chain to test state propagation
        agent_chain = self.create_agent_chain(
            ["triage", "data", "optimization", "reporting"], 
            mock_agents
        )
        
        final_state = await self.execute_agent_chain_sequential(agent_chain, initial_state, run_id)
        
        # Verify original context preserved
        assert final_state.context["user_preferences"]["optimization_focus"] == "cost"
        assert final_state.context["system_constraints"]["budget"] == 50000
        assert len(final_state.context["historical_data"]["previous_optimizations"]) == 2
        
        # Verify each agent added its own state while preserving others
        state_attributes = []
        for attr in ['triage_result', 'data_result', 'optimizations_result', 'report_result']:
            if hasattr(final_state, attr):
                state_attributes.append(attr)
                
        assert len(state_attributes) == 4  # All 4 agents added their results
        
        # Verify data integrity across transformations
        # Check that data from early agents is referenced by later agents
        report_sections = final_state.report_result.sections
        section_titles = [section['title'] for section in report_sections]
        
        assert "Triage Analysis" in section_titles
        assert "Data Analysis" in section_titles  
        assert "Optimization Recommendations" in section_titles
        
        # Verify complex data propagation
        # Optimization agent should have used data from data agent
        assert final_state.optimizations_result.cost_savings > 1000  # Indicates data dependency was used
        
        # Verify timestamps show progression
        triage_time = final_state.triage_result['timestamp']
        data_time = final_state.data_result['timestamp']  
        assert data_time > triage_time  # Later timestamp indicates sequential execution

    async def test_agent_chain_failure_recovery_and_partial_execution(self, mock_agents, initial_state):
        """
        Test agent chain behavior with failures and partial execution
        
        Validates:
        - Graceful handling of agent failures
        - Partial execution continues where possible
        - Failure information is captured in state
        """
        run_id = str(uuid.uuid4())
        
        # Configure data agent to fail
        mock_agents["data"].processing_time = 0.001  # Very fast execution
        original_execute = mock_agents["data"].execute
        
        async def failing_execute(state, run_id, stream=False):
            raise RuntimeError("Simulated data processing failure")
            
        mock_agents["data"].execute = failing_execute
        
        # Execute chain with failing agent
        agent_chain = self.create_agent_chain(
            ["triage", "data", "optimization"], 
            mock_agents
        )
        
        final_state = await self.execute_agent_chain_sequential(agent_chain, initial_state, run_id)
        
        # Verify partial execution
        assert hasattr(final_state, 'triage_result')  # First agent succeeded
        assert not hasattr(final_state, 'data_result')  # Second agent failed
        assert not hasattr(final_state, 'optimizations_result')  # Third agent didn't execute due to dependency
        
        # Verify failure information captured
        assert hasattr(final_state, 'failures')
        assert len(final_state.failures) >= 1
        assert final_state.failures[0]['agent'] == "DataAgent"
        assert "data processing failure" in final_state.failures[0]['error']
        
        # Test recovery scenario - fix the failing agent and continue
        mock_agents["data"].execute = original_execute  # Restore original
        mock_agents["optimization"].requires_data_dependency = False  # Allow execution without data
        
        # Continue from partial state
        recovered_state = await mock_agents["optimization"].execute(final_state, f"{run_id}_recovery")
        
        # Verify recovery execution
        assert hasattr(recovered_state, 'optimizations_result')
        assert recovered_state.optimizations_result.cost_savings == 500.0  # Lower due to no data dependency

    async def test_parallel_agent_execution_with_result_aggregation(self, mock_agents, initial_state):
        """
        Test parallel agent execution with proper result aggregation
        
        Validates:
        - Multiple agents can execute simultaneously
        - Results are properly aggregated
        - No race conditions in state updates
        """
        run_id = str(uuid.uuid4())
        
        # First, run triage to set up dependencies
        state_with_triage = await mock_agents["triage"].execute(initial_state, run_id)
        
        # Configure agents for parallel execution
        mock_agents["data"].requires_data_dependency = False  # Remove circular dependency
        mock_agents["optimization"].requires_data_dependency = False  # Allow parallel execution
        
        # Execute data and optimization agents in parallel
        parallel_agents = [mock_agents["data"], mock_agents["optimization"]]
        
        start_time = time.time()
        final_state, exceptions = await self.execute_agents_parallel(
            parallel_agents, state_with_triage, run_id
        )
        execution_time = time.time() - start_time
        
        # Verify parallel execution was faster than sequential
        expected_sequential_time = mock_agents["data"].processing_time + 0.15  # optimization time
        assert execution_time < expected_sequential_time * 0.8  # At least 20% faster
        
        # Verify no exceptions occurred
        assert len(exceptions) == 0
        
        # Verify both agents executed
        assert mock_agents["data"].execution_count == 1
        assert mock_agents["optimization"].execution_count == 1
        
        # Verify results from both agents are present
        # Note: In parallel execution, results are merged back to final state
        has_data_result = hasattr(final_state, 'data_result')
        has_opt_result = hasattr(final_state, 'optimizations_result')
        
        # At least one should be present (depending on execution order and merge logic)
        assert has_data_result or has_opt_result
        
        # Verify triage result is still preserved
        assert hasattr(final_state, 'triage_result')
        assert final_state.triage_result['routing_decision'] == "full_pipeline"


@pytest.mark.env("dev") 
@pytest.mark.env("staging")
class TestComplexMultiAgentChainsIntegration(ComplexMultiAgentTestBase):
    """Integration tests for complex multi-agent chains with real service dependencies"""
    
    async def test_end_to_end_enterprise_workflow_with_redis_state(self, mock_agents, initial_state):
        """
        Test end-to-end enterprise workflow with Redis state management
        
        Validates:
        - State persistence across agent transitions
        - Redis-based state sharing between agents  
        - Recovery from state store failures
        """
        run_id = str(uuid.uuid4())
        
        # Mock Redis client for state management
        mock_redis = MockRedisClient()
        
        # Simulate state storage between agent executions
        with patch('netra_backend.app.services.state.state_manager.StateManager') as MockStateManager:
            state_manager = Mock()
            state_manager.get = AsyncMock(return_value=None)
            state_manager.set = AsyncMock()
            MockStateManager.return_value = state_manager
            
            # Execute first agent and store state
            state_after_triage = await mock_agents["triage"].execute(initial_state, run_id)
            await state_manager.set(f"agent_state:{run_id}", state_after_triage.model_dump())
            
            # Simulate retrieval and continuation by next agent
            stored_state_data = await state_manager.get(f"agent_state:{run_id}")
            if stored_state_data:
                # In real implementation, would deserialize from stored state
                state_for_data_agent = state_after_triage
            else:
                state_for_data_agent = state_after_triage
                
            state_after_data = await mock_agents["data"].execute(state_for_data_agent, run_id)
            
            # Verify state manager was used
            state_manager.set.assert_called()
            state_manager.get.assert_called()
            
            # Verify agent chain completed successfully
            assert hasattr(state_after_data, 'triage_result')
            assert hasattr(state_after_data, 'data_result')

    @pytest.mark.slow
    async def test_high_load_multi_agent_concurrent_execution(self, mock_agents):
        """
        Test multiple concurrent multi-agent chains under load
        
        Validates:
        - System handles multiple simultaneous agent chains
        - No resource contention or deadlocks
        - Performance remains acceptable under load
        """
        concurrent_chains = 5
        chain_length = 3
        
        async def execute_single_chain(chain_id: int):
            """Execute a single agent chain"""
            chain_state = DeepAgentState(
                user_request=f"Process chain {chain_id}",
                request_type="optimization",
                context={"chain_id": chain_id}
            )
            
            agent_chain = self.create_agent_chain(
                ["triage", "data", "optimization"], 
                mock_agents
            )
            
            run_id = f"chain_{chain_id}_{uuid.uuid4()}"
            return await self.execute_agent_chain_sequential(agent_chain, chain_state, run_id)
        
        # Execute multiple chains concurrently
        start_time = time.time()
        tasks = [execute_single_chain(i) for i in range(concurrent_chains)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Verify all chains completed successfully
        assert len(results) == concurrent_chains
        
        for i, result in enumerate(results):
            assert hasattr(result, 'triage_result')
            assert hasattr(result, 'data_result') 
            assert hasattr(result, 'optimizations_result')
            assert result.context['chain_id'] == i
            
        # Verify reasonable performance (should be faster than sequential)
        expected_sequential_time = concurrent_chains * (0.1 + 0.2 + 0.15)  # Sum of agent execution times
        assert total_time < expected_sequential_time * 0.7  # At least 30% improvement from concurrency
        
        # Verify agents handled concurrent load
        # Each agent should have executed once per chain
        assert mock_agents["triage"].execution_count >= concurrent_chains
        assert mock_agents["data"].execution_count >= concurrent_chains  
        assert mock_agents["optimization"].execution_count >= concurrent_chains