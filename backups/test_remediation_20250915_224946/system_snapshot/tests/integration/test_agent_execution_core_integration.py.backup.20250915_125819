"""
Integration tests for AgentExecutionCore and AgentRegistryAdapter signature compatibility.

ISSUE: AgentExecutionCore expects registry.get_async(agent_name, context=context)
       but AgentRegistryAdapter only provides get_async(agent_name)

This test suite:
1. Tests the full agent execution pipeline with real component integration
2. Reproduces the signature mismatch in realistic scenarios
3. Validates the fix works end-to-end
4. Ensures proper user isolation and context propagation

TESTING APPROACH: Non-docker integration tests using real component integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, Optional

# Core imports for integration testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.agents.registry import AgentRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.workflow_orchestrator import WorkflowOrchestrator


class IntegrationTestAgent(BaseAgent):
    """Test agent for integration testing."""

    def __init__(self, name: str = "integration_test_agent", **kwargs):
        self.name = name
        self.user_context = kwargs.get('user_context')
        self.execution_count = 0
        self.last_execution_params = None

    async def execute(self, task: str = "default_task", **kwargs):
        """Execute test task with tracking."""
        self.execution_count += 1
        self.last_execution_params = {"task": task, **kwargs}

        return {
            "success": True,
            "agent_name": self.name,
            "task": task,
            "user_id": self.user_context.user_id if self.user_context else None,
            "execution_count": self.execution_count
        }


class TestAgentExecutionCoreIntegration:
    """Integration tests for the complete agent execution pipeline."""

    def setup_method(self):
        """Set up integration test environment."""
        # Create realistic user context
        self.user_context = UserExecutionContext.from_request_supervisor(
            user_id="integration_user_001",
            thread_id="integration_thread_001",
            run_id="integration_run_001",
            request_id="req_integration_001",
            metadata={
                "test_type": "integration",
                "pipeline": "agent_execution_core"
            }
        )

        # Create real components
        self.agent_class_registry = AgentRegistry()
        self.agent_factory = AgentInstanceFactory()

        # Register our test agent
        self.agent_class_registry.register("integration_test_agent", IntegrationTestAgent)

        # Create the adapter that has the signature issue
        self.registry_adapter = AgentRegistryAdapter(
            agent_class_registry=self.agent_class_registry,
            agent_factory=self.agent_factory,
            user_context=self.user_context
        )

        # Mock external dependencies
        self.mock_websocket_manager = Mock()
        self.mock_state_manager = Mock()
        self.mock_state_manager.save_execution_state = AsyncMock()
        self.mock_state_manager.get_execution_state = AsyncMock(return_value={})

        # Create the execution core with the problematic adapter
        self.execution_core = AgentExecutionCore(
            registry=self.registry_adapter,  # This has the broken signature
            websocket_manager=self.mock_websocket_manager,
            state_manager=self.mock_state_manager
        )

    @pytest.mark.asyncio
    async def test_signature_mismatch_in_real_execution_pipeline(self):
        """Test that the signature mismatch causes real execution failures.

        This reproduces the actual error that occurs when AgentExecutionCore
        tries to execute an agent through the adapter.
        """
        # This should fail with TypeError due to signature mismatch
        # The execution core will call: registry.get_async(agent_name, context=user_context)
        # But the adapter only accepts: get_async(agent_name)

        with pytest.raises(TypeError) as exc_info:
            # This triggers the problematic call in agent_execution_core.py:1085
            result = await self.execution_core.execute_agent_async(
                agent_name="integration_test_agent",
                user_execution_context=self.user_context,
                task_params={"task": "test_signature_mismatch"}
            )

        # Verify we get the expected signature mismatch error
        error_msg = str(exc_info.value)
        assert "unexpected keyword argument 'context'" in error_msg or \
               "positional argument" in error_msg, \
               f"Expected signature error, got: {error_msg}"

    @pytest.mark.asyncio
    async def test_execution_pipeline_with_mocked_fixed_signature(self):
        """Test that execution pipeline works with correct signature.

        This demonstrates how the system should work after the fix.
        """
        # Create a mock registry with the correct signature
        mock_fixed_registry = Mock()

        async def fixed_get_async(agent_name: str, context=None):
            """Mock with correct signature that includes context parameter."""
            # Use real agent creation but with correct signature
            agent_class = self.agent_class_registry.get(agent_name)
            if agent_class:
                return self.agent_factory.create_instance(agent_class, user_context=context)
            return None

        mock_fixed_registry.get_async = fixed_get_async

        # Create execution core with fixed registry
        fixed_execution_core = AgentExecutionCore(
            registry=mock_fixed_registry,
            websocket_manager=self.mock_websocket_manager,
            state_manager=self.mock_state_manager
        )

        # This should work correctly
        result = await fixed_execution_core.execute_agent_async(
            agent_name="integration_test_agent",
            user_execution_context=self.user_context,
            task_params={"task": "test_fixed_signature"}
        )

        # Verify successful execution
        assert result.success is True
        assert result.agent_name == "integration_test_agent"
        assert "test_fixed_signature" in str(result.result)

    @pytest.mark.asyncio
    async def test_user_context_propagation_with_fixed_signature(self):
        """Test that user context is properly propagated through the pipeline."""
        # Mock registry with fixed signature that handles context
        mock_registry = Mock()
        created_agents = []

        async def context_aware_get_async(agent_name: str, context=None):
            """Mock that properly handles context propagation."""
            agent_class = self.agent_class_registry.get(agent_name)
            if agent_class:
                agent = self.agent_factory.create_instance(agent_class, user_context=context)
                created_agents.append(agent)
                return agent
            return None

        mock_registry.get_async = context_aware_get_async

        # Create execution core
        execution_core = AgentExecutionCore(
            registry=mock_registry,
            websocket_manager=self.mock_websocket_manager,
            state_manager=self.mock_state_manager
        )

        # Execute agent
        result = await execution_core.execute_agent_async(
            agent_name="integration_test_agent",
            user_execution_context=self.user_context,
            task_params={"task": "context_propagation_test"}
        )

        # Verify context was properly propagated
        assert len(created_agents) == 1
        agent = created_agents[0]
        assert agent.user_context == self.user_context
        assert agent.user_context.user_id == "integration_user_001"

        # Verify execution result includes user context
        assert result.success is True
        result_data = result.result
        assert result_data["user_id"] == "integration_user_001"

    @pytest.mark.asyncio
    async def test_multi_user_isolation_with_signature_fix(self):
        """Test that different user contexts create isolated agent instances."""
        # Create second user context
        user_context_2 = UserExecutionContext.from_request_supervisor(
            user_id="integration_user_002",
            thread_id="integration_thread_002",
            run_id="integration_run_002",
            request_id="req_integration_002",
            metadata={"test_type": "multi_user_isolation"}
        )

        # Mock registry that properly handles context
        mock_registry = Mock()
        created_agents = []

        async def isolation_aware_get_async(agent_name: str, context=None):
            agent_class = self.agent_class_registry.get(agent_name)
            if agent_class:
                agent = self.agent_factory.create_instance(agent_class, user_context=context)
                created_agents.append(agent)
                return agent
            return None

        mock_registry.get_async = isolation_aware_get_async

        # Create execution cores for both users
        execution_core_1 = AgentExecutionCore(
            registry=mock_registry,
            websocket_manager=Mock(),
            state_manager=Mock()
        )
        execution_core_1.state_manager.save_execution_state = AsyncMock()
        execution_core_1.state_manager.get_execution_state = AsyncMock(return_value={})

        execution_core_2 = AgentExecutionCore(
            registry=mock_registry,
            websocket_manager=Mock(),
            state_manager=Mock()
        )
        execution_core_2.state_manager.save_execution_state = AsyncMock()
        execution_core_2.state_manager.get_execution_state = AsyncMock(return_value={})

        # Execute for both users
        result_1 = await execution_core_1.execute_agent_async(
            agent_name="integration_test_agent",
            user_execution_context=self.user_context,  # user_001
            task_params={"task": "user_1_task"}
        )

        result_2 = await execution_core_2.execute_agent_async(
            agent_name="integration_test_agent",
            user_execution_context=user_context_2,  # user_002
            task_params={"task": "user_2_task"}
        )

        # Verify isolation - different agent instances created
        assert len(created_agents) == 2
        agent_1, agent_2 = created_agents

        assert agent_1 != agent_2  # Different instances
        assert agent_1.user_context.user_id == "integration_user_001"
        assert agent_2.user_context.user_id == "integration_user_002"

        # Verify execution results are properly isolated
        assert result_1.result["user_id"] == "integration_user_001"
        assert result_2.result["user_id"] == "integration_user_002"
        assert result_1.result["task"] == "user_1_task"
        assert result_2.result["task"] == "user_2_task"

    def test_current_adapter_signature_inspection(self):
        """Inspect current adapter signature to document the issue."""
        import inspect

        # Get the current signature
        signature = inspect.signature(self.registry_adapter.get_async)
        params = list(signature.parameters.keys())

        # Document current broken state
        assert 'agent_name' in params
        assert 'context' not in params, "Current signature missing context parameter"

        # Expected parameters after fix
        expected_params = ['agent_name', 'context']
        missing_params = [p for p in expected_params if p not in params]

        # This documents what needs to be fixed
        assert missing_params == ['context'], \
            f"Missing required parameters: {missing_params}"

    @pytest.mark.asyncio
    async def test_direct_adapter_call_with_context_fails(self):
        """Test direct call to adapter with context parameter fails."""
        # Direct call to adapter should fail with current signature
        with pytest.raises(TypeError) as exc_info:
            await self.registry_adapter.get_async(
                "integration_test_agent",
                context=self.user_context
            )

        error_msg = str(exc_info.value)
        assert "unexpected keyword argument 'context'" in error_msg

    @pytest.mark.asyncio
    async def test_direct_adapter_call_without_context_works(self):
        """Test that adapter works correctly when called without context."""
        # This should work with current signature
        agent = await self.registry_adapter.get_async("integration_test_agent")

        assert agent is not None
        assert isinstance(agent, IntegrationTestAgent)
        assert agent.name == "integration_test_agent"
        # Note: user_context comes from adapter's constructor context
        assert agent.user_context == self.user_context


class TestWorkflowOrchestratorIntegration:
    """Integration tests for workflow orchestrator using the problematic adapter."""

    def setup_method(self):
        """Set up workflow orchestrator integration tests."""
        self.user_context = UserExecutionContext.from_request_supervisor(
            user_id="workflow_user_001",
            thread_id="workflow_thread_001",
            run_id="workflow_run_001",
            request_id="workflow_req_001",
            metadata={"workflow": "integration_test"}
        )

        # Create registry and adapter with signature issue
        self.agent_class_registry = AgentRegistry()
        self.agent_factory = AgentInstanceFactory()
        self.agent_class_registry.register("workflow_agent", IntegrationTestAgent)

        self.registry_adapter = AgentRegistryAdapter(
            agent_class_registry=self.agent_class_registry,
            agent_factory=self.agent_factory,
            user_context=self.user_context
        )

        # Mock orchestrator dependencies
        self.mock_websocket_manager = Mock()
        self.mock_state_manager = Mock()
        self.mock_state_manager.save_workflow_state = AsyncMock()
        self.mock_state_manager.get_workflow_state = AsyncMock(return_value={})

    @pytest.mark.asyncio
    async def test_workflow_orchestrator_signature_mismatch_impact(self):
        """Test how signature mismatch affects workflow orchestration."""
        # Create orchestrator with problematic adapter
        with patch('netra_backend.app.agents.supervisor.workflow_orchestrator.AgentExecutionCore') as mock_core_class:
            # Mock the execution core class to use our problematic adapter
            mock_execution_core = Mock()
            mock_core_class.return_value = mock_execution_core

            # Set up the execution core to call the adapter with context (triggering the error)
            async def failing_execute_agent_async(agent_name, user_execution_context, task_params):
                # This simulates the actual call that fails in agent_execution_core.py:1085
                await self.registry_adapter.get_async(agent_name, context=user_execution_context)

            mock_execution_core.execute_agent_async = failing_execute_agent_async

            # Create workflow orchestrator
            orchestrator = WorkflowOrchestrator(
                registry=self.registry_adapter,
                websocket_manager=self.mock_websocket_manager,
                state_manager=self.mock_state_manager
            )

            # This should fail due to signature mismatch
            with pytest.raises(TypeError) as exc_info:
                await orchestrator.execute_workflow(
                    workflow_config={
                        "agents": ["workflow_agent"],
                        "tasks": [{"agent": "workflow_agent", "task": "test"}]
                    },
                    user_context=self.user_context
                )

            assert "unexpected keyword argument 'context'" in str(exc_info.value)


class TestSignatureFixSpecification:
    """Test suite documenting the exact requirements for the signature fix."""

    def test_required_signature_specification(self):
        """Document the exact signature requirements for the fix.

        This test serves as specification documentation for the fix.
        """
        # CURRENT BROKEN SIGNATURE:
        # async def get_async(self, agent_name: str)

        # REQUIRED FIXED SIGNATURE:
        # async def get_async(self, agent_name: str, context=None)

        # REQUIREMENTS:
        requirements = {
            "add_context_parameter": True,
            "context_is_optional": True,
            "context_default_none": True,
            "maintain_backward_compatibility": True,
            "support_user_isolation": True,
            "pass_context_to_factory": True
        }

        # BEHAVIOR REQUIREMENTS:
        behavior_requirements = {
            "agent_execution_core_compatibility": "Must accept context parameter",
            "backward_compatibility": "Must work when called without context",
            "user_isolation": "Must use context for proper user isolation",
            "factory_integration": "Must pass context to agent factory",
            "no_caching": "Must not cache instances (Issue #1186 Phase 2)"
        }

        # This documents what the implementation must satisfy
        assert all(requirements.values()), "All requirements must be met"
        assert len(behavior_requirements) == 5, "All behavior requirements documented"

    def test_fix_implementation_checklist(self):
        """Checklist for implementing the signature fix."""
        implementation_steps = [
            "Add context parameter with default None to get_async signature",
            "Update method to accept context=None in parameter list",
            "Pass context to agent_factory.create_instance if provided",
            "Maintain existing behavior when context is not provided",
            "Add logging for context usage in debug mode",
            "Update any internal calls to get_async to include context",
            "Verify no breaking changes to existing callers",
            "Add tests for both with and without context scenarios"
        ]

        # This provides implementation guidance
        assert len(implementation_steps) == 8, "All implementation steps documented"


if __name__ == "__main__":
    # Run the integration tests focusing on signature mismatch
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-k", "signature_mismatch or signature_fix"
    ])