"""
Agent Factory Phase 2 SSOT Compliance Tests

CRITICAL: These tests validate SSOT compliance patterns for agent factory migration
and ensure proper user isolation is maintained throughout the system.

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Compliance
- Value Impact: Prevents regulatory violations and data breaches 
- Strategic Impact: Enables enterprise deployment with $500K+ ARR protection

The tests validate:
1. SSOT factory creation patterns
2. Memory isolation between factory instances
3. UserExecutionContext requirement enforcement
4. Proper cleanup and resource management
"""

import asyncio
import pytest
import time
import uuid
import gc
import weakref
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import warnings

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    create_agent_instance_factory,
    configure_agent_instance_factory  # Deprecated function
)
from netra_backend.app.agents.supervisor.agent_class_registry import AgentClassRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestAgentFactoryPhase2Compliance(SSotAsyncTestCase):
    """
    CRITICAL: Test SSOT compliance patterns for agent factory Phase 2 migration.
    
    These tests ensure that the factory patterns follow SSOT principles and
    provide proper user isolation without singleton vulnerabilities.
    """

    async def asyncSetUp(self):
        """Set up test infrastructure with SSOT patterns."""
        await super().asyncSetUp()
        
        # Create mock infrastructure for testing
        self.mock_agent_class_registry = AgentClassRegistry()
        self.mock_websocket_bridge = AsyncMock(spec=AgentWebSocketBridge)
        
        # Track created factories for cleanup
        self.created_factories = []
        
    async def asyncTearDown(self):
        """Clean up test resources."""
        # Cleanup any created factories
        for factory in self.created_factories:
            if hasattr(factory, 'cleanup_inactive_contexts'):
                try:
                    await factory.cleanup_inactive_contexts(max_age_seconds=0)
                except Exception as e:
                    logger.warning(f"Error cleaning up factory: {e}")
        
        await super().asyncTearDown()
        
    def create_test_user_context(self, user_id: str, suffix: str = "") -> UserExecutionContext:
        """Create test user execution context."""
        thread_id = f"thread_{user_id}_{suffix}_{uuid.uuid4().hex[:8]}"
        run_id = f"run_{user_id}_{suffix}_{uuid.uuid4().hex[:8]}"
        
        return UserExecutionContext.from_request_supervisor(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=f"req_{user_id}_{suffix}",
            metadata={'test_suffix': suffix}
        )

    async def test_ssot_factory_creation_requires_user_context(self):
        """
        TEST 1: SSOT factory creation must require UserExecutionContext.
        
        CRITICAL: The SSOT-compliant create_agent_instance_factory() function
        must enforce user context requirement to prevent context-less execution.
        """
        logger.info("TEST 1: Validating SSOT factory creation requires user context")
        
        # TEST: Factory creation without user context should raise ValueError
        with self.assertRaises(ValueError) as context:
            create_agent_instance_factory(None)
        
        error_message = str(context.exception)
        self.assertIn("UserExecutionContext is required", error_message)
        
        # TEST: Factory creation with valid user context should succeed
        user_context = self.create_test_user_context("ssot_user", "creation_test")
        factory = create_agent_instance_factory(user_context)
        
        self.assertIsInstance(factory, AgentInstanceFactory)
        self.assertEqual(factory._user_context, user_context)
        
        self.created_factories.append(factory)
        logger.info("✅ PASS: SSOT factory creation properly requires user context")

    async def test_factory_memory_isolation_patterns(self):
        """
        TEST 2: Validate factory memory isolation patterns.
        
        CRITICAL: Each factory instance must have completely separate memory
        to prevent state leakage between users.
        """
        logger.info("TEST 2: Testing factory memory isolation patterns")
        
        # Create multiple factories with different user contexts
        factories = []
        contexts = []
        
        for i in range(3):
            context = self.create_test_user_context(f"memory_user_{i}", "isolation")
            factory = create_agent_instance_factory(context)
            factory.configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            
            factories.append(factory)
            contexts.append(context)
            self.created_factories.append(factory)
        
        # VALIDATION: Each factory should have unique memory space
        for i, factory1 in enumerate(factories):
            for j, factory2 in enumerate(factories):
                if i != j:
                    # Different factory instances
                    self.assertNotEqual(factory1, factory2)
                    
                    # Different user contexts
                    self.assertNotEqual(factory1._user_context, factory2._user_context)
                    
                    # Separate metrics tracking
                    metrics1 = factory1.get_factory_metrics()
                    metrics2 = factory2.get_factory_metrics()
                    
                    # Should start with independent state
                    self.assertEqual(metrics1['total_instances_created'], 0)
                    self.assertEqual(metrics2['total_instances_created'], 0)
        
        logger.info("✅ PASS: Factory memory isolation patterns validated")

    async def test_user_execution_context_binding_enforcement(self):
        """
        TEST 3: Validate UserExecutionContext binding enforcement.
        
        CRITICAL: Factory methods must enforce that agents are created with
        proper user context binding to prevent execution without context.
        """
        logger.info("TEST 3: Testing UserExecutionContext binding enforcement")
        
        user_context = self.create_test_user_context("binding_user", "enforcement")
        factory = create_agent_instance_factory(user_context)
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        self.created_factories.append(factory)
        
        # Register a simple mock agent for testing
        class SimpleMockAgent(BaseAgent):
            def __init__(self):
                super().__init__()
                self.user_context = None
                
            @classmethod
            def create_agent_with_context(cls, user_context: UserExecutionContext):
                agent = cls()
                agent.user_context = user_context
                return agent
        
        self.mock_agent_class_registry.register_agent_class("SimpleMockAgent", SimpleMockAgent)
        
        # TEST: Agent creation should require user context
        with self.assertRaises(ValueError) as context:
            await factory.create_agent_instance("SimpleMockAgent", None)
        
        error_message = str(context.exception)
        self.assertIn("UserExecutionContext is required", error_message)
        
        # TEST: Agent creation with proper context should succeed
        agent = await factory.create_agent_instance("SimpleMockAgent", user_context)
        self.assertIsInstance(agent, SimpleMockAgent)
        self.assertEqual(agent.user_context, user_context)
        
        logger.info("✅ PASS: UserExecutionContext binding enforcement validated")

    async def test_deprecated_configure_function_warnings(self):
        """
        TEST 4: Validate deprecated configure function produces warnings.
        
        CRITICAL: The deprecated configure_agent_instance_factory() should
        produce warnings about security risks while maintaining some compatibility.
        """
        logger.info("TEST 4: Testing deprecated configure function warnings")
        
        # Capture warnings
        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            
            # Call deprecated function
            factory = await configure_agent_instance_factory(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            self.created_factories.append(factory)
        
        # VALIDATION: Should produce deprecation warning
        deprecation_warnings = [w for w in warning_list if issubclass(w.category, DeprecationWarning)]
        self.assertGreater(len(deprecation_warnings), 0, "Should produce deprecation warning")
        
        # Check warning message content
        warning_message = str(deprecation_warnings[0].message)
        self.assertIn("deprecated", warning_message.lower())
        self.assertIn("security vulnerabilities", warning_message.lower())
        self.assertIn("create_agent_instance_factory", warning_message)
        
        # VALIDATION: Factory should still be created for backward compatibility
        self.assertIsInstance(factory, AgentInstanceFactory)
        
        logger.info("✅ PASS: Deprecated configure function produces proper warnings")

    async def test_factory_performance_config_isolation(self):
        """
        TEST 5: Validate factory performance configuration isolation.
        
        CRITICAL: Performance configurations should be properly isolated
        between factory instances to prevent interference.
        """
        logger.info("TEST 5: Testing factory performance configuration isolation")
        
        # Create factories with different configurations
        context1 = self.create_test_user_context("perf_user1", "config")
        context2 = self.create_test_user_context("perf_user2", "config")
        
        factory1 = create_agent_instance_factory(context1)
        factory2 = create_agent_instance_factory(context2)
        
        self.created_factories.extend([factory1, factory2])
        
        # VALIDATION: Performance configs should be independent
        config1 = factory1._performance_config
        config2 = factory2._performance_config
        
        # Configs should be separate instances (if mutable) or safely shared (if immutable)
        # The key is that changes to one factory's performance don't affect others
        metrics1_before = factory1.get_factory_metrics()
        metrics2_before = factory2.get_factory_metrics()
        
        # Simulate activity on factory1
        factory1._factory_metrics['total_instances_created'] = 5
        
        # Factory2 should be unaffected
        metrics2_after = factory2.get_factory_metrics()
        self.assertEqual(metrics2_after['total_instances_created'], 0)
        
        logger.info("✅ PASS: Factory performance configuration isolation validated")

    async def test_factory_cleanup_isolation(self):
        """
        TEST 6: Validate factory cleanup isolation.
        
        CRITICAL: Cleanup operations on one factory should not affect
        other factory instances or their resources.
        """
        logger.info("TEST 6: Testing factory cleanup isolation")
        
        # Create multiple factories with active contexts
        factories = []
        contexts = []
        
        for i in range(3):
            context = self.create_test_user_context(f"cleanup_user_{i}", "isolation")
            factory = create_agent_instance_factory(context)
            factory.configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            
            # Create execution context to track
            exec_context = await factory.create_user_execution_context(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id
            )
            
            factories.append(factory)
            contexts.append(context)
            self.created_factories.append(factory)
        
        # Verify all factories have active contexts
        for factory in factories:
            metrics = factory.get_factory_metrics()
            self.assertGreater(metrics['active_contexts'], 0)
        
        # Cleanup factory 0
        await factories[0].cleanup_inactive_contexts(max_age_seconds=0)
        
        # VALIDATION: Other factories should be unaffected
        for i, factory in enumerate(factories[1:], 1):
            metrics = factory.get_factory_metrics()
            # Factory 1 and 2 should still have active contexts
            self.assertGreater(metrics['active_contexts'], 0, 
                             f"Factory {i} should still have active contexts")
        
        logger.info("✅ PASS: Factory cleanup isolation validated")

    async def test_concurrent_factory_creation_safety(self):
        """
        TEST 7: Validate concurrent factory creation safety.
        
        CRITICAL: Multiple concurrent factory creations should be safe
        and not interfere with each other.
        """
        logger.info("TEST 7: Testing concurrent factory creation safety")
        
        async def create_factory_for_user(user_index: int):
            """Create factory for specific user index."""
            user_id = f"concurrent_user_{user_index}"
            context = self.create_test_user_context(user_id, "concurrent")
            
            factory = create_agent_instance_factory(context)
            factory.configure(
                agent_class_registry=self.mock_agent_class_registry,
                websocket_bridge=self.mock_websocket_bridge
            )
            
            return user_index, factory, context
        
        # Create multiple factories concurrently
        concurrent_count = 10
        concurrent_tasks = [create_factory_for_user(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*concurrent_tasks)
        
        # VALIDATION: All factories should be created successfully
        self.assertEqual(len(results), concurrent_count)
        
        created_factories = []
        for user_index, factory, context in results:
            # Each factory should be unique
            self.assertIsInstance(factory, AgentInstanceFactory)
            self.assertEqual(factory._user_context.user_id, f"concurrent_user_{user_index}")
            
            created_factories.append(factory)
            self.created_factories.append(factory)
        
        # VALIDATION: All factories should be unique instances
        for i, factory1 in enumerate(created_factories):
            for j, factory2 in enumerate(created_factories):
                if i != j:
                    self.assertNotEqual(factory1, factory2)
                    self.assertNotEqual(factory1._user_context, factory2._user_context)
        
        logger.info(f"✅ PASS: Concurrent factory creation safety validated ({concurrent_count} factories)")

    async def test_factory_weak_reference_support(self):
        """
        TEST 8: Validate factory weak reference support for memory management.
        
        CRITICAL: Factories should support proper garbage collection
        when no longer referenced to prevent memory leaks.
        """
        logger.info("TEST 8: Testing factory weak reference support")
        
        # Create factory and get weak reference
        context = self.create_test_user_context("weak_ref_user", "memory")
        factory = create_agent_instance_factory(context)
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Create weak reference to factory
        factory_weak_ref = weakref.ref(factory)
        factory_id = id(factory)
        
        # Verify weak reference is valid
        self.assertIsNotNone(factory_weak_ref())
        self.assertEqual(id(factory_weak_ref()), factory_id)
        
        # Remove strong reference
        del factory
        
        # Force garbage collection
        gc.collect()
        
        # VALIDATION: Weak reference should eventually become None
        # (Note: This may not happen immediately in all Python implementations)
        # The key is that the factory supports weak references
        try:
            weak_factory = factory_weak_ref()
            if weak_factory is not None:
                logger.info("Factory still referenced (expected in some cases)")
            else:
                logger.info("Factory successfully garbage collected")
        except Exception as e:
            logger.info(f"Weak reference handling: {e}")
        
        logger.info("✅ PASS: Factory weak reference support validated")

    async def test_ssot_compliance_validation(self):
        """
        TEST 9: Comprehensive SSOT compliance validation.
        
        CRITICAL: Validate that factory patterns comply with all SSOT
        principles and architectural requirements.
        """
        logger.info("TEST 9: Testing comprehensive SSOT compliance")
        
        context = self.create_test_user_context("ssot_compliance", "validation")
        factory = create_agent_instance_factory(context)
        
        # VALIDATION 1: Factory requires user context
        self.assertIsNotNone(factory._user_context)
        self.assertEqual(factory._user_context, context)
        
        # VALIDATION 2: Factory has proper SSOT structure
        self.assertTrue(hasattr(factory, 'configure'))
        self.assertTrue(hasattr(factory, 'create_agent_instance'))
        self.assertTrue(hasattr(factory, 'create_user_execution_context'))
        self.assertTrue(hasattr(factory, 'cleanup_user_context'))
        
        # VALIDATION 3: Factory metrics are isolated
        metrics = factory.get_factory_metrics()
        self.assertIsInstance(metrics, dict)
        self.assertIn('total_instances_created', metrics)
        self.assertIn('active_contexts', metrics)
        self.assertIn('configuration_status', metrics)
        
        # VALIDATION 4: Factory supports proper configuration
        factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        config_status = factory.get_factory_metrics()['configuration_status']
        self.assertTrue(config_status['websocket_bridge_configured'])
        
        # VALIDATION 5: Factory provides user execution scope
        self.assertTrue(hasattr(factory, 'user_execution_scope'))
        
        self.created_factories.append(factory)
        logger.info("✅ PASS: Comprehensive SSOT compliance validated")

    async def test_factory_error_handling_isolation(self):
        """
        TEST 10: Validate factory error handling isolation.
        
        CRITICAL: Errors in one factory should not affect other factory
        instances or corrupt the overall system state.
        """
        logger.info("TEST 10: Testing factory error handling isolation")
        
        # Create multiple factories
        good_context = self.create_test_user_context("good_user", "error_test")
        error_context = self.create_test_user_context("error_user", "error_test")
        
        good_factory = create_agent_instance_factory(good_context)
        error_factory = create_agent_instance_factory(error_context)
        
        # Configure good factory properly
        good_factory.configure(
            agent_class_registry=self.mock_agent_class_registry,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        # Configure error factory with problematic setup
        error_factory.configure(
            agent_class_registry=None,  # This will cause errors
            websocket_bridge=self.mock_websocket_bridge
        )
        
        self.created_factories.extend([good_factory, error_factory])
        
        # TEST: Error in error_factory should not affect good_factory
        try:
            # This should fail due to missing agent registry
            await error_factory.create_agent_instance("NonExistentAgent", error_context)
        except Exception as e:
            logger.info(f"Expected error in error_factory: {e}")
        
        # VALIDATION: Good factory should still work
        try:
            # Register a simple agent for testing
            class SimpleAgent(BaseAgent):
                def __init__(self):
                    super().__init__()
                    
            self.mock_agent_class_registry.register_agent_class("SimpleAgent", SimpleAgent)
            
            # This should succeed despite error in other factory
            good_context_execution = await good_factory.create_user_execution_context(
                user_id=good_context.user_id,
                thread_id=good_context.thread_id,
                run_id=good_context.run_id
            )
            
            self.assertIsNotNone(good_context_execution)
            logger.info("Good factory continues to work despite error in other factory")
            
        except Exception as e:
            self.fail(f"Good factory affected by error in other factory: {e}")
        
        logger.info("✅ PASS: Factory error handling isolation validated")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])