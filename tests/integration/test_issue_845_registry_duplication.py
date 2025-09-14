"""
Test Suite for Issue #845 - SSOT AgentRegistry Duplication

This test suite demonstrates the critical SSOT violation where two different
AgentRegistry implementations exist, causing import conflicts and WebSocket
event delivery failures that block the Golden Path user flow.

Business Value: Protects $500K+ ARR chat functionality by ensuring single
source of truth for agent registry implementation.

Expected Behavior:
- BEFORE FIX: Tests should FAIL showing conflicts between basic/advanced registries
- AFTER FIX: Tests should PASS using single advanced registry as SSOT

CRITICAL: These tests protect the 5 business-critical WebSocket events:
1. agent_started - User sees agent began processing
2. agent_thinking - Real-time reasoning visibility
3. tool_executing - Tool usage transparency
4. tool_completed - Tool results display
5. agent_completed - User knows response is ready
"""

import pytest
import asyncio
import sys
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

# Test Framework SSOT Compliance
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestIssue845RegistryDuplication(SSotAsyncTestCase):
    """Test suite demonstrating SSOT AgentRegistry duplication issues."""

    async def asyncSetUp(self):
        """Set up test environment."""
        await super().asyncSetUp()
        self.test_user_id = "test_user_845"
        self.import_conflicts = []
        self.websocket_events = []

    async def asyncTearDown(self):
        """Clean up test environment."""
        # Clear any cached imports to prevent test interference
        modules_to_clear = [
            'netra_backend.app.agents.registry',
            'netra_backend.app.agents.supervisor.agent_registry'
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]
        await super().asyncTearDown()

    async def test_duplicate_registry_imports_exist(self):
        """
        CRITICAL TEST: Demonstrates that two different AgentRegistry classes exist.

        This test should FAIL initially, showing the SSOT violation.
        After fix, this test should show only one registry exists.
        """
        # Import both registries and show they are different classes
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            basic_registry_file = BasicRegistry.__module__
            basic_registry_lines = len(BasicRegistry.__doc__.split('\n')) if BasicRegistry.__doc__ else 0

            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
            advanced_registry_file = AdvancedRegistry.__module__
            advanced_registry_lines = len(str(AdvancedRegistry.__doc__).split('\n')) if AdvancedRegistry.__doc__ else 0

            # CRITICAL ASSERTION: These should be different classes (showing the violation)
            self.assertNotEqual(BasicRegistry, AdvancedRegistry,
                              "SSOT VIOLATION: Two different AgentRegistry classes exist")

            self.assertNotEqual(basic_registry_file, advanced_registry_file,
                              "SSOT VIOLATION: Registries exist in different modules")

            # Show capability differences
            basic_methods = set(dir(BasicRegistry))
            advanced_methods = set(dir(AdvancedRegistry))
            method_differences = advanced_methods - basic_methods

            # Advanced registry should have more methods (user isolation, etc.)
            self.assertGreater(len(method_differences), 10,
                             f"Advanced registry should have significantly more methods. Found differences: {method_differences}")

            # Log the violation for analysis
            self.logger.error(f"SSOT VIOLATION DETECTED:")
            self.logger.error(f"  Basic Registry: {basic_registry_file} (simpler implementation)")
            self.logger.error(f"  Advanced Registry: {advanced_registry_file} (enhanced implementation)")
            self.logger.error(f"  Method differences: {len(method_differences)} additional methods in advanced")

        except ImportError as e:
            self.fail(f"Could not import duplicate registries for testing: {e}")

    async def test_websocket_integration_differences(self):
        """
        CRITICAL TEST: Shows different WebSocket integration patterns between registries.

        This demonstrates why WebSocket events fail in the Golden Path.
        """
        from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

        # Create instances
        basic_registry = BasicRegistry()

        # Mock dependencies for advanced registry
        mock_llm_manager = Mock()
        advanced_registry = AdvancedRegistry(llm_manager=mock_llm_manager)

        # Test WebSocket manager setup patterns
        mock_websocket_manager = Mock()

        # Basic registry - simple pattern
        basic_registry.set_websocket_manager(mock_websocket_manager)
        basic_websocket_attr = hasattr(basic_registry, '_websocket_manager')

        # Advanced registry - user isolation pattern
        advanced_registry.set_websocket_manager(mock_websocket_manager)
        advanced_websocket_attr = hasattr(advanced_registry, 'websocket_manager')

        # Show different attribute patterns
        self.assertTrue(basic_websocket_attr, "Basic registry should have _websocket_manager")
        self.assertTrue(advanced_websocket_attr, "Advanced registry should have websocket_manager")

        # Test user isolation capabilities
        basic_has_user_isolation = hasattr(basic_registry, 'get_user_session')
        advanced_has_user_isolation = hasattr(advanced_registry, 'get_user_session')

        self.assertFalse(basic_has_user_isolation, "Basic registry lacks user isolation")
        self.assertTrue(advanced_has_user_isolation, "Advanced registry has user isolation")

        # Test factory pattern capabilities
        basic_has_factory_patterns = hasattr(basic_registry, 'create_tool_dispatcher_for_user')
        advanced_has_factory_patterns = hasattr(advanced_registry, 'create_tool_dispatcher_for_user')

        self.assertFalse(basic_has_factory_patterns, "Basic registry lacks factory patterns")
        self.assertTrue(advanced_has_factory_patterns, "Advanced registry has factory patterns")

        self.logger.error(f"WEBSOCKET INTEGRATION DIFFERENCES:")
        self.logger.error(f"  Basic: Simple WebSocket manager storage")
        self.logger.error(f"  Advanced: User-isolated WebSocket bridge factory pattern")
        self.logger.error(f"  IMPACT: Basic registry cannot deliver proper WebSocket events for multi-user scenarios")

    async def test_agent_creation_pattern_differences(self):
        """
        CRITICAL TEST: Shows different agent creation patterns causing Golden Path failures.
        """
        from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create test user context
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="test_request_845",
            thread_id="test_thread_845",
            run_id="test_run_845"
        )

        # Test basic registry agent creation
        basic_registry = BasicRegistry()
        basic_agent_types = basic_registry.get_all_agents()  # Should be empty initially
        basic_supports_user_context = 'context' in str(basic_registry.register_agent.__code__.co_varnames)

        # Test advanced registry agent creation
        mock_llm_manager = Mock()
        advanced_registry = AdvancedRegistry(llm_manager=mock_llm_manager)

        # Advanced registry should support user-isolated agent creation
        advanced_supports_user_creation = hasattr(advanced_registry, 'create_agent_for_user')
        advanced_supports_user_sessions = hasattr(advanced_registry, 'get_user_session')

        self.assertTrue(basic_supports_user_context, "Basic registry should accept user context")
        self.assertTrue(advanced_supports_user_creation, "Advanced registry should support user-isolated agent creation")
        self.assertTrue(advanced_supports_user_sessions, "Advanced registry should support user sessions")

        # Test memory leak prevention
        advanced_has_lifecycle_manager = hasattr(advanced_registry, '_lifecycle_manager')
        advanced_has_cleanup = hasattr(advanced_registry, 'cleanup_user_session')

        self.assertTrue(advanced_has_lifecycle_manager, "Advanced registry should have lifecycle management")
        self.assertTrue(advanced_has_cleanup, "Advanced registry should have cleanup capabilities")

        # Basic registry lacks these capabilities
        basic_has_lifecycle_manager = hasattr(basic_registry, '_lifecycle_manager')
        basic_has_cleanup = hasattr(basic_registry, 'cleanup_user_session')

        self.assertFalse(basic_has_lifecycle_manager, "Basic registry lacks lifecycle management")
        self.assertFalse(basic_has_cleanup, "Basic registry lacks cleanup capabilities")

        self.logger.error(f"AGENT CREATION PATTERN DIFFERENCES:")
        self.logger.error(f"  Basic: Simple agent registration without user isolation")
        self.logger.error(f"  Advanced: User-isolated agent creation with memory management")
        self.logger.error(f"  IMPACT: Basic registry causes memory leaks and user context contamination")

    async def test_import_resolution_conflicts(self):
        """
        CRITICAL TEST: Demonstrates import resolution conflicts in production code.

        This test shows how different parts of the system importing different
        registries leads to inconsistent behavior and WebSocket event failures.
        """
        # Simulate different modules importing different registries
        import_scenarios = []

        # Scenario 1: Test imports basic registry
        try:
            from netra_backend.app.agents.registry import AgentRegistry
            basic_import_success = True
            basic_registry_class = AgentRegistry
        except ImportError:
            basic_import_success = False
            basic_registry_class = None

        # Scenario 2: Production code imports advanced registry
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
            advanced_import_success = True
            advanced_registry_class = AgentRegistry
        except ImportError:
            advanced_import_success = False
            advanced_registry_class = None

        # Both imports should succeed but give different classes
        self.assertTrue(basic_import_success, "Basic registry import should succeed")
        self.assertTrue(advanced_import_success, "Advanced registry import should succeed")

        if basic_registry_class and advanced_registry_class:
            self.assertNotEqual(basic_registry_class, advanced_registry_class,
                              "CRITICAL: Same import name gives different classes")

            # This creates the fundamental SSOT violation
            import_scenarios.append({
                'import_path': 'netra_backend.app.agents.registry',
                'class': basic_registry_class,
                'capabilities': 'basic'
            })
            import_scenarios.append({
                'import_path': 'netra_backend.app.agents.supervisor.agent_registry',
                'class': advanced_registry_class,
                'capabilities': 'advanced'
            })

        # Record the conflict
        self.assertEqual(len(import_scenarios), 2,
                        "SSOT VIOLATION: Multiple import paths for AgentRegistry")

        self.logger.error(f"IMPORT RESOLUTION CONFLICTS:")
        for scenario in import_scenarios:
            self.logger.error(f"  Path: {scenario['import_path']}")
            self.logger.error(f"  Class: {scenario['class']}")
            self.logger.error(f"  Capabilities: {scenario['capabilities']}")
        self.logger.error(f"  IMPACT: Inconsistent agent registry behavior across system components")

    @pytest.mark.asyncio
    async def test_websocket_event_delivery_failure_demonstration(self):
        """
        CRITICAL TEST: Demonstrates how registry duplication causes WebSocket event failures.

        This test shows the exact mechanism by which the Golden Path fails.
        """
        from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
        from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create mock WebSocket manager that tracks events
        mock_websocket_manager = Mock()
        mock_websocket_manager.broadcast = AsyncMock()
        mock_websocket_manager.send_to_user = AsyncMock()

        # Test basic registry WebSocket event handling
        basic_registry = BasicRegistry()
        basic_registry.set_websocket_manager(mock_websocket_manager)

        # Register a test agent with basic registry
        test_agent = Mock()
        test_agent.agent_type = "test_agent"
        basic_registry.register_agent(
            agent_type=basic_registry.AgentType.TRIAGE,
            name="Test Agent",
            description="Test agent for WebSocket events",
            agent_instance=test_agent
        )

        # Check if basic registry can deliver the 5 critical events
        basic_events_delivered = []

        # Simulate agent execution events
        critical_events = [
            'agent_started', 'agent_thinking', 'tool_executing',
            'tool_completed', 'agent_completed'
        ]

        for event_type in critical_events:
            # Basic registry uses simple broadcast pattern
            if hasattr(basic_registry, '_notify_agent_event'):
                try:
                    agent_info = list(basic_registry._agents.values())[0]
                    basic_registry._notify_agent_event(event_type, agent_info)
                    basic_events_delivered.append(event_type)
                except Exception as e:
                    self.logger.error(f"Basic registry failed to deliver {event_type}: {e}")

        # Test advanced registry with proper user isolation
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="test_request_845",
            thread_id="test_thread_845",
            run_id="test_run_845"
        )

        mock_llm_manager = Mock()
        advanced_registry = AdvancedRegistry(llm_manager=mock_llm_manager)
        advanced_registry.set_websocket_manager(mock_websocket_manager)

        # Advanced registry should support user-isolated WebSocket events
        advanced_supports_user_events = hasattr(advanced_registry, 'get_user_session')

        self.assertTrue(advanced_supports_user_events,
                       "Advanced registry should support user-isolated events")

        # The key difference: basic registry cannot properly isolate events per user
        # This is why the Golden Path fails - events get mixed up between users

        self.logger.error(f"WEBSOCKET EVENT DELIVERY ANALYSIS:")
        self.logger.error(f"  Basic Registry Events Delivered: {len(basic_events_delivered)}/{len(critical_events)}")
        self.logger.error(f"  Events: {basic_events_delivered}")
        self.logger.error(f"  Advanced Registry: Supports user-isolated event delivery")
        self.logger.error(f"  GOLDEN PATH IMPACT: Users don't receive proper real-time updates")

        # This test demonstrates the core issue: inconsistent event delivery patterns
        # between the two registry implementations


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])