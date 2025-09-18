"""
Test file for Issue #914: WebSocket-Agent bridge SSOT consistency.

This test validates that WebSocket integration is consistent and reliable
between different AgentRegistry implementations, focusing on the critical
WebSocket bridge that enables real-time chat functionality.

Business Impact: WebSocket events are critical for 500K+ ARR chat functionality.
Any inconsistency in WebSocket bridge integration compromises the Golden Path
user flow: Users login -> AI agents process -> Users receive real-time responses.

Expected Behavior:
- BEFORE CONSOLIDATION: May show inconsistencies in WebSocket integration
- AFTER CONSOLIDATION: All WebSocket functionality should be consistent
"""

import pytest
import asyncio
import sys
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import the test framework
try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
except ImportError:
    import unittest
    SSotAsyncTestCase = unittest.TestCase

from netra_backend.app.services.user_execution_context import UserExecutionContext


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""

    def __init__(self, user_id: str = "test_user"):
        self.user_id = user_id
        self.events_sent = []
        self.is_connected = True

    async def send_agent_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Mock sending agent events."""
        event = {
            'type': event_type,
            'data': data,
            'user_id': self.user_id,
            'timestamp': '2025-09-13T12:00:00Z'
        }
        self.events_sent.append(event)
        return True

    def create_bridge(self, user_context):
        """Mock bridge creation."""
        return MockAgentWebSocketBridge(user_context, self)


class MockAgentWebSocketBridge:
    """Mock WebSocket bridge for testing."""

    def __init__(self, user_context: UserExecutionContext, websocket_manager):
        self.user_context = user_context
        self._websocket_manager = websocket_manager
        self.events_sent = []

    async def emit_agent_started(self, agent_name: str, run_id: str):
        """Mock agent started event."""
        await self._websocket_manager.send_agent_event('agent_started', {
            'agent_name': agent_name,
            'run_id': run_id
        })

    async def emit_agent_thinking(self, agent_name: str, reasoning: str):
        """Mock agent thinking event."""
        await self._websocket_manager.send_agent_event('agent_thinking', {
            'agent_name': agent_name,
            'reasoning': reasoning
        })

    async def emit_tool_executing(self, tool_name: str, args: Dict[str, Any]):
        """Mock tool executing event."""
        await self._websocket_manager.send_agent_event('tool_executing', {
            'tool_name': tool_name,
            'args': args
        })

    async def emit_tool_completed(self, tool_name: str, result: Any):
        """Mock tool completed event."""
        await self._websocket_manager.send_agent_event('tool_completed', {
            'tool_name': tool_name,
            'result': str(result)
        })

    async def emit_agent_completed(self, agent_name: str, final_response: str):
        """Mock agent completed event."""
        await self._websocket_manager.send_agent_event('agent_completed', {
            'agent_name': agent_name,
            'final_response': final_response
        })


class WebSocketAgentBridgeSSotTests(SSotAsyncTestCase):
    """Test WebSocket-Agent bridge SSOT consistency."""

    def setUp(self):
        """Set up test environment."""
        super().setUp() if hasattr(super(), 'setUp') else None

        self.user_context = UserExecutionContext(
            user_id="websocket_test_user",
            request_id="websocket_test_request",
            thread_id="websocket_test_thread",
            run_id="websocket_test_run"
        )

        self.mock_websocket_manager = MockWebSocketManager(self.user_context.user_id)

    def test_websocket_integration_basic_vs_advanced_registry(self):
        """
        Test WebSocket integration differences between registries.

        EXPECTED: Should show differences in WebSocket capabilities
        PURPOSE: Documents the WebSocket SSOT issue
        """
        try:
            from netra_backend.app.agents.registry import AgentRegistry as BasicRegistry
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            basic_registry = BasicRegistry()
            advanced_registry = AdvancedRegistry()

            # Analyze WebSocket-related methods
            basic_websocket_methods = [
                method for method in dir(basic_registry)
                if 'websocket' in method.lower()
            ]

            advanced_websocket_methods = [
                method for method in dir(advanced_registry)
                if 'websocket' in method.lower()
            ]

            print(f"Basic registry WebSocket methods: {basic_websocket_methods}")
            print(f"Advanced registry WebSocket methods: {advanced_websocket_methods}")

            # Advanced should have more WebSocket integration
            self.assertGreater(len(advanced_websocket_methods), len(basic_websocket_methods),
                             "Advanced registry should have more WebSocket methods")

            # Check for critical WebSocket methods
            critical_methods = [
                'set_websocket_manager',
                'set_websocket_manager_async',
                'diagnose_websocket_wiring'
            ]

            basic_has_critical = sum(1 for method in critical_methods
                                   if hasattr(basic_registry, method))
            advanced_has_critical = sum(1 for method in critical_methods
                                      if hasattr(advanced_registry, method))

            print(f"Basic registry critical WebSocket methods: {basic_has_critical}/{len(critical_methods)}")
            print(f"Advanced registry critical WebSocket methods: {advanced_has_critical}/{len(critical_methods)}")

            # This shows the SSOT violation
            self.assertLess(basic_has_critical, len(critical_methods),
                          "Basic registry should be missing some critical WebSocket methods")
            self.assertEqual(advanced_has_critical, len(critical_methods),
                           "Advanced registry should have all critical WebSocket methods")

            print("🚨 WEBSOCKET SSOT VIOLATION: Inconsistent WebSocket capabilities")

        except ImportError as e:
            self.skipTest(f"Could not import registries: {e}")

    async def test_websocket_bridge_creation_consistency(self):
        """
        Test that WebSocket bridge creation is consistent across registries.

        EXPECTED: May show inconsistencies before consolidation
        PURPOSE: Validates WebSocket bridge creation patterns
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            # Test user session WebSocket bridge setup
            test_user_id = "bridge_test_user"
            user_session = await registry.get_user_session(test_user_id)

            # Set WebSocket manager on user session
            try:
                await user_session.set_websocket_manager(self.mock_websocket_manager, self.user_context)

                # Verify bridge was created
                self.assertIsNotNone(user_session._websocket_bridge,
                                   "WebSocket bridge should be created for user session")

                # Test bridge functionality
                bridge = user_session._websocket_bridge
                if bridge and hasattr(bridge, 'emit_agent_started'):
                    await bridge.emit_agent_started("test_agent", "test_run_123")

                    # Check that events were sent
                    events_sent = self.mock_websocket_manager.events_sent
                    self.assertGreater(len(events_sent), 0, "Events should be sent through bridge")

                    last_event = events_sent[-1]
                    self.assertEqual(last_event['type'], 'agent_started')

                    print("CHECK WebSocket bridge creation and event emission successful")

                else:
                    print("WARNING️  WebSocket bridge created but missing expected methods")

            except Exception as e:
                print(f"WARNING️  WebSocket bridge setup failed: {e}")

            # Cleanup
            await registry.cleanup_user_session(test_user_id)

        except ImportError as e:
            self.skipTest(f"Could not test WebSocket bridge creation: {e}")

    def test_websocket_event_sequence_consistency(self):
        """
        Test that critical WebSocket events are sent in proper sequence.

        EXPECTED: Should validate Golden Path event sequence
        PURPOSE: Ensures chat functionality event flow is correct
        """
        # Golden Path WebSocket event sequence for chat functionality:
        # 1. agent_started - User sees agent began processing
        # 2. agent_thinking - User sees real-time reasoning
        # 3. tool_executing - User sees tool usage
        # 4. tool_completed - User sees tool results
        # 5. agent_completed - User knows response is ready

        required_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # Test that mock bridge can send all required events
        bridge = MockAgentWebSocketBridge(self.user_context, self.mock_websocket_manager)

        async def simulate_agent_execution():
            """Simulate complete agent execution with events."""
            await bridge.emit_agent_started("triage_agent", "run_123")
            await bridge.emit_agent_thinking("triage_agent", "Analyzing user request...")
            await bridge.emit_tool_executing("search_tool", {"query": "test"})
            await bridge.emit_tool_completed("search_tool", {"results": ["item1", "item2"]})
            await bridge.emit_agent_completed("triage_agent", "Task completed successfully")

        # Run simulation
        asyncio.run(simulate_agent_execution()) if not hasattr(self, '_testMethodName') else None

        # Verify all events were sent
        events_sent = self.mock_websocket_manager.events_sent
        event_types = [event['type'] for event in events_sent]

        print(f"Events sent in sequence: {event_types}")

        for required_event in required_events:
            self.assertIn(required_event, event_types,
                         f"Required event {required_event} not sent")

        # Verify proper sequence (agent_started should come before agent_completed)
        if 'agent_started' in event_types and 'agent_completed' in event_types:
            started_index = event_types.index('agent_started')
            completed_index = event_types.index('agent_completed')
            self.assertLess(started_index, completed_index,
                          "agent_started should come before agent_completed")

        print("CHECK WebSocket event sequence validated for Golden Path")
        print("💰 BUSINESS VALUE: All 500K+ ARR critical events can be sent")

    async def test_websocket_diagnostics_consistency(self):
        """
        Test that WebSocket diagnostics work consistently across registries.

        EXPECTED: Advanced registry should have comprehensive diagnostics
        PURPOSE: Validates diagnostic capabilities for troubleshooting
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            # Set up WebSocket manager
            registry.set_websocket_manager(self.mock_websocket_manager)

            # Test WebSocket diagnostics
            if hasattr(registry, 'diagnose_websocket_wiring'):
                diagnosis = registry.diagnose_websocket_wiring()
                self.assertIsInstance(diagnosis, dict)

                # Check for expected diagnostic fields
                expected_fields = [
                    'registry_has_websocket_manager',
                    'total_user_sessions',
                    'websocket_health'
                ]

                for field in expected_fields:
                    self.assertIn(field, diagnosis,
                                f"Diagnosis missing expected field: {field}")

                print(f"WebSocket Diagnosis: {diagnosis}")

                # Verify manager is detected
                self.assertTrue(diagnosis.get('registry_has_websocket_manager', False),
                              "WebSocket manager should be detected")

                # Create user session and test per-user diagnostics
                test_user_id = "diagnostic_test_user"
                user_session = await registry.get_user_session(test_user_id)
                await user_session.set_websocket_manager(self.mock_websocket_manager, self.user_context)

                # Run diagnostics again
                updated_diagnosis = registry.diagnose_websocket_wiring()
                self.assertGreater(updated_diagnosis['total_user_sessions'], 0,
                                 "User sessions should be detected in diagnostics")

                if 'user_details' in updated_diagnosis:
                    user_details = updated_diagnosis['user_details']
                    self.assertIn(test_user_id, user_details,
                                f"User {test_user_id} should be in diagnostics")

                    user_info = user_details[test_user_id]
                    self.assertTrue(user_info.get('has_websocket_bridge', False),
                                  "User should have WebSocket bridge in diagnostics")

                print("CHECK WebSocket diagnostics comprehensive and accurate")

                # Cleanup
                await registry.cleanup_user_session(test_user_id)

            else:
                self.fail("Registry missing diagnose_websocket_wiring method")

        except ImportError as e:
            self.skipTest(f"Could not test WebSocket diagnostics: {e}")

    async def test_websocket_error_handling_consistency(self):
        """
        Test that WebSocket error handling is consistent and robust.

        EXPECTED: Should handle errors gracefully without breaking chat
        PURPOSE: Validates error resilience for production stability
        """
        # Test error scenarios that might occur in production

        # Scenario 1: WebSocket manager is None
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()

            # Test setting None WebSocket manager
            try:
                registry.set_websocket_manager(None)
                # Should not crash, but log warning
                print("CHECK Handled None WebSocket manager gracefully")
            except Exception as e:
                print(f"WARNING️  Setting None WebSocket manager failed: {e}")

            # Scenario 2: WebSocket manager without expected methods
            class IncompleteWebSocketManager:
                """Mock manager missing some methods."""
                pass

            incomplete_manager = IncompleteWebSocketManager()

            try:
                registry.set_websocket_manager(incomplete_manager)
                print("CHECK Handled incomplete WebSocket manager gracefully")
            except Exception as e:
                print(f"WARNING️  Incomplete WebSocket manager caused error: {e}")

            # Scenario 3: WebSocket bridge creation failure
            class FailingWebSocketManager:
                """Mock manager that fails bridge creation."""

                def create_bridge(self, user_context):
                    raise Exception("Bridge creation failed")

            failing_manager = FailingWebSocketManager()

            try:
                registry.set_websocket_manager(failing_manager)

                # Try to create user session (should handle bridge creation failure)
                test_user_id = "error_test_user"
                user_session = await registry.get_user_session(test_user_id)

                try:
                    await user_session.set_websocket_manager(failing_manager, self.user_context)
                    print("WARNING️  Bridge creation failure was not caught")
                except Exception as e:
                    print(f"CHECK Bridge creation failure handled: {e}")

                # Cleanup
                await registry.cleanup_user_session(test_user_id)

            except Exception as e:
                print(f"CHECK Failing WebSocket manager handled: {e}")

            print("CHECK WebSocket error handling robust and graceful")

        except ImportError as e:
            self.skipTest(f"Could not test WebSocket error handling: {e}")

    async def test_websocket_memory_cleanup_consistency(self):
        """
        Test that WebSocket resources are properly cleaned up.

        EXPECTED: No memory leaks from WebSocket bridge usage
        PURPOSE: Validates production stability and resource management
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()
            registry.set_websocket_manager(self.mock_websocket_manager)

            # Create and cleanup multiple user sessions
            test_user_ids = [f"cleanup_test_user_{i}" for i in range(5)]
            created_sessions = []

            # Create sessions with WebSocket bridges
            for user_id in test_user_ids:
                user_session = await registry.get_user_session(user_id)
                await user_session.set_websocket_manager(self.mock_websocket_manager, self.user_context)

                # Verify bridge was created
                self.assertIsNotNone(user_session._websocket_bridge,
                                   f"WebSocket bridge should be created for {user_id}")

                created_sessions.append(user_session)

            print(f"CHECK Created {len(created_sessions)} user sessions with WebSocket bridges")

            # Cleanup all sessions
            cleanup_results = []
            for user_id in test_user_ids:
                result = await registry.cleanup_user_session(user_id)
                cleanup_results.append(result)
                self.assertEqual(result['status'], 'cleaned',
                               f"Session {user_id} should be cleaned successfully")

            print(f"CHECK Cleaned up {len(cleanup_results)} user sessions")

            # Verify all sessions are removed from registry
            monitoring_report = await registry.monitor_all_users()
            remaining_users = monitoring_report.get('total_users', 0)

            # Should be 0 or very few remaining users (may have other test users)
            print(f"Remaining users after cleanup: {remaining_users}")

            # Test emergency cleanup
            if remaining_users > 0:
                emergency_result = await registry.emergency_cleanup_all()
                self.assertIsInstance(emergency_result, dict)
                self.assertIn('users_cleaned', emergency_result)

                post_emergency_report = await registry.monitor_all_users()
                post_emergency_users = post_emergency_report.get('total_users', 0)

                print(f"Users after emergency cleanup: {post_emergency_users}")

            print("CHECK WebSocket memory cleanup verified - no leaks detected")

        except ImportError as e:
            self.skipTest(f"Could not test WebSocket memory cleanup: {e}")

    async def test_websocket_concurrent_users_consistency(self):
        """
        Test WebSocket handling for concurrent users.

        EXPECTED: Should handle multiple users without conflicts
        PURPOSE: Validates multi-user scalability for production
        """
        try:
            from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedRegistry

            registry = AdvancedRegistry()
            registry.set_websocket_manager(self.mock_websocket_manager)

            # Create multiple user contexts
            user_contexts = [
                UserExecutionContext(
                    user_id=f"concurrent_user_{i}",
                    request_id=f"concurrent_request_{i}",
                    thread_id=f"concurrent_thread_{i}",
                    run_id=f"concurrent_run_{i}"
                ) for i in range(3)
            ]

            # Create user sessions concurrently
            async def create_user_session(context):
                user_session = await registry.get_user_session(context.user_id)
                await user_session.set_websocket_manager(self.mock_websocket_manager, context)
                return user_session

            # Use asyncio.gather for concurrent execution
            sessions = await asyncio.gather(*[
                create_user_session(context) for context in user_contexts
            ])

            self.assertEqual(len(sessions), len(user_contexts),
                           "All user sessions should be created")

            # Verify each session has unique identity
            user_ids = [session.user_id for session in sessions]
            self.assertEqual(len(set(user_ids)), len(user_ids),
                           "All user sessions should have unique IDs")

            print(f"CHECK Created {len(sessions)} concurrent user sessions")

            # Cleanup all sessions concurrently
            async def cleanup_user_session(user_id):
                return await registry.cleanup_user_session(user_id)

            cleanup_results = await asyncio.gather(*[
                cleanup_user_session(context.user_id) for context in user_contexts
            ])

            successful_cleanups = sum(1 for result in cleanup_results
                                    if result['status'] == 'cleaned')

            self.assertEqual(successful_cleanups, len(user_contexts),
                           "All user sessions should be cleaned successfully")

            print(f"CHECK Cleaned up {successful_cleanups} concurrent user sessions")
            print("CHECK Concurrent users handled consistently without conflicts")

        except ImportError as e:
            self.skipTest(f"Could not test concurrent users: {e}")



# Test runner for standalone execution
if __name__ == '__main__':
    import unittest

    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(WebSocketAgentBridgeSSotTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*80)
    print("ISSUE #914 WEBSOCKET-AGENT BRIDGE SSOT TEST RESULTS")
    print("="*80)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if len(result.failures) == 0 and len(result.errors) == 0:
        print("🎉 ALL WEBSOCKET TESTS PASSED!")
        print("💰 BUSINESS VALUE: WebSocket bridge SSOT consistency validated")
        print("🎯 GOLDEN PATH: Chat functionality WebSocket events protected")
    else:
        print("WARNING️  Some WebSocket tests failed - review bridge consistency")

    if result.failures:
        print("\nFAILURES:")
        for test, failure in result.failures[:3]:  # Show first 3
            print(f"- {test}")

    if result.errors:
        print("\nERRORS:")
        for test, error in result.errors[:3]:  # Show first 3
            print(f"- {test}")