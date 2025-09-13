"""
AgentInstanceFactory DataHelper Creation Test - SSOT Compliance

This test validates AgentInstanceFactory ability to create DataHelper agent instances
with proper SSOT compliance and dependency injection patterns.

EXPECTED BEHAVIOR:
- FAIL before fix: Import violations prevent proper factory creation
- PASS after fix: Factory can create DataHelper with SSOT dependencies

Business Value: Ensures $500K+ ARR Golden Path can create DataHelper agents reliably
"""

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment

class TestAgentFactoryDataHelperSSot(SSotAsyncTestCase):
    """Test AgentInstanceFactory ability to create DataHelper agent with SSOT compliance."""

    def setup_method(self, method):
        """Setup test environment with factory dependencies."""
        super().setup_method(method)
        self.env = IsolatedEnvironment()

        # Test data
        self.user_id = "test_user_001"
        self.thread_id = f"thread_{uuid.uuid4()}"
        self.run_id = f"run_{uuid.uuid4()}"
        self.request_id = f"req_{uuid.uuid4()}"

    async def test_agent_factory_datahelper_creation_EXPECT_FAILURE(self):
        """
        EXPECTED FAILURE: AgentInstanceFactory fails to create DataHelper due to SSOT violation.

        Before fix: Import violations break dependency injection
        After fix: Factory successfully creates DataHelper agent
        """
        try:
            # Import factory and dependencies
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge

            # Create mock dependencies
            mock_websocket_bridge = self._create_mock_websocket_bridge()
            mock_llm_manager = self._create_mock_llm_manager()

            # Configure factory with minimal dependencies
            factory = AgentInstanceFactory()
            factory.configure(
                websocket_bridge=mock_websocket_bridge,
                llm_manager=mock_llm_manager
            )

            # Create user execution context
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id,
                request_id=self.request_id,
                metadata={"test_mode": True}
            )

            # CRITICAL TEST: Attempt to create DataHelper agent
            # This MUST FAIL before fix due to SSOT import violation
            agent = await factory.create_agent_instance(
                agent_name="DataHelperAgent",
                user_context=user_context
            )

            # If we reach here, creation succeeded (after fix)
            self.assertIsNotNone(agent, "DataHelper agent creation should succeed after SSOT fix")

            # Validate agent type
            self.assertEqual(
                agent.__class__.__name__, "DataHelperAgent",
                f"Expected DataHelperAgent, got {agent.__class__.__name__}"
            )

            # Validate agent has required dependencies
            self.assertTrue(
                hasattr(agent, 'llm_manager'),
                "DataHelper agent must have llm_manager after factory creation"
            )

            # Validate WebSocket integration works
            if hasattr(agent, '_websocket_adapter'):
                self.assertIsNotNone(
                    agent._websocket_adapter,
                    "DataHelper agent must have WebSocket adapter for event emission"
                )

        except ImportError as e:
            self.fail(f"Cannot import required dependencies for factory test: {e}")

        except Exception as e:
            # Before fix: This exception indicates SSOT violation
            # After fix: This should not happen
            violation_indicators = [
                "import", "module", "UnifiedToolDispatcher", "tool_dispatcher",
                "factory", "dependency", "injection"
            ]

            if any(indicator in str(e).lower() for indicator in violation_indicators):
                self.fail(
                    f"SSOT VIOLATION DETECTED: Factory failed to create DataHelper agent. "
                    f"Error: {e}. This indicates import path issues preventing proper "
                    f"dependency injection in AgentInstanceFactory."
                )
            else:
                # Re-raise unexpected errors
                raise

    async def test_datahelper_factory_method_direct_call(self):
        """
        Test DataHelper factory method can be called directly with proper dependencies.

        This validates the agent's own factory method works with SSOT imports.
        """
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create user context
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id,
                request_id=self.request_id,
                metadata={"direct_call_test": True}
            )

            # Mock LLM manager for context
            mock_llm_manager = self._create_mock_llm_manager()
            user_context.set_dependency('llm_manager', mock_llm_manager)

            # CRITICAL: Call agent's factory method directly
            # This will fail if SSOT imports are broken
            agent = DataHelperAgent.create_agent_with_context(user_context)

            self.assertIsNotNone(agent, "DataHelper factory method should create agent")
            self.assertEqual(
                agent.__class__.__name__, "DataHelperAgent",
                f"Factory method should return DataHelperAgent, got {agent.__class__.__name__}"
            )

            # Validate dependencies were injected
            self.assertIsNotNone(
                getattr(agent, 'llm_manager', None),
                "DataHelper agent should have llm_manager after factory creation"
            )

        except ImportError as e:
            if "tool_dispatcher" in str(e) or "UnifiedToolDispatcher" in str(e):
                self.fail(
                    f"SSOT IMPORT VIOLATION: Cannot import DataHelper due to tool dispatcher "
                    f"import issues: {e}. This indicates facade import instead of SSOT."
                )
            else:
                self.fail(f"Import error in DataHelper factory test: {e}")

        except Exception as e:
            self.fail(f"DataHelper factory method failed: {e}")

    async def test_datahelper_tool_dispatcher_dependency_injection(self):
        """
        Test that DataHelper agent can receive tool dispatcher via proper SSOT channels.

        This validates the fix enables proper dependency flow.
        """
        try:
            from netra_backend.app.agents.data_helper_agent import DataHelperAgent
            from netra_backend.app.services.user_execution_context import UserExecutionContext
            from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory

            # Create user context
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id,
                request_id=self.request_id,
                metadata={"dependency_test": True}
            )

            # Create SSOT tool dispatcher
            mock_tool_dispatcher = await self._create_mock_tool_dispatcher_ssot(user_context)

            # Inject dependencies into context
            mock_llm_manager = self._create_mock_llm_manager()
            user_context.set_dependency('llm_manager', mock_llm_manager)
            user_context.set_dependency('tool_dispatcher', mock_tool_dispatcher)

            # Create agent with dependencies
            agent = DataHelperAgent.create_agent_with_context(user_context)

            # Validate tool dispatcher injection
            self.assertIsNotNone(
                getattr(agent, 'tool_dispatcher', None),
                "DataHelper should have tool_dispatcher after SSOT dependency injection"
            )

            # Validate tool dispatcher type (should be from SSOT)
            tool_dispatcher = getattr(agent, 'tool_dispatcher', None)
            if tool_dispatcher:
                # Check it's the SSOT implementation
                dispatcher_module = tool_dispatcher.__class__.__module__
                self.assertIn(
                    'core.tools', dispatcher_module,
                    f"Tool dispatcher should be from SSOT core.tools module, got {dispatcher_module}"
                )

        except ImportError as e:
            self.fail(f"SSOT tool dispatcher import failed: {e}")

        except Exception as e:
            self.fail(f"Tool dispatcher dependency injection test failed: {e}")

    async def test_datahelper_websocket_integration_after_ssot_fix(self):
        """
        Test that DataHelper agent WebSocket integration works after SSOT compliance fix.

        This ensures the fix doesn't break WebSocket event emission.
        """
        try:
            from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
            from netra_backend.app.services.user_execution_context import UserExecutionContext

            # Create factory with WebSocket bridge
            factory = AgentInstanceFactory()
            mock_websocket_bridge = self._create_mock_websocket_bridge()
            mock_llm_manager = self._create_mock_llm_manager()

            factory.configure(
                websocket_bridge=mock_websocket_bridge,
                llm_manager=mock_llm_manager
            )

            # Create user context
            user_context = UserExecutionContext.from_request_supervisor(
                user_id=self.user_id,
                thread_id=self.thread_id,
                run_id=self.run_id,
                request_id=self.request_id,
                metadata={"websocket_test": True}
            )

            # Create agent via factory
            agent = await factory.create_agent_instance(
                agent_name="DataHelperAgent",
                user_context=user_context
            )

            # Test WebSocket event emission
            if hasattr(agent, 'emit_thinking'):
                # This should not raise exceptions
                await agent.emit_thinking("Testing WebSocket integration after SSOT fix")

            # Verify WebSocket bridge received events
            mock_websocket_bridge.notify_agent_thinking.assert_called()

        except Exception as e:
            self.fail(f"WebSocket integration test failed after SSOT fix: {e}")

    def _create_mock_websocket_bridge(self) -> AsyncMock:
        """Create mock WebSocket bridge for testing."""
        mock_bridge = AsyncMock()

        # Configure return values for WebSocket methods
        mock_bridge.notify_agent_started = AsyncMock(return_value=True)
        mock_bridge.notify_agent_thinking = AsyncMock(return_value=True)
        mock_bridge.notify_tool_executing = AsyncMock(return_value=True)
        mock_bridge.notify_tool_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_completed = AsyncMock(return_value=True)
        mock_bridge.notify_agent_error = AsyncMock(return_value=True)

        return mock_bridge

    def _create_mock_llm_manager(self) -> MagicMock:
        """Create mock LLM manager for testing."""
        mock_llm = MagicMock()
        mock_llm.model_name = "test-model"
        mock_llm.configured = True
        return mock_llm

    async def _create_mock_tool_dispatcher_ssot(self, user_context) -> AsyncMock:
        """Create mock SSOT tool dispatcher for testing."""
        mock_dispatcher = AsyncMock()
        mock_dispatcher.user_context = user_context
        mock_dispatcher.__class__.__module__ = "netra_backend.app.core.tools.unified_tool_dispatcher"
        return mock_dispatcher

    async def teardown_method(self, method):
        """Cleanup test environment."""
        await super().teardown_method(method)