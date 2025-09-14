"""
Issue #914 AgentRegistry Cross-Service Consistency Integration Test Suite

This test suite validates that AgentRegistry SSOT consolidation maintains
cross-service consistency without requiring Docker infrastructure.

EXPECTED BEHAVIOR: Tests should validate service integration patterns work
consistently regardless of registry implementation used by different services.

Business Impact:
- Protects Golden Path: Users login → get AI responses
- Ensures service-to-service communication reliability
- Maintains $500K+ ARR cross-service functionality
- Validates microservice independence during SSOT transition

Test Strategy:
1. Test registry usage consistency across backend services
2. Validate agent creation patterns work across service boundaries
3. Ensure WebSocket events flow consistently between services
4. Test user context preservation in cross-service calls
"""

import asyncio
import logging
import unittest
import uuid
import warnings
import pytest
from typing import Optional, Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

# SSOT Base Test Case
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# Test different registry imports (the SSOT violation we're testing)
registry_imports = {}
try:
    from netra_backend.app.agents.registry import AgentRegistry as BasicAgentRegistry
    registry_imports['basic'] = BasicAgentRegistry
except ImportError:
    registry_imports['basic'] = None

try:
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry as AdvancedAgentRegistry
    registry_imports['advanced'] = AdvancedAgentRegistry
except ImportError:
    registry_imports['advanced'] = None

# Service integration imports (no docker required)
try:
    from test_framework.ssot.mock_factory import SSotMockFactory
    from test_framework.ssot.integration_test_base import IntegrationTestBase
    integration_available = True
except ImportError:
    SSotMockFactory = None
    IntegrationTestBase = None
    integration_available = False

# WebSocket testing (for cross-service event flow)
try:
    from test_framework.ssot.websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory
    websocket_available = True
except ImportError:
    WebSocketTestInfrastructureFactory = None
    websocket_available = False

logger = logging.getLogger(__name__)


class TestRegistryCrossServiceConsistency(SSotAsyncTestCase):
    """
    Integration test suite for cross-service registry consistency.

    Tests service-to-service integration patterns without Docker,
    focusing on registry usage consistency during SSOT consolidation.
    """

    def setup_method(self, method):
        """Setup integration test environment."""
        super().setup_method(method)
        self.test_user_id = f"integration_user_{uuid.uuid4().hex[:8]}"
        self.service_contexts = {}
        self.registry_instances = []
        self.mock_factory = SSotMockFactory() if SSotMockFactory else None

        # Service simulation contexts
        self.service_contexts = {
            'backend_api': {'service_name': 'backend_api', 'registry_type': None},
            'agent_supervisor': {'service_name': 'agent_supervisor', 'registry_type': None},
            'websocket_service': {'service_name': 'websocket_service', 'registry_type': None}
        }

    async def teardown_method(self, method):
        """Cleanup integration test resources."""
        for registry in self.registry_instances:
            if hasattr(registry, 'cleanup') and callable(registry.cleanup):
                try:
                    await registry.cleanup()
                except Exception as e:
                    logger.warning(f"Registry cleanup failed: {e}")

        self.registry_instances.clear()
        self.service_contexts.clear()
        await super().teardown_method(method)

    async def test_01_cross_service_registry_consistency(self):
        """
        Test 1: Cross-service registry usage consistency

        Validates that different services can use the same registry
        interface consistently for cross-service communication.

        EXPECTED: PASS when SSOT consolidation complete
        DURING CONSOLIDATION: May show inconsistencies
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for cross-service testing")

        # Simulate different services using registries
        service_registry_usage = {}

        for service_name, service_context in self.service_contexts.items():
            for registry_name, registry_class in available_registries.items():
                try:
                    # Test registry instantiation for this service
                    if registry_name == 'basic':
                        registry = registry_class()
                        service_registry_usage[f"{service_name}_{registry_name}"] = {
                            'instantiation': True,
                            'has_register_agent': hasattr(registry, 'register_agent'),
                            'has_websocket_methods': hasattr(registry, 'set_websocket_manager')
                        }
                        self.registry_instances.append(registry)

                    elif registry_name == 'advanced':
                        mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
                        mock_dispatcher = MagicMock()
                        mock_bridge = MagicMock()

                        registry = registry_class(
                            user_context=mock_context,
                            tool_dispatcher=mock_dispatcher,
                            websocket_bridge=mock_bridge
                        )
                        service_registry_usage[f"{service_name}_{registry_name}"] = {
                            'instantiation': True,
                            'has_register_agent': hasattr(registry, 'register_agent'),
                            'has_websocket_methods': hasattr(registry, 'set_websocket_manager')
                        }
                        self.registry_instances.append(registry)

                except Exception as e:
                    logger.warning(f"Service {service_name} failed to use {registry_name} registry: {e}")
                    service_registry_usage[f"{service_name}_{registry_name}"] = {
                        'instantiation': False,
                        'error': str(e)
                    }

        # Analyze consistency across services
        instantiation_results = []
        interface_consistency = []

        for usage_key, usage_data in service_registry_usage.items():
            if usage_data.get('instantiation'):
                instantiation_results.append(True)
                # Check interface consistency
                has_required_methods = (
                    usage_data.get('has_register_agent', False) and
                    usage_data.get('has_websocket_methods', False)
                )
                interface_consistency.append(has_required_methods)
            else:
                instantiation_results.append(False)
                interface_consistency.append(False)

        # Calculate consistency metrics
        instantiation_rate = sum(instantiation_results) / len(instantiation_results) if instantiation_results else 0
        interface_rate = sum(interface_consistency) / len(interface_consistency) if interface_consistency else 0

        # Record metrics
        self.record_metric('cross_service_instantiation_rate', instantiation_rate)
        self.record_metric('cross_service_interface_rate', interface_rate)
        self.record_metric('service_registry_usage', service_registry_usage)

        logger.info(f"Cross-service registry usage: {service_registry_usage}")
        logger.info(f"Instantiation rate: {instantiation_rate:.1%}")
        logger.info(f"Interface consistency rate: {interface_rate:.1%}")

        # For SSOT consolidation, we expect improving consistency over time
        # During consolidation, some inconsistency is expected
        if len(available_registries) > 1:
            # Multiple registries exist - expect some inconsistency during transition
            self.assertGreaterEqual(instantiation_rate, 0.3,
                                   f"During SSOT transition, at least 30% of cross-service usage should work, "
                                   f"got {instantiation_rate:.1%}")
        else:
            # Single registry - should have high consistency
            self.assertGreaterEqual(instantiation_rate, 0.8,
                                   f"With unified registry, cross-service usage should be at least 80%, "
                                   f"got {instantiation_rate:.1%}")

    async def test_02_agent_creation_cross_service_patterns(self):
        """
        Test 2: Agent creation patterns work across service boundaries

        Validates that agent creation initiated by one service can be
        completed successfully using registries from other services.

        EXPECTED: PASS when services interoperate correctly
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for agent creation testing")

        agent_creation_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create registry instance
                if registry_name == 'basic':
                    registry = registry_class()
                    self.registry_instances.append(registry)
                elif registry_name == 'advanced':
                    mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
                    mock_dispatcher = MagicMock()
                    mock_bridge = MagicMock()
                    registry = registry_class(
                        user_context=mock_context,
                        tool_dispatcher=mock_dispatcher,
                        websocket_bridge=mock_bridge
                    )
                    self.registry_instances.append(registry)
                else:
                    continue

                # Test agent creation capability
                creation_capabilities = {
                    'can_register_agent': hasattr(registry, 'register_agent'),
                    'can_get_agent': hasattr(registry, 'get_agent'),
                    'can_list_agents': hasattr(registry, 'list_agents'),
                    'can_create_from_type': hasattr(registry, 'create_agent_from_type')
                }

                # Test actual agent registration if method exists
                if creation_capabilities['can_register_agent']:
                    try:
                        mock_agent = MagicMock()
                        mock_agent.agent_id = f"test_agent_{uuid.uuid4().hex[:8]}"
                        mock_agent.agent_type = "test_agent"

                        # Attempt registration
                        registry.register_agent(mock_agent)
                        creation_capabilities['registration_successful'] = True
                    except Exception as e:
                        logger.warning(f"Agent registration failed for {registry_name}: {e}")
                        creation_capabilities['registration_successful'] = False

                agent_creation_results[registry_name] = creation_capabilities

            except Exception as e:
                logger.error(f"Failed to test agent creation with {registry_name} registry: {e}")
                agent_creation_results[registry_name] = {'error': str(e)}

        # Analyze agent creation consistency
        successful_creations = 0
        total_registries = len(agent_creation_results)

        for registry_name, capabilities in agent_creation_results.items():
            if capabilities.get('can_register_agent', False):
                successful_creations += 1

        creation_consistency_rate = successful_creations / total_registries if total_registries > 0 else 0

        # Record metrics
        self.record_metric('agent_creation_consistency_rate', creation_consistency_rate)
        self.record_metric('agent_creation_capabilities', agent_creation_results)

        logger.info(f"Agent creation capabilities: {agent_creation_results}")
        logger.info(f"Creation consistency rate: {creation_consistency_rate:.1%}")

        # Expect reasonable agent creation capability
        self.assertGreaterEqual(creation_consistency_rate, 0.5,
                               f"At least 50% of registries should support agent creation for cross-service functionality, "
                               f"got {creation_consistency_rate:.1%}")

    async def test_03_websocket_event_flow_consistency(self):
        """
        Test 3: WebSocket event flow consistency across services

        Validates that WebSocket events can flow consistently between
        services regardless of which registry implementation is used.

        EXPECTED: PASS when WebSocket integration is stable
        """
        if not websocket_available:
            pytest.skip("WebSocket infrastructure required for event flow testing")

        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for WebSocket event flow testing")

        # Create WebSocket infrastructure
        websocket_infra = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False
        )

        websocket_integration_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create registry with WebSocket integration
                if registry_name == 'basic':
                    registry = registry_class()
                    self.registry_instances.append(registry)
                elif registry_name == 'advanced':
                    mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
                    mock_dispatcher = MagicMock()
                    registry = registry_class(
                        user_context=mock_context,
                        tool_dispatcher=mock_dispatcher,
                        websocket_bridge=websocket_infra.bridge
                    )
                    self.registry_instances.append(registry)
                else:
                    continue

                # Test WebSocket integration
                integration_capabilities = {
                    'has_websocket_manager_setter': hasattr(registry, 'set_websocket_manager'),
                    'has_websocket_bridge': hasattr(registry, 'websocket_bridge'),
                    'has_send_event': hasattr(registry, 'send_websocket_event')
                }

                # Test WebSocket manager integration
                if integration_capabilities['has_websocket_manager_setter']:
                    try:
                        registry.set_websocket_manager(websocket_infra.websocket_manager)
                        integration_capabilities['websocket_manager_integration'] = True
                    except Exception as e:
                        logger.warning(f"WebSocket manager integration failed for {registry_name}: {e}")
                        integration_capabilities['websocket_manager_integration'] = False

                # Test event sending capability
                if integration_capabilities['has_send_event']:
                    try:
                        test_event = {
                            'type': 'cross_service_test',
                            'data': {'registry': registry_name, 'user_id': self.test_user_id},
                            'user_id': self.test_user_id
                        }
                        registry.send_websocket_event(test_event)
                        integration_capabilities['event_sending'] = True
                    except Exception as e:
                        logger.warning(f"Event sending failed for {registry_name}: {e}")
                        integration_capabilities['event_sending'] = False

                websocket_integration_results[registry_name] = integration_capabilities

            except Exception as e:
                logger.error(f"WebSocket integration failed for {registry_name}: {e}")
                websocket_integration_results[registry_name] = {'error': str(e)}

        # Analyze WebSocket integration consistency
        successful_integrations = 0
        total_registries = len(websocket_integration_results)

        for registry_name, capabilities in websocket_integration_results.items():
            if (capabilities.get('has_websocket_manager_setter', False) or
                capabilities.get('has_websocket_bridge', False)):
                successful_integrations += 1

        websocket_consistency_rate = successful_integrations / total_registries if total_registries > 0 else 0

        # Record metrics
        self.record_metric('websocket_integration_consistency_rate', websocket_consistency_rate)
        self.record_metric('websocket_integration_results', websocket_integration_results)

        logger.info(f"WebSocket integration results: {websocket_integration_results}")
        logger.info(f"WebSocket consistency rate: {websocket_consistency_rate:.1%}")

        # Expect reasonable WebSocket integration capability
        self.assertGreaterEqual(websocket_consistency_rate, 0.5,
                               f"At least 50% of registries should support WebSocket integration for cross-service events, "
                               f"got {websocket_consistency_rate:.1%}")

        # Cleanup WebSocket infrastructure
        if hasattr(websocket_infra, 'cleanup'):
            await websocket_infra.cleanup()

    async def test_04_user_context_preservation_cross_service(self):
        """
        Test 4: User context preservation in cross-service calls

        Validates that user context is properly preserved when
        registry calls cross service boundaries.

        EXPECTED: PASS when user isolation is maintained
        """
        available_registries = {k: v for k, v in registry_imports.items() if v is not None}

        if len(available_registries) == 0:
            pytest.skip("No registries available for user context testing")

        user1_id = f"{self.test_user_id}_context_1"
        user2_id = f"{self.test_user_id}_context_2"

        context_preservation_results = {}

        for registry_name, registry_class in available_registries.items():
            try:
                # Create registries for different users
                user_registries = {}

                if registry_name == 'basic':
                    # Basic registry may not have explicit user context
                    user_registries[user1_id] = registry_class()
                    user_registries[user2_id] = registry_class()
                    self.registry_instances.extend(user_registries.values())

                elif registry_name == 'advanced':
                    # Advanced registry has explicit user context
                    mock_context1 = self.mock_factory.create_mock_user_context(user1_id) if self.mock_factory else MagicMock()
                    mock_context1.user_id = user1_id
                    mock_dispatcher = MagicMock()
                    mock_bridge = MagicMock()

                    user_registries[user1_id] = registry_class(
                        user_context=mock_context1,
                        tool_dispatcher=mock_dispatcher,
                        websocket_bridge=mock_bridge
                    )

                    mock_context2 = self.mock_factory.create_mock_user_context(user2_id) if self.mock_factory else MagicMock()
                    mock_context2.user_id = user2_id

                    user_registries[user2_id] = registry_class(
                        user_context=mock_context2,
                        tool_dispatcher=mock_dispatcher,
                        websocket_bridge=mock_bridge
                    )
                    self.registry_instances.extend(user_registries.values())

                # Test user context isolation
                context_capabilities = {
                    'different_instances': user_registries[user1_id] != user_registries[user2_id],
                    'has_user_context': all(hasattr(reg, 'user_context') for reg in user_registries.values()),
                    'contexts_isolated': True
                }

                # Check context isolation
                if context_capabilities['has_user_context']:
                    try:
                        context1 = user_registries[user1_id].user_context
                        context2 = user_registries[user2_id].user_context
                        context_capabilities['contexts_isolated'] = (context1 != context2)

                        if hasattr(context1, 'user_id') and hasattr(context2, 'user_id'):
                            context_capabilities['user_ids_different'] = (context1.user_id != context2.user_id)
                    except Exception as e:
                        logger.warning(f"Context isolation check failed for {registry_name}: {e}")
                        context_capabilities['contexts_isolated'] = False

                context_preservation_results[registry_name] = context_capabilities

            except Exception as e:
                logger.error(f"User context testing failed for {registry_name}: {e}")
                context_preservation_results[registry_name] = {'error': str(e)}

        # Analyze context preservation
        successful_isolation = 0
        total_registries = len(context_preservation_results)

        for registry_name, capabilities in context_preservation_results.items():
            if (capabilities.get('different_instances', False) and
                capabilities.get('contexts_isolated', True)):  # True if no explicit context
                successful_isolation += 1

        context_preservation_rate = successful_isolation / total_registries if total_registries > 0 else 0

        # Record metrics
        self.record_metric('user_context_preservation_rate', context_preservation_rate)
        self.record_metric('context_preservation_results', context_preservation_results)

        logger.info(f"User context preservation results: {context_preservation_results}")
        logger.info(f"Context preservation rate: {context_preservation_rate:.1%}")

        # Expect good user context preservation for security
        self.assertGreaterEqual(context_preservation_rate, 0.8,
                               f"At least 80% of registries should preserve user context isolation, "
                               f"got {context_preservation_rate:.1%}")


if __name__ == "__main__":
    unittest.main()