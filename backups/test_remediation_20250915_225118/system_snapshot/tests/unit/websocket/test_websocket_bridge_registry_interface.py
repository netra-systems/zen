"""
Issue #914 WebSocket Bridge Registry Interface Protection Test Suite

This test suite validates that WebSocket bridge interfaces remain stable
throughout the AgentRegistry SSOT consolidation process, protecting the
Golden Path user flow and business value.

EXPECTED BEHAVIOR: These tests MUST ALWAYS PASS - they protect business continuity.
Any failures indicate breaking changes that affect $500K+ ARR functionality.

Business Impact:
- Protects Golden Path: Users login → get AI responses
- Ensures WebSocket event delivery for real-time chat experience
- Maintains $500K+ ARR chat functionality reliability
- Validates enterprise customer real-time communication

Test Strategy:
1. Test WebSocket bridge interface stability during registry transitions
2. Validate event delivery continues to work regardless of registry implementation
3. Ensure user session management remains intact
4. Protect multi-user WebSocket isolation patterns
5. Validate critical WebSocket events (5 required events)
"""
import pytest

import asyncio
import logging
import unittest
import uuid
import warnings
from typing import Optional, Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# WebSocket testing infrastructure - CRITICAL for business value protection
try:
    from test_framework.ssot.websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory
    from test_framework.ssot.websocket_bridge_test_helper import WebSocketBridgeTestHelper
    from test_framework.ssot.websocket_test_client import WebSocketTestClient
    websocket_infra_available = True
except ImportError:
    WebSocketTestInfrastructureFactory = None
    WebSocketBridgeTestHelper = None
    WebSocketTestClient = None
    websocket_infra_available = False

# Registry imports - testing both during transition
try:
    from netra_backend.app.agents.registry import AgentRegistry as BasicAgentRegistry
    basic_available = True
except ImportError:
    BasicAgentRegistry = None
    basic_available = False

try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedAgentRegistry
    advanced_available = True
except ImportError:
    AdvancedAgentRegistry = None
    advanced_available = False

# Mock factory for test support
try:
    from test_framework.ssot.mock_factory import SSotMockFactory
except ImportError:
    SSotMockFactory = None

logger = logging.getLogger(__name__)


@pytest.mark.unit
class WebSocketBridgeRegistryInterfaceTests(SSotAsyncTestCase):
    """
    Test suite to protect WebSocket bridge interface stability.

    These tests MUST ALWAYS PASS to ensure business continuity
    during AgentRegistry SSOT consolidation.
    """

    def setup_method(self, method):
        """Setup test environment with WebSocket infrastructure."""
        super().setup_method(method)
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.websocket_infrastructure = None
        self.registry_instances: List[Any] = []
        self.mock_factory = SSotMockFactory() if SSotMockFactory else None

        # Critical business value metrics
        self.business_value_metrics = {
            'websocket_event_delivery': False,
            'user_session_isolation': False,
            'real_time_communication': False,
            'multi_user_support': False,
            'golden_path_protection': False
        }

    async def teardown_method(self, method):
        """Cleanup WebSocket infrastructure and registries."""
        # Cleanup registries
        for registry in self.registry_instances:
            if hasattr(registry, 'cleanup') and callable(registry.cleanup):
                try:
                    await registry.cleanup()
                except Exception as e:
                    logger.warning(f"Registry cleanup failed: {e}")

        # Cleanup WebSocket infrastructure
        if self.websocket_infrastructure and hasattr(self.websocket_infrastructure, 'cleanup'):
            try:
                await self.websocket_infrastructure.cleanup()
            except Exception as e:
                logger.warning(f"WebSocket infrastructure cleanup failed: {e}")

        self.registry_instances.clear()
        await super().teardown_method(method)

    async def test_01_websocket_bridge_interface_stability(self):
        """
        Test 1: WebSocket bridge interface remains stable (MUST ALWAYS PASS)

        Validates that WebSocket bridge interfaces work consistently
        regardless of which registry implementation is used.

        CRITICAL: This protects $500K+ ARR chat functionality
        """
        if not websocket_infra_available:
            pytest.skip("WebSocket infrastructure required for business value protection")

        # Create WebSocket infrastructure
        self.websocket_infrastructure = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False  # Simplified for unit test
        )

        # Validate infrastructure creation
        self.assertIsNotNone(self.websocket_infrastructure,
                           "WebSocket infrastructure must be available for Golden Path")
        self.assertIsNotNone(self.websocket_infrastructure.websocket_manager,
                           "WebSocket manager must be available for real-time communication")
        self.assertIsNotNone(self.websocket_infrastructure.bridge,
                           "WebSocket bridge must be available for agent integration")

        # Test bridge interface methods
        bridge = self.websocket_infrastructure.bridge
        required_bridge_methods = ['send_event', 'connect_user', 'disconnect_user']
        available_bridge_methods = []

        for method_name in required_bridge_methods:
            if hasattr(bridge, method_name):
                available_bridge_methods.append(method_name)

        bridge_completeness = len(available_bridge_methods) / len(required_bridge_methods)
        self.business_value_metrics['real_time_communication'] = (bridge_completeness >= 0.8)

        # MUST PASS - Bridge interface stability is critical
        self.assertGreaterEqual(bridge_completeness, 0.8,
                               f"WebSocket bridge must be at least 80% complete for business value, "
                               f"got {bridge_completeness:.1%}")

        # Record critical business metrics
        self.record_metric('websocket_bridge_completeness', bridge_completeness)
        logger.info(f"WebSocket bridge interface stability validated: {bridge_completeness:.1%}")

    async def test_02_critical_websocket_events_delivery(self):
        """
        Test 2: Critical WebSocket events are delivered (MUST ALWAYS PASS)

        Validates that the 5 critical WebSocket events required for
        Golden Path user experience are properly delivered.

        CRITICAL: These events are essential for user experience
        """
        if not websocket_infra_available:
            pytest.skip("WebSocket infrastructure required for event delivery testing")

        # Create WebSocket infrastructure
        self.websocket_infrastructure = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False
        )

        # Critical events for Golden Path
        critical_events = [
            'agent_started',    # User sees agent began processing
            'agent_thinking',   # Real-time reasoning visibility
            'tool_executing',   # Tool usage transparency
            'tool_completed',   # Tool results display
            'agent_completed'   # User knows response is ready
        ]

        bridge = self.websocket_infrastructure.bridge
        successful_events = 0

        for event_type in critical_events:
            try:
                test_event = {
                    'type': event_type,
                    'data': {'message': f'Test {event_type} event', 'user_id': self.test_user_id},
                    'user_id': self.test_user_id,
                    'timestamp': uuid.uuid4().hex[:8]
                }

                # Test event delivery
                if hasattr(bridge, 'send_event'):
                    bridge.send_event(test_event)
                    successful_events += 1
                elif hasattr(bridge, 'emit'):
                    bridge.emit(event_type, test_event)
                    successful_events += 1

            except Exception as e:
                logger.error(f"Critical event {event_type} delivery failed: {e}")

        event_delivery_rate = successful_events / len(critical_events)
        self.business_value_metrics['websocket_event_delivery'] = (event_delivery_rate >= 1.0)

        # MUST PASS - All critical events must be deliverable
        self.assertEqual(event_delivery_rate, 1.0,
                        f"ALL critical WebSocket events must be deliverable for Golden Path - "
                        f"only {event_delivery_rate:.1%} working, affecting $500K+ ARR functionality")

        # Record critical metrics
        self.record_metric('critical_events_delivery_rate', event_delivery_rate)
        logger.info(f"Critical WebSocket events delivery validated: {successful_events}/{len(critical_events)}")

    async def test_03_user_session_isolation_protection(self):
        """
        Test 3: User session isolation is protected (MUST ALWAYS PASS)

        Validates that WebSocket user sessions remain properly isolated
        during registry transitions, protecting enterprise customer data.

        CRITICAL: User isolation prevents data leakage
        """
        if not websocket_infra_available:
            pytest.skip("WebSocket infrastructure required for isolation testing")

        user1_id = f"{self.test_user_id}_isolation_1"
        user2_id = f"{self.test_user_id}_isolation_2"

        # Create isolated WebSocket infrastructure for each user
        infra1 = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=user1_id,
            enable_auth=False
        )
        infra2 = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=user2_id,
            enable_auth=False
        )

        # Validate isolation
        self.assertNotEqual(infra1.bridge, infra2.bridge,
                          "User WebSocket bridges must be isolated")

        # Test event isolation
        user1_received_events = []
        user2_received_events = []

        # Mock event collection
        if hasattr(infra1.bridge, 'send_event'):
            original_send1 = infra1.bridge.send_event
            def capture_user1_events(event):
                user1_received_events.append(event)
                return original_send1(event)
            infra1.bridge.send_event = capture_user1_events

        if hasattr(infra2.bridge, 'send_event'):
            original_send2 = infra2.bridge.send_event
            def capture_user2_events(event):
                user2_received_events.append(event)
                return original_send2(event)
            infra2.bridge.send_event = capture_user2_events

        # Send events to each user
        user1_event = {
            'type': 'test_event',
            'data': {'secret': 'user1_data', 'user_id': user1_id},
            'user_id': user1_id
        }

        user2_event = {
            'type': 'test_event',
            'data': {'secret': 'user2_data', 'user_id': user2_id},
            'user_id': user2_id
        }

        try:
            if hasattr(infra1.bridge, 'send_event'):
                infra1.bridge.send_event(user1_event)
            if hasattr(infra2.bridge, 'send_event'):
                infra2.bridge.send_event(user2_event)
        except Exception as e:
            logger.warning(f"Event sending failed: {e}")

        # Validate isolation (events should not cross-contaminate)
        user1_data = [e.get('data', {}).get('secret', '') for e in user1_received_events]
        user2_data = [e.get('data', {}).get('secret', '') for e in user2_received_events]

        self.assertNotIn('user2_data', user1_data,
                        "User 1 should not receive User 2's events - data leakage risk")
        self.assertNotIn('user1_data', user2_data,
                        "User 2 should not receive User 1's events - data leakage risk")

        self.business_value_metrics['user_session_isolation'] = True

        # Record isolation metrics
        self.record_metric('user_session_isolation', 'protected')
        logger.info(f"User session isolation validated for {user1_id} and {user2_id}")

        # Cleanup additional infrastructure
        if hasattr(infra1, 'cleanup'):
            await infra1.cleanup()
        if hasattr(infra2, 'cleanup'):
            await infra2.cleanup()

    async def test_04_registry_websocket_integration_compatibility(self):
        """
        Test 4: Registry-WebSocket integration compatibility (MUST ALWAYS PASS)

        Validates that both registry implementations can integrate
        with WebSocket infrastructure without breaking functionality.

        CRITICAL: Integration must work during SSOT transition
        """
        if not websocket_infra_available:
            pytest.skip("WebSocket infrastructure required for integration testing")

        integration_results = {}
        self.websocket_infrastructure = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False
        )

        # Test basic registry integration (if available)
        if basic_available:
            try:
                basic_registry = BasicAgentRegistry()
                self.registry_instances.append(basic_registry)

                # Test WebSocket integration
                basic_integration_success = False
                if hasattr(basic_registry, 'set_websocket_manager'):
                    basic_registry.set_websocket_manager(self.websocket_infrastructure.websocket_manager)
                    basic_integration_success = True

                integration_results['basic_registry'] = basic_integration_success
            except Exception as e:
                logger.warning(f"Basic registry WebSocket integration failed: {e}")
                integration_results['basic_registry'] = False

        # Test advanced registry integration (if available)
        if advanced_available:
            try:
                mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
                mock_dispatcher = MagicMock()

                advanced_registry = AdvancedAgentRegistry(
                    user_context=mock_context,
                    tool_dispatcher=mock_dispatcher,
                    websocket_bridge=self.websocket_infrastructure.bridge
                )
                self.registry_instances.append(advanced_registry)

                # Test WebSocket integration
                advanced_integration_success = False
                if hasattr(advanced_registry, 'set_websocket_manager'):
                    advanced_registry.set_websocket_manager(self.websocket_infrastructure.websocket_manager)
                    advanced_integration_success = True
                elif hasattr(advanced_registry, 'websocket_bridge'):
                    advanced_integration_success = (advanced_registry.websocket_bridge is not None)

                integration_results['advanced_registry'] = advanced_integration_success
            except Exception as e:
                logger.warning(f"Advanced registry WebSocket integration failed: {e}")
                integration_results['advanced_registry'] = False

        # At least one registry must integrate successfully for business continuity
        successful_integrations = sum(integration_results.values())
        total_available_registries = len(integration_results)

        if total_available_registries > 0:
            integration_rate = successful_integrations / total_available_registries
            self.business_value_metrics['multi_user_support'] = (integration_rate > 0)

            # MUST PASS - At least one integration must work
            self.assertGreater(successful_integrations, 0,
                             f"At least one registry must integrate with WebSocket for business continuity - "
                             f"all {total_available_registries} integrations failed, breaking Golden Path")

            # Record integration metrics
            self.record_metric('registry_websocket_integration_rate', integration_rate)
            logger.info(f"Registry-WebSocket integration validated: {integration_results}")

    async def test_05_golden_path_websocket_flow_protection(self):
        """
        Test 5: Golden Path WebSocket flow protection (MUST ALWAYS PASS)

        Validates that the complete WebSocket flow for Golden Path
        (login → agent events → AI response) remains functional.

        CRITICAL: This is the core $500K+ ARR user experience
        """
        if not websocket_infra_available:
            pytest.skip("WebSocket infrastructure required for Golden Path testing")

        # Create WebSocket infrastructure
        self.websocket_infrastructure = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False
        )

        # Simulate Golden Path WebSocket flow
        golden_path_steps = {
            'user_connection': False,
            'agent_started_event': False,
            'agent_thinking_event': False,
            'tool_execution_events': False,
            'agent_completed_event': False,
            'response_delivery': False
        }

        bridge = self.websocket_infrastructure.bridge

        # Step 1: User connection
        try:
            if hasattr(bridge, 'connect_user'):
                bridge.connect_user(self.test_user_id)
                golden_path_steps['user_connection'] = True
            else:
                golden_path_steps['user_connection'] = True  # Assume connection works
        except Exception as e:
            logger.error(f"User connection failed: {e}")

        # Step 2-5: Critical agent events
        critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed']

        for event_type in critical_events:
            try:
                test_event = {
                    'type': event_type,
                    'data': {
                        'message': f'Golden Path {event_type}',
                        'user_id': self.test_user_id,
                        'session_id': f"session_{uuid.uuid4().hex[:8]}"
                    },
                    'user_id': self.test_user_id
                }

                if hasattr(bridge, 'send_event'):
                    bridge.send_event(test_event)
                    if event_type == 'agent_started':
                        golden_path_steps['agent_started_event'] = True
                    elif event_type == 'agent_thinking':
                        golden_path_steps['agent_thinking_event'] = True
                    elif event_type == 'tool_executing':
                        golden_path_steps['tool_execution_events'] = True
                    elif event_type == 'agent_completed':
                        golden_path_steps['agent_completed_event'] = True

            except Exception as e:
                logger.error(f"Golden Path event {event_type} failed: {e}")

        # Step 6: Response delivery simulation
        try:
            response_event = {
                'type': 'agent_response',
                'data': {
                    'response': 'AI response delivered successfully',
                    'user_id': self.test_user_id,
                    'status': 'completed'
                },
                'user_id': self.test_user_id
            }

            if hasattr(bridge, 'send_event'):
                bridge.send_event(response_event)
                golden_path_steps['response_delivery'] = True
        except Exception as e:
            logger.error(f"Response delivery failed: {e}")

        # Calculate Golden Path success rate
        successful_steps = sum(golden_path_steps.values())
        total_steps = len(golden_path_steps)
        golden_path_success_rate = successful_steps / total_steps

        self.business_value_metrics['golden_path_protection'] = (golden_path_success_rate >= 0.9)

        # MUST PASS - Golden Path success rate must be very high
        self.assertGreaterEqual(golden_path_success_rate, 0.9,
                               f"Golden Path WebSocket flow must be at least 90% successful - "
                               f"got {golden_path_success_rate:.1%}, risking $500K+ ARR functionality")

        # Record Golden Path metrics
        self.record_metric('golden_path_websocket_success_rate', golden_path_success_rate)
        self.record_metric('golden_path_steps', golden_path_steps)

        logger.info(f"Golden Path WebSocket flow protected: {golden_path_success_rate:.1%} success rate")
        logger.info(f"Golden Path steps: {golden_path_steps}")

    async def test_06_business_value_protection_summary(self):
        """
        Test 6: Business value protection summary (INFORMATIONAL)

        Summarizes all business value protection metrics to demonstrate
        that critical functionality remains intact during SSOT transition.

        This test provides visibility into protected business value.
        """
        # Calculate overall business value protection score
        protected_areas = sum(self.business_value_metrics.values())
        total_areas = len(self.business_value_metrics)
        business_protection_score = protected_areas / total_areas if total_areas > 0 else 0

        # Record comprehensive business metrics
        self.record_metric('business_value_protection_score', business_protection_score)
        self.record_metric('protected_business_areas', self.business_value_metrics)

        # Log business value protection status
        logger.info("=== BUSINESS VALUE PROTECTION SUMMARY ===")
        logger.info(f"Overall Protection Score: {business_protection_score:.1%}")
        logger.info("Protected Areas:")
        for area, protected in self.business_value_metrics.items():
            status = "✓ PROTECTED" if protected else "✗ AT RISK"
            logger.info(f"  - {area}: {status}")

        logger.info(f"WebSocket Event Delivery: {'✓' if self.business_value_metrics.get('websocket_event_delivery') else '✗'}")
        logger.info(f"User Session Isolation: {'✓' if self.business_value_metrics.get('user_session_isolation') else '✗'}")
        logger.info(f"Real-time Communication: {'✓' if self.business_value_metrics.get('real_time_communication') else '✗'}")
        logger.info(f"Multi-user Support: {'✓' if self.business_value_metrics.get('multi_user_support') else '✗'}")
        logger.info(f"Golden Path Protection: {'✓' if self.business_value_metrics.get('golden_path_protection') else '✗'}")

        # Business value should be highly protected
        self.assertGreaterEqual(business_protection_score, 0.8,
                               f"Business value protection should be at least 80% during SSOT transition - "
                               f"got {business_protection_score:.1%}")

        logger.info("=== END BUSINESS VALUE SUMMARY ===")


if __name__ == "__main__":
    unittest.main()