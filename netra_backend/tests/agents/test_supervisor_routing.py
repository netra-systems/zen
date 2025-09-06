from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""
Test module: Supervisor Agent Routing
Split from large test file for architecture compliance
Test classes: TestSupervisorConsolidatedAgentRouting, TestSupervisorErrorCascadePrevention
"""""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
from datetime import datetime, timezone

import pytest
from netra_backend.app.schemas import (
AgentCompleted,
AgentStarted,
SubAgentLifecycle,
SubAgentUpdate,
WebSocketMessage,
)

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.supervisor.execution_context import (
AgentExecutionContext,
AgentExecutionResult,
)
from netra_backend.app.core.interfaces_execution import ExecutionStrategy

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.tests.helpers.supervisor_extensions import (
install_supervisor_extensions,
)
from netra_backend.tests.supervisor_test_helpers import (
assert_agent_called,
create_agent_state,
create_execution_context,
create_pipeline_config,
create_supervisor_agent,
create_supervisor_mocks,
execute_pipeline,
setup_circuit_breaker,
setup_data_agent_mock,
setup_failing_agent_mock,
setup_optimization_agent_mock,
setup_retry_agent_mock,
setup_triage_agent_mock,
)

# Install extension methods for testing
install_supervisor_extensions()

class TestSupervisorConsolidatedAgentRouting:
    """Test 1: Test multi-agent routing decisions based on message content"""
    @pytest.mark.asyncio
    async def test_routes_to_triage_for_classification(self):
        """Test routing to triage agent for message classification"""
        mocks = create_supervisor_mocks()
        supervisor = create_supervisor_agent(mocks)
        setup_triage_agent_mock(supervisor, {
        'user_request': "How can I optimize my model?",
        'triage_result': {"message_type": "optimization_query", "requires_data": False, "confidence": 0.95}
        })

        state = create_agent_state("How can I optimize my model?")
        context = create_execution_context("test-run-1")
        result = await supervisor._route_to_agent(state, context, "triage")

        assert result.success
        assert_agent_called(supervisor, "triage")
        assert result.state.triage_result.category == "optimization_query"
        @pytest.mark.asyncio
        async def test_routes_to_optimization_for_ai_workloads(self):
            """Test routing to optimization agent for AI workload queries"""
            mocks = create_supervisor_mocks()
            supervisor = create_supervisor_agent(mocks)
            setup_optimization_agent_mock(supervisor, {
            'user_request': "Optimize my training pipeline",
            'optimizations_result': {
            "optimization_type": "performance",
            "recommendations": [
            "Increase batch size to 64",
            "Decrease learning rate to 0.001"
            ]
            }
            })

            state = create_agent_state("Optimize my training pipeline", 
            triage_result={"message_type": "optimization_query"})
            context = create_execution_context("test-run-2")
            result = await supervisor._route_to_agent(state, context, "optimization")

            assert result.success
            assert_agent_called(supervisor, "optimization")
            assert len(result.state.optimizations_result.recommendations) == 2
            @pytest.mark.asyncio
            async def test_routes_to_data_for_analysis_queries(self):
                """Test routing to data agent for data analysis requests"""
                mocks = create_supervisor_mocks()
                supervisor = create_supervisor_agent(mocks)
                setup_data_agent_mock(supervisor, {
                'user_request': "Analyze my model metrics",
                'data_result': {
                "analysis": {
                "metrics": {"accuracy": 0.95, "loss": 0.05},
                "trends": "improving"
                }
                }
                })

                state = create_agent_state("Analyze my model metrics",
                triage_result={"message_type": "data_query", "requires_data": True})
                context = create_execution_context("test-run-3")
                result = await supervisor._route_to_agent(state, context, "data")

                assert result.success
                assert_agent_called(supervisor, "data")
                assert result.state.data_result.confidence_score == 0.95
                @pytest.mark.asyncio
                async def test_routing_with_conditional_pipeline(self):
                    """Test conditional routing based on state conditions"""
                    mocks = create_supervisor_mocks()
                    supervisor = create_supervisor_agent(mocks)

        # Setup multiple agents with simple return values
                    for agent_name in ["triage", "data", "optimization"]:
                        agent = supervisor.agents.get(agent_name)
            # Mock: Generic component isolation for controlled unit testing
                        agent.execute = AsyncMock()  # TODO: Use real service instance
                        agent.execute.return_value = create_agent_state("Complex query")

                        pipeline = create_pipeline_config(
                        ["triage", "data", "optimization"],
                        [ExecutionStrategy.SEQUENTIAL, ExecutionStrategy.CONDITIONAL, ExecutionStrategy.SEQUENTIAL]
                        )

                        state = create_agent_state("Complex query", triage_result={"requires_data": True})
                        context = create_execution_context("test-run-4")
                        await execute_pipeline(supervisor, state, context, pipeline)

        # Verify all agents were called appropriately
                        assert_agent_called(supervisor, "triage")
                        assert_agent_called(supervisor, "data")  # Should be called due to requires_data
                        assert_agent_called(supervisor, "optimization")

                        class TestSupervisorErrorCascadePrevention:
                            """Test 2: Test error handling when sub-agents fail"""
                            @pytest.mark.asyncio
                            async def test_prevents_cascade_on_single_agent_failure(self):
                                """Test that supervisor prevents cascade when one agent fails"""
                                mocks = create_supervisor_mocks()
                                supervisor = create_supervisor_agent(mocks)
                                setup_failing_agent_mock(supervisor, "triage", "Triage failed")
                                setup_data_agent_mock(supervisor, {
                                'user_request': "Test query",
                                'data_result': {"processed": True}
                                })

                                state = create_agent_state("Test query")
                                context = create_execution_context("test-run-5")

        # Test that triage fails but data agent can still be called
                                result = await supervisor._route_to_agent_with_retry(state, context, "triage")
                                assert not result.success
                                assert result.error == "Triage failed"

        # But data agent should still be callable
                                data_result = await supervisor._route_to_agent(state, context, "data")
                                assert data_result.success
                                assert data_result.state.data_result.confidence_score > 0
                                @pytest.mark.asyncio
                                async def test_retry_mechanism_on_transient_failures(self):
                                    """Test retry mechanism for transient failures"""
                                    mocks = create_supervisor_mocks()
                                    supervisor = create_supervisor_agent(mocks)
                                    setup_retry_agent_mock(supervisor, "triage", 
                                    ["Transient error 1", "Transient error 2"],
                                    {'user_request': "Test query", 'triage_result': {"success": True}})

                                    state = create_agent_state("Test query")
                                    context = create_execution_context("test-run-6", max_retries=3)
                                    result = await supervisor._route_to_agent_with_retry(state, context, "triage")

                                    agent = supervisor.agents.get("triage")
                                    assert result.success
                                    assert agent.execute.call_count == 3
                                    assert result.state.triage_result.category == "success"
                                    @pytest.mark.asyncio
                                    async def test_circuit_breaker_after_multiple_failures(self):
                                        """Test circuit breaker pattern after multiple failures"""
                                        mocks = create_supervisor_mocks()
                                        supervisor = create_supervisor_agent(mocks)
                                        setup_circuit_breaker(supervisor, threshold=3)
                                        setup_failing_agent_mock(supervisor, "optimization", "Service unavailable")

                                        state = create_agent_state("Test query")

        # Trigger multiple failures
                                        for i in range(4):
                                            context = create_execution_context(f"test-run-{i}")
                                            result = await supervisor._route_to_agent_with_circuit_breaker(
                                            state, context, "optimization"
                                            )

                                            if i < 3:
                                                assert not result.success
                                                agent = supervisor.agents["optimization"]
                                                assert agent.execute.call_count == i + 1
                                            else:
                # Circuit breaker should be open
                                                assert not result.success
                                                assert result.error == "Circuit breaker open for optimization"
                                                assert agent.execute.call_count == 3  # No additional calls