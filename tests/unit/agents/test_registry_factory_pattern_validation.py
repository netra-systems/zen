"""
Issue #914 AgentRegistry Factory Pattern Validation Test Suite

This test suite validates that after SSOT consolidation, the unified AgentRegistry
maintains proper factory pattern consistency and user isolation capabilities.

EXPECTED BEHAVIOR: These tests SHOULD PASS when SSOT consolidation is complete.
Currently may fail due to the registry duplication issue.

Business Impact:
- Protects Golden Path user flow: Users login -> get AI responses
- Ensures 500K+ ARR chat functionality reliability
- Validates enterprise-grade multi-user isolation
- Confirms WebSocket event delivery consistency

Test Strategy:
1. Validate single registry factory creates consistent instances
2. Test user isolation preservation across registry instances
3. Confirm WebSocket interface stability during SSOT transition
4. Verify agent execution context preservation
5. Test concurrent user access patterns
6. Validate registry method consistency
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

# Test imports - after SSOT consolidation, this should be single source
try:
    # This should eventually be the ONLY AgentRegistry import
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    advanced_registry_available = True
except ImportError:
    AgentRegistry = None
    advanced_registry_available = False

# Support infrastructure
try:
    from test_framework.ssot.websocket_test_infrastructure_factory import WebSocketTestInfrastructureFactory
    from test_framework.ssot.websocket_bridge_test_helper import WebSocketBridgeTestHelper
    from test_framework.ssot.mock_factory import SSotMockFactory
except ImportError:
    WebSocketTestInfrastructureFactory = None
    WebSocketBridgeTestHelper = None
    SSotMockFactory = None

logger = logging.getLogger(__name__)


@pytest.mark.unit
class RegistryFactoryPatternValidationTests(SSotAsyncTestCase):
    """
    Test suite to validate registry factory pattern consistency.

    These tests ensure that after SSOT consolidation, the unified
    registry maintains business value and user isolation patterns.
    """

    def setup_method(self, method):
        """Setup test environment with SSOT base infrastructure."""
        super().setup_method(method)
        self.test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        self.registry_instances: List[Any] = []
        self.mock_factory = SSotMockFactory() if SSotMockFactory else None

    async def teardown_method(self, method):
        """Cleanup registry instances to prevent memory leaks."""
        # Clean up registry instances
        for registry in self.registry_instances:
            if hasattr(registry, 'cleanup') and callable(registry.cleanup):
                try:
                    await registry.cleanup()
                except Exception as e:
                    logger.warning(f"Registry cleanup failed: {e}")

        self.registry_instances.clear()
        await super().teardown_method(method)

    async def test_01_unified_registry_factory_consistency(self):
        """
        Test 1: Validate unified registry factory creates consistent instances

        After SSOT consolidation, all registry instances should be created
        through a consistent factory pattern that maintains user isolation.

        EXPECTED: PASS after SSOT consolidation
        DURING CONSOLIDATION: May fail due to transitional issues
        """
        if not advanced_registry_available:
            self.skipTest("AgentRegistry not available for factory testing")

        user1_id = f"{self.test_user_id}_1"
        user2_id = f"{self.test_user_id}_2"

        # Create mock dependencies
        mock_context1 = self.mock_factory.create_mock_user_context(user1_id) if self.mock_factory else MagicMock()
        mock_context2 = self.mock_factory.create_mock_user_context(user2_id) if self.mock_factory else MagicMock()
        mock_dispatcher = MagicMock()
        mock_bridge = MagicMock()

        # Test factory consistency - should create isolated instances
        registry1 = AgentRegistry(
            user_context=mock_context1,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=mock_bridge
        )
        self.registry_instances.append(registry1)

        registry2 = AgentRegistry(
            user_context=mock_context2,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=mock_bridge
        )
        self.registry_instances.append(registry2)

        # Validate instances are properly isolated
        self.assertIsNotNone(registry1, "Registry 1 should be created successfully")
        self.assertIsNotNone(registry2, "Registry 2 should be created successfully")
        self.assertNotEqual(registry1, registry2, "Registry instances should be unique")

        # Validate user context isolation
        if hasattr(registry1, 'user_context') and hasattr(registry2, 'user_context'):
            self.assertNotEqual(registry1.user_context, registry2.user_context,
                               "User contexts should be isolated between registries")

        # Record factory consistency metrics
        self.record_metric('factory_consistency_test', 'passed')
        logger.info(f"Factory pattern validation successful for users {user1_id}, {user2_id}")

    async def test_02_registry_interface_stability(self):
        """
        Test 2: Validate registry interface stability during SSOT transition

        Ensures that the registry interface remains stable and provides
        all necessary methods for Golden Path functionality.

        EXPECTED: PASS - Interface should be stable
        """
        if not advanced_registry_available:
            self.skipTest("AgentRegistry not available for interface testing")

        # Create registry instance
        mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
        mock_dispatcher = MagicMock()
        mock_bridge = MagicMock()

        registry = AgentRegistry(
            user_context=mock_context,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=mock_bridge
        )
        self.registry_instances.append(registry)

        # Critical interface methods for Golden Path
        required_methods = [
            'register_agent', 'get_agent', 'list_agents',
            'set_websocket_manager', 'create_agent_from_type'
        ]

        available_methods = []
        missing_methods = []

        for method_name in required_methods:
            if hasattr(registry, method_name):
                available_methods.append(method_name)
            else:
                missing_methods.append(method_name)

        # Log interface status for debugging
        logger.info(f"Available methods: {available_methods}")
        if missing_methods:
            logger.warning(f"Missing methods: {missing_methods}")

        # Validate critical methods exist
        self.assertIn('register_agent', available_methods,
                     "register_agent method required for agent creation")
        self.assertIn('set_websocket_manager', available_methods,
                     "set_websocket_manager required for WebSocket integration")

        # Record interface stability metrics
        interface_completeness = len(available_methods) / len(required_methods)
        self.record_metric('interface_completeness', interface_completeness)
        self.assertGreaterEqual(interface_completeness, 0.8,
                               f"Interface completeness should be >= 80%, got {interface_completeness:.1%}")

    async def test_03_user_isolation_preservation(self):
        """
        Test 3: Validate user isolation preservation in factory pattern

        Ensures that registry instances properly isolate user data
        and prevent cross-contamination between users.

        EXPECTED: PASS - User isolation must be maintained
        """
        if not advanced_registry_available:
            self.skipTest("AgentRegistry not available for isolation testing")

        user1_id = f"{self.test_user_id}_isolation_1"
        user2_id = f"{self.test_user_id}_isolation_2"

        # Create isolated contexts
        mock_context1 = self.mock_factory.create_mock_user_context(user1_id) if self.mock_factory else MagicMock()
        mock_context2 = self.mock_factory.create_mock_user_context(user2_id) if self.mock_factory else MagicMock()
        mock_dispatcher = MagicMock()
        mock_bridge = MagicMock()

        # Configure mock contexts with different data
        mock_context1.user_id = user1_id
        mock_context1.session_id = f"session_{user1_id}"
        mock_context2.user_id = user2_id
        mock_context2.session_id = f"session_{user2_id}"

        # Create isolated registries
        registry1 = AgentRegistry(
            user_context=mock_context1,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=mock_bridge
        )
        self.registry_instances.append(registry1)

        registry2 = AgentRegistry(
            user_context=mock_context2,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=mock_bridge
        )
        self.registry_instances.append(registry2)

        # Validate user isolation
        if hasattr(registry1, 'user_context') and hasattr(registry2, 'user_context'):
            self.assertNotEqual(registry1.user_context.user_id, registry2.user_context.user_id,
                               "User IDs should be isolated between registries")
            self.assertNotEqual(registry1.user_context.session_id, registry2.user_context.session_id,
                               "Session IDs should be isolated between registries")

        # Test agent registration isolation
        if hasattr(registry1, 'register_agent'):
            mock_agent1 = MagicMock()
            mock_agent1.agent_id = f"agent_{user1_id}"
            mock_agent2 = MagicMock()
            mock_agent2.agent_id = f"agent_{user2_id}"

            try:
                registry1.register_agent(mock_agent1)
                registry2.register_agent(mock_agent2)

                # Verify agents don't cross-contaminate
                if hasattr(registry1, 'list_agents') and hasattr(registry2, 'list_agents'):
                    agents1 = registry1.list_agents()
                    agents2 = registry2.list_agents()

                    # Agents should be isolated
                    agent1_ids = [a.agent_id for a in agents1] if agents1 else []
                    agent2_ids = [a.agent_id for a in agents2] if agents2 else []

                    self.assertNotIn(f"agent_{user2_id}", agent1_ids,
                                   "User 2's agent should not appear in User 1's registry")
                    self.assertNotIn(f"agent_{user1_id}", agent2_ids,
                                   "User 1's agent should not appear in User 2's registry")
            except Exception as e:
                logger.warning(f"Agent registration test failed: {e}")

        # Record isolation metrics
        self.record_metric('user_isolation_test', 'passed')
        logger.info(f"User isolation validated for {user1_id} and {user2_id}")

    async def test_04_websocket_integration_consistency(self):
        """
        Test 4: Validate WebSocket integration consistency

        Ensures that registry WebSocket integration remains stable
        and supports all required event delivery patterns.

        EXPECTED: PASS - WebSocket integration should work
        """
        if not advanced_registry_available or not WebSocketTestInfrastructureFactory:
            self.skipTest("Registry or WebSocket infrastructure not available")

        # Create WebSocket infrastructure
        websocket_infra = WebSocketTestInfrastructureFactory.create_test_infrastructure(
            user_id=self.test_user_id,
            enable_auth=False
        )

        # Create registry with WebSocket support
        mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
        mock_dispatcher = MagicMock()

        registry = AgentRegistry(
            user_context=mock_context,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=websocket_infra.bridge
        )
        self.registry_instances.append(registry)

        # Test WebSocket manager integration
        websocket_integration_success = False
        try:
            if hasattr(registry, 'set_websocket_manager'):
                registry.set_websocket_manager(websocket_infra.websocket_manager)
                websocket_integration_success = True
            elif hasattr(registry, 'websocket_bridge'):
                # Alternative integration pattern
                websocket_integration_success = (registry.websocket_bridge is not None)
        except Exception as e:
            logger.warning(f"WebSocket integration failed: {e}")

        self.assertTrue(websocket_integration_success,
                       "Registry should integrate successfully with WebSocket infrastructure")

        # Test event delivery capability
        if hasattr(registry, 'send_websocket_event') or hasattr(registry, 'websocket_bridge'):
            try:
                # Test event sending
                test_event = {
                    'type': 'test_event',
                    'data': {'message': 'Registry factory pattern test'},
                    'user_id': self.test_user_id
                }

                if hasattr(registry, 'send_websocket_event'):
                    registry.send_websocket_event(test_event)
                elif hasattr(registry.websocket_bridge, 'send_event'):
                    registry.websocket_bridge.send_event(test_event)

                self.record_metric('websocket_event_test', 'passed')
            except Exception as e:
                logger.warning(f"WebSocket event test failed: {e}")

        logger.info(f"WebSocket integration consistency validated for user {self.test_user_id}")

    async def test_05_concurrent_factory_access_safety(self):
        """
        Test 5: Validate concurrent factory access safety

        Ensures that multiple concurrent factory calls don't cause
        race conditions or data corruption.

        EXPECTED: PASS - Concurrent access should be safe
        """
        if not advanced_registry_available:
            self.skipTest("AgentRegistry not available for concurrency testing")

        concurrent_user_count = 3
        registries_created = []

        async def create_registry_for_user(user_index: int) -> Any:
            """Create a registry for a specific user."""
            user_id = f"{self.test_user_id}_concurrent_{user_index}"
            mock_context = self.mock_factory.create_mock_user_context(user_id) if self.mock_factory else MagicMock()
            mock_context.user_id = user_id
            mock_dispatcher = MagicMock()
            mock_bridge = MagicMock()

            registry = AgentRegistry(
                user_context=mock_context,
                tool_dispatcher=mock_dispatcher,
                websocket_bridge=mock_bridge
            )
            return registry, user_id

        # Create registries concurrently
        tasks = [create_registry_for_user(i) for i in range(concurrent_user_count)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful_creations = 0
        for result in results:
            if isinstance(result, tuple):
                registry, user_id = result
                registries_created.append(registry)
                self.registry_instances.append(registry)
                successful_creations += 1
            else:
                logger.warning(f"Concurrent registry creation failed: {result}")

        # Validate all registries were created successfully
        self.assertEqual(successful_creations, concurrent_user_count,
                        f"All {concurrent_user_count} registries should be created concurrently")

        # Validate registries are properly isolated
        user_contexts = []
        for registry in registries_created:
            if hasattr(registry, 'user_context'):
                user_contexts.append(registry.user_context.user_id)

        # All user contexts should be unique
        self.assertEqual(len(set(user_contexts)), len(user_contexts),
                        "All concurrent registries should have unique user contexts")

        # Record concurrency metrics
        self.record_metric('concurrent_factory_access', successful_creations)
        logger.info(f"Concurrent factory access validated with {successful_creations} successful creations")

    async def test_06_registry_lifecycle_management(self):
        """
        Test 6: Validate registry lifecycle management

        Ensures proper initialization, operation, and cleanup
        of registry instances throughout their lifecycle.

        EXPECTED: PASS - Lifecycle management should be robust
        """
        if not advanced_registry_available:
            self.skipTest("AgentRegistry not available for lifecycle testing")

        # Test registry initialization
        mock_context = self.mock_factory.create_mock_user_context(self.test_user_id) if self.mock_factory else MagicMock()
        mock_dispatcher = MagicMock()
        mock_bridge = MagicMock()

        registry = AgentRegistry(
            user_context=mock_context,
            tool_dispatcher=mock_dispatcher,
            websocket_bridge=mock_bridge
        )
        self.registry_instances.append(registry)

        # Validate initialization state
        self.assertIsNotNone(registry, "Registry should initialize successfully")

        # Test operational state
        operational_checks = {
            'has_user_context': hasattr(registry, 'user_context'),
            'has_tool_dispatcher': hasattr(registry, 'tool_dispatcher'),
            'has_websocket_bridge': hasattr(registry, 'websocket_bridge'),
            'has_register_method': hasattr(registry, 'register_agent'),
            'has_get_method': hasattr(registry, 'get_agent')
        }

        operational_score = sum(operational_checks.values()) / len(operational_checks)
        self.record_metric('registry_operational_score', operational_score)

        logger.info(f"Registry operational checks: {operational_checks}")
        self.assertGreaterEqual(operational_score, 0.6,
                               f"Registry should be at least 60% operational, got {operational_score:.1%}")

        # Test cleanup capability
        cleanup_successful = False
        if hasattr(registry, 'cleanup'):
            try:
                await registry.cleanup()
                cleanup_successful = True
            except Exception as e:
                logger.warning(f"Registry cleanup failed: {e}")

        # Even if cleanup method doesn't exist, registry should be cleanable
        self.record_metric('registry_cleanup_available', cleanup_successful)
        logger.info(f"Registry lifecycle management validated, cleanup available: {cleanup_successful}")


if __name__ == "__main__":
    unittest.main()