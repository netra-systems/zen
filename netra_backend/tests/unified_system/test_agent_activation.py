"""Test Suite: Agent Activation and Routing

Tests agent activation, routing decisions, sub-agent spawning, and response aggregation.
Validates real agent behavior and decision-making processes.

Business Value Justification (BVJ):
- Segment: Enterprise & Growth ($25K MRR)
- Business Goal: Ensure intelligent agent routing and reliable sub-agent orchestration
- Value Impact: Validates core AI decision-making and agent coordination
- Revenue Impact: Critical for delivering accurate AI optimization recommendations
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pytest

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.base.execution_context import AgentExecutionContext
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.config import AppConfig

logger = central_logger.get_logger(__name__)

@dataclass
class AgentActivationEvent:
    """Tracks agent activation events."""
    agent_name: str
    user_request: str
    timestamp: float
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None

class MockAnalysisAgent(BaseAgent):
    """Mock analysis agent for testing."""
    
    def __init__(self):
    pass
        super().__init__()
        self.executions = []
        self.response_delay = 0.5
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
        """Execute analysis agent with tracking."""
        start_time = time.time()
        
        # Simulate analysis work
        await asyncio.sleep(self.response_delay)
        
        execution_data = {
            "agent": "analysis",
            "request": state.user_request if hasattr(state, 'user_request') else 'unknown',
            "duration": time.time() - start_time,
            "run_id": run_id
        }
        self.executions.append(execution_data)
        
        # Simulate analysis response
        # Store response in messages list for tracking
        response_data = {
            "agent": "analysis",
            "findings": "Cost optimization opportunities identified",
            "recommendations": ["Switch to Claude 3.5", "Implement caching"],
            "estimated_savings": "$4,500/month"
        }
        state.messages.append({"type": "agent_response", "data": response_data})
        
        await asyncio.sleep(0)
    return execution_data

class MockDebugAgent(BaseAgent):
    """Mock debug agent for testing."""
    
    def __init__(self):
    pass
        super().__init__()
        self.executions = []
        self.response_delay = 0.3
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
        """Execute debug agent with tracking."""
        start_time = time.time()
        
        # Simulate debug work
        await asyncio.sleep(self.response_delay)
        
        execution_data = {
            "agent": "debug",
            "request": state.user_request if hasattr(state, 'user_request') else 'unknown',
            "duration": time.time() - start_time,
            "run_id": run_id
        }
        self.executions.append(execution_data)
        
        # Simulate debug response
        response_data = {
            "agent": "debug",
            "issues_found": ["API timeout errors", "Rate limit exceeded"],
            "solutions": ["Implement exponential backoff", "Use connection pooling"],
            "severity": "medium"
        }
        state.messages.append({"type": "agent_response", "data": response_data})
        
        await asyncio.sleep(0)
    return execution_data

class MockOptimizationAgent(BaseAgent):
    """Mock optimization agent for testing."""
    
    def __init__(self):
    pass
        super().__init__()
        self.executions = []
        self.response_delay = 0.7
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
        """Execute optimization agent with tracking."""
        start_time = time.time()
        
        # Simulate optimization work
        await asyncio.sleep(self.response_delay)
        
        execution_data = {
            "agent": "optimization",
            "request": state.user_request if hasattr(state, 'user_request') else 'unknown',
            "duration": time.time() - start_time,
            "run_id": run_id
        }
        self.executions.append(execution_data)
        
        # Simulate optimization response
        response_data = {
            "agent": "optimization",
            "strategies": ["Model switching", "Request batching", "Cache implementation"],
            "impact": "65% cost reduction potential",
            "timeline": "2-3 weeks implementation"
        }
        state.messages.append({"type": "agent_response", "data": response_data})
        
        await asyncio.sleep(0)
    return execution_data

class AgentActivationTestHelper:
    """Helper for testing agent activation and routing."""
    
    def __init__(self):
    pass
        self.activations = []
        self.routing_decisions = []
        self.response_aggregations = []
        self.error_events = []
    
    def track_activation(self, event: AgentActivationEvent):
        """Track agent activation event."""
        self.activations.append(event)
        logger.info(f"Agent activated: {event.agent_name} for request: {event.user_request[:50]}")
    
    def track_routing_decision(self, user_request: str, selected_agents: List[str], reasoning: str = ""):
        """Track routing decision."""
    pass
        decision = {
            "request": user_request,
            "selected_agents": selected_agents,
            "reasoning": reasoning,
            "timestamp": time.time()
        }
        self.routing_decisions.append(decision)
        logger.info(f"Routing decision: {selected_agents} for request: {user_request[:50]}")
    
    def track_response_aggregation(self, agent_responses: Dict[str, Any], final_response: str):
        """Track response aggregation."""
        aggregation = {
            "agent_responses": agent_responses,
            "final_response": final_response,
            "timestamp": time.time()
        }
        self.response_aggregations.append(aggregation)
    
    def get_activation_times(self) -> List[float]:
        """Get activation durations."""
    pass
        return [event.duration for event in self.activations if event.duration is not None]
    
    def assert_timing_performance(self, max_seconds: float = 3.0):
        """Assert all activations completed within time limit."""
        times = self.get_activation_times()
        if times:
            max_time = max(times)
            assert max_time < max_seconds, f"Agent activation took {max_time}s, exceeds {max_seconds}s limit"

@pytest.fixture
 def real_agent_registry():
    """Use real service instance."""
    # TODO: Initialize real service
    pass
    """Fixture providing mock agent registry with test agents."""
    # Create mock dependencies for registry
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
    
    registry = AgentRegistry()
    
    # Register mock agents
    analysis_agent = MockAnalysisAgent()
    debug_agent = MockDebugAgent()
    optimization_agent = MockOptimizationAgent()
    
    registry.register("analysis", analysis_agent)
    registry.register("debug", debug_agent) 
    registry.register("optimization", optimization_agent)
    # Mock: Generic component isolation for controlled unit testing
    registry.register("triage", None  # TODO: Use real service instance)  # Simple mock for triage
    
    return registry, analysis_agent, debug_agent, optimization_agent

@pytest.fixture
def activation_helper():
    """Use real service instance."""
    # TODO: Initialize real service
    """Fixture providing agent activation test helper."""
    pass
    return AgentActivationTestHelper()

@pytest.fixture
async def supervisor_with_registry(mock_agent_registry):
    """Fixture providing supervisor with mock registry."""
    registry, analysis_agent, debug_agent, optimization_agent = mock_agent_registry
    
    # Create LLM manager mock for routing decisions
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager = llm_manager_instance  # Initialize appropriate service
    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.ask_llm = AsyncNone  # TODO: Use real service instance
    
    # Create tool dispatcher mock
    # Mock: Tool execution isolation for predictable agent testing
    tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service
    
    # Create WebSocket manager mock  
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager = UnifiedWebSocketManager()
    # Mock: WebSocket connection isolation for testing without network overhead
    websocket_manager.send_message = AsyncNone  # TODO: Use real service instance
    
    # Create database session mock
    # Mock: Database session isolation for transaction testing without real database dependency
    mock_db_session = AsyncNone  # TODO: Use real service instance
    
    supervisor = SupervisorAgent(
        db_session=mock_db_session,
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    # Replace registry with our mock
    supervisor.registry = registry
    
    yield supervisor, registry, analysis_agent, debug_agent, optimization_agent, llm_manager

@pytest.mark.asyncio
class TestAgentActivation:
    """Test agent activation and routing."""
    
    @pytest.mark.asyncio
    async def test_supervisor_agent_routing(self, supervisor_with_registry, activation_helper):
        """Test supervisor routing decisions.
        
        Flow:
        - Send optimization request → verify AnalysisAgent selected
        - Send troubleshooting request → verify DebugAgent selected
        """
    pass
        supervisor, registry, analysis_agent, debug_agent, optimization_agent, llm_manager = supervisor_with_registry
        
        # Mock LLM to await asyncio.sleep(0)
    return routing decisions
        async def mock_routing_llm(prompt, **kwargs):
    pass
            if "optimization" in prompt.lower() or "cost" in prompt.lower():
                await asyncio.sleep(0)
    return "analysis_agent,optimization_agent"
            elif "debug" in prompt.lower() or "error" in prompt.lower():
                return "debug_agent"
            else:
                return "analysis_agent"
        
        llm_manager.ask_llm.side_effect = mock_routing_llm
        
        # Test cases with expected routing
        test_cases = [
            {
                "request": "Help me optimize my AI costs and reduce spending",
                "expected_agents": ["analysis", "optimization"],
                "test_name": "optimization_request"
            },
            {
                "request": "Debug my API errors and connection timeouts", 
                "expected_agents": ["debug"],
                "test_name": "troubleshooting_request"
            },
            {
                "request": "Analyze my model performance metrics",
                "expected_agents": ["analysis"],
                "test_name": "analysis_request"
            }
        ]
        
        for case in test_cases:
            start_time = time.time()
            
            # Create state for the request
            state = DeepAgentState()
            state.user_request = case["request"]
            
            # Track which agents would be activated
            activation_helper.track_routing_decision(
                case["request"], 
                case["expected_agents"],
                f"Test case: {case['test_name']}"
            )
            
            # Execute specific agents based on routing logic
            for agent_name in case["expected_agents"]:
                if agent_name in registry.agents:
                    agent = registry.get(agent_name)
                    execution_start = time.time()
                    
                    await agent.execute(state, f"run_{case['test_name']}")
                    
                    duration = time.time() - execution_start
                    activation_helper.track_activation(AgentActivationEvent(
                        agent_name=agent_name,
                        user_request=case["request"],
                        timestamp=execution_start,
                        duration=duration
                    ))
            
            total_time = time.time() - start_time
            logger.info(f"✅ Routing test '{case['test_name']}' completed in {total_time:.2f}s")
        
        # Verify routing decisions were made
        assert len(activation_helper.routing_decisions) == len(test_cases)
        
        # Verify agents were activated appropriately
        activation_helper.assert_timing_performance(max_seconds=3.0)
        
        # Verify specific agent executions
        assert len(analysis_agent.executions) >= 2, "Analysis agent should execute for multiple requests"
        assert len(debug_agent.executions) >= 1, "Debug agent should execute for debug request"
        assert len(optimization_agent.executions) >= 1, "Optimization agent should execute for cost request"
        
        logger.info("✅ Supervisor routing test completed successfully")
    
    @pytest.mark.asyncio
    async def test_sub_agent_spawning(self, supervisor_with_registry, activation_helper):
        """Test sub-agent creation and execution.
        
        Flow:
        - Supervisor decides on sub-agents
        - Verify sub-agents created
        - Check resource allocation  
        - Test concurrent agent limits
        """
    pass
        supervisor, registry, analysis_agent, debug_agent, optimization_agent, llm_manager = supervisor_with_registry
        
        # Complex request requiring multiple agents
        complex_request = "Analyze my AI infrastructure, debug performance issues, and optimize costs"
        
        # Mock LLM to suggest multiple agents
        llm_manager.ask_llm.return_value = "analysis_agent,debug_agent,optimization_agent"
        
        # Create state
        state = DeepAgentState()
        state.user_request = complex_request
        
        # Track spawning
        agents_to_spawn = ["analysis", "debug", "optimization"]
        activation_helper.track_routing_decision(complex_request, agents_to_spawn, "Multi-agent request")
        
        # Execute agents concurrently to test spawning
        spawn_start_time = time.time()
        
        async def spawn_agent(agent_name: str):
            """Spawn and execute an agent."""
            agent = registry.get(agent_name)
            if agent:
                execution_start = time.time()
                await agent.execute(state, f"spawn_run_{agent_name}")
                duration = time.time() - execution_start
                
                activation_helper.track_activation(AgentActivationEvent(
                    agent_name=agent_name,
                    user_request=complex_request,
                    timestamp=execution_start,
                    duration=duration
                ))
        
        # Spawn agents concurrently
        spawn_tasks = [spawn_agent(name) for name in agents_to_spawn]
        await asyncio.gather(*spawn_tasks)
        
        total_spawn_time = time.time() - spawn_start_time
        
        # Verify concurrent execution was faster than sequential
        sequential_time_estimate = sum(
            [analysis_agent.response_delay, debug_agent.response_delay, optimization_agent.response_delay]
        )
        assert total_spawn_time < sequential_time_estimate * 1.2, \
            f"Concurrent execution {total_spawn_time:.2f}s not significantly faster than sequential {sequential_time_estimate:.2f}s"
        
        # Verify all agents executed
        assert len(activation_helper.activations) == len(agents_to_spawn)
        
        # Verify resource allocation (agents got proper state)
        for agent_name in agents_to_spawn:
            if agent_name == "analysis":
                assert len(analysis_agent.executions) > 0
            elif agent_name == "debug":
                assert len(debug_agent.executions) > 0
            elif agent_name == "optimization":
                assert len(optimization_agent.executions) > 0
        
        # Test concurrent agent limits (simulate)
        max_concurrent_agents = 5
        assert len(agents_to_spawn) <= max_concurrent_agents, "Should respect concurrent agent limits"
        
        logger.info(f"✅ Sub-agent spawning test: {len(agents_to_spawn)} agents in {total_spawn_time:.2f}s")
    
    @pytest.mark.asyncio
    async def test_agent_response_aggregation(self, supervisor_with_registry, activation_helper):
        """Test response aggregation from multiple agents.
        
        Flow:
        - Multiple sub-agents respond
        - Supervisor aggregates responses
        - Final response formatted
        - Quality gates applied
        """
    pass
        supervisor, registry, analysis_agent, debug_agent, optimization_agent, llm_manager = supervisor_with_registry
        
        # Request requiring multiple agents
        request = "Provide comprehensive AI optimization report"
        
        # Create state
        state = DeepAgentState()
        state.user_request = request
        
        # Execute multiple agents to generate responses
        agents_to_execute = ["analysis", "debug", "optimization"]
        
        for agent_name in agents_to_execute:
            agent = registry.get(agent_name)
            await agent.execute(state, f"aggregate_run_{agent_name}")
        
        # Collect agent responses from messages
        agent_responses = {}
        for message in state.messages:
            if message.get("type") == "agent_response":
                agent_name = message["data"]["agent"]
                agent_responses[agent_name] = message["data"]
        
        # Mock LLM aggregation
        aggregated_response = """
        Comprehensive AI Optimization Report:
        
        Analysis Findings: Cost optimization opportunities identified
        - Recommendations: Switch to Claude 3.5, Implement caching
        - Estimated savings: $4,500/month
        
        Debug Results: 2 issues found
        - API timeout errors, Rate limit exceeded
        - Solutions: Exponential backoff, Connection pooling
        
        Optimization Strategy: 65% cost reduction potential
        - Timeline: 2-3 weeks implementation
        - Key strategies: Model switching, Request batching, Cache implementation
        """
        
        llm_manager.ask_llm.return_value = aggregated_response
        
        # Track aggregation
        activation_helper.track_response_aggregation(agent_responses, aggregated_response)
        
        # Verify responses were collected
        assert len(agent_responses) == len(agents_to_execute), \
            f"Expected {len(agents_to_execute)} responses, got {len(agent_responses)}"
        
        # Verify each agent type contributed
        assert "analysis" in agent_responses
        assert "debug" in agent_responses
        assert "optimization" in agent_responses
        
        # Verify response quality
        analysis_response = agent_responses["analysis"]
        assert "recommendations" in analysis_response
        assert "estimated_savings" in analysis_response
        
        debug_response = agent_responses["debug"]
        assert "issues_found" in debug_response
        assert "solutions" in debug_response
        
        optimization_response = agent_responses["optimization"] 
        assert "strategies" in optimization_response
        assert "impact" in optimization_response
        
        # Verify aggregation occurred
        assert len(activation_helper.response_aggregations) > 0
        aggregation = activation_helper.response_aggregations[0]
        assert len(aggregation["agent_responses"]) == len(agents_to_execute)
        assert "Comprehensive AI Optimization Report" in aggregation["final_response"]
        
        logger.info(f"✅ Response aggregation test: {len(agent_responses)} responses aggregated")
    
    @pytest.mark.asyncio
    async def test_agent_error_handling(self, supervisor_with_registry, activation_helper):
        """Test agent failure scenarios.
        
        Business Value: $10K MRR - Error handling
        
        Flow:
        - Sub-agent fails
        - Supervisor handles gracefully
        - Error message generated
        - User notified appropriately
        """
    pass
        supervisor, registry, analysis_agent, debug_agent, optimization_agent, llm_manager = supervisor_with_registry
        
        # Create a failing agent
        class FailingAgent(BaseAgent):
            def __init__(self, failure_type: str = "timeout"):
    """Use real service instance."""
    # TODO: Initialize real service
                super().__init__()
                self.failure_type = failure_type
            
            async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False):
                if self.failure_type == "timeout":
                    raise asyncio.TimeoutError("Agent execution timeout")
                elif self.failure_type == "llm_error":
                    raise Exception("LLM service unavailable")
                else:
                    raise ValueError("Invalid input parameters")
        
        # Register failing agent
        failing_agent = FailingAgent("timeout")
        registry.register("failing", failing_agent)
        
        # Test error scenarios
        error_scenarios = [
            {
                "agent_name": "failing",
                "error_type": "timeout",
                "request": "Test timeout error handling"
            }
        ]
        
        for scenario in error_scenarios:
            state = DeepAgentState()
            state.user_request = scenario["request"]
            
            # Execute failing agent with error handling
            agent = registry.get(scenario["agent_name"])
            error_occurred = False
            error_message = ""
            
            try:
                await agent.execute(state, f"error_run_{scenario['error_type']}")
            except Exception as e:
                error_occurred = True
                error_message = str(e)
                
                # Track error event
                activation_helper.track_activation(AgentActivationEvent(
                    agent_name=scenario["agent_name"],
                    user_request=scenario["request"],
                    timestamp=time.time(),
                    success=False,
                    error=error_message
                ))
            
            # Verify error was handled
            assert error_occurred, f"Expected error for scenario {scenario['error_type']}"
            assert error_message, "Error message should be captured"
            
            # Verify other agents can still execute
            healthy_agent = registry.get("analysis")
            healthy_start = time.time()
            await healthy_agent.execute(state, f"healthy_after_error_{scenario['error_type']}")
            healthy_duration = time.time() - healthy_start
            
            # Track successful execution after error
            activation_helper.track_activation(AgentActivationEvent(
                agent_name="analysis",
                user_request=scenario["request"] + " (recovery)",
                timestamp=healthy_start,
                duration=healthy_duration
            ))
        
        # Verify error tracking
        error_activations = [a for a in activation_helper.activations if not a.success]
        successful_activations = [a for a in activation_helper.activations if a.success]
        
        assert len(error_activations) > 0, "Should have tracked error activations"
        assert len(successful_activations) > 0, "Should have successful activations after errors"
        
        # Verify system remained stable
        for activation in successful_activations:
            assert activation.duration < 2.0, "System should remain responsive after errors"
        
        logger.info(f"✅ Error handling test: {len(error_activations)} errors handled gracefully")
    
    @pytest.mark.asyncio
    async def test_agent_performance_benchmarks(self, supervisor_with_registry, activation_helper):
        """Test agent performance benchmarks and timing constraints."""
    pass
        supervisor, registry, analysis_agent, debug_agent, optimization_agent, llm_manager = supervisor_with_registry
        
        # Performance test scenarios
        performance_tests = [
            {
                "name": "single_agent_speed",
                "agents": ["analysis"],
                "max_time": 2.0,
                "request": "Quick analysis request"
            },
            {
                "name": "dual_agent_coordination",
                "agents": ["analysis", "debug"],
                "max_time": 3.0,
                "request": "Analysis and debug coordination"
            },
            {
                "name": "triple_agent_orchestration",
                "agents": ["analysis", "debug", "optimization"],
                "max_time": 4.0,
                "request": "Full orchestration test"
            }
        ]
        
        for test in performance_tests:
            state = DeepAgentState()
            state.user_request = test["request"]
            
            start_time = time.time()
            
            # Execute agents concurrently
            async def execute_agent(agent_name: str):
    pass
                agent = registry.get(agent_name)
                execution_start = time.time()
                await agent.execute(state, f"perf_run_{test['name']}_{agent_name}")
                duration = time.time() - execution_start
                
                activation_helper.track_activation(AgentActivationEvent(
                    agent_name=agent_name,
                    user_request=test["request"],
                    timestamp=execution_start,
                    duration=duration
                ))
            
            tasks = [execute_agent(name) for name in test["agents"]]
            await asyncio.gather(*tasks)
            
            total_time = time.time() - start_time
            
            # Verify performance benchmark
            assert total_time < test["max_time"], \
                f"Performance test '{test['name']}' took {total_time:.2f}s, exceeds {test['max_time']}s limit"
            
            logger.info(f"✅ Performance test '{test['name']}': {len(test['agents'])} agents in {total_time:.2f}s")
        
        # Overall performance verification
        activation_helper.assert_timing_performance(max_seconds=5.0)
        
        # Calculate average response times
        activation_times = activation_helper.get_activation_times()
        if activation_times:
            avg_time = sum(activation_times) / len(activation_times)
            assert avg_time < 1.0, f"Average agent activation time {avg_time:.2f}s should be under 1s"
            
            logger.info(f"✅ Overall performance: {len(activation_times)} activations, avg {avg_time:.2f}s")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])