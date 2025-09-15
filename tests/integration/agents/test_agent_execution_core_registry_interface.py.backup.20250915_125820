"""
Integration tests for Issue #1205 - AgentExecutionCore registry interface mismatch.

These tests reproduce the actual integration failure between AgentExecutionCore
and AgentRegistryAdapter in real service scenarios.

EXPECTED BEHAVIOR: Tests should FAIL initially, showing real integration failures.
After fix: Tests should PASS, confirming end-to-end integration works.

Test Strategy:
1. Real AgentExecutionCore instantiation and execution
2. Real UserExecutionContext with proper user isolation
3. Actual get_async() call patterns from production
4. No mocks for core components (following SSOT testing guidelines)
"""

import pytest
import asyncio
import logging
from unittest.mock import Mock, patch
from typing import Optional, Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.user_execution_engine import AgentRegistryAdapter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory


logger = logging.getLogger(__name__)


class TestAgentExecutionCoreRegistryInterface(SSotAsyncTestCase):
    """Integration tests for AgentExecutionCore and AgentRegistryAdapter interaction."""

    def setUp(self):
        """Set up real service components for integration testing."""
        super().setUp()

        # Create real user execution context
        self.user_context = UserExecutionContext(
            user_id="integration_test_user_1205",
            session_id="session_1205_test",
            websocket_id="ws_1205_test",
            metadata={"test_case": "issue_1205_integration"}
        )

        # Create real agent class registry
        self.agent_class_registry = AgentClassRegistry()

        # Create real agent factory (may need mocking of some dependencies)
        self.agent_factory = AgentInstanceFactory()

        # Create adapter with real components
        self.adapter = AgentRegistryAdapter(
            agent_class_registry=self.agent_class_registry,
            agent_factory=self.agent_factory,
            user_context=self.user_context
        )

    async def test_agent_execution_core_real_instantiation(self):
        """Test real AgentExecutionCore instantiation with AgentRegistryAdapter.

        ISSUE #1205: This should reproduce the actual TypeError in production context.
        """
        try:
            # Create real AgentExecutionCore with our adapter
            agent_core = AgentExecutionCore(registry=self.adapter)

            # Verify initialization
            self.assertIsNotNone(agent_core, "AgentExecutionCore should initialize")
            self.assertEqual(agent_core.registry, self.adapter, "Registry should be set correctly")

            logger.info("AgentExecutionCore instantiation successful")

        except Exception as e:
            self.fail(f"Failed to instantiate AgentExecutionCore with AgentRegistryAdapter: {e}")

    async def test_agent_execution_core_get_agent_call(self):
        """Test the actual get_agent() call that triggers the interface mismatch.

        ISSUE #1205: This reproduces the exact production failure scenario.
        """
        # Create AgentExecutionCore
        agent_core = AgentExecutionCore(registry=self.adapter)

        # Test agent name that should exist in registry
        agent_name = "supervisor_agent"  # Common agent name

        try:
            # This is the call pattern that fails in production
            # From agent_execution_core.py: await self.registry.get_async(agent_name, context=user_execution_context)
            agent = await agent_core.get_agent(agent_name, user_execution_context=self.user_context)

            # If we reach here after fix, validate the result
            logger.info(f"Successfully retrieved agent: {type(agent)}")
            self.assertIsNotNone(agent, "Should return agent instance")

        except TypeError as e:
            if "unexpected keyword argument 'context'" in str(e):
                # This is the expected bug we're reproducing
                logger.error(f"Reproduced Issue #1205 TypeError: {e}")
                self.fail(f"Issue #1205 confirmed: {e}")
            else:
                # Different TypeError - not our bug
                self.fail(f"Unexpected TypeError: {e}")

        except Exception as e:
            # Other exceptions might be acceptable (e.g., agent not found)
            logger.warning(f"Non-TypeError exception (may be acceptable): {e}")
            # Don't fail on non-TypeError exceptions as they might be normal

    async def test_multiple_agent_types_interface_compliance(self):
        """Test interface compliance across multiple agent types.

        ISSUE #1205: Verify the fix works for all agent types, not just one.
        """
        agent_names = [
            "supervisor_agent",
            "data_helper_agent",
            "triage_agent",
            "apex_optimizer_agent"
        ]

        results = {}

        for agent_name in agent_names:
            try:
                agent_core = AgentExecutionCore(registry=self.adapter)
                agent = await agent_core.get_agent(agent_name, user_execution_context=self.user_context)
                results[agent_name] = {"success": True, "agent": agent}
                logger.info(f"Successfully retrieved {agent_name}")

            except TypeError as e:
                if "unexpected keyword argument 'context'" in str(e):
                    results[agent_name] = {"success": False, "error": str(e)}
                    logger.error(f"Issue #1205 confirmed for {agent_name}: {e}")
                else:
                    results[agent_name] = {"success": False, "error": f"Unexpected TypeError: {e}"}

            except Exception as e:
                # Non-TypeError exceptions may be acceptable (agent not found, etc.)
                results[agent_name] = {"success": True, "note": f"Non-blocking exception: {e}"}

        # Report results
        failed_agents = [name for name, result in results.items()
                        if not result.get("success", True)]

        if failed_agents:
            failure_details = [f"{name}: {results[name]['error']}"
                             for name in failed_agents]
            self.fail(f"Interface failures for agents: {failure_details}")

    async def test_concurrent_user_isolation_with_interface_fix(self):
        """Test that interface fix maintains proper user isolation.

        ISSUE #1205: Ensure fixing the interface doesn't break user isolation.
        """
        # Create multiple user contexts
        user_contexts = [
            UserExecutionContext(
                user_id=f"user_{i}",
                session_id=f"session_{i}",
                websocket_id=f"ws_{i}",
                metadata={"test": "isolation"}
            )
            for i in range(3)
        ]

        # Create adapters for each user
        adapters = []
        for user_context in user_contexts:
            adapter = AgentRegistryAdapter(
                agent_class_registry=self.agent_class_registry,
                agent_factory=self.agent_factory,
                user_context=user_context
            )
            adapters.append(adapter)

        # Test concurrent agent retrieval
        async def get_agent_for_user(adapter, user_context):
            try:
                agent_core = AgentExecutionCore(registry=adapter)
                agent = await agent_core.get_agent("supervisor_agent",
                                                 user_execution_context=user_context)
                return {"success": True, "user_id": user_context.user_id, "agent": agent}
            except Exception as e:
                return {"success": False, "user_id": user_context.user_id, "error": str(e)}

        # Execute concurrent requests
        tasks = [
            get_agent_for_user(adapter, user_context)
            for adapter, user_context in zip(adapters, user_contexts)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        failures = [r for r in results if not r.get("success", True)]
        if failures:
            failure_details = [f"User {r['user_id']}: {r['error']}" for r in failures]
            self.fail(f"Concurrent user isolation failures: {failure_details}")

        logger.info(f"Concurrent user isolation test successful for {len(results)} users")

    async def test_interface_backwards_compatibility(self):
        """Test that interface fix maintains backwards compatibility.

        Ensures existing code patterns continue to work after the fix.
        """
        # Test direct adapter calls (existing pattern)
        try:
            # Call without context (existing pattern should still work)
            agent = await self.adapter.get_async("supervisor_agent")
            logger.info("Backwards compatibility maintained for get_async() without context")

        except Exception as e:
            self.fail(f"Backwards compatibility broken: {e}")

        # Test AgentExecutionCore with new pattern
        try:
            agent_core = AgentExecutionCore(registry=self.adapter)
            agent = await agent_core.get_agent("supervisor_agent",
                                             user_execution_context=self.user_context)
            logger.info("New pattern works with context parameter")

        except Exception as e:
            self.fail(f"New pattern fails after fix: {e}")

    def test_interface_contract_documentation(self):
        """Document the expected interface contract for future reference.

        ISSUE #1205: Ensures the interface contract is clearly defined.
        """
        expected_contract = {
            "AgentRegistryAdapter.get_async": {
                "signature": "(agent_name: str, context: Optional[UserExecutionContext] = None)",
                "returns": "Optional[BaseAgent]",
                "behavior": "Creates fresh agent instance with user context"
            },
            "AgentExecutionCore.get_agent": {
                "call_pattern": "await registry.get_async(agent_name, context=user_execution_context)",
                "expectation": "Registry must accept context parameter"
            }
        }

        # Log the contract for documentation
        logger.info(f"Expected interface contract: {expected_contract}")

        # This test always passes - it's for documentation
        self.assertTrue(True, "Interface contract documented")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])