#!/usr/bin/env python
"""Unit Test: Issue #960 WebSocket Manager Factory Consolidation

GitHub Issue: #960 WebSocket Manager SSOT fragmentation crisis

THIS TEST VALIDATES FACTORY PATTERN SSOT COMPLIANCE.
Business Value: $500K+ ARR - Validates factory patterns delegate to SSOT properly

PURPOSE:
- Test validates that all factory patterns delegate to SSOT implementation
- This test SHOULD FAIL initially (proving factories create independent instances)
- This test SHOULD PASS after SSOT factory consolidation (proving delegation works)
- Validates factory instance sharing and user context binding

CRITICAL FACTORY VIOLATIONS DETECTED:
- Factories create independent instances instead of delegating to SSOT
- Different factories return different instances for same user context
- Factories don't properly bind user contexts for isolation
- Factory pattern violations create multi-user contamination risks

TEST STRATEGY:
1. Test all known factory functions and their delegation behavior
2. Validate that factories return shared instances for same user context
3. Test factory user context binding for proper isolation
4. Validate factory dependency injection patterns
5. This test should FAIL until factory consolidation is complete

BUSINESS IMPACT:
Factory pattern violations create user isolation failures and inconsistent
WebSocket behavior, breaking the Golden Path user flow where users login
and receive AI responses without cross-user contamination.
"""

import os
import sys
import asyncio
import inspect
import importlib
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple, Callable
from collections import defaultdict
from unittest.mock import MagicMock, patch

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import test framework
from test_framework.ssot.base_test_case import SSotBaseTestCase
import pytest
from loguru import logger


class WebSocketManagerFactoryConsolidationTests(SSotBaseTestCase):
    """Issue #960: WebSocket Manager Factory Consolidation Validation

    This test validates that factory patterns properly delegate to SSOT
    implementations and maintain user isolation.

    Expected Behavior:
    - This test SHOULD FAIL initially (proving factory violations exist)
    - This test SHOULD PASS after SSOT factory consolidation (proving delegation works)
    """

    def setup_method(self, method):
        """Set up test environment for factory consolidation validation."""
        super().setup_method(method)

        # Define factory functions to analyze
        self.factory_functions = {}
        self.factory_violations = defaultdict(list)

        # Define user contexts for testing isolation
        self.test_user_contexts = [
            {'user_id': 'user1', 'thread_id': 'thread1'},
            {'user_id': 'user2', 'thread_id': 'thread2'},
            {'user_id': 'user1', 'thread_id': 'thread3'},  # Same user, different thread
        ]

        # Factory function specifications to test
        self.factory_specs = [
            ('netra_backend.app.websocket_core.websocket_manager', 'get_websocket_manager'),
            ('netra_backend.app.websocket_core.websocket_manager_factory', 'create_websocket_manager'),
            ('netra_backend.app.websocket_core.websocket_manager_factory', 'get_websocket_manager_factory'),
            ('netra_backend.app.websocket_core.unified_manager', 'get_websocket_manager'),
        ]

        # Load factory functions for analysis
        self._load_factory_functions()

    def test_factory_delegation_to_ssot(self):
        """CRITICAL: Detect factories creating instances instead of delegating (SHOULD FAIL initially)

        This test validates that factory functions delegate to SSOT implementation
        rather than creating independent instances.
        """
        logger.info("🔍 Testing factory delegation to SSOT implementation...")

        delegation_violations = []

        for factory_name, factory_func in self.factory_functions.items():
            if factory_func:
                try:
                    # Test factory behavior with mock user context
                    test_context = self.test_user_contexts[0]

                    # Check if factory is async
                    if asyncio.iscoroutinefunction(factory_func):
                        # Test async factory
                        manager_instance = asyncio.run(self._test_async_factory_delegation(factory_func, test_context))
                    else:
                        # Test sync factory
                        manager_instance = self._test_sync_factory_delegation(factory_func, test_context)

                    if manager_instance:
                        # Analyze instance creation pattern
                        instance_class = manager_instance.__class__
                        instance_module = instance_class.__module__

                        # Check if instance comes from SSOT module
                        is_ssot_instance = 'unified_manager' in instance_module

                        if not is_ssot_instance:
                            delegation_violations.append({
                                'factory_name': factory_name,
                                'instance_class': f"{instance_module}.{instance_class.__name__}",
                                'violation_type': 'non_ssot_instance_creation',
                                'expected_module': 'unified_manager'
                            })

                            logger.error(f"🚨 DELEGATION VIOLATION: {factory_name}")
                            logger.error(f"  Creates instance: {instance_module}.{instance_class.__name__}")
                            logger.error(f"  Expected SSOT module: unified_manager")

                except Exception as e:
                    logger.warning(f"⚠️ Could not test factory {factory_name}: {e}")
                    delegation_violations.append({
                        'factory_name': factory_name,
                        'violation_type': 'factory_test_failure',
                        'error': str(e)
                    })

        self.factory_violations['delegation_violations'] = delegation_violations

        # ASSERTION: This should FAIL initially if delegation violations exist
        assert len(delegation_violations) == 0, (
            f"Factory SSOT VIOLATION: Found {len(delegation_violations)} factories not delegating to SSOT. "
            f"Violating factories: {[v['factory_name'] for v in delegation_violations]}. "
            f"SSOT requires all factories to delegate to unified_manager implementation."
        )

    def test_factory_instance_sharing(self):
        """CRITICAL: Detect factories returning different instances (SHOULD FAIL initially)

        This test validates that different factory functions return the same manager
        instance for the same user context, ensuring SSOT compliance.
        """
        logger.info("🔍 Testing factory instance sharing for SSOT compliance...")

        instance_sharing_violations = []

        # Test instance sharing across different factories for same user context
        test_context = self.test_user_contexts[0]
        factory_instances = {}

        for factory_name, factory_func in self.factory_functions.items():
            if factory_func:
                try:
                    # Get manager instance from factory
                    if asyncio.iscoroutinefunction(factory_func):
                        manager_instance = asyncio.run(self._get_manager_from_async_factory(factory_func, test_context))
                    else:
                        manager_instance = self._get_manager_from_sync_factory(factory_func, test_context)

                    if manager_instance:
                        factory_instances[factory_name] = {
                            'instance': manager_instance,
                            'instance_id': id(manager_instance),
                            'instance_class': manager_instance.__class__.__name__
                        }

                except Exception as e:
                    logger.warning(f"⚠️ Could not get instance from factory {factory_name}: {e}")

        # Analyze instance sharing
        if len(factory_instances) > 1:
            # Check if all factories return the same instance
            instance_ids = [data['instance_id'] for data in factory_instances.values()]
            unique_instance_ids = set(instance_ids)

            if len(unique_instance_ids) > 1:
                instance_sharing_violations.append({
                    'user_context': test_context,
                    'factory_instances': factory_instances,
                    'unique_instances': len(unique_instance_ids),
                    'violation_type': 'multiple_instances_for_same_context'
                })

                logger.error(f"🚨 INSTANCE SHARING VIOLATION: Multiple instances for same user context")
                logger.error(f"  User context: {test_context}")
                logger.error(f"  Unique instances: {len(unique_instance_ids)}")
                for factory_name, data in factory_instances.items():
                    logger.error(f"  {factory_name}: {data['instance_class']} (id: {data['instance_id']})")

        self.factory_violations['instance_sharing_violations'] = instance_sharing_violations

        # ASSERTION: This should FAIL initially if instance sharing violations exist
        assert len(instance_sharing_violations) == 0, (
            f"Factory SSOT VIOLATION: Found {len(instance_sharing_violations)} instance sharing violations. "
            f"Different factories return different instances for same user context. "
            f"SSOT requires all factories to return the same manager instance for same user context."
        )

    def test_factory_user_context_binding(self):
        """CRITICAL: Detect factories not properly binding user contexts (SHOULD FAIL initially)

        This test validates that factories properly bind user contexts for isolation
        and return different instances for different user contexts.
        """
        logger.info("🔍 Testing factory user context binding for isolation...")

        context_binding_violations = []

        # Test each factory with different user contexts
        for factory_name, factory_func in self.factory_functions.items():
            if factory_func:
                context_instances = {}

                for context in self.test_user_contexts:
                    try:
                        # Get manager instance for this context
                        if asyncio.iscoroutinefunction(factory_func):
                            manager_instance = asyncio.run(self._get_manager_from_async_factory(factory_func, context))
                        else:
                            manager_instance = self._get_manager_from_sync_factory(factory_func, context)

                        if manager_instance:
                            context_key = f"{context['user_id']}:{context['thread_id']}"
                            context_instances[context_key] = {
                                'context': context,
                                'instance': manager_instance,
                                'instance_id': id(manager_instance)
                            }

                    except Exception as e:
                        logger.warning(f"⚠️ Could not test context binding for {factory_name} with {context}: {e}")

                # Analyze user context isolation
                if len(context_instances) > 1:
                    # Check isolation patterns
                    same_user_different_thread = []
                    different_users = []

                    for ctx1_key, ctx1_data in context_instances.items():
                        for ctx2_key, ctx2_data in context_instances.items():
                            if ctx1_key != ctx2_key:
                                ctx1 = ctx1_data['context']
                                ctx2 = ctx2_data['context']

                                if ctx1['user_id'] == ctx2['user_id'] and ctx1['thread_id'] != ctx2['thread_id']:
                                    # Same user, different thread - should have different instances
                                    if ctx1_data['instance_id'] == ctx2_data['instance_id']:
                                        same_user_different_thread.append({
                                            'context1': ctx1,
                                            'context2': ctx2,
                                            'shared_instance_id': ctx1_data['instance_id']
                                        })

                                if ctx1['user_id'] != ctx2['user_id']:
                                    # Different users - should definitely have different instances
                                    if ctx1_data['instance_id'] == ctx2_data['instance_id']:
                                        different_users.append({
                                            'context1': ctx1,
                                            'context2': ctx2,
                                            'shared_instance_id': ctx1_data['instance_id']
                                        })

                    # Check for violations
                    if same_user_different_thread or different_users:
                        context_binding_violations.append({
                            'factory_name': factory_name,
                            'same_user_violations': same_user_different_thread,
                            'different_user_violations': different_users,
                            'violation_type': 'context_isolation_failure'
                        })

                        logger.error(f"🚨 CONTEXT BINDING VIOLATION: {factory_name}")
                        if same_user_different_thread:
                            logger.error(f"  Same user, different thread sharing instances: {len(same_user_different_thread)}")
                        if different_users:
                            logger.error(f"  Different users sharing instances: {len(different_users)}")

        self.factory_violations['context_binding_violations'] = context_binding_violations

        # ASSERTION: This should FAIL initially if context binding violations exist
        assert len(context_binding_violations) == 0, (
            f"Factory SSOT VIOLATION: Found {len(context_binding_violations)} context binding violations. "
            f"Factories not properly isolating user contexts. "
            f"SSOT requires proper user context isolation to prevent data contamination."
        )

    def test_validate_factory_dependency_injection_patterns(self):
        """VALIDATION: Check factory dependency injection patterns

        This test validates that factories use proper dependency injection
        patterns for SSOT compliance.
        """
        logger.info("🔍 Validating factory dependency injection patterns...")

        injection_analysis = {}

        for factory_name, factory_func in self.factory_functions.items():
            if factory_func:
                try:
                    # Analyze function signature for dependency injection patterns
                    signature = inspect.signature(factory_func)
                    parameters = signature.parameters

                    # Check for user context parameter
                    has_user_context = any(
                        'user_context' in param_name.lower() or 'context' in param_name.lower()
                        for param_name in parameters.keys()
                    )

                    # Check for dependency injection parameters
                    has_dependencies = any(
                        'websocket' in param_name.lower() or 'manager' in param_name.lower()
                        for param_name in parameters.keys()
                    )

                    injection_analysis[factory_name] = {
                        'signature': str(signature),
                        'parameter_count': len(parameters),
                        'has_user_context': has_user_context,
                        'has_dependencies': has_dependencies,
                        'parameters': list(parameters.keys())
                    }

                    logger.info(f"✓ Factory analysis: {factory_name}")
                    logger.info(f"  Signature: {signature}")
                    logger.info(f"  User context parameter: {has_user_context}")

                except Exception as e:
                    logger.warning(f"⚠️ Could not analyze factory {factory_name}: {e}")

        # Log injection pattern analysis
        logger.info("📊 Factory Dependency Injection Analysis:")
        for factory_name, analysis in injection_analysis.items():
            logger.info(f"  {factory_name}:")
            logger.info(f"    Parameters: {analysis['parameter_count']}")
            logger.info(f"    User context: {analysis['has_user_context']}")
            logger.info(f"    Dependencies: {analysis['has_dependencies']}")

        self.factory_violations['injection_analysis'] = injection_analysis

        # This test provides information but doesn't fail
        # It helps understand factory patterns for consolidation

    def _load_factory_functions(self):
        """Load factory functions for analysis."""
        for module_path, function_name in self.factory_specs:
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, function_name):
                    factory_func = getattr(module, function_name)
                    factory_key = f"{module_path}.{function_name}"
                    self.factory_functions[factory_key] = factory_func
                    logger.info(f"✓ Loaded factory function: {factory_key}")
                else:
                    logger.warning(f"⚠️ Function {function_name} not found in {module_path}")
                    self.factory_functions[f"{module_path}.{function_name}"] = None
            except ImportError as e:
                logger.warning(f"⚠️ Could not import {module_path}: {e}")
                self.factory_functions[f"{module_path}.{function_name}"] = None

    def _test_sync_factory_delegation(self, factory_func, user_context):
        """Test sync factory delegation behavior."""
        try:
            # Test with different parameter patterns
            signature = inspect.signature(factory_func)
            parameters = signature.parameters

            if 'user_context' in parameters:
                return factory_func(user_context=user_context)
            elif len(parameters) > 0:
                # Try positional parameter
                return factory_func(user_context)
            else:
                # No parameters
                return factory_func()
        except Exception as e:
            logger.warning(f"Sync factory test failed: {e}")
            return None

    async def _test_async_factory_delegation(self, factory_func, user_context):
        """Test async factory delegation behavior."""
        try:
            # Test with different parameter patterns
            signature = inspect.signature(factory_func)
            parameters = signature.parameters

            if 'user_context' in parameters:
                return await factory_func(user_context=user_context)
            elif len(parameters) > 0:
                # Try positional parameter
                return await factory_func(user_context)
            else:
                # No parameters
                return await factory_func()
        except Exception as e:
            logger.warning(f"Async factory test failed: {e}")
            return None

    def _get_manager_from_sync_factory(self, factory_func, user_context):
        """Get manager instance from sync factory."""
        return self._test_sync_factory_delegation(factory_func, user_context)

    async def _get_manager_from_async_factory(self, factory_func, user_context):
        """Get manager instance from async factory."""
        return await self._test_async_factory_delegation(factory_func, user_context)

    def teardown_method(self, method):
        """Clean up and log factory consolidation results."""
        if self.factory_violations:
            logger.info("📊 Factory Consolidation Analysis Summary:")

            total_violations = 0
            for violation_type, violations in self.factory_violations.items():
                if isinstance(violations, list) and violations:
                    count = len(violations)
                    total_violations += count
                    logger.warning(f"  {violation_type}: {count} violations")
                elif isinstance(violations, dict):
                    logger.info(f"  {violation_type}: analyzed {len(violations)} factories")

            if total_violations > 0:
                logger.error(f"🚨 TOTAL FACTORY VIOLATIONS: {total_violations}")
                logger.error("💡 Factory consolidation required for SSOT compliance")
            else:
                logger.info("✅ No factory violations detected - delegation patterns are SSOT compliant")

        super().teardown_method(method)


if __name__ == "__main__":
    # Run this test directly to check factory consolidation
    # MIGRATED: Use SSOT unified test runner
    # python tests/unified_test_runner.py --category unit
    pass  # TODO: Replace with appropriate SSOT test execution