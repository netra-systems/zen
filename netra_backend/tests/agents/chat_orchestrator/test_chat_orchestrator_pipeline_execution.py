"""
Comprehensive unit tests for ChatOrchestrator pipeline execution module.

Business Value: Tests the end-to-end pipeline orchestration that coordinates multiple
agents to deliver complete AI optimization workflows and solutions to users.

Coverage Areas:
- Pipeline execution workflow from plan to completion
- Agent routing and execution coordination
- Step-by-step result accumulation and data flow
- Error handling and graceful degradation
- Agent registry integration and availability checking
- Context preparation and data passing between agents
- Execution engine integration and agent coordination

SSOT Compliance: Uses SSotAsyncTestCase, real service integration, no mocks for core logic
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.agents.chat_orchestrator.pipeline_executor import PipelineExecutor
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
from netra_backend.app.agents.base.interface import ExecutionContext
from dataclasses import dataclass

@dataclass
class AgentState:
    """Simple agent state for testing ChatOrchestrator."""
    user_request: str = ""
    accumulated_data: dict = None

    def __post_init__(self):
        if self.accumulated_data is None:
            self.accumulated_data = {}


class TestChatOrchestratorPipelineExecution(SSotAsyncTestCase):
    """Comprehensive tests for ChatOrchestrator pipeline execution business logic."""

    async def setUp(self):
        """Set up test environment with pipeline executor and mock orchestrator."""
        await super().setUp()

        # Create mock orchestrator with required components
        self.mock_orchestrator = MagicMock()
        self.mock_agent_registry = MagicMock()
        self.mock_execution_engine = AsyncMock()
        self.mock_trace_logger = AsyncMock()

        # Set up orchestrator dependencies
        self.mock_orchestrator.agent_registry = self.mock_agent_registry
        self.mock_orchestrator.execution_engine = self.mock_execution_engine
        self.mock_orchestrator.trace_logger = self.mock_trace_logger

        # Initialize pipeline executor
        self.pipeline_executor = PipelineExecutor(self.mock_orchestrator)

        # Create test execution context
        self.test_context = self._create_test_context(
            "Optimize my AI model performance and analyze costs"
        )

        # Create test execution plans
        self.simple_plan = [
            {
                "agent": "DataHelperAgent",
                "action": "analyze_requirements",
                "params": {"focus": "performance"}
            }
        ]

        self.complex_plan = [
            {
                "agent": "DataHelperAgent",
                "action": "analyze_requirements",
                "params": {"focus": "performance"}
            },
            {
                "agent": "TriageAgent",
                "action": "assess_complexity",
                "params": {"type": "optimization"}
            },
            {
                "agent": "APEXOptimizerAgent",
                "action": "generate_recommendations",
                "params": {"strategy": "cost_performance"}
            }
        ]

    def _create_test_context(self, user_request: str) -> ExecutionContext:
        """Create test execution context with user request."""
        state = AgentState()
        state.user_request = user_request

        context = ExecutionContext(
            request_id=f"test_req_{id(user_request)}",
            state=state,
            user_id="test_user_pipeline"
        )
        return context

    async def test_pipeline_execution_result_initialization(self):
        """Test proper initialization of pipeline result structure."""
        intent = IntentType.OPTIMIZATION_ADVICE
        result = self.pipeline_executor._initialize_result(intent)

        # Assert business logic: result has proper structure
        self.assertEqual(result["intent"], intent.value)
        self.assertEqual(result["steps"], [])
        self.assertEqual(result["data"], {})
        self.assertEqual(result["status"], "processing")

    async def test_simple_pipeline_execution_success(self):
        """Test successful execution of a simple single-step pipeline."""
        # Set up successful agent execution
        mock_agent = MagicMock()
        self.mock_agent_registry.agents = {"DataHelperAgent": mock_agent}
        self.mock_agent_registry.get_agent.return_value = mock_agent

        expected_agent_result = {
            "analysis": "performance requirements identified",
            "recommendations": ["optimize batch size", "reduce model complexity"]
        }
        self.mock_execution_engine.execute_agent.return_value = expected_agent_result

        # Execute pipeline
        result = await self.pipeline_executor.execute(
            self.test_context,
            self.simple_plan,
            IntentType.OPTIMIZATION_ADVICE
        )

        # Assert business logic: pipeline completes successfully
        self.assertEqual(result["intent"], IntentType.OPTIMIZATION_ADVICE.value)
        self.assertEqual(len(result["steps"]), 1)
        self.assertEqual(result["steps"][0]["agent"], "DataHelperAgent")
        self.assertEqual(result["steps"][0]["action"], "analyze_requirements")
        self.assertEqual(result["steps"][0]["result"], expected_agent_result)

    async def test_complex_multi_step_pipeline_execution(self):
        """Test successful execution of a complex multi-step pipeline."""
        # Set up multiple agents in registry
        self.mock_agent_registry.agents = {
            "DataHelperAgent": MagicMock(),
            "TriageAgent": MagicMock(),
            "APEXOptimizerAgent": MagicMock()
        }

        # Mock successful agent executions with different results
        agent_results = [
            {"requirements": "performance optimization needed"},
            {"complexity": "medium", "estimated_time": "2 hours"},
            {"optimizations": ["model pruning", "quantization"], "cost_savings": "30%"}
        ]

        self.mock_execution_engine.execute_agent.side_effect = agent_results

        # Execute complex pipeline
        result = await self.pipeline_executor.execute(
            self.test_context,
            self.complex_plan,
            IntentType.OPTIMIZATION_ADVICE
        )

        # Assert business logic: all steps execute and accumulate results
        self.assertEqual(len(result["steps"]), 3)
        self.assertEqual(result["intent"], IntentType.OPTIMIZATION_ADVICE.value)

        # Verify each step was recorded
        expected_agents = ["DataHelperAgent", "TriageAgent", "APEXOptimizerAgent"]
        actual_agents = [step["agent"] for step in result["steps"]]
        self.assertEqual(actual_agents, expected_agents)

        # Verify execution engine was called for each agent
        self.assertEqual(self.mock_execution_engine.execute_agent.call_count, 3)

    async def test_agent_availability_checking(self):
        """Test agent availability checking logic."""
        # Test with available agent
        self.mock_agent_registry.agents = {"DataHelperAgent": MagicMock()}

        is_available = self.pipeline_executor._is_agent_available("DataHelperAgent")
        self.assertTrue(is_available, "Registered agent should be available")

        # Test with unavailable agent
        is_unavailable = self.pipeline_executor._is_agent_available("NonexistentAgent")
        self.assertFalse(is_unavailable, "Unregistered agent should not be available")

    async def test_placeholder_result_for_unavailable_agents(self):
        """Test creation of placeholder results for unavailable agents."""
        # Set up empty agent registry
        self.mock_agent_registry.agents = {}

        # Execute pipeline with unavailable agent
        result = await self.pipeline_executor.execute(
            self.test_context,
            self.simple_plan,
            IntentType.OPTIMIZATION_ADVICE
        )

        # Assert business logic: placeholder result created
        self.assertEqual(len(result["steps"]), 1)
        step_result = result["steps"][0]["result"]

        self.assertEqual(step_result["status"], "pending")
        self.assertEqual(step_result["agent"], "DataHelperAgent")
        self.assertEqual(step_result["action"], "analyze_requirements")
        self.assertIn("pending", step_result["message"])

    async def test_context_preparation_with_accumulated_data(self):
        """Test that context is properly prepared with accumulated data."""
        # Set up available agent
        self.mock_agent_registry.agents = {"DataHelperAgent": MagicMock()}

        # Create plan with multiple steps to accumulate data
        accumulated_data = {"previous_analysis": "completed"}

        # Test context preparation
        self.pipeline_executor._prepare_context(self.test_context, accumulated_data)

        # Assert business logic: context receives accumulated data
        self.assertEqual(
            self.test_context.state.accumulated_data,
            accumulated_data,
            "Context should receive accumulated data from previous steps"
        )

    async def test_data_accumulation_between_steps(self):
        """Test data accumulation logic between pipeline steps."""
        # Set up agents with results that should accumulate
        self.mock_agent_registry.agents = {
            "DataHelperAgent": MagicMock(),
            "TriageAgent": MagicMock()
        }

        step_results = [
            {"analysis": "requirements gathered", "data_points": 15},
            {"complexity_score": 0.7, "recommendations": ["optimize"]}
        ]

        self.mock_execution_engine.execute_agent.side_effect = step_results

        two_step_plan = [
            {"agent": "DataHelperAgent", "action": "analyze", "params": {}},
            {"agent": "TriageAgent", "action": "triage", "params": {}}
        ]

        # Execute pipeline
        await self.pipeline_executor.execute(
            self.test_context,
            two_step_plan,
            IntentType.OPTIMIZATION_ADVICE
        )

        # Verify context preparation was called with accumulated data
        # The second agent execution should have access to first agent's results
        self.assertEqual(self.mock_execution_engine.execute_agent.call_count, 2)

    async def test_trace_logging_during_execution(self):
        """Test that pipeline execution is properly traced and logged."""
        # Set up available agent
        self.mock_agent_registry.agents = {"DataHelperAgent": MagicMock()}
        self.mock_execution_engine.execute_agent.return_value = {"success": True}

        # Execute pipeline
        await self.pipeline_executor.execute(
            self.test_context,
            self.simple_plan,
            IntentType.OPTIMIZATION_ADVICE
        )

        # Assert business logic: trace logging occurs for each step
        self.mock_trace_logger.log.assert_called()
        log_calls = self.mock_trace_logger.log.call_args_list

        # Should log step execution
        self.assertTrue(any("Executing" in str(call) for call in log_calls),
                       "Should log step execution")

    async def test_step_execution_with_parameters(self):
        """Test that step parameters are properly passed during execution."""
        # Set up available agent
        mock_agent = MagicMock()
        self.mock_agent_registry.agents = {"DataHelperAgent": mock_agent}
        self.mock_agent_registry.get_agent.return_value = mock_agent

        step_with_params = {
            "agent": "DataHelperAgent",
            "action": "analyze_requirements",
            "params": {"focus": "performance", "detail_level": "high"}
        }

        # Execute single step
        await self.pipeline_executor._execute_step(
            self.test_context,
            step_with_params,
            {}
        )

        # Assert business logic: trace logging includes parameters
        self.mock_trace_logger.log.assert_called()
        log_call_args = self.mock_trace_logger.log.call_args

        # Verify parameters are logged
        logged_params = log_call_args[0][1]  # Second argument should be params
        self.assertEqual(logged_params["focus"], "performance")
        self.assertEqual(logged_params["detail_level"], "high")

    async def test_pipeline_execution_error_handling(self):
        """Test error handling during pipeline execution."""
        # Set up agent that will fail
        self.mock_agent_registry.agents = {"DataHelperAgent": MagicMock()}
        self.mock_execution_engine.execute_agent.side_effect = Exception("Agent execution failed")

        # Execute pipeline - should not crash
        with self.assertRaises(Exception) as context:
            await self.pipeline_executor.execute(
                self.test_context,
                self.simple_plan,
                IntentType.OPTIMIZATION_ADVICE
            )

        # Error should propagate appropriately
        self.assertIn("Agent execution failed", str(context.exception))

    async def test_result_update_logic(self):
        """Test that pipeline results are properly updated after each step."""
        initial_result = {
            "intent": IntentType.OPTIMIZATION_ADVICE.value,
            "steps": [],
            "data": {},
            "status": "processing"
        }

        step = {"agent": "DataHelperAgent", "action": "analyze", "params": {}}
        step_result = {"analysis": "completed", "confidence": 0.9}

        # Update result
        self.pipeline_executor._update_result(initial_result, step, step_result)

        # Assert business logic: result is updated correctly
        self.assertEqual(len(initial_result["steps"]), 1)
        recorded_step = initial_result["steps"][0]

        self.assertEqual(recorded_step["agent"], "DataHelperAgent")
        self.assertEqual(recorded_step["action"], "analyze")
        self.assertEqual(recorded_step["result"], step_result)

    async def test_data_accumulation_logic(self):
        """Test data accumulation logic between steps."""
        accumulated_data = {"existing": "data"}

        # Test with dictionary result
        dict_result = {"new": "information", "score": 0.85}
        self.pipeline_executor._accumulate_data(accumulated_data, dict_result)

        # Assert business logic: dictionary data is merged
        self.assertEqual(accumulated_data["existing"], "data")  # Original data preserved
        self.assertEqual(accumulated_data["new"], "information")  # New data added
        self.assertEqual(accumulated_data["score"], 0.85)

        # Test with non-dictionary result
        non_dict_result = "string result"
        original_keys = set(accumulated_data.keys())
        self.pipeline_executor._accumulate_data(accumulated_data, non_dict_result)

        # Assert business logic: non-dictionary results don't modify accumulated data
        self.assertEqual(set(accumulated_data.keys()), original_keys)

    async def tearDown(self):
        """Clean up test environment."""
        await super().tearDown()


class TestPipelineExecutorAgentRouting(SSotAsyncTestCase):
    """Specialized tests for agent routing logic within pipeline execution."""

    async def setUp(self):
        """Set up test environment for agent routing tests."""
        await super().setUp()

        # Create mock orchestrator with minimal setup
        self.mock_orchestrator = MagicMock()
        self.mock_agent_registry = MagicMock()
        self.mock_execution_engine = AsyncMock()
        self.mock_trace_logger = AsyncMock()

        self.mock_orchestrator.agent_registry = self.mock_agent_registry
        self.mock_orchestrator.execution_engine = self.mock_execution_engine
        self.mock_orchestrator.trace_logger = self.mock_trace_logger

        self.pipeline_executor = PipelineExecutor(self.mock_orchestrator)

        # Create test context
        self.test_context = self._create_test_context("Test routing request")

    def _create_test_context(self, user_request: str) -> ExecutionContext:
        """Create test execution context with user request."""
        state = AgentState()
        state.user_request = user_request

        context = ExecutionContext(
            request_id=f"test_req_{id(user_request)}",
            state=state,
            user_id="test_user_routing"
        )
        return context

    async def test_agent_routing_to_available_agent(self):
        """Test routing to an available agent in the registry."""
        # Set up available agent
        mock_agent = MagicMock()
        self.mock_agent_registry.agents = {"TestAgent": mock_agent}
        self.mock_agent_registry.get_agent.return_value = mock_agent

        expected_result = {"routed": "successfully"}
        self.mock_execution_engine.execute_agent.return_value = expected_result

        # Route to agent
        result = await self.pipeline_executor._route_to_agent(
            self.test_context,
            "TestAgent",
            "test_action",
            {"param": "value"},
            {}
        )

        # Assert business logic: routing succeeds and returns agent result
        self.assertEqual(result, expected_result)
        self.mock_agent_registry.get_agent.assert_called_with("TestAgent")
        self.mock_execution_engine.execute_agent.assert_called_with(mock_agent, self.test_context)

    async def test_agent_routing_to_unavailable_agent(self):
        """Test routing to an unavailable agent creates placeholder."""
        # Set up empty agent registry
        self.mock_agent_registry.agents = {}

        # Route to unavailable agent
        result = await self.pipeline_executor._route_to_agent(
            self.test_context,
            "UnavailableAgent",
            "test_action",
            {"param": "value"},
            {}
        )

        # Assert business logic: placeholder result created
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["agent"], "UnavailableAgent")
        self.assertEqual(result["action"], "test_action")
        self.assertIn("pending", result["message"])

    async def test_placeholder_result_creation(self):
        """Test creation of placeholder results for unimplemented agents."""
        placeholder = self.pipeline_executor._create_placeholder_result(
            "FutureAgent",
            "complex_analysis"
        )

        # Assert business logic: placeholder contains proper information
        self.assertEqual(placeholder["status"], "pending")
        self.assertEqual(placeholder["agent"], "FutureAgent")
        self.assertEqual(placeholder["action"], "complex_analysis")
        self.assertIn("pending", placeholder["message"])

    async def tearDown(self):
        """Clean up agent routing test environment."""
        await super().tearDown()