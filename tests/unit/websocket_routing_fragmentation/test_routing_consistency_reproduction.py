"""
Test Message Routing Consistency Across Implementations

PURPOSE: Reproduce routing behavior differences causing Golden Path failures
STATUS: SHOULD FAIL initially - inconsistent routing behavior
EXPECTED: PASS after SSOT consolidation ensures consistent behavior

Business Value Justification (BVJ):
- Segment: Enterprise/Platform
- Goal: Reliability and Golden Path consistency
- Value Impact: Ensures consistent message routing behavior across all implementations
- Revenue Impact: Prevents $500K+ ARR loss from inconsistent routing causing AI response failures

This test reproduces the specific routing inconsistencies that block Golden Path:
Different router implementations handle identical messages differently, causing
unpredictable tool dispatching and agent execution failures that prevent users
from receiving AI responses.
"""

import asyncio
from typing import Dict, Any, List, Optional
from unittest.mock import MagicMock, AsyncMock
import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestMessageRoutingConsistency(SSotAsyncTestCase):
    """Validate consistent routing behavior across implementations."""

    def setUp(self) -> None:
        """Set up test environment with mock dependencies."""
        super().setUp()
        self.test_messages = self._create_test_messages()
        self.router_instances = {}

    def _create_test_messages(self) -> Dict[str, Dict[str, Any]]:
        """Create test messages that should be routed consistently."""
        return {
            'agent_start': {
                'type': 'start_agent',
                'data': {
                    'user_id': 'test-user-123',
                    'thread_id': 'test-thread-456',
                    'message': 'Test agent request'
                }
            },
            'quality_message': {
                'type': 'get_quality_metrics',
                'data': {
                    'user_id': 'test-user-123',
                    'thread_id': 'test-thread-456',
                    'metric_types': ['accuracy', 'relevance']
                }
            },
            'websocket_event': {
                'type': 'agent_thinking',
                'data': {
                    'user_id': 'test-user-123',
                    'thread_id': 'test-thread-456',
                    'message': 'Agent is processing your request...'
                }
            },
            'user_message': {
                'type': 'user_message',
                'data': {
                    'user_id': 'test-user-123',
                    'thread_id': 'test-thread-456',
                    'message': 'User input message'
                }
            },
            'tool_execution': {
                'type': 'tool_executing',
                'data': {
                    'user_id': 'test-user-123',
                    'thread_id': 'test-thread-456',
                    'tool_name': 'data_analyzer',
                    'parameters': {'query': 'test'}
                }
            }
        }

    async def _setup_message_router(self) -> Optional[Any]:
        """Set up MessageRouter instance with mocked dependencies."""
        try:
            from netra_backend.app.websocket_core.handlers import MessageRouter
            return MessageRouter()
        except ImportError as e:
            print(f"Could not import MessageRouter: {e}")
            return None

    async def _setup_quality_message_router(self) -> Optional[Any]:
        """Set up QualityMessageRouter instance with mocked dependencies."""
        try:
            from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

            # Create mock dependencies
            mock_supervisor = MagicMock()
            mock_db_session_factory = MagicMock()
            mock_quality_gate_service = MagicMock()
            mock_monitoring_service = MagicMock()

            return QualityMessageRouter(
                supervisor=mock_supervisor,
                db_session_factory=mock_db_session_factory,
                quality_gate_service=mock_quality_gate_service,
                monitoring_service=mock_monitoring_service
            )
        except ImportError as e:
            print(f"Could not import QualityMessageRouter: {e}")
            return None
        except Exception as e:
            print(f"Could not instantiate QualityMessageRouter: {e}")
            return None

    async def _setup_websocket_event_router(self) -> Optional[Any]:
        """Set up WebSocketEventRouter instance with mocked dependencies."""
        try:
            from netra_backend.app.services.websocket_event_router import WebSocketEventRouter

            # Create mock WebSocket manager
            mock_websocket_manager = MagicMock()

            return WebSocketEventRouter(websocket_manager=mock_websocket_manager)
        except ImportError as e:
            print(f"Could not import WebSocketEventRouter: {e}")
            return None

    async def test_identical_message_routing_behavior(self):
        """SHOULD FAIL: Different routers handle identical messages differently.

        This test sends identical messages through different router instances and
        compares their routing decisions to detect behavioral inconsistencies.

        Expected failures:
        1. MessageRouter routes messages differently than QualityMessageRouter
        2. Handler selection varies between implementations
        3. Message processing outcomes differ for identical inputs

        SUCCESS CRITERIA: All routers produce identical routing behavior
        """
        # Set up router instances
        message_router = await self._setup_message_router()
        quality_router = await self._setup_quality_message_router()
        event_router = await self._setup_websocket_event_router()

        routers = {
            'MessageRouter': message_router,
            'QualityMessageRouter': quality_router,
            'WebSocketEventRouter': event_router
        }

        # Filter out None instances
        available_routers = {name: router for name, router in routers.items()
                           if router is not None}

        print(f"\n=== AVAILABLE ROUTERS FOR TESTING: {list(available_routers.keys())} ===")

        routing_results = {}

        # Test each message through each router
        for message_name, message_data in self.test_messages.items():
            routing_results[message_name] = {}

            for router_name, router_instance in available_routers.items():
                try:
                    result = await self._test_message_routing(
                        router_instance, router_name, message_data
                    )
                    routing_results[message_name][router_name] = result
                except Exception as e:
                    routing_results[message_name][router_name] = {
                        'error': str(e),
                        'handled': False,
                        'handler_type': None
                    }

        # Analyze routing consistency
        inconsistencies = self._analyze_routing_inconsistencies(routing_results)

        # Document results
        print("\n=== ROUTING CONSISTENCY ANALYSIS ===")
        for message_name, router_results in routing_results.items():
            print(f"\nMessage: {message_name}")
            for router_name, result in router_results.items():
                print(f"  {router_name}: {result}")

        print(f"\nDetected inconsistencies: {inconsistencies}")

        # This should FAIL initially - expect routing inconsistencies
        self.assertEqual(len(inconsistencies), 0,
            f"ROUTING BEHAVIOR INCONSISTENCY: Found {len(inconsistencies)} "
            f"inconsistencies in message routing behavior: {inconsistencies}")

    async def _test_message_routing(self, router_instance: Any, router_name: str,
                                  message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Test message routing through a specific router instance."""
        result = {
            'handled': False,
            'handler_type': None,
            'response': None,
            'error': None
        }

        try:
            user_id = message_data['data']['user_id']

            if router_name == 'MessageRouter':
                # Test MessageRouter routing
                handled = await self._test_message_router_routing(
                    router_instance, user_id, message_data
                )
                result['handled'] = handled
                result['handler_type'] = 'MessageRouter'

            elif router_name == 'QualityMessageRouter':
                # Test QualityMessageRouter routing
                handled = await self._test_quality_router_routing(
                    router_instance, user_id, message_data
                )
                result['handled'] = handled
                result['handler_type'] = 'QualityMessageRouter'

            elif router_name == 'WebSocketEventRouter':
                # Test WebSocketEventRouter routing
                handled = await self._test_event_router_routing(
                    router_instance, user_id, message_data
                )
                result['handled'] = handled
                result['handler_type'] = 'WebSocketEventRouter'

        except Exception as e:
            result['error'] = str(e)

        return result

    async def _test_message_router_routing(self, router: Any, user_id: str,
                                         message_data: Dict[str, Any]) -> bool:
        """Test routing through MessageRouter."""
        # Check if router has handle_message method
        if hasattr(router, 'handle_message'):
            try:
                # Mock WebSocket connection
                mock_websocket = MagicMock()

                result = await router.handle_message(mock_websocket, message_data)
                return result is not None
            except Exception:
                return False

        # Check if router has route_message method
        if hasattr(router, 'route_message'):
            try:
                result = await router.route_message(user_id, message_data)
                return result is not None
            except Exception:
                return False

        return False

    async def _test_quality_router_routing(self, router: Any, user_id: str,
                                         message_data: Dict[str, Any]) -> bool:
        """Test routing through QualityMessageRouter."""
        message_type = message_data.get('type', '')

        # Check if router handles this message type
        if hasattr(router, 'handlers'):
            handlers = getattr(router, 'handlers', {})
            return message_type in handlers

        # Check for specific handling methods
        if hasattr(router, 'handle_message'):
            try:
                result = await router.handle_message(user_id, message_data)
                return result is not None
            except Exception:
                return False

        return False

    async def _test_event_router_routing(self, router: Any, user_id: str,
                                       message_data: Dict[str, Any]) -> bool:
        """Test routing through WebSocketEventRouter."""
        # WebSocketEventRouter typically handles event emission rather than message routing
        # Check for event emission capabilities
        if hasattr(router, 'emit_to_user'):
            try:
                await router.emit_to_user(user_id, message_data)
                return True
            except Exception:
                return False

        # Check for connection management
        if hasattr(router, 'add_connection'):
            return True  # Can handle connection routing

        return False

    def _analyze_routing_inconsistencies(self, routing_results: Dict[str, Dict[str, Dict]]) -> List[str]:
        """Analyze routing results to detect inconsistencies."""
        inconsistencies = []

        for message_name, router_results in routing_results.items():
            # Get all non-error results
            valid_results = {router: result for router, result in router_results.items()
                           if 'error' not in result or result['error'] is None}

            if len(valid_results) < 2:
                continue  # Need at least 2 routers to compare

            # Check if handling behavior is consistent
            handled_states = [result['handled'] for result in valid_results.values()]
            if len(set(handled_states)) > 1:
                inconsistencies.append(
                    f"Message '{message_name}': Inconsistent handled states {handled_states} "
                    f"across routers {list(valid_results.keys())}"
                )

            # Check if handler types are appropriate for message
            handler_types = [result['handler_type'] for result in valid_results.values()]
            if len(set(handler_types)) > 1:
                inconsistencies.append(
                    f"Message '{message_name}': Different handler types {handler_types} "
                    f"across routers {list(valid_results.keys())}"
                )

        return inconsistencies

    async def test_quality_message_routing_fragmentation(self):
        """SHOULD FAIL: Quality messages routed inconsistently.

        This test specifically examines quality message routing to detect
        fragmentation between QualityMessageRouter and QualityRouterHandler.

        Expected failures:
        1. QualityMessageRouter handles quality messages differently than QualityRouterHandler
        2. Quality message types routed to wrong handlers
        3. Quality metrics and reports delivered inconsistently

        SUCCESS CRITERIA: Quality messages routed consistently through single SSOT
        """
        quality_messages = {
            'quality_metrics': self.test_messages['quality_message'],
            'quality_validation': {
                'type': 'validate_content',
                'data': {
                    'user_id': 'test-user-123',
                    'content': 'Test content to validate',
                    'validation_rules': ['accuracy', 'relevance']
                }
            }
        }

        # Test quality routing through different implementations
        routing_analysis = {}

        # Test QualityMessageRouter
        quality_router = await self._setup_quality_message_router()
        if quality_router:
            routing_analysis['QualityMessageRouter'] = {}
            for msg_name, msg_data in quality_messages.items():
                try:
                    result = await self._test_quality_router_routing(
                        quality_router, msg_data['data']['user_id'], msg_data
                    )
                    routing_analysis['QualityMessageRouter'][msg_name] = {
                        'handled': result,
                        'router_type': 'dedicated_quality'
                    }
                except Exception as e:
                    routing_analysis['QualityMessageRouter'][msg_name] = {
                        'error': str(e)
                    }

        # Test MessageRouter with QualityRouterHandler
        message_router = await self._setup_message_router()
        if message_router:
            routing_analysis['MessageRouter_QualityHandler'] = {}
            for msg_name, msg_data in quality_messages.items():
                try:
                    result = await self._test_message_router_routing(
                        message_router, msg_data['data']['user_id'], msg_data
                    )
                    routing_analysis['MessageRouter_QualityHandler'][msg_name] = {
                        'handled': result,
                        'router_type': 'integrated_quality'
                    }
                except Exception as e:
                    routing_analysis['MessageRouter_QualityHandler'][msg_name] = {
                        'error': str(e)
                    }

        # Analyze quality routing fragmentation
        print("\n=== QUALITY MESSAGE ROUTING ANALYSIS ===")
        for router_name, results in routing_analysis.items():
            print(f"\n{router_name}:")
            for msg_name, result in results.items():
                print(f"  {msg_name}: {result}")

        # Detect quality routing inconsistencies
        quality_inconsistencies = []

        # Compare quality message handling across routers
        if len(routing_analysis) > 1:
            router_names = list(routing_analysis.keys())
            for msg_name in quality_messages.keys():
                handled_states = []
                for router_name in router_names:
                    if (router_name in routing_analysis and
                        msg_name in routing_analysis[router_name] and
                        'handled' in routing_analysis[router_name][msg_name]):
                        handled_states.append(routing_analysis[router_name][msg_name]['handled'])

                if len(set(handled_states)) > 1:
                    quality_inconsistencies.append(
                        f"Quality message '{msg_name}' handled inconsistently: {handled_states}"
                    )

        # This should FAIL initially - expect quality routing fragmentation
        self.assertEqual(len(quality_inconsistencies), 0,
            f"QUALITY ROUTING FRAGMENTATION: Found {len(quality_inconsistencies)} "
            f"quality routing inconsistencies: {quality_inconsistencies}")

    async def test_event_routing_coordination_failures(self):
        """SHOULD FAIL: Event routing not coordinated between routers.

        This test examines coordination between WebSocketEventRouter and MessageRouter
        to detect coordination failures affecting user experience.

        Expected failures:
        1. Events routed through WebSocketEventRouter not coordinated with MessageRouter
        2. Message handling and event emission not synchronized
        3. User isolation not maintained consistently across routing implementations

        SUCCESS CRITERIA: Event routing fully coordinated through single SSOT
        """
        # Test critical WebSocket events that must be coordinated
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        coordination_analysis = {}

        # Test WebSocketEventRouter event handling
        event_router = await self._setup_websocket_event_router()
        if event_router:
            coordination_analysis['WebSocketEventRouter'] = {}
            for event_type in critical_events:
                event_data = {
                    'type': event_type,
                    'data': {
                        'user_id': 'test-user-123',
                        'thread_id': 'test-thread-456',
                        'message': f'Test {event_type} event'
                    }
                }

                try:
                    result = await self._test_event_router_routing(
                        event_router, event_data['data']['user_id'], event_data
                    )
                    coordination_analysis['WebSocketEventRouter'][event_type] = {
                        'can_route': result,
                        'coordination_type': 'event_emission'
                    }
                except Exception as e:
                    coordination_analysis['WebSocketEventRouter'][event_type] = {
                        'error': str(e)
                    }

        # Test MessageRouter event coordination
        message_router = await self._setup_message_router()
        if message_router:
            coordination_analysis['MessageRouter'] = {}
            for event_type in critical_events:
                event_data = {
                    'type': event_type,
                    'data': {
                        'user_id': 'test-user-123',
                        'thread_id': 'test-thread-456',
                        'message': f'Test {event_type} event'
                    }
                }

                try:
                    result = await self._test_message_router_routing(
                        message_router, event_data['data']['user_id'], event_data
                    )
                    coordination_analysis['MessageRouter'][event_type] = {
                        'can_route': result,
                        'coordination_type': 'message_handling'
                    }
                except Exception as e:
                    coordination_analysis['MessageRouter'][event_type] = {
                        'error': str(e)
                    }

        # Analyze coordination failures
        print("\n=== EVENT ROUTING COORDINATION ANALYSIS ===")
        for router_name, results in coordination_analysis.items():
            print(f"\n{router_name}:")
            for event_type, result in results.items():
                print(f"  {event_type}: {result}")

        # Detect coordination failures
        coordination_failures = []

        # Check if both routers can handle the same events (indicates overlap/conflict)
        if len(coordination_analysis) > 1:
            router_names = list(coordination_analysis.keys())
            for event_type in critical_events:
                can_route_states = []
                coordination_types = []

                for router_name in router_names:
                    if (router_name in coordination_analysis and
                        event_type in coordination_analysis[router_name] and
                        'can_route' in coordination_analysis[router_name][event_type]):
                        can_route_states.append(coordination_analysis[router_name][event_type]['can_route'])
                        coordination_types.append(coordination_analysis[router_name][event_type]['coordination_type'])

                # If both routers can route the same event, there's potential conflict
                if len(can_route_states) > 1 and all(can_route_states):
                    coordination_failures.append(
                        f"Event '{event_type}' can be routed by multiple routers with "
                        f"coordination types: {coordination_types}"
                    )

        # Check for missing coordination mechanisms
        if len(coordination_analysis) > 1:
            coordination_failures.append(
                f"Multiple routing implementations ({list(coordination_analysis.keys())}) "
                f"without unified coordination mechanism"
            )

        # This should FAIL initially - expect coordination failures
        self.assertEqual(len(coordination_failures), 0,
            f"EVENT ROUTING COORDINATION FAILURES: Found {len(coordination_failures)} "
            f"coordination failures: {coordination_failures}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])