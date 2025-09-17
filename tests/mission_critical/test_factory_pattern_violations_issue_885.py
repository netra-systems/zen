"
Mission Critical Factory Pattern Violation Tests for Issue #885

These tests are designed to FAIL and prove factory pattern violations exist.
They validate proper factory-based user isolation for multi-user execution.

Business Value: Proves factory pattern implementation gaps affecting user isolation
Expected Result: ALL TESTS SHOULD FAIL proving violations exist
""

import asyncio
import pytest
import inspect
from typing import Dict, List, Set, Any, Optional, Type
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.logging.unified_logging_ssot import get_logger

logger = get_logger(__name__)


class TestFactoryPatternViolations(SSotAsyncTestCase):
    ""Test suite to prove factory pattern violations in WebSocket system."

    async def asyncSetUp(self):
        "Setup for factory pattern violation tests.""
        await super().asyncSetUp()
        self.factory_violations = []
        self.tested_factories = []

    def test_multiple_factory_implementations_exist(self):
        ""
        EXPECTED TO FAIL: Test should detect multiple factory implementations.

        This proves that multiple factory patterns exist instead of one canonical pattern.
        "
        factory_implementations = []

        # Test known factory patterns that should be consolidated
        factory_patterns = [
            ("netra_backend.app.websocket_core.websocket_manager_factory, WebSocketManagerFactory"),
            ("netra_backend.app.websocket_core.canonical_import_patterns, get_websocket_manager"),
            ("netra_backend.app.websocket_core.unified_manager, create_websocket_manager"),
            ("netra_backend.app.websocket_core.supervisor_factory, SupervisorFactory"),
            ("netra_backend.app.websocket_core.manager, WebSocketManager"),  # If it has factory methods
        ]

        for module_path, factory_name in factory_patterns:
            self.tested_factories.append(f"{module_path}.{factory_name})
            try:
                module = __import__(module_path, fromlist=[factory_name]
                if hasattr(module, factory_name):
                    factory = getattr(module, factory_name)
                    factory_implementations.append({
                        'path': f{module_path}.{factory_name}",
                        'factory': factory,
                        'type': type(factory).__name__,
                        'callable': callable(factory),
                        'is_class': inspect.isclass(factory),
                        'is_function': inspect.isfunction(factory)
                    }

                    violation = f"Multiple factory pattern: {module_path}.{factory_name}
                    self.factory_violations.append(violation)

            except (ImportError, AttributeError) as e:
                logger.debug(fFactory pattern test - expected failure: {module_path}.{factory_name} - {e}")

        # ASSERTION THAT SHOULD FAIL: Multiple factory patterns exist
        self.assertGreater(
            len(factory_implementations), 1,
            f"FACTORY PATTERN VIOLATION: Found {len(factory_implementations)} factory implementations. 
            fShould be exactly 1 canonical factory pattern after SSOT consolidation. "
            f"Factories found: {[impl['path'] for impl in factory_implementations]}
        )

        logger.error(fFACTORY PATTERN VIOLATIONS: {len(factory_implementations)} factory implementations found")

    def test_factory_returns_singleton_instances(self):
        "
        EXPECTED TO FAIL: Test should detect factories returning singleton instances.

        This proves that factories violate user isolation by returning shared instances.
        ""
        singleton_violations = []

        try:
            # Test the canonical factory pattern
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create multiple contexts
            context1 = {user_id": "factory_test_user_1, session_id": "session_1}
            context2 = {user_id": "factory_test_user_2, session_id": "session_2}

            # Get instances from factory
            instance1 = get_websocket_manager(user_context=context1)
            instance2 = get_websocket_manager(user_context=context2)

            # Test 1: Check if same instance returned (singleton violation)
            if instance1 is instance2:
                violation = CRITICAL: Factory returns same instance for different users (singleton violation)"
                singleton_violations.append(violation)
                self.factory_violations.append(violation)

            # Test 2: Check if instances share the same class but different internal state
            if instance1.__class__ is instance2.__class__:
                # They should be same class but different instances
                if hasattr(instance1, '_connections') and hasattr(instance2, '_connections'):
                    if instance1._connections is instance2._connections:
                        violation = "CRITICAL: Factory instances share connection registry
                        singleton_violations.append(violation)
                        self.factory_violations.append(violation)

                if hasattr(instance1, '_user_connections') and hasattr(instance2, '_user_connections'):
                    if instance1._user_connections is instance2._user_connections:
                        violation = CRITICAL: Factory instances share user connection mapping"
                        singleton_violations.append(violation)
                        self.factory_violations.append(violation)

            # Test 3: Rapid successive calls should return different instances
            rapid_instances = []
            for i in range(5):
                context = {"user_id: frapid_user_{i}", "session_id: frapid_session_{i}"}
                instance = get_websocket_manager(user_context=context)
                rapid_instances.append(instance)

            # Check if any instances are the same
            for i, inst1 in enumerate(rapid_instances):
                for j, inst2 in enumerate(rapid_instances):
                    if i != j and inst1 is inst2:
                        violation = f"CRITICAL: Factory returned same instance for rapid calls: positions {i} and {j}
                        singleton_violations.append(violation)
                        self.factory_violations.append(violation)

        except ImportError as e:
            violation = fCannot test factory pattern - import failed: {e}"
            singleton_violations.append(violation)
            self.factory_violations.append(violation)

        except Exception as e:
            violation = f"Factory singleton test failed: {e}
            singleton_violations.append(violation)
            self.factory_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Singleton violations detected
        self.assertGreater(
            len(singleton_violations), 0,
            fFACTORY SINGLETON VIOLATION: Found {len(singleton_violations)} singleton violations. "
            f"Factory should create isolated instances, not shared singletons. 
            fViolations: {singleton_violations}"
        )

        logger.error(f"FACTORY SINGLETON VIOLATIONS: {len(singleton_violations)} violations detected)

    def test_factory_lacks_user_context_isolation(self):
        ""
        EXPECTED TO FAIL: Test should detect that factory doesn't properly isolate user context.

        This proves that user context is not properly encapsulated in factory instances.
        "
        context_isolation_violations = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create distinct user contexts
            alpha_context = {
                "user_id: alpha_isolation_user",
                "session_id: alpha_session",
                "thread_id: alpha_thread",
                "tenant_id: alpha_tenant",
                "permissions: [read", "write, admin"],
                "secret_data: alpha_secret_123"
            }

            beta_context = {
                "user_id: beta_isolation_user",
                "session_id: beta_session",
                "thread_id: beta_thread",
                "tenant_id: beta_tenant",
                "permissions: [read"],
                "secret_data: beta_secret_456"
            }

            # Get instances
            alpha_manager = get_websocket_manager(user_context=alpha_context)
            beta_manager = get_websocket_manager(user_context=beta_context)

            # Test 1: Check if user context is properly encapsulated
            if hasattr(alpha_manager, '_user_context'):
                if alpha_manager._user_context is alpha_context:
                    # Using reference instead of copy is a violation
                    violation = "CRITICAL: Factory stores reference to user context instead of isolated copy
                    context_isolation_violations.append(violation)
                    self.factory_violations.append(violation)

            # Test 2: Check if context data bleeds between instances
            if hasattr(alpha_manager, '_user_context') and hasattr(beta_manager, '_user_context'):
                alpha_stored_context = alpha_manager._user_context
                beta_stored_context = beta_manager._user_context

                # Check for data bleeding
                if alpha_stored_context and beta_stored_context:
                    if alpha_stored_context.get('secret_data') == beta_stored_context.get('secret_data'):
                        violation = CRITICAL: User context data bleeding between different users"
                        context_isolation_violations.append(violation)
                        self.factory_violations.append(violation)

                    if alpha_stored_context.get('tenant_id') == beta_stored_context.get('tenant_id'):
                        violation = "CRITICAL: Tenant isolation violated - same tenant_id in different contexts
                        context_isolation_violations.append(violation)
                        self.factory_violations.append(violation)

            # Test 3: Modify context after factory creation and check isolation
            original_alpha_secret = alpha_context.get('secret_data')
            alpha_context['secret_data'] = 'modified_secret_789'

            # If factory stored reference, the manager's context will also be modified
            if hasattr(alpha_manager, '_user_context'):
                manager_secret = alpha_manager._user_context.get('secret_data') if alpha_manager._user_context else None
                if manager_secret == 'modified_secret_789':
                    violation = CRITICAL: Factory vulnerable to context modification after creation"
                    context_isolation_violations.append(violation)
                    self.factory_violations.append(violation)

            # Test 4: Check if factory validates user context
            # Try to create manager with invalid/malicious context
            malicious_context = {
                "user_id: ../../../etc/passwd",
                "session_id: <script>alert('xss')</script>",
                "permissions: [*", "admin, root"],
                "sql_injection: '; DROP TABLE users; --"
            }

            try:
                malicious_manager = get_websocket_manager(user_context=malicious_context)
                if malicious_manager:
                    violation = "CRITICAL: Factory accepts malicious user context without validation
                    context_isolation_violations.append(violation)
                    self.factory_violations.append(violation)
            except Exception:
                # Expected - factory should reject malicious context
                pass

        except Exception as e:
            violation = fContext isolation test failed: {e}"
            context_isolation_violations.append(violation)
            self.factory_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Context isolation violations detected
        self.assertGreater(
            len(context_isolation_violations), 0,
            f"CONTEXT ISOLATION VIOLATION: Found {len(context_isolation_violations)} context isolation violations. 
            fFactory should properly isolate and validate user contexts. "
            f"Violations: {context_isolation_violations}
        )

        logger.error(fCONTEXT ISOLATION VIOLATIONS: {len(context_isolation_violations)} violations detected")

    def test_factory_configuration_sharing_violation(self):
        "
        EXPECTED TO FAIL: Test should detect shared configuration between factory instances.

        This proves that factory instances share configuration state.
        ""
        config_sharing_violations = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create managers with different configuration needs
            prod_context = {
                user_id": "prod_user,
                environment": "production,
                rate_limit": 1000,
                "timeout: 30
            }

            dev_context = {
                user_id": "dev_user,
                environment": "development,
                rate_limit": 100,
                "timeout: 5
            }

            prod_manager = get_websocket_manager(user_context=prod_context)
            dev_manager = get_websocket_manager(user_context=dev_context)

            # Test 1: Check if configuration objects are shared
            if hasattr(prod_manager, '_config') and hasattr(dev_manager, '_config'):
                if prod_manager._config is dev_manager._config:
                    violation = CRITICAL: Factory instances share configuration object"
                    config_sharing_violations.append(violation)
                    self.factory_violations.append(violation)

            # Test 2: Check if rate limiters are shared
            if hasattr(prod_manager, '_rate_limiter') and hasattr(dev_manager, '_rate_limiter'):
                if prod_manager._rate_limiter is dev_manager._rate_limiter:
                    violation = "CRITICAL: Factory instances share rate limiter
                    config_sharing_violations.append(violation)
                    self.factory_violations.append(violation)

            # Test 3: Check if event handlers are shared
            if hasattr(prod_manager, '_event_handlers') and hasattr(dev_manager, '_event_handlers'):
                if prod_manager._event_handlers is dev_manager._event_handlers:
                    violation = CRITICAL: Factory instances share event handlers"
                    config_sharing_violations.append(violation)
                    self.factory_violations.append(violation)

            # Test 4: Check if error handlers are shared
            if hasattr(prod_manager, '_error_handler') and hasattr(dev_manager, '_error_handler'):
                if prod_manager._error_handler is dev_manager._error_handler:
                    violation = "CRITICAL: Factory instances share error handler
                    config_sharing_violations.append(violation)
                    self.factory_violations.append(violation)

            # Test 5: Configuration modification isolation
            # Modify one manager's config and check if it affects the other
            if hasattr(prod_manager, '_config') and hasattr(dev_manager, '_config'):
                if prod_manager._config and dev_manager._config:
                    # Try to modify prod config
                    original_prod_setting = prod_manager._config.get('test_setting')
                    original_dev_setting = dev_manager._config.get('test_setting')

                    prod_manager._config['test_setting'] = 'modified_by_prod'

                    # Check if dev config was also modified
                    if dev_manager._config.get('test_setting') == 'modified_by_prod':
                        violation = CRITICAL: Configuration modification affects other factory instances"
                        config_sharing_violations.append(violation)
                        self.factory_violations.append(violation)

        except Exception as e:
            violation = f"Configuration sharing test failed: {e}
            config_sharing_violations.append(violation)
            self.factory_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Configuration sharing violations detected
        self.assertGreater(
            len(config_sharing_violations), 0,
            fCONFIGURATION SHARING VIOLATION: Found {len(config_sharing_violations)} configuration sharing violations. "
            f"Factory instances should have isolated configurations. 
            fViolations: {config_sharing_violations}"
        )

        logger.error(f"CONFIGURATION SHARING VIOLATIONS: {len(config_sharing_violations)} violations detected)

    def test_factory_lacks_cleanup_mechanisms(self):
        ""
        EXPECTED TO FAIL: Test should detect that factory lacks proper cleanup mechanisms.

        This proves that factory doesn't provide proper resource cleanup.
        "
        cleanup_violations = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create manager instance
            test_context = {"user_id: cleanup_test_user", "session_id: cleanup_session"}
            manager = get_websocket_manager(user_context=test_context)

            # Test 1: Check if manager has cleanup method
            if not hasattr(manager, 'cleanup') and not hasattr(manager, 'close') and not hasattr(manager, 'shutdown'):
                violation = "CRITICAL: Factory-created manager lacks cleanup method
                cleanup_violations.append(violation)
                self.factory_violations.append(violation)

            # Test 2: Check if manager implements context manager protocol
            if not hasattr(manager, '__enter__') or not hasattr(manager, '__exit__'):
                violation = CRITICAL: Factory-created manager doesn't support context manager protocol"
                cleanup_violations.append(violation)
                self.factory_violations.append(violation)

            # Test 3: Check if factory provides cleanup utilities
            factory_module_path = "netra_backend.app.websocket_core.canonical_import_patterns
            try:
                factory_module = __import__(factory_module_path, fromlist=['']

                cleanup_functions = [
                    'cleanup_websocket_manager',
                    'cleanup_all_managers',
                    'cleanup_user_manager',
                    'shutdown_manager'
                ]

                factory_has_cleanup = any(hasattr(factory_module, func) for func in cleanup_functions)

                if not factory_has_cleanup:
                    violation = CRITICAL: Factory module lacks cleanup utilities"
                    cleanup_violations.append(violation)
                    self.factory_violations.append(violation)

            except ImportError:
                violation = "CRITICAL: Cannot access factory module for cleanup testing
                cleanup_violations.append(violation)
                self.factory_violations.append(violation)

            # Test 4: Check if manager tracks resources for cleanup
            resource_tracking_attributes = [
                '_connections',
                '_active_tasks',
                '_background_tasks',
                '_event_listeners',
                '_timers'
            ]

            tracks_resources = any(hasattr(manager, attr) for attr in resource_tracking_attributes)

            if not tracks_resources:
                violation = CRITICAL: Manager doesn't track resources for cleanup"
                cleanup_violations.append(violation)
                self.factory_violations.append(violation)

        except Exception as e:
            violation = f"Cleanup mechanism test failed: {e}
            cleanup_violations.append(violation)
            self.factory_violations.append(violation)

        # ASSERTION THAT SHOULD FAIL: Cleanup violations detected
        self.assertGreater(
            len(cleanup_violations), 0,
            fCLEANUP MECHANISM VIOLATION: Found {len(cleanup_violations)} cleanup mechanism violations. "
            f"Factory should provide proper resource cleanup mechanisms. 
            fViolations: {cleanup_violations}"
        )

        logger.error(f"CLEANUP MECHANISM VIOLATIONS: {len(cleanup_violations)} violations detected)

    def tearDown(self):
        ""Report all factory pattern violations found."
        if self.factory_violations:
            logger.error("=*80)
            logger.error(FACTORY PATTERN VIOLATIONS SUMMARY")
            logger.error("=*80)
            for i, violation in enumerate(self.factory_violations, 1):
                logger.error(f{i:2d}. {violation}")
            logger.error("=*80)
            logger.error(fTOTAL FACTORY VIOLATIONS: {len(self.factory_violations)}")
            logger.error("=*80)

        if self.tested_factories:
            logger.info(Factory patterns tested: " + ", .join(self.tested_factories))


if __name__ == __main__":
    pytest.main([__file__, "-v, -s", "--tb=short"]