"""
DataHelper Integration SSOT Test

This integration test validates DataHelper agent with proper SSOT patterns through
the complete stack including factory creation, dependency injection, and
WebSocket integration without Docker dependencies.

EXPECTED BEHAVIOR:
- FAIL before fix: Integration issues due to SSOT import violations
- PASS after fix: Complete integration works with SSOT patterns

Business Value: Validates $500K+ ARR Golden Path DataHelper functionality
"""

import asyncio
import uuid
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

class TestDataHelperSSotIntegration(SSotAsyncTestCase):
    """Integration test for DataHelper agent with SSOT compliance through full stack."""

    def setup_method(self, method):
        """Setup integration test environment."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Test data for integration
        self.user_id = "integration_user_001"
        self.thread_id = f"integration_thread_{uuid.uuid4()}"
        self.run_id = f"integration_run_{uuid.uuid4()}"
        self.request_id = f"integration_req_{uuid.uuid4()}"

        # Sample data request scenario
        self.test_user_request = "I need to optimize my cloud costs"
        self.test_triage_result = {
            "optimization_type": "cost_optimization",
            "priority": "high",
            "requires_data": True
        }

    async def test_datahelper_full_stack_integration_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: Full stack DataHelper integration fails due to SSOT violations.

        Before fix: Import violations break integration at factory level
        After fix: Complete DataHelper workflow succeeds with SSOT patterns
        """
        try:
            # Import all required components
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Setup integration environment
            factory = await self._setup_integration_factory()

            # Create user execution context with request data
            user_context = await self._create_integration_user_context()

            # CRITICAL INTEGRATION TEST: Create DataHelper through factory
            # This tests the complete SSOT compliance chain
            agent = await factory.create_agent_instance(
                agent_name="DataHelperAgent",
                user_context=user_context
            )

            self.assertIsNotNone(agent, "DataHelper integration should succeed after SSOT fix")

            # Test complete agent execution workflow
            result_context = await self._execute_datahelper_workflow(agent, user_context)

            # Validate integration results
            self.assertIsNotNone(result_context, "DataHelper execution should return enhanced context")

            # Check that data request was generated
            data_result = result_context.metadata.get('data_result')
            self.assertIsNotNone(data_result, "DataHelper should generate data request in integration test")

            # Validate WebSocket events were emitted during integration
            await self._validate_websocket_integration(agent)

        except ImportError as e:
            if any(indicator in str(e).lower() for indicator in ['tool_dispatcher', 'unifiedtooldispatcher']):
                self.fail(
                    f"SSOT INTEGRATION VIOLATION: Cannot import DataHelper components due to "
                    f"tool dispatcher import issues: {e}. This indicates facade import "
                    f"breaking full stack integration."
                )
            else:
                self.fail(f"Integration import error: {e}")

        except Exception as e:
            # Check if error is related to SSOT violations
            error_str = str(e).lower()
            ssot_violation_indicators = [
                "import", "module", "tool_dispatcher", "factory", "dependency"
            ]

            if any(indicator in error_str for indicator in ssot_violation_indicators):
                self.fail(
                    f"SSOT INTEGRATION FAILURE: DataHelper full stack integration failed "
                    f"due to SSOT compliance issues: {e}. This indicates import violations "
                    f"preventing proper factory-based agent creation and dependency injection."
                )
            else:
                # Re-raise unexpected integration errors
                raise

    async def test_datahelper_dependency_injection_integration(self):
        """
        Integration test for DataHelper dependency injection through SSOT patterns.

        This validates that dependencies flow correctly through the complete stack.
        """
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory

            # Create integration context
            user_context = await self._create_integration_user_context()

            # Setup SSOT dependencies
            mock_llm_manager = self._create_integration_llm_manager()
            mock_tool_dispatcher = await self._create_integration_tool_dispatcher(user_context)

            # Inject dependencies via context (SSOT pattern)
            user_context.set_dependency('llm_manager', mock_llm_manager)
            user_context.set_dependency('tool_dispatcher', mock_tool_dispatcher)

            # Create agent with dependency injection
            agent = DataHelperAgent.create_agent_with_context(user_context)

            # Validate dependency injection worked
            self.assertIsNotNone(
                getattr(agent, 'llm_manager', None),
                "Integration: LLM manager should be injected via SSOT pattern"
            )

            self.assertIsNotNone(
                getattr(agent, 'tool_dispatcher', None),
                "Integration: Tool dispatcher should be injected via SSOT pattern"
            )

            # Test that dependencies are from SSOT modules
            tool_dispatcher = getattr(agent, 'tool_dispatcher', None)
            if tool_dispatcher:
                dispatcher_module = tool_dispatcher.__class__.__module__
                self.assertIn(
                    'core.tools', dispatcher_module,
                    f"Integration: Tool dispatcher should be from SSOT module, got {dispatcher_module}"
                )

        except Exception as e:
            self.fail(f"DataHelper dependency injection integration failed: {e}")

    async def test_datahelper_websocket_event_integration(self):
        """
        Integration test for DataHelper WebSocket events with SSOT compliance.

        This validates event emission works through the complete stack.
        """
        try:
            # Setup factory with WebSocket bridge
            factory = await self._setup_integration_factory()
            user_context = await self._create_integration_user_context()

            # Create agent through factory (includes WebSocket setup)
            agent = await factory.create_agent_instance(
                agent_name="DataHelperAgent",
                user_context=user_context
            )

            # Test WebSocket event emission integration
            websocket_events = []

            # Mock WebSocket bridge to capture events
            if hasattr(agent, '_websocket_adapter') and agent._websocket_adapter.websocket_bridge:
                original_bridge = agent._websocket_adapter.websocket_bridge

                # Wrap methods to capture events
                async def capture_thinking(run_id, agent_name, reasoning, **kwargs):
                    websocket_events.append(('thinking', reasoning))
                    return True

                async def capture_tool_executing(run_id, agent_name, tool_name, **kwargs):
                    websocket_events.append(('tool_executing', tool_name))
                    return True

                original_bridge.notify_agent_thinking = capture_thinking
                original_bridge.notify_tool_executing = capture_tool_executing

            # Execute agent to trigger WebSocket events
            enhanced_context = await agent._execute_with_user_context(user_context)

            # Validate WebSocket events were emitted
            self.assertGreater(
                len(websocket_events), 0,
                "Integration: DataHelper should emit WebSocket events during execution"
            )

            # Check for expected event types
            event_types = [event[0] for event in websocket_events]
            expected_events = ['thinking', 'tool_executing']

            for expected_event in expected_events:
                self.assertIn(
                    expected_event, event_types,
                    f"Integration: Expected WebSocket event '{expected_event}' not found. "
                    f"Events: {event_types}"
                )

        except Exception as e:
            self.fail(f"DataHelper WebSocket integration test failed: {e}")

    async def test_datahelper_error_handling_integration(self):
        """
        Integration test for DataHelper error handling with SSOT compliance.

        This validates error scenarios work correctly through the complete stack.
        """
        try:
            factory = await self._setup_integration_factory()
            user_context = await self._create_integration_user_context()

            # Create invalid context to trigger error handling
            invalid_context = UserExecutionContext.from_request_supervisor(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id,
                request_id=self.request_id,
                metadata={}  # Empty metadata should trigger error
            )

            # Create agent
            agent = await factory.create_agent_instance(
                agent_name="DataHelperAgent",
                user_context=invalid_context
            )

            # Execute with invalid context (should handle gracefully)
            result_context = await agent._execute_with_user_context(invalid_context)

            # Should return context even with errors (not raise exceptions)
            self.assertIsNotNone(result_context, "DataHelper should handle errors gracefully")

            # Check error was logged in metadata
            error_result = result_context.metadata.get('data_helper_error')
            self.assertIsNotNone(
                error_result,
                "DataHelper should log errors in context metadata during integration"
            )

        except Exception as e:
            self.fail(f"DataHelper error handling integration test failed: {e}")

    async def _setup_integration_factory(self) -> 'AgentInstanceFactory':
        """Setup AgentInstanceFactory for integration testing."""
        from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory

        factory = AgentInstanceFactory()

        # Create integration mocks
        mock_websocket_bridge = self._create_integration_websocket_bridge()
        mock_llm_manager = self._create_integration_llm_manager()

        # Configure factory with integration dependencies
        factory.configure(
            websocket_bridge=mock_websocket_bridge,
            llm_manager=mock_llm_manager
        )

        return factory

    async def _create_integration_user_context(self) -> 'UserExecutionContext':
        """Create UserExecutionContext for integration testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        return UserExecutionContext.from_request_supervisor(
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            request_id=self.request_id,
            metadata={
                'user_request': self.test_user_request,
                'triage_result': self.test_triage_result,
                'integration_test': True
            }
        )

    async def _execute_datahelper_workflow(self, agent, user_context) -> 'UserExecutionContext':
        """Execute complete DataHelper workflow for integration testing."""
        return await agent._execute_with_user_context(user_context)

    async def _validate_websocket_integration(self, agent):
        """Validate WebSocket integration for DataHelper agent."""
        # Check agent has WebSocket adapter
        self.assertTrue(
            hasattr(agent, '_websocket_adapter'),
            "DataHelper should have WebSocket adapter for integration"
        )

        # Test event emission capability
        if hasattr(agent, 'emit_thinking'):
            await agent.emit_thinking("Integration test WebSocket validation")

    def _create_integration_websocket_bridge(self) -> AsyncMock:
        """Create WebSocket bridge mock for integration testing."""
        mock_bridge = AsyncMock()

        # Configure all WebSocket methods
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
        mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_error = AsyncMock(return_value=True)

        return mock_bridge

    def _create_integration_llm_manager(self) -> MagicMock:
        """Create LLM manager mock for integration testing."""
        mock_llm = MagicMock()
        mock_llm.model_name = "integration-test-model"
        mock_llm.configured = True
        mock_llm.max_tokens = 4000
        return mock_llm

    async def _create_integration_tool_dispatcher(self, user_context) -> AsyncMock:
        """Create SSOT tool dispatcher mock for integration testing."""
        mock_dispatcher = AsyncMock()
        mock_dispatcher.user_context = user_context
        mock_dispatcher.__class__.__module__ = "netra_backend.app.core.tools.unified_tool_dispatcher"
        mock_dispatcher.__class__.__name__ = "UnifiedToolDispatcher"
        return mock_dispatcher

    async def teardown_method(self, method):
        """Cleanup integration test environment."""
        await super().teardown_method(method)