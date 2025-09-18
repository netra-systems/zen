#!/usr/bin/env python3
"""Unit Tests: WebSocket Manager Fragmentation Detection - Issue #824

PURPOSE: Detect and validate WebSocket Manager fragmentation issues that break Golden Path

BUSINESS IMPACT:
- Priority: P0 CRITICAL
- Impact: $500K+ ARR Golden Path functionality
- Root Cause: Multiple WebSocket Manager implementations causing race conditions

TEST OBJECTIVES:
1. Detect circular import dependencies between WebSocket modules
2. Validate SSOT compliance - only ONE WebSocketManager implementation should exist
3. Test import path consistency across all WebSocket factory patterns
4. Reproduce race conditions caused by multiple managers
5. Validate user isolation fails with fragmented implementations

EXPECTED BEHAVIOR:
- Tests should FAIL with current fragmentation (multiple managers)
- Tests should PASS after SSOT consolidation to unified_manager.py only

This test suite MUST be run without Docker dependencies (unit test category).
"""

import sys
import os
import importlib
import inspect
from typing import Set, Dict, List, Any, Optional
from unittest.mock import patch, MagicMock
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestWebSocketManagerFragmentationDetection(SSotBaseTestCase, unittest.TestCase):
    """Test suite to detect WebSocket Manager fragmentation causing SSOT violations."""

    def setUp(self):
        """Set up test environment for fragmentation detection."""
        super().setUp()
        self.websocket_modules = [
            'netra_backend.app.websocket_core.unified_manager',
            'netra_backend.app.websocket_core.websocket_manager',
            'netra_backend.app.websocket_core.websocket_manager_factory',
            'netra_backend.app.websocket_core.migration_adapter',
            'netra_backend.app.websocket_core.__init__'
        ]

    def test_detect_multiple_websocket_manager_classes(self):
        """
        FRAGMENTATION TEST: Detect multiple WebSocketManager class implementations.

        EXPECTED TO FAIL: Current system has multiple manager classes
        EXPECTED TO PASS: After consolidation to unified_manager.py only
        """
        manager_classes = []

        for module_path in self.websocket_modules:
            try:
                module = importlib.import_module(module_path)

                # Look for WebSocketManager classes
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if 'WebSocketManager' in name and not name.startswith('_'):
                        manager_classes.append({
                            'module': module_path,
                            'class': name,
                            'object': obj
                        })

                # Look for WebSocketManager aliases/assignments
                for name in dir(module):
                    if name == 'WebSocketManager' or name == 'UnifiedWebSocketManager':
                        obj = getattr(module, name)
                        if inspect.isclass(obj):
                            manager_classes.append({
                                'module': module_path,
                                'class': name,
                                'object': obj,
                                'is_alias': True
                            })

            except ImportError as e:
                self.logger.warning(f"Could not import {module_path}: {e}")
                continue

        self.logger.info(f"Found {len(manager_classes)} WebSocketManager implementations:")
        for manager in manager_classes:
            self.logger.info(f"  - {manager['module']}.{manager['class']}")

        # ASSERTION: Should have only ONE actual implementation
        # Current state: WILL FAIL due to fragmentation
        # Target state: WILL PASS with unified_manager.py only
        actual_implementations = [m for m in manager_classes if not m.get('is_alias', False)]

        self.assertEqual(
            len(actual_implementations), 1,
            f"SSOT VIOLATION: Found {len(actual_implementations)} WebSocketManager implementations. "
            f"Expected exactly 1 in unified_manager.py only. "
            f"Found: {[m['module'] + '.' + m['class'] for m in actual_implementations]}"
        )

    def test_detect_multiple_get_websocket_manager_functions(self):
        """
        FRAGMENTATION TEST: Detect multiple get_websocket_manager() factory functions.

        EXPECTED TO FAIL: Current system has multiple factory functions
        EXPECTED TO PASS: After consolidation to single canonical function
        """
        factory_functions = []

        for module_path in self.websocket_modules:
            try:
                module = importlib.import_module(module_path)

                if hasattr(module, 'get_websocket_manager'):
                    func = getattr(module, 'get_websocket_manager')
                    factory_functions.append({
                        'module': module_path,
                        'function': func,
                        'signature': str(inspect.signature(func))
                    })

            except ImportError as e:
                self.logger.warning(f"Could not import {module_path}: {e}")
                continue

        self.logger.info(f"Found {len(factory_functions)} get_websocket_manager() functions:")
        for factory in factory_functions:
            self.logger.info(f"  - {factory['module']}.get_websocket_manager{factory['signature']}")

        # ASSERTION: Should have only ONE canonical factory function
        # Current state: WILL FAIL due to multiple functions
        # Target state: WILL PASS with single canonical function
        self.assertEqual(
            len(factory_functions), 1,
            f"FACTORY FRAGMENTATION: Found {len(factory_functions)} get_websocket_manager() functions. "
            f"Expected exactly 1 canonical function. "
            f"Found in modules: {[f['module'] for f in factory_functions]}"
        )

    def test_detect_circular_import_dependencies(self):
        """
        CIRCULAR DEPENDENCY TEST: Detect circular imports between WebSocket modules.

        EXPECTED TO FAIL: Current system has circular dependencies
        EXPECTED TO PASS: After removing circular import patterns
        """
        import_graph = {}

        for module_path in self.websocket_modules:
            try:
                # Clear module from cache to get fresh import analysis
                if module_path in sys.modules:
                    del sys.modules[module_path]

                # Import and analyze dependencies
                module = importlib.import_module(module_path)

                # Get module source to analyze imports
                try:
                    source_file = inspect.getfile(module)
                    with open(source_file, 'r', encoding='utf-8') as f:
                        source = f.read()

                    # Extract WebSocket-related imports
                    websocket_imports = []
                    for line in source.split('\n'):
                        line = line.strip()
                        if line.startswith('from ') and 'websocket' in line.lower():
                            if any(ws_module.split('.')[-1] in line for ws_module in self.websocket_modules):
                                websocket_imports.append(line)
                        elif line.startswith('import ') and 'websocket' in line.lower():
                            if any(ws_module.split('.')[-1] in line for ws_module in self.websocket_modules):
                                websocket_imports.append(line)

                    import_graph[module_path] = websocket_imports

                except (OSError, TypeError):
                    # Module might be built-in or not have a file
                    import_graph[module_path] = []

            except ImportError as e:
                self.logger.warning(f"Could not import {module_path}: {e}")
                import_graph[module_path] = []

        # Analyze for circular dependencies
        circular_deps = []
        for module_a, imports_a in import_graph.items():
            for module_b, imports_b in import_graph.items():
                if module_a != module_b:
                    # Check if A imports from B and B imports from A
                    a_imports_b = any(module_b.split('.')[-1] in imp for imp in imports_a)
                    b_imports_a = any(module_a.split('.')[-1] in imp for imp in imports_b)

                    if a_imports_b and b_imports_a:
                        circular_pair = tuple(sorted([module_a, module_b]))
                        if circular_pair not in circular_deps:
                            circular_deps.append(circular_pair)

        self.logger.info("Import dependency analysis:")
        for module, imports in import_graph.items():
            self.logger.info(f"  {module}:")
            for imp in imports:
                self.logger.info(f"    {imp}")

        if circular_deps:
            self.logger.error(f"CIRCULAR DEPENDENCIES DETECTED: {circular_deps}")

        # ASSERTION: Should have NO circular dependencies
        # Current state: MAY FAIL if circular dependencies exist
        # Target state: WILL PASS with no circular dependencies
        self.assertEqual(
            len(circular_deps), 0,
            f"CIRCULAR DEPENDENCY VIOLATION: Found {len(circular_deps)} circular dependencies. "
            f"Circular pairs: {circular_deps}. "
            f"This causes race conditions and initialization failures."
        )

    def test_websocket_manager_import_consistency(self):
        """
        IMPORT CONSISTENCY TEST: Validate all WebSocket imports resolve to same implementation.

        EXPECTED TO FAIL: Current system has inconsistent import paths
        EXPECTED TO PASS: After SSOT consolidation with consistent imports
        """
        import_paths = [
            'netra_backend.app.websocket_core.websocket_manager.WebSocketManager',
            'netra_backend.app.websocket_core.unified_manager.UnifiedWebSocketManager',
            'netra_backend.app.websocket_core.websocket_manager.UnifiedWebSocketManager'
        ]

        resolved_classes = {}

        for import_path in import_paths:
            try:
                module_path, class_name = import_path.rsplit('.', 1)
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name, None)

                if cls is not None:
                    resolved_classes[import_path] = {
                        'class': cls,
                        'id': id(cls),
                        'module': cls.__module__,
                        'name': cls.__name__
                    }

            except (ImportError, AttributeError) as e:
                self.logger.warning(f"Could not resolve {import_path}: {e}")
                resolved_classes[import_path] = None

        self.logger.info("WebSocket Manager import resolution:")
        for path, info in resolved_classes.items():
            if info:
                self.logger.info(f"  {path} -> {info['module']}.{info['name']} (id: {info['id']})")
            else:
                self.logger.info(f"  {path} -> FAILED TO RESOLVE")

        # Get all successfully resolved classes
        valid_classes = [info for info in resolved_classes.values() if info is not None]

        if len(valid_classes) > 1:
            # Check if all resolve to the same class object
            first_class_id = valid_classes[0]['id']
            all_same = all(info['id'] == first_class_id for info in valid_classes)

            if not all_same:
                unique_classes = {}
                for info in valid_classes:
                    key = f"{info['module']}.{info['name']}"
                    if key not in unique_classes:
                        unique_classes[key] = []
                    unique_classes[key].append(info['id'])

                self.logger.error(f"IMPORT INCONSISTENCY: Multiple distinct classes found: {unique_classes}")

        # ASSERTION: All imports should resolve to the same class object
        # Current state: MAY FAIL due to import inconsistencies
        # Target state: WILL PASS with consistent SSOT imports
        if len(valid_classes) > 1:
            unique_ids = set(info['id'] for info in valid_classes)
            self.assertEqual(
                len(unique_ids), 1,
                f"IMPORT INCONSISTENCY: WebSocket imports resolve to {len(unique_ids)} different classes. "
                f"All imports must resolve to the same SSOT implementation. "
                f"Classes found: {[info['module'] + '.' + info['name'] for info in valid_classes]}"
            )


class TestWebSocketManagerUserIsolationFragmentation(SSotBaseTestCase, unittest.TestCase):
    """Test user isolation failures caused by WebSocket Manager fragmentation."""

    def test_user_context_isolation_with_multiple_managers(self):
        """
        USER ISOLATION TEST: Validate user isolation fails with multiple manager instances.

        EXPECTED TO FAIL: Multiple managers break user isolation
        EXPECTED TO PASS: Single SSOT manager maintains proper isolation
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create test user contexts
        user1_context = UserExecutionContext(
            user_id="user_1_test",
            thread_id="thread_1",
            run_id="run_1",
            request_id="req_1"
        )

        user2_context = UserExecutionContext(
            user_id="user_2_test",
            thread_id="thread_2",
            run_id="run_2",
            request_id="req_2"
        )

        # Try to create managers for different users
        managers = []

        try:
            # Import from different paths to simulate fragmentation
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

            manager1 = WebSocketManager(user_context=user1_context)
            manager2 = WebSocketManager(user_context=user2_context)

            managers.extend([manager1, manager2])

            # Test user isolation
            self.assertNotEqual(
                id(manager1), id(manager2),
                "ISOLATION FAILURE: Managers should be different instances for different users"
            )

            self.assertNotEqual(
                manager1.user_context.user_id, manager2.user_context.user_id,
                "USER ISOLATION FAILURE: Managers have same user context"
            )

            # Test that managers don't share state
            if hasattr(manager1, '_connections') and hasattr(manager2, '_connections'):
                self.assertIsNot(
                    manager1._connections, manager2._connections,
                    "STATE SHARING VIOLATION: Managers share connection storage"
                )

        except Exception as e:
            self.logger.error(f"Failed to create isolated WebSocket managers: {e}")
            self.fail(f"WebSocket Manager fragmentation prevents proper user isolation: {e}")

    def test_websocket_manager_factory_consistency(self):
        """
        FACTORY CONSISTENCY TEST: Validate factory patterns produce consistent managers.

        EXPECTED TO FAIL: Fragmented factories produce inconsistent managers
        EXPECTED TO PASS: SSOT factory produces consistent managers
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        test_context = UserExecutionContext(
            user_id="test_factory_user",
            thread_id="test_thread",
            run_id="test_run",
            request_id="test_request"
        )

        managers_created = []
        creation_methods = []

        # Test different creation methods
        try:
            # Method 1: Direct instantiation
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            manager1 = WebSocketManager(user_context=test_context)
            managers_created.append(manager1)
            creation_methods.append("Direct WebSocketManager")

        except Exception as e:
            self.logger.warning(f"Direct WebSocketManager creation failed: {e}")

        try:
            # Method 2: Factory function (if exists)
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            manager2 = loop.run_until_complete(get_websocket_manager(user_context=test_context))
            managers_created.append(manager2)
            creation_methods.append("get_websocket_manager factory")
            loop.close()

        except Exception as e:
            self.logger.warning(f"Factory function creation failed: {e}")

        self.logger.info(f"Successfully created {len(managers_created)} managers via: {creation_methods}")

        if len(managers_created) > 1:
            # Validate all managers are of the same type
            manager_types = [type(manager).__name__ for manager in managers_created]
            unique_types = set(manager_types)

            self.assertEqual(
                len(unique_types), 1,
                f"FACTORY INCONSISTENCY: Different creation methods produce different manager types: {manager_types}"
            )

            # Validate all managers have the same user context
            for i, manager in enumerate(managers_created):
                self.assertEqual(
                    manager.user_context.user_id, test_context.user_id,
                    f"CONTEXT INCONSISTENCY: Manager {i} ({creation_methods[i]}) has wrong user context"
                )


if __name__ == '__main__':
    # Run tests with verbose output
    pytest.main([__file__, '-v', '--tb=short'])